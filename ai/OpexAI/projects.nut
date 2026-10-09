/* Etape 1 : portefeuille de projets multimodaux.
 *
 * Le catalogue ne decide rien. Pour chaque couple origine/destination, cette etape compare tous
 * les modes faisables sur un ROI homogene (profit annuel / capital) et ne garde que le meilleur.
 * Le portefeuille passe ensuite par deux contraintes, dans cet ordre :
 *   1. capital : maximiser le revenu annuel par livre immobilisee et remplir le budget disponible ;
 *   2. calcul : ordonner les projets finances par revenu annuel / opcodes attendus.
 *
 * Les chantiers sont indivisibles ; un renfort AIR peut etre reduit avant classement.
 * Apres chaque construction reussie, main.nut regenere le portefeuille, car le cash et les
 * origines disponibles ont change. Il n'existe donc plus de priorite rail/route/air/eau pour
 * l'ouverture de nouvelles lignes dans l'ordonnanceur.
 */

/* Cascade pax par distance decroissante. Le fret accompagne la premiere passe. */
const OPEX_STAGE_AIR_ONLY = 0;
const OPEX_STAGE_AIR_RAIL = 1;
const OPEX_STAGE_RAIL_ONLY = 2;
const OPEX_STAGE_ROUTE_ONLY = 3;
const OPEX_STAGE_COMPLETE = 4;
/* C43/E3 (docs/taches.md) : sature a 77,4%/70,1% des appels de selection (VIVIER, 5x6, 2026-09-08)
 * -- mord fort. Rendu reglable pour le banc factoriel 32 contre 64, jamais retouche depuis 2026-09-02
 * avant cette mesure. */
PROJECT_TOP_K <- 64;
/* Propose par l'utilisateur le 2026-09-08 : caler PROJECT_TOP_K sur villes+industries de la carte
 * plutot que sur une constante fixe. Defaut 0 : aucun changement de comportement. */
PROJECT_TOP_K_DYNAMIC <- false;

/* Mesures communes. Le pathfinder rail consomme environ 2 700 opcodes par iteration. Pour les
 * autres modes, la partie plan est mesuree pendant la generation ; les constantes ci-dessous
 * couvrent les commandes transactionnelles qui restent apres le plan. */
/* Calibré sur la médiane réelle mesurée (3 105 opcodes par itération d'A* rail, cf. docs/taches.md §3 octies & C3). */
const PROJECT_RAIL_OPS_PER_ITERATION = 3105;
const PROJECT_RAIL_TRANSACTION_OPS = 200000;
const PROJECT_ROAD_TRANSACTION_OPS = 287000;
const PROJECT_AIR_TRANSACTION_OPS = 100000;
const PROJECT_WATER_TRANSACTION_OPS = 100000;
CLEAN_DENSITY_SCORE <- true;

/* R14 : etapes du portefeuille, chargees dans l'ordre historique de definition. */
require("projects_rank_log.nut");
require("projects_models.nut");
require("projects_finance.nut");
require("projects_builders.nut");
require("projects_selection.nut");
require("projects_generation.nut");
require("projects_diagnostics.nut");
require("projects_update.nut");

function OpexProjectEmptyRoad()
{
  return {
    all = 0, candidates = [], best = [],
    stats = { pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
              economicsUnavailable = 0, profitTooLow = 0, profitNonPositive = 0,
              profitBelowFloorKept = 0, accepted = 0,
              roadDistanceShort = 0, roadDistanceLong = 0 },
    opcodes = 0,
  };
}

function OpexEmptyRailCandidates()
{
  return {
    all = 0, candidates = [], best = [], bands = [0, 0, 0, 0],
    stats = {
      townsServed = 0, townsUnserved = 0, industriesServed = 0, industriesUnserved = 0,
      pairsTotal = 0, pairsOriginServed = 0,
      noMonthly = 0, unsitable = 0,
      distanceShort = 0, distanceLong = 0, economicsUnavailable = 0,
      profitNonPositive = 0, ratioTooLow = 0, accepted = 0, topKOmitted = 0,
    },
    opcodes = 0, profile = null,
  };
}

/* Les etapes du bootstrap conservent les familles deja generees, mais une
 * construction peut avoir rendu une paire desservie entre deux etapes. Passer
 * les objets bruts par la meme validation que le cache incremental avant de les
 * reinjecter empeche le projet qui vient d'etre construit de revenir en tete. */
