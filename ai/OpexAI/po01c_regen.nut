/* PO-01C: ephemeral reactive batch, private producers, selective publication. */
/* Opcodes per call, across ticks if needed (about 4 ticks, < 1 day). The hook runs once
 * per main-loop pass (~44 ticks measured), so 4000 left a batch at ~26 k ops/day. */
const PO01C_SLICE_OPS = 40000;
/* One resume gets 30k before propagation. Step can start a second unit near
 * 40k: target <70k plus one indivisible operation, not a hard API-call bound.
 * Only Step writes the mark, immediately before resume; never persisted. */
const PO01C_WORK_OPS = 30000;
PO01C_WORK_MARK <- null;
/* Transient diagnostic only, never part of Save/Load. Allocated only on logging. */
PO01C_WHERE <- null;
function OpexPO01CWhere(gen, site, idx)
{
  if (DECISION_LOG) {
    if (PO01C_WHERE == null) PO01C_WHERE = { gen = "", site = "", idx = -1 };
    PO01C_WHERE.gen = gen;
    PO01C_WHERE.site = site;
    PO01C_WHERE.idx = idx;
  }
}

function OpexPO01CUnitEnd(mark, phase, unit, gen, site)
{
  if (!DECISION_LOG) return;
  local ops = OpexOpsMeasureEnd(mark);
  if (ops > PO01C_SLICE_OPS) OpexDecide("PO01C_UNIT", "phase=" + phase
      + " mode=" + unit + " gen=" + gen + " site=" + site + " idx=-1 ops=" + ops);
}

/* Expressions keep historical evaluation order inside table literals. Only the
 * logged branch calls these wrappers; no extra yield or historical computation. */
function OpexPO01CLoggedTopK(all, count, mode)
{
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", mode + ":OpexTopK", -1);
  return OpexTopK(all, count);
}

function OpexPO01CLoggedBands(all)
{
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", "rail:OpexBands", -1);
  return OpexBands(all);
}
function OpexPO01CModeEnabled(mode)
{
  if (mode == "air") return MODE_AIR;
  if (mode == "rail") return MODE_RAIL;
  if (mode == "road") return MODE_ROAD && ROAD_BUILD_ENABLED;
  if (mode == "water") return MODE_WATER;
  return true;
}

function OpexPO01CEmptyGenerated(projects)
{
  return { projects = [], rail = null, road = null, airPlan = null, waterPlan = null,
      airPlans = [], waterPlans = [], freightCargo = projects.freightCargo };
}

