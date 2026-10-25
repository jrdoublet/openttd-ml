"""PCAL-02 contracts and source-derived projections, without engine or VM.

OFF SHA pins include every edited production source and generated copy. The
projections exercise real predicates/advancement expressions, not NoAI opcode
costs, command semantics, compilation or economic equivalence.
"""
import copy
import hashlib
from pathlib import Path
import random
import re
from types import SimpleNamespace as NS
import unittest

from campaign_freeze import parse_ai_setting_specs
from po01c_generate import function, generated
from test_v261_forum_behaviours import uncomment

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / 'ai/OpexAI'


def read(name):
    return (AI / name).read_text(encoding='utf-8')


def body(name):
    return function(read('pcal02_air_sites.nut'), 'OpexPCAL02' + name)


FIND_GUARD = '''  if (PCAL02_AIR_SITES && requiredSlotTownId < 0) {
    local prepared = OpexPCAL02FindSite(town, airport, probes);
    if (prepared != null) return prepared;
  }
'''
BUILD_GUARD = '''  if (PCAL02_AIR_SITES && ((!reuseA && !OpexPCAL02BuildSiteOk(plan.siteA, airport, planeChoice, catalog))
      || (!reuseB && !OpexPCAL02BuildSiteOk(plan.siteB, airport, planeChoice, catalog)))) {
    result.reason = "PCALSTALE";
    return result;
  }
'''
OFF_REMOVALS = {
    'air_sites.nut': [FIND_GUARD],
    'po01c_generators.nut': [FIND_GUARD.replace(
        'return prepared;', '{ po01dResult.value = prepared; return; }')],
    'air_construction.nut': [BUILD_GUARD] + [
        f'    if (PCAL02_AIR_SITES && airport{s} != null) OpexPCAL02Built(plan.site{s}, airport);\n'
        for s in 'AB'],
    'air_coverage.nut': [
        '  if (PCAL02_AIR_SITES) OpexPCAL02Reset();\n',
        '  if (PCAL02_AIR_SITES) PCAL02_STATE.epoch++;\n'],
    'builder_air.nut': ['require("pcal02_air_sites.nut");\n'],
    'globals_pre.nut': ['PCAL02_AIR_SITES <- false;\n'],
    'settings.nut': ['  PCAL02_AIR_SITES = AIController.GetSetting("pcal02_air_sites") == 1;\n'],
    'info.nut': ['''    AddSetting({ name = "pcal02_air_sites",
      description = "PCAL-02: prepare two flat AIR sites per candidate town/type in unused tick opcodes (prototype, default off)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
'''],
    'main.nut': ['    if (PCAL02_AIR_SITES) OpexPCAL02Tick(this);\n'],
    'probes.nut': ['    if (PCAL02_AIR_SITES) OpexPCAL02Tick(this);\n'],
}
# Initial 269ec7bc tree: only the exact guarded insertions above may disappear.
OFF_SHA = {
    'air_construction.nut': 'b22b7ee81ff807165bda421f07be0bd9dcd3d2918f37b1d1c8c18839468e9c74',
    'air_coverage.nut': 'bc706713c0041f1c0009c18a38074b4a07700dfb11e9e30260753e40252a227e',
    'air_sites.nut': '1ef05fc3b922e34d5ed800a52d9b5816e2d958492e434075bd0fe1e4e5a546f7',
    'builder_air.nut': '5d1655b6075054be79696a2fc4c71d376b2183cd68dc9aa410d48d111dcbf4f4',
    'globals_pre.nut': 'ad897533dd853cb14a6a14f0bdb4b98f317c213862d9bbed496c690360337651',
    'info.nut': '1bc76539590e9272aa59849baa54d0248a74ac5f993e0d0e77d679906c7ad2c3',
    'main.nut': 'b716838631daba2621fd9b7d992b72accd042c0ba0a2c4d8d89527709358ad68',
    'po01c_generators.nut': '2a294f62cb19c9c20584b731df53e8a7b94ddab9389322c405b4ab4d2cfe55d2',
    'probes.nut': '005a79a7647c1ddd98754b3854497f5328c6eb4bea62ae3a9192e0a03dfab84e',
    'settings.nut': '6946a9ed7d3864e22714167b4fbb4fe74d8e6b95b39c0fac0054cfde80bc214b',
}


