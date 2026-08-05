<a id="english"></a>

<h1 align="center">
  <img src="docs/images/tauloop-mark.png" alt="" width="48" height="48" valign="middle"> <strong>τ-Loop</strong>
</h1>

<p align="center">
  <strong>TauLoop</strong> · τ = 2π: one complete turn, not an endlessly growing chat.
</p>

<p align="center">
  You name the goal. Codex shapes the work, verifies it, and leaves the next step behind.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4C430?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8 or later">
  <img src="https://img.shields.io/badge/Codex-Skill-10A37F?style=flat-square" alt="Codex Skill">
  <img src="https://img.shields.io/badge/macOS%20%2B%20Ubuntu-supported-4C8BF5?style=flat-square" alt="macOS and Ubuntu supported">
</p>

<p align="center">
  <strong>English</strong> · <a href="#chinese">简体中文</a>
</p>

<p align="center">
  <a href="#start-with-one-sentence">Start with one sentence</a> · <a href="#three-things-it-keeps-safe">What it keeps safe</a> · <a href="#two-things-it-is-especially-good-at">Two scenarios</a> · <a href="#want-to-look-a-little-closer">Look closer</a> · <a href="#what-it-will-not-do">Limits</a> · <a href="#manual-install">Manual install</a>
</p>

<p align="center">
  <img src="docs/images/tauloop-readme-cover.png" alt="TauLoop: one complete turn, continuing forward" width="960">
</p>

---

>You give Codex a goal before bed. The next morning, it is stuck at the very first step, waiting for a decision that should never have been yours.
>TauLoop leaves the plan, verification results, and next step in the project, so the work is not trapped in one chat.

## Start with one sentence

> [!TIP]
> **First time here?** You do not need to learn commands, file layouts, or agent workflows. Send Codex the text below with this repository link, then replace `xxx` with your goal.

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project forward to xxx.

