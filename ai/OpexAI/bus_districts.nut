/* ROAD1Y-B2. Cache reconstructible : aucune reservation speculative ne
 * survit au chantier. La carte est l'autorite, y compris apres Load. */
function OpexBusDistrictOccupied(townId)
{
  local out = [];
  local stations = AIStationList(AIStation.STATION_BUS_STOP);
  for (local id = stations.Begin(); !stations.IsEnd(); id = stations.Next()) {
    if (AIStation.GetNearestTown(id) != townId) continue;
    local tiles = AITileList_StationType(id, AIStation.STATION_BUS_STOP);
    for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next())
      out.append(tile);
  }
  return out;
}

function OpexBusDistrictAxis(tile)
{
  if (!AIRoad.IsRoadTile(tile) || AITile.IsStationTile(tile)
      || AIRoad.IsRoadDepotTile(tile)) return 0;
  local width = AIMap.GetMapSizeX();
  local xConnected = false;
  local yConnected = false;
  foreach (offset in [1, -1, width, -width]) {
    local neighbour = tile + offset;
    if (!AIMap.IsValidTile(neighbour) || AIMap.DistanceManhattan(tile, neighbour) != 1) continue;
    if (!AIRoad.AreRoadTilesConnected(tile, neighbour)
        && !AIRoad.AreRoadTilesConnected(neighbour, tile)) continue;
    if (offset == 1 || offset == -1) xConnected = true;
    else yConnected = true;
  }
  if (xConnected == yConnected) return 0; // virage, carrefour ou route isolee
  return xConnected ? 1 : width;
}

function OpexBusDistrictSortDistance(a, b)
{
  if (a.d < b.d) return -1;
  if (a.d > b.d) return 1;
  return 0;
}

/* Reserve the geometry of a neighbourhood before excluding the next one.
 * Test mode does not create a StationID: real joins are rechecked later. */
