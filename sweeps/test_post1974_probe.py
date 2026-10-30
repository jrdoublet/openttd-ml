"""Fixture contracts for non-invasive post-1974 instrumented-log parsing."""
import json
from pathlib import Path
import tempfile
import unittest

try:
    from sweeps.post1974_probe import parse_log
except ImportError:
    from post1974_probe import parse_log


class TestPost1974Probe(unittest.TestCase):
    def test_unique_od_lower_bound_and_paid_not_quote(self):
        sample = "\n".join([
            "INFO: OPEX 1979-5-1 PROJECT_CHOSEN mode=rail kind=freight cargo=7 src=12 dst=28 cost=90000 profit=15000",
            "INFO: OPEX 1979-5-1 RAIL_ATTEMPT src=12 dst=28 kind=freight pred_profit=15000 quote=90000 actual=7000 ok=0 reason=SITEAB",
            "INFO: OPEX 1979-5-2 RAIL_ATTEMPT src=12 dst=28 kind=freight pred_profit=15000 quote=90000 actual=0 ok=0 reason=SITEAB",
            "INFO: OPEX 1979-5-2 RAIL_ATTEMPT src=12 dst=30 kind=freight pred_profit=18000 quote=140000 actual=120000 ok=1 reason=OK",
            "INFO: OPEX 1979-5-2 AIR_BUILD src=54 dst=42 cost=300000 profit=15000",
            "INFO: OPEX 1979-5-2 AIR_BUILD src=42 dst=54 cost=300000 profit=15000",
            "INFO: OPEX 1979-5-2 C78_SLOT phase=projects_pass pass=10 air_candidates=0 available=2000000",
            "INFO: OPEX 1979-5-3 C78_SLOT phase=pass_stop reason=rail_search",
            "INFO: OPEX 1979-5-3 V233L_REJECT src=12 dst=28 reason=second_track",
            "INFO: OPEX 1979-6-3 V284 action=reject reason=waiting",
            "INFO: OPEX 1975-5-1 ESTIM_DECISION mode=air stage=mode_top_0 id=air|42|54 reason=excluded_or_topk",
            "INFO: OPEX 1980-1-1 C63_INVEST phase=spend year=1979 mode=rail planned_ok=140000 actual_ok=120000 n_ok=1 planned_fail=180000 actual_fail=7000 n_fail=2",
            "INFO: OPEX 1980-1-1 C63_INVEST phase=opp year=1979 absent_n=1 absent_d=20 invalid_n=0 invalid_d=0",
        ])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "probe.log"
            path.write_text(sample, encoding="utf-8")
            data = parse_log(path)
        year = data["years"]["1979"]
        self.assertEqual(year["event_counts"]["RAIL_ATTEMPT"], 3)
        self.assertEqual(year["rail_min_distinct_od_kind"], 2)
        self.assertEqual(year["rail_reason_counts"], {"SITEAB": 2, "OK": 1})
        self.assertEqual(year["rail_success_actual_paid_observed"], 120000)
        self.assertEqual(year["air_min_distinct_od"], 2)  # directed reverse leg is distinct
        self.assertEqual(len(data["air_crossyear_witnesses"]), 2)
        self.assertEqual(year["c78_limited_trace"]["passes_no_air_candidates"], 1)
        self.assertEqual(year["c78_limited_trace"]["cash_available_min"], 2000000)
        self.assertEqual(year["c78_limited_trace"]["pass_stop_reasons"], {"rail_search": 1})
        self.assertEqual(year["v233l_reject_distinct_od"], 1)
        self.assertEqual(year["chosen_events_by_mode"]["rail"], 1)
        self.assertEqual(year["chosen_unique_od_mode_kind_cargo"], 1)
        self.assertEqual(year["rail_attempt_details"][0]["quote"], 90000)
        self.assertEqual(year["rail_attempt_details"][0]["actual"], 7000)
        self.assertEqual(year["rail_attempt_details"][0]["ok"], False)
        self.assertEqual(year["c63_mature_lines_by_mode"]["rail"]["n"], 0)
        self.assertEqual(data["rail_crossyear_witnesses"][0]["physically_built"], False)
        self.assertEqual(year["v284_events_by_action"]["reject"], 1)
        self.assertEqual(data["years"]["1975"]["event_counts"]["ESTIM_DECISION"], 1)
        self.assertEqual(year["c63_spend_by_mode"]["rail"]["actual_fail"], 7000)
        self.assertEqual(data["years"]["1978"]["c63_spend_by_mode"], None)

    def test_freight_direction_and_cross_year_physical_proof(self):
        sample = "\n".join([
            "INFO: OPEX 1977-2-1 PROJECT_CHOSEN mode=rail kind=freight cargo=GOOD src=10 dst=20 cost=900 profit=300",
            "INFO: OPEX 1977-5-1 RAIL_ATTEMPT src=10 dst=20 kind=freight actual=1300 ok=1 reason=OK pred_profit=200",
            "INFO: OPEX 1977-5-1 RAIL_BUILD line=63 src=10 dst=20 cargo=GOOD cost=1300",
            "INFO: OPEX 1978-2-1 PROJECT_CHOSEN mode=rail kind=freight cargo=GOOD src=20 dst=10 cost=900 profit=300",
            "INFO: OPEX 1978-7-1 RAIL_ATTEMPT src=20 dst=10 kind=freight actual=-1 ok=0 reason=NOPLAN2 pred_profit=250",
        ])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "probe.log"
            path.write_text(sample, encoding="utf-8")
            data = parse_log(path)
        witness = {(w["src"], w["dst"]): w for w in data["rail_crossyear_witnesses"]}
        self.assertEqual(len(witness), 2)
        self.assertEqual(witness[("10", "20")]["classification"], "build_confirmed")
        self.assertEqual(witness[("10", "20")]["actual_success_paid"], 1300)
        self.assertEqual(witness[("10", "20")]["builds"][0]["line"], 63)
        self.assertEqual(witness[("20", "10")]["classification"], "attempt_failed_no_build_proof")
        self.assertEqual(data["years"]["1977"]["rail_min_distinct_od_kind"], 1)

    def test_published_seed42_funnel_is_internally_consistent(self):
        """Checks the attached immutable evidence, not a fresh simulation."""
        path = Path(__file__).resolve().parents[1] / "docs" / "post1974_entonnoir_seed42_1x10_20261030.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        witnesses = data["rail_crossyear_witnesses"]
        self.assertEqual(len(witnesses), 9)
        self.assertEqual(sum(w["classification"] == "build_confirmed" for w in witnesses), 3)
        self.assertEqual(sum(w["classification"] == "attempt_failed_no_build_proof" for w in witnesses), 5)
        self.assertEqual(sum(w["classification"] == "selected_no_completed_attempt" for w in witnesses), 1)
        self.assertEqual(sum(w["actual_success_paid"] for w in witnesses), 411212)
        self.assertEqual(data["years"]["1977"]["c63_spend_by_mode"]["rail"]["actual_ok"], 411212)
        self.assertIsNone(data["years"]["1979"]["c63_spend_by_mode"])
        self.assertEqual(data["years"]["1978"]["c78_limited_trace"]["projects_pass_events"], 92)
        self.assertEqual(data["years"]["1978"]["c78_limited_trace"]["passes_no_air_candidates"], 92)
        self.assertEqual(len(data["air_crossyear_witnesses"]), 2)
        self.assertEqual(sum(len(a["built"]) for a in data["air_crossyear_witnesses"]), 3)
        realized = {row["line"]: row["real_p"] for row in data["years"]["1978"]["c63_lines"]}
        self.assertEqual({k: realized[k] for k in (62, 63, 65)}, {62: -2882, 63: 30843, 65: 25294})


if __name__ == "__main__":
    unittest.main()
