/* ROAD100 V37: ephemeral, resumable, MULTI-SITE best-first ROAD proposal.
 *
 * Caller: require road100_graph_bridge.nut before using these functions.
 *   s = OpexRoad100V37Start([{ a = siteA, b = siteB }, ...], 180000);
 *   s = OpexRoad100V37Step(s, 20000); // once per scheduling opportunity
 *   if (s.status == "CANDIDATE") ... s.trace, s.siteA, s.siteB ...
 *
 * Each site has integer .tile and .front and MUST originate from the real
 * drive-through-stop AITest scanner. No site construction is attempted here.
 * The returned trace is ONLY a geometrical CANDIDATE_NEEDS_VERIFY, NOT a
 * physical route: caller MUST run OpexRoad100LongVerifyTrace on the entire
 * trace, then depot, finance, slot and transaction checks. Never publish a
 * candidate based on this search alone. No Save/Load support or world writes.
 *
 * Search budget is shared across ALL supplied site pairs. The caller owns the
 * 180k pair budget: this module takes at most min(100k, budget-50k) and leaves
 * 50k for verification and admission. Callers must also account for their
 * previous site-scanning costs before passing the remaining pair budget.
 * A step targets <=20k measured opcodes; no single native call can be split.
 */

const ROAD100_V37_SEARCH_MAX_OPS = 100000;
const ROAD100_V37_RESERVE_OPS = 50000;
const ROAD100_V37_MAX_PAIR_OPS = 180000;
const ROAD100_V37_MAX_SLICE_OPS = 20000;
const ROAD100_V37_MAX_SITE_PAIRS = 3;
const ROAD100_V37_MAX_STATES = 768;
/* Must exceed the 190-edge longest legal trace, otherwise long-distance
 * markets would be impossible even with no branches. */
const ROAD100_V37_MAX_EXPANSIONS = 256;
const ROAD100_V37_MAX_DEPTH = 189;
const ROAD100_V37_REAL_EDGE_COST = 3;
const ROAD100_V37_MISSING_EDGE_COST = 11;
const ROAD100_V37_TURN_COST = 2;
/* Goal-directed weighted best-first, NOT a claim of shortest-path optimality.
 * Lower weights over-explore near the source under the 100k search budget. */
const ROAD100_V37_HEURISTIC_WEIGHT = 9;

function OpexRoad100V37Distance(ax, ay, bx, by)
{
  local dx = ax - bx;
  local dy = ay - by;
  if (dx < 0) dx = -dx;
  if (dy < 0) dy = -dy;
  return dx + dy;
}

/* Heap entries are INDICES into stable nodes[]. Never store a node reference
 * as a parent: index 0 is valid and only -1 means "no parent". */
function OpexRoad100V37Less(s, ai, bi)
{
  local a = s.nodes[ai];
  local b = s.nodes[bi];
  if (a.f != b.f) return a.f < b.f;
  if (a.h != b.h) return a.h < b.h;
  if (a.g != b.g) return a.g < b.g;
  if (a.depth != b.depth) return a.depth < b.depth;
  if (a.pairIndex != b.pairIndex) return a.pairIndex < b.pairIndex;
  if (a.tile != b.tile) return a.tile < b.tile;
  return ai < bi;
}

function OpexRoad100V37Push(s, nodeIndex)
{
  local heap = s.open;
  heap.append(nodeIndex);
  local i = heap.len() - 1;
  while (i > 0) {
    local parentIndex = (i - 1) / 2;
    if (!OpexRoad100V37Less(s, heap[i], heap[parentIndex])) break;
    local swap = heap[i]; heap[i] = heap[parentIndex]; heap[parentIndex] = swap;
    i = parentIndex;
  }
}

