"""
DO Core — Health Model
Converts DistortionScore into a 0-100 health score with breakdown.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .distortion import DistortionMap, DistortionScore


@dataclass
class HealthBreakdown:
    depth: float = 100.0
    load: float = 100.0
    async_: float = 100.0
    burst: float = 100.0
    loop: float = 100.0
    flow: float = 100.0

    def to_dict(self) -> dict:
        return {
            "depth": round(self.depth, 1),
            "load": round(self.load, 1),
            "async": round(self.async_, 1),
            "burst": round(self.burst, 1),
            "loop": round(self.loop, 1),
            "flow": round(self.flow, 1),
        }


@dataclass
class HealthReport:
    score: float = 100.0          # 0-100
    breakdown: HealthBreakdown = field(default_factory=HealthBreakdown)
    level: str = "healthy"        # healthy / warning / critical
    node_health: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "level": self.level,
            "breakdown": self.breakdown.to_dict(),
            "node_health": {k: round(v, 1) for k, v in self.node_health.items()},
        }


def _score_to_health(distortion: float) -> float:
    return 100.0 * (1.0 - distortion)


def _level(score: float) -> str:
    if score >= 75:
        return "healthy"
    if score >= 40:
        return "warning"
    return "critical"


def compute(dm: DistortionMap) -> HealthReport:
    g = dm.global_score
    breakdown = HealthBreakdown(
        depth=_score_to_health(g.depth),
        load=_score_to_health(g.load),
        async_=_score_to_health(g.async_),
        burst=_score_to_health(g.burst),
        loop=_score_to_health(g.loop),
        flow=_score_to_health(g.flow),
    )
    score = _score_to_health(g.total)
    node_health = {
        nid: _score_to_health(ds.total)
        for nid, ds in dm.node_scores.items()
    }
    return HealthReport(
        score=score,
        breakdown=breakdown,
        level=_level(score),
        node_health=node_health,
    )
