"""
DO Core — Structure Model
The lowest layer. Defines what exists: nodes and edges.
No UI, no AI, no meaning.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class Node:
    node_id: str
    label: str = ""
    avg_ms: float = 0.0       # average processing time (ms)
    async_rate: float = 0.0   # 0.0 ~ 1.0
    burst_count: int = 0      # sudden spikes
    depth: int = 0            # call stack depth
    subsystem: str = "default"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "avg_ms": self.avg_ms,
            "async_rate": self.async_rate,
            "burst_count": self.burst_count,
            "depth": self.depth,
            "subsystem": self.subsystem,
            "timestamp": self.timestamp,
        }


@dataclass
class Edge:
    edge_id: str
    source_id: str
    target_id: str
    flow_count: int = 0       # how many times this path was taken
    async_flag: bool = False  # is this an async call?
    weight: float = 1.0       # structural importance

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "flow_count": self.flow_count,
            "async_flag": self.async_flag,
            "weight": self.weight,
        }


@dataclass
class StructureModel:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges[edge.edge_id] = edge

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        dead = [eid for eid, e in self.edges.items()
                if e.source_id == node_id or e.target_id == node_id]
        for eid in dead:
            self.edges.pop(eid)

    def neighbors(self, node_id: str) -> list[str]:
        return [e.target_id for e in self.edges.values()
                if e.source_id == node_id]

    def in_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges.values() if e.target_id == node_id]

    def out_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges.values() if e.source_id == node_id]

    def to_dict(self) -> dict:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": {eid: e.to_dict() for eid, e in self.edges.items()},
        }
