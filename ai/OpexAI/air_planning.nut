/* Module AIR extrait de builder_air.nut (R11) : planification des liaisons (OpexAirPlans et etapes). */
/* C78.2 : une paire AIR est non orientee. Generation et chantier ecrivent
 * exactement la meme cle, meme si un hub inverse l'ordre des extremites. */
function OpexAirPairKey(siteA, siteB)
{
  local a = siteA.town.tile;
  local b = siteB.town.tile;
  if (a > b) {
    local swap = a;
    a = b;
    b = swap;
  }
  return "air|" + a + "|" + b;
}

/* Compatibilite des sauvegardes anterieures a C78.2 : les anciennes cles
 * pouvaient avoir ete ecrites dans l'autre sens. */
function OpexAirPairIsAbandoned(abandoned, siteA, siteB)
{
  if (abandoned == null || siteA == null || siteB == null) return false;
  local canonical = OpexAirPairKey(siteA, siteB);
  if (canonical in abandoned) return true;
  local legacyForward = "air|" + siteA.town.tile + "|" + siteB.town.tile;
  if (legacyForward != canonical && (legacyForward in abandoned)) return true;
  local legacyReverse = "air|" + siteB.town.tile + "|" + siteA.town.tile;
  return legacyReverse != canonical && (legacyReverse in abandoned);
}

/* C78 etape 2 : identification de la ville d'un hub aerien. */
function OpexC78HubTownId(h)
{
  if (h != null) {
    if (("town" in h) && h.town != null && ("id" in h.town)) return h.town.id;
    if (("anchor" in h) && AIMap.IsValidTile(h.anchor)) return AITile.GetClosestTown(h.anchor);
  }
  return -1;
}

/* Calcul du delta d'opcodes consommes depuis (t0, l0). */
function OpexAirCalcDeltaOps(t0, l0)
{
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - t0;
  return elapsed <= 0
    ? l0 - left
    : l0 + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
}

/* FRONT-PAX-2 : un seul dossier de chaque bras survit a la generation.
 * Les sites viennent du balayage deja effectue ; aucun autre parcours de
 * villes, sondage de terrain, C121 ou A* n'est fait en mode shadow. */
function OpexFP2NewShortlist(bounds)
{
  return {
    bounds = bounds, slots = [null, null, null], thresholds = {},
    seen = [0, 0, 0], eligible = [0, 0, 0],
    duplicates = [0, 0, 0], shadowOps = 0,
  };
}

function OpexFP2Shortlist(ctx, arm, siteA, siteB, airport, plane,
                          manhattan, flightDistance, orderDistance, minDist)
{
  local fp = ctx.fp2;
  if (fp == null) return;
  /* Le scan C78 peut chevaucher un rafraichissement annuel du catalogue.
   * Ne pas melanger les bornes d'une epoque avec des paires d'une autre. */
  if (ctx.catalog.bounds != fp.bounds) return;
  if (manhattan < minDist || manhattan >= fp.bounds.airMin
      || manhattan < fp.bounds.railMin || flightDistance <= 0 || orderDistance <= 0
      || fp.bounds.airMax <= 0
      || (fp.bounds.airMax > 0 && flightDistance > fp.bounds.airMax)
      || (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE)
      || (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance)
      || siteA == null || siteB == null || siteA.town == null || siteB.town == null
      || siteA.town.id == siteB.town.id) return;
  fp.seen[arm]++;
  /* C121 uses the REAL types of reused endpoints; combo.airport.type only
   * describes a newly built airport. Missing hub geometry fails closed. */
  local typeA = airport.type, typeB = airport.type;
  if (arm >= 1) {
    if (!AIMap.IsValidTile(siteA.anchor) || !AIAirport.IsAirportTile(siteA.anchor))
      return;
    typeA = AIAirport.GetAirportType(siteA.anchor);
  }
  if (arm == 2) {
    if (!AIMap.IsValidTile(siteB.anchor) || !AIAirport.IsAirportTile(siteB.anchor))
      return;
    typeB = AIAirport.GetAirportType(siteB.anchor);
  }
  if (!AIAirport.IsValidAirportType(typeA) || !AIAirport.IsValidAirportType(typeB))
    return;
  local thresholdKey = airport.type + "|" + plane.id + "|" + typeA + "|" + typeB;
  if (!(thresholdKey in fp.thresholds)) {
    local pax = ctx.catalog.paxCargo;
    local wagon = pax >= 0 && ctx.catalog.wagonByCargo != null
        && (pax in ctx.catalog.wagonByCargo)
        ? ctx.catalog.wagonByCargo[pax] : null;
    local minDistance = OpexFP2PhysicalBoundary(fp.bounds, plane.speed,
        typeA, typeB, wagon);
    fp.thresholds.rawset(thresholdKey, {
      min = minDistance,
      ground = minDistance >= 0
          ? OpexC100AirManeuverDays(plane.id, typeA, typeB) : -1.0,
    });
  }
  local boundary = fp.thresholds[thresholdKey];
  local threshold = boundary.min;
  local pax = ctx.catalog.paxCargo;
  local wagon = pax >= 0 && ctx.catalog.wagonByCargo != null
      && (pax in ctx.catalog.wagonByCargo)
      ? ctx.catalog.wagonByCargo[pax] : null;
  if (threshold < 0 || manhattan < threshold
      || !OpexFP2PhysicalPairWins(fp.bounds, plane.speed,
          wagon, manhattan, flightDistance, boundary.ground)
      || OpexAirPairIsAbandoned(ctx.abandoned, siteA, siteB)) return;
  local monthly = 0;
  if (arm == 0) {
    monthly = (siteA.town.pop + siteB.town.pop) * TOWN_CATCHMENT_SHARE_PCT / 100;
  } else if (arm == 1) {
    if (!("routes" in siteA) || siteA.routes < 0) return;
    monthly = siteA.town.pop * TOWN_CATCHMENT_SHARE_PCT / (100 * (siteA.routes + 1))
        + siteB.town.pop * TOWN_CATCHMENT_SHARE_PCT / 100;
  } else {
    if (!("routes" in siteA) || !("routes" in siteB)
        || siteA.routes < 0 || siteB.routes < 0) return;
    monthly = siteA.town.pop * TOWN_CATCHMENT_SHARE_PCT / (100 * (siteA.routes + 1))
        + siteB.town.pop * TOWN_CATCHMENT_SHARE_PCT / (100 * (siteB.routes + 1));
  }
  if (monthly < 10) monthly = 10;
  local mark = OpexOpsMeasureBegin();
  local keyA = siteA.town.tile, keyB = siteB.town.tile;
  if (keyA > keyB) { local tmp = keyA; keyA = keyB; keyB = tmp; }
  /* Tie-break exact et stable sur les sites et le combo : aucune iteration
   * supplementaire, une seule entree en memoire par bras. */
  local key = keyA + "|" + keyB + "|" + siteA.anchor + "|" + siteB.anchor
      + "|" + airport.type + "|" + plane.id;
  local score = monthly.tofloat() * manhattan;
  fp.eligible[arm]++;
  local previous = fp.slots[arm];
  if (previous != null && previous.key == key) fp.duplicates[arm]++;
  if (previous == null || score > previous.score
      || (score == previous.score && key < previous.key)) {
    fp.slots[arm] = {
      key = key, pair = OpexAirPairKey(siteA, siteB),
      siteA = siteA, siteB = siteB, airport = airport, plane = plane,
      distance = manhattan, flightDistance = flightDistance,
      orderDistance = orderDistance, threshold = threshold,
      score = score, monthlyPax = monthly, arm = arm,
    };
  }
  fp.shadowOps += OpexOpsMeasureEnd(mark);
}

/* Mode ON seulement, APRES le dernier combo du scan. Chaque bras peut faire
 * au plus un appel C121, et seulement apres revalidation des deux sites.
 * Le projet resultant emprunte OpexProjectFromAir puis la selection commune
 * OpexProjectSelectAffordable (C77/K_dec/V252 inchanges). */
function OpexFP2Finalize(ctx)
{
  local fp = ctx.fp2;
  if (fp == null) return;
  local stale = false;
  if (FRONT_PAX2_BOUNDED_OVERLAP == 2) {
    stale = ctx.catalog == null || ctx.catalog.bounds != fp.bounds
        || AIDate.GetYear(AIDate.GetCurrentDate()) != fp.bounds.year;
  }
  local names = ["newpair", "hubsite", "hubhub"];
  local used = {};
  for (local arm = 2; arm >= 0; arm--) {
    local candidate = fp.slots[arm];
    local result = candidate == null ? "none" : "shadow";
    local profit = 0, finance = 0, ops = 0;
    if (candidate != null && FRONT_PAX2_BOUNDED_OVERLAP == 2 && stale) {
      result = "stale_scan";
    } else if (candidate != null && FRONT_PAX2_BOUNDED_OVERLAP == 2) {
      result = "site";
      if (candidate.pair in used) {
        result = "duplicate_pair";
      } else {
        used.rawset(candidate.pair, true);
        local t0 = AIController.GetTick(), l0 = AIController.GetOpsTillSuspend();
        local airport = candidate.airport, plane = candidate.plane;
        local reuseA = arm != 0, reuseB = arm == 2;
        if (OpexAirSiteStillBuildable(candidate.siteA, airport, plane, reuseA)
            && OpexAirSiteStillBuildable(candidate.siteB, airport, plane, reuseB)) {
          local plan = {
            siteA = candidate.siteA, siteB = candidate.siteB, airport = airport,
            plane = plane, distance = candidate.flightDistance,
            orderDistance = candidate.orderDistance, monthlyPax = candidate.monthlyPax,
            planes = 1, capital = 0, economics = null,
            reuseA = reuseA, reuseB = reuseB,
            hubRoutes = arm == 0 ? 0 : (arm == 1 ? candidate.siteA.routes
                : candidate.siteA.routes + candidate.siteB.routes),
            c83OwnSecondSlotA = !reuseA && ("c83OwnSecondSlot" in candidate.siteA)
                && candidate.siteA.c83OwnSecondSlot,
            c83OwnSecondSlotB = !reuseB && ("c83OwnSecondSlot" in candidate.siteB)
                && candidate.siteB.c83OwnSecondSlot,
            arm = names[arm],
          };
          local choice = OpexC121CatalogChoice(ctx.catalog, plan, ctx.lines);
          local economics = choice != null ? choice.economics : null;
          local selectedPlane = choice != null ? choice.plane : null;
          result = "c121";
          local paxCargo = ctx.catalog.paxCargo;
          local railWagon = paxCargo >= 0 && ctx.catalog.wagonByCargo != null
              && (paxCargo in ctx.catalog.wagonByCargo)
              ? ctx.catalog.wagonByCargo[paxCargo] : null;
          if (economics != null && selectedPlane != null && economics.profitAnnual > 0
              && fp.bounds.vRail > 0 && railWagon != null && railWagon.capacity > 0
              && ("oneWayDays" in economics) && economics.oneWayDays > 0
              && economics.oneWayDays + (arm == 0 ? 1.0 / 74.0 : 0.0)
                  <= candidate.distance.tofloat()
                      / (0.036 * fp.bounds.vRail.tofloat())
                      + OpexRailStationDwellDays(railWagon)
              && OpexAirPlaneInRange(selectedPlane, candidate.flightDistance)
              && OpexAirSiteStillBuildable(candidate.siteA, airport, selectedPlane, reuseA)
              && OpexAirSiteStillBuildable(candidate.siteB, airport, selectedPlane, reuseB)) {
            plan.plane = selectedPlane;
            plan.planes = economics.planes;
            plan.capital = economics.capital;
            plan.economics = economics;
            if (("decisionEconomics" in choice) && choice.decisionEconomics != null)
              plan.decisionEconomics <- choice.decisionEconomics;
            if (("portfolioEconomics" in choice) && choice.portfolioEconomics != null)
              plan.portfolioEconomics <- choice.portfolioEconomics;
            plan.targetPlanes <- choice.targetPlanes;
            plan.frontPax2Id <- candidate.key;
            plan.frontPax2Scan <- ctx.servedDiag != null ? ctx.servedDiag.scan : -1;
            /* Neither admission nor its cash check is an independent score:
             * unchanged downstream mode selection will rank this project. */
            local project = OpexProjectFromAir(ctx.catalog, plan, 0);
            result = "economics";
            if (project != null) {
              finance = OpexProjectFinanceCapital(project);
              profit = project.profitAnnual;
              local available = OpexAvailableCapital();
              if (finance > 0 && finance <= available
                  && (ctx.maxCapital <= 0 || finance <= ctx.maxCapital)) {
                OpexAirReserveJoinedStops(ctx.catalog, plan);
                ctx.bestPlan = OpexAirStoreRoutePlan(ctx.projects, plan, choice, ctx.bestPlan);
                result = "fundable";
              } else result = "cash";
            }
          }
        }
        ops = OpexAirCalcDeltaOps(t0, l0);
      }
    }
    if (DECISION_LOG) {
      OpexDecide("FRONT_PAX2_BOUNDED", "arm=" + names[arm]
          + " mode=" + FRONT_PAX2_BOUNDED_OVERLAP
          + " seen=" + fp.seen[arm] + " eligible=" + fp.eligible[arm]
          + " dup=" + fp.duplicates[arm]
          + " key=" + (candidate != null ? candidate.key : "none")
          + " dist=" + (candidate != null ? candidate.distance : -1)
          + " threshold=" + (candidate != null ? candidate.threshold : -1)
          + " result=" + result + " profit=" + profit + " finance=" + finance
          + " shadow_ops=" + fp.shadowOps + " eval_ops=" + ops);
    }
  }
}

