"""
DO Core — Distortion Model v2.1 (3-layer Energy Physics)

local      = wd‖∇E‖ + wb|∂E/∂t| + wl|Γ| + wa·async  (exists even at flow=0)
propagated = Σ_{j→i} β·F_{j→i}                        (spreads via flow)
total      = local + propagated
latent     = local · (1 − σ(‖F‖))                     (static danger)

system_distortion = wS·S + wP·P + wV·V
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from .models import StructureModel, Node
from .causal import CausalGraph
from .flow import FlowModel

# ── Normalization baselines ───────────────────────────────────────────────────
D_GRAD_0  = 1.0
D_TIME_0  = 0.5
D_LOOP_0  = 50.0
D_ASYNC_0 = 1.0

# ── Local distortion weights ──────────────────────────────────────────────────
WEIGHTS = {"grad": 0.30, "time": 0.25, "loop": 0.25, "async": 0.20}

# ── System distortion ─────────────────────────────────────────────────────────
W_S, W_P, W_V     = 0.5, 0.3, 0.2
ALPHA1, ALPHA2    = 0.7, 0.3   # strength: max / mean
BETA1, BETA2      = 0.6, 0.4   # dynamics: d/dt max / mean
SPREAD_TAU        = 0.6        # danger threshold for spread fraction


@dataclass
class DistortionScore:
    # local components
    grad:   float = 0.0   # ‖∇E‖ / D_GRAD_0
    time_d: float = 0.0   # |∂E/∂t| / D_TIME_0
    loop:   float = 0.0   # |Γ| / D_LOOP_0
    async_: float = 0.0   # AsyncScore / D_ASYNC_0
    # layers
    local:      float = 0.0   # weighted sum of 4 components
    propagated: float = 0.0   # incoming flow-borne distortion
    total:      float = 0.0   # local + propagated
    latent:     float = 0.0   # local · (1 − σ(‖F‖))

    # legacy aliases
    @property
    def depth(self)  -> float: return self.grad
    @property
    def load(self)   -> float: return self.grad
    @property
    def burst(self)  -> float: return self.time_d
    @property
    def flow(self)   -> float: return self.loop

    def to_dict(self) -> dict:
        return {
            "grad":       round(self.grad,       4),
            "time":       round(self.time_d,     4),
            "loop":       round(self.loop,       4),
            "async":      round(self.async_,     4),
            "local":      round(self.local,      4),
            "propagated": round(self.propagated, 4),
            "total":      round(self.total,      4),
            "latent":     round(self.latent,     4),
            # legacy
            "depth": round(self.grad,   4),
            "load":  round(self.grad,   4),
            "burst": round(self.time_d, 4),
            "flow":  round(self.loop,   4),
        }


@dataclass
class SystemDistortion:
    strength:  float = 0.0   # S = α1·max + α2·mean
    spread:    float = 0.0   # P = fraction of nodes > τ
    dynamics:  float = 0.0   # V = |d/dt(max, mean)|
    score:     float = 0.0   # wS·S + wP·P + wV·V

    def to_dict(self) -> dict:
        return {
            "strength":  round(self.strength,  4),
            "spread":    round(self.spread,    4),
            "dynamics":  round(self.dynamics,  4),
            "score":     round(self.score,     4),
        }


@dataclass
class DistortionMap:
    node_scores:          dict[str, DistortionScore] = field(default_factory=dict)
    edge_flow_distortion: dict[str, float]           = field(default_factory=dict)
    global_score:         DistortionScore            = field(default_factory=DistortionScore)
    system:               SystemDistortion           = field(default_factory=SystemDistortion)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _resolve_energy(node: Node) -> float:
    if node.energy > 0.0:
        return node.energy
    return _clamp((node.avg_ms - 16.0) / 100.0)


def _resolve_burst(node: Node) -> float:
    if node.burst > 0.0:
        return node.burst
    return _clamp(node.burst_count / 11.0)


def _gamma_loop(node_id: str, causal: CausalGraph,
                structure: StructureModel) -> float:
    gamma = 0.0
    for cycle in causal.cycles:
        if node_id not in cycle:
            continue
        cycle_flow = 0.0
        n = len(cycle)
        for i in range(n):
            src, tgt = cycle[i], cycle[(i + 1) % n]
            for edge in structure.edges.values():
                if edge.source_id == src and edge.target_id == tgt:
                    cycle_flow += edge.flow_count * edge.weight
                    break
        gamma += (1.0 / n) * cycle_flow
    return gamma


def _sigmoid(x: float) -> float:
    """σ(x) centered at 0.3 — flow_mag < 0.3 → latent persists."""
    return 1.0 / (1.0 + math.exp(-12.0 * (x - 0.3)))


# ── Public API ────────────────────────────────────────────────────────────────

def compute(structure: StructureModel,
            causal: CausalGraph,
            flow: FlowModel | None = None,
            prev_dm: DistortionMap | None = None) -> DistortionMap:
    dm = DistortionMap()

    energy_map: dict[str, float] = {
        nid: _resolve_energy(n) for nid, n in structure.nodes.items()
    }

    for nid, node in structure.nodes.items():
        nf = flow.node_flows.get(nid) if flow else None

        # ── ∇E ───────────────────────────────────────────────────────────────
        if nf:
            grad_e = nf.grad_e
        else:
            e_self = energy_map[nid]
            nbrs = (structure.neighbors(nid) +
                    [e.source_id for e in structure.in_edges(nid)])
            grad_e = max(
                (abs(e_self - energy_map.get(nb, 0.0)) for nb in nbrs),
                default=0.0,
            )

        # ── local components ──────────────────────────────────────────────────
        grad   = _clamp(grad_e / D_GRAD_0)
        time_d = _clamp(_resolve_burst(node) / D_TIME_0)
        loop   = _clamp(_gamma_loop(nid, causal, structure) / D_LOOP_0)

        if nf:
            async_ = _clamp(nf.async_score / D_ASYNC_0)
        else:
            a = node.async_score if node.async_score > 0 else node.async_rate ** 2
            async_ = _clamp(a / D_ASYNC_0)

        local = _clamp(
            WEIGHTS["grad"]  * grad   +
            WEIGHTS["time"]  * time_d +
            WEIGHTS["loop"]  * loop   +
            WEIGHTS["async"] * async_
        )

        # ── propagated ────────────────────────────────────────────────────────
        propagated = _clamp(nf.prop_in if nf else 0.0)

        # ── total & latent ────────────────────────────────────────────────────
        total  = _clamp(local + propagated)
        f_mag  = nf.flow_mag if nf else 0.0
        latent = _clamp(local * (1.0 - _sigmoid(f_mag)))

        dm.node_scores[nid] = DistortionScore(
            grad=grad, time_d=time_d, loop=loop, async_=async_,
            local=local, propagated=propagated, total=total, latent=latent,
        )

    # ── Edge distortion ───────────────────────────────────────────────────────
    for eid, edge in structure.edges.items():
        if flow:
            dm.edge_flow_distortion[eid] = flow.edge_flows.get(eid, 0.0)
        else:
            e_src = energy_map.get(edge.source_id, 0.0)
            e_tgt = energy_map.get(edge.target_id, 0.0)
            dm.edge_flow_distortion[eid] = _clamp(abs(e_src - e_tgt) / D_GRAD_0)

    # ── Global score = mean of all node scores ────────────────────────────────
    if dm.node_scores:
        scores = list(dm.node_scores.values())
        n = len(scores)
        dm.global_score = DistortionScore(
            grad       = sum(s.grad       for s in scores) / n,
            time_d     = sum(s.time_d     for s in scores) / n,
            loop       = sum(s.loop       for s in scores) / n,
            async_     = sum(s.async_     for s in scores) / n,
            local      = sum(s.local      for s in scores) / n,
            propagated = sum(s.propagated for s in scores) / n,
            total      = sum(s.total      for s in scores) / n,
            latent     = sum(s.latent     for s in scores) / n,
        )

    # ── System Distortion ─────────────────────────────────────────────────────
    if dm.node_scores:
        totals = [s.total for s in dm.node_scores.values()]
        max_t  = max(totals)
        mean_t = sum(totals) / len(totals)

        S = _clamp(ALPHA1 * max_t + ALPHA2 * mean_t)
        P = sum(1 for t in totals if t > SPREAD_TAU) / len(totals)

        V = 0.0
        if prev_dm and prev_dm.node_scores:
            prev = [s.total for s in prev_dm.node_scores.values()]
            if prev:
                pm = max(prev)
                pa = sum(prev) / len(prev)
                V = _clamp(abs(BETA1 * (max_t - pm) + BETA2 * (mean_t - pa)))

        dm.system = SystemDistortion(
            strength=S, spread=P, dynamics=V,
            score=_clamp(W_S * S + W_P * P + W_V * V),
        )

    return dm
