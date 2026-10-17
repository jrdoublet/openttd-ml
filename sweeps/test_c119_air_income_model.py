"""Contrats du helper C119 partage et du retrait de son traitement autonome."""

from pathlib import Path
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air

ROOT = Path(__file__).resolve().parents[1]
AIR = read_builder_air()
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")

def function_body(source: str, name: str, next_name: str | None = None) -> str:
    start = source.index(f"function {name}")
    return source[start:] if next_name is None else source[start:source.index(f"function {next_name}", start)]

class TestC119AirIncomeModel(unittest.TestCase):
    def test_standalone_treatment_is_removed(self):
        self.assertNotIn("C119_AIR_INCOME_MODEL", GLOBALS + SETTINGS + AIR)
        self.assertNotIn('name = "c119_air_income_model"', INFO)

    def test_payment_time_is_engine_and_geometry_derived(self):
        body = function_body(AIR, "OpexC119AirIncomeDays", "OpexAirEconomics")
        self.assertIn("AIEngine.GetMaxSpeed(plane.id)", body)
        self.assertIn("flightDistance + 30", body)
        self.assertIn("664", body)
        self.assertIn("speed * 24 * dayLengthFactor", body)
        self.assertIn('"GetDayLengthFactor" in AIDate', body)

    def test_legacy_cycle_and_fleet_economics_remain(self):
        body = function_body(AIR, "OpexAirEconomics", "OpexAirReconcileActualBuild")
        self.assertIn("local incomeDays = OpexCeilDiv(oneWayDays, 1);", body)
        self.assertIn("OpexAirFarePerPax(catalog, plane, distance, incomeDays)", body)
        self.assertIn("OpexAirTripModel(plane.speed, plane.capacity, distance, plane.id, airport.type,", body)
        self.assertNotIn("paymentDistance", body)
        self.assertIn("local targetPlanes = OpexCeilDiv(monthlyPax, capacityPerPlane.tointeger());", body)
        self.assertIn("local carried = (offered < monthlyCapacity ? offered : monthlyCapacity).tointeger();", body)

    def test_mail_model_is_not_part_of_c119(self):
        fare = function_body(AIR, "OpexAirFarePerPax", "OpexC119AirIncomeDays")
        self.assertNotIn("C119_AIR_INCOME_MODEL", fare)
        self.assertIn("local mailPct = 15;", fare)

    def test_c84_target_fleet_helpers_are_removed(self):
        self.assertNotIn("function OpexAirTargetEconomics", AIR)
        self.assertNotIn("function OpexAirExistingLineMarginalEconomics", AIR)
        self.assertNotIn("C84_AIR_TARGET_FLEET", AIR)
        self.assertNotIn('name = "c84_air_target_fleet"', INFO)

if __name__ == "__main__":
    unittest.main()
