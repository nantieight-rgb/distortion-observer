"""
DO Core — Causal Graph
Reconstructs StructureModel as a directed causal graph with metrics.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import StructureModel, Node, Edge


@dataclass
class GraphMetrics:
    node_id: str
    degree: int = 0
    in_degree: int = 0
    out_degree: int = 0
    centrality: float = 0.0
    depth: int = 0


@dataclass
class CausalGraph:
    structure: StructureModel
    metrics: dict[str, GraphMetrics] = field(default_factory=dict)
    layout_2d: dict[str, tuple[float, float]] = field(default_factory=dict)
    cycles: list[list[str]] = field(default_factory=list)

    def compute(self) -> None:
        self._compute_metrics()
        self._compute_layout()
        self._detect_cycles()

    def _compute_metrics(self) -> None:
        self.metrics.clear()
        for nid in self.structure.nodes:
            in_e = self.structure.in_edges(nid)
            out_e = self.structure.out_edges(nid)
            m = GraphMetrics(
                node_id=nid,
                in_degree=len(in_e),
                out_degree=len(out_e),
                degree=len(in_e) + len(out_e),
                depth=self.structure.nodes[nid].depth,
            )
            self.metrics[nid] = m

        # Simple centrality: degree / max_degree
        max_deg = max((m.degree for m in self.metrics.values()), default=1)
        for m in self.metrics.values():
            m.centrality = m.degree / max_deg if max_deg > 0 else 0.0

    def _compute_layout(self) -> None:
        """Simple hierarchical layout by depth."""
        self.layout_2d.clear()
        depth_groups: dict[int, list[str]] = {}
        for nid, node in self.structure.nodes.items():
            d = node.depth
            depth_groups.setdefault(d, []).append(nid)

        for depth, nids in depth_groups.items():
            for i, nid in enumerate(nids):
                x = depth * 120.0
                y = i * 80.0 - (len(nids) - 1) * 40.0
                self.layout_2d[nid] = (x, y)

    def _detect_cycles(self) -> None:
        """DFS-based cycle detection."""
        self.cycles.clear()
        visited: set[str] = set()
        path: list[str] = []
        path_set: set[str] = set()

        def dfs(nid: str) -> None:
            visited.add(nid)
            path.append(nid)
            path_set.add(nid)
            for neighbor in self.structure.neighbors(nid):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in path_set:
                    # Found cycle
                    idx = path.index(neighbor)
                    self.cycles.append(list(path[idx:]))
            path.pop()
            path_set.discard(nid)

        for nid in self.structure.nodes:
            if nid not in visited:
                dfs(nid)

    def to_dict(self) -> dict:
        return {
            "metrics": {nid: vars(m) for nid, m in self.metrics.items()},
            "layout_2d": {nid: list(pos) for nid, pos in self.layout_2d.items()},
            "cycle_count": len(self.cycles),
        }
