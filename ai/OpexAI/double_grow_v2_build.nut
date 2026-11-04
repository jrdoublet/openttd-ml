/* DOUBLE-GROW v2 : ajout differe d'une seconde voie a une ligne fret
 * SIMPLE deja ouverte. Reprend le constructeur independant V190 avec une
 * recherche A* locale bornee, sans intervenir dans le slot _railSearch.
 * Les quais, le depot et la voie primaire sont proteges durant la pose.
 * La transformation directionnelle (aiguillages et PBS) est deleguee a
 * OpexDoubleGrowFleetFinalize, qui refuse toute paire non certifiee.
 * Aucune voie independante a deux rames ne devient une ligne >2 rames. */
/* Etat transitoire : owner._doubleGrowV2State est declare dans OpexAI.
 * Save/Load repart avec une recherche vide, sans changement sur la carte. */

/* Devis de la route effectivement retenue, et non longueur de la ligne 1.
 * Le cout de la voie peut venir d'AIAccounting/AITestMode apres succes
 * natif ; avant ce test, il est estime a partir des cases du trajet. */
function OpexDoubleGrowV2Quote(owner, line, tiles, padA = null, padB = null,
                               nativeTrackCost = -1)
{
  if (owner == null || owner._catalog == null || line == null
      || tiles == null || tiles.len() < 2 || !("depot" in line)
      || !AIRail.IsRailDepotTile(line.depot)) return -1;
  local railType = AIRail.GetRailType(line.depot);
  local unitCost = AIRail.GetBuildCost(railType, AIRail.BT_TRACK);
  local depotCost = AIRail.GetBuildCost(railType, AIRail.BT_DEPOT);
  local lengthA = padA != null ? padA.length
      : (("platformLength" in line) ? line.platformLength : 0);
  local lengthB = padB != null ? padB.length
      : (("platformLength" in line) ? line.platformLength : 0);
  if (unitCost <= 0 || depotCost <= 0 || lengthA <= 0 || lengthB <= 0)
    return -1;
  local trackCost = nativeTrackCost >= 0 ? nativeTrackCost : tiles.len() * unitCost;
  local trainCost = 0;
  if (("vehicles" in line) && line.vehicles != null && line.vehicles.len() > 0
      && AIVehicle.IsValidVehicle(line.vehicles[0])) {
    local sample = line.vehicles[0];
    for (local i = 0; i < AIVehicle.GetNumWagons(sample); i++) {
      local engine = AIVehicle.GetWagonEngineType(sample, i);
      if (AIEngine.IsBuildable(engine)) trainCost += AIEngine.GetPrice(engine);
    }
  }
  return trackCost + (lengthA + lengthB) * owner._catalog.costStation
      + depotCost + trainCost;
}

function OpexDoubleGrowV2BuildLog(line, step, reason, tile = -1,
                                  owner = null, tiles = null, padA = null,
                                  padB = null, nativeTrackCost = -1)
{
  if (!DECISION_LOG) return;
  local quote = OpexDoubleGrowV2Quote(owner, line, tiles, padA, padB, nativeTrackCost);
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  OpexDecide("DOUBLE_GROW", "version=2 phase=build"
      + " line=" + (line != null && ("lineId" in line) ? line.lineId : -1)
      + " step=" + step + " reason=" + reason
      + " tile=" + tile + " quote=" + quote
      + " quote_kind=" + (quote < 0 ? "not_routed"
          : (nativeTrackCost >= 0 ? "native_track" : "route_estimate"))
      + " reserve=50000 cash=" + cash
      + " available=" + OpexAvailableCapital());
}

/* Le pathfinder V129 retourne [station_exit_A, lead_A, ..., lead_B,
 * station_exit_B] : sa source a la gare comme parent, son but ajoute
 * station_exit_B dans FindPath. Ecrire les quatre tuiles reelles et celles
 * de la paire de quais retenue pour verifier la convention en smoke. */
function OpexDoubleGrowV2PathLog(line, tiles, planA = null, planB = null)
{
  if (!DECISION_LOG) return;
  local n = tiles != null ? tiles.len() : 0;
  OpexDecide("DOUBLE_GROW", "version=2 phase=astar_endpoints"
      + " line=" + line.lineId + " path_len=" + n
      + " path_a_exit=" + (n >= 1 ? tiles[0] : -1)
      + " path_a_lead=" + (n >= 2 ? tiles[1] : -1)
      + " path_b_lead=" + (n >= 2 ? tiles[n - 2] : -1)
      + " path_b_exit=" + (n >= 1 ? tiles[n - 1] : -1)
      + " site_a_exit=" + (planA != null ? planA.station_exit : -1)
      + " site_a_lead=" + (planA != null ? planA.lead : -1)
      + " site_b_lead=" + (planB != null ? planB.lead : -1)
      + " site_b_exit=" + (planB != null ? planB.station_exit : -1));
}

