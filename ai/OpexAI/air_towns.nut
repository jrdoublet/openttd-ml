/* Module AIR extrait de builder_air.nut (R11) : selection des villes, creneaux C83/V95 et hygiene des candidats. */
/* Les plus grosses villes, sans trier le catalogue lui-meme. L'insertion est deterministe et
 * garde l'ordre d'enumeration d'OpenTTD en cas d'egalite de population. */
function OpexAirSortedTowns(towns)
{
  local out = [];
  foreach (town in towns) {
    local pos = out.len();
    while (pos > 0 && out[pos - 1].pop < town.pop) pos--;
    out.insert(pos, town);
  }
  return out;
}

/* C78.3 : le vivier aerien n'a plus de plafond arbitraire en nombre de villes.
 * La capacite spatiale garde le plafond en cellules utile aux petites cartes,
 * puis ajoute une borne lineaire en perimetre pour eviter O(n^2) sur 1024+. */
function OpexAirTownPoolLimit(towns)
{
  if (towns == null || towns.len() == 0) return 0;
  local minDistance = AIR_TOWN_MIN_DISTANCE > 0 ? AIR_TOWN_MIN_DISTANCE : 1;
  local cellsX = (AIMap.GetMapSizeX() + minDistance - 1) / minDistance;
  local cellsY = (AIMap.GetMapSizeY() + minDistance - 1) / minDistance;
  local gridCapacity = cellsX * cellsY;
  local perimeterCapacity = 4 * (cellsX + cellsY);
  local spatialCapacity = gridCapacity < perimeterCapacity ? gridCapacity : perimeterCapacity;
  if (spatialCapacity < 2 && towns.len() >= 2) spatialCapacity = 2;
  return towns.len() < spatialCapacity ? towns.len() : spatialCapacity;
}

function OpexAirTownServed(town, lines, diag = null)
{
  /* Keep the non-diagnostic path byte-for-byte equivalent in its tests and short-circuiting. */
  if (!DECISION_LOG || diag == null) {
    if (lines == null) return false;
    foreach (line in lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      if (AIMap.DistanceManhattan(town.tile, line.originA) < 15) return true;
      if (AIMap.DistanceManhattan(town.tile, line.originB) < 15) return true;
    }
    return false;
  }

  if (lines == null) {
    diag.nullCalls++;
    diag.falseCalls++;
    if (DECISION_LOG && !diag.noAirLogged) {
      diag.noAirLogged = true;
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=null line_count=0"
                 + " air_line_count=0 verdict=0 comparisons=none");
    }
    return false;
  }
  if (lines.len() == 0) diag.emptyCalls++;
  else diag.nonemptyCalls++;

  local comparisons = "";
  local airLineCount = 0;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    local distanceA = AIMap.DistanceManhattan(town.tile, line.originA);
    if (distanceA < 15) {
      diag.trueCalls++;
      return true;
    }
    local distanceB = AIMap.DistanceManhattan(town.tile, line.originB);
    if (distanceB < 15) {
      diag.trueCalls++;
      return true;
    }
    comparisons += " line" + airLineCount
        + "_id=" + (("lineId" in line) ? line.lineId : "none")
        + " line" + airLineCount + "_originA=" + line.originA
        + " line" + airLineCount + "_originB=" + line.originB
        + " line" + airLineCount + "_distA=" + distanceA
        + " line" + airLineCount + "_distB=" + distanceB;
    airLineCount++;
  }
  diag.falseCalls++;
  if (airLineCount == 0 && !diag.noAirLogged) {
    diag.noAirLogged = true;
    if (DECISION_LOG) {
      local linesState = lines.len() == 0 ? "empty" : "nonempty";
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=" + linesState
                 + " line_count=" + lines.len()
                 + " air_line_count=0 verdict=0 comparisons=none");
    }
  }
  /* One record per failed town per OpexAirPlans invocation: repeated combo/site scans compare
   * the same immutable town and lines, so suppressing duplicates loses no comparison. */
  if (airLineCount > 0 && !(town.id in diag.loggedFalseTowns)) {
    diag.loggedFalseTowns[town.id] <- true;
    diag.loggedFalseCount++;
    if (DECISION_LOG) {
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=nonempty line_count=" + lines.len()
                 + " air_line_count=" + airLineCount + " verdict=0" + comparisons);
    }
  }
  return false;
}