def expr(code):
    """Only scalar boolean/arithmetic source expressions in these projections."""
    code = code.replace('&&', ' and ').replace('||', ' or ')
    code = re.sub(r'!(?!=)', ' not ', code)
    code = re.sub(r'\bnull\b', 'None', code)
    return ' '.join(code.split())


def evaluate(code, **context):
    return eval(expr(code), {'__builtins__': {}}, context)


class Array(list):
    """Only the Squirrel array API used by the admission predicates."""
    def len(self):
        return len(self)


def compile_predicate(name, namespace):
    """Translate the delivered scalar/queue predicate, not a rewritten policy.

    Restricted to assignments, if/return and the two bounded loop forms below.
    This is an offline projection; it cannot validate Squirrel or NoAI costs.
    """
    source = uncomment(body(name)).split('{', 1)[1].rsplit('}', 1)[0]
    tokens, start, depth = [], 0, 0
    for i, char in enumerate(source):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char in '{};' and depth == 0:
            if source[start:i].strip():
                tokens.append(source[start:i].strip())
            if char != ';':
                tokens.append(char)
            start = i + 1
    if source[start:].strip():
        tokens.append(source[start:].strip())

    def value(text):
        text = expr(text)
        if '?' in text:
            condition, yes, no = re.fullmatch(r'(.*?)\?(.*?):(.*)', text).groups()
            text = f'({yes} if {condition} else {no})'
        return text

    lines, indent = [], 1
    for token in tokens:
        if token == '{':
            indent += 1
            continue
        if token == '}':
            indent -= 1
            continue
        if token.startswith('if ('):
            level = 1
            end = 4
            while level:
                level += (token[end] == '(') - (token[end] == ')')
                end += 1
            condition = value(token[4:end-1])
            tail = token[end:].strip()
            if tail:
                assert tail.startswith('return '), tail
                token = f'if {condition}: return {value(tail[7:])}'
            else:
                token = f'if {condition}:'
        elif token.startswith('foreach ('):
            token = f'for {token[9:-1]}:'
        elif token.startswith('for ('):
            match = re.fullmatch(r'for \(local (\w+) = (.*?); \1 < (.*?); \1\+\+\)', token)
            assert match, token
            var, begin, end = match.groups()
            token = f'for {var} in range({begin}, {end}):'
        elif token.startswith('return '):
            token = 'return ' + value(token[7:])
        elif token.startswith('local '):
            lhs, rhs = token[6:].split(' = ', 1)
            token = lhs + ' = ' + value(rhs)
        else:
            raise AssertionError(token)
        lines.append('    ' * indent + token)
    assert indent == 1
    signature = re.search(r'function \w+\((.*?)\)', body(name))[1]
    script = f'def projected({signature}):\n' + '\n'.join(lines)
    env = dict(namespace, range=range)
    exec(script, env)
    return env['projected']


def admission_owner():
    return NS(_activeWorker=None, _po01cPending=False, _po01cJob=None,
              _portfolioInvalidated=False, _catalog=NS(), _reactiveQueue=None,
              _projects=NS(best=Array([NS(mode='air', capital=100)]),
                           airPlans=Array([NS(capital=1)])),
              _taskQueue=Array([NS(name='projects', enabled=True, dueCycle=0)]),
              _taskCursor=0, _taskCycle=0)


def admission(owner, room_check=lambda _: True, **settings):
    env = dict(MODE_AIR=True, CASH_RESERVE_MIN=5, C77_INTENT_DEFER=True,
               C77_INTENT_DEFER_SUBSIDY=True, PO01C_REGEN_SPLIT=True,
               AICompany=NS(COMPANY_SELF=0, GetBankBalance=lambda _: 1000),
               OpexProjectFinanceCapital=lambda p: p.capital,
               OpexPCAL02Room=room_check)
    env.update(settings)
    env['OpexPCAL02BuildTurn'] = compile_predicate('BuildTurn', env)
    return compile_predicate('Admit', env)(owner, NS())


def constants():
    return {key: int(value) for key, value in re.findall(
        r'^(PCAL02_\w+) <- (\d+);', read('pcal02_air_sites.nut'), re.M)}


def room(tick, left, mark):
    code = body('Room')
    condition = re.search(r'if \((.*?)\) return false;', code)[1]
    result = re.findall(r'\breturn ([^;]+);', code)[-1]
    api = NS(GetTick=lambda: tick, GetOpsTillSuspend=lambda: left)
    env = dict(constants(), AIController=api, mark=mark, left=left)
    return not evaluate(condition, **env) and evaluate(result, **env)


