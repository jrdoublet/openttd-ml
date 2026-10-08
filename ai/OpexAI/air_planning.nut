/* Module AIR extrait de builder_air.nut (R11) : planification des liaisons (OpexAirPlans et etapes). */
/* An anchor only describes the north-west corner. Its buildability depends on
 * the airport footprint, so the airport type is part of the durable-site key. */
function OpexAirSitePaddingKey(site, airportType)
{
  return "air_site|" + airportType + "|" + site.anchor;
}

function OpexAirTownPaddingKey(site)
{
  return "air_town_limit|" + site.town.tile;
}

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

/* EXP_AIR_HUB_PAIR_PREFILTER (globale false / setting 0 par defaut) :
 * index du seul predicat OpexAirTownCentersLinked, egal a la derniere
 * boucle de OpexAirBatchPlanStillLive. Centres commerciaux originA/B,
 * NON ancres, StationID, TownID ou villes de slot. Le contrat final est
 * symetrique et independant du cargo : ne pas ajouter de filtre cargo,
 * deadStreak ou scrapping ici, ni de fermeture transitive du reseau.
 * Aucune reservation des candidats : les variantes d'une paire encore
 * libre (sites, aeroports, moteurs, cargos) continuent toutes leur evaluation. */
function OpexAirHubTownPairKey(tileA, tileB)
{
  if (tileA == null || tileB == null) return null;
  return tileA <= tileB ? (tileA + "|" + tileB) : (tileB + "|" + tileA);
}

function OpexAirHubPairPrefilterLinked(ctx, tileA, tileB)
{
  if (ctx.lines == null || tileA == null || tileB == null) return false;
  /* Paresseux : pas de scan sans paire hub eligible. ctx est neuf a CHAQUE
   * appel OpexAirPlans, y compris chaque reprise. Jamais dans resumeState,
   * un plan, une globale ou Save. Les lignes Opex ne mutent pas pendant
   * cet appel synchrone ; une autre tranche reconstruit depuis ctx.lines.
   * Partage entre bras/combos, pas entre contextes. La revalidation finale
   * reste obligatoire apres toute evolution de la topologie. */
  if (!("airHubTownPairs" in ctx)) {
    local pairs = {};
    foreach (line in ctx.lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      local key = OpexAirHubTownPairKey(line.originA, line.originB);
      if (key != null) pairs.rawset(key, true);
    }
    ctx.airHubTownPairs <- pairs;
    if (DECISION_LOG || C69_BOTTLENECK_PROBE) {
      local fields = "phase=index lines=" + ctx.lines.len() + " pairs=" + pairs.len()
          + " target=" + ctx.targetTownId;
      if (DECISION_LOG) OpexDecide("AIR_HUB_PAIR_PREFILTER", fields);
      else OpexC78Log("AIR_HUB_PAIR_PREFILTER", fields);
    }
  }
  return OpexAirHubTownPairKey(tileA, tileB) in ctx.airHubTownPairs;
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

/* Mesure legere, uniquement sous le gate existant catalog_cost_probe.
 * Identites transitoires a la VM : le lecteur ajoute source/compagnie/session.
 * Aucun etat metier, aucune persistance, aucun log dans les boucles de candidats.
 * Deux lignes par invocation active, sept agregats de phases disjointes au plus.
 * Le cout englobant inclut ENTER et l'agregation, mais pas l'emission EXIT. */
OPEX_AIR_LIGHT_SEQ <- 0;

function OpexAirLightLog(fields)
{
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
      + AIDate.GetDayOfMonth(date) + " AIR_LIGHT v=1 " + fields);
}

function OpexAirLightBegin(resumeState, target, band)
{
  /* Reconsommer un resultat termine n'est pas une nouvelle generation. */
  if (resumeState != null && ("done" in resumeState) && resumeState.done) return null;
  OPEX_AIR_LIGHT_SEQ++;
  local state = null;
  if (resumeState != null && ("airLight" in resumeState)) state = resumeState.airLight;
  if (state == null) {
    state = { gen = OPEX_AIR_LIGHT_SEQ, slice = 0,
        origin = (resumeState == null || !("startTick" in resumeState)) ? 1 : 0 };
    if (resumeState != null) resumeState.airLight <- state;
  }
  state.slice++;
  local mark = OpexOpsMeasureBegin();
  local light = { mark = mark, day = AIDate.GetCurrentDate(), phases = {},
      identity = "inv=" + OPEX_AIR_LIGHT_SEQ + " gen=" + state.gen
          + " slice=" + state.slice + " origin=" + state.origin
          + " sliced=" + (resumeState != null ? 1 : 0)
          + " target=" + target + " band=" + band };
  OpexAirLightLog(light.identity + " edge=enter day=" + light.day + " tick=" + mark.tick);
  return light;
}

function OpexAirLightPhaseBegin()
{
  local mark = OpexOpsMeasureBegin();
  mark.day <- AIDate.GetCurrentDate();
  return mark;
}

function OpexAirLightPhaseEnd(light, phase, mark)
{
  local ops = OpexOpsMeasureEnd(mark);
  local ticks = AIController.GetTick() - mark.tick;
  local days = AIDate.GetCurrentDate() - mark.day;
  if (!(phase in light.phases)) light.phases[phase] <- { ops = 0, ticks = 0, days = 0, calls = 0 };
  local part = light.phases[phase];
  part.ops += ops;
  part.ticks += ticks;
  part.days += days;
  part.calls++;
}

function OpexAirLightEnd(light, complete, reason)
{
  local ops = OpexOpsMeasureEnd(light.mark);
  local tick = AIController.GetTick();
  local day = AIDate.GetCurrentDate();
  local fields = light.identity + " edge=exit complete=" + (complete ? 1 : 0)
      + " reason=" + reason + " day=" + day + " tick=" + tick + " ops=" + ops;
  foreach (phase in ["prepare", "sites", "new_pairs", "hub_discover", "hub_site", "hub_hub", "finalize"]) {
    if (!(phase in light.phases)) continue;
    local part = light.phases[phase];
    fields += " " + phase + "_ops=" + part.ops + " " + phase + "_ticks=" + part.ticks
        + " " + phase + "_days=" + part.days + " " + phase + "_calls=" + part.calls;
  }
  OpexAirLightLog(fields);
}