/* C83.1 : avec la limite historique de deux aeroports par ville, ce signal
 * donne directement le nombre de slots restants. Il n'est valable que lorsque
 * la regle de bruit est desactivee et que le conseil municipal n'est pas en
 * mode permissif (qui leve la limite). */
function OpexAirC83SlotSignalEnabled()
{
  return AIGameSettings.IsValid("economy.station_noise_level")
      && AIGameSettings.GetValue("economy.station_noise_level") == 0
      && AIGameSettings.IsValid("difficulty.town_council_tolerance")
      && AIGameSettings.GetValue("difficulty.town_council_tolerance") != 3;
}

function OpexAirC83SecondSlotOpen(town)
{
  if (!OpexAirC83SlotSignalEnabled() || town == null
      || !("id" in town) || !AITown.IsValidTown(town.id)) return false;
  if (AITown.GetPopulation(town.id) < AIR_EARLY_SLOT_MIN_POP) return false;
  return AITown.GetAllowedNoise(town.id) == 1;
}

/* Plancher des grands aeroports (combo large), 600 aujourd'hui. Point unique :
 * un futur reglage du type V93_AIRPORT_MIN_POP se brancherait ici. */
function OpexAirLargeAirportMinPop()
{
  return 600;
}

/* Plancher de la preemption C83. Le plancher historique reste 600. Si V93 est
 * arme, le plancher minimal de ce reglage remplace les 600, et seulement ici. */
function OpexAirPreemptMinPop()
{
  if (V93_AIRPORT_NO_POP_FLOOR) return V93_AIRPORT_MIN_POP;
  return OpexAirLargeAirportMinPop();
}

/* Plus grande ville encore vide : deux slots libres, population au plancher,
 * aucun aeroport Opex impute a cette ville. Une seule cible. */
function OpexAirPreemptPickTown(towns, ownCounts)
{
  if (!C83_PREEMPT_OPEN || !OpexAirC83SlotSignalEnabled() || towns == null) return null;
  local floor = OpexAirPreemptMinPop();
  local best = null;
  local bestPop = -1;
  foreach (town in towns) {
    if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) continue;
    local pop = AITown.GetPopulation(town.id);
    if (pop < floor) continue;
    if (AITown.GetAllowedNoise(town.id) != 2) continue;
    if (ownCounts != null && (town.id in ownCounts)) continue;
    if (best == null || pop > bestPop || (pop == bestPop && town.id < best.id)) {
      best = town;
      bestPop = pop;
    }
  }
  return best;
}

/* Ville debitÃƒÆ’Ã‚Â©e par le moteur pour un aeroport : ClosestTown de l'ancre
 * (CmdBuildAirport), pas GetNearestTown ni la ville commerciale du site. */
function OpexAirSlotTownId(anchor)
{
  if (anchor == null || !AIMap.IsValidTile(anchor)) return -1;
  local townId = AITile.GetClosestTown(anchor);
  if (townId >= 0 && AITown.IsValidTown(townId)) return townId;
  return -1;
}

function OpexAirOwnSlotTownCounts()
{
  local counts = {};
  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local townId = OpexAirSlotTownId(AIStation.GetLocation(st));
    if (townId < 0) continue;
    local n = (townId in counts) ? counts[townId] : 0;
    counts.rawset(townId, n + 1);
  }
  return counts;
}

/* V126 : trouve l'aeroport Opex impute a la ville et compte ses lignes AIR.
 * Une ville peut avoir plusieurs stations AIR dans des configurations speciales ;
 * le candidat est admissible si au moins un aeroport vivant de cette ville reste
 * sous le plafond de deux routes. */
function OpexAirV126ServedTownState(town, lines)
{
  local state = { eligible = false, stationId = -1, routes = 0, noise = -1 };
  if (!V126_AIR_SERVED_TOWN_REUSE || town == null || !("id" in town)
      || !AITown.IsValidTown(town.id)) return state;

  state.noise = AITown.GetAllowedNoise(town.id);
  if (state.noise < 1) return state;

  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local loc = AIStation.GetLocation(st);
    if (OpexAirSlotTownId(loc) != town.id) continue;
    local routes = 0;
    if (lines != null) {
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        local stationA = ("stationA" in line) ? line.stationA : -1;
        local stationB = ("stationB" in line) ? line.stationB : -1;
        if (stationA == st || stationB == st) routes++;
      }
    }
    if (routes < 2) {
      state.eligible = true;
      state.stationId = st;
      state.routes = routes;
      return state;
    }
  }
  return state;
}