/* 1. Preparation : combos, villes, OpexAirTownPoolLimit, indices et reprise. */
function OpexAirPlansPrepare(ctx)
{
  local catalog = ctx.catalog;
  local lines = ctx.lines;
  local targetTownId = ctx.targetTownId;
  local resumeState = ctx.resumeState;
  local t0_all = ctx.t0_all;
  local sliced = ctx.sliced;

  if (!sliced) {
    OpexAirResetStationCoverageTownCache();
  } else if (!("stationCoverageTownCacheInit" in resumeState)) {
    OpexAirResetStationCoverageTownCache();
    resumeState.stationCoverageTownCacheInit <- true;
  }

  /* V278 : seule la preparation stable est sautee ; les entrees vivantes sont relues. */
  if (V278_AIR_LAZY_SITES && sliced && ("v278Prepare" in resumeState)
      && !resumeState.done && OpexV278RestorePrepare(ctx)) return true;
  if (sliced) {
    if (!("done" in resumeState)) resumeState.done <- false;
    if (resumeState.done) {
      ctx.bestPlan = ("bestPlan" in resumeState) ? resumeState.bestPlan : null;
      return false;
    }
    if (!("combo" in resumeState)) resumeState.combo <- 0;
    if (!("a" in resumeState)) resumeState.a <- 0;
    if (!("b" in resumeState)) resumeState.b <- 1;
    if (!("sites" in resumeState)) resumeState.sites <- null;
    if (!("bestPlan" in resumeState)) resumeState.bestPlan <- null;
    if (!("stationLimitedTowns" in resumeState)) resumeState.stationLimitedTowns <- {};
    if (!("perfOpsSites" in resumeState)) resumeState.perfOpsSites <- 0;
    if (!("perfOpsEval" in resumeState)) resumeState.perfOpsEval <- 0;
    if (!("perfProbesCount" in resumeState)) resumeState.perfProbesCount <- 0;
    if (!("perfCheapSkip" in resumeState)) resumeState.perfCheapSkip <- 0;
    if (!("perfSitesFound" in resumeState)) resumeState.perfSitesFound <- 0;
    if (!("totalOps" in resumeState)) resumeState.totalOps <- 0;
    if (!("startTick" in resumeState)) resumeState.startTick <- t0_all;
    if (!("towns" in resumeState)) resumeState.towns <- null;
    if (!("combos" in resumeState)) resumeState.combos <- null;
    if (!("townLimit" in resumeState)) resumeState.townLimit <- -1;
    if (!("scanIndex" in resumeState)) resumeState.scanIndex <- 0;
    if (!("scanSites" in resumeState)) resumeState.scanSites <- [];
    if (!("scanProbes" in resumeState)) resumeState.scanProbes <- null;
    if (!("rankIndex" in resumeState)) resumeState.rankIndex <- 0;
    if (!("rankSites" in resumeState)) resumeState.rankSites <- [];
    if (!("c83TopTownIds" in resumeState)) resumeState.c83TopTownIds <- null;
  }
  if (sliced) {
    if (!("c121PlanPerf" in resumeState)) {
      resumeState.c121PlanPerf <- { calls = 0, demandOps = 0, demandTicks = 0,
          staticOps = 0, staticTicks = 0, scanOps = 0, scanTicks = 0,
          engineEvals = 0, winnerOps = 0, winnerTicks = 0, noWinner = 0,
          endpointHits = 0, endpointMisses = 0 };
    }
    if (!("c121EndpointCache" in resumeState)) resumeState.c121EndpointCache <- {};
    C121_AIR_PLAN_PERF = resumeState.c121PlanPerf;
    C121_AIR_ENDPOINT_CACHE = resumeState.c121EndpointCache;
  } else {
    C121_AIR_PLAN_PERF = { calls = 0, demandOps = 0, demandTicks = 0,
        staticOps = 0, staticTicks = 0, scanOps = 0, scanTicks = 0,
        engineEvals = 0, winnerOps = 0, winnerTicks = 0, noWinner = 0,
        endpointHits = 0, endpointMisses = 0 };
    C121_AIR_ENDPOINT_CACHE = {};
  }
  local perfOpsSites = sliced ? resumeState.perfOpsSites : 0;
  local perfOpsEval = sliced ? resumeState.perfOpsEval : 0;
  local perfProbesCount = sliced ? resumeState.perfProbesCount : 0;
  local perfCheapSkip = sliced ? resumeState.perfCheapSkip : 0;
  local perfSitesFound = sliced ? resumeState.perfSitesFound : 0;

  local combos = sliced && resumeState.combos != null
      ? resumeState.combos
      : ((("airCombos" in catalog) && catalog.airCombos != null && catalog.airCombos.len() > 0)
          ? catalog.airCombos
          : (catalog.airport != null && catalog.plane != null ? [{ airport = catalog.airport, plane = catalog.plane }] : []));
  if (sliced && resumeState.combos == null) resumeState.combos = combos;
  local servedDiag = sliced && ("servedDiag" in resumeState) ? resumeState.servedDiag : null;
  if (DECISION_LOG && servedDiag == null) {
    AIR_PLAN_DIAG_SEQ++;
    servedDiag = {
      scan = AIR_PLAN_DIAG_SEQ,
      nullCalls = 0, emptyCalls = 0, nonemptyCalls = 0,
      trueCalls = 0, falseCalls = 0,
      loggedFalseTowns = {}, loggedFalseCount = 0, noAirLogged = false,
    };
    local linesState = lines == null ? "null" : (lines.len() == 0 ? "empty" : "nonempty");
    local lineCount = lines == null ? 0 : lines.len();
    local airLineCount = 0;
    if (lines != null) {
      foreach (line in lines) {
        if (("mode" in line) && line.mode == "air") airLineCount++;
      }
    }
    OpexDecide("AIR_PLAN_INPUT", "scan=" + servedDiag.scan + " lines_state=" + linesState
               + " line_count=" + lineCount + " air_line_count=" + airLineCount
               + " combos=" + combos.len());
    if (sliced) resumeState.servedDiag <- servedDiag;
  }
  if (combos.len() == 0) {
    if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "no_engine", 1);
    if (DECISION_LOG) {
      OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
                 + " null_calls=0 empty_calls=0 nonempty_calls=0 true_calls=0 false_calls=0"
                 + " false_towns_logged=0");
    }
    if (sliced) {
      resumeState.bestPlan = null;
      resumeState.sites = null;
      resumeState.done = true;
    }

    ctx.bestPlan = null;
    return false;
  }

  /* C80 tranche 5 bis : index exacts des lignes aeriennes, construits une fois par appel (les
   * lignes ne changent pas pendant la planification). Memes resolutions de gare que les boucles
   * qu'ils remplacent : nombre de routes par gare (decouverte des hubs) et paires deja reliees
   * (hub a hub), au lieu d'un parcours de toutes les lignes par hub et par paire de hubs. */
  local hubIndex = null;
  if (lines != null) {
    hubIndex = { routes = {}, pairs = {} };
    foreach (other in lines) {
      if (!("mode" in other) || other.mode != "air") continue;
      local oA = OpexAirLineStationId(other, 0);
      local oB = OpexAirLineStationId(other, 1);
      hubIndex.routes.rawset(oA, ((oA in hubIndex.routes) ? hubIndex.routes[oA] : 0) + 1);
      if (oB != oA) hubIndex.routes.rawset(oB, ((oB in hubIndex.routes) ? hubIndex.routes[oB] : 0) + 1);
      if (AIStation.IsValidStation(oA) && AIStation.IsValidStation(oB)) {
        hubIndex.pairs.rawset(oA + "|" + oB, true);
        hubIndex.pairs.rawset(oB + "|" + oA, true);
      }
    }
  }

  local c83TopTownIds = sliced && resumeState.c83TopTownIds != null
      ? resumeState.c83TopTownIds
      : {};
  local towns = sliced && resumeState.towns != null
      ? resumeState.towns
      : OpexAirSortedTowns(catalog.towns);
  if (!sliced || resumeState.towns == null) {
    /* C83.1 : la double prise proactive ne concerne que les plus grandes
     * villes deja couvertes par la politique early-slot. Calculer ce rang
     * avant une eventuelle remise en tete targetTownId preserve le vrai
     * classement par population. */
    if (OpexAirC83SlotSignalEnabled() && AIR_C83_TARGET_TOWNS > 0) {
      /* Cette liste autorise le second slot proactif d'une ville
       * deja servie par Opex (C83.1 adopte). */
      local c83TopLimit = towns.len() < AIR_C83_TARGET_TOWNS
          ? towns.len() : AIR_C83_TARGET_TOWNS;
      for (local c83i = 0; c83i < c83TopLimit; c83i++) {
        if (towns[c83i].pop >= AIR_EARLY_SLOT_MIN_POP) {
          c83TopTownIds.rawset(towns[c83i].id, true);
        }
      }
    }
    if (sliced) resumeState.c83TopTownIds = c83TopTownIds;
    if (targetTownId >= 0) {
      local targetedTowns = [];
      foreach (town in towns) if (town.id == targetTownId) targetedTowns.append(town);
      foreach (town in towns) if (town.id != targetTownId) targetedTowns.append(town);
      towns = targetedTowns;
    } else if (sliced) {
      OpexC121CatalogRankDirtyTowns();
      towns.sort(OpexC121CatalogTownPriorityCompare);
    }
    if (sliced) resumeState.towns = towns;
  }
  local limit = sliced && resumeState.townLimit >= 0
      ? resumeState.townLimit
      : OpexAirTownPoolLimit(towns);
  if (sliced) resumeState.townLimit = limit;
  /* C78 etape 2 : une generation complete journalisee par an, sous sonde seulement (aucun appel
   * d'API au defaut). Les bornes et les tuiles permettent de situer toute paire d'AAAHogEx par
   * rapport aux bandes de distance (airMin = bascule rail/avion). En mode reprenable (C78.4),
   * la decision est prise a la premiere tranche et conservee dans resumeState. */
  local c78Year = -1;
  local c78Gen = false;
  if (sliced && ("c78Gen" in resumeState)) {
    c78Year = resumeState.c78Year;
    c78Gen = resumeState.c78Gen;
  } else {
    if (C69_BOTTLENECK_PROBE && targetTownId < 0) {
      c78Year = AIDate.GetYear(AIDate.GetCurrentDate());
      c78Gen = C78_GEN_LOG_YEAR != c78Year;
    }
    if (c78Gen) {
      C78_GEN_LOG_YEAR = c78Year;
      local poolLimit = towns.len() < 120 ? towns.len() : 120;
      local townsStr = "";
      for (local idx = 0; idx < poolLimit; idx++) {
        if (idx > 0) townsStr += ",";
        townsStr += towns[idx].id + ":" + towns[idx].pop + ":" + towns[idx].tile;
      }
      local c78B = OpexCatalogBounds(catalog);
      OpexC78Log("C78_AIRPOOL", "year=" + c78Year + " pool=" + limit
          + " mapx=" + AIMap.GetMapSizeX() + " airMin=" + c78B.airMin + " airMax=" + c78B.airMax
          + " railMin=" + c78B.railMin + " railMax=" + c78B.railMax
          + " overlap=" + c78B.railAirOverlapMin
          + " e_cash=" + AIError.ERR_NOT_ENOUGH_CASH + " e_authority=" + AIError.ERR_LOCAL_AUTHORITY_REFUSES
          + " e_clear=" + AIError.ERR_AREA_NOT_CLEAR + " e_flat=" + AIError.ERR_FLAT_LAND_REQUIRED
          + " e_site=" + AIError.ERR_SITE_UNSUITABLE
          + " e_town_stations=" + AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN
          + " e_too_close=" + AIStation.ERR_STATION_TOO_CLOSE_TO_ANOTHER_STATION
          + " towns=" + townsStr);
    }
    if (sliced) {
      resumeState.c78Year <- c78Year;
      resumeState.c78Gen <- c78Gen;
    }
  }
  local stationLimitedTowns = sliced ? resumeState.stationLimitedTowns : {};
  local bestPlan = sliced ? resumeState.bestPlan : null;
  /* GetMonthlyMaintenanceCost expose le tarif potentiel, pas une depense toujours active.
   * CompaniesGenStatistics ne le debite que si le reglage de partie est arme. La configuration
   * gelee le laisse a false : compter ce tarif rendait toutes les paires de la graine 42
   * artificiellement deficitaires (270 000/an pour deux AT_LARGE). */
  local infrastructureMaintenance =
      AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local comboStart = sliced ? resumeState.combo : 0;

  ctx.combos = combos;
  ctx.servedDiag = servedDiag;
  ctx.hubIndex = hubIndex;
  ctx.c83TopTownIds = c83TopTownIds;
  ctx.towns = towns;
  ctx.limit = limit;
  ctx.c78Year = c78Year;
  ctx.c78Gen = c78Gen;
  ctx.stationLimitedTowns = stationLimitedTowns;
  ctx.bestPlan = bestPlan;
  ctx.infrastructureMaintenance = infrastructureMaintenance;
  ctx.comboStart = comboStart;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;

  if (V278_AIR_LAZY_SITES && sliced) OpexV278StorePrepare(ctx);
  return true;
}

