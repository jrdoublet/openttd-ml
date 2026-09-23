/* C67.2: isolated, reconstructible terrain summaries. C67.4: loaded by OpexAI, but only
 * constructed under c67_terrain_map (task_terrain.nut). budget.nut must be loaded first.
 * No economic consumer and no connectivity claim. */

class OpexTerrainSource {
  function Width() { return AIMap.GetMapSizeX(); }
  function Height() { return AIMap.GetMapSizeY(); }
  function Tick() { return AIController.GetTick(); }
  function Mark() { return OpexOpsMeasureBegin(); }
  function Spent(mark) { return OpexOpsMeasureEnd(mark); }
  function Remaining() { return AIController.GetOpsTillSuspend(); }
  function Read(x, y) {
    local tile = AIMap.GetTileIndex(x, y);
    if (!AIMap.IsValidTile(tile)) return null;
    return {
      water = AITile.IsWaterTile(tile), coast = AITile.IsCoastTile(tile),
      lo = AITile.GetMinHeight(tile), hi = AITile.GetMaxHeight(tile),
      flat = AITile.GetSlope(tile) == AITile.SLOPE_FLAT,
      buildable = AITile.IsBuildable(tile)
    };
  }
}

/* Intrusive integer-key list: FIFO queues and LRU, without array.remove(0) or scans. */
class OpexTerrainIds {
  nodes = null;
  head = null;
  tail = null;
  constructor() { this.nodes = {}; }
  function Remove(id) {
    if (!(id in this.nodes)) return;
    local n = this.nodes[id];
    if (n.prev == null) this.head = n.next;
    else this.nodes[n.prev].next = n.next;
    if (n.next == null) this.tail = n.prev;
    else this.nodes[n.next].prev = n.prev;
    delete this.nodes[id];
  }
  function Push(id) {
    this.Remove(id);
    this.nodes.rawset(id, { prev = this.tail, next = null });
    if (this.tail == null) this.head = id;
    else this.nodes[this.tail].next = id;
    this.tail = id;
  }
  function Pop() {
    local id = this.head;
    if (id != null) this.Remove(id);
    return id;
  }
}

class OpexTerrainMap {
  _source = null;
  _width = 0;
  _height = 0;
  _side = 0;
  _nx = 0;
  _ny = 0;
  _capacity = 0;
  _queueCapacity = 0;
  _cache = null;
  _lru = null;
  _requests = null;
  _urgent = null;
  _background = null;
  _active = null;
  _serial = 0;
  _stats = null;
  /* C67.4: lazy invalidation. At most _rectLimit dated rectangles, never a scan of residents. */
  _rects = null;
  _rectLimit = 32;

  constructor(side, capacity = 4096, queueCapacity = 256, source = null) {
    if (side != 5 && side != 10) throw "C67: side must be 5 or 10";
    if (capacity < 1 || capacity > 4096 || queueCapacity < 1 || queueCapacity > 256)
      throw "C67: invalid capacity";
    this._source = source == null ? OpexTerrainSource() : source;
    this._width = this._source.Width();
    this._height = this._source.Height();
    if (this._width <= 0 || this._height <= 0) throw "C67: invalid map dimensions";
    this._side = side;
    this._nx = (this._width + side - 1) / side;
    this._ny = (this._height + side - 1) / side;
    this._capacity = capacity;
    this._queueCapacity = queueCapacity;
    this.Clear();
  }

  function Clear() {
    this._cache = {};
    this._lru = OpexTerrainIds();
    this._requests = {};
    this._urgent = OpexTerrainIds();
    this._background = OpexTerrainIds();
    this._active = null;
    this._rects = [];
    /* Never reuse a version within the lifetime of this service. */
    this._serial++;
    this._stats = { reads = 0, hits = 0, misses = 0, refused = 0,
      evictions = 0, completed = 0, cancelled = 0, queue_peak = 0,
      steps = 0, ops_total = 0, ops_max = 0, read_ops_max = 0,
      bg_refused = 0, bg_dropped = 0, withdrawn = 0, invalidations = 0 };
  }

  function BlockId(x, y) {
    if (x < 0 || y < 0 || x >= this._width || y >= this._height) return null;
    return (y / this._side) * this._nx + x / this._side;
  }

  function _valid(id) {
    return typeof id == "integer" && id >= 0 && id < this._nx * this._ny;
  }

  function _bounds(id) {
    local x = (id % this._nx) * this._side;
    local y = (id / this._nx) * this._side;
    return { x0 = x, y0 = y, x1 = min(this._width, x + this._side),
      y1 = min(this._height, y + this._side) };
  }

