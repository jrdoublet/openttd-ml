/* V276 : transaction ephemere portee par catalog, jamais serialisee.
 * Le chemin historique reste accessible uniquement avec le reglage OFF.
 * Enumerateur bon marche -> AIList.Sort natif -> evaluation d'une paire.
 * Une evaluation economique reste atomique, comme un combo de sites AIR.
 * Aucune boucle quadratique ne se trouve dans cette operation atomique. */
V276_CAND_SLICES <- 0;
V276_CATALOG_TASK <- null;
V276_CARGO_YEAR <- -1;
V276_CARGO_MONTH <- -1;
V276_CARGO_ORDER <- null;
const V276_PUBLISH_EVERY = 50;
const V276_EVAL_CAP = 500;

function OpexV276Tick(owner)
{
  if (!OpexV276Pending()) return false;
  local tick = AIController.GetTick();
  local remaining = AIController.GetOpsTillSuspend() - 2000;
  if (remaining <= 1000) return false;
  return OpexV276Continue(owner, V276_CATALOG_TASK,
      remaining < 6000 ? remaining : 6000, tick + 1);
}

function OpexV276CargoOrder(catalog)
{
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  local month = AIDate.GetMonth(AIDate.GetCurrentDate());
  if (V276_CARGO_ORDER != null && V276_CARGO_YEAR == year
      && (V276_CAND_SLICES != 2 || V276_CARGO_MONTH == month)) return V276_CARGO_ORDER;
  local ranked = AIList();
  local bounds = OpexCatalogBounds(catalog);
  local days = (80.0 * OpexDaysPerTile(bounds.vRail > 0 ? bounds.vRail : 1,
                                      bounds.ticksPerDay)).tointeger();
  foreach (cargo, sources in catalog.producers) {
    if (cargo == catalog.paxCargo || sources.len() == 0) continue;
    local score = AICargo.GetCargoIncome(cargo, 80, days);
    if (V276_CAND_SLICES == 2) {
      /* Somme annuelle dans ce cache, jamais dans le worker par tranche. */
      local monthly = 0;
      foreach (source in sources)
        monthly += AIIndustry.GetLastMonthProduction(catalog.industries[source].id, cargo);
      score *= monthly;
    }
    ranked.AddItem(cargo, score);
  }
  ranked.Sort(AIList.SORT_BY_VALUE, false);
  local result = [];
  for (local cargo = ranked.Begin(); !ranked.IsEnd(); cargo = ranked.Next()) result.append(cargo);
  V276_CARGO_YEAR = year;
  V276_CARGO_MONTH = month;
  V276_CARGO_ORDER = result;
  return result;
}

function OpexV276Request(catalog, kind = null, id = -1)
{
  local task = V276_CATALOG_TASK;
  if (task == null) return;
  /* Ne jamais remplacer un curseur en vol. En opt-in, un refill V269
   * tardif demande une seconde passe, avec son contexte capture au tick
   * demandeur ; les requetes ordinaires suivent la logique historique. */
  if (("v276" in task) && task.v276 != null) {
    if (DIST_BORNES_V276_FREIGHT && V269_RAIL_LATE_RELAX > 0 && V269_RELAXED) {
      if (!("v276Request" in task) || task.v276Request == null)
        task.v276Request <- { catalog = catalog, kind = kind, id = id, v269LateFreight = true };
      else {
        if (task.v276Request.kind != kind || task.v276Request.id != id) {
          task.v276Request.kind = null;
          task.v276Request.id = -1;
        }
        task.v276Request.v269LateFreight = true;
      }
    }
    return;
  }
  if (!("v276Request" in task) || task.v276Request == null)
    task.v276Request <- { catalog = catalog, kind = kind, id = id,
      v269LateFreight = DIST_BORNES_V276_FREIGHT && V269_RAIL_LATE_RELAX > 0 && V269_RELAXED };
  else if (task.v276Request.kind != kind || task.v276Request.id != id) {
    task.v276Request.kind = null;
    task.v276Request.id = -1;
  }
  /* Plusieurs demandes peuvent etre coalescees avant l'execution V276. */
  if (DIST_BORNES_V276_FREIGHT && V269_RAIL_LATE_RELAX > 0 && V269_RELAXED)
    task.v276Request.v269LateFreight = true;
}

