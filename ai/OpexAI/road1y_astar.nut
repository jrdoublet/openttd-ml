/* ROAD1Y-K : A* routier léger pour les paires de bus site-first.
 *
 * Constat du 02/11 (3 graines, 3 ans, route seule) : les candidats bus de
 * 96 à 192 tuiles sont les plus nombreux et les mieux estimés (profit médian
 * 6-10 k£ contre 4-5 k£ sous 64), mais AUCUN n'est construit au-delà de 128 :
 * tous meurent en TRACEX, faute de voirie continue (BFS) et de L constructible.
 * AAA trace ces liaisons avec un vrai pathfinder.
 *
 * Ce solveur ne pose aucune AITestMode par voisin (coût mesuré de ROAD100-16) :
 * il explore sur des prédicats de tuile bon marché, puis valide le tracé complet
 * arête par arête avec OpexRoadTraceBuildable. Une arête refusée est bannie et la
 * recherche relancée, au plus ROAD1Y_ASTAR_RETRIES fois, dans le même budget de
 * nœuds. Appelé uniquement à la construction (paires road1yBusSite), jamais dans
 * un try ; il peut donc durer plusieurs ticks sans risque. */

ROAD1Y_ASTAR_RETRIES <- 3;

function OpexRoad1yAStarTileOk(tile, banned)
{
  if (!AIMap.IsValidTile(tile)) return false;
  if (tile in banned) return false;
  if (AITile.IsWaterTile(tile) || AITile.IsStationTile(tile)) return false;
  if (AIRail.IsRailTile(tile) || AIRoad.IsRoadDepotTile(tile)) return false;
  if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) return false;
  return AIRoad.IsRoadTile(tile) || AITile.IsBuildable(tile);
}

/* Pente admise : plate, ou inclinée dans l'axe du déplacement (sans virage). */
function OpexRoad1yAStarSlopeOk(tile, alongX)
{
  local s = AITile.GetSlope(tile);
  if (s == AITile.SLOPE_FLAT) return 0;
  if (alongX && (s == AITile.SLOPE_NE || s == AITile.SLOPE_SW)) return 1;
  if (!alongX && (s == AITile.SLOPE_NW || s == AITile.SLOPE_SE)) return 1;
  return -1;
}

/* Rampes de pont admises : tuile plate ou dont la pente monte vers le pont selon d. */
function OpexRoad1yBridgeRampOk(tile, d, stepX)
{
  local s = AITile.GetSlope(tile);
  if (s == AITile.SLOPE_FLAT) return true;
  if (d == stepX) return s == AITile.SLOPE_SW;
  if (d == -stepX) return s == AITile.SLOPE_NE;
  local stepY = AIMap.GetTileIndex(0, 1);
  if (d == stepY) return s == AITile.SLOPE_SE;
  if (d == -stepY) return s == AITile.SLOPE_NW;
  return false;
}

function OpexRoad1yBridgeSortPrice(a, b)
{
  if (a.price < b.price) return -1;
  if (a.price > b.price) return 1;
  return 0;
}

/* Une recherche : renvoie la liste d'arêtes {from,to} de src à dst ou null.
 * budget.nodes est décrémenté par nœud développé. */