/* 2. Recherche des sites : sondage des villes candidates et revalidation avant classement. */
function OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo)
{
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local opsBudget = ctx.opsBudget;
  local deadlineTick = ctx.deadlineTick;
  local limit = ctx.limit;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local towns = ctx.towns;
  local lines = ctx.lines;
  local targetTownId = ctx.targetTownId;
  local servedDiag = ctx.servedDiag;
  local c83TopTownIds = ctx.c83TopTownIds;
  local c78Gen = ctx.c78Gen;
  local c78Year = ctx.c78Year;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local bestPlan = ctx.bestPlan;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  local sites = resumingCombo ? resumeState.sites : [];
  if (!resumingCombo) {
    local scanSites = sliced ? resumeState.scanSites : [];
    local probes = sliced && resumeState.scanProbes != null
        ? resumeState.scanProbes
        : {
            left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
            stationLimitedTowns = stationLimitedTowns
          };
    local scanStart = sliced ? resumeState.scanIndex : 0;
    local scanEnd = limit;
    if (V278_AIR_LAZY_SITES && ("v278ScanEnd" in ctx)) scanEnd = ctx.v278ScanEnd;
    local testedBefore = probes.tested;
    local cheapBefore = ("cheapSkip" in probes) ? probes.cheapSkip : 0;
    local foundBefore = scanSites.len();
    local tSites0 = AIController.GetTick();
    local lSites0 = AIController.GetOpsTillSuspend();
    for (local i = scanStart; i < scanEnd; i++) {
      probes.townsLeft = limit - i;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      if (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(towns[i], null, -1, ctx.catalog)) {
        /* Levier A : bridage de difficulte (niveaux 0 et 1). Niveaux 2 et 3 : zero opcode. */
      } else if (towns[i].id in stationLimitedTowns) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_station_limit", 1);
        if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_station_limit");
      } else {
        /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
         * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
         * construction aerienne sur une carte partiellement couverte. */
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        local skipServed = isServed && !c83OwnSecondSlot;
        if (skipServed) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "origin_served", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=origin_served");
        } else if (towns[i].pop < V93_AIRPORT_MIN_POP) {
          /* V93 fige : plancher minimal, grand ou petit. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_v93", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_v93");
        } else {
          local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
              ? targetTownId : -1;
          if (c78Gen && ("c78NoSite" in probes)) probes.c78NoSite = null;
          local v278Started = V278_AIR_LAZY_SITES ? AIController.GetTick() : -1;
          local site = OpexAirFindSite(towns[i], airport, probes, c83RequiredSlotTown);
          if (site != null) {
            if (c83OwnSecondSlot) site.c83OwnSecondSlot <- true;
            if (V278_AIR_LAZY_SITES) OpexV278RememberFoundSite(site, airport, v278Started);
            scanSites.append(site);
            if (c78Gen) {
              if (towns[i].pop < 600) {
                OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site v93=1 pop=" + towns[i].pop);
              } else {
                OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site");
              }
            }
          }
          else {
            if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "no_site", 1);
            if (c78Gen) {
              local c78Outcome = "no_site_terrain";
              if (("c78NoSite" in probes) && probes.c78NoSite != null) c78Outcome = probes.c78NoSite;
              if (c78Outcome != "no_site_slot" && OpexAirC83SlotSignalEnabled()
                  && AITown.GetAllowedNoise(towns[i].id) < 1) {
                c78Outcome = "no_site_slot";
              }
              OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=" + c78Outcome);
            }
          }
        }
      }
      if (sliced) {
        resumeState.combo = comboIndex;
        resumeState.scanIndex = i + 1;
        resumeState.scanSites = scanSites;
        resumeState.scanProbes = probes;
        local scanSliceOps = _calcDeltaOps(t0_all, l0_all);
        if ((opsBudget > 0 && scanSliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
          perfOpsSites += _calcDeltaOps(tSites0, lSites0);
          perfProbesCount += probes.tested - testedBefore;
          perfCheapSkip += (("cheapSkip" in probes) ? probes.cheapSkip : 0) - cheapBefore;
          perfSitesFound += scanSites.len() - foundBefore;
          resumeState.bestPlan = bestPlan;
          resumeState.stationLimitedTowns = stationLimitedTowns;
          resumeState.perfOpsSites = perfOpsSites;
          resumeState.perfOpsEval = perfOpsEval;
          resumeState.perfProbesCount = perfProbesCount;
          resumeState.perfCheapSkip = perfCheapSkip;
          resumeState.perfSitesFound = perfSitesFound;
          resumeState.totalOps += scanSliceOps;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          return false;
        }
      }
    }
    perfOpsSites += _calcDeltaOps(tSites0, lSites0);
    if (sliced) {
      perfProbesCount += probes.tested - testedBefore;
      perfCheapSkip += (("cheapSkip" in probes) ? probes.cheapSkip : 0) - cheapBefore;
      perfSitesFound += scanSites.len() - foundBefore;
    } else {
      perfProbesCount += probes.tested;
      if ("cheapSkip" in probes) perfCheapSkip += probes.cheapSkip;
      perfSitesFound += scanSites.len();
    }

    /* C78.4 : la revalidation peut elle aussi consommer plusieurs ticks. Elle
     * reprend par index de site ; aucun site valide n'est sonde deux fois juste
     * parce qu'une tranche a rendu la main. */
    local rankableSites = sliced ? resumeState.rankSites : [];
    local rankStart = sliced ? resumeState.rankIndex : 0;
    for (local rankIndex = rankStart; rankIndex < scanSites.len(); rankIndex++) {
      local site = scanSites[rankIndex];
      if (V278_AIR_LAZY_SITES
          ? OpexV278SiteOk(site, airport, plane, stationLimitedTowns)
          : OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
        rankableSites.append(site);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("air", "site_stale_before_rank", 1);
      }
      if (sliced) {
        resumeState.combo = comboIndex;
        resumeState.rankIndex = rankIndex + 1;
        resumeState.rankSites = rankableSites;
        local rankSliceOps = _calcDeltaOps(t0_all, l0_all);
        if ((opsBudget > 0 && rankSliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
          resumeState.bestPlan = bestPlan;
          resumeState.stationLimitedTowns = stationLimitedTowns;
          resumeState.perfOpsSites = perfOpsSites;
          resumeState.perfOpsEval = perfOpsEval;
          resumeState.perfProbesCount = perfProbesCount;
          resumeState.perfCheapSkip = perfCheapSkip;
          resumeState.perfSitesFound = perfSitesFound;
          resumeState.totalOps += rankSliceOps;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          return false;
        }
      }
    }
    sites = rankableSites;
    if (sliced) {
      resumeState.combo = comboIndex;
      resumeState.a = 0;
      resumeState.b = 1;
      resumeState.sites = sites;
      resumeState.scanIndex = 0;
      resumeState.scanSites = [];
      resumeState.scanProbes = null;
      resumeState.rankIndex = 0;
      resumeState.rankSites = [];
    }
  }
  /* En mode reprenable, ne pas reconstruire le meme panneau a chaque
   * tranche de paires. Outre la pollution de SIGN, AISign.BuildSign consomme
   * des opcodes et faisait de la reprise elle-meme une part majeure du cout. */
  if (!sliced || !resumingCombo) {
    OpexSign(AIMap.GetTileIndex(1, 3), "AS|S=" + sites.len() + "|A=" + airport.name);
  }

  ctx.sites = sites;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;
  return true;
}

/* 3. Arm Ãƒâ€šÃ‚Â« nouvelles paires Ãƒâ€šÃ‚Â» : evaluation de toutes les paires (a, b) de sites neufs. */
function OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo)
{
  local sites = ctx.sites;
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local opsBudget = ctx.opsBudget;
  local deadlineTick = ctx.deadlineTick;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local targetTownId = ctx.targetTownId;
  local lines = ctx.lines;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local projects = ctx.projects;
  local c78Gen = ctx.c78Gen;
  local c78Year = ctx.c78Year;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local bestPlan = ctx.bestPlan;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  local tEval0 = AIController.GetTick();
  local lEval0 = AIController.GetOpsTillSuspend();
  local siteValidity = {};
  /* Une regeneration AIR ciblee sur une ville ne conservera plus tard que les
   * projets qui touchent cette ville. OpexAirPlansPrepare met deja la cible en
   * tete : dans le cas normal, evaluer seulement a=0 transforme C(n,2) en O(n)
   * sans changer l'ensemble de candidats finalement reinjecte. Si l'invariant
   * ne tient pas, repli exact sur le parcours complet + filtre historique. */
  local targetSiteIndex = -1;
  if (targetTownId >= 0) {
    for (local targetIndex = 0; targetIndex < sites.len(); targetIndex++) {
      if (sites[targetIndex].town.id == targetTownId) {
        targetSiteIndex = targetIndex;
        break;
      }
    }
  }
  local pairOuterLimit = sites.len();
  if (targetTownId >= 0 && targetSiteIndex < 0) pairOuterLimit = 0;
  else if (targetTownId >= 0 && targetSiteIndex == 0) pairOuterLimit = 1;
  local startA = sliced && resumeState.combo == comboIndex ? resumeState.a : 0;
  local pairProgress = false;
  for (local a = startA; a < pairOuterLimit; a++) {
    local startB = sliced && resumeState.combo == comboIndex && a == startA
        ? resumeState.b : a + 1;
    for (local b = startB; b < sites.len(); b++) {
      if (sliced) {
        resumeState.bestPlan = bestPlan;
        resumeState.perfOpsSites = perfOpsSites;
        resumeState.perfOpsEval = perfOpsEval + _calcDeltaOps(tEval0, lEval0);
        resumeState.perfProbesCount = perfProbesCount;
        resumeState.perfCheapSkip = perfCheapSkip;
        resumeState.perfSitesFound = perfSitesFound;
        local sliceOps = _calcDeltaOps(t0_all, l0_all);
        /* Toujours consommer au moins UNE paire par appel. Le cout fixe de
         * reprise peut depasser le reliquat du tick ; rendre la main avant la
         * premiere paire bloquait alors eternellement sur le meme curseur. */
        if (pairProgress && ((opsBudget > 0 && sliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick))) {
          resumeState.totalOps += sliceOps;
          ctx.bestPlan = bestPlan;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          return false;
        }
        resumeState.combo = comboIndex;
        resumeState.sites = sites;
        local nextA = a;
        local nextB = b + 1;
        if (nextB >= sites.len()) {
          nextA = a + 1;
          nextB = nextA + 1;
        }
        resumeState.a = nextA;
        resumeState.b = nextB;
        pairProgress = true;
        if (resumingCombo) {
          local keyA = sites[a].anchor;
          local keyB = sites[b].anchor;
          if (!(keyA in siteValidity)) {
            siteValidity.rawset(keyA, OpexAirSiteStillBuildable(
                sites[a], airport, plane, false, stationLimitedTowns));
          }
          if (!siteValidity[keyA]) continue;
          if (!(keyB in siteValidity)) {
            siteValidity.rawset(keyB, OpexAirSiteStillBuildable(
                sites[b], airport, plane, false, stationLimitedTowns));
          }
          if (!siteValidity[keyB]) continue;
        }
      }
      local pairMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airPairs++;
      if (targetTownId >= 0
          && sites[a].town.id != targetTownId && sites[b].town.id != targetTownId) continue;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);

      local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      sites[a].anchor, sites[b].anchor);
      local flightDistance = OpexFlightDistance(sites[a].anchor, sites[b].anchor);
      if (distance < minDist) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 0, sites[a], sites[b],
            airport, plane, distance, flightDistance, orderDistance, minDist);
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }

      if (abandoned != null) {
        if (OpexAirPairIsAbandoned(abandoned, sites[a], sites[b])) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }

      local popA = sites[a].town.pop;
      local popB = sites[b].town.pop;
      local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local opcodePadding = 0;
      if (monthlyPax < 10) monthlyPax = 10;
      if (a == 0 && b == 1 && !(V278_AIR_LAZY_SITES && ("v278SinglePair" in ctx))) {
        OpexSign(AIMap.GetTileIndex(1, 5), "AX|PA=" + popA + "|PB=" + popB + "|MPX=" + monthlyPax);
      }

      local plan = {
        siteA = sites[a], siteB = sites[b], distance = flightDistance,
        orderDistance = orderDistance,
        airport = airport, plane = plane,
        monthlyPax = monthlyPax, planes = 1, capital = 0, economics = null,
        reuseA = false, reuseB = false, hubRoutes = 0, arm = "newpair",
        c83OwnSecondSlotA = ("c83OwnSecondSlot" in sites[a]) && sites[a].c83OwnSecondSlot,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in sites[b]) && sites[b].c83OwnSecondSlot,
      };
      local routeChoice = OpexC121CatalogChoice(catalog, plan, ctx.lines);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      local portfolioEconomics = (routeChoice != null && ("portfolioEconomics" in routeChoice) && routeChoice.portfolioEconomics != null)
          ? routeChoice.portfolioEconomics : null;
      local admissionEconomics = economics;
      if (EQUIPMENT_ROI_PROBE && routePlane != null && economics != null) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 2, opcodePadding, economics, "pre_admission_newpair");
      }
      if (economics == null) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "economics_unavailable", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
        continue;
      }

      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (portfolioEconomics != null) plan.portfolioEconomics <- portfolioEconomics;
      plan.targetPlanes <- routeChoice.targetPlanes;
      OpexAirReserveJoinedStops(catalog, plan);

      if (a == 0 && b == 1 && !(V278_AIR_LAZY_SITES && ("v278SinglePair" in ctx))) {
        OpexSign(AIMap.GetTileIndex(1, 8), "AY|" + economics.capital + "|"
                                              + economics.profitAnnual);
        OpexSign(AIMap.GetTileIndex(1, 9), "AV|" + routePlane.speed + "|" + routePlane.capacity
                                              + "|" + economics.planes + "|"
                                              + economics.oneWayDays.tointeger());
      }
      if (admissionEconomics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "profit_nonpositive", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
      } else {
        if (c78Gen) {
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
        }
        bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
      }
      if (pairMark != null) OpexSpanAgg("air.pair", pairMark);
    }
  }
  perfOpsEval += _calcDeltaOps(tEval0, lEval0);
  if (sliced) {
    resumeState.a = sites.len();
    resumeState.b = sites.len();
    resumeState.bestPlan = bestPlan;
    resumeState.perfOpsEval = perfOpsEval;
    local pairSliceOps = _calcDeltaOps(t0_all, l0_all);
    if ((opsBudget > 0 && pairSliceOps >= opsBudget)
        || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
      resumeState.perfOpsSites = perfOpsSites;
      resumeState.perfProbesCount = perfProbesCount;
      resumeState.perfCheapSkip = perfCheapSkip;
      resumeState.perfSitesFound = perfSitesFound;
      resumeState.totalOps += pairSliceOps;
      ctx.bestPlan = bestPlan;
      ctx.perfOpsSites = perfOpsSites;
      ctx.perfOpsEval = perfOpsEval;
      ctx.perfProbesCount = perfProbesCount;
      ctx.perfCheapSkip = perfCheapSkip;
      ctx.perfSitesFound = perfSitesFound;
      return false;
    }
  }

  ctx.bestPlan = bestPlan;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;
  return true;
}

