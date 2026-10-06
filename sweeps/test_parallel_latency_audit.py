"""Contrats du parseur hors ligne, sans moteur ni écriture de fixtures."""
import unittest

from parallel_latency_audit import audit_text, classify, distribution, parse_log


def log(day, body, owner=0):
    return f"dbg: [script:4] [{owner}] [I] OPEX {day} {body}"


def analyze(*lines):
    return audit_text("\n".join(lines), "fixture.log")


class LatencyAuditTests(unittest.TestCase):
    def test_missing_is_not_zero(self):
        result = analyze(log("1970-1-1", "SCHED_IDLE t=report r=report_same_year"))
        s = result["streams"][0]["summaries"]["scheduler:report:report_same_year"]
        self.assertEqual(s["days"], {"eligible": 1, "n": 0, "missing": 1, "median": None, "p95": None, "max": None})

    def test_actual_zero(self):
        result = analyze(log("1970-1-1", "SCHED_IDLE t=report r=report_same_year d=0 tk=0 op=0"))
        self.assertEqual(result["streams"][0]["intervals"][0]["ops_proxy"], 0)

    def test_year_and_leap_boundaries(self):
        r = analyze(log("1971-12-31", "TASK name=catalog"), log("1972-3-1", "TASK name=projects"))
        self.assertEqual(r["streams"][0]["intervals"][0]["days"], 61)

    def test_interleaved_worker_uses_step_ops(self):
        r = analyze(log("1970-1-1", "C56_TASK WORKER_ENTER name=rail_search cycle=- tick=1 opsclk=10000"),
                    log("1970-1-2", "C56_TASK TASK_ENTER name=report cycle=8 tick=10 opsclk=100000"),
                    log("1970-1-2", "C56_TASK TASK_EXIT name=report cycle=8 tick=12 opsclk=120000"),
                    log("1970-1-3", "C56_TASK WORKER_EXIT name=rail_search cycle=- tick=50 opsclk=500000 step_ops=123"))
        worker = r["streams"][0]["intervals"][-1]
        self.assertEqual((worker["days"], worker["ticks"], worker["ops_proxy"]), (2, 49, 123))

    def test_incomplete_and_wrong_cycle(self):
        r = analyze(log("1970-1-1", "C56_TASK TASK_ENTER name=catalog cycle=2 tick=1 opsclk=1"),
                    log("1970-1-2", "C56_TASK TASK_EXIT name=catalog cycle=3 tick=2 opsclk=2"))
        self.assertEqual(r["streams"][0]["intervals"], [])
        self.assertEqual(len(r["streams"][0]["issues"]), 2)

    def test_repeated_enter_is_ambiguous(self):
        r = analyze(log("1970-1-1", "C56_TASK TASK_ENTER name=catalog cycle=2 tick=1 opsclk=1"),
                    log("1970-1-2", "C56_TASK TASK_ENTER name=catalog cycle=2 tick=2 opsclk=2"),
                    log("1970-1-3", "C56_TASK TASK_EXIT name=catalog cycle=2 tick=3 opsclk=3"))
        self.assertFalse(r["streams"][0]["intervals"])

    def test_companies_never_paired(self):
        r = analyze(log("1970-1-1", "TASK name=catalog", 0), log("1970-2-1", "TASK name=projects", 1))
        self.assertEqual(len(r["streams"]), 2)
        self.assertTrue(all(not s["intervals"] for s in r["streams"]))

    def test_reload_and_clock_rewind_split(self):
        r = analyze(log("1970-1-1", "TASK name=catalog"), log("1971-1-1", "LOAD_RECONCILE saved=2"),
                    log("1971-1-2", "TASK name=report"), log("1970-1-1", "TASK name=catalog"))
        self.assertEqual(len(r["streams"]), 3)
        self.assertTrue(all(not s["intervals"] for s in r["streams"]))

    def test_silence_not_catalog_duration(self):
        r = analyze(log("1970-1-1", "TASK name=catalog"), log("1970-2-1", "TASK name=report"))
        item = r["streams"][0]["intervals"][0]
        self.assertEqual((item["category"], item["metric"], item["ops_proxy"]), ("cause_inconnue", "dispatch_gap", None))

    def test_watcher_summary_not_poll_distribution(self):
        r = analyze(log("1970-1-1", "C78_SLOT phase=c83_poll_summary polls=1 max_gap_days=0"),
                    log("1970-2-1", "C78_SLOT phase=c83_poll_summary polls=8 max_gap_days=20"))
        self.assertFalse(r["streams"][0]["intervals"])
        self.assertEqual(len(r["streams"][0]["observations"]), 2)

    def test_watcher_window_not_initial_or_exact_delay(self):
        r = analyze(log("1970-1-1", "C78_SLOT phase=c83_poll_state initial=1 seen_before=-1 detected=10"),
                    log("1970-1-5", "C78_SLOT phase=c83_poll_state initial=0 seen_before=10 detected=14"))
        self.assertEqual(len(r["streams"][0]["intervals"]), 1)
        self.assertEqual(r["streams"][0]["intervals"][0]["days"], 4)

    def test_choice_build_interleaving_and_identifiers(self):
        r = analyze(log("1970-12-31", "PROJECT_CHOSEN mode=air src=1 dst=2"),
                    log("1970-12-31", "PROJECT_CHOSEN mode=air src=3 dst=4"),
                    log("1971-1-2", "AIR_BUILD src=1 dst=2 line=0"))
        i = r["streams"][0]["intervals"][0]
        self.assertEqual(i["days"], 2)
        self.assertEqual(i["identity"]["line"], "0")
        self.assertEqual(i["start"]["line"], 1)
        self.assertEqual(i["end"]["line"], 3)

    def test_stale_choice_never_pairs_after_discard(self):
        r = analyze(log("1970-1-1", "PROJECT_CHOSEN mode=air src=1 dst=2"),
                    log("1970-1-2", "PROJECT_DISCARD src=1 dst=2 reason=batch_plan_dead"),
                    log("1970-1-3", "AIR_BUILD src=1 dst=2 line=0"))
        self.assertFalse(r["streams"][0]["intervals"])
        self.assertEqual(r["streams"][0]["observations"][-1]["category"], "candidat_caduc")

    def test_finance_refusal_has_no_invented_wait(self):
        r = analyze(log("1970-1-1", "C50_CHRONO phase=refused_cash mode=air need=12"))
        self.assertFalse(r["streams"][0]["intervals"])
        self.assertEqual(r["streams"][0]["observations"][0]["category"], "attente_financiere")

    def test_p2_explicit_id(self):
        r = analyze(log("1970-12-31", "P2_BUILD id=7 cause=all_unaffordable"),
                    log("1971-1-2", "P2_RESOLVE id=7 days=2 ticks=37 ret_reason=capital"))
        i = r["streams"][0]["intervals"][0]
        self.assertEqual((i["days"], i["ticks"], i["category"]), (2, 37, "attente_financiere"))

    def test_p2_censored(self):
        r = analyze(log("1970-12-31", "P2_BUILD id=7 cause=all_unaffordable"),
                    log("1971-1-2", "P2_RESOLVE id=7 days=2 ticks=37 ret_reason=sim_end"))
        self.assertFalse(r["streams"][0]["intervals"])

    def test_invalid_date_and_truncated_numeric(self):
        events, issues = parse_log(log("1970-2-30", "TASK name=catalog"), "x")
        self.assertFalse(events)
        self.assertEqual(len(issues), 1)
        r = analyze(log("1970-1-1", "SCHED_IDLE t=catalog op=partial d=-1 tk=oops"))
        self.assertIsNone(r["streams"][0]["intervals"][0]["ops_proxy"])

    def test_p95_linear_and_empty(self):
        self.assertEqual(distribution([0, 10, None])["p95"], 9.5)
        self.assertIsNone(distribution([])["median"])

    def test_units_never_converted(self):
        r = analyze(log("1970-1-1", "AIR_PLAN_PERF days=1 ticks=19 total_ops=777"))
        i = r["streams"][0]["intervals"][0]
        self.assertEqual((i["days"], i["ticks"], i["ops_proxy"]), (None, 19, 777))
        self.assertEqual(i["legacy_days_tick74"], 1)
        self.assertEqual(i["category"], "cause_inconnue")

    def test_unknown_not_default_finance(self):
        self.assertEqual(classify({"reason": "plan_failed"}), "cause_inconnue")

    def test_repeated_ready_search_not_mixed_with_active_work(self):
        r = analyze(log("1970-1-1", "P5_RAIL_SEARCH id=1 slices=3 days=20 ticks=100 ops=500"),
                    log("1970-1-1", "P5_RAIL_SEARCH id=2 slices=0 days=0 ticks=0 ops=0"))
        s = r["streams"][0]["summaries"]
        self.assertEqual(s["rail_search:active_slices"]["days"]["median"], 20)
        self.assertEqual(s["rail_search:no_measured_slices"]["days"]["median"], 0)

    def test_search_missing_metric_stays_missing(self):
        r = analyze(log("1970-1-1", "P5_RAIL_SEARCH id=1 slices=1 ticks=10"))
        self.assertIsNone(r["streams"][0]["intervals"][0]["days"])

    def test_nested_stages_not_summed_with_parent(self):
        r = analyze(log("1970-1-1", "C56_TASK TASK_ENTER name=catalog cycle=2 tick=0 opsclk=0"),
                    log("1970-1-2", "C56_TASK STAGE_ENTER name=c56_stage_rail cycle=- tick=1 opsclk=10"),
                    log("1970-1-3", "C56_TASK STAGE_EXIT name=c56_stage_rail cycle=- tick=2 opsclk=20"),
                    log("1970-1-4", "C56_TASK TASK_EXIT name=catalog cycle=2 tick=3 opsclk=30"))
        self.assertEqual(len(r["streams"][0]["summaries"]), 2)

    def test_multiple_choices_without_id_are_not_forced(self):
        r = analyze(log("1970-1-1", "PROJECT_CHOSEN mode=air src=1 dst=2"),
                    log("1970-1-2", "PROJECT_CHOSEN mode=air src=1 dst=2"),
                    log("1970-1-3", "AIR_BUILD src=1 dst=2 line=0"))
        self.assertFalse(r["streams"][0]["intervals"])


if __name__ == "__main__":
    unittest.main()