function OpexBusDistrictJoinedPreflight(tile, axis, excluded, coverage)
{
  local out = [];
  if (ROAD1Y_EXTRA_STOPS <= 0) return out;
  foreach (offset in [axis, -axis]) {
    if (out.len() >= ROAD1Y_EXTRA_STOPS) break;
    local neighbour = tile + offset;
    if (!AIMap.IsValidTile(neighbour) || AIMap.DistanceManhattan(tile, neighbour) != 1
        || OpexBusDistrictAxis(neighbour) != axis
        || OpexRoad100CatchmentOverlaps(neighbour, excluded, coverage)) continue;
    local ok = false;
    { local test = AITestMode();
      ok = AIRoad.BuildDriveThroughRoadStation(neighbour, neighbour + axis,
          AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
    if (ok) out.append(neighbour);
  }
  return out;
}

function OpexBusDistrictSites(town, cargo, coverage)
{
  local today = AIDate.GetCurrentDate();
  local occupied = OpexBusDistrictOccupied(town.id);
  local entry = town.id in ROAD_BUS_SITE_CACHE ? ROAD_BUS_SITE_CACHE[town.id] : null;
  if (entry == null || !("sites" in entry) || today - entry.date >= 90) {
    local mark = OpexOpsMeasureBegin();
    local radius = sqrt(AITown.GetHouseCount(town.id)).tointeger();
    if (radius < 4) radius = 4;
    if (radius > ROAD_TOWN_SEARCH_RADIUS) radius = ROAD_TOWN_SEARCH_RADIUS;
    local cx = AIMap.GetTileX(town.tile), cy = AIMap.GetTileY(town.tile);
    local x0 = cx - radius, y0 = cy - radius;
    local x1 = cx + radius, y1 = cy + radius;
    if (x0 < 1) x0 = 1;
    if (y0 < 1) y0 = 1;
    if (x1 >= AIMap.GetMapSizeX() - 1) x1 = AIMap.GetMapSizeX() - 2;
    if (y1 >= AIMap.GetMapSizeY() - 1) y1 = AIMap.GetMapSizeY() - 2;
    local corner = AIMap.GetTileIndex(x0, y0);
    // Meme unite (tuiles productrices), aucun recouvrement de sommes rad=3.
    local producers = AITile.GetCargoProduction(corner, cargo, x1-x0+1, y1-y0+1, 0);
    local tiles = AITileList();
    tiles.AddRectangle(corner, AIMap.GetTileIndex(x1, y1));
    tiles.Valuate(AIRoad.IsRoadTile);
    tiles.KeepValue(1);
    tiles.Valuate(AITile.GetClosestTown);
    tiles.KeepValue(town.id);
    tiles.Valuate(AITile.GetCargoAcceptance, cargo, 1, 1, coverage);
    tiles.KeepAboveValue(7);
    tiles.Valuate(AITile.GetCargoProduction, cargo, 1, 1, coverage);
    tiles.KeepAboveValue(0);
    tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
    local sites = [], excluded = [];
    foreach (tile in occupied) excluded.append(tile);
    local tested = 0, corners = 0, overlap = 0;
    for (local tile = tiles.Begin(); !tiles.IsEnd() && sites.len() < 12; tile = tiles.Next()) {
      if (tested >= 32 || OpexOpsMeasureEnd(mark) >= 120000) break;
      if (OpexRoad100CatchmentOverlaps(tile, excluded, coverage)) { overlap++; continue; }
      local axis = OpexBusDistrictAxis(tile);
      if (axis == 0) { corners++; continue; }
      local front = tile + axis, back = tile - axis;
      if (!AIMap.IsValidTile(front) || !AIMap.IsValidTile(back)
          || AIMap.DistanceManhattan(tile, front) != 1
          || AIMap.DistanceManhattan(tile, back) != 1) continue;
      local ok = false;
      tested++;
      { local test = AITestMode();
        ok = AIRoad.BuildDriveThroughRoadStation(tile, front,
            AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
      if (!ok) continue;
      local joined = OpexBusDistrictJoinedPreflight(tile, axis, excluded, coverage);
      sites.append({ tile = tile, front = front, front2 = back,
          driveThrough = true, townId = town.id, prod = tiles.GetValue(tile),
          accept = 8, score = tiles.GetValue(tile), claimed = false, joined = joined });
      foreach (plannedTile in joined) excluded.append(plannedTile);
      excluded.append(tile);
    }
    // Repli en baie : utilise le chercheur existant, seulement sans site DT.
    if (sites.len() == 0) {
      local hunt = OpexRoadSites(town.tile, town.id, cargo, AIRoad.ROADVEHTYPE_BUS,
          coverage, true, radius, town.tile, true, occupied);
      foreach (site in hunt.sites) {
        if (sites.len() >= 12) break;
        if (OpexRoad100CatchmentOverlaps(site.tile, excluded, coverage)) continue;
        site.prod <- AITile.GetCargoProduction(site.tile, cargo, 1, 1, coverage);
        if (site.prod <= 0) continue;
        site.driveThrough <- false;
        site.townId <- town.id;
        site.claimed <- false;
        sites.append(site); excluded.append(site.tile);
      }
    }
    entry = { date = today, sites = sites, producers = producers };
    ROAD_BUS_SITE_CACHE[town.id] <- entry;
    if (DECISION_LOG) OpexDecide("BUS_DISTRICT_SCAN", "town=" + town.id
        + " tiles=" + tiles.Count() + " tests=" + tested + " corners=" + corners
        + " overlap=" + overlap + " sites=" + sites.len() + " producers=" + producers
        + " ops=" + OpexOpsMeasureEnd(mark));
  }
  local monthly = AITown.GetLastMonthProduction(town.id, cargo);
  local out = [];
  foreach (site in entry.sites) {
    site.claimed = OpexRoad100CatchmentOverlaps(site.tile, occupied, coverage);
    if (site.claimed || AITile.IsStationTile(site.tile) || entry.producers <= 0) continue;
    local captured = site.prod < entry.producers ? site.prod : entry.producers;
    site.monthly <- monthly * captured / entry.producers;
    // La note est appliquee UNE fois par OpexRoadLineEconomics (headway).
    site.value <- site.monthly;
    if (site.monthly > 0) out.append(site);
  }
  return out;
}

/* ROAD1Y : uniquement des routes deja raccordees, aucun terrassement ni
 * branche morte. Les ordres existants vers A/B designent leur StationID :
 * les quais joints sont donc accessibles sans dupliquer les ordres. */
function OpexRoad1yBuildExtraStop(catalog, line, side, tiles)
{
  local out = { ok = false, tile = -1, reason = "NO_SITE" };
  local root = side == 0 ? line.stationA : line.stationB;
  if (!AIRoad.IsRoadStationTile(root) || !AICompany.IsMine(AITile.GetOwner(root))) {
    out.reason = "ROOT"; return out;
  }
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local id = AIStation.GetStationID(root);
  local rootFront = AIRoad.GetRoadStationFrontTile(root);
  local passenger = AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS);
  local vehType = passenger ? AIRoad.ROADVEHTYPE_BUS : AIRoad.ROADVEHTYPE_TRUCK;
  local price = AIRoad.GetBuildCost(catalog.roadType,
      passenger ? AIRoad.BT_BUS_STOP : AIRoad.BT_TRUCK_STOP);
  if (price <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + 50000) {
    out.reason = "CASH"; return out;
  }
  local mark = OpexOpsMeasureBegin();
  local anchors = [root];
  foreach (tile in tiles) anchors.append(tile);
  local offsets = [1, -1, AIMap.GetMapSizeX(), -AIMap.GetMapSizeX()];
  local seen = {};
  local tested = 0;
  // Au plus 4 ancres x 4 voisins ; quatre preflights, BFS 32 noeuds.
  foreach (anchor in anchors) {
    foreach (offset in offsets) {
      if (OpexOpsMeasureEnd(mark) >= 24000 || tested >= 4) {
        out.reason = "BUDGET"; return out;
      }
      local tile = anchor + offset;
      if (!AIMap.IsValidTile(tile) || AIMap.DistanceManhattan(anchor, tile) != 1
          || tile in seen) continue;
      seen[tile] <- true;
      if (!AIRoad.IsRoadTile(tile) || AITile.IsStationTile(tile)
          || AIRoad.IsRoadDepotTile(tile)) continue;
      if (passenger && ROAD1Y_PAX_SITES) {
        local neighbours = OpexRoadOurBusTiles();
        local otherDistrict = [];
        foreach (existing in neighbours) {
          if (AIStation.GetStationID(existing) != id) otherDistrict.append(existing);
        }
        if (OpexRoad100CatchmentOverlaps(tile, otherDistrict,
            AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP))) continue;
      }
      foreach (axis in [1, AIMap.GetMapSizeX()]) {
        local front = tile + axis;
        local back = tile - axis;
        // Ne pas convertir un carrefour : le quai traversant supprimerait
        // l'acces lateral d'un ancien terminus ou d'une autre route.
        local lateral = axis == 1 ? AIMap.GetMapSizeX() : 1;
        local crossing = false;
        foreach (neighbour in [tile + lateral, tile - lateral]) {
          if (AIMap.IsValidTile(neighbour) && AIMap.DistanceManhattan(tile, neighbour) == 1
              && (AIRoad.AreRoadTilesConnected(tile, neighbour)
                  || AIRoad.AreRoadTilesConnected(neighbour, tile))) crossing = true;
        }
        if (crossing) continue;
        if (!AIMap.IsValidTile(front) || !AIMap.IsValidTile(back)
            || AIMap.DistanceManhattan(tile, front) != 1
            || AIMap.DistanceManhattan(tile, back) != 1
            || !AIRoad.AreRoadTilesConnected(tile, front)
            || !AIRoad.AreRoadTilesConnected(front, tile)
            || !AIRoad.AreRoadTilesConnected(tile, back)
            || !AIRoad.AreRoadTilesConnected(back, tile)) continue;
        if (OpexOpsMeasureEnd(mark) >= 24000 || tested >= 4) {
          out.reason = "BUDGET"; return out;
        }
        tested++;
        if (OpexRoadBfsPath(front, rootFront, 32) == null
            || OpexRoadBfsPath(rootFront, front, 32) == null) continue;
        if (OpexOpsMeasureEnd(mark) >= 24000) { out.reason = "BUDGET"; return out; }
        local canBuild = false;
        local cost = 0;
        { local accounting = AIAccounting();
          local test = AITestMode();
          canBuild = AIRoad.BuildDriveThroughRoadStation(tile, front, vehType, id);
          cost = accounting.GetCosts(); }
        if (!canBuild) continue;
        local cashReserve = (ROAD1Y_FLEET_UNLOCK & 1) != 0 ? 5000 : 50000;
        if (cost < 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cost + cashReserve) {
          out.reason = "CASH"; return out;
        }
        local built = AIRoad.BuildDriveThroughRoadStation(tile, front, vehType, id);
        local ours = AIRoad.IsRoadStationTile(tile) && AICompany.IsMine(AITile.GetOwner(tile));
        if (built && ours && AIStation.GetStationID(tile) == id
            && AIRoad.AreRoadTilesConnected(root, rootFront)
            && AIRoad.AreRoadTilesConnected(rootFront, root)
            && AIRoad.AreRoadTilesConnected(tile, front)
            && AIRoad.AreRoadTilesConnected(front, tile)
            && AIRoad.AreRoadTilesConnected(tile, back)
            && AIRoad.AreRoadTilesConnected(back, tile)) {
          out.ok = true; out.tile = tile; out.reason = "OK";
        } else {
          out.reason = "BUILD";
          if (ours && !AIRoad.RemoveRoadStation(tile)) {
            out.reason = "ROLLBACK"; out.tile = tile;
          }
        }
        return out; // Une seule commande effective par extremite.
      }
    }
  }
  return out;
}

/* M1/M2 : un seul decompte physique, sans sommer PORTFOLIO et ROAD1Y.
 * Reconstruit aussi les tuiles absentes d'une ancienne projection Save. */
function OpexRoad1yReconcileExtraStops(line)
{
  line.road1yExtraStops <- [[], []];
  for (local side = 0; side < 2; side++) {
    local root = side == 0 ? line.stationA : line.stationB;
    if (!AIRoad.IsRoadStationTile(root) || !AICompany.IsMine(AITile.GetOwner(root))) continue;
    local kind = AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)
        ? AIStation.STATION_BUS_STOP : AIStation.STATION_TRUCK_STOP;
    local tiles = AITileList_StationType(AIStation.GetStationID(root), kind);
    for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next()) {
      if (("road1yExtraPending" in line) && tile == line.road1yExtraPending) continue;
      if (tile != root) line.road1yExtraStops[side].append(tile);
    }
    local count = 1 + line.road1yExtraStops[side].len();
    if (side == 0) line.nStopsA = count;
    else line.nStopsB = count;
  }
}

function OpexRoad1yCleanupExtraStop(line)
{
  if (!("road1yExtraPending" in line) || line.road1yExtraPending < 0) return;
  local tile = line.road1yExtraPending;
  if (!AIRoad.IsRoadStationTile(tile) || !AICompany.IsMine(AITile.GetOwner(tile))
      || AIRoad.RemoveRoadStation(tile)) line.road1yExtraPending = -1;
}

