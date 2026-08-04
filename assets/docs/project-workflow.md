# Project Workflow And Lifecycle

## Install The Skill

Run `python3 install.py` from a `tau-loop` checkout. It installs exactly two user-level surfaces:

- `~/.codex/skills/tau-loop/`, which Codex discovers as a skill.
- `~/.codex/bin/tau`, the project lifecycle and execution command.

Add `~/.codex/bin` to `PATH` if your environment does not already expose it. The installer does not edit shell configuration.

## Add A Project

`tau init --root .` is for a new project. `tau adopt --root .` is for an existing one. Both operations create only missing files:

- root `AGENTS.md`
- `.codex/` starter documents, task-spec template, validation profiles, and state guide
- repo-local hooks and Python tools
- `.codex-workflow` enrollment marker

They do not create live continuous-work JSON state. When the project needs the durable v1 control plane, run `tau state init --root .` explicitly.

## File Ownership

Project records are user-owned after creation: `AGENTS.md`, memory, plan, brief, specs, reports, failure log, verification rules, and live `.codex/state/` data. An upgrade never rewrites them.

Repo-local hooks and tools are tool-managed only when a fresh `init` or `adopt` created them. Their installed hashes are recorded in `.codex/.tau-loop-managed.json`.

## Upgrade

Always inspect the plan first:

```bash
tau upgrade --root . --dry-run
```

The real command updates a tool only when its current hash still matches the last tau-loop-installed hash. A modified or unrecognized tool is skipped. `--force` may replace it and should be used only after a diff review.

## Remove

`tau uninstall --root .` removes only unchanged tool-managed hooks and tools plus the enrollment marker. It deliberately leaves project records and live state intact for recovery. Remove those records manually only after you no longer need them.

`python3 install.py --uninstall` removes the user-level skill and its unchanged command wrapper.
