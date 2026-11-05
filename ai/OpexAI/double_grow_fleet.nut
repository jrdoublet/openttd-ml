/* DOUBLE-GROW : une rame supplementaire par decision, uniquement sur une
 * double voie directionnelle certifiee. La construction des aiguillages, PBS
 * one-way et waypoints appartient au module de geometrie. Ce module ne pose
 * aucun rail et ne transforme jamais une double voie independante en boucle.
 * Tous les etats durables sont de simples entiers dans la ligne sauvegardee. */

function OpexDoubleGrowLog(action, line, fields)
{
  if (DECISION_LOG) OpexDecide("DOUBLE_GROW", "action=" + action
      + " line=" + line.lineId + " trains=" + line.vehicles.len() + " " + fields);
}

/* La certification doit provenir du constructeur DIRECTIONNEL, jamais du
 * seul succes des quais ou des deux traces. Les ordres des rames historiques
 * sont verifies avant de les partager : meme gare, memes waypoints et memes
 * drapeaux, sans perte du plein chargement de la SOURCE. */
function OpexDoubleGrowOrdersSafe(line)
{
  if (!("doubleGrowDirectional" in line) || !line.doubleGrowDirectional
      || !("doubleTrack" in line) || line.doubleTrack != 1
      || (("v190Independent" in line) && line.v190Independent)
      || !("stationA" in line) || !("stationB" in line)
      || !("vehicles" in line) || line.vehicles == null
      || !("trains" in line) || line.vehicles.len() < 2
      || line.trains != line.vehicles.len()) return false;
  local a = AIStation.GetStationID(line.stationA);
  local b = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(a) || !AIStation.IsValidStation(b) || a == b)
    return false;
  local model = line.vehicles[0];
  if (!AIVehicle.IsValidVehicle(model) || AIOrder.GetOrderCount(model) != 4
      || !AIOrder.IsGotoStationOrder(model, 0)
      || !AIOrder.IsGotoWaypointOrder(model, 1)
      || !AIOrder.IsGotoStationOrder(model, 2)
      || !AIOrder.IsGotoWaypointOrder(model, 3)
      || AIStation.GetStationID(AIOrder.GetOrderDestination(model, 0)) != a
      || AIStation.GetStationID(AIOrder.GetOrderDestination(model, 2)) != b
      || (AIOrder.GetOrderFlags(model, 0) & AIOrder.OF_FULL_LOAD_ANY) == 0
      || (AIOrder.GetOrderFlags(model, 2) & AIOrder.OF_FULL_LOAD_ANY) != 0)
    return false;
  local waypointAB = AIOrder.GetOrderDestination(model, 1);
  local waypointBA = AIOrder.GetOrderDestination(model, 3);
  if (!AIRail.IsRailWaypointTile(waypointAB)
      || !AIRail.IsRailWaypointTile(waypointBA)) return false;
  local wpAB = AIWaypoint.GetWaypointID(waypointAB);
  local wpBA = AIWaypoint.GetWaypointID(waypointBA);
  if (!AIWaypoint.IsValidWaypoint(wpAB) || !AIWaypoint.IsValidWaypoint(wpBA)
      || wpAB == wpBA) return false;
  foreach (vehicle in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(vehicle)
        || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL
        || AIOrder.GetOrderCount(vehicle) != 4
        || AIStation.GetStationID(AIOrder.GetOrderDestination(vehicle, 0)) != a
        || AIStation.GetStationID(AIOrder.GetOrderDestination(vehicle, 2)) != b
        || AIWaypoint.GetWaypointID(AIOrder.GetOrderDestination(vehicle, 1)) != wpAB
        || AIWaypoint.GetWaypointID(AIOrder.GetOrderDestination(vehicle, 3)) != wpBA)
      return false;
    for (local i = 0; i < 4; i++) {
      if (AIOrder.GetOrderFlags(vehicle, i) != AIOrder.GetOrderFlags(model, i))
        return false;
    }
  }
  return true;
}

/* Les signaux unidirectionnels restent presents sur les DEUX branches. Une
 * rame par bloc directionnel au minimum, soit ceil(N/2) blocs par voie pour
 * N trains. Cette porte est volontairement conservative en cas de demolitions
 * apres la construction ou de route non attestee par le constructeur. */