function OpexV276Published(catalog, kind = null, id = -1)
{
  OpexV276Request(catalog, kind, id);
  local task = V276_CATALOG_TASK;
  if (task != null && ("v276Rail" in task) && task.v276Rail != null) return OpexV276CopyResult(task.v276Rail);
  return OpexEmptyRailCandidates();
}

function OpexV276AddUnits(units, catalog, pax)
{
  if (pax) {
    units.append({ mode = "rail", cargo = catalog.paxCargo, pax = true, band = PAX_BAND_AIR_RAIL });
    units.append({ mode = "rail", cargo = catalog.paxCargo, pax = true, band = PAX_BAND_RAIL_ONLY });
  } else {
    foreach (cargo in OpexV276CargoOrder(catalog))
      units.append({ mode = "rail", cargo = cargo, pax = false, band = PAX_BAND_ALL });
  }
}

function OpexV276Start(owner, task)
{
  local request = task.v276Request;
  local catalog = clone request.catalog;
  /* refresh remplace ces collections ; clone les conteneurs mutables aussi. */
  catalog.towns = clone catalog.towns;
  catalog.industries = clone catalog.industries;
  catalog.producers = clone catalog.producers;
  catalog.acceptors = clone catalog.acceptors;
  catalog.townAcceptors = clone catalog.townAcceptors;
  catalog.bounds = clone OpexCatalogBounds(catalog);
  /* La demande V217 et son execution reprenable ne sont pas le meme tick. */
  if (DIST_BORNES_V276_FREIGHT)
    catalog.bounds.distBornesV269Relaxed <- request.v269LateFreight;
  local units = [];
  if (MODE_RAIL) {
    OpexV276AddUnits(units, catalog, !MODE_AIR);
    OpexV276AddUnits(units, catalog, MODE_AIR);
  }
  if (MODE_ROAD && ROAD_BUILD_ENABLED) {
    foreach (cargo in OpexV276CargoOrder(catalog))
      units.append({ mode = "road", cargo = cargo, pax = false, band = PAX_BAND_ROUTE_ONLY });
  }
  local batches = {};
  foreach (u in units) {
    local key = OpexV276UnitKey(u);
    if (("v276Batches" in task) && (key in task.v276Batches))
      batches.rawset(key, task.v276Batches[key]);
  }
  task.v276 <- { catalog = catalog, units = units, batches = batches, unit = 0, phase = "init",
    a = 0, b = 0, target = -1, targetScan = 0, targetA = -1, targetB = -1,
    prep = 0, pairs = AIList(), unitBest = [], lastAtom = "start", context = null,
    enumerated = 0, evaluated = 0, publications = 0, unitEvaluated = 0, lastPublished = -1,
    kind = request.kind, id = request.id,
    revisions = OpexAC06CaptureRevisionNumbers(owner) };
  task.v276Request = null;
}

/* Invariants calcules une fois par unite. Les positions des puits sont celles
 * attendues par le micro-catalogue (industries, puis villes). */
