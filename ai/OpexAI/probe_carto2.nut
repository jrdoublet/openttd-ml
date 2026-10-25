/* CARTO-2: preparation passive des trajets rail longs en 1970-1974.
 * Activation explicite des bits probes 24+25+26. Aucune commande de pose.
 * Tous les etats sont ephemeres; aucune modification de Save/Load. */

CARTO2_STATE <- null;

function OpexCarto2NewRow(src, dst, cargo, sample, source, score, mapState, kind = "freight")
{
  if (!AIMap.IsValidTile(src) || !AIMap.IsValidTile(dst)) return null;
  local ax = AIMap.GetTileX(src) / 8, ay = AIMap.GetTileY(src) / 8;
  local bx = AIMap.GetTileX(dst) / 8, by = AIMap.GetTileY(dst) / 8;
  local dx = bx - ax, dy = by - ay;
  local sx = dx < 0 ? -dx : dx, sy = dy < 0 ? -dy : dy;
  return { id = sample, sample = sample, source = source,
    key = kind + ":" + cargo + ":" + src + ":" + dst,
    kind = kind, cargo = cargo, src = src, dst = dst,
    distance = AIMap.DistanceManhattan(src, dst), score = score,
    ax = ax, ay = ay, bx = bx, by = by, steps = sx > sy ? sx : sy,
    i = 0, ids = [], member = {}, lineMember = {}, pos = 0,
    phase = "corridor", direct = 0, water = 0, relief = 0, town = 0,
    houses = 0, roads = 0, realTowns = 0, crossings = 0, maxRelief = 0,
    lineCost = 0, lineOps = 0, bandOps = -1, lineBlocks = 0,
    routeWater = 0, routeRelief = 0, routeTown = 0, bridgeCandidates = 0,
    frontier = {}, visited = {}, dist = {}, back = {},
    route = -1, routeBlocks = 0, routeIds = [],
    target = by * mapState.nx + bx, ops = 0, ticks = 0,
    quote = -1, guideTiles = {}, guidePos = 0, guideTilePos = 0,
    free = null, guided = null, expires = -1,
    plansA = null, plansB = null, livePlans = false, planFrozen = false };
}

function OpexCarto2Init(ai)
{
  if (CARTO1_STATE == null) OpexCarto1Init();
  CARTO2_STATE = { phase = "collect", rows = [], cursor = 0, index = 0,
    mapIndex = 0, logIndex = 0, search = null, mapOps = 0,
    searchOps = 0, ticks = 0, stopped = false, lastSummary = -1,
    ready = {}, mapReads = 0, idleSteps = 0, slackSteps = 0,
    fullTurns = 0, fullTurnOps = 0, pausedTurns = 0, fullTurnLeft = 0,
    fullTurnMaxOps = 0, peakAstarOps = 0, consecutive = 0,
    astarTurnTick = -1, astarTurnLeft = 0,
    pauseEvents = 0, resumeEvents = 0,
    liveCount = 0, pairs = 0, complete = 0,
    townCenters = {}, townList = null, townScanDone = false };
  OpexDecide("CARTO2_START", "version=2b mapx=" + AIMap.GetMapSizeX()
    + " mapy=" + AIMap.GetMapSizeY() + " start_year=" + OPEX_START_YEAR
    + " years=5 seed=" + ai._rlw04bState.sampleSeed + " bit=24_25_26");
}

/* Une ville reelle possede un centre AITown.GetLocation et des tuiles
 * construites; AITile.GetTownAuthority seul ne prouve aucune urbanisation.
 * L'inventaire des centres est avance 4 identifiants par tranche. */
function OpexCarto2TownStep(s)
{
  if (s.townScanDone) return;
  if (s.townList == null) s.townList = AITownList();
  for (local n = 0; n < 4 && !s.townList.IsEmpty(); n++) {
    local id = s.townList.Begin();
    if (!AITown.IsValidTown(id)) { s.townList.RemoveItem(id); continue; }
    local tile = AITown.GetLocation(id);
    if (AIMap.IsValidTile(tile)) {
      local bx = AIMap.GetTileX(tile) / 8, by = AIMap.GetTileY(tile) / 8;
      s.townCenters[by * CARTO1_STATE.nx + bx] <- true;
    }
    s.townList.RemoveItem(id);
  }
  if (s.townList.IsEmpty()) s.townScanDone = true;
}

