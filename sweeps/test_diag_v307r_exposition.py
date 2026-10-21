"""Contrats du diagnostic V307R, sans OpenTTD et sans modifier les bancs."""

import gzip
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v307r_exposition import (
    analyze_campaign, arm_events, evaluate, parse_log, percentile, ratio_change,
)


def event(tag, **fields):
    payload = " ".join(f"{key}={value}" for key, value in fields.items())
    return f"[2026-10-21 20:10:04] dbg: [script:4] [0] [I] OPEX 1974-2-7 {tag} {payload}\n"


def attempt(ok, reason, *, shared=False):
    return event("RAIL_ATTEMPT", src=1, dst=2, shared_dest=int(shared),
                 join_end="B" if shared else "-", ok=ok, reason=reason)


def build(shared=False, line=1):
    return event("RAIL_BUILD", line=line, src=1, dst=2, cargo="COAL",
                 shared_dest=int(shared), join_end="B" if shared else "-",
                 pred_profit=1000)


def metric(arm, seed, repeat, profit, value):
    return {"arm": "OpexAI", "company_slot": 0, "duel_policy_id": arm,
            "seed": seed, "repeat": repeat, "profit_year": profit,
            "profit_year_coverage": "complete", "company_value": value,
            "game_ok": True, "horizon_complete": True, "status": "complete"}


