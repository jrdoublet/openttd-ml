"""AIR physical payment-time contract, before Squirrel integration tests."""
from pathlib import Path
import math
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(filename):
    return (AI / filename).read_text(encoding="utf-8")


class PhysicalPaymentDaysTests(unittest.TestCase):
    def test_setting_is_on_by_default(self):
        setting = read("info.nut").split('name = "air_c121_physical_payment_days",')[1].split("});")[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 1", setting)
        self.assertIn("AIR_C121_PHYSICAL_PAYMENT_DAYS <- false;", read("globals_pre.nut"))
        self.assertEqual(read("settings.nut").count(
            'AIController.GetSetting("air_c121_physical_payment_days")'), 1)

    def test_rounding_uses_physical_one_way_not_magic_offset(self):
        body = read("air_economics_c121.nut").split(
            "function OpexC121PhysicalPaymentDays(trip)")[1].split("}\n", 1)[0]
        self.assertIn("trip.physicalOneWayDays", body)
        self.assertIn("days.tofloat() < trip.physicalOneWayDays", body)
        self.assertNotIn("+ 30", body)
        for d in (0.01, 1.0, 1.01, 26.89457, 300.01):
            rounded = max(1, math.ceil(d))
            self.assertGreaterEqual(rounded, d)
            self.assertLess(rounded - d, 1.0)

    def test_all_c121_income_paths_use_switch(self):
        econ = read("air_economics_c121.nut")
        self.assertEqual(econ.count("OpexC121PhysicalPaymentDays("), 6)
        self.assertEqual(econ.count("AIR_C121_PHYSICAL_PAYMENT_DAYS"), 5)
        self.assertIn("OpexC121PhysicalPaymentDays(ctx.trip)", econ)
        self.assertIn("OpexC119AirIncomeDays(plane, plan.distance)", econ)

    def test_trip_includes_airport_manoeuvres(self):
        econ = read("air_economics_c121.nut")
        self.assertIn("local oneWayDays = flightDays + maneuverDays;", econ)
        self.assertIn("ground * OpexDaysPerTile(taxiSpeed, tpd)", econ)
        self.assertIn("physicalOneWayDays = physical.oneWayDays", econ)
        self.assertIn("roundTripDays = 2.0 * physical.oneWayDays + hubDelayA + hubDelayB;", econ)

    def test_off_keeps_legacy_proxy(self):
        econ = read("air_economics_c121.nut")
        self.assertIn("((flightDistance + 30) * 664)", econ)
        self.assertEqual(econ.count("OpexC119AirIncomeDays(plane, plan.distance)"), 5)
        self.assertIn("AICargo.GetCargoIncome(catalog.paxCargo, paymentDistance, incomeDays)", econ)


if __name__ == "__main__":
    unittest.main()
