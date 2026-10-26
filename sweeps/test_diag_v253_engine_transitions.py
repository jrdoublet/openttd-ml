"""Host-only fixtures for the V253/V252 engine-choice event audit."""

import contextlib
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from sweeps.diag_v253_engine_transitions import aggregate, analyze, main, parse_events


def replace(year=1975, old=223, new=217, line=3, price=32812, arm=0, more=""):
    return (f"[2026-10-21 11:00:00] dbg: [script:4] [{arm}] [I] "
            f"OPEX {year}-3-1 V252_REPLACE line={line} old_engine={old} "
            f"new_engine={new} old_veh=16 new_veh=405 price={price} "
            f"age=1400 profit=37000{more}\n")


def skip(reason="loan", year=1972, arm=0):
    ending = "" if reason is None else f" reason={reason}"
    return f"[0] [I] OPEX {year}-4-5 V252_SKIP{ending} loan=300000\n".replace(
        "[0] [I]", f"[{arm}] [I]"
    )


class V253EngineTransitionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, name, text, parent=None):
        path = (parent or self.root) / name
        if name.endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def test_transition_counts_repeated_same_date_are_distinct(self):
        game = self.write("reference_seed42_r0.log", replace() + replace() +
                          replace(1977, old=228, new=218, line=4, price=153808))
        row = analyze([game])["games"][0]
        self.assertEqual(row["replacements"], 3)
        self.assertEqual(row["classified_transitions"], 3)
        self.assertEqual(row["distinct_line_ids_with_replacements"], 2)
        self.assertEqual(row["transitions"], {"223->217": 2, "228->218": 1})
        self.assertEqual(row["replacements_by_year"], {1975: 2, 1977: 1})
        self.assertEqual(row["observed_price_median_by_new_engine"], {"217": 32812.0, "218": 153808})

    def test_skip_events_are_not_replace_and_unknown_reason_is_separate(self):
        row = analyze([self.write("reference_seed42_r0.log", skip() + skip(None))])["games"][0]
        self.assertEqual(row["replacements"], 0)
        self.assertEqual(row["skip_events_by_reason"], {"<missing>": 1, "loan": 1})

    def test_missing_numeric_is_not_zero_or_complete_transition(self):
        malformed = replace(old="BAD", new=217, price="-1")
        zero = replace(old=223, new=218, line=0, price=0)
        row = analyze([self.write("reference_seed42_r0.log", malformed + zero)])["games"][0]
        self.assertEqual(row["replacements"], 2)
        self.assertEqual(row["classified_transitions"], 1)
        self.assertEqual(row["transitions"], {"223->218": 1})
        self.assertEqual(row["missing_or_invalid_replacement_fields"], {"old_engine": 1, "price": 1})
        self.assertEqual(row["observed_price_median_by_new_engine"]["218"], 0)

    def test_negative_historical_profit_is_valid_but_not_used_as_causal_delta(self):
        content = replace().replace("profit=37000", "profit=-5000")
        path = self.write("reference_seed42_r0.log", content)
        event = list(parse_events(path))[0]
        self.assertEqual(event["profit"], -5000)
        self.assertNotIn("profit", event["fields_missing_or_invalid"])
        report = aggregate([event])
        self.assertEqual(report["replacements"], 1)
        self.assertNotIn("profit", report["missing_or_invalid_replacement_fields"])

    def test_duplicate_kv_fails_closed(self):
        path = self.write("reference_seed42_r0.log", replace(more=" new_engine=218"))
        with self.assertRaisesRegex(ValueError, "duplique"):
            analyze([path])

    def test_plain_gzip_identical_copies_count_one_game(self):
        body = replace() + skip()
        text = self.write("reference_seed42_r0.log", body)
        zipped = self.write("reference_seed42_r0.log.gz", body)
        report = analyze([self.root, zipped, text])
        self.assertEqual(report["logical_games"], 1)
        self.assertEqual(report["physical_files"], 2)
        self.assertEqual(report["by_arm"]["reference"]["replacements"], 1)

    def test_gzip_only_and_conflicting_copies(self):
        compressed = self.write("reference_seed42_r0.log.gz", replace())
        self.assertEqual(analyze([compressed])["logical_games"], 1)
        self.write("reference_seed42_r0.log", replace(new=218))
        with self.assertRaisesRegex(ValueError, "copies texte/gzip contradictoires"):
            analyze([self.root])

    def test_alias_seeds_do_not_merge_silently(self):
        self.write("reference_seed1_r0.log", replace())
        self.write("reference_seed01_r0.log", replace())
        with self.assertRaisesRegex(ValueError, "ambigue"):
            analyze([self.root])

    def test_arms_seeds_repeats_and_directories_remain_distinct(self):
        self.write("reference_seed42_r0.log", replace())
        self.write("reference_seed42_r1.log", replace(new=218))
        self.write("variant_seed42_r0.log", replace(old=228))
        other = self.root / "other"
        other.mkdir()
        self.write("reference_seed42_r0.log", replace(new=218), other)
        report = analyze([self.root, other])
        self.assertEqual(report["logical_games"], 4)
        self.assertEqual(report["by_arm"]["reference"]["replacements"], 3)
        self.assertEqual(report["by_arm"]["variant"]["replacements"], 1)
        self.assertEqual(report["by_arm"]["reference"]["distinct_line_ids_with_replacements"], 1)
        self.assertEqual(report["by_arm"]["reference"]["distinct_game_line_pairs_with_replacements"], 3)
        self.assertEqual(report["by_arm"]["variant"]["distinct_game_line_pairs_with_replacements"], 1)

    def test_pooled_local_line_ids_do_not_hide_distinct_game_line_pairs(self):
        self.write("reference_seed42_r0.log", replace(line=3) + replace(line=3))
        self.write("reference_seed100_r0.log", replace(line=3) + replace(line=4))
        self.write("reference_seed7_r0.log", skip())
        report = analyze([self.root])
        arm = report["by_arm"]["reference"]
        self.assertEqual(arm["replacements"], 4)
        self.assertEqual(arm["distinct_line_ids_with_replacements"], 2)
        self.assertEqual(arm["distinct_game_line_pairs_with_replacements"], 3)
        self.assertEqual(sum(game["distinct_line_ids_with_replacements"]
                             for game in report["games"]), 3)

    def test_other_company_and_other_tag_ignored(self):
        body = (replace(arm=1) + "[0] [I] OPEX 1975-3-1 V252_KEEP line=3\n"
                + skip(arm=1) + replace())
        row = analyze([self.write("reference_seed42_r0.log", body)])["games"][0]
        self.assertEqual(row["replacements"], 1)
        self.assertEqual(row["skip_events_by_reason"], {})

    def test_empty_log_observed_as_zero_events_not_zero_engine_profit(self):
        row = analyze([self.write("reference_seed42_r0.log", "no V252 telemetry\n")])["games"][0]
        self.assertEqual(row["replacements"], 0)
        self.assertEqual(row["observed_price_median_by_new_engine"], {})
        with self.assertRaisesRegex(ValueError, "inexistant"):
            analyze([self.root / "missing"])

    def test_cli_prints_json_only_without_writing(self):
        log = self.write("reference_seed42_r0.log", replace())
        output = io.StringIO()
        with patch.object(sys, "argv", ["diag_v253_engine_transitions.py", str(log)]):
            with contextlib.redirect_stdout(output):
                main()
        self.assertEqual(json.loads(output.getvalue())["logical_games"], 1)
        self.assertEqual([p.name for p in self.root.iterdir()], [log.name])


if __name__ == "__main__":
    unittest.main()
