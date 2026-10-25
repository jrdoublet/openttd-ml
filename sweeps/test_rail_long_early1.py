"""Contrats RAIL-LONG-EARLY-1 : seconde borne fret V269, sans effet par defaut."""

from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class TestRailLongEarly1(unittest.TestCase):
    def test_only_one_new_setting_and_all_defaults_zero(self):
        info = source("info.nut")
        m = re.search(r'name = "v269_rail_long_max"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(m)
        block = m.group(1)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"{difficulty}_value\s*=\s*0\b")
        self.assertIn("max_value = 512", block)
        self.assertIn("V269_RAIL_LONG_MAX <- 0;", source("globals_pre.nut"))
        settings = source("settings.nut")
        self.assertEqual(settings.count('GetSetting("v269_rail_long_max")'), 1)
        self.assertIn("railLongMax >= 250 && railLongMax <= 512", settings)

    def test_normal_rail_cap_and_calibration_unchanged(self):
        self.assertIn("V294_RAIL_DIST_DECOUPLE <- 200;", source("globals_pre.nut"))
        self.assertIn("V269_RAIL_MAX_DIST <- 250;", source("globals_pre.nut"))
        self.assertIn("V269_RAIL_LATE_RELAX <- 5;", source("globals_pre.nut"))
        info = source("info.nut")
        m = re.search(r'name = "v294_rail_dist_decouple"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(m)
        self.assertIn("easy_value = 200", m.group(1))
        self.assertIn("rail_cal", info)

    def test_secondary_cap_is_freight_only_and_gated(self):
        candidates = source("candidates.nut")
        self.assertIn("function OpexRailFreightMaxDistance(catalog, bounds, cargo = null)", candidates)
        self.assertIn("if (V269_RAIL_LATE_RELAX > 0 && V269_RELAXED)", candidates)
        self.assertIn("cargo == V269_RAIL_LONG_CARGO", candidates)
        self.assertIn("distance <= OpexRailFreightMaxDistance(catalog, bounds, cargo)", candidates)
        self.assertIn("if (distance > bounds.railMax)", candidates)  # pax
        self.assertIn("manhattan <= b.railMax", candidates)  # AIR_ONLY
        orch = source("orchestrator.nut")
        self.assertIn("year >= OPEX_START_YEAR + V269_RAIL_LATE_RELAX && cash >= V269_IDLE_CASH_MIN", orch)
        self.assertIn("if (startable >= V217_POOL_MIN)", orch)
        self.assertIn("if (year < OPEX_START_YEAR + 2) return;", orch)

    def test_v276_late_request_persists_after_relax_flag_resets(self):
        v276 = source("candidates_v276.nut")
        self.assertIn("v269FreightCap = freightCap", v276)
        self.assertIn('catalog.bounds.v269FreightCap <- request.v269FreightCap;', v276)
        self.assertIn("OpexRailFreightMaxDistance(s.catalog, bounds, u.cargo)", v276)  # grille
        self.assertIn("distance > OpexRailFreightMaxDistance(s.catalog, s.catalog.bounds, u.cargo)", v276)
        self.assertIn("catalog.bounds.v269FreightCap <- request.v269FreightCap;", v276)
        self.assertIn("catalog.bounds.v269FreightCargo <- request.v269FreightCargo;", v276)
        self.assertIn('("v269FreightCap" in bounds)', source("candidates.nut"))
        self.assertNotIn("catalog.v269FreightCap <-", v276)
        self.assertNotIn("catalog.v269FreightCargo <-", v276)
        self.assertIn("if (longFreight &&", v276)  # file secondaire, curseur actif
        self.assertIn("if (V269_RAIL_LATE_RELAX > 0) V269_RELAXED = false;", source("orchestrator.nut"))

    def test_trace_cargo_year_distance_with_probe_only(self):
        candidates = source("candidates.nut")
        self.assertIn("DECISION_LOG && V269_RAIL_LONG_MAX > 0 && distance > 200", candidates)
        self.assertIn('OpexDecide("RAIL_LONG_SCREEN"', candidates)
        self.assertIn('OpexDecide("RAIL_LONG_CANDIDATE"', candidates)
        self.assertIn('" cargo=" + AICargo.GetCargoLabel(cargo)', candidates)
        self.assertIn('" dist=" + distance', candidates)


if __name__ == "__main__":
    unittest.main()
