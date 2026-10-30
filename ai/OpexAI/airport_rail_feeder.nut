/*
 * AIRPORT-RAIL-FEEDER v0 (non-imported, OFF by default).
 *
 * Narrow, honest capability: reuse TWO EXISTING train platforms and ONE
 * EXISTING, idle, passenger-capable train in OUR existing rail depot. The hub
 * train platform MUST have precisely the StationID of an owned airport with
 * an active Opex passenger flight. We do not lay track, join stations, buy
 * trains, commandeer working vehicles, or touch the airport infrastructure.
 * No railway feeder is claimed merely because two stations are adjacent.
 *
 * Required plan:
 *   { townId, airportTile, sourceRailTile, hubRailTile, depot, train }
 * The shared BUS certificate OpexAirportFeederTownSlotProof proves ONLY a
 * zero remaining town airport quota under the two-slot rules. No geometric
 * site-search result (possibly truncated) counts as impossibility.
 *
 * No imports or settings added: callers explicitly pass optIn=true. They must
 * publish a tracked line immediately on success:
 *   mode="rail", kind="pax", purpose="airport_rail_feeder",
 *   sourceTownId, parentAirLineId, stationA=sourceRailTile,
 *   stationB=hubRailTile, depot, vehicles=[train], cargo=paxCargo.
 * The ordinary RAIL passenger veto requires a separate feeder-specific
 * admission path before this opt-in can be integrated into the scheduler.
 *
 * Railway reachability uses bounded real owned rail triples and deliberately
 * refuses bridges/tunnels, unknown ownership, mismatched railtypes and budget
 * exhaustion. It proves track connectivity, NOT signal authority, timetable
 * feasibility or delivered transfers: those require an OpenTTD smoke.
 */

const OPEX_AIRPORT_RAIL_FEEDER_MAX_EXPANSIONS = 512;
const OPEX_AIRPORT_RAIL_FEEDER_MAX_PLATFORM_TILES = 24;
const OPEX_AIRPORT_RAIL_FEEDER_MIN_CASH = 150000;

function OpexAirportRailFeederEnabled(optIn)
{
  return optIn == true && MODE_AIR && MODE_RAIL;
}

function OpexAirportRailFeederCertified(townId, classifyTown)
{
  /* The BUS verifier re-reads the live settings + municipal slots after
   * checking the certificate. No stale or fabricated geometry proof passes. */
  return OpexAirportFeederCertified(townId, classifyTown);
}

/* Do not treat an orphan airport, a static line record, or a parked aircraft
 * as proof of an operational AIR interchange. A live passenger plane must
 * have BOTH an order at this StationID and an order to a different station.
 * line.stationA/B in Opex are tiles, not StationIDs. */
function OpexAirportRailFeederAirParent(lines, hubId, paxCargo)
{
  if (lines == null || !AIStation.IsValidStation(hubId)) return -1;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "air"
        || !("cargo" in line) || line.cargo != paxCargo
        || (("scrapping" in line) && line.scrapping)
        || (("deadStreak" in line) && line.deadStreak >= 2)) continue;
    local touches = false, other = false;
    foreach (field in ["stationA", "stationB"]) {
      if (!(field in line) || line[field] == null
          || !AIMap.IsValidTile(line[field])) continue;
      local st = AIStation.GetStationID(line[field]);
      if (st == hubId) touches = true;
      else if (AIStation.IsValidStation(st)) other = true;
    }
    if (!touches || !other || !("vehicles" in line) || line.vehicles == null) continue;
    foreach (plane in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(plane)
          || AIVehicle.GetVehicleType(plane) != AIVehicle.VT_AIR
          || AIVehicle.IsStoppedInDepot(plane)
          || AIVehicle.GetCapacity(plane, paxCargo) <= 0) continue;
      local hasHub = false, hasOther = false;
      local count = AIOrder.GetOrderCount(plane);
      for (local i = 0; i < count; i++) {
        if (!AIOrder.IsValidVehicleOrder(plane, i)) continue;
        local dest = AIOrder.GetOrderDestination(plane, i);
        if (!AIMap.IsValidTile(dest)) continue;
        local st = AIStation.GetStationID(dest);
        if (st == hubId) hasHub = true;
        else if (AIStation.IsValidStation(st)) hasOther = true;
      }
      if (hasHub && hasOther) return ("lineId" in line) ? line.lineId : -1;
    }
  }
  return -1;
}

