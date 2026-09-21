/* C65 passe 3 : un dispatch par tache de file, corps deplace depuis
 * _runNextTask. */
function OpexAI::_dispatchCatalog(task, year)
{

  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  /* portfolio_v2 : le portefeuille n'etait regenere qu'au CHANGEMENT DE MOIS ou apres une
   * construction reussie, et son capitalBudget etait fige a la generation. Un mois qui s'ouvrait
   * a 60 k£ sans projet finançable rendait donc un portefeuille vide, et _tryBuildProjects
   * sortait des sa premiere ligne POUR TOUT LE MOIS -- meme si la tresorerie montait ensuite a
   * 400 k£. C'est la mesure « 4,15 mois en moyenne avec >= 100 k£ et aucune croissance »
   * (docs/taches.md S0 septies, trouvaille A). On regenere donc aussi des que le capital
   * mobilisable a materiellement grandi depuis la derniere generation. */
  local stale = false;
  if (this._projects != null) {
    local budgetNow = OpexAvailableCapital();
    local budgetThen = this._projects.capitalBudget;
    /* Seuil relatif ET absolu : on ne rejoue pas la generation pour quelques milliers de livres,
     * mais un doublement du capital mobilisable rouvre le vivier. */
    local gainOk = budgetNow > budgetThen + PORTFOLIO_REFRESH_MIN_GAIN;
    local doubleOk = budgetNow > budgetThen * 2;
    if (PORTFOLIO_REFRESH_PROBE) {
      PORTFOLIO_REFRESH_PROBE_CHECKS++;
      if (gainOk) PORTFOLIO_REFRESH_PROBE_GAIN_OK++;
      if (doubleOk) PORTFOLIO_REFRESH_PROBE_DOUBLE_OK++;
      /* C43/E3 : le seul cas ou PORTFOLIO_REFRESH_MIN_GAIN bloque reellement un rafraichissement
       * que le doublement aurait seul autorise -- utile seulement si budgetThen < MIN_GAIN. */
      if (doubleOk && !gainOk) PORTFOLIO_REFRESH_PROBE_DOUBLE_ONLY++;
    }
    if (gainOk && doubleOk) stale = true;
  }
  /* Une invalidation evenementielle prime toujours la cadence mensuelle et le seuil de
   * tresorerie : le portefeuille est derive du catalogue, pas seulement du capital. */
  if (this._lastCatalogMonth == ym && this._projects != null && !stale &&
      !this._portfolioInvalidated) {
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  local refreshReason = this._portfolioInvalidated ? "event"
      : (stale ? "capital" : "month");
  if (DECISION_LOG) {
    OpexDecide("PORTFOLIO_REFRESH", "reason=" + refreshReason + " budget="
               + OpexAvailableCapital());
  }
  this._lastCatalogMonth = ym;
  this._pruneAbandonedPairs(date);
  if (PORTFOLIO_REFRESH_PROBE) {
    local refreshMark = OpexOpsMeasureBegin();
    this._catalog.refresh(this._budget, year);
    PORTFOLIO_REFRESH_PROBE_REFRESH_OPS += OpexOpsMeasureEnd(refreshMark);
    PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT++;
  } else {
    this._catalog.refresh(this._budget, year);
  }
  local fleetPlan = null;
  if (FLEET_PORTFOLIO) {
    /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
    fleetPlan = [];
    this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
  }
  if (this._recomputeEpochBounds) {
    OpexRefreshEpochBounds(this._catalog);
    this._recomputeEpochBounds = false;
  }
  this._rebuildProjects(fleetPlan);
  /* C39.5 : le vivier vient d'etre (re)genere. Horodater ici, et pas seulement au prochain
   * tour projects, pour que D2 mesure toute la fenetre de finançabilite. */
  if (C39_PROJECTS_CADENCE_PROBE) this._c39StampFinanceable();
  if (this._catalog != null && this._catalog.bounds != null) {
    local b = this._catalog.bounds;
    OpexSign(AIMap.GetTileIndex(1, 2), "EB|" + b.roadMin + "|" + b.railMin
             + "|" + b.railAirOverlapMin + "|" + b.railMax);
  }
  if ((C41_ROAD_CANDIDATE_PROFILE || C41_ROAD_FREIGHT_PROFILE || C41_ROAD_FREIGHT_TOWN_PROFILE) && this._projects != null && ("road" in this._projects) &&
      this._projects.road != null && ("profile" in this._projects.road) &&
      this._projects.road.profile != null) {
    local profile = this._projects.road.profile;
    if (C41_ROAD_CANDIDATE_PROFILE) {
      OpexC39Log("C41_ROAD_CANDIDATE_PROFILE", "ops=" + this._projects.road.opcodes
                 + " pax_ops=" + profile.paxOps + " freight_ops=" + profile.freightOps
                 + " topk_ops=" + profile.topKOps
                 + " candidates=" + this._projects.road.all);
    }
    if (C41_ROAD_FREIGHT_PROFILE) {
      OpexC39Log("C41_ROAD_FREIGHT_PROFILE", "road_ops=" + this._projects.road.opcodes
                 + " preparation_ops=" + profile.freightPreparationOps
                 + " industry_ops=" + profile.freightIndustryOps
                 + " town_ops=" + profile.freightTownOps
                 + " candidates=" + this._projects.road.all);
    }
    if (C41_ROAD_FREIGHT_TOWN_PROFILE) {
      OpexC39Log("C41_ROAD_FREIGHT_TOWN_PROFILE", "road_ops=" + this._projects.road.opcodes
                 + " scanned=" + profile.freightTownScanned
                 + " acceptance_hits=" + profile.freightTownAcceptanceHits
                 + " acceptance_misses=" + profile.freightTownAcceptanceMisses
                 + " acceptance_ops=" + profile.freightTownAcceptanceOps
                 + " accepted_pairs=" + profile.freightTownAcceptedPairs
                 + " candidate_ops=" + profile.freightTownCandidateOps);
    }
  }
  if (C41_RAIL_PORTFOLIO_PROFILE && this._projects != null && ("stats" in this._projects)
      && this._projects.stats != null && ("railProfile" in this._projects.stats)) {
    local railProfile = this._projects.stats.railProfile;
    OpexC39Log("C41_RAIL_PORTFOLIO_PROFILE", "generation_ops=" + railProfile.generationOps
               + " generation_candidates=" + railProfile.generationCandidates
               + " topk_candidates=" + railProfile.topKCandidates
               + " insert_ops=" + railProfile.insertOps
               + " inserted_projects=" + railProfile.insertedProjects
               + " selection_ops=" + this._projects.stats.selectionOpcodes
               + " selection_considered=" + this._projects.stats.budgetConsidered
               + " selection_selected=" + this._projects.stats.budgetSelected);
  }
  if (C41_RAIL_CANDIDATE_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_CANDIDATE_PROFILE", "ops=" + this._projects.rail.opcodes
               + " pax_ops=" + profile.paxOps + " freight_ops=" + profile.freightOps
               + " topk_ops=" + profile.topKOps + " candidates=" + this._projects.rail.all);
  }
  if (C41_RAIL_PAX_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_PAX_PROFILE", "preparation_ops=" + profile.paxPreparationOps
               + " pair_total_ops=" + profile.paxPairTotalOps
               + " candidate_ops=" + profile.paxCandidateOps
               + " pairs_scanned=" + profile.paxPairsScanned
               + " candidate_calls=" + profile.paxCandidateCalls
               + " candidates=" + this._projects.rail.all);
  }
  if (C41_RAIL_PAX_CANDIDATE_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_PAX_CANDIDATE_PROFILE", "sitable_ops=" + profile.paxSitableOps
               + " sitable_calls=" + profile.paxSitableCalls
               + " economics_ops=" + profile.paxEconomicsOps
               + " economics_calls=" + profile.paxEconomicsCalls);
  }
  if (C41_RAIL_PAX_ECONOMICS_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_PAX_ECONOMICS_PROFILE", "total_ops=" + profile.paxEconomicsOps
               + " calls=" + profile.paxEconomicsCalls
               + " setup_ops=" + profile.paxEconomicsSetupOps
               + " loop_ops=" + profile.paxEconomicsLoopOps
               + " loop_calls=" + profile.paxEconomicsLoopCalls
               + " post_ops=" + profile.paxEconomicsPostOps);
  }
  if (C41_RAIL_PAX_SPEED_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_PAX_SPEED_PROFILE", "setup_ops=" + profile.paxEconomicsSetupOps
               + " speed_ops=" + profile.paxSpeedOps
               + " speed_calls=" + profile.paxSpeedCalls
               + " corrected_speed_calls=" + profile.paxCorrectedSpeedCalls);
  }
  if (C41_RAIL_PAX_SPEED_DETAIL_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_PAX_SPEED_DETAIL_PROFILE", "cruise_ops=" + profile.paxCruiseOps
               + " acceleration_ops=" + profile.paxAccelerationOps
               + " integration_ops=" + profile.paxIntegrationOps
               + " speed_calls=" + profile.paxSpeedCalls
               + " unique_keys=" + profile.paxSpeedUniqueKeys
               + " cacheable_hits=" + profile.paxSpeedCacheableHits);
  }
  if (C41_RAIL_PAX_CRUISE_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_PAX_CRUISE_PROFILE", "cruise_ops=" + profile.paxCruiseOps
               + " cruise_calls=" + profile.paxCruiseCalls
               + " unique_keys=" + profile.paxCruiseUniqueKeys
               + " cacheable_hits=" + profile.paxCruiseCacheableHits);
  }
  if (C41_RAIL_FREIGHT_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_PROFILE", "preparation_ops=" + profile.freightPreparationOps
               + " industry_ops=" + profile.freightIndustryOps
               + " town_ops=" + profile.freightTownOps);
  }
  if (C41_RAIL_FREIGHT_CANDIDATE_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_CANDIDATE_PROFILE", "industry_ops=" + profile.freightIndustryOps
               + " industry_candidate_ops=" + profile.freightIndustryCandidateOps
               + " industry_candidate_calls=" + profile.freightIndustryCandidateCalls
               + " town_ops=" + profile.freightTownOps
               + " town_candidate_ops=" + profile.freightTownCandidateOps
               + " town_candidate_calls=" + profile.freightTownCandidateCalls);
  }
  if (C41_RAIL_FREIGHT_ECONOMICS_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail)
      && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_PROFILE", "ops=" + profile.freightEconomicsOps
               + " calls=" + profile.freightEconomicsCalls);
  }
  if (C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE", "ops=" + profile.freightEconomicsOps
               + " calls=" + profile.freightEconomicsCalls
               + " setup_ops=" + profile.freightEconomicsSetupOps
               + " setup_calls=" + profile.freightEconomicsSetupCalls
               + " loop_ops=" + profile.freightEconomicsLoopOps
               + " loop_calls=" + profile.freightEconomicsLoopCalls
               + " post_ops=" + profile.freightEconomicsPostOps
               + " post_calls=" + profile.freightEconomicsPostCalls);
  }
  if (C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE", "ops=" + profile.freightEconomicsOps
               + " calls=" + profile.freightEconomicsCalls
               + " reference_ops=" + profile.freightEconomicsReferenceOps
               + " reference_calls=" + profile.freightEconomicsReferenceCalls
               + " consist_ops=" + profile.freightEconomicsConsistOps
               + " consist_calls=" + profile.freightEconomicsConsistCalls
               + " capital_ops=" + profile.freightEconomicsCapitalOps
               + " capital_calls=" + profile.freightEconomicsCapitalCalls);
  }
  if (C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE", "ops=" + profile.freightEconomicsOps
               + " initial_speed_ops=" + profile.freightEconomicsConsistInitialSpeedOps
               + " initial_speed_calls=" + profile.freightEconomicsConsistInitialSpeedCalls
               + " corrected_speed_ops=" + profile.freightEconomicsConsistCorrectedSpeedOps
               + " corrected_speed_calls=" + profile.freightEconomicsConsistCorrectedSpeedCalls);
  }
  if (C41_RAIL_FREIGHT_CRUISE_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_CRUISE_PROFILE", "cruise_calls=" + profile.freightCruiseCalls
               + " unique_keys=" + profile.freightCruiseUniqueKeys
               + " cacheable_hits=" + profile.freightCruiseCacheableHits);
  }
  if (C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE", "acceleration_ops=" + profile.freightAccelerationOps
               + " acceleration_calls=" + profile.freightAccelerationCalls
               + " integration_ops=" + profile.freightIntegrationOps
               + " integration_calls=" + profile.freightIntegrationCalls);
  }
  if (C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE", "calls=" + profile.freightSpeedCalls
               + " unique_keys=" + profile.freightSpeedUniqueKeys + " cacheable_hits=" + profile.freightSpeedCacheableHits);
  }
  if (C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE && this._projects != null && ("rail" in this._projects)
      && this._projects.rail != null && ("profile" in this._projects.rail) && this._projects.rail.profile != null) {
    local profile = this._projects.rail.profile;
    OpexC39Log("C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE", "ops=" + profile.freightTownGuardsOps + " calls=" + profile.freightTownGuardsCalls + " service_ops=" + profile.freightTownServiceOps + " service_calls=" + profile.freightTownServiceCalls);
  }
  this._logStalenessRefresh(refreshReason);
  this._portfolioInvalidated = false;
  this._ranked = this._projects.rail;
  if (PORTFOLIO_LOG) {
    if (this._projects != null && this._projects.best != null && this._projects.best.len() > 0) {
      OpexLogPortfolioRank(this._projects);
    } else if (DECISION_LOG) {
      local cBudget = (this._projects != null) ? this._projects.capitalBudget : 0;
      OpexDecide("PORTFOLIO_EMPTY", "budget=" + cBudget);
    }
  }
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  /* M1 : knapsackExact est un slot legacy de compatibilite. Aucun solveur knapsack/B&B n'existe
   * dans le chemin courant ; projects.nut le force donc a false afin de ne jamais publier un
   * « optimum prouve » fictif. */
  /* Dernier champ : cout reel de CETTE selection en milliers d'opcodes.
   * On reutilise IG au lieu d'ajouter un BuildSign : la sonde H5 ne doit pas
   * creer elle-meme une tache/signature CPU supplementaire. */
  OpexSign(anchor, "IG|" + yy + "|" + this._projects.stats.modeCandidates + "|"
           + this._projects.stats.odProjects + "|" + this._projects.stats.budgetSelected
           + "|" + (this._projects.stats.knapsackExact ? 0 : 1)
           + "|" + this._budget.nested + "|" + (this._projects.stats.selectionOpcodes / 1000));
  /* Meme schema que task_projects : le 3e champ reste le capital du pool de selection legacy.
   * Cette tache ne construit rien elle-meme, donc B0 est exact. */
  OpexSign(anchor, "IB|" + yy + "|" + this._projects.capitalBudget + "|"
           + this._projects.stats.selectedCapital + "|B0");
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchC41Water(task, year)
{

  /* C41.1 : aucun merge de candidats ni re-election n'est encore correct. La tache consomme
   * exclusivement la revision qu'elle a vraiment reconstruite. */
  task.dueCycle = 2147483647;
  if (!C41_WATER_REFRESH || !C41_REVISION_PROBE || this._staleness == null ||
      this._staleness.revisions.catalog.water <= this._staleness.acknowledged.catalog.water) {
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  local revision = this._staleness.revisions.catalog.water;
  /* Le slack est seulement le reliquat du tick d'admission. Si la tache traverse un tick,
   * ses opcodes ulterieurs sont comptabilises dans `ops`, jamais abuses comme slack initial. */
  local slackOpsAvailable = AIController.GetOpsTillSuspend();
  local ops = this._catalog.refreshWater(this._budget);
  local stalenessAgeDays = this._staleness.waterCatalogDirtyDate >= 0
      ? AIDate.GetCurrentDate() - this._staleness.waterCatalogDirtyDate : -1;
  this._staleness.acknowledged.catalog.water = revision;
  this._staleness.catalog.water = false;
  OpexC39Log("C41_WATER_REFRESH", "revision=" + revision + " ops=" + ops
             + " ships=" + this._catalog.ships.len()
             + " staleness_age_days=" + stalenessAgeDays
             + " slack_ops_available=" + slackOpsAvailable
             + " slack_ops_used=" + (ops < slackOpsAvailable ? ops : slackOpsAvailable));
  if (C41_STALENESS_LEDGER) {
    OpexC41StalenessLog("C41_STALENESS_ACK", "layer=catalog.water method=targeted revision="
                        + revision + " age_days=" + stalenessAgeDays);
  }
  this._staleness.waterCatalogDirtyDate = -1;
  this._staleness.waterCatalogDirtyTick = -1;
  this._staleness.dirtySince.catalog.water = -1;
  /* C41.3 : OpexWaterPlans travaille dans un tableau temporaire. Ses tests de docks sont sous
   * AITestMode ; aucun projet persistant ni revision aval n'est modifie dans cette tranche.
   * Le catalogue geometrique eau est la seule memoisation voulue : un moteur nouveau ne doit
   * pas relancer le scan du littoral. */
  if (C41_WATER_CANDIDATE_PROBE) {
    local plans = [];
    local profile = C41_WATER_PLANS_PROFILE ? {
      town_sort_ops = 0, site_ops = 0, pair_total_ops = 0, pair_filter_rank_ops = 0,
      bfs_ops = 0, economics_ops = 0, towns_considered = 0, sites_found = 0,
      pairs_considered = 0, pairs_after_range = 0, bfs_attempts = 0,
      bfs_connected = 0, economics_attempts = 0, positive_economics = 0,
      dock_test_ops = 0, site_scan_filter_ops = 0, coast_candidates = 0,
      navigable_coast_candidates = 0, dock_tests = 0, site_cache_hits = 0,
      site_cache_misses = 0, site_tiles_visited = 0,
    } : null;
    this._budget.begin();
    OpexWaterPlans(this._catalog, this._lines, plans, profile, this._waterSiteCatalog);
    local planOps = this._budget.end("project_water_targeted_probe");
    OpexC39Log("C41_WATER_PLANS", "revision=" + revision + " ops=" + planOps
               + " plans=" + plans.len());
    if (profile != null) {
      OpexC39Log("C41_WATER_PLAN_PROFILE", "revision=" + revision + " ops=" + planOps
                 + " slack_ops_available=" + slackOpsAvailable
                 + " slack_ops_used=" + ((ops + planOps) < slackOpsAvailable
                                           ? (ops + planOps) : slackOpsAvailable)
                 + " town_sort_ops=" + profile.town_sort_ops + " site_ops=" + profile.site_ops
                 + " pair_total_ops=" + profile.pair_total_ops
                 + " pair_filter_rank_ops=" + profile.pair_filter_rank_ops
                 + " bfs_ops=" + profile.bfs_ops + " economics_ops=" + profile.economics_ops
                 + " towns=" + profile.towns_considered + " sites=" + profile.sites_found
                 + " pairs=" + profile.pairs_considered + " range=" + profile.pairs_after_range
                 + " bfs=" + profile.bfs_attempts + " connected=" + profile.bfs_connected
                 + " economics=" + profile.economics_attempts
                 + " positive=" + profile.positive_economics
                 + " dock_test_ops=" + profile.dock_test_ops
                 + " site_scan_filter_ops=" + profile.site_scan_filter_ops
                 + " coast=" + profile.coast_candidates
                 + " navigable_coast=" + profile.navigable_coast_candidates
                 + " dock_tests=" + profile.dock_tests
                 + " site_cache_hits=" + profile.site_cache_hits
                 + " site_cache_misses=" + profile.site_cache_misses
                 + " site_tiles_visited=" + profile.site_tiles_visited);
    }
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchC41Road(task, year)
{

  /* C41.15 : un seul acquittement, sans candidats/portefeuille/re-election. */
  task.dueCycle = 2147483647;
  if (!C41_ROAD_REFRESH || !C41_REVISION_PROBE || this._staleness == null ||
      this._staleness.revisions.catalog.road <= this._staleness.acknowledged.catalog.road) {
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  local revision = this._staleness.revisions.catalog.road;
  local slackOpsAvailable = AIController.GetOpsTillSuspend();
  local ops = this._catalog.refreshRoad(this._budget);
  local stalenessAgeDays = this._staleness.dirtySince.catalog.road >= 0
      ? AIDate.GetCurrentDate() - this._staleness.dirtySince.catalog.road : -1;
  this._staleness.acknowledged.catalog.road = revision;
  this._staleness.catalog.road = false;
  OpexC39Log("C41_ROAD_REFRESH", "revision=" + revision + " ops=" + ops
             + " cargo_engines=" + this._catalog.roadEngineByCargo.len()
             + " staleness_age_days=" + stalenessAgeDays
             + " slack_ops_available=" + slackOpsAvailable
             + " slack_ops_used=" + (ops < slackOpsAvailable ? ops : slackOpsAvailable));
  if (C41_STALENESS_LEDGER) {
    OpexC41StalenessLog("C41_STALENESS_ACK", "layer=catalog.road method=targeted revision="
                        + revision + " age_days=" + stalenessAgeDays);
  }
  this._staleness.dirtySince.catalog.road = -1;
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchC41RailSignals(task, year)
{

  task.dueCycle = 2147483647;
  if (!C41_RAIL_LOST_SIGNAL_REPAIR || this._c41RailSignalLines == null) {
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  local lineId = -1;
  foreach (pendingLine, ignored in this._c41RailSignalLines) { lineId = pendingLine.tointeger(); break; }
  if (lineId < 0) { task.enabled = false; if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  delete this._c41RailSignalLines["" + lineId];
  local line = this._findLineById(lineId);
  if (line == null || !("mode" in line) || line.mode != "rail" ||
      !("doubleTrack" in line) || line.doubleTrack != 1) {
    OpexC41RailSignalRepairLog("C41_RAIL_SIGNAL_REPAIR", "line=" + lineId + " status=stale");
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  local a = OpexC41BuildPbsAtApproach(("platformA" in line) ? line.platformA : null);
  local b = OpexC41BuildPbsAtApproach(("platformB" in line) ? line.platformB : null);
  local a2 = OpexC41BuildPbsAtApproach(("platformA2" in line) ? line.platformA2 : null,
                                       ("stationA2" in line) ? line.stationA2 : null);
  local b2 = OpexC41BuildPbsAtApproach(("platformB2" in line) ? line.platformB2 : null,
                                       ("stationB2" in line) ? line.stationB2 : null);
  OpexC41RailSignalRepairLog("C41_RAIL_SIGNAL_REPAIR", "line=" + lineId + " a=" + a + " b=" + b
                             + " a2=" + a2 + " b2=" + b2);
  if (this._c41RailSignalLines.len() > 0) task.dueCycle = this._taskCycle + 1;
  else task.enabled = false;
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return a == 1 || b == 1 || a2 == 1 || b2 == 1;
}
function OpexAI::_dispatchC41RailJunction(task, year)
{

  task.dueCycle = 2147483647;
  if (!C41_RAIL_LOST_JUNCTION_REPAIR || this._c41RailJunctionLines == null) {
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  local lineId = -1;
  foreach (pendingLine, ignored in this._c41RailJunctionLines) { lineId = pendingLine.tointeger(); break; }
  if (lineId < 0) { task.enabled = false; if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  delete this._c41RailJunctionLines["" + lineId];
  local line = this._findLineById(lineId);
  if (line == null || !("mode" in line) || line.mode != "rail" ||
      !("doubleTrack" in line) || line.doubleTrack != 1) {
    OpexC41RailJunctionRepairLog("C41_RAIL_JUNCTION_REPAIR", "line=" + lineId + " status=stale");
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  local exitA = ("platformA" in line && line.platformA != null && ("station_exit" in line.platformA)) ? line.platformA.station_exit : null;
  local exitB = ("platformB" in line && line.platformB != null && ("station_exit" in line.platformB)) ? line.platformB.station_exit : null;
  local leadA = OpexC41RailApproachLead(("platformA" in line) ? line.platformA : null);
  local leadB = OpexC41RailApproachLead(("platformB" in line) ? line.platformB : null);
  local leadA2 = OpexC41RailApproachLead(("platformA2" in line) ? line.platformA2 : null,
                                         ("stationA2" in line) ? line.stationA2 : null);
  local leadB2 = OpexC41RailApproachLead(("platformB2" in line) ? line.platformB2 : null,
                                         ("stationB2" in line) ? line.stationB2 : null);
  local a = OpexC41RepairJunction(leadA, exitA);
  local b = OpexC41RepairJunction(leadB, exitB);
  local a2 = OpexC41RepairJunction(leadA2, ("stationA2" in line) ? line.stationA2 : null);
  local b2 = OpexC41RepairJunction(leadB2, ("stationB2" in line) ? line.stationB2 : null);
  local depot = ("depot" in line) ? line.depot : null;
  local front = (depot != null && AIMap.IsValidTile(depot) && AIRail.IsRailDepotTile(depot))
      ? AIRail.GetRailDepotFrontTile(depot) : null;
  local depotRepair = OpexC41RepairJunction(front, depot);
  local depot2 = ("depot2" in line) && line.depot2 != null ? line.depot2 : -1;
  local front2 = (AIMap.IsValidTile(depot2) && AIRail.IsRailDepotTile(depot2))
      ? AIRail.GetRailDepotFrontTile(depot2) : null;
  local depot2Repair = OpexC41RepairJunction(front2, depot2);
  OpexC41RailJunctionRepairLog("C41_RAIL_JUNCTION_REPAIR", "line=" + lineId + " a=" + a + " b=" + b
                               + " a2=" + a2 + " b2=" + b2 + " depot=" + depotRepair + " depot2=" + depot2Repair);
  if (this._c41RailJunctionLines.len() > 0) task.dueCycle = this._taskCycle + 1;
  else task.enabled = false;
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return a == 1 || b == 1 || a2 == 1 || b2 == 1 || depotRepair == 1 || depot2Repair == 1;
}
function OpexAI::_dispatchReport(task, year)
{

  if (this._lastReportYear == year) { if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  this._lastReportYear = year;
  if (DECISION_LOG) {
    local bank = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local loan = AICompany.GetLoanAmount();
    OpexDecide("REPORT", "year=" + year + " lines=" + this._lines.len() + " bank=" + bank + " loan=" + loan);
  }
  OpexSign(AIMap.GetTileIndex(1, 1), "LB|" + (year % 100) + "|"
           + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
  if (CASH_RESERVE_PROBE) {
    local calls = CASH_RESERVE_PROBE_CALLS - this._cashReserveProbeLastCalls;
    local minBinds = CASH_RESERVE_PROBE_MIN_BINDS - this._cashReserveProbeLastMinBinds;
    local maxBinds = CASH_RESERVE_PROBE_MAX_BINDS - this._cashReserveProbeLastMaxBinds;
    this._cashReserveProbeLastCalls = CASH_RESERVE_PROBE_CALLS;
    this._cashReserveProbeLastMinBinds = CASH_RESERVE_PROBE_MIN_BINDS;
    this._cashReserveProbeLastMaxBinds = CASH_RESERVE_PROBE_MAX_BINDS;
    OpexCashReserveProbeLog("year=" + year + " calls=" + calls + " min_binds=" + minBinds
                            + " max_binds=" + maxBinds);
  }
  if (PORTFOLIO_REFRESH_PROBE) {
    local checks = PORTFOLIO_REFRESH_PROBE_CHECKS - this._portfolioRefreshProbeLastChecks;
    local gainOk = PORTFOLIO_REFRESH_PROBE_GAIN_OK - this._portfolioRefreshProbeLastGainOk;
    local doubleOk = PORTFOLIO_REFRESH_PROBE_DOUBLE_OK - this._portfolioRefreshProbeLastDoubleOk;
    local doubleOnly = PORTFOLIO_REFRESH_PROBE_DOUBLE_ONLY - this._portfolioRefreshProbeLastDoubleOnly;
    this._portfolioRefreshProbeLastChecks = PORTFOLIO_REFRESH_PROBE_CHECKS;
    this._portfolioRefreshProbeLastGainOk = PORTFOLIO_REFRESH_PROBE_GAIN_OK;
    this._portfolioRefreshProbeLastDoubleOk = PORTFOLIO_REFRESH_PROBE_DOUBLE_OK;
    this._portfolioRefreshProbeLastDoubleOnly = PORTFOLIO_REFRESH_PROBE_DOUBLE_ONLY;
    local refreshOps = PORTFOLIO_REFRESH_PROBE_REFRESH_OPS - this._portfolioRefreshProbeLastRefreshOps;
    local refreshCount = PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT - this._portfolioRefreshProbeLastRefreshCount;
    this._portfolioRefreshProbeLastRefreshOps = PORTFOLIO_REFRESH_PROBE_REFRESH_OPS;
    this._portfolioRefreshProbeLastRefreshCount = PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT;
    OpexPortfolioRefreshProbeLog("year=" + year + " checks=" + checks + " gain_ok=" + gainOk
                                 + " double_ok=" + doubleOk + " double_only=" + doubleOnly
                                 + " refresh_ops=" + refreshOps + " refresh_count=" + refreshCount);
  }
  /* C41.11 : le rapport exclut son propre cout, publie au plus une fois par an. */
  this._logC41SlackLedger(year);
  this._logC41OpportunityLedger(year);
  this._logC41AdmissionLedger(year);
  this._logC41RailSliceLedger(year);
  this._logC39PassClockLedger(year);
  if (C49_SCARCITY_LEDGER) this._logC49ScarcityLedger(year);
  if (C55_ORIGIN_RELAX_PROBE) this._logC55OriginRelaxLedger(year);
  if (C52_AUTOREPLACE_LOG) this._logC52AutoreplaceLedger(year);
  if (C52_EVENT_EXPOSURE_PROBE) this._logC52EventExposureLedger(year);
  if (C54_VEHICLE_ORDERS_PROBE) this._logC54VehicleOrders(year);
  if (C60_TOWN_RATING_PROBE) this._logC60TownRatingLedger(year);
  if (C50_CHRONOLOGY_PROBE) this._logC50AnnualReport(year);
  this._reportYear(year, this._ranked);
  this._reportLines(year);
  if (C63_INVEST_PROBE) OpexC63EnsureYear(year);
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchScrap(task, year)
{

  this._scrapDeadLines(year);
  this._scrapRetiredVehicles(year);
  this._purgeUnprofitableStreaks();
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchAir(task, year)
{

  /* C34.1 : sous air_portfolio, la construction aerienne passe EXCLUSIVEMENT par le portefeuille.
   * Motif mesure (docs/taches.md 0 novemquinquagesies) : OpexAirPlans est appele DEUX fois par
   * cycle -- une fois ici (main.nut:971) et une fois dans OpexBuildProjects (projects.nut:693) --
   * et chaque passage coute ~21 jours de temps de jeu. Sur la graine 1, 11 passages ont mange
   * 63 % de l'annee 1. Eteindre cette tache supprime la moitie du goulot, et l'executeur du
   * portefeuille sait deja batir mode == "air" (main.nut:1839). */
  if (AIR_PORTFOLIO) { task.enabled = false; if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  this._tryBuildAir(year); if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return true;
}
function OpexAI::_dispatchAirFleet(task, year)
{

  /* C34.2 / C36.2 : sous fleet_portfolio, la croissance de flotte est arbitree par le portefeuille.
   * La tache dediee ne depense plus a l'aveugle, mais inspecte la flotte et injecte
   * les opportunites mures dans le vivier incremental du portefeuille sans attendre un an. */
  task.dueCycle = this._taskCycle + 1;
  if (FLEET_PORTFOLIO) {
    if (PORTFOLIO_CACHE && this._projects != null) {
      local fleetPlan = [];
      this._resizeAirFleets(year, fleetPlan);
      if (fleetPlan.len() > 0) {
        local budgetNow = OpexAvailableCapital();
        this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs);
        this._ranked = this._projects.rail;
      }
    }
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  if (C56_TASK_TRACE) {
    local resized = this._resizeAirFleets(year);
    OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return resized;
  }
  return this._resizeAirFleets(year);
}
function OpexAI::_dispatchProjects(task, year)
{

  /* Si l'evenement est arrive apres le passage catalog dans le cycle courant, attendre
   * sa reconstruction plutot que de choisir une ligne dans le vivier devenu obsolete. */
  if (C39_PROJECTS_CADENCE_PROBE) {
    local date = AIDate.GetCurrentDate();
    local tick = AIController.GetTick();
    /* C39.5b : un seul OpexAvailableCapital() par dispatch -- reutilise pour le comptage
     * finançable ET pour le champ capital= ci-dessous, au lieu de l'appeler deux fois pour la
     * meme valeur. isProjectsTurn=true : c'est le seul site qui doit avancer turns/topTurns. */
    local capitalNow = OpexAvailableCapital();
    local financeable = this._c39StampFinanceable(capitalNow, true);
    OpexC39ProjectsCadenceLog("phase=dispatch days_since_last="
        + (this._c39CadenceLastDate >= 0 ? date - this._c39CadenceLastDate : -1)
        + " ticks_since_last="
        + (this._c39CadenceLastTick >= 0 ? tick - this._c39CadenceLastTick : -1)
        + " cycles_since_last="
        + (this._c39CadenceLastCycle >= 0 ? this._taskCycle - this._c39CadenceLastCycle : -1)
        + " rail_search=" + (this._railSearch != null ? 1 : 0)
        + " rail_phase=" + (this._railSearch != null ? this._railSearch.phase : "-")
        + " rail_kind=" + (this._railSearch != null ? this._railSearch.kind : "-")
        + " invalidated=" + (this._portfolioInvalidated ? 1 : 0)
        + " best_len=" + (this._projects != null ? this._projects.best.len() : -1)
        + " capital=" + capitalNow + " financeable=" + financeable);
    this._c39CadenceLastDate = date;
    this._c39CadenceLastTick = tick;
    this._c39CadenceLastCycle = this._taskCycle;
  }
  if (this._portfolioInvalidated) { if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  if (C56_TASK_TRACE) {
    local builtProjects = this._tryBuildProjects(year);
    OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return builtProjects;
  }
  return this._tryBuildProjects(year);
}
function OpexAI::_dispatchExpand(task, year)
{

  /* G6§1 : la tache portait UNIQUEMENT sur RAIL_EXPAND, alors que le bloc RAIL_REFLEET
   * (second train, passage en double voie) vit a l'interieur de _expandRailLines. La desactiver
   * sur !RAIL_EXPAND rendait donc rail_refleet injoignable malgre son defaut a 1.
   * Desormais inconditionnel : on ne desactive que si les DEUX sont eteints. */
  if (!RAIL_EXPAND && !RAIL_REFLEET) { task.enabled = false; if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  this._expandRailLines(year);
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchRefleet(task, year)
{

  this._refleetRoadLines(year);
  this._refleetCrashedWaterLines(year);
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchTownGrowth(task, year)
{

  if (!TOWN_GROWTH_ENABLED) { task.enabled = false; if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  if (TOWN_GROWTH_SKIP_NOOP && !this._tryTownGrowth(year)) {
    if (C56_TASK_TRACE) {
      local nextTask = this._runNextTask();
      OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
      return nextTask;
    }
    return this._runNextTask();
  }
  else this._tryTownGrowth(year);
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
function OpexAI::_dispatchRepay(task, year)
{

  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._lastRepayMonth == ym) { if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle); return false; }
  this._lastRepayMonth = ym;
  this._tryRepayLoan(year);
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return true;
}
