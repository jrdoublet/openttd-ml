"""Host-only invariants for the forensic evidence, no OpenTTD required."""

import statistics
import unittest

from analyze_h3_empty_pool_20261014 import report


class Evidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = report()

    def test_all_five_pairs_and_seed_5678_exposure(self):
        self.assertEqual(set(self.result["seed_results"]), {"42", "100", "999", "1234", "5678"})
        e = self.result["seed_results"]["5678"]["arms"]
        self.assertEqual(e["hub_shadow_historical"]["zero_pool_capital_ge_threshold"], 1)
        self.assertEqual(e["hub_signed_positive"]["zero_pool_capital_ge_threshold"], 14)

    def test_postbuild_not_permanent_deadlock(self):
        events = self.result["seed_results"]["5678"]["arms"]["hub_signed_positive"]["high_capital_events"]
        late = [e for e in events if e["last_logged_game_date"].startswith("1972-")]
        self.assertEqual(len(late), 13)
        self.assertTrue(all(e["next_physical"] is not None for e in late))
        days = [e["approx_days_to_next_physical"] for e in late]
        self.assertEqual(statistics.median(days), 24)
        self.assertEqual(max(days), 67)
        self.assertTrue(all(e["preceding_physical"] is not None for e in late))
        self.assertTrue(all(e["preceding_physical"]["lines_before"] <= 14 for e in late))

    def test_difference_is_not_same_tick(self):
        mismatch = self.result["seed_results"]["5678"]["first_cache_sequence_mismatch_rows"]
        self.assertNotEqual(mismatch["hub_shadow_historical"]["last_logged_game_date"],
                            mismatch["hub_signed_positive"]["last_logged_game_date"])
        self.assertEqual(self.result["claim"], "descriptive_only_not_same_tick_not_marginal")

    def test_unmodified_v166_exposure_not_directly_logged(self):
        base = self.result["v166_physical_base"]
        self.assertEqual(sorted(base["run_month_rows"].values()), [60] * 4)
        self.assertEqual(len(base["referenced_engine_logs_not_preserved"]), 2)

    def test_recovered_49_month_bench_is_single_arm(self):
        fork = self.result["recovered_recent_49m_benchmark"]
        self.assertEqual(fork["manifest_branches"], ["aa0", "aa1", "variant"])
        self.assertEqual(set(fork["complete_replays_present"]), {"aa0"})
        self.assertFalse(fork["paired_comparison_possible"])
        self.assertFalse(fork["same_historical_tick"])
        self.assertFalse(fork["historical_source_exact"])
        a = fork["complete_replays_present"]["aa0"]
        self.assertEqual(a["rows"], 49)
        self.assertEqual(a["last_date"], "1975-01-01")
        self.assertTrue(a["terminal_checkpoint_observed"])
        self.assertEqual(a["unexpected_companies"], [])
        self.assertEqual(a["script_failures"], [])
        self.assertEqual(a["opex_terminal"]["profit_year"], 1974739)


if __name__ == "__main__":
    unittest.main()