function OpexDoubleGrowV2SiteLog(line, diag, padsA, padsB, eligibleA, eligibleB)
{
  if (!DECISION_LOG) return;
  OpexDecide("DOUBLE_GROW", "version=2 phase=sites line=" + line.lineId
      + " a_plans=" + padsA.len() + " b_plans=" + padsB.len()
      + " a_eligible=" + eligibleA.len() + " b_eligible=" + eligibleB.len()
      + " a_try=" + (("a_site_try" in diag) ? diag.a_site_try : 0)
      + " b_try=" + (("b_site_try" in diag) ? diag.b_site_try : 0)
      + " a_occupied=" + (("a_site_occupied" in diag) ? diag.a_site_occupied : 0)
      + " b_occupied=" + (("b_site_occupied" in diag) ? diag.b_site_occupied : 0)
      + " a_join=" + (("a_site_join" in diag) ? diag.a_site_join : 0)
      + " b_join=" + (("b_site_join" in diag) ? diag.b_site_join : 0)
      + " obstacle=" + (("obstacle_first_kind" in diag) ? diag.obstacle_first_kind : "none")
      + " obstacle_tile=" + (("obstacle_first_tile" in diag) ? diag.obstacle_first_tile : -1));
}

/* Les motifs clear_short / clear_forbidden portent deja _detail, _idx,
 * _tile depuis OpexDoubleGrowDiagnosticReject. Les autres motifs ont
 * seulement un compteur : retrouver la premiere tuile POUR LE LOG, sans
 * changer un seul predicat de OpexDoubleGrowClear. */
function OpexDoubleGrowV2ClearLocation(reason, tiles, structures, pA, pB)
{
  local missing = { index = -1, tile = -1, detail = "not_located" };
  if (tiles == null) return missing;
  if (reason == "clear_turn") {
    local lastBit = 0;
    for (local i = 1; i < tiles.len() - 1; i++) {
      local bit = OpexV190Fix2TrackBit(tiles[i - 1], tiles[i], tiles[i + 1]);
      if (bit == 0) {
        if (AIMap.DistanceManhattan(tiles[i - 1], tiles[i]) == 1 &&
            AIMap.DistanceManhattan(tiles[i], tiles[i + 1]) == 1)
          return { index = i, tile = tiles[i], detail = "unreadable_turn" };
        lastBit = 0;
        continue;
      }
      if ((lastBit == 1 && bit == 2) || (lastBit == 2 && bit == 1) ||
          ((lastBit == 4 || lastBit == 8) && (bit == 16 || bit == 32)) ||
          ((lastBit == 16 || lastBit == 32) && (bit == 4 || bit == 8)))
        return { index = i, tile = tiles[i], detail = "forbid_90_turn" };
      lastBit = bit;
    }
  } else if (reason == "clear_repeat") {
    local visited = {};
    for (local i = 0; i < tiles.len(); i++) {
      if (tiles[i] in visited)
        return { index = i, tile = tiles[i], detail = "repeated_tile" };
      visited[tiles[i]] <- true;
    }
  } else if (reason == "clear_pad") {
    foreach (pad in [pA, pB]) {
      for (local j = 0; j < pad.length; j++) {
        local t = pad.anchor + j * pad.step;
        if (t == pad.station_exit) continue;
        for (local i = 0; i < tiles.len(); i++)
          if (tiles[i] == t)
            return { index = i, tile = t, detail = "secondary_platform" };
      }
    }
  } else {
    for (local i = 1; i < tiles.len() - 1; i++) {
      local t = tiles[i];
      if (reason == "clear_occupied" &&
          (AIRail.IsRailTile(t) || AIRail.IsRailStationTile(t) ||
           AIRail.IsRailDepotTile(t) || AIBridge.IsBridgeTile(t) ||
           AITunnel.IsTunnelTile(t) ||
           AITile.HasTransportType(t, AITile.TRANSPORT_RAIL)))
        return { index = i, tile = t, detail = "existing_infrastructure" };
      if (reason == "clear_terrain" && !AITile.IsBuildable(t))
        return { index = i, tile = t, detail = OpexDoubleGrowObstacleKind(t) };
      if (reason == "clear_structure" && i + 1 < tiles.len() &&
          AIMap.DistanceManhattan(t, tiles[i + 1]) > 1 &&
          OpexPlannedStructureKind(structures, t, tiles[i + 1]) == null)
        return { index = i, tile = t, detail = "missing_bridge_or_tunnel" };
    }
  }
  return missing;
}

