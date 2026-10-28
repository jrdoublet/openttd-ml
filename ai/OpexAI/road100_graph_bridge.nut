/* ROAD100 Graph Bridge (opt-in integration by caller, no settings/defaults here).
 *
 * Deterministic, bounded rolling bridge between two prequalified LONG bus
 * facades. This is intentionally NOT the sparse fixed-band V35 trace:
 *  - first follow only genuinely connected public roads (short sleeves);
 *  - then advance by short locally searched gaps, preferring existing bits;
 *  - return a CONTIGUOUS CANDIDATE edge trace, never a built connection.
 *
 * CRITICAL: neither this file nor its helpers issue BuildRoad, even in
 * AITestMode. A missing edge remains HYPOTHETICAL. The caller MUST pass
 * the returned trace through physical verification (same mechanics as
 * OpexRoad100LongVerifyTrace, GRAPH minimum length 43 rather than 80), the
 * depot/finance preflight, and finally the transactional OpexBuildRoadRoute.
 * In particular,
 * road bits on hypothetical neighbouring tiles cannot be assumed connected.
 *
 * Dependencies already provided by builder_road.nut: OpexRoadIsFlat,
 * OpexRoadOnDtAxis, OpexOpsMeasureBegin/End, OpexDecide and DECISION_LOG.
 * No monolithic A*, runtime construction or file mutations occur here.
 */

/* Only one cache per GRAPH attempt: no persistence across game months or
 * intervening road construction. A tile/edge is queried natively once.
 * All numeric keys stay well below Squirrel signed-int limits on game maps. */
function OpexRoad100GBCache()
{
  return { width = AIMap.GetMapSizeX(), height = AIMap.GetMapSizeY(),
      road = {}, occupied = {}, flat = {}, buildable = {}, edges = {},
      road_queries = 0, edge_queries = 0, cache_hits = 0 };
}

function OpexRoad100GBRoadTile(tile, cache)
{
  if (tile in cache.road) { cache.cache_hits++; return cache.road[tile]; }
  local answer = AIRoad.IsRoadTile(tile);
  cache.road.rawset(tile, answer);
  cache.road_queries++;
  return answer;
}

function OpexRoad100GBFlat(tile, cache)
{
  if (tile in cache.flat) return cache.flat[tile];
  local answer = OpexRoadIsFlat(tile);
  cache.flat.rawset(tile, answer);
  return answer;
}

function OpexRoad100GBBuildable(tile, cache)
{
  if (tile in cache.buildable) return cache.buildable[tile];
  local answer = AITile.IsBuildable(tile);
  cache.buildable.rawset(tile, answer);
  return answer;
}

function OpexRoad100GBRoadEdge(fromTile, toTile, cache = null)
{
  if (cache == null) cache = OpexRoad100GBCache();
  local width = cache.width;
  local diff = toTile - fromTile;
  local direction = diff == 1 ? 0 : diff == -1 ? 1 :
      diff == width ? 2 : diff == -width ? 3 : -1;
  if (direction < 0 || fromTile < 0 || toTile < 0 ||
      fromTile >= width * cache.height || toTile >= width * cache.height ||
      (diff == 1 && fromTile % width == width - 1) ||
      (diff == -1 && fromTile % width == 0)) return false;
  local key = fromTile * 4 + direction;
  if (key in cache.edges) { cache.cache_hits++; return cache.edges[key]; }
  local connected = OpexRoad100GBRoadTile(fromTile, cache) &&
      OpexRoad100GBRoadTile(toTile, cache) &&
      AIRoad.AreRoadTilesConnected(fromTile, toTile) &&
      AIRoad.AreRoadTilesConnected(toTile, fromTile);
  cache.edges.rawset(key, connected);
  /* The predicate requires BOTH directions, so reverse is identical. */
  local reverse = direction % 2 == 0 ? direction + 1 : direction - 1;
  cache.edges.rawset(toTile * 4 + reverse, connected);
  cache.edge_queries++;
  return connected;
}

function OpexRoad100GBOccupied(tile, stopA, stopB, cache = null)
{
  /* Endpoints are not yet stations; accept their ordinary road bits. */
  if (cache != null) {
    if (tile < 0 || tile >= cache.width * cache.height) return true;
  } else if (!AIMap.IsValidTile(tile)) return true;
  if (tile == stopA || tile == stopB) return false;
  if (cache != null && tile in cache.occupied) return cache.occupied[tile];
  local answer = AITile.IsStationTile(tile) ||
      AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile);
  if (cache != null) cache.occupied.rawset(tile, answer);
  return answer;
}

/* ROAD100-36 site ranking, before Top-3: a miniature rail-style
 * two-step look-ahead along CONNECTED public road edges, not a claimed
 * future corridor. Borrow the native-cheap-first / costly-verify-later
 * separation from AIR site ranking. Never AITest or BuildRoad here.
 * A timeout is unknown (-1), not a physical rejection. */
function OpexRoad100GBExistingExit(site, toward, cache, mark, ceiling)
{
  if (site == null || toward == null ||
      OpexOpsMeasureEnd(mark) >= ceiling) return -1;
  /* Station->front is already proven by the build-sites preflight.
   * Evaluate no more than the TWO axes pointing toward the partner;
   * searching all four directions and all their neighbours censored every
   * site under the 4k opcode budget on seed42. */
  local dx = AIMap.GetTileX(toward.front) - AIMap.GetTileX(site.front);
  local dy = AIMap.GetTileY(toward.front) - AIMap.GetTileY(site.front);
  local ax = dx < 0 ? -dx : dx;
  local ay = dy < 0 ? -dy : dy;
  local horizontal = dx > 0 ? 1 : dx < 0 ? -1 : 0;
  local vertical = dy > 0 ? cache.width : dy < 0 ? -cache.width : 0;
  local steps = ax >= ay ? [horizontal, vertical] : [vertical, horizontal];
  local best = 0;
  foreach (step in steps) {
    if (OpexOpsMeasureEnd(mark) >= ceiling) return -1;
    if (step == 0) continue;
    local next = site.front + step;
    if (!AIMap.IsValidTile(next) ||
        AIMap.DistanceManhattan(site.front, next) != 1 ||
        next == site.tile ||
        OpexRoad100GBOccupied(next, site.tile, toward.tile, cache) ||
        !OpexRoad100GBRoadEdge(site.front, next, cache)) continue;
    local score = 2;
    /* Only a same-axis second road link; no speculative corner and no
     * credit for a road tile without the exact physical connecting edge. */
    local second = next + step;
    if (OpexOpsMeasureEnd(mark) < ceiling &&
        AIMap.IsValidTile(second) &&
        AIMap.DistanceManhattan(next, second) == 1 &&
        second != site.tile && second != site.front &&
        !OpexRoad100GBOccupied(second, site.tile, toward.tile, cache) &&
        OpexRoad100GBRoadEdge(next, second, cache)) score = 4;
    if (score > best) best = score;
  }
  return best;
}

/* RAIL-style bounded local A* replacement around ONE motor-rejected Graph
 * edge. This is NOT a whole-map pathfinder and never changes the real world.
 * Every missing link remains speculative and is re-tested by LongVerifyTrace
 * before admission. In particular a road tile is not a connected road edge. */
