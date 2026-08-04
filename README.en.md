<h1 align="center"><strong>τ-Loop</strong></h1>

<p align="center">
  <strong>TauLoop</strong> · τ = 2π · One complete turn, not an endless chat.
</p>

<p align="center">
  You name the goal. Codex breaks it down, verifies the work, and leaves a record behind.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4C430?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8 or later">
  <img src="https://img.shields.io/badge/Codex-Skill-10A37F?style=flat-square" alt="Codex Skill">
  <img src="https://img.shields.io/badge/macOS%20%2B%20Ubuntu-supported-4C8BF5?style=flat-square" alt="macOS and Ubuntu supported">
</p>

<p align="center">
  <a href="README.md">中文</a>
</p>

<p align="center">
  <a href="#what-it-keeps-safe">What it keeps safe</a> · <a href="#start-with-codex">Start with Codex</a> · <a href="#what-to-say">What to say</a> · <a href="#five-useful-words">Five useful words</a> · <a href="#manual-install">Manual install</a>
</p>

---

## What it keeps safe

Giving Codex a task should not mean waking up to discover that it stopped halfway through. TauLoop keeps waiting work, project memory, and the next action in the repository, rather than in one chat that keeps growing.

### Let long-running work wait quietly

For downloads, installation, builds, or tests with explicit commands and completion checks, continuous-work v2 supervises the real local process, records low-noise health evidence, and starts the next stage only after the prior verifier passes. Codex does not need to keep returning to reread a log.

### Let a fresh context pick up the work

After each piece of work, TauLoop writes a checkpoint: what happened, where the evidence is, and what comes next. When work moves to a new session or a clean context, Codex receives those facts instead of an entire old chat.

### Let the project remember its progress

The root `AGENTS.md` tells Codex where to start. `.codex/plan.md` says what is being moved forward now. `.codex/memory.md` keeps the facts that still matter. Together, they are shared project memory rather than knowledge trapped in one window.

> [!NOTE]
> TauLoop keeps a supervised long-running stage waiting and verifying while the local supervisor is still running. It is not a background service that wakes up after a reboot or closed terminal.

---

## Start with Codex

> [!TIP]
> **First time here?** You do not need to learn commands or project structure first. Let Codex read TauLoop, then tell it what you want to achieve.

Send the text below, together with this repository URL, to Codex. You do not need to memorize commands.

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to manage the current project.

Briefly explain how I should use TauLoop.
```

Codex installs the skill and explains, in plain language, how it helps manage the project. It creates specs, starts work, and writes checkpoints only after you give it a concrete goal.

<!-- Screenshot TODO: A real Codex conversation receiving the prompt above.
Suggested path: docs/images/01-tell-codex-the-goal.png -->

## What to say

Replace the goal and send one of these messages.

### Scenario 1: Move a project forward

```text
Use TauLoop to keep moving this repo until v1 is complete. Break down the work and verify each part. Stop only when you need my decision.
```

### Scenario 2: Move a known set of tasks forward

```text
Use TauLoop to create spec1 through spec4 and keep moving until they are all complete. Leave a checkpoint after every spec.
```

### Scenario 3: See the plan before work begins

```text
Use TauLoop to create specs for this goal. Show me only the plan and the definition of done for each spec. Wait for my approval before making changes.
```

### Scenario 4: Set up a long environment

```text
Use TauLoop to set up Python, PyTorch, and a simulator environment.
Split downloads, installation, and checks into serial stages. Start a stage only after the prior one verifies. Do not keep polling download progress. Stop at a checkpoint when everything is ready.
```

<!-- Screenshot TODO: A real terminal or Codex view showing one supervised stage and concise health evidence.
Suggested path: docs/images/02-a-long-task-is-running.png -->

---

## Five useful words

You do not need to learn a new system. These are the only words worth knowing.

| Word | Meaning | What to say to Codex |
| --- | --- | --- |
| Task | The outcome you want, such as "take this project to v1." | "Take this project to v1." |
| Spec | A small job card: what to do, what not to do, and how to know it is done. | "Create specs for this goal first." |
| Harness | The project's shared notebook. It keeps plans, evidence, and problems outside an ever-growing chat. | "Use TauLoop to manage this project." |
| Checkpoint | The factual record left after a piece of work. A new Codex session can continue from it. | "Write a checkpoint when this is done." |
| Long-running work | Serial work that takes time: downloading, installing, training, or testing. | "Do not poll; verify before continuing." |

Codex creates the files and calls the tools for you. You can always ask it to explain the current spec, progress, or checkpoint.

---

## What happens in one turn

TauLoop makes work into a turn that can actually finish:

1. Break the goal into small, checkable specs.
2. Complete the current spec and run its agreed verification.
3. Write a checkpoint after it passes, then start the next spec or stop for review.

It is not an infinite agent loop. A live process or a heartbeat is not proof that the work is done. Without verification, the next step is not unlocked.

<!-- Screenshot TODO: A real checkpoint or review view after a verified task finishes.
Suggested path: docs/images/03-verified-checkpoint.png -->

---

## Long-running work

For long downloads, environment setup, or a sequence of commands that must run in order, use the long-environment prompt above. TauLoop has Codex write and review an execution plan, supervise the real process, record quiet health evidence, and advance only after verification passes.

> [!NOTE]
> You do not need to know what a `run contract` is. It is the record Codex uses to state commands, deadlines, permissions, and verification.

When you want to inspect it, say:

```text
Before the long task starts, show me the execution plan, how each stage is verified, and every point where it will wait for my confirmation.
```

## What it does not do

> [!IMPORTANT]
> **Verify, then continue.** TauLoop is meant to end work with evidence, not keep an agent running forever.

- It does not magically survive a reboot or a closed terminal.
- It does not treat a heartbeat as proof of success.
- It does not claim that a fixture proves CUDA, a GPU, or a simulator works in your project.
- It does not make permission, spending, irreversible-change, or recovery decisions for you.

---

## Manual install

The natural-language path above is recommended. Use these commands only when Codex asks you to install it manually:

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

After installation, Codex discovers the TauLoop skill. If `~/.codex/bin` is not on your `PATH`, follow Codex's instructions.

## Learn more

- [Project workflow and upgrades](assets/docs/project-workflow.md)
- [First-use guide for Codex](assets/docs/first-use.en.md)
- [Full guide to long-running work](assets/docs/continuous-work-v2.md)
- [Legacy control-plane reference](assets/docs/continuous-work-v1.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

TauLoop is available under the [MIT License](LICENSE).
