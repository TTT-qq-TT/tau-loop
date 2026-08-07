# TauLoop 完整使用手册

[English](user-manual.en.md) | **简体中文**

> 把目标交给 agent。TauLoop 负责让项目留下计划、证据和下一步。
>
> 这不是一套要求你背下来的「agent workflow」课程。它是一组放在项目里的记录与约定：一段工作完成后，下一段能据此继续；需要等待的长命令由操作系统托管，agent 按约定醒来检查；真正属于你的决定仍然回到你手里。

## 目录

- [先用起来](#先用起来)
- [安装](#安装)
- [启用项目](#启用项目)
- [日常推进一个项目](#日常推进一个项目)
- [让长命令安静地完成](#让长命令安静地完成)
- [验证与钩子](#验证与钩子)
- [安全边界与人工决定](#安全边界与人工决定)
- [命令速查](#命令速查)

---

## 先用起来

### 最推荐的开始方式：说清目标

把下面这段话连同 TauLoop 仓库链接发给 agent，将 `xxx` 换成你的结果即可：

```text
请阅读并安装 https://github.com/TTT-qq-TT/tau-loop ，然后用 TauLoop 把当前项目推进到 xxx。

能自己验证的就继续；真正需要我决定时再停下来。
```

agent 会安装 TauLoop、判断项目是新项目还是已有项目、创建必要的项目记录，并先把工作拆成可检查的部分。你不需要先知道 `spec`、`checkpoint` 或 `harness` 分别是什么。

如果你希望先看方案，在最后补一句：

```text
先只给我看计划和每一段的完成标准，等我确认后再开始。
```

## 安装

需要 Python 3.9+；当前支持 macOS 和 Ubuntu。

### 装法一：自然语言（推荐）

对 agent 说"请安装 TauLoop"或直接给仓库链接。agent 会下载仓库并运行安装器，全程不需要你敲命令。装完后 `tau` 命令可用。

### 装法二：终端安装

```bash
git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop /tmp/tau-loop-install
python3 /tmp/tau-loop-install/install.py
rm -rf /tmp/tau-loop-install   # 可选清理
```

安装器把 skill 放到 `~/.codex/skills/tau-loop/`，把 `tau` 命令放到 `~/.codex/bin/`。如果终端找不到 `tau`，把 `~/.codex/bin` 加入 `PATH`，再检查：

```bash
tau --help
```

卸载：

```bash
python3 ~/.codex/skills/tau-loop/install.py --uninstall
```

## 启用项目

### 用法一：命令

```bash
cd 你的项目
tau init --root .
```

`tau init` 只创建缺失的骨架文件：根 `AGENTS.md` + `.harness/`（spec 模板、hooks、check 脚本、verification profiles）。它从不覆盖你已有的文件。

### 用法二：自然语言

进项目后对 agent 说一句"我要用 tauloop 管理这个项目"。agent 会在项目目录里自己执行 `tau init`，然后向你说明准备了什么，等你给出目标。

### 存量项目迁移

如果项目还在用旧的 `.codex/` 目录，按[迁移指南](migration-from-codex.md)一次性迁移到 `.harness/`。

## 日常推进一个项目

启用后，项目的 `AGENTS.md` 就是约定本身：

1. **启动顺序**：agent 先读 `.harness/memory.md`、`.harness/plan.md`，再按 plan 指向当前任务的 spec。架构背景、验证细则和历史只在任务需要时读取。
2. **先写 spec**：非平凡工作先写成 `.harness/specs/<名称>.md`（目标、边界、允许改的文件、验收），再动代码。spec 是任务的持久契约。
3. **执行与验证**：按 spec 推进，每段完成记录验证证据，更新 spec 的 checklist。
4. **换任务或结束线程前**：更新 `.harness/memory.md` 和 `.harness/plan.md`，让下一段工作能接着继续。

## 让长命令安静地完成

长时间的命令（大下载、大构建、数据组装）**由操作系统托管，不占用对话**。这是 `AGENTS.md` 里 `Long-Running Tasks` 章节的约定，agent 按如下节奏执行：

1. 把长命令写成脚本，用 `nohup` 或 `screen` 解耦启动，记录 PID 和日志路径。
2. agent 在会话里 `sleep` 等待（粗粒度间隔，不做高频轮询）。
3. 醒来后读日志尾部、查进程、比对产物；正常就记一条状态继续睡，失败就读日志修脚本重新启动。
4. 完成标准是阶段自检与产物存在（校验和、测试输出），不是"进程还活着"。

这套约定不需要任何 daemon、状态机或脚本执行层——进程归 OS，agent 只是周期性访问者。

## 验证与钩子

- `.harness/hooks/pre-task.sh`：开始非平凡任务前跑，检查文档新鲜度与任务状态。
- `.harness/hooks/pre-closeout.sh`：任务收尾前跑，检查 spec 是否完成、验证是否记录。
- `.harness/hooks/verify.sh`：完整验证（文档新鲜度 + 任务状态 + 在源仓库里校验打包资产不漂移）。
- `assets/tools/check_markdown_links.py`：检查文档链接有效性。

hooks 是唯一的机械兜底；其余靠 agent 纪律与证据。

## 安全边界与人工决定

- TauLoop 没有 daemon，也不替你执行命令。长任务由 OS 托管，agent 周期性检查。
- 进程在跑、日志在输出，都不算完成。完成必须有实际的验证证据。
- 命令面只有 `tau init`（+ `--help`）。其余全部是约定，不是命令。
- 需要你拍板的时刻 agent 会停下：新权限、花钱、不可逆操作、验证失败、依赖不满足、或你明确要求 review。

## 命令速查

| 想做什么 | 怎么做 |
|---|---|
| 装 TauLoop（自然语言） | 对 agent 说"请安装 TauLoop" |
| 装 TauLoop（终端） | `python3 install.py` |
| 卸载 | `python3 install.py --uninstall` |
| 启用项目（命令） | `tau init --root .` |
| 启用项目（自然语言） | "我要用 tauloop 管理这个项目" |
| 存量迁移 | `migration-from-codex.md` |
| 查看帮助 | `tau --help` |
| 完整验证 | `.harness/hooks/verify.sh` |
