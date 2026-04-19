"""
DO Core — Kernel
Single Source of Truth. Ties all Core models together.
"""
from __future__ import annotations
from .models import StructureModel, Node, Edge
from .causal import CausalGraph
from .distortion import DistortionMap, compute as compute_distortion
from .health import HealthReport, compute as compute_health
from .flow import FlowModel, compute as compute_flow
from .timeline import Timeline, Snapshot
from .bus import SelectionBus, TimeBus, FilterBus
from .flow_bus import FlowBus


class DOKernel:
    def __init__(self):
        self.structure = StructureModel()
        self.causal = CausalGraph(self.structure)
        self.timeline = Timeline()

        self.selection_bus = SelectionBus()
        self.time_bus = TimeBus()
        self.filter_bus = FilterBus()
        self.flow_bus = FlowBus()

        self._distortion: DistortionMap | None = None
        self._health: HealthReport | None = None
        self._flow: FlowModel | None = None

    # ------------------------------------------------------------------
    # Structure mutation
    # ------------------------------------------------------------------

    def ingest_node(self, node: Node) -> None:
        self.structure.add_node(node)

    def ingest_edge(self, edge: Edge) -> None:
        self.structure.add_edge(edge)

    def remove_node(self, node_id: str) -> None:
        self.structure.remove_node(node_id)

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def tick(self) -> Snapshot:
        """Recompute all models and record a timeline snapshot."""
        self.causal.compute()

        # Flow first — distortion uses flow for propagated layer
        self._flow = compute_flow(self.structure)

        # Pass prev distortion for dynamics (V) calculation
        prev_dm = self._distortion
        self._distortion = compute_distortion(
            self.structure, self.causal, self._flow, prev_dm
        )
        self._health = compute_health(self._distortion)

        # Emit distortion pulses for high-distortion nodes
        if self._distortion:
            for nid, ds in self._distortion.node_scores.items():
                self.flow_bus.check_and_pulse(nid, ds.total)

        snap = self.timeline.record(
            self.structure, self._distortion, self._health, self._flow
        )
        return snap

    # ------------------------------------------------------------------
    # Read access
    # ------------------------------------------------------------------

    @property
    def distortion(self) -> DistortionMap | None:
        return self._distortion

    @property
    def health(self) -> HealthReport | None:
        return self._health

    @property
    def flow(self) -> FlowModel | None:
        return self._flow

    def snapshot(self) -> dict:
        latest = self.timeline.latest()
        return latest.to_dict() if latest else {}

    def health_score(self) -> float:
        return self._health.score if self._health else 100.0

    def distortion_total(self) -> float:
        if self._distortion:
            return self._distortion.global_score.total
        return 0.0
