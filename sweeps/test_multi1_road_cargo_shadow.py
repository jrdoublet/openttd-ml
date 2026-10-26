"""MULTI-1: fourth hypothesis is diagnostic only, with a frozen OFF path."""

import hashlib
import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_bytes, MULTI1_ROAD_CARGO_HELPER_SHA256

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class Multi1RoadCargoShadowContracts(unittest.TestCase):
    def test_setting_is_explicitly_opt_in_on_four_profiles(self):
        info = source("info.nut")
        block = re.search(
            r'AddSetting\(\{ name = "multi1_road_cargo_shadow".*?\}\);', info, re.S
        )
        self.assertIsNotNone(block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", block.group())
        self.assertEqual(source("settings.nut").count(
            'AIController.GetSetting("multi1_road_cargo_shadow")'), 1)
        self.assertIn("MULTI1_ROAD_CARGO_SHADOW <- 0;", source("globals_pre.nut"))

    def test_legacy_paths_keep_original_frozen_bytes(self):
        # Changes to an old decision path do not silently rebaseline its hash.
        for name in ("info.nut", "settings.nut", "main.nut", "probes.nut", "candidates.nut"):
            with self.subTest(name=name):
                raw = (AI / name).read_bytes()
                self.assertNotIn(b"MULTI1_ROAD_CARGO_SHADOW", historical_bytes(name, raw))
        self.assertEqual(len(MULTI1_ROAD_CARGO_HELPER_SHA256), 64)

    def test_shadow_never_publishes_or_executes_a_route(self):
        src = source("candidates.nut")
        start = src.index("function OpexMulti1RoadCargoShadowArm")
        end = src.index("/* Classement routier complet.", start)
        shadow = src[start:end]
        for forbidden in ("OpexBuildRoadRoute(", "OpexReselectProjects(",
                          "OpexProjectRememberAll(", ".candidateGroups", ".outputs.rawset"):
            self.assertNotIn(forbidden, shadow)
        self.assertIn("s.planCursor >= 3", shadow)
        self.assertIn("sources = OpexMulti1RoadCargoSample(catalog.producers[alternate], 2", shadow)
        self.assertIn("OpexMulti1RoadCargoSample(catalog.towns, 4", shadow)
        self.assertIn("200000", shadow)
        self.assertIn("OpexProjectFinanceCapital(project)", shadow)
        self.assertIn("AIRoad.GetCurrentRoadType()", shadow)
        self.assertIn("AIRoad.SetCurrentRoadType(roadTypeBefore)", shadow)
        self.assertIn("OpexMulti1RoadCargoShadowLog", shadow)
        self.assertNotIn('OpexDecide("MULTI1_ROAD_CARGO_SHADOW"', shadow)

    def test_both_loops_and_po01c_have_opt_in_hook(self):
        for name in ("main.nut", "probes.nut"):
            with self.subTest(name=name):
                src = source(name)
                self.assertIn("if (MULTI1_ROAD_CARGO_SHADOW == 1 && MULTI1_ROAD_CARGO_PENDING != null)", src)
                self.assertIn("OpexMulti1RoadCargoShadowTick(this);", src)
        po = source("po01c_regen.nut")
        self.assertIn("OpexMulti1RoadCargoShadowArm(s.catalog, s.lines, s.abandoned, generated.freightCargo, all);", po)
        cands = source("candidates.nut")
        self.assertIn("OpexMulti1RoadCargoShadowArm(catalog, lines, abandonedPairs, freightCargo, all);", cands)
        self.assertIn("V276_CAND_SLICES > 0", cands)

    def test_load_discards_transient_transaction_and_no_policy_output(self):
        data = source("persist.nut")
        load = data[data.index("function OpexAI::Load("):]
        self.assertLess(load.index("MULTI1_ROAD_CARGO_PENDING = null"),
                        load.index("V276_CATALOG_TASK = null"))
        src = source("candidates.nut")
        block = src[src.index("function OpexMulti1RoadCargoShadowTick"):src.index("/* Classement routier complet.")]
        self.assertIn("OpexCandidateIsAbandoned(candidate, owner._abandonedPairs)", block)
        self.assertIn("OpexOriginServed(owner._lines, candidate.src, true)", block)
        self.assertIn("if (realProfit > s.predictedProfit)", block)


if __name__ == "__main__":
    unittest.main()
