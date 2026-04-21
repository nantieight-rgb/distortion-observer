# **DO（Distortion Observer）Minimal README（Origin 用）**

DO（Distortion Observer）は、  
**構造の歪みだけを観測する最小 OS**です。

本 README は DO の **Origin（起点）** を示すための  
最小構成の公開記録です。

---

## **1. Minimal Syntax**

```
D-DEPTH: 0.1
D-LOAD: 0.3
D-ASYNC: 0.2
D-BURST: 0.0
D-LOOP: 0.1
D-FLOW: 0.4
```

---

## **2. Origin**

- Qiita Origin 記事  
  → *（https://qiita.com/ToyohroArimoto/items/57aafa7761eb314ff489）*

- Initial Commit Hash  
  ```
  （43816d64257cb7affe522d25b4fa99e7aaa23069）
  ```

---

## **3. Update Policy**

Origin 証明のため、  
**大幅な書き換えは行いません。**

---

## **4. Origin Declaration**

- 初期定義者：有本 豊拡（ToyohiroArimoto）  
- 初期仕様：本 README および初期コミット  

---# Distortion Observer

**DO は、構造上に定義されたエネルギー場 E(x,t) の歪み・流れ・蓄積・位相を観測し、FlowDot として可視化する "構造物理エンジン" です。**

DO は load / flow / burst / loop / depth / async をエネルギー物理として統一的に扱います。  
FlowDot はエネルギー場の状態（量・勾配・流動・位相・閉路・変化率）を 2D/3D にリアルタイム可視化する HUD です。  
Distortion はエネルギーの偏り・変化・閉路・位相ズレを統合した構造歪みの指標です。

![v1.0.0](https://img.shields.io/badge/stable-v1.0.0-44ff88?style=flat-square)
![v2 in progress](https://img.shields.io/badge/v2-energy%20model%20in%20progress-ffcc44?style=flat-square)
![Health 85%](https://img.shields.io/badge/demo-healthy%2085%25-44ff88?style=flat-square)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)
![Platform Windows](https://img.shields.io/badge/platform-Windows-lightgrey?style=flat-square)
![License MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## Energy Model

DO の全概念は、たった一つのエネルギー場から導出される。

```
E(x,t)   — スカラー場（構造上の位置 x、時間 t）
```

| 概念 | 物理定義 | 意味 |
|------|---------|------|
| load  | `E(x,t)` | エネルギー量（ポテンシャル） |
| depth | `∇E(x,t)` | ポテンシャル勾配 |
| flow  | `F = −k∇E` | エネルギーの移動状態 |
| burst | `∂E/∂t` | エネルギーの時間微分 |
| loop  | `∮F·dl` | エネルギー閉路 |
| async | `\|ϕᵢ − ϕⱼ\|` | 非同期による位相ズレ |

**Distortion（歪み）:**

```
D(x,t) = w_d‖∇E‖ + w_b|∂E/∂t| + w_l|Γloop| + w_a·AsyncScore
```

---

## FlowDot = 構造物理 HUD

FlowDot は UI ではなく、エネルギー場をリアルタイムに可視化する HUD。

| 視覚要素 | 物理量 |
|---------|--------|
| サイズ | `E` — ポテンシャル量 |
| 色 | `‖∇E‖` — 勾配歪み |
| 速度 | `‖F‖` — 流れの強さ |
| 揺らぎ | `async` — 位相歪み |
| 脈動 | `\|∂E/∂t\|` — 時間歪み |
| 軌道歪み | `Γloop` — 閉路歪み |
| 光度 | `D` — 歪み総量 |

---

## Quick Start

### Run from source

```bash
git clone https://github.com/nantieight-rgb/distortion-observer
cd distortion-observer
python do_launcher.py
```

Python 3.10+ required. No external dependencies.

### Download pre-built exe

→ [Releases](../../releases) から `DistortionObserver-v1.0.0-windows.zip` をダウンロード  
→ 解凍して `DistortionObserver.exe` を実行

---

## Modes

| Mode | 表示内容 |
|------|---------|
| **Read** | 現在のエネルギー場・FlowDot |
| **Analyze** | 歪みヒートマップ + AI Insight Panel |
| **Predict** | Ghost Flow（未来血流）+ 改善提案 |

---

## HTTP Boundary API

起動中、DO はローカル HTTP API を公開する（読み取り専用）:

```
GET  http://127.0.0.1:7700/              — エンドポイント一覧
GET  http://127.0.0.1:7700/do/status     — 健康・歪み状態
GET  http://127.0.0.1:7700/do/graph      — 構造（ノード・エッジ・サイクル）
GET  http://127.0.0.1:7700/do/predict/all — AI 未来予測
GET  http://127.0.0.1:7700/do/stream/poll — ライブ状態（ポーリング）

POST http://127.0.0.1:7700/do/ingest/node  — ノード追加/更新
POST http://127.0.0.1:7700/do/ingest/edge  — エッジ追加/更新
POST http://127.0.0.1:7700/do/ingest/clear — 構造リセット
POST http://127.0.0.1:7700/do/ingest/tick  — 強制再計算
```

`--no-boundary` で無効化、`--port N` でポート変更。

---

## Use Cases

構造（ノードとエッジ）を持つものなら何でも観測できる。

- ゲームエンジンのサブシステム依存
- マイクロサービス間の API 呼び出し
- OS プロセス・サービスの依存グラフ
- React コンポーネントツリー
- CI/CD パイプライン
- 医療センサーの臓器間依存
- 地震断層の応力伝播

---

## Architecture

```
DO/
├── core/      — Kernel, Energy Model, Distortion, Health, Timeline, Buses
├── view/      — 2D Canvas, 3D Canvas, FlowLayer (HUD), InsightPanel
└── boundary/  — HTTP Server, Ingest API, Storage, Analyzer API
```

DO Core はゼロ UI 依存。Boundary API 経由で外部ツールから観測可能。

---

## License

MIT

---

## Author

Toyohiro Arimoto  
Built with [Claude Code](https://claude.ai/code) & Copilot
