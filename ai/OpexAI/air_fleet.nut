/* Module AIR extrait de builder_air.nut (R11) : flottes : reequipement, hangar, ajout et remplacement d'avions. */
function OpexAirLineSellValue(line)
{
  local total = 0;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v)) total += AIVehicle.GetCurrentValue(v);
  }
  return total;
}

function OpexAirLineReequipPending(line)
{
  return line != null && ("v92PendingEngine" in line) && line.v92PendingEngine >= 0;
}

function OpexAirClearReequip(line)
{
  if (line == null) return;
  if ("v92PendingEngine" in line) delete line.v92PendingEngine;
  if ("v92PendingCount" in line) delete line.v92PendingCount;
  if ("v92SentToHangar" in line) line.v92SentToHangar = [];
}

function OpexAirAlreadySentToHangar(line, vehicle)
{
  if (!("v92SentToHangar" in line) || line.v92SentToHangar == null) return false;
  foreach (id in line.v92SentToHangar) {
    if (id == vehicle) return true;
  }
  return false;
}

/* SendVehicleToDepot est une bascule, et l'ordre manuel n'est pas dans la liste
 * d'ordres. On memorise les vehicules deja envoyes et on ne les renvoie jamais.
 * Le hangar d'arrivee est le plus proche, pas forcement celui de l'aeroport A. */
function OpexAirSendLineToHangar(line, hangar)
{
  local waiting = false;
  foreach (v in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(v) || AIVehicle.IsStoppedInDepot(v)) continue;
    waiting = true;
    if (OpexAirAlreadySentToHangar(line, v)) continue;
    if (!AIVehicle.SendVehicleToDepot(v)) continue;
    if (!("v92SentToHangar" in line) || line.v92SentToHangar == null) line.v92SentToHangar <- [];
    line.v92SentToHangar.append(v);
  }
  return waiting;
}

function OpexAirReleaseHangarHold(line)
{
  if (line == null || !("vehicles" in line) || line.vehicles == null) {
    OpexAirClearReequip(line);
    return;
  }
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsStoppedInDepot(v)) AIVehicle.StartStopVehicle(v);
  }
  OpexAirClearReequip(line);
}

