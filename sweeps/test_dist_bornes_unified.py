"""DIST-BORNES-1: cross-path boundaries and historical OFF contracts.

These source contracts are complemented by real OpenTTD smoke/Save/Load.
"""

import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_bytes

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def body(filename, name):
    src = (AI / filename).read_text(encoding="utf-8")
    start = src.index("function " + name + "(")
    opening = src.index("{", start)
    depth = 0
    for end in range(opening, len(src)):
        if src[end] == "{":
            depth += 1
        elif src[end] == "}":
            depth -= 1
            if depth == 0:
                return src[start:end + 1]
    raise AssertionError("Unterminated " + name)


class UnifiedDistanceContracts(unittest.TestCase):
    @staticmethod
    def read(name):
        return (AI / name).read_text(encoding="utf-8")

    def test_opt_in_off_on_all_difficulties_and_once_loaded(self):
        info = self.read("info.nut")
        block = re.search(r'AddSetting\(\{\s*name = "dist_bornes_unified".*?\}\);', info, re.S)
        self.assertIsNotNone(block)
        self.assertIn("default_value = 0", block.group())
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(), rf'{difficulty}_value\s*=\s*0\b')
        settings = self.read("settings.nut")
        self.assertEqual(settings.count('GetSetting("dist_bornes_unified")'), 1)
        self.assertIn("DIST_BORNES_UNIFIED <- false;", self.read("globals_pre.nut"))

    def test_one_window_is_pure_and_v269_is_request_scoped(self):
        window = body("candidates.nut", "OpexDistBornesWindow")
        self.assertNotIn("AIMap.", window)
        self.assertNotIn("AIController.", window)
        self.assertNotIn(".rawset", window)
        self.assertIn('mode == "road"', window)
        self.assertIn('"roadGenMax" in bounds', window)
        self.assertIn("minDistance = 0, maxDistance = cap", window)
        self.assertIn('"distBornesV269Relaxed" in bounds', window)
        self.assertIn("V269_RAIL_MAX_DIST > cap", window)
        self.assertIn("maxDistance = bounds.railAirOverlapMin - 1", window)
        self.assertIn("minDistance = bounds.railMax + 1", window)
        self.assertIn("flightMax = bounds.airMax", window)

    def test_every_consumer_uses_shared_window_only_when_opted_in(self):
        candidates = self.read("candidates.nut")
        v276 = self.read("candidates_v276.nut")
        po01c = self.read("po01c_generators.nut")
        for filename, names in (
            ("candidates.nut", ["OpexRoadDistanceAllowed", "OpexAirPairInBand",
                                "OpexRailPaxPairInBand", "OpexMakeCandidate",
                                "OpexGenerateSubsidyCandidates"]),
            ("po01c_generators.nut", ["OpexPO01CMakePaxCandidate"]),
            ("candidates_v276.nut", ["OpexV276PrepareUnit", "OpexV276Enumerate"]),
        ):
            for name in names:
                with self.subTest(filename=filename, function=name):
                    block = body(filename, name)
                    self.assertIn("DIST_BORNES_UNIFIED", block)
                    if name == "OpexV276Enumerate":
                        self.assertIn("c.distBornesWindow", block)
                    else:
                        self.assertIn("OpexDistBornesWindow", block)
        self.assertIn('} else if (kind == "pax") {', candidates)
        self.assertIn('} else if (kind == "pax") {', po01c)
        self.assertIn('else if (!u.pax && DIST_BORNES_V276_FREIGHT', v276)
        self.assertIn('v269LateFreight = DIST_BORNES_V276_FREIGHT', v276)
        self.assertIn('catalog.bounds.distBornesV269Relaxed <- request.v269LateFreight;', v276)

    def test_frozen_preexisting_source_inventory_is_still_exact(self):
        # Byte-exact preservation, including the prior V276-freight opt-in and
        # without rewriting the PO01D digest to accept the new branches.
        for filename in ("candidates.nut", "settings.nut", "info.nut"):
            with self.subTest(filename=filename):
                source = historical_bytes(filename, (AI / filename).read_bytes())
                self.assertNotIn(b"DIST_BORNES_UNIFIED", source)
                self.assertNotIn(b"dist_bornes_unified", source)


if __name__ == "__main__":
    unittest.main()
