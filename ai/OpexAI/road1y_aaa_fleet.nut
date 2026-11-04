/* ROAD1Y aaa_fleet : gestion de flotte des lignes bus PAX en route seule,
 * portee d'un bloc depuis AAAHogEx (route.nut). Appele par
 * OpexRoad1yRefleetSaved seulement si road1y_aaa_fleet = 1 ; remplace pour
 * ces lignes le plafond fixe 4 x min(arrets) et la regle somme >= capacite.
 *  - plafond : EstimateMaxVehicles (route.nut:2374-2380), abaisse a chaque
 *    retrait (:2613-2616), releve de max(1, estimation/12) quand la source
 *    deborde (:2799-2808, IsOverflow :492-503) ;
 *  - ajout : min(attente A, B) > 30 (100 au-dela de 10 bus), moins de 2 bus
 *    arretes en charge a la source (ExistsWaiting :3012-3026), nombre
 *    (attente - min(50, capacite)) / capacite, au plus 4 (:2838-2921) ;
 *  - retrait : plus de 3 bus, min(attente) < min(50, capacite), plus de 3 bus
 *    arretes : un bus au depot puis vendu, au plus un par mois (:2553-2619).
 * Renvoie la cible de flotte pour OpexRoadRefleet (jamais sous la flotte
 * courante sauf apres une vente, ou elle vaut la flotte restante). */

function OpexRoad1yAaaFleetEstimate(line, vehicles)
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

function OpexRoad1yAaaFleetLog(action, line, have, cap, estimate, waitingA, waitingB,
    stopped, stoppedAtSource, extra)
{
  if (!DECISION_LOG) return;
  OpexDecide("ROAD1Y_AAA_FLEET", "action=" + action + " line=" + line.lineId
      + " have=" + have + " cap=" + cap + " est=" + estimate
      + " dist=" + AIMap.DistanceManhattan(line.stationA, line.stationB)
      + " wait_a=" + waitingA + " wait_b=" + waitingB
      + " stopped=" + stopped + " stopped_src=" + stoppedAtSource + extra);
}

function OpexRoad1yAaaFleetTarget(ai, line, have, capacity, waitingA, waitingB, year)
{
  local stationA = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(stationA)) return have;
  local vehicles = OpexLineVehicleIds(line, stationA);
  local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());

  /* Vente d'un bus envoye au depot par un retrait precedent. */
  if (("road1yAaaSell" in line) && line.road1yAaaSell >= 0) {
    local pending = line.road1yAaaSell;
    if (!AIVehicle.IsValidVehicle(pending)) {
      line.road1yAaaSell = -1;
    } else if (AIVehicle.IsStoppedInDepot(pending)) {
      if (AIVehicle.SellVehicle(pending)) {
        line.road1yAaaSell = -1;
        if (("vehCount" in line) && line.vehCount > 1) line.vehCount--;
        local sold = ("vehCount" in line) ? line.vehCount : have - 1;
        local soldCap = ("road1yAaaCap" in line) ? line.road1yAaaCap : sold;
        OpexRoad1yAaaFleetLog("sell", line, sold, soldCap,
            ("road1yAaaEst" in line) ? line.road1yAaaEst : 0,
            waitingA, waitingB, 0, 0, " veh=" + pending);
        return sold;
      }
    } else if (!AIOrder.IsGotoDepotOrder(pending, AIOrder.ORDER_CURRENT)) {
      /* Le bus a repris son service (ordre de depot annule) : rien a vendre. */
      line.road1yAaaSell = -1;
    }
    if (line.road1yAaaSell >= 0) return have;
  }

  local estimate = OpexRoad1yAaaFleetEstimate(line, vehicles);
  if (!("road1yAaaCap" in line)) line.road1yAaaCap <- estimate;
  if (!("road1yAaaSell" in line)) line.road1yAaaSell <- -1;
  line.road1yAaaEst <- estimate;
  if (line.road1yAaaCap > estimate) line.road1yAaaCap = estimate;

  local stopped = 0;
  local stoppedAtSource = 0;
  local lastStopped = -1;
  local count = 0;
  foreach (v in vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    if (AIVehicle.IsStoppedInDepot(v)) continue;
    if (AIVehicle.GetState(v) == AIVehicle.VS_CRASHED) continue;
    count++;
    if (AIVehicle.GetCurrentSpeed(v) != 0) continue;
    stopped++;
    lastStopped = v;
    if (AIVehicle.GetState(v) == AIVehicle.VS_AT_STATION
        && AIStation.GetStationID(AIVehicle.GetLocation(v)) == stationA)
      stoppedAtSource++;
  }
  local minWait = waitingA < waitingB ? waitingA : waitingB;
  local bottom = capacity < 50 ? capacity : 50;

  if (("road1yAaaYm" in line) && line.road1yAaaYm == ym) return have;
  line.road1yAaaYm <- ym;

  /* Releve progressif du plafond quand la source deborde. */
  local ratingA = AIStation.GetCargoRating(stationA, line.cargo);
  if (line.road1yAaaCap < estimate
      && ((AIStation.HasCargoRating(stationA, line.cargo) && ratingA < 40) || waitingA > 1000)) {
    local step = estimate / 12;
    if (step < 1) step = 1;
    line.road1yAaaCap += step;
    if (line.road1yAaaCap > estimate) line.road1yAaaCap = estimate;
    OpexRoad1yAaaFleetLog("raise", line, have, line.road1yAaaCap, estimate,
        waitingA, waitingB, stopped, stoppedAtSource, " rating_a=" + ratingA);
  }

  /* Retrait : gare peu fournie et plus de trois bus a l'arret. */
  if (count > 3 && minWait < bottom && stopped > 3 && lastStopped >= 0) {
    if (AIVehicle.SendVehicleToDepot(lastStopped)) {
      line.road1yAaaSell = lastStopped;
      local lowered = (count < line.road1yAaaCap ? count : line.road1yAaaCap) - 1;
      if (lowered < 1) lowered = 1;
      line.road1yAaaCap = lowered;
      OpexRoad1yAaaFleetLog("send", line, have, line.road1yAaaCap, estimate,
          waitingA, waitingB, stopped, stoppedAtSource, " veh=" + lastStopped);
    }
    return have;
  }

  /* Ajout sur l'attente du bout le plus faible. */
  local needs = count < 10 ? 30 : 100;
  local want = 0;
  if (minWait > needs && stoppedAtSource < 2 && capacity > 0) {
    want = (minWait - bottom) / capacity;
    if (want > 4) want = 4;
    if (want > line.road1yAaaCap - have) want = line.road1yAaaCap - have;
    if (want > 0 && !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, want)) want = 0;
    if (want < 0) want = 0;
  }
  OpexRoad1yAaaFleetLog(want > 0 ? "add" : "state", line, have, line.road1yAaaCap, estimate,
      waitingA, waitingB, stopped, stoppedAtSource, " want=" + want);
  return have + want;
}