/* Insertion par score decroissant, sans tri capturant une variable locale.
 * Une seule paire evaluee par appel : production × revenu retenu lent. */
function OpexCarto2Insert(s, row)
{
  local n = s.rows.len();
  s.rows.append(row);
  while (n > 0 && s.rows[n - 1].score < row.score) {
    s.rows[n] = s.rows[n - 1];
    n--;
  }
  s.rows[n] = row;
}

function OpexCarto2Collect(ai, s)
{
  local sample = ai._rlw04bState.sample;
  if (s.cursor < sample.len()) {
    local p = sample[s.cursor++];
    if (!AIIndustry.IsValidIndustry(p.srcId) || !AIIndustry.IsValidIndustry(p.dstId)) return;
    local src = AIIndustry.GetLocation(p.srcId), dst = AIIndustry.GetLocation(p.dstId);
    local prod = AIIndustry.GetLastMonthProduction(p.srcId, p.cargo);
    if (prod < 0) prod = 0;
    local days = p.distance * OpexDaysPerTile(80.0, 74.0);
    local income = AICargo.GetCargoIncome(p.cargo, p.distance, days.tointeger() + 6);
    if (income < 0) income = 0;
    local score = prod * income;
    local row = OpexCarto2NewRow(src, dst, p.cargo, s.cursor - 1, "long",
      score, CARTO1_STATE);
    if (row != null) OpexCarto2Insert(s, row);
    return;
  }
  /* Les projets reels sont ajoutes a la cartographie, avec leur provenance,
   * sans concurrencer le panel RLW dans les comparaisons A*. */
  if (s.liveCount < 6 && ai._projects != null && ("rail" in ai._projects)
      && ai._projects.rail != null) {
    local rail = ai._projects.rail;
    local choices = ("best" in rail) && rail.best != null && rail.best.len() > 0
      ? rail.best : (("candidates" in rail) ? rail.candidates : null);
    if (choices != null) {
      foreach (cand in choices) {
        if (s.liveCount >= 6) break;
        if (cand == null || !("src" in cand) || !("dst" in cand)
            || !("cargo" in cand) || !("kind" in cand)) continue;
        local row = OpexCarto2NewRow(cand.src, cand.dst, cand.cargo,
          30 + s.liveCount, "live", 0, CARTO1_STATE, cand.kind);
        if (row == null) continue;
        if (("railPlan" in cand) && cand.railPlan != null
            && ("plansA" in cand.railPlan) && cand.railPlan.plansA != null
            && ("plansB" in cand.railPlan) && cand.railPlan.plansB != null) {
          row.plansA = OpexCarto2FreezePlans(cand.railPlan.plansA);
          row.plansB = OpexCarto2FreezePlans(cand.railPlan.plansB);
          row.livePlans = true;
        }
        local seen = false;
        foreach (previous in s.rows) {
          if (previous.key == row.key) { seen = true; break; }
        }
        if (seen) continue;
        s.rows.append(row);
        s.liveCount++;
      }
    }
  }
  s.pairs = s.rows.len();
  s.phase = "pairs";
}

/* Le constructeur reel reste prioritaire, mais son entree n'efface jamais
 * l'etat ni le chemin A* shadow : la reprise sera exclusivement hors rail live. */
function OpexCarto2YieldToLive()
{
  local s = CARTO2_STATE;
  if (!CARTO2_SHADOW || s == null || s.search == null) return;
  if (s.phase != "search_run" && s.phase != "search_trace") return;
  if (s.search.paused) return;
  s.search.paused = true;
  s.pauseEvents++;
  OpexDecide("CARTO2_PAUSE", "id=" + s.search.row.id
    + " mode=" + s.search.mode + " iters=" + s.search.iters);
}

/* Les tableaux du constructeur sont vivants. Copier les deux seules
 * coordonnees effectivement consommees par OpexCreateRailPathfinder. */
