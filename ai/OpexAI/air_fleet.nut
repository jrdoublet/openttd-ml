/* Module AIR extrait de builder_air.nut (R11) : flottes et ajout d'avions. */
/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees. */
/* V252 Mode 1 : determine le meilleur modele d'avion actuellement constructible
 * pour une ligne donnee selon le critere causal du catalogue AIR (C68 / OpexAirEconomics).
 * Retourne l'EngineID retenu, ou null si choix indisponible ou impossible. */
function OpexAirBestEngineForLine(line, catalog)
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
  /* Demande inconnue : pas de choix, le renfort clone comme avant. */
  local monthlyPax = ("airMonthlyPax" in line && line.airMonthlyPax > 0)
      ? line.airMonthlyPax
      : (("monthlyPax" in line && line.monthlyPax > 0) ? line.monthlyPax : 0);
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

    local economics = OpexAirEconomics(catalog, airportObj, plane, distance, monthlyPax, false, 0, 0, 0, 1);
    if (economics == null) continue;

    if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
        (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
      bestEconomics = economics;
      bestPlaneId = plane.id;
    }
  }

  if (bestPlaneId < 0) return null;
  return bestPlaneId;
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

  if (catalog != null) {
    local candidate = OpexAirBestEngineForLine(line, catalog);
    if (candidate != null && candidate != oldEngine && AIEngine.IsBuildable(candidate)) {
      targetEngine = candidate;
    }
  }

  if (AIR_GROW_MARGINAL > 0) {
    local marginal = OpexAirGrowMarginal(line, catalog, lines, "purchase", targetEngine);
    if (AIR_GROW_MARGINAL == 2 && marginal.fallback == "none" && marginal.dp <= 0) {
      result.reason = "MARGINAL"; return result;
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

  /* AIVehicle.IsValidVehicle attend un VehicleID entier, jamais null. */
  local extra = -1;
  if (targetEngine == oldEngine) {
    extra = AIVehicle.CloneVehicle(hangar, template, true);
    if (extra == null || !AIVehicle.IsValidVehicle(extra)) {
      local engine = AIVehicle.GetEngineType(template);
      local cargo = ("cargo" in line) ? line.cargo : 0;
      extra = AIVehicle.BuildVehicleWithRefit(hangar, engine, cargo);
      if (extra != null && AIVehicle.IsValidVehicle(extra)) {
        if (!AIOrder.ShareOrders(extra, template)) {
          if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
          result.reason = "ORDER"; return result;
        }
      }
    }
  } else {
    local cargo = ("cargo" in line) ? line.cargo : 0;
    extra = AIVehicle.BuildVehicleWithRefit(hangar, targetEngine, cargo);
    if (extra != null && AIVehicle.IsValidVehicle(extra)) {
      if (!AIOrder.ShareOrders(extra, template) && !AIOrder.CopyOrders(extra, template)) {
        if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
        /* L'avion a ete revendu : repli sur le clonage de l'ancien modele. */
        extra = -1;
      }
    }
    if (extra == null || !AIVehicle.IsValidVehicle(extra)) {
      if (AIR_GROW_MARGINAL > 0) {
        local marginal = OpexAirGrowMarginal(line, catalog, lines, "clone_fallback", oldEngine);
        if (AIR_GROW_MARGINAL == 2 && marginal.fallback == "none" && marginal.dp <= 0) {
          result.reason = "MARGINAL"; return result;
        }
      }
      targetEngine = oldEngine;
      price = AIEngine.GetPrice(oldEngine);
      extra = AIVehicle.CloneVehicle(hangar, template, true);
    }
  }

  if (extra == null || !AIVehicle.IsValidVehicle(extra)) {
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
    if (DECISION_LOG) OpexDecide("V252_ENGINE", "action=reinforce line=" + (("lineId" in line) ? line.lineId : -1)
                 + " old_engine=" + oldEngine + " new_engine=" + targetEngine + " price=" + price
                 + " reason=reinforce");
  }
  result.added = 1;
  result.reason = "OK";
  return result;
}

/* Reconstitue un avion perdu sans dependre d'un appareil encore vivant. Le moteur
 * est memorise dans la ligne a sa construction; les deux aeroports sont des
 * destinations durables, donc les ordres peuvent etre recrees sans clonage. */
function OpexAirRefleetCrashedPlane(line, catalog = null)
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
  if (catalog != null) {
    local candidate = OpexAirBestEngineForLine(line, catalog);
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
    if (DECISION_LOG) OpexDecide("V252_ENGINE", "action=crash line=" + (("lineId" in line) ? line.lineId : -1)
                 + " old_engine=" + oldEngine + " new_engine=" + targetEngine + " price=" + price
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

/* AIR-GROW: no persistent state. C117 current window, quantities/year (365.25 d).
 * A C117 leg labelled A has destination A, hence its pickup belongs to B.
 * D = (observed pickups + current backlog) * 365.25 / windowDays, fixed for
 * both fleet sizes. This deliberately drains the backlog over one window;
 * it predicts no rating improvement. Shared stations are explicitly unknown.
 * K = N * purchased-engine capacity * rotations/year, independently per cargo.
 */
function OpexAirGrowMarginalEstimate(line, catalog, lines, forcedEngine = null)
{
  local r = { fallback = "observation", n = 0, d = "unknown", kn = "unknown",
    kn1 = "unknown", drev = 0.0, cost = 0.0, amort = 0.0, dp = 0.0, price = 0 };
  if (line != null && ("vehCount" in line)) r.n = line.vehCount;
  if (line == null || catalog == null || !("lineId" in line)
      || !(line.lineId in C117_AIR_LINE_STATE)) return r;
  if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) {
    r.fallback = "fleet_changed"; return r;
  }
  if (!("stationA" in line) || !("stationB" in line)
      || !AIAirport.IsAirportTile(line.stationA) || !AIAirport.IsAirportTile(line.stationB)) {
    r.fallback = "station"; return r;
  }
  if (!("cargo" in line) || !("paxCargo" in catalog)) { r.fallback = "cargo"; return r; }
  local s = C117_AIR_LINE_STATE[line.lineId];
  local days = s.lastDate - s.startDate;
  if (days < 14 || AIDate.GetCurrentDate() - s.lastDate > 3
      || s.tripsA < 1 || s.tripsB < 1 || s.invalidOrderSamples > 0
      || s.unobservedTransitions > 0 || s.engineChanges > 0
      || s.mixedEngineSamples > 0) return r;
  local template = null;
  r.n = 0;
  foreach (v in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
    r.n++;
    if (AIVehicle.GetEngineType(v) != s.lastEngine) { r.fallback = "fleet_changed"; return r; }
    if (template == null) template = v;
  }
  if (r.n <= 0 || s.lastLive != r.n || s.liveSum != s.samples * r.n) {
    r.fallback = "fleet_changed"; return r;
  }
  local stationA = OpexAirLineStationId(line, 0);
  local stationB = OpexAirLineStationId(line, 1);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) || stationA == stationB
      || lines == null) { r.fallback = "station"; return r; }
  foreach (other in lines) {
    if (other == null || other == line || !("stationA" in other) || !("stationB" in other)) continue;
    if (OpexAirLineStationId(other, 0) == stationA || OpexAirLineStationId(other, 0) == stationB
        || OpexAirLineStationId(other, 1) == stationA || OpexAirLineStationId(other, 1) == stationB) {
      r.fallback = "shared_station"; return r;
    }
  }
  local engine = forcedEngine;
  if (engine == null) engine = OpexAirBestEngineForLine(line, catalog);
  if (engine == null) engine = AIVehicle.GetEngineType(template);
  local oldEngine = AIVehicle.GetEngineType(template);
  local paxCap = 0;
  local mailCap = 0;
  if (!("mailCargo" in catalog) || !AICargo.IsValidCargo(catalog.mailCargo)
      || line.cargo != catalog.paxCargo) { r.fallback = "cargo"; return r; }
  if (engine == oldEngine) {
    paxCap = AIVehicle.GetCapacity(template, line.cargo);
    mailCap = AIVehicle.GetCapacity(template, catalog.mailCargo);
  } else if (engine in C121_AIR_ENGINE_CAPACITY_OBS) {
    local caps = C121_AIR_ENGINE_CAPACITY_OBS[engine];
    if (caps == null || !("pax" in caps) || !("mail" in caps)) { r.fallback = "engine_capacity"; return r; }
    paxCap = caps.pax; mailCap = caps.mail;
  } else { r.fallback = "engine_capacity"; return r; }
  if (paxCap <= 0 || mailCap < 0) { r.fallback = "engine_capacity"; return r; }
  local distance = AIMap.DistanceManhattan(line.stationA, line.stationB);
  local plan = { distance = distance, airport = { type = AIAirport.GetAirportType(line.stationA) },
    siteA = { anchor = line.stationA, stationId = stationA },
    siteB = { anchor = line.stationB, stationId = stationB }, reuseA = true, reuseB = true };
  local trip = OpexC121AirTripModel(plan, { id = engine });
  if (trip == null || trip.roundTripDays <= 0) { r.fallback = "rotation"; return r; }
  local roundDays = trip.roundTripDays;
  /* Observed full rotation = twice the mean completed leg, with loading time.
   * Different purchased engine: C121 instead of reusing the old engine speed. */
  if (engine == oldEngine && s.legDaysN >= 2 && s.legDays > 0)
    roundDays = 2.0 * s.legDays / s.legDaysN;
  local rotations = 365.25 / roundDays;
  local incomeDays = OpexC121PhysicalPaymentDays(trip);
  r.price = AIEngine.GetPrice(engine);
  r.cost = AIEngine.GetRunningCost(engine).tofloat();
  local lifeDays = AIEngine.GetMaxAge(engine);
  if (r.price <= 0 || r.cost < 0 || lifeDays <= 0) { r.fallback = "cost"; return r; }
  r.amort = r.price.tofloat() * 365.25 / lifeDays;
  r.d = ""; r.kn = ""; r.kn1 = "";
  for (local direction = 0; direction < 2; direction++) {
    local station = direction == 0 ? stationA : stationB;
    for (local cargoIndex = 0; cargoIndex < 2; cargoIndex++) {
      local cargo = cargoIndex == 0 ? line.cargo : catalog.mailCargo;
      local cap = cargoIndex == 0 ? paxCap : mailCap;
      local picked = cargoIndex == 0 ? (direction == 0 ? s.paxB : s.paxA)
                                    : (direction == 0 ? s.mailB : s.mailA);
      local waiting = AIStation.GetCargoWaiting(station, cargo);
      local fare = AICargo.GetCargoIncome(cargo, distance, incomeDays);
      if (waiting < 0 || fare < 0) { r.fallback = "flow_or_fare"; return r; }
      local demand = (picked.tofloat() + waiting) * 365.25 / days;
      local kn = r.n * cap * rotations;
      local kn1 = (r.n + 1) * cap * rotations;
      r.drev += fare * ((demand < kn1 ? demand : kn1) - (demand < kn ? demand : kn));
      if (DECISION_LOG) {
        local sep = direction == 0 && cargoIndex == 0 ? "" : ",";
        r.d += sep + demand; r.kn += sep + kn; r.kn1 += sep + kn1;
      }
    }
  }
  r.dp = r.drev - r.cost - r.amort;
  r.fallback = "none";
  return r;
}