function OpexPO01CGenerateMode(owner, s, mode)
{
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", "before_first_yield", -1);
  local generated = OpexPO01CEmptyGenerated(s.seed);
  local all = [];
  local stats = null;
  local iterator = null;
  if (mode == "rail") {
    ::OpexSitableCache = {};
    stats = OpexRailCandidateStats();
    iterator = OpexPO01CPaxCandidates(s.catalog, s.lines, all, stats, s.abandoned,
        null, null, null, PAX_BAND_ALL, null, -1, s.paxDiagnostics);
    while (iterator.getstatus() != "dead") { resume iterator; yield null; }
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", "rail:OpexFreightCargoOrder", -1);
    local cargoOrder = OpexFreightCargoOrder(s.catalog);
    local start = -1;
    for (local i = 0; i < cargoOrder.len(); i++) {
      if (cargoOrder[i] == generated.freightCargo) start = i;
    }
    for (local offset = 0; offset < cargoOrder.len(); offset++) {
      if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", "rail:freight_generator", offset);
      local cargo = cargoOrder[start >= 0 ? (start + offset) % cargoOrder.len() : offset];
      local previousCount = all.len();
      iterator = OpexPO01CFreightCandidates(s.catalog, s.lines, all, stats, s.abandoned,
          null, null, cargo);
      while (iterator.getstatus() != "dead") { resume iterator; yield null; }
      if (all.len() > previousCount) { generated.freightCargo = cargo; break; }
    }
    generated.rail = { all = all.len(), candidates = all,
        best = DECISION_LOG ? OpexPO01CLoggedTopK(all, TOP_K, mode) : OpexTopK(all, TOP_K),
        bands = DECISION_LOG ? OpexPO01CLoggedBands(all) : OpexBands(all), stats = stats, opcodes = 0, profile = null };
  } else if (mode == "road") {
    stats = { pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
        townAcceptancePrefiltered = 0, economicsUnavailable = 0, profitTooLow = 0,
        profitNonPositive = 0, profitBelowFloorKept = 0, accepted = 0,
        roadDistanceShort = 0, roadDistanceLong = 0 };
    if (s.catalog.roadType >= 0) {
      iterator = OpexPO01CRoadFreightCandidates(s.catalog, s.lines, all, stats, s.abandoned,
          null, generated.freightCargo);
      while (iterator.getstatus() != "dead") { resume iterator; yield null; }
    }
    generated.road = { all = all.len(), candidates = all,
        best = DECISION_LOG ? OpexPO01CLoggedTopK(all, ROAD_TOP_K, mode) : OpexTopK(all, ROAD_TOP_K),
        stats = stats, opcodes = 0, profile = null };
  } else if (mode == "water") {
    iterator = OpexPO01CWaterPlans(s.catalog, s.lines, generated.waterPlans);
    while (iterator.getstatus() != "dead") { resume iterator; yield null; }
    generated.waterPlan = generated.waterPlans.len() > 0 ? generated.waterPlans[0] : null;
    foreach (plan in generated.waterPlans) {
      yield null;
      local project = OpexProjectFromWater(s.catalog, plan, 0);
      if (project != null) generated.projects.append(project);
    }
  }
  foreach (candidateIndex, candidate in all) {
    yield null;
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", mode + ":project_filter", candidateIndex);
    if (OpexAbandonedPairKey(candidate) in s.abandoned) continue;
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", mode + ":OpexProjectFromCandidate", candidateIndex);
    local project = OpexProjectFromCandidate(candidate);
    if (project != null) generated.projects.append(project);
  }
  s.outputs.rawset(mode, generated);
  if (mode == "rail") s.seed.freightCargo = generated.freightCargo;
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CGenerateMode", "after_last_yield", -1);
}

/* AIR keeps its existing cursor protocol; nested generators only split the
 * atomic site/hub scans within each call. Null results use a separate box. */
function OpexPO01CGenerateAir(s)
{
  local best = null;
  while (!("done" in s.airCursor) || !s.airCursor.done) {
    local result = { value = null };
    local iterator = OpexPO01CAirPlans(result, s.catalog, s.lines, 0, s.airPlans,
        s.abandoned, PAX_BAND_ALL, -1, s.airCursor, PO01C_SLICE_OPS,
        AIController.GetTick() + 5);
    while (iterator.getstatus() != "dead") {
      /* Other AIR planners can run between checkpoints. Restore the same
       * cursor-owned C121 state that Prepare binds on synchronous entry. */
      if ("c121PlanPerf" in s.airCursor) C121_AIR_PLAN_PERF = s.airCursor.c121PlanPerf;
      if ("c121EndpointCache" in s.airCursor) C121_AIR_ENDPOINT_CACHE = s.airCursor.c121EndpointCache;
      resume iterator;
      yield null; // PO01C_CHECKPOINT
    }
    best = result.value;
  }
  local generated = OpexPO01CEmptyGenerated(s.seed);
  generated.airPlans = s.airPlans;
  generated.airPlan = best;
  foreach (plan in s.airPlans) {
    yield null; // PO01C_CHECKPOINT
    local project = OpexProjectFromAir(s.catalog, plan, 0);
    if (project != null) generated.projects.append(project);
  }
  s.outputs.rawset("air", generated);
}

function OpexPO01CCopyLines(lines)
{
  local copied = [];
  foreach (line in lines) {
    local record = clone line;
    if (("vehicles" in record) && record.vehicles != null) record.vehicles = clone record.vehicles;
    foreach (key in ["platformA", "platformB"])
      if ((key in record) && record[key] != null) record[key] = clone record[key];
    copied.append(record);
  }
  return copied;
}

