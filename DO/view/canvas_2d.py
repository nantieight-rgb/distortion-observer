"""
DO View — 2D CausalChainView
Reads the causal graph and renders nodes/edges on a tkinter Canvas.
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING
from .colors import (BG, FG, FG_DIM, BORDER, NODE_DEFAULT, NODE_SELECTED,
                     EDGE_DEFAULT, CYAN, distortion_color, health_color, alpha_hex)

if TYPE_CHECKING:
    from ..core.kernel import DOKernel
    from .flow_layer import FlowState


NODE_R = 26
FONT_LABEL = ("Segoe UI", 8)
FONT_SCORE = ("Segoe UI", 7)


class CausalChainView(tk.Canvas):
    def __init__(self, parent, kernel: "DOKernel", flow_state: "FlowState", **kwargs):
        super().__init__(parent, bg=BG, highlightthickness=0, **kwargs)
        self._kernel = kernel
        self._flow_state = flow_state
        self._mode = "Read"
        self._analysis = None   # AnalysisResult | None
        self._selected: str | None = None
        self._drag_origin: tuple[int, int] | None = None
        self._offset = [0, 0]
        self._zoom = 1.0
        self._node_items: dict[str, int] = {}

        self.bind("<ButtonPress-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonPress-2>", self._on_pan_start)
        self.bind("<B2-Motion>", self._on_pan)
        self.bind("<MouseWheel>", self._on_zoom)

    def set_mode(self, mode: str):
        self._mode = mode

    def set_analysis(self, result):
        self._analysis = result

    def refresh(self):
        self.delete("all")
        if not self._kernel.causal.layout_2d:
            self._draw_empty()
            return
        self._draw_edges()
        self._draw_flow_dots()
        self._draw_nodes()
        self._draw_distortion_rings()
        if self._mode in ("Analyze", "Predict") and self._analysis:
            self._draw_future_overlays()
        self._draw_label()

    def _world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        sx = x * self._zoom + w / 2 + self._offset[0]
        sy = y * self._zoom + h / 2 + self._offset[1]
        return sx, sy

    def _draw_edges(self):
        structure = self._kernel.structure
        dm = self._kernel.distortion
        layout = self._kernel.causal.layout_2d

        for eid, edge in structure.edges.items():
            if edge.source_id not in layout or edge.target_id not in layout:
                continue
            sx, sy = self._world_to_screen(*layout[edge.source_id])
            tx, ty = self._world_to_screen(*layout[edge.target_id])

            fd = dm.edge_flow_distortion.get(eid, 0) if dm else 0
            color = distortion_color(fd)
            width = max(1, int(edge.flow_count / 20 * self._zoom))

            self.create_line(sx, sy, tx, ty, fill=color,
                             width=width, arrow=tk.LAST,
                             arrowshape=(10, 12, 4))

            # Flow count label
            mx, my = (sx + tx) / 2, (sy + ty) / 2
            self.create_text(mx, my - 8, text=str(edge.flow_count),
                             fill=FG_DIM, font=FONT_SCORE)

    def _draw_nodes(self):
        structure = self._kernel.structure
        dm = self._kernel.distortion
        layout = self._kernel.causal.layout_2d

        for nid, node in structure.nodes.items():
            if nid not in layout:
                continue
            sx, sy = self._world_to_screen(*layout[nid])
            r = NODE_R * self._zoom

            dist = dm.node_scores[nid].total if dm and nid in dm.node_scores else 0
            fill = distortion_color(dist)
            outline = CYAN if nid == self._selected else BORDER
            width = 2 if nid == self._selected else 1

            self.create_oval(sx - r, sy - r, sx + r, sy + r,
                             fill=NODE_DEFAULT, outline=fill, width=2)

            # Health ring
            if dm and nid in dm.node_scores:
                h_score = 1.0 - dist
                arc_extent = h_score * 360
                self.create_arc(sx - r, sy - r, sx + r, sy + r,
                                start=90, extent=-arc_extent,
                                outline=fill, width=2, style=tk.ARC)

            # Label
            label = node.label or nid
            if len(label) > 14:
                label = label[:12] + "…"
            self.create_text(sx, sy - 4, text=label,
                             fill=FG, font=FONT_LABEL, anchor="center")
            self.create_text(sx, sy + 10, text=f"{node.avg_ms:.0f}ms",
                             fill=FG_DIM, font=FONT_SCORE, anchor="center")

            # Store for click detection
            self._node_items[nid] = (sx, sy, r)

    def _draw_flow_dots(self):
        layout = self._kernel.causal.layout_2d
        structure = self._kernel.structure
        agg = self._flow_state.aggregator

        for dot in self._flow_state.dots:
            edge = structure.edges.get(dot.edge_id)
            if not edge:
                continue
            if edge.source_id not in layout or edge.target_id not in layout:
                continue
            sx, sy = self._world_to_screen(*layout[edge.source_id])
            tx, ty = self._world_to_screen(*layout[edge.target_id])
            dx, dy = dot.pos(sx, sy, tx, ty)
            r = max(2, dot.size * self._zoom * 0.5)
            self.create_oval(dx - r, dy - r, dx + r, dy + r,
                             fill=dot.color, outline="")

        # Aggregated streams: bright pulsing dashes
        for eid, edge in structure.edges.items():
            if not agg.should_aggregate(edge.flow_count):
                continue
            if edge.source_id not in layout or edge.target_id not in layout:
                continue
            sx, sy = self._world_to_screen(*layout[edge.source_id])
            tx, ty = self._world_to_screen(*layout[edge.target_id])
            phase = agg._streams.get(eid, 0)
            for i in range(4):
                t = (phase + i / 4) % 1.0
                mx = sx + (tx - sx) * t
                my = sy + (ty - sy) * t
                r = 4 * self._zoom
                self.create_oval(mx - r, my - r, mx + r, my + r,
                                 fill="#44ffcc", outline="")

    def _draw_distortion_rings(self):
        layout = self._kernel.causal.layout_2d
        for ring in self._flow_state.rings:
            if ring.node_id not in layout:
                continue
            sx, sy = self._world_to_screen(*layout[ring.node_id])
            base_r = NODE_R * self._zoom
            expand_r, alpha, color = ring.draw_params(base_r)
            hex_color = alpha_hex(color, alpha)
            self.create_oval(sx - expand_r, sy - expand_r,
                             sx + expand_r, sy + expand_r,
                             outline=hex_color, width=2, fill="")

    def _draw_future_overlays(self):
        """Draw future distortion hotspot halos and ghost flow dots."""
        layout = self._kernel.causal.layout_2d
        r_result = self._analysis

        # Hotspot halos on predicted high-distortion nodes
        fd_map = {f.node_id: f for f in r_result.future_distortions}
        for nid, fd in fd_map.items():
            if not fd.hotspot:
                continue
            if nid not in layout:
                continue
            sx, sy = self._world_to_screen(*layout[nid])
            base_r = NODE_R * self._zoom
            halo_r = base_r + 14 * self._zoom * fd.predicted
            halo_color = alpha_hex("#ff4466", 0.3)
            self.create_oval(sx - halo_r, sy - halo_r,
                             sx + halo_r, sy + halo_r,
                             outline=halo_color, width=3, fill="")
            # Predicted score label
            self.create_text(sx, sy - base_r - 10,
                             text=f"pred:{fd.predicted:.2f}",
                             fill="#ff6688", font=("Segoe UI", 7))

        # Ghost flow dots in Predict mode
        if self._mode == "Predict":
            structure = self._kernel.structure
            for ghost in self._flow_state.ghost_dots:
                edge = structure.edges.get(ghost.edge_id)
                if not edge:
                    continue
                if edge.source_id not in layout or edge.target_id not in layout:
                    continue
                sx, sy = self._world_to_screen(*layout[edge.source_id])
                tx, ty = self._world_to_screen(*layout[edge.target_id])
                dx, dy = ghost.pos(sx, sy, tx, ty)
                r = max(2, ghost.size * self._zoom * 0.5)
                g_color = alpha_hex(ghost.color, 0.4)
                self.create_oval(dx - r, dy - r, dx + r, dy + r,
                                 fill=g_color, outline="")

    def _draw_label(self):
        health = self._kernel.health
        if not health:
            return
        color = {"healthy": "#44ff88", "warning": "#ffcc44", "critical": "#ff4466"}[health.level]
        self.create_text(10, 10, text=f"Health: {health.score:.0f}%  [{health.level}]",
                         fill=color, font=("Segoe UI", 9, "bold"), anchor="nw")
        dist = self._kernel.distortion_total()
        self.create_text(10, 28, text=f"Distortion: {dist:.3f}",
                         fill=FG_DIM, font=("Segoe UI", 8), anchor="nw")

        cycles = len(self._kernel.causal.cycles)
        if cycles:
            self.create_text(10, 44, text=f"⚠ Cycles: {cycles}",
                             fill="#ffcc44", font=("Segoe UI", 8), anchor="nw")

    def _draw_empty(self):
        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        self.create_text(w // 2, h // 2, text="No structure data",
                         fill=FG_DIM, font=("Segoe UI", 12))

    def _on_click(self, event):
        for nid, (sx, sy, r) in self._node_items.items():
            if abs(event.x - sx) < r and abs(event.y - sy) < r:
                self._selected = nid
                self._kernel.selection_bus.select_node(nid)
                self.refresh()
                return
        self._selected = None
        self._kernel.selection_bus.clear()
        self.refresh()

    def _on_drag(self, event):
        if self._drag_origin:
            dx = event.x - self._drag_origin[0]
            dy = event.y - self._drag_origin[1]
            self._offset[0] += dx
            self._offset[1] += dy
        self._drag_origin = (event.x, event.y)
        self.refresh()

    def _on_pan_start(self, event):
        self._drag_origin = (event.x, event.y)

    def _on_pan(self, event):
        self._on_drag(event)

    def _on_zoom(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self._zoom = max(0.3, min(3.0, self._zoom * factor))
        self.refresh()