function OpexV276PrepareUnit(s, u)
{
  local towns = s.catalog.towns;
  local sources = !u.pax && (u.cargo in s.catalog.producers) ? s.catalog.producers[u.cargo] : [];
  local sinks = !u.pax && (u.cargo in s.catalog.acceptors) ? s.catalog.acceptors[u.cargo] : [];
  local townSinks = u.mode == "road" ? towns
      : (!u.pax && (u.cargo in s.catalog.townAcceptors) ? s.catalog.townAcceptors[u.cargo] : []);
  local destinations = [];
  if (u.pax) destinations = towns;
  else {
    foreach (i in sinks) destinations.append(s.catalog.industries[i]);
    foreach (town in townSinks) destinations.append(town);
  }
  local bounds = s.catalog.bounds;
  local maxDistance = u.mode == "road"
      ? (("roadGenMax" in bounds) ? bounds.roadGenMax : bounds.roadMax) : bounds.railMax;
  if (u.mode == "rail" && !u.pax && DIST_BORNES_V276_FREIGHT
      && ("distBornesV269Relaxed" in bounds) && bounds.distBornesV269Relaxed
      && V269_RAIL_MAX_DIST > maxDistance) maxDistance = V269_RAIL_MAX_DIST;
  if (u.pax && u.band == PAX_BAND_RAIL_ONLY) maxDistance = bounds.railAirOverlapMin - 1;
  local grid = OpexSpatialGrid();
  grid.Build(destinations, maxDistance);
  s.context = { towns = towns, sources = sources, sinks = sinks, townSinks = townSinks,
    destinations = destinations, n = destinations.len(), outer = u.pax ? towns.len() : sources.len(),
    grid = grid, neighbors = null,
    roadStats = { roadDistanceShort = 0, roadDistanceLong = 0 } };
  s.unitEvaluated = 0; s.lastPublished = -1;
  s.unitBest = []; s.pairs = AIList();
  s.phase = "prepare";
}

/* Une seule paire du catalogue original, avec indices remappes. Les gardes
 * metier (V163/V179/V264, courrier, origine, abandon) restent dans les generateurs.
 * Aucun appel OpexBuildCandidates ici : pas de recursion ni de drapeau global bypass. */
function OpexV276Evaluate(s, u, a, b, lines, abandonedPairs, budget)
{
  local catalog = clone s.catalog;
  local out = [];
  if (u.mode == "rail" && !MODE_RAIL) return out;
  if (u.mode == "road" && (!MODE_ROAD || !ROAD_BUILD_ENABLED)) return out;
  if (u.pax) {
    catalog.towns = a < b ? [s.catalog.towns[a], s.catalog.towns[b]]
        : [s.catalog.towns[b], s.catalog.towns[a]];
    OpexPaxCandidates(catalog, lines, out, OpexRailCandidateStats(), abandonedPairs,
                      null, null, null, u.band);
  } else {
    local sources = s.catalog.producers[u.cargo];
    local sinks = u.cargo in s.catalog.acceptors ? s.catalog.acceptors[u.cargo] : [];
    local source = s.catalog.industries[sources[a]];
    catalog.industries = [source];
    catalog.producers = {};
    catalog.producers.rawset(u.cargo, [0]);
    catalog.acceptors = {};
    catalog.townAcceptors = {};
    catalog.towns = [];
    if (b < sinks.len()) {
      catalog.industries.append(s.catalog.industries[sinks[b]]);
      catalog.acceptors.rawset(u.cargo, [1]);
    } else {
      local towns = u.mode == "road" ? s.catalog.towns : s.catalog.townAcceptors[u.cargo];
      local town = towns[b - sinks.len()];
      catalog.towns = [town];
      catalog.townAcceptors.rawset(u.cargo, [town]);
    }
    if (u.mode == "road") {
      /* Le wrapper historique classe seulement ce micro-catalogue. */
      local road = OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs, null, u.cargo, null, -1, true);
      out = road.candidates;
    } else OpexFreightCandidates(catalog, lines, out, OpexRailCandidateStats(),
                                 abandonedPairs, null, null, u.cargo);
  }
  return out;
}