/* 1. Preparation : combos, villes, OpexAirTownPoolLimit, indices et reprise. */
function OpexAirPlansPrepare(ctx)
{
  local catalog = ctx.catalog;
  local lines = ctx.lines;
  local targetTownId = ctx.targetTownId;
  if (V93_AIR_DEMAND_PRODUCTION) AIR_DEMAND_PAX_CARGO = catalog.paxCargo;
  local resumeState = ctx.resumeState;
  local t0_all = ctx.t0_all;
  local sliced = ctx.sliced;

  if (!sliced) {
    OpexAirResetStationCoverageTownCache();
  } else if (!("stationCoverageTownCacheInit" in resumeState)) {
    OpexAirResetStationCoverageTownCache();
    resumeState.stationCoverageTownCacheInit <- true;
  }

  if (C80_AIR_EVAL_FAST) {
    /* Les prix changent au debut de chaque mois (inflation) : une planification decoupee qui
     * enjambe un changement de mois repart avec des memos vides pour rester exacte. */
    local memoDate = AIDate.GetCurrentDate();
    local memoMonth = AIDate.GetYear(memoDate) * 12 + AIDate.GetMonth(memoDate);
    if (!sliced || !("airFastInit" in resumeState) || AIR_MEMO_MONTH != memoMonth) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
      if (sliced) resumeState.airFastInit <- true;
    }
    AIR_MEMO_MONTH = memoMonth;
  }
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
  if (C121_AIR_ECONOMICS) {
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
  } else {
    C121_AIR_PLAN_PERF = null;
    C121_AIR_ENDPOINT_CACHE = null;
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
    if (C80_AIR_EVAL_FAST) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
    }
    ctx.bestPlan = null;
    return false;
  }

  /* C80 tranche 5 bis : index exacts des lignes aeriennes, construits une fois par appel (les
   * lignes ne changent pas pendant la planification). Memes resolutions de gare que les boucles
   * qu'ils remplacent : nombre de routes par gare (decouverte des hubs) et paires deja reliees
   * (hub a hub), au lieu d'un parcours de toutes les lignes par hub et par paire de hubs. */
  local hubIndex = null;
  if (C80_AIR_HUB_INDEX && AIR_HUB && lines != null) {
    hubIndex = { routes = {}, pairs = {} };
    foreach (other in lines) {
      if (!("mode" in other) || other.mode != "air") continue;
      local oA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
          : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
      local oB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
          : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
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
      /* c83_fixes ne retouche pas cette liste : elle autorise le second slot
       * proactif d'une ville DEJA servie par Opex (C83.1 adopte). Le filtre
       * Ãƒâ€šÃ‚Â« ville encore disputable, Opex absent Ãƒâ€šÃ‚Â» ne concerne que le watcher. */
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
    } else if (C121_CATALOG_INCREMENTAL && sliced) {
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
  if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabBeginPass(sliced, resumeState, catalog, targetTownId);
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

  return true;
}

/* 2. Recherche des sites : sondage des villes candidates et revalidation avant classement. */
function OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo)
{
  if (ctx.sliced && ("c83Repair" in ctx.resumeState)) {
    local repaired = OpexC83RepairFindSites(ctx, comboIndex, combo, airport, plane);
    if (repaired.handled) return repaired.done;
  }
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
    if (C83_FIXES && targetTownId >= 0) {
      scanEnd = scanStart;
      for (local c83Scan = scanStart; c83Scan < limit; c83Scan++) {
        if (towns[c83Scan].id == targetTownId) {
          scanEnd = c83Scan + 1;
          break;
        }
      }
    }
    local testedBefore = probes.tested;
    local cheapBefore = ("cheapSkip" in probes) ? probes.cheapSkip : 0;
    local foundBefore = scanSites.len();
    local tSites0 = AIController.GetTick();
    local lSites0 = AIController.GetOpsTillSuspend();
    for (local i = scanStart; i < scanEnd; i++) {
      probes.townsLeft = limit - i;
      if (C83_FIXES && targetTownId >= 0) probes.townsLeft = scanEnd - i;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      if (towns[i].id in stationLimitedTowns) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_station_limit", 1);
        if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_station_limit");
      } else {
        /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
         * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
         * construction aerienne sur une carte partiellement couverte. */
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        local v126State = isServed ? OpexAirV126ServedTownState(towns[i], lines)
                                   : { eligible = false, stationId = -1, routes = 0, noise = -1 };
        local v126Reuse = isServed && v126State.eligible;
        local v134State = (V134_AIR_P2P_SATURATED_HUB && isServed)
            ? OpexAirV134SaturatedHubState(towns[i], lines, ctx.hubIndex)
            : { eligible = false, hubRoutes = 0 };
        local v134Eligible = v134State.eligible;
        if (DECISION_LOG && isServed && V126_AIR_SERVED_TOWN_REUSE) {
          OpexDecide("V126_AIR_TOWN", "town=" + towns[i].id
              + " eligible=" + (v126Reuse ? 1 : 0)
              + " station=" + v126State.stationId
              + " routes=" + v126State.routes + " noise=" + v126State.noise);
        }
        local skipServed = false;
        if (isServed && !c83OwnSecondSlot && !v126Reuse) skipServed = !v134Eligible;
        if (skipServed) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "origin_served", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=origin_served");
        } else if (!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600) {
          /* Grands aeroports : accessibles des 600 habitants. A 0, le booleen
           * est le seul test ajoute sur ce chemin. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_small", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_small");
        } else if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP) {
          /* V93 : plancher minimal, grand ou petit. A 0 ce test est faux. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_v93", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_v93");
        } else {
          local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
              ? targetTownId : -1;
          if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
            c83RequiredSlotTown = towns[i].id;
          }
          if (c83RequiredSlotTown < 0 && v134Eligible) {
            c83RequiredSlotTown = towns[i].id;
          }
          if (c78Gen && ("c78NoSite" in probes)) probes.c78NoSite = null;
          local site = OpexAirFindSite(towns[i], airport, probes, c83RequiredSlotTown);
          if (site != null) {
            if (c83OwnSecondSlot) site.c83OwnSecondSlot <- true;
            if (v126Reuse) {
              site.v126ServedTown <- true;
              site.v126StationId <- v126State.stationId;
              site.v126Routes <- v126State.routes;
            }
            if (v134Eligible) {
              site.v134SecondSlot <- true;
              site.v134HubRoutes <- v134State.hubRoutes;
            }
            if (C83_FIXES && c83RequiredSlotTown >= 0) site.c83SlotTown <- c83RequiredSlotTown;
            scanSites.append(site);
            if (c78Gen) {
              if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < 600) {
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
      if (OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
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
      if (C83_FIXES && OpexAirTownCentersLinked(sites[a].town.tile, sites[b].town.tile, lines)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "batch_plan_dead", 1);
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + linkedDist + " outcome=batch_plan_dead P=-1 C=-1");
        }
        continue;
      }
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
      if (C80_AIR_EVAL_FAST) {
        if (distance < minDist) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
          continue;
        }
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      sites[a].anchor, sites[b].anchor);
      local flightDistance = OpexFlightDistance(sites[a].anchor, sites[b].anchor);
      if (!C80_AIR_EVAL_FAST && distance < minDist) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
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
        if (OpexAirPairIsAbandoned(abandoned, sites[a], sites[b])
            || (OPEX_AIR_TOWN_PAD && ((OpexAirTownPaddingKey(sites[a]) in abandoned)
                || (OpexAirTownPaddingKey(sites[b]) in abandoned)))
            || (OPEX_AIR_SITE_PAD && ((OpexAirSitePaddingKey(sites[a], airport.type) in abandoned)
                || (OpexAirSitePaddingKey(sites[b], airport.type) in abandoned)))) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }

      local popA = sites[a].town.pop;
      local popB = sites[b].town.pop;
      local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthlyPax = OpexAirTownMonthlyPax(sites[a].town, sites[a].anchor, airport, ctx.lines)
            + OpexAirTownMonthlyPax(sites[b].town, sites[b].anchor, airport, ctx.lines);
      }
      if (a == 0 && b == 1) {
        OpexSign(AIMap.GetTileIndex(1, 5), "AX|PA=" + popA + "|PB=" + popB + "|MPX=" + monthlyPax);
      }

      local v134A = V134_AIR_P2P_SATURATED_HUB && ("v134SecondSlot" in sites[a]) && sites[a].v134SecondSlot;
      local v134B = V134_AIR_P2P_SATURATED_HUB && ("v134SecondSlot" in sites[b]) && sites[b].v134SecondSlot;
      local servedOtherA = (("c83OwnSecondSlot" in sites[a]) && sites[a].c83OwnSecondSlot)
          || (("v126ServedTown" in sites[a]) && sites[a].v126ServedTown);
      local servedOtherB = (("c83OwnSecondSlot" in sites[b]) && sites[b].c83OwnSecondSlot)
          || (("v126ServedTown" in sites[b]) && sites[b].v126ServedTown);
      if (v134A && (v134B || servedOtherB)) continue;
      if (v134B && (v134A || servedOtherA)) continue;

      local plan = {
        siteA = sites[a], siteB = sites[b], distance = flightDistance,
        orderDistance = orderDistance,
        airport = airport, plane = plane,
        monthlyPax = monthlyPax, planes = 1, capital = 0, economics = null,
        reuseA = false, reuseB = false, hubRoutes = 0, arm = "newpair",
        c83OwnSecondSlotA = ("c83OwnSecondSlot" in sites[a]) && sites[a].c83OwnSecondSlot,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in sites[b]) && sites[b].c83OwnSecondSlot,
        v134SecondSlotA = v134A,
        v134SecondSlotB = v134B,
      };
      if (DECISION_LOG && V126_AIR_SERVED_TOWN_REUSE) {
        local v126A = ("v126ServedTown" in sites[a]) && sites[a].v126ServedTown;
        local v126B = ("v126ServedTown" in sites[b]) && sites[b].v126ServedTown;
        if (v126A || v126B) {
          OpexDecide("V126_AIR_PAIR", "townA=" + sites[a].town.id + " townB=" + sites[b].town.id
              + " servedA=" + (v126A ? 1 : 0) + " servedB=" + (v126B ? 1 : 0)
              + " routesA=" + (v126A ? sites[a].v126Routes : -1)
              + " routesB=" + (v126B ? sites[b].v126Routes : -1));
        }
      }
      if (DECISION_LOG && V134_AIR_P2P_SATURATED_HUB) {
        if (v134A) {
          OpexDecide("V134_P2P", "town=" + sites[a].town.id + " hubRoutes=" + sites[a].v134HubRoutes);
        }
        if (v134B) {
          OpexDecide("V134_P2P", "town=" + sites[b].town.id + " hubRoutes=" + sites[b].v134HubRoutes);
        }
      }
      local routeChoice = C121_AIR_ECONOMICS
          ? (C121_CATALOG_INCREMENTAL
              ? OpexC121CatalogChoice(catalog, plan, ctx.lines)
              : OpexC121ChooseRoutePlane(catalog, plan, ctx.lines))
          : OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 2, opcodePadding,
              C80_AIR_CHOICE_MEMO ? ("n|" + sites[a].town.id + "|" + sites[b].town.id
                  + "|" + airport.type + "|" + plane.id) : null,
              C119_AIR_INCOME_MODEL
                  ? AIMap.DistanceManhattan(sites[a].anchor, sites[b].anchor) : 0);
      if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabAfterChoice(plan, routeChoice);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      local portfolioEconomics = (routeChoice != null && ("portfolioEconomics" in routeChoice) && routeChoice.portfolioEconomics != null)
          ? routeChoice.portfolioEconomics : null;
      local admissionEconomics = (C113_AIR_C100_FULL_DECISION_SHADOW && decisionEconomics != null)
          ? decisionEconomics : economics;
      if (EQUIPMENT_ROI_PROBE && routePlane != null && economics != null) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 2, opcodePadding, economics, "pre_admission_newpair");
      }
      if (economics == null) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "economics_unavailable", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
        continue;
      }

      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, sites[a].anchor, sites[b].anchor);
      }
      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (portfolioEconomics != null) plan.portfolioEconomics <- portfolioEconomics;
      if (C118_AIR_TERRITORIAL_EXPANSION && ("c118C68Plane" in routeChoice)
          && ("c118C68Economics" in routeChoice)) {
        plan.c118C68Plane <- routeChoice.c118C68Plane;
        plan.c118C68Economics <- routeChoice.c118C68Economics;
        if ("c118EngineChoices" in routeChoice) plan.c118EngineChoices <- routeChoice.c118EngineChoices;
      }
      if (C121_AIR_ECONOMICS) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      } else if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);

      if (a == 0 && b == 1) {
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
          if (V93_AIR_DEMAND_PRODUCTION) {
            local paxOld = ((sites[a].town.pop + sites[b].town.pop) * TOWN_CATCHMENT_SHARE_PCT) / 100;
            if (paxOld < 10) paxOld = 10;
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        if (C97_AIR_C69_ENGINE_PROBE) OpexC97ProbeAirEngine(catalog, plan);
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
    local otherA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
        : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
    local otherB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
        : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
    if (otherA == stationId || otherB == stationId) routeCount++;
  }
  return routeCount;
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

  if (AIR_HUB && lines != null) {
    if (!ctx.c83RepairCombo && sites.len() < AIR_HUB_NEW_SITE_POOL) {
      local hubProbes = {
        left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
        stationLimitedTowns = stationLimitedTowns
      };
      local tHubSites0 = AIController.GetTick();
      local lHubSites0 = AIController.GetOpsTillSuspend();
      local hubScanEnd = limit;
      if (C83_FIXES && targetTownId >= 0) {
        hubScanEnd = 0;
        for (local c83Scan = 0; c83Scan < limit; c83Scan++) {
          if (towns[c83Scan].id == targetTownId) {
            hubScanEnd = c83Scan + 1;
            break;
          }
        }
      }
      for (local i = 0; i < hubScanEnd && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
        hubProbes.townsLeft = limit - i;
        if (C83_FIXES && targetTownId >= 0) hubProbes.townsLeft = hubScanEnd - i;
        if (towns[i].id in stationLimitedTowns) {
          continue;
        }
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        if (isServed && !c83OwnSecondSlot) continue;
        /* Typage : grands aeroports des 600 hab. A 0, seul le booleen est ajoute. */
        if (!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600) continue;
        if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP) continue;
        if (combo.kind == "small" && towns[i].pop >= 2500) continue;
        local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
            ? targetTownId : -1;
        if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
          c83RequiredSlotTown = towns[i].id;
        }
        local extraSite = OpexAirFindSite(towns[i], airport, hubProbes, c83RequiredSlotTown);
        if (extraSite != null) {
          if (c83OwnSecondSlot) extraSite.c83OwnSecondSlot <- true;
          if (C83_FIXES && c83RequiredSlotTown >= 0) extraSite.c83SlotTown <- c83RequiredSlotTown;
          /* v93=1 seulement si le scan principal n'a pas deja retenu cette ville. */
          if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < 600 && ("c78Gen" in ctx) && ctx.c78Gen) {
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
      /* air_hub_fix : l'ancre d'un hub est la TUILE D'AEROPORT (line.stationA/B), pas le
       * centre-ville (line.originA/B). Sous 0, on rejoue litteralement le comportement casse. */
      local ends = null;
      if (AIR_HUB_FIX) {
        ends = [
          { anchor = line.stationA, origin = line.originA, stationId = line.stationA },
          { anchor = line.stationB, origin = line.originB, stationId = line.stationB },
        ];
      } else {
        ends = [
          { anchor = line.originA, origin = line.originA, stationId = line.stationA },
          { anchor = line.originB, origin = line.originB, stationId = line.stationB },
        ];
      }
      foreach (end in ends) {
        if (!AIMap.IsValidTile(end.anchor) || !AIAirport.IsAirportTile(end.anchor)) continue;
        local existingType = AIAirport.GetAirportType(end.anchor);
        if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
        /* Resolution non ambigue : `end.stationId` est une tuile, et `IsValidStation(tuile)`
         * peut etre vrai par pure collision d'indices. On resout toujours depuis l'ancre. */
        local station = AIR_HUB_FIX
            ? AIStation.GetStationID(end.anchor)
            : (AIStation.IsValidStation(end.stationId) ? end.stationId : AIStation.GetStationID(end.anchor));
        if (!AIStation.IsValidStation(station) || (station in seenStations)) continue;

        local routeCount = 0;
        if (hubIndex != null) {
          if (station in hubIndex.routes) routeCount = hubIndex.routes[station];
        } else {
          foreach (other in lines) {
            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
                : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
            local otherB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
                : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
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
        if (AIR0310_HUB_SNAPSHOT) OpexAir0310NoteHubOrigin(ctx, 0);
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
      if (AIR0310_HUB_SNAPSHOT) OpexAir0310NoteHubOrigin(ctx, 1);
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

  local incrementalSlice = ctx.sliced && C121_CATALOG_INCREMENTAL;
  local resumeHub = incrementalSlice && ("hubSiteI" in ctx.resumeState)
      ? ctx.resumeState.hubSiteI : 0;
  local resumeSite = incrementalSlice && ("hubSiteJ" in ctx.resumeState)
      ? ctx.resumeState.hubSiteJ : 0;
  local progressed = false;
  for (local hi = resumeHub; hi < hubs.len(); hi++) {
    local hub = hubs[hi];
    local hubMonthlyPre = C80_AIR_EVAL_FAST
        ? (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1))
        : 0;
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
      local hubSiteMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      local site = sites[sj];
      if (AIR0310_HUB_SNAPSHOT && (ctx.air0310HubRestored || ctx.air0310HubSkip != null)
          && OpexAir0310SkipRestoredPair(ctx, airport, "hubsite", hub, null, site, plane)) continue;
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airHubSitePairs++;
      if (targetTownId >= 0
          && hub.town.id != targetTownId && site.town.id != targetTownId) continue;
      if (EXP_AIR_HUB_PAIR_PREFILTER
          && OpexAirHubPairPrefilterLinked(ctx, hub.town.tile, site.town.tile)) {
        if (C69_BOTTLENECK_PROBE) {
          OpexC73RecordExamined("air", 1);
          OpexC73RecordRejection("air", "hubsite_pair_linked", 1);
        }
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + linkedDist + " outcome=hubsite_pair_linked P=-1 C=-1 src=" + hub.town.tile + " dst=" + site.town.tile + " cargo=" + catalog.paxCargo);
        }
        continue;
      }
      if (C83_FIXES && OpexAirTownCentersLinked(hub.town.tile, site.town.tile, lines)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "batch_plan_dead", 1);
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + linkedDist + " outcome=batch_plan_dead P=-1 C=-1");
        }
        continue;
      }
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
      if (distance < 20) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      hub.anchor, site.anchor);
      local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
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
        if (OpexAirPairIsAbandoned(abandoned, hub, site)
            || (OPEX_AIR_TOWN_PAD && (OpexAirTownPaddingKey(site) in abandoned))
            || (OPEX_AIR_SITE_PAD && (OpexAirSitePaddingKey(site, airport.type) in abandoned))) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }
      local hubMonthly = C80_AIR_EVAL_FAST
          ? hubMonthlyPre
          : (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1));
      local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local monthlyPax = hubMonthly + newMonthly;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthlyPax = OpexAirTownMonthlyPax(hub.town, hub.anchor, airport, ctx.lines)
            + OpexAirTownMonthlyPax(site.town, site.anchor, airport, ctx.lines);
      }
      local plan = {
        siteA = hub, siteB = site, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = plane, monthlyPax = monthlyPax, planes = 1,
        capital = 0, economics = null,
        reuseA = true, reuseB = false, hubRoutes = hub.routes, arm = "hubsite",
        c83OwnSecondSlotA = false,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in site) && site.c83OwnSecondSlot,
      };
      local routeChoice = C121_AIR_ECONOMICS
          ? (C121_CATALOG_INCREMENTAL
              ? OpexC121CatalogChoice(catalog, plan, ctx.lines)
              : OpexC121ChooseRoutePlane(catalog, plan, ctx.lines))
          : OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 1, opcodePadding,
              C80_AIR_CHOICE_MEMO ? ("h|" + hub.stationId + "|" + site.town.id
                  + "|" + airport.type + "|" + plane.id) : null,
              C119_AIR_INCOME_MODEL
                  ? AIMap.DistanceManhattan(hub.anchor, site.anchor) : 0);
      if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabAfterChoice(plan, routeChoice);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      local portfolioEconomics = (routeChoice != null && ("portfolioEconomics" in routeChoice) && routeChoice.portfolioEconomics != null)
          ? routeChoice.portfolioEconomics : null;
      local admissionEconomics = (C113_AIR_C100_FULL_DECISION_SHADOW && decisionEconomics != null)
          ? decisionEconomics : economics;
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
      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub.anchor, site.anchor);
      }
      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (portfolioEconomics != null) plan.portfolioEconomics <- portfolioEconomics;
      if (C118_AIR_TERRITORIAL_EXPANSION && ("c118C68Plane" in routeChoice)
          && ("c118C68Economics" in routeChoice)) {
        plan.c118C68Plane <- routeChoice.c118C68Plane;
        plan.c118C68Economics <- routeChoice.c118C68Economics;
        if ("c118EngineChoices" in routeChoice) plan.c118EngineChoices <- routeChoice.c118EngineChoices;
      }
      if (C121_AIR_ECONOMICS) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      } else if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);
      if (admissionEconomics.profitAnnual <= 0) {
        if (hubSiteMark != null) OpexSpanAgg("air.hub_site_pair", hubSiteMark);
        continue;
      }
      if (c78Gen) {
        if (V93_AIR_DEMAND_PRODUCTION) {
          local paxOld = (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1))
              + ((site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100);
          if (paxOld < 10) paxOld = 10;
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
        } else {
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
        }
      }
      if (C97_AIR_C69_ENGINE_PROBE) OpexC97ProbeAirEngine(catalog, plan);
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

  local hubAvgIncome = [];
  if (AIR_HUBHUB_MARGINAL) {
    for (local h = 0; h < hubs.len(); h++) hubAvgIncome.append(0.0);
    if (lines != null && hubs.len() > 0) {
      local hubIndexByStation = {};
      for (local h = 0; h < hubs.len(); h++) {
        hubIndexByStation.rawset(hubs[h].stationId, h);
      }
      local hubLinesCount = [];
      local hubLinesIncomeSum = [];
      for (local h = 0; h < hubs.len(); h++) {
        hubLinesCount.append(0);
        hubLinesIncomeSum.append(0.0);
      }
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        if (("deadStreak" in line) && line.deadStreak >= 2) continue;
        local stA = AIR_HUB_FIX ? OpexAirLineStationId(line, 0)
            : (AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA));
        local stB = AIR_HUB_FIX ? OpexAirLineStationId(line, 1)
            : (AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB));
        if (!AIStation.IsValidStation(stA) || !AIStation.IsValidStation(stB)) continue;

        local dist = ("distance" in line && line.distance > 0)
            ? line.distance
            : (AIMap.IsValidTile(line.stationA) && AIMap.IsValidTile(line.stationB)
                ? OpexFlightDistance(line.stationA, line.stationB) : 0);
        if (dist <= 0) continue;
        local days = ("predOneWayDays" in line && line.predOneWayDays > 0) ? line.predOneWayDays : 0;
        local incomeDays = OpexCeilDiv(days, 1);
        if (incomeDays < 1) incomeDays = 1;
        local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, dist, incomeDays);
        local totalIncomePerUnit = paxIncome;
        if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
          local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, dist, incomeDays);
          totalIncomePerUnit = paxIncome + (mailIncome * 15) / 100;
        }
        local incomePerUnit = (totalIncomePerUnit * AIR_PAX_REVENUE_CALIBRATION_PCT) / 100.0;

        if (stA in hubIndexByStation) {
          local h = hubIndexByStation[stA];
          hubLinesCount[h]++;
          hubLinesIncomeSum[h] += incomePerUnit;
        }
        if (stB in hubIndexByStation && stB != stA) {
          local h = hubIndexByStation[stB];
          hubLinesCount[h]++;
          hubLinesIncomeSum[h] += incomePerUnit;
        }
      }
      for (local h = 0; h < hubs.len(); h++) {
        if (hubLinesCount[h] > 0) {
          hubAvgIncome[h] = hubLinesIncomeSum[h] / hubLinesCount[h];
        }
      }
    }
  }

  local incrementalSlice = ctx.sliced && C121_CATALOG_INCREMENTAL;
  local resumeI = incrementalSlice && ("hubHubI" in ctx.resumeState)
      ? ctx.resumeState.hubHubI : 0;
  local resumeJ = incrementalSlice && ("hubHubJ" in ctx.resumeState)
      ? ctx.resumeState.hubHubJ : 1;
  local progressed = false;
  for (local i = resumeI; i < hubs.len(); i++) {
    local hub1MonthlyPre = C80_AIR_EVAL_FAST
        ? (((hubs[i].town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hubs[i].routes + 1))
        : 0;
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
      local hubHubMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      local hub1 = hubs[i];
      local hub2 = hubs[j];
      if (AIR0310_HUB_SNAPSHOT && (ctx.air0310HubRestored || ctx.air0310HubSkip != null)
          && OpexAir0310SkipRestoredPair(ctx, airport, "hubhub", hub1, hub2, null, plane)) continue;
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airHubHubPairs++;
      if (targetTownId >= 0
          && hub1.town.id != targetTownId && hub2.town.id != targetTownId) continue;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      if (EXP_AIR_HUB_PAIR_PREFILTER
          && OpexAirHubPairPrefilterLinked(ctx, hub1.town.tile, hub2.town.tile)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "hubhub_pair_linked", 1);
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + linkedDist + " outcome=hubhub_pair_linked P=-1 C=-1 src=" + hub1.town.tile + " dst=" + hub2.town.tile + " cargo=" + catalog.paxCargo);
        }
        continue;
      }
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
        local oA = AIR_HUB_FIX ? OpexAirLineStationId(line, 0)
            : (AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA));
        local oB = AIR_HUB_FIX ? OpexAirLineStationId(line, 1)
            : (AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB));
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
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
      local flightDistance = OpexFlightDistance(hub1.anchor, hub2.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
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
      local monthly1 = C80_AIR_EVAL_FAST
          ? hub1MonthlyPre
          : (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1));
      local monthly2 = ((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1);
      local monthlyPax = monthly1 + monthly2;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthly1 = OpexAirTownMonthlyPax(hub1.town, hub1.anchor, airport, lines);
        monthly2 = OpexAirTownMonthlyPax(hub2.town, hub2.anchor, airport, lines);
        monthlyPax = monthly1 + monthly2;
      }
      local plan = {
        siteA = hub1, siteB = hub2, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = plane, monthlyPax = monthlyPax, planes = 1,
        capital = 0, economics = null,
        reuseA = true, reuseB = true, hubRoutes = hub1.routes + hub2.routes,
        arm = "hubhub",
      };
      local routeChoice = C121_AIR_ECONOMICS
          ? (C121_CATALOG_INCREMENTAL
              ? OpexC121CatalogChoice(catalog, plan, lines)
              : OpexC121ChooseRoutePlane(catalog, plan, lines))
          : OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 0, opcodePadding,
              C80_AIR_CHOICE_MEMO ? ("hh|" + hub1.stationId + "|" + hub2.stationId
                  + "|" + airport.type + "|" + plane.id) : null,
              C119_AIR_INCOME_MODEL
                  ? AIMap.DistanceManhattan(hub1.anchor, hub2.anchor) : 0);
      if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabAfterChoice(plan, routeChoice);
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
      if (AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS
          && economics != null && economics.profitAnnual > 0) {
        /* V86 Variante A : retrancher la perte de revenu annuel des lignes aeriennes existantes.
         * Hypothese : CargoDist etant desactive (DT_MANUAL), les passagers montent dans le premier avion
         * quelle que soit sa destination. La nouvelle ligne hub->hub cannibalise les passagers des lignes
         * existantes des deux hubs. Aucun gain de note de gare (station rating) n'est modelise. */
        local pax1 = (monthlyPax > 0) ? (economics.carried.tofloat() * monthly1) / monthlyPax : 0.0;
        if (pax1 > monthly1) pax1 = monthly1.tofloat();
        local pax2 = (monthlyPax > 0) ? (economics.carried.tofloat() * monthly2) / monthlyPax : 0.0;
        if (pax2 > monthly2) pax2 = monthly2.tofloat();
        local lossAnnual = (12.0 * (pax1 * hubAvgIncome[i] + pax2 * hubAvgIncome[j])).tointeger();
        if (lossAnnual > 0) {
          economics = clone economics;
          economics.profitAnnual -= lossAnnual;
          local totalCapital = economics.capital + economics.immobilise;
          economics.roi = totalCapital > 0 ? (economics.profitAnnual * 1000) / totalCapital : 0;
        }
      }
      if (AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS
          && decisionEconomics != null && decisionEconomics.profitAnnual > 0) {
        local decisionPax1 = (monthlyPax > 0) ? (decisionEconomics.carried.tofloat() * monthly1) / monthlyPax : 0.0;
        if (decisionPax1 > monthly1) decisionPax1 = monthly1.tofloat();
        local decisionPax2 = (monthlyPax > 0) ? (decisionEconomics.carried.tofloat() * monthly2) / monthlyPax : 0.0;
        if (decisionPax2 > monthly2) decisionPax2 = monthly2.tofloat();
        local decisionLossAnnual = (12.0 * (decisionPax1 * hubAvgIncome[i] + decisionPax2 * hubAvgIncome[j])).tointeger();
        if (decisionLossAnnual > 0) {
          decisionEconomics = clone decisionEconomics;
          decisionEconomics.profitAnnual -= decisionLossAnnual;
          local decisionTotalCapital = decisionEconomics.capital + decisionEconomics.immobilise;
          decisionEconomics.roi = decisionTotalCapital > 0
              ? (decisionEconomics.profitAnnual * 1000) / decisionTotalCapital : 0;
        }
      }
      local admissionEconomics = (C113_AIR_C100_FULL_DECISION_SHADOW && decisionEconomics != null)
          ? decisionEconomics : economics;
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
      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
      }
      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (portfolioEconomics != null) plan.portfolioEconomics <- portfolioEconomics;
      if (C118_AIR_TERRITORIAL_EXPANSION && ("c118C68Plane" in routeChoice)
          && ("c118C68Economics" in routeChoice)) {
        plan.c118C68Plane <- routeChoice.c118C68Plane;
        plan.c118C68Economics <- routeChoice.c118C68Economics;
        if ("c118EngineChoices" in routeChoice) plan.c118EngineChoices <- routeChoice.c118EngineChoices;
      }
      if (C121_AIR_ECONOMICS) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      } else if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);
      /* C113 : l'admission a deja ete arbitree sur le shadow C68. Le profit
       * legacy du moteur replay peut etre negatif sans invalider le marche de
       * decision ; hors C113, admissionEconomics == economics et le contrat
       * historique reste strictement identique. */
      if (hubHubMark != null && admissionEconomics.profitAnnual <= 0) OpexSpanAgg("air.hub_hub_pair", hubHubMark);
      if (admissionEconomics.profitAnnual <= 0) continue;
      if (c78Gen) {
        if (V93_AIR_DEMAND_PRODUCTION) {
          local paxOld = (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1))
              + (((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1));
          if (paxOld < 10) paxOld = 10;
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
        } else {
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
        }
      }
      if (C97_AIR_C69_ENGINE_PROBE) OpexC97ProbeAirEngine(catalog, plan);
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

