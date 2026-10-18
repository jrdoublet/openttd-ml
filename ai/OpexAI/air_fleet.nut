/* Module AIR extrait de builder_air.nut (R11) : flottes et ajout d'avions. */
/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees. */
/* V253 mode 3 : economie C121 d'une flotte homogene de taille reelle.
 * Retirer la ligne du service existant : le candidat represente deja sa flotte.
 * Ce proxy compare les moteurs a nombre de creneaux constant ; il ne predit pas
 * exactement une flotte mixte pendant sa transition. Aucun etat sur la ligne. */
function OpexAirRefreshC121Plan(line, catalog, lines, airportType)
{
  if (lines == null) return null;
  local count = 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (vehicle in line.vehicles) {
      if (AIVehicle.IsValidVehicle(vehicle) && AIVehicle.GetVehicleType(vehicle) == AIVehicle.VT_AIR) count++;
    }
  } else if (("vehicle" in line) && AIVehicle.IsValidVehicle(line.vehicle)
      && AIVehicle.GetVehicleType(line.vehicle) == AIVehicle.VT_AIR) count++;
  local sites = [];
  foreach (tile in [line.stationA, line.stationB]) {
    local station = AIStation.GetStationID(tile);
    if (!AIStation.IsValidStation(station)) return null;
    local town = AIStation.GetNearestTown(station);
    if (!AITown.IsValidTown(town)) return null;
    local routes = OpexAirLiveRoutesAtAirport(tile, lines) - (count > 0 ? 1 : 0);
    if (routes < 0) routes = 0;
    sites.append({ anchor = tile, stationId = station, routes = routes,
        town = { id = town, tile = AITown.GetLocation(town), pop = AITown.GetPopulation(town) } });
  }
  /* Crash sans survivant : evaluer l'unique appareil a reconstituer. */
  if (count < 1) count = 1;
  local others = [];
  foreach (other in lines) { if (other != line) others.append(other); }
  local plan = { siteA = sites[0], siteB = sites[1], reuseA = true, reuseB = true,
      airport = { type = airportType, price = 0, maintenance = 0 },
      distance = OpexFlightDistance(line.stationA, line.stationB),
      monthlyPax = 0, refreshPlanes = count };
  OpexC121PrepareDemandShadow(catalog, plan, others);
  if (!("c121Demand" in plan)) return null;
  OpexC121PrepareEngineStatic(catalog, plan);
  return plan;
}

/* V252 Mode 1 : determine le meilleur modele d'avion actuellement constructible
 * pour une ligne donnee selon le critere causal du catalogue AIR (C68 / OpexAirEconomics).
 * V253 Mode 3 : C121 courant, nombre reel de creneaux, profit puis ROI.
 * Retourne l'EngineID retenu, ou null si choix indisponible ou impossible. */
