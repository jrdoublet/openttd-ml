/* PAX-AIR-FIRST: guarded creation of ONE NEW bus bay at a source town.
 * On failure only that NEW station may be removed. Existing roads, depots,
 * airport station and joined hub BUS stop must never be demolished.
 * Save/Load recovery tickets keep a failed vehicle from being orphaned.
 */
PAX_AIR_FEEDER_SITING_DIAG <- {};
function OpexAirportFeederRecordRecovery(owner, plan, result, year, createdSource)
{
  /* The recovery record MUST survive deletion of the source bay and Save/Load.
   * Anchor both station fields to the still-owned AIR hub; the source tile is
   * a separate optional resource, NEVER the persistence identity. */
  local sourceStillExists = AIMap.IsValidTile(plan.sourceStop)
      && AIRoad.IsRoadStationTile(plan.sourceStop)
      && AICompany.IsMine(AITile.GetOwner(plan.sourceStop))
      && AIStation.GetStationID(plan.sourceStop)
          != AIStation.GetStationID(plan.hubStop);
  local recoveryEngine = result.vehicle != null
      && AIVehicle.IsValidVehicle(result.vehicle)
      ? AIVehicle.GetEngineType(result.vehicle) : -1;
  local ticket = { mode = "road", kind = "pax",
      purpose = "airport_feeder_recovery", scrapping = true,
      expandBlocked = true, sourceTownId = plan.townId,
      stationA = plan.hubStop,
      stationB = plan.hubStop,
      sourceStopTile = plan.sourceStop,
      sourceStationId = sourceStillExists
          ? AIStation.GetStationID(plan.sourceStop) : -1,
      recoveryEngine = recoveryEngine,
      /* All lines, including recovery records, are visited by the shared
       * freight origin index and Save/Load validators. Supply valid tiles
       * but NEVER report a completed passenger service for this record. */
      originA = AITown.GetLocation(plan.townId),
      originB = plan.airportTile,
      depot = plan.depot, cargo = owner._catalog.paxCargo,
      vehicle = result.vehicle, vehicles = result.vehicle != null ? [result.vehicle] : [],
      trains = 0, trains0 = 0, vehCount = 0, predTrains = 0,
      predicted = 0, predRevenue = 0, predRunning = 0, predAmort = 0,
      createdSourceStop = createdSource,
      createdDepot = ("newDepot" in plan) && plan.newDepot,
      newRoadEdges = ("newRoadEdges" in plan) ? plan.newRoadEdges : [],
      newDepotStubBuilt = ("newDepotStubBuilt" in plan)
          && plan.newDepotStubBuilt,
      depotFront = ("depotFront" in plan) ? plan.depotFront : -1,
      buildDate = AIDate.GetCurrentDate(), year = year,
      lineId = owner._nextLineId };
  /* A recovery record may already exist: it is installed BEFORE the first
   * native mutation and refreshed as the transaction progresses. Never
   * publish duplicate records for one construction attempt. */
  if (("recoveryTicket" in plan) && plan.recoveryTicket != null) {
    local existing = plan.recoveryTicket;
    ticket.lineId = existing.lineId;
    foreach (key, value in ticket) existing[key] = value;
    owner._saveProjection = null;
    return existing;
  }
  owner._lines.append(ticket);
  plan.pendingLineId <- ticket.lineId;
  plan.recoveryTicket <- ticket;
  owner._nextLineId++;
  owner._saveProjection = null;
  owner._c76BumpLayer("lines", false);
  if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_RECOVERY", "mode=road line="
      + (owner._nextLineId - 1) + " town=" + plan.townId
      + " vehicle=" + result.vehicle);
  return ticket;
}