def scalar_statement(statement, entry):
    """Execute the scalar assignment subset used by the real Next function."""
    statement = statement.strip()
    increment = re.fullmatch(r'entry\.(\w+)\+\+', statement)
    if increment:
        field = increment[1]
        setattr(entry, field, getattr(entry, field) + 1)
        return
    field, rhs = re.fullmatch(r'entry\.(\w+) = (.*)', statement).groups()
    if '?' in rhs:
        condition, yes, no = re.fullmatch(r'(.*?)\?(.*?):(.*)', rhs).groups()
        rhs = yes if evaluate(condition, entry=entry) else no
    setattr(entry, field, evaluate(rhs, entry=entry))


def next_anchor(entry):
    # Interpret the actual three ifs and assignments. There is no independently
    # rewritten geometric cursor here; the independent oracle is a square ring.
    code = body('Next').split('{', 1)[1].rsplit('}', 1)[0].strip()
    first = re.match(r'if \(([^\n]+)\) ([^;]+);\s*else ([^;]+);', code)
    branch = first[2] if evaluate(first[1], entry=entry, abs=abs) else first[3]
    scalar_statement(branch, entry)
    rest = code[first.end():]
    for match in re.finditer(r'if \(([^\n]+?)\) \{([^}]+)\}', rest):
        if evaluate(match[1], entry=entry):
            for statement in match[2].split(';'):
                if statement.strip():
                    scalar_statement(statement, entry)
    scalar_statement(rest.rsplit('}', 1)[1].strip().removesuffix(';'), entry)


