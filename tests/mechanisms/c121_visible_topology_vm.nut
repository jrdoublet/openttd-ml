FXVT_CACHE <- {};
FXVT_CALLS <- 0;
FXVT_DEPTH_DONE <- {};
function FxVTInvalidate(reason)
{
  local kept = reason == "age" || reason == "input";
  AILog.Info("C121_VISIBLE_TOPOLOGY_INVALIDATE reason=" + reason + " kept=" + (kept ? 1 : 0)
      + " entries=" + FXVT_CACHE.len());
  if (!kept) FXVT_CACHE.clear();
}
function FxVTShadowCoverage(stationId)
{
  local empty = [];
  if (!AIStation.IsValidStation(stationId)) return empty;
  if (stationId in FXVT_CACHE) return FXVT_CACHE[stationId];
  local out = [];
  local tiles = AITileList_StationCoverage(stationId);
  foreach (tile, value in tiles) out.append(tile);
  FXVT_CACHE.rawset(stationId, out);
  return out;
}
function FxVTGeometryEqual(a, b)
{
  if (a.len() != b.len()) return false;
  local ids = {};
  foreach (tile in a) ids.rawset(tile, true);
  foreach (tile in b) if (!(tile in ids)) return false;
  return ids.len() == a.len();
}
function OpexC121StationCoverageTiles(stationId)
{
  local oldHit = stationId in AIR_C121_STATION_COVERAGE_CACHE;
  local newHit = stationId in FXVT_CACHE;
  local mark = FxVRMark();
  local original = FxVTOriginalCoverage(stationId);
  local originalOps = FxVRSpent(mark);
  mark = FxVRMark();
  local shadow = FxVTShadowCoverage(stationId);
  local shadowOps = FxVRSpent(mark);
  // Independent fresh API oracle, excluded from both measured costs.
  local fresh = [];
  if (AIStation.IsValidStation(stationId)) {
    local tiles = AITileList_StationCoverage(stationId);
    foreach (tile, value in tiles) fresh.append(tile);
  }
  if (!FxVTGeometryEqual(original, shadow) || !FxVTGeometryEqual(fresh, shadow))
    throw "C121_VISIBLE_TOPOLOGY_ASSERT geometry";
  FXVT_CALLS++;
  AILog.Info("C121_VISIBLE_TOPOLOGY_CASE case=" + FXVT_CALLS + " station=" + stationId
      + " old_hit=" + (oldHit ? 1 : 0) + " new_hit=" + (newHit ? 1 : 0)
      + " tiles=" + shadow.len() + " original_ops=" + originalOps + " shadow_ops=" + shadowOps);
  if (FXVT_CALLS == 1) AILog.Info("C121_VISIBLE_TOPOLOGY_WORLD pass=1");
  return original;
}
function FxVTDepthMatrix(catalog, quote, plane, pax, mail, target)
{
  if (target == null) return;
  foreach (extra in [0, 1]) {
    if (extra in FXVT_DEPTH_DONE) continue;
    local have = target.fleetScanCap+extra;
    local date = AIDate.GetCurrentDate();
    local expected = OpexC121AirEconomics(catalog, quote, plane, pax, mail, 0);
    local before = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have);
    local after = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have+1);
    local capture = { have = have, values = {} };
    local fused = FxVRFused(catalog, quote, plane, pax, mail, 0, false, null, null, null, capture);
    local fallback = 0;
    foreach (n in [have, have+1]) if (!(n in capture.values)) {
      capture.values.rawset(n, OpexC121AirEconomics(catalog, quote, plane, pax, mail, n));
      fallback++;
    }
    if (date != AIDate.GetCurrentDate()) continue;
    if (!FxVREqual(expected, fused)) throw "C121_VISIBLE_TOPOLOGY_ASSERT depth_target";
    foreach (field in ["profitAnnual", "revenueAnnual", "realizationFactor"])
      if (before[field] != capture.values[have][field] || after[field] != capture.values[have+1][field])
        throw "C121_VISIBLE_TOPOLOGY_ASSERT depth_margin";
    if (fallback != extra+1) throw "C121_VISIBLE_TOPOLOGY_ASSERT fallback";
    FXVT_DEPTH_DONE.rawset(extra, true);
    AILog.Info("C121_VISIBLE_TOPOLOGY_DEPTH extra=" + extra + " have=" + have
        + " cap=" + target.fleetScanCap + " fallback=" + fallback + " equal=1");
  }
}
