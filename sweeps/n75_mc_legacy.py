"""N75-MC, P6 and P3 isolation: remove ONLY the exact opt-in additions.

Historical inventory ceilings and PO01C byte hashes must continue to cover
the same 58 legacy settings and the exact original bytes. Never rebaseline.
"""

import hashlib


INFO_DELTA = (
    b'    AddSetting({ name = "n75_multi_cargo",\n'
    b'      description = "1972+ cash-idle rail refill: 0=off, 1=shadow, 2=one extra freight cargo on empty funded rail pool (default 2)",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 2, medium_value = 2, hard_value = 2, custom_value = 2,\n'
    b'      flags = 0 });\n'
)
SETTINGS_DELTA = (
    b'  local n75MultiCargo = AIController.GetSetting("n75_multi_cargo");\n'
    b'  N75_MULTI_CARGO = (n75MultiCargo >= 1 && n75MultiCargo <= 2) ? n75MultiCargo : 0;\n'
    b'  N75_MC_LAST_MONTH = (N75_MULTI_CARGO > 0) ? N75_MC_SAVED_MONTH : -1;\n'
    b'  N75_MC_SAVED_MONTH = -1;\n'
)

# P6 is an independent, opt-in experiment. Its three source additions are
# deliberately removed from the PO01D byte snapshot without changing the
# historical SHA or concealing changes elsewhere in these source files.
P6_INFO_DELTA = (
    b'    AddSetting({ name = "p6_air_firstline_window",\n'
    b'      description = "P6 experimental first AIR line: 0=immediate historical build (default), 1=wait for at most one additional catalog publication (32 ticks / 160000 scan opcodes) when two affordable distinct AIR pairs are already selected",\n'
    b'      min_value = 0, max_value = 1,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = AICONFIG_BOOLEAN });\n'
)
P6_SETTINGS_DELTA = (
    b'  P6_AIR_FIRSTLINE_WINDOW = AIController.GetSetting("p6_air_firstline_window");\n'
)
P6_MAIN_DELTA = (
    b'  /* P6 : l\'attente est consommee une fois, y compris apres Save/Load. */\n'
    b'  _p6FirstlineWindowConsumed = false;\n'
    b'  _p6FirstlineWindow = null;\n'
)
P6_DELTAS = {
    "info.nut": P6_INFO_DELTA,
    "settings.nut": P6_SETTINGS_DELTA,
    "main.nut": P6_MAIN_DELTA,
}

