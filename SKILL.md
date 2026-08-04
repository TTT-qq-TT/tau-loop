---
name: tau-loop
description: "Use when a Codex project needs a complete, evidence-backed turn of work: durable specs, verification, checkpoints, recovery, or continuous-work v2 for long serial commands."
metadata:
  license: MIT
  repository: https://github.com/TTT-qq-TT/tau-loop
---

# TauLoop

Use this skill to give a repository a lightweight, file-backed execution harness and the complete continuous-work v2 runtime. TauLoop treats `tau = 2pi` as one closed turn: specify, run, verify, checkpoint, then review or hand off.

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

## Normal Project Work

After a project is enabled, read its root `AGENTS.md`, then follow its startup order. For non-trivial work, create or update a task spec before implementation, run the project pre-task hook, record verification, and checkpoint before changing scope.

Use `tau upgrade --root . --dry-run` before upgrading an existing project. It only updates tool-managed files whose contents still match the last installed version. It does not rewrite memory, plans, specs, reports, runtime state, or customized files.

## Continuous Work v2

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

## Boundaries

- A heartbeat proves only that the local supervisor recently observed its managed process. It is not proof of success.
- Do not advance when a deadline, PID identity, verifier, or recovery check fails. Stop in the recorded recovery state.
- Do not claim that fixture success proves CUDA, a simulator, or a GPU works. Validate those in a named target repository.
- The core is a foreground, local macOS/Ubuntu supervisor. It does not promise persistence after the terminal dies or automatic creation of a visible Codex Desktop window.
- Review every run contract. Its declared permissions are an audit boundary, not an operating-system sandbox.

Read `assets/docs/continuous-work-v2.md` for the operator contract and `assets/docs/project-workflow.md` for install, migration, and removal details.
