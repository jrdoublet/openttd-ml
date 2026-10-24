"""Publication defaults and benchmark instrumentation, without starting a game."""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import benchmark_opex_settings, effective_ai_settings, validate_policy_settings
from run_c66_reference import inject_probes


class PublicationProbesDefault(unittest.TestCase):
    def test_publication_metadata_and_four_defaults(self):
        text = (ROOT / "ai/OpexAI/info.nut").read_text()
        block = text.split('name = "probes"', 1)[1].split("});", 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"\b{level}_value\s*=\s*0\b")
        self.assertRegex(text, r"GetVersion\(\)\s*\{ return 8;")
        self.assertRegex(text, r'GetDate\(\)\s*\{ return "2026-10-24";')

    def test_host_injection_and_explicit_mask(self):
        self.assertEqual(inject_probes(None), "OpexAI[probes=2]")
        self.assertEqual(inject_probes("OpexAI"), "OpexAI[probes=2]")
        self.assertEqual(inject_probes("OpexAI[mode_air=0]"), "OpexAI[mode_air=0,probes=2]")
        self.assertEqual(inject_probes("OpexAI[probes=514]"), "OpexAI[probes=514]")
        for value in (0, 4, 256, 512, -1, 2147483648):
            with self.subTest(value=value), self.assertRaises(ValueError):
                inject_probes(None, value)
            with self.subTest(explicit=value), self.assertRaises(ValueError):
                inject_probes(f"OpexAI[probes={value}]")
        tree = ast.parse((ROOT / "sweeps/run_c66_reference.py").read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "add_argument"
                 and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "--probes"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(next(k.value.value for k in calls[0].keywords if k.arg == "default"), 2)

    def test_direct_constructor_preserves_explicit_masks(self):
        self.assertEqual(benchmark_opex_settings((("mode_air", 0),)),
                         (("mode_air", 0), ("probes", 2)))
        # Dedicated diagnostics may deliberately disable all signs.
        for value in (0, 2, 514):
            self.assertEqual(benchmark_opex_settings({"probes": value}), (("probes", value),))

    def test_provenance_and_effective_identity(self):
        info = ROOT / "ai/OpexAI/info.nut"
        automatic = effective_ai_settings(info)
        explicit = effective_ai_settings(info, (("probes", 2),))
        self.assertEqual(automatic["defaults"]["probes"], 0)
        self.assertEqual(automatic["explicit"], {})
        self.assertEqual(automatic["benchmark_injected"], {"probes": 2})
        self.assertEqual(automatic["effective"], explicit["effective"])
        self.assertEqual(validate_policy_settings(automatic["effective"], explicit["effective"]), {})
        candidate = effective_ai_settings(info, (("mode_air", 0),))
        differences = validate_policy_settings(automatic["effective"], candidate["effective"], ("mode_air",))
        self.assertEqual(set(differences), {"mode_air"})
        self.assertEqual(effective_ai_settings(info, (("probes", 514),))["effective"]["probes"], 514)

    def test_active_direct_opex_constructors_keep_signs(self):
        # Inventory invariant: every direct OpexAI descriptor uses the same fallback.
        found = 0
        for path in (ROOT / "sweeps").glob("*.py"):
            if path.name.startswith("test"):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
                if name != "local_folder" or len(node.args) < 2:
                    continue
                if not isinstance(node.args[1], ast.Constant) or node.args[1].value != "OpexAI":
                    continue
                found += 1
                with self.subTest(path=path.name, line=node.lineno):
                    self.assertGreaterEqual(len(node.args), 3)
                    self.assertIsInstance(node.args[2], ast.Call)
                    self.assertEqual(node.args[2].func.id, "benchmark_opex_settings")
        self.assertGreater(found, 0)


if __name__ == "__main__":
    unittest.main()
