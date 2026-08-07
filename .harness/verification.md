# Verification

## Global Rules

- Every non-trivial task must record what verification was run.
- If verification was intentionally skipped, state why and what residual risk remains.
- Prefer targeted verification over broad, expensive sweeps.
- Verification belongs in the task spec first. This file defines repo-level defaults.
- Keep this file short. Detailed checklists live in `.codex/verification-profiles/` and should be read only when they match the task.

## Default Closeout Checklist

- Confirm the implementation stayed within the allowed file boundary.
- Run the smallest command set that validates the changed behavior.
- Run `.codex/hooks/pre-closeout.sh` when hook entrypoints are installed.
- Check that changed docs, paths, and commands remain internally consistent.
- For launcher packaging, verify the PATH-preferred user launcher, not only its `~/.codex/bin` compatibility copy; enroll a fresh disposable Git repo through that entrypoint.
- Update memory, plan, and the active spec before ending the thread.

## Profile Selector

- `code-change`
  Use for feature work, bug fixes, and behavior-changing code edits.

- `refactor`
  Use when the goal is structural change with intended behavior parity.

- `docs-workflow`
  Use for workflow docs, templates, onboarding docs, and bootstrap logic.

- `reliability`
  Use when fixing recurring failures, adding prevention, or tightening the harness.

Read only the matching file under `.codex/verification-profiles/` instead of loading every checklist.
