# dev_test/ui 目录说明

本目录是 **测试端可视化 UI**（Tkinter/ttk）。目标是：
- 快速测试后端结算逻辑（移动/攻击/法术/回放等）；
- 在不改后端代码的前提下，提供测试端“运行时注入/覆盖”能力（例如濒死系统、法术池等）。

> 入口：`main_ui.py`

补充：`main_ui.py` 启动时会设置 `sys.dont_write_bytecode = True`，避免运行 UI 产生/更新 `__pycache__/*.pyc` 带来 git 噪音。

---

## 1. 当前目录结构

## 1.1 实时项目结构（tree）

> 维护要求：每次在 `ui/` 下新增/移动/删除文件后，请同步更新此树。

```text
ui/
  README.md               # 本说明
  main_ui.py              # 主入口（装配/事件协调）
  components.py           # 通用 UI 组件
  assets/                 # 文案/素材
    tutorial.txt            # 教程文本
    dev_info.txt            # 开发信息文本
    trap_pixel.png          # 图片素材等
  services/               # 业务/运行时逻辑（优先从这里找）
    __init__.py
    layout/               # 主窗口布局装配（左右侧 UI 框架）
      __init__.py
      main_layout_service.py                      # MainUI 左/右侧区域装配
      main_ui_bootstrap_service.py                # MainUI.__init__ 启动/状态初始化下沉
    board/                # 棋盘刷新/覆盖层计算
      __init__.py
      board_view_service.py                      # 棋盘刷新 + move/spell 预览 + 🎯/陷阱标记
      board_data_service.py                      # runtime/mock 棋盘数据提取（rows/pieces）
    cards/                # 卡片/状态行刷新
      __init__.py
      piece_cards_service.py                     # 左上 6 卡 + 行动状态行刷新
    replay/               # 回放/跳转/播放控制 + 回合详情
      __init__.py
      replay_service.py                          # 回放 UI + 回放推进 + mock 状态重建 + 回合详情追加
    actions/              # 行动（面板/提交）
      __init__.py
      action_submit_service.py       # 提交分发器（move/attack/spell）
      action_panel_service.py        # 行动面板（渲染/选点/日志/陷阱/行动完毕）
      action_move_service.py         # move 提交
      action_attack_service.py       # attack 提交
      action_spell_service.py        # spell 提交
    attribute_settings/   # 属性设置窗口
      __init__.py
      attribute_settings_window_service.py            # 新建页/切页/应用
      attribute_settings_page_switch_service.py       # 页内切换（piece/map/action）
      attribute_settings_piece_page_service.py        # piece 页面
      attribute_piece_utils_service.py                # piece 页工具：归一化/可走性/错误高亮
      attribute_settings_map_page_service.py          # 地图设置页面
      attribute_settings_action_page_service.py       # 行动设置页面
      attribute_derived_stats_service.py              # 职业与派生属性、初始化、一键开始
    data_loading/         # 模式选择/加载流程
      __init__.py
      mode_selection_dialog_service.py                # 模式/数据源/数据集选择弹窗
      game_data_loading_service.py                    # 加载流程（含 runtime hook 安装点）
      source_mode_utils_service.py                    # source/mode 工具函数
      reset_game_service.py                           # 重置流程（清空 UI 状态并重新选择加载）
    dialogs/              # 通用弹窗
      __init__.py
      popup_service.py                               # confirm/notice/initiative/game_over 等
    design/               # 玩法设计（测试端规则覆盖）
      __init__.py
      design_page_service.py                         # 玩法设计页总装配
      design_attribute_page_service.py               # 属性规则覆盖页
      design_global_page_service.py                  # 全局规则覆盖页
      design_spell_pool_page_service.py              # 法术池覆盖页
    runtime/              # 运行时（hook/监控/初始化/输入）
      __init__.py
      runtime_hooks_service.py                       # hook 注入/跨局重应用
      runtime_monitor_service.py                     # 存活判定/消息 flush/图标刷新/胜负播报
      runtime_init_service.py                        # runtime 初始化配置/输入/先攻掷骰捕获
    system_settings/      # 系统设置窗口
      __init__.py
      system_general_page_service.py                 # general 页构建/应用
      system_text_pages_service.py                   # tutorial/dev 文本页
      system_settings_dirty_service.py               # dirty 追踪/回滚/抑制
      system_settings_window_service.py              # 窗口框架/切页/关闭
```