/* V95 : diagnostic annuel, strictement passif, des occasions que le scan courant
 * n'atteint pas parce que la ville est deja servie ou sous le plancher de 600.
 * La sonde ne remplit ni AIR_SITE_CACHE, ni ctx.sites, ni le portefeuille. */
function OpexAirV95Log(fields)
{
  if (!V95_AIR_POST73_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("V95_AIR_POST73 year=" + AIDate.GetYear(date)
      + " month=" + AIDate.GetMonth(date) + " " + fields);
}

/* Cout de terrassement estime seul. AITestMode ne modifie pas le terrain, donc
 * on ne peut pas enchainer dessus un BuildAirport fiable ; le cout de site publie
 * separement airport.price + ce terrassement, sans pretendre inclure les arbres. */
function OpexAirV95LevelCost(site, airport)
{
  if (site == null || airport == null) return -1;
  if (OpexAirFootprintIsFlat(site.anchor, airport)) return 0;
  local accounting = AIAccounting();
  local ok = false;
  {
    local test = AITestMode();
    ok = AITile.LevelTiles(site.anchor, OpexAirFootprintEnd(site.anchor, airport));
  }
  if (!ok) return -1;
  local cost = accounting.GetCosts();
  if (cost < 0) cost = -cost;
  return cost;
}

/* Meilleur raccordement du site ignore vers un hub Opex existant, avec les memes
 * filtres et le meme proxy de demande que le bras hub->site courant. On ne memoise
 * pas le choix d'avion : c'est une lecture ponctuelle du C68 courant. */
function OpexAirV95BestHubRoute(ctx, site, airport, plane)
{
  local result = { best = null, reject = "no_hub" };
  if (ctx.hubs == null || ctx.hubs.len() == 0) return result;
  result.reject = "distance_or_band";
  foreach (hub in ctx.hubs) {
    /* La revalidation de chantier refuse toujours une paire de centres deja
     * reliee, meme quand c83_fixes=0. Le shadow doit appliquer le meme contrat,
     * sinon il surestime les extensions V95 qui mourraient avant tentative. */
    if (OpexAirTownCentersLinked(hub.town.tile, site.town.tile, ctx.lines)) {
      result.reject = "already_linked";
      continue;
    }
    local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
    if (distance < 20) continue;
    local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
    if (!OpexAirPairInBand(ctx.catalog, distance, flightDistance, ctx.paxBand)) continue;
    if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
    if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) continue;
    if (ctx.abandoned != null
        && (OpexAirPairIsAbandoned(ctx.abandoned, hub, site)
            || (OPEX_AIR_TOWN_PAD && (OpexAirTownPaddingKey(site) in ctx.abandoned))
            || (OPEX_AIR_SITE_PAD && (OpexAirSitePaddingKey(site, airport.type) in ctx.abandoned)))) {
      result.reject = "abandoned";
      continue;
    }

    local hubMonthly = ((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1);
    local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
    local monthlyPax = hubMonthly + newMonthly;
    if (monthlyPax < 10) monthlyPax = 10;
    local choice = OpexAirChooseRoutePlane(ctx.catalog, airport, plane, flightDistance, monthlyPax,
        ctx.infrastructureMaintenance, 0, 1, 0, null,
        C119_AIR_INCOME_MODEL ? AIMap.DistanceManhattan(hub.anchor, site.anchor) : 0);
    local econ = choice != null ? choice.economics : null;
    if (econ == null) {
      result.reject = "economics_unavailable";
      continue;
    }
    if (econ.profitAnnual <= 0) {
      result.reject = "profit_nonpositive";
      continue;
    }
    if (result.best == null || econ.profitAnnual > result.best.economics.profitAnnual
        || (econ.profitAnnual == result.best.economics.profitAnnual
            && econ.roi > result.best.economics.roi)) {
      result.best = {
        hub = hub, choice = choice, economics = econ,
        distance = flightDistance, monthlyPax = monthlyPax
      };
      result.reject = "candidate";
    }
  }
  return result;
}

function OpexAirV95Post73Probe(ctx, combo, airport, plane)
{
  if (!V95_AIR_POST73_PROBE || ctx.targetTownId >= 0) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (year < 1973 || V95_AIR_POST73_YEAR == year) return;
  if (!(("kind" in combo) && combo.kind == "large")) return;
  V95_AIR_POST73_YEAR = year;

  local ownCounts = OpexAirOwnSlotTownCounts();
  local available = OpexAvailableCapital();
  local smallCount = 0;
  local secondCount = 0;
  local siteCount = 0;
  local profitableCount = 0;
  local affordableCount = 0;
  local scanLimit = ctx.limit < ctx.towns.len() ? ctx.limit : ctx.towns.len();

  for (local i = 0; i < scanLimit; i++) {
    local town = ctx.towns[i];
    local served = OpexAirTownServed(town, ctx.lines);
    local c83OwnSecond = served && (town.id in ctx.c83TopTownIds)
        && OpexAirC83SecondSlotOpen(town);
    local isSmall = town.pop < OpexAirLargeAirportMinPop();
    local isSecond = served && !c83OwnSecond;
    if (!isSmall && !isSecond) continue;

    local currentReject = "";
    if (town.id in ctx.stationLimitedTowns) {
      currentReject = "station_limit";
    } else if (isSecond) {
      currentReject = "origin_served";
    } else if (!V93_AIRPORT_NO_POP_FLOOR && isSmall) {
      currentReject = "pop_floor";
    } else {
      continue;
    }

    if (isSmall) smallCount++;
    if (isSecond) secondCount++;
    local family = isSmall ? (isSecond ? "small_second" : "small") : "second";

    local requiredSlotTown = isSecond ? town.id : -1;
    local preSlots = OpexAirC83SlotSignalEnabled() ? AITown.GetAllowedNoise(town.id) : -1;
    local preOwn = (town.id in ownCounts) ? ownCounts[town.id] : 0;
    if (requiredSlotTown >= 0 && preSlots == 0) {
      OpexAirV95Log("phase=town family=" + family + " town=" + town.id + " pop=" + town.pop
          + " current_reject=" + currentReject
          + " shadow_reject=slot_closed served=" + (served ? 1 : 0)
          + " slot_town=" + town.id + " slots_remaining=0 own_airports=" + preOwn
          + " competitor_airports=" + (2 - preOwn));
      continue;
    }

    local probes = {
      left = AIR_MAX_SITE_PROBES, townsLeft = 1, tested = 0, cheapSkip = 0,
      stationLimitedTowns = {}
    };
    local key = "v95|" + year + "|" + town.id + "|" + airport.type;
    local found = OpexAirFindSiteListed(town, airport, probes, requiredSlotTown, key, false);
    local site = found.site;
    if (site == null) {
      local reason = probes.left <= 0 ? "site_budget" : "site_terrain";
      if (town.id in probes.stationLimitedTowns) reason = "site_slot";
      OpexAirV95Log("phase=town family=" + family + " town=" + town.id + " pop=" + town.pop
          + " current_reject=" + currentReject + " shadow_reject=" + reason
          + " served=" + (served ? 1 : 0) + " slots_remaining=" + preSlots
          + " own_airports=" + preOwn + " probes=" + found.used);
      continue;
    }
    siteCount++;

    local slotTown = OpexAirSlotTownId(site.anchor);
    local slotsRemaining = (slotTown >= 0 && OpexAirC83SlotSignalEnabled())
        ? AITown.GetAllowedNoise(slotTown) : -1;
    local ownAirports = (slotTown in ownCounts) ? ownCounts[slotTown] : 0;
    local occupied = slotsRemaining >= 0 ? 2 - slotsRemaining : -1;
    local competitors = occupied >= 0 ? occupied - ownAirports : -1;
    if (competitors < 0 && occupied >= 0) competitors = 0;

    local paxProd = AITown.GetLastMonthProduction(town.id, ctx.catalog.paxCargo);
    if (paxProd < 0) paxProd = 0;
    local mailProd = -1;
    if (("mailCargo" in ctx.catalog) && ctx.catalog.mailCargo >= 0) {
      mailProd = AITown.GetLastMonthProduction(town.id, ctx.catalog.mailCargo);
      if (mailProd < 0) mailProd = 0;
    }
    local paxTiles = OpexAirAirportCatchmentProduction(site.anchor, airport.type, ctx.catalog.paxCargo);
    local mailTiles = -1;
    if (("mailCargo" in ctx.catalog) && ctx.catalog.mailCargo >= 0) {
      mailTiles = OpexAirAirportCatchmentProduction(site.anchor, airport.type, ctx.catalog.mailCargo);
    }
    local houses = AITown.GetHouseCount(town.id);
    if (houses < 1) houses = 1;
    local paxSiteEst = (paxTiles * paxProd) / houses;
    local mailSiteEst = mailProd >= 0 && mailTiles >= 0 ? (mailTiles * mailProd) / houses : -1;
    local levelCost = OpexAirV95LevelCost(site, airport);
    local siteCost = airport.price + (levelCost > 0 ? levelCost : 0);

    local route = OpexAirV95BestHubRoute(ctx, site, airport, plane);
    local shadowReject = route.reject;
    local planeId = -1;
    local profit = -1;
    local capital = -1;
    local roi = -1;
    local hubTown = -1;
    local monthlyProxy = -1;
    local measuredMonthly = -1;
    local measuredPlaneId = -1;
    local measuredProfit = -1;
    local measuredCapital = -1;
    local measuredRoi = -1;
    local hubOnlyMonthly = -1;
    local hubOnlyPlaneId = -1;
    local hubOnlyProfit = -1;
    if (route.best != null) {
      profitableCount++;
      planeId = route.best.choice.plane != null ? route.best.choice.plane.id : -1;
      profit = route.best.economics.profitAnnual;
      capital = route.best.economics.capital;
      roi = route.best.economics.roi;
      hubTown = route.best.hub.town.id;
      monthlyProxy = route.best.monthlyPax;
      if (capital > available) {
        shadowReject = "cash";
      } else {
        shadowReject = "candidate";
        affordableCount++;
      }

      /* Contre-factuel diagnostic minimal : meme site, meme hub et meme C68,
       * mais la demande du nouveau site est remplacee par la production de
       * bassin estimee ci-dessus. Le hub existant garde son proxy courant. */
      local hubMonthlyMeasured = ((route.best.hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100)
          / (route.best.hub.routes + 1);
      measuredMonthly = hubMonthlyMeasured + paxSiteEst;
      if (measuredMonthly < 10) measuredMonthly = 10;
      local measuredChoice = OpexAirChooseRoutePlane(ctx.catalog, airport, plane,
          route.best.distance, measuredMonthly, ctx.infrastructureMaintenance, 0, 1, 0, null);
      if (measuredChoice != null && measuredChoice.economics != null) {
        measuredPlaneId = measuredChoice.plane != null ? measuredChoice.plane.id : -1;
        measuredProfit = measuredChoice.economics.profitAnnual;
        measuredCapital = measuredChoice.economics.capital;
        measuredRoi = measuredChoice.economics.roi;
      }
      hubOnlyMonthly = hubMonthlyMeasured;
      if (hubOnlyMonthly < 10) hubOnlyMonthly = 10;
      local hubOnlyChoice = OpexAirChooseRoutePlane(ctx.catalog, airport, plane,
          route.best.distance, hubOnlyMonthly, ctx.infrastructureMaintenance, 0, 1, 0, null);
      if (hubOnlyChoice != null && hubOnlyChoice.economics != null) {
        hubOnlyPlaneId = hubOnlyChoice.plane != null ? hubOnlyChoice.plane.id : -1;
        hubOnlyProfit = hubOnlyChoice.economics.profitAnnual;
      }
    }

    OpexAirV95Log("phase=town family=" + family + " town=" + town.id + " pop=" + town.pop
        + " current_reject=" + currentReject + " shadow_reject=" + shadowReject
        + " served=" + (served ? 1 : 0)
        + " anchor=" + site.anchor + " slot_town=" + slotTown
        + " slots_remaining=" + slotsRemaining + " own_airports=" + ownAirports
        + " competitor_airports=" + competitors
        + " pax_prod=" + paxProd + " mail_prod=" + mailProd
        + " pax_tiles=" + paxTiles + " mail_tiles=" + mailTiles
        + " pax_site_est=" + paxSiteEst + " mail_site_est=" + mailSiteEst
        + " airport_price=" + airport.price + " level_cost=" + levelCost
        + " site_cost_est=" + siteCost
        + " hub_town=" + hubTown + " plane=" + planeId
        + " monthly_proxy=" + monthlyProxy + " profit=" + profit
        + " capital=" + capital + " roi=" + roi + " available=" + available
        + " measured_monthly=" + measuredMonthly + " measured_plane=" + measuredPlaneId
        + " measured_profit=" + measuredProfit + " measured_capital=" + measuredCapital
        + " measured_roi=" + measuredRoi
        + " hub_only_monthly=" + hubOnlyMonthly + " hub_only_plane=" + hubOnlyPlaneId
        + " hub_only_profit=" + hubOnlyProfit
        + " probes=" + found.used);
  }
  OpexAirV95Log("phase=summary towns=" + scanLimit + " small=" + smallCount
      + " second=" + secondCount + " sites=" + siteCount
      + " profitable=" + profitableCount + " affordable=" + affordableCount
      + " hubs=" + ctx.hubs.len() + " available=" + available);
}

/* 7. Finalisation : enregistrement des perf, sondes et nettoyage de la reprise. */
function OpexAirPlansFinalize(ctx)
{
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
    if (C80_AIR_EVAL_FAST) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
    }
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
  if (C80_AIR_EVAL_FAST && !sliced) {
    AIR_ECONOMICS_MEMO = {};
    AIR_TRIP_MEMO = {};
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
  local light = CATALOG_COST_PROBE ? OpexAirLightBegin(resumeState, targetTownId, paxBand) : null;
  local lightMark = null;
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
    c83RepairCombo = false,
    air0310HubRestored = false,
    air0310HubSkip = null,
  };

  local spPlans = PROBE_SPAN_TRACE ? OpexSpanBegin("air.plans") : null;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_prepare", "-");
  if (light != null) lightMark = OpexAirLightPhaseBegin();
  local spPrepare = PROBE_SPAN_TRACE ? OpexSpanBegin("air.prepare") : null;
  local prepared = OpexAirPlansPrepare(ctx);
  if (spPrepare != null) OpexSpanEnd(spPrepare);
  if (light != null) OpexAirLightPhaseEnd(light, "prepare", lightMark);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_prepare", "-",
      "combos=" + (ctx.combos != null ? ctx.combos.len() : 0) + " towns=" + (ctx.towns != null ? ctx.towns.len() : 0)
      + " target=" + targetTownId);
  if (!prepared) {
    if (light != null) OpexAirLightEnd(light, !ctx.sliced || ctx.resumeState.done, "prepare_return");
    if (spPlans != null) OpexSpanEnd(spPlans);
    return ctx.bestPlan;
  }

  for (local comboIndex = ctx.comboStart; comboIndex < ctx.combos.len(); comboIndex++) {
    local combo = ctx.combos[comboIndex];
    local airport = combo.airport;
    local plane = combo.plane;
    local minDist = (plane.speed >= 400) ? 32 : 30;
    local resumingCombo = ctx.sliced && ctx.resumeState.combo == comboIndex && ctx.resumeState.sites != null;

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_find_sites", "-");
    if (light != null) lightMark = OpexAirLightPhaseBegin();
    local spSites = PROBE_SPAN_TRACE ? OpexSpanBegin("air.sites") : null;
    local sitesOk = OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo);
    if (spSites != null) OpexSpanEnd(spSites);
    if (light != null) OpexAirLightPhaseEnd(light, "sites", lightMark);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_find_sites", "-",
        "combo=" + comboIndex + " sites=" + ctx.sites.len() + " probes=" + ctx.perfProbesCount);
    if (!sitesOk) {
      if (light != null) OpexAirLightEnd(light, false, "sites_yield");
      if (spPlans != null) OpexSpanEnd(spPlans);
      return ctx.bestPlan;
    }

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_new_pairs", "-");
    if (light != null) lightMark = OpexAirLightPhaseBegin();
    local spPairs = PROBE_SPAN_TRACE ? OpexSpanBegin("air.new_pairs") : null;
    local pairsOk = OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo);
    if (spPairs != null) OpexSpanEnd(spPairs);
    if (light != null) OpexAirLightPhaseEnd(light, "new_pairs", lightMark);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_new_pairs", "-",
        "combo=" + comboIndex + " plans=" + (ctx.projects != null ? ctx.projects.len() : -1));
    if (!pairsOk) {
      if (light != null) OpexAirLightEnd(light, false, "pairs_yield");
      if (spPlans != null) OpexSpanEnd(spPlans);
      return ctx.bestPlan;
    }

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hubs", "-");
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_discover", "-");
    local reuseHubs = false;
    if (AIR0310_HUB_SNAPSHOT && ctx.sliced) {
      local hubSnapAction = OpexAir0310HubSnapshotPrepare(ctx, comboIndex, airport, plane);
      OpexAir0310HubSnapshotCount(ctx, hubSnapAction);
      reuseHubs = hubSnapAction == "reuse";
    }
    if (!reuseHubs) {
      if (AIR0310_HUB_SNAPSHOT) ctx.air0310HubOrphan <- [];
      if (light != null) lightMark = OpexAirLightPhaseBegin();
      local spDisc = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_discover") : null;
      OpexAirPlansDiscoverHubs(ctx, combo, airport, plane);
      if (spDisc != null) OpexSpanEnd(spDisc);
      if (light != null) OpexAirLightPhaseEnd(light, "hub_discover", lightMark);
      if (AIR0310_HUB_SNAPSHOT && ctx.sliced) OpexAir0310HubSnapshotStore(ctx, comboIndex);
    }
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_discover", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len());
    OpexAirV95Post73Probe(ctx, combo, airport, plane);

    local c56PlansBefore = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_site", "-");
    local tHubEval0 = AIController.GetTick();
    local lHubEval0 = AIController.GetOpsTillSuspend();
    if (light != null) lightMark = OpexAirLightPhaseBegin();
    local spHubSite = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_site") : null;
    if (!ctx.sliced || !C121_CATALOG_INCREMENTAL
        || !("hubPhase" in ctx.resumeState) || ctx.resumeState.hubPhase < 1) {
      if (!OpexAirPlansHubToSite(ctx, combo, airport, plane)) {
        if (light != null) {
          OpexAirLightPhaseEnd(light, "hub_site", lightMark);
          OpexAirLightEnd(light, false, "hub_site_yield");
        }
        if (spHubSite != null) OpexSpanEnd(spHubSite);
        if (spPlans != null) OpexSpanEnd(spPlans);
        return ctx.bestPlan;
      }
      if (ctx.sliced && C121_CATALOG_INCREMENTAL) ctx.resumeState.hubPhase <- 1;
    }
    if (spHubSite != null) OpexSpanEnd(spHubSite);
    if (light != null) OpexAirLightPhaseEnd(light, "hub_site", lightMark);
    local c56PlansMid = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_site", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len() + " admitted=" + (c56PlansMid - c56PlansBefore));
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_hub", "-");
    if (light != null) lightMark = OpexAirLightPhaseBegin();
    local spHubHub = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_hub") : null;
    local hubsOk = OpexAirPlansHubToHub(ctx, combo, airport, plane);
    if (spHubHub != null) OpexSpanEnd(spHubHub);
    if (light != null) OpexAirLightPhaseEnd(light, "hub_hub", lightMark);
    if (!hubsOk) {
      if (light != null) OpexAirLightEnd(light, false, "hub_hub_yield");
      if (spPlans != null) OpexSpanEnd(spPlans);
      return ctx.bestPlan;
    }
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_hub", "-",
        "hubs=" + ctx.hubs.len() + " admitted=" + (((ctx.projects != null) ? ctx.projects.len() : 0) - c56PlansMid));
    ctx.perfOpsEval += _calcDeltaOps(tHubEval0, lHubEval0);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hubs", "-", "hubs=" + ctx.hubs.len());

    if (AIR_HUB && ctx.hubs.len() > 0) {
      OpexSign(AIMap.GetTileIndex(1, 6), "AU|" + ctx.hubs.len() + "|"
               + (ctx.bestPlan != null && ctx.bestPlan.reuseA ? 1 : 0));
    }
    OpexSign(AIMap.GetTileIndex(1, 4), "AE|S=" + ctx.sites.len() + "|B=" + (ctx.bestPlan != null ? ctx.bestPlan.economics.profitAnnual : "NO"));
    if (ctx.sliced) {
      ctx.resumeState.combo = comboIndex + 1;
      ctx.resumeState.a = 0;
      ctx.resumeState.b = 1;
      ctx.resumeState.sites = null;
      ctx.resumeState.scanIndex = 0;
      ctx.resumeState.scanSites = [];
      ctx.resumeState.scanProbes = null;
      ctx.resumeState.rankIndex = 0;
      ctx.resumeState.rankSites = [];
      if (C121_CATALOG_INCREMENTAL) {
        ctx.resumeState.hubPhase <- 0;
        ctx.resumeState.hubSiteI <- 0;
        ctx.resumeState.hubSiteJ <- 0;
        ctx.resumeState.hubHubI <- 0;
        ctx.resumeState.hubHubJ <- 1;
      }
      if (AIR0310_HUB_SNAPSHOT) {
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
      if (!V93_AIRPORT_NO_POP_FLOOR) break;
      if (!(("kind" in combo) && combo.kind == "small")) {
        local nextSmall = OpexAirV93NextSmallCombo(ctx.combos, comboIndex);
        if (nextSmall < 0) break;
        if (ctx.sliced) ctx.resumeState.combo = nextSmall;
        comboIndex = nextSmall - 1;
      }
    }
  }

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_finalize", "-");
  if (light != null) lightMark = OpexAirLightPhaseBegin();
  local spFinal = PROBE_SPAN_TRACE ? OpexSpanBegin("air.finalize") : null;
  local finalPlan = OpexAirPlansFinalize(ctx);
  if (spFinal != null) OpexSpanEnd(spFinal);
  if (light != null) OpexAirLightPhaseEnd(light, "finalize", lightMark);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_finalize", "-");
  if (light != null) OpexAirLightEnd(light, true, "done");
  if (spPlans != null) OpexSpanEnd(spPlans);
  return finalPlan;
}

