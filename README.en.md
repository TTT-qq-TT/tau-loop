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
  <strong>English</strong> · <a href="README.md#chinese">简体中文</a>
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