/* Every call is behind AIR_GROW_MARGINAL > 0. Logs alone count fallback reasons;
 * no accumulator or behavioural state is saved. prior is the existing score. */
function OpexAirGrowMarginal(line, catalog, lines, prior, forcedEngine = null)
{
  local r = OpexAirGrowMarginalEstimate(line, catalog, lines, forcedEngine);
  if (DECISION_LOG) OpexAirGrowMarginalLog(line, r,
      typeof prior == "string" ? "unknown" : prior,
      typeof prior == "string" ? prior : "execute");
  return r;
}

function OpexAirGrowMarginalLog(line, r, prior, phase)
{
  if (DECISION_LOG) OpexDecide("AIR_GROW_MARGINAL", "line=" + line.lineId
      + " n=" + r.n + " d=" + r.d + " kn=" + r.kn + " kn1=" + r.kn1
      + " drev=" + r.drev + " cost=" + r.cost + " amort=" + r.amort
      + " dp=" + (r.fallback == "none" ? r.dp.tostring() : "unknown") + " prior=" + prior
      + " decision=" + (AIR_GROW_MARGINAL == 1 ? "shadow" :
          (r.fallback != "none" ? "legacy" : (r.dp > 0 ? "accept" : "reject")))
      + " fallback=" + r.fallback + " phase=" + phase);
}