/* Platform existence/ownership and exact StationID are checked against the
 * game, never inferred from an anchor, nearby tile or plan.stationId. */
function OpexAirportRailFeederPlatform(tile, stationId, maxTiles)
{
  if (tile == null || !AIMap.IsValidTile(tile)
      || !AIStation.IsValidStation(stationId)
      || !AIRail.IsRailStationTile(tile)
      || AIStation.GetStationID(tile) != stationId
      || !AICompany.IsMine(AITile.GetOwner(tile))) return false;
  local tiles = AITileList_StationType(stationId, AIStation.STATION_TRAIN);
  return tiles.Count() > 0 && tiles.Count() <= maxTiles && tiles.HasItem(tile);
}

function OpexAirportRailFeederOwnedRail(tile, railType)
{
  if (tile == null || !AIMap.IsValidTile(tile)
      || !AICompany.IsMine(AITile.GetOwner(tile))
      || (!AIRail.IsRailTile(tile) && !AIRail.IsRailStationTile(tile))
      || AIRail.IsRailDepotTile(tile)
      || AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile))
    return false;
  return AIRail.GetRailType(tile) == railType;
}

/* Four true coordinate neighbors; tile+width arithmetic without X/Y bounds
 * could wrap the east edge into the next row and invent a connection. */
function OpexAirportRailFeederNeighbors(tile)
{
  local x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
  local maxX = AIMap.GetMapSizeX(), maxY = AIMap.GetMapSizeY();
  local result = [];
  if (x > 0) result.append(AIMap.GetTileIndex(x - 1, y));
  if (x + 1 < maxX) result.append(AIMap.GetTileIndex(x + 1, y));
  if (y > 0) result.append(AIMap.GetTileIndex(x, y - 1));
  if (y + 1 < maxY) result.append(AIMap.GetTileIndex(x, y + 1));
  return result;
}

/* Exhaustive bounded BFS over ORIENTED rail triples (previous,current,next),
 * not raw adjacent rail tiles. AreTilesConnected is the native physical
 * predicate for the actual built track geometry. A cached 2-tile pair is not
 * proof of a complete path. The target's entered rail platform is checked by
 * the same native predicate BEFORE a success can be reported.
 *
 * Depot seed: (depot, GetRailDepotFrontTile(depot)).
 * Platform seed: (platform, every owned adjacent rail tile).
 * On platforms with no confirmed outgoing straight track this intentionally
 * fails closed (not even a simulated build is attempted).
 */
function OpexAirportRailFeederRailPath(startTile, targetStation, depotStart,
                                      railType, maxExpansions)
{
  if (maxExpansions < 1 || maxExpansions > OPEX_AIRPORT_RAIL_FEEDER_MAX_EXPANSIONS
      || !AIStation.IsValidStation(targetStation)) return false;
  local queue = [], seen = {};
  if (depotStart) {
    if (!AIRail.IsRailDepotTile(startTile)
        || !AICompany.IsMine(AITile.GetOwner(startTile))
        || AIRail.GetRailType(startTile) != railType) return false;
    local front = AIRail.GetRailDepotFrontTile(startTile);
    if (!OpexAirportRailFeederOwnedRail(front, railType)
        || AIMap.DistanceManhattan(startTile, front) != 1) return false;
    queue.append({ prev = startTile, cur = front });
  } else {
    if (!OpexAirportRailFeederOwnedRail(startTile, railType)
        || !AIRail.IsRailStationTile(startTile)) return false;
    foreach (neighbor in OpexAirportRailFeederNeighbors(startTile)) {
      if (!OpexAirportRailFeederOwnedRail(neighbor, railType)) continue;
      queue.append({ prev = startTile, cur = neighbor });
    }
  }
  local head = 0, expanded = 0;
  while (head < queue.len() && expanded < maxExpansions) {
    local current = queue[head++];
    expanded++;
    local key = current.prev + "|" + current.cur;
    if (key in seen) continue;
    seen.rawset(key, true);
    if (!OpexAirportRailFeederOwnedRail(current.cur, railType)) continue;
    foreach (next in OpexAirportRailFeederNeighbors(current.cur)) {
      if (next == current.prev
          || !OpexAirportRailFeederOwnedRail(next, railType)
          || !AIRail.AreTilesConnected(current.prev, current.cur, next)) continue;
      if (AIRail.IsRailStationTile(next)
          && AIStation.GetStationID(next) == targetStation) return true;
      local nextKey = current.cur + "|" + next;
      if (!(nextKey in seen)) queue.append({ prev = current.cur, cur = next });
    }
  }
  return false;
}

