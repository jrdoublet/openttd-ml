"""V233e contracts and real log excerpts; no Squirrel VM or OpenTTD launch."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from analyze_v233_sites import analyze_directory, analyze_sites
from test_v233b_exposure import body
from test_v233_contracts import AI

FIXTURES = Path(__file__).parent / 'fixtures'


def ebody(name):
    return body('goods_v233e.nut', 'function ' + name + '(')


class V233eContracts(unittest.TestCase):
    def test_mode_three_dispatch_does_not_edit_legacy_algorithms(self):
        frozen = json.loads((FIXTURES / 'v233e_legacy_contracts.json').read_text())
        dispatches = (
            'if (V233_GOODS_POLICY == 3) { OpexV233eGoodsStep(this); return; }',
            'if (V233_GOODS_POLICY == 3) { OpexV233eGraftStep(this); return; }',
            'if (V233_GOODS_POLICY == 3) return OpexV233eCandidateLive(this, candidate);',
            'if (V233_GOODS_POLICY == 3) return OpexV233ePlatformPlans(catalog, candidate, statsA, statsB);',
        )
        for name, expected in frozen['functions'].items():
            with self.subTest(name=name):
                code = body('goods_v233.nut', 'function ' + name + '(')
                for dispatch in dispatches:
                    code = code.replace(dispatch, '')
                code = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/', '', code)
                code = re.sub(r'\s+', '', code)
                self.assertEqual(hashlib.sha256(code.encode()).hexdigest(), expected)

    def test_setting_dependency_default_and_public_count(self):
        block = (AI / 'info.nut').read_text().split('name = "v233_goods_graft"')[1].split('});')[0]
        self.assertIn('max_value = 3', block)
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(difficulty + '_value = 0', block)
        self.assertLessEqual((AI / 'info.nut').read_text().count('AddSetting('), 76)
        self.assertIn('V233_GOODS_GRAFT && !V233_PENDING_CONTINUE', (AI / 'settings.nut').read_text())
        self.assertIn('require("goods_v233e.nut");', (AI / 'main.nut').read_text())

    def test_observer_keeps_cursor_across_month_and_revision_changes(self):
        observer = ebody('OpexV233eGoodsStep')
        self.assertIn('work.phase == "done" && work.month != month && generated', observer)
        self.assertIn('gen.cursor >= work.keys.len()', observer)
        self.assertIn('work != null && gen != null && gen.current == null', observer)
        self.assertNotIn('work.revision !=', observer)
        self.assertNotIn('month_coverage', observer)
        self.assertIn('lineLimit = ai._lines.len()', observer)
        self.assertIn('n < 8', observer)
        self.assertLess(observer.index('ai._v233GoodsObservations[key] <- row'),
                        observer.index('work.phase = "done"'))
        self.assertIn('quantity < 0', observer)
        self.assertNotIn('row.count == 3', observer)

    def test_all_secondary_outputs_are_discovered_by_type_api(self):
        observer = ebody('OpexV233eGoodsStep')
        self.assertIn('OpexV233Support(line)', observer)
        self.assertIn('AIIndustryType.GetProducedCargo(AIIndustry.GetIndustryType(support.factoryId))', observer)
        self.assertNotIn('TE_GOODS', observer)
        self.assertNotIn('OpexV233FactoryCovered(line.platformB', observer)
        generate = ebody('OpexV233eGraftStep')
        for item in ('AICargo.GetTownEffect(row.cargo)', 'AICargo.TE_NONE',
                     'ai._catalog.townAcceptors', 'ai._catalog.acceptors[row.cargo]',
                     'industryRows = ai._catalog.industries', 'state.industryRows['):
            self.assertIn(item, generate)

    def test_real_monthly_output_uses_existing_economic_admission(self):
        generate = ebody('OpexV233eGraftStep')
        self.assertIn('AIIndustry.GetLastMonthProduction(state.row.factoryId, state.row.cargo)', generate)
        self.assertIn('monthly <= 0', generate)
        self.assertEqual(generate.count('OpexMakeCandidate('), 1)
        self.assertNotIn('V233_GOODS_MIN_MONTHLY', generate)
        for banned in ('OpexApplyRailActualCapital', 'candidate.roi =', 'candidate.ratio =',
                       'OpexAvailableCapital', 'Sleep(', 'OpexBuildLine('):
            self.assertNotIn(banned, generate)
        ordinary = body('candidates.nut', 'function OpexMakeCandidate(')
        self.assertIn('economics.profitAnnual <= 0', ordinary)

    def test_liveness_ignores_other_lines_but_checks_own_contract(self):
        live = ebody('OpexV233eCandidateLive')
        for check in ('OpexV233eSupport(ai, candidate)', 'OpexV233JoinContextValid(',
                      'GetLastMonthProduction(candidate.v233FactoryId, candidate.cargo) < candidate.monthly',
                      'OpexV233eOutputAllocated(ai, candidate.src, candidate.cargo)',
                      'candidate.v233EngineRevision', 'AITown.IsValidTown',
                      'AIIndustry.IsValidIndustry(candidate.v233DstIndustry)',
                      'OpexAbandonedPairKey(candidate)', 'OpexV233SourceSiteKey('):
            self.assertIn(check, live)
        for unrelated in ('work.phase', 'work.month', 'work.revision', '_v233WorldRevision'):
            self.assertNotIn(unrelated, live)
        support = ebody('OpexV233eSupport')
        for check in ('line.lineId != context.joinLineId', 'support.stationId != context.joinStationId',
                      'support.factoryId != context.v233FactoryId', 'p.anchor != old.anchor',
                      'p.direction != old.direction', 'p.length != old.length'):
            self.assertIn(check, support)

    def test_stock_still_checks_track_quote_ttl_and_spending(self):
        stock = body('goods_v233.nut', 'function OpexAI::_v233PlanStep(')
        for check in ('V233_GOODS_POLICY != 3 && entry.revision !=', 'V233_PLAN_TTL_DAYS',
                      'OpexTestRailTrack', 'OpexQuoteRailCapital', 'OpexV131PlatformCargoOk'):
            self.assertIn(check, stock)
        spend = body('goods_v233.nut', 'function OpexV233SpendAllowed(')
        for check in ('V233_GOODS_POLICY == 2 || V233_GOODS_POLICY == 3',
                      'AIStation.STATION_ANY', 'OpexV233NewPlatform', 'tile in protectedTiles'):
            self.assertIn(check, spend)

    def test_alternative_towns_then_accepting_industries_without_three_town_cap(self):
        generate = ebody('OpexV233eGraftStep')
        self.assertIn('state.towns.len() + state.industries.len()', generate)
        self.assertIn('state.evaluate++', generate)
        self.assertNotIn('state.nearest.pop()', generate)
        self.assertIn('sink.id == state.row.factoryId', generate)
        self.assertIn('candidate.dstTown <- sink.town ? sink.id : -1', generate)
        self.assertIn('candidate.v233DstIndustry <- sink.town ? -1 : sink.id', generate)
        self.assertIn('state.evaluate = state.nearest.len()', generate)
        key = body('lines.nut', 'function OpexAbandonedPairKey(')
        self.assertIn('candidate.v233FactoryId + "|" + candidate.v233DstIndustry', key)
        self.assertIn('candidate.v233FactoryId + "|t" + candidate.dstTown', key)

    def test_expanded_source_captures_output_before_capping_site_plans(self):
        plans = ebody('OpexV233ePlatformPlans')
        self.assertIn('candidate.v233StationTile, length, candidate.cargo', plans)
        self.assertIn('statsA, candidate.joinStationId, candidate.v233FactoryId', plans)
        self.assertIn('OpexRailMinimumPlatformLength()', plans)
        finder = ebody('OpexV233eStationPlans')
        for check in ('station.station_spread', 'radius += coverage + length - 1',
                      'RAILTRACK_NE_SW', 'RAILTRACK_NW_SE', 'sign += 2',
                      'AIMap.DistanceManhattan', 'AIAccounting()', 'AITestMode()',
                      'AIRail.BuildRailStation(anchor, axis[0], 1, length, stationId)'):
            self.assertIn(check, finder)
        self.assertLess(finder.index('OpexV233FactoryCovered(p, sourceIndustry'), finder.index('plans.append(p)'))
        self.assertNotIn('LevelTiles(', finder)

    def test_exact_industrial_catchment_search_stock_and_spend(self):
        check = ebody('OpexV233eDestinationCargoOk')
        for item in ('AIIndustry.IsValidIndustry(industry)', 'AIIndustry.GetLocation(industry) != candidate.dst',
                     'GetAcceptedCargo', 'AITileList_IndustryAccepting(industry, coverage)',
                     'AITileList_StationType(p.stationId, AIStation.STATION_TRAIN)'):
            self.assertIn(item, check)
        self.assertNotIn('AIStation.STATION_ANY', check)
        validate = body('task_rail.nut', 'function OpexV131PlatformCargoOk(')
        self.assertIn('V233_GOODS_POLICY == 3 && !OpexV233eDestinationCargoOk', validate)
        self.assertIn('OpexV233AcceptingStation(p.stationId', validate)
        self.assertIn('OpexV233TownAcceptance(p, candidate.cargo, coverage) >= 8', validate)

    def test_logging_has_source_native_error_and_destination_identity(self):
        generate = ebody('OpexV233eGraftStep')
        for item in ('if (DECISION_LOG)', 'lastA=', 'errorA=', 'industry=', 'cargo=',
                     'clearA=', 'commandA=', 'best_acceptanceB='):
            self.assertIn(item, generate)

    def test_squirrel_has_no_closure_new_method_or_unverified_api_symbol(self):
        text = (AI / 'goods_v233e.nut').read_text()
        self.assertNotRegex(text, r'\blocal\s+(?:clone|base|parent)\b')
        self.assertNotRegex(text, r'=\s*function\s*\(')
        self.assertNotIn('function OpexAI::', text)
        self.assertNotIn('AITile.GetIndustryID', text)
        self.assertNotRegex(text, r'"\w+"\s*:')
        symbols = set(re.findall(r'\bAI\w+\.\w+', text))
        known = set(json.loads((FIXTURES / 'v233e_noai_symbols.json').read_text())['symbols'])
        self.assertEqual(symbols, known)


class V233eLogContracts(unittest.TestCase):
    def test_real_calendar_interruption_is_not_a_failed_production_threshold(self):
        # v233d_mode2_seed512_r0.log:11499: every row observed, phase not yet marked done.
        result = analyze_sites(['OPEX 1973-3-3 V233_DROP reason=month_coverage month=23678 '
                                'cause=calendar phase=observe indexed=22 observed=2 expected=2'])
        self.assertEqual(result['counts']['drop_month_coverage'], 1)
        drop = result['drops'][0]
        self.assertEqual((drop['observed'], drop['expected']), ('2', '2'))
        self.assertEqual(drop['cause'], 'calendar')

    def test_source_rejection_does_not_imply_failed_destination_command(self):
        # v233d_mode2_seed17_r0.log:14778.
        result = analyze_sites(['OPEX 1973-5-17 V233_GRAFT state=site_rejected factory=5 town=26 '
            'reason=SITEAB clearA=6 commandA=0 clearB=0 cargoB=0 commandB=0 tilesB=0 '
            'triedB=0 lastB=not_searched errorB=-1 best_acceptanceB=-1'])
        self.assertEqual(result['rejections'][0]['commandA'], '0')
        self.assertEqual(result['rejections'][0]['lastB'], 'not_searched')
        self.assertEqual(result['rejections'][0]['errorB'], '-1')

    def test_custom_pattern_reads_mode_three_and_counts_builds_deliveries_and_drops(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'v233e_mode3_seed42_r0.log').write_text(
                'OPEX 1971-1-1 V233_GRAFT state=result built=1 reason=OK error=0\n'
                'OPEX 1971-1-2 V233_DELIVERY state=first_observed_since_load factory=2\n'
                'OPEX 1971-1-3 V233_DROP reason=publication_not_live factory=2\n')
            result = analyze_directory(root, 'v233e_mode3_seed*_r0.log')
        self.assertEqual(result['seeds_built'], [42])
        self.assertEqual(result['seeds_delivered'], [42])
        self.assertEqual(result['totals']['drop_publication_not_live'], 1)


if __name__ == '__main__':
    unittest.main()
