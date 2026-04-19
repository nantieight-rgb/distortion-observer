"""
DO View — Flow Layer (Phase 3)
Shared FlowDot logic used by both 2D and 3D renderers.
Includes: FlowDot, DistortionPulse, FlowAggregator.
"""
from __future__ import annotations
import math
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.kernel import DOKernel

MAX_DOTS_PER_EDGE = 6
AGGREGATE_THRESHOLD = 4   # edges above this flow_count get aggregated
MAX_GHOST_PER_EDGE = 3


@dataclass
class FlowDot:
    edge_id: str
    t: float = field(default_factory=lambda: random.random())
    speed: float = 0.12
    color: str = "#44ff88"
    size: float = 3.0
    opacity: float = 1.0

    def step(self, dt: float):
        self.t = (self.t + self.speed * dt) % 1.0

    def pos(self, sx: float, sy: float, tx: float, ty: float) -> tuple[float, float]:
        return sx + (tx - sx) * self.t, sy + (ty - sy) * self.t


@dataclass
class GhostDot:
    """Translucent future FlowDot predicted by DO Analyzer."""
    edge_id: str
    t: float = field(default_factory=lambda: random.random())
    speed: float = 0.14
    color: str = "#ff6688"   # ghostly red-pink
    size: float = 2.5

    def step(self, dt: float):
        self.t = (self.t + self.speed * dt) % 1.0

    def pos(self, sx: float, sy: float, tx: float, ty: float) -> tuple[float, float]:
        return sx + (tx - sx) * self.t, sy + (ty - sy) * self.t


@dataclass
class DistortionRing:
    """Pulsing ring that appears on distorted nodes."""
    node_id: str
    phase: float = 0.0        # 0.0 → 1.0 animation phase
    severity: str = "low"     # low / medium / high
    born: float = field(default_factory=time.time)

    SPEED = {"low": 0.8, "medium": 1.4, "high": 2.2}
    COLOR = {"low": "#ffcc44", "medium": "#ff8844", "high": "#ff4466"}
    MAX_R = {"low": 20, "medium": 30, "high": 42}

    def step(self, dt: float) -> bool:
        """Returns False when animation is done."""
        self.phase += self.SPEED[self.severity] * dt
        return self.phase < 1.0

    def draw_params(self, base_r: float) -> tuple[float, float, str]:
        """Returns (expand_r, alpha, color)."""
        ease = math.sin(self.phase * math.pi)
        expand = self.MAX_R[self.severity] * self.phase
        alpha = 1.0 - self.phase
        return base_r + expand, alpha, self.COLOR[self.severity]


class FlowAggregator:
    """
    When an edge has very high flow, replace individual dots with
    a compressed stream (solid animated gradient line).
    """
    def __init__(self):
        self._streams: dict[str, float] = {}  # edge_id → phase

    def should_aggregate(self, flow_count: int) -> bool:
        return flow_count >= 80

    def step(self, edge_id: str, dt: float) -> float:
        phase = self._streams.get(edge_id, random.random())
        phase = (phase + 0.3 * dt) % 1.0
        self._streams[edge_id] = phase
        return phase


class FlowState:
    """
    Manages all FlowDots, GhostDots, DistortionRings, and Aggregator state
    for one canvas view.
    """
    def __init__(self, kernel: "DOKernel"):
        self._kernel = kernel
        self._dots: list[FlowDot] = []
        self._ghost_dots: list[GhostDot] = []
        self._rings: list[DistortionRing] = []
        self._aggregator = FlowAggregator()
        self._last_tick = time.time()

        # Subscribe to distortion pulses
        kernel.flow_bus.subscribe(self._on_flow_event)

    def _on_flow_event(self, event):
        from ..core.flow_bus import DistortionPulse
        if isinstance(event, DistortionPulse):
            # Spawn a new ring (limit: 3 rings per node)
            existing = sum(1 for r in self._rings if r.node_id == event.node_id)
            if existing < 3:
                self._rings.append(DistortionRing(
                    node_id=event.node_id,
                    severity=event.severity,
                ))

    def tick(self) -> float:
        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        structure = self._kernel.structure
        dm = self._kernel.distortion
        edge_ids = set(structure.edges.keys())

        # Remove stale dots
        self._dots = [d for d in self._dots if d.edge_id in edge_ids]

        # Sync dots to edge flow counts
        from .colors import distortion_color
        for eid, edge in structure.edges.items():
            if self._aggregator.should_aggregate(edge.flow_count):
                # Remove individual dots, aggregator handles it
                self._dots = [d for d in self._dots if d.edge_id != eid]
                continue

            current = [d for d in self._dots if d.edge_id == eid]
            target = min(MAX_DOTS_PER_EDGE, max(1, edge.flow_count // 15))
            while len(current) < target:
                dist = dm.edge_flow_distortion.get(eid, 0) if dm else 0
                color = distortion_color(dist)
                speed = 0.10 + edge.flow_count / 400.0
                size = 2.5 + edge.flow_count / 60.0
                dot = FlowDot(eid, speed=speed, color=color, size=size)
                self._dots.append(dot)
                current.append(dot)

        # Step dots
        for dot in self._dots:
            dot.step(dt)

        # Step ghost dots
        for ghost in self._ghost_dots:
            ghost.step(dt)

        # Step rings, remove dead ones
        self._rings = [r for r in self._rings if r.step(dt)]

        return dt

    def sync_ghost_flow(self, future_flows, future_distortions):
        """
        Update GhostDots from AnalysisResult data.
        Call this from workspace when mode = Analyze/Predict.
        """
        from ..core.analyzer import FutureFlow, FutureDistortion

        structure = self._kernel.structure
        edge_ids = set(structure.edges.keys())

        # Remove ghosts for gone edges
        self._ghost_dots = [g for g in self._ghost_dots if g.edge_id in edge_ids]

        # Build index of high-risk flows
        risk_map: dict[str, float] = {}
        for ff in future_flows:
            if ff.direction_risk > 0.2 or ff.predicted_count > ff.current_count * 1.2:
                risk_map[ff.edge_id] = max(ff.direction_risk, 0.3)

        # Hotspot nodes → color their edges more intensely
        hotspot_nodes: set[str] = set()
        for fd in future_distortions:
            if fd.hotspot:
                hotspot_nodes.add(fd.node_id)

        for eid, edge in structure.edges.items():
            in_hotspot = (edge.source_id in hotspot_nodes or
                          edge.target_id in hotspot_nodes)
            risk = risk_map.get(eid, 0)

            should_ghost = in_hotspot or risk > 0.2
            existing = [g for g in self._ghost_dots if g.edge_id == eid]

            if should_ghost:
                target = MAX_GHOST_PER_EDGE if in_hotspot else 1
                while len(existing) < target:
                    color = "#ff4466" if risk > 0.5 else "#ff8844"
                    speed = 0.08 + risk * 0.05
                    g = GhostDot(eid, speed=speed, color=color)
                    self._ghost_dots.append(g)
                    existing.append(g)
            else:
                # Remove ghosts for non-risk edges
                self._ghost_dots = [g for g in self._ghost_dots
                                    if g.edge_id != eid]

    @property
    def ghost_dots(self) -> list[GhostDot]:
        return self._ghost_dots

    @property
    def dots(self) -> list[FlowDot]:
        return self._dots

    @property
    def rings(self) -> list[DistortionRing]:
        return self._rings

    @property
    def aggregator(self) -> FlowAggregator:
        return self._aggregator
