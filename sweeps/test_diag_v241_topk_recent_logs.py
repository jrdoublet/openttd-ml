"""Read-only V241 VIVIER parser contracts. No Docker, engine or disk artifacts."""

import contextlib
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from diag_v241_topk_recent_logs import analyze, main, parse_events, summarize


def vivier(date="1971-2-3", *, path="reselect", selected="64", considered="90",
           not_selected="26", sel_ops="200000", arm=0, fields=None):
    values = {
        "path": path, "considered": considered, "selected": selected,
        "not_selected": not_selected, "sel_ops": sel_ops,
    }
    if fields is not None:
        values = fields
    body = " ".join(f"{key}={value}" for key, value in values.items()
                    if value is not None)
    return (f"[2026-10-25 20:00:00] dbg: [script:4] [{arm}] [I] "
            f"OPEX {date} VIVIER {body}\n")


class V241TopKContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, name, content, root=None):
        path = (root or self.root) / name
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def single(self, content, *, name="reference_seed42_r0.log"):
        log = self.write(name, content)
        report = analyze([log])
        self.assertEqual(report["logical_log_count"], 1)
        return report["groups"][0]

    def test_only_selected_at_least_64_is_cap_even_with_positive_selected(self):
        row = self.single(
            vivier(selected="0", considered="100", sel_ops="0") +
            vivier(selected="1", considered="100", sel_ops="10") +
            vivier(selected="63", considered="100", sel_ops="20") +
            vivier(selected="64", considered="100", sel_ops="200") +
            vivier(selected="65", considered="100", sel_ops="220")
        )
        self.assertEqual(row["calls"], 5)
        self.assertEqual(row["cap_reached_selected_ge_64"], 2)
        self.assertEqual(row["not_cap_selected_lt_64"], 3)
        self.assertEqual(row["selected_positive_calls"], 4)
        self.assertEqual(row["selected_zero_calls"], 1)
        self.assertEqual(row["cap_fraction_known_selected"], 0.4)
        self.assertEqual(row["sel_ops_by_cap"]["cap_reached"]["sum"], 420)
        self.assertEqual(row["sel_ops_by_cap"]["not_cap"]["sum"], 30)
        self.assertEqual(row["sel_ops_by_cap"]["not_cap"]["observed_calls"], 3)
        self.assertEqual(row["sel_ops_by_cap"]["not_cap"]["min"], 0)

    def test_exact_fit_is_not_an_observed_candidate_surplus(self):
        row = self.single(
            vivier(selected="64", considered="64", not_selected="0") +
            vivier(selected="64", considered="90", not_selected="26")
        )
        self.assertEqual(row["cap_reached_selected_ge_64"], 2)
        self.assertEqual(row["cap_reached_exact_fit_no_unselected"], 1)
        self.assertEqual(row["cap_reached_with_unselected"], 1)
        self.assertEqual(row["cap_reached_insufficient_or_inconsistent"], 0)

    def test_missing_or_inconsistent_surplus_cannot_be_claimed(self):
        row = self.single(
            vivier(selected="64", considered=None, not_selected=None) +
            vivier(selected="64", considered="64", not_selected="1") +
            vivier(selected="65", considered="100", not_selected="35") +
            vivier(selected="63", considered="100", not_selected="37")
        )
        self.assertEqual(row["cap_reached_selected_ge_64"], 3)
        self.assertEqual(row["cap_reached_exact_fit_no_unselected"], 0)
        self.assertEqual(row["cap_reached_with_unselected"], 0)
        self.assertEqual(row["cap_reached_insufficient_or_inconsistent"], 3)
        self.assertEqual(row["not_cap_selected_lt_64"], 1)

    def test_missing_is_not_zero_and_cap_fraction_denominator_excludes_missing(self):
        row = self.single(
            vivier(selected=None, sel_ops=None, not_selected=None, considered="0") +
            vivier(selected="garbled", sel_ops="NaN", considered=None,
                   not_selected="5") +
            vivier(selected="0", sel_ops="0", considered="0", not_selected="0")
        )
        self.assertEqual(row["calls"], 3)
        self.assertEqual(row["unknown_cap_selected_missing_or_invalid"], 2)
        self.assertEqual(row["not_cap_selected_lt_64"], 1)
        self.assertEqual(row["cap_fraction_known_selected"], 0)
        self.assertEqual(row["field_coverage"]["selected"], {
            "observed": 1, "missing_or_invalid": 2, "invalid": 1,
            "zero": 1, "sum": 0,
        })
        self.assertEqual(row["field_coverage"]["considered"]["zero"], 2)
        self.assertEqual(row["field_coverage"]["not_selected"]["missing_or_invalid"], 1)
        self.assertEqual(row["sel_ops_by_cap"]["not_cap"]["sum"], 0)
        self.assertEqual(row["sel_ops_by_cap"]["unknown_cap"]["sum"], None)
        self.assertEqual(row["sel_ops_by_cap"]["unknown_cap"]["calls_missing_or_invalid_sel_ops"], 2)

    def test_undetermined_cap_with_measured_cost_keeps_cost_separate(self):
        row = self.single(vivier(selected=None, sel_ops="80") +
                          vivier(selected="64", sel_ops=None))
        self.assertEqual(row["unknown_cap_selected_missing_or_invalid"], 1)
        self.assertEqual(row["sel_ops_by_cap"]["unknown_cap"]["sum"], 80)
        self.assertEqual(row["sel_ops_by_cap"]["cap_reached"]["observed_calls"], 0)
        self.assertIsNone(row["sel_ops_by_cap"]["cap_reached"]["mean"])
        self.assertEqual(row["cap_fraction_known_selected"], 1)
        self.assertEqual(row["cap_fraction_all_calls_lower_bound"], 0.5)

    def test_grouped_by_arm_seed_repeat_year_path_and_missing_path(self):
        self.write("reference_seed42_r0.log",
                   vivier("1971-1-1", path="build", selected="0") +
                   vivier("1971-2-1", path="reselect", selected="64") +
                   vivier("1972-1-1", path=None, selected="2"))
        self.write("reference_seed42_r1.log", vivier(path="build", selected="4"))
        self.write("variant_seed7_r0.log", vivier(path="build", selected="64"))
        report = analyze([self.root])
        self.assertEqual(report["logical_log_count"], 3)
        self.assertEqual(report["total_vivier_calls"], 5)
        self.assertEqual(len(report["groups"]), 5)
        missing = [g for g in report["groups"] if g["path"] is None]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["path_missing"], 1)
        self.assertEqual(missing[0]["year"], 1972)
        self.assertEqual(
            {(g["arm"], g["seed"], g["repeat"]) for g in report["groups"]},
            {("reference", 42, 0), ("reference", 42, 1), ("variant", 7, 0)},
        )

    def test_same_day_same_payload_is_two_selection_calls_not_deduplicated(self):
        row = self.single(vivier() * 2)
        self.assertEqual(row["calls"], 2)
        self.assertEqual(row["sel_ops_by_cap"]["cap_reached"]["sum"], 400000)

    def test_non_selection_vivier_mix_div_and_wrong_company_are_ignored(self):
        text = (vivier(selected="64", arm=1) +
                "[0] [I] OPEX 1971-2-3 VIVIER_MIX rail=1 road=1\n" +
                "[0] [I] OPEX 1971-2-3 VIVIER_DIV srcs=2 dsts=3\n" +
                "[0] [I] OPEX 1971-2-3 VIVIER path=build selected=63 "
                "not_selected=12 considered=75 sel_ops=300\n")
        row = self.single(text)
        self.assertEqual(row["calls"], 1)
        self.assertEqual(row["not_cap_selected_lt_64"], 1)
        self.assertEqual(row["sel_ops_by_cap"]["not_cap"]["sum"], 300)

    def test_gzip_only_and_duplicate_log_gzip_is_one_game(self):
        content = vivier() + vivier(selected="0", sel_ops="0")
        zipped = self.write("reference_seed42_r0.log.gz", content)
        self.assertEqual(analyze([zipped])["total_vivier_calls"], 2)
        plain = self.write("reference_seed42_r0.log", content)
        report = analyze([self.root, plain, zipped])
        self.assertEqual(report["physical_file_count"], 2)
        self.assertEqual(report["logical_log_count"], 1)
        self.assertEqual(report["duplicate_log_gzip_copies_ignored"], 1)
        self.assertEqual(report["total_vivier_calls"], 2)
        self.assertEqual(len(report["files"][0]["source_files"]), 2)

    def test_contradictory_log_and_gzip_fail_closed(self):
        self.write("reference_seed42_r0.log", vivier(selected="63"))
        self.write("reference_seed42_r0.log.gz", vivier(selected="64"))
        with self.assertRaisesRegex(ValueError, "contradictory"):
            analyze([self.root])

    def test_alias_seed_spelling_cannot_count_one_game_twice(self):
        self.write("reference_seed1_r0.log", vivier(selected="63"))
        self.write("reference_seed01_r0.log", vivier(selected="64"))
        with self.assertRaisesRegex(ValueError, "ambiguous V241 game identity"):
            analyze([self.root])

    def test_duplicate_field_cannot_silently_change_cap_classification(self):
        self.write("reference_seed42_r0.log", vivier() +
                   "[0] [I] OPEX 1971-2-3 VIVIER path=build selected=64 "
                   "selected=0 sel_ops=20\n")
        with self.assertRaisesRegex(ValueError, "duplicate VIVIER field"):
            analyze([self.root])

    def test_corrupted_gzip_reports_cli_error_instead_of_traceback(self):
        path = self.write("reference_seed42_r0.log.gz", vivier())
        path.write_bytes(path.read_bytes()[:-8])  # Truncated gzip footer.
        with patch.object(sys, "argv", ["diag_v241_topk_recent_logs.py", str(path)]):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    main()
        self.assertEqual(caught.exception.code, 2)

    def test_different_dirs_with_same_game_id_remain_independent(self):
        left, right = self.root / "small", self.root / "large"
        left.mkdir()
        right.mkdir()
        self.write("reference_seed42_r0.log", vivier(selected="63"), left)
        self.write("reference_seed42_r0.log", vivier(selected="64"), right)
        report = analyze([left, right])
        self.assertEqual(report["logical_log_count"], 2)
        self.assertEqual(len(report["groups"]), 2)
        self.assertEqual(sum(g["cap_reached_selected_ge_64"] for g in report["groups"]), 1)

    def test_empty_no_selection_logs_and_absent_dir(self):
        self.write("reference_seed42_r0.log", "no matching VIVIER event\n")
        result = analyze([self.root])
        self.assertEqual(result["logical_log_count"], 1)
        self.assertEqual(result["total_vivier_calls"], 0)
        self.assertEqual(result["groups"], [])
        with self.assertRaisesRegex(ValueError, "not an existing"):
            analyze([self.root / "does_not_exist"])

    def test_observed_cost_zero_and_missing_are_distinct(self):
        report = summarize([
            {"path": "build", "selected": 64, "considered": 64,
             "not_selected": 0, "sel_ops": 0, "invalid_numeric_fields": []},
            {"path": "build", "selected": 64, "considered": 64,
             "not_selected": None, "sel_ops": None, "invalid_numeric_fields": []},
        ])
        self.assertEqual(report["sel_ops_by_cap"]["cap_reached"]["observed_calls"], 1)
        self.assertEqual(report["sel_ops_by_cap"]["cap_reached"]["sum"], 0)
        self.assertEqual(report["sel_ops_by_cap"]["cap_reached"]["calls_missing_or_invalid_sel_ops"], 1)
        self.assertEqual(report["field_coverage"]["not_selected"]["zero"], 1)

    def test_cli_json_stdout_without_writing_anything(self):
        src = self.write("reference_seed42_r0.log", vivier())
        output = io.StringIO()
        with patch.object(sys, "argv", ["diag_v241_topk_recent_logs.py", str(src)]):
            with contextlib.redirect_stdout(output):
                main()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["total_vivier_calls"], 1)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [src.name])


if __name__ == "__main__":
    unittest.main()
