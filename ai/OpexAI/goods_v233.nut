/* V233: bounded observation of GLOBAL factory output, not proof of our contribution.
 * No projects are inserted by this observer. No API calls from the save codec. */
function OpexV233ObservationKey(factory, cargo, station)
{
  return factory + "|" + cargo + "|" + station;
}

function OpexV233Sample(row, month, quantity)
{
  if (row.lastMonth == month) return false;
  if (row.lastMonth != month - 1) {
    row.count = 0;
    row.q0 = 0; row.q1 = 0; row.q2 = 0;
  }
  row.q2 = row.q1; row.q1 = row.q0; row.q0 = quantity;
  row.count = row.count < 3 ? row.count + 1 : 3;
  row.lastMonth = month;
  return true;
}

function OpexV233Quantity(row, month)
{
  if (row == null || row.count != 3 || row.lastMonth != month) return 0;
  local q = row.q0 < row.q1 ? row.q0 : row.q1;
  if (row.q2 < q) q = row.q2;
  return q >= V233_GOODS_MIN_MONTHLY ? q : 0;
}

function OpexV233Support(line)
{
  if (line == null || !("mode" in line) || line.mode != "rail"
      || !("kind" in line) || line.kind != "freight"
      || (("scrapping" in line) && line.scrapping)
      || !("dstIndustry" in line) || !AIIndustry.IsValidIndustry(line.dstIndustry)
      || !("platformB" in line) || line.platformB == null) return null;
  local station = OpexLineStationId(line, "B");
  if (station < 0 || !AIStation.IsValidStation(station)
      || !AICompany.IsMine(AITile.GetOwner(line.stationB))) return null;
  local accepting = AICargoList_StationAccepting(station);
  if (!accepting.HasItem(line.cargo)) return null;
  return { factoryId = line.dstIndustry, factoryTile = AIIndustry.GetLocation(line.dstIndustry),
           stationId = station, stationTile = line.stationB, line = line };
}

function OpexV233SaveObservations(rows)
{
  local out = [];
  if (rows != null) foreach (key, row in rows) {
    if (row.count < 1 || row.lastMonth < 0) continue;
    out.append([row.factoryId, row.factoryTile, row.cargo, row.stationId, row.stationTile,
                row.lastMonth, row.q0, row.q1, row.q2, row.count]);
  }
  return { version = 1, rows = out };
}

function OpexV233LoadObservations(data)
{
  local out = {};
  if (data == null || typeof data != "table" || !("version" in data) || data.version != 1
      || !("rows" in data) || typeof data.rows != "array") return out;
  foreach (tuple in data.rows) {
    if (typeof tuple != "array" || tuple.len() != 10) continue;
    local valid = true;
    foreach (value in tuple) if (typeof value != "integer" || value < 0) valid = false;
    if (!valid || tuple[9] < 1 || tuple[9] > 3) continue;
    local row = { factoryId = tuple[0], factoryTile = tuple[1], cargo = tuple[2],
                  stationId = tuple[3], stationTile = tuple[4], lastMonth = tuple[5],
                  q0 = tuple[6], q1 = tuple[7], q2 = tuple[8], count = tuple[9] };
    out[OpexV233ObservationKey(row.factoryId, row.cargo, row.stationId)] <- row;
  }
  return out;
}

function OpexAI::_v233GoodsStep()
{
  local date = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  local work = this._v233GoodsWork;
  if (work == null || work.month != month) {
    if (DECISION_LOG && work != null && work.phase != "done")
      OpexDecide("V233_DROP", "reason=month_coverage month=" + work.month);
    work = { month = month, phase = "index", lineCursor = 0, rows = {},
             keys = [], cursor = 0, supports = {} };
    this._v233GoodsWork = work;
  }
  if (work.phase == "index") {
    /* Rebuild monthly even if fleet is unchanged. Eight lines maximum per invocation.
     * Cargo enumeration is bounded by the engine's cargo limit (64). */
    for (local n = 0; n < 8 && work.lineCursor < this._lines.len(); n++) {
      local support = OpexV233Support(this._lines[work.lineCursor++]);
      if (support == null) continue;
      local produced = AIIndustryType.GetProducedCargo(AIIndustry.GetIndustryType(support.factoryId));
      for (local cargo = produced.Begin(); !produced.IsEnd(); cargo = produced.Next()) {
        if (AICargo.GetTownEffect(cargo) != AICargo.TE_GOODS) continue;
        if (OpexV207PlatformUnionValue(support.line.platformB, cargo, this._catalog.railCoverage) <= 0) continue;
        local key = OpexV233ObservationKey(support.factoryId, cargo, support.stationId);
        if (key in work.rows) continue;
        local row = null;
        if (this._v233GoodsObservations != null && key in this._v233GoodsObservations) {
          local saved = this._v233GoodsObservations[key];
          if (saved.factoryTile == support.factoryTile && saved.stationTile == support.stationTile
              && saved.lastMonth <= month) row = saved;
        }
        if (row == null) row = { factoryId = support.factoryId, factoryTile = support.factoryTile,
          cargo = cargo, stationId = support.stationId, stationTile = support.stationTile,
          lastMonth = -1, q0 = 0, q1 = 0, q2 = 0, count = 0 };
        work.rows[key] <- row;
        work.supports[key] <- support.line;
        work.keys.append(key);
      }
    }
    if (work.lineCursor < this._lines.len()) return;
    this._v233GoodsObservations = work.rows;
    work.phase = "observe";
    return;
  }
  if (work.phase != "observe") return;
  if (work.cursor >= work.keys.len()) { work.phase = "done"; return; }
  local key = work.keys[work.cursor++];
  local row = work.rows[key];
  local support = OpexV233Support(work.supports[key]);
  if (support == null || support.factoryTile != row.factoryTile
      || support.stationId != row.stationId || support.stationTile != row.stationTile) {
    delete work.rows[key];
    return;
  }
  local quantity = AIIndustry.GetLastMonthProduction(row.factoryId, row.cargo);
  if (quantity < 0) { delete work.rows[key]; return; }
  if (!OpexV233Sample(row, month, quantity)) return;
  if (DECISION_LOG) {
    OpexDecide("V233_OBS", "factory=" + row.factoryId + " cargo=" + row.cargo
      + " station=" + row.stationId + " month=" + month + " global_output=" + quantity
      + " count=" + row.count);
    if (OpexV233Quantity(row, month) > 0)
      OpexDecide("V233_ELIGIBLE", "factory=" + row.factoryId + " cargo=" + row.cargo
        + " station=" + row.stationId + " month=" + month + " quantity=" + OpexV233Quantity(row, month));
  }
}