function OpexCarto2FreezePlans(plans)
{
  local frozen = [];
  if (plans == null) return frozen;
  foreach (p in plans) {
    if (p == null || !("lead" in p) || !("station_exit" in p)) continue;
    frozen.append({ lead = p.lead, station_exit = p.station_exit });
  }
  return frozen;
}

/* Ne jamais recalculer OpexPrepareRailRoute : il modifie les devis live.
 * Snapshot des plans physiques deja calcules par le constructeur normal. */
function OpexCarto2CaptureLivePlans(candidate, plan)
{
  local s = CARTO2_STATE;
  if (!CARTO2_SHADOW || s == null || plan == null
      || plan.plansA == null || plan.plansB == null) return;
  local key = candidate.kind + ":" + candidate.cargo + ":" + candidate.src + ":" + candidate.dst;
  foreach (row in s.rows) {
    if (row.source != "live" || row.key != key) continue;
    /* Aucune substitution de plans entre libre et guide, meme si le
     * portefeuille live renouvelle le candidat pendant la mesure. */
    if (row.planFrozen || row.free != null || row.plansA != null
        || (s.search != null && s.search.row == row)) return;
    row.plansA = OpexCarto2FreezePlans(plan.plansA);
    row.plansB = OpexCarto2FreezePlans(plan.plansB);
    row.livePlans = true;
    return;
  }
}

function OpexCarto2RecordBlock(row, id, item, ops)
{
  if (id in row.lineMember) {
    row.lineCost += item.cost;
    row.lineOps += ops;
    row.lineBlocks++;
  }
  row.houses += item.house;
  row.roads += item.road;
  if (CARTO2_STATE != null && (id in CARTO2_STATE.townCenters))
    row.realTowns++;
  /* Une cellule aquatique signale une traversee possible; les ponts ne sont
   * confirmes qu'a l'echelle des tuiles par le vrai moteur. */
  if (item.water > 0) row.crossings++;
  if (item.relief > row.maxRelief) row.maxRelief = item.relief;
}

/* Bresenham dedoublonne, STRICTEMENT les centres de blocs, jamais la
 * bande +/-1. OpexCarto1ReadBlock conserve le patron full6. */
function OpexCarto2LineStep(state, row)
{
  for (local n = 0; n < 2 && row.i <= row.steps; n++) {
    local k = row.i++;
    local x = row.ax + (row.steps == 0 ? 0 : (row.bx - row.ax) * k / row.steps);
    local y = row.ay + (row.steps == 0 ? 0 : (row.by - row.ay) * k / row.steps);
    local id = y * state.nx + x;
    if (id in row.member) continue;
    row.member[id] <- true;
    row.lineMember[id] <- true;
    row.ids.append(id);
  }
  if (row.i > row.steps) row.phase = row.ids.len() > 420 ? "skip" : "scan";
}

/* Le cache full6 et Dijkstra sont reutilises sans lire les deux bordures. */
function OpexCarto2MapSlice(s, row)
{
  local mark = OpexOpsMeasureBegin();
  local priorPos = row.pos;
  local priorOps = CARTO1_STATE.ops;
  local phase = row.phase;
  if (phase == "corridor") OpexCarto2LineStep(CARTO1_STATE, row);
  else if (phase == "scan") OpexCarto1ScanStep(CARTO1_STATE, row);
  else if (phase == "route") OpexCarto1RouteStep(CARTO1_STATE, row);
  if (phase == "scan" && row.pos > priorPos) {
    local id = row.ids[priorPos];
    OpexCarto2RecordBlock(row, id, CARTO1_STATE.cache[id], CARTO1_STATE.ops - priorOps);
  }
  local ops = OpexOpsMeasureEnd(mark);
  row.ops += ops;
  s.mapOps += ops;
  /* row.ticks est local au couloir ; le total s.ticks est comptabilise
   * UNE seule fois par OpexCarto2Unsafe lorsque le caller constate
   * mapping_tick (sinon ce franchissement apparait deux fois). */
  if (AIController.GetTick() != mark.tick) row.ticks++;
}