function OpexDoubleGrowV2ClearLog(line, diag, tiles, structures, pA, pB)
{
  if (!DECISION_LOG) return;
  local reason = "UNKNOWN";
  foreach (key in ["clear_short", "clear_turn", "clear_forbidden",
                   "clear_repeat", "clear_pad", "clear_occupied",
                   "clear_terrain", "clear_structure"]) {
    if ((key in diag) && diag[key] > 0) { reason = key; break; }
  }
  local detail = reason + "_detail";
  local indexKey = reason + "_idx";
  local tileKey = reason + "_tile";
  local location = (detail in diag)
      ? { detail = diag[detail], index = diag[indexKey], tile = diag[tileKey] }
      : OpexDoubleGrowV2ClearLocation(reason, tiles, structures, pA, pB);
  /* geometry_end_jump fournit volontairement index=-1 dans le helper
   * historique ; retrouver l'indice a partir de la tuile signalee. */
  if (location.index < 0 && location.tile >= 0 && tiles != null) {
    for (local i = 0; i < tiles.len(); i++) {
      if (tiles[i] == location.tile) { location.index = i; break; }
    }
  }
  OpexDecide("DOUBLE_GROW", "version=2 phase=clear ok=0"
      + " line=" + line.lineId
      + " reason=" + reason + " detail=" + location.detail
      + " index=" + location.index + " tile=" + location.tile);
}

/* Ensemble des emprises preexistantes. Le depot, son front et les deux
 * gorges sont proteges meme si le traceur historique ne les reference pas. */
function OpexDoubleGrowV2Protected(line, route)
{
  local blocked = {};
  foreach (tile in route) blocked[tile] <- true;
  foreach (platform in [line.platformA, line.platformB]) {
    for (local i = 0; i < platform.length; i++)
      blocked[platform.anchor + i * platform.step] <- true;
    blocked[platform.station_exit] <- true;
    blocked[platform.lead] <- true;
  }
  blocked[line.depot] <- true;
  local front = AIRail.GetRailDepotFrontTile(line.depot);
  if (AIMap.IsValidTile(front)) blocked[front] <- true;
  return blocked;
}

/* V190 independant / OpexJoinPlatformPlans : memes quais paralleles
 * perpendiculaires, longueur/axe inchanges, lead libre et terrain plat.
 * Le test BuildRailStation(..., stationId) du finder V1 eliminait ces
 * candidats AVANT l'A* sur une gare deja exploitee. Ici, ne pas tester la
 * jointure en admission : elle reste OBLIGATOIRE pendant la construction
 * reelle, avec controle du vrai StationID et rollback sinon. Les quelques
 * translations axiales V1 restent disponibles en repli sans demolition. */
