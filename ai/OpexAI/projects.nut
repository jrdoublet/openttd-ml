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
CLEAN_DENSITY_SCORE <- true;
CAPITAL_CEILING_CYCLES <- 24;

/* Journal historique conserve mot pour mot pour le chemin tension_probe=0. */
function OpexLogPortfolioRank(projects)
{
  if (!DECISION_LOG) return;
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) return;
  local n = projects.best.len();
  if (n > 5) n = 5;
  for (local i = 0; i < n; i++) {
    local p = projects.best[i];
    if (p == null) continue;
    local cargoStr = ("cargo" in p && p.cargo >= 0) ? AICargo.GetCargoLabel(p.cargo) : "none";
    local scoreVal = ((TENSION_SCORING || SHADOW_PRICING) && ("tensionScore" in p)) ? p.tensionScore : p.budgetScore;
    if (DECISION_LOG) OpexDecide("PORTFOLIO_RANK", "rank=" + i + " mode=" + p.mode + " kind=" + p.kind + " cargo=" + cargoStr + " src=" + p.src + " dst=" + p.dst + " dist=" + p.distance + " roi=" + p.roi + " score=" + scoreVal + " cost=" + p.capital + " profit=" + p.profitAnnual);
  }
}

/* Remplace le logger ci-dessus uniquement a l'activation de la sonde. Le meme parcours publie
 * PORTFOLIO_RANK si demande, puis TENSION ; aucun second parcours du portefeuille n'est cree.
 * Le contexte -- flotte, plafonds, engagements, foncier -- ne depend PAS du projet : il est
 * calcule une seule fois, hors de la boucle. Un seul bloc de budget encadre l'ensemble, pour que
 * probe_ops mesure le cout REEL de la sonde par cycle et non par projet. */
function OpexLogPortfolioRankWithTension(projects)
{
  if (!DECISION_LOG && !TENSION_PROBE) return;
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) return;
  local n = projects.best.len();
  if (n > 5) n = 5;

  TENSION_BUDGET.begin();
  local ctx = OpexTensionContext(projects);
  local lines = [];
  for (local i = 0; i < n; i++) {
    local p = projects.best[i];
    if (p == null) continue;
    local result = OpexTensionVector(p, ctx);
    local fields = "rank=" + i + " mode=" + p.mode + " dominant=" + result.dominant
                 + " gap=" + result.gapRelative;
    foreach (entry in result.vector) {
      fields += " " + entry.resource + "_tension=" + entry.tension
              + " " + entry.resource + "_cost=" + entry.cost
              + " " + entry.resource + "_available=" + entry.available
              + " " + entry.resource + "_commitments=" + entry.commitments
              + " " + entry.resource + "_flow=" + entry.flow
              + " " + entry.resource + "_tau=" + entry.tau;
    }
    lines.append(fields);
  }
  local spent = TENSION_BUDGET.end("tension");

  /* Journalisation hors du bloc mesure : le cout du journal n'est pas celui du calcul. */
  for (local i = 0; i < n; i++) {
    local p = projects.best[i];
    if (p == null) continue;
    local cargoStr = ("cargo" in p && p.cargo >= 0) ? AICargo.GetCargoLabel(p.cargo) : "none";
    local scoreVal = ((TENSION_SCORING || SHADOW_PRICING) && ("tensionScore" in p)) ? p.tensionScore : p.budgetScore;
    if (DECISION_LOG) OpexDecide("PORTFOLIO_RANK", "rank=" + i + " mode=" + p.mode + " kind=" + p.kind + " cargo=" + cargoStr + " src=" + p.src + " dst=" + p.dst + " dist=" + p.distance + " roi=" + p.roi + " score=" + scoreVal + " cost=" + p.capital + " profit=" + p.profitAnnual);
  }
  foreach (fields in lines) OpexDecide("TENSION", fields);
  /* Les quatre mesures foncieres cote a cote : le stock d'origines libres (celui qui est
   * desormais au denominateur), la pression de separation, les paires produites, et l'ancien
   * proxy de taille de vivier. C'est ce qui permet de comparer les mesures entre elles au lieu
   * d'en figer une a l'aveugle. */
  OpexDecide("TENSION_COST", "probe_ops=" + spent + " projects=" + lines.len()
             + " fleet_rail=" + ctx.fleet.rail + " fleet_road=" + ctx.fleet.road
             + " fleet_air=" + ctx.fleet.air + " fleet_water=" + ctx.fleet.water
             + " origins_free=" + ctx.originsFree + " origins_served=" + ctx.originsServed
             + " pairs_total=" + ctx.pairsTotal + " separation_rejected=" + ctx.separationRejected
             + " pairs_one_served=" + ctx.pairsOneServed
             + " pool_rail=" + ctx.pool.rail + " pool_road=" + ctx.pool.road
             + " pool_air=" + ctx.pool.air + " pool_water=" + ctx.pool.water);
}

/* C32 : un feeder n'est pas une desserte origine-destination, c'est un RABATTEMENT vers un hub.
 * Lui laisser la meme cle qu'une liaison pax entre les deux memes points le ferait concourir --
 * et gagner, son ROI reseau etant eleve -- contre la ligne aerienne du hub dans
 * OpexProjectModeBetter, qui n'en garde qu'un par cle. Sous portfolio_v2 = 0 (le defaut),
 * l'eviction est reelle : c'est le motif pour lequel C29.3 les avait sortis du portefeuille.
 * Un prefixe distinct les fait concourir sur le CAPITAL, dans le sac a dos, sans jamais evincer
 * un autre mode sur une cle partagee. */
function OpexProjectKeyFor(project)
{
  local prefix = "";
  if (project.mode == "fleet") {
    /* C34.2 : un achat d'avion n'a pas d'origine-destination -- il appartient a UNE ligne. */
    local lid = (("payload" in project) && project.payload != null
                 && ("line" in project.payload) && ("lineId" in project.payload.line))
                ? project.payload.line.lineId : -1;
    return "fleet|" + lid;
  }
  if (("payload" in project) && project.payload != null
      && ("isFeeder" in project.payload) && project.payload.isFeeder) {
    prefix = "feeder|";
    if ("hubStationId" in project.payload) prefix += project.payload.hubStationId + "|";
  }
  return prefix + OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
}

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
  if (value <= 0 || cost <= 0) return 0.0;
  return (value.tofloat() * 1000.0) / cost;
}