/* AIR 03/10 2 : signature topologique bon marche. Le nombre de lignes
 * aeriennes vivantes reprend le filtre de la decouverte (deadStreak < 2).
 * Le nombre de gares aeroport est celui de la compagnie. Deux topologies
 * distinctes de memes effectifs partagent donc la signature. */
function OpexAir0310HubTopologySignature(lines)
{
  local live = 0;
  if (lines != null) {
    foreach (line in lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      if (("deadStreak" in line) && line.deadStreak >= 2) continue;
      live++;
    }
  }
  local stations = 0;
  local stationList = AIStationList(AIStation.STATION_AIRPORT);
  if (stationList != null) stations = stationList.Count();
  return live + ":" + stations;
}

function OpexAir0310NoteHubOrigin(ctx, orphan)
{
  if (!("air0310HubOrphan" in ctx)) ctx.air0310HubOrphan <- [];
  ctx.air0310HubOrphan.append(orphan);
}

function OpexAir0310CopyHubList(hubs)
{
  local copy = [];
  if (hubs == null) return copy;
  foreach (hub in hubs) {
    copy.append({
      town = hub.town,
      anchor = hub.anchor,
      stationId = hub.stationId,
      routes = hub.routes,
    });
  }
  return copy;
}

function OpexAir0310CopySiteList(sites)
{
  local copy = [];
  if (sites == null) return copy;
  foreach (site in sites) copy.append(site);
  return copy;
}

/* Meme resolution que la decouverte des hubs issus d'une ligne. Les orphelins
 * gardent routes = 0 : la decouverte ne consulte pas l'index pour eux. */
function OpexAir0310CountStationRoutes(ctx, stationId)
{
  local hubIndex = ctx.hubIndex;
  if (hubIndex != null) {
    if (stationId in hubIndex.routes) return hubIndex.routes[stationId];
    return 0;
  }
  local routeCount = 0;
  local lines = ctx.lines;
  if (lines == null) return 0;
  foreach (other in lines) {
    if (!("mode" in other) || other.mode != "air") continue;
    local otherA = OpexAirLineStationId(other, 0);
    local otherB = OpexAirLineStationId(other, 1);
    if (otherA == stationId || otherB == stationId) routeCount++;
  }
  return routeCount;
}

