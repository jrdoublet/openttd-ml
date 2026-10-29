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
        if (cost < 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cost + 50000) {
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