function OpexDoubleGrowV2Pads(platform, stationId, diag, prefix)
{
  if (!AIStation.IsValidStation(stationId)) return [];
  local available = [];
  local sidewaysX = platform.direction == AIRail.RAILTRACK_NE_SW ? 0 : 1;
  local sidewaysY = platform.direction == AIRail.RAILTRACK_NE_SW ? 1 : 0;
  local dx = AIMap.GetTileX(platform.lead) - AIMap.GetTileX(platform.station_exit);
  local dy = AIMap.GetTileY(platform.lead) - AIMap.GetTileY(platform.station_exit);
  if (abs(dx) + abs(dy) != 1) return [];
  local maxSide = max(3, JOIN_PARALLEL_MAX_SIDE);
  local maxShift = min(3, platform.length - 1);
  for (local dist = 1; dist <= maxSide && available.len() < 16; dist++) {
    for (local shift = 0; shift <= maxShift && available.len() < 16; shift++) {
      foreach (flip in [-1, 1]) {
        OpexDoubleGrowDiagCount(diag, prefix + "_site_try");
        local offX = sidewaysX * dist * flip + dx * shift;
        local offY = sidewaysY * dist * flip + dy * shift;
        local anchor = OpexV190MakeTile(platform.anchor, offX, offY);
        local stationExit = OpexV190MakeTile(platform.station_exit, offX, offY);
        local lead = OpexV190MakeTile(platform.lead, offX, offY);
        if (anchor == null || stationExit == null || lead == null) {
          OpexDoubleGrowDiagCount(diag, prefix + "_site_bounds");
          continue;
        }
        local duplicate = false;
        foreach (p in available)
          if (p.anchor == anchor) { duplicate = true; break; }
        if (duplicate) continue;
        if (AIMap.DistanceManhattan(stationExit, lead) != 1) {
          OpexDoubleGrowDiagCount(diag, prefix + "_site_bounds");
          continue;
        }
        local usable = AITile.IsBuildable(lead)
            && AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
        if (!usable) {
          if (!AITile.IsBuildable(lead)) OpexDoubleGrowSiteBlocked(diag, prefix, lead, true);
          else OpexDoubleGrowDiagCount(diag, prefix + "_site_nonflat");
        }
        for (local j = 0; j < platform.length && usable; j++) {
          local tile = anchor + j * platform.step;
          if (!AIMap.IsValidTile(tile) ||
              (platform.direction == AIRail.RAILTRACK_NE_SW
                  ? AIMap.GetTileY(tile) != AIMap.GetTileY(anchor)
                      || abs(AIMap.GetTileX(tile) - AIMap.GetTileX(anchor)) != j
                  : AIMap.GetTileX(tile) != AIMap.GetTileX(anchor)
                      || abs(AIMap.GetTileY(tile) - AIMap.GetTileY(anchor)) != j)) {
            OpexDoubleGrowDiagCount(diag, prefix + "_site_bounds");
            usable = false;
          } else if (!AITile.IsBuildable(tile)) {
            OpexDoubleGrowSiteBlocked(diag, prefix, tile, false);
            usable = false;
          } else if (AITile.GetSlope(tile) != AITile.SLOPE_FLAT) {
            OpexDoubleGrowDiagCount(diag, prefix + "_site_nonflat");
            usable = false;
          }
        }
        if (!usable) continue;
        available.append({ anchor = anchor, station_exit = stationExit,
            lead = lead, direction = platform.direction, step = platform.step,
            length = platform.length, axialShift = shift, lateralDist = dist });
        OpexDoubleGrowDiagCount(diag, prefix + "_site_accept");
        if (available.len() >= 16) break;
      }
    }
  }
  return available;
}

/* Le parallele strict V190 ne passe pas a proximite des gares anciennes,
 * des depots ou des coudes. Construire une SECONDE route par l'A* independant
 * qu'utilise V190 comme repli, avec un budget local fixe et sans etat
 * _railSearch. La boucle de production donne la priorite aux nouveaux
 * projets avant d'appeler ce module. L'A* ne donne jamais l'autorisation
 * de franchir la voie primaire : controle explicite de chaque case. */
function OpexDoubleGrowV2Prepare(line, route)
{
  local idA = AIStation.GetStationID(line.stationA);
  local idB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(idA) || !AIStation.IsValidStation(idB)
      || idA == idB || route == null || route.len() < 36) return null;
  local blocked = OpexDoubleGrowV2Protected(line, route);
  local diag = DECISION_LOG ? {} : null;
  local padsA = OpexDoubleGrowV2Pads(line.platformA, idA, diag, "a");
  local padsB = OpexDoubleGrowV2Pads(line.platformB, idB, diag, "b");
  if (padsA.len() == 0 || padsB.len() == 0) {
    if (diag != null) OpexDoubleGrowV2SiteLog(line, diag, padsA, padsB, [], []);
    OpexDoubleGrowV2BuildLog(line, "site", "NO_V190_SITE_GEOMETRY");
    return null;
  }
  local eligibleA = [];
  foreach (pA in padsA) {
    if (OpexSameStationEnd(pA, line.platformA)
        && !OpexPlanHitsSet(pA, blocked)) eligibleA.append(pA);
  }
  local eligibleB = [];
  foreach (pB in padsB) {
    if (OpexSameStationEnd(pB, line.platformB)
        && !OpexPlanHitsSet(pB, blocked)) eligibleB.append(pB);
  }
  if (diag != null) OpexDoubleGrowV2SiteLog(line, diag, padsA, padsB, eligibleA, eligibleB);
  if (eligibleA.len() == 0 || eligibleB.len() == 0) {
    OpexDoubleGrowV2BuildLog(line, "plan", "SITES_HIT_PRIMARY");
    return null;
  }

  local ignored = [];
  foreach (tile, ignoredVal in blocked) ignored.append(tile);
  return { line = line, route = route, blocked = blocked,
      eligibleA = eligibleA, eligibleB = eligibleB, ignored = ignored };
}

/* Resolution de la seconde route : la trace trouvee par l'A* est un avis
 * de recherche, pas une autorisation de construire. La commande AITestMode
 * doit egalement accepter chaque tuile et chaque ouvrage. */
