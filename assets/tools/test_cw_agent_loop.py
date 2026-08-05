#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


SCRIPT = Path(__file__).with_name("cw_agent_loop.py")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def git(root: Path, *args: str) -> None:
    result = subprocess.run(["git", "-C", str(root), *args], check=False, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")


def setup_repo(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True)
    git(root, "init")
    git(root, "config", "user.email", "cw@example.test")
    git(root, "config", "user.name", "CW Test")
    (root / "repair.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
    contract = root / ".codex" / "contracts" / "download.json"
    write_json(
        contract,
        {
            "schema_version": "cw-run-contract/v2",
            "id": "download-contract",
            "limits": {"max_run_seconds": 30, "health_interval_seconds": 0.05, "terminate_grace_seconds": 0.2},
            "permissions": {"network": "required", "credentials": "none", "path_roots": ["."]},
            "agent_loop": {
                "mode": "assisted",
                "repair_on": ["command_failed"],
                "max_repair_turns": 1,
                "max_total_agent_seconds": 20,
                "allowed_files": ["repair.py", ".codex/contracts/download-r2.json"],
                "allowed_contract_roots": [".codex/contracts"],
                "candidate_checks": [{"id": "repair-syntax", "argv": [sys.executable, "-m", "py_compile", "repair.py"], "cwd": "."}],
                "repair_execution_policy": "same_argv_only",
                "require_clean_git": True,
                "require_final_review": False,
            },
            "stages": [
                {
                    "id": "download",
                    "argv": [sys.executable, "repair.py"],
                    "cwd": ".",
                    "verifier": {"argv": [sys.executable, "-c", "from pathlib import Path; assert Path('payload.txt').read_text() == 'done'"], "cwd": "."},
                }
            ],
        },
    )
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    fake = root / "fake-codex"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os\n"
        "from pathlib import Path\n"
        "case=json.loads(Path(os.environ['CW_AGENT_LOOP_CASE']).read_text())\n"
        "root=Path.cwd()\n"
        "mode=os.environ.get('CW_FAKE_MODE','repair')\n"
        "if mode == 'worker-fail': raise SystemExit(7)\n"
        "if mode == 'invalid':\n"
        "    Path(os.environ['CW_AGENT_LOOP_DECISION']).write_text('not json')\n"
        "    raise SystemExit(0)\n"
        "changed=['.codex/contracts/download-r2.json']\n"
        "if mode == 'repair':\n"
        "    (root/'repair.py').write_text(\"from pathlib import Path; Path('payload.txt').write_text('done')\\n\")\n"
        "    changed.insert(0, 'repair.py')\n"
        "elif mode == 'outside':\n"
        "    (root/'repair.py').write_text(\"from pathlib import Path; Path('payload.txt').write_text('done')\\n\")\n"
        "    (root/'outside.txt').write_text('not allowed')\n"
        "    changed.insert(0, 'repair.py')\n"
        "contract=json.loads((root/'.codex/contracts/download.json').read_text())\n"
        "Path(os.environ['CW_AGENT_LOOP_STAGED_CONTRACT']).write_text(json.dumps(contract, indent=2)+'\\n')\n"
        "decision={'schema_version':'cw-repair-decision/v1','case_id':case['id'],'decision':'propose_repair','failure_fingerprint':case['failure_fingerprint'],'replacement_contract':'.codex/contracts/download-r2.json','staged_replacement_contract_path':f\"cw-agent-output/{case['id']}/replacement-contract.json\",'changed_files':changed,'candidate_check_ids':['repair-syntax']}\n"
        "Path(os.environ['CW_AGENT_LOOP_DECISION']).write_text(json.dumps(decision)+'\\n')\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    git(root, "add", "fake-codex")
    git(root, "commit", "-m", "fake worker")
    return contract, fake


def run_loop(root: Path, contract: Path, fake: Path, loop_id: str, mode: str = "repair") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "loop", "--root", str(root), "--loop-id", loop_id, "--codex-bin", str(fake), str(contract.relative_to(root))],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "CW_FAKE_MODE": mode},
    )


