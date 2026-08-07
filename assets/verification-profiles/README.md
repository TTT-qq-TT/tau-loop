# Verification Profiles

Use one verification profile per non-trivial task when the default closeout checklist is too vague.

## Rule

- Keep profile choice explicit in `.harness/plan.md` or the active spec.
- Read only the profile that matches the task.
- If none fit, use `.harness/verification.md` plus task-specific checks in the spec.

## Available Profiles

- `code-change.md`
- `refactor.md`
- `docs-workflow.md`
- `reliability.md`