/* Sonde passive probe_c121_engine_table. Chaque emetteur retourne avant tout
 * travail quand le reglage est a 0. Aucun appel economique : on journalise
 * des valeurs deja calculees. Une reprise de tranche relit c121EngTabPass
 * dans resumeState et n'ouvre pas une nouvelle passe.
 * PLAN porte ge=0 scan normal, 1 raccourci avion-de-la-partie (aucune ligne
 * ENG : seul E est retenu, sans decisionOnly), 2 controle, 3 repli, et
 * ge_est=moteur etabli ou -1. Absents : 0 / -1. */
function OpexC121EngTabPad2(n)
{
  if (n < 10) return "0" + n;
  return "" + n;
}

function OpexC121EngTabDate()
{
  local date = AIDate.GetCurrentDate();
  return AIDate.GetYear(date) + "-"
      + OpexC121EngTabPad2(AIDate.GetMonth(date)) + "-"
      + OpexC121EngTabPad2(AIDate.GetDayOfMonth(date));
}

function OpexC121EngTabKey(plan)
{
  local townA = -1;
  local townB = -1;
  if (plan != null && ("siteA" in plan) && plan.siteA != null
      && ("town" in plan.siteA) && plan.siteA.town != null) townA = plan.siteA.town.id;
  if (plan != null && ("siteB" in plan) && plan.siteB != null
      && ("town" in plan.siteB) && plan.siteB.town != null) townB = plan.siteB.town.id;
  local ap = -1;
  if (plan != null && ("airport" in plan) && plan.airport != null
      && ("type" in plan.airport)) ap = plan.airport.type;
  local arm = (plan != null && ("arm" in plan) && plan.arm != null) ? plan.arm : "na";
  return townA + "-" + townB + "-" + ap + "-" + arm;
}

