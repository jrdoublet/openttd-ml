/* CARTO-1: carte de couloirs rail a la demande, purement shadow (probes bit 25).
 * Une seule lecture full6 par bloc physique. Aucune commande de construction.
 * Etats transitoires: le cache et les jobs sont reconstruits apres Save/Load. */

CARTO1_STATE <- null;

function OpexCarto1Key(candidate)
{
  return candidate.kind + ":" + candidate.cargo + ":" + candidate.src + ":" + candidate.dst;
}

function OpexCarto1Init()
{
  local nx = AIMap.GetMapSizeX() / 8;
  local ny = AIMap.GetMapSizeY() / 8;
  CARTO1_STATE = { nx = nx, ny = ny, cache = {}, seen = {}, queue = [], current = null,
    lastProjects = null, blocks = 0, ops = 0, ticks = 0, over = 0, requests = 0,
    costs = 0, queueDrops = 0, date = AIDate.GetCurrentDate(), scans = 0,
    nextPortfolio = 0 };
  OpexDecide("CARTO1_START", "mapx=" + AIMap.GetMapSizeX() + " mapy=" + AIMap.GetMapSizeY()
    + " side=8 total_blocks=" + (nx * ny) + " pattern=full6 bit=25");
}

/* File plafonnee: une re-selection du meme candidat ne relance pas son corridor. */
function OpexCarto1Request(candidate, source)
{
  if (!CARTO1_SHADOW || CARTO2_SHADOW || candidate == null || !("kind" in candidate)
      || !("src" in candidate) || !("dst" in candidate) || !("cargo" in candidate)) return;
  if (CARTO1_STATE == null) OpexCarto1Init();
  if (!AIMap.IsValidTile(candidate.src) || !AIMap.IsValidTile(candidate.dst)) return;
  local state = CARTO1_STATE;
  local key = OpexCarto1Key(candidate);
  if (key in state.seen) return;
  if (state.requests >= 72 || state.queue.len() >= 16) {
    state.queueDrops++;
    return;
  }
  state.seen[key] <- true;
  local ax = AIMap.GetTileX(candidate.src) / 8;
  local ay = AIMap.GetTileY(candidate.src) / 8;
  local bx = AIMap.GetTileX(candidate.dst) / 8;
  local by = AIMap.GetTileY(candidate.dst) / 8;
  local dx = bx - ax, dy = by - ay;
  local sx = dx < 0 ? -dx : dx;
  local sy = dy < 0 ? -dy : dy;
  local steps = sx > sy ? sx : sy;
  local job = { key = key, src = candidate.src, dst = candidate.dst, source = source,
    ax = ax, ay = ay, bx = bx, by = by, steps = steps, i = 0,
    ids = [], member = {}, pos = 0, phase = "corridor", direct = 0, water = 0,
    relief = 0, town = 0, frontier = {}, visited = {}, dist = {}, back = {},
    route = -1, routeBlocks = 0, target = by * state.nx + bx };
  if (source == "astar") state.queue.insert(0, job);
  else state.queue.append(job);
  state.requests++;
  OpexDecide("CARTO1_QUEUE", "key=" + key + " source=" + source + " src=" + job.src
    + " dst=" + job.dst + " steps=" + steps + " pending=" + state.queue.len());
}

/* Courbe de Bresenham en coordonnees de blocs, elargie d'un bloc de chaque cote.
 * Construite progressivement (2 centres par tranche), pas de rectangle complet. */
function OpexCarto1CorridorStep(state, job)
{
  for (local n = 0; n < 2 && job.i <= job.steps; n++) {
    local k = job.i++;
    local x = job.ax + (job.steps == 0 ? 0 : (job.bx - job.ax) * k / job.steps);
    local y = job.ay + (job.steps == 0 ? 0 : (job.by - job.ay) * k / job.steps);
    if ("lineMember" in job) job.lineMember[y * state.nx + x] <- true;
    for (local oy = -1; oy <= 1; oy++) {
      for (local ox = -1; ox <= 1; ox++) {
        local xx = x + ox, yy = y + oy;
        if (xx < 0 || xx >= state.nx || yy < 0 || yy >= state.ny) continue;
        local id = yy * state.nx + xx;
        if (id in job.member) continue;
        job.member[id] <- true;
        job.ids.append(id);
      }
    }
  }
  if (job.i > job.steps) job.phase = job.ids.len() > 420 ? "skip" : "scan";
}

