"""Synthetic reader fixtures/source contracts. NO Squirrel VM, game or container."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sweeps import diag_r1_r3_mechanisms as diag


def log_line(mechanism, phase, company=0, **fields):
    values = {"test_only": 1, "date": 719900, "tick": 100, "mechanism": mechanism,
              "phase": phase, **fields}
    return "dbg: [script:4] [%s] [I] R1R3 %s" % (
        company, " ".join(f"{k}={v}" for k, v in values.items()))


def fleet_fixture(*, budget=31000, fitted=1, added=1, stale=False, repeat=False):
    # Numbers are invented reader inputs, NOT outputs of the Squirrel fit.
    out = [log_line("R1", "fit", id="f1", line=7, original=4, fitted=fitted,
                    admitted=int(budget >= 31000), base=1, have=1, scrapping=0,
                    budget=budget, price=30000, reserve=10000, cash=budget + 10000, buffer=1000)]
    if budget < 31000:
        return out
    out.append(log_line("R1", "rank", id="f1", rank=2, score=0.5, finance=31000, budget=budget))
    common = dict(id="f1", line=7, rank=2, cycle=4, want=1, base=1, price=30000,
                  reserve=10000, buffer=1000, cash=41000)
    out.append(log_line("R1", "execute", **common, reason="entry", inventory=2 if stale else 1,
                        cached=2 if stale else 1, vehicles="8,9" if stale else "8", **{"pass": 1}))
    if not stale:
        out.append(log_line("R1", "api_result", id="f1", rank=2, added=added, unit=0, reason="OK", **{"pass": 1}))
    out.append(log_line("R1", "result", **common,
                        reason="fleet_stale" if stale else "built" if added else "fleet_grow_failed",
                        added=0 if stale else added, replaced=0,
                        inventory=2 if stale or added else 1, cached=2 if stale or added else 1,
                        vehicles="8,9" if stale or added else "8", **{"pass": 1}))
    if repeat:
        out.append(log_line("R1", "execute", **common, reason="entry", inventory=2, cached=2,
                            vehicles="8,9", **{"pass": 2}))
        out.append(log_line("R1", "result", **common, reason="fleet_stale", inventory=2, cached=2,
                            vehicles="8,9", added=0, replaced=0, **{"pass": 2}))
    return out


def air(phase, rank, src, dst, reason, **fields):
    values = {"pass": 1, "cycle": 4, "id": f"air_{src}_{dst}", "rank": rank,
              "src": src, "dst": dst, "reason": reason, "finance": 60000,
              "available": 100000, "threshold": 10000, "built": 1,
              "bypass_before": 0, "bypass_after": 0, **fields}
    return log_line("R3", phase, **values)


FIRST = air("result", 0, 10, 20, "built", outcome="built", lines_before=0, lines_after=1)
STALE_THEN_VALID = [
    FIRST,
    air("examine", 1, 10, 30, "entry"),
    air("reject", 1, 10, 30, "batch_plan_dead"),
    air("examine", 2, 40, 50, "entry"),
    air("consume", 2, 40, 50, "eligible", bypass_after=1),
    air("attempt", 2, 40, 50, "executor", bypass_before=1, bypass_after=1),
    air("result", 2, 40, 50, "built", outcome="built", bypass_before=1, bypass_after=1,
        lines_before=1, lines_after=2),
]
TOO_EXPENSIVE = [FIRST, air("examine", 1, 40, 50, "entry", finance=120000),
                 air("stop", 1, 40, 50, "cash", finance=120000)]
REAL_REFUSAL = [FIRST, air("consume", 1, 40, 50, "eligible", bypass_after=1),
                air("attempt", 1, 40, 50, "executor", bypass_before=1, bypass_after=1),
                air("result", 1, 40, 50, "build_failed", outcome="rejected", error=771,
                    detail="BFAIL", bypass_before=1, bypass_after=1, lines_before=1, lines_after=1),
                air("stop", 2, 60, 70, "k_pass", bypass_before=1, bypass_after=1)]


def analyse(lines):
    return diag.analyse_text("\n".join(lines), evidence_kind="synthetic_fixture")


class ReaderContracts(unittest.TestCase):
    def test_fitted_one_without_execution_is_not_success(self):
        self.assertEqual(analyse(fleet_fixture()[:2])["trace_summary"]["r1_exact"], "incomplete")

    def test_actual_purchase_and_identity_inventory_are_required(self):
        report = analyse(fleet_fixture())
        self.assertEqual(report["trace_summary"]["r1_exact"], "pass")
        self.assertFalse(report["engine_validated"])
        self.assertEqual(report["evidence_kind"], "synthetic_fixture")
        self.assertEqual(report["economic_verdict"], "not_evaluated")

    def test_no_purchase_is_failure_not_full_success(self):
        self.assertEqual(analyse(fleet_fixture(added=0))["trace_summary"]["r1_exact"], "fail")

    def test_below_boundary_and_unrelated_rejection(self):
        self.assertEqual(analyse(fleet_fixture(budget=30999))["trace_summary"]["r1_below"], "pass")
        lines = [fleet_fixture(budget=30999)[0].replace("have=1", "have=2")]
        self.assertEqual(analyse(lines)["trace_summary"]["r1_below"], "non_expose")

    def test_stale_inventory_and_second_pass(self):
        self.assertEqual(analyse(fleet_fixture(stale=True))["trace_summary"]["r1_stale"], "pass")
        self.assertEqual(analyse(fleet_fixture(repeat=True))["trace_summary"]["r1_repeat"], "pass")

    def test_missing_price_and_reserve_are_not_zero(self):
        for field in ("price=30000", "reserve=10000", "buffer=1000", "cash=41000"):
            lines = fleet_fixture()
            lines[0] = lines[0].replace(field, "")
            self.assertEqual(analyse(lines)["trace_summary"]["r1_exact"], "non_expose")

    def test_final_rank_not_admitted(self):
        lines = fleet_fixture()
        lines[1] = lines[1].replace("rank=2", "rank=-1")
        self.assertEqual(analyse(lines)["trace_summary"]["r1_exact"], "incomplete")

    def test_duplicate_ids_and_inventory_are_not_silently_deduplicated(self):
        lines = fleet_fixture()
        self.assertEqual(analyse([lines[0]] + lines)["trace_summary"]["r1_exact"], "incomplete")
        lines[-1] = lines[-1].replace("vehicles=8,9", "vehicles=8,8")
        self.assertEqual(analyse(lines)["trace_summary"]["r1_exact"], "incomplete")

    def test_company_ids_are_not_script_ids_or_default_zero(self):
        lines = fleet_fixture()
        lines[-1] = lines[-1].replace("[0] [I]", "[1] [I]")
        self.assertEqual(analyse(lines)["trace_summary"]["r1_exact"], "incomplete")

    def test_invalid_prefix_or_test_gate_invalidates_trace(self):
        for text in ("R1R3 mechanism=R1 phase=fit", log_line("R1", "fit", test_only=0)):
            self.assertTrue(diag.analyse_text(text)["malformed_lines"])

    def test_r3_stale_continuation(self):
        self.assertEqual(analyse(STALE_THEN_VALID)["trace_summary"]["r3_dead"], "pass")

    def test_r3_stale_consumption_is_failure(self):
        lines = list(STALE_THEN_VALID)
        lines[2] = lines[2].replace("bypass_after=0", "bypass_after=1")
        self.assertEqual(analyse(lines)["trace_summary"]["r3_dead"], "fail")

    def test_r3_cash_does_not_promise_skipping_expensive_candidate(self):
        self.assertEqual(analyse(TOO_EXPENSIVE)["trace_summary"]["r3_cash"], "pass")
        extra = TOO_EXPENSIVE + [air("attempt", 2, 60, 70, "executor")]
        self.assertEqual(analyse(extra)["trace_summary"]["r3_cash"], "fail")

    def test_real_refusal_keeps_consumption(self):
        self.assertEqual(analyse(REAL_REFUSAL)["trace_summary"]["r3_failure"], "pass")
        lines = list(REAL_REFUSAL)
        lines[3] = lines[3].replace("bypass_after=1", "bypass_after=0")
        self.assertEqual(analyse(lines)["trace_summary"]["r3_failure"], "fail")

    def test_synthetic_refusal_and_site_checks_do_not_prove_api_refusal(self):
        for replacement in ("error=-1", "error=unknown", "error=0"):
            lines = [line.replace("error=771", replacement) for line in REAL_REFUSAL]
            self.assertEqual(analyse(lines)["trace_summary"]["r3_failure"], "non_expose")
        lines = [line.replace("reason=build_failed", "reason=siteB_unbuildable") for line in REAL_REFUSAL]
        self.assertEqual(analyse(lines)["trace_summary"]["r3_failure"], "non_expose")
        for detail in ("unknown", "PREA", "HANGAR"):
            lines = [line.replace("detail=BFAIL", "detail=" + detail) for line in REAL_REFUSAL]
            self.assertEqual(analyse(lines)["trace_summary"]["r3_failure"], "non_expose")

    def test_duplicate_fields_and_unknown_id_invalidate_stream(self):
        lines = fleet_fixture()
        for bad in (lines[0] + " id=f2", lines[0].replace("id=f1", "id=unknown")):
            self.assertEqual(analyse([bad] + lines[1:])["trace_summary"]["r1_exact"], "invalid")

    def test_ghost_line_is_failure(self):
        lines = list(REAL_REFUSAL)
        lines[3] = lines[3].replace("lines_after=1", "lines_after=2")
        self.assertEqual(analyse(lines)["trace_summary"]["r3_failure"], "fail")

    def test_passes_and_cycles_do_not_mix(self):
        for field in ("pass", "cycle"):
            lines = list(STALE_THEN_VALID)
            lines[2] = lines[2].replace(f"{field}={'1' if field == 'pass' else '4'}", f"{field}=99")
            self.assertEqual(analyse(lines)["trace_summary"]["r3_dead"], "non_expose")

    def test_duplicate_pass_is_ambiguous(self):
        self.assertEqual(analyse(STALE_THEN_VALID * 2)["trace_summary"]["r3_dead"], "incomplete")

    def test_missing_finance_and_threshold_do_not_become_zero(self):
        lines = [line.replace("threshold=10000", "threshold=unknown") for line in REAL_REFUSAL]
        self.assertEqual(analyse(lines)["trace_summary"]["r3_failure"], "non_expose")

    def test_empty_stream_is_non_exposed(self):
        self.assertEqual(set(analyse([])["trace_summary"].values()), {"non_expose"})

    def test_health_error_is_not_a_mechanism_failure(self):
        report = analyse(fleet_fixture() + ["dbg: [script:4] [0] [E] Your script made an error"])
        self.assertEqual(report["trace_summary"]["r1_exact"], "invalid")

    def test_changed_line_identity_cannot_pass(self):
        lines = fleet_fixture()
        lines[-1] = lines[-1].replace("line=7", "line=99")
        self.assertNotEqual(analyse(lines)["trace_summary"]["r1_exact"], "pass")


class IOContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Leave test artifacts in the only authorized result directory. No cleanup
        # of historical runs, no tempfile outside the assigned write scope.
        diag.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        cls.directory = Path(tempfile.mkdtemp(prefix="reader_fixtures_", dir=diag.OUTPUT_ROOT))
        diag.write_new(cls.directory / "provenance.json", {"kind": "synthetic_reader_fixtures", "engine_executed": False})

    def test_phase_isolation_and_reload_not_inferred(self):
        path = self.directory / "split_save_load.json"
        lines = fleet_fixture()
        diag.write_new(path, {"phase_a": {"openttd_output_raw": "\n".join(lines[:2])},
                              "phase_b": {"openttd_output_raw": "\n".join(lines[2:])}})
        report = diag.analyse_file(path)
        self.assertEqual(len(report["streams"]), 2)
        self.assertTrue(all(s["trace_summary"]["r1_exact"] != "pass" for s in report["streams"]))
        self.assertTrue(all(s["trace_summary"]["r1_reload"] == "non_expose" for s in report["streams"]))
        self.assertEqual(len(report["sha256"]), 64)

    def test_unsupported_schema_does_not_mean_zero_events(self):
        path = self.directory / "aggregate.json"
        diag.write_new(path, {"total": 12})
        self.assertEqual(diag.analyse_file(path)["coverage"], "no_supported_log_stream")

    def test_output_refuses_overwrite_and_escape(self):
        directory = diag.new_directory(self.directory / "exclusive")
        with self.assertRaises(FileExistsError):
            diag.new_directory(directory)
        with self.assertRaises(ValueError):
            diag.new_directory(diag.ROOT / "not_allowed")
        path = directory / "once.json"
        diag.write_new(path, {"sentinel": True})
        with self.assertRaises(FileExistsError):
            diag.write_new(path, {"sentinel": False})
        self.assertTrue(json.loads(path.read_text())["sentinel"])

    def test_prepare_no_runtime_import_or_launch(self):
        directory = self.directory / "prepare"
        with patch.object(diag, "run_smoke", side_effect=AssertionError("No game")):
            with contextlib.redirect_stdout(io.StringIO()):
                diag.main(["prepare", "--out", str(directory)])
        plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
        self.assertFalse(plan["engine_executed"])
        self.assertEqual(set(plan["scenarios"]), set(diag.SCENARIOS))
        self.assertEqual(plan["workers"], 1)

    def test_smoke_requires_both_central_confirmations_before_writing(self):
        for flag in ([], ["--centralized"], ["--sources-stable"]):
            target = self.directory / "must_not_exist"
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                diag.main(["smoke", "--out", str(target), *flag])
            self.assertFalse(target.exists())

    def test_copy_only_changes_test_gate(self):
        target = diag.stage_ai(diag.new_directory(self.directory / "staged"))
        source = diag.ROOT / "ai/OpexAI"
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            copied = target / path.relative_to(source)
            if path.name == "projects_selection.nut":
                self.assertEqual(copied.read_text(encoding="utf-8"),
                                 path.read_text(encoding="utf-8").replace(diag.GATE, diag.GATE.replace("= 0", "= 1")))
            else:
                self.assertEqual(copied.read_bytes(), path.read_bytes())
        self.assertIn(diag.GATE, (source / "projects_selection.nut").read_text(encoding="utf-8"))


class SquirrelSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection = (diag.ROOT / "ai/OpexAI/projects_selection.nut").read_text(encoding="utf-8")
        cls.task = (diag.ROOT / "ai/OpexAI/task_projects.nut").read_text(encoding="utf-8")

    def test_gate_declared_and_off(self):
        self.assertEqual(self.selection.count(diag.GATE), 1)
        self.assertIn("R1_R3_TEST_SEQ <- 0;", self.selection)
        self.assertIn("R1_R3_TEST_PASS <- 0;", self.selection)

    def test_fit_trace_is_after_real_fit_before_common_ranking(self):
        start = self.selection.index("function OpexProjectSelectAffordable(")
        code = self.selection[start:]
        self.assertLess(code.index("OpexProjectFitFleetToBudget(project, capitalBudget)"), code.index("OpexR1R3FitTrace("))
        self.assertLess(code.index("OpexR1R3FitTrace("), code.index('project.fundScore <-'))

    def test_no_repeat_physical_checks_or_second_purchase(self):
        start = self.task.index("function OpexAI::_tryBuildProjects(")
        self.assertEqual(self.task[start:].count("OpexAirBatchPlanStillLive("), 1)
        fleet = self.task.split("function OpexAI::_tryBuildFleetProject(", 1)[1].split("\nfunction ", 1)[0]
        self.assertEqual(fleet.count("local grown = OpexAirAddPlane("), 1)
        self.assertLess(fleet.index("local grown = OpexAirAddPlane("), fleet.index("phase=api_result"))
        self.assertEqual(self.task.count("c75BypassConsumed = true;"), 1)

    def test_gate_only_emits_not_policy_or_fault_injection(self):
        helper = self.selection.split("function OpexR1R3FitTrace(", 1)[1].split("\nfunction ", 1)[0]
        self.assertIn("local traced = clone fitted;", helper)
        for forbidden in ("SetLoanAmount", "BuildVehicle", "BuildAirport", "SetSetting"):
            self.assertNotIn(forbidden, helper)
        self.assertIn('"cash_note", "cash"', self.task)  # below-K cash note isn't a break


if __name__ == "__main__":
    unittest.main()