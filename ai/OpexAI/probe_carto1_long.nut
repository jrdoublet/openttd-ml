/* CARTO-1 paires longues : mesure pre-enregistree sur RLW-04b, sans construction.
 * L'echantillon reservoir est fige par RLW-04b avant toute lecture de carte.
 * Reutilise le cache de blocs CARTO-1 et le vrai pathfinder rail de production.
 * Aucun resultat n'affecte la selection, les lignes ou les abandons. */

CARTO1_LONG_STATE <- null;

function OpexCarto1LongJob(pair, sample, mapState)
{
  local src = AIIndustry.GetLocation(pair.srcId);
  local dst = AIIndustry.GetLocation(pair.dstId);
  if (!AIMap.IsValidTile(src) || !AIMap.IsValidTile(dst)) return null;
  local ax = AIMap.GetTileX(src) / 8, ay = AIMap.GetTileY(src) / 8;
  local bx = AIMap.GetTileX(dst) / 8, by = AIMap.GetTileY(dst) / 8;
  local dx = bx - ax, dy = by - ay;
  local sx = dx < 0 ? -dx : dx, sy = dy < 0 ? -dy : dy;
  local key = "freight:" + pair.cargo + ":" + src + ":" + dst;
  return { sample = sample, key = key, cargo = pair.cargo, src = src, dst = dst,
    distance = pair.distance, ax = ax, ay = ay, bx = bx, by = by,
    steps = sx > sy ? sx : sy, i = 0, ids = [], member = {}, pos = 0,
    phase = "corridor", direct = 0, water = 0, relief = 0, town = 0,
    frontier = {}, visited = {}, dist = {}, back = {}, route = -1,
    routeBlocks = 0, target = by * mapState.nx + bx, ops = 0, ticks = 0 };
}

/* Deux sorties potentielles proches des industries. Memes interfaces de noeuds
 * [lead, station_exit] que OpexCreateRailPathfinder; elles sont virtuelles :
 * ce test qualifie le moteur A*, pas la faisabilite de gares physiques. */
function OpexCarto1LongEnds(center, other)
{
  local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
  local mx = AIMap.GetMapSizeX(), my = AIMap.GetMapSizeY();
  local dx = AIMap.GetTileX(other) - cx;
  local dy = AIMap.GetTileY(other) - cy;
  local sx = dx >= 0 ? 1 : -1, sy = dy >= 0 ? 1 : -1;
  /* Les orientations pointent generalement vers le but, sans modifier la
   * pathfinding elle-meme. Chercher un espace plat autour de chaque industrie. */
  local dirs = (dx * dx >= dy * dy) ? [[sx, 0], [0, sy], [0, -sy], [-sx, 0]]
                                     : [[0, sy], [sx, 0], [-sx, 0], [0, -sy]];
  local plans = [];
  for (local radius = 4; radius <= 12 && plans.len() < 2; radius += 2) {
    foreach (d in dirs) {
      local x = cx + d[0] * radius, y = cy + d[1] * radius;
      local px = x - d[0], py = y - d[1];
      if (x <= 1 || y <= 1 || px <= 1 || py <= 1 ||
          x >= mx - 1 || y >= my - 1 || px >= mx - 1 || py >= my - 1) continue;
      local lead = AIMap.GetTileIndex(x, y);
      local exit = AIMap.GetTileIndex(px, py);
      if (!AITile.IsBuildable(lead) || !AITile.IsBuildable(exit)
          || AITile.GetSlope(lead) != AITile.SLOPE_FLAT
          || AITile.GetSlope(exit) != AITile.SLOPE_FLAT) continue;
      plans.append({ lead = lead, station_exit = exit });
      if (plans.len() >= 2) break;
    }
  }
  return plans;
}

/* Les workers de vivier ou de rapport ne font pas de recherche ferroviaire.
 * Seules les recherches rail effectivement en phase search sont mutuellement
 * exclusives avec notre pathfinder shadow. */
function OpexCarto1LongRailBusy(ai)
{
  if (ai._railSearch != null && ("phase" in ai._railSearch)
      && ai._railSearch.phase == "search") return true;
  if (ai._activeWorker != null && ("kind" in ai._activeWorker)
      && (ai._activeWorker.kind == "rail_search" || ai._activeWorker.kind == "rail_stock")) return true;
  return false;
}

function OpexCarto1LongLogAstar(s, row, outcome)
{
  if (outcome != "OK" && outcome != "ABND" && outcome != "DEAD" && outcome != "NOPA") outcome = "NOPA";
  if (outcome != "OK") s.failures++;
  OpexDecide("CARTO1_LONG_ASTAR", "sample=" + row.sample + " key=" + row.key
    + " phase=end outcome=" + outcome + " search_ops=" + s.searchOps
    + " setup_ops=" + s.setupOps
    + " iters=" + s.iters + " started=" + (s.started ? 1 : 0)
    + " ticks=" + s.searchTicks + " overruns=" + s.overruns
    + " budget=" + HARD_ITERATION_CAP + " site=" + s.site);
  s.current = null;
  s.pf = null;
  s.seg = null;
  s.stage = "astar_next";
  s.index++;
}

