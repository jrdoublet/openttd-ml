"""B2 contracts: default path, homogeneous units, live map and save projection.

These checks do not compile Squirrel; the five-seed OFF/ON engine runs do.
"""
import difflib
import hashlib
import json
import re
from pathlib import Path
import subprocess
import unittest

from test_v261_forum_behaviours import body, source
from road100_off_projection import _subtract_exact

ROOT = Path(__file__).resolve().parents[1]
# Default-path bodies that are 4354cafa plus only the lines origin/master
# inserted inside the function. The merged text is not a single ancestor blob.
MERGED_FUNCTION_SHA = {
    'OpexAI::_tryBuildRoadProject': 'e775e1aeba5ba60d22409e032c21b652d62549c27b8d18dc85b9b0b0daa21f69',
    'OpexAI::_refleetRoadLines': '6fb02ac06ca4b6041c90165910ffc324148693f88faa160ed535f5ff0097048d',
}
MASTER_OWNED_FUNCTIONS = (
    'OpexCandidateStillValid',
    'OpexCandidateStillValidIndexed',
)


def complete_function(text, name):
    match = re.search(r'function ' + re.escape(name) + r'\s*\(', text)
    start = text.index('{', match.end())
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|[{}]', text[start:]):
        if token[0] == '{':
            depth += 1
        elif token[0] == '}':
            depth -= 1
            if depth == 0:
                return text[match.start():start + token.end()]
    raise AssertionError(name)