Keep going when you can verify the work yourself; stop only when a real decision is mine.
```

Codex installs TauLoop and prepares the project records it needs. You do not have to memorize commands or understand `spec`, `checkpoint`, or `harness` first.

## Three things it keeps safe

### 1. It does not stop in the gaps

`plan` · `spec`

>TauLoop turns "get to xxx" into a next step with a definition of done. Once the goal and boundaries are clear, Codex does not have to ask you what to do after every small move.

### 2. It does not start over after a new window

`checkpoint` · `memory`

>After each piece of work, the project keeps what happened, where the evidence is, and what comes next. When context fills up or a fresh Codex takes over, it receives those facts, not an entire old chat.

### 3. It does not turn waiting into noise

`continuous-work`

>Downloads, installs, builds, and tests with clear completion criteria can wait quietly in a local process and be verified. Codex does not need to keep rereading logs, and it does not confuse "the process is still alive" with "the task is done."

---

## Two things it is especially good at

### 1. Move a project to xxx

You do not need to know every small task up front. State the outcome you need and the places where only you should decide. TauLoop has Codex first lay out the path and the completion criteria for each piece; after verification, it leaves a checkpoint and moves on.

```text
Use TauLoop to keep moving this repo until xxx is complete.
Break down the work and verify each piece yourself; stop only when you need my decision.
```

When you return the next day, you should find inspectable progress, not a long chat you have to understand again.

### 2. Let a long command finish quietly

When dependencies are downloading, an environment is being configured, or a build or test is running, it is the local command that needs to wait, not Codex's chat window. For serial work with explicit steps and verification, TauLoop has Codex write the execution plan, supervise the real process, and start the next stage only after the previous one passes.

```text
Use TauLoop to configure the xxx environment.
Split downloading, installation, and checks into serial stages; start the next stage only after the previous one verifies; do not frequently inspect download progress; stop at a checkpoint when everything is complete.
```

---

## Want to look a little closer?

You do not need to manage TauLoop's workflow. But when a project matters, knowing how to ask these four questions is enough to see where it is going.

| What I want to know now | What TauLoop leaves behind | Say this to Codex |
| --- | --- | --- |
| Where is the project going now? | **`plan`** records the goal, current phase, and next step. | "Show me the current plan and the step being worked on now." |
| What makes this piece complete? | **`spec`** defines the scope, completion criteria, and verification. | "Show me the current spec's definition of done, then wait for my approval before starting it." |
| How can it resume after a new window? | **`checkpoint`** keeps the facts that just happened; **`memory`** keeps facts that still matter. | "Show me this checkpoint and what the project still needs to remember." |
| What is it waiting for, and when will it continue? | **`continuous-work`** supervises serial work with explicit commands and verification conditions. | "Keep moving this project until feature xx is complete." |

### TauLoop's "one turn"

`goal -> checkable step -> verification -> handoff -> next step or your decision`

It does not make Codex loop forever. It lets one unit of work complete a whole turn with evidence.

> [!NOTE]
> These records live in the project. Some people call that a harness; for you, it is simply project work that does not depend on a single chat window.

## What it will not do

> [!IMPORTANT]
> **Verify, then continue.** TauLoop is meant to finish work in a checkable way, not let Codex run without boundaries.

- It will not magically continue after a computer restart or terminal close.
- It will not treat a heartbeat as proof of success.
- It will not claim that CUDA, a GPU, or a simulator works just because a test fixture passes.
- It will not make decisions about permissions, spending, irreversible changes, or what to do after verification fails.

---

## Manual install

The natural-language path above is recommended. You only need these three lines when Codex asks you to install it manually:

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

After installation, Codex discovers the TauLoop skill. If your environment does not put `~/.codex/bin` on `PATH`, follow Codex's prompt.

## Learn more

- [First-use guide](assets/docs/first-use.en.md)
- [Complete user manual](assets/docs/user-manual.en.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

TauLoop is available under the [MIT License](LICENSE).

---

<a id="chinese"></a>

<h1 align="center">
  <img src="docs/images/tauloop-mark.png" alt="" width="48" height="48" valign="middle"> <strong>τ-Loop</strong>
</h1>

<p align="center">
  <strong>TauLoop</strong> · τ = 2π：一整圈，不是一段无限长的对话。
</p>

<p align="center">
  你说目标，Codex 拆任务、做验证、留下下一步。
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4C430?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8 or later">
  <img src="https://img.shields.io/badge/Codex-Skill-10A37F?style=flat-square" alt="Codex Skill">
  <img src="https://img.shields.io/badge/macOS%20%2B%20Ubuntu-supported-4C8BF5?style=flat-square" alt="macOS and Ubuntu supported">
</p>

<p align="center">
  <a href="#english">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <a href="#从一句话开始">从一句话开始</a> · <a href="#它替你守住三件事">它替你守住三件事</a> · <a href="#两件它特别适合做的事">两个场景</a> · <a href="#想多看一眼">想多看一眼</a> · <a href="#它不会做什么">边界</a> · <a href="#手动安装">手动安装</a>
</p>

<p align="center">
  <img src="docs/images/tauloop-readme-cover.png" alt="TauLoop：一整圈，继续向前" width="960">
</p>

---

>你睡前把一个目标交给 Codex。第二天，它停在最早的一步，等你决定本不该由你决定的事。
>TauLoop 把计划、验证的结果和下一步留在项目里，让工作不被一段聊天困住。

## 从一句话开始

> [!TIP]
> **第一次使用？** 不需要先学习命令、文件结构或 agent workflow。把下面这段话连同仓库链接发给 Codex，然后把 `xxx` 换成你的目标。

```text
请阅读并安装 https://github.com/TTT-qq-TT/tau-loop ，然后用 TauLoop 把当前项目推进到 xxx。

