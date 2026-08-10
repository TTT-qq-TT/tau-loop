# AGENTS.md

## Startup

Read in this order:
1. `.harness/memory.md`
2. `.harness/plan.md`
3. Read the active task spec from `.harness/specs/` when `.harness/plan.md` points to one.

Read `.harness/brief.md` only when the task needs stable project foundation:
- product scope
- architecture
- technology choices
- onboarding into an unfamiliar area

Read `.harness/verification.md` when you need repo-level validation rules or when closing out a task.
Read only the matching file under `.harness/verification-profiles/` when the task needs a detailed checklist.

Read `.harness/failure-log.md` when the task resembles a previous failure mode, or when a new reusable failure was discovered.

Do not read by default:
- `.harness/report.md`

Read `.harness/report.md` only when the task needs prior experiments, audit trail, design history, or regression context.

## Context Tiers

- Quick task:
  Read `.harness/memory.md` only.
- Standard task:
  Read `.harness/memory.md`, `.harness/plan.md`, and the active spec when one exists.
- Deep task:
  Read `.harness/memory.md`, `.harness/plan.md`, the active spec, `.harness/brief.md`, `.harness/verification.md`, and only the relevant section of `.harness/report.md`.

## Workflow

- Keep threads scoped to one subtask.
- For non-trivial work, create or update a task spec before code changes.
- For non-trivial work, run the pre-task hook after shaping the task when hook entrypoints are installed: `.harness/hooks/pre-task.sh` on bash hosts, `.harness/hooks/pre-task.py` (via `python`/`py -3`) on Windows.
- Treat `Allowed files` in the spec as the current change boundary.
- If scope changes, update the spec before continuing.
- Record verification in the spec before marking the task done.
- Before marking a non-trivial task done, run the pre-closeout hook when hook entrypoints are installed: `.harness/hooks/pre-closeout.sh` on bash hosts, `.harness/hooks/pre-closeout.py` (via `python`/`py -3`) on Windows.
- Treat repeated compaction as a warning sign, not normal workflow.
- Before ending a thread or switching scope, update `.harness/memory.md` and `.harness/plan.md`.
- Update the active spec before ending a thread if task-local state changed.
- Update `.harness/failure-log.md` when the task exposed a reusable failure or prevention.
- Update `.harness/report.md` only when the information is worth preserving as durable history.

## Specs

- A `spec` (`.harness/specs/*.md`) is the task's durable contract: goal, boundaries, allowed files, acceptance. Start every task as a spec.
- Rule: always write the task as a spec first. A spec is the single source of truth for what the task must do; keep it updated as scope changes.
- Long machine-supervised command sequences (download, build, assemble, train, ...) are executed by the agent in-session, not handed to an external runner. See `Long-Running Tasks` below.

## Long-Running Tasks

Long-running work (large downloads, builds, data assembly, model training) is **owned by the OS**, not the agent session. The agent decouples the process (`nohup`/`screen`/`Start-Process`), records state in `.harness/plan.md`, and then either checks in manually or — for unattended work — hands the watch to a **shift agent**: a system timer periodically launches a short headless inspection round that reads state, checks progress, fixes what it safely can, and writes the outcome back to the state file.

Core pattern:

1. **Plan**: write the task as a spec, then break the work into stages with commands, self-checks, and expected artifacts. Record the plan in `.harness/plan.md` and the current stage in the active spec.
2. **Launch decoupled**: start the long command so it is owned by the OS, not the session:
   - `nohup bash scripts/stage.sh > logs/stage.log 2>&1 &`
   - or `screen -dmS stage bash scripts/stage.sh` when you need to re-attach interactively.
   - On native Windows (PowerShell), use `Start-Process` instead:
     ```powershell
     Start-Process python -ArgumentList "scripts/stage.py" -NoNewWindow -RedirectStandardOutput logs/stage.log -RedirectStandardError logs/stage.err -PassThru
     ```
     `screen` has no native Windows equivalent — either drop re-attach or run the stage under WSL/Git Bash.
   - Record the PID, log path, and expected artifacts in `.harness/plan.md` (the shift-status section, fields per `.harness/templates/shift-agent.md`).

