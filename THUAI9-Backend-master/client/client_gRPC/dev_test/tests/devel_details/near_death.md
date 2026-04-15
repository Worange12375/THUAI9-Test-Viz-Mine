# 濒死系统（dev_test）开发细节与落地计划

## 目标与口径（当前约定）

- 触发：棋子 HP 变为 0 时触发死亡检定（d20）。
- 结果：
  - d20=20：恢复至设定的 HP（默认 1），并显示 😇 角标。
  - d20=1：直接死亡。
  - 其它：进入濒死（HP=0 但仍存活），并开始倒计时。
- 倒计时口径（你当前要求）：
  - 设定值为 N“轮”（UI 输入 `turns_to_die`）。
  - 进入濒死时计算总回合数：`remaining_turns = 当前场上未死亡棋子数 × N`。
  - 这里“回合”定义为每次 `env.step()`（即行动队列推进一次）。
  - 每次 `env.step()` 结束后，输出一次濒死列表剩余回合数。
  - 当 `remaining_turns` 递减到 0：棋子立即死亡（必须从棋盘/队列移除）。

## 当前代码落点（已实现/在实现中）

### 1) 运行时配置（UI 写入）

- 文件：`client/client_gRPC/dev_test/ui/main_ui.py`
- 运行时字段：`env._ui_near_death_config`（dict）
  - `enabled`
  - `revive_hp_on_20`
  - `turns_to_die`（UI 文案是“轮”，逻辑上按“轮数”解释）
  - `die_on_damage_when_dying`
  - `can_move_when_dying`（目前仅 UI/配置，不拦截行动）
  - `can_attack_or_spell_when_dying`（目前仅 UI/配置，不拦截行动）

### 2) 规则 hook（玩法落地）

- 文件：`client/client_gRPC/dev_test/logic/test_mock_gameplay.py`
- 安装入口：`ensure_test_mock_gameplay_installed(env, logger=...)`
- 关键 hook：
  - `handle_death_check_hook(target)`：实现“20 复活 / 1 死亡 / 其它进濒死 + 初始化 remaining_turns”。
  - `step_hook()`：每次 `env.step()` 结束后
    - 维护濒死列表（`env._ui_near_death_state`）
    - 统一递减 remaining_turns
    - remaining_turns<=0 时调用 `_kill_piece(..., reason="濒死超时")`
    - 输出系统通知（濒死列表/死亡原因）

### 3) UI 信息展示（右下角）

- 文件：`client/client_gRPC/dev_test/ui/main_ui.py`
- 机制：规则 hook 会把消息写到 `env._ui_pending_info_messages`（list[str]）
- 刷新点：每次回合结束输出回合详细信息后，UI flush 该队列到右侧信息区。

## 已知问题（需要验证/可能踩坑）

- “场上未死亡棋子数”的统计口径：
  - 当前实现优先统计 `player1/player2.pieces` 的 `is_alive=True`，并回退到 `action_queue`。
  - 需要你确认：是否应包含濒死棋子（目前包含，因为 `is_alive=True`）。
- 消息展示顺序：
  - 目前将系统队列在“回合结束日志”后统一刷出，保证可见性；若你希望插入到更精确的时序点（例如伤害公式后立刻显示），需要再细化 flush 时机。

## 下一阶段：设置“下局生效”的补丁（你提出的方向）

你希望避免对战中途修改系统设置影响当前局，因此计划改为“设置写入下局，当前局不变”。

### 设计建议（按优先级）

1. **引入 staged config（待生效配置）**
   - UI 应用按钮不再直接写 `env._ui_near_death_config`，而写 `env._ui_near_death_config_next`。
   - UI 显示明确提示：已保存，下局生效。

2. **在开局/初始化点切换配置**
   - 在环境创建/初始化完成后（如 `initialize_environment` 后）执行：
     - 若存在 `*_next`，则复制到当前 config 并清空 next。
   - 注意：这一步需要一个稳定的“新局开始”事件点。

3. **把 hook 安装与配置切换解耦**
   - hook 安装可以一次性完成（仍然读取 `env._ui_near_death_config`）。
   - 配置切换只负责“本局使用哪份配置”。

## 落地优先级（建议执行顺序）

P0（必须闭环）
- 自动死亡：倒计时递减 + 到期 kill + 从棋盘/队列移除 + 右下角可见日志。
- 濒死列表：每回合输出，便于对局中确认。

P1（体验/一致性）
- 统一“轮/回合”口径：UI/日志/实现一致。
- 统计口径确认（alive_cnt 的定义）。

P2（下局生效改造）
- staged config + 开局切换 + UI 提示。

P3（行动能力限制真正落地）
- `can_move_when_dying` / `can_attack_or_spell_when_dying`：在输入处理或 action 校验处拦截。
  - 注意：这会影响对局逻辑，容易引入新 bug，建议单独开分支/分阶段。
