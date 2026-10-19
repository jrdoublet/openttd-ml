/* PO-01 : diagnostic passif, active seulement pendant une reconstruction reactive. */
function OpexPO01Describe(owner)
{
  local layers = [];
  local modes = [];
  if (owner._c76Revisions == null || owner._c76AckRevisions == null)
    return { layers = ["bootstrap"], modes = ["air", "rail", "road", "water", "fleet"] };
  local r = owner._c76Revisions;
  local a = owner._c76AckRevisions;
  if (r.towns > a.towns) layers.append("towns");
  if (r.industries > a.industries) layers.append("industries");
  if (r.lines > a.lines) layers.append("lines");
  foreach (mode in ["air", "rail", "road", "water"]) {
    if (r.engines[mode] > a.engines[mode]) layers.append("engines." + mode);
  }
  foreach (mode in ["air", "rail", "road", "water", "fleet"]) {
    local affected = false;
    foreach (dep in owner._c76GetModeDeps(mode)) {
      foreach (layer in layers) if (dep == layer) affected = true;
    }
    if (affected) modes.append(mode);
  }
  return { layers = layers, modes = modes };
}

function OpexPO01ProbeBegin(owner)
{
  local cause = OpexPO01Describe(owner);
  local layers = "";
  foreach (layer in cause.layers) layers += (layers == "" ? "" : ",") + layer;
  local modes = "";
  foreach (mode in cause.modes) modes += (modes == "" ? "" : ",") + mode;
  PO01_PROBE_SEQUENCE++;
  PO01_PROBE_CONTEXT = "batch=" + PO01_PROBE_SEQUENCE + " cause=" + layers + " modes=" + modes;
  OpexDecide("PO01_REACTIVE", PO01_PROBE_CONTEXT);
  return PO01_PROBE_CONTEXT;
}

function OpexPO01ProbeCost(mark, phase, unit)
{
  local ops = OpexOpsMeasureEnd(mark);
  OpexDecide("PO01_COST", PO01_PROBE_CONTEXT + " phase=" + phase
      + " unit=" + unit + " ops=" + ops);
}

/* File de fond : aucun nouvel appel sur le chemin a 0, indices historiques conserves. */
function OpexPO01ExtendQueue(owner)
{
  owner._taskQueue.append({ name = "po01_reactive", dueCycle = 0, enabled = true });
}

function OpexPO01AirPending(owner)
{
  foreach (task in owner._taskQueue) {
    if (task.name == "catalog" && ("c78AirRebuild" in task)
        && task.c78AirRebuild != null) return true;
  }
  return false;
}

function OpexPO01ModeEnabled(mode)
{
  if (mode == "air") return MODE_AIR;
  if (mode == "rail") return MODE_RAIL;
  if (mode == "road") return MODE_ROAD && ROAD_BUILD_ENABLED;
  if (mode == "water") return MODE_WATER;
  return true;
}

function OpexPO01EmptyGenerated(projects)
{
  return { projects = [], rail = null, road = null, airPlan = null, waterPlan = null,
      airPlans = [], waterPlans = [], freightCargo = projects.freightCargo };
}

/* Un generateur par mode. Les generateurs feuilles conservent leurs propres locales ;
 * aucune comptabilite OpexBudget.begin/end ne reste ouverte entre deux reprises. */
