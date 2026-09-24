/* C67.5: water component graph over S=5 blocks and a bounded connectivity oracle
 * (docs/c67_cartographie_contrat.md section 16). Not loaded by OpexAI in C67.5.
 * Requires terrain_map.nut (OpexTerrainIds) and budget.nut.
 *
 * Predicate identical to OpexWaterFindConnection: a navigable tile is IsWaterTile; an edge
 * joins two cardinal neighbours that are both water and AreWaterTilesConnected. The block
 * quotient is exact, so "connected" and "disconnected" are proofs about the observed tiles;
 * any budget, cap or invalidation yields "unknown", never a guess. */

class OpexWaterGraphSource {
  function Width() { return AIMap.GetMapSizeX(); }
  function Height() { return AIMap.GetMapSizeY(); }
  function Tick() { return AIController.GetTick(); }
  function Mark() { return OpexOpsMeasureBegin(); }
  function Spent(mark) { return OpexOpsMeasureEnd(mark); }
  function Remaining() { return AIController.GetOpsTillSuspend(); }
  function IsWater(x, y) { return AITile.IsWaterTile(AIMap.GetTileIndex(x, y)); }
  function Connected(x1, y1, x2, y2) {
    return AIMarine.AreWaterTilesConnected(AIMap.GetTileIndex(x1, y1), AIMap.GetTileIndex(x2, y2));
  }
}

class OpexWaterGraph {
  _src = null;
  _width = 0;
  _height = 0;
  _side = 5;
  _nx = 0;
  _ny = 0;
  _capacity = 0;
  _cache = null;
  _lru = null;
  _rects = null;
  _rectLimit = 32;
  _serial = 0;
  _job = null;     // block analysis in progress
  _query = null;   // at most one oracle query
  _stats = null;
  /* Opcodes kept in the tick before any unit: above the measured unit peak (3 578, C67.5). */
  _reserve = 4000;

  constructor(capacity = 4096, source = null) {
    if (capacity < 1 || capacity > 4096) throw "C67.5: invalid capacity";
    this._src = source == null ? OpexWaterGraphSource() : source;
    this._width = this._src.Width();
    this._height = this._src.Height();
    this._nx = (this._width + this._side - 1) / this._side;
    this._ny = (this._height + this._side - 1) / this._side;
    this._capacity = capacity;
    this.Clear();
  }

  function Clear() {
    this._cache = {};
    this._lru = OpexTerrainIds();
    this._rects = [];
    this._job = null;
    this._query = null;
    this._serial++;
    this._stats = { analyzed = 0, api_reads = 0, evictions = 0, queries = 0,
      connected = 0, disconnected = 0, unknown = 0, steps = 0, ops_total = 0, ops_max = 0,
      unit_ops_max = 0, restarts = 0 };
  }

  function BlockOf(x, y) { return (y / this._side) * this._nx + x / this._side; }

  function _bounds(id) {
    local x = (id % this._nx) * this._side;
    local y = (id / this._nx) * this._side;
    return { x0 = x, y0 = y, x1 = min(this._width, x + this._side),
      y1 = min(this._height, y + this._side) };
  }

  function _intersects(id, x0, y0, x1, y1) {
    local b = this._bounds(id);
    return b.x0 < x1 && b.x1 > x0 && b.y0 < y1 && b.y1 > y0;
  }

  /* Fresh record or null; a record older than an intersecting rectangle is dropped. */
  function _record(id) {
    if (!(id in this._cache)) return null;
    local rec = this._cache[id];
    local bx = id % this._nx, by = id / this._nx;
    foreach (r in this._rects) {
      if (r.serial > rec.generation && bx >= r.bx0 && bx <= r.bx1 && by >= r.by0 && by <= r.by1) {
        delete this._cache[id];
        this._lru.Remove(id);
        return null;
      }
    }
    this._lru.Push(id);
    return rec;
  }

