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

/* Cascade pax par distance decroissante. Le fret accompagne la premiere passe. */
const OPEX_STAGE_AIR_ONLY = 0;
const OPEX_STAGE_AIR_RAIL = 1;
const OPEX_STAGE_RAIL_ONLY = 2;
const OPEX_STAGE_ROUTE_ONLY = 3;
const OPEX_STAGE_COMPLETE = 4;
/* C43/E3 (docs/taches.md) : sature a 77,4%/70,1% des appels de selection (VIVIER, 5x6, 2026-09-08)
 * -- mord fort. Rendu reglable pour le banc factoriel 32 contre 64, jamais retouche depuis 2026-09-02
 * avant cette mesure. */
PROJECT_TOP_K <- 64;
/* Propose par l'utilisateur le 2026-09-08 : caler PROJECT_TOP_K sur villes+industries de la carte
 * plutot que sur une constante fixe. Defaut 0 : aucun changement de comportement. */
PROJECT_TOP_K_DYNAMIC <- false;

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
 * Un prefixe distinct evite d'evincer ou d'entrer en collision avec une liaison directe entre les
 * memes villes, permettant la coexistence dans candidateGroups. */
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
      && ("isSubsidy" in project.payload) && project.payload.isSubsidy) {
    return "subsidy|" + project.payload.subsidyId;
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

/* P1 : cout a comparer a la tresorerie mobilisable. `budgetCapital` reste le
 * cout economique utilise par les scores historiques ; il ne faut pas y
 * injecter un multiplicateur global. Repli temporaire par mode, mesure au
 * sondage AIAccounting-isole (jamais un devis physique) : rail 1,7x
 * (docs/opexai_prix_rail_terrain.md), route 1,21x (docs/taches.md, mesure du
 * 2026-09-08 sur road_cost_probe, 5 graines x 6 ans, 4 812 tentatives). P1.1
 * doit remplacer le rail par un devis physique avant l'election ; la route
 * n'a pas d'equivalent. Si le trace a deja fourni un devis reel, le candidat
 * porte `capitalIsActual` et ce montant remplace le facteur. Les marges et le
 * capital immobilise ne sont pas des travaux de voie : ils restent inchanges. */
function OpexProjectFinanceCapital(project)
{
  if (project == null || !("budgetCapital" in project)) return 0;
  local financeCapital = project.budgetCapital;
  if (!CAPITAL_CALIBRATION || !("mode" in project)) return financeCapital;

  local biasPct = 0;
  if (project.mode == "rail") biasPct = 170;
  else if (project.mode == "road") biasPct = 121;
  else return financeCapital;

  local capital = ("capital" in project) ? project.capital : 0;
  local modelCapital = capital;
  if (capital <= 0) return financeCapital;
  local capitalIsActual = ("capitalIsActual" in project) && project.capitalIsActual;
  if (!capitalIsActual && ("payload" in project) && project.payload != null
      && ("capitalIsActual" in project.payload)) {
    capitalIsActual = project.payload.capitalIsActual;
    if (capitalIsActual && ("capital" in project.payload)
        && project.payload.capital > 0) {
      capital = project.payload.capital;
    }
  }
  local nonConstructionCapital = financeCapital - modelCapital;
  if (nonConstructionCapital < 0) nonConstructionCapital = 0;
  if (capitalIsActual) return capital + nonConstructionCapital;

  return ((capital * biasPct) / 100) + nonConstructionCapital;
}

/* P1.1 : le ×1,7 n'est qu'un repli. Pour les quelques meilleurs rails du
 * préfiltre, on peut payer un A* borné et le même devis AITestMode que le
 * constructeur AVANT l'élection. Le plan n'est volontairement pas conservé :
 * il peut devenir périmé entre le rafraîchissement et le chantier. */
function OpexPrequoteRailCandidates(catalog, budget, rail)
{
  local result = { attempted = 0, quoted = 0, failed = 0, skippedJoin = 0, opcodes = 0 };
  if (!RAIL_PREQUOTE || rail == null || !("best" in rail) || rail.best == null) return result;

  foreach (candidate in rail.best) {
    if (result.attempted >= RAIL_PREQUOTE_MAX_CANDIDATES) break;
    /* Le rattachement à une gare existante dépend de l'état vivant de
     * OpexAI::_tooClose. Le devis sans ce join serait faux : garder ×1,7. */
    if (("placeJoin" in candidate) && candidate.placeJoin != null) {
      result.skippedJoin++;
      continue;
    }
    result.attempted++;
    if (RAIL_TERRAIN_PROBE && DECISION_LOG) {
      budget.begin();
      local scan = OpexRailTerrainScanProbe(candidate.src, candidate.dst);
      local scanOpcodes = budget.end("p1_2_terrain_scan");
      OpexDecide("P1_2_TERRAIN", "src=" + candidate.src + " dst=" + candidate.dst
                 + " distance=" + candidate.distance + " tiles=" + scan.tilesScanned
                 + " complex_tiles=" + scan.complexTiles + " complex_segments="
                 + scan.complexSegments + " water_tiles=" + scan.waterTiles
                 + " slope_tiles=" + scan.slopeTiles + " ops=" + scanOpcodes);
    }
    budget.begin();
    local plan = OpexPlanRailRoute(catalog, budget, candidate, MIN_RATIO, null,
                                   RAIL_PREQUOTE_HARD_CAP);
    result.opcodes += budget.end("p1_1_prequote_plan");
    if (!plan.ok) {
      result.failed++;
      continue;
    }

    budget.begin();
    local actualCapital = OpexQuoteRailCapital(catalog, candidate, plan, null);
    result.opcodes += budget.end("p1_1_prequote_devis");
    if (actualCapital <= 0) {
      result.failed++;
      continue;
    }
    OpexApplyRailActualCapital(candidate, actualCapital);
    candidate.quotedCapital <- actualCapital;
    candidate.quotedAtDate <- AIDate.GetCurrentDate();
    if (RAIL_PREQUOTE_KEEP_PLAN) candidate.quotedPlan <- plan;
    result.quoted++;
    if (DECISION_LOG) {
      OpexDecide("P1_1_QUOTE", "src=" + candidate.src + " dst=" + candidate.dst
                 + " model=" + plan.capital + " quoted=" + actualCapital
                 + " ops=" + result.opcodes);
    }
  }
  if (DECISION_LOG && result.attempted > 0) {
    OpexDecide("P1_1_QUOTE_SUMMARY", "attempted=" + result.attempted
               + " quoted=" + result.quoted + " failed=" + result.failed
               + " join_skipped=" + result.skippedJoin + " ops=" + result.opcodes);
  }
  return result;
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
   * results/bench_isolation_3y_20seeds.json). Le tri au seul RATIO profit/capital a ete mesure isole :
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
    if (OpexProjectFinanceCapital(project) > capitalBudget) continue;
    if (project.profitAnnual > bestProfit) bestProfit = project.profitAnnual;
  }
  local floorProfit = 0;
  if (PORTFOLIO_FLOOR_PCT > 0 && bestProfit > 0) {
    floorProfit = bestProfit * PORTFOLIO_FLOOR_PCT / 100;
  }

  local affordable = [];
  local scoreKey = (TENSION_SCORING || SHADOW_PRICING) ? "tensionScore" : "fundScore";
  foreach (project in alternatives) {
    if (OpexProjectFinanceCapital(project) > capitalBudget) continue;
    if (project.profitAnnual < floorProfit) continue;
    if (!TENSION_SCORING && !SHADOW_PRICING) {
      project.fundScore <- OpexProjectScore(project.profitAnnual, OpexProjectFinanceCapital(project));
    }
    OpexProjectInsert(affordable, project, scoreKey, limit);
  }
  /* Filet de securite : si le plancher a tout ecarte -- il ne le peut pas puisque le meilleur
   * projet l'atteint par construction, mais un profitAnnual nul ou negatif rendrait bestProfit nul
   * et le plancher inoperant -- on retombe sur l'ensemble finançable brut plutot que de ne rien
   * batir du tout. */
  if (affordable.len() == 0 && floorProfit > 0) {
    foreach (project in alternatives) {
      if (OpexProjectFinanceCapital(project) > capitalBudget) continue;
      if (!TENSION_SCORING && !SHADOW_PRICING) {
        project.fundScore <- OpexProjectScore(project.profitAnnual, OpexProjectFinanceCapital(project));
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


function OpexLogVivier(path, candidates, stats, capitalBudget, capitalRemaining)
{
  if (!DECISION_LOG) return;
  if (DECISION_LOG) {
    OpexDecide("VIVIER", "path=" + path + " considered=" + stats.budgetConsidered
               + " selected=" + stats.budgetSelected + " rejected=" + stats.budgetRejected
               + " infundable=" + stats.poolInfundable
               + " budget=" + capitalBudget + " remaining=" + capitalRemaining
               + " sel_ops=" + (("selectionOpcodes" in stats) ? stats.selectionOpcodes : -1));
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
 * candidateGroups porte le vivier ; cette fonction se contente de reaplatir ses alternatives et
 * de retester le capital. Aucune planification rail, recherche de site aerien ou generation de
 * route ne repasse ici. Les statistiques sont remplacees ensemble car IG| et IB| doivent decrire
 * la meme solution que best, y compris lorsque la selection n'a pas prouve son optimum. */
function OpexReselectProjects(projects, capitalBudget)
{
  local funded = null;
  local considered = 0;
  local opsMark = OpexOpsMeasureBegin();
  local alternatives = [];
  foreach (key, list in projects.candidateGroups) {
    foreach (project in list) alternatives.push(project);
  }
  funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);
  considered = alternatives.len();
  projects.stats.knapsackNodes = 0;
  projects.stats.knapsackExact = true;
  projects.stats.selectionOpcodes <- OpexOpsMeasureEnd(opsMark);

  projects.stats.budgetConsidered = considered;
  projects.stats.budgetSelected = funded.len();
  projects.stats.budgetRejected = considered - funded.len();

  local selectedRev = 0;
  local selectedCap = 0;
  foreach (project in funded) {
    selectedRev += project.revenueAnnual;
    selectedCap += OpexProjectFinanceCapital(project);
  }
  projects.stats.selectedRevenue = selectedRev;
  projects.stats.selectedCapital = selectedCap;

  projects.capitalBudget = capitalBudget;
  projects.capitalRemaining = capitalBudget - selectedCap;
  if (projects.capitalRemaining < 0) projects.capitalRemaining = 0;

  projects.best = funded;

  if (DECISION_LOG) {
    local vivierPool = [];
    if (("candidateGroups" in projects) && projects.candidateGroups != null) {
      foreach (key, list in projects.candidateGroups) {
        foreach (project in list) vivierPool.push(project);
      }
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
        local siteAKey = OpexAirSiteAbandonKey(plan.siteA, plan.airport.type);
        local siteBKey = OpexAirSiteAbandonKey(plan.siteB, plan.airport.type);
        if ((aKey1 in abandonedPairs) || (aKey2 in abandonedPairs)
            || (AIR_ABANDON_SITE && ((siteAKey in abandonedPairs) || (siteBKey in abandonedPairs)))) return false;
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
    local isSubsidy = (("payload" in p) && p.payload != null &&
                       ("isSubsidy" in p.payload) && p.payload.isSubsidy);
    if (isSubsidy) {
      local subId = p.payload.subsidyId;
      if (!AISubsidy.IsValidSubsidy(subId) || AISubsidy.IsAwarded(subId)) return false;
      local today = AIDate.GetCurrentDate();
      local oneWay = ("oneWayDays" in p.payload) ? p.payload.oneWayDays : -1;
      local chantier = ("chantierDays" in p.payload) ? p.payload.chantierDays : OpexSubsidyChantierDays(oneWay);
      if (AISubsidy.GetExpireDate(subId) - today < chantier) return false;
      return true;
    }
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
      if (p.kind == "pax") {
        local srcServed = OpexOriginServed(lines, p.src, true);
        local dstServed = OpexOriginServed(lines, p.dst, true);
        local isOriginBlocked = srcServed || dstServed;

        if (C55_PAX_TRACE_PROBE) {
          OpexC55PaxTraceObserveRevalidated(isOriginBlocked);
        }

        if (C55_ROAD_PAX_ORIGIN_RELAX || C55_ROAD_ORIGIN_RELAX) {
          if (OpexRoadPairServed(lines, p.src, p.dst)) return false;
          if (OpexTownRoadLineCount(lines, p.src) >= 4) return false;
          if (OpexTownRoadLineCount(lines, p.dst) >= 4) return false;
          if (isOriginBlocked) {
            if (!("_c55_pax_spared" in p) || !p._c55_pax_spared) {
              p._c55_pax_spared <- true;
              if (p.payload != null) p.payload._c55_pax_spared <- true;
              if (C55_PAX_TRACE_PROBE) {
                OpexC55PaxTraceObserveSpared();
              }
            }
          }
        } else {
          if (C55_ORIGIN_RELAX_PROBE) {
            OpexC55OriginRelaxObserve("pax", lines, p.src, p.dst, srcServed, dstServed);
          }
          if (isOriginBlocked) return false;
          if (OpexRoadPairServed(lines, p.src, p.dst)) return false;
        }
      } else {
        /* Fret routier */
        if (C55_FREIGHT_ORIGIN_RELAX || C55_ROAD_ORIGIN_RELAX) {
          local srcServed = OpexOriginServed(lines, p.src, true);
          local dstServed = OpexOriginServed(lines, p.dst, true);
          if (srcServed && dstServed) return false;
          /* Une seule paire est revalidee : une boucle directe evite de construire un index. */
          if (OpexRoadFreightBusy(lines, p.cargo, p.src) ||
              OpexRoadFreightBusy(lines, p.cargo, p.dst)) return false;
        } else if (C55_ORIGIN_RELAX_PROBE) {
          local srcServed = OpexOriginServed(lines, p.src, true);
          local dstServed = OpexOriginServed(lines, p.dst, true);
          OpexC55OriginRelaxObserve("freight", lines, p.src, p.dst, srcServed, dstServed);
          if (srcServed || dstServed) return false;
        } else {
          if (OpexOriginServed(lines, p.src, true)) return false;
          if (OpexOriginServed(lines, p.dst, true)) return false;
        }
      }
      local towns = OpexGetCandidateTownEndpoints(p);
      if (C60_TOWN_RATING_PROBE) {
        if (towns.srcTown >= 0) OpexC60ObserveTownRating("road", "incremental_valid", towns.srcTown);
        if (towns.dstTown >= 0) OpexC60ObserveTownRating("road", "incremental_valid", towns.dstTown);
      }
      if (C60_TOWN_RATING_FILTER) {
        if ((towns.srcTown >= 0 && !OpexTownRatingAllowStation(towns.srcTown)) ||
            (towns.dstTown >= 0 && !OpexTownRatingAllowStation(towns.dstTown))) return false;
      }
    }
    return true;
  }

  /* 3. Mode rail : les deux extremites servies excluent la ligne */
  if (mode == "rail") {
    local towns = OpexGetCandidateTownEndpoints(p);
    if (C60_TOWN_RATING_PROBE) {
      if (towns.srcTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.srcTown);
      if (towns.dstTown >= 0) OpexC60ObserveTownRating("rail", "incremental_valid", towns.dstTown);
    }
    if (C60_TOWN_RATING_FILTER) {
      if ((towns.srcTown >= 0 && !OpexTownRatingAllowStation(towns.srcTown)) ||
          (towns.dstTown >= 0 && !OpexTownRatingAllowStation(towns.dstTown))) return false;
    }
    if (OpexOriginServed(lines, p.src, false) && OpexOriginServed(lines, p.dst, false)) {
      return false;
    }
    return true;
  }

  /* 4. Mode aerien : validite du plan de lot et constructibilite des sites */
  if (mode == "air") {
    local plan = p.payload;
    if (plan == null) return false;
    if (C60_TOWN_RATING_PROBE) {
      if (("siteA" in plan) && ("town" in plan.siteA)) OpexC60ObserveTownRating("air", "incremental_valid", plan.siteA.town.id);
      if ("siteB" in plan && ("town" in plan.siteB)) OpexC60ObserveTownRating("air", "incremental_valid", plan.siteB.town.id);
    }
    if (C60_TOWN_RATING_FILTER) {
      if ((("siteA" in plan) && ("town" in plan.siteA) && OpexTownRatingHopeless(plan.siteA.town.id)) ||
          (("siteB" in plan) && ("town" in plan.siteB) && OpexTownRatingHopeless(plan.siteB.town.id))) {
        return false;
      }
    }
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
  if (("payload" in p) && p.payload != null
      && ("isSubsidy" in p.payload) && p.payload.isSubsidy) {
    return "subsidy|" + p.payload.subsidyId;
  }
  local src = ("src" in p) ? p.src : -1;
  local dst = ("dst" in p) ? p.dst : -1;
  local cargo = ("cargo" in p) ? p.cargo : -1;
  local kind = ("kind" in p) ? p.kind : "";
  return mode + "|" + src + "|" + dst + "|" + cargo + "|" + kind;
}

/* Retire du vivier incremental les projets deja essayes dans le batch courant, puis rejoue la
 * seule contrainte de capital. */
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
  return OpexReselectProjects(projects, capitalBudget);
}

/* C36.1 : Caching incremental du vivier post-chantier.
 * Au lieu de reconstruire tout le portefeuille ex nihilo apres chaque ligne achevee (15 jours
 * d'attente sur A* et scan aerien), filtre les candidats existants en memoire, injecte les
 * nouveaux feeders / opportunites de flotte, et réélit le portefeuille sur le capital restant.
 * Execution : < 1 tick (< 500 opcodes, 0 jour). */
function OpexIncrementalUpdateProjects(projects, catalog, budget, lines, capitalBudget, fleetPlan = null, abandonedPairs = null)
{
  local c48TotalMark = null;
  local c48TotalDate = 0;
  local c48Lines = 0;
  if (C48_INCREMENTAL_PROFILE) {
    c48TotalDate = AIDate.GetCurrentDate();
    c48TotalMark = OpexOpsMeasureBegin();
    c48Lines = lines.len();
  }
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
    local c48Mark = null;
    local c48Date = 0;
    if (C48_INCREMENTAL_PROFILE) {
      c48Date = AIDate.GetCurrentDate();
      c48Mark = OpexOpsMeasureBegin();
    }
    tensionCtx = OpexTensionContext(projects);
    if (C48_INCREMENTAL_PROFILE) {
      local c48Days = AIDate.GetCurrentDate() - c48Date;
      OpexC48IncrementalRecord("tension_ctx", OpexOpsMeasureEnd(c48Mark), c48Days,
          0, 0, 0, 0, 0, 0, 0, 0, 0);
    }
  }

  local newWinners = {};

  /* 1. Filtrer les candidats existants du vivier */
  if (("candidateGroups" in projects) && projects.candidateGroups != null) {
    local c48Mark = null;
    local c48Date = 0;
    local c48Groups = 0;
    local c48Scanned = 0;
    local c48Retained = 0;
    if (C48_INCREMENTAL_PROFILE) {
      c48Date = AIDate.GetCurrentDate();
      c48Mark = OpexOpsMeasureBegin();
    }
    foreach (key, entry in projects.candidateGroups) {
      if (C48_INCREMENTAL_PROFILE) c48Groups++;
      local list = (typeof entry == "array") ? entry : [entry];
      foreach (p in list) {
        if (C48_INCREMENTAL_PROFILE) c48Scanned++;
        if (p == null) continue;
        /* La flotte et les feeders sont regeneres frais ci-dessous */
        if (p.mode == "fleet") continue;
        if (("payload" in p) && p.payload != null &&
            ("isFeeder" in p.payload) && p.payload.isFeeder) continue;
        if (!OpexIncrementalCandidateStillValid(p, lines, abandonedPairs)) continue;
        OpexProjectRememberAll(newWinners, p, stats);
        if (C48_INCREMENTAL_PROFILE) c48Retained++;
      }
    }
    if (C48_INCREMENTAL_PROFILE) {
      local c48Days = AIDate.GetCurrentDate() - c48Date;
      OpexC48IncrementalRecord("groups_replay", OpexOpsMeasureEnd(c48Mark), c48Days,
          0, c48Groups, c48Scanned, c48Retained, 0, 0, 0, 0, 0);
    }
  }

  /* 2. Injection des rabattements (feeders) frais vers les hubs */
  if (FEEDER_PORTFOLIO && ("roadType" in catalog) && catalog.roadType >= 0) {
    local c48Mark = null;
    local c48Date = 0;
    if (C48_INCREMENTAL_PROFILE) {
      c48Date = AIDate.GetCurrentDate();
      c48Mark = OpexOpsMeasureBegin();
    }
    local freshFeeders = [];
    local feederStats = {
      pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
      economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
      feederHubs = 0, feederCandidates = 0,
      roadDistanceShort = 0, roadDistanceLong = 0,
    };
    local feederRefreshMark = C41_ROAD_FEEDER_PROFILE ? OpexOpsMeasureBegin() : null;
    OpexRoadFeederCandidates(catalog, lines, freshFeeders, feederStats, abandonedPairs);
    if (feederRefreshMark != null) {
      OpexC39Log("C41_ROAD_FEEDER_REFRESH_PROFILE", "ops=" + OpexOpsMeasureEnd(feederRefreshMark)
                 + " candidates=" + freshFeeders.len());
    }
    if (("road" in projects) && ("stats" in projects.road)) {
      projects.road.stats.feederHubs = feederStats.feederHubs;
      projects.road.stats.feederCandidates = feederStats.feederCandidates;
    }
    foreach (cand in freshFeeders) {
      local p = OpexProjectFromCandidate(cand, tensionCtx);
      if (p != null) {
        OpexProjectRememberAll(newWinners, p, stats);
      }
    }
    if (C48_INCREMENTAL_PROFILE) {
      local c48Days = AIDate.GetCurrentDate() - c48Date;
      OpexC48IncrementalRecord("feeders", OpexOpsMeasureEnd(c48Mark), c48Days,
          0, 0, 0, 0, freshFeeders.len(), 0, 0, 0, 0);
    }
  }

  /* 3. Injection des projets de croissance de flotte (refleet) frais */
  if (FLEET_PORTFOLIO && fleetPlan != null) {
    local c48Mark = null;
    local c48Date = 0;
    if (C48_INCREMENTAL_PROFILE) {
      c48Date = AIDate.GetCurrentDate();
      c48Mark = OpexOpsMeasureBegin();
    }
    foreach (entry in fleetPlan) {
      local p = OpexProjectFromFleet(entry, tensionCtx);
      if (p != null) {
        OpexProjectRememberAll(newWinners, p, stats);
      }
    }
    if (C48_INCREMENTAL_PROFILE) {
      local c48Days = AIDate.GetCurrentDate() - c48Date;
      OpexC48IncrementalRecord("fleet", OpexOpsMeasureEnd(c48Mark), c48Days,
          0, 0, 0, 0, 0, fleetPlan.len(), 0, 0, 0);
    }
  }

  /* 4. Injection des projets aeriens frais (notamment les lignes hub ouvertes par un nouvel aeroport) */
  if (AIR_PORTFOLIO && ((catalog.airCombos != null && catalog.airCombos.len() > 0) || catalog.airport != null)) {
    local c48Mark = null;
    local c48Date = 0;
    if (C48_INCREMENTAL_PROFILE) {
      c48Date = AIDate.GetCurrentDate();
      c48Mark = OpexOpsMeasureBegin();
    }
    local freshAirPlans = [];
    OpexAirPlans(catalog, lines, 0, freshAirPlans, abandonedPairs);
    local airOpsPerPlan = (freshAirPlans.len() > 0) ? (PROJECT_AIR_TRANSACTION_OPS / freshAirPlans.len()) : PROJECT_AIR_TRANSACTION_OPS;
    foreach (plan in freshAirPlans) {
      local p = OpexProjectFromAir(catalog, plan, airOpsPerPlan, tensionCtx);
      if (p != null) {
        OpexProjectRememberAll(newWinners, p, stats);
      }
    }
    if (C48_INCREMENTAL_PROFILE) {
      local c48Days = AIDate.GetCurrentDate() - c48Date;
      OpexC48IncrementalRecord("air", OpexOpsMeasureEnd(c48Mark), c48Days,
          0, 0, 0, 0, 0, 0, freshAirPlans.len(), 0, 0);
    }
  }

  /* 5. Selection du portefeuille sur le capital restant */
  local funded = null;
  local c48SelectionMark = null;
  local c48SelectionDate = 0;
  local c48Alternatives = 0;
  if (C48_INCREMENTAL_PROFILE) {
    c48SelectionDate = AIDate.GetCurrentDate();
    c48SelectionMark = OpexOpsMeasureBegin();
  }
  local opsMark = OpexOpsMeasureBegin();
  local alternatives = [];
  foreach (key, list in newWinners) {
    stats.odProjects++;
    foreach (project in list) alternatives.push(project);
  }
  funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);
  if (C48_INCREMENTAL_PROFILE) c48Alternatives = alternatives.len();
  stats.budgetConsidered = alternatives.len();
  stats.budgetSelected = funded.len();
  stats.budgetRejected = alternatives.len() - funded.len();
  stats.knapsackNodes = 0;
  stats.knapsackExact = true;
  stats.selectionOpcodes <- OpexOpsMeasureEnd(opsMark);
  if (C48_INCREMENTAL_PROFILE) {
    local c48Days = AIDate.GetCurrentDate() - c48SelectionDate;
    OpexC48IncrementalRecord("selection", OpexOpsMeasureEnd(c48SelectionMark), c48Days,
        0, 0, 0, 0, 0, 0, 0, c48Alternatives, funded.len());
  }

  /* 6. Cloture des statistiques et du capital restant */
  local selectedRev = 0;
  local selectedCap = 0;
  foreach (p in funded) {
    selectedRev += p.revenueAnnual;
    selectedCap += OpexProjectFinanceCapital(p);
  }
  stats.selectedRevenue = selectedRev;
  stats.selectedCapital = selectedCap;
  local remaining = capitalBudget - selectedCap;
  if (remaining < 0) remaining = 0;

  local byOpcodes = funded;

  if (DECISION_LOG) {
    local vivierPool = [];
    foreach (key, list in newWinners) {
      foreach (project in list) vivierPool.push(project);
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
  /* Les six mesures de phase sont imbriquees dans total (OpexOpsMeasureBegin/End ne partage
   * aucun etat) : total - somme(phases) est le reste de la fonction, PAS un double comptage. */
  if (C48_INCREMENTAL_PROFILE) {
    local c48Days = AIDate.GetCurrentDate() - c48TotalDate;
    OpexC48IncrementalRecord("total", OpexOpsMeasureEnd(c48TotalMark), c48Days,
        c48Lines, 0, 0, 0, 0, 0, 0, 0, 0);
  }
  return projects;
}

function OpexProjectEmptyRoad()
{
  return {
    all = 0, candidates = [], best = [],
    stats = { pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
              economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
              feederHubs = 0, feederCandidates = 0,
              roadDistanceShort = 0, roadDistanceLong = 0 },
    opcodes = 0,
  };
}

function OpexEmptyRailCandidates()
{
  return {
    all = 0, candidates = [], best = [], bands = [0, 0, 0, 0],
    stats = {
      townsServed = 0, townsUnserved = 0, industriesServed = 0, industriesUnserved = 0,
      pairsTotal = 0, pairsOriginServed = 0, pairsJoinImpossible = 0, pairsOneServed = 0,
      noMonthly = 0, unsitable = 0,
      distanceShort = 0, distanceLong = 0, economicsUnavailable = 0,
      profitNonPositive = 0, ratioTooLow = 0, accepted = 0, topKOmitted = 0,
    },
    opcodes = 0, profile = null,
  };
}

function OpexCloneCandidateGroups(source)
{
  local winners = {};
  if (source == null) return winners;
  foreach (key, list in source) {
    local copy = [];
    foreach (project in list) copy.append(project);
    winners.rawset(key, copy);
  }
  return winners;
}

/* Les etapes du bootstrap conservent les familles deja generees, mais une
 * construction peut avoir rendu une paire desservie entre deux etapes. Passer
 * les objets bruts par la meme validation que le cache incremental avant de les
 * reinjecter empeche le projet qui vient d'etre construit de revenir en tete. */
function OpexStagedCandidateStillValid(candidate, lines, abandonedPairs = null)
{
  if (candidate == null) return false;
  local project = OpexProjectFromCandidate(candidate, null);
  return project != null && OpexIncrementalCandidateStillValid(project, lines, abandonedPairs);
}

function OpexStagedAirPlanStillValid(catalog, plan, lines, abandonedPairs = null)
{
  if (plan == null) return false;
  local project = OpexProjectFromAir(catalog, plan, 0, null);
  return project != null && OpexIncrementalCandidateStillValid(project, lines, abandonedPairs);
}

function OpexStagedWaterPlanStillValid(catalog, plan, lines, abandonedPairs = null)
{
  if (plan == null) return false;
  local project = OpexProjectFromWater(catalog, plan, 0, null);
  return project != null && OpexIncrementalCandidateStillValid(project, lines, abandonedPairs);
}

function OpexMergeRailCandidateSet(base, extra)
{
  if (base == null) return extra;
  if (extra == null) return base;
  foreach (candidate in extra.candidates) base.candidates.append(candidate);
  base.all = base.candidates.len();
  base.best = OpexTopK(base.candidates, TOP_K);
  base.bands = OpexBands(base.candidates);
  base.opcodes += extra.opcodes;
  if (("stats" in base) && base.stats != null && ("stats" in extra) && extra.stats != null) {
    foreach (key, value in extra.stats) {
      local valueType = typeof value;
      if ((valueType == "integer" || valueType == "float") && (key in base.stats)) {
        base.stats[key] += value;
      }
    }
  }
  return base;
}

function OpexBuildProjects(catalog, budget, lines, fleetPlan = null, abandonedPairs = null, generationStage = null, priorProjects = null, freightCargo = null, freightCargoOrder = null, waterSiteCatalog = null, activeSubsidies = null)
{
  if (generationStage == null) generationStage = OPEX_STAGE_COMPLETE;
  local doFreight = (generationStage == OPEX_STAGE_AIR_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  local doPaxRail = (generationStage == OPEX_STAGE_AIR_RAIL || generationStage == OPEX_STAGE_RAIL_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  local doRoad = (generationStage == OPEX_STAGE_ROUTE_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  local doAir = (generationStage == OPEX_STAGE_AIR_ONLY || generationStage == OPEX_STAGE_AIR_RAIL || generationStage == OPEX_STAGE_COMPLETE);
  local doWater = (generationStage == OPEX_STAGE_ROUTE_ONLY || generationStage == OPEX_STAGE_COMPLETE);
  local paxBand = generationStage == OPEX_STAGE_AIR_RAIL ? PAX_BAND_AIR_RAIL
      : (generationStage == OPEX_STAGE_RAIL_ONLY ? PAX_BAND_RAIL_ONLY : PAX_BAND_ALL);
  local airBand = generationStage == OPEX_STAGE_AIR_ONLY ? PAX_BAND_AIR_ONLY
      : (generationStage == OPEX_STAGE_AIR_RAIL ? PAX_BAND_AIR_RAIL : PAX_BAND_ALL);
  if (DECISION_LOG) {
    OpexDecide("BOOTSTRAP_STAGE", "stage=" + generationStage
               + " freight=" + (doFreight ? 1 : 0) + " pax_rail=" + (doPaxRail ? 1 : 0)
               + " road=" + (doRoad ? 1 : 0) + " air=" + (doAir ? 1 : 0)
               + " freight_cargo=" + (freightCargo != null ? freightCargo : -1)
               + " freight_label=" + (freightCargo != null ? AICargo.GetCargoLabel(freightCargo) : "none")
               + " freight_price=" + (freightCargo != null ? AICargo.GetCargoIncome(freightCargo, 20, 0) : 0));
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_rail", "-");
  /* C41.22 : intervalles disjoints du chemin rail historique. Le pre-devis peut etre inactif
   * par reglage : publier alors son zero est justement necessaire pour ne pas attribuer son cout
   * hypothetique au comportement par defaut. */
  local railProfile = C41_RAIL_PORTFOLIO_PROFILE
      ? { generationOps = 0, generationCandidates = 0, topKCandidates = 0,
          prequoteOps = 0, prequoteAttempted = 0, prequoteQuoted = 0, prequoteFailed = 0,
          insertOps = 0, insertedProjects = 0 } : null;
  local railGenerationMark = railProfile != null ? OpexOpsMeasureBegin() : null;
  local railCandidateProfile = (C41_RAIL_CANDIDATE_PROFILE || C41_RAIL_PAX_PROFILE || C41_RAIL_PAX_CANDIDATE_PROFILE || C41_RAIL_PAX_ECONOMICS_PROFILE || C41_RAIL_PAX_SPEED_PROFILE || C41_RAIL_PAX_SPEED_DETAIL_PROFILE || C41_RAIL_PAX_CRUISE_PROFILE || C41_RAIL_FREIGHT_PROFILE || C41_RAIL_FREIGHT_CANDIDATE_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE || C41_RAIL_FREIGHT_CRUISE_PROFILE || C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE || C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE || C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE)
      ? { paxOps = 0, freightOps = 0, topKOps = 0,
          paxPreparationOps = 0, paxPairTotalOps = 0, paxCandidateOps = 0,
          paxPairsScanned = 0, paxCandidateCalls = 0,
          paxSitableOps = 0, paxSitableCalls = 0, paxEconomicsOps = 0, paxEconomicsCalls = 0,
          paxEconomicsSetupOps = 0, paxEconomicsLoopOps = 0, paxEconomicsLoopCalls = 0,
          paxEconomicsPostOps = 0, paxSpeedOps = 0, paxSpeedCalls = 0,
          paxCorrectedSpeedCalls = 0, paxCruiseOps = 0, paxAccelerationOps = 0,
          paxIntegrationOps = 0, paxSpeedKeys = {}, paxSpeedUniqueKeys = 0,
          paxSpeedCacheableHits = 0, paxCruiseKeys = {}, paxCruiseCalls = 0,
          paxCruiseUniqueKeys = 0, paxCruiseCacheableHits = 0,
          freightPreparationOps = 0, freightIndustryOps = 0, freightTownOps = 0, freightTownGuardsOps = 0, freightTownGuardsCalls = 0, freightTownServiceOps = 0, freightTownServiceCalls = 0,
          freightIndustryCandidateOps = 0, freightIndustryCandidateCalls = 0,
          freightTownCandidateOps = 0, freightTownCandidateCalls = 0,
          freightEconomicsOps = 0, freightEconomicsCalls = 0,
          /* C41.34 : les trois phases de OpexLineEconomics, mais uniquement pour fret.
           * Ne pas reutiliser les compteurs pax : le meme helper sert aux deux familles. */
          freightEconomicsSetupOps = 0, freightEconomicsSetupCalls = 0,
          freightEconomicsLoopOps = 0, freightEconomicsLoopCalls = 0,
          freightEconomicsPostOps = 0, freightEconomicsPostCalls = 0,
          freightEconomicsReferenceOps = 0, freightEconomicsReferenceCalls = 0,
          freightEconomicsConsistOps = 0, freightEconomicsConsistCalls = 0,
          freightEconomicsCapitalOps = 0, freightEconomicsCapitalCalls = 0,
          freightEconomicsConsistInitialSpeedOps = 0, freightEconomicsConsistInitialSpeedCalls = 0,
          freightEconomicsConsistCorrectedSpeedOps = 0, freightEconomicsConsistCorrectedSpeedCalls = 0,
          freightCruiseKeys = {}, freightCruiseCalls = 0, freightCruiseUniqueKeys = 0,
          freightCruiseCacheableHits = 0,
          freightAccelerationOps = 0, freightAccelerationCalls = 0,
          freightIntegrationOps = 0, freightIntegrationCalls = 0,
          freightSpeedKeys = {}, freightSpeedCalls = 0, freightSpeedUniqueKeys = 0,
          freightSpeedCacheableHits = 0 } : null;
  local railPaxProfile = C41_RAIL_PAX_PROFILE ? railCandidateProfile : null;
  local railPaxCandidateProfile = (C41_RAIL_PAX_CANDIDATE_PROFILE || C41_RAIL_PAX_ECONOMICS_PROFILE || C41_RAIL_PAX_SPEED_PROFILE || C41_RAIL_PAX_SPEED_DETAIL_PROFILE || C41_RAIL_PAX_CRUISE_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE)
      ? railCandidateProfile : null;
  /* C41.30/C41.38 : caches epuises apres cette generation ; aucun moteur/cargo/terrain d'une
   * passe suivante ne peut reutiliser une valeur ancienne. Les tables pax/fret sont separees :
   * l'AB fret ne change donc pas la cadence pax. */
  local railPaxCruiseCache = C41_RAIL_PAX_CRUISE_CACHE ? {} : null;
  local railFreightCruiseCache = C41_RAIL_FREIGHT_CRUISE_CACHE ? {} : null;
  local rail;
  if (doPaxRail || doFreight) {
    rail = OpexBuildCandidates(catalog, budget, lines, abandonedPairs, railCandidateProfile, railPaxProfile, railPaxCandidateProfile, railPaxCruiseCache, railFreightCruiseCache, doPaxRail, doFreight, paxBand, freightCargo);
    if (priorProjects != null && ("rail" in priorProjects)
        && priorProjects.rail != null && ("candidates" in priorProjects.rail)) {
      local merged = [];
      foreach (c in priorProjects.rail.candidates) {
        /* Une passe pax de repli a pu avoir lieu a l'etape 0. L'etape pax
         * normale vient de la regenerer avec l'etat courant : ne conserver
         * ici que le fret herite pour ne pas dupliquer chaque paire pax. */
        local replaced = generationStage == OPEX_STAGE_AIR_RAIL && c.kind == "pax";
        if (!replaced && OpexStagedCandidateStillValid(c, lines, abandonedPairs)) {
          merged.append(c);
        }
      }
      foreach (c in rail.candidates) merged.append(c);
      rail.candidates = merged;
      rail.best = OpexTopK(merged, TOP_K);
      rail.all = merged.len();
    }
  } else if (priorProjects != null && ("rail" in priorProjects) && priorProjects.rail != null) {
    rail = priorProjects.rail;
    local liveRail = [];
    foreach (c in rail.candidates) {
      if (OpexStagedCandidateStillValid(c, lines, abandonedPairs)) liveRail.append(c);
    }
    rail.candidates = liveRail;
    rail.best = OpexTopK(liveRail, TOP_K);
    rail.all = liveRail.len();
  } else {
    rail = OpexEmptyRailCandidates();
  }
  /* Un cargo actif peut encore ne produire aucun candidat admissible (aucun
   * puits, distance, economie ou site). Comme pour le repli pax air->air+rail,
   * essayer immediatement les cargos suivants par prix, sans regenerer le pax
   * ni l'air deja calcules. Le premier lot fret non vide devient le lot reel
   * de ce portefeuille. */
  if (doFreight && freightCargo != null && freightCargoOrder != null
      && freightCargoOrder.len() > 1) {
    local hasFreight = false;
    foreach (candidate in rail.candidates) {
      if (candidate.kind == "freight") { hasFreight = true; break; }
    }
    if (!hasFreight) {
      local start = -1;
      for (local i = 0; i < freightCargoOrder.len(); i++) {
        if (freightCargoOrder[i] == freightCargo) { start = i; break; }
      }
      local tried = 1;
      for (local offset = 1; offset < freightCargoOrder.len(); offset++) {
        local idx = start >= 0 ? (start + offset) % freightCargoOrder.len() : offset - 1;
        local nextCargo = freightCargoOrder[idx];
        local extraFreight = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
            railCandidateProfile, null, null, null, railFreightCruiseCache,
            false, true, PAX_BAND_ALL, nextCargo);
        tried++;
        if (extraFreight.candidates.len() == 0) continue;
        local previousCargo = freightCargo;
        rail = OpexMergeRailCandidateSet(rail, extraFreight);
        freightCargo = nextCargo;
        hasFreight = true;
        if (DECISION_LOG) {
          OpexDecide("FREIGHT_CARGO_FALLBACK", "from=" + previousCargo
                     + " to=" + freightCargo + " label=" + AICargo.GetCargoLabel(freightCargo)
                     + " tried=" + tried + " candidates=" + extraFreight.candidates.len());
        }
        break;
      }
      if (!hasFreight && DECISION_LOG) {
        OpexDecide("FREIGHT_CARGO_FALLBACK", "from=" + freightCargo
                   + " to=none tried=" + tried + " candidates=0");
      }
    }
  }
  if (railProfile != null) {
    railProfile.generationOps = OpexOpsMeasureEnd(railGenerationMark);
    railProfile.generationCandidates = rail.candidates.len();
    railProfile.topKCandidates = rail.best.len();
  }
  local railPrequoteMark = railProfile != null ? OpexOpsMeasureBegin() : null;
  local railPrequote = (doPaxRail || doFreight)
      ? OpexPrequoteRailCandidates(catalog, budget, rail)
      : { attempted = 0, quoted = 0, failed = 0, opcodes = 0, skippedJoin = 0 };
  if (railProfile != null) {
    railProfile.prequoteOps = OpexOpsMeasureEnd(railPrequoteMark);
    railProfile.prequoteAttempted = railPrequote.attempted;
    railProfile.prequoteQuoted = railPrequote.quoted;
    railProfile.prequoteFailed = railPrequote.failed;
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_rail", "-");
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_road", "-");
  /* C41.16/C41.17 : mesure seulement les etapes de generation route pendant la passe historique. */
  local roadProfile = (C41_ROAD_CANDIDATE_PROFILE || C41_ROAD_FREIGHT_PROFILE || C41_ROAD_FREIGHT_TOWN_PROFILE || C41_ROAD_FEEDER_PROFILE)
      ? { paxOps = 0, freightOps = 0, feederOps = 0, topKOps = 0,
          freightPreparationOps = 0, freightIndustryOps = 0, freightTownOps = 0,
          freightTownScanned = 0, freightTownAcceptanceHits = 0, freightTownAcceptanceMisses = 0,
          freightTownAcceptanceOps = 0, freightTownAcceptedPairs = 0, freightTownCandidateOps = 0 } : null;
  local road;
  if (doRoad && ROAD_BUILD_ENABLED) {
    road = OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs, roadProfile, freightCargo);
  } else if (priorProjects != null && ("road" in priorProjects) && priorProjects.road != null) {
    road = priorProjects.road;
    local liveRoad = [];
    foreach (c in road.candidates) {
      if (OpexStagedCandidateStillValid(c, lines, abandonedPairs)) liveRoad.append(c);
    }
    road.candidates = liveRoad;
    road.best = OpexTopK(liveRoad, ROAD_TOP_K);
    road.all = liveRoad.len();
  } else {
    road = OpexProjectEmptyRoad();
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_road", "-");

  local capitalBudget = OpexAvailableCapital();

  local airPlan = null;
  local airPlans = [];
  local airOps = 0;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_air", "-");
  if (doAir && ((catalog.airCombos != null && catalog.airCombos.len() > 0) || catalog.airport != null)) {
    budget.begin();
    airPlan = OpexAirPlans(catalog, lines, 0, airPlans, abandonedPairs, airBand);
    airOps = budget.end("project_air");
    if (generationStage == OPEX_STAGE_AIR_RAIL && priorProjects != null
        && ("airPlans" in priorProjects) && priorProjects.airPlans != null) {
      foreach (plan in priorProjects.airPlans) {
        if (OpexStagedAirPlanStillValid(catalog, plan, lines, abandonedPairs)) airPlans.append(plan);
      }
      if (airPlans.len() > 0) airPlan = airPlans[0];
    }
  } else if (!doAir && priorProjects != null) {
    airPlan = ("airPlan" in priorProjects) ? priorProjects.airPlan : null;
    if (("airPlans" in priorProjects) && priorProjects.airPlans != null) {
      foreach (plan in priorProjects.airPlans) {
        if (OpexStagedAirPlanStillValid(catalog, plan, lines, abandonedPairs)) airPlans.append(plan);
      }
    }
    airPlan = airPlans.len() > 0 ? airPlans[0] : null;
    airOps = ("airPlanningOpcodes" in priorProjects) ? priorProjects.airPlanningOpcodes : 0;
  }

  /* L'air reste le pax prioritaire de l'etape initiale. Une liste vide signifie
   * qu'aucun plan pax aerien n'a franchi ses filtres ; dans ce seul cas, ouvrir
   * le rail pax maintenant plutot que laisser un premier vivier 100 % fret. */
  if (generationStage == OPEX_STAGE_AIR_ONLY && airPlans.len() == 0) {
    budget.begin();
    airPlan = OpexAirPlans(catalog, lines, 0, airPlans, abandonedPairs, PAX_BAND_AIR_RAIL);
    airOps += budget.end("project_air_overlap_fallback");
    local paxFallback = OpexBuildCandidates(catalog, budget, lines, abandonedPairs,
        railCandidateProfile, railPaxProfile, railPaxCandidateProfile,
        railPaxCruiseCache, railFreightCruiseCache, true, false, PAX_BAND_AIR_RAIL);
    rail = OpexMergeRailCandidateSet(rail, paxFallback);
    local fallbackPrequote = OpexPrequoteRailCandidates(catalog, budget, paxFallback);
    railPrequote.attempted += fallbackPrequote.attempted;
    railPrequote.quoted += fallbackPrequote.quoted;
    railPrequote.failed += fallbackPrequote.failed;
    railPrequote.skippedJoin += fallbackPrequote.skippedJoin;
    railPrequote.opcodes += fallbackPrequote.opcodes;
    if (railProfile != null) {
      railProfile.generationCandidates = rail.candidates.len();
      railProfile.topKCandidates = rail.best.len();
      railProfile.prequoteAttempted = railPrequote.attempted;
      railProfile.prequoteQuoted = railPrequote.quoted;
      railProfile.prequoteFailed = railPrequote.failed;
    }
    if (DECISION_LOG) {
      OpexDecide("BOOTSTRAP_PAX_FALLBACK", "air=0 rail_pax=" + paxFallback.candidates.len());
    }
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_air", "-");

  local waterPlan = null;
  local waterPlans = [];
  local waterOps = 0;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_water", "-");
  if (doWater && catalog.ships.len() > 0 && catalog.paxCargo >= 0) {
    budget.begin();
    waterPlan = OpexWaterPlans(catalog, lines, waterPlans, null,
                               WATER_SITE_CATALOG ? waterSiteCatalog : null);
    waterOps = budget.end("project_water");
  } else if (!doWater && priorProjects != null) {
    waterPlan = ("waterPlan" in priorProjects) ? priorProjects.waterPlan : null;
    if (("waterPlans" in priorProjects) && priorProjects.waterPlans != null) {
      foreach (plan in priorProjects.waterPlans) {
        if (OpexStagedWaterPlanStillValid(catalog, plan, lines, abandonedPairs)) waterPlans.append(plan);
      }
    }
    waterPlan = waterPlans.len() > 0 ? waterPlans[0] : null;
    waterOps = ("waterPlanningOpcodes" in priorProjects) ? priorProjects.waterPlanningOpcodes : 0;
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_water", "-");

  local stats = {
    modeCandidates = 0, modeAlternatives = 0, modeReplaced = 0,
    odProjects = 0, budgetConsidered = 0, budgetSelected = 0,
    budgetRejected = 0, selectedRevenue = 0, selectedCapital = 0,
    knapsackNodes = 0, knapsackExact = true, poolInfundable = 0,
    railPrequoteAttempted = railPrequote.attempted, railPrequoteQuoted = railPrequote.quoted,
    railPrequoteFailed = railPrequote.failed, railPrequoteOpcodes = railPrequote.opcodes,
  };
  if (railProfile != null) stats.railProfile <- railProfile;
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

  local subCandidates = [];
  if (C42_SUBSIDIES && activeSubsidies != null) {
    subCandidates = OpexGenerateSubsidyCandidates(catalog, lines, activeSubsidies, stats, abandonedPairs);
  }

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "c56_stage_assembly", "-");
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
      foreach (candidate in subCandidates) {
        local p = OpexProjectFromCandidate(candidate, null);
        if (p != null) allProjects.append(p);
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
        OpexProjectRememberAll(winners, p, stats);
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
    local railInsertMark = railProfile != null ? OpexOpsMeasureBegin() : null;
    local railProjectsBefore = stats.modeCandidates;
    foreach (candidate in rail.candidates) {
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
      OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate, tensionCtx), stats);
    }
    if (railProfile != null) {
      railProfile.insertOps = OpexOpsMeasureEnd(railInsertMark);
      railProfile.insertedProjects = stats.modeCandidates - railProjectsBefore;
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
    foreach (candidate in subCandidates) {
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null && (OpexAbandonedPairKey(candidate) in abandonedPairs)) continue;
      OpexProjectRememberAll(winners, OpexProjectFromCandidate(candidate, tensionCtx), stats);
    }
  }

  local funded = null;
  local opsMark = OpexOpsMeasureBegin();
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
  stats.selectionOpcodes <- OpexOpsMeasureEnd(opsMark);

  local selectedRev = 0;
  local selectedCap = 0;
  foreach (p in funded) {
    selectedRev += p.revenueAnnual;
    selectedCap += OpexProjectFinanceCapital(p);
  }
  stats.selectedRevenue = selectedRev;
  stats.selectedCapital = selectedCap;
  local remaining = capitalBudget - selectedCap;
  if (remaining < 0) remaining = 0;

  local byOpcodes = funded;

  if (DECISION_LOG) {
    local vivierPool = [];
    foreach (key, list in winners) {
      foreach (project in list) vivierPool.push(project);
    }
    OpexLogVivier("build", vivierPool, stats, capitalBudget, remaining);
  }

  /* Le retour historique reste litteralement intact sous 0. Le bras 1 seul conserve le vivier :
   * cela evite meme de changer la forme de this._projects dans le controle. */
  if (PORTFOLIO_FRESH_BUDGET || PORTFOLIO_CACHE) {
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_assembly", "-");
    return {
      all = stats.odProjects, best = byOpcodes, stats = stats,
      capitalBudget = capitalBudget, generationCapitalBudget = capitalBudget,
      capitalRemaining = remaining, candidateGroups = winners,
      rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
      airPlans = airPlans, waterPlans = waterPlans,
      airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
      generationStage = generationStage,
      freightCargo = freightCargo,
    };
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "c56_stage_assembly", "-");
  return {
    all = stats.odProjects, best = byOpcodes, stats = stats,
    capitalBudget = capitalBudget,
    capitalRemaining = remaining,
    rail = rail, road = road, airPlan = airPlan, waterPlan = waterPlan,
    airPlans = airPlans, waterPlans = waterPlans,
    airPlanningOpcodes = airOps, waterPlanningOpcodes = waterOps,
    generationStage = generationStage,
    freightCargo = freightCargo,
  };
}
