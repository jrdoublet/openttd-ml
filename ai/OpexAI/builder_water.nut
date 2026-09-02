/* Liaison maritime passagers v1 : pas de canal, ecluse ni bouee. */
WATER_TOWN_POOL <- 12;
WATER_TOWN_MIN_DISTANCE <- 45;
WATER_MAX_SITE_PROBES <- 720;
WATER_MAX_WATER_TILES <- 8;
WATER_MAX_DEPOT_PROBES <- 96;
WATER_BFS_MARGIN <- 24;
WATER_BFS_MAX_NODES <- 12000;
WATER_CAPITAL_MARGIN <- 50000;
WATER_PROJECT_POOL <- 4;

function OpexWaterInMap(x, y)
{
  return x >= 0 && y >= 0 && x < AIMap.GetMapSizeX() && y < AIMap.GetMapSizeY();
}

/* Insertion stable : l'enumeration OpenTTD departage les populations egales. */
function OpexWaterSortedTowns(towns)
{
  local out = [];
  foreach (town in towns) {
    local pos = out.len();
    while (pos > 0 && out[pos - 1].pop < town.pop) pos--;
    out.insert(pos, town);
  }
  return out;
}
function OpexWaterTownServed(town, lines)
{
  if (lines == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "water") continue;
    if (AIMap.DistanceManhattan(town.tile, line.originA) < 15) return true;
    if (AIMap.DistanceManhattan(town.tile, line.originB) < 15) return true;
  }
  return false;
}

/* Une tuile navigable a une vraie arete navigable ; aucun AIWaterTile n'est utilise. */
function OpexWaterIsNavigable(tile)
{
  if (!AITile.IsWaterTile(tile)) return false;
  local x = AIMap.GetTileX(tile);
  local y = AIMap.GetTileY(tile);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (offset in offsets) {
    local nx = x + offset[0];
    local ny = y + offset[1];
    if (!OpexWaterInMap(nx, ny)) continue;
    local next = AIMap.GetTileIndex(nx, ny);
    if (AITile.IsWaterTile(next) && AIMarine.AreWaterTilesConnected(tile, next)) return true;
  }
  return false;
}

function OpexWaterAdjacentTiles(dock)
{
  local out = [];
  local x = AIMap.GetTileX(dock);
  local y = AIMap.GetTileY(dock);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (offset in offsets) {
    if (out.len() >= WATER_MAX_WATER_TILES) break;
    local nx = x + offset[0];
    local ny = y + offset[1];
    if (!OpexWaterInMap(nx, ny)) continue;
    local water = AIMap.GetTileIndex(nx, ny);
    if (OpexWaterIsNavigable(water)) out.append(water);
  }
  return out;
}

/* Acces reel : land et waterPart sont des tuiles de station. Les fronts sont toutes les cases eau
 * cardinales autour de waterPart, sauf land ; aucun test de connectivite ne relie station et eau. */
function OpexWaterFindDockAccess(land)
{
  if (!AIMarine.IsDockTile(land)) return null;
  local station = AIStation.GetStationID(land);
  if (!AIStation.IsValidStation(station)) return null;
  local x = AIMap.GetTileX(land);
  local y = AIMap.GetTileY(land);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (offset in offsets) {
    local px = x + offset[0];
    local py = y + offset[1];
    if (!OpexWaterInMap(px, py)) continue;
    local waterPart = AIMap.GetTileIndex(px, py);
    if (!AIMarine.IsDockTile(waterPart)) continue;
    if (AIStation.GetStationID(waterPart) != station) continue;
    local fronts = [];
    foreach (side in offsets) {
      local fx = px + side[0];
      local fy = py + side[1];
      if (!OpexWaterInMap(fx, fy) || (fx == x && fy == y)) continue;
      local front = AIMap.GetTileIndex(fx, fy);
      if (!AITile.IsWaterTile(front) ||
          !AITile.HasTransportType(front, AITile.TRANSPORT_WATER)) continue;
      local navigable = false;
      foreach (near in offsets) {
        local qx = fx + near[0];
        local qy = fy + near[1];
        if (!OpexWaterInMap(qx, qy) || (qx == px && qy == py)) continue;
        local q = AIMap.GetTileIndex(qx, qy);
        if (AITile.IsWaterTile(q) && AIMarine.AreWaterTilesConnected(front, q)) {
          navigable = true;
          break;
        }
      }
      if (!navigable) continue;
      local duplicate = false;
      foreach (known in fronts) if (known == front) duplicate = true;
      if (!duplicate) fronts.append(front);
    }
    if (fronts.len() > 0) return { waterPart = waterPart, fronts = fronts };
  }
  return null;
}

