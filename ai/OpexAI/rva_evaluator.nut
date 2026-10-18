/* RVA-12 : one observation job, one tile/part/station per unit of slack.
 * No command, candidate mutation, score or persistent state. Busy jobs are
 * reported, never silently replaced. Model 1: uniform production per house;
 * unlike a game rule this prior is uncertain for heterogeneous/NewGRF houses.
 * Complete-inventory reference implementation: sweeps/rva_demand.py.
 * All stations of a company share its best capture, then split by rating sum
 * (15.3 station_cmd.cpp:4635-4660). No equal-share rival constant.
 */
RVA_EVAL_WORK <- null;
RVA_EVAL_SERIAL <- 0;
RVA_EVAL_OPS <- 0;
RVA_EVAL_PEAK <- 0;

function OpexRvaResetTransient()
{
  RVA_EVAL_WORK = null;
  RVA_EVAL_SERIAL = 0;
  RVA_EVAL_OPS = 0;
  RVA_EVAL_PEAK = 0;
  RVA_CYCLE_STATE = null;
  RVA_CYCLE_OPS = 0;
  RVA_CYCLE_CALLS = 0;
  RVA_CYCLE_SKIPS = 0;
  RVA_CYCLE_MODEL_OPS = 0;
}

function OpexRvaProjectKey(c)
{
  return "rail|" + c.src + "|" + c.dst + "|" + c.cargo + "|" + c.kind;
}

function OpexRvaObserveAttempt(candidate, result, lineId)
{
  if (candidate.kind != "pax") return;
  RVA_EVAL_SERIAL++;
  local id = RVA_EVAL_SERIAL;
  OpexDecide("RVA_ATTEMPT", "v=1 id=" + id + " key=" + OpexRvaProjectKey(candidate)
      + " date=" + AIDate.GetCurrentDate() + " ok=" + (result.ok ? 1 : 0)
      + " line=" + (result.ok ? lineId : "na"));
  if (!result.ok || result.platformA == null || result.platformB == null) return;
  if (RVA_EVAL_WORK != null) {
    OpexDecide("RVA_EVAL_SKIP", "id=" + id + " reason=busy");
    return;
  }
  // Snapshot scalar economics. No reference to a mutable candidate/line kept.
  local second = ("cargo2" in candidate) && ("perTrain2" in candidate)
      && candidate.perTrain2 > 0;
  local cargos = [{ cargo = candidate.cargo, cap = candidate.monthlyCapacity,
      carried = candidate.carried,
      revenue = candidate.revenueAnnual - (second ? candidate.revenue2 : 0) }];
  if (second) cargos.append({ cargo = candidate.cargo2,
      cap = candidate.trains * candidate.perTrain2 * candidate.tripsPerMonth,
      carried = candidate.carried2, revenue = candidate.revenue2 });
  local plans = [];
  foreach (p in [result.platformA, result.platformB])
    plans.append({ anchor = p.anchor, step = p.step, length = p.length });
  RVA_EVAL_WORK = { id = id, key = OpexRvaProjectKey(candidate), line = lineId,
      date = AIDate.GetCurrentDate(), phase = "footprint", plans = plans, pi = 0, part = 0,
      footprint = AITileList(), radius = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN),
      excludeA = AIStation.GetStationID(result.stationA), excludeB = AIStation.GetStationID(result.stationB),
      cargos = cargos, ci = 0, own = [], stations = null, stationCursor = null,
      cursor = null, scan = null, demand = 0.0, ownDelta = 0.0, ownOverlap = false,
      revenue = 0.0, complete = true, lineComplete = true, cargoComplete = true,
      townWeights = {}, running = candidate.runningAnnual,
      amort = candidate.amortAnnual, newRaw = candidate.stationRating * 255.0 / 100.0,
      calls = 0, ops = 0, cargoStatus = "not_started" };
}

function OpexRvaAddCoverage(list, tile, radius)
{
  local x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
  local x0 = x - radius, x1 = x + radius, y0 = y - radius, y1 = y + radius;
  if (x0 < 0) x0 = 0;
  if (y0 < 0) y0 = 0;
  if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
  if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
  list.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
}

