"""Tests statiques du shadow C119 (aucun changement décisionnel)."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_c119_air_income_shadow import (
    MAIL_PAYMENT,
    PAX_PAYMENT,
    aaa_rated_production,
    cargo_income,
    direction_balance,
    engine_mail_ratios,
    enrich,
    mature_load_factors,
    script_air_speed,
)
from campaign_freeze import parse_ai_settings


INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
BUILDER_AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"


class TestC119AirIncomeShadow(unittest.TestCase):
    def test_decision_flag_defaults_off_and_is_loaded(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["c119_air_income_model"], 0)
        self.assertIn("C119_AIR_INCOME_MODEL <- false;", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn(
            'C119_AIR_INCOME_MODEL = AIController.GetSetting("c119_air_income_model") != 0;',
            SETTINGS.read_text(encoding="utf-8"),
        )

    def test_c119_payment_time_is_delivery_only(self):
        src = BUILDER_AIR.read_text(encoding="utf-8")
        start = src.index("function OpexC119AirIncomeDays")
        end = src.index("function OpexC121EndpointAirportType", start)
        body = src[start:end]
        self.assertIn("AIEngine.GetMaxSpeed(plane.id)", body)
        self.assertIn("(flightDistance + 30) * 664", body)
        self.assertNotIn("airportDelayDays", body)
        self.assertNotIn("roundTripDays", body)

    def test_c119_changes_payment_inputs_not_cycle_or_fleet(self):
        src = BUILDER_AIR.read_text(encoding="utf-8")
        start = src.index("function OpexAirEconomics")
        end = src.index("function OpexAirTargetEconomics", start)
        body = src[start:end]
        self.assertIn("local c119Income = C119_AIR_INCOME_MODEL && paymentDistance > 0;", body)
        self.assertIn("OpexAirTripModel(plane.speed, plane.capacity, distance", body)
        self.assertIn("local incomeDistance = c119Income ? paymentDistance : distance;", body)
        self.assertIn("local targetPlanes = OpexCeilDiv(monthlyPax, capacityPerPlane.tointeger());", body)
        self.assertNotIn("mailCapacity =", body)

    def test_all_three_prebuild_arms_supply_manhattan_payment_distance(self):
        src = BUILDER_AIR.read_text(encoding="utf-8")
        for token in (
            "AIMap.DistanceManhattan(sites[a].anchor, sites[b].anchor)",
            "AIMap.DistanceManhattan(hub.anchor, site.anchor)",
            "AIMap.DistanceManhattan(hub1.anchor, hub2.anchor)",
        ):
            self.assertIn(token, src)

    def test_base_engine_speed_replay_matches_noai_scale(self):
        self.assertEqual(script_air_speed(223), 236)
        self.assertEqual(script_air_speed(228), 236)

    def test_shorter_payment_time_never_reduces_default_passenger_income(self):
        self.assertGreaterEqual(
            cargo_income(214, 28, PAX_PAYMENT),
            cargo_income(214, 104, PAX_PAYMENT),
        )

    def test_mail_payment_uses_independent_cargo_curve(self):
        self.assertNotEqual(
            cargo_income(214, 60, MAIL_PAYMENT),
            cargo_income(214, 60, PAX_PAYMENT),
        )

    def test_engine_mail_ratio_uses_capacity_not_realised_mail_per_pax(self):
        c117 = {"rows": [{"events": [{
            "engine": 223,
            "seat_legs": 2200,
            "mail_seat_legs": 400,
            "mixed_engine_samples": 0,
        }]}]}
        ratios = engine_mail_ratios(c117)
        self.assertAlmostEqual(ratios[223], 40 / 220)
        self.assertLess(ratios[223], 0.344)

    def test_time_and_mail_are_independent_shadows(self):
        rows = [{
            "seed": 42,
            "line": 7,
            "revenue_per_pax": 200.0,
            "pred_revenue_per_carried": 100.0,
            "actual_leg_days": 60.0,
            "pred_oneway_days": 104.0,
            "pred_carried": 50.0,
            "revenue_pm": 7000.0,
        }]
        static = {(42, 7): {
            "distance": 214,
            "engine": 223,
            "base_monthly": 500,
        }}
        out = enrich(rows, static, {223: 40 / 220}, 0.15)[0]
        self.assertGreater(out["time_gain_vs_legacy"], 1.0)
        self.assertNotEqual(out["mail_gain_vs_legacy"], 1.0)
        self.assertGreater(out["combined_gain_vs_legacy"], out["time_gain_vs_legacy"])

    def test_aaa_station_rate_formula_is_reported_separately(self):
        rows = [{
            "engine_speed": 236,
            "base_monthly": 500,
            "pred_carried": 100,
        }]
        out = aaa_rated_production(rows, rich_bonus=False)
        self.assertAlmostEqual(
            out["rated_over_input_production"]["median"],
            207 / 255,
            places=6,
        )

    def test_direction_balance_does_not_claim_load_balance(self):
        c117 = {"rows": [{"seed": 42, "events": [{
            "line": 7, "age_bucket": 6, "period_days": 30,
            "trips_a": 9, "trips_b": 10,
        }]}]}
        self.assertEqual(direction_balance(c117)["median"], 0.9)

    def test_mature_load_factors_keep_pax_and_mail_separate(self):
        c117 = {"rows": [{"seed": 42, "events": [{
            "line": 7, "age_bucket": 6, "period_days": 30,
            "pax": 100, "seat_legs": 300,
            "mail": 90, "mail_seat_legs": 100,
        }]}]}
        out = mature_load_factors(c117)
        self.assertAlmostEqual(out["pax_load_factor"]["median"], 1 / 3, places=6)
        self.assertEqual(out["mail_load_factor"]["median"], 0.9)


if __name__ == "__main__":
    unittest.main()
