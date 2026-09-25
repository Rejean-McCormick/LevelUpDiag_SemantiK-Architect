import unittest
from pathlib import Path


class Run2RegressionTests(unittest.TestCase):
    @property
    def root(self):
        return Path(__file__).resolve().parents[1]

    def test_s90_requires_stable_language_error_for_unknown_operation(self):
        text=(self.root/'levels/s90_semantik_adversarial_semantics.py').read_text(encoding='utf-8')
        self.assertIn('expect_code(lambda: plan(hinted), "SA-LANG-003")', text)
        self.assertNotIn('except (ValueError, SemantikArchitectError)', text)

    def test_s60_requires_stable_coverage_error(self):
        text=(self.root/'levels/s60_semantik_faithfulness.py').read_text(encoding='utf-8')
        self.assertIn('negative_error == "SA-SEM-002"', text)
        self.assertNotIn('except (SemantikArchitectError,ValueError)', text)
        self.assertIn('bad_unit=RealizationUnit(', text)
        self.assertNotIn('bad=type(lp)(lp.plan_id,lp.language,lp.locale,lp.blocks,(),lp.capability_profile)', text)


if __name__ == '__main__':
    unittest.main()