### Shift Mode (unattended, recommended for hours-long work)

When no one will watch the task (overnight training, long builds), set up a periodic inspection instead of sleeping in-session:

1. **Write the shift-status section** in `.harness/plan.md` (`task`, `cmd`, `process`, `log`, `artifact`, `acceptance`, `pid`, `status`, `next_check_at`; format per `.harness/templates/shift-agent.md`).
2. **Arm a system timer** (OS-level; survives crashes by design — each launch is a fresh process):
   - cron, headless single-shot mode: `*/15 * * * * cd /path/to/project && <agent> exec --prompt .harness/templates/shift-agent.md`
   - examples: `claude -p "$(cat .harness/templates/shift-agent.md)"` / `codex exec --prompt-file .harness/templates/shift-agent.md`
   - Windows: Task Scheduler launching the same command. Keep the machine awake while unattended.
3. **Each inspection round** (a fresh headless agent): reads the shift-status section → checks process/log/artifacts → decides (continue / fix & relaunch / research & fix / finish & wrap up) → updates the section → exits. The template constrains behavior: read-only by default, no blind retries, backup + self-check before relaunch, hand over with a case file only when a real decision is needed.
4. **Check results later**: read the shift-status section — `done` (acceptance summary), `need_decision` (case notes), `fixed` (repair history), or `running` (still going). Never trust a running process as success; completion requires verified artifacts.

Manual check-in works the same way when someone is watching: `ps -p <pid>`, log tail, artifact compare — all plain foreground commands — then record a short status note.

The agent owns the loop: it decides what to check, what to fix, and when to stop. There is no separate executor, daemon, or event system — the timer is the OS's, and the state file is the truth. (The handoff mechanics mirror `Active Window-Switch` below: write state, exit, next round resumes from the file.)

## Active Window-Switch

When the context window is nearly full, or you want to separate discussion from execution, offer:

> "Please hand off to the next window."

Then, in order:

1. **Decide the intent** (required): state in one line what the next window should do, plus one line of why. Reference intents: *continue running* / *decision→execution separation* / *fresh review* / *explore a branch*. If none fit, decide yourself — intent is a declaration, not a menu.
2. **Confirm the facts are current**: `spec` / `plan` / `memory` are maintained as usual; just make sure they reflect the latest state.
3. **Write the handoff** to `.harness/handoffs/<id>.md`, carrying only:
   - `intent` + one-line reason
   - `spec_path` — the current contract
   - `progress` — completed stages, current stage, artifacts
   - `evidence` — verified receipts
   - `constraints` — decisions, allowed_files, next_action
   - Never chat history.
4. **Produce the prompt** for the user to copy: ≤5 lines, no role-play boilerplate. Three elements: intent in one line, handoff path, one action line derived from the intent.

The user opens a fresh session and pastes the prompt. The new window reads AGENTS.md, then the handoff, verifies its listed evidence before acting, and follows the intent — no further explanation needed.

Hand off at semantic boundaries (stage done, spec switch, decision frozen). Do not hand off for short tasks or when the window is not full — official compact is enough there.

## Checkpoint Rule

If the current thread has compacted once and is growing again, checkpoint and start a fresh thread instead of relying on another compaction.

## Working Agreement

- `.harness/memory.md` is the current source of truth.
- `.harness/brief.md` is stable project foundation and is read only when needed.
- `.harness/plan.md` is the active execution plan.
- `.harness/specs/*.md` are task execution contracts.
- `.harness/verification.md` defines repo-level validation defaults.
- `.harness/verification-profiles/*.md` hold task-type specific checklists and are read only on demand.
- `.harness/failure-log.md` stores reusable failures and prevention changes.
- `.harness/report.md` is historical record and is not startup context.

## Large Repos

If this repository has clearly separate subsystems, add local `AGENTS.md` files inside those subdirectories with more specific guidance. Keep the root file short.
This follows the emerging hierarchical AGENT/AGENTS pattern used by multi-agent tooling.