function OpexAirportFeederRecover(owner)
{
  local pending = false;
  for (local i = owner._lines.len() - 1; i >= 0; i--) {
    local line = owner._lines[i];
    if (!("purpose" in line) || line.purpose != "airport_feeder_recovery") continue;
    local v = ("vehicle" in line) ? line.vehicle : null;
    if (v != null && AIVehicle.IsValidVehicle(v)) {
      /* Vehicle IDs are recycled in OpenTTD. A stale ticket must NEVER
       * sell another line's bus after Load or change of opt-in settings. */
      local ours = AIVehicleList();
      if (!ours.HasItem(v)
          || AIVehicle.GetVehicleType(v) != AIVehicle.VT_ROAD
          || !("recoveryEngine" in line) || line.recoveryEngine < 0
          || AIVehicle.GetEngineType(v) != line.recoveryEngine) {
        pending = true;
        if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_RECOVERY",
            "mode=road action=blocked reason=vehicle_identity line=" + line.lineId);
        continue;
      }
      local assignedElsewhere = false;
      foreach (other in owner._lines) {
        if (other == null || other == line) continue;
        if (("vehicle" in other) && other.vehicle == v) assignedElsewhere = true;
        if (("vehicles" in other) && other.vehicles != null)
          foreach (known in other.vehicles)
            if (known == v) assignedElsewhere = true;
      }
      if (assignedElsewhere) {
        pending = true;
        continue;
      }
      if (!AIVehicle.IsStoppedInDepot(v)) {
        AIVehicle.SendVehicleToDepot(v);
        pending = true;
        continue;
      }
      if (!AIVehicle.SellVehicle(v)) { pending = true; continue; }
    }
    if (("createdSourceStop" in line) && line.createdSourceStop) {
      /* A delayed station demolition is safe only if it is still our
       * original isolated source and no vehicle is visiting it. */
      local source = ("sourceStopTile" in line) ? line.sourceStopTile : -1;
      if (AIMap.IsValidTile(source) && AIRoad.IsRoadStationTile(source)) {
        local sid = AIStation.GetStationID(source);
        local expected = ("sourceStationId" in line) ? line.sourceStationId : -1;
        /* If Save happened between BuildRoadStation and journal update,
         * the identity was never certified. Retain the bay: guessing from
         * tile coordinates could destroy a station now owned by others. */
        if (expected < 0) {
          if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_RECOVERY",
              "mode=road action=source_retained reason=unknown_station_identity"
              + " line=" + line.lineId);
        } else if (!AICompany.IsMine(AITile.GetOwner(source))
            || sid != expected
            || sid == AIStation.GetStationID(line.stationB)
            || AIVehicleList_Station(sid).Count() != 0
            || !AIRoad.RemoveRoadStation(source)) {
          pending = true;
          continue;
        }
        OpexAir0310InvalidateSiteValidity();
      }
      line.createdSourceStop = false;
      owner._saveProjection = null;
    }
    /* A route/depot may have become shared since this transaction failed.
     * We cannot prove exclusivity from a historical list of new edges.
     * Retain those assets rather than demolish another service's access.
     * Immediate, synchronous failure still uses the precise rollback. */
    if ((("createdDepot" in line) && line.createdDepot)
        || (("newRoadEdges" in line) && line.newRoadEdges != null
            && line.newRoadEdges.len() > 0)) {
      if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_RECOVERY",
          "mode=road action=infrastructure_retained line=" + line.lineId
          + " depot=" + ((("createdDepot" in line) && line.createdDepot) ? 1 : 0)
          + " edges=" + (("newRoadEdges" in line) && line.newRoadEdges != null
              ? line.newRoadEdges.len() : 0));
    }
    owner._lines.remove(i);
    owner._saveProjection = null;
    owner._c76BumpLayer("lines", false);
  }
  return pending;
}

function OpexAirportFeederRoadFronts(tile, roadType)
{
  local fronts = [];
  local x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
  local dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (d in dirs) {
    local xx = x + d[0], yy = y + d[1];
    if (xx < 1 || yy < 1 || xx >= AIMap.GetMapSizeX() - 1
        || yy >= AIMap.GetMapSizeY() - 1) continue;
    local front = AIMap.GetTileIndex(xx, yy);
    if (AIRoad.IsRoadTile(front) && AIRoad.HasRoadType(front, roadType))
      fronts.append(front);
  }
  return fronts;
}

