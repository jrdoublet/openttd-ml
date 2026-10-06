"""P4: source contracts and small specification models, NOT Squirrel/NoAI tests.

No games, subprocesses or environment dependencies. Runtime wiring contracts are
deliberately mandatory: the integrator owns main/globals/settings/info. They must
be connected before running this suite or a smoke. Models cannot establish opcode
cost, scheduler latency, airport ownership semantics or economic profitability.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / "ai" / "OpexAI" / name).read_text(encoding="utf-8")


def body(source, signature):
    """Extract a function while ignoring braces inside comments and strings."""
    start = source.index(signature)
    brace = source.index("{", start)
    tokens = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|[{}]', re.S)
    depth = 0
    for token in tokens.finditer(source, brace):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return source[start:token.end()]
    raise AssertionError(f"unterminated function: {signature}")


class DailyWatchContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read("task_projects.nut")
        cls.air = read("air_towns.nut")
        cls.poll = body(cls.source, "function OpexAI::_expC83PollAirSlots(")
        cls.legacy = body(cls.source, "function OpexAI::_c83WatchAirSlotTransitions(")

    def test_disabled_returns_before_any_state_or_date_access(self):
        gate = self.poll.index("if (!EXP_C83_WATCH_DAILY) return 0;")
        self.assertLess(gate, self.poll.index("this._catalog"))
        self.assertLess(gate, self.poll.index("this._expC83WatchDaily"))
        self.assertLess(gate, self.poll.index("AIDate.GetCurrentDate()"))

    def test_missing_catalog_and_invalid_signal_do_not_consume_day(self):
        for guard in ("this._catalog == null", "this._catalog.towns == null",
                      "this._catalog.towns.len() == 0", "!OpexAirC83SlotSignalEnabled()"):
            self.assertLess(self.poll.index(guard), self.poll.index("poll.lastDate = today;"))
        self.assertNotIn("this._projects == null", self.poll)

    def test_one_poll_per_day_also_stamps_completion_after_suspension(self):
        skip = self.poll.index("if (poll != null && poll.lastDate == today) return 0;")
        call = self.poll.index("this._c83WatchAirSlotTransitions();")
        self.assertLess(skip, self.poll.index("OpexAirC83SlotSignalEnabled()"))
        self.assertLess(skip, self.poll.index("OpexOpsMeasureBegin()"))
        self.assertLess(self.poll.index("poll.lastDate = today;"), call)
        self.assertLess(call, self.poll.index("poll.lastDate = AIDate.GetCurrentDate();"))
        self.assertEqual(self.poll.count("this._c83WatchAirSlotTransitions();"), 1)
        self.assertNotIn("while (", self.poll)

    def test_projects_fallback_keeps_promotion_and_does_not_replay_receipts(self):
        attempt = body(self.source, "function OpexAI::_tryBuildProjects(")
        begin = attempt.index("local c83TargetedRegens = 0;")
        end = attempt.index("OpexPromoteLiveDefensiveAir(this._projects, OpexAvailableCapital());")
        block = attempt[begin:end]
        self.assertIn("if (EXP_C83_WATCH_DAILY)", block)
        self.assertIn('this._expC83PollAirSlots("projects");', block)
        self.assertIn("} else {\n      c83TargetedRegens = this._c83WatchAirSlotTransitions();", block)
        self.assertIn("if (c83TargetedRegens > 0) return true;", block)
        self.assertNotIn("poll.enqueued", block)
        for forbidden in ("dueCycle", "_enqueueReactive", "while ("):
            self.assertNotIn(forbidden, block)

    def test_same_six_towns_and_population_policy_not_contestable_by_default(self):
        watch = body(self.air, "function OpexAirC83WatchTowns(")
        self.assertIn("AIR_C83_TARGET_TOWNS <- 6;", read("globals_pre.nut"))
        self.assertIn("} else if (pop < AIR_EARLY_SLOT_MIN_POP) continue;", watch)
        self.assertIn("if (C83_FIXES)", watch)
        self.assertIn("best[pos - 1].pop < pop", watch)  # stable population ties
        self.assertIn("if (best.len() > AIR_C83_TARGET_TOWNS) best.pop();", watch)
        self.assertIn("OpexAirC83WatchTowns(this._catalog.towns)", self.legacy)
        self.assertNotIn("EXP_C83_WATCH_DAILY", watch)
        self.assertNotIn("C83_FIXES =", self.poll)

    def test_observation_and_treatment_reuse_known_objects_not_map_or_site_scans(self):
        blocks = [self.poll, self.legacy,
                  body(self.air, "function OpexAirC83WatchTowns("),
                  body(self.air, "function OpexAirOwnSlotTownCounts("),
                  body(self.source, "function OpexC83WatchAirSlots("),
                  body(self.source, "function OpexC83WatchOneTown("),
                  body(self.source, "function OpexAirC83FundedRaceCoversTown(")]
        for block in blocks:
            for forbidden in ("AITownList(", "AITileList(", "GetLastMonthProduction(",
                              "GetCargoProduction(", "OpexAirFindSite(", "OpexAirPlans(",
                              "OpexAirSiteStillBuildable(", "_tryBuildProjects(",
                              "_rebuildProjects(", "_runOrchestratorTick("):
                self.assertNotIn(forbidden, block)
        self.assertIn("PROJECT_TOP_K", self.legacy)
        self.assertIn("AIStationList(AIStation.STATION_AIRPORT)", self.legacy)
        self.assertIn("AITile.GetClosestTown(ownLoc)", self.legacy)

    def test_legacy_one_shot_and_optional_fixes_rearm_are_not_rewritten(self):
        self.assertIn("if (state != 1 || previous == 1) continue;", self.legacy)
        self.assertIn("OpexProjectTouchesEntity(project, \"town\", town.id)", self.legacy)
        self.assertIn("if (C83_FIXES) return OpexC83WatchAirSlots(this);", self.legacy)
        one = body(self.source, "function OpexC83WatchOneTown(")
        self.assertIn("OpexAirC83FundedRaceCoversTown(ai._projects, ai._lines, townId)", one)
        self.assertIn("ai._reactiveQueue.has(raceKey)", one)
        self.assertIn("today - lastEnqueue < rearmDays", one)
        self.assertLess(one.index("ai._c77EnqueueEntity("),
                        one.index("ai._c83SlotRace.rawset(townId, today);"))
        slots = body(self.source, "function OpexC83WatchAirSlots(")
        self.assertIn("local rearmDays = 365;", slots)
        self.assertIn("OpexC83WatchDroppedTown", slots)
        # No new C122 retry call, cash reservation, builder or score change.
        for forbidden in ("OpexC122ThreatRetryUnbuildable", "OpexCashReserve",
                          "fundScore", "OpexPromoteLiveDefensiveAir"):
            self.assertNotIn(forbidden, self.poll)

    def test_transition_observation_covers_legacy_fixes_and_dropped_towns(self):
        for signature in ("function OpexC83WatchDroppedTown(",
                          "function OpexC83WatchOneTown(",
                          "function OpexAI::_c83WatchAirSlotTransitions("):
            block = body(self.source, signature)
            self.assertIn("if (EXP_C83_WATCH_DAILY) OpexExpC83ObserveSlot(", block)
        observe = body(self.source, "function OpexExpC83ObserveSlot(")
        self.assertIn("old == null || old.state != state", observe)
        self.assertIn("if (!changed) return;", observe)
        self.assertIn('" seen_before=" + (old == null ? -1 : old.date)', observe)
        self.assertIn('" detected=" + today', observe)
        self.assertIn("poll.observed = poll.current;", self.poll)

    def test_logs_are_gated_aggregated_and_do_not_suppress_real_enqueues(self):
        log = body(self.source, "function OpexExpC83WatchLog(")
        self.assertIn("if (C78_SLOT_INTERCEPT_PROBE) OpexC78SlotLog(fields);", log)
        self.assertIn('else if (DECISION_LOG) OpexDecide("C83_WATCH", fields);', log)
        action = body(self.source, "function OpexExpC83WatchActionLog(")
        self.assertIn('sample.action == action && action != "targeted_regen"', action)
        self.assertNotIn("_c77EnqueueEntity", action)
        self.assertIn("if (poll.logMonth != month)", self.poll)
        for metric in ("polls=", "towns=", "changes=", "enqueued=", "watcher_ops=",
                       "max_gap_days=", "max_span_days="):
            self.assertIn(metric, self.poll)
        self.assertNotIn("this._budget.begin", self.poll)

    def test_reset_is_transient_and_does_not_clear_queue_or_business_state(self):
        reset = body(self.source, "function OpexExpC83ResetWatchDaily(")
        self.assertIn("ai._expC83WatchDaily = null;", reset)
        for forbidden in ("_c83SlotWatch", "_c83SlotRace", "_reactiveQueue", "_projects"):
            self.assertNotIn(forbidden, reset)
        persist = read("persist.nut")
        save = body(persist, "function OpexAI::Save(")
        self.assertNotIn("_expC83WatchDaily", save)


class DailyWatchIntegrationContracts(unittest.TestCase):
    """Owned by the integrator: missing wiring must fail, not silently skip."""

    def test_flag_is_declared_loaded_and_off_at_all_difficulties(self):
        self.assertIn("EXP_C83_WATCH_DAILY <- false;", read("globals_pre.nut"))
        self.assertRegex(read("settings.nut"),
                         r'EXP_C83_WATCH_DAILY\s*=\s*AIController.GetSetting\("exp_c83_watch_daily"\)\s*!=\s*0;')
        info = read("info.nut")
        self.assertEqual(info.count('name = "exp_c83_watch_daily"'), 1)
        setting = info.split('name = "exp_c83_watch_daily"', 1)[1].split("});", 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting, rf"{difficulty}_value\s*=\s*0")
        self.assertIn("AICONFIG_BOOLEAN", setting)

    def test_class_declaration_reset_after_load_and_main_hook_before_arbitration(self):
        main = read("main.nut")
        self.assertIn("_expC83WatchDaily = null;", main)
        self.assertIn('function _expC83PollAirSlots(source = "main");', main)
        start = body(main, "function OpexAI::Start(")
        reset = start.index("OpexExpC83ResetWatchDaily(this);")
        self.assertGreater(reset, start.index("OpexLoadSettings();"))
        self.assertGreater(reset, start.index("this._reconcileAfterLoad();"))
        events = start.index("this._processEvents();")
        poll = start.index("this._expC83PollAirSlots();", events)
        arbitration = start.index("this._runOrchestratorTick();", events)
        self.assertLess(reset, events)
        self.assertLess(events, poll)
        self.assertLess(poll, arbitration)


class PollModel:
    """Executable specification ONLY: no execution of the Squirrel source."""

    def __init__(self, enabled=True, fixes=False):
        self.enabled = enabled
        self.fixes = fixes
        self.last_day = None
        self.state = {}
        self.receipts = {}
        self.calls = 0
        self.closures = []

    def reset_clock(self):
        self.last_day = None

    def step(self, day, samples, source="main", ready=True, end_day=None,
             funded=(), queued=(), enqueue_ok=True):
        if not self.enabled and source != "projects":
            return 0
        if not ready or (self.enabled and day == self.last_day):
            return 0
        self.calls += 1
        enqueued = 0
        for town, (remaining, own_count) in samples.items():
            previous = self.state.get(town, 2)
            current = remaining + (10 if own_count else 0)
            if remaining == 0 and previous in (1, 11, 2):
                claimed = own_count >= 2 if previous == 11 else own_count > 0
                self.closures.append((town, "claimed" if claimed else "lost", previous))
            if self.fixes and current != 1:
                self.receipts.pop(town, None)
            if current != 1 or (not self.fixes and previous == 1):
                self.state[town] = current
                continue
            blocked = town in funded
            if self.fixes:
                blocked |= town in queued
                blocked |= town in self.receipts and day - self.receipts[town] < 365
            if not blocked and enqueue_ok:
                enqueued += 1
                if self.fixes:
                    self.receipts[town] = day
            # Legacy consumes the observation even on enqueue failure; fixes
            # does not write state on failure. Neither rule is repaired by P4.
            if not self.fixes or blocked or enqueue_ok:
                self.state[town] = current
        if self.enabled:
            self.last_day = day if end_day is None else end_day
        return enqueued


class DailyWatchModelTests(unittest.TestCase):
    def test_disabled_preserves_each_projects_call_but_main_is_inert(self):
        m = PollModel(enabled=False)
        self.assertEqual(m.step(10, {1: (1, 0)}), 0)
        self.assertEqual(m.calls, 0)
        self.assertEqual(m.step(10, {1: (1, 0)}, source="projects"), 1)
        self.assertEqual(m.step(10, {1: (1, 0)}, source="projects"), 0)
        self.assertEqual(m.calls, 2)

    def test_main_then_projects_does_not_replay_enqueue_or_poll(self):
        m = PollModel()
        self.assertEqual(m.step(10, {1: (1, 0)}), 1)
        self.assertEqual(m.step(10, {1: (0, 0)}, source="projects"), 0)
        self.assertEqual(m.calls, 1)
        m.step(11, {1: (0, 0)})
        self.assertEqual(m.closures, [(1, "lost", 1)])

    def test_projects_fallback_then_main_same_day_is_also_deduplicated(self):
        m = PollModel()
        self.assertEqual(m.step(4, {1: (1, 0)}, source="projects"), 1)
        self.assertEqual(m.step(4, {1: (1, 0)}), 0)
        self.assertEqual(m.calls, 1)

    def test_no_catalog_or_slot_signal_does_not_consume_day(self):
        m = PollModel()
        self.assertEqual(m.step(4, {}, ready=False), 0)
        self.assertIsNone(m.last_day)
        self.assertEqual(m.step(4, {1: (1, 0)}), 1)

    def test_suspension_and_missed_days_do_not_create_catchup_loop(self):
        m = PollModel()
        m.step(10, {1: (2, 0)}, end_day=12)
        m.step(12, {1: (1, 0)}, source="projects")
        self.assertEqual(m.calls, 1)
        self.assertEqual(m.step(30, {1: (1, 0)}), 1)
        self.assertEqual(m.calls, 2)

    def test_legacy_failure_is_not_retried_until_state_reopens(self):
        m = PollModel()
        self.assertEqual(m.step(10, {1: (1, 0)}, enqueue_ok=False), 0)
        self.assertEqual(m.step(11, {1: (1, 0)}), 0)
        m.step(12, {1: (2, 0)})
        self.assertEqual(m.step(13, {1: (1, 0)}), 1)

    def test_funded_skip_is_not_rearmed_in_legacy(self):
        m = PollModel()
        self.assertEqual(m.step(10, {1: (1, 0)}, funded={1}), 0)
        self.assertEqual(m.step(11, {1: (1, 0)}), 0)

    def test_own_airport_disappearance_reopens_state_eleven(self):
        m = PollModel()
        self.assertEqual(m.step(10, {1: (1, 1)}), 0)
        self.assertEqual(m.step(11, {1: (1, 0)}), 1)

    def test_claim_loss_and_jump_are_observed_once(self):
        for own_count, result in ((0, "lost"), (1, "claimed")):
            with self.subTest(own_count=own_count):
                m = PollModel()
                m.step(10, {1: (1, 0)})
                m.step(11, {1: (0, own_count)})
                m.step(12, {1: (0, own_count)})
                self.assertEqual(m.closures, [(1, result, 1)])
        m = PollModel()
        m.step(10, {1: (2, 0)})
        m.step(11, {1: (0, 0)})
        self.assertEqual(m.closures, [(1, "lost", 2)])

    def test_state_eleven_closure_counts_physical_own_airports(self):
        for count, result in ((1, "lost"), (2, "claimed")):
            m = PollModel()
            m.step(10, {1: (1, 1)})
            m.step(11, {1: (0, count)})
            self.assertEqual(m.closures, [(1, result, 11)])

    def test_fixes_keeps_coalescence_failed_enqueue_and_365_day_receipt(self):
        m = PollModel(fixes=True)
        self.assertEqual(m.step(10, {1: (1, 0)}, queued={1}), 0)
        self.assertNotIn(1, m.receipts)
        self.assertEqual(m.step(11, {1: (1, 0)}, enqueue_ok=False), 0)
        self.assertNotIn(1, m.receipts)
        self.assertEqual(m.step(12, {1: (1, 0)}), 1)
        self.assertEqual(m.step(376, {1: (1, 0)}), 0)
        self.assertEqual(m.step(377, {1: (1, 0)}), 1)

    def test_reset_clears_clock_not_existing_business_state(self):
        m = PollModel()
        m.step(10, {1: (1, 0)})
        m.reset_clock()
        self.assertEqual(m.step(10, {1: (1, 0)}), 0)
        self.assertEqual(m.calls, 2)
        # Actual Load rebuilds the original transient watcher too; a new
        # instance may legitimately rediscover the still-open first slot.
        loaded = PollModel()
        self.assertEqual(loaded.step(10, {1: (1, 0)}), 1)


if __name__ == "__main__":
    unittest.main()