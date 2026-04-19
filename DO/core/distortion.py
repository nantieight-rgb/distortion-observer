"""
DO Core — Distortion Model v2 (Energy Physics)
Distortion = weighted sum of normalized energy deviations.

D(x,t) = w_d·D̃_grad + w_b·D̃_time + w_l·D̃_loop + w_a·D̃_async

All axes derived from a single scalar field E(x,t).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import StructureModel, Node
from .causal import CausalGraph

# ── Normalization baselines (design values) ──────────────────────────────────
D_GRAD_0  = 1.0    # ‖∇E‖ = 1.0 → max gradient distortion
D_TIME_0  = 0.5    # |∂E/∂t| = 0.5 → max burst distortion
D_LOOP_0  = 50.0   # Γloop = 50 flow units → max loop distortion
D_ASYNC_0 = 1.0    # AsyncScore = 1.0 → max async distortion (already 0–1)

# ── Physical weights ──────────────────────────────────────────────────────────
# w_d: sensitivity to energy gradient (steepness of potential well)
# w_b: sensitivity to energy time change (spike / crash speed)
# w_l: sensitivity to closed-loop amplification
# w_a: sensitivity to phase desynchronization
WEIGHTS = {
    "grad":  0.30,
    "time":  0.25,
    "loop":  0.25,
    "async": 0.20,
}


@dataclass
class DistortionScore:
    # v2 axes
    grad:   float = 0.0   # D̃_grad  = ‖∇E‖ / D_GRAD_0
    time_d: float = 0.0   # D̃_time  = |∂E/∂t| / D_TIME_0
    loop:   float = 0.0   # D̃_loop  = |Γ| / D_LOOP_0
    async_: float = 0.0   # D̃_async = AsyncScore / D_ASYNC_0
    total:  float = 0.0

    # legacy aliases (kept for UI / Analyzer compatibility)
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
            "grad":   round(self.grad,   4),
            "time":   round(self.time_d, 4),
            "loop":   round(self.loop,   4),
            "async":  round(self.async_, 4),
            "total":  round(self.total,  4),
            # legacy
            "depth":  round(self.grad,   4),
            "load":   round(self.grad,   4),
            "burst":  round(self.time_d, 4),
            "flow":   round(self.loop,   4),
        }


@dataclass
class DistortionMap:
    node_scores:          dict[str, DistortionScore] = field(default_factory=dict)
    edge_flow_distortion: dict[str, float]           = field(default_factory=dict)
    global_score:         DistortionScore            = field(default_factory=DistortionScore)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _resolve_energy(node: Node) -> float:
    """E(x,t): use provided value or derive from legacy avg_ms."""
    if node.energy > 0.0:
        return node.energy
    # Fallback: normalize avg_ms (16ms baseline → 0, 116ms → 1.0)
    return _clamp((node.avg_ms - 16.0) / 100.0)


def _grad_e(node_id: str, structure: StructureModel,
            energy_map: dict[str, float]) -> float:
    """‖∇E(x)‖ — max energy difference across connected edges."""
    e_self = energy_map.get(node_id, 0.0)
    neighbors = (structure.neighbors(node_id) +
                 [e.source_id for e in structure.in_edges(node_id)])
    if not neighbors:
        return 0.0
    return max(abs(e_self - energy_map.get(n, 0.0)) for n in neighbors)


def _gamma_loop(node_id: str, causal: CausalGraph,
                structure: StructureModel) -> float:
    """Discrete Γloop = Σ w_C · Σ_{e∈C} F_e · l_e for cycles containing node."""
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
        w_c = 1.0 / n          # shorter cycles weighted more
        gamma += w_c * cycle_flow
    return gamma


def _resolve_async(node: Node) -> float:
    """AsyncScore: use provided value or derive from legacy async_rate."""
    if node.async_score > 0.0:
        return node.async_score
    return node.async_rate ** 2   # legacy quadratic mapping


def _weighted(ds: DistortionScore) -> float:
    return (WEIGHTS["grad"]  * ds.grad   +
            WEIGHTS["time"]  * ds.time_d +
            WEIGHTS["loop"]  * ds.loop   +
            WEIGHTS["async"] * ds.async_)


# ── Public API ───────────────────────────────────────────────────────────────

def compute(structure: StructureModel, causal: CausalGraph) -> DistortionMap:
    dm = DistortionMap()

    # Pre-compute energy map
    energy_map: dict[str, float] = {
        nid: _resolve_energy(node)
        for nid, node in structure.nodes.items()
    }

    for nid, node in structure.nodes.items():
        grad   = _clamp(_grad_e(nid, structure, energy_map) / D_GRAD_0)
        time_d = _clamp(_resolve_burst(node) / D_TIME_0)
        loop   = _clamp(_gamma_loop(nid, causal, structure) / D_LOOP_0)
        async_ = _clamp(_resolve_async(node) / D_ASYNC_0)

        ds = DistortionScore(grad=grad, time_d=time_d, loop=loop, async_=async_)
        ds.total = _clamp(_weighted(ds))
        dm.node_scores[nid] = ds

    # Edge distortion = gradient across source→target
    for eid, edge in structure.edges.items():
        e_src = energy_map.get(edge.source_id, 0.0)
        e_tgt = energy_map.get(edge.target_id, 0.0)
        dm.edge_flow_distortion[eid] = _clamp(abs(e_src - e_tgt) / D_GRAD_0)

    # Global score = mean of all node scores
    if dm.node_scores:
        scores = list(dm.node_scores.values())
        n = len(scores)
        dm.global_score = DistortionScore(
            grad   = sum(s.grad   for s in scores) / n,
            time_d = sum(s.time_d for s in scores) / n,
            loop   = sum(s.loop   for s in scores) / n,
            async_ = sum(s.async_ for s in scores) / n,
        )
        dm.global_score.total = _clamp(_weighted(dm.global_score))

    return dm


def _resolve_burst(node: Node) -> float:
    """∂E/∂t: use provided burst or derive from legacy burst_count."""
    if node.burst > 0.0:
        return node.burst
    total_flow = 1  # avoid div by zero
    return _clamp(node.burst_count / (total_flow + 10.0))
