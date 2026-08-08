<h1 align="center">
  <img src="docs/images/tauloop-mark.png" alt="" width="48" height="48" valign="middle"> <strong>τ-Loop</strong>
</h1>

<p align="center">
  <strong>TauLoop</strong> · τ = 2π：一整圈，不是一段无限长的对话。
</p>

<p align="center">
  你说目标，agent 拆任务、做验证、留下下一步。
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4C430?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9 or later">
  <img src="https://img.shields.io/badge/agents-Codex%20%C2%B7%20Claude%20%C2%B7%20CodeWhale-10A37F?style=flat-square" alt="适用于 Codex、Claude 与 CodeWhale 的 agent skill">
  <img src="https://img.shields.io/badge/macOS%20%C2%B7%20Ubuntu%20%C2%B7%20Windows-supported-4C8BF5?style=flat-square" alt="macOS, Ubuntu 与 Windows 受支持">
</p>

<p align="center">
  <a href="README.md#english">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <a href="#从一句话开始">从一句话开始</a> · <a href="#怎么用">怎么用</a> · <a href="#它凭什么让你放心">凭什么放心</a> · <a href="#两件它特别适合做的事">两个场景</a> · <a href="#它不会做什么">边界</a> · <a href="#手动安装">手动安装</a>
</p>

<p align="center">
  <img src="docs/images/tauloop-readme-cover.png" alt="TauLoop：一整圈，继续向前" width="960">
</p>

---

>你睡前把一个目标交给 agent。第二天，它停在最早的一步，等你决定本不该由你决定的事。
>TauLoop 把计划、验证的结果和下一步留在项目里，让工作不被一段聊天困住。

### 如果这是你的痛点：
  - 刚接触 agent，不知道 workflow 怎么上手？
  - harness engineering，loop engineering，这些名词太眼花缭乱，却不知道该怎么用
  - 见过不少 workflow skill，却觉得它们都太「重」？

我想，你可以先试试 TauLoop -— 够轻、够用，减去一切你用不上的东西，只做痛点。

---

## 从一句话开始

> [!TIP]
> **第一次使用？** 不需要先学习命令、文件结构或 agent workflow。把下面这段话连同仓库链接发给 agent，然后把 `xxx` 换成你的目标。

```text
请阅读并安装 https://github.com/TTT-qq-TT/tau-loop ，然后用 TauLoop 把当前项目推进到 xxx。

能自己验证的就继续；真正需要我决定时再停下来。
```

agent 会安装 TauLoop，并在项目里准备它需要的工作记录。你不必记住命令，也不必先理解 `spec`、`checkpoint` 或 `harness`。

如果你希望先看方案，在最后补一句：

```text
先只给我看计划和每一段的完成标准，等我确认后再开始。
```

---

## 怎么用

TauLoop 的用法只有一句话：**说清目标，然后让它把目标拆成一段段可检查的工作。**

```text
你说目标
  -> agent 写 spec（这一段改哪里、怎样算完成、怎么验证）
  -> 按 spec 执行，用证据收尾，而不是一句「做好了」
  -> 留下 checkpoint，进入下一段
  -> 长任务由操作系统托管，agent 定期检查，不占聊天窗口
```

只需要记住四个词：

- **spec**：一段工作的契约——改哪里、怎样算完成、怎么验证。范围变了就先改 spec。
- **checkpoint**：一段工作结束时的现场——刚做了什么、证据在哪、下一步是什么。
- **memory**：项目还值得记住的事实——不是聊天全文，是下一位 agent 需要知道的结论。
- **长任务**：下载、构建、训练这类慢活，由操作系统托管进程，agent 定期醒来检查，不紧盯着轮询。

### TauLoop 的「一圈」

`目标 -> 可检查的一步 -> 实现 -> 验证 -> checkpoint -> 下一步或你的决定`

它不是让 agent 无限循环；它让一次工作能留下证据地走完一圈。

---

## 它凭什么让你放心

**极简。** 一条命令 `tau init`，之后没有 daemon、没有状态机、没有要记的命令面。规则写在项目的 `AGENTS.md` 里，剩下的全是约定。

**文件即真相。** 计划、验证结果、下一步都存在项目文件里（`.harness/`），不依赖任何一段聊天。换窗口、换 agent、隔天再来，读到的都是同一份事实。

**机械兜底。** 一层极薄的 hooks/check 脚本在任务开始前和完成前自动核对：spec 写全了吗？验证记录了吗？「进程还活着」不等于「任务完成」——成功必须来自实际完成并通过验证的证据。

---

## 三件它特别适合做的事

### 1. 把一个项目推进到 xxx

你不需要先把所有小任务想清楚。只要说出要达到的结果，以及哪些地方必须由你决定。TauLoop 会让 agent 先列出路径和每段工作的完成标准；通过验证后留下 checkpoint，再接着推进下一段。

```text
用 TauLoop 持续推进这个 repo，直到 xxx 完成。
自己拆分任务、逐项验证；需要我决定时再停下来。
```

第二天回来时，你看到的应当是一份可检查的进展，而不是一串需要重新读懂的聊天记录。

### 2. 让一条长命令安静地跑完

下载依赖、配置环境、编译或测试时，真正需要等待的是本地命令，不是 agent 的聊天窗口。对于步骤明确、能够验证的串行工作，TauLoop 让 agent 写清执行计划，监督真实进程，并在上一步验证通过后才进入下一步。

```text
用 TauLoop 帮我配置 xxx 环境。
把下载、安装和检查拆成串行步骤；前一步验证通过才开始下一步；不要频繁查看下载进度；全部完成后停在检查点。
```

### 3. 窗口快满时，换窗继续

上下文窗口快满，或想把"讨论"和"执行"分开时，直接说：

```text
请 handoff 给下一个窗口。
```

agent 会整理好交接物（意图、进度、证据、已定决策），给你一句启动语；你开新窗口粘贴即可无缝继续，不用重新解释。

---

## 它不会做什么

> [!IMPORTANT]
> **先验证，再继续。** TauLoop 的目标是让工作可检查地结束，不是让 agent 无边界地一直跑下去。

- 不会在电脑重启或终端关闭后神奇地继续运行。
- 不会因为smoke通过，就过度声称你的 CUDA、GPU 或仿真器已经可用。
- 不会替你决定权限、费用、不可逆修改，或验证失败后的下一步。

---

## 手动安装

上面的自然语言方式是推荐路径。只有当 agent 请你手动安装时，才需要下面三行：

```bash
git clone https://github.com/TTT-qq-TT/tau-loop.git
cd tau-loop
python3 install.py
```

安装后，agent 会发现 TauLoop skill。若你的环境没有把 `~/.codex/bin` 加入 `PATH`，按 agent 的提示处理即可。
`~/.codex` 是 Codex 环境的默认位置。其他 agent 环境可用 `python3 install.py --codex-home <目录>` 指定安装位置，并用 `TAU_LOOP_CODEX_HOME` 环境变量让 `tau` 从同一位置读取。

## 更多内容

- [第一次使用](assets/docs/first-use.md)
- [完整使用手册](assets/docs/user-manual.md)
- [安全策略](SECURITY.md)
- [贡献指南](CONTRIBUTING.md)

使用 [MIT License](LICENSE)。