function OpexV276Publish(owner, task, s, u)
{
  local key = OpexV276UnitKey(u);
  local batch = [];
  if (s.kind != null && (key in s.batches)) foreach (candidate in s.batches[key]) {
    local project = OpexProjectFromCandidate(candidate);
    if (project != null && !OpexProjectTouchesEntity(project, s.kind, s.id)) batch.append(candidate);
  }
  foreach (candidate in s.unitBest) batch.append(candidate);
  s.batches.rawset(key, batch);
  task.v276Batches <- s.batches;
  local pool = [];
  foreach (unit in s.units) {
    local unitKey = OpexV276UnitKey(unit);
    if (unit.mode != u.mode || !(unitKey in s.batches)) continue;
    foreach (candidate in s.batches[unitKey]) {
      if (OpexStagedCandidateStillValid(candidate, owner._lines, owner._abandonedPairs)) pool.append(candidate);
    }
  }
  /* Le vivier conserve TOP_K par unite, pas les ~100000 paires enumerees. */
  local generated = { projects = [], freightCargo = null, rail = null, road = null };
  local result = u.mode == "rail" ? OpexEmptyRailCandidates() : OpexProjectEmptyRoad();
  result.candidates = clone pool;
  result["best"] = OpexTopK(pool, TOP_K);
  result.all = pool.len();
  foreach (candidate in pool) {
    if (!OpexStagedCandidateStillValid(candidate, owner._lines, owner._abandonedPairs)) continue;
    local project = OpexProjectFromCandidate(candidate);
    if (project != null) generated.projects.append(project);
  }
  if (u.mode == "rail") { generated.rail = result; task.v276Rail <- result; }
  else { generated.road = result; task.v276Road <- result; }
  owner._projects = OpexApplyGeneratedModeProjects(owner._projects, generated,
      owner._abandonedPairs, u.mode, s.kind, s.id, owner._lines);
  if (u.mode == "rail") owner._ranked = result;
  s.publications++;
  s.lastPublished = s.unitEvaluated;
  if (DECISION_LOG) OpexDecide("V276_PUBLISH", "unit=" + s.unit
      + " evaluated=" + s.unitEvaluated + " kept=" + s.unitBest.len()
      + " mode=" + u.mode + " cargo=" + u.cargo + " band=" + u.band);
}

/* Plusieurs voisins par passage, invariants charges une fois ; garde entre
 * chaque paire, y compris celles rejetees, et curseur conserve entre ticks. */
function OpexV276Enumerate(s, u, mark, opsBudget, startTick, deadlineTick)
{
  local c = s.context;
  local towns = c.towns, sources = c.sources, sinks = c.sinks;
  local n = c.n;
  local targetedPax = u.pax && s.kind != null;
  local targetedFreight = !u.pax && s.kind != null && s.id >= 0;
  local outer = targetedPax ? (s.kind == "town" && s.target >= 0 ? 1 : 0) : c.outer;
  s.lastAtom = "enumerate";
  while (OpexOpsMeasureEnd(mark) < opsBudget && AIController.GetTick() == startTick
      && AIController.GetTick() < deadlineTick && AIController.GetOpsTillSuspend() >= 2000) {
    if (s.a >= outer || n == 0) {
      s.lastAtom = "native_sort";
      s.pairs.Sort(AIList.SORT_BY_VALUE, false); // natif, pas de comparateur Squirrel
      if (s.pairs.Count() > V276_EVAL_CAP) s.pairs.KeepTop(V276_EVAL_CAP);
      s.phase = "evaluate";
      return;
    }
    local wholeRow = !targetedFreight || s.a == s.targetA;
    local a = targetedPax ? s.target : s.a;
    local src = u.pax ? towns[a] : s.catalog.industries[sources[a]];
    if (c.neighbors == null) {
      c.neighbors = wholeRow ? c.grid.GetCandidatesAt(src.tile, u.pax && !targetedPax ? a : -1)
          : (s.targetB >= 0 ? [s.targetB] : []);
    }
    if (s.b >= c.neighbors.len()) { s.a++; s.b = 0; c.neighbors = null; continue; }
    local b = c.neighbors[s.b];
    s.b++;
    s.enumerated++;
    if (u.pax && a == b) continue;
    local dst = c.destinations[b];
    if (!u.pax && src.tile == dst.tile) continue;
    if (!u.pax && s.kind != null && s.id >= 0) {
      local touches = s.kind == "industry" ? src.id == s.id || (b < sinks.len() && dst.id == s.id)
          : b >= sinks.len() && dst.id == s.id;
      if (!touches) continue;
    }
    local distance = AIMap.DistanceManhattan(src.tile, dst.tile);
    if (u.mode == "rail") {
      if (!u.pax && DIST_BORNES_V276_FREIGHT
          && ("distBornesV269Relaxed" in s.catalog.bounds)
          && s.catalog.bounds.distBornesV269Relaxed
          && V269_RAIL_MAX_DIST > s.catalog.bounds.railMax) {
        if (distance < s.catalog.bounds.railMin || distance > V269_RAIL_MAX_DIST) continue;
      } else if (!OpexRailPaxPairInBand(s.catalog.bounds, distance, u.band)) continue;
    }
    if (u.mode == "road" && !OpexRoadDistanceAllowed(s.catalog, distance, c.roadStats)) continue;
    local score = u.pax ? (src.pop.tofloat() * dst.pop * sqrt(distance.tofloat())).tointeger() : distance;
    /* Prune par la meme priorite native avant que la liste depasse 1000 paires.
     * Les ex aequo au rang 500 peuvent dependre du moment du prune : verifier
     * la neutralite des trajectoires sur le banc apparie. */
    if (s.pairs.Count() >= V276_EVAL_CAP * 2) {
      s.pairs.Sort(AIList.SORT_BY_VALUE, false);
      s.pairs.KeepTop(V276_EVAL_CAP);
    }
    s.pairs.AddItem(a * n + b, score);
  }
}

