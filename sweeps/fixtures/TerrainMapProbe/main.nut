/* The Python harness stages the exact production sources beside this fixture. */
require("budget.nut");
require("terrain_map.nut");

function C67Assert(ok, message) {
  if (!ok) throw "C67 FAIL: " + message;
}

class C67FakeSource {
  w = 13;
  h = 7;
  reads = 0;
  ops = 0;
  offset = 0;
  invalid = false;
  function Width() { return this.w; }
  function Height() { return this.h; }
  function Tick() { return this.ops / 10000; }
  function Mark() { return this.ops; }
  function Spent(mark) { return this.ops - mark; }
  function Remaining() { return 10000; }
  function Read(x, y) {
    C67Assert(x >= 0 && y >= 0 && x < this.w && y < this.h, "out of bounds");
    this.reads++;
    this.ops += 100;
    if (this.invalid || (x == 12 && y == 6)) return null;
    local z = x + y + this.offset;
    return { water = x % 2 == 0, coast = y == 0, lo = z,
      hi = z + (x + y) % 2, flat = (x + y) % 2 == 0, buildable = x % 2 == 1 };
  }
}

function C67Drain(map, source, budget) {
  for (local i = 0; i < 10000 && map.Stats().pending > 0; i++)
    map.Step(budget, source.Tick() + 1000);
  C67Assert(map.Stats().pending == 0, "drain did not finish");
}

function C67SyntheticTests() {
  local source = C67FakeSource();
  local m = OpexTerrainMap(5, 2, 2, source);
  C67Assert(source.reads == 0 && m.Peek(5).status == "absent", "lazy constructor");
  C67Assert(m.BlockId(12, 6) == 5 && m.BlockId(13, 6) == null, "edge geometry");
  C67Assert(m.Request(-1) == "invalid" && m.Request(0, 2) == "invalid", "input guard");
  C67Assert(m.Request(5) == "pending" && m.Request(5) == "pending", "dedup");
  m.Step(0, 1000); m.Step(1000, source.Tick());
  C67Assert(source.reads == 0, "expired/zero budget");
  m.Step(1, 1000);
  C67Assert(source.reads == 1 && m.Peek(5).summary == null, "private partial");
  C67Drain(m, source, 1);
  local s = m.Peek(5).summary;
  C67Assert(s.sample_count == 5 && s.invalid_count == 1, "partial block denominator");
  C67Assert(s.water_count == 3 && s.flat_count == 2 && s.buildable_count == 2, "counts");
  C67Assert(s.height_min == 15 && s.height_max == 18 && s.height_min_sum == 81, "heights");
  C67Assert(abs(s.water_ratio - 0.6) < 0.00001, "fractional ratio");
  s.water_count = -100;
  C67Assert(m.Peek(5).summary.water_count == 3, "snapshot isolation");
  local reads = source.reads;
  C67Assert(m.Request(5) == "ready", "warm request");
  C67Assert(source.reads == reads, "warm read has no terrain calls");

  local fastSource = C67FakeSource();
  local fast = OpexTerrainMap(5, 2, 2, fastSource);
  fast.Request(5); C67Drain(fast, fastSource, 100000);
  foreach (key in ["sample_count", "invalid_count", "height_min_sum", "water_count", "flat_count"])
    C67Assert(fast.Peek(5).summary[key] == m.Peek(5).summary[key], "resumption equivalence");

  m.Request(0); C67Drain(m, source, 100000);
  m.Peek(5); // 0 becomes least recently used.
  m.Request(1); C67Drain(m, source, 100000);
  C67Assert(m.Peek(0).status == "absent" && m.Peek(5).status == "ready", "LRU eviction");
  C67Assert(m.Stats().resident == 2 && m.Stats().evictions == 1, "cache bound");
  local oldVersion = m.Peek(5).generation;
  m.InvalidateRect(10, 5, 13, 7);
  C67Assert(m.Peek(5).status == "stale" && m.Peek(5).summary == null, "stale hidden");
  m.Request(5); m.Step(1, source.Tick() + 1000);
  source.offset = 100;
  m.InvalidateRect(12, 6, 13, 7);
  C67Drain(m, source, 100000);
  C67Assert(m.Peek(5).generation > oldVersion, "generation advanced");
  C67Assert(m.Peek(5).summary.height_min_sum == 581, "old partial discarded");
  C67Assert(m.Stats().cancelled == 1, "invalidation cancellation");

  m.Clear();
  C67Assert(m.Request(0, 0) == "pending" && m.Request(1, 0) == "pending", "queue fill");
  C67Assert(m.Request(2) == "full" && m.Stats().pending == 2, "queue limit");
  m.Request(1, 1); // Promotion must not duplicate its background entry.
  m.Step(2500, source.Tick() + 1000);
  C67Assert(m.Peek(1).status == "ready" && m.Peek(0).status == "pending", "priority");
  C67Drain(m, source, 100000);
  C67Assert(m.Stats().completed == 2, "no duplicate completion after promotion");

  m.Clear(); m.Request(0, 0); m.Step(1, source.Tick() + 1000);
  m.Request(1, 1); m.Step(2500, source.Tick() + 1000);
  C67Assert(m.Peek(1).status == "ready", "urgent preempts background partial");
  C67Drain(m, source, 1);
  C67Assert(m.Peek(0).status == "ready", "background can resume");

  source.invalid = true;
  m.Clear(); m.Request(5); C67Drain(m, source, 100000);
  C67Assert(m.Peek(5).summary.water_ratio == null && m.Peek(5).summary.height_min == null,
    "all invalid is unknown");
  local large = C67FakeSource(); large.w = 2048; large.h = 2048;
  local grid5 = OpexTerrainMap(5, 2, 2, large);
  local grid10 = OpexTerrainMap(10, 2, 2, large);
  C67Assert(grid5.BlockId(2047, 2047) == 168099, "2048 grid5");
  C67Assert(grid10.BlockId(2047, 2047) == 42024 && large.reads == 0, "2048 grid10 lazy");
  grid10.Request(42024); C67Drain(grid10, large, 1);
  C67Assert(grid10.Peek(42024).summary.sample_count == 64, "10x10 partial edge");
  local bounded = OpexTerrainMap(5, 4096, 256, large);
  for (local i = 0; i < 256; i++) C67Assert(bounded.Request(i) == "pending", "default queue fill");
  C67Assert(bounded.Request(256) == "full" && bounded.Stats().pending == 256, "257th request refused");
  bounded.Clear();
  C67Assert(bounded.Stats().pending == 0 && bounded.Stats().resident == 0, "clear pending queue");
  C67LifecycleTests();
  AILog.Info("C67_SYNTHETIC_PASS");
}

