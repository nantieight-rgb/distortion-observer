"""
DO Core — Flow Model
Numeric blood flow data only. No rendering logic.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import StructureModel


@dataclass
class FlowMetrics:
    node_id: str
    flow_count: int = 0
    avg_duration: float = 0.0
    async_rate: float = 0.0
    noise_level: float = 0.0
    pressure: float = 0.0        # relative load vs neighbors

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "flow_count": self.flow_count,
            "avg_duration": round(self.avg_duration, 3),
            "async_rate": round(self.async_rate, 3),
            "noise_level": round(self.noise_level, 3),
            "pressure": round(self.pressure, 3),
        }


@dataclass
class FlowModel:
    node_flows: dict[str, FlowMetrics] = field(default_factory=dict)
    total_flow: int = 0
    avg_pressure: float = 0.0

    def to_dict(self) -> dict:
        return {
            "node_flows": {k: v.to_dict() for k, v in self.node_flows.items()},
            "total_flow": self.total_flow,
            "avg_pressure": round(self.avg_pressure, 3),
        }


def compute(structure: StructureModel) -> FlowModel:
    fm = FlowModel()

    all_flows = []
    for nid, node in structure.nodes.items():
        in_flow = sum(e.flow_count for e in structure.in_edges(nid))
        out_flow = sum(e.flow_count for e in structure.out_edges(nid))
        total = in_flow + out_flow
        all_flows.append(total)

        metrics = FlowMetrics(
            node_id=nid,
            flow_count=total,
            avg_duration=node.avg_ms,
            async_rate=node.async_rate,
            noise_level=node.burst_count / (total + 1),
        )
        fm.node_flows[nid] = metrics

    fm.total_flow = sum(all_flows)
    avg = fm.total_flow / len(all_flows) if all_flows else 0

    for nid, metrics in fm.node_flows.items():
        metrics.pressure = metrics.flow_count / (avg + 1)

    fm.avg_pressure = sum(m.pressure for m in fm.node_flows.values()) / max(len(fm.node_flows), 1)
    return fm
