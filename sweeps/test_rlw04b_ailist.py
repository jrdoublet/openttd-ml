"""RLW-04b: source contracts for an opt-in, passive and bounded native scan."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class RLW04BContracts(unittest.TestCase):
    def test_probe_is_off_with_default_settings(self):
        self.assertIn('RLW04B_SHADOW <- false;', read('globals_pre.nut'))
        self.assertIn('RLW04B_SHADOW = OpexProbeEnabled(16777216);', read('settings.nut'))
        settings = read('info.nut')
        self.assertEqual(settings.count('name = "probes"'), 1)
        self.assertNotIn('name = "rlw04b', settings)
        self.assertIn('if (RLW04B_SHADOW) this._rlw04bStep();', read('main.nut'))
        self.assertIn('if (RLW04B_SHADOW) this._rlw04bStep();', read('probes.nut'))
        self.assertIn('require("rail_long_window_enumerator.nut");', read('main.nut'))

    def test_cargo_qualification_uses_physical_rail_time_and_newgrf_classes(self):
        code = read('rail_long_window_enumerator.nut')
        for token in ('OpexGetEpochRailProfile(catalog, cargo, 256)',
                      '256.0 * OpexDaysPerTile(profile.speed.tofloat(), 74.0)',
                      'AICargo.GetCargoIncome(cargo, 256, info.fast)',
                      'AICargo.GetCargoIncome(cargo, 256, info.slow)',
                      'info.ratioPm >= 800',
                      'AICargo.CC_PASSENGERS', 'AICargo.CC_MAIL',
                      'AICargo.GetTownEffect(cargo) == AICargo.TE_GOODS'):
            self.assertIn(token, code)
        self.assertNotRegex(code, r'AICargo\.\w+\(\s*\d+\s*[,)]')

    def test_one_source_per_slice_and_native_distance(self):
        code = read('rail_long_window_enumerator.nut')
        for token in ('AIIndustryList_CargoAccepting(u.cargo)',
                      'sinks.Valuate(AIIndustry.GetDistanceManhattanToTile, tile)',
                      'sinks.KeepBetweenValue(223, 289)',
                      'if (sinks.Count() > RLW04B_SOURCE_CAP)',
                      'OpexRLW04BSource(s, this._catalog)',
                      'RLW04B_SLICE_BUDGET', 's.overruns++'):
            self.assertIn(token, code)
        self.assertEqual(code.count('OpexRLW04BSource(s, this._catalog)'), 1)
        self.assertIn('this._catalog.industries[srcIndex].id', code)
        for legacy in ('RLW04_CELL', 'AIList.Sort(', 'OpexMakeCandidate(', 'OpexV276Publish('):
            self.assertNotIn(legacy, code)

    def test_no_construction_or_portfolio_publication(self):
        code = read('rail_long_window_enumerator.nut')
        for token in ('_projects', 'candidateGroups', 'BuildRail(', 'BuildVehicle(', 'FindPath('):
            # Comments may describe forbidden calls; only actual invocations matter.
            self.assertNotRegex(code, r'(?m)^\s*[^/\n]*' + re.escape(token))
        self.assertIn('s.stocked.len() < RLW04B_POOL_CAP', code)
        self.assertNotIn('rlw04b', read('persist.nut').lower())

    def test_logging_reports_completion_and_ops(self):
        code = read('rail_long_window_enumerator.nut')
        for token in ('RLW04B_CARGO', 'RLW04B_ENUM', '"done"', 'overruns=',
                      'total_ops=', 'max_ops=', 'pairs=', 'ratio_pm='):
            self.assertIn(token, code)


if __name__ == '__main__':
    unittest.main()
