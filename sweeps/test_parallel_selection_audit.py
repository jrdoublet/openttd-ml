"""Tests hors moteur. Aucun test ici ne compile/exécute Squirrel."""
from collections import Counter
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sweeps.parallel_selection_audit import (
    action_category, annual_window, audit_events, audit_file, collect,
    log_events, vehicle_profit_gbp,
)


def calibration(**overrides):
    event = dict(phase="line_calib", year="1972", age="3", line="7", mode="air",
                 pred_p="100", real_p="150", pred_amort="20", trains0="1", vehs="1",
                 seed=42, _company=0, _segment="$", _date="1973-01-01", _locator="L10")
    event.update(overrides)
    return event


def built(**overrides):
    event = dict(phase="project_built", line="7", mode="air", seed=42,
                 _company=0, _segment="$", _date="1970-05-03", _locator="L1",
                 rank="0", profit="110", cost="1000")
    event.update(overrides)
    return event


class SelectionAuditTests(unittest.TestCase):
    def test_units_raw_noai_gbp_and_unknown(self):
        self.assertEqual(vehicle_profit_gbp(256, "currency_fract"), 1)
        self.assertEqual(vehicle_profit_gbp(256, "GBP"), 256)
        self.assertEqual(vehicle_profit_gbp(-256, "currency_fract"), -1)
        with self.assertRaises(ValueError):
            vehicle_profit_gbp(1, "kGBP")

    def test_missing_and_nonfinite_are_not_zero(self):
        for value in (None, "", "nan", "inf", True):
            self.assertIsNone(vehicle_profit_gbp(value, "GBP"))
        self.assertEqual(vehicle_profit_gbp(0, "GBP"), 0)

    def test_real_zero_is_kept_but_missing_is_rejected(self):
        self.assertEqual(audit_events([calibration(real_p="0")])["identity_pairs"], 1)
        for value in (None, "NaN", "oops"):
            self.assertEqual(audit_events([calibration(real_p=value)])["identity_pairs"], 0)

    def test_closed_year_and_leap_year(self):
        w = annual_window(2000, 2)
        self.assertEqual((w["start"], w["end_exclusive"]), ("2000-01-01", "2001-01-01"))
        self.assertEqual(w["maturity"], "first_full_year_ramp_possible")
        self.assertEqual(annual_window(2050, 3)["exposure"], "full_calendar_year_by_build_year")

    def test_opening_partial_not_annualized(self):
        self.assertEqual(annual_window(1970, 1)["exposure"], "opening_year_date_unknown")
        self.assertEqual(annual_window(1970, 1, "1970-05-03")["exposure"], "partial_opening")
        self.assertEqual(annual_window(1970, 1, "1970-01-01")["exposure"], "full_calendar_year")
        self.assertEqual(annual_window(1970, None)["exposure"], "unknown")
        self.assertEqual(annual_window(1970, 1, "1971-01-01")["exposure"], "before_build")

    def test_invalid_years(self):
        for y in (None, -1, "bad", 1972.5, 9999):
            self.assertIsNone(annual_window(y, 2)["start"])

    def test_preserves_company_dates_and_raw_locator(self):
        text = "[script:4] [0] [I] OPEX 1973-1-2 C69_BOTTLENECK phase=line_calib year=1972 line=7 mode=air"
        e = list(log_events(text, "$/phase_b/openttd_output_raw"))[0]
        self.assertEqual(e["_company"], 0)
        self.assertEqual(e["_date"], "1973-01-02")
        self.assertEqual(e["_locator"], "$/phase_b/openttd_output_raw:L1")
        self.assertEqual(list(log_events(text.split("OPEX", 1)[1], "$")), [])

    def test_report_year_is_not_profit_year(self):
        r = audit_events([calibration(year="1973")])
        self.assertEqual(r["identity_pairs"], 0)
        self.assertEqual(r["rejected"]["inconsistent_report_year"], 1)

    def test_exact_build_line_binding(self):
        result = audit_events([built(), calibration()])
        p = result["pairs"][0]
        self.assertEqual(result["build_bindings"], 1)
        self.assertEqual(p["category"], "new_line_reported")
        self.assertEqual(p["build_binding"]["rank"], 0)
        self.assertEqual(p["predicted_net_gbp_per_year"], 100)
        self.assertEqual(p["build_binding"]["reported_project_profit_gbp_per_year"], 110)
        self.assertIsNone(p["election_bias_gbp_per_year"])

    def test_cross_company_phase_seed_repeat_mode_id_never_joined(self):
        for changes in ({"_company": 1}, {"_segment": "phase_b"}, {"seed": 999},
                        {"repeat": 1}, {"mode": "rail"}, {"line": "8"}, {"_company": None}):
            with self.subTest(changes=changes):
                self.assertEqual(audit_events([built(), calibration(**changes)])["build_bindings"], 0)

    def test_ambiguous_build_not_nearest_match(self):
        r = audit_events([built(), built(_date="1970-06-01"), calibration()])
        self.assertEqual(r["build_bindings"], 0)

    def test_future_and_age_inconsistent_build_rejected(self):
        for b in (built(_date="1974-01-01"), built(_date="1971-01-01")):
            self.assertEqual(audit_events([b, calibration()])["build_bindings"], 0)

    def test_duplicate_line_year_and_conflict(self):
        r = audit_events([calibration(), calibration(_locator="L20")])
        self.assertEqual((r["identity_pairs"], r["duplicate_line_year_rows"]), (1, 1))
        r = audit_events([calibration(), calibration(real_p="151")])
        self.assertEqual((r["identity_pairs"], r["conflicting_line_years"]), (0, 1))

    def test_duplicate_date_validation_is_order_independent(self):
        a, b = calibration(), calibration(_date="1974-01-01", _locator="L20")
        self.assertEqual(audit_events([a, b]), audit_events([b, a]))
        r = audit_events([a, b])
        self.assertEqual(r["rejected"]["inconsistent_report_year"], 1)
        self.assertEqual(r["identity_pairs"], 1)

    def test_collector_preserves_and_separates_structured_scopes(self):
        a, b = built(), calibration()
        a.pop("_segment")
        b.pop("_segment")
        r = audit_events(list(collect({"phase_a": {"events": [a]}, "phase_b": {"events": [b]}})))
        self.assertEqual(r["build_bindings"], 0)
        r = audit_events(list(collect({"runs": [{"events": [a]}, {"events": [b]}]})))
        self.assertEqual(r["build_bindings"], 0)
        self.assertEqual(list(collect([calibration(_segment="declared")]))[0]["_segment"], "declared")

    def test_calibration_normalizes_line_ids_and_integer_strings(self):
        r = audit_events([calibration(line=7, age="3.0"),
                          calibration(line="7", year="1973", age="4", _date="1974-01-01")])
        s = r["calibration_proxy_not_election_bias"][0]["summary"]["air"]
        self.assertEqual(s["lines"], 1)
        self.assertEqual(s["line_years"], 2)

    def test_bad_line_ids_not_coerced(self):
        for lid in (None, -1, "7.5", "rail|7,8", True):
            self.assertEqual(audit_events([calibration(line=lid)])["identity_pairs"], 0)

    def test_no_seed_or_company_cannot_deduplicate_line_years(self):
        e = calibration(seed=None, _company=None)
        self.assertEqual(audit_events([e])["identity_pairs"], 0)

    def test_proxy_reuses_existing_calibration_but_is_not_realized_net(self):
        r = audit_events([calibration()])
        summary = r["calibration_proxy_not_election_bias"][0]["summary"]["air"]
        self.assertEqual(summary["M1"], 1.3)
        self.assertEqual(summary["M2"], 1.3)
        self.assertIsNone(r["bias_by_category"]["unknown"]["mean_bias_gbp_per_year"])

    def test_proxy_excludes_missing_amort_and_partial_year(self):
        for e in (calibration(pred_amort=None), calibration(age="1"), calibration(vehs=None)):
            self.assertEqual(audit_events([e])["calibration_proxy_not_election_bias"], [])

    def test_proxy_company_and_phase_namespaced(self):
        r = audit_events([calibration(), calibration(_company=1), calibration(_segment="phase_b")])
        self.assertEqual(r["identity_pairs"], 3)
        self.assertEqual(len(r["calibration_proxy_not_election_bias"]), 3)

    def test_fleet_count_change_not_a_replacement_proof(self):
        r = audit_events([calibration(vehs="2")])
        self.assertEqual(r["pairs"][0]["category"], "unknown")
        self.assertIsNone(r["calibration_proxy_not_election_bias"][0]["summary"]["air"]["M2"])
        self.assertEqual(action_category(built(mode="fleet")), "fleet_action_unresolved")
        self.assertEqual(action_category(built(action="replacement")), "replacement")
        self.assertEqual(action_category(built(action="reinforcement")), "reinforcement")

    def test_station_keys_signs_and_company_profit_inventory_only(self):
        c = Counter()
        data = {"profit_year": 99, "profit_year_coverage": "complete", "signs": {"a": "AF|7|1|100"},
                "lines": [{"line_key_local": "air|7,8", "profit_last_year_gbp": 50}]}
        self.assertEqual(list(collect(data, inventory=c)), [])
        self.assertEqual(c["company_profit_records"], 1)
        self.assertEqual(c["station_key_line_records"], 1)
        self.assertEqual(c["parsed_sign_strings_no_owner_binding"], 1)

    def test_jsonl_provenance_and_corruption(self):
        p = Path("events.jsonl")
        content = (json.dumps(calibration()) + "\n").encode()
        with patch.object(Path, "is_file", return_value=True), patch.object(Path, "read_bytes", return_value=content):
            r = audit_file(p)
            self.assertEqual(r["audit"]["pairs"][0]["source_locator"], "L1")
            self.assertEqual(len(r["sha256"]), 64)
        with patch.object(Path, "is_file", return_value=True), patch.object(Path, "read_bytes", return_value=content + b"{"):
            r = audit_file(p)
            self.assertEqual(r["status"], "unreadable")
            self.assertNotIn("audit", r)
        with patch.object(Path, "is_file", return_value=False):
            self.assertEqual(audit_file(p.with_name("absent.json"))["status"], "missing")


if __name__ == "__main__":
    unittest.main()