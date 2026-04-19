"""
DO Core — Analyzer (Phase 4)
Heuristic-based future prediction: Distortion / Load / Flow / Suggestions.
No heavy ML dependencies — uses timeline trends + structural rules.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .kernel import DOKernel


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class FutureDistortion:
    node_id: str
    current: float
    predicted: float
    trend: float          # positive = worsening per step
    hotspot: bool         # predicted > 0.6


@dataclass
class FutureLoad:
    node_id: str
    current_ms: float
    predicted_ms: float
    spike_prob: float     # 0.0–1.0


@dataclass
class FutureFlow:
    edge_id: str
    current_count: int
    predicted_count: int
    direction_risk: float  # 0–1, risk of flow reversal/collapse


@dataclass
class Suggestion:
    node_id: str | None
    edge_id: str | None
    severity: str   # low / medium / high
    text: str
    action: str     # async / loop / depth / burst / flow / refactor


@dataclass
class AnalysisResult:
    future_distortions: list[FutureDistortion] = field(default_factory=list)
    future_loads: list[FutureLoad] = field(default_factory=list)
    future_flows: list[FutureFlow] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    stability_score: float = 1.0   # 0 = chaos, 1 = stable
    hotspot_count: int = 0


# ── Analyzer ─────────────────────────────────────────────────────────────────

class DOAnalyzer:
    """
    Reads DO Core state and predicts future structural health.
    Pure heuristic — no external ML libs required.
    """

    def analyze(self, kernel: "DOKernel") -> AnalysisResult:
        dm = kernel.distortion
        structure = kernel.structure
        causal = kernel.causal

        if not dm or not structure.nodes:
            return AnalysisResult()

        # Global distortion trend from timeline
        global_trend = self._global_trend(kernel)

        # Per-node cycle membership
        cycle_nodes: set[str] = set()
        for cycle in causal.cycles:
            cycle_nodes.update(cycle)

        # ── Future Distortions ───────────────────────────────────────────────
        future_distortions: list[FutureDistortion] = []
        for nid, ds in dm.node_scores.items():
            node = structure.nodes.get(nid)
            factor = self._node_trend_factor(node, nid in cycle_nodes)
            trend = global_trend * factor
            predicted = min(1.0, ds.total + trend * 4)
            future_distortions.append(FutureDistortion(
                node_id=nid,
                current=ds.total,
                predicted=predicted,
                trend=trend,
                hotspot=predicted > 0.6,
            ))

        # ── Future Loads ─────────────────────────────────────────────────────
        future_loads: list[FutureLoad] = []
        for nid, node in structure.nodes.items():
            spike_prob = self._spike_probability(node, dm)
            pred_ms = node.avg_ms * (1.0 + spike_prob * 0.6)
            future_loads.append(FutureLoad(
                node_id=nid,
                current_ms=node.avg_ms,
                predicted_ms=pred_ms,
                spike_prob=spike_prob,
            ))

        # ── Future Flows ─────────────────────────────────────────────────────
        future_flows: list[FutureFlow] = []
        for eid, edge in structure.edges.items():
            dist = dm.edge_flow_distortion.get(eid, 0)
            # High distortion + low flow → risk of reversal/collapse
            direction_risk = dist * max(0, 1.0 - edge.flow_count / 50.0)
            pred_count = int(edge.flow_count * (1.0 + dist * 0.25))
            future_flows.append(FutureFlow(
                edge_id=eid,
                current_count=edge.flow_count,
                predicted_count=pred_count,
                direction_risk=min(1.0, direction_risk),
            ))

        # ── Suggestions ──────────────────────────────────────────────────────
        fd_map = {f.node_id: f for f in future_distortions}
        fl_map = {f.node_id: f for f in future_loads}
        suggestions = self._generate_suggestions(
            structure, dm, fd_map, fl_map, cycle_nodes
        )

        # ── Stability Score ───────────────────────────────────────────────────
        hotspot_count = sum(1 for f in future_distortions if f.hotspot)
        if future_distortions:
            avg_pred = sum(f.predicted for f in future_distortions) / len(future_distortions)
            stability = max(0.0, 1.0 - avg_pred * 1.2)
        else:
            stability = 1.0

        return AnalysisResult(
            future_distortions=future_distortions,
            future_loads=future_loads,
            future_flows=future_flows,
            suggestions=suggestions,
            stability_score=round(stability, 3),
            hotspot_count=hotspot_count,
        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _global_trend(self, kernel: "DOKernel") -> float:
        dist_log = kernel.timeline.distortion_log()
        if len(dist_log) < 2:
            # No history yet: use current distortion as baseline trend signal
            dm = kernel.distortion
            if dm:
                return dm.global_score.total * 0.015
            return 0.01
        recent = dist_log[-6:]
        deltas = [recent[i + 1][1] - recent[i][1] for i in range(len(recent) - 1)]
        avg = sum(deltas) / len(deltas)
        # Clamp: even stable systems have small positive drift
        return max(0.005, avg)

    def _node_trend_factor(self, node, in_cycle: bool) -> float:
        if not node:
            return 1.0
        factor = 1.0
        if node.async_rate > 0.6:
            factor *= 1.4
        if node.burst_count > 6:
            factor *= 1.3
        if node.avg_ms > 60:
            factor *= 1.5
        if in_cycle:
            factor *= 1.6
        return factor

    def _spike_probability(self, node, dm) -> float:
        prob = 0.0
        if node.avg_ms > 80:
            prob += 0.45
        elif node.avg_ms > 40:
            prob += 0.25
        if node.burst_count > 8:
            prob += 0.30
        if dm and node.node_id in dm.node_scores:
            prob += dm.node_scores[node.node_id].total * 0.30
        return min(1.0, prob)

    def _generate_suggestions(
        self, structure, dm, fd_map, fl_map, cycle_nodes
    ) -> list[Suggestion]:
        suggestions: list[Suggestion] = []
        seen_cycles: set[frozenset] = set()

        for nid, node in structure.nodes.items():
            fd = fd_map.get(nid)
            fl = fl_map.get(nid)

            # Async separation for heavy nodes
            if fl and fl.spike_prob > 0.45 and node.avg_ms > 20:
                sev = "high" if fl.spike_prob > 0.7 else "medium"
                suggestions.append(Suggestion(
                    node_id=nid, edge_id=None, severity=sev,
                    text=(f"{node.label or nid} の処理時間が増加傾向 "
                          f"（{node.avg_ms:.0f}ms → 推定 {fl.predicted_ms:.0f}ms）。"
                          f"非同期分離を検討。"),
                    action="async",
                ))

            # Cycle + worsening distortion
            if nid in cycle_nodes and fd and fd.predicted > 0.45:
                # Deduplicate cycle suggestions per cycle
                cy_key = frozenset(c for cycle in structure.nodes if True for c in [nid])
                if cy_key not in seen_cycles:
                    seen_cycles.add(cy_key)
                    suggestions.append(Suggestion(
                        node_id=nid, edge_id=None, severity="high",
                        text=(f"{node.label or nid} が循環依存に含まれ、"
                              f"歪みが悪化する可能性（予測: {fd.predicted:.2f}）。"
                              f"ループ分離を推奨。"),
                        action="loop",
                    ))

            # Deep node distortion
            if fd and node.depth >= 3 and fd.predicted > 0.35:
                suggestions.append(Suggestion(
                    node_id=nid, edge_id=None, severity="medium",
                    text=(f"{node.label or nid} の依存深度が高い（depth={node.depth}）。"
                          f"依存チェーンの短縮で安定性が向上。"),
                    action="depth",
                ))

            # Burst pressure
            if node.burst_count > 8 and fd and fd.predicted > 0.35:
                suggestions.append(Suggestion(
                    node_id=nid, edge_id=None, severity="medium",
                    text=(f"{node.label or nid} のバースト密度が高い"
                          f"（{node.burst_count} 回）。レート制限を検討。"),
                    action="burst",
                ))

        # Flow saturation
        for eid, edge in structure.edges.items():
            if edge.flow_count > 80:
                src = structure.nodes.get(edge.source_id)
                tgt = structure.nodes.get(edge.target_id)
                src_l = (src.label if src else edge.source_id) or edge.source_id
                tgt_l = (tgt.label if tgt else edge.target_id) or edge.target_id
                suggestions.append(Suggestion(
                    node_id=None, edge_id=eid, severity="low",
                    text=(f"{src_l} → {tgt_l} の流量が飽和"
                          f"（{edge.flow_count}）。負荷分散を検討。"),
                    action="flow",
                ))

        # Sort by severity and limit
        order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: order.get(s.severity, 3))
        return suggestions[:8]
