#!/usr/bin/env python3
"""Contrats V95 item 1 : ledger observatoire des tours de file inutiles."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "sweeps"))

from analyse_sched_idle import (  # noqa: E402
    PREDICTABLE_REASONS,
    SchedIdleTracker,
    _stats,
    parse_sched_idle_output,
    summarize_events,
)
from c65_pass3 import EXPECTED_TASKS, extract_main_task_queue  # noqa: E402

AI = ROOT / "ai" / "OpexAI"


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _fn_body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start:idx + 1]
    raise AssertionError("unterminated " + signature)


def _scan_loop(run_next):
    start = run_next.index("for (local index = this._taskCursor;")
    due = run_next.index("task.dueCycle = this._taskCycle + 1;")
    return run_next[start:due]


def unguarded_schedidle_calls(text):
    """Positions `_schedIdle*` hors definition, hors commentaire, hors garde V95."""
    covered = set()
    for match in re.finditer(r"if \(V95_SCHED_IDLE_LEDGER\) \{", text):
        start = match.start()
        depth = 0
        for idx in range(text.index("{", start), len(text)):
            if text[idx] == "{":
                depth += 1
            elif text[idx] == "}":
                depth -= 1
                if depth == 0:
                    covered.update(range(start, idx + 1))
                    break
    for match in re.finditer(r"V95_SCHED_IDLE_LEDGER \? [^\n]+", text):
        covered.update(range(match.start(), match.end()))
    for match in re.finditer(r"if \(V95_SCHED_IDLE_LEDGER\) [^\n]+", text):
        covered.update(range(match.start(), match.end()))
    unguarded = []
    for match in re.finditer(r"_schedIdle\w+", text):
        start = match.start()
        line_start = text.rfind("\n", 0, start) + 1
        line = text[line_start:text.find("\n", start)]
        stripped = line.strip()
        if stripped.startswith("function ") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        if start in covered:
            continue
        if "V95_SCHED_IDLE_LEDGER" in line:
            continue
        unguarded.append(stripped)
    return unguarded


class TestSchedIdleAccumulator(unittest.TestCase):
    def test_selected_increments_once_per_selection(self):
        tr = SchedIdleTracker()
        tr.on_selected("catalog", 1, 10)
        tr.note(True, "catalog_refresh", "work")
        tr.finish(1, 11, ops=100, days=0, ticks=1)
        self.assertEqual(tr.by_task["catalog"]["selected"], 1)
        tr.on_selected("catalog", 2, 20)
        tr.note(False, "catalog_fresh", "pred")
        tr.finish(2, 21, ops=8, days=0, ticks=1)
        self.assertEqual(tr.by_task["catalog"]["selected"], 2)

    def test_noop_increments_reason(self):
        tr = SchedIdleTracker()
        tr.on_selected("report", 5, 50)
        tr.note(False, "report_same_year", "pred")
        rec = tr.finish(5, 51, ops=9, days=0, ticks=1)
        self.assertEqual(rec["w"], 0)
        self.assertEqual(rec["r"], "report_same_year")
        self.assertEqual(tr.by_task["report"]["noop"], 1)
        self.assertEqual(tr.by_task["report"]["did_work"], 0)
        self.assertEqual(tr.reasons[("report", "report_same_year")], 1)
        self.assertEqual(tr.by_task["report"]["pred"], 1)

    def test_did_work_increments(self):
        tr = SchedIdleTracker()
        tr.on_selected("projects", 8, 80)
        tr.note(True, "projects_useful", "work", examined=1, sub_field="built")
        rec = tr.finish(10, 90, ops=3000, days=2, ticks=10)
        self.assertEqual(rec["w"], 1)
        self.assertEqual(tr.by_task["projects"]["did_work"], 1)
        self.assertEqual(tr.by_task["projects"]["noop"], 0)

    def test_age_resets_only_on_true_work(self):
        tr = SchedIdleTracker()
        # 1er tour : noop (repay_same_month), pas d'age prealable
        tr.on_selected("repay", 30, 300)
        tr.note(False, "repay_same_month", "pred")
        rec = tr.finish(30, 301, ops=5, days=0, ticks=1)
        self.assertEqual(rec["ad"], -1)
        self.assertEqual(rec["at"], -1)
        self.assertNotIn("repay", tr.last_work_date)

        # 2e tour : vrai travail
        tr.on_selected("repay", 40, 400)
        tr.note(True, "repay_work", "work")
        rec = tr.finish(40, 410, ops=40, days=0, ticks=10)
        self.assertEqual(rec["ad"], -1)
        self.assertEqual(tr.last_work_date["repay"], 40)
        self.assertEqual(tr.last_work_tick["repay"], 410)

        # 3e tour : no-op a t=45/tick=450 -> age = 5 jours, 40 ticks. N'ecrase PAS last_work
        tr.on_selected("repay", 45, 450)
        tr.note(False, "repay_same_month", "pred")
        rec = tr.finish(45, 451, ops=5, days=0, ticks=1)
        self.assertEqual(rec["ad"], 5)
        self.assertEqual(rec["at"], 40)
        self.assertEqual(tr.last_work_date["repay"], 40)
        self.assertEqual(tr.last_work_tick["repay"], 410)

        # 4e tour : vrai travail a t=70/tick=700 -> age = 30 jours, 290 ticks. Reinitialise last_work
        tr.on_selected("repay", 70, 700)
        tr.note(True, "repay_work", "work")
        rec = tr.finish(70, 701, ops=40, days=0, ticks=1)
        self.assertEqual(rec["ad"], 30)
        self.assertEqual(rec["at"], 290)
        self.assertEqual(tr.last_work_date["repay"], 70)
        self.assertEqual(tr.last_work_tick["repay"], 701)

    def test_projects_gap_counts_background_tasks(self):
        tr = SchedIdleTracker()
        # 1er passage utile
        tr.on_selected("projects", 10, 100)
        tr.note(True, "projects_useful", "work", 1, "built")
        rec = tr.finish(10, 110, 100, 0, 10)
        self.assertEqual(rec["bg"], 0)
        self.assertEqual(rec["gap_d"], -1)

        # Taches d'arriere-plan (dont projects_empty et projects_examined_no_effect qui NE SONT PAS utiles)
        for name, work, reason, cls in (
            ("expand", False, "expand_no_work", "after"),
            ("refleet", False, "refleet_no_work", "after"),
            ("town_growth", True, "town_growth_work", "work"),
            ("repay", False, "repay_same_month", "pred"),
            ("catalog", False, "catalog_fresh", "pred"),
            ("projects", False, "projects_empty", "after"),
            ("projects", False, "projects_examined_no_effect", "after"),
        ):
            tr.on_selected(name, 11, 111)
            tr.note(work, reason, cls)
            tr.finish(11, 112, 10, 0, 1)

        # 7 taches traversees au total, 1 avec vrai travail
        self.assertEqual(tr.since_sel, 7)
        self.assertEqual(tr.since_work, 1)

        # 2e passage utile de projects : reset des compteurs et enregistrement de l'intervalle
        tr.on_selected("projects", 20, 200)
        tr.note(True, "projects_useful", "work", 1, "built")
        rec = tr.finish(20, 210, 200, 0, 10)
        self.assertEqual(rec["bg"], 7)
        self.assertEqual(rec["bgw"], 1)
        self.assertEqual(rec["gap_d"], 10)
        self.assertEqual(tr.since_sel, 0)
        self.assertEqual(tr.since_work, 0)

    def test_median_le_max_and_mean_ge_half_median(self):
        """Proprietes mathematiques obligatoires sur distributions >= 0."""
        distributions = [
            [0, 0, 0, 100],
            [10, 20, 30, 40, 50],
            [1000],
            [5, 5, 5, 5],
            [0, 10, 10, 10, 10],
            [1, 2, 3, 4, 100, 200, 1000],
            [0, 0, 0, 0, 1, 2, 5, 10, 20],
        ]
        for dist in distributions:
            st = _stats(dist)
            self.assertLessEqual(st["median"], st["max"], f"median > max in {dist}")
            self.assertGreaterEqual(st["mean"], 0.5 * st["median"], f"mean < 0.5*median in {dist}")
            self.assertLessEqual(st["min"], st["median"], f"min > median in {dist}")
            self.assertLessEqual(st["p90"], st["max"], f"p90 > max in {dist}")

    def test_consistency_of_totals_between_tables(self):
        """Coherence stricte et exacte des totaux entre by_task, years, reasons et seed_year."""
        events = []
        # Graine 42 : 1970 complet (12 mois), 1971 complet (12 mois), 1972 complet (12 mois)
        for y in (1970, 1971, 1972):
            for m in range(1, 13):
                events.append({
                    "seed": 42, "year": y, "month": m, "day": 1,
                    "t": "catalog", "w": 0, "r": "catalog_fresh", "cls": "pred",
                    "op": 20, "d": 0, "tk": 1, "ad": -1, "at": -1,
                })
                events.append({
                    "seed": 42, "year": y, "month": m, "day": 15,
                    "t": "projects", "w": 1, "r": "projects_useful", "cls": "work",
                    "op": 5000, "d": 1, "tk": 10, "ad": -1, "at": -1, "gap_d": 30, "bg": 5, "bgw": 0,
                })
                events.append({
                    "seed": 42, "year": y, "month": m, "day": 20,
                    "t": "projects", "w": 0, "r": "projects_empty", "cls": "after",
                    "op": 10, "d": 0, "tk": 1, "ad": -1, "at": -1,
                })
        # Graine 100 : 1970 complet (12 mois), 1971 complet (12 mois), 1972 complet (12 mois), 1973 partiel (5 mois)
        for y in (1970, 1971, 1972):
            for m in range(1, 13):
                events.append({
                    "seed": 100, "year": y, "month": m, "day": 5,
                    "t": "repay", "w": 0, "r": "repay_same_month", "cls": "pred",
                    "op": 15, "d": 0, "tk": 0, "ad": -1, "at": -1,
                })
        # 1973 partiel (doit etre exclu des annees completes 1970-1972)
        for m in range(1, 6):
            events.append({
                "seed": 100, "year": 1973, "month": m, "day": 5,
                "t": "repay", "w": 0, "r": "repay_same_month", "cls": "pred",
                "op": 15, "d": 0, "tk": 0, "ad": -1, "at": -1,
            })

        summary = summarize_events(events)
        self.assertEqual(summary["complete_years"], [1970, 1971, 1972])
        # Verifier que les totaux se recoupent
        task_sel = sum(r["selected"] for r in summary["by_task"])
        year_sel = sum(v["selected"] for v in summary["years"].values())
        reason_n = sum(r["n"] for r in summary["reasons"])
        sy_comp_sel = sum(sy["selected"] for sy in summary["seed_year_breakdown"] if sy["year"] in summary["complete_years"])
        self.assertEqual(task_sel, summary["total_selected"])
        self.assertEqual(year_sel, summary["total_selected"])
        self.assertEqual(reason_n, summary["total_selected"])
        self.assertEqual(sy_comp_sel, summary["total_selected"])

    def test_class_iff_did_work(self):
        """classe work <==> did_work == 1 obligatoire."""
        # 1. Evenement valide work
        ev_ok_work = {"seed": 1, "year": 1970, "month": 1, "t": "catalog", "w": 1, "r": "catalog_refresh", "cls": "work", "op": 10, "d": 0, "tk": 1}
        # 2. Evenement valide no-op
        ev_ok_noop = {"seed": 1, "year": 1970, "month": 1, "t": "catalog", "w": 0, "r": "catalog_fresh", "cls": "pred", "op": 10, "d": 0, "tk": 1}
        summary = summarize_events([ev_ok_work, ev_ok_noop])
        self.assertEqual(summary["total_selected"], 0)  # non complet car seulement mois 1, mais pas d'erreur de validation

        # 3. Violation 1 : w=0 avec cls='work' doit lever AssertionError
        ev_bad1 = {"seed": 1, "year": 1970, "month": 1, "t": "scrap", "w": 0, "r": "scrap_no_work", "cls": "work", "op": 10, "d": 0, "tk": 1}
        with self.assertRaises(AssertionError):
            summarize_events([ev_bad1])

        # 4. Violation 2 : w=1 avec cls='after' doit lever AssertionError
        ev_bad2 = {"seed": 1, "year": 1970, "month": 1, "t": "repay", "w": 1, "r": "repay_work", "cls": "after", "op": 10, "d": 0, "tk": 1}
        with self.assertRaises(AssertionError):
            summarize_events([ev_bad2])

    def test_stats_by_reason_on_known_fixture(self):
        """Cout par raison calcule independamment sur les echantillons du couple (tache, raison)."""
        events = []
        for m in range(1, 13):
            # catalog_fresh (no-op pred) : 10, 20, 30 opcodes, 0 jours, 1 tick
            events.append({"seed": 1, "year": 1970, "month": m, "day": 1, "t": "catalog", "w": 0, "r": "catalog_fresh", "cls": "pred", "op": 10 + m, "d": 0, "tk": 1})
            # catalog_refresh (work) : 600 000 opcodes, 2 jours, 80 ticks
            events.append({"seed": 1, "year": 1970, "month": m, "day": 15, "t": "catalog", "w": 1, "r": "catalog_refresh", "cls": "work", "op": 600000, "d": 2, "tk": 80})

        summary = summarize_events(events)
        reasons_map = {(r["task"], r["reason"]): r for r in summary["reasons"]}

        fresh = reasons_map[("catalog", "catalog_fresh")]
        self.assertEqual(fresh["n"], 12)
        self.assertEqual(fresh["skip_class"], "pred")
        self.assertEqual(fresh["days_sum"], 0)
        self.assertEqual(fresh["days_mean"], 0.0)
        self.assertLess(fresh["ops_median"], 30)

        refresh = reasons_map[("catalog", "catalog_refresh")]
        self.assertEqual(refresh["n"], 12)
        self.assertEqual(refresh["skip_class"], "work")
        self.assertEqual(refresh["days_sum"], 24)
        self.assertEqual(refresh["days_mean"], 2.0)
        self.assertEqual(refresh["ops_median"], 600000)

        # Le cout de catalog_fresh est distinct et independant de catalog_refresh
        self.assertNotEqual(fresh["ops_mean"], refresh["ops_mean"])

    def test_monthly_yearly_attribution_and_coverage(self):
        log = "\n".join([
            *[f"OPEX 1970-{m}-15 SCHED_IDLE t=catalog w=0 r=catalog_fresh cls=pred op=10 d=0 tk=1 ad=-1 at=-1" for m in range(1, 13)],
            *[f"OPEX 1971-{m}-15 SCHED_IDLE t=catalog w=0 r=catalog_fresh cls=pred op=10 d=0 tk=1 ad=-1 at=-1" for m in range(1, 13)],
            *[f"OPEX 1972-{m}-15 SCHED_IDLE t=catalog w=0 r=catalog_fresh cls=pred op=10 d=0 tk=1 ad=-1 at=-1" for m in range(1, 13)],
            *[f"OPEX 1973-{m}-15 SCHED_IDLE t=catalog w=0 r=catalog_fresh cls=pred op=10 d=0 tk=1 ad=-1 at=-1" for m in range(1, 12)],
        ])
        parsed = parse_sched_idle_output(log)
        summary = summarize_events(parsed["events"])
        self.assertEqual(summary["complete_years"], [1970, 1971, 1972])
        self.assertNotIn(1973, summary["years"])
        self.assertEqual(summary["coverage_by_seed_year"]["s0_y1970"], "12/12")
        self.assertEqual(summary["coverage_by_seed_year"]["s0_y1971"], "12/12")
        self.assertEqual(summary["coverage_by_seed_year"]["s0_y1972"], "12/12")
        self.assertEqual(summary["coverage_by_seed_year"]["s0_y1973"], "11/12")


class TestSchedIdleSourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.globals = _read("ai/OpexAI/globals_pre.nut")
        cls.settings = _read("ai/OpexAI/settings.nut")
        cls.info = _read("ai/OpexAI/info.nut")
        cls.scheduler = _read("ai/OpexAI/scheduler.nut")
        cls.tasks = _read("ai/OpexAI/scheduler_tasks.nut")
        cls.main = _read("ai/OpexAI/main.nut")
        cls.ledgers = _read("ai/OpexAI/ledgers.nut")
        cls.probes = _read("ai/OpexAI/probes.nut")
        cls.run_next = _fn_body(cls.scheduler, "function OpexAI::_runNextTask()")

    def test_probe_default_off_and_wired_to_probe_scheduler(self):
        self.assertIn("V95_SCHED_IDLE_LEDGER <- false;", self.globals)
        self.assertIn("V95_SCHED_IDLE_LEDGER = probeScheduler;", self.settings)
        self.assertIn('name = "probe_scheduler"', self.info)
        self.assertIn("Enable scheduler opcode, latency and idle-tour diagnostic ledgers (C41, C39, V95)", self.info)
        block = self.info[self.info.index('name = "probe_scheduler"'):]
        block = block[:block.index("});")]
        self.assertIn("custom_value = 0", block)

    def test_queue_order_and_due_cycle_untouched(self):
        self.assertEqual(extract_main_task_queue(self.main), EXPECTED_TASKS)
        self.assertIn("this._taskCursor = (taskIndex + 1) % this._taskQueue.len();", self.run_next)
        self.assertIn("task.dueCycle = this._taskCycle + 1;", self.run_next)
        scan = _scan_loop(self.run_next)
        self.assertNotIn("V95_SCHED_IDLE_LEDGER", scan)
        self.assertNotIn("_lastReportYear", scan)
        self.assertNotIn("_lastRepayMonth", scan)
        self.assertNotIn("_lastCatalogMonth", scan)
        self.assertNotIn("skip-not-due", scan)
        self.assertIn("candidate.enabled && candidate.dueCycle <= this._taskCycle", scan)

    def test_probe_does_not_enable_experimental_skip_admission(self):
        # P7 existe desormais derriere son propre flag OFF ; la sonde V95
        # reste observatoire et ne doit jamais armer ce chemin de decision.
        self.assertIn("EXP_SCHEDULER_SKIP_NOT_DUE <- false;", self.globals)
        self.assertIn('EXP_SCHEDULER_SKIP_NOT_DUE = AIController.GetSetting("exp_scheduler_skip_not_due") != 0;', self.settings)
        self.assertNotIn("EXP_SCHEDULER_SKIP_NOT_DUE = probeScheduler", self.settings)
        self.assertIn("if (EXP_SCHEDULER_SKIP_NOT_DUE) {", self.run_next)
        self.assertNotIn("V95_SCHED_IDLE_LEDGER", _scan_loop(self.run_next))
        for signature in ("function OpexAI::_schedIdlePreDispatch()",
                          "function OpexAI::_schedIdlePostDispatch(taskName, ran, ops, days, ticks)"):
            self.assertNotIn("OpexExpSchedulerSelectTask", _fn_body(self.ledgers + self.probes, signature))
        self.assertIn("AIController.Sleep(1);", self.main)

    def test_added_idle_code_is_probe_guarded(self):
        idle_fns = [
            "function OpexAI::_schedIdleEnsure()",
            "function OpexAI::_schedIdlePreDispatch()",
            "function OpexAI::_schedIdlePostDispatch(taskName, ran, ops, days, ticks)",
            "function OpexSchedIdleLog(kind, fields)",
        ]
        sources = self.ledgers + "\n" + self.probes
        for sig in idle_fns:
            body = _fn_body(sources, sig)
            self.assertIn("V95_SCHED_IDLE_LEDGER", body[:120], sig)

        for label, text in (
            ("scheduler.nut", self.scheduler),
            ("scheduler_tasks.nut", self.tasks),
        ):
            unguarded = unguarded_schedidle_calls(text)
            self.assertEqual(unguarded, [], f"{label}: {unguarded}")

    def test_dispatchers_keep_historical_returns(self):
        report = _fn_body(self.tasks, "function OpexAI::_dispatchReport(task, year)")
        self.assertIn("if (this._lastReportYear == year)", report)
        self.assertNotIn("_schedIdle", report)
        self.assertNotIn("V95", report)

        repay = _fn_body(self.tasks, "function OpexAI::_dispatchRepay(task, year)")
        self.assertIn("if (this._lastRepayMonth == ym)", repay)
        self.assertNotIn("_schedIdle", repay)
        self.assertNotIn("V95", repay)

        catalog = _fn_body(self.tasks, "function OpexAI::_dispatchCatalog(task, year)")
        self.assertNotIn("_schedIdle", catalog)
        self.assertNotIn("V95", catalog)

        projects = _fn_body(self.tasks, "function OpexAI::_dispatchProjects(task, year)")
        self.assertIn("if (this._portfolioInvalidated)", projects)
        self.assertIn("return this._tryBuildProjects(year);", projects)
        self.assertNotIn("_schedIdle", projects)
        self.assertNotIn("V95", projects)

        expand = _fn_body(self.tasks, "function OpexAI::_dispatchExpand(task, year)")
        self.assertIn("this._expandRailLines(year);", expand)
        self.assertIn("return true;", expand)
        self.assertNotIn("_schedIdle", expand)
        self.assertNotIn("V95", expand)

        wrap = _fn_body(self.scheduler, "function OpexAI::_runNextTaskWithSlackLedger()")
        self.assertIn("this._schedIdlePreDispatch();", wrap)
        self.assertIn("this._schedIdlePostDispatch(taskName, ran, taskOps, passDays, passTicks);", wrap)

    def test_ops_use_existing_measure_helpers(self):
        post = _fn_body(self.ledgers, "function OpexAI::_schedIdlePostDispatch(taskName, ran, ops, days, ticks)")
        self.assertNotIn("OpexOpsMeasureBegin()", post)
        self.assertNotIn("OpexOpsMeasureEnd", post)
        wrap = _fn_body(self.scheduler, "function OpexAI::_runNextTaskWithSlackLedger()")
        self.assertIn("OpexOpsMeasureBegin()", wrap)
        self.assertIn("C39_PASS_CLOCK_LEDGER", wrap)
        self.assertIn("this._schedIdlePostDispatch(taskName, ran, taskOps, passDays, passTicks);", wrap)


if __name__ == "__main__":
    unittest.main()
