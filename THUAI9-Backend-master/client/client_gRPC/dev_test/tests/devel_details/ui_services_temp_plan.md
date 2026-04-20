# dev_test/ui services 临时规划（服务粒度、依赖关系与读者向说明）

更新时间：2026-04-20

本文件是“规划说明”，用于帮助读者理解当前 dev_test UI 的分层与 `services/` 的项目关系，并为后续重组提供清晰路线。

重要约束（本次任务范围）
- 不做“规划性重构改代码”（只完善规划文档）。
- 允许做稳定性修复（若验证发现明确 bug/导入问题）。

---

## 0) TL;DR（给第一次读的人）

- 现状：`ui/main_ui.py` 已完全薄委托化（所有方法均委托到 `ui/services/**`）。
- `services/**` 内部“互相 import”非常少：当前只存在 2 条显式依赖
  - `services/system_settings/system_settings_window_service.py` → `services/system_settings/system_settings_dirty_service.py`
  - `services/data_loading/game_data_loading_service.py` → `services/data_loading/mode_selection_dialog_service.py`
- 这说明当前依赖方向已经比较健康：大多数 service 只依赖 `components.py` / `logic/**` / `core/**` / `env.py` 等“下游模块”，而不是互相缠绕。

---

## 1) dev_test 项目整体架构（从大到小）

### 1.1 三大块

1) `dev_test/ui/`：Tk UI + services（交互/装配/调度）
- `main_ui.py` 作为“适配器 + 门面”：把 UI 事件转成对 services 的调用。
- `components.py` 放可复用 UI 组件（棋盘、面板、卡片）。

2) `dev_test/logic/`：控制器与流程编排
- `logic/controller.py` 负责：加载数据（mock/runtime）、推进回合、发事件、持有 runtime env。

3) `dev_test/core/`：通用事件与基础设施
- `core/events.py` 定义事件类型（GAME_LOADED/ROUND_STARTED/...）。

此外：`env.py`（后端/规则实现）是 UI 与 controller 的“业务对象模型”来源。

### 1.2 两种运行模式（决定 services 的“副作用方向”）

- `mock`：主要是回放/展示，不改后端 env。
- `runtime_env`：会操作/注入/覆写后端 env（例如 hook、玩法设计、强制 d20 等）。

因此 services 大体分两类：
- **UI 视图类 service**：纯装配/刷新（可在 mock 与 runtime 两边复用）。
- **运行时注入类 service**：只在 runtime_env 模式下有意义，会写入 `env`。

---

## 2) 当前 services 子包“项目关系”（谁负责什么、谁调用谁）

读者快速索引：一般是 `main_ui` 调用 services；services 再调用 `controller/env/components`，并通过 `main_ui` 传入的控件引用更新界面。

### 2.1 services 子包职责图（读者向）

- `services/layout/`
  - 主窗口启动与左右装配（窗口骨架、布局组件放置、事件订阅）。
  - 典型入口：`bootstrap_main_ui()`、`build_left_side()`、`build_right_side()`。

- `services/data_loading/`
  - 模式选择/数据源/数据集选择弹窗 + 加载流程 + 重置流程。
  - 典型入口：`_startup_load_with_source_dialog()` 链路最终落到 `game_data_loading_service`。

- `services/replay/`
  - 回放控制区 UI、播放/暂停/单步、回合跳转/回退，以及回合详情追加。

- `services/board/` + `services/cards/`
  - 纯渲染/刷新：棋盘视图 + 左上卡片/行动状态行。

- `services/actions/`
  - 行动面板渲染、选点/目标选择、提交 move/attack/spell、陷阱/法术相关 UI。

- `services/attribute_settings/`
  - 属性设置窗口（piece/map/action 三页）与派生属性/职业/装备相关计算与应用。

- `services/system_settings/`
  - 系统设置窗口框架、综合设置页、tutorial/dev 文本页、dirty/快照/回滚。

- `services/design/`
  - 玩法设计页（系统设置窗口中的“玩法设计”页）：全局（濒死系统）、属性梯度、法术池。

- `services/runtime/`
  - runtime_env 的 hook 注入、跨局重应用、运行时监控（存活判定/消息 flush/胜负播报）、runtime 初始化输入与先攻捕获。

- `services/dialogs/`
  - 通用弹窗：confirm/notice/initiative/game_over 等。

### 2.2 当前真实依赖（重点：services 内部依赖极少）

当前明确的 service-to-service import 关系只有两条：
- `system_settings_window_service` 依赖 `system_settings_dirty_service`（窗口关闭时 dirty 回滚）。
- `game_data_loading_service` 依赖 `mode_selection_dialog_service`（加载流程需要弹窗结果）。

除此之外：大多数 service 只依赖下游模块（`components`、`logic`、`core`、`env`）以及 Tk。

---

## 3) 依赖方向与“允许/禁止”的 import 规则（建议固化为约定）

### 3.1 推荐的依赖方向

- `main_ui.py` → `services/**`（允许）
- `services/**` → `components.py`（允许）
- `services/**` → `logic/**`、`core/**`、`env.py`（允许）
- `services/**` → `services/**`（尽量少；若必须，优先同子包内，且避免循环）

### 3.2 明确禁止

