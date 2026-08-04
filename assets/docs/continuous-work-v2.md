# Continuous-Work v2

Continuous-work v2 is a foreground local supervisor for long, serial, bounded work. It owns child processes, waits for them, records evidence, and only advances after a verifier succeeds.

## Before Running

Create a run contract from `assets/examples/cw-environment-bootstrap.template.md`. A contract must declare:

- JSON `argv` for each stage; do not hide commands in shell strings.
- a finite deadline and clear verifier for every stage.
- allowed working paths, network/credential requirements, and human gates.
- a final review point.

Review it before execution. A contract is an audit record, not a sandbox.

## Commands

```bash
tau state init --root .
tau run --root . contract.json
tau run-status --root . <run-id>
tau cancel --root . <run-id>
tau recover --root . <run-id>
```

The normal path is process exit plus verifier pass. The supervisor does not ask Codex to poll a download log. It writes low-frequency health evidence only while it can observe the local process it owns.

## Recovery

If the deadline expires, the PID is missing, or the process identity differs from the recorded process, the run becomes `unknown_recovery_needed`. Do not start another stage from that state. Inspect the saved event log and process evidence, then choose recovery or a new reviewed contract.

## Fresh Context Handoff

At a semantic checkpoint or an independent new spec, create a bounded handoff package and launch a fresh Codex invocation:

```bash
tau handoff create --root . <run-id>
tau handoff launch --root . <handoff-id>
tau handoff review --root . <handoff-id>
```

The new invocation receives durable facts and must verify the working tree and recorded evidence. It does not inherit the old chat. The final review remains a human gate.

## Limits

- v2 is not a terminal-survival daemon.
- A heartbeat is health evidence, not task success.
- Fixture tests prove the portable control plane only. Verify Python, PyTorch, CUDA, simulators, and GPUs in the named target repository.
- The Codex bridge may create a new thread through supported CLI/app-server paths, but v2 does not promise that it becomes a visible or focused Desktop window.
