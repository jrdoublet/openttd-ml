"""Static contracts for the adopted C121 hub realization switch.

Run in Docker with the repository's existing unittest workflow. These
contracts complement, but do not replace, the archived 40x10 game A/B.
"""

from pathlib import Path
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(filename):
    return (AI / filename).read_text(encoding="utf-8")


class TestDirectRealizationDefault(unittest.TestCase):
    def test_switch_on_by_default_but_can_be_disabled(self):
        info = src("info.nut")
        setting = info.split('name = "air_p0_direct_realization",', 1)[1].split('});', 1)[0]
        for difficulty in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{difficulty} = 1", setting)
        self.assertIn("AIR_P0_DIRECT_REALIZATION <- true;", src("globals_pre.nut"))
        self.assertEqual(src("settings.nut").count(
            'AIController.GetSetting("air_p0_direct_realization")'), 1)

    def test_hub_only_direct_ratio_and_cold_start(self):
        models = src("projects_models.nut")
        self.assertIn('if (arm != "hubsite" && arm != "hubhub") return 1.0;', models)
        self.assertIn('return C121_AIR_P0_DIRECT_FACTOR[arm];', models)
        self.assertIn('local direct = n > 0 ? acc[0].tofloat() / (n.tofloat() * 1000.0) : 1.0;', models)
        self.assertIn('if (direct != 1.0) AIR_P0_DIRECT_REALIZATION_ACTIVE = true;', models)
        self.assertIn('C121_AIR_P0_DIRECT_FACTOR <- { hubsite = 1.0, hubhub = 1.0 };',
                      src("globals_pre.nut"))
        # One observation, no pseudo-observation, no empirical smoothing.
        self.assertEqual(700 / (1 * 1000), 0.7)

    def test_no_double_calibration_while_cold_keeps_legacy(self):
        models = src("projects_models.nut")
        for name in ("OpexC70Profit", "OpexC82Profit"):
            block = models.split(f"function {name}(project)", 1)[1].split("\n}", 1)[0]
            self.assertIn("AIR_P0_DIRECT_REALIZATION_ACTIVE", block)
            self.assertIn("OpexC121ProjectHasRealization(project, false)", block)
            self.assertIn("project.payload.economics.realizationFactor != 1.0", block)
            self.assertIn("return project.profitAnnual;", block)
        self.assertIn("if (!C70_MODE_CALIBRATION) return project.profitAnnual;", models)

    def test_annual_and_reload_derive_non_persistent_cache(self):
        models = src("projects_models.nut")
        settings = src("settings.nut")
        persist = src("persist.nut")
        self.assertIn('AIR_P0_DIRECT_REALIZATION_ACTIVE = false;', models)
        self.assertIn('C121_AIR_P0_DIRECT_FACTOR.hubsite = 1.0;', settings)
        self.assertIn('C121_AIR_P0_DIRECT_FACTOR.hubhub = 1.0;', settings)
        self.assertIn('line.c121RealizationYear < year - 1', models)
        self.assertIn('sums[line.c121Arm][0] += line.c121RealizationPm;', models)
        self.assertIn('OpexC121ApplyRealizationSums(sums, year, "reload");', models)
        self.assertIn('OpexC121RecomputeRealizationFactors(this._lines)', persist)
        self.assertIn('OpexC121ApplyRealizationSums(c121RealizationSums, year, "annual");',
                      src("task_report.nut"))


if __name__ == "__main__":
    unittest.main()