class TestV307RDiagnostic(unittest.TestCase):
    def test_real_log_format_and_gz_keep_all_attempts_and_filter_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "variant_seed42_r0.log.gz"
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(event("V307R_SITE", src=1, dst=2, before=12, after=5,
                                   ops=1234, fallback=0, bit=1))
                handle.write(event("V307R_SITE", src=2, dst=3, before=12, after=12,
                                   ops=2345, fallback=1, bit=1))
                handle.write(attempt(0, "ABND"))
                handle.write(attempt(0, "SITEAB"))
                handle.write(attempt(1, "OK", shared=True))
                handle.write(build(True, 8))
                handle.write("[script:4] [0] [S] Your script made an error\n")
            parsed = parse_log(path)
        actual = arm_events([parsed])
        self.assertEqual((actual["site_calls"], actual["site_reduced"], actual["site_fallback"]), (2, 1, 1))
        self.assertEqual((actual["site_before_sum"], actual["site_after_sum"]), (24, 17))
        self.assertEqual(actual["site_ops_total"], 3579)
        self.assertEqual((actual["attempts"], actual["attempts_ok"], actual["abnd_siteab"]), (3, 1, 2))
        self.assertEqual((actual["attempts_join_B"], actual["joins_B"], actual["new_lines"]), (1, 1, 0))
        self.assertEqual(actual["script_errors"], 1)

    def test_thresholds_pass_with_exposure_and_complete_10y(self):
        def fake(reason_counts, shared_attempts, shared_ok, joined, new, site=0):
            ref = {"logs": 1, "script_errors": 0, "site_calls": site, "site_reduced": site,
                   "attempts": 10, "attempt_missing_fields": 0, "attempt_inconsistent_ok_reason": 0,
                   "attempts_join_B": shared_attempts, "attempts_join_B_ok": shared_ok,
                   "joins_B": joined, "abnd_siteab": reason_counts,
                   "abnd_siteab_per_attempt": reason_counts / 10, "new_lines": new}
            return ref
        a = fake(5, 4, 2, 2, 3)
        b = fake(2, 4, 4, 4, 3, site=4)
        verdict = evaluate(a, b, 1, 1, True, True)
        self.assertEqual(verdict["verdict"], "all_pass")
        self.assertEqual(verdict["join_success_rate_delta_pct"], 100)
        self.assertEqual(verdict["siteab_abnd_count_delta_pct"], -60)
        self.assertEqual(verdict["criteria"]["new_lines_no_loss"], "pass")
        b["new_lines"] = 2
        self.assertEqual(evaluate(a, b, 1, 1, True, True)["criteria"]["new_lines_no_loss"], "fail")

    def test_no_exposure_or_no_baseline_yields_not_evaluable(self):
        a = {"logs": 1, "site_calls": 0, "site_reduced": 0, "script_errors": 0,
             "attempts": 2, "attempts_join_B": 0, "attempts_join_B_ok": 0,
             "joins_B": 0, "abnd_siteab": 0, "abnd_siteab_per_attempt": 0,
             "new_lines": 1, "attempt_missing_fields": 0, "attempt_inconsistent_ok_reason": 0}
        b = dict(a, site_calls=0, joins_B=1, new_lines=2)
        self.assertEqual(evaluate(a, b, 1, 1, True, True)["verdict"], "not_evaluable")
        b.update(site_calls=1, site_reduced=1)
        verdict = evaluate(a, b, 1, 1, True, True)
        self.assertEqual(verdict["criteria"]["join_success_plus_50pct"], "not_evaluable")
        self.assertEqual(verdict["criteria"]["siteab_abnd_minus_40pct"], "not_evaluable")
        self.assertIsNone(ratio_change(4, 0))

    def test_all_site_calls_fallback_does_not_count_as_exposure(self):
        stub = {"logs": 1, "site_calls": 3, "site_reduced": 0, "site_fallback": 3,
                "script_errors": 0, "attempts": 3, "attempts_join_B": 2,
                "attempts_join_B_ok": 1, "joins_B": 1, "abnd_siteab": 2,
                "abnd_siteab_per_attempt": 2 / 3, "new_lines": 1,
                "attempt_missing_fields": 0, "attempt_inconsistent_ok_reason": 0}
        verdict = evaluate(stub, stub, 1, 1, True, True)
        self.assertFalse(verdict["exposed"])
        self.assertIn("only_fallback_sites", verdict["limits"])
        self.assertEqual(verdict["verdict"], "not_evaluable")

    def test_campaign_json_paired_opex_profit_and_partial_smoke_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            campaign = "v307r_bit1_test_20261021"
            engine = parent / (campaign + "_engine")
            engine.mkdir()
            (engine / "reference_seed42_r0.log").write_text(attempt(0, "ABND") + build(line=1))
            (engine / "v307r_bit1_seed42_r0.log").write_text(
                event("V307R_SITE", before=12, after=4, ops=1500, fallback=0, bit=1)
                + attempt(1, "OK") + build(line=2))
            report = {"seeds": [42], "repeats": 1, "years": 10,
                      "policies": [{"id": "reference", "role": "reference"},
                                   {"id": "v307r_bit1", "role": "variant"}],
                      "games": [{"game_ok": True, "game_status": "complete"}] * 2,
                      "summary": [metric("reference", 42, 0, 100000, 250000),
                                  metric("v307r_bit1", 42, 0, 140000, 280000),
                                  {"arm": "AAAHogEx", "policy_id": "reference", "company_slot": 1,
                                   "seed": 42, "repeat": 0, "profit_year": 9999999}]}
            (parent / (campaign + ".json")).write_text(json.dumps(report), encoding="utf-8")
            summary = analyze_campaign(engine, campaign, results_dir=parent)
            report["policy_comparison"] = {"comparison_complete": False}
            (parent / (campaign + ".json")).write_text(json.dumps(report), encoding="utf-8")
            incomplete_comparison = analyze_campaign(engine, campaign, results_dir=parent)
        self.assertEqual(summary["economics"]["profit_year_delta_mean"], 40000)
        self.assertEqual(summary["economics"]["company_value_delta_mean"], 30000)
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["reference"]["abnd_siteab"], 1)
        self.assertEqual(summary["variant"]["attempts_ok"], 1)
        self.assertFalse(incomplete_comparison["complete"])
        self.assertEqual(incomplete_comparison["evaluation"]["verdict"], "not_evaluable")

    def test_missing_results_is_incomplete_without_zero_profit_imputation(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            engine = parent / "v307r_bit1_running_engine"
            engine.mkdir()
            (engine / "v307r_bit1_seed42_r0.log").write_text(event("V307R_SITE", before=12,
                                                                 after=12, fallback=1, ops=999))
            summary = analyze_campaign(engine, "v307r_bit1_running", results_dir=parent)
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["evaluation"]["verdict"], "not_evaluable")
        self.assertEqual(summary["economics"]["profit_year_n"], 0)
        self.assertIsNone(summary["economics"]["profit_year_delta_mean"])

    def test_partial_campaign_never_compares_extra_reference_seed_to_one_variant(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            engine = parent / "v307r_bit1_partial_engine"
            engine.mkdir()
            (engine / "reference_seed42_r0.log").write_text(attempt(0, "ABND"))
            (engine / "reference_seed7_r0.log").write_text(attempt(0, "SITEAB") * 8)
            (engine / "v307r_bit1_seed42_r0.log").write_text(
                event("V307R_SITE", before=12, after=6, ops=800, fallback=0)
                + attempt(1, "OK"))
            summary = analyze_campaign(engine, "v307r_bit1_partial", results_dir=parent)
        self.assertEqual(summary["reference"]["attempts"], 1)
        self.assertEqual(summary["unpaired_observed"]["reference"]["attempts"], 9)
        self.assertEqual(summary["evaluation"]["siteab_abnd_count_delta_pct"], -100.0)
        self.assertEqual(summary["evaluation"]["verdict"], "not_evaluable")

    def test_percentile_small_samples(self):
        self.assertEqual(percentile([200, 100, 400], 50), 200)
        self.assertEqual(percentile([200, 100, 400], 90), 360)


if __name__ == "__main__":
    unittest.main()