function OpexRoad1yExtraStops(catalog, line, have, capacity, waitingA, waitingB, moving, month)
{
  OpexRoad1yReconcileExtraStops(line);
  if (("road1yExtraPending" in line) && line.road1yExtraPending >= 0) return;
  if (ROAD1Y_EXTRA_STOPS <= 0 || capacity <= 0 || moving <= 0) return;
  if ((ROAD1Y_BUS_FIXES & 1) != 0
      && !AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)) return;
  if (("road1yExtraMonth" in line) && line.road1yExtraMonth == month) return;
  local stops = line.nStopsA < line.nStopsB ? line.nStopsA : line.nStopsB;
  local cap = OpexRoadPhysicalVehicleCap(line.nStopsA, line.nStopsB);
  // ROAD1Y_FLEET remplace le cap historique dans son chemin de refleet.
  if (ROAD1Y_FLEET > 0) cap = ROAD1Y_FLEET * stops;
  local waiting = waitingA > waitingB ? waitingA : waitingB;
  if (have < cap || waiting <= cap * capacity) return;
  line.road1yExtraMonth <- month; // Echecs et manque de caisse dedupliques aussi.
  if (!("road1yExtraStops" in line)) line.road1yExtraStops <- [[], []];
  // Les deux extremites limitantes sont concernees, meme un puits de fret.
  for (local side = 0; side < 2; side++) {
    local count = side == 0 ? line.nStopsA : line.nStopsB;
    local tiles = line.road1yExtraStops[side];
    if (count > stops || count >= 1 + ROAD1Y_EXTRA_STOPS) continue;
    local result = OpexRoad1yBuildExtraStop(catalog, line, side, tiles);
    if (result.reason == "ROLLBACK") line.road1yExtraPending <- result.tile;
    if (result.ok) {
      tiles.append(result.tile);
      if (side == 0) line.nStopsA++;
      else line.nStopsB++;
      OpexAir0310InvalidateSiteValidity();
    }
    if (DECISION_LOG) OpexDecide("ROAD1Y_EXTRA_STOPS",
        "phase=build line=" + line.lineId + " side=" + side
        + " ok=" + result.ok + " reason=" + result.reason + " tile=" + result.tile
        + " stops_a=" + line.nStopsA + " stops_b=" + line.nStopsB);
    if (result.reason == "ROLLBACK") break;
  }
}

/* --- ROAD1Y_MAIL_ON_PAX : ligne MAIL fille sur paire de villes bus PAX rentable --- */

function OpexRoad1yOurTruckTiles(ai, townId)
{
  local tiles = [];
  foreach (line in ai._lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    local isPax = ("kind" in line) && line.kind == "pax";
    if (isPax) continue;
    local ends = [line.stationA, line.stationB];
    foreach (t in ends) {
      if (typeof t != "integer" || !AIMap.IsValidTile(t)) continue;
      if (!AIRoad.IsRoadStationTile(t) || !AICompany.IsMine(AITile.GetOwner(t))) continue;
      if (AITile.GetClosestTown(t) == townId) tiles.append(t);
    }
  }
  return tiles;
}

function OpexRoad1yFindMailSite(ai, catalog, townId, busTile, mailCargo)
{
  if (!AITown.IsValidTown(townId) || !AIMap.IsValidTile(busTile)
      || !AIRoad.IsRoadStationTile(busTile)) return null;
  local busFront = AIRoad.GetRoadStationFrontTile(busTile);
  if (!AIMap.IsValidTile(busFront)) return null;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
  local used = OpexRoad1yOurTruckTiles(ai, townId);
  local center = AITown.GetLocation(townId);
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local bx = AIMap.GetTileX(busTile);
  local by = AIMap.GetTileY(busTile);
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local cands = [];
  for (local pass = 0; pass < 2; pass++) {
    local ox = pass == 0 ? cx : bx;
    local oy = pass == 0 ? cy : by;
    local rad = pass == 0 ? 6 : 4;
    for (local dx = -rad; dx <= rad; dx++) {
      for (local dy = -rad; dy <= rad; dy++) {
        local x = ox + dx;
        local y = oy + dy;
        if (x <= 0 || y <= 0 || x >= mapX - 1 || y >= mapY - 1) continue;
        if (pass == 1) {
          local cdx = x - cx; if (cdx < 0) cdx = -cdx;
          local cdy = y - cy; if (cdy < 0) cdy = -cdy;
          if (cdx <= 6 && cdy <= 6) continue;
        }
        local tile = AIMap.GetTileIndex(x, y);
        if (tile == busTile || !AIRoad.IsRoadTile(tile)
            || AIRoad.IsRoadDepotTile(tile) || AIRoad.IsRoadStationTile(tile)
            || AITile.IsStationTile(tile)) continue;
        if (AITile.GetClosestTown(tile) != townId) continue;
        if (OpexRoad100CatchmentOverlaps(tile, used, coverage)) continue;
        local axis = OpexBusDistrictAxis(tile);
        if (axis == 0) continue;
        local front = tile + axis;
        local back = tile - axis;
        if (!AIMap.IsValidTile(front) || !AIMap.IsValidTile(back)) continue;
        local prod = AITile.GetCargoProduction(tile, mailCargo, 1, 1, coverage);
        if (prod <= 0) continue;
        local acc = AITile.GetCargoAcceptance(tile, mailCargo, 1, 1, coverage);
        if (acc < 8) continue;
        local score = prod * 100 + acc - AIMap.DistanceManhattan(tile, center);
        local item = { tile = tile, front = front, back = back, prod = prod, acc = acc, score = score };
        local pos = cands.len();
        cands.append(item);
        while (pos > 0 && cands[pos - 1].score < item.score) {
          cands[pos] = cands[pos - 1];
          pos--;
        }
        cands[pos] = item;
        if (cands.len() > 4) cands.pop();
      }
    }
  }
  foreach (c in cands) {
    if (OpexRoadBfsPath(c.front, busFront, 48) == null
        || OpexRoadBfsPath(busFront, c.front, 48) == null) continue;
    local canBuild = false;
    { local test = AITestMode();
      canBuild = AIRoad.BuildDriveThroughRoadStation(c.tile, c.front,
          AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW); }
    if (canBuild) return c;
  }
  return null;
}

function OpexRoad1yParentAlive(ai, parentId)
{
  if (parentId < 0) return null;
  local p = ai._findLineById(parentId);
  if (p == null) return null;
  if (("scrapping" in p) && p.scrapping) return null;
  if (("deadStreak" in p) && p.deadStreak >= DEAD_STREAK_THRESHOLD) return null;
  if (!AIMap.IsValidTile(p.stationA) || !AIRoad.IsRoadStationTile(p.stationA)
      || !AICompany.IsMine(AITile.GetOwner(p.stationA))) return null;
  if (!AIMap.IsValidTile(p.stationB) || !AIRoad.IsRoadStationTile(p.stationB)
      || !AICompany.IsMine(AITile.GetOwner(p.stationB))) return null;
  return p;
}

function OpexRoad1yAbandonMailChild(ai, child, reason)
{
  if (("scrapping" in child) && child.scrapping) return;
  local parentId = ("parentLineId" in child) ? child.parentLineId : -1;
  if (parentId >= 0) {
    local p = ai._findLineById(parentId);
    if (p != null && ("mailChildLineId" in p) && p.mailChildLineId == child.lineId)
      p.mailChildLineId = -1;
  }
  ai._triggerScrapLine(child, reason);
  if (AIMap.IsValidTile(child.stationA) && AIRoad.IsRoadStationTile(child.stationA)
      && AICompany.IsMine(AITile.GetOwner(child.stationA)))
    AIRoad.RemoveRoadStation(child.stationA);
  if (AIMap.IsValidTile(child.stationB) && AIRoad.IsRoadStationTile(child.stationB)
      && AICompany.IsMine(AITile.GetOwner(child.stationB)))
    AIRoad.RemoveRoadStation(child.stationB);
  AILog.Info("ROAD1Y_MAIL action=abandon line=" + child.lineId
      + " parent=" + parentId
      + " pair=" + (("srcTown" in child) ? child.srcTown : -1) + ":" + (("dstTown" in child) ? child.dstTown : -1)
      + " tiles=" + child.stationA + ":" + child.stationB
      + " mail_vol=0 vans=" + (("vehCount" in child) ? child.vehCount : 0)
      + " reason=" + reason);
}