/* V134 : verifie si un aeroport existant d'une ville a atteint AIR_HUB_MAX_ROUTES
 * et si la ville ouvre un second slot (OpexAirC83SecondSlotOpen). */
function OpexAirV134SaturatedHubState(town, lines, hubIndex = null)
{
  local state = { eligible = false, hubRoutes = 0 };
  if (!V134_AIR_P2P_SATURATED_HUB || town == null || !("id" in town)
      || !AITown.IsValidTown(town.id)) return state;

  if (!OpexAirC83SecondSlotOpen(town)) return state;

  local capRoutes = (AIR_HUB_MAX_ROUTES > 0) ? AIR_HUB_MAX_ROUTES : 3;
  local maxRoutes = 0;
  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local loc = AIStation.GetLocation(st);
    if (OpexAirSlotTownId(loc) != town.id) continue;
    local routes = 0;
    if (hubIndex != null && ("routes" in hubIndex) && (st in hubIndex.routes)) {
      routes = hubIndex.routes[st];
    } else if (lines != null) {
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        local stA = AIR_HUB_FIX ? OpexAirLineStationId(line, 0)
            : (AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA));
        local stB = AIR_HUB_FIX ? OpexAirLineStationId(line, 1)
            : (AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB));
        if (stA == st || stB == st) routes++;
      }
    }
    if (routes > maxRoutes) maxRoutes = routes;
    if (routes >= capRoutes) {
      state.eligible = true;
      state.hubRoutes = routes;
      return state;
    }
  }
  state.hubRoutes = maxRoutes;
  return state;
}

/* V95 causal : le second slot doit etre encore libre et le premier doit etre
 * detenu par un tiers. Avec station_noise_level=0, slots=1 et zero aeroport
 * Opex sur la ville physique impliquent exactement un aeroport concurrent. */
function OpexAirV95CompetitorSecondSlotOpen(town, anchor = null)
{
  if (!OpexAirC83SlotSignalEnabled() || town == null || !("id" in town)
      || !AITown.IsValidTown(town.id)) return false;
  if (anchor != null && OpexAirSlotTownId(anchor) != town.id) return false;
  if (AITown.GetAllowedNoise(town.id) != 1) return false;
  local ownCounts = OpexAirOwnSlotTownCounts();
  return !(town.id in ownCounts) || ownCounts[town.id] == 0;
}

/* Ville encore disputable : population du plancher grand aeroport, au moins un
 * slot, et aucun aeroport Opex dont l'ancre est imputee a cette ville. */
function OpexAirC83TownContestable(town, ownCounts)
{
  if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) return false;
  if (AITown.GetPopulation(town.id) < OpexAirLargeAirportMinPop()) return false;
  if (AITown.GetAllowedNoise(town.id) < 1) return false;
  if (ownCounts != null && (town.id in ownCounts)) return false;
  return true;
}

/* Meme predicat que la derniere boucle de OpexAirBatchPlanStillLive : une ligne
 * aerienne relie deja les centres-villes (originA/originB), pas les tuiles d'aeroport. */
function OpexAirTownCentersLinked(tileA, tileB, lines)
{
  if (lines == null || tileA == null || tileB == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if ((line.originA == tileA && line.originB == tileB) ||
        (line.originA == tileB && line.originB == tileA)) return true;
  }
  return false;
}

function OpexAirC78NoteNoSite(probes, reason)
{
  if (!C69_BOTTLENECK_PROBE || probes == null) return;
  if ("c78NoSite" in probes) probes.c78NoSite = reason;
  else probes.c78NoSite <- reason;
}

/* C83.1 : petit ensemble surveille par la course reactive. Contrairement a
 * OpexAirSortedTowns, ce helper ne trie jamais tout le catalogue : il maintient
 * seulement les K plus grandes villes, donc O(n*K) avec K=6 au defaut. */
