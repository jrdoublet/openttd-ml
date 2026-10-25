"""Host-only synthetic fixtures for V285 logging, without OpenTTD or Docker."""

import contextlib
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from diag_v285_event_funnel import analyze, main, read_one, summarize


def gate(day="1971-1-1", *, line="4", reason="eligible", extra=""):
    return (f"[2026-10-20 12:31:35] dbg: [script:4] [0] [I] OPEX {day} "
            f"V285_GATE line={line} reason={reason} trains=1 wagons=2 platform=4{extra}\n")


def intent(day="1971-1-1", *, line="4", old="2", new="3"):
    return (f"[0] [I] OPEX {day} V285 action=wagon line={line} kind=pax "
            f"old_wagons={old} new_wagons={new} platform=4 waiting=612 "
            "train_cap=80 speed=147 new_speed=145\n")


def result(action="moved", day="1971-1-4", *, line="4", old="2", new="3",
           op_date="719909", reason=None):
    if reason is None:
        reason = "move_wagon_ok" if action == "moved" else "resumed"
    return (f"[0] [I] OPEX {day} V285_RESULT action={action} reason={reason} "
            f"line={line} date={op_date} old_wagons={old} new_wagons={new} cost=1447\n")


class EventFunnelTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)

    def write(self, name, content):
        path = self.directory / name
        if str(path).endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def test_full_wagon_funnel_counts_one_move_not_two(self):
        path = self.write("v285m6_seed42_r0.log", gate() + intent() +
                          result("moved") + result("completed"))
        one = analyze([path])["runs"][0]
        self.assertEqual(one["counts"]["gate_events"], 1)
        self.assertEqual(one["counts"]["wagon_intent_events"], 1)
        self.assertEqual(one["counts"]["result_events"], 2)
        self.assertEqual(one["counts"]["moved_result_events"], 1)
        self.assertEqual(one["counts"]["completed_result_events"], 1)
        self.assertEqual(one["counts"]["confirmed_move_operations"], 1)
        self.assertEqual(one["counts"]["moved_and_completed_same_operation"], 1)
        self.assertEqual(one["counts"]["intent_move_signature_overlap"], 1)
        self.assertEqual(one["counts"]["intent_events_without_move_signature_match"], 0)
        self.assertEqual(one["per_line"]["4"]["confirmed_move_operations"], 1)
        self.assertEqual(one["missing_fields_by_kind"]["result"]["line"], 0)

    def test_repeated_gate_different_day_not_deduplicated_but_lines_unique(self):
        src = gate() + gate() + gate("1971-2-2") + gate(reason="cooldown")
        row = analyze([self.write("v285m6_seed42_r0.log", src)])["runs"][0]
        self.assertEqual(row["raw_event_lines"], 4)
        self.assertEqual(row["identical_event_lines_ignored"], 1)
        self.assertEqual(row["counts"]["gate_events"], 3)
        self.assertEqual(row["gate_events_by_reason"], {"cooldown": 1, "eligible": 2})
        self.assertEqual(row["distinct_gate_lines_by_reason"], {"cooldown": 1, "eligible": 1})
        self.assertEqual(row["distinct_line_counts"]["gate"], 1)

    def test_intention_only_cannot_be_inferred_as_move(self):
        row = analyze([self.write("v285m6_seed42_r0.log", intent())])["runs"][0]
        self.assertEqual(row["counts"]["wagon_intent_events"], 1)
        self.assertEqual(row["counts"]["confirmed_move_operations"], 0)
        self.assertEqual(row["counts"]["intent_events_without_move_signature_match"], 1)
        self.assertEqual(row["distinct_line_counts"]["intention_without_observed_move"], 1)

    def test_completion_alone_is_not_a_confirmed_move(self):
        row = analyze([self.write("v285m6_seed42_r0.log", result("completed"))])["runs"][0]
        self.assertEqual(row["counts"]["completed_operation_notifications"], 1)
        self.assertEqual(row["counts"]["completed_without_moved_operation"], 1)
        self.assertEqual(row["counts"]["confirmed_move_operations"], 0)

    def test_distinct_operations_same_line_and_unmatched_moved(self):
        src = result("moved") + result("completed") + result(
            "moved", "1971-3-4", old="3", new="4", op_date="719960")
        row = analyze([self.write("v285m6_seed42_r0.log", src)])["runs"][0]
        self.assertEqual(row["counts"]["confirmed_move_operations"], 2)
        self.assertEqual(row["counts"]["moved_without_completed_notification"], 1)
        self.assertEqual(row["distinct_line_counts"]["moved_result"], 1)

    def test_missing_values_explicit_zero_remains_zero(self):
        incomplete = ("[0] [I] OPEX 1971-2-2 V285_GATE line=5 trains=0 "
                      "wagons=2 platform=BAD\n"
                      "[0] [I] OPEX 1971-2-3 V285 action=wagon kind=pax old_wagons=2\n"
                      "[0] [I] OPEX 1971-2-4 V285_RESULT action=moved line=5 "
                      "old_wagons=2 new_wagons=3 cost=0\n")
        parsed = read_one(self.write("v285m6_seed42_r0.log", incomplete))
        self.assertEqual(parsed["events"][0]["trains"], 0)
        self.assertIsNone(parsed["events"][0]["platform"])
        self.assertIsNone(parsed["events"][1]["line"])
        report = summarize(parsed["events"])
        self.assertEqual(report["missing_fields_by_kind"]["gate"]["reason"], 1)
        self.assertEqual(report["missing_fields_by_kind"]["gate"]["platform"], 1)
        self.assertEqual(report["missing_fields_by_kind"]["wagon_intent"]["line"], 1)
        self.assertEqual(report["counts"]["intent_events_missing_pair_identity"], 1)
        self.assertEqual(report["missing_fields_by_kind"]["result"]["date"], 1)
        self.assertEqual(report["counts"]["moved_result_events"], 1)
        self.assertEqual(report["counts"]["confirmed_move_operations"], 0)
        self.assertEqual(report["counts"]["result_events_missing_operation_identity"], 1)
        self.assertEqual(report["gate_events_by_reason"], {"<missing>": 1})

    def test_malformed_selected_marker_explicitly_reported(self):
        src = ("V285_GATE line=4 reason=eligible\n" + gate() +
               "[0] [I] OPEX 1971-1-3 V285 action=skip line=4\n")
        row = analyze([self.write("v285m6_seed42_r0.log", src)])["runs"][0]
        self.assertEqual(row["unparsed_marker_lines"], 1)
        self.assertEqual(row["counts"]["gate_events"], 1)

    def test_gzip_only_and_matching_text_gzip_count_single_logical_game(self):
        src = gate() + intent() + result() + result("completed")
        compressed = self.write("v285m6_seed42_r0.log.gz", src)
        self.assertEqual(analyze([compressed])["logical_games"], 1)
        plain = self.write("v285m6_seed42_r0.log", src)
        report = analyze([self.directory, compressed, plain])
        self.assertEqual(report["source_files"], 2)
        self.assertEqual(report["log_gzip_copies_collapsed"], 1)
        self.assertEqual(report["logical_games"], 1)
        self.assertEqual(report["runs"][0]["counts"]["confirmed_move_operations"], 1)

    def test_conflicting_text_gzip_copies_fail_closed(self):
        self.write("v285m6_seed42_r0.log", gate(reason="eligible"))
        self.write("v285m6_seed42_r0.log.gz", gate(reason="profit"))
        with self.assertRaisesRegex(ValueError, "copies log/gzip contradictoires"):
            analyze([self.directory])

    def test_different_arms_seeds_repeats_kept_separate(self):
        self.write("reference_seed42_r0.log", "other campaign log\n")
        self.write("v285m6_seed42_r0.log", intent())
        self.write("v285m6_seed42_r1.log.gz", result())
        self.write("v285m6_seed7_r0.log", gate())
        report = analyze([self.directory])
        self.assertEqual(report["logical_games"], 4)
        self.assertEqual(report["by_arm"]["reference"]["logical_games"], 1)
        self.assertEqual(report["by_arm"]["v285m6"]["logical_games"], 3)
        self.assertEqual(report["by_arm"]["v285m6"]["confirmed_move_operations"], 1)
        self.assertEqual([r["seed"] for r in report["runs"] if r["arm"] == "v285m6"],
                         [42, 42, 7])

    def test_distinct_directories_do_not_collapse_same_basename(self):
        left, right = self.directory / "one", self.directory / "two"
        left.mkdir()
        right.mkdir()
        (left / "v285m6_seed42_r0.log").write_text(intent(), encoding="utf-8")
        (right / "v285m6_seed42_r0.log").write_text(result(), encoding="utf-8")
        report = analyze([left, right])
        self.assertEqual(report["logical_games"], 2)
        self.assertEqual(report["log_gzip_copies_collapsed"], 0)

    def test_empty_directory_fails_instead_of_silent_zero(self):
        with self.assertRaisesRegex(ValueError, "aucun journal"):
            analyze([self.directory])

    def test_cli_emits_strict_json_to_stdout_without_writing_files(self):
        path = self.write("v285m6_seed42_r0.log", gate() + intent())
        out = io.StringIO()
        with patch.object(sys, "argv", ["diag_v285_event_funnel.py", str(path)]):
            with contextlib.redirect_stdout(out):
                main()
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["logical_games"], 1)
        self.assertEqual(payload["runs"][0]["counts"]["confirmed_move_operations"], 0)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), [path.name])


if __name__ == "__main__":
    unittest.main()