function OpexAirBestEngineForLine(line, catalog, lines = null)
{
  if (catalog == null || !("airPlaneChoicesByAirport" in catalog) || catalog.airPlaneChoicesByAirport == null) {
    return null;
  }
  if (line == null || !("stationA" in line) || !("stationB" in line)) return null;
  if (!AIAirport.IsAirportTile(line.stationA) || !AIAirport.IsAirportTile(line.stationB)) return null;

  local typeA = AIAirport.GetAirportType(line.stationA);
  local typeB = AIAirport.GetAirportType(line.stationB);
  if (!AIAirport.IsValidAirportType(typeA) || !AIAirport.IsValidAirportType(typeB)) return null;

  local isSmall = (typeA == AIAirport.AT_SMALL || typeA == AIAirport.AT_COMMUTER ||
                   typeB == AIAirport.AT_SMALL || typeB == AIAirport.AT_COMMUTER);
  local airportType = isSmall ? ((typeA == AIAirport.AT_SMALL || typeA == AIAirport.AT_COMMUTER) ? typeA : typeB) : typeA;

  if (!(airportType in catalog.airPlaneChoicesByAirport)) return null;
  local choices = catalog.airPlaneChoicesByAirport[airportType];
  if (choices == null || choices.len() == 0) return null;

  local distance = ("distance" in line && line.distance > 0) ? line.distance : 0;
  if (distance <= 0) {
    distance = AIMap.DistanceManhattan(line.stationA, line.stationB);
  }
  local cargo = ("cargo" in line) ? line.cargo : catalog.paxCargo;

  /* Demande historique de la ligne. */
  local demandOld = ("airMonthlyPax" in line && line.airMonthlyPax > 0)
      ? line.airMonthlyPax
      : (("monthlyPax" in line && line.monthlyPax > 0) ? line.monthlyPax : 0);
  local demandNow = demandOld;

  local refreshPlan = null;
  if (V252_AIR_ENGINE_REFRESH == 3) {
    refreshPlan = OpexAirRefreshC121Plan(line, catalog, lines, airportType);
    if (refreshPlan == null) return null;
    demandNow = refreshPlan.c121Demand.paxA + refreshPlan.c121Demand.paxB;
  }

  /* Pour le journal seulement : jamais sur la ligne, qui est sauvegardee telle quelle. */
  if (DECISION_LOG) { V252_LAST_DEMAND_OLD = demandOld; V252_LAST_DEMAND_NOW = demandNow; }

  local monthlyPax = demandNow;
  if (monthlyPax <= 0) return null;

  local airportTile = ("originA" in line) && AIAirport.IsAirportTile(line.originA)
      ? line.originA : line.stationA;
  local hangar = AIAirport.GetHangarOfAirport(airportTile);
  local hasHangar = AIMap.IsValidTile(hangar) && AIAirport.IsHangarTile(hangar);

  local bestPlaneId = -1;
  local bestEconomics = null;
  /* OpexAirEconomics lit price et maintenance sans condition : aeroports deja payes. */
  local airportObj = { type = airportType, price = 0, maintenance = 0 };

  foreach (plane in choices) {
    if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
    if (!OpexAirPlaneInRange(plane, distance)) continue;
    if (!OpexAirAirportAcceptsPlane(typeA, plane.planeType) || !OpexAirAirportAcceptsPlane(typeB, plane.planeType)) continue;
    if (!AIEngine.CanRefitCargo(plane.id, cargo)) continue;
    if (hasHangar && AIVehicle.GetBuildWithRefitCapacity(hangar, plane.id, cargo) <= 0) continue;

    local economics = refreshPlan != null
        ? OpexC121EngineEconomics(catalog, refreshPlan, plane, refreshPlan.refreshPlanes)
        : OpexAirEconomics(catalog, airportObj, plane, distance, monthlyPax, false, 0, 0, 0, 1);
    if (economics == null) continue;
    if (DECISION_LOG && refreshPlan != null) OpexDecide("V253_CHOICE",
        "line=" + (("lineId" in line) ? line.lineId : -1)
        + " engine=" + plane.id + " distance=" + refreshPlan.distance
        + " demand=" + demandNow + " planes=" + refreshPlan.refreshPlanes
        + " speed=" + plane.speed + " capacity=" + plane.capacity
        + " price=" + plane.price + " running=" + plane.runningCost
        + " profit=" + economics.profitAnnual + " revenue=" + economics.revenueAnnual
        + " amort=" + economics.amortAnnual + " roi=" + economics.roi
        + " income_days=" + economics.incomeDays + " headway=" + economics.headwayDays
        + " pax=" + economics.carriedPax + " mail=" + economics.carriedMail);

    if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
        (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
      bestEconomics = economics;
      bestPlaneId = plane.id;
    }
  }

  if (bestPlaneId < 0) return null;
  return bestPlaneId;
}

/* V253 (Proposition 2) : Choix incrémental marginal par flux de trésorerie net.
 * Évalue les caractéristiques physiques et économiques d'un aéronef sur une liaison.
 * Rotations à la vitesse réelle NoAI (OpenTTD 15.3 script_engine.cpp:120, déjà
 * divisée par vehicle.plane_speed ; aucun /4 supplémentaire).
 * Constantes et sources :
 * - 0.036 : facteur cinématique OpenTTD de traversée de tuile par jour à V km/h (air_trip.nut:51).
 * - 3.0 : délai d'aéroport minimal terminal et roulage en jours (air_trip.nut:52).
 * - 365.0 : jours par an du calendrier OpenTTD (TimerGameCalendar::DAYS_IN_YEAR).
 * - (R + 1) / 256.0 : part captée par la note de gare MoveGoodsToStation (air_coverage.nut:445).
 */
