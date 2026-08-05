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

Codex installs TauLoop, determines whether this is a new or existing project, creates the records it needs, and breaks the work into checkable pieces. You do not need to know what `spec`, `checkpoint`, `harness`, or `cw` mean first.

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

For an existing project with its own `AGENTS.md`, `.codex/`, or collaboration rules:

```bash
tau adopt --root .
```

Both commands create missing files by default and do not overwrite existing project records. After that, tell Codex the outcome you need.

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

After you enable it, a project has `AGENTS.md` and `.codex/`. They are not another application subsystem; they are shared project records for the current and next Codex.

```text
your-project/
├── AGENTS.md
└── .codex/
    ├── memory.md
    ├── plan.md
    ├── brief.md
    ├── specs/
    ├── verification.md
    ├── verification-profiles/
    ├── hooks/
    ├── tools/
    ├── state/
    ├── failure-log.md
    └── report.md
```

Codex does not need to read every file every time. `AGENTS.md` is the entrypoint: it normally starts with `.codex/memory.md` and `.codex/plan.md`, then follows the plan to the active task spec. Architecture context, verification detail, and history are loaded only when the task needs them.

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

### Inspecting durable project state

Natural language is the normal path. When you need the machine-readable state records, use:

```bash
tau state init --root .
tau status --root .
tau state next --root .
tau state recover --root .
tau doctor --root .
```

- `tau status` summarizes project, spec, session, worktree, and human-gate state.
- `tau state next` recommends the next serial control action.
- `tau state recover` conservatively checks interrupted or lost sessions, missing worktrees, and unresolved gates; it does not pretend to resume them automatically.
- `tau doctor` reports actionable health and reliability findings.

These are observability tools, not commands every user needs to memorize. Ask Codex to run and explain them when useful.

---

## Letting long commands finish quietly

### When to use continuous work

Continuous work is for local tasks with ordered stages, a verifier for each stage, and a finite overall boundary:

- downloading dependencies or models, then checking their integrity;
- creating a Python environment, installing packages, and running checks;
- building, then testing or packaging; and
- preparing data before a command with a clear exit condition.

It is not for open-ended research, "keep trying things," work that needs frequent subjective judgment, or a task without a completion check.

### One path from execution to repair

`cw` is a foreground local controller. It starts and owns child processes, waits for their exit, records low-noise health evidence while a process can be observed, and advances only after a verifier passes.

```text
stage command starts
  -> local supervisor observes the managed process
  -> command exits
  -> verifier runs
  -> pass: next stage
  -> failure: record facts
       -> contract allows it and budget remains: an isolated Codex worker proposes a bounded repair
          -> controller validates the patch, permissions, and command boundary
          -> a fresh run verifies again
       -> otherwise: human gate
```

A download in progress is not success, and neither is a heartbeat. Whether or not a repair happens in the middle, success comes only from a new run that actually completes and passes its verifier.

This is not an invitation to retry forever. A failure first records a run snapshot, events, stdout/stderr, and a failure fingerprint. Only a failure class declared in the contract may start a fresh, time-bounded Codex worker. That worker can propose a candidate repair; it cannot turn the old failed run into success.

### Let Codex prepare the contract

You usually do not need to author a contract. Say:

```text
Use TauLoop to set up xxx.
Split downloading, installation, and checks into serial stages. Give every stage a command, deadline, and verifier. Do not start the next stage unless the previous one passes, and do not poll download logs frequently.
For a pre-approved failure that can be fixed within a narrow scope, let Codex propose a repair and verify it again.
Show me the run contract for review before executing it.
```

Codex starts from `assets/examples/cw-environment-bootstrap.template.md`. Every stage uses JSON-array `argv`, never a hidden shell string, and declares working paths, network and credential needs, deadlines, verification commands, and final review.

This shortened example includes a bounded-repair policy. Omit `agent_loop` when the task only needs quiet waiting and verification. Replace every path, limit, and verifier with facts from the target project.

```json
{
  "schema_version": "cw-run-contract/v2",
  "id": "prepare-environment",
  "permissions": {
    "network": "required",
    "credentials": "none",
    "path_roots": ["."]
  },
  "limits": {
    "max_run_seconds": 3600,
    "health_interval_seconds": 60,
    "terminate_grace_seconds": 30,
    "max_stage_attempts": 1,
    "max_handoffs": 1
  },
  "stages": [
    {
      "id": "install",
      "argv": ["python3", "-m", "pip", "install", "-r", "requirements.txt"],
      "cwd": ".",
      "deadline_seconds": 1800,
      "verifier": {
        "argv": ["python3", "-c", "import example_package"],
        "cwd": "."
      }
    }
  ],
  "agent_loop": {
    "mode": "assisted",
    "repair_on": ["command_failed", "verifier_failed"],
    "max_repair_turns": 2,
    "max_total_agent_seconds": 1800,
    "allowed_files": ["scripts/repair_environment.py"],
    "allowed_contract_roots": [".codex/contracts"],
    "candidate_checks": [
      {
        "id": "repair-script-syntax",
        "argv": ["python3", "-m", "py_compile", "scripts/repair_environment.py"],
        "cwd": "."
      }
    ],
    "repair_execution_policy": "same_argv_only",
    "require_clean_git": true,
    "require_final_review": true
  }
}
```

`permissions` is an audit boundary, not an operating-system sandbox. Review it like code: what the command does, where it runs, whether it uses the network or credentials, and which important paths it can touch.

### How repair stays bounded

`agent_loop` is explicit authority for what may happen after a failure. It requires a Git worktree, finite repair count and agent time, an allowlist of editable files, allowed locations for replacement contracts, and checks the controller can run by itself.

