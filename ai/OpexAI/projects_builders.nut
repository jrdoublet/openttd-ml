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

  local calibProfit = OpexCalibratedProfit(project);
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
     * mais le pathfinder réel est plafonné à HARD_ITERATION_CAP (5 000). Ne pas borner ici
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
    expectedOps = PROJECT_ROAD_TRANSACTION_OPS;
  } else {
    return null;
  }
  local budgetCapital = candidate.capital + margin;
  if (("immobilise" in candidate) && candidate.immobilise > 0) {
    budgetCapital += candidate.immobilise;
  }
  local scoreRevenue = candidate.revenueAnnual;
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
 * Sous la cible C121, le score est la marge par avion deja publiee sur la ligne.
 * Sinon le profit realise / avion, puis le repli predRevenue - predRunning. */
function OpexProjectFromFleet(entry)
{
  if (entry == null || entry.want <= 0 || entry.planePrice <= 0) return null;
  local line = entry.line;
  local have = ("vehCount" in line && line.vehCount > 0) ? line.vehCount
             : (("vehicles" in line) ? line.vehicles.len() : 0);
  if (have < 1) return null;

  local profit = 0;
  local revenue = 0;
  local profitIsObserved = false;
  local usedTargetMarginal = false;
  local c121BelowTarget = ("targetAirPlanes" in line)
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

  /* V161 : la marge C121 (ligne seule) et le profit moyen ignorent ce que l'avion retire
   * aux voisines du meme aeroport : plafonner par l'a priori net des voisines. Une valeur
   * restee "model" perd l'exemption C70 des renforts (v161Calibrate). */
  local v161Source = null;
  local v161Model = 0;
  {
    v161Model = profit / entry.want;
    local marginalCost = revenue - profit;
    local v161 = OpexV161PerPlaneProfit(line, entry, v161Model);
    if (v161 == null) return null;
    profit = v161.profit * entry.want;
    revenue = profit + (marginalCost > 0 ? marginalCost : 0);
    v161Source = v161.source;
    profitIsObserved = v161Source != "model";
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
    /* Provenance transitoire du profit. C121 conserve son exemption de
     * realisation propre dans OpexC70Profit. */
    profitIsObserved = profitIsObserved,
    roi = capital > 0 ? (profit * 1000) / capital : 0,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(revenue, capital + 1000),
    opcodeScore = OpexProjectScore(revenue, expectedOps),
    planningOpcodes = 0,
    /* B6/06.11 diagnostic-only: horodate l'economie mise en cache. */
    economicsDate = AIDate.GetCurrentDate(),
  };
  if (v161Source != null) {
    project.v161Source <- v161Source;
    project.v161ModelPerPlane <- v161Model;
    project.v161Calibrate <- true;
  }
  OpexAirCalibrateInvestment(project);
  return project;
}

/* Marge de caisse AIR selon le nombre d'aeroports neufs. `plan` reste dans la
 * signature : les appelants le passent, il n'est plus lu. */
function OpexAirRequiredMargin(newAirports, plan = null)
{
  return (newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000);
}

function OpexProjectFromAir(catalog, plan, planningOps)
{
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  local decisionEconomics = (("decisionEconomics" in plan)
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
  /* La decouverte a deja ete payee pendant l'etape projets. La contrainte d'execution ne porte
   * que sur les opcodes encore necessaires pour construire le projet. */
  local expectedOps = PROJECT_AIR_TRANSACTION_OPS;
  local project = {
    mode = "air", kind = "pax", cargo = catalog.paxCargo,
    src = plan.siteA.town.tile, dst = plan.siteB.town.tile, payload = plan,
    distance = plan.distance, capital = economics.capital,
    budgetCapital = budgetCapital, decisionFinanceCapital = decisionBudgetCapital,
    decisionConstructionCapital = decisionEconomics.capital,
    profitAnnual = decisionEconomics.profitAnnual,
    revenueAnnual = decisionEconomics.revenueAnnual, roi = decisionEconomics.roi,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(decisionEconomics.revenueAnnual, decisionBudgetCapital),
    opcodeScore = OpexProjectScore(decisionEconomics.revenueAnnual, expectedOps),
    planningOpcodes = planningOps,
    economicsDate = AIDate.GetCurrentDate(),
  };
  OpexAirCalibrateInvestment(project);
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