function OpexV253PlaneOperations(catalog, planeObj, distance, demandAnnual, observedByte, servicePlane = null)
{
  local speed = (("speed" in planeObj) && planeObj.speed > 0)
      ? planeObj.speed.tofloat() : AIEngine.GetMaxSpeed(planeObj.id).tofloat();
  if (speed < 1.0) speed = 1.0;

  local flightDays = distance.tofloat() / (0.036 * speed);
  local oneWayDays = flightDays + 3.0;
  if (oneWayDays < 1.0) oneWayDays = 1.0;

  local incomeDays = oneWayDays.tointeger();
  if (incomeDays.tofloat() < oneWayDays) incomeDays++;
  if (incomeDays < 1) incomeDays = 1;

  local fare = OpexAirFarePerPax(catalog, planeObj, distance, incomeDays);
  if (fare <= 0.0) fare = 1.0;

  local predByte = observedByte;
  local capturedDemand = demandAnnual;
  if (servicePlane != null) {
    local ptsService = OpexC121SpeedRatingPoints(servicePlane);
    local ptsCand = OpexC121SpeedRatingPoints(planeObj);
    predByte = observedByte + ptsCand - ptsService;
    if (predByte < 0) predByte = 0;
    if (predByte > 255) predByte = 255;
    local obsShare = (observedByte + 1).tofloat() / 256.0;
    local predShare = (predByte + 1).tofloat() / 256.0;
    if (obsShare > 0.0) capturedDemand = demandAnnual.tofloat() * predShare / obsShare;
  }

  local cap = (("capacity" in planeObj) && planeObj.capacity > 0)
      ? planeObj.capacity : AIEngine.GetCapacity(planeObj.id);
  local roundTripDays = 2.0 * oneWayDays;
  local rotationsPerYear = 365.0 / roundTripDays;
  local annualCapacity = rotationsPerYear * (2.0 * cap);

  local carried = (annualCapacity < capturedDemand) ? annualCapacity : capturedDemand;
  local revenue = (carried * fare).tointeger();
  local running = (("runningCost" in planeObj) && planeObj.runningCost > 0)
      ? planeObj.runningCost : AIEngine.GetRunningCost(planeObj.id);

  return {
    engineId = planeObj.id,
    speed = speed,
    oneWayDays = oneWayDays,
    fare = fare,
    predByte = predByte,
    annualCapacity = annualCapacity,
    capturedDemand = capturedDemand,
    carried = carried,
    revenue = revenue,
    running = running
  };
}

/* V253 (mode 4) : Évalue le remplacement marginal d'un aéronef en service sur une ligne.
 * Remplace seulement si :
 *   gain annuel = Δrecette - Δentretien > 0, ET
 *   gain annuel * durée de vie restante de s >= prix d'achat(c) - valeur de revente(s).
 * Retourne une table { replace, targetEngine, gain, revNew, revOld, ratingPred, payback, price }.
 */
