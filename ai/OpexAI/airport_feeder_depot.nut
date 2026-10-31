/* BUS->AIR feeder: real NEW depot on an existing, proven road path.
 * OpexRoadFindDepot is the already-reviewed layout: it checks BOTH the
 * missing perpendicular road stub and depot under AITestMode. Without the
 * stub OpenTTD may build a depot whose bus cannot enter the road at all.
 * Only the single new depot and its single new spur can be rolled back.
 */
PAX_AIR_FEEDER_DEPOT_DIAG <- {};

function OpexAirportFeederFindDepotOnExistingRoad(sourceStop, sourceFront,
                                                 hubStop, roadType)
{
  if (!("attempts" in PAX_AIR_FEEDER_DEPOT_DIAG))
    PAX_AIR_FEEDER_DEPOT_DIAG = { attempts = 0, noFront = 0,
        noConnectedPath = 0, noDepotSite = 0, found = 0 };
  PAX_AIR_FEEDER_DEPOT_DIAG.attempts++;
  if (sourceStop == null || hubStop == null || sourceFront == null
      || !AIMap.IsValidTile(sourceStop) || !AIMap.IsValidTile(hubStop)
      || !AIMap.IsValidTile(sourceFront)) return null;
  AIRoad.SetCurrentRoadType(roadType);
  local hubFront = OpexAirportFeederRoadFront(hubStop);
  if (hubFront == null || !AIRoad.IsRoadTile(sourceFront)
      || !AIRoad.IsRoadTile(hubFront)) {
    PAX_AIR_FEEDER_DEPOT_DIAG.noFront++;
    return null;
  }
  /* A real connected road, not a Manhattan/straight-line proposal. */
  local edges = OpexRoadBfsPath(sourceFront, hubFront, 128);
  if (edges == null || edges.len() < 3) {
    PAX_AIR_FEEDER_DEPOT_DIAG.noConnectedPath++;
    return null;
  }
  local depot = OpexRoadFindDepot(edges,
      { tile = sourceStop, front = sourceFront },
      { tile = hubStop, front = hubFront }, true);
  if (depot == null || !AIMap.IsValidTile(depot.tile)
      || !AIMap.IsValidTile(depot.front)
      || !AITile.IsBuildable(depot.tile)
      || !AIRoad.IsRoadTile(depot.front)
      || !AIRoad.HasRoadType(depot.front, roadType)) {
    PAX_AIR_FEEDER_DEPOT_DIAG.noDepotSite++;
    return null;
  }
  PAX_AIR_FEEDER_DEPOT_DIAG.found++;
  return depot;
}

/* Retry another real depot site when traffic blocks the one selected in
 * AITestMode. The new source stop and route are already physically built,
 * so both candidates must use the CURRENT connected road graph. At most
 * two extra depot sites are considered by the calling transaction. */
function OpexAirportFeederAlternateDepot(plan, roadType, excludedSites,
                                        excludedFronts)
{
  if (plan == null || !("sourceStop" in plan)
      || !("sourceFront" in plan) || !("hubStop" in plan)
      || !AIMap.IsValidTile(plan.sourceStop)
      || !AIMap.IsValidTile(plan.sourceFront)
      || !AIMap.IsValidTile(plan.hubStop)) return null;
  AIRoad.SetCurrentRoadType(roadType);
  local hubFront = OpexAirportFeederRoadFront(plan.hubStop);
  if (hubFront == null) return null;
  local edges = OpexRoadBfsPath(plan.sourceFront, hubFront, 128);
  if (edges == null || edges.len() < 3) return null;
  local nextDepot = OpexRoadFindDepot(edges,
      { tile = plan.sourceStop, front = plan.sourceFront },
      { tile = plan.hubStop, front = hubFront }, true,
      excludedSites, excludedFronts);
  if (nextDepot == null || !AIMap.IsValidTile(nextDepot.tile)
      || !AIMap.IsValidTile(nextDepot.front)
      || !AITile.IsBuildable(nextDepot.tile)
      || !AIRoad.IsRoadTile(nextDepot.front)
      || !AIRoad.HasRoadType(nextDepot.front, roadType))
    return null;
  return nextDepot;
}

/* Returns true exclusively for a physically connected depot, never for
 * an unproven successful BuildRoadDepot command. No airport is touched. */