/* Admission identique au scan AIR : mesurer aussi le reliquat du tick et
 * rendre la main apres une suspension VM. Le curseur est avance avant l'atome.
 * Les helpers economiques d'une paire et la publication restent atomiques. */
function OpexV276Continue(owner, task, opsBudget, deadlineTick)
{
  local mark = OpexOpsMeasureBegin();
  local startTick = AIController.GetTick();
  local progressed = false;
  if (!("v276" in task) || task.v276 == null) {
    if (!("v276Request" in task) || task.v276Request == null) return false;
    if (owner._projects == null) return false;
    /* AIR initial d'abord ; une publication suffit, ne pas attendre un scan
     * perpetuellement renouvele (famine PO01). */
    if (MODE_AIR && ("c78AirRebuild" in task) && task.c78AirRebuild != null
        && !task.c78AirRebuild.published) return false;
    OpexV276Start(owner, task);
    progressed = true;
  }
  local s = task.v276;
  while (s.unit < s.units.len()) {
    if (progressed && (OpexOpsMeasureEnd(mark) >= opsBudget
        || AIController.GetTick() != startTick
        || AIController.GetTick() >= deadlineTick
        || AIController.GetOpsTillSuspend() < 2000)) return OpexV276Yield(s, mark, opsBudget);
    progressed = true;
    local u = s.units[s.unit];
    if (s.phase == "init") { OpexV276PrepareUnit(s, u); continue; }
    local n = s.context.n;
    if (s.phase == "prepare") {
      local c = s.context;
      local towns = c.towns, sources = c.sources, sinks = c.sinks, townSinks = c.townSinks;
      /* Recherche de l'entite cible elle-meme reprenable, puis O(n) pax. */
      if (u.pax && s.kind == "town" && s.id >= 0 && s.targetScan < towns.len()) {
        local i = s.targetScan++;
        if (towns[i].id == s.id) s.target = i;
        continue;
      }
      if (!u.pax && s.kind != null && s.id >= 0 && s.prep < sources.len() + n) {
        local i = s.prep++;
        if (i < sources.len()) {
          if (s.kind == "industry" && s.catalog.industries[sources[i]].id == s.id) s.targetA = i;
        } else {
          local k = i - sources.len();
          if (k < sinks.len()) {
            if (s.kind == "industry" && s.catalog.industries[sinks[k]].id == s.id) s.targetB = k;
          } else if (s.kind == "town" && townSinks[k - sinks.len()].id == s.id) s.targetB = k;
        }
        continue;
      }
      s.phase = "enumerate";
      s.a = 0; s.b = 0;
      continue;
    }
    if (s.phase == "enumerate") {
      OpexV276Enumerate(s, u, mark, opsBudget, startTick, deadlineTick);
      continue;
    }
    if (s.phase == "evaluate") {
      if (s.pairs.Count() == 0 || s.unitEvaluated >= V276_EVAL_CAP) { s.phase = "publish"; continue; }
      local key = s.pairs.Begin();
      s.pairs.RemoveItem(key); // curseur exact, meme si l'evaluation suspend la VM
      ::OpexSitableCache = {}; // terrain/gares peuvent avoir change entre deux tranches
      s.lastAtom = "economics";
      local evaluated = OpexV276Evaluate(s, u, key / n, key % n,
                                        owner._lines, owner._abandonedPairs, owner._budget);
      foreach (candidate in evaluated) s.unitBest.append(candidate);
      s.unitBest = OpexTopK(s.unitBest, TOP_K);
      s.unitEvaluated++; s.evaluated++;
      if (s.unitEvaluated % V276_PUBLISH_EVERY == 0) s.phase = "publish";
      continue;
    }
    s.lastAtom = "publish";
    if (s.lastPublished != s.unitEvaluated) OpexV276Publish(owner, task, s, u);
    if (s.pairs.Count() > 0 && s.unitEvaluated < V276_EVAL_CAP) {
      s.phase = "evaluate";
      continue;
    }
    s.unit++;
    s.phase = "init";
    s.context = null;
    s.prep = 0; s.targetA = -1; s.targetB = -1;
  }
  if (s.kind == null) OpexV276Acknowledge(owner, s.revisions);
  task.v276 = null;
  return OpexV276Yield(s, mark, opsBudget);
}

