"""P7: source contracts and bounded-scan model, NOT Squirrel execution.

Run with unittest after integrator wiring; no OpenTTD/Docker dependency.
The model checks ordering, deadlines and fairness; source contracts bind its
critical rules to scheduler.nut and to the real dispatcher early returns.
Compilation, dates across VM suspensions and Save/Load still need engine checks.
"""

from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def uncomment(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def compact(text):
    return " ".join(uncomment(text).split())


def function_body(source, name):
    """Extract these functions after stripping comments (not a general parser)."""
    text = uncomment(source)
    start = text.index("{", text.index("function " + name + "("))
    depth = 1
    end = start + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start + 1 : end - 1]


@dataclass
class Task:
    name: str
    due: int = 0
    enabled: bool = True


@dataclass
class State:
    tasks: list[Task]
    cursor: int = 0
    cycle: int = 0
    projects_present: bool = True
    last_report: int = -1
    last_repay: int = -1


def skip_reason(state, task, year, month):
    if not state.projects_present:
        return None
    if task.name == "report" and state.last_report == year:
        return "report_same_year"
    if task.name == "repay" and state.last_repay == year * 12 + month:
        return "repay_same_month"
    return None


def select(state, year=1970, month=1):
    """Model selector + common scheduler deadline/cursor updates, no dispatch."""
    count = len(state.tasks)
    if not count:
        return None, [], []
    index = state.cursor
    selected = None
    visited = []
    skipped = []
    for _ in range(count):
        if index >= count:
            state.cycle += 1
            index = 0
        task = state.tasks[index]
        visited.append(index)
        if task.enabled and task.due <= state.cycle:
            reason = skip_reason(state, task, year, month)
            if reason is None:
                selected = index
                break
            task.due = state.cycle + 1
            skipped.append((index, reason))
        index += 1
    if index >= count:
        state.cycle += 1
        index = 0
    state.cursor = index
    if selected is not None:
        state.cursor = (selected + 1) % count
        state.tasks[selected].due = state.cycle + 1
    return selected, visited, skipped


class SourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scheduler = (AI / "scheduler.nut").read_text(encoding="utf-8")
        cls.dispatchers = (AI / "scheduler_tasks.nut").read_text(encoding="utf-8")
        cls.reason = function_body(cls.scheduler, "OpexExpSchedulerSkipReason")
        cls.selector = function_body(cls.scheduler, "OpexExpSchedulerSelectTask")
        cls.run_source = function_body(cls.scheduler, "OpexAI::_runNextTask")

    def test_exact_read_only_whitelist_matches_dispatch_keys(self):
        self.assertEqual(compact(self.reason), compact('''
          if (owner._projects == null) return null;
          if (candidate.name == "report" && owner._lastReportYear == year) return "report_same_year";
          if (candidate.name == "repay") {
            local date = AIDate.GetCurrentDate();
            local ym = year * 12 + AIDate.GetMonth(date);
            if (owner._lastRepayMonth == ym) return "repay_same_month";
          }
          return null;
        '''))

    def test_real_report_guard_precedes_all_business_side_effects(self):
        body = compact(function_body(self.dispatchers, "OpexAI::_dispatchReport"))
        self.assertTrue(body.startswith(compact('''
          if (this._lastReportYear == year) {
            if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
            return false;
          }
          this._lastReportYear = year;
        ''')))

    def test_real_repay_guard_precedes_stamp_and_loan_attempt(self):
        body = compact(function_body(self.dispatchers, "OpexAI::_dispatchRepay"))
        self.assertTrue(body.startswith(compact('''
          local date = AIDate.GetCurrentDate();
          local ym = year * 12 + AIDate.GetMonth(date);
          if (this._lastRepayMonth == ym) {
            if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
            return false;
          }
          this._lastRepayMonth = ym;
          this._tryRepayLoan(year);
        ''')))

    def test_catalog_is_excluded_even_if_observatory_predicts_fresh(self):
        self.assertNotIn('"catalog"', self.reason)
        self.assertNotIn('"catalog_fresh"', self.reason)
        body = function_body(self.dispatchers, "OpexAI::_dispatchCatalog")
        fresh = body.index("this._lastCatalogMonth == ym")
        for effect in ("C121_CATALOG_FIRST_YEAR_ACTIVE =",
                       "OpexC121CatalogTownProductionBatch(this._catalog)",
                       "OpexC78ContinueCatalogAirRebuild(this, task, year)",
                       "PORTFOLIO_REFRESH_PROBE_CHECKS++"):
            self.assertLess(body.index(effect), fresh)

    def test_flag_selects_new_path_and_legacy_scan_is_unchanged(self):
        start = self.run_source.index("if (EXP_SCHEDULER_SKIP_NOT_DUE)")
        end = self.run_source.index("if (task == null) return false;", start)
        self.assertEqual(compact(self.run_source[start:end]), compact('''
          if (EXP_SCHEDULER_SKIP_NOT_DUE) {
            taskIndex = OpexExpSchedulerSelectTask(this, year);
            if (taskIndex >= 0) task = this._taskQueue[taskIndex];
          } else {
            for (local index = this._taskCursor; index < this._taskQueue.len(); index++) {
              local candidate = this._taskQueue[index];
              if (candidate.enabled && candidate.dueCycle <= this._taskCycle) {
                task = candidate;
                taskIndex = index;
                break;
              }
            }
            if (task == null) {
              this._taskCycle++;
              this._taskCursor = 0;
              for (local index = 0; index < this._taskQueue.len(); index++) {
                local candidate = this._taskQueue[index];
                if (candidate.enabled && candidate.dueCycle <= this._taskCycle) {
                  task = candidate;
                  taskIndex = index;
                  break;
                }
              }
            }
          }
        '''))

    def test_bounded_scan_and_common_deadline_contract(self):
        body = compact(self.selector)
        self.assertIn("for (local visited = 0; visited < count; visited++)", body)
        self.assertEqual(len(re.findall(r"\bfor\s*\(", body)), 1)
        self.assertNotRegex(body, r"\bwhile\s*\(")
        self.assertIn("candidate.enabled && candidate.dueCycle <= owner._taskCycle", body)
        self.assertIn("candidate.dueCycle = owner._taskCycle + 1;", body)
        self.assertIn("if (reason == null) { selected = index; break; }", body)
        self.assertIn("owner._taskCursor = index;", body)
        self.assertIn("return selected;", body)
        run = compact(self.run_source)
        self.assertIn("this._taskCursor = (taskIndex + 1) % this._taskQueue.len();", run)
        self.assertIn("task.dueCycle = this._taskCycle + 1;", run)

    def test_helpers_do_not_dispatch_recurse_scan_world_or_change_policy(self):
        body = self.selector + self.reason
        for forbidden in ("_runNextTask(", "_dispatch", "_advanceRail", "_continueRail",
                          "_activeWorker", "_railSearch", "AIVehicleList", "AITownList",
                          "OpexAvailableCapital", "_tryRepayLoan", "_reportYear",
                          "PORTFOLIO_MAX_BATCH", "FLEET_BEFORE_NEW", "C115", "Sleep("):
            self.assertNotIn(forbidden, body)
        self.assertNotRegex(body, r"(?:_lastReportYear|_lastRepayMonth|\.enabled)\s*=(?!=)")
        self.assertLess(self.run_source.index("this._advanceRailSearchSliceWithLedgers();"),
                self.run_source.index("OpexExpSchedulerSelectTask(this, year)"))
        self.assertEqual(self.run_source.count("OpexExpSchedulerSelectTask(this, year)"), 1)

    def test_skip_keeps_trace_pair_and_monthly_observation(self):
        body = compact(self.selector)
        self.assertIn(compact('''
                    owner._taskCursor = (index + 1) % count;
          candidate.dueCycle = owner._taskCycle + 1;
          if (C56_TASK_TRACE) OpexC56TaskLog("TASK_ENTER", candidate.name, owner._taskCycle);
          if (C50_CHRONOLOGY_PROBE) owner._checkC50MonthlyTreasury(year);
          if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", candidate.name, owner._taskCycle);
        '''), body)

    def test_skip_measurement_is_gated_aggregated_and_outside_loop(self):
        body = compact(self.selector)
        self.assertIn("if ((V95_SCHED_IDLE_LEDGER || DECISION_LOG) && reportSkips + repaySkips > 0)", body)
        self.assertLess(body.index("owner._taskCursor = index;"), body.index("local fields ="))
        self.assertIn('if (V95_SCHED_IDLE_LEDGER) OpexSchedIdleLog("P7_SCHED_SKIP", fields);', body)
        self.assertIn('else OpexDecide("P7_SCHED_SKIP", fields);', body)
        for field in ("report_same_year=", "repay_same_month=", "scanned=", "limit=",
                      "cursor_from=", "cycle_from=", "cycle=", "next="):
            self.assertIn(field, body)


