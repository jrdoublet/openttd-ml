/* V266: no work is called unless v266_rail_air_feeder=1. No portfolio insertion.
 * Monetary split is virtual: OpenTTD 15.3 economy.cpp:1219-1248.
 * Numeric factors below are units (12 months, 365 calendar days: NoAI 15.3
 * script/api/script_date.hpp:35,48; two endpoints: the two-order route contract),
 * not distance, population, cash or fill-rate thresholds. */
function OpexV266IsFeeder(item)
{
  return item != null && ("v266Airport" in item);
}

function OpexV266Ops(state, mark, planning)
{
  local ops = OpexOpsMeasureEnd(mark);
  local today = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(today) * 12 + AIDate.GetMonth(today);
  if (!("opsMonth" in state)) {
    state.opsMonth <- month; state.observeOps <- 0; state.planOps <- 0;
    state.observeCalls <- 0; state.planCalls <- 0;
  }
  if (month != state.opsMonth) {
    if (DECISION_LOG) OpexDecide("V266_OPS", "month=" + state.opsMonth
      + " observe_calls=" + state.observeCalls + " observe_ops=" + state.observeOps
      + " plan_calls=" + state.planCalls + " plan_ops=" + state.planOps);
    state.opsMonth = month; state.observeOps = 0; state.planOps = 0;
    state.observeCalls = 0; state.planCalls = 0;
  }
  if (planning) { state.planCalls++; state.planOps += ops; }
  else { state.observeCalls++; state.observeOps += ops; }
}

function OpexAI::_v266Observe()
{
  if (!MODE_AIR || !MODE_RAIL || this._catalog == null || this._lines.len() == 0) return;
  if (this._v266 == null)
    this._v266 = { line = 0, vehicle = 0, town = 0, flights = {}, offer = null, ready = null };
  local s = this._v266;
  // One line/vehicle per scheduler dispatch: no whole-fleet scan before AIR.
  if (s.line >= this._lines.len()) s.line = 0;
  local line = this._lines[s.line];
  if (OpexV266IsFeeder(line)) {
    // Its own transfer-account profit is not a closure criterion. Retire when
    // the actual downstream service disappears; leave shared airport tiles intact.
    local service = false;
    foreach (air in this._lines) {
      if (air.lineId == line.v266AirLine && air.mode == "air" && !air.scrapping
          && (OpexLineStationId(air, "A") == line.v266Airport
            || OpexLineStationId(air, "B") == line.v266Airport)) service = true;
    }
    if (!service && !line.scrapping) this._triggerScrapLine(line, "v266_air_removed");
    s.line++; s.vehicle = 0; return;
  }
  if (!("mode" in line) || line.mode != "air" || line.scrapping
      || !("vehicles" in line) || line.vehicles.len() == 0) {
    s.line++; s.vehicle = 0; return;
  }
  if (s.vehicle >= line.vehicles.len()) s.vehicle = 0;
  local v = line.vehicles[s.vehicle++];
  if (s.vehicle >= line.vehicles.len()) { s.line++; s.vehicle = 0; }
  if (!AIVehicle.IsValidVehicle(v) || AIOrder.GetOrderCount(v) != 2) return;
  // Loading is explicitly excluded (script_vehicle.cpp:362). A stationary/hangar
  // sample must never masquerade as unused sellable capacity.
  if (AIVehicle.GetState(v) != AIVehicle.VS_RUNNING
      || AIVehicle.GetCurrentSpeed(v) <= 0
      || !AIOrder.IsGotoStationOrder(v, AIOrder.ORDER_CURRENT)) return;
  local target = AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT);
  if (target < 0 || target > 1) return;
  local airport = OpexLineStationId(line, target == 1 ? "A" : "B");
  local finalStation = OpexLineStationId(line, target == 1 ? "B" : "A");
  if (!AIStation.IsValidStation(airport) || !AIStation.IsValidStation(finalStation)) return;
  if (AIStation.GetStationID(AIOrder.GetOrderDestination(v, 0)) != OpexLineStationId(line, "A")
      || AIStation.GetStationID(AIOrder.GetOrderDestination(v, 1)) != OpexLineStationId(line, "B")) return;
  if (AIStation.GetStationID(AIOrder.GetOrderDestination(v, AIOrder.ORDER_CURRENT)) != finalStation) return;
  local cargo = this._catalog.paxCargo;
  local cap = AIVehicle.GetCapacity(v, cargo);
  local load = AIVehicle.GetCargoLoad(v, cargo);
  if (cap <= 0 || load < 0 || load > cap) return;
  local today = AIDate.GetCurrentDate();
  local age = AIVehicle.GetAge(v);
  if (!(v in s.flights) || s.flights[v].airLine != line.lineId || age < s.flights[v].age)
    s.flights[v] <- { target = -1, departures = {}, airLine = line.lineId, age = age };
  local flight = s.flights[v];
  flight.age = age;
  if (flight.target == target) return; // Exactly one observation per flight.
  flight.target = target;
  local empty = cap - load;
  if (airport in flight.departures) {
    local previous = flight.departures[airport];
    local cycle = today - previous.date;
    if (cycle > 0 && previous.cap == cap) {
      local seats = empty < previous.empty ? empty : previous.empty;
      s.offer = { aircraft = v, airLine = line.lineId, airport = airport,
        finalStation = finalStation, date = today, cycle = cycle,
        capacity = cap, age = age, cargo = cargo,
        seats = seats, annual = seats * 365.0 / cycle };
      if (DECISION_LOG) OpexDecide("V266_SEATS", "air_line=" + line.lineId
        + " aircraft=" + v + " airport=" + airport + " load=" + load
        + " capacity=" + cap + " seats=" + seats + " cycle_days=" + cycle);
    }
  }
  flight.departures[airport] <- { date = today, empty = empty, cap = cap };
}

