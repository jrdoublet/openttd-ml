/* ROAD1Y truck_fleet : flotte des lignes de fret routier en route seule,
 * geree comme AAAHogEx (route.nut) pour une ligne unidirectionnelle. Appele
 * par OpexRoad1yRefleetSaved seulement si road1y_truck_fleet = 1 ; remplace
 * pour ces lignes le plafond fixe ROAD1Y (4 x min(quais)) et le plafond
 * physique historique de 2 camions.
 *  - plafond : EstimateMaxVehicles (route.nut:2374-2380), abaisse a chaque
 *    retrait (:2613-2616), releve de max(1, estimation/12) quand la source
 *    deborde (:2799-2808, IsOverflow :492-503) ;
 *  - ajout : attente a la source (ligne unidirectionnelle, :2720-2724) > 30
 *    (100 au-dela de 10 camions), moins de 2 camions arretes en charge a la
 *    source (ExistsWaiting :3012-3026), nombre (attente - min(50, capacite))
 *    / capacite, au plus 4 (:2838-2921) ;
 *  - retrait : plus de 3 camions, attente < min(50, capacite), plus de 3
 *    camions arretes : un camion au depot puis vendu, au plus un par mois
 *    (:2553-2619).
 * Renvoie la cible de flotte pour OpexRoadRefleet (jamais sous la flotte
 * courante sauf apres une vente, ou elle vaut la flotte restante). */

function OpexRoad1yTruckFleetEstimate(line, vehicles)
{
  local engine = -1;
  foreach (v in vehicles) {
    if (AIVehicle.IsValidVehicle(v)) {
      engine = AIVehicle.GetEngineType(v);
      break;
    }
  }
  local speed = engine >= 0 ? AIEngine.GetMaxSpeed(engine) : 0;
  if (engine >= 0 && AIGameSettings.IsValid("difficulty.vehicle_breakdowns")
      && AIGameSettings.GetValue("difficulty.vehicle_breakdowns") > 0)
    speed = speed * (100 + AIEngine.GetReliability(engine)) / 200;
  if (speed < 4) speed = 4;
  local distance = AIMap.DistanceManhattan(line.stationA, line.stationB);
  local days = distance * 664 / speed / 24;
  local byTime = days * 2 + 1;
  local byLength = (distance + 4) * 16 / 8;
  return (byTime < byLength ? byTime : byLength) + 2;
}

function OpexRoad1yTruckFleetLog(action, line, have, cap, estimate, waitingA,
    stopped, stoppedAtSource, extra)
{
  if (!DECISION_LOG) return;
  OpexDecide("ROAD1Y_TRUCK_FLEET", "action=" + action + " line=" + line.lineId
      + " cargo=" + AICargo.GetCargoLabel(line.cargo)
      + " have=" + have + " cap=" + cap + " est=" + estimate
      + " dist=" + AIMap.DistanceManhattan(line.stationA, line.stationB)
      + " wait_a=" + waitingA + " stopped=" + stopped
      + " stopped_src=" + stoppedAtSource + extra);
}

