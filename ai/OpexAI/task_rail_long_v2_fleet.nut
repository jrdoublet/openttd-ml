/* RAIL-LONG v2 : croissance d'une rame existante sur quai deja long.
 * Le moteur de transaction V284 conserve l'ancien convoi jusqu'a l'adoption.
 * Aucun second train n'est autorise sans preuve topologique PBS. */

function OpexRailLongV2FleetPending(owner)
{
  return owner != null && owner._v284State != null
      && ("pending" in owner._v284State) && owner._v284State.pending != null
      && ("railLongV2" in owner._v284State.pending)
      && owner._v284State.pending.railLongV2;
}

/* Un revenu marginal estime sur du fret reellement produit et en attente.
 * La vitesse peut baisser legerement apres un wagon, mais il faut une marge
 * positive apres traction, fonctionnement et amortissement du train neuf. */
function OpexRailLongV2FleetMargin(owner, line, vehicle, wagon, oldWagons, equipment)
{
  if (line == null || equipment == null || !("engine" in equipment)
      || owner == null || wagon == null || oldWagons < 1
      || !("srcIndustry" in line) || !AIIndustry.IsValidIndustry(line.srcIndustry)) return null;
  local production = AIIndustry.GetLastMonthProduction(line.srcIndustry, line.cargo);
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)) return null;
  local rating = AIStation.GetCargoRating(station, line.cargo); // NoAI : 0..100
  local waiting = AIStation.GetCargoWaiting(station, line.cargo);
  if (production <= 0 || rating <= 0 || rating > 100 || waiting < 2 * wagon.capacity)
    return null;
  local newLoco = OpexV257Engine(equipment.engine, line.cargo, false);
  local oldLoco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
  if (newLoco == null || oldLoco == null || newLoco.ageYears <= 0) return null;
  local dist = (("routeDistance" in line) && line.routeDistance > 0)
      ? line.routeDistance : line.distance;
  if (dist <= 0) return null;
  local oldSpeed = OpexRailEffectiveSpeed(oldLoco, wagon, oldWagons, dist);
  local newSpeed = OpexRailEffectiveSpeed(newLoco, wagon, oldWagons + 1, dist);
  if (oldSpeed <= 0 || newSpeed < oldSpeed * 0.85) return null;
  local dwell = OpexRailStationDwellDays(wagon);
  local oldCycle = 2.0 * dist / (0.036 * oldSpeed) + dwell;
  local newCycle = 2.0 * dist / (0.036 * newSpeed) + dwell;
  if (oldCycle <= 0 || newCycle <= 0) return null;
  local oldCapacity = AIVehicle.GetCapacity(vehicle, line.cargo) * 30.0 / oldCycle;
  local newCapacity = (oldWagons + 1) * wagon.capacity * 30.0 / newCycle;
  local otherCapacity = 0.0;
  foreach (other in owner._lines) {
    if (other == line || !("mode" in other) || other.mode != "rail"
        || !("kind" in other) || other.kind != "freight"
        || !("srcIndustry" in other) || other.srcIndustry != line.srcIndustry
        || other.cargo != line.cargo) continue;
    otherCapacity += OpexInvestStallLineCapacity(other);
  }
  local capturable = production.tofloat() * rating / 100.0 - oldCapacity - otherCapacity;
  if (capturable < 0) capturable = 0;
  /* Le stock de gare n'est pas un debit permanent : amortir sur 12 mois. */
  capturable += waiting.tofloat() / 12.0;
  local extra = newCapacity - oldCapacity;
  if (extra > capturable) extra = capturable;
  if (extra <= 0) return null;
  local income = AICargo.GetCargoIncome(line.cargo, line.distance,
      OpexCeilDiv(dist / (0.036 * newSpeed) + 1, 1));
  if (income <= 0) return null;
  local price = newLoco.price + (oldWagons + 1) * wagon.price;
  local runningExtra = newLoco.runningCost + (oldWagons + 1) * wagon.runningCost
      - AIVehicle.GetRunningCost(vehicle);
  local profit = 12.0 * extra * income - runningExtra - price / newLoco.ageYears;
  if (profit <= 0 || price <= 0 || OpexAvailableCapital() < price + 100000) return null;
  return { score = profit / price, profit = profit, cost = price,
           extra = extra, waiting = waiting, production = production, rating = rating };
}

