---
name: tau-loop
description: "Use when a Codex project needs a complete, evidence-backed turn of work: durable specs, verification, checkpoints, recovery, or continuous work for long serial commands."
metadata:
  license: MIT
  repository: https://github.com/TTT-qq-TT/tau-loop
---

# TauLoop

Use this skill to give a repository a lightweight, file-backed execution harness and continuous-work runtime. TauLoop treats `tau = 2pi` as one closed turn: specify, run, verify, checkpoint, then review or hand off.

## First Use

Before operating on a project, check that `tau` is installed. The user-level installation creates this skill and one command:

```bash
tau --help
```

To enable a new or existing repository, run:

```bash
tau init --root .
```

For an existing repository with its own `AGENTS.md` or `.codex/` files, use the more explicit spelling:

```bash
tau adopt --root .
```

Both commands create missing workflow files and never overwrite existing user files by default.

## Natural-Language Requests

The user should not need to remember `tau`, `cw`, or the on-disk layout. Interpret ordinary requests such as these as TauLoop work:

- "Keep working until this repo reaches its next release goal."
- "Create spec1 through spec4, then finish them."
- "Set up this environment without repeatedly polling downloads."

When a user gives the TauLoop GitHub URL before the skill is installed, read the repository instructions, install it with `python3 install.py` when that action is permitted, then continue from the user's stated goal. A URL alone is not an instruction to modify a machine; respect the user's authorization and report any network or permission blocker.

When a user asks what TauLoop is or how to begin, read `assets/docs/first-use.md` for Chinese users or `assets/docs/first-use.en.md` for English users. Explain it briefly in the user's language, then ask for the outcome they want. Do not create specs, start continuous work, or bury the user in command names before a concrete goal exists. If the user explicitly asks to install and manage an existing project without naming a goal, the non-overwriting `tau adopt` path is allowed; explain what was prepared, then wait for the goal.

For a normal project goal:

1. Determine whether the repository needs `tau init` or the explicit `tau adopt` path. Run the appropriate command yourself.
2. Turn the goal into one parent task and small, checkable specs. Each spec must state scope, expected result, and verification. Use the project's template and records; do not require the user to author files or type commands.
3. If the user asks to see a plan first, stop after producing the specs and their definitions of done. Otherwise, work through them in order, verify each result, write a checkpoint, then proceed.
4. Stop for a genuine human decision: new permissions or spending, an irreversible action, a failed verifier, an unmet dependency, or an explicit review request. A heartbeat, a running PID, or an unfinished chat is never a reason to claim completion.

For a request that names existing specs, inspect their state and advance only the requested, unblocked specs. Report concise evidence at checkpoints rather than narrating frequent progress polls.

## Long Serial Work

Use continuous work only when the request has bounded serial stages with real commands and verifiers, such as Python -> PyTorch -> simulator -> GPU checks. Create and review the run contract yourself from the packaged template; the user does not need to know that term or call `tau run` manually.

Use it to supervise the child process and advance after verification. Do not use it for open-ended research, a task without a completion check, or an unrelated coding change. For long downloads, record low-frequency health evidence and wait for real process events rather than repeatedly polling output.

## Normal Project Work

After a project is enabled, read its root `AGENTS.md`, then follow its startup order. For non-trivial work, create or update a task spec before implementation, run the project pre-task hook, record verification, and checkpoint before changing scope.

Use `tau upgrade --root . --dry-run` before upgrading an existing project. It only updates tool-managed files whose contents still match the last installed version. It does not rewrite memory, plans, specs, reports, runtime state, or customized files.

## Continuous Work

Use continuous work only when a task contains bounded serial stages with explicit commands and verifiers. Create a JSON run contract from `assets/examples/cw-environment-bootstrap.template.md`, review its permissions and deadlines, then run:

```bash
tau state init --root .
tau run --root . contract.json
```

The supervisor owns the child process, waits for it without chat polling, records low-frequency local health evidence, and advances only after the stage verifier passes. Inspect or stop it with:

```bash
tau run-status --root . <run-id>
tau cancel --root . <run-id>
```

For a semantic checkpoint or a new independent spec, use `tau handoff create`, `tau handoff launch`, and `tau handoff review`. The new Codex invocation receives a bounded handoff package, not the previous chat history.

## Agent-Led Continuous Work (Current Main Path)

For a long task that must keep working across failures, prefer the agent-led path: a memory-backed Codex session (resume continuation) drives the work, wakes only on completion or failure, and the same lead agent repairs and re-runs after failure. Inside an initialized project:

```bash
tau agent-run --dry-run   # local closed loop: prints wake decisions, calls no agent
tau agent-run             # real loop: resumes the lead agent after failure
```

The v3 `cw loop` / `tau loop*` bounded-repair commands are deprecated and archived; their `--help` stays available but execution is blocked, so agents only run the current agent-run path.

## Boundaries

- A heartbeat proves only that the local supervisor recently observed its managed process. It is not proof of success.
- Do not advance when a deadline, PID identity, verifier, or recovery check fails. Stop in the recorded recovery state.
- Do not claim that fixture success proves CUDA, a simulator, or a GPU works. Validate those in a named target repository.
- The core is a foreground, local macOS/Ubuntu supervisor. It does not promise persistence after the terminal dies or automatic creation of a visible Codex Desktop window.
- Review every run contract. Its declared permissions are an audit boundary, not an operating-system sandbox.

Read `assets/docs/user-manual.md` for Chinese users or `assets/docs/user-manual.en.md` for English users when complete operating guidance is needed, including installation, project records, long-running work, recovery, and limits.
