"""
DO Boundary — Kernel API
Serializes DO Core state to plain dicts for external consumption.
Read-only. Never modifies kernel state.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.kernel import DOKernel


def graph_dict(kernel: "DOKernel") -> dict:
    s = kernel.structure
    return {
        "nodes": {
            nid: {
                "label": n.label,
                "avg_ms": n.avg_ms,
                "async_rate": n.async_rate,
                "burst_count": n.burst_count,
                "depth": n.depth,
                "subsystem": n.subsystem,
                "energy": n.energy,
                "async_score": n.async_score,
                "burst": n.burst,
            }
            for nid, n in s.nodes.items()
        },
        "edges": {
            eid: {
                "source_id": e.source_id,
                "target_id": e.target_id,
                "flow_count": e.flow_count,
                "async_flag": e.async_flag,
                "weight": e.weight,
            }
            for eid, e in s.edges.items()
        },
        "cycles": [list(c) for c in kernel.causal.cycles],
    }


def distortion_dict(kernel: "DOKernel") -> dict:
    dm = kernel.distortion
    if not dm:
        return {"available": False}
    return {
        "available": True,
        "global": dm.global_score.to_dict(),
        "system": dm.system.to_dict(),
        "nodes": {
            nid: ds.to_dict()
            for nid, ds in dm.node_scores.items()
        },
        "edges": {
            eid: round(v, 4)
            for eid, v in dm.edge_flow_distortion.items()
        },
    }


def health_dict(kernel: "DOKernel") -> dict:
    h = kernel.health
    if not h:
        return {"available": False}
    return {"available": True, **h.to_dict()}


def flow_dict(kernel: "DOKernel") -> dict:
    fm = kernel.flow
    if not fm:
        return {"available": False}
    return {
        "available": True,
        "total_flow": fm.total_flow,
        "avg_pressure": round(fm.avg_pressure, 3),
        "nodes": {
            nid: nf.to_dict()
            for nid, nf in fm.node_flows.items()
        },
        "edges": {
            eid: round(v, 4)
            for eid, v in fm.edge_flows.items()
        },
    }


def status_dict(kernel: "DOKernel") -> dict:
    h = kernel.health
    dm = kernel.distortion
    return {
        "running": True,
        "node_count": len(kernel.structure.nodes),
        "edge_count": len(kernel.structure.edges),
        "health_score": kernel.health_score(),
        "health_level": h.level if h else "unknown",
        "distortion_total": round(kernel.distortion_total(), 4),
        "system_distortion": round(dm.system.score, 4) if dm else 0.0,
        "cycle_count": len(kernel.causal.cycles),
    }
