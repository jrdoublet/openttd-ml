"""Contrats B3 : cibles de flotte routière et switch temporel."""
from pathlib import Path
import re
import unittest
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
                return text[brace + 1 : pos]
    raise AssertionError(f"corps non fermé: {signature}")


class TestB3RoadFleetTargets(unittest.TestCase):
    def setUp(self):
        self.economy = source("economy.nut")
        self.candidates = source("candidates.nut")
        self.projects = read_projects_source()
        self.road = source("task_road.nut")
        self.report = source("task_report.nut")
        self.info = source("info.nut")
        self.settings = source("settings.nut")
        self.globals_pre = source("globals_pre.nut")
        self.persist = source("persist.nut")

    def test_switch_defaults_off_and_is_bound_once(self):
        setting = re.search(
            r'name\s*=\s*"road_time_scaled_cap".*?custom_value\s*=\s*(\d+)',
            self.info,
            re.S,
        )
        self.assertIsNotNone(setting)
        self.assertEqual(setting.group(1), "0")
        self.assertIn("ROAD_TIME_SCALED_CAP <- false", self.globals_pre)
        self.assertIn(
            'ROAD_TIME_SCALED_CAP = AIController.GetSetting("road_time_scaled_cap") != 0',
            self.settings,
        )

    def test_time_scaled_cap_is_pax_only_conservative_and_bounded(self):
        body = function_body(self.economy, "function OpexRoadFleetVehicleCap(")
        self.assertIn("local berthCapacity = OpexRoadPhysicalVehicleCap", body)
        self.assertIn('if (!ROAD_TIME_SCALED_CAP || kind != "pax") return berthCapacity', body)
        self.assertIn("(berthCapacity * oneWayDays) / ROAD_PAX_STOP_DWELL_DAYS", body)
        self.assertIn("if (cap < berthCapacity) cap = berthCapacity", body)
        self.assertIn("if (cap > MAX_ROAD_VEHICLES) cap = MAX_ROAD_VEHICLES", body)

    def test_switch_zero_and_freight_keep_historical_berth_cap(self):
        body = function_body(self.economy, "function OpexRoadFleetVehicleCap(")
        self.assertIn('!ROAD_TIME_SCALED_CAP || kind != "pax"', body)
        self.assertIn("return berthCapacity", body)

    def test_economics_exposes_raw_berth_fleet_cap_and_selected_target(self):
        body = function_body(self.economy, "function OpexRoadLineEconomics(")
        self.assertIn("local vehiclesForVolume = OpexCeilDiv", body)
        self.assertIn("local vehicles = vehiclesForVolume", body)
        self.assertIn("local roadBerthCapacity = OpexRoadPhysicalVehicleCap(1, 1)", body)
        self.assertIn("local roadVehicleCap = OPEX_ECONOMY_OPCODE_COMPAT_FALSE ? 1 : roadBerthCapacity", body)
        self.assertIn('if (!OPEX_ECONOMY_OPCODE_COMPAT_FALSE && ROAD_TIME_SCALED_CAP && kind == "pax")', body)
        self.assertIn("roadVehicleCap = OpexRoadFleetVehicleCap(1, 1, oneWayDays, kind)", body)
        self.assertIn("if (vehicles > roadVehicleCap) vehicles = roadVehicleCap", body)
        self.assertIn("vehiclesForVolume = vehiclesForVolume", body)
        self.assertIn("roadBerthCapacity = roadBerthCapacity", body)
        self.assertIn("roadVehicleCap = roadVehicleCap", body)
        self.assertIn("trains = vehicles", body)

    def test_post_siting_recalibration_propagates_all_three_notions(self):
        body = function_body(self.economy, "function OpexApplyRoadEconomics(")
        self.assertIn("candidate.vehiclesForVolume = economics.vehiclesForVolume", body)
        self.assertIn("candidate.roadBerthCapacity = economics.roadBerthCapacity", body)
        self.assertIn("candidate.roadVehicleCap = economics.roadVehicleCap", body)
        self.assertIn("candidate.trains = economics.trains", body)

    def test_candidate_keeps_raw_berth_fleet_cap_and_selected_target_separate(self):
        body = function_body(self.candidates, "function OpexMakeRoadCandidate(")
        self.assertIn("vehiclesForVolume = economics.vehiclesForVolume", body)
        self.assertIn("roadBerthCapacity = economics.roadBerthCapacity", body)
        self.assertIn("roadVehicleCap = economics.roadVehicleCap", body)
        self.assertIn("trains = economics.trains", body)

    def test_ranking_carries_measurements_but_scores_still_use_existing_fields(self):
        body = function_body(self.projects, "function OpexProjectFromCandidate(")
        self.assertIn("project.vehiclesForVolume <-", body)
        self.assertIn("project.roadVehicleCap <-", body)
        self.assertIn("project.selectedRoadVehicles <- candidate.trains", body)
        self.assertIn("budgetScore = OpexProjectScore(scoreRevenue, budgetCapital)", body)
        self.assertIn("opcodeScore = OpexProjectScore(scoreRevenue, expectedOps)", body)
        for logger in (
            "function OpexLogPortfolioRank(projects)",
            "function OpexLogPortfolioRankWithTension(projects)",
        ):
            log_body = function_body(self.projects, logger)
            self.assertIn("raw_vehs=", log_body)
            self.assertIn("berth_cap=", log_body)
            self.assertIn("fleet_cap=", log_body)
            self.assertIn("capped_vehs=", log_body)
            self.assertIn("p.payload.roadBerthCapacity", log_body)

    def test_road_build_persists_measurements_for_actual_comparison(self):
        body = function_body(self.road, "function OpexAI::_tryBuildRoadProject(")
        self.assertIn("raw_vehs=", body)
        self.assertIn("berth_cap=", body)
        self.assertIn("fleet_cap=", body)
        self.assertIn("capped_vehs=", body)
        self.assertIn("predVehiclesForVolume =", body)
        self.assertIn("predRoadBerthCapacity =", body)
        self.assertIn("predRoadVehicleCap =", body)
        self.assertIn("predTrains = candidate.trains", body)

    def test_refleet_uses_temporal_cap_without_retired_c50b_override(self):
        body = function_body(self.road, "function OpexAI::_refleetRoadLines(")
        self.assertIn("local physicalCap = OpexRoadPhysicalVehicleCap(", body)
        self.assertNotIn("C50B_ROAD_CAP_RELAX", body)
        self.assertIn("ROAD_TIME_SCALED_CAP", body)
        self.assertIn("OpexRoadFleetVehicleCap(nStopsA, nStopsB, oneWayDays, line.kind)", body)
        self.assertIn("if (target > physicalCap) target = physicalCap", body)

    def test_annual_report_separates_raw_berth_vehicle_cap_and_actual_fleet(self):
        body = function_body(self.report, "function OpexAI::_reportLines(")
        for field in (
            '" raw_vehs="',
            '" pred_berth_cap="',
            '" pred_vehicle_cap="',
            '" berth_cap="',
            '" vehicle_cap="',
            '" pred_vehs="',
            '" n_stops_a="',
            '" n_stops_b="',
            '" vehs="',
        ):
            self.assertIn(field, body)
        self.assertIn("OpexRoadPhysicalVehicleCap(nStopsA, nStopsB)", body)
        self.assertIn("OpexRoadFleetVehicleCap(nStopsA, nStopsB, predDays, lKind)", body)

    def test_line_fields_survive_generic_serialization(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        self.assertIn("local saveLines = this._lines", save)
        self.assertIn("foreach (key, val in line)", save)
        # C121 : `clone line` conserve tous les champs ; seuls floats, types non
        # serialisables et diagnostics c121* sont ensuite retouches.
        self.assertIn("local serializableLine = clone line;", save)
        self.assertIn("serializableLine[key] = val.tointeger();", save)
        self.assertIn("delete serializableLine[key];", save)

    def test_line_serialization_is_single_pass_under_save_opcode_budget(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        self.assertIn("foreach (line in this._lines)", save)
        self.assertEqual(save.count("foreach (key, val in line)"), 1)
        self.assertNotIn("needsProjection", save)


if __name__ == "__main__":
    unittest.main()
