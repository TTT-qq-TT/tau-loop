# 环境配置运行合同模板

这是给操作者确认的合同模板，不是一份可以原样执行的命令。确认目标仓库、操作系统、Python、CUDA、包索引、仿真器和 GPU 验收标准后，必须替换全部尖括号中的值。

## 目标事实

- Consumer repo：`<绝对路径或 repo-local 身份>`
- 目标平台：`<macOS 或 Ubuntu 版本>`
- Python 可执行文件与版本：`<例如：.venv/bin/python, 3.11.x>`
- PyTorch 版本与 index URL：`<精确版本和已批准索引>`
- CUDA 预期：`<仅 CPU、CUDA 版本，或不适用>`
- 仿真器包与版本：`<精确包名或安装命令>`
- 最终 GPU verifier：`<精确命令和预期可见设备数>`
- 已批准的网络与凭据来源：`<无、公共索引，或批准的继承环境变量>`
- 最终人工审查人：`<姓名或角色>`

## 推进等级

- L1：操作者手动执行每个已批准阶段，并记录 verifier 输出。
- L2：agent 创建这份 contract；操作者启动 `tau run` 并审查异常 handoff。
- L3：只有同一目标形态已成功留下 L1、L2 证据时才允许。必须设置下方全部限额，并停在最终审查处。

## 必需的串行合同

将补全后的 JSON 保存到目标 repo 内，例如 `.codex/contracts/environment-bootstrap.json`。

```json
{
  "schema_version": "cw-run-contract/v1",
  "id": "environment-bootstrap-<target>",
  "limits": {
    "max_run_seconds": 14400,
    "health_interval_seconds": 300,
    "terminate_grace_seconds": 30,
    "max_stage_attempts": 1,
    "max_handoffs": 2
  },
  "permissions": {
    "network": "required",
    "credentials": "none",
    "path_roots": ["."]
  },
  "stages": [
    {
      "id": "python_preflight",
      "argv": ["<python>", "-c", "import sys; assert sys.version_info[:2] == (<major>, <minor>)"],
      "cwd": ".",
      "verifier": {
        "argv": ["<python>", "--version"],
        "cwd": "."
      },
      "deadline_seconds": 300
    },
    {
      "id": "pytorch_install",
      "argv": ["<python>", "-m", "pip", "install", "torch==<version>", "--index-url", "<approved-index-url>"],
      "cwd": ".",
      "verifier": {
        "argv": ["<python>", "-c", "import torch; print(torch.__version__); print(torch.cuda.is_available())"],
        "cwd": "."
      },
      "deadline_seconds": 7200
    },
    {
      "id": "simulator_install",
      "argv": ["<python>", "-m", "pip", "install", "<simulator==version>"],
      "cwd": ".",
      "verifier": {
        "argv": ["<python>", "-c", "import <simulator_module>; print(<simulator_module>.__version__)"],
        "cwd": "."
      },
      "deadline_seconds": 7200
    },
    {
      "id": "final_gpu_check",
      "argv": ["<python>", "-c", "import torch; assert torch.cuda.device_count() == <expected_device_count>"],
      "cwd": ".",
      "verifier": {
        "argv": ["<python>", "-c", "import torch; assert torch.cuda.device_count() == <expected_device_count>"],
        "cwd": "."
      },
      "deadline_seconds": 300
    }
  ]
}
```

## 必须停止的情况

- 不要把 JSON 数组改成 shell 字符串或 `sh -c` 包装。
- L3 不得设置无限 deadline、attempt 数或 handoff 数。
- verifier 失败、deadline 到期、PID 缺失、PID 身份不一致、出现未批准的凭据请求，或目标信息仍有歧义时：停止自动推进，并创建一份基于事实的 handoff 供审查。
- 最后一阶段始终停在人工最终审查。fixture 成功不等于目标 GPU 环境已经就绪。