function OpexRoad1yRefleetMailLine(ai, line, year)
{
  local parentId = ("parentLineId" in line) ? line.parentLineId : -1;
  if (OpexRoad1yParentAlive(ai, parentId) == null) {
    OpexRoad1yAbandonMailChild(ai, line, "PARENT_ABANDONED");
    return;
  }
  if (!AIMap.IsValidTile(line.stationA) || !AIRoad.IsRoadStationTile(line.stationA)
      || !AICompany.IsMine(AITile.GetOwner(line.stationA))
      || !AIMap.IsValidTile(line.stationB) || !AIRoad.IsRoadStationTile(line.stationB)
      || !AICompany.IsMine(AITile.GetOwner(line.stationB))) {
    OpexRoad1yAbandonMailChild(ai, line, "STOP_LOST");
    return;
  }
  local stationA = AIStation.GetStationID(line.stationA);
  local stationB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) {
    OpexRoad1yAbandonMailChild(ai, line, "STATION_INVALID");
    return;
  }
  local waitingA = AICargo.IsValidCargo(line.cargo) ? AIStation.GetCargoWaiting(stationA, line.cargo) : 0;
  local waitingB = AICargo.IsValidCargo(line.cargo) ? AIStation.GetCargoWaiting(stationB, line.cargo) : 0;
  local totalWaiting = waitingA + waitingB;
  local vehicles = OpexLineVehicleIds(line, stationA);
  local have = 0;
  local movingCount = 0;
  local liveCap = 0;
  local unitPrice = 0;
  foreach (v in vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    have++;
    if (AIVehicle.GetCurrentSpeed(v) > 0) movingCount++;
    if (liveCap <= 0) {
      local c = AIVehicle.GetCapacity(v, line.cargo);
      if (c > 0) liveCap = c;
    }
    if (unitPrice <= 0) unitPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
  }
  line.vehCount <- have;
  local stopsA = ("nStopsA" in line) && line.nStopsA > 0 ? line.nStopsA : 1;
  local stopsB = ("nStopsB" in line) && line.nStopsB > 0 ? line.nStopsB : 1;
  local stops = stopsA < stopsB ? stopsA : stopsB;
  local mailCap = 2 * stops;
  if (ROAD1Y_GAP > mailCap) mailCap = ROAD1Y_GAP;
  local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (("road1yMailRefleetMonth" in line) && line.road1yMailRefleetMonth == ym) return;
  local capacity = liveCap > 0 ? liveCap : (("capacity" in line) ? line.capacity : 0);
  if (have >= mailCap || movingCount <= 0 || capacity <= 0 || totalWaiting < capacity) return;
  if (unitPrice <= 0 && ai._catalog != null && (line.cargo in ai._catalog.roadEngineByCargo))
    unitPrice = ai._catalog.roadEngineByCargo[line.cargo].price;
  local cashReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : (ROAD1Y_PAX_REFLEET ? 15000 : 25000);
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (unitPrice <= 0 || money < cashReserve + unitPrice) return;
  local want = totalWaiting / capacity;
  if (want > 2) want = 2;
  if (have + want > mailCap) want = mailCap - have;
  local canPay = (money - cashReserve) / unitPrice;
  if (want > canPay) want = canPay;
  if (want <= 0) return;
  line.road1yMailRefleetMonth <- ym;
  local refill = OpexRoadRefleet(ai._catalog, line, have, have + want);
  if (refill.added > 0) {
    line.vehCount <- refill.after;
    if (("trains" in line) && line.trains < refill.after) line.trains = refill.after;
    AILog.Info("ROAD1Y_MAIL action=refleet line=" + line.lineId
        + " parent=" + parentId + " pair=" + line.srcTown + ":" + line.dstTown
        + " tiles=" + line.stationA + ":" + line.stationB
        + " mail_vol=" + totalWaiting + " vans=" + refill.after
        + " added=" + refill.added + " reason=OK");
  } else {
    AILog.Info("ROAD1Y_MAIL action=fail line=" + line.lineId
        + " parent=" + parentId + " pair=" + line.srcTown + ":" + line.dstTown
        + " tiles=" + line.stationA + ":" + line.stationB
        + " mail_vol=" + totalWaiting + " vans=" + have
        + " added=0 reason=REFLEET_" + refill.reason);
  }
}

function OpexRoad1yBuildMailChild(ai, parentLine, cashReserve)
{
  local catalog = ai._catalog;
  local mailCargo = catalog.mailCargo;
  local engine = catalog.roadEngineByCargo[mailCargo];
  local townA = parentLine.srcTown;
  local townB = parentLine.dstTown;
  local siteA = OpexRoad1yFindMailSite(ai, catalog, townA, parentLine.stationA, mailCargo);
  local siteB = siteA != null ? OpexRoad1yFindMailSite(ai, catalog, townB, parentLine.stationB, mailCargo) : null;
  if (siteA == null || siteB == null) {
    if (ROAD1Y_GAP > 0) parentLine.road1yMailNoSite <- 1;
    AILog.Info("ROAD1Y_MAIL action=fail parent=" + parentLine.lineId
        + " pair=" + townA + ":" + townB
        + " tiles=" + (siteA != null ? siteA.tile : -1) + ":" + (siteB != null ? siteB.tile : -1)
        + " mail_vol=0 vans=0 reason=" + (siteA == null ? "NO_SITE_A" : "NO_SITE_B"));
    return false;
  }
  local mailVol = siteA.prod + siteB.prod;
  local refitCap = OpexRoadRefitCapacity(parentLine.depot, engine, mailCargo);
  if (refitCap <= 0) {
    AILog.Info("ROAD1Y_MAIL action=fail parent=" + parentLine.lineId
        + " pair=" + townA + ":" + townB + " tiles=" + siteA.tile + ":" + siteB.tile
        + " mail_vol=" + mailVol + " vans=0 reason=REFIT_CAP");
    return false;
  }
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local okA = AIRoad.BuildDriveThroughRoadStation(siteA.tile, siteA.front,
      AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW);
  local validA = okA && AIRoad.IsRoadStationTile(siteA.tile)
      && AICompany.IsMine(AITile.GetOwner(siteA.tile))
      && AIRoad.AreRoadTilesConnected(siteA.tile, siteA.front)
      && AIRoad.AreRoadTilesConnected(siteA.tile, siteA.back);
  if (!validA) {
    if (AIRoad.IsRoadStationTile(siteA.tile) && AICompany.IsMine(AITile.GetOwner(siteA.tile)))
      AIRoad.RemoveRoadStation(siteA.tile);
    AILog.Info("ROAD1Y_MAIL action=fail parent=" + parentLine.lineId
        + " pair=" + townA + ":" + townB + " tiles=" + siteA.tile + ":" + siteB.tile
        + " mail_vol=" + mailVol + " vans=0 reason=BUILD_STOP_A");
    return false;
  }
  local okB = AIRoad.BuildDriveThroughRoadStation(siteB.tile, siteB.front,
      AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW);
  local stIdA = AIStation.GetStationID(siteA.tile);
  local stIdB = AIStation.GetStationID(siteB.tile);
  local validB = okB && AIRoad.IsRoadStationTile(siteB.tile)
      && AICompany.IsMine(AITile.GetOwner(siteB.tile))
      && AIStation.IsValidStation(stIdA) && AIStation.IsValidStation(stIdB) && stIdA != stIdB
      && AIRoad.AreRoadTilesConnected(siteB.tile, siteB.front)
      && AIRoad.AreRoadTilesConnected(siteB.tile, siteB.back);
  if (!validB) {
    if (AIRoad.IsRoadStationTile(siteB.tile) && AICompany.IsMine(AITile.GetOwner(siteB.tile)))
      AIRoad.RemoveRoadStation(siteB.tile);
    if (AIRoad.IsRoadStationTile(siteA.tile) && AICompany.IsMine(AITile.GetOwner(siteA.tile)))
      AIRoad.RemoveRoadStation(siteA.tile);
    AILog.Info("ROAD1Y_MAIL action=fail parent=" + parentLine.lineId
        + " pair=" + townA + ":" + townB + " tiles=" + siteA.tile + ":" + siteB.tile
        + " mail_vol=" + mailVol + " vans=0 reason=BUILD_STOP_B");
    return false;
  }
  local wantVans = (mailVol >= 2 * refitCap
      && AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= cashReserve + 2 * engine.price
      && OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 2)) ? 2 : 1;
  local built = [];
  local first = AIVehicle.BuildVehicleWithRefit(parentLine.depot, engine.id, mailCargo);
  if (!AIVehicle.IsValidVehicle(first)) {
    OpexRoadRollback(siteA.tile, siteB.tile, null, built, null);
    AILog.Info("ROAD1Y_MAIL action=fail parent=" + parentLine.lineId
        + " pair=" + townA + ":" + townB + " tiles=" + siteA.tile + ":" + siteB.tile
        + " mail_vol=" + mailVol + " vans=0 reason=BUILD_VEH");
    return false;
  }
  built.append(first);
  local cap = AIVehicle.GetCapacity(first, mailCargo);
  local orderFlags = AIOrder.OF_NONE | AIOrder.OF_NON_STOP_INTERMEDIATE;
  local ordersOk = cap > 0
      && AIOrder.AppendOrder(first, siteA.tile, orderFlags)
      && AIOrder.AppendOrder(first, siteB.tile, orderFlags)
      && AIOrder.GetOrderCount(first) == 2;
  if (!ordersOk) {
    OpexRoadRollback(siteA.tile, siteB.tile, null, built, null);
    AILog.Info("ROAD1Y_MAIL action=fail parent=" + parentLine.lineId
        + " pair=" + townA + ":" + townB + " tiles=" + siteA.tile + ":" + siteB.tile
        + " mail_vol=" + mailVol + " vans=0 reason=ORDERS");
    return false;
  }
  if (wantVans == 2) {
    local second = AIVehicle.CloneVehicle(parentLine.depot, first, true);
    if (AIVehicle.IsValidVehicle(second)) built.append(second);
  }
  local started = 0;
  foreach (v in built) {
    if (AIVehicle.StartStopVehicle(v)) started++;
  }
  if (started <= 0) {
    OpexRoadRollback(siteA.tile, siteB.tile, null, built, null);
    AILog.Info("ROAD1Y_MAIL action=fail parent=" + parentLine.lineId
        + " pair=" + townA + ":" + townB + " tiles=" + siteA.tile + ":" + siteB.tile
        + " mail_vol=" + mailVol + " vans=0 reason=START_VEH");
    return false;
  }
  local idx = ai._nextLineId++;
  local dist = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
  local childLine = {
    mode = "road",
    kind = "mail_pax",
    parentLineId = parentLine.lineId,
    stationA = siteA.tile,
    stationB = siteB.tile,
    originA = ("originA" in parentLine) ? parentLine.originA : siteA.tile,
    originB = ("originB" in parentLine) ? parentLine.originB : siteB.tile,
    depot = parentLine.depot,
    cargo = mailCargo,
    nStopsA = 1,
    nStopsB = 1,
    trains = built.len(),
    trains0 = built.len(),
    predTrains = built.len(),
    vehCount = built.len(),
    capacity = cap,
    distance = dist,
    srcTown = townA,
    dstTown = townB,
    srcIndustry = -1,
    dstIndustry = -1,
    deadStreak = 0,
    scrapping = false,
    scrapVehicles = [],
    lineId = idx
  };
  ai._lines.append(childLine);
  parentLine.mailChildLineId <- idx;
  if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;
  ai._c76BumpLayer("lines", false);
  OpexAir0310InvalidateSiteValidity();
  AILog.Info("ROAD1Y_MAIL action=create line=" + idx
      + " parent=" + parentLine.lineId + " pair=" + townA + ":" + townB
      + " tiles=" + siteA.tile + ":" + siteB.tile
      + " mail_vol=" + mailVol + " vans=" + built.len() + " reason=OK");
  return true;
}

