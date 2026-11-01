/* ROAD100 sparse corridor, independent experimental trace builder.
 *
 * A small, deterministic set of routes joins road-front continuations via
 * sparse anchors spaced about ten tiles apart. Each gap explores at most
 * 48 local states (bounded box), favouring already connected road edges.
 * Only completed traces receive AITestMode edge probes. A failed probe
 * excludes that edge for one local repair attempt; alternatives have
 * independent visited sets. Nothing is constructed here.
 *
 * The caller must explicitly load and opt into this file. A returned trace
 * is an array of {from, to} edges compatible with LongVerifyTrace, and is
 * still subject to LongVerifyTrace, depot preflight and the real cash quote.
 */

function OpexRoad100SparseUsable(tile, siteA, siteB)
{
  if (!AIMap.IsValidTile(tile) || tile == siteA.tile || tile == siteB.tile)
    return false;
  if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile) ||
      AITile.IsStationTile(tile)) return false;
  return AIRoad.IsRoadTile(tile) || AITile.IsBuildable(tile);
}

/* No speculative new turn is permitted on a nonflat tile. This is a
 * conservative restriction even when two existing bits might work. */
function OpexRoad100SparseTurn(prev, current, next)
{
  if (prev == null) return true;
  return current - prev == next - current ||
      AITile.GetSlope(current) == AITile.SLOPE_FLAT;
}

/* Local gap search, not an end-to-end A*. Nodes are keyed by tile plus
 * entering direction: a turn may be possible from one approach but not
 * another. The global occupied set protects the full assembled trace. */
function OpexRoad100SparseGap(source, target, incoming, occupied, banned,
                                  siteA, siteB, mark, ceiling)
{
  local out = { tiles = null, reason = "NO_GAP", expanded = 0,
      flat_reject = 0, road_links = 0 };
  local sx = AIMap.GetTileX(source);
  local sy = AIMap.GetTileY(source);
  local tx = AIMap.GetTileX(target);
  local ty = AIMap.GetTileY(target);
  local left = (sx < tx ? sx : tx) - 5;
  local right = (sx > tx ? sx : tx) + 5;
  local top = (sy < ty ? sy : ty) - 5;
  local bottom = (sy > ty ? sy : ty) + 5;
  if (left < 0) left = 0;
  if (top < 0) top = 0;
  if (right >= AIMap.GetMapSizeX()) right = AIMap.GetMapSizeX() - 1;
  if (bottom >= AIMap.GetMapSizeY()) bottom = AIMap.GetMapSizeY() - 1;
  local width = AIMap.GetMapSizeX();
  local dx = [1, -1, 0, 0];
  local dy = [0, 0, 1, -1];
  local stride = [1, -1, width, -width];
  local nodes = [{ tile = source, prev = -1, step = incoming, cost = 0,
      rank = 3 * AIMap.DistanceManhattan(source, target), depth = 0,
      closed = false }];
  local visited = {};
  visited.rawset(source * 4 + (incoming == 1 ? 0 : incoming == -1 ? 1 :
      incoming == width ? 2 : 3), 0);
  for (local scan = 0; scan < 48; scan++) {
    if (OpexOpsMeasureEnd(mark) >= ceiling) {
      out.reason = "OPCAP"; return out;
    }
    local best = -1;
    for (local n = 0; n < nodes.len(); n++) {
      if (nodes[n].closed) continue;
      if (best < 0 || nodes[n].rank < nodes[best].rank ||
          (nodes[n].rank == nodes[best].rank &&
           nodes[n].cost < nodes[best].cost)) best = n;
    }
    if (best < 0) return out;
    nodes[best].closed = true;
    local current = nodes[best];
    out.expanded++;
    if (current.tile == target) {
      local reversed = [];
      local cursor = best;
      while (cursor >= 0) {
        reversed.append(nodes[cursor].tile);
        cursor = nodes[cursor].prev;
      }
      out.tiles = [];
      for (local back = reversed.len() - 1; back >= 0; back--)
        out.tiles.append(reversed[back]);
      out.reason = "OK";
      return out;
    }
    if (current.depth >= 19) continue;
    for (local d = 0; d < 4; d++) {
      local nx = AIMap.GetTileX(current.tile) + dx[d];
      local ny = AIMap.GetTileY(current.tile) + dy[d];
      if (nx < left || nx > right || ny < top || ny > bottom) continue;
      local next = current.tile + stride[d];
      if (next in banned || (next != target && next in occupied) ||
          !OpexRoad100SparseUsable(next, siteA, siteB)) continue;
      if (current.step != stride[d] &&
          AITile.GetSlope(current.tile) != AITile.SLOPE_FLAT) {
        out.flat_reject++;
        continue;
      }
      local connected = AIRoad.AreRoadTilesConnected(current.tile, next) &&
          AIRoad.AreRoadTilesConnected(next, current.tile);
      if (connected) out.road_links++;
      local stepCost = connected ? 1 : 4;
      if (current.step != stride[d]) stepCost += 2;
      local cost = current.cost + stepCost;
      local stateKey = next * 4 + d;
      if (stateKey in visited && nodes[visited[stateKey]].cost <= cost)
        continue;
      local rank = cost + 3 * AIMap.DistanceManhattan(next, target);
      nodes.append({ tile = next, prev = best, step = stride[d], cost = cost,
          rank = rank, depth = current.depth + 1, closed = false });
      visited.rawset(stateKey, nodes.len() - 1);
    }
  }
  out.reason = "NODE_CAP";
  return out;
}

