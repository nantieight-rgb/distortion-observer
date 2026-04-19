"""
DO Core — Flow Model v2.1
F = -k∇E, edge flows, propagation term, phase φ_i, async.
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from .models import StructureModel, Node

K_FLOW   = 0.5   # F = -k∇E
BETA     = 0.6   # propagation attenuation  P_i = Σ β·F_{j→i}
T_REF    = 1.0   # phase reference period (seconds)


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _resolve_energy(node: Node) -> float:
    if node.energy > 0.0:
        return node.energy
    return _clamp((node.avg_ms - 16.0) / 100.0)


@dataclass
class NodeFlow:
    node_id: str
    energy:      float = 0.0   # E(x,t)
    grad_e:      float = 0.0   # ‖∇E‖
    flow_mag:    float = 0.0   # ‖F‖ = k·‖∇E‖
    prop_in:     float = 0.0   # P_i = Σ β·F_{j→i}
    phase:       float = 0.0   # φ_i  (0 ~ 2π)
    async_score: float = 0.0   # phase desync with neighbors (0~1)
    # legacy
    flow_count:  int   = 0
    avg_duration: float = 0.0
    async_rate:  float = 0.0
    noise_level: float = 0.0
    pressure:    float = 0.0

    def to_dict(self) -> dict:
        return {
            "node_id":     self.node_id,
            "energy":      round(self.energy,      4),
            "grad_e":      round(self.grad_e,      4),
            "flow_mag":    round(self.flow_mag,    4),
            "prop_in":     round(self.prop_in,     4),
            "phase":       round(self.phase,       4),
            "async_score": round(self.async_score, 4),
            "flow_count":  self.flow_count,
            "avg_duration": round(self.avg_duration, 3),
            "pressure":    round(self.pressure,    3),
        }


@dataclass
class FlowModel:
    node_flows:  dict[str, NodeFlow] = field(default_factory=dict)
    edge_flows:  dict[str, float]    = field(default_factory=dict)  # F_{i→j}
    total_flow:  int   = 0
    avg_pressure: float = 0.0

    def to_dict(self) -> dict:
        return {
            "node_flows":  {k: v.to_dict() for k, v in self.node_flows.items()},
            "edge_flows":  {k: round(v, 4) for k, v in self.edge_flows.items()},
            "total_flow":  self.total_flow,
            "avg_pressure": round(self.avg_pressure, 3),
        }


def compute(structure: StructureModel) -> FlowModel:
    fm = FlowModel()
    now = time.time()
    nodes = structure.nodes
    edges = structure.edges

    if not nodes:
        return fm

    # ── Step 1: Energy map ────────────────────────────────────────────────────
    energy_map: dict[str, float] = {
        nid: _resolve_energy(n) for nid, n in nodes.items()
    }

    # ── Step 2: ∇E per node — max |E_i - E_j| over all connected nodes ───────
    grad_map: dict[str, float] = {}
    for nid in nodes:
        e_self = energy_map[nid]
        nbrs = (structure.neighbors(nid) +
                [e.source_id for e in structure.in_edges(nid)])
        grad_map[nid] = (
            max(abs(e_self - energy_map.get(nb, 0.0)) for nb in nbrs)
            if nbrs else 0.0
        )

    # ── Step 3: Edge flows  F_{i→j} = max(0, E_i - E_j) * K_FLOW ────────────
    for eid, edge in edges.items():
        e_src = energy_map.get(edge.source_id, 0.0)
        e_tgt = energy_map.get(edge.target_id, 0.0)
        fm.edge_flows[eid] = _clamp(max(0.0, e_src - e_tgt) * K_FLOW)

    # ── Step 4: Propagation term  P_i = Σ_{j→i} β · F_{j→i} ─────────────────
    prop_map: dict[str, float] = {nid: 0.0 for nid in nodes}
    for eid, edge in edges.items():
        tgt = edge.target_id
        prop_map[tgt] = prop_map.get(tgt, 0.0) + BETA * fm.edge_flows[eid]

    # ── Step 5: Phase φ_i = 2π·((t - t_last) / T_ref) mod 2π ───────────────
    phase_map: dict[str, float] = {
        nid: (2 * math.pi * ((now - n.timestamp) / T_REF)) % (2 * math.pi)
        for nid, n in nodes.items()
    }

    # ── Step 6: Async = mean min-angle diff with neighbors (normalized 0~1) ──
    async_map: dict[str, float] = {}
    for nid, node in nodes.items():
        phi_i = phase_map[nid]
        nbrs = (structure.neighbors(nid) +
                [e.source_id for e in structure.in_edges(nid)])
        if nbrs:
            diffs = []
            for nb in nbrs:
                d = abs(phi_i - phase_map.get(nb, 0.0))
                diffs.append(min(d, 2 * math.pi - d))
            phase_async = _clamp(sum(diffs) / (len(diffs) * math.pi))
        else:
            phase_async = 0.0
        # Explicit async_score acts as lower bound (user-provided behavioral desync)
        explicit = node.async_score if node.async_score > 0 else node.async_rate
        async_map[nid] = _clamp(max(phase_async, explicit))

    # ── Step 7: Assemble NodeFlow ─────────────────────────────────────────────
    all_counts: list[int] = []
    for nid, node in nodes.items():
        in_cnt  = sum(e.flow_count for e in structure.in_edges(nid))
        out_cnt = sum(e.flow_count for e in structure.out_edges(nid))
        count   = in_cnt + out_cnt
        all_counts.append(count)

        grad_e = grad_map[nid]
        fm.node_flows[nid] = NodeFlow(
            node_id=nid,
            energy=energy_map[nid],
            grad_e=grad_e,
            flow_mag=_clamp(K_FLOW * grad_e),
            prop_in=_clamp(prop_map.get(nid, 0.0)),
            phase=phase_map[nid],
            async_score=async_map[nid],
            flow_count=count,
            avg_duration=node.avg_ms,
            async_rate=node.async_rate,
            noise_level=node.burst_count / (count + 1),
        )

    fm.total_flow = sum(all_counts)
    avg = fm.total_flow / len(all_counts) if all_counts else 1.0
    for nf in fm.node_flows.values():
        nf.pressure = nf.flow_count / (avg + 1)
    fm.avg_pressure = (
        sum(nf.pressure for nf in fm.node_flows.values()) /
        max(len(fm.node_flows), 1)
    )
    return fm
