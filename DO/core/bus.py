"""
DO Core — Bus System
SelectionBus, TimeBus, FilterBus.
Synchronizes DO View / DO Flow / DO Analyzer without coupling them.
"""
from __future__ import annotations
from typing import Callable, Any
from dataclasses import dataclass, field


Handler = Callable[[Any], None]


class _Bus:
    def __init__(self, name: str):
        self.name = name
        self._handlers: list[Handler] = []
        self._last: Any = None

    def subscribe(self, handler: Handler) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: Handler) -> None:
        self._handlers = [h for h in self._handlers if h is not handler]

    def publish(self, event: Any) -> None:
        self._last = event
        for h in self._handlers:
            h(event)

    @property
    def last(self) -> Any:
        return self._last


@dataclass
class SelectionEvent:
    node_id: str | None = None
    edge_id: str | None = None


@dataclass
class TimeEvent:
    snapshot_id: str | None = None
    timestamp: float | None = None
    playing: bool = False


@dataclass
class FilterEvent:
    subsystem: str | None = None      # filter by subsystem
    min_distortion: float = 0.0       # show nodes above this distortion
    show_async_only: bool = False


class SelectionBus(_Bus):
    def __init__(self):
        super().__init__("SelectionBus")

    def select_node(self, node_id: str) -> None:
        self.publish(SelectionEvent(node_id=node_id))

    def select_edge(self, edge_id: str) -> None:
        self.publish(SelectionEvent(edge_id=edge_id))

    def clear(self) -> None:
        self.publish(SelectionEvent())


class TimeBus(_Bus):
    def __init__(self):
        super().__init__("TimeBus")

    def seek(self, snapshot_id: str) -> None:
        self.publish(TimeEvent(snapshot_id=snapshot_id))

    def play(self) -> None:
        self.publish(TimeEvent(playing=True))

    def pause(self) -> None:
        self.publish(TimeEvent(playing=False))


class FilterBus(_Bus):
    def __init__(self):
        super().__init__("FilterBus")

    def filter_subsystem(self, subsystem: str | None) -> None:
        self.publish(FilterEvent(subsystem=subsystem))

    def filter_distortion(self, min_distortion: float) -> None:
        self.publish(FilterEvent(min_distortion=min_distortion))

    def filter_async(self, async_only: bool) -> None:
        self.publish(FilterEvent(show_async_only=async_only))
