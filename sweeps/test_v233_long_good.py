"""V233L source contracts and edge-case fixtures; no Squirrel VM/game invoked.

OFF projection pins original bytes; the small independent observation model
checks calendar/zero/missing-data cases, not execution timing or profitability.
"""
import hashlib
from pathlib import Path
import re
import unittest

from po01c_generate import generated
from test_v261_forum_behaviours import body, source, uncomment
from v233_long_good_legacy import FIXTURE, off_source

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


def observe(samples):
    """Six real observations in seven calendar months; no missing value imputed."""
    window = []
    last = None
    for month, production, transported in samples:
        if last is not None and month <= last:
            continue
        window.append((month, production, max(0, production - transported)))
        window = [sample for sample in window if sample[0] >= month - 6][-6:]
        last = month
    durable = (len(window) == 6 and sum(p > 0 for _, p, _ in window) >= 2
               and sum(p for m, p, _ in window if m >= last - 2) > 0)
    return window, durable, sum(r for _, _, r in window) // len(window) if window else 0


def fresh(month, now):
    return 1 <= now - month <= 3 and month >= 0


def reject_reasons(samples, now, *, input_live=True, export_exists=False, distance=200):
    """Independent gate expectations, including simultaneous source failures."""
    window, durable, monthly = observe(samples)
    reasons = set()
    if not durable:
        reasons.add("window")
    if not window or not fresh(window[-1][0], now):
        reasons.add("stale")
    if not input_live:
        reasons.add("input_not_live")
    if export_exists:
        reasons.add("export_exists")
    if monthly <= 0:
        reasons.add("no_residual")
    if not reasons and not 150 <= distance <= 300:
        reasons.add("distance")
    return reasons


