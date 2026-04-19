"""
DO Core — FlowBus
Dedicated event bus for FlowDot updates and Distortion Flow signals.
"""
from __future__ import annotations
from dataclasses import dataclass
from .bus import _Bus


@dataclass
class FlowEvent:
    node_id: str | None = None
    edge_id: str | None = None
    flow_delta: int = 0          # change in flow count
    distortion_spike: bool = False  # sudden distortion increase


@dataclass
class DistortionPulse:
    """Emitted when a node exceeds distortion threshold."""
    node_id: str
    distortion: float
    severity: str  # "low" / "medium" / "high"


class FlowBus(_Bus):
    def __init__(self):
        super().__init__("FlowBus")
        self._pulse_threshold = 0.4

    def emit_flow(self, event: FlowEvent) -> None:
        self.publish(event)

    def emit_pulse(self, pulse: DistortionPulse) -> None:
        self.publish(pulse)

    def check_and_pulse(self, node_id: str, distortion: float) -> None:
        if distortion >= self._pulse_threshold:
            if distortion >= 0.7:
                sev = "high"
            elif distortion >= 0.5:
                sev = "medium"
            else:
                sev = "low"
            self.emit_pulse(DistortionPulse(node_id, distortion, sev))
