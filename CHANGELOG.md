# Changelog

## 0.10.0 - 2026-08-20

- **DSH native path for long-running tasks** — when the host is DeepSeek Harness (dsh web), long work no longer needs polling loops, OS timers, or shift-agent inspection rounds. The convention (in `AGENTS.md` → Long-Running Tasks → DSH native path) is: package the whole flow into one script, launch it as a background job (`bash` tool `run_in_background: true` — no timeout, host-owned), record the job id in the shift-status section, end the turn, and **DSH wakes the session automatically when the job settles — completion, failure, or interruption — so the agent continues in the foreground**: read the status file, fix what failed (backup → smoke → relaunch), run the next stage, wrap up on acceptance, report. Zero user operations.
- DSH-path discipline documented: one flow = one script job (consecutive automatic wake-ups are capped at 3 per owner — put every stage in one script, or bridge stages with a foreground `job_output(wait)`); **do not create a goal while waiting on a background job** (goal rounds auto-open on an idle agent and fight the wait); a host restart loses process-local jobs, so cross-restart unattended work must be resumable (status-file driven) and re-invoked after restart.
- The previous dual-mode watch (Mode A foreground polling + Mode B shift agent with OS timers) is kept unchanged for non-DSH hosts (Claude Code / Codex / other runtimes) under a "Non-DSH hosts" heading in the same chapter.
- Docs (zh/en): user manual long-task chapter, first-use guide, and SKILL.md aligned to the DSH native path. No new commands, no daemon, no dependencies — doc-only change; `tau init` remains the single command surface.