function OpexCarto2FinishMap(s, row)
{
  if (row.route >= 0) {
    local p = row.target;
    local count = 0;
    local priorWet = false;
    while (count < 420) {
      row.routeIds.append(p);
      local item = CARTO1_STATE.cache[p];
      local wet = item.water > 0;
      row.routeWater += item.water;
      row.routeRelief += item.relief;
      row.routeTown += item.town;
      if (wet && !priorWet) row.bridgeCandidates++;
      priorWet = wet;
      count++;
      if (!(p in row.back)) break;
      p = row.back[p];
    }
  }
  /* Devis d'ordre de grandeur, livres sterlings, non devis moteur.
   * Voie simple ~1000£/tuile, ouvrages/eau 15000£ par bloc concerne. */
  row.quote = row.route >= 0 ? row.routeBlocks * 8000
    + row.bridgeCandidates * 15000 + row.routeWater * 5000
    + row.routeRelief * 2500 + row.routeTown * 500 : -1;
  OpexDecide("CARTO2_COST", "id=" + row.id + " key=" + row.key
    + " source=" + row.source + " score=" + row.score + " map_mode=line"
    + " line_ops=" + row.lineOps + " band_ops=" + row.bandOps
    + " line_ticks=" + row.ticks + " band_ticks=-1"
    + " line_cells=" + row.lineBlocks + " band_cells=-1"
    + " line_cost=" + row.lineCost + " band_cost=" + row.direct
    + " route=" + row.route + " route_blocks=" + row.routeBlocks
    + " water=" + row.water + " crossings=" + row.crossings
    + " bridge_candidates=" + row.bridgeCandidates
    + " route_water=" + row.routeWater + " route_relief=" + row.routeRelief
    + " route_town=" + row.routeTown
    + " relief=" + row.relief + " max_relief=" + row.maxRelief
    + " houses=" + row.houses + " roads=" + row.roads
    + " real_towns=" + (s.townScanDone ? row.realTowns : -1) + " quote=" + row.quote
    + " town_centers_complete=" + (s.townScanDone ? 1 : 0)
    + " valid=" + (row.route >= 0 ? 1 : 0));
}

function OpexCarto2GuideSlice(s, row)
{
  /* La voie guidee utilise le parametre _guideTiles du vrai A* rail.
   * Construire progressivement les 64 tuiles de chaque bloc de route :
   * 16 ajouts par tour, sans A* en parallele. */
  for (local n = 0; n < 64 && row.guidePos < row.routeIds.len()
      && AIController.GetOpsTillSuspend() >= 3900; n++) {
    local id = row.routeIds[row.guidePos];
    local bx = id % CARTO1_STATE.nx, by = id / CARTO1_STATE.nx;
    local xx = bx * 8 + row.guideTilePos % 8;
    local yy = by * 8 + row.guideTilePos / 8;
    local tile = AIMap.GetTileIndex(xx, yy);
    row.guideTiles[tile] <- 0;
    row.guideTilePos++;
    if (row.guideTilePos == 64) { row.guideTilePos = 0; row.guidePos++; }
  }
  if (row.guidePos >= row.routeIds.len()) s.phase = "search_start";
}

