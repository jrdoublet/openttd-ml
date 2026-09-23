from pathlib import Path
import unittest

from sweeps.campaign_freeze import parse_ai_settings


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


class TestC84AirTargetFleet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = AI / "info.nut"
        cls.globals = source("globals_pre.nut")
        cls.settings = source("settings.nut")
        cls.builder = source("builder_air.nut")
        cls.task_air = source("task_air.nut")
        cls.projects = source("projects.nut")

    def test_setting_is_experimental_and_loaded_once(self):
        defaults = parse_ai_settings(self.info)
        self.assertEqual(defaults["c84_air_target_fleet"], 0)
        self.assertIn("C84_AIR_TARGET_FLEET <- false;", self.globals)
        self.assertIn(
            'C84_AIR_TARGET_FLEET = AIController.GetSetting("c84_air_target_fleet") != 0;',
            self.settings,
        )

    def test_target_sizing_keeps_historical_one_plane_base_variant(self):
        economics = function_body(self.builder, "function OpexAirEconomics(")
        self.assertIn("targetSizing = false", economics)
        self.assertIn("local multiPlaneMax =", economics)
        self.assertIn("local maxAllowed = targetSizing ? multiPlaneMax", economics)
        self.assertIn(
            "((OPEX_ECONOMY_OPCODE_COMPAT_FALSE || FLEET_PORTFOLIO) ? 1 : multiPlaneMax)",
            economics,
        )

        target = function_body(self.builder, "function OpexAirTargetEconomics(")
        self.assertIn(
            "infrastructureMaintenance, 0, newAirportCount, opcodePadding, 0, true",
            target,
        )
        economics = function_body(self.builder, "function OpexAirEconomics(")
        self.assertNotIn("targetProfitCurve", economics)
        self.assertNotIn("targetRevenueCurve", economics)
        self.assertNotIn("targetProfitCurve", self.builder)
        self.assertNotIn("targetRevenueCurve", self.builder)

        self.assertNotIn("function OpexAirTargetInitialPlan(", self.builder)
        self.assertNotIn("c84InitialTarget", self.builder)
        self.assertNotIn("c84TargetPlan", self.builder)

    def test_target_is_attached_after_current_aircraft_choice(self):
        choose = function_body(self.builder, "function OpexAirChooseRoutePlane(")
        full_at = choose.index("OpexAirChooseRoutePlaneFull(")
        attach_at = choose.index("OpexAirAttachTargetFleet(", full_at)
        self.assertLess(full_at, attach_at)

        attach = function_body(self.builder, "function OpexAirAttachTargetFleet(")
        self.assertIn("OpexAirTargetEconomics(catalog, airport, choice.plane", attach)
        full = function_body(self.builder, "function OpexAirChooseRoutePlaneFull(")
        self.assertNotIn("OpexAirTargetEconomics(", full)
        self.assertNotIn("targetSizing", full)

    def test_growth_keeps_physical_wait_and_cash_guards(self):
        resize = function_body(self.task_air, "function OpexAI::_resizeAirFleets(")
        below = resize.index("local c84BelowTarget =")
        hard_dead = resize.index("line.deadStreak >= 2", below)
        wait = resize.index('OpexAirFleetRefusal(line, year, "W")', hard_dead)
        target_cap = resize.index("local targetNeed = line.targetAirPlanes - have;", wait)
        purchase = resize.index("OpexAirAddPlane(line)", target_cap)

        self.assertLess(below, hard_dead)
        self.assertLess(hard_dead, wait)
        self.assertLess(wait, target_cap)
        self.assertLess(target_cap, purchase)
        self.assertIn("if (have >= physicalMaxPlanes)", resize)
        self.assertIn("if (money < need)", resize)

    def test_target_only_relaxes_first_health_gate(self):
        resize = function_body(self.task_air, "function OpexAI::_resizeAirFleets(")
        self.assertIn(
            'if (!c84BelowTarget && ("lastProfit" in line) && line.lastProfit < 0)',
            resize,
        )
        self.assertIn(
            'if (!c84BelowTarget && ("deadStreak" in line) && line.deadStreak >= 1)',
            resize,
        )
        self.assertIn(
            'if (("deadStreak" in line) && line.deadStreak >= 2)',
            resize,
        )

    def test_under_target_project_uses_live_fixed_plane_marginal_before_historical_fallback(self):
        marginal_helper = function_body(
            self.builder, "function OpexAirExistingLineMarginalEconomics("
        )
        self.assertIn("AIVehicle.GetEngineType(template)", marginal_helper)
        self.assertIn(
            "infrastructureMaintenance, 0, 0, 0, have);",
            marginal_helper,
        )
        self.assertIn(
            "infrastructureMaintenance, 0, 0, 0, have + want);",
            marginal_helper,
        )
        self.assertNotIn("OpexAirChooseRoutePlane", marginal_helper)

        resize = function_body(self.task_air, "function OpexAI::_resizeAirFleets(")
        wait = resize.index('OpexAirFleetRefusal(line, year, "W")')
        want = resize.index(
            "local want = (room < maxAddedPerPass) ? room : maxAddedPerPass;",
            wait,
        )
        marginal = resize.index(
            "OpexAirExistingLineMarginalEconomics(this._catalog, line, have, want)",
            want,
        )
        append = resize.index("plan.append(fleetEntry);", marginal)
        self.assertLess(wait, want)
        self.assertLess(want, marginal)
        self.assertLess(marginal, append)
        self.assertEqual(self.task_air.count("airMonthlyPax <-"), 2)

        project = function_body(self.projects, "function OpexProjectFromFleet(")
        below = project.index("local c84BelowTarget =")
        gate = project.index('if (!("c84MarginalProfit" in entry)) return null;', below)
        delta = project.index("profit = entry.c84MarginalProfit;", gate)
        reject = project.index("if (profit <= 0) return null;", delta)
        fallback = project.index('if (("lastProfit" in line) && line.lastProfit > 0)', reject)

        self.assertLess(below, gate)
        self.assertLess(gate, delta)
        self.assertLess(delta, reject)
        self.assertLess(reject, fallback)
        self.assertIn('if ("c84MarginalRevenue" in entry)', project)
        self.assertNotIn("targetAirProfitCurve", project)
        self.assertNotIn("targetAirRevenueCurve", project)


if __name__ == "__main__":
    unittest.main()
