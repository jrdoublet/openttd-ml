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
  local proximityDroppedPax = 0, proximityDroppedFreight = 0;

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
        if (!OpexIncrementalCandidateStillValid(p, lines, abandonedPairs)) {
          if (RAIL_FAILURE_AUDIT && RAIL_CACHED_PROXIMITY_GATE == 2 && p.mode == "rail") {
            local close = OpexRailCachedProximity(p, lines);
            if (close != null && (close.hard >= 0 || close.blocking >= 0)) {
              if (p.kind == "pax") proximityDroppedPax++;
              else if (p.kind == "freight") proximityDroppedFreight++;
            }
          }
          continue;
        }
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
  if (fleetPlan != null && FLEET_PORTFOLIO) {
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

  /* 3. Injection des feeders V139 frais lors de l'implantation d'aeroports */
  if (V139_FEEDER_BUS && airBuilt) {
    local feeders = OpexBuildFeederCandidates(catalog, lines);
    foreach (candidate in feeders) {
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null
          && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
      local p = OpexProjectFromCandidate(candidate);
      if (p != null) {
        local recycledKey = OpexProjectAttemptKey(p);
        if (!(recycledKey in recycledKeys)) {
          recycledKeys[recycledKey] <- true;
          OpexProjectRememberAll(newWinners, p, stats);
        }
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
  if (RAIL_FAILURE_AUDIT) OpexRailPortfolioAudit("incremental", alternatives, funded,
      capitalBudget, proximityDroppedPax, proximityDroppedFreight);
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

/* Eau et flotte sont memorises apres l'air. Une subvention a souvent le mode
 * route, mais sa cle n'est creee qu'apres l'air : la traiter comme la route
 * la ferait passer devant les plans neufs au departage. */
function OpexAir0310KeyIsLate(key)
{
  if (typeof key != "string") return false;
  return (key.len() >= 8 && key.slice(0, 8) == "subsidy|")
      || (key.len() >= 6 && key.slice(0, 6) == "fleet|");
}

function OpexAir0310ModeIsLate(project)
{
  if (project == null || !("mode" in project)) return false;
  return project.mode == "water" || project.mode == "fleet";
}

/* OpexProjectInsertDefensive garde le projet deja present quand le score est
 * egal et que son revenu est >= (`prior.revenueAnnual >= project.revenueAnnual`).
 * L'ordre d'emission doit donc suivre OpexBuildProjects : rail, route, air deja
 * publie, air neuf, puis eau et flotte. */
function OpexAir0310InsertAirBlock(others, airBlock)
{
  local out = [];
  local inserted = false;
  foreach (project in others) {
    if (!inserted && OpexAir0310ModeIsLate(project)) {
      foreach (airProject in airBlock) out.append(airProject);
      inserted = true;
    }
    out.append(project);
  }
  if (!inserted) {
    foreach (airProject in airBlock) out.append(airProject);
  }
  return out;
}

function OpexAir0310PriorDropped(payload, priorRaw, priorKept)
{
  if (payload == null || priorRaw == null || priorRaw.len() == 0) return false;
  local found = false;
  foreach (plan in priorRaw) {
    if (plan == payload) { found = true; break; }
  }
  if (!found) return false;
  foreach (plan in priorKept) {
    if (plan == payload) return false;
  }
  return true;
}

/* Publication partielle AIR 03/10 1. Ne reconvertit que les plans neufs et
 * reecrit les projets air deja materialises la ou OpexProjectFromAir depend
 * de l'etat courant :
 * - planningOpcodes = airOps / nombre TOTAL de plans (change a chaque lot ;
 *   ce n'est pas opcodeScore) ;
 * - economicsDate = date courante ;
 * - cargo = catalog.paxCargo, et c118TownIds si C118 est actif ;
 * - budgetScore et opcodeScore sont recalcules par le meme appel. Ils ne
 *   dependent pas de airOpsPerPlan : expectedOpcodes vaut
 *   PROJECT_AIR_TRANSACTION_OPS et le score budget vient de l'economie du
 *   plan. La caisse n'est pas lue ici.
 * La selection (filtre de validite, plancher, K_dec, slots defensifs, top-K)
 * est rejouee par OpexReselectProjects. Rail, route, eau, flotte et
 * subventions ne sont pas regeneres ici : ils restent ceux du dernier
 * rebuild complet, jusqu'a la phase apply. Retourne null si le portefeuille
 * ne peut pas etre complete : l'appelant reconstruit alors tout. */
function OpexAir0310PublishIncremental(owner, scanPlans, publishedCount, airOps, bestPlan)
{
  if (owner == null || scanPlans == null || publishedCount <= 0) return null;
  if (owner._projects == null || owner._catalog == null) return null;
  local projects = owner._projects;
  if (!("candidateGroups" in projects) || projects.candidateGroups == null) return null;
  if (!("stats" in projects) || projects.stats == null) return null;

  local catalog = owner._catalog;
  local stage = OPEX_STAGE_COMPLETE;
  if (STAGED_BOOTSTRAP && owner._generationStage < OPEX_STAGE_COMPLETE) {
    stage = owner._generationStage;
  }
  local hadAirPlans = ("airPlans" in projects) && projects.airPlans != null;

  /* Queue heritee du bootstrap AIR_RAIL seulement. Le prefixe deja publie
   * de ce scan est dans scanPlans : le rebuild complet, lui, re-ajoute aussi
   * ce prefixe s'il est encore dans airPlans, et le compte deux fois. Ecart
   * assume, limite a cette etape. */
  local spPubPrior = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.prior") : null;
  local priorRaw = [];
  local priorKept = [];
  if (stage == OPEX_STAGE_AIR_RAIL && hadAirPlans
      && projects.airPlans.len() > publishedCount) {
    for (local i = publishedCount; i < projects.airPlans.len(); i++) {
      local priorPlan = projects.airPlans[i];
      priorRaw.append(priorPlan);
      if (OpexStagedAirPlanStillValid(catalog, priorPlan, owner._lines, owner._abandonedPairs)) {
        priorKept.append(priorPlan);
      }
    }
  }
  if (spPubPrior != null) OpexSpanEnd(spPubPrior);

  /* Meme denominateur que OpexBuildProjects : tous les plans du lot, y compris
   * ceux que OpexProjectFromAir refusera, plus les plans herites encore valides. */
  local spPubNew = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.new_plans") : null;
  local planCount = scanPlans.len() + priorKept.len();
  local airOpsPerPlan = (planCount > 0) ? airOps / planCount : airOps;
  local added = 0;
  local reconverted = 0;
  local invalidated = 0;
  local refreshedCount = 0;
  local pendingNew = {};
  local newKeyOrder = [];
  local newPlans = (publishedCount < scanPlans.len()) ? scanPlans.slice(publishedCount) : [];
  foreach (plan in newPlans) {
    local created = OpexProjectFromAir(catalog, plan, airOpsPerPlan);
    if (created == null) {
      invalidated++;
      continue;
    }
    local createdKey = OpexProjectKeyFor(created);
    if (!(createdKey in pendingNew)) {
      pendingNew.rawset(createdKey, []);
      newKeyOrder.append(createdKey);
    }
    pendingNew[createdKey].append(created);
    added++;
  }
  if (spPubNew != null) OpexSpanEnd(spPubNew);

  local spPubFilter = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.filter") : null;
  local keptAir = {};
  local movedAir = {};
  local othersByKey = {};
  foreach (slotKey, entry in projects.candidateGroups) {
    local list = (typeof entry == "array") ? entry : [entry];
    local others = [];
    local kept = [];
    foreach (project in list) {
      if (project == null) continue;
      if (!(("mode" in project) && project.mode == "air")) {
        others.append(project);
        continue;
      }
      local payload = ("payload" in project) ? project.payload : null;
      if (OpexAir0310PriorDropped(payload, priorRaw, priorKept)) {
        invalidated++;
        continue;
      }
      /* Pas un plan aerien : le laisser en place plutot que d'appeler
       * OpexProjectFromAir sur un payload sans sites. */
      if (payload == null || !("economics" in payload) || !("siteA" in payload)
          || !("siteB" in payload) || payload.siteA == null || payload.siteB == null) {
        kept.append(project);
        continue;
      }
      local refreshed = OpexProjectFromAir(catalog, payload, airOpsPerPlan);
      if (refreshed == null) {
        invalidated++;
        continue;
      }
      reconverted++;
      local freshKey = OpexProjectKeyFor(refreshed);
      if (freshKey == slotKey) {
        kept.append(refreshed);
      } else {
        if (!(freshKey in movedAir)) movedAir.rawset(freshKey, []);
        movedAir[freshKey].append(refreshed);
      }
    }
    othersByKey.rawset(slotKey, others);
    if (kept.len() > 0) keptAir.rawset(slotKey, kept);
  }
  if (spPubFilter != null) OpexSpanEnd(spPubFilter);

  local spPubPart = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.partition") : null;
  local preKeys = [];
  local postKeys = [];
  local preMark = {};
  foreach (slotKey, entry in projects.candidateGroups) {
    local hasRailRoad = false;
    local lane = othersByKey[slotKey];
    foreach (project in lane) {
      if (("mode" in project) && (project.mode == "rail" || project.mode == "road")) {
        hasRailRoad = true;
        break;
      }
    }
    local hasKept = (slotKey in keptAir);
    local hasIncoming = (slotKey in pendingNew) || (slotKey in movedAir);
    if (!OpexAir0310KeyIsLate(slotKey) && (hasRailRoad || hasKept)) {
      preKeys.append(slotKey);
      preMark.rawset(slotKey, true);
    } else if (!hasIncoming && (lane.len() > 0 || hasKept)) {
      postKeys.append(slotKey);
    }
  }

  local deferred = [];
  foreach (addedKey in newKeyOrder) {
    if (addedKey in preMark) continue;
    deferred.append(addedKey);
  }
  foreach (movedKey, movedList in movedAir) {
    if (movedKey in preMark) continue;
    if (movedKey in pendingNew) continue;
    if (movedList == null) continue;
    deferred.append(movedKey);
  }
  if (spPubPart != null) OpexSpanEnd(spPubPart);

  local spPubInsert = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.insert") : null;
  local rebuilt = {};
  local emitOrder = [];
  foreach (slotKey in preKeys) emitOrder.append(slotKey);
  foreach (slotKey in deferred) emitOrder.append(slotKey);
  foreach (slotKey in postKeys) emitOrder.append(slotKey);
  foreach (slotKey in emitOrder) {
    local row = (slotKey in othersByKey) ? othersByKey[slotKey] : [];
    local airBlock = [];
    if (slotKey in keptAir) {
      foreach (project in keptAir[slotKey]) airBlock.append(project);
    }
    if (slotKey in movedAir) {
      foreach (project in movedAir[slotKey]) airBlock.append(project);
    }
    if (slotKey in pendingNew) {
      foreach (project in pendingNew[slotKey]) airBlock.append(project);
    }
    local spliced = OpexAir0310InsertAirBlock(row, airBlock);
    if (spliced.len() > 0) rebuilt.rawset(slotKey, spliced);
  }
  if (spPubInsert != null) OpexSpanEnd(spPubInsert);

  local spPubStore = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.store") : null;
  local storedPlans = [];
  foreach (plan in scanPlans) storedPlans.append(plan);
  foreach (plan in priorKept) storedPlans.append(plan);
  projects.candidateGroups = rebuilt;
  projects.airPlans = storedPlans;
  projects.airPlanningOpcodes = airOps;
  if (stage == OPEX_STAGE_AIR_RAIL && hadAirPlans && storedPlans.len() > 0) {
    projects.airPlan = storedPlans[0];
  } else if ("airPlan" in projects) {
    projects.airPlan = bestPlan;
  } else {
    projects.airPlan <- bestPlan;
  }
  if (spPubStore != null) OpexSpanEnd(spPubStore);
  local spPubRecount = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.recount") : null;
  OpexProjectsRecountGroups(projects);
  if (spPubRecount != null) OpexSpanEnd(spPubRecount);
  /* La caisse est lue ici, juste avant la reelection, pas pendant FromAir. */
  local spPubCap = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.capital") : null;
  local publishCapital = OpexAvailableCapital();
  if (spPubCap != null) OpexSpanEnd(spPubCap);
  local spPubSelect = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select") : null;
  OpexReselectProjects(projects, publishCapital, owner._abandonedPairs, owner._lines,
      owner._railReadyStock);
  if (spPubSelect != null) OpexSpanEnd(spPubSelect);
  return { added = added, reconverted = reconverted, invalidated = invalidated,
      refreshed = refreshedCount };
}