function OpexPO01GenerateMode(owner, s, mode)
{
  local generated = OpexPO01EmptyGenerated(s.seed);
  local all = [];
  local stats = null;
  local iterator = null;
  if (mode == "rail") {
    ::OpexSitableCache = {};
    stats = OpexRailCandidateStats();
    iterator = OpexPO01PaxCandidates(s.catalog, s.lines, all, stats, s.abandoned);
    while (iterator.getstatus() != "dead") { resume iterator; yield null; }
    local cargoOrder = OpexFreightCargoOrder(s.catalog);
    local start = -1;
    for (local i = 0; i < cargoOrder.len(); i++) {
      if (cargoOrder[i] == generated.freightCargo) start = i;
    }
    for (local offset = 0; offset < cargoOrder.len(); offset++) {
      local cargo = cargoOrder[start >= 0 ? (start + offset) % cargoOrder.len() : offset];
      local previousCount = all.len();
      iterator = OpexPO01FreightCandidates(s.catalog, s.lines, all, stats, s.abandoned,
          null, null, cargo);
      while (iterator.getstatus() != "dead") { resume iterator; yield null; }
      if (all.len() > previousCount) { generated.freightCargo = cargo; break; }
    }
    generated.rail = { all = all.len(), candidates = all, best = OpexTopK(all, TOP_K),
        bands = OpexBands(all), stats = stats, opcodes = 0, profile = null };
  } else if (mode == "road") {
    stats = { pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
        townAcceptancePrefiltered = 0, economicsUnavailable = 0, profitTooLow = 0,
        profitNonPositive = 0, profitBelowFloorKept = 0, accepted = 0,
        roadDistanceShort = 0, roadDistanceLong = 0 };
    if (s.catalog.roadType >= 0) {
      iterator = OpexPO01RoadFreightCandidates(s.catalog, s.lines, all, stats, s.abandoned,
          null, generated.freightCargo);
      while (iterator.getstatus() != "dead") { resume iterator; yield null; }
    }
    generated.road = { all = all.len(), candidates = all, best = OpexTopK(all, ROAD_TOP_K),
        stats = stats, opcodes = 0, profile = null };
  } else if (mode == "water") {
    iterator = OpexPO01WaterPlans(s.catalog, s.lines, generated.waterPlans);
    while (iterator.getstatus() != "dead") { resume iterator; yield null; }
    generated.waterPlan = generated.waterPlans.len() > 0 ? generated.waterPlans[0] : null;
    foreach (plan in generated.waterPlans) {
      yield null;
      local project = OpexProjectFromWater(s.catalog, plan, 0);
      if (project != null) generated.projects.append(project);
    }
  }
  foreach (candidate in all) {
    yield null;
    if (OpexAbandonedPairKey(candidate) in s.abandoned) continue;
    local project = OpexProjectFromCandidate(candidate);
    if (project != null) generated.projects.append(project);
  }
  s.outputs.rawset(mode, generated);
  if (mode == "rail") s.seed.freightCargo = generated.freightCargo;
}

function OpexPO01CopyLines(lines)
{
  local copied = [];
  foreach (line in lines) {
    local record = clone line;
    if (("vehicles" in record) && record.vehicles != null) record.vehicles = clone record.vehicles;
    copied.append(record);
  }
  return copied;
}

/* Une etape de catalogue par passage ; seule la copie privee change. */
function OpexPO01RefreshLayer(s, layer)
{
  if (layer == "cargos") s.catalog._refreshCargos();
  else if (layer == "towns") s.catalog._refreshTowns();
  else if (layer == "industries") s.catalog._refreshIndustries();
  else if (layer == "engines.rail") s.catalog._refreshRail();
  else if (layer == "engines.road") s.catalog._refreshRoad();
  else if (layer == "engines.air") s.catalog._refreshAir();
  else if (layer == "engines.water") s.catalog._refreshWater();
}

/* Publication transactionnelle sur une copie du portefeuille LE PLUS RECENT : les autres
 * modes, les subventions et le stock rail ne sont jamais remplaces par une ancienne copie.
 * Pas de traitement d'evenements entre publication et acquittement (VM cooperative NoAI). */
