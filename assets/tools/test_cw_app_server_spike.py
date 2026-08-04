#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("cw_app_server_spike.py")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cw-app-server-spike-test-") as temp_dir:
        root = Path(temp_dir)
        fake_server = root / "fake-codex"
        fake_server.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            "for line in sys.stdin:\n"
            "  message=json.loads(line)\n"
            "  if message.get('method') == 'initialize': print(json.dumps({'id': message['id'], 'result': {'userAgent': 'fake'}}), flush=True)\n"
            "  elif message.get('method') == 'thread/start':\n"
            "    print(json.dumps({'method': 'thread/started', 'params': {'thread': {'id': 'thr_fake'}}}), flush=True)\n"
            "    print(json.dumps({'id': message['id'], 'result': {'thread': {'id': 'thr_fake'}}}), flush=True)\n"
            "  elif message.get('method') == 'thread/read': print(json.dumps({'id': message['id'], 'result': {'thread': {'id': 'thr_fake'}}}), flush=True)\n",
            encoding="utf-8",
        )
        fake_server.chmod(0o755)
        output = root / "result.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--server-bin", str(fake_server), "--cwd", str(root), "--output", str(output)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"spike probe failed: {result.stdout}\n{result.stderr}")
        payload = json.loads(output.read_text(encoding="utf-8"))
        if payload["protocol"]["thread_id"] != "thr_fake" or payload["adapter_decision"] != "rejected_pending_observed_desktop_mapping":
            raise AssertionError(f"unexpected probe result: {payload}")
    print("cw app-server spike fixture passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
