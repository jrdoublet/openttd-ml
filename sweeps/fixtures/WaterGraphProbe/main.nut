/* C67.5 water graph fixture. The harness stages the exact production sources beside it. */
require("budget.nut");
require("terrain_map.nut");
require("water_graph.nut");
require("builder_water.nut");

function W5Assert(ok, message) {
  if (!ok) throw "C675 FAIL: " + message;
}

/* ASCII map: '~' water, anything else land. Blocked edges model AreWaterTilesConnected false. */
class W5FakeSource {
  w = 0;
  h = 0;
  cells = null;
  blocked = null;
  ops = 0;
  constructor(rows) {
    this.h = rows.len();
    this.w = rows[0].len();
    this.cells = array(this.w * this.h, false);
    for (local y = 0; y < this.h; y++)
      for (local x = 0; x < this.w; x++) this.cells[y * this.w + x] = rows[y][x] == '~';
    this.blocked = {};
  }
  function Width() { return this.w; }
  function Height() { return this.h; }
  function Tick() { return this.ops / 10000; }
  function Mark() { return this.ops; }
  function Spent(mark) { return this.ops - mark; }
  function Remaining() { return 10000; }
  function Water(x, y) { return this.cells[y * this.w + x]; }
  function IsWater(x, y) {
    W5Assert(x >= 0 && y >= 0 && x < this.w && y < this.h, "read out of map");
    this.ops += 50;
    return this.Water(x, y);
  }
  function EdgeKey(x1, y1, x2, y2) {
    local a = y1 * this.w + x1, b = y2 * this.w + x2;
    return a < b ? a * 100000 + b : b * 100000 + a;
  }
  function Block(x1, y1, x2, y2) { this.blocked.rawset(this.EdgeKey(x1, y1, x2, y2), true); }
  function Link(x1, y1, x2, y2) {
    return this.Water(x1, y1) && this.Water(x2, y2) && !(this.EdgeKey(x1, y1, x2, y2) in this.blocked);
  }
  function Connected(x1, y1, x2, y2) {
    W5Assert(abs(x1 - x2) + abs(y1 - y2) == 1, "non-cardinal connection query");
    this.ops += 50;
    return this.Link(x1, y1, x2, y2);
  }
}

