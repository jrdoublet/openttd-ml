/* V252 : modernisation de la flotte aerienne quand on est riche. Aucun montant fixe.
 * Riche = aucun emprunt, aucune passe projets arretee faute de caisse depuis le mois
 * precedent (V252_CASH_STOP), et apres l'achat la caisse couvre encore la reserve
 * et le projet le plus cher du portefeuille. Au plus un remplacement par passage.
 * Aucun nombre a 4 chiffres ou plus dans ce fichier. */

function OpexAI::_dispatchV252AirEngineRefresh(task, year)
{
  if (V252_AIR_ENGINE_REFRESH < 2) return false;
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v252RefreshMonth == ym) return false;
  this._v252RefreshMonth = ym;

  local cashStop = V252_CASH_STOP;
  ::V252_CASH_STOP = false;
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=loan loan=" + loan);
    return true;
  }
  if (cashStop) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=cash_stop");
    return true;
  }

  if (this._lines == null || this._lines.len() == 0 || this._catalog == null) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=no_lines");
    return true;
  }

  local bestLine = null;
  local bestVeh = -1;
  local bestAge = -1;
  local bestProfit = 0;
  local bestNewEngine = -1;
  local bestDemandOld = 0;
  local bestDemandNow = 0;
  local curEngine = -1;
  local nAirLines = 0;
  local nOutdated = 0;

  foreach (line in this._lines) {
    if (line == null) continue;
    if (("mode" in line) && line.mode != "air") continue;
    if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    nAirLines++;

    local lineProfit = 0;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v)) lineProfit += AIVehicle.GetProfitLastYear(v);
    }
    /* Ligne rentable requise */
    if (lineProfit <= 0) continue;

    local targetEngine = OpexAirBestEngineForLine(line, this._catalog, this._lines);
    if (targetEngine == null) continue;

    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (this._vehiclesToRetire != null && (v in this._vehiclesToRetire)) continue;
      local e = AIVehicle.GetEngineType(v);
      if (e == targetEngine) continue;
      nOutdated++;

      local age = AIVehicle.GetAge(v);
      local prof = AIVehicle.GetProfitLastYear(v);

      /* Cibler l'avion le plus vieux, ou de plus faible rendement a age egal */
      if (bestVeh < 0 || age > bestAge || (age == bestAge && prof < bestProfit)) {
        bestLine = line;
        bestVeh = v;
        bestAge = age;
        bestProfit = prof;
        bestNewEngine = targetEngine;
        bestDemandOld = V252_LAST_DEMAND_OLD;
        bestDemandNow = V252_LAST_DEMAND_NOW;
        curEngine = e;
      }
    }
  }

  if (bestVeh < 0 || bestLine == null) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=no_candidate air_lines=" + nAirLines + " outdated=" + nOutdated);
    return true;
  }

  local price = AIEngine.GetPrice(bestNewEngine);
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects);
  if (price <= 0 || cash - price < threshold) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=cost cash=" + cash + " cost=" + price + " threshold=" + threshold + " line=" + bestLine.lineId);
    return true;
  }

  local airportTile = ("originA" in bestLine) && AIAirport.IsAirportTile(bestLine.originA)
      ? bestLine.originA : bestLine.stationA;
  local hangar = AIAirport.GetHangarOfAirport(airportTile);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=no_hangar line=" + bestLine.lineId);
    return true;
  }

  local cargo = ("cargo" in bestLine) ? bestLine.cargo : this._catalog.paxCargo;
  local newPlane = AIVehicle.BuildVehicleWithRefit(hangar, bestNewEngine, cargo);
  if (!AIVehicle.IsValidVehicle(newPlane)) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=build_failed line=" + bestLine.lineId + " engine=" + bestNewEngine);
    return true;
  }

  if (!AIOrder.ShareOrders(newPlane, bestVeh) && !AIOrder.CopyOrders(newPlane, bestVeh)) {
    if (AIVehicle.IsStoppedInDepot(newPlane)) AIVehicle.SellVehicle(newPlane);
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=order_failed line=" + bestLine.lineId);
    return true;
  }

  if (!AIVehicle.StartStopVehicle(newPlane)) {
    if (AIVehicle.IsStoppedInDepot(newPlane)) AIVehicle.SellVehicle(newPlane);
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=start_failed line=" + bestLine.lineId);
    return true;
  }

  bestLine.vehicles.append(newPlane);
  for (local i = 0; i < bestLine.vehicles.len(); i++) {
    if (bestLine.vehicles[i] == bestVeh) {
      bestLine.vehicles.remove(i);
      break;
    }
  }
  if (("vehicle" in bestLine) && bestLine.vehicle == bestVeh) {
    bestLine.vehicle = newPlane;
  }
  bestLine.refleetEngine = bestNewEngine;

  /* Retraite et mise a la casse de l'ancien appareil via le mecanisme existant */
  if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
  this._vehiclesToRetire.rawset(bestVeh, {
    lineId = bestLine.lineId, startedDate = date, lastSendDate = date, attempts = 1
  });
  AIVehicle.SendVehicleToDepot(bestVeh);
  if (AIVehicle.IsStoppedInDepot(bestVeh)) {
    if (AIVehicle.SellVehicle(bestVeh)) {
      delete this._vehiclesToRetire[bestVeh];
    }
  }

  local dOld = bestDemandOld;
  local dNow = bestDemandNow;
  if (DECISION_LOG) OpexDecide("V252_REPLACE", "line=" + bestLine.lineId + " old_engine=" + curEngine
             + " new_engine=" + bestNewEngine + " old_veh=" + bestVeh + " new_veh=" + newPlane
             + " price=" + price + " age=" + bestAge + " profit=" + bestProfit
             + " demand_old=" + dOld + " demand_now=" + dNow);
  return true;
}