def scenario_repair_continues_to_verified_completion(root: Path) -> None:
    contract, fake = setup_repo(root)
    result = run_loop(root, contract, fake, "repair-loop")
    if result.returncode != 0:
        raise AssertionError(f"repair loop failed: {result.stdout}\n{result.stderr}")
    loop = json.loads((root / ".codex" / "agent-loops" / "repair-loop" / "loop.json").read_text())
    if loop["status"] != "completed" or loop["repair_turns"] != 1 or len(loop["run_ids"]) != 2:
        raise AssertionError(f"unexpected completed loop: {loop}")
    if (root / "payload.txt").read_text() != "done" or not (root / ".codex" / "contracts" / "download-r2.json").is_file():
        raise AssertionError("accepted repair did not produce replacement output")
    events = (root / ".codex" / "agent-loops" / "repair-loop" / "events.jsonl").read_text()
    if '"event": "repair_accepted"' not in events or '"event": "replacement_run_started"' not in events:
        raise AssertionError(f"missing repair lifecycle evidence: {events}")
    worker = json.loads((root / ".codex" / "agent-loops" / "repair-loop" / "workers" / "repair-001.json").read_text())
    if worker["argv"][2:6] != ["--sandbox", "workspace-write", "--add-dir", worker["worktree"]]:
        raise AssertionError(f"repair worker must have isolated write access: {worker['argv']}")
    worker_case = json.loads((Path(worker["worktree"]) / ".codex" / "agent-loop-cases" / "repair-001.json").read_text())
    if worker_case["evidence"]["run_snapshot"] != ".codex/agent-loop-evidence/repair-001/run.json" or worker_case["decision_requirements"]["schema_version"] != "cw-repair-decision/v1" or worker_case["decision_requirements"]["write_path"] != "cw-agent-output/repair-001/decision.json":
        raise AssertionError(f"worker was not given materialized evidence and decision requirements: {worker_case}")
    if "not the Codex patch tool" not in worker["argv"][-1]:
        raise AssertionError(f"worker prompt does not prevent linked-worktree patch rejection: {worker['argv']}")


def scenario_out_of_scope_candidate_stops_at_human_gate(root: Path) -> None:
    contract, fake = setup_repo(root)
    result = run_loop(root, contract, fake, "outside-loop", "outside")
    loop = json.loads((root / ".codex" / "agent-loops" / "outside-loop" / "loop.json").read_text())
    if result.returncode == 0 or loop["status"] != "waiting_human" or not loop["terminal_reason"].startswith("repair_rejected:"):
        raise AssertionError(f"out-of-scope candidate advanced: {result.stdout}\n{result.stderr}\n{loop}")
    if (root / "outside.txt").exists() or (root / "payload.txt").exists():
        raise AssertionError("rejected worktree candidate changed the active worktree")


def scenario_repeated_fingerprint_stops_at_human_gate(root: Path) -> None:
    contract, fake = setup_repo(root)
    result = run_loop(root, contract, fake, "repeat-loop", "nochange")
    loop = json.loads((root / ".codex" / "agent-loops" / "repeat-loop" / "loop.json").read_text())
    if result.returncode == 0 or loop["status"] != "waiting_human" or loop["terminal_reason"] != "repeated_failure_fingerprint":
        raise AssertionError(f"repeated fingerprint retried indefinitely: {result.stdout}\n{result.stderr}\n{loop}")


def scenario_worker_failure_and_invalid_decision_stop(root: Path) -> None:
    contract, fake = setup_repo(root / "worker")
    failed = run_loop(root / "worker", contract, fake, "worker-loop", "worker-fail")
    failed_loop = json.loads((root / "worker" / ".codex" / "agent-loops" / "worker-loop" / "loop.json").read_text())
    if failed.returncode == 0 or failed_loop["status"] != "waiting_human" or failed_loop["terminal_reason"] != "worker_failed":
        raise AssertionError(f"failed worker advanced loop: {failed.stdout}\n{failed.stderr}\n{failed_loop}")
    contract, fake = setup_repo(root / "invalid")
    invalid = run_loop(root / "invalid", contract, fake, "invalid-loop", "invalid")
    invalid_loop = json.loads((root / "invalid" / ".codex" / "agent-loops" / "invalid-loop" / "loop.json").read_text())
    if invalid.returncode == 0 or invalid_loop["status"] != "waiting_human" or not invalid_loop["terminal_reason"].startswith("repair_rejected:"):
        raise AssertionError(f"invalid decision advanced loop: {invalid.stdout}\n{invalid.stderr}\n{invalid_loop}")


