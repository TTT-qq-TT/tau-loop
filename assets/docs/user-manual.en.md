# TauLoop User Manual

[简体中文](user-manual.md) | **English**

> Hand the goal to your agent. TauLoop makes sure the project keeps a plan, evidence, and a next step.
>
> This is not a "workflow course" you have to memorize. It is a set of records and conventions living inside the project: one piece of work finishes, the next one can continue from it; long commands are owned by the operating system and checked by the agent on a schedule; decisions that are genuinely yours still come back to you.

## Contents

- [Get Started](#get-started)
- [Installation](#installation)
- [Enabling a Project](#enabling-a-project)
- [Working on a Project Day to Day](#working-on-a-project-day-to-day)
- [Letting Long Commands Finish Quietly](#letting-long-commands-finish-quietly)
- [Verification and Hooks](#verification-and-hooks)
- [Safety Boundaries and Human Decisions](#safety-boundaries-and-human-decisions)
- [Command Reference](#command-reference)

---

## Get Started

### The Recommended Way: State the Goal

Send the following to your agent, with the TauLoop repository link, replacing `xxx` with your outcome:

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project to xxx.

Continue on your own when you can verify; stop when I really need to decide.
```

The agent installs TauLoop, decides whether the project is new or existing, creates the records it needs, and breaks the work into checkable pieces. You do not need to know what `spec`, `checkpoint`, or `harness` mean first.

If you want to see the plan first, add:

```text
Only show me the plan and the definition of done for each part first; start after I confirm.
```

## Installation

Requires Python 3.9+; currently supports macOS and Ubuntu.

### Install by Natural Language (recommended)

Tell the agent "please install TauLoop" or just give the repository link. The agent downloads the repo and runs the installer — no terminal commands needed from you. After that, the `tau` command is available.

### Terminal Install

```bash
git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop /tmp/tau-loop-install
python3 /tmp/tau-loop-install/install.py
rm -rf /tmp/tau-loop-install   # optional cleanup
```

The installer places the skill under `~/.codex/skills/tau-loop/` and the `tau` command under `~/.codex/bin/`. If the terminal cannot find `tau`, add `~/.codex/bin` to your `PATH`, then check:

```bash
tau --help
```

Uninstall:

```bash
python3 ~/.codex/skills/tau-loop/install.py --uninstall
```

## Enabling a Project

### Enable by Command

```bash
cd your-project
tau init --root .
```

`tau init` only creates the missing skeleton: a root `AGENTS.md` plus `.harness/` (spec templates, hooks, check scripts, verification profiles). It never overwrites existing user files.

### Enable by Natural Language

Inside the project, tell the agent "I want to manage this project with TauLoop". The agent runs `tau init --root .` itself, explains what was prepared, and waits for your goal.

### Migrating an Existing Project

If the project still uses the legacy `.codex/` directory, migrate it to `.harness/` once with the [migration guide](migration-from-codex.md).

## Working on a Project Day to Day

After enabling, the project's `AGENTS.md` is the convention itself:

1. **Startup order**: the agent reads `.harness/memory.md`, then `.harness/plan.md`, then the active task spec the plan points to. Architecture context, verification detail, and history are loaded only when the task needs them.
2. **Spec first**: non-trivial work starts as a spec (`.harness/specs/<name>.md` — goal, boundaries, allowed files, acceptance) before any code changes. The spec is the durable contract for the task.
3. **Execute and verify**: work through the spec, record verification evidence for each part, and update the spec checklist.
4. **Before switching tasks or ending a thread**: update `.harness/memory.md` and `.harness/plan.md` so the next piece of work can continue.

## Letting Long Commands Finish Quietly

Long-running commands (large downloads, builds, data assembly) are **owned by the operating system, not the conversation**. This is the `Long-Running Tasks` convention in `AGENTS.md`; the agent works in this rhythm:

1. Turn the long command into a script and launch it decoupled with `nohup` or `screen`; record the PID and log path.
2. The agent `sleep`s in-session (coarse intervals, no tight polling).
3. On wake it reads the log tail, checks the process, and compares artifacts; normal progress means a short status note and another sleep, failure means reading the log, fixing the script, and relaunching.
4. Completion is a stage self-check plus artifact evidence (checksums, test output) — not "the process is still alive".

No daemon, state machine, or script execution layer is needed — the OS owns the process and the agent is a periodic visitor.

## Verification and Hooks

- `.harness/hooks/pre-task.sh`: run before starting a non-trivial task; checks doc freshness and task state.
- `.harness/hooks/pre-closeout.sh`: run before closing out a task; checks the spec is complete and verification is recorded.
- `.harness/hooks/verify.sh`: full verification (doc freshness + task state +, in the source repo, that packaged assets cannot drift).
- `assets/tools/check_markdown_links.py`: checks documentation link validity.

Hooks are the only mechanical guard; everything else relies on agent discipline and evidence.

## Safety Boundaries and Human Decisions

- TauLoop has no daemon and does not run your commands for you. Long tasks are owned by the OS and checked periodically by the agent.
- A running process or fresh log output is not completion. Completion requires real verification evidence.
- The command surface is exactly `tau init` (+ `--help`). Everything else is convention, not command.
- The agent stops for decisions that are yours: new permissions, spending, irreversible actions, failed verifiers, unmet dependencies, or an explicit review request.

## Command Reference

| What | How |
|---|---|
| Install TauLoop (natural language) | Tell the agent "please install TauLoop" |
| Install TauLoop (terminal) | `python3 install.py` |
| Uninstall | `python3 install.py --uninstall` |
| Enable a project (command) | `tau init --root .` |
| Enable a project (natural language) | "I want to manage this project with TauLoop" |
| Migrate a legacy project | `migration-from-codex.md` |
| Help | `tau --help` |
| Full verification | `.harness/hooks/verify.sh` |
