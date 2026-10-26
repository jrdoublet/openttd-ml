"""P1 long freight: independent contract checks, no OpenTTD or A* launched.

These checks protect the OFF/shadow/no-second-A* controls. They cannot prove
that a physical rail line is buildable or that P1 improves annual profit.
"""

from pathlib import Path
import re
import unittest

from n75_mc_legacy import historical_bytes


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
PREREG = Path(__file__).resolve().parents[1] / "docs" / "p1_rail_long_value_prereg_20261026.md"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function(text, name):
    start = text.index("function " + name + "(")
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if not depth:
                return text[start:index + 1]
    raise AssertionError(f"missing closing brace for {name}")


def proxy_choice(pairs, ordinary_max, cap=4096):
    """Reference shortlist: stable ties, hard exclusion and finite scan."""
    best = None
    for src, dst, cargo, distance, monthly in pairs[:cap]:
        if not monthly or distance < 160 or distance > 300 or distance <= ordinary_max:
            continue
        key = (monthly * distance, -src, -dst, -cargo)
        if best is None or key > best[0]:
            best = key, (src, dst, cargo)
    return None if best is None else best[1]


class TestP1LongRank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = source("candidates.nut")
        cls.prep = source("rail_prep_c121.nut")
        cls.builder = source("builder_rail.nut")
        cls.task = source("task_rail.nut")

    def test_setting_four_profiles_and_off_default(self):
        info = source("info.nut")
        setting = re.search(r'AddSetting\(\{ name = "rail_long_value_rank",.*?\}\);', info, re.S)
        self.assertIsNotNone(setting)
        self.assertIn("min_value = 0, max_value = 2", setting.group())
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(), rf"{level}_value = 0\b")
        self.assertIn("P1_RAIL_LONG_VALUE_RANK <- 0;", source("globals_pre.nut"))
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("rail_long_value_rank")'), 1)
        self.assertIn("(p1LongRank == 1 || p1LongRank == 2)", settings)

    def test_historical_producers_and_bytes_stay_frozen(self):
        # P1 may extend the C121 catalog, but the historic OFF decision source
        # and the PO01D byte pins remain those of the control arm.
        for filename in ("info.nut", "settings.nut", "candidates.nut", "builder_rail.nut"):
            frozen = historical_bytes(filename, (AI / filename).read_bytes())
            self.assertNotIn(b"P1_LONG", frozen)
        make = function(self.candidates, "OpexMakeCandidate")
        self.assertNotIn("p1Long", make)
        self.assertNotIn("P1_RAIL_LONG_VALUE_RANK", make)

    def test_proxy_window_tie_and_scan_budget(self):
        fixture = [
            (1, 12, 3, 160, 10),    # admissible when baseline railMax <160
            (2, 13, 3, 159, 200),   # below window
            (3, 14, 3, 301, 200),   # above window
            (4, 15, 3, 250, 0),     # empty source
            (5, 16, 3, 200, 8),     # ties 10*160, later src loses
            (0, 17, 3, 200, 8),     # ties, lowest src wins
            (0, 16, 3, 200, 8),     # lowest destination wins
        ]
        self.assertEqual(proxy_choice(fixture, 140), (0, 16, 3))
        self.assertIsNone(proxy_choice(fixture, 300))
        self.assertEqual(proxy_choice(fixture[:1] + [(7, 9, 3, 270, 100)], 140, cap=1),
                         (1, 12, 3))
        offer = function(self.candidates, "OpexP1LongOffer")
        self.assertIn("state.scanned >= 4096", offer)
        self.assertIn("state.scanned++", offer)
        self.assertIn("dist < 160 || dist > 300", offer)
        self.assertIn("monthly.tofloat() * dist", offer)

    def test_shadow_does_not_quote_mutate_catalog_or_search(self):
        evaluate = function(self.candidates, "OpexP1LongEvaluate")
        self.assertIn("P1_RAIL_LONG_VALUE_RANK != 2", evaluate)
        self.assertIn("local localCatalog = clone catalog", evaluate)
        self.assertIn("localCatalog.bounds = clone OpexCatalogBounds(catalog)", evaluate)
        self.assertIn("localCatalog.bounds.railMax = pair.distance", evaluate)
        self.assertNotIn("catalog.bounds.railMax =", evaluate)
        self.assertEqual(evaluate.count("OpexMakeCandidate("), 1)
        self.assertNotIn("OpexCreateRailPathfinder", evaluate)
        self.assertIn("candidate.trains != 1", evaluate)
        build = function(self.candidates, "OpexBuildCandidates")
        self.assertIn("if (P1_RAIL_LONG_VALUE_RANK == 2)", build)
        self.assertLess(build.index("OpexFreightCandidates("), build.index("OpexP1LongEvaluate("))
        self.assertNotIn("p1LongState.candidate", build[build.index("local all = []"):build.index("local opsFreight =")])

    def test_one_c80_slot_exclusion_and_real_path_revalidation(self):
        maybe = function(self.prep, "OpexAI::_c121RailPrepMaybeCatalog")
        self.assertIn("if (V276_CAND_SLICES > 0)", maybe)
        self.assertLess(maybe.index("if (V276_CAND_SLICES > 0)"), maybe.index("local p1State"))
        self.assertIn("!V269_RELAXED", maybe)
        self.assertIn("ranked.insert(0, p1State.candidate)", maybe)
        self.assertNotIn("_startRailStockSearch", maybe)
        start = function(self.prep, "OpexAI::_tryStartC121RailPrepSearch")
        self.assertIn("if (this._railSearch != null) return false;", start)
        self.assertEqual(start.count("this._startRailStockSearch(candidate)"), 1)
        after = function(self.builder, "OpexCompleteRailRouteAfterSearch")
        self.assertLess(after.index("if ((\"p1Long\" in candidate)"),
                        after.index("OpexTryDoubleTrack("))
        for token in ("candidate.trains != 1", "OpexV190Active()", 'plan.reason = "P1FLEET"',
                      'plan.reason = "P1VALUE"'):
            self.assertIn(token, after)

    def test_trace_and_save_load_transience(self):
        stock = function(self.task, "OpexAI::_handleRailStockSearchCompleted")
        self.assertIn('OpexDecide("P1_LONG_MARGIN"', stock)
        self.assertIn("OpexProjectFinanceCapital(alt) > available", stock)
        self.assertIn("OpexCalibratedProfit(alt)", stock)
        self.assertIn("this._railReadyStock[pairKey] <-", stock)
        chosen = function(self.task, "OpexAI::_tryBuildRailProject")
        self.assertIn('OpexDecide("PROJECT_CHOSEN"', chosen)
        self.assertIn("c121PrepPlan && (\"p1Long\" in candidate)", chosen)
        self.assertIn("this._revalidateRailStockPlan(candidate, candidate.railPlan)", chosen)
        self.assertIn('reason = "p1_revalidate_" + reval.reason', chosen)
        self.assertLess(chosen.index('reason = "p1_revalidate_" + reval.reason'),
                        chosen.index('local start = this._startRailSearch('))
        reval = function(self.task, "OpexAI::_revalidateRailStockPlan")
        self.assertIn('!V131_RAIL_REPAIR || (("p1Long" in candidate) && candidate.p1Long)', reval)
        persist = source("persist.nut")
        for mark in ("this._railReadyStock = {};", "this._railStockCooldown = {};",
                     "this._c121RailPrepCandidates = null;", "this._railSearch = null;"):
            self.assertIn(mark, persist)
        self.assertNotIn("p1Long", persist)

    def test_preregistered_exposure_is_not_a_stock_deposit(self):
        prereg = PREREG.read_text(encoding="utf-8")
        for token in ("au moins deux graines distinctes", "RAIL_BUILD", "P1_LONG_MARGIN",
                      "4 %", "40 graines × 5 ans", "20 graines × 10 ans"):
            self.assertIn(token, prereg)


if __name__ == "__main__":
    unittest.main()
