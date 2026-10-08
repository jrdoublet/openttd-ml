/* Extrait de projects.nut (R14) : Construction des projets depuis candidats, flotte, AIR et eau. Requis depuis projects.nut. */

/* C80 tâche 5 : nombre de véhicules/convois introduits ou ajoutés par un projet. */
function OpexProjectVehicleCount(project)
{
  if (project == null) return 1;
  local mode = ("mode" in project) ? project.mode : "unknown";
  if (mode == "fleet") {
    if (("payload" in project) && project.payload != null && ("want" in project.payload)) {
      local w = project.payload.want;
      return w > 0 ? w : 1;
    }
    return 1;
  }
  if (mode == "road") {
    if (("selectedRoadVehicles" in project) && project.selectedRoadVehicles > 0) {
      return project.selectedRoadVehicles;
    }
    if (("payload" in project) && project.payload != null && ("trains" in project.payload) && project.payload.trains > 0) {
      return project.payload.trains;
    }
    return 1;
  }
  if (mode == "rail") {
    if (("payload" in project) && project.payload != null && ("trains" in project.payload) && project.payload.trains > 0) {
      return project.payload.trains;
    }
    return 1;
  }
  /* Air : le plan porte le nombre d'avions achetes (plan.planes, economie de la route). */
  if (mode == "air") {
    if (("payload" in project) && project.payload != null && ("planes" in project.payload) && project.payload.planes > 0) {
      return project.payload.planes;
    }
    return 1;
  }
  return 1;
}

/* C80 tâche 5 : filtre de valeur des projets marginaux.
 * Écarte un chantier marginal dont le profit par véhicule calibré est strictement
 * inférieur à la moyenne réalisée par véhicule des lignes existantes du même mode.
 * Sans lignes matures ou si le profit réalisé du mode est non positif, ne filtre rien. */
function OpexC80ProjectBelowMarginalFloor(lines, project)
{
  if (project == null || lines == null) return false;
  local mode = ("mode" in project) ? project.mode : "unknown";
  local targetMode = mode;
  if (targetMode == "fleet") targetMode = "air";

  local totalProfit = 0;
  local totalVehs = 0;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != targetMode) continue;
    if (!("vehCount" in line) || line.vehCount <= 0) continue;
    if (!("lastProfit" in line)) continue;
    totalProfit += line.lastProfit;
    totalVehs += line.vehCount;
  }
  if (totalVehs <= 0 || totalProfit <= 0) return false;

  local projVehs = OpexProjectVehicleCount(project);
  if (projVehs <= 0) projVehs = 1;

  local calibProfit = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(project) : (("profitAnnual" in project) ? project.profitAnnual : 0);
  if (calibProfit <= 0) return true;

  local projProfitPerVeh = calibProfit.tofloat() / projVehs.tofloat();
  local modeProfitPerVeh = totalProfit.tofloat() / totalVehs.tofloat();

  return projProfitPerVeh < modeProfitPerVeh;
}

function OpexProjectFromCandidate(candidate)
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
  /* Garde de cadence : l'ancien bonus fret (freightBonus > 100) n'existe plus depuis FLAT_BONUS,
   * mais ce test reste lu a chaque projet (re-tarification C76 comprise). */
  if (!CLEAN_DENSITY_SCORE) {}
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
    economicsDate = AIDate.GetCurrentDate(),
  };
  /* B3 diagnostic-only : distinguer la demande brute, la borne appliquee au classement et la
   * cible retenue. Aucun de ces champs nouveaux n'entre dans un score ou un tri. */
  if (mode == "road") {
    project.vehiclesForVolume <- ("vehiclesForVolume" in candidate) ? candidate.vehiclesForVolume : candidate.trains;
    project.roadVehicleCap <- ("roadVehicleCap" in candidate) ? candidate.roadVehicleCap : candidate.trains;
    project.selectedRoadVehicles <- candidate.trains;
  }
  /* B6 : conserver les composantes de pre-classement comme mesures seulement. */
  project.turnoverBonus <- ("turnoverBonus" in candidate) ? candidate.turnoverBonus : 100;
  project.generationRatio <- ("ratio" in candidate) ? candidate.ratio : 0;
  if (("isChain" in candidate) && candidate.isChain) {
    project.isChain <- true;
    if (V88_CHAIN_STEP1_FINANCE && ("inputCandidate" in candidate) && candidate.inputCandidate != null) {
      project.budgetCapital = candidate.inputCandidate.capital;
    }
  }
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
 * Profit marginal : sous C84 et tant que la ligne est sous sa cible, utiliser la DIFFERENCE
 * have -> have+want calculee a blanc par _resizeAirFleets avec OpexAirEconomics(fixedPlanes).
 * Le profit realise / avion et le repli predRevenue - predRunning restent le contrat historique
 * hors de ce chemin. */
