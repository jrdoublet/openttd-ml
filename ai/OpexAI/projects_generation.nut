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
    local generatePax = (!targeted || entityKind == "town") && !V217_REGEN_NO_PAX;
    local generateFreight = !targeted || entityKind == "industry";
    local freightOrder = OpexFreightCargoOrder(catalog);
    local rail = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
        null, null, null, null, null, generatePax, generateFreight, PAX_BAND_ALL,
        freightCargo, entityKind, entityId);
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
        if (impossibleTargetCargo) {
          if (DECISION_LOG) {
            OpexDecide("RAIL_TARGET_CARGO_SKIP", "industry=" + entityId
                       + " cargo=" + fallbackCargo + " reason=no_structural_pair");
          }
          continue;
        }
        local extra = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
            null, null, null, null, null, false, true, PAX_BAND_ALL, fallbackCargo,
            entityKind, entityId);
        if (DECISION_LOG && impossibleTargetCargo) {
          OpexDecide("RAIL_TARGET_CARGO_SHADOW", "industry=" + entityId
                     + " cargo=" + fallbackCargo + " opcodes=" + extra.opcodes
                     + " candidates=" + extra.candidates.len());
        }
        if (extra.candidates.len() == 0) continue;
        rail = OpexMergeRailCandidateSet(rail, extra);
        freightCargo = fallbackCargo;
        generated.freightCargo = freightCargo;
        /* Sous C77, le mode route est traite a la tranche suivante : publier le fallback reel
         * uniquement sur cette regeneration ciblee, sans toucher au chemin normal. */
        if (targeted) projects.freightCargo = freightCargo;
        break;
      }
    }
    generated.rail = rail;
    foreach (candidate in rail.candidates) {
      if (abandonedPairs != null
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
      if (abandonedPairs != null
          && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
      local p = OpexProjectFromCandidate(candidate);
      if (p != null) generated.projects.append(p);
    }

  } else if (mode == "air") {
    local mark = OpexOpsMeasureBegin();
    local plans = [];

    local best = OpexAirPlans(catalog, lines, 0, plans, abandonedPairs, PAX_BAND_ALL,
                              entityKind == "town" ? entityId : -1);

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
  if (V276_CAND_SLICES > 0 && (mode == "rail" || mode == "road")) {
    OpexV276Request(catalog, entityKind, entityId);
    return OpexReselectProjects(projects, OpexAvailableCapital(), abandonedPairs, lines);
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

  local best = OpexAirPlans(catalog, lines, 0, sliceState.plans, abandonedPairs, PAX_BAND_ALL,
                            entityKind == "town" ? entityId : -1,
                            sliceState.airCursor, opsBudget, deadlineTick);

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
      if (OpexAirPairIsAbandoned(abandonedPairs, plan.siteA, plan.siteB)) return true;
    }
  } else if ((mode == "road" || mode == "rail")) {
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
        /* Fret routier : exclusivite d'origine historique (C55_FREIGHT_ORIGIN_RELAX fige a false). */
        if (C55_ORIGIN_RELAX_PROBE) {
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
    return true;
  }

  /* 3. Mode rail : les deux extremites servies excluent la ligne */
  if (mode == "rail") {
    local towns = OpexGetCandidateTownEndpoints(p);
    if (C60_TOWN_RATING_PROBE) {
      if (towns.srcTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.srcTown);
      if (towns.dstTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.dstTown);
    }
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
function OpexIncrementalCandidateStillValid(p, lines, abandonedPairs = null, ctx = null)
{
  if (ctx != null) return OpexCandidateStillValidIndexed(p, lines, abandonedPairs, ctx);
  return OpexCandidateStillValid(p, lines, abandonedPairs);
}

/* V156 : Construction d'un contexte d'indexation pour la revalidation incrementale du vivier.
 * Indexe les predicats dependant de lines : doublons exacts, losange OpexOriginServed,
 * bus pax de ville, freight busy, paires et hubs air. */
function OpexIncrRevalidateIndexContext(lines)
{
  local ctx = {
    exactLines = {},
    servedWithRoad = {},
    servedRailOnly = {},
    townBusPaxServed = {},
    roadFreightBusy = {},
    airOrigins = [],
    airTownServed = {},
    airHubRouteCounts = {},
    airLinePairs = {},
    airSiteValidity = {},
    stationLimitedTowns = {},
  };
  {
    ctx.airValidityState <- OpexAir0310SiteValidityBegin(ctx.stationLimitedTowns);
  }
  if (lines == null || lines.len() == 0) return ctx;

  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  local radius = ORIGIN_SEPARATION - 1;

  foreach (line in lines) {
    if (line == null) continue;
    local hasOriginA = ("originA" in line);
    local hasOriginB = ("originB" in line);
    local hasCargo = ("cargo" in line);
    local hasMode = ("mode" in line);
    local mode = hasMode ? line.mode : null;

    /* 1. Doublons exacts : cargo + originA + originB dans les deux sens */
    if (hasCargo && hasOriginA && hasOriginB) {
      ctx.exactLines.rawset(line.cargo + "|" + line.originA + "|" + line.originB, true);
      ctx.exactLines.rawset(line.cargo + "|" + line.originB + "|" + line.originA, true);
    }

    /* 2. Index losange OpexOriginServed (rayon ORIGIN_SEPARATION - 1) */
    local isRail = !hasMode || mode == "rail";
    local isRoad = hasMode && mode == "road";
    if (hasOriginA && hasOriginB && (isRail || isRoad)) {
      local origins = [line.originA, line.originB];
      foreach (origin in origins) {
        if (!AIMap.IsValidTile(origin)) continue;
        local ox = AIMap.GetTileX(origin);
        local oy = AIMap.GetTileY(origin);
        for (local dx = -radius; dx <= radius; dx++) {
          local x = ox + dx;
          if (x < 0 || x >= width) continue;
          local dyLimit = radius - abs(dx);
          for (local dy = -dyLimit; dy <= dyLimit; dy++) {
            local y = oy + dy;
            if (y < 0 || y >= height) continue;
            local tIdx = AIMap.GetTileIndex(x, y);
            if (isRail) ctx.servedRailOnly.rawset(tIdx, true);
            ctx.servedWithRoad.rawset(tIdx, true);
          }
        }
      }
    }

    /* 3. Aides mode route */
    if (isRoad) {

      if (!("scrapping" in line && line.scrapping) && hasCargo && line.cargo >= 0
          && AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)) {
        local srcTown = ("srcTown" in line && line.srcTown >= 0)
            ? line.srcTown : (hasOriginA && AIMap.IsValidTile(line.originA) ? AITile.GetClosestTown(line.originA) : -1);
        if (srcTown >= 0) ctx.townBusPaxServed.rawset(srcTown, true);
        local dstTown = ("dstTown" in line && line.dstTown >= 0)
            ? line.dstTown : (hasOriginB && AIMap.IsValidTile(line.originB) ? AITile.GetClosestTown(line.originB) : -1);
        if (dstTown >= 0) ctx.townBusPaxServed.rawset(dstTown, true);
      }
    }

    /* 4. Fret routier busy */
    if ((isRail || isRoad) && hasCargo && hasOriginA && hasOriginB) {
      ctx.roadFreightBusy.rawset(line.cargo + "|" + line.originA, true);
      ctx.roadFreightBusy.rawset(line.cargo + "|" + line.originB, true);
    }

    /* 5. Aides mode air */
    if (hasMode && mode == "air") {
      if (hasOriginA && AIMap.IsValidTile(line.originA)) ctx.airOrigins.append(line.originA);
      if (hasOriginB && AIMap.IsValidTile(line.originB)) ctx.airOrigins.append(line.originB);
      if (hasOriginA && hasOriginB) {
        ctx.airLinePairs.rawset(line.originA + "|" + line.originB, true);
        ctx.airLinePairs.rawset(line.originB + "|" + line.originA, true);
      }
      local stA = ("stationA" in line && AIMap.IsValidTile(line.stationA)) ? AIStation.GetStationID(line.stationA) : -1;
      local stB = ("stationB" in line && AIMap.IsValidTile(line.stationB)) ? AIStation.GetStationID(line.stationB) : -1;
      if (stA >= 0 && AIStation.IsValidStation(stA)) {
        if (stA in ctx.airHubRouteCounts) ctx.airHubRouteCounts[stA]++;
        else ctx.airHubRouteCounts.rawset(stA, 1);
      }
      if (stB >= 0 && stB != stA && AIStation.IsValidStation(stB)) {
        if (stB in ctx.airHubRouteCounts) ctx.airHubRouteCounts[stB]++;
        else ctx.airHubRouteCounts.rawset(stB, 1);
      }
    }
  }

  return ctx;
}

/* V156 : Revalidation incrementale indexee d'un candidat du vivier contre ctx et lines.
 * Structure de decision et court-circuits strictement equivalents a OpexCandidateStillValid. */
function OpexCandidateStillValidIndexed(p, lines, abandonedPairs, ctx)
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
  if (("cargo" in p) && ("src" in p) && ("dst" in p)) {
    local dupKey = p.cargo + "|" + p.src + "|" + p.dst;
    if (dupKey in ctx.exactLines) return false;
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
      if ((endpoints.srcTown >= 0 && (endpoints.srcTown in ctx.townBusPaxServed)) ||
          (endpoints.dstTown >= 0 && (endpoints.dstTown in ctx.townBusPaxServed))) return false;
    }
    if (p.kind == "pax") {
      local srcServed = (p.src in ctx.servedWithRoad);
      local dstServed = (p.dst in ctx.servedWithRoad);
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
      /* Fret routier : exclusivite d'origine historique (C55_FREIGHT_ORIGIN_RELAX fige a false). */
      if (C55_ORIGIN_RELAX_PROBE) {
        local srcServed = (p.src in ctx.servedWithRoad);
        local dstServed = (p.dst in ctx.servedWithRoad);
        OpexC55OriginRelaxObserve("freight", lines, p.src, p.dst, srcServed, dstServed);
        if (srcServed || dstServed) return false;
      } else {
        if (p.src in ctx.servedWithRoad) return false;
        if (p.dst in ctx.servedWithRoad) return false;
      }
      local towns = OpexGetCandidateTownEndpoints(p);
      if (C60_TOWN_RATING_PROBE) {
        if (towns.srcTown >= 0) OpexC60ObserveTownRating("road", "incremental_valid", towns.srcTown);
        if (towns.dstTown >= 0) OpexC60ObserveTownRating("road", "incremental_valid", towns.dstTown);
      }
    }
    return true;
  }

  /* 3. Mode rail : les deux extremites servies excluent la ligne */
  if (mode == "rail") {
    local towns = OpexGetCandidateTownEndpoints(p);
    if (C60_TOWN_RATING_PROBE) {
      if (towns.srcTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.srcTown);
      if (towns.dstTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.dstTown);
    }
    if ((p.src in ctx.servedRailOnly) && (p.dst in ctx.servedRailOnly)) {
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
    if (!OpexAirBatchPlanStillLiveIndexed(plan, lines, ctx)) return false;
    local reuseA = ("reuseA" in plan) && plan.reuseA;
    if (!OpexAirSiteStillBuildableIndexed(plan.siteA, plan.airport, plan.plane, reuseA, ctx)) {
      return false;
    }
    local reuseB = ("reuseB" in plan) && plan.reuseB;
    if (!OpexAirSiteStillBuildableIndexed(plan.siteB, plan.airport, plan.plane, reuseB, ctx)) {
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

/* C78.2 : les sites AIR sont des predictions faites pendant un scan qui peut
 * suspendre plusieurs fois. Juste avant tout classement, retirer les plans dont
 * une extremite est devenue impossible ou dont la paire a ete abandonnee.
 * Plusieurs projets peuvent partager la meme extremite : une seule sonde par
 * site/type/reuse suffit pour toute la selection. */
function OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs = null, lines = null, externalSiteValidity = null, externalStationLimitedTowns = null)
{
  return OpexAir0310FilterAirAlternativesStillValid(alternatives, abandonedPairs, lines);
}

/* V122 : meme filtre, avec le cache global de validite. Le chemin a 0
 * n'entre pas ici. La cle reste celle de keyA/keyB. stationLimitedTowns
 * est amorce depuis les villes deja plafonnees, puis complete par les
 * misses ; une entree deja stockee n'est pas recalculee. */
function OpexAir0310FilterAirAlternativesStillValid(alternatives, abandonedPairs = null, lines = null)
{
  local live = [];
  local stationLimitedTowns = {};
  local validity = OpexAir0310SiteValidityBegin(stationLimitedTowns);
  foreach (project in alternatives) {
    if (project != null && ("mode" in project) && project.mode == "air") {
      if (!("payload" in project) || project.payload == null
          || OpexCandidateIsAbandoned(project, abandonedPairs)) {
        continue;
      }
      local plan = project.payload;
      if (!("siteA" in plan) || !("siteB" in plan) || !("airport" in plan) || !("plane" in plan)) {
        continue;
      }
      local reuseA = ("reuseA" in plan) && plan.reuseA;
      local reuseB = ("reuseB" in plan) && plan.reuseB;
      local keyA = (reuseA ? "R|" : "N|") + plan.airport.type + "|" + plan.plane.planeType + "|" + plan.siteA.anchor;
      local keyB = (reuseB ? "R|" : "N|") + plan.airport.type + "|" + plan.plane.planeType + "|" + plan.siteB.anchor;
      if (!OpexAir0310SiteValidityOk(validity, keyA,
            plan.siteA, plan.airport, plan.plane, reuseA, stationLimitedTowns)) {
        continue;
      }
      if (!OpexAir0310SiteValidityOk(validity, keyB,
            plan.siteB, plan.airport, plan.plane, reuseB, stationLimitedTowns)) {
        continue;
      }
    }
    live.append(project);
  }
  return live;
}

/* Preparation C121 : attache le trace pret aux alternatives rail deja elues
 * et ajoute les projets du stock absents du vivier. Ne retire aucun rail
 * sans retirer aucun rail du vivier. Inerte pendant l'annee AIR. */
function OpexRailPrepMergeAlternatives(alternatives, railReadyStock)
{
  if (!(MODE_AIR && MODE_RAIL) || C121_CATALOG_FIRST_YEAR_ACTIVE) return alternatives;
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