  function InvalidateRect(x0, y0, x1, y1) {
    x0 = max(0, x0); y0 = max(0, y0);
    x1 = min(this._width, x1); y1 = min(this._height, y1);
    if (x0 >= x1 || y0 >= y1) return;
    /* Stored in block coordinates (inclusive), so a staleness check is four comparisons. */
    this._rects.append({ bx0 = x0 / this._side, by0 = y0 / this._side,
      bx1 = (x1 - 1) / this._side, by1 = (y1 - 1) / this._side, serial = ++this._serial });
    if (this._rects.len() > this._rectLimit) {
      local a = this._rects[0], b = this._rects[1];
      this._rects[1] = { bx0 = min(a.bx0, b.bx0), by0 = min(a.by0, b.by0),
        bx1 = max(a.bx1, b.bx1), by1 = max(a.by1, b.by1), serial = max(a.serial, b.serial) };
      this._rects.remove(0);
    }
    if (this._job != null && this._intersects(this._job.id, x0, y0, x1, y1)) {
      this._job = null;
      this._stats.restarts++;
    }
    local q = this._query;
    if (q != null && q.status == "running" && q.bx0 != null
        && q.bx0 * this._side < x1 && (q.bx1 + 1) * this._side > x0
        && q.by0 * this._side < y1 && (q.by1 + 1) * this._side > y0) {
      this._finish("unknown", "invalidated");
    }
  }

  /* ---- Block analysis: one unit = one tile, at most two API calls. ---- */

  function _beginJob(id) {
    local b = this._bounds(id);
    local w = b.x1 - b.x0, h = b.y1 - b.y0;
    local n = w * h;
    local water = array(n, false);
    local uf = array(n, 0);
    for (local i = 0; i < n; i++) uf[i] = i;
    this._job = { id = id, b = b, w = w, h = h, n = n, phase = 0, cursor = 0,
      water = water, uf = uf, crossE = array(h, false), crossS = array(w, false),
      generation = ++this._serial };
  }

  function _find(uf, i) {
    while (uf[i] != i) { uf[i] = uf[uf[i]]; i = uf[i]; }
    return i;
  }

  function _unitJob() {
    local j = this._job;
    local src = this._src;
    if (j.phase == 0) {             // water flags
      local i = j.cursor++;
      j.water[i] = src.IsWater(j.b.x0 + i % j.w, j.b.y0 + i / j.w);
      this._stats.api_reads++;
      if (j.cursor == j.n) { j.phase = 1; j.cursor = 0; }
      return;
    }
    if (j.phase == 1) {             // internal east/south edges
      local i = j.cursor++;
      if (j.water[i]) {
        local lx = i % j.w, ly = i / j.w;
        local x = j.b.x0 + lx, y = j.b.y0 + ly;
        if (lx + 1 < j.w && j.water[i + 1] && src.Connected(x, y, x + 1, y)) {
          this._stats.api_reads++;
          j.uf[this._find(j.uf, i)] = this._find(j.uf, i + 1);
        }
        if (ly + 1 < j.h && j.water[i + j.w] && src.Connected(x, y, x, y + 1)) {
          this._stats.api_reads++;
          j.uf[this._find(j.uf, i)] = this._find(j.uf, i + j.w);
        }
      }
      if (j.cursor == j.n) { j.phase = 2; j.cursor = 0; }
      return;
    }
    if (j.phase == 2) {             // border edges: h east rows, then w south columns
      local k = j.cursor++;
      if (k < j.h) {
        local x = j.b.x1 - 1, y = j.b.y0 + k;
        if (j.b.x1 < this._width && j.water[k * j.w + j.w - 1] && src.IsWater(x + 1, y)) {
          this._stats.api_reads++;
          j.crossE[k] = src.Connected(x, y, x + 1, y);
        }
      } else {
        local c = k - j.h;
        local x = j.b.x0 + c, y = j.b.y1 - 1;
        if (j.b.y1 < this._height && j.water[(j.h - 1) * j.w + c] && src.IsWater(x, y + 1)) {
          this._stats.api_reads++;
          j.crossS[c] = src.Connected(x, y, x, y + 1);
        }
      }
      if (j.cursor == j.h + j.w) this._publishJob();
    }
  }

