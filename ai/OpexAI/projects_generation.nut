/* Extrait de projects.nut (R14) : Generation par mode, validation des candidats et porte stock rail. Requis depuis projects.nut. */

function OpexGenerateModeProjects(projects, catalog, budget, lines, abandonedPairs, mode,
                                  waterSiteCatalog = null, entityKind = null, entityId = -1)
{
  local generated = {
    projects = [],
    rail = null, road = null,
    airPlan = null, waterPlan = null,
    airPlans = [], waterPlans = [],
    freightCargo = null,
  };
  local freightCargo = (projects != null && ("freightCargo" in projects))
      ? projects.freightCargo : null;
  if (freightCargo == null) {
    local freightOrder = OpexFreightCargoOrder(catalog);
    if (freightOrder.len() > 0) freightCargo = freightOrder[0];
  }
  generated.freightCargo = freightCargo;
  local targeted = entityKind != null && entityId >= 0;

  if (mode == "rail") {
    local generatePax = !targeted || entityKind == "town";
    local generateFreight = !targeted || entityKind == "industry";
    local freightOrder = OpexFreightCargoOrder(catalog);
    local deferRailReuseAdmission = generateFreight && freightCargo != null
        && freightOrder.len() > 1;
    local rail = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
        null, null, null, null, null, generatePax, generateFreight, PAX_BAND_ALL,
        freightCargo, entityKind, entityId, deferRailReuseAdmission);
    local hasFreight = false;
    foreach (candidate in rail.candidates) {
      if (candidate.kind == "freight") { hasFreight = true; break; }
    }
    if (!hasFreight && freightCargo != null && freightOrder.len() > 1) {
      local start = -1;
      for (local i = 0; i < freightOrder.len(); i++) {
        if (freightOrder[i] == freightCargo) { start = i; break; }
      }
      for (local offset = 1; offset < freightOrder.len(); offset++) {
        local idx = start >= 0 ? (start + offset) % freightOrder.len() : offset - 1;
        local fallbackCargo = freightOrder[idx];
        local impossibleTargetCargo = targeted && entityKind == "industry"
            && !OpexRailTargetIndustryHasStructuralPairForCargo(catalog, entityId, fallbackCargo);
        if (RAIL_TARGET_CARGO_PREFILTER && impossibleTargetCargo) {
          if (DECISION_LOG) {
            OpexDecide("RAIL_TARGET_CARGO_SKIP", "industry=" + entityId
                       + " cargo=" + fallbackCargo + " reason=no_structural_pair");
          }
          continue;
        }
        local extra = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
            null, null, null, null, null, false, true, PAX_BAND_ALL, fallbackCargo,
            entityKind, entityId, deferRailReuseAdmission);
        if (DECISION_LOG && impossibleTargetCargo) {
          OpexDecide("RAIL_TARGET_CARGO_SHADOW", "industry=" + entityId
                     + " cargo=" + fallbackCargo + " opcodes=" + extra.opcodes
                     + " candidates=" + extra.candidates.len());
        }
        if (extra.candidates.len() == 0) continue;
        rail = OpexRailSelectFreightReusePool(rail, extra);
        rail = OpexMergeRailCandidateSet(rail, extra, false);
        freightCargo = fallbackCargo;
        generated.freightCargo = freightCargo;
        /* Sous C77, le mode route est traite a la tranche suivante : publier le fallback reel
         * uniquement sur cette regeneration ciblee, sans toucher au chemin normal. */
        if (targeted) projects.freightCargo = freightCargo;
        break;
      }
    }
    rail = OpexRailOriginReuseFinalize(rail, TOP_K, catalog, budget, lines);
    generated.rail = rail;
    foreach (candidate in rail.candidates) {
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null
          && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
      local p = OpexProjectFromCandidate(candidate);
      if (p != null) generated.projects.append(p);
    }
  } else if (mode == "road") {
    local road = ROAD_BUILD_ENABLED
        ? OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs, null, freightCargo,
                                  entityKind, entityId)
        : OpexProjectEmptyRoad();
    generated.road = road;
    foreach (candidate in road.candidates) {
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null
          && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
      local p = OpexProjectFromCandidate(candidate);
      if (p != null) generated.projects.append(p);
    }
  } else if (mode == "air") {
    local mark = OpexOpsMeasureBegin();
    local plans = [];
    if (C80_AIR_CHOICE_MEMO) AIR_CHOICE_MEMO_STATE = 2;
    local best = OpexAirPlans(catalog, lines, 0, plans, abandonedPairs, PAX_BAND_ALL,
                              entityKind == "town" ? entityId : -1);
    AIR_CHOICE_MEMO_STATE = 0;
    local ops = OpexOpsMeasureEnd(mark);
    local perPlan = plans.len() > 0 ? ops / plans.len() : ops;
    generated.airPlan = best;
    generated.airPlans = plans;
    foreach (plan in plans) {
      local p = OpexProjectFromAir(catalog, plan, perPlan);
      if (p != null) generated.projects.append(p);
    }
  } else if (mode == "water") {
    local mark = OpexOpsMeasureBegin();
    local plans = [];
    local best = OpexWaterPlans(catalog, lines, plans, null,
        null);
    local ops = OpexOpsMeasureEnd(mark);
    local perPlan = plans.len() > 0 ? ops / plans.len() : ops;
    generated.waterPlan = best;
    generated.waterPlans = plans;
    foreach (plan in plans) {
      local p = OpexProjectFromWater(catalog, plan, perPlan);
      if (p != null) generated.projects.append(p);
    }
  }
  return generated;
}

