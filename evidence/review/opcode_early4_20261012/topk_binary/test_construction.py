"""C66 paired physical/non-famine QA; no fabricated AIR/RAIL build counts."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from analyse_p0_topk_construction import (
    checkpoint_evidence, extract_ib_proxy, load_checkpoints, nonnegative,
    summarize_pairs,
)


BUNDLE = "def46d63" + "0" * 56


def fixture():
    rows, games, checkpoints = [], [], {}
    for policy, offset in (("reference", 0), ("p0_topk_binary", 2)):
        game_id = f"fixture:policy={policy}:s42:r0"
        row = {
            "arm": "OpexAI", "seed": 42, "repeat": 0,
            "policy_id": policy, "duel_policy_id": policy,
            "game_id": game_id, "source_bundle_sha256": BUNDLE,
            "status": "complete", "run_ok": True, "game_ok": True,
            "horizon_complete": True, "physical_ok": True,
            "vehs_chunk_valid": True, "stnn_chunk_valid": True,
            "last_year": 1970, "n_savegames": 12,
            "profit_year_coverage": "complete", "profit_year_quarters_valid": 4,
            "months_of_bankruptcy": 0, "script_errors": [],
            "company_value": 1000 + offset, "profit_year": -100 + offset,
            "primary_vehicles": 13 + offset, "n_vehicles": 13 + offset,
            "n_stations": 13 + offset,
            "qualified_modes": {"air": True, "rail": True, "water": False},
            "primary_vehicles_by_mode": {"air": 12 + offset, "rail": 1},
            "stations_by_facility": {"airport": 12 + offset, "rail": 1},
            "activity": {"signal": "active", "n_checkpoints": 12,
                         "fleet_changes": 11, "network_changes": 11,
                         "value_increases": 5,
                         "months_since_fleet_or_network_change": 0},
        }
        game = {"seed": 42, "repeat": 0, "policy_id": policy,
                "game_id": game_id, "source_bundle_sha256": BUNDLE,
                "game_ok": True, "game_status": "complete", "unattributed_errors": []}
        rows.append(row)
        games.append(game)
        cp = []
        for month in range(1, 13):
            cp.append({"run": ["OpexAI", 42, 0], "duel_policy_id": policy,
                       "game_id": game_id, "source_bundle_sha256": BUNDLE,
                       "date": f"1970-{month:02d}-01", "vehs_chunk_valid": True,
                       "stnn_chunk_valid": True,
                       "primary_vehicles_by_mode": {"air": month + offset,
                                                    "rail": 1},
                       "stations_by_facility": {"airport": month + offset,
                                                "rail": 1},
                       "project_build_signs_parsed": 2,
                       "project_builds_sign_total": 4,
                       "project_builds_sign_by_year": {"1970": 4}})
        checkpoints[(policy, 42, 0)] = cp
    data = {"campaign_id": "fixture", "source_bundle_sha256": BUNDLE,
            "years": 1, "repeats": 1, "seeds": [42],
            "expected_last_checkpoint": "1970-12-01",
            "policies": [{"id": "reference", "role": "reference"},
                         {"id": "p0_topk_binary", "role": "variant"}],
            "summary": rows, "games": games}
    return data, checkpoints


def run_fixture(data, checkpoints=None):
    return summarize_pairs(data, expected_seeds=1, expected_years=1,
                           expected_bundle_prefix="def46d63", checkpoints=checkpoints)


class ConstructionC66Tests(unittest.TestCase):
    def test_full_pair_stocks_and_monotone_checkpoints_not_builds(self):
        data, cp = fixture()
        out = run_fixture(data, cp)
        self.assertTrue(out["qa"]["pairwise_health_complete"])
        self.assertEqual(out["qa"]["complete_monthly_checkpoint_pairs"], 1)
        self.assertFalse(out["qa"]["strict_non_famine_certified"])
        row = out["per_seed"][0]
        self.assertEqual(row["variant_minus_reference"]["air_vehicles_final_stock"], 2)
        self.assertEqual(row["variant_minus_reference"]["rail_stations_final_stock"], 0)
        self.assertEqual(row["variant_minus_reference"]["profit_year"], 2)
        self.assertIsNone(row["line_builds_air_rail"]["delta"])
        self.assertEqual(row["reference"]["checkpoints"]["monthly_stock_changes"]
                         ["air_vehicles"]["net_positive_stock_deltas_sum"], 11)
        self.assertEqual(row["retained_ib_project_pass_proxy"]["delta_retained_total"], 0)
        self.assertEqual(row["retained_ib_project_pass_proxy"]["status"],
                         "observed_retained_signs_not_total_builds")

    def test_positive_final_stocks_do_not_invent_line_builds_without_jsonl(self):
        data, _ = fixture()
        out = run_fixture(data)
        self.assertTrue(out["qa"]["pairwise_health_complete"])
        self.assertFalse(out["qa"]["monthly_checkpoints_available"])
        self.assertEqual(out["qa"]["retained_ib_proxy_paired_n"], 0)
        for row in out["per_seed"]:
            self.assertIsNone(row["line_builds_air_rail"]["reference"])
            self.assertIsNone(row["checkpoint_stock_change_deltas"]
                              ["air_vehicles_positive_change_months"])

    def test_invalid_physical_mode_is_unknown_never_zero(self):
        data, cp = fixture()
        data["summary"][0]["vehs_chunk_valid"] = False
        out = run_fixture(data, cp)
        self.assertFalse(out["qa"]["pairwise_health_complete"])
        row = out["per_seed"][0]
        self.assertIsNone(row["reference"]["physical_final_stocks"]["air"]["vehicles"])
        self.assertIsNone(row["variant_minus_reference"]["air_vehicles_final_stock"])
        self.assertIn("vehs_chunk_valid_not_true", row["reference"]["issues"])

    def test_invalid_count_missing_and_bool_not_zero(self):
        self.assertIsNone(nonnegative(None))
        self.assertIsNone(nonnegative(True))
        self.assertIsNone(nonnegative(-1))
        self.assertIsNone(nonnegative(2.0))
        data, _ = fixture()
        del data["summary"][0]["primary_vehicles_by_mode"]["air"]
        self.assertIsNone(run_fixture(data)["per_seed"][0]
                          ["reference"]["physical_final_stocks"]["air"]["vehicles"])

    def test_absent_duplicate_and_bad_campaign_identity(self):
        data, cp = fixture()
        del data["summary"][0]
        out = run_fixture(data, cp)
        self.assertFalse(out["qa"]["pairwise_health_complete"])
        self.assertIn("reference_summary_count_0", out["per_seed"][0]["issues"])
        data, cp = fixture()
        data["summary"].append(copy.deepcopy(data["summary"][0]))
        self.assertIn("reference_summary_count_2", run_fixture(data, cp)["per_seed"][0]["issues"])
        data, cp = fixture()
        data["summary"][0]["source_bundle_sha256"] = "different"
        self.assertIn("reference_bundle_identity_mismatch", run_fixture(data, cp)["per_seed"][0]["issues"])

    def test_wrong_horizon_game_and_invalid_years_rejected(self):
        data, cp = fixture()
        data["games"][0]["game_ok"] = False
        data["summary"][0]["last_year"] = 1971
        out = run_fixture(data, cp)
        self.assertFalse(out["qa"]["pairwise_health_complete"])
        self.assertIn("horizon_last_year_mismatch", out["per_seed"][0]["reference"]["issues"])
        self.assertIn("duel_game_not_complete", out["per_seed"][0]["reference"]["issues"])
        data, cp = fixture()
        data["years"] = 9
        self.assertIn("campaign_years_mismatch", run_fixture(data, cp)["qa"]["campaign_issues"])

    def test_jsonl_corruption_duplicate_or_missing_checkpoint_detected(self):
        data, cp = fixture()
        cp[("reference", 42, 0)].pop()
        out = run_fixture(data, cp)
        self.assertIn("reference_monthly_checkpoint_count_mismatch", out["per_seed"][0]["issues"])
        data, cp = fixture()
        cp[("reference", 42, 0)][1]["date"] = "1970-01-01"
        self.assertIn("reference_duplicate_monthly_checkpoint", run_fixture(data, cp)["per_seed"][0]["issues"])
        data, cp = fixture()
        cp[("reference", 42, 0)][0]["date"] = None
        self.assertIn("reference_checkpoint_dates_invalid", run_fixture(data, cp)["per_seed"][0]["issues"])

    def test_monthly_final_stock_conflict_detected(self):
        data, cp = fixture()
        cp[("p0_topk_binary", 42, 0)][-1]["primary_vehicles_by_mode"]["air"] = 900
        out = run_fixture(data, cp)
        self.assertIn("variant_air_vehicles_checkpoint_final_stock_conflict", out["per_seed"][0]["issues"])
        self.assertFalse(out["qa"]["pairwise_health_complete"])

    def test_ib_retention_cannot_claim_air_or_rail_builds(self):
        self.assertEqual(extract_ib_proxy({"project_build_signs_parsed": 0,
                                           "project_builds_sign_total": 0,
                                           "project_builds_sign_by_year": {}}, 1970, 1979)
                         ["status"], "no_retained_panels")
        self.assertEqual(extract_ib_proxy({"project_build_signs_parsed": 2,
                                           "project_builds_sign_total": 4,
                                           "project_builds_sign_by_year": {"1975": 3}}, 1970, 1979)
                         ["status"], "inconsistent_total")
        data, cp = fixture()
        cp[("reference", 42, 0)][-1]["project_builds_sign_total"] = 9
        out = run_fixture(data, cp)
        self.assertIn("reference_retained_ib_panel_inconsistent", out["per_seed"][0]["issues"])
        self.assertIsNone(out["per_seed"][0]["retained_ib_project_pass_proxy"]["delta_retained_total"])

    def test_load_jsonl_uses_opex_and_policy_seed_identity(self):
        data, cp = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.jsonl"
            rows = cp[("reference", 42, 0)] + cp[("p0_topk_binary", 42, 0)]
            with path.open("w", encoding="utf-8") as out:
                for row in rows:
                    out.write(json.dumps(row) + "\n")
                out.write(json.dumps({"run": ["AAAHogEx", 42, 0]}) + "\n")
                out.write("NOT_JSON\n")
            found, errors = load_checkpoints(path)
        self.assertEqual(len(found), 2)
        self.assertEqual(len(found[("reference", 42, 0)]), 12)
        self.assertTrue(errors[0].startswith("malformed_jsonl_line_"))
        self.assertFalse(run_fixture(data, found)["qa"]["campaign_issues"])


if __name__ == "__main__":
    unittest.main()