/* AC04-A-v3 : ne pas modifier l'ordre de decouverte, les indices de curseur
 * ni la longueur des snapshots. Une station non retenue car pleine par
 * DiscoverHubs pouvait revenir avec routes=0 par le bras orphelin. La
 * classification au point d'usage lit l'index C80 deja construit (O(1)),
 * avec repli historique si C80 est OFF. Les lignes deadStreak>=2 comptent,
 * comme dans OpexAirBatchHubHasCapacity avant construction. */
function OpexAC04ValidateHubsAtUsage(ctx)
{
  foreach (hub in ctx.hubs) {
    hub.ac04Blocked <- false;
    if (hub.routes != 0) continue;
    local effective = OpexAir0310CountStationRoutes(ctx, hub.stationId);
    if (effective <= 0) continue;
    if (!AIMap.IsValidTile(hub.anchor) || !AIAirport.IsAirportTile(hub.anchor)) {
      hub.ac04Blocked = true;
      continue;
    }
    hub.routes = effective;
    hub.ac04Blocked = effective >= OpexAirAirportMaxRoutes(AIAirport.GetAirportType(hub.anchor));
  }
}

function OpexAir0310RefreshHubRoutes(ctx, orphan)
{
  local hubs = ctx.hubs;
  if (hubs == null) return;
  for (local i = 0; i < hubs.len(); i++) {
    local isOrphan = orphan != null && i < orphan.len() && orphan[i];
    if (isOrphan) continue;
    hubs[i].routes = OpexAir0310CountStationRoutes(ctx, hubs[i].stationId);
  }
}

function OpexAir0310RestoredHubUsable(ctx, hub)
{
  if (hub == null || !("stationId" in hub)) return false;
  if (!("air0310HubLive" in ctx)) ctx.air0310HubLive <- {};
  local key = hub.stationId;
  if (key in ctx.air0310HubLive) return ctx.air0310HubLive[key];
  local ok = AIMap.IsValidTile(hub.anchor) && AIAirport.IsAirportTile(hub.anchor)
      && AIStation.IsValidStation(hub.stationId);
  if (ok && hub.routes >= OpexAirAirportMaxRoutes(AIAirport.GetAirportType(hub.anchor))) ok = false;
  ctx.air0310HubLive.rawset(key, ok);
  return ok;
}

function OpexAir0310RestoredSiteUsable(ctx, site, airport, plane)
{
  if (site == null || !("anchor" in site)) return false;
  if (!("air0310SiteLive" in ctx)) ctx.air0310SiteLive <- {};
  local key = site.anchor;
  if (key in ctx.air0310SiteLive) return ctx.air0310SiteLive[key];
  local ok = OpexAirSiteStillBuildable(site, airport, plane, false, ctx.stationLimitedTowns);
  ctx.air0310SiteLive.rawset(key, ok);
  return ok;
}

/* Paires deja admises dans ce scan pour cet aeroport. Le moteur choisi peut
 * differer de l'avion du combo : la cle est le bras, le type d'aeroport et
 * la paire de villes. hubHubJ repart a 1, pas a 0 : 0 evaluerait un hub
 * contre lui-meme. */
function OpexAir0310RememberPublishedHubPairs(ctx, airport)
{
  local skip = {};
  local projects = ctx.projects;
  if (projects != null && airport != null && ("type" in airport)) {
    local airportType = airport.type;
    foreach (plan in projects) {
      if (plan == null) continue;
      if (!("arm" in plan) || (plan.arm != "hubsite" && plan.arm != "hubhub")) continue;
      if (!("airport" in plan) || plan.airport == null || !("type" in plan.airport)
          || plan.airport.type != airportType) continue;
      if (!("siteA" in plan) || !("siteB" in plan) || plan.siteA == null || plan.siteB == null) continue;
      if (!("town" in plan.siteA) || plan.siteA.town == null || !("tile" in plan.siteA.town)) continue;
      if (!("town" in plan.siteB) || plan.siteB.town == null || !("tile" in plan.siteB.town)) continue;
      skip.rawset(plan.arm + "|" + airportType + "|" + OpexAirPairKey(plan.siteA, plan.siteB), true);
    }
  }
  ctx.resumeState.air0310HubSkip <- skip;
  ctx.air0310HubSkip = skip;
}

function OpexAir0310SkipRestoredPair(ctx, airport, arm, hubA, hubB, site, plane)
{
  if (ctx.air0310HubSkip != null && airport != null && hubA != null) {
    local other = site != null ? site : hubB;
    if (other != null) {
      local key = arm + "|" + airport.type + "|" + OpexAirPairKey(hubA, other);
      if (key in ctx.air0310HubSkip) return true;
    }
  }
  if (!ctx.air0310HubRestored) return false;
  if (hubA != null && !OpexAir0310RestoredHubUsable(ctx, hubA)) return true;
  if (hubB != null && !OpexAir0310RestoredHubUsable(ctx, hubB)) return true;
  if (site != null && !OpexAir0310RestoredSiteUsable(ctx, site, airport, plane)) return true;
  return false;
}

/* "reuse" : meme combo, meme signature. "invalidate" : meme combo, signature
 * differente, curseurs remis au depart. "discover" : pas de snapshot
 * utilisable. Les compteurs vivent dans le curseur du scan. */
function OpexAir0310HubSnapshotPrepare(ctx, comboIndex, airport, plane)
{
  local resumeState = ctx.resumeState;
  local sig = OpexAir0310HubTopologySignature(ctx.lines);
  ctx.air0310HubSig <- sig;
  ctx.air0310HubRestored = false;
  ctx.air0310HubSkip = ("air0310HubSkip" in resumeState) ? resumeState.air0310HubSkip : null;
  ctx.air0310HubLive <- {};
  ctx.air0310SiteLive <- {};
  local snap = ("air0310HubSnap" in resumeState) ? resumeState.air0310HubSnap : null;
  if (snap != null && snap.combo == comboIndex && snap.sig == sig) {
    ctx.hubs = OpexAir0310CopyHubList(snap.hubs);
    ctx.sites = OpexAir0310CopySiteList(snap.sites);
    OpexAir0310RefreshHubRoutes(ctx, ("orphan" in snap) ? snap.orphan : null);
    ctx.air0310HubRestored = true;
    return "reuse";
  }
  if (snap != null && snap.combo == comboIndex) {
    delete resumeState.air0310HubSnap;
    resumeState.hubPhase <- 0;
    resumeState.hubSiteI <- 0;
    resumeState.hubSiteJ <- 0;
    resumeState.hubHubI <- 0;
    resumeState.hubHubJ <- 1;
    OpexAir0310RememberPublishedHubPairs(ctx, airport);
    return "invalidate";
  }
  return "discover";
}

function OpexAir0310HubSnapshotStore(ctx, comboIndex)
{
  local orphan = ("air0310HubOrphan" in ctx) ? ctx.air0310HubOrphan : [];
  local orphanCopy = [];
  foreach (flag in orphan) orphanCopy.append(flag ? 1 : 0);
  local sig = ("air0310HubSig" in ctx) ? ctx.air0310HubSig
      : OpexAir0310HubTopologySignature(ctx.lines);
  ctx.resumeState.air0310HubSnap <- {
    combo = comboIndex,
    sig = sig,
    hubs = OpexAir0310CopyHubList(ctx.hubs),
    sites = OpexAir0310CopySiteList(ctx.sites),
    orphan = orphanCopy,
  };
}

function OpexAir0310HubSnapshotCount(ctx, kind)
{
  local resumeState = ctx.resumeState;
  if (!("air0310HubCounts" in resumeState)) {
    resumeState.air0310HubCounts <- { discover = 0, reuse = 0, invalidate = 0 };
  }
  local counts = resumeState.air0310HubCounts;
  if (kind == "discover") counts.discover++;
  else if (kind == "reuse") counts.reuse++;
  else if (kind == "invalidate") counts.invalidate++;
  if (PROBE_SPAN_TRACE || C56_TASK_TRACE) {
    OpexDecide("AIR0310_HUB_SNAPSHOT", "discover=" + counts.discover
        + " reuse=" + counts.reuse
        + " invalidate=" + counts.invalidate);
  }
}

/* 4. Decouverte des hubs : lignes existantes et aeroports orphelins. */
/* AC04-B adopte : un supplement est distinct seulement par son ANCRE
 * physique. C83 peut conserver plusieurs ancres dans la meme ville. */
function OpexAC04ExtraSiteAlreadyKnown(sites, candidate)
{
  if (sites == null || candidate == null || !("anchor" in candidate)) return false;
  foreach (site in sites) {
    if (site != null && ("anchor" in site) && site.anchor == candidate.anchor)
      return true;
  }
  return false;
}

