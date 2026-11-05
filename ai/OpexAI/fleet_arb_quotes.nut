/* Quote adapters only. No vehicle construction, sale or refit commands here. */
function OpexFleetRailProfit(line, price)
{
  if (line == null || !("vehicles" in line) || line.vehicles == null
      || line.vehicles.len() == 0 || line.vehicles.len() > 64
      || !("monthly" in line) || line.monthly <= 0 || !("distance" in line)) return null;
  local model = line.vehicles[0];
  if (!AIVehicle.IsValidVehicle(model)) return null;
  local engine = AIVehicle.GetEngineType(model);
  local number = AIVehicle.GetNumWagons(model) - 1;
  if (number < 1 || number > 64 || AIEngine.GetCapacity(engine) > 0) return null;
  local wagonId = AIVehicle.GetWagonEngineType(model, 1);
  foreach (vehicle in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetEngineType(vehicle) != engine
        || AIVehicle.GetNumWagons(vehicle) != number + 1) return null;
    for (local w = 1; w <= number; w++)
      if (AIVehicle.GetWagonEngineType(vehicle, w) != wagonId) return null;
  }
  local loco = OpexV257Engine(engine, line.cargo, false);
  local wagon = OpexV257Engine(wagonId, line.cargo, true);
  if (loco == null || wagon == null) return null;
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)) return null;
  local rating = AIStation.GetCargoRating(station, line.cargo);
  if (rating < 0) return null;
  local count = line.vehicles.len();
  local monthly = OpexV257UncensoredMonthly(line, line.vehicles, rating, line.monthly.tofloat() / count);
  local limits = OpexV257WagonSpeedLimits();
  local speed = OpexV257ConsistLastSpeed(loco, wagon, limits);
  local before = OpexV257Plan(line, loco, wagon, number, monthly, rating, speed, limits);
  local after = OpexV257Plan(line, loco, wagon, number,
      monthly * count / (count + 1), rating, speed, limits);
  local life = AIEngine.GetMaxAge(engine).tofloat() / 365.0;
  if (before == null || after == null || life <= 0) return null;
  return after.revenue * (count + 1) - before.revenue * count
      - after.running - price / life;
}

function OpexFleetRoadProfit(catalog, line, have, missing, engine)
{
  if (engine == null || !("monthly" in line) || line.monthly <= 0
      || !("distance" in line) || !("kind" in line) || missing <= 0) return null;
  local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
  local economics = OpexRoadLineEconomics(catalog, line.cargo, line.distance,
      line.monthly, engine, line.kind, distance);
  if (economics == null || economics.oneWayDays <= 0 || engine.ageYears <= 0) return null;
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)) return null;
  local rating = AIStation.GetCargoRating(station, line.cargo);
  if (rating < 0) return null;
  local offered = line.monthly.tofloat() * rating / 100.0;
  local unit = engine.capacity * OpexLoadedTripsPerMonth(economics.oneWayDays,
      2 * economics.oneWayDays, line.kind == "pax");
  local before = have * unit;
  local after = (have + missing) * unit;
  if (before > offered) before = offered;
  if (after > offered) after = offered;
  return 12 * (after - before) * AICargo.GetCargoIncome(line.cargo,
      line.distance, OpexCeilDiv(economics.transitDays, 1))
      - missing * (engine.runningCost + engine.price.tofloat() / engine.ageYears);
}

function OpexFleetAirProfit(line, catalog, lines, targetEngine)
{
  if (catalog == null || lines == null || !("vehicles" in line)) return null;
  local index = OpexAirBuildRoutesIndex(lines);
  local marginal = OpexV161NextMarginal(line, catalog, line.vehicles.len(),
      OpexV161NeighbourCount(line, index));
  if (marginal == null || marginal.engine != targetEngine) return null;
  return marginal.profit;
}

function OpexFleetPlanProfit(plan)
{
  if (("economics" in plan) && plan.economics != null && ("profitAnnual" in plan.economics))
    return plan.economics.profitAnnual;
  return ("profitAnnual" in plan) ? plan.profitAnnual : null;
}

function OpexFleetSaleProfit(line)
{
  if (!("lastProfit" in line)) return null;
  return -line.lastProfit;
}