function OpexApplyGeneratedModeProjects(projects, generated, abandonedPairs, mode,
                                        entityKind = null, entityId = -1, lines = null)
{
  if (projects == null || !(("candidateGroups" in projects)) || projects.candidateGroups == null) {
    return projects;
  }
  local targeted = entityKind != null && entityId >= 0;
  local winners = {};
  local scratch = { modeCandidates = 0, modeAlternatives = 0 };

  foreach (groupKey, entry in projects.candidateGroups) {
    local list = (typeof entry == "array") ? entry : [entry];
    foreach (project in list) {
      if (project == null) continue;
      local remove = project.mode == mode && !OpexProjectIsPersistentSpecial(project);
      if (remove && targeted) remove = OpexProjectTouchesEntity(project, entityKind, entityId);
      if (!remove) OpexProjectRememberAll(winners, project, scratch);
    }
  }

  foreach (project in generated.projects) {
    if (targeted && !OpexProjectTouchesEntity(project, entityKind, entityId)) continue;
    OpexProjectRememberAll(winners, project, scratch);
  }

  projects.candidateGroups = winners;
  if (!targeted) {
    if (mode == "rail") {
      projects.rail = generated.rail;
      projects.freightCargo = generated.freightCargo;
    } else if (mode == "road") {
      projects.road = generated.road;
      projects.freightCargo = generated.freightCargo;
    } else if (mode == "air") {
      projects.airPlan = generated.airPlan;
      projects.airPlans = generated.airPlans;
    } else if (mode == "water") {
      projects.waterPlan = generated.waterPlan;
      projects.waterPlans = generated.waterPlans;
    }
  }
  OpexProjectsRecountGroups(projects);
  return OpexReselectProjects(projects, OpexAvailableCapital(), abandonedPairs, lines);
}

function OpexRegenerateModeProjects(projects, catalog, budget, lines, abandonedPairs, mode,
                                    waterSiteCatalog = null, entityKind = null, entityId = -1)
{
  if (projects == null || !(("candidateGroups" in projects)) || projects.candidateGroups == null) {
    return projects;
  }
  local spMode = PROBE_SPAN_TRACE ? OpexSpanBegin("regen.mode") : null;
  local generated = OpexGenerateModeProjects(projects, catalog, budget, lines, abandonedPairs,
                                             mode, waterSiteCatalog, entityKind, entityId);
  local applied = OpexApplyGeneratedModeProjects(projects, generated, abandonedPairs, mode,
                                        entityKind, entityId, lines);
  if (spMode != null) OpexSpanEnd(spMode);
  return applied;
}