function OpexDoubleGrowSignalsSafe(line, wanted)
{
  if (!("SIGNALTYPE_PBS_ONEWAY" in AIRail)) return false;
  if (!("tiles1" in line) || !("tiles2" in line)
      || line.tiles1 == null || line.tiles2 == null) return false;
  local first = line.tiles1;
  local second = line.tiles2;
  if (first.len() < 8 || second.len() < 8) return false;
  local need = (wanted + 1) / 2;
  local count1 = 0;
  local count2 = 0;
  for (local i = 1; i < first.len() - 1; i++) {
    local tile = first[i];
    local prev = first[i - 1];
    if (AIRail.IsRailTile(tile) && AIMap.DistanceManhattan(tile, prev) == 1
        && AIRail.GetSignalType(tile, prev) == AIRail.SIGNALTYPE_PBS_ONEWAY)
      count1++;
  }
  for (local j = 1; j < second.len() - 1; j++) {
    local tile = second[j];
    local next = second[j + 1];
    if (AIRail.IsRailTile(tile) && AIMap.DistanceManhattan(tile, next) == 1
        && AIRail.GetSignalType(tile, next) == AIRail.SIGNALTYPE_PBS_ONEWAY)
      count2++;
  }
  return count1 >= need && count2 >= need;
}

/* Une production deja captee par plusieurs lignes de la meme origine n'est
 * disponible qu'une fois. Le stock de gare est amorti sur douze mois : une
 * pointe passagere ne justifie pas une flotte de huit rames. */
function OpexDoubleGrowMargin(owner, line, model)
{
  if (!("srcIndustry" in line) && !("originA" in line)) return null;
  local source = ("srcIndustry" in line) ? line.srcIndustry
      : AIIndustry.GetIndustryID(line.originA);
  if (!AIIndustry.IsValidIndustry(source)) return null;
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)
      || !AIStation.HasCargoRating(station, line.cargo)) return null;
  local production = AIIndustry.GetLastMonthProduction(source, line.cargo);
  local carried = AIIndustry.GetLastMonthTransportedPercentage(source, line.cargo);
  local rating = AIStation.GetCargoRating(station, line.cargo);
  local waiting = AIStation.GetCargoWaiting(station, line.cargo);
  local trainCapacity = AIVehicle.GetCapacity(model, line.cargo);
  if (production <= 0 || carried < 0 || carried > 100
      || rating <= 0 || rating > 100 || waiting < 0 || trainCapacity <= 0
      || waiting.tofloat() < trainCapacity * 0.75
      || (carried >= 95 && waiting < 2 * trainCapacity)) return null;
  local dist = (("routeDistance" in line) && line.routeDistance > 0)
      ? line.routeDistance : line.distance;
  if (dist <= 0) return null;
  local loco = OpexV257Engine(AIVehicle.GetEngineType(model), line.cargo, false);
  local wagonId = AIVehicle.GetWagonEngineType(model, 1);
  local wagon = OpexV257Engine(wagonId, line.cargo, true);
  if (loco == null || wagon == null || wagon.capacity <= 0) return null;
  local speed = OpexRailEffectiveSpeed(loco, wagon,
      AIVehicle.GetNumWagons(model) - 1, dist);
  if (speed <= 0) return null;
  local cycle = 2.0 * dist / (0.036 * speed) + OpexRailStationDwellDays(wagon);
  if (cycle <= 0) return null;
  local newMonthly = trainCapacity * 30.0 / cycle;
  local usedMonthly = 0.0;
  foreach (existing in owner._lines) {
    if (existing == null || !("mode" in existing) || existing.mode != "rail"
        || !("kind" in existing) || existing.kind != "freight"
        || !("cargo" in existing) || existing.cargo != line.cargo) continue;
    local existingSource = ("srcIndustry" in existing) ? existing.srcIndustry
        : (("originA" in existing) ? AIIndustry.GetIndustryID(existing.originA) : -1);
    if (existingSource == source) usedMonthly += OpexInvestStallLineCapacity(existing);
  }
  local free = production.tofloat() * rating / 100.0 - usedMonthly
      + waiting.tofloat() / 12.0;
  if (free <= 0) return null;
  local extra = min(newMonthly, free);
  if (extra < newMonthly * 0.55) return null;
  local days = OpexCeilDiv(dist / (0.036 * speed) + 1, 1);
  local income = AICargo.GetCargoIncome(line.cargo, line.distance, days);
  if (income <= 0) return null;
  local price = 0;
  local units = AIVehicle.GetNumWagons(model);
  if (units < 2) return null;
  for (local i = 0; i < units; i++) {
    local engine = AIVehicle.GetWagonEngineType(model, i);
    if (!AIEngine.IsBuildable(engine)) return null;
    price += AIEngine.GetPrice(engine);
  }
  local years = AIEngine.GetMaxAge(AIVehicle.GetEngineType(model)).tofloat() / 365.0;
  local running = AIVehicle.GetRunningCost(model);
  if (price <= 0 || years <= 0 || running < 0) return null;
  local revenue = 12.0 * extra * income;
  local annualProfit = revenue - running - price / years;
  /* MARGE apres depreciation et retour du capital en cinq ans. */
  if (annualProfit <= 0 || 5.0 * (revenue - running) <= price
      || OpexAvailableCapital() < price + 1000) return null;
  return { score = annualProfit / price, profit = annualProfit,
      cost = price, production = production, carried = carried,
      rating = rating, waiting = waiting, extra = extra,
      trainCapacity = trainCapacity, usedMonthly = usedMonthly };
}

