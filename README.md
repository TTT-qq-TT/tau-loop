<p align="center">
  <img src="docs/images/tauloop-mark.png" alt="" width="48" height="48" valign="middle"> <strong>τ-Loop</strong>
  <br>
  <em>Give the goal to the agent. TauLoop keeps the plan, the evidence, and the next step.</em>
</p>

<p align="center">
  <img src="docs/images/tauloop-readme-cover.png" alt="TauLoop: a lightweight file-backed execution harness" width="960">
</p>

TauLoop gives a repository a lightweight, file-backed execution harness with one command: `tau init`. After that, the workflow is pure convention in the project's `AGENTS.md` — no daemon, no state machine, no script execution layer.

---

## Start with one sentence

Tell your agent:

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project forward to xxx.
```

The agent installs TauLoop, runs `tau init` in the project, and breaks the goal into checkable pieces.

## Three things it keeps safe

### 1. It does not stop in the gaps

Between turns, the project keeps its plan, specs, and verification records. The next agent reads `AGENTS.md`, then `.harness/memory.md` and `.harness/plan.md`, and continues from evidence — not from a fresh chat.

### 2. It does not start over after a new window

A spec is the durable contract for a task: goal, boundaries, allowed files, acceptance. Work resumes where the records say it was.

### 3. It does not turn waiting into noise

Long commands are owned by the operating system (`nohup`/`screen`), decoupled from the conversation. The agent sleeps in-session and wakes to check the log, the process, and the artifacts. Completion requires verification evidence, not a heartbeat.

## Two things it is especially good at

### 1. Move a project to xxx

Turn a goal into small checkable specs, work through them in order, verify each one, and record checkpoints. Stop only for genuine human decisions.

### 2. Let a long command finish quietly

Downloads, builds, and data assembly follow the `Long-Running Tasks` convention in `AGENTS.md`: plan as a spec, launch decoupled, sleep, wake and check, record evidence, close out.

## Want to look a little closer?

- [User manual](assets/docs/user-manual.en.md) — installation, enabling a project, the daily workflow, long tasks, verification hooks, and boundaries.
- [First-use guide](assets/docs/first-use.en.md) — the fastest way to start.
- [Migration guide](assets/docs/migration-from-codex.md) — moving an existing `.codex/` repo to `.harness/`.
- The only mechanical guards are the packaged hooks and check scripts; everything else is documented convention.

## What it will not do

- It will not run your commands or keep a daemon around.
- It will not claim a running process is success.
- It will not grow a command surface: `tau` is exactly `tau init` (+ `--help`).
- It will not make decisions that are yours: permissions, spending, irreversible actions, failed verifiers, and review points stay with you.

## Manual install

Requires Python 3.9+; supports macOS and Ubuntu.

```bash
git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

After installation, the `tau` command lands in `~/.codex/bin`; make sure it is on `PATH`. Uninstall with `python3 install.py --uninstall`.

## Learn more

- [User manual (中文)](assets/docs/user-manual.md) · [First-use (中文)](assets/docs/first-use.md)
- [License](LICENSE) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

<p align="center">
  <img src="docs/images/tauloop-mark.png" alt="" width="48" height="48" valign="middle"> <strong>τ-Loop</strong>
  <br>
  <em>把目标交给 agent。TauLoop 负责让项目留下计划、证据和下一步。</em>
</p>

<p align="center">
  <img src="docs/images/tauloop-readme-cover.png" alt="TauLoop：轻量的文件化执行 harness" width="960">
</p>

TauLoop 用一条命令 `tau init` 给仓库一个轻量的文件化执行 harness。之后的全部工作流都是项目 `AGENTS.md` 里的约定——没有 daemon、没有状态机、没有脚本执行层。

---

## 从一句话开始

告诉你的 agent：

```text
请阅读并安装 https://github.com/TTT-qq-TT/tau-loop ，然后用 TauLoop 把当前项目推进到 xxx。
```

agent 会安装 TauLoop、在项目里执行 `tau init`，并把目标拆成可检查的小任务。

## 它替你守住三件事

### 1. 不会在空白处停住

回合之间，项目会留下计划、spec 和验证记录。下一位 agent 读 `AGENTS.md`，再读 `.harness/memory.md` 和 `.harness/plan.md`，从证据继续——而不是从一段新聊天重新开始。

### 2. 不会因为换窗口重新开始

spec 是任务的持久契约：目标、边界、允许改的文件、验收。工作从记录停下的地方继续。

### 3. 不会把等待变成刷屏

长命令由操作系统托管（`nohup`/`screen`），与对话解耦。agent 在会话里 sleep，醒来检查日志、进程和产物。完成靠验证证据，不靠心跳。

## 两件它特别适合做的事

### 1. 把一个项目推进到 xxx

把目标拆成可检查的小 spec，按顺序完成、逐个验证、记录 checkpoint。只在真正需要你拍板时停下。

### 2. 让一条长命令安静地跑完

下载、构建、数据组装都走 `AGENTS.md` 里的 `Long-Running Tasks` 约定：先写 spec、解耦启动、sleep、醒来检查、记录证据、收尾。

## 想多看一眼？

- [完整使用手册](assets/docs/user-manual.md)——安装、启用项目、日常工作流、长任务、验证钩子与边界。
- [初次使用指南](assets/docs/first-use.md)——最快的开始方式。
- [迁移指南](assets/docs/migration-from-codex.md)——把存量 `.codex/` 仓库迁到 `.harness/`。
- 唯一的机械兜底是打包的 hooks 与 check 脚本；其余都是文档化约定。

## 它不会做什么

- 不会替你执行命令，也不会有常驻 daemon。
- 不会把"进程还在跑"当成完成。
- 不会膨胀命令面：`tau` 只有 `tau init`（+ `--help`）。
- 不会替你决定属于你的事：权限、花钱、不可逆操作、验证失败与 review 节点都留在你手里。

## 手动安装

需要 Python 3.9+；支持 macOS 和 Ubuntu。

```bash
git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

安装后 `tau` 命令位于 `~/.codex/bin`，确保它在 `PATH` 上。卸载：`python3 install.py --uninstall`。

## 更多内容

- [User manual (English)](assets/docs/user-manual.en.md) · [First-use (English)](assets/docs/first-use.en.md)
- [License](LICENSE) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)
