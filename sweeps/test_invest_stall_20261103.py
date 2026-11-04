"""Contrats opt-in INVEST-STALL et protection des autres politiques du worktree."""

from pathlib import Path
import unittest

from invest_stall_source_off import BEFORE, check_off, project_off

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class TestInvestStall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.read = staticmethod(lambda name: (AI / name).read_text(encoding="utf8"))

    def test_off_sources_are_exact_previous_bytes(self):
        self.assertEqual(check_off(), BEFORE)

    def test_strict_projector(self):
        for name in BEFORE:
            text = self.read(name)
            self.assertEqual(project_off(name, project_off(name, text)), project_off(name, text))
        with self.assertRaises(ValueError):
            project_off("scheduler.nut", "without marker")

    def test_setting_0_on_all_four_profiles(self):
        info = self.read("info.nut")
        block = info.split('AddSetting({ name = "invest_stall",', 1)[1].split("});", 1)[0]
        for key in ("easy", "medium", "hard", "custom"):
            self.assertIn(key + "_value = 0", block)
        self.assertIn('INVEST_STALL <- false;', self.read("globals_pre.nut"))
        self.assertIn('INVEST_STALL = AIController.GetSetting("invest_stall") == 1;', self.read("settings.nut"))
        self.assertIn('if (INVEST_STALL) OpexInvestStallTick(this);', self.read("scheduler.nut"))
        self.assertIn('require("invest_stall.nut");', self.read("main.nut"))
        self.assertIn('require("invest_stall_fleet.nut");', self.read("main.nut"))

    def test_undertransport_and_cash_gate(self):
        code = self.read("invest_stall.nut")
        for line in (
            "return INVEST_STALL && MODE_RAIL",
            "OPEX_START_YEAR + 4",
            "OpexAvailableCapital() >= 750000",
            "AIIndustry.GetLastMonthProduction(industry, line.cargo)",
            "AIIndustry.GetLastMonthTransportedPercentage(industry, line.cargo)",
            "AIStation.GetCargoRating(station, line.cargo)",
            "(rawRating >= 0 && rawRating <= 100) ? rawRating : -1",
            "pct >= 75 && rating >= 75",
            "production.tofloat() <= total",
            "OpexInvestStallLineCapacity(existing)",
            "INVEST_STALL_LAST_MONTH == month",
        ):
            self.assertIn(line, code)
        for forbidden in ("CloneVehicle", "BuildRail(", "BuildRailStation(", "SellVehicle(", "OpexGenerateModeProjects", "V217_REGEN_NO_PAX"):
            self.assertNotIn(forbidden, code)

    def test_station_rating_is_already_a_percent(self):
        code = self.read("invest_stall.nut")
        self.assertIn("AIStation.GetCargoRating(station, line.cargo)", code)
        self.assertIn("rawRating >= 0 && rawRating <= 100", code)
        self.assertNotIn("rawRating * 100 / 255", code)

    def test_v284_recovery_and_pre_astar_hook(self):
        self.assertIn('if (INVEST_STALL && OpexInvestStallFleetSelect(this, year)) return;', self.read("task_rail.nut"))
        orchestrator = self.read("orchestrator.nut")
        self.assertIn('(INVEST_STALL && OpexV284Busy(this))', orchestrator)
        persist = self.read("persist.nut")
        self.assertIn('(INVEST_STALL && this._v284State != null)', persist)
        self.assertIn('OpexInvestStallPending(this)', persist)
        self.assertIn('OpexInvestStallPending(this)', orchestrator)

    def test_save_load_monthly_marker(self):
        persist = self.read("persist.nut")
        self.assertIn('if (INVEST_STALL) shortSave.investStallLastMonth <- INVEST_STALL_LAST_MONTH;', persist)
        self.assertIn('if (INVEST_STALL) saveObj.investStallLastMonth <- INVEST_STALL_LAST_MONTH;', persist)
        self.assertIn('typeof data.investStallLastMonth == "integer"', persist)
        self.assertIn('INVEST_STALL_LAST_MONTH = INVEST_STALL ? INVEST_STALL_SAVED_MONTH : -1;', self.read("settings.nut"))

    def test_observable_exposure(self):
        code = self.read("invest_stall.nut")
        for event in ('event=gate', 'event=screen', 'event=summary'):
            self.assertIn(event, code)
        self.assertIn('if (DECISION_LOG)', code)


if __name__ == "__main__":
    unittest.main()