function OpexDoubleGrowQuote(owner, line)
{
  if (owner == null || owner._lines == null || line == null
      || !("mode" in line) || line.mode != "rail"
      || !("kind" in line) || line.kind != "freight"
      || !("lineId" in line) || !("cargo" in line)
      || !("vehicles" in line) || !("depot" in line)
      || !("depot2" in line)
      || !("platformLength" in line) || line.platformLength < 2
      || !("distance" in line) || line.distance <= 0
      || !("lastProfit" in line) || line.lastProfit <= 0
      || (("scrapping" in line) && line.scrapping)
      || (("expandBlocked" in line) && line.expandBlocked)
      || !OpexRailVehicleSlotAvailable()) return null;
  /* DOUBLE-GROW dispose de son propre plafond : le v190_max_trains
   * historique (defaut 4) ne doit pas bloquer ce lot a quatre rames. */
  local cap = DOUBLE_GROW_V2 ? 6 : 8;
  if (cap < 3 || line.vehicles == null || line.vehicles.len() >= cap
      || !OpexDoubleGrowOrdersSafe(line)
      || !OpexDoubleGrowSignalsSafe(line, line.vehicles.len() + 1)) return null;
  local depot = (line.vehicles.len() % 2 == 0) ? line.depot : line.depot2;
  local model = (line.vehicles.len() % 2 == 0) ? line.vehicles[0] : line.vehicles[1];
  if (depot == null || !AIRail.IsRailDepotTile(depot)
      || AITile.GetOwner(depot) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)
      || !AIVehicle.IsValidVehicle(model)
      || AIVehicle.GetLength(model) > min(line.platformLength,
          AIGameSettings.GetValue("vehicle.max_train_length")) * 16
      || !AIEngine.HasPowerOnRail(AIVehicle.GetEngineType(model), AIRail.GetRailType(depot)))
    return null;
  local margin = OpexDoubleGrowMargin(owner, line, model);
  if (margin == null) return null;
  return { depot = depot, model = model, margin = margin };
}

/* En une transaction courte : relire la marge, unifier les ordres historiques
 * de meme destination, cloner des ordres partages, forcer le depart A et enfin
 * enregistrer le nouvel ID. En cas d'echec, ne vendre QUE ce clone, arrete au
 * depot precis ou nous venons de le creer. */
