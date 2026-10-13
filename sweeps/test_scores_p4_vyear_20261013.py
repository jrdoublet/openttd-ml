"""Contracts + economic reference fixtures for experimental P4 vehicle-year.

The fixtures model the algorithm, not the Squirrel VM. A real engine roundtrip
remains mandatory before attributing gameplay differences to the estimator.
"""

import copy
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / 'ai' / 'OpexAI'


def read(name):
    return (AI / name).read_text(encoding='utf-8')


def panel_entry(id_, engine, capacity, count=2, order_parts=None):
    if order_parts is None:
        order_parts = (11, 0, 22, 0) if count == 2 else tuple(x for i in range(count) for x in (11 + i, 0))
    assert len(order_parts) == 2 * count
    return [id_, engine, capacity, count, *order_parts]


def model_report(old, *, year, current, n0, predicted, amort=0, owned=True):
    """current[id] = (engine, capacity, order_count, age_days, profit, optional legs)."""
    snapshot = [panel_entry(id_, row[0], row[1], row[2], row[5] if len(row) > 5 else None)
                for id_, row in current.items()]
    observed = {item[0]: item for item in snapshot}
    previous = old is not None and old.get('version', 2) == 2 and old['reportYear'] == year - 1
    prior = old['snapshot'] if old is not None else []
    dirty = bool(old and (old.get('dirtyYear') == year - 1
                          or old.get('dirtyPriorYear') == year - 1))
    accepted = previous and bool(prior) and owned and n0 > 0 and predicted > 0 and not dirty
    sum_profit = 0
    if accepted:
        for entry in prior:
            id_ = entry[0]
            row = current.get(id_)
            if row is None or observed[id_] != entry or row[3] < 365 or row[1] <= 0:
                accepted = False
                break
            sum_profit += row[4]
    total = old['sumPm'] if old else 0
    count = old['count'] if old else 0
    if not accepted:
        total = 0
        count = 0
    if accepted:
        ratio = (sum_profit * n0 / len(prior) - amort) / predicted
        ratio = max(-.5, min(2.5, ratio))
        if count >= 20:
            count //= 2
            total //= 2
        count += 1
        total += int(ratio * 1000)
    return dict(version=2, reportYear=year, snapshot=snapshot, sumPm=total,
                count=count, valid=1 if accepted else 0,
                dirtyYear=old.get('dirtyYear', -1) if old else -1,
                dirtyPriorYear=old.get('dirtyPriorYear', -1) if old else -1)


def factor(lines, report_year, legacy=1.0):
    """No covered sample keeps legacy C70; otherwise neutral lines get one vote."""
    eligible = [l for l in lines if report_year - l['year'] >= 2
                and l['predicted'] > 0 and l['trains0'] > 0]
    ratio_sum = 2.0
    covered = 0
    for line in eligible:
        state = line.get('p4VYear')
        if state and state.get('version', 2) == 2 and state['reportYear'] == report_year and state['valid'] and state['count']:
            ratio_sum += state['sumPm'] / (1000 * state['count'])
            covered += 1
        else:
            ratio_sum += 1
    return ratio_sum / (len(eligible) + 2) if covered else legacy


def saved_projection_and_sidecar(lines, old_month_cache):
    """Simulation of Save(): cache for legacy lines, live sidecar for P4 state."""
    projection = [copy.deepcopy(old_month_cache.get(l['lineId'], l)) for l in lines]
    for l in projection:
        l.pop('p4VYear', None)
    sidecar = {l['lineId']: copy.deepcopy(l['p4VYear']) for l in lines if 'p4VYear' in l}
    return projection, sidecar


def load_projection(projection, sidecar):
    live = copy.deepcopy(projection)
    for line in live:
        line.pop('p4VYear', None)
        if line['lineId'] in sidecar:
            line['p4VYear'] = copy.deepcopy(sidecar[line['lineId']])
    return live


def valid_vyear_sidecar(state):
    """Python contract mirror of OpexP4VYearStateValid (not Squirrel execution)."""
    if not isinstance(state, dict) or state.get('version') != 2:
        return False
    if not isinstance(state.get('snapshot'), list):
        return False
    if any(type(state.get(k)) is not int for k in (
            'sumPm', 'count', 'reportYear', 'valid', 'dirtyYear', 'dirtyPriorYear')):
        return False
    count, total = state['count'], state['sumPm']
    if not 0 <= count <= 20 or not -500 * count <= total <= 2500 * count:
        return False
    if state['valid'] not in (0, 1) or min(state['dirtyYear'], state['dirtyPriorYear']) < -1:
        return False
    if state['valid'] == 1 and (count == 0 or not state['snapshot']):
        return False
    return all(isinstance(item, list) and len(item) >= 6 and
               type(item[3]) is int and item[3] > 0 and
               len(item) == 4 + 2 * item[3] and
               all(type(element) is int for element in item)
               for item in state['snapshot'])


