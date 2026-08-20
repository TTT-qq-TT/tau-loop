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

## Debug Triage: Research First

When you hit a bug (test failure, command error, anomalous log, behavior mismatch, or a user-reported bug), default to **research first, fix second** — no blind fixes (trial-and-error patches, working around the symptom, or changing acceptance criteria to pass). The detailed workflow lives in `.harness/templates/debug-triage.md`; for unattended long-task rounds use `shift-agent.md` instead.

- **Research priority**: ① official docs (current version, matching platform) → ② upstream repo (source + issue tracker; search GitHub with a distinctive fragment of the raw error message, not the whole message) → ③ open-source community (Stack Overflow, similar projects) → ④ papers / arXiv / technical reports (**research projects move this to ②**: research repos, bugs in algorithm/method implementation, or the user declaring a research scenario).
- **Before you fix, you must have**: a minimal reproduction, the raw evidence (error text / stack / log tail), a falsifiable root-cause hypothesis, and a research trail with specific sources (URL / issue # / commit / paper title).
- **Skipping research is allowed only for**: pure formatting/typing/mechanical edits with no behavior change; no network access (then record "not researched" and the residual risk). State the skip in the spec's debug-evidence section.
- **Evidence lands in the spec**: for fix tasks, record 现象 (symptom) / 查证记录 (research trail) / 根因结论 (root cause) / 修复依据 (fix rationale) / 残余风险 (residual risk) in the spec's debug-evidence section; reusable failure modes go into `.harness/failure-log.md`.
- **Hand over instead of fabricating**: when research is exhausted and there is still no fix, stop and hand over (observed / tried / researched / suggested next step) — never invent sources or conclusions.

## Specs

- A `spec` (`.harness/specs/*.md`) is the task's durable contract: goal, boundaries, allowed files, acceptance. Start every task as a spec.
- Rule: always write the task as a spec first. A spec is the single source of truth for what the task must do; keep it updated as scope changes.
- Long machine-supervised command sequences (download, build, assemble, train, ...) are executed by the agent in-session, not handed to an external runner. See `Long-Running Tasks` below.

## Long-Running Tasks

### DSH native path (host = DeepSeek Harness)

In a DeepSeek Harness session the long-running process is watched by DSH itself: launch it as a background job, end the turn, and DSH wakes the session when the job settles — **completion, failure, and interruption all wake you** — then continue in the foreground. No polling loop, no OS timer, no shift agent, no user operation.

1. **Take the goal**: the user gives one sentence of intent; write the task as a spec and record a shift-status section in `.harness/plan.md` (task, command/script, log, status_file, artifact, acceptance).
2. **Package**: put the whole long flow into one script that appends one machine-readable line per step to a status file (`STEP=START|DONE|FAIL model=... exit=...`). One flow = one background job = one wake-up.
3. **Launch**: start the script with `run_in_background: true` (no timeout; the host owns the process), write the job id into the shift-status section, end the turn, and wait.
4. **Wake and continue**: collect the result with `job_output <job_id>`, read the status file, fix what failed (backup → smoke → relaunch), keep working in the foreground on the next stage, and when everything passes acceptance wrap up, update the shift-status section, and report.
5. **Short foreground waits only**: `job_output(job_id, wait: true, timeout_ms: 600000)` blocks up to 10 minutes per call and may be repeated; never block on a long wait — end the turn and let DSH wake you.

DSH discipline:

- One long flow = one script job. Consecutive automatic wake-ups are capped at 3 per owner; put every stage in one script, or bridge stages with a foreground `job_output(wait)`.
- **Do not create a goal while waiting on a background job** — goal rounds auto-open on an idle agent and fight the wait; goals are for continuous-work objectives only.
- A host restart loses background jobs (process-local): for cross-restart unattended work, make the script resumable (status-file driven) and re-invoke the session after restart.
- Everything else stays: research-first debugging, backup + smoke before relaunch, write facts, never fake completion.

### Non-DSH hosts (Claude Code / Codex / other runtimes)

Long-running work (large downloads, builds, data assembly, model training) is **owned by the OS**, not the agent session. The agent decouples the process from the session, records state in `.harness/plan.md`, and then either **watches it in the foreground** (short tasks) or hands the watch to a **shift agent** (long/unattended work): a system timer periodically launches a short headless inspection round that reads state, checks progress, fixes what it safely can, and writes the outcome back to the state file.

**Pick a mode first** (two criteria; decide before launching):

- **Mode A — foreground watch** (short task): a single run ≤1h and total ≤5h, and someone can stay online → watch the status file in the foreground with a polling loop; instant diagnosis beats remote inspection. Prefer A also when a new model/step is integrated for the first time (high chance of needing quick fixes — dtype/path/OOM issues only surface on the first real run).
- **Mode B — shift agent** (long/unattended): total >5h, overnight/cross-day, or no one will watch → arm the timer + headless inspection rounds (Shift Mode below), close the window, verify later.

Core pattern (both modes):

1. **Plan**: write the task as a spec, then break the work into stages with commands, self-checks, and expected artifacts. Record the plan in `.harness/plan.md` and the current stage in the active spec.
2. **Launch decoupled**: start the long command so it is owned by the OS, not the session:
   - **Linux with systemd → `systemd-run --user` (preferred)**: a transient unit, decoupled from any session and process group. `nohup` background processes can be killed with the agent session's process group (observed in practice):
     ```bash
     systemd-run --user --unit=<name> --collect bash -c 'cd <root> && bash scripts/<stage>.sh >> logs/<stage>.log 2>&1'
     systemctl --user is-active <name>   # liveness; use the unit name as `pid` in the shift-status section
     ```
   - **No systemd → `nohup` or `screen`**: `nohup bash scripts/stage.sh > logs/stage.log 2>&1 &`, or `screen -dmS stage bash scripts/stage.sh` when you need to re-attach interactively.
   - **On native Windows (PowerShell) → `Start-Process`**:
     ```powershell
     Start-Process python -ArgumentList "scripts/stage.py" -NoNewWindow -RedirectStandardOutput logs/stage.log -RedirectStandardError logs/stage.err -PassThru
     ```
     `screen` has no native Windows equivalent — either drop re-attach or run the stage under WSL/Git Bash.
   - Record the process handle (PID or systemd unit name), log path, status file, and expected artifacts in `.harness/plan.md` (the shift-status section, fields per `.harness/templates/shift-agent.md`).

### Mode A — Foreground watch (short tasks, verified 2026-08-12)

When you stay online for the duration, do not hand the watch away — watch it yourself:

1. **Write an orchestration script** (recommended): sequential steps; append one machine-readable line per step to a status file (`STEP=START|DONE|FAIL model=... run=... exit=...`); do not abort on a failed step (record FAIL and continue); finish with post-processing (metrics/videos/summary). The status file is the single source of truth read by your polling, the backup timer, and any handover.
2. **Launch via systemd-run** (above), not nohup.
3. **Write the shift-status section** in `.harness/plan.md` — including `status_file` (the orchestration status file) and `mode: foreground`.
4. **Arm a backup timer** (recommended, 15min): a shift-agent inspection round as a safety net — "a second pair of eyes if the foreground dies". It may never fire (the task finishes first); that is fine, that is its job.
5. **Poll in the foreground**: a single bash call running a loop reads the status file and checks the unit — one call can run 10–20 minutes without being cut:
   ```bash
   for i in $(seq 1 10); do
     sleep 120
     grep STEP= logs/<task>.status | tail -2    # progress
     systemctl --user is-active <unit>          # executor alive
   done
   ```
   If a poll loop is interrupted (runtime timeout, window closed), the task is unaffected (OS-owned) — come back and resume reading the status file.
6. **Fix immediately** when a step fails: diagnose from the status file/logs → backup (`cp .bak`) → minimal change → quick self-check (smoke) → relaunch via systemd-run → record in `.harness/failure-log.md`. **Smoke-before-full-run is a hard gate for any new model/step**: dtype/path/memory issues only surface on the first real run.
7. **Close out**: stop the backup timer (`systemctl --user stop shift-<task>.timer && disable`), update memory/plan/spec, deliver the summary.

### Shift Mode (unattended, recommended for hours-long work)

When no one will watch the task (overnight training, long builds), set up a periodic inspection instead of sleeping in-session:

1. **Write the shift-status section** in `.harness/plan.md` (`task`, `cmd`, `process`, `log`, `artifact`, `acceptance`, `headless_cmd`, `timer_type`, `pid`, `status`, `next_check_at`; plus `status_file` when the task has its own machine-readable status file and `mode: shift`; format per `.harness/templates/shift-agent.md`).
2. **Pick a timer — try in order, first that works wins** (the agent decides; probe each, do not assume):
   - **Linux → systemd user timer** (OS-level; survives reboots via `loginctl enable-linger`). Probe and arm:
     ```bash
     export XDG_RUNTIME_DIR=/run/user/$(id -u)   # must be in the SAME Bash call as systemctl
     systemctl --user is-system-running           # if OK, proceed
     ```
     Write `~/.config/systemd/user/shift-<task>.{service,timer}` (service runs the headless inspection command from `headless_cmd`; timer `OnUnitActiveSec=15min`), then `systemctl --user daemon-reload && systemctl --user enable --now shift-<task>.timer`.
     - If `systemctl --user` fails with "Failed to connect to bus", it is almost always the missing `XDG_RUNTIME_DIR` (see the export above) — **not** a broken system. If the user bus genuinely does not exist, one-time `loginctl enable-linger <user>` (a normal user can do this for themselves) makes the user instance persist across reboots.
   - **macOS → launchd user agent** (no setuid restriction on macOS): a `LaunchAgent` plist running the headless inspection command on an interval.
   - **Neither available (e.g. no systemd user instance, or agent shell cannot reach it) → self-loop** (process-level reliability; verified in practice): start a `setsid` background loop that runs the headless inspection command every N minutes and exits when the shift-status section reaches `done`/`need_decision` or the task process disappears:
     ```bash
     setsid bash -c 'while :; do <headless_cmd>; sleep 900; done' > logs/shift-loop.log 2>&1 &
     ```
     Record its PID in `loop_pid` and note the fallback reason in `cron_note`.
   - **Host already configured cron → consume it** (enhancement, optional): if `crontab -l` already has the inspection entry, just use it.
   - Record the choice: `timer_type: systemd-user | launchd | selfloop | cron` and a `cron_note` explaining why (e.g. "crontab blocked in agent env by NoNewPrivs → systemd user timer").
   - **Never try to run `crontab` or `sudo` from the agent shell on Linux**: the agent's command layer hard-sets `PR_SET_NO_NEW_PRIVS` (process hardening, not a config flag), so setuid/setgid binaries structurally fail. If the agent environment cannot arm any timer, it falls back to the self-loop and records it — the host can later upgrade to cron from a normal shell if desired.
3. **Each inspection round** (a fresh headless agent): reads the shift-status section (and the `status_file` first when one is declared) → checks process/log/artifacts/timer health → decides (continue / fix & relaunch / research & fix / finish & wrap up) → updates the section → exits. The template constrains behavior: read-only by default, no blind retries, backup + self-check before relaunch, hand over with a case file only when a real decision is needed.
4. **Check results later**: read the shift-status section — `done` (acceptance summary), `need_decision` (case notes), `fixed` (repair history), or `running` (still going). Never trust a running process as success; completion requires verified artifacts.

Manual check-in works the same way when someone is watching: `ps -p <pid>`, log tail, artifact compare — all plain foreground commands — then record a short status note.

The agent owns the loop: it decides what to check, what to fix, and when to stop. There is no separate executor, daemon, or event system — the timer is the OS's (or a self-loop when the OS timer is unreachable from the agent env), and the state file is the truth. (The handoff mechanics mirror `Active Window-Switch` below: write state, exit, next round resumes from the file.)

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
