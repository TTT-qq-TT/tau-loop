# TauLoop 完整使用手册

[English](user-manual.en.md) | **简体中文**

> 把目标交给 Codex。TauLoop 负责让项目留下计划、证据和下一步。
>
> 这不是一套要求你背下来的「agent workflow」课程。它是一组放在项目里的记录和执行工具：一段工作完成后，下一段能据此继续；需要等待的命令由本地进程等待；真正属于你的决定仍然回到你手里。

## 目录

- [先用起来](#先用起来)
- [TauLoop 解决什么，又不替你决定什么](#tauloop-解决什么又不替你决定什么)
- [项目如何留下记忆](#项目如何留下记忆)
- [日常推进一个项目](#日常推进一个项目)
- [让长命令安静地完成](#让长命令安静地完成)
- [查看进度、恢复、取消与换上下文](#查看进度恢复取消与换上下文)
- [安装、升级与移除](#安装升级与移除)
- [安全边界与人工决定](#安全边界与人工决定)
- [贡献与排错](#贡献与排错)
- [名词与命令速查](#名词与命令速查)

---

## 先用起来

### 最推荐的开始方式：说清目标

把下面这段话连同 TauLoop 仓库链接发给 Codex，将 `xxx` 换成你的结果即可：

```text
请阅读并安装 https://github.com/TTT-qq-TT/tau-loop ，然后用 TauLoop 把当前项目推进到 xxx。

能自己验证的就继续；真正需要我决定时再停下来。
```

Codex 会安装 TauLoop、判断项目是新项目还是已有项目、创建必要的项目记录，并先把工作拆成可检查的部分。你不需要先知道 `spec`、`checkpoint`、`harness` 或 `cw` 分别是什么。

如果你希望先看方案，在最后补一句：

```text
先只给我看计划和每一段的完成标准，等我确认后再开始。
```

### 手动安装

只有在 Codex 请你手动安装，或你需要排错时，才需要执行下面三行：

需要 Codex 与 Python 3.8+；当前支持 macOS 和 Ubuntu。只有使用受限修复时，项目才需要在 Git 工作树中。

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

安装后，TauLoop 会放入两个用户级位置：

- `~/.codex/skills/tau-loop/`：供 Codex 发现和阅读的 skill。
- `~/.codex/bin/tau`：项目工作流与连续工作的命令入口。

若终端找不到 `tau`，将 `~/.codex/bin` 加入 `PATH`，再检查：

```bash
tau --help
```

### 在项目中启用

新项目使用：

```bash
tau init --root .
```

已有 `AGENTS.md`、`.codex/` 或既有协作规则的项目，使用更明确的：

```bash
tau adopt --root .
```

两者默认都只补齐缺失文件，不会覆盖已有的项目记录。之后直接告诉 Codex 你要达到的目标即可。

---

## TauLoop 解决什么，又不替你决定什么

TauLoop 的重点不是让 Codex 永远运行，而是让每一段工作走完一个可追溯的闭环：

```text
目标 -> 可检查的一步 -> 实现 -> 验证 -> checkpoint -> 下一步或你的决定
```

它主要处理五种很常见的断点。

| 你遇到的时刻 | TauLoop 留下或执行什么 | 结果 |
| --- | --- | --- |
| Codex 在最早的一步停住，等待一个本可自行判断的小决定。 | `plan` 和 `spec` 先写清目标、范围、完成标准与验证。 | 目标和边界已经明确时，它有下一步可走。 |
| 换了窗口或上下文后，项目像被重新认识一遍。 | `memory`、`plan`、`spec` 和 `checkpoint` 保存在仓库。 | 新上下文读取项目事实，而不是猜测旧聊天发生过什么。 |
| 下载、安装、构建时，聊天不断轮询日志，或半路不再继续。 | `continuous-work` 监督真实本地进程，记录低频健康证据。 | 前一步验证通过后才开始下一步；等待不占用聊天。 |
| 项目推进像一串临时对话，没有阶段感。 | 每个非小任务都有范围、验证和收口记录。 | 你能检查正在做什么、为何算完成、接下来是什么。 |
| 上下文快满时不敢继续。 | checkpoint 和有界 handoff 只带走下一次需要的事实。 | 换上下文是一次可审查的交接，不是遗忘或整段聊天搬家。 |

TauLoop 也有明确的边界。它不替你批准新权限、花费、不可逆操作；也不会把一个还在运行的进程、一次 heartbeat 或一份很长的日志当成成功。验证失败、依赖缺失、风险扩大或需要产品判断时，它应该停在一个能被你检查的人工关口。

---

## 项目如何留下记忆

启用后，项目根目录会多出 `AGENTS.md` 和 `.codex/`。它们不是另一套业务代码，而是给当前与下一次 Codex 共同使用的项目记录。

### 最小结构

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

不需要每次都读完这些文件。`AGENTS.md` 是入口，告诉 Codex 先读什么；它通常会先读 `.codex/memory.md`、`.codex/plan.md`，再按计划指向当前的 task spec。详细的架构背景、验证规则和历史记录只在任务确实需要时加载。

| 记录 | 它回答的问题 | 什么时候更新 |
| --- | --- | --- |
| `AGENTS.md` | 新上下文应该从哪里开始、遵守什么仓库规则？ | 规则或项目入口变化时。 |
| `memory.md` | 下一位 Codex 仍必须知道哪些当前事实？ | 每次结束一段工作、切换任务或准备换上下文前。 |
| `plan.md` | 当前项目正在推进什么，下一步是什么？ | 任务开始、阶段切换、完成或阻塞时。 |
| `specs/*.md` | 这一小段允许改哪里，怎样才算完成，有什么风险？ | 开工前；范围或验证变化时；完成时记录证据。 |
| `verification.md` | 本项目默认怎样验证？ | 项目验证约定变化时。 |
| `failure-log.md` | 哪些失败曾重复发生，今后怎样防止？ | 发现可复用的失败模式时。 |
| `report.md` | 哪些决定、试验或里程碑值得长期保存？ | 形成长期可复用的结论时。 |

### 记忆不是聊天全文

`memory.md` 保存的是仍然有用的结论，例如：当前目标、已验证的环境事实、已知风险、下一次安全的开始点。它不是聊天逐字稿。

这样做有两个好处：

1. 新上下文可以很快知道项目真相，不必消耗大量上下文重读无关过程。
2. 过去的猜测、已解决的调试噪声不会长期影响下一次判断。

当你想确认交接质量，可以直接问：

```text
给我看这次 checkpoint、当前 memory 和下一步；只保留下一次真正需要的事实。
```

---

## 日常推进一个项目

### 你需要说清的三件事

一段足够好的自然语言目标通常包含：

1. **结果**：希望项目到达什么状态。
2. **边界**：哪些地方不能动，哪些决定必须交给你。
3. **推进方式**：先看方案，还是在可验证时持续推进。

例如：

```text
用 TauLoop 把支付页面推进到可上线。
先检查现有实现，拆成可验证的 specs；不改变支付渠道、不产生任何真实扣费。
能验证的部分持续完成，涉及产品取舍或发布时停下来给我 review。
```

比起「帮我优化一下」，这样的目标能让 Codex 在合理范围内自行前进，也让你知道它在哪里必须停下。

### 一段正常工作的生命周期

#### 1. 先塑形，不急着改

对于非小任务，Codex 应先创建或更新 task spec。每个 spec 至少有：

- 目标与非目标；
- 可参考的已有代码或文档；
- 允许改动的文件范围；
- 可检查的完成清单；
- 验证方法；
- 风险与可能回归点。

这一步不是额外的文书工作。它把「应该继续做什么」和「什么情况下必须停下」写在项目里，而不留在一段随时会结束的对话中。

#### 2. 按 spec 执行

执行时，Codex 应把 `Allowed files` 当作当前边界。若发现完成任务必须扩大范围，应先更新 spec，再动新文件。对非小任务，它会运行仓库的 pre-task 检查，并按 spec 中的验证计划推进。

#### 3. 用证据完成，而不是用一句话完成

「已经实现」不够。每个 spec 应记录实际运行过的检查、结果和残余风险。针对代码改动，可能是测试、构建、静态检查或手动验证；针对文档，则是链接、命令和事实一致性检查。

#### 4. 写 checkpoint，再进入下一段

一段工作结束或切换时，更新当前记忆、计划和 spec。需要长期保留的结论进入 `report.md`；可重复的失败模式进入 `failure-log.md`。然后再进入下一份可执行 spec，或请求你的 review。

### 你可以怎样介入

| 你想要的控制程度 | 直接对 Codex 说 |
| --- | --- |
| 先只看方案 | 「先给我看计划、spec 列表和每个 spec 的完成标准；我确认前不要实现。」 |
| 持续推进 | 「按当前计划继续；每个 spec 验证并写 checkpoint 后，直接开始下一个未阻塞的 spec。」 |
| 只推进一部分 | 「只完成 `spec-a` 到 `spec-c`，不要扩展到无关工作。」 |
| 做一次审查 | 「暂停实现，给我看当前 spec 的范围、变更、验证结果和残余风险。」 |
| 安全换上下文 | 「先把当前工作 checkpoint 好，更新 memory 和 plan，再交给一个新上下文继续。」 |

### 需要查看机械状态时

日常项目工作以自然语言为主。若项目需要查看持久的状态记录，可使用：

```bash
tau state init --root .
tau status --root .
tau state next --root .
tau state recover --root .
tau doctor --root .
```

其中：

- `tau status` 汇总项目、spec、会话、工作树和人工关口的状态。
- `tau state next` 给出下一个建议的串行控制动作。
- `tau state recover` 保守地检查中断、失联会话、缺失工作树或未解决关口；它不会假装自动恢复。
- `tau doctor` 给出可执行的健康与可靠性发现。

这些命令是可观察性工具，不要求每位用户手动操作。你也可以请 Codex 在需要时运行并解释它们。

---

## 让长命令安静地完成

### 什么时候应该交给连续工作

连续工作（continuous-work） 适合**步骤有顺序、每步都能验证、总时长有边界**的本地任务，例如：

- 下载依赖或模型，再校验文件完整性；
- 创建 Python 环境，再安装包、运行检查；
- 构建，再运行测试或打包验证；
- 准备数据，再执行一个有明确退出条件的任务。

它不适合没有结束标准的开放式研究、单纯的「一直想办法」、需要频繁主观判断的创作，或无法写出验证条件的工作。

### 一条从执行到修复的路径

`cw` 是一个**前台、本地**的控制器。它启动并拥有实际子进程，等待进程退出，在可观察到进程时低频写入健康证据，并且只有 verifier 通过才会开始下一阶段。

```text
阶段命令开始
  -> 本地 supervisor 观察受管进程
  -> 命令退出
  -> verifier 运行
  -> 通过：下一阶段
  -> 未通过：保存事实
       -> 合同已允许且仍有预算：隔离的 Codex worker 提出受限修复
          -> 控制器验证补丁、权限和命令边界
          -> 新的一次运行重新验证
       -> 其余情况：停在人工关口
```

因此，下载正在进行不是成功，heartbeat 也不是成功。无论中间是否发生修复，成功始终来自一份新的、实际完成并通过 verifier 的运行。

这不是「让 Codex 无限重试直到成功」。失败会先留下 run snapshot、事件、stdout/stderr 与失败指纹。只有事先写进合同的失败类型，才可能触发一次新的、有限时间的 Codex worker；它只能提交候选修复，不能把旧失败记录改写成成功。

### 让 Codex 替你准备一份合同

通常不需要手写 contract。这样说即可：

```text
用 TauLoop 配置 xxx 环境。
把下载、安装和检查拆成串行阶段；每阶段写清命令、截止时间和 verifier；
前一步没有通过验证就不要开始下一步；不要频繁轮询下载日志。
遇到已经预先允许、且能在受限范围内修复的失败时，再让 Codex 提出修复并重新验证。
先把 run contract 给我审阅，再执行。
```

Codex 会以 `assets/examples/cw-environment-bootstrap.template.md` 为起点，写一份 JSON run contract。每一阶段必须包含 JSON 数组形式的 `argv`，不能把一长段 shell 字符串藏进去；还要声明工作目录、可用路径、网络与凭据需求、deadline、验证命令和最终 review。

下面是一份包含受限修复策略的缩短示意。若任务只需要安静地等待和验证，可以省略 `agent_loop`；它不是必填项。真实 contract 必须按项目补全路径、限制和 verifier：

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

`permissions` 是审阅边界，不是操作系统 sandbox。像审查代码一样审查它：命令会做什么、在哪里运行、是否联网、是否涉及凭据、是否会修改重要文件。

### 修复策略怎样保持受控

`agent_loop` 是「失败后可以做什么」的明确授权。它要求 Git 工作树、有限的修复次数和总 agent 时间、允许修改的文件、允许写入替代合同的位置，以及 controller 能独立运行的候选检查。

最重要的限制是 `repair_execution_policy: "same_argv_only"`：修复可以改 allowlist 中的实现文件，并生成一份新的 revisioned contract；但不能扩大执行面。下面任一变化都会被拒绝并转为人工关口：

- 修改阶段命令或 verifier 的 `argv`、工作目录或环境；
- 新增阶段或新的破坏性命令类别；
- 扩大网络、凭据或路径权限；
- 延长 deadline，增加修复轮数、agent 时间或其他预算；
- 改动 allowlist 外的文件，或未通过预声明的候选检查。

默认从 `mode: "assisted"` 开始。`unattended` 只适用于已经有相同合同家族成功证据、且由操作者明确打开的场景；它同样不能越过这些边界。

### 执行、查看、修复与取消

先初始化项目状态。正常的串行运行使用：

```bash
tau state init --root .
tau run --root . path/to/contract.json
```

运行会创建一个 run id。查看证据、请求停止或在中断后检查：

```bash
tau run-status --root . <run-id>
tau cancel --root . <run-id>
tau recover --root . <run-id>
```

当阶段失败且属于可修复类型时，用 **agent 主导的连续工作**处理：主导 agent 会被唤醒，直接修复后重跑，直到全部阶段通过或到达人工关口。

```bash
tau agent-run --dry-run   # 本机：只打印唤醒决策，不真实调用 agent
tau agent-run             # 真实：resume 主导 agent 修复并重跑
```

agent-run 会记录事件、账本、失败分类与每次尝试的决策；每次真实阶段运行仍有自己的证据目录可复查。

出现 deadline 到期、PID 不存在、PID 身份与记录不一致，或无法确认旧 controller 的情况时，运行会进入 `unknown_recovery_needed`。这不是「可以继续试一下」的信号。先阅读 snapshot、事件和日志，再决定是否恢复、修改合同后重新开始，或交给人工处理。

以下情况一定停在人工关口：失败类型未获授权、同一个失败 fingerprint 重复出现、修复预算耗尽、worker 启动失败或超时、候选补丁越界、候选合同改变执行面、候选检查失败，以及任何权限、花费、不可逆操作或业务判断需要改变。

### 在语义检查点换一个 Codex

完成一个 run，或开始一份彼此独立的新 spec 时，可以创建一个只带必要事实的 handoff：

```bash
tau handoff create --root . --run-id <run-id> \
  --spec-path .codex/specs/<spec>.md \
  --next-action "验证当前工作树并执行下一步" \
  --allowed-file src/example.py \
  --checkpoint-ref .codex/memory.md \
  --final-review

tau handoff launch --root . <handoff-id>
tau handoff review --root . <handoff-id>
```

新 invocation 读取的是 handoff package 中的 checkpoint、证据引用、允许文件和下一步，不会继承旧聊天全文。它仍要先验证工作树和已有证据。`--final-review` 保留最终人工验收关口。

> [!IMPORTANT]
> 连续工作是前台本地工具。终端关闭、控制器被杀死或电脑重启后，它不承诺继续运行；它只会留下足以保守诊断的记录。也不承诺新 Codex invocation 自动出现在或聚焦到可见的 Codex Desktop 窗口。

---

## 查看进度、恢复、取消与换上下文

### 先看事实，再决定是否继续

遇到中断时，按下面顺序处理：

1. 查看当前 `plan`、active spec 和最近 checkpoint，确认项目原本在做什么。
2. 若是连续工作，查看 run 或 agent-run 的状态、事件、日志和 verifier 结果。
3. 区分「已验证完成」「明确失败」「需要人工恢复」「仍在被可确认的 controller 管理」。
4. 只从有明确证据的状态继续；其余情况重新审阅、修复或新建 contract。

不建议只问「还在不在跑」。更有用的问法是：

```text
检查当前项目记录和连续工作状态。
告诉我最后一个已验证的事实、当前阻塞、可安全继续的下一步，以及需要我决定的事。
```

### 常见状态的含义

| 状态 | 意味着什么 | 合理动作 |
| --- | --- | --- |
| `completed` / `all_stages_verified` | 每个阶段退出且 verifier 通过。 | 进入下一份 spec，或按约定 review。 |
| `waiting_human_final_review` | 技术验证结束，但 contract 要求人工验收。 | 查看成果和证据，明确接受或提出下一项工作。 |
| `failed` | 命令或 verifier 失败，证据已保存。 | 审查失败原因；只有合同已授权、预算仍在且候选受限时，才会尝试一次有界修复。 |
| `unknown_recovery_needed` | PID、身份或 controller 状态无法安全确认。 | 不自动接管；阅读证据后选择恢复或新 run。 |
| `waiting_human` | 策略、预算、重复失败或候选验证要求你决定。 | 审阅提出的变更、风险与证据。 |
| `cancelled` | 运行已收到取消请求并完成停止路径。 | 检查工作树和状态；决定清理、恢复或重新规划。 |

### 换上下文时的最小动作

上下文变长不等于项目变危险。真正重要的是在切换前留下这四类事实：

- 当前目标、完成进度与下一步；
- 已运行的验证及其结果；
- 当前工作树、连续 run 或人工关口的状态；
- 尚未解决的风险与不可自行决定的事项。

TauLoop 的 `memory`、`plan`、spec 和 handoff 正是为此服务。它们比保留一段不断膨胀的聊天更可靠，也更节省下一次的上下文。

---

## 安装、升级与移除

### 文件所有权

TauLoop 将文件分成两类：

| 类别 | 示例 | 升级时的规则 |
| --- | --- | --- |
| 项目拥有的记录 | `AGENTS.md`、memory、plan、spec、brief、report、验证规则、live state | 不由升级覆盖。 |
| 工具管理的运行文件 | `.codex/tools/`、`.codex/hooks/` 中由首次初始化创建的文件 | 只有当前内容仍等于上次安装版本时才更新。 |

安装器会在 `.codex/.tau-loop-managed.json` 记录工具管理文件的哈希。你改过的或无法识别的工具会被跳过，而不是被静默覆盖。

### 升级

先看计划：

```bash
tau upgrade --root . --dry-run
```

确认后再执行：

```bash
tau upgrade --root .
```

`--force` 可以覆盖，但只应在审阅 diff 后使用。它不能替你解决项目记录与新工具之间的语义冲突。

### 移除

```bash
tau uninstall --root .
```

此操作只移除未修改的工具管理 hooks、tools 和 enrollment marker，刻意保留项目记录与 live state，以便恢复或审计。确定再也不需要它们后，才手动删除。

移除用户级 skill 与命令：

```bash
python3 install.py --uninstall
```

---

## 安全边界与人工决定

TauLoop 的原则是：**先验证，再继续；不确定就留下事实并停下。**

### 必须由人决定的事

- 新权限、网络访问、凭据使用或实际花费；
- 不可逆修改、删除、发布、迁移或外部系统写入；
- 需要产品取舍、优先级或业务判断的选择；
- verifier 失败后的策略改变；
- 需要扩大文件范围、命令能力、时间或 agent 预算的 proposal；
- 最终 review，若项目或 run contract 明确要求。

### 不应作出的承诺

- heartbeat 只能说明 supervisor 最近观察到它拥有的本地进程，不证明工作成功。
- fixture 通过只能证明控制面行为；不能证明 Python、PyTorch、CUDA、GPU、模拟器或你的生产环境已经可用。必须在命名的目标项目中验证。
- 连续工作核心是前台本地运行；不会在终端关闭、控制器死亡或电脑重启后神奇地持续。
- 新 Codex invocation 可以从 handoff 或 worker 输入中读取事实，但不保证创建、显示或聚焦一个可见的 Codex Desktop 窗口。
- contract 中的 permissions 是审阅与审计边界，不是操作系统级隔离。

### 处理敏感信息

不要把 token、密码、私有路径或未脱敏日志写入 run contract、handoff、issue 或 pull request。contract 中若确实需要声明凭据需求，应声明用途和边界，而不是把密钥本身存进去。

发现疑似安全问题、凭据泄露、危险删除或命令注入风险时，不要公开开 issue；按仓库的[安全策略](../../SECURITY.md)通过 GitHub Security Advisory 私下报告。

---

## 贡献与排错

### 贡献时保持什么不变

TauLoop 希望保持轻量：Python 3.8+、标准库优先、macOS 与 Ubuntu 可移植。一次完整 turn 的边界也应保持：指定、执行、验证、checkpoint，再 review 或 handoff。

贡献新能力时，请避免顺手把它变成 daemon、dashboard 或未经验证的 Codex Desktop 自动化。一个小功能不应悄悄扩张为难以审计的运行平台。

### 贡献前检查

1. 阅读 [贡献指南](../../CONTRIBUTING.md) 和相关的详细文档。
2. 把变更范围控制在一个清楚的行为上，并说明兼容性影响。
3. 修改 lifecycle 或 supervisor 行为时，增加或更新对应 fixture。
4. 对命令、权限与限制作精确描述，不能把 fixture 成功写成硬件或桌面能力保证。
5. 在 pull request 中写明用户可见行为、验证结果和残余风险。

### 常见问题

**`tau: command not found`**

检查安装是否成功，并确认 `~/.codex/bin` 已进入终端 `PATH`。运行 `tau --help` 验证。

**`tau run` 提示找不到 supervisor 或 control plane**

先在目标项目中运行 `tau init --root .` 或 `tau adopt --root .`。连续工作需要 repo-local 的 `.codex/tools/` 文件；仅安装用户级 skill 不会替每个项目创建它们。

**连续工作在中断后没有自动继续**

这是预期的保守行为。执行 `tau recover --root . <run-id>`，检查 `.codex/runs/<run-id>/` 中的 snapshot、事件和日志。确认事实后再决定继续、修复 contract 或开始新的 run。

**想处理失败修复但不知道用什么命令**

用 agent 主导的连续工作：先 `tau agent-run --dry-run` 在本机试跑（不真实调用 agent），确认唤醒决策符合预期后，再用 `tau agent-run` 真实执行。失败时主导 agent 会被唤醒修复并重跑。若工具缺失，先运行 `tau upgrade --root . --dry-run` 检查项目工具，再升级到包含当前连续工作运行层的 TauLoop 版本。不要用别的命令拼凑替代路径。

**Codex 又开始问很多小问题**

通常说明目标、边界或完成标准没有写清，或者碰到了必须人工决定的关口。让它先显示当前 plan/spec；把你愿意授权自行推进的范围与必须停下的事项写进 spec。

---

## 名词与命令速查

### 最少需要知道的名词

| 名词 | 一句话解释 |
| --- | --- |
| 目标 | 你真正想得到的项目结果。 |
| task / spec | 将目标拆开的可检查工作单元；spec 写清范围、完成标准与验证。 |
| verification | 对成果运行的可复查证据，不是 Codex 的主观判断。 |
| checkpoint | 一段工作结束时留下的当前事实和下一步。 |
| memory | 之后仍值得记住的项目事实，不是聊天全文。 |
| handoff | 给新上下文的有界交接包，只带它继续所需的事实。 |
| run contract | 长任务的可审阅执行计划：命令、权限、期限、阶段与 verifier。 |
| verifier | 在阶段命令结束后判断它是否真的达标的命令。 |
| continuous-work | TauLoop 对有边界串行本地命令的监督能力。 |
| agent-led continuous-work | 当前主路径：有记忆的 agent 会话（resume 续接）主导长任务，完成或失败才唤醒，失败由主导 agent 修复后重跑。入口 `tau agent-run`。 |

### 常用命令

```bash
# 项目生命周期
tau init --root .
tau adopt --root .
tau upgrade --root . --dry-run
tau uninstall --root .

# 项目状态
tau state init --root .
tau status --root .
tau state next --root .
tau state recover --root .
tau doctor --root .

# 运行一份连续工作合同
tau run --root . path/to/contract.json
tau run-status --root . <run-id>
tau cancel --root . <run-id>
tau recover --root . <run-id>

# 在检查点交给新上下文
tau handoff create --root . ...
tau handoff launch --root . <handoff-id>
tau handoff review --root . <handoff-id>

# agent 主导的连续工作（当前主路径）
tau agent-run --dry-run          # 本机自动闭环（不真实调用 agent）
tau agent-run                    # 真实 resume 主导 agent 循环
```

### 继续阅读

- [第一次使用](first-use.md)
- [安全策略](../../SECURITY.md)
- [贡献指南](../../CONTRIBUTING.md)

手册读到这里已经足够开始。下一次只要告诉 Codex 目标、边界，以及「能自己验证的就继续；真正需要我决定时再停下来」。
