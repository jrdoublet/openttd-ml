"""Merge contract: ROAD1Y defaults stay intact while RAIL decisions are added.

This is a source/inventory test, not an economic qualification or NoAI smoke.
"""

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def setting(name):
    source = (ROOT / "info.nut").read_text(encoding="utf-8")
    pat = r'AddSetting\(\{\s*name\s*=\s*"' + re.escape(name) + r'"([\s\S]*?)\}\);'
    matches = re.findall(pat, source)
    if len(matches) != 1:
        raise AssertionError(f"{name}: AddSetting count={len(matches)}")
    return matches[0]


class MergeRoadRailDefaults(unittest.TestCase):
    def test_expected_user_defaults_at_all_difficulties(self):
        expected = {
            "rail_sibling": 1,
            "rail_open": 1,
            "rail_loop": 1,
            "rail_fill": 0,
            "v257_demand": 1,
            "road1y_load_orders": 1,
            "road1y_spread_stops": 2,
        }
        for name, value in expected.items():
            block = setting(name)
            with self.subTest(name=name):
                for difficulty in ("easy", "medium", "hard", "custom"):
                    self.assertRegex(block, rf'\b{difficulty}_value\s*=\s*{value}\b')

    def test_settings_inventory_unique_and_complete(self):
        info = (ROOT / "info.nut").read_text(encoding="utf-8")
        names = re.findall(r'AddSetting\(\{\s*name\s*=\s*"([^"]+)"', info)
        self.assertEqual(len(names), 166)
        self.assertEqual(len(set(names)), len(names))
        settings = (ROOT / "settings.nut").read_text(encoding="utf-8")
        for name in ("rail_sibling", "rail_open", "rail_loop", "rail_fill", "v257_demand"):
            with self.subTest(setting=name):
                self.assertEqual(settings.count('GetSetting("' + name + '")'), 1)


if __name__ == "__main__":
    unittest.main()
