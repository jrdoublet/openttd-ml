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

/* ESTIM-1 lot 3 : meme schema comptable pour les lignes neuves et les
 * operations marginales. L'economie de l'AIR C121 porte deja son propre k_R
 * sous bit 1, celle des autres modes est corrigee dans OpexEstimProfit. */
function OpexEstimAttachProjectComponents(project, revenue, running, amort)
{
  if (project == null || (ESTIM_UNIFIE & 4) == 0) return;
  local dR = revenue;
  if ((ESTIM_UNIFIE & 17) != 0 && project.mode != "air"
      && project.mode in ESTIM_K_R)
    dR = (revenue.tofloat() * (project.mode == "rail" && (ESTIM_UNIFIE & 16) != 0
        ? OpexEstimRailRevenueFactor(("distance" in project) ? project.distance : 0)
        : ((ESTIM_UNIFIE & 1) != 0 ? ESTIM_K_R[project.mode] : 1.0))).tointeger();
  project.deltaR <- dR;
  project.deltaE <- running;
  project.deltaA <- amort;
  project.deltaC <- project.capital;
  project.deltaP <- dR - running - amort;
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
  if ((ESTIM_UNIFIE & 2) != 0) budgetCapital = candidate.capital;
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
  OpexEstimAttachProjectComponents(project, candidate.revenueAnnual,
      candidate.runningAnnual, candidate.amortAnnual);
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
 * Le projet est toujours une transition n -> n+1 evaluee par V161 avant
 * publication (C121 avec cannibalisation ou modele physique sans voisines). */
function OpexProjectFromFleet(entry)
{
  if ((ESTIM_UNIFIE & 4) != 0 && OpexEstimFleetStepCurrent(entry))
    return OpexEstimProjectFromFleet(entry);
  if (entry == null || entry.want != 1 || entry.planePrice <= 0) return null;
  local line = entry.line;
  local have = ("vehCount" in line && line.vehCount > 0) ? line.vehCount
             : (("vehicles" in line) ? line.vehicles.len() : 0);
  if (have < 1 || !("v161BaseVehicles" in entry) || entry.v161BaseVehicles != have
      || !("v161Profit" in entry) || !("v161DeltaR" in entry)
      || !("v161DeltaE" in entry) || !("v161DeltaA" in entry)
      || !("v161Engine" in entry) || !("v161Source" in entry)
      || entry.v161Profit != entry.v161DeltaR - entry.v161DeltaE - entry.v161DeltaA
      || entry.v161Profit <= 0 || entry.v161DeltaR <= 0) return null;
  local profit = entry.v161Profit;
  local revenue = entry.v161DeltaR;

  /* P3 : OFF n'effectue aucune lecture de monde ni de sonde. Shadow journalise
   * le meme verdict que ON mais ne touche jamais les projets. Limiter aux
   * renforts 2->3+ ; C121 1->2, refleet et V252 restent prioritaires. */
  if (P3_AIR_FLEET_YIELD > 0 && have >= 2) {
    local p3 = OpexP3MatureEvidence(line, have, entry.planePrice);
    if (DECISION_LOG) {
      OpexDecide("P3_FLEET_YIELD", "stage=score mode=" + P3_AIR_FLEET_YIELD
          + " line=" + line.lineId + " have=" + have
          + " want=" + entry.want
          + " evidence=" + (p3 != null ? 1 : 0)
          + " veto=" + (p3 != null && p3.veto ? 1 : 0)
          + " v252_upgrade=" + (("p3EngineUpgrade" in entry) && entry.p3EngineUpgrade ? 1 : 0)
          + " trips=" + (p3 != null ? p3.trips : -1)
          + " seats=" + (p3 != null ? p3.seats : -1)
          + " pax=" + (p3 != null ? p3.pax : -1)
          + " margin=" + (p3 != null ? p3.lastMarginal : -1));
    }
    if (P3_AIR_FLEET_YIELD == 2 && p3 != null && p3.veto
        && !(("p3EngineUpgrade" in entry) && entry.p3EngineUpgrade)) return null;
  }

  local capital = entry.planePrice * entry.want;
  local budget = capital + ((ESTIM_UNIFIE & 2) != 0 ? 0 : 1000);
  /* Un achat d'avion ne coute aucune planification : ni pathfinder, ni sondage de site. Seules
   * les commandes transactionnelles restent, d'ou un opcodeScore structurellement tres favorable
   * -- c'est exact, et c'est precisement ce que l'arbitrage doit pouvoir voir. */
  local expectedOps = PROJECT_ROAD_TRANSACTION_OPS;
  local project = {
    mode = "fleet", kind = "fleet", cargo = line.cargo,
    src = line.stationA, dst = ("stationB" in line) ? line.stationB : line.stationA,
    payload = entry, distance = 0, capital = capital,
    /* Le budget peut inclure la marge historique de liquidite; sous
     * ESTIM bit 2, seule la depense physique est requise. */
    budgetCapital = budget, profitAnnual = profit, revenueAnnual = revenue,
    /* Provenance transitoire du profit. C121 conserve son exemption de
     * realisation propre dans OpexC70Profit. */
    profitIsObserved = false,
    roi = capital > 0 ? (profit * 1000) / capital : 0,
    expectedOpcodes = expectedOps,
    budgetScore = OpexProjectScore(revenue, budget),
    opcodeScore = OpexProjectScore(revenue, expectedOps),
    planningOpcodes = 0,
    /* B6/06.11 diagnostic-only: horodate l'economie mise en cache. */
    economicsDate = AIDate.GetCurrentDate(),
  };
  project.v161Source <- entry.v161Source;
  project.v161ModelPerPlane <- profit;
  project.v161NetMarginalModeled <- true;
  if ((ESTIM_UNIFIE & 4) != 0) {
    project.deltaR <- revenue;
    project.deltaE <- entry.v161DeltaE;
    project.deltaA <- entry.v161DeltaA;
    project.deltaC <- capital;
    project.deltaP <- profit;
  }
  return project;
}

/* ESTIM-1 lot 3 : le renfort garde la composante physique n -> n+1 de C121,
 * recompose sa recette au facteur commun, puis retire exploitation/amortissement.
 * Un palier devenu perime apres un achat ne peut pas etre rejoue sans nouveau
 * calcul C121 : on attend alors le prochain chantier physique. */
function OpexEstimFleetStepCurrent(entry)
{
  if (entry == null || entry.line == null) return false;
  local line = entry.line;
  local have = ("vehCount" in line) ? line.vehCount
      : (("vehicles" in line) && line.vehicles != null ? line.vehicles.len() : 0);
  return have > 0 && entry.want == 1 && ("v161BaseVehicles" in entry)
      && entry.v161BaseVehicles == have && ("v161Profit" in entry)
      && ("v161Source" in entry) && entry.v161Source == "c121"
      && ("estimMarginalRawRevenue" in line)
      && ("estimMarginalBaseVehicles" in line) && line.estimMarginalBaseVehicles == have;
}

function OpexEstimProjectFromFleet(entry)
{
  if (entry == null || entry.line == null || entry.want != 1 || entry.planePrice <= 0) return null;
  local line = entry.line;
  local have = ("vehCount" in line) ? line.vehCount
      : (("vehicles" in line) && line.vehicles != null ? line.vehicles.len() : 0);
  if (have <= 0 || !("estimMarginalRawRevenue" in line)
      || !("estimMarginalRunning" in line) || !("estimMarginalAmort" in line)
      || !("estimMarginalBaseVehicles" in line)
      || line.estimMarginalBaseVehicles != have) return null;
  /* C121 a evalue une unique transition n -> n+1. Ne pas extrapoler la
   * marge de ce palier a plusieurs avions, car demande et cannibalisation
   * changent a chaque achat. Le prochain palier sera reevalue apres l'achat. */
  local tranche = clone entry;
  tranche.want = 1;
  local dR = entry.v161DeltaR;
  local dE = entry.v161DeltaE;
  local dA = entry.v161DeltaA;
  local dC = entry.planePrice;
  local dP = dR - dE - dA;
  if (dR <= 0 || dP <= 0 || dC <= 0) return null;
  local budget = dC + ((ESTIM_UNIFIE & 2) != 0 ? 0 : 1000);
  return {
    mode = "fleet", kind = "fleet", cargo = line.cargo,
    src = line.stationA, dst = ("stationB" in line) ? line.stationB : line.stationA,
    payload = tranche, distance = 0, capital = dC, budgetCapital = budget,
    deltaR = dR, deltaE = dE, deltaA = dA, deltaC = dC, deltaP = dP,
    revenueAnnual = dR, profitAnnual = dP, estimMarginalModeled = true,
    v161NetMarginalModeled = true, v161Source = entry.v161Source,
    v161ModelPerPlane = dP,
    roi = (dP * 1000) / dC, expectedOpcodes = PROJECT_ROAD_TRANSACTION_OPS,
    budgetScore = OpexProjectScore(dR, budget),
    opcodeScore = OpexProjectScore(dR, PROJECT_ROAD_TRANSACTION_OPS),
    planningOpcodes = 0, economicsDate = AIDate.GetCurrentDate(),
  };
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
  if ((ESTIM_UNIFIE & 2) != 0) budgetCapital = economics.capital;
  if (("immobilise" in economics) && economics.immobilise > 0) {
    budgetCapital += economics.immobilise;
  }
  local decisionBudgetCapital = decisionEconomics.capital + margin;
  if ((ESTIM_UNIFIE & 2) != 0) decisionBudgetCapital = decisionEconomics.capital;
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
  OpexEstimAttachProjectComponents(project, decisionEconomics.revenueAnnual,
      decisionEconomics.runningAnnual, decisionEconomics.amortAnnual);
  return project;
}

function OpexProjectFromWater(catalog, plan, planningOps)
{
  if (plan == null || !("economics" in plan)) return null;
  local economics = plan.economics;
  if (economics.profitAnnual <= 0 || economics.revenueAnnual <= 0 ||
      economics.capital <= 0) return null;
  local budgetCapital = economics.capital + WATER_CAPITAL_MARGIN;
  if ((ESTIM_UNIFIE & 2) != 0) budgetCapital = economics.capital;
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
  OpexEstimAttachProjectComponents(project, economics.revenueAnnual,
      economics.runningAnnual, economics.amortAnnual);
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