function OpexAI::_v266Reserve()
{
  // Reserve the best currently affordable AIR project, including fleet additions.
  // candidateGroups contains all modes, before affordable truncation (projects.nut).
  if (this._projects == null || !("candidateGroups" in this._projects)) return null;
  local available = AICompany.GetBankBalance(AICompany.COMPANY_SELF) - OpexCashReserve();
  local best = null;
  local bestScore = 0.0;
  local kDec = OpexC69ComputeKDec().K_dec;
  foreach (key, group in this._projects.candidateGroups) {
    foreach (p in group) {
      if (!OpexC121AutopsyIsAirRelated(p)) continue;
      if (p.mode == "air") {
        if (!OpexIncrementalCandidateStillValid(p, this._lines, this._abandonedPairs)) continue;
      } else {
        // The generic exact-OD filter rejects fleet additions by construction.
        local live = false;
        foreach (line in this._lines)
          if (line == p.payload.line && !line.scrapping) live = true;
        if (!live) continue;
      }
      local cost = OpexProjectFinanceCapital(p);
      if (cost <= 0 || cost > available) continue;
      // Same denominator as projects_selection.nut:773-788. Do not read a stale
      // fundScore: previously unaffordable candidates may never have received one.
      local decisionCost = (p.mode == "air" && ("decisionFinanceCapital" in p)
        && p.decisionFinanceCapital > 0) ? p.decisionFinanceCapital : cost;
      local exempt = p.mode == "fleet" && !OpexC121ProjectHasRealization(p);
      local scored = clone p;
      scored.fundScore <- OpexProjectScore(OpexProjectFundProfit(p),
        kDec > decisionCost && !exempt ? kDec : decisionCost);
      local score = OpexProjectSelectionScore(scored, "fundScore");
      if (best == null || score > bestScore) { best = p; bestScore = score; }
    }
  }
  return OpexCashReserve() + (best == null ? 0 : OpexProjectFinanceCapital(best));
}

function OpexV266AirportFree(lines, airport)
{
  foreach (line in lines) {
    // A single feeder per airport: never sell the same observed empty seats twice.
    if (OpexV266IsFeeder(line) && line.v266Airport == airport) return false;
  }
  return true;
}

function OpexV266OfferLive(offer, lines)
{
  if (offer == null || offer.seats <= 0 || offer.annual <= 0
      || AIDate.GetCurrentDate() - offer.date > offer.cycle
      || !AIVehicle.IsValidVehicle(offer.aircraft)
      || AIVehicle.GetAge(offer.aircraft) < offer.age
      || AIVehicle.GetCapacity(offer.aircraft, offer.cargo) != offer.capacity
      || !AIStation.IsValidStation(offer.airport)
      || !AIStation.IsValidStation(offer.finalStation)
      || !AIStation.HasStationType(offer.airport, AIStation.STATION_AIRPORT)
      || !AIStation.HasStationType(offer.finalStation, AIStation.STATION_AIRPORT)
      || !AICompany.IsMine(AITile.GetOwner(AIStation.GetLocation(offer.airport)))
      || !OpexV266AirportFree(lines, offer.airport)) return false;
  foreach (line in lines) {
    if (line.lineId != offer.airLine || line.scrapping || line.mode != "air") continue;
    local found = false;
    foreach (v in line.vehicles) if (v == offer.aircraft) found = true;
    return found && ((OpexLineStationId(line, "A") == offer.airport
        && OpexLineStationId(line, "B") == offer.finalStation)
      || (OpexLineStationId(line, "B") == offer.airport
        && OpexLineStationId(line, "A") == offer.finalStation));
  }
  return false;
}

