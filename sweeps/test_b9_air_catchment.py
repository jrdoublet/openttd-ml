"""Contrats B9/G4 : géométrie STNN et sonde AIR strictement passive."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

try:
    from bench_1v1_5y_20seeds import _station_route_index
except ImportError as exc:  # openttdlab absent hors du conteneur openttd-lab
    raise unittest.SkipTest(f"harnais indisponible hors Docker : {exc}")
from campaign_freeze import parse_ai_settings

INFO = ROOT / "ai" / "OpexAI" / "info.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
PROBES = ROOT / "ai" / "OpexAI" / "probes.nut"
BUILDER = ROOT / "ai" / "OpexAI" / "builder_air.nut"
FIXTURE = ROOT / "sweeps" / "fixtures" / "c66_control_fixture_15_3.json"

class TestB9AirCatchment(unittest.TestCase):
    def test_probe_is_default_off_and_loaded_once(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["probe_events"], 0)
        self.assertIn("AIR_CATCHMENT_PROBE <- false;", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn(
            "AIR_CATCHMENT_PROBE = probeEvents;",
            SETTINGS.read_text(encoding="utf-8"),
        )

    def test_probe_has_dedicated_logger(self):
        probes = PROBES.read_text(encoding="utf-8")
        start = probes.index("function OpexAirCatchmentLog")
        self.assertIn("if (!AIR_CATCHMENT_PROBE) return;", probes[start:start + 500])

    def test_probe_runs_after_success_and_before_reconciliation(self):
        src = BUILDER.read_text(encoding="utf-8")
        probe = src.index('OpexAirCatchmentLog("AIR_CATCHMENT_BUILD"')
        reconcile = src.index("OpexAirReconcileActualBuild(catalog, plan, result);")
        success = src.index("result.ok = true;", src.index("function OpexBuildAirRoute"))
        self.assertLess(success, probe)
        self.assertLess(probe, reconcile)
        self.assertIn("joinedMonthlyPaxA = 0", src)
        self.assertIn("joinedMonthlyPaxB = 0", src)

    def test_probe_keeps_measurement_dimensions_separate(self):
        src = BUILDER.read_text(encoding="utf-8")
        for token in (
            "airport_pax_prod=", "union_pax_prod=", "airport_mail_prod=",
            "union_mail_prod=", "base_source=", "base_monthly=",
            "reserve_stop_cost=", "actual_stop_cost=", "overlap_overcount_pax=",
            "model_joined_pax=", "model_error_pax=", "probe_ops=",
        ):
            self.assertIn(token, src)

    def test_station_index_exposes_airport_geometry_from_stnn(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        chunks = None
        stack = [fixture]
        while stack and chunks is None:
            current = stack.pop()
            if not isinstance(current, dict):
                continue
            if "STNN" in current:
                chunks = current
                break
            stack.extend(value for value in current.values() if isinstance(value, dict))
        self.assertIsNotNone(chunks)
        stations = _station_route_index(chunks)
        airports = [s["airport"] for s in stations.values() if s.get("airport") is not None]
        self.assertTrue(airports)
        sample = airports[0]
        for key in ("tile", "width", "height", "type"):
            self.assertIn(key, sample)
        self.assertIsInstance(sample["width"], int)
        self.assertGreater(sample["width"], 0)

    def test_air_default_planning_uses_named_proxy_not_duplicated_literal(self):
        src = BUILDER.read_text(encoding="utf-8")
        self.assertNotIn("* 22", src)
        self.assertGreaterEqual(src.count("TOWN_CATCHMENT_SHARE_PCT"), 4)
        self.assertIn(
            "local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;",
            src,
        )
        self.assertIn("town_population_proxy", src)

    def test_joined_stop_reconciliation_uses_union_marginal(self):
        src = BUILDER.read_text(encoding="utf-8")
        self.assertIn("function OpexAirJoinedMarginalProduction", src)
        self.assertIn("joinedRawMonthlyPaxA = 0", src)
        self.assertIn("result.joinedRawMonthlyPaxA = joinedA.monthlyPax;", src)
        self.assertIn("result.joinedMonthlyPaxA = OpexAirJoinedMarginalProduction(", src)
        self.assertIn(
            'local joinedMonthly = OPEX_AIR_PLAN_PAD && ("joinedMonthlyPax" in result)',
            src,
        )
        ai = BUILDER.parent
        self.assertIn("OPEX_AIR_PLAN_PAD <- false;", (ai / "globals_pre.nut").read_text(encoding="utf-8"))
        self.assertIn("OPEX_AIR_PLAN_PAD = false;", (ai / "settings.nut").read_text(encoding="utf-8"))
        reserve = src[src.index("function OpexAirReserveJoinedStops"):src.index(
            "function OpexAirAddPlane"
        )]
        self.assertIn("plan.joinedStopReserve <- 0;", reserve)
        self.assertNotIn("economics.capital +=", reserve)

if __name__ == "__main__":
    unittest.main()
