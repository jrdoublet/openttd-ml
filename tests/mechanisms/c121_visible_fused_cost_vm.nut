FXVF_CASES <- 0;
FXVF_INPUT <- null;
function FxVFInput(quote, pax, mail, have)
{
  FXVF_INPUT = { quote = quote, pax = pax, mail = mail, have = have,
    realization = OpexC121RealizationFactor(quote), trip = OpexC121AirTripModel(quote, quote.plane) };
}
function FxVFInputEqual(a, b)
{
  if (typeof a != typeof b) return false;
  if (typeof a == "table") {
    if (a.len() != b.len()) return false;
    foreach (key, value in a) {
      if (typeof key == "string" && (key.find("Ops") != null || key.find("Ticks") != null)) continue;
      if (!(key in b) || !FxVFInputEqual(value, b[key])) return false;
    }
    return true;
  }
  if (typeof a == "array") {
    if (a.len() != b.len()) return false;
    for (local i = 0; i < a.len(); i++) if (!FxVFInputEqual(a[i], b[i])) return false;
    return true;
  }
  return a == b;
}
function FxTLStart(ai) { }
function FxTLWorld(ai) { }
function FxVFMark() { return { tick = AIController.GetTick(), ops = AIController.GetOpsTillSuspend() }; }
function FxVFSpent(mark)
{
  local left = AIController.GetOpsTillSuspend();
  local ticks = AIController.GetTick()-mark.tick;
  return ticks <= 0 ? mark.ops-left : mark.ops+(ticks-1)*OPS_PER_TICK+(OPS_PER_TICK-left);
}
function FxVFCaches()
{
  return { fleet = clone C121_VISIBLE_FLEET_CACHE, endpoint = C121_AIR_ENDPOINT_CACHE == null ? null : clone C121_AIR_ENDPOINT_CACHE,
    geometry = clone AIR_C121_STATION_COVERAGE_CACHE, rival = clone C121_VISIBLE_AIRPORT_CACHE,
    kdecDate = C69_CACHED_KDEC_DATE, kdecValue = C69_CACHED_KDEC_VALUE };
}
function FxVFRestore(s)
{
  C121_VISIBLE_FLEET_CACHE = s.fleet;
  C121_AIR_ENDPOINT_CACHE = s.endpoint;
  AIR_C121_STATION_COVERAGE_CACHE = s.geometry;
  C121_VISIBLE_AIRPORT_CACHE = s.rival;
  C69_CACHED_KDEC_DATE = s.kdecDate;
  C69_CACHED_KDEC_VALUE = s.kdecValue;
}
function FxVFFields(line)
{
  local out = {};
  foreach (field in ["targetAirPlanes", "c121TargetPlanes", "c121MarginalProfit", "c121MarginalRevenue", "c121RealizationPmAtBuild"])
    if (field in line) out.rawset(field, line[field]);
  return out;
}
function OpexC121RefreshVisibleFleet(catalog, line, lines, force = false)
{
  if (line == null || !("lineId" in line) || !("vehicles" in line)) {
    FxVFCandidate(catalog, line, lines, force); return;
  }
  local date = AIDate.GetCurrentDate();
  if (!force && line.lineId in C121_VISIBLE_FLEET_CACHE) {
    local state = C121_VISIBLE_FLEET_CACHE[line.lineId];
    if (date >= state.date && date-state.date < 30 && state.vehicles == line.vehicles.len()
        && state.epoch == C121_CATALOG_ENDPOINT_EPOCH) { FxVFCandidate(catalog, line, lines, force); return; }
  }
  local initial = clone line;
  local caches = FxVFCaches();
  local savedFused = C121_AIR_VISIBLE_FUSED;
  C121_AIR_VISIBLE_FUSED = false;
  local mark = FxVFMark();
  FXVF_INPUT = null;
  FxVFOriginal(catalog, line, lines, force);
  local originalOps = FxVFSpent(mark);
  C121_AIR_VISIBLE_FUSED = savedFused;
  local expected = FxVFFields(line);
  local input = FXVF_INPUT;
  local quoted = line.lineId in C121_VISIBLE_FLEET_CACHE
    && (!(line.lineId in caches.fleet) || C121_VISIBLE_FLEET_CACHE[line.lineId] != caches.fleet[line.lineId]);
  line.clear();
  foreach (field, value in initial) line.rawset(field, value);
  FxVFRestore(caches);
  mark = FxVFMark();
  FXVF_INPUT = null;
  FxVFCandidate(catalog, line, lines, force);
  local candidateOps = FxVFSpent(mark);
  local stable = date == AIDate.GetCurrentDate();
  local inputEqual = input != null && FxVFInputEqual(input, FXVF_INPUT);
  local actual = FxVFFields(line);
  local equal = actual.len() == expected.len();
  foreach (field, value in expected) if (!(field in actual) || value != actual[field]) equal = false;
  if (stable && inputEqual && !equal) throw "C121_VISIBLE_FUSED_ASSERT fields";
  if (!quoted) return;
  FXVF_CASES++;
  AILog.Info("C121_VISIBLE_FUSED_CASE case=" + FXVF_CASES + " stable=" + (stable ? 1 : 0)
      + " input_equal=" + (inputEqual ? 1 : 0) + " equal=" + (equal ? 1 : 0)
      + " original_ops=" + originalOps + " candidate_ops=" + candidateOps
      + " samples=" + (("c121MarginalSamples" in line) ? line.c121MarginalSamples : 0));
  if (FXVF_CASES == 1) AILog.Info("C121_VISIBLE_FUSED_WORLD pass=1");
}