function OpexRoad100GBRepairLocal(original, blockedIndex, siteA, siteB,
                                  mark, limitOps)
{
  local out = { trace = null, reason = "PRECHECK", expanded = 0,
      states = 0, ops = 0 };
  local repairMark = OpexOpsMeasureBegin();
  if (original == null || original.len() < 43 ||
      blockedIndex < 2 || blockedIndex >= original.len() - 3 ||
      OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
    out.reason = "NO_WINDOW";
    return out;
  }
  local begin = blockedIndex - 3;
  if (begin < 1) begin = 1;
  local finish = blockedIndex + 4;
  if (finish > original.len() - 2) finish = original.len() - 2;
  local first = original[begin].from;
  local last = original[finish].to;
  if (!AIMap.IsValidTile(first) || !AIMap.IsValidTile(last) ||
      AIMap.DistanceManhattan(first, last) > 12) {
    out.reason = "WINDOW_DISTANCE";
    return out;
  }
  local protectedTiles = {};
  for (local i = 0; i < begin; i++)
    protectedTiles.rawset(original[i].from, true);
  for (local i = finish + 1; i < original.len(); i++)
    protectedTiles.rawset(original[i].to, true);
  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  local sx = first % width;
  local sy = (first - sx) / width;
  local gx = last % width;
  local gy = (last - gx) / width;
  local steps = [1, -1, width, -width];
  local dx = [1, -1, 0, 0];
  local dy = [0, 0, 1, -1];
  local nodes = [{ tile = first, x = sx, y = sy,
      parentIndex = -1, direction = -1,
      depth = 0, cost = 0,
      estimate = ((sx > gx ? sx - gx : gx - sx) +
          (sy > gy ? sy - gy : gy - sy)) * 3,
      closed = false }];
  local cheapest = {};
  local goal = -1;
  for (local expanded = 0; expanded < 24; expanded++) {
    if (OpexOpsMeasureEnd(repairMark) >= 18000 ||
        OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
      out.reason = "REPAIR_OPCAP";
      break;
    }
    local best = -1;
    for (local i = 0; i < nodes.len(); i++) {
      if (nodes[i].closed) continue;
      if (best < 0 || nodes[i].estimate < nodes[best].estimate ||
          (nodes[i].estimate == nodes[best].estimate &&
           nodes[i].cost < nodes[best].cost)) best = i;
    }
    if (best < 0) { out.reason = "NO_FRONTIER"; break; }
    local current = nodes[best];
    nodes[best].closed = true;
    out.expanded++;
    /* No native accessibility claim in this small geometric proposal.
     * The complete OpenTTD verifier remains the sole physical authority. */
    if (current.tile == last) { goal = best; break; }
    if (current.depth >= 18) continue;
    for (local direction = 0; direction < steps.len(); direction++) {
      if (OpexOpsMeasureEnd(repairMark) >= 18000 ||
          OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
        out.reason = "REPAIR_OPCAP";
        break;
      }
      local nx = current.x + dx[direction];
      local ny = current.y + dy[direction];
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
      local next = current.tile + steps[direction];
      local sourceDist = (nx > sx ? nx - sx : sx - nx) +
          (ny > sy ? ny - sy : sy - ny);
      local goalDist = (nx > gx ? nx - gx : gx - nx) +
          (ny > gy ? ny - gy : gy - ny);
      if ((next in protectedTiles && next != last) ||
          (current.tile == original[blockedIndex].from &&
           next == original[blockedIndex].to) ||
          (current.tile == original[blockedIndex].to &&
           next == original[blockedIndex].from) ||
          sourceDist > 11 || goalDist > 11) continue;
      local turn = current.direction >= 0 && current.direction != direction;
      /* Every edge is conservatively costed as MISSING. Two adjacent
       * road tiles are never assumed connected. Real connections, slopes,
       * other stations and cumulative foundations are rechecked by the
       * mandatory physical verifier before any quote or construction. */
      local newCost = current.cost + 5 + (turn ? 2 : 0);
      local state = next * 4 + direction;
      if (state in cheapest && cheapest[state] <= newCost) continue;
      cheapest.rawset(state, newCost);
      if (nodes.len() >= 96) { out.reason = "STATE_CAP"; break; }
      nodes.append({ tile = next, x = nx, y = ny,
          parentIndex = best, direction = direction,
          depth = current.depth + 1, cost = newCost,
          estimate = newCost + goalDist * 3,
          closed = false });
    }
    if (out.reason == "REPAIR_OPCAP" || out.reason == "STATE_CAP") break;
  }
  out.states = nodes.len();
  if (goal < 0) {
    if (out.reason == "PRECHECK") out.reason = "LOCAL_NO_PATH";
    out.ops = OpexOpsMeasureEnd(repairMark);
    return out;
  }
  local reversed = [];
  for (local n = goal; n >= 0; n = nodes[n].parentIndex)
    reversed.append(nodes[n].tile);
  local result = [];
  for (local i = 0; i < begin; i++) result.append(original[i]);
  for (local i = reversed.len() - 1; i > 0; i--)
    result.append({ from = reversed[i], to = reversed[i - 1] });
  for (local i = finish + 1; i < original.len(); i++)
    result.append(original[i]);
  if (result.len() < 43 || result.len() > 190 ||
      result[0].from != siteA.tile ||
      result[result.len() - 1].to != siteB.tile ||
      !OpexRoadOnDtAxis(siteA.tile, siteA.front, result[0].to) ||
      !OpexRoadOnDtAxis(siteB.tile, siteB.front,
          result[result.len() - 1].from)) {
    out.reason = "LENGTH_OR_AXIS";
    out.ops = OpexOpsMeasureEnd(repairMark);
    return out;
  }
  local visited = {};
  local cache = OpexRoad100GBCache();
  visited.rawset(siteA.tile, true);
  local previous = siteA.tile;
  local lastStep = 0;
  foreach (edge in result) {
    if (edge.from != previous || !AIMap.IsValidTile(edge.to) ||
        AIMap.DistanceManhattan(edge.from, edge.to) != 1 ||
        edge.to in visited) {
      out.reason = "CYCLE_OR_DISCONTIGUOUS";
      return out;
    }
    local step = edge.to - edge.from;
    if (lastStep != 0 && step != lastStep &&
        !OpexRoad100GBFlat(edge.from, cache)) {
      out.reason = "UNBUILDABLE_TURN";
      return out;
    }
    visited.rawset(edge.to, true);
    lastStep = step;
    previous = edge.to;
  }
  out.ops = OpexOpsMeasureEnd(repairMark);
  if (out.ops >= 18000 || OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
    out.reason = "REPAIR_OPCAP";
    return out;
  }
  out.trace = result;
  out.reason = "LOCAL_CANDIDATE";
  return out;
}

/* FAST only: cheap occupancy tests at junctions/corners, NEVER per tile.
 * `AITile.IsStationTile` covers all station types, including road stops;
 * road depots are not stations. Every interior speculative tile is checked
 * later by mandatory LongVerifyTrace, then by the actual construction. */