function OpexRoad1yTruckFleetTarget(line, have, capacity, waitingA, year)
{
  local stationA = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(stationA)) return have;
  local vehicles = OpexLineVehicleIds(line, stationA);
  local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());

  /* Vente d'un camion envoye au depot par un retrait precedent. */
  if (("road1yTruckSell" in line) && line.road1yTruckSell >= 0) {
    local pending = line.road1yTruckSell;
    if (!AIVehicle.IsValidVehicle(pending)) {
      line.road1yTruckSell = -1;
    } else if (AIVehicle.IsStoppedInDepot(pending)) {
      if (AIVehicle.SellVehicle(pending)) {
        line.road1yTruckSell = -1;
        if (("vehCount" in line) && line.vehCount > 1) line.vehCount--;
        local sold = ("vehCount" in line) ? line.vehCount : have - 1;
        local soldCap = ("road1yTruckCap" in line) ? line.road1yTruckCap : sold;
        OpexRoad1yTruckFleetLog("sell", line, sold, soldCap,
            ("road1yTruckEst" in line) ? line.road1yTruckEst : 0,
            waitingA, 0, 0, " veh=" + pending);
        return sold;
      }
    } else if (!AIOrder.IsGotoDepotOrder(pending, AIOrder.ORDER_CURRENT)) {
      /* Le camion a repris son service (ordre de depot annule) : rien a vendre. */
      line.road1yTruckSell = -1;
    }
    if (line.road1yTruckSell >= 0) return have;
  }

  local estimate = OpexRoad1yTruckFleetEstimate(line, vehicles);
  if (!("road1yTruckCap" in line)) line.road1yTruckCap <- estimate;
  if (!("road1yTruckSell" in line)) line.road1yTruckSell <- -1;
  line.road1yTruckEst <- estimate;
  if (line.road1yTruckCap > estimate) line.road1yTruckCap = estimate;

  local stopped = 0;
  local stoppedAtSource = 0;
  local lastStopped = -1;
  local count = 0;
  local price = 0;
  foreach (v in vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    if (AIVehicle.IsStoppedInDepot(v)) continue;
    if (AIVehicle.GetState(v) == AIVehicle.VS_CRASHED) continue;
    count++;
    if (price <= 0) price = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
    if (AIVehicle.GetCurrentSpeed(v) != 0) continue;
    stopped++;
    lastStopped = v;
    if (AIVehicle.GetState(v) == AIVehicle.VS_AT_STATION
        && AIStation.GetStationID(AIVehicle.GetLocation(v)) == stationA)
      stoppedAtSource++;
  }
  local bottom = capacity < 50 ? capacity : 50;

  if (("road1yTruckYm" in line) && line.road1yTruckYm == ym) return have;
  line.road1yTruckYm <- ym;

  /* Releve progressif du plafond quand la source deborde. */
  local ratingA = AIStation.GetCargoRating(stationA, line.cargo);
  if (line.road1yTruckCap < estimate
      && ((AIStation.HasCargoRating(stationA, line.cargo) && ratingA < 40) || waitingA > 1000)) {
    local step = estimate / 12;
    if (step < 1) step = 1;
    line.road1yTruckCap += step;
    if (line.road1yTruckCap > estimate) line.road1yTruckCap = estimate;
    OpexRoad1yTruckFleetLog("raise", line, have, line.road1yTruckCap, estimate,
        waitingA, stopped, stoppedAtSource, " rating_a=" + ratingA);
  }

  /* Retrait : source peu fournie et plus de trois camions a l'arret. */
  if (count > 3 && waitingA < bottom && stopped > 3 && lastStopped >= 0) {
    if (AIVehicle.SendVehicleToDepot(lastStopped)) {
      line.road1yTruckSell = lastStopped;
      local lowered = (count < line.road1yTruckCap ? count : line.road1yTruckCap) - 1;
      if (lowered < 1) lowered = 1;
      line.road1yTruckCap = lowered;
      OpexRoad1yTruckFleetLog("send", line, have, line.road1yTruckCap, estimate,
          waitingA, stopped, stoppedAtSource, " veh=" + lastStopped);
    }
    return have;
  }

  /* Ajout sur l'attente a la source, avec une reserve de caisse. */
  local needs = count < 10 ? 30 : 100;
  local want = 0;
  if (waitingA > needs && stoppedAtSource < 2 && capacity > 0) {
    want = (waitingA - bottom) / capacity;
    if (want > 4) want = 4;
    if (want > line.road1yTruckCap - have) want = line.road1yTruckCap - have;
    if (want > 0 && price > 0) {
      local affordable = (AICompany.GetBankBalance(AICompany.COMPANY_SELF) - 15000) / price;
      if (want > affordable) want = affordable;
    }
    if (want > 0 && !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, want)) want = 0;
    if (want < 0) want = 0;
  }
  OpexRoad1yTruckFleetLog(want > 0 ? "add" : "state", line, have, line.road1yTruckCap,
      estimate, waitingA, stopped, stoppedAtSource, " want=" + want);
  return have + want;
}