function OpexRvaEvalUnit(w)
{
  if (w.phase == "footprint") {
    local p = w.plans[w.pi];
    OpexRvaAddCoverage(w.footprint, p.anchor + p.step * w.part, w.radius);
    w.part++;
    if (w.part >= p.length) { w.part = 0; w.pi++; }
    if (w.pi >= w.plans.len()) w.phase = "cargo";
    return;
  }
  local cargo = w.cargos[w.ci].cargo;
  if (w.phase == "cargo") {
    w.cargoComplete = true;
    w.townWeights = {};
    local dist = OpexRvaDistribution(cargo);
    w.cargoStatus = dist != null ? dist.status : "invalid_cargo";
    if (dist == null || !dist.manual || !AIGameSettings.IsValid("station.modified_catchment")
        || AIGameSettings.GetValue("station.modified_catchment") == 0
        || !AIGameSettings.IsValid("economy.timekeeping_units")
        || AIGameSettings.GetValue("economy.timekeeping_units") != 0) {
      // Per-tile API expands radius to 4 when modified catchment is OFF.
      w.complete = false;
      w.cargoComplete = false;
      w.lineComplete = false;
      w.phase = "cargo_done";
      return;
    }
    w.stations = AIStationList(AIStation.STATION_ANY);
    w.stationCursor = w.stations.Begin();
    w.own = []; w.demand = 0.0; w.ownDelta = 0.0; w.ownOverlap = false;
    w.phase = "stations";
    return;
  }
  if (w.phase == "stations") {
    if (w.stations.IsEnd()) {
      w.cursor = w.footprint.Begin(); w.phase = "tiles";
      return;
    }
    local st = w.stationCursor;
    if (st != w.excludeA && st != w.excludeB && AIStation.HasCargoRating(st, cargo)) {
      w.own.append({ station = st, tiles = AITileList_StationCoverage(st),
          raw = AIStation.GetCargoRating(st, cargo) * 255.0 / 100.0,
          waiting = AIStation.GetCargoWaiting(st, cargo) });
    }
    w.stationCursor = w.stations.Next();
    return;
  }
  if (w.phase == "tiles") {
    if (w.footprint.IsEnd()) { w.phase = "cargo_done"; return; }
    local tile = w.cursor;
    if (w.scan == null) {
      local weight = AITile.GetCargoProduction(tile, cargo, 1, 1, 0);
      local town = AITile.GetTownAuthority(tile);
      if (weight < 0 || (weight > 0 && (!AITile.IsHouseTile(tile) || !AITown.IsValidTown(town)))) {
        w.complete = false;
        w.cargoComplete = false;
        w.lineComplete = false;
      }
      local production = 0.0;
      if (weight > 0 && AITile.IsHouseTile(tile) && AITown.IsValidTown(town)) {
        local houses = AITown.GetHouseCount(town);
        if (!(town in w.townWeights)) w.townWeights.rawset(town, 0);
        w.townWeights[town] += weight;
        if (houses <= 0 || w.townWeights[town] > houses) {
          w.complete = false; w.cargoComplete = false; w.lineComplete = false;
        } else production = AITown.GetLastMonthProduction(town, cargo) * weight.tofloat() / houses;
      }
      w.scan = { production = production, si = 0, sum = 0.0, maxRaw = 0.0 };
      return;
    }
    local s = w.scan;
    if (s.si < w.own.len()) {
      local station = w.own[s.si++];
      if (station.tiles.HasItem(tile)) {
        s.sum += station.raw;
        if (station.raw > s.maxRaw) s.maxRaw = station.raw;
      }
      return;
    }
    local best = w.newRaw > s.maxRaw ? w.newRaw : s.maxRaw;
    local captured = best > 0 ? s.production * (best + 1.0) / 256.0 : 0.0;
    local added = w.newRaw + s.sum > 0 ? captured * w.newRaw / (w.newRaw + s.sum) : 0.0;
    w.demand += added;
    w.ownDelta += captured - (s.sum > 0 ? s.production * (s.maxRaw + 1.0) / 256.0 : 0.0);
    if (s.sum > 0 && s.production > 0) w.ownOverlap = true;
    w.scan = null;
    w.cursor = w.footprint.Next();
    return;
  }
  if (w.phase == "cargo_done") {
    local c = w.cargos[w.ci];
    local carried = w.cargoComplete ? (w.demand < c.cap ? w.demand : c.cap) : null;
    local revenue = carried != null && c.carried > 0 ? carried * c.revenue / c.carried : null;
    if (revenue == null) { w.complete = false; w.lineComplete = false; }
    else w.revenue += revenue;
    OpexDecide("RVA_EVAL_CARGO", "id=" + w.id + " line=" + w.line + " cargo=" + cargo
        + " status=" + (w.cargoComplete ? w.cargoStatus : "reference_fallback_incomplete")
        + " demand_month=" + (w.cargoComplete ? w.demand : "na")
        + " own_delta_month=" + (w.cargoComplete ? w.ownDelta : "na")
        + " own_overlap=" + (w.cargoComplete ? (w.ownOverlap ? 1 : 0) : "na")
        + " carried_month=" + (carried != null ? carried : "na")
        + " revenue_annual=" + (revenue != null ? revenue : "na")
        + " normalizer=town_house_prior rivals=unobserved");
    // Any own overlap needs service marginal final receipts, absent in this snapshot.
    if (w.ownOverlap) w.complete = false;
    w.ci++;
    w.demand = 0.0; w.ownDelta = 0.0; w.ownOverlap = false;
    w.phase = w.ci < w.cargos.len() ? "cargo" : "done";
  }
}