- `services/**` 禁止 import `main_ui.py`
  - 原因：循环依赖风险 + 单元化拆分困难。
  - 交互方式：继续使用 duck-typing（把 `main_ui` 当作“接口对象”传入）。

### 3.3 经验法则（帮助读者判断该放哪）

- “创建 Tk 控件/布局 grid/pack”：倾向放在 page/window/layout 服务。
- “解析/校验/格式化/映射（纯函数）”：倾向放 shared（后续要建）或就近 utils。
- “会写入 env/controller，或会产生明显副作用”：倾向放 domain/service。

---

## 4) 依赖图（读者向，抽象层级）

下面的图表达的是**大体调用方向**，不是每个函数都连线。

```mermaid
flowchart LR
  UI[main_ui.py\n(薄委托/门面)] --> S[services/**]

  S --> C[logic/controller.py]
  S --> E[env.py / runtime env]
  S --> Comp[components.py]
  C -->|EventBus| UI

  subgraph Services
    L[layout]
    DL[data_loading]
    R[replay]
    B[board]
    K[cards]
    A[actions]
    AS[attribute_settings]
    SS[system_settings]
    D[design]
    RT[runtime]
    DG[dialogs]
  end

  UI --> L
  UI --> DL
  UI --> R
  UI --> B
  UI --> K
  UI --> A
  UI --> AS
  UI --> SS
  UI --> D
  UI --> RT
  UI --> DG

  SS -->|仅两处跨 service 依赖之一| SS2[system_settings_dirty_service]
  DL -->|仅两处跨 service 依赖之一| DL2[mode_selection_dialog_service]
```

---

## 5) 重新定义稳定分层（建议：让“家具摆放”更自然）

建议把 services 在“逻辑层次”上固化为 4 层（这是概念分层，不要求立刻改目录）：

1) bootstrap
- 只做启动装配：创建 controller、root window、事件订阅、after 启动加载。

2) views
- 纯 UI 结构/组件装配（frame、notebook、panel、控件布局）。

3) domain
- 面向“领域功能”的逻辑：数据加载、回放、运行时监控、卡片渲染、属性编辑规则、玩法设计注入。

4) shared
- 通用工具：解析、校验、格式化、简单 mapping。

这套分层的核心价值：
- 读者能快速判断“文件放哪”；
- 防止 page service 里既有 UI 装配又有复杂业务；
- 防止 runtime/domain 逻辑散落在很多 30 行小文件里。

---

## 6) 具体合并/拆分建议（未来做；不改行为）

### A. `layout/` vs `bootstrap`

现状：
- `services/layout/main_ui_bootstrap_service.py` 同时承担：root window 初始化、状态字段初始化、事件订阅。

建议（未来）：
- 抽概念层：把“事件订阅”作为独立模块（bootstrap/event_subscribe），把“窗口/状态初始化”保留在 bootstrap。
- `services/layout/main_layout_service.py` 保持纯布局装配。

迁移顺序（最小风险）：
1) 先抽 event subscribe（只搬订阅行，风险最低）。
2) 再抽 window size/title 等纯 UI 初始化。

### B. `design/` 与 `system_settings/` 的边界

现状：
- `design/*` 的页面实际上挂在“系统设置窗口”下。

建议（未来）：
- 让 `system_settings/` 成为“窗口框架 + 一级页切换”的 view 层。
- 让 `design/` 更像 domain（收集配置、校验、应用到 runtime env）。

### C. `attribute_settings/` 的共享逻辑沉淀

现状：
- piece/map/action 三页存在较多共享的解析/校验/格式化。

建议（未来）：
- 把纯函数抽到 shared（例如 attribute_utils）。
- page service 只做控件装配 + 调 shared/domain。

### D. `runtime/` 文件过大风险（拆分建议）

现状：
- `runtime_monitor_service.py` 包含 near-death 判定、消息 flush、胜负判定、事件回调。

建议（未来）：
- 先拆 near-death 纯逻辑（最低风险），再拆 game_over 与 message_flush。

---

## 7) 命名与文件大小的“临时规则”（便于持续搬家）

- 规则 1：单个 service 文件若 < 50 行且只提供 1-2 个函数，优先合并进同域模块或 shared。
- 规则 2：单个文件若 > 400 行，优先按“领域子块”拆分（bootstrap/runtime/design 容易膨胀）。
- 规则 3：命名反映用途：
  - `*_page_service.py`：某一页装配/交互
  - `*_window_service.py`：窗口框架/切页
  - `*_service.py`：有副作用的流程编排（controller/env/UI）
  - `*_utils*`：纯函数（无 Tk、无 IO、无副作用）

---

## 8) 执行顺序与验证清单（未来做）

建议顺序（从低风险到高风险）：
1) shared 抽取（纯函数）
2) runtime 拆分（先 near-death 再 game_over/message_flush）
3) system_settings/design 归类（先逻辑分层后目录搬迁）
4) bootstrap/layout 归位（最后做，涉及入口与大量引用）

每一步结束都跑：
- `python -m compileall THUAI9-Backend-master/client/client_gRPC/dev_test/ui`
- `python -c "... import main_ui"`（不启动 UI）

补充：如果改动涉及 runtime_env 注入，建议额外跑一次“启动 UI 并加载 runtime 模式”的手工 smoke（不在本文件范围内）。