# P3 default-OFF is a separate worktree behavioral experiment. Historical
# byte snapshots retain their original hashes, not a new P3-derived baseline.
P3_INFO_DELTA = (
    b'    AddSetting({ name = "air_fleet_yield_rightsize",\n'
    b'      description = "P3 mature AIR 2->3+ reinforcement: 0=off (default), 1=C117 shadow, 2=conservative low-yield veto",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
P3_SETTINGS_DELTA = (
    b'  local p3AirFleetYield = AIController.GetSetting("air_fleet_yield_rightsize");\n'
    b'  P3_AIR_FLEET_YIELD = (p3AirFleetYield == 1 || p3AirFleetYield == 2) ? p3AirFleetYield : 0;\n'
    b'  P3_AIR_FLEET_WINDOWS = {};\n'
)
P3_DELTAS = {"info.nut": P3_INFO_DELTA, "settings.nut": P3_SETTINGS_DELTA}

# FRONT-PAX-2 is an independent default-OFF option. Subtract its exact bytes
# from frozen legacy inventories without altering any historical hash.
FP2_INFO_DELTA = (
    b'    AddSetting({ name = "front_pax2_bounded_overlap",\n'
    b'      description = "FRONT-PAX-2 AIR PASS only: 0=historical (default), 1=passive bounded shortlist, 2=up to one additional C121 candidate per arm per completed ALL-band scan",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
FP2_SETTINGS_DELTA = (
    b'  local fp2Overlap = AIController.GetSetting("front_pax2_bounded_overlap");\n'
    b'  FRONT_PAX2_BOUNDED_OVERLAP = (fp2Overlap == 1 || fp2Overlap == 2) ? fp2Overlap : 0;\n'
)
FP2_DELTAS = {"info.nut": FP2_INFO_DELTA, "settings.nut": FP2_SETTINGS_DELTA}

# P2 is an opt-in, default-OFF rank experiment. Its exact settings bytes are
# excluded from the frozen historic inventory; all prior digests stay fixed.
P2_INFO_DELTA = (
    b'    AddSetting({ name = "rail_cargo_opportunity_rank",\n'
    b'      description = "P2 prepared RAIL freight opportunity: 0=historical (default), 1=passive top-K shadow, 2=one adjacent same-C77-tier promotion (8% score, 93% fund, 80% profit)",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
P2_SETTINGS_DELTA = (
    b'  local p2Opportunity = AIController.GetSetting("rail_cargo_opportunity_rank");\n'
    b'  P2_RAIL_CARGO_OPPORTUNITY_RANK = (p2Opportunity == 1 || p2Opportunity == 2) ? p2Opportunity : 0;\n'
    b'  P2_OPPORTUNITY_STAMP = 0;\n'
)
P2_DELTAS = {"info.nut": P2_INFO_DELTA, "settings.nut": P2_SETTINGS_DELTA}

# P1 is an independent opt-in C121 rail experiment; retain the frozen
# historical contract by subtracting ONLY its exact additions. In particular,
# P1's auxiliary freight candidate must never rebaseline PO01D's rail scan.
P1_INFO_DELTA = (
    b'    AddSetting({ name = "rail_long_value_rank",\n'
    b'      description = "P1: C121/C80 one-train freight 160-300 beyond railMax; 0=off (default), 1=passive proxy shadow, 2=one physically prepared long option",\n'
    b'      min_value = 0, max_value = 2,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = 0 });\n'
)
P1_SETTINGS_DELTA = (
    b'  local p1LongRank = AIController.GetSetting("rail_long_value_rank");\n'
    b'  P1_RAIL_LONG_VALUE_RANK = (p1LongRank == 1 || p1LongRank == 2) ? p1LongRank : 0;\n'
)
P1_DELTAS = {"info.nut": P1_INFO_DELTA, "settings.nut": P1_SETTINGS_DELTA}

# V286 adds an independent, default-OFF passive rail flow probe. Preserve
# PO01D's original byte hashes by subtracting only these reviewed fragments;
# the probe body has its own frozen hash to catch accidental changes.
V286_INFO_DELTA = (
    b'    AddSetting({ name = "v286_rail_flow_probe",\n'
    b'      description = "V286 passive RAIL cargo/vehicle/industry snapshots: 0=off (default), 1=sample 16 lines every 30 game days; no policy change",\n'
    b'      min_value = 0, max_value = 1,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = AICONFIG_BOOLEAN });\n\n'
)
V286_SETTINGS_DELTA = (
    b'  V286_FLOW_PROBE = AIController.GetSetting("v286_rail_flow_probe") == 1;\n'
    b'  V286_FLOW_LAST_DAY = -1;\n'
    b'  V286_FLOW_CURSOR = 0;\n'
)
V286_MAIN_DELTA = b'    if (V286_FLOW_PROBE) OpexV286FlowSample(this._lines);\n'
V286_DELTAS = {
    "info.nut": V286_INFO_DELTA,
    "settings.nut": V286_SETTINGS_DELTA,
    "main.nut": V286_MAIN_DELTA,
}
# C75 is a separate default-OFF opcode experiment. Remove only the exact
# setting/loader declarations from the historical byte inventory; do not
# rebaseline any frozen hash or remove the decision-critical K_pass code.
C75_INFO_DELTA = (
    b'    AddSetting({ name = "c75_year_ledger_skip",\n'
    b'      description = "C75 opcode experiment: 0=keep annual counters (default), 1=skip only when C49/C69 diagnostics are off; K_pass unchanged",\n'
    b'      min_value = 0, max_value = 1,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      flags = AICONFIG_BOOLEAN });\n\n'
)
C75_SETTINGS_DELTA = b'  C75_YEAR_LEDGER_SKIP = AIController.GetSetting("c75_year_ledger_skip") == 1;\n'
C75_DELTAS = {"info.nut": C75_INFO_DELTA, "settings.nut": C75_SETTINGS_DELTA}
# DIST-BORNES-1 is a separate default-OFF correction to the deferred V276
# freight path. Remove the *exact* reviewed addition from the frozen PO01D
# inventory, including restoration of the historic V269 expression. This
# keeps the original hashes and rejects edits to any other part of the file.
DIST_BORNES_INFO_DELTA = (
    b'    AddSetting({\n'
    b'      name = "dist_bornes_v276_freight",\n'
    b'      description = "DIST-BORNES-1: 1 = preserve V269 late freight relaxation in deferred V276 scans, including the spatial grid and freight band; 0 = historical V276 (default)",\n'
    b'      min_value = 0, max_value = 1,\n'
    b'      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,\n'
    b'      default_value = 0, step_size = 1, flags = 0\n'
    b'    });\n'
)
DIST_BORNES_SETTINGS_DELTA = (
    b'  DIST_BORNES_V276_FREIGHT = AIController.GetSetting("dist_bornes_v276_freight") == 1;\n'
)
DIST_BORNES_DELTAS = {
    "info.nut": DIST_BORNES_INFO_DELTA,
    "settings.nut": DIST_BORNES_SETTINGS_DELTA,
}
DIST_BORNES_CANDIDATE_EDIT = (
    b'  } else if (distance > ((V269_RAIL_LATE_RELAX > 0\n'
    b'      && (V269_RELAXED || (DIST_BORNES_V276_FREIGHT\n'
    b'          && ("distBornesV269Relaxed" in bounds) && bounds.distBornesV269Relaxed))\n'
    b'      && V269_RAIL_MAX_DIST > bounds.railMax) ? V269_RAIL_MAX_DIST : bounds.railMax)) {\n',
    b'  } else if (distance > ((V269_RAIL_LATE_RELAX > 0 && V269_RELAXED && V269_RAIL_MAX_DIST > bounds.railMax) ? V269_RAIL_MAX_DIST : bounds.railMax)) {\n',
)
C75_PROBES_DELTA = (
    "  /* C75_PASS_DATES et K_pass restent décisionnels. Les compteurs annuels ne\n"
    "   * servent qu'aux consommateurs de diagnostic C49/UB et C69/c75_year.\n"
    "   * Le chemin historique (réglage 0) garde exactement les compteurs. */\n"
    "  if (C75_YEAR_LEDGER_SKIP && !C49_SCARCITY_LEDGER && !C69_BOTTLENECK_PROBE) {\n"
    "    C75_YEAR_LEDGER = null;\n"
    "    return;\n"
    "  }\n"
).encode("utf-8")
V286_PROBES_BLOCK_PREFIX = b"/* V286 : photographies RAIL"
V286_PROBES_BLOCK_END = b"/* V309 : observation passive"
# 26/10 : reviewed V286 opt-in only: sample-ops + industry cargo units,
# and count four vehicles with positive cargo capacity. Historical PO01D
# remains frozen; this digest guards the intentionally changed probe body.
V286_PROBES_BLOCK_SHA256 = "dc8210ba9cc27be6c5879006961a2e550e2a31c154b99443b27115f91b5dff40"
V286_PROBES_CALL = b'    if (V286_FLOW_PROBE) OpexV286FlowSample(this._lines);\n'

P1_CANDIDATES_BLOCK_START = b"/* P1 : le balayage industriel normal"
P1_CANDIDATES_BLOCK_END = b"/* Ne garder que les K meilleurs"
P1_CANDIDATES_BLOCK_SHA256 = "69db60bef45147f21364ae192cd82c961764469b7a719a0e56da49409e99879f"
P1_BUILDER_RAIL_DELTA = (
    b'  /* P1 : un trajet reel plus long peut transformer une rame en deux et activer\n'
    b'   * la recherche BLOQUANTE de seconde voie juste dessous. Ce chemin experimental\n'
    b'   * abandonne avant cet A* et conserve l\'unique recherche segmentee C80. */\n'
    b'  if (("p1Long" in candidate) && candidate.p1Long) {\n'
    b'    if (candidate.trains != 1 || OpexV190Active()) {\n'
    b'      plan.reason = "P1FLEET";\n'
    b'      return plan;\n'
    b'    }\n'
    b'    if (candidate.profitAnnual < 25000 || candidate.roi < 150) {\n'
    b'      plan.reason = "P1VALUE";\n'
    b'      return plan;\n'
    b'    }\n'
    b'  }\n\n'
)
P1_CANDIDATES_EDITS = (
    (
        b'function OpexFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1, p1LongState = null)\n',
        b'function OpexFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1)\n',
    ),
    (
        b'        /* P1 : les paires hors railMax ne doivent pas evincer les courtes du TopK\n'
        b'         * papier. En shadow les stats historiques restent identiques. */\n'
        b'        if (p1LongState != null && monthly > 0\n'
        b'            && OpexP1LongOffer(p1LongState, catalog, cargo, source, industries[di],\n'
        b'                               monthly, isTransformer)) {\n'
        b'          stats.distanceLong++;\n'
        b'          continue;\n'
        b'        }\n',
        b'',
    ),
    (
        b'function OpexBuildCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, paxProfile = null, paxCandidateProfile = null, paxCruiseCache = null, freightCruiseCache = null, generatePax = true, generateFreight = true, paxBand = PAX_BAND_ALL, freightCargo = null, targetKind = null, targetId = -1, p1LongState = null)\n',
        b'function OpexBuildCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, paxProfile = null, paxCandidateProfile = null, paxCruiseCache = null, freightCruiseCache = null, generatePax = true, generateFreight = true, paxBand = PAX_BAND_ALL, freightCargo = null, targetKind = null, targetId = -1)\n',
    ),
    (
        b'                          freightCargo, targetKind, targetId, p1LongState);\n',
        b'                          freightCargo, targetKind, targetId);\n',
    ),
    (
        b'  /* P1 : l\'economie n\'est calculee qu\'APRES le scan, pour l\'unique meilleur\n'
        b'   * proxy. Le candidat reste hors `all` et hors `best` jusqu\'a la preuve C80. */\n'
        b'  if (p1LongState != null && p1LongState.best != null) {\n'
        b'    if (P1_RAIL_LONG_VALUE_RANK == 2)\n'
        b'      p1LongState.candidate = OpexP1LongEvaluate(catalog, p1LongState, stats);\n'
        b'    if (DECISION_LOG) OpexDecide("P1_LONG_SHADOW", "mode=" + P1_RAIL_LONG_VALUE_RANK\n'
        b'        + " count=" + p1LongState.observed + " cargo=" + p1LongState.best.cargo\n'
        b'        + " src=" + p1LongState.best.src + " dst=" + p1LongState.best.dst\n'
        b'        + " dist=" + p1LongState.best.distance\n'
        b'        + " candidate=" + (p1LongState.candidate != null ? 1 : 0));\n'
        b'  }\n\n',
        b'',
    ),
)

# FRONT-PAX-1 : retirer uniquement les fragments opt-in depuis la version
# publiee, afin de verifier les SHA historiques sur des octets inchanges.
# Patches exacts entre le commit precedent et la sonde, controles 1 fois.
FP1_SOURCE_PATCHES = {
    "candidates.nut": (
        (r'''}

function OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, ticksPerDay, probe = null)
{
  local roadMin = (AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP) * 2) + 1;
  if (bestBus == null || bestTrain == null || catalog.paxCargo < 0) {
    if (probe != null) probe.reason = (catalog.paxCargo < 0) ? "no_pax"
        : (bestBus == null ? "no_bus" : "no_train");
    return roadMin;
  }

  local kStop = catalog.costRoadBusStop;
'''.encode("utf-8"), r'''}

function OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, ticksPerDay)
{
  local roadMin = (AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP) * 2) + 1;
  if (bestBus == null || bestTrain == null || catalog.paxCargo < 0) return roadMin;

  local kStop = catalog.costRoadBusStop;
'''.encode("utf-8")),
        (r'''  local incBus = AICargo.GetCargoIncome(catalog.paxCargo, refD, transitBus.tointeger());
  local deltaM = incRail - incBus;
  if (probe != null) {
    probe.deltaM = deltaM;
    probe.num = num;
  }
  if (deltaM <= 0) {
    if (probe != null) probe.reason = "nonpositive_income_edge";
    return roadMin;
  }
  /* GetCargoIncome livre ici le gain TOTAL a refD, pas un gain par tuile.
   * L'equation qui isole d doit soustraire deux coefficients par tuile. */
'''.encode("utf-8"), r'''  local incBus = AICargo.GetCargoIncome(catalog.paxCargo, refD, transitBus.tointeger());
  local deltaM = incRail - incBus;
  if (deltaM <= 0) return roadMin;
  /* GetCargoIncome livre ici le gain TOTAL a refD, pas un gain par tuile.
   * L'equation qui isole d doit soustraire deux coefficients par tuile. */
'''.encode("utf-8")),
        (r'''  /* r_cible = 0,40 : ROI annuel vise pour amortir le capital fixe ferroviaire. */
  local denom = ((12.0 * M * deltaPerTile * 100.0) / 40.0) - cTile;
  if (probe != null) probe.denom = denom;
  if (denom <= 0) {
    if (probe != null) probe.reason = "nonpositive_denom";
    return roadMin;
  }
  if (num <= 0) {
    if (probe != null) probe.reason = "nonpositive_num";
    return roadMin;
  }
  local d = num / denom;
  if (probe != null) {
    probe.rawRoad = d;
    probe.reason = d < roadMin ? "below_road_min"
        : (d.tointeger() == roadMin ? "truncated_to_min" : "computed_road");
  }
  if (d < roadMin) d = roadMin;
  return d.tointeger();
}

function OpexComputeRailToAirDistance(bestTrain, bestPlane, ticksPerDay, airportType, probe = null)
{
  if (bestTrain == null || bestPlane == null) return OpexMapManhattanSpan();
'''.encode("utf-8"), r'''  /* r_cible = 0,40 : ROI annuel vise pour amortir le capital fixe ferroviaire. */
  local denom = ((12.0 * M * deltaPerTile * 100.0) / 40.0) - cTile;
  if (denom <= 0) return roadMin;
  if (num <= 0) return roadMin;
  local d = num / denom;
  if (d < roadMin) d = roadMin;
  return d.tointeger();
}

function OpexComputeRailToAirDistance(bestTrain, bestPlane, ticksPerDay, airportType)
{
  if (bestTrain == null || bestPlane == null) return OpexMapManhattanSpan();
'''.encode("utf-8")),
        (r'''  local tauAir = OpexDaysPerTile(vAir, ticksPerDay);
  local tFixe = OpexAirManeuverDays(bestPlane, airportType, airportType, ticksPerDay, planeDiv);
  if (probe != null) {
    probe.tauRail = tauRail;
    probe.tauAir = tauAir;
    probe.tFixe = tFixe;
  }
  if (tauRail <= tauAir) {
    if (probe != null) {
      probe.reason = "rail_as_fast";
      probe.rawRailAir = OpexMapManhattanSpan();
    }
    return OpexMapManhattanSpan();
  }
  local d = tFixe / (tauRail - tauAir);
  if (probe != null) {
    probe.rawRailAir = d;
    probe.reason = "physical";
  }
  if (d < 1.0) d = 1.0;
  return d.tointeger();
'''.encode("utf-8"), r'''  local tauAir = OpexDaysPerTile(vAir, ticksPerDay);
  local tFixe = OpexAirManeuverDays(bestPlane, airportType, airportType, ticksPerDay, planeDiv);
  if (tauRail <= tauAir) return OpexMapManhattanSpan();
  local d = tFixe / (tauRail - tauAir);
  if (d < 1.0) d = 1.0;
  return d.tointeger();
'''.encode("utf-8")),
        (r'''  if (roadMin < 1) roadMin = 1;

  local fp1Mark = FRONT_PAX1_CLAMP_PROBE ? OpexOpsMeasureBegin() : null;
  local bestBus = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_ROAD, pax) : null;
  local bestTrain = (pax >= 0) ? OpexGetEpochRailProfile(catalog, pax, 20) : null;
  local bestPlane = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_AIR, pax) : null;

  /* FRONT-PAX-1: sonde locale transitoire, jamais incluse dans catalog,
   * Save/Load, tri, ni construction. Un seul releve par refresh des bornes. */
  local fp1Probe = FRONT_PAX1_CLAMP_PROBE
      ? { reason = "unknown", deltaM = -1, num = -1, denom = -1, rawRoad = -1 }
      : null;
  local roadMax = OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, tpd, fp1Probe);
  if (roadMax < roadMin) roadMax = roadMin;
  local mapSpan = OpexMapManhattanSpan();
'''.encode("utf-8"), r'''  if (roadMin < 1) roadMin = 1;

  local bestBus = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_ROAD, pax) : null;
  local bestTrain = (pax >= 0) ? OpexGetEpochRailProfile(catalog, pax, 20) : null;
  local bestPlane = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_AIR, pax) : null;

  local roadMax = OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, tpd);
  if (roadMax < roadMin) roadMax = roadMin;
  local mapSpan = OpexMapManhattanSpan();
'''.encode("utf-8")),
        (r'''  local vRail = 0;
  local vAirEff = 0.0;
  local fp1AirProbe = FRONT_PAX1_CLAMP_PROBE
      ? { reason = "no_plane", tauRail = -1, tauAir = -1, tFixe = -1, rawRailAir = -1 }
      : null;
  if (bestPlane != null && bestTrain != null) {
    railAir = OpexComputeRailToAirDistance(bestTrain, bestPlane, tpd, airportType, fp1AirProbe);
    vRail = bestTrain.speed;
    vAirEff = AIEngine.GetMaxSpeed(bestPlane).tofloat() / OpexPlaneSpeedDivisor();
'''.encode("utf-8"), r'''  local vRail = 0;
  local vAirEff = 0.0;
  if (bestPlane != null && bestTrain != null) {
    railAir = OpexComputeRailToAirDistance(bestTrain, bestPlane, tpd, airportType);
    vRail = bestTrain.speed;
    vAirEff = AIEngine.GetMaxSpeed(bestPlane).tofloat() / OpexPlaneSpeedDivisor();
'''.encode("utf-8")),
        (r'''  } else if (bestPlane != null) {
    railAir = roadMax;
    if (fp1AirProbe != null) fp1AirProbe.reason = "no_train";
  }
  local fp1RailAirRaw = FRONT_PAX1_CLAMP_PROBE ? railAir : -1;

  local airMax = bestPlane ? OpexComputeAirMaxDistance(bestPlane, tpd, airportType, pax) : 0;
'''.encode("utf-8"), r'''  } else if (bestPlane != null) {
    railAir = roadMax;
  }

  local airMax = bestPlane ? OpexComputeAirMaxDistance(bestPlane, tpd, airportType, pax) : 0;
'''.encode("utf-8")),
        (r'''  };

  if (FRONT_PAX1_CLAMP_PROBE) {
    /* Inclut les calculs de bornes, avant les journaux ; le coût du journal
     * lui-même est distinct. Les valeurs -1 signifient non calculé. */
    local fp1Ops = OpexOpsMeasureEnd(fp1Mark);
    local fp1Clamp = fp1RailAirRaw > mapSpan ? "map_span"
        : (fp1RailAirRaw < roadMax ? "road_max"
        : (fp1RailAirRaw > railMax ? "rail_max" : "none"));
    /* OpexDecide modifie _currentTaskLogged : journaliser directement
     * pour garantir la passivite, y compris pendant un TASK actif. */
    local fp1Date = AIDate.GetCurrentDate();
    AILog.Info("OPEX " + AIDate.GetYear(fp1Date) + "-"
        + AIDate.GetMonth(fp1Date) + "-" + AIDate.GetDayOfMonth(fp1Date)
        + " FRONT_PAX_CLAMP road_reason=" + fp1Probe.reason
        + " road_raw=" + fp1Probe.rawRoad + " road_final=" + roadMax
        + " road_min=" + roadMin + " deltaM=" + fp1Probe.deltaM
        + " num=" + fp1Probe.num + " denom=" + fp1Probe.denom
        + " air_reason=" + fp1AirProbe.reason
        + " air_clamp=" + fp1Clamp
        + " rail_air_raw=" + fp1RailAirRaw
        + " rail_air_physical=" + fp1AirProbe.rawRailAir
        + " rail_air_final=" + railAir + " rail_max=" + railMax
        + " map_span=" + mapSpan + " airport_type="
        + (airportType == null ? -1 : airportType)
        + " rail_speed=" + vRail + " air_speed=" + vAirEff
        + " air_fixed=" + tFixe + " tau_rail=" + fp1AirProbe.tauRail
        + " tau_air=" + fp1AirProbe.tauAir + " tpd=" + tpd
        + " ops=" + fp1Ops);
  }

  if (DECISION_LOG) {
    OpexDecide("EPOCH_BOUNDS", "roadMin=" + roadMin + " roadMax=" + roadMax
'''.encode("utf-8"), r'''  };

  if (DECISION_LOG) {
    OpexDecide("EPOCH_BOUNDS", "roadMin=" + roadMin + " roadMax=" + roadMax
'''.encode("utf-8")),
    ),
    "globals_pre.nut": (
        (r'''V309_IDLE_PROBE <- false;
V309_IDLE_STATE <- null;
FRONT_PAX1_CLAMP_PROBE <- false; // Réglage indépendant, motifs des bornes PASS.
V284_RAIL_GROWTH <- 0; // 0 : master ; N : croissance fret apres N ans et 1 M£ disponible.
/* V294 : ponts/tunnels longs et recherche A* continue (defauts 0 = master inchange). */
'''.encode("utf-8"), r'''V309_IDLE_PROBE <- false;
V309_IDLE_STATE <- null;
V284_RAIL_GROWTH <- 0; // 0 : master ; N : croissance fret apres N ans et 1 M£ disponible.
/* V294 : ponts/tunnels longs et recherche A* continue (defauts 0 = master inchange). */
'''.encode("utf-8")),
    ),
    "info.nut": (
        (r'''      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "front_pax1_bounds_probe",
      description = "FRONT-PAX-1: passive one-log-per-bounds-refresh road/rail and rail/air clamp reasons, 0=off (default), 1=log; no candidate or policy changes",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    /* --- 1. Systeme et instrumentation --- */

'''.encode("utf-8"), r'''      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    /* --- 1. Systeme et instrumentation --- */

'''.encode("utf-8")),
    ),
    "settings.nut": (
        (r'''  V307_LONG_PROBE = (v307Probe != null && v307Probe > 0 && v307Probe <= 9) ? v307Probe : 0;
  V309_IDLE_PROBE = OpexProbeEnabled(67108864);
  FRONT_PAX1_CLAMP_PROBE = AIController.GetSetting("front_pax1_bounds_probe") == 1;
  local v307Year = AIController.GetSetting("v307_probe_year");
  V307_PROBE_YEAR = (v307Year != null && v307Year > 0 && v307Year <= 9) ? v307Year : 0;
'''.encode("utf-8"), r'''  V307_LONG_PROBE = (v307Probe != null && v307Probe > 0 && v307Probe <= 9) ? v307Probe : 0;
  V309_IDLE_PROBE = OpexProbeEnabled(67108864);
  local v307Year = AIController.GetSetting("v307_probe_year");
  V307_PROBE_YEAR = (v307Year != null && v307Year > 0 && v307Year <= 9) ? v307Year : 0;
'''.encode("utf-8")),
    ),
}

# The two PO01D-frozen producer files gained FP2 helpers and guarded call
# sites. Verify the precise independent helper contents and delete ONLY those
# additions for historical byte-hash checks. Never change the frozen digests.
FP2_PLANNING_BLOCK_START = b"/* FRONT-PAX-2 : un seul dossier"
FP2_PLANNING_BLOCK_END = b"/* 1. Preparation"
FP2_PLANNING_BLOCK_SHA256 = "065bb2d87059671e152c71e2d62818e551eb14fd72990bedf69770bdd145396c"
FP2_CANDIDATES_BLOCK_START = b"/* FRONT-PAX-2 : comparaison CINEMATIQUE"
FP2_CANDIDATES_BLOCK_END = b"function OpexComputeAirMaxDistance"
FP2_CANDIDATES_BLOCK_SHA256 = "cd0257813fb12f5982c074b27c0fcb21b6dd6340d902a63c824b08d75606e8ab"
FP2_PLANNING_INSERTS = (
    b'        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 0, sites[a], sites[b],\n'
    b'            airport, plane, distance, flightDistance, orderDistance, minDist);\n',
    b'        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 1, hub, site,\n'
    b'            airport, plane, distance, flightDistance, orderDistance, 20);\n',
    b'        if (ctx.fp2 != null) OpexFP2Shortlist(ctx, 2, hub1, hub2,\n'
    b'            airport, plane, distance, flightDistance, orderDistance, 20);\n',
    b'  /* Mutating evaluation is restricted to ON and to the completed scan.\n'
    b'   * Shadow reports only the selected references and arithmetic shortlist. */\n'
    b'  if (ctx.fp2 != null) OpexFP2Finalize(ctx);\n'
    b'  if (ctx.fp2 != null && ctx.sliced\n'
    b'      && ("frontPax2Bounded" in ctx.resumeState))\n'
    b'    delete ctx.resumeState.frontPax2Bounded;\n',
    b'    fp2 = null,\n',
    b'  if (FRONT_PAX2_BOUNDED_OVERLAP > 0 && paxBand == PAX_BAND_ALL\n'
    b'      && catalog != null && catalog.bounds != null) {\n'
    b'    if (resumeState != null && ("frontPax2Bounded" in resumeState)) {\n'
    b'      ctx.fp2 = resumeState.frontPax2Bounded;\n'
    b'    } else {\n'
    b'      ctx.fp2 = OpexFP2NewShortlist(catalog.bounds);\n'
    b'      if (resumeState != null) resumeState.frontPax2Bounded <- ctx.fp2;\n'
    b'    }\n'
    b'  }\n\n',
)


def _strip_fp2_block(raw, name, begin, end, digest):
    assert raw.count(begin) == 1, f"FP2 {name}: missing or repeated helper start"
    assert raw.count(end) == 1, f"FP2 {name}: missing or repeated original next function"
    start_at = raw.index(begin)
    end_at = raw.index(end, start_at)
    block = raw[start_at:end_at]
    assert hashlib.sha256(block).hexdigest() == digest, (
        f"FP2 {name}: helper changed; review and update its independent digest"
    )
    return raw[:start_at] + raw[end_at:]

# P3 adds one standalone helper block and exactly two guarded call sites to
# C117's existing lean path. Extract by unique function boundaries, verify the
# independent P3 block hash, then subtract only these additions before checking
# the frozen PO01D hash. A changed historical source remains an error.
P3_PROBES_BLOCK_PREFIX = b"/* P3 : cette signature n'est calculee que pour shadow/ON"
P3_PROBES_BLOCK_END = b"function OpexC117FlushLine(line, state)"
P3_PROBES_BLOCK_SHA256 = "a42b7b5002fb57e5c73c5fd291d7b6840d236cccf390e9b82fab96c6e1ae0215"
P3_PROBES_CALLS = (
    b'    if (P3_AIR_FLEET_YIELD > 0) OpexP3MatureFlush(line, state);\n',
    b'    if (P3_AIR_FLEET_YIELD > 0)\n'
    b'      OpexP3MatureSample(line, state, ageDays, live, mixedEngine);\n',
)


def historical_bytes(name, raw):
    dist_delta = DIST_BORNES_DELTAS.get(name)
    if dist_delta is not None:
        assert raw.count(dist_delta) == 1, f"DIST-BORNES {name}: opt-in fragment changed"
        raw = raw.replace(dist_delta, b"", 1)
    if name == "candidates.nut":
        edited, previous = DIST_BORNES_CANDIDATE_EDIT
        assert raw.count(edited) == 1, "DIST-BORNES candidates: reviewed opt-in guard changed"
        raw = raw.replace(edited, previous, 1)
    if name == "probes.nut":
        assert raw.count(C75_PROBES_DELTA) == 1, "C75 probes: guard changed or duplicated"
        raw = raw.replace(C75_PROBES_DELTA, b"", 1)
    c75_delta = C75_DELTAS.get(name)
    if c75_delta is not None:
        assert raw.count(c75_delta) == 1, f"C75 {name}: opt-in fragment changed or duplicated"
        raw = raw.replace(c75_delta, b"", 1)
    v286_delta = V286_DELTAS.get(name)
    if v286_delta is not None:
        assert raw.count(v286_delta) == 1, f"V286 {name}: opt-in addition changed or duplicated"
        raw = raw.replace(v286_delta, b"", 1)
    if name == "probes.nut":
        raw = _strip_fp2_block(raw, name, V286_PROBES_BLOCK_PREFIX,
                               V286_PROBES_BLOCK_END, V286_PROBES_BLOCK_SHA256)
        assert raw.count(V286_PROBES_CALL) == 1, "V286 profiled-loop call changed or duplicated"
        raw = raw.replace(V286_PROBES_CALL, b"", 1)
    for source, previous in FP1_SOURCE_PATCHES.get(name, ()):
        assert raw.count(source) == 1, f"FRONT-PAX-1 {name}: source diagnostique absente ou modifiee"
        raw = raw.replace(source, previous, 1)
    delta = {"info.nut": INFO_DELTA, "settings.nut": SETTINGS_DELTA}.get(name)
    if delta is not None:
        assert raw.count(delta) == 1, f"N75-MC {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(delta, b"", 1)
    p6_delta = P6_DELTAS.get(name)
    if p6_delta is not None:
        assert raw.count(p6_delta) == 1, f"P6 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(p6_delta, b"", 1)
    p3_delta = P3_DELTAS.get(name)
    if p3_delta is not None:
        assert raw.count(p3_delta) == 1, f"P3 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(p3_delta, b"", 1)
    fp2_delta = FP2_DELTAS.get(name)
    if fp2_delta is not None:
        assert raw.count(fp2_delta) == 1, f"FP2 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(fp2_delta, b"", 1)
    p2_delta = P2_DELTAS.get(name)
    if p2_delta is not None:
        assert raw.count(p2_delta) == 1, f"P2 {name}: expected precisely one unchanged opt-in fragment"
        raw = raw.replace(p2_delta, b"", 1)
    p1_delta = P1_DELTAS.get(name)
    if p1_delta is not None:
        assert raw.count(p1_delta) == 1, f"P1 {name}: expected one unchanged opt-in fragment"
        raw = raw.replace(p1_delta, b"", 1)
    if name == "builder_rail.nut":
        assert raw.count(P1_BUILDER_RAIL_DELTA) == 1, "P1 builder: safety guard changed or duplicated"
        raw = raw.replace(P1_BUILDER_RAIL_DELTA, b"", 1)
    if name == "air_planning.nut":
        raw = _strip_fp2_block(
            raw, name, FP2_PLANNING_BLOCK_START, FP2_PLANNING_BLOCK_END,
            FP2_PLANNING_BLOCK_SHA256,
        )
        for insert in FP2_PLANNING_INSERTS:
            assert raw.count(insert) == 1, f"FP2 {name}: guarded call changed or duplicated"
            raw = raw.replace(insert, b"", 1)
    if name == "candidates.nut":
        raw = _strip_fp2_block(raw, name, P1_CANDIDATES_BLOCK_START,
                               P1_CANDIDATES_BLOCK_END, P1_CANDIDATES_BLOCK_SHA256)
        for addition, original in P1_CANDIDATES_EDITS:
            assert raw.count(addition) == 1, "P1 candidates: addition changed or duplicated"
            raw = raw.replace(addition, original, 1)
        raw = _strip_fp2_block(
            raw, name, FP2_CANDIDATES_BLOCK_START, FP2_CANDIDATES_BLOCK_END,
            FP2_CANDIDATES_BLOCK_SHA256,
        )
    if name == "probes.nut":
        assert raw.count(P3_PROBES_BLOCK_PREFIX) == 1, "P3 probes helper begin must be unique"
        assert raw.count(P3_PROBES_BLOCK_END) == 1, "P3 probes helper end must be unique"
        begin = raw.index(P3_PROBES_BLOCK_PREFIX)
        end = raw.index(P3_PROBES_BLOCK_END, begin)
        block = raw[begin:end]
        assert hashlib.sha256(block).hexdigest() == P3_PROBES_BLOCK_SHA256, (
            "P3 probes helper changed: inspect and review its independent hash"
        )
        raw = raw[:begin] + raw[end:]
        for insertion in P3_PROBES_CALLS:
            assert raw.count(insertion) == 1, "P3 C117 call changed or duplicated"
            raw = raw.replace(insertion, b"", 1)
    return raw


def historical_info(info):
    return historical_bytes("info.nut", info.encode("utf-8")).decode("utf-8")