/* Pick a waypoint near the straight sparse lattice. A connected, flat
 * existing road receives a strong bonus, allowing the local search to
 * follow useful town streets without demanding an all-road route. */
function OpexRoad100SparseAnchor(x, y, lateral, alongX, source, goal,
                                     occupied, banned, siteA, siteB)
{
  local chosen = null;
  local best = 999999;
  for (local off = -3; off <= 3; off++) {
    for (local cross = -2; cross <= 2; cross++) {
      local nx = x + (alongX ? off : lateral + cross);
      local ny = y + (alongX ? lateral + cross : off);
      if (nx < 0 || ny < 0 || nx >= AIMap.GetMapSizeX() ||
          ny >= AIMap.GetMapSizeY()) continue;
      local tile = AIMap.GetTileIndex(nx, ny);
      if (tile in occupied || tile in banned ||
          !OpexRoad100SparseUsable(tile, siteA, siteB) ||
          AIMap.DistanceManhattan(source, tile) > 16 ||
          AIMap.DistanceManhattan(tile, goal) >
              AIMap.DistanceManhattan(source, goal) + 6) continue;
      local onRoad = AIRoad.IsRoadTile(tile);
      local flat = AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
      local score = 3 * ((off < 0 ? -off : off) +
          (cross < 0 ? -cross : cross));
      if (onRoad) score -= 5;
      if (flat) score -= 2;
      if (score < best) {
        best = score;
        chosen = tile;
      }
    }
  }
  return chosen;
}

/* A single candidate has its own occupied set, so one speculative
 * routing attempt never contaminates a different corridor candidate. */
function OpexRoad100SparseTrial(siteA, siteB, variant, banned, mark, ceiling)
{
  local out = { trace = null, reason = "NO_ROUTE", expanded = 0,
      anchors = 0, road_links = 0, flat_reject = 0 };
  local startStep = siteA.front - siteA.tile;
  local finishStep = siteB.front - siteB.tile;
  local launch = siteA.front + startStep;
  local approach = siteB.front + finishStep;
  if (!AIMap.IsValidTile(launch) || !AIMap.IsValidTile(approach) ||
      AIMap.DistanceManhattan(siteA.front, launch) != 1 ||
      AIMap.DistanceManhattan(siteB.front, approach) != 1 ||
      launch == approach || launch == siteB.front ||
      approach == siteA.front || launch in banned || approach in banned ||
      !OpexRoad100SparseUsable(launch, siteA, siteB) ||
      !OpexRoad100SparseUsable(approach, siteA, siteB)) {
    out.reason = "FRONT_ESCAPE"; return out;
  }
  local occupied = {};
  occupied.rawset(siteA.tile, true);
  occupied.rawset(siteA.front, true);
  occupied.rawset(siteB.front, true);
  occupied.rawset(siteB.tile, true);
  local path = [siteA.tile, siteA.front, launch];
  occupied.rawset(launch, true);
  local dx = AIMap.GetTileX(approach) - AIMap.GetTileX(launch);
  local dy = AIMap.GetTileY(approach) - AIMap.GetTileY(launch);
  local distance = AIMap.DistanceManhattan(launch, approach);
  local gaps = (distance + 9) / 10;
  if (gaps < 1) gaps = 1;
  if (gaps > 18) { out.reason = "ANCHOR_CAP"; return out; }
  local alongX = (dx >= 0 ? dx : -dx) >= (dy >= 0 ? dy : -dy);
  local lane = variant == 0 ? 0 : variant == 1 ? 3 : variant == 2 ? -3 : 5;
  local current = launch;
  local incoming = startStep;
  for (local g = 1; g <= gaps; g++) {
    if (OpexOpsMeasureEnd(mark) >= ceiling || path.len() > 180) {
      out.reason = "OPCAP_OR_LENGTH"; return out;
    }
    local target = approach;
    if (g < gaps) {
      local x = AIMap.GetTileX(launch) + dx * g / gaps;
      local y = AIMap.GetTileY(launch) + dy * g / gaps;
      target = OpexRoad100SparseAnchor(x, y, lane, alongX, current,
          approach, occupied, banned, siteA, siteB);
      if (target == null) { out.reason = "NO_ANCHOR"; return out; }
    }
    /* The target is allowed even though it is already reserved as a
     * mandatory endpoint only on the final segment. */
    local gap = OpexRoad100SparseGap(current, target, incoming,
        occupied, banned, siteA, siteB, mark, ceiling);
    out.expanded += gap.expanded;
    out.road_links += gap.road_links;
    out.flat_reject += gap.flat_reject;
    if (gap.tiles == null) {
      out.reason = "GAP_" + gap.reason;
      return out;
    }
    out.anchors++;
    for (local i = 1; i < gap.tiles.len(); i++) {
      local next = gap.tiles[i];
      if (next in occupied || path.len() >= 189 ||
          !OpexRoad100SparseTurn(path[path.len() - 2],
              path[path.len() - 1], next)) {
        out.reason = "CYCLE_OR_TURN"; return out;
      }
      incoming = next - path[path.len() - 1];
      path.append(next);
      occupied.rawset(next, true);
    }
    current = target;
  }
  if (current != approach) { out.reason = "ENDPOINT"; return out; }
  if (!OpexRoad100SparseTurn(path[path.len() - 2], approach,
      siteB.front) || !OpexRoad100SparseTurn(approach, siteB.front,
      siteB.tile)) {
    out.reason = "END_TURN"; return out;
  }
  path.append(siteB.front);
  path.append(siteB.tile);
  if (path.len() - 1 < 80 || path.len() - 1 > 190 ||
      path[0] != siteA.tile || path[1] != siteA.front ||
      path[2] != launch || path[path.len() - 3] != approach ||
      path[path.len() - 2] != siteB.front ||
      path[path.len() - 1] != siteB.tile) {
    out.reason = "LENGTH_OR_ENDPOINT"; return out;
  }
  local trace = [];
  for (local p = 1; p < path.len(); p++)
    trace.append({ from = path[p - 1], to = path[p] });
  out.trace = trace;
  out.reason = "OK";
  return out;
}

