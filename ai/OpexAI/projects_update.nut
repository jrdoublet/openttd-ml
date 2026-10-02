/* Extrait de projects.nut (R14) : Mise a jour incrementale du cache de candidats et injection flotte. Requis depuis projects.nut. */

/* C80 fleet inject : injecte les opportunites mures de flotte directement dans
 * candidateGroups, sans recalculer les plans aeriens. */
function OpexInjectFleetProjects(projects, fleetPlan, abandonedPairs = null, capitalBudget = null, lines = null)
{
  if (projects == null || !(("candidateGroups" in projects)) || projects.candidateGroups == null) {
    return projects;
  }
  if (capitalBudget == null) capitalBudget = OpexAvailableCapital();

  local winners = {};
  local scratch = { modeCandidates = 0, modeAlternatives = 0 };

  /* 1. Retirer les anciens projets de mode fleet et filtrer les paires abandonnees */
  foreach (groupKey, entry in projects.candidateGroups) {
    local list = (typeof entry == "array") ? entry : [entry];
    foreach (project in list) {
      if (project == null) continue;
      if (project.mode == "fleet") continue;
      if (abandonedPairs != null && OpexCandidateIsAbandoned(project, abandonedPairs)) continue;
      OpexProjectRememberAll(winners, project, scratch);
    }
  }

  /* 2. Injecter les opportunites de flotte fraiches */
  if (FLEET_PORTFOLIO && fleetPlan != null) {
    foreach (entry in fleetPlan) {
      local p = OpexProjectFromFleet(entry);
      if (p != null) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordProduced("fleet", 1, 1);
        OpexProjectRememberAll(winners, p, scratch);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("fleet", "profit_nonpositive", 1);
      }
    }
  }

  projects.candidateGroups = winners;
  OpexProjectsRecountGroups(projects);
  return OpexReselectProjects(projects, capitalBudget, abandonedPairs, lines);
}

/* C36.1 : Caching incremental du vivier post-chantier.
 * Au lieu de reconstruire tout le portefeuille ex nihilo apres chaque ligne achevee (15 jours
 * d'attente sur A* et scan aerien), filtre les candidats existants en memoire, injecte les
 * nouvelles opportunites de flotte, et réélit le portefeuille sur le capital restant.
 * Execution : < 1 tick (< 500 opcodes, 0 jour). */
function OpexC121PlanTouchesTowns(project, towns)
{
  if (towns == null || !("payload" in project) || project.payload == null) return true;
  local plan = project.payload;
  if (("siteA" in plan) && plan.siteA != null && ("town" in plan.siteA)
      && (plan.siteA.town.id in towns)) return true;
  if (("siteB" in plan) && plan.siteB != null && ("town" in plan.siteB)
      && (plan.siteB.town.id in towns)) return true;
  return false;
}