function OpexAirPlansDiscoverHubs(ctx, combo, airport, plane)
{
  /* Bras hub : un aeroport existant, rentable et non sature (max 8 routes), plus UNE destination. */
  local hubs = [];
  local sites = ctx.sites;
  local lines = ctx.lines;
  local limit = ctx.limit;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local towns = ctx.towns;
  local targetTownId = ctx.targetTownId;
  local servedDiag = ctx.servedDiag;
  local c83TopTownIds = ctx.c83TopTownIds;
  local hubIndex = ctx.hubIndex;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  if (lines != null) {
    if (sites.len() < AIR_HUB_NEW_SITE_POOL) {
      local hubProbes = {
        left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
        stationLimitedTowns = stationLimitedTowns
      };
      local tHubSites0 = AIController.GetTick();
      local lHubSites0 = AIController.GetOpsTillSuspend();
      local hubScanEnd = limit;
      for (local i = 0; i < hubScanEnd && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
        hubProbes.townsLeft = limit - i;
        if (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(towns[i], null, -1, ctx.catalog)) continue;
        if (towns[i].id in stationLimitedTowns) {
          continue;
        }
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        if (isServed && !c83OwnSecondSlot) continue;
        /* V93 fige : plancher sanitaire commun aux types d'aeroport. */
        if (towns[i].pop < V93_AIRPORT_MIN_POP) continue;
        if (combo.kind == "small" && towns[i].pop >= 2500) continue;
        local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
            ? targetTownId : -1;
        local extraSite = OpexAirFindSite(towns[i], airport, hubProbes, c83RequiredSlotTown);
        if (extraSite != null) {
          if (OpexAC04ExtraSiteAlreadyKnown(sites, extraSite))
            continue;
          if (c83OwnSecondSlot) extraSite.c83OwnSecondSlot <- true;
          /* v93=1 seulement si le scan principal n'a pas deja retenu cette ville. */
          if (towns[i].pop < 600 && ("c78Gen" in ctx) && ctx.c78Gen) {
            local v93Already = false;
            foreach (prev in sites) {
              if (("town" in prev) && prev.town != null && ("id" in prev.town) && prev.town.id == towns[i].id) {
                v93Already = true;
                break;
              }
            }
            if (!v93Already) {
              OpexC78Log("C78_AIRTOWN", "year=" + ctx.c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site v93=1 pop=" + towns[i].pop);
            }
          }
          sites.append(extraSite);
          ctx.perfSitesFound++;
        }
      }
      ctx.perfOpsSites += _calcDeltaOps(tHubSites0, lHubSites0);
      ctx.perfProbesCount += hubProbes.tested;
      if ("cheapSkip" in hubProbes) ctx.perfCheapSkip += hubProbes.cheapSkip;
    }
    local seenStations = {};
    foreach (line in lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      if (("deadStreak" in line) && line.deadStreak >= 2) continue;
      /* L'ancre d'un hub est la tuile d'aeroport (line.stationA/B). */
      local ends = [
        { anchor = line.stationA, origin = line.originA, stationId = line.stationA },
        { anchor = line.stationB, origin = line.originB, stationId = line.stationB },
      ];
      foreach (end in ends) {
        if (!AIMap.IsValidTile(end.anchor) || !AIAirport.IsAirportTile(end.anchor)) continue;
        local existingType = AIAirport.GetAirportType(end.anchor);
        if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
        /* Resolution non ambigue : `end.stationId` est une tuile, et `IsValidStation(tuile)`
         * peut etre vrai par pure collision d'indices. On resout toujours depuis l'ancre. */
        local station = AIStation.GetStationID(end.anchor);
        if (!AIStation.IsValidStation(station) || (station in seenStations)) continue;

        local routeCount = 0;
        if (hubIndex != null) {
          if (station in hubIndex.routes) routeCount = hubIndex.routes[station];
        } else {
          foreach (other in lines) {
            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = OpexAirLineStationId(other, 0);
            local otherB = OpexAirLineStationId(other, 1);
            if (otherA == station || otherB == station) routeCount++;
          }
        }
        local maxRoutes = OpexAirAirportMaxRoutes(existingType);
        if (routeCount >= maxRoutes) continue;
        local townId = AITile.GetClosestTown(end.origin);
        if (townId < 0) continue;
        local hubTown = null;
        foreach (town in towns) {
          if (town.id == townId) { hubTown = town; break; }
        }
        if (hubTown == null) {
          hubTown = { id = townId, tile = end.origin, pop = AITown.GetPopulation(townId) };
        }
        seenStations.rawset(station, true);
        hubs.append({ town = hubTown, anchor = end.anchor, stationId = station, routes = routeCount });
        OpexAir0310NoteHubOrigin(ctx, 0);
      }
    }
    /* AÃƒÆ’Ã‚Â©roports orphelins : aÃƒÆ’Ã‚Â©roports bÃƒÆ’Ã‚Â¢tis sans ligne active (ex: issu d'un BFAIL conservÃƒÆ’Ã‚Â©). */
    local orphanList = AIStationList(AIStation.STATION_AIRPORT);
    for (local st = orphanList.Begin(); !orphanList.IsEnd(); st = orphanList.Next()) {
      if (st in seenStations) continue;
      local loc = AIStation.GetLocation(st);
      if (!AIMap.IsValidTile(loc) || !AIAirport.IsAirportTile(loc)) continue;
      local existingType = AIAirport.GetAirportType(loc);
      if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
      local townId = AITile.GetClosestTown(loc);
      if (townId < 0) continue;
      local hubTown = null;
      foreach (town in towns) {
        if (town.id == townId) { hubTown = town; break; }
      }
      if (hubTown == null) {
        hubTown = { id = townId, tile = loc, pop = AITown.GetPopulation(townId) };
      }
      seenStations.rawset(st, true);
      hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 });
      OpexAir0310NoteHubOrigin(ctx, 1);
    }
  }

  /* La decouverte des hubs et des sites supplementaires peut elle aussi
   * suspendre. Revalider les destinations neuves au dernier moment avant
   * le classement hub-site. */
  if (sites.len() > 0) {
    local liveHubSites = [];
    foreach (site in sites) {
      if (OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
        liveHubSites.append(site);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("air", "site_stale_before_rank", 1);
      }
    }
    sites = liveHubSites;
  }

  if (DECISION_LOG) {
    local siteFields = sites.len() == 0 ? "none" : "";
    foreach (site in sites) {
      if (siteFields != "") siteFields += ",";
      siteFields += site.town.id + ":" + site.town.tile;
    }
    local hubFields = hubs.len() == 0 ? "none" : "";
    foreach (hub in hubs) {
      if (hubFields != "") hubFields += ",";
      hubFields += hub.town.id + ":" + hub.town.tile;
    }
    OpexDecide("AIR_PLAN_SETS", "scan=" + servedDiag.scan + " combo=" + combo.kind
               + " airport_type=" + airport.type + " plane=" + plane.id
               + " sites_count=" + sites.len() + " sites=" + siteFields
               + " hubs_count=" + hubs.len() + " hubs=" + hubFields);
  }

  ctx.sites = sites;
  ctx.hubs = hubs;
}

/* 5. Arm Ãƒâ€šÃ‚Â« hub vers site Ãƒâ€šÃ‚Â» : evaluation des paires (hub existant, site neuf). */
function OpexAirPlansHubToSite(ctx, combo, airport, plane)
{
  local hubs = ctx.hubs;
  local sites = ctx.sites;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local c78Year = ctx.c78Year;
  local c78Gen = ctx.c78Gen;
  local projects = ctx.projects;
  local bestPlan = ctx.bestPlan;
  local targetTownId = ctx.targetTownId;
  local lines = ctx.lines;

  local incrementalSlice = ctx.sliced;
  local resumeHub = incrementalSlice && ("hubSiteI" in ctx.resumeState)
      ? ctx.resumeState.hubSiteI : 0;
  local resumeSite = incrementalSlice && ("hubSiteJ" in ctx.resumeState)
      ? ctx.resumeState.hubSiteJ : 0;
  local progressed = false;
  for (local hi = resumeHub; hi < hubs.len(); hi++) {
    local hub = hubs[hi];
    if (hub.ac04Blocked) continue;
    for (local sj = hi == resumeHub ? resumeSite : 0; sj < sites.len(); sj++) {
      if (incrementalSlice) {
        local used = OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all);
        if (progressed && ((ctx.opsBudget > 0 && used >= ctx.opsBudget)
            || (ctx.deadlineTick > 0 && AIController.GetTick() >= ctx.deadlineTick))) {
          ctx.resumeState.hubSiteI <- hi;
          ctx.resumeState.hubSiteJ <- sj;
          ctx.bestPlan = bestPlan;
          return false;
        }
        progressed = true;
      }
      local site = sites[sj];
      local hubSiteMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      if ((ctx.air0310HubRestored || ctx.air0310HubSkip != null) && OpexAir0310SkipRestoredPair(ctx, airport, "hubsite", hub, null, site, plane)) continue;
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airHubSitePairs++;
      if (targetTownId >= 0
          && hub.town.id != targetTownId && site.town.id != targetTownId) continue;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
      if (distance < 20) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      hub.anchor, site.anchor);
      local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 1, hub, site,
            airport, plane, distance, flightDistance, orderDistance, 20);
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }
      if (abandoned != null) {
        if (OpexAirPairIsAbandoned(abandoned, hub, site)) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }
      local hubMonthly = (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1));
      local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local monthlyPax = hubMonthly + newMonthly;
      local opcodePadding = 0;
      if (monthlyPax < 10) monthlyPax = 10;
      local plan = {
        siteA = hub, siteB = site, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = plane, monthlyPax = monthlyPax, planes = 1,
        capital = 0, economics = null,
        reuseA = true, reuseB = false, hubRoutes = hub.routes, arm = "hubsite",
        c83OwnSecondSlotA = false,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in site) && site.c83OwnSecondSlot,
      };
      local routeChoice = OpexC121CatalogChoice(catalog, plan, ctx.lines);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      local portfolioEconomics = (routeChoice != null && ("portfolioEconomics" in routeChoice) && routeChoice.portfolioEconomics != null)
          ? routeChoice.portfolioEconomics : null;
      local admissionEconomics = economics;
      if (EQUIPMENT_ROI_PROBE && routePlane != null && economics != null) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 1, opcodePadding, economics, "pre_admission_hubsite");
      }
      if (economics == null || admissionEconomics == null || admissionEconomics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) {
          if (economics == null) OpexC73RecordRejection("air", "economics_unavailable", 1);
          else OpexC73RecordRejection("air", "profit_nonpositive", 1);
        }
        if (c78Gen) {
          if (economics == null) {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        if (hubSiteMark != null) OpexSpanAgg("air.hub_site_pair", hubSiteMark);
        continue;
      }

      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (portfolioEconomics != null) plan.portfolioEconomics <- portfolioEconomics;
      plan.targetPlanes <- routeChoice.targetPlanes;
      OpexAirReserveJoinedStops(catalog, plan);
      if (admissionEconomics.profitAnnual <= 0) {
        if (hubSiteMark != null) OpexSpanAgg("air.hub_site_pair", hubSiteMark);
        continue;
      }
      if (c78Gen) {
        OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
      }
      bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
      if (hubSiteMark != null) OpexSpanAgg("air.hub_site_pair", hubSiteMark);
    }
  }
  ctx.bestPlan = bestPlan;
  if (incrementalSlice) {
    ctx.resumeState.hubSiteI <- hubs.len();
    ctx.resumeState.hubSiteJ <- 0;
  }
  return true;
}

