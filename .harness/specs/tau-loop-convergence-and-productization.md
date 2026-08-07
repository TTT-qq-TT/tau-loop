# Task Spec: tau-loop-convergence-and-productization（草案）

- Status: ready（定稿，2026-08-07，D1–D4 已冻结；待迁移到 tau-loop 执行）
- Owner: Codex + owner
- Updated: 2026-08-07
- Related plan: 待定（本 spec 生效后更新 `.harness/plan.md`）
- Verification profile: `.harness/verification-profiles/refactor.md`
- 目标仓库：`/Users/tt/Project/tau-loop`（本 spec 在 tt-workflow 起草，审核通过后迁移到 tau-loop 执行）
- 前置：tt-workflow 大修已完成（`.codex/specs/overhaul-tt-workflow-architecture.md`，commit `15f9669`，分支 `overhaul/de-cw-and-agent-led-doc`）

## 0. 背景与目标（owner 决策链）

方案 A（owner 2026-08-07）：**只维护 tau-loop 一个仓库**。tt-workflow 冻结为历史归档；tau-loop 同时承担产品仓库与研发沙箱（开发者用 tau-loop 开发 tau-loop，三机真实项目作为消费方 dogfood）。

6 点细化：

1. **tau-loop 大修**，对齐 tt-workflow（去 cw 化 + agent-led 纯文档化）。
2. **tau 独有命令面（bin/tau）owner 已审核（D2）**：**只留 `tau init`（初始化骨架）**，其余全部退役；卸载走 `install.py --uninstall`。
3. **不要 cproj 族命令（D3）**：`tau init` 只创建骨架（AGENTS.md + harness 目录 + 模板 + hooks + check 脚本），**不做 enroll + 启动 agent**。
4. **harness 层目录名定为 `.harness/`（D1）**——因为 tau-loop 不止服务于 Codex，还服务于其他 agent。本 spec 迁移时即用新目录名。
5. **三机**：历史项目不动；活跃项目由 agent 按新流程更新。
6. **tau-loop 更明确的使用/安装方法**（产品化）：

   - 用法层：
     - 用法一：`cd 进项目` → `tau init` → 自动创建骨架（AGENTS.md、`.harness/` 下的 spec/hook/check 等）。
     - 用法二：全自然语言。进项目告诉 agent"我要用 tauloop 管理这个项目"，agent 自己在终端执行 `tau init`。
   - 安装层：
     - 装法一：全自然语言。一句话让 agent 装好——agent 根据 tau-loop GitHub 页下载 skill 到全局 skills，并运行 `install.py` 补齐 `tau` 命令。**（D4：现在就写进 SKILL.md）**
     - 装法二：终端安装（`install.py`）。

## 1. Goal

把 tau-loop 收敛为唯一仓库，达成：

- **G1**：tau-loop 与 tt-workflow 大修后的能力面一致（无 cw 字眼、无状态命令面、长时任务 agent 侧纯文档约定、hooks 为唯一机械兜底）。
- **G2**：产品命令面 `bin/tau` 重写为最小形态——**只留 `tau init`**（创建骨架）；卸载走 `install.py --uninstall`。
- **G3**：harness 层目录名定为 `.harness/`，全链（AGENTS.md/install/check/hooks/模板/教程/CI/README）一致。
- **G4**：安装与使用双通道产品化（用法一/二、装法一/二），自然语言可驱动。
- **G5**：tt-workflow 冻结为历史归档；三机活跃项目切换到 tau-loop。
- **G6**：dogfood 基线——用 tau-loop 开发 tau-loop + 三机真实项目消费，形成反馈闭环。

## 2. Non-Goals

- 不做"主动换窗"（仍为设计态，见 `doc/01_项目方案/24_*.md`；本 spec 只保证命令面干净）。
- 不复活 agent-led 脚本层（方向 1 已定，归档保留）。
- 不清理 tt-workflow 历史（冻结保留，供查阅）。
- 不保留 cproj 族命令与任何执行/状态命令面（D2/D3 已定：只留 `tau init`）。
- 不迁移 tt-workflow 的研发历史记录（spec/memory/report 留在 tt-workflow 冻结仓库）。

## 3. References Or Prior Art

