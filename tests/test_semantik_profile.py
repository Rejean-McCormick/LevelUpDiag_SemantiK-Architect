import json
import os
import tempfile
import unittest
from pathlib import Path

from levelupdiag_core.semantik import (
    module_exists,
    normalize_distribution,
    target_python_env,
    windows_path_to_wsl,
)


class SemantikProfileTests(unittest.TestCase):
    def test_distribution_normalization(self):
        self.assertEqual(normalize_distribution("pytest>=8.0.0"), "pytest")
        self.assertEqual(normalize_distribution("pgf==1.1"), "pgf")
        self.assertEqual(normalize_distribution("jsonschema>=4.0.0"), "jsonschema")

    def test_src_layout_local_module_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "src" / "semantik_architect" / "domain"
            p.mkdir(parents=True)
            (root / "src" / "semantik_architect" / "__init__.py").write_text("", encoding="utf-8")
            (p / "__init__.py").write_text("", encoding="utf-8")
            self.assertTrue(module_exists(root, "semantik_architect.domain", ("src",)))
            self.assertFalse(module_exists(root, "semantik_architect.missing", ("src",)))

    def test_windows_path_to_wsl(self):
        self.assertEqual(
            windows_path_to_wsl(
                r"C:\mycode\SemantiK_Architect\SemantiK_Architect\runtime\sq-core\runtime.manifest.json"
            ),
            "/mnt/c/mycode/SemantiK_Architect/SemantiK_Architect/runtime/sq-core/runtime.manifest.json",
        )
        self.assertEqual(windows_path_to_wsl("tests/test_demo.py"), "tests/test_demo.py")

    def test_target_python_env_includes_src(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {
                "_target_root": td,
                "semantik": {
                    "python_execution": "native",
                    "python_path_entries": ["src"],
                },
            }
            env = target_python_env(cfg)
            self.assertIn(str(Path(td) / "src"), env["PYTHONPATH"])
            self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")

    def test_manifest_declares_v1_semantik_campaign(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "levelupdiag_manifest.json").read_text(encoding="utf-8"))
        ids = {x["id"] for x in data["levels"]}
        self.assertTrue({"S10", "S20", "S30", "S40", "S50", "S60", "S70", "S80", "S90", "S100", "S110", "S120"}.issubset(ids))
        self.assertEqual(data["suite_version"], "2.1.3")
        self.assertIn("semantik", data["campaigns"])
        self.assertIn("S80", data["campaigns"]["standard"]["levels"])
        self.assertNotIn("S90", data["campaigns"]["standard"]["levels"])
        self.assertEqual(data["campaigns"]["deep"]["levels"][-4:], ["S90", "S100", "S110", "S120"])

    def test_config_targets_clean_v1_tree(self):
        root = Path(__file__).resolve().parents[1]
        cfg = json.loads((root / "levelupdiag.config.json").read_text(encoding="utf-8"))
        profile = cfg["semantik"]
        self.assertIn("src/semantik_architect", profile["active_python_roots"])
        self.assertIn("schemas/gf_bridge_spec.schema.json", profile["schema_files"])
        self.assertNotIn("app", profile["local_packages"])
        self.assertEqual(profile["runtime_root"], "runtime")


if __name__ == "__main__":
    unittest.main()