class Contracts(unittest.TestCase):
    def test_setting_off_and_read_once(self):
        spec = parse_ai_setting_specs(AI / 'info.nut')['pcal02_air_sites']
        self.assertEqual((spec['min_value'], spec['max_value'], spec['default']), (0, 1, 0))
        block = read('info.nut').split('name = "pcal02_air_sites"', 1)[1].split('});', 1)[0]
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(level + '_value = 0', block)
        self.assertEqual(read('settings.nut').count('GetSetting("pcal02_air_sites")'), 1)
        self.assertIn('PCAL02_AIR_SITES <- false;', read('globals_pre.nut'))

    def test_off_projection_is_byte_exact_for_all_touched_sources(self):
        self.assertEqual(OFF_REMOVALS.keys(), OFF_SHA.keys())
        for name, pieces in OFF_REMOVALS.items():
            text = read(name)
            for piece in pieces:
                expected_count = 2 if 'PCAL02_STATE.epoch++' in piece else 1
                self.assertEqual(text.count(piece), expected_count, (name, piece))
                text = text.replace(piece, '')
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), OFF_SHA[name], name)

    def test_generated_copy_tracks_source(self):
        self.assertEqual(read('po01c_generators.nut'), generated())

    def test_terminal_hook_in_both_loops_after_existing_work(self):
        for name in ('main.nut', 'probes.nut'):
            text = read(name)
            pos = text.index('if (PCAL02_AIR_SITES) OpexPCAL02Tick(this);')
            self.assertLess(text.rindex('OpexV309IdleTick(this)', 0, pos), pos)
            self.assertLess(pos, text.index('AIController.Sleep(1);', pos))
            self.assertLess(text.rindex('_advanceRailSearchThroughput()', 0, pos), pos)

    def test_log_guard_and_no_probe_side_effect(self):
        log = body('Log')
        self.assertLess(log.index('if (!DECISION_LOG) return;'), log.index('OpexDecide('))
        self.assertEqual(read('pcal02_air_sites.nut').count('OpexDecide('), 1)
        self.assertNotIn('AILog.', read('pcal02_air_sites.nut'))
        for action in ('calc', 'hit', 'miss', 'stale', 'built'):
            self.assertIn('OpexPCAL02Log("' + action + '"', read('pcal02_air_sites.nut'))
        self.assertIn('DECISION_LOG = (probes & 508) != 0;', read('settings.nut'))
        self.assertEqual(508 & 256, 256)
        self.assertNotIn('DECISION_LOG =', read('pcal02_air_sites.nut'))

    def test_existing_catalogue_only_and_executable_air_yields(self):
        code = uncomment(read('pcal02_air_sites.nut'))
        for forbidden in ('AITownList(', 'AIEngineList(', '.Valuate(', 'OpexCatalog(',
                          'OpexAirPlans(', '_ensureSelection(', 'OpexReselectProjects(',
                          'OpexCashReserve(', 'LevelTiles(', 'OpexBoostTownRating('):
            self.assertNotIn(forbidden, code)
        admit = body('Admit')
        for guard in ('OpexPCAL02BuildTurn', 'owner._projects.best',
                      'CASH_RESERVE_MIN', 'OpexProjectFinanceCapital'):
            self.assertIn(guard, admit)
        self.assertNotIn('owner._projects.airPlans', admit)
        self.assertNotIn('c78AirRebuild', uncomment(body('BuildTurn')))
        for code in (admit, body('BuildTurn')):
            for loop in re.split(r'\b(?:for|foreach) \(', code)[1:]:
                self.assertIn('if (!OpexPCAL02Room(mark)) return "room";', loop)
        self.assertIn('catalog.airCombos', body('Combo'))
        self.assertIn('AIEngine.IsBuildable', body('Combo'))
        self.assertIn('OpexAirAirportAcceptsPlane', body('Combo'))
        self.assertNotIn('AT_LARGE', code)

    def test_waiting_worker_or_queue_allows_fundable_air(self):
        owner = admission_owner()
        self.assertEqual(admission(owner), 'best_air')
        owner._activeWorker = NS(kind='regen_candidates')
        self.assertEqual(admission(owner), 'none')
        owner._activeWorker = None
        owner._taskQueue.insert(0, NS(name='air_cat_scan', enabled=True, dueCycle=0,
                                     c78AirRebuild=NS()))
        self.assertEqual(admission(owner), 'none')
        owner._taskCursor = 1
        self.assertEqual(admission(owner), 'best_air')

    def test_raw_air_plan_and_unpublished_portfolio_are_not_executable(self):
        owner = admission_owner()
        owner._projects.best.clear()
        self.assertEqual(admission(owner), 'none')  # cheap raw plan is still present
        owner._projects = None
        self.assertEqual(admission(owner), 'none')
        owner = admission_owner()
        owner._portfolioInvalidated = True
        self.assertEqual(admission(owner), 'none')

    def test_partial_lots_and_rail_workers_do_not_hide_ready_air(self):
        owner = admission_owner()
        owner._po01cPending = True
        owner._po01cJob = NS()
        owner._taskQueue[0].c78AirRebuild = NS(published=True)
        self.assertEqual(admission(owner), 'best_air')
        for kind in ('rail_search', 'rail_stock'):
            owner._activeWorker = NS(kind=kind)
            self.assertEqual(admission(owner), 'best_air')
        owner._projects.best[0].capital = 996
        self.assertEqual(admission(owner), 'none')

    def test_queue_suffix_wrap_and_reactive_build_priority(self):
        owner = admission_owner()
        owner._taskQueue = Array([NS(name='catalog', enabled=True, dueCycle=1),
                                  NS(name='projects', enabled=True, dueCycle=0)])
        self.assertEqual(admission(owner), 'best_air')  # current suffix before next cycle
        owner._taskQueue[1].dueCycle = 1
        self.assertEqual(admission(owner), 'none')  # next cycle starts with catalog
        owner._taskQueue[0].enabled = False
        self.assertEqual(admission(owner), 'best_air')
        owner._taskQueue[0].enabled = True
        owner._taskQueue[0].dueCycle = 0
        owner._reactiveQueue = NS(isEmpty=lambda: False, _order=['build'], _head=0,
                                 get=lambda _: NS(kind='c77_build'))
        self.assertEqual(admission(owner), 'best_air')
        owner._po01cPending = True
        self.assertEqual(admission(owner), 'none')  # C77 defer 2; catalog is next

    def test_denial_reasons_and_budgeted_readiness(self):
        owner = admission_owner()
        self.assertEqual(admission(owner, MODE_AIR=False), 'mode_off')
        owner._catalog = None
        self.assertEqual(admission(owner), 'catalog_missing')
        owner._catalog = NS()
        for successful_checks in range(3):
            calls = iter([True] * successful_checks + [False] * 10)
            self.assertEqual(admission(owner, room_check=lambda _: next(calls)), 'room')
        tick = body('Tick')
        self.assertIn('" deny=" + deny', tick)
        for reason in ('stock_ready', 'entry_expired', 'room'):
            self.assertIn('"' + reason + '"', tick)
        self.assertIn('local admitted = deny == "none";', tick)

    def test_tick_guard_uses_its_measurement_mark_after_precheck(self):
        tick = body('Tick')
        self.assertIn('local tick = mark.tick;', tick)
        self.assertLess(tick.index('GetOpsTillSuspend() <'), tick.index('OpexOpsMeasureBegin()'))
        self.assertLess(tick.index('OpexOpsMeasureBegin()'), tick.index('local tick = mark.tick;'))
        self.assertLess(tick.index('local tick = mark.tick;'), tick.index('PCAL02_STATE.lastTick = tick;'))
        self.assertNotIn('local tick = AIController.GetTick();', tick)

    def test_bounded_tick_and_fixed_size_steps(self):
        conf = constants()
        self.assertEqual(conf['PCAL02_TICK_BUDGET'], 4000)
        self.assertEqual(conf['PCAL02_SLEEP_RESERVE'], 2000)
        self.assertEqual(conf['PCAL02_MAX_STEPS'], 16)
        tick = body('Tick')
        for text in ('PCAL02_STATE.lastTick == tick', 'PCAL02_STATE.fault',
                     'OpexPCAL02Room(mark) && steps < PCAL02_MAX_STEPS',
                     'total > PCAL02_TICK_BUDGET', 'PCAL02_STATE.fault = true',
                     'reason=budget_overrun'):
            self.assertIn(text, tick)
        step = uncomment(body('Step'))
        self.assertNotRegex(step, r'\b(for|foreach|while)\s*\(')
        self.assertIn('entry.tileIndex++', step)
        self.assertIn('entry.tested >= PCAL02_MAX_ANCHORS', step)
        self.assertIn('C96_AIR_SITE_MAX_VALID', step)

    def test_room_real_expression_rejects_other_tick_and_small_reliquats(self):
        for initial in range(0, 10001, 29):
            mark = NS(tick=5, left=initial)
            self.assertFalse(room(6, 10000, mark))
            for spent in (0, 500, 2200, 2201, 4000):
                allowed = room(5, initial - spent, mark)
                if allowed:
                    self.assertLessEqual(spent + 1200 + 600, 4000)
                    self.assertGreaterEqual(initial - spent - 1200 - 600, 2000)

    def test_simulated_atomic_upper_bound_allows_tail_without_crossing_tick(self):
        # This proves the guard arithmetic only, assuming <=1200 per atom.
        # That assumption is explicitly unmeasured until a real NoAI smoke.
        for initial in (6000, 7000, 10000):
            for atom in (80, 600, 1200):
                mark = NS(tick=1, left=initial)
                left, count = initial - 300, 0  # admission/dispatch fixture cost
                while room(1, left, mark) and count < constants()['PCAL02_MAX_STEPS']:
                    left -= atom
                    count += 1
                left -= 600
                self.assertLessEqual(initial - left, 4000)
                self.assertGreaterEqual(left, 2000)

    def test_flat_test_commands_are_scoped_and_accounting_shielded(self):
        step = body('Step')
        scope = step.split('entry.phase == 2', 1)[1].split('entry.phase == 3', 1)[0]
        for text in ('local shield = AIAccounting();', 'local test = AITestMode();',
                     'AIAirport.BuildAirport(', 'shield.GetCosts()',
                     'ERR_STATION_TOO_MANY_STATIONS_IN_TOWN'):
            self.assertIn(text, scope)
        self.assertLess(scope.index('local test = AITestMode();'), scope.index('AIAirport.BuildAirport('))
        self.assertEqual(step.count('AIAirport.BuildAirport('), 1)
        self.assertIn('AITile.GetMaxHeight(tile) != entry.z', step)
        self.assertIn('OpexAirSiteHasCatchment', step)
        self.assertIn('OpexAirC96SiteCatchmentScore', step)

    def test_invalidation_ttl_epoch_year_engine_catalogue_and_dimensions(self):
        fresh = body('Expiry')
        for predicate in ('entry.epoch != PCAL02_STATE.epoch', 'date < entry.date',
                          'date - entry.date >= PCAL02_TTL_DAYS', 'entry.year',
                          'entry.airport.width != airport.width', 'entry.airport.height != airport.height',
                          'combo.plane.id != entry.plane.id', 'AITown.IsValidTown'):
            self.assertIn(predicate, fresh)
        coverage = read('air_coverage.nut')
        for name in ('OpexAir0310InvalidateSiteValidity', 'OpexAirInvalidateCachedSite'):
            self.assertIn('if (PCAL02_AIR_SITES) PCAL02_STATE.epoch++;', function(coverage, name))
        entry = NS(epoch=2, date=100, year=1970, plane=NS(id=223),
                   airport=NS(type=1, width=6, height=6), town=NS(id=1))
        state = NS(epoch=2)
        combo = NS(plane=NS(id=223))
        def expiry(date=120, year=1970):
            project = compile_predicate('Expiry', dict(constants(), PCAL02_STATE=state,
                OpexPCAL02Combo=lambda _: combo, AIDate=NS(GetCurrentDate=lambda: date,
                GetYear=lambda _: year), AITown=NS(IsValidTown=lambda _: True)))
            return project(entry, NS(type=1, width=6, height=6))
        self.assertEqual(expiry(189), 'none')
        self.assertEqual(expiry(190), 'ttl')
        self.assertEqual(expiry(99), 'date_reversed')
        state.epoch = 3
        self.assertEqual(expiry(), 'epoch')
        state.epoch = 2
        self.assertEqual(expiry(year=1971), 'year')
        combo = NS(plane=NS(id=223))  # replacement tables, same compatible engine
        self.assertEqual(expiry(), 'none')
        combo.plane.id = 224
        self.assertEqual(expiry(), 'engine')
        entry.airport.width = 7
        self.assertEqual(expiry(), 'dimensions')

    def test_unstarted_demand_survives_epoch_and_year_but_not_ttl(self):
        entry = NS(epoch=2, date=100, year=1970, plane=None,
                   airport=NS(type=1, width=6, height=6), town=NS(id=1))
        api = NS(GetCurrentDate=lambda: 114, GetYear=lambda _: 1971)
        expiry = compile_predicate('Expiry', dict(constants(), PCAL02_STATE=NS(epoch=9),
            AIDate=api, AITown=NS(IsValidTown=lambda _: True)))
        self.assertEqual(expiry(entry, entry.airport), 'none')
        api.GetCurrentDate = lambda: 190
        self.assertEqual(expiry(entry, entry.airport), 'ttl')
        tick = body('Tick')
        self.assertIn('entry.epoch = PCAL02_STATE.epoch;', tick)
        self.assertIn('entry.year = AIDate.GetYear(AIDate.GetCurrentDate());', tick)
        self.assertNotIn('entry.date =', tick)  # no sliding TTL on preparation
        drop = body('Drop')
        self.assertIn('" cause=" + OpexPCAL02Expiry', drop)
        self.assertIn('" age_days="', drop)

    def test_stock_top_k_and_request_limit(self):
        self.assertEqual(constants()['PCAL02_TOP_K'], 2)
        self.assertEqual(constants()['PCAL02_MAX_ENTRIES'], 8)
        request = body('Request')
        self.assertIn('stock[pos].town.pop >= town.pop', request)
        self.assertIn('if (pos >= PCAL02_MAX_ENTRIES) return null;', request)
        self.assertIn('stock.len() >= PCAL02_MAX_ENTRIES', request)
        # Execute the source comparator against independent lexicographic sorting.
        compare = re.search(r'if \((.*?)\) break;', body('Keep'), re.S)[1]
        rng = random.Random(20261025)
        items = [NS(anchor=i, pax=rng.randrange(5), mail=rng.randrange(3), cost=rng.randrange(3))
                 for i in range(100)]
        top = []
        for item in items:
            at = next((i for i, other in enumerate(top) if evaluate(compare, item=item, other=other)), len(top))
            top.insert(at, item)
            top = top[:2]
        expected = sorted(items, key=lambda x: (-x.pax, -x.mail, x.cost))[:2]
        self.assertEqual([x.anchor for x in top], [x.anchor for x in expected])

    def test_source_cursor_resume_matches_ring_oracle_without_duplicates(self):
        entry = NS(r=4, dx=-4, dy=-4, phase=4)
        anchors = []
        while entry.r <= 25:
            anchors.append((entry.r, entry.dx, entry.dy))
            next_anchor(entry)
            self.assertEqual(entry.phase, 0)
            entry = copy.deepcopy(entry)  # copy the transient cursor between every invocation
        expected = [(r, x, y) for r in range(4, 26)
                    for x in range(-r, r + 1) for y in range(-r, r + 1)
                    if max(abs(x), abs(y)) == r]
        self.assertEqual(anchors, expected)
        self.assertEqual(len(anchors), len(set(anchors)))

    def test_new_function_calls_and_entry_writes_have_definitions(self):
        code = uncomment(read('pcal02_air_sites.nut'))
        functions = set(re.findall(r'function (OpexPCAL02\w+)\(', code))
        calls = set(re.findall(r'\b(OpexPCAL02\w+)\(', code))
        self.assertEqual(calls, functions)
        initializer = body('Request').split('local entry = {', 1)[1].split('};', 1)[0]
        fields = set(re.findall(r'\b(\w+)\s*=', initializer))
        for name in ('Next', 'Keep', 'Step', 'Tick'):
            assignments = set(re.findall(r'entry\.(\w+)\s*(?:=(?!=)|\+\+|\+=)', body(name)))
            self.assertLessEqual(assignments, fields, name)

    def test_lookup_is_not_construction_and_c83_is_excluded(self):
        find = body('FindSite')
        self.assertIn('OpexAirSiteStillBuildable', find)
        self.assertIn('OpexAirSiteHasCatchment', find)
        self.assertIn('AIR_SITE_CACHE.rawset', find)
        self.assertIn('site.pcal02 <-', find)
        self.assertIn('entry.credited ? 0', find)
        self.assertIn('saved_kind=prepared_proxy', find)
        self.assertNotIn('OpexPCAL02Built(', find)
        original = function(read('air_sites.nut'), 'OpexAirFindSite')
        self.assertIn('PCAL02_AIR_SITES && requiredSlotTownId < 0', original)
        self.assertLess(original.index('town.id in probes.stationLimitedTowns'), original.index('OpexPCAL02FindSite'))

    def test_physical_consumer_revalidates_then_records_actual_airports(self):
        build = function(read('air_construction.nut'), 'OpexBuildAirRoute')
        self.assertLess(build.index('OpexPCAL02BuildSiteOk'), build.index('local costs = AIAccounting();'))
        check = body('BuildSiteOk')
        for token in ('PCAL02_TTL_DAYS', 'PCAL02_STATE.epoch', 'proof.engine == plane.id',
                      'OpexTownAirportAllowedByLevel', 'OpexAirSiteStillBuildable',
                      'OpexAirSiteHasCatchment', 'shield.GetCosts() <= proof.cost',
                      'local test = AITestMode();', 'OpexAirInvalidateCachedSite'):
            self.assertIn(token, check)
        for side in 'AB':
            self.assertLess(build.index(f'if (ok{side} && AIAirport.IsAirportTile'),
                            build.index(f'OpexPCAL02Built(plan.site{side}, airport)'))
        self.assertIn('AICompany.IsMine', body('Built'))
        self.assertIn('AIAirport.GetAirportType', body('Built'))

    def test_transient_reset_after_load_before_any_loop(self):
        self.assertNotIn('PCAL02', read('persist.nut'))
        reset = body('Reset')
        self.assertIn('PCAL02_STATE.entries = [];', reset)
        self.assertIn('PCAL02_STATE.catalog = null;', reset)
        self.assertIn('PCAL02_STATE.fault = false;', reset)
        start = function(read('main.nut'), 'OpexAI::Start')
        self.assertLess(start.index('OpexLoadSettings();'), start.index('OpexAirResetSiteCache();'))
        self.assertLess(start.index('OpexAirResetSiteCache();'), start.index('while (true)'))
        self.assertIn('if (PCAL02_AIR_SITES) OpexPCAL02Reset();',
                      function(read('air_coverage.nut'), 'OpexAirResetSiteCache'))

    def test_no_new_squirrel_traps(self):
        code = uncomment(read('pcal02_air_sites.nut'))
        self.assertNotRegex(code, r'\b(?:clone|base|parent|static|delegate|vargc|vargv|resume|yield|constructor|instanceof)\b')
        self.assertNotRegex(code, r'function\s*\(')
        self.assertNotIn('.find(', code)
        self.assertNotIn('const ', code)
        self.assertNotIn('.Valuate(', code)
        # Strings and comments are skipped; catch delimiter errors before a VM smoke.
        stack = []
        for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}()\[\]]', code):
            if token[0].startswith('"'):
                continue
            if token[0] in '({[':
                stack.append(token[0])
            else:
                self.assertTrue(stack)
                self.assertEqual(stack.pop(), dict(zip(')}]', '({['))[token[0]])
        self.assertFalse(stack)


if __name__ == '__main__':
    unittest.main()
