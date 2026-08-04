# Contributing

## Scope

Keep the core portable: Python 3.8+, standard library first, macOS and Ubuntu. Preserve TauLoop's complete-turn boundary: specify, run, verify, checkpoint, then review or hand off. Do not add a daemon, a dashboard, or undocumented Codex Desktop automation as a side effect of a small change.

## Changes

1. Keep `SKILL.md` short and route detailed behavior to files under `assets/docs/`.
2. Preserve the distinction between user-owned project records and tool-managed files.
3. Add or update a fixture test for changed lifecycle or supervisor behavior.
4. State limitations precisely. Do not turn fixture success into a GPU or Desktop capability claim.
5. Run the checks from the README and include their results in the pull request.

## Pull Requests

Use a focused branch and describe the user-visible behavior, compatibility impact, tests, and residual risk. Avoid committing local Codex state, run logs, credentials, machine paths, or raw research exports.

## Releases

Use semantic version tags. Update `CHANGELOG.md`, test a clean user installation and a fresh target project, then create a GitHub release from the signed-off commit.