function OpexV266Value(candidate)
{
  // economy.nut calls OpexLoadedTripsPerMonth(..., kind == "pax"); the
  // distinct "feeder" kind therefore counts only the A->airport loaded leg.
  // Use one train's throughput; keep the full model cost (conservative if >1).
  local throughput = candidate.perTrain * candidate.tripsPerMonth * 12.0;
  local supply = candidate.monthly * candidate.stationRating / 100.0 * 12;
  local sellable = candidate.v266Offer.annual;
  if (sellable > throughput) sellable = throughput;
  if (sellable > supply) sellable = supply;
  // Full OD distance, not the sum of leg distances: economy.cpp:1221.
  local distance = AIMap.DistanceManhattan(candidate.src,
      AIStation.GetLocation(candidate.v266Offer.finalStation));
  // One observed air round trip is a conservative allowance for wait + flight.
  local fillDays = candidate.perTrain * (365.0 / 12) / candidate.monthly;
  local days = OpexCeilDiv(fillDays + candidate.oneWayDays + candidate.v266Offer.cycle, 1);
  local fare = AICargo.GetCargoIncome(candidate.cargo, distance, days);
  candidate.revenueAnnual = (sellable * fare).tointeger();
  candidate.profitAnnual = candidate.revenueAnnual - candidate.runningAnnual - candidate.amortAnnual;
  candidate.trains = 1; // Dedicated single-track shuttle; no fleet expansion.
  candidate.roi = 0; // The complete fare never enters a portfolio ratio.
  if (DECISION_LOG) OpexDecide("V266_VALUE", "airport=" + candidate.v266Airport
    + " src=" + candidate.src + " annual_sellable=" + sellable + " fare=" + fare
    + " days=" + days + " revenue=" + candidate.revenueAnnual
    + " running=" + candidate.runningAnnual + " amort=" + candidate.amortAnnual
    + " marginal=" + candidate.profitAnnual);
}

/* Both endpoints reuse current platform geometry/search/cleanup. Destination
 * join is mandatory; the engine itself checks station spread and distant joining.
 * No fallback to an independent airport-side station. */
function OpexV266Platforms(catalog, candidate)
{
  local statsA = { nClear = 0, nCargo = 0, nCmd = 0 };
  local statsB = { nClear = 0, nCargo = 0, nCmd = 0 };
  local length = candidate.platformLength;
  local a = OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS,
    length, MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, true, statsA);
  local b = [];
  // STATION_SEARCH_RADIUS/MAX_STATION_PLANS (builder_rail.nut:22-23) are existing bounds, not V226's
  // unsourced 30-60/80-tile distance gates. The native join command is authoritative.
  local nearby = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS,
    length, MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, false, statsB);
  foreach (p in nearby) {
    local ok = false;
    {
      local shield = AIAccounting();
      local probe = AITestMode();
      ok = AIRail.BuildRailStation(p.anchor, p.direction, 1, length, candidate.v266Airport);
    }
    if (ok) { p.stationId <- candidate.v266Airport; b.append(p); }
  }
  return { plansA = a, plansB = b, length = length, slopeRelaxed = 0,
    reason = OpexRailSiteReason(a.len() > 0, b.len() > 0), statsA = statsA, statsB = statsB };
}

