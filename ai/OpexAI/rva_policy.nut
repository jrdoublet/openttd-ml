/* RVA-16 : one intervention, at the last boundary before spending.
 * Only standalone single-cargo manual-distribution passenger rail. The more
 * uncertain network/mail/extension/learning branches are NOT jointly enabled.
 * Economics: economy.nut:387-400; station capture: station_cmd.cpp:4631.
 * House normalizer is an estimated prior, not a vanilla guarantee.
 */
function OpexRvaStandaloneGain(productionMonth, rawRating, capacityMonth, unitIncome,
                               runningAnnual, amortAnnual)
{
  if (productionMonth < 0 || rawRating < 0 || rawRating > 255 || capacityMonth < 0
      || unitIncome < 0 || runningAnnual < 0 || amortAnnual < 0) return null;
  local offered = rawRating > 0 ? productionMonth * (rawRating + 1.0) / 256.0 : 0.0;
  local carried = (offered < capacityMonth ? offered : capacityMonth).tointeger();
  local revenue = 12 * carried * unitIncome;
  return { carried = carried, revenue = revenue,
      gain = revenue - runningAnnual - amortAnnual };
}

function OpexRvaLocalAdmission(candidate, plan)
{
  if (candidate.kind != "pax" || !AICargo.HasCargoClass(candidate.cargo, AICargo.CC_PASSENGERS)) return null;
  if (("wagons2" in candidate) && candidate.wagons2 > 0) return null;
  if (V207_RAIL_PAX_JOINED_STOPS > 0 || V212_RAIL_PAX_REVENUE_PCT != 100) return null;
  if (!AIGameSettings.IsValid("economy.timekeeping_units")
      || AIGameSettings.GetValue("economy.timekeeping_units") != 0) return null;
  local dist = OpexRvaDistribution(candidate.cargo);
  if (dist == null || !dist.manual) return null;
  if (!AIGameSettings.IsValid("station.modified_catchment")
      || AIGameSettings.GetValue("station.modified_catchment") == 0) return null;
  if (plan.planA == null || plan.planB == null) return null;
  local footprint = AITileList(), destroyed = {};
  local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  if (radius < 0) return null;
  foreach (p in [plan.planA, plan.planB]) {
    if (("stationId" in p) && AIStation.IsValidStation(p.stationId)) return null;
    for (local part = 0; part < p.length; part++) {
      if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return null;
      local tile = p.anchor + p.step * part;
      destroyed.rawset(tile, true);
      OpexRvaAddCoverage(footprint, tile, radius);
    }
  }
  // An overlap is a service externality; without marginal final receipts it
  // MUST keep the reference decision, rather than equating cargo with money.
  foreach (station, sv in AIStationList(AIStation.STATION_ANY)) {
    if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return null;
    local coverage = AITileList_StationCoverage(station);
    foreach (tile, tv in footprint) {
      if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return null;
      if (coverage.HasItem(tile)) return null;
    }
  }
  local towns = {};
  foreach (tile, tv in footprint) {
    if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return null;
    if (tile in destroyed) continue;
    local weight = AITile.GetCargoProduction(tile, candidate.cargo, 1, 1, 0);
    if (weight < 0) return null;
    if (weight == 0) continue;
    // Urban production only: industry-produced passengers require their own inventory.
    if (!AITile.IsHouseTile(tile)) return null;
    local town = AITile.GetTownAuthority(tile);
    if (!AITown.IsValidTown(town)) return null;
    if (!(town in towns)) towns.rawset(town, { weight = 0,
        houses = AITown.GetHouseCount(town), production = AITown.GetLastMonthProduction(town, candidate.cargo) });
    towns[town].weight += weight;
  }
  local monthly = 0.0;
  foreach (town, row in towns) {
    if (row.houses <= 0 || row.production < 0) return null;
    // Never project more than the town's whole observed production.
    local weight = row.weight < row.houses ? row.weight : row.houses;
    monthly += row.production * weight.tofloat() / row.houses;
  }
  local incomeDays = OpexCeilDiv(candidate.oneWayDays, 1);
  local income = AICargo.GetCargoIncome(candidate.cargo, candidate.distance, incomeDays);
  return OpexRvaStandaloneGain(monthly, candidate.stationRating * 255.0 / 100.0,
      candidate.monthlyCapacity, income, candidate.runningAnnual, candidate.amortAnnual);
}

function OpexRvaRejectLocalPurchase(candidate, plan)
{
  local mark = OpexOpsMeasureBegin();
  local estimate = OpexRvaLocalAdmission(candidate, plan);
  local veto = estimate != null && estimate.gain <= 0;
  if (RVA_CYCLE_PROBE) OpexDecide("RVA_POLICY", "v=1 key=" + OpexRvaProjectKey(candidate)
      + " action=" + (veto ? "veto_before_spend" : "reference")
      + " gain_company=" + (estimate != null ? estimate.gain : "na")
      + " carried_month=" + (estimate != null ? estimate.carried : "na")
      + " status=" + (estimate != null ? "estimated_house_prior_no_rivals" : "reference_fallback")
      + " ops_prefix=" + OpexOpsMeasureEnd(mark));
  return veto;
}
