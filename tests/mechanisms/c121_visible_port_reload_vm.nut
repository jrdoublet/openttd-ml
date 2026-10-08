require("c121_visible_flux_vm.nut");
FXVP_START <- FxTLStart;
FXVP_DEPTH_DONE <- {};
function FxTLStart(ai)
{
  FXVP_START(ai);
  FxVLAssert(C121_AIR_VISIBLE_FUSED, "ported_setting_loaded");
  local bad = OpexC121VisibleFleetEconomics(null, null, null, 0, 0, 1);
  FxVLAssert(bad.target == null && bad.before == null && bad.after == null, "ported_null_contract");
}
function FxVPEqual(a, b)
{
  if (typeof a != typeof b) return false;
  if (typeof a == "table") {
    if (a.len() != b.len()) return false;
    foreach (key, value in a) if (!(key in b) || !FxVPEqual(value, b[key])) return false;
    return true;
  }
  return a == b;
}
function FxVPMatrix(catalog, quote, plane, pax, mail, have)
{
  foreach (extra in [0, 1]) {
    if (extra in FXVP_DEPTH_DONE) continue;
    local date = AIDate.GetCurrentDate();
    local target = OpexC121AirEconomics(catalog, quote, plane, pax, mail, 0);
    local n = target.fleetScanCap+extra;
    local before = OpexC121AirEconomics(catalog, quote, plane, pax, mail, n);
    local after = OpexC121AirEconomics(catalog, quote, plane, pax, mail, n+1);
    local fused = OpexC121VisibleFleetEconomics(catalog, quote, plane, pax, mail, n);
    if (date != AIDate.GetCurrentDate()) continue;
    FxVLAssert(FxVPEqual(target, fused.target), "ported_depth_target");
    foreach (field in ["profitAnnual", "revenueAnnual", "realizationFactor"])
      FxVLAssert(before[field] == fused.before[field] && after[field] == fused.after[field], "ported_depth_margin");
    FXVP_DEPTH_DONE.rawset(extra, true);
    AILog.Info("C121_VISIBLE_PORT_DEPTH extra=" + extra + " equal=1");
  }
}
