import json
import tempfile
import unittest
from pathlib import Path

from levelupdiag_core.semantik import (
    runtime_manifest_paths,
    scan_architecture_imports,
    scan_language_branches,
)


class SemantikRuleTests(unittest.TestCase):
    def _cfg(self, root: Path):
        return {
            "_target_root": str(root),
            "scan": {"exclude_dirs": []},
            "semantik": {
                "core_forbidden_import_prefixes": ["pgf", "semantik_architect.adapters"],
                "application_forbidden_import_prefixes": ["pgf", "semantik_architect.adapters"],
                "runtime_root": "runtime",
                "runtime_manifest_globs": ["runtime.manifest.json", "*.runtime.json"],
            },
        }

    def test_architecture_import_violation_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            domain = root / "src/semantik_architect/domain"
            domain.mkdir(parents=True)
            (domain / "bad.py").write_text("import pgf\n", encoding="utf-8")
            hits = scan_architecture_imports(self._cfg(root))
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["module"], "pgf")
            self.assertEqual(hits[0]["zone"], "domain")

    def test_language_branch_is_detected_in_shared_core(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app = root / "src/semantik_architect/application"
            app.mkdir(parents=True)
            (app / "bad.py").write_text(
                'def f(language):\n    return 1 if language == "fr" else 2\n',
                encoding="utf-8",
            )
            hits = scan_language_branches(self._cfg(root))
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["path"], "src/semantik_architect/application/bad.py")

    def test_runtime_manifest_discovery_is_composed_not_single_pgf(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            runtime = root / "runtime" / "sq-core"
            runtime.mkdir(parents=True)
            (runtime / "runtime.manifest.json").write_text(
                json.dumps({"schema_version": "1.0", "runtime_set_id": "sq-core"}),
                encoding="utf-8",
            )
            paths = runtime_manifest_paths(self._cfg(root))
            self.assertEqual([p.name for p in paths], ["runtime.manifest.json"])


if __name__ == "__main__":
    unittest.main()