/* C78.4 : variante reprenable du seul mode AIR pour le worker C77. Le scan de sites
 * d'un combo reste atomique, mais la boucle quadratique des paires rend la main sur
 * opsBudget/deadlineTick et reprend exactement au curseur combo/a/b. */
function OpexRegenerateAirProjectsSlice(projects, catalog, budget, lines, abandonedPairs,
                                        sliceState, opsBudget, deadlineTick,
                                        entityKind = null, entityId = -1, c83Race = false)
{
  if (projects == null || !(("candidateGroups" in projects)) || projects.candidateGroups == null) {
    return { done = true, projects = projects };
  }
  if (sliceState == null || typeof sliceState != "table") {
    return { done = true, projects = projects };
  }
  local spAirSlice = PROBE_SPAN_TRACE ? OpexSpanBegin("regen.air_slice") : null;
  if (!("plans" in sliceState)) sliceState.plans <- [];
  if (!("airCursor" in sliceState)) sliceState.airCursor <- {};
  if (!("ops" in sliceState)) sliceState.ops <- 0;

  local mark = OpexOpsMeasureBegin();
  if (c83Race && !("c83StartTick" in sliceState)) {
    sliceState.c83StartTick <- AIController.GetTick();
    if (C83_LOCAL_REPAIR) {
      sliceState.airCursor.c83Repair <- OpexC83RepairSnapshot(projects);
    }
  }
  if (C80_AIR_CHOICE_MEMO) AIR_CHOICE_MEMO_STATE = 2;
  local best = OpexAirPlans(catalog, lines, 0, sliceState.plans, abandonedPairs, PAX_BAND_ALL,
                            entityKind == "town" ? entityId : -1,
                            sliceState.airCursor, opsBudget, deadlineTick);
  AIR_CHOICE_MEMO_STATE = 0;
  sliceState.ops += OpexOpsMeasureEnd(mark);
  if (!("done" in sliceState.airCursor) || !sliceState.airCursor.done) {
    if (spAirSlice != null) OpexSpanEnd(spAirSlice);
    return { done = false, projects = projects };
  }

  local generated = {
    projects = [],
    rail = null, road = null,
    airPlan = best, waterPlan = null,
    airPlans = sliceState.plans, waterPlans = [],
    freightCargo = (projects != null && ("freightCargo" in projects))
        ? projects.freightCargo : null,
  };
  local perPlan = sliceState.plans.len() > 0 ? sliceState.ops / sliceState.plans.len() : sliceState.ops;
  foreach (plan in sliceState.plans) {
    local p = OpexProjectFromAir(catalog, plan, perPlan);
    if (p != null) generated.projects.append(p);
  }
  if (c83Race) {
    local repair = ("c83Repair" in sliceState.airCursor) ? sliceState.airCursor.c83Repair : null;
    AILog.Info("C83_LOCAL_REPAIR enabled=" + (C83_LOCAL_REPAIR ? 1 : 0)
        + " town=" + entityId + " local=" + (repair != null ? repair.localCombos : 0)
        + " fallback=" + (repair != null ? repair.fallbackCombos : 0)
        + " kept=" + (repair != null ? repair.targetKept : 0)
        + " searched=" + (repair != null ? repair.targetSearched : 0)
        + " partners=" + (repair != null ? repair.partners : 0)
        + " ops=" + sliceState.ops + " ticks=" + (AIController.GetTick() - sliceState.c83StartTick));
  }
  local appliedAir = OpexApplyGeneratedModeProjects(projects, generated, abandonedPairs, "air",
                                              entityKind, entityId, lines);
  if (spAirSlice != null) OpexSpanEnd(spAirSlice);
  return {
    done = true,
    projects = appliedAir,
  };
}

