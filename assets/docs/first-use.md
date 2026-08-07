# TauLoop 初次使用指南

[English](first-use.en.md) | **简体中文**

> 把目标交给 agent，剩下的记录与验证交给 TauLoop。

## 开始

把下面这句话发给 agent，`xxx` 换成你真正想要的结果：

```text
请阅读并安装 https://github.com/TTT-qq-TT/tau-loop ，然后用 TauLoop 把当前项目推进到 xxx。

能自己验证的就继续；真正需要我决定时再停下来。
```

agent 会：

1. 下载并安装 TauLoop（skill + `tau` 命令）；
2. 在项目里执行 `tau init`，创建 `AGENTS.md` 和 `.harness/` 骨架；
3. 把你的目标拆成可检查的小任务（spec），逐个完成并记录验证。

你不必先记住命令，也不必先理解 `spec`、`checkpoint` 或 `harness` 分别是什么。

如果你只想先看方案，补一句：

```text
先只给我看计划和每一段的完成标准，等我确认后再开始。
```

## 手动安装（只有排错时需要）

需要 Python 3.9+。

```bash
git clone --depth 1 https://github.com/TTT-qq-TT/tau-loop /tmp/tau-loop-install
python3 /tmp/tau-loop-install/install.py
```

## 之后

- 日常推进：告诉 agent 你想把项目推进到哪里，以及"能自己验证的就继续；真正需要我决定时再停下来"。
- 长命令：agent 会用 `nohup`/`screen` 把进程交给操作系统，自己定期醒来检查——不会一直占用对话。
- 存量项目：还在用 `.codex/` 的仓库，先看[迁移指南](migration-from-codex.md)。
- 想深入了解：读[完整使用手册](user-manual.md)。