function OpexV253MarginalPlanForVehicle(line, catalog, vehicle, lines = null)
{
  if (catalog == null || !("airPlaneChoicesByAirport" in catalog) || catalog.airPlaneChoicesByAirport == null) {
    return null;
  }
  if (line == null || !("stationA" in line) || !("stationB" in line)) return null;
  if (!AIAirport.IsAirportTile(line.stationA) || !AIAirport.IsAirportTile(line.stationB)) return null;

  local typeA = AIAirport.GetAirportType(line.stationA);
  local typeB = AIAirport.GetAirportType(line.stationB);
  if (!AIAirport.IsValidAirportType(typeA) || !AIAirport.IsValidAirportType(typeB)) return null;

  local isSmall = (typeA == AIAirport.AT_SMALL || typeA == AIAirport.AT_COMMUTER ||
                   typeB == AIAirport.AT_SMALL || typeB == AIAirport.AT_COMMUTER);
  local airportType = isSmall ? ((typeA == AIAirport.AT_SMALL || typeA == AIAirport.AT_COMMUTER) ? typeA : typeB) : typeA;

  if (!(airportType in catalog.airPlaneChoicesByAirport)) return null;
  local choices = catalog.airPlaneChoicesByAirport[airportType];
  if (choices == null || choices.len() == 0) return null;

  if (!AIVehicle.IsValidVehicle(vehicle)) return null;
  local curEngine = AIVehicle.GetEngineType(vehicle);
  if (!AIEngine.IsValidEngine(curEngine)) return null;

  local distance = ("distance" in line && line.distance > 0) ? line.distance : 0;
  if (distance <= 0) {
    distance = AIMap.DistanceManhattan(line.stationA, line.stationB);
  }
  if (distance <= 0) return null;
  local cargo = ("cargo" in line) ? line.cargo : catalog.paxCargo;

  local airportTile = ("originA" in line) && AIAirport.IsAirportTile(line.originA)
      ? line.originA : line.stationA;
  local hangar = AIAirport.GetHangarOfAirport(airportTile);
  local hasHangar = AIMap.IsValidTile(hangar) && AIAirport.IsHangarTile(hangar);

  local curValue = AIVehicle.GetCurrentValue(vehicle);
  if (curValue < 0) curValue = 0;
  local ageLeftDays = AIVehicle.GetAgeLeft(vehicle);
  local remainingYears = ageLeftDays.tofloat() / 365.0;
  if (remainingYears < 0.0) remainingYears = 0.0;

  /* Demande observée de la ligne : transportés réels de l'an dernier + stock en attente. */
  local lineRevenue = 0;
  local nPlanes = 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      nPlanes++;
      local prof = AIVehicle.GetProfitLastYear(v);
      local run = AIVehicle.GetRunningCost(v);
      if (prof + run > 0) lineRevenue += (prof + run);
    }
  }
  if (nPlanes < 1) nPlanes = 1;

  local currentBaseOps = OpexV253PlaneOperations(catalog, { id = curEngine }, distance, 1.0, 50, null);
  local fare_s = currentBaseOps.fare;
  local annualDelivered = lineRevenue > 0 ? (lineRevenue.tofloat() / fare_s) : 0.0;

  local stA = AIStation.GetStationID(line.stationA);
  local stB = AIStation.GetStationID(line.stationB);
  local waiting = 0;
  if (AIStation.IsValidStation(stA)) waiting += AIStation.GetCargoWaiting(stA, cargo);
  if (AIStation.IsValidStation(stB)) waiting += AIStation.GetCargoWaiting(stB, cargo);

  local annualDemandPerPlane = (annualDelivered + waiting.tofloat()) / nPlanes.tofloat();
  if (annualDemandPerPlane < 1.0) annualDemandPerPlane = 1.0;

  local ratingA = AIStation.IsValidStation(stA) ? AIStation.GetCargoRating(stA, cargo) : -1;
  local ratingB = AIStation.IsValidStation(stB) ? AIStation.GetCargoRating(stB, cargo) : -1;
  local rating = ratingA;
  if (ratingB >= 0 && (rating < 0 || ratingB < rating)) rating = ratingB;
  if (rating < 0) rating = 50;
  local observedByte = OpexC121RatingPercentToByteMid(rating);

  local servicePlaneObj = { id = curEngine, speed = currentBaseOps.speed };
  local sOps = OpexV253PlaneOperations(catalog, servicePlaneObj, distance, annualDemandPerPlane, observedByte, null);
  local rev_s = sOps.revenue;
  local run_s = sOps.running;

  local bestPlan = null;
  local bestKeepCand = null;

  foreach (c in choices) {
    if (!AIEngine.IsValidEngine(c.id) || !AIEngine.IsBuildable(c.id)) continue;
    if (!OpexAirPlaneInRange(c, distance)) continue;
    if (!OpexAirAirportAcceptsPlane(typeA, c.planeType) || !OpexAirAirportAcceptsPlane(typeB, c.planeType)) continue;
    if (!AIEngine.CanRefitCargo(c.id, cargo)) continue;
    if (hasHangar && AIVehicle.GetBuildWithRefitCapacity(hangar, c.id, cargo) <= 0) continue;

    local cOps = OpexV253PlaneOperations(catalog, c, distance, annualDemandPerPlane, observedByte, servicePlaneObj);
    local rev_c = cOps.revenue;
    local run_c = cOps.running;
    local deltaRev = rev_c - rev_s;
    local deltaRun = run_c - run_s;
    local gain = deltaRev - deltaRun;

    local price_c = (("price" in c) && c.price > 0) ? c.price : AIEngine.GetPrice(c.id);
    local netCost = price_c - curValue;
    local pays = (c.id != curEngine) && (gain > 0) && (netCost <= 0 || (remainingYears > 0.0 && gain.tofloat() * remainingYears >= netCost));
    local payback = (gain > 0 && netCost > 0) ? (netCost.tofloat() / gain.tofloat()) : 0.0;

    if (pays) {
      if (bestPlan == null || gain > bestPlan.gain || (gain == bestPlan.gain && netCost < bestPlan.netCost)) {
        bestPlan = {
          engineId = c.id,
          gain = gain,
          revNew = rev_c,
          revOld = rev_s,
          ratingPred = cOps.predByte,
          payback = payback,
          price = price_c,
          netCost = netCost
        };
      }
    }

    if (c.id != curEngine) {
      if (bestKeepCand == null || gain > bestKeepCand.gain) {
        bestKeepCand = {
          engineId = c.id,
          gain = gain,
          revCand = rev_c,
          ratingPred = cOps.predByte,
          payback = payback,
          pays = pays
        };
      }
    }
  }

  if (bestPlan != null) {
    return {
      replace = true,
      targetEngine = bestPlan.engineId,
      gain = bestPlan.gain,
      revNew = bestPlan.revNew,
      revOld = bestPlan.revOld,
      ratingPred = bestPlan.ratingPred,
      payback = bestPlan.payback,
      price = bestPlan.price
    };
  }

  local reason = "current_best";
  if (bestKeepCand == null) reason = "no_candidate";
  else if (bestKeepCand.gain <= 0) reason = "gain_negative";
  else if (!bestKeepCand.pays) reason = "payback_failed";

  if (DECISION_LOG) {
    local candId = bestKeepCand != null ? bestKeepCand.engineId : -1;
    local candGain = bestKeepCand != null ? bestKeepCand.gain : 0;
    local candRev = bestKeepCand != null ? bestKeepCand.revCand : 0;
    local candRating = bestKeepCand != null ? bestKeepCand.ratingPred : observedByte;
    local candPayback = bestKeepCand != null ? bestKeepCand.payback : 0.0;
    OpexDecide("V252_KEEP", "line=" + (("lineId" in line) ? line.lineId : -1)
               + " old_engine=" + curEngine + " cand_engine=" + candId
               + " gain=" + candGain + " rev_cand=" + candRev + " rev_old=" + rev_s
               + " rating_pred=" + candRating + " payback=" + candPayback
               + " reason=" + reason);
  }

  return {
    replace = false,
    targetEngine = curEngine,
    gain = bestKeepCand != null ? bestKeepCand.gain : 0,
    revNew = bestKeepCand != null ? bestKeepCand.revCand : 0,
    revOld = rev_s,
    ratingPred = bestKeepCand != null ? bestKeepCand.ratingPred : observedByte,
    payback = bestKeepCand != null ? bestKeepCand.payback : 0.0,
    reason = reason
  };
}