function OpexIncrementalUpdateProjects(projects, catalog, budget, lines, capitalBudget, fleetPlan = null, abandonedPairs = null, airTouchedTowns = null, railReadyStock = null)
{
  local spIncr = PROBE_SPAN_TRACE ? OpexSpanBegin("select.incremental") : null;
  if (C80_RAIL_STOCK_GATE && railReadyStock == null && projects != null && ("railReadyStock" in projects)) {
    railReadyStock = projects.railReadyStock;
  }
  local airBuilt = airTouchedTowns != null && airTouchedTowns.len() > 0;
  local b6BudgetDate = AIDate.GetCurrentDate();
  local stats = {
    odProjects = 0,
    modeCandidates = 0,
    modeAlternatives = 0,
    modeReplaced = 0,
    poolInfundable = 0,
    budgetConsidered = 0,
    budgetSelected = 0,
    budgetRejected = 0,
    selectedRevenue = 0,
    selectedCapital = 0,
    selectionPoolCapital = 0,
    nextProjectCapital = 0,
    knapsackNodes = 0,
    knapsackExact = false,
  };

  local newWinners = {};
  local recycledKeys = {};
  local cacheScanned = 0;
  local cacheRetained = 0;
  local abandonFiltered = 0;

  /* 1. Filtrer les candidats existants du vivier */
  if (("candidateGroups" in projects) && projects.candidateGroups != null) {
    foreach (key, entry in projects.candidateGroups) {
      local list = (typeof entry == "array") ? entry : [entry];
      foreach (p in list) {
        cacheScanned++;
        if (p == null) continue;
        /* La flotte est regeneree fraiche ci-dessous. */
        if (p.mode == "fleet" && FLEET_PORTFOLIO && fleetPlan != null) continue;
        /* Early-slot est une priorite transitoire. Apres chaque chantier, le
         * nombre de villes deja securisees peut changer ; un ancien plan air ne
         * doit donc jamais conserver un bonus devenu perime. Les plans air sont
         * regeneres frais un peu plus bas dans cette meme passe. */
        /* Sans chantier aerien dans la passe, les plans air sont gardes
         * (le bonus early slot est recalcule a la selection, OpexProjectRefreshEarlySlot) ; apres un
         * chantier aerien, comportement historique : tout jeter puis tout replanifier. */
        if (airBuilt && AIR_EARLY_SLOT && p.mode == "air") {
          /* C121 catalogue incremental : ne jeter que les plans qui touchent une ville du
           * chantier ; les autres restent (bonus early slot recalcule a la selection) et le
           * catalogue decoupe ajoutera les nouvelles paires par tranches. */
          if (!C121_CATALOG_INCREMENTAL || OpexC121PlanTouchesTowns(p, airTouchedTowns)) continue;
        }

        if (OpexCandidateIsAbandoned(p, abandonedPairs)) {
          abandonFiltered++;
          continue;
        }
        if (!OpexIncrementalCandidateStillValid(p, lines, abandonedPairs)) continue;
        local recycledKey = OpexProjectAttemptKey(p);
        if (!(recycledKey in recycledKeys)) recycledKeys[recycledKey] <- true;
        /* B6/06.11 mesure seulement : marquer les objets qui traversent REELLEMENT
         * le replay incremental. Le champ n'est jamais lu hors du diagnostic. */
        if (DECISION_LOG) p.b6RecycledSinceFresh <- true;
        OpexProjectRememberAll(newWinners, p, stats);
        cacheRetained++;
      }
    }
  }

  /* 2. Injection des projets de croissance de flotte (refleet) frais */
  if (FLEET_PORTFOLIO && fleetPlan != null) {
    foreach (entry in fleetPlan) {
      local p = OpexProjectFromFleet(entry);
      if (p != null) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordProduced("fleet", 1, 1);
        OpexProjectRememberAll(newWinners, p, stats);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("fleet", "profit_nonpositive", 1);
      }
    }
  }

  /* 4. Injection des projets aeriens frais (notamment les lignes hub ouvertes par un nouvel aeroport) */
  if (AIR_PORTFOLIO && ((catalog.airCombos != null && catalog.airCombos.len() > 0) || catalog.airport != null)) {
    if (airBuilt && C121_CATALOG_INCREMENTAL) {
      /* Replanification AIR differee au catalogue decoupe (couche C76 lines non acquittee
       * par l'appelant) : plus de OpexAirPlans synchrone de 4 a 18 M opcodes ici. */
      if (C69_BOTTLENECK_PROBE) OpexC80RecordAirIncremental("deferred");
    } else if (airBuilt) {
      if (C69_BOTTLENECK_PROBE) OpexC80RecordAirIncremental("targeted");
      local freshAirPlans = [];
      if (C80_AIR_CHOICE_MEMO) AIR_CHOICE_MEMO_STATE = 2;
      OpexAirPlans(catalog, lines, 0, freshAirPlans, abandonedPairs);
      AIR_CHOICE_MEMO_STATE = 0;
      local airOpsPerPlan = (freshAirPlans.len() > 0) ? (PROJECT_AIR_TRANSACTION_OPS / freshAirPlans.len()) : PROJECT_AIR_TRANSACTION_OPS;
      foreach (plan in freshAirPlans) {
        local p = OpexProjectFromAir(catalog, plan, airOpsPerPlan);
        if (p != null) {
          OpexProjectRememberAll(newWinners, p, stats);
        }
      }
    } else {
      if (C69_BOTTLENECK_PROBE) OpexC80RecordAirIncremental("none");
    }
  }

  /* 5. Selection du portefeuille sur le capital restant */
  local funded = null;
  local selectionLight = CATALOG_COST_PROBE ? OpexSelectionLightBegin() : null;
  local opsMark = OpexOpsMeasureBegin();
  local alternatives = [];
  foreach (key, list in newWinners) {
    stats.odProjects++;
    foreach (project in list) alternatives.push(project);
  }
  if (C80_RAIL_STOCK_GATE) alternatives = OpexRailStockMergeAlternatives(alternatives, railReadyStock, stats);
  if (C121_AIR_FIRST_YEAR_RAIL_PREP && !C121_CATALOG_FIRST_YEAR_ACTIVE) {
    if (railReadyStock == null && ("railReadyStock" in projects) && projects.railReadyStock != null)
      railReadyStock = projects.railReadyStock;
    alternatives = OpexRailPrepMergeAlternatives(alternatives, railReadyStock);
  }
  alternatives = OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines);
  funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);
  stats.budgetConsidered = alternatives.len();
  stats.budgetSelected = funded.len();
  stats.budgetRejected = alternatives.len() - funded.len();
  stats.knapsackNodes = 0;
  stats.knapsackExact = false;
  stats.selectionOpcodes <- OpexOpsMeasureEnd(opsMark);
  if (selectionLight != null) OpexSelectionLightEnd(selectionLight, "incremental",
      stats.selectionOpcodes, alternatives.len(), funded.len());
  OpexB6LogSelectionCausality("incremental", alternatives, funded, capitalBudget, b6BudgetDate,
                             recycledKeys);
  OpexB6LogRepricedFreightTop(catalog, lines, funded, recycledKeys, capitalBudget);

  /* 6. Cloture des statistiques et du capital restant */
  local selectedRev = 0;
  local selectedCap = 0;
  foreach (p in funded) {
    selectedRev += p.revenueAnnual;
    selectedCap += OpexProjectFinanceCapital(p);
  }
  stats.selectedRevenue = selectedRev;
  stats.selectedCapital = selectedCap;
  stats.selectionPoolCapital = selectedCap;
  stats.nextProjectCapital = funded.len() > 0 ? OpexProjectFinanceCapital(funded[0]) : 0;
  local remaining = capitalBudget - selectedCap;
  if (remaining < 0) remaining = 0;

  local stampExtras = {
    abandonFiltered = abandonFiltered,
    abandonedPairsCount = (abandonedPairs != null) ? abandonedPairs.len() : 0,
    cacheScanned = cacheScanned,
    cacheRetained = cacheRetained
  };
  OpexProjectsStampSelectionStats(stats, projects, alternatives, funded, capitalBudget, stampExtras);

  if (DECISION_LOG) {
    local vivierPool = [];
    foreach (key, list in newWinners) {
      foreach (project in list) vivierPool.push(project);
    }
    OpexLogVivier("incremental", vivierPool, stats, capitalBudget, remaining);
  }

  AILog.Info("[PORTFOLIO_CACHE] incremental: candidates=" + stats.modeCandidates + " od=" + stats.odProjects + " selected=" + stats.budgetSelected + " remaining=" + remaining);

  projects.all = stats.odProjects;
  projects.best = funded;
  if (C69_BOTTLENECK_PROBE) {
    projects.c69Best <- ::C69_LAST_AFFORDABLE;
    projects.c69KDecData <- ::C69_LAST_KDEC_DATA;
  }
  projects.stats = stats;
  projects.capitalBudget = capitalBudget;
  projects.capitalRemaining = remaining;
  projects.candidateGroups = newWinners;
  if (C80_RAIL_STOCK_GATE) projects.railReadyStock <- railReadyStock;
  else if (C121_AIR_FIRST_YEAR_RAIL_PREP && railReadyStock != null) {
    if ("railReadyStock" in projects) projects.railReadyStock = railReadyStock;
    else projects.railReadyStock <- railReadyStock;
  }
  if (spIncr != null) OpexSpanEnd(spIncr);
  return projects;
}
