# Changelog

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
