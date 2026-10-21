/* V307 : banc de mesure des longs traces rail (21/10). Mesure seule, defaut 0.
 *
 * Sous v307_long_probe = N > 0, au 1er janvier de l'annee de depart + v307_probe_year, partie
 * neuve seulement, on tire N paires de villes et N paires fret (industrie productrice vers
 * acceptante) par tranche de distance Manhattan (120-179, 180-249, 250-349) et, pour chacune,
 * sur la meme carte figee (rien n'est construit pendant la sonde) :
 *   base    : la recherche segmentee de production, budget V307_ITERS au lieu du plafond de 5 000 ;
 *             reussir en <= HARD_ITERATION_CAP iterations = reussir au plafond actuel ;
 *   coarse  : un A* grossier sur des blocs de V307_SIDE tuiles echantillonnes (hauteur, eau,
 *             obstacles), qui predit faisabilite et longueur ;
 *   guided  : la meme recherche de production, guidee (guideTiles, cout x0,5 dedans, x2 dehors)
 *             par le couloir grossier dilate de V307_CORRIDOR blocs.
 * Chaque bras journalise iterations, opcodes, ticks, segments, longueur et cout du trace repricé
 * par la fonction de cout commune sans guide (comparable entre bras).
 * La sonde est bloquante : en partie de mesure seulement. A annee > 0, la carte porte le reseau
 * construit jusque-la (le notre, celui d'AAAHogEx en duel, la croissance des villes). */

const V307_SIDE = 8;
const V307_CORRIDOR = 1;
const V307_ITERS = 20000;
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
    pairs.push({ kind = "pax", a = a, b = b, ta = AITown.GetLocation(a), tb = AITown.GetLocation(b),
                 cargo = OpexAirDemandPaxCargo(), dist = d, bin = bin });
  }
  return pairs;
}

/* Paires fret deterministes : pour chaque cargo hors passagers/courrier, les 15 industries qui
 * produisent le plus le mois dernier vers toute industrie acceptante ; triees par production,
 * au plus 2 paires par source, N par tranche. */
