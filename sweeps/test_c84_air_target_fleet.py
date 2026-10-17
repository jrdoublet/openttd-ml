"""Contrat de retrait C84 — c84_air_target_fleet (defaut 0, refute −69,6 k£/an).

Au defaut, C84_AIR_TARGET_FLEET etait false : X || false = X et X && false = false.
La croissance AIR reste la flotte historique a un avion, assouplie seulement par
la cible C121 (targetAirPlanes). targetSizing d'OpexAirEconomics reste dans la
signature, fige a false : les arguments positionnels suivants (serviceScan,
timings C100) partagent cet appel.
"""
from pathlib import Path
import unittest

from sweeps.campaign_freeze import parse_ai_settings
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


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
                return text[start : pos + 1]
    raise AssertionError(f"corps non ferme: {signature}")


class TestC84AirTargetFleetRemoved(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.globals = source("globals_pre.nut")
        cls.settings = source("settings.nut")
        cls.builder = read_builder_air()
        cls.task_air = source("task_air.nut")
        cls.projects = read_projects_source()

    def test_setting_global_and_loader_are_gone(self):
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertNotIn("c84_air_target_fleet", defaults)
        self.assertNotIn('name = "c84_air_target_fleet"', self.info)
        self.assertNotIn("C84_AIR_TARGET_FLEET", self.globals)
        self.assertNotIn('GetSetting("c84_air_target_fleet")', self.settings)
        for path in AI.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("C84_AIR_TARGET_FLEET", text, path.name)
            self.assertNotIn("c84_air_target_fleet", text, path.name)
            self.assertNotIn("c84BelowTarget", text, path.name)
            self.assertNotIn("c84MarginalProfit", text, path.name)
            self.assertNotIn("c84Catalog", text, path.name)

    def test_one_plane_base_stays_and_target_helpers_are_gone(self):
        economics = function_body(self.builder, "function OpexAirEconomics(")
        self.assertIn("targetSizing = false", economics)
        self.assertIn("local multiPlaneMax =", economics)
        self.assertIn("local maxAllowed = (targetSizing || serviceScan) ? multiPlaneMax", economics)
        self.assertIn(
            "((OPEX_ECONOMY_OPCODE_COMPAT_FALSE || FLEET_PORTFOLIO) ? 1 : multiPlaneMax)",
            economics,
        )
        self.assertNotIn("function OpexAirTargetEconomics(", self.builder)
        self.assertNotIn("function OpexAirAttachTargetFleet(", self.builder)
        self.assertNotIn("function OpexAirExistingLineMarginalEconomics(", self.builder)
        self.assertNotIn("opcodePadding, 0, true)", self.builder)
        choose = function_body(self.builder, "function OpexAirChooseRoutePlane(")
        self.assertNotIn("OpexAirAttachTargetFleet", choose)
        self.assertNotIn("OpexAirTargetEconomics", choose)

    def test_growth_health_gates_follow_c121_target_only(self):
        resize = function_body(self.task_air, "function OpexAI::_resizeAirFleets(")
        self.assertNotIn("c84BelowTarget", resize)
        self.assertNotIn("local belowTarget", resize)
        self.assertNotIn("!belowTarget", resize)
        self.assertIn(
            'local c121BelowTarget = ("targetAirPlanes" in line)',
            resize,
        )
        self.assertIn(
            'if (!c121BelowTarget && ("lastProfit" in line) && line.lastProfit < 0)',
            resize,
        )
        self.assertIn(
            'if (!c121BelowTarget && ("deadStreak" in line) && line.deadStreak >= 1)',
            resize,
        )
        self.assertIn('if (("deadStreak" in line) && line.deadStreak >= 2)', resize)
        self.assertIn("if (have >= physicalMaxPlanes)", resize)
        self.assertIn("if (money < need)", resize)
        self.assertIn("if (c121BelowTarget) {", resize)
        self.assertIn("local targetNeed = line.targetAirPlanes - have;", resize)
        self.assertNotIn("OpexAirExistingLineMarginalEconomics", resize)
        self.assertNotIn('OpexSpanAgg("fleet.marginal"', resize)

    def test_fleet_project_keeps_c121_or_historical_profit(self):
        project = function_body(self.projects, "function OpexProjectFromFleet(")
        self.assertIn('local c121BelowTarget = ("targetAirPlanes" in line)', project)
        self.assertIn("profit = perPlaneProfit * entry.want;", project)
        self.assertIn('if (("lastProfit" in line) && line.lastProfit > 0)', project)
        self.assertNotIn("c84MarginalProfit", project)
        self.assertNotIn("c84BelowTarget", project)
        self.assertIn("if (V161_FLEET_NET_MARGINAL > 0) {", project)
        self.assertNotIn("!c84BelowTarget", project)
        fit = function_body(self.projects, "function OpexProjectFitFleetToBudget(")
        self.assertIn(
            "fitted.profitAnnual = (project.profitAnnual / entry.want) * quantity;",
            fit,
        )
        self.assertNotIn("C84_AIR_TARGET_FLEET", fit)
        self.assertNotIn("c84Catalog", fit)
        self.assertNotIn("OpexAirExistingLineMarginalEconomics", fit)


if __name__ == "__main__":
    unittest.main()