/* Conservative topology records, not a lossy hash. Unknown baseline rebuilds.
 * AIR vehicle counts are retained for its hub/capacity guards. */
function OpexPO01CLineState(lines, catalog = null)
{
  local state = { rail = "", road = "", air = "", water = "", airRail = "" };
  foreach (line in lines) {
    local mode = ("mode" in line) ? line.mode : "rail";
    if (!(mode in state)) continue;
    local record = "|";
    foreach (key in ["lineId", "originA", "originB", "stationA", "stationB",
        "cargo", "srcTown", "dstTown", "scrapping", "deadStreak", "platformLength"])
      record += key + "=" + ((key in line) ? line[key].tostring() : "-") + ";";
    if (mode == "air" && ("vehicles" in line) && line.vehicles != null)
      record += "vehicles=" + line.vehicles.len();
    foreach (key in ["platformA", "platformB"]) {
      if (!(key in line) || line[key] == null) continue;
      foreach (field in ["direction", "length", "anchor", "step"])
        if (field in line[key]) record += key + "." + field + "=" + line[key][field] + ";";
    }
    state[mode] += record;
    if (mode == "air") {
      state.airRail += "|" + line.originA + "," + line.originB
          + "," + (("scrapping" in line) && line.scrapping ? 1 : 0);
      if (V275_AIR_TOWN_FREE > 0 && !(("scrapping" in line) && line.scrapping)) {
        local paxCargo = (catalog != null && ("paxCargo" in catalog)) ? catalog.paxCargo : -1;
        local railCov = (catalog != null && ("railCoverage" in catalog))
            ? catalog.railCoverage : AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
        local freeA = OpexV275AirTownFreeOrigin(line.originA, lines, paxCargo, railCov) ? 1 : 0;
        local freeB = OpexV275AirTownFreeOrigin(line.originB, lines, paxCargo, railCov) ? 1 : 0;
        state.airRail += "," + freeA + "," + freeB;
      }
    }
  }
  return state;
}

function OpexPO01CLinesAffect(owner, state, mode)
{
  local old = owner._po01cLineState;
  if (old == null || mode == "fleet") return true;
  if (mode == "road") return old.rail != state.rail || old.road != state.road;
  if (mode == "rail") return old.rail != state.rail
      || ((V275_RAIL_PAX_MM & 1) && old.airRail != state.airRail);
  return old[mode] != state[mode];
}

function OpexPO01CAirPending(owner)
{
  foreach (task in owner._taskQueue)
    if (task.name == "catalog" && ("c78AirRebuild" in task)
        && task.c78AirRebuild != null) return true;
  return false;
}

function OpexPO01CLayerFields(layer)
{
  if (layer == "towns") return ["towns", "townAcceptors"];
  if (layer == "industries") return ["industries", "producers", "acceptors"];
  if (layer == "engines.rail") return ["railType", "loco", "railLocos", "wagonByCargo",
      "locoByCargoWagons", "wagonChoicesByCargo", "platformLength", "maxTrainLength",
      "railCoverage", "freightTrainMultiplier", "costTrackPerTile", "costStation",
      "costRailDepot", "costRailSignal"];
  if (layer == "engines.road") return ["roadType", "roadEngineByCargo",
      "roadEngineChoicesByCargo", "maxRoadVehiclePrice", "costRoadPerTile",
      "costRoadBusStop", "costRoadTruckStop", "costRoadDepot"];
  if (layer == "engines.water") return ["ships", "maxShipPrice", "costDock", "costWaterDepot"];
  if (layer == "engines.air") return ["airport", "plane", "airCombos", "airPlaneChoicesByAirport"];
  return [];
}

function OpexPO01CLayerIterator(catalog, layer)
{
  if (layer == "towns") return OpexPO01CTowns(catalog);
  if (layer == "industries") return OpexPO01CIndustries(catalog);
  if (layer == "engines.rail") return OpexPO01CRail(catalog);
  if (layer == "engines.road") return OpexPO01CRoad(catalog);
  if (layer == "engines.air") return OpexPO01CAir(catalog);
  if (layer == "engines.water") return OpexPO01CWater(catalog);
  return null;
}