/* Only a train deliberately left unused and stopped in its OWN existing depot
 * is eligible. A train referenced by any existing service is never hijacked.
 * The length <= 16/16 tile restriction makes even a single-platform-tile
 * source/hub long enough; it intentionally excludes many existing rakes. */
function OpexAirportRailFeederIdleTrain(train, depot, lines, paxCargo)
{
  if (train == null || !AIVehicle.IsValidVehicle(train)
      || AIVehicle.GetVehicleType(train) != AIVehicle.VT_RAIL
      || !AIVehicle.IsPrimaryVehicle(train)
      || !AIVehicle.IsStoppedInDepot(train)
      || AIVehicle.GetLocation(train) != depot
      || AIOrder.GetOrderCount(train) != 0
      || AIVehicle.GetCapacity(train, paxCargo) <= 0
      || AIVehicle.GetLength(train) <= 0 || AIVehicle.GetLength(train) > 16)
    return false;
  if (lines != null) foreach (line in lines) {
    if (line == null) continue;
    if (("vehicle" in line) && line.vehicle == train) return false;
    if (("vehicles" in line) && line.vehicles != null)
      foreach (other in line.vehicles) if (other == train) return false;
  }
  return true;
}

function OpexAirportRailFeederValidate(catalog, lines, plan, classifyTown,
                                       optIn = false, maxExpansions = 256)
{
  local out = { ok = false, reason = "DISABLED", parentLine = -1,
                sourceStation = -1, hubStation = -1, train = null,
                validatedTick = -1 };
  if (!OpexAirportRailFeederEnabled(optIn)) return out;
  out.reason = "PLAN";
  if (catalog == null || !("paxCargo" in catalog) || catalog.paxCargo < 0
      || !AICargo.HasCargoClass(catalog.paxCargo, AICargo.CC_PASSENGERS)
      || plan == null || typeof plan != "table"
      || !("townId" in plan) || !AITown.IsValidTown(plan.townId)
      || !("airportTile" in plan) || !("sourceRailTile" in plan)
      || !("hubRailTile" in plan) || !("depot" in plan)
      || !("train" in plan) || maxExpansions < 1
      || maxExpansions > OPEX_AIRPORT_RAIL_FEEDER_MAX_EXPANSIONS) return out;
  foreach (key in ["airportTile", "sourceRailTile", "hubRailTile", "depot"])
    if (plan[key] == null || !AIMap.IsValidTile(plan[key])) return out;
  if (!AIAirport.IsAirportTile(plan.airportTile)
      || !AICompany.IsMine(AITile.GetOwner(plan.airportTile))
      || !AIRail.IsRailDepotTile(plan.depot)
      || !AICompany.IsMine(AITile.GetOwner(plan.depot))
      || AITile.GetClosestTown(plan.sourceRailTile) != plan.townId)
    return out;
  local hubId = AIStation.GetStationID(plan.airportTile);
  local srcId = AIStation.GetStationID(plan.sourceRailTile);
  if (!AIStation.IsValidStation(hubId) || !AIStation.IsValidStation(srcId)
      || hubId == srcId
      || !OpexAirportRailFeederPlatform(plan.sourceRailTile, srcId,
            OPEX_AIRPORT_RAIL_FEEDER_MAX_PLATFORM_TILES)
      || !OpexAirportRailFeederPlatform(plan.hubRailTile, hubId,
            OPEX_AIRPORT_RAIL_FEEDER_MAX_PLATFORM_TILES)) {
    out.reason = "NO_JOINED_RAIL"; return out;
  }
  out.sourceStation = srcId;
  out.hubStation = hubId;
  local parentAirId = OpexAirportRailFeederAirParent(lines, hubId, catalog.paxCargo);
  if (parentAirId < 0) { out.reason = "NO_ACTIVE_AIR"; return out; }
  out.parentLine = parentAirId;
  if (lines != null) foreach (line in lines) {
    if (line == null || !("purpose" in line)
        || line.purpose != "airport_rail_feeder") continue;
    if (("sourceTownId" in line) && line.sourceTownId == plan.townId) {
      out.reason = "DUPLICATE"; return out;
    }
  }
  if (AITile.GetCargoProduction(plan.sourceRailTile, catalog.paxCargo, 1, 1,
          AIStation.GetCoverageRadius(AIStation.STATION_TRAIN)) <= 0) {
    out.reason = "NO_SOURCE_PAX"; return out;
  }
  local railType = AIRail.GetRailType(plan.depot);
  if (!OpexAirportRailFeederOwnedRail(plan.sourceRailTile, railType)
      || !OpexAirportRailFeederOwnedRail(plan.hubRailTile, railType)
      || !OpexAirportRailFeederIdleTrain(plan.train, plan.depot, lines, catalog.paxCargo)) {
    out.reason = "NO_IDLE_TRAIN"; return out;
  }
  /* Both directions are required, and the depot must ACTUALLY reach the
   * source. A matching StationID alone supplies no rail path. */
  if (!OpexAirportRailFeederRailPath(plan.sourceRailTile, hubId, false,
          railType, maxExpansions)
      || !OpexAirportRailFeederRailPath(plan.hubRailTile, srcId, false,
          railType, maxExpansions)
      || !OpexAirportRailFeederRailPath(plan.depot, srcId, true,
          railType, maxExpansions)) {
    out.reason = "NO_PHYSICAL_RAIL_PATH"; return out;
  }
  /* Last, not first: a paused path scan must not reuse an expired certificate. */
  if (!OpexAirportRailFeederCertified(plan.townId, classifyTown)) {
    out.reason = "AIRPORT_UNKNOWN"; return out;
  }
  out.train = plan.train;
  out.validatedTick = AIController.GetTick();
  out.reason = "OK";
  out.ok = true;
  return out;
}