/* Repose `count` appareils d'un moteur deja vendu. Retourne le nombre rÃƒÆ’Ã‚Â©ellement relancÃƒÆ’Ã‚Â©. */
function OpexAirRebuildFleet(line, hangar, engineId, count, cargo)
{
  if (engineId < 0 || count < 1) return 0;
  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local restored = [];
  for (local i = 0; i < count; i++) {
    local aircraft = AIVehicle.BuildVehicleWithRefit(hangar, engineId, cargo);
    if (!AIVehicle.IsValidVehicle(aircraft)) break;
    local ordersOk = true;
    if (restored.len() == 0) {
      ordersOk = AIOrder.AppendOrder(aircraft, line.stationA, airFlagsA)
          && AIOrder.AppendOrder(aircraft, line.stationB, airFlagsB)
          && AIOrder.GetOrderCount(aircraft) == 2;
    } else {
      ordersOk = AIOrder.ShareOrders(aircraft, restored[0]);
    }
    if (!ordersOk || !AIVehicle.StartStopVehicle(aircraft)) {
      if (AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
      break;
    }
    restored.append(aircraft);
  }
  if (restored.len() == 0) return 0;
  line.vehicles = restored;
  line.vehicle = restored[0];
  line.refleetEngine = engineId;
  line.vehCount <- restored.len();
  line.trains = restored.len();
  return restored.len();
}

function OpexAirLineAllInHangar(line)
{
  local any = false;
  foreach (v in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    any = true;
    if (!AIVehicle.IsStoppedInDepot(v)) return false;
  }
  return any;
}

/* Vend la flotte et pose `count` appareils du nouveau moteur. En echec, rachete l'ancien. */
function OpexAirReplaceFleet(line, hangar, catalog, plane, count)
{
  if (plane == null || count < 1 || !OpexAirLineAllInHangar(line)) return null;
  local cargo = ("cargo" in line) ? line.cargo : catalog.paxCargo;
  local oldEngine = ("refleetEngine" in line) ? line.refleetEngine : -1;
  if (!AIEngine.IsBuildable(plane.id) || (oldEngine >= 0 && !AIEngine.IsBuildable(oldEngine))) {
    return { added = 0, reason = "ABORT" };
  }
  local sell = OpexAirLineSellValue(line);
  local cost = count * plane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money + sell < cost + OpexCashReserve()) return { added = 0, reason = "ABORT" };
  local old = [];
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v)) old.append(v);
  }
  local oldCount = old.len();
  local kept = [];
  foreach (v in old) {
    if (!AIVehicle.SellVehicle(v)) kept.append(v);
  }
  if (kept.len() > 0) {
    line.vehicles = kept;
    line.vehicle = kept[0];
    line.vehCount <- kept.len();
    line.trains = kept.len();
    return null;
  }
  local built = [];
  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local failed = false;
  for (local i = 0; i < count; i++) {
    local aircraft = AIVehicle.BuildVehicleWithRefit(hangar, plane.id, cargo);
    if (!AIVehicle.IsValidVehicle(aircraft)) { failed = true; break; }
    local ordersOk = true;
    if (built.len() == 0) {
      ordersOk = AIOrder.AppendOrder(aircraft, line.stationA, airFlagsA)
          && AIOrder.AppendOrder(aircraft, line.stationB, airFlagsB)
          && AIOrder.GetOrderCount(aircraft) == 2;
    } else {
      ordersOk = AIOrder.ShareOrders(aircraft, built[0]);
    }
    if (!ordersOk) {
      if (AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
      failed = true;
      break;
    }
    built.append(aircraft);
  }
  if (failed || built.len() != count) {
    foreach (aircraft in built) {
      if (AIVehicle.IsValidVehicle(aircraft) && AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
    }
    if (OpexAirRebuildFleet(line, hangar, oldEngine, oldCount, cargo) <= 0) {
      line.vehicles = [];
      line.vehicle = -1;
      line.vehCount <- 0;
      line.trains = 0;
    }
    return null;
  }
  local started = true;
  foreach (aircraft in built) {
    if (!AIVehicle.StartStopVehicle(aircraft)) {
      foreach (sold in built) {
        if (AIVehicle.IsValidVehicle(sold) && AIVehicle.IsStoppedInDepot(sold)) AIVehicle.SellVehicle(sold);
      }
      started = false;
      break;
    }
  }
  if (!started) {
    if (OpexAirRebuildFleet(line, hangar, oldEngine, oldCount, cargo) <= 0) {
      line.vehicles = [];
      line.vehicle = -1;
      line.vehCount <- 0;
      line.trains = 0;
    }
    return null;
  }
  line.vehicles = built;
  line.vehicle = built[0];
  line.refleetEngine = plane.id;
  line.planeId = plane.id;
  line.planeCapacity = plane.capacity;
  line.vehCount <- built.len();
  line.trains = built.len();
  line.v92LastReplaceYear <- AIDate.GetYear(AIDate.GetCurrentDate());
  OpexAirClearReequip(line);
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local mail = AIVehicle.GetCapacity(built[0], catalog.mailCargo);
    if (mail >= 0) AIR_MAIL_CAP.rawset(plane.id, mail);
  }
  return { added = 0, reason = "REPLACE", vehCount = built.len() };
}

/* Un autre moteur au meilleur nombre bat un appareil de plus du moteur actuel. */
function OpexAirConsiderReplace(line, catalog, airportTile)
{
  if (("scrapping" in line) && line.scrapping) return null;
  if (!("distance" in line) || line.distance <= 0) return null;
  if (!("airMonthlyPax" in line) || line.airMonthlyPax <= 0) return null;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (("v92LastReplaceYear" in line) && year - line.v92LastReplaceYear < 2) return null;
  local airportType = AIAirport.GetAirportType(airportTile);
  if (!AIAirport.IsValidAirportType(airportType)) return null;
  local currentId = ("refleetEngine" in line) ? line.refleetEngine : -1;
  if (currentId < 0) return null;
  local have = 0;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) have++;
  }
  if (have < 1) return null;
  OpexAirLearnMailCaps(catalog);
  local airport = {
    type = airportType,
    price = AIAirport.GetPrice(airportType),
    maintenance = AIAirport.GetMonthlyMaintenanceCost(airportType),
  };
  local infrastructure = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local current = OpexAirCatalogPlane(catalog, airportType, currentId);
  if (current == null) return null;
  OpexAirApplyKnownMail(current);
  local keep = OpexAirEconomics(catalog, airport, current, line.distance, line.airMonthlyPax,
      infrastructure, 0, 0, 0, have + 1, false, false);
  if (catalog.airPlaneChoicesByAirport == null
      || !(airportType in catalog.airPlaneChoicesByAirport)) return null;
  local bestPlane = null;
  local bestEcon = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airportType]) {
    if (plane.id == currentId || !OpexAirPlaneInRange(plane, line.distance)) continue;
    OpexAirApplyKnownMail(plane);
    local econ = OpexAirEconomics(catalog, airport, plane, line.distance, line.airMonthlyPax,
        infrastructure, 0, 0, 0, 0, false, true);
    if (OpexAirServiceBetter(econ, bestEcon)) {
      bestPlane = plane;
      bestEcon = econ;
    }
  }
  if (bestPlane == null) return null;
  local cap = OpexAirCadenceCap(line, catalog, null);
  if (cap < 1) cap = 1;
  if (bestEcon.planes > cap) {
    bestEcon = OpexAirEconomics(catalog, airport, bestPlane, line.distance, line.airMonthlyPax,
        infrastructure, 0, 0, 0, cap, false, false);
  }
  if (!OpexAirServiceBetter(bestEcon, keep)) return null;
  local sell = OpexAirLineSellValue(line);
  local cost = bestEcon.planes * bestPlane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money + sell < cost + OpexCashReserve()) return null;
  return { plane = bestPlane, count = bestEcon.planes };
}