function OpexC121EngTabEngineSignature(catalog)
{
  if (!PROBE_C121_ENGINE_TABLE) return "none";
  if (catalog == null || !("airPlaneChoicesByAirport" in catalog)
      || catalog.airPlaneChoicesByAirport == null) return "none";
  local types = [];
  local byType = {};
  foreach (airportType, choices in catalog.airPlaneChoicesByAirport) {
    local ids = [];
    if (choices != null) {
      foreach (plane in choices) {
        if (plane == null || !("id" in plane)) continue;
        if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
        ids.append(plane.id);
      }
    }
    ids.sort();
    local idText = "";
    foreach (engineId in ids) {
      if (idText != "") idText += ",";
      idText += engineId;
    }
    types.append(airportType);
    byType.rawset(airportType, idText);
  }
  if (types.len() == 0) return "none";
  types.sort();
  local text = "";
  foreach (sortedType in types) {
    if (text != "") text += ";";
    text += sortedType + ":" + byType[sortedType];
  }
  return text;
}

function OpexC121EngTabBeginPass(sliced, resumeState, catalog, targetTownId)
{
  if (!PROBE_C121_ENGINE_TABLE) return;
  /* Une tranche reprise restaure l'identifiant de SA passe sans toucher au
   * compteur : un etat reprenable ancien peut etre repris entre deux passes
   * neuves, et ne doit pas faire reculer la numerotation. */
  if (sliced && resumeState != null && ("c121EngTabPass" in resumeState)) {
    C121_ENGTAB_PASS = resumeState.c121EngTabPass;
    return;
  }
  C121_ENGTAB_NEXT = C121_ENGTAB_NEXT + 1;
  C121_ENGTAB_PASS = C121_ENGTAB_NEXT;
  if (sliced && resumeState != null) resumeState.c121EngTabPass <- C121_ENGTAB_PASS;
  OpexC121EngTabEmitPass(catalog, sliced, targetTownId);
}