/* Roll back ONLY our new orders on the previously orderless, idle train.
 * No rail, station, airport, depot or train is ever sold or removed. */
function OpexAirportRailFeederClearOrders(train)
{
  if (!AIVehicle.IsValidVehicle(train) || !AIVehicle.IsStoppedInDepot(train))
    return false;
  local count = AIOrder.GetOrderCount(train);
  if (count > 2) return false;
  while (count > 0) {
    if (!AIOrder.RemoveOrder(train, 0)) return false;
    local nextCount = AIOrder.GetOrderCount(train);
    if (nextCount >= count) return false;
    count = nextCount;
  }
  return true;
}

/* A failed AppendOrder may leave a partial timetable. Never call GetStationID
 * on an invalid destination; no-load is checked on the ACTUAL second order. */
function OpexAirportRailFeederOrdersOk(train, sourceStation, hubStation)
{
  if (!AIVehicle.IsValidVehicle(train) || AIOrder.GetOrderCount(train) != 2
      || !AIOrder.IsValidVehicleOrder(train, 0)
      || !AIOrder.IsValidVehicleOrder(train, 1)) return false;
  local srcTile = AIOrder.GetOrderDestination(train, 0);
  local hubTile = AIOrder.GetOrderDestination(train, 1);
  if (!AIMap.IsValidTile(srcTile) || !AIMap.IsValidTile(hubTile)
      || AIStation.GetStationID(srcTile) != sourceStation
      || AIStation.GetStationID(hubTile) != hubStation) return false;
  local flags = AIOrder.GetOrderFlags(train, 1);
  return (flags & AIOrder.OF_TRANSFER) != 0
      && (flags & AIOrder.OF_NO_LOAD) != 0;
}

