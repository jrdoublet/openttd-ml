/* RAIL-PAIR : plans de quai/raccord V271b (9403c73), trace sure V284. */
V271_LAST_GEOMETRY_ISSUE <- "";
V271_LAST_TRACE_ISSUE <- "";
V271_LAST_TRACE_DETAIL <- "";

/* Repli strict pour les gares B ayant plusieurs tuiles jointes au meme ID.
 * V284 refuse une bifurcation vers un autre quai de B, meme lorsque notre
 * sortie B est identifiee et que tous les autres choix terminent dans B.
 * Les aiguillages vers une VRAIE voie restent interdits. Le detail de refus
 * rend observables les ponts, tunnels, depots et sorties de gare ambiguës. */
function OpexV271TraceJoinedDestination(start, lead, target)
{
  local visited = {};
  local route = [start, lead];
  local previous = start;
  local current = lead;
  local targetId = AIStation.GetStationID(target);
  local company = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local offsets = [1, -1, AIMap.GetMapSizeX(), -AIMap.GetMapSizeX()];
  for (local step = 0; step < 2000; step++) {
    if (current == target) return route;
    if (current in visited) { V271_LAST_TRACE_ISSUE = "cycle"; return null; }
    visited.rawset(current, true);
    if (AITile.GetOwner(current) != company) {
      V271_LAST_TRACE_ISSUE = "foreign_tile"; return null;
    }
    local next = null;
    if (AIBridge.IsBridgeTile(current) || AITunnel.IsTunnelTile(current)) {
      local bridge = AIBridge.IsBridgeTile(current);
      local other = bridge ? AIBridge.GetOtherBridgeEnd(current) : AITunnel.GetOtherTunnelEnd(current);
      if (!AIMap.IsValidTile(other)) { V271_LAST_TRACE_ISSUE = "structure_end"; return null; }
      local span = AIMap.DistanceManhattan(current, other);
      if (span <= 1) { V271_LAST_TRACE_ISSUE = "structure_span"; return null; }
      local direction = (other - current) / span;
      if (AIMap.DistanceManhattan(previous, current) == 1) {
        if (previous != current - direction) {
          V271_LAST_TRACE_ISSUE = "structure_axis_entry"; return null;
        }
        next = other;
      } else {
        if (previous != other) { V271_LAST_TRACE_ISSUE = "structure_axis_exit"; return null; }
        next = current - direction;
        if (!AIMap.IsValidTile(next)) {
          V271_LAST_TRACE_ISSUE = "structure_exit_invalid"; return null;
        }
        /* AIRail.IsRailTile exclut les tuiles de gare et les tetes
         * d'ouvrages. Autoriser la sortie directement sur NOTRE quai B,
         * et sur une autre tete de structure sur le meme axe. */
        if (!AIRail.IsRailTile(next) && !(next == target && AIRail.IsRailStationTile(next))
            && !AIBridge.IsBridgeTile(next) && !AITunnel.IsTunnelTile(next)) {
          V271_LAST_TRACE_ISSUE = "structure_exit_rail";
          V271_LAST_TRACE_DETAIL = "current=" + current + " other=" + other + " next=" + next
              + " target=" + target + " station=" + (AIRail.IsRailStationTile(next) ? 1 : 0)
              + " depot=" + (AIRail.IsRailDepotTile(next) ? 1 : 0)
              + " owner=" + AITile.GetOwner(next);
          return null;
        }
      }
    } else {
      foreach (offset in offsets) {
        local tile = current + offset;
        if (!AIMap.IsValidTile(tile) || AIMap.DistanceManhattan(current, tile) != 1
            || tile == previous || AIRail.IsRailDepotTile(tile)) continue;
        if (!AIRail.IsRailTile(tile) && !AIBridge.IsBridgeTile(tile)
            && !AITunnel.IsTunnelTile(tile)) continue;
        if (!AIRail.AreTilesConnected(previous, current, tile)) continue;
        /* Les autres quais d'une meme gare B ne menent pas vers une autre
         * ligne : ils ne doivent pas rendre ambigu le chemin vers NOTRE B. */
        if (tile != target && AIRail.IsRailStationTile(tile)
            && AIStation.GetStationID(tile) == targetId) continue;
        if (next != null) { V271_LAST_TRACE_ISSUE = "junction"; return null; }
        next = tile;
      }
    }
    if (next == null) { V271_LAST_TRACE_ISSUE = "dead_end"; return null; }
    previous = current;
    current = next;
    route.append(current);
  }
  V271_LAST_TRACE_ISSUE = "length_limit";
  return null;
}

/* Reutiliser le traceur V284 : un ouvrage doit etre traverse dans son axe,
 * toute ambiguite/branche/cycle retourne null et seule la destination exacte
 * est acceptee. Le traceur V271b historique pouvait retourner un prefixe. */