def scenario_recovery_never_claims_missing_controller(root: Path) -> None:
    loop_dir = root / ".codex" / "agent-loops" / "missing-loop"
    loop_dir.mkdir(parents=True)
    write_json(loop_dir / "loop.json", {"schema_version": "cw-agent-loop/v1", "id": "missing-loop", "status": "running", "process": {"pid": 999999, "identity": {"kind": "ps_lstart", "value": "missing"}}})
    (loop_dir / "events.jsonl").write_text("", encoding="utf-8")
    result = subprocess.run([sys.executable, str(SCRIPT), "loop-recover", "--root", str(root), "missing-loop"], check=False, capture_output=True, text=True)
    loop = json.loads((loop_dir / "loop.json").read_text())
    if result.returncode == 0 or loop["status"] != "unknown_recovery_needed":
        raise AssertionError(f"recovery trusted missing controller: {result.stdout}\n{result.stderr}\n{loop}")


def scenario_cancel_stops_managed_stage(root: Path) -> None:
    contract, fake = setup_repo(root)
    (root / "repair.py").write_text("import time; time.sleep(5)\n", encoding="utf-8")
    git(root, "add", "repair.py")
    git(root, "commit", "-m", "long stage")
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), "loop", "--root", str(root), "--loop-id", "cancel-loop", "--codex-bin", str(fake), str(contract.relative_to(root))],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    run_path = root / ".codex" / "runs" / "cancel-loop-run-1" / "run.json"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if run_path.exists() and json.loads(run_path.read_text())["status"] == "running":
            break
        time.sleep(0.02)
    else:
        process.kill()
        raise AssertionError("loop never started its managed stage")
    cancel = subprocess.run([sys.executable, str(SCRIPT), "loop-cancel", "--root", str(root), "cancel-loop"], check=False, capture_output=True, text=True)
    stdout, stderr = process.communicate(timeout=10)
    loop = json.loads((root / ".codex" / "agent-loops" / "cancel-loop" / "loop.json").read_text())
    if cancel.returncode != 0 or process.returncode == 0 or loop["status"] != "cancelled":
        raise AssertionError(f"loop cancellation did not converge: {cancel.stdout}\n{cancel.stderr}\n{stdout}\n{stderr}\n{loop}")


def scenario_real_codex_smoke(codex_bin: str) -> int:
    if not shutil.which(codex_bin):
        raise AssertionError(f"real Codex binary not found: {codex_bin}")
    root = Path(tempfile.mkdtemp(prefix="cw-real-codex-")) / "repo"
    contract, _ = setup_repo(root)
    value = json.loads(contract.read_text(encoding="utf-8"))
    value["agent_loop"]["max_total_agent_seconds"] = 300
    write_json(contract, value)
    git(root, "add", ".codex/contracts/download.json")
    git(root, "commit", "-m", "real worker smoke budget")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "loop", "--root", str(root), "--loop-id", "real-codex-smoke", "--codex-bin", codex_bin, str(contract.relative_to(root))],
        check=False,
        capture_output=True,
        text=True,
        timeout=330,
    )
    loop = json.loads((root / ".codex" / "agent-loops" / "real-codex-smoke" / "loop.json").read_text(encoding="utf-8"))
    print(f"real Codex smoke evidence retained at: {root}")
    if result.returncode != 0 or loop["status"] != "completed" or len(loop["run_ids"]) != 2:
        raise AssertionError(f"real Codex worker did not complete: {result.stdout}\n{result.stderr}\n{loop}")
    print("real Codex agent loop smoke passed")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--real-codex-smoke":
        return scenario_real_codex_smoke(sys.argv[2] if len(sys.argv) > 2 else "codex")
    with tempfile.TemporaryDirectory(prefix="cw-agent-loop-test-") as temp_dir:
        root = Path(temp_dir)
        scenario_repair_continues_to_verified_completion(root / "repair")
        scenario_out_of_scope_candidate_stops_at_human_gate(root / "outside")
        scenario_repeated_fingerprint_stops_at_human_gate(root / "repeat")
        scenario_worker_failure_and_invalid_decision_stop(root / "worker-invalid")
        scenario_recovery_never_claims_missing_controller(root / "recovery")
        scenario_cancel_stops_managed_stage(root / "cancel")
    print("cw agent loop fixtures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