function OpexStagedCandidateStillValid(candidate, lines, abandonedPairs = null)
{
  if (candidate == null) return false;
  local project = OpexProjectFromCandidate(candidate);
  return project != null && OpexIncrementalCandidateStillValid(project, lines, abandonedPairs);
}

function OpexStagedAirPlanStillValid(catalog, plan, lines, abandonedPairs = null)
{
  if (plan == null) return false;
  local project = OpexProjectFromAir(catalog, plan, 0);
  return project != null && OpexIncrementalCandidateStillValid(project, lines, abandonedPairs);
}

function OpexStagedWaterPlanStillValid(catalog, plan, lines, abandonedPairs = null)
{
  if (plan == null) return false;
  local project = OpexProjectFromWater(catalog, plan, 0);
  return project != null && OpexIncrementalCandidateStillValid(project, lines, abandonedPairs);
}

function OpexMergeRailCandidateSet(base, extra, mergeReuse = true)
{
  if (base == null) return extra;
  if (extra == null) return base;
  foreach (candidate in extra.candidates) base.candidates.append(candidate);
  if (mergeReuse && ("reuseCandidates" in extra) && extra.reuseCandidates != null
      && extra.reuseCandidates.len() > 0) {
    if (!("reuseCandidates" in base) || base.reuseCandidates == null) base.reuseCandidates <- [];
    foreach (candidate in extra.reuseCandidates) base.reuseCandidates.append(candidate);
  }
  base.all = base.candidates.len();
  base.best = OpexTopK(base.candidates, TOP_K);
  base.bands = OpexBands(base.candidates);
  base.opcodes += extra.opcodes;
  if (("stats" in base) && base.stats != null && ("stats" in extra) && extra.stats != null) {
    foreach (key, value in extra.stats) {
      local valueType = typeof value;
      if ((valueType == "integer" || valueType == "float") && (key in base.stats)) {
        base.stats[key] += value;
      }
    }
  }
  return base;
}

/* Le fallback freightCargo choisit un seul cargo actif. Quand un cargo suivant fournit enfin du
 * fret FRAIS, conserver les reuse pax de la passe initiale mais remplacer le pool reuse fret par
 * celui de ce cargo selectionne. Les reuse des cargos vides intermediaires ne doivent pas fuir
 * dans le portefeuille final. */
function OpexRailSelectFreightReusePool(base, selected)
{
  if (base == null) return selected;
  if (selected != null && ("reuseFreightDeferred" in selected)
      && selected.reuseFreightDeferred != null) {
    base.reuseFreightDeferred <- selected.reuseFreightDeferred;
  } else if ("reuseFreightDeferred" in base) {
    /* Le cargo frais selectionne n'a aucun reuse fret : ne pas conserver ceux du cargo precedent. */
    base.reuseFreightDeferred = null;
  }
  local keep = [];
  if (("reuseCandidates" in base) && base.reuseCandidates != null) {
    foreach (candidate in base.reuseCandidates) {
      if (!("kind" in candidate) || candidate.kind != "freight") keep.append(candidate);
    }
  }
  if (selected != null && ("reuseCandidates" in selected)
      && selected.reuseCandidates != null) {
    foreach (candidate in selected.reuseCandidates) {
      if (("kind" in candidate) && candidate.kind == "freight") keep.append(candidate);
    }
  }
  if (keep.len() > 0) base.reuseCandidates <- keep;
  else if ("reuseCandidates" in base) base.reuseCandidates = [];
  return base;
}