function OpexAirC83WatchTowns(towns)
{
  local best = [];
  if (!OpexAirC83SlotSignalEnabled() || towns == null || AIR_C83_TARGET_TOWNS <= 0) {
    return best;
  }
  local ownCounts = null;
  if (C83_FIXES) ownCounts = OpexAirOwnSlotTownCounts();
  foreach (town in towns) {
    if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) continue;
    local pop = AITown.GetPopulation(town.id);
    if (C83_FIXES) {
      if (!OpexAirC83TownContestable(town, ownCounts)) continue;
    } else if (pop < AIR_EARLY_SLOT_MIN_POP) continue;
    local item = { town = town, pop = pop };
    local pos = best.len();
    while (pos > 0 && best[pos - 1].pop < pop) pos--;
    if (pos >= AIR_C83_TARGET_TOWNS) continue;
    best.insert(pos, item);
    if (best.len() > AIR_C83_TARGET_TOWNS) best.pop();
  }
  local out = [];
  foreach (item in best) out.append(item.town);
  return out;
}

/* ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´ Une ligne aerienne stocke des TUILES d'aeroport dans stationA/stationB, malgre leur nom :
 * OpexBuildAirRoute calcule bien les StationID (`:831-832`) puis rend `result.stationA = airportA`,
 * la tuile. main.nut lit ces champs comme des tuiles partout (`GetStationID(line.stationA)` en
 * :1046, :1319, :2034) -- la convention "tuile" est donc la bonne. Seul le code de hub ci-dessous
 * les prenait pour des StationID deja resolus, avec trois consequences mesurees le 2026-09-03 :
 *   1. la garde `alreadyConnected` comparait un StationID a une tuile : TOUJOURS fausse, d'ou
 *      NEUF liaisons sur la meme paire de villes (graine 42, 1970-1972) ;
 *   2. la decouverte de hub testait `IsAirportTile()` sur un CENTRE-VILLE : toujours fausse, donc
 *      tous les aeroports tombaient dans le repli "orphelins" avec `routes = 0` code en dur ;
 *   3. `routes = 0` rendait le plafond `maxRoutes` inoperant ET annulait la decote de saturation
 *      `hubMonthly / (routes + 1)`, qui divisait donc toujours par 1.
 * Resoudre la tuile en StationID repare les trois d'un coup. */
function OpexAirLineStationId(line, which)
{
  local tile = (which == 0) ? line.stationA : line.stationB;
  if (tile == null || !AIMap.IsValidTile(tile)) return -1;
  return AIStation.GetStationID(tile);
}

/* V133. Les appelants testent V133_AIR_BUILD_RETRY avant d'entrer ici :
 * a 0 la fonction n'est pas appelee. 730 jours de jeu, pas un reglage. */
function OpexV133Log(message)
{
  AILog.Info(message);
  OpexC56TaskLog("V133", "air", "-", message);
}

function OpexV133AirTownQuarantined(townId)
{
  if (townId == null || townId < 0) return false;
  if (!(townId in V133_AIR_QUARANTINE)) return false;
  local untilDate = V133_AIR_QUARANTINE[townId];
  if (AIDate.GetCurrentDate() >= untilDate) {
    delete V133_AIR_QUARANTINE[townId];
    return false;
  }
  return true;
}

function OpexV133TownIdOf(node)
{
  if (node == null || !("town" in node) || node.town == null || !("id" in node.town)) return -1;
  return node.town.id;
}

function OpexV133LogAirSkip(seen, townId)
{
  if (townId == null || townId < 0) return;
  if (seen != null && (townId in seen)) return;
  if (seen != null) seen.rawset(townId, true);
  OpexV133Log("V133_SKIP town=" + townId);
}

/* Vrai si la ville est encore en quarantaine. Journal V133_SKIP une fois
 * par ville et par balayage (table vue sur le contexte de generation). */
function OpexV133AirTownSkip(ctx, townId)
{
  if (!OpexV133AirTownQuarantined(townId)) return false;
  if (ctx != null && !("v133Skip" in ctx)) ctx.v133Skip <- {};
  local seen = (ctx != null) ? ctx.v133Skip : null;
  OpexV133LogAirSkip(seen, townId);
  return true;
}