function OpexAirAddPlane(line, catalog = null, lines = null)
{
  local result = { added = 0, reason = "" };
  if (!("vehicles" in line) || line.vehicles.len() == 0) {
    result.reason = "NOVEH"; return result;
  }
  local airportTile = ("originA" in line) && AIAirport.IsAirportTile(line.originA)
      ? line.originA
      : (AIAirport.IsAirportTile(line.stationA) ? line.stationA : null);
  if (airportTile == null) {
    result.reason = "NOAIR"; return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(airportTile);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    result.reason = "HANG"; return result;
  }
  local template = null;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) {
      template = v; break;
    }
  }
  if (template == null) { result.reason = "NOLIVE"; return result; }
  local oldEngine = AIVehicle.GetEngineType(template);
  local targetEngine = oldEngine;

  if (V252_AIR_ENGINE_REFRESH >= 1 && catalog != null) {
    local candidate = OpexAirBestEngineForLine(line, catalog, lines);
    if (candidate != null && candidate != oldEngine && AIEngine.IsBuildable(candidate)) {
      targetEngine = candidate;
    }
  }

  local price = AIEngine.GetPrice(targetEngine);
  if (price <= 0) { result.reason = "PRICE"; return result; }
  local need = price + OpexCashReserve() + 1000;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    if (money < need) {
      result.reason = "CASH"; return result;
    }
  }

  local extra = null;
  if (targetEngine == oldEngine) {
    extra = AIVehicle.CloneVehicle(hangar, template, true);
    if (!AIVehicle.IsValidVehicle(extra)) {
      local engine = AIVehicle.GetEngineType(template);
      local cargo = ("cargo" in line) ? line.cargo : 0;
      extra = AIVehicle.BuildVehicleWithRefit(hangar, engine, cargo);
      if (AIVehicle.IsValidVehicle(extra)) {
        if (!AIOrder.ShareOrders(extra, template)) {
          if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
          result.reason = "ORDER"; return result;
        }
      }
    }
  } else {
    local cargo = ("cargo" in line) ? line.cargo : 0;
    extra = AIVehicle.BuildVehicleWithRefit(hangar, targetEngine, cargo);
    if (AIVehicle.IsValidVehicle(extra)) {
      if (!AIOrder.ShareOrders(extra, template) && !AIOrder.CopyOrders(extra, template)) {
        if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
        extra = null;
      }
    }
    if (!AIVehicle.IsValidVehicle(extra)) {
      targetEngine = oldEngine;
      price = AIEngine.GetPrice(oldEngine);
      extra = AIVehicle.CloneVehicle(hangar, template, true);
    }
  }

  if (!AIVehicle.IsValidVehicle(extra)) {
    result.reason = "CLONE|" + AIError.GetLastError();
    return result;
  }
  if (!AIVehicle.StartStopVehicle(extra)) {
    if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
    result.reason = "START"; return result;
  }
  line.vehicles.append(extra);
  if (targetEngine != oldEngine) {
    line.refleetEngine = targetEngine;
    local dOld = V252_LAST_DEMAND_OLD;
    local dNow = V252_LAST_DEMAND_NOW;
    if (DECISION_LOG) OpexDecide("V252_ENGINE", "action=reinforce line=" + (("lineId" in line) ? line.lineId : -1)
                 + " old_engine=" + oldEngine + " new_engine=" + targetEngine + " price=" + price
                 + " demand_old=" + dOld + " demand_now=" + dNow
                 + " reason=reinforce");
  }
  result.added = 1;
  result.reason = "OK";
  return result;
}

