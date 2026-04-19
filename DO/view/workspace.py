"""
DO View — Workspace
Main window. Ties TopBar + 2D/3D views + TimelineBar together.
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING
from .colors import BG, PANEL, BORDER, FG, FG_DIM, CYAN
from .canvas_2d import CausalChainView
from .canvas_3d import FlowView3D
from .top_bar import TopBar
from .timeline_bar import TimelineBar
from .flow_layer import FlowState
from .insight_panel import InsightPanel

if TYPE_CHECKING:
    from ..core.kernel import DOKernel


class DOWorkspace(tk.Tk):
    def __init__(self, kernel: DOKernel):
        super().__init__()
        self._kernel = kernel
        self._flow_state = FlowState(kernel)
        self.title("Distortion Observer")
        self.geometry("1280x800")
        self.configure(bg=BG)
        self.resizable(True, True)
        self._build()
        self._tick()

    def _build(self):
        # Top bar
        self._top = TopBar(self, self._kernel,
                           on_mode_change=self._on_mode)
        self._top.pack(fill="x", side="top", pady=(0, 1))

        # Separator
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Main area: 2D left, 3D center, InsightPanel right (hidden in Read mode)
        self._main = tk.Frame(self, bg=BG)
        self._main.pack(fill="both", expand=True)
        self._main.columnconfigure(0, weight=3)
        self._main.columnconfigure(1, weight=3)
        self._main.columnconfigure(2, weight=2)
        self._main.rowconfigure(0, weight=1)

        # 2D panel
        left = tk.Frame(self._main, bg=PANEL, padx=1, pady=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(6, 3), pady=6)
        tk.Label(left, text="Causal Chain  (2D)",
                 bg=PANEL, fg=FG_DIM,
                 font=("Segoe UI", 8)).pack(anchor="nw", padx=6, pady=(4, 0))
        self._view2d = CausalChainView(left, self._kernel, self._flow_state)
        self._view2d.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        # 3D panel
        right = tk.Frame(self._main, bg=PANEL, padx=1, pady=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(3, 3), pady=6)
        tk.Label(right, text="Flow View  (3D)",
                 bg=PANEL, fg=FG_DIM,
                 font=("Segoe UI", 8)).pack(anchor="nw", padx=6, pady=(4, 0))
        self._view3d = FlowView3D(right, self._kernel, self._flow_state)
        self._view3d.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        # AI Insight Panel (hidden by default)
        self._insight_frame = tk.Frame(self._main, bg=PANEL, padx=1, pady=1)
        self._insight = InsightPanel(self._insight_frame, self._kernel)
        self._insight.pack(fill="both", expand=True, padx=2, pady=2)
        self._insight_visible = False

        # Separator
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Timeline bar
        self._timeline = TimelineBar(self, self._kernel)
        self._timeline.pack(fill="x", side="bottom", padx=6, pady=(2, 6))

        # Detail panel (right click info)
        self._detail = tk.Label(self, text="Click a node to inspect",
                                bg=PANEL, fg=FG_DIM,
                                font=("Segoe UI", 8), anchor="w")
        self._detail.pack(fill="x", side="bottom", padx=6)

        # Subscribe to selection
        self._kernel.selection_bus.subscribe(self._on_selection)

        # Start 3D animation
        self._view3d.start()

    def _tick(self):
        """Refresh every 500ms."""
        self._kernel.tick()
        self._view2d.refresh()
        self._timeline.refresh()
        self._top.update_status()

        # Update Insight Panel in Analyze / Predict mode
        if self._insight_visible:
            self._insight.refresh()
            result = self._insight.get_result()
            if result:
                self._view2d.set_analysis(result)
                self._flow_state.sync_ghost_flow(
                    result.future_flows, result.future_distortions
                )

        self.after(500, self._tick)

    def _on_mode(self, mode: str):
        self._view2d.set_mode(mode)
        self._view3d.set_mode(mode)

        if mode in ("Analyze", "Predict"):
            if not self._insight_visible:
                self._insight_frame.grid(
                    row=0, column=2, sticky="nsew", padx=(3, 6), pady=6
                )
                self._insight_visible = True
        else:
            if self._insight_visible:
                self._insight_frame.grid_forget()
                self._insight_visible = False
                # Clear ghost flow
                self._flow_state.sync_ghost_flow([], [])

    def _on_selection(self, event):
        nid = event.node_id
        if not nid:
            self._detail.config(text="Click a node to inspect")
            return
        node = self._kernel.structure.nodes.get(nid)
        dm = self._kernel.distortion
        if not node or not dm:
            return
        ds = dm.node_scores.get(nid)
        text = (f"  Node: {node.label or nid}  |  "
                f"avg_ms: {node.avg_ms:.1f}  |  "
                f"depth: {node.depth}  |  "
                f"async: {node.async_rate:.2f}  |  "
                f"distortion: {ds.total:.3f}" if ds else "")
        self._detail.config(text=text, fg=CYAN)