能自己验证的就继续；真正需要我决定时再停下来。
```

Codex 会安装 TauLoop，并在项目里准备它需要的工作记录。你不必记住命令，也不必先理解 `spec`、`checkpoint` 或 `harness`。

## 它替你守住三件事

### 1. 不会在空白处停住

`plan` · `spec`

>TauLoop 先把“做到 xxx” 整理成有完成标准的下一步。目标和边界已经清楚时，Codex 不必每走一步都回来问你。

### 2. 不会因为换窗口重新开始

`checkpoint` · `memory`

>每完成一段，项目会留下已经做了什么、证据在哪里、接下来做什么。上下文快满或需要换一个 Codex 时，接过去的是这些事实，不是一整段旧聊天。

### 3. 不会把等待变成刷屏

`continuous-work`

>下载、安装、构建、测试这类有明确完成条件的工作，可以由本地进程安静地等待和验证。Codex 不必反复回来读日志，也不会把“进程还活着”说成“任务已经完成”。

---

## 两件它特别适合做的事

### 1. 把一个项目推进到 xxx

你不需要先把所有小任务想清楚。只要说出要达到的结果，以及哪些地方必须由你决定。TauLoop 会让 Codex 先列出路径和每段工作的完成标准；通过验证后留下 checkpoint，再接着推进下一段。

```text
用 TauLoop 持续推进这个 repo，直到 xxx 完成。
自己拆分任务、逐项验证；需要我决定时再停下来。
```

第二天回来时，你看到的应当是一份可检查的进展，而不是一串需要重新读懂的聊天记录。

### 2. 让一条长命令安静地跑完

下载依赖、配置环境、编译或测试时，真正需要等待的是本地命令，不是 Codex 的聊天窗口。对于步骤明确、能够验证的串行工作，TauLoop 让 Codex 写清执行计划，监督真实进程，并在上一步验证通过后才进入下一步。

```text
用 TauLoop 帮我配置 xxx 环境。
把下载、安装和检查拆成串行步骤；前一步验证通过才开始下一步；不要频繁查看下载进度；全部完成后停在检查点。
```

---

## 想多看一眼？

你不需要管理 TauLoop 的工作流；但当项目重要时，只要会问下面四件事，就能始终知道它在往哪里走。

| 此刻我想知道 | TauLoop 留下什么 | 直接对 Codex 说 |
| --- | --- | --- |
| 项目现在正往哪里走？ | **`plan`** 记录目标、当前阶段和下一步。 | “给我看当前计划和现在正在推进的一步。” |
| 这一小段怎样才算完成？ | **`spec`** 写清范围、完成标准和验证方式。 | “先给我看当前 spec 的完成标准，在我确认后再开始这个 spec。” |
| 换窗口后为什么还能接上？ | **`checkpoint`** 留下刚刚发生的事实；**`memory`** 留下之后仍重要的事。 | “给我看这次 checkpoint，以及项目现在还需要记住什么。” |
| 它在等什么，什么时候会继续？ | **`continuous-work`** 监督有明确命令和验证条件的串行工作。 | “请持续推进到项目完成 xx Feature” |

### TauLoop 的“一圈”

`目标 -> 可检查的一步 -> 验证 -> 留下交接 -> 下一步或你的决定`

它不是让 Codex 无限循环；它让一次工作能留下证据地走完一圈。

> [!NOTE]
> 上面这些记录都留在项目里。有人把它叫作 harness；对你来说，它就是不依赖某一个聊天窗口的项目工作记录。

## 它不会做什么

> [!IMPORTANT]
> **先验证，再继续。** TauLoop 的目标是让工作可检查地结束，不是让 Codex 无边界地一直跑下去。

- 不会在电脑重启或终端关闭后神奇地继续运行。
- 不会把 heartbeat 当作成功证明。
- 不会因为测试样例通过，就声称你的 CUDA、GPU 或仿真器已经可用。
- 不会替你决定权限、费用、不可逆修改，或验证失败后的下一步。

---

## 手动安装

上面的自然语言方式是推荐路径。只有当 Codex 请你手动安装时，才需要下面三行：

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

安装后，Codex 会发现 TauLoop skill。若你的环境没有把 `~/.codex/bin` 加入 `PATH`，按 Codex 的提示处理即可。

## 更多内容

- [第一次使用](assets/docs/first-use.md)
- [完整使用手册](assets/docs/user-manual.md)
- [安全策略](SECURITY.md)
- [贡献指南](CONTRIBUTING.md)

使用 [MIT License](LICENSE)。
