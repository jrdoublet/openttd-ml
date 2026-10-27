/* V252 : modernisation de la flotte aerienne quand on est riche. Aucun montant fixe.
 * Riche = aucun emprunt, aucune passe projets arretee faute de caisse depuis le mois
 * precedent (V252_CASH_STOP), et apres l'achat la caisse couvre encore
 * le projet le plus cher du portefeuille. Au plus un remplacement par passage.
 * Aucun nombre a 4 chiffres ou plus dans ce fichier. */

/* ESTIM-1 : cout et marge de la substitution d'UN avion a flotte constante.
 * Les deux appareils passent par le meme modele physique de route ; la
 * difference entre flottes homogenes est repartie sur les n appareils. */
function OpexEstimV252Project(line, vehicle, newEngine, catalog, hangar, kDec = -1)
{
  local monthly = ("airMonthlyPax" in line && line.airMonthlyPax > 0) ? line.airMonthlyPax
      : (("monthlyPax" in line) ? line.monthlyPax : 0);
  if (monthly <= 0 || line.vehicles == null || line.vehicles.len() == 0) return null;
  local distance = ("distance" in line && line.distance > 0)
      ? line.distance : AIMap.DistanceManhattan(line.stationA, line.stationB);
  if (distance <= 0) return null;
  local cargo = ("cargo" in line) ? line.cargo : catalog.paxCargo;
  local oldEngine = AIVehicle.GetEngineType(vehicle);
  local oldCapacity = AIVehicle.GetCapacity(vehicle, cargo);
  local newCapacity = AIVehicle.GetBuildWithRefitCapacity(hangar, newEngine, cargo);
  if (oldCapacity <= 0 || newCapacity <= 0) return null;
  local airport = { type = AIAirport.GetAirportType(line.stationA), price = 0, maintenance = 0 };
  local oldPlane = { id = oldEngine, speed = AIEngine.GetMaxSpeed(oldEngine),
      capacity = oldCapacity, price = AIEngine.GetPrice(oldEngine),
      runningCost = AIEngine.GetRunningCost(oldEngine) };
  local newPlane = { id = newEngine, speed = AIEngine.GetMaxSpeed(newEngine),
      capacity = newCapacity, price = AIEngine.GetPrice(newEngine),
      runningCost = AIEngine.GetRunningCost(newEngine) };
  local count = line.vehicles.len();
  local before = OpexAirEconomics(catalog, airport, oldPlane, distance, monthly,
      false, 0, 0, 0, count);
  local after = OpexAirEconomics(catalog, airport, newPlane, distance, monthly,
      false, 0, 0, 0, count);
  if (before == null || after == null) return null;
  local price = AIEngine.GetPrice(newEngine);
  local sale = AIVehicle.GetCurrentValue(vehicle);
  if (sale < 0) sale = 0;
  local netCapital = price - sale;
  if (netCapital < 0) netCapital = 0;
  local years = AIEngine.GetMaxAge(newEngine).tofloat() / 365.0;
  if (years <= 0) return null;
  local deltaR = (after.revenueAnnual - before.revenueAnnual).tofloat() / count;
  local deltaE = newPlane.runningCost - oldPlane.runningCost;
  return OpexEstimVProject("air", deltaR, deltaE, netCapital / years, netCapital, kDec);
}