function OpexRoad100GBFastOccupied(tile, siteA, siteB, cache)
{
  if (tile == siteA || tile == siteB) return false;
  if (tile in cache.occupied) return cache.occupied[tile];
  local answer = AITile.IsStationTile(tile) || AIRoad.IsRoadDepotTile(tile);
  cache.occupied.rawset(tile, answer);
  return answer;
}

/* A SHORT exact-road sleeve: at most 20 visited nodes and 6 road edges.
 * This is an existing-road graph, NOT a speculative road-to-road BFS.
 * The selected exit minimizes remaining distance with deterministic ties.
 * A zero-step sleeve is allowed, but the station->front edge must exist. */
function OpexRoad100GBSleeve(site, other, stopA, stopB, mark, ceiling,
                             cache = null)
{
  local out = { tiles = null, expanded = 0, reason = "NO_ROAD" };
  if (cache == null) cache = OpexRoad100GBCache();
  if (!OpexRoad100GBRoadEdge(site.tile, site.front, cache)) {
    out.reason = "FRONT_NOT_CONNECTED";
    return out;
  }
  local dirs = [1, -1, cache.width, -cache.width];
  local entries = [{ tile = site.front, parent_index = -1, depth = 0 }];
  local seen = {};
  seen.rawset(site.tile, true);
  seen.rawset(site.front, true);
  local best = 0;
  local bestDist = AIMap.DistanceManhattan(site.front, other.front);
  local cursor = 0;
  while (cursor < entries.len() && cursor < 20) {
    if (OpexOpsMeasureEnd(mark) >= ceiling - 2000) {
      out.reason = "OPCAP";
      return out;
    }
    local node = entries[cursor];
    out.expanded++;
    local dist = AIMap.DistanceManhattan(node.tile, other.front);
    /* Prefer improvement first, then fewer road edges, then tile index. */
    if (dist < bestDist ||
        (dist == bestDist && node.depth < entries[best].depth) ||
        (dist == bestDist && node.depth == entries[best].depth &&
         node.tile < entries[best].tile)) {
      best = cursor;
      bestDist = dist;
    }
    if (node.depth < 6) {
      foreach (step in dirs) {
        local next = node.tile + step;
        if (next in seen || next == other.tile || next == other.front ||
            OpexRoad100GBOccupied(next, stopA, stopB, cache) ||
            !OpexRoad100GBRoadEdge(node.tile, next, cache)) continue;
        if (entries.len() < 24) {
          seen.rawset(next, true);
          entries.append({ tile = next, parent_index = cursor,
              depth = node.depth + 1 });
        }
      }
    }
    cursor++;
  }
  local reversed = [];
  local pointer = best;
  while (pointer >= 0) {
    reversed.append(entries[pointer].tile);
    pointer = entries[pointer].parent_index;
  }
  out.tiles = [];
  for (local i = reversed.len() - 1; i >= 0; i--)
    out.tiles.append(reversed[i]);
  out.reason = "OK";
  return out;
}

/* One ROLLING LOCAL GAP. The goal is not a fixed grid checkpoint: it is
 * either the far facade or an advance >=4 for d43..80 (>=8 beyond 80).
 * Each closed expansion scans only four neighbours; 42 expansions at most,
 * maximum 14 steps and a 14-tile neighbourhood around the current tip.
 *
 * An existing road edge costs 1, a speculative new bit costs 5. A switch
 * of axis through a future road bit requires a flat corner. Only existing
 * two-way connections are credited as real; all other edges stay pending.
 * No AITestMode is used, hence no false claim about compounded road bits. */
function OpexRoad100GBGap(startTile, goalTile, incoming, occupied,
                          stopA, stopB, mark, ceiling, cache = null,
                          incomingReal = true)
{
  local out = { tiles = null, expanded = 0, reason = "NO_GAP",
      obstacles = 0, pending = 0 };
  if (cache == null) cache = OpexRoad100GBCache();
  local width = cache.width;
  local sx = AIMap.GetTileX(startTile);
  local sy = AIMap.GetTileY(startTile);
  local gx = AIMap.GetTileX(goalTile);
  local gy = AIMap.GetTileY(goalTile);
  local d0 = (sx > gx ? sx - gx : gx - sx) +
      (sy > gy ? sy - gy : gy - sy);
  if (d0 < 1) { out.tiles = [startTile]; out.reason = "OK"; return out; }
  local dx = [1, -1, 0, 0];
  local dy = [0, 0, 1, -1];
  local steps = [1, -1, width, -width];
  local frontier = [{ tile = startTile, x = sx, y = sy,
      parent_index = -1, step = incoming, real_in = incomingReal, depth = 0,
      cost = 0, score = d0 * 6, closed = false }];
  /* Entering from another direction (or speculative rather than existing
   * edge) changes whether the following bend is physically feasible. */
  local cheapest = {};
  local advanceMin = d0 <= 80 ? 4 : 8;
  local completed = false;
  for (local count = 0; count < 42; count++) {
    if (OpexOpsMeasureEnd(mark) >= ceiling - 1700) {
      out.reason = "OPCAP";
      return out;
    }
    local best = -1;
    for (local k = 0; k < frontier.len(); k++) {
      if (frontier[k].closed) continue;
      if (best < 0 || frontier[k].score < frontier[best].score ||
          (frontier[k].score == frontier[best].score &&
           frontier[k].cost < frontier[best].cost) ||
          (frontier[k].score == frontier[best].score &&
           frontier[k].cost == frontier[best].cost &&
           frontier[k].tile < frontier[best].tile)) best = k;
    }
    if (best < 0) break;
    local cur = frontier[best];
    frontier[best].closed = true;
    out.expanded++;
    local remain = (cur.x > gx ? cur.x - gx : gx - cur.x) +
        (cur.y > gy ? cur.y - gy : gy - cur.y);
    /* A short d43..80 corridor can cross obstacles in four-tile sections.
     * A long corridor retains eight-tile advances to fit in 20 hops.
     * An exit is only a *candidate*, not proof of a new road connection. */
    if (cur.tile == goalTile || (d0 > 12 && d0 - remain >= advanceMin)) {
      local reverse = [];
      local i = best;
      while (i >= 0) {
        reverse.append(frontier[i].tile);
        i = frontier[i].parent_index;
      }
      out.tiles = [];
      for (local j = reverse.len() - 1; j >= 0; j--)
        out.tiles.append(reverse[j]);
      out.reason = "OK";
      completed = true;
      break;
    }
    if (cur.depth >= 14) continue;
    for (local direction = 0; direction < 4; direction++) {
      local nx = cur.x + dx[direction];
      local ny = cur.y + dy[direction];
      if (nx < 0 || ny < 0 || nx >= cache.width || ny >= cache.height)
        continue;
      local next = cur.tile + steps[direction];
      if (((next in occupied) && next != goalTile) ||
          (cur.parent_index >= 0 &&
           next == frontier[cur.parent_index].tile)) continue;
      local fromStart = (nx > sx ? nx - sx : sx - nx) +
          (ny > sy ? ny - sy : sy - ny);
      local toGoal = (nx > gx ? nx - gx : gx - nx) +
          (ny > gy ? ny - gy : gy - ny);
      if (fromStart > 14 || toGoal > d0 + 2) continue;
      if (OpexRoad100GBOccupied(next, stopA, stopB, cache)) {
        out.obstacles++;
        continue;
      }
      /* The former OpexRoad100GBRoadEdge(cur.tile, next) call now shares
       * the per-attempt cache; dropping the third argument regresses ops. */
      local real = OpexRoad100GBRoadEdge(cur.tile, next, cache);
      if (!real) {
        /* RoadTile alone does NOT imply a usable road link. Future edges
         * are classified pending; VerifyTrace may reject ERR260. */
        if (!OpexRoad100GBRoadTile(next, cache) &&
            !OpexRoad100GBBuildable(next, cache)) {
          out.obstacles++;
          continue;
        }
        if (cur.step != 0 && cur.step != steps[direction] &&
            !OpexRoad100GBFlat(cur.tile, cache)) {
          out.obstacles++;
          continue;
        }
        if (next != goalTile && !OpexRoad100GBRoadTile(next, cache) &&
            !OpexRoad100GBFlat(next, cache)) {
          out.obstacles++;
          continue;
        }
      }
      local turn = cur.step != 0 && cur.step != steps[direction];
      local newCost = cur.cost + (real ? 1 : 5) + (turn ? 2 : 0);
      /* Every state depends on tile, arrival axis/direction and whether
       * the incoming edge already connects; no accidental cheapest collapse. */
      local key = next * 8 + direction * 2 + (real ? 1 : 0);
      if (key in cheapest && cheapest[key] <= newCost) continue;
      cheapest.rawset(key, newCost);
      if (frontier.len() >= 130) { out.reason = "FRONTIER_CAP"; return out; }
      frontier.append({ tile = next, x = nx, y = ny,
          parent_index = best, step = steps[direction], real_in = real,
          depth = cur.depth + 1, cost = newCost,
          score = newCost + 6 * toGoal, closed = false });
    }
  }
  if (!completed) out.reason = "LOCAL_NODE_CAP";
  return out;
}