function OpexDoubleGrowV2Plan(line, prep, search)
{
  local route = prep.route;
  local blocked = prep.blocked;
  local eligibleA = prep.eligibleA;
  local eligibleB = prep.eligibleB;
  local owner = ("owner" in prep) ? prep.owner : null;
  local tiles = OpexResolveSearchTiles(search);
  local structures = OpexResolveSearchStructures(search);
  OpexDoubleGrowV2PathLog(line, tiles);
  if (tiles == null || tiles.len() < 36 ||
      structures == null || !OpexJoinPathIsDedicated(tiles)) {
    OpexDoubleGrowV2BuildLog(line, "astar", "SHORT_OR_NOT_DEDICATED",
        -1, owner, tiles);
    return null;
  }
  local pA = OpexMatchPlanExact(eligibleA, tiles[0], tiles[1]);
  local pB = OpexMatchPlanExact(eligibleB, tiles[tiles.len() - 1],
                              tiles[tiles.len() - 2]);
  OpexDoubleGrowV2PathLog(line, tiles, pA, pB);
  if (pA == null || pB == null || OpexPlanHitsSet(pB, blocked)) {
    OpexDoubleGrowV2BuildLog(line, "astar",
        pA == null ? "NO_EXACT_SOURCE" : (pB == null ? "NO_EXACT_GOAL" : "GOAL_PAD_PRIMARY"),
        -1, owner, tiles, pA, pB);
    return null;
  }
  local padASet = clone blocked;
  padASet[pA.lead] <- true;
  for (local i = 0; i < pA.length; i++)
    padASet[pA.anchor + i * pA.step] <- true;
  if (OpexPlanHitsSet(pB, padASet)) {
    OpexDoubleGrowV2BuildLog(line, "site", "SECONDARY_PAD_OVERLAP",
        pB.anchor, owner, tiles, pA, pB);
    return null;
  }
  local clearDiag = {};
  if (!OpexDoubleGrowClear(tiles, structures, blocked, pA, pB,
                            clearDiag, route, line.depot)) {
    OpexDoubleGrowV2ClearLog(line, clearDiag, tiles, structures, pA, pB);
    OpexDoubleGrowV2BuildLog(line, "clear", "GEOMETRY_FAILED",
        -1, owner, tiles, pA, pB);
    return null;
  }
  local native = null;
  local nativeTrackCost = -1;
  {
    local quoteAccount = AIAccounting();
    native = OpexTestRailTrack(tiles, structures);
    nativeTrackCost = quoteAccount.GetCosts();
  }
  if (native == null || native.failed != 0) {
    local tile = native != null && native.firstTile != null ? native.firstTile : -1;
    OpexDoubleGrowV2BuildLog(line, "native", "NATIVE_TRACK",
        tile, owner, tiles, pA, pB);
    if (DECISION_LOG && native != null) {
      local firstIndex = -1;
      for (local i = 0; i < tiles.len(); i++) {
        if (tiles[i] == tile) { firstIndex = i; break; }
      }
      OpexDecide("DOUBLE_GROW", "version=2 phase=native ok=0"
          + " line=" + line.lineId + " fails=" + native.failed
          + " first_index=" + firstIndex + " first_tile=" + tile
          + " first_segment=" + (native.firstSegment != null ? native.firstSegment : "none"));
    }
    return null;
  }
  OpexDoubleGrowV2BuildLog(line, "astar", "CERTIFIED_GEOMETRY");
  return { tiles1 = route, tiles2 = tiles, structures2 = structures,
      platformA2 = pA, platformB2 = pB, forbidden = blocked,
      stationIdA = AIStation.GetStationID(line.stationA),
      stationIdB = AIStation.GetStationID(line.stationB), depot2 = null,
      nativeTrackCost = nativeTrackCost };
}

function OpexDoubleGrowV2HasPending(owner)
{
  return owner != null && owner._doubleGrowV2State != null;
}

/* Begin ne pose aucun rail et ne change aucune rame. Le selecteur peut
 * laisser progresser l'A* entre les autres decisions de l'IA. */
