"""Tests statiques du modele economique C119 AIR."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")

def function_body(source: str, name: str, next_name: str | None = None) -> str:
    start = source.index(f"function {name}")
    return source[start:] if next_name is None else source[start:source.index(f"function {next_name}", start)]

class TestC119AirIncomeModel(unittest.TestCase):
    def test_flag_exists_and_defaults_off(self):
        self.assertEqual(GLOBALS.count("C119_AIR_INCOME_MODEL <- false;"), 1)
        self.assertIn('C119_AIR_INCOME_MODEL = AIController.GetSetting("c119_air_income_model") != 0;', SETTINGS)
        self.assertIn('name = "c119_air_income_model"', INFO)
        setting = INFO[INFO.index('name = "c119_air_income_model"'):]
        setting = setting[:setting.index("});")]
        self.assertIn("easy_value = 0, medium_value = 0, hard_value = 0", setting)
        self.assertIn("custom_value = 0", setting)

    def test_payment_time_is_engine_and_geometry_derived(self):
        body = function_body(AIR, "OpexC119AirIncomeDays", "OpexAirEconomics")
        self.assertIn("AIEngine.GetMaxSpeed(plane.id)", body)
        self.assertIn("flightDistance + 30", body)
        self.assertIn("664", body)
        self.assertIn("speed * 24 * dayLengthFactor", body)
        self.assertIn('"GetDayLengthFactor" in AIDate', body)

    def test_c119_changes_payment_not_cycle_or_fleet(self):
        body = function_body(AIR, "OpexAirEconomics", "OpexAirTargetEconomics")
        self.assertIn("local c119Income = C119_AIR_INCOME_MODEL && paymentDistance > 0;", body)
        self.assertIn("local incomeDistance = c119Income ? paymentDistance : distance;", body)
        self.assertIn("OpexAirFarePerPax(catalog, plane, incomeDistance, incomeDays)", body)
        self.assertIn("OpexAirTripModel(plane.speed, plane.capacity, distance, plane.id, airport.type,", body)
        self.assertNotIn("OpexAirTripModel(plane.speed, plane.capacity, paymentDistance", body)
        self.assertIn("local targetPlanes = OpexCeilDiv(monthlyPax, capacityPerPlane.tointeger());", body)
        self.assertIn("local carried = (offered < monthlyCapacity ? offered : monthlyCapacity).tointeger();", body)

    def test_mail_model_is_not_part_of_c119(self):
        fare = function_body(AIR, "OpexAirFarePerPax", "OpexC119AirIncomeDays")
        self.assertNotIn("C119_AIR_INCOME_MODEL", fare)
        self.assertIn("local mailPct = 15;", fare)

    def test_c115_engine_scan_receives_payment_distance(self):
        c104 = function_body(AIR, "OpexC104BestAirEngine", "OpexC106MarginalPhysicalChoice")
        self.assertIn("mode, paymentDistance = 0", c104)
        self.assertGreaterEqual(c104.count("paymentDistance"), 4)
        c115 = function_body(AIR, "OpexC115ChooseRoutePlane", "OpexC116RouteFinanceCapital")
        self.assertIn("opcodePadding, paymentDistance = 0", c115)
        self.assertIn("opcodePadding, 0, paymentDistance", c115)
        self.assertIn("opcodePadding, 1, paymentDistance", c115)
        self.assertIn("opcodePadding, paymentDistance)", c115)

    def test_real_project_families_use_manhattan_payment_distance(self):
        self.assertIn("AIMap.DistanceManhattan(sites[a].anchor, sites[b].anchor)", AIR)
        self.assertIn("AIMap.DistanceManhattan(hub.anchor, site.anchor)", AIR)
        self.assertIn("AIMap.DistanceManhattan(hub1.anchor, hub2.anchor)", AIR)

    def test_c84_target_fleet_stays_outside_c119(self):
        target = function_body(AIR, "OpexAirTargetEconomics", "OpexAirExistingLineMarginalEconomics")
        self.assertNotIn("paymentDistance", target)
        self.assertNotIn("C119", target)

if __name__ == "__main__":
    unittest.main()