/* 6. Arm Ãƒâ€šÃ‚Â« hub vers hub Ãƒâ€šÃ‚Â» : liaisons directes entre deux aeroports existants. */
function OpexAirPlansHubToHub(ctx, combo, airport, plane)
{
  /* Liaisons Hub-a-Hub directes entre deux aeroports existants (capital = 1 avion seul) */
  local hubs = ctx.hubs;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local c78Year = ctx.c78Year;
  local c78Gen = ctx.c78Gen;
  local projects = ctx.projects;
  local lines = ctx.lines;
  local hubIndex = ctx.hubIndex;
  local bestPlan = ctx.bestPlan;
  local targetTownId = ctx.targetTownId;

  local incrementalSlice = ctx.sliced;
  local resumeI = incrementalSlice && ("hubHubI" in ctx.resumeState)
      ? ctx.resumeState.hubHubI : 0;
  local resumeJ = incrementalSlice && ("hubHubJ" in ctx.resumeState)
      ? ctx.resumeState.hubHubJ : 1;
  local progressed = false;
  for (local i = resumeI; i < hubs.len(); i++) {
    for (local j = i == resumeI ? resumeJ : i + 1; j < hubs.len(); j++) {
      if (incrementalSlice) {
        local used = OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all);
        if (progressed && ((ctx.opsBudget > 0 && used >= ctx.opsBudget)
            || (ctx.deadlineTick > 0 && AIController.GetTick() >= ctx.deadlineTick))) {
          ctx.resumeState.hubHubI <- i;
          ctx.resumeState.hubHubJ <- j;
          ctx.bestPlan = bestPlan;
          return false;
        }
        progressed = true;
      }
      local hub1 = hubs[i];
      local hub2 = hubs[j];
      if ((hub1.ac04Blocked || hub2.ac04Blocked)) continue;
      local hubHubMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      if ((ctx.air0310HubRestored || ctx.air0310HubSkip != null) && OpexAir0310SkipRestoredPair(ctx, airport, "hubhub", hub1, hub2, null, plane)) continue;
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airHubHubPairs++;
      if (targetTownId >= 0
          && hub1.town.id != targetTownId && hub2.town.id != targetTownId) continue;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local st1 = hub1.stationId;
      local st2 = hub2.stationId;
      local alreadyConnected = false;
      if (hubIndex != null) {
        alreadyConnected = (st1 + "|" + st2) in hubIndex.pairs;
      } else
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        /* air_hub_fix : c'est CETTE comparaison qui etait morte -- un StationID (st1/st2, issus
         * de la decouverte de hub) contre une tuile d'aeroport (line.stationA/B). */
        local oA = OpexAirLineStationId(line, 0);
        local oB = OpexAirLineStationId(line, 1);
        if (!AIStation.IsValidStation(oA) || !AIStation.IsValidStation(oB)) continue;
        if ((oA == st1 && oB == st2) || (oA == st2 && oB == st1)) {
          alreadyConnected = true; break;
        }
      }
      if (alreadyConnected) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "already_connected", 1);
        if (c78Gen) {
          local c78Dist = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + c78Dist + " outcome=already_connected P=-1 C=-1");
        }
        continue;
      }
      local distance = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
      if (distance < 20) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
      local flightDistance = OpexFlightDistance(hub1.anchor, hub2.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 2, hub1, hub2,
            airport, plane, distance, flightDistance, orderDistance, 20);
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }
      if (OpexAirPairIsAbandoned(abandoned, hub1, hub2)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
        continue;
      }
      local monthly1 = (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1));
      local monthly2 = ((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1);
      local monthlyPax = monthly1 + monthly2;
      local opcodePadding = 0;
      if (monthlyPax < 10) monthlyPax = 10;
      local plan = {
        siteA = hub1, siteB = hub2, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = plane, monthlyPax = monthlyPax, planes = 1,
        capital = 0, economics = null,
        reuseA = true, reuseB = true, hubRoutes = hub1.routes + hub2.routes,
        arm = "hubhub",
      };
      local routeChoice = OpexC121CatalogChoice(catalog, plan, lines);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      local portfolioEconomics = (routeChoice != null && ("portfolioEconomics" in routeChoice) && routeChoice.portfolioEconomics != null)
          ? routeChoice.portfolioEconomics : null;
      if (EQUIPMENT_ROI_PROBE && routePlane != null && economics != null) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 0, opcodePadding, economics, "pre_admission_hubhub");
      }
      local admissionEconomics = economics;
      if (economics == null || admissionEconomics == null || admissionEconomics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) {
          if (economics == null) OpexC73RecordRejection("air", "economics_unavailable", 1);
          else OpexC73RecordRejection("air", "profit_nonpositive", 1);
        }
        if (c78Gen) {
          if (economics == null) {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        if (hubHubMark != null) OpexSpanAgg("air.hub_hub_pair", hubHubMark);
        continue;
      }
      if (decisionEconomics != null && decisionEconomics.profitAnnual <= 0) {
        if (hubHubMark != null) OpexSpanAgg("air.hub_hub_pair", hubHubMark);
        continue;
      }

      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (portfolioEconomics != null) plan.portfolioEconomics <- portfolioEconomics;
      plan.targetPlanes <- routeChoice.targetPlanes;
      OpexAirReserveJoinedStops(catalog, plan);
      if (hubHubMark != null && admissionEconomics.profitAnnual <= 0) OpexSpanAgg("air.hub_hub_pair", hubHubMark);
      if (admissionEconomics.profitAnnual <= 0) continue;
      if (c78Gen) {
        OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
      }
      bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
      if (hubHubMark != null) OpexSpanAgg("air.hub_hub_pair", hubHubMark);
    }
  }
  ctx.bestPlan = bestPlan;
  if (incrementalSlice) {
    ctx.resumeState.hubHubI <- hubs.len();
    ctx.resumeState.hubHubJ <- 0;
  }
  return true;
}

/* 7. Finalisation : enregistrement des perf, sondes et nettoyage de la reprise. */
function OpexAirPlansFinalize(ctx)
{
  /* Mutating evaluation is restricted to ON and to the completed scan.
   * Shadow reports only the selected references and arithmetic shortlist. */
  if (ctx.fp2 != null) OpexFP2Finalize(ctx);
  if (ctx.fp2 != null && ctx.sliced
      && ("frontPax2Bounded" in ctx.resumeState))
    delete ctx.resumeState.frontPax2Bounded;
  local servedDiag = ctx.servedDiag;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local bestPlan = ctx.bestPlan;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local combos = ctx.combos;
  local projects = ctx.projects;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  if (DECISION_LOG) {
    OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
               + " null_calls=" + servedDiag.nullCalls + " empty_calls=" + servedDiag.emptyCalls
               + " nonempty_calls=" + servedDiag.nonemptyCalls + " true_calls=" + servedDiag.trueCalls
               + " false_calls=" + servedDiag.falseCalls
               + " false_towns_logged=" + servedDiag.loggedFalseCount);
  }
  local totalOps = _calcDeltaOps(t0_all, l0_all);
  if (CATALOG_COST_ACTIVE != null) {
    local cost = CATALOG_COST_ACTIVE;
    cost.airScans++;
    cost.airTowns += ctx.limit;
    cost.airCombos += combos.len();
    cost.airSiteProbes += perfProbesCount;
    cost.airSites += perfSitesFound;
    cost.airSiteOps += perfOpsSites;
    cost.airEvalOps += perfOpsEval;
    if (C121_AIR_PLAN_PERF != null) {
      cost.c121Calls += C121_AIR_PLAN_PERF.calls;
      cost.c121DemandOps += C121_AIR_PLAN_PERF.demandOps;
      cost.c121StaticOps += C121_AIR_PLAN_PERF.staticOps;
      cost.c121ScanOps += C121_AIR_PLAN_PERF.scanOps;
      cost.c121EngineEvals += C121_AIR_PLAN_PERF.engineEvals;
      cost.c121WinnerOps += C121_AIR_PLAN_PERF.winnerOps;
    }
  }
  local elapsedTicks = AIController.GetTick() - t0_all;
  if (sliced) {
    totalOps += resumeState.totalOps;
    elapsedTicks = AIController.GetTick() - resumeState.startTick;
    resumeState.totalOps = totalOps;
    resumeState.bestPlan = bestPlan;
    resumeState.done = true;
    resumeState.sites = null;
    resumeState.towns = null;
    resumeState.combos = null;
    if (V278_AIR_LAZY_SITES && ("v278Prepare" in resumeState)) delete resumeState.v278Prepare;
  }
  local elapsedDays = elapsedTicks / 74;
  if (DECISION_LOG) {
    local scanNum = (servedDiag != null && ("scan" in servedDiag)) ? servedDiag.scan : 0;
    OpexDecide("AIR_PLAN_PERF", "scan=" + scanNum + " total_ops=" + totalOps
               + " ops_sites=" + perfOpsSites + " ops_eval=" + perfOpsEval
               + " ticks=" + elapsedTicks + " days=" + elapsedDays
               + " probes=" + perfProbesCount + " cheap_skip=" + perfCheapSkip
               + " sites=" + perfSitesFound
               + " combos=" + combos.len()
               + " plans=" + (projects != null ? projects.len() : (bestPlan != null ? 1 : 0)));
  }
  AILog.Info("AIR_PLAN_PERF: total_ops=" + totalOps + " ops_sites=" + perfOpsSites
             + " ops_eval=" + perfOpsEval + " ticks=" + elapsedTicks + " days=" + elapsedDays
             + " probes=" + perfProbesCount + " cheap_skip=" + perfCheapSkip
             + " sites=" + perfSitesFound
             + " c121_calls=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.calls : 0)
             + " c121_demand_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.demandOps : 0)
             + " c121_demand_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.demandTicks : 0)
             + " c121_static_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.staticOps : 0)
             + " c121_static_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.staticTicks : 0)
             + " c121_scan_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.scanOps : 0)
             + " c121_scan_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.scanTicks : 0)
             + " c121_engine_evals=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.engineEvals : 0)
             + " c121_winner_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.winnerOps : 0)
             + " c121_winner_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.winnerTicks : 0)
             + " c121_no_winner=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.noWinner : 0)
             + " c121_endpoint_hits=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.endpointHits : 0)
             + " c121_endpoint_misses=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.endpointMisses : 0));
  OpexSign(AIMap.GetTileIndex(1, 2), "AP|T=" + totalOps + "|S=" + perfOpsSites + "|E=" + perfOpsEval + "|TK=" + elapsedTicks);
  if (C69_BOTTLENECK_PROBE) {
    local actualPlans = (projects != null) ? projects.len() : (bestPlan != null ? 1 : 0);
    OpexC73RecordProduced("air", actualPlans, actualPlans);
  }

  return bestPlan;
}

/* Index du prochain combo kind=small apres comboIndex, ou -1. Aucun appel d'API. */
function OpexAirV93NextSmallCombo(combos, comboIndex)
{
  local nextSmall = comboIndex + 1;
  while (nextSmall < combos.len()) {
    local candidate = combos[nextSmall];
    if (("kind" in candidate) && candidate.kind == "small") return nextSmall;
    nextSmall++;
  }
  return -1;
}

/* CD01 : la preparation est une sous-etape executable reutilisable sur le
 * meme contexte d'invocation. Un echec de Prepare signifie deja termine
 * (done/no combo), jamais un yield de tranche. Les sondes restent entourees
 * exactement comme dans le driver initial. */
function OpexAirPlansStepPrepare(ctx)
{
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_prepare", "-");
  local spPrepare = PROBE_SPAN_TRACE ? OpexSpanBegin("air.prepare") : null;
  local prepared = OpexAirPlansPrepare(ctx);
  if (spPrepare != null) OpexSpanEnd(spPrepare);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_prepare", "-",
      "combos=" + (ctx.combos != null ? ctx.combos.len() : 0) + " towns=" + (ctx.towns != null ? ctx.towns.len() : 0)
      + " target=" + ctx.targetTownId);
  return prepared;
}

/* CD01 : la tranche Sites possede le meme seul point de suspension que
 * FindSites (scanIndex/rankIndex et C83). L'appelant conserve son bestPlan
 * quand la sous-etape renvoie false. */
function OpexAirPlansStepFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo)
{
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_find_sites", "-");
  local spSites = PROBE_SPAN_TRACE ? OpexSpanBegin("air.sites") : null;
  local sitesOk = V278_AIR_LAZY_SITES && OpexV278LazyEnabled(ctx)
      ? OpexV278LazySites(ctx, comboIndex, combo, airport, plane)
      : OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo);
  if (spSites != null) OpexSpanEnd(spSites);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_find_sites", "-",
      "combo=" + comboIndex + " sites=" + ctx.sites.len() + " probes=" + ctx.perfProbesCount);
  return sitesOk;
}