function OpexC121EngTabEmitPass(catalog, sliced, targetTownId)
{
  if (!PROBE_C121_ENGINE_TABLE) return;
  AILog.Info("C121_ENGTAB_PASS pass=" + C121_ENGTAB_PASS
      + " date=" + OpexC121EngTabDate()
      + " sliced=" + (sliced ? 1 : 0)
      + " target=" + targetTownId
      + " engines=" + OpexC121EngTabEngineSignature(catalog));
}

function OpexC121EngTabEmitEng(plan, engineId, upperScore, evaluated, economics)
{
  if (!PROBE_C121_ENGINE_TABLE) return;
  local score = -1;
  local profit = -1;
  local capital = -1;
  if (evaluated && economics != null) {
    if ("decisionScore" in economics) score = economics.decisionScore;
    else if ("score" in economics) score = economics.score;
    if ("decisionProfitAnnual" in economics) profit = economics.decisionProfitAnnual;
    else if ("profitAnnual" in economics) profit = economics.profitAnnual;
    if ("capital" in economics) capital = economics.capital;
  }
  AILog.Info("C121_ENGTAB_ENG pass=" + C121_ENGTAB_PASS
      + " key=" + OpexC121EngTabKey(plan)
      + " eng=" + engineId
      + " upper=" + upperScore
      + " eval=" + evaluated
      + " score=" + score
      + " P=" + profit
      + " C=" + capital);
}