function OpexAI::_dispatchV252AirEngineRefresh(task, year)
{
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
  local curEngine = -1;
  local nAirLines = 0;
  local nOutdated = 0;
  local candidates = [];
  local rank = 0;
  local bestProject = null;
  local kDec = (ESTIM_UNIFIE & 4) != 0 ? OpexC69ComputeKDec().K_dec : -1;

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

    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (this._vehiclesToRetire != null && (v in this._vehiclesToRetire)) continue;
      candidates.append({
        veh = v,
        line = line,
        age = AIVehicle.GetAge(v),
        profit = AIVehicle.GetProfitLastYear(v),
        engine = AIVehicle.GetEngineType(v),
        rank = rank++
      });
    }
  }

  /* Ordre de preference : age decroissant, profit croissant, rang croissant */
  candidates.sort(function(a, b) {
    if (a.age != b.age) return a.age > b.age ? -1 : 1;
    if (a.profit != b.profit) return a.profit < b.profit ? -1 : 1;
    if (a.rank != b.rank) return a.rank < b.rank ? -1 : 1;
    return 0;
  });

  local lineTargetCache = {};
  foreach (cand in candidates) {
    local lineKey = ("lineId" in cand.line) ? cand.line.lineId : cand.line;
    if (!(lineKey in lineTargetCache)) {
      lineTargetCache[lineKey] <- OpexAirBestEngineForLine(cand.line, this._catalog);
    }

    local targetEngine = lineTargetCache[lineKey];
    if (targetEngine == null) continue;
    if (cand.engine == targetEngine) continue;

    local project = null;
    if ((ESTIM_UNIFIE & 4) != 0) {
      local airportTile = ("originA" in cand.line) && AIAirport.IsAirportTile(cand.line.originA)
          ? cand.line.originA : cand.line.stationA;
      local hangar = AIAirport.GetHangarOfAirport(airportTile);
      if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) continue;
      project = OpexEstimV252Project(cand.line, cand.veh, targetEngine, this._catalog, hangar, kDec);
      if (project == null || project.deltaP <= 0 || project.score <= 0) continue;
      if (bestProject != null && project.score <= bestProject.score) continue;
      bestProject = project;
    }
    nOutdated = 1;
    bestLine = cand.line;
    bestVeh = cand.veh;
    bestAge = cand.age;
    bestProfit = cand.profit;
    bestNewEngine = targetEngine;
    curEngine = cand.engine;
    if ((ESTIM_UNIFIE & 4) == 0) break;
  }

  if (bestVeh < 0 || bestLine == null) {
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=no_candidate air_lines=" + nAirLines + " outdated=" + nOutdated);
    return true;
  }

  local price = AIEngine.GetPrice(bestNewEngine);
  if ((ESTIM_UNIFIE & 4) != 0) OpexEstimVLog("V252", bestLine.lineId, bestProject);
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexV249MaxListedCapital(this._projects);
  if ((ESTIM_UNIFIE & 2) != 0)
    threshold = 0;
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
  /* AIR-FLOTTE-1 : pas de ROI marginal du remplacement dans V252. Le profit
   * de l'ancien appareil est historique, jamais une prediction de delta. */
  local airF1Event = AIR_FLOTTE1_SHADOW
      ? OpexAirF1Before(this, "renewal", bestLine.lineId, price,
                        null, -1, curEngine, bestNewEngine, null, threshold, bestProfit) : null;
  if (airF1Event != null) OpexAirF1Ready(airF1Event);
  local newPlane = AIVehicle.BuildVehicleWithRefit(hangar, bestNewEngine, cargo);
  if (!AIVehicle.IsValidVehicle(newPlane)) {
    if (airF1Event != null) OpexAirF1After(airF1Event, "build_failed");
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=build_failed line=" + bestLine.lineId + " engine=" + bestNewEngine);
    return true;
  }

  if (!AIOrder.ShareOrders(newPlane, bestVeh) && !AIOrder.CopyOrders(newPlane, bestVeh)) {
    if (AIVehicle.IsStoppedInDepot(newPlane)) AIVehicle.SellVehicle(newPlane);
    if (airF1Event != null) OpexAirF1After(airF1Event, "order_failed");
    if (DECISION_LOG) OpexDecide("V252_SKIP", "reason=order_failed line=" + bestLine.lineId);
    return true;
  }

  if (!AIVehicle.StartStopVehicle(newPlane)) {
    if (AIVehicle.IsStoppedInDepot(newPlane)) AIVehicle.SellVehicle(newPlane);
    if (airF1Event != null) OpexAirF1After(airF1Event, "start_failed");
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
  if (airF1Event != null) OpexAirF1After(airF1Event, "built", 0, 1);

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

  if (DECISION_LOG) OpexDecide("V252_REPLACE", "line=" + bestLine.lineId + " old_engine=" + curEngine
             + " new_engine=" + bestNewEngine + " old_veh=" + bestVeh + " new_veh=" + newPlane
             + " price=" + price + " age=" + bestAge + " profit=" + bestProfit);
  return true;
}