function OpexCandidateIsAbandoned(p, abandonedPairs)
{
  if (p == null || abandonedPairs == null) return false;
  local mode = ("mode" in p) ? p.mode : "";
  if (mode == "air") {
    local plan = ("payload" in p) ? p.payload : null;
    if (plan != null && ("siteA" in plan) && ("siteB" in plan)) {
      local siteAKey = OpexAirSitePaddingKey(plan.siteA, plan.airport.type);
      local siteBKey = OpexAirSitePaddingKey(plan.siteB, plan.airport.type);
      local townAKey = OpexAirTownPaddingKey(plan.siteA);
      local townBKey = OpexAirTownPaddingKey(plan.siteB);
      if (OpexAirPairIsAbandoned(abandonedPairs, plan.siteA, plan.siteB)
          || (OPEX_AIR_TOWN_PAD && ((!(("reuseA" in plan) && plan.reuseA) && (townAKey in abandonedPairs))
              || (!(("reuseB" in plan) && plan.reuseB) && (townBKey in abandonedPairs))))
          || (OPEX_AIR_SITE_PAD && ((siteAKey in abandonedPairs) || (siteBKey in abandonedPairs)))) return true;
    }
  } else if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (mode == "road" || mode == "rail")) {
    if (("payload" in p) && p.payload != null) {
      local aKey = OpexAbandonedPairKey(p.payload);
      if (aKey in abandonedPairs) return true;
    }
  }
  return false;
}

/* C36.1 : Revalidation rapide d'un candidat deja en memoire contre this._lines.
 * Verifie qu'aucune extremite n'est devenue invalide, qu'aucune ligne identique n'a ete batie,
 * et que les contraintes physiques du mode tiennent toujours. */