function OpexPO01Publish(owner, s)
{
  local nextProjects = clone owner._projects;
  nextProjects.stats = clone owner._projects.stats;
  foreach (mode in s.modes) {
    if (mode == "fleet" || !(mode in s.outputs)) continue;
    local modeMark = (C39_INVALIDATION_PROBE || DECISION_LOG) ? OpexOpsMeasureBegin() : null;
    nextProjects = OpexRegenerateModeProjects(nextProjects, s.catalog, owner._budget,
        owner._lines, owner._abandonedPairs, mode, null, null, -1, s.outputs[mode]);
    if (modeMark != null) OpexDecide("PO01_PUBLISH_MODE", s.probeContext
        + " unit=" + mode + " ops=" + OpexOpsMeasureEnd(modeMark));
  }
  foreach (mode in s.modes) {
    if (mode != "fleet") continue;
    local fleetMark = (C39_INVALIDATION_PROBE || DECISION_LOG) ? OpexOpsMeasureBegin() : null;
    local fleetPlan = [];
    owner._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    nextProjects = OpexInjectFleetProjects(nextProjects, fleetPlan,
        owner._abandonedPairs, OpexAvailableCapital(), owner._lines);
    if (fleetMark != null) OpexDecide("PO01_PUBLISH_MODE", s.probeContext
        + " unit=fleet ops=" + OpexOpsMeasureEnd(fleetMark));
  }
  nextProjects = OpexReselectProjects(nextProjects, OpexAvailableCapital(),
      owner._abandonedPairs, owner._lines);
  owner._projects = nextProjects;
  owner._ranked = nextProjects.rail;
  owner._catalog = s.catalog;
  /* Tous les consommateurs de chaque couche du snapshot ont ete traites (ou mode coupe).
   * La fonction AC06 est monotone et ne lit jamais les revisions courantes a acquitter. */
  OpexAC06AcknowledgeSnapshot(owner, s.snapshot);
  if (owner._c76AnyLayerChanged()) owner._po01Pending = true;
}