/* Les probes sont partagees equitablement : une cote sans dock ne mange pas tout le budget. */
function OpexWaterFindSite(town, probes)
{
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_DOCK);
  local allowance = probes.townsLeft > 0
      ? (probes.left + probes.townsLeft - 1) / probes.townsLeft : 0;
  probes.townsLeft--;
  local used = 0;
  local tx = AIMap.GetTileX(town.tile);
  local ty = AIMap.GetTileY(town.tile);
  for (local r = 0; r <= coverage; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local x = tx + dx;
        local y = ty + dy;
        if (!OpexWaterInMap(x, y)) continue;
        local dock = AIMap.GetTileIndex(x, y);
        if (!AITile.IsCoastTile(dock)) continue;
        if (AIMap.DistanceManhattan(town.tile, dock) > coverage) continue;
        local waterTiles = OpexWaterAdjacentTiles(dock);
        if (waterTiles.len() == 0) continue;
        if (used >= allowance || probes.left <= 0) return null;
        local ok = false;
        { local probe = AITestMode(); ok = AIMarine.BuildDock(dock, AIStation.STATION_NEW); }
        used++;
        probes.left--;
        if (ok) return { town = town, dock = dock, waterTiles = waterTiles };
      }
    }
  }
  return null;
}

function OpexWaterContains(tiles, tile)
{
  foreach (entry in tiles) if (entry == tile) return true;
  return false;
}

/* La portee est filtree avant le BFS ; le depot ne sera sonde qu apres les docks reels. */
function OpexWaterHasRange(catalog, orderDistance)
{
  foreach (ship in catalog.ships) {
    if (ship.maxOrderDistance <= 0 || orderDistance <= ship.maxOrderDistance) return true;
  }
  return false;
}

/* BFS 4 voisins avec rectangle x/y explicite. */
function OpexWaterFindConnection(siteA, siteB)
{
  local ax = AIMap.GetTileX(siteA.dock);
  local ay = AIMap.GetTileY(siteA.dock);
  local bx = AIMap.GetTileX(siteB.dock);
  local by = AIMap.GetTileY(siteB.dock);
  local minX = max(0, min(ax, bx) - WATER_BFS_MARGIN);
  local minY = max(0, min(ay, by) - WATER_BFS_MARGIN);
  local maxX = min(AIMap.GetMapSizeX() - 1, max(ax, bx) + WATER_BFS_MARGIN);
  local maxY = min(AIMap.GetMapSizeY() - 1, max(ay, by) + WATER_BFS_MARGIN);
  local queue = [];
  local seen = {};
  foreach (water in siteA.waterTiles) { queue.append(water); seen.rawset(water, true); }
  local head = 0;
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < queue.len() && head < WATER_BFS_MAX_NODES) {
    local current = queue[head++];
    if (OpexWaterContains(siteB.waterTiles, current)) return true;
    local x = AIMap.GetTileX(current);
    local y = AIMap.GetTileY(current);
    foreach (offset in offsets) {
      local nx = x + offset[0];
      local ny = y + offset[1];
      if (nx < minX || nx > maxX || ny < minY || ny > maxY) continue;
      local next = AIMap.GetTileIndex(nx, ny);
      if (!AITile.IsWaterTile(next)) continue;
      if (!AIMarine.AreWaterTilesConnected(current, next)) continue;
      if (!(next in seen)) { seen.rawset(next, true); queue.append(next); }
    }
  }
  return false;
}

/* Le depot est cherche apres la pose des docks, dans le composant deja prouve. AITestMode voit
 * donc les empreintes effectivement occupees par les docks. */