/* C36.1 : Revalidation rapide d'un candidat deja en memoire contre this._lines. */
function OpexCandidateStillValid(p, lines, abandonedPairs = null)
{
  if (p == null) return false;
  local mode = p.mode;

  /* 0. Candidat abandonne (echec de trace ou depot) */
  if (OpexCandidateIsAbandoned(p, abandonedPairs)) return false;

  if (mode == "road" && ("payload" in p) && p.payload != null &&
      ("isRoadExtension" in p.payload) && p.payload.isRoadExtension) {
    return false;
  }

  /* 1. Doublon exact avec une ligne deja batie */
  foreach (line in lines) {
    if (("cargo" in line) && line.cargo == p.cargo &&
        ("originA" in line) && ("originB" in line) &&
        ((line.originA == p.src && line.originB == p.dst) ||
         (line.originA == p.dst && line.originB == p.src))) {
      return false;
    }
  }

  /* 2. Mode route */
  if (mode == "road") {
    local isSubsidy = (("payload" in p) && p.payload != null &&
                       ("isSubsidy" in p.payload) && p.payload.isSubsidy);
    if (isSubsidy) {
      local subId = p.payload.subsidyId;
      if (!AISubsidy.IsValidSubsidy(subId) || AISubsidy.IsAwarded(subId)) return false;
      local today = AIDate.GetCurrentDate();
      local oneWay = ("oneWayDays" in p.payload) ? p.payload.oneWayDays : -1;
      local chantier = ("chantierDays" in p.payload) ? p.payload.chantierDays : OpexSubsidyChantierDays(oneWay);
      if (AISubsidy.GetExpireDate(subId) - today < chantier) return false;
      return true;
    }
    if (p.kind == "pax") {
      local endpoints = OpexGetCandidateTownEndpoints(p.payload);
      if ((endpoints.srcTown >= 0 && OpexTownBusPaxServed(lines, endpoints.srcTown)) ||
          (endpoints.dstTown >= 0 && OpexTownBusPaxServed(lines, endpoints.dstTown))) return false;
    }
      if (p.kind == "pax") {
        local srcServed = OpexOriginServed(lines, p.src, true);
        local dstServed = OpexOriginServed(lines, p.dst, true);
        local isOriginBlocked = srcServed || dstServed;

        if (C55_PAX_TRACE_PROBE) {
          OpexC55PaxTraceObserveRevalidated(isOriginBlocked);
        }

          if (C55_ORIGIN_RELAX_PROBE) {
            OpexC55OriginRelaxObserve("pax", lines, p.src, p.dst, srcServed, dstServed);
          }
          if (isOriginBlocked) return false;
          if (OpexRoadPairServed(lines, p.src, p.dst)) return false;
      } else {
        /* Fret routier */
        if (C55_FREIGHT_ORIGIN_RELAX) {
          local srcServed = OpexOriginServed(lines, p.src, true);
          local dstServed = OpexOriginServed(lines, p.dst, true);
          if (srcServed && dstServed) return false;
          /* Une seule paire est revalidee : une boucle directe evite de construire un index. */
          if (OpexRoadFreightBusy(lines, p.cargo, p.src) ||
              OpexRoadFreightBusy(lines, p.cargo, p.dst)) return false;
        } else if (C55_ORIGIN_RELAX_PROBE) {
          local srcServed = OpexOriginServed(lines, p.src, true);
          local dstServed = OpexOriginServed(lines, p.dst, true);
          OpexC55OriginRelaxObserve("freight", lines, p.src, p.dst, srcServed, dstServed);
          if (srcServed || dstServed) return false;
        } else {
          if (OpexOriginServed(lines, p.src, true)) return false;
          if (OpexOriginServed(lines, p.dst, true)) return false;
        }
      local towns = OpexGetCandidateTownEndpoints(p);
      if (C60_TOWN_RATING_PROBE) {
        if (towns.srcTown >= 0) OpexC60ObserveTownRating("road", "incremental_valid", towns.srcTown);
        if (towns.dstTown >= 0) OpexC60ObserveTownRating("road", "incremental_valid", towns.dstTown);
      }
    }
    if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
    return true;
  }

  /* 3. Mode rail : les deux extremites servies excluent la ligne */
  if (mode == "rail") {
    local towns = OpexGetCandidateTownEndpoints(p);
    if (C60_TOWN_RATING_PROBE) {
      if (towns.srcTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.srcTown);
      if (towns.dstTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.dstTown);
    }
    if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
    if (OpexOriginServed(lines, p.src, false) && OpexOriginServed(lines, p.dst, false)) {
      return false;
    }
    return true;
  }

  /* 4. Mode aerien : validite du plan de lot et constructibilite des sites */
  if (mode == "air") {
    local plan = p.payload;
    if (plan == null) return false;
    if (C60_TOWN_RATING_PROBE) {
      if (("siteA" in plan) && ("town" in plan.siteA)) OpexC60ObserveTownRating("air", "incremental_valid", plan.siteA.town.id);
      if ("siteB" in plan && ("town" in plan.siteB)) OpexC60ObserveTownRating("air", "incremental_valid", plan.siteB.town.id);
    }
    if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
    if (!OpexAirBatchPlanStillLive(plan, lines)) return false;
    if (!OpexAirBatchSiteStillBuildable(plan.siteA, plan.airport, plan.plane,
                                         ("reuseA" in plan) && plan.reuseA)) {
      return false;
    }
    if (!OpexAirBatchSiteStillBuildable(plan.siteB, plan.airport, plan.plane,
                                         ("reuseB" in plan) && plan.reuseB)) {
      return false;
    }
    return true;
  }

  /* 5. Mode maritime : dock constructible */
  if (mode == "water") {
    local plan = p.payload;
    if (plan == null || !("siteA" in plan) || !("siteB" in plan)) return false;
    if (!OpexWaterBatchSiteStillBuildable(plan.siteA) ||
        !OpexWaterBatchSiteStillBuildable(plan.siteB)) {
      return false;
    }
    return true;
  }

  return true;
}

/* C36.1 : Point d'entree unifie de revalidation incrementale. */
function OpexIncrementalCandidateStillValid(p, lines, abandonedPairs = null)
{
  return OpexCandidateStillValid(p, lines, abandonedPairs);
}

/* C78.2 : les sites AIR sont des predictions faites pendant un scan qui peut
 * suspendre plusieurs fois. Juste avant tout classement, retirer les plans dont
 * une extremite est devenue impossible ou dont la paire a ete abandonnee.
 * Plusieurs projets peuvent partager la meme extremite : une seule sonde par
 * site/type/reuse suffit pour toute la selection. */
function OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs = null, lines = null)
{
  local live = [];
  local siteValidity = {};
  local stationLimitedTowns = {};
  local c120InputAir = 0;
  local c120FilteredAir = 0;
  foreach (project in alternatives) {
    if (project != null && ("mode" in project) && project.mode == "air") {
      if (C120_AIR_TERRITORIAL_RANKING) c120InputAir++;
      if (!("payload" in project) || project.payload == null
          || OpexCandidateIsAbandoned(project, abandonedPairs)) {
        if (C120_AIR_TERRITORIAL_RANKING) c120FilteredAir++;
        continue;
      }
      local plan = project.payload;
      if (!("siteA" in plan) || !("siteB" in plan) || !("airport" in plan) || !("plane" in plan)) {
        if (C120_AIR_TERRITORIAL_RANKING) c120FilteredAir++;
        continue;
      }
      if (C83_FIXES && lines != null && !OpexAirBatchPlanStillLive(plan, lines)) {
        if (C120_AIR_TERRITORIAL_RANKING) c120FilteredAir++;
        continue;
      }

      local reuseA = ("reuseA" in plan) && plan.reuseA;
      local reuseB = ("reuseB" in plan) && plan.reuseB;
      local keyA = (reuseA ? "R|" : "N|") + plan.airport.type + "|" + plan.plane.planeType + "|" + plan.siteA.anchor;
      local keyB = (reuseB ? "R|" : "N|") + plan.airport.type + "|" + plan.plane.planeType + "|" + plan.siteB.anchor;
      if (!(keyA in siteValidity)) {
        siteValidity.rawset(keyA, OpexAirSiteStillBuildable(
            plan.siteA, plan.airport, plan.plane, reuseA, stationLimitedTowns));
      }
      if (!siteValidity[keyA]) {
        if (C120_AIR_TERRITORIAL_RANKING) c120FilteredAir++;
        continue;
      }
      if (!(keyB in siteValidity)) {
        siteValidity.rawset(keyB, OpexAirSiteStillBuildable(
            plan.siteB, plan.airport, plan.plane, reuseB, stationLimitedTowns));
      }
      if (!siteValidity[keyB]) {
        if (C120_AIR_TERRITORIAL_RANKING) c120FilteredAir++;
        continue;
      }
    }
    live.append(project);
  }
  if (C120_AIR_TERRITORIAL_RANKING) {
    C120_AIR_FILTER_SNAPSHOT = {
      date = AIDate.GetCurrentDate(), inputAir = c120InputAir,
      filteredAir = c120FilteredAir, liveAir = c120InputAir - c120FilteredAir,
    };
  }
  return live;
}

/* C80 étape 1 : vérifie si un projet rail possède un tracé prêt validé dans le stock. */
function OpexRailProjectHasReadyRoute(project, railReadyStock)
{
  if (project == null) return false;
  if (("payload" in project) && project.payload != null
      && ("railPlan" in project.payload) && project.payload.railPlan != null
      && (!("ok" in project.payload.railPlan) || project.payload.railPlan.ok)) {
    return true;
  }
  if (railReadyStock == null) return false;
  local pairKey = OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
  if (!(pairKey in railReadyStock)) return false;
  local entry = railReadyStock[pairKey];
  if (entry == null || !("plan" in entry) || entry.plan == null) return false;
  if (("ok" in entry.plan) && !entry.plan.ok) return false;
  return true;
}

/* C80 étape 1 : filtre les alternatives rail sans tracé prêt validé dans le stock. */
function OpexFilterRailStockGate(alternatives, railReadyStock)
{
  local kept = [];
  foreach (project in alternatives) {
    if (project != null && ("mode" in project) && project.mode == "rail") {
      /* Le worker est le seul producteur de projets rail eligibles. */
      if (C80_RAIL_STOCK_WORKER) continue;
      if (!OpexRailProjectHasReadyRoute(project, railReadyStock)) continue;
    }
    kept.push(project);
  }
  if (C80_RAIL_STOCK_WORKER && railReadyStock != null) {
    foreach (pairKey, entry in railReadyStock) {
      if (entry != null && ("project" in entry) && entry.project != null)
        kept.push(entry.project);
    }
  }
  return kept;
}

/* Preparation C121 : attache le trace pret aux alternatives rail deja elues
 * et ajoute les projets du stock absents du vivier. Ne retire aucun rail
 * (contrairement a OpexFilterRailStockGate). Inerte pendant l'annee AIR. */
