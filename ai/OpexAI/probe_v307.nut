/* V307 : banc de mesure des longs traces rail (21/10). Mesure seule, defaut 0.
 *
 * Au demarrage d'une partie neuve, sous v307_long_probe = N > 0, on tire N paires de villes par
 * tranche de distance Manhattan (120-179, 180-249, 250-349) et, pour chacune, sur la meme carte
 * figee (rien n'est construit pendant la sonde) :
 *   base    : la recherche segmentee de production, budget V307_ITERS au lieu du plafond de 5 000 ;
 *             reussir en <= HARD_ITERATION_CAP iterations = reussir au plafond actuel ;
 *   coarse  : un A* grossier sur des blocs de V307_SIDE tuiles echantillonnes (hauteur, eau,
 *             obstacles), qui predit faisabilite et longueur ;
 *   guided  : la meme recherche de production, guidee (guideTiles, cout x0,5 dedans, x2 dehors)
 *             par le couloir grossier dilate de V307_CORRIDOR blocs.
 * Chaque bras journalise iterations, opcodes, ticks, segments, longueur et cout du trace repricé
 * par la fonction de cout commune sans guide (comparable entre bras).
 * La sonde est bloquante : en partie de mesure seulement (solo AAAHogEx sans vehicule). */

const V307_SIDE = 8;
const V307_CORRIDOR = 1;
const V307_ITERS = 30000;
const V307_TOWNS = 40;
const V307_PLATFORM = 5;

function OpexV307Bin(dist)
{
  if (dist >= 120 && dist < 180) return 0;
  if (dist >= 180 && dist < 250) return 1;
  if (dist >= 250 && dist < 350) return 2;
  return -1;
}

/* Paires deterministes : les V307_TOWNS plus grandes villes, paires triees par produit des
 * populations, au plus 3 paires par ville, N par tranche. */
function OpexV307Pairs(perBin)
{
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
  towns.KeepTop(V307_TOWNS);
  local ids = [];
  for (local t = towns.Begin(); !towns.IsEnd(); t = towns.Next()) ids.push(t);
  local scored = AIList();
  local n = ids.len();
  for (local i = 0; i < n; i++) {
    for (local j = i + 1; j < n; j++) {
      local d = AIMap.DistanceManhattan(AITown.GetLocation(ids[i]), AITown.GetLocation(ids[j]));
      if (OpexV307Bin(d) < 0) continue;
      scored.AddItem(i * 1000 + j, AITown.GetPopulation(ids[i]) * AITown.GetPopulation(ids[j]));
    }
  }
  scored.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
  local used = {};
  local taken = [0, 0, 0];
  local pairs = [];
  for (local k = scored.Begin(); !scored.IsEnd(); k = scored.Next()) {
    local a = ids[k / 1000], b = ids[k % 1000];
    local d = AIMap.DistanceManhattan(AITown.GetLocation(a), AITown.GetLocation(b));
    local bin = OpexV307Bin(d);
    if (taken[bin] >= perBin) continue;
    local ua = (a in used) ? used[a] : 0, ub = (b in used) ? used[b] : 0;
    if (ua >= 3 || ub >= 3) continue;
    used[a] <- ua + 1;
    used[b] <- ub + 1;
    taken[bin]++;
    pairs.push({ a = a, b = b, dist = d, bin = bin });
  }
  return pairs;
}

/* Echantillon d'un bloc : 5 tuiles (centre et quarts). Memo par bloc. */
function OpexV307Block(memo, bx, by)
{
  local id = by * 10000 + bx;
  if (id in memo) return memo[id];
  local offs = [[V307_SIDE / 2, V307_SIDE / 2], [V307_SIDE / 4, V307_SIDE / 4],
                [3 * V307_SIDE / 4, V307_SIDE / 4], [V307_SIDE / 4, 3 * V307_SIDE / 4],
                [3 * V307_SIDE / 4, 3 * V307_SIDE / 4]];
  local s = { n = 0, h = 0, water = 0, obst = 0 };
  foreach (o in offs) {
    local tile = AIMap.GetTileIndex(bx * V307_SIDE + o[0], by * V307_SIDE + o[1]);
    if (!AIMap.IsValidTile(tile)) continue;
    s.n++;
    s.h += AITile.GetMaxHeight(tile);
    if (AITile.IsWaterTile(tile)) s.water++;
    else if (!AITile.IsBuildable(tile) && !AIRoad.IsRoadTile(tile)) s.obst++;
  }
  memo[id] <- s;
  return s;
}

/* Cout d'un pas de bloc, en dixiemes de tuile : longueur, pente moyenne, eau et obstacles. */
function OpexV307StepCost(a, b, diag)
{
  local len = diag ? V307_SIDE * 14 : V307_SIDE * 10;
  if (b.n == 0) return -1;
  local dh = a.n > 0 ? abs(b.h / b.n - a.h / a.n) : 0;
  return len + (len * (3 * b.water + 2 * b.obst)) / 5 + dh * 40;
}