class SourceContracts(unittest.TestCase):
    def test_flag_off_all_four_and_requires_full_save(self):
        info = read('info.nut').split('name = "score_c70_vyear_cohort"', 1)[1].split('});', 1)[0]
        shadow_info = read('info.nut').split('name = "score_c70_vyear_measure_shadow"', 1)[1].split('});', 1)[0]
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(f'{difficulty}_value = 0', info)
            self.assertIn(f'{difficulty}_value = 0', shadow_info)
        settings = read('settings.nut')
        self.assertIn('AIController.GetSetting("score_c70_vyear_cohort")', settings)
        self.assertIn('AIController.GetSetting("score_c70_vyear_measure_shadow")', settings)
        self.assertIn('&& !SCORE_C70_STABLE_COHORT && SAVE_FULL_STATE', settings)
        self.assertIn('SCORE_C70_VYEAR_MEASURE = SCORE_C70_VYEAR_COHORT || SCORE_C70_VYEAR_MEASURE_SHADOW;', settings)
        self.assertIn('SCORE_C70_VYEAR_COHORT <- false', read('globals_pre.nut'))
        self.assertIn('SCORE_C70_VYEAR_MEASURE_SHADOW <- false', read('globals_pre.nut'))

    def test_c70_c82_and_original_behavior_coexist(self):
        report = read('task_report.nut')
        self.assertIn('OpexC70C82AccumulateLine(line, year, profit, vehCount, c70Sums, c82Sums)', report)
        self.assertIn('OpexC70P4ObserveLine(line, year, vehicles, vehicleType, profit, vehCount, p4C70Sums)', report)
        self.assertIn('if (SCORE_C70_VYEAR_MEASURE)', report)
        self.assertIn('OpexC70VYearRecomputeFactors(this._lines, year)', report)
        self.assertIn('OpexC82RecomputeFactors(this._lines)', read('persist.nut'))

    def test_panel_all_incumbents_and_only_veteran_profit(self):
        report = read('task_report.nut')
        start = report.index('function OpexC70VYearObserveLine(')
        end = report.index('function OpexC82PublishEngineFactors(', start)
        body = report[start:end]
        for required in ('previous && prior.len() > 0 && owned',
                         '!(id in observed)', 'AIVehicle.GetAge(id) < dayFloor',
                         'observed[id][1] != entry[1]', 'observed[id][2] != entry[2]',
                         'observed[id][part] != entry[part]',
                         'AIOrder.GetOrderDestination(v, pos)',
                         'AIOrder.GetOrderFlags(v, pos)',
                         'AICargo.IsValidCargo(cargo)',
                         'veteranProfit += AIVehicle.GetProfitLastYear(id)',
                         'veteranProfit.tofloat() * n0 / prior.len() - amort'):
            self.assertIn(required, body)
        self.assertIn('line.mode != "road"', body)
        self.assertNotIn('profit.tofloat() * n0 / vehCount', body)
        self.assertIn('dirtyYear == year - 1 || dirtyPrior == year - 1', body)
        self.assertIn('if (!allIncumbents) { sumPm = 0; count = 0; }', body)

    def test_neutral_missing_attrition_regularizer_and_float_free_storage(self):
        model = read('projects_models.nut')
        start = model.index('function OpexC70VYearRecomputeFactors(')
        end = model.index('function OpexC82RecomputeFactors(', start)
        body = model[start:end]
        self.assertIn('acc[0] += 1.0', body)
        self.assertIn('acc[0] += state.sumPm.tofloat() / (1000.0 * state.count)', body)
        self.assertIn('(acc[0] + 2.0) / (acc[1] + 2).tofloat()', body)
        report = read('task_report.nut')
        self.assertIn('ratioPm = (ratio * 1000.0).tointeger()', report)
        self.assertIn('sumPm = sumPm, count = count, valid = allIncumbents ? 1 : 0', report)

    def test_save_avoids_stale_cache_and_float_and_load_before_settings(self):
        persistence = read('persist.nut')
        self.assertIn('function OpexSaveProjectLineVYear(line)', persistence)
        self.assertIn('if ("p4VYear" in projected) delete projected.p4VYear', persistence)
        self.assertIn('p4Adjust.rawset(line.lineId, line.p4VYear)', persistence)
        self.assertIn('if (p4Adjust != null) saveObj.p4Adjust <- p4Adjust', persistence)
        self.assertIn('this._reloadP4Adjust = ("p4Adjust" in data)', persistence)
        self.assertLess(persistence.index('this._reloadP4Adjust = ("p4Adjust" in data)'),
                        persistence.index('function OpexAI::_reconcileAfterLoad()'))
        self.assertIn('OpexC70VYearRecomputeFactors(this._lines, this._lastReportYear)', persistence)
        self.assertIn('function OpexP4VYearStateValid(state)', persistence)
        self.assertIn('if (!OpexP4VYearStateValid(state)) continue;', persistence)
        self.assertIn('entry.len() != 4 + 2 * entry[3]', persistence)
        self.assertIn('state.version != 2', persistence)
        self.assertIn('state.dirtyYear < -1', persistence)
        self.assertIn('state.sumPm < -500 * state.count', persistence)
        self.assertIn('_reloadP4Adjust = null;', read('main.nut'))

    def test_structural_events_are_marked_but_not_claimed_exhaustive(self):
        body = read('task_report.nut')
        self.assertIn('function OpexC70VYearMarkStructuralMutation(line)', body)
        self.assertIn('if (p4Found && SCORE_C70_VYEAR_MEASURE)', read('event_handlers.nut'))
        self.assertIn('OpexC70VYearMarkStructuralMutation(line)', read('air_fleet.nut'))
        self.assertIn('OpexC70VYearMarkStructuralMutation(line)', read('task_rail.nut'))
        self.assertIn('OpexC70VYearMarkStructuralMutation(ownerLine)', body)