function OpexC121EngTabEmitPruned(plan, candidates, seen)
{
  if (!PROBE_C121_ENGINE_TABLE) return;
  if (candidates == null) return;
  for (local i = seen; i < candidates.len(); i = i + 1) {
    local candidate = candidates[i];
    OpexC121EngTabEmitEng(plan, candidate.plane.id, candidate.upperScore, 0, null);
  }
}

function OpexC121EngTabEmitHit(plan)
{
  if (!PROBE_C121_ENGINE_TABLE) return;
  AILog.Info("C121_ENGTAB_HIT pass=" + C121_ENGTAB_PASS
      + " key=" + OpexC121EngTabKey(plan));
}

function OpexC121EngTabNum(obj, name)
{
  if (obj == null || !(name in obj) || obj[name] == null) return -1;
  return obj[name];
}

function OpexC121EngTabScoreOf(obj, preferDecision)
{
  if (obj == null) return -1;
  if (preferDecision && ("decisionScore" in obj) && obj.decisionScore != null) return obj.decisionScore;
  if ("score" in obj && obj.score != null) return obj.score;
  return -1;
}

function OpexC121EngTabDemand(plan, name)
{
  if (plan == null || !("c121Demand" in plan) || plan.c121Demand == null) return -1;
  if (!(name in plan.c121Demand) || plan.c121Demand[name] == null) return -1;
  return plan.c121Demand[name];
}