class AlgorithmContracts(unittest.TestCase):
    def test_same_scan_skips_two_noops_then_selects_projects_once(self):
        state = State([Task("report"), Task("repay"), Task("projects")],
                      last_report=1970, last_repay=1970 * 12 + 1)
        selected, visited, skipped = select(state)
        self.assertEqual((selected, visited), (2, [0, 1, 2]))
        self.assertEqual(skipped, [(0, "report_same_year"), (1, "repay_same_month")])
        self.assertEqual([task.due for task in state.tasks], [1, 1, 1])
        self.assertEqual((state.last_report, state.last_repay), (1970, 1970 * 12 + 1))

    def test_wrap_scans_suffix_then_prefix_at_next_cycle(self):
        state = State([Task("projects", 5), Task("disabled", enabled=False),
                       Task("report", 4), Task("repay", 4)], cursor=2, cycle=4,
                      last_report=1970, last_repay=1970 * 12 + 1)
        selected, visited, skipped = select(state)
        self.assertEqual((selected, visited, state.cycle, state.cursor), (0, [2, 3, 0], 5, 1))
        self.assertEqual(len(skipped), 2)
        self.assertEqual([task.due for task in state.tasks], [6, 0, 5, 5])

    def test_future_and_disabled_tasks_are_never_consumed_or_filtered(self):
        state = State([Task("report", 7), Task("repay", 0, False), Task("projects")],
                      last_report=1970, last_repay=1970 * 12 + 1)
        selected, _, skipped = select(state)
        self.assertEqual(selected, 2)
        self.assertEqual(skipped, [])
        self.assertEqual([task.due for task in state.tasks], [7, 0, 1])
        self.assertFalse(state.tasks[1].enabled)

    def test_bootstrap_and_unrecognised_tasks_are_not_new_filters(self):
        names = ("report", "repay", "catalog", "projects", "town_growth", "air",
                 "expand", "c41_water", "unknown")
        for name in names:
            for present in (False, True):
                with self.subTest(name=name, projects_present=present):
                    state = State([Task(name)], projects_present=present)
                    self.assertEqual(select(state), (0, [0], []))
        state = State([Task("report"), Task("repay")], projects_present=False,
                      last_report=1970, last_repay=1970 * 12 + 1)
        self.assertEqual(select(state), (0, [0], []))

    def test_empty_disabled_and_all_skippable_queues_terminate(self):
        state = State([])
        self.assertEqual(select(state), (None, [], []))
        for tasks in ([Task("x", enabled=False), Task("y", enabled=False)],
                      [Task("report"), Task("repay")]):
            state = State(tasks, last_report=1970, last_repay=1970 * 12 + 1)
            selected, visited, _ = select(state)
            self.assertIsNone(selected)
            self.assertEqual(visited, [0, 1])
            self.assertEqual((state.cursor, state.cycle), (0, 1))

    def test_one_slot_noop_never_repeats_in_same_scan(self):
        state = State([Task("report")], last_report=1970)
        for cycle in range(5):
            selected, visited, skipped = select(state)
            self.assertEqual((selected, visited), (None, [0]))
            self.assertEqual(skipped, [(0, "report_same_year")])
            self.assertEqual(state.cycle, cycle + 1)

    def test_future_suffix_is_not_revisited_after_wrap(self):
        state = State([Task("disabled", enabled=False), Task("projects", 1)], cursor=1)
        self.assertEqual(select(state), (None, [1, 0], []))
        self.assertEqual((state.cursor, state.cycle), (1, 1))
        self.assertEqual(select(state), (1, [1], []))

    def test_report_year_and_repay_month_transitions_release_tasks(self):
        report = State([Task("report")], last_report=1970)
        self.assertIsNone(select(report, 1970, 12)[0])
        self.assertEqual(select(report, 1971, 1)[0], 0)
        repay = State([Task("repay")], last_repay=1970 * 12 + 12)
        self.assertIsNone(select(repay, 1970, 12)[0])
        self.assertEqual(select(repay, 1971, 1)[0], 0)
        # Full year+month key, not merely equality of month number.
        repay = State([Task("repay")], last_repay=1970 * 12 + 1)
        self.assertEqual(select(repay, 1971, 1)[0], 0)

    def test_attempt_without_debt_change_still_consumes_month(self):
        state = State([Task("repay")])
        self.assertEqual(select(state)[0], 0)
        # Dispatcher stamps the month even when _tryRepayLoan changes nothing.
        state.last_repay = 1970 * 12 + 1
        self.assertIsNone(select(state)[0])
        self.assertIsNone(select(state)[0])
        self.assertEqual(select(state, month=2)[0], 0)

    def test_no_starvation_or_hot_projects_across_many_cycles(self):
        state = State([Task(name) for name in
                       ("catalog", "report", "scrap", "projects", "refleet", "repay")],
                      last_report=1970, last_repay=1970 * 12 + 1)
        history = []
        project_cycles = []
        for _ in range(80):
            selected, visited, _ = select(state)
            self.assertLessEqual(len(visited), len(state.tasks))
            self.assertEqual(len(set(visited)), len(visited))
            if selected is not None:
                name = state.tasks[selected].name
                history.append(name)
                if name == "projects":
                    project_cycles.append(state.cycle)
        self.assertEqual(history, ["catalog", "scrap", "projects", "refleet"] * 20)
        self.assertEqual(project_cycles, list(range(20)))

    def test_exhaustive_small_queues_bound_deadlines_and_first_eligible(self):
        # Independent circular-order oracle, including disabled and future entries.
        for names in product(("report", "repay", "projects"), repeat=3):
            for due in product((0, 1, 3), repeat=3):
                for cursor in range(3):
                    state = State([Task(name, deadline, i != 1) for i, (name, deadline)
                                   in enumerate(zip(names, due))], cursor=cursor,
                                  last_report=1970, last_repay=1970 * 12 + 1)
                    before = deepcopy(state)
                    selected, visited, skipped = select(state)
                    order = [(cursor + offset) % 3 for offset in range(3)]
                    expected = next((i for offset, i in enumerate(order)
                                     if before.tasks[i].enabled
                                     and before.tasks[i].due <= (cursor + offset) // 3
                                     and before.tasks[i].name == "projects"), None)
                    self.assertEqual(selected, expected)
                    self.assertEqual(visited, order[:len(visited)])
                    self.assertEqual(len(visited), len(set(visited)))
                    self.assertLessEqual(state.cycle - before.cycle, 1)
                    consumed = {i for i, _ in skipped}
                    if selected is not None:
                        consumed.add(selected)
                    for i, task in enumerate(state.tasks):
                        self.assertEqual(task.enabled, before.tasks[i].enabled)
                        self.assertGreaterEqual(task.due, before.tasks[i].due)
                        if i not in consumed:
                            self.assertEqual(task.due, before.tasks[i].due)

    def test_all_enabled_business_tasks_eventually_run_despite_future_due(self):
        for cursor in range(5):
            for due in product((0, 2, 5), repeat=3):
                state = State([Task("report"), Task("projects", due[0]),
                               Task("catalog", due[1]), Task("repay"),
                               Task("scrap", due[2])], cursor=cursor,
                              last_report=1970, last_repay=1970 * 12 + 1)
                seen = set()
                for _ in range(5 * (max(due) + 2)):
                    selected, visited, _ = select(state)
                    self.assertLessEqual(len(visited), 5)
                    if selected is not None:
                        seen.add(state.tasks[selected].name)
                self.assertEqual(seen, {"projects", "catalog", "scrap"})

    def test_reload_needs_only_existing_cursor_cycle_deadlines_and_stamps(self):
        state = State([Task("report"), Task("projects"), Task("repay")],
                      last_report=1970, last_repay=1970 * 12 + 1)
        select(state)
        restored = deepcopy(state)
        for _ in range(12):
            self.assertEqual(select(state), select(restored))
            self.assertEqual(state, restored)


if __name__ == "__main__":
    unittest.main()