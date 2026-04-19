"""
Distortion Observer — Launcher
Steam entry point. Do not rename this file.
"""
import sys
import os

# Ensure project root is in path (handles both dev and PyInstaller _MEIPASS)
if getattr(sys, "frozen", False):
    base = sys._MEIPASS
else:
    base = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base)

from DO.core import DOKernel, Node, Edge
from DO.view import DOWorkspace


def _load_demo(kernel: DOKernel):
    nodes = [
        Node("GameLoop",      label="GameLoop",       avg_ms=16.0,  depth=0),
        Node("InputManager",  label="InputManager",   avg_ms=2.0,   depth=1),
        Node("PhysicsEngine", label="PhysicsEngine",  avg_ms=8.0,   depth=1, async_rate=0.3),
        Node("Renderer",      label="Renderer",       avg_ms=12.0,  depth=1),
        Node("UIManager",     label="UIManager",      avg_ms=45.0,  depth=2, burst_count=8),
        Node("Inventory",     label="Inventory",      avg_ms=30.0,  depth=3, burst_count=12),
        Node("EventBus",      label="EventBus",       avg_ms=1.0,   depth=2, async_rate=0.9),
        Node("AudioManager",  label="AudioManager",   avg_ms=3.0,   depth=2),
        Node("AIController",  label="AIController",   avg_ms=22.0,  depth=2, async_rate=0.6),
        Node("SaveSystem",    label="SaveSystem",     avg_ms=120.0, depth=3, burst_count=3),
    ]
    edges = [
        Edge("e1",  "GameLoop",     "InputManager",   flow_count=60),
        Edge("e2",  "GameLoop",     "PhysicsEngine",  flow_count=60),
        Edge("e3",  "GameLoop",     "Renderer",       flow_count=60),
        Edge("e4",  "GameLoop",     "UIManager",      flow_count=60),
        Edge("e5",  "GameLoop",     "EventBus",       flow_count=200),
        Edge("e6",  "UIManager",    "Inventory",      flow_count=40),
        Edge("e7",  "EventBus",     "AIController",   flow_count=30),
        Edge("e8",  "EventBus",     "AudioManager",   flow_count=50),
        Edge("e9",  "Inventory",    "EventBus",       flow_count=20),
        Edge("e10", "AIController", "EventBus",       flow_count=15),
        Edge("e11", "PhysicsEngine","EventBus",       flow_count=25),
        Edge("e12", "InputManager", "EventBus",       flow_count=60),
        Edge("e13", "Renderer",     "UIManager",      flow_count=10),
        Edge("e14", "SaveSystem",   "Inventory",      flow_count=5),
        Edge("e15", "EventBus",     "SaveSystem",     flow_count=2),
    ]
    for n in nodes:
        kernel.ingest_node(n)
    for e in edges:
        kernel.ingest_edge(e)


def main():
    no_boundary = "--no-boundary" in sys.argv
    port = 7700
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass

    kernel = DOKernel()
    _load_demo(kernel)
    kernel.tick()

    if not no_boundary:
        try:
            from DO.boundary import DOBoundary
            boundary = DOBoundary(kernel, port=port)
            boundary.start()
        except OSError:
            pass  # port in use — continue without boundary

    app = DOWorkspace(kernel)
    app.mainloop()


if __name__ == "__main__":
    main()
