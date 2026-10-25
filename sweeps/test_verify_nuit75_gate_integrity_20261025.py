"""Unit tests for pair, source and script-health audit, no Docker."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from verify_nuit75_gate_integrity_20261025 import verify


def make_data():
    policy_ids = ("reference", "experimental")
    seeds = (42, 100)
    bundle = "a" * 64
    companies = {"OpexAI": {"run_ok": True, "status": "complete",
                            "horizon_complete": True, "failure_reason": None},
                 "AAAHogEx": {"run_ok": True, "status": "complete",
                              "horizon_complete": True, "failure_reason": None}}
    games = [{"policy_id": p, "seed": seed, "repeat": 0,
              "engine_log_path": f"/work/results/mock_engine/{p}_seed{seed}_r0.log",
              "source_bundle_sha256": bundle, "game_ok": True,
              "game_status": "complete", "unattributed_errors": [],
              "companies": copy.deepcopy(companies)}
             for p in policy_ids for seed in seeds]
    summary = [{"duel_policy_id": p, "seed": seed, "repeat": 0, "arm": arm,
                "source_bundle_sha256": bundle, "run_ok": True,
                "game_ok": True, "horizon_complete": True,
                "include_in_economic_stats": True,
                "failure_reason": None, "status": "complete",
                "last_year": 1974, "expected_last_year": 1974,
                "script_errors": [], "unattributed_errors": []}
               for p in policy_ids for seed in seeds for arm in companies]
    return {"campaign_id": "synthetic", "policies": [
                {"id": p, "role": "reference" if p == "reference" else "variant",
                 "explicit_settings": [["test_setting", 0 if p == "reference" else 2],
                                       ["probes", 2]]}
                for p in policy_ids],
            "seeds": list(seeds), "years": 5, "repeats": 1,
            "source_bundle_sha256": bundle, "start_year": 1970, "map_size": 8,
            "expected_last_year": 1974, "games": games, "summary": summary,
            "failed_runs": [], "policy_comparison":
                {"complete_pairs": 2, "comparison_complete": True,
                 "verdict": "fail_primary", "decision_rule": {
                     "rule": "gain_short", "required_pairs": 2,
                     "min_useful_primary_delta_pct": 4.0,
                     "value_guard_max_loss_pct": 5.0}}}


class GateIntegrity(unittest.TestCase):
    def check(self, payload, *, corrupt_log=False, omit_log=False):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mock.json"
            logs = Path(tmp) / "mock_engine"
            logs.mkdir()
            for game in payload["games"]:
                (logs / Path(game["engine_log_path"]).name).touch()
            first = logs / Path(payload["games"][0]["engine_log_path"]).name
            if corrupt_log:
                first.write_text("Squirrel exception in OpexAI\n", encoding="utf-8")
            if omit_log:
                first.unlink()
            manifest = {"source_bundle": {"sha256": "a" * 64},
                        "configuration": {"seeds": [42, 100], "years": 5,
                                          "map_size": 8, "repeats": 1},
                        "execution": {"options": {"max_workers": 9}},
                        "policies": [
                            {"role": "reference", "settings": {
                                "defaults": {"test_setting": 0, "probes": 0},
                                "effective": {"test_setting": 0, "probes": 2}}},
                            {"role": "variant", "settings": {
                                "defaults": {"test_setting": 0, "probes": 0},
                                "effective": {"test_setting": 2, "probes": 2}}}],
                        "comparison": {"decision_rule": {"rule": "gain_short"},
                                       "effective_differences": {
                                           "test_setting": {"reference": 0, "candidate": 2}}}}
            manifest_bytes = json.dumps(manifest).encode("utf-8")
            path.with_suffix(".manifest.json").write_bytes(manifest_bytes)
            payload["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
            path.write_text(json.dumps(payload), encoding="utf-8")
            return verify(path, 2, 5, setting="test_setting", value=2)

    def test_healthy(self):
        self.assertTrue(self.check(make_data())["ok"])

    def test_duplicate_and_missing_seed_pair(self):
        data = make_data()
        data["games"][0] = data["games"][1]
        self.assertFalse(self.check(data)["ok"])

    def test_squirrel_script_error_blocks_pass(self):
        data = make_data()
        data["summary"][0]["script_errors"] = ["Squirrel runtime exception"]
        result = self.check(data)
        self.assertFalse(result["ok"])
        self.assertEqual(result["script_error_count"], 1)

    def test_wrong_source_bundle_rejected(self):
        data = make_data()
        data["games"][0]["source_bundle_sha256"] = "b" * 64
        self.assertFalse(self.check(data)["ok"])

    def test_missing_company_and_incomplete_horizon(self):
        data = make_data()
        del data["games"][0]["companies"]["AAAHogEx"]
        data["summary"][0]["horizon_complete"] = False
        self.assertFalse(self.check(data)["ok"])

    def test_incomplete_comparison(self):
        data = make_data()
        data["policy_comparison"]["complete_pairs"] = 1
        self.assertFalse(self.check(data)["ok"])

    def test_wrong_horizon_or_rule(self):
        data = make_data()
        data["summary"][0]["last_year"] = 1973
        data["policy_comparison"]["decision_rule"]["min_useful_primary_delta_pct"] = 0
        self.assertFalse(self.check(data)["ok"])

    def test_unsymmetrical_probes(self):
        data = make_data()
        data["policies"][1]["explicit_settings"][1][1] = 0
        self.assertFalse(self.check(data)["ok"])

    def test_manifest_bundle_mismatch(self):
        data = make_data()
        data["source_bundle_sha256"] = "b" * 64
        self.assertFalse(self.check(data)["ok"])

    def test_fatal_message_in_engine_log(self):
        result = self.check(make_data(), corrupt_log=True)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["fatal_engine_messages"]), 1)

    def test_missing_engine_log_blocks_integrity(self):
        self.assertFalse(self.check(make_data(), omit_log=True)["ok"])


if __name__ == "__main__":
    unittest.main()