function OpexRoad100V37Pop(s)
{
  if (s.open.len() == 0) return -1;
  local root = s.open[0];
  local tail = s.open.pop();
  if (s.open.len() == 0) return root;
  s.open[0] = tail;
  local i = 0;
  while (true) {
    local left = i * 2 + 1;
    if (left >= s.open.len()) break;
    local right = left + 1;
    local pick = left;
    if (right < s.open.len() &&
        OpexRoad100V37Less(s, s.open[right], s.open[left])) pick = right;
    if (!OpexRoad100V37Less(s, s.open[pick], s.open[i])) break;
    local swap = s.open[i]; s.open[i] = s.open[pick]; s.open[pick] = swap;
    i = pick;
  }
  return root;
}

function OpexRoad100V37PairKey(pairIndex, tile, direction)
{
  /* No multiplication by map area: avoid signed-integer overflow on large maps. */
  return pairIndex + ":" + tile + ":" + direction;
}

function OpexRoad100V37Ancestor(s, nodeIndex, tile)
{
  /* The explicit parent walk prevents simple cycles in every proposed trace;
   * depth is capped, as are global states and expansions. */
  for (local p = nodeIndex; p >= 0; p = s.nodes[p].parentIndex)
    if (s.nodes[p].tile == tile) return true;
  return false;
}

function OpexRoad100V37SitePair(entry)
{
  if (entry == null || typeof entry != "table") return null;
  local a = ("a" in entry) ? entry.a : (("siteA" in entry) ? entry.siteA : null);
  local b = ("b" in entry) ? entry.b : (("siteB" in entry) ? entry.siteB : null);
  if (a == null || b == null || typeof a != "table" || typeof b != "table" ||
      !("tile" in a) || !("front" in a) ||
      !("tile" in b) || !("front" in b) ||
      typeof a.tile != "integer" || typeof a.front != "integer" ||
      typeof b.tile != "integer" || typeof b.front != "integer" ||
      !AIMap.IsValidTile(a.tile) || !AIMap.IsValidTile(a.front) ||
      !AIMap.IsValidTile(b.tile) || !AIMap.IsValidTile(b.front) ||
      AIMap.DistanceManhattan(a.tile, a.front) != 1 ||
      AIMap.DistanceManhattan(b.tile, b.front) != 1 ||
      a.tile == b.tile || a.front == b.front ||
      AIMap.DistanceManhattan(a.tile, b.tile) > 190) return null;
  /* Ephemeral references preserve EXACT caller site identity (including
   * catchment value). Nothing here is intended for Save/Load. */
  return { a = a, b = b,
      ax = AIMap.GetTileX(a.front), ay = AIMap.GetTileY(a.front),
      bx = AIMap.GetTileX(b.front), by = AIMap.GetTileY(b.front) };
}

function OpexRoad100V37Start(sitePairs, budget)
{
  local cap = typeof budget == "integer" ? budget : 0;
  if (cap > ROAD100_V37_MAX_PAIR_OPS) cap = ROAD100_V37_MAX_PAIR_OPS;
  local searchCap = cap - ROAD100_V37_RESERVE_OPS;
  if (searchCap > ROAD100_V37_SEARCH_MAX_OPS)
    searchCap = ROAD100_V37_SEARCH_MAX_OPS;
  if (searchCap < 0) searchCap = 0;
  local pairs = [];
  if (sitePairs != null && typeof sitePairs == "array") {
    foreach (entry in sitePairs) {
      if (pairs.len() >= ROAD100_V37_MAX_SITE_PAIRS) break;
      local normalized = OpexRoad100V37SitePair(entry);
      if (normalized != null) pairs.append(normalized);
    }
  }
  return { status = "PENDING",
      reason = searchCap == 0 ? "NO_SEARCH_BUDGET" :
          (pairs.len() == 0 ? "NO_SITES" : "SEARCHING"),
      candidate = false, verified = false, trace = null, pairIndex = -1,
      siteA = null, siteB = null,
      route = 0, existing = 0, pending = 0,
      pairs = pairs, seedCursor = 0, nodes = [], open = [], bestG = {},
      cache = OpexRoad100GBCache(), searchLimit = searchCap,
      searchOps = 0, slices = 0, expanded = 0, states = 0,
      width = AIMap.GetMapSizeX(), height = AIMap.GetMapSizeY(),
      startDate = AIDate.GetCurrentDate() };
}

