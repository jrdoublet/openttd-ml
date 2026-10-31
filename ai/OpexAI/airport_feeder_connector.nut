/* Physical BUS source -> airport-hub road link, only for PAX bit4.
 * L and bounded two-turn geometry of the existing ROAD planner, including
 * opt-in only, capped alternate midpoint corridors (variants 6..9).
 * No fake join: the destination BUS stop MUST belong to the airport's
 * StationID; the link's real bits are rechecked AFTER construction.
 */
const OPEX_AIRPORT_FEEDER_TRACE_MAX_EDGES = 48;
PAX_AIR_FEEDER_CONNECTOR_DIAG <- {};

function OpexAirportFeederFindRoadConnector(sourceStop, sourceFront,
                                            hubStop, roadType)
{
  if (!("tested" in PAX_AIR_FEEDER_CONNECTOR_DIAG))
    PAX_AIR_FEEDER_CONNECTOR_DIAG = { tested = 0, extraProbed = 0,
        invalid = 0, unbuildable = 0, depotMissing = 0, found = 0 };
  AIRoad.SetCurrentRoadType(roadType);
  local hubFront = OpexAirportFeederRoadFront(hubStop);
  if (hubFront == null || !AIMap.IsValidTile(sourceFront)
      || !AIRoad.IsRoadTile(sourceFront)
      || !AIRoad.IsRoadTile(hubFront)
      || AIMap.DistanceManhattan(sourceFront, hubFront) > 32) return null;

  /* 0..5 are the former geometries. 6..9 already exist in the reviewed ROAD
   * generator but are tested ONLY here, under bit4, never for ordinary ROAD.
   * Probe at most two extra corridors for the ENTIRE monthly siting pass. */
  local ym = AIDate.GetYear(AIDate.GetCurrentDate()) * 12
      + AIDate.GetMonth(AIDate.GetCurrentDate());
  for (local variant = 0; variant < 10; variant++) {
    if (variant >= 6) {
      if (!PAX_AIR_FIRST_FEEDER_ONLY
          || PAX_AIR_FEEDER_CONNECTOR_DIAG.extraProbed >= 2
          || AIController.GetOpsTillSuspend() < 4000) break;
      if (((ym % 2) == 0 && variant != 6 && variant != 8)
          || ((ym % 2) != 0 && variant != 7 && variant != 9)) continue;
      PAX_AIR_FEEDER_CONNECTOR_DIAG.extraProbed++;
    }
    local trace = OpexRoadTraceMulti(sourceFront, hubFront, variant);
    PAX_AIR_FEEDER_CONNECTOR_DIAG.tested++;
    if (trace == null || trace.len() < 3
        || trace.len() > OPEX_AIRPORT_FEEDER_TRACE_MAX_EDGES
        || OpexRoadTraceHitsStop(trace, sourceStop)
        || OpexRoadTraceHitsStop(trace, hubStop)) {
      PAX_AIR_FEEDER_CONNECTOR_DIAG.invalid++;
      continue;
    }
    local blocked = false;
    foreach (edge in trace) {
      if (!AIMap.IsValidTile(edge.from) || !AIMap.IsValidTile(edge.to)
          || AIRoad.IsRoadStationTile(edge.from)
          || AIRoad.IsRoadStationTile(edge.to)
          || AIRoad.IsRoadDepotTile(edge.from)
          || AIRoad.IsRoadDepotTile(edge.to)) {
        blocked = true;
        break;
      }
    }
    if (blocked || !OpexRoadTraceBuildable(trace)) {
      PAX_AIR_FEEDER_CONNECTOR_DIAG.unbuildable++;
      continue;
    }
    local depot = OpexRoadFindDepot(trace,
        { tile = sourceStop, front = sourceFront },
        { tile = hubStop, front = hubFront }, true);
    if (depot == null || !AIMap.IsValidTile(depot.tile)
        || !AIMap.IsValidTile(depot.front)
        || !AITile.IsBuildable(depot.tile)) {
      PAX_AIR_FEEDER_CONNECTOR_DIAG.depotMissing++;
      continue;
    }
    PAX_AIR_FEEDER_CONNECTOR_DIAG.found++;
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_CONNECTOR",
        "variant=" + variant + " trace_edges=" + trace.len()
        + " extra_probed=" + PAX_AIR_FEEDER_CONNECTOR_DIAG.extraProbed);
    return { routeTrace = trace, depot = depot.tile,
        depotFront = depot.front, newDepot = true, newRoad = true };
  }
  return null;
}

/* The reviewed ROAD transaction only records edges which were REALLY built.
 * This rollback never removes pre-existing road edges and never touches the
 * joined hub airport stop. It is appropriate for immediate failed builds;
 * delayed recovery must ensure no other service has started using the route. */
function OpexAirportFeederRollbackRoadEdges(edges)
{
  if (edges == null) return true;
  local ok = true;
  for (local i = edges.len() - 1; i >= 0; i--) {
    local edge = edges[i];
    if (edge == null || !("from" in edge) || !("to" in edge)
        || !AIMap.IsValidTile(edge.from) || !AIMap.IsValidTile(edge.to)) {
      ok = false;
      continue;
    }
    if (!AIRoad.RemoveRoad(edge.from, edge.to)) ok = false;
  }
  return ok;
}
