# Migrating from `.codex/` to `.harness/`

[简体中文](#从-codex-迁移到-harness) | **English**

TauLoop 0.4+ uses `.harness/` as the harness directory (agent-agnostic, not bound
to Codex). Repos initialized with older versions have a `.codex/` directory and
a `.codex-workflow` marker. Migrate them once with the commands below.

> Requirements: the repo has no uncommitted changes you care about losing. Run
> `git status` first, commit or stash before migrating.

## English

### 1. Rename the directory and marker

```bash
cd <repo>
git mv .codex .harness 2>/dev/null || mv .codex .harness
git mv .codex-workflow .harness-workflow 2>/dev/null || mv .codex-workflow .harness-workflow
```

### 2. Fix the marker contents

```bash
sed -i '' 's|state_dir=\.codex|state_dir=.harness|' .harness-workflow   # macOS
sed -i 's|state_dir=\.codex|state_dir=.harness|' .harness-workflow     # Linux
```

### 3. Rewrite path references

Replace `` `.codex/` `` with `` `.harness/` `` in tracked docs and scripts:

```bash
grep -rl '\.codex/' --exclude-dir=.git --include='*.md' --include='*.py' --include='*.sh' --include='*.yml' . \
  | xargs sed -i '' 's|\.codex/|.harness/|g'   # macOS
# or on Linux:  | xargs sed -i 's|\.codex/|.harness/|g'
```

Keep `~/.codex/bin` and `~/.codex/skills` references untouched — those are the
user-level install paths, not the repo harness directory.

### 4. Move the managed-file manifest (if present)

```bash
git mv .codex/.tau-loop-managed.json .harness/.tau-loop-managed.json 2>/dev/null || true
```

### 5. Verify

```bash
tau init --root .          # refresh: creates missing files, updates unmodified managed tools
bash .harness/hooks/verify.sh .
```

---

## 从 `.codex/` 迁移到 `.harness/`

TauLoop 0.4+ 使用 `.harness/` 作为 harness 目录（多 agent 通用，不绑定 Codex）。
用旧版本初始化的仓库会有 `.codex/` 目录和 `.codex-workflow` 标记，按下面步骤迁移一次。

> 前提：仓库没有你关心丢失的未提交改动。先 `git status` 确认，提交或 stash 后再迁移。

### 1. 重命名目录与标记

```bash
cd <repo>
git mv .codex .harness 2>/dev/null || mv .codex .harness
git mv .codex-workflow .harness-workflow 2>/dev/null || mv .codex-workflow .harness-workflow
```

### 2. 修正标记内容

```bash
sed -i '' 's|state_dir=\.codex|state_dir=.harness|' .harness-workflow   # macOS
sed -i 's|state_dir=\.codex|state_dir=.harness|' .harness-workflow     # Linux
```

### 3. 重写路径引用

把已跟踪文档和脚本里的 `` `.codex/` `` 替换为 `` `.harness/` ``：

```bash
grep -rl '\.codex/' --exclude-dir=.git --include='*.md' --include='*.py' --include='*.sh' --include='*.yml' . \
  | xargs sed -i '' 's|\.codex/|.harness/|g'   # macOS
# Linux 用：  | xargs sed -i 's|\.codex/|.harness/|g'
```

`~/.codex/bin` 和 `~/.codex/skills` 引用保持不变——那是用户级安装路径，不是仓库 harness 目录。

### 4. 移动托管文件清单（如有）

```bash
git mv .codex/.tau-loop-managed.json .harness/.tau-loop-managed.json 2>/dev/null || true
```

### 5. 验证

```bash
tau init --root .          # 刷新：创建缺失文件，更新未修改的托管工具
bash .harness/hooks/verify.sh .
```