function OpexPO01CConsumed(owner, mode, layer)
{
  if (!(mode in owner._c76ModeConsumed)) return 0;
  local consumed = owner._c76ModeConsumed[mode];
  return layer in consumed ? consumed[layer] : 0;
}

/* Capture before any producer; defer only AIR, never the land/water lot.
 * C78 retains ownership of AIR while in flight. Its own AC06 publication will
 * cover AIR's revisions; no timeout fallback and no synchronous reconstruction. */
function OpexPO01CStart(owner)
{
  local snapshot = OpexAC06CaptureRevisionNumbers(owner);
  local state = OpexPO01CLineState(owner._lines, owner._catalog);
  local modes = [], coveredModes = [], layers = [], dirty = {};
  local airPending = OpexPO01CAirPending(owner);
  foreach (mode in ["rail", "road", "water", "fleet", "air"]) {
    local needed = false;
    foreach (layer in owner._c76GetModeDeps(mode)) {
      if (OpexAC06SnapshotLayer(snapshot, layer) <= OpexPO01CConsumed(owner, mode, layer)) continue;
      if (layer == "lines" && !OpexPO01CLinesAffect(owner, state, mode)) continue;
      needed = true;
    }
    if (needed && mode == "air" && airPending) continue;
    coveredModes.append(mode);
    if (!needed || !OpexPO01CModeEnabled(mode)) continue;
    modes.append(mode);
    foreach (layer in owner._c76GetModeDeps(mode)) {
      if (layer != "lines" && OpexAC06SnapshotLayer(snapshot, layer)
          > OpexPO01CConsumed(owner, mode, layer)) dirty.rawset(layer, true);
    }
  }
  if (modes.len() == 0) return null;
  foreach (layer in ["engines.rail", "towns", "industries", "engines.air", "engines.water", "engines.road"])
    if (layer in dirty) layers.append(layer);
  local catalog = clone owner._catalog;
  catalog.bounds = clone OpexCatalogBounds(catalog);
  local initial = {};
  foreach (layer in layers) foreach (field in OpexPO01CLayerFields(layer))
    initial.rawset(field, owner._catalog[field]);
  return { snapshot = snapshot, modes = modes, coveredModes = coveredModes, layers = layers,
      lineState = state, initial = initial, layerCursor = 0, modeCursor = 0,
      iterator = null, outputs = {}, catalog = catalog,
      seed = { freightCargo = owner._projects.freightCargo },
      lines = OpexPO01CCopyLines(owner._lines), abandoned = clone owner._abandonedPairs,
      airCursor = {}, airPlans = [], modeOps = {}, totalOps = 0, slices = 0, maxDays = 0,
      paxDiagnostics = DECISION_LOG ? { coverRebuilds = 0, sitableFills = 0 } : null,
      startTick = AIController.GetTick(), startDate = AIDate.GetCurrentDate() };
}

function OpexPO01CAcknowledge(owner, s)
{
  foreach (mode in s.coveredModes) {
    local aliases = [mode];
    if (mode == "rail" || mode == "road") {
      aliases.append(mode + "_pax"); aliases.append(mode + "_freight");
    }
    foreach (alias in aliases) {
      if (!(alias in owner._c76ModeConsumed)) owner._c76ModeConsumed.rawset(alias, {});
      local consumed = owner._c76ModeConsumed[alias];
      local sumRev = 0;
      foreach (layer in owner._c76GetModeDeps(alias)) {
        local covered = OpexAC06SnapshotLayer(s.snapshot, layer);
        local old = layer in consumed ? consumed[layer] : 0;
        consumed.rawset(layer, covered > old ? covered : old);
        sumRev += consumed[layer];
      }
      owner._c76ModeConsumedRevision.rawset(alias, sumRev);
    }
  }
  /* A shared revision is acknowledged only after EVERY consumer covers it.
   * Never read current revisions here (AC06 v2). */
  foreach (layer in ["towns", "industries", "lines", "engines.rail", "engines.road", "engines.air", "engines.water"]) {
    local covered = OpexAC06SnapshotLayer(s.snapshot, layer);
    foreach (mode in ["air", "rail", "road", "water", "fleet"]) {
      if (!OpexPO01CModeEnabled(mode)) continue;
      foreach (dep in owner._c76GetModeDeps(mode)) if (dep == layer) {
        local consumed = OpexPO01CConsumed(owner, mode, layer);
        if (consumed < covered) covered = consumed;
      }
    }
    local ack = owner._c76AckRevisions;
    if (layer == "towns" || layer == "industries" || layer == "lines") {
      if (covered > ack[layer]) ack[layer] = covered;
    } else {
      local mode = layer.slice(8);
      if (covered > ack.engines[mode]) ack.engines[mode] = covered;
    }
  }
  /* Do not erase AIR's baseline when that mode was deferred. */
  if (owner._po01cLineState == null) owner._po01cLineState = { rail = "?", road = "?", air = "?", water = "?", airRail = "?" };
  foreach (mode in s.coveredModes) if (mode != "fleet") {
    owner._po01cLineState[mode] = s.lineState[mode];
    if (mode == "rail") owner._po01cLineState.airRail = s.lineState.airRail;
  }
}

