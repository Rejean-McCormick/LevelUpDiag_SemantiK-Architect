import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from levelupdiag_core.report import Report
from levels import s70_semantik_public_surfaces as s70


class Run4RegressionTests(unittest.TestCase):
    def _cfg(self, root):
        return {
            "_target_root": str(root),
            "semantik": {
                "public_sdk_methods": ["render"],
                "cli_commands": ["render"],
                "http_paths": ["/health"],
            },
        }

    def _report(self, root):
        return Report("S70", "Public SDK / CLI / HTTP Surface", "test", str(root), "run4")

    def test_s70_rejects_runtime_warning_on_cli_stderr(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            http = root / "src/semantik_architect/adapters/inbound/http"
            http.mkdir(parents=True)
            (http / "server.py").write_text('ROUTES = ["/health"]\n', encoding="utf-8")
            results = [
                {
                    "exit_code": 0,
                    "stdout_tail": '{"version":"1.0.0","sdk":{"render":true},"cli_callable":true,"http_callable":true}\n',
                    "stderr_tail": "",
                },
                {
                    "exit_code": 0,
                    "stdout_tail": "render\n",
                    "stderr_tail": "RuntimeWarning: already imported\n",
                },
            ]
            with patch.object(s70, "run_target_python", side_effect=results):
                report = self._report(root)
                s70.run(self._cfg(root), report)
            cli = next(x for x in report.findings if x["id"] == "semantik.public.cli_contract")
            self.assertEqual(cli["verdict"], "FAIL")
            self.assertTrue(cli["evidence"]["runtime_warning"])

    def test_s70_invokes_python_with_runtimewarning_as_error(self):
        text = (Path(__file__).resolve().parents[1] / "levels/s70_semantik_public_surfaces.py").read_text(encoding="utf-8")
        self.assertIn('"error::RuntimeWarning"', text)
        self.assertIn('and not stderr', text)


if __name__ == "__main__":
    unittest.main()
