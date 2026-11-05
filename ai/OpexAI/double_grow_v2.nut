/* DOUBLE-GROW v2: deferred, low-priority upgrade of an existing profitable
 * single-track freight service. V190 physical retrofit is delegated to
 * OpexDoubleGrowV2Build, which may reject an unsafe existing route.
 * This selector never starts a second _railSearch or cancels a line. */
DOUBLE_GROW_V2_CURSOR <- 0;

function OpexDoubleGrowV2Log(line, action, reason, waiting)
{
  if (DECISION_LOG) OpexDecide("DOUBLE_GROW", "version=2 action=" + action
      + " line=" + line.lineId + " reason=" + reason + " waiting=" + waiting
      + " trains=" + line.trains);
}

/* Admission on the actual bank balance, not an arbitrary wealth tier.
 * Before A* the full second route is unknown: quote the existing route as
 * a lower-bound planning estimate; the builder reprices the discovered path
 * and requires a 50k reserve before touching the map. */
function OpexDoubleGrowV2AdmissionQuote(owner, line)
{
  local route = OpexDoubleGrowPrimaryRoute(line);
  if (route == null || route.len() < 3) return -1;
  local railType = AIRail.GetRailType(line.depot);
  local tileCost = AIRail.GetBuildCost(railType, AIRail.BT_TRACK);
  if (tileCost <= 0) return -1;
  local padCost = ("platformLength" in line) ?
      2 * line.platformLength * owner._catalog.costStation : 0;
  local trainCost = 0;
  if ("vehicles" in line && line.vehicles != null && line.vehicles.len() > 0) {
    local sample = line.vehicles[0];
    if (AIVehicle.IsValidVehicle(sample)) {
      for (local i = 0; i < AIVehicle.GetNumWagons(sample); i++) {
        local engine = AIVehicle.GetWagonEngineType(sample, i);
        if (AIEngine.IsBuildable(engine)) trainCost += AIEngine.GetPrice(engine);
      }
    }
  }
  return route.len() * tileCost + padCost
      + AIRail.GetBuildCost(railType, AIRail.BT_DEPOT) + trainCost + 50000;
}

/* A ready project has priority. The ranked best portfolio is not a queue:
 * it contains already rejected / unbuildable candidates (too_close_no_join,
 * ABND), and checking merely affordable entries here starved upgrades even
 * while the true rail-search slot was idle for months. Actual project work
 * is guarded by _railSearch/_activeWorker/_railExpansion in the selector;
 * PO01C is another explicit pending construction intent. */
function OpexDoubleGrowV2PrimaryPending(owner)
{
  return owner != null && owner._po01cPending;
}

function OpexDoubleGrowV2Select(owner, year)
{
  if (!DOUBLE_GROW_V2 || !MODE_RAIL || !SAVE_FULL_STATE || owner == null
      || owner._lines == null || owner._catalog == null || owner._lines.len() == 0)
    return false;

  /* A funded main project can pause a resumable secondary A* without
   * destroying the pathfinder or its spent iteration budget. */
  local principalBusy = owner._railSearch != null || owner._activeWorker != null
      || owner._railExpansion != null || owner._v257Pending != null
      || owner._v271Pending != null || owner._railLongV2Pending != null
      || OpexV284Busy(owner) || OpexDoubleGrowV2PrimaryPending(owner);
  if (owner._doubleGrowV2State != null) {
    if (principalBusy) {
      if (!("pauseLogged" in owner._doubleGrowV2State)
          || !owner._doubleGrowV2State.pauseLogged) {
        owner._doubleGrowV2State.rawset("pauseLogged", true);
        if (DECISION_LOG) OpexDecide("DOUBLE_GROW",
            "version=2 action=pause reason=principal_busy"
            + " spent=" + owner._doubleGrowV2State.spent);
      }
      return false;
    }
    if (("pauseLogged" in owner._doubleGrowV2State)
        && owner._doubleGrowV2State.pauseLogged) {
      owner._doubleGrowV2State.pauseLogged = false;
      if (DECISION_LOG) OpexDecide("DOUBLE_GROW",
          "version=2 action=resume spent=" + owner._doubleGrowV2State.spent);
    }
    local result = OpexDoubleGrowV2Continue(owner);
    if (result.status == "built") return true;
    return false;
  }
  if (principalBusy) return false;

  local count = owner._lines.len();
  local now = AIDate.GetCurrentDate();
  local scan = min(count, 12);
  for (local i = 0; i < scan; i++) {
    local line = owner._lines[(DOUBLE_GROW_V2_CURSOR + i) % count];
    if (line == null || !("lineId" in line) || !("mode" in line)
        || line.mode != "rail" || !("kind" in line) || line.kind != "freight"
        || !("vehicles" in line) || line.vehicles == null
        || !("trains" in line) || line.trains != line.vehicles.len()
        || !("cargo" in line) || !("stationA" in line)
        || !("buildDate" in line) || now - line.buildDate < 365
        || !("lastProfit" in line) || line.lastProfit <= 0
        || (("scrapping" in line) && line.scrapping)) continue;

    local station = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(station)) continue;
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    if (waiting < 120) continue;
    if (("doubleGrowDirectional" in line) && line.doubleGrowDirectional) {
      if (line.trains < 6 && OpexDoubleGrowFleet(owner, line)) {
        DOUBLE_GROW_V2_CURSOR = (DOUBLE_GROW_V2_CURSOR + i + 1) % count;
        OpexDoubleGrowV2Log(line, "fleet", "ok", waiting);
        return true;
      }
      continue;
    }
    if (line.trains != 1 || (("doubleTrack" in line) && line.doubleTrack != 0)
        || (("v271Tandem" in line) && line.v271Tandem)) continue;
    if (("doubleGrowV2Retry" in line) && now < line.doubleGrowV2Retry) continue;
    local quote = OpexDoubleGrowV2AdmissionQuote(owner, line);
    local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (quote <= 0 || cash < quote) {
      if (DECISION_LOG) OpexDecide("DOUBLE_GROW",
          "version=2 phase=admission line=" + line.lineId
          + " result=skip_cash quote=" + quote + " cash=" + cash
          + " available=" + OpexAvailableCapital());
      OpexDoubleGrowV2Log(line, "skip", "cash", waiting);
      return false;
    }
    if (FLEET_ARB && !OpexFleetRequest(line, "rail", "add_vehicle", quote,
        null, "DOUBLE_CONVERSION_V2")) continue;
    /* Failed admissions are retried monthly; paused search is resumed. */
    line.rawset("doubleGrowV2Retry", now + 30);
    owner._saveProjection = null;
    DOUBLE_GROW_V2_CURSOR = (DOUBLE_GROW_V2_CURSOR + i + 1) % count;
    if (DECISION_LOG) OpexDecide("DOUBLE_GROW",
        "version=2 phase=admission line=" + line.lineId
        + " result=start quote=" + quote + " cash=" + cash
        + " available=" + OpexAvailableCapital());
    local accepted = OpexDoubleGrowV2Begin(owner, line);
    OpexDoubleGrowV2Log(line, accepted ? "search" : "skip",
        accepted ? "started" : "retrofit_rejected", waiting);
    if (!accepted) return false;
    local result = OpexDoubleGrowV2Continue(owner);
    return result.status == "built";
  }
  DOUBLE_GROW_V2_CURSOR = (DOUBLE_GROW_V2_CURSOR + scan) % count;
  return false;
}
