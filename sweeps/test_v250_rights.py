"""V250 : contrats statiques des droits exclusifs.

Defaut 0 aux quatre niveaux et dans default_value. A 0 la tache ne touche
aucune API. Le mode 1 reste coupe en facile et moyen. Le mode 2 ne l'est pas.
Le journal est garde par DECISION_LOG sur la meme ligne qu'OpexDecide.
Aucune cle de sauvegarde n'est ecrite quand le reglage est a 0.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV250Rights(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v250.nut"]
        cls.dispatch = _body(cls.task, "function OpexAI::_dispatchV250Rights(task, year)")
        cls.measure = _body(cls.task, "function OpexV250MeasureRightsCost(townId)")
        cls.buy = _body(cls.task, "function OpexV250BuyRights(ai, townId, mode, pop, reserve, mark = 1)")
        cls.slots = _body(cls.task, "function OpexV250YearSlots(cash, reserve, cost)")
        cls.normal = _body(cls.task, "function OpexV250RunNormal(ai)")
        cls.test = _body(cls.task, "function OpexV250RunTest(ai, date, allRival = false)")
        cls.save = _body(cls.sources["persist.nut"], "function OpexSaveV250(saveObj, ai)")

    def test_setting_default_zero_at_four_levels(self):
        block = re.search(
            r'name = "v250_rights",(.*?)\}\);', self.sources["info.nut"], re.S)
        self.assertIsNotNone(block)
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 4", body)
        self.assertIn("flags = 0", body)
        self.assertNotIn("AICONFIG_BOOLEAN", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertRegex(body, level + r" = 0\b")
        self.assertIn("Easy and medium keep mode 1 off", body)
        self.assertIn("not filtered by difficulty", body)
        self.assertIn("fair_play", body)
        self.assertNotIn('name = "fair_play"', self.sources["info.nut"])
        self.assertIn("V250_RIGHTS <- 0;", self.sources["globals_pre.nut"])
        self.assertIn("V250_CASH_STOP <- true;", self.sources["globals_pre.nut"])

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v250_rights")'))
                 for name, text in self.sources.items()]
        self.assertEqual(sum(count for _, count in reads), 1)
        self.assertIn('GetSetting("v250_rights")', self.sources["settings.nut"])

    def test_zero_cost_guard_and_queue(self):
        self.assertTrue(self.dispatch)
        guard = "if (V250_RIGHTS == 0) return false;"
        self.assertIn(guard, self.dispatch)
        guard_at = self.dispatch.index(guard)
        level = 'if (!OpexLevelAllows("v250_rights")) return false;'
        self.assertIn(level, self.dispatch)
        self.assertLess(guard_at, self.dispatch.index(level))
        for api in ("AIDate", "AICompany", "AITown", "AIStation", "AIAccounting",
                    "AITestMode", "OpexDecide", "AITile", "OpexAir"):
            found = self.dispatch.find(api)
            if found >= 0:
                self.assertGreater(found, self.dispatch.index(level), api)
        start = self.sources["main.nut"]
        statue = 'this._taskQueue.append({ name = "v249_statue", dueCycle = 0, enabled = V249_STATUE });'
        rights = 'this._taskQueue.append({ name = "v250_rights", dueCycle = 0, enabled = V250_RIGHTS > 0 });'
        self.assertLess(start.index(statue), start.index(rights))
        self.assertIn('task.name == "v250_rights"', self.sources["scheduler.nut"])
        self.assertIn("this._dispatchV250Rights(task, year)", self.sources["scheduler.nut"])
        hook = 'if (V250_RIGHTS == 1 && c75StopReason == "cash") ::V250_CASH_STOP = true;'
        self.assertEqual(self.sources["task_projects.nut"].count(hook), 1)

    def test_mode1_rich_and_difficulty_filter(self):
        self.assertIn("local cashStop = V250_CASH_STOP;", self.normal)
        self.assertLess(self.normal.index("::V250_CASH_STOP = false;"),
                        self.normal.index("OpexV250Contested()"))
        self.assertLess(self.normal.index("AICompany.GetLoanAmount()"),
                        self.normal.index("OpexV250Contested()"))
        self.assertIn("OpexCashReserve()", self.normal)
        self.assertIn("if (mode == 1) need += OpexV249MaxListedCapital(ai._projects);", self.buy)
        self.assertIn("cash - cost < need", self.buy)
        self.assertNotIn("OPEX_DIFFICULTY", self.test)
        self.assertNotIn("V250_CASH_STOP", self.test)
        self.assertEqual(self.normal.count("OpexV250BuyRights"), 1)

    def test_mode2_slot_signal_and_derived_cap(self):
        self.assertLess(self.test.index("OpexV250Watch(ai, date, ownCounts);"),
                        self.test.index("if (!OpexAirC83SlotSignalEnabled()) return true;"))
        self.assertIn("OpexAirOwnSlotTownCounts()", self.test)
        self.assertIn("AITown.GetAllowedNoise(townId) != 0", self.test)
        self.assertIn("if (own != 0) continue;", self.test)
        self.assertIn("OpexV250YearSlots(cash, reserve, cost)", self.task)
        self.assertIn("local spendable = cash - reserve;", self.slots)
        self.assertIn("(spendable / cost).tointeger()", self.slots)
        self.assertNotRegex(self.slots, r"\b[1-9]\d*\b")
        self.assertNotIn("BuildAirport", self.task)
        self.assertNotIn("AIAirport", self.task)
        self.assertIn("noise >= 1", self.task)

    def test_mode3_all_rival_towns(self):
        self.assertIn("local rival = 2 - noise - own;", self.test)
        self.assertIn("if (rival <= 0) continue;", self.test)
        self.assertIn("foreach (item in others) ordered.append(item);", self.test)
        self.assertIn("OpexV250RunTest(this, date, V250_RIGHTS >= 3)", self.dispatch)
        self.assertIn("if (mark == 1) OpexV250WatchTown(ai, townId, date, ownCounts);", self.task)

    def test_measure_shield_and_journal(self):
        self.assertLess(self.measure.index("local test = AITestMode();"),
                        self.measure.index("AITown.PerformTownAction"))
        self.assertLess(self.measure.index("local account = AIAccounting();"),
                        self.measure.index("local test = AITestMode();"))
        self.assertLess(self.buy.index("OpexV250MeasureRightsCost(townId)"),
                        self.buy.index("local bought = AITown.PerformTownAction"))
        for line in self.task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, line)
        self.assertIn(
            'OpexDecide("V250_RIGHTS", "town=" + townId + " cost=" + cost + " mode=" + mode + " pop=" + pop + " noise=" + noise)',
            self.buy)
        self.assertIn(
            'OpexDecide("V250_WATCH", "town=" + townId + " noise=" + noise + " own=" + own)',
            self.task)
        self.assertIn(
            'OpexDecide("V250_SLOT_FREED", "town=" + townId + " date=" + date)',
            self.task)

    def test_no_saved_state_at_default(self):
        self.assertTrue(self.save)
        self.assertLess(self.save.index("if (V250_RIGHTS == 0 || saveObj == null || ai == null) return;"),
                        self.save.index("v250Targets"))
        persist = self.sources["persist.nut"]
        self.assertEqual(persist.count("OpexSaveV250("), 3)
        self.assertIn("if (V250_RIGHTS != 0)", persist)
        self.assertNotIn('GetSetting("v250_rights")', persist)
        self.assertIn("_v250Month = -1;", self.sources["main.nut"])
        self.assertNotIn("_v250Month", persist)



class TestV250Level3AndTargeted(unittest.TestCase):
    """18/10 : toute la V250 est reservee au niveau 3 ; mode 4 cible."""

    @classmethod
    def setUpClass(cls):
        cls.settings = (AI / "settings.nut").read_text(encoding="utf-8")
        cls.task = (AI / "task_v250.nut").read_text(encoding="utf-8")

    def test_level_three_only(self):
        gate = 'if (!OpexLevelAllows("v250_rights")) rights = 0;'
        self.assertIn(gate, self.settings)
        self.assertLess(self.settings.index("OPEX_DIFFICULTY = OpexResolveDifficulty();"),
                        self.settings.index(gate))
        self.assertLess(self.settings.index(gate), self.settings.index("V250_RIGHTS = rights;"))

    def test_mode4_targets(self):
        order = _body(self.task, "function OpexV250TargetedOrder()")
        self.assertIn("AITown.GetRating(townId, c) != AITown.TOWN_RATING_NONE", order)
        self.assertIn("AITown.GetRating(townId, self) == AITown.TOWN_RATING_NONE", order)
        self.assertIn("pops[pops.len() * 3 / 4]", order)
        self.assertIn("else if (pop >= bigPop)", order)
        self.assertIn("if (V250_RIGHTS == 4) return OpexV250BuyOrdered(ai, date, OpexV250TargetedOrder(), ownCounts, 4);",
                      self.task)
        buy = _body(self.task, "function OpexV250BuyOrdered(ai, date, ordered, ownCounts, mode)")
        self.assertIn("if (mode == 4 && ai._v250Targets != null)", buy)

if __name__ == "__main__":
    unittest.main()
