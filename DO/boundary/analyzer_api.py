"""
DO Boundary — Analyzer API
Exposes DO Analyzer future predictions as serializable dicts.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..core.analyzer import DOAnalyzer, AnalysisResult

if TYPE_CHECKING:
    from ..core.kernel import DOKernel

_analyzer = DOAnalyzer()


def _result(kernel: "DOKernel") -> AnalysisResult:
    return _analyzer.analyze(kernel)


def predict_distortion_dict(kernel: "DOKernel") -> dict:
    r = _result(kernel)
    return {
        "stability_score": r.stability_score,
        "hotspot_count": r.hotspot_count,
        "future_distortions": [
            {
                "node_id": f.node_id,
                "current": round(f.current, 4),
                "predicted": round(f.predicted, 4),
                "trend": round(f.trend, 5),
                "hotspot": f.hotspot,
            }
            for f in r.future_distortions
        ],
    }


def predict_load_dict(kernel: "DOKernel") -> dict:
    r = _result(kernel)
    return {
        "future_loads": [
            {
                "node_id": f.node_id,
                "current_ms": round(f.current_ms, 2),
                "predicted_ms": round(f.predicted_ms, 2),
                "spike_prob": round(f.spike_prob, 3),
            }
            for f in r.future_loads
        ],
    }


def predict_flow_dict(kernel: "DOKernel") -> dict:
    r = _result(kernel)
    return {
        "future_flows": [
            {
                "edge_id": f.edge_id,
                "current_count": f.current_count,
                "predicted_count": f.predicted_count,
                "direction_risk": round(f.direction_risk, 3),
            }
            for f in r.future_flows
        ],
    }


def predict_suggestions_dict(kernel: "DOKernel") -> dict:
    r = _result(kernel)
    return {
        "count": len(r.suggestions),
        "suggestions": [
            {
                "node_id": s.node_id,
                "edge_id": s.edge_id,
                "severity": s.severity,
                "action": s.action,
                "text": s.text,
            }
            for s in r.suggestions
        ],
    }


def full_predict_dict(kernel: "DOKernel") -> dict:
    r = _result(kernel)
    return {
        "stability_score": r.stability_score,
        "hotspot_count": r.hotspot_count,
        "future_distortions": [
            {"node_id": f.node_id, "current": round(f.current, 4),
             "predicted": round(f.predicted, 4), "hotspot": f.hotspot}
            for f in r.future_distortions
        ],
        "future_loads": [
            {"node_id": f.node_id, "current_ms": round(f.current_ms, 2),
             "predicted_ms": round(f.predicted_ms, 2), "spike_prob": round(f.spike_prob, 3)}
            for f in r.future_loads
        ],
        "future_flows": [
            {"edge_id": f.edge_id, "current_count": f.current_count,
             "predicted_count": f.predicted_count, "direction_risk": round(f.direction_risk, 3)}
            for f in r.future_flows
        ],
        "suggestions": [
            {"node_id": s.node_id, "edge_id": s.edge_id,
             "severity": s.severity, "action": s.action, "text": s.text}
            for s in r.suggestions
        ],
    }