function OpexProjectFromCandidate(candidate, tensionCtx = null)
{
  if (candidate == null || candidate.profitAnnual <= 0 || candidate.revenueAnnual <= 0 ||
      candidate.capital <= 0) return null;
  local mode = candidate.mode;
  local margin = 0;
  local expectedOps = 0;
  if (mode == "rail") {
    /* C21 : candidate.iterations peut prédire 36k à 75k itérations sur les longues distances,
     * mais le pathfinder réel est plafonné à HARD_ITERATION_CAP (10 000). Ne pas borner ici
     * surestime expectedOps d'un facteur 4 à 7 et pénalise le rail dans opcodeScore. */
    local iters = candidate.iterations;
    if (iters > HARD_ITERATION_CAP) iters = HARD_ITERATION_CAP;
    expectedOps = iters * PROJECT_RAIL_OPS_PER_ITERATION
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
  if (("immobilise" in candidate) && candidate.immobilise > 0) {
    budgetCapital += candidate.immobilise;
  }
  local scoreRevenue = candidate.revenueAnnual;
  if (!CLEAN_DENSITY_SCORE) {
    if (candidate.kind == "freight" && ("freightBonus" in candidate) && candidate.freightBonus > 100) {
      scoreRevenue = (scoreRevenue * candidate.freightBonus) / 100;
    }
  }
  local project = {
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
  project.tensionScore <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null)
      ? OpexTensionScore(project, tensionCtx)
      : project.budgetScore;
  project.tensionRegime <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null && ("regime" in tensionCtx))
      ? tensionCtx.regime : "none";
  return project;
}

/* C34.2 : un ACHAT D'AVION devient un projet, pour etre arbitre contre les lignes neuves au lieu
 * d'etre servi d'office avant elles (la tache air_fleet passait avant `projects` dans l'ordre de
 * service, main.nut:626-630, donc elle avait un droit de tirage sur la tresorerie).
 *
 * L'entree vient du MODE A BLANC de _resizeAirFleets : toutes les gardes de refus ont deja ete
 * franchies, y compris la regle de tampon C14 qui garantit qu'une pleine capacite d'avion attend
 * reellement au sol. Il ne reste ici qu'a pricer la marge.
 *
 * Profit marginal : on prefere le profit REALISE par appareil quand la ligne en a un ; sinon on
 * retombe sur sa prediction (predRevenue - predRunning) par appareil. Sans ce repli, aucune ligne
 * de moins d'un an ne produirait de projet de flotte -- or l'annee 1 est precisement la cible. */
function OpexProjectFromFleet(entry, tensionCtx = null)
{
  if (entry == null || entry.want <= 0 || entry.planePrice <= 0) return null;
  local line = entry.line;
  local have = ("vehCount" in line && line.vehCount > 0) ? line.vehCount
             : (("vehicles" in line) ? line.vehicles.len() : 0);
  if (have < 1) return null;

  local perPlaneProfit = 0;
  if (("lastProfit" in line) && line.lastProfit > 0) {
    perPlaneProfit = line.lastProfit / have;
  } else if (("predRevenue" in line) && line.predRevenue > 0) {
    local running = ("predRunning" in line) ? line.predRunning : 0;
    local planes = ("predTrains" in line && line.predTrains > 0) ? line.predTrains : have;
    perPlaneProfit = (line.predRevenue - running) / planes;
  }
  if (perPlaneProfit <= 0) return null;

  local profit = perPlaneProfit * entry.want;
  local capital = entry.planePrice * entry.want;
  local revenue = profit;
  if (("predRevenue" in line) && line.predRevenue > 0) {
    local planes = ("predTrains" in line && line.predTrains > 0) ? line.predTrains : have;
    revenue = (line.predRevenue / planes) * entry.want;
  }
  /* Un achat d'avion ne coute aucune planification : ni pathfinder, ni sondage de site. Seules
   * les commandes transactionnelles restent, d'ou un opcodeScore structurellement tres favorable
   * -- c'est exact, et c'est precisement ce que l'arbitrage doit pouvoir voir. */
  local expectedOps = PROJECT_ROAD_TRANSACTION_OPS;
  local project = {
    mode = "fleet", kind = "fleet", cargo = line.cargo,
    src = line.stationA, dst = ("stationB" in line) ? line.stationB : line.stationA,
    payload = entry, distance = 0, capital = capital,
    budgetCapital = capital, profitAnnual = profit, revenueAnnual = revenue,
    roi = capital > 0 ? (profit * 1000) / capital : 0,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(revenue, capital),
    opcodeScore = OpexProjectScore(revenue, expectedOps),
    planningOpcodes = 0,
  };
  project.tensionScore <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null)
      ? OpexTensionScore(project, tensionCtx)
      : project.budgetScore;
  project.tensionRegime <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null && ("regime" in tensionCtx))
      ? tensionCtx.regime : "none";
  return project;
}

function OpexProjectFromAir(catalog, plan, planningOps, tensionCtx = null)
{
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  if (economics.profitAnnual <= 0 || economics.revenueAnnual <= 0 ||
      economics.capital <= 0) return null;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local margin = AIR_MARGIN_V2
      ? ((newAirports == 2) ? 15000 : (newAirports == 1 ? 6000 : 0))
      : ((newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000));
  local budgetCapital = economics.capital + margin;
  if (("immobilise" in economics) && economics.immobilise > 0) {
    budgetCapital += economics.immobilise;
  }
  /* La decouverte a deja ete payee pendant l'etape projets. La contrainte d'execution ne porte
   * que sur les opcodes encore necessaires pour construire le projet. */
  local expectedOps = PROJECT_AIR_TRANSACTION_OPS;
  local project = {
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
  project.tensionScore <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null)
      ? OpexTensionScore(project, tensionCtx)
      : project.budgetScore;
  project.tensionRegime <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null && ("regime" in tensionCtx))
      ? tensionCtx.regime : "none";
  return project;
}

function OpexProjectFromWater(catalog, plan, planningOps, tensionCtx = null)
{
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  if (economics.profitAnnual <= 0 || economics.revenueAnnual <= 0 ||
      economics.capital <= 0) return null;
  local budgetCapital = economics.capital + WATER_CAPITAL_MARGIN;
  if (("immobilise" in economics) && economics.immobilise > 0) {
    budgetCapital += economics.immobilise;
  }
  local expectedOps = PROJECT_WATER_TRANSACTION_OPS;
  local project = {
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
  project.tensionScore <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null)
      ? OpexTensionScore(project, tensionCtx)
      : project.budgetScore;
  project.tensionRegime <- ((TENSION_SCORING || SHADOW_PRICING) && tensionCtx != null && ("regime" in tensionCtx))
      ? tensionCtx.regime : "none";
  return project;
}

/* Comparaison strictement modale : sous TENSION_SCORING, departage sur tensionScore (loi de Liebig).
 * Sinon : ROI, puis profit, revenu et enfin calcul. */