## 0.9.0 - 2026-08-12
- **Status-file-driven shift-status section**: new `status_file` field (the task's own machine-readable status file; polling/inspection/handover all read it, so they agree and history survives) and `mode: foreground | shift`; `pid` now accepts a systemd unit name (`systemctl --user is-active`). All existing fields kept — old watch sections stay compatible.
- Shift-agent template v3 adds two disciplines learned in the field: **kill precision** (a `pkill -f <long command string>` can match and kill your own shell — use exact PIDs / more specific patterns) and the **smoke hard gate** (any new model/step must run a small smoke test before its first real run — dtype/path/memory issues only surface on first real inference). Template self-check now also requires `summary` to agree with the status file when one is declared.
- Docs (zh/en): user manual long-task flow, execution, and first-use aligned to the two modes and systemd-run; SKILL.md updated. No new commands, no daemon, no dependencies — doc/template changes only; `tau init` remains the single command surface.

## 0.8.0 - 2026-08-11

- New capability: **research-first bug triage** — when the agent hits a bug (test failure, command error, anomalous log, behavior mismatch, or a user-reported bug), it defaults to research first, fix second: no blind fixes (trial-and-error patches, working around the symptom, or changing acceptance criteria to pass).
- Convention-only, four layers (no mechanical layer, by owner decision): ① `AGENTS.md` gains a `Debug Triage: Research First` chapter (mirrored to `assets/AGENTS.md`) defining triggers, the research priority (official docs → upstream repo source + issue tracker, searched with a distinctive fragment of the raw error message → open-source community → papers / arXiv, **moved up for research projects** — research repos, algorithm-implementation bugs, or a declared research scenario), the before-you-fix bar (minimal reproduction + raw evidence + falsifiable root-cause hypothesis + research trail with concrete sources), the skip exceptions (pure formatting/typing/mechanical edits with no behavior change; no network access — then "not researched" plus residual risk is recorded), and hand-over-not-fabricate (exhausted research → hand over observed / tried / researched / suggested; never invent sources); ② a new `assets/templates/debug-triage.md` template (shipped via `tau init` like `shift-agent.md`; the two templates cross-reference, they do not duplicate) with a five-step workflow: reproduce → falsifiable hypothesis → research (record every source) → minimal fix + regression check (pass or revert to hypothesis) → record evidence; ③ the spec template gains a `5b. Debug Evidence` section, required for bug-fix tasks (现象 / 查证记录 / 根因结论 / 修复依据 / 残余风险 — symptom / research trail / root cause / fix rationale / residual risk); ④ user manual (zh/en) gains an "on bugs: research first, then fix" section and SKILL.md one line in the workflow list.
- Reusable failure modes still land in `.harness/failure-log.md`. The research-first discipline generalizes what shift mode already did for unattended rounds (research before repair, hand over only for real decisions) to everyday development.
- No new commands, no daemon, no dependencies. Doc/template changes only; `tau init` remains the single command surface.

## 0.7.1 - 2026-08-11

- Shift mode timer becomes **agent-probed, three options**: the agent picks the best timer it can actually configure — Linux prefers `systemd --user timer` (OS-level, survives reboots via `loginctl enable-linger`; probe with `export XDG_RUNTIME_DIR=/run/user/$(id -u)` in the same Bash call), macOS uses launchd, and a `setsid` self-loop (process-level) is the fallback when no OS timer is reachable from the agent environment. A host-configured cron entry is consumed when present. The choice is recorded in the shift-status section (`timer_type` + `cron_note`).
- Why: field evidence. On Linux the agent command layer hard-sets `PR_SET_NO_NEW_PRIVS` (process hardening, not a config flag), so setuid/setgid binaries (`crontab`, `sudo`) structurally fail from the agent shell; three prior approaches (cron in-session, elevation, sandbox_mode values) cannot bypass it. `systemd --user timer` needs no setuid and was verified end-to-end on two machines from both the host shell and a live agent session.
- Shift-agent template v2 adds two disciplines: **environment awareness** (when permission is denied, suspect your own execution environment first — missing `XDG_RUNTIME_DIR`, NoNewPrivs hardening — and have the host re-check before concluding the system is broken) and **timer ownership** (inspection rounds never create/modify system timers; they only confirm the timer is still alive and note anomalies). New shift-status fields: `headless_cmd` (pinned launch command, prevents grabbing the wrong CLI), `timer_type`, `loop_pid`, `cron_note`.
- Docs (zh/en): AGENTS.md Long-Running Tasks rewritten around the three-option pick (with `enable-linger` one-time setup for a normal user), user manual flow/execution/FAQ updated, first-use and SKILL.md aligned. No new commands, no daemon, no dependencies.

## 0.7.0 - 2026-08-10

- New capability: **shift mode (long-task watch)** — unattended monitoring and repair of hours-long work (training, builds, downloads). Instead of sleeping in-session (unreliable on turn-based runtimes: foreground commands are bounded and shell background tasks detach), the agent decouples the process, writes a shift-status section in `.harness/plan.md`, and arms a system timer (cron / launchd / Task Scheduler) that periodically launches a short headless inspection round. Each round reads state, checks process/log/artifacts, fixes what it safely can, updates the state file, and exits. The user reads `done` / `need_decision` / `fixed` / `running` from the plan in the morning.
- Three-layer minimal design: ① clock = OS timer (no supervisor code; survives crashes by design — each launch is a fresh process); ② inspection round = a single headless agent turn (`claude -p` / `codex exec` / any headless mode) driven by a template; ③ state = the shift-status section in plan.md (file-as-truth; `active` mutual exclusion so rounds never overlap; `next_check_at` self-scheduling).
- The shift-agent template (`.harness/templates/shift-agent.md`, shipped via `tau init`) constrains each round: read-only by default, no blind retries (same approach twice without effect → switch to research), backup + self-check + rollback before relaunch, research-first on hard failures (GitHub issues / upstream source / community fixes), hand over with a case file only for real decisions (irreversible actions, spending, experiment-design changes, research exhausted), finish-and-wrap-up with acceptance evidence on completion, optional system notification on `done`/`need_decision`.
- Distribution: `project_lifecycle.py` now vendors `assets/templates/` into `.harness/templates/` on init, so the shift-agent template lands in every project skeleton.
- Documentation: `AGENTS.md` Long-Running Tasks rewritten around shift mode (with cron / headless-launch examples, mirrored in `assets/AGENTS.md`); user manual (zh/en) long-task flow, FAQ and execution sections updated; first-use (zh/en) "the agent goes to sleep" wording replaced by the timer + inspection-round mechanism; SKILL.md aligned.
- Research-driven: four survey passes (official Claude Code / Codex / codewhale; competitors LoopX / Ralph / flow-next / OpenHands; community practice; source inspection of Nightcrawler / Night-loop / LoopX) concluded that no existing project implements the full "wake → inspect → repair → finish" loop. The design borrows ideas (OS timer as supervisor, fresh-context rounds, file-based handoff) without copying code. Official in-session timers were rejected on evidence: Claude Code scheduled tasks silently stall (#85474), cannot be cancelled under rate limits (#85292), resurrect after `/compact` (#46561) — 7 related issues, no upstream fix.

## 0.6.0 - 2026-08-09

- Windows support (CI-verified): tau-loop now runs on Windows for agents (e.g. the Codex desktop app) — hooks do not error and long tasks have a documented replacement. Windows users never touch a terminal: they work in natural language through a desktop client and the agent initializes tau-loop (pure Python path); if Python is missing, the agent installs it (e.g. `winget install Python.Python.3.12`).
- Dual-entry hooks: every hook ships a bash version (`.harness/hooks/*.sh`, unchanged for macOS/Linux) and a shell-agnostic Python version (`*.py`, invoked via `python`/`py -3` on Windows; internally uses `sys.executable` so no command-name dependency). `verify.sh` mirror checks now cover the `.py` entries too.
- Long-task convention gains a native Windows replacement: `Start-Process -NoNewWindow -RedirectStandardOutput` (documented in AGENTS.md and user manual zh/en); `screen` has no Windows equivalent — either drop re-attach or run under WSL/Git Bash.
- Documentation: README badges, user manual (zh/en), and CONTRIBUTING now declare macOS / Ubuntu / Windows; platform-specific command names documented (`python3` on POSIX, `python`/`py -3` on Windows — the Windows `python3` Store alias stub pitfall noted).
- CI: `verify.yml` matrix adds `windows-latest` (× 3.9/3.12), with platform-aware steps (unittest via `python`, `compileall` instead of glob `py_compile`, `bash -n` POSIX-only) plus a PowerShell long-task smoke test that actually starts a process and asserts log redirection.
- Tests: platform branches for the packaged `tau` entry and the verify hook; mirror-consistency list extended to `.py` hooks; the cw-brand asset check now matches brand forms instead of the bare substring (avoids false positives on `Path.cwd()`).

## 0.5.0 - 2026-08-08

- New capability: proactive window-switch — when the context window is nearly full or you want to separate discussion from execution, say "please hand off to the next window". The agent decides the intent, confirms spec/plan/memory are current, writes a handoff file (`.harness/handoffs/<id>.md`), and gives you a short launch line; a fresh window pastes it and continues seamlessly, no re-explaining.
- Intent-first design: the agent must declare the current intent (with one line of why) in the handoff; the four reference intents (continue / decision-to-execution / fresh review / explore a branch) are defaults, not an exhaustive menu.
- Two-layer handoff: a short prompt layer for you to copy (≤5 lines: intent, handoff path, next action) and a self-contained state layer in the handoff file (spec path, progress, evidence, constraints) the new window reads directly.
- No orchestrator: the switch is executed by you (one copy-paste); the agent only prepares the handover. No daemon, no new command — `tau init` remains the only command.
- Documented in `AGENTS.md` (Active Window-Switch chapter, mirrored in `assets/AGENTS.md`), user manual (zh/en) with the design philosophy (intent-first, minimal by design), README (zh/en/en-standalone) third "what it is especially good for" item, first-use glossary entry, and SKILL.md one-line guidance.
- `.harness/handoffs/` added to `.gitignore` (dev-sandbox handover files, never published).

## 0.4.1 - 2026-08-08

- README (zh/en) restructured around the product's essence: minimal (one `tau init`, no daemon / state machine / command surface), files-as-truth (records live in `.harness/`), and a thin mechanical backstop (hooks and check scripts).
- Positioning: for newcomers who find harness / loop-engineering terms daunting, and for those who find existing workflow skills too heavy — light, capable, pain-point-only.
- New standalone `README.zh.md`; the bilingual `README.md` keeps the in-page language switch, with `README.en.md` as the English standalone.
- User manual (zh/en) restructured into 10 chapters (start here → what it solves → getting started → how a project keeps its memory → how it is kept in check → long-running tasks → safety boundaries → daily maintenance → contributing → glossary), removing legacy continuous-work / run / contract / supervisor references.
- Narrative unified from Codex to agent across docs (installation paths under `~/.codex` kept); Python requirement corrected to 3.9+; install redirect documented (`install.py --codex-home` / `TAU_LOOP_CODEX_HOME`).
- First-use guide (zh/en) deepened: five core terms (spec / plan / checkpoint / memory / long-running tasks) and the long-task "the agent sleeps" mechanism, staying lighter than the full manual.
- SKILL.md install guidance documents the `--codex-home` / `TAU_LOOP_CODEX_HOME` redirect; heartbeat references removed across all reader docs for consistency.

## 0.4.0 - 2026-08-07

- Consolidate into the single tau-loop repository; tt-workflow is frozen as historical archive.
- Remove the entire cw surface: dispatch shell, state machine, agent-led runtime, spike, supervisor, hooks, fixtures, and contract examples.
- Command surface converges to a single `tau init` (bootstrap skeleton); uninstall moves to `python3 install.py --uninstall`.
- Harness directory is `.harness/` (agent-agnostic, not bound to Codex); enrollment marker is `.harness-workflow`.
- Long-running tasks become a documentation convention in `AGENTS.md` (`Long-Running Tasks`: nohup/screen decouple + sleep + wake-and-check), with hooks as the only mechanical guard.
- Productized install/use channels: install by natural language (SKILL.md guidance) or terminal (`install.py`); enable a project by `tau init` or by natural language.
- Development-sandbox state (`.harness/memory.md`, `plan.md`, `report.md`, `failure-log.md`, task specs) is gitignored and never published.
- Packaged assets mirror `.harness/` and are verified by `verify.sh` (doc freshness + task state + mirror consistency).
- SKILL.md rewritten for the new capability surface; README and user manuals (zh/en) finalized for it too (owner 2026-08-07).

## 0.3.0 - 2026-08-07

- Align the packaged assets with the latest tt-workflow: add the agent-led continuous-work runtime and multi-agent backend adapters.
- New command: `tau agent-run` (agent-led orchestrator; plus `cw agent-session`, `cw agent-events`, `cw agent-exec`, and `cw agent-guard` support tools).
- Backend adapters: CodexBackend complete, CodewhaleBackend complete, ClaudeBackend skeleton — selectable per work order (`backend` field); model follows the Codex config.
- Deprecate the v3 bounded loop: `cw loop*` / `tau loop*` keep `--help` but block execution (exit 2); agent-led continuous work (`tau agent-run`) is now the current main path.
- Update SKILL.md, user manuals (zh/en), and verification hook; require the B-direction runner and backend fixtures during installation.

## 0.2.0 - 2026-08-05

- Expose bounded continuous-work v3 commands through `tau loop`, `tau loop-status`, `tau loop-recover`, and `tau loop-cancel`.
- Require the packaged v3 worker and fixture during installation, and prove them in the clean-install lifecycle test.

## 0.1.0 - 2026-08-04

- First TauLoop public release candidate.
- `tau = 2pi`: one complete, evidence-backed turn of work for coding agents.
- One Codex-first skill containing the harness and complete continuous-work v2 runtime.
- Safe project lifecycle commands: `init`, `adopt`, `upgrade`, and `uninstall`.
- Bilingual onboarding, portable fixture tests, and explicit capability boundaries.
