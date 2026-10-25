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

    def test_existing_catalogue_only_and_busy_or_fundable_air_yields(self):
        code = uncomment(read('pcal02_air_sites.nut'))
        for forbidden in ('AITownList(', 'AIEngineList(', '.Valuate(', 'OpexCatalog(',
                          'OpexAirPlans(', '_ensureSelection(', 'OpexReselectProjects(',
                          'OpexCashReserve(', 'LevelTiles(', 'OpexBoostTownRating('):
            self.assertNotIn(forbidden, code)
        admit = body('Admit')
        for guard in ('owner._activeWorker != null', 'owner._po01cPending',
                      'owner._po01cJob != null', 'task.c78AirRebuild != null',
                      'owner._projects.best', 'owner._projects.airPlans',
                      'CASH_RESERVE_MIN', 'OpexProjectFinanceCapital',
                      'OpexAirRequiredMargin', 'plan.plane.price'):
            self.assertIn(guard, admit)
        for loop in admit.split('foreach (')[1:]:
            self.assertIn('if (!OpexPCAL02Room(mark)) return false;', loop)
        self.assertIn('catalog.airCombos', body('Combo'))
        self.assertIn('AIEngine.IsBuildable', body('Combo'))
        self.assertIn('OpexAirAirportAcceptsPlane', body('Combo'))
        self.assertNotIn('AT_LARGE', code)

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
        fresh = body('Fresh')
        for predicate in ('entry.epoch != PCAL02_STATE.epoch', 'date < entry.date',
                          'date - entry.date >= PCAL02_TTL_DAYS', 'entry.year',
                          'entry.airport.width != airport.width', 'entry.airport.height != airport.height',
                          'combo.plane.id == entry.plane.id', 'entry.combos == entry.catalog.airCombos',
                          'entry.catalog == PCAL02_STATE.catalog', 'AITown.IsValidTown'):
            self.assertIn(predicate, fresh)
        coverage = read('air_coverage.nut')
        for name in ('OpexAir0310InvalidateSiteValidity', 'OpexAirInvalidateCachedSite'):
            self.assertIn('if (PCAL02_AIR_SITES) PCAL02_STATE.epoch++;', function(coverage, name))
        condition = re.search(r'if \((.*?)\) return false;', fresh, re.S)[1]
        entry = NS(epoch=2, date=100, year=1970, airport=NS(width=6, height=6), town=NS(id=1))
        state = NS(epoch=2)
        def invalid(date=120):
            return evaluate(condition, entry=entry, airport=NS(width=6, height=6),
                            date=date, PCAL02_STATE=state, **constants(),
                            AIDate=NS(GetYear=lambda _: 1970), AITown=NS(IsValidTown=lambda _: True))
        self.assertFalse(invalid(189))
        self.assertTrue(invalid(190))
        self.assertTrue(invalid(99))
        state.epoch = 3
        self.assertTrue(invalid())
        state.epoch = 2
        entry.airport.width = 7
        self.assertTrue(invalid())

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
