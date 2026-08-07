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
- For non-trivial work, run `.harness/hooks/pre-task.sh` after shaping the task when hook entrypoints are installed.
- Treat `Allowed files` in the spec as the current change boundary.
- If scope changes, update the spec before continuing.
- Record verification in the spec before marking the task done.
- Before marking a non-trivial task done, run `.harness/hooks/pre-closeout.sh` when hook entrypoints are installed.
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

Long-running work (large downloads, builds, data assembly) is done by the agent directly in the session, with the actual work process decoupled from the agent session so it survives sleep and window changes.

Core pattern:

1. **Plan**: write the task as a spec, then break the work into stages with commands, self-checks, and expected artifacts. Record the plan in `.harness/plan.md` and the current stage in the active spec.
2. **Launch decoupled**: start the long command so it is owned by the OS, not the session:
   - `nohup bash scripts/stage.sh > logs/stage.log 2>&1 &`
   - or `screen -dmS stage bash scripts/stage.sh` when you need to re-attach interactively.
   - Record the PID, log path, and expected artifacts in `.harness/plan.md`.
3. **Sleep**: wait in-session with `sleep` (verified zero-output, near-zero token cost). Do not poll in a tight loop; a coarse interval (e.g. 30-60 min) is fine.
4. **Wake and check**: read the log tail, check the process (`ps -p <pid>`), and compare artifacts. All checks are plain foreground commands in the session.
   - Normal progress → record a short status note and sleep again.
   - Failure → read the log, fix the stage script, relaunch decoupled, and return to step 3.
5. **Verify completion**: run the stage self-check and confirm expected artifacts exist. Record evidence (checksums, test output) in `.harness/plan.md` and the spec.
6. **Close out**: run `.harness/hooks/pre-closeout.sh`; the hook checks that the spec is complete and that declared artifacts are present.

The agent owns the loop: it decides when to sleep, what to check, and what to fix. There is no separate executor, daemon, or event system.

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

## Current Migration Context (2026-08-07)

This repository (tau-loop) is being consolidated into the single source of truth
for the harness. The active spec is `.harness/specs/tau-loop-convergence-and-productization.md`
(ready). Read `.harness/memory.md` and `.harness/plan.md` before doing any work.
Key decisions already frozen: directory is `.harness/` (not `.codex/`), command
surface is a single `tau init`, no cproj family, install via `install.py` or
natural-language agent setup. The upstream reference repo (tt-workflow) has been
overhauled (de-cw, agent-led long tasks as doc-only) and is frozen/archived;
consult its git history or `.harness/memory.md` for that background.
