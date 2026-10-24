"""C77 dispatch model and source contracts (no Squirrel/engine execution)."""
from collections import OrderedDict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / 'ai/OpexAI' / name).read_text(encoding='utf-8')


class DispatchModel:
    """One FIFO pop per orchestrator call; false dispatch yields to worker/fond.

    Execution abstracts the unchanged downstream eligibility checks: fixtures
    represent a valid subsidy or an eligible funded project touching the entity.
    Background readiness is injected after several scheduler/scan/publication passes.
    """
    def __init__(self, enabled, kind='c77_build'):
        self.enabled = enabled
        self.queue = OrderedDict()
        self.projects = False
        self.worker = None
        self.air_mode = True
        self.air_year = False
        self.subsidy_valid = True
        self.subsidy_awarded = False
        self.subsidy_expiry = 1000
        self.candidate_feasible = True
        self.injected = []
        self.executed = []
        self.expired = []
        self.worker_steps = self.background_steps = 0
        self.enqueue(kind, {'subsidyId': 7})

    def enqueue(self, kind, payload):
        payload = deepcopy(payload)
        old = self.queue.get(kind)
        if self.enabled and old is not None and 'c77DeferDate' in old:
            payload['c77DeferDate'] = old['c77DeferDate']
        self.queue[kind] = payload

    def dispatch(self, kind, payload, date):
        if self.enabled:
            blocked = not self.projects or self.worker is not None
            if self.enabled == 2 and payload.get('subsidyId', -1) >= 0:
                if (not self.subsidy_valid or self.subsidy_awarded
                        or date >= self.subsidy_expiry):
                    self.expired.append(kind)
                    return False
                if kind == 'c77_subsidy' and self.air_mode and self.air_year:
                    blocked = True
            if blocked:
                payload.setdefault('c77DeferDate', date)
            if 'c77DeferDate' in payload and date - payload['c77DeferDate'] >= 365:
                self.expired.append(kind)
                return False
            if blocked:
                self.enqueue(kind, payload)
                return False
        # Historical guard precedes both retry branches, even with projects null.
        if self.worker == 'regen_candidates':
            self.enqueue(kind, payload)
            return False
        if not self.projects:
            retries = payload.get('retries', 0)
            if retries < 3:
                payload['retries'] = retries + 1
                self.enqueue(kind, payload)
                return False
            return True
        if kind == 'c77_subsidy':
            # Existing injection rejects AIR year without retry with a live pool.
            if self.air_mode and self.air_year:
                return True
            self.injected.append(kind)
            if not self.candidate_feasible:
                return True
        self.executed.append(kind)
        return True

    def tick(self, date):
        if self.queue:
            kind, payload = self.queue.popitem(last=False)
            if self.dispatch(kind, payload, date):
                return
        if self.worker is not None:
            self.worker_steps += 1
            if self.worker not in ('rail_search', 'rail_stock'):
                return
        self.background_steps += 1