function OpexProjectFromFleet(entry)
{
  if (entry == null || entry.want <= 0 || entry.planePrice <= 0) return null;
  local line = entry.line;
  local have = ("vehCount" in line && line.vehCount > 0) ? line.vehCount
             : (("vehicles" in line) ? line.vehicles.len() : 0);
  if (have < 1) return null;
  if (C121_AIR_ECONOMICS && C121_AIR_TARGET_LIMIT
      && (!("targetAirPlanes" in line) || have + entry.want > line.targetAirPlanes)) return null;

  local profit = 0;
  local revenue = 0;
  local profitIsObserved = false;
  local usedTargetMarginal = false;
  local c121BelowTarget = C121_AIR_ECONOMICS && ("targetAirPlanes" in line)
      && line.targetAirPlanes > have;
  local c84BelowTarget = C84_AIR_TARGET_FLEET && ("targetAirPlanes" in line)
      && line.targetAirPlanes > have;
  if (c121BelowTarget) {
    /* C121 : score MARGINAL, jamais profit moyen / avion. Le premier palier
     * vient du modele exact post-build. Tant qu'aucune marge reelle n'a ete
     * observee, recalibrer ce cold-start avec le facteur de realisation courant
     * de l'arm. Apres la premiere observation complete, c121Marginal* ne
     * contient plus que du reel. */
    if (!("c121MarginalProfit" in line) || !("c121MarginalRevenue" in line)) return null;
    local perPlaneProfit = line.c121MarginalProfit;
    local perPlaneRevenue = line.c121MarginalRevenue;
    local samples = ("c121MarginalSamples" in line) ? line.c121MarginalSamples : 0;
    /* Une moyenne historique positive ne peut pas financer un nouveau palier
     * si le dernier renfort mesure a detruit du profit. Le cold-start (0 sample)
     * conserve exactement le comportement C121 existant. */
    if (samples > 0 && ("c121LastMarginalProfit" in line)
        && line.c121LastMarginalProfit <= 0) return null;
    if (samples <= 0 && ("c121Arm" in line) && (line.c121Arm in C121_AIR_REALIZATION_FACTOR)) {
      local builtFactor = ("c121RealizationPmAtBuild" in line)
          ? line.c121RealizationPmAtBuild.tofloat() / 1000.0
          : (("c121RealizationFactor" in line) ? line.c121RealizationFactor : 1.0);
      local learnedFactor = C121_AIR_REALIZATION_FACTOR[line.c121Arm];
      if (builtFactor > 0.0 && learnedFactor >= 0.0 && learnedFactor != builtFactor) {
        local marginalCost = perPlaneRevenue - perPlaneProfit;
        perPlaneRevenue = (perPlaneRevenue.tofloat() * learnedFactor / builtFactor).tointeger();
        perPlaneProfit = perPlaneRevenue - marginalCost;
      }
    }
    profit = perPlaneProfit * entry.want;
    revenue = perPlaneRevenue * entry.want;
    if (profit <= 0 || revenue <= 0) return null;
    usedTargetMarginal = true;
  } else if (c84BelowTarget) {
    /* Une sauvegarde/prototype C84 plus ancien peut porter targetAirPlanes sans airMonthlyPax,
     * donc _resizeAirFleets ne peut pas produire le marginal exact. Ne jamais retomber alors sur
     * la prediction lineaire 1-avion qui a motive ce correctif. */
    if (!("c84MarginalProfit" in entry)) return null;
    profit = entry.c84MarginalProfit;
    if (profit <= 0) return null;
    if ("c84MarginalRevenue" in entry) revenue = entry.c84MarginalRevenue;
    if (revenue <= 0) revenue = profit;
    usedTargetMarginal = true;
  }

  if (!usedTargetMarginal) {
    local perPlaneProfit = 0;
    if (("lastProfit" in line) && line.lastProfit > 0) {
      perPlaneProfit = line.lastProfit / have;
      profitIsObserved = true;
    } else if (("predRevenue" in line) && line.predRevenue > 0) {
      local running = ("predRunning" in line) ? line.predRunning : 0;
      local planes = ("predTrains" in line && line.predTrains > 0) ? line.predTrains : have;
      perPlaneProfit = (line.predRevenue - running) / planes;
    }
    if (perPlaneProfit <= 0) return null;
    profit = perPlaneProfit * entry.want;
    revenue = profit;
    if (("predRevenue" in line) && line.predRevenue > 0) {
      local planes = ("predTrains" in line && line.predTrains > 0) ? line.predTrains : have;
      revenue = (line.predRevenue / planes) * entry.want;
    }
  }

  local capital = entry.planePrice * entry.want;
  /* Un achat d'avion ne coute aucune planification : ni pathfinder, ni sondage de site. Seules
   * les commandes transactionnelles restent, d'ou un opcodeScore structurellement tres favorable
   * -- c'est exact, et c'est precisement ce que l'arbitrage doit pouvoir voir. */
  local expectedOps = PROJECT_ROAD_TRANSACTION_OPS;
  local project = {
    mode = "fleet", kind = "fleet", cargo = line.cargo,
    src = line.stationA, dst = ("stationB" in line) ? line.stationB : line.stationA,
    payload = entry, distance = 0, capital = capital,
    /* Meme tampon de 1000 que le dernier garde d'OpexAirAddPlane, une seule
     * fois par lot, en plus de la reserve deja soustraite par le portefeuille. */
    budgetCapital = capital + 1000, profitAnnual = profit, revenueAnnual = revenue,
    /* Provenance transitoire du profit ; C84 reste modelise, C121 conserve
     * son exemption de realisation propre dans OpexC70Profit/OpexC82Profit. */
    profitIsObserved = profitIsObserved,
    roi = capital > 0 ? (profit * 1000) / capital : 0,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(revenue, capital + 1000),
    opcodeScore = OpexProjectScore(revenue, expectedOps),
    planningOpcodes = 0,
    /* B6/06.11 diagnostic-only: horodate l'economie mise en cache. */
    economicsDate = AIDate.GetCurrentDate(),
  };
  return project;
}