/* Pure arithmetic: reject a corridor crossing a protected sleeve/station
 * before spending opcodes populating 100+ speculative per-tile edges.
 * This is NOT a road connectivity or buildability test. */
function OpexRoad100GBFastOnSegment(tile, x0, y0, x1, y1, width)
{
  local x = tile % width;
  local y = (tile - x) / width;
  if (x0 == x1) return x == x0 &&
      y >= (y0 < y1 ? y0 : y1) && y <= (y0 > y1 ? y0 : y1);
  if (y0 == y1) return y == y0 &&
      x >= (x0 < x1 ? x0 : x1) && x <= (x0 > x1 ? x0 : x1);
  return false;
}

/* ROAD100-36 FAST sleeve-to-sleeve geometry, strictly speculative.
 * No graph search, no AITest and no construction. Every sleeve edge is
 * bidirectionally connected already; ALL bridge edges are conservatively
 * pending, even when two adjacent road tiles happen to be present. The
 * existing OpexRoad100LongVerifyTrace is the only physical arbiter.
 *
 * Try a small deterministic family: direct L (one bend), offset doglegs
 * (two bends), then a middle corridor (three bends). No loop over map
 * positions: every corner is derived from the actual sleeve tips. */
function OpexRoad100GBFastTrace(siteA, siteB, sleeveA, sleeveB,
                                 mark, pairCeiling, cache)
{
  local result = { trace = null, reason = "FAST_REJECT", ops = 0,
      variants = 0, bends = 0, existing = 0, pending = 0,
      blocked_tile = -1, route = -1, rejections = "" };
  local started = OpexOpsMeasureBegin();
  local axTile = sleeveA.tiles[sleeveA.tiles.len() - 1];
  local bxTile = sleeveB.tiles[sleeveB.tiles.len() - 1];
  local ax = AIMap.GetTileX(axTile);
  local ay = AIMap.GetTileY(axTile);
  local bx = AIMap.GetTileX(bxTile);
  local by = AIMap.GetTileY(bxTile);
  local width = cache.width;
  local middleX = ax + (bx - ax) / 2;
  local middleY = ay + (by - ay) / 2;
  /* Prefer the axis continuing away from the actual city-road sleeve.
   * For a 2-corner detour, avoid a corner on the first/last urban tile. */
  local firstStep = sleeveA.tiles.len() > 1
      ? axTile - sleeveA.tiles[sleeveA.tiles.len() - 2]
      : siteA.front - siteA.tile;
  local horizontal = firstStep == 1 || firstStep == -1;
  local variants = horizontal ? [2, 0, 3, 1, 4]
      : [3, 1, 2, 0, 4];
  local span = (ax > bx ? ax - bx : bx - ax) +
      (ay > by ? ay - by : by - ay);
  for (local vi = 0; vi < variants.len(); vi++) {
    if (OpexOpsMeasureEnd(started) >= 6000 ||
        OpexOpsMeasureEnd(mark) >= pairCeiling - 50000) {
      result.reason = "FAST_OPCAP";
      break;
    }
    result.variants++;
    local variant = variants[vi];
    local corners = [];
    if (variant == 0) corners.append([bx, ay]);
    else if (variant == 1) corners.append([ax, by]);
    else if (variant == 2) {
      corners.append([middleX, ay]);
      corners.append([middleX, by]);
    } else if (variant == 3) {
      corners.append([ax, middleY]);
      corners.append([bx, middleY]);
    } else {
      corners.append([middleX, ay]);
      corners.append([middleX, middleY]);
      corners.append([bx, middleY]);
    }
    local points = [[ax, ay]];
    foreach (point in corners) {
      local previous = points[points.len() - 1];
      if (point[0] == previous[0] && point[1] == previous[1]) continue;
      points.append(point);
    }
    local previous = points[points.len() - 1];
    if (previous[0] != bx || previous[1] != by) points.append([bx, by]);
    /* A straight, degenerate corridor is legal; diagonal/zero segments
     * are not. Prune length before any per-tile native calls. */
    local bridgeLength = 0;
    local badGeometry = false;
    for (local i = 1; i < points.len(); i++) {
      local x0 = points[i - 1][0];
      local y0 = points[i - 1][1];
      local x1 = points[i][0];
      local y1 = points[i][1];
      if ((x0 != x1 && y0 != y1) ||
          x0 < 0 || x1 < 0 || y0 < 0 || y1 < 0 ||
          x0 >= cache.width || x1 >= cache.width ||
          y0 >= cache.height || y1 >= cache.height) {
        badGeometry = true; break;
      }
      bridgeLength += (x0 > x1 ? x0 - x1 : x1 - x0) +
          (y0 > y1 ? y0 - y1 : y1 - y0);
    }
    local length = 2 + sleeveA.tiles.len() - 1 +
        sleeveB.tiles.len() - 1 + bridgeLength;
    if (badGeometry || length < 43 || length > 190 ||
        bridgeLength != span || bridgeLength == 0) {
      result.reason = "FAST_REJECT_GEOMETRY";
      result.rejections += variant + ":GEOMETRY;";
      continue;
    }
    /* A corridor must not return through the true A sleeve, station A/B
     * or B's reserved suffix. Test a few protected tiles against simple
     * segments before allocating a 43..190 edge route. The exhaustive
     * per-tile cycle test below remains mandatory. */
    local sleeveCollision = false;
    for (local si = 1; si < points.len() && !sleeveCollision; si++) {
      local x0 = points[si - 1][0];
      local y0 = points[si - 1][1];
      local x1 = points[si][0];
      local y1 = points[si][1];
      if (OpexRoad100GBFastOnSegment(siteA.tile,
              x0, y0, x1, y1, width) ||
          OpexRoad100GBFastOnSegment(siteB.tile,
              x0, y0, x1, y1, width)) {
        sleeveCollision = true;
        break;
      }
      for (local sa = 0; sa + 1 < sleeveA.tiles.len(); sa++) {
        if (OpexRoad100GBFastOnSegment(sleeveA.tiles[sa],
                x0, y0, x1, y1, width)) {
          sleeveCollision = true;
          break;
        }
      }
      if (sleeveCollision) break;
      for (local sb = 0; sb + 1 < sleeveB.tiles.len(); sb++) {
        if (OpexRoad100GBFastOnSegment(sleeveB.tiles[sb],
                x0, y0, x1, y1, width)) {
          sleeveCollision = true;
          break;
        }
      }
    }
    if (sleeveCollision) {
      result.reason = "FAST_REJECT_SLEEVE_CROSS";
      result.rejections += variant + ":SLEEVE_CROSS;";
      continue;
    }
    /* Exact L1 length makes the orthogonal bridge monotone in X and Y:
     * no internal tile can repeat. The explicit sleeve-cross check above
     * excludes ALL A/B prefixes. Only real sleeve tiles need a seen map;
     * inserting/checking 43..190 speculative tiles is redundant and costly. */
    local seen = {};
    seen.rawset(siteA.tile, true);
    local trace = [];
    local fromTile = siteA.tile;
    local prevTile = -1;
    local rejected = false;
    local blocked = -1;
    foreach (tile in sleeveA.tiles) {
      if (tile in seen) { rejected = true; blocked = tile; break; }
      seen.rawset(tile, true);
      trace.append({ from = fromTile, to = tile });
      prevTile = fromTile;
      fromTile = tile;
    }
    if (rejected) {
      result.reason = "FAST_REJECT_CYCLE";
      result.rejections += variant + ":SLEEVE_CYCLE;";
      continue;
    }
    if (bxTile in seen) {
      result.reason = "FAST_REJECT_CYCLE";
      result.rejections += variant + ":TIP_CYCLE;";
      continue;
    }
    /* Walk the candidate's purely geometric tiles. Native occupancy,
     * road-bit and terrain queries PER TILE exhaust the whole FAST 8k
     * budget. Only critical turns are probed here; all intermediate
     * tiles remain speculative until mandatory LongVerifyTrace. */
    for (local i = 1; i < points.len() && !rejected; i++) {
      local x0 = points[i - 1][0];
      local y0 = points[i - 1][1];
      local x1 = points[i][0];
      local y1 = points[i][1];
      local step = x0 != x1 ? (x1 > x0 ? 1 : -1)
          : (y1 > y0 ? width : -width);
      local steps = (x0 != x1 ? (x1 > x0 ? x1 - x0 : x0 - x1)
          : (y1 > y0 ? y1 - y0 : y0 - y1));
      local current = fromTile;
      /* The direction is constant inside an orthogonal segment, so its
       * only possible new turn is at `current`, checked exactly once. */
      local incoming = prevTile >= 0 ? current - prevTile : 0;
      if (incoming != 0 && incoming != step &&
          (OpexRoad100GBFastOccupied(current, siteA.tile, siteB.tile,
              cache) || !OpexRoad100GBFlat(current, cache))) {
        blocked = current;
        result.reason = "FAST_REJECT_TURN";
        rejected = true;
        break;
      }
      for (local j = 0; j < steps; j++) {
        if (j % 32 == 0 &&
            (OpexOpsMeasureEnd(started) >= 6000 ||
             OpexOpsMeasureEnd(mark) >= pairCeiling - 50000)) {
          result.reason = "FAST_OPCAP";
          rejected = true;
          break;
        }
        local next = current + step;
        if (next == siteB.tile) {
          blocked = next;
          result.reason = "FAST_REJECT_CYCLE";
          rejected = true;
          break;
        }
        /* A missing tile is only a geometrical hypothesis here; all
         * road bits/stations/depots are tested in LongVerifyTrace. */
        trace.append({ from = current, to = next });
        prevTile = current;
        current = next;
      }
      fromTile = current;
    }
    if (rejected) {
      result.blocked_tile = blocked;
      result.rejections += variant + ":" + result.reason + ";";
      continue;
    }
    /* Physical sleeve B is traversed in reverse, not spuriously joined
     * to nearby road bits. Check join turn before adding this suffix. */
    for (local bi = sleeveB.tiles.len() - 2; bi >= 0; bi--) {
      local next = sleeveB.tiles[bi];
      if (next in seen) {
        rejected = true;
        blocked = next;
        result.reason = "FAST_REJECT_CYCLE";
        break;
      }
      local current = fromTile;
      local incoming = current - prevTile;
      local outgoing = next - current;
      /* Only the FIRST transition from a hypothetical bridge into a
       * physically connected B sleeve needs a new turn precheck. Turns
       * inside an existing sleeve were already true road connections. */
      if (bi == sleeveB.tiles.len() - 2 && incoming != outgoing &&
          (OpexRoad100GBFastOccupied(current, siteA.tile, siteB.tile,
              cache) || !OpexRoad100GBFlat(current, cache))) {
        rejected = true;
        blocked = current;
        result.reason = "FAST_REJECT_TURN";
        break;
      }
      seen.rawset(next, true);
      trace.append({ from = current, to = next });
      prevTile = current;
      fromTile = next;
    }
    if (rejected) {
      result.blocked_tile = blocked;
      result.rejections += variant + ":" + result.reason + ";";
      continue;
    }
    if (siteB.tile in seen) {
      result.reason = "FAST_REJECT_CYCLE";
      result.blocked_tile = siteB.tile;
      result.rejections += variant + ":END_CYCLE;";
      continue;
    }
    /* The reverse B station-front link is already connected, but a new
     * bridge approaching it at 90 degrees needs a flat B-front turn. */
    local bFrontTile = fromTile;
    local toStation = siteB.tile - bFrontTile;
    local fromBridge = bFrontTile - prevTile;
    if (sleeveB.tiles.len() == 1 && fromBridge != toStation &&
        (OpexRoad100GBFastOccupied(bFrontTile, siteA.tile, siteB.tile,
            cache) || !OpexRoad100GBFlat(bFrontTile, cache))) {
      result.reason = "FAST_REJECT_TURN_B";
      result.blocked_tile = bFrontTile;
      result.rejections += variant + ":TURN_B;";
      continue;
    }
    trace.append({ from = fromTile, to = siteB.tile });
    if (trace.len() != length ||
        !OpexRoadOnDtAxis(siteA.tile, siteA.front, trace[0].to) ||
        !OpexRoadOnDtAxis(siteB.tile, siteB.front,
            trace[trace.len() - 1].from)) {
      result.reason = "FAST_REJECT_AXIS";
      result.rejections += variant + ":AXIS;";
      continue;
    }
    /* Single-pass contiguous trace: no intermediate path array or
     * second full traversal. Missing edges are NEVER credited as real
     * connectivity until LongVerifyTrace and transactional construction. */
    result.ops = OpexOpsMeasureEnd(started);
    if (result.ops >= 7800 ||
        OpexOpsMeasureEnd(mark) >= pairCeiling - 50000) {
      result.reason = "FAST_OPCAP";
      break;
    }
    result.trace = trace;
    result.route = trace.len();
    result.bends = points.len() - 2;
    result.existing = sleeveA.tiles.len() + sleeveB.tiles.len();
    result.pending = bridgeLength;
    result.reason = "FAST_CANDIDATE";
    break;
  }
  result.ops = OpexOpsMeasureEnd(started);
  if (result.ops >= 8000 ||
      OpexOpsMeasureEnd(mark) >= pairCeiling - 50000) {
    result.trace = null;
    result.reason = "FAST_OPCAP";
  }
  return result;
}

