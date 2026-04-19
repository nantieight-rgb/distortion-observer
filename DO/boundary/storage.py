"""
DO Boundary — Storage
Append-only JSON persistence for timeline snapshots and analysis results.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.kernel import DOKernel


class DOStorage:
    def __init__(self, base_dir: str = "do_data"):
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        (self._base / "snapshots").mkdir(exist_ok=True)

    # ── Timeline export ───────────────────────────────────────────────────────

    def save_timeline(self, kernel: "DOKernel", label: str = "") -> str:
        """Save full timeline to JSON. Returns the written file path."""
        tag = label or f"timeline_{int(time.time())}"
        path = self._base / f"{tag}.json"
        kernel.timeline.export(str(path))
        return str(path)

    # ── Snapshot persistence ─────────────────────────────────────────────────

    def save_snapshot(self, kernel: "DOKernel") -> str:
        """Append current kernel state as a named snapshot file."""
        snap = kernel.timeline.latest()
        if not snap:
            return ""
        fname = f"{snap.snapshot_id}.json"
        path = self._base / "snapshots" / fname
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snap.to_dict(), f, ensure_ascii=False, indent=2)
        return str(path)

    def load_snapshot(self, path: str) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def list_snapshots(self) -> list[str]:
        snap_dir = self._base / "snapshots"
        return sorted(str(p) for p in snap_dir.glob("*.json"))

    # ── Full state export ────────────────────────────────────────────────────

    def export_state(self, kernel: "DOKernel") -> str:
        """Export complete current state (graph + distortion + health + flow)."""
        from .kernel_api import graph_dict, distortion_dict, health_dict, flow_dict
        data = {
            "exported_at": time.time(),
            "graph": graph_dict(kernel),
            "distortion": distortion_dict(kernel),
            "health": health_dict(kernel),
            "flow": flow_dict(kernel),
        }
        path = self._base / f"state_{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(path)

    # ── Predictions export ───────────────────────────────────────────────────

    def export_predictions(self, kernel: "DOKernel") -> str:
        from .analyzer_api import full_predict_dict
        data = {
            "predicted_at": time.time(),
            "predictions": full_predict_dict(kernel),
        }
        path = self._base / f"predict_{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(path)