function OpexRoad1yAStarSearch(src, srcFront, dst, dstFront, banned, budget, maxLen)
{
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  local stepX = AIMap.GetTileIndex(1, 0);
  local came = {};
  local inDir = {};
  local isBridge = {};
  local gScore = {};
  local closed = {};
  local heap = OpexBinaryHeapV90();
  came.rawset(src, src);
  gScore.rawset(src, 0);
  heap.Insert(src, 2 * AIMap.DistanceManhattan(src, dst));
  while (heap.Count() > 0) {
    local cur = heap.Pop();
    if (cur in closed) continue;
    closed.rawset(cur, true);
    if (cur == dst) {
      local edges = [];
      local t = dst;
      while (t != src) {
        local p = came[t];
        if ((t in isBridge) && isBridge[t] > 0) {
          edges.insert(0, { from = p, to = t, len = isBridge[t], bridge = true });
        } else {
          edges.insert(0, { from = p, to = t });
        }
        t = p;
      }
      return edges;
    }
    budget.nodes--;
    if (budget.nodes <= 0) return null;
    local g = gScore[cur];
    local prev = came[cur];
    local curFlat = AITile.GetSlope(cur) == AITile.SLOPE_FLAT;
    foreach (d in dirs) {
      local nxt = cur + d;
      if (nxt == prev || (nxt in closed)) continue;
      /* Sortie et entrée des arrêts traversants sur leur axe. */
      if (cur == src && !OpexRoadOnDtAxis(src, srcFront, nxt)) continue;
      if (nxt == dst && !OpexRoadOnDtAxis(dst, dstFront, cur)) continue;
      if (nxt == src) continue;
      local alongX = (d == stepX || d == -stepX);

      // --- Normal road step ---
      local canRoad = false;
      local roadCost = 0;
      if (nxt == dst) {
        canRoad = true;
        roadCost = 1;
      } else if (OpexRoad1yAStarTileOk(nxt, banned)) {
        if (AIRoad.AreRoadTilesConnected(cur, nxt)) {
          canRoad = true;
          roadCost = 1;
        } else {
          local slope = OpexRoad1yAStarSlopeOk(nxt, alongX);
          if (slope >= 0) {
            canRoad = true;
            roadCost = (AIRoad.IsRoadTile(nxt) ? 2 : 3) + 2 * slope;
          }
        }
      }

      if (canRoad) {
        local cost = roadCost;
        if (cur != src && (cur in inDir) && d != inDir[cur]) {
          if (!curFlat) cost = -1;
          else cost += 1;
        }
        if (cost >= 0) {
          local ng = g + cost;
          if (!(nxt in gScore) || ng < gScore[nxt]) {
            if (ng <= 3 * maxLen) {
              gScore.rawset(nxt, ng);
              came.rawset(nxt, cur);
              inDir.rawset(nxt, d);
              isBridge.rawset(nxt, 0);
              heap.Insert(nxt, ng + 2 * AIMap.DistanceManhattan(nxt, dst));
            }
          }
        }
      }

      // --- Bridge jump neighbor ---
      if (ROAD1Y_BRIDGE > 0 && cur != src && !AITile.IsStationTile(cur) && OpexRoad1yBridgeRampOk(cur, d, stepX)) {
        local nxt1 = cur + d;
        if (AIMap.IsValidTile(nxt1) && (AITile.IsWaterTile(nxt1) || AIRail.IsRailTile(nxt1))) {
          local canEnterBridge = true;
          local bridgeTurnCost = 0;
          if (cur != src && (cur in inDir) && d != inDir[cur]) {
            if (!curFlat) canEnterBridge = false;
            else bridgeTurnCost = 1;
          }
          if (canEnterBridge) {
            for (local k = 2; k <= ROAD1Y_BRIDGE + 1; k++) {
              local mid = cur + (k - 1) * d;
              if (!AIMap.IsValidTile(mid)) break;
              if (!AITile.IsWaterTile(mid) && !AIRail.IsRailTile(mid)) break;
              local target = cur + k * d;
              if (!AIMap.IsValidTile(target)) break;
              if (AITile.IsWaterTile(target) || AIRail.IsRailTile(target)) continue;
              if (!(target in closed) && target != src && target != dst && !AITile.IsStationTile(target)
                  && OpexRoad1yAStarTileOk(target, banned)
                  && OpexRoad1yBridgeRampOk(target, -d, stepX)) {
                local bCost = 4 * k + 6 + bridgeTurnCost;
                local ng = g + bCost;
                if (!(target in gScore) || ng < gScore[target]) {
                  if (ng <= 3 * maxLen) {
                    gScore.rawset(target, ng);
                    came.rawset(target, cur);
                    inDir.rawset(target, d);
                    isBridge.rawset(target, k);
                    heap.Insert(target, ng + 2 * AIMap.DistanceManhattan(target, dst));
                  }
                }
              }
              break;
            }
          }
        }
      }
    }
  }
  return null;
}