/* CD02 : NewPairs reutilise le meme contexte et les meme curseurs a/b.
 * Aucun point de yield ni reevaluation supplementaire d'une paire. */
function OpexAirPlansStepNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo)
{
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_new_pairs", "-");
  local spPairs = PROBE_SPAN_TRACE ? OpexSpanBegin("air.new_pairs") : null;
  local pairsOk = V278_AIR_LAZY_SITES && OpexV278LazyEnabled(ctx)
      ? OpexV278LazyPairs(ctx, comboIndex, combo, airport, plane, minDist)
      : OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo);
  if (spPairs != null) OpexSpanEnd(spPairs);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_new_pairs", "-",
      "combo=" + comboIndex + " plans=" + (ctx.projects != null ? ctx.projects.len() : -1));
  return pairsOk;
}

/* CD05 : clore exactement un combo, puis expliciter le prochain combo.
 * -1 signifie break ; aucun point de yield ni nouvelle transaction. */
function OpexAirPlansCompleteCombo(ctx, comboIndex, combo)
{
    if (ctx.hubs.len() > 0) {
      OpexSign(AIMap.GetTileIndex(1, 6), "AU|" + ctx.hubs.len() + "|"
               + (ctx.bestPlan != null && ctx.bestPlan.reuseA ? 1 : 0));
    }
    OpexSign(AIMap.GetTileIndex(1, 4), "AE|S=" + ctx.sites.len() + "|B=" + (ctx.bestPlan != null ? ctx.bestPlan.economics.profitAnnual : "NO"));
    if (ctx.sliced) {
      if (V278_AIR_LAZY_SITES && ("v278Lazy" in ctx.resumeState)) delete ctx.resumeState.v278Lazy;
      ctx.resumeState.combo = comboIndex + 1;
      ctx.resumeState.a = 0;
      ctx.resumeState.b = 1;
      ctx.resumeState.sites = null;
      ctx.resumeState.scanIndex = 0;
      ctx.resumeState.scanSites = [];
      ctx.resumeState.scanProbes = null;
      ctx.resumeState.rankIndex = 0;
      ctx.resumeState.rankSites = [];
      {
        ctx.resumeState.hubPhase <- 0;
        ctx.resumeState.hubSiteI <- 0;
        ctx.resumeState.hubSiteJ <- 0;
        ctx.resumeState.hubHubI <- 0;
        ctx.resumeState.hubHubJ <- 1;
      }
      {
        if ("air0310HubSnap" in ctx.resumeState) delete ctx.resumeState.air0310HubSnap;
        if ("air0310HubSkip" in ctx.resumeState) delete ctx.resumeState.air0310HubSkip;
      }
      ctx.resumeState.bestPlan = ctx.bestPlan;
      ctx.resumeState.stationLimitedTowns = ctx.stationLimitedTowns;
      ctx.resumeState.perfOpsSites = ctx.perfOpsSites;
      ctx.resumeState.perfOpsEval = ctx.perfOpsEval;
      ctx.resumeState.perfProbesCount = ctx.perfProbesCount;
      ctx.resumeState.perfCheapSkip = ctx.perfCheapSkip;
      ctx.resumeState.perfSitesFound = ctx.perfSitesFound;
    }
    /* Un plan grand arrete la boucle. Sous V93, les combos petits qui suivent
     * sont quand meme parcourus ; les grands suivants restent sautes. A 0, le
     * booleen provoque le meme break, sans helper ni appel d'API. */
    local bestPlan = ctx.bestPlan;
    if (bestPlan != null && bestPlan.airport.allowBig) {

      if (!(("kind" in combo) && combo.kind == "small")) {
        local nextSmall = OpexAirV93NextSmallCombo(ctx.combos, comboIndex);
        if (nextSmall < 0) return -1;
        if (ctx.sliced) ctx.resumeState.combo = nextSmall;
        return nextSmall;
      }
    }
    return comboIndex + 1;
}

/* CD03 : visite et reprise du snapshot hub dans une unique phase interne.
 * Le span de decouverte reste conditionne a !reuseHubs ; aucun nouveau yield. */
function OpexAirPlansHubDiscoveryPhase(ctx, comboIndex, combo, airport, plane)
{
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hubs", "-");
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_discover", "-");
    local reuseHubs = false;
    if (ctx.sliced) {
      local hubSnapAction = OpexAir0310HubSnapshotPrepare(ctx, comboIndex, airport, plane);
      OpexAir0310HubSnapshotCount(ctx, hubSnapAction);
      reuseHubs = hubSnapAction == "reuse";
    }
    if (!reuseHubs) {
      ctx.air0310HubOrphan <- [];
      local spDisc = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_discover") : null;
      OpexAirPlansDiscoverHubs(ctx, combo, airport, plane);
      if (spDisc != null) OpexSpanEnd(spDisc);
      if (ctx.sliced) OpexAir0310HubSnapshotStore(ctx, comboIndex);
    }
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_discover", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len());
    OpexAC04ValidateHubsAtUsage(ctx);
}

/* CD04: la sous-etape hub->site maintient le checkpoint hubPhase et
 * retourne false sur exactement le meme yield qu'avant. */
function OpexAirPlansHubToSitePhase(ctx, combo, airport, plane)
{
  if (!ctx.sliced || !("hubPhase" in ctx.resumeState) || ctx.resumeState.hubPhase < 1) {
    if (!OpexAirPlansHubToSite(ctx, combo, airport, plane)) return false;
    if (ctx.sliced) ctx.resumeState.hubPhase <- 1;
  }
  return true;
}
/* `abandoned` : table des paires dont une construction a deja echoue (cle
 * canonique OpexAirPairKey), et optionnellement des
 * sites exacts et types ("air_site|airportType|anchor"). null = filtre desactive.
 * Le filtre est place APRES les tests de distance et AVANT OpexAirEconomics : les paires
 * ecartees pour distance ne paient pas la concatenation, et celles qui restent evitent le
 * calcul cher. */
function OpexAirPlans(catalog, lines = null, maxCapital = 0, projects = null, abandoned = null,
                      paxBand = PAX_BAND_ALL, targetTownId = -1,
                      resumeState = null, opsBudget = 0, deadlineTick = 0)
{
  local t0_all = AIController.GetTick();
  local l0_all = AIController.GetOpsTillSuspend();
  local _calcDeltaOps = OpexAirCalcDeltaOps;
  local ctx = {
    catalog = catalog,
    lines = lines,
    maxCapital = maxCapital,
    projects = projects,
    abandoned = abandoned,
    paxBand = paxBand,
    targetTownId = targetTownId,
    resumeState = resumeState,
    opsBudget = opsBudget,
    deadlineTick = deadlineTick,
    t0_all = t0_all,
    l0_all = l0_all,
    sliced = resumeState != null,
    combos = null,
    servedDiag = null,
    hubIndex = null,
    c83TopTownIds = null,
    towns = null,
    limit = 0,
    c78Year = -1,
    c78Gen = false,
    stationLimitedTowns = null,
    bestPlan = null,
    infrastructureMaintenance = false,
    comboStart = 0,
    perfOpsSites = 0,
    perfOpsEval = 0,
    perfProbesCount = 0,
    perfCheapSkip = 0,
    perfSitesFound = 0,
    sites = [],
    hubs = [],
    air0310HubRestored = false,
    air0310HubSkip = null,
    fp2 = null,
  };

  local spPlans = PROBE_SPAN_TRACE ? OpexSpanBegin("air.plans") : null;
  local prepared = OpexAirPlansStepPrepare(ctx);
  if (!prepared) {
    if (spPlans != null) OpexSpanEnd(spPlans);
    return ctx.bestPlan;
  }

  if (FRONT_PAX2_BOUNDED_OVERLAP > 0 && paxBand == PAX_BAND_ALL
      && catalog != null && catalog.bounds != null) {
    if (resumeState != null && ("frontPax2Bounded" in resumeState)) {
      ctx.fp2 = resumeState.frontPax2Bounded;
    } else {
      ctx.fp2 = OpexFP2NewShortlist(catalog.bounds);
      if (resumeState != null) resumeState.frontPax2Bounded <- ctx.fp2;
    }
  }

  for (local comboIndex = ctx.comboStart; comboIndex < ctx.combos.len(); comboIndex++) {
    local combo = ctx.combos[comboIndex];
    local airport = combo.airport;
    local plane = combo.plane;
    local minDist = (plane.speed >= 400) ? 32 : 30;
    local resumingCombo = ctx.sliced && ctx.resumeState.combo == comboIndex && ctx.resumeState.sites != null;

    local sitesOk = OpexAirPlansStepFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo);
    if (!sitesOk) {
      if (spPlans != null) OpexSpanEnd(spPlans);
      return ctx.bestPlan;
    }

    local pairsOk = OpexAirPlansStepNewPairs(ctx, comboIndex, combo, airport, plane,
        minDist, resumingCombo);
    if (!pairsOk) {
      if (spPlans != null) OpexSpanEnd(spPlans);
      return ctx.bestPlan;
    }

    OpexAirPlansHubDiscoveryPhase(ctx, comboIndex, combo, airport, plane);

    local c56PlansBefore = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_site", "-");
    local tHubEval0 = AIController.GetTick();
    local lHubEval0 = AIController.GetOpsTillSuspend();
    local spHubSite = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_site") : null;
    if (!OpexAirPlansHubToSitePhase(ctx, combo, airport, plane)) {
      if (spHubSite != null) OpexSpanEnd(spHubSite);
      if (spPlans != null) OpexSpanEnd(spPlans);
      return ctx.bestPlan;
    }
    if (spHubSite != null) OpexSpanEnd(spHubSite);
    local c56PlansMid = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_site", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len() + " admitted=" + (c56PlansMid - c56PlansBefore));
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_hub", "-");
    local spHubHub = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_hub") : null;
    local hubsOk = OpexAirPlansHubToHub(ctx, combo, airport, plane);
    if (spHubHub != null) OpexSpanEnd(spHubHub);
    if (!hubsOk) {
      if (spPlans != null) OpexSpanEnd(spPlans);
      return ctx.bestPlan;
    }
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_hub", "-",
        "hubs=" + ctx.hubs.len() + " admitted=" + (((ctx.projects != null) ? ctx.projects.len() : 0) - c56PlansMid));
    ctx.perfOpsEval += _calcDeltaOps(tHubEval0, lHubEval0);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hubs", "-", "hubs=" + ctx.hubs.len());

    local nextCombo = OpexAirPlansCompleteCombo(ctx, comboIndex, combo);
    if (nextCombo < 0) break;
    comboIndex = nextCombo - 1;
  }

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_finalize", "-");
  local spFinal = PROBE_SPAN_TRACE ? OpexSpanBegin("air.finalize") : null;
  local finalPlan = OpexAirPlansFinalize(ctx);
  if (spFinal != null) OpexSpanEnd(spFinal);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_finalize", "-");
  if (spPlans != null) OpexSpanEnd(spPlans);
  return finalPlan;
}

