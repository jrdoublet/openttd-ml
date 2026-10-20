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