function OpexC111ProjectFromAir(catalog, plan, planningOps)
{
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  local decisionEconomics = (("decisionEconomics" in plan) && plan.decisionEconomics != null)
      ? plan.decisionEconomics : economics;
  if (economics.revenueAnnual <= 0 || economics.capital <= 0 ||
      (!C113_AIR_C100_FULL_DECISION_SHADOW && economics.profitAnnual <= 0)) return null;
  if (decisionEconomics.profitAnnual <= 0 || decisionEconomics.revenueAnnual <= 0 ||
      decisionEconomics.capital <= 0) return null;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local margin = OpexAirRequiredMargin(newAirports, plan);
  local budgetCapital = economics.capital + margin;
  if (("immobilise" in economics) && economics.immobilise > 0) {
    budgetCapital += economics.immobilise;
  }
  local decisionBudgetCapital = decisionEconomics.capital + margin;
  if (("immobilise" in decisionEconomics) && decisionEconomics.immobilise > 0) {
    decisionBudgetCapital += decisionEconomics.immobilise;
  }
  /* C121 peut isoler strictement l'economie du projet execute maintenant : une
   * nouvelle ligne construit un seul avion. Les avions suivants sont deja des
   * projets flotte marginaux concurrents, donc crediter ici la croisiere future
   * peut compter deux fois la meme valeur. Le mode historique reste le defaut. */
  local useInitialProjectEconomics = C121_AIR_ECONOMICS && C121_AIR_INITIAL_PROJECT_ECONOMICS;
  local projectEconomics = useInitialProjectEconomics ? economics : decisionEconomics;
  local projectDecisionBudgetCapital = useInitialProjectEconomics ? budgetCapital : decisionBudgetCapital;
  /* La decouverte a deja ete payee pendant l'etape projets. La contrainte d'execution ne porte
   * que sur les opcodes encore necessaires pour construire le projet. */
  local expectedOps = PROJECT_AIR_TRANSACTION_OPS;
  local project = {
    mode = "air", kind = "pax", cargo = catalog.paxCargo,
    src = plan.siteA.town.tile, dst = plan.siteB.town.tile, payload = plan,
    distance = plan.distance, capital = economics.capital,
    budgetCapital = budgetCapital, decisionFinanceCapital = projectDecisionBudgetCapital,
    profitAnnual = projectEconomics.profitAnnual,
    revenueAnnual = projectEconomics.revenueAnnual, roi = projectEconomics.roi,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(projectEconomics.revenueAnnual, projectDecisionBudgetCapital),
    opcodeScore = OpexProjectScore(projectEconomics.revenueAnnual, expectedOps),
    planningOpcodes = planningOps,
    economicsDate = AIDate.GetCurrentDate(),
  };
  return project;
}

