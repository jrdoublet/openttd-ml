/* Etape 1 : portefeuille de projets multimodaux.
 *
 * Le catalogue ne decide rien. Pour chaque couple origine/destination, cette etape compare tous
 * les modes faisables sur un ROI homogene (profit annuel / capital) et ne garde que le meilleur.
 * Le portefeuille passe ensuite par deux contraintes, dans cet ordre :
 *   1. capital : maximiser le revenu annuel par livre immobilisee et remplir le budget disponible ;
 *   2. calcul : ordonner les projets finances par revenu annuel / opcodes attendus.
 *
 * Les projets sont indivisibles : la passe de capital est une approximation gloutonne bornee.
 * Apres chaque construction reussie, main.nut regenere le portefeuille, car le cash et les
 * origines disponibles ont change. Il n'existe donc plus de priorite rail/route/air/eau pour
 * l'ouverture de nouvelles lignes dans l'ordonnanceur.
 */

const PROJECT_POOL_K = 128;
const PROJECT_TOP_K = 64;

/* Mesures communes. Le pathfinder rail consomme environ 2 700 opcodes par iteration. Pour les
 * autres modes, la partie plan est mesuree pendant la generation ; les constantes ci-dessous
 * couvrent les commandes transactionnelles qui restent apres le plan. */
const PROJECT_RAIL_OPS_PER_ITERATION = 2700;
const PROJECT_RAIL_TRANSACTION_OPS = 200000;
const PROJECT_ROAD_TRANSACTION_OPS = 287000;
const PROJECT_AIR_TRANSACTION_OPS = 100000;
const PROJECT_WATER_TRANSACTION_OPS = 100000;

function OpexProjectPairKey(kind, cargo, src, dst)
{
  if (kind == "pax" && src > dst) {
    local swap = src;
    src = dst;
    dst = swap;
  }
  return kind + "|" + cargo + "|" + src + "|" + dst;
}

function OpexProjectScore(value, cost)
{
  if (value <= 0 || cost <= 0) return 0;
  local thousands = cost / 1000;
  if (thousands < 1) thousands = 1;
  return value / thousands;
}

function OpexProjectFromCandidate(candidate)
{
  if (candidate == null || candidate.profitAnnual <= 0 || candidate.revenueAnnual <= 0 ||
      candidate.capital <= 0) return null;
  local mode = candidate.mode;
  local margin = 0;
  local expectedOps = 0;
  if (mode == "rail") {
    expectedOps = candidate.iterations * PROJECT_RAIL_OPS_PER_ITERATION
                + PROJECT_RAIL_TRANSACTION_OPS;
  } else if (mode == "road") {
    margin = ROAD_CAPITAL_MARGIN;
    expectedOps = candidate.iterations * PROJECT_RAIL_OPS_PER_ITERATION
                + PROJECT_ROAD_TRANSACTION_OPS;
  } else {
    return null;
  }
  local budgetCapital = candidate.capital + margin;
  return {
    mode = mode, kind = candidate.kind, cargo = candidate.cargo,
    src = candidate.src, dst = candidate.dst, payload = candidate,
    distance = candidate.distance, capital = candidate.capital,
    budgetCapital = budgetCapital, profitAnnual = candidate.profitAnnual,
    revenueAnnual = candidate.revenueAnnual, roi = candidate.roi,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(candidate.revenueAnnual, budgetCapital),
    opcodeScore = OpexProjectScore(candidate.revenueAnnual, expectedOps),
    planningOpcodes = 0,
  };
}

function OpexProjectFromAir(catalog, plan, planningOps)
{
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  if (economics.profitAnnual <= 0 || economics.revenueAnnual <= 0 ||
      economics.capital <= 0) return null;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local margin = (newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000);
  local budgetCapital = economics.capital + margin;
  /* La decouverte a deja ete payee pendant l'etape projets. La contrainte d'execution ne porte
   * que sur les opcodes encore necessaires pour construire le projet. */
  local expectedOps = PROJECT_AIR_TRANSACTION_OPS;
  return {
    mode = "air", kind = "pax", cargo = catalog.paxCargo,
    src = plan.siteA.town.tile, dst = plan.siteB.town.tile, payload = plan,
    distance = plan.distance, capital = economics.capital,
    budgetCapital = budgetCapital, profitAnnual = economics.profitAnnual,
    revenueAnnual = economics.revenueAnnual, roi = economics.roi,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(economics.revenueAnnual, budgetCapital),
    opcodeScore = OpexProjectScore(economics.revenueAnnual, expectedOps),
    planningOpcodes = planningOps,
  };
}