/* ROAD1Y_GAP : jusqu'a 4 parents PAX par passe, en sautant un parent sans
 * site MAIL. Un seul succes. A 0, OpexRoad1yMailStep garde le parent unique. */
function OpexRoad1yMailStepGap(ai, cashReserve, activeParents, activePairs, ym)
{
  local attempts = 0;
  while (attempts < 4) {
    local bestLine = null;
    local bestProfit = 0;
    foreach (line in ai._lines) {
      if (!("mode" in line) || line.mode != "road") continue;
      if (("scrapping" in line) && line.scrapping) continue;
      if (!("kind" in line) || line.kind != "pax") continue;
      if (("deadStreak" in line) && line.deadStreak > 0) continue;
      if (line.lineId in activeParents) continue;
      if (("road1yMailTryMonth" in line) && line.road1yMailTryMonth == ym) continue;
      if (("road1yMailNoSite" in line) && line.road1yMailNoSite != 0) continue;
      local ta = ("srcTown" in line) ? line.srcTown : -1;
      local tb = ("dstTown" in line) ? line.dstTown : -1;
      if (ta < 0 || tb < 0 || ta == tb) continue;
      local pairKey = ta < tb ? (ta + ":" + tb) : (tb + ":" + ta);
      if (pairKey in activePairs) continue;
      if (!AIMap.IsValidTile(line.stationA) || !AIRoad.IsRoadStationTile(line.stationA)
          || !AICompany.IsMine(AITile.GetOwner(line.stationA))) continue;
      if (!AIMap.IsValidTile(line.stationB) || !AIRoad.IsRoadStationTile(line.stationB)
          || !AICompany.IsMine(AITile.GetOwner(line.stationB))) continue;
      if (!("depot" in line) || !AIMap.IsValidTile(line.depot)
          || !AIRoad.IsRoadDepotTile(line.depot)
          || !AICompany.IsMine(AITile.GetOwner(line.depot))) continue;
      local profit = 0;
      if ("lastProfit" in line) {
        profit = line.lastProfit;
      } else {
        local stA = AIStation.GetStationID(line.stationA);
        if (AIStation.IsValidStation(stA)) {
          local vehs = OpexLineVehicleIds(line, stA);
          foreach (v in vehs) {
            if (AIVehicle.IsValidVehicle(v)) profit += AIVehicle.GetProfitThisYear(v);
          }
          if (profit <= 500) profit = 0;
        }
      }
      if (profit > bestProfit) {
        bestProfit = profit;
        bestLine = line;
      }
    }
    if (bestLine == null) return;
    bestLine.road1yMailTryMonth <- ym;
    attempts++;
    if (OpexRoad1yBuildMailChild(ai, bestLine, cashReserve)) return;
  }
}