function OpexDoubleGrowV2Begin(owner, line)
{
  if (!DOUBLE_GROW_V2 || owner == null || owner._doubleGrowV2State != null
      || line == null || !("mode" in line)
      || line.mode != "rail" || !("kind" in line) || line.kind != "freight"
      || !("lastProfit" in line) || line.lastProfit <= 0
      || !("vehicles" in line) || line.vehicles == null
      || line.vehicles.len() != 1 || !("trains" in line) || line.trains != 1
      || (("doubleTrack" in line) && line.doubleTrack != 0)
      || !("depot" in line) || line.depot == null
      || !AIRail.IsRailDepotTile(line.depot)
      || !("platformA" in line) || !("platformB" in line)
      || !("stationA" in line) || !("stationB" in line)
      || !("distance" in line) || line.distance <= 0) {
    OpexDoubleGrowV2BuildLog(line, "begin", "INVALID_ADMISSION");
    return false;
  }
  local oldType = AIRail.GetCurrentRailType();
  local requiredType = AIRail.GetRailType(line.depot);
  AIRail.SetCurrentRailType(requiredType);
  if (AIRail.GetCurrentRailType() != requiredType) {
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2BuildLog(line, "begin", "RAIL_TYPE", -1, owner);
    return false;
  }
  local route = OpexDoubleGrowPrimaryRoute(line);
  if (route == null || !OpexDoubleGrowVerifyRoute(route,
                                                  line.platformA, line.platformB)) {
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2BuildLog(line, "begin", "PRIMARY_ROUTE", -1, owner, route);
    return false;
  }
  local prep = OpexDoubleGrowV2Prepare(line, route);
  if (prep == null) {
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2BuildLog(line, "begin", "SITE_OR_PROTECTION_REJECT",
        -1, owner, route);
    return false;
  }
  local finder = OpexCreateRailPathfinder(prep.eligibleA, prep.eligibleB,
      prep.ignored, OpexRailAstarWeight(line.distance));
  AIRail.SetCurrentRailType(oldType);
  if (finder == null) {
    OpexDoubleGrowV2BuildLog(line, "begin", "PATHFINDER_UNAVAILABLE",
        -1, owner, route);
    return false;
  }
  prep.owner <- owner;
  prep.railType <- requiredType;
  prep.pathfinder <- finder;
  prep.spent <- 0;
  prep.budget <- 6000;
  owner._doubleGrowV2State = prep;
  OpexDoubleGrowV2BuildLog(line, "begin", "ASTAR_PENDING");
  return true;
}

/* Annulation sans effet de bord : la recherche ne pose rien. */
function OpexDoubleGrowV2Cancel(owner)
{
  if (owner == null || owner._doubleGrowV2State == null) return false;
  if (owner._doubleGrowV2State.owner != owner) return false;
  local line = owner._doubleGrowV2State.line;
  local route = owner._doubleGrowV2State.route;
  owner._doubleGrowV2State = null;
  OpexDoubleGrowV2BuildLog(line, "search", "PREEMPTED",
      -1, owner, route);
  return true;
}

/* Un appel = une tranche de 300 iterations au maximum. Les autres projets
 * priment ; un changement de priorite detruit seulement le pathfinder. */
function OpexDoubleGrowV2Continue(owner)
{
  if (owner == null || owner._doubleGrowV2State == null)
    return { status = "idle", reason = "NO_SEARCH" };
  local state = owner._doubleGrowV2State;
  if (state.owner != owner || !DOUBLE_GROW_V2) {
    OpexDoubleGrowV2Cancel(owner);
    return { status = "rejected", reason = "PRIMARY_PREEMPTION" };
  }
  /* Priorite au chantier principal : une recherche secondaire suspendue
   * garde son pathfinder et son budget, sans rien construire. */
  if (owner._railSearch != null || owner._activeWorker != null
      || owner._railExpansion != null || owner._v257Pending != null
      || owner._v271Pending != null || owner._railLongV2Pending != null
      || OpexV284Busy(owner))
    return { status = "pending", reason = "PRIMARY_BUSY" };
  local oldType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(state.railType);
  if (AIRail.GetCurrentRailType() != state.railType) {
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2Cancel(owner);
    return { status = "rejected", reason = "RAIL_TYPE" };
  }
  local result = OpexAdvanceRailPathfinder(state.pathfinder,
      state.spent, state.budget, AIController.GetTick() + 250, 300);
  state.spent = result.iterations;
  AIRail.SetCurrentRailType(oldType);
  if (!result.done) return { status = "pending", reason = "ASTAR_CONT" };
  owner._doubleGrowV2State = null;
  if (result.path == null || result.path == false) {
    OpexDoubleGrowV2BuildLog(state.line, "astar", "SEARCH_" + result.stop,
        -1, owner, state.route);
    return { status = "rejected", reason = "ASTAR_" + result.stop };
  }
  AIRail.SetCurrentRailType(state.railType);
  local plan = OpexDoubleGrowV2Plan(state.line, state, result);
  AIRail.SetCurrentRailType(oldType);
  if (plan == null) return { status = "rejected", reason = "GEOMETRY" };
  if (!OpexDoubleGrowV2Build(owner, state.line, plan))
    return { status = "rejected", reason = "PHYSICAL_BUILD" };
  return { status = "built", reason = "DIRECTIONAL_CERTIFIED" };
}

