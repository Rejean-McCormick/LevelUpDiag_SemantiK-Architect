import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from levels.n06_security_hygiene import _tracked_files
from levels.s80_semantik_validation import diagnose_validator_failure


class Run1RegressionTests(unittest.TestCase):
    def test_security_scan_untracked_false_uses_git_tracked_scope(self):
        if not shutil.which("git"):
            self.skipTest("git unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            (root / "safe.txt").write_text("safe", encoding="utf-8")
            (root / ".env").write_text("LOCAL_ONLY=1", encoding="utf-8")
            subprocess.run(["git", "add", "safe.txt"], cwd=root, check=True)
            cfg = {"scan": {"exclude_dirs": []}}
            files = [rel for _, rel in _tracked_files(root, cfg, max_files=100, extra_globs=[])]
            self.assertIn("safe.txt", files)
            self.assertNotIn(".env", files)

    def test_s80_identifies_local_package_loss_inside_validator(self):
        cfg = {"semantik": {"local_packages": ["semantik_architect"]}}
        result = {
            "exit_code": 1,
            "timed_out": False,
            "stdout_tail": "ModuleNotFoundError: No module named 'semantik_architect'",
            "stderr_tail": "",
        }
        verdict, missing, recommendation = diagnose_validator_failure(cfg, result, import_ok=True)
        self.assertEqual(verdict, "FAIL")
        self.assertEqual(missing, "semantik_architect")
        self.assertIn("os.pathsep", recommendation)

    def test_s80_keeps_missing_pytest_as_blocked_dependency(self):
        cfg = {"semantik": {"local_packages": ["semantik_architect"]}}
        result = {
            "exit_code": 1,
            "timed_out": False,
            "stdout_tail": "",
            "stderr_tail": "ModuleNotFoundError: No module named 'pytest'",
        }
        verdict, missing, recommendation = diagnose_validator_failure(cfg, result, import_ok=True)
        self.assertEqual(verdict, "BLOCKED")
        self.assertEqual(missing, "pytest")
        self.assertIn("pytest", recommendation)


if __name__ == "__main__":
    unittest.main()
