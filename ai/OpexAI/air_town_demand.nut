/* Module AIR extrait de builder_air.nut (R11) : cargo passagers du catchment de site.
 * Repli : premiere classe CC_PASSENGERS, sans identifiant fixe. */
function OpexAirDemandPaxCargo()
{
  if (AIR_DEMAND_PAX_CARGO >= 0) return AIR_DEMAND_PAX_CARGO;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    if (AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) {
      AIR_DEMAND_PAX_CARGO = c;
      return c;
    }
  }
  return -1;
}