/* Graph-only local bypass of an ERR_AREA_NOT_CLEAR or town-road rejection
 * within the first 20 road edges. This does not certify construction:
 * caller tests the ENTIRE returned route through LongVerifyTrace. The
 * short straight window avoids moving either stop, and all own turns
 * must be flat. Historical LongDoglegTrace remains byte-exact OFF. */
/* V36 only: rank nearer 43..80 markets before expensive full urban scans.
 * This is an EXPLORATION priority, not a passenger revenue/ROI estimate.
 * Keep the same two disjoint town pairs and all longer markets available. */
function OpexRoad100GBMarketBetter(a, b)
{
  local aNear = a.distance >= 43 && a.distance <= 80;
  local bNear = b.distance >= 43 && b.distance <= 80;
  if (aNear != bNear) return aNear;
  if (a.proxy != b.proxy) return a.proxy > b.proxy;
  if (a.distance != b.distance) return a.distance < b.distance;
  if (a.idLo != b.idLo) return a.idLo < b.idLo;
  return a.idHi < b.idHi;
}

function OpexRoad100GBSelectDiverseMarkets(pool)
{
  local chosen = [];
  local first = null;
  foreach (item in pool) {
    if (first == null || OpexRoad100GBMarketBetter(item, first)) first = item;
  }
  if (first == null) return chosen;
  chosen.append(first);
  local second = null;
  foreach (item in pool) {
    if (item.idLo == first.idLo || item.idLo == first.idHi ||
        item.idHi == first.idLo || item.idHi == first.idHi) continue;
    if (second == null || OpexRoad100GBMarketBetter(item, second)) second = item;
  }
  if (second == null) {
    foreach (item in pool) {
      if (item.idLo == first.idLo && item.idHi == first.idHi) continue;
      if (second == null || OpexRoad100GBMarketBetter(item, second)) second = item;
    }
  }
  if (second != null) chosen.append(second);
  return chosen;
}

