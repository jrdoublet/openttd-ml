"""Contrats synthétiques de l'analyse de causalité de P4."""

import tempfile
import json
from pathlib import Path
import unittest

from analyse_scores_p4_causal_exposure_20261013 import (
    builds_with_revenue, classify_fork, factors, first_money_difference,
    first_sequence_difference,
    matched_mature_same_od, read_log, selected_signature,
)


class TestP4CausalExposure(unittest.TestCase):
    def test_timing_shift_does_not_imply_different_project(self):
        a = [{"mode": "air", "cargo": "PASS", "src": "11", "dst": "12",
              "date": "1972-04-03"}]
        b = [{**a[0], "date": "1972-04-04"}]
        self.assertIsNone(first_sequence_difference(a, b, selected_signature))
        self.assertEqual("1972-04-03", first_sequence_difference(
            a, b, lambda r: (r["date"], selected_signature(r)))["first_date"])

    def test_od_change_can_precede_money_but_remains_unproven(self):
        a = [{"date": "1972-11-02", "src": "1"}]
        b = [{"date": "1972-11-03", "src": "2"}]
        fork = first_sequence_difference(a, b, lambda r: r["src"])
        self.assertEqual("post_factor_pre_money_unproven_same_state",
                         classify_fork(fork, "1972-01-01", "1972-12-01"))
        self.assertEqual("before_p4_factor_or_no_factor",
                         classify_fork(fork, "1973-01-01", "1972-12-01"))
        self.assertEqual("after_observed_world_divergence",
                         classify_fork(fork, "1972-01-01", "1972-10-01"))

    def test_build_requires_line_id_and_maturity_is_only_own_profit(self):
        events = {key: [] for key in
                  ("PROJECT_CHOSEN", "AIR_BUILD", "RAIL_BUILD",
                   "LINE_REVENUE", "P4_VYEAR_MODE")}
        events["AIR_BUILD"] = [{"date": "1972-01-05", "line": "17",
                                "src": "1", "dst": "2", "profit": "42000"}]
        events["LINE_REVENUE"] = [
            {"line": "17", "age": "1", "real_prof": "12000",
             "pred_prof": "42000", "year": "1973"},
            {"line": "17", "age": "2", "real_prof": "22000",
             "pred_prof": "42000", "year": "1974", "vehs": "3"},
        ]
        rows = builds_with_revenue(events)
        self.assertEqual(1, len(rows))
        self.assertEqual("17", rows[0]["line"])
        self.assertEqual(1, len(rows[0]["mature_reports"]))
        self.assertEqual(22000, rows[0]["mature_reports"][0]["real_prof"])
        events["AIR_BUILD"][0].pop("line")
        with self.assertRaises(ValueError):
            builds_with_revenue(events)

    def test_factor_only_if_applied_and_non_neutral(self):
        x = {"P4_VYEAR_MODE": [
            {"applied": "0", "factor": "0.6", "legacy_k": "0.4",
             "date": "1972-01-01", "mode": "air", "covered": "7"},
            {"applied": "1", "factor": "0.4", "legacy_k": "0.4",
             "date": "1973-01-01", "mode": "air", "covered": "7"},
            {"applied": "1", "factor": "0.5", "legacy_k": "0.4",
             "date": "1974-01-01", "mode": "rail", "covered": "4"},
        ]}
        self.assertEqual(["1974-01-01"], [x["date"] for x in factors(x)])

    def test_log_only_emits_real_builds_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "test.log"
            log.write_text("\n".join([
                "[clock] dbg: [script:4] [0] [I] OPEX 1972-2-4 PROJECT_CHOSEN rank=0 mode=air cargo=PASS src=1 dst=2",
                "[clock] dbg: [script:4] [0] [I] OPEX 1972-2-4 AIR_BUILD line=3 src=1 dst=2 profit=100",
                "[clock] dbg: [script:4] [0] [I] P4_VYEAR_MODE exercise=1971 mode=air covered=1 factor=0.5 legacy_k=0.4 applied=1",
                "[clock] dbg: [script:4] [0] [I] OPEX 1974-1-4 LINE_REVENUE line=3 age=2 year=1974 real_prof=44 pred_prof=100 vehs=2",
                "[clock] dbg: [script:4] [1] [I] OPEX 1972-2-5 AIR_BUILD line=9 src=2 dst=3",
            ]), encoding="utf8")
            events = read_log(log)
        self.assertEqual(1, len(events["AIR_BUILD"]))
        self.assertEqual(1, len(events["LINE_REVENUE"]))
        self.assertEqual("1972-02-04", events["PROJECT_CHOSEN"][0]["date"])
        self.assertEqual("1972-02-04", factors(events)[0]["date"])

    def test_same_od_line_year_requires_unique_line_and_matching_year(self):
        a = [{"line": "1", "mode": "air", "cargo": "PASS", "src": "10",
              "dst": "20", "date": "1972-02-02", "mature_reports": [
                  {"year": "1974", "real_prof": 100, "vehs": 3}]}]
        b = [{**a[0], "line": "7", "date": "1972-03-01", "mature_reports": [
                  {"year": "1974", "real_prof": 130, "vehs": 4},
                  {"year": "1975", "real_prof": 180, "vehs": 4}]}]
        pairs, ambiguous = matched_mature_same_od(a, b)
        self.assertEqual(1, len(pairs))
        self.assertEqual(30, pairs[0]["profit_delta"])
        self.assertEqual(3, pairs[0]["reference_vehs"])
        self.assertEqual(4, pairs[0]["variant_vehs"])
        self.assertEqual(0, ambiguous)
        pairs, ambiguous = matched_mature_same_od(a + a, b)
        self.assertEqual([], pairs)
        self.assertEqual(1, ambiguous)

    def test_rival_uses_duel_policy_and_can_fork_before_opex(self):
        events = []
        for dt in ("1972-11-01", "1972-12-01"):
            for policy in ("ref", "on"):
                events.append({"run": ["OpexAI", 42, 0],
                               "date": dt, "policy_id": policy,
                               "duel_policy_id": policy,
                               "source_bundle_sha256": "sha",
                               "money": 100 + (1 if policy == "on" and dt == "1972-12-01" else 0)})
                events.append({"run": ["AAAHogEx", 42, 0],
                               "date": dt, "policy_id": "AAAHogEx",
                               "duel_policy_id": policy,
                               "source_bundle_sha256": "sha",
                               "money": 100 + (1 if policy == "on" else 0)})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in events), encoding="utf8")
            self.assertEqual("1972-12-01", first_money_difference(path, "ref", "on", 42))
            self.assertEqual("1972-11-01", first_money_difference(
                path, "ref", "on", 42, "AAAHogEx"))


if __name__ == "__main__":
    unittest.main()