function OpexC121EngTabEmitPlan(plan, routeChoice)
{
  if (!PROBE_C121_ENGINE_TABLE) return;
  local opening = (routeChoice != null && ("economics" in routeChoice)) ? routeChoice.economics : null;
  local decision = (routeChoice != null && ("decisionEconomics" in routeChoice)
      && routeChoice.decisionEconomics != null) ? routeChoice.decisionEconomics : null;
  local portfolio = (routeChoice != null && ("portfolioEconomics" in routeChoice)
      && routeChoice.portfolioEconomics != null) ? routeChoice.portfolioEconomics : null;
  local rankObj = opening;
  if (!C121_AIR_INITIAL_PROJECT_ECONOMICS) {
    if (decision != null) rankObj = decision;
  }
  local eng = -1;
  if (routeChoice != null && ("plane" in routeChoice) && routeChoice.plane != null
      && ("id" in routeChoice.plane)) eng = routeChoice.plane.id;
  local planes = -1;
  if (routeChoice != null && ("targetPlanes" in routeChoice) && routeChoice.targetPlanes != null)
    planes = routeChoice.targetPlanes;
  else if (opening != null && ("planes" in opening) && opening.planes != null)
    planes = opening.planes;
  local dist = (plan != null && ("distance" in plan) && plan.distance != null) ? plan.distance : -1;
  local ap = -1;
  if (plan != null && ("airport" in plan) && plan.airport != null && ("type" in plan.airport))
    ap = plan.airport.type;
  local arm = (plan != null && ("arm" in plan) && plan.arm != null) ? plan.arm : "na";
  local n1P = -1;
  local n1C = -1;
  local n2P = -1;
  local n2C = -1;
  if (C121_ENGTAB_N1 != null) {
    n1P = OpexC121EngTabNum(C121_ENGTAB_N1, "profitAnnual");
    n1C = OpexC121EngTabNum(C121_ENGTAB_N1, "capital");
  }
  if (C121_ENGTAB_N2 != null) {
    n2P = OpexC121EngTabNum(C121_ENGTAB_N2, "profitAnnual");
    n2C = OpexC121EngTabNum(C121_ENGTAB_N2, "capital");
  }
  local initFlag = C121_AIR_INITIAL_PROJECT_ECONOMICS ? 1 : 0;
  local splitFlag = 0;
  local ge = 0;
  local geEst = -1;
  if (plan != null && ("c121GeMode" in plan) && plan.c121GeMode != null) ge = plan.c121GeMode;
  if (plan != null && ("c121GeEst" in plan) && plan.c121GeEst != null) geEst = plan.c121GeEst;
  AILog.Info("C121_ENGTAB_PLAN pass=" + C121_ENGTAB_PASS
      + " date=" + OpexC121EngTabDate()
      + " key=" + OpexC121EngTabKey(plan)
      + " arm=" + arm
      + " ap=" + ap
      + " dist=" + dist
      + " paxRawA=" + OpexC121EngTabDemand(plan, "paxRawA")
      + " paxRawB=" + OpexC121EngTabDemand(plan, "paxRawB")
      + " paxA=" + OpexC121EngTabDemand(plan, "paxA")
      + " paxB=" + OpexC121EngTabDemand(plan, "paxB")
      + " mailRawA=" + OpexC121EngTabDemand(plan, "mailRawA")
      + " mailRawB=" + OpexC121EngTabDemand(plan, "mailRawB")
      + " eng=" + eng
      + " score=" + OpexC121EngTabScoreOf(opening, false)
      + " P=" + OpexC121EngTabNum(opening, "profitAnnual")
      + " C=" + OpexC121EngTabNum(opening, "capital")
      + " dScore=" + OpexC121EngTabScoreOf(decision, true)
      + " dP=" + OpexC121EngTabNum(decision, "profitAnnual")
      + " dC=" + OpexC121EngTabNum(decision, "capital")
      + " pfScore=" + OpexC121EngTabScoreOf(portfolio, true)
      + " pfP=" + OpexC121EngTabNum(portfolio, "profitAnnual")
      + " pfC=" + OpexC121EngTabNum(portfolio, "capital")
      + " n=" + planes
      + " P_n1=" + n1P
      + " C_n1=" + n1C
      + " P_n2=" + n2P
      + " C_n2=" + n2C
      + " imm=" + OpexC121EngTabNum(rankObj, "immobilise")
      + " kdec=" + OpexC121EngTabNum(rankObj, "decisionKDec")
      + " init=" + initFlag
      + " split=" + splitFlag
      + " ge=" + ge
      + " ge_est=" + geEst);
}

function OpexC121EngTabAfterChoice(plan, routeChoice)
{
  if (!PROBE_C121_ENGINE_TABLE) return;
  if (plan == null || !("c121EngTabReal" in plan)) return;
  OpexC121EngTabEmitPlan(plan, routeChoice);
  if ("c121EngTabReal" in plan) delete plan.c121EngTabReal;
  C121_ENGTAB_N1 = null;
  C121_ENGTAB_N2 = null;
}
