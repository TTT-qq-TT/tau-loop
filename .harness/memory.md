# Memory

## Current State

Project:
- Name: tau-loop
- Summary: 收敛为唯一仓库的迁移进行中（2026-08-07）。tau-loop 同时承担产品仓库与研发沙箱；tt-workflow 已大修（去 cw + agent-led 纯文档化）并冻结为历史归档。本仓库的 harness 层目录名为 `.harness/`（不再用 `.codex/`），命令面为单命令 `tau init`。
- Current focus: 执行迁移 spec `.harness/specs/tau-loop-convergence-and-productization.md`（ready，阶段 0 决策已冻结；当前处于阶段 1 前夜——知识面已迁移，等待在本仓库开新窗口继续大修）。
- 上游参考：tt-workflow（`/Users/tt/Project/tt-workflow`）已冻结；其大修分支 `overhaul/de-cw-and-agent-led-doc`（commit `15f9669`）记录了完整去 cw 过程，可作实现参考。

Working:
- 已冻结决策（owner，2026-08-07）：
  - **D1 目录名 = `.harness/`**（多 agent 通用，不绑定 Codex）。
  - **D2 tau 命令面 = 只留 `tau init`**（初始化骨架）；卸载走 `install.py --uninstall`；其余全部退役。
  - **D3 不要 cproj 族**：`tau init` 只创建骨架，不做 enroll + 启动 agent。
  - **D4 装法一现在就写**：SKILL.md 增加"自然语言安装"指引（agent 从 GitHub 下载 skill + 运行 install.py）。
- 已迁移到本仓库的知识面：根 `AGENTS.md`（指向 `.harness/` + 迁移上下文）、`.harness/memory.md`、`.harness/plan.md`、`.harness/specs/tau-loop-convergence-and-productization.md`（定稿 spec）、`.harness/specs/{TEMPLATE,README}.md`、`.harness/verification.md` + `verification-profiles/`（4 个）、`.harness/hooks/{pre-task,pre-closeout,verify}.sh`、`.harness/tools/{check_doc_freshness,check_task_state}.py`（路径已替换为 `.harness/`）。
- 尚未迁移/待做（后续窗口执行）：bin/tau 重写（单命令）、install.py 更新、assets/ 去 cw（删除 cw 面文件）、SKILL.md 增加装法一、docs/README/CHANGELOG 去 cw、tests/CI 更新、删除旧 `.codex/` 模板（本窗口已完成删除，见 git）、tt-workflow 冻结标记、三机切换。

Broken or missing:
- 旧 `.codex/` 模板（tau-loop 原本的干净模板）已随迁移删除（git 中记录）。
- `assets/` 仍是旧版 cw 面全套（cw_state/supervisor/agent_*/cw-hook/verify-v1/v2/模板）——这是阶段 1 要清理的，未动。
- `bin/tau` 仍是旧版（cw 透传链），未重写。
- `install.py` 仍装 assets 全套（含 cw），未更新。
- SKILL.md 仍是旧版（描述 cw 命令面），装法一指引未写入。

Active decisions:
- Decision: 收敛为单仓库（只维护 tau-loop），tt-workflow 冻结。
  Why: 双仓库维护成本高；开发者作为使用者（dogfood）能更快发现问题。
- Decision: harness 目录 `.harness/`，命令面单 `tau init`，无 cproj。
  Why: 多 agent 通用；最小命令面；只初始化骨架不绑定启动。

Open risks:
- Risk: tau-loop 的 v0.3.0 未推送提交（`09cfdc2`、`206039b`）与本次迁移方向相反（旧版含 agent-run/backends，本次已归档）。
  Impact: 若直接推送旧 v0.3.0 会发布错误方向。
  Mitigation: 本迁移在分支 `overhaul/consolidate-to-tau-loop` 上进行；发布前按新架构重做 v0.3.0（或直接推送新架构版）。
- Risk: 三机活跃项目可能依赖旧 cw/tau 命令面。
  Impact: 切换后命令不存在。
  Mitigation: D2 已定只留 `tau init`；切换前盘点活跃项目依赖，用 AGENTS.md 长时任务约定接管。

Current checkpoints:
- Last thread ended because: 迁移知识面已落盘到 tau-loop，等待新窗口继续执行阶段 1 大修。
- Safe restart point: 在 tau-loop 目录开新窗口 → 读 `AGENTS.md`（含迁移上下文）→ 读 `.harness/memory.md`、`.harness/plan.md` → 读定稿 spec `.harness/specs/tau-loop-convergence-and-productization.md` → 从阶段 1 开始执行。
- Must-read files for the next thread: `AGENTS.md`、`.harness/memory.md`、`.harness/plan.md`、`.harness/specs/tau-loop-convergence-and-productization.md`

## Important Context

- **为什么目录是 `.harness/` 而不是 `.codex/`**：tau-loop 服务于多 agent（Codex/Claude/其他），harness 层不应绑定单一 agent 品牌；`.codex/` 是历史遗留名。
- **为什么命令面只留 `tau init`**：15 个旧命令里绝大多数是已被删除/归档能力层（supervisor、状态机、agent-led 脚本、v3 loop）的残留入口；能力没了命令是无本之木；adopt/upgrade 与 init 语义重叠；uninstall 走 install.py。长时任务由 AGENTS.md `Long-Running Tasks` 约定取代（nohup/screen 解耦 + sleep + 醒来检查，零脚本执行层）。
- **长时任务正解**（已在 AGENTS.md 落地）：任务进程由 OS 托管（`nohup` / `screen`），agent 只是周期性访问者；事件驱动唤醒在有头场景不省 token（resume 全量带回 vs sleep 增量）。
- **防假完成边界**：放弃机械账本后依赖 agent 纪律 + pre-closeout 证据检查（hooks 是唯一机械兜底）。

## Archive

- tt-workflow 的完整研发历史留在冻结仓库 `/Users/tt/Project/tt-workflow`（60+ spec、报告 23-26、大修分支 `overhaul/de-cw-and-agent-led-doc`）；本仓库 `.harness/memory.md` 只保留迁移所需的浓缩知识。
