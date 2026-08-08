from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.py"

IS_WINDOWS = sys.platform == "win32"


def run(command: List[str], *, env: Optional[Dict[str, str]] = None, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    result = subprocess.run(command, check=False, capture_output=True, text=True, env=env, cwd=cwd)
    if result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def tau_env(codex_home: Path) -> Dict[str, str]:
    return dict(os.environ, TAU_LOOP_CODEX_HOME=str(codex_home))


def tau_command(codex_home: Path) -> List[str]:
    """The tau init entry: the bash launcher on POSIX, direct Python on Windows."""
    if IS_WINDOWS:
        return [sys.executable, str(codex_home / "skills" / "tau-loop" / "assets" / "tools" / "project_lifecycle.py")]
    return [str(codex_home / "bin" / "tau")]


def verify_command(project: Path) -> List[str]:
    """The packaged verify hook: bash entry on POSIX, Python entry on Windows."""
    if IS_WINDOWS:
        return [sys.executable, str(project / ".harness" / "hooks" / "verify.py")]
    return ["bash", str(project / ".harness" / "hooks" / "verify.sh")]


class PackageLifecycleTests(unittest.TestCase):
    def test_clean_install_init_verify_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tau-loop-package-") as temporary:
            temporary_root = Path(temporary)
            codex_home = temporary_root / "codex-home"
            project = temporary_root / "project"
            project.mkdir()
            run([sys.executable, str(INSTALLER), "--codex-home", str(codex_home)])

            command = codex_home / "bin" / "tau"
            skill_root = codex_home / "skills" / "tau-loop"
            self.assertTrue((skill_root / "SKILL.md").is_file())
            self.assertTrue((skill_root / "assets" / "AGENTS.md").is_file())
            self.assertTrue((skill_root / "assets" / "hooks" / "verify.sh").is_file())
            self.assertTrue((skill_root / "assets" / "hooks" / "verify.py").is_file())
            self.assertTrue((skill_root / "assets" / "tools" / "project_lifecycle.py").is_file())
            self.assertTrue(command.is_file())

            run(tau_command(codex_home) + ["init", "--root", str(project)], env=tau_env(codex_home))
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / ".harness" / "memory.md").is_file())
            self.assertTrue((project / ".harness" / "plan.md").is_file())
            self.assertTrue((project / ".harness" / "hooks" / "pre-task.sh").is_file())
            self.assertTrue((project / ".harness" / "hooks" / "pre-task.py").is_file())
            self.assertTrue((project / ".harness" / "hooks" / "pre-closeout.sh").is_file())
            self.assertTrue((project / ".harness" / "hooks" / "pre-closeout.py").is_file())
            self.assertTrue((project / ".harness" / "hooks" / "verify.sh").is_file())
            self.assertTrue((project / ".harness" / "hooks" / "verify.py").is_file())
            self.assertTrue((project / ".harness" / "tools" / "check_doc_freshness.py").is_file())
            self.assertTrue((project / ".harness" / "tools" / "check_task_state.py").is_file())
            self.assertTrue((project / ".harness" / "specs" / "TEMPLATE.md").is_file())
            self.assertTrue((project / ".harness" / ".tau-loop-managed.json").is_file())
            self.assertTrue((project / ".harness-workflow").is_file())
            self.assertIn(project.name, (project / ".harness" / "memory.md").read_text(encoding="utf-8"))

            # no cw files may be installed
            cw_files = [p for p in (project / ".harness").rglob("*") if "cw" in p.name.lower()]
            self.assertEqual(cw_files, [])

            # the packaged verify hook passes on a freshly initialized project
            run(verify_command(project) + [str(project)])

            # uninstall roundtrip
            run([sys.executable, str(INSTALLER), "--codex-home", str(codex_home), "--uninstall"])
            self.assertFalse(skill_root.exists())
            self.assertFalse(command.exists())

    def test_only_init_command_exposed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tau-loop-surface-") as temporary:
            temporary_root = Path(temporary)
            codex_home = temporary_root / "codex-home"
            run([sys.executable, str(INSTALLER), "--codex-home", str(codex_home), "--quiet"])
            command = codex_home / "bin" / "tau"

            help_text = run(tau_command(codex_home) + ["--help"]).stdout
            self.assertIn("tau init", help_text)

            for retired in ("adopt", "upgrade", "uninstall", "run", "run-status", "cancel", "recover",
                            "handoff", "agent-run", "loop", "loop-status", "loop-recover", "loop-cancel",
                            "state", "status", "doctor", "verify"):
                with self.subTest(command=retired):
                    result = subprocess.run(tau_command(codex_home) + [retired], check=False, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    if IS_WINDOWS:
                        self.assertIn("invalid choice", result.stderr)
                    else:
                        self.assertIn("Unknown command", result.stderr)

    def test_init_preserves_existing_user_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tau-loop-preserve-") as temporary:
            temporary_root = Path(temporary)
            codex_home = temporary_root / "codex-home"
            project = temporary_root / "project"
            (project / ".harness").mkdir(parents=True)
            agents = project / "AGENTS.md"
            memory = project / ".harness" / "memory.md"
            agents.write_text("# Existing Rules\n\nKeep this file.\n", encoding="utf-8")
            memory.write_text("# Existing Memory\n", encoding="utf-8")
            run([sys.executable, str(INSTALLER), "--codex-home", str(codex_home), "--quiet"])
            command = codex_home / "bin" / "tau"

            run(tau_command(codex_home) + ["init", "--root", str(project)], env=tau_env(codex_home))

            self.assertEqual(agents.read_text(encoding="utf-8"), "# Existing Rules\n\nKeep this file.\n")
            self.assertEqual(memory.read_text(encoding="utf-8"), "# Existing Memory\n")


class PackagedAssetTests(unittest.TestCase):
    def test_assets_have_no_cw_references(self) -> None:
        import re
        # Match the retired cw brand (codewhale / cw_* commands) without false
        # positives on legitimate substrings such as Path.cwd() or workflow.
        brand = re.compile(r"(?:^|[^a-z])cw(?:$|[^a-z])|codewhale")
        offenders: List[Path] = []
        for path in sorted((ROOT / "assets").rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.name.startswith(("cw", "cw_")) or "cw" in path.stem.lower():
                offenders.append(path)
                continue
            if brand.search(path.read_text(encoding="utf-8", errors="ignore").lower()):
                offenders.append(path)
        self.assertEqual(offenders, [])

    def test_mirror_consistency_between_harness_and_assets(self) -> None:
        for rel in (
            "tools/check_doc_freshness.py",
            "tools/check_task_state.py",
            "hooks/pre-task.sh",
            "hooks/pre-task.py",
            "hooks/pre-closeout.sh",
            "hooks/pre-closeout.py",
            "hooks/verify.sh",
            "hooks/verify.py",
        ):
            with self.subTest(rel=rel):
                harness = ROOT / ".harness" / rel
                asset = ROOT / "assets" / rel
                self.assertTrue(harness.is_file(), f"missing .harness/{rel}")
                self.assertTrue(asset.is_file(), f"missing assets/{rel}")
                self.assertEqual(harness.read_bytes(), asset.read_bytes(), f"mirror drift: {rel}")
        self.assertEqual(
            (ROOT / "AGENTS.md").read_bytes(),
            (ROOT / "assets" / "AGENTS.md").read_bytes(),
            "AGENTS.md mirror drift",
        )


if __name__ == "__main__":
    unittest.main()