  function _publishJob() {
    local j = this._job;
    local labels = null;
    local comps = 0;
    local roots = {};
    for (local i = 0; i < j.n; i++) {
      if (!j.water[i]) continue;
      if (labels == null) labels = array(j.n, -1);
      local r = this._find(j.uf, i);
      if (!(r in roots)) roots.rawset(r, comps++);
      labels[i] = roots[r];
    }
    if (!(j.id in this._cache) && this._cache.len() >= this._capacity) {
      local victim = this._lru.Pop();
      delete this._cache[victim];
      this._stats.evictions++;
    }
    this._cache.rawset(j.id, { generation = j.generation, w = j.w, h = j.h, comps = comps,
      labels = labels, crossE = j.crossE, crossS = j.crossS });
    this._lru.Push(j.id);
    this._stats.analyzed++;
    this._job = null;
  }

  /* ---- Oracle ---- */

  function Begin(ax, ay, bx, by, maxBlocks = 1024, maxNodes = 4096) {
    if (ax < 0 || ay < 0 || bx < 0 || by < 0 || ax >= this._width || bx >= this._width
        || ay >= this._height || by >= this._height) throw "C67.5: tile out of map";
    this._stats.queries++;
    this._query = { ax = ax, ay = ay, bx = bx, by = by, maxBlocks = maxBlocks,
      maxNodes = maxNodes, status = "running", reason = null, analyzed = 0,
      start = null, target = null, prev = {}, queue = [], head = 0, dir = 0,
      bx0 = null, by0 = null, bx1 = null, by1 = null, chain = null };
    return "running";
  }

  function Result() {
    local q = this._query;
    if (q == null) return null;
    return { status = q.status, reason = q.reason, distance_kind = "none", distance = null,
      chain = q.chain, blocks_analyzed = q.analyzed, nodes = q.prev.len(),
      /* After a closed "disconnected" proof, every node of A's component. */
      component = q.status == "disconnected" ? q.prev : null };
  }

  /* Node (block, component) of a tile from a fresh record, or null when not known yet. */
  function NodeOf(x, y) {
    local id = this.BlockOf(x, y);
    local rec = this._record(id);
    if (rec == null || rec.labels == null) return null;
    local label = rec.labels[this._local(rec, id, x, y)];
    return label < 0 ? null : id * 16 + label;
  }

  function Cancel() {
    this._query = null;
    this._job = null;
  }

  function _finish(status, reason) {
    local q = this._query;
    q.status = status;
    q.reason = reason;
    this._stats[status]++;
    this._job = null;
  }

  function _local(rec, id, x, y) {
    local b = this._bounds(id);
    return (y - b.y0) * rec.w + (x - b.x0);
  }

  function _touch(q, id) {
    local bx = id % this._nx, by = id / this._nx;
    if (q.bx0 == null) { q.bx0 = bx; q.bx1 = bx; q.by0 = by; q.by1 = by; return; }
    q.bx0 = min(q.bx0, bx); q.bx1 = max(q.bx1, bx);
    q.by0 = min(q.by0, by); q.by1 = max(q.by1, by);
  }

  /* Record for block id, or null after scheduling its analysis (budget checked here). */
  function _need(q, id) {
    local rec = this._record(id);
    if (rec != null) { this._touch(q, id); return rec; }
    if (this._job == null || this._job.id != id) {
      if (q.analyzed >= q.maxBlocks) { this._finish("unknown", "block_budget"); return null; }
      q.analyzed++;
      this._beginJob(id);
    }
    return null;
  }

