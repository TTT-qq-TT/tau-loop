<p align="center">
  <img src="docs/images/tauloop-mark.png" alt="" width="48" height="48" valign="middle"> <strong>τ-Loop</strong>
  <br>
  <em>Give the goal to the agent. TauLoop keeps the plan, the evidence, and the next step.</em>
</p>

<p align="center">
  <img src="docs/images/tauloop-readme-cover.png" alt="TauLoop: a lightweight file-backed execution harness" width="960">
</p>

TauLoop gives a repository a lightweight, file-backed execution harness with one command: `tau init`. After that, the workflow is pure convention in the project's `AGENTS.md` — no daemon, no state machine, no script execution layer.

---

## Start with one sentence

Tell your agent:

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project forward to xxx.
```

The agent installs TauLoop, runs `tau init` in the project, and breaks the goal into checkable pieces.

## Three things it keeps safe

### 1. It does not stop in the gaps

Between turns, the project keeps its plan, specs, and verification records. The next agent reads `AGENTS.md`, then `.harness/memory.md` and `.harness/plan.md`, and continues from evidence — not from a fresh chat.

### 2. It does not start over after a new window

A spec is the durable contract for a task: goal, boundaries, allowed files, acceptance. Work resumes where the records say it was.

### 3. It does not turn waiting into noise

Long commands are owned by the operating system (`nohup`/`screen`), decoupled from the conversation. The agent sleeps in-session and wakes to check the log, the process, and the artifacts. Completion requires verification evidence, not a heartbeat.

## Two things it is especially good at

### 1. Move a project to xxx

Turn a goal into small checkable specs, work through them in order, verify each one, and record checkpoints. Stop only for genuine human decisions.

### 2. Let a long command finish quietly

Downloads, builds, and data assembly follow the `Long-Running Tasks` convention in `AGENTS.md`: plan as a spec, launch decoupled, sleep, wake and check, record evidence, close out.

## Want to look a little closer?

- [User manual](assets/docs/user-manual.en.md) — installation, enabling a project, the daily workflow, long tasks, verification hooks, and boundaries.
- [First-use guide](assets/docs/first-use.en.md) — the fastest way to start.
- [Migration guide](assets/docs/migration-from-codex.md) — moving an existing `.codex/` repo to `.harness/`.
- The only mechanical guards are the packaged hooks and check scripts; everything else is documented convention.

## What it will not do

- It will not run your commands or keep a daemon around.
- It will not claim a running process is success.
- It will not grow a command surface: `tau` is exactly `tau init` (+ `--help`).
- It will not make decisions that are yours: permissions, spending, irreversible actions, failed verifiers, and review points stay with you.

## Manual install

Requires Python 3.9+; supports macOS and Ubuntu.

```bash
git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

After installation, the `tau` command lands in `~/.codex/bin`; make sure it is on `PATH`. Uninstall with `python3 install.py --uninstall`.

## Learn more

- [User manual](assets/docs/user-manual.en.md) · [First-use](assets/docs/first-use.en.md)
- [License](LICENSE) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)