function OpexDoubleGrowFleet(owner, line)
{
  if (!(DOUBLE_GROW || DOUBLE_GROW_V2) || !MODE_RAIL || !SAVE_FULL_STATE || owner == null
      || owner._catalog == null || owner._lines == null
      || owner._railExpansion != null || owner._v257Pending != null
      || owner._v271Pending != null || owner._railSearch != null
      || owner._railLongV2Pending != null || OpexV284Busy(owner)) return false;
  if (line == null || !OpexDoubleGrowOrdersSafe(line)) return false;
  /* Apres un Save ou un echec de demarrage lors de la conversion initiale,
   * retenter le depart d'une rame de CETTE ligne depuis un de ses depots.
   * Ne jamais creer une autre rame tant qu'une rame reste arretée. */
  foreach (existing in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(existing)) return false;
    if (!AIVehicle.IsStoppedInDepot(existing)) continue;
    local location = AIVehicle.GetLocation(existing);
    if (location != line.depot && location != line.depot2) return false;
    local position = AIOrder.ResolveOrderPosition(existing, AIOrder.ORDER_CURRENT);
    if (position != 0 && !AIOrder.SkipToOrder(existing, 0)) return false;
    if (!AIVehicle.StartStopVehicle(existing)) return false;
    OpexDoubleGrowLog("resumed", line, "vehicle=" + existing);
    return true;
  }
  if (("doubleGrowNextDate" in line)
      && AIDate.GetCurrentDate() < line.doubleGrowNextDate) return false;
  local quote = OpexDoubleGrowQuote(owner, line);
  if (quote == null) return false;
  if (FLEET_ARB && !OpexFleetRequest(line, "rail", "add_vehicle", quote.margin.cost,
      quote.margin.profit, "DOUBLE_GROW")) return false;
  local first = line.vehicles[0];
  for (local i = 1; i < line.vehicles.len(); i++) {
    if (!AIOrder.ShareOrders(line.vehicles[i], first)) {
      OpexDoubleGrowLog("skip", line, "reason=share_orders");
      return false;
    }
  }
  /* La provenance du depot n'est jamais deduite de la position du modele :
   * les deux depots deja certifies sont alternes pour repartir les entrees. */
  local oldType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(quote.depot));
  local extra = AIVehicle.CloneVehicle(quote.depot, quote.model, true);
  AIRail.SetCurrentRailType(oldType);
  if (!AIVehicle.IsValidVehicle(extra)) {
    OpexDoubleGrowLog("skip", line, "reason=clone_failed");
    return false;
  }
  local ok = AIVehicle.IsStoppedInDepot(extra)
      && AIVehicle.GetLocation(extra) == quote.depot
      && AIOrder.GetOrderCount(extra) == 4
      && (AIOrder.GetOrderFlags(extra, 0) & AIOrder.OF_FULL_LOAD_ANY) != 0
      && AIOrder.IsGotoWaypointOrder(extra, 1)
      && AIOrder.IsGotoWaypointOrder(extra, 3)
      && AIOrder.GetOrderDestination(extra, 1) == AIOrder.GetOrderDestination(first, 1)
      && AIOrder.GetOrderDestination(extra, 3) == AIOrder.GetOrderDestination(first, 3)
      && AIVehicle.GetCapacity(extra, line.cargo) == AIVehicle.GetCapacity(quote.model, line.cargo);
  if (ok && AIOrder.ResolveOrderPosition(extra, AIOrder.ORDER_CURRENT) != 0)
    ok = AIOrder.SkipToOrder(extra, 0);
  if (ok) ok = AIVehicle.StartStopVehicle(extra);
  if (!ok) {
    if (AIVehicle.IsValidVehicle(extra) && AIVehicle.IsStoppedInDepot(extra)
        && AIVehicle.GetLocation(extra) == quote.depot)
      AIVehicle.SellVehicle(extra);
    OpexDoubleGrowLog("skip", line, "reason=clone_orders_or_start");
    return false;
  }
  line.vehicles.append(extra);
  line.trains = line.vehicles.len();
  line.vehCount <- line.trains;
  line.doubleGrowNextDate <- AIDate.GetCurrentDate() + 90;
  owner._saveProjection = null;
  OpexDoubleGrowLog("built", line, "profit=" + quote.margin.profit.tointeger()
      + " cost=" + quote.margin.cost + " monthly_extra=" + quote.margin.extra.tointeger()
      + " waiting=" + quote.margin.waiting + " production=" + quote.margin.production
      + " carried_pct=" + quote.margin.carried + " shared_orders=1 source_full=1");
  return true;
}

/* Finalisation de la DEUXIEME rame. Le constructeur a pose uniquement le
 * deuxieme quai, la voie et le depot et livre une COPIE stagedLine avec une
 * seule rame. Le convertisseur V190-FIX2 pose les jonctions directionnelles,
 * PBS_ONEWAY, waypoints, puis les ordres A/WP_AB/B/WP_BA sur les deux rames.
 * Le constructeur adopte seul stagedLine apres succes. En echec, retirer
 * tous les wagons neufs, garder la rame historique, puis laisser au caller
 * le rollback de la seule infrastructure secondaire. */