  function _push(q, node, from) {
    if (node in q.prev) return;
    if (q.prev.len() >= q.maxNodes) { this._finish("unknown", "node_budget"); return; }
    q.prev.rawset(node, from);
    q.queue.append(node);
    if (node == q.target) {
      local chain = [];
      for (local n = node; n != null; n = q.prev[n]) chain.append(n);
      chain.reverse();
      q.chain = chain;
      this._finish("connected", null);
    }
  }

  /* One unit of query work without API calls, or false when a block analysis is required. */
  function _unitQuery() {
    local q = this._query;
    if (q.start == null) {
      local ida = this.BlockOf(q.ax, q.ay);
      local ra = this._need(q, ida);
      if (ra == null) return false;
      local idb = this.BlockOf(q.bx, q.by);
      local rb = this._need(q, idb);
      if (rb == null) return false;
      local la = ra.labels == null ? -1 : ra.labels[this._local(ra, ida, q.ax, q.ay)];
      local lb = rb.labels == null ? -1 : rb.labels[this._local(rb, idb, q.bx, q.by)];
      if (la < 0 || lb < 0) { this._finish("unknown", "not_water"); return true; }
      q.start = ida * 16 + la;
      q.target = idb * 16 + lb;
      this._push(q, q.start, null);
      return true;
    }
    if (q.head >= q.queue.len()) { this._finish("disconnected", null); return true; }
    local node = q.queue[q.head];
    local id = node / 16, label = node % 16;
    local rec = this._record(id);
    if (rec == null) return this._need(q, id) != null;
    local bx = id % this._nx, by = id / this._nx;
    /* Directions in order E, S, W, N; each needs the neighbour record. */
    while (q.dir < 4 && q.status == "running") {
      local d = q.dir;
      local nbx = bx + (d == 0 ? 1 : (d == 2 ? -1 : 0));
      local nby = by + (d == 1 ? 1 : (d == 3 ? -1 : 0));
      if (nbx < 0 || nby < 0 || nbx >= this._nx || nby >= this._ny) { q.dir++; continue; }
      local nid = nby * this._nx + nbx;
      local nrec = this._need(q, nid);
      if (nrec == null) return false;
      if (d == 0 || d == 2) {       // shared vertical border, rows 0..h-1
        local west = d == 0 ? rec : nrec, east = d == 0 ? nrec : rec;
        for (local r = 0; r < rec.h; r++) {
          /* A crossing seen by one record but not the other (world changed between two
           * analyses) is skipped: it can only make a later answer less connected. */
          if (!west.crossE[r] || west.labels == null || east.labels == null) continue;
          local a = west.labels[r * west.w + west.w - 1], b = east.labels[r * east.w];
          if (a < 0 || b < 0) continue;
          if (d == 0 && a == label) this._push(q, nid * 16 + b, node);
          if (d == 2 && b == label) this._push(q, nid * 16 + a, node);
          if (q.status != "running") return true;
        }
      } else {                      // shared horizontal border, columns 0..w-1
        local north = d == 1 ? rec : nrec, south = d == 1 ? nrec : rec;
        for (local c = 0; c < rec.w; c++) {
          if (!north.crossS[c] || north.labels == null || south.labels == null) continue;
          local a = north.labels[(north.h - 1) * north.w + c], b = south.labels[c];
          if (a < 0 || b < 0) continue;
          if (d == 1 && a == label) this._push(q, nid * 16 + b, node);
          if (d == 3 && b == label) this._push(q, nid * 16 + a, node);
          if (q.status != "running") return true;
        }
      }
      q.dir++;
    }
    q.dir = 0;
    q.head++;
    return true;
  }

