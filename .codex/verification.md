# Verification

## Global Rules

- Every non-trivial task must record what verification was run.
- If verification was intentionally skipped, state why and what residual risk remains.
- Prefer targeted verification over broad, expensive test sweeps.
- Verification belongs in the task spec first. This file defines repo-level defaults.
- Keep this file short. Detailed checklists live in `.codex/verification-profiles/` and should be read only when needed.

## Default Closeout Checklist

- Confirm the implementation stayed within the allowed file boundary.
- Run the smallest command set that validates the changed behavior.
- Run `.codex/hooks/pre-closeout.sh` when hook entrypoints are installed.
- Check for obvious regressions in adjacent paths.
- Update docs when behavior, interfaces, or workflow changed.

## Profile Selector

- `code-change`
  Use for feature work, bug fixes, or behavior-changing code edits.

- `refactor`
  Use when the goal is structural change with intended behavior parity.

- `docs-workflow`
  Use for workflow docs, templates, onboarding docs, and bootstrap logic.

- `reliability`
  Use when fixing recurring failures, adding prevention, or tightening the harness.

Read only the matching file under `.codex/verification-profiles/` instead of loading every checklist.