function OpexBuildProjects(catalog, budget, lines, fleetPlan = null, abandonedPairs = null,
                           generationStage = null, priorProjects = null, freightCargo = null,
                           freightCargoOrder = null, activeSubsidies = null, airOverride = null,
                           railReadyStock = null)
{
  local cost = CATALOG_COST_ACTIVE;
  local costMark = cost != null ? OpexOpsMeasureBegin() : null;
  if (generationStage == null) generationStage = OPEX_STAGE_COMPLETE;
  local doFreight = (generationStage == OPEX_STAGE_AIR_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  local doPaxRail = (generationStage == OPEX_STAGE_AIR_RAIL || generationStage == OPEX_STAGE_RAIL_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  local doRoad = (generationStage == OPEX_STAGE_ROUTE_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  local doAir = (generationStage == OPEX_STAGE_AIR_ONLY || generationStage == OPEX_STAGE_AIR_RAIL || generationStage == OPEX_STAGE_COMPLETE);
  local doWater = (generationStage == OPEX_STAGE_ROUTE_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  if (C121_CATALOG_AIR_FIRST_YEAR && C121_CATALOG_FIRST_YEAR_ACTIVE) {
    doFreight = false;
    doPaxRail = false;
    doRoad = false;
    doWater = false;
    doAir = true;
  }
  local paxBand = generationStage == OPEX_STAGE_AIR_RAIL ? PAX_BAND_AIR_RAIL
      : (generationStage == OPEX_STAGE_RAIL_ONLY ? PAX_BAND_RAIL_ONLY : PAX_BAND_ALL);
  local airBand = generationStage == OPEX_STAGE_AIR_ONLY ? PAX_BAND_AIR_ONLY
      : (generationStage == OPEX_STAGE_AIR_RAIL ? PAX_BAND_AIR_RAIL : PAX_BAND_ALL);
  if (DECISION_LOG) {
    OpexDecide("BOOTSTRAP_STAGE", "stage=" + generationStage
               + " freight=" + (doFreight ? 1 : 0) + " pax_rail=" + (doPaxRail ? 1 : 0)
               + " road=" + (doRoad ? 1 : 0) + " air=" + (doAir ? 1 : 0)
               + " freight_cargo=" + (freightCargo != null ? freightCargo : -1)
               + " freight_label=" + (freightCargo != null ? AICargo.GetCargoLabel(freightCargo) : "none")
               + " freight_price=" + (freightCargo != null ? AICargo.GetCargoIncome(freightCargo, 20, 0) : 0));
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_rail", "-");
  /* C41.22 : intervalles disjoints du chemin rail historique. */
  local railProfile = C41_RAIL_PORTFOLIO_PROFILE
      ? { generationOps = 0, generationCandidates = 0, topKCandidates = 0,
          insertOps = 0, insertedProjects = 0 } : null;
  local railGenerationMark = railProfile != null ? OpexOpsMeasureBegin() : null;
  local railCandidateProfile = (C41_RAIL_CANDIDATE_PROFILE || C41_RAIL_PAX_PROFILE || C41_RAIL_PAX_CANDIDATE_PROFILE || C41_RAIL_PAX_ECONOMICS_PROFILE || C41_RAIL_PAX_SPEED_PROFILE || C41_RAIL_PAX_SPEED_DETAIL_PROFILE || C41_RAIL_PAX_CRUISE_PROFILE || C41_RAIL_FREIGHT_PROFILE || C41_RAIL_FREIGHT_CANDIDATE_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE || C41_RAIL_FREIGHT_CRUISE_PROFILE || C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE || C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE || C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE)
      ? { paxOps = 0, freightOps = 0, topKOps = 0,
          paxPreparationOps = 0, paxPairTotalOps = 0, paxCandidateOps = 0,
          paxPairsScanned = 0, paxCandidateCalls = 0,
          paxSitableOps = 0, paxSitableCalls = 0, paxEconomicsOps = 0, paxEconomicsCalls = 0,
          paxEconomicsSetupOps = 0, paxEconomicsLoopOps = 0, paxEconomicsLoopCalls = 0,
          paxEconomicsPostOps = 0, paxSpeedOps = 0, paxSpeedCalls = 0,
          paxCorrectedSpeedCalls = 0, paxCruiseOps = 0, paxAccelerationOps = 0,
          paxIntegrationOps = 0, paxSpeedKeys = {}, paxSpeedUniqueKeys = 0,
          paxSpeedCacheableHits = 0, paxCruiseKeys = {}, paxCruiseCalls = 0,
          paxCruiseUniqueKeys = 0, paxCruiseCacheableHits = 0,
          freightPreparationOps = 0, freightIndustryOps = 0, freightTownOps = 0, freightTownGuardsOps = 0, freightTownGuardsCalls = 0, freightTownServiceOps = 0, freightTownServiceCalls = 0,
          freightIndustryCandidateOps = 0, freightIndustryCandidateCalls = 0,
          freightTownCandidateOps = 0, freightTownCandidateCalls = 0,
          freightEconomicsOps = 0, freightEconomicsCalls = 0,
          /* C41.34 : les trois phases de OpexLineEconomics, mais uniquement pour fret.
           * Ne pas reutiliser les compteurs pax : le meme helper sert aux deux familles. */
          freightEconomicsSetupOps = 0, freightEconomicsSetupCalls = 0,
          freightEconomicsLoopOps = 0, freightEconomicsLoopCalls = 0,
          freightEconomicsPostOps = 0, freightEconomicsPostCalls = 0,
          freightEconomicsReferenceOps = 0, freightEconomicsReferenceCalls = 0,
          freightEconomicsConsistOps = 0, freightEconomicsConsistCalls = 0,
          freightEconomicsCapitalOps = 0, freightEconomicsCapitalCalls = 0,
          freightEconomicsConsistInitialSpeedOps = 0, freightEconomicsConsistInitialSpeedCalls = 0,
          freightEconomicsConsistCorrectedSpeedOps = 0, freightEconomicsConsistCorrectedSpeedCalls = 0,
          freightCruiseKeys = {}, freightCruiseCalls = 0, freightCruiseUniqueKeys = 0,
          freightCruiseCacheableHits = 0,
          freightAccelerationOps = 0, freightAccelerationCalls = 0,
          freightIntegrationOps = 0, freightIntegrationCalls = 0,
          freightSpeedKeys = {}, freightSpeedCalls = 0, freightSpeedUniqueKeys = 0,
          freightSpeedCacheableHits = 0 } : null;
  local railPaxProfile = C41_RAIL_PAX_PROFILE ? railCandidateProfile : null;
  local railPaxCandidateProfile = (C41_RAIL_PAX_CANDIDATE_PROFILE || C41_RAIL_PAX_ECONOMICS_PROFILE || C41_RAIL_PAX_SPEED_PROFILE || C41_RAIL_PAX_SPEED_DETAIL_PROFILE || C41_RAIL_PAX_CRUISE_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE)
      ? railCandidateProfile : null;
  /* C41.30/C41.38 : caches epuises apres cette generation ; aucun moteur/cargo/terrain d'une
   * passe suivante ne peut reutiliser une valeur ancienne. Les tables pax/fret sont separees :
   * l'AB fret ne change donc pas la cadence pax. */
  local railPaxCruiseCache = C41_RAIL_PAX_CRUISE_CACHE ? {} : null;
  local railFreightCruiseCache = C41_RAIL_FREIGHT_CRUISE_CACHE ? {} : null;
  local rail;
  local deferRailReuseAdmission = doFreight && freightCargo != null
      && freightCargoOrder != null && freightCargoOrder.len() > 1;
  if (doPaxRail || doFreight) {
    local spRail = PROBE_SPAN_TRACE ? OpexSpanBegin("build.rail") : null;
    rail = OpexBuildCandidates(catalog, budget, lines, abandonedPairs, railCandidateProfile,
        railPaxProfile, railPaxCandidateProfile, railPaxCruiseCache, railFreightCruiseCache,
        doPaxRail, doFreight, paxBand, freightCargo, null, -1, deferRailReuseAdmission);
    if (spRail != null) OpexSpanEnd(spRail);
    if (priorProjects != null && ("rail" in priorProjects)
        && priorProjects.rail != null && ("candidates" in priorProjects.rail)) {
      local merged = [];
      foreach (c in priorProjects.rail.candidates) {
        /* Une passe pax de repli a pu avoir lieu a l'etape 0. L'etape pax
         * normale vient de la regenerer avec l'etat courant : ne conserver
         * ici que le fret herite pour ne pas dupliquer chaque paire pax. */
        local replaced = generationStage == OPEX_STAGE_AIR_RAIL && c.kind == "pax";
        if (!replaced && OpexStagedCandidateStillValid(c, lines, abandonedPairs)) {
          merged.append(c);
        }
      }
      foreach (c in rail.candidates) merged.append(c);
      rail.candidates = merged;
      rail.best = OpexTopK(merged, TOP_K);
      rail.all = merged.len();
    }
  } else if (priorProjects != null && ("rail" in priorProjects) && priorProjects.rail != null) {
    rail = priorProjects.rail;
    local liveRail = [];
    foreach (c in rail.candidates) {
      if (OpexStagedCandidateStillValid(c, lines, abandonedPairs)) liveRail.append(c);
    }
    rail.candidates = liveRail;
    rail.best = OpexTopK(liveRail, TOP_K);
    rail.all = liveRail.len();
  } else {
    rail = OpexEmptyRailCandidates();
  }
  /* Un cargo actif peut encore ne produire aucun candidat admissible (aucun
   * puits, distance, economie ou site). Comme pour le repli pax air->air+rail,
   * essayer immediatement les cargos suivants par prix, sans regenerer le pax
   * ni l'air deja calcules. Le premier lot fret non vide devient le lot reel
   * de ce portefeuille. */
  if (doFreight && freightCargo != null && freightCargoOrder != null
      && freightCargoOrder.len() > 1) {
    local hasFreight = false;
    foreach (candidate in rail.candidates) {
      if (candidate.kind == "freight") { hasFreight = true; break; }
    }
    if (!hasFreight) {
      local start = -1;
      for (local i = 0; i < freightCargoOrder.len(); i++) {
        if (freightCargoOrder[i] == freightCargo) { start = i; break; }
      }
      local tried = 1;
      for (local offset = 1; offset < freightCargoOrder.len(); offset++) {
        local idx = start >= 0 ? (start + offset) % freightCargoOrder.len() : offset - 1;
        local nextCargo = freightCargoOrder[idx];
        local spRailFb = PROBE_SPAN_TRACE ? OpexSpanBegin("build.rail") : null;
        local extraFreight = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
            railCandidateProfile, null, null, null, railFreightCruiseCache,
            false, true, PAX_BAND_ALL, nextCargo, null, -1, deferRailReuseAdmission);
        if (spRailFb != null) OpexSpanEnd(spRailFb);
        tried++;
        if (extraFreight.candidates.len() == 0) continue;
        rail = OpexRailSelectFreightReusePool(rail, extraFreight);
        rail = OpexMergeRailCandidateSet(rail, extraFreight, false);
        local previousCargo = freightCargo;
        freightCargo = nextCargo;
        hasFreight = true;
        if (DECISION_LOG) {
          OpexDecide("FREIGHT_CARGO_FALLBACK", "from=" + previousCargo
                     + " to=" + freightCargo + " label=" + AICargo.GetCargoLabel(freightCargo)
                     + " tried=" + tried + " candidates=" + extraFreight.candidates.len());
        }
        break;
      }
      if (!hasFreight && DECISION_LOG) {
        OpexDecide("FREIGHT_CARGO_FALLBACK", "from=" + freightCargo
                   + " to=none tried=" + tried + " candidates=0");
      }
    }
    rail = OpexRailOriginReuseFinalize(rail, TOP_K, catalog, budget, lines,
        railCandidateProfile, railPaxProfile, railPaxCandidateProfile,
        railPaxCruiseCache, railFreightCruiseCache);
  }
  if (railProfile != null) {
    railProfile.generationOps = OpexOpsMeasureEnd(railGenerationMark);
    railProfile.generationCandidates = rail.candidates.len();
    railProfile.topKCandidates = rail.best.len();
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_rail", "-");
  if (cost != null) {
    cost.railOps += OpexOpsMeasureEnd(costMark);
    cost.railCandidates = rail.candidates.len();
    costMark = OpexOpsMeasureBegin();
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_road", "-");
  /* C41.16/C41.17 : mesure seulement les etapes de generation route pendant la passe historique. */
  local roadProfile = (C41_ROAD_CANDIDATE_PROFILE || C41_ROAD_FREIGHT_PROFILE || C41_ROAD_FREIGHT_TOWN_PROFILE)
      ? { paxOps = 0, freightOps = 0, topKOps = 0,
          freightPreparationOps = 0, freightIndustryOps = 0, freightTownOps = 0,
          freightTownScanned = 0, freightTownAcceptanceHits = 0, freightTownAcceptanceMisses = 0,
          freightTownAcceptanceOps = 0, freightTownAcceptedPairs = 0, freightTownCandidateOps = 0 } : null;
  local road;
  if (doRoad && ROAD_BUILD_ENABLED) {
    local spRoad = PROBE_SPAN_TRACE ? OpexSpanBegin("build.road") : null;
    road = OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs, roadProfile, freightCargo);
    if (spRoad != null) OpexSpanEnd(spRoad);
  } else if (priorProjects != null && ("road" in priorProjects) && priorProjects.road != null) {
    road = priorProjects.road;
    local liveRoad = [];
    foreach (c in road.candidates) {
      if (OpexStagedCandidateStillValid(c, lines, abandonedPairs)) liveRoad.append(c);
    }
    road.candidates = liveRoad;
    road.best = OpexTopK(liveRoad, ROAD_TOP_K);
    road.all = liveRoad.len();
  } else {
    road = OpexProjectEmptyRoad();
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_road", "-");
  if (cost != null) {
    cost.roadOps += OpexOpsMeasureEnd(costMark);
    cost.roadCandidates = road.candidates.len();
    costMark = OpexOpsMeasureBegin();
  }

  local spCapital = PROBE_SPAN_TRACE ? OpexSpanBegin("build.capital") : null;
  local capitalBudget = OpexAvailableCapital();
  if (spCapital != null) OpexSpanEnd(spCapital);
  local capitalBudgetDate = AIDate.GetCurrentDate();

  local airPlan = null;
  local airPlans = [];
  local airOps = 0;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_air", "-");
  if (doAir && ((catalog.airCombos != null && catalog.airCombos.len() > 0) || catalog.airport != null)) {
    if (airOverride != null && typeof airOverride == "table"
        && ("complete" in airOverride) && airOverride.complete) {
      airPlan = ("airPlan" in airOverride) ? airOverride.airPlan : null;
      if (("airPlans" in airOverride) && airOverride.airPlans != null) {
        foreach (plan in airOverride.airPlans) airPlans.append(plan);
      }
      airOps = ("airOps" in airOverride) ? airOverride.airOps : 0;
    } else {
      budget.begin();
      /* C80 tranche 5 : la generation complete refait tous les choix d'avion et les memorise. */
      if (C80_AIR_CHOICE_MEMO) {
        AIR_CHOICE_MEMO = {};
        AIR_CHOICE_MEMO_STATE = 1;
      }
      airPlan = OpexAirPlans(catalog, lines, 0, airPlans, abandonedPairs, airBand);
      AIR_CHOICE_MEMO_STATE = 0;
      airOps = budget.end("project_air");
    }
    if (generationStage == OPEX_STAGE_AIR_RAIL && priorProjects != null
        && ("airPlans" in priorProjects) && priorProjects.airPlans != null) {
      foreach (plan in priorProjects.airPlans) {
        if (OpexStagedAirPlanStillValid(catalog, plan, lines, abandonedPairs)) airPlans.append(plan);
      }
      if (airPlans.len() > 0) airPlan = airPlans[0];
    }
  } else if (!doAir && priorProjects != null) {
    airPlan = ("airPlan" in priorProjects) ? priorProjects.airPlan : null;
    if (("airPlans" in priorProjects) && priorProjects.airPlans != null) {
      foreach (plan in priorProjects.airPlans) {
        if (OpexStagedAirPlanStillValid(catalog, plan, lines, abandonedPairs)) airPlans.append(plan);
      }
    }
    airPlan = airPlans.len() > 0 ? airPlans[0] : null;
    airOps = ("airPlanningOpcodes" in priorProjects) ? priorProjects.airPlanningOpcodes : 0;
  }

  /* L'air reste le pax prioritaire de l'etape initiale. Une liste vide signifie
   * qu'aucun plan pax aerien n'a franchi ses filtres ; dans ce seul cas, ouvrir
   * le rail pax maintenant plutot que laisser un premier vivier 100 % fret. */
  if (generationStage == OPEX_STAGE_AIR_ONLY && airPlans.len() == 0) {
    if (airOverride == null || !("complete" in airOverride) || !airOverride.complete) {
      budget.begin();
      airPlan = OpexAirPlans(catalog, lines, 0, airPlans, abandonedPairs, PAX_BAND_AIR_RAIL);
      airOps += budget.end("project_air_overlap_fallback");
    }
    local spPaxFb = PROBE_SPAN_TRACE ? OpexSpanBegin("build.rail") : null;
    local paxFallback = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
        railCandidateProfile, railPaxProfile, railPaxCandidateProfile,
        railPaxCruiseCache, railFreightCruiseCache, true, false, PAX_BAND_AIR_RAIL);
    if (spPaxFb != null) OpexSpanEnd(spPaxFb);
    rail = OpexMergeRailCandidateSet(rail, paxFallback);
    if (railProfile != null) {
      railProfile.generationCandidates = rail.candidates.len();
      railProfile.topKCandidates = rail.best.len();
    }
    if (DECISION_LOG) {
      OpexDecide("BOOTSTRAP_PAX_FALLBACK", "air=0 rail_pax=" + paxFallback.candidates.len());
    }
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_air", "-");
  if (cost != null) {
    cost.airOps += OpexOpsMeasureEnd(costMark);
    cost.airPlans = airPlans.len();
    costMark = OpexOpsMeasureBegin();
  }

  local waterPlan = null;
  local waterPlans = [];
  local waterOps = 0;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_water", "-");
  if (doWater && catalog.ships.len() > 0 && catalog.paxCargo >= 0) {
    budget.begin();
    local spWater = PROBE_SPAN_TRACE ? OpexSpanBegin("build.water") : null;
    waterPlan = OpexWaterPlans(catalog, lines, waterPlans, null, WATER_OPCODE_COMPAT_FALSE ? null : null);
    if (spWater != null) OpexSpanEnd(spWater);
    waterOps = budget.end("project_water");
  } else if (!doWater && priorProjects != null) {
    waterPlan = ("waterPlan" in priorProjects) ? priorProjects.waterPlan : null;
    if (("waterPlans" in priorProjects) && priorProjects.waterPlans != null) {
      foreach (plan in priorProjects.waterPlans) {
        if (OpexStagedWaterPlanStillValid(catalog, plan, lines, abandonedPairs)) waterPlans.append(plan);
      }
    }
    waterPlan = waterPlans.len() > 0 ? waterPlans[0] : null;
    waterOps = ("waterPlanningOpcodes" in priorProjects) ? priorProjects.waterPlanningOpcodes : 0;
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_water", "-");
  if (cost != null) {
    cost.waterOps += OpexOpsMeasureEnd(costMark);
    cost.waterPlans = waterPlans.len();
    costMark = OpexOpsMeasureBegin();
  }

  local stats = {
    modeCandidates = 0, modeAlternatives = 0, modeReplaced = 0,
    odProjects = 0, budgetConsidered = 0, budgetSelected = 0,
    budgetRejected = 0, selectedRevenue = 0, selectedCapital = 0,
    selectionPoolCapital = 0, nextProjectCapital = 0,
    knapsackNodes = 0, knapsackExact = false, poolInfundable = 0,
  };
  if (railProfile != null) stats.railProfile <- railProfile;
  /* Branchement explicite plutot qu'une fonction passee dans un local : ce depot a deja paye
   * plusieurs echecs Squirrel silencieux, et ici une IA morte ressemblerait exactement a une IA
   * nulle au banc. */
  /* Le cout de decouverte mesure couvre TOUT le balayage (OpexAirPlans / OpexWaterPlans), pas un
   * plan en particulier. Le passer tel quel a chaque plan faisait rapporter N fois le meme cout
   * dans planningOpcodes, donc dans les panneaux OA| et eau : surestimation d'un facteur N, et
   * corruption de la mesure meme qui servirait a pricer la decouverte aerienne
   * (docs/taches.md S0 septies). On repartit desormais la depense entre les plans qu'elle a
   * produits. */
  local airOpsPerPlan = (airPlans.len() > 0) ? airOps / airPlans.len() : airOps;
  local waterOpsPerPlan = (waterPlans.len() > 0) ? waterOps / waterPlans.len() : waterOps;

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_assembly", "-");
  local spAssembly = PROBE_SPAN_TRACE ? OpexSpanBegin("build.assembly") : null;
  local winners = {};
  local abandonFiltered = 0;
    local railInsertMark = railProfile != null ? OpexOpsMeasureBegin() : null;
    local railProjectsBefore = stats.modeCandidates;
    foreach (candidate in rail.candidates) {
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) {
        abandonFiltered++;
        continue;
      }
      OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate), stats);
    }
    if (railProfile != null) {
      railProfile.insertOps = OpexOpsMeasureEnd(railInsertMark);
      railProfile.insertedProjects = stats.modeCandidates - railProjectsBefore;
    }
    foreach (candidate in road.candidates) {
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) {
        abandonFiltered++;
        continue;
      }
      OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate), stats);
    }
    if (V139_FEEDER_BUS) {
      local feeders = OpexBuildFeederCandidates(catalog, lines);
      foreach (candidate in feeders) {
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) {
          abandonFiltered++;
          continue;
        }
        OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate), stats);
      }
    }
    foreach (plan in airPlans) {
      OpexProjectRememberAll(winners, OpexProjectFromAir(catalog, plan, airOpsPerPlan), stats);
    }
    foreach (plan in waterPlans) {
      OpexProjectRememberAll(winners, OpexProjectFromWater(catalog, plan, waterOpsPerPlan), stats);
    }
    if (fleetPlan != null) {
      foreach (entry in fleetPlan) {
        local p = OpexProjectFromFleet(entry);
        if (p != null) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordProduced("fleet", 1, 1);
          OpexProjectRememberAll(winners, p, stats);
        } else if (C69_BOTTLENECK_PROBE) {
          OpexC73RecordRejection("fleet", "profit_nonpositive", 1);
        }
      }
    }
    /* C77 : une regeneration complete (celle de C76 comprise) recree les candidats des offres de
     * subvention suivies, sinon elle effacerait ceux que l'offre avait injectes. L'appelant ne
     * transmet activeSubsidies que sous C77. */
    if (activeSubsidies != null && activeSubsidies.len() > 0
        && !(C121_CATALOG_AIR_FIRST_YEAR && C121_CATALOG_FIRST_YEAR_ACTIVE)) {
      foreach (candidate in OpexGenerateSubsidyCandidates(catalog, lines, activeSubsidies, stats, abandonedPairs)) {
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) {
          abandonFiltered++;
          continue;
        }
        OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate), stats);
      }
    }
  if (spAssembly != null) OpexSpanEnd(spAssembly);

  local funded = null;
  if (cost != null) {
    cost.assemblyOps += OpexOpsMeasureEnd(costMark);
    cost.modeAlternatives = stats.modeCandidates;
  }
  local selectionLight = CATALOG_COST_PROBE ? OpexSelectionLightBegin() : null;
  local opsMark = OpexOpsMeasureBegin();
  /* Toutes les alternatives de tous les couples, aplaties : c'est le test de capital qui
   * tranchera, pas une election modale prealable au ratio. */
  local alternatives = [];
  foreach (key, list in winners) {
    stats.odProjects++;
    foreach (project in list) alternatives.push(project);
  }
  if (C80_RAIL_STOCK_GATE) {
    alternatives = OpexRailStockMergeAlternatives(alternatives, railReadyStock, stats);
    if (C80_RAIL_STOCK_WORKER) winners = OpexRailStockStripCandidateGroups(winners);
  }
  if (C121_AIR_FIRST_YEAR_RAIL_PREP && !C121_CATALOG_FIRST_YEAR_ACTIVE) {
    alternatives = OpexRailPrepMergeAlternatives(alternatives, railReadyStock);
  }
  alternatives = OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines);
  funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);
  if (RAIL_FAILURE_AUDIT) OpexRailPortfolioAudit("full", alternatives, funded, capitalBudget);
  stats.budgetConsidered = alternatives.len();
  stats.budgetSelected = funded.len();
  stats.budgetRejected = alternatives.len() - funded.len();
  stats.knapsackNodes = 0;
  stats.knapsackExact = false;
  stats.selectionOpcodes <- OpexOpsMeasureEnd(opsMark);
  if (selectionLight != null) OpexSelectionLightEnd(selectionLight, "full",
      stats.selectionOpcodes, alternatives.len(), funded.len());
  if (cost != null) {
    cost.selectionOps += stats.selectionOpcodes;
    cost.considered = alternatives.len();
    cost.selected = funded.len();
  }
  OpexB6LogSelectionCausality("build", alternatives, funded, capitalBudget, capitalBudgetDate);

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

  local stampProjects = {
    rail = rail, road = road, airPlans = airPlans, waterPlans = waterPlans
  };
  local stampExtras = {
    abandonFiltered = abandonFiltered,
    abandonedPairsCount = (abandonedPairs != null) ? abandonedPairs.len() : 0,
    cacheScanned = 0,
    cacheRetained = 0
  };
  OpexProjectsStampSelectionStats(stats, stampProjects, alternatives, funded, capitalBudget, stampExtras);

  if (DECISION_LOG) {
    local vivierPool = [];
    foreach (key, list in winners) {
      foreach (project in list) vivierPool.push(project);
    }
    OpexLogVivier("build", vivierPool, stats, capitalBudget, remaining);
  }

  /* Le vivier est conservé en permanence par le chemin incrémental adopté. */
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_assembly", "-");
  local ret = {
    all = stats.odProjects, best = funded, stats = stats,
    capitalBudget = capitalBudget, capitalRemaining = remaining,
    candidateGroups = winners,
    rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
    airPlans = airPlans, waterPlans = waterPlans,
    airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
    generationStage = generationStage,
    freightCargo = freightCargo,
  };
  if (C80_RAIL_STOCK_GATE) ret.railReadyStock <- railReadyStock;
  else if (C121_AIR_FIRST_YEAR_RAIL_PREP && railReadyStock != null) ret.railReadyStock <- railReadyStock;
  if (C69_BOTTLENECK_PROBE) {
    ret.c69Best <- ::C69_LAST_AFFORDABLE;
    ret.c69KDecData <- ::C69_LAST_KDEC_DATA;
  }
  return ret;
}