class VehicleYearEconomics(unittest.TestCase):
    def test_expansion_uses_only_previous_year_incumbents(self):
        old = dict(reportYear=1972, snapshot=[panel_entry(1, 2, 100)], sumPm=0, count=0)
        current = {1: (2, 100, 2, 900, 200), 2: (2, 100, 2, 100, 5000)}
        updated = model_report(old, year=1973, current=current, n0=1, predicted=100)
        self.assertEqual((updated['valid'], updated['sumPm'], updated['count']), (1, 2000, 1))
        self.assertEqual(len(updated['snapshot']), 2)

    def test_lost_incumbent_cannot_turn_into_survivor_only_selection(self):
        old = dict(reportYear=1972, snapshot=[panel_entry(1, 2, 100), panel_entry(2, 2, 100)], sumPm=450, count=1)
        new = model_report(old, year=1973, current={1: (2, 100, 2, 900, 2000)},
                           n0=2, predicted=100)
        self.assertEqual(new['valid'], 0)
        self.assertEqual((new['sumPm'], new['count']), (0, 0))
        line = dict(year=1970, predicted=100, trains0=2, p4VYear=new)
        self.assertEqual(factor([line], 1973), 1.0)

    def test_refit_engine_order_and_young_vehicle_neutralize(self):
        baseline = dict(reportYear=1972, snapshot=[panel_entry(1, 2, 100)], sumPm=0, count=0)
        for changed in ((3, 100, 2, 900, 200), (2, 101, 2, 900, 200),
                        (2, 100, 3, 900, 200), (2, 100, 2, 30, 200)):
            with self.subTest(changed=changed):
                state = model_report(baseline, year=1973, current={1: changed},
                                     n0=1, predicted=100)
                self.assertEqual((state['valid'], state['count']), (0, 0))

    def test_same_order_count_but_different_destination_or_flags_is_rejected(self):
        initial = dict(version=2, reportYear=1972,
                       snapshot=[panel_entry(1, 2, 100)], sumPm=600, count=1)
        for legs in ((11, 0, 23, 0), (11, 0, 22, 4)):
            with self.subTest(legs=legs):
                revised = model_report(initial, year=1973,
                                       current={1: (2, 100, 2, 900, 300, legs)},
                                       n0=1, predicted=100)
                self.assertEqual((revised['valid'], revised['count'], revised['sumPm']), (0, 0, 0))

    def test_invalid_refit_resets_history_then_new_clean_year_relearns(self):
        original = dict(version=2, reportYear=1972,
                        snapshot=[panel_entry(1, 2, 100)], sumPm=1500, count=2)
        invalid = model_report(original, year=1973,
                               current={1: (2, 120, 2, 900, 200)}, n0=1, predicted=100)
        self.assertEqual((invalid['sumPm'], invalid['count'], invalid['valid']), (0, 0, 0))
        recovery = model_report(invalid, year=1974,
                                current={1: (2, 120, 2, 1250, 200)}, n0=1, predicted=100)
        self.assertEqual((recovery['sumPm'], recovery['count'], recovery['valid']), (2000, 1, 1))

    def test_no_covered_mode_preserves_legacy_factor_and_covered_neutrals_still_vote(self):
        unmeasured = [dict(year=1970, predicted=100, trains0=1) for _ in range(4)]
        self.assertEqual(factor(unmeasured, 1973, legacy=.75), .75)
        covered = dict(year=1970, predicted=100, trains0=1, p4VYear={
            'version': 2, 'reportYear': 1973, 'valid': 1, 'sumPm': 400, 'count': 1})
        self.assertAlmostEqual(factor(unmeasured + [covered], 1973, legacy=.75), (2 + 4 + .4)/7)

    def test_road_unattributable_is_neutral(self):
        old = dict(reportYear=1972, snapshot=[panel_entry(1, 2, 100)], sumPm=0, count=0)
        state = model_report(old, year=1973, current={1: (2, 100, 2, 900, 200)},
                             n0=1, predicted=100, owned=False)
        self.assertEqual(state['valid'], 0)

    def test_hidden_transient_mutation_marked_neutral_even_if_ids_match(self):
        old = dict(reportYear=1972, snapshot=[panel_entry(1, 2, 100)], sumPm=0,
                   count=0, dirtyYear=1972, dirtyPriorYear=-1)
        current = {1: (2, 100, 2, 900, 300)}
        rejected = model_report(old, year=1973, current=current, n0=1, predicted=100)
        self.assertEqual(rejected['valid'], 0)
        self.assertEqual(rejected['count'], 0)

    def test_missing_lines_count_as_neutral_prevent_survivor_bias(self):
        measured = dict(year=1970, predicted=100, trains0=1, p4VYear={
            'reportYear': 1973, 'valid': 1, 'sumPm': 400, 'count': 1})
        missing = [dict(year=1970, predicted=100, trains0=1) for _ in range(9)]
        self.assertAlmostEqual(factor([measured] + missing, 1973), (0.4 + 9 + 2)/12)
        self.assertAlmostEqual(factor([measured], 1973), (0.4 + 2)/3)

    def test_old_save_over_64_lines_and_float_state_are_exact_on_new_sidecar(self):
        current = []
        stale_cache = {}
        for i in range(90):
            current_state = dict(version=2, reportYear=1973, snapshot=[panel_entry(i, 9, 100)],
                                 sumPm=333 if i % 2 else 625, count=1, valid=1,
                                 dirtyYear=-1, dirtyPriorYear=-1)
            old_state = dict(version=2, reportYear=1972, snapshot=[],
                             sumPm=0, count=0, valid=0, dirtyYear=-1, dirtyPriorYear=-1)
            line = dict(lineId=i, year=1970, predicted=100.25,
                        trains0=1, p4VYear=current_state)
            current.append(line)
            stale_cache[i] = {**line, 'p4VYear': old_state}
        saved, sidecar = saved_projection_and_sidecar(current, stale_cache)
        self.assertEqual(len(saved), 90)
        self.assertTrue(all('p4VYear' not in x for x in saved))
        loaded = load_projection(saved, sidecar)
        self.assertEqual([l['p4VYear'] for l in loaded],
                         [l['p4VYear'] for l in current])
        self.assertEqual(factor(loaded, 1973), factor(current, 1973))
        self.assertTrue(all(isinstance(l['p4VYear']['sumPm'], int) for l in loaded))

    def test_old_save_without_sidecar_neutral_fallback(self):
        projection = [dict(lineId=i, year=1970, predicted=50, trains0=1,
                           p4VYear=dict(reportYear=1972, valid=1, sumPm=300, count=1))
                      for i in range(65)]
        loaded = load_projection(projection, {})
        self.assertEqual(factor(loaded, 1973), 1.0)

    def test_no_cumulative_int_overflow_under_20_sample_thinning(self):
        old = dict(reportYear=1972, snapshot=[panel_entry(1, 2, 100)], sumPm=50000, count=20)
        current = {1: (2, 100, 2, 900, 500)}
        new = model_report(old, year=1973, current=current, n0=1, predicted=100)
        self.assertEqual(new['count'], 11)
        self.assertEqual(new['sumPm'], 27500)

    def test_vyear_sidecar_rejects_corrupted_state_before_reload(self):
        valid = dict(version=2, reportYear=1973,
                     snapshot=[panel_entry(101, 7, 40, 2)],
                     sumPm=750, count=1, valid=1,
                     dirtyYear=-1, dirtyPriorYear=-1)
        self.assertTrue(valid_vyear_sidecar(valid))
        corruptions = [
            ('old schema', {'version': 1}),
            ('bad valid', {'valid': 2}),
            ('negative count', {'count': -1}),
            ('count exceeds bound', {'count': 21}),
            ('bad float', {'sumPm': 750.2}),
            ('ratio out of bounds', {'sumPm': 2501}),
            ('missing dirty', {'dirtyYear': None}),
            ('bad dirty', {'dirtyPriorYear': -2}),
            ('broken order pairs', {'snapshot': [[101, 7, 40, 2, 11, 0]]}),
            ('empty order', {'snapshot': [[101, 7, 40, 0]]}),
            ('invalid id type', {'snapshot': [["101", 7, 40, 2, 11, 0, 22, 0]]}),
        ]
        for label, changes in corruptions:
            with self.subTest(label=label):
                self.assertFalse(valid_vyear_sidecar({**valid, **changes}))


if __name__ == '__main__':
    unittest.main()