function OpexRvaEvalStep()
{
  if (RVA_EVAL_WORK == null) return;
  if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN
      || AIController.GetOpsTillSuspend() < RVA_EVAL_PEAK + C67_SLACK_RESERVE) return;
  local mark = OpexOpsMeasureBegin();
  local w = RVA_EVAL_WORK;
  // Month rollover makes the multi-visit snapshot incomparable; discard explicitly.
  if (AIDate.GetYear(w.date) != AIDate.GetYear(AIDate.GetCurrentDate())
      || AIDate.GetMonth(w.date) != AIDate.GetMonth(AIDate.GetCurrentDate())) {
    OpexDecide("RVA_EVAL_ABORT", "id=" + w.id + " reason=month_changed");
    RVA_EVAL_WORK = null;
    return;
  }
  if (w.phase == "done") {
    OpexDecide("RVA_EVAL", "v=1 id=" + w.id + " key=" + w.key + " line=" + w.line
        + " date_begin=" + w.date + " date_end=" + AIDate.GetCurrentDate()
        + " status=" + (w.complete ? "estimated_no_rivals" : "reference_fallback")
        + " profit_line=" + (w.lineComplete ? (w.revenue - w.running - w.amort) : "na")
        + " gain_company=" + (w.complete ? (w.revenue - w.running - w.amort) : "na")
        + " calls=" + w.calls + " completed_ops=" + w.ops);
    RVA_EVAL_WORK = null;
  } else {
    // Consume only available slack; unit cost learnt within this visit.
    local unitPeak = RVA_EVAL_PEAK;
    while (w.phase != "done" && AIController.GetOpsTillSuspend() >= C67_SLACK_MIN
        && AIController.GetOpsTillSuspend() >= unitPeak + C67_SLACK_RESERVE) {
      local unitMark = OpexOpsMeasureBegin();
      OpexRvaEvalUnit(w);
      w.calls++;
      local unitOps = OpexOpsMeasureEnd(unitMark);
      if (unitOps > unitPeak) unitPeak = unitOps;
      if (unitOps > RVA_EVAL_PEAK) RVA_EVAL_PEAK = unitOps;
    }
  }
  local ops = OpexOpsMeasureEnd(mark);
  w.ops += ops; RVA_EVAL_OPS += ops;
}
