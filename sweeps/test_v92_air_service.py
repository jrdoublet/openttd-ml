"""Contrat V92 : choix d'un service aerien (moteur x nombre) et variante bon marche."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
CATALOG = (ROOT / "ai" / "OpexAI" / "catalog.nut").read_text(encoding="utf-8")
TASK_AIR = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    raise AssertionError(signature)


class V92AirServiceChoiceTests(unittest.TestCase):
    def test_setting_defaults_off(self):
        self.assertIn("V92_AIR_SERVICE_CHOICE <- false;", GLOBALS)
        start = INFO.index('name = "v92_air_service_choice"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertIn(
            'V92_AIR_SERVICE_CHOICE = AIController.GetSetting("v92_air_service_choice") != 0;',
            SETTINGS,
        )

    def test_service_scan_keeps_one_plane_cap_unless_requested(self):
        economics = function_body(BUILDER, "function OpexAirEconomics(")
        self.assertIn("serviceScan = false", economics)
        self.assertIn("(targetSizing || serviceScan) ? multiPlaneMax", economics)
        self.assertIn('&& !serviceScan', economics)
        self.assertIn("plane.ageYears > 1", economics)
        self.assertIn("plane.price / lifeYears", economics)

    def test_mail_uses_measured_hold_ratio(self):
        fare = function_body(BUILDER, "function OpexAirFarePerPax(")
        self.assertIn("local mailPct = 15;", fare)
        self.assertIn("(plane.mailCapacity * 100) / plane.capacity", fare)
        self.assertIn("V92_AIR_SERVICE_CHOICE", fare)

    def test_choice_emits_service_and_cheap_variant(self):
        choose = function_body(BUILDER, "function OpexAirChooseRoutePlane(")
        self.assertLess(
            choose.index("V92_AIR_SERVICE_CHOICE"),
            choose.index("OpexAirChooseRoutePlaneFull("),
        )
        service = function_body(BUILDER, "function OpexAirChooseRouteService(")
        self.assertIn("false, true)", service)
        self.assertIn("choice.alternate <-", service)
        self.assertIn("plane.price <= cheapLimit", service)
        self.assertIn("infrastructureMaintenance, maxCapital, newAirportCount", service)
        store = function_body(BUILDER, "function OpexAirStoreRoutePlan(")
        self.assertIn('cheap.v92Role = "cheap"', store)
        self.assertIn("v92PairKey", store)
        self.assertIn("OpexAirV92PairBlocked", TASK_AIR)

    def test_growth_can_replace_the_engine(self):
        add = function_body(BUILDER, "function OpexAirAddPlane(")
        self.assertIn("OpexAirMaybeReequip(line, catalog, hangar, airportTile)", add)
        consider = function_body(BUILDER, "function OpexAirConsiderReplace(")
        self.assertIn("have + 1", consider)
        self.assertIn("OpexAirCadenceCap(line, catalog, null)", consider)
        self.assertIn("OpexAirLineSellValue(line)", consider)
        send = function_body(BUILDER, "function OpexAirSendLineToHangar(")
        self.assertIn("OpexAirAlreadySentToHangar(line, v)", send)
        self.assertIn("line.v92SentToHangar.append(v)", send)
        self.assertNotIn("OpexAirVehicleGoingToHangar", BUILDER)
        replace = function_body(BUILDER, "function OpexAirReplaceFleet(")
        self.assertLess(replace.index("money + sell < cost + OpexCashReserve()"), replace.index("SellVehicle"))
        self.assertLess(replace.index("AIEngine.IsBuildable(plane.id)"), replace.index("SellVehicle"))
        self.assertEqual(replace.count("OpexAirRebuildFleet(line, hangar, oldEngine, oldCount, cargo)"), 2)
        self.assertIn("line.vehicles = []", replace)
        resize = function_body(TASK_AIR, "function OpexAI::_resizeAirFleets(")
        self.assertLess(resize.index("OpexAirLineReequipPending(line)"), resize.index("lastAirFleetYear"))
        report = (ROOT / "ai" / "OpexAI" / "task_report.nut").read_text(encoding="utf-8")
        scrap = function_body(report, "function OpexAI::_triggerScrapLine(")
        self.assertIn("if (!reequipPending) AIVehicle.SendVehicleToDepot(v);", scrap)
        self.assertIn("OpexAirClearReequip(line)", scrap)
        self.assertIn("ageYears = AIEngine.GetMaxAge(e) / 365", CATALOG)
        self.assertIn("mailCapacity = -1", CATALOG)


if __name__ == "__main__":
    unittest.main()