function OpexPO01Step(owner)
{
  local tick = AIController.GetTick();
  if (owner._po01LastTick == tick || AIController.GetOpsTillSuspend() <= 2500) return false;
  owner._po01LastTick = tick;
  if (owner._c76ForceReloadRegen || owner._portfolioInvalidated) {
    /* Ne pas bloquer le filet de surete catalogue avec un lot devenu inutilisable. */
    if (owner._po01Job != null) owner._po01Pending = true;
    owner._po01Job = null;
    return false;
  }
  /* Ne jamais remplacer/devancer scan, publish OU apply AIR, ni ouvrir rail/route
   * entre deux tranches du scan initial (V143 reste exclu). */
  if (OpexPO01AirPending(owner) || owner._activeWorker != null
      || owner._projects == null || owner._catalog == null
      || owner._c76Revisions == null || owner._c76AckRevisions == null
      || (STAGED_BOOTSTRAP && owner._generationStage < OPEX_STAGE_COMPLETE)
      || (MODE_AIR && AIDate.GetYear(AIDate.GetCurrentDate()) == OPEX_START_YEAR)) return false;
  if (owner._po01Job == null) {
    if (!owner._po01Pending) return false;
    local description = OpexPO01Describe(owner);
    owner._po01Pending = false;
    if (description.layers.len() == 0) return false;
    /* Snapshot AVANT refresh/calcul. Les demandes tardives restent dans _po01Pending. */
    local snapshot = OpexAC06CaptureRevisionNumbers(owner);
    local modes = [];
    foreach (mode in description.modes) if (OpexPO01ModeEnabled(mode)) modes.append(mode);
    local layers = ["cargos"];
    local needed = {};
    foreach (mode in modes) {
      foreach (layer in owner._c76GetModeDeps(mode)) needed.rawset(layer, true);
    }
    /* Meme ordre que refresh() : rail fixe railCoverage avant villes/accepteurs. */
    foreach (layer in ["engines.rail", "towns", "industries", "engines.air",
        "engines.water", "engines.road"]) {
      if (layer in needed) layers.append(layer);
    }
    owner._po01Job = { snapshot = snapshot, modes = modes, layers = layers,
        layerCursor = 0, modeCursor = 0, iterator = null, outputs = {},
        seed = { freightCargo = owner._projects.freightCargo },
        catalog = clone owner._catalog, lines = OpexPO01CopyLines(owner._lines),
        abandoned = clone owner._abandonedPairs, airState = {}, airResult = {},
        ops = {}, totalOps = 0, probeContext = "" };
    owner._po01Job.catalog.year = AIDate.GetYear(AIDate.GetCurrentDate());
    if (C39_INVALIDATION_PROBE || DECISION_LOG) {
      owner._po01Job.probeContext = OpexPO01ProbeBegin(owner);
      OpexDecide("PO01_SNAPSHOT", owner._po01Job.probeContext
          + " towns=" + snapshot.towns + " industries=" + snapshot.industries
          + " lines=" + snapshot.lines + " engines_air=" + snapshot.engines_air
          + " engines_rail=" + snapshot.engines_rail + " engines_road=" + snapshot.engines_road
          + " engines_water=" + snapshot.engines_water);
    }
    PO01_PROBE_CONTEXT = null;
    return true;
  }
  local s = owner._po01Job;
  local phase = "";
  local unit = "";
  local mark = OpexOpsMeasureBegin();
  if (s.layerCursor < s.layers.len()) {
    phase = "layer";
    unit = s.layers[s.layerCursor++];
    OpexPO01RefreshLayer(s, unit);
  } else if (s.modeCursor < s.modes.len()) {
    phase = "mode";
    unit = s.modes[s.modeCursor];
    if (unit == "fleet") {
      /* La flotte est calculee au commit sur les lignes/capital courants. */
      s.modeCursor++;
    } else if (unit == "air") {
      local slice = OpexRegenerateAirProjectsSlice(owner._projects, s.catalog, owner._budget,
          s.lines, s.abandoned, s.airState, 4000, tick, null, -1, false, s.airResult);
      if (slice.done) {
        s.outputs.rawset("air", s.airResult.generated);
        s.modeCursor++;
      }
    } else {
      if (s.iterator == null) s.iterator = OpexPO01GenerateMode(owner, s, unit);
      /* Budget de tranche, sans emprunter le budget neuf apres une suspension moteur.
       * Chaque reprise feuille avance d'une unite (paire/noeud), puis rend la main. */
      while (s.iterator.getstatus() != "dead" && AIController.GetTick() == tick
          && AIController.GetOpsTillSuspend() > 2000 && OpexOpsMeasureEnd(mark) < 4000) {
        resume s.iterator;
      }
      if (s.iterator.getstatus() == "dead") { s.iterator = null; s.modeCursor++; }
    }
  } else {
    phase = "publish";
    unit = "all";
    OpexPO01Publish(owner, s);
    owner._po01Job = null;
  }
  local ops = OpexOpsMeasureEnd(mark);
  s.totalOps += ops;
  local key = phase + ":" + unit;
  s.ops.rawset(key, (key in s.ops ? s.ops[key] : 0) + ops);
  if (phase == "mode" && unit in s.outputs) {
    local generated = s.outputs[unit];
    local generationOps = s.ops[key];
    if (unit == "rail") generated.rail.opcodes = generationOps;
    if (unit == "road") generated.road.opcodes = generationOps;
    if (unit == "water") {
      local count = generated.waterPlans.len();
      foreach (project in generated.projects)
        project.planningOpcodes = count > 0 ? generationOps / count : generationOps;
    }
  }
  if (C39_INVALIDATION_PROBE || DECISION_LOG) {
    OpexDecide("PO01_SLICE", s.probeContext + " phase=" + phase + " unit=" + unit + " ops=" + ops
        + " total_ops=" + s.totalOps + " ticks=" + (AIController.GetTick() - tick));
    if (owner._po01Job == null) {
      foreach (name, total in s.ops)
        OpexDecide("PO01_BATCH", s.probeContext + " unit=" + name + " ops=" + total);
    }
  }
  return true;
}
