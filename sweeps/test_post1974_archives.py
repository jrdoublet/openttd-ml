"""Contracts for qualified 20x10 archive analyzer (stdlib only)."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

try:
    from sweeps.post1974_archives import read_campaign, analyze_suite, YEARS
except ImportError:
    from post1974_archives import read_campaign, analyze_suite, YEARS


def fixture(seed=42, year=1979, role="OpexAI", sha="correct"):
    row = {
        "run": [role, seed, 0], "date": f"{year}-12-01", "company_present": True,
        "duel_policy_id": "variant", "source_bundle_sha256": sha,
        "profit_year": 200 if role == "OpexAI" else 100,
        "money": 12000000, "air_airports": year - 1960,
        "primary_vehicles_by_mode": {"rail": year - 1950},
    }
    if role == "OpexAI":
        row.update({
            "project_builds_sign_by_year": {"1979": 2},
            "c75_bypass_years": {"1978": {"eligible": 5, "consumed": 3, "stop_cash": 1}},
            "rail_attempt_sign_by_year": {"1979": {"or_signs": 4, "ob_signs": 4, "reasons": {"OTHER": 3, "OK": 1}, "iterations": 9, "iteration_budget": 20, "opcodes": 100}},
            "rail_attempt_sign_or": [{"year": 1979} for _ in range(4)],
            "rail_attempt_sign_ob": [{"year": 1979} for _ in range(4)],
        })
    return row


class TestPost1974(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "fixture.jsonl"

    def write(self, rows):
        self.path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def rows(self):
        return [fixture(year=y, role=role) for y in YEARS for role in ("OpexAI", "AAAHogEx")]

    def test_c75_absent_final_year_is_censored_not_zero(self):
        self.write(self.rows())
        final, yearly = read_campaign(self.path, "variant", "correct", {42})
        data = analyze_suite(final, yearly)
        self.assertIsNone(data["by_year"]["1979"]["c75_eligible"])
        self.assertEqual(data["by_year"]["1979"]["c75_observed_seed_count"], 0)
        self.assertEqual(data["by_year"]["1979"]["project_build_signs"], 2)
        self.assertEqual(data["by_year"]["1979"]["rail_attempt_reasons"]["OTHER"], 3)
        self.assertEqual(data["by_year"]["1979"]["ratio_of_mean_profits_pct"], 200)

    def test_rejects_wrong_source(self):
        rows = self.rows()
        rows[-1]["source_bundle_sha256"] = "wrong"
        self.write(rows)
        with self.assertRaisesRegex(ValueError, "Source SHA mismatch"):
            read_campaign(self.path, "variant", "correct", {42})

    def test_rejects_duplicate_snapshot(self):
        rows = self.rows()
        self.write(rows + [rows[-1]])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            read_campaign(self.path, "variant", "correct", {42})

    def test_rejects_missing_company(self):
        self.write([r for r in self.rows() if r["date"] != "1979-12-01" or r["run"][0] != "AAAHogEx"])
        with self.assertRaisesRegex(ValueError, "Incomplete final company pair"):
            read_campaign(self.path, "variant", "correct", {42})

    def test_no_duplicate_ledger_from_annual_checkpoints(self):
        rows = self.rows()
        self.write(rows)
        final, yearly = read_campaign(self.path, "variant", "correct", {42})
        result = analyze_suite(final, yearly)
        # A retained final sign is assigned to its encoded build year once.
        self.assertEqual(sum(x["project_build_signs"] for x in result["by_year"].values()), 2)


if __name__ == "__main__":
    unittest.main()
