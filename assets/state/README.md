# continuous-work state foundation

`.codex/state/` is the machine-readable runtime layer for continuous-work.

The packaged `tau-loop` skill installs this README by default so a repo can discover the control-plane contract without inheriting another repo's runtime JSON.

## What This Directory Is For

Use `.codex/state/` only for durable continuous-work runtime records such as:

- `project.json`
- `specs/*.json`
- `agents/*.json`
- `sessions/*.json`
- `worktrees/*.json`
- `gates/*.json`

These records are created by the control plane, not copied from the proving repo.

## Default Packaging Rule

`tau init` creates:

- `.codex/state/README.md`
- `.codex/tools/cw_state.py`
- `.codex/hooks/cw-hook.sh`
- `.codex/hooks/verify-continuous-work-v1.sh`

It does not create live runtime entities automatically.

To initialize state for the current repo, run:

```bash
tau state init --root .
```

## Primary Commands

The packaged launcher is `tau state`, which proxies the repo-local `.codex/tools/cw_state.py`.

Typical entrypoints:

```bash
tau status --root .
tau state next --root .
tau state recover --root .
tau doctor --root .
```

For the full command contract, inspect `tau --help` and the repo-local state subcommand help in the active repo.