function OpexPO01CPublish(owner, s)
{
  /* C78 can start even after our final AIR slice. It keeps write ownership. */
  if (OpexPO01CAirPending(owner)) {
    for (local i = s.modes.len() - 1; i >= 0; i--)
      if (s.modes[i] == "air") s.modes.remove(i);
    for (local i = s.coveredModes.len() - 1; i >= 0; i--)
      if (s.coveredModes[i] == "air") s.coveredModes.remove(i);
  }
  /* Merge into the LATEST portfolio. Other modes and special alternatives
   * remain owned by their current producers. No catalogue object replacement. */
  local projects = clone owner._projects;
  projects.stats = clone owner._projects.stats;
  foreach (mode in s.modes) {
    if (mode == "fleet") {
      local fleet = [];
      local fleetMark = DECISION_LOG ? OpexOpsMeasureBegin() : null;
      owner._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleet);
      if (DECISION_LOG) OpexPO01CUnitEnd(fleetMark, "publish", "fleet", "OpexPO01CPublish", "resizeAirFleets");
      local generated = { projects = [] };
      foreach (entry in fleet) {
        local project = OpexProjectFromFleet(entry);
        if (project != null) generated.projects.append(project);
      }
      OpexPO01CMerge(projects, generated, "fleet");
    } else if (mode in s.outputs) {
      OpexPO01CMerge(projects, s.outputs[mode], mode);
    }
  }
  local selectionMark = DECISION_LOG ? OpexOpsMeasureBegin() : null;
  owner._projects = OpexReselectProjects(projects, OpexAvailableCapital(), owner._abandonedPairs, owner._lines);
  if (DECISION_LOG) OpexPO01CUnitEnd(selectionMark, "publish", "all", "OpexPO01CPublish", "OpexReselectProjects");
  owner._ranked = owner._projects.rail;
  foreach (layer in s.layers) {
    if (layer == "engines.air" && OpexPO01CAirPending(owner)) continue;
    foreach (field in OpexPO01CLayerFields(layer)) {
      /* A concurrent refresh wins over our older copy. */
      if (owner._catalog[field] == s.initial[field]) owner._catalog[field] = s.catalog[field];
    }
  }
  OpexPO01CAcknowledge(owner, s);
}

/* Same merge as OpexApplyGeneratedModeProjects, with ONE final selection for
 * the whole lot. Calling that helper per mode would repeat the costly filter. */
function OpexPO01CMerge(projects, generated, mode)
{
  local winners = {};
  local scratch = { modeCandidates = 0, modeAlternatives = 0 };
  foreach (key, entry in projects.candidateGroups) {
    local list = typeof entry == "array" ? entry : [entry];
    foreach (project in list) {
      if (project != null && (project.mode != mode
          || (mode != "fleet" && OpexProjectIsPersistentSpecial(project))))
        OpexProjectRememberAll(winners, project, scratch);
    }
  }
  foreach (project in generated.projects) OpexProjectRememberAll(winners, project, scratch);
  projects.candidateGroups = winners;
  if (mode == "rail") { projects.rail = generated.rail; projects.freightCargo = generated.freightCargo; }
  else if (mode == "road") { projects.road = generated.road; projects.freightCargo = generated.freightCargo; }
  else if (mode == "water") { projects.waterPlan = generated.waterPlan; projects.waterPlans = generated.waterPlans; }
  else if (mode == "air") { projects.airPlan = generated.airPlan; projects.airPlans = generated.airPlans; }
  OpexProjectsRecountGroups(projects);
}