function OpexRoad100GBFrontDoglegTrace(original, blockedIndex, side, offset,
                                       siteA, siteB, diagnostic = null)
{
  if (diagnostic != null) diagnostic.reason = "PARAM";
  if (original == null || blockedIndex < 1 || blockedIndex > 20 ||
      original.len() < 43 || offset < 1 || offset > 3 ||
      (side != -1 && side != 1)) return null;
  local direction = original[blockedIndex].to - original[blockedIndex].from;
  if (direction != 1 && direction != -1 &&
      direction != AIMap.GetMapSizeX() && direction != -AIMap.GetMapSizeX()) {
    if (diagnostic != null) diagnostic.reason = "DIRECTION";
    return null;
  }
  local begin = blockedIndex;
  while (begin > 1 && blockedIndex - begin < 3 &&
      original[begin - 1].to - original[begin - 1].from == direction) begin--;
  /* If the near anchor lies on a hill, retreat up to four MORE straight
   * physical trace edges to find a flat turn. Never enter the station
   * frontage at index 0 or cross a change of direction. This changes
   * only speculative geometry; the caller verifies all actual bits. */
  local flatBackoff = 0;
  while (begin > 1 && flatBackoff < 4 &&
      !OpexRoadIsFlat(original[begin].from) &&
      original[begin - 1].to - original[begin - 1].from == direction) {
    begin--;
    flatBackoff++;
  }
  local finish = blockedIndex;
  while (finish + 2 < original.len() && finish - blockedIndex < 4 &&
      original[finish + 1].to - original[finish + 1].from == direction) finish++;
  if (finish - begin < 2) {
    if (diagnostic != null) diagnostic.reason = "STRAIGHT_WINDOW";
    return null;
  }
  local first = original[begin].from;
  local last = original[finish].to;
  local x0 = AIMap.GetTileX(first);
  local y0 = AIMap.GetTileY(first);
  local x1 = AIMap.GetTileX(last);
  local y1 = AIMap.GetTileY(last);
  if (x0 != x1 && y0 != y1) {
    if (diagnostic != null) diagnostic.reason = "WINDOW_TURN";
    return null;
  }
  local dx = x0 == x1 ? side * offset : 0;
  local dy = y0 == y1 ? side * offset : 0;
  if (!OpexRoadInMap(x0 + dx, y0 + dy) ||
      !OpexRoadInMap(x1 + dx, y1 + dy)) {
    if (diagnostic != null) diagnostic.reason = "MAP_EDGE";
    return null;
  }
  local bypassA = AIMap.GetTileIndex(x0 + dx, y0 + dy);
  local bypassB = AIMap.GetTileIndex(x1 + dx, y1 + dy);
  if (!OpexRoadIsFlat(first)) {
    if (diagnostic != null) diagnostic.reason = "NONFLAT_FIRST";
    return null;
  }
  if (!OpexRoadIsFlat(last)) {
    if (diagnostic != null) diagnostic.reason = "NONFLAT_LAST";
    return null;
  }
  if (!OpexRoadIsFlat(bypassA)) {
    if (diagnostic != null) diagnostic.reason = "NONFLAT_BYPASS_A";
    return null;
  }
  if (!OpexRoadIsFlat(bypassB)) {
    if (diagnostic != null) diagnostic.reason = "NONFLAT_BYPASS_B";
    return null;
  }
  local result = [];
  for (local i = 0; i < begin; i++) result.append(original[i]);
  OpexRoadAppendSegment(result, first, bypassA);
  OpexRoadAppendSegment(result, bypassA, bypassB);
  OpexRoadAppendSegment(result, bypassB, last);
  for (local i = finish + 1; i < original.len(); i++)
    result.append(original[i]);
  if (result.len() < 43 || result.len() > 190 ||
      result[0].from != siteA.tile ||
      result[result.len() - 1].to != siteB.tile ||
      !OpexRoadOnDtAxis(siteA.tile, siteA.front, result[0].to) ||
      !OpexRoadOnDtAxis(siteB.tile, siteB.front,
          result[result.len() - 1].from)) {
    if (diagnostic != null) diagnostic.reason = "LENGTH_OR_STOP_AXIS";
    return null;
  }
  local visited = {};
  visited.rawset(siteA.tile, true);
  local prevDir = 0;
  foreach (edge in result) {
    if (!AIMap.IsValidTile(edge.from) || !AIMap.IsValidTile(edge.to) ||
        AIMap.DistanceManhattan(edge.from, edge.to) != 1) {
      if (diagnostic != null) diagnostic.reason = "INVALID_EDGE";
      return null;
    }
    if (edge.to in visited) {
      if (diagnostic != null) diagnostic.reason = "CYCLE";
      return null;
    }
    local step = edge.to - edge.from;
    if (prevDir != 0 && step != prevDir &&
        !OpexRoadIsFlat(edge.from)) {
      if (diagnostic != null) diagnostic.reason = "NONFLAT_TURN";
      return null;
    }
    visited.rawset(edge.to, true);
    prevDir = step;
  }
  if (diagnostic != null) diagnostic.reason = "OK";
  return result;
}