  /* A resident older than an intersecting invalidation rectangle becomes stale here. */
  function _fresh(id) {
    local entry = this._cache[id];
    if (entry.stale) return false;
    foreach (r in this._rects) {
      if (r.serial > entry.generation && this._intersects(id, r.x0, r.y0, r.x1, r.y1)) {
        entry.stale = true;
        entry.summary = null;
        entry.generation = r.serial;
        return false;
      }
    }
    return true;
  }

  function Peek(id) {
    if (!this._valid(id)) return { status = "absent", generation = null, summary = null };
    if (id in this._requests)
      return { status = "pending", generation = this._requests[id].generation, summary = null };
    if (!(id in this._cache)) return { status = "absent", generation = null, summary = null };
    this._fresh(id);
    local entry = this._cache[id];
    this._lru.Push(id);
    return { status = entry.stale ? "stale" : "ready", generation = entry.generation,
      summary = entry.stale ? null : clone entry.summary };
  }

  /* priority 1 = requested by a consumer, 0 = optional background. */
  function Request(id, priority = 1) {
    if (!this._valid(id) || (priority != 0 && priority != 1)) return "invalid";
    if (id in this._requests) {
      local r = this._requests[id];
      if (priority > r.priority) {
        r.priority = priority;
        if (this._active == null || this._active.id != id) {
          this._background.Remove(id);
          this._urgent.Push(id);
        }
      }
      return "pending";
    }
    if ((id in this._cache) && this._fresh(id)) {
      /* A background probe must not reorder the LRU nor count as a consumer hit. */
      if (priority == 0) return "ready";
      this._stats.hits++;
      this._lru.Push(id);
      return "ready";
    }
    /* C67.4: background work never evicts; leave room for the pending requests too. */
    if (priority == 0 && !(id in this._cache)
        && this._cache.len() + this._requests.len() >= this._capacity) {
      this._stats.bg_refused++;
      return "full";
    }
    if (this._requests.len() >= this._queueCapacity) {
      this._stats.refused++;
      return "full";
    }
    this._stats.misses++;
    this._serial++;
    this._requests.rawset(id, { priority = priority, generation = this._serial });
    if (priority == 1) this._urgent.Push(id);
    else this._background.Push(id);
    this._stats.queue_peak = max(this._stats.queue_peak, this._requests.len());
    return "pending";
  }

  function _begin(id) {
    local b = this._bounds(id);
    /* The generation starts with the computation: later rectangles cancel or stale it. */
    this._requests[id].generation = ++this._serial;
    this._active = { id = id, bounds = b, cursor = 0, summary = {
      schema_version = 1, block_id = id, generation = this._requests[id].generation,
      sample_count = 0, invalid_count = 0, water_count = 0, coast_count = 0,
      height_min = null, height_max = null, height_min_sum = 0,
      flat_count = 0, buildable_count = 0, first_sample_tick = null,
      last_sample_tick = null, dynamic_sample_tick = null
    } };
  }

  function _readOne() {
    local a = this._active;
    local b = a.bounds;
    local w = b.x1 - b.x0;
    local s = a.summary;
    if (s.first_sample_tick == null) s.first_sample_tick = this._source.Tick();
    local t = this._source.Read(b.x0 + a.cursor % w, b.y0 + a.cursor / w);
    this._stats.reads++;
    a.cursor++;
    s.last_sample_tick = this._source.Tick();
    s.dynamic_sample_tick = s.last_sample_tick;
    if (t == null) { s.invalid_count++; return; }
    s.sample_count++;
    if (t.water) s.water_count++;
    if (t.coast) s.coast_count++;
    if (t.flat) s.flat_count++;
    if (t.buildable) s.buildable_count++;
    s.height_min = s.height_min == null ? t.lo : min(s.height_min, t.lo);
    s.height_max = s.height_max == null ? t.hi : max(s.height_max, t.hi);
    s.height_min_sum += t.lo;
  }

  function _publish() {
    local a = this._active;
    local s = a.summary;
    local n = s.sample_count;
    s.rawset("water_ratio", n == 0 ? null : s.water_count.tofloat() / n);
    s.rawset("flat_ratio", n == 0 ? null : s.flat_count.tofloat() / n);
    s.rawset("buildable_ratio", n == 0 ? null : s.buildable_count.tofloat() / n);
    s.rawset("mean_tile_min_height", n == 0 ? null : s.height_min_sum.tofloat() / n);
    s.rawset("relief", n == 0 ? null : s.height_max - s.height_min);
    if (!(a.id in this._cache) && this._cache.len() >= this._capacity
        && this._requests[a.id].priority == 0) {
      delete this._requests[a.id];
      this._active = null;
      this._stats.bg_dropped++;
      return;
    }
    if (!(a.id in this._cache) && this._cache.len() >= this._capacity) {
      local victim = this._lru.Pop();
      delete this._cache[victim];
      this._stats.evictions++;
    }
    this._cache.rawset(a.id, { stale = false, generation = s.generation, summary = s });
    this._lru.Push(a.id);
    delete this._requests[a.id];
    this._active = null;
    this._stats.completed++;
  }

