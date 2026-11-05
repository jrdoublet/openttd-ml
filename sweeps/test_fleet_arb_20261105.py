"""Static contracts only: these tests neither compile nor simulate NoAI."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import unittest

from fleet_arb_off import MANIFEST, off_source, NEW_MODULES

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def mask(source):
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                  lambda m: " " * len(m[0]), source, flags=re.S)


def args(source, opening):
    depth = 0
    count = 0
    nonempty = False
    for i in range(opening + 1, len(source)):
        c = source[i]
        if c == ')' and depth == 0:
            return count + int(nonempty), i
        if c in '([{': depth += 1
        elif c in ')]}': depth -= 1
        elif c == ',' and depth == 0: count += 1
        if not c.isspace(): nonempty = True
    raise AssertionError("unterminated call")


class FleetArbContracts(unittest.TestCase):
    def test_setting_opt_in_four_defaults_single_read(self):
        setting = re.search(r'AddSetting\(\{ name = "fleet_arb",(.*?)\}\);', read('info.nut'), re.S)[1]
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(f'{level}_value = 0', setting)
        sources = ''.join(p.read_text(encoding='utf-8') for p in AI.glob('*.nut'))
        self.assertEqual(sources.count('AIController.GetSetting("fleet_arb")'), 1)
        self.assertIn('FLEET_ARB <- false;', read('globals_pre.nut'))
        self.assertEqual(read('info.nut').count('AddSetting('), 158)
        self.assertEqual(off_source('info.nut', read('info.nut')).count('AddSetting('), 157)

    def test_all_changed_sources_restore_exact_base_and_are_idempotent(self):
        for name, entry in MANIFEST['files'].items():
            with self.subTest(name=name):
                projected = off_source(name, read(name))
                self.assertEqual(hashlib.sha256(projected.encode()).hexdigest(), entry['sha256'])
                self.assertEqual(off_source(name, projected), projected)
                historical = subprocess.check_output(['git', 'show', f"{MANIFEST['base']}:ai/OpexAI/{name}"], cwd=ROOT)
                self.assertEqual(projected.encode(), historical)

    def test_new_modules_absent_off(self):
        for name in NEW_MODULES:
            self.assertEqual(off_source(name, read(name)), '')

    def test_complete_physical_writer_inventory_and_admission_routes(self):
        inventory = json.loads((ROOT / 'sweeps/fixtures/fleet_arb_writers_20261105.json').read_text(encoding='utf-8'))
        actual = []
        for p in sorted(AI.glob('*.nut')):
            text = p.read_text(encoding='utf-8')
            definitions = list(re.finditer(r'^function ([\w:]+)\(', text, re.M))
            for call in re.finditer(r'AIVehicle\.(BuildVehicle(?:WithRefit)?|CloneVehicle|SellVehicle|AttachWagon|MoveWagon|RefitVehicle|SendVehicleToDepot)\(', text):
                fn = [m for m in definitions if m.start() < call.start()][-1][1]
                actual.append((p.name, fn, call[1]))
        self.assertEqual(actual, [(r['file'], r['function'], r['api']) for r in inventory])
        self.assertEqual(len(inventory), 100)
        for row in inventory:
            self.assertIn(row['policy'], ('admitted', 'native_transaction', 'rollback', 'simulation'))
            if row['policy'] == 'admitted':
                text = read(row['gate_file'])
                start = text.index('function ' + row['function'] + '(')
                end = text.find('\nfunction ', start + 1)
                body = text[start:end if end >= 0 else len(text)]
                self.assertIn('FLEET_ARB', body)
                self.assertIn('OpexFleetRequest(', body)
                self.assertIn('"' + row['source'] + '"', body)
            else:
                self.assertTrue(row['reason'])

    def test_pending_gross_reservations_survive_load_and_recheck_before_build(self):
        s = read('fleet_arb.nut')
        self.assertIn('reserved = action.cost', s)
        self.assertIn('total += lock.reserved', s)
        self.assertIn('lock.lineId >= 0 ? owner._findLineById(lock.lineId)', s)
        self.assertIn('lock.reserved = 0', s)
        self.assertIn('typeof lock.reserved == "integer"', s)
        for name, marker in [('task_v257.nut','local built = OpexBuildTrains('),
                             ('task_v284.nut','local built = OpexBuildTrains(')]:
            text=read(name)
            self.assertLess(text.index('OpexFleetSpendAllowed('), text.index(marker))
        self.assertIn('OpexFleetFinish(line, "SCRAP_LINE", remaining.len() == 0', read('task_report.nut'))

    def test_mutation_code_and_existing_settings_unchanged_off(self):
        # The independent frozen SHA witnesses cover *all* existing .nut edits,
        # including branches tested through historical projected readers.
        tracked=subprocess.check_output(['git','diff','--name-only',MANIFEST['base'],'--','ai/OpexAI'],cwd=ROOT,text=True)
        names={Path(p).name for p in tracked.splitlines() if p.endswith('.nut')}
        self.assertLessEqual(names, set(MANIFEST['files']) | NEW_MODULES)
        for name in NEW_MODULES:
            self.assertNotIn('AIController.GetSetting(',read(name))

    def test_partial_and_unreviewed_edits_fail_closed(self):
        for name, entry in MANIFEST['files'].items():
            source = read(name)
            with self.subTest(name=name):
                with self.assertRaises(AssertionError):
                    off_source(name, source.replace('fleet_arb', 'fleet_arb_BROKEN', 1)
                               if name in ('info.nut', 'main.nut') else source.replace('FLEET_ARB', 'FLEET_ARB_BROKEN', 1))
                with self.assertRaises(AssertionError):
                    off_source(name, source + '\n// unexplained edit\n')

    def test_every_hook_is_guarded_or_loads_only_saved_feature_state(self):
        for name in MANIFEST['files']:
            if name in ('globals_pre.nut','settings.nut','info.nut','main.nut'): continue
            for line in read(name).splitlines():
                if 'OpexFleet' not in line: continue
                # Multi-line request expressions have their guard on the prior line.
                pos = read(name).index(line)
                context = read(name)[max(0,pos-1000):pos+len(line)]
                self.assertTrue('FLEET_ARB' in context or '"fleetArb" in data' in context, (name,line))

    def test_writers_have_admission_before_first_mutation(self):
        for name, source in [('task_v257.nut','V257'), ('task_v284.nut','V284'),
                ('invest_stall_fleet.nut','INVEST_STALL'), ('rail_loop.nut','RAIL_LOOP'),
                ('builder_rail.nut','BUILD_RAIL'), ('air_fleet.nut','AIR_FLEET'),
                ('builder_road.nut','ROAD_REFLEET'), ('builder_water.nut','BUILD_WATER'),
                ('task_report.nut','SCRAP_LINE'), ('task_v252.nut','V252'),
                ('bus_districts.nut','ROAD_WEAK_TRANSFER'), ('airport_feeder.nut','AIRPORT_FEEDER')]:
            with self.subTest(name=name):
                self.assertIn('OpexFleetRequest(', read(name))
                self.assertIn('"'+source+'"', read(name))
        self.assertLess(read('task_v257.nut').index('"V257"))'),
                        read('task_v257.nut').index('this._v257Pending = { lineId'))
        self.assertLess(read('rail_loop.nut').index('OpexFleetRequest('),
                        read('rail_loop.nut').index('AIVehicle.CloneVehicle('))

    def test_monthly_sort_budget_and_hard_bounds(self):
        s = read('fleet_arb.nut')
        for token in ('state.month == month', 'state.queue.sort(OpexFleetCompare)',
                      'a.marginalProfitYear.tofloat() * b.cost',
                      'a.serial < b.serial', 'FLEET_ARB_QUEUE_LIMIT = 64',
                      'FLEET_ARB_ACTION_LIMIT = 8', 'budget -= action.cost',
                      'FLEET_ARB_OPS = 12000', 'OpexOpsMeasureEnd(mark) >= FLEET_ARB_OPS',
                      'OpexAvailableCapital() - FLEET_ARB_RESERVE - OpexFleetReserved()',
                      '"quote_changed"', '"cash_recheck"', '"nonpositive_margin"'):
            self.assertIn(token,s)
        self.assertNotIn('Sleep(', s)
        self.assertNotRegex(s, r'AIVehicle\.(Build|Clone|Sell|Refit|Move|Send)')

    def test_lock_precedes_authorization_and_native_transactions_block(self):
        s=read('fleet_arb.nut')
        self.assertIn('FLEET_ARB_HOLD_DAYS = 90',s)
        self.assertLess(s.index('state.locks.rawset(action.key'),s.index('"live_revalidation"'))
        for token in ('"recent_action"','"transaction_busy"','"line_locked"',
                      '_v257Pending','_railLongV3UpgradePending','_v284State','_vehiclesToRetire'):
            self.assertIn(token,s)
        self.assertIn('OpexFleetBorn(',read('task_rail.nut'))

    def test_save_load_no_live_queue_or_float_serialization(self):
        s=read('fleet_arb.nut')
        save=s[s.index('function OpexFleetSave()'):s.index('function OpexFleetLoad(')]
        for token in ('queue','grants','active','stamp','marginalProfitYear'):
            self.assertNotIn(token,save)
        self.assertIn('FLEET_ARB_STATE = null;',s[s.index('function OpexFleetLoad('):])
        self.assertIn('shortSave.fleetArb <- OpexFleetSave()',read('persist.nut'))
        self.assertIn('saveObj.fleetArb <- OpexFleetSave()',read('persist.nut'))
        self.assertIn('typeof lock.until != "integer"',s)

    def test_common_scheduler_reaches_profiled_and_normal_loops(self):
        self.assertIn('if (FLEET_ARB) OpexFleetTick(this);',read('scheduler.nut'))
        self.assertIn('_runNextTask',read('main.nut'))
        self.assertIn('_runOrchestratorTick',read('probes.nut'))
        self.assertIn('_runNextTask',read('orchestrator.nut'))

    def test_logs_all_lifecycle_outcomes(self):
        s=read('fleet_arb.nut')
        for event in ('proposed','retained','refused','executed','failed'):
            self.assertIn('"'+event+'"',s)
        self.assertIn('if (DECISION_LOG) OpexDecide("FLEET_ARB"',s)

    def test_new_functions_exist_and_call_arities_match(self):
        definitions={}
        all_sources={p.name:p.read_text(encoding='utf-8') for p in AI.glob('*.nut')}
        for s in all_sources.values():
            for m in re.finditer(r'function\s+(Opex\w+)\s*\(([^)]*)\)',s):
                params=[p.strip() for p in m[2].split(',') if p.strip()]
                definitions[m[1]]=(sum('=' not in p for p in params),len(params))
        for name,s in all_sources.items():
            for m in re.finditer(r'\b(Opex\w+)\s*\(',s):
                if name not in NEW_MODULES and not m[1].startswith('OpexFleet'): continue
                if s[max(0,m.start()-9):m.start()].strip()=='function': continue
                if mask(s)[m.start():m.end()].strip()=='': continue
                count,_=args(mask(s),s.index('(',m.start()))
                with self.subTest(file=name,call=m[1]):
                    self.assertIn(m[1],definitions)
                    low,high=definitions[m[1]]
                    self.assertTrue(low<=count<=high,(m[1],count,low,high))

    def test_no_new_squirrel_parser_traps(self):
        for name in NEW_MODULES:
            s=mask(read(name))
            self.assertNotRegex(s,r'\b(local|function)\s+(clone|base|parent|static|delegate|resume|yield)\b')
            self.assertNotRegex(s,r'function\s*\(')
            self.assertNotIn('.find(',s)
            stack=[]
            for c in s:
                if c in '([{': stack.append(c)
                elif c in ')]}': self.assertEqual(stack.pop(),{')':'(',']':'[','}':'{'}[c],name)
            self.assertEqual(stack,[],name)


if __name__ == '__main__':
    unittest.main()