/* Marge de caisse AIR selon le nombre d'aeroports neufs. Remplace l'ancienne
 * branche morte airMarginPadding (toujours false) dupliquee en cinq endroits. */
function OpexAirRequiredMargin(newAirports, plan = null)
{
  /* V126 : avec le devis actif, la marge suit le risque residuel (plancher 2000
   * plus un pourcentage du cout du site) a condition que le plan porte son devis
   * C121 ; sinon, ou au defaut, la marge historique par aeroport neuf. */
  if (AIR_SITE_COST_QUOTE && C121_AIR_ECONOMICS && plan != null
      && ("c121EngineStatic" in plan) && plan.c121EngineStatic != null) {
    local st = plan.c121EngineStatic;
    if (("v126Quoted" in st) && st.v126Quoted == true) {
      return 2000 + (st.v126SiteCost * AIR_SITE_COST_MARGIN_PCT) / 100;
    }
  }
  return (newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000);
}

function OpexProjectFromAir(catalog, plan, planningOps)
{
  if (C111_AIR_C100_DECISION_SHADOW && plan != null
      && ("decisionEconomics" in plan) && plan.decisionEconomics != null) {
    return OpexC111ProjectFromAir(catalog, plan, planningOps);
  }
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  local decisionEconomics = (C121_AIR_ECONOMICS && ("decisionEconomics" in plan)
      && plan.decisionEconomics != null) ? plan.decisionEconomics : economics;
  if (economics.profitAnnual <= 0 || economics.revenueAnnual <= 0 ||
      economics.capital <= 0) return null;
  if (decisionEconomics.profitAnnual <= 0 || decisionEconomics.revenueAnnual <= 0 ||
      decisionEconomics.capital <= 0) return null;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local margin = OpexAirRequiredMargin(newAirports, plan);
  local budgetCapital = economics.capital + margin;
  if (("immobilise" in economics) && economics.immobilise > 0) {
    budgetCapital += economics.immobilise;
  }
  local decisionBudgetCapital = decisionEconomics.capital + margin;
  if (("immobilise" in decisionEconomics) && decisionEconomics.immobilise > 0) {
    decisionBudgetCapital += decisionEconomics.immobilise;
  }
  /* Option experimentale : classer le projet sur ce qui est construit maintenant
   * (N=1). Les renforcements futurs restent des projets flotte independants. */
  local useInitialProjectEconomics = C121_AIR_ECONOMICS && C121_AIR_INITIAL_PROJECT_ECONOMICS;
  local projectEconomics = useInitialProjectEconomics ? economics : decisionEconomics;
  local projectDecisionBudgetCapital = useInitialProjectEconomics ? budgetCapital : decisionBudgetCapital;
  /* La decouverte a deja ete payee pendant l'etape projets. La contrainte d'execution ne porte
   * que sur les opcodes encore necessaires pour construire le projet. */
  local expectedOps = PROJECT_AIR_TRANSACTION_OPS;
  local project = {
    mode = "air", kind = "pax", cargo = catalog.paxCargo,
    src = plan.siteA.town.tile, dst = plan.siteB.town.tile, payload = plan,
    distance = plan.distance, capital = economics.capital,
    budgetCapital = budgetCapital, decisionFinanceCapital = projectDecisionBudgetCapital,
    profitAnnual = projectEconomics.profitAnnual,
    revenueAnnual = projectEconomics.revenueAnnual, roi = projectEconomics.roi,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(projectEconomics.revenueAnnual, projectDecisionBudgetCapital),
    opcodeScore = OpexProjectScore(projectEconomics.revenueAnnual, expectedOps),
    planningOpcodes = planningOps,
    economicsDate = AIDate.GetCurrentDate(),
  };
  if (C118_AIR_TERRITORIAL_EXPANSION) {
    project.c118TownIds <- OpexC118PlanCoverageTowns(plan, catalog.paxCargo);
    local c68 = (("c118C68Economics") in plan) ? plan.c118C68Economics : economics;
    project.c118C68Profit <- c68 != null ? c68.profitAnnual : economics.profitAnnual;
    project.c118C68Roi <- c68 != null ? c68.roi : economics.roi;
  }
  return project;
}