/* Activation only: NO BuildRailStation, BuildRail, BuildVehicle or demolition.
 * Cash/slots: 0 new train slots and £0 construction; enforce available game
 * RAIL mode and explicit liquidity buffer, never assume cash allows a train
 * already in service to be hijacked.
 *
 * result.ok authorizes caller's immediate line registration; a failed start
 * that cannot be rolled back yields PENDING_RECOVERY with the train ID, which
 * caller must keep quarantined. Successful start is never rolled back by
 * deleting shared infrastructure.
 */
function OpexAirportRailFeederActivate(catalog, lines, plan, classifyTown,
                                       optIn = false, cashReserve = -1,
                                       maxExpansions = 256)
{
  local result = { ok = false, reason = "DISABLED", vehicle = null,
                   sourceStation = -1, hubStation = -1,
                   parentLine = -1, actualCost = 0, slotsAdded = 0 };
  if (!OpexAirportRailFeederEnabled(optIn)) return result;
  local checked = OpexAirportRailFeederValidate(
      catalog, lines, plan, classifyTown, optIn, maxExpansions);
  result.reason = checked.reason;
  if (!checked.ok) return result;
  result.vehicle = checked.train;
  result.sourceStation = checked.sourceStation;
  result.hubStation = checked.hubStation;
  result.parentLine = checked.parentLine;
  local reserve = cashReserve >= 0 ? cashReserve : OPEX_AIRPORT_RAIL_FEEDER_MIN_CASH;
  if (reserve < OPEX_AIRPORT_RAIL_FEEDER_MIN_CASH
      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < reserve) {
    result.reason = "CASH"; return result;
  }
  if (AIGameSettings.IsDisabledVehicleType(AIVehicle.VT_RAIL)) {
    result.reason = "NO_RAIL_SLOT"; return result;
  }
  /* No new vehicle is bought: an existing primary train already occupies its
   * slot. This is valid even when the game's cap is exactly full. */
  if (AIGameSettings.IsValid("vehicle.max_trains")
      && AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, AIVehicle.VT_RAIL)
          > AIGameSettings.GetValue("vehicle.max_trains")) {
    result.reason = "NO_RAIL_SLOT"; return result;
  }
  /* Revalidate zero-order state immediately before mutation. */
  local train = checked.train;
  if (!OpexAirportRailFeederIdleTrain(train, plan.depot, lines, catalog.paxCargo)) {
    result.reason = "TRAIN_CHANGED"; return result;
  }
  if (AIController.GetTick() != checked.validatedTick) {
    result.reason = "STALE"; return result;
  }
  local sourceFlags = AIOrder.OF_NONE | AIOrder.OF_NON_STOP_INTERMEDIATE;
  local hubFlags = AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD
      | AIOrder.OF_NON_STOP_INTERMEDIATE;
  local orderOk = AIOrder.AppendOrder(train, plan.sourceRailTile, sourceFlags)
      && AIOrder.AppendOrder(train, plan.hubRailTile, hubFlags)
      && OpexAirportRailFeederOrdersOk(train,
            checked.sourceStation, checked.hubStation);
  if (!orderOk) {
    result.reason = OpexAirportRailFeederClearOrders(train)
        ? "ORDERS" : "PENDING_RECOVERY";
    return result;
  }
  if (AIController.GetTick() != checked.validatedTick) {
    result.reason = OpexAirportRailFeederClearOrders(train)
        ? "STALE" : "PENDING_RECOVERY";
    return result;
  }
  if (!AIVehicle.StartStopVehicle(train)) {
    result.reason = OpexAirportRailFeederClearOrders(train)
        ? "START" : "PENDING_RECOVERY";
    return result;
  }
  result.ok = true;
  result.reason = "OK";
  return result;
}
