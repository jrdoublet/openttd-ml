/* V278 experimental, OFF au defaut. Les courses C83 et les appels synchrones
 * conservent le pipeline historique. Aucun etat n'est ajoute a Save(). */
function OpexV278LazyEnabled(ctx)
{
  return ctx.sliced && ctx.targetTownId < 0 && !("c83Repair" in ctx.resumeState);
}

/* Copie superficielle explicite : pas de closure capturant des locales. */
function OpexV278CopyContext(ctx)
{
  local out = {};
  foreach (key, value in ctx) out.rawset(key, value);
  return out;
}

/* Les lignes peuvent changer ENTRE tranches (publication progressive puis
 * chantier). Comparer leurs champs exacts, pas seulement un nombre de routes.
 * La validite des StationID est couverte par le tick : l'index seul est refait
 * a un nouveau tick, le reste de Prepare reste un snapshot de scan. */
function OpexV278LinesSignature(lines)
{
  local signature = "";
  if (lines == null) return "null";
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    signature += "|" + line.stationA + ":" + line.stationB;
  }
  return signature;
}

function OpexV278RestorePrepare(ctx)
{
  local state = ctx.resumeState;
  if (!("v278Prepare" in state)) return false;
  local memo = state.v278Prepare;
  if (memo.catalog != ctx.catalog) return false;
  foreach (key, value in memo.fields) ctx.rawset(key, value);
  local signature = OpexV278LinesSignature(ctx.lines);
  if (memo.lines != signature || memo.epoch != V278_AIR_EPOCH
      || memo.tick != AIController.GetTick()) {
    local tick = AIController.GetTick();
    ctx.hubIndex = OpexV278HubIndex(ctx.lines);
    memo.fields.hubIndex = ctx.hubIndex;
    memo.lines = signature;
    memo.epoch = V278_AIR_EPOCH;
    memo.tick = AIController.GetTick() == tick ? tick : -1;
  }
  ctx.infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  ctx.bestPlan = state.bestPlan;
  ctx.comboStart = state.combo;
  ctx.perfOpsSites = state.perfOpsSites;
  ctx.perfOpsEval = state.perfOpsEval;
  ctx.perfProbesCount = state.perfProbesCount;
  ctx.perfCheapSkip = state.perfCheapSkip;
  ctx.perfSitesFound = state.perfSitesFound;
  C121_AIR_PLAN_PERF = state.c121PlanPerf;
  C121_AIR_ENDPOINT_CACHE = state.c121EndpointCache;
  return true;
}

function OpexV278HubIndex(lines)
{
  if (lines == null) return null;
  local index = { routes = {}, pairs = {} };
  foreach (other in lines) {
    if (!("mode" in other) || other.mode != "air") continue;
    local oA = OpexAirLineStationId(other, 0);
    local oB = OpexAirLineStationId(other, 1);
    index.routes.rawset(oA, ((oA in index.routes) ? index.routes[oA] : 0) + 1);
    if (oB != oA) index.routes.rawset(oB, ((oB in index.routes) ? index.routes[oB] : 0) + 1);
    if (AIStation.IsValidStation(oA) && AIStation.IsValidStation(oB)) {
      index.pairs.rawset(oA + "|" + oB, true);
      index.pairs.rawset(oB + "|" + oA, true);
    }
  }
  return index;
}

function OpexV278StorePrepare(ctx)
{
  local fields = {};
  foreach (key in ["combos", "servedDiag", "hubIndex", "c83TopTownIds", "towns", "limit",
      "c78Year", "c78Gen", "stationLimitedTowns", "infrastructureMaintenance"])
    fields.rawset(key, ctx[key]);
  ctx.resumeState.v278Prepare <- { catalog = ctx.catalog, fields = fields,
      lines = OpexV278LinesSignature(ctx.lines), epoch = V278_AIR_EPOCH,
      tick = -1 };
}

/* Fusion de lignes de la matrice triangulaire, chaque ligne b>a etant triee
 * par popB. Maximum global popA*popB, puis indices croissants. Conversion
 * float AVANT multiplication (pas de debordement entier sur les grandes villes).
 * O(n) memoire, O(log n) par paire, aucun tableau O(n^2). */
function OpexV278PairBefore(a, b)
{
  if (a.potential != b.potential) return a.potential > b.potential;
  return a.a != b.a ? a.a < b.a : a.b < b.b;
}