/* Pure geometric reconstruction. The two terminal stop-front links are
 * included, never inferred from the search's interior path. No claim of
 * constructability is made from cached real-road or speculative edges. */
function OpexRoad100V37Candidate(s, nodeIndex)
{
  local node = s.nodes[nodeIndex];
  local pair = s.pairs[node.pairIndex];
  if (node.tile != pair.b.front || node.depth + 1 < 43 ||
      node.depth + 1 > 190) return false;
  local finalReal = OpexRoad100GBRoadEdge(pair.b.front, pair.b.tile, s.cache);
  local finalDirection = pair.b.tile - pair.b.front;
  if (node.direction != finalDirection &&
      !(node.incomingReal && finalReal) &&
      !OpexRoad100GBFlat(pair.b.front, s.cache)) return false;
  local reversed = [];
  for (local p = nodeIndex; p >= 0; p = s.nodes[p].parentIndex)
    reversed.append(s.nodes[p].tile);
  if (reversed.len() == 0 || reversed[reversed.len() - 1] != pair.a.front)
    return false;
  local seen = {};
  local trace = [];
  local prev = pair.a.tile;
  seen.rawset(prev, true);
  for (local i = reversed.len() - 1; i >= 0; i--) {
    local next = reversed[i];
    if (!AIMap.IsValidTile(next) ||
        AIMap.DistanceManhattan(prev, next) != 1 || next in seen ||
        OpexRoad100GBOccupied(next, pair.a.tile, pair.b.tile, s.cache))
      return false;
    seen.rawset(next, true);
    trace.append({ from = prev, to = next });
    prev = next;
  }
  if (pair.b.tile in seen ||
      AIMap.DistanceManhattan(prev, pair.b.tile) != 1) return false;
  trace.append({ from = prev, to = pair.b.tile });
  if (trace.len() < 43 || trace.len() > 190 ||
      trace[0].to != pair.a.front ||
      trace[trace.len() - 1].from != pair.b.front ||
      !OpexRoadOnDtAxis(pair.a.tile, pair.a.front, trace[0].to) ||
      !OpexRoadOnDtAxis(pair.b.tile, pair.b.front,
          trace[trace.len() - 1].from)) return false;
  s.trace = trace;
  s.pairIndex = node.pairIndex;
  s.siteA = pair.a;
  s.siteB = pair.b;
  s.route = trace.len();
  s.existing = node.existing + (finalReal ? 1 : 0);
  s.pending = trace.len() - s.existing;
  s.candidate = true;
  s.verified = false;
  s.reason = "CANDIDATE_NEEDS_VERIFY";
  s.status = "CANDIDATE";
  return true;
}

/* Incremental multi-source/multi-goal A*: every site pair owns its own goal,
 * with all roots in a SHARED best-first heap. Real edge = bidirectional native
 * ROAD connection via OpexRoad100GBRoadEdge. Missing = HYPOTHETICAL, more
 * expensive; BuildRoad and AITestMode are forbidden in this module. */