/* Exhaustive tile BFS on the fake map: shortest length, or -1 when disconnected. */
function W5Exact(src, ax, ay, bx, by) {
  if (!src.Water(ax, ay) || !src.Water(bx, by)) return -2;
  local seen = {};
  local queue = [ay * src.w + ax];
  seen.rawset(queue[0], 0);
  for (local head = 0; head < queue.len(); head++) {
    local cur = queue[head];
    local x = cur % src.w, y = cur / src.w;
    if (x == bx && y == by) return seen[cur];
    foreach (o in [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      local nx = x + o[0], ny = y + o[1];
      if (nx < 0 || ny < 0 || nx >= src.w || ny >= src.h) continue;
      local key = ny * src.w + nx;
      if ((key in seen) || !src.Link(x, y, nx, ny)) continue;
      seen.rawset(key, seen[cur] + 1);
      queue.append(key);
    }
  }
  return -1;
}

function W5Run(g, src, ax, ay, bx, by, maxBlocks = 100000, maxNodes = 100000) {
  g.Begin(ax, ay, bx, by, maxBlocks, maxNodes);
  for (local i = 0; i < 1000000 && g.Step(2000, src.Tick() + 1000) != "done"; i++) {}
  return g.Result();
}

function W5Corridor(g, src, res, ax, ay, bx, by) {
  local c = OpexWaterCorridor(g, g.CorridorBlocks(res.chain), ax, ay, bx, by, 100000, src);
  for (local i = 0; i < 1000000 && c.Step(2000, src.Tick() + 1000) != "done"; i++) {}
  return c;
}

function W5Check(src, ax, ay, bx, by, expected, label) {
  local g = OpexWaterGraph(64, src);
  local r = W5Run(g, src, ax, ay, bx, by);
  W5Assert(r.status == expected, label + ": " + r.status + " expected " + expected);
  return r;
}

function W5AdverseTests() {
  /* Two basins in one block: high water share is no connection. */
  local basins = W5FakeSource(["~~~~#~~~~~", "~~~~#~~~~~", "~~~~#~~~~~"]);
  W5Check(basins, 0, 0, 3, 2, "connected", "same basin");
  W5Check(basins, 0, 0, 9, 0, "disconnected", "two basins");
  /* Narrow channel through a block border. */
  local channel = W5FakeSource(["##########", "~~~~~~~~~~", "##########"]);
  W5Check(channel, 0, 1, 9, 1, "connected", "channel across border");
  /* Diagonal contact only. */
  local diag = W5FakeSource(["~~~~~#####", "~~~~~#####", "~~~~~#####", "~~~~~#####",
    "~~~~~#####", "#####~~~~~", "#####~~~~~"]);
  W5Check(diag, 0, 0, 9, 6, "disconnected", "diagonal contact");
  /* Island: detour around land, longer than Manhattan. */
  local island = W5FakeSource(["~~~~~~~~~~~~~~~", "~~~~~~~~~~~~~~~", "~~###########~~",
    "~~###########~~", "~~###########~~", "~~~~~~~~~~~~~~~", "~~~~~~~~~~~~~~~"]);
  local r = W5Check(island, 7, 1, 7, 5, "connected", "island detour");
  local c = W5Corridor(OpexWaterGraph(64, island), island, r, 7, 1, 7, 5);
  W5Assert(c.status == "found" && c.distance == W5Exact(island, 7, 1, 7, 5), "island corridor");
  /* Blocked edge (half-tile coast): water on both sides but not connected. */
  local gate = W5FakeSource(["~~~~~~~~~~"]);
  gate.Block(4, 0, 5, 0);
  W5Check(gate, 0, 0, 9, 0, "disconnected", "blocked border edge");
  gate = W5FakeSource(["~~~~~~~~~~"]);
  gate.Block(2, 0, 3, 0);
  W5Check(gate, 0, 0, 4, 0, "disconnected", "blocked internal edge");
  /* Land endpoints and partial edge blocks (13x7: last block 3x2). */
  W5Check(basins, 4, 0, 0, 0, "unknown", "land endpoint");
  local edge = W5FakeSource(["~~~~~~~~~~~~~", "#############", "#############", "#############",
    "#############", "~~~~~~~~~~~~~", "~~~~~~~~~~~~~"]);
  W5Check(edge, 12, 6, 0, 5, "connected", "partial edge block");
  W5Check(edge, 12, 0, 0, 6, "disconnected", "edge basins");
  /* Bounded peninsula-like exploration: unknown, never disconnected. */
  local sea = [];
  for (local y = 0; y < 30; y++) sea.append("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~");
  local seaSrc = W5FakeSource(sea);
  local g = OpexWaterGraph(64, seaSrc);
  r = W5Run(g, seaSrc, 0, 0, 29, 29, 3);
  W5Assert(r.status == "unknown" && r.reason == "block_budget", "block budget");
  r = W5Run(g, seaSrc, 0, 0, 29, 29, 100000, 2);
  W5Assert(r.status == "unknown" && r.reason == "node_budget", "node budget");
  /* Invalidation of a visited block during the query. */
  g = OpexWaterGraph(64, seaSrc);
  g.Begin(0, 0, 29, 29, 100000, 100000);
  for (local i = 0; i < 20; i++) g.Step(2000, seaSrc.Tick() + 1000);
  g.InvalidateRect(0, 0, 1, 1);
  W5Assert(g.Result().status == "unknown" && g.Result().reason == "invalidated", "invalidated query");
  /* Stale records are recomputed: world change after invalidation is seen. */
  g = OpexWaterGraph(64, gate);
  W5Assert(W5Run(g, gate, 0, 0, 4, 0).status == "disconnected", "before change");
  gate.blocked = {};
  W5Assert(W5Run(g, gate, 0, 0, 4, 0).status == "disconnected", "cache is an observation");
  g.InvalidateRect(2, 0, 4, 1);
  W5Assert(W5Run(g, gate, 0, 0, 4, 0).status == "connected", "recomputed after invalidation");
  /* Small cache: evictions force recomputation, never a wrong answer. */
  g = OpexWaterGraph(4, seaSrc);
  W5Assert(W5Run(g, seaSrc, 0, 0, 29, 29).status == "connected" && g.Stats().evictions > 0,
    "evicting cache");
  AILog.Info("C675_ADVERSE_PASS");
}

/* Deterministic LCG in a table (closures do not capture enclosing locals). */
class W5Lcg {
  s = 0;
  constructor(seed) { this.s = seed; }
  function Next(n) {
    this.s = (this.s * 1103515245 + 12345) & 0x7fffffff;
    return this.s % n;
  }
}

function W5RandomTests() {
  local rng = W5Lcg(675);
  local pairs = 0, unknown = 0;
  for (local m = 0; m < 30; m++) {
    local w = 7 + rng.Next(20), h = 5 + rng.Next(16);
    local rows = [];
    local density = 40 + rng.Next(40);
    for (local y = 0; y < h; y++) {
      local row = "";
      for (local x = 0; x < w; x++) row += rng.Next(100) < density ? "~" : "#";
      rows.append(row);
    }
    local src = W5FakeSource(rows);
    for (local k = 0; k < w * h / 8; k++) {
      local x = rng.Next(w - 1), y = rng.Next(h);
      src.Block(x, y, x + 1, y);
    }
    local water = [];
    for (local i = 0; i < w * h; i++) if (src.cells[i]) water.append(i);
    if (water.len() < 2) continue;
    local full = OpexWaterGraph(4096, src);
    local tight = OpexWaterGraph(8, src);
    for (local p = 0; p < 12; p++) {
      local a = water[rng.Next(water.len())], b = water[rng.Next(water.len())];
      local ax = a % w, ay = a / w, bx = b % w, by = b / w;
      local exact = W5Exact(src, ax, ay, bx, by);
      local r = W5Run(full, src, ax, ay, bx, by);
      local want = exact >= 0 ? "connected" : "disconnected";
      W5Assert(r.status == want, "random map " + m + " pair " + p + ": " + r.status);
      if (exact >= 0) {
        local c = W5Corridor(full, src, r, ax, ay, bx, by);
        W5Assert(c.status == "found" && c.distance >= exact, "corridor bound");
      }
      local rb = W5Run(tight, src, ax, ay, bx, by, 2 + rng.Next(6), 1000);
      W5Assert(rb.status == want || rb.status == "unknown", "bounded never contradicts");
      if (rb.status == "unknown") unknown++;
      pairs++;
    }
  }
  W5Assert(pairs > 200 && unknown > 0, "random coverage");
  AILog.Info("C675_RANDOM_PASS pairs=" + pairs + " bounded_unknown=" + unknown);
}

/* ---- Real map: oracle and current builder predicate against an exact labelling. ---- */

/* Waits by Sleep(1) between tranches: the reported cost is the service's own work. */
function W5Drive(stepper) {
  while (stepper.Step(5000, AIController.GetTick() + 1) != "done") AIController.Sleep(1);
}

class WaterGraphProbe extends AIController {
  function Start() {
    W5AdverseTests();
    W5RandomTests();
    this.RealMap();
    local tile = AIMap.GetTileIndex(AIMap.GetMapSizeX() / 2, AIMap.GetMapSizeY() / 2);
    AISign.BuildSign(tile, "C675|PASS");
    AILog.Info("C675_ALL_PASS");
    while (true) AIController.Sleep(1);
  }

  function RealMap() {
    local src = OpexWaterGraphSource();
    local w = src.Width(), h = src.Height();
    /* Exact component labels by flood fill over the whole map: diagnostic cost only. */
    local mark = OpexOpsMeasureBegin();
    local label = array(w * h, -1);
    local water = [];
    local comps = 0;
    for (local i = 0; i < w * h; i++) {
      if (label[i] >= 0 || !src.IsWater(i % w, i / w)) continue;
      label[i] = comps;
      local queue = [i];
      for (local head = 0; head < queue.len(); head++) {
        local cur = queue[head];
        local x = cur % w, y = cur / w;
        water.append(cur);
        foreach (o in [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          local nx = x + o[0], ny = y + o[1];
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          local key = ny * w + nx;
          if (label[key] >= 0 || !src.IsWater(nx, ny) || !src.Connected(x, y, nx, ny)) continue;
          label[key] = comps;
          queue.append(key);
        }
      }
      comps++;
    }
    AILog.Info("C675_MAP w=" + w + " h=" + h + " water=" + water.len() + " comps=" + comps
               + " label_ops=" + OpexOpsMeasureEnd(mark));
    if (water.len() < 2) return;
    local rng = W5Lcg(w * 7919 + h);
    local g = OpexWaterGraph(4096, src);
    for (local p = 0; p < 200; p++) {
      local a = water[rng.Next(water.len())];
      local b = water[rng.Next(water.len())];
      if (p % 2 == 1) {     // near pair: another water tile within 60 tiles if possible
        for (local t = 0; t < 64; t++) {
          local c = water[rng.Next(water.len())];
          if (abs(c % w - a % w) + abs(c / w - a / w) <= 60) { b = c; break; }
        }
      }
      local ax = a % w, ay = a / w, bx = b % w, by = b / w;
      local exact = label[a] == label[b] ? 1 : 0;
      local before = g.Stats().ops_total;
      g.Begin(ax, ay, bx, by);
      W5Drive(g);
      local ops = g.Stats().ops_total - before;
      local r = g.Result();
      local wrong = (r.status == "connected" && exact == 0) || (r.status == "disconnected" && exact == 1);
      local ta = AIMap.GetTileIndex(ax, ay), tb = AIMap.GetTileIndex(bx, by);
      mark = OpexOpsMeasureBegin();
      local builder = OpexWaterFindConnection({ dock = ta, waterTiles = [ta] },
                                              { dock = tb, waterTiles = [tb] });
      local builderOps = OpexOpsMeasureEnd(mark);
      local cstatus = "-", cdist = -1, cops = 0;
      if (r.status == "connected") {
        local c = OpexWaterCorridor(g, g.CorridorBlocks(r.chain), ax, ay, bx, by);
        W5Drive(c);
        cops = c.ops_total;
        cstatus = c.status;
        if (c.distance != null) cdist = c.distance;
      }
      AILog.Info("C675_PAIR i=" + p + " manh=" + (abs(ax - bx) + abs(ay - by)) + " exact=" + exact
                 + " oracle=" + r.status + " reason=" + (r.reason == null ? "-" : r.reason)
                 + " wrong=" + (wrong ? 1 : 0) + " blocks=" + r.blocks_analyzed + " nodes=" + r.nodes
                 + " ops=" + ops + " builder=" + builder + " builder_ops=" + builderOps
                 + " corridor=" + cstatus + " cdist=" + cdist + " cops=" + cops);
      W5Assert(!wrong, "real map pair " + p + " contradicts exact labelling");
    }
    local s = g.Stats();
    AILog.Info("C675_GRAPH analyzed=" + s.analyzed + " resident=" + s.resident + " evictions="
               + s.evictions + " ops_max=" + s.ops_max + " unit_ops_max=" + s.unit_ops_max
               + " steps=" + s.steps);
  }
}