function OpexWaterFindDepot(siteA, siteB)
{
  local ax = AIMap.GetTileX(siteA.dock);
  local ay = AIMap.GetTileY(siteA.dock);
  local bx = AIMap.GetTileX(siteB.dock);
  local by = AIMap.GetTileY(siteB.dock);
  local minX = max(0, min(ax, bx) - WATER_BFS_MARGIN);
  local minY = max(0, min(ay, by) - WATER_BFS_MARGIN);
  local maxX = min(AIMap.GetMapSizeX() - 1, max(ax, bx) + WATER_BFS_MARGIN);
  local maxY = min(AIMap.GetMapSizeY() - 1, max(ay, by) + WATER_BFS_MARGIN);
  local queue = [];
  local seen = {};
  foreach (water in siteA.waterTiles) { queue.append(water); seen.rawset(water, true); }
  local head = 0;
  local probes = 0;
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < queue.len() && head < WATER_BFS_MAX_NODES && probes < WATER_MAX_DEPOT_PROBES) {
    local current = queue[head++];
    local x = AIMap.GetTileX(current);
    local y = AIMap.GetTileY(current);
    foreach (offset in offsets) {
      if (probes >= WATER_MAX_DEPOT_PROBES) break;
      local nx = x + offset[0];
      local ny = y + offset[1];
      if (nx < minX || nx > maxX || ny < minY || ny > maxY) continue;
      local next = AIMap.GetTileIndex(nx, ny);
      if (!AITile.IsWaterTile(next) || !AIMarine.AreWaterTilesConnected(current, next)) continue;
      local depotOk = false;
      { local probe = AITestMode(); depotOk = AIMarine.BuildWaterDepot(current, next); }
      probes++;
      if (depotOk) return { tile = current, front = next };
      if (!(next in seen)) { seen.rawset(next, true); queue.append(next); }
    }
  }
  return null;
}

/* Economie maritime avant construction. La capacite du catalogue est une approximation de refit,
 * comme pour la route ; le constructeur relit la capacite exacte dans le depot. */
function OpexWaterEconomics(catalog, distance, orderDistance, monthlyPax)
{
  local best = null;
  foreach (ship in catalog.ships) {
    if (ship.capacity <= 0 || ship.speed <= 0) continue;
    if (ship.maxOrderDistance > 0 && orderDistance > ship.maxOrderDistance) continue;
    local effectiveSpeed = ship.speed / 2;
    if (effectiveSpeed < 1) effectiveSpeed = 1;
    local oneWayDays = (distance * 1000) / (36 * effectiveSpeed);
    if (oneWayDays < 1) oneWayDays = 1;
    local roundTripDays = 2 * oneWayDays;
    local headwayDays = roundTripDays;
    local tripsPerMonth = 30 / oneWayDays;
    if (tripsPerMonth < 1) tripsPerMonth = 1;
    local stationRating = OpexStationRatingForHeadway(headwayDays);
    local offered = (monthlyPax * stationRating) / 100;
    local monthlyCapacity = ship.capacity * tripsPerMonth;
    local carried = offered < monthlyCapacity ? offered : monthlyCapacity;
    local income = AICargo.GetCargoIncome(catalog.paxCargo, distance, oneWayDays);
    local revenueAnnual = 12 * carried * income;
    local infraCapital = 2 * catalog.costDock + catalog.costWaterDepot;
    local capital = infraCapital + ship.price;
    local runningAnnual = ship.runningCost;
    local amortAnnual = infraCapital / INFRA_LIFE_YEARS + ship.price / 20;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    local roi = (profitAnnual > 0 && capital > 0)
        ? (profitAnnual * 1000) / capital : 0;
    local economics = {
      ship = ship, oneWayDays = oneWayDays, roundTripDays = roundTripDays,
      headwayDays = headwayDays, stationRating = stationRating,
      carried = carried,
      revenueAnnual = revenueAnnual, runningAnnual = runningAnnual,
      amortAnnual = amortAnnual, profitAnnual = profitAnnual,
      capital = capital, roi = roi,
    };
    if (best == null || economics.roi > best.roi ||
        (economics.roi == best.roi && economics.profitAnnual > best.profitAnnual)) {
      best = economics;
    }
  }
  return best;
}