function OpexProjectFromWater(catalog, plan, planningOps)
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
    /* L'eau est recyclee par OpexIncrementalUpdateProjects : dater son economie
     * permet de mesurer 06.11 au meme titre que rail/route. */
    economicsDate = AIDate.GetCurrentDate(),
  };
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

/* FLEET_AMORT_SHADOW_BEGIN
 * Diagnostic seulement, sans appel au defaut ni nouveau symbole global de reglage.
 * L'integrateur appelle ce helper APRES R1, sur le projet ajuste de CETTE election.
 * Aucun cache sur project/payload : 4 -> 1 recalcule prix * 1 / duree, et non
 * (amortissement du lot de 4) / 4. Les divisions entieres restent celles du modele AIR.
 * C84/C121 sont hors perimetre, y compris leurs marges : ne pas les recalculer ici.
 * Sous V92, plane doit etre la vue modele du moteur ajoute, pas un moteur rechoisi.
 * L'identite, le denominateur, les priorites et l'emission appartiennent au selecteur.
 * Retour null = inactif/hors perimetre/incomplet, jamais amortissement mesure a zero.
 */
function OpexFleetAmortShadow(project, enabled = false, plane = null)
{
  if (!enabled) return null;
  if (C84_AIR_TARGET_FLEET || C121_AIR_ECONOMICS) return null;
  if (project == null || !("mode" in project) || project.mode != "fleet"
      || !("payload" in project) || project.payload == null
      || !("profitAnnual" in project) || project.profitAnnual <= 0
      || !("profitIsObserved" in project) || typeof project.profitIsObserved != "bool") return null;
  local entry = project.payload;
  if (!("want" in entry) || typeof entry.want != "integer" || entry.want <= 0
      || !("planePrice" in entry) || typeof entry.planePrice != "integer" || entry.planePrice <= 0
      || !("line" in entry) || entry.line == null
      || !("mode" in entry.line) || entry.line.mode != "air") return null;
  if (V92_AIR_SERVICE_CHOICE && plane == null) return null;
  local lifeYears = 20;
  if (V92_AIR_SERVICE_CHOICE && ("ageYears" in plane) && plane.ageYears > 1) lifeYears = plane.ageYears;
  local addedAmortAnnual = entry.want * entry.planePrice / lifeYears;
  local netProfitAnnual = project.profitAnnual - addedAmortAnnual;
  /* Pas de plancher a zero sur le net. Le score commun pourra etre nul.
   * R2 : le clone conserve profitIsObserved ; ne jamais recalibrer une observation.
   * Aucun champ decisionnel de l'original ni de son payload partage n'est ecrit. */
  local diagnostic = clone project;
  diagnostic.profitAnnual = netProfitAnnual;
  local calibratedProfitAnnual = C70_PROFIT_CALIBRATED
      ? OpexCalibratedProfit(diagnostic) : netProfitAnnual;
  return {
    quantity = entry.want, planePrice = entry.planePrice, lifeYears = lifeYears,
    profitSource = project.profitIsObserved ? "observed" : "predictive_fallback",
    profitIsObserved = project.profitIsObserved,
    grossProfitAnnual = project.profitAnnual, addedAmortAnnual = addedAmortAnnual,
    netProfitAnnual = netProfitAnnual, calibratedProfitAnnual = calibratedProfitAnnual,
  };
}
/* FLEET_AMORT_SHADOW_END */
