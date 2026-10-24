"""Fixtures offline: ne confondre ni refus, ni passes, ni capital engagé."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from analyse_air_load_reselect import (
    FROZEN_FILES, analyse_log, classify_vivier, summarise_vivier, verify_frozen_files,
)
from test_b5_rail_persistence import function_body


def vivier(**changes):
    fields = dict(budget=100, selection_pool_capital=40, remaining=60,
                  next_capital=-1, considered=1, selected=1, rejected=0)
    fields.update(changes)
    return fields


def log(tag, fields="", owner=0):
    return f"[2026-10-24 11:26:43] dbg: [script:4] [{owner}] [I] OPEX 1972-12-1 {tag} {fields}"


class AirLoadReselectAudit(unittest.TestCase):
    def test_partitions_each_observed_pound_without_treating_pool_as_committed(self):
        rows = [classify_vivier(vivier()),
                classify_vivier(vivier(considered=0, selected=0, selection_pool_capital=0, remaining=100)),
                classify_vivier(vivier(considered=2, rejected=1, next_capital=120)),
                classify_vivier(vivier(selection_pool_capital=140, remaining=0))]
        result = summarise_vivier(rows)
        self.assertEqual(result["remaining_pound_snapshots"], 220)
        self.assertEqual(result["categories"]["no_extra_candidate"]["remaining_pound_snapshots"], 60)
        self.assertEqual(result["categories"]["no_candidate"]["remaining_pound_snapshots"], 100)
        self.assertEqual(result["categories"]["unaffordable_candidate"]["remaining_pound_snapshots"], 60)
        self.assertEqual(rows[-1]["category"], "pool_sum_covers_budget")

    def test_no_cash_only_diagnosis_from_negative_next_capital(self):
        row = classify_vivier(vivier(considered=2, rejected=1))
        self.assertEqual(row["category"], "other_unresolved")

    def test_missing_and_inconsistent_vivier_do_not_become_zero(self):
        fields = vivier()
        del fields["remaining"]
        with self.assertRaises(KeyError):
            classify_vivier(fields)
        for fields in (vivier(remaining=61), vivier(rejected=1), vivier(budget=-1)):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                classify_vivier(fields)

    def test_failed_purchase_is_distinct_from_guard_and_refusals_are_not_passes(self):
        result = analyse_log([
            log("AIR_FLEET", "action=refuse line=3 reason=low_load_factor"),
            log("TASK", "name=projects"),
            log("PROJECT_DISCARD", "rank=0 mode=fleet reason=fleet_grow_failed"),
            log("PROJECT_DISCARD", "rank=1 mode=fleet reason=fleet_grow_failed"),
            log("TASK", "name=expand"),
        ], "airload50log_seed42_r0.log")
        self.assertEqual(result["fleet_discard_events"], 2)
        self.assertEqual(result["fleet_discard_blocks"], 1)
        self.assertEqual(result["blocks_with_later_higher_rank_discard"], 1)
        self.assertEqual(result["refusal_counts"]["1972/AIR_FLEET/-/low_load_factor/refuse"], 1)
        self.assertNotIn("total_passes", result)
        self.assertFalse(any("FLEET_PROJECT" in k for k in result["refusal_counts"]))

    def test_same_day_tasks_split_discard_blocks_and_eof_is_flushed(self):
        result = analyse_log([
            log("PROJECT_DISCARD", "rank=0 mode=fleet reason=low_load_factor"),
            log("TASK", "name=projects"),
            log("PROJECT_DISCARD", "rank=0 mode=fleet reason=fleet_grow_failed"),
        ], "airload50log_seed7_r0.log")
        self.assertEqual(result["fleet_discard_blocks"], 2)
        self.assertEqual(result["fleet_head_discard_blocks"], 2)

    def test_other_company_cannot_contaminate_diagnostic(self):
        result = analyse_log([
            log("PROJECT_DISCARD", "rank=0 mode=fleet reason=low_load_factor", owner=1),
            log("VIVIER", "path=reselect " + " ".join(f"{k}={v}" for k, v in vivier().items())),
        ], "reference_seed100_r0.log")
        self.assertEqual(result["fleet_discard_events"], 0)
        self.assertEqual(result["vivier"][0]["remaining"], 60)
        self.assertEqual(result["seed"], 100)

    def test_fleet_must_be_counted_from_total_not_omitted_mode_columns(self):
        fields = "path=reselect " + " ".join(f"{k}={v}" for k, v in vivier().items())
        result = analyse_log([log("VIVIER", fields),
            log("VIVIER_MIX", "rail=0 road=0 air=0 water=0 total=1").replace("1972-12-1 ", "1972-12-2 ")],
            "reference_seed7_r0.log")
        self.assertEqual(result["vivier"][0]["modes"]["fleet"], 1)
        self.assertEqual(summarise_vivier(result["vivier"])["positive_remaining_with_fleet"], 1)
        raw = analyse_log([log("VIVIER", fields),
            log("VIVIER_MIX", "rail=0 road=0 air=2 water=0 total=2")], "reference_seed7_r0.log")
        self.assertEqual(raw["vivier"][0]["considered"], 1)  # filtré != brut
        self.assertEqual(raw["vivier"][0]["modes"]["total"], 2)
        with self.assertRaises(ValueError):
            analyse_log([log("VIVIER", fields),
                log("VIVIER_MIX", "rail=2 road=0 air=0 water=0 total=1")], "reference_seed7_r0.log")

    def test_frozen_source_mismatch_fails_instead_of_reinterpreting_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            ai = bundle / "ai" / "OpexAI"
            ai.mkdir(parents=True)
            for name in FROZEN_FILES:
                (ai / name).write_bytes(b"frozen")
            manifest = {"sources": {"OpexAI": {"files": [
                {"path": name, "sha256": hashlib.sha256(b"frozen").hexdigest()}
                for name in FROZEN_FILES]}}}
            self.assertEqual(len(verify_frozen_files(bundle, manifest)), len(FROZEN_FILES))
            (ai / "task_projects.nut").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "task_projects.nut"):
                verify_frozen_files(bundle, manifest)

    def test_existing_rejected_fleet_does_not_return_or_break_the_portfolio_pass(self):
        ai = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
        code = (ai / "task_projects.nut").read_text(encoding="utf-8")
        execute = function_body(code, "function OpexAI::_tryBuildProjects(")
        branch = function_body(execute, 'if (mode == "fleet")')
        # Les return/break concernent exclusivement pending, pas rejected.
        pending = function_body(branch, 'if (attempt.outcome == "pending")')
        without_pending = branch.replace(pending, "")
        self.assertNotIn("return ", without_pending)
        self.assertNotIn("break;", without_pending)
        self.assertTrue(branch.rstrip().endswith("continue;"))
        guard = function_body(code, "if (AIR_LOAD_MIN_PCT > 0 && OpexAirLoadBlocksGrowth(line))")
        self.assertIn('outcome = "rejected"', guard)
        self.assertNotIn("fleet_grow_failed", guard)


if __name__ == "__main__":
    unittest.main()