function OpexProjectFromWater(catalog, plan, planningOps)
{
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  if (economics.profitAnnual <= 0 || economics.revenueAnnual <= 0 ||
      economics.capital <= 0) return null;
  local budgetCapital = economics.capital + WATER_CAPITAL_MARGIN;
  local expectedOps = PROJECT_WATER_TRANSACTION_OPS;
  return {
    mode = "water", kind = "pax", cargo = catalog.paxCargo,
    src = plan.siteA.town.tile, dst = plan.siteB.town.tile, payload = plan,
    distance = plan.distance, capital = economics.capital,
    budgetCapital = budgetCapital, profitAnnual = economics.profitAnnual,
    revenueAnnual = economics.revenueAnnual, roi = economics.roi,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(economics.revenueAnnual, budgetCapital),
    opcodeScore = OpexProjectScore(economics.revenueAnnual, expectedOps),
    planningOpcodes = planningOps,
  };
}

/* Comparaison strictement modale : ROI, puis profit, revenu et enfin calcul. La contrainte
 * d'opcodes ne peut donc jamais choisir le mode avant le ROI du couple. */
function OpexProjectModeBetter(candidate, incumbent)
{
  if (incumbent == null) return true;
  if (candidate.roi != incumbent.roi) return candidate.roi > incumbent.roi;
  if (candidate.profitAnnual != incumbent.profitAnnual) {
    return candidate.profitAnnual > incumbent.profitAnnual;
  }
  if (candidate.revenueAnnual != incumbent.revenueAnnual) {
    return candidate.revenueAnnual > incumbent.revenueAnnual;
  }
  return candidate.expectedOpcodes < incumbent.expectedOpcodes;
}

function OpexProjectRemember(winners, project, stats)
{
  if (project == null) return;
  stats.modeCandidates++;
  local key = OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
  if (!(key in winners)) {
    winners.rawset(key, project);
    return;
  }
  stats.modeAlternatives++;
  if (OpexProjectModeBetter(project, winners[key])) {
    winners[key] = project;
    stats.modeReplaced++;
  }
}

/* Insertion bornee et stable. field vaut budgetScore pendant la premiere contrainte, opcodeScore
 * pendant la seconde. Les egalites gardent le revenu absolu le plus eleve. */
function OpexProjectInsert(best, project, field, limit)
{
  local pos = best.len();
  while (pos > 0) {
    local prior = best[pos - 1];
    if (prior[field] > project[field]) break;
    if (prior[field] == project[field] && prior.revenueAnnual >= project.revenueAnnual) break;
    pos--;
  }
  best.insert(pos, project);
  if (best.len() > limit) best.pop();
}

/* Solveur Knapsack 0/1 borne (Branch & Bound avec borne superieure fractionnaire gloutonne)
 * sur les candidats classes par budgetScore. Le plafond de noeuds protege les opcodes ; le
 * resultat expose donc explicitement si l'optimalite a pu etre prouvee. */
function OpexKnapsackComputeBound(candidates, n, startIdx, cap)
{
  local bound = 0;
  local rem = cap;
  for (local j = startIdx; j < n; j++) {
    local p = candidates[j];
    if (p.budgetCapital <= rem) {
      rem -= p.budgetCapital;
      bound += p.revenueAnnual;
    } else {
      if (rem > 0 && p.budgetCapital > 0) {
        bound += ((p.revenueAnnual.tofloat() * rem) / p.budgetCapital).tointeger();
      }
      break;
    }
  }
  return bound;
}

function OpexKnapsackSearch(state, idx, currentCapital, currentRevenue, currentRoad, currentItems)
{
  if (state.nodeCount >= state.maxNodes) {
    state.truncated = true;
    return;
  }
  state.nodeCount++;
  if (currentRevenue > state.bestValue) {
    state.bestValue = currentRevenue;
    state.bestSolution = [];
    foreach (item in currentItems) state.bestSolution.append(item);
  }
  if (idx >= state.n || currentItems.len() >= state.maxItems) return;

  local remCap = state.capitalBudget - currentCapital;
  local bound = currentRevenue + OpexKnapsackComputeBound(state.candidates, state.n, idx, remCap);
  if (bound <= state.bestValue) return;

  local p = state.candidates[idx];

  // Branche 1 : Inclure le projet si finançable et respecte la limite route
  local canInclude = (currentCapital + p.budgetCapital <= state.capitalBudget);
  if (canInclude && p.mode == "road" && currentRoad >= state.maxRoad) canInclude = false;
  if (canInclude && ((p.src in state.originsUsed) || (p.dst in state.originsUsed))) canInclude = false;

  if (canInclude) {
    currentItems.append(p);
    state.originsUsed[p.src] <- true;
    state.originsUsed[p.dst] <- true;
    OpexKnapsackSearch(state, idx + 1, currentCapital + p.budgetCapital, currentRevenue + p.revenueAnnual,
                       p.mode == "road" ? currentRoad + 1 : currentRoad, currentItems);
    delete state.originsUsed[p.src];
    delete state.originsUsed[p.dst];
    currentItems.pop();
  }

  // Branche 2 : Exclure le projet
  OpexKnapsackSearch(state, idx + 1, currentCapital, currentRevenue, currentRoad, currentItems);
}

/* Résout le problème du sac à dos 0/1 borné par Branch & Bound.
 * Maximise la somme des revenueAnnual sous contrainte de capitalBudget, maxRoad et maxItems. */
