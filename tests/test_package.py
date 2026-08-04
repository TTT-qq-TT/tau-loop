from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.py"


def run(command: List[str], *, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    result = subprocess.run(command, check=False, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


class PackageLifecycleTests(unittest.TestCase):
    def test_adopt_preserves_existing_project_guidance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tau-loop-adopt-") as temporary:
            temporary_root = Path(temporary)
            codex_home = temporary_root / "codex-home"
            project = temporary_root / "project"
            (project / ".codex").mkdir(parents=True)
            agents = project / "AGENTS.md"
            memory = project / ".codex" / "memory.md"
            agents.write_text("# Existing Rules\n\nKeep this file.\n", encoding="utf-8")
            memory.write_text("# Existing Memory\n", encoding="utf-8")
            run([sys.executable, str(INSTALLER), "--codex-home", str(codex_home), "--quiet"])
            command = codex_home / "bin" / "tau"
            environment = dict(os.environ, TAU_LOOP_CODEX_HOME=str(codex_home))

            run([str(command), "adopt", "--root", str(project)], env=environment)

            self.assertEqual(agents.read_text(encoding="utf-8"), "# Existing Rules\n\nKeep this file.\n")
            self.assertEqual(memory.read_text(encoding="utf-8"), "# Existing Memory\n")
            self.assertTrue((project / ".codex" / "tools" / "cw_state.py").is_file())

    def test_clean_install_project_lifecycle_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tau-loop-package-") as temporary:
            temporary_root = Path(temporary)
            codex_home = temporary_root / "codex-home"
            project = temporary_root / "project"
            project.mkdir()
            run([sys.executable, str(INSTALLER), "--codex-home", str(codex_home)])

            command = codex_home / "bin" / "tau"
            self.assertTrue((codex_home / "skills" / "tau-loop" / "SKILL.md").is_file())
            self.assertTrue(command.is_file())
            environment = dict(os.environ, TAU_LOOP_CODEX_HOME=str(codex_home))

            run([str(command), "init", "--root", str(project)], env=environment)
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / ".codex" / "tools" / "cw_supervisor.py").is_file())
            self.assertTrue((project / ".codex" / ".tau-loop-managed.json").is_file())
            self.assertIn(project.name, (project / ".codex" / "memory.md").read_text(encoding="utf-8"))

            run([str(command), "state", "init", "--root", str(project)], env=environment)
            status = run([str(command), "status", "--root", str(project)], env=environment)
            self.assertIn('"project"', status.stdout)

            contract = project / "tau-fixture.json"
            contract.write_text(
                json.dumps(
                    {
                        "schema_version": "cw-run-contract/v1",
                        "id": "tau-fixture",
                        "stages": [
                            {
                                "id": "write-evidence",
                                "argv": [sys.executable, "-c", "from pathlib import Path; Path('tau-evidence.txt').write_text('complete')"],
                                "cwd": ".",
                                "verifier": {
                                    "argv": [sys.executable, "-c", "from pathlib import Path; assert Path('tau-evidence.txt').read_text() == 'complete'"],
                                    "cwd": ".",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            run([str(command), "run", "--root", str(project), "--run-id", "tau-fixture", "tau-fixture.json"], env=environment)
            run_status = run([str(command), "run-status", "--root", str(project), "tau-fixture"], env=environment)
            self.assertIn('"completed"', run_status.stdout)
            run([str(command), "verify", "--root", str(project)], env=environment)
            run([str(project / ".codex" / "hooks" / "verify-continuous-work-v1.sh"), str(project)])

            managed_tool = project / ".codex" / "tools" / "cw_state.py"
            original_tool = managed_tool.read_text(encoding="utf-8")
            managed_tool.write_text(original_tool + "\n# local customization\n", encoding="utf-8")
            preview = run([str(command), "upgrade", "--root", str(project), "--dry-run"], env=environment)
            self.assertIn("modified or unmanaged", preview.stdout)
            run([str(command), "upgrade", "--root", str(project)], env=environment)
            self.assertIn("local customization", managed_tool.read_text(encoding="utf-8"))

            memory = project / ".codex" / "memory.md"
            run([str(command), "uninstall", "--root", str(project)], env=environment)
            self.assertTrue(memory.is_file())
            self.assertTrue(managed_tool.is_file(), "modified tools must survive uninstall")

            run([sys.executable, str(INSTALLER), "--codex-home", str(codex_home), "--uninstall"])
            self.assertFalse((codex_home / "skills" / "tau-loop").exists())
            self.assertFalse(command.exists())


if __name__ == "__main__":
    unittest.main()