/* One physical AITest per missing edge on a completed candidate. This
 * reports the first offending tile; the caller may repair it once. AITest
 * is noncumulative, so a success is STILL only a speculative corridor. */
function OpexRoad100SparseTestTrace(trace, mark, ceiling)
{
  local out = { ok = false, reason = "UNBUILDABLE", bad_tile = -1,
      tested = 0, existing = 0, missing = 0 };
  for (local i = 0; i < trace.len(); i++) {
    if (OpexOpsMeasureEnd(mark) >= ceiling) {
      out.reason = "OPCAP"; return out;
    }
    local edge = trace[i];
    if (!AIMap.IsValidTile(edge.from) || !AIMap.IsValidTile(edge.to) ||
        AIMap.DistanceManhattan(edge.from, edge.to) != 1) {
      out.reason = "EDGE"; return out;
    }
    if (AIRoad.AreRoadTilesConnected(edge.from, edge.to) &&
        AIRoad.AreRoadTilesConnected(edge.to, edge.from)) {
      out.existing++;
      continue;
    }
    local allowed = false;
    { local test = AITestMode(); allowed = AIRoad.BuildRoad(edge.from, edge.to); }
    out.tested++;
    out.missing++;
    if (!allowed) {
      out.bad_tile = edge.to;
      return out;
    }
  }
  out.ok = true;
  out.reason = "EDGES_TESTED";
  return out;
}

/* Entry point: mark belongs to the whole builder, including the site scans.
 * The local 100k allowance therefore starts from the CURRENT global counter,
 * never from zero. Reserve 65k of the builder limit for LongVerifyTrace,
 * depot preflight and finance. Both limits are checked within the loops;
 * the caller must also enforce its own 150k-per-pair total budget. */