function OpexAirMaybeReequip(line, catalog, hangar, airportTile)
{
  if (("v92PendingEngine" in line) && line.v92PendingEngine >= 0) {
    if (!OpexAirLineAllInHangar(line)) {
      OpexAirSendLineToHangar(line, hangar);
      return { added = 0, reason = "REEEQUIP_WAIT" };
    }
    local airportType = AIAirport.GetAirportType(airportTile);
    local plane = OpexAirCatalogPlane(catalog, airportType, line.v92PendingEngine);
    local count = ("v92PendingCount" in line) ? line.v92PendingCount : 1;
    local swapped = OpexAirReplaceFleet(line, hangar, catalog, plane, count);
    if (swapped != null && swapped.reason == "ABORT") {
      OpexAirReleaseHangarHold(line);
      return { added = 0, reason = "REEEQUIP_ABORT" };
    }
    if (swapped != null) return swapped;
    OpexAirClearReequip(line);
    return { added = 0, reason = "REEEQUIP_FAIL" };
  }
  local decision = OpexAirConsiderReplace(line, catalog, airportTile);
  if (decision == null) return null;
  line.v92PendingEngine <- decision.plane.id;
  line.v92PendingCount <- decision.count;
  OpexAirSendLineToHangar(line, hangar);
  if (OpexAirLineAllInHangar(line)) {
    local swapped = OpexAirReplaceFleet(line, hangar, catalog, decision.plane, decision.count);
    if (swapped != null && swapped.reason == "ABORT") {
      OpexAirReleaseHangarHold(line);
      return { added = 0, reason = "REEEQUIP_ABORT" };
    }
    if (swapped != null) return swapped;
    OpexAirClearReequip(line);
    return { added = 0, reason = "REEEQUIP_FAIL" };
  }
  return { added = 0, reason = "REEEQUIP_WAIT" };
}

/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees.
 * Sous V92, un autre service peut remplacer la flotte avant ce clonage. */
function OpexAirAddPlane(line, catalog = null)
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
  if (V92_AIR_SERVICE_CHOICE && catalog != null) {
    local swapped = OpexAirMaybeReequip(line, catalog, hangar, airportTile);
    if (swapped != null) return swapped;
  }
  local price = AIEngine.GetPrice(AIVehicle.GetEngineType(template));
  if (price <= 0) { result.reason = "PRICE"; return result; }
  local need = price + OpexCashReserve() + 1000;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    if (money < need) {
      result.reason = "CASH"; return result;
    }
  }
  local extra = AIVehicle.CloneVehicle(hangar, template, true);
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
  if (!AIVehicle.IsValidVehicle(extra)) {
    result.reason = "CLONE|" + AIError.GetLastError();
    return result;
  }
  if (!AIVehicle.StartStopVehicle(extra)) {
    if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
    result.reason = "START"; return result;
  }
  line.vehicles.append(extra);
  result.added = 1;
  result.reason = "OK";
  return result;
}

/* Reconstitue un avion perdu sans dependre d'un appareil encore vivant. Le moteur
 * est memorise dans la ligne a sa construction; les deux aeroports sont des
 * destinations durables, donc les ordres peuvent etre recrees sans clonage. */
function OpexAirRefleetCrashedPlane(line)
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
  if (AIVehicle.GetBuildWithRefitCapacity(hangar, line.refleetEngine, line.cargo) <= 0) {
    result.reason = "REFIT"; return result;
  }
  local price = AIEngine.GetPrice(line.refleetEngine);
  if (price <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + OpexCashReserve()) {
    result.reason = "CASH"; return result;
  }
  local plane = AIVehicle.BuildVehicleWithRefit(hangar, line.refleetEngine, line.cargo);
  if (!AIVehicle.IsValidVehicle(plane)) { result.reason = "BUILD"; return result; }
  local flagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local flagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
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
  result.added = 1; result.reason = "OK";
  return result;
}