  function Step(ops_budget, deadline_tick) {
    if (ops_budget <= 0 || this._source.Tick() >= deadline_tick) return "idle";
    /* A tile read may be much dearer than its average. Do not start it at the
     * end of a VM tick; the caller may schedule another task then retry. */
    if (this._source.Remaining() < 3000) return "idle";
    local mark = this._source.Mark();
    this._stats.steps++;
    /* One accumulator only: discard/requeue background partial work for urgent demand.
     * C67.4 may improve this policy; never occupy the game's worker registry here. */
    if (this._active != null && this._urgent.head != null
        && this._requests[this._active.id].priority == 0) {
      this._background.Push(this._active.id);
      this._active = null;
    }
    while (this._source.Tick() < deadline_tick && this._source.Spent(mark) < ops_budget) {
      if (this._active == null) {
        local id = this._urgent.Pop();
        if (id == null) id = this._background.Pop();
        if (id == null) break;
        this._begin(id);
      }
      local readMark = this._source.Mark();
      this._readOne();
      this._stats.read_ops_max = max(this._stats.read_ops_max, this._source.Spent(readMark));
      local a = this._active;
      if (a.cursor == (a.bounds.x1 - a.bounds.x0) * (a.bounds.y1 - a.bounds.y0))
        this._publish();
    }
    local spent = this._source.Spent(mark);
    this._stats.ops_total += spent;
    this._stats.ops_max = max(this._stats.ops_max, spent);
    return this._requests.len() == 0 ? "done" : "running";
  }

  function _intersects(id, x0, y0, x1, y1) {
    local b = this._bounds(id);
    return b.x0 < x1 && b.x1 > x0 && b.y0 < y1 && b.y1 > y0;
  }

  function InvalidateRect(x0, y0, x1, y1) {
    x0 = max(0, x0); y0 = max(0, y0);
    x1 = min(this._width, x1); y1 = min(this._height, y1);
    if (x0 >= x1 || y0 >= y1) return;
    /* O(_rectLimit), never bounded by residents or map area. Merging the two oldest
     * rectangles over-invalidates, which only costs recomputation.
     * No topology exists yet: C67.5 must also invalidate incident graph edges. */
    this._stats.invalidations++;
    this._rects.append({ x0 = x0, y0 = y0, x1 = x1, y1 = y1, serial = ++this._serial });
    if (this._rects.len() > this._rectLimit) {
      local a = this._rects[0], b = this._rects[1];
      this._rects[1] = { x0 = min(a.x0, b.x0), y0 = min(a.y0, b.y0),
        x1 = max(a.x1, b.x1), y1 = max(a.y1, b.y1), serial = max(a.serial, b.serial) };
      this._rects.remove(0);
    }
    /* Pending requests are stamped when their computation begins; only the active one
     * holds partial aggregates of an older generation. */
    if (this._active != null && this._intersects(this._active.id, x0, y0, x1, y1)) {
      local id = this._active.id;
      this._active = null;
      if (this._requests[id].priority == 1) this._urgent.Push(id);
      else this._background.Push(id);
      this._stats.cancelled++;
    }
  }

  /* C67.4: withdraw one request, including the block being computed. */
  function Cancel(id) {
    if (!(id in this._requests)) return false;
    if (this._active != null && this._active.id == id) this._active = null;
    this._urgent.Remove(id);
    this._background.Remove(id);
    delete this._requests[id];
    this._stats.withdrawn++;
    return true;
  }

  /* Slots the background may still fill without ever forcing an eviction. */
  function BackgroundRoom() {
    return this._capacity - this._cache.len() - this._requests.len();
  }

  function BlockCount() { return this._nx * this._ny; }

  function PendingCount() { return this._requests.len(); }

  function HasUrgent() { return this._urgent.head != null; }

  function Stats() {
    local out = clone this._stats;
    out.rawset("resident", this._cache.len());
    out.rawset("pending", this._requests.len());
    out.rawset("active", this._active == null ? 0 : 1);
    out.rawset("rects", this._rects.len());
    return out;
  }
}
