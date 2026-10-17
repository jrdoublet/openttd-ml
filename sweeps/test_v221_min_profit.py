"""V221 : contrats statiques du profit minimal des vehicules de plus de 2 ans.

Reglage entier en livres, 0 = inerte sur les quatre difficultes. Au defaut, le
scheduler ne fait qu'un test. La passe, au plus une fois par mois, lit
GetProfitLastYear (montant de la note) et ne touche pas GetProfitThisYear.
Aucun etat persistant nouveau : le mois est une globale remise a -1 au chargement.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_setting_specs  # noqa: E402


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


class TestV221Setting(unittest.TestCase):
    def test_setting_inert_on_four_difficulties(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v221_min_profit"]
        self.assertEqual(spec["default"], 0)
        self.assertFalse(spec["boolean"])
        self.assertEqual(spec["min_value"], 0)
        self.assertEqual(spec["max_value"], 1000000)
        self.assertEqual(spec["step_size"], 1)
        block = _read("info.nut").split('name = "v221_min_profit"', 1)[1].split("});", 1)[0]
        self.assertNotIn("}", block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, level + r" = 0\b")
        self.assertNotIn("AICONFIG_BOOLEAN", block)

    def test_global_and_single_clamped_read(self):
        self.assertIn("V221_MIN_PROFIT <- 0;", _read("globals_pre.nut"))
        self.assertIn("V221_LAST_MONTH <- -1;", _read("globals_pre.nut"))
        sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        reads = [(name, text.count('GetSetting("v221_min_profit")')) for name, text in sources.items()]
        self.assertEqual([(n, c) for n, c in reads if c], [("settings.nut", 1)])
        body = _function_body(_read("settings.nut"), "OpexLoadSettings")
        self.assertIn(
            "V221_MIN_PROFIT = (v221MinProfit != null && v221MinProfit > 0"
            " && v221MinProfit <= 1000000) ? v221MinProfit : 0;",
            body,
        )
        self.assertIn("V221_LAST_MONTH = -1;", body)

    def test_no_new_persisted_state(self):
        persist = _read("persist.nut")
        self.assertNotIn("V221", persist)
        self.assertNotIn("v221", persist)


class TestV221Hook(unittest.TestCase):
    def test_single_guard_after_v217(self):
        scheduler = _read("scheduler.nut")
        hook = "if (V221_MIN_PROFIT > 0) this._v221MinProfitCull();"
        self.assertEqual(scheduler.count(hook), 1)
        self.assertEqual(scheduler.count("V221_MIN_PROFIT"), 1)
        self.assertLess(
            scheduler.index("if (V217_RAIL_REFILL > 0) this._v217RailRefill();"),
            scheduler.index(hook),
        )
        main = _read("main.nut")
        self.assertIn("function _v221MinProfitCull();", main)
        self.assertIn("function _v221RetireUnit(vehicle, line);", main)
        self.assertIn("function _v221Renew(vehicle, line, reserve);", main)
        self.assertLess(main.index('require("v221_min_profit.nut");'), main.index('require("scheduler.nut");'))
        calls = [
            (name, line.strip())
            for name, text in ((p.name, p.read_text(encoding="utf-8")) for p in AI.glob("*.nut"))
            for line in text.splitlines()
            if "_v221MinProfitCull(" in line and "function" not in line
        ]
        self.assertEqual(calls, [("scheduler.nut", hook)])


class TestV221Pass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = _read("v221_min_profit.nut")
        cls.cull = _function_body(cls.src, "OpexAI::_v221MinProfitCull")
        cls.retire = _function_body(cls.src, "OpexAI::_v221RetireUnit")
        cls.renew = _function_body(cls.src, "OpexAI::_v221Renew")
        cls.young = _function_body(cls.src, "OpexV221LineYoung")
        cls.log = _function_body(cls.src, "OpexV221Log")

    def test_last_year_profit_and_age_margin(self):
        self.assertIn("V221_AGE_MIN <- 700;", self.src)
        self.assertIn("V221_MAX_ACTIONS <- 4;", self.src)
        self.assertIn("if (V221_MIN_PROFIT <= 0) return;", self.cull)
        self.assertLess(self.cull.index("if (this._lines == null) return;"), self.cull.index("V221_LAST_MONTH = ym;"))
        self.assertLess(self.cull.index("if (V221_LAST_MONTH == ym) return;"), self.cull.index("V221_LAST_MONTH = ym;"))
        self.assertIn("if (age < V221_AGE_MIN) continue;", self.cull)
        self.assertIn("local profit = AIVehicle.GetProfitLastYear(vehicle);", self.cull)
        self.assertIn("if (profit >= V221_MIN_PROFIT) continue;", self.cull)
        self.assertNotIn("AIVehicle.GetProfitThisYear", self.src)
        self.assertEqual(self.src.count("AIVehicle.GetProfitLastYear"), 1)
        self.assertIn("if (actions >= V221_MAX_ACTIONS) break;", self.cull)
        self.assertEqual(self.cull.count("actions++"), 4)
        self.assertIn("local reserve = OpexCashReserve();", self.cull)

    def test_retire_matches_existing_mechanic_once(self):
        self.assertLess(
            self.retire.index("vehicle in this._vehiclesToRetire"),
            self.retire.index("line.vehCount--"),
        )
        self.assertIn("if (line != null && OpexAirLineReequipPending(line)) return false;", self.retire)
        self.assertIn("if (!AIVehicle.SendVehicleToDepot(vehicle)) return false;", self.retire)
        self.assertIn("this._vehiclesToRetire.rawset(vehicle,", self.retire)
        self.assertIn('if ("vehCount" in line && line.vehCount > 0) line.vehCount--;', self.retire)
        self.assertIn('if ("trains" in line && line.trains > 1) line.trains--;', self.retire)
        self.assertIn('if ("predTrains" in line && line.predTrains > 1) line.predTrains--;', self.retire)
        self.assertIn("if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire)) continue;", self.cull)
        self.assertIn("if (have > 1) {", self.cull)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "retire", "multi")', self.cull)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "retire", "orphan")', self.cull)
        handler = _function_body(_read("event_handlers.nut"), "OpexAI::_onVehicleUnprofitable")
        self.assertIn("streak >= UNPROFITABLE_STREAK_THRESHOLD", handler)
        self.assertNotIn("V221", handler)

    def test_single_vehicle_renew_or_scrap(self):
        self.assertIn("if (row.profit <= 0) {", self.cull)
        self.assertLess(self.cull.index("OpexV221HasPendingRetire(this, line)"), self.cull.index('_triggerScrapLine(line, "v221")'))
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "retire_pending")', self.cull)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "retire", "line_loss")', self.cull)
        self.assertIn("AIVehicle.CloneVehicle(depot, vehicle, true)", self.renew)
        self.assertIn("if (cash < price * 2 + reserve) return \"cash\";", self.renew)
        self.assertNotIn("vehCount--", self.renew)
        self.assertNotIn("trains--", self.renew)
        self.assertNotIn("predTrains--", self.renew)
        self.assertNotIn("BuildVehicle", self.src)
        self.assertNotIn("ShareOrders", self.src)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "renew", "ok")', self.cull)
        for reason in ("cash", "no_depot", "no_price", "build_fail", "start", "depot_refused", "v92"):
            self.assertIn('return "' + reason + '"', self.renew)

    def test_temporary_delivery_skips_and_journal(self):
        self.assertIn("AIVehicle.IsInDepot(vehicle)", self.cull)
        self.assertIn("AIVehicle.IsStoppedInDepot(vehicle)", self.cull)
        self.assertIn("AIOrder.IsGotoDepotOrder(vehicle, AIOrder.ORDER_CURRENT)", self.cull)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "depot")', self.cull)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "v92")', self.cull)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "line_young")', self.cull)
        self.assertIn('OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "crashed")', self.cull)
        self.assertNotIn("VS_BROKEN", self.src)
        self.assertIn("(date - built) < 365", self.young)
        self.assertIn("(AIDate.GetYear(date) - line.year) < 1", self.young)
        self.assertIn("if (!DECISION_LOG) return;", self.log)
        self.assertIn('OpexDecide("V221_CULL"', self.log)
        for field in ("vehicle=", "mode=", "line=", "age=", "profit=", "action=", "reason="):
            self.assertIn(field, self.log)

    def test_no_reserved_identifiers(self):
        self.assertIsNone(re.search(r"\b(clone|base|parent|resume)\b", self.src))


if __name__ == "__main__":
    unittest.main()
