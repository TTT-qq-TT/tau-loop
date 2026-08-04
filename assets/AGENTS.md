# AGENTS.md

## Startup

Read in this order:
1. `.codex/memory.md`
2. `.codex/plan.md`
3. Read the active task spec from `.codex/specs/` when `.codex/plan.md` points to one.

Read `.codex/brief.md` only when the task needs stable project foundation:
- product scope
- architecture
- technology choices
- onboarding into an unfamiliar area

Read `.codex/verification.md` when you need repo-level validation rules or when closing out a task.
Read only the matching file under `.codex/verification-profiles/` when the task needs a detailed checklist.

Read `.codex/failure-log.md` when the task resembles a previous failure mode, or when a new reusable failure was discovered.

Read `.codex/state/README.md` only when the repo is using continuous-work state or when you need the control-plane command surface.

Do not read by default:
- `.codex/report.md`

Read `.codex/report.md` only when the task needs prior experiments, audit trail, design history, or regression context.

## Context Tiers

- Quick task:
  Read `.codex/memory.md` only.
- Standard task:
  Read `.codex/memory.md`, `.codex/plan.md`, and the active spec when one exists.
- Deep task:
  Read `.codex/memory.md`, `.codex/plan.md`, the active spec, `.codex/brief.md`, `.codex/verification.md`, and only the relevant section of `.codex/report.md`.

## Workflow

- Keep threads scoped to one subtask.
- For non-trivial work, create or update a task spec before code changes.
- For non-trivial work, run `.codex/hooks/pre-task.sh` after shaping the task when hook entrypoints are installed.
- Treat `Allowed files` in the spec as the current change boundary.
- If scope changes, update the spec before continuing.
- Record verification in the spec before marking the task done.
- Before marking a non-trivial task done, run `.codex/hooks/pre-closeout.sh` when hook entrypoints are installed.
- Treat repeated compaction as a warning sign, not normal workflow.
- Before ending a thread or switching scope, update `.codex/memory.md` and `.codex/plan.md`.
- Update the active spec before ending a thread if task-local state changed.
- Update `.codex/failure-log.md` when the task exposed a reusable failure or prevention.
- Update `.codex/report.md` only when the information is worth preserving as durable history.

## Checkpoint Rule

If the current thread has compacted once and is growing again, checkpoint and start a fresh thread instead of relying on another compaction.

## Working Agreement

- `.codex/memory.md` is the current source of truth.
- `.codex/brief.md` is stable project foundation and is read only when needed.
- `.codex/plan.md` is the active execution plan.
- `.codex/specs/*.md` are task execution contracts.
- `.codex/verification.md` defines repo-level validation defaults.
- `.codex/verification-profiles/*.md` hold task-type specific checklists and are read only on demand.
- `.codex/state/README.md` describes the packaged continuous-work runtime layer and activation path.
- `.codex/failure-log.md` stores reusable failures and prevention changes.
- `.codex/report.md` is historical record and is not startup context.

## Large Repos

If this repository has clearly separate subsystems, add local `AGENTS.md` files inside those subdirectories with more specific guidance. Keep the root file short.
This follows the emerging hierarchical AGENT/AGENTS pattern used by multi-agent tooling.
