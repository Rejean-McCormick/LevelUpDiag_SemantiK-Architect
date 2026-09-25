import ast
import json
import unittest
from pathlib import Path


class DeepAdversarialProfileTests(unittest.TestCase):
    @property
    def root(self):
        return Path(__file__).resolve().parents[1]

    def test_deep_only_levels_are_declared_and_ordered(self):
        manifest=json.loads((self.root/'levelupdiag_manifest.json').read_text(encoding='utf-8'))
        standard=manifest['campaigns']['standard']['levels']
        deep=manifest['campaigns']['deep']['levels']
        self.assertTrue(all(x not in standard for x in ('S90','S100','S110','S120')))
        self.assertEqual(deep[-4:], ['S90','S100','S110','S120'])
        meta={x['id']:x for x in manifest['levels']}
        self.assertLess(meta['S90']['order'],meta['S100']['order'])
        self.assertLess(meta['S100']['order'],meta['S110']['order'])
        self.assertLess(meta['S110']['order'],meta['S120']['order'])
        self.assertFalse(meta['S120']['parallel_safe'])

    def test_embedded_deep_probe_scripts_compile(self):
        for rel in (
            'levels/s90_semantik_adversarial_semantics.py',
            'levels/s100_semantik_runtime_mutation.py',
            'levels/s110_semantik_bridge_lexical_adversarial.py',
            'levels/s120_semantik_determinism_packaging.py',
        ):
            path=self.root/rel
            text=path.read_text(encoding='utf-8')
            compile(text,rel,'exec')
            tree=ast.parse(text)
            scripts=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in node.targets):
                    if isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
                        scripts.append(node.value.value)
            self.assertEqual(len(scripts),1,rel)
            compile(scripts[0],rel+'::<embedded>','exec')

    def test_deep_probes_use_temporary_mutation_surfaces(self):
        for rel in (
            'levels/s100_semantik_runtime_mutation.py',
            'levels/s110_semantik_bridge_lexical_adversarial.py',
            'levels/s120_semantik_determinism_packaging.py',
        ):
            text=(self.root/rel).read_text(encoding='utf-8')
            self.assertIn('TemporaryDirectory',text,rel)
        packaging=(self.root/'levels/s120_semantik_determinism_packaging.py').read_text(encoding='utf-8')
        self.assertIn('copytree(Path.cwd(), source',packaging)
        self.assertNotIn("pip','wheel',str(Path.cwd())",packaging)


if __name__ == '__main__':
    unittest.main()