function OpexV133AirBuildReason(error, errorText)
{
  if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES) return "authority";
  if (error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) return "station_limit";
  if (error == AIError.ERR_FLAT_LAND_REQUIRED) return "terrain";
  if (error == AIError.ERR_LAND_SLOPED_WRONG) return "terrain";
  if (error == AIError.ERR_AREA_NOT_CLEAR) return "unbuildable";
  if (error == AIError.ERR_SITE_UNSUITABLE) return "unbuildable";
  if (typeof errorText == "string") {
    if (errorText.find("recovery") != null) return null;
    if (errorText.find("non-flat") != null) return "terrain";
    if (errorText.find("invalid airport footprint") != null) return "footprint";
    if (errorText.find("invalid airport preflight") != null) return "footprint";
    if (errorText.find("airport site preflight failed") != null) return "unbuildable";
    if (errorText.find("airport preflight error") != null) return "unbuildable";
  }
  if (error == AIError.ERR_PRECONDITION_FAILED) return "footprint";
  return null;
}

/* Extremite neuve seulement : un hub reuse ne depend pas du site fautif. */
function OpexV133AirPlanUsesTown(plan, townId)
{
  if (plan == null || townId == null || townId < 0) return false;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (!reuseA && OpexV133TownIdOf(("siteA" in plan) ? plan.siteA : null) == townId) return true;
  if (!reuseB && OpexV133TownIdOf(("siteB" in plan) ? plan.siteB : null) == townId) return true;
  return false;
}

function OpexV133CountBatchSalvage(best, rank, townA, townB)
{
  local kept = 0;
  local dropped = 0;
  if (best != null) {
    for (local j = rank + 1; j < best.len(); j++) {
      local other = best[j];
      if (other == null || !("mode" in other) || other.mode != "air") continue;
      if (!("payload" in other) || other.payload == null) continue;
      if (OpexV133AirPlanUsesTown(other.payload, townA)
          || OpexV133AirPlanUsesTown(other.payload, townB)) dropped++;
      else kept++;
    }
  }
  local tally = {};
  tally.kept <- kept;
  tally.dropped <- dropped;
  return tally;
}

function OpexV133LogBatchSalvage(best, rank, townA, townB)
{
  local tally = OpexV133CountBatchSalvage(best, rank, townA, townB);
  OpexV133Log("V133_BATCH_SALVAGE kept=" + tally.kept + " dropped=" + tally.dropped);
}

function OpexV133OnAirSiteFailed(best, rank, townId, reason)
{
  if (!V133_AIR_BUILD_RETRY || townId == null || townId < 0) return;
  local untilDate = AIDate.GetCurrentDate() + 730;
  V133_AIR_QUARANTINE.rawset(townId, untilDate);
  OpexV133Log("V133_QUARANTINE town=" + townId + " reason=" + reason + " until=" + untilDate);
  local freshTown = !(townId in V133_AIR_BATCH_FAILED);
  V133_AIR_BATCH_FAILED.rawset(townId, true);
  if (freshTown) OpexV133LogBatchSalvage(best, rank, townId, -1);
}

/* batch_plan_dead : la ville neuve deja desservie est le site pris.
 * On ne la met pas en quarantaine (ce n'est pas un echec physique).
 * Les paires du lot qui ne l'utilisent pas restent sur le parcours normal. */
function OpexV133SalvageDeadPlan(best, rank, plan, lines)
{
  if (!V133_AIR_BUILD_RETRY || plan == null) return;
  local townA = -1;
  local townB = -1;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (!reuseA) {
    local idA = OpexV133TownIdOf(("siteA" in plan) ? plan.siteA : null);
    if (idA >= 0 && ("siteA" in plan) && plan.siteA != null
        && OpexAirTownServed(plan.siteA.town, lines)) townA = idA;
  }
  if (!reuseB) {
    local idB = OpexV133TownIdOf(("siteB" in plan) ? plan.siteB : null);
    if (idB >= 0 && ("siteB" in plan) && plan.siteB != null
        && OpexAirTownServed(plan.siteB.town, lines)) townB = idB;
  }
  if (townA < 0 && townB < 0) return;
  local freshTown = false;
  if (townA >= 0 && !(townA in V133_AIR_BATCH_FAILED)) {
    V133_AIR_BATCH_FAILED.rawset(townA, true);
    freshTown = true;
  }
  if (townB >= 0 && !(townB in V133_AIR_BATCH_FAILED)) {
    V133_AIR_BATCH_FAILED.rawset(townB, true);
    freshTown = true;
  }
  if (freshTown) OpexV133LogBatchSalvage(best, rank, townA, townB);
}

