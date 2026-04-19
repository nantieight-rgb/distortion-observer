"""
DO View — AI Insight Panel (Phase 4)
Shows future distortion hotspots, predicted loads, and suggestions.
Visible in Analyze / Predict modes.
"""
from __future__ import annotations
import tkinter as tk
from typing import TYPE_CHECKING
from .colors import BG, PANEL, FG, FG_DIM, CYAN, BORDER
from ..core.analyzer import DOAnalyzer, AnalysisResult

if TYPE_CHECKING:
    from ..core.kernel import DOKernel


class InsightPanel(tk.Frame):
    def __init__(self, parent, kernel: "DOKernel", **kwargs):
        super().__init__(parent, bg=PANEL, **kwargs)
        self._kernel = kernel
        self._analyzer = DOAnalyzer()
        self._result: AnalysisResult | None = None
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=PANEL)
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(hdr, text="AI Insight", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._stability_label = tk.Label(hdr, text="",
                                          bg=PANEL, fg=FG_DIM,
                                          font=("Segoe UI", 8))
        self._stability_label.pack(side="right")

        # Separator
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=4)

        # Scrollable text area
        body = tk.Frame(self, bg=PANEL)
        body.pack(fill="both", expand=True, padx=2, pady=2)

        sb = tk.Scrollbar(body, bg=PANEL, troughcolor=PANEL)
        sb.pack(side="right", fill="y")

        self._text = tk.Text(
            body, bg=PANEL, fg=FG,
            font=("Segoe UI", 8), wrap="word",
            yscrollcommand=sb.set,
            state="disabled", relief="flat",
            highlightthickness=0, padx=6, pady=4,
            cursor="arrow",
        )
        self._text.pack(fill="both", expand=True)
        sb.config(command=self._text.yview)

        # Color tags
        self._text.tag_config("high",    foreground="#ff4466")
        self._text.tag_config("medium",  foreground="#ffcc44")
        self._text.tag_config("low",     foreground="#44ff88")
        self._text.tag_config("section", foreground=CYAN, font=("Segoe UI", 8, "bold"))
        self._text.tag_config("dim",     foreground=FG_DIM)
        self._text.tag_config("normal",  foreground=FG)

    def refresh(self):
        """Run analysis and redraw. Call this when mode = Analyze or Predict."""
        self._result = self._analyzer.analyze(self._kernel)
        self._redraw()

    def get_result(self) -> AnalysisResult | None:
        return self._result

    # ── Internal ─────────────────────────────────────────────────────────────

    def _redraw(self):
        r = self._result
        if not r:
            return

        stab_color = (
            "#44ff88" if r.stability_score > 0.7
            else "#ffcc44" if r.stability_score > 0.4
            else "#ff4466"
        )
        self._stability_label.config(
            text=f"安定性 {r.stability_score * 100:.0f}%",
            fg=stab_color,
        )

        self._text.config(state="normal")
        self._text.delete("1.0", "end")

        # ── Future Distortion Hotspots ────────────────────────────────────
        hotspots = sorted(
            [f for f in r.future_distortions if f.hotspot],
            key=lambda x: -x.predicted,
        )
        if hotspots:
            self._text.insert("end", "▸ 未来の歪みホットスポット\n", "section")
            for h in hotspots[:5]:
                node = self._kernel.structure.nodes.get(h.node_id)
                label = (node.label if node else h.node_id) or h.node_id
                arrow = "↑" if h.trend > 0.005 else "→"
                tag = "high" if h.predicted > 0.7 else "medium"
                self._text.insert(
                    "end",
                    f"  {label}  {h.current:.2f} {arrow} {h.predicted:.2f}\n",
                    tag,
                )
            self._text.insert("end", "\n")

        # ── Future Load Spikes ────────────────────────────────────────────
        spikes = sorted(
            [fl for fl in r.future_loads if fl.spike_prob > 0.45],
            key=lambda x: -x.spike_prob,
        )
        if spikes:
            self._text.insert("end", "▸ 負荷スパーク予測\n", "section")
            for fl in spikes[:4]:
                node = self._kernel.structure.nodes.get(fl.node_id)
                label = (node.label if node else fl.node_id) or fl.node_id
                prob_pct = int(fl.spike_prob * 100)
                tag = "high" if fl.spike_prob > 0.7 else "medium"
                self._text.insert(
                    "end",
                    f"  {label}  {fl.current_ms:.0f}ms → {fl.predicted_ms:.0f}ms"
                    f"  [{prob_pct}%]\n",
                    tag,
                )
            self._text.insert("end", "\n")

        # ── Suggestions ───────────────────────────────────────────────────
        if r.suggestions:
            self._text.insert("end", "▸ 改善提案\n", "section")
            icons = {"high": "⚠", "medium": "◆", "low": "●"}
            for s in r.suggestions:
                icon = icons.get(s.severity, "·")
                self._text.insert("end", f"  {icon} ", s.severity)
                self._text.insert("end", f"{s.text}\n\n", "normal")

        # ── No Issues ─────────────────────────────────────────────────────
        if not hotspots and not spikes and not r.suggestions:
            self._text.insert("end",
                              "  構造は安定しています。\n  予測される問題はありません。",
                              "low")

        self._text.config(state="disabled")