function OpexV271TraceTrackTiles(startStationTile, leadTile, endStationTile, crossStructures = false)
{
  V271_LAST_TRACE_ISSUE = "invalid_start";
  V271_LAST_TRACE_DETAIL = "";
  if (!AIMap.IsValidTile(startStationTile) || !AIMap.IsValidTile(leadTile)
      || !AIMap.IsValidTile(endStationTile)
      || (!AIRail.IsRailTile(leadTile) && !AIBridge.IsBridgeTile(leadTile)
          && !AITunnel.IsTunnelTile(leadTile))
      || AIMap.DistanceManhattan(startStationTile, leadTile) != 1) return null;
  local route = OpexV284Trace({ stationA = startStationTile, stationB = endStationTile,
      platformA = { station_exit = startStationTile, lead = leadTile } });
  if (route == null || route.len() < 3 || route[route.len() - 1] != endStationTile) {
    V271_LAST_TRACE_ISSUE = "v284_strict";
    route = OpexV271TraceJoinedDestination(startStationTile, leadTile, endStationTile);
  }
  if (route == null || route.len() < 3 || route[route.len() - 1] != endStationTile) return null;
  if (!crossStructures) foreach (tile in route)
    if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) {
      V271_LAST_TRACE_ISSUE = "structure_not_allowed"; return null;
    }
  V271_LAST_TRACE_ISSUE = "";
  return route;
}

function OpexV271PlatformPlan(line)
{
  local original = line.platformA;
  V271_LAST_GEOMETRY_ISSUE = "lead";
  if (AIMap.DistanceManhattan(original.lead, original.station_exit) != 1) return null;
  local target = line.platformB.station_exit;
  if (AIStation.GetStationID(target) != AIStation.GetStationID(line.stationB)) return null;
  local route = OpexV271TraceTrackTiles(original.station_exit, original.lead, target, true);
  if (route == null || route[route.len() - 1] != target) {
    V271_LAST_GEOMETRY_ISSUE = "trace_or_end"; return null;
  }
  local merges = {};
  local signalIndex = -1;
  for (local i = 1; i <= 12 && i + 1 < route.len(); i++) {
    local tile = route[i];
    /* Le PBS source doit etre pose AVANT le premier pont/tunnel. Sinon une
     * rame pourrait entrer dans l'ouvrage avant la reservation du canton. */
    if (signalIndex < 0 && (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile))) {
      V271_LAST_GEOMETRY_ISSUE = "front_structure_before_signal";
      return null;
    }
    local straight = AIRail.IsRailTile(tile) && !AIRail.IsRailStationTile(tile) &&
        !AIRail.IsRailDepotTile(tile) && !AIBridge.IsBridgeTile(tile) && !AITunnel.IsTunnelTile(tile) &&
        OpexTileTrackCount(tile) == 1 && AIMap.DistanceManhattan(route[i - 1], tile) == 1 &&
        AIMap.DistanceManhattan(tile, route[i + 1]) == 1 &&
        tile - route[i - 1] == route[i + 1] - tile &&
        AIRail.AreTilesConnected(route[i - 1], tile, route[i + 1]);
    if (!straight) continue;
    if (signalIndex >= 0) merges[tile] <- { next = route[i + 1],
        after = i + 2 < route.len() ? route[i + 2] : null,
        signalTile = route[signalIndex], signalFront = route[signalIndex - 1] };
    /* Premier emplacement droit : reste strictement AVANT tous les merges. */
    if (signalIndex < 0) signalIndex = i;
  }
  if (signalIndex < 0) { V271_LAST_GEOMETRY_ISSUE = "no_primary_signal"; return null; }
  if (merges.len() == 0) { V271_LAST_GEOMETRY_ISSUE = "no_merge_tile"; return null; }
  V271_LAST_GEOMETRY_ISSUE = "no_adjacent_platform";
  foreach (plan in OpexV190FindParallelPlatformPlans(original, true, 2)) {
    V271_LAST_GEOMETRY_ISSUE = "path";
    local path = OpexV271ConnectionPath(plan, merges);
    if (path == null) continue;
    local merge = merges[path[path.len() - 2]];
    return { platform = plan, tiles = path,
        signalTile = merge.signalTile, signalFront = merge.signalFront };
  }
  return null;
}