/* INTEGRATION API (the prime must include this file, opt-in default 0):
 * local graph = OpexRoad100GraphBridgeTrace(pair.a, pair.b, mark, limitOps);
 * // Only the GRAPH branch may lower the verifier's legacy 80-tile minimum
 * // to 43. Same edge AITest rules as OpexRoad100LongVerifyTrace; the prime
 * // integrates this dispatch and its guard, never the tracer itself.
 * DO NOT publish, budget or construct unless checked.ok, depot and finance
 * preflight all succeed. `verified = false` is intentional, always.
 *
 * mark/limitOps are the EXISTING ConstructPlan shared budget. This helper
 * additionally enforces <42k measured opcodes per attempt and considers
 * at most 180k of the caller's current pair budget (50k retained for
 * VerifyTrace, depot and economics). It does not allocate a new 180k pot.
 */
function OpexRoad100GraphBridgeTrace(siteA, siteB, mark, limitOps)
{
  local out = { trace = null, verified = false, reason = "PRECHECK",
      ops = 0, sleeve_a = 0, sleeve_b = 0, expanded = 0,
      hops = 0, existing = 0, pending = 0, obstacles = 0,
      blocked_tile = -1, route = -1, join = 0,
      road_queries = 0, edge_queries = 0, cache_hits = 0,
      fast_reason = "FAST_NOT_RUN", fast_ops = 0,
      fast_variants = 0, fast_bends = 0, fast_blocked = -1,
      fast_rejections = "" };
  local beginMark = OpexOpsMeasureBegin();
  local pairCeiling = limitOps < 180000 ? limitOps : 180000;
  /* The original 38k upper budget includes 3k reserved for aggregation:
   * actual sleeves/gaps cease at 35k, hard return at 42k. */
  local attemptCeiling = 38000;
  local usableOps = pairCeiling - OpexOpsMeasureEnd(mark) - 50000;
  if (usableOps < attemptCeiling) attemptCeiling = usableOps;
  if (attemptCeiling < 7000) out.reason = "COUPLE_OPCAP";
  else if (siteA == null || siteB == null ||
      !("tile" in siteA) || !("front" in siteA) ||
      !("tile" in siteB) || !("front" in siteB) ||
      !AIMap.IsValidTile(siteA.tile) || !AIMap.IsValidTile(siteB.tile) ||
      !AIMap.IsValidTile(siteA.front) || !AIMap.IsValidTile(siteB.front))
    out.reason = "INVALID_SITE";
  else if (!OpexRoad100GBRoadEdge(siteA.tile, siteA.front) ||
      !OpexRoad100GBRoadEdge(siteB.tile, siteB.front))
    out.reason = "FRONT_NOT_CONNECTED";
  else {
    local localMark = OpexOpsMeasureBegin();
    local cache = OpexRoad100GBCache();
    /* Attempt budget and shared budget: checked in every sleeve/mini-gap. */
    local localCeiling = attemptCeiling - 3000;
    local sleeveA = OpexRoad100GBSleeve(siteA, siteB, siteA.tile,
        siteB.tile, localMark, localCeiling, cache);
    local sleeveB = sleeveA.reason == "OK" ?
        OpexRoad100GBSleeve(siteB, siteA, siteA.tile,
            siteB.tile, localMark, localCeiling, cache) : null;
    if (sleeveA.reason != "OK" || sleeveB == null ||
        sleeveB.reason != "OK")
      out.reason = sleeveA.reason != "OK" ? "SLEEVE_A_" + sleeveA.reason :
          "SLEEVE_B_" + sleeveB.reason;
    else {
      out.sleeve_a = sleeveA.tiles.len() - 1;
      out.sleeve_b = sleeveB.tiles.len() - 1;
      /* ROAD100-36 fixed hypothesis: one bounded orthogonal proposal,
       * before any repeated GBGap graph expansions. Its speculative edges
       * MUST still pass the common LongVerifyTrace in builder_road.nut. */
      local fast = OpexRoad100GBFastTrace(siteA, siteB, sleeveA, sleeveB,
          mark, pairCeiling, cache);
      out.fast_reason = fast.reason;
      out.fast_ops = fast.ops;
      out.fast_variants = fast.variants;
      out.fast_bends = fast.bends;
      out.fast_blocked = fast.blocked_tile;
      out.fast_rejections = fast.rejections;
      if (fast.trace != null) {
        out.trace = fast.trace;
        out.reason = "FAST_CANDIDATE";
        out.route = fast.route;
        out.existing = fast.existing;
        out.pending = fast.pending;
        out.blocked_tile = -1;
      }
      if (fast.trace == null) {
      local used = {};
      local protectedB = {};
      local candidate = [siteA.tile];
      used.rawset(siteA.tile, true);
      local ok = true;
      /* A shared road tile is physical connectivity, not a collision.
       * Join the first A-prefix to the B-prefix (traversed backwards),
       * but ONLY on genuinely bidirectional road bits. Prefixes are short
       * and cannot contain speculative links. A short joint trace still
       * has to meet the caller's 43-edge minimum, without padding loops. */
      local joinA = -1;
      local joinB = -1;
      local joinLength = 999999;
      for (local ai = 0; ai < sleeveA.tiles.len(); ai++) {
        for (local bi = 0; bi < sleeveB.tiles.len(); bi++) {
          if (sleeveA.tiles[ai] != sleeveB.tiles[bi]) continue;
          local length = ai + bi + 2;
          if (length < joinLength ||
              (length == joinLength &&
               sleeveA.tiles[ai] < sleeveA.tiles[joinA])) {
            joinA = ai;
            joinB = bi;
            joinLength = length;
          }
        }
      }
      if (joinA >= 0) {
        /* All these edges were individually proven connected BOTH ways
         * when their road sleeves were scanned. Still check uniqueness. */
        for (local i = 0; i <= joinA; i++) {
          local tile = sleeveA.tiles[i];
          if (tile in used) { ok = false; out.reason = "JOIN_CYCLE"; break; }
          candidate.append(tile);
          used.rawset(tile, true);
        }
        if (ok) {
          for (local i = joinB - 1; i >= 0; i--) {
            local tile = sleeveB.tiles[i];
            if (tile in used) { ok = false; out.reason = "JOIN_CYCLE"; break; }
            candidate.append(tile);
            used.rawset(tile, true);
          }
        }
        out.join = 1;
      } else {
        foreach (tile in sleeveA.tiles) {
          if (tile in used) { out.reason = "SLEEVE_A_CYCLE"; ok = false; break; }
          candidate.append(tile);
          used.rawset(tile, true);
        }
        foreach (tile in sleeveB.tiles) protectedB.rawset(tile, true);
      }
      if (ok) {
        local bTip = joinA >= 0 ? sleeveB.tiles[0] :
            sleeveB.tiles[sleeveB.tiles.len() - 1];
        local current = candidate[candidate.len() - 1];
        local incoming = candidate.len() >= 2 ?
            candidate[candidate.len() - 1] - candidate[candidate.len() - 2] : 0;
        /* A single table accumulates occupancy, instead of rebuilding it
         * at each hop (hotspot of V36 seed42). A's current tip is already
         * occupied; the gap rejects only NEXT tiles from this table. */
        /* The reserved B sleeve must NOT be marked as a VISITED A tile:
         * its suffix is appended later and checked against `used` only. */
        local occupied = {};
        foreach (tile, flag in used) occupied.rawset(tile, true);
        if (joinA < 0) {
          occupied.rawset(siteB.tile, true);
          foreach (tile in sleeveB.tiles) {
            if (tile != bTip) occupied.rawset(tile, true);
          }
        }
        for (local hop = 0; hop < 20 && current != bTip; hop++) {
          if (OpexOpsMeasureEnd(localMark) >= localCeiling - 2000 ||
              OpexOpsMeasureEnd(mark) >= pairCeiling - 50000) {
            out.reason = "OPCAP"; ok = false; break;
          }
          local realIncoming = candidate.len() >= 2 &&
              OpexRoad100GBRoadEdge(candidate[candidate.len() - 2],
                  current, cache);
          local patch = OpexRoad100GBGap(current, bTip, incoming,
              occupied, siteA.tile, siteB.tile, localMark, localCeiling,
              cache, realIncoming);
          out.expanded += patch.expanded;
          out.obstacles += patch.obstacles;
          if (patch.tiles == null || patch.tiles.len() < 2) {
            out.reason = "GAP_" + patch.reason;
            ok = false;
            break;
          }
          for (local j = 1; j < patch.tiles.len(); j++) {
            local next = patch.tiles[j];
            if (next in used || (next in protectedB && next != bTip) ||
                candidate.len() >= 190) {
              out.reason = "CYCLE_OR_LENGTH"; ok = false; break;
            }
            candidate.append(next);
            used.rawset(next, true);
            occupied.rawset(next, true);
          }
          if (!ok) break;
          out.hops++;
          incoming = candidate[candidate.len() - 1] -
              candidate[candidate.len() - 2];
          current = candidate[candidate.len() - 1];
        }
        if (ok && current != bTip) { out.reason = "HOP_CAP"; ok = false; }
        if (ok && joinA < 0) {
          /* Reverse B sleeve: tip -> ... -> front B -> stop B. */
          for (local j = sleeveB.tiles.len() - 2; j >= 0; j--) {
            local next = sleeveB.tiles[j];
            if (next in used || candidate.len() >= 190) {
              out.reason = "SUFFIX_CYCLE"; ok = false; break;
            }
            candidate.append(next);
            used.rawset(next, true);
          }
        }
        if (ok && (siteB.tile in used || candidate.len() >= 191)) {
          out.reason = "END_CYCLE"; ok = false;
        }
        if (ok) candidate.append(siteB.tile);
      }
      if (ok) {
        local routeLength = candidate.len() - 1;
        out.route = routeLength;
        if (routeLength < 43 || routeLength > 190 ||
            !OpexRoadOnDtAxis(siteA.tile, siteA.front, candidate[1]) ||
            !OpexRoadOnDtAxis(siteB.tile, siteB.front,
                candidate[candidate.len() - 2]))
          out.reason = "LENGTH_OR_AXIS";
        else {
          local trace = [];
          for (local i = 1; i < candidate.len(); i++) {
            local fromTile = candidate[i - 1];
            local toTile = candidate[i];
            if (AIMap.DistanceManhattan(fromTile, toTile) != 1 ||
                OpexRoad100GBOccupied(fromTile, siteA.tile, siteB.tile, cache) ||
                OpexRoad100GBOccupied(toTile, siteA.tile, siteB.tile, cache)) {
              out.reason = "OCCUPIED_OR_DISCONTIGUOUS";
              out.blocked_tile = toTile;
              ok = false;
              break;
            }
            if (OpexRoad100GBRoadEdge(fromTile, toTile, cache)) out.existing++;
            else out.pending++;
            trace.append({ from = fromTile, to = toTile });
          }
          if (ok) {
            out.trace = trace;
            out.reason = "CANDIDATE_NEEDS_VERIFY";
          }
        }
      }
      }
    }
    out.road_queries = cache.road_queries;
    out.edge_queries = cache.edge_queries;
    out.cache_hits = cache.cache_hits;
  }
  out.ops = OpexOpsMeasureEnd(beginMark);
  /* Decide publication BEFORE logging. Reserve 4k for string formatting,
   * the single diagnostic and the return path, rather than logging an
   * accepted trace then silently replacing it by null. */
  if (out.ops >= 38000 || OpexOpsMeasureEnd(mark) >= pairCeiling - 50000) {
    out.trace = null;
    out.reason = "OPCAP";
  }
  if (DECISION_LOG) OpexDecide("ROAD100_GRAPH_BRIDGE",
      "reason=" + out.reason + " candidate=" + (out.trace != null ? 1 : 0)
      + " verified=0 src=" + (siteA != null ? siteA.tile : -1)
      + " dst=" + (siteB != null ? siteB.tile : -1)
      + " route=" + out.route + " sleeve_a=" + out.sleeve_a
      + " sleeve_b=" + out.sleeve_b + " hops=" + out.hops
      + " expanded=" + out.expanded + " existing=" + out.existing
      + " pending=" + out.pending + " occupied=" + out.obstacles
      + " blocked_tile=" + out.blocked_tile + " ops=" + out.ops
      + " join=" + out.join + " road_queries=" + out.road_queries
      + " edge_queries=" + out.edge_queries + " cache_hits=" + out.cache_hits
      + " fast_reason=" + out.fast_reason + " fast_ops=" + out.fast_ops
      + " fast_variants=" + out.fast_variants
      + " fast_bends=" + out.fast_bends + " fast_blocked=" + out.fast_blocked
      + " fast_rejections=" + out.fast_rejections
      + " attempt_cap=42000 search_cap=35000 pair_cap=180000");
  out.ops = OpexOpsMeasureEnd(beginMark);
  /* Emergency guard: should remain unreachable with the reserved 4k.
   * The ordinary log above already followed the definitive 38k gate. */
  if (out.ops >= 42000) { out.trace = null; out.reason = "OPCAP"; }
  return out;
}