function OpexAirportFeederFindNewSourcePlan(catalog, lines)
{
  PAX_AIR_FEEDER_SITING_DIAG = { activeHub = 0, joinedBus = 0,
      quotaTown = 0, sitePax = 0, siteLegal = 0,
      stubLegal = 0, stopLegal = 0, stubRejected = 0,
      stopRejected = 0,
      nearDepot = 0, routeChecked = 0, newDepotChecked = 0,
      newDepotFound = 0 };
  PAX_AIR_FEEDER_DEPOT_DIAG = { attempts = 0, noFront = 0,
      noConnectedPath = 0, noDepotSite = 0, found = 0 };
  PAX_AIR_FEEDER_CONNECTOR_DIAG = { tested = 0, extraProbed = 0, invalid = 0,
      unbuildable = 0, depotMissing = 0, found = 0 };
  if (!PAX_AIR_FIRST_FEEDER_ONLY || catalog == null
      || catalog.roadType != AIRoad.ROADTYPE_ROAD
      || catalog.paxCargo < 0) return null;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local ownedAirTowns = OpexAirportFeederOwnAirTowns();
  local hubs = AIStationList(AIStation.STATION_AIRPORT);
  local towns = AITownList();
  local depots = AIDepotList(AITile.TRANSPORT_ROAD);
  /* Evaluate municipal capacity ONCE per source town, not once per AIR hub.
   * On 256^2 maps the former nested hub x town certification exhausted the
   * scheduler slice before the new-source scanner reached a plausible pair.
   * All finalists are independently re-certified at the build tick. */
  local saturatedTowns = [];
  for (local t = towns.Begin(); !towns.IsEnd(); t = towns.Next()) {
    if (t in ownedAirTowns || !OpexAirportFeederCertified(t, null)) continue;
    local loc = AITown.GetLocation(t);
    if (AIMap.IsValidTile(loc))
      saturatedTowns.append({ id = t, center = loc });
  }
  if (saturatedTowns.len() == 0) return null;
  local possibleSites = 0, fullChecks = 0;
  /* Four of 32 physical source road faces per month: repeated probes of the
   * same obstructed geometry never create a route. Cap expensive checks and
   * leave opcode headroom for the rest of the scheduler. */
  local slotMonth = AIDate.GetYear(AIDate.GetCurrentDate()) * 12
      + AIDate.GetMonth(AIDate.GetCurrentDate());
  local slotStart = (slotMonth % 8) * 4;
  local hubOrder = [];
  for (local hub = hubs.Begin(); !hubs.IsEnd(); hub = hubs.Next()) {
    hubOrder.append(hub);
  }
  local skipHubs = hubOrder.len() > 0 ? slotMonth % hubOrder.len() : 0;
  for (local hi = 0; hi < hubOrder.len(); hi++) {
    /* The refleet task may start with <24k ops after other scheduled work.
     * A 24k floor starved ALL feeder scans in the measured 4y smoke.
     * Keep a small emergency reserve instead of disabling the feature. */
    if (AIController.GetOpsTillSuspend() < 4000) return null;
    /* Circular rotation: do not silently discard earlier hubs in the list. */
    local hub = hubOrder[(hi + skipHubs) % hubOrder.len()];
    if (!AIStation.IsValidStation(hub)) continue;
    local airports = AITileList_StationType(hub, AIStation.STATION_AIRPORT);
    local airport = -1;
    for (local tile = airports.Begin(); !airports.IsEnd(); tile = airports.Next()) {
      if (AIAirport.IsAirportTile(tile)) { airport = tile; break; }
    }
    if (!AIMap.IsValidTile(airport)
        || OpexAirportFeederParent(lines, hub, catalog.paxCargo) < 0) continue;
    PAX_AIR_FEEDER_SITING_DIAG.activeHub++;
    local hubStops = AITileList_StationType(hub, AIStation.STATION_BUS_STOP);
    for (local hubStop = hubStops.Begin(); !hubStops.IsEnd(); hubStop = hubStops.Next()) {
      if (!AIRoad.IsRoadStationTile(hubStop)
          || !AIRoad.IsDriveThroughRoadStationTile(hubStop)) continue;
      PAX_AIR_FEEDER_SITING_DIAG.joinedBus++;
      foreach (sourceTown in saturatedTowns) {
        local town = sourceTown.id;
        local center = sourceTown.center;
        if (AIMap.DistanceManhattan(center, hubStop) > 32) continue;
        PAX_AIR_FEEDER_SITING_DIAG.quotaTown++;
        local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
        for (local dx = -5; dx <= 5; dx++) {
          for (local dy = -5; dy <= 5; dy++) {
            local xx = cx + dx, yy = cy + dy;
            if (xx <= 1 || yy <= 1 || xx >= AIMap.GetMapSizeX() - 2
                || yy >= AIMap.GetMapSizeY() - 2) continue;
            local stop = AIMap.GetTileIndex(xx, yy);
            if (AITile.GetClosestTown(stop) != town || !AITile.IsBuildable(stop)
                || AIMap.DistanceManhattan(stop, hubStop) > 32) continue;
            if (AITile.GetCargoProduction(stop, catalog.paxCargo, 1, 1,
                    AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP)) <= 0)
              continue;
            PAX_AIR_FEEDER_SITING_DIAG.sitePax++;
            foreach (front in OpexAirportFeederRoadFronts(stop, catalog.roadType)) {
              possibleSites++;
              if (possibleSites > 32) return null;
              if (possibleSites <= slotStart || possibleSites > slotStart + 4)
                continue;
              if (AIController.GetOpsTillSuspend() < 4000) return null;
              local stubOk = false, stopOk = false;
              {
                local test = AITestMode();
                /* Same mandatory entrance stub as the reviewed regular ROAD
                 * builder: CmdBuildRoadStation itself does NOT add the road
                 * bit from front into the stop (August frozen regression). */
                stubOk = AIRoad.BuildRoad(front, stop);
                stopOk = AIRoad.BuildRoadStation(stop, front,
                    AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
                /* AITestMode does NOT mutate the real map; testing physical
                 * connectivity here would reject every valid empty site.
                 * Mandatory connection postconditions run after REAL build. */
              }
              if (stubOk) PAX_AIR_FEEDER_SITING_DIAG.stubLegal++;
              else PAX_AIR_FEEDER_SITING_DIAG.stubRejected++;
              if (stopOk) PAX_AIR_FEEDER_SITING_DIAG.stopLegal++;
              else PAX_AIR_FEEDER_SITING_DIAG.stopRejected++;
              if (!stubOk || !stopOk) continue;
              PAX_AIR_FEEDER_SITING_DIAG.siteLegal++;
              for (local depot = depots.Begin(); !depots.IsEnd(); depot = depots.Next()) {
                if (!AIRoad.IsRoadDepotTile(depot)
                    || AIMap.DistanceManhattan(depot, stop) > 24) continue;
                PAX_AIR_FEEDER_SITING_DIAG.nearDepot++;
                fullChecks++;
                PAX_AIR_FEEDER_SITING_DIAG.routeChecked++;
                if (fullChecks > 4) return null;
                /* Check both directions BEFORE altering an empty source tile. */
                if (!OpexAirportFeederRoadReachable(front, hubStop,
                        catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS)
                    || !OpexAirportFeederRoadReachable(hubStop, front,
                        catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS)
                    || !OpexAirportFeederRoadReachable(depot, front,
                        catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS)
                    || !OpexAirportFeederRoadReachable(front, depot,
                        catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS)) continue;
                return { townId = town, airportTile = airport,
                    sourceStop = stop, hubStop = hubStop, depot = depot,
                    sourceFront = front };
              }
              /* The most frequent measured blocker is 0 nearby depots.
               * Reuse the reviewed OpexRoadFindDepot geometry to propose a
               * NEW physical depot on an existing connected road path.
               * Max four potentially expensive tests per monthly scan. */
              if (PAX_AIR_FEEDER_SITING_DIAG.newDepotChecked < 4) {
                PAX_AIR_FEEDER_SITING_DIAG.newDepotChecked++;
                local newD = OpexAirportFeederFindDepotOnExistingRoad(
                    stop, front, hubStop, catalog.roadType);
                if (newD != null) {
                  PAX_AIR_FEEDER_SITING_DIAG.newDepotFound++;
                  return { townId = town, airportTile = airport,
                      sourceStop = stop, hubStop = hubStop,
                      sourceFront = front, depot = newD.tile,
                      depotFront = newD.front, newDepot = true };
                }
                /* A missing existing road was proven by the path probe.
                 * This SECOND path physically constructs a capped L route.
                 * It is never a speculative proximity-only connection. */
                local newLink = OpexAirportFeederFindRoadConnector(
                    stop, front, hubStop, catalog.roadType);
                if (newLink != null) {
                  PAX_AIR_FEEDER_SITING_DIAG.newDepotFound++;
                  return { townId = town, airportTile = airport,
                      sourceStop = stop, hubStop = hubStop,
                      sourceFront = front, depot = newLink.depot,
                      depotFront = newLink.depotFront, newDepot = true,
                      newRoad = true, routeTrace = newLink.routeTrace };
                }
              }
            }
          }
        }
      }
    }
  }
  return null;
}