  /* Advances the query (and any block analysis it needs) within ops_budget. */
  function Step(ops_budget, deadline_tick) {
    local q = this._query;
    if (q == null || q.status != "running") return "done";
    if (ops_budget <= 0 || this._src.Tick() >= deadline_tick) return "idle";
    if (this._src.Remaining() < this._reserve) return "idle";
    local mark = this._src.Mark();
    this._stats.steps++;
    /* The reserve is checked before every unit, not only on entry: a unit never starts near the
     * end of a VM tick, so none is split across two ticks. */
    while (q.status == "running" && this._src.Tick() < deadline_tick
           && this._src.Spent(mark) < ops_budget && this._src.Remaining() >= this._reserve) {
      local unit = this._src.Mark();
      if (this._job != null) this._unitJob();
      else this._unitQuery();
      this._stats.unit_ops_max = max(this._stats.unit_ops_max, this._src.Spent(unit));
    }
    local spent = this._src.Spent(mark);
    this._stats.ops_total += spent;
    this._stats.ops_max = max(this._stats.ops_max, spent);
    return q.status == "running" ? "running" : "done";
  }

  /* Blocks of a connected chain dilated by one block: the corridor for CorridorDistance. */
  function CorridorBlocks(chain) {
    local out = {};
    foreach (node in chain) {
      local id = node / 16;
      local bx = id % this._nx, by = id / this._nx;
      for (local dy = -1; dy <= 1; dy++) for (local dx = -1; dx <= 1; dx++) {
        local x = bx + dx, y = by + dy;
        if (x >= 0 && y >= 0 && x < this._nx && y < this._ny) out.rawset(y * this._nx + x, true);
      }
    }
    return out;
  }

  function Stats() {
    local out = clone this._stats;
    out.rawset("resident", this._cache.len());
    out.rawset("rects", this._rects.len());
    return out;
  }
}

/* Tile BFS restricted to a block set, by slices. Length of a real path (an upper bound on the
 * shortest path), or unknown; never a disconnection claim. */
class OpexWaterCorridor {
  _src = null;
  _graph = null;
  _allowed = null;
  _w = 0;
  _tx = 0;
  _ty = 0;
  _seen = null;
  _queue = null;
  _head = 0;
  _maxNodes = 0;
  status = "running";
  distance = null;
  ops_max = 0;
  ops_total = 0;

  constructor(graph, allowed, ax, ay, bx, by, maxNodes = 20000, source = null) {
    this._graph = graph;
    this._src = source == null ? graph._src : source;
    this._allowed = allowed;
    this._w = graph._width;
    this._tx = bx; this._ty = by;
    this._maxNodes = maxNodes;
    local start = ay * this._w + ax;
    this._seen = {};
    this._seen.rawset(start, 0);
    this._queue = [start];
  }

  function _ok(x, y) {
    return x >= 0 && y >= 0 && x < this._graph._width && y < this._graph._height
      && (this._graph.BlockOf(x, y) in this._allowed);
  }

  function Step(ops_budget, deadline_tick) {
    if (this.status != "running") return "done";
    if (ops_budget <= 0 || this._src.Tick() >= deadline_tick
        || this._src.Remaining() < this._graph._reserve) return "idle";
    local mark = this._src.Mark();
    while (this.status == "running" && this._src.Tick() < deadline_tick
           && this._src.Spent(mark) < ops_budget && this._src.Remaining() >= this._graph._reserve) {
      if (this._head >= this._queue.len()) { this.status = "unknown"; break; }
      local cur = this._queue[this._head++];
      local x = cur % this._w, y = cur / this._w, d = this._seen[cur];
      if (x == this._tx && y == this._ty) { this.status = "found"; this.distance = d; break; }
      foreach (o in [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        local nx = x + o[0], ny = y + o[1];
        local key = ny * this._w + nx;
        if (!this._ok(nx, ny) || (key in this._seen)) continue;
        if (!this._src.IsWater(nx, ny) || !this._src.Connected(x, y, nx, ny)) continue;
        if (this._seen.len() >= this._maxNodes) { this.status = "unknown"; break; }
        this._seen.rawset(key, d + 1);
        this._queue.append(key);
      }
    }
    local spent = this._src.Spent(mark);
    this.ops_max = max(this.ops_max, spent);
    this.ops_total += spent;
    return this.status == "running" ? "running" : "done";
  }
}