function OpexCarto1LongAstarStart(ai, s, row)
{
  if (OpexCarto1LongRailBusy(ai)) return;
  if (AIController.GetOpsTillSuspend() < 8500) return;
  s.overruns = 0;
  s.searchOps = 0;
  s.setupOps = 0;
  s.iters = 0;
  s.searchTicks = 0;
  local mark = OpexOpsMeasureBegin();
  local a = OpexCarto1LongEnds(row.src, row.dst);
  local b = OpexCarto1LongEnds(row.dst, row.src);
  s.setupOps = OpexOpsMeasureEnd(mark);
  if (AIController.GetTick() != mark.tick) {
    s.overruns++;
    s.overrunsTotal++;
  }
  if (a.len() == 0 || b.len() == 0) {
    s.site = "missing_virtual_endpoint";
    s.started = false;
    s.setupOpsTotal += s.setupOps;
    OpexCarto1LongLogAstar(s, row, "NOPA");
    return;
  }
  local tick = AIController.GetTick();
  local weight = OpexRailAstarWeight(row.distance);
  mark = OpexOpsMeasureBegin();
  if (V294_RAIL_CONTINUOUS > 0) {
    s.pf = OpexCreateRailPathfinder(a, b, null, weight, null, null, null);
    s.seg = null;
  } else {
    s.seg = OpexCreateSegmentedSearch(a, b, HARD_ITERATION_CAP, null, weight, null, null, null);
    s.pf = null;
  }
  local used = OpexOpsMeasureEnd(mark);
  s.setupOps += used;
  if (AIController.GetTick() != mark.tick) {
    s.overruns++;
    s.overrunsTotal++;
  }
  s.setupOpsTotal += s.setupOps;
  s.started = s.pf != null || s.seg != null;
  s.site = s.started ? "virtual" : "no_pathfinder";
  s.searchStartTick = tick;
  if (!s.started) {
    OpexCarto1LongLogAstar(s, row, "NOPA");
    return;
  }
  s.stage = "astar";
  OpexDecide("CARTO1_LONG_ASTAR", "sample=" + row.sample + " key=" + row.key
    + " phase=start budget=" + HARD_ITERATION_CAP + " weight=" + weight
    + " path=" + (s.seg == null ? "continuous" : "segmented"));
}

function OpexCarto1LongAstarSlice(ai, s, row)
{
  /* Jamais deux recherches A* simultanees, meme si la recherche live a
   * commence apres la tranche precedente du banc. */
  if (OpexCarto1LongRailBusy(ai)) return;
  /* Un pas A* peut depasser 2 000 opcodes. A 6 000 et huit pas par
   * tranche, la premiere campagne comptait des franchissements de tick.
   * Revenir a un pas autonome avec reserve quasi complete par tour. */
  if (AIController.GetOpsTillSuspend() < 9500) return;
  local sliceTick = AIController.GetTick();
  local mark = OpexOpsMeasureBegin();
  local result = { done = false, stop = "CONT" };
  if (s.seg != null) {
    result = OpexAdvanceSegmentedSearch(s.seg, 1, sliceTick + BUILD_TICK_MARGIN);
    s.iters = result.iterations;
  } else {
    local path = s.pf.FindPath(1);
    s.iters++;
    if (path == null) result = { done = true, stop = "NOPA" };
    else if (path != false) result = { done = true, stop = "OK" };
    else if (s.iters >= HARD_ITERATION_CAP) result = { done = true, stop = "ABND" };
  }
  local used = OpexOpsMeasureEnd(mark);
  s.searchOps += used;
  if (AIController.GetTick() != sliceTick) s.overruns++;
  s.searchTicks = AIController.GetTick() - s.searchStartTick;
  if (result.done || s.iters >= HARD_ITERATION_CAP) {
    local outcome = result.done ? result.stop : "ABND";
    if (s.iters >= HARD_ITERATION_CAP && outcome == "CONT") outcome = "ABND";
    OpexCarto1LongLogAstar(s, row, outcome);
  }
}

function OpexCarto1LongSummary(s, phase)
{
  OpexDecide("CARTO1_LONG_SUMMARY", "phase=" + phase + " samples=" + s.rows.len()
    + " completed=" + s.index + " failures=" + s.failures
    + " costs=" + s.costs + " map_ops=" + s.mapOps + " search_ops=" + s.totalSearchOps
    + " setup_ops=" + s.setupOpsTotal
    + " overruns=" + s.overrunsTotal + " mapx=" + AIMap.GetMapSizeX()
    + " mapy=" + AIMap.GetMapSizeY() + " cap=" + HARD_ITERATION_CAP);
}

/* Une expansion FindPath(1) est atomique et peut depasser 10 000 opcodes.
 * Il est impossible de rattraper le tick deja franchi : arreter toute la
 * campagne shadow pour eviter de multiplier les franchissements. L'analyseur
 * refuse obligatoirement phase=unsafe, sans creer de fausse issue A*. */
