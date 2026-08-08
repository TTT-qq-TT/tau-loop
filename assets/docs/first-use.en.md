# TauLoop: First Use

**English** | [简体中文](first-use.md)

> You do not need to learn a workflow before you are allowed to hand a project to the agent.
>
> Name where you want to get to. TauLoop leaves behind what is in progress, what has been verified, and what should happen next.

## Start with one sentence

In your project, tell the agent:

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

You do not need to memorize commands or understand `spec` or `checkpoint` first.

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

You should not need to relay every small step. Within a scope that can be checked with evidence, the agent should be able to finish the next piece itself.

### Let a long task run quietly

For downloads, installations, builds, or tests that need time, say:

```text
Use TauLoop to complete xxx.
Arrange downloading, installation, and checks as verified stages. Do not start the next stage unless the prior one passes, and do not frequently inspect download progress.
```

After launching, the agent hands the process to the operating system and then "goes to sleep" — it does not watch the progress bar. It wakes periodically to read the log tail, check the process, and compare expected artifacts, moving on only when verification passes. The local process is what waits, not the chat window; "the process is alive" is not "the task is done" — completion requires evidence that actually passed verification.

## Words you will keep hearing

- **spec**: the contract for one piece of work. The agent breaks your goal into pieces and, for each one, writes down what changes, what counts as done, and how to verify before touching code. When the scope changes, update the spec first.
- **plan**: the project's roadmap — the current goal, where it stands, and what comes next. To see progress, just say "show me the current plan".
- **checkpoint**: the state left after a piece of work — what just happened, where the evidence is, what comes next. After a new window or the next day, the agent continues from here.
- **memory**: facts the project still needs to remember — not a chat transcript, but conclusions, verified environment facts, and known risks.
- **long-running tasks**: slow work like downloads and builds is owned by an OS-managed process; the agent wakes periodically to check (covered above), instead of occupying the chat window.
- **handoff (window switch)**: when the context window is nearly full or you want to separate discussion from execution, say "please hand off to the next window". The agent writes a handover file and gives you one launch line; paste it into a fresh window and it continues seamlessly, no re-explaining.

## The project remembers

After a piece of work ends, the project keeps its plan, definition of done, verification results, and next step. When you return tomorrow or switch to a fresh context, the agent starts from those facts instead of asking you to reconstruct the last chat.

At any time, ask:

```text
Show me the current plan, the last verified result, and the next step that is safe to continue.
```

## When TauLoop stops

TauLoop is not meant to let the agent decide everything. These still need your confirmation:

- New permissions, costs, credentials, or irreversible actions.
- A strategy change after verification fails.
- Product tradeoffs, release decisions, or any point where you asked for review.
- An interrupted task whose state cannot be confirmed safely.

A running process or a growing log is not completion. Completion needs real verification evidence.

## Want the full picture?

You do not need to read it now. When you want to see how project records work, recover long-running work, use bounded repair, or run commands yourself, open the [complete user manual](user-manual.en.md).

Next time, tell the agent where you want the project to go, then add: "Keep going when you can verify the work yourself; stop only when a real decision is mine."
