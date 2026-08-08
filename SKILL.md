---
name: tau-loop
description: "Use when a repository needs a lightweight, file-backed execution harness: durable specs, verification checkpoints, and a documented long-task convention. One command (`tau init`) bootstraps the skeleton; natural language is enough everywhere else."
metadata:
  license: MIT
  repository: https://github.com/TTT-qq-TT/tau-loop
---

# TauLoop

TauLoop gives a repository a lightweight, file-backed execution harness with one command: `tau init`. After that, the workflow is pure convention documented in the project's `AGENTS.md` — no daemon, no state machine, no script execution layer. Long-running work is decoupled from the session by the OS (`nohup`/`screen`) and checked periodically by the agent; the only mechanical guards are the packaged hooks and check scripts.

## First Use — Natural-Language Install (装法一)

The user should not need to install anything by hand. When the user points at TauLoop (repository URL or skill name) and asks to use it, the agent installs it:

1. Read the repository instructions from <https://github.com/TTT-qq-TT/tau-loop>.
2. Download the package to a temp directory:
   ```bash
   git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop /tmp/tau-loop-install
   ```
3. Run the installer (it places the skill under `~/.codex/skills/tau-loop/` and the `tau` command under `~/.codex/bin/`):
   ```bash
   python3 /tmp/tau-loop-install/install.py
   ```
   If the target agent environment uses a different skill directory, pass `--codex-home <dir>` to the installer; `tau` reads the same location via the `TAU_LOOP_CODEX_HOME` environment variable.
4. Confirm `tau --help` works (and `~/.codex/bin` is on PATH); optionally remove the temp clone:
   ```bash
   rm -rf /tmp/tau-loop-install
   ```
5. Continue from the user's stated goal.

Run the install steps only when the user asked for installation or that action is permitted. Report any network or permission blocker instead of silently failing. If the agent cannot install, fall back to telling the user the terminal commands for 装法二.

## Terminal Install (装法二)

```bash
cd <checked-out tau-loop repo>
python3 install.py
```

Uninstall: `python3 install.py --uninstall`.

## Enable a Project — Command (用法一)

```bash
cd <project>
tau init --root .
```

Creates the missing skeleton only: `AGENTS.md` plus `.harness/` (spec templates, hooks, check scripts, verification profiles). It never overwrites existing user files.

## Enable a Project — Natural Language (用法二)

The user just says, for example: "我要用 tauloop 管理这个项目". Run `tau init --root .` yourself in the project directory, explain briefly what was prepared, then wait for the goal.

## The Workflow (convention only, after init)

After init, the project's `AGENTS.md` owns the convention:

- Read `.harness/memory.md` then `.harness/plan.md`, then the active task spec.
- Non-trivial work starts as a spec (`.harness/specs/<slug>.md`) before code changes.
- Long-running work follows the `Long-Running Tasks` section of `AGENTS.md`: plan as a spec, launch decoupled (`nohup`/`screen`), sleep in-session, wake and check the log and process, record evidence, then close out.
- Window switch follows the `Active Window-Switch` section of `AGENTS.md`: on "please hand off to the next window", decide the intent, confirm spec/plan/memory are current, write `.harness/handoffs/<id>.md`, and give the user a short launch line (≤5 lines, intent + handoff path + next action).
- Close out a task with `.harness/hooks/pre-closeout.sh`; `verify.sh` checks doc freshness, task state, and (in the source repo) that packaged assets cannot drift.

## Boundaries

- TauLoop does not run your commands for you and has no daemon or event system. Long tasks are owned by the OS and visited periodically by the agent.
- A running process is not success; completion requires real verification evidence.
- `tau` has exactly one command today: `tau init` (+ `--help`). Everything else is convention, not command surface.
- Review every spec and its verification before advancing. Stop for genuine human decisions: new permissions, spending, irreversible actions, failed verifiers, unmet dependencies, or an explicit review request.

Read `assets/docs/first-use.md` (简体中文) or `assets/docs/first-use.en.md` (English) for onboarding, and `assets/docs/user-manual.md` / `assets/docs/user-manual.en.md` for complete operating guidance.