/* Tracé validé arête par arête, avec bannissement et relance. */
function OpexRoad1yAStarTrace(siteA, siteB, maxLen)
{
  local nodeBudget = ROAD1Y_ASTAR * 1000;
  local dist = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
  if (ROAD1Y_FAR > 0 && dist > 128) {
    nodeBudget = (nodeBudget * dist) / 128;
  }
  local budget = { nodes = nodeBudget };
  local banned = {};
  local tries = 0;
  local reason = "BUDGET";
  while (tries <= ROAD1Y_ASTAR_RETRIES && budget.nodes > 0) {
    tries++;
    local trace = OpexRoad1yAStarSearch(siteA.tile, siteA.front, siteB.tile, siteB.front,
                                        banned, budget, maxLen);
    if (trace == null) { reason = budget.nodes > 0 ? "NO_PATH" : "BUDGET"; break; }
    if (trace.len() > maxLen) { reason = "LONG"; break; }
    local bad = null;
    foreach (edge in trace) {
      if (("bridge" in edge) && edge.bridge) {
        local bridgeList = AIBridgeList_Length(edge.len + 1);
        local cands = [];
        foreach (bridgeId, _ in bridgeList) {
          local price = AIBridge.GetPrice(bridgeId, edge.len + 1);
          if (price >= 0) cands.append({ id = bridgeId, price = price });
        }
        cands.sort(OpexRoad1yBridgeSortPrice);
        local chosenId = -1;
        local chosenPrice = -1;
        foreach (c in cands) {
          local ok = false;
          {
            local test = AITestMode();
            ok = AIBridge.BuildBridge(AIVehicle.VT_ROAD, c.id, edge.from, edge.to);
          }
          if (ok) {
            chosenId = c.id;
            chosenPrice = c.price;
            break;
          }
        }
        if (chosenId < 0) { bad = edge; break; }
        edge.id <- chosenId;
        edge.price <- chosenPrice;
        continue;
      }
      if (AIRoad.AreRoadTilesConnected(edge.from, edge.to)) continue;
      local ok = false;
      { local test = AITestMode(); ok = AIRoad.BuildRoad(edge.from, edge.to); }
      if (!ok) { bad = edge; break; }
    }
    if (bad == null) {
      if (DECISION_LOG) {
        local nBridges = 0;
        local sumBridgeTiles = 0;
        foreach (e in trace) {
          if (("bridge" in e) && e.bridge) {
            nBridges++;
            sumBridgeTiles += e.len;
          }
        }
        OpexDecide("ROAD1Y_ASTAR", "ok=1 a=" + siteA.tile + " b=" + siteB.tile
            + " d=" + AIMap.DistanceManhattan(siteA.tile, siteB.tile) + " len=" + trace.len()
            + " bridges=" + nBridges + " bridgeTiles=" + sumBridgeTiles
            + " tries=" + tries + " left=" + budget.nodes);
      }
      return trace;
    }
    reason = "UNBUILDABLE";
    local victim = (bad.to != siteB.tile) ? bad.to : bad.from;
    if (victim == siteA.tile) break;
    banned.rawset(victim, true);
  }
  if (DECISION_LOG) OpexDecide("ROAD1Y_ASTAR", "ok=0 a=" + siteA.tile + " b=" + siteB.tile
      + " d=" + AIMap.DistanceManhattan(siteA.tile, siteB.tile) + " reason=" + reason
      + " tries=" + tries + " left=" + budget.nodes);
  return null;
}

/* Pose du tracé avec support des ponts ROAD1Y. */
function OpexRoadBuildTrace(trace, added)
{
  for (local i = 0; i < trace.len(); i++) {
    local edge = trace[i];
    if (("bridge" in edge) && edge.bridge) {
      local bridgeBuilt = false;
      if (AIBridge.IsBridgeTile(edge.from) && AIBridge.GetOtherBridgeEnd(edge.from) == edge.to) {
        bridgeBuilt = true;
      } else {
        local ok = AIBridge.BuildBridge(AIVehicle.VT_ROAD, edge.id, edge.from, edge.to);
        if (DECISION_LOG) OpexDecide("ROAD1Y_BRIDGE", "from=" + edge.from + " to=" + edge.to
            + " len=" + edge.len + " id=" + edge.id + " price=" + edge.price + " ok=" + (ok ? 1 : 0));
        if (!ok) return false;
        added.append({ from = edge.from, to = edge.to, bridge = true });
        bridgeBuilt = true;
      }
      if (i > 0) {
        local prevEdge = trace[i - 1];
        if (!("bridge" in prevEdge && prevEdge.bridge) && !AIRoad.AreRoadTilesConnected(prevEdge.from, edge.from)) {
          local okP = AIRoad.BuildRoad(prevEdge.from, edge.from);
          if (AIRoad.AreRoadTilesConnected(prevEdge.from, edge.from)) {
            if (okP) added.append({ from = prevEdge.from, to = edge.from });
          } else {
            return false;
          }
        }
      }
      if (i + 1 < trace.len()) {
        local nextEdge = trace[i + 1];
        if (!("bridge" in nextEdge && nextEdge.bridge) && !AIRoad.AreRoadTilesConnected(edge.to, nextEdge.to)) {
          local okN = AIRoad.BuildRoad(edge.to, nextEdge.to);
          if (AIRoad.AreRoadTilesConnected(edge.to, nextEdge.to)) {
            if (okN) added.append({ from = edge.to, to = nextEdge.to });
          } else {
            return false;
          }
        }
      }
      continue;
    }
    if (AIRoad.AreRoadTilesConnected(edge.from, edge.to)) continue;
    local ok = AIRoad.BuildRoad(edge.from, edge.to);
    local connected = AIRoad.AreRoadTilesConnected(edge.from, edge.to);
    if (!connected) return false;
    if (ok) added.append(edge);
  }
  return true;
}

OpexRoadOriginalRollback <- OpexRoadRollback;
function OpexRoadRollback(stopA, stopB, depot, vehicles, added, satellites = null)
{
  if (added != null) {
    for (local i = added.len() - 1; i >= 0; i--) {
      local edge = added[i];
      if (("bridge" in edge) && edge.bridge) {
        AIBridge.RemoveBridge(edge.from);
      }
    }
  }
  OpexRoadOriginalRollback(stopA, stopB, depot, vehicles, added, satellites);
}
