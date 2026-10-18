"""E3 integration contracts, deliberately static: no game/NoAI compilation here."""
import re
import unittest
from test_v233_contracts import AI
from test_c45_subsidy_persistence import function_body


def body(file, signature):
    return function_body((AI / file).read_text(), signature)


class GraftContracts(unittest.TestCase):
    def test_graft_is_off_and_dependency_is_rejected_explicitly(self):
        info = (AI / 'info.nut').read_text().split('name = "v233_goods_graft"', 1)[1].split('});', 1)[0]
        for level in ('easy', 'medium', 'hard', 'custom'):
            self.assertIn(f'{level}_value = 0', info)
        settings = body('settings.nut', 'function OpexLoadSettings()')
        self.assertIn('if (V233_GOODS_GRAFT && !V233_PENDING_CONTINUE)', settings)
        self.assertIn('AILog.Warning("V233:', settings)
        self.assertIn('V233_GOODS_GRAFT = false;', settings)
        self.assertNotIn('V233_PENDING_CONTINUE = true', settings)
        scheduler = body('scheduler.nut', 'function OpexAI::_runNextTaskWithSlackLedger()')
        self.assertIn('if (V233_GOODS_GRAFT && this._catalog != null && (!V233_GOODS_CHAIN || MODE_RAIL))', scheduler)
        self.assertNotIn('if (V233_PENDING_CONTINUE', scheduler)

    def test_context_identity_and_factory_specific_capture(self):
        live = body('goods_v233.nut', 'function OpexV233JoinContextValid(context, cargo, source, coverage)')
        for token in ('AIStation.GetStationID(context.v233StationTile) != context.joinStationId',
                      'AIIndustry.GetLocation(context.v233FactoryId) != source',
                      'AICompany.IsMine', 'produced.HasItem(cargo)', 'AICargo.TE_GOODS'):
            self.assertIn(token, live)
        coverage = body('goods_v233.nut', 'function OpexV233FactoryCovered(platform, factory, cargo, coverage)')
        self.assertIn('AITileList_IndustryProducing(factory, coverage)', coverage)
        builder = body('builder_rail.nut', 'function OpexRailPlatformPlans(catalog, candidate)')
        self.assertIn('OpexV233FactoryCovered(p, candidate.v233FactoryId', builder)
        self.assertIn('candidate.strictJoin', builder.split('if (!joinB)', 1)[0])
        self.assertIn('if (strictOriginReuseJoin)', builder)

    def test_no_global_sitability_cache_forgery(self):
        candidate = body('candidates.nut', 'function OpexMakeCandidate(')
        self.assertIn('if (V233_GOODS_GRAFT && joinContext != null)', candidate)
        joint_branch = candidate.split('if (V233_GOODS_GRAFT && joinContext != null)', 1)[1].split('} else {', 1)[0]
        self.assertIn('OpexV233JoinContextValid', joint_branch)
        self.assertNotIn('OpexSitableCache', joint_branch)
        close = body('lines.nut', 'function OpexAI::_tooClose(candidate)')
        self.assertEqual(close.count('if (!v233Join && joinLineId'), 2)
        self.assertIn('v233Join && entry[0] == "A" && OpexLineStationId(line, lineEnd) == joinStationId', close)
        self.assertIn('v233Join && entry[0] == "A" && stationId == joinStationId', close)
        self.assertNotIn('v233Join && entry[0] == "B"', close)

    def test_generation_is_bounded_and_uses_only_ordinary_economics(self):
        generate = body('goods_v233.nut', 'function OpexAI::_v233GraftStep()')
        for token in ('n < 8', 'state.nearest.len() > 3', 'state.evaluate++',
                      'OpexMakeCandidate(', '"freight|"', '"|t"', 'outputKey in gen.seen'):
            self.assertIn(token, generate)
        self.assertEqual(generate.count('OpexMakeCandidate('), 1)
        self.assertNotIn('OpexReselectProjects(', generate)
        self.assertNotIn('predCarried', generate)
        for file in ('projects_models.nut', 'economy.nut'):
            source = (AI / file).read_text()
            if file == 'economy.nut':
                # Mode 5 must preserve its own mixed consist when the ordinary
                # builder reprices it. No chain bonus belongs in line economics.
                helper = body(file, 'function OpexV163CandidateSecondary(')
                source = source.replace(helper, '')
            self.assertNotIn('V233', source)
        selection = (AI / 'projects_selection.nut').read_text()
        self.assertIn('if (V233_GOODS_CHAIN && project.mode == "rail")', selection)
        publish = body('goods_v233.nut', 'function OpexAI::_v233Publish()')
        for token in ('OpexProjectFromCandidate(', 'OpexProjectRememberAll(',
                      'OpexProjectsRecountGroups(', 'OpexReselectProjects('):
            self.assertIn(token, publish)
        task = body('task_projects.nut', 'function OpexAI::_tryBuildProjects(year)')
        self.assertLess(task.index('this._v233Publish();'), task.index('for (local i = 0; i < this._projects.best.len(); i++)'))
        self.assertIn('this._v233PublishedGroups == this._projects.candidateGroups', publish)

    def test_search_completion_deposits_without_spending_and_ready_bypasses_slot(self):
        continuation = body('task_rail.nut', 'function OpexAI::_continueRailSearch()')
        deposit = continuation.split('if (V233_GOODS_GRAFT && OpexV233IsGraft(state.candidate) && plan.ok)', 1)[1].split('return;', 1)[0]
        self.assertIn('this._v233StorePlan(state.candidate, plan);', deposit)
        self.assertIn('this._railSearch = null;', deposit)
        self.assertNotIn('OpexBuildLine', deposit)
        consumer = body('task_projects.nut', 'function OpexAI::_consumeResumableRailAtPassStart(')
        self.assertLess(consumer.index('this._v233StorePlan'), consumer.index('this._consumeRailSearch'))
        attempt = body('task_rail.nut', 'function OpexAI::_tryBuildRailProject(')
        self.assertIn('searchBlocked && !c121PrepPlan && !v233Ready', attempt)
        self.assertIn('!c121PrepPlan && !v233Ready && builtCount > 0', attempt)
        self.assertIn('if (start.pending) return { outcome = "pending"', attempt)
        self.assertNotIn('if (v233Graft) return { outcome = "pending"', attempt)
        self.assertIn('this._revalidateRailStockPlan(candidate, candidate.railPlan)', attempt)

    def test_stock_limit_ttl_revalidation_and_cash_contracts(self):
        globals_text = (AI / 'globals_pre.nut').read_text()
        self.assertIn('const V233_PLAN_LIMIT = 4;', globals_text)
        self.assertIn('const V233_PLAN_TTL_DAYS = 90;', globals_text)
        stock = body('goods_v233.nut', 'function OpexAI::_v233StorePlan(candidate, plan)')
        self.assertIn('this._v233Plans.len() >= V233_PLAN_LIMIT', stock)
        validate = body('goods_v233.nut', 'function OpexAI::_v233PlanStep()')
        for token in ('now - entry.date >= V233_PLAN_TTL_DAYS', 'n < 16',
                      'OpexTestRailTrack(', 'OpexQuoteRailCapital(', '_v233WorldRevision()',
                      'plan.v233RankCapital <- candidate.capital'):
            self.assertIn(token, validate)
        # A stock plan is not a financial reservation or a build on search completion.
        self.assertNotIn('OpexBuildLine(', validate)
        task = body('task_projects.nut', 'function OpexAI::_tryBuildProjects(year)')
        slot = task.index('if (V233_PENDING_CONTINUE && project.mode == "rail"')
        cash = task.index('&& OpexProjectFinanceCapital(project) > OpexAvailableCapital()) continue;')
        kpass = task.index('local c121ChainAttempt = false;')
        self.assertLess(slot, kpass)
        self.assertLess(cash, kpass)

    def test_catalogue_and_equipment_changes_invalidate_cached_offers(self):
        revision = body('goods_v233.nut', 'function OpexAI::_v233WorldRevision()')
        for layer in ('lines', 'industries', 'towns', 'engines.rail'):
            self.assertIn(f'_c76GetLayerRevision("{layer}")', revision)
        live = body('goods_v233.nut', 'function OpexAI::_v233CandidateLive(candidate)')
        self.assertIn('candidate.v233Revision != work.revision', live)
        observer = body('goods_v233.nut', 'function OpexAI::_v233GoodsStep()')
        self.assertIn('work.revision != revision', observer)
        self.assertIn('this._v233Generation = null;', observer)

    def test_fail_before_spend_and_protected_rollback(self):
        for name in ('OpexExecuteRailPlan', 'OpexV190ExecuteRailPlan'):
            execute = body('builder_rail.nut', 'function ' + name + '(')
            self.assertLess(execute.index('OpexV233SpendAllowed'), execute.index('local costs = AIAccounting();'))
            self.assertIn('candidate.capital != plan.v233RankCapital', execute)
        guard = body('goods_v233.nut', 'function OpexV233SpendAllowed(')
        self.assertIn('AITileList_StationType(candidate.joinStationId, AIStation.STATION_TRAIN)', guard)
        self.assertIn('p.v233Protected <- protectedTiles', guard)
        rollback = body('builder_rail.nut', 'function OpexRollback(')
        self.assertEqual(rollback.count('v233Protected != null &&'), 3)
        secondary = body('builder_rail.nut', 'function OpexV190RollbackDoubleTrack(')
        self.assertIn('planA1.v233Protected', secondary)
        build = body('builder_rail.nut', 'function OpexBuildLine(')
        self.assertIn('&& !(V233_GOODS_GRAFT && OpexV233IsGraft(candidate))', build)

    def test_save_reload_loses_plans_and_keeps_shared_line_identity_when_off(self):
        save = body('persist.nut', 'function OpexAI::Save()')
        for banned in ('_v233Plans', '_v233Offers', '_v233Generation', '_v233GoodsWork'):
            self.assertNotIn(banned, save)
        load = body('persist.nut', 'function OpexAI::Load(version, data)')
        for transient in ('_v233Plans', '_v233Offers', '_v233Generation', '_v233GoodsWork'):
            self.assertIn(f'this.{transient} = null;', load)
        vehicles = body('lines.nut', 'function OpexLineVehicleIds(line, stationId)')
        self.assertIn('"v233SharedStationId" in line', vehicles)
        self.assertIn('OpexVehicleServesStation(v, other)', vehicles)
        self.assertNotIn('V233_GOODS_GRAFT', vehicles)  # lifecycle survives flags OFF
        scrap = body('task_report.nut', 'function OpexAI::_scrapDeadLines(year)')
        self.assertNotIn('RemoveRailStation', scrap)
        self.assertNotIn('DemolishTile', scrap)

    def test_no_reserved_identifiers_or_new_undeclared_methods(self):
        text = (AI / 'goods_v233.nut').read_text()
        self.assertNotRegex(text, r'\blocal\s+(?:clone|base|parent)\b')
        main = (AI / 'main.nut').read_text()
        for name in re.findall(r'function OpexAI::(\w+)\(', text):
            self.assertIn(f'function {name}(', main)


if __name__ == '__main__':
    unittest.main()
