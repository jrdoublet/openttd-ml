"""B2 contracts: default path, homogeneous units, live map and save projection.

These checks do not compile Squirrel; the five-seed OFF/ON engine runs do.
"""
import json
import re
from pathlib import Path
import subprocess
import unittest

from test_v261_forum_behaviours import body, source
from road100_off_projection import _subtract_exact

ROOT = Path(__file__).resolve().parents[1]


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
                projected = complete_function(source('bus_districts_overrides.nut'), name)
                for edit in reversed(item['hunks']):
                    self.assertEqual(projected.count(edit['after']), 1)
                    projected = projected.replace(edit['after'], edit['before'], 1)
                self.assertEqual(projected, original)
                historical = subprocess.check_output(
                    ['git', 'show', '4354cafa:ai/OpexAI/' + item['file']], cwd=ROOT).decode()
                self.assertEqual(original, complete_function(historical, name))

    def test_lazy_class_methods_are_installed_before_instantiation(self):
        settings = source('settings.nut')
        loader = body('settings.nut', 'OpexLoadBusDistrictSettings')
        self.assertIn('require("bus_districts_overrides.nut")', loader)
        self.assertNotIn('bus_districts_overrides', body('settings.nut', 'OpexLoadSettings'))
        self.assertEqual(settings.count('GetSetting("road1y_pax_sites")'), 1)
        self.assertTrue(source('main.nut').rstrip().endswith('OpexLoadBusDistrictSettings();'))

    def test_reviewed_layer_reconstructs_exact_parent(self):
        edits = json.loads((ROOT / 'sweeps/fixtures/road100_bus_districts_hunks.json').read_text())
        for name, hunks in edits.items():
            with self.subTest(name=name):
                parent = subprocess.check_output(
                    ['git', 'show', '4354cafa:ai/OpexAI/' + name], cwd=ROOT).decode()
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
        task = body('bus_districts_overrides.nut', 'OpexAI::_refleetRoadLines')
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
