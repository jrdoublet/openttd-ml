/* RVA-10 : read-only per-cargo detection. Called only under RVA guards.
 * 15.3 script_cargo.cpp:81, script_station.hpp:100-169.
 * Cargo-specific override is authoritative; settings retained as provenance. */
function OpexRvaDistribution(cargo)
{
  if (!AICargo.IsValidCargo(cargo)) return null;
  local settings = {};
  foreach (key in ["linkgraph.distribution_pax", "linkgraph.distribution_mail",
                   "linkgraph.distribution_default"]) {
    settings.rawset(key, AIGameSettings.IsValid(key) ? AIGameSettings.GetValue(key) : null);
  }
  local mode = AICargo.GetDistributionType(cargo);
  local manual = mode == AICargo.DT_MANUAL;
  return { cargo = cargo, mode = mode, manual = manual, settings = settings,
      status = manual ? "manual_estimate" : "reference_fallback_graph_unobserved" };
}

function OpexRvaExistingFlow(station, origin, via, cargo)
{
  if (!AIStation.IsValidStation(station) || !AICargo.IsValidCargo(cargo)) return null;
  if (origin != AIStation.STATION_INVALID && !AIStation.IsValidStation(origin)) return null;
  if (via != AIStation.STATION_INVALID && !AIStation.IsValidStation(via)) return null;
  return { plannedMonth = AIStation.GetCargoPlannedFromVia(station, origin, via, cargo),
      waiting = AIStation.GetCargoWaitingFromVia(station, origin, via, cargo),
      origin = origin, via = via, revenue = null, revenueStatus = "requires_final_receipts" };
}
