"""Tests de contrat pour EB-10 : garde sentinelle 65535 et acceptation express urbaine >= 8."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestEB10Guards(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"eb10_guards"', info)
        block = re.search(r'AddSetting\(\{\s*name = "eb10_guards"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting eb10_guards manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 1", body)
        self.assertIn("easy_value = 0", body)
        self.assertIn("medium_value = 0", body)
        self.assertIn("hard_value = 0", body)
        self.assertIn("custom_value = 0", body)

    def test_global_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("EB10_GUARDS <- false;", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('EB10_GUARDS = AIController.GetSetting("eb10_guards") == 1;', settings)

    def test_lines_and_overrides_sentinel_65535(self):
        lines = read_nut("lines.nut")
        overrides = read_nut("bus_districts_overrides.nut")
        for code, label in ((lines, "lines.nut"), (overrides, "bus_districts_overrides.nut")):
            self.assertIn("EB10_GUARDS", code, label)
            self.assertIn("dst == 65535", code, label)
            self.assertIn("src == 65535", code, label)
            self.assertIn("AIIndustry.IsValidIndustry(dst)", code, label)
            self.assertIn("AIIndustry.IsValidIndustry(src)", code, label)

    def test_catalog_and_po01c_acceptance_guard(self):
        catalog = read_nut("catalog.nut")
        po01c = read_nut("po01c_generators.nut")
        for code, label in ((catalog, "catalog.nut"), (po01c, "po01c_generators.nut")):
            self.assertIn("EB10_GUARDS", code, label)
            self.assertIn("acceptance >= 8", code, label)
            self.assertIn("AICargo.CC_EXPRESS", code, label)

    def test_persist_filter_removes_65535(self):
        persist = read_nut("persist.nut")
        self.assertIn("EB10_GUARDS", persist)
        self.assertIn('"|65535"', persist)

    def test_hygiene_no_forbidden_constructs(self):
        for name in ("lines.nut", "bus_districts_overrides.nut", "catalog.nut", "po01c_generators.nut", "persist.nut"):
            content = read_nut(name)
            self.assertNotIn(".find(", content, f".find( interdit dans {name}")


if __name__ == "__main__":
    unittest.main()
