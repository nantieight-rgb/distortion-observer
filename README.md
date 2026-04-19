# Distortion Observer

**Structural health monitoring OS for software systems.**  
Detects architectural distortions — before they become bugs.

![Health 85%](https://img.shields.io/badge/demo-healthy%2085%25-44ff88?style=flat-square)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)
![Platform Windows](https://img.shields.io/badge/platform-Windows-lightgrey?style=flat-square)
![License MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## What is it?

Distortion Observer (DO) observes the **structure** of your software — not the logs, not the code — and detects where your system is under stress *before* it fails.

It models your system as a living organism:
- **Nodes** = subsystems / events / components
- **Edges** = causal relationships / data flow
- **FlowDots** = blood flow (live throughput)
- **Distortion** = structural stress (6-axis model)

> Most debuggers tell you *what broke*.  
> DO tells you *what's about to break*.

---

## Features

| Phase | Feature |
|-------|---------|
| Core | 6-axis distortion model (Depth / Load / Async / Burst / Loop / Flow) |
| View | 2D Causal Chain View + 3D Flow View (dual panel) |
| Flow | Animated FlowDots + DistortionRings + FlowAggregator |
| Analyzer | AI future prediction — hotspots, load spikes, improvement suggestions |
| Boundary | Local HTTP API (`http://127.0.0.1:7700`) for external tool integration |

---

## Quick Start

### Run from source

```bash
git clone https://github.com/YOUR_USERNAME/distortion-observer
cd distortion-observer
python do_launcher.py
```

Python 3.10+ required. No external dependencies needed for core features.

### Download pre-built exe

→ See [Releases](../../releases) for the latest `DistortionObserver.exe`

---

## HTTP Boundary API

When running, DO exposes a local read-only API:

```
GET http://127.0.0.1:7700/              → endpoint list
GET http://127.0.0.1:7700/do/status     → health & distortion
GET http://127.0.0.1:7700/do/graph      → structure (nodes / edges / cycles)
GET http://127.0.0.1:7700/do/predict/all → AI future predictions
GET http://127.0.0.1:7700/do/stream/poll → live state (poll every N ms)
```

Use `--no-boundary` flag to disable. Use `--port N` to change port.

---

## 6-Axis Distortion Model

```
Depth    — dependency chain too deep
Load     — processing time exceeding baseline
Async    — excessive async entanglement
Burst    — spike density too high
Loop     — circular dependency pressure
Flow     — throughput saturation or reversal risk
```

Each axis scored 0.0–1.0. Combined into a global Distortion score.  
Health = `100 - f(distortion)`, shown as green / yellow / red.

---

## Modes

| Mode | What you see |
|------|-------------|
| **Read** | Current structure, live FlowDots |
| **Analyze** | Distortion heatmap + AI Insight Panel (future hotspots) |
| **Predict** | Ghost Flow (future blood flow) + improvement suggestions |

---

## Architecture

```
DO/
├── core/        — Kernel, Structure, Distortion, Health, Flow, Timeline, Buses
├── view/        — 2D Canvas, 3D Canvas, FlowLayer, InsightPanel, Workspace
└── boundary/    — HTTP Server, Storage, Kernel/Timeline/Analyzer APIs
```

DO Core has zero UI dependencies. It can run headless and be observed via Boundary API.

---

## Use Cases

- **Game engine debugging** — visualize subsystem coupling and load before shipping
- **Microservice health** — map services as nodes, calls as edges
- **Refactoring guidance** — let AI suggest which modules to decouple first
- **Live monitoring** — poll `/do/stream/poll` from any external dashboard

---

## License

MIT — free to use, modify, and distribute.

---

## Author

Toyohiro Arimoto  
Built with [Claude Code](https://claude.ai/code)