function OpexPO01CLog(owner, s, phase)
{
  if (!DECISION_LOG) return;
  local modes = "", layers = "";
  foreach (mode in s.modes) modes += (modes == "" ? "" : ",") + mode;
  foreach (layer in s.layers) layers += (layers == "" ? "" : ",") + layer;
  local a = owner._c76AckRevisions;
  OpexDecide("PO01C_BATCH", "phase=" + phase + " modes=" + modes + " layers=" + layers
      + " ops=" + s.totalOps + " slices=" + s.slices + " ticks=" + (AIController.GetTick() - s.startTick)
      + " days=" + (AIDate.GetCurrentDate() - s.startDate) + " max_slice_days=" + s.maxDays
      + " cover_rebuilds=" + (s.paxDiagnostics != null ? s.paxDiagnostics.coverRebuilds : 0)
      + " sitable_fills=" + (s.paxDiagnostics != null ? s.paxDiagnostics.sitableFills : 0)
      + " ack_towns=" + a.towns + " ack_industries=" + a.industries + " ack_lines=" + a.lines
      + " ack_air=" + a.engines.air + " ack_rail=" + a.engines.rail
      + " ack_road=" + a.engines.road + " ack_water=" + a.engines.water);
  if (phase == "begin") OpexDecide("PO01C_SNAPSHOT", "towns=" + s.snapshot.towns
      + " industries=" + s.snapshot.industries + " lines=" + s.snapshot.lines
      + " air=" + s.snapshot.engines_air + " rail=" + s.snapshot.engines_rail
      + " road=" + s.snapshot.engines_road + " water=" + s.snapshot.engines_water);
}

