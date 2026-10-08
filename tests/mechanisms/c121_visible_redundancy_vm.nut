FXVR_REASON <- "none";
FXVR_CASES <- 0;
function FxTLStart(ai) { }
function FxTLWorld(ai) { }
function FxVRReason(line, now, force)
{
  FXVR_REASON = "cold";
  if (force) { FXVR_REASON = "force"; return; }
  if (!(line.lineId in C121_VISIBLE_FLEET_CACHE)) return;
  local s = C121_VISIBLE_FLEET_CACHE[line.lineId];
  FXVR_REASON = "hit";
  if (now < s.date || now-s.date >= 30) FXVR_REASON += "_age";
  if (s.vehicles != line.vehicles.len()) FXVR_REASON += "_vehicles";
  if (s.epoch != C121_CATALOG_ENDPOINT_EPOCH) FXVR_REASON += "_epoch";
}
function FxVRMark() { return { tick = AIController.GetTick(), ops = AIController.GetOpsTillSuspend() }; }
function FxVRSpent(mark)
{
  local left = AIController.GetOpsTillSuspend();
  local ticks = AIController.GetTick()-mark.tick;
  return ticks <= 0 ? mark.ops-left : mark.ops+(ticks-1)*OPS_PER_TICK+(OPS_PER_TICK-left);
}
function FxVREqual(a, b)
{
  if (typeof a != typeof b) return false;
  if (typeof a == "table") {
    if (a.len() != b.len()) return false;
    foreach (key, value in a) if (!(key in b) || !FxVREqual(value, b[key])) return false;
    return true;
  }
  return a == b;
}
function FxVRCompare(catalog, quote, plane, pax, mail, have)
{
  local date = AIDate.GetCurrentDate();
  local mark = FxVRMark();
  local target = OpexC121AirEconomics(catalog, quote, plane, pax, mail, 0);
  local targetOps = FxVRSpent(mark);
  mark = FxVRMark();
  local before = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have);
  local beforeOps = FxVRSpent(mark);
  mark = FxVRMark();
  local after = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have+1);
  local afterOps = FxVRSpent(mark);
  mark = FxVRMark();
  local captured = { have = have, values = {} };
  local fused = FxVRFused(catalog, quote, plane, pax, mail, 0, false, null, null, null, captured);
  local fallback = 0;
  foreach (n in [have, have+1]) if (!(n in captured.values)) {
    captured.values.rawset(n, OpexC121AirEconomics(catalog, quote, plane, pax, mail, n));
    fallback++;
  }
  local fusedOps = FxVRSpent(mark);
  local stable = date == AIDate.GetCurrentDate();
  local equal = FxVREqual(target, fused);
  foreach (field in ["profitAnnual", "revenueAnnual", "realizationFactor"]) {
    equal = equal && before != null && after != null
      && captured.values[have] != null && captured.values[have+1] != null
      && before[field] == captured.values[have][field] && after[field] == captured.values[have+1][field];
  }
  if (stable && !equal) throw "C121_VISIBLE_REDUNDANCY_ASSERT outputs";
  FXVR_CASES++;
  AILog.Info("C121_VISIBLE_REDUNDANCY_CASE case=" + FXVR_CASES + " stable=" + (stable ? 1 : 0)
      + " equal=" + (equal ? 1 : 0) + " reason=" + FXVR_REASON + " have=" + have
      + " cap=" + (target != null ? target.fleetScanCap : -1) + " fallback=" + fallback
      + " target_ops=" + targetOps + " before_ops=" + beforeOps + " after_ops=" + afterOps
      + " fused_ops=" + fusedOps);
  if (FXVR_CASES == 1) AILog.Info("C121_VISIBLE_REDUNDANCY_WORLD pass=1");
  return { target = target, before = before, after = after };
}