function OpexRoad100SparseCorridorTrace(siteA, siteB, mark, limitOps)
{
  local startMark = OpexOpsMeasureBegin();
  local out = { trace = null, reason = "PRECHECK", ops = 0,
      stats = { trials = 0, repairs = 0, anchors = 0, expanded = 0,
          road_links = 0, flat_reject = 0, tested = 0, existing = 0,
          missing = 0, rejected = 0, candidate_edges = 0 } };
  if (siteA == null || siteB == null || mark == null ||
      !("tile" in siteA) || !("front" in siteA) ||
      !("tile" in siteB) || !("front" in siteB) ||
      !AIMap.IsValidTile(siteA.tile) || !AIMap.IsValidTile(siteB.tile) ||
      !AIMap.IsValidTile(siteA.front) || !AIMap.IsValidTile(siteB.front)) {
    out.ops = OpexOpsMeasureEnd(startMark);
    return out;
  }
  if (limitOps < 50000 || !AIRoad.IsRoadTile(siteA.tile) ||
      !AIRoad.IsRoadTile(siteB.tile) ||
      !AIRoad.IsRoadTile(siteA.front) || !AIRoad.IsRoadTile(siteB.front) ||
      AIMap.DistanceManhattan(siteA.tile, siteB.tile) < 80 ||
      AIMap.DistanceManhattan(siteA.tile, siteB.tile) > 170 ||
      AIMap.DistanceManhattan(siteA.tile, siteA.front) != 1 ||
      AIMap.DistanceManhattan(siteB.tile, siteB.front) != 1 ||
      !AIRoad.AreRoadTilesConnected(siteA.tile, siteA.front) ||
      !AIRoad.AreRoadTilesConnected(siteA.front, siteA.tile) ||
      !AIRoad.AreRoadTilesConnected(siteB.front, siteB.tile) ||
      !AIRoad.AreRoadTilesConnected(siteB.tile, siteB.front)) {
    out.reason = "FRONT_OR_DISTANCE";
    out.ops = OpexOpsMeasureEnd(startMark);
    return out;
  }
  local globalAtEntry = OpexOpsMeasureEnd(mark);
  local ceiling = globalAtEntry + 100000;
  if (ceiling > limitOps - 65000) ceiling = limitOps - 65000;
  if (ceiling <= globalAtEntry) {
    out.reason = "OPCAP";
    out.ops = OpexOpsMeasureEnd(startMark);
    return out;
  }
  local bestTrace = null;
  local bestCost = 999999;
  out.reason = "NO_CORRIDOR";
  for (local variant = 0; variant < 4; variant++) {
    if (OpexOpsMeasureEnd(startMark) >= 105000 ||
        OpexOpsMeasureEnd(mark) >= ceiling) {
      out.reason = bestTrace == null ? "OPCAP" : "OK";
      break;
    }
    local banned = {};
    for (local attempt = 0; attempt < 2; attempt++) {
      if (OpexOpsMeasureEnd(mark) >= ceiling ||
          OpexOpsMeasureEnd(startMark) >= 105000) break;
      out.stats.trials++;
      local trial = OpexRoad100SparseTrial(siteA, siteB, variant,
          banned, mark, ceiling);
      out.stats.anchors += trial.anchors;
      out.stats.expanded += trial.expanded;
      out.stats.road_links += trial.road_links;
      out.stats.flat_reject += trial.flat_reject;
      if (trial.trace == null) {
        if (trial.reason == "GAP_OPCAP") out.reason = "OPCAP";
        break;
      }
      out.stats.candidate_edges += trial.trace.len();
      local check = OpexRoad100SparseTestTrace(trial.trace, mark, ceiling);
      out.stats.tested += check.tested;
      out.stats.rejected += check.ok ? 0 : 1;
      if (check.ok) {
        local cost = check.missing * 4 + trial.trace.len();
        if (cost < bestCost) {
          bestCost = cost;
          bestTrace = trial.trace;
          out.stats.existing = check.existing;
          out.stats.missing = check.missing;
        }
        out.reason = "OK";
        break;
      }
      if (check.reason == "OPCAP") { out.reason = "OPCAP"; break; }
      if (attempt + 1 >= 2 || check.bad_tile < 0 ||
          check.bad_tile == siteB.tile ||
          check.bad_tile == siteB.front || check.bad_tile == siteA.front) break;
      banned.rawset(check.bad_tile, true);
      out.stats.repairs++;
    }
    /* A validated first candidate leaves the widest possible remaining
     * budget to LongVerifyTrace, depot checks and the complete cash quote. */
    if (bestTrace != null) break;
  }
  out.ops = OpexOpsMeasureEnd(startMark);
  if (bestTrace != null && out.ops <= 110000 &&
      OpexOpsMeasureEnd(mark) < ceiling) {
    out.trace = bestTrace;
    out.reason = "OK";
  } else if (out.reason == "OK") out.reason = "OPCAP";
  return out;
}

/* ROAD100-35 — independent portal-stitch experiment. V33 entry points above
 * are deliberately unchanged. This module finds a SPECULATIVE simple trace;
 * the caller must still run LongVerifyTrace, depot preflight, the real quote,
 * and transactional OpexBuildRoadRoute. No BuildRoad or AITest is done here.
 *
 * Two <=16-node searches follow only existing, bidirectionally linked
 * streets. The middle is a chain of <=12 short cardinal bands, not a
 * full-map A*. Each band has <=3 geometric attempts (one 0/+/− lane).
 * All state is call-local, never shared with V33's caches or ban tables. */
function OpexRoad100PortalUsable(tile, siteA, siteB)
{
  if (!AIMap.IsValidTile(tile) || tile == siteA.tile || tile == siteB.tile ||
      AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile) ||
      AITile.IsStationTile(tile)) return false;
  return AIRoad.IsRoadTile(tile) || AITile.IsBuildable(tile);
}

/* Existing-road breadth-first search, at most 16 expanded street tiles,
 * 9 steps deep. Keep three endpoints with distinct departure branches first.
 * A front is not forced to continue straight: a REAL road corner is valid. */
