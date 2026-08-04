from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContinuousWorkFixtureTests(unittest.TestCase):
    def test_supervisor_fixture(self) -> None:
        result = subprocess.run([sys.executable, str(ROOT / "assets" / "tools" / "test_cw_supervisor.py")], check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")

    def test_app_server_fixture(self) -> None:
        result = subprocess.run([sys.executable, str(ROOT / "assets" / "tools" / "test_cw_app_server_spike.py")], check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"{result.stdout}\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
