"""V233L-CONSTRUCTIBILITE: contrats du contre-factuel mono/double, sans moteur.

Ce fichier ne pretends pas que AITestMode compose correctement les commandes
successives, ni qu'une OD est reellement constructible ou profitable.
"""

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


def function(name, filename):
    content = source(filename)
    marker = "function " + name + "("
    start = content.index(marker)
    end = content.find("\nfunction ", start + len(marker))
    return content[start:] if end < 0 else content[start:end]


class V233LConstructibilityContracts(unittest.TestCase):
    def test_setting_is_separate_default_off_on_all_difficulties(self):
        info = source("info.nut")
        block = re.search(r'name = "v233l_constructibilite"([\s\S]*?)\}\);', info)
        self.assertIsNotNone(block)
        for token in ("min_value = 0", "max_value = 2", "easy_value = 0",
                      "medium_value = 0", "hard_value = 0", "custom_value = 0",
                      "default_value = 0"):
            self.assertIn(token, block.group(1))
        self.assertIn("V233L_CONSTRUCT <- 0", source("globals_pre.nut"))
        self.assertEqual(source("settings.nut").count('GetSetting("v233l_constructibilite")'), 1)

    def test_single_counterfactual_only_after_primary_success_and_double_failure(self):
        finish = function("OpexCompleteRailRouteAfterSearch", "builder_rail.nut")
        self.assertLess(finish.index("if (search.path == false"),
                        finish.index("OpexV233LMonoCounterfactual"))
        self.assertIn("if (OpexV233LIs(candidate) && plan.doubleTrack != 1)", finish)
        self.assertIn("V233L_CONSTRUCT > 0", finish)
        self.assertIn('plan.reason = "NOPLAN2";', finish)
        self.assertLess(finish.index('plan.reason = "NOPLAN2";'),
                        finish.index("plan.ok = true;"))

    def test_shadow_is_read_only_and_on_requires_one_train_positive_net_profit(self):
        quote = function("OpexV233LMonoCounterfactual", "v233_long_good.nut")
        self.assertIn("local mono = null", quote)
        self.assertIn("mono = clone candidate", quote)
        self.assertIn("model.trains != 1 || model.profitAnnual <= 0", quote)
        self.assertIn("OpexQuoteRailCapital(catalog, mono, plan, failure)", quote)
        self.assertIn("OpexApplyRailActualCapital(mono, quoted)", quote)
        self.assertIn('reason = "NEGATIVE_AFTER_QUOTE"', quote)
        self.assertIn('reason = "CASH"', quote)
        self.assertIn('reason = "NOSLOT"', quote)
        self.assertLess(quote.index("if (reason != \"OK\" || V233L_CONSTRUCT != 2) return false;"),
                        quote.index("OpexApplyRailEconomics(candidate, model)"))
        self.assertIn("plan.v233MonoVerified <- true", quote)
        self.assertIn("local testMode = AITestMode()", function("OpexSimulateRailInfraCost", "builder_rail.nut"))

    def test_monorail_economics_does_not_steal_double_track_default(self):
        econ = function("OpexLineEconomics", "economy.nut")
        self.assertIn("v233Single = false", econ)
        self.assertIn("longModel && v233Single && V233L_CONSTRUCT > 0", econ)
        self.assertIn("longModel && !monoLong", econ)
        self.assertIn("monoLong ? 1 :", econ)
        self.assertIn("if (longModel && !monoLong) calibrationOffered /= 2.0", econ)
        self.assertIn("if (longModel && offered > 0) paidDays", econ)
        quote = function("OpexV233LMonoCounterfactual", "v233_long_good.nut")
        self.assertIn("OpexV163CandidateSecondary(candidate), true, true", quote)

    def test_executor_requotes_and_rolls_back_on_failure(self):
        allow = function("OpexV233LMonoAllowed", "v233_long_good.nut")
        self.assertIn("V233L_CONSTRUCT == 2", allow)
        self.assertIn("plan.doubleTrack == 0 && candidate.trains == 1", allow)
        recheck = function("OpexV233LRecheck", "v233_long_good.nut")
        self.assertIn("!OpexV233LMonoAllowed(candidate, plan)", recheck)
        execute = function("OpexV190ExecuteRailPlan", "builder_rail.nut")
        self.assertLess(execute.index("OpexV233LRecheck"), execute.index("OpexQuoteRailCapital"))
        self.assertIn("OpexV233LMonoAllowed(candidate, plan) ? 1 : 2", execute)
        self.assertIn("OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles)", execute)
        self.assertIn("&& !OpexV233LMonoAllowed(candidate, plan)", execute)
        self.assertIn('phase=actual outcome=build_ok track=single', execute)


if __name__ == "__main__":
    unittest.main()
