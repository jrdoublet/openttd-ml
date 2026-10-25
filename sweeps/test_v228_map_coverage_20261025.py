"""Host-only contract for V228 descriptive map comparison; no engine access."""

import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v228_map_coverage_20261025 import CANONICAL_SEEDS, compare


def _reference(map_size):
    campaign = f"fixture-map{map_size}"
    seeds = list(CANONICAL_SEEDS)
    summary = []
    games = []
    for seed in seeds:
        game_id = f"{campaign}:policy=reference:s{seed}:r0"
        games.append({
            "seed": seed, "repeat": 0, "source_bundle_sha256": "fixture-bundle",
            "campaign_id": campaign, "policy_id": "reference", "game_id": game_id,
            "expected_last_checkpoint": "1979-12-01",
            "game_ok": True, "game_status": "complete", "unattributed_errors": [],
            "companies": {
                arm: {"run_ok": True, "horizon_complete": True, "status": "complete"}
                for arm in ("OpexAI", "AAAHogEx")
            },
        })
        for arm in ("OpexAI", "AAAHogEx"):
            summary.append({
                "seed": seed, "repeat": 0, "arm": arm, "run_ok": True,
                "campaign_id": campaign, "game_id": game_id,
                "duel_policy_id": "reference",
                "policy_id": "reference" if arm == "OpexAI" else "AAAHogEx",
                "company_slot": 0 if arm == "OpexAI" else 1,
                "last_year": 1979, "profit_year_quarters_valid": 4,
                "last_date": "1979-12-01", "expected_last_checkpoint": "1979-12-01",
                "profit_year_coverage": "complete", "status": "complete",
                "horizon_complete": True, "game_ok": True,
                "include_in_economic_stats": True, "script_errors": [],
                "unattributed_errors": [], "source_bundle_sha256": "fixture-bundle",
                "profit_year": 100 * seed if arm == "OpexAI" else 150 * seed,
                "company_value": 1 if arm == "OpexAI" and seed == 1 else 10000,
                "n_vehicles": 5 if arm == "OpexAI" else 12,
            })
    return {
        "campaign_id": campaign, "expected_last_checkpoint": "1979-12-01",
        "manifest_sha256": "1" * 64,
        "start_year": 1970, "map_size": map_size, "years": 10, "repeats": 1,
        "policy_id": "reference", "source_bundle_sha256": "fixture-bundle",
        "policies": [{"id": "reference", "role": "reference", "explicit_settings": []}],
        "arms": ["OpexAI", "AAAHogEx"], "design": "Duel partage",
        "openttd_version": "15.3", "opengfx_version": "7.1",
        "aaahogex_settings": {}, "seeds": seeds, "failed_runs": [],
        "expected_last_year": 1979, "summary": summary, "games": games,
    }


class MapReferenceContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.small = Path(self.tmp.name) / "small.json"
        self.large = Path(self.tmp.name) / "large.json"
        self.small_data = _reference(8)
        self.large_data = _reference(10)

    def _write(self):
        self.small.write_text(json.dumps(self.small_data), encoding="utf-8")
        self.large.write_text(json.dumps(self.large_data), encoding="utf-8")

    def test_complete_same_bundle_20x10_is_descriptive(self):
        self._write()
        result = compare(self.small, self.large)
        self.assertEqual(result["map1024"]["pairs"], 20)
        self.assertEqual(result["map1024"]["opex_company_value_floor_1_count"], 1)
        self.assertAlmostEqual(result["map256"]["opex_to_aaa_ratio_of_means_pct"], 66.667, places=3)
        self.assertIn("descriptive", result["interpretation"])

    def test_refuse_different_bundle_or_seed_set(self):
        self.large_data["source_bundle_sha256"] = "other"
        for game in self.large_data["games"]:
            game["source_bundle_sha256"] = "other"
        for entry in self.large_data["summary"]:
            entry["source_bundle_sha256"] = "other"
        self._write()
        with self.assertRaisesRegex(ValueError, "bundle ou reglage divergent"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        self.large_data["seeds"][-1] = 21
        for entry in self.large_data["summary"]:
            if entry["seed"] == CANONICAL_SEEDS[-1]:
                entry["seed"] = 21
        self._write()
        with self.assertRaisesRegex(ValueError, "graines canoniques"):
            compare(self.small, self.large)

    def test_refuse_missing_or_failed_parties(self):
        self.large_data["summary"].pop()
        self._write()
        with self.assertRaisesRegex(ValueError, "40 bilans"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        self.large_data["summary"][0]["run_ok"] = False
        self._write()
        with self.assertRaisesRegex(ValueError, "malsain"):
            compare(self.small, self.large)

    def test_refuse_partial_horizon_or_repetition(self):
        self.large_data["years"] = 9
        self._write()
        with self.assertRaisesRegex(ValueError, "20 graines canoniques"):
            compare(self.small, self.large)
        self.large_data["years"] = 10
        self.large_data["repeats"] = 2
        self._write()
        with self.assertRaisesRegex(ValueError, "20 graines canoniques"):
            compare(self.small, self.large)

    def test_refuse_incomplete_profit_quarters_and_repeat(self):
        self.large_data["summary"][0]["profit_year_quarters_valid"] = 3
        self._write()
        with self.assertRaisesRegex(ValueError, "jeu incomplet"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        self.large_data["summary"][0]["repeat"] = 1
        self._write()
        with self.assertRaisesRegex(ValueError, "jeu incomplet"):
            compare(self.small, self.large)

    def test_refuse_policy_and_engine_changes(self):
        self.large_data["policies"][0]["explicit_settings"] = [["probes", 0]]
        self._write()
        with self.assertRaisesRegex(ValueError, "bundle ou reglage divergent"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        self.large_data["opengfx_version"] = "other"
        self._write()
        with self.assertRaisesRegex(ValueError, "bundle ou reglage divergent"):
            compare(self.small, self.large)

    def test_refuse_failed_engine_game_even_with_complete_company_summary(self):
        self.large_data["games"][0]["game_ok"] = False
        self._write()
        with self.assertRaisesRegex(ValueError, "partie manquante ou malsaine"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        self.large_data["games"].pop()
        self._write()
        with self.assertRaisesRegex(ValueError, "20 parties moteur manquantes"):
            compare(self.small, self.large)

    def test_refuse_script_errors_and_wrong_bundle_on_company_row(self):
        self.large_data["summary"][0]["script_errors"] = ["script crash"]
        self._write()
        with self.assertRaisesRegex(ValueError, "jeu incomplet ou malsain"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        self.large_data["summary"][0]["source_bundle_sha256"] = "another-bundle"
        self._write()
        with self.assertRaisesRegex(ValueError, "jeu incomplet ou malsain"):
            compare(self.small, self.large)

    def test_refuse_absent_failed_runs(self):
        del self.large_data["failed_runs"]
        self._write()
        with self.assertRaisesRegex(ValueError, "failed_runs absent"):
            compare(self.small, self.large)

    def test_refuse_wrong_game_identity_or_company_slot(self):
        self.large_data["games"][0]["game_id"] = "a-different-game"
        self._write()
        with self.assertRaisesRegex(ValueError, "partie manquante ou malsaine"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        self.large_data["summary"][0]["company_slot"] = 99
        self._write()
        with self.assertRaisesRegex(ValueError, "jeu incomplet ou malsain"):
            compare(self.small, self.large)

    def test_refuse_incomplete_terminal_date_or_ratio(self):
        self.large_data["summary"][0]["last_date"] = "1979-11-01"
        self._write()
        with self.assertRaisesRegex(ValueError, "jeu incomplet ou malsain"):
            compare(self.small, self.large)
        self.large_data = _reference(10)
        next(entry for entry in self.large_data["summary"]
             if entry["arm"] == "AAAHogEx")["profit_year"] = 0
        self._write()
        with self.assertRaisesRegex(ValueError, "profit terminal AAAHogEx non positif"):
            compare(self.small, self.large)


if __name__ == "__main__":
    unittest.main()
