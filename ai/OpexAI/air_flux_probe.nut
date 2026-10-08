/* Positive net load increments are a lower bound on pickups, not a complete
 * count. Do not infer unknown losses as zero or read this state in decisions. */
function OpexC121FluxNewState(now, waiting)
{
  return { startDate = now, lastDate = now, queueStart = waiting, queueLast = waiting,
    pickups = 0, samples = 0, maxGap = 0, skew = 0, risk = 0,
    ratingMin = 101, ratingMax = -1, vehicles = {}, loadingSamples = 0, multimodalSamples = 0 };
}

function OpexC121FluxObservedIncrease(previous, atStation, load, capacity, tick)
{
  if (previous == null || !previous.atStation || !atStation
      || previous.capacity != capacity || previous.tick >= tick || previous.load < 0 || load < 0) return 0;
  return load > previous.load ? load - previous.load : 0;
}

function OpexC121FluxFlush(station, cargo, state)
{
  local days = state.lastDate - state.startDate;
  if (days <= 0) return;
  local balance = state.pickups + state.queueLast - state.queueStart;
  local bound = balance > 0 ? balance.tofloat() * 30.4 / days.tofloat() : 0.0;
  local qualified = state.risk == 0 && state.skew == 0;
  AILog.Info("C121_STATION_FLUX station=" + station + " cargo=" + cargo
      + " start_date=" + state.startDate + " end_date=" + state.lastDate + " period_days=" + days
      + " pickups_lower=" + state.pickups + " queue_start=" + state.queueStart
      + " queue_end=" + state.queueLast + " balance=" + balance
      + " lower_pm=" + (qualified ? bound : -1.0) + " exact_pm=-1 losses=-1"
      + " qualified_bound=" + (qualified ? 1 : 0) + " risk_samples=" + state.risk
      + " skew_samples=" + state.skew + " samples=" + state.samples + " max_gap=" + state.maxGap
      + " loading_samples=" + state.loadingSamples + " rating_min=" + state.ratingMin
      + " rating_max=" + state.ratingMax + " multimodal_samples=" + state.multimodalSamples);
}

function OpexC121StationFluxStep(catalog)
{
  if (!C121_STATION_FLUX_PROBE || catalog == null || catalog.paxCargo < 0) return;
  local now = AIDate.GetCurrentDate();
  if (C121_STATION_FLUX_LAST_DATE >= 0 && now - C121_STATION_FLUX_LAST_DATE < 2) return;
  C121_STATION_FLUX_LAST_DATE = now;
  local cargo = catalog.paxCargo;
  local manual = AICargo.GetDistributionType(cargo) == AICargo.DT_MANUAL;
  local airports = {};
  local list = AIStationList(AIStation.STATION_AIRPORT);
  foreach (station, unused in list) {
    airports.rawset(station, { vehicles = {}, risk = !manual, multimodal = false });
    if (AIStation.HasStationType(station, AIStation.STATION_TRAIN)
        || AIStation.HasStationType(station, AIStation.STATION_BUS_STOP)
        || AIStation.HasStationType(station, AIStation.STATION_TRUCK_STOP)
        || AIStation.HasStationType(station, AIStation.STATION_DOCK)) airports[station].multimodal = true;
  }
  /* All own primary PASS services; never resolve virtual current orders.
   * Depot flags reuse transfer's bit: inspect flags only on station orders. */
  local allVehicles = AIVehicleList();
  local nonAirPassengerService = false;
  foreach (v, unused in allVehicles) {
    if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetCapacity(v, cargo) <= 0) continue;
    if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) nonAirPassengerService = true;
    local count = AIOrder.GetOrderCount(v);
    local unsafe = count < 0;
    local touched = {};
    for (local i = 0; i < count; i++) {
      if (!AIOrder.IsGotoStationOrder(v, i)) { unsafe = true; continue; }
      local station = AIStation.GetStationID(AIOrder.GetOrderDestination(v, i));
      local flags = AIOrder.GetOrderFlags(v, i);
      if (flags == AIOrder.OF_INVALID || (flags & (AIOrder.OF_TRANSFER | AIOrder.OF_UNLOAD
          | AIOrder.OF_NO_UNLOAD)) != 0) unsafe = true;
      if (station in airports) touched.rawset(station, true);
    }
    foreach (station, unusedStation in touched) {
      airports[station].vehicles.rawset(v, true);
      if (unsafe || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) airports[station].risk = true;
    }
  }
  foreach (station, service in airports) {
    /* Joined catchment stops are not transfers. Conservatively exclude a
     * mixed station if ANY non-AIR PASS service exists: trains can also call
     * at intermediate stations absent from their manual order list. */
    if (service.multimodal && nonAirPassengerService) service.risk = true;
    local tickStart = AIController.GetTick();
    local waiting = AIStation.GetCargoWaiting(station, cargo);
    if (waiting < 0) continue;
    local rating = AIStation.GetCargoRating(station, cargo);
    local state = (station in C121_STATION_FLUX_STATE) ? C121_STATION_FLUX_STATE[station] : null;
    if (state == null || now < state.lastDate) {
      state = OpexC121FluxNewState(now, waiting);
      C121_STATION_FLUX_STATE.rawset(station, state);
    }
    local current = {};
    local increases = 0;
    local loadingSamples = 0;
    foreach (v, unused in service.vehicles) {
      local capacity = AIVehicle.GetCapacity(v, cargo);
      local load = AIVehicle.GetCargoLoad(v, cargo);
      if (capacity < 0 || load < 0) service.risk = true;
      local atStation = AIVehicle.GetState(v) == AIVehicle.VS_AT_STATION
          && AIStation.GetStationID(AIVehicle.GetLocation(v)) == station;
      local previous = (v in state.vehicles) ? state.vehicles[v] : null;
      increases += OpexC121FluxObservedIncrease(previous, atStation, load, capacity, tickStart);
      current.rawset(v, { atStation = atStation, load = load, capacity = capacity, tick = tickStart });
      if (atStation) loadingSamples++;
    }
    local coherent = AIController.GetTick() == tickStart && AIDate.GetCurrentDate() == now;
    if (coherent) {
      state.pickups += increases;
      state.vehicles = current;
    } else {
      state.skew++;
      state.vehicles = {};
    }
    state.loadingSamples += loadingSamples;
    local gap = now - state.lastDate;
    if (gap > state.maxGap) state.maxGap = gap;
    state.lastDate = now;
    state.queueLast = waiting;
    state.samples++;
    if (service.multimodal) state.multimodalSamples++;
    if (service.risk) state.risk++;
    if (rating >= 0) {
      if (rating < state.ratingMin) state.ratingMin = rating;
      if (rating > state.ratingMax) state.ratingMax = rating;
    }
    if (now - state.startDate >= 30) {
      OpexC121FluxFlush(station, cargo, state);
      local nextState = OpexC121FluxNewState(now, waiting);
      nextState.vehicles = state.vehicles;
      if (!coherent) nextState.skew = 1;
      C121_STATION_FLUX_STATE[station] = nextState;
    }
  }
  local stale = [];
  foreach (station, state in C121_STATION_FLUX_STATE) if (!(station in airports)) stale.append(station);
  foreach (station in stale) delete C121_STATION_FLUX_STATE[station];
}