function OpexV278HeapPush(heap, item)
{
  heap.append(item);
  local at = heap.len() - 1;
  while (at > 0) {
    local up = (at - 1) / 2;
    if (!OpexV278PairBefore(item, heap[up])) break;
    heap[at] = heap[up];
    at = up;
  }
  heap[at] = item;
}

function OpexV278HeapPop(heap)
{
  local first = heap[0];
  local last = heap.pop();
  if (heap.len() == 0) return first;
  local at = 0;
  while (at * 2 + 1 < heap.len()) {
    local down = at * 2 + 1;
    if (down + 1 < heap.len() && OpexV278PairBefore(heap[down + 1], heap[down])) down++;
    if (!OpexV278PairBefore(heap[down], last)) break;
    heap[at] = heap[down];
    at = down;
  }
  heap[at] = last;
  return first;
}

function OpexV278Pair(towns, a, b)
{
  return { a = a, b = b, potential = towns[a].pop.tofloat() * towns[b].pop };
}

function OpexV278LazyState(ctx, comboIndex)
{
  local state = ctx.resumeState;
  if ("v278Lazy" in state) return state.v278Lazy;
  /* Meme ensemble de villes que master, puis population decroissante.
   * Figer aussi les valeurs : le catalogue peut muter entre deux tranches. */
  local pool = [];
  for (local i = 0; i < ctx.limit; i++) {
    local town = {};
    foreach (key, value in ctx.towns[i]) town.rawset(key, value);
    pool.append(town);
  }
  local towns = OpexAirSortedTowns(pool);
  local heap = [];
  for (local a = 0; a + 1 < towns.len(); a++)
    OpexV278HeapPush(heap, OpexV278Pair(towns, a, a + 1));
  local lazy = { towns = towns, heap = heap, sites = [], byTown = {},
      covered = 0, end = towns.len() < 8 ? towns.len() : 8,
      scan = null, probes = { left = AIR_MAX_SITE_PROBES, townsLeft = ctx.limit,
          tested = 0, cheapSkip = 0, stationLimitedTowns = ctx.stationLimitedTowns },
      pairsDone = false };
  state.v278Lazy <- lazy;
  return lazy;
}

/* Checkpoint de recherche independant : FindSites garde ses contrats de yield,
 * scanIndex/rankIndex, sondes, filtres et budget GLOBAL de sondage par combo. */
function OpexV278ExtendSites(ctx, comboIndex, combo, airport, plane, lazy)
{
  if (lazy.covered >= lazy.end) return true;
  if (lazy.scan == null) {
    /* Meme schema de reprise que Prepare, avec le resultat cumule courant
     * (null/0 au premier lot). FindSites suspend aussi pendant le classement. */
    lazy.scan = { combo = comboIndex, scanIndex = lazy.covered, scanSites = [],
        scanProbes = lazy.probes, rankIndex = 0, rankSites = [], sites = null,
        bestPlan = ctx.bestPlan, stationLimitedTowns = ctx.stationLimitedTowns,
        perfOpsSites = ctx.perfOpsSites, perfOpsEval = ctx.perfOpsEval,
        perfProbesCount = ctx.perfProbesCount, perfCheapSkip = ctx.perfCheapSkip,
        perfSitesFound = ctx.perfSitesFound,
        a = 0, b = 1, totalOps = 0 };
  }
  local work = OpexV278CopyContext(ctx);
  work.towns = lazy.towns;
  work.v278ScanEnd <- lazy.end;
  work.resumeState = lazy.scan;
  /* Le premier lot est deja sous StepFindSites ; les extensions sont sous
   * StepNewPairs et ont besoin de leur propre span sites (pas de double compte). */
  local mark = PROBE_SPAN_TRACE && ("v278ExtendingPairs" in ctx)
      ? OpexSpanBegin("air.sites") : null;
  local ok = OpexAirPlansFindSites(work, comboIndex, combo, airport, plane, false);
  if (mark != null) OpexSpanEnd(mark);
  if ("v133Skip" in work) ctx.v133Skip <- work.v133Skip;
  ctx.bestPlan = work.bestPlan;
  ctx.stationLimitedTowns = work.stationLimitedTowns;
  ctx.perfOpsSites = work.perfOpsSites;
  ctx.perfOpsEval = work.perfOpsEval;
  ctx.perfProbesCount = work.perfProbesCount;
  ctx.perfCheapSkip = work.perfCheapSkip;
  ctx.perfSitesFound = work.perfSitesFound;
  if (!ok) return false;
  foreach (site in work.sites) {
    lazy.sites.append(site);
    lazy.byTown.rawset(site.town.id, site);
  }
  lazy.covered = lazy.end;
  lazy.scan = null;
  return true;
}

