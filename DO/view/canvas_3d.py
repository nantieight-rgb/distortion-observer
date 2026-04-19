"""
DO View — 3D FlowView
Perspective projection. Nodes float in depth space.
FlowDots animate along edges as blood flow.
DistortionRings pulse on high-distortion nodes.
"""
from __future__ import annotations
import tkinter as tk
import math
from typing import TYPE_CHECKING
from .colors import BG, FG_DIM, distortion_color, health_color, alpha_hex

if TYPE_CHECKING:
    from ..core.kernel import DOKernel
    from .flow_layer import FlowState


FOV = 600.0
ZDIST = 400.0


class FlowView3D(tk.Canvas):
    def __init__(self, parent, kernel: "DOKernel", flow_state: "FlowState", **kwargs):
        super().__init__(parent, bg=BG, highlightthickness=0, **kwargs)
        self._kernel = kernel
        self._flow_state = flow_state
        self._angle_y = 0.2
        self._angle_x = 0.1
        self._running = False
        self._mode = "Read"  # Read / Analyze / Predict

    def set_mode(self, mode: str):
        self._mode = mode

    def start(self):
        self._running = True
        self._loop()

    def stop(self):
        self._running = False

    def _loop(self):
        if not self._running:
            return
        self._flow_state.tick()
        self.refresh()
        self.after(33, self._loop)  # ~30fps

    def refresh(self):
        self.delete("all")
        layout = self._kernel.causal.layout_2d
        structure = self._kernel.structure
        if not layout:
            self._draw_empty()
            return

        w = self.winfo_width() or 500
        h = self.winfo_height() or 400

        # Build 3D positions: x,y from layout, z from depth
        pos3d: dict[str, tuple[float, float, float]] = {}
        for nid, (lx, ly) in layout.items():
            node = structure.nodes.get(nid)
            z = (node.depth if node else 0) * 60.0
            pos3d[nid] = (lx, ly * 0.6, z)

        def project(x, y, z):
            rx = x * math.cos(self._angle_y) - z * math.sin(self._angle_y)
            rz = x * math.sin(self._angle_y) + z * math.cos(self._angle_y)
            ry = y * math.cos(self._angle_x) - rz * math.sin(self._angle_x)
            rz2 = y * math.sin(self._angle_x) + rz * math.cos(self._angle_x)
            scale = FOV / (FOV + rz2 + ZDIST)
            sx = w / 2 + rx * scale
            sy = h / 2 + ry * scale
            return sx, sy, scale

        dm = self._kernel.distortion

        # Draw edges
        for eid, edge in structure.edges.items():
            if edge.source_id not in pos3d or edge.target_id not in pos3d:
                continue
            sx, sy, ss = project(*pos3d[edge.source_id])
            tx, ty, ts = project(*pos3d[edge.target_id])
            dist = dm.edge_flow_distortion.get(eid, 0) if dm else 0
            color = alpha_hex(distortion_color(dist), 0.4)
            self.create_line(sx, sy, tx, ty, fill=color, width=1)

        # Draw aggregated stream edges
        agg = self._flow_state.aggregator
        for eid, edge in structure.edges.items():
            if not agg.should_aggregate(edge.flow_count):
                continue
            if edge.source_id not in pos3d or edge.target_id not in pos3d:
                continue
            sx, sy, ss = project(*pos3d[edge.source_id])
            tx, ty, ts = project(*pos3d[edge.target_id])
            phase = agg._streams.get(eid, 0)
            # Draw 3 staggered bright lines to simulate stream
            for i in range(3):
                t = (phase + i / 3) % 1.0
                mx = sx + (tx - sx) * t
                my = sy + (ty - sy) * t
                r = 3
                self.create_oval(mx - r, my - r, mx + r, my + r,
                                 fill="#44ffcc", outline="")

        # Draw FlowDots
        for dot in self._flow_state.dots:
            edge = structure.edges.get(dot.edge_id)
            if not edge:
                continue
            if edge.source_id not in pos3d or edge.target_id not in pos3d:
                continue
            sx, sy, ss = project(*pos3d[edge.source_id])
            tx, ty, ts = project(*pos3d[edge.target_id])
            t = dot.t
            dx = sx + (tx - sx) * t
            dy = sy + (ty - sy) * t
            scale = ss + (ts - ss) * t
            r = max(2, int(dot.size * scale))
            self.create_oval(dx - r, dy - r, dx + r, dy + r,
                             fill=dot.color, outline="")

        # Draw Ghost Dots (Predict/Analyze mode only)
        if self._mode in ("Predict", "Analyze"):
            for ghost in self._flow_state.ghost_dots:
                edge = structure.edges.get(ghost.edge_id)
                if not edge:
                    continue
                if edge.source_id not in pos3d or edge.target_id not in pos3d:
                    continue
                sx, sy, ss = project(*pos3d[edge.source_id])
                tx, ty, ts = project(*pos3d[edge.target_id])
                t = ghost.t
                dx = sx + (tx - sx) * t
                dy = sy + (ty - sy) * t
                scale = ss + (ts - ss) * t
                r = max(2, int(ghost.size * scale))
                ghost_color = alpha_hex(ghost.color, 0.45)
                self.create_oval(dx - r, dy - r, dx + r, dy + r,
                                 fill=ghost_color, outline="")

        # Draw nodes
        screen_pos: dict[str, tuple[float, float, float]] = {}
        for nid, p3 in pos3d.items():
            sx, sy, scale = project(*p3)
            screen_pos[nid] = (sx, sy, scale)
            node = structure.nodes.get(nid)
            dist = dm.node_scores[nid].total if dm and nid in dm.node_scores else 0
            color = distortion_color(dist)
            r = max(8, int(18 * scale))
            self.create_oval(sx - r, sy - r, sx + r, sy + r,
                             fill="#0d1520", outline=color, width=2)
            label = (node.label or nid)[:10] if node else nid[:10]
            self.create_text(sx, sy, text=label,
                             fill=color, font=("Segoe UI", max(7, int(8 * scale))))

        # Draw DistortionRings
        for ring in self._flow_state.rings:
            if ring.node_id not in screen_pos:
                continue
            sx, sy, scale = screen_pos[ring.node_id]
            base_r = max(8, int(18 * scale))
            expand_r, alpha, color = ring.draw_params(base_r)
            hex_alpha = alpha_hex(color, alpha)
            self.create_oval(sx - expand_r, sy - expand_r,
                             sx + expand_r, sy + expand_r,
                             outline=hex_alpha, width=2, fill="")

        # Slowly rotate
        self._angle_y += 0.003

        # Health indicator
        health = self._kernel.health
        if health:
            color = {"healthy": "#44ff88", "warning": "#ffcc44", "critical": "#ff4466"}[health.level]
            self.create_text(10, 10, text=f"Flow View  ●  {health.score:.0f}%",
                             fill=color, font=("Segoe UI", 9, "bold"), anchor="nw")

    def _draw_empty(self):
        w = self.winfo_width() or 500
        h = self.winfo_height() or 400
        self.create_text(w // 2, h // 2, text="Waiting for flow data…",
                         fill=FG_DIM, font=("Segoe UI", 11))
