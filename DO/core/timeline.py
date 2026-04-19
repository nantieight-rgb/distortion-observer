"""
DO Core — Timeline Model
Snapshots and diffs of structural state over time.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import time
import json
from .models import StructureModel
from .distortion import DistortionMap
from .health import HealthReport
from .flow import FlowModel


@dataclass
class Snapshot:
    snapshot_id: str
    timestamp: float
    structure: dict       # StructureModel.to_dict()
    distortion: dict      # DistortionMap global_score
    health: dict          # HealthReport.to_dict()
    flow: dict            # FlowModel.to_dict()

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "structure": self.structure,
            "distortion": self.distortion,
            "health": self.health,
            "flow": self.flow,
        }


@dataclass
class Diff:
    from_id: str
    to_id: str
    timestamp: float
    nodes_added: list[str] = field(default_factory=list)
    nodes_removed: list[str] = field(default_factory=list)
    health_delta: float = 0.0
    distortion_delta: float = 0.0

    def to_dict(self) -> dict:
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "timestamp": self.timestamp,
            "nodes_added": self.nodes_added,
            "nodes_removed": self.nodes_removed,
            "health_delta": round(self.health_delta, 2),
            "distortion_delta": round(self.distortion_delta, 4),
        }


class Timeline:
    def __init__(self, max_snapshots: int = 1000):
        self._snapshots: list[Snapshot] = []
        self._diffs: list[Diff] = []
        self._max = max_snapshots
        self._counter = 0

    def record(
        self,
        structure: StructureModel,
        dm: DistortionMap,
        health: HealthReport,
        flow: FlowModel,
    ) -> Snapshot:
        self._counter += 1
        snap = Snapshot(
            snapshot_id=f"snap_{self._counter:06d}",
            timestamp=time.time(),
            structure=structure.to_dict(),
            distortion=dm.global_score.to_dict(),
            health=health.to_dict(),
            flow=flow.to_dict(),
        )

        if self._snapshots:
            prev = self._snapshots[-1]
            prev_nodes = set(prev.structure["nodes"].keys())
            curr_nodes = set(snap.structure["nodes"].keys())
            diff = Diff(
                from_id=prev.snapshot_id,
                to_id=snap.snapshot_id,
                timestamp=snap.timestamp,
                nodes_added=list(curr_nodes - prev_nodes),
                nodes_removed=list(prev_nodes - curr_nodes),
                health_delta=snap.health["score"] - prev.health["score"],
                distortion_delta=snap.distortion["total"] - prev.distortion["total"],
            )
            self._diffs.append(diff)

        self._snapshots.append(snap)
        if len(self._snapshots) > self._max:
            self._snapshots.pop(0)
            self._diffs.pop(0)

        return snap

    def latest(self) -> Snapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def history(self, n: int = 10) -> list[Snapshot]:
        return self._snapshots[-n:]

    def diffs(self, n: int = 10) -> list[Diff]:
        return self._diffs[-n:]

    def health_log(self) -> list[tuple[float, float]]:
        return [(s.timestamp, s.health["score"]) for s in self._snapshots]

    def distortion_log(self) -> list[tuple[float, float]]:
        return [(s.timestamp, s.distortion["total"]) for s in self._snapshots]

    def export(self, path: str) -> None:
        data = {
            "snapshots": [s.to_dict() for s in self._snapshots],
            "diffs": [d.to_dict() for d in self._diffs],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
