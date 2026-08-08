<h1 align="center">
  <img src="docs/images/tauloop-mark.png" alt="" width="48" height="48" valign="middle"> <strong>τ-Loop</strong>
</h1>

<p align="center">
  <strong>TauLoop</strong> · τ = 2π: one complete turn, not an endlessly growing chat.
</p>

<p align="center">
  You name the goal. The agent shapes the work, verifies it, and leaves the next step behind.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4C430?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9 or later">
  <img src="https://img.shields.io/badge/agents-Codex%20%C2%B7%20Claude%20%C2%B7%20CodeWhale-10A37F?style=flat-square" alt="Agent skills for Codex, Claude, and CodeWhale">
  <img src="https://img.shields.io/badge/macOS%20%C2%B7%20Ubuntu%20%C2%B7%20Windows-supported-4C8BF5?style=flat-square" alt="macOS, Ubuntu, and Windows supported">
</p>

<p align="center">
  <strong>English</strong> · <a href="README.md#chinese">简体中文</a>
</p>

<p align="center">
  <a href="#start-with-one-sentence">Start with one sentence</a> · <a href="#how-it-works">How it works</a> · <a href="#why-you-can-trust-it">Why you can trust it</a> · <a href="#two-things-it-is-especially-good-at">Two scenarios</a> · <a href="#what-it-will-not-do">Limits</a> · <a href="#manual-install">Manual install</a>
</p>

<p align="center">
  <img src="docs/images/tauloop-readme-cover.png" alt="TauLoop: one complete turn, continuing forward" width="960">
</p>

---

>You give the agent a goal before bed. The next morning, it is stuck at the very first step, waiting for a decision that should never have been yours.
>TauLoop leaves the plan, verification results, and next step in the project, so the work is not trapped in one chat.

### If any of this sounds like you:
  - You are new to agents and do not know how to get started with a workflow.
  - Terms like harness engineering and loop engineering are overwhelming, and you do not know how to actually use them.
  - You have seen plenty of workflow skills, and they all feel too heavy.

Give TauLoop a try — it is light and capable, everything you do not need has been cut, and it only solves the pain points.

---

## Start with one sentence

> [!TIP]
> **First time here?** You do not need to learn commands, file layouts, or agent workflows. Send the agent the text below with this repository link, then replace `xxx` with your goal.

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project forward to xxx.

Keep going when you can verify the work yourself; stop only when a real decision is mine.
```

The agent installs TauLoop and prepares the project records it needs. You do not have to memorize commands or understand `spec`, `checkpoint`, or `harness` first.

To review the route before work begins, add:

```text
Show me only the plan and the definition of done for each part. Wait for my approval before starting.
```

---

## How it works

TauLoop's usage fits in one sentence: **state the goal, and let the agent break it into checkable pieces of work.**

```text
You state the goal
  -> the agent writes a spec (what changes, what counts as done, how to verify)
  -> executes against the spec and closes with evidence, not with "it works"
  -> leaves a checkpoint and moves to the next piece
  -> long-running tasks are owned by the OS; the agent checks periodically, without occupying the chat
```

Four words are all you need to remember:

- **spec**: the contract for one piece of work — what changes, what counts as done, how to verify. When the scope changes, update the spec first.
- **checkpoint**: the state left after a piece of work — what just happened, where the evidence is, what comes next.
- **memory**: facts the project still needs to remember — not a chat transcript, but conclusions the next agent needs.
- **long-running tasks**: slow work like downloads, builds, and training. The OS owns the process; the agent wakes periodically to check instead of polling.

### TauLoop's "one turn"

`goal -> checkable step -> implementation -> verification -> checkpoint -> next step or your decision`

It does not make the agent loop forever. It lets one unit of work complete a whole turn with evidence.

---

## Why you can trust it

**Minimal.** One command, `tau init`. After that, no daemon, no state machine, no command surface to memorize. The rules live in the project's `AGENTS.md`; everything else is convention.

**Files are the truth.** The plan, verification results, and next step live in project files (`.harness/`), not in any single chat. A new window, a different agent, or the next day all read the same facts.

**Mechanical backstop.** A thin layer of hooks and check scripts runs before a task starts and before it is marked done: is the spec complete? is verification recorded? "The process is alive" is not "the task is done" — success always requires work that actually completed and passed verification.

---

## Three things it is especially good at

### 1. Move a project to xxx

You do not need to know every small task up front. State the outcome you need and the places where only you should decide. TauLoop has the agent first lay out the path and the completion criteria for each piece; after verification, it leaves a checkpoint and moves on.

```text
Use TauLoop to keep moving this repo until xxx is complete.
Break down the work and verify each piece yourself; stop only when you need my decision.
```

When you return the next day, you should find inspectable progress, not a long chat you have to understand again.

### 2. Let a long command finish quietly

When dependencies are downloading, an environment is being configured, or a build or test is running, it is the local command that needs to wait, not the agent's chat window. For serial work with explicit steps and verification, TauLoop has the agent write the execution plan, supervise the real process, and start the next stage only after the previous one passes.

```text
Use TauLoop to configure the xxx environment.
Split downloading, installation, and checks into serial stages; start the next stage only after the previous one verifies; do not frequently inspect download progress; stop at a checkpoint when everything is complete.
```

### 3. Hand off to a fresh window when it is getting full

When the context window is nearly full, or you want to separate discussion from execution, just say:

```text
Please hand off to the next window.
```

The agent packs up the handover (intent, progress, evidence, settled decisions), and gives you one short launch line. Paste it into a fresh window and it continues seamlessly — no re-explaining.

---

## What it will not do

> [!IMPORTANT]
> **Verify, then continue.** TauLoop is meant to finish work in a checkable way, not let the agent run without boundaries.

- It will not magically continue after a computer restart or terminal close.
- It will not overclaim that your CUDA, GPU, or simulator works just because a smoke test passes.
- It will not make decisions about permissions, spending, irreversible changes, or what to do after verification fails.

---

## Manual install

The natural-language path above is recommended. You only need these three lines when the agent asks you to install it manually:

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

After installation, the agent discovers the TauLoop skill. If your environment does not put `~/.codex/bin` on `PATH`, follow the agent's prompt.
`~/.codex` is the default location for Codex environments. Other agent environments can install elsewhere with `python3 install.py --codex-home <dir>` and point `tau` there via `TAU_LOOP_CODEX_HOME`.

## Learn more

- [First-use guide](assets/docs/first-use.en.md)
- [Complete user manual](assets/docs/user-manual.en.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

TauLoop is available under the [MIT License](LICENSE).