/* C67.4 (contract section 14): lazy invalidation, background without eviction, cancel. */
function C67LifecycleTests() {
  local source = C67FakeSource();
  local m = OpexTerrainMap(5, 2, 2, source);
  m.Request(0); C67Drain(m, source, 100000);
  local hits = m.Stats().hits;
  C67Assert(m.Request(0, 0) == "ready" && m.Stats().hits == hits, "background probe is silent");
  m.Request(1); C67Drain(m, source, 100000);
  C67Assert(m.BackgroundRoom() == 0 && m.Request(2, 0) == "full", "background refused when full");
  C67Assert(m.Stats().bg_refused == 1 && m.Stats().evictions == 0, "background never evicts");

  m.Clear(); m.Request(0); C67Drain(m, source, 100000);
  C67Assert(m.Request(1, 0) == "pending" && m.Request(2, 1) == "pending", "mixed queue");
  C67Drain(m, source, 100000);
  C67Assert(m.Peek(2).status == "ready" && m.Peek(1).status == "absent", "background result dropped");
  C67Assert(m.Stats().bg_dropped == 1 && m.Stats().evictions == 0, "dropped, not evicted");

  m.Clear(); m.Request(5);
  m.InvalidateRect(10, 5, 13, 7); // Before the computation begins: not stale afterwards.
  C67Drain(m, source, 100000);
  C67Assert(m.Peek(5).status == "ready", "generation stamped at computation start");
  local reads = source.reads;
  for (local i = 0; i < 40; i++) m.InvalidateRect(0, 0, 1, 1);
  C67Assert(m.Stats().rects <= 32 && source.reads == reads, "bounded rectangles, no reads");
  C67Assert(m.Peek(5).status == "stale", "merged rectangle stays conservative");
  C67Assert(m.Stats().invalidations == 41, "invalidation count");

  m.Clear(); m.Request(0); m.Step(1, source.Tick() + 1000);
  C67Assert(m.Cancel(0) && !m.Cancel(0), "cancel active once");
  C67Assert(m.PendingCount() == 0 && m.Peek(0).status == "absent", "cancel leaves nothing");
  C67Drain(m, source, 100000);
  C67Assert(m.Stats().completed == 0 && m.Stats().withdrawn == 1, "cancelled block not published");
  AILog.Info("C67_LIFECYCLE_PASS");
}

class TerrainMapProbe extends AIController {
  function Start() {
    C67SyntheticTests();
    /* Also execute the actual NoAI source on both granularities, independently of fake clock. */
    foreach (side in [5, 10]) {
      local source = OpexTerrainSource();
      local m = OpexTerrainMap(side, 2, 2, source);
      local id = m.BlockId(AIMap.GetMapSizeX() / 2, AIMap.GetMapSizeY() / 2);
      m.Request(id);
      C67Drain(m, source, 2000);
      C67Assert(m.Peek(id).status == "ready", "real map ready");
      C67Assert(m.Peek(id).summary.sample_count == side * side, "real interior area");
      AILog.Info("C67_REAL_PASS side=" + side + " ops_max=" + m.Stats().ops_max);
    }
    local tile = AIMap.GetTileIndex(AIMap.GetMapSizeX() / 2, AIMap.GetMapSizeY() / 2);
    AISign.BuildSign(tile, "C67|PASS");
    AILog.Info("C67_ALL_PASS");
    // Fixture completed: keep the company alive until the harness horizon.
    while (true) AIController.Sleep(1);
  }
}
