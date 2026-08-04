# TauLoop: First-use Guide for Codex

This guide is for Codex. When a user first asks how TauLoop works, explain it in plain language. Do not begin with commands, directories, or internal terms.

## One-sentence introduction

TauLoop turns a project goal into small, clear pieces of work. Codex completes them, verifies them, and leaves progress behind, so work survives a new session and long tasks do not pretend to advance through repeated log polling.

## What to say in the first conversation

Tell the user only three things:

1. They only need to state the outcome, such as "take this project to v1" or "set up this environment."
2. I will break that goal into specs. Every spec says what to do and how to know it is complete.
3. After each spec, I verify the result and write a checkpoint. I stop only for a user decision, permission or spending decision, or failed verification.
4. The project keeps shared memory: `AGENTS.md` says how to begin, `.codex/plan.md` records current work, and `.codex/memory.md` keeps facts that still matter.

Then ask one useful question: **"What goal would you like me to move forward first?"**

## Explain these words only when needed

- **Task**: the outcome the user wants.
- **Spec**: a small job card with scope and a definition of done.
- **Checkpoint**: the factual record left after a piece of work; the next session can continue from it.
- **Harness**: the shared project record for plans, results, and problems.
- **Long-running work**: serial work that takes time, such as downloading, installing, training, or testing.

Do not explain every term at once. Explain one in a sentence when the user needs it.

## What to do after a goal exists

- Create or update one parent task and the needed specs.
- If the user says "show me the plan first," show only the plan and definitions of done, then wait.
- If the user says "keep moving," complete the actionable specs in order; verify and checkpoint each one before the next.
- If the user names `spec1` through `spec4`, advance only those specs and do not expand into unrelated work.

## How to handle long-running work

When work has downloads, installation, training, or ordered commands, first write an execution plan and a verifier for each stage. Supervise the real process and record low-noise health evidence. Do not start the next stage before the prior verifier passes.

Never call a heartbeat, a live process, or a long log "complete." Do not repeatedly poll download progress.

## When to stop

Stop and ask the user to decide when there is:

- A new permission, spending, or irreversible change.
- Failed verification, a missing dependency, or a recovery choice.
- A requested review, or completed work that needs acceptance.

TauLoop is a foreground local tool. It does not survive a closed terminal or reboot, and fixture success does not prove CUDA, a GPU, or a simulator works in the target project.
