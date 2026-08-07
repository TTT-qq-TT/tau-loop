# TauLoop Complete User Manual

**English** | [简体中文](user-manual.md)

> Give Codex the goal. TauLoop leaves the plan, evidence, and next step in the project.
>
> This is not a course in agent workflows. It is a set of project records and execution tools: one piece of work can lead to the next, local commands can wait without filling the chat, and decisions that belong to you still come back to you.

## Contents

- [Start here](#start-here)
- [What TauLoop solves, and what it does not decide](#what-tauloop-solves-and-what-it-does-not-decide)
- [How a project keeps its memory](#how-a-project-keeps-its-memory)
- [Moving a project forward](#moving-a-project-forward)
- [Letting long commands finish quietly](#letting-long-commands-finish-quietly)
- [Inspecting progress, recovering, cancelling, and changing context](#inspecting-progress-recovering-cancelling-and-changing-context)
- [Installing, upgrading, and removing](#installing-upgrading-and-removing)
- [Safety boundaries and human decisions](#safety-boundaries-and-human-decisions)
- [Contributing and troubleshooting](#contributing-and-troubleshooting)
- [Glossary and command reference](#glossary-and-command-reference)

---

## Start here

### The recommended path: name the goal

Send this text to Codex with the TauLoop repository link, replacing `xxx` with your intended result:

```text
Please read and install https://github.com/TTT-qq-TT/tau-loop , then use TauLoop to move the current project forward to xxx.

Keep going when you can verify the work yourself; stop only when a real decision is mine.
```

Codex installs TauLoop, determines whether this is a new or existing project, creates the records it needs, and breaks the work into checkable pieces. You do not need to know what `spec`, `checkpoint`, or `harness` mean first.

To review the route before work begins, add:

```text
Show me only the plan and the definition of done for each part. Wait for my approval before starting.
```

### Install by hand

Only run these commands when Codex asks you to install manually, or when you are troubleshooting:

TauLoop requires Codex and Python 3.8+ and currently supports macOS and Ubuntu. A Git worktree is required only for bounded repair.

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

Installation creates two user-level surfaces:

- `~/.codex/skills/tau-loop/`, which Codex can discover and read.
- `~/.codex/bin/tau`, the command entrypoint for the project workflow and continuous work.

If the terminal cannot find `tau`, add `~/.codex/bin` to `PATH`, then check:

```bash
tau --help
```

### Enable a project

For a new project:

```bash
tau init --root .
```

For an existing project with its own `AGENTS.md` or collaboration rules, use the same command — it creates only missing files and never overwrites existing records:

```bash
tau init --root .
``` After that, tell Codex the outcome you need.

---

## What TauLoop solves, and what it does not decide

TauLoop is not about making Codex run forever. It helps each piece of work complete a traceable turn:

```text
goal -> checkable step -> implementation -> verification -> checkpoint -> next step or your decision
```

| The moment you recognize | What TauLoop leaves behind or runs | The result |
| --- | --- | --- |
| Codex stops at the first small decision it should have been able to make itself. | `plan` and `spec` state the goal, scope, definition of done, and verification first. | When the goal and boundary are clear, it has a next step to take. |
| A fresh window makes the project feel unknown again. | `memory`, `plan`, `spec`, and `checkpoint` live in the repository. | A fresh context reads project facts instead of guessing what happened in the old chat. |
| Downloads, installs, and builds turn into repeated log polling or stop halfway through. | `continuous-work` supervises real local processes and records low-noise health evidence. | A later stage starts only after the prior stage verifies; waiting does not occupy the chat. |
| Project progress feels like a string of improvised conversations. | Each non-trivial task has scope, verification, and a closeout record. | You can inspect what is being done, why it is complete, and what is next. |
| A growing context makes it risky to continue. | Checkpoints and bounded handoffs carry only the facts needed next. | A new context is a reviewable handoff, not amnesia or a copied chat transcript. |

TauLoop also has clear limits. It does not approve new permissions, spending, or irreversible actions for you. It does not call a live process, a heartbeat, or a long log a success. When verification fails, a dependency is missing, risk must expand, or product judgment is needed, it should stop at a human gate you can inspect.

---

## How a project keeps its memory

After you enable it, a project has `AGENTS.md` and `.harness/`. They are not another application subsystem; they are shared project records for the current and next agent.

```text
your-project/
├── AGENTS.md
└── .harness/
    ├── memory.md
    ├── plan.md
    ├── brief.md
    ├── specs/
    ├── verification.md
    ├── verification-profiles/
    ├── hooks/
    ├── tools/
    ├── failure-log.md
    └── report.md
```

Codex does not need to read every file every time. `AGENTS.md` is the entrypoint: it normally starts with `.harness/memory.md` and `.harness/plan.md`, then follows the plan to the active task spec. Architecture context, verification detail, and history are loaded only when the task needs them.

| Record | The question it answers | When it changes |
| --- | --- | --- |
| `AGENTS.md` | Where should a fresh context start, and what repository rules apply? | When rules or project entrypoints change. |
| `memory.md` | What facts must the next Codex still know? | Before ending a piece of work, changing scope, or handing off context. |
| `plan.md` | What is the project moving toward now, and what is next? | When work starts, changes phase, finishes, or blocks. |
| `specs/*.md` | What may this piece change, what makes it done, and what could regress? | Before work, when scope or verification changes, and at completion. |
| `verification.md` | How does this repository normally prove its work? | When verification conventions change. |
| `failure-log.md` | Which failures repeat, and how should they be prevented next time? | When a reusable failure pattern appears. |
| `report.md` | Which decisions, experiments, or milestones are worth keeping? | When the conclusion has durable value. |

`memory.md` is not a chat transcript. It holds only facts that still matter: the current goal, verified environment facts, known risk, and a safe restart point. That lets a fresh context begin quickly and keeps old debugging noise from shaping the next decision.

To check the quality of a handoff, say:

```text
Show me this checkpoint, the current memory, and the next step. Keep only facts that the next context truly needs.
```

---

## Moving a project forward

### The three things worth saying up front

A useful natural-language goal usually contains:

1. **Outcome:** the state you want the project to reach.
2. **Boundary:** what must not change, and which decisions remain yours.
3. **Pace:** whether you want to see a plan first or continue whenever work can be verified.

For example:

```text
Use TauLoop to take the payment page to a releasable state.
Inspect the existing implementation and split it into verifiable specs. Do not change payment providers or create real charges.
Keep completing what you can verify; stop for product tradeoffs or release review.
```

This gives Codex room to move on its own while making the stopping points explicit.

### The normal lifecycle of a piece of work

#### 1. Shape it before editing

For non-trivial work, Codex creates or updates a task spec. Each spec should at least state:

- the goal and non-goals;
- relevant existing code or documents;
- allowed files;
- a checkable implementation list;
- how to verify the result; and
- risks and likely regression points.

That is not paperwork for its own sake. It records both the next action and the conditions under which work must stop, instead of leaving them inside a chat that may end.

#### 2. Execute against the spec

`Allowed files` is the current boundary. If the task needs a wider scope, update the spec before editing new files. For non-trivial work, Codex runs the repository's pre-task check and follows the verification plan recorded in the spec.

#### 3. Finish with evidence

"Implemented" is not enough. A spec records the checks actually run, their outcome, and residual risk. For code, that may be tests, builds, static checks, or a manual verification; for documentation, link, command, and fact checks.

#### 4. Checkpoint before moving on

When a piece ends or scope changes, update memory, the plan, and the spec. Durable conclusions go in `report.md`; reusable failure patterns go in `failure-log.md`. Only then start the next actionable spec or ask for review.

### How you can intervene

| How much control you want | Tell Codex |
| --- | --- |
| See the plan first | "Show me the plan, the spec list, and every definition of done. Do not implement until I approve." |
| Keep moving | "Continue with the current plan. Verify and checkpoint each spec, then start the next unblocked spec." |
| Move only part of it | "Complete only `spec-a` through `spec-c`; do not expand into unrelated work." |
| Review now | "Pause implementation. Show me the current spec's scope, changes, verification, and residual risk." |
| Change context safely | "Checkpoint the current work, update memory and the plan, then hand it to a fresh context." |

### Inspecting the current state

Natural language is the normal path. State lives in files: `.harness/memory.md` keeps current project facts, `.harness/plan.md` the active task and next step, and `.harness/specs/` each task's scope and definition of done. Read them directly or ask the agent to summarize; there is no extra command surface.

---

## Letting long commands finish quietly

### When to use continuous work

Continuous work is for local tasks with ordered stages, a verifier for each stage, and a finite overall boundary:

- downloading dependencies or models, then checking their integrity;
- creating a Python environment, installing packages, and running checks;
- building, then testing or packaging; and
- preparing data before a command with a clear exit condition.

It is not for open-ended research, "keep trying things," work that needs frequent subjective judgment, or a task without a completion check.

### One path from execution to verification

Long tasks follow the `Long-Running Tasks` convention in `AGENTS.md`: the process is owned by the operating system and the agent is a periodic visitor.

```text
write the spec (stage commands, self-checks, expected artifacts)
  -> launch decoupled with nohup/screen; record PID and log path
  -> agent sleeps in-session (coarse intervals)
  -> wake: read the log tail, check the process, compare artifacts
  -> pass: record evidence, move to the next stage
  -> fail: read the log, fix the script, relaunch decoupled
```

A download in progress is not success, and a live process is not success either. With or without repair in between, success is always a new run that actually completed and passed its verification.

This is not an invitation to retry forever. Failures first leave logs and facts. Repair is bounded and controlled: fix the script, re-run, re-verify. Anything that expands authority, scope, or the execution surface goes back to a human gate.

### Let Codex prepare a long-task plan

You usually do not need to author a plan by hand. Say:

```text
Use TauLoop to configure the xxx environment.
Break downloading, installation, and checks into serial stages; write the command, deadline, and self-check for each;
do not start the next stage unless the prior one passes; do not poll download logs.
When a failure is pre-approved and repairable within bounds, let Codex propose a fix and re-verify.
Review the plan with me before executing.
```

The agent turns the long task into a spec (`.harness/specs/`), each stage declaring the command, working directory, network and credential needs, deadline, and verification, and reviews it with you before running.

### How failure handling stays controlled

Repair has boundaries: which files may change, how many attempts, and how much time are all declared in advance in the plan. Any of the following should return to a human gate:

- changing a stage command or its verification, expanding the execution surface;
- adding stages or new destructive command categories;
- widening network, credential, or path permissions;
- extending a deadline or increasing the repair budget;
- touching files outside the plan.

### Execute, inspect, and repair

Launch a long task:

```bash
nohup bash scripts/stage.sh > logs/stage.log 2>&1 &
# or screen -dmS stage bash scripts/stage.sh
```

Record the PID, log path, and expected artifacts in `.harness/plan.md`. The agent sleeps in-session and wakes periodically to check progress with `ps -p <pid>` and the log tail; on failure it fixes the script and re-runs. There is no extra command surface.

### Switch context at a semantic checkpoint

When you finish a piece of work or start an independent new spec, first update `.harness/memory.md` (current facts) and `.harness/plan.md` (next step), and checkpoint the spec. A new context continues from those files; it does not inherit the old chat transcript. It still verifies the working tree and existing evidence first.

> [!IMPORTANT]
> Long-task processes are owned by the operating system. Whether they survive a terminal close or reboot follows nohup/screen semantics; records stay in logs and the plan, enough for conservative diagnosis. It also does not promise that a fresh Codex invocation appears in or focuses a visible Codex Desktop window.

---

## Inspecting progress, recovering, cancelling, and changing context

### Read facts before deciding to continue

When work is interrupted:

1. Read the current `plan`, active spec, and most recent checkpoint.
2. For continuous work, read the run or agent-run state, events, logs, and verifier result.
3. Distinguish verified completion, explicit failure, required human recovery, and a controller whose identity is still observable.
4. Continue only from a state supported by evidence; otherwise review, repair, or start a new contract.

Instead of asking only whether something is still running, ask:

```text
Inspect the current project records and continuous-work state.
Tell me the last verified fact, the current blocker, the next step that is safe to continue, and what needs my decision.
```

| State | What it means | Appropriate action |
| --- | --- | --- |
| `completed` / `all_stages_verified` | Every stage exited and its verifier passed. | Move to the next spec or the agreed review. |
| `waiting_human_final_review` | Technical verification ended, but the contract requires human acceptance. | Review results and evidence, then accept or set the next task. |
| `failed` | A command or verifier failed and evidence was saved. | Review the cause; only an authorized, budgeted, in-scope candidate may attempt bounded repair. |
| `unknown_recovery_needed` | PID, identity, or controller state cannot be confirmed safely. | Do not take it over automatically; read evidence and choose recovery or a new run. |
| `waiting_human` | Policy, budget, repeated failure, or candidate validation needs your decision. | Review the proposed change, risk, and evidence. |
| `cancelled` | The run followed a requested cancellation path. | Check the worktree and state, then clean up, recover, or replan. |

### The minimum before changing context

Before you switch contexts, leave four kinds of facts:

- the current goal, progress, and next action;
- verification that has run and its outcome;
- the state of any worktree, run, or human gate; and
- unresolved risk and decisions nobody should make alone.

TauLoop's `memory`, `plan`, specs, and handoffs are built for this. They are more reliable, and cheaper for the next context, than preserving an ever-growing chat.

---

## Installing, upgrading, and removing

### File ownership

| Kind | Examples | Upgrade rule |
| --- | --- | --- |
| Project-owned records | `AGENTS.md`, memory, plan, specs, brief, reports, verification rules, live state | Never overwritten by an upgrade. |
| Tool-managed runtime files | Files under `.harness/tools/` and `.harness/hooks/` created by initial setup | Updated only when their contents still match the last installed version. |

The installer records managed-file hashes in `.harness/.tau-loop-managed.json`. Modified or unrecognized tools are skipped instead of silently overwritten.

### Upgrade

To refresh to a new release version, run `tau init --root .` — it creates missing files and updates unmodified managed tools to the new version; files you changed are kept. The installer records managed-file hashes in `.harness/.tau-loop-managed.json`.

### Remove

```bash
tau uninstall --root .
```

This removes only unchanged tool-managed hooks, tools, and the enrollment marker. It intentionally keeps project records and live state for recovery or audit. Remove them manually only after you no longer need them.

To remove the user-level skill and command:

```bash
python3 install.py --uninstall
```

---

## Safety boundaries and human decisions

TauLoop's rule is: **verify, then continue; when uncertain, leave facts and stop.**

### Decisions that remain human

- New permissions, network access, credential use, or real spending.
- Irreversible changes, deletion, release, migration, or external writes.
- Product tradeoffs, prioritization, or business judgment.
- A strategy change after a verifier fails.
- A proposal that expands files, command capability, time, or agent budget.
- Final review when the project or contract requires it.

### Promises it must not make

- A heartbeat only shows that the supervisor recently observed a process it owns; it does not prove success.
- A fixture proves control-plane behavior, not that Python, PyTorch, CUDA, a GPU, a simulator, or your production environment works. Verify those in the named target project.
- The continuous-work core is foreground and local. It does not survive a closed terminal, dead controller, or reboot by magic.
- A fresh Codex invocation can read handoff or worker facts, but is not guaranteed to create, display, or focus a visible Codex Desktop window.
- Contract permissions are review and audit boundaries, not operating-system isolation.

### Sensitive information

Do not put tokens, passwords, private paths, or unredacted logs in a plan, handoff, issue, or pull request. When a plan needs to declare credentials, declare the purpose and boundary, not the secret itself.

For a suspected vulnerability, credential leak, unsafe deletion path, or command-injection risk, do not open a public issue. Use the repository's [security policy](../../SECURITY.md) and GitHub Security Advisories.

---

## Contributing and troubleshooting

### What contributions should preserve

TauLoop stays deliberately light: Python 3.8+, standard library first, and portable across macOS and Ubuntu. Keep the complete-turn boundary intact: specify, run, verify, checkpoint, then review or hand off.

Do not turn a small change into a daemon, dashboard, or unverified Codex Desktop automation. A small feature should not quietly become an opaque execution platform.

### Before contributing

1. Read the [contribution guide](../../CONTRIBUTING.md) and relevant implementation material.
2. Keep the change focused on one clear behavior and state its compatibility impact.
3. Update or add a fixture when lifecycle or supervisor behavior changes.
4. State command, permission, and capability limits precisely; fixture success is not a hardware or Desktop guarantee.
5. In a pull request, report user-visible behavior, verification, and residual risk.

### Common problems

**`tau: command not found`**

Check the installation and whether `~/.codex/bin` is on `PATH`. Run `tau --help` to verify.

**How should a long task be launched?**

First run `tau init --root .` in the project. Long tasks follow the `Long-Running Tasks` convention in `AGENTS.md`: write a spec, launch decoupled with `nohup`/`screen`, sleep in-session, wake and check the log and process, and close out with verification evidence.

**Continuous work did not resume after interruption**

After an interruption, read the last recorded evidence in `.harness/plan.md` and the spec, confirm the facts, then decide whether to continue or change direction.

**Not sure which command handles failure repair**

On failure the agent reads the log, fixes the script, and relaunches decoupled, until verification passes or the work reaches a human gate. If tool files are missing, run `tau init --root .` to refresh.

**Codex keeps asking small questions**

Usually the goal, boundary, or definition of done is not yet clear, or the task reached a genuine human gate. Ask it to show the current plan and spec, then record the scope it may advance on its own and the decisions where it must stop.

---

## Glossary and command reference

### The few terms worth knowing

| Term | In one sentence |
| --- | --- |
| Goal | The project outcome you actually want. |
| Task / spec | A checkable unit of work; a spec records scope, definition of done, and verification. |
| Verification | Reproducible evidence about a result, not Codex's opinion. |
| Checkpoint | The factual record left after a piece of work, including what is next. |
| Memory | Project facts that still matter later, not a chat transcript. |
| Handoff | A bounded package for a fresh context, carrying only facts it needs to continue. |
| Run contract | A reviewable plan for long work: commands, permissions, limits, stages, and verifiers. |
| Verifier | The command that decides whether a completed stage actually met its condition. |
| Continuous work | TauLoop's supervision for bounded, serial local commands. |
| Agent loop | The bounded repair controller that starts a fresh worker only under a declared policy. |

### Common commands

```bash
# The only command surface
tau init --root .     # create or refresh the project skeleton (AGENTS.md + .harness/)
tau --help
```

Uninstall via `python3 install.py --uninstall`. Everything else is convention, not command.

### Keep reading

- [First use](first-use.en.md)
- [Security policy](../../SECURITY.md)
- [Contributing](../../CONTRIBUTING.md)

You have enough to start. Tell Codex where the project should go, then add: "Keep going when you can verify the work yourself; stop only when a real decision is mine."