function OpexRoad100V37Step(s, quotaOps = ROAD100_V37_MAX_SLICE_OPS)
{
  if (s == null || typeof s != "table" || !("status" in s) ||
      s.status != "PENDING") return s;
  local quota = typeof quotaOps == "integer" ? quotaOps : ROAD100_V37_MAX_SLICE_OPS;
  if (quota > ROAD100_V37_MAX_SLICE_OPS) quota = ROAD100_V37_MAX_SLICE_OPS;
  if (quota <= 0) return s;
  if (s.pairs.len() == 0) {
    s.status = "NO_PATH"; s.reason = "NO_SITES";
    return s;
  }
  if (AIMap.GetMapSizeX() != s.width || AIMap.GetMapSizeY() != s.height ||
      AIDate.GetCurrentDate() - s.startDate > 30) {
    s.status = "NO_PATH"; s.reason = "WORLD_OR_AGE_CHANGED";
    return s;
  }
  local remaining = s.searchLimit - s.searchOps;
  if (remaining <= 1200) {
    s.status = "OPCAP"; s.reason = "SEARCH_OPCAP";
    return s;
  }
  if (quota > remaining - 800) quota = remaining - 800;
  if (quota <= 0) {
    s.status = "OPCAP"; s.reason = "SEARCH_OPCAP";
    return s;
  }
  local mark = OpexOpsMeasureBegin();
  local dirs = [1, -1, s.width, -s.width];
  local dx = [1, -1, 0, 0];
  local dy = [0, 0, 1, -1];
  /* Seed one root per verified physical site pair. These are distinct goals;
   * the graph never silently connects two different town pairs. */
  while (s.seedCursor < s.pairs.len() &&
      OpexOpsMeasureEnd(mark) < quota - 1500 &&
      s.searchOps + OpexOpsMeasureEnd(mark) < s.searchLimit - 1200) {
    local pairIndex = s.seedCursor++;
    local pair = s.pairs[pairIndex];
    if (!OpexRoad100GBRoadTile(pair.a.tile, s.cache) ||
        !OpexRoad100GBRoadTile(pair.a.front, s.cache) ||
        !OpexRoad100GBRoadTile(pair.b.tile, s.cache) ||
        !OpexRoad100GBRoadTile(pair.b.front, s.cache) ||
        OpexRoad100GBOccupied(pair.a.front, pair.a.tile, pair.b.tile, s.cache) ||
        OpexRoad100GBOccupied(pair.b.front, pair.a.tile, pair.b.tile, s.cache))
      continue;
    local real = OpexRoad100GBRoadEdge(pair.a.tile, pair.a.front, s.cache);
    local direction = pair.a.front - pair.a.tile;
    local directionIndex = direction == 1 ? 0 : direction == -1 ? 1 :
        direction == s.width ? 2 : direction == -s.width ? 3 : -1;
    if (directionIndex < 0) continue;
    local g = real ? ROAD100_V37_REAL_EDGE_COST : ROAD100_V37_MISSING_EDGE_COST;
    local h = OpexRoad100V37Distance(pair.ax, pair.ay, pair.bx, pair.by)
        * ROAD100_V37_HEURISTIC_WEIGHT + ROAD100_V37_REAL_EDGE_COST;
    local index = s.nodes.len();
    s.nodes.append({ tile = pair.a.front, x = pair.ax, y = pair.ay,
        pairIndex = pairIndex, parentIndex = -1, direction = direction,
        depth = 1, g = g, h = h, f = g + h, incomingReal = real,
        existing = real ? 1 : 0, closed = false });
    s.bestG.rawset(OpexRoad100V37PairKey(pairIndex, pair.a.front,
        directionIndex), g);
    OpexRoad100V37Push(s, index);
  }
  while (s.seedCursor >= s.pairs.len() && s.open.len() > 0 &&
      s.expanded < ROAD100_V37_MAX_EXPANSIONS &&
      OpexOpsMeasureEnd(mark) < quota - 1500 &&
      s.searchOps + OpexOpsMeasureEnd(mark) < s.searchLimit - 1200) {
    local index = OpexRoad100V37Pop(s);
    local node = s.nodes[index];
    if (node.closed) continue;
    local directionIndex = node.direction == 1 ? 0 : node.direction == -1 ? 1 :
        node.direction == s.width ? 2 : node.direction == -s.width ? 3 : -1;
    local key = OpexRoad100V37PairKey(node.pairIndex, node.tile, directionIndex);
    if (key in s.bestG && s.bestG[key] < node.g) continue;
    node.closed = true;
    s.expanded++;
    local pair = s.pairs[node.pairIndex];
    if (node.tile == pair.b.front && OpexRoad100V37Candidate(s, index)) break;
    if (node.depth >= ROAD100_V37_MAX_DEPTH - 1) continue;
    for (local d = 0; d < 4; d++) {
      if (OpexOpsMeasureEnd(mark) >= quota - 1200 ||
          s.searchOps + OpexOpsMeasureEnd(mark) >= s.searchLimit - 1000)
        break;
      local nx = node.x + dx[d];
      local ny = node.y + dy[d];
      if (nx < 0 || ny < 0 || nx >= s.width || ny >= s.height) continue;
      local next = node.tile + dirs[d];
      if (!AIMap.IsValidTile(next) || next == pair.a.tile ||
          next == pair.b.tile ||
          (next == pair.b.front && node.depth + 2 < 43) ||
          OpexRoad100V37Ancestor(s, index, next) ||
          OpexRoad100GBOccupied(next, pair.a.tile, pair.b.tile, s.cache))
        continue;
      local toGoal = OpexRoad100V37Distance(nx, ny, pair.bx, pair.by);
      if (node.depth + 2 + toGoal > 190) continue;
      local real = OpexRoad100GBRoadEdge(node.tile, next, s.cache);
      if (!real && (AITile.IsWaterTile(next) || AITile.IsCoastTile(next) ||
          AITile.IsRiverTile(next))) continue;
      local turns = node.direction != dirs[d];
      /* A speculative corner on non-flat terrain is not a viable proposal.
       * Existing physically connected bends remain allowed as-is. */
      if (turns && !(node.incomingReal && real) &&
          !OpexRoad100GBFlat(node.tile, s.cache)) continue;
      local g = node.g + (real ? ROAD100_V37_REAL_EDGE_COST :
          ROAD100_V37_MISSING_EDGE_COST) + (turns ? ROAD100_V37_TURN_COST : 0);
      local newKey = OpexRoad100V37PairKey(node.pairIndex, next, d);
      if (newKey in s.bestG && s.bestG[newKey] <= g) continue;
      if (s.nodes.len() >= ROAD100_V37_MAX_STATES) break;
      local newIndex = s.nodes.len();
      local h = toGoal * ROAD100_V37_HEURISTIC_WEIGHT +
          ROAD100_V37_REAL_EDGE_COST;
      s.nodes.append({ tile = next, x = nx, y = ny,
          pairIndex = node.pairIndex, parentIndex = index, direction = dirs[d],
          depth = node.depth + 1, g = g, h = h, f = g + h,
          incomingReal = real, existing = node.existing + (real ? 1 : 0),
          closed = false });
      s.bestG.rawset(newKey, g);
      OpexRoad100V37Push(s, newIndex);
    }
    if (s.nodes.len() >= ROAD100_V37_MAX_STATES) break;
  }
  s.searchOps += OpexOpsMeasureEnd(mark);
  s.slices++;
  s.states = s.nodes.len();
  if (s.status == "CANDIDATE") return s;
  if (s.states >= ROAD100_V37_MAX_STATES ||
      s.expanded >= ROAD100_V37_MAX_EXPANSIONS) {
    s.status = "NO_PATH";
    s.reason = s.states >= ROAD100_V37_MAX_STATES ? "STATE_CAP" : "EXPANSION_CAP";
  } else if (s.searchOps >= s.searchLimit - 1200) {
    s.status = "OPCAP"; s.reason = "SEARCH_OPCAP";
  } else if (s.seedCursor == s.pairs.len() && s.open.len() == 0) {
    s.status = "NO_PATH"; s.reason = "FRONTIER_EXHAUSTED";
  }
  /* A non-terminal PENDING result is a checkpoint only, not a trace. */
  return s;
}
