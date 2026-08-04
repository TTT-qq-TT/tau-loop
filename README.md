<h1 align="center"><strong>τ-Loop</strong></h1>

<p align="center">
  <strong>TauLoop</strong> · τ = 2π ：一整圈，不是一段无限长的对话。
</p>

<p align="center">
  你说目标，Codex 拆任务、做验证、留下进度。
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4C430?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.8 or later">
  <img src="https://img.shields.io/badge/Codex-Skill-10A37F?style=flat-square" alt="Codex Skill">
  <img src="https://img.shields.io/badge/macOS%20%2B%20Ubuntu-supported-4C8BF5?style=flat-square" alt="macOS and Ubuntu supported">
</p>

<p align="center">
  <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="#它替你守住什么">它替你守住什么</a> · <a href="#让-codex-开始工作">让 Codex 开始工作</a> · <a href="#常用说法">常用说法</a> · <a href="#几个够用的词">几个够用的词</a> · <a href="#手动安装">手动安装</a>
</p>

---

> 做长任务时 agent 总是做不好？想学习却被被 harness 工程、loop 工程这些名词搞的眼花缭乱？试试 TauLoop ！

## 它替你守住什么

把一件事交给 Codex，不该意味着一觉醒来才发现它早就停在半路。TauLoop 把需要等待的工作、项目的记忆和下一步要做什么，留在项目里，而不是留在一段会越聊越长的对话里。

### 让长任务安静地等完

对于有明确命令和完成检查的下载、安装、编译或测试，continuous-work v2 会监督真实的本地进程，低频记录健康证据，并且只在上一步验证通过后进入下一步。你不需要让 Codex 每隔几分钟回来读一次日志。

### 让新上下文接得上旧工作

每完成一段工作，TauLoop 写入 checkpoint：做了什么、证据在哪里、下一步是什么。需要换会话或换一个干净上下文时，Codex 接到的是这些事实，不是一整段旧聊天记录。

### 让项目自己记住进度

项目根目录的 `AGENTS.md` 告诉 Codex 从哪里开始；`.codex/plan.md` 记录现在在推进什么；`.codex/memory.md` 留下仍然重要的事实。它们组成一份放在项目里的共享记忆，让工作不会只存在于某一个窗口。

> [!NOTE]
> TauLoop 让受管的长步骤在本地 supervisor 仍在运行时持续等待和验证；它不是电脑重启或终端关闭后仍会自动醒来的后台服务。

---

## 让 Codex 开始工作

> [!TIP]
> **第一次使用？** 你不需要先学习命令或项目结构。先让 Codex 读完 TauLoop，再告诉它你想完成什么。

把下面这段话连同仓库链接发给 Codex。你不需要记住任何命令。

```text
请阅读并安装 https://github.com/TTT-qq-TT/tau-loop ，然后用 TauLoop 管理当前项目。

请为我简要说明 TauLoop 的用法。
```

Codex 会安装 skill，并用简单的话说明它怎么帮助你管理项目。等你给出具体目标后，它才会创建 specs、开始执行和写入 checkpoint。

<!-- Screenshot TODO: A real Codex conversation receiving the prompt above.
Suggested path: docs/images/01-tell-codex-the-goal.png -->

## 常用说法

直接把目标换进去就可以。

### 场景一：推进一个项目

```text
用 TauLoop 持续推进这个 repo，直到 xxx（你的具体目标） 完成。自己拆分任务、逐项验证；需要我决定时再停下来。
```

### 场景二：推进一组明确任务

```text
接下来的任务分为四个阶段：xxx -> xxx -> xxx -> xxx。

用 TauLoop 创建 spec1 到 spec4，并持续推进，直到它们全部完成。每份 spec 完成后都要留下 checkpoint 给我检查。
```

### 场景三：先看计划，再开始

```text
请先根据我的需求，为项目列一个完整计划，并拆分为若干 spec。

先只给我看计划和每份 spec 的完成标准，等我确认后再开始执行。
```