function OpexV278Checkpoint(ctx)
{
  local state = ctx.resumeState;
  state.bestPlan = ctx.bestPlan;
  state.perfOpsSites = ctx.perfOpsSites;
  state.perfOpsEval = ctx.perfOpsEval;
  state.perfProbesCount = ctx.perfProbesCount;
  state.perfCheapSkip = ctx.perfCheapSkip;
  state.perfSitesFound = ctx.perfSitesFound;
  state.totalOps += OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all);
  return false;
}

function OpexV278BudgetSpent(ctx)
{
  return (ctx.opsBudget > 0 && OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all) >= ctx.opsBudget)
      || (ctx.deadlineTick > 0 && AIController.GetTick() >= ctx.deadlineTick);
}

function OpexV278LazySites(ctx, comboIndex, combo, airport, plane)
{
  local lazy = OpexV278LazyState(ctx, comboIndex);
  ctx.sites = lazy.sites;
  ctx.resumeState.combo = comboIndex;
  if (!OpexV278ExtendSites(ctx, comboIndex, combo, airport, plane, lazy))
    return OpexV278Checkpoint(ctx);
  ctx.resumeState.sites = lazy.sites;
  return true;
}

function OpexV278LazyPairs(ctx, comboIndex, combo, airport, plane, minDist)
{
  local lazy = ctx.resumeState.v278Lazy;
  if (lazy.pairsDone) return true;
  ctx.v278ExtendingPairs <- true;
  local progress = false;
  while (lazy.heap.len() > 0) {
    if (progress && OpexV278BudgetSpent(ctx)) return OpexV278Checkpoint(ctx);
    local pair = lazy.heap[0];
    /* Le sommet global commande l'extension AVANT toute paire inferieure.
     * On ne depile rien avant la fin de la recherche des deux extremites. */
    if (pair.b >= lazy.end) {
      lazy.end = ((pair.b / 8) + 1) * 8;
      if (lazy.end > lazy.towns.len()) lazy.end = lazy.towns.len();
    }
    if (!OpexV278ExtendSites(ctx, comboIndex, combo, airport, plane, lazy))
      return OpexV278Checkpoint(ctx);
    pair = OpexV278HeapPop(lazy.heap);
    if (pair.b + 1 < lazy.towns.len())
      OpexV278HeapPush(lazy.heap, OpexV278Pair(lazy.towns, pair.a, pair.b + 1));
    progress = true;
    local townA = lazy.towns[pair.a].id;
    local townB = lazy.towns[pair.b].id;
    if (!(townA in lazy.byTown) || !(townB in lazy.byTown)) continue;
    local siteA = lazy.byTown[townA];
    local siteB = lazy.byTown[townB];
    local tick = AIController.GetTick();
    local left = AIController.GetOpsTillSuspend();
    local valid = OpexV278SiteOk(siteA, airport, plane, ctx.stationLimitedTowns)
        && OpexV278SiteOk(siteB, airport, plane, ctx.stationLimitedTowns);
    ctx.perfOpsEval += OpexAirCalcDeltaOps(tick, left);
    if (!valid) continue;
    local work = OpexV278CopyContext(ctx);
    work.sliced = false;
    work.resumeState = null;
    work.sites = [siteA, siteB];
    work.v278SinglePair <- true;
    /* Une seule paire atomique, comme la garantie de progres historique.
     * Pas de copie de l'economie C121 ni de ses filtres d'admission. */
    OpexAirPlansNewPairs(work, comboIndex, combo, airport, plane, minDist, false);
    if ("v133Skip" in work) ctx.v133Skip <- work.v133Skip;
    ctx.bestPlan = work.bestPlan;
    ctx.perfOpsSites = work.perfOpsSites;
    ctx.perfOpsEval = work.perfOpsEval;
    ctx.perfProbesCount = work.perfProbesCount;
    ctx.perfCheapSkip = work.perfCheapSkip;
    ctx.perfSitesFound = work.perfSitesFound;
  }
  /* Meme un vivier sans paire doit fournir tous les sites aux bras hubs. */
  lazy.end = lazy.towns.len();
  if (!OpexV278ExtendSites(ctx, comboIndex, combo, airport, plane, lazy))
    return OpexV278Checkpoint(ctx);
  lazy.pairsDone = true;
  ctx.sites = lazy.sites;
  ctx.resumeState.sites = lazy.sites;
  if (OpexV278BudgetSpent(ctx)) return OpexV278Checkpoint(ctx);
  return true;
}
