# Plan

## Active Task

- Task: **tau-loop 收敛与产品化（迁移执行中）**——把 tau-loop 收敛为唯一仓库；对齐 tt-workflow 大修（去 cw + agent-led 纯文档化）；命令面收敛为单 `tau init`；harness 目录定为 `.harness/`；安装/使用双通道产品化（用法一/二、装法一/二）；tt-workflow 冻结；三机切换；dogfood。
- Spec: `.harness/specs/tau-loop-convergence-and-productization.md`
- Verification profile: `.harness/verification-profiles/refactor.md`
- Phase: 迁移知识面已完成（本窗口）；**阶段 1（tau-loop 大修对齐）待后续窗口执行**
- Owner: Codex + owner
- Status: in_progress
- Complexity: standard（大修）+ 产品化

## Steps

- [x] 阶段 0 决策冻结（D1 `.harness/`、D2 单 `tau init`、D3 无 cproj、D4 装法一现在写）——owner 2026-08-07 拍板。
- [x] 迁移知识面到 tau-loop：`AGENTS.md`（`.harness/` 路径 + 迁移上下文）、`.harness/{memory,plan,specs,verification,verification-profiles,hooks,tools}`。
- [ ] 阶段 1：tau-loop 大修对齐 tt-workflow（删 cw 面、verify.sh、AGENTS.md Long-Running Tasks、install.py/tests/CI/docs 更新）——后续窗口。
- [ ] 阶段 2：`bin/tau` 重写为单命令 `tau init`；`project_lifecycle.py` 改纯骨架创建——后续窗口。
- [ ] 阶段 3：全链 `.codex/` → `.harness/`（install.py/check 脚本/模板/README/CI/tests）——后续窗口（已部分完成：迁移时 hooks/tools/specs 已用 `.harness/`）。
- [ ] 阶段 4：安装/使用产品化（装法一 SKILL.md 指引、装法二 install.py、用法一 `tau init`、用法二自然语言）——后续窗口。
- [ ] 阶段 5：tt-workflow 冻结标记 + 三机切换——后续窗口。
- [ ] 阶段 6：dogfood 验证（tau-loop 内真实任务 + 三机消费）——后续窗口。

## Next Actions

- **下一步（新窗口起点）**：在 tau-loop 目录开新 codewhale 窗口 → 读 `AGENTS.md`（含迁移上下文）→ 读 `.harness/memory.md`、`.harness/plan.md` → 读定稿 spec → 从**阶段 1（tau-loop 大修对齐）**开始执行：删除 assets/ 的 cw 面（cw_state/supervisor/spike/agent_*/cw-hook/verify-v1/v2/模板/state）、建 verify.sh、改 AGENTS.md（Long-Running Tasks）、更新 install.py/tests/CI/docs。
- 参考实现：tt-workflow 大修分支 `overhaul/de-cw-and-agent-led-doc`（commit `15f9669`）——去 cw 的具体删除/改写清单可对照。
- 注意：tau-loop 的 v0.3.0 未推送提交（`09cfdc2`、`206039b`）方向与本次相反（含 agent-run/backends），发布前按新架构重做；本迁移在分支 `overhaul/consolidate-to-tau-loop` 上进行。

## Verification Plan

- `python3 .harness/tools/check_doc_freshness.py .` 通过。
- `python3 .harness/tools/check_task_state.py . --mode closeout` 通过。
- `.harness/hooks/verify.sh` exit 0（阶段 1 完成后）。
- 全仓无 `cw`/`cw_` 引用（archive 除外）；AGENTS.md 含 Long-Running Tasks；`tau init` 干净 repo 骨架；装法一/二、用法一/二四通道真实验证。
- git 分支：`overhaul/consolidate-to-tau-loop`。

## Exit Criteria

- 阶段 1–6 全部完成；tau-loop 成为唯一可维护仓库；tt-workflow 冻结；三机活跃项目切换；dogfood 基线跑通一个真实任务。
