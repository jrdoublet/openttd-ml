/* Passive, opt-in only. Real cargo, orders and company money from OpenTTD;
 * no proxy estimates. Sampling monthly can miss transfers that board an
 * airplane before this observation; a zero is NOT proof of no transport.
 */
function OpexAirportFeederObserveFlows(lines, paxCargo)
{
  if (!PAX_AIR_FIRST_FEEDER_ONLY || !DECISION_LOG || lines == null
      || paxCargo < 0) return;
  foreach (line in lines) {
    if (line == null || !("purpose" in line)
        || (line.purpose != "airport_feeder"
            && line.purpose != "airport_rail_feeder")
        || !("stationA" in line) || !("stationB" in line)) continue;
    local source = AIStation.GetStationID(line.stationA);
    local hub = AIStation.GetStationID(line.stationB);
    if (!AIStation.IsValidStation(source) || !AIStation.IsValidStation(hub)
        || source == hub) continue;
    local vehicle = ("vehicle" in line) ? line.vehicle : null;
    if (!AIVehicle.IsValidVehicle(vehicle)) continue;
    local carriedNow = AIVehicle.GetCargoLoad(vehicle, paxCargo);
    local profitNow = AIVehicle.GetProfitThisYear(vehicle);
    local waitingFromSource = AIStation.GetCargoWaitingFrom(hub, source, paxCargo);
    local waitingTotal = AIStation.GetCargoWaiting(hub, paxCargo);
    local planeCount = 0, planeLoad = 0;
    /* NoAI can identify packets WAITING at this hub by their true first
     * station and planned next hop. It cannot identify the origins of
     * packets already loaded onto a plane. Manual distribution has no
     * next-hop information, so keep an explicit unknown (-1). */
    local viaParentAir = AICargo.GetDistributionType(paxCargo)
        == AICargo.DT_MANUAL ? -1 : 0;
    local seenAirDest = {};
    foreach (air in lines) {
      if (air == null || !("mode" in air) || air.mode != "air"
          || !("lineId" in air) || !("parentAirLineId" in line)
          || air.lineId != line.parentAirLineId
          || !("vehicles" in air) || air.vehicles == null) continue;
      if (viaParentAir >= 0) foreach (field in ["stationA", "stationB"]) {
        if (!(field in air) || air[field] == null
            || !AIMap.IsValidTile(air[field])) continue;
        local airDest = AIStation.GetStationID(air[field]);
        if (!AIStation.IsValidStation(airDest) || airDest == hub
            || airDest in seenAirDest) continue;
        seenAirDest.rawset(airDest, true);
        viaParentAir += AIStation.GetCargoWaitingFromVia(
            hub, source, airDest, paxCargo);
      }
      foreach (plane in air.vehicles) {
        if (!AIVehicle.IsValidVehicle(plane)
            || AIVehicle.GetVehicleType(plane) != AIVehicle.VT_AIR) continue;
        planeCount++;
        planeLoad += AIVehicle.GetCargoLoad(plane, paxCargo);
      }
    }
    OpexDecide("AIRPORT_FEEDER_FLOW", "mode=" + line.mode
        + " line=" + line.lineId + " src=" + source + " hub=" + hub
        + " bus_or_train_load=" + carriedNow
        + " hub_from_source=" + waitingFromSource
        + " hub_source_via_parent_air=" + viaParentAir
        + " hub_waiting=" + waitingTotal
        + " feeder_profit_this_year=" + profitNow
        + " connecting_air_planes=" + planeCount
        + " connecting_air_load=" + planeLoad);
  }
}
