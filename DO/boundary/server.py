"""
DO Boundary — HTTP Server
Serves DO Core state over localhost HTTP.
Read-only. Runs in a daemon thread alongside the tkinter UI.

Endpoints:
  GET  /do/status
  GET  /do/graph
  GET  /do/distortion
  GET  /do/health
  GET  /do/flow
  GET  /do/stream/poll          ← latest state for polling clients
  GET  /do/timeline/snapshots   ?n=10
  GET  /do/timeline/diffs       ?n=10
  GET  /do/timeline/health
  GET  /do/timeline/distortion
  GET  /do/predict/distortion
  GET  /do/predict/load
  GET  /do/predict/flow
  GET  /do/predict/suggestions
  GET  /do/predict/all
  POST /do/storage/save         body: {"label":"...", "type":"state|timeline|snapshot"}
"""
from __future__ import annotations
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from typing import TYPE_CHECKING

from .kernel_api import (graph_dict, distortion_dict, health_dict,
                         flow_dict, status_dict)
from .timeline_api import (snapshots_dict, diffs_dict,
                            health_log_dict, distortion_log_dict)
from .analyzer_api import (predict_distortion_dict, predict_load_dict,
                            predict_flow_dict, predict_suggestions_dict,
                            full_predict_dict)
from .storage import DOStorage

if TYPE_CHECKING:
    from ..core.kernel import DOKernel

DEFAULT_PORT = 7700


def _make_handler(kernel: "DOKernel", storage: DOStorage):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # silence default access log

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)

            route_map = {
                "/":                        lambda: {
                    "name": "Distortion Observer — Boundary API",
                    "version": "1.0",
                    "endpoints": [
                        "GET /do/status",
                        "GET /do/graph",
                        "GET /do/distortion",
                        "GET /do/health",
                        "GET /do/flow",
                        "GET /do/stream/poll",
                        "GET /do/timeline/snapshots?n=10",
                        "GET /do/timeline/diffs?n=10",
                        "GET /do/timeline/health",
                        "GET /do/timeline/distortion",
                        "GET /do/predict/distortion",
                        "GET /do/predict/load",
                        "GET /do/predict/flow",
                        "GET /do/predict/suggestions",
                        "GET /do/predict/all",
                        "POST /do/storage/save  body:{label,type}",
                    ],
                },
                "/do/status":               lambda: status_dict(kernel),
                "/do/graph":                lambda: graph_dict(kernel),
                "/do/distortion":           lambda: distortion_dict(kernel),
                "/do/health":               lambda: health_dict(kernel),
                "/do/flow":                 lambda: flow_dict(kernel),
                "/do/stream/poll":          lambda: {
                    **status_dict(kernel),
                    "distortion": distortion_dict(kernel),
                    "flow": flow_dict(kernel),
                },
                "/do/timeline/snapshots":   lambda: snapshots_dict(
                    kernel, int(qs.get("n", ["10"])[0])),
                "/do/timeline/diffs":       lambda: diffs_dict(
                    kernel, int(qs.get("n", ["10"])[0])),
                "/do/timeline/health":      lambda: health_log_dict(kernel),
                "/do/timeline/distortion":  lambda: distortion_log_dict(kernel),
                "/do/predict/distortion":   lambda: predict_distortion_dict(kernel),
                "/do/predict/load":         lambda: predict_load_dict(kernel),
                "/do/predict/flow":         lambda: predict_flow_dict(kernel),
                "/do/predict/suggestions":  lambda: predict_suggestions_dict(kernel),
                "/do/predict/all":          lambda: full_predict_dict(kernel),
            }

            handler = route_map.get(path)
            if handler:
                try:
                    data = handler()
                    self._send_json(200, data)
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            else:
                self._send_json(404, {"error": "not found", "path": path})

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            length = int(self.headers.get("Content-Length", 0))
            body = {}
            if length:
                try:
                    body = json.loads(self.rfile.read(length))
                except Exception:
                    pass

            if path == "/do/storage/save":
                label = body.get("label", "")
                save_type = body.get("type", "state")
                try:
                    if save_type == "timeline":
                        saved = storage.save_timeline(kernel, label)
                    elif save_type == "snapshot":
                        saved = storage.save_snapshot(kernel)
                    elif save_type == "predictions":
                        saved = storage.export_predictions(kernel)
                    else:
                        saved = storage.export_state(kernel)
                    self._send_json(200, {"saved": saved})
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            else:
                self._send_json(404, {"error": "not found"})

        def _send_json(self, code: int, data: dict):
            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

    return _Handler


class DOBoundary:
    """
    Wraps the HTTP server. Call start() to launch in a background thread.
    """
    def __init__(self, kernel: "DOKernel",
                 port: int = DEFAULT_PORT,
                 storage_dir: str = "do_data"):
        self._kernel = kernel
        self._port = port
        self._storage = DOStorage(storage_dir)
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> int:
        """Start server in daemon thread. Returns the port."""
        handler = _make_handler(self._kernel, self._storage)
        self._server = HTTPServer(("127.0.0.1", self._port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="DOBoundaryServer",
        )
        self._thread.start()
        return self._port

    def stop(self):
        if self._server:
            self._server.shutdown()

    @property
    def storage(self) -> DOStorage:
        return self._storage

    @property
    def port(self) -> int:
        return self._port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._port}"
