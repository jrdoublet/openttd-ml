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
/* Calibré sur la médiane réelle mesurée (3 105 opcodes par itération d'A* rail, cf. docs/taches.md §3 octies & C3). */
const PROJECT_RAIL_OPS_PER_ITERATION = 3105;
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
    /* pricing_fix : ERREUR DE DIMENSION. `candidate.iterations` d'un candidat ROUTE vient
     * d'OpexRoadIterations(distance) -- ce n'est PAS un compte d'iterations d'A* rail, et le
     * multiplier par PROJECT_RAIL_OPS_PER_ITERATION (2 700 opcodes par iteration du pathfinder
     * RAIL) n'a aucun sens dimensionnel. Le commentaire d'en-tete de ce fichier dit d'ailleurs que
     * la partie plan est deja mesuree pendant la generation et que les constantes ne couvrent que
     * les commandes transactionnelles restantes : ce terme double-comptait donc une planification
     * deja payee, en la facturant au tarif d'un autre mode (docs/taches.md S0 septies).
     * Consequence : opcodeScore route sous-estime, donc la route defavorisee au second tri. */
    expectedOps = PRICING_ROAD_OPS
        ? PROJECT_ROAD_TRANSACTION_OPS
        : candidate.iterations * PROJECT_RAIL_OPS_PER_ITERATION + PROJECT_ROAD_TRANSACTION_OPS;
  } else {
    return null;
  }
  local budgetCapital = candidate.capital + margin;
  local scoreRevenue = candidate.revenueAnnual;
  if (candidate.kind == "freight" && ("freightBonus" in candidate) && candidate.freightBonus > 100) {
    scoreRevenue = (scoreRevenue * candidate.freightBonus) / 100;
  }
  return {
    mode = mode, kind = candidate.kind, cargo = candidate.cargo,
    src = candidate.src, dst = candidate.dst, payload = candidate,
    distance = candidate.distance, capital = candidate.capital,
    budgetCapital = budgetCapital, profitAnnual = candidate.profitAnnual,
    revenueAnnual = candidate.revenueAnnual, roi = candidate.roi,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(scoreRevenue, budgetCapital),
    opcodeScore = OpexProjectScore(scoreRevenue, expectedOps),
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

/* portfolio_v2 : garde TOUTES les alternatives modales d'un couple origine/destination au lieu
 * d'en elire une avant le test de capital. Motif (docs/taches.md S0 septies, soupcon 1 confirme) :
 * OpexProjectModeBetter classe sur `roi`, un RATIO -- une ligne rail a 900 k£ (roi 180) bat une
 * route a 45 k£ (roi 170) sur le meme couple, puis echoue au test de capital, et le couple ne
 * rapporte alors RIEN alors qu'une alternative finançable existait. */
function OpexProjectRememberAll(winners, project, stats)
{
  if (project == null) return;
  stats.modeCandidates++;
  local key = OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
  if (!(key in winners)) {
    winners.rawset(key, [project]);
    return;
  }
  stats.modeAlternatives++;
  winners[key].push(project);
}

/* portfolio_v2 : la selection finale.
 *
 * Remplace le sac a dos 0/1 par « le meilleur projet finançable ». Motif (S0 septies, trouvaille
 * B) : `maxBatch = 1` dans main.nut -- UN SEUL projet est construit, puis tout le portefeuille est
 * regenere. Tout le sac a dos etait donc jete sauf un item, et cet item avait ete admis par un
 * empaquetage dont l'objectif etait le REVENU total. A 300 k£ de budget, le solveur preferait
 * {3 x 100 k£ / rev 20k} = 60k a {1 x 280 k£ / rev 55k} = 55k : le meilleur projet etait
 * finançable et n'etait jamais construit.
 *
 * Trois defauts tombent d'un coup :
 *   - l'objectif passe du revenu au PROFIT (soupcons 2 et 3) ;
 *   - la contrainte « deux projets ne partagent aucune extremite » disparait (soupcon 4) : elle
 *     interdisait la topologie en etoile que builder_air produit, sans rien apporter puisqu'un
 *     seul projet est bati ;
 *   - le couple garde son alternative finançable (soupcon 1), l'election modale se faisant
 *     desormais APRES le test de capital.
 *
 * Le classement est le profit par livre de capital reellement mobilisable. */
function OpexProjectSelectAffordable(alternatives, capitalBudget, limit)
{
  /* 🔴 LE PLANCHER DE PROFIT ABSOLU, ET POURQUOI IL EXISTE (banc du 2026-09-02,
   * docs/bench_isolation_3y_20seeds.json). Le tri au seul RATIO profit/capital a ete mesure isole :
   * il fait bien ce qu'on lui demandait sur le volume -- 21,4 -> 27,2 gares, +27 %, le SEUL des
   * quatre reglages a le bouger -- mais il coute -24,4 % de valeur et -30,7 % de profit annuel.
   *
   * Mecanisme : un ratio favorise les tout petits projets bon marche, dont le profit absolu est
   * negligeable. Comme main.nut n'en batit qu'UN par cycle (maxBatch = 1), chaque cycle est alors
   * consomme par une ligne mediocre, et les gros projets rentables ne sont jamais atteints. C'est
   * exactement le risque « cheap-first » que l'analyse avait nomme d'avance.
   *
   * Le correctif garde le ratio -- c'est lui qui apporte le volume -- mais n'admet au classement
   * que les projets dont le profit annuel atteint une fraction du MEILLEUR profit finançable du
   * moment. Le plancher est relatif, donc il ne depend ni de l'epoque, ni de la taille de la carte,
   * ni de l'inflation : a 0 il reproduit exactement le comportement mesure ci-dessus. */
  local bestProfit = 0;
  foreach (project in alternatives) {
    if (project.budgetCapital > capitalBudget) continue;
    if (project.profitAnnual > bestProfit) bestProfit = project.profitAnnual;
  }
  local floorProfit = 0;
  if (PORTFOLIO_FLOOR_PCT > 0 && bestProfit > 0) {
    floorProfit = bestProfit * PORTFOLIO_FLOOR_PCT / 100;
  }

  local affordable = [];
  foreach (project in alternatives) {
    if (project.budgetCapital > capitalBudget) continue;
    if (project.profitAnnual < floorProfit) continue;
    project.fundScore <- OpexProjectScore(project.profitAnnual, project.budgetCapital);
    OpexProjectInsert(affordable, project, "fundScore", limit);
  }
  /* Filet de securite : si le plancher a tout ecarte -- il ne le peut pas puisque le meilleur
   * projet l'atteint par construction, mais un profitAnnual nul ou negatif rendrait bestProfit nul
   * et le plancher inoperant -- on retombe sur l'ensemble finançable brut plutot que de ne rien
   * batir du tout. */
  if (affordable.len() == 0 && floorProfit > 0) {
    foreach (project in alternatives) {
      if (project.budgetCapital > capitalBudget) continue;
      project.fundScore <- OpexProjectScore(project.profitAnnual, project.budgetCapital);
      OpexProjectInsert(affordable, project, "fundScore", limit);
    }
  }
  return affordable;
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

/* Rejoue UNIQUEMENT la contrainte de capital sur les projets deja produits par le catalogue.
 * budgetCandidates est exactement le vivier deja passe au sac a dos historique ; candidateGroups
 * ne sert qu'a reaplatir les alternatives du chemin portfolio_v2. Aucune planification rail,
 * recherche de site aerien ou generation de route ne repasse ici. Les statistiques sont
 * remplacees ensemble car IG| et IB| doivent decrire la meme solution que best, y compris
 * lorsqu'un sac a dos borne n'a pas prouve son optimum. */
function OpexReselectProjects(projects, capitalBudget)
{
  local funded = null;
  local considered = 0;
  if (PORTFOLIO_V2) {
    local alternatives = [];
    foreach (key, list in projects.candidateGroups) {
      foreach (project in list) alternatives.push(project);
    }
    funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);
    considered = alternatives.len();
    projects.stats.knapsackNodes = 0;
    projects.stats.knapsackExact = true;
  } else {
    local knapsack = OpexKnapsackSolve(projects.budgetCandidates, capitalBudget,
                                       ROAD_MAX_NEW_LINES_PER_YEAR, PROJECT_TOP_K);
    funded = knapsack.projects;
    considered = projects.budgetCandidates.len();
    projects.stats.knapsackNodes = knapsack.nodes;
    projects.stats.knapsackExact = knapsack.exact;
  }

  projects.stats.budgetConsidered = considered;
  projects.stats.budgetSelected = funded.len();
  projects.stats.budgetRejected = considered - funded.len();

  local selectedRev = 0;
  local selectedCap = 0;
  foreach (project in funded) {
    selectedRev += project.revenueAnnual;
    selectedCap += project.budgetCapital;
  }
  projects.stats.selectedRevenue = selectedRev;
  projects.stats.selectedCapital = selectedCap;

  projects.capitalBudget = capitalBudget;
  projects.capitalRemaining = capitalBudget - selectedCap;
  if (projects.capitalRemaining < 0) projects.capitalRemaining = 0;

  /* Le chemin historique consomme le portefeuille par revenu/opcode apres le sac a dos. */
  local byOpcodes = funded;
  if (!PORTFOLIO_V2) {
    byOpcodes = [];
    foreach (project in funded) {
      OpexProjectInsert(byOpcodes, project, "opcodeScore", PROJECT_TOP_K);
    }
  }
  projects.best = byOpcodes;
  return projects;
}

function OpexProjectEmptyRoad()
{
  return {
    all = 0, candidates = [], best = [],
    stats = { pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
              economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
              feederHubs = 0, feederCandidates = 0 },
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
  /* Branchement explicite plutot qu'une fonction passee dans un local : ce depot a deja paye
   * plusieurs echecs Squirrel silencieux, et ici une IA morte ressemblerait exactement a une IA
   * nulle au banc. */
  /* Le cout de decouverte mesure couvre TOUT le balayage (OpexAirPlans / OpexWaterPlans), pas un
   * plan en particulier. Le passer tel quel a chaque plan faisait rapporter N fois le meme cout
   * dans planningOpcodes, donc dans les panneaux OA| et eau : surestimation d'un facteur N, et
   * corruption de la mesure meme qui servirait a pricer la decouverte aerienne
   * (docs/taches.md S0 septies). On repartit desormais la depense entre les plans qu'elle a
   * produits. */
  local airOpsPerPlan = (airPlans.len() > 0) ? airOps / airPlans.len() : airOps;
  local waterOpsPerPlan = (waterPlans.len() > 0) ? waterOps / waterPlans.len() : waterOps;

  local winners = {};
  if (PORTFOLIO_V2) {
    foreach (candidate in rail.candidates) {
      OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate), stats);
    }
    foreach (candidate in road.candidates) {
      OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate), stats);
    }
    foreach (plan in airPlans) {
      OpexProjectRememberAll(winners, OpexProjectFromAir(catalog, plan, airOpsPerPlan), stats);
    }
    foreach (plan in waterPlans) {
      OpexProjectRememberAll(winners, OpexProjectFromWater(catalog, plan, waterOpsPerPlan), stats);
    }
  } else {
    foreach (candidate in rail.candidates) {
      OpexProjectRemember(winners, OpexProjectFromCandidate(candidate), stats);
    }
    foreach (candidate in road.candidates) {
      OpexProjectRemember(winners, OpexProjectFromCandidate(candidate), stats);
    }
    foreach (plan in airPlans) {
      OpexProjectRemember(winners, OpexProjectFromAir(catalog, plan, airOpsPerPlan), stats);
    }
    foreach (plan in waterPlans) {
      OpexProjectRemember(winners, OpexProjectFromWater(catalog, plan, waterOpsPerPlan), stats);
    }
  }

  local funded = null;
  local byBudget = [];
  if (PORTFOLIO_V2) {
    /* Toutes les alternatives de tous les couples, aplaties : c'est le test de capital qui
     * tranchera, pas une election modale prealable au ratio. */
    local alternatives = [];
    foreach (key, list in winners) {
      stats.odProjects++;
      foreach (project in list) alternatives.push(project);
    }
    funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);
    stats.budgetConsidered = alternatives.len();
    stats.budgetSelected = funded.len();
    stats.budgetRejected = alternatives.len() - funded.len();
    stats.knapsackNodes = 0;
    stats.knapsackExact = true;
  } else {
    foreach (key, project in winners) {
      stats.odProjects++;
      OpexProjectInsert(byBudget, project, "budgetScore", PROJECT_POOL_K);
    }
    local knapsack = OpexKnapsackSolve(byBudget, capitalBudget, ROAD_MAX_NEW_LINES_PER_YEAR, PROJECT_TOP_K);
    funded = knapsack.projects;
    stats.knapsackNodes = knapsack.nodes;
    stats.knapsackExact = knapsack.exact;
    stats.budgetConsidered = byBudget.len();
    stats.budgetSelected = funded.len();
    stats.budgetRejected = byBudget.len() - funded.len();
  }

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

  /* portfolio_v2 : on garde l'ordre de financement (profit par livre de capital). Le reclassement
   * par `opcodeScore` du chemin historique est un classement au REVENU par opcode, et comme un
   * seul projet est bati par cycle il decidait a lui seul lequel -- en contredisant l'objectif de
   * profit qu'on vient d'etablir. */
  local byOpcodes = funded;
  if (!PORTFOLIO_V2) {
    byOpcodes = [];
    foreach (project in funded) {
      OpexProjectInsert(byOpcodes, project, "opcodeScore", PROJECT_TOP_K);
    }
  }

  /* Le retour historique reste litteralement intact sous 0. Le bras 1 seul conserve le vivier :
   * cela evite meme de changer la forme de this._projects dans le controle. */
  if (PORTFOLIO_FRESH_BUDGET) {
    return {
      all = stats.odProjects, best = byOpcodes, stats = stats,
      capitalBudget = capitalBudget, generationCapitalBudget = capitalBudget,
      capitalRemaining = remaining, candidateGroups = winners, budgetCandidates = byBudget,
      rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
      airPlans = airPlans, waterPlans = waterPlans,
      airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
    };
  }
  return {
    all = stats.odProjects, best = byOpcodes, stats = stats,
    capitalBudget = capitalBudget, capitalRemaining = remaining,
    rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
    airPlans = airPlans, waterPlans = waterPlans,
    airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
  };
}