function OpexV276Acknowledge(owner, snapshot)
{
  foreach (mode in ["rail", "rail_pax", "rail_freight", "road", "road_pax", "road_freight"]) {
    if ((mode == "rail" || mode == "rail_pax" || mode == "rail_freight") && !MODE_RAIL) continue;
    if ((mode == "road" || mode == "road_pax" || mode == "road_freight") && !MODE_ROAD) continue;
    local consumed = mode in owner._c76ModeConsumed ? owner._c76ModeConsumed[mode] : {};
    local sumRev = 0;
    foreach (layer in owner._c76GetModeDeps(mode)) {
      local covered = OpexAC06SnapshotLayer(snapshot, layer);
      local previous = layer in consumed ? consumed[layer] : 0;
      consumed.rawset(layer, covered > previous ? covered : previous);
      sumRev += consumed[layer];
    }
    owner._c76ModeConsumed.rawset(mode, consumed);
    owner._c76ModeConsumedRevision.rawset(mode, sumRev);
  }
}

function OpexV276DeferredMode(mode)
{
  return mode == "rail" || mode == "rail_pax" || mode == "rail_freight"
      || mode == "road" || mode == "road_pax" || mode == "road_freight";
}

/* Les consommateurs historiques peuvent fusionner/pruner leurs tableaux :
 * ne jamais leur donner les conteneurs de la derniere publication. */
function OpexV276CopyResult(result)
{
  local copied = clone result;
  copied.candidates = clone result.candidates;
  copied.rawset("best", clone result["best"]);
  return copied;
}

function OpexV276Pending()
{
  local task = V276_CATALOG_TASK;
  return task != null && ((("v276" in task) && task.v276 != null)
      || (("v276Request" in task) && task.v276Request != null));
}

function OpexV276UnitKey(u)
{
  return u.mode + "|" + u.cargo + "|" + u.band;
}

function OpexV276Yield(s, mark, opsBudget)
{
  if (DECISION_LOG) {
    local used = OpexOpsMeasureEnd(mark);
    OpexDecide("V276_SLICE", "unit=" + s.unit + " phase=" + s.phase
        + " enumerated=" + s.enumerated + " evaluated=" + s.evaluated
        + " publications=" + s.publications
        + " atom=" + s.lastAtom + " ops=" + used + " budget=" + opsBudget
        + " ticks=" + (AIController.GetTick() - mark.tick)
        + " overrun=" + (used > opsBudget ? 1 : 0));
  }
  return true;
}