/* Quarantaine : les deux bouts, y compris un hub. Lot fautif de la passe :
 * seulement l'extremite neuve, pour ne pas ecarter un hubhub independent. */
function OpexV133AirPlanBlocked(plan)
{
  if (plan == null) return false;
  if (OpexV133EndpointBlocked(plan, true)) return true;
  if (OpexV133EndpointBlocked(plan, false)) return true;
  return false;
}

function OpexV133EndpointBlocked(plan, isA)
{
  local site = isA ? (("siteA" in plan) ? plan.siteA : null) : (("siteB" in plan) ? plan.siteB : null);
  local reuse = isA ? (("reuseA" in plan) && plan.reuseA) : (("reuseB" in plan) && plan.reuseB);
  local townId = OpexV133TownIdOf(site);
  if (townId < 0) return false;
  if (OpexV133AirTownQuarantined(townId)) return true;
  if (!reuse && (townId in V133_AIR_BATCH_FAILED)) return true;
  return false;
}

function OpexV133LogBlockedTowns(plan)
{
  if (plan == null) return;
  local idA = OpexV133TownIdOf(("siteA" in plan) ? plan.siteA : null);
  local idB = OpexV133TownIdOf(("siteB" in plan) ? plan.siteB : null);
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (idA >= 0 && (OpexV133AirTownQuarantined(idA) || (!reuseA && (idA in V133_AIR_BATCH_FAILED)))) {
    OpexV133LogAirSkip(V133_AIR_SKIP_LOGGED, idA);
  }
  if (idB >= 0 && idB != idA
      && (OpexV133AirTownQuarantined(idB) || (!reuseB && (idB in V133_AIR_BATCH_FAILED)))) {
    OpexV133LogAirSkip(V133_AIR_SKIP_LOGGED, idB);
  }
}

function OpexV133NoteUnbuildableEndpoint(best, rank, site, reuse)
{
  if (!V133_AIR_BUILD_RETRY || reuse) return;
  local townId = OpexV133TownIdOf(site);
  if (townId < 0) return;
  local anchorOk = site != null && ("anchor" in site) && AIMap.IsValidTile(site.anchor);
  if (anchorOk && OpexAirRecoveryOwnsAirport(site.anchor)) return;
  local reason = OpexV133AirBuildReason(V133_AIR_LAST_SITE_ERROR, "");
  if (reason == null) reason = "unbuildable";
  OpexV133OnAirSiteFailed(best, rank, townId, reason);
}

function OpexV133NoteBuildFailure(best, rank, plan, result)
{
  if (!V133_AIR_BUILD_RETRY || plan == null || result == null) return;
  local why = ("reason" in result) ? result.reason : "";
  local site = null;
  local reuse = false;
  if (why == "PREA" || why == "AFAIL") {
    site = ("siteA" in plan) ? plan.siteA : null;
    reuse = ("reuseA" in plan) && plan.reuseA;
  } else if (why == "PREB" || why == "BFAIL") {
    site = ("siteB" in plan) ? plan.siteB : null;
    reuse = ("reuseB" in plan) && plan.reuseB;
  } else {
    return;
  }
  if (reuse) return;
  local townId = OpexV133TownIdOf(site);
  if (townId < 0) return;
  local reason = OpexV133AirBuildReason(("error" in result) ? result.error : 0,
      ("errorText" in result) ? result.errorText : "");
  if (reason == null) return;
  OpexV133OnAirSiteFailed(best, rank, townId, reason);
}

function OpexV133SaveQuarantine(target)
{
  if (!V133_AIR_BUILD_RETRY || V133_AIR_QUARANTINE.len() == 0 || target == null) return;
  local flat = [];
  foreach (townId, untilDate in V133_AIR_QUARANTINE) {
    flat.append(townId.tointeger());
    flat.append(untilDate.tointeger());
  }
  target.v133AirQuarantine <- flat;
}

function OpexV133LoadQuarantine(data)
{
  V133_AIR_QUARANTINE = {};
  if (data == null || !("v133AirQuarantine" in data) || data.v133AirQuarantine == null) return;
  local flat = data.v133AirQuarantine;
  for (local i = 0; i + 1 < flat.len(); i += 2) {
    V133_AIR_QUARANTINE.rawset(flat[i], flat[i + 1]);
  }
}