function OpexWaterPlans(catalog, lines = null, projects = null)
{
  if (catalog.ships.len() == 0 || catalog.paxCargo < 0) return null;
  local towns = OpexWaterSortedTowns(catalog.towns);
  local limit = towns.len() < WATER_TOWN_POOL ? towns.len() : WATER_TOWN_POOL;
  local sites = [];
  local probes = { left = WATER_MAX_SITE_PROBES, townsLeft = limit };
  for (local i = 0; i < limit; i++) {
    if (OpexWaterTownServed(towns[i], lines)) continue;
    local site = OpexWaterFindSite(towns[i], probes);
    if (site != null) sites.append(site);
  }
  /* La connectivite maritime est couteuse. On classe d'abord toutes les paires sur leur ROI,
   * puis on ne lance le BFS que sur un petit bassin economique. */
  local ranked = [];
  for (local a = 0; a < sites.len(); a++) {
    for (local b = a + 1; b < sites.len(); b++) {
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
      if (distance < WATER_TOWN_MIN_DISTANCE) continue;
      local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_WATER,
                                                      sites[a].dock, sites[b].dock);
      if (orderDistance < 0 || !OpexWaterHasRange(catalog, orderDistance)) continue;
      local monthlyPax = ((sites[a].town.pop + sites[b].town.pop) * 22) / 100;
      local economics = OpexWaterEconomics(catalog, distance, orderDistance, monthlyPax);
      if (economics == null || economics.profitAnnual <= 0) continue;
      local plan = { siteA = sites[a], siteB = sites[b], distance = distance,
                     orderDistance = orderDistance, economics = economics };
      local pos = ranked.len();
      while (pos > 0 && (ranked[pos - 1].economics.roi < economics.roi ||
             (ranked[pos - 1].economics.roi == economics.roi &&
              ranked[pos - 1].economics.profitAnnual < economics.profitAnnual))) pos--;
      ranked.insert(pos, plan);
      if (ranked.len() > WATER_PROJECT_POOL) ranked.pop();
    }
  }
  local best = null;
  foreach (plan in ranked) {
    if (!OpexWaterFindConnection(plan.siteA, plan.siteB)) continue;
    if (projects != null) projects.append(plan);
    if (best == null) best = plan;
  }
  return best;
}

function OpexWaterRollback(dockA, dockB, depot, ship)
{
  if (ship != null && AIVehicle.IsValidVehicle(ship)) AIVehicle.SellVehicle(ship);
  if (depot != null && AIMarine.IsWaterDepotTile(depot)) AIMarine.RemoveWaterDepot(depot);
  if (dockB != null && AIMarine.IsDockTile(dockB)) AIMarine.RemoveDock(dockB);
  if (dockA != null && AIMarine.IsDockTile(dockA)) AIMarine.RemoveDock(dockA);
}

