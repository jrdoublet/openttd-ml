/* C67.3: control and both block sizes use the same staged production sources.
 * Telemetry uses <31-char signs so the savegame decoder sees it without log level changes. */
require("budget.nut");
require("terrain_map.nut");

class TerrainBenchProbe extends AIController {
  _signIndex = 0;

  function Emit(phase, key, value) {
    local name = "C67|" + phase + "|" + key + "|" + value;
    if (name.len() > 31) throw "C67 telemetry exceeds sign limit";
    local w = AIMap.GetMapSizeX();
    local h = AIMap.GetMapSizeY();
    local x = w / 2 - 20 + this._signIndex % 40;
    local y = h / 2 - 2 + this._signIndex / 40;
    this._signIndex++;
    local signId = AISign.BuildSign(AIMap.GetTileIndex(x, y), name);
    if (!AISign.IsValidSign(signId))
      throw "C67 telemetry sign failed";
  }

  function RunBlock(map, id) {
    local status = map.Request(id);
    if (status == "invalid" || status == "full") throw "C67 request failed";
    for (local i = 0; i < 20000 && map.Peek(id).status != "ready"; i++)
      if (map.Step(1000, AIController.GetTick() + 1000) == "idle")
        AIController.Sleep(1);
    if (map.Peek(id).status != "ready") throw "C67 request incomplete";
    return map.Peek(id).summary;
  }

  function CheckOracle(source, side, id, summary) {
    local nx = (source.Width() + side - 1) / side;
    local x0 = (id % nx) * side;
    local y0 = (id / nx) * side;
    local count = 0, water = 0, coast = 0, flat = 0, buildable = 0;
    local sum = 0, lo = null, hi = null;
    for (local y = y0; y < min(source.Height(), y0 + side); y++) {
      for (local x = x0; x < min(source.Width(), x0 + side); x++) {
        local t = source.Read(x, y);
        if (t == null) continue;
        count++;
        if (t.water) water++;
        if (t.coast) coast++;
        if (t.flat) flat++;
        if (t.buildable) buildable++;
        sum += t.lo;
        lo = lo == null ? t.lo : min(lo, t.lo);
        hi = hi == null ? t.hi : max(hi, t.hi);
      }
    }
    return summary.sample_count == count && summary.water_count == water
      && summary.coast_count == coast && summary.flat_count == flat
      && summary.buildable_count == buildable && summary.height_min_sum == sum
      && summary.height_min == lo && summary.height_max == hi;
  }

  function Phase(map, phase, mark, startTick, before) {
    local ops = OpexOpsMeasureEnd(mark);
    local stats = map.Stats();
    this.Emit(phase, "ops", ops);
    this.Emit(phase, "ticks", AIController.GetTick() - startTick);
    this.Emit(phase, "reads", stats.reads - before.reads);
    this.Emit(phase, "hits", stats.hits - before.hits);
    this.Emit(phase, "evict", stats.evictions - before.evictions);
    this.Emit(phase, "resident", stats.resident);
    this.Emit(phase, "done", stats.completed - before.completed);
    this.Emit(phase, "max", stats.ops_max);
    this.Emit(phase, "tilemax", stats.read_ops_max);
  }

  function Start() {
    local side = AIController.GetSetting("allocate");
    local full = AIController.GetSetting("full");
    if (side != 0 && side != 5 && side != 10) throw "C67 side invalid";
    this.Emit("meta", "side", side);
    this.Emit("meta", "full", full);
    this.Emit("meta", "width", AIMap.GetMapSizeX());
    this.Emit("meta", "height", AIMap.GetMapSizeY());
    local source = OpexTerrainSource();
    local points = [];
    local fingerprint = 0;
    for (local i = 0; i < 64; i++) {
      local x = (i * 97 + 13) % source.Width();
      local y = (i * 193 + 29) % source.Height();
      points.append([x, y]);
      local t = source.Read(x, y);
      if (t != null) fingerprint += (i + 1) * (t.lo + t.hi + (t.water ? 3 : 0)
        + (t.flat ? 7 : 0));
    }
    this.Emit("meta", "finger", fingerprint);
    /* Control runs identical input checks and telemetry, without constructing the cache. */
    if (side == 0) {
      this.Emit("meta", "pass", 1);
      while (true) AIController.Sleep(1);
    }

    local map = OpexTerrainMap(side);
    this.Emit("init", "resident", map.Stats().resident);
    this.Emit("init", "reads", map.Stats().reads);
    local startTick = AIController.GetTick();
    local mark = OpexOpsMeasureBegin();
    local before = map.Stats();
    local seen = {};
    local oracleChecks = 0, oracleFails = 0;
    foreach (point in points) {
      local id = map.BlockId(point[0], point[1]);
      local result = this.RunBlock(map, id);
      if (!(id in seen) && oracleChecks < 16) {
        if (!this.CheckOracle(source, side, id, result)) oracleFails++;
        oracleChecks++;
        seen.rawset(id, true);
      }
    }
    this.Phase(map, "cold", mark, startTick, before);
    this.Emit("cold", "oracle", oracleChecks);
    this.Emit("cold", "errors", oracleFails);
    if (oracleFails > 0 || oracleChecks != 16) throw "C67 oracle failed";

    startTick = AIController.GetTick(); mark = OpexOpsMeasureBegin(); before = map.Stats();
    foreach (point in points) this.RunBlock(map, map.BlockId(point[0], point[1]));
    this.Phase(map, "warm", mark, startTick, before);

    if (full != 0) {
      local nx = (source.Width() + side - 1) / side;
      local ny = (source.Height() + side - 1) / side;
      startTick = AIController.GetTick(); mark = OpexOpsMeasureBegin(); before = map.Stats();
      for (local id = 0; id < nx * ny; id++) this.RunBlock(map, id);
      this.Phase(map, "scan", mark, startTick, before);
      this.Emit("scan", "blocks", nx * ny);
      this.Emit("scan", "area", source.Width() * source.Height());
      if (map.Stats().resident > 4096) throw "C67 cache bound";
      startTick = AIController.GetTick(); mark = OpexOpsMeasureBegin(); before = map.Stats();
      this.RunBlock(map, map.BlockId(points[0][0], points[0][1]));
      this.Phase(map, "evict", mark, startTick, before);
      local cornerId = map.BlockId(0, 0);
      map.InvalidateRect(0, 0, 1, 1);
      this.RunBlock(map, cornerId);
      this.Emit("invalidate", "ready", map.Peek(cornerId).status == "ready" ? 1 : 0);
    }
    this.Emit("meta", "pass", 1);
    while (true) AIController.Sleep(1);
  }
}
