"""Mode 5 contracts. No engine launch and no claim of Squirrel compilation."""
import itertools
import re
import unittest

from test_v233_contracts import AI
from test_v233b_exposure import body


def chain(name):
    return body('goods_v233chain.nut', 'function ' + name + '(')


class ChainContracts(unittest.TestCase):
    def test_secondary_repricing_guard_truth_table(self):
        # Evaluate the actual pure Squirrel guard, translating only its boolean
        # operators. This catches the original loss with V163=0 in both builders.
        helper = body('economy.nut', 'function OpexV163CandidateSecondary(')
        chain_expr = re.search(r'local chainInput = (.*?);', helper).group(1)
        refusal = re.search(r'if \((!V163_MULTI_CARGO.*?)\) return null;', helper, re.S).group(1)

        def boolean(expr, context):
            expr = expr.replace('&&', ' and ').replace('||', ' or ')
            expr = re.sub(r'!(?!=)', ' not ', expr).strip()
            return eval('(' + expr + ')', {'__builtins__': {}}, context)

        class Fields(dict):
            __getattr__ = dict.__getitem__

        for v163, mode5, marked, mail, kind in itertools.product(
                (False, True), (False, True), (None, False, True),
                (False, True), ('freight', 'pax')):
            candidate = Fields(kind=kind, cargo2=4, monthly2=80)
            if marked is not None:
                candidate['v233ChainInput'] = marked
            context = dict(candidate=candidate, V163_MULTI_CARGO=v163,
                           V233_GOODS_CHAIN=mode5, V207_RAIL_MAIL=mail)
            context['chainInput'] = boolean(chain_expr, context)
            with self.subTest(v163=v163, mode5=mode5, marked=marked, mail=mail, kind=kind):
                self.assertEqual(not boolean(refusal, context),
                                 v163 or (mode5 and marked is True) or (mail and kind == 'pax'))
        self.assertIn('!("cargo2" in candidate) || !("monthly2" in candidate)', helper)
        builder = (AI / 'builder_rail.nut').read_text()
        self.assertEqual(builder.count('OpexV163CandidateSecondary(candidate)'), 2)

    def test_mode_five_trace_exposes_offer_publication_and_silent_refusals(self):
        source = (AI / 'goods_v233chain.nut').read_text()
        for event in ('state=offer', 'state=published', 'state=unavailable'):
            self.assertIn(event, source)
        live = chain('OpexV233ChainInputLive')
        for reason in ('expired', 'industry_changed', 'origin_served',
                       'production_primary', 'production_secondary', 'abandoned_pair'):
            self.assertIn('"' + reason + '"', live)

    def test_mode_five_reuses_three_without_enabling_other_public_settings(self):
        info = (AI / 'info.nut').read_text()
        setting = info.split('name = "v233_goods_graft"')[1].split('});')[0]
        self.assertIn('max_value = 5', setting)
        self.assertLessEqual(info.count('AddSetting('), 76)
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(level + '_value = 0', setting)
        settings = (AI / 'settings.nut').read_text()
        self.assertIn('V233_GOODS_CHAIN = V233_GOODS_POLICY == 5;', settings)
        self.assertIn('if (V233_GOODS_CHAIN) V233_GOODS_POLICY = 3;', settings)
        self.assertIn('V233_GOODS_GRAFT && !V233_PENDING_CONTINUE', settings)
        self.assertNotRegex(settings, r'V163_MULTI_CARGO\s*=\s*true')

    def test_factory_api_and_dormant_production(self):
        factory = chain('OpexV233ChainFactory')
        for item in ('AIIndustryType.GetAcceptedCargo', 'AIIndustryType.GetProducedCargo',
                     'AIIndustryType.IsProcessingIndustry', 'AICargo.GetCargoLabel', '"GOOD"'):
            self.assertIn(item, factory)
        self.assertNotIn('GetLastMonthProduction', factory)
        self.assertNotIn('GetName', factory)
        source = (AI / 'goods_v233chain.nut').read_text()
        self.assertNotIn('AINewGRFList', source)  # no such class in NoAI 15

    def test_generator_reused_in_single_pair_slices_with_mode_gate(self):
        work = chain('OpexV233ChainStep')
        self.assertIn('!V233_GOODS_CHAIN || !MODE_RAIL', work)
        self.assertEqual(work.count('OpexFreightCandidates('), 1)
        self.assertIn('{ source = si, factory = state.factory.id }', work)
        self.assertIn('state.source++', work)
        self.assertIn('state.town++', work)
        self.assertNotIn('OpexMakeCandidate(', work)
        self.assertNotIn('OpexBuildLine(', work)
        generator = body('candidates.nut', 'function OpexFreightCandidates(')
        self.assertIn('si != chainSlice.source', generator)
        self.assertIn('industries[di].id != chainSlice.factory', generator)
        self.assertIn('hasTownSinks && chainSlice == null', generator)
        self.assertIn('(V163_MULTI_CARGO || chainSlice != null)', generator)

    def test_conversion_counts_carried_both_cargos_and_full_capital_once(self):
        work = chain('OpexV233ChainStep')
        for item in ('state.volume += c.carried;', 'state.volume += c.carried2;',
                     'state.profit += parts.profit; state.capital += parts.capital;',
                     'c.src in state.sources', 'cargo in state.covered',
                     'state.profit + downstream.parts.profit',
                     'state.capital + downstream.parts.capital'):
            self.assertIn(item, work)
        self.assertIn('label == "GRAI" || label == "LVST"', work)
        self.assertNotIn('GetLastMonthProduction(state.factory', work)
        parts = chain('OpexV233ChainParts')
        self.assertIn('OpexProjectFundProfit(project)', parts)
        self.assertIn('OpexProjectFinanceCapital(project)', parts)

    def test_option_is_separate_discounted_capped_and_full_chain_bounds_score(self):
        score = chain('OpexV233ChainScore')
        for item in ('v233OptionRepresentative', '3.79078677', '0.25', '1.21',
                     'c.v233GoodsCash * factor * a - c.v233GoodsCapital',
                     'c.v233GoodsCapital > kDec', 'project.fundScore * 0.10',
                     'totalCapital > kDec', 'score < chainScore ? score : chainScore'):
            self.assertIn(item, score)
        self.assertNotIn('project.profitAnnual =', score)
        self.assertNotIn('candidate.profitAnnual =', score)
        selection = (AI / 'projects_selection.nut').read_text()
        self.assertIn('if (V233_GOODS_CHAIN && project.mode == "rail")', selection)
        work = chain('OpexV233ChainStep')
        self.assertIn('c.v233OptionRepresentative <- i == 0;', work)

    def test_no_month_gap_and_train_gate_uses_captured_volume(self):
        volume = chain('OpexV233ChainVolume')
        self.assertIn('row.count != 3', volume)
        self.assertIn('row.lastMonth != OpexV233eMonth()', volume)
        self.assertIn('(row.q0 + row.q1 + row.q2) / 3', volume)
        train = chain('OpexV233ChainTrainReady')
        self.assertIn('monthly * candidate.stationRating / 100.0', train)
        self.assertIn('candidate.perTrain * candidate.tripsPerMonth', train)
        observer = body('goods_v233e.nut', 'function OpexV233eGoodsStep(')
        self.assertIn('(generated || V233_GOODS_CHAIN)', observer)
        self.assertIn('if (!V233_GOODS_CHAIN || generated) ai._v233Generation = null;', observer)

    def test_graft_requires_both_inputs_live_and_monthly_observation(self):
        fed = chain('OpexV233ChainFed')
        self.assertIn('OpexV233Support(line)', fed)
        self.assertIn('label == "GRAI" || label == "LVST"', fed)
        self.assertIn('line.cargo2', fed)
        live = chain('OpexV233ChainGraftLive')
        for item in ('ai._v233GoodsObservations', 'OpexV233ChainVolume(row) >= candidate.monthly',
                     'OpexV233ChainTrainReady(candidate, row)', 'OpexV233AirYieldAllows(candidate)'):
            self.assertIn(item, live)

    def test_best_town_within_current_bound_and_no_first_city_early_exit(self):
        work = chain('OpexV233ChainStep')
        self.assertIn('distance > OpexCatalogBounds(ai._catalog).railMax', work)
        self.assertIn('parts.profit / parts.capital > state.downstream.yieldValue', work)
        graft = body('goods_v233e.nut', 'function OpexV233eGraftStep(')
        self.assertIn('!V233_GOODS_CHAIN && row.cargo in ai._catalog.acceptors', graft)
        self.assertIn('OpexV233ChainTrainReady(candidate, state.row)', graft)
        self.assertIn('if (!V233_GOODS_CHAIN) state.evaluate = state.nearest.len();', graft)

    def test_air_floor_covers_chain_and_incremental_goods_investment(self):
        total = chain('OpexV233ChainYield')
        self.assertIn('capital = capital', total)
        self.assertIn('capitalIsActual = true', total)  # already financed sum
        self.assertIn('candidate.profitAnnual = profit / factor', total)
        self.assertIn('OpexV233AirYieldAllows(candidate)', total)
        spend = body('goods_v233.nut', 'function OpexV233SpendAllowed(')
        self.assertIn('V233_GOODS_CHAIN && !OpexV233AirYieldAllows(candidate)', spend)
        input_spend = chain('OpexV233ChainInputSpend')
        self.assertIn('candidate.v233ChainCapital - candidate.v233InitialCapital + own.capital', input_spend)

    def test_input_spend_guard_also_covers_resumable_path(self):
        spend = body('builder_rail.nut', 'function OpexExecuteRailPlan(')
        self.assertLess(spend.index('OpexV233ChainInputSpend(candidate)'), spend.index('budget.begin();'))
        record = body('task_rail.nut', 'function OpexAI::_recordRailAttempt(')
        self.assertLess(record.index('this._lines.append('), record.index('state=input_built'))
        self.assertIn('line.v233InputCapital <- result.actualCost', record)
        resume = body('task_rail.nut', 'function OpexAI::_consumeRailSearch(')
        self.assertIn('_recordRailAttempt(', resume)

    def test_unprofitable_requote_is_rejected_before_calibration(self):
        parts = chain('OpexV233ChainParts')
        self.assertLess(parts.index('project == null'), parts.index('OpexProjectFundProfit(project)'))
        spend = chain('OpexV233ChainInputSpend')
        self.assertIn('own.profit <= 0 || own.capital <= 0', spend)
        self.assertIn('OpexV233ChainInputPlan(candidate, plan, catalog.railCoverage)',
                      body('builder_rail.nut', 'function OpexExecuteRailPlan('))
        footprint = chain('OpexV233ChainInputPlan')
        self.assertIn('AITileList_IndustryAccepting(candidate.v233FactoryId, coverage)', footprint)
        self.assertIn('accepted.HasItem(candidate.cargo2)', footprint)

    def test_publication_replaces_duplicate_rail_pair_and_keeps_other_modes(self):
        publish = chain('OpexV233ChainPublish')
        self.assertIn('OpexProjectKeyFor(project)', publish)
        self.assertIn('if (group[i].mode == "rail") group.remove(i);', publish)
        self.assertIn('OpexV233ChainInputLive(ai, candidate)', publish)
        work = chain('OpexV233ChainStep')
        self.assertIn('offer.v233FactoryId == state.factory.id', work)
        self.assertIn('foreach (key in obsolete) delete ai._v233ChainOffers[key];', work)
        scheduler = (AI / 'scheduler.nut').read_text()
        self.assertIn('(!V233_GOODS_CHAIN || MODE_RAIL)', scheduler)

    def test_sites_are_searched_after_all_city_economics_and_in_yield_order(self):
        graft = body('goods_v233e.nut', 'function OpexV233eGraftStep(')
        self.assertIn('state.ranked[pos].value >= value', graft)
        self.assertIn('state.ranked[state.siteCursor++].candidate', graft)
        self.assertLess(graft.index('state.ranked.insert('), graft.index('OpexRailPlatformPlans('))
        self.assertIn('monthly = state.monthlyQuantity;', graft)
        self.assertIn('else state.siteCursor = state.ranked.len();', graft)

    def test_load_rebuilds_work_but_preserves_scalar_line_facts(self):
        persist = (AI / 'persist.nut').read_text()
        self.assertEqual(persist.count('this._v233ChainWork = null;'), 2)
        self.assertEqual(persist.count('this._v233ChainOffers = null;'), 2)
        codec = body('persist.nut', 'function OpexSaveProjectLine(')
        self.assertIn('clone line', codec)
        skip = persist.split('OPEX_SAVE_LINE_SKIP <- {')[1].split('};')[0]
        self.assertNotIn('v233Input', skip)
        self.assertNotIn('v233ChainFactory', skip)

    def test_telemetry_is_guarded_and_joins_realized_by_line(self):
        work = chain('OpexV233ChainStep')
        self.assertIn('if (DECISION_LOG) OpexDecide("V233_CHAIN"', work)
        for key in ('total_profit=', 'total_capital=', 'input_profit=', 'goods_profit=', 'goods_monthly='):
            self.assertIn(key, work)
        report = (AI / 'task_report.nut').read_text()
        self.assertIn('state=realized factory=', report)
        self.assertIn('" line=" + line.lineId', report)
        self.assertIn('" profit=" + profit', report)
        build = (AI / 'task_rail.nut').read_text()
        self.assertIn('policy=5 town=', build)
        self.assertIn('" wagons=" + result.wagons', build)

    def test_no_lock_reservation_or_nested_closure(self):
        source = (AI / 'goods_v233chain.nut').read_text()
        for item in ('Sleep(', '_activeGoodsChain', 'OpexCashReserve(', 'OF_TRANSFER', 'OpexExecuteRailPlan('):
            self.assertNotIn(item, source)
        self.assertNotRegex(source, r'=\s*function\s*\(')
        self.assertNotRegex(source, r'\blocal\s+(?:clone|base|yield)\b')


if __name__ == '__main__':
    unittest.main()