/* Fige le devis et revalide le trace AVANT toute construction. Aucun
 * terrassement n'est autorise sur une emprise preexistante. Le verificateur
 * V190 ne constitue qu'une condition necessaire : la boucle n'est adoptee
 * qu'apres certification FIX2 de sa seconde rame. */
function OpexDoubleGrowV2Build(owner, line, plan)
{
  if (!DOUBLE_GROW_V2 || !MODE_RAIL || !SAVE_FULL_STATE || owner == null
      || owner._catalog == null || line == null || !("lineId" in line)
      || !("kind" in line) || line.kind != "freight"
      || !("mode" in line) || line.mode != "rail"
      || !("lastProfit" in line) || line.lastProfit <= 0
      || !("vehicles" in line) || line.vehicles == null
      || line.vehicles.len() != 1 || !("trains" in line) || line.trains != 1
      || (("doubleTrack" in line) && line.doubleTrack != 0)
      || (("v271Tandem" in line) && line.v271Tandem)
      || (("scrapping" in line) && line.scrapping)
      || !("depot" in line) || !AIRail.IsRailDepotTile(line.depot)
      || !("stationA" in line) || !("stationB" in line)
      || !("platformA" in line) || !("platformB" in line)
      || !("platformLength" in line) || line.platformLength < 2
      || !("cargo" in line) || !("loco" in line) || !("wagons" in line)
      || !AIVehicle.IsValidVehicle(line.vehicles[0])) {
    OpexDoubleGrowV2BuildLog(line, "check", "INVALID_INPUT");
    return false;
  }

  local oldType = AIRail.GetCurrentRailType();
  local requiredType = AIRail.GetRailType(line.depot);
  AIRail.SetCurrentRailType(requiredType);
  if (AIRail.GetCurrentRailType() != requiredType) {
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2BuildLog(line, "check", "RAIL_TYPE", -1, owner,
        plan != null ? plan.tiles2 : null);
    return false;
  }
  local route = plan != null ? plan.tiles1 : null;
  if (route == null || !OpexDoubleGrowVerifyRoute(route,
                                                  line.platformA, line.platformB)) {
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2BuildLog(line, "check", "PRIMARY_ROUTE", -1, owner,
        plan != null ? plan.tiles2 : null);
    return false;
  }
  local estimate = OpexDoubleGrowV2Quote(owner, line, plan.tiles2,
      plan.platformA2, plan.platformB2,
      ("nativeTrackCost" in plan) ? plan.nativeTrackCost : -1);
  if (estimate <= 0 || OpexAvailableCapital() < estimate + 50000
      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < estimate + 50000) {
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2BuildLog(line, "check", "CAPITAL", -1, owner,
        plan.tiles2, plan.platformA2, plan.platformB2,
        ("nativeTrackCost" in plan) ? plan.nativeTrackCost : -1);
    return false;
  }
  if (DECISION_LOG) OpexDecide("DOUBLE_GROW", "version=2 phase=quote"
      + " line=" + line.lineId + " infrastructure_train=" + estimate
      + " reserve=50000 total=" + (estimate + 50000)
      + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
      + " available=" + OpexAvailableCapital()
      + " native_track=" + (("nativeTrackCost" in plan) ? plan.nativeTrackCost : -1));

  OpexAir0310InvalidateSiteValidity();
  local built = AIRail.BuildRailStation(plan.platformA2.anchor,
      plan.platformA2.direction, 1, plan.platformA2.length, plan.stationIdA);
  if (!built) {
    OpexDoubleGrowV2BuildLog(line, "station", "STATION_A_NATIVE_ERR_"
        + AIError.GetLastError(), plan.platformA2.anchor, owner,
        plan.tiles2, plan.platformA2, plan.platformB2, plan.nativeTrackCost);
  } else if (AIStation.GetStationID(plan.platformA2.anchor) != plan.stationIdA) {
    built = false;
    OpexDoubleGrowV2BuildLog(line, "station", "STATION_A_WRONG_ID",
        plan.platformA2.anchor, owner, plan.tiles2, plan.platformA2,
        plan.platformB2, plan.nativeTrackCost);
  }
  if (built) {
    built = AIRail.BuildRailStation(plan.platformB2.anchor,
        plan.platformB2.direction, 1, plan.platformB2.length, plan.stationIdB);
    if (!built) {
      OpexDoubleGrowV2BuildLog(line, "station", "STATION_B_NATIVE_ERR_"
          + AIError.GetLastError(), plan.platformB2.anchor, owner,
          plan.tiles2, plan.platformA2, plan.platformB2, plan.nativeTrackCost);
    } else if (AIStation.GetStationID(plan.platformB2.anchor) != plan.stationIdB) {
      built = false;
      OpexDoubleGrowV2BuildLog(line, "station", "STATION_B_WRONG_ID",
          plan.platformB2.anchor, owner, plan.tiles2, plan.platformA2,
          plan.platformB2, plan.nativeTrackCost);
    }
  }
  if (built && !OpexDoubleGrowBuildTrack(plan)) {
    built = false;
    OpexDoubleGrowV2BuildLog(line, "track", "TRACK_BUILD_FAILED", -1,
        owner, plan.tiles2, plan.platformA2, plan.platformB2, plan.nativeTrackCost);
  }

  if (built) {
    local forbiddenDepot = clone plan.forbidden;
    foreach (tile in plan.tiles2) forbiddenDepot[tile] <- true;
    foreach (pad in [plan.platformA2, plan.platformB2]) {
      for (local i = 0; i < pad.length; i++)
        forbiddenDepot[pad.anchor + i * pad.step] <- true;
      forbiddenDepot[pad.lead] <- true;
    }
    local midpoint = plan.tiles2.len() / 2;
    local inner = [];
    for (local i = max(2, midpoint - 8);
         i <= min(plan.tiles2.len() - 3, midpoint + 8); i++)
      inner.append(plan.tiles2[i]);
    if (inner.len() >= 3) plan.depot2 = OpexBuildDepot(inner, forbiddenDepot);
    built = plan.depot2 != null && AIRail.IsRailDepotTile(plan.depot2)
        && plan.depot2 != line.depot
        && OpexDoubleGrowVerifyRoute(route, line.platformA, line.platformB)
        && OpexDoubleGrowVerifyRoute(plan.tiles2, plan.platformA2,
                                     plan.platformB2);
  }

  local staged = null;
  if (built) {
    staged = clone line;
    staged.rawset("tiles1", route);
    staged.rawset("tiles2", plan.tiles2);
    staged.rawset("platformA2", plan.platformA2);
    staged.rawset("platformB2", plan.platformB2);
    staged.rawset("stationA2", plan.platformA2.station_exit);
    staged.rawset("stationB2", plan.platformB2.station_exit);
    staged.rawset("depot2", plan.depot2);
    staged.rawset("doubleTrack", 1);
    staged.rawset("vehicles", [line.vehicles[0]]);
    /* Controle V190 de separation physique avant tout changement d'ordres.
     * FIX2 ne sera appelle que par la finalisation de flotte. */
    built = OpexV190VerifyIndependentDouble(staged, line.depot, plan.depot2)
        && OpexDoubleGrowFleetFinalize(owner, line, staged);
  }
  if (!built) {
    local rollback = OpexDoubleGrowRollbackGeometry(plan);
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowV2BuildLog(line, "rollback",
        rollback ? "DIRECTIONAL_OR_BUILD" : "ROLLBACK_FAILED",
        -1, owner, plan.tiles2, plan.platformA2, plan.platformB2,
        plan.nativeTrackCost);
    return false;
  }

  /* La finalisation FIX2 a certifie la circulation directionnelle, avec
   * deux rames enregistrees. Ne pas ajouter un controle qui imposerait un
   * rollback de la voie 2 APRES la pose des aiguillages primaires. */
  line.rawset("tiles1", route);
  line.rawset("tiles2", plan.tiles2);
  line.rawset("platformA2", plan.platformA2);
  line.rawset("platformB2", plan.platformB2);
  line.rawset("stationA2", plan.platformA2.station_exit);
  line.rawset("stationB2", plan.platformB2.station_exit);
  line.rawset("depot2", plan.depot2);
  line.rawset("vehicles", staged.vehicles);
  line.rawset("doubleTrack", 1);
  line.rawset("trains", staged.vehicles.len());
  line.rawset("vehCount", staged.vehicles.len());
  line.rawset("v190Independent", false);
  line.rawset("v190Directional", true);
  line.rawset("v181Loop", true);
  line.rawset("doubleGrowDirectional", true);
  line.rawset("doubleGrowNextDate", AIDate.GetCurrentDate() + 90);
  owner._saveProjection = null;
  OpexAir0310InvalidateSiteValidity();
  AIRail.SetCurrentRailType(oldType);
  OpexDoubleGrowV2BuildLog(line, "commit", "DIRECTIONAL_CERTIFIED");
  return true;
}
