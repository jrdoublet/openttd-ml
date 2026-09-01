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

const PROJECT_POOL_K = 64;
const PROJECT_TOP_K = 32;

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
  local margin = AIR_STARTER ? 10000 : AIR_CAPITAL_MARGIN;
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
  local key = project.mode + "|" + OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
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
    airPlan = OpexAirPlans(catalog, lines, capitalBudget, airPlans);
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

  local funded = [];
  local remaining = capitalBudget;
  local roadCount = 0;
  foreach (project in byBudget) {
    stats.budgetConsidered++;
    if (project.mode == "road") {
      if (roadCount >= ROAD_MAX_NEW_LINES_PER_YEAR) continue;
    }
    if (project.budgetCapital > remaining) {
      stats.budgetRejected++;
      continue;
    }
    funded.append(project);
    if (project.mode == "road") roadCount++;
    remaining -= project.budgetCapital;
    stats.selectedRevenue += project.revenueAnnual;
    stats.selectedCapital += project.budgetCapital;
    if (funded.len() >= PROJECT_TOP_K) break;
  }
  stats.budgetSelected = funded.len();

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
