/* Distributed catchment, independent of ROAD100 satellite accounting. */
function OpexRoad1ySpreadNear(tile, occupied)
{
  foreach (other in occupied) {
    local dx = abs(AIMap.GetTileX(tile) - AIMap.GetTileX(other));
    local dy = abs(AIMap.GetTileY(tile) - AIMap.GetTileY(other));
    if (dx <= 5 && dy <= 5) return true;
  }
  return false;
}

function OpexRoad1ySpreadSort(a, b)
{
  if (a.acceptance != b.acceptance) return a.acceptance > b.acceptance ? -1 : 1;
  return a.tile < b.tile ? -1 : (a.tile == b.tile ? 0 : 1);
}

function OpexRoad1ySpreadCount(line)
{
  foreach (end in ["A", "B"]) {
    local root = end == "A" ? line.stationA : line.stationB;
    if (!AIRoad.IsRoadStationTile(root) || !AICompany.IsMine(AITile.GetOwner(root))) continue;
    local tiles = AITileList_StationType(AIStation.GetStationID(root), AIStation.STATION_BUS_STOP);
    line.rawset("nStops" + end, tiles.Count());
  }
}

function OpexRoad1ySpreadCopy(src, dst)
{
  foreach (key in ["road1ySpreadA", "road1ySpreadB", "road1ySpreadDone"])
    if (key in src) dst.rawset(key, src[key]);
}

function OpexRoad1ySpreadStops(catalog, line, end)
{
  if (ROAD1Y_SPREAD_STOPS <= 0) return;
  if (line == null || line.mode != "road" || line.kind != "pax"
      || !AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)) return;
  local key = "road1ySpread" + end;
  if (!(key in line)) line.rawset(key, []);
  local root = end == "A" ? line.stationA : line.stationB;
  local candidates = [];
  local built = 0, cost = 0, refused = "NO_SITE";
  do {
    if (!AIRoad.IsRoadStationTile(root) || !AICompany.IsMine(AITile.GetOwner(root))) {
      refused = "ROOT"; break;
    }
    local stationId = AIStation.GetStationID(root);
    if (stationId == 65535 || !AIStation.IsValidStation(stationId)) {
      refused = "STATION"; break;
    }
    // Keep only still-live spread pieces; N is a total, not N every five years.
    local live = [];
    foreach (tile in line[key])
      if (AIRoad.IsRoadStationTile(tile) && AICompany.IsMine(AITile.GetOwner(tile))
          && AIStation.GetStationID(tile) == stationId) live.append(tile);
    line[key] = live;
    if (live.len() >= ROAD1Y_SPREAD_STOPS) { refused = "LIMIT"; break; }
    local radius = 12;
    // Reading settings cannot suspend. No construction inside this try.
    try {
      local spread = AIGameSettings.GetValue("station.station_spread");
      if (spread > 0 && spread < radius) radius = spread;
    } catch (e) {}
    local occupied = [];
    local stations = AIStationList(AIStation.STATION_ANY);
    for (local id = stations.Begin(); !stations.IsEnd(); id = stations.Next()) {
      local tiles = AITileList_StationType(id, AIStation.STATION_ANY);
      for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next()) occupied.append(tile);
    }
    local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    AIRoad.SetCurrentRoadType(catalog.roadType);
    local cx = AIMap.GetTileX(root), cy = AIMap.GetTileY(root);
    for (local x = cx - radius; x <= cx + radius; x++) {
      if (x < 0 || x >= AIMap.GetMapSizeX()) continue;
      for (local y = cy - radius; y <= cy + radius; y++) {
        if (y < 0 || y >= AIMap.GetMapSizeY()) continue;
        local tile = AIMap.GetTileIndex(x, y);
        if (!AIRoad.IsRoadTile(tile) || AITile.IsStationTile(tile)
            || AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)
            || AIRoad.IsRoadDepotTile(tile) || AITile.GetSlope(tile) != AITile.SLOPE_FLAT
            || OpexRoad1ySpreadNear(tile, occupied)) continue;
        local axis = OpexBusDistrictAxis(tile);
        if (axis == 0) continue;
        local front = tile + axis, back = tile - axis;
        if (!AIMap.IsValidTile(front) || !AIMap.IsValidTile(back)
            || AIMap.DistanceManhattan(tile, front) != 1
            || AIMap.DistanceManhattan(tile, back) != 1
            || !AIRoad.AreRoadTilesConnected(tile, front)
            || !AIRoad.AreRoadTilesConnected(front, tile)
            || !AIRoad.AreRoadTilesConnected(tile, back)
            || !AIRoad.AreRoadTilesConnected(back, tile)) continue;
        local acceptance = AITile.GetCargoAcceptance(tile, line.cargo, 1, 1, coverage);
        if (acceptance > 1) candidates.append({ tile = tile, axis = axis, acceptance = acceptance });
      }
    }
    candidates.sort(OpexRoad1ySpreadSort);
    local reserve = (ROAD1Y_FLEET_UNLOCK & 2) != 0 ? 10000 : 50000;
    foreach (site in candidates) {
      if (live.len() >= ROAD1Y_SPREAD_STOPS) { refused = "LIMIT"; break; }
      if (OpexRoad1ySpreadNear(site.tile, occupied)) continue;
      if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < reserve + catalog.costRoadBusStop) {
        refused = "CASH"; break;
      }
      local accounting = AIAccounting();
      local exec = AIExecMode();
      local ok = AIRoad.BuildDriveThroughRoadStation(site.tile, site.tile + site.axis,
          AIRoad.ROADVEHTYPE_BUS, stationId);
      local error = AIError.GetLastError();
      cost += accounting.GetCosts();
      if (ok) {
        live.append(site.tile);
        occupied.append(site.tile);
        built++;
        refused = "OK";
      } else {
        refused = "BUILD_" + error;
        if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES) { refused = "AUTHORITY"; break; }
      }
    }
  } while (false);
  OpexRoad1ySpreadCount(line);
  if (DECISION_LOG) OpexDecide("ROAD1Y_SPREAD",
      "line=" + (("lineId" in line) ? line.lineId : root)
      + " end=" + end + " candidates=" + candidates.len() + " built=" + built
      + " refused=" + refused + " cost=" + cost + " nStops=" + line["nStops" + end]);
}