function OpexCarto2StartSearch(ai, s, row, mode)
{
  if (OpexCarto1LongRailBusy(ai) || ai._railSearch != null) return;
  if (AIController.GetOpsTillSuspend() < 6000) return;
  local mark = OpexOpsMeasureBegin();
  if (mode == "guided" && row.route < 0) {
    s.search = { row = row, mode = mode, pf = null, iters = 0,
      ops = OpexOpsMeasureEnd(mark), ticks = 0, pathDist = -1,
      outcome = "NOPA", tail = null, paused = false };
    s.phase = "search_end";
    return;
  }
  /* Une seule photographie des extremites par paire: identique pour les
   * deux bras. Les projets live doivent utiliser des gares reelles. */
  if (row.plansA == null && row.source != "live") {
    row.plansA = OpexCarto1LongEnds(row.src, row.dst);
    row.plansB = OpexCarto1LongEnds(row.dst, row.src);
  }
  row.planFrozen = true;
  local a = row.plansA == null ? [] : row.plansA;
  local b = row.plansB == null ? [] : row.plansB;
  if (a.len() == 0 || b.len() == 0) {
    local setupOps = OpexOpsMeasureEnd(mark);
    local setupTicks = AIController.GetTick() - mark.tick;
    s.search = { row = row, mode = mode, pf = null, iters = 0,
      ops = setupOps, ticks = setupTicks, pathDist = -1,
      outcome = "NOPA", tail = null, paused = false };
    s.phase = "search_end";
    if (setupTicks > 0) OpexCarto2Unsafe(s, "search_setup_tick");
    return;
  }
  local weight = OpexRailAstarWeight(row.distance);
  local guide = (mode == "guided" && row.route >= 0) ? row.guideTiles : null;
  local pf = OpexCreateRailPathfinder(row.plansA, row.plansB, null, weight, null, guide, null);
  local used = OpexOpsMeasureEnd(mark);
  s.search = { row = row, mode = mode, pf = pf, iters = 0,
    ops = used, ticks = AIController.GetTick() - mark.tick, pathDist = -1,
    outcome = "CONT", tail = null, paused = false };
  s.phase = pf == null ? "search_end" : "search_run";
  if (pf == null) s.search.outcome = "NOPA";
  if (s.search.ticks > 0) OpexCarto2Unsafe(s, "search_setup_tick");
}

/* Etalonnage 1024 seed100 : ancien pas de 7844 opcodes ayant traverse
 * le tick faute de reserve. Au nouveau smoke, 9300 + dispatch bloquait
 * tout FindPath(1) : ~9177 opcodes seulement avant appel. Demander
 * 9000 opcodes reels restants, ou pic mesure + 1200 si superieur.
 * Aucun plafond : au-dela du budget, ceder au live plutot que forcer.
 * Ce seuil empirique NE borne PAS un pire cas inconnu : SAFETY demeure. */
function OpexCarto2AstarReserve(s)
{
  local reserve = 9000;
  if (s.peakAstarOps > 0 && s.peakAstarOps + 1200 > reserve)
    reserve = s.peakAstarOps + 1200;
  return reserve;
}

function OpexCarto2Slice(ai, s)
{
  local search = s.search;
  /* Une recherche reelle suspend le shadow sans perdre pf, son curseur,
   * ses iterations ni les extremites figees. */
  if (OpexCarto1LongRailBusy(ai) || ai._railSearch != null) {
    search.paused = true;
    return;
  }
  /* Admission exclusive du DEBUT d'un tour entier. Ne jamais lancer
   * l'A* cree par le setup du meme tour, ni deux FindPath(1) par tick.
   * Garder jusqu'a 500 opcodes de frais de dispatch depuis l'admission. */
  if (s.astarTurnTick != AIController.GetTick()
      || s.astarTurnLeft - AIController.GetOpsTillSuspend() > 500
      || AIController.GetOpsTillSuspend() < OpexCarto2AstarReserve(s)) return;
  if (search.paused) {
    s.resumeEvents++;
    OpexDecide("CARTO2_RESUME", "id=" + search.row.id
      + " mode=" + search.mode + " iters=" + search.iters);
  }
  search.paused = false;
  s.astarTurnTick = -1;  // Consommer l'unique permission AVANT FindPath.
  local mark = OpexOpsMeasureBegin();
  local path = search.pf.FindPath(1);
  search.iters++;
  local used = OpexOpsMeasureEnd(mark);
  search.ops += used;
  if (used > s.peakAstarOps) s.peakAstarOps = used;
  local crossed = AIController.GetTick() - mark.tick;
  search.ticks += crossed;
  if (crossed > 0) { OpexCarto2Unsafe(s, "astar_atomic_tick"); return; }
  if (path == null) { search.outcome = "NOPA"; s.phase = "search_end"; }
  else if (path != false) {
    search.outcome = "OK";
    search.tail = path;
    search.pathDist = 0;
    s.phase = "search_trace";
  } else if (search.iters >= HARD_ITERATION_CAP) {
    search.outcome = "ABND"; s.phase = "search_end";
  }
}

function OpexCarto2Trace(s)
{
  local search = s.search;
  for (local n = 0; n < 12 && search.tail != null; n++) {
    search.pathDist++;
    search.tail = search.tail.GetParent();
  }
  if (search.tail == null) s.phase = "search_end";
}

