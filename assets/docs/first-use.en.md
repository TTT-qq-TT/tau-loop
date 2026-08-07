# TauLoop First-Use Guide

[简体中文](first-use.md) | **English**

> Hand the goal to your agent; TauLoop handles the records and verification.

## Get Started

Send this to your agent, replacing `xxx` with the outcome you actually want:

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project to xxx.

Continue on your own when you can verify; stop when I really need to decide.
```

The agent will:

1. Download and install TauLoop (the skill + the `tau` command);
2. Run `tau init` in the project, creating `AGENTS.md` and the `.harness/` skeleton;
3. Break your goal into small checkable tasks (specs), complete them one by one, and record verification.

You do not need to memorize commands or understand `spec`, `checkpoint`, or `harness` first.

If you want to see the plan first, add:

```text
Only show me the plan and the definition of done for each part first; start after I confirm.
```

## Manual Install (only for troubleshooting)

Requires Python 3.9+.

```bash
git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop /tmp/tau-loop-install
python3 /tmp/tau-loop-install/install.py
```

## After That

- Day to day: tell the agent where you want to take the project, and "continue when you can verify; stop when I really need to decide".
- Long commands: the agent hands the process to the OS with `nohup`/`screen` and wakes periodically to check — it never fills the conversation.
- Legacy projects: repos still using `.codex/` should migrate once via the [migration guide](migration-from-codex.md).
- To go deeper: read the [full user manual](user-manual.en.md).