- tt-workflow 大修 spec：`.codex/specs/overhaul-tt-workflow-architecture.md`（去 cw + agent-led 方向 1，验证全过）。
- 调研报告：`doc/01_项目方案/25_cw-command-surface-research.md`（cw 无消费者实证）、`26_架构改革基线.md`（大修前后对比）。
- 长时任务正解：报告 23（sleep 正解）、报告 24（主动换窗）；AGENTS.md `Long-Running Tasks` 章节。
- tau-loop 现状（2026-08-07 勘察）：`bin/tau` 全文（cw 透传链）、`install.py`（装 assets 全套 + SKILL.md + bin/tau）、`assets/`（旧 cw 面全套）、`.codex/`（干净模板）、产品外壳（SKILL.md/CHANGELOG/CI/docs/LICENSE/CONTRIBUTING/SECURITY/README.en）。
- tt-workflow 待迁移命令：`assets/bin/{cproj,cproj-on,cproj-off,cproj-safe,codex-project-on,codex-project-off,codex-project-init,tt-workflow-install}`。

## 4. Allowed Files

- `/Users/tt/Project/tau-loop/`（全部：bin/assets/docs/tests/.github/install.py/SKILL.md/CHANGELOG.md/README*.md/AGENTS.md/.harness/）
- `/Users/tt/Project/tt-workflow/`（仅：本 spec、memory/plan/report 记录、README 冻结标记）
- `doc/01_项目方案/27_*.md`（本方案落盘，新建）

## 5. Implementation Checklist

### 阶段 0：决策冻结（✅ 完成，2026-08-07，owner 已拍板）

- [x] **D1 目录名 = `.harness/`**（多 agent 通用，不绑定 Codex）。
- [x] **D2 tau 命令面 = 只留 `tau init`**（初始化骨架）；adopt/upgrade 合并进 init；uninstall 走 `install.py --uninstall`；run/run-status/cancel/recover/handoff/agent-run/loop*/state/status/doctor/verify 全部退役（能力层已删/归档，命令是无本之木）。
- [x] **D3 不要 cproj 族**：`tau init` 只创建骨架，不做 enroll + 启动 agent。
- [x] **D4 装法一现在就写**：SKILL.md 增加"自然语言安装"指引（agent 从 GitHub 下载 skill + 运行 install.py）。
- [x] 结论已冻结，本 spec 定稿（ready）。

### 阶段 1：tau-loop 大修对齐 tt-workflow（G1）

- [ ] 删除 `assets/bin/cw`、`assets/tools/cw_*`（cw_state/supervisor/spike/agent_*/test_cw_*）与 `assets/hooks/cw-hook.sh`、`verify-continuous-work-v1.sh`、`verify-continuous-work-v2.sh`。
- [ ] 删除 `assets/state/`、`assets/docs/continuous-work-v1.md`、`continuous-work-v2.md`、`assets/examples/cw-environment-bootstrap.template.md`。
- [ ] `assets/hooks/verify.sh`（对齐 tt-workflow：check 脚本 + closeout + 镜像一致性）。
- [ ] `assets/AGENTS.md`：加 `Long-Running Tasks` 章节，去 Spec vs Contract / cw 引用。
- [ ] `assets/tools/check_doc_freshness.py` / `check_task_state.py`：保留（含 check_markdown_links.py、project_lifecycle.py 评估去留）。
- [ ] `install.py`：validate_source 更新为新保留清单；去掉 cw 安装。
- [ ] `tests/`（test_package.py / test_v2_fixtures.py）：按新能力面改写。
- [ ] `.github/workflows/verify.yml`：去掉 cw fixtures，改跑新 verify。
- [ ] `docs/user-manual*.md`、`first-use*.md`、`README*.md`、`CHANGELOG.md`：全部去 cw，按新能力面重写。

### 阶段 2：命令面重塑（G2，✅ D2/D3 已定）

- [ ] `bin/tau` 重写：**只留 `tau init`**（创建骨架），去掉 cw 透传与全部旧命令；卸载走 `install.py --uninstall`。
- [ ] `project_lifecycle.py`：改为纯骨架创建逻辑（init），适配 `.harness/` 目录；adopt/upgrade 语义并入 init。
- [ ] `tau --help` 输出为单命令面（`tau init` + `--help`）。

### 阶段 3：目录改名（G3，✅ D1 = `.harness/`）