function OpexRoad1yMailStep(ai, year)
{
  local catalog = ai._catalog;
  if (catalog == null || !("mailCargo" in catalog) || catalog.mailCargo < 0) return;
  local mailCargo = catalog.mailCargo;
  if (!(mailCargo in catalog.roadEngineByCargo)) return;
  local engine = catalog.roadEngineByCargo[mailCargo];
  if (engine == null || engine.price <= 0) return;
  local cashReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : (ROAD1Y_PAX_REFLEET ? 15000 : 25000);
  local needCash = cashReserve + 2 * catalog.costRoadTruckStop + engine.price;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < needCash) return;
  if (!OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 1)) return;
  local activeParents = {};
  local activePairs = {};
  foreach (line in ai._lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("kind" in line) || line.kind != "mail_pax") continue;
    if ("parentLineId" in line) activeParents[line.parentLineId] <- true;
    local ta = ("srcTown" in line) ? line.srcTown : -1;
    local tb = ("dstTown" in line) ? line.dstTown : -1;
    if (ta >= 0 && tb >= 0) {
      local key = ta < tb ? (ta + ":" + tb) : (tb + ":" + ta);
      activePairs[key] <- true;
    }
  }
  local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (ROAD1Y_GAP > 0) {
    OpexRoad1yMailStepGap(ai, cashReserve, activeParents, activePairs, ym);
    return;
  }
  local bestParent = null;
  local bestProfit = 0;
  foreach (line in ai._lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("kind" in line) || line.kind != "pax") continue;
    if (("deadStreak" in line) && line.deadStreak > 0) continue;
    if (line.lineId in activeParents) continue;
    if (("road1yMailTryMonth" in line) && line.road1yMailTryMonth == ym) continue;
    local ta = ("srcTown" in line) ? line.srcTown : -1;
    local tb = ("dstTown" in line) ? line.dstTown : -1;
    if (ta < 0 || tb < 0 || ta == tb) continue;
    local pairKey = ta < tb ? (ta + ":" + tb) : (tb + ":" + ta);
    if (pairKey in activePairs) continue;
    if (!AIMap.IsValidTile(line.stationA) || !AIRoad.IsRoadStationTile(line.stationA)
        || !AICompany.IsMine(AITile.GetOwner(line.stationA))) continue;
    if (!AIMap.IsValidTile(line.stationB) || !AIRoad.IsRoadStationTile(line.stationB)
        || !AICompany.IsMine(AITile.GetOwner(line.stationB))) continue;
    if (!("depot" in line) || !AIMap.IsValidTile(line.depot)
        || !AIRoad.IsRoadDepotTile(line.depot)
        || !AICompany.IsMine(AITile.GetOwner(line.depot))) continue;
    local profit = 0;
    if ("lastProfit" in line) {
      profit = line.lastProfit;
    } else {
      local stA = AIStation.GetStationID(line.stationA);
      if (AIStation.IsValidStation(stA)) {
        local vehs = OpexLineVehicleIds(line, stA);
        foreach (v in vehs) {
          if (AIVehicle.IsValidVehicle(v)) profit += AIVehicle.GetProfitThisYear(v);
        }
        if (profit <= 500) profit = 0;
      }
    }
    if (profit > bestProfit) {
      bestProfit = profit;
      bestParent = line;
    }
  }
  if (bestParent == null) return;
  bestParent.road1yMailTryMonth <- ym;
  OpexRoad1yBuildMailChild(ai, bestParent, cashReserve);
}

/* ROAD1Y_MAIL_NET : lignes MAIL routieres autonomes, sans parent bus.
 * A 0, OpexRoad1yMailNetStep retourne avant tout appel API.
 * Mois d'ouverture deja tente : non lu tant que le reglage vaut 0. */
ROAD1Y_MAIL_NET_OPEN_YM <- -1;

function OpexRoad1yMailNetLog(fields)
{
  if (DECISION_LOG) OpexDecide("ROAD1Y_MAIL_NET", fields);
}

/* Boucle de OpexRoad1yFindMailSite, rayon 6 autour du centre seulement.
 * Pas de BFS vers un bus : la ligne n'a pas de parent. */
function OpexRoad1yFindMailNetSite(ai, catalog, townId, mailCargo)
{
  if (!AITown.IsValidTown(townId)) return null;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
  local used = OpexRoad1yOurTruckTiles(ai, townId);
  local center = AITown.GetLocation(townId);
  if (!AIMap.IsValidTile(center)) return null;
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local cands = [];
  local rad = 6;
  for (local dx = -rad; dx <= rad; dx++) {
    for (local dy = -rad; dy <= rad; dy++) {
      local x = cx + dx;
      local y = cy + dy;
      if (x <= 0 || y <= 0 || x >= mapX - 1 || y >= mapY - 1) continue;
      local tile = AIMap.GetTileIndex(x, y);
      if (!AIRoad.IsRoadTile(tile) || AIRoad.IsRoadDepotTile(tile)
          || AIRoad.IsRoadStationTile(tile) || AITile.IsStationTile(tile)) continue;
      if (AITile.GetClosestTown(tile) != townId) continue;
      if (OpexRoad100CatchmentOverlaps(tile, used, coverage)) continue;
      local axis = OpexBusDistrictAxis(tile);
      if (axis == 0) continue;
      local front = tile + axis;
      local back = tile - axis;
      if (!AIMap.IsValidTile(front) || !AIMap.IsValidTile(back)) continue;
      local prod = AITile.GetCargoProduction(tile, mailCargo, 1, 1, coverage);
      if (prod <= 0) continue;
      local acc = AITile.GetCargoAcceptance(tile, mailCargo, 1, 1, coverage);
      if (acc < 8) continue;
      local score = prod * 100 + acc - AIMap.DistanceManhattan(tile, center);
      local item = { tile = tile, front = front, back = back, prod = prod, acc = acc, score = score };
      local pos = cands.len();
      cands.append(item);
      while (pos > 0 && cands[pos - 1].score < item.score) {
        cands[pos] = cands[pos - 1];
        pos--;
      }
      cands[pos] = item;
      if (cands.len() > 4) cands.pop();
    }
  }
  foreach (cand in cands) {
    local canBuild = false;
    { local test = AITestMode();
      canBuild = AIRoad.BuildDriveThroughRoadStation(cand.tile, cand.front,
          AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW); }
    if (canBuild) return cand;
  }
  return null;
}

/* BFS sur la voirie existante, sinon le L des deux axes retenu par
 * OpexRoadTraceBuildable. Un trace qui traverse le corps de l'arret est
 * refuse : la pose du quai couperait le chemin (meme filet que le bus). */
function OpexRoad1yMailNetTrace(frontA, frontB, tileA, tileB)
{
  local direct = OpexRoadBfsPath(frontA, frontB, ROAD_MAX_TRACE_TILES);
  if (direct != null && direct.len() > 0
      && !OpexRoadTraceHitsStop(direct, tileA)
      && !OpexRoadTraceHitsStop(direct, tileB)) return direct;
  local picked = null;
  local pickedLen = 0;
  local axisH = OpexRoadTrace(frontA, frontB, true);
  local axisV = OpexRoadTrace(frontA, frontB, false);
  if (axisH.len() > 0 && OpexRoadTraceBuildable(axisH)
      && !OpexRoadTraceHitsStop(axisH, tileA)
      && !OpexRoadTraceHitsStop(axisH, tileB)) {
    picked = axisH;
    pickedLen = axisH.len();
  }
  if (axisV.len() > 0 && OpexRoadTraceBuildable(axisV)
      && !OpexRoadTraceHitsStop(axisV, tileA)
      && !OpexRoadTraceHitsStop(axisV, tileB)) {
    if (picked == null || axisV.len() < pickedLen) picked = axisV;
  }
  /* Repli A* routier (road1y_astar) entre les deux facades. */
  if (picked == null && ROAD1Y_ASTAR > 0) {
    local astar = OpexRoad1yAStarTrace({ tile = frontA, front = null },
                                       { tile = frontB, front = null }, ROAD_MAX_TRACE_TILES + 64);
    if (astar != null && astar.len() > 0
        && !OpexRoadTraceHitsStop(astar, tileA)
        && !OpexRoadTraceHitsStop(astar, tileB)) picked = astar;
  }
  return picked;
}