/* Reconstitue un avion perdu sans dependre d'un appareil encore vivant. Le moteur
 * est memorise dans la ligne a sa construction; les deux aeroports sont des
 * destinations durables, donc les ordres peuvent etre recrees sans clonage. */
function OpexAirRefleetCrashedPlane(line, catalog = null, lines = null)
{
  local result = { added = 0, reason = "" };
  if (!(("refleetEngine" in line) && line.refleetEngine >= 0)) {
    result.reason = "NOENGINE"; return result;
  }
  if (!AIAirport.IsAirportTile(line.stationA) || !AIAirport.IsAirportTile(line.stationB)) {
    result.reason = "NOAIRPORT"; return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(line.stationA);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    result.reason = "HANGAR"; return result;
  }

  local oldEngine = line.refleetEngine;
  local targetEngine = oldEngine;
  if (V252_AIR_ENGINE_REFRESH >= 1 && catalog != null) {
    local candidate = OpexAirBestEngineForLine(line, catalog, lines);
    if (candidate != null && candidate != oldEngine && AIEngine.IsBuildable(candidate)) {
      targetEngine = candidate;
    }
  }

  if (AIVehicle.GetBuildWithRefitCapacity(hangar, targetEngine, line.cargo) <= 0) {
    if (targetEngine != oldEngine && AIVehicle.GetBuildWithRefitCapacity(hangar, oldEngine, line.cargo) > 0) {
      targetEngine = oldEngine;
    } else {
      result.reason = "REFIT"; return result;
    }
  }
  local price = AIEngine.GetPrice(targetEngine);
  if (price <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + OpexCashReserve()) {
    result.reason = "CASH"; return result;
  }
  local plane = AIVehicle.BuildVehicleWithRefit(hangar, targetEngine, line.cargo);
  if (!AIVehicle.IsValidVehicle(plane)) {
    if (targetEngine != oldEngine) {
      targetEngine = oldEngine;
      price = AIEngine.GetPrice(oldEngine);
      plane = AIVehicle.BuildVehicleWithRefit(hangar, oldEngine, line.cargo);
    }
  }
  if (!AIVehicle.IsValidVehicle(plane)) { result.reason = "BUILD"; return result; }
  local flagsA = AIOrder.OF_NONE;
  local flagsB = AIOrder.OF_NONE;
  if (!AIOrder.AppendOrder(plane, line.stationA, flagsA) ||
      !AIOrder.AppendOrder(plane, line.stationB, flagsB) || AIOrder.GetOrderCount(plane) != 2) {
    AIVehicle.SellVehicle(plane); result.reason = "ORDER"; return result;
  }
  if (!AIVehicle.StartStopVehicle(plane)) {
    if (AIVehicle.IsStoppedInDepot(plane)) AIVehicle.SellVehicle(plane);
    result.reason = "START"; return result;
  }
  if (!("vehicles" in line)) line.vehicles <- [];
  else if (line.vehicles == null) line.vehicles = [];
  line.vehicles.append(plane);
  if ("vehicle" in line) line.vehicle = plane;
  else line.vehicle <- plane;
  if (targetEngine != oldEngine) {
    line.refleetEngine = targetEngine;
    local dOld = V252_LAST_DEMAND_OLD;
    local dNow = V252_LAST_DEMAND_NOW;
    if (DECISION_LOG) OpexDecide("V252_ENGINE", "action=crash line=" + (("lineId" in line) ? line.lineId : -1)
                 + " old_engine=" + oldEngine + " new_engine=" + targetEngine + " price=" + price
                 + " demand_old=" + dOld + " demand_now=" + dNow
                 + " reason=crash_refleet");
  }
  result.added = 1; result.reason = "OK";
  return result;
}

