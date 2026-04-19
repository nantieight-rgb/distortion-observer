"""
DO View — Top Bar
Search / Filter / Mode selector.
"""
from __future__ import annotations
import tkinter as tk
from typing import Callable, TYPE_CHECKING
from .colors import BG, PANEL, FG, FG_DIM, BORDER, CYAN, YELLOW

if TYPE_CHECKING:
    from ..core.kernel import DOKernel

MODE_READ = "Read"
MODE_ANALYZE = "Analyze"
MODE_PREDICT = "Predict"


class TopBar(tk.Frame):
    def __init__(self, parent, kernel: DOKernel,
                 on_mode_change: Callable[[str], None] | None = None, **kwargs):
        super().__init__(parent, bg=PANEL, **kwargs)
        self._kernel = kernel
        self._on_mode = on_mode_change
        self._mode = tk.StringVar(value=MODE_READ)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        self._build()

    def _build(self):
        # Title
        tk.Label(self, text="Distortion Observer",
                 bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=(14, 20))

        # Search
        tk.Label(self, text="Search",
                 bg=PANEL, fg=FG_DIM,
                 font=("Segoe UI", 8)).pack(side="left")
        entry = tk.Entry(self, textvariable=self._search_var,
                         bg="#1a1c28", fg=FG, insertbackground=FG,
                         relief="flat", font=("Segoe UI", 9), width=18)
        entry.pack(side="left", padx=(4, 16), ipady=3)

        # Mode buttons
        for mode in [MODE_READ, MODE_ANALYZE, MODE_PREDICT]:
            tk.Radiobutton(
                self, text=mode, variable=self._mode, value=mode,
                bg=PANEL, fg=FG_DIM, selectcolor=PANEL,
                activebackground=PANEL, activeforeground=CYAN,
                font=("Segoe UI", 9), indicatoron=False,
                relief="flat", padx=10, pady=3,
                command=self._mode_changed,
            ).pack(side="left", padx=2)

        # Health display
        self._health_label = tk.Label(self, text="Health: --",
                                      bg=PANEL, fg=FG_DIM,
                                      font=("Segoe UI", 9, "bold"))
        self._health_label.pack(side="right", padx=14)

        # Distortion
        self._dist_label = tk.Label(self, text="Distortion: --",
                                    bg=PANEL, fg=FG_DIM,
                                    font=("Segoe UI", 8))
        self._dist_label.pack(side="right", padx=8)

    def update_status(self):
        health = self._kernel.health
        if not health:
            return
        color = {"healthy": "#44ff88", "warning": "#ffcc44", "critical": "#ff4466"}[health.level]
        self._health_label.config(text=f"Health: {health.score:.0f}%", fg=color)
        dist = self._kernel.distortion_total()
        self._dist_label.config(text=f"Distortion: {dist:.3f}")

    def _mode_changed(self):
        if self._on_mode:
            self._on_mode(self._mode.get())

    def _on_search(self, *_):
        q = self._search_var.get().strip().lower()
        self._kernel.filter_bus.filter_subsystem(q if q else None)

    @property
    def mode(self) -> str:
        return self._mode.get()