function OpexDoubleGrowFleetFinalize(owner, line, stagedLine)
{
  if (!(DOUBLE_GROW || DOUBLE_GROW_V2) || !MODE_RAIL || !SAVE_FULL_STATE || owner == null
      || owner._catalog == null || line == null || stagedLine == null
      || !("kind" in line) || line.kind != "freight"
      || !("cargo" in line) || !("loco" in line) || !("wagons" in line)
      || !("platformLength" in line) || !("depot" in line)
      || !("vehicles" in line) || line.vehicles == null || line.vehicles.len() != 1
      || !("vehicles" in stagedLine) || stagedLine.vehicles == null
      || stagedLine.vehicles.len() != 1 || stagedLine.vehicles[0] != line.vehicles[0]
      || !("depot2" in stagedLine) || stagedLine.depot2 == null
      || !("tiles1" in stagedLine) || !("tiles2" in stagedLine)
      || !("doubleTrack" in stagedLine) || stagedLine.doubleTrack != 1
      || !AIRail.IsRailDepotTile(line.depot)
      || !AIRail.IsRailDepotTile(stagedLine.depot2)
      || line.depot == stagedLine.depot2) return false;
  local first = line.vehicles[0];
  if (!AIVehicle.IsValidVehicle(first)
      || AIOrder.GetOrderCount(first) != 2
      || !AIOrder.IsGotoStationOrder(first, 0)
      || !AIOrder.IsGotoStationOrder(first, 1)
      || (AIOrder.GetOrderFlags(first, 0) & AIOrder.OF_FULL_LOAD_ANY) == 0
      || (AIOrder.GetOrderFlags(first, 1) & AIOrder.OF_FULL_LOAD_ANY) != 0)
    return false;
  local wagon = (line.cargo in owner._catalog.wagonByCargo)
      ? owner._catalog.wagonByCargo[line.cargo] : null;
  if (wagon == null || line.wagons < 1) return false;
  local price = line.loco.price + line.wagons * wagon.price
      + OpexV163WagonsPrice(owner._catalog, line);
  if (price <= 0 || OpexAvailableCapital() < price + 50000) return false;
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)
      || AIStation.GetCargoWaiting(station, line.cargo)
          < AIVehicle.GetCapacity(first, line.cargo)) return false;

  local oldType = AIRail.GetCurrentRailType();
  local expectedType = AIRail.GetRailType(stagedLine.depot2);
  AIRail.SetCurrentRailType(expectedType);
  if (AIRail.GetCurrentRailType() != expectedType) {
    AIRail.SetCurrentRailType(oldType);
    return false;
  }
  local built = OpexBuildTrains(owner._catalog, line.cargo, line.kind,
      stagedLine.depot2, stagedLine.stationA2, stagedLine.stationB2,
      1, line.loco, line.wagons, line.platformLength, false,
      OpexV163Cargo2(line), OpexV163Wagons2(line));
  if (built.failed || built.built != 1 || built.vehicles.len() != 1) {
    OpexRollback(null, null, null, null, built.rollbackVehicles);
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowLog("skip", line, "reason=second_train_build");
    return false;
  }
  local second = built.vehicles[0];
  if (!AIVehicle.IsValidVehicle(second)
      || !AIVehicle.IsStoppedInDepot(second)
      || AIVehicle.GetLocation(second) != stagedLine.depot2
      || AIVehicle.GetCapacity(second, line.cargo) <= 0) {
    OpexRollback(null, null, null, null, built.rollbackVehicles);
    AIRail.SetCurrentRailType(oldType);
    return false;
  }
  stagedLine.vehicles.append(second);
  stagedLine.trains = 2;
  stagedLine.rawset("vehCount", 2);
  local diag = { step = "" };
  local guided = OpexV190Fix2BuildDirectional(stagedLine,
      line.depot, stagedLine.depot2, line.platformLength, diag);
  if (!guided) {
    /* FIX2 garde ses propres listes d'aiguillages, signaux et waypoints et
     * les annule en cas d'echec. Ce dernier controle refuse les ordres
     * residuels avant que la voie2 puisse etre demontee par le caller. */
    local restored = OpexV190Fix2RestoreOrders(stagedLine.vehicles);
    OpexRollback(null, null, null, null, built.rollbackVehicles);
    stagedLine.vehicles.pop();
    stagedLine.trains = 1;
    AIRail.SetCurrentRailType(oldType);
    OpexDoubleGrowLog("skip", line, "reason=directional_" + diag.step
        + " restored=" + (restored ? 1 : 0));
    return false;
  }
  /* Apres la conversion physique reussie, les deux rames doivent rester
   * repertoriees, meme si une action transitoire sur leurs ordres ou sur le
   * demarrage echoue : renvoyer false detruirait la voie2 alors que les
   * aiguillages du FIX2 sont deja actifs. La croissance ulterieure retente
   * ces operations avant tout autre achat. */
  local shared = AIOrder.ShareOrders(second, first);
  local source = AIOrder.ResolveOrderPosition(second, AIOrder.ORDER_CURRENT);
  local sourceOk = source == 0 || AIOrder.SkipToOrder(second, 0);
  local started = sourceOk && AIVehicle.StartStopVehicle(second);
  stagedLine.doubleGrowDirectional <- true;
  stagedLine.v190Directional <- true;
  stagedLine.v181Loop <- true;
  stagedLine.doubleGrowNextDate <- AIDate.GetCurrentDate() + 90;
  AIRail.SetCurrentRailType(oldType);
  OpexDoubleGrowLog("directional_ready", stagedLine,
      "depot2=" + stagedLine.depot2 + " shared_orders=" + (shared ? 1 : 0)
      + " started=" + (started ? 1 : 0) + " source_full=1");
  return true;
}