function OpexRoad100PortalSleeve(site, otherSite, siteA, siteB, mark, ceiling)
{
  local out = { portals = [], reason = "FRONT_ESCAPE", expanded = 0,
      road_links = 0 };
  local start = site.front;
  local width = AIMap.GetMapSizeX();
  local dirs = [1, -1, width, -width];
  local nodes = [{ tile = start, prevIndex = -1, depth = 0, branch = -1 }];
  local seen = {};
  seen.rawset(start, true);
  seen.rawset(site.tile, true);
  local cursor = 0;
  while (cursor < nodes.len() && out.expanded < 16) {
    if (OpexOpsMeasureEnd(mark) >= ceiling) {
      out.reason = "OPCAP"; return out;
    }
    local node = nodes[cursor];
    local currentIndex = cursor;
    cursor++;
    out.expanded++;
    if (node.depth >= 9) continue;
    for (local d = 0; d < 4; d++) {
      local tile = node.tile + dirs[d];
      if (!AIMap.IsValidTile(tile) || tile in seen ||
          AIMap.DistanceManhattan(node.tile, tile) != 1 ||
          tile == otherSite.front ||
          !OpexRoad100PortalUsable(tile, siteA, siteB) ||
          !AIRoad.IsRoadTile(tile)) continue;
      if (!AIRoad.AreRoadTilesConnected(node.tile, tile) ||
          !AIRoad.AreRoadTilesConnected(tile, node.tile)) continue;
      seen.rawset(tile, true);
      out.road_links++;
      local child = { tile = tile, prevIndex = currentIndex,
          depth = node.depth + 1,
          branch = node.depth == 0 ? d : node.branch };
      nodes.append(child);
    }
  }
  /* Rank street portals by progress AND useful existing-road depth. */
  local ranked = [];
  for (local n = 1; n < nodes.len(); n++) {
    local leaf = nodes[n];
    local score = AIMap.DistanceManhattan(leaf.tile, otherSite.front) * 4
        - leaf.depth * 5;
    local at = 0;
    while (at < ranked.len() &&
        (ranked[at].score < score ||
         (ranked[at].score == score && ranked[at].index < n))) at++;
    ranked.insert(at, { index = n, score = score });
  }
  local chosenBranches = {};
  for (local pass = 0; pass < 2 && out.portals.len() < 3; pass++) {
    foreach (rankedLeaf in ranked) {
      if (out.portals.len() >= 3) break;
      local leaf = nodes[rankedLeaf.index];
      if (pass == 0 && leaf.branch in chosenBranches) continue;
      local already = false;
      foreach (prior in out.portals) {
        if (prior.tile == leaf.tile) { already = true; break; }
      }
      if (already) continue;
      local reversed = [];
      local back = rankedLeaf.index;
      while (back >= 0) {
        reversed.append(nodes[back].tile);
        back = nodes[back].prevIndex;
      }
      local tiles = [];
      for (local i = reversed.len() - 1; i >= 0; i--)
        tiles.append(reversed[i]);
      out.portals.append({ tile = leaf.tile, tiles = tiles,
          depth = leaf.depth, branch = leaf.branch });
      chosenBranches.rawset(leaf.branch, true);
    }
  }
  /* The front itself is an existing road tile and a legitimate zero-step
   * portal if the city street has no continuation. It does NOT assert an
   * imaginary outgoing road: the first new edge still needs VerifyTrace. */
  if (out.portals.len() < 3)
    out.portals.append({ tile = start, tiles = [start],
        depth = 0, branch = -1 });
  if (out.portals.len() > 0) out.reason = "OK";
  return out;
}

/* Append at most one Manhattan band via one pivot. No global search. The
 * optional offset is <=4 and creates at most two extra flat turns. A tile
 * is never accepted merely because a neighbouring road tile exists:
 * only AreRoadTilesConnected in BOTH directions counts as an old road link.
 * Every other edge remains to be checked with AITest by LongVerifyTrace. */
