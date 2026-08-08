# Changelog

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
