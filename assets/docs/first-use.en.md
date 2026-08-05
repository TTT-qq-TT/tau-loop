# TauLoop: First Use

**English** | [简体中文](first-use.md)

> You do not need to learn a workflow before you are allowed to hand a project to Codex.
>
> Name where you want to get to. TauLoop leaves behind what is in progress, what has been verified, and what should happen next.

## Start with one sentence

In your project, tell Codex:

```text
Use TauLoop to move the current project forward to xxx.

Keep going when you can verify the work yourself; stop only when a real decision is mine.
```

Replace `xxx` with the result you actually want: finish a feature, fix a class of problems, set up an environment, or reach a point that is ready to review.

The first time, when TauLoop is not installed yet, send the repository link too:

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project forward to xxx.

Keep going when you can verify the work yourself; stop only when a real decision is mine.
```

You do not need to memorize commands or understand `spec`, `checkpoint`, or `cw` first.

## Choose a pace

### Look at the route first

When you do not want work to begin yet, say:

```text
Show me the plan and the definition of done for each part first. Do not implement anything until I approve it.
```

You will see how the project is expected to move forward, what makes each part complete, and where your choice is needed.

### Keep moving

When the goal and boundaries are clear, say:

```text
Continue with the plan. After each part, verify it, leave a checkpoint, then start the next unblocked part.
```

You should not need to relay every small step. Within a scope that can be checked with evidence, Codex should be able to finish the next piece itself.

### Let a long task run quietly

For downloads, installations, builds, or tests that need time, say:

```text
Use TauLoop to complete xxx.
Arrange downloading, installation, and checks as verified stages. Do not start the next stage unless the prior one passes, and do not repeatedly inspect progress logs.
```

The local command needs to wait, not the chat window. TauLoop records the facts along the way and moves forward only after a check passes.

## The project remembers

After a piece of work ends, the project keeps its plan, definition of done, verification results, and next step. When you return tomorrow or switch to a fresh context, Codex starts from those facts instead of asking you to reconstruct the last chat.

At any time, ask:

```text
Show me the current plan, the last verified result, and the next step that is safe to continue.
```

## When TauLoop stops

TauLoop is not meant to let Codex decide everything. These still need your confirmation:

- New permissions, costs, credentials, or irreversible actions.
- A strategy change after verification fails.
- Product tradeoffs, release decisions, or any point where you asked for review.
- An interrupted task whose state cannot be confirmed safely.

A running process, a heartbeat, or a growing log is not completion. Completion needs real verification evidence.

## Want the full picture?

You do not need to read it now. When you want to see how project records work, recover long-running work, use bounded repair, or run commands yourself, open the [complete user manual](user-manual.en.md).

Next time, tell Codex where you want the project to go, then add: "Keep going when you can verify the work yourself; stop only when a real decision is mine."