function OpexCarto2LogSearch(s)
{
  local q = s.search, row = q.row;
  local ready = q.outcome == "OK" && q.pathDist >= 0;
  OpexDecide("CARTO2_SEARCH", "id=" + row.id + " key=" + row.key
    + " source=" + row.source + " live_plans=" + (row.livePlans ? 1 : 0)
    + " mode=" + q.mode + " phase=end outcome=" + q.outcome
    + " iters=" + q.iters + " ops=" + q.ops + " ticks=" + q.ticks
    + " ready=" + (ready ? 1 : 0) + " path_dist=" + q.pathDist
    + " year=" + AIDate.GetYear(AIDate.GetCurrentDate()));
  s.searchOps += q.ops;
  if (q.mode == "free") {
    row.free = { outcome = q.outcome, iters = q.iters, ops = q.ops };
    s.phase = (row.route >= 0) ? "guide" : "search_start";
    if (row.route < 0) row.guideTiles = {};
  } else {
    row.guided = { outcome = q.outcome, iters = q.iters, ops = q.ops };
    if (ready) { row.expires = AIDate.GetCurrentDate() + 180; s.ready[row.key] <- row.expires; }
    s.index++;
    s.complete++;
    s.phase = s.mapIndex < s.rows.len() ? "map" : "search_start";
  }
  s.search = null;
}

function OpexCarto2Summary(s, phase)
{
  local ready = 0, date = AIDate.GetCurrentDate();
  foreach (key, expiry in s.ready) if (expiry >= date) ready++;
  OpexDecide("CARTO2_SUMMARY", "phase=" + phase + " pairs=" + s.pairs
    + " mapped=" + s.mapIndex + " completed=" + s.complete
    + " ready=" + ready + " map_ops=" + s.mapOps
    + " search_ops=" + s.searchOps + " ticks=" + s.ticks
    + " idle_steps=" + s.idleSteps + " slack_steps=" + s.slackSteps
    + " full_turns=" + s.fullTurns + " full_turn_ops=" + s.fullTurnOps
    + " paused_turns=" + s.pausedTurns + " peak_astar_ops=" + s.peakAstarOps
    + " pause_events=" + s.pauseEvents + " resume_events=" + s.resumeEvents
    + " town_centers_complete=" + (s.townScanDone ? 1 : 0)
    + " year=" + AIDate.GetYear(date));
}

function OpexCarto2Unsafe(s, reason)
{
  /* Le pas atomique est deja detecte par OpexCarto2Slice ; le wrapper
   * full_turn ne doit pas compter / journaliser deux fois le meme tick. */
  if (s.stopped) return;
  s.ticks++;
  OpexDecide("CARTO2_SAFETY", "phase=abort reason=" + reason
    + " id=" + (s.search != null ? s.search.row.id : s.mapIndex));
  s.search = null;
  s.stopped = true;
  OpexCarto2Summary(s, "unsafe");
}