## 1.2 目录树补充说明（tree 看不出来的部分）

- `main_ui.py`
  - 负责主窗口装配与“薄委托”事件协调；复杂逻辑优先下沉到 `services/`。
- `components.py`
  - 放可复用 UI 组件（棋盘/信息面板/卡片等），尽量不塞业务规则。
- `services/data_loading/`
  - 模式选择（runtime_custom/runtime_profession/mock）+ mock 数据集选择 + 加载流程（含死亡检定 hook）。
- `services/system_settings/`
  - 系统设置窗口：建页/切页/dirty/关闭回滚 + tutorial/dev 文本页。
- `services/attribute_settings/`
  - 属性设置窗口：装配、切页、piece/map/action 三页的构建与应用。
- `services/actions/`
  - 行动面板 + 行动提交：move/attack/spell 的面板渲染、选点与提交/预览逻辑。
- `services/board/`
  - 棋盘刷新与覆盖层计算（移动高亮、法术 AOE、🎯目标、陷阱标记）以及 runtime/mock 的棋盘数据提取。
- `services/cards/`
  - 左上 6 卡片 + 行动状态行刷新（runtime/mock）。
- `services/replay/`
  - 回放控制区 UI、播放/暂停/单步、回合跳转/回退的 mock 状态重建，以及回合详情追加。
- `services/runtime/`
  - 运行时相关：hook 注入、存活判定/提示 flush、初始化配置与输入等。
- `services/dialogs/`
  - 通用弹窗：确认/提示/先攻详情等。

- `main_ui.py`
  - 主入口与总装配（窗口骨架、左右分栏、按钮事件、刷新/渲染）。
  - 当前已完成薄委托化：复杂逻辑优先下沉到 `services/**`，`main_ui.py` 只做入口与协调。

- `components.py`
  - 可复用 UI 组件（棋盘、信息面板、右侧组合面板、卡片等）。
  - 原则：尽量“纯 UI 组件”，不要塞业务规则。

- `assets/`
  - UI 文案与素材文件。
  - 例如：`tutorial.txt`（使用教程）、`dev_info.txt`（开发信息）。

- `services/`
  - **Service 层（推荐先找这里）**：放“运行时环境操作/注入/业务计算”等逻辑。
  - 目标：让页面代码只负责“拿输入 → 调 service → 渲染输出”。

---

## 2. 新手快速定位：我要改什么？去哪里？

- 想改主窗口布局/按钮入口/整体流程：看 `main_ui.py`
- 想改棋盘/信息面板/卡片等 UI 组件：看 `components.py`
- 想改“玩法规则在测试端怎么覆盖/注入到 runtime env”：优先看 `services/`
- 想改“濒死系统的结算逻辑本体”：看 `dev_test/logic/test_mock_gameplay.py`

---

## 3. 文件命名与注释约定

- 文件名尽量直白：
  - service 已按功能分到 `services/<子包>/` 下（例如 `services/actions/`、`services/design/`）
  - `runtime_hooks_service.py` = 运行时 hook 注入/重应用
  - `runtime_monitor_service.py` = 存活判定/消息 flush/图标刷新/胜负播报
  - `runtime_init_service.py` = runtime 初始化默认配置/初始化入参/动作输入/先攻捕获
  - `action_submit_service.py` = 行动提交分发器（move/attack/spell）
  - `action_move_service.py` = move 提交
  - `action_attack_service.py` = attack 提交
  - `action_spell_service.py` = spell 提交
  - 未来可能有：`runtime_loader_service.py`（加载数据）等

- 每个新拆出的文件都在文件开头用 docstring 写清：
  - 这个文件负责什么
  - 不负责什么（边界）
  - 主要对外接口/用法

---

## 4. 拆分重构的规划文档

- 当前规划文档未纳入仓库交付物；以本 README 的 tree 与各 service 文件头注释为准。
