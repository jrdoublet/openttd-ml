"""Contrats de la sonde passive INVEST-STALL : zéro changement de décision."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from analyse_invest_stall_diagnostic import parse_logs, mixed_wagon_subcauses
from invest_stall_diagnostic_off import off_source as diagnostic_off
from invest_stall_platform_off import FIXTURE, off_source as platform_off
from rail_long_v3_multi_off import upgrade_reservation_off
from test_invest_stall_fleet import source, function


class InvestStallDiagnosticContracts(unittest.TestCase):
    def test_diagnostics_are_removable_before_frozen_platform_projection(self):
        old = json.loads(FIXTURE.read_text(encoding="utf8"))["files"]
        for filename in ("invest_stall_fleet.nut", "task_v284.nut"):
            with self.subTest(filename=filename):
                clean = diagnostic_off(filename, source(filename))
                clean = upgrade_reservation_off(filename, clean)
                self.assertEqual(hashlib.sha256(clean.encode()).hexdigest(),
                                 old[filename]["after_sha256"])
                prior = platform_off(filename, clean)
                self.assertEqual(hashlib.sha256(prior.encode()).hexdigest(),
                                 old[filename]["before_sha256"])
                self.assertEqual(diagnostic_off(filename, clean), clean)

    def test_recheck_uses_original_gates_and_only_diagnoses_on_reject(self):
        tick = function("task_v284.nut", "OpexV284Tick")
        reject = tick.index('OpexV284Cancel(owner, pending, "invest_stall_recheck")')
        detail = tick.index("OpexInvestStallRecheckDiagnostic(owner, line, pending")
        self.assertLess(detail, reject)
        self.assertLess(reject, tick.index("OpexBuildTrains("))
        self.assertIn("if (DECISION_LOG) OpexInvestStallRecheckDiagnostic", tick)
        original = diagnostic_off("task_v284.nut", source("task_v284.nut"))
        self.assertIn('OpexV284Cancel(owner, pending, "invest_stall_recheck")', original)

    def test_platform_guard_is_identical_when_diagnostic_layer_removed(self):
        plan = function("invest_stall_fleet.nut", "OpexInvestStallPlatformPlan")
        self.assertLess(plan.index("OpexInvestStallPlatformDiagnostic(owner, line)"),
                        plan.index('reason=unsafe_or_busy'))
        self.assertIn("if (DECISION_LOG) OpexInvestStallPlatformDiagnostic", plan)
        for token in ('"kind=platform reason=unsafe_or_busy"',
                      'line.platformA.length != line.platformLength',
                      'OpexRailLongV2LineSafe(owner, line)'):
            self.assertIn(token, plan)

    def test_transaction_id_does_not_modify_investment_decision(self):
        select = function("invest_stall_fleet.nut", "OpexInvestStallFleetSelect")
        self.assertIn("traceStart = now", select)
        self.assertIn("OpexInvestStallTraceId(state.pending)", select)
        self.assertIn("OpexInvestStallTraceId(pending)", source("task_v284.nut"))
        self.assertIn("txn=", source("task_v284.nut"))
        self.assertIn("margin_detail=", source("invest_stall_fleet.nut"))
        self.assertIn("failed=", source("invest_stall_fleet.nut"))
        self.assertNotIn('AIController.GetSetting("invest_stall_diagnostic")',
                         source("invest_stall_fleet.nut"))

    def test_missing_or_duplicate_probe_is_rejected(self):
        current = source("task_v284.nut")
        marker = "OpexInvestStallRecheckDiagnostic(owner, line, pending,"
        with self.assertRaises(AssertionError):
            diagnostic_off("task_v284.nut", current.replace(marker, "Removed("))
        with self.assertRaises(AssertionError):
            diagnostic_off("task_v284.nut", current + "\n" + marker + "\n")

    def test_log_reader_correlates_detailed_and_generic_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "invest_stall_probe_seed17_r0.log"
            log.write_text(
                "[2026-11-04 15:00:00] OPEX 1975-3-25 INVEST_STALL "
                "event=diagnostic route=fleet line=22 kind=wagon "
                "reason=invest_stall_recheck primary=mixed_wagons "
                "failed=mixed_wagons margin_detail=positive "
                "loco_capacity=-1 wagon_mismatches=0 txn=22_7_1\n"
                "[2026-11-04 15:00:00] OPEX 1975-3-25 INVEST_STALL "
                "event=skip route=fleet line=22 reason=invest_stall_recheck "
                "txn=22_7_1\n",
                encoding="utf8",
            )
            rejects, details, primary, causes, txns, rows = parse_logs([log])
            self.assertEqual(rejects[(17, "wagon", "invest_stall_recheck")], 1)
            self.assertEqual(details[(17, "wagon", "invest_stall_recheck")], 1)
            self.assertEqual(primary[(17, "wagon", "mixed_wagons")], 1)
            self.assertEqual(causes[(17, "wagon", "mixed_wagons")], 1)
            self.assertEqual(len(txns[(17, "diagnostic")]), 1)
            self.assertEqual(rows[0]["loco_capacity"], "-1")
            self.assertEqual(rows[0]["wagon_mismatches"], "0")
            self.assertEqual(mixed_wagon_subcauses(rows), [
                {"seed": 17, "subcause": "loco_capacity_only", "count": 1}
            ])

    def test_mixed_wagon_subcauses_fail_closed_on_missing_or_inconsistent_data(self):
        rows = [
            {"seed": 17, "kind": "wagon", "failed": "mixed_wagons",
             "loco_capacity": "", "wagon_mismatches": ""},
            {"seed": 17, "kind": "wagon", "failed": "mixed_wagons",
             "loco_capacity": "0", "wagon_mismatches": "2"},
            {"seed": 17, "kind": "wagon", "failed": "mixed_wagons",
             "loco_capacity": "3", "wagon_mismatches": "1"},
            {"seed": 17, "kind": "wagon", "failed": "mixed_wagons",
             "loco_capacity": "0", "wagon_mismatches": "0"},
        ]
        self.assertEqual(mixed_wagon_subcauses(rows), [
            {"seed": 17, "subcause": "both", "count": 1},
            {"seed": 17, "subcause": "inconsistent_no_failed_subcondition", "count": 1},
            {"seed": 17, "subcause": "unmeasured", "count": 1},
            {"seed": 17, "subcause": "wagon_ids_only", "count": 1},
        ])


if __name__ == "__main__":
    unittest.main()