function OpexRoad100PortalBand(source, target, incoming, shape, occupied,
                               siteA, siteB, mark, ceiling)
{
  local out = { tiles = null, reason = "GAP_GEOMETRY", existing = 0,
      missing = 0, turns = 0 };
  local sx = AIMap.GetTileX(source);
  local sy = AIMap.GetTileY(source);
  local tx = AIMap.GetTileX(target);
  local ty = AIMap.GetTileY(target);
  local points = [[sx, sy]];
  if (sx != tx && sy != ty) {
    if (shape == 0) points.append([tx, sy]);
    else if (shape == 1) points.append([sx, ty]);
    else {
      /* A short offset lane gives a bypass when the direct L is blocked.
       * Every corner still has to be FLAT unless both road links exist. */
      if ((sx > tx ? sx - tx : tx - sx) >=
          (sy > ty ? sy - ty : ty - sy)) {
        local shiftX = tx + (tx >= sx ? -2 : 2);
        if (shiftX == sx || shiftX == tx) shiftX = tx + (tx >= sx ? 2 : -2);
        points.append([shiftX, sy]);
        points.append([shiftX, ty]);
      } else {
        local shiftY = ty + (ty >= sy ? -2 : 2);
        if (shiftY == sy || shiftY == ty) shiftY = ty + (ty >= sy ? 2 : -2);
        points.append([sx, shiftY]);
        points.append([tx, shiftY]);
      }
    }
  }
  points.append([tx, ty]);
  local candidate = [source];
  local localSeen = {};
  localSeen.rawset(source, true);
  local prevStep = incoming;
  local last = source;
  for (local p = 1; p < points.len(); p++) {
    local fromX = points[p - 1][0];
    local fromY = points[p - 1][1];
    local toX = points[p][0];
    local toY = points[p][1];
    if ((fromX != toX && fromY != toY) ||
        (fromX == toX && fromY == toY)) {
      out.reason = "GAP_SHAPE"; return out;
    }
    local stepX = toX == fromX ? 0 : (toX > fromX ? 1 : -1);
    local stepY = toY == fromY ? 0 : (toY > fromY ? 1 : -1);
    local length = (toX > fromX ? toX - fromX : fromX - toX) +
        (toY > fromY ? toY - fromY : fromY - toY);
    if (length > 24 || candidate.len() + length > 190) {
      out.reason = "GAP_LENGTH"; return out;
    }
    for (local k = 1; k <= length; k++) {
      if ((k % 4) == 1 && OpexOpsMeasureEnd(mark) >= ceiling) {
        out.reason = "OPCAP"; return out;
      }
      local nx = fromX + k * stepX;
      local ny = fromY + k * stepY;
      if (nx < 0 || ny < 0 || nx >= AIMap.GetMapSizeX() ||
          ny >= AIMap.GetMapSizeY()) {
        out.reason = "EDGE_MAP"; return out;
      }
      local tile = AIMap.GetTileIndex(nx, ny);
      if ((tile in occupied && tile != target) ||
          tile in localSeen || !OpexRoad100PortalUsable(tile, siteA, siteB)) {
        out.reason = "EDGE_OCCUPIED"; return out;
      }
      local direction = tile - last;
      if (AIMap.DistanceManhattan(tile, last) != 1) {
        out.reason = "EDGE_NONCARDINAL"; return out;
      }
      local connected = AIRoad.IsRoadTile(last) && AIRoad.IsRoadTile(tile) &&
          AIRoad.AreRoadTilesConnected(last, tile) &&
          AIRoad.AreRoadTilesConnected(tile, last);
      if (direction != prevStep) {
        /* Existing corners on slopes are safe only when BOTH incoming
         * and outgoing links are physically present. Otherwise a new road
         * bit requires flat ground at the corner. */
        local oldEntry = last - prevStep;
        local incomingRoad = AIMap.IsValidTile(oldEntry) &&
            AIRoad.IsRoadTile(oldEntry) && AIRoad.IsRoadTile(last) &&
            AIRoad.AreRoadTilesConnected(oldEntry, last) &&
            AIRoad.AreRoadTilesConnected(last, oldEntry);
        if (AITile.GetSlope(last) != AITile.SLOPE_FLAT &&
            !(connected && incomingRoad)) {
          out.reason = "GAP_TURN"; return out;
        }
        out.turns++;
      }
      if (connected) out.existing++;
      else out.missing++;
      candidate.append(tile);
      localSeen.rawset(tile, true);
      last = tile;
      prevStep = direction;
    }
  }
  if (last != target) { out.reason = "GAP_TARGET"; return out; }
  out.tiles = candidate;
  out.reason = "OK";
  return out;
}

/* Source and destination are actual tested DT station tiles and front tiles;
 * unlike V33, no speculative straight launch beyond either front is needed.
 * The existing sleeves and every candidate band use independent visited
 * maps. The caller's shared mark is the absolute hard budget reference. */