class BusDistrictContracts(unittest.TestCase):
    def test_lazy_overrides_are_only_reviewed_deltas_of_live_modules(self):
        edits = json.loads((ROOT / 'sweeps/fixtures/road100_bus_districts_overrides.json').read_text())
        for name, item in edits.items():
            with self.subTest(name=name):
                original = complete_function(source(item['file']), name)
                if name == 'OpexAI::_refleetRoadLines':
                    original = original.replace('  if (ROAD1Y_SAVED_STOPS) return OpexRoad1yRefleetSaved.call(this, year);\n', '')
                projected = complete_function(source('bus_districts_overrides.nut'),
                    'OpexRoad1yRefleetSaved' if name == 'OpexAI::_refleetRoadLines' else name)
                projected = projected.replace('function OpexRoad1yRefleetSaved', 'function OpexAI::_refleetRoadLines')
                for edit in reversed(item['hunks']):
                    self.assertEqual(projected.count(edit['after']), 1)
                    projected = projected.replace(edit['after'], edit['before'], 1)
                self.assertEqual(projected, original)
                if name in MERGED_FUNCTION_SHA:
                    # Byte pin, plus the proof that every difference from
                    # 4354cafa is an insertion taken from origin/master.
                    self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                                     MERGED_FUNCTION_SHA[name])
                    baseline = subprocess.check_output(
                        ['git', 'show', '4354cafa:ai/OpexAI/' + item['file']], cwd=ROOT).decode()
                    master_text = subprocess.check_output(
                        ['git', 'show', '481e7c08:ai/OpexAI/' + item['file']], cwd=ROOT).decode()
                    parent_fn = complete_function(baseline, name)
                    matcher = difflib.SequenceMatcher(
                        None, parent_fn.splitlines(), original.splitlines(), autojunk=False)
                    saw_insert = False
                    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
                        if tag == 'equal':
                            continue
                        saw_insert = True
                        self.assertEqual(tag, 'insert')
                        self.assertIn('\n'.join(original.splitlines()[j1:j2]), master_text)
                    self.assertTrue(saw_insert)
                else:
                    rev = '481e7c08' if name in MASTER_OWNED_FUNCTIONS else '4354cafa'
                    historical = subprocess.check_output(
                        ['git', 'show', rev + ':ai/OpexAI/' + item['file']], cwd=ROOT).decode()
                    self.assertEqual(original, complete_function(historical, name))

    def test_lazy_class_methods_are_installed_before_instantiation(self):
        settings = source('settings.nut')
        loader = body('settings.nut', 'OpexLoadBusDistrictSettings')
        self.assertIn('require("bus_districts_overrides.nut")', loader)
        self.assertNotIn('bus_districts_overrides', body('settings.nut', 'OpexLoadSettings'))
        self.assertEqual(settings.count('GetSetting("road1y_pax_sites")'), 1)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_PAX_SITES = false;", loader)
        self.assertTrue(source('main.nut').rstrip().endswith('OpexLoadBusDistrictSettings();'))
        self.assertIn('OpexAI._refleetRoadLines <- OpexRoad1yRefleetSaved;', source('bus_districts_overrides.nut'))
        self.assertNotIn('OpexAI._refleetRoadLines =', source('bus_districts_overrides.nut'))

    def test_reviewed_layer_reconstructs_exact_parent(self):
        edits = json.loads((ROOT / 'sweeps/fixtures/road100_bus_districts_hunks.json').read_text())
        for name, hunks in edits.items():
            with self.subTest(name=name):
                parent = subprocess.check_output(
                    ['git', 'show', '481e7c08:ai/OpexAI/' + name], cwd=ROOT).decode()
                self.assertEqual(_subtract_exact(name, source(name), hunks, 'B2'), parent)

    def test_no_shadowed_lists_in_default_fallback(self):
        code = body('bus_districts_overrides.nut', 'OpexRoadPlanPaxVoirie')
        self.assertEqual(code.count('local sitesA'), 1)
        self.assertNotIn('local sitesB = OpexRoadPaxVoirieSites', code)
        self.assertIn('sitesA = [candidate.siteA]; sitesB = [candidate.siteB];', code)

    def test_coverage_and_dimensions_are_consistent(self):
        code = body('bus_districts.nut', 'OpexBusDistrictSites')
        self.assertIn('cargo, x1-x0+1, y1-y0+1, 0)', code)
        self.assertIn('site.prod < entry.producers', code)
        self.assertIn('monthly * captured / entry.producers', code)
        self.assertIn('sites.len() < 12', code)
        self.assertIn('today - entry.date >= 90', code)
        self.assertIn('site.claimed = OpexRoad100CatchmentOverlaps', code)
        self.assertLess(code.index('OpexBusDistrictAxis(tile)'), code.index('AITestMode()'))
        self.assertNotIn('STATION_RATING_PCT', code)  # economics applies headway rating

    def test_load_and_monthly_recount_use_physical_union(self):
        code = body('bus_districts.nut', 'OpexRoad1yReconcileExtraStops')
        self.assertIn('AITileList_StationType(AIStation.GetStationID(root), kind)', code)
        self.assertIn('line.nStopsA = count', code)
        self.assertNotIn('lost', code)
        load = body('bus_districts_overrides.nut', 'OpexAI::_reconcileAfterLoad')
        self.assertIn('ROAD_BUS_SITE_CACHE.clear()', load)
        self.assertIn('OpexRoad1yReconcileExtraStops(line)', load)
        task = body('bus_districts_overrides.nut', 'OpexRoad1yRefleetSaved')
        self.assertLess(task.index('delete this._saveProjection[line]'),
                        task.index('OpexRoad1yCleanupExtraStop(line)'))
        self.assertLess(task.index('OpexRoad1yCleanupExtraStop(line)'),
                        task.index('"expandBlocked"'))
        self.assertLess(task.index('newCounts[side]'),
                        task.index('OpexRoad1yReconcileExtraStops(line)'))

    def test_joined_geometry_is_reserved_before_next_district(self):
        scan = body('bus_districts.nut', 'OpexBusDistrictSites')
        self.assertLess(scan.index('OpexBusDistrictJoinedPreflight(tile'),
                        scan.index('foreach (plannedTile in joined)'))
        preflight = body('bus_districts.nut', 'OpexBusDistrictJoinedPreflight')
        self.assertIn('OpexBusDistrictAxis(neighbour) != axis', preflight)
        self.assertIn('OpexRoad100CatchmentOverlaps(neighbour, excluded, coverage)', preflight)
        build = body('bus_districts.nut', 'OpexRoad1yBuildExtraStop')
        self.assertIn('AIStation.GetStationID(existing) != id', build)
        self.assertIn('OpexRoad100CatchmentOverlaps(tile, otherDistrict,', build)

    def test_district_identity_survives_both_validators(self):
        code = source('bus_districts_overrides.nut')
        self.assertEqual(code.count('!(ROAD1Y_PAX_SITES && ("road1yBusSite" in p.payload))'), 2)
        self.assertIn('"bus_district|"', body('bus_districts_overrides.nut', 'OpexAbandonedPairKey'))
        self.assertIn('OpexRoadBusSiteStillBuildable(candidate.siteA)',
                      body('bus_districts_overrides.nut', 'OpexRoadPlanPaxVoirie'))

    def test_no_squirrel_scope_or_reserved_identifier_hazards(self):
        code = source('bus_districts.nut')
        for word in ('clone', 'base', 'par', 'parent', 'static', 'yield'):
            self.assertNotRegex(code, r'\blocal\s+' + word + r'\b')
        self.assertNotIn('function(', code)
        self.assertNotIn('.find(', code)

    def test_projection_rebuilt_after_each_maintenance_before_veto(self):
        task = body('bus_districts_overrides.nut', 'OpexRoad1yRefleetSaved')
        self.assertEqual(task.count('delete this._saveProjection[line]'), 2)
        self.assertEqual(task.count('this._saveProjection[line] <- OpexSaveProjectLine(line)'), 2)
        self.assertLess(task.index('OpexSaveProjectLine(line)'), task.index('"expandBlocked"'))

    def test_saved_markers_enable_maintenance_without_construction(self):
        load = body('bus_districts_overrides.nut', 'OpexAI::_reconcileAfterLoad')
        self.assertIn('ROAD1Y_SAVED_STOPS = true', load)
        self.assertIn('("road1yExtraPending" in line)', load)
        self.assertIn('if (ROAD1Y_SAVED_STOPS) return OpexRoad1yRefleetSaved.call', source('task_road.nut'))
        self.assertIn('if (ROAD1Y_EXTRA_STOPS > 0) {', body('bus_districts_overrides.nut', 'OpexRoad1yRefleetSaved'))

    def test_pending_tiles_never_supply_capacity(self):
        code = body('bus_districts.nut', 'OpexRoad1yReconcileExtraStops')
        self.assertLess(code.index('tile == line.road1yExtraPending) continue'), code.index('append(tile)'))

    def test_live_filter_accepts_districts_and_refleet_restores_load_policy(self):
        self.assertIn('!(ROAD1Y_PAX_SITES && ("road1yBusSite" in project.payload))',
                      body('projects_selection.nut', 'OpexRoad100FilterLiveBusTownProjects'))
        code = body('builder_road.nut', 'OpexRoadRefleet')
        self.assertIn('isFreight || ROAD1Y_LOAD_ORDERS', code)
        self.assertIn('(ROAD1Y_LOAD_ORDERS && isFreight) ? (AIOrder.OF_UNLOAD | AIOrder.OF_NO_LOAD)', code)

    def test_isolated_fixes_default_off_and_loaded_once(self):
        settings = source('settings.nut')
        self.assertEqual(settings.count('GetSetting("road1y_bus_fixes")'), 1)
        self.assertIn("if (!road1yRoadOnly) ROAD1Y_BUS_FIXES = 0;", body('settings.nut', 'OpexLoadBusDistrictSettings'))
        self.assertIn('ROAD1Y_BUS_FIXES <- 0;', source('globals_pre.nut'))
        setting = source('info.nut').split('name = "road1y_bus_fixes",')[1].split('});')[0]
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(difficulty + '_value = 0', setting)

    def test_passenger_restriction_preserves_saved_freight_maintenance(self):
        code = body('bus_districts.nut', 'OpexRoad1yExtraStops')
        guard = code.index('(ROAD1Y_BUS_FIXES & 1)')
        self.assertLess(code.index('OpexRoad1yReconcileExtraStops(line)'), guard)
        self.assertLess(guard, code.index('OpexRoad1yBuildExtraStop('))
        self.assertIn('!AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)', code)
        self.assertNotIn('ROAD1Y_BUS_FIXES', body('bus_districts.nut', 'OpexRoad1yCleanupExtraStop'))

    def test_diversity_keeps_best_two_before_top40_and_distance_before_quote(self):
        code = body('bus_districts_overrides.nut', 'OpexRoad100SoloPaxCandidates')
        self.assertLess(code.index('ranked.sort('), code.index('(ROAD1Y_BUS_FIXES & 8)'))
        self.assertIn('if (count >= 2) continue;', code)
        self.assertLess(code.index('ranked = diverse;'), code.index('if (n > 40)'))
        self.assertIn('(ROAD1Y_BUS_FIXES & 4) != 0 && distance < 30', code)
        self.assertLess(code.index('distance < 30'), code.index('OpexMakeRoadCandidate('))
