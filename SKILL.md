---
name: tau-loop
description: "Use when a repository needs a lightweight, file-backed execution harness: durable specs, verification checkpoints, and a documented long-task convention. One command (`tau init`) bootstraps the skeleton; natural language is enough everywhere else."
metadata:
  license: MIT
  repository: https://github.com/TTT-qq-TT/tau-loop
---

# TauLoop

TauLoop gives a repository a lightweight, file-backed execution harness with one command: `tau init`. After that, the workflow is pure convention documented in the project's `AGENTS.md` — no daemon, no state machine, no script execution layer. Long-running work is decoupled from the session by the OS (`systemd-run --user` on Linux when available, else `nohup`/`screen`) and watched by two modes: short tasks (≤5h) are polled in the foreground with a backup inspection timer, long/unattended work hands the watch to a shift agent — a timer (systemd --user / launchd / self-loop, agent-probed) launches headless inspection rounds per `.harness/templates/shift-agent.md`; the only mechanical guards are the packaged hooks and check scripts. On a DeepSeek Harness host the convention is the DSH native path instead: launch the script as a background job (`run_in_background: true`), end the turn, and DSH wakes the session on completion/failure/interruption so the agent continues in the foreground — no polling, no timers (see `AGENTS.md` → Long-Running Tasks → DSH native path).

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
- Long-running work follows the `Long-Running Tasks` section of `AGENTS.md`. On a DeepSeek Harness host use the **DSH native path**: one script as a background job (`run_in_background: true`), record the job id in the shift-status section, end the turn, and continue in the foreground when DSH wakes you on completion/failure/interruption. On other hosts: plan as a spec, pick a mode (short → foreground watch + backup timer; long/unattended → shift agent), launch decoupled (`systemd-run --user` preferred on Linux, else `nohup`/`screen`), write the shift-status section (incl. `status_file`), and let each headless inspection round read the status file, check the log and process, fix what it safely can, update state, then close out with verification evidence.
- Window switch follows the `Active Window-Switch` section of `AGENTS.md`: on "please hand off to the next window", decide the intent, confirm spec/plan/memory are current, write `.harness/handoffs/<id>.md`, and give the user a short launch line (≤5 lines, intent + handoff path + next action).
- Bug triage follows the `Debug Triage: Research First` section of `AGENTS.md`: research official docs, the upstream repo (source + issues), the community, and papers (for research projects) before fixing — never blind-fix; record the evidence in the spec's Debug Evidence section per `.harness/templates/debug-triage.md`.
- Close out a task with `.harness/hooks/pre-closeout.sh`; `verify.sh` checks doc freshness, task state, and (in the source repo) that packaged assets cannot drift.

## Boundaries

- TauLoop does not run your commands for you and has no daemon or event system. Long tasks are owned by the OS and visited periodically by the agent.
- A running process is not success; completion requires real verification evidence.
- `tau` has exactly one command today: `tau init` (+ `--help`). Everything else is convention, not command surface.
- Review every spec and its verification before advancing. Stop for genuine human decisions: new permissions, spending, irreversible actions, failed verifiers, unmet dependencies, or an explicit review request.

Read `assets/docs/first-use.md` (简体中文) or `assets/docs/first-use.en.md` (English) for onboarding, and `assets/docs/user-manual.md` / `assets/docs/user-manual.en.md` for complete operating guidance.