function OpexAirportFeederTryNewSource(owner, year)
{
  if (!PAX_AIR_FIRST_FEEDER_ONLY || owner == null) return false;
  local plan = OpexAirportFeederFindNewSourcePlan(owner._catalog, owner._lines);
  if (plan == null) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_SCAN", "mode=road source=new result=none"
        + " active_hub=" + PAX_AIR_FEEDER_SITING_DIAG.activeHub
        + " joined_bus=" + PAX_AIR_FEEDER_SITING_DIAG.joinedBus
        + " quota_town=" + PAX_AIR_FEEDER_SITING_DIAG.quotaTown
        + " site_pax=" + PAX_AIR_FEEDER_SITING_DIAG.sitePax
        + " site_legal=" + PAX_AIR_FEEDER_SITING_DIAG.siteLegal
        + " stub_legal=" + PAX_AIR_FEEDER_SITING_DIAG.stubLegal
        + " stop_legal=" + PAX_AIR_FEEDER_SITING_DIAG.stopLegal
        + " stub_rejected=" + PAX_AIR_FEEDER_SITING_DIAG.stubRejected
        + " stop_rejected=" + PAX_AIR_FEEDER_SITING_DIAG.stopRejected
        + " near_depot=" + PAX_AIR_FEEDER_SITING_DIAG.nearDepot
        + " checked=" + PAX_AIR_FEEDER_SITING_DIAG.routeChecked
        + " new_depot_checked=" + PAX_AIR_FEEDER_SITING_DIAG.newDepotChecked
        + " new_depot_found=" + PAX_AIR_FEEDER_SITING_DIAG.newDepotFound
        + " path_missing=" + PAX_AIR_FEEDER_DEPOT_DIAG.noConnectedPath
        + " no_depot_site=" + PAX_AIR_FEEDER_DEPOT_DIAG.noDepotSite
        + " no_front=" + PAX_AIR_FEEDER_DEPOT_DIAG.noFront
        + " route_tested=" + PAX_AIR_FEEDER_CONNECTOR_DIAG.tested
        + " route_extra_probed=" + PAX_AIR_FEEDER_CONNECTOR_DIAG.extraProbed
        + " route_unbuildable=" + PAX_AIR_FEEDER_CONNECTOR_DIAG.unbuildable
        + " route_depot_missing=" + PAX_AIR_FEEDER_CONNECTOR_DIAG.depotMissing
        + " route_found=" + PAX_AIR_FEEDER_CONNECTOR_DIAG.found);
    return false;
  }
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local stationCost = AIRoad.GetBuildCost(owner._catalog.roadType, AIRoad.BT_BUS_STOP);
  local engine = (owner._catalog.paxCargo in owner._catalog.roadEngineByCargo)
      ? owner._catalog.roadEngineByCargo[owner._catalog.paxCargo] : null;
  if (engine == null || !("id" in engine)) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_BUILD", "stage=engine result=missing town=" + plan.townId);
    return false;
  }
  local busPrice = AIEngine.GetPrice(engine.id);
  local newDepotCost = (("newDepot" in plan) && plan.newDepot)
      ? AIRoad.GetBuildCost(owner._catalog.roadType, AIRoad.BT_DEPOT) : 0;
  local newRoadCost = (("newRoad" in plan) && plan.newRoad)
      ? plan.routeTrace.len() * 2 * AIRoad.GetBuildCost(
          owner._catalog.roadType, AIRoad.BT_ROAD) : 0;
  local sourceStubCost = 2 * AIRoad.GetBuildCost(
      owner._catalog.roadType, AIRoad.BT_ROAD);
  if (stationCost <= 0 || busPrice <= 0 || newDepotCost < 0
      || newRoadCost < 0 || sourceStubCost <= 0
      || busPrice > OPEX_AIRPORT_FEEDER_MAX_SPEND
      || cash < stationCost + busPrice + newDepotCost + newRoadCost
          + sourceStubCost
          + OPEX_AIRPORT_FEEDER_MIN_RESERVE) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_BUILD", "stage=budget town="
        + plan.townId + " cash=" + cash + " need="
        + (stationCost + busPrice + newDepotCost + newRoadCost
            + sourceStubCost
            + OPEX_AIRPORT_FEEDER_MIN_RESERVE));
    return false;
  }
  AIRoad.SetCurrentRoadType(owner._catalog.roadType);
  /* PRE-COMMIT: this hub-anchored line is saved even if OpenTTD suspends or
   * reloads after any of the following native construction commands. */
  plan.newRoadEdges <- [];
  OpexAirportFeederRecordRecovery(owner, plan,
      { vehicle = null }, year, true);
  /* A bay's declared front direction is not a physical connection. Install
   * the missing road bit while the source tile is STILL EMPTY; only then
   * place the stop and verify the real OpenTTD road-station connection. */
  local builtStub = AIRoad.BuildRoad(plan.sourceFront, plan.sourceStop);
  /* Record the NEW edge immediately after the native command succeeds:
   * even a failed connectivity postcondition may have changed road bits. */
  if (builtStub) {
    /* Keep the SAME array referenced by the pre-commit recovery record. */
    plan.newRoadEdges.append(
        { from = plan.sourceFront, to = plan.sourceStop });
    owner._saveProjection = null;
  }
  if (!builtStub || !AIRoad.AreRoadTilesConnected(
          plan.sourceFront, plan.sourceStop)) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_BUILD", "stage=source_stub failed town=" + plan.townId);
    if (builtStub && !OpexAirportFeederRollbackRoadEdges(plan.newRoadEdges))
      OpexAirportFeederRecordRecovery(owner, plan,
          { vehicle = null }, year, false);
    return false;
  }
  local builtSource = AIRoad.BuildRoadStation(plan.sourceStop, plan.sourceFront,
      AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
  if (!builtSource || !AIRoad.IsRoadStationTile(plan.sourceStop)
      || AIRoad.GetRoadStationFrontTile(plan.sourceStop) != plan.sourceFront
      || !AIRoad.AreRoadTilesConnected(plan.sourceStop, plan.sourceFront)) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_BUILD", "stage=source_station_or_link failed town=" + plan.townId);
    local clearedSource = !AIRoad.IsRoadStationTile(plan.sourceStop)
        || AIRoad.RemoveRoadStation(plan.sourceStop);
    local clearedStub = OpexAirportFeederRollbackRoadEdges(plan.newRoadEdges);
    if (!clearedSource || !clearedStub)
      OpexAirportFeederRecordRecovery(owner, plan,
          { vehicle = null }, year, true);
    OpexAir0310InvalidateSiteValidity();
    return false;
  }
  OpexAir0310InvalidateSiteValidity();
  if (("newRoad" in plan) && plan.newRoad) {
    local added = plan.newRoadEdges;
    local okRoute = OpexRoadBuildTrace(plan.routeTrace, added);
    if (!okRoute || !OpexAirportFeederRoadReachable(plan.sourceStop,
            plan.hubStop, owner._catalog.roadType,
            OPEX_AIRPORT_FEEDER_MAX_BFS)
        || !OpexAirportFeederRoadReachable(plan.hubStop,
            plan.sourceStop, owner._catalog.roadType,
            OPEX_AIRPORT_FEEDER_MAX_BFS)) {
      if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_BUILD", "stage=road_path failed town="
          + plan.townId + " built_edges=" + added.len() + " trace=" + plan.routeTrace.len());
      local clearedStop = AIRoad.RemoveRoadStation(plan.sourceStop);
      local clearedRoad = OpexAirportFeederRollbackRoadEdges(added);
      if (!clearedStop || !clearedRoad)
        OpexAirportFeederRecordRecovery(owner, plan,
            { vehicle = null }, year, true);
      OpexAir0310InvalidateSiteValidity();
      return false;
    }
  }
  if (("newDepot" in plan) && plan.newDepot
      && !OpexAirportFeederBuildDepot(plan, owner._catalog.roadType, owner)) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_BUILD", "stage=depot failed town=" + plan.townId);
    local clearedStop = AIRoad.RemoveRoadStation(plan.sourceStop);
    local clearedRoad = !("newRoadEdges" in plan)
        || OpexAirportFeederRollbackRoadEdges(plan.newRoadEdges);
    if (!clearedStop || !clearedRoad
        || (("newDepotCleanupPending" in plan) && plan.newDepotCleanupPending)) {
      OpexAirportFeederRecordRecovery(owner, plan,
          { vehicle = null }, year, true);
    }
    OpexAir0310InvalidateSiteValidity();
    return false;
  }
  local r = OpexAirportFeederBuild(owner._catalog, owner._lines, plan,
      OpexAirportFeederTownSlotProof, true);
  if (r.ok) return OpexAirportFeederRegisterBuilt(owner, plan, r, year, true);
  if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_BUILD", "stage=bus failed town="
      + plan.townId + " reason=" + r.reason);
  if (r.reason == "PENDING_SELL" && r.vehicle != null
      && AIVehicle.IsValidVehicle(r.vehicle)) {
    OpexAirportFeederRecordRecovery(owner, plan, r, year, true);
    return false;
  }
  /* The newly built bay is an isolated STATION_NEW on a formerly EMPTY tile;
   * no road or airport was replaced. Remove ONLY our new unused station. */
  local cleanedStop = AIRoad.RemoveRoadStation(plan.sourceStop);
  local cleanedDepot = !("newDepot" in plan) || !plan.newDepot
      || OpexAirportFeederRollbackDepot(plan);
  local cleanedRoad = !("newRoadEdges" in plan)
      || OpexAirportFeederRollbackRoadEdges(plan.newRoadEdges);
  if (!cleanedStop || !cleanedDepot || !cleanedRoad)
    OpexAirportFeederRecordRecovery(owner, plan, r, year, true);
  OpexAir0310InvalidateSiteValidity();
  return false;
}