### 场景四：配置一个长环境

```text
用 TauLoop 帮我配置 xxx 仿真环境。
把下载、安装和检查拆成串行步骤；前一步验证通过才开始下一步；不要频繁查看下载进度；全部完成后停在检查点。
```

<!-- Screenshot TODO: A real terminal or Codex view showing one supervised stage and concise health evidence.
Suggested path: docs/images/02-a-long-task-is-running.png -->

---

## 几个够用的词

你不用学习一套新系统，只需要认识下面几个词。

| 词 | 它是什么意思 | 你怎么对 Codex 说 |
| --- | --- | --- |
| Harness | 项目里的共享笔记本。它保存计划、证据和问题，不靠一段越来越长的聊天。 | “用 TauLoop 管理当前项目。” |
| 任务 | 你想得到的结果，例如“推进到 xxx”。 | “把这个项目推进到 xxx。” |
| Spec | 一个小任务：做什么、别做什么、怎样算完成。 | “先为这个目标创建 specs。” |
| Checkpoint | 完成一段工作后留下的事实记录。换一个会话时，新的 Codex 可以从这里接上。 | “自动写好 checkpoint，并让新窗口的 codex 检查。” |
| 长任务 | 需要等待的串行工作，例如下载、安装、训练或测试。 | “不要轮询；验证后再继续。” |

通常不需要自己创建文件或调用命令。Codex 会在项目里完成这些事；你可以随时要求它解释当前 spec、进度或 checkpoint。

---

## 加上 Loop，会发生什么

如果我们加上 Loop engineering，会发生什么？

TauLoop 把一次工作变成一个可以结束的回合：

1. 先把目标拆成小而可检查的 specs。
2. Codex 完成当前 spec，并运行约定的验证。
3. 通过后写入 checkpoint，再进入下一份 spec，持续工作直到结束，除非——你要求它停下来。

它不是让 agent 无限循环。进程还活着、heartbeat 还在，都不等于任务已经完成。没有验证，就不会把下一步当作已解锁。

<!-- Screenshot TODO: A real checkpoint or review view after a verified task finishes.
Suggested path: docs/images/03-verified-checkpoint.png -->

---

## 长任务

遇到长下载、环境配置或一串必须按顺序执行的命令时，直接使用上面的“配置一个长环境”说法。TauLoop 会让 Codex 写出并审查执行计划，监督实际进程，低频记录健康证据，并且只在验证通过后进入下一步。

> [!NOTE]
> 你不需要知道 `run contract` 是什么。它是 Codex 用来写清命令、时限、权限和验证方法的记录。

想多看一眼时，只要说：

```text
在开始长任务前，先给我看执行计划、每一步的验证方法，以及它会在哪些地方停下来等我确认。
```

## 它不会做什么

> [!IMPORTANT]
> **先验证，再继续。** TauLoop 的目标是让工作可检查地结束，不是让 agent 一直跑下去。

- 不会在电脑重启或终端关闭后神奇地继续运行。
- 不会把 heartbeat 当作成功证明。
- 不会因为测试样例通过，就声称你的 CUDA、GPU 或仿真器已经可用。
- 不会替你决定权限、费用、不可逆修改，或验证失败后的下一步。

---

## 手动安装

上面的自然语言方式是推荐路径。只有当 Codex 请你手动安装时，才需要下面三行：

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

安装后，Codex 会发现 TauLoop skill。若你的环境没有把 `~/.codex/bin` 加入 `PATH`，按 Codex 的提示处理即可。

## 更多内容

- [项目工作流与升级方式](assets/docs/project-workflow.md)
- [给 Codex 的第一次介绍](assets/docs/first-use.md)
- [长任务的完整操作说明](assets/docs/continuous-work-v2.md)
- [旧版控制面参考](assets/docs/continuous-work-v1.md)
- [安全策略](SECURITY.md)
- [贡献指南](CONTRIBUTING.md)

使用 [MIT License](LICENSE)。