/* V161 : valeur d'un renfort AIR nette de ce qu'il retire aux voisines.
 * Mesure du 12/10 (v160_B20x10, regression Delta profit par ligne, effets fixes d'annee,
 * 1973-74) : un avion de plus rapporte +13,4 k/an a SA ligne et retire -2,6 k/an a chaque
 * voisine ; la marge C121 et le profit moyen ne regardent que la ligne (23 a 73 k predits).
 * Une mesure en jeu a l'echelle de la grappe d'aeroports a ete essayee puis retiree : sans
 * temoin a flotte stable et avec les lignes neuves qui cannibalisent, elle donnait -5 a
 * -110 k par avion (smoke 12/10), et elle n'arrive qu'en 1974, quand la tresorerie n'est
 * plus le verrou (mediane 0,5 M en 1973, 1,4 M en 1974). L'a priori agit des 1970, la ou
 * la tresorerie lie (emprunt au maximum, 87 refus air faute de caisse en 1971).
 * Retourne null pour refuser le renfort, sinon { profit, source } ; source = "model"
 * (valeur historique, sous l'a priori ; calibree C70) ou "prior". */
function OpexV161PerPlaneProfit(line, entry, modelPerPlane)
{
  local neighbours = ("v161Neighbours" in entry) ? entry.v161Neighbours : 0;
  /* L'a priori mesure des profits annuels hors amortissement ; le modele C121 en est net. */
  local amort = (("c121VehicleAmortPerPlane" in line) && line.c121VehicleAmortPerPlane > 0)
      ? line.c121VehicleAmortPerPlane.tointeger() : 0;
  local prior = V161_PRIOR_OWN - V161_PRIOR_NEIGHBOUR * neighbours - amort;
  if (prior <= 0) return null;
  if (modelPerPlane <= prior) return { profit = modelPerPlane, source = "model" };
  return { profit = prior, source = "prior" };
}
