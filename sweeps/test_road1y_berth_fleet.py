"""Contrats du masque road1y_berth_fleet (defaut 0, route seule).

Bit 0 : reserve 50 000 £, declencheur cap*capacity, les deux bouts, want historique.
Bit 1 : extra-quai bus a cout + max(20000, capital du vivier), attente = capacity,
        bout le plus court pour faire monter min(quais).
Bit 2 : si min(quais) >= 2, +1 bus/mois si min(attente) > 10 et moins de 2 bus
        a l'arret, plafond ROAD1Y_FLEET * min, caisse >= prix + 20000.
Ces tests ne compilent pas le Squirrel.
"""
from pathlib import Path
import re
import unittest

from test_v261_forum_behaviours import body, source

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


class TestRoad1yBerthFleet(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info_src = source("info.nut")
        self.assertEqual(info_src.count('name = "road1y_berth_fleet"'), 1)
        setting_block = info_src.split('name = "road1y_berth_fleet",')[1].split("});")[0]
        self.assertIn("min_value = 0", setting_block)
        self.assertIn("max_value = 3", setting_block)
        for diff in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{diff}_value = 0", setting_block)
        self.assertIn("flags = 0", setting_block)

    def test_global_and_road_only_gate(self):
        self.assertIn("ROAD1Y_BERTH_FLEET <- 0;", source("globals_pre.nut"))
        settings_src = source("settings.nut")
        self.assertEqual(settings_src.count('GetSetting("road1y_berth_fleet")'), 2)
        for path in AI.glob("*.nut"):
            if path.name == "settings.nut":
                continue
            self.assertNotIn('GetSetting("road1y_berth_fleet")', path.read_text(encoding="utf-8"))
        load_fn = body("settings.nut", "OpexLoadSettings")
        self.assertIn(
            'ROAD1Y_BERTH_FLEET = AIController.GetSetting("road1y_berth_fleet");',
            load_fn,
        )
        self.assertIn(
            "if (ROAD1Y_BERTH_FLEET < 0 || ROAD1Y_BERTH_FLEET > 3) ROAD1Y_BERTH_FLEET = 0;",
            load_fn,
        )
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_BERTH_FLEET = 0;", load_fn)
        bus_fn = body("settings.nut", "OpexLoadBusDistrictSettings")
        self.assertIn(
            'ROAD1Y_BERTH_FLEET = AIController.GetSetting("road1y_berth_fleet");',
            bus_fn,
        )
        self.assertIn(
            "if (ROAD1Y_BERTH_FLEET < 0 || ROAD1Y_BERTH_FLEET > 3) ROAD1Y_BERTH_FLEET = 0;",
            bus_fn,
        )
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_BERTH_FLEET = 0;", bus_fn)

    def test_bit0_keeps_historical_cash_and_unlock_line(self):
        code = body("bus_districts.nut", "OpexRoad1yBuildExtraStop")
        self.assertIn("berthReserve = -1", source("bus_districts.nut").split(
            "function OpexRoad1yBuildExtraStop")[1].split("{")[0])
        self.assertIn("local openingReserve = berthReserve >= 0 ? berthReserve : 50000;", code)
        self.assertIn("price + openingReserve", code)
        self.assertIn("local cashReserve = (ROAD1Y_FLEET_UNLOCK & 1) != 0 ? 5000 : 50000;", code)
        self.assertLess(
            code.index("local cashReserve = (ROAD1Y_FLEET_UNLOCK & 1) != 0 ? 5000 : 50000;"),
            code.index("if (berthReserve >= 0) cashReserve = berthReserve;"),
        )
        self.assertIn("< cost + cashReserve", code)

    def test_bit1_reserve_wait_and_shorter_side(self):
        helper = body("bus_districts.nut", "OpexRoad1yBerthReserve")
        self.assertIn("local floor = 20000;", helper)
        self.assertIn('("nextProjectCapital" in projects.stats)', helper)
        self.assertIn('typeof nextCap != "integer"', helper)
        self.assertIn("if (nextCap > floor) return nextCap;", helper)
        extra = body("bus_districts.nut", "OpexRoad1yExtraStops")
        self.assertIn("(ROAD1Y_BERTH_FLEET & 1) != 0", extra)
        self.assertLess(
            extra.index("(ROAD1Y_BERTH_FLEET & 1) != 0"),
            extra.index("AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)",
                        extra.index("(ROAD1Y_BERTH_FLEET & 1) != 0")),
        )
        self.assertIn("local waitLimit = cap * capacity;", extra)
        self.assertIn("waitLimit = capacity;", extra)
        self.assertIn("waiting <= waitLimit", extra)
        self.assertIn("if (line.nStopsA < line.nStopsB) onlySide = 0;", extra)
        self.assertIn("else if (line.nStopsB < line.nStopsA) onlySide = 1;", extra)
        self.assertIn("if (onlySide >= 0 && side != onlySide) continue;", extra)
        self.assertIn("berthReserve = OpexRoad1yBerthReserve(ai);", extra)
        self.assertIn(
            "OpexRoad1yBuildExtraStop(catalog, line, side, tiles, berthReserve)",
            extra,
        )
        # Le garde passagers historique reste avant toute construction.
        guard = extra.index("(ROAD1Y_BUS_FIXES & 1)")
        self.assertLess(guard, extra.index("OpexRoad1yBuildExtraStop("))
        caller = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")
        self.assertIn(
            "OpexRoad1yExtraStops(this._catalog, line, have, capacity,\n"
            "          waitingA, waitingB, movingCount, ym, this);",
            caller,
        )

    def test_bit2_adds_one_bus_under_min_stops_cap(self):
        code = body("bus_districts_overrides.nut", "OpexRoad1yRefleetSaved")
        start = code.index("if (isPax && (ROAD1Y_BERTH_FLEET & 2) != 0)")
        end = code.index("if (road1yWant > 2)", start)
        block = code[start:end]
        self.assertIn("if (berthMin >= 2)", block)
        self.assertIn("local berthCap = ROAD1Y_FLEET * berthMin;", block)
        self.assertNotIn("road1yStopsA + road1yStopsB", block)
        self.assertIn("local berthWait = waitingA < waitingB ? waitingA : waitingB;", block)
        self.assertIn("else if (berthWait <= 10) berthDecision = \"wait\";", block)
        self.assertIn("AIVehicle.GetCurrentSpeed(berthVeh) == 0", block)
        self.assertIn("else if (berthStopped >= 2) berthDecision = \"stopped\";", block)
        self.assertIn("berthCash < berthPrice + 20000", block)
        self.assertIn("road1yWant = 0;", block)
        self.assertIn("road1yWant = 1;", block)
        self.assertIn("road1yCap = berthCap;", block)
        # Le plafond historique min, pas la somme, reste le chemin hors bit 2.
        self.assertIn(": (road1yStopsB < road1yStopsA ? road1yStopsB : road1yStopsA)", code)
        self.assertIn("local road1yCap = fleetPerStop * road1yStops;", code)

    def test_decision_log_fields(self):
        districts = source("bus_districts.nut")
        overrides = source("bus_districts_overrides.nut")
        for blob in (districts, overrides):
            self.assertIn('OpexDecide("ROAD1Y_BERTH_FLEET"', blob)
            self.assertIn("stops_a=", blob)
            self.assertIn("stops_b=", blob)
            self.assertIn("wait=", blob)
            self.assertIn("cash=", blob)
            self.assertIn("decision=", blob)
        self.assertIn('"bit=1 line="', districts)
        self.assertIn('"bit=2 line="', overrides)
        self.assertIn('decision=" + (have < cap ? "fleet" : "wait")', districts)
        for decision in ("ok", "cash", "no_site", "add", "stopped", "cap"):
            self.assertIn(f'"{decision}"', districts if decision in ("ok", "cash", "no_site") else overrides)

    def test_squirrel_hazards(self):
        for filename in ("bus_districts.nut", "bus_districts_overrides.nut",
                         "settings.nut", "globals_pre.nut", "info.nut"):
            code = source(filename)
            for word in ("clone", "base", "par", "parent", "static", "yield",
                         "vargc", "vargv", "resume", "constructor", "instanceof", "delegate"):
                self.assertNotRegex(code, r"\blocal\s+" + word + r"\b", filename)
            self.assertNotIn("function(", code, filename)
            self.assertNotIn(".find(", code, filename)
            try_blocks = re.findall(r"try\s*\{[^}]*\}", code, re.DOTALL)
            for tb in try_blocks:
                self.assertNotIn("yield", tb, filename)


if __name__ == "__main__":
    unittest.main()