class DeferModelTests(unittest.TestCase):
    def test_offer_checks_only_mode_2_and_subsidy_builds(self):
        for mode in (0, 1, 2):
            for payload in ({}, {'subsidyId': -1}, {'subsidyId': 7}):
                m = DispatchModel(mode)
                m.projects = m.air_year = True
                m.subsidy_valid = False
                m.queue['c77_build'] = payload
                m.tick(100)
                dropped = mode == 2 and payload.get('subsidyId', -1) >= 0
                self.assertEqual(m.executed, [] if dropped else ['c77_build'])
                self.assertFalse(m.queue)

    def test_air_year_loss_0_1_and_replay_2(self):
        for mode in (0, 1, 2):
            m = DispatchModel(mode, 'c77_subsidy')
            m.projects = m.air_year = True
            m.tick(100)
            self.assertFalse(m.injected)
            self.assertEqual(bool(m.queue), mode == 2)
            if mode == 2:
                self.assertEqual(m.queue['c77_subsidy']['c77DeferDate'], 100)
                self.assertNotIn('retries', m.queue['c77_subsidy'])
                self.assertEqual(m.background_steps, 1)
            m.air_year = False
            m.tick(150)
            self.assertEqual(m.executed, ['c77_subsidy'] if mode == 2 else [])

    def test_no_air_mode_or_no_air_year_unchanged_and_no_forced_candidate(self):
        for mode in (0, 1, 2):
            for air_mode, air_year in ((False, True), (True, False)):
                for feasible in (False, True):
                    m = DispatchModel(mode, 'c77_subsidy')
                    m.projects = True
                    m.air_mode, m.air_year = air_mode, air_year
                    m.candidate_feasible = feasible
                    m.tick(100)
                    self.assertEqual(m.injected, ['c77_subsidy'])
                    self.assertEqual(bool(m.executed), feasible)
                    self.assertFalse(m.queue)

    def test_offer_deadline_and_award_precede_worker_and_readiness(self):
        for kind in ('c77_subsidy', 'c77_build'):
            for cause in ('invalid', 'awarded', 'deadline'):
                for ready in (False, True):
                    m = DispatchModel(2, kind)
                    m.subsidy_expiry = 120
                    m.tick(100)
                    m.tick(119)
                    self.assertTrue(m.queue)
                    m.projects = ready
                    m.worker = None if ready else 'rail_stock'
                    m.subsidy_valid = cause != 'invalid'
                    m.subsidy_awarded = cause == 'awarded'
                    m.tick(120 if cause == 'deadline' else 119)
                    self.assertFalse(m.queue)
                    self.assertFalse(m.executed)
                    self.assertEqual(m.expired, [kind])

    def test_air_worker_reload_coalescence_share_original_365_day_limit(self):
        m = DispatchModel(2, 'c77_subsidy')
        m.projects = m.air_year = True
        m.tick(0)
        m.air_year, m.worker = False, 'rail_search'
        m.enqueue('c77_subsidy', {'subsidyId': 7})
        m.queue = OrderedDict(json.loads(json.dumps(list(m.queue.items()))))
        m.tick(364)
        self.assertEqual(m.queue['c77_subsidy']['c77DeferDate'], 0)
        self.assertIs(type(m.queue['c77_subsidy']['c77DeferDate']), int)
        m.worker = None
        m.tick(365)
        self.assertFalse(m.executed)
        self.assertFalse(m.queue)

    def test_reload_loss_fourth_dispatch_and_survival_until_publication(self):
        for kind in ('c77_build', 'c77_subsidy'):
            for enabled in (False, True):
                with self.subTest(kind=kind, enabled=enabled):
                    m = DispatchModel(enabled, kind)
                    for tick in range(3):
                        m.tick(100)
                        self.assertTrue(m.queue)
                    m.tick(100)
                    self.assertEqual(bool(m.queue), enabled)
                    for day in range(101, 130):
                        m.tick(day)
                    self.assertGreaterEqual(m.background_steps, 30)
                    m.projects = True  # first partial publication / final apply
                    m.tick(130)
                    self.assertEqual(m.executed, [kind] if enabled else [])
                    self.assertFalse(m.queue)

    def test_each_worker_yields_then_executes(self):
        for kind in ('c77_build', 'c77_subsidy'):
            for worker in ('rail_search', 'rail_stock', 'regen_candidates'):
                for enabled in (False, True):
                    with self.subTest(kind=kind, worker=worker, enabled=enabled):
                        m = DispatchModel(enabled, kind)
                        m.projects, m.worker = True, worker
                        m.tick(10)
                        deferred = enabled or worker == 'regen_candidates'
                        self.assertEqual(m.worker_steps, int(deferred))
                        self.assertEqual(bool(m.executed), not deferred)
                        m.worker = None
                        m.tick(11)
                        self.assertEqual(m.executed, [kind])

    def test_calendar_boundary_reason_change_coalescence_and_save_load(self):
        for kind in ('c77_build', 'c77_subsidy'):
            m = DispatchModel(True, kind)
            m.tick(0)  # date zero is a valid date, not a missing value
            for _ in range(500):
                m.tick(0)
            self.assertNotIn('retries', m.queue[kind])
            m.projects, m.worker = True, 'rail_stock'
            m.enqueue(kind, {'subsidyId': 8})
            # Full save preserves the complete payload; reload keeps the first date.
            saved = json.loads(json.dumps(list(m.queue.items())))
            m.queue = OrderedDict(saved)
            self.assertIs(type(m.queue[kind]['c77DeferDate']), int)
            m.tick(364)
            self.assertTrue(m.queue)
            blocked = deepcopy(m)
            blocked.tick(365)
            self.assertEqual(blocked.expired, [kind])
            self.assertFalse(blocked.queue)
            self.assertEqual(blocked.worker_steps, m.worker_steps + 1)
            m.worker = None  # deadline also applies if readiness arrives too late
            m.tick(365)
            self.assertEqual(m.expired, [kind])
            self.assertEqual(m.executed, [])
            self.assertFalse(m.queue)

    def test_fifo_other_intention_gets_turn(self):
        m = DispatchModel(True)
        m.enqueue('c77_subsidy', {'subsidyId': 3})
        m.tick(1)
        self.assertEqual(list(m.queue), ['c77_subsidy', 'c77_build'])
        m.tick(1)
        self.assertEqual(m.background_steps, 2)


