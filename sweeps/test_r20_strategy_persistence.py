"""R20 source contracts, not a NoAI Save/Load roundtrip."""
from pathlib import Path
import re
import unittest
from opex_projects_source import read_projects_source

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


def body(source, name):
    return source.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


class TestStrategyPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (AI / "persist.nut").read_text(encoding="utf-8")
        cls.save = body(cls.source, "OpexSaveC121Strategy")
        cls.load = body(cls.source, "OpexLoadC121Strategy")
        cls.restore = body(cls.source, "OpexRestoreC121Strategy")

    def test_short_and_full_saves_include_optional_versioned_state(self):
        save = body(self.source, "OpexAI::Save")
        self.assertIn("if (OpexC121StrategyStateEnabled()) OpexSaveC121Strategy(shortSave);", save)
        self.assertIn("if (OpexC121StrategyStateEnabled()) OpexSaveC121Strategy(saveObj);", save)
        self.assertLess(save.index("OpexSaveC121Strategy(shortSave)"), save.index("return shortSave;"))
        self.assertLess(save.index("OpexSaveC121Strategy(saveObj)"), save.index("return saveObj;"))
        self.assertIn("version = 1,", self.save)

    def test_each_observer_or_policy_can_enable_state_without_economics_gate(self):
        enabled = body(self.source, "OpexC121StrategyStateEnabled")
        self.assertIn("return C121_AIR_PRESSURE_PROBE || C121_AIR_PROJECT_REALIZATION_ADAPTIVE", enabled)
        self.assertIn("|| C122_AIR_REGIME_PRIORITY || C122_AIR_REGIME_SHADOW;", enabled)
        self.assertNotIn("C121_AIR_ECONOMICS", enabled)
        self.assertNotIn("C122_AIR_THREAT", enabled)

    def test_observation_tables_are_copied_without_floats_or_world_scan(self):
        self.assertIn("towns = clone C121_AIR_PRESSURE_ACCUM.towns,", self.save)
        self.assertIn("clone C121_AIR_PRESSURE_PREV", self.save)
        for token in ("yearsObserved = C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED",
                      "regime = C121_AIR_PROJECT_REALIZATION_REGIME",
                      "year = C121_AIR_PRESSURE_ACCUM.year", "samples = C121_AIR_PRESSURE_ACCUM.samples"):
            self.assertIn(token, self.save)
        self.assertNotIn("tofloat", self.save)
        self.assertNotIn("AITown.", self.save)
        self.assertNotIn("C121_CATALOG_CACHE", self.save)
        self.assertNotIn("C121_AIR_PRESSURE_SNAPSHOT", self.save)

    def test_load_rejects_unknown_versions_and_noninteger_or_incomplete_state(self):
        for token in ('typeof data != "table"', 'typeof data[key] != "integer"',
                      "data.version != 1", "data.regime < -1", "data.regime > 1",
                      "data.yearsObserved < 0", '!("accum" in data)', '!("previous" in data)',
                      'typeof townId != "integer"', 'typeof remaining != "integer"',
                      'typeof a.towns != "table"', 'p[key] > 1000'):
            self.assertIn(token, self.load)
        self.assertIn("towns.rawset(townId, remaining);", self.load)
        self.assertNotIn("IsValidTown", self.load)
        self.assertNotRegex(self.load, r"\bAI\w+\.")
        self.assertNotIn("OpexC121StrategyStateEnabled()", self.load)

    def test_load_buffers_before_settings_instead_of_applying_early(self):
        load = body(self.source, "OpexAI::Load")
        self.assertLess(load.index("OPEX_RELOAD_C121_STRATEGY = null;"), load.index("if (data == null) return;"))
        self.assertIn('if ("c121Strategy" in data) OPEX_RELOAD_C121_STRATEGY = OpexLoadC121Strategy(data.c121Strategy);', load)
        self.assertNotIn("OpexRestoreC121Strategy", load)
        main = (AI / "main.nut").read_text(encoding="utf-8").split("function OpexAI::Start()", 1)[1]
        self.assertLess(main.index("OpexLoadSettings();"), main.index("this._reconcileAfterLoad();"))
        reconcile = body(self.source, "OpexAI::_reconcileAfterLoad")
        self.assertRegex(reconcile, r"OpexRestoreC121Strategy\(OPEX_RELOAD_C121_STRATEGY\);\s*OPEX_RELOAD_C121_STRATEGY = null;")

    def test_legacy_missing_state_restarts_observation_without_reclassification(self):
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME = -1;", self.restore)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED = 0;", self.restore)
        self.assertIn("if (!OpexC121StrategyStateEnabled()) return;", self.restore)
        self.assertRegex(self.restore, r'if \(data == null\)\s*\{\s*AILog.Info\([^;]+;\s*return;')
        code = re.sub(r"/\*.*?\*/", "", self.restore, flags=re.S)
        self.assertNotIn("OpexC121PressureAdvanceYear(", code)

    def test_regime_and_observation_progress_are_restored_together(self):
        for assignment in (
            "C121_AIR_PROJECT_REALIZATION_REGIME = data.regime;",
            "C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED = data.yearsObserved;",
            "C121_AIR_PRESSURE_ACCUM = data.accum;",
            "C121_AIR_PRESSURE_PREV = data.previous;",
        ):
            self.assertIn(assignment, self.restore)
        self.assertIn("C121_AIR_PRESSURE_SNAPSHOT = null;", self.restore)

    def test_classifier_keeps_lock_and_closes_each_accumulator_year_once(self):
        projects = read_projects_source()
        advance = body(projects, "OpexC121PressureAdvanceYear")
        self.assertIn("if (C121_AIR_PRESSURE_ACCUM.year == year) return;", advance)
        self.assertIn("if (C121_AIR_PROJECT_REALIZATION_REGIME < 0", advance)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED++;", advance)
        self.assertIn("C121_AIR_PRESSURE_ACCUM = OpexC121PressureNewAccum(year);", advance)


if __name__ == "__main__":
    unittest.main()