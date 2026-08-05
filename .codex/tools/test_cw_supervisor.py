#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


SCRIPT = Path(__file__).with_name("cw_supervisor.py")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run_supervisor(root: Path, contract: Path, run_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "run", "--root", str(root), "--run-id", run_id, str(contract.relative_to(root))],
        check=False,
        capture_output=True,
        text=True,
    )


def start_supervisor(root: Path, contract: Path, run_id: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(SCRIPT), "run", "--root", str(root), "--run-id", run_id, str(contract.relative_to(root))],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for_running_stage(root: Path, run_id: str) -> dict:
    runtime_path = root / ".codex" / "runs" / run_id / "run.json"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if runtime_path.exists():
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            if runtime["stages"][0]["status"] == "running":
                return runtime
        time.sleep(0.01)
    raise AssertionError(f"run {run_id} never reached a running first stage")


def command(source: str) -> list[str]:
    return [sys.executable, "-c", source]


def stage(stage_id: str, source: str, verifier_source: str) -> dict:
    return {"id": stage_id, "argv": command(source), "cwd": ".", "verifier": {"argv": command(verifier_source), "cwd": "."}}


def scenario_success_serial(root: Path) -> None:
    contract = root / "contracts" / "success.json"
    write_json(
        contract,
        {
            "schema_version": "cw-run-contract/v1",
            "id": "success-contract",
            "stages": [
                stage("first", "from pathlib import Path; Path('sequence.txt').write_text('A')", "from pathlib import Path; assert Path('sequence.txt').read_text() == 'A'"),
                stage("second", "from pathlib import Path; p=Path('sequence.txt'); p.write_text(p.read_text() + 'B')", "from pathlib import Path; assert Path('sequence.txt').read_text() == 'AB'"),
            ],
        },
    )
    result = run_supervisor(root, contract, "success-run")
    if result.returncode != 0:
        raise AssertionError(f"success run failed: {result.stdout}\n{result.stderr}")
    runtime = json.loads((root / ".codex" / "runs" / "success-run" / "run.json").read_text(encoding="utf-8"))
    if runtime["status"] != "completed" or [item["status"] for item in runtime["stages"]] != ["completed", "completed"]:
        raise AssertionError(f"unexpected success runtime: {runtime}")
    process = runtime["stages"][0]["process"]
    if not isinstance(process["pid"], int) or not process["identity"].get("value"):
        raise AssertionError(f"missing process identity: {process}")
    events = (root / ".codex" / "runs" / "success-run" / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if not any('"event": "stage_completed"' in line for line in events):
        raise AssertionError(f"missing stage completion evidence: {events}")
    for stage_runtime in runtime["stages"]:
        for relative_path in stage_runtime["logs"].values():
            if not (root / relative_path).is_file():
                raise AssertionError(f"missing log: {relative_path}")


def scenario_verifier_failure_stops_serial(root: Path) -> None:
    contract = root / "contracts" / "verifier-failure.json"
    write_json(
        contract,
        {
            "schema_version": "cw-run-contract/v1",
            "id": "verifier-failure-contract",
            "stages": [
                stage("first", "from pathlib import Path; Path('first-ran.txt').write_text('yes')", "raise SystemExit(9)"),
                stage("second", "from pathlib import Path; Path('second-ran.txt').write_text('must not run')", "raise SystemExit(0)"),
            ],
        },
    )
    result = run_supervisor(root, contract, "verifier-failure-run")
    if result.returncode == 0:
        raise AssertionError("verifier failure unexpectedly succeeded")
    runtime = json.loads((root / ".codex" / "runs" / "verifier-failure-run" / "run.json").read_text(encoding="utf-8"))
    statuses = [item["status"] for item in runtime["stages"]]
    if runtime["status"] != "failed" or statuses != ["failed", "planned"]:
        raise AssertionError(f"verifier failure advanced a stage: {runtime}")
    if runtime["stages"][0]["failure_reason"] != "verifier_failed" or (root / "second-ran.txt").exists():
        raise AssertionError(f"missing verifier failure boundary: {runtime}")


def scenario_contract_rejects_shell_string(root: Path) -> None:
    contract = root / "contracts" / "invalid.json"
    write_json(contract, {"schema_version": "cw-run-contract/v1", "id": "invalid", "stages": [{"id": "bad", "argv": "echo unsafe", "verifier": {"argv": command("pass")}}]})
    result = run_supervisor(root, contract, "invalid-run")
    if result.returncode != 2 or "argv must be a non-empty array" not in result.stderr:
        raise AssertionError(f"shell string contract was accepted: {result.stdout}\n{result.stderr}")


def scenario_verifier_launch_failure_stops_serial(root: Path) -> None:
    contract = root / "contracts" / "verifier-launch-failure.json"
    broken_verifier = {"argv": ["cw-command-that-does-not-exist"], "cwd": "."}
    write_json(
        contract,
        {
            "schema_version": "cw-run-contract/v1",
            "id": "verifier-launch-failure-contract",
            "stages": [
                {"id": "first", "argv": command("pass"), "cwd": ".", "verifier": broken_verifier},
                stage("second", "from pathlib import Path; Path('second-ran.txt').write_text('must not run')", "pass"),
            ],
        },
    )
    result = run_supervisor(root, contract, "verifier-launch-failure-run")
    if result.returncode == 0:
        raise AssertionError("verifier launch failure unexpectedly succeeded")
    runtime = json.loads((root / ".codex" / "runs" / "verifier-launch-failure-run" / "run.json").read_text(encoding="utf-8"))
    statuses = [item["status"] for item in runtime["stages"]]
    if runtime["status"] != "failed" or statuses != ["failed", "planned"]:
        raise AssertionError(f"verifier launch failure advanced a stage: {runtime}")
    if not runtime["stages"][0]["failure_reason"].startswith("verifier_launch_error:"):
        raise AssertionError(f"missing verifier launch failure: {runtime}")


def scenario_health_and_cancel_stop_serial(root: Path) -> None:
    contract = root / "contracts" / "cancel.json"
    write_json(
        contract,
        {
            "schema_version": "cw-run-contract/v1",
            "id": "cancel-contract",
            "limits": {"health_interval_seconds": 0.05, "terminate_grace_seconds": 0.2},
            "permissions": {"network": "none", "credentials": "none", "path_roots": ["."]},
            "stages": [
                stage("first", "import time; time.sleep(5)", "pass"),
                stage("second", "from pathlib import Path; Path('second-ran.txt').write_text('must not run')", "pass"),
            ],
        },
    )
    process = start_supervisor(root, contract, "cancel-run")
    wait_for_running_stage(root, "cancel-run")
    time.sleep(0.12)
    cancel = subprocess.run([sys.executable, str(SCRIPT), "run-cancel", "--root", str(root), "cancel-run"], check=False, capture_output=True, text=True)
    stdout, stderr = process.communicate(timeout=5)
    if cancel.returncode != 0 or process.returncode == 0:
        raise AssertionError(f"cancel did not stop supervisor: {cancel.stdout}\n{cancel.stderr}\n{stdout}\n{stderr}")
    runtime = json.loads((root / ".codex" / "runs" / "cancel-run" / "run.json").read_text(encoding="utf-8"))
    if runtime["status"] != "cancelled" or [item["status"] for item in runtime["stages"]] != ["cancelled", "planned"]:
        raise AssertionError(f"cancel advanced a stage: {runtime}")
    if runtime["stages"][0]["health"] is None or runtime["permissions"]["enforcement"] != "declarative_only":
        raise AssertionError(f"missing evidence or permission boundary: {runtime}")


def scenario_deadline_becomes_unknown(root: Path) -> None:
    contract = root / "contracts" / "deadline.json"
    first = stage("first", "import time; time.sleep(5)", "pass")
    first["deadline_seconds"] = 0.1
    write_json(
        contract,
        {
            "schema_version": "cw-run-contract/v1",
            "id": "deadline-contract",
            "limits": {"health_interval_seconds": 0.05, "terminate_grace_seconds": 0.2},
            "stages": [first, stage("second", "raise AssertionError('must not run')", "pass")],
        },
    )
    result = run_supervisor(root, contract, "deadline-run")
    runtime = json.loads((root / ".codex" / "runs" / "deadline-run" / "run.json").read_text(encoding="utf-8"))
    if result.returncode == 0 or runtime["status"] != "unknown_recovery_needed":
        raise AssertionError(f"deadline did not become unknown: {result.stdout}\n{result.stderr}\n{runtime}")
    if [item["status"] for item in runtime["stages"]] != ["unknown_recovery_needed", "planned"] or not runtime["stages"][0]["failure_fingerprint"]:
        raise AssertionError(f"deadline advanced a stage or omitted fingerprint: {runtime}")


def scenario_recovery_marks_missing_process_unknown(root: Path) -> None:
    run_dir = root / ".codex" / "runs" / "recovery-run"
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "logs" / "first.stderr.log").write_text("", encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    write_json(
        run_dir / "run.json",
        {
            "schema_version": "cw-run-runtime/v1",
            "run_id": "recovery-run",
            "status": "running",
            "stages": [
                {
                    "id": "first",
                    "status": "running",
                    "process": {"pid": 999999, "identity": {"kind": "ps_lstart", "value": "missing"}, "exit_code": None},
                    "logs": {"stdout": ".codex/runs/recovery-run/logs/first.stdout.log", "stderr": ".codex/runs/recovery-run/logs/first.stderr.log"},
                    "failure_reason": None,
                    "failure_fingerprint": None,
                },
                {"id": "second", "status": "planned", "process": None, "logs": {"stdout": ".", "stderr": "."}, "failure_reason": None, "failure_fingerprint": None},
            ],
        },
    )
    result = subprocess.run([sys.executable, str(SCRIPT), "run-recover", "--root", str(root), "recovery-run"], check=False, capture_output=True, text=True)
    runtime = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    if result.returncode == 0 or runtime["status"] != "unknown_recovery_needed" or runtime["stages"][1]["status"] != "planned":
        raise AssertionError(f"recovery advanced a missing process: {result.stdout}\n{result.stderr}\n{runtime}")


def scenario_fresh_handoff_bridge_and_review(root: Path) -> None:
    contract = root / "contracts" / "handoff.json"
    first = stage("first", "from pathlib import Path; Path('handoff-result.txt').write_text('verified')", "from pathlib import Path; assert Path('handoff-result.txt').read_text() == 'verified'")
    first["env"] = {"TOP_SECRET": "must-not-enter-handoff"}
    write_json(
        contract,
        {
            "schema_version": "cw-run-contract/v1",
            "id": "handoff-contract",
            "limits": {"max_handoffs": 1},
            "stages": [first],
        },
    )
    result = run_supervisor(root, contract, "handoff-run")
    if result.returncode != 0:
        raise AssertionError(f"handoff setup run failed: {result.stdout}\n{result.stderr}")
    spec = root / "spec.md"
    checkpoint = root / "checkpoint.md"
    spec.write_text("allowed spec\n", encoding="utf-8")
    checkpoint.write_text("verified checkpoint\n", encoding="utf-8")
    create = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "handoff-create",
            "--root",
            str(root),
            "--run-id",
            "handoff-run",
            "--spec-path",
            "spec.md",
            "--next-action",
            "Run the next isolated stage.",
            "--allowed-file",
            "spec.md",
            "--checkpoint-ref",
            "checkpoint.md",
            "--handoff-id",
            "handoff-one",
            "--final-review",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if create.returncode != 0:
        raise AssertionError(f"handoff creation failed: {create.stdout}\n{create.stderr}")
    package_path = root / ".codex" / "handoffs" / "handoff-one.json"
    package_text = package_path.read_text(encoding="utf-8")
    package = json.loads(package_text)
    if package["verified_stage_ids"] != ["first"] or "must-not-enter-handoff" in package_text:
        raise AssertionError(f"handoff leaked runtime context or missed evidence: {package}")
    fake_codex = root / "fake-codex"
    fake_codex.write_text(
        "#!/usr/bin/env python3\nimport json, sys\nfrom pathlib import Path\nPath('bridge-args.json').write_text(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)
    launch = subprocess.run(
        [sys.executable, str(SCRIPT), "handoff-launch", "--root", str(root), "--codex-bin", str(fake_codex), "handoff-one"],
        check=False,
        capture_output=True,
        text=True,
    )
    if launch.returncode != 0:
        raise AssertionError(f"handoff launch failed: {launch.stdout}\n{launch.stderr}")
    bridge_args = json.loads((root / "bridge-args.json").read_text(encoding="utf-8"))
    if bridge_args[:2] != ["exec", "-C"] or Path(bridge_args[2]).resolve() != root.resolve() or "handoff-one.json" not in bridge_args[-1] or "must-not-enter-handoff" in bridge_args[-1]:
        raise AssertionError(f"bridge did not receive a clean handoff prompt: {bridge_args}")
    review = subprocess.run(
        [sys.executable, str(SCRIPT), "handoff-review", "--root", str(root), "--summary", "Ready for human review.", "handoff-one"],
        check=False,
        capture_output=True,
        text=True,
    )
    if review.returncode != 0 or json.loads(package_path.read_text(encoding="utf-8"))["status"] != "waiting_human_final_review":
        raise AssertionError(f"final review was not requested: {review.stdout}\n{review.stderr}")
    repeat = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "handoff-create",
            "--root",
            str(root),
            "--run-id",
            "handoff-run",
            "--spec-path",
            "spec.md",
            "--next-action",
            "must fail due to limit",
            "--allowed-file",
            "spec.md",
            "--checkpoint-ref",
            "checkpoint.md",
            "--handoff-id",
            "handoff-two",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if repeat.returncode != 2 or "handoff limit reached" not in repeat.stderr:
        raise AssertionError(f"handoff limit was not enforced: {repeat.stdout}\n{repeat.stderr}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cw-supervisor-test-") as temp_dir:
        root = Path(temp_dir)
        scenario_success_serial(root)
        scenario_verifier_failure_stops_serial(root)
        scenario_verifier_launch_failure_stops_serial(root)
        scenario_health_and_cancel_stop_serial(root)
        scenario_deadline_becomes_unknown(root)
        scenario_recovery_marks_missing_process_unknown(root)
        scenario_fresh_handoff_bridge_and_review(root)
        scenario_contract_rejects_shell_string(root)
    print("cw supervisor fixtures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