class DeferSourceContracts(unittest.TestCase):
    def test_po01c_stale_portfolio_blocks_mode_2_c77_build(self):
        code = source('orchestrator.nut')
        guard = code.split('  /* C77 defer ON :', 1)[1].split('  /* C77 : un travailleur', 1)[0]
        self.assertIn('intention.kind == "c77_build"', guard)
        # A live but stale portfolio and no C80 worker make the original blocked false.
        self.assertIn('local blocked = this._projects == null || this._activeWorker != null;', guard)
        mode2 = guard.split('    /* C77 defer 2 :', 1)[1].split('    /* Fin C77 defer 2. */', 1)[0]
        match = re.search(r'if \((C77_INTENT_DEFER_SUBSIDY && PO01C_REGEN_SPLIT[^\n]+)\)\s*blocked = true;', mode2)
        self.assertIsNotNone(match, 'PO01C pending/job must defer C77 on a non-null stale portfolio')
        condition = match.group(1)
        for mode2_enabled, split, job, pending, expected in (
            (True, True, True, False, True),   # PO01C generator is still running
            (True, True, False, True, True),   # PO01C publication has not started
            (True, True, False, False, False), # fully published, dispatch resumes
            (True, False, True, True, False),  # PO01C disabled
            (False, True, True, True, False),  # modes 0/1 unchanged
        ):
            with self.subTest(mode2=mode2_enabled, split=split, job=job, pending=pending):
                expr = (condition.replace('this._po01cJob != null', str(job))
                        .replace('this._po01cPending', str(pending))
                        .replace('C77_INTENT_DEFER_SUBSIDY', str(mode2_enabled))
                        .replace('PO01C_REGEN_SPLIT', str(split))
                        .replace('&&', ' and ').replace('||', ' or '))
                self.assertRegex(expr, r'^[() A-Za-z]+$')
                self.assertEqual(eval(expr, {'__builtins__': {}}, {}), expected)
        self.assertLess(guard.index('if (C77_INTENT_DEFER_SUBSIDY && PO01C_REGEN_SPLIT'),
                        guard.index('if (blocked &&'))

    def test_setting(self):
        setting = re.search(r'AddSetting\(\{ name = "c77_intent_defer".*?\}\);', source('info.nut'), re.S)[0]
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(level + '_value = 2', setting)
        self.assertIn('min_value = 0, max_value = 2', setting)
        self.assertIn('flags = 0', setting)
        self.assertIn('C77_INTENT_DEFER = c77IntentDefer != 0;', source('settings.nut'))
        self.assertIn('C77_INTENT_DEFER_SUBSIDY = c77IntentDefer == 2;', source('settings.nut'))
        self.assertIn('C77_INTENT_DEFER_SUBSIDY <- true;', source('globals_pre.nut'))
        self.assertEqual(source('settings.nut').count('GetSetting("c77_intent_defer")'), 1)
        self.assertIn('C77_INTENT_DEFER <- true;', source('globals_pre.nut'))
        self.assertIn('const C77_INTENT_DEFER_DAYS = 365;', source('globals_pre.nut'))

    def test_guard_and_single_pop_yield(self):
        code = source('orchestrator.nut')
        guard = code.split('  /* C77 defer ON :', 1)[1].split('  /* C77 : un travailleur', 1)[0]
        self.assertIn('if (C77_INTENT_DEFER && (intention.kind == "c77_build" || intention.kind == "c77_subsidy"))', guard)
        self.assertIn('this._projects == null || this._activeWorker != null', guard)
        self.assertIn('deferPayload.c77DeferDate <- deferDate;', guard)
        self.assertIn('local deferDate = AIDate.GetCurrentDate();', guard)
        self.assertIn('deferDate - deferPayload.c77DeferDate >= C77_INTENT_DEFER_DAYS', guard)
        self.assertIn('if (DECISION_LOG) OpexDecide("C77_INTENT_EXPIRE"', guard)
        self.assertIn('this._enqueueReactive(intention.key, intention.kind, deferPayload);\n      return false;', guard)
        self.assertNotIn('retries', guard.split('if (C77_INTENT_DEFER', 1)[1])
        tick = code.split('function OpexAI::_runOrchestratorTick()', 1)[1].split('\nfunction ', 1)[0]
        self.assertEqual(tick.count('this._popReactive()'), 1)
        self.assertNotRegex(tick, r'\b(?:while|for)\s*\(')
        self.assertLess(tick.index('OpexC56DispatchReactive'), tick.index('OpexC56WorkerStep'))
        self.assertIn('return this._runBackgroundQueue();', tick)

    def test_payload_full_and_short_save(self):
        code = source('persist.nut')
        save = code.split('function OpexSaveReactiveQueue', 1)[1].split('function OpexLoadReactiveQueue', 1)[0]
        load = code.split('function OpexLoadReactiveQueue', 1)[1].split('function OpexSaveActiveWorker', 1)[0]
        self.assertIn('payload = ("payload" in item) ? item.payload : null', save)
        self.assertIn('local payload = ("payload" in item) ? item.payload : null;', load)
        self.assertIn('q.restoreItem(item.key, item.kind, payload, enqueuedDate, count);', load)
        self.assertIn('saveObj.c80ReactiveQueue <- OpexSaveReactiveQueue(this._reactiveQueue);', code)
        self.assertIn('this._reactiveQueue = OpexLoadReactiveQueue(data.c80ReactiveQueue);', code)
        short = code.split('if (!SAVE_FULL_STATE) {', 1)[1].split('return shortSave;', 1)[0]
        self.assertNotIn('c80ReactiveQueue', short)
        self.assertNotIn('c77DeferDate', short)
        queue = source('orchestrator.nut')
        self.assertIn('payload.c77DeferDate <- existing.payload.c77DeferDate;', queue)

    def test_historical_dispatch_bytes_unchanged(self):
        # SHA256 of the pre-existing dispatch function at task base 190b4ba1.
        # Removing only the new guarded block must reproduce the exact old bytes.
        code = source('orchestrator.nut')
        dispatch = code.split('function OpexAI::_dispatchReactiveIntention', 1)[1].split('function OpexAI::_c77EnqueueEntity', 1)[0]
        start = dispatch.index('  /* C77 defer ON :')
        end = dispatch.index('  /* C77 : un travailleur', start)
        historical = dispatch[:start] + dispatch[end:]
        self.assertEqual(hashlib.sha256(historical.encode()).hexdigest(), 'b5382534a506696f44cd5316e86e27a51b27ee74537180a70edfde22c51d65e6')

    def test_modes_0_1_orchestrator_bytes_and_api_contract(self):
        code = source('orchestrator.nut')
        start = code.index('    /* C77 defer 2 :')
        end = code.index('    /* Fin C77 defer 2. */\n', start) + len('    /* Fin C77 defer 2. */\n')
        # Whole file after removing only the mode-2 block.
        self.assertEqual(hashlib.sha256((code[:start] + code[end:]).encode()).hexdigest(),
                         '08bfd51a7994af250ceb7ed63f3f46dfef82fd181fa94da6c985dcf3979e91ca')
        block = code[start:end]
        self.assertIn('if (C77_INTENT_DEFER_SUBSIDY && ("subsidyId" in deferPayload) && deferPayload.subsidyId >= 0)', block)
        self.assertIn('!AISubsidy.IsValidSubsidy(deferSubId) || AISubsidy.IsAwarded(deferSubId)', block)
        self.assertIn('deferDate >= AISubsidy.GetExpireDate(deferSubId)) return false;', block)
        self.assertIn('intention.kind == "c77_subsidy" && MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE', block)
        self.assertLess(end, code.index('if (blocked && !("c77DeferDate" in deferPayload))', start))
        self.assertNotRegex(block, r'\.find\(|function\s*\(|\bfloat\b|\blocal\s+(?:clone|base|parent|static|delegate|resume|yield)\b')


if __name__ == '__main__':
    unittest.main()