The most important restriction is `repair_execution_policy: "same_argv_only"`. A repair may change allowlisted implementation files and create a revisioned replacement contract, but it cannot widen the execution surface. These changes are rejected and become a human gate:

- changing a stage or verifier `argv`, working directory, or environment;
- adding a stage or a new destructive command category;
- expanding network, credential, or path permissions;
- increasing deadlines, repair turns, agent time, or other budgets; or
- touching a file outside the allowlist or failing a predeclared candidate check.

Start with `mode: "assisted"`. `unattended` is only for a contract family with successful evidence and an operator who explicitly enables it; it cannot cross the same boundaries.

### Run, inspect, repair, and cancel

Initialize project state, then start an ordinary serial run:

```bash
tau state init --root .
tau run --root . path/to/contract.json
```

Each run has a run id. Inspect evidence, request a stop, or diagnose an interruption with:

```bash
tau run-status --root . <run-id>
tau cancel --root . <run-id>
tau recover --root . <run-id>
```

When a contract declares `agent_loop` and you want the controller to handle pre-approved, bounded repairs, use:

```bash
tau loop --root . path/to/contract.json
tau loop-status --root . <loop-id>
tau loop-recover --root . <loop-id>
tau loop-cancel --root . <loop-id>
```

The controller keeps loop state, events, repair cases, worker logs, decisions, and candidate patches in `.codex/agent-loops/<loop-id>/`. Each actual stage run still has separate evidence under `.codex/runs/<run-id>/`.

If a deadline expires, a PID is absent or mismatched, or an old controller cannot be confirmed, work becomes `unknown_recovery_needed`. That is not a signal to try again blindly. Read the snapshot, events, and logs, then choose recovery, a revised contract, a new run, or a human decision.

The controller always stops for a human when a failure is not authorized, the same fingerprint repeats, budget is exhausted, a worker fails or times out, a candidate leaves scope, a candidate contract changes the execution surface, a check fails, or permissions, spending, irreversible work, or product judgment would change.

### Hand off at a semantic checkpoint

After a completed run, or before an independent new spec, create a bounded handoff:

```bash
tau handoff create --root . --run-id <run-id> \
  --spec-path .codex/specs/<spec>.md \
  --next-action "Verify the current worktree and carry out the next step" \
  --allowed-file src/example.py \
  --checkpoint-ref .codex/memory.md \
  --final-review

tau handoff launch --root . <handoff-id>
tau handoff review --root . <handoff-id>
```

The fresh invocation receives a package of checkpoints, evidence references, allowed files, and next actions, not the old chat. It must still verify the worktree and evidence. `--final-review` retains the final human acceptance gate.

> [!IMPORTANT]
> Continuous work is foreground and local. It does not promise to continue after the terminal closes, the controller is killed, or the computer restarts. It leaves enough records for conservative diagnosis. It also does not promise that a fresh Codex invocation appears in or focuses a visible Codex Desktop window.

---

## Inspecting progress, recovering, cancelling, and changing context

### Read facts before deciding to continue

When work is interrupted:

1. Read the current `plan`, active spec, and most recent checkpoint.
2. For continuous work, read the run or loop state, events, logs, and verifier result.
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
| Tool-managed runtime files | Files under `.codex/tools/` and `.codex/hooks/` created by initial setup | Updated only when their contents still match the last installed version. |

The installer records managed-file hashes in `.codex/.tau-loop-managed.json`. Modified or unrecognized tools are skipped instead of silently overwritten.

### Upgrade

Inspect the plan first:

```bash
tau upgrade --root . --dry-run
```

Then apply it:

```bash
tau upgrade --root .
```

`--force` can overwrite files, but only after reviewing the diff. It cannot resolve a semantic conflict between project records and new tools for you.

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

Do not put tokens, passwords, private paths, or unredacted logs in a run contract, handoff, issue, or pull request. When a contract needs to declare credentials, declare the purpose and boundary, not the secret itself.

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

**`tau run` cannot find the supervisor or control plane**

Run `tau init --root .` or `tau adopt --root .` in the target project. Continuous work needs repo-local files in `.codex/tools/`; installing the user-level skill alone does not create them for every project.

**Continuous work did not resume after interruption**

That is deliberate. Run `tau recover --root . <run-id>` and inspect the snapshot, events, and logs under `.codex/runs/<run-id>/`. Use the evidence to choose recovery, a contract change, or a fresh run.

**`tau loop` cannot be found**

Run `tau upgrade --root . --dry-run` to inspect the project tools, then upgrade to a TauLoop version containing the current continuous-work runtime. Do not assemble a substitute path from unrelated commands.

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
# Project lifecycle
tau init --root .
tau adopt --root .
tau upgrade --root . --dry-run
tau uninstall --root .

# Project state
tau state init --root .
tau status --root .
tau state next --root .
tau state recover --root .
tau doctor --root .

# Run a continuous-work contract
tau run --root . path/to/contract.json
tau run-status --root . <run-id>
tau cancel --root . <run-id>
tau recover --root . <run-id>

# Handoff at a checkpoint
tau handoff create --root . ...
tau handoff launch --root . <handoff-id>
tau handoff review --root . <handoff-id>

# Handle a failure within the contract's declared scope
tau loop --root . path/to/contract.json
tau loop-status --root . <loop-id>
tau loop-recover --root . <loop-id>
tau loop-cancel --root . <loop-id>
```

### Keep reading

- [First use](first-use.en.md)
- [Security policy](../../SECURITY.md)
- [Contributing](../../CONTRIBUTING.md)

You have enough to start. Tell Codex where the project should go, then add: "Keep going when you can verify the work yourself; stop only when a real decision is mine."
