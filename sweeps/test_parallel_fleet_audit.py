"""Fixtures synthétiques uniquement ; ni moteur, ni VM Squirrel, ni écritures."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sweeps.parallel_fleet_audit import analyse_file, analyse_payload, events_from_log, number


def log(day, fields, tag="C50_CHRONO", owner=0):
    return f"[script:4] [{owner}] [I] OPEX {day} {tag} {fields}"


def annual(year, profit, revenue, vehicles, age, owner=0):
    return log(f"{year + 1}-1-2", f"phase=line_profit mode=air line=3 year={year + 1} "
               f"profit_year={year} profit={profit} rev={revenue} vehs={vehicles} age={age}", owner=owner)


def fixture(profit=180, revenue=260):
    return [annual(1971, 100, 150, 1, 2),
            log("1972-5-2", "phase=fleet_built mode=air line=3 added=1 total=2 want=1"),
            log("1972-5-2", "action=grow line=3 added=1 want=1 price=30000 profit=80", "FLEET_PROJECT"),
            annual(1972, 130, 180, 2, 3), annual(1973, profit, revenue, 2, 4)]


def report(lines):
    return analyse_payload({"seed": 42, "openttd_output_raw": "\n".join(lines)})["streams"][0]


class FleetAuditTests(unittest.TestCase):
    def test_full_years_and_units_not_partial_purchase_year(self):
        row = report(fixture())["purchases"][0]
        self.assertEqual(row["before"]["year"], 1971)
        self.assertEqual(row["after"]["year"], 1973)
        self.assertEqual(row["delta_profit_gbp_per_year"], 80)
        self.assertEqual(row["delta_revenue_proxy_gbp_per_year"], 110)
        self.assertEqual(row["purchase_capital_estimate_gbp"], 30000)
        self.assertEqual(row["signal"], "positive_before_after_signal")
        self.assertEqual(row["economic_verdict"], "not_identified_no_counterfactual")
        self.assertIsNone(row["actual_purchase_cost_gbp"])

    def test_zero_and_negative_are_observations(self):
        for profit in (0, -30):
            row = report(fixture(profit, 140))["purchases"][0]
            self.assertEqual(row["delta_profit_gbp_per_year"], profit - 100)
            self.assertEqual(row["signal"], "capital_at_risk_signal")

    def test_missing_is_not_zero(self):
        lines = fixture()
        lines[-1] = lines[-1].replace("profit=180", "profit=unknown")
        row = report(lines)["purchases"][0]
        self.assertIsNone(row["delta_profit_gbp_per_year"])
        self.assertEqual(row["signal"], "insufficient_observations")
        self.assertTrue(all(v is None for v in row["service_measurements"].values()))

    def test_nonfinite_values_rejected(self):
        for value in (None, True, "NaN", "Infinity", "missing"):
            self.assertIsNone(number(value))
        self.assertEqual(number("0"), 0)

    def test_partial_opening_year_not_full(self):
        lines = fixture()
        lines[0] = lines[0].replace("age=2", "age=1")
        row = report(lines)["purchases"][0]
        self.assertIn("no_full_pre_year", row["blockers"])
        self.assertIsNone(row["delta_profit_gbp_per_year"])

    def test_no_post_year_no_extrapolation(self):
        row = report(fixture()[:-1])["purchases"][0]
        self.assertIn("no_full_post_year", row["blockers"])
        self.assertIsNone(row["delta_profit_gbp_per_year"])

    def test_other_purchase_blocks_attribution(self):
        lines = fixture() + [log("1973-4-1", "phase=fleet_built mode=air line=3 added=1 total=3 want=1")]
        self.assertIn("other_fleet_events_in_window", report(lines)["purchases"][0]["blockers"])

    def test_company_is_authoritative_not_script_number(self):
        lines = fixture()
        lines[-1] = lines[-1].replace("[0] [I]", "[1] [I]")
        self.assertIn("no_full_post_year", report(lines)["purchases"][0]["blockers"])

    def test_missing_owner_not_inferred(self):
        row = report(["OPEX " + line.split("OPEX ", 1)[1] for line in fixture()])["purchases"][0]
        self.assertIsNone(row["company"])
        self.assertIn("missing_identity", row["blockers"])

    def test_phases_are_not_joined(self):
        lines = fixture()
        data = {"seed": 42, "phase_a": {"openttd_output_raw": "\n".join(lines[:3])},
                "phase_b": {"openttd_output_raw": "\n".join(lines[3:])}}
        result = analyse_payload(data)
        self.assertEqual(len(result["streams"]), 2)
        self.assertIn("no_full_post_year", result["streams"][0]["purchases"][0]["blockers"])
        self.assertEqual(result["streams"][1]["metadata"]["seed"], 42)

    def test_repeated_annual_observation_is_one_year(self):
        row = report(fixture() + [fixture()[-1]])["purchases"][0]
        self.assertEqual(row["after"]["report_count"], 2)
        self.assertEqual(row["delta_profit_gbp_per_year"], 80)

    def test_conflicting_reports_not_arbitrarily_chosen(self):
        row = report(fixture() + [annual(1973, 999, 999, 2, 4)])["purchases"][0]
        self.assertEqual(row["after"]["status"], "conflicting_reports")
        self.assertIsNone(row["delta_profit_gbp_per_year"])

    def test_inconsistent_year_rejected(self):
        lines = fixture()
        lines[-1] = lines[-1].replace("year=1974", "year=1975")
        self.assertEqual(report(lines)["purchases"][0]["after"]["status"], "inconsistent_year")

    def test_duplicate_purchase_and_decision_join_ambiguous(self):
        row = report(fixture() + [fixture()[1]])["purchases"][0]
        self.assertIsNone(row["purchase_capital_estimate_gbp"])
        self.assertIn("other_fleet_events_in_window", row["blockers"])

    def test_project_built_not_second_purchase(self):
        result = report(fixture() + [log("1972-5-2", "phase=project_built mode=fleet line=3 cost=30000 profit=80")])
        self.assertEqual(result["coverage"]["air_fleet_event_records"], 1)
        self.assertEqual(result["coverage"]["added_quantity_sum_known"], 1)

    def test_r1_fitted_want_is_not_original_need(self):
        row = report(fixture())["purchases"][0]
        self.assertFalse(row["execution_partial"])
        self.assertIsNone(row["original_want"])
        self.assertIsNone(row["r1_budget_fit_exposed"])
        lines = fixture()
        lines[1] = lines[1].replace("want=1", "want=4")
        self.assertTrue(report(lines)["purchases"][0]["execution_partial"])

    def test_zero_added_is_not_no_purchase_or_growth(self):
        lines = fixture()
        lines[1] = lines[1].replace("added=1", "added=0")
        row = report(lines)["purchases"][0]
        self.assertIn("not_confirmed_growth", row["blockers"])
        self.assertIsNone(row["purchase_capital_estimate_gbp"])

    def test_inventory_change_blocks_delta(self):
        lines = fixture()
        lines[-1] = lines[-1].replace("vehs=2", "vehs=3")
        self.assertIn("fleet_composition_not_reconciled", report(lines)["purchases"][0]["blockers"])

    def test_invalid_date_retained_as_rejected(self):
        events, rejected = events_from_log(log("1972-2-31", "phase=fleet_built mode=air line=3"))
        self.assertEqual(events, [])
        self.assertEqual(rejected[0]["reason"], "invalid_date")

    def test_empty_unsupported_and_alias_outputs(self):
        result = analyse_payload({"rows": [{"profit_year": 100}]})
        self.assertEqual(result["input_coverage"], "no_supported_nonempty_logs")
        data = {"openttd_output_raw": "\n".join(fixture()), "openttd_output": "\n".join(fixture())}
        self.assertEqual(len(analyse_payload(data)["streams"]), 1)
        self.assertIsNone(report(["unrelated"])["coverage"]["added_quantity_sum_known"])

    def test_health_scan_not_complete_game_validation(self):
        result = report(fixture() + ["Your script made an error"])
        self.assertTrue(result["health_log_scan"]["unattributed"])
        self.assertEqual(result["health_scope"], "log_markers_only_not_horizon_validation")
        self.assertIn("log_health_error", result["purchases"][0]["blockers"])
        self.assertIsNone(result["purchases"][0]["delta_profit_gbp_per_year"])

    def test_missing_and_negative_quantity_sum_remains_unknown(self):
        for value in ("unknown", "-1"):
            lines = fixture()
            lines[1] = lines[1].replace("added=1", "added=" + value)
            result = report(lines)
            self.assertIsNone(result["coverage"]["added_quantity_sum_known"])
            self.assertIsNone(result["purchases"][0]["added"])

    def test_january_purchase_before_baseline_report(self):
        lines = [s.replace("1972-5-2", "1972-1-1") for s in fixture()]
        self.assertIn("baseline_report_not_before_purchase", report(lines)["purchases"][0]["blockers"])

    def test_price_join_requires_matching_quantity(self):
        lines = fixture()
        lines[2] = lines[2].replace("want=1", "want=2")
        self.assertIsNone(report(lines)["purchases"][0]["purchase_capital_estimate_gbp"])

    def test_checkpoint_streams_never_merge(self):
        payload = [{"seed": 42, "repeat": repeat, "openttd_output_raw": "\n".join(fixture())}
                   for repeat in (0, 1)]
        result = analyse_payload(payload)
        self.assertEqual(len(result["streams"]), 2)
        self.assertNotEqual(result["streams"][0]["pointer"], result["streams"][1]["pointer"])
        self.assertEqual([s["metadata"]["repeat"] for s in result["streams"]], [0, 1])

    def test_jsonl_read_only_and_hash(self):
        raw = (json.dumps({"openttd_output_raw": "\n".join(fixture())}) + "\n").encode()
        with patch.object(Path, "read_bytes", return_value=raw):
            result = analyse_file("synthetic.jsonl")
        self.assertEqual(len(result["sha256"]), 64)
        self.assertEqual(len(result["streams"]), 1)
        json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()