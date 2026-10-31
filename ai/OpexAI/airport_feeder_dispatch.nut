/* PAX-AIR-FIRST: strictly opt-in real BUS feeder using existing infrastructure.
 * Own bus source in an airport-slot-saturated town -> bus stop exactly JOINED
 * to an active own airport, using real road connectivity and an owned depot.
 * No source stop, joint hub stop, depot or physical route => no construction.
 */
PAX_AIR_FEEDER_LAST_MONTH <- -1;
PAX_AIR_FEEDER_EXISTING_DIAG <- {};

function OpexAirportFeederOwnAirTowns()
{
  local owned = {};
  local list = AIStationList(AIStation.STATION_AIRPORT);
  for (local sid = list.Begin(); !list.IsEnd(); sid = list.Next()) {
    local tiles = AITileList_StationType(sid, AIStation.STATION_AIRPORT);
    for (local t = tiles.Begin(); !tiles.IsEnd(); t = tiles.Next()) {
      if (!AIAirport.IsAirportTile(t)) continue;
      local town = AITile.GetClosestTown(t);
      if (AITown.IsValidTown(town)) owned.rawset(town, true);
      break;
    }
  }
  return owned;
}

function OpexAirportFeederFindExistingPlan(catalog, lines)
{
  PAX_AIR_FEEDER_EXISTING_DIAG = { activeHub = 0, joinedBus = 0,
      quotaTown = 0, nearDepot = 0, checked = 0 };
  if (!PAX_AIR_FIRST_FEEDER_ONLY || !MODE_ROAD || !ROAD_BUILD_ENABLED
      || catalog == null || catalog.paxCargo < 0) return null;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local airTowns = OpexAirportFeederOwnAirTowns();
  local hubs = AIStationList(AIStation.STATION_AIRPORT);
  local origins = AIStationList(AIStation.STATION_BUS_STOP);
  local depots = AIDepotList(AITile.TRANSPORT_ROAD);
  local considered = 0;
  local validations = 0;
  for (local hub = hubs.Begin(); !hubs.IsEnd(); hub = hubs.Next()) {
    if (!AIStation.IsValidStation(hub)) continue;
    local airport = -1;
    local airports = AITileList_StationType(hub, AIStation.STATION_AIRPORT);
    for (local t = airports.Begin(); !airports.IsEnd(); t = airports.Next()) {
      if (AIAirport.IsAirportTile(t)) { airport = t; break; }
    }
    if (!AIMap.IsValidTile(airport)
        || OpexAirportFeederParent(lines, hub, catalog.paxCargo) < 0) continue;
    PAX_AIR_FEEDER_EXISTING_DIAG.activeHub++;
    local hubStops = AITileList_StationType(hub, AIStation.STATION_BUS_STOP);
    for (local hubStop = hubStops.Begin(); !hubStops.IsEnd(); hubStop = hubStops.Next()) {
      if (!AIRoad.IsRoadStationTile(hubStop)
          || !AIRoad.IsDriveThroughRoadStationTile(hubStop)) continue;
      PAX_AIR_FEEDER_EXISTING_DIAG.joinedBus++;
      for (local source = origins.Begin(); !origins.IsEnd(); source = origins.Next()) {
        if (!AIStation.IsValidStation(source) || source == hub) continue;
        local srcStops = AITileList_StationType(source, AIStation.STATION_BUS_STOP);
        for (local srcStop = srcStops.Begin(); !srcStops.IsEnd(); srcStop = srcStops.Next()) {
          if (!AIRoad.IsRoadStationTile(srcStop)
              || AIMap.DistanceManhattan(srcStop, hubStop) > 40) continue;
          local town = AITile.GetClosestTown(srcStop);
          if (!AITown.IsValidTown(town) || town in airTowns
              || !OpexAirportFeederCertified(town, null)) continue;
          PAX_AIR_FEEDER_EXISTING_DIAG.quotaTown++;
          considered++;
          if (considered > 12) return null;
          for (local depot = depots.Begin(); !depots.IsEnd(); depot = depots.Next()) {
            if (!AIRoad.IsRoadDepotTile(depot)
                || AIMap.DistanceManhattan(srcStop, depot) > 24) continue;
            PAX_AIR_FEEDER_EXISTING_DIAG.nearDepot++;
            local p = { townId = town, airportTile = airport,
                sourceStop = srcStop, hubStop = hubStop, depot = depot };
            validations++;
            PAX_AIR_FEEDER_EXISTING_DIAG.checked++;
            /* Bound to two complete physical route checks per month. */
            if (OpexAirportFeederValidate(catalog, lines, p,
                    OpexAirportFeederTownSlotProof, true).ok) return p;
            if (validations >= 2) return null;
          }
        }
      }
    }
  }
  return null;
}

/* Publish immediately after successful construction. Save/Load's ordinary
 * _lines array then owns this route and its exact transfer orders. Never
 * refleet using the generic road builder (which would discard OF_TRANSFER). */