function OpexAirportFeederBuildDepot(plan, roadType, owner = null)
{
  if (plan == null || !("newDepot" in plan) || !plan.newDepot
      || !("depot" in plan) || !("depotFront" in plan)
      || !AIMap.IsValidTile(plan.depot)
      || !AIMap.IsValidTile(plan.depotFront)
      || !AITile.IsBuildable(plan.depot)
      || !AIRoad.IsRoadTile(plan.depotFront)) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_DEPOT",
        "stage=precheck result=failed"
        + " plan=" + (plan == null ? "null" : "present")
        + " depot_valid=" + (plan != null && ("depot" in plan)
            && AIMap.IsValidTile(plan.depot) ? 1 : 0)
        + " front_valid=" + (plan != null && ("depotFront" in plan)
            && AIMap.IsValidTile(plan.depotFront) ? 1 : 0)
        + " depot_buildable=" + (plan != null && ("depot" in plan)
            && AIMap.IsValidTile(plan.depot)
            && AITile.IsBuildable(plan.depot) ? 1 : 0));
    return false;
  }
  AIRoad.SetCurrentRoadType(roadType);
  local excludedSites = {};
  local excludedFronts = {};
  for (local attempt = 0; attempt < 3; attempt++) {
    /* Never remove an old attempt's stub while cleaning up the new site. */
    plan.newDepotStubBuilt <- false;
    local failure = 0;
    local stubConnected = false, depotBuilt = false;
    local depotTile = false, frontCorrect = false, depotConnected = false;
    if (AIRoad.AreRoadTilesConnected(plan.depotFront, plan.depot)) {
      if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_DEPOT",
          "stage=stub result=already_connected attempt=" + attempt);
    } else {
      local builtStub = AIRoad.BuildRoad(plan.depotFront, plan.depot);
      failure = builtStub ? 0 : AIError.GetLastError();
      if (!builtStub && failure == AIError.ERR_VEHICLE_IN_THE_WAY) {
        /* AITest cannot reserve a busy road frontage. One tick, then
         * choose another depot rather than retrying this site indefinitely. */
        if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_DEPOT",
            "stage=stub action=defer_one_tick error=vehicle_in_the_way");
        AIController.Sleep(1);
        if (AIMap.IsValidTile(plan.depot)
            && AIMap.IsValidTile(plan.depotFront)
            && AITile.IsBuildable(plan.depot)
            && AIRoad.IsRoadTile(plan.depotFront)
            && !AIRoad.AreRoadTilesConnected(plan.depotFront, plan.depot)) {
          builtStub = AIRoad.BuildRoad(plan.depotFront, plan.depot);
          failure = builtStub ? 0 : AIError.GetLastError();
        }
      }
      if (builtStub) {
        plan.newDepotStubBuilt <- true;
        if (("recoveryTicket" in plan) && plan.recoveryTicket != null)
          plan.recoveryTicket.newDepotStubBuilt = true;
        if (owner != null) owner._saveProjection = null;
        stubConnected = AIRoad.AreRoadTilesConnected(plan.depotFront, plan.depot);
        if (stubConnected) {
          depotBuilt = AIRoad.BuildRoadDepot(plan.depot, plan.depotFront);
          if (!depotBuilt) failure = AIError.GetLastError();
          depotTile = depotBuilt && AIRoad.IsRoadDepotTile(plan.depot);
          frontCorrect = depotTile
              && AIRoad.GetRoadDepotFrontTile(plan.depot) == plan.depotFront;
          depotConnected = frontCorrect
              && AIRoad.AreRoadTilesConnected(plan.depot, plan.depotFront);
        }
      }
    }
    if (depotConnected) return true;
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_DEPOT",
        "stage=postcondition result=failed attempt=" + attempt
        + " stub_connected=" + (stubConnected ? 1 : 0)
        + " depot_built=" + (depotBuilt ? 1 : 0)
        + " depot_tile=" + (depotTile ? 1 : 0)
        + " front_correct=" + (frontCorrect ? 1 : 0)
        + " error=" + failure);
    if (("newDepotStubBuilt" in plan) && plan.newDepotStubBuilt
        && !OpexAirportFeederRollbackDepot(plan)) {
      plan.newDepotCleanupPending <- true;
      return false;
    }
    if (("recoveryTicket" in plan) && plan.recoveryTicket != null)
      plan.recoveryTicket.newDepotStubBuilt = false;
    if (owner != null) owner._saveProjection = null;
    excludedSites.rawset(plan.depot, true);
    /* A bus blocking the road frontage can obstruct ALL adjacent depot
     * tiles. Skip that frontage as well instead of retrying beside it. */
    if (failure == AIError.ERR_VEHICLE_IN_THE_WAY)
      excludedFronts.rawset(plan.depotFront, true);
    if (attempt >= 2) break;
    local alternate = OpexAirportFeederAlternateDepot(
        plan, roadType, excludedSites, excludedFronts);
    if (alternate == null) break;
    plan.depot = alternate.tile;
    plan.depotFront = alternate.front;
    /* Update the pre-commit ticket BEFORE the next native mutation.
     * Save/Load must never try to repair the previous failed site. */
    if (("recoveryTicket" in plan) && plan.recoveryTicket != null) {
      plan.recoveryTicket.depot = plan.depot;
      plan.recoveryTicket.depotFront = plan.depotFront;
      plan.recoveryTicket.newDepotStubBuilt = false;
    }
    if (owner != null) owner._saveProjection = null;
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_DEPOT",
        "stage=alternate attempt=" + (attempt + 1));
  }
  return false;
}

/* Call ONLY for depot plans explicitly created by this feeder. The road spur
 * consists of a formerly non-existent single edge ending at a previously
 * buildable empty tile. Never remove adjacent existing road segments. */
function OpexAirportFeederRollbackDepot(plan)
{
  if (plan == null || !("newDepot" in plan) || !plan.newDepot
      || !("depot" in plan) || !("depotFront" in plan)
      || !AIMap.IsValidTile(plan.depot)
      || !AIMap.IsValidTile(plan.depotFront)) return false;
  if (AIRoad.IsRoadDepotTile(plan.depot)) {
    if (!AICompany.IsMine(AITile.GetOwner(plan.depot))
        || !AIRoad.RemoveRoadDepot(plan.depot)) return false;
  }
  /* If the build changed the front's directional bit, this removes only
   * the new spur, not the through-road or third-party infrastructure. */
  /* The depot removal has emptied its tile. AreRoadTilesConnected now returns
   * false even if the perpendicular road bit on front is STILL present.
   * Thus remove the reviewed spur unconditionally whenever BuildRoad succeeded
   * (same sequence as OpexRoadRollback, never another existing road edge). */
  if (("newDepotStubBuilt" in plan) && plan.newDepotStubBuilt) {
    if (!AIRoad.RemoveRoad(plan.depotFront, plan.depot)) return false;
    plan.newDepotStubBuilt = false;
    return true;
  }
  return true;
}
