"""RLW-03 : contrats de non-intervention de la sonde Squirrel, sans OpenTTD.

Ces assertions statiques et les tests synthétiques RLW-02 ne remplacent pas
une compilation et un Save/Load dans OpenTTD (qualification ultérieure).
"""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class TestRailLongWindowProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = source("rail_long_window_probe.nut")
        cls.main = source("main.nut")
        cls.persist = source("persist.nut")
        cls.scheduler = source("scheduler.nut")

    def test_source_flag_off_and_no_extra_setting(self):
        self.assertIn("RLW03_SHADOW <- false;", source("globals_post.nut"))
        # L'instantane source inclut les deux settings independants V269 et
        # AIR-ROI-RENFORT-1 : RLW-03/04 n'ajoutent aucun setting eux-memes.
        self.assertEqual(source("info.nut").count("AddSetting("), 101)
        self.assertNotIn("rlw03", source("settings.nut").lower())

    def test_module_loaded_after_class_declaration_and_hook_declared(self):
        self.assertLess(self.main.index("class OpexAI"),
                        self.main.index('require("rail_long_window_probe.nut")'))
        self.assertIn("function _rlw03MonthlyObserve();", self.main)
        self.assertIn("_rlw03State = null;", self.main)

    def test_no_computation_when_off_or_without_decision_log(self):
        self.assertIn("if (RLW03_SHADOW) this._rlw03MonthlyObserve();", self.scheduler)
        self.assertIn("if (!RLW03_SHADOW || !DECISION_LOG || !MODE_RAIL", self.probe)
        self.assertEqual(self.scheduler.count("_rlw03MonthlyObserve()"), 1)

    def test_monthly_cohort_and_missing_data(self):
        self.assertIn("clone catalog.towns", self.probe)
        self.assertIn("(ranked.len() * 30 + 99) / 100", self.probe)
        self.assertIn("s.lastMonth == ym", self.probe)
        self.assertIn("if (!AITown.IsValidTown(id)) return -1", self.probe)
        self.assertIn("AITile.GetClosestTown(line.originA)", self.probe)
        self.assertIn("AITile.GetClosestTown(line.originB)", self.probe)
        self.assertIn("row.month == ym - 12", self.probe)
        self.assertIn("ym != s.lastMonth + 1", self.probe)
        self.assertIn("old >= 0 && coverage >= 0", self.probe)
        self.assertIn("growth != -1001", self.probe)

    def test_independent_signals_and_rail_only(self):
        self.assertIn('MODE_AIR ? OpexRLW03ReachedTowns(s.cohort, "air"', self.probe)
        self.assertIn('!MODE_AIR ? OpexRLW03ReachedTowns(s.cohort, "rail"', self.probe)
        self.assertIn('line.kind != "pax"', self.probe)
        self.assertIn('project.mode != "rail"', self.probe)
        self.assertIn('kind != "pax" && kind != "freight"', self.probe)
        self.assertIn("OpexAbandonedPairKey(c)", self.probe)
        self.assertIn("if (unique in seen) continue;", self.probe)
        self.assertIn("OpexProjectFinanceCapital(project) > cash", self.probe)
        self.assertIn("owner._tooClose(c)", self.probe)
        self.assertIn("s.paxShortage >= 2", self.probe)
        self.assertIn("s.freightShortage >= 2", self.probe)
        self.assertIn("age >= 24", self.probe)
        self.assertIn("coverage >= 800", self.probe)
        self.assertIn("growth <= 50", self.probe)
        self.assertIn("cash >= 100000", self.probe)

    def test_state_saved_in_full_and_short_modes(self):
        self.assertEqual(self.persist.count("shortSave.rlw03State <- this._rlw03State"), 1)
        self.assertEqual(self.persist.count("saveObj.rlw03State <- this._rlw03State"), 1)
        self.assertIn('if (("rlw03State" in data) && typeof data.rlw03State == "table")',
                      self.persist)
        self.assertIn("this._rlw03State = data.rlw03State;", self.persist)
        self.assertIn("this._rlw03State = null;", self.persist)

    def test_shadow_does_not_publish_build_or_mutate_projects(self):
        for forbidden in (
            "OpexRegenerateModeProjects(", "OpexBuildCandidates(",
            "OpexProjectSelectAffordable(", "BuildRail(", "OpexV276Request(",
            "_projects <-", "candidateGroups <-", "v269_rail_long_max",
        ):
            self.assertNotIn(forbidden, self.probe, forbidden)
        self.assertNotRegex(self.probe, r"\b(?:owner|this)\._projects\s*=(?!=)")
        self.assertEqual(self.probe.count('OpexDecide("RLW03_TRIGGER"'), 2)
        self.assertNotIn("AITownList(", self.probe)

    def test_no_undeclared_squirrel_class_method(self):
        definitions = set(re.findall(r"function OpexAI::(_\w+)\(", self.probe))
        declarations = set(re.findall(r"function (_\w+)\(", self.main))
        self.assertEqual(definitions - declarations, set())


if __name__ == "__main__":
    unittest.main()