function OpexProjectModeBetter(candidate, incumbent)
{
  if (incumbent == null) return true;
  if (TENSION_SCORING || SHADOW_PRICING) {
    local tCand = ("tensionScore" in candidate) ? candidate.tensionScore : 0.0;
    local tInc = ("tensionScore" in incumbent) ? incumbent.tensionScore : 0.0;
    if (tCand != tInc) return tCand > tInc;
  }
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
  local key = OpexProjectKeyFor(project);
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
  local key = OpexProjectKeyFor(project);
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
  local scoreKey = (TENSION_SCORING || SHADOW_PRICING) ? "tensionScore" : "fundScore";
  foreach (project in alternatives) {
    if (project.budgetCapital > capitalBudget) continue;
    if (project.profitAnnual < floorProfit) continue;
    if (!TENSION_SCORING && !SHADOW_PRICING) {
      project.fundScore <- OpexProjectScore(project.profitAnnual, project.budgetCapital);
    }
    OpexProjectInsert(affordable, project, scoreKey, limit);
  }
  /* Filet de securite : si le plancher a tout ecarte -- il ne le peut pas puisque le meilleur
   * projet l'atteint par construction, mais un profitAnnual nul ou negatif rendrait bestProfit nul
   * et le plancher inoperant -- on retombe sur l'ensemble finançable brut plutot que de ne rien
   * batir du tout. */
  if (affordable.len() == 0 && floorProfit > 0) {
    foreach (project in alternatives) {
      if (project.budgetCapital > capitalBudget) continue;
      if (!TENSION_SCORING && !SHADOW_PRICING) {
        project.fundScore <- OpexProjectScore(project.profitAnnual, project.budgetCapital);
      }
      OpexProjectInsert(affordable, project, scoreKey, limit);
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

/* C36.2 : Construction multimodale du vivier budgetaire.
 * Empeche un mode a faible capital unitaire (ex. rail fret court ou route) de saturer l'integralite
 * des PROJECT_POOL_K places et d'evincer completement l'aerien ou le refleet avant le sac a dos.
 * Phase 1 : reserve des quotas pour les meilleurs projets de chaque mode present.
 * Phase 2 : complete le vivier jusqu'au plafond global avec les meilleurs restants tout mode confondu. */
function OpexBuildMultimodalBudgetPool(winners, stats, capitalCeiling, scoreField, poolLimit = 128)
{
  local byMode = { rail = [], road = [], air = [], water = [], fleet = [] };
  local infundableByMode = { rail = 0, road = 0, air = 0, water = 0 };

  foreach (key, project in winners) {
    if (project == null) continue;
    stats.odProjects++;
    if (POOL_FINANCEABLE && project.budgetCapital > capitalCeiling) {
      stats.poolInfundable++;
      if (DECISION_LOG && (project.mode in infundableByMode)) infundableByMode[project.mode]++;
      continue;
    }
    local m = project.mode;
    if (!(m in byMode)) byMode[m] <- [];
    OpexProjectInsert(byMode[m], project, scoreField, poolLimit);
  }

  if (DECISION_LOG && stats.poolInfundable > 0) {
    OpexDecide("VIVIER_INFUNDABLE", "rail=" + infundableByMode.rail + " road=" + infundableByMode.road
               + " air=" + infundableByMode.air + " water=" + infundableByMode.water
               + " total=" + stats.poolInfundable + " ceiling=" + capitalCeiling);
  }

  local quotas = { air = 16, fleet = 12, road = 24, water = 8, rail = 48 };
  local byBudget = [];
  local used = {};

  /* Phase 1 : Reserver les meilleurs de chaque mode */
  foreach (m, list in byMode) {
    local q = (m in quotas) ? quotas[m] : 8;
    local take = list.len() < q ? list.len() : q;
    for (local i = 0; i < take; i++) {
      byBudget.append(list[i]);
      local pKey = list[i].mode + "|" + list[i].src + "|" + list[i].dst;
      used[pKey] <- true;
    }
  }

  /* Phase 2 : Remplir le solde jusqu'a poolLimit avec les meilleurs restants */
  local remaining = [];
  foreach (m, list in byMode) {
    for (local i = 0; i < list.len(); i++) {
      local pKey = list[i].mode + "|" + list[i].src + "|" + list[i].dst;
      if (!(pKey in used)) {
        OpexProjectInsert(remaining, list[i], scoreField, poolLimit);
      }
    }
  }

  for (local i = 0; i < remaining.len() && byBudget.len() < poolLimit; i++) {
    byBudget.append(remaining[i]);
  }

  return byBudget;
}

/* Solveur Knapsack 0/1 borne (Branch & Bound avec borne superieure fractionnaire gloutonne)
 * sur les candidats classes par budgetScore. Le plafond de noeuds protege les opcodes ; le
 * resultat expose donc explicitement si l'optimalite a pu etre prouvee. */
function OpexKnapsackComputeBound(candidates, n, startIdx, cap)
{
  local bound = 0;
  local rem = cap;

  /* G1§1 : l'ancien remplissage glouton suivait l'ordre du tri composite
   * (75 % budgetScore + 25 % opcodeScore). Cet ordre n'est PAS la densite pure de
   * l'objectif : opcodeScore peut intervertir deux items de densites differentes, et la
   * borne gloutonne devient alors une SOUS-estimation -- l'elagage coupe des solutions
   * valides. Le chemin tension utilisait deja maxDensity * rem, qui est une borne
   * superieure correcte. On unifie les deux chemins. */
  local maxDensity = 0.0;
  for (local j = startIdx; j < n; j++) {
    local p = candidates[j];
    local pv = KNAPSACK_ROI ? p.profitAnnual : p.revenueAnnual;
    if (p.budgetCapital > 0) {
      local d = pv.tofloat() / p.budgetCapital;
      if (d > maxDensity) maxDensity = d;
    }
  }
  return (maxDensity * rem).tointeger();
}

function OpexProjectConflictKeys(p)
{
  local keys = [];
  local mode = p.mode;
  if (mode == "rail") {
    /* Deux projets rail ne doivent pas brancher sur la meme industrie ou gare en meme temps */
    keys.append("rail|" + p.src);
    keys.append("rail|" + p.dst);
  } else if (mode == "air") {
    local s = p.src;
    local d = p.dst;
    if (s > d) { local swap = s; s = d; d = swap; }
    keys.append("air|" + s + "|" + d);
    local plan = p.payload;
    if (plan != null) {
      if (!("reuseA" in plan) || !plan.reuseA) keys.append("new_airport|" + p.src);
      if (!("reuseB" in plan) || !plan.reuseB) keys.append("new_airport|" + p.dst);
    }
  } else if (mode == "road") {
    local s = p.src;
    local d = p.dst;
    if (s > d) { local swap = s; s = d; d = swap; }
    local isFeeder = (("payload" in p) && p.payload != null && ("isFeeder" in p.payload) && p.payload.isFeeder);
    if (isFeeder) {
      local hubId = ("hubStationId" in p.payload) ? p.payload.hubStationId : d;
      keys.append("feeder_hub|" + hubId);
      keys.append("feeder|" + s + "|" + d);
    } else {
      keys.append("road|" + s + "|" + d);
    }
  } else if (mode == "water") {
    local s = p.src;
    local d = p.dst;
    if (s > d) { local swap = s; s = d; d = swap; }
    keys.append("water|" + s + "|" + d);
  } else if (mode == "fleet") {
    if (p.payload != null && ("line" in p.payload) && ("lineId" in p.payload.line)) {
      keys.append("fleet|" + p.payload.line.lineId);
    }
  }
  return keys;
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

  // Branche 1 : Inclure le projet si finançable et respecte les contraintes modales
  local conflictKeys = OpexProjectConflictKeys(p);
  local hasConflict = false;
  foreach (k in conflictKeys) {
    if (k in state.originsUsed) { hasConflict = true; break; }
  }
  local canInclude = !hasConflict && (currentCapital + p.budgetCapital <= state.capitalBudget);
  if (canInclude && p.mode == "road" && currentRoad >= state.maxRoad) canInclude = false;

  if (canInclude) {
    currentItems.append(p);
    foreach (k in conflictKeys) state.originsUsed[k] <- true;
    local objValue = (TENSION_SCORING || SHADOW_PRICING || KNAPSACK_ROI) ? p.profitAnnual : p.revenueAnnual;
    OpexKnapsackSearch(state, idx + 1, currentCapital + p.budgetCapital,
                       currentRevenue + objValue,
                       p.mode == "road" ? currentRoad + 1 : currentRoad, currentItems);
    foreach (k in conflictKeys) delete state.originsUsed[k];
    currentItems.pop();
  }

  // Branche 2 : Exclure le projet
  OpexKnapsackSearch(state, idx + 1, currentCapital, currentRevenue, currentRoad, currentItems);
}

/* Résout le problème du sac à dos 0/1 borné par Branch & Bound.
 * Maximise la somme des revenueAnnual sous contrainte de capitalBudget, maxRoad et maxItems --
 * ou la somme des profitAnnual sous knapsack_roi. Le revenu ignore le roulement : deux projets
 * a revenu egal y sont equivalents meme si l'un paie deux fois plus de frais. Le meme defaut
 * avait deja ete corrige un etage plus bas (economy.nut:261, choix du nombre de convois) sans
 * qu'on remonte d'un cran. Voir docs/taches.md C13. */
function OpexKnapsackSolve(candidates, capitalBudget, maxRoad = 18, maxItems = 32)
{
  if (candidates.len() == 0 || capitalBudget <= 0) {
    return { projects = [], nodes = 0, exact = true };
  }

  // Trier les candidats par score composite décroissant (rendement économique et efficacité d'opcodes)
  /* L'ordre de branchement doit suivre la DENSITE de la grandeur optimisee, sinon la borne
   * gloutonne majore mal et le Branch & Bound explore dans le desordre. budgetScore est une
   * densite de REVENU par livre ; sous knapsack_roi on lui substitue la densite de PROFIT. */
  /* Chemin ETEINT laisse mot pour mot tel qu'il etait, pour que le socle ne glisse pas : ici le
   * comportement depend des opcodes consommes. Chemin allume : cle precalculee plutot que lue
   * dans la closure -- ce depot n'a aucun precedent de globale lue depuis un comparateur, et une
   * passe sur 64 candidats coute moins que deux lectures par comparaison sur ~384 comparaisons. */
  if (KNAPSACK_ROI) {
    foreach (c in candidates) {
      /* Densite de PROFIT par livre, calculee ICI et pas dans les constructeurs : la porter
       * en champ la ferait payer aux DEUX bras. profitAnnual est deja net du roulement et de
       * l'amortissement, et le capital rail deja corrige du terrain (RAIL_TERRAIN_FACTOR).
       * Le bonus fret est REPRIS a l'identique du chemin revenu (voir OpexProjectFromCandidate) :
       * sans lui, basculer sur le profit retirerait AUSSI la preference fret (jusqu'a x1,89),
       * et le banc mesurerait deux changements au lieu d'un. */
      local scoreProfit = c.profitAnnual;
      if (!CLEAN_DENSITY_SCORE) {
        if (c.kind == "freight" && ("payload" in c) && c.payload != null
            && ("freightBonus" in c.payload) && c.payload.freightBonus > 100) {
          scoreProfit = (scoreProfit * c.payload.freightBonus) / 100;
        }
      }
      local roiScore = OpexProjectScore(scoreProfit, c.budgetCapital);
      c.sortKey <- (roiScore * 75 + c.opcodeScore * 25).tofloat();
    }
    candidates.sort(function(a, b) {
      if (a.sortKey > b.sortKey) return -1;
      if (a.sortKey < b.sortKey) return 1;
      return 0;
    });
  } else {
    candidates.sort(function(a, b) {
      if ((TENSION_SCORING || SHADOW_PRICING) && ("tensionScore" in a) && ("tensionScore" in b)) {
        if (a.tensionScore > b.tensionScore) return -1;
        if (a.tensionScore < b.tensionScore) return 1;
        return 0;
      }
      local va = (a.budgetScore * 75 + a.opcodeScore * 25).tofloat();
      local vb = (b.budgetScore * 75 + b.opcodeScore * 25).tofloat();
      if (va > vb) return -1;
      if (va < vb) return 1;
      return 0;
    });
  }

  local n = candidates.len();
  if (n > 64) n = 64; // Limiter aux 64 meilleurs candidats

  if (DECISION_LOG) {
    local airInCand = 0;
    for (local i = 0; i < n; i++) {
      local c = candidates[i];
      if (c.mode == "air") airInCand++;
      if (i < 10 || c.mode == "air") {
        local arm = (("payload" in c) && c.payload != null && ("arm" in c.payload)) ? c.payload.arm : "none";
        OpexDecide("KS_CAND", "i=" + i + " mode=" + c.mode + " arm=" + arm + " src=" + c.src + " dst=" + c.dst
                   + " cap=" + c.budgetCapital + " rev=" + c.revenueAnnual + " prof=" + c.profitAnnual
                   + " bScore=" + c.budgetScore + " oScore=" + c.opcodeScore);
      }
    }
    OpexDecide("KS_POOL", "n=" + n + " total=" + candidates.len() + " air=" + airInCand + " budget=" + capitalBudget);
  }

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
  if (DECISION_LOG) {
    local solSummary = "items=" + state.bestSolution.len() + " val=" + state.bestValue;
    foreach (idx, sol in state.bestSolution) {
      solSummary += " [" + idx + ":" + sol.mode + ":" + sol.src + "->" + sol.dst + ":cap=" + sol.budgetCapital + "]";
    }
    OpexDecide("KS_SOL", solSummary);
  }
  return { projects = state.bestSolution, nodes = state.nodeCount, exact = !state.truncated };
}

function OpexLogVivier(path, candidates, stats, capitalBudget, capitalRemaining)
{
  if (!DECISION_LOG) return;
  if (DECISION_LOG) {
    OpexDecide("VIVIER", "path=" + path + " considered=" + stats.budgetConsidered
               + " selected=" + stats.budgetSelected + " rejected=" + stats.budgetRejected
               + " infundable=" + stats.poolInfundable
               + " budget=" + capitalBudget + " remaining=" + capitalRemaining);
  }
  if (candidates == null) return;
  if (DECISION_LOG) {
    local rail = 0;
    local road = 0;
    local air = 0;
    local water = 0;
    local seenSrcs = {};
    local seenDsts = {};
    local seenPairs = {};
    local nSrcs = 0;
    local nDsts = 0;
    local nPairs = 0;
    foreach (p in candidates) {
      if (p == null) continue;
      local m = ("mode" in p) ? p.mode : null;
      if (m == "rail") rail++;
      else if (m == "road") road++;
      else if (m == "air") air++;
      else if (m == "water") water++;

      if (("src" in p) && ("dst" in p) && p.src != null && p.dst != null) {
        local s = p.src;
        local d = p.dst;
        local sk = "" + s;
        if (!(sk in seenSrcs)) { seenSrcs[sk] <- true; nSrcs++; }
        local dk = "" + d;
        if (!(dk in seenDsts)) { seenDsts[dk] <- true; nDsts++; }
        local pk = "" + s + ":" + d;
        if (!(pk in seenPairs)) { seenPairs[pk] <- true; nPairs++; }
      }
    }
    local total = candidates.len();
    OpexDecide("VIVIER_MIX", "rail=" + rail + " road=" + road + " air=" + air
               + " water=" + water + " total=" + total);
    OpexDecide("VIVIER_DIV", "srcs=" + nSrcs + " dsts=" + nDsts + " pairs=" + nPairs
               + " total=" + total);
  }
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

  if (DECISION_LOG) {
    local vivierPool = null;
    if (PORTFOLIO_V2) {
      vivierPool = [];
      if (("candidateGroups" in projects) && projects.candidateGroups != null) {
        foreach (key, list in projects.candidateGroups) {
          foreach (project in list) vivierPool.push(project);
        }
      }
    } else {
      vivierPool = ("budgetCandidates" in projects) ? projects.budgetCandidates : null;
    }
    OpexLogVivier("reselect", vivierPool, projects.stats, projects.capitalBudget, projects.capitalRemaining);
  }

  return projects;
}

/* C36.1 : Revalidation rapide d'un candidat deja en memoire contre this._lines.
 * Verifie qu'aucune extremite n'est devenue invalide, qu'aucune ligne identique n'a ete batie,
 * et que les contraintes physiques du mode tiennent toujours. */
function OpexIncrementalCandidateStillValid(p, lines, abandonedPairs = null)
{
  if (p == null) return false;
  local mode = p.mode;

  /* 0. Candidat abandonne (echec de trace ou depot) */
  if (abandonedPairs != null) {
    if (mode == "air") {
      local plan = p.payload;
      if (plan != null && ("siteA" in plan) && ("siteB" in plan)) {
        local aKey1 = "air|" + plan.siteA.town.tile + "|" + plan.siteB.town.tile;
        local aKey2 = "air|" + plan.siteB.town.tile + "|" + plan.siteA.town.tile;
        if ((aKey1 in abandonedPairs) || (aKey2 in abandonedPairs)) return false;
      }
    } else if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (mode == "road" || mode == "rail")) {
      if (("payload" in p) && p.payload != null) {
        local aKey = OpexAbandonedPairKey(p.payload);
        if (aKey in abandonedPairs) return false;
      }
    }
  }

  /* 1. Doublon exact avec une ligne deja batie */
  foreach (line in lines) {
    if (("cargo" in line) && line.cargo == p.cargo &&
        ("originA" in line) && ("originB" in line) &&
        ((line.originA == p.src && line.originB == p.dst) ||
         (line.originA == p.dst && line.originB == p.src))) {
      return false;
    }
  }

  /* 2. Mode route */
  if (mode == "road") {
    local isFeeder = (("payload" in p) && p.payload != null &&
                      ("isFeeder" in p.payload) && p.payload.isFeeder);
    if (isFeeder) {
      local cand = p.payload;
      local isHubTown = ("isHubTown" in cand) ? cand.isHubTown : false;
      local maxFeeders = 1;
      if (isHubTown && FEEDER_TOWN_COVERAGE) {
        local tId = ("srcTown" in cand && cand.srcTown >= 0) ? cand.srcTown : AITile.GetClosestTown(cand.src);
        local houses = AITown.IsValidTown(tId) ? AITown.GetHouseCount(tId) : 0;
        if (houses <= 0 && AITown.IsValidTown(tId)) houses = AITown.GetPopulation(tId) / 25;
        maxFeeders = OpexCeilDiv(houses, ROAD_STOP_CATCHMENT_HOUSES);
        if (maxFeeders > 4) maxFeeders = 4;
        if (maxFeeders < 1) maxFeeders = 1;
      }
      local currCount = OpexTownFeederCount(lines, cand.src, cand.hubStationId);
      local slot = ("feederSlot" in cand) ? cand.feederSlot : 0;
      local currYear = AIDate.GetYear(AIDate.GetCurrentDate());
      local startYear = 1970;
      if (currCount >= maxFeeders || (slot >= 1 && (currYear - startYear) < 2)) return false;
    } else {
      if (OpexOriginServed(lines, p.src, true)) return false;
      if (OpexOriginServed(lines, p.dst, true)) return false;
      if (p.kind == "pax" && OpexRoadPairServed(lines, p.src, p.dst)) return false;
    }
    return true;
  }

  /* 3. Mode rail : les deux extremites servies excluent la ligne */
  if (mode == "rail") {
    if (OpexOriginServed(lines, p.src, false) && OpexOriginServed(lines, p.dst, false)) {
      return false;
    }
    return true;
  }

  /* 4. Mode aerien : validite du plan de lot et constructibilite des sites */
  if (mode == "air") {
    local plan = p.payload;
    if (plan == null) return false;
    if (!OpexAirBatchPlanStillLive(plan, lines)) return false;
    if (!OpexAirBatchSiteStillBuildable(plan.siteA, plan.airport, plan.plane,
                                         ("reuseA" in plan) && plan.reuseA)) {
      return false;
    }
    if (!OpexAirBatchSiteStillBuildable(plan.siteB, plan.airport, plan.plane,
                                         ("reuseB" in plan) && plan.reuseB)) {
      return false;
    }
    return true;
  }

  /* 5. Mode maritime : dock constructible */
  if (mode == "water") {
    local plan = p.payload;
    if (plan == null || !("siteA" in plan) || !("siteB" in plan)) return false;
    if (!OpexWaterBatchSiteStillBuildable(plan.siteA) ||
        !OpexWaterBatchSiteStillBuildable(plan.siteB)) {
      return false;
    }
    return true;
  }

  return true;
}

/* C38 : cle stable d'une tentative au sein d'un batch. Les plans air/eau sont des objets
 * regenerables ; l'identite doit donc reposer sur le mode, les extremites, le cargo et le type,
 * jamais sur l'adresse du payload. La flotte cible une ligne existante. */
function OpexProjectAttemptKey(p)
{
  if (p == null) return "none";
  local mode = ("mode" in p) ? p.mode : "unknown";
  if (mode == "fleet" && ("payload" in p) && p.payload != null &&
      ("line" in p.payload) && p.payload.line != null && ("lineId" in p.payload.line)) {
    return "fleet|" + p.payload.line.lineId;
  }
  local src = ("src" in p) ? p.src : -1;
  local dst = ("dst" in p) ? p.dst : -1;
  local cargo = ("cargo" in p) ? p.cargo : -1;
  local kind = ("kind" in p) ? p.kind : "";
  return mode + "|" + src + "|" + dst + "|" + cargo + "|" + kind;
}

/* Retire du vivier incremental les projets deja essayes dans le batch courant, puis rejoue la
 * seule contrainte de capital. Le filtre porte sur les deux representations afin de garder le
 * chemin portfolio_v2 et le solveur historique coherents. */
function OpexDynamicBatchReselect(projects, lines, attempted, capitalBudget, abandonedPairs = null)
{
  if (projects == null) return null;
  if (("candidateGroups" in projects) && projects.candidateGroups != null) {
    local filteredGroups = {};
    foreach (groupKey, entry in projects.candidateGroups) {
      local source = (typeof(entry) == "array") ? entry : [entry];
      local kept = [];
      foreach (p in source) {
        if (p == null) continue;
        if (!OpexIncrementalCandidateStillValid(p, lines, abandonedPairs)) continue;
        local key = OpexProjectAttemptKey(p);
        if (!(key in attempted)) kept.push(p);
      }
      if (kept.len() > 0) filteredGroups[groupKey] <- kept;
    }
    projects.candidateGroups = filteredGroups;
  }
  if (("budgetCandidates" in projects) && projects.budgetCandidates != null) {
    local filteredBudget = [];
    foreach (p in projects.budgetCandidates) {
      if (p == null) continue;
      if (!OpexIncrementalCandidateStillValid(p, lines, abandonedPairs)) continue;
      local key = OpexProjectAttemptKey(p);
      if (!(key in attempted)) filteredBudget.push(p);
    }
    projects.budgetCandidates = filteredBudget;
  }
  return OpexReselectProjects(projects, capitalBudget);
}

/* C36.1 : Caching incremental du vivier post-chantier.
 * Au lieu de reconstruire tout le portefeuille ex nihilo apres chaque ligne achevee (15 jours
 * d'attente sur A* et scan aerien), filtre les candidats existants en memoire, injecte les
 * nouveaux feeders / opportunites de flotte, et resout le sac a dos sur la tresorerie restante.
 * Execution : < 1 tick (< 500 opcodes, 0 jour). */
function OpexIncrementalUpdateProjects(projects, catalog, budget, lines, capitalBudget, fleetPlan = null, abandonedPairs = null)
{
  local stats = {
    odProjects = 0,
    modeCandidates = 0,
    modeAlternatives = 0,
    modeReplaced = 0,
    poolInfundable = 0,
    budgetConsidered = 0,
    budgetSelected = 0,
    budgetRejected = 0,
    selectedRevenue = 0,
    selectedCapital = 0,
    knapsackNodes = 0,
    knapsackExact = true,
  };

  local tensionCtx = null;
  if (TENSION_SCORING || SHADOW_PRICING) {
    tensionCtx = OpexTensionContext(projects);
  }

  local newWinners = {};

  /* 1. Filtrer les candidats existants du vivier */
  if (("candidateGroups" in projects) && projects.candidateGroups != null) {
    foreach (key, entry in projects.candidateGroups) {
      local list = (typeof entry == "array") ? entry : [entry];
      foreach (p in list) {
        if (p == null) continue;
        /* La flotte et les feeders sont regeneres frais ci-dessous */
        if (p.mode == "fleet") continue;
        if (("payload" in p) && p.payload != null &&
            ("isFeeder" in p.payload) && p.payload.isFeeder) continue;
        if (!OpexIncrementalCandidateStillValid(p, lines, abandonedPairs)) continue;
        if (PORTFOLIO_V2) {
          OpexProjectRememberAll(newWinners, p, stats);
        } else {
          OpexProjectRemember(newWinners, p, stats);
        }
      }
    }
  }

  /* 2. Injection des rabattements (feeders) frais vers les hubs */
  if (FEEDER_PORTFOLIO && ("roadType" in catalog) && catalog.roadType >= 0) {
    local freshFeeders = [];
    local feederStats = {
      pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
      economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
      feederHubs = 0, feederCandidates = 0,
    };
    OpexRoadFeederCandidates(catalog, lines, freshFeeders, feederStats, abandonedPairs);
    if (("road" in projects) && ("stats" in projects.road)) {
      projects.road.stats.feederHubs = feederStats.feederHubs;
      projects.road.stats.feederCandidates = feederStats.feederCandidates;
    }
    foreach (cand in freshFeeders) {
      local p = OpexProjectFromCandidate(cand, tensionCtx);
      if (p != null) {
        if (PORTFOLIO_V2) {
          OpexProjectRememberAll(newWinners, p, stats);
        } else {
          OpexProjectRemember(newWinners, p, stats);
        }
      }
    }
  }

  /* 3. Injection des projets de croissance de flotte (refleet) frais */
  if (FLEET_PORTFOLIO && fleetPlan != null) {
    foreach (entry in fleetPlan) {
      local p = OpexProjectFromFleet(entry, tensionCtx);
      if (p != null) {
        if (PORTFOLIO_V2) {
          OpexProjectRememberAll(newWinners, p, stats);
        } else {
          OpexProjectRemember(newWinners, p, stats);
        }
      }
    }
  }

  /* 4. Injection des projets aeriens frais (notamment les lignes hub ouvertes par un nouvel aeroport) */
  if (AIR_PORTFOLIO && ((catalog.airCombos != null && catalog.airCombos.len() > 0) || catalog.airport != null)) {
    local freshAirPlans = [];
    OpexAirPlans(catalog, lines, 0, freshAirPlans, abandonedPairs);
    local airOpsPerPlan = (freshAirPlans.len() > 0) ? (PROJECT_AIR_TRANSACTION_OPS / freshAirPlans.len()) : PROJECT_AIR_TRANSACTION_OPS;
    foreach (plan in freshAirPlans) {
      local p = OpexProjectFromAir(catalog, plan, airOpsPerPlan, tensionCtx);
      if (p != null) {
        if (PORTFOLIO_V2) {
          OpexProjectRememberAll(newWinners, p, stats);
        } else {
          OpexProjectRemember(newWinners, p, stats);
        }
      }
    }
  }

  /* 5. Avancer le plafond glissant AVANT de filtrer le vivier : un budget qui
   * remonte doit rendre ses projets accessibles dans cette meme reelection. */
  local capitalCeiling = capitalBudget;
  if ("capitalBudgetHistory" in projects && typeof(projects.capitalBudgetHistory) == "array") {
    projects.capitalBudgetHistory.append(capitalBudget);
    if (CAPITAL_CEILING_CYCLES > 0) {
      while (projects.capitalBudgetHistory.len() > CAPITAL_CEILING_CYCLES) {
        projects.capitalBudgetHistory.remove(0);
      }
    }
    local maxVal = 0;
    foreach (val in projects.capitalBudgetHistory) {
      if (val > maxVal) maxVal = val;
    }
    projects.capitalBudgetPeak = maxVal;
    capitalCeiling = maxVal;
  } else if ("capitalBudgetPeak" in projects) {
    capitalCeiling = projects.capitalBudgetPeak;
  }

  /* 6. Selection et resolution du sac a dos sur le capital restant */
  local funded = null;
  local byBudget = [];
  if (PORTFOLIO_V2) {
    local alternatives = [];
    foreach (key, list in newWinners) {
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
    local scoreField = (TENSION_SCORING || SHADOW_PRICING) ? "tensionScore" : "budgetScore";
    byBudget = OpexBuildMultimodalBudgetPool(newWinners, stats, capitalCeiling, scoreField, PROJECT_POOL_K);
    local knapsack = OpexKnapsackSolve(byBudget, capitalBudget, ROAD_MAX_NEW_LINES_PER_YEAR, PROJECT_TOP_K);
    funded = knapsack.projects;
    stats.knapsackNodes = knapsack.nodes;
    stats.knapsackExact = knapsack.exact;
    stats.budgetConsidered = byBudget.len();
    stats.budgetSelected = funded.len();
    stats.budgetRejected = byBudget.len() - funded.len();
  }

  /* 5. Cloture des statistiques et du capital restant */
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

  local byOpcodes = funded;
  if (!PORTFOLIO_V2 && !TENSION_SCORING && !SHADOW_PRICING) {
    byOpcodes = [];
    foreach (project in funded) {
      OpexProjectInsert(byOpcodes, project, "opcodeScore", PROJECT_TOP_K);
    }
  }

  if (DECISION_LOG) {
    local vivierPool = null;
    if (PORTFOLIO_V2) {
      vivierPool = [];
      foreach (key, list in newWinners) {
        foreach (project in list) vivierPool.push(project);
      }
    } else {
      vivierPool = byBudget;
    }
    OpexLogVivier("incremental", vivierPool, stats, capitalBudget, remaining);
  }

  AILog.Info("[PORTFOLIO_CACHE] incremental: candidates=" + stats.modeCandidates + " od=" + stats.odProjects + " selected=" + stats.budgetSelected + " remaining=" + remaining);

  projects.all = stats.odProjects;
  projects.best = byOpcodes;
  projects.stats = stats;
  projects.capitalBudget = capitalBudget;
  projects.capitalRemaining = remaining;
  projects.candidateGroups = newWinners;
  projects.budgetCandidates = byBudget;
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

function OpexBuildProjects(catalog, budget, lines, priorCapitalPeak = 0, priorCapitalHistory = null, fleetPlan = null, abandonedPairs = null)
{
  local rail = OpexBuildCandidates(catalog, budget, lines, abandonedPairs);
  local road = ROAD_BUILD_ENABLED
      ? OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs) : OpexProjectEmptyRoad();

  local capitalBudget = OpexAvailableCapital();

  /* C28 (docs/taches.md C28) : Remplacement du cliquet sans decroissance par un maximum glissant
   * sur les N derniers cycles.
   * L'admission au vivier engage une place pour tout un cycle, elle s'evalue donc sur le meilleur
   * capital mobilisable recent, et non sur la tresorerie du moment qui suit un achat (creux de cycle).
   * Mais sous le cliquet infini historique (CAPITAL_CEILING_CYCLES = 0), une compagnie qui
   * s'appauvrit garde un plafond fige (mesure a 295 000 £) et continue d'admettre des projets
   * inaccessibles au vivier, ce qui evince les projets abordables.
   * Sous CAPITAL_CEILING_CYCLES > 0, on retient le maximum sur les N derniers cycles (defaut 24, ~2 ans). */
  local history = [];
  if (typeof(priorCapitalPeak) == "array") {
    priorCapitalHistory = priorCapitalPeak;
    priorCapitalPeak = 0;
  }
  if (priorCapitalHistory != null && typeof(priorCapitalHistory) == "array") {
    foreach (val in priorCapitalHistory) history.append(val);
  } else if (priorCapitalPeak > 0) {
    history.append(priorCapitalPeak);
  }
  history.append(capitalBudget);

  local capitalCeiling;
  if (CAPITAL_CEILING_CYCLES > 0) {
    while (history.len() > CAPITAL_CEILING_CYCLES) {
      history.remove(0);
    }
    local maxVal = 0;
    foreach (val in history) {
      if (val > maxVal) maxVal = val;
    }
    capitalCeiling = maxVal;
  } else {
    capitalCeiling = (priorCapitalPeak > capitalBudget) ? priorCapitalPeak : capitalBudget;
  }

  local airPlan = null;
  local airPlans = [];
  local airOps = 0;
  if ((catalog.airCombos != null && catalog.airCombos.len() > 0) || catalog.airport != null) {
    budget.begin();
    airPlan = OpexAirPlans(catalog, lines, 0, airPlans, abandonedPairs);
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
    knapsackNodes = 0, knapsackExact = true, poolInfundable = 0,
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
  local tensionCtx = null;
  if (TENSION_SCORING || SHADOW_PRICING) {
    local projMap = { rail = rail, road = road, airPlans = airPlans, waterPlans = waterPlans, fleetPlan = fleetPlan };
    tensionCtx = OpexTensionContext(projMap);
    if (SHADOW_PRICING) {
      local allProjects = [];
      if (rail != null && ("candidates" in rail)) {
        foreach (candidate in rail.candidates) {
          local p = OpexProjectFromCandidate(candidate, null);
          if (p != null) allProjects.append(p);
        }
      }
      if (road != null && ("candidates" in road)) {
        foreach (candidate in road.candidates) {
          local p = OpexProjectFromCandidate(candidate, null);
          if (p != null) allProjects.append(p);
        }
      }
      if (airPlans != null) {
        foreach (plan in airPlans) {
          local p = OpexProjectFromAir(catalog, plan, airOpsPerPlan, null);
          if (p != null) allProjects.append(p);
        }
      }
      if (waterPlans != null) {
        foreach (plan in waterPlans) {
          local p = OpexProjectFromWater(catalog, plan, waterOpsPerPlan, null);
          if (p != null) allProjects.append(p);
        }
      }
      if (fleetPlan != null) {
        foreach (entry in fleetPlan) {
          local p = OpexProjectFromFleet(entry, null);
          if (p != null) allProjects.append(p);
        }
      }
      local shadowPrices = OpexTensionComputeShadowPrices(tensionCtx, allProjects, capitalBudget);
      tensionCtx.shadowPrices <- shadowPrices;
      tensionCtx.regime <- "shadow";
      tensionCtx.dominant <- "shadow";
      if (DECISION_LOG) {
        OpexDecide("SHADOW_PRICES", "lambda_argent=" + shadowPrices.argent
                   + " lambda_ops=" + shadowPrices.opcodes
                   + " lambda_foncier=" + shadowPrices.foncier
                   + " lambda_slots_road=" + shadowPrices.slots.road
                   + " lambda_slots_air=" + shadowPrices.slots.air
                   + " lambda_slots_rail=" + shadowPrices.slots.rail
                   + " b_argent=" + shadowPrices.budgetArgent
                   + " b_ops=" + shadowPrices.budgetOps
                   + " b_foncier=" + shadowPrices.budgetFoncier);
      }
      foreach (p in allProjects) {
        local score = OpexReducedCostScore(p, shadowPrices);
        p.tensionScore = score;
        p.shadowScore <- score;
        p.tensionRegime = "shadow";
        if (PORTFOLIO_V2) {
          OpexProjectRememberAll(winners, p, stats);
        } else {
          OpexProjectRemember(winners, p, stats);
        }
      }
    } else {
      /* C35.2 : le score continu lit le vecteur propre a chaque projet. Ne pas
       * choisir ici une formule unique a partir d'un argmax macro : foncier >= 1
       * rendait cette bascule presque toujours egale au profit brut et perdait
       * l'information des trois autres tensions. */
      tensionCtx.regime <- "continuous";
      tensionCtx.dominant <- "project";
      if (DECISION_LOG) {
        OpexDecide("TENSION_REGIME", "regime=continuous dominant=project");
      }
    }
  }

  if (!SHADOW_PRICING) {
    if (PORTFOLIO_V2) {
      foreach (candidate in rail.candidates) {
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
        OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate, tensionCtx), stats);
      }
      foreach (candidate in road.candidates) {
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
        OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate, tensionCtx), stats);
      }
      foreach (plan in airPlans) {
        OpexProjectRememberAll(winners, OpexProjectFromAir(catalog, plan, airOpsPerPlan, tensionCtx), stats);
      }
      foreach (plan in waterPlans) {
        OpexProjectRememberAll(winners, OpexProjectFromWater(catalog, plan, waterOpsPerPlan, tensionCtx), stats);
      }
      if (fleetPlan != null) {
        foreach (entry in fleetPlan) {
          OpexProjectRememberAll(winners, OpexProjectFromFleet(entry, tensionCtx), stats);
        }
      }
    } else {
      foreach (candidate in rail.candidates) {
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
        OpexProjectRemember(winners, OpexProjectFromCandidate(candidate, tensionCtx), stats);
      }
      foreach (candidate in road.candidates) {
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
        OpexProjectRemember(winners, OpexProjectFromCandidate(candidate, tensionCtx), stats);
      }
      foreach (plan in airPlans) {
        OpexProjectRemember(winners, OpexProjectFromAir(catalog, plan, airOpsPerPlan, tensionCtx), stats);
      }
      foreach (plan in waterPlans) {
        OpexProjectRemember(winners, OpexProjectFromWater(catalog, plan, waterOpsPerPlan, tensionCtx), stats);
      }
      if (fleetPlan != null) {
        foreach (entry in fleetPlan) {
          OpexProjectRemember(winners, OpexProjectFromFleet(entry, tensionCtx), stats);
        }
      }
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
    local scoreField = (TENSION_SCORING || SHADOW_PRICING) ? "tensionScore" : "budgetScore";
    byBudget = OpexBuildMultimodalBudgetPool(winners, stats, capitalCeiling, scoreField, PROJECT_POOL_K);
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
   * profit qu'on vient d'etablir. Sous TENSION_SCORING, la tension opcode est deja integree au
   * denominateur de Liebig : on conserve egalement l'ordre de tensionScore. */
  local byOpcodes = funded;
  if (!PORTFOLIO_V2 && !TENSION_SCORING && !SHADOW_PRICING) {
    byOpcodes = [];
    foreach (project in funded) {
      OpexProjectInsert(byOpcodes, project, "opcodeScore", PROJECT_TOP_K);
    }
  }

  if (DECISION_LOG) {
    local vivierPool = null;
    if (PORTFOLIO_V2) {
      vivierPool = [];
      foreach (key, list in winners) {
        foreach (project in list) vivierPool.push(project);
      }
    } else {
      vivierPool = byBudget;
    }
    OpexLogVivier("build", vivierPool, stats, capitalBudget, remaining);
  }

  /* Le retour historique reste litteralement intact sous 0. Le bras 1 seul conserve le vivier :
   * cela evite meme de changer la forme de this._projects dans le controle. */
  if (PORTFOLIO_FRESH_BUDGET || PORTFOLIO_CACHE) {
    return {
      all = stats.odProjects, best = byOpcodes, stats = stats,
      capitalBudget = capitalBudget, generationCapitalBudget = capitalBudget,
      capitalBudgetPeak = capitalCeiling, capitalBudgetHistory = history,
      capitalRemaining = remaining, candidateGroups = winners, budgetCandidates = byBudget,
      rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
      airPlans = airPlans, waterPlans = waterPlans,
      airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
    };
  }
  return {
    all = stats.odProjects, best = byOpcodes, stats = stats,
    capitalBudget = capitalBudget, capitalBudgetPeak = capitalCeiling,
    capitalBudgetHistory = history,
    capitalRemaining = remaining,
    rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
    airPlans = airPlans, waterPlans = waterPlans,
    airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
  };
}