function OpexRailLongV2FleetSelect(owner, year)
{
  if (!RAIL_LONG_V2 || !MODE_RAIL || owner == null || !SAVE_FULL_STATE
      || owner._catalog == null || owner._lines == null
      || owner._railLongV2Pending != null || owner._railExpansion != null
      || owner._railSearch != null || owner._v257Pending != null
      || owner._v271Pending != null || OpexV284Busy(owner)) return false;
  if (V233_LONG_GOOD > 0 && V233L_STATE != null && V233L_STATE.pending != null)
    return false;
  if (owner._v284State == null)
    owner._v284State = { nextDate = 0, dates = {}, loops = {}, pending = null };
  local state = owner._v284State;
  local now = AIDate.GetCurrentDate();
  if (("railLongV2NextDate" in state) && now < state.railLongV2NextDate) return false;
  state.rawset("railLongV2NextDate", now + 30);
  if (!("railLongV2Dates" in state) || state.railLongV2Dates == null)
    state.rawset("railLongV2Dates", {});
  local best = null;
  foreach (line in owner._lines) {
    if (!("mode" in line) || line.mode != "rail" || !("kind" in line)
        || line.kind != "freight" || !("platformLength" in line)
        || line.platformLength < 6 || !("vehicles" in line)
        || line.vehicles == null || line.vehicles.len() != 1 || line.trains != 1
        || OpexV163Wagons2(line) > 0
        || (("doubleTrack" in line) && line.doubleTrack != 0)
        || (("scrapping" in line) && line.scrapping)
        || !("lastProfit" in line) || line.lastProfit <= 0
        || !("depot" in line) || line.depot == null
        || !AIRail.IsRailDepotTile(line.depot)) continue;
    if ((line.lineId in state.railLongV2Dates)
        && now < state.railLongV2Dates[line.lineId]) continue;
    local vehicle = line.vehicles[0];
    if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL
        || (owner._vehiclesToRetire != null && (vehicle in owner._vehiclesToRetire))) continue;
    local count = AIVehicle.GetNumWagons(vehicle) - 1;
    local limit = OpexV284Limit(line);
    if (count < 1 || count >= OpexRailNominalMaxWagons(limit)
        || AIVehicle.GetLength(vehicle) + 8 > limit * 16) continue;
    local wagonId = AIVehicle.GetWagonEngineType(vehicle, 1);
    if (!AIEngine.IsWagon(wagonId) || !AIEngine.IsBuildable(wagonId)
        || AIEngine.GetCargoType(wagonId) != line.cargo) continue;
    local homogeneous = true;
    for (local i = 1; i <= count; i++)
      if (AIVehicle.GetWagonEngineType(vehicle, i) != wagonId) homogeneous = false;
    if (!homogeneous) continue;
    local wagon = OpexV257Engine(wagonId, line.cargo, true);
    if (wagon == null || wagon.capacity <= 0) continue;
    local station = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(station)) continue;
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    local equipment = OpexV284Equipment(line, vehicle, wagon, count + 1, false, waiting);
    local margin = OpexRailLongV2FleetMargin(owner, line, vehicle, wagon, count, equipment);
    if (margin == null) continue;
    if (best == null || margin.score > best.margin.score)
      best = { line = line, vehicle = vehicle, wagon = wagon,
               equipment = equipment, margin = margin, count = count };
  }
  if (best == null) return false;
  local line = best.line;
  if (FLEET_ARB && !OpexFleetRequest(line, "rail", "add_wagons",
      AIEngine.GetPrice(best.equipment.engine) + (best.count + 1) * best.wagon.price,
      best.margin.profit, "RAIL_LONG_V2_FLEET")) { state.railLongV2NextDate = now + 1; return false; }
  state.railLongV2Dates.rawset(line.lineId, now + 180);
  local waitDays = (2 * line.distance / (0.036 * best.equipment.speed)).tointeger() + 60;
  if (waitDays < 120) waitDays = 120;
  if (waitDays > 730) waitDays = 730;
  state.pending = {
    lineId = line.lineId, vehicle = best.vehicle, newVehicle = -1,
    engine = best.equipment.engine, wagon = best.wagon.id, wagons = best.count + 1,
    oldWagons = best.count, add = false, loopPlan = null,
    speedMilli = (best.equipment.speed * 1000).tointeger(),
    oldSpeedMilli = (best.equipment.oldSpeed * 1000).tointeger(),
    phase = "approach", deadline = now + waitDays, before = null,
    depot = line.depot, waiting = best.margin.waiting, cashBefore = 0,
    railLongV2 = true
  };
  if (DECISION_LOG) OpexDecide("RAIL_LONG_V2", "event=fleet_pick line=" + line.lineId
      + " wagons_old=" + best.count + " wagons_new=" + (best.count + 1)
      + " profit=" + best.margin.profit + " cash_cost=" + best.margin.cost
      + " waiting=" + best.margin.waiting + " production=" + best.margin.production);
  return true;
}