function OpexRoad1yBuildMailNet(ai, townA, townB, cashReserve)
{
  local catalog = ai._catalog;
  if (catalog == null || !("mailCargo" in catalog) || catalog.mailCargo < 0) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB + " reason=NO_CARGO");
    return false;
  }
  local mailCargo = catalog.mailCargo;
  if (!(mailCargo in catalog.roadEngineByCargo)) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB + " reason=NO_ENGINE");
    return false;
  }
  local engine = catalog.roadEngineByCargo[mailCargo];
  if (engine == null || engine.price <= 0) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB + " reason=NO_ENGINE");
    return false;
  }
  local needCash = cashReserve + 2 * catalog.costRoadTruckStop
      + catalog.costRoadDepot + 2 * engine.price;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < needCash) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB + " reason=CASH");
    return false;
  }
  local siteA = OpexRoad1yFindMailNetSite(ai, catalog, townA, mailCargo);
  local siteB = siteA != null ? OpexRoad1yFindMailNetSite(ai, catalog, townB, mailCargo) : null;
  if (siteA == null || siteB == null) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " reason=" + (siteA == null ? "NO_SITE_A" : "NO_SITE_B"));
    return false;
  }
  /* Front qui regarde l'autre ville : le sens unique de l'axe peut partir
   * a l'oppose, et le trace traverserait alors le corps de l'arret. */
  local frontA = siteA.front;
  local frontB = siteB.front;
  if (AIMap.DistanceManhattan(siteA.back, siteB.tile)
      < AIMap.DistanceManhattan(siteA.front, siteB.tile)) frontA = siteA.back;
  if (AIMap.DistanceManhattan(siteB.back, siteA.tile)
      < AIMap.DistanceManhattan(siteB.front, siteA.tile)) frontB = siteB.back;
  local siteDist = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
  if (siteDist < 40 || siteDist > 160) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=SITE_DIST");
    return false;
  }
  local trace = OpexRoad1yMailNetTrace(frontA, frontB, siteA.tile, siteB.tile);
  if (trace == null) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=NO_TRACE");
    return false;
  }
  local depotPlan = OpexRoadFindDepot(trace, siteA, siteB, true);
  if (depotPlan == null) {
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=NO_DEPOT");
    return false;
  }
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local added = [];
  local built = [];
  local okA = AIRoad.BuildDriveThroughRoadStation(siteA.tile, frontA,
      AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW);
  local validA = okA && AIRoad.IsRoadStationTile(siteA.tile)
      && AICompany.IsMine(AITile.GetOwner(siteA.tile))
      && AIRoad.AreRoadTilesConnected(siteA.tile, siteA.front)
      && AIRoad.AreRoadTilesConnected(siteA.tile, siteA.back);
  if (!validA) {
    if (AIRoad.IsRoadStationTile(siteA.tile) && AICompany.IsMine(AITile.GetOwner(siteA.tile)))
      AIRoad.RemoveRoadStation(siteA.tile);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=BUILD_STOP_A");
    return false;
  }
  local okB = AIRoad.BuildDriveThroughRoadStation(siteB.tile, frontB,
      AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW);
  local stIdA = AIStation.GetStationID(siteA.tile);
  local stIdB = AIStation.GetStationID(siteB.tile);
  local validB = okB && AIRoad.IsRoadStationTile(siteB.tile)
      && AICompany.IsMine(AITile.GetOwner(siteB.tile))
      && AIStation.IsValidStation(stIdA) && AIStation.IsValidStation(stIdB)
      && stIdA != stIdB && stIdA != 65535 && stIdB != 65535
      && AIRoad.AreRoadTilesConnected(siteB.tile, siteB.front)
      && AIRoad.AreRoadTilesConnected(siteB.tile, siteB.back);
  if (!validB) {
    if (AIRoad.IsRoadStationTile(siteB.tile) && AICompany.IsMine(AITile.GetOwner(siteB.tile)))
      AIRoad.RemoveRoadStation(siteB.tile);
    if (AIRoad.IsRoadStationTile(siteA.tile) && AICompany.IsMine(AITile.GetOwner(siteA.tile)))
      AIRoad.RemoveRoadStation(siteA.tile);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=BUILD_STOP_B");
    return false;
  }
  if (!OpexRoadBuildTrace(trace, added)) {
    OpexRoadRollback(siteA.tile, siteB.tile, null, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=TRACE");
    return false;
  }
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cashReserve) {
    OpexRoadRollback(siteA.tile, siteB.tile, null, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=RESERVE");
    return false;
  }
  /* Bit perpendiculaire : BuildRoad(front, tile) avant BuildRoadDepot.
   * CmdBuildRoadDepot ne pose rien sur front. */
  AIRoad.BuildRoad(depotPlan.front, depotPlan.tile);
  local stubConnected = AIRoad.AreRoadTilesConnected(depotPlan.front, depotPlan.tile);
  if (stubConnected) added.append({ from = depotPlan.front, to = depotPlan.tile });
  local depotOk = stubConnected && AIRoad.BuildRoadDepot(depotPlan.tile, depotPlan.front);
  local depotTile = null;
  if (depotOk && AIRoad.IsRoadDepotTile(depotPlan.tile)
      && AIRoad.GetRoadDepotFrontTile(depotPlan.tile) == depotPlan.front
      && AIRoad.AreRoadTilesConnected(depotPlan.tile, depotPlan.front))
    depotTile = depotPlan.tile;
  if (depotTile == null) {
    local leftover = AIRoad.IsRoadDepotTile(depotPlan.tile) ? depotPlan.tile : null;
    OpexRoadRollback(siteA.tile, siteB.tile, leftover, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=DEPOT");
    return false;
  }
  local refitCap = OpexRoadRefitCapacity(depotTile, engine, mailCargo);
  if (refitCap <= 0) {
    OpexRoadRollback(siteA.tile, siteB.tile, depotTile, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=REFIT_CAP");
    return false;
  }
  local moneyNow = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local wantVans = 1;
  if (moneyNow >= cashReserve + 2 * engine.price
      && OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 2)) wantVans = 2;
  if (moneyNow < cashReserve + engine.price
      || !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, wantVans)) {
    OpexRoadRollback(siteA.tile, siteB.tile, depotTile, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=CASH_VEH");
    return false;
  }
  local first = AIVehicle.BuildVehicleWithRefit(depotTile, engine.id, mailCargo);
  if (!AIVehicle.IsValidVehicle(first)) {
    OpexRoadRollback(siteA.tile, siteB.tile, depotTile, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=BUILD_VEH");
    return false;
  }
  built.append(first);
  local cap = AIVehicle.GetCapacity(first, mailCargo);
  local orderFlags = AIOrder.OF_FULL_LOAD_ANY | AIOrder.OF_NON_STOP_INTERMEDIATE;
  local ordersOk = cap > 0
      && AIOrder.AppendOrder(first, siteA.tile, orderFlags)
      && AIOrder.AppendOrder(first, siteB.tile, orderFlags)
      && AIOrder.GetOrderCount(first) == 2;
  if (!ordersOk) {
    OpexRoadRollback(siteA.tile, siteB.tile, depotTile, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=ORDERS");
    return false;
  }
  if (wantVans == 2) {
    local second = AIVehicle.CloneVehicle(depotTile, first, true);
    if (AIVehicle.IsValidVehicle(second)) built.append(second);
  }
  local started = 0;
  foreach (veh in built) {
    if (AIVehicle.StartStopVehicle(veh)) started++;
  }
  if (started <= 0) {
    OpexRoadRollback(siteA.tile, siteB.tile, depotTile, built, added);
    OpexRoad1yMailNetLog("action=fail pair=" + townA + ":" + townB
        + " dist=" + siteDist + " reason=START_VEH");
    return false;
  }
  local idx = ai._nextLineId++;
  local netLine = {
    mode = "road",
    kind = "mail_net",
    stationA = siteA.tile,
    stationB = siteB.tile,
    originA = siteA.tile,
    originB = siteB.tile,
    depot = depotTile,
    cargo = mailCargo,
    nStopsA = 1,
    nStopsB = 1,
    trains = built.len(),
    trains0 = built.len(),
    predTrains = built.len(),
    vehCount = built.len(),
    capacity = cap,
    distance = siteDist,
    srcTown = townA,
    dstTown = townB,
    srcIndustry = -1,
    dstIndustry = -1,
    deadStreak = 0,
    scrapping = false,
    scrapVehicles = [],
    lineId = idx,
    road1yMailNetMonth = -1
  };
  ai._lines.append(netLine);
  if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;
  ai._c76BumpLayer("lines", false);
  OpexAir0310InvalidateSiteValidity();
  OpexRoad1yMailNetLog("action=open pair=" + townA + ":" + townB
      + " dist=" + siteDist + " vans=" + built.len() + " line=" + idx);
  return true;
}

function OpexRoad1yRefleetMailNet(ai, line, year)
{
  if (!AIMap.IsValidTile(line.stationA) || !AIRoad.IsRoadStationTile(line.stationA)
      || !AICompany.IsMine(AITile.GetOwner(line.stationA))
      || !AIMap.IsValidTile(line.stationB) || !AIRoad.IsRoadStationTile(line.stationB)
      || !AICompany.IsMine(AITile.GetOwner(line.stationB))) {
    OpexRoad1yMailNetLog("action=fail pair=" + line.srcTown + ":" + line.dstTown
        + " line=" + line.lineId + " reason=STOP_LOST");
    return;
  }
  local stationA = AIStation.GetStationID(line.stationA);
  local stationB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)
      || stationA == 65535 || stationB == 65535) {
    OpexRoad1yMailNetLog("action=fail pair=" + line.srcTown + ":" + line.dstTown
        + " line=" + line.lineId + " reason=STATION_INVALID");
    return;
  }
  local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (("road1yMailNetMonth" in line) && line.road1yMailNetMonth == ym) return;
  local waitingA = AICargo.IsValidCargo(line.cargo) ? AIStation.GetCargoWaiting(stationA, line.cargo) : 0;
  local waitingB = AICargo.IsValidCargo(line.cargo) ? AIStation.GetCargoWaiting(stationB, line.cargo) : 0;
  local minWait = waitingA < waitingB ? waitingA : waitingB;
  local vehicles = OpexLineVehicleIds(line, stationA);
  local have = 0;
  local movingCount = 0;
  local liveCap = 0;
  local unitPrice = 0;
  foreach (veh in vehicles) {
    if (!AIVehicle.IsValidVehicle(veh)) continue;
    have++;
    if (AIVehicle.GetCurrentSpeed(veh) > 0) movingCount++;
    if (liveCap <= 0) {
      local liveOne = AIVehicle.GetCapacity(veh, line.cargo);
      if (liveOne > 0) liveCap = liveOne;
    }
    if (unitPrice <= 0) unitPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(veh));
  }
  line.vehCount <- have;
  local capacity = liveCap > 0 ? liveCap : (("capacity" in line) ? line.capacity : 0);
  local waitFloor = have < 10 ? 30 : 100;
  if (have >= ROAD1Y_MAIL_NET || movingCount <= 0 || capacity <= 0
      || minWait < capacity || minWait <= waitFloor) return;
  if (unitPrice <= 0 && ai._catalog != null && (line.cargo in ai._catalog.roadEngineByCargo))
    unitPrice = ai._catalog.roadEngineByCargo[line.cargo].price;
  local cashReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : (ROAD1Y_PAX_REFLEET ? 15000 : 25000);
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (unitPrice <= 0 || money < cashReserve + unitPrice) return;
  local capFloor = capacity < 50 ? capacity : 50;
  local want = (minWait - capFloor) / capacity;
  if (want > 4) want = 4;
  local room = ROAD1Y_MAIL_NET - have;
  if (want > room) want = room;
  local canPay = (money - cashReserve) / unitPrice;
  if (want > canPay) want = canPay;
  if (want <= 0) return;
  if (!OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 1)) return;
  line.road1yMailNetMonth <- ym;
  local before = have;
  local refill = OpexRoadRefleet(ai._catalog, line, have, have + want);
  if (refill.added > 0) {
    line.vehCount <- refill.after;
    if (("trains" in line) && line.trains < refill.after) line.trains = refill.after;
    OpexRoad1yMailNetLog("action=refleet pair=" + line.srcTown + ":" + line.dstTown
        + " line=" + line.lineId + " before=" + before + " after=" + refill.after
        + " waitA=" + waitingA + " waitB=" + waitingB);
  } else {
    OpexRoad1yMailNetLog("action=fail pair=" + line.srcTown + ":" + line.dstTown
        + " line=" + line.lineId + " before=" + before + " after=" + have
        + " waitA=" + waitingA + " waitB=" + waitingB
        + " reason=REFLEET_" + refill.reason);
  }
}

