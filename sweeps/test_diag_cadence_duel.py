"""Fixtures du diagnostic : aucun moteur lance par ces tests."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diag_cadence_duel as diag


def game(arm, seed, op=100, aaa=200, value=1000, valid=True):
    return {"arm": arm, "seed": seed, "valid": valid,
            "ratio_pct": {1970: 100 * op / aaa},
            "annual": {"OpexAI": {0: op}, "AAAHogEx": {0: aaa}},
            "final": [{"company_value": value}]}


class ComparisonTests(unittest.TestCase):
    def test_ratio_is_mean_of_ratios_not_ratio_of_sums(self):
        games = [game("reference", 42, 100, 100), game("reference", 100, 100, 1000)]
        self.assertEqual(diag.compare(games, ["reference"], [42, 100], 1)["annual"],
                         {"reference": {1970: 55}})

    def test_missing_failed_duplicate_and_extra_games_fail_closed(self):
        valid = [game("reference", 42), game("watch_daily", 42)]
        for games in (valid[:1], valid + [valid[0]], valid + [game("extra", 42)],
                      [valid[0], game("watch_daily", 42, valid=False)]):
            r = diag.compare(games, ["reference", "watch_daily"], [42], 1)
            self.assertFalse(r["complete"])
            self.assertEqual(r["annual"], {})
            self.assertEqual(r["paired_final"], {})

    def test_opponent_loss_does_not_hide_own_loss(self):
        games = [game("reference", 42), game("watch_daily", 42, 90, 100, 900)]
        r = diag.compare(games, ["reference", "watch_daily"], [42], 1)["paired_final"]["watch_daily"]
        self.assertEqual(r["opex_profit_delta"], -10)
        self.assertEqual(r["aaa_profit_delta"], -100)
        self.assertEqual(r["gap_delta"], 90)
        self.assertEqual(r["ratio_delta_pts"], 40)
        self.assertAlmostEqual(r["value_delta_pct"], -10)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        log = Path(self.tmp.name) / "engine.log"
        log.write_text("", encoding="utf-8")
        rec = {"vehs_chunk_valid": True, "stnn_chunk_valid": True,
               "profit_year_coverage": "complete"}
        self.row = {"arm": "reference", "seed": 42, "date": "1971-02-01",
                    "records": [rec.copy(), rec.copy()], "log_path": str(log),
                    "annual": {"OpexAI": {0: 100}, "AAAHogEx": {0: 200}}}

    @patch.object(diag, "assess_game", return_value={"game_ok": True, "game_status": "complete"})
    def test_full_data_pass_and_each_bad_dimension_refuses(self, health):
        self.assertTrue(diag.finish_game([self.row], 1)["valid"])
        bad = []
        row = deepcopy(self.row); row["date"] = "1971-01-01"; bad.append(row)
        row = deepcopy(self.row); row["annual"]["OpexAI"] = {}; bad.append(row)
        row = deepcopy(self.row); row["annual"]["AAAHogEx"][0] = 0; bad.append(row)
        row = deepcopy(self.row); row["records"][0]["vehs_chunk_valid"] = False; bad.append(row)
        row = deepcopy(self.row); row["records"][1]["profit_year_coverage"] = "partial"; bad.append(row)
        for row in bad:
            self.assertFalse(diag.finish_game([row], 1)["valid"])

    @patch.object(diag, "assess_game", return_value={"game_ok": False, "game_status": "noai_error"})
    def test_noai_error_cannot_be_overridden_by_complete_profits(self, health):
        result = diag.finish_game([self.row], 1)
        self.assertFalse(result["valid"])
        self.assertIn("noai_error", result["reasons"])

    def test_source_fingerprint_detects_added_deleted_and_modified_code(self):
        root = Path(self.tmp.name)
        directory = root / "ai" / "OpexAI"
        directory.mkdir(parents=True)
        file = directory / "main.nut"
        file.write_text("before", encoding="utf-8")
        before = diag.source_hashes(root)
        file.write_text("after", encoding="utf-8")
        self.assertNotEqual(before, diag.source_hashes(root))
        file.unlink()
        self.assertNotEqual(before, diag.source_hashes(root))


class SettingsIntegrationTests(unittest.TestCase):
    def test_each_variant_changes_exactly_one_off_default_setting(self):
        base = diag.bench_v2.resolve_opex_arm_settings(diag.ARMS["reference"])["effective"]
        self.assertEqual(base["c115_air_c100_capital_replay"], 1)
        for name, spec in diag.ARMS.items():
            if name == "reference":
                continue
            other = diag.bench_v2.resolve_opex_arm_settings(spec)["effective"]
            changed = [k for k in base if base[k] != other[k]]
            self.assertEqual(len(changed), 1)
            self.assertTrue(changed[0].startswith("exp_"))
            self.assertEqual((base[changed[0]], other[changed[0]]), (0, 1))
            self.assertEqual(other["c121_air_economics"], 0)


if __name__ == "__main__":
    unittest.main()