class V233LongGoodContracts(unittest.TestCase):
    def test_setting_bounds_defaults_and_single_read(self):
        block = re.search(r'AddSetting\(\{\s*name = "v233_long_good",.*?\}\);', source("info.nut"), re.S)[0]
        self.assertIn("min_value = 0, max_value = 1", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, level + r"_value\s*=\s*0\b")
        self.assertEqual(source("settings.nut").count('GetSetting("v233_long_good")'), 1)
        self.assertIn("V233_LONG_GOOD <- 0;", source("globals_pre.nut"))
        self.assertEqual(source("info.nut").count("AddSetting("), 60)

    def test_off_reviewed_edits_preserve_all_original_hashes(self):
        for name, entry in FIXTURE["files"].items():
            with self.subTest(name=name):
                projected = off_source(name, source(name))
                self.assertEqual(hashlib.sha256(projected.encode()).hexdigest(), entry["sha256_off"])
                if name not in ("main.nut", "globals_pre.nut", "info.nut", "settings.nut", "persist.nut"):
                    self.assertNotIn("OpexV233L", uncomment(projected))
        edited = source("candidates.nut").replace("V233_LONG_GOOD > 0 ? OpexV233LSource", "true ? OpexV233LSource")
        with self.assertRaises(AssertionError):
            off_source("candidates.nut", edited)

    def test_off_switch_short_circuits_all_entry_paths(self):
        self.assertIn('return V233_LONG_GOOD > 0 && candidate != null', body("v233_long_good.nut", "OpexV233LIs"))
        self.assertIn('V233_LONG_GOOD > 0 ? OpexV233LSource', body("candidates.nut", "OpexFreightCandidates"))
        self.assertIn('if (V233_LONG_GOOD > 0) OpexV233LTick(this);', body("orchestrator.nut", "OpexAI::_runOrchestratorTick"))
        self.assertIn('if (V233_LONG_GOOD > 0 && OpexV233LSelectGrowth', body("task_rail.nut", "OpexAI::_expandRailLines"))
        self.assertIn('local longModel = V233_LONG_GOOD > 0 && longGood;', body("economy.nut", "OpexLineEconomics"))

    def test_source_checks_exact_factory_cargo_and_live_input(self):
        code = body("v233_long_good.nut", "OpexV233LInput")
        for token in ('line.cargo == cargo', 'IsProcessingIndustry', 'producing.HasItem(cargo)',
                      'accepting.HasItem(line.cargo)', 'OpexV233LTouches', 'AIVehicle.IsValidVehicle',
                      'OpexVehicleServesStation', 'AITile.GetOwner(line.stationB)'):
            self.assertIn(token, code)
        source_code = body("v233_long_good.nut", "OpexV233LSource")
        self.assertIn('AICargo.GetCargoLabel(cargo) != "GOOD"', source_code)
        self.assertIn('line.originA == source.tile', source_code)
        self.assertIn('OpexV233LInput(line, cargo) == source.id', source_code)
        self.assertIn('complete && !inputLive', source_code)
        self.assertNotIn('AIStation.GetOwner', source("v233_long_good.nut"))  # GameScript-only API.

    def test_alternating_deliveries_are_durable_zero_not_missing(self):
        samples = [[m, 120 if m % 2 else 0, 20 if m % 2 else 0] for m in range(6)]
        window, durable, monthly = observe(samples)
        self.assertEqual(len(window), 6)
        self.assertTrue(durable)
        self.assertEqual(monthly, 50)
        self.assertEqual(window[0], (0, 0, 0))
        code = body("v233_long_good.nut", "OpexV233LObserve")
        self.assertIn('row.month >= month - 1', code)
        self.assertIn('OpexV233LMonth() != month', code)
        self.assertIn('OpexV233LRecord(row, month - 1, production, residual)', code)
        record = body("v233_long_good.nut", "OpexV233LRecord")
        self.assertIn('month <= row.month', record)
        self.assertIn('row.months.append(month)', record)
        self.assertIn('row.production.append(production)', record)
        self.assertIn('row.residual.append(residual)', record)
        self.assertIn('row.months[0] < month - V233L_WINDOW', record)

    def test_missing_duplicate_and_stopped_production_windows(self):
        cases = (
            ([[m, 100, 20] for m in range(5)], False, 80),
            ([[m, 100, 20] for m in (0, 1, 2, 4, 5, 6)], True, 80),
            ([[m, 100, 20] for m in (0, 1, 3, 4, 6, 7)], False, 80),
            ([[m, 100, 20] for m in range(6)] + [[9, 100, 20]], False, 80),
            ([[0, 600, 0]] + [[m, 0, 0] for m in range(1, 6)], False, 100),
            ([[m, 100, 200] for m in range(6)], True, 0),
            ([[m, 100, 20] for m in range(6)] + [[5, 999, 0]], True, 80),
            ([[m, 100, 20] for m in range(6)] + [[3, 999, 0]], True, 80),
        )
        for samples, durable, monthly in cases:
            with self.subTest(samples=samples):
                _, actual_durable, actual_monthly = observe(samples)
                self.assertEqual((actual_durable, actual_monthly), (durable, monthly))
        self.assertIn('positive >= 2 && recent > 0', body("v233_long_good.nut", "OpexV233LDurable"))

    def test_missing_month_is_neither_zero_nor_sample(self):
        # At month 5, the absent month 3 cannot complete a six-sample window.
        samples = [[m, 100, 10] for m in (0, 1, 2, 4, 5)]
        window, durable, monthly = observe(samples)
        self.assertEqual([m for m, _, _ in window], [0, 1, 2, 4, 5])
        self.assertFalse(durable)
        self.assertEqual(monthly, 90)
        window, durable, monthly = observe(samples + [[6, 400, 40]])
        self.assertTrue(durable)
        self.assertEqual([m for m, _, _ in window], [0, 1, 2, 4, 5, 6])
        self.assertEqual(monthly, 135)  # 810 / 6 observations, never / 7.

    def test_recent_production_uses_calendar_months_with_gap(self):
        samples = [[m, 100 if m in (2, 3) else 0, 0] for m in (0, 1, 2, 3, 4, 6)]
        self.assertFalse(observe(samples)[1])  # last three calendar months 4..6 are idle.
        samples[-1][1] = 100
        self.assertTrue(observe(samples)[1])
        self.assertIn('row.months[i] >= row.month - 2', body("v233_long_good.nut", "OpexV233LDurable"))

    def test_sample_expiry_boundaries_and_all_consumers(self):
        for now, expected in ((4, False), (5, False), (6, True), (7, True), (8, True), (9, False)):
            with self.subTest(now=now):
                self.assertEqual(fresh(5, now), expected)
        self.assertFalse(fresh(-1, 1))
        helper = body("v233_long_good.nut", "OpexV233LFresh")
        self.assertIn('month >= 0 && month < now && now - month <= V233L_MAX_AGE', helper)
        self.assertIn('const V233L_MAX_AGE = 3;', source("v233_long_good.nut"))
        for name in ("Source", "Recheck", "InputTarget", "FleetMargin"):
            with self.subTest(consumer=name):
                self.assertIn('OpexV233LFresh(row.month,', body("v233_long_good.nut", "OpexV233L" + name))
        admit = body("v233_long_good.nut", "OpexV233LAdmit")
        self.assertIn('OpexV233LFresh(context.sampleMonth, OpexV233LMonth())', admit)
        self.assertIn('sampleMonth = row.month', body("v233_long_good.nut", "OpexV233LSource"))

    def test_distinct_reject_reasons_and_simultaneous_failures(self):
        samples = [[m, 100, 20] for m in (0, 1, 2, 4, 5, 6)]
        self.assertEqual(reject_reasons(samples, 9), set())  # age three, not only previous month.
        self.assertEqual(reject_reasons(samples, 10), {"stale"})
        self.assertEqual(reject_reasons(samples, 7, input_live=False), {"input_not_live"})
        self.assertEqual(reject_reasons(samples, 7, export_exists=True), {"export_exists"})
        self.assertEqual(reject_reasons([[m, 100, 100] for m in range(6)], 6), {"no_residual"})
        self.assertEqual(reject_reasons([[0, 0, 0]], 4, input_live=False, export_exists=True),
                         {"window", "stale", "input_not_live", "export_exists", "no_residual"})
        for distance in (149, 150, 300, 301):
            self.assertEqual(reject_reasons(samples, 7, distance=distance),
                             set() if 150 <= distance <= 300 else {"distance"})
        code = body("v233_long_good.nut", "OpexV233LSource")
        for reason in ("window", "stale", "input_not_live", "export_exists", "no_residual", "budget", "source_changed"):
            self.assertIn(f'reasons.append("{reason}")', code)
        self.assertIn('foreach (reason in reasons) OpexV233LLog("REJECT"', code)
        self.assertIn('if (complete && !inputLive)', code)
        self.assertLess(code.index('foreach (line in lines)'), code.index('reasons.append("input_not_live")'))
        self.assertIn('ready = reasons.len() == 0', code)
        self.assertNotIn('production_or_export', source("v233_long_good.nut"))

    def test_load_checks_observation_dates_and_migrates_consecutive_legacy_windows(self):
        code = body("v233_long_good.nut", "OpexV233LLoad")
        for token in ('row.months.len() != row.production.len()', 'month <= previous',
                      'month > row.month', 'month < row.month - V233L_WINDOW',
                      'previous != row.month', 'row.months <- []',
                      'row.month - row.production.len() + 1 + i'):
            self.assertIn(token, code)
        self.assertNotIn('AIDate.', code)  # Load must work before world APIs/settings.
        self.assertLess(code.index('pending.phase != "prepare" && pending.before == null'),
                        code.index('row.months <- []'))  # no partial migration of invalid saves.

    def test_candidate_keeps_destination_guard_and_normal_portfolio(self):
        code = body("candidates.nut", "OpexFreightCandidates")
        self.assertIn('(ss != null && longGood == null) || st != null', code)
        self.assertIn('longGood != null && !OpexV233LAdmit', code)
        self.assertIn('candidate.v233LongGood <- true', code)
        self.assertIn('out.append(candidate)', code)
        self.assertIn('distance < 150 || distance > 300', body("v233_long_good.nut", "OpexV233LAdmit"))
        self.assertIn('distance >= 150 && distance <= 300', body("v233_long_good.nut", "OpexV233LRecheck"))
        self.assertNotIn('v233', source("projects_selection.nut").lower())
        self.assertNotIn('v233', source("capital.nut").lower())

    def test_two_train_sizing_tariff_and_both_recalculations(self):
        econ = body("economy.nut", "OpexLineEconomics")
        self.assertIn('if (longModel) calibrationOffered /= 2.0;', econ)
        self.assertIn('longModel || (OpexV190Active()', econ)
        self.assertIn('AICargo.GetCargoIncome(cargo, distance, paidDays)', econ)
        self.assertIn('oneWayDays + dwellDays / 2 + perTrain * 15.0 / offered', econ)
        self.assertIn('OpexV163CandidateSecondary(candidate), OpexV233LIs(candidate)', source("builder_rail.nut"))
        complete = body("builder_rail.nut", "OpexCompleteRailRouteAfterSearch")
        self.assertIn('candidate.distance = tariffDistance', complete)
        self.assertIn('candidate.v233RouteDistance <- routeDistance', complete)
        execute = body("builder_rail.nut", "OpexV190ExecuteRailPlan")
        self.assertLess(execute.index('!OpexV233LRecheck'), execute.index('OpexQuoteRailCapital'))
        self.assertLess(execute.index('OpexV233LIs(candidate) && !okD'), execute.index('local started = []'))
        self.assertIn('result.reason = "DOUBLEFAIL"', execute)

    def test_whole_platform_acceptance_and_optional_share_use_good_rating(self):
        code = body("v233_long_good.nut", "OpexV233LCargoValue")
        self.assertIn('horizontal ? length : 1, horizontal ? 1 : length', code)
        plans = body("v233_long_good.nut", "OpexV233LPlatformPlans")
        self.assertIn('OpexV233LTouches(p, industry, true', plans)
        self.assertIn('AIStation.GetCargoRating(station, candidate.cargo)', plans)
        self.assertIn('goodRating >= candidate.stationRating', plans)
        self.assertIn('p.stationId <- station', plans)
        self.assertIn('AIRail.BuildRailStation', plans)
        self.assertIn('end == "A" && line.originB == candidate.src', body("v233_long_good.nut", "OpexV233LSourceNeighbour"))

    def test_growth_needs_persistent_stock_physics_margin_and_real_loop(self):
        backlog = body("v233_long_good.nut", "OpexV233LBacklog")
        for text in ('row.waiting.len() == 3', 'OpexV233LMin(row.waiting) >= required', 'row.month >= row.nextMonth'):
            self.assertIn(text, backlog)
        selection = body("v233_long_good.nut", "OpexV233LSelectGrowth")
        for text in ('line.vehicles.len() >= 14', 'line.v181Loop', 'line.doubleTrack != 1',
                     'OpexV233LFleetMargin', 'OpexV284Select(owner, year, true)', 'OpexV233LInputTarget(line)'):
            self.assertIn(text, selection)
        margin = body("v233_long_good.nut", "OpexV233LFleetMargin")
        self.assertIn('OpexRailEffectiveSpeed', margin)
        self.assertIn('delta <= 0', margin)
        self.assertIn('AICargo.GetCargoIncome', margin)
        self.assertIn('OpexAvailableCapital()', margin)
        self.assertNotRegex(margin, r'waiting\s*\*\s*12')
        v284 = body("task_v284.nut", "OpexV284Select")
        self.assertIn('!v233Input && (year < OPEX_START_YEAR', v284)
        self.assertIn('v233Input && !OpexV233LInputMargin', v284)

    def test_save_load_option_guards_scalar_state_and_idempotent_adoption(self):
        save = body("persist.nut", "OpexAI::Save")
        self.assertIn('if (V233_LONG_GOOD > 0) saveObj.v233LongGood <- V233L_STATE;', save)
        self.assertIn('key == "v233LongGood" && V233_LONG_GOOD <= 0', body("persist.nut", "OpexSaveProjectLine"))
        load = body("persist.nut", "OpexAI::Load")
        self.assertIn('this._v233LReload = data.v233LongGood', load)
        start = body("main.nut", "OpexAI::Start")
        self.assertIn('V233_LONG_GOOD > 0 ? OpexV233LLoad(this._v233LReload) : null', start)
        self.assertLess(start.index('OpexLoadSettings()'), start.index('OpexV233LLoad'))
        decode = body("v233_long_good.nut", "OpexV233LLoad")
        for text in ('row[key] != "integer"', 'pending[key] != "integer"', 'row[key].len() > V233L_WINDOW',
                     'row.waiting.len() > 3', 'pending.before == null'):
            self.assertIn(text, decode)
        transaction = body("v233_long_good.nut", "OpexV233LGrowthStep")
        self.assertLess(transaction.index('pending.phase = "building"'), transaction.index('AIVehicle.CloneVehicle'))
        self.assertLess(transaction.index('pending.phase = "starting"'), transaction.index('AIVehicle.StartStopVehicle'))
        self.assertIn('!OpexWaterContains(line.vehicles, pending.newVehicle)', transaction)
        self.assertIn('OpexFindLineForVehicle(owner._lines, v) == null', transaction)
        self.assertIn('pending.phase == "building"', body("v233_long_good.nut", "OpexV233LReconcile"))

    def test_bounds_measurements_log_guards_no_new_valuate_or_sleep(self):
        code = source("v233_long_good.nut")
        for text in ('const V233L_SLICE_OPS = 20000;', 'count < 8', 'state.rows.len() >= V233L_MAX_FACTORIES',
                     'growth.len() >= 128', 'OpexOpsMeasureEnd(mark)', '"OPS"', 'if (DECISION_LOG) OpexDecide'):
            self.assertIn(text, code)
        self.assertIn('k >= V233L_TOWNS', source("candidates.nut"))
        self.assertNotIn('longGood.mark', source("candidates.nut") + source("po01c_generators.nut"))
        self.assertIn('longGood.ops += OpexOpsMeasureEnd(v233Mark)', source("candidates.nut"))
        self.assertIn('workMark != null && OpexOpsMeasureEnd(workMark)', source("builder_rail.nut"))
        for token in ('.Valuate(', '.find(', 'Sleep(', 'function('):
            self.assertNotIn(token, uncomment(code))
        self.assertEqual(source("po01c_generators.nut"), generated())  # read-only, never regenerate.

    def test_new_module_balanced_and_no_reserved_identifiers(self):
        code = uncomment(source("v233_long_good.nut"))
        self.assertNotRegex(code, r'\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield)\b')
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        for token in re.findall(r'"(?:\\.|[^"\\])*"|[()\[\]{}]', code):
            if token.startswith('"'):
                continue
            if token in '([{':
                stack.append(token)
            else:
                self.assertTrue(stack)
                self.assertEqual(stack.pop(), pairs[token])
        self.assertEqual(stack, [])

    def test_rollback_keeps_existing_depot_traffic_and_tracks_new_identity(self):
        code = body("v233_long_good.nut", "OpexV233LGrowthStep")
        self.assertIn('OpexV257Discard(owner, pending.newVehicle)', code)
        self.assertIn('if (pending.before != null)', code)
        self.assertIn('!OpexWaterContains(pending.before, v)', code)
        self.assertIn('OpexFindLineForVehicle(owner._lines, v) == null', code)
        self.assertIn('vehicles.Count() > 2048', code)

    def test_input_growth_requires_our_live_output(self):
        code = body("v233_long_good.nut", "OpexV233LInputTarget")
        self.assertIn('row.exportLine < 0', code)
        self.assertIn('row.exportMonth < OpexV233LMonth() - 1', code)
        observe_code = body("v233_long_good.nut", "OpexV233LObserveBacklog")
        self.assertIn('AIVehicle.IsValidVehicle(line.vehicles[0])', observe_code)
        self.assertIn('V233L_STATE.rows[industry].exportMonth = month', observe_code)

    def test_opcode_meters_only_span_synchronous_work(self):
        code = body("v233_long_good.nut", "OpexV233LSourceEnd")
        self.assertIn('" ops=" + context.ops', code)
        self.assertNotIn('OpexOpsMeasureEnd(context.', code)
        candidate = body("candidates.nut", "OpexFreightCandidates")
        self.assertIn('longGood.ops >= V233L_SLICE_OPS', candidate)
        execute = body("v233_long_good.nut", "OpexV233LContinueGrowth")
        self.assertIn('OpexV233LGrowthStep(owner)', execute)
        self.assertIn('phase=growth_execute ops=', execute)