function OpexRailPrepMergeAlternatives(alternatives, railReadyStock)
{
  if (!C121_AIR_FIRST_YEAR_RAIL_PREP || C121_CATALOG_FIRST_YEAR_ACTIVE) return alternatives;
  if (railReadyStock == null || alternatives == null) return alternatives;
  if (railReadyStock.len() == 0) return alternatives;
  local seen = {};
  foreach (project in alternatives) {
    if (project == null || !("mode" in project) || project.mode != "rail") continue;
    if (!("kind" in project) || !("cargo" in project) || !("src" in project) || !("dst" in project)) continue;
    local pairKey = OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
    seen[pairKey] <- true;
    if (!(pairKey in railReadyStock)) continue;
    local entry = railReadyStock[pairKey];
    if (entry == null || !("plan" in entry) || entry.plan == null) continue;
    if (("ok" in entry.plan) && !entry.plan.ok) continue;
    if (("payload" in project) && project.payload != null) {
      project.payload.rawset("railPlan", entry.plan);
      project.payload.rawset("c121PrepStock", true);
    }
  }
  foreach (pairKey, entry in railReadyStock) {
    if (pairKey in seen) continue;
    if (entry == null || !("project" in entry) || entry.project == null) continue;
    if (!("plan" in entry) || entry.plan == null) continue;
    if (("ok" in entry.plan) && !entry.plan.ok) continue;
    if (("payload" in entry.project) && entry.project.payload != null) {
      entry.project.payload.rawset("railPlan", entry.plan);
      entry.project.payload.rawset("c121PrepStock", true);
    }
    alternatives.push(entry.project);
  }
  return alternatives;
}

/* Meme sonde d'opcodes que la selection, limitee a la fusion par passe. */
function OpexRailStockMergeAlternatives(alternatives, railReadyStock, stats)
{
  local mark = C80_RAIL_STOCK_WORKER ? OpexOpsMeasureBegin() : null;
  local merged = OpexFilterRailStockGate(alternatives, railReadyStock);
  if (mark != null) stats.railStockFusionOpcodes <- OpexOpsMeasureEnd(mark);
  return merged;
}

/* Appele seulement dans une branche C80 deja armee ; la file des candidats
 * reste dans projects.rail, tandis que candidateGroups porte les autres modes. */
function OpexRailStockStripCandidateGroups(groups)
{
  local nonRailGroups = {};
  foreach (key, list in groups) {
    local retained = [];
    foreach (p in list) if (p != null && p.mode != "rail") retained.push(p);
    if (retained.len() > 0) nonRailGroups.rawset(key, retained);
  }
  return nonRailGroups;
}

/* C38 : cle stable d'une tentative au sein d'un batch. Les plans air/eau sont des objets
 * regenerables ; l'identite doit donc reposer sur le mode, les extremites, le cargo et le type,
 * jamais sur l'adresse du payload. La flotte cible une ligne existante. */
function OpexProjectAttemptKey(p)
{
  if (p == null) return "none";
  local mode = ("mode" in p) ? p.mode : "unknown";
  if (mode == "fleet" && ("payload" in p) && p.payload != null &&
      ("line" in p.payload) && p.payload.line != null && ("lineId" in p.payload.line)) {
    return "fleet|" + p.payload.line.lineId;
  }
  if (("payload" in p) && p.payload != null
      && ("isSubsidy" in p.payload) && p.payload.isSubsidy) {
    return "subsidy|" + p.payload.subsidyId;
  }
  if (("payload" in p) && p.payload != null
      && ("isRoadExtension" in p.payload) && p.payload.isRoadExtension) {
    return "road_extension|" + p.payload.targetLineId + "|"
           + p.payload.extensionTown + "|" + p.payload.extensionSite.tile;
  }
  local src = ("src" in p) ? p.src : -1;
  local dst = ("dst" in p) ? p.dst : -1;
  local cargo = ("cargo" in p) ? p.cargo : -1;
  local kind = ("kind" in p) ? p.kind : "";
  return mode + "|" + src + "|" + dst + "|" + cargo + "|" + kind;
}