function OpexAirportFeederRegisterBuilt(owner, plan, r, year, createdSource = false)
{
  local v = r.vehicle;
  local hasTicket = ("pendingLineId" in plan) && plan.pendingLineId >= 0;
  local id = hasTicket ? plan.pendingLineId : owner._nextLineId;
  local activeLine = { stationA = plan.sourceStop, stationB = plan.hubStop,
      originA = AITown.GetLocation(plan.townId), originB = plan.airportTile,
      cargo = owner._catalog.paxCargo, mode = "road", kind = "pax",
      purpose = "airport_feeder", sourceTownId = plan.townId,
      parentAirLineId = r.parentLine, lineId = id,
      depot = plan.depot, vehicle = v, vehicles = [v],
      trains = 1, trains0 = 1, vehCount = 1, predTrains = 1,
      nStopsA = 1, nStopsB = 1,
      capacity = AIVehicle.GetCapacity(v, owner._catalog.paxCargo),
      buildDate = AIDate.GetCurrentDate(), year = year,
      distance = AIMap.DistanceManhattan(plan.sourceStop, plan.hubStop),
      actualCapital = r.actualCost, predicted = 0,
      predRevenue = 0, predRunning = 0, predAmort = 0,
      predCarried = 0, predOneWayDays = 0,
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lastLiveVehicles = 1, expandBlocked = true,
      createdSourceStop = createdSource,
      createdDepot = ("newDepot" in plan) && plan.newDepot,
      newRoadEdges = ("newRoadEdges" in plan) ? plan.newRoadEdges : [],
      newDepotStubBuilt = ("newDepotStubBuilt" in plan)
          && plan.newDepotStubBuilt,
      depotFront = ("depotFront" in plan) ? plan.depotFront : -1 };
  if (hasTicket) {
    /* Atomic in-memory promotion: never leave a recovery record referring
     * to a bus that is now owned by a successful active line. */
    local replaced = false;
    for (local i = 0; i < owner._lines.len(); i++) {
      local line = owner._lines[i];
      if (line != null && ("purpose" in line)
          && line.purpose == "airport_feeder_recovery"
          && ("lineId" in line) && line.lineId == id) {
        owner._lines[i] = activeLine;
        replaced = true;
        break;
      }
    }
    if (!replaced) {
      if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_RECOVERY",
          "mode=road action=missing_commit_ticket line=" + id);
      /* Preserve a live vehicle's ownership if a corruption removed the
       * pre-commit record, but surface the broken transaction in the logs. */
      owner._lines.append(activeLine);
    }
  } else {
    owner._lines.append(activeLine);
    owner._nextLineId++;
  }
  owner._saveProjection = null;
  owner._c76BumpLayer("lines", false);
  if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER", "mode=road action=built line="
      + id + " town=" + plan.townId + " hub=" + r.hubStation
      + " parent_air=" + r.parentLine + " vehicle=" + v);
  return true;
}

/* Build, then persist. The caller of the new-stop variant handles its own
 * isolated station rollback; the old-stop variant never removes anything. */
function OpexAirportFeederTryExisting(owner, year)
{
  if (!PAX_AIR_FIRST_FEEDER_ONLY || !MODE_AIR || !MODE_ROAD
      || !ROAD_BUILD_ENABLED || owner == null || owner._lines == null
      || owner._catalog == null) return false;
  /* Complete any previous partial transaction before attempting new work.
   * Recovery records live inside the ordinary persisted lines array. */
  if (OpexAirportFeederRecover(owner)) return false;
  local month = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (month == PAX_AIR_FEEDER_LAST_MONTH) return false;
  PAX_AIR_FEEDER_LAST_MONTH = month;
  local plan = OpexAirportFeederFindExistingPlan(owner._catalog, owner._lines);
  if (plan == null) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_SCAN", "mode=road source=existing result=none"
        + " active_hub=" + PAX_AIR_FEEDER_EXISTING_DIAG.activeHub
        + " joined_bus=" + PAX_AIR_FEEDER_EXISTING_DIAG.joinedBus
        + " quota_town=" + PAX_AIR_FEEDER_EXISTING_DIAG.quotaTown
        + " near_depot=" + PAX_AIR_FEEDER_EXISTING_DIAG.nearDepot
        + " checks=" + PAX_AIR_FEEDER_EXISTING_DIAG.checked);
    return OpexAirportFeederTryNewSource(owner, year);
  }
  /* Persist a recovery intent before BuildVehicleWithRefit can spend cash. */
  OpexAirportFeederRecordRecovery(owner, plan,
      { vehicle = null }, year, false);
  local r = OpexAirportFeederBuild(owner._catalog, owner._lines, plan,
      OpexAirportFeederTownSlotProof, true);
  if (!r.ok) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER", "mode=road action=refused town="
        + plan.townId + " reason=" + r.reason);
    if (r.reason == "PENDING_SELL" && AIVehicle.IsValidVehicle(r.vehicle))
      OpexAirportFeederRecordRecovery(owner, plan, r, year, false);
    return false;
  }
  return OpexAirportFeederRegisterBuilt(owner, plan, r, year);
}
