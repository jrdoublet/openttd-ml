"""R21 source contracts; engine acceptance and annual lifecycle need a real smoke."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TestFreightDestination(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "ai/OpexAI/task_report.nut").read_text(encoding="utf-8")
        # R13 : la sante fret est extraite dans OpexUpdateFreightLineHealth, appelee
        # depuis la branche isFreight de _reportLines.
        fn = cls.source.split("function OpexUpdateFreightLineHealth(", 1)[1].split("\nfunction ", 1)[0]
        cls.health = fn.split("local srcSuffering =", 1)[1]
        report = cls.source.split("function OpexAI::_reportLines(", 1)[1].split("\nfunction ", 1)[0]
        cls.freight_branch = report.split("    if (isFreight) {", 1)[1].split("} else if (vehicleType", 1)[0]

    def test_health_update_is_called_from_freight_branch(self):
        self.assertIn(
            "OpexUpdateFreightLineHealth(line, year, anchor, stationB, profit, runCost, srcAlive, srcProd);",
            self.freight_branch)

    def test_destination_is_checked_at_real_station_not_industry_id(self):
        self.assertIn("AICargoList_StationAccepting(stationB)", self.health)
        self.assertIn("dstSuffering = !accepting.HasItem(line.cargo);", self.health)
        self.assertNotIn("dstAlive", self.health)
        self.assertNotIn("dstIndustry", self.health)
        self.assertNotIn("GetCargoRating", self.health)

    def test_no_station_or_invalid_cargo_is_guarded(self):
        self.assertIn("if (!AIStation.IsValidStation(stationB)) {\n      dstSuffering = true;", self.health)
        self.assertIn("else if (AICargo.IsValidCargo(line.cargo))", self.health)
        self.assertIn("local dstSuffering = false;", self.health)

    def test_acceptance_query_is_limited_to_no_revenue_and_productive_source(self):
        self.assertIn("if (!srcSuffering && (profit + runCost) <= 0)", self.health)
        self.assertIn("(!srcAlive) || (srcProd == 0);", self.health)
        self.assertIn("local collapsed = (srcSuffering || dstSuffering) && (profit + runCost) <= 0;", self.health)

    def test_consecutive_year_hysteresis_is_preserved(self):
        self.assertIn("line.deadStreak = collapsed ? line.deadStreak + 1 : 0;", self.health)
        self.assertIn("if (!line.scrapping && line.deadStreak >= DEAD_STREAK_THRESHOLD)", self.source)
        self.assertIn('this._triggerScrapLine(line, "dead_streak");', self.source)
        self.assertNotIn("POLICY_VEHICLE_EVENTS", self.health)

    def test_retirement_keeps_vehicle_identity_and_confirmed_sales(self):
        trigger = self.source.split("function OpexAI::_triggerScrapLine(", 1)[1].split("\nfunction ", 1)[0]
        scrap = self.source.split("function OpexAI::_scrapDeadLines(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("line.scrapVehicles = ids;", trigger)
        self.assertIn("AIVehicle.IsStoppedInDepot(v) && AIVehicle.SellVehicle(v)", scrap)
        self.assertIn("line.scrapVehicles = remaining;", scrap)
        self.assertIn("this._lines.remove(toRemove[k]);", scrap)


if __name__ == "__main__":
    unittest.main()