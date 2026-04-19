"""
DO View — Timeline Bar
Shows health/distortion history. Scrubbing coming in Phase 4.
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING
from .colors import BG, PANEL, FG, FG_DIM, BORDER, GREEN, YELLOW, RED

if TYPE_CHECKING:
    from ..core.kernel import DOKernel


class TimelineBar(tk.Canvas):
    def __init__(self, parent, kernel: DOKernel, **kwargs):
        super().__init__(parent, bg=PANEL, highlightthickness=0,
                         height=60, **kwargs)
        self._kernel = kernel

    def refresh(self):
        self.delete("all")
        log = self._kernel.timeline.health_log()
        if not log:
            return

        w = self.winfo_width() or 800
        h = self.winfo_height() or 60

        # Draw health curve
        if len(log) < 2:
            return

        min_t = log[0][0]
        max_t = log[-1][0]
        t_range = max(max_t - min_t, 1e-6)

        points = []
        for ts, score in log:
            x = 8 + (ts - min_t) / t_range * (w - 16)
            y = h - 8 - (score / 100.0) * (h - 16)
            points.append((x, y))

        # Gradient line segments
        for i in range(1, len(points)):
            score = log[i][1]
            if score >= 75:
                color = GREEN
            elif score >= 40:
                color = YELLOW
            else:
                color = RED
            x0, y0 = points[i - 1]
            x1, y1 = points[i]
            self.create_line(x0, y0, x1, y1, fill=color, width=2)

        # Current marker
        lx, ly = points[-1]
        score = log[-1][1]
        color = GREEN if score >= 75 else (YELLOW if score >= 40 else RED)
        self.create_oval(lx - 4, ly - 4, lx + 4, ly + 4,
                         fill=color, outline="")

        # Labels
        self.create_text(8, 8, text=f"Health history ({len(log)} snapshots)",
                         fill=FG_DIM, font=("Segoe UI", 7), anchor="nw")
        self.create_text(lx + 6, ly, text=f"{score:.0f}%",
                         fill=color, font=("Segoe UI", 7), anchor="w")