- [ ] 全链替换 `.codex/` → `.harness/`：AGENTS.md、install.py、check 脚本（CORE_FILES/LEGACY_PATHS）、hooks、specs 模板、README、docs、CI、tests。
- [ ] enrollment marker：`.codex-workflow` → `.harness-workflow`。
- [ ] 兼容迁移说明：存量 repo 如何从 `.codex/` 迁到 `.harness/`（文档 + 一次性迁移命令，若需要）。

### 阶段 4：安装与使用产品化（G4）

- [ ] **装法二**（终端）：`python3 install.py` 可用，安装 SKILL + bin/tau + assets；`tau --help` 正常。
- [ ] **装法一**（自然语言）：SKILL.md 写清"一句话安装"指引（agent 从 GitHub 下载 skill + 运行 install.py）；用真实 agent 会话验证。
- [ ] **用法一**（命令）：`cd 项目` → `tau init` → 自动生成 AGENTS.md + `.harness/` 骨架（spec 模板/hooks/check）。
- [ ] **用法二**（自然语言）：进项目说"我要用 tauloop 管理这个项目" → agent 自动执行用法一命令；用真实 agent 会话验证。
- [ ] 文档：README 与 SKILL.md 各含"用法一/二、装法一/二"四段式指引。

### 阶段 5：冻结与三机切换（G5）

- [ ] tt-workflow：README 加冻结标记（"archived, superseded by tau-loop"）；不再接收新工作。
- [ ] 本机：卸载 `~/.codex/skills/tt-workflow` 与 `~/.local/bin/{cproj,cw}`；安装 tau-loop；活跃项目用 tau。
- [ ] Y7000P / WS：活跃项目由 agent 更新到 tau-loop（历史项目不动）。
- [ ] 三机活跃项目 smoke：`tau init` + pre-task/pre-closeout 跑通。

### 阶段 6：dogfood 验证（G6）

- [ ] 用 tau-loop 开发一个真实任务（在 tau-loop 仓库内，走完整 spec→hooks→closeout）。
- [ ] 三机真实项目作为消费方反馈问题，记录到 failure-log。

## 6. Verification

- 命令：`tau --help`；`tau init` 干净 repo 骨架；`verify.sh` exit 0；`python3 install.py` + `--uninstall` 往返；CI（verify.yml）绿。
- 手动检查：tau-loop 全仓无 `cw`/`cw_` 引用（archive 除外）；AGENTS.md 含 Long-Running Tasks；目录名决策落地后全链一致；用法一/二、装法一/二四通道各真实验证一次。
- 残余风险：目录改名影响面大（阶段 3 单独验证）；三机活跃项目依赖盘点需 owner 提供清单。

## 7. Risks And Regression Points

- Risk: 目录改名破坏存量引用（AGENTS.md/install/check/templates/教程）。
  Why: `.codex/` 是发布面与所有 repo 的默认路径。
  Mitigation: 阶段 3 单独决策 + 全链 grep 验证 + 存量迁移文档；改名不可行则回退保留 `.codex/`。
- Risk: tau 命令面删错（owner 在用）。
  Why: 三机活跃项目可能依赖 `tau run` / `tau agent-run`。
  Mitigation: D2 先审后删；退役命令先 deprecated 拦截；三机依赖盘点先行。
- Risk: 装法一（自然语言安装）不可靠（agent 拉错版本/缺权限）。
  Why: 依赖 GitHub 下载 + 全局 skills 写入。
  Mitigation: 文档给精确命令序列；真实 agent 会话验证；失败时回退装法二。
- Risk: tt-workflow 冻结后历史不可找回。
  Why: 冻结是只读不是删除；git 历史保留。
  Mitigation: 冻结前确认所有活跃内容已迁；README 标记归档位置。

## 8. Notes And Decisions

- 本 spec 已定稿（ready），owner 已冻结 D1–D4；下一步迁移到 tau-loop 作为第一个真实 spec 执行。
- 决策链：方案 A（单仓库）→ 6 点细化（2026-08-07）→ 本草案。
- 目录名已定：`.harness/`（多 agent 通用，不绑定 Codex）。
- 命令面已定：只留 `tau init`，不做 enroll/启动；多 agent 兼容通过 AGENTS.md 通用约定实现（不绑定 codex 启动）。
