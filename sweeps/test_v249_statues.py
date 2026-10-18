"""V249 : contrats statiques des statues de ville.

Reglage v249_statue (0 = inactif par defaut, 1 = profit brut de lignes historique,
2 = gain annuel attendu et test de remboursement sur la duree de vie des vehicules).
A 0 la tache ne touche aucune API de jeu. Un passage pose au plus une statue.
Le journal est garde par DECISION_LOG. Aucun etat n'est sauvegarde.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV249Statues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v249.nut"]
        cls.dispatch = _body(cls.task, "function OpexAI::_dispatchV249Statue(task, year)")
        cls.ratings = _body(cls.task, "function OpexAI::_v249LogStatueRatings()")
        cls.measure = _body(cls.task, "function OpexV249MeasureStatueCost(townId)")

    def test_setting_declared_default_zero(self):
        block = re.search(
            r'name = "v249_statue",(.*?)\}\);', self.sources["info.nut"], re.S)
        self.assertIsNotNone(block)
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 2", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, level + r" = 0\b")
        self.assertIn("V249_STATUE <- 0;", self.sources["globals_pre.nut"])
        self.assertIn("V249_CASH_STOP <- true;", self.sources["globals_pre.nut"])
        joined = "".join(self.sources.values())
        self.assertNotIn("v249_statue_cash", joined)
        self.assertNotIn("V249_STATUE_CASH", joined)

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v249_statue")'))
                 for name, text in self.sources.items()]
        self.assertEqual(sum(count for _, count in reads), 1)
        self.assertIn('AIController.GetSetting("v249_statue")', self.sources["settings.nut"])
        self.assertIn('V249_STATUE = (v249 != null && v249 >= 0 && v249 <= 2) ? v249 : 0;',
                      self.sources["settings.nut"])

    def test_zero_cost_guard(self):
        self.assertTrue(self.dispatch)
        guard = "if (!V249_STATUE) return false;"
        self.assertIn(guard, self.dispatch)
        guard_at = self.dispatch.index(guard)
        for api in ("AIDate", "AICompany", "AITown", "AIStation", "AIVehicle",
                    "AIAccounting", "AITestMode", "OpexDecide", "V249_CASH_STOP"):
            found = self.dispatch.find(api)
            if found >= 0:
                self.assertGreater(found, guard_at, api)
        start = self.sources["main.nut"]
        appended = 'this._taskQueue.append({ name = "v249_statue", dueCycle = 0, enabled = V249_STATUE });'
        self.assertIn(appended, start)
        self.assertLess(start.index("OpexV147ExtendQueue(this);"), start.index(appended))
        hook = 'if (V249_STATUE && c75StopReason == "cash") ::V249_CASH_STOP = true;'
        self.assertEqual(self.sources["task_projects.nut"].count(hook), 1)

    def test_rich_without_fixed_amount(self):
        loan = self.dispatch.index('reason=loan')
        stop = self.dispatch.index('reason=cash_stop')
        cost = self.dispatch.index('OpexV249MeasureStatueCost(bestTown)')
        self.assertLess(loan, cost)
        self.assertLess(stop, cost)
        self.assertLess(self.dispatch.index("::V249_CASH_STOP = false;"), stop)
        self.assertIn("local threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects);",
                      self.dispatch)
        self.assertIn("cash - cost < threshold", self.dispatch)
        self.assertNotRegex(self.task, r"\b\d{4,}\b")

    def test_at_most_one_statue_per_pass(self):
        self.assertEqual(self.dispatch.count("AITown.PerformTownAction"), 1)
        call = self.dispatch.index("AITown.PerformTownAction")
        self.assertNotIn("foreach", self.dispatch[call:])
        self.assertNotIn("while", self.dispatch[call:])
        self.assertLess(self.dispatch.rfind("return true;"), len(self.dispatch))
        self.assertIn("local built = AITown.PerformTownAction", self.dispatch)
        self.assertIn("if (!built)", self.dispatch)
        self.assertEqual(self.measure.count("AITown.PerformTownAction"), 1)
        self.assertLess(self.measure.index("local test = AITestMode();"),
                        self.measure.index("AITown.PerformTownAction"))
        self.assertIn("if (this._v249StatueMonth == ym) return false;", self.dispatch)
        self.assertIn('this._taskQueue.append({ name = "v249_statue"', self.sources["main.nut"])
        self.assertIn('task.name == "v249_statue"', self.sources["scheduler.nut"])

    def test_journal_guarded_and_aggregated(self):
        for line in self.task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, line)
        # Mode 1 exact log line preserved
        self.assertIn(
            'OpexDecide("V249_STATUE", "town=" + bestTown + " cost=" + cost + " cash=" + cash'
            ' + " threshold=" + threshold + " lines=" + bestLines + " profit=" + bestProfit)',
            self.dispatch)
        # Mode 2 enriched log line
        self.assertIn(
            'OpexDecide("V249_STATUE", "town=" + bestTown + " gain=" + bestGain.tointeger() + " cost=" + cost + " payback=" + pbStr + " stations=" + bestStations + " rating_before=" + bestAvgRating + " cash=" + cash + " threshold=" + threshold)',
            self.dispatch)
        # Skips
        self.assertIn('OpexDecide("V249_SKIP", "reason=cash_stop")', self.dispatch)
        self.assertIn('OpexDecide("V249_SKIP", "reason=payback', self.dispatch)
        self.assertIn(
            '"reason=no_town statue=" + nStatue + " unavailable=" + nUnavail',
            self.dispatch)
        # Monthly rating probe
        self.assertIn('OpexDecide("V249_RATING", "town=" + townId + " rating=" + avgRating + " stations=" + info.stations.len())', self.ratings)

    def test_no_saved_state(self):
        persist = self.sources["persist.nut"]
        self.assertNotIn("v249", persist.lower())
        self.assertNotIn("_v249StatueMonth", persist)
        self.assertNotIn("_v249StatueTowns", persist)
        self.assertNotIn("V249_CASH_STOP", persist)
        self.assertIn("_v249StatueMonth = -1;", self.sources["main.nut"])
        self.assertIn("this._v249StatueTowns = [];", self.sources["main.nut"])

    def test_mode2_gain_calculation(self):
        # Target rating +26 capped at 255 from station_cmd.cpp
        self.assertIn("local targetNote = note + 26;", self.dispatch)
        self.assertIn("if (targetNote > 255) targetNote = 255;", self.dispatch)
        self.assertIn("local relGain = (targetNote - note).tofloat() / note.tofloat();", self.dispatch)
        # Rating percent to byte conversion
        self.assertIn("OpexC121RatingPercentToByteMid(pct)", self.dispatch)
        # Weighted by line profit
        self.assertIn("local lineProfit = OpexV249LineProfit(line);", self.dispatch)
        # 50% split for intra-town lines
        self.assertIn("sameTown ? (lineProfit.tofloat() * 0.5) : lineProfit.tofloat()", self.dispatch)

    def test_mode2_payback_vehicle_life(self):
        # Uses vehicle remaining service life (GetMaxAge - GetAge) / 365
        self.assertIn("AIVehicle.GetMaxAge(v) - AIVehicle.GetAge(v)", self.dispatch)
        self.assertIn("/ 365.0", self.dispatch)
        # Payback comparison: bestGain * vehRemainingYears >= cost
        self.assertIn("bestGain * vehRemainingYears < cost.tofloat()", self.dispatch)

    def test_mode2_monthly_rating_tracking(self):
        self.assertTrue(self.ratings)
        # Called only in mode 2 and guarded by DECISION_LOG
        self.assertIn("if (V249_STATUE == 2 && DECISION_LOG && this._v249StatueTowns != null", self.dispatch)
        # Strictly O(statue towns)
        self.assertIn("foreach (townId in this._v249StatueTowns)", self.ratings)
        self.assertIn("if (!(townId in tracked)) continue;", self.ratings)


if __name__ == "__main__":
    unittest.main()