/* A* grossier par blocs, 8 voisins, heuristique octile admissible (cout >= longueur). */
function OpexV307Coarse(fromTile, toTile)
{
  local nx = (AIMap.GetMapSizeX() + V307_SIDE - 1) / V307_SIDE;
  local ny = (AIMap.GetMapSizeY() + V307_SIDE - 1) / V307_SIDE;
  local sx = AIMap.GetTileX(fromTile) / V307_SIDE, sy = AIMap.GetTileY(fromTile) / V307_SIDE;
  local gx = AIMap.GetTileX(toTile) / V307_SIDE, gy = AIMap.GetTileY(toTile) / V307_SIDE;
  local memo = {};
  local g = {};
  local prev = {};
  local closed = {};
  local open = AIList();
  open.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
  local start = sy * 10000 + sx, goal = gy * 10000 + gx;
  g[start] <- 0;
  prev[start] <- -1;
  open.AddItem(start, 0);
  local expanded = 0;
  local dirs = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];
  while (!open.IsEmpty()) {
    local cur = open.Begin();
    open.RemoveItem(cur);
    if (cur in closed) continue;
    closed[cur] <- true;
    expanded++;
    if (cur == goal) break;
    local cx = cur % 10000, cy = cur / 10000;
    local cb = OpexV307Block(memo, cx, cy);
    foreach (d in dirs) {
      local x = cx + d[0], y = cy + d[1];
      if (x < 1 || y < 1 || x >= nx - 1 || y >= ny - 1) continue;
      local id = y * 10000 + x;
      if (id in closed) continue;
      local step = OpexV307StepCost(cb, OpexV307Block(memo, x, y), d[0] != 0 && d[1] != 0);
      if (step < 0) continue;
      local ng = g[cur] + step;
      if ((id in g) && g[id] <= ng) continue;
      g[id] <- ng;
      prev[id] <- cur;
      local ddx = abs(gx - x), ddy = abs(gy - y);
      local h = V307_SIDE * (10 * max(ddx, ddy) + 4 * min(ddx, ddy));
      open.AddItem(id, ng + h);
    }
  }
  if (!(goal in closed)) return { ok = false, blocks = [], cost = -1, expanded = expanded, sampled = memo.len() };
  local blocks = [];
  local water = 0, obst = 0;
  for (local b = goal; b >= 0; b = prev[b]) {
    blocks.push(b);
    local s = memo[b];
    if (s.water > 0) water++;
    if (s.obst > 0) obst++;
  }
  blocks.reverse();
  return { ok = true, blocks = blocks, cost = g[goal], expanded = expanded, sampled = memo.len(),
           waterBlocks = water, obstBlocks = obst };
}

/* Couloir : toutes les tuiles des blocs du trace grossier dilates de V307_CORRIDOR blocs. */
function OpexV307Guide(blocks)
{
  local guide = {};
  local seen = {};
  local mx = AIMap.GetMapSizeX(), my = AIMap.GetMapSizeY();
  foreach (b in blocks) {
    local bx = b % 10000, by = b / 10000;
    for (local dx = -V307_CORRIDOR; dx <= V307_CORRIDOR; dx++) {
      for (local dy = -V307_CORRIDOR; dy <= V307_CORRIDOR; dy++) {
        local id = (by + dy) * 10000 + bx + dx;
        if (id in seen) continue;
        seen[id] <- true;
        local x0 = (bx + dx) * V307_SIDE, y0 = (by + dy) * V307_SIDE;
        for (local x = x0; x < x0 + V307_SIDE; x++) {
          if (x <= 0 || x >= mx - 1) continue;
          for (local y = y0; y < y0 + V307_SIDE; y++) {
            if (y <= 0 || y >= my - 1) continue;
            guide.rawset(y * mx + x, 0);
          }
        }
      }
    }
  }
  return guide;
}

/* Cout du trace complet par la fonction de cout commune, sans guide. */
function OpexV307PathCost(tiles)
{
  local pf = OpexNewRailPathfinderV129();
  pf.cost.max_cost = PATHFINDER_MAX_COST;
  OpexV294ApplyRailCosts(pf, null);
  local node = null;
  foreach (tile in tiles) {
    local cost = node == null ? 0 : pf._Cost(node, tile, 0, pf);
    node = OpexAyStarV129.Path(node, tile, 0xFF, cost, 0);
  }
  return node == null ? -1 : node.GetCost();
}