function OpexKnapsackSolve(candidates, capitalBudget, maxRoad = 18, maxItems = 32)
{
  if (candidates.len() == 0 || capitalBudget <= 0) {
    return { projects = [], nodes = 0, exact = true };
  }

  // Trier les candidats par score composite décroissant (rendement économique et efficacité d'opcodes)
  candidates.sort(function(a, b) {
    local va = (a.budgetScore * 75 + a.opcodeScore * 25).tofloat();
    local vb = (b.budgetScore * 75 + b.opcodeScore * 25).tofloat();
    if (va > vb) return -1;
    if (va < vb) return 1;
    return 0;
  });

  local n = candidates.len();
  if (n > 64) n = 64; // Limiter aux 64 meilleurs candidats

  local state = {
    candidates = candidates,
    n = n,
    capitalBudget = capitalBudget,
    maxRoad = maxRoad,
    maxItems = maxItems,
    nodeCount = 0,
    maxNodes = 2000,
    bestValue = 0,
    truncated = false,
    originsUsed = {},
    bestSolution = [],
  };

  OpexKnapsackSearch(state, 0, 0, 0, 0, []);
  return { projects = state.bestSolution, nodes = state.nodeCount, exact = !state.truncated };
}

function OpexProjectEmptyRoad()
{
  return {
    all = 0, candidates = [], best = [],
    stats = { pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
              economicsUnavailable = 0, profitTooLow = 0, accepted = 0 },
    opcodes = 0,
  };
}

function OpexBuildProjects(catalog, budget, lines)
{
  local rail = OpexBuildCandidates(catalog, budget, lines);
  local road = ROAD_BUILD_ENABLED
      ? OpexBuildRoadCandidates(catalog, budget, lines) : OpexProjectEmptyRoad();

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local borrowable = REBORROW
      ? AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount() : 0;
  if (borrowable < 0) borrowable = 0;
  local capitalBudget = cash + borrowable - OpexCashReserve();
  if (capitalBudget < 0) capitalBudget = 0;

  local airPlan = null;
  local airPlans = [];
  local airOps = 0;
  if ((catalog.airCombos != null && catalog.airCombos.len() > 0) || catalog.airport != null) {
    budget.begin();
    airPlan = OpexAirPlans(catalog, lines, 0, airPlans);
    airOps = budget.end("project_air");
  }

  local waterPlan = null;
  local waterPlans = [];
  local waterOps = 0;
  if (catalog.ships.len() > 0 && catalog.paxCargo >= 0) {
    budget.begin();
    waterPlan = OpexWaterPlans(catalog, lines, waterPlans);
    waterOps = budget.end("project_water");
  }

  local stats = {
    modeCandidates = 0, modeAlternatives = 0, modeReplaced = 0,
    odProjects = 0, budgetConsidered = 0, budgetSelected = 0,
    budgetRejected = 0, selectedRevenue = 0, selectedCapital = 0,
    knapsackNodes = 0, knapsackExact = true,
  };
  local winners = {};
  foreach (candidate in rail.candidates) {
    OpexProjectRemember(winners, OpexProjectFromCandidate(candidate), stats);
  }
  foreach (candidate in road.candidates) {
    OpexProjectRemember(winners, OpexProjectFromCandidate(candidate), stats);
  }
  foreach (plan in airPlans) {
    OpexProjectRemember(winners, OpexProjectFromAir(catalog, plan, airOps), stats);
  }
  foreach (plan in waterPlans) {
    OpexProjectRemember(winners, OpexProjectFromWater(catalog, plan, waterOps), stats);
  }

  local byBudget = [];
  foreach (key, project in winners) {
    stats.odProjects++;
    OpexProjectInsert(byBudget, project, "budgetScore", PROJECT_POOL_K);
  }

  local knapsack = OpexKnapsackSolve(byBudget, capitalBudget, ROAD_MAX_NEW_LINES_PER_YEAR, PROJECT_TOP_K);
  local funded = knapsack.projects;
  stats.knapsackNodes = knapsack.nodes;
  stats.knapsackExact = knapsack.exact;
  stats.budgetConsidered = byBudget.len();
  stats.budgetSelected = funded.len();
  stats.budgetRejected = byBudget.len() - funded.len();

  local selectedRev = 0;
  local selectedCap = 0;
  foreach (p in funded) {
    selectedRev += p.revenueAnnual;
    selectedCap += p.budgetCapital;
  }
  stats.selectedRevenue = selectedRev;
  stats.selectedCapital = selectedCap;
  local remaining = capitalBudget - selectedCap;
  if (remaining < 0) remaining = 0;

  local byOpcodes = [];
  foreach (project in funded) {
    OpexProjectInsert(byOpcodes, project, "opcodeScore", PROJECT_TOP_K);
  }

  return {
    all = stats.odProjects, best = byOpcodes, stats = stats,
    capitalBudget = capitalBudget, capitalRemaining = remaining,
    rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
    airPlans = airPlans, waterPlans = waterPlans,
    airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
  };
}
