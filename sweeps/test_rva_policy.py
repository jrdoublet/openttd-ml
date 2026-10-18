"""Static purchase-boundary proof, not an OpenTTD game or Squirrel compiler."""
from pathlib import Path
import json
import re
import unittest
from rva_demand import station_allocation

ROOT=Path(__file__).resolve().parents[1]
AI=ROOT/'ai/OpexAI'


class Policy(unittest.TestCase):
    def test_single_setting_off_at_all_difficulties_and_single_load(self):
        info=(AI/'info.nut').read_text()
        block=info.split('name = "rva_policy",')[1].split('});')[0]
        for difficulty in ('easy','medium','hard','custom'):
            self.assertRegex(block,rf'{difficulty}_value\s*=\s*0')
        self.assertIn('min_value = 0, max_value = 1',block)
        self.assertLessEqual(info.count('AddSetting('),80)
        names=re.findall(r'name\s*=\s*"(rva_[^"]+)"',info)
        self.assertEqual(names,['rva_policy'])
        self.assertEqual((AI/'settings.nut').read_text().count('GetSetting("rva_policy")'),1)

    def test_lazy_guard_precedes_all_real_spending_after_site_refresh(self):
        text=(AI/'builder_rail.nut').read_text().split('function OpexExecuteRailPlan(')[1]
        text=text.split('function OpexBuildLine(')[0]
        gate=text.index('if (RVA_POLICY == 1 && OpexRvaRejectLocalPurchase(candidate, plan))')
        self.assertGreater(gate,text.index('OpexQuoteRailCapital('))
        self.assertGreater(gate,text.index('OpexApplyRailActualCapital('))
        for token in ('AITile.DemolishTile(', 'AIRail.BuildRailStation(', 'OpexBuildTrains('):
            self.assertLess(gate,text.index(token))
        body=text[gate:text.index('local costs = AIAccounting();',gate)]
        self.assertIn('result.reason = "RVA_GAIN";',body)
        self.assertIn('return result;',body)

    def test_rejections_never_enter_geometry_failure_memory(self):
        text=(AI/'task_rail.nut').read_text()
        for signature in ('function OpexAI::_tryBuildRailProject(', 'function OpexAI::_consumeRailSearch('):
            part=text.split(signature)[1].split('\nfunction ')[0]
            self.assertLess(part.index('result.reason == "RVA_GAIN"'),part.index('this._recordRailAttempt('))
            self.assertIn('outcome = "rejected"',part)

    def test_purchase_witness_with_independent_station_allocation_contract(self):
        w=json.loads((ROOT/'sweeps/fixtures/rva_purchase_witness.json').read_text())
        c=w['reference_candidate'];local=w['local_inventory'];e=w['expected']
        production=local['town_production_month']*local['covered_producers_after_platform_clearance']/local['town_houses']
        allocation=station_allocation(production,[dict(station='new',owner=0,rating_raw=c['raw_station_rating'])])
        carried=int(min(c['monthly_capacity'],allocation['new']))
        gain=12*carried*c['income_per_unit']-c['running_annual']-c['amort_annual']
        self.assertEqual(carried,e['rva_carried_month']);self.assertEqual(gain,e['rva_gain_annual'])
        # Baseline candidate is admitted and affordable, not a negative candidate
        # which master would already reject before ever reaching this gate.
        original=int(min(c['monthly_capacity'],c['monthly']*c['raw_station_rating']/255))
        self.assertEqual(original,e['reference_carried_month'])
        self.assertGreater(12*original*c['income_per_unit']-c['running_annual']-c['amort_annual'],0)
        self.assertLess(c['capital'],c['budget']);self.assertLess(gain,0)
        source=(AI/'rva_policy.nut').read_text()
        self.assertIn('estimate != null && estimate.gain <= 0',source)

    def test_uncovered_keeps_reference_without_global_mode_year_gate(self):
        source=(AI/'rva_policy.nut').read_text()
        for token in ('!dist.manual','V207_RAIL_PAX_JOINED_STOPS','wagons2',
                      'V212_RAIL_PAX_REVENUE_PCT','coverage.HasItem(tile)',
                      'C67_SLACK_MIN','town_house', 'reference_fallback'):
            if token=='town_house':
                self.assertIn('estimated_house_prior_no_rivals',source)
            else:self.assertIn(token,source)
        self.assertNotRegex(source,r'\b(?:MODE_AIR|MODE_ROAD|MODE_WATER|OPEX_START_YEAR)\b')
        self.assertNotRegex(source,r'\b(?:candidate|plan)\.\w+\s*(?:<-|=(?!=))')
        self.assertNotRegex(source,r'\blocal\s+(?:clone|base|parent)\b')