function OpexCarto1ReadBlock(state, id)
{
  local bx = id % state.nx, by = id / state.nx;
  local mark = OpexOpsMeasureBegin();
  /* V308 full6 utilise quatre points peripheriques puis les deux centraux. */
  local sample = OpexV308Arm(bx, by, 1);
  local s = sample.stats;
  /* GetTownAuthority est souvent valide sans bati : ne compter que les
   * maisons et routes vraiment presentes dans la cellule. */
  local price = 100 + (s.sea + s.lake) * 220 + s.river * 130
    + s.house * 90 + (s.house > 0 ? s.road : 0) * 25
    + s.obst * 100 + s.relief * 85;
  local record = { cost = price, water = s.sea + s.lake + s.river,
    town = s.house + (s.house > 0 ? s.road : 0), house = s.house,
    road = s.house > 0 ? s.road : 0,
    sea = s.sea + s.lake, river = s.river, relief = s.relief };
  state.cache[id] <- record;
  state.blocks++;
  local ops = OpexOpsMeasureEnd(mark);
  local ticks = AIController.GetTick() - mark.tick;
  state.ops += ops;
  state.ticks += ticks;
  if (ticks > 0) state.over++;
  OpexDecide("CARTO1_BLOCK", "id=" + id + " bx=" + bx + " by=" + by
    + " cost=" + price + " water=" + record.water + " town=" + record.town
    + " relief=" + record.relief + " ops=" + ops + " ticks=" + ticks);
}

function OpexCarto1ScanStep(state, job)
{
  if (job.pos >= job.ids.len()) {
    job.phase = "route";
    job.frontier[job.ay * state.nx + job.ax] <- true;
    job.dist[job.ay * state.nx + job.ax] <- 0;
    return;
  }
  local id = job.ids[job.pos];
  if (!(id in state.cache)) {
    /* full6 ~1150 opcodes dans V308. Reserve 5k avant toute API terrain. */
    if (AIController.GetOpsTillSuspend() < 5000) return;
    OpexCarto1ReadBlock(state, id);
  }
  local item = state.cache[id];
  job.direct += item.cost;
  job.water += item.water;
  job.relief += item.relief;
  job.town += item.town;
  job.pos++;
}

/* Dijkstra coarse sur le sous-graphe du couloir. Une expansion par tranche;
 * on traite les diagonales avec facteur 14/10. */
function OpexCarto1RouteStep(state, job)
{
  if (AIController.GetOpsTillSuspend() < 6000) return;
  local best = -1, score = 2147483647;
  foreach (id, active in job.frontier) {
    if (active && job.dist[id] < score) { score = job.dist[id]; best = id; }
  }
  if (best < 0 || best == job.target) {
    job.route = best == job.target ? score : -1;
    if (best == job.target) {
      local p = best;
      while (p in job.back && job.routeBlocks < 420) { job.routeBlocks++; p = job.back[p]; }
      job.routeBlocks++;
    }
    job.phase = "done";
    return;
  }
  delete job.frontier[best];
  job.visited[best] <- true;
  local x = best % state.nx, y = best / state.nx;
  for (local oy = -1; oy <= 1; oy++) {
    for (local ox = -1; ox <= 1; ox++) {
      if (ox == 0 && oy == 0) continue;
      local xx = x + ox, yy = y + oy;
      if (xx < 0 || yy < 0 || xx >= state.nx || yy >= state.ny) continue;
      local next = yy * state.nx + xx;
      if (!(next in job.member) || (next in job.visited)) continue;
      local weight = (state.cache[best].cost + state.cache[next].cost) / 2;
      local nextCost = score + (ox != 0 && oy != 0 ? weight * 14 / 10 : weight);
      if (!(next in job.dist) || nextCost < job.dist[next]) {
        job.dist[next] <- nextCost;
        job.back[next] <- best;
        job.frontier[next] <- true;
      }
    }
  }
}

