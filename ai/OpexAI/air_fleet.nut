/* Module AIR extrait de builder_air.nut (R11) : flottes et ajout d'avions. */
/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees. */
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
