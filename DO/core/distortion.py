"""
DO Core — Distortion Model
6-axis structural distortion calculation. Pure math, no meaning.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import StructureModel
from .causal import CausalGraph

# Baseline constants
DEPTH_BASELINE = 5
DEPTH_SCALE = 10.0
LOAD_BASELINE = 16.0    # ms (one frame at 60fps)
LOAD_SCALE = 100.0
BURST_SCALE = 10.0

# Distortion weights
WEIGHTS = {
    "depth": 0.15,
    "load": 0.25,
    "async": 0.15,
    "burst": 0.15,
    "loop": 0.20,
    "flow": 0.10,
}


@dataclass
class DistortionScore:
    depth: float = 0.0
    load: float = 0.0
    async_: float = 0.0
    burst: float = 0.0
    loop: float = 0.0
    flow: float = 0.0
    total: float = 0.0

    def to_dict(self) -> dict:
        return {
            "depth": round(self.depth, 4),
            "load": round(self.load, 4),
            "async": round(self.async_, 4),
            "burst": round(self.burst, 4),
            "loop": round(self.loop, 4),
            "flow": round(self.flow, 4),
            "total": round(self.total, 4),
        }


@dataclass
class DistortionMap:
    node_scores: dict[str, DistortionScore] = field(default_factory=dict)
    edge_flow_distortion: dict[str, float] = field(default_factory=dict)
    global_score: DistortionScore = field(default_factory=DistortionScore)


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _depth_distortion(depth: int) -> float:
    return _clamp((depth - DEPTH_BASELINE) / DEPTH_SCALE)


def _load_distortion(avg_ms: float) -> float:
    return _clamp((avg_ms - LOAD_BASELINE) / LOAD_SCALE)


def _async_distortion(async_rate: float) -> float:
    return _clamp(async_rate ** 2)


def _burst_distortion(burst_count: int, flow_count: int) -> float:
    return _clamp(burst_count / (flow_count + BURST_SCALE))


def _flow_distortion(flow_in: int, flow_out: int) -> float:
    total = flow_in + flow_out
    if total == 0:
        return 0.0
    return _clamp(abs(flow_in - flow_out) / total)


def _weighted(ds: DistortionScore) -> float:
    return (
        WEIGHTS["depth"] * ds.depth +
        WEIGHTS["load"] * ds.load +
        WEIGHTS["async"] * ds.async_ +
        WEIGHTS["burst"] * ds.burst +
        WEIGHTS["loop"] * ds.loop +
        WEIGHTS["flow"] * ds.flow
    )


def compute(structure: StructureModel, causal: CausalGraph) -> DistortionMap:
    dm = DistortionMap()

    node_count = len(structure.nodes)
    loop_distortion = _clamp(len(causal.cycles) / max(node_count, 1))

    for nid, node in structure.nodes.items():
        in_flow = sum(e.flow_count for e in structure.in_edges(nid))
        out_flow = sum(e.flow_count for e in structure.out_edges(nid))
        total_flow = in_flow + out_flow

        ds = DistortionScore(
            depth=_depth_distortion(node.depth),
            load=_load_distortion(node.avg_ms),
            async_=_async_distortion(node.async_rate),
            burst=_burst_distortion(node.burst_count, total_flow),
            loop=loop_distortion,
            flow=_flow_distortion(in_flow, out_flow),
        )
        ds.total = _weighted(ds)
        dm.node_scores[nid] = ds

    for eid, edge in structure.edges.items():
        src = structure.nodes.get(edge.source_id)
        tgt = structure.nodes.get(edge.target_id)
        if src and tgt:
            in_f = sum(e.flow_count for e in structure.in_edges(edge.target_id))
            out_f = sum(e.flow_count for e in structure.out_edges(edge.source_id))
            dm.edge_flow_distortion[eid] = _flow_distortion(in_f, out_f)

    if dm.node_scores:
        scores = list(dm.node_scores.values())
        dm.global_score = DistortionScore(
            depth=sum(s.depth for s in scores) / len(scores),
            load=sum(s.load for s in scores) / len(scores),
            async_=sum(s.async_ for s in scores) / len(scores),
            burst=sum(s.burst for s in scores) / len(scores),
            loop=loop_distortion,
            flow=sum(s.flow for s in scores) / len(scores),
        )
        dm.global_score.total = _weighted(dm.global_score)

    return dm