/* Chaque retour ferme le budget ouvert et retourne une table. */
function OpexBuildWaterRoute(catalog, budget, plan)
{
  local result = { ok = false, reason = "", opcodes = 0, error = 0, dockA = null,
                   dockB = null, stationA = null, stationB = null, depot = null, vehicle = null };
  local dockA = null;
  local dockB = null;
  local depot = null;
  local ship = null;
  budget.begin();
  local okA = AIMarine.BuildDock(plan.siteA.dock, AIStation.STATION_NEW);
  local errorA = okA ? 0 : AIError.GetLastError();
  if (okA && AIMarine.IsDockTile(plan.siteA.dock)) dockA = plan.siteA.dock;
  if (dockA == null) {
    result.error = errorA; result.opcodes += budget.end("build_docks"); result.reason = "ADOCK";
    return result;
  }
  local okB = AIMarine.BuildDock(plan.siteB.dock, AIStation.STATION_NEW);
  local errorB = okB ? 0 : AIError.GetLastError();
  if (okB && AIMarine.IsDockTile(plan.siteB.dock)) dockB = plan.siteB.dock;
  result.opcodes += budget.end("build_docks");
  if (dockB == null) {
    result.error = errorB; OpexWaterRollback(dockA, null, null, null); result.reason = "BDOCK";
    return result;
  }
  local stationA = AIStation.GetStationID(dockA);
  local stationB = AIStation.GetStationID(dockB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) || stationA == stationB) {
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "STATION"; return result;
  }

  local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_WATER, dockA, dockB);
  if (orderDistance < 0 || !OpexWaterHasRange(catalog, orderDistance)) {
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "RANGE"; return result;
  }

  /* Les fronts et leur composant sont relus apres les constructions reelles. */
  budget.begin();
  local accessA = OpexWaterFindDockAccess(dockA);
  local accessB = OpexWaterFindDockAccess(dockB);
  if (accessA == null || accessB == null) {
    result.opcodes += budget.end("build_water_depot");
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "NOWATER"; return result;
  }
  local realA = { dock = dockA, waterTiles = accessA.fronts };
  local realB = { dock = dockB, waterTiles = accessB.fronts };
  if (!OpexWaterFindConnection(realA, realB)) {
    result.opcodes += budget.end("build_water_depot");
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "NOWATER"; return result;
  }
  local depotPlan = OpexWaterFindDepot(realA, realB);
  if (depotPlan == null) {
    result.opcodes += budget.end("build_water_depot");
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "NOWATER"; return result;
  }
  local depotOk = AIMarine.BuildWaterDepot(depotPlan.tile, depotPlan.front);
  local depotError = depotOk ? 0 : AIError.GetLastError();
  if (depotOk && AIMarine.IsWaterDepotTile(depotPlan.tile)) depot = depotPlan.tile;
  result.opcodes += budget.end("build_water_depot");
  if (depot == null) {
    result.error = depotError; OpexWaterRollback(dockA, dockB, null, null); result.reason = "DEPOT";
    return result;
  }

  budget.begin();
  local chosen = null;
  local chosenCapacity = 0;
  foreach (candidate in catalog.ships) {
    if (candidate.maxOrderDistance > 0 && orderDistance > candidate.maxOrderDistance) continue;
    local capacity = AIVehicle.GetBuildWithRefitCapacity(depot, candidate.id, catalog.paxCargo);
    if (capacity > chosenCapacity ||
        (capacity == chosenCapacity && capacity > 0 &&
         (chosen == null || candidate.speed > chosen.speed ||
          (candidate.speed == chosen.speed && candidate.price < chosen.price)))) {
      chosen = candidate;
      chosenCapacity = capacity;
    }
  }
  if (chosen == null || chosenCapacity <= 0) {
    result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, null); result.reason = "REFIT"; return result;
  }
  ship = AIVehicle.BuildVehicleWithRefit(depot, chosen.id, catalog.paxCargo);
  local shipError = AIError.GetLastError();
  if (!AIVehicle.IsValidVehicle(ship)) {
    result.error = shipError; result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, null); result.reason = "SHIP"; return result;
  }
  if (AIVehicle.GetCapacity(ship, catalog.paxCargo) <= 0) {
    result.opcodes += budget.end("build_ships"); OpexWaterRollback(dockA, dockB, depot, ship);
    result.reason = "PAX"; return result;
  }
  local maxOrderDistance = AIEngine.GetMaximumOrderDistance(chosen.id);
  if (maxOrderDistance > 0 && orderDistance > maxOrderDistance) {
    result.opcodes += budget.end("build_ships"); OpexWaterRollback(dockA, dockB, depot, ship);
    result.reason = "RANGE"; return result;
  }
  local orderA = AIOrder.AppendOrder(ship, dockA, AIOrder.OF_NONE);
  local errorOrderA = orderA ? 0 : AIError.GetLastError();
  local orderB = AIOrder.AppendOrder(ship, dockB, AIOrder.OF_NONE);
  local errorOrderB = orderB ? 0 : AIError.GetLastError();
  if (!orderA || !orderB || AIOrder.GetOrderCount(ship) != 2) {
    result.error = !orderA ? errorOrderA : errorOrderB; result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, ship); result.reason = "ORDERS"; return result;
  }
  local started = AIVehicle.StartStopVehicle(ship);
  local startError = started ? 0 : AIError.GetLastError();
  if (!started) {
    result.error = startError; result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, ship); result.reason = "START"; return result;
  }
  result.opcodes += budget.end("build_ships");
  result.ok = true; result.reason = "OK"; result.dockA = dockA; result.dockB = dockB;
  result.stationA = stationA; result.stationB = stationB; result.depot = depot; result.vehicle = ship;
  return result;
}
