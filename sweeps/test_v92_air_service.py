"""Contrat de retrait V92 — v92_air_service_choice (defaut 0, refute −42 %).

Au defaut, V92_AIR_SERVICE_CHOICE etait false : le choix de service, la
variante bon marche et le reequipement ne partaient jamais. Le chemin
conserve est le memo C80 puis OpexAirChooseRoutePlaneFull, le forfait
courrier de 15 % et une duree de vie de 20 ans. serviceScan reste un
argument positionnel d'OpexAirEconomics, toujours false.
"""
from pathlib import Path
import unittest

from sweeps.campaign_freeze import parse_ai_settings
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"

REMOVED = (
    "v92_air_service_choice",
    "V92_AIR_SERVICE_CHOICE",
    "AIR_MAIL_CAP",
    "AIR_MAIL_LEARN_MONTH",
    "V92_CLOSED_PAIRS",
    "OpexAirV92PairBlocked",
    "OpexAirLearnMailCaps",
    "OpexAirApplyKnownMail",
    "OpexAirServiceBetter",
    "OpexAirChooseRouteService",
    "OpexAirLineSellValue",
    "OpexAirLineReequipPending",
    "OpexAirClearReequip",
    "OpexAirAlreadySentToHangar",
    "OpexAirSendLineToHangar",
    "OpexAirReleaseHangarHold",
    "OpexAirRebuildFleet",
    "OpexAirLineAllInHangar",
    "OpexAirReplaceFleet",
    "OpexAirConsiderReplace",
    "OpexAirMaybeReequip",
    "OpexAirCatalogPlane",
    "v92PairKey",
    "v92PendingEngine",
    "v92SentToHangar",
    "v92Role",
)


def source(name):
    return (AI / name).read_text(encoding="utf-8")


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
    raise AssertionError(f"corps non ferme: {signature}")


class V92AirServiceChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.globals = source("globals_pre.nut")
        cls.settings = source("settings.nut")
        cls.builder = read_builder_air()
        cls.task_air = source("task_air.nut")
        cls.catalog = source("catalog.nut")
        cls.report = source("task_report.nut")
        cls.events = source("event_handlers.nut")

    def test_setting_global_and_loader_are_gone(self):
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertNotIn("v92_air_service_choice", defaults)
        self.assertNotIn('name = "v92_air_service_choice"', self.info)
        self.assertNotIn("V92_AIR_SERVICE_CHOICE", self.globals)
        self.assertNotIn('GetSetting("v92_air_service_choice")', self.settings)
        for path in AI.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            for token in REMOVED:
                self.assertNotIn(token, text, f"{path.name}:{token}")

    def test_default_economics_keep_flat_mail_and_twenty_year_life(self):
        economics = function_body(self.builder, "function OpexAirEconomics(")
        self.assertIn("serviceScan = false", economics)
        self.assertIn("(targetSizing || serviceScan) ? multiPlaneMax", economics)
        self.assertIn("&& !serviceScan", economics)
        self.assertIn("local lifeYears = 20;", economics)
        self.assertIn("plane.price / lifeYears", economics)
        self.assertNotIn("plane.ageYears", economics)
        fare = function_body(self.builder, "function OpexAirFarePerPax(")
        self.assertIn("local mailPct = 15;", fare)
        self.assertNotIn("mailCapacity", fare)
        self.assertNotIn("(plane.mailCapacity * 100) / plane.capacity", fare)
        self.assertIn("function OpexAirPlaneInRange(plane, distance)", self.builder)
        self.assertIn("ageYears = AIEngine.GetMaxAge(e) / 365", self.catalog)
        self.assertIn("mailCapacity = -1", self.catalog)

    def test_route_choice_stays_on_the_historical_plane(self):
        choose = function_body(self.builder, "function OpexAirChooseRoutePlane(")
        self.assertIn("OpexAirChooseRoutePlaneFull(", choose)
        self.assertNotIn("OpexAirChooseRouteService", choose)
        store = function_body(self.builder, "function OpexAirStoreRoutePlan(")
        self.assertIn("if (projects != null) projects.append(plan);", store)
        self.assertIn("if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;", store)
        self.assertNotIn("v92", store)
        self.assertNotIn("function OpexAirChooseRouteService(", self.builder)
        self.assertNotIn("OpexAirV92PairBlocked", self.task_air)

    def test_growth_cooldown_and_scrap_ignore_reequipment(self):
        resize = function_body(self.task_air, "function OpexAI::_resizeAirFleets(")
        self.assertIn("if (AIR_FLEET_COOLDOWN_PREFILTER && !priorityPath)", resize)
        self.assertNotIn("!V92_AIR_SERVICE_CHOICE", resize)
        self.assertNotIn("OpexAirLineReequipPending", resize)
        add = function_body(self.builder, "function OpexAirAddPlane(")
        self.assertNotIn("OpexAirMaybeReequip", add)
        self.assertNotIn('result.reason = "TARGET"', add)
        self.assertIn('result.reason = "PRICE"', add)
        scrap = function_body(self.report, "function OpexAI::_triggerScrapLine(")
        self.assertIn("AIVehicle.SendVehicleToDepot(v);", scrap)
        self.assertNotIn("reequipPending", scrap)
        self.assertNotIn("OpexAirClearReequip", scrap)
        retire = function_body(self.report, "function OpexAI::_scrapRetiredVehicles(")
        self.assertNotIn("OpexAirLineReequipPending", retire)
        self.assertIn("if (AIVehicle.SendVehicleToDepot(vehicle))", self.events)
        self.assertNotIn("defer_v92", self.events)


if __name__ == "__main__":
    unittest.main()
