"""Contract for the 2026-10-23 rebased parameter removal.

The local experimental tree predates PO01C, PO03/C77 and PO02 adoption:
their settings must NOT be treated as removals. This test deliberately
checks the published interface, not the number in that old local tree.
"""

from pathlib import Path
import re
import unittest
from n75_mc_legacy import historical_info


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"

# 43 genuine retirements. Do not accidentally reintroduce old opt-in policies.
RETIRED = frozenset((
    "air_flotte1_shadow",
    "c122_air_regime_shadow",
    "c122_air_threat_probe",
    "c122_air_threat_retry",
    "c67_water_exposure_probe",
    "c83_fixes",
    "c83_local_repair",
    "c83_preempt_open",
    "debug_signs",
    "decision_log",
    "probe_candidates_rail",
    "probe_candidates_road",
    "probe_catalogue",
    "probe_cost",
    "probe_event_backlog",
    "probe_events",
    "probe_loop_ops",
    "probe_portfolio",
    "probe_rail_search",
    "probe_scheduler",
    "probe_select_reject",
    "probe_span_trace",
    "probe_vehicle_lost",
    "rail_cal",
    "rail_failure_audit",
    "v133_air_build_retry",
    "v134_air_p2p_saturated_hub",
    "v177_rail_pax_min_dist",
    "v182_rail_freight_min_dist",
    "v195_v182_years",
    "v211_rivals_log",
    "v216_probe",
    "v233_goods_graft",
    "v233_pending_continue",
    "v264_convergent_freight",
    "v294_rail_defer",
    "v294_rail_reverse_probe",
    "v295_astar_fast",
    "v296_astar_native",
    "v296_rail_batch_build",
    "v307_abnd_autopsy",
    "v308_carto_probe",
    "v309_idle_probe",
))

UNADOPTED_ADDITIONS = frozenset((
    "air_roi_renfort1_itt",
    "rail_reverse_astar_iters",
    "v269_rail_long_max",
))


def declared(text):
    return {
        name: body
        for body in re.findall(r"AddSetting\s*\(\s*\{(.*?)\}\s*\)", text, re.S)
        if (m := re.search(r'\bname\s*=\s*"([^"]+)"', body))
        for name in (m.group(1),)
    }


class TestParameterRetirement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = (ROOT / "info.nut").read_text(encoding="utf8")
        cls.settings = (ROOT / "settings.nut").read_text(encoding="utf8")
        cls.config = declared(cls.info)

    def test_exact_size_after_retirement(self):
        self.assertEqual(len(RETIRED), 43)
        # 58 historiques + N75 adopte + P6/P3/FP2/P2/P1 opt-in + FP1/V286/C75.
        self.assertEqual(len(self.config), 67)
        self.assertIn("n75_multi_cargo", self.config)
        self.assertIn("p6_air_firstline_window", self.config)
        self.assertIn("air_fleet_yield_rightsize", self.config)
        self.assertIn("front_pax2_bounded_overlap", self.config)
        self.assertIn("rail_cargo_opportunity_rank", self.config)
        self.assertIn("rail_long_value_rank", self.config)
        self.assertIn("front_pax1_bounds_probe", self.config)
        self.assertIn("v286_rail_flow_probe", self.config)
        self.assertIn("c75_year_ledger_skip", self.config)
        p2_setting = self.config["rail_cargo_opportunity_rank"]
        self.assertRegex(p2_setting, r"\bmin_value\s*=\s*0\b")
        self.assertRegex(p2_setting, r"\bmax_value\s*=\s*2\b")
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(p2_setting, rf"\b{level}_value\s*=\s*0\b")
        self.assertEqual(len(declared(historical_info(self.info))), 58)

    def test_retired_settings_have_no_declarations_or_direct_reads(self):
        for name in sorted(RETIRED):
            with self.subTest(name=name):
                self.assertNotIn(name, self.config)
                self.assertNotRegex(
                    self.settings, r'GetSetting\s*\(\s*"' + re.escape(name) + r'"\s*\)'
                )

    def test_unadopted_wip_settings_not_imported(self):
        for name in sorted(UNADOPTED_ADDITIONS):
            with self.subTest(name=name):
                self.assertNotIn(name, self.config)

    def test_adopted_defaults_survive_rebase(self):
        for name, expected in (
            ("c77_intent_defer", "2"),
            ("station_plan_precheck", "1"),
            ("po01c_regen_split", "1"),
        ):
            with self.subTest(name=name):
                self.assertIn(name, self.config)
                body = self.config[name]
                for level in ("easy", "medium", "hard", "custom"):
                    self.assertRegex(
                        body, rf"\b{level}_value\s*=\s*{expected}\b"
                    )


if __name__ == "__main__":
    unittest.main()