function OpexV307Search(plansA, plansB, dist, guide)
{
  local mark = OpexOpsMeasureBegin();
  local tick0 = AIController.GetTick();
  local date0 = AIDate.GetCurrentDate();
  local state = OpexCreateSegmentedSearch(plansA, plansB, V307_ITERS, null, OpexRailAstarWeight(dist), null, guide, null);
  if (state == null) return { stop = "NOPA", iters = 0, ops = 0, ticks = 0, days = 0, segments = 0, backtracks = 0, tiles = null };
  local res = null;
  local deadline = tick0 + 100000000;
  do {
    res = OpexAdvanceSegmentedSearch(state, V307_ITERS, deadline);
  } while (res.stop == "CONT");
  return { stop = res.stop, iters = res.iterations, ops = OpexOpsMeasureEnd(mark),
           ticks = AIController.GetTick() - tick0, days = AIDate.GetCurrentDate() - date0,
           segments = res.segments, backtracks = res.backtracks,
           tiles = res.stop == "OK" ? res.tiles : null,
           structures = (res.stop == "OK" && res.structures != null) ? res.structures.len() : 0 };
}

function OpexV307Log(arm, pair, r)
{
  local len = -1, cost = -1, jumps = 0;
  if (r.tiles != null) {
    len = 0;
    for (local i = 1; i < r.tiles.len(); i++) {
      local step = AIMap.DistanceManhattan(r.tiles[i - 1], r.tiles[i]);
      len += step;
      if (step > 1) jumps++;
    }
    cost = OpexV307PathCost(r.tiles);
  }
  OpexDecide("V307_ARM", "arm=" + arm + " a=" + pair.a + " b=" + pair.b + " dist=" + pair.dist
      + " bin=" + pair.bin + " outcome=" + r.stop + " iters=" + r.iters + " ops=" + r.ops
      + " ticks=" + r.ticks + " days=" + r.days + " segments=" + r.segments
      + " backtracks=" + r.backtracks + " len=" + len + " jumps=" + jumps + " cost=" + cost
      + " cap_ok=" + ((r.stop == "OK" && r.iters <= HARD_ITERATION_CAP) ? 1 : 0));
}

function OpexV307RailType()
{
  local types = AIRailTypeList();
  types.Valuate(AIRail.IsRailTypeAvailable);
  types.KeepValue(1);
  local chosen = -1;
  for (local t = types.Begin(); !types.IsEnd(); t = types.Next()) if (t > chosen) chosen = t;
  if (chosen >= 0) AIRail.SetCurrentRailType(chosen);
  return chosen;
}

function OpexV307LongProbe(perBin)
{
  local railType = OpexV307RailType();
  local pax = OpexAirDemandPaxCargo();
  local cov = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  local pairs = OpexV307Pairs(perBin);
  OpexDecide("V307_START", "pairs=" + pairs.len() + " per_bin=" + perBin + " rail=" + railType
      + " side=" + V307_SIDE + " corridor=" + V307_CORRIDOR + " iters=" + V307_ITERS
      + " cap=" + HARD_ITERATION_CAP + " map=" + AIMap.GetMapSizeX() + "x" + AIMap.GetMapSizeY());
  foreach (pair in pairs) {
    local ta = AITown.GetLocation(pair.a), tb = AITown.GetLocation(pair.b);
    local plansA = OpexStationPlans(ta, tb, STATION_SEARCH_RADIUS, V307_PLATFORM, MAX_STATION_PLANS, pax, cov, true);
    local plansB = OpexStationPlans(tb, ta, STATION_SEARCH_RADIUS, V307_PLATFORM, MAX_STATION_PLANS, pax, cov, true);
    if (plansA.len() == 0 || plansB.len() == 0) {
      OpexDecide("V307_ARM", "arm=plans a=" + pair.a + " b=" + pair.b + " dist=" + pair.dist
          + " bin=" + pair.bin + " outcome=NOPLAN na=" + plansA.len() + " nb=" + plansB.len());
      continue;
    }
    OpexV307Log("base", pair, OpexV307Search(plansA, plansB, pair.dist, null));

    local mark = OpexOpsMeasureBegin();
    local coarse = OpexV307Coarse(plansA[0].lead, plansB[0].lead);
    local coarseOps = OpexOpsMeasureEnd(mark);
    OpexDecide("V307_ARM", "arm=coarse a=" + pair.a + " b=" + pair.b + " dist=" + pair.dist
        + " bin=" + pair.bin + " outcome=" + (coarse.ok ? "OK" : "NOPA") + " ops=" + coarseOps
        + " expanded=" + coarse.expanded + " sampled=" + coarse.sampled
        + " blocks=" + coarse.blocks.len() + " cost=" + coarse.cost
        + " water_blocks=" + (coarse.ok ? coarse.waterBlocks : -1)
        + " obst_blocks=" + (coarse.ok ? coarse.obstBlocks : -1));
    if (!coarse.ok) continue;
    mark = OpexOpsMeasureBegin();
    local guide = OpexV307Guide(coarse.blocks);
    local guideOps = OpexOpsMeasureEnd(mark);
    local r = OpexV307Search(plansA, plansB, pair.dist, guide);
    r.ops += guideOps;
    OpexV307Log("guided", pair, r);
  }
  OpexDecide("V307_END", "pairs=" + pairs.len());
}
