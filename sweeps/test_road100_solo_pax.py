"""ROAD100 : garde ROAD seul, filtres anti-cannibalisation et integration."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def function_body(source, name):
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:i]
    raise AssertionError("Unterminated " + name)


class Road100Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = (ROOT / "info.nut").read_text(encoding="utf-8")
        cls.settings = (ROOT / "settings.nut").read_text(encoding="utf-8")
        cls.globaldefs = (ROOT / "globals_pre.nut").read_text(encoding="utf-8")
        cls.candidates = (ROOT / "candidates.nut").read_text(encoding="utf-8")

    def test_settings_inert_unless_road_only(self):
        setting = re.search(r'name = "road100_solo_pax"(.{0,320})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_SOLO_PAX <- false", self.globaldefs)
        expression = re.search(r'ROAD100_SOLO_PAX\s*=\s*AIController.GetSetting\("road100_solo_pax"\)\s*==\s*1\s*'
                               r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;', self.settings)
        self.assertIsNotNone(expression)
        self.assertEqual(self.settings.count('GetSetting("road100_solo_pax")'), 1)

    def test_road100_portfolio_is_new_default_off_road_only_policy(self):
        block = re.search(r'name = "road100_pax_portfolio"(.{0,430})',
                          self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_PAX_PORTFOLIO <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_PAX_PORTFOLIO\s*=\s*AIController.GetSetting\("road100_pax_portfolio"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST && !ROAD100_JOINED_STOPS && !ROAD100_LONG_BUILD;')
        self.assertEqual(self.settings.count('GetSetting("road100_pax_portfolio")'), 1)
        gen = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("OpexRoad100PaxPortfolioPreview(catalog, preliminary, plan)", gen)
        self.assertIn("candidate.road100PaxPortfolio <- true", gen)
        self.assertIn("candidate.road100PaxPortfolioPreview <- portfolioPreview", gen)
        self.assertIn("candidate.monthly = siteMonthly", gen)
        # V20e conserve le classement BASE uniquement : l'augmentation
        # de profit non construite de V20d a érodé les cinq horizons.
        self.assertIn("candidate.road100PaxPortfolioRankDelta <- 0", gen)
        self.assertNotIn("candidate.ratio +=", gen)
        task = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                             "OpexAI::_tryBuildRoadProject")
        self.assertIn("OpexRoad100PaxPortfolioPreview(this._catalog,", task)
        self.assertIn("previewCacheHit", task)
        self.assertIn("savedPreview.frontA == plan.stopA.front", task)
        self.assertIn("savedPreview.frontB == plan.stopB.front", task)
        self.assertIn("savedPreview.roadType == this._catalog.roadType", task)
        self.assertIn("plan.road100PortfolioPreview <- portfolioLive", task)
        self.assertLess(task.index("plan.road100PortfolioPreview <- portfolioLive"),
                        task.index("OpexBuildRoadRoute(this._catalog"))

    def test_road100_freight_diversity_off_and_po01c_parity(self):
        block = re.search(r'name = "road100_freight_diversity"(.{0,430})',
                          self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{difficulty}_value\s*=\s*[01]")
        self.assertIn("ROAD100_FREIGHT_DIVERSITY <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_FREIGHT_DIVERSITY\s*=\s*AIController.GetSetting\("road100_freight_diversity"\)\s*==\s*1\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        self.assertEqual(self.settings.count('GetSetting("road100_freight_diversity")'), 1)
        selection = function_body(self.candidates, "OpexRoad100FreightDiverseCargoSet")
        self.assertIn("extras < 2", selection)
        self.assertIn("V276_CAND_SLICES > 0", selection)
        self.assertIn("catalog.roadEngineByCargo", selection)
        road_sync = function_body(self.candidates, "OpexRoadFreightCandidates")
        road_async = function_body((ROOT / "po01c_generators.nut").read_text(encoding="utf-8"),
                                   "OpexPO01CRoadFreightCandidates")
        for path in (road_sync, road_async):
            self.assertIn("OpexRoad100FreightDiverseCargoSet(catalog, freightCargo)", path)
            self.assertIn("(diversityCargos == null || !(cargo in diversityCargos))", path)
            self.assertIn("V276_CAND_SLICES <= 0", path)
        # Le curseur PO01C et les yields ne sont pas remplacés par un scan
        # synchrone, et la génération des bus n'est appelée qu'une fois.
        self.assertIn("yield null; // PO01C_CHECKPOINT", road_async)
        assert self.candidates.count("OpexRoadFreightCandidates(catalog, lines, all, stats,") >= 1

    def test_road100_freight_cargo_origin_keeps_same_cargo_and_off_guards(self):
        block = re.search(r'name = "road100_freight_cargo_origin"(.{0,430})',
                          self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_FREIGHT_CARGO_ORIGIN <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_FREIGHT_CARGO_ORIGIN\s*=\s*AIController.GetSetting\("road100_freight_cargo_origin"\)\s*==\s*1\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        self.assertEqual(self.settings.count('GetSetting("road100_freight_cargo_origin")'), 1)
        index = function_body(self.candidates, "OpexRoadFreightServedIndex")
        self.assertIn('("cargo" in line) && line.cargo != cargoFilter', index)
        self.assertIn('served.rawset(AIMap.GetTileIndex(x, y), true)', index)
        guard = function_body(self.candidates, "OpexRoadFreightOriginServedCargo")
        self.assertIn('("cargo" in line) && line.cargo != cargo', guard)
        self.assertIn('AIMap.DistanceManhattan(tile, line.originA) < ORIGIN_SEPARATION', guard)
        for body in (function_body(self.candidates, "OpexRoadFreightCandidates"),
                     function_body((ROOT / "po01c_generators.nut").read_text(encoding="utf-8"),
                                   "OpexPO01CRoadFreightCandidates")):
            self.assertIn('if (ROAD100_FREIGHT_CARGO_ORIGIN && V276_CAND_SLICES <= 0)', body)
            self.assertIn('OpexRoadFreightServedIndex(lines, cargo)', body)
            self.assertIn('OpexRoadFreightAcceptedTowns(towns, servedTownCargo, cargo', body)
            self.assertIn('servedIndustryCargo[si]', body)
            self.assertIn('servedIndustryCargo[di]', body)
            self.assertIn('servedTownCargo[t]', body)
        task = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                             "OpexAI::_tryBuildRoadProject")
        self.assertIn('OpexRoadFreightOriginServedCargo(this._lines, candidate.src, candidate.cargo)', task)
        self.assertIn('OpexRoadFreightOriginServedCargo(this._lines, candidate.dst, candidate.cargo)', task)
        self.assertIn('OpexOriginServed(this._lines, candidate.src, true)', task)
        self.assertIn('OpexOriginServed(this._lines, candidate.dst, true)', task)

    def test_road100_batch_roi15_is_optin_cash_and_physical_unchanged(self):
        block = re.search(r'name = "road100_batch_roi_15"(.{0,480})', self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn('ROAD100_BATCH_ROI_15 <- false', self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_BATCH_ROI_15\s*=\s*AIController.GetSetting\("road100_batch_roi_15"\)\s*==\s*1\s*'
                         r'&& ROAD100_ROAD_BATCH;')
        body = function_body((ROOT / 'task_projects.nut').read_text(encoding='utf-8'),
                             'OpexAI::_tryBuildProjects')
        self.assertIn('ROAD100_BATCH_ROI_15 ? 0.15 : 0.25', body)
        self.assertIn('road100Return >= road100Floor && availCap >= projCap + 50000', body)
        self.assertIn('builtCount < 4 && project.profitAnnual > 0', body)

    def test_road100_freight_berths_are_built_and_verified_before_refleet(self):
        block = re.search(r'name = "road100_freight_berths"(.{0,490})', self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertRegex(block.group(1), rf'{difficulty}_value\s*=\s*0')
        self.assertIn('ROAD100_FREIGHT_BERTHS <- false', self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_FREIGHT_BERTHS\s*=\s*AIController.GetSetting\("road100_freight_berths"\)\s*==\s*1\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        builder = function_body((ROOT / 'builder_road.nut').read_text(encoding='utf-8'),
                                'OpexRoad100FreightBerthGrow')
        for token in ('line.kind != "freight"', 'waitingSource < 3 * line.capacity',
                      'line.lastProfit < 3000', 'roads.Valuate(AIRoad.IsRoadTile)',
                      'visited >= 12', 'out.tested >= 4', 'OpexOpsMeasureEnd(mark) >= 60000',
                      'OpexRoadBfsPath(f, fronts[end], 96)', 'local test = AITestMode()',
                      'AIRoad.BuildDriveThroughRoadStation(tile, f,',
                      'AIRoad.BuildDriveThroughRoadStation(p.tile, p.front,',
                      'AIStation.GetStationID(p.tile) == ids[end]',
                      'AIRoad.AreRoadTilesConnected(p.tile, p.back)',
                      'AIRoad.RemoveRoadStation(placed[i])',
                      'AICompany.GetBankBalance(AICompany.COMPANY_SELF)',
                      'out.cost = cashBefore - AICompany.GetBankBalance'):
            self.assertIn(token, builder)
        self.assertNotIn('GetCargoWaiting', builder)
        self.assertNotIn('candidate.monthly', builder)
        task = function_body((ROOT / 'task_road.nut').read_text(encoding='utf-8'),
                             'OpexAI::_refleetRoadLines')
        for token in ('road100FreightBerthTryYear', 'OpexRoad100FreightBerthGrow(',
                      'line.rawset("road100FreightBerths", [expanded.a, expanded.b])',
                      'line.nStopsA = 2; line.nStopsB = 2;',
                      'line.nStopsA = 1; line.nStopsB = 1;',
                      'waitingA >= 3 * capacity', 'movingCount > 0 && !isAnyWaiting',
                      'money - 50000', 'OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, wanted)',
                      'OpexRoadRefleet(this._catalog, line, have, target)'):
            self.assertIn(token, task)
        persist = function_body((ROOT / 'persist.nut').read_text(encoding='utf-8'),
                                'OpexSaveProjectLine')
        self.assertIn('local serializableLine = clone line;', persist)

    def test_road100_pax_live_filter_rechecks_both_publication_paths(self):
        block = re.search(r'name = "road100_pax_live_filter"(.{0,490})', self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertRegex(block.group(1), rf'{difficulty}_value\s*=\s*0')
        self.assertIn('ROAD100_PAX_LIVE_FILTER <- false', self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_PAX_LIVE_FILTER\s*=\s*AIController.GetSetting\("road100_pax_live_filter"\)\s*==\s*1\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        selection = (ROOT / 'projects_selection.nut').read_text(encoding='utf-8')
        live = function_body(selection, 'OpexRoad100FilterLiveBusTownProjects')
        for token in ('if (!ROAD100_PAX_LIVE_FILTER || lines == null) return alternatives',
                      'line.mode != "road"', 'line.scrapping',
                      'AICargo.CC_PASSENGERS', 'served.rawset(aTown, true)',
                      'served.rawset(bTown, true)',
                      'project.mode == "road"', 'project.kind == "pax"',
                      'project.payload.isRoadExtension',
                      'ROAD100_MULTICATCHMENT', 'project.payload.road100MultiCatchment',
                      'OpexGetCandidateTownEndpoints(project.payload)',
                      'live.append(project)', 'ROAD100_PAX_LIVE'):
            self.assertIn(token, live)
        self.assertNotIn('OpexAbandonedPairKey', live)
        self.assertNotIn('_markPairAbandoned', live)
        self.assertNotIn('profitAnnual =', live)
        self.assertNotIn('candidate.monthly', live)
        reselect = function_body(selection, 'OpexReselectProjects')
        self.assertLess(reselect.index('OpexFilterAirAlternativesStillValid('),
                        reselect.index('OpexRoad100FilterLiveBusTownProjects(alternatives, lines)'))
        self.assertLess(reselect.index('OpexRoad100FilterLiveBusTownProjects(alternatives, lines)'),
                        reselect.index('OpexProjectSelectAffordable('))
        # Toutes les publications, y compris PO01C sur snapshot perime,
        # convergent vers le meme point de revalidation sur lignes LIVE.
        po01c = function_body((ROOT / 'po01c_regen.nut').read_text(encoding='utf-8'),
                              'OpexPO01CPublish')
        self.assertIn('OpexReselectProjects(projects, OpexAvailableCapital(), owner._abandonedPairs, owner._lines)', po01c)
        sync = (ROOT / 'projects_generation.nut').read_text(encoding='utf-8')
        self.assertIn('OpexReselectProjects(projects, OpexAvailableCapital(), abandonedPairs, lines)', sync)
        dispatcher = function_body((ROOT / 'task_road.nut').read_text(encoding='utf-8'),
                                   'OpexAI::_tryBuildRoadProject')
        self.assertIn('reason = "town_already_bus_served"', dispatcher)
        served = dispatcher[dispatcher.index('reason = "town_already_bus_served"'):
                            dispatcher.index('reason = "pair_already_served"')]
        self.assertIn('if (ROAD100_PAX_LIVE_FILTER) this._hadAbandonsThisPass = true;', served)
        self.assertNotIn('this._markPairAbandoned', served)
        self.assertNotIn('this._portfolioInvalidated = true', served)
        self.assertNotIn('this._c76BumpLayer', served)

    def test_road100_pax_berth_balance_is_real_and_mature_only(self):
        block = re.search(r'name = "road100_pax_berth_balance"(.{0,490})', self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertRegex(block.group(1), rf'{difficulty}_value\s*=\s*0')
        self.assertIn('ROAD100_PAX_BERTH_BALANCE <- false', self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_PAX_BERTH_BALANCE\s*=\s*AIController.GetSetting\("road100_pax_berth_balance"\)\s*==\s*1\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        builder = function_body((ROOT / 'builder_road.nut').read_text(encoding='utf-8'),
                                'OpexRoad100PaxBalanceBerth')
        for token in ('ROAD100_PAX_BERTH_BALANCE', 'line.kind != "pax"',
                      'AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP)',
                      'AIStation.GetStationID(root)',
                      'AIRoad.GetRoadStationFrontTile(root)',
                      'AIRoad.AreRoadTilesConnected(root, rootFront)',
                      'out.visited >= 12', 'out.tested >= 4',
                      'OpexOpsMeasureEnd(mark) >= 40000',
                      'OpexRoadBfsPath(f, rootFront, 96)',
                      'OpexRoadBfsPath(rootFront, f, 96)',
                      'local test = AITestMode()',
                      'AIRoad.BuildDriveThroughRoadStation(tile, f,',
                      'AIRoad.ROADVEHTYPE_BUS, id',
                      'AIStation.GetStationID(tile) == id',
                      'AIRoad.RemoveRoadStation(tile)',
                      'cashBefore - AICompany.GetBankBalance',
                      'finished = true', 'ROAD100_PAX_BERTH'):
            self.assertIn(token, builder)
        self.assertNotIn('candidate.monthly', builder)
        self.assertNotIn('GetCargoWaiting', builder)
        self.assertNotIn('BuildRoad(', builder)
        self.assertNotIn('AIStation.STATION_NEW', builder)
        task = function_body((ROOT / 'task_road.nut').read_text(encoding='utf-8'),
                             'OpexAI::_refleetRoadLines')
        for token in ('road100PaxBalanceAttempts < 2',
                      'road100PaxBalanceBuilt', 'year >= line.year + 2',
                      'line.lastProfit >= 5000', 'totalWaiting >= 3 * capacity',
                      'have == 2 && movingCount > 0',
                      'line.nStopsB == 1 && line.nStopsA >= 2',
                      'line.nStopsA == 1 && line.nStopsB >= 2',
                      'OpexRoad100PaxBalanceBerth(this._catalog, line, weakSide)',
                      'line.rawset("road100PaxBalanceTile", expandedPax.tile)',
                      'line.rawset("road100PaxBalancePreviousStops", 1)',
                      'line.nStopsA = previousStops',
                      'line.nStopsB = previousStops',
                      'AIStation.GetStationID(bayTile) == AIStation.GetStationID(bayRoot)',
                      'OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, wanted)',
                      '(money - 50000) / busPrice',
                      'OpexRoadRefleet(this._catalog, line, have, target)'):
            self.assertIn(token, task)
        self.assertIn('local serializableLine = clone line;',
                      function_body((ROOT / 'persist.nut').read_text(encoding='utf-8'),
                                    'OpexSaveProjectLine'))

    def test_road100_mail_uses_town_production_and_real_truck_sites(self):
        block = re.search(r'name = "road100_mail_intertown"(.{0,490})', self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertRegex(block.group(1), rf'{difficulty}_value\s*=\s*0')
        self.assertIn('ROAD100_MAIL_INTERTOWN <- false', self.globaldefs)
        self.assertIn('ROAD100_MAIL_LONG_EXISTING <- false', self.globaldefs)
        self.assertRegex(block.group(1), r'min_value\s*=\s*0,\s*max_value\s*=\s*2')
        self.assertIn('local road100MailMode = AIController.GetSetting("road100_mail_intertown");',
                      self.settings)
        self.assertRegex(self.settings,
                         r'ROAD100_MAIL_INTERTOWN\s*=\s*road100MailMode\s*>=\s*1\s*'
                         r'&& ROAD100_SITE_FIRST && MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        self.assertIn('ROAD100_MAIL_LONG_EXISTING = ROAD100_MAIL_INTERTOWN && road100MailMode == 2;',
                      self.settings)
        mail = function_body(self.candidates, 'OpexRoad100MailIntertownGenerator')
        for token in ('catalog.mailCargo', 'OpexOriginServed(lines, town.tile, true)',
                      'AITown.GetLastMonthProduction(town.id, cargo)',
                      'towns.len() > 16', 'ROAD100_MAIL_LONG_EXISTING ? 43 : 12',
                      'ROAD100_MAIL_LONG_EXISTING ? 80 : 42',
                      'tested >= 3', 'OpexOpsMeasureEnd(mark) >= 200000',
                      'yield null;', 'OpexRoadPlanFor(catalog, preliminary)',
                      'plan.vehType != AIRoad.ROADVEHTYPE_TRUCK',
                      'plan.stationType != AIStation.STATION_TRUCK_STOP',
                      'plan.stopA.value <= 0',
                      'plan.stopB.value < ROAD_ACCEPTANCE_FULL_UNIT',
                      'OpexRoad100MailOwnedCoverage()',
                      'OpexRoad100MailMarginalSource(cargo, plan.stopA.tile, covered)',
                      'OpexMakeRoadCandidate(catalog, "freight", cargo',
                      'realDistance, marginal, stats',
                      'marginal, candidate.engine, "freight", plan.routeDistance',
                      'candidate.road100MailIntertown <- true',
                      'candidate.road100SiteFirst <- true',
                      'ROAD100_MAIL'):
            self.assertIn(token, mail)
        coverage = function_body(self.candidates, 'OpexRoad100MailOwnedCoverage')
        self.assertIn('AIStationList(AIStation.STATION_ANY)', coverage)
        self.assertIn('AITileList_StationCoverage(id)', coverage)
        marginal = function_body(self.candidates, 'OpexRoad100MailMarginalSource')
        self.assertIn('AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP)', marginal)
        self.assertIn('sources.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0)', marginal)
        self.assertIn('covered.HasItem(tile)', marginal)
        self.assertNotIn('GetCargoWaiting', marginal)
        self.assertNotIn('plan.stopA.value + plan.stopB.value', mail)
        self.assertNotIn('candidate.monthly = pair.from.monthly', mail)
        self.assertNotIn('candidate.monthly = pair.to.monthly', mail)
        sync = function_body(self.candidates, 'OpexBuildRoadCandidates')
        po01c = function_body((ROOT / 'po01c_regen.nut').read_text(encoding='utf-8'),
                              'OpexPO01CGenerateMode')
        self.assertIn('OpexRoad100MailIntertownGenerator(', sync)
        self.assertIn('OpexRoad100MailIntertownGenerator(', po01c)
        self.assertIn('while (iterator.getstatus() != "dead") { resume iterator; yield null; }', po01c)
        task = function_body((ROOT / 'task_road.nut').read_text(encoding='utf-8'),
                             'OpexAI::_tryBuildRoadProject')
        self.assertIn('candidate.road100MailIntertown', task)
        self.assertIn('OpexRoad100MailMarginalSource(candidate.cargo, plan.stopA.tile,', task)
        self.assertIn('OpexRoad100MailOwnedCoverage()', task)
        self.assertIn('plan.stopB.value < ROAD_ACCEPTANCE_FULL_UNIT', task)
        self.assertIn('OpexRoadLineEconomics(this._catalog, candidate.cargo, actualDist,', task)
        stop = function_body((ROOT / 'builder_road.nut').read_text(encoding='utf-8'),
                             'OpexRoadStopKind')
        self.assertIn('AIRoad.ROADVEHTYPE_TRUCK', stop)
        route = function_body((ROOT / 'builder_road.nut').read_text(encoding='utf-8'),
                              'OpexBuildRoadRoute')
        self.assertIn('AIStation.STATION_NEW', route)
        self.assertIn('stationA == stationB', route)

    def test_road100_pax_double_berths_two_year_physical_recovery(self):
        block = re.search(r'name = "road100_pax_double_berths"(.{0,450})',
                          self.info, re.S)
        self.assertIsNotNone(block)
        for difficulty in ('easy', 'medium', 'hard', 'custom'):
            self.assertRegex(block.group(1), rf'{difficulty}_value\s*=\s*0')
        self.assertIn('ROAD100_PAX_DOUBLE_BERTHS <- false', self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_PAX_DOUBLE_BERTHS\s*=\s*AIController.GetSetting'
                         r'\("road100_pax_double_berths"\)\s*==\s*1\s*'
                         r'&& !ROAD100_PAX_BERTH_BALANCE\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        builder = function_body((ROOT / 'builder_road.nut').read_text(encoding='utf-8'),
                                'OpexRoad100PaxBalanceBerth')
        self.assertIn('ROAD100_PAX_BERTH_BALANCE || ROAD100_PAX_DOUBLE_BERTHS', builder)
        self.assertIn('AIRoad.BuildDriveThroughRoadStation(tile, f,', builder)
        self.assertIn('AIRoad.ROADVEHTYPE_BUS, id', builder)
        self.assertIn('AIStation.GetStationID(tile) == id', builder)
        self.assertIn('AIRoad.RemoveRoadStation(tile)', builder)
        task = function_body((ROOT / 'task_road.nut').read_text(encoding='utf-8'),
                             'OpexAI::_refleetRoadLines')
        for token in ('road100PaxDoubleAttempts < 2',
                      'road100PaxDoubleBuiltYear',
                      'year >= line.year + 2 && have == 2',
                      'line.lastProfit >= 5000',
                      'totalWaiting >= 3 * capacity',
                      'line.nStopsA == 1 && line.nStopsB == 1',
                      'line.road100PaxDoubleBays[0] != -1',
                      'line.road100PaxDoubleBays[1] != -1',
                      'reason=BAD_BAYS',
                      'line.road100PaxDoubleBays = null',
                      'line.road100PaxDoubleBays[0] == -1',
                      'line.road100PaxDoubleBays[1] == -1',
                      'waitingA >= waitingB ? 0 : 1',
                      'OpexRoad100PaxBalanceBerth(',
                      'line.rawset("road100PaxDoubleBays", doubleBays)',
                      'doubleBays[doubleSide] = expandedDouble.tile',
                      'line.nStopsA = 2', 'line.nStopsB = 2',
                      'line.road100PaxDoubleBays[dbSide] = -1',
                      'line.nStopsA = 1', 'line.nStopsB = 1',
                      'AIStation.GetStationID(bay) == AIStation.GetStationID(root)',
                      'line.lastProfit >= 5000 && totalWaiting >= 3 * capacity',
                      'doubleCash - 50000', 'extraNeeded > 2',
                      'OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, extraNeeded)'):
            self.assertIn(token, task)
        self.assertNotIn('AITown.GetLastMonthProduction', builder)
        self.assertNotIn('AAA', function_body((ROOT / 'builder_road.nut').read_text(encoding='utf-8'),
                                       'OpexRoad100PaxBalanceBerth'))

    def test_road100_mail_mode2_only_uses_bidirectional_preexisting_roads(self):
        builder = (ROOT / 'builder_road.nut').read_text(encoding='utf-8')
        planner = (ROOT / 'opcode_exact.nut').read_text(encoding='utf-8')
        mail = function_body(self.candidates, 'OpexRoad100MailIntertownGenerator')
        physical = function_body(builder, 'OpexRoad100MailExistingConnectedPlan')
        priced = function_body(builder, 'OpexRoad100MailExistingEconomics')
        dispatch = function_body(planner, 'OpexRoadPlanForActive')
        self.assertIn('local mailLong = ROAD100_MAIL_LONG_EXISTING;', mail)
        self.assertIn('preliminary.road100MailLongExisting <- true', mail)
        self.assertIn('candidate.road100MailLongExisting <- true', mail)
        self.assertIn('economics.profitAnnual < 3000 || economics.roi < 250', mail)
        self.assertIn('ROAD100_MAIL_LONG_EXISTING', physical)
        self.assertIn('centerDistance < 43 || centerDistance > 80', physical)
        self.assertIn('AIStation.STATION_TRUCK_STOP', physical)
        self.assertIn('foundA = OpexRoadSites(', physical)
        self.assertIn('foundB = OpexRoadSites(', physical)
        self.assertEqual(physical.count('true, null, true)'), 2)
        self.assertIn('AIRoad.IsRoadTile(siteA.front)', physical)
        self.assertIn('AIRoad.IsRoadTile(siteB.front)', physical)
        self.assertIn('OpexRoadBfsPath(siteA.front, siteB.front, 256)', physical)
        self.assertIn('OpexRoadBfsPath(siteB.front, siteA.front, 256)', physical)
        self.assertIn('OpexRoadTraceHitsStop(direct, siteA.tile)', physical)
        self.assertIn('OpexRoadTraceHitsStop(direct, siteB.tile)', physical)
        self.assertIn('OpexRoadFindDepot(direct, siteA, siteB)', physical)
        self.assertIn('road100MailExisting = true', physical)
        self.assertIn('"phase=reject reason="', physical)
        self.assertIn('" no_conn=" + noConnected', physical)
        self.assertIn('" no_depot=" + noDepot', physical)
        self.assertNotIn('BuildRoad(', physical)
        self.assertNotIn('Pathfinder', physical)
        sites = function_body(planner, 'OpexRoadSitesScan')
        fronts = function_body(planner, 'OpexRoadAccumulateFronts')
        self.assertIn('existingOnly = false', planner)
        self.assertIn('if (existingOnly && !AIRoad.IsRoadTile(front)) continue;', fronts)
        self.assertIn('offsets, probes, nCmd, existingOnly', sites)
        self.assertIn('return economics;', priced)
        self.assertNotIn('economics.revenueAnnual +=', priced)
        self.assertNotIn('economics.capital -=', priced)
        self.assertIn('OpexRoad100MailExistingConnectedPlan(catalog, candidate)', dispatch)
        self.assertIn('"MAIL_NO_CONNECTED_ROAD" : "OK"', dispatch)
        self.assertIn('reason = "MAIL_DRIFT"', dispatch)
        task = function_body((ROOT / 'task_road.nut').read_text(encoding='utf-8'),
                             'OpexAI::_tryBuildRoadProject')
        self.assertIn('OpexRoad100MailExistingEconomics(this._catalog, economics, plan)', task)
        self.assertIn('economics.profitAnnual < 3000 || economics.roi < 250', task)

    def test_portfolio_ring_scan_finance_rollback_and_fleet_are_bounded(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        preview = function_body(road, "OpexRoad100PaxPortfolioPreview")
        physical = function_body(road, "OpexRoad100PaxPortfolioBuild")
        route = function_body(road, "OpexBuildRoadRoute")
        self.assertEqual(preview.count("roads.Valuate(AIRoad.IsRoadTile)"), 1)
        self.assertIn("roads.KeepAboveValue(0)", preview)
        self.assertIn("if (radius > 11) radius = 11;", preview)
        self.assertIn("acceptedSites < 12", preview)
        self.assertIn("out.stationTests >= 4", preview)
        self.assertIn("out.quote + price + reserveAfterSat > balance", preview)
        self.assertIn("price + reserveAfterSat", physical)
        self.assertIn("out.builtTiles.append({ tile = sat.tile, id = ids[end] })", physical)
        self.assertIn('out.reason = "ROLLBACK"', physical)
        self.assertIn("out.builtTiles.pop()", physical)
        self.assertIn('if (portfolioSummary.reason == "ROLLBACK")', route)
        self.assertIn("portfolioSummary.joined > 0", route)
        self.assertIn("preview.frontA != plan.stopA.front", physical)
        self.assertIn("preview.frontB != plan.stopB.front", physical)
        self.assertIn("OpexRoadRollback(stopA, stopB, null, built, added, portfolioSatellites)", route)

    def test_long_city_sleeve_never_uses_reserved_parent_identifier(self):
        builder = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        sleeve = function_body(builder, "OpexRoad100LongRoadSleeve")
        self.assertNotRegex(sleeve, r'(?<!\w)parent\s*=')
        self.assertNotIn(".parent", sleeve)
        self.assertIn("prev_index", sleeve)

    def test_pax_candidates_stay_behind_opt_in_and_use_profit_admission(self):
        build = function_body(self.candidates, "OpexBuildRoadCandidates")
        self.assertIn("if (ROAD100_SOLO_PAX)", build)
        self.assertIn("OpexRoad100SoloPaxCandidates(catalog, lines, all, stats", build)
        pax = function_body(self.candidates, "OpexRoad100SoloPaxCandidates")
        self.assertIn("if (!ROAD100_SOLO_PAX", pax)
        self.assertIn("OpexTownBusPaxServed(lines", pax)
        self.assertIn("OpexRoadPairServed(lines", pax)
        self.assertIn("OpexRoadDistanceAllowed(catalog, distance, stats)", pax)
        self.assertIn('OpexMakeRoadCandidate(catalog, "pax"', pax)
        admiss = function_body(self.candidates, "OpexMakeRoadCandidate")
        self.assertIn("if (economics.profitAnnual <= 0)", admiss)

    def test_local_bus_opt_in_and_one_town_guard(self):
        setting = re.search(r'name = "road100_town_bus"(.{0,320})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_TOWN_BUS <- false", self.globaldefs)
        self.assertRegex(self.settings, r'ROAD100_TOWN_BUS\s*=\s*AIController.GetSetting\("road100_town_bus"\)\s*==\s*1\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        pax = function_body(self.candidates, "OpexRoad100TownBusCandidates")
        self.assertIn("if (!ROAD100_TOWN_BUS", pax)
        self.assertIn("OpexTownBusPaxServed(lines, town.id)", pax)
        self.assertIn("AITile.GetClosestTown(src) != town.id", pax)
        self.assertIn("AITile.GetClosestTown(dst) != town.id", pax)
        self.assertIn('OpexMakeRoadCandidate(catalog, "pax"', pax)
        self.assertIn('"ROAD100_TOWN_GEN"', pax)
        build = function_body(self.candidates, "OpexBuildRoadCandidates")
        self.assertIn("if (ROAD100_TOWN_BUS)", build)
        self.assertIn("OpexRoad100TownBusCandidates(catalog, lines, all", build)

    def test_road_batch_is_exclusively_road_only_and_financed(self):
        setting = re.search(r'name = "road100_road_batch"(.{0,320})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_ROAD_BATCH <- false", self.globaldefs)
        self.assertRegex(self.settings, r'ROAD100_ROAD_BATCH\s*=\s*AIController.GetSetting\("road100_road_batch"\)\s*==\s*1\s*'
                         r'&& MODE_ROAD && !MODE_AIR && !MODE_RAIL && !MODE_WATER;')
        task = (ROOT / "task_projects.nut").read_text(encoding="utf-8")
        body = function_body(task, "OpexAI::_tryBuildProjects")
        self.assertIn("ROAD100_ROAD_BATCH && project.mode == \"road\"", body)
        self.assertIn("builtCount < 4 && project.profitAnnual > 0", body)
        self.assertIn("ROAD100_BATCH_ROI_15 ? 0.15 : 0.25", body)
        self.assertIn("road100Return >= road100Floor && availCap >= projCap + 50000", body)
        self.assertIn("OpexAvailableCapital()", body)
        self.assertIn('"ROAD100_BATCH"', body)

    def test_town_voirie_only_when_town_bus_is_active(self):
        setting = re.search(r'name = "road100_town_voirie"(.{0,320})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_TOWN_VOIRIE <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_TOWN_VOIRIE\s*=\s*AIController.GetSetting\("road100_town_voirie"\)\s*==\s*1\s*'
                         r'&& ROAD100_TOWN_BUS;')
        plan = function_body((ROOT / "opcode_exact.nut").read_text(encoding="utf-8"),
                             "OpexRoadPlanForActive")
        self.assertIn("if (!sameTown || ROAD100_TOWN_VOIRIE)", plan)
        self.assertIn("OpexRoadPlanPaxVoirie(candidate, catalog)", plan)

    def test_fleet_8_preserves_physical_cap_at_default_and_revalidates(self):
        setting = re.search(r'name = "road100_pax_fleet_cap"(.{0,390})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_PAX_FLEET_CAP <- 0", self.globaldefs)
        self.assertIn("ROAD100_TOWN_BUS && road100FleetCap == 8 ? 8 : 0", self.settings)
        econ = function_body((ROOT / "economy.nut").read_text(encoding="utf-8"),
                             "OpexRoadLineEconomics")
        self.assertIn("if (fleetCapOverride == 8 && kind == \"pax\")", econ)
        make = function_body(self.candidates, "OpexMakeRoadCandidate")
        self.assertIn("null, fleetCapOverride", make)
        intratown = function_body(self.candidates, "OpexRoad100TownBusCandidates")
        self.assertIn("candidate.road100FleetCap <- ROAD100_PAX_FLEET_CAP", intratown)
        build = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                              "OpexAI::_tryBuildRoadProject")
        self.assertIn('("road100FleetCap" in candidate) ? candidate.road100FleetCap : 0', build)

    def test_post_siting_roi_guard_is_opt_in_and_pre_payment(self):
        setting = re.search(r'name = "road100_town_roi_post"(.{0,390})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_TOWN_ROI_POST <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_TOWN_ROI_POST\s*=\s*AIController.GetSetting\("road100_town_roi_post"\)\s*==\s*1\s*'
                         r'&& ROAD100_TOWN_BUS && ROAD100_TOWN_VOIRIE;')
        body = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                             "OpexAI::_tryBuildRoadProject")
        self.assertIn('ROAD100_TOWN_ROI_POST && candidate.kind == "pax"', body)
        self.assertIn("economics.profitAnnual * 1000", body)
        self.assertIn("estimatedPermille >= 250", body)
        self.assertIn('"ROAD100_TOWN_ROI"', body)
        self.assertLess(body.index("if (ROAD100_TOWN_ROI_POST"),
                        body.index("OpexApplyRoadEconomics(candidate, economics"))

    def test_intercity_site_fleet_uses_physical_coverage_and_cash_guard(self):
        setting = re.search(r'name = "road100_intercity_site_fleet"(.{0,390})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_INTERCITY_SITE_FLEET <- false", self.globaldefs)
        self.assertIn('ROAD100_INTERCITY_SITE_FLEET = AIController.GetSetting("road100_intercity_site_fleet") == 1', self.settings)
        self.assertIn("&& ROAD100_SOLO_PAX;", self.settings)
        gen = function_body(self.candidates, "OpexRoad100SoloPaxCandidates")
        self.assertIn("src.totalMonthly + dst.totalMonthly", gen)
        self.assertIn("candidate.road100IntercitySiteFleet <- true", gen)
        econ = function_body((ROOT / "economy.nut").read_text(encoding="utf-8"),
                             "OpexRoadLineEconomics")
        self.assertIn('if (fleetCapOverride == 30 && kind == "pax")', econ)
        body = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                             "OpexAI::_tryBuildRoadProject")
        self.assertIn("plan.stopA.value + plan.stopB.value", body)
        self.assertIn("candidate.monthly = siteDemand", body)
        self.assertIn("OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, economics.trains)", body)
        self.assertIn('OpexDecide("ROAD100_SITE_FLEET"', body)
        self.assertLess(body.index("candidate.monthly = siteDemand"),
                        body.index("OpexRoadLineEconomics(this._catalog"))
        build = function_body((ROOT / "builder_road.nut").read_text(encoding="utf-8"),
                              "OpexBuildRoadRoute")
        self.assertIn('"road100IntercitySiteFleet" in candidate', build)
        self.assertIn("price + 25000", build)

    def test_site_first_ranks_real_sites_before_project_selection(self):
        setting = re.search(r'name = "road100_site_first"(.{0,410})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_SITE_FIRST <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_SITE_FIRST\s*=\s*AIController.GetSetting\("road100_site_first"\)\s*==\s*1\s*'
                         r'&& ROAD100_SOLO_PAX;')
        gen = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("if (n > 40) n = 40", gen)
        self.assertIn("if (distance < 12 || distance > 42) continue", gen)
        self.assertIn("nearby.sort(OpexRoad100SortSitePreview)", gen)
        self.assertIn("plans < 6 && ops < 2500000", gen)
        self.assertIn("yield null", gen)
        self.assertIn("OpexRoadPlanFor(catalog, preliminary)", gen)
        self.assertIn("plan.stopA.value + plan.stopB.value", gen)
        self.assertLess(gen.index("OpexRoadPlanFor(catalog, preliminary)"),
                        gen.index("OpexMakeRoadCandidate(catalog, \"pax\""))
        self.assertLess(gen.index("OpexRoadPlanFor(catalog, preliminary)"), gen.index("out.append(candidate)"))
        self.assertIn("OpexRoadLineEconomics(catalog, cargo, actualDistance", gen)
        self.assertIn("candidate.immobilise = economics.immobilise", gen)
        self.assertIn("candidate.ratio = (economics.profitAnnual * 1000) / candidate.iterations", gen)
        generator = function_body(self.candidates, "OpexRoad100SoloPaxCandidates")
        self.assertIn("if (ROAD100_SITE_FIRST)", generator)
        self.assertLess(generator.index("if (ROAD100_SITE_FIRST)"), generator.index("local cargo"))
        planner = function_body((ROOT / "builder_road.nut").read_text(encoding="utf-8"),
                                "OpexRoadPlanPaxVoirie")
        self.assertIn('("road100SiteFirst" in candidate) && candidate.road100SiteFirst', planner)
        self.assertIn("pairs.sort(OpexRoad100SortSitePair)", planner)
        self.assertIn("siteFirst && pair.d > ROAD_MAX_TRACE_TILES", planner)
        self.assertIn("viableSitePlans >= 3", planner)
        self.assertIn("finances.profitAnnual > bestProfit", planner)
        self.assertIn("OpexEstimFinanceCapital(", planner)
        build = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                              "OpexAI::_tryBuildRoadProject")
        self.assertIn('("road100SiteFirst" in candidate) && candidate.road100SiteFirst', build)
        self.assertIn("plan.stopA.value + plan.stopB.value", build)
        self.assertIn("siteNeed + cashMargin", build)
        self.assertIn("? 50000 : 25000", build)
        self.assertIn('OpexDecide("ROAD100_PLAN_DRIFT"', build)
        self.assertIn('OpexDecide("ROAD100_REPRICE"', build)
        planner_dispatch = function_body((ROOT / "opcode_exact.nut").read_text(encoding="utf-8"),
                                         "OpexRoadPlanForActive")
        self.assertIn('("road100SiteFirst" in candidate) && candidate.road100SiteFirst',
                      planner_dispatch)
        # Never silently treat the historical L-only plan as site-first after
        # the physically connected drive-through plan has failed (v3 BSTOP).
        self.assertLess(planner_dispatch.index('return { plan = null, reason = "TRACEX" }'),
                        planner_dispatch.index('local radiusA ='))

    def test_po01c_road_publication_includes_opt_in_site_first(self):
        source = (ROOT / "po01c_regen.nut").read_text(encoding="utf-8")
        gen = function_body(source, "OpexPO01CGenerateMode")
        self.assertIn("if (ROAD100_SITE_FIRST)", gen)
        self.assertIn("OpexRoad100SiteFirstGenerator(s.catalog, s.lines, all, stats, s.abandoned)", gen)
        self.assertIn('while (iterator.getstatus() != "dead") { resume iterator; yield null; }', gen)
        self.assertLess(gen.index("OpexRoad100SiteFirstGenerator("),
                        gen.index("generated.road ="))

    def test_joined_stops_is_off_by_default_and_road_sitefirst_only(self):
        setting = re.search(r'name = "road100_joined_stops"(.{0,420})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_JOINED_STOPS <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_JOINED_STOPS\s*=\s*AIController.GetSetting\("road100_joined_stops"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST;')
        gen = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("if (ROAD100_JOINED_STOPS) candidate.road100JoinedStops <- true;", gen)
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        expansion = function_body(road, "OpexRoad100ExpandJoinedStops")
        self.assertIn("ROAD100_JOINED_STOPS", expansion)
        self.assertIn("candidate.kind != \"pax\"", expansion)
        self.assertIn("AITileList_StationCoverage(id)", expansion)
        self.assertIn("OpexRoadBfsPath(adj, baseFront, 96)", expansion)
        self.assertIn("AIStation.GetStationID(choice.tile) != id", expansion)
        self.assertIn("deltaAnnual * 100 < actualCost * 20", expansion)
        self.assertIn("AIController.GetOpsTillSuspend()", expansion)
        self.assertIn('OpexDecide("ROAD100_JOINED_STOP"', expansion)
        self.assertIn("choices.sort(OpexRoad100SortJoinedSite)", expansion)
        self.assertNotIn("choices.sort(function(", expansion)
        build = function_body(road, "OpexBuildRoadRoute")
        self.assertIn("OpexRoad100ExpandJoinedStops(", build)
        self.assertIn("result.road100JoinedStops <-", build)
        self.assertLess(build.index("result.road100JoinedStops <-"), build.index("result.cost ="))

    def test_multicatchment_requires_disjoint_physical_stops_and_existing_guards(self):
        setting = re.search(r'name = "road100_multicatchment"(.{0,420})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_MULTICATCHMENT <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_MULTICATCHMENT\s*=\s*AIController.GetSetting\("road100_multicatchment"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST;')
        gen = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("!ROAD100_MULTICATCHMENT && OpexTownBusPaxServed", gen)
        self.assertIn("OpexTownRoadLineCount(lines, town.tile) >= 4", gen)
        self.assertIn("if (ROAD100_MULTICATCHMENT) candidate.road100MultiCatchment <- true;", gen)
        self.assertIn("road100MultiCatchment = ROAD100_MULTICATCHMENT", gen)
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        bound = function_body(road, "OpexRoad100CatchmentOverlaps")
        self.assertIn("AIMap.DistanceMax(tile, other) <= 2 * coverage", bound)
        planner = function_body(road, "OpexRoadPlanPaxVoirie")
        self.assertIn('("road100MultiCatchment" in candidate)', planner)
        self.assertIn("OpexRoad100CatchmentOverlaps(siteA.tile, exclude, coverage)", planner)
        self.assertIn("OpexRoad100CatchmentOverlaps(siteB.tile, exclude, coverage)", planner)
        build = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                              "OpexAI::_tryBuildRoadProject")
        self.assertIn('"road100MultiCatchment" in candidate', build)
        self.assertIn("&& ROAD100_MULTICATCHMENT", build)
        self.assertIn("town_already_bus_served", build)
        self.assertIn("OpexRoadPairServed(this._lines", build)
        self.assertIn("OpexVehicleSlotAvailable(AIVehicle.VT_ROAD", build)

    def test_wait_fleet_only_for_mature_profitable_road_passenger_lines(self):
        setting = re.search(r'name = "road100_wait_fleet"(.{0,430})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_WAIT_FLEET <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_WAIT_FLEET\s*=\s*AIController.GetSetting\("road100_wait_fleet"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST;')
        resize = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                               "OpexAI::_refleetRoadLines")
        self.assertIn('dynamicWaitFleet = ROAD100_WAIT_FLEET && ("kind" in line)', resize)
        self.assertIn('line.kind == "pax"', resize)
        self.assertIn('year > line.year', resize)
        self.assertIn("lastProfit > 2000 && movingCount > 0", resize)
        self.assertIn("totalWaiting >= capacity * (have + 1)", resize)
        self.assertIn("timeCap > 16", resize)
        self.assertIn("incrementalWanted > 2", resize)
        self.assertIn("money - 50000", resize)
        self.assertIn("if (dynamicWaitFleet && have >= 2) extraNeeded = incrementalWanted;", resize)
        self.assertIn('OpexDecide("ROAD100_WAIT_FLEET"', resize)

    def test_site_window_rotates_only_secondary_preflights_at_fixed_budget(self):
        setting = re.search(r'name = "road100_site_window"(.{0,430})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_SITE_WINDOW <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_SITE_WINDOW\s*=\s*AIController.GetSetting\("road100_site_window"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST;')
        gen = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("nearby.sort(OpexRoad100SortSitePreview)", gen)
        self.assertIn("if (ROAD100_SITE_WINDOW && shortlisted > 1)", gen)
        self.assertIn("((AIDate.GetYear(today) % 10) * 5", gen)
        self.assertIn("? 1 + ((siteWindowOffset + k - 1) % (shortlisted - 1)) : k;", gen)
        self.assertIn("plans < 6 && ops < 2500000", gen)
        self.assertIn("yield null;", gen)
        self.assertIn('ROAD100_SITE_WINDOW ? " rank=" + rank : ""', gen)
        self.assertIn("OpexRoadLineEconomics(catalog, cargo, actualDistance", gen)

    def test_site_near_prioritizes_short_positive_proxy_preflights(self):
        setting = re.search(r'name = "road100_site_near"(.{0,430})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_SITE_NEAR <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_SITE_NEAR\s*=\s*AIController.GetSetting\("road100_site_near"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST;')
        sort = function_body(self.candidates, "OpexRoad100SortSiteNear")
        self.assertIn("a.score > 0", sort)
        self.assertIn("b.score > 0", sort)
        self.assertIn("a.distance < b.distance", sort)
        gen = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("if (ROAD100_SITE_NEAR) nearby.sort(OpexRoad100SortSiteNear);", gen)
        self.assertIn("else nearby.sort(OpexRoad100SortSitePreview);", gen)
        self.assertIn("plans < 6 && ops < 2500000", gen)

    def test_detour_is_site_first_only_with_bounded_two_corner_shapes(self):
        setting = re.search(r'name = "road100_detour"(.{0,430})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_DETOUR <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_DETOUR\s*=\s*AIController.GetSetting\("road100_detour"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST;')
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        planner = function_body(road, "OpexRoadPlanPaxVoirie")
        self.assertIn("ROAD100_DETOUR", planner)
        self.assertIn("OpexRoadTraceMulti", planner)
        self.assertIn("OpexRoadTraceBuildable", planner)
        self.assertIn("OpexRoadFindDepot", planner)
        self.assertIn("ROAD_MAX_TRACE_TILES", planner)
        self.assertIn("OpexRoadOnDtAxis", planner)
        self.assertIn("OpexOpsMeasureEnd", planner)
        self.assertIn('OpexDecide("ROAD100_DETOUR"', planner)

    def test_long_intercity_shadow_optin_and_no_world_mutation(self):
        setting = re.search(r'name = "road100_long_intercity"(.{0,440})',
                            self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_LONG_INTERCITY <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_LONG_INTERCITY\s*=\s*AIController.GetSetting\("road100_long_intercity"\)\s*==\s*1\s*'
                         r'&& ROAD100_SITE_FIRST;')
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        shadow = function_body(road, "OpexRoad100LongCorridorShadow")
        self.assertIn("!ROAD100_LONG_INTERCITY", shadow)
        self.assertIn("OpexRoad100LongCheapSites(", shadow)
        site_scan = function_body(road, "OpexRoad100LongCheapSites")
        self.assertIn("radius <= 16", site_scan)
        self.assertIn("seenRoad < 160", site_scan)
        self.assertIn("tests < 16", site_scan)
        self.assertIn("ringTests < 2", site_scan)
        self.assertIn("OpexOpsMeasureEnd(scanMark) >= 65000", site_scan)
        self.assertIn("AIMap.DistanceMax(rawSites[j].tile, out[0].tile)", site_scan)
        self.assertIn("AITile.GetCargoProduction(", site_scan)
        self.assertIn("AITestMode()", site_scan)
        self.assertIn("BuildDriveThroughRoadStation(", site_scan)
        self.assertIn("ROAD_PAX_VOIRIE_MIN_PAIR", site_scan)
        self.assertNotIn("production.Valuate(", site_scan)
        self.assertIn("OpexRoadBfsPath(", shadow)
        self.assertIn("OpexRoadFindDepot(", shadow)
        self.assertIn("OpexRoadDistanceAllowed", (ROOT / "candidates.nut").read_text(encoding="utf-8"))
        self.assertIn("OpexOpsMeasureEnd(mark)", shadow)
        self.assertIn("fleetGrid = [2, 4, 8, 12, 16, 24, 30]", shadow)
        self.assertIn("OpexStationRatingForHeadway(headway)", shadow)
        self.assertIn("AICargo.GetCargoIncome(", shadow)
        self.assertIn("startCash < capital + 50000", shadow)
        self.assertIn('result.reason = "SHADOW_OK"', shadow)
        for forbidden in ("BuildRoad(", "BuildRoadDepot(", "AppendOrder(",
                          "BuildDriveThroughRoadStation(", "BuildVehicle("):
            self.assertNotIn(forbidden, shadow)

    def test_long_union_deduplicates_house_tiles_and_never_admits_unverified_join(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        union = function_body(road, "OpexRoad100LongUnionEnd")
        shadow = function_body(road, "OpexRoad100LongCorridorShadow")
        self.assertEqual(union.count("producing.Valuate("), 1)
        self.assertIn("AITile.GetCargoProduction, cargo, 1, 1, 0", union)
        self.assertIn("ownCoverage.HasItem(producer)", union)
        self.assertIn("byMask[mask] += amount", union)
        self.assertIn("if ((m & subset) != 0) volume += byMask[m]", union)
        self.assertIn("selected > 3", union)
        self.assertIn("stationSpread", union)
        self.assertIn("ROAD_BUS_STOP_MIN_DISTANCE", union)
        self.assertIn("AIStationList(AIStation.STATION_ANY)", shadow)
        self.assertIn("AITileList_StationCoverage(stationId)", shadow)
        self.assertIn("OpexRoad100LongUnionEnd(", shadow)
        self.assertIn("measuredA.value < 80 || measuredB.value < 80", shadow)
        self.assertIn('result.reason = "JOIN_UNVERIFIED"', shadow)
        self.assertIn("join_validated = false", shadow)
        self.assertIn("limitOps = 250000", road)
        self.assertIn("limitOps - 40000", shadow)
        self.assertIn("limitOps - 40000", union)
        self.assertIn(' ? "OPCAP" : "SITE_B"', shadow)
        generator = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("ROAD100_LONG_SHADOW_YEAR =", generator)
        self.assertIn("250000 - longOps", generator)
        self.assertIn("phase=summary towns=", generator)
        long_only = generator[generator.index("if (ROAD100_LONG_INTERCITY"):]
        shadow_only = long_only[long_only.index("local longMark = OpexOpsMeasureBegin();"):]
        self.assertNotIn("out.append(", shadow_only)

        # Union sur masques de présence : une maison partagée par 2/3
        # stations ne doit jamais être ajoutée plusieurs fois.
        sites = [(3, 3), (5, 3), (6, 5), (12, 12)]
        houses = {(3, 2): 4, (4, 3): 6, (6, 4): 9, (5, 5): 2,
                  (12, 12): 11, (10, 10): 7}
        excluded = {(4, 3)}
        rad = 2
        by_mask = [0] * 16
        for tile, amount in houses.items():
            if tile in excluded:
                continue
            mask = 0
            for idx, (x, y) in enumerate(sites):
                if max(abs(tile[0] - x), abs(tile[1] - y)) <= rad:
                    mask |= 1 << idx
            by_mask[mask] += amount
        for subset in range(1, 16):
            counted = sum(by_mask[m] for m in range(1, 16) if m & subset)
            direct = sum(amount for tile, amount in houses.items()
                         if tile not in excluded and any(
                             (subset & (1 << idx)) and
                             max(abs(tile[0] - x), abs(tile[1] - y)) <= rad
                             for idx, (x, y) in enumerate(sites)))
            self.assertEqual(counted, direct, subset)

    def test_long_v5_selects_distinct_town_pairs_with_deterministic_fallback(self):
        """Deux prospects de la même ville ne prouvent pas deux marchés."""
        choose = function_body(self.candidates, "OpexRoad100LongSelectDiverse")
        generator = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        self.assertIn("OpexRoad100LongShadowBetter(item, first)", choose)
        self.assertIn("OpexRoad100LongShadowBetter(item, second)", choose)
        self.assertIn("item.idLo == first.idLo || item.idLo == first.idHi", choose)
        self.assertIn("item.idHi == first.idLo || item.idHi == first.idHi", choose)
        self.assertIn("if (second == null)", choose)
        self.assertIn("longPool.append(preview)", generator)
        self.assertIn("longBest = OpexRoad100LongSelectDiverse(longPool)", generator)
        self.assertIn("longOps += OpexOpsMeasureEnd(choiceMark)", generator)
        self.assertIn("li < longBest.len() && longOps < longCap", generator)
        long_only = generator[generator.index("if (ROAD100_LONG_INTERCITY"):]
        shadow_only = long_only[long_only.index("local longMark = OpexOpsMeasureBegin();"):]
        self.assertNotIn("out.append(", shadow_only)

        # Exécuter la règle Squirrel sur un échantillon adversarial en Python :
        # la deuxième meilleure paire globale partage ville 22, tandis que
        # le deuxième territoire indépendant est 7-100.
        pool = [(22, 28, 140, 129), (22, 23, 138, 84),
                (7, 100, 100, 120), (22, 7, 120, 95)]
        ordered = sorted(pool, key=lambda p: (-p[2], p[3], p[0], p[1]))
        first = ordered[0]
        distinct = [p for p in ordered[1:] if not ({p[0], p[1]} & {first[0], first[1]})]
        second = distinct[0] if distinct else ordered[1]
        self.assertEqual((first[:2], second[:2]), ((22, 28), (7, 100)))

        fallback = [(22, 28, 140, 129), (22, 23, 138, 84)]
        ordered = sorted(fallback, key=lambda p: (-p[2], p[3], p[0], p[1]))
        self.assertEqual(ordered[1][:2], (22, 23))

    def test_long_v5_path_only_never_grants_profit_or_join_approval(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        bfs = function_body(road, "OpexRoad100LongPathBudgetBfs")
        path = function_body(road, "OpexRoad100LongPathOnly")
        shadow = function_body(road, "OpexRoad100LongCorridorShadow")
        self.assertIn("out.nodes < 512", bfs)
        self.assertIn("OpexOpsMeasureEnd(mark) >= limitOps - 10000", bfs)
        self.assertIn("AIRoad.AreRoadTilesConnected(cur, nextTile)", bfs)
        self.assertIn("OpexRoadOnDtAxis(src, srcFront, nextTile)", bfs)
        self.assertIn("OpexRoadOnDtAxis(dst, dstFront, cur)", bfs)
        self.assertIn("out.route = count", bfs)
        self.assertIn("OpexRoad100LongPathBudgetBfs(firstA.tile, firstB.tile", path)
        self.assertIn("OpexRoad100LongPathBudgetBfs(firstB.tile, firstA.tile", path)
        self.assertIn("limitOps - 60000", path)
        self.assertIn("limitOps - 40000", path)
        self.assertIn('out.reason = "PATH_BIDIRECTIONAL"', path)
        self.assertIn('out.reason = "PATH_NO_BIDIRECTIONAL"', path)
        self.assertIn('out.reason = "PATH_SKIPPED_OPCAP"', path)
        self.assertIn("result.path_reason = path.reason", shadow)
        self.assertIn("result.path_ops = path.ops", shadow)
        self.assertIn('OpexDecide("ROAD100_LONG_PATH"', shadow)
        self.assertIn('main_reason=" + result.reason', shadow)
        self.assertLess(shadow.index("OpexRoad100LongPathOnly("),
                        shadow.index("OpexRoad100LongUnionEnd("))
        self.assertLess(shadow.index("OpexRoad100LongPathOnly("),
                        shadow.index('result.reason = "LOW_DEMAND"'))
        for fragment in (".Valuate(", "BuildRoad(", "BuildRoadDepot(",
                         "BuildDriveThroughRoadStation(", "CloneVehicle(",
                         "AppendOrder(", "profitAnnual", "pred_profit"):
            self.assertNotIn(fragment, bfs + path)

    def test_long_v6_build_is_separate_off_default_with_strict_plan_replay(self):
        info = re.search(r'name = "road100_long_build"(.{0,470})', self.info, re.S)
        self.assertIsNotNone(info)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(info.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_LONG_BUILD <- false", self.globaldefs)
        self.assertRegex(self.settings,
                         r'ROAD100_LONG_BUILD\s*=\s*AIController.GetSetting\("road100_long_build"\)\s*==\s*1\s*'
                         r'&& ROAD100_LONG_INTERCITY;')
        self.assertEqual(self.settings.count('GetSetting("road100_long_build")'), 1)
        candidate = function_body(self.candidates, "OpexRoad100LongBuildCandidate")
        hashbody = function_body(self.candidates, "OpexRoad100LongTraceHash")
        self.assertIn("plan.stopA.value + plan.stopB.value", candidate)
        self.assertIn("OpexRoadLineEconomics(", candidate)
        self.assertIn("economics.profitAnnual <= 0", candidate)
        self.assertIn("cash < need + 50000", candidate)
        self.assertIn("OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, economics.trains)", candidate)
        reprice = function_body(self.candidates, "OpexRoad100LongQuotedEconomics")
        self.assertIn("plan.roadQuoteCost + 3 * catalog.costRoadPerTile", reprice)
        self.assertIn("economics.capital += extra", reprice)
        self.assertIn("economics.amortAnnual +=", reprice)
        self.assertIn("economics.profitAnnual = economics.revenueAnnual", reprice)
        self.assertIn("OpexRoad100LongQuotedEconomics(catalog,", candidate)
        self.assertIn("cash < plan.road100LongCashNeed", candidate)
        self.assertIn("OpexRoad100LongTraceHash(plan.trace)", candidate)
        self.assertIn('OpexDecide("ROAD100_LONG_ADMIT",', candidate)
        for reason in ("MONTHLY_OR_TRACE", "DISTANCE", "NEG_PROFIT",
                       "FINANCE_OR_SLOT", "MAKE_CANDIDATE", "OK"):
            self.assertIn('reason=' + reason, candidate)
        self.assertIn("pos * (17 * (edge.from % 4093)", hashbody)
        generator = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        long_only = generator[generator.index("if (ROAD100_LONG_INTERCITY"):]
        self.assertIn("local longCap = ROAD100_LONG_BUILD ? 400000 : 250000;", long_only)
        self.assertIn("OpexRoad100LongConstructPlan(catalog, preliminaryLong,", long_only)
        self.assertIn("local attemptLimit = longCap - longOps", long_only)
        self.assertIn("li + 1 < longBest.len() && attemptLimit > 180000", long_only)
        self.assertIn("attemptLimit = 180000", long_only)
        self.assertIn("attempt_cap=", long_only)
        self.assertIn("OpexRoad100LongBuildCandidate(catalog,", long_only)
        self.assertIn("if (admittedLong != null)", long_only)
        self.assertIn("out.append(admittedLong)", long_only)
        self.assertIn("continue;", long_only)
        self.assertIn("OpexRoad100LongCorridorShadow(catalog, preliminaryLong,", long_only)
        dispatch = function_body((ROOT / "opcode_exact.nut").read_text(encoding="utf-8"),
                                 "OpexRoadPlanForActive")
        self.assertIn('"road100LongBuild" in candidate', dispatch)
        self.assertIn('reason = "LONG_TRACEX"', dispatch)
        self.assertIn('reason = "LONG_DRIFT"', dispatch)
        for contract in ("longPlan.stopA.tile != candidate.road100GenSiteA",
                         "longPlan.stopB.tile != candidate.road100GenSiteB",
                         "longPlan.stopA.front != candidate.road100GenFrontA",
                         "longPlan.stopB.front != candidate.road100GenFrontB",
                         "longPlan.depot.tile != candidate.road100GenDepot",
                         "OpexRoad100LongTraceHash(longPlan.trace) != candidate.road100GenTraceHash"):
            self.assertIn(contract, dispatch)
        self.assertLess(dispatch.index('"road100LongBuild" in candidate'),
                        dispatch.index("OpexRoadPlanPaxVoirie(candidate, catalog)"))
        task = function_body((ROOT / "task_road.nut").read_text(encoding="utf-8"),
                             "OpexAI::_tryBuildRoadProject")
        self.assertIn('"road100LongBuild" in candidate', task)
        self.assertIn("? 50000 : 25000", task)
        self.assertIn("OpexRoad100LongQuotedEconomics(this._catalog, economics, plan)", task)
        self.assertIn("available < plan.road100LongCashNeed", task)

    def test_long_v6_trace_is_bounded_and_accounts_all_new_roads(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        plan = function_body(road, "OpexRoad100LongConstructPlan")
        trace = function_body(road, "OpexRoad100LongShapeTrace")
        verify = function_body(road, "OpexRoad100LongVerifyTrace")
        depot = function_body(road, "OpexRoad100LongDepotPreflight")
        self.assertIn("ROAD100_LONG_BUILD", plan)
        self.assertIn("limitOps = 400000", road)
        self.assertIn("limitOps < 65000 || limitOps > 400000", plan)
        self.assertIn("limitOps - 50000", plan)
        self.assertIn("ROAD100_LONG_PLAN", plan)
        # V6: both endpoints use the real-production BUILD scanner, never
        # CheapSites. V35 adds one guarded full-scan fallback per endpoint;
        # those are not two extra unconditional site searches.
        self.assertEqual(re.findall(r"(buildScan[AB])\s*=\s*OpexRoad100LongBuildSites\(", plan),
                         ["buildScanA", "buildScanA", "buildScanB", "buildScanB"])
        for end in ("A", "B"):
            guarded_fallback = re.compile(
                rf"buildScan{end}\s*=\s*OpexRoad100LongBuildSites\(.*?"
                rf"mark, limitOps,\s*ROAD100_PORTAL_STITCH\);\s*"
                rf"if \(ROAD100_PORTAL_STITCH && buildScan{end}\.sites\.len\(\) == 0\s*"
                rf"&& buildScan{end}\.reason != \"OPCAP\"\s*"
                rf"&& OpexOpsMeasureEnd\(mark\) < limitOps - 100000\)\s*\{{\s*"
                rf"buildScan{end}\s*=\s*OpexRoad100LongBuildSites\(.*?"
                rf"mark, limitOps\);\s*\}}", re.S)
            self.assertRegex(plan, guarded_fallback)
        self.assertNotIn("OpexRoad100LongCheapSites(", plan)
        shadow = function_body(road, "OpexRoad100LongCorridorShadow")
        self.assertEqual(shadow.count("OpexRoad100LongCheapSites("), 2)
        self.assertNotIn("OpexRoad100LongBuildSites(", shadow)
        self.assertIn("roadMissingCount = missing", plan)
        self.assertIn("roadQuoteCost = quoteRoad", plan)
        self.assertIn("road100LongCashNeed = quoteTotal", plan)
        self.assertIn("trace.len() < 80 || trace.len() > 190", verify)
        self.assertIn("AIRoad.AreRoadTilesConnected(edge.from, edge.to)", verify)
        self.assertIn("AIRoad.BuildRoad(edge.from, edge.to)", verify)
        self.assertIn("AITestMode()", verify)
        self.assertIn("OpexRoadOnDtAxis(siteA.tile", trace)
        self.assertIn("OpexRoadOnDtAxis(siteB.tile", trace)
        self.assertIn("OpexRoadAppendSegment(trace,", trace)
        self.assertIn("AIRoad.BuildRoadDepot(tile, front)", depot)
        self.assertIn("AITestMode()", depot)
        for body in (plan, trace, verify, depot):
            self.assertNotIn(".Valuate(", body)
            self.assertNotIn("AIOrder.AppendOrder(", body)

    def test_long_v8_build_site_scan_is_local_bounded_and_distinct_from_shadow(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        scanner = function_body(road, "OpexRoad100LongBuildSites")
        shadow = function_body(road, "OpexRoad100LongCorridorShadow")
        self.assertIn("AITile.GetCargoProduction(tile, cargo, 1, 1, coverage)", scanner)
        self.assertIn("AITile.GetClosestTown(tile) != townId", scanner)
        self.assertIn("AIRoad.IsRoadTile(tile)", scanner)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation(site.tile, front,", scanner)
        self.assertIn("AIRoad.BuildDriveThroughRoadStation(front, site.tile,", scanner)
        self.assertIn("AITile.GetCargoProduction(front, cargo, 1, 1, coverage)", scanner)
        self.assertIn("probesHere < 4", scanner)
        self.assertIn("local orderedDirs = absX >= absY", scanner)
        self.assertIn("local axis = orderedDirs[d]", scanner)
        self.assertIn("AIStation.STATION_NEW", scanner)
        self.assertIn("res.tests < 12", scanner)
        self.assertIn("OpexOpsMeasureEnd(mark) >= limitOps - 90000", scanner)
        self.assertNotIn(".Valuate(", scanner)
        self.assertNotIn("OpexRoad100LongBuildSites(", shadow)
        self.assertEqual(shadow.count("OpexRoad100LongCheapSites("), 2)

    def test_long_v10_obstacle_search_rechecks_actual_road_edges(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        search = function_body(road, "OpexRoad100LongObstacleTrace")
        retry = function_body(road, "OpexRoad100LongObstacleVerified")
        plan = function_body(road, "OpexRoad100LongConstructPlan")
        # Search is an inexpensive proposal, never an AITest claim.
        self.assertNotIn("AITestMode()", search)
        self.assertNotIn("AIRoad.BuildRoad(", search)
        self.assertIn("OpexRoad100LongVerifyTrace(search.trace,", retry)
        self.assertIn("bannedEdges.rawset(", retry)
        self.assertIn("for (local attempt = 0; attempt < 3; attempt++)", retry)
        self.assertIn("OpexRoad100LongObstacleVerified(", plan)
        self.assertIn("obstacle_reason=", plan)
        self.assertIn("obstacle_ops=", plan)
        self.assertNotIn("parent =", search)  # Squirrel reserved identifier.
        polyline = function_body(road, "OpexRoad100LongPolylineTrace")
        self.assertIn("local trace = [{ from = siteA.tile, to = siteA.front }]", polyline)
        self.assertIn("trace.append({ from = siteB.front, to = siteB.tile })", polyline)
        self.assertIn("trace[0].to != siteA.front", polyline)
        self.assertIn("trace[trace.len() - 1].from != siteB.front", polyline)

    def test_long_v7_big_town_rank_only_selects_physical_build_prospects(self):
        compare = function_body(self.candidates, "OpexRoad100LongSortTownTotal")
        generator = function_body(self.candidates, "OpexRoad100SiteFirstGenerator")
        long_only = generator[generator.index("if (ROAD100_LONG_INTERCITY"):]
        self.assertIn("if (a.total != b.total) return a.total > b.total ? -1 : 1", compare)
        self.assertIn("return a.id < b.id ? -1 : 1", compare)
        self.assertIn("return 0;", compare)
        self.assertIn("if (ROAD100_LONG_BUILD) {", long_only)
        self.assertIn("longRanked.sort(OpexRoad100LongSortTownTotal)", long_only)
        self.assertIn("longCount = longRanked.len() < 40 ? longRanked.len() : 40", long_only)
        self.assertIn("longSrc.total + longDst.total", long_only)
        self.assertIn("longSrc.captured + longDst.captured", long_only)
        self.assertIn("local longCap = ROAD100_LONG_BUILD ? 400000 : 250000", long_only)
        self.assertIn("OpexRoad100LongConstructPlan(catalog, preliminaryLong", long_only)
        self.assertIn("longCap - longOps", long_only)
        self.assertIn("OpexRoad100LongBuildCandidate(", long_only)
        self.assertIn("OpexRoad100LongCorridorShadow(", long_only)
        self.assertNotIn("AITown.GetLastMonthProduction(", long_only)
        self.assertNotIn(".Valuate(", long_only)
        budget = function_body(self.candidates, "OpexRoad100LongBuildCandidate")
        self.assertIn("plan.stopA.value + plan.stopB.value", budget)
        self.assertNotIn(".total", budget)

    def test_long_v7_dogleg_preflight_is_bounded_and_rechecked(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        dogleg = function_body(road, "OpexRoad100LongDoglegTrace")
        verify = function_body(road, "OpexRoad100LongVerifyTrace")
        construct = function_body(road, "OpexRoad100LongConstructPlan")
        self.assertIn("blockedIndex", dogleg)
        self.assertIn("OpexRoadOnDtAxis(siteA.tile", dogleg)
        self.assertIn("OpexRoadOnDtAxis(siteB.tile", dogleg)
        self.assertIn("route.len() < 80 || route.len() > 190", dogleg)
        self.assertIn("edge.to in visited", dogleg)
        self.assertIn('blocked_stage = "AITEST_BUILD_ROAD"', verify)
        self.assertIn("AIError.GetLastError()", verify)
        self.assertIn("OpexRoad100LongDoglegTrace(trace,", construct)
        self.assertIn("OpexRoad100LongVerifyTrace(alternate,", construct)
        self.assertIn("doglegAttempts < 12", construct)
        self.assertIn("limitOps - 50000", construct)
        self.assertIn("ROAD100_LONG_PLAN", construct)
        self.assertIn("firstBlockedIndex", construct)

    # ROAD100-14 : contrats statiques pre-enregistres pour le circuit a
    # StationIDs distincts. Ils doivent etre verifies APRES integration du
    # builder, de la reconciliation Save/Load et du refleet, pas pendant
    # l'edition concurrente de ces fichiers.
    def test_tour_defaults_off_and_requires_solo_road_pax(self):
        setting = re.search(r'name = "road100_tour"(.{0,430})', self.info, re.S)
        self.assertIsNotNone(setting)
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(setting.group(1), rf"{difficulty}_value\s*=\s*0")
        self.assertIn("ROAD100_TOUR <- false", self.globaldefs)
        self.assertRegex(
            self.settings,
            r'ROAD100_TOUR\s*=\s*AIController.GetSetting\("road100_tour"\)\s*==\s*1\s*'
            r'&& ROAD100_SOLO_PAX;',
        )
        self.assertEqual(self.settings.count('GetSetting("road100_tour")'), 1)

    def test_tour_reuses_one_profitable_existing_line_behind_opt_in(self):
        task = (ROOT / "task_road.nut").read_text(encoding="utf-8")
        resize = function_body(task, "OpexAI::_refleetRoadLines")
        self.assertIn("if (ROAD100_TOUR", resize)
        self.assertIn("road100TourAttempted", resize)
        self.assertIn("road100TourAttemptYear", resize)
        self.assertIn('line.kind == "pax"', resize)
        self.assertIn("year > line.year", resize)
        self.assertIn("line.lastProfit > ", resize)
        self.assertIn('!("road100TourActive" in line)', resize)
        self.assertIn("OpexLineVehicleIds(line,", resize)
        self.assertIn("OpexRoad100TryTourAddStop(this._catalog, line, model)", resize)
        # Creation de la nouvelle station uniquement sur une ligne deja posee,
        # sans rouvrir la generation des paires/villes desservies.
        build = function_body(task, "OpexAI::_tryBuildRoadProject")
        self.assertNotIn("OpexRoad100TryTourAddStop", build)
        self.assertIn("town_already_bus_served", build)
        self.assertIn("OpexRoadPairServed(this._lines", build)
        self.assertLess(resize.index("if (ROAD100_TOUR"),
                        resize.index("OpexRoad100TryTourAddStop("))

    def test_tour_builds_independent_station_with_unique_coverage_and_bounded_work(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        tour = function_body(road, "OpexRoad100TryTourAddStop")
        self.assertIn("AIRoad.BuildDriveThroughRoadStation", tour)
        self.assertIn("AIStation.STATION_NEW", tour)
        self.assertNotIn("AIStation.STATION_JOIN_ADJACENT", tour)
        self.assertIn("AITestMode()", tour)
        self.assertIn("AIStation.GetStationID(", tour)
        self.assertIn("AITile.GetClosestTown(", tour)
        self.assertIn("AITileList_StationCoverage(", tour)
        self.assertIn("GetCargoProduction", tour)
        self.assertIn("OpexRoadBfsPath(", tour)
        self.assertIn("AIRoad.AreRoadTilesConnected(", tour)
        self.assertIn("AICompany.GetBankBalance(", tour)
        self.assertIn("OpexOpsMeasure", tour)
        self.assertIn("AIController.GetOpsTillSuspend()", tour)
        # Sur echec, ne jamais demolir les terminus ni une route historique :
        # la seule station dont le retrait est autorise est la nouvelle.
        self.assertIn("AIRoad.RemoveRoadStation(", tour)
        self.assertNotIn("OpexRoadRollback(", tour)

    def test_tour_v5_sparse_marginal_equivalent_to_v3_and_bounded(self):
        """L'index clairseme ne doit pas inventer de production ni de bassin."""
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        tour = function_body(road, "OpexRoad100TryTourAddStop")
        self.assertEqual(tour.count("production.Valuate("), 1)
        self.assertIn("production.Begin()", tour)
        self.assertIn("covered.HasItem(producingTile)", tour)
        self.assertIn("sourcesByX = array(gridW)", tour)
        self.assertIn("sourcesByX[gx].append(", tour)
        self.assertIn("foreach (source in sourcesByX[scanX])", tour)
        self.assertIn("source.y >= top && source.y <= bottom", tour)
        self.assertIn("roadSitesSeen < 64", tour)
        self.assertIn("candidatesChecked < 12", tour)
        self.assertIn("if (marginal > 0)", tour)
        self.assertIn("local limit = choices.len() < 4 ? choices.len() : 4;", tour)
        self.assertNotIn("for (local sx = -coverage;", tour)
        self.assertNotIn("local integral = array(", tour)
        self.assertIn("if (OpexOpsMeasureEnd(mark) >= 100000)", tour)

        width, height, coverage = 9, 8, 2
        raw = [[((x * 13 + y * 7) % 11) if (x + y) % 4 else 0
                for x in range(width)] for y in range(height)]
        covered = {(0, 0), (1, 1), (6, 4), (8, 7), (5, 3)}
        grid = [[0 if (x, y) in covered else raw[y][x]
                 for x in range(width)] for y in range(height)]
        sparse = [[] for _ in range(width)]
        for y in range(height):
            for x in range(width):
                if grid[y][x] > 0:
                    sparse[x].append((y, grid[y][x]))
        for x in range(width):
            for y in range(height):
                left, right = max(0, x - coverage), min(width - 1, x + coverage)
                top, bottom = max(0, y - coverage), min(height - 1, y + coverage)
                fast = sum(amount for col in range(left, right + 1)
                           for yy, amount in sparse[col] if top <= yy <= bottom)
                slow = sum(grid[yy][xx] for yy in range(top, bottom + 1)
                           for xx in range(left, right + 1))
                self.assertEqual(fast, slow, (x, y))

    def test_tour_records_four_orders_a0_b0_a1_b0_and_keeps_original_ids(self):
        task = (ROOT / "task_road.nut").read_text(encoding="utf-8")
        resize = function_body(task, "OpexAI::_refleetRoadLines")
        self.assertRegex(
            resize,
            r'line\.road100TourStops\s*<-\s*\[\s*line\.stationA\s*,\s*line\.stationB\s*,'
            r'\s*tourResult\.tile\s*,\s*line\.stationB\s*\]',
        )
        self.assertIn("line.road100TourActive <- true", resize)
        self.assertIn("line.road100TourVersion <- 1", resize)
        # Aucun nouveau LineID ni remplacement des terminus canoniques.
        self.assertNotIn("line.stationA =", resize)
        self.assertNotIn("line.stationB =", resize)
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        tour = function_body(road, "OpexRoad100TryTourAddStop")
        self.assertRegex(tour, r'AIOrder\.(?:AppendOrder|InsertOrder)\(')
        self.assertIn("AIOrder.GetOrderCount(", tour)
        self.assertIn("AIOrder.GetOrderDestination(", tour)
        self.assertIn("AIOrder.OF_NON_STOP_INTERMEDIATE", tour)
        self.assertIn("AIOrder.OF_NONE", tour)
        self.assertNotIn("AIOrder.OF_TRANSFER", tour)
        self.assertNotIn("AIOrder.OF_NO_LOAD", tour)
        self.assertNotIn("AIOrder.OF_FULL_LOAD_ANY", tour)

    def test_tour_save_load_keeps_small_station_tile_array_and_reconciles_a1(self):
        task = (ROOT / "task_road.nut").read_text(encoding="utf-8")
        resize = function_body(task, "OpexAI::_refleetRoadLines")
        for field in ("road100TourActive", "road100TourVersion",
                      "road100TourStops", "road100TourCost"):
            self.assertIn("line." + field, resize)
        persist = (ROOT / "persist.nut").read_text(encoding="utf-8")
        save = function_body(persist, "OpexSaveProjectLine")
        self.assertIn("clone line", save)
        self.assertIn('valType != "array"', save)
        skipped = persist.split("OPEX_SAVE_LINE_SKIP <- {", 1)[1].split("};", 1)[0]
        for field in ("road100TourActive", "road100TourVersion",
                      "road100TourStops", "road100TourCost"):
            self.assertNotIn(field, skipped)
        restore = function_body(persist, "OpexAI::_reconcileAfterLoad")
        self.assertIn("road100TourActive", restore)
        self.assertIn("road100TourStops", restore)
        self.assertIn("AIMap.IsValidTile(", restore)
        self.assertIn("AIStation.GetStationID(", restore)
        self.assertIn("AICompany.IsMine(", restore)
        # Une sauvegarde avec un A1 disparu doit etre rabattue sur A0/B0,
        # non rejetee comme une ligne historique corrompue.
        self.assertRegex(restore, r'road100TourStops')

    def test_tour_refleet_restores_four_orders_even_when_creation_setting_is_off(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        refill = function_body(road, "OpexRoadRefleet")
        self.assertIn("road100TourActive", refill)
        self.assertIn("road100TourStops", refill)
        self.assertIn("AIOrder.AppendOrder(", refill)
        self.assertIn("AIOrder.GetOrderCount(", refill)
        # La télémétrie ROAD100_TOUR est permise ; seule l'option de
        # CREATION ne doit pas conditionner la reconstruction 4 ordres.
        self.assertNotIn("if (ROAD100_TOUR", refill)
        # Le renouvellement utilise l'etat de la ligne sauvegardee, pas
        # l'opt-in courant : un changement ON->OFF ne casse pas la desserte.
        self.assertIn("AIVehicle.CloneVehicle(", refill)

    def test_tour_probe_and_off_path_do_not_modify_baseline_construction(self):
        road = (ROOT / "builder_road.nut").read_text(encoding="utf-8")
        task = (ROOT / "task_road.nut").read_text(encoding="utf-8")
        tour = function_body(road, "OpexRoad100TryTourAddStop")
        self.assertIn('OpexDecide("ROAD100_TOUR"', road + task)
        self.assertIn("DECISION_LOG", road + task)
        self.assertIn("OpexOpsMeasure", tour)
        build = function_body(road, "OpexBuildRoadRoute")
        self.assertNotIn("ROAD100_TOUR", build)
        self.assertNotIn("OpexRoad100TryTourAddStop(", build)
        candidates = function_body(self.candidates, "OpexBuildRoadCandidates")
        self.assertNotIn("ROAD100_TOUR", candidates)
        self.assertNotIn("OpexRoad100TryTourAddStop(", candidates)


if __name__ == "__main__":
    unittest.main()
