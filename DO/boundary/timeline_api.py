"""
DO Boundary — Timeline API
Exposes past snapshots, diffs, and trend logs.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.kernel import DOKernel


def snapshots_dict(kernel: "DOKernel", n: int = 10) -> dict:
    snaps = kernel.timeline.history(n)
    return {
        "count": len(snaps),
        "snapshots": [s.to_dict() for s in snaps],
    }


def diffs_dict(kernel: "DOKernel", n: int = 10) -> dict:
    diffs = kernel.timeline.diffs(n)
    return {
        "count": len(diffs),
        "diffs": [d.to_dict() for d in diffs],
    }


def health_log_dict(kernel: "DOKernel") -> dict:
    log = kernel.timeline.health_log()
    return {
        "count": len(log),
        "entries": [{"timestamp": t, "score": round(s, 2)} for t, s in log],
    }


def distortion_log_dict(kernel: "DOKernel") -> dict:
    log = kernel.timeline.distortion_log()
    return {
        "count": len(log),
        "entries": [{"timestamp": t, "total": round(v, 4)} for t, v in log],
    }