function OpexAI::_v266AfterPass()
{
  // Called only after the normal pass built nothing. AIR gets its normal slot first.
  if (!MODE_AIR || !MODE_RAIL || this._catalog == null || this._v266 == null
      || this._railSearch != null || this._railExpansion != null) return;
  local s = this._v266;
  if (s.ready != null) {
    local ready = s.ready;
    s.ready = null;
    this._v266Finish(ready.candidate, ready.plan);
    return;
  }
  if (!OpexV266OfferLive(s.offer, this._lines) || this._catalog.towns.len() == 0) return;
  local reserve = this._v266Reserve();
  if (reserve == null) return;
  // One town per idle pass, no fleet x town cross-product before air construction.
  if (s.town >= this._catalog.towns.len()) s.town = 0;
  local town = this._catalog.towns[s.town++];
  local offer = s.offer;
  local dst = AIStation.GetLocation(offer.airport);
  // Satellite must be outside our current service; do not siphon existing routes.
  if (OpexOriginService(this._lines, town.tile) != null
      || AITile.GetClosestTown(dst) == town.id
      || AITile.GetClosestTown(AIStation.GetLocation(offer.finalStation)) == town.id) return;
  foreach (air in this._lines) {
    if (air.mode == "air" && (AITile.GetClosestTown(air.stationA) == town.id
        || AITile.GetClosestTown(air.stationB) == town.id)) return;
  }
  local cargo = this._catalog.paxCargo;
  // CargoDist requires destination-specific demand, absent from these samples.
  // API 15.3 script_cargo.hpp:71-75,162: use enum, never a hard-coded setting ID.
  if (AICargo.GetDistributionType(cargo) != AICargo.DT_MANUAL) return;
  local monthly = AITown.GetLastMonthProduction(town.id, cargo);
  local distance = AIMap.DistanceManhattan(town.tile, dst);
  if (monthly <= 0 || distance <= 0 || !OpexRailVehicleSlotAvailable()) return;
  local econ = OpexLineEconomics(this._catalog, cargo, distance, monthly, "feeder");
  if (econ == null) return;
  local c = clone econ;
  c.mode <- "rail"; c.kind <- "feeder"; c.cargo <- cargo;
  c.src <- town.tile; c.dst <- dst; c.distance <- distance; c.monthly <- monthly;
  c.originServed <- false; c.iterations <- OpexRailIterations(distance);
  c.ratio <- 0; c.opcodeRatio <- 0; c.isLowRatio <- false;
  c.v266Airport <- offer.airport; c.v266AirLine <- offer.airLine;
  c.v266Offer <- clone offer;
  OpexV266Value(c);
  if (DECISION_LOG) OpexDecide("V266_RESIDUAL", "airport=" + c.v266Airport
    + " reserve=" + reserve + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
    + " capital=" + c.capital + " marginal=" + c.profitAnnual);
  if (c.profitAnnual <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < c.capital + reserve) return;
  local close = this._tooClose(c);
  if (close.hard >= 0 || close.blocking >= 0) return;
  if (OpexAbandonedPairKey(c) in this._abandonedPairs) return;
  if (DECISION_LOG) OpexDecide("V266_SEARCH", "airport=" + c.v266Airport
    + " src=" + c.src + " reserve=" + reserve + " capital=" + c.capital);
  // Zero alternative ratio requests the existing cap (globals_pre.nut:586), not a fare ROI.
  local start = this._startRailSearch(c, 0, HARD_ITERATION_CAP, 0);
  if (!start.pending) this._v266Finish(c, start.plan);
}

function OpexAI::_v266Finish(candidate, plan)
{
  candidate.railPlan <- plan;
  if (plan == null) {
    if (DECISION_LOG) OpexDecide("V266_BUILD", "ok=0 reason=plan");
    return { outcome = "failed", reason = "plan", error = 0 };
  }
  if (!plan.ok) {
    // Preserve native failure telemetry and pair cooldown; no expense is possible.
    local failed = OpexBuildLine(this._catalog, this._budget, candidate, 0,
      OpexCashReserve(), HARD_ITERATION_CAP);
    this._recordRailAttempt(candidate, failed, 0, AIDate.GetYear(AIDate.GetCurrentDate()));
    if (DECISION_LOG) OpexDecide("V266_BUILD", "ok=0 reason=" + failed.reason);
    return { outcome = "failed", reason = failed.reason, error = failed.error };
  }
  local reserve = this._v266Reserve();
  if (reserve == null || !OpexV266OfferLive(candidate.v266Offer, this._lines)) {
    if (DECISION_LOG) OpexDecide("V266_BUILD", "ok=0 reason=stale_air");
    return { outcome = "rejected", reason = "stale_air", error = 0 };
  }
  local result = OpexBuildLine(this._catalog, this._budget, candidate, 0, reserve, HARD_ITERATION_CAP);
  local built = this._recordRailAttempt(candidate, result, 0, AIDate.GetYear(AIDate.GetCurrentDate()));
  if (DECISION_LOG) OpexDecide("V266_BUILD", "ok=" + (built ? 1 : 0)
    + " reason=" + result.reason + " airport=" + candidate.v266Airport
    + " air_line=" + candidate.v266AirLine + " reserve=" + reserve);
  return { outcome = built ? "built" : "failed", reason = result.reason, error = result.error };
}
