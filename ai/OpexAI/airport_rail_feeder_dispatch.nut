/* Opt-in railway counterpart: existing joined platform, track, depot and
 * idle passenger train only. No simulated rails, joined-by-proximity station,
 * equipment commandeered from another service, or false revenue claim.
 */
PAX_AIR_RAIL_FEEDER_LAST_MONTH <- -1;
PAX_AIR_RAIL_FEEDER_DIAG <- {};

function OpexAirportRailFeederRecover(owner)
{
  local pending = false;
  for (local i = owner._lines.len() - 1; i >= 0; i--) {
    local line = owner._lines[i];
    if (!("purpose" in line) || line.purpose != "airport_rail_feeder_recovery") continue;
    local v = ("vehicle" in line) ? line.vehicle : null;
    if (v != null && AIVehicle.IsValidVehicle(v)) {
      /* ID recycling after Save/Load must never make us clear a train's
       * orders after another service has taken ownership of that ID. */
      local ownVehicles = AIVehicleList();
      if (!ownVehicles.HasItem(v)
          || AIVehicle.GetVehicleType(v) != AIVehicle.VT_RAIL
          || !("recoveryEngine" in line)
          || line.recoveryEngine != AIVehicle.GetEngineType(v)) {
        pending = true;
        continue;
      }
      local shared = false;
      foreach (other in owner._lines) {
        if (other == null || other == line) continue;
        if (("vehicle" in other) && other.vehicle == v) shared = true;
        if (("vehicles" in other) && other.vehicles != null)
          foreach (known in other.vehicles)
            if (known == v) shared = true;
      }
      if (shared) { pending = true; continue; }
      if (!AIVehicle.IsStoppedInDepot(v)) {
        AIVehicle.SendVehicleToDepot(v);
        pending = true;
        continue;
      }
      if (!OpexAirportRailFeederClearOrders(v)) { pending = true; continue; }
    }
    owner._lines.remove(i);
    owner._c76BumpLayer("lines", false);
  }
  return pending;
}

function OpexAirportRailFeederFindExistingPlan(catalog, lines)
{
  PAX_AIR_RAIL_FEEDER_DIAG = { activeHub = 0, joinedRail = 0,
      quotaTown = 0, idleTrain = 0, checked = 0 };
  if (!PAX_AIR_FIRST_FEEDER_ONLY || !MODE_RAIL || catalog == null
      || catalog.paxCargo < 0) return null;
  local ownAir = OpexAirportFeederOwnAirTowns();
  local airHubs = AIStationList(AIStation.STATION_AIRPORT);
  local railStations = AIStationList(AIStation.STATION_TRAIN);
  local depots = AIDepotList(AITile.TRANSPORT_RAIL);
  local validations = 0;
  for (local hub = airHubs.Begin(); !airHubs.IsEnd(); hub = airHubs.Next()) {
    if (!AIStation.IsValidStation(hub)) continue;
    local airport = -1;
    local airTiles = AITileList_StationType(hub, AIStation.STATION_AIRPORT);
    for (local tile = airTiles.Begin(); !airTiles.IsEnd(); tile = airTiles.Next()) {
      if (AIAirport.IsAirportTile(tile)) { airport = tile; break; }
    }
    if (!AIMap.IsValidTile(airport)
        || OpexAirportRailFeederAirParent(lines, hub, catalog.paxCargo) < 0)
      continue;
    PAX_AIR_RAIL_FEEDER_DIAG.activeHub++;
    local hubRails = AITileList_StationType(hub, AIStation.STATION_TRAIN);
    for (local hubRail = hubRails.Begin(); !hubRails.IsEnd(); hubRail = hubRails.Next()) {
      if (!AIRail.IsRailStationTile(hubRail)) continue;
      PAX_AIR_RAIL_FEEDER_DIAG.joinedRail++;
      for (local src = railStations.Begin(); !railStations.IsEnd(); src = railStations.Next()) {
        if (src == hub || !AIStation.IsValidStation(src)) continue;
        local srcRails = AITileList_StationType(src, AIStation.STATION_TRAIN);
        for (local srcRail = srcRails.Begin(); !srcRails.IsEnd(); srcRail = srcRails.Next()) {
          if (!AIRail.IsRailStationTile(srcRail)
              || AIMap.DistanceManhattan(srcRail, hubRail) > 90) continue;
          local town = AITile.GetClosestTown(srcRail);
          if (!AITown.IsValidTown(town) || town in ownAir
              || !OpexAirportRailFeederCertified(town,
                    OpexAirportFeederTownSlotProof)) continue;
          PAX_AIR_RAIL_FEEDER_DIAG.quotaTown++;
          for (local depot = depots.Begin(); !depots.IsEnd(); depot = depots.Next()) {
            if (!AIRail.IsRailDepotTile(depot)
                || AIMap.DistanceManhattan(depot, srcRail) > 48) continue;
            local vehicles = AIVehicleList_Depot(depot);
            for (local train = vehicles.Begin(); !vehicles.IsEnd(); train = vehicles.Next()) {
              if (!OpexAirportRailFeederIdleTrain(train, depot, lines, catalog.paxCargo)) continue;
              PAX_AIR_RAIL_FEEDER_DIAG.idleTrain++;
              validations++;
              PAX_AIR_RAIL_FEEDER_DIAG.checked++;
              if (validations > 2) return null;
              local plan = { townId = town, airportTile = airport,
                  sourceRailTile = srcRail, hubRailTile = hubRail,
                  depot = depot, train = train };
              if (OpexAirportRailFeederValidate(catalog, lines, plan,
                      OpexAirportFeederTownSlotProof, true, 256).ok) return plan;
            }
          }
        }
      }
    }
  }
  return null;
}