function OpexV271ConnectionPath(plan, merges)
{
  local d = plan.lead - plan.station_exit;
  local queue = OpexBinaryHeapV90(); // deja charge pour les raccords rail
  queue.Insert([plan.station_exit, plan.lead], 0);
  local queued = 1;
  local seen = {};
  local offsets = [1, -1, AIMap.GetTileIndex(0, 1), -AIMap.GetTileIndex(0, 1)];
  local shield = AIAccounting();
  local testMode = AITestMode();
  for (local head = 0; queue.Count() > 0 && head < 256; head++) {
    local path = queue.Pop();
    local n = path.len();
    local cur = path[n - 1];
    local prev = path[n - 2];
    foreach (offset in offsets) {
      /* PBS secondaire sur le lead droit, jamais sur une courbe. */
      if (n == 2 && offset != d) continue;
      local next = cur + offset;
      if (!AIMap.IsValidTile(next) || AIMap.DistanceManhattan(cur, next) != 1 ||
          OpexWaterContains(path, next)) continue;
      /* Deux courbes de meme sens consecutives = virage a 90 degres. */
      if (n >= 3 && offset == path[n - 3] - prev) continue;
      local joining = next in merges;
      if (!joining && (!AITile.IsBuildable(next) || AIRail.IsRailTile(next) ||
          AIBridge.IsBridgeTile(next) || AITunnel.IsTunnelTile(next))) continue;
      /* Ne jamais traverser ni longer dans le quai en construction. */
      local inPlatform = false;
      for (local i = 0; i < plan.length; i++) {
        if (next == plan.anchor + i * plan.step) inPlatform = true;
      }
      if (inPlatform) continue;
      if (!AIRail.BuildRail(prev, cur, next)) continue;
      if (joining) {
        local goal = merges[next];
        if (goal.next == cur || goal.next - next == prev - cur ||
            OpexWaterContains(path, goal.next)) continue;
        // Inclure la premiere courbe existante apres le merge dans le test 90.
        if (goal.after != null && goal.after - goal.next == cur - next) continue;
        if (!AIRail.BuildRail(cur, next, goal.next)) {
          V271_LAST_GEOMETRY_ISSUE = "test_build"; continue;
        }
        local result = clone path;
        result.append(next);
        result.append(goal.next);
        return result;
      }
      if (n >= 17 || queued >= 256) continue;
      local key = cur + ":" + next + ":" + (cur - prev);
      if (key in seen) continue;
      seen[key] <- true;
      local extended = clone path;
      extended.append(next);
      local distance = 1000000;
      foreach (tile, goal in merges) distance = min(distance, AIMap.DistanceManhattan(next, tile));
      // Priorite geometrique, sans promesse de plus court chemin exhaustif.
      queue.Insert(extended, n + 2 * distance);
      queued++;
    }
  }
  return null;
}

function OpexV271IsolatedRoute(line)
{
  return OpexV271RouteIssue(line) == "";
}

function OpexV271RouteIssue(line)
{
  local target = line.platformB.station_exit;
  if (AIStation.GetStationID(target) != AIStation.GetStationID(line.stationB)) return "target_station_changed";
  local route = OpexV271TraceTrackTiles(line.platformA.station_exit, line.platformA.lead,
      target, true);
  if (route == null) return "trace_" + V271_LAST_TRACE_ISSUE;
  if (route[route.len() - 1] != target) return "trace_end";
  local offsets = [1, -1, AIMap.GetTileIndex(0, 1), -AIMap.GetTileIndex(0, 1)];
  for (local i = 1; i + 1 < route.len(); i++) {
    local tile = route[i];
    if (AIRail.IsRailStationTile(tile)) return "station_on_route";
    /* Sur les tetes de pont/tunnel, GetSignalType n'a pas le sens d'un
     * signal de voie ordinaire. OpexV271TraceTrackTiles a deja valide
     * l'ouvrage, ses deux extremites et la continuite dans son axe. */
    if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) continue;
    foreach (offset in offsets) {
      local neighbor = tile + offset;
      if (!AIMap.IsValidTile(neighbor) || AIMap.DistanceManhattan(tile, neighbor) != 1) continue;
      if (AIRail.GetSignalType(tile, neighbor) != AIRail.SIGNALTYPE_NONE) return "signal";
      if (neighbor != line.depot && AIRail.IsRailDepotTile(neighbor)) return "other_depot";
      if (AIMap.DistanceManhattan(route[i - 1], tile) != 1 ||
          neighbor == route[i - 1] || neighbor == route[i + 1] || neighbor == line.depot) continue;
      if (AIRail.IsRailTile(neighbor) && AIRail.AreTilesConnected(route[i - 1], tile, neighbor)) return "branch";
    }
  }
  return "";
}

function OpexV271RestoreTracks(snapshots)
{
  local ok = true;
  local bits = [AIRail.RAILTRACK_NE_SW, AIRail.RAILTRACK_NW_SE, AIRail.RAILTRACK_NW_NE,
                AIRail.RAILTRACK_SW_SE, AIRail.RAILTRACK_NW_SW, AIRail.RAILTRACK_NE_SE];
  foreach (snapshot in snapshots) {
    if (!AIRail.IsRailTile(snapshot.tile) || AIRail.IsRailStationTile(snapshot.tile)) continue;
    /* Seulement les bits confirmes comme ajoutes par cette transaction.
     * Un Save entre pose et capture laisse au pire une piece orpheline ;
     * jamais de suppression d'un rail pose entre-temps par une autre tache. */
    local added = ("added" in snapshot) ? (AIRail.GetRailTracks(snapshot.tile) & snapshot.added) : 0;
    foreach (bit in bits) {
      if ((added & bit) != 0 && !AIRail.RemoveRailTrack(snapshot.tile, bit)) ok = false;
    }
  }
  return ok;
}