function OpexCarto1Finish(state, job)
{
  if (job.phase == "done") {
    state.costs++;
    OpexDecide("CARTO1_COST", "key=" + job.key + " src=" + job.src + " dst=" + job.dst
      + " direct=" + job.direct + " route=" + job.route + " blocks=" + job.ids.len()
      + " route_blocks=" + job.routeBlocks + " water=" + job.water
      + " town=" + job.town + " relief=" + job.relief + " valid=" + (job.route >= 0 ? 1 : 0));
  } else {
    OpexDecide("CARTO1_SKIP", "key=" + job.key + " reason=corridor_too_large blocks=" + job.ids.len());
  }
  state.current = null;
}

function OpexCarto1Summary(state)
{
  local today = AIDate.GetCurrentDate();
  if (today - state.date < 30) return;
  state.date = today;
  OpexDecide("CARTO1_SUMMARY", "total_blocks=" + (state.nx * state.ny)
    + " read=" + state.blocks + " requests=" + state.requests + " costs=" + state.costs
    + " queued=" + state.queue.len() + " active=" + (state.current == null ? 0 : 1)
    + " drops=" + state.queueDrops + " ops=" + state.ops + " work_ops=" + state.scans
    + " ticks=" + state.ticks + " overruns=" + state.over);
}

function OpexCarto1Step(ai)
{
  if (!CARTO1_SHADOW) return;
  if (CARTO1_STATE == null) OpexCarto1Init();
  local state = CARTO1_STATE;
  /* Portefeuille rail reel seulement. Les candidats RLW-04b restent hors scope. */
  if (ai._projects != null && (ai._projects != state.lastProjects
      || AIDate.GetCurrentDate() >= state.nextPortfolio)) {
    state.lastProjects = ai._projects;
    state.nextPortfolio = AIDate.GetCurrentDate() + 30;
    if (("rail" in ai._projects) && ai._projects.rail != null
        && ("candidates" in ai._projects.rail)) {
      local rail = ai._projects.rail;
      local choices = ("best" in rail) && rail.best != null && rail.best.len() > 0
        ? rail.best : rail.candidates;
      local considered = 0;
      foreach (candidate in choices) {
        if (considered++ >= 6) break;
        OpexCarto1Request(candidate, "portfolio");
      }
    }
  }
  if (ai._railSearch != null && ai._railSearch.kind == "primary"
      && ai._railSearch.candidate != null && AIController.GetOpsTillSuspend() >= 7500) {
    OpexCarto1Request(ai._railSearch.candidate, "astar");
  }
  if (state.current == null && state.queue.len() > 0) {
    state.current = state.queue[0];
    state.queue.remove(0);
  }
  local job = state.current;
  if (job != null) {
    /* Trois lectures full6 max (3 x ~1250 opcodes observes sur 256/1024),
     * chaque iteration exige encore 6500 opcodes avant de commencer. */
    for (local n = 0; n < 3 && AIController.GetOpsTillSuspend() >= 6500; n++) {
      local mark = OpexOpsMeasureBegin();
      local phase = job.phase;
      if (phase == "corridor") OpexCarto1CorridorStep(state, job);
      else if (phase == "scan") OpexCarto1ScanStep(state, job);
      else if (phase == "route") OpexCarto1RouteStep(state, job);
      if (job.phase == "done" || job.phase == "skip") OpexCarto1Finish(state, job);
      local spent = OpexOpsMeasureEnd(mark);
      state.scans += spent;
      if (AIController.GetTick() != mark.tick) state.over++;
      if (phase == "route" || state.current == null) break;
    }
  }
  if (AIController.GetOpsTillSuspend() >= 2700) OpexCarto1Summary(state);
}

function OpexCarto1Astar(candidate, phase, outcome, iters)
{
  if (!CARTO1_SHADOW || candidate == null) return;
  OpexDecide("CARTO1_ASTAR", "phase=" + phase + " key=" + OpexCarto1Key(candidate)
    + " outcome=" + outcome + " iters=" + iters + " src=" + candidate.src + " dst=" + candidate.dst);
}