/* Strictly after the fifth calendar anniversary (including leap days). */
function OpexRoad1ySpreadDue(date, now)
{
  local years = AIDate.GetYear(now) - AIDate.GetYear(date);
  if (years != 5) return years > 5;
  local months = AIDate.GetMonth(now) - AIDate.GetMonth(date);
  if (months != 0) return months > 0;
  return AIDate.GetDayOfMonth(now) > AIDate.GetDayOfMonth(date);
}

function OpexRoad1ySpreadStep(ai)
{
  if (ROAD1Y_SPREAD_STOPS <= 0) return;
  local now = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now);
  // Derive monthly throttling from persistent line dates, including after Load.
  foreach (line in ai._lines) {
    if (!("road1ySpreadDone" in line)) continue;
    local date = line.road1ySpreadDone;
    if (AIDate.GetYear(date) * 12 + AIDate.GetMonth(date) == month) return;
  }
  foreach (line in ai._lines) {
    if (!("mode" in line) || line.mode != "road"
        || !("kind" in line) || line.kind != "pax"
        || (("scrapping" in line) && line.scrapping)
        || (("road1ySpreadDone" in line) && !OpexRoad1ySpreadDue(line.road1ySpreadDone, now))) continue;
    if (ai._saveProjection != null && line in ai._saveProjection) delete ai._saveProjection[line];
    OpexRoad1ySpreadStops(ai._catalog, line, "A");
    OpexRoad1ySpreadStops(ai._catalog, line, "B");
    line.road1ySpreadDone <- now;
    if (ai._saveProjection != null) ai._saveProjection[line] <- OpexSaveProjectLine(line);
    break;
  }
}
