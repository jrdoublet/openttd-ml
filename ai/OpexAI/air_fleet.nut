/* Module AIR extrait de builder_air.nut (R11) : flottes, cible visible et ajout d'avions. */
/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees. */
/* Pour la concurrence visible, la borne du scan economique n'est pas une
 * capacite d'aeroport. La cible memorisee reste un plafond. Aucun
 * nouveau champ persistant et aucune vente implicite d'une flotte deja livree. */
function OpexC121AirTargetLimit(line, physicalCap)
{
  if (line == null || !("targetAirPlanes" in line) || line.targetAirPlanes <= 0
      || physicalCap <= 0) return 0;
  return line.targetAirPlanes < physicalCap ? line.targetAirPlanes : physicalCap;
}

/* Reconstructible monthly quote for EXISTING routes, including pre-candidate
 * saves. Exclude this route from hub service before adding its N aircraft;
 * otherwise its seats would be counted twice. Preserve observed marginals. */
function OpexC121RefreshVisibleFleet(catalog, line, lines, force = false)
{
  if (!C121_AIR_VISIBLE_COMPETITION || catalog == null
      || line == null || !("lineId" in line) || !("vehicles" in line)
      || !("stationA" in line) || !("stationB" in line)) return;
  local now = AIDate.GetCurrentDate();
  if (!force && line.lineId in C121_VISIBLE_FLEET_CACHE) {
    local state = C121_VISIBLE_FLEET_CACHE[line.lineId];
    if (now >= state.date && now - state.date < 30
        && state.vehicles == line.vehicles.len() && state.epoch == C121_CATALOG_ENDPOINT_EPOCH) return;
  }
  local template = null;
  local have = 0;
  foreach (v in line.vehicles) if (AIVehicle.IsValidVehicle(v)
      && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) { have++; if (template == null) template = v; }
  if (template == null || !AIAirport.IsAirportTile(line.stationA)
      || !AIAirport.IsAirportTile(line.stationB)) return;
  local sidA = AIStation.GetStationID(line.stationA);
  local sidB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(sidA) || !AIStation.IsValidStation(sidB)) return;
  local type = AIAirport.GetAirportType(line.stationA);
  local engine = AIVehicle.GetEngineType(template);
  local pax = AIVehicle.GetCapacity(template, catalog.paxCargo);
  local mail = catalog.mailCargo >= 0 ? AIVehicle.GetCapacity(template, catalog.mailCargo) : 0;
  if (pax <= 0 || mail < 0) return;
  local plane = { id = engine, capacity = pax, speed = AIEngine.GetMaxSpeed(engine),
    price = AIEngine.GetPrice(engine), runningCost = AIEngine.GetRunningCost(engine) };
  local quote = { siteA = { anchor = line.stationA, stationId = sidA,
      town = { id = AIStation.GetNearestTown(sidA) } },
    siteB = { anchor = line.stationB, stationId = sidB,
      town = { id = AIStation.GetNearestTown(sidB) } },
    reuseA = true, reuseB = true, airport = { type = type,
      price = AIAirport.GetPrice(type), maintenance = AIAirport.GetMonthlyMaintenanceCost(type) },
    arm = ("c121Arm" in line) ? line.c121Arm : "newpair",
    distance = OpexFlightDistance(line.stationA, line.stationB), plane = plane };
  local others = [];
  if (lines != null) foreach (other in lines) if (other != line) others.append(other);
  OpexC121PrepareDemandShadow(catalog, quote, others);
  OpexC121PrepareEngineStatic(catalog, quote);
  local target = null;
  local before = null;
  local after = null;
  if (C121_AIR_VISIBLE_FUSED) {
    local fused = OpexC121VisibleFleetEconomics(catalog, quote, plane, pax, mail, have);
    target = fused.target;
    before = fused.before;
    after = fused.after;
  } else {
    target = OpexC121AirEconomics(catalog, quote, plane, pax, mail, 0);
    before = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have);
    after = OpexC121AirEconomics(catalog, quote, plane, pax, mail, have+1);
  }
  if (target == null || before == null || after == null) return;
  line.targetAirPlanes <- target.planes;
  if ("c121TargetPlanes" in line) line.c121TargetPlanes = target.planes;
  local samples = ("c121MarginalSamples" in line) ? line.c121MarginalSamples : 0;
  if (samples <= 0) {
    line.c121MarginalProfit <- after.profitAnnual - before.profitAnnual;
    line.c121MarginalRevenue <- after.revenueAnnual - before.revenueAnnual;
    line.c121RealizationPmAtBuild <- (before.realizationFactor * 1000.0).tointeger();
  }
  C121_VISIBLE_FLEET_CACHE.rawset(line.lineId, { date = now,
      vehicles = line.vehicles.len(), epoch = C121_CATALOG_ENDPOINT_EPOCH });
  if (DECISION_LOG) AILog.Info("C121_VISIBLE_FLEET line=" + line.lineId + " have=" + have
      + " target=" + target.planes + " observed_samples=" + samples
      + " pax_raw_a=" + quote.c121Demand.paxRawA + " pax_raw_b=" + quote.c121Demand.paxRawB
      + " rival_weight_a=" + quote.c121Demand.paxCompetitionA.rivalWeight
      + " rival_weight_b=" + quote.c121Demand.paxCompetitionB.rivalWeight);
}

function OpexC121AirPhysicalTarget(line, catalog, lines)
{
  local isSmall = (AIAirport.IsAirportTile(line.stationA)
      && AIAirport.GetAirportType(line.stationA) == AIAirport.AT_SMALL)
      || (AIAirport.IsAirportTile(line.stationB)
          && AIAirport.GetAirportType(line.stationB) == AIAirport.AT_SMALL);
  local physicalCap = isSmall ? 4 : AIR_MAX_PLANES_PER_ROUTE;
  if (AIR_CADENCE_CAP) physicalCap = OpexAirCadenceCap(line, catalog != null ? catalog : {}, lines);
  return OpexC121AirTargetLimit(line, physicalCap);
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
  /* Revalider au dernier site d'achat : un projet peut etre cache et un autre
   * chantier peut avoir consomme la cadence partagee depuis sa generation. */
  if (C121_AIR_VISIBLE_COMPETITION) {
    OpexC121RefreshVisibleFleet(catalog, line, lines);
    local liveCount = 0;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) liveCount++;
    }
    local limit = OpexC121AirPhysicalTarget(line, catalog, lines);
    if (liveCount >= limit) {
      if (DECISION_LOG) OpexDecide("C121_TARGET_LIMIT", "phase=buy line=" + line.lineId
          + " have=" + liveCount + " limit=" + limit);
      result.reason = "TARGET"; return result;
    }
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