function OpexAirportRailFeederTryExisting(owner, year)
{
  if (!PAX_AIR_FIRST_FEEDER_ONLY || !MODE_AIR || !MODE_RAIL
      || owner == null || owner._catalog == null || owner._lines == null) return false;
  if (OpexAirportRailFeederRecover(owner)) return false;
  local month = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (month == PAX_AIR_RAIL_FEEDER_LAST_MONTH) return false;
  PAX_AIR_RAIL_FEEDER_LAST_MONTH = month;
  local plan = OpexAirportRailFeederFindExistingPlan(owner._catalog, owner._lines);
  if (plan == null) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_SCAN", "mode=rail source=existing result=none"
        + " active_hub=" + PAX_AIR_RAIL_FEEDER_DIAG.activeHub
        + " joined_rail=" + PAX_AIR_RAIL_FEEDER_DIAG.joinedRail
        + " quota_town=" + PAX_AIR_RAIL_FEEDER_DIAG.quotaTown
        + " idle_train=" + PAX_AIR_RAIL_FEEDER_DIAG.idleTrain
        + " checked=" + PAX_AIR_RAIL_FEEDER_DIAG.checked);
    return false;
  }
  local r = OpexAirportRailFeederActivate(owner._catalog, owner._lines, plan,
      OpexAirportFeederTownSlotProof, true, -1, 256);
  if (!r.ok) {
    if (r.reason == "PENDING_RECOVERY" && r.vehicle != null) {
      owner._lines.append({ mode = "rail", kind = "pax",
          purpose = "airport_rail_feeder_recovery", scrapping = true,
          stationA = plan.sourceRailTile, stationB = plan.hubRailTile,
          originA = AITown.GetLocation(plan.townId),
          originB = plan.airportTile,
          depot = plan.depot, cargo = owner._catalog.paxCargo,
          vehicle = r.vehicle, vehicles = [r.vehicle],
          recoveryEngine = AIVehicle.IsValidVehicle(r.vehicle)
              ? AIVehicle.GetEngineType(r.vehicle) : -1,
          trains = 0, trains0 = 0, vehCount = 0, predTrains = 0,
          predicted = 0, predRevenue = 0, predRunning = 0, predAmort = 0,
          sourceTownId = plan.townId, lineId = owner._nextLineId });
      owner._nextLineId++;
      owner._saveProjection = null;
      owner._c76BumpLayer("lines", false);
    }
    return false;
  }
  local id = owner._nextLineId;
  owner._lines.append({ mode = "rail", kind = "pax",
      purpose = "airport_rail_feeder", stationA = plan.sourceRailTile,
      stationB = plan.hubRailTile, originA = AITown.GetLocation(plan.townId),
      originB = plan.airportTile, depot = plan.depot,
      cargo = owner._catalog.paxCargo, sourceTownId = plan.townId,
      parentAirLineId = r.parentLine, vehicle = r.vehicle,
      vehicles = [r.vehicle], trains = 1, trains0 = 1,
      predTrains = 1, vehCount = 1, lineId = id,
      buildDate = AIDate.GetCurrentDate(), year = year,
      distance = AIMap.DistanceManhattan(plan.sourceRailTile, plan.hubRailTile),
      actualCapital = 0, predicted = 0, predRevenue = 0,
      predRunning = 0, predAmort = 0, predCarried = 0,
      scrapping = false, scrapVehicles = [], deadStreak = 0,
      expandBlocked = true, lastLiveVehicles = 1 });
  owner._nextLineId++;
  owner._c76BumpLayer("lines", false);
  if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER", "mode=rail action=activated line="
      + id + " town=" + plan.townId + " parent_air=" + r.parentLine);
  return true;
}