function OpexCarto2Step(ai)
{
  if (!CARTO2_SHADOW || ai._rlw04bState == null || !ai._rlw04bState.completed) return;
  local today = AIDate.GetCurrentDate();
  local year = AIDate.GetYear(today);
  if (year < OPEX_START_YEAR || year > OPEX_START_YEAR + 4) return;
  if (CARTO2_STATE == null) OpexCarto2Init(ai);
  local s = CARTO2_STATE;
  if (s.stopped) return;
  /* Appele uniquement depuis un tour ENTIER reserve par V309, pas en
   * queue de boucle normale. Un appel traite une etape atomique. */
  if (AIController.GetOpsTillSuspend() < 2200) return;
  if (s.phase != "search_run" && AIController.GetOpsTillSuspend() < 4500) return;
  if (OpexCarto1LongRailBusy(ai)) return;
  /* Sur un tour A* autorise, ne pas entamer la reserve avec town scan. */
  if (s.phase != "search_run" && !s.townScanDone
      && AIController.GetOpsTillSuspend() >= 7400) {
    local townTick = AIController.GetTick();
    OpexCarto2TownStep(s);
    if (AIController.GetTick() != townTick) {
      OpexCarto2Unsafe(s, "town_scan_tick");
      return;
    }
  }
  if (s.phase == "collect") OpexCarto2Collect(ai, s);
  else if (s.phase == "pairs") {
    if (s.logIndex < s.rows.len()) {
      local row = s.rows[s.logIndex];
      row.id = s.logIndex++;
      OpexDecide("CARTO2_PAIR", "id=" + row.id + " key=" + row.key
        + " src=" + row.src + " dst=" + row.dst
        + " dist=" + row.distance + " score=" + row.score
        + " source=" + row.source);
    } else s.phase = "map";
  } else if (s.phase == "map") {
    if (s.mapIndex >= s.rows.len()) s.phase = "search_start";
    else {
      local row = s.rows[s.mapIndex];
      for (local i = 0; i < 3 && row.phase != "done" && row.phase != "skip"
          && AIController.GetOpsTillSuspend() >= 6500; i++) {
        OpexCarto2MapSlice(s, row);
        if (row.ticks > 0) { OpexCarto2Unsafe(s, "mapping_tick"); return; }
        if (row.phase == "route") break;
      }
      if (row.phase == "done" || row.phase == "skip") {
        OpexCarto2FinishMap(s, row);
        s.mapIndex++;
        s.index = s.mapIndex - 1;
        s.phase = "search_start";
      }
    }
  } else if (s.phase == "search_start") {
    if (s.index >= s.rows.len()) {
      OpexCarto2Summary(s, "done");
      s.stopped = true;
      return;
    }
    local row = s.rows[s.index];
    if (row.free == null) OpexCarto2StartSearch(ai, s, row, "free");
    else OpexCarto2StartSearch(ai, s, row, "guided");
  } else if (s.phase == "guide") OpexCarto2GuideSlice(s, s.rows[s.index]);
  else if (s.phase == "search_run") OpexCarto2Slice(ai, s);
  else if (s.phase == "search_trace") OpexCarto2Trace(s);
  else if (s.phase == "search_end") OpexCarto2LogSearch(s);
  if (today - s.lastSummary >= 180 && AIController.GetOpsTillSuspend() >= 4500) {
    s.lastSummary = today;
    OpexCarto2Summary(s, "progress");
  }
}

/* Eligibility: V309 a constate sur le dernier tour normal une absence
 * stable de projets financables. Reverifier juste AVANT de sauter le
 * gestionnaire live; au moindre doute ceder le tour entier au jeu normal. */
function OpexCarto2CanTakeTurn(ai)
{
  if (!CARTO2_SHADOW || !CARTO2_IDLE_READY || V309_IDLE_STATE == null
      || ai._rlw04bState == null || !ai._rlw04bState.completed
      || AIController.GetOpsTillSuspend() < 9300) return false;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (year < OPEX_START_YEAR || year > OPEX_START_YEAR + 4) return false;
  local v = V309_IDLE_STATE;
  if (v.priorSource != "unfunded_snapshot" || v.priorCost == null
      || v.priorCost <= 0 || OpexAvailableCapital() >= v.priorCost
      || OpexV309IdleRevisionKey(ai) != v.priorRevision) return false;
  /* Revalider exactement les empreintes O(1) du cache V309, y compris les
   * stats mutables. Un nouveau devis financable ne doit jamais etre masque
   * par un tableau best vide conserve a la meme adresse. */
  local portfolio = ai._projects;
  if (portfolio == null || portfolio != v.cachedPortfolio
      || SELECT_BISECT_STAMP != v.cachedSelectStamp) return false;
  local best = ("best" in portfolio) ? portfolio.best : null;
  if (best != v.cachedBest || v.cachedBestCount != 0
      || (best != null && best.len() != 0)) return false;
  local nextCost = -1, minCost = -1;
  if (("stats" in portfolio) && portfolio.stats != null) {
    if ("nextProjectCapital" in portfolio.stats)
      nextCost = portfolio.stats.nextProjectCapital;
    if ("minCapital" in portfolio.stats) minCost = portfolio.stats.minCapital;
  }
  if (nextCost != v.cachedNextCost || minCost != v.cachedMinCost) return false;
  if (ai._railSearch != null || OpexCarto1LongRailBusy(ai)) return false;
  if (ai._activeWorker != null || ai._railExpansion != null) return false;
  if (PO01C_REGEN_SPLIT && (ai._po01cPending || ai._po01cJob != null)) return false;
  /* Les intentions reactives sont traitees AVANT les taches periodiques. */
  if (ai._hasReactiveIntentions()) return false;
  /* La file normale contient toujours les taches periodiques : sa longueur
   * n'est pas un signe d'urgence. Trois tours max, puis un vrai tour complet. */
  if (CARTO2_STATE != null && (CARTO2_STATE.stopped || CARTO2_STATE.consecutive >= 3))
    return false;
  return true;
}