function OpexPO01CStep(owner)
{
  local tick = AIController.GetTick();
  if (tick == owner._po01cLastTick || AIController.GetOpsTillSuspend() < 4000) return false;
  owner._po01cLastTick = tick;
  if (owner._c76ForceReloadRegen || owner._portfolioInvalidated) {
    if (owner._po01cJob != null) owner._po01cPending = true;
    owner._po01cJob = null;
    return false;
  }
  if (owner._projects == null || owner._catalog == null || owner._c76Revisions == null
      || owner._c76AckRevisions == null || (STAGED_BOOTSTRAP && owner._generationStage < OPEX_STAGE_COMPLETE)) return false;
  if (owner._po01cJob == null) {
    if (!owner._po01cPending) return false;
    owner._po01cJob = OpexPO01CStart(owner);
    if (owner._po01cJob == null) {
      owner._po01cPending = owner._c76AnyLayerChanged();
      return false;
    }
    owner._po01cPending = false;
    OpexPO01CLog(owner, owner._po01cJob, "begin");
    return true;
  }
  local s = owner._po01cJob;
  local mark = OpexOpsMeasureBegin();
  local date = AIDate.GetCurrentDate();
  local phase = "layer";
  local unit = s.modeCursor < s.modes.len() ? s.modes[s.modeCursor] : "none";
  if (s.layerCursor < s.layers.len()) {
    unit = s.layers[s.layerCursor];
    if (s.iterator == null) s.iterator = OpexPO01CLayerIterator(s.catalog, s.layers[s.layerCursor]);
  } else if (s.modeCursor < s.modes.len()) {
    phase = "mode";
    local mode = s.modes[s.modeCursor];
    if (mode == "fleet") { s.modeCursor++; }
    else if (mode == "air") {
      if (OpexPO01CAirPending(owner)) {
        /* C78 may have started after our snapshot. Release the non-AIR lot;
         * do not let its last unit hold all completed modes indefinitely. */
        s.iterator = null;
        s.modes.remove(s.modeCursor);
        for (local i = s.coveredModes.len() - 1; i >= 0; i--)
          if (s.coveredModes[i] == "air") s.coveredModes.remove(i);
        for (local i = s.layers.len() - 1; i >= 0; i--)
          if (s.layers[i] == "engines.air") s.layers.remove(i);
        return true;
      }
      if (s.iterator == null) s.iterator = OpexPO01CGenerateAir(s);
    } else if (s.iterator == null) s.iterator = OpexPO01CGenerateMode(owner, s, mode);
  } else {
    phase = "publish";
    if (owner._activeWorker != null && owner._activeWorker.kind == "regen_candidates") return false;
    OpexPO01CPublish(owner, s);
    if (DECISION_LOG) OpexPO01CUnitEnd(mark, phase, "all", "OpexPO01CPublish", "whole_publish");
    owner._po01cJob = null;
    if (owner._c76AnyLayerChanged()) owner._po01cPending = true;
  }
  if (s.iterator != null) {
    if (DECISION_LOG) {
      local largest = null;
      while (s.iterator.getstatus() != "dead" && OpexOpsMeasureEnd(mark) < PO01C_SLICE_OPS) {
        /* Seed each unit: no stale rail site when another mode starts. Nested
         * generators overwrite this only after entering their own work. */
        OpexPO01CWhere(phase == "layer" ? "OpexPO01CLayerIterator"
            : (unit == "air" ? "OpexPO01CGenerateAir" : "OpexPO01CGenerateMode"), "before_first_yield", -1);
        local unitMark = OpexOpsMeasureBegin();
        PO01C_WORK_MARK = unitMark;
        resume s.iterator;
        local unitOps = OpexOpsMeasureEnd(unitMark);
        if (unitOps > PO01C_SLICE_OPS && (largest == null || unitOps > largest.ops))
          largest = { gen = PO01C_WHERE.gen, site = PO01C_WHERE.site,
              idx = PO01C_WHERE.idx, ops = unitOps };
      }
      if (largest != null) OpexDecide("PO01C_UNIT", "phase=" + phase + " mode=" + unit
          + " gen=" + largest.gen + " site=" + largest.site + " idx=" + largest.idx
          + " ops=" + largest.ops);
    } else {
      while (s.iterator.getstatus() != "dead" && OpexOpsMeasureEnd(mark) < PO01C_SLICE_OPS) {
        PO01C_WORK_MARK = OpexOpsMeasureBegin();
        resume s.iterator;
      }
    }
    if (s.iterator.getstatus() == "dead") {
      s.iterator = null;
      if (phase == "layer") s.layerCursor++; else s.modeCursor++;
    }
  }
  local ops = OpexOpsMeasureEnd(mark);
  if (phase == "mode") {
    s.modeOps.rawset(unit, (unit in s.modeOps ? s.modeOps[unit] : 0) + ops);
    if (unit in s.outputs) {
      local generated = s.outputs[unit];
      if (unit == "rail") generated.rail.opcodes = s.modeOps[unit];
      if (unit == "road") generated.road.opcodes = s.modeOps[unit];
      local count = generated.projects.len();
      foreach (project in generated.projects)
        project.planningOpcodes <- count > 0 ? s.modeOps[unit] / count : s.modeOps[unit];
    }
  }
  local days = AIDate.GetCurrentDate() - date;
  if (days > s.maxDays) s.maxDays = days;
  s.totalOps += ops; s.slices++;
  if (DECISION_LOG) OpexDecide("PO01C_SLICE", "phase=" + phase + " ops=" + ops
      + " ticks=" + (AIController.GetTick() - tick) + " days=" + days);
  if (owner._po01cJob == null) {
    OpexPO01CLog(owner, s, "publish");
    if (C39_INVALIDATION_PROBE) owner._c76RecordRegen("split", s.totalOps, s.maxDays,
        AIDate.GetYear(AIDate.GetCurrentDate()), "reactive");
  } else if (DECISION_LOG && s.slices % 200 == 0) {
    OpexPO01CLog(owner, s, "progress");
  }
  return true;
}