function OpexV307FreightPairs(perBin)
{
  local scored = AIList();
  local meta = {};
  local key = 0;
  local cargos = AICargoList();
  for (local c = cargos.Begin(); !cargos.IsEnd(); c = cargos.Next()) {
    if (AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS) || AICargo.HasCargoClass(c, AICargo.CC_MAIL)) continue;
    local prod = AIIndustryList_CargoProducing(c);
    prod.Valuate(AIIndustry.GetLastMonthProduction, c);
    prod.KeepAboveValue(0);
    prod.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
    prod.KeepTop(15);
    local acc = AIIndustryList_CargoAccepting(c);
    for (local i = prod.Begin(); !prod.IsEnd(); i = prod.Next()) {
      local ti = AIIndustry.GetLocation(i);
      for (local j = acc.Begin(); !acc.IsEnd(); j = acc.Next()) {
        if (i == j) continue;
        local tj = AIIndustry.GetLocation(j);
        local d = AIMap.DistanceManhattan(ti, tj);
        local bin = OpexV307Bin(d);
        if (bin < 0) continue;
        meta[key] <- { kind = "freight", a = i, b = j, ta = ti, tb = tj, cargo = c, dist = d, bin = bin };
        scored.AddItem(key, prod.GetValue(i));
        key++;
      }
    }
  }
  scored.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
  local used = {};
  local taken = [0, 0, 0];
  local pairs = [];
  for (local k = scored.Begin(); !scored.IsEnd(); k = scored.Next()) {
    local m = meta[k];
    if (taken[m.bin] >= perBin) continue;
    local ua = (m.a in used) ? used[m.a] : 0;
    if (ua >= 2) continue;
    used[m.a] <- ua + 1;
    taken[m.bin]++;
    pairs.push(m);
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

function OpexV307PairFields(pair)
{
  return "kind=" + pair.kind + " cargo=" + pair.cargo + " a=" + pair.a + " b=" + pair.b
      + " ta=" + pair.ta + " tb=" + pair.tb + " dist=" + pair.dist + " bin=" + pair.bin;
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
  OpexDecide("V307_ARM", "arm=" + arm + " " + OpexV307PairFields(pair) + " outcome=" + r.stop + " iters=" + r.iters + " ops=" + r.ops
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

/* Appele a chaque tour de boucle sous V307_LONG_PROBE > 0 : une seule fois, au 1er janvier de
 * l'annee de depart + V307_PROBE_YEAR, jamais apres un chargement. */
function OpexV307MaybeRun(loadedFromSave)
{
  if (V307_DONE || loadedFromSave) return;
  if (AIDate.GetYear(AIDate.GetCurrentDate()) < OPEX_START_YEAR + V307_PROBE_YEAR) return;
  V307_DONE = true;
  OpexV307LongProbe(V307_LONG_PROBE);
}

function OpexV307LongProbe(perBin)
{
  local railType = OpexV307RailType();
  local cov = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  local pairs = OpexV307Pairs(perBin);
  pairs.extend(OpexV307FreightPairs(perBin));
  OpexDecide("V307_START", "pairs=" + pairs.len() + " per_bin=" + perBin + " rail=" + railType
      + " side=" + V307_SIDE + " corridor=" + V307_CORRIDOR + " iters=" + V307_ITERS
      + " cap=" + HARD_ITERATION_CAP + " map=" + AIMap.GetMapSizeX() + "x" + AIMap.GetMapSizeY()
      + " year_offset=" + V307_PROBE_YEAR);
  foreach (pair in pairs) {
    local plansA = OpexStationPlans(pair.ta, pair.tb, STATION_SEARCH_RADIUS, V307_PLATFORM, MAX_STATION_PLANS, pair.cargo, cov, true);
    local plansB = OpexStationPlans(pair.tb, pair.ta, STATION_SEARCH_RADIUS, V307_PLATFORM, MAX_STATION_PLANS, pair.cargo, cov, pair.kind == "pax");
    if (plansA.len() == 0 || plansB.len() == 0) {
      OpexDecide("V307_ARM", "arm=plans " + OpexV307PairFields(pair) + " outcome=NOPLAN na=" + plansA.len() + " nb=" + plansB.len());
      continue;
    }
    OpexV307Log("base", pair, OpexV307Search(plansA, plansB, pair.dist, null));

    local mark = OpexOpsMeasureBegin();
    local coarse = OpexV307Coarse(plansA[0].lead, plansB[0].lead);
    local coarseOps = OpexOpsMeasureEnd(mark);
    OpexDecide("V307_ARM", "arm=coarse " + OpexV307PairFields(pair)
        + " outcome=" + (coarse.ok ? "OK" : "NOPA") + " ops=" + coarseOps
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

/* V307 autopsie : apres un ABND de production (recherche primaire), deux A* frais non segmentes,
 * bloquants, de V307_ITERS iterations, avec les memes quais, interdictions, poids et moteur :
 * aller (A -> B) et inverse (B -> A). null = file ouverte videe, but prouve inaccessible avec ces
 * contraintes ; false = budget epuise ; sinon trace trouve (le plafond de production manquait). */
function OpexV307AutopsyOne(plansFrom, plansTo, ignored, weight, outwardSide, engine)
{
  local mark = OpexOpsMeasureBegin();
  local date0 = AIDate.GetCurrentDate();
  local pf = OpexCreateRailPathfinder(plansFrom, plansTo, ignored, weight, outwardSide, null, engine);
  if (pf == null) return "out=NOPLAN iters=0 ops=0 days=0 len=-1";
  local res = pf.FindPath(V307_ITERS);
  local out = res == null ? "NOPA" : (res == false ? "CAP" : "OK");
  local len = -1;
  if (out == "OK") len = OpexPathTiles(res).len();
  return "out=" + out + " iters=" + pf.LastConsumed() + " ops=" + OpexOpsMeasureEnd(mark)
      + " days=" + (AIDate.GetCurrentDate() - date0) + " len=" + len;
}

function OpexV307Autopsy(state)
{
  local plan = state.plan, cand = state.candidate;
  if (plan == null || cand == null || plan.plansA == null || plan.plansB == null) return;
  local seg = ("segmented" in state) ? state.segmented : null;
  local ignored = ("clearanceTiles" in state) ? state.clearanceTiles : null;
  local outward = (seg != null && ("outwardSide" in seg)) ? seg.outwardSide : null;
  local engine = (seg != null && ("engine" in seg)) ? seg.engine : null;
  local joinB = ("joinEnd" in cand) && cand.joinEnd == "B";
  local joined = ("joinStationId" in cand) && cand.joinStationId != null && cand.joinStationId >= 0;
  local head = "src=" + cand.src + " dst=" + cand.dst + " dist=" + (("distance" in cand) ? cand.distance : -1)
      + " kind=" + cand.kind + " join=" + (joined ? (joinB ? "B" : "A") : "none")
      + " shared=" + ((("shared_dest" in cand) && cand.shared_dest) ? 1 : 0)
      + " na=" + plan.plansA.len() + " nb=" + plan.plansB.len()
      + " ignored=" + (ignored == null ? 0 : ignored.len()) + " spent=" + state.spent;
  OpexDecide("V307_AUTOPSY", head + " dir=fwd " + OpexV307AutopsyOne(plan.plansA, plan.plansB, ignored, state.weight, outward, engine));
  OpexDecide("V307_AUTOPSY", head + " dir=rev " + OpexV307AutopsyOne(plan.plansB, plan.plansA, ignored, state.weight, null, engine));
}