/* Un quantum dedie : plusieurs operations puis FindPath(1) repetes.
 * Cible maximale 9000/10000 opcodes, jamais un Sleep interne.
 * La reserve adaptative de FindPath(1) prime cette cible si le pas
 * atomique risque de consommer le reliquat du tick. */
function OpexCarto2FullTurn(ai)
{
  if (!OpexCarto2CanTakeTurn(ai)) return false;
  /* Un A* deja initialise n'obtient pas un tour vide quand le budget
   * au debut est trop court pour sa reserve + le cout du dispatch. */
  if (CARTO2_STATE != null && CARTO2_STATE.phase == "search_run"
      && AIController.GetOpsTillSuspend()
         < OpexCarto2AstarReserve(CARTO2_STATE) + 100) return false;
  CARTO2_IDLE_READY = false;
  local mark = OpexOpsMeasureBegin();
  local n = 0;
  if (CARTO2_STATE == null) OpexCarto2Init(ai);
  local s = CARTO2_STATE;
  /* La permission est accordee uniquement si search_run existait DEJA
   * a l'entree du tour. Si setup cree pf plus bas, permission reste -1
   * jusqu'au prochain tour, avec le meme pf/iters pour reprendre. */
  s.astarTurnTick = -1;
  s.astarTurnLeft = 0;
  if (s.phase == "search_run" && s.search != null
      && AIController.GetOpsTillSuspend() >= OpexCarto2AstarReserve(s) + 100) {
    s.astarTurnTick = mark.tick;
    s.astarTurnLeft = AIController.GetOpsTillSuspend();
  }
  s.fullTurns++;
  s.idleSteps++;
  s.consecutive++;
  while (!s.stopped && AIController.GetTick() == mark.tick
      && AIController.GetOpsTillSuspend() >= 2200 && n < 128
      && OpexOpsMeasureEnd(mark) < 9000) {
    local phase = s.phase;
    if (s.phase == "search_run" && s.astarTurnTick != mark.tick) break;
    if (phase != "search_run" && AIController.GetOpsTillSuspend() < 4500) break;
    if (phase == "search_run"
        && AIController.GetOpsTillSuspend() < OpexCarto2AstarReserve(s)) break;
    local prior = AIController.GetOpsTillSuspend();
    OpexCarto2Step(ai);
    n++;
    if (s.phase == phase && AIController.GetOpsTillSuspend() == prior) break;
    if (s.search != null && s.search.paused) { s.pausedTurns++; break; }
    if (AIController.GetOpsTillSuspend() <= 1000) break;
  }
  local used = OpexOpsMeasureEnd(mark);
  s.fullTurnOps += used;
  if (used > s.fullTurnMaxOps) s.fullTurnMaxOps = used;
  s.fullTurnLeft += AIController.GetOpsTillSuspend();
  s.astarTurnTick = -1;
  s.astarTurnLeft = 0;
  local crossed = AIController.GetTick() != mark.tick;
  if (crossed) OpexCarto2Unsafe(s, "full_turn_tick");
  /* Ne jamais classer un tick d'urgence comme tour CARTO2_TURN sain. */
  if (!crossed && AIController.GetOpsTillSuspend() >= 2500) {
    OpexDecide("CARTO2_TURN", "phase=full ops=" + used
      + " left=" + AIController.GetOpsTillSuspend()
      + " count=" + n + " year=" + AIDate.GetYear(AIDate.GetCurrentDate()));
  }
  return true;
}