function OpexCarto1LongUnsafe(s, row, reason)
{
  s.pf = null;
  s.seg = null;
  s.current = null;
  s.stage = "unsafe";
  s.finished = true;
  OpexDecide("CARTO1_LONG_SAFETY", "phase=abort reason=" + reason
    + " sample=" + row.sample + " key=" + row.key
    + " iters=" + s.iters + " overruns=" + s.overrunsTotal);
  OpexCarto1LongSummary(s, "unsafe");
}

function OpexCarto1LongStep(ai)
{
  if (CARTO2_SHADOW) return;
  if (!CARTO1_SHADOW || !RLW04B_SHADOW || ai._rlw04bState == null
      || !ai._rlw04bState.completed) return;
  if (CARTO1_STATE == null) OpexCarto1Init();
  if (CARTO1_LONG_STATE == null) {
    local rows = [];
    foreach (pair in ai._rlw04bState.sample) {
      local job = OpexCarto1LongJob(pair, rows.len(), CARTO1_STATE);
      if (job != null) rows.append(job);
    }
    CARTO1_LONG_STATE = { rows = rows, index = 0, mapIndex = 0,
      logIndex = 0, current = null,
      stage = "samples", pf = null, seg = null, started = false,
      site = "none", searchOps = 0, iters = 0, searchTicks = 0,
      searchStartTick = 0,
      overruns = 0, overrunsTotal = 0, totalSearchOps = 0,
      setupOps = 0, setupOpsTotal = 0,
      mapOps = 0, costs = 0, failures = 0, finished = false };
    OpexDecide("CARTO1_LONG_START", "samples=" + rows.len() + " pair_pool="
      + ai._rlw04bState.pairs + " seed=" + ai._rlw04bState.sampleSeed);
    return;
  }
  local s = CARTO1_LONG_STATE;
  if (s.finished) return;
  if (s.stage == "samples") {
    if (AIController.GetOpsTillSuspend() < 4000) return;
    if (s.logIndex < s.rows.len()) {
      local row = s.rows[s.logIndex++];
      OpexDecide("CARTO1_LONG_SAMPLE", "sample=" + row.sample
        + " key=" + row.key + " src=" + row.src + " dst=" + row.dst
        + " distance=" + row.distance);
      return;
    }
    s.stage = "map_next";
  }
  if (s.index >= s.rows.len() && s.mapIndex >= s.rows.len()) {
    s.finished = true;
    OpexCarto1LongSummary(s, "done");
    return;
  }
  if (s.stage == "map_next" && s.mapIndex >= s.rows.len()) s.stage = "astar_next";
  if (s.stage == "map_next") { s.current = s.rows[s.mapIndex]; s.stage = "map"; }
  if (s.stage == "map") {
    local row = s.current;
    if (AIController.GetOpsTillSuspend() < 8500) return;
    local callTick = AIController.GetTick();
    for (local n = 0; n < 8 && row.phase != "done" && row.phase != "skip"
        && AIController.GetTick() == callTick
        && AIController.GetOpsTillSuspend() >= 6000; n++) {
      local mark = OpexOpsMeasureBegin();
      if (row.phase == "corridor") OpexCarto1CorridorStep(CARTO1_STATE, row);
      else if (row.phase == "scan") OpexCarto1ScanStep(CARTO1_STATE, row);
      else if (row.phase == "route") OpexCarto1RouteStep(CARTO1_STATE, row);
      local ops = OpexOpsMeasureEnd(mark);
      row.ops += ops;
      s.mapOps += ops;
      if (AIController.GetTick() != mark.tick) { row.ticks++; s.overrunsTotal++; }
    }
    if (row.ticks > 0) {
      OpexCarto1LongUnsafe(s, row, "carto_tick_cross");
      return;
    }
    if (row.phase == "done" || row.phase == "skip") {
      OpexDecide("CARTO1_LONG_COST", "sample=" + row.sample + " key=" + row.key
        + " route=" + row.route + " direct=" + row.direct
        + " route_blocks=" + row.routeBlocks + " blocks=" + row.ids.len()
        + " ops=" + row.ops + " ticks=" + row.ticks
        + " valid=" + (row.route >= 0 ? 1 : 0));
      s.costs++;
      s.mapIndex++;
      s.stage = "map_next";
    }
    return;
  }
  if (s.stage == "astar_next") { s.current = s.rows[s.index]; s.stage = "prepare"; }
  local row = s.current;
  if (s.stage == "prepare") {
    OpexCarto1LongAstarStart(ai, s, row);
    if (s.overruns > 0) OpexCarto1LongUnsafe(s, row, "astar_setup_tick_cross");
    return;
  }
  if (s.stage == "astar") {
    local opsBefore = s.searchOps, overrunsBefore = s.overruns;
    OpexCarto1LongAstarSlice(ai, s, row);
    s.totalSearchOps += s.searchOps - opsBefore;
    s.overrunsTotal += s.overruns - overrunsBefore;
    if (s.overruns > overrunsBefore) {
      OpexCarto1LongUnsafe(s, row, "astar_slice_tick_cross");
    }
  }
}
