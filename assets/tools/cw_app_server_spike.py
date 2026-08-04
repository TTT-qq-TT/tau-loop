#!/usr/bin/env python3
"""Bounded Phase D probe for the public Codex app-server thread protocol."""

from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


class ProbeError(RuntimeError):
    pass


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def collect_lines(handle: Any, lines: queue.Queue[str | None]) -> None:
    for line in handle:
        lines.put(line)
    lines.put(None)


def receive_response(lines: queue.Queue[str | None], request_id: int, timeout_seconds: float) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    while True:
        try:
            line = lines.get(timeout=timeout_seconds)
        except queue.Empty as exc:
            raise ProbeError(f"app-server request {request_id} timed out") from exc
        if line is None:
            raise ProbeError("app-server closed stdout before responding")
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProbeError(f"app-server emitted invalid JSON: {line!r}") from exc
        messages.append(message)
        if message.get("id") == request_id:
            if "error" in message:
                raise ProbeError(f"app-server request {request_id} failed: {message['error']}")
            return messages
def send(process: subprocess.Popen[str], payload: dict[str, Any]) -> None:
    if process.stdin is None:
        raise ProbeError("app-server stdin is unavailable")
    process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    process.stdin.flush()


def probe(server_bin: str, cwd: Path, timeout_seconds: float) -> dict[str, Any]:
    command = [server_bin, "app-server", "--stdio"]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.stdout is None:
        raise ProbeError("app-server stdout is unavailable")
    lines: queue.Queue[str | None] = queue.Queue()
    threading.Thread(target=collect_lines, args=(process.stdout, lines), daemon=True).start()
    try:
        send(
            process,
            {
                "method": "initialize",
                "id": 1,
                "params": {"clientInfo": {"name": "cw_v2_phase_d_spike", "title": "continuous-work v2 Phase D spike", "version": "1"}},
            },
        )
        initialize_messages = receive_response(lines, 1, timeout_seconds)
        send(process, {"method": "initialized", "params": {}})
        send(process, {"method": "thread/start", "id": 2, "params": {"cwd": str(cwd.resolve()), "ephemeral": False, "serviceName": "cw_v2_phase_d_spike"}})
        start_messages = receive_response(lines, 2, timeout_seconds)
        response = next(message for message in start_messages if message.get("id") == 2)
        thread = response.get("result", {}).get("thread", {})
        thread_id = thread.get("id")
        if not isinstance(thread_id, str) or not thread_id:
            raise ProbeError("thread/start returned no thread id")
        send(process, {"method": "thread/read", "id": 3, "params": {"threadId": thread_id, "includeTurns": False}})
        read_messages = receive_response(lines, 3, timeout_seconds)
        return {
            "schema_version": "cw-app-server-spike/v1",
            "protocol": {"initialized": True, "thread_started": True, "thread_read": True, "thread_id": thread_id},
            "events_observed": [message.get("method") for message in start_messages + read_messages if message.get("method")],
            "desktop_visibility": "not_provable_from_public_app_server_protocol",
            "adapter_decision": "rejected_pending_observed_desktop_mapping",
            "command": command,
            "initialize_message_count": len(initialize_messages),
        }
    finally:
        if process.stdin is not None:
            process.stdin.close()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe app-server thread creation without claiming Desktop visibility")
    parser.add_argument("--server-bin", default="codex")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--timeout-seconds", type=float, default=10)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout_seconds <= 0:
        raise SystemExit("timeout-seconds must be positive")
    try:
        result = probe(args.server_bin, Path(args.cwd), args.timeout_seconds)
    except (OSError, ProbeError) as exc:
        print(f"cw app-server spike: {exc}", file=sys.stderr)
        return 1
    write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