function OpexRoad1yMailNetStep(ai, year)
{
  if (ROAD1Y_MAIL_NET <= 0) return;
  local catalog = ai._catalog;
  if (catalog == null || !("mailCargo" in catalog) || catalog.mailCargo < 0) return;
  local mailCargo = catalog.mailCargo;
  if (!(mailCargo in catalog.roadEngineByCargo)) return;
  local engine = catalog.roadEngineByCargo[mailCargo];
  if (engine == null || engine.price <= 0) return;
  local nLines = 0;
  local townUse = {};
  local covered = {};
  foreach (line in ai._lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("kind" in line) || line.kind != "mail_net") continue;
    nLines++;
    local endA = ("srcTown" in line) ? line.srcTown : -1;
    local endB = ("dstTown" in line) ? line.dstTown : -1;
    if (endA >= 0) {
      local prevA = (endA in townUse) ? townUse[endA] : 0;
      townUse[endA] <- prevA + 1;
    }
    if (endB >= 0) {
      local prevB = (endB in townUse) ? townUse[endB] : 0;
      townUse[endB] <- prevB + 1;
    }
    if (endA >= 0 && endB >= 0) {
      local coveredKey = endA < endB ? (endA + ":" + endB) : (endB + ":" + endA);
      covered[coveredKey] <- true;
    }
  }
  if (nLines >= ROAD1Y_MAIL_NET) return;
  local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (ROAD1Y_MAIL_NET_OPEN_YM == ym) return;
  local cashReserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : (ROAD1Y_PAX_REFLEET ? 15000 : 25000);
  local needCash = cashReserve + 2 * catalog.costRoadTruckStop
      + catalog.costRoadDepot + 2 * engine.price;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < needCash) return;
  if (!OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 1)) return;
  local towns = [];
  local list = AITownList();
  for (local townId = list.Begin(); !list.IsEnd(); townId = list.Next()) {
    if (!AITown.IsValidTown(townId)) continue;
    local pop = AITown.GetPopulation(townId);
    if (pop < 400) continue;
    local prod = AITown.GetLastMonthProduction(townId, mailCargo);
    if (prod < 27) continue;
    local capEnds = pop / 10000 + 1;
    local usedEnds = (townId in townUse) ? townUse[townId] : 0;
    if (usedEnds >= capEnds) continue;
    local center = AITown.GetLocation(townId);
    if (!AIMap.IsValidTile(center)) continue;
    towns.append({ id = townId, prod = prod, center = center });
  }
  local pairs = [];
  for (local i = 0; i < towns.len(); i++) {
    for (local j = i + 1; j < towns.len(); j++) {
      local leftTown = towns[i];
      local rightTown = towns[j];
      local pairKey = leftTown.id < rightTown.id
          ? (leftTown.id + ":" + rightTown.id)
          : (rightTown.id + ":" + leftTown.id);
      if (pairKey in covered) continue;
      local centerDist = AIMap.DistanceManhattan(leftTown.center, rightTown.center);
      if (centerDist < 40 || centerDist > 130) continue;
      local prodMin = leftTown.prod < rightTown.prod ? leftTown.prod : rightTown.prod;
      local absDist = centerDist - 80;
      if (absDist < 0) absDist = -absDist;
      local score = prodMin * 1000 - absDist;
      local pairItem = { idA = leftTown.id, idB = rightTown.id, score = score };
      local pos = pairs.len();
      pairs.append(pairItem);
      while (pos > 0 && pairs[pos - 1].score < pairItem.score) {
        pairs[pos] = pairs[pos - 1];
        pos--;
      }
      pairs[pos] = pairItem;
      if (pairs.len() > 4) pairs.pop();
    }
  }
  ROAD1Y_MAIL_NET_OPEN_YM = ym;
  if (pairs.len() == 0) {
    OpexRoad1yMailNetLog("action=fail pair=-1:-1 dist=0 vans=0 reason=NO_PAIR");
    return;
  }
  local attempts = 0;
  foreach (pairTry in pairs) {
    if (attempts >= 4) return;
    attempts++;
    if (OpexRoad1yBuildMailNet(ai, pairTry.idA, pairTry.idB, cashReserve)) return;
  }
}
