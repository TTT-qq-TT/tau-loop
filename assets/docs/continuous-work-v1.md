# Continuous-Work v1 Control Plane

The v1 control plane stores project-level state for specs, sessions, gates, review, and recovery. It is included because v2 uses the same repo-local workflow foundation.

Initialize runtime state only when the project needs it:

```bash
tau state init --root .
tau status --root .
tau doctor --root .
```

Use v1 state commands for durable task topology and v2 run commands for supervised external processes. Neither command family turns an unbounded task into proof of completion; follow project verification and human-gate rules.