function OpexRoad100PortalStitchTrace(siteA, siteB, mark, limitOps)
{
  local localMark = OpexOpsMeasureBegin();
  local out = { trace = null, reason = "PRECHECK",
      reason_detail = "PRECHECK", ops = 0,
      stats = { portals_a = 0, portals_b = 0, expanded_a = 0,
          expanded_b = 0, road_links = 0, portal_pairs = 0,
          bands = 0, alternatives = 0, existing = 0, missing = 0,
          turns = 0, cycles = 0, first_reject = "NONE" } };
  if (siteA == null || siteB == null || mark == null ||
      !("tile" in siteA) || !("front" in siteA) ||
      !("tile" in siteB) || !("front" in siteB) ||
      !AIMap.IsValidTile(siteA.tile) || !AIMap.IsValidTile(siteB.tile) ||
      !AIMap.IsValidTile(siteA.front) || !AIMap.IsValidTile(siteB.front) ||
      !AIRoad.IsRoadTile(siteA.tile) || !AIRoad.IsRoadTile(siteB.tile) ||
      !AIRoad.IsRoadTile(siteA.front) || !AIRoad.IsRoadTile(siteB.front) ||
      AIMap.DistanceManhattan(siteA.tile, siteA.front) != 1 ||
      AIMap.DistanceManhattan(siteB.tile, siteB.front) != 1 ||
      !AIRoad.AreRoadTilesConnected(siteA.tile, siteA.front) ||
      !AIRoad.AreRoadTilesConnected(siteA.front, siteA.tile) ||
      !AIRoad.AreRoadTilesConnected(siteB.tile, siteB.front) ||
      !AIRoad.AreRoadTilesConnected(siteB.front, siteB.tile)) {
    out.reason = "FRONT_ESCAPE";
    out.reason_detail = "DT_FRONT_LINK";
    out.ops = OpexOpsMeasureEnd(localMark);
    return out;
  }
  local centres = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
  if (centres < 80 || centres > 190 || limitOps > 180000 ||
      limitOps < 65000) {
    out.reason = "DISTANCE_OR_LIMIT";
    out.reason_detail = "CENTRES_OR_PAIR_CAP";
    out.ops = OpexOpsMeasureEnd(localMark);
    return out;
  }
  local entry = OpexOpsMeasureEnd(mark);
  local ceiling = entry + 42000;
  if (ceiling > limitOps - 66000) ceiling = limitOps - 66000;
  if (entry >= ceiling) {
    out.reason = "OPCAP";
    out.reason_detail = "NO_RESERVE";
    out.ops = OpexOpsMeasureEnd(localMark);
    return out;
  }
  local fromRoad = OpexRoad100PortalSleeve(siteA, siteB,
      siteA, siteB, mark, ceiling);
  local toRoad = OpexRoad100PortalSleeve(siteB, siteA,
      siteA, siteB, mark, ceiling);
  out.stats.portals_a = fromRoad.portals.len();
  out.stats.portals_b = toRoad.portals.len();
  out.stats.expanded_a = fromRoad.expanded;
  out.stats.expanded_b = toRoad.expanded;
  out.stats.road_links = fromRoad.road_links + toRoad.road_links;
  if (fromRoad.reason != "OK" || toRoad.reason != "OK") {
    out.reason = fromRoad.reason == "OPCAP" || toRoad.reason == "OPCAP"
        ? "OPCAP" : "FRONT_ESCAPE";
    out.reason_detail = fromRoad.reason != "OK" ?
        "PORTAL_A_" + fromRoad.reason : "PORTAL_B_" + toRoad.reason;
    out.ops = OpexOpsMeasureEnd(localMark);
    return out;
  }
  out.reason = "NO_CORRIDOR";
  out.reason_detail = "GAP_UNTRIED";
  /* Three distinct sleeve pairs at most, so alternatives cannot silently
   * multiply to 3x3x12x3. The first complete candidate is returned. */
  local pairChoices = [[0, 0]];
  if (fromRoad.portals.len() > 1) pairChoices.append([1, 0]);
  if (toRoad.portals.len() > 1) pairChoices.append([0, 1]);
  if (pairChoices.len() < 3 && fromRoad.portals.len() > 2)
    pairChoices.append([2, 0]);
  if (pairChoices.len() < 3 && toRoad.portals.len() > 2)
    pairChoices.append([0, 2]);
  for (local pairIndex = 0; pairIndex < pairChoices.len(); pairIndex++) {
    if (OpexOpsMeasureEnd(mark) >= ceiling) {
      out.reason = "OPCAP"; out.reason_detail = "PORTAL_PAIR_BUDGET"; break;
    }
    local ia = pairChoices[pairIndex][0];
    local ib = pairChoices[pairIndex][1];
    out.stats.portal_pairs++;
    local a = fromRoad.portals[ia];
    local b = toRoad.portals[ib];
    local path = [siteA.tile];
    local occupied = {};
    occupied.rawset(siteA.tile, true);
    foreach (tile in a.tiles) {
      if (tile in occupied) break;
      path.append(tile);
      occupied.rawset(tile, true);
    }
    local reserved = {};
    foreach (tile in b.tiles) reserved.rawset(tile, true);
    reserved.rawset(siteB.tile, true);
    local overlaps = false;
    foreach (tile in b.tiles) {
      if (tile in occupied) overlaps = true;
    }
    if (overlaps) {
      out.stats.cycles++;
      out.reason_detail = "PORTAL_OVERLAP";
      continue;
    }
    foreach (tile, unused in reserved) occupied.rawset(tile, true);
    local current = a.tile;
    local incoming = path[path.len() - 1] - path[path.len() - 2];
    local dx = AIMap.GetTileX(b.tile) - AIMap.GetTileX(current);
    local dy = AIMap.GetTileY(b.tile) - AIMap.GetTileY(current);
    local remaining = AIMap.DistanceManhattan(current, b.tile);
    local bands = (remaining + 15) / 16;
    if (bands < 1) bands = 1;
    if (bands > 12) {
      out.reason_detail = "GAP_BAND_CAP"; continue;
    }
    local majorX = (dx >= 0 ? dx : -dx) >= (dy >= 0 ? dy : -dy);
    local failed = false;
    for (local band = 1; band <= bands; band++) {
      if (OpexOpsMeasureEnd(mark) >= ceiling) {
        out.reason = "OPCAP"; out.reason_detail = "GAP_BUDGET";
        failed = true; break;
      }
      local bx = AIMap.GetTileX(a.tile) + (dx * band) / bands;
      local by = AIMap.GetTileY(a.tile) + (dy * band) / bands;
      local success = false;
      local detail = "GAP_NO_ALTERNATIVE";
      for (local mode = 0; mode < 3; mode++) {
        out.stats.alternatives++;
        local offset = mode == 0 ? 0 : mode == 1 ? 2 : -2;
        local tx = band == bands ? AIMap.GetTileX(b.tile) :
            bx + (majorX ? 0 : offset);
        local ty = band == bands ? AIMap.GetTileY(b.tile) :
            by + (majorX ? offset : 0);
        if (tx < 0 || ty < 0 || tx >= AIMap.GetMapSizeX() ||
            ty >= AIMap.GetMapSizeY()) {
          detail = "EDGE_MAP"; continue;
        }
        local target = AIMap.GetTileIndex(tx, ty);
        if (target == current || (target in occupied && target != b.tile)) {
          detail = "EDGE_OCCUPIED"; continue;
        }
        local leg = OpexRoad100PortalBand(current, target,
            incoming, mode, occupied, siteA, siteB, mark, ceiling);
        if (leg.tiles == null) {
          detail = leg.reason;
          if (out.stats.first_reject == "NONE")
            out.stats.first_reject = detail;
          if (detail == "OPCAP") break;
          continue;
        }
        if (path.len() + leg.tiles.len() - 1 + b.tiles.len() > 191) {
          detail = "GAP_TOTAL_LENGTH"; continue;
        }
        for (local t = 1; t < leg.tiles.len(); t++) {
          local nextTile = leg.tiles[t];
          path.append(nextTile);
          occupied.rawset(nextTile, true);
        }
        out.stats.existing += leg.existing;
        out.stats.missing += leg.missing;
        out.stats.turns += leg.turns;
        current = target;
        incoming = path[path.len() - 1] - path[path.len() - 2];
        out.stats.bands++;
        success = true;
        break;
      }
      if (!success) {
        failed = true;
        out.reason_detail = "BAND_" + band + "_" + detail;
        if (detail == "OPCAP") out.reason = "OPCAP";
        break;
      }
    }
    if (failed || current != b.tile) continue;
    /* Attach B's *verified existing-road* sleeve in reverse, then the DT
     * station. Check the join turn and all tile identities before returning. */
    local pathSeen = {};
    foreach (usedTile in path) pathSeen.rawset(usedTile, true);
    for (local t = b.tiles.len() - 2; t >= 0; t--) {
      local nextTile = b.tiles[t];
      if (nextTile in pathSeen) {
        failed = true; out.reason_detail = "END_CYCLE"; break;
      }
      local oldIncoming = current - incoming;
      local bothOld = AIMap.IsValidTile(oldIncoming) &&
          AIRoad.AreRoadTilesConnected(oldIncoming, current) &&
          AIRoad.AreRoadTilesConnected(current, oldIncoming) &&
          AIRoad.AreRoadTilesConnected(current, nextTile) &&
          AIRoad.AreRoadTilesConnected(nextTile, current);
      if (incoming != nextTile - current &&
          AITile.GetSlope(current) != AITile.SLOPE_FLAT &&
          !bothOld) {
        failed = true; out.reason_detail = "END_TURN"; break;
      }
      incoming = nextTile - current;
      current = nextTile;
      path.append(current);
      pathSeen.rawset(current, true);
    }
    if (failed || current != siteB.front) continue;
    if (incoming != siteB.tile - siteB.front &&
        AITile.GetSlope(siteB.front) != AITile.SLOPE_FLAT) {
      out.reason_detail = "END_DT_TURN"; continue;
    }
    path.append(siteB.tile);
    if (path.len() - 1 < 80 || path.len() - 1 > 190 ||
        path[0] != siteA.tile || path[1] != siteA.front ||
        path[path.len() - 2] != siteB.front ||
        path[path.len() - 1] != siteB.tile) {
      out.reason_detail = "LENGTH_OR_ENDPOINT"; continue;
    }
    local seen = {};
    local valid = true;
    for (local n = 0; n < path.len(); n++) {
      if (path[n] in seen ||
          (n > 0 && AIMap.DistanceManhattan(path[n - 1], path[n]) != 1)) {
        valid = false; break;
      }
      seen.rawset(path[n], true);
    }
    if (!valid) {
      out.stats.cycles++;
      out.reason_detail = "CYCLE_OR_EDGE"; continue;
    }
    if (OpexOpsMeasureEnd(mark) >= ceiling) {
      out.reason = "OPCAP"; out.reason_detail = "FINAL_BUDGET"; break;
    }
    local trace = [];
    for (local n = 1; n < path.len(); n++)
      trace.append({ from = path[n - 1], to = path[n] });
    out.trace = trace;
    out.reason = "OK";
    out.reason_detail = "TRACE_UNVERIFIED";
    break;
  }
  out.ops = OpexOpsMeasureEnd(localMark);
  if (OpexOpsMeasureEnd(mark) >= limitOps - 65000 || out.ops > 43000) {
    out.trace = null;
    out.reason = "OPCAP";
    out.reason_detail = "GLOBAL_OR_LOCAL_RESERVE";
  }
  return out;
}
