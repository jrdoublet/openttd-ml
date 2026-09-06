/* Sonde du vecteur de tension (A6).
 *
 * Ce fichier ne prend AUCUNE decision. Il lit les ressources vivantes et rapporte, pour chaque
 * projet deja classe, cout / (disponible - engagements + flux * tau).
 *
 * Trois regles de conception, chacune tranchee par une mesure au dossier :
 *   - tau est ENDOGENE : l'horizon d'amortissement de l'action elle-meme, jamais un horizon
 *     de confort choisi a la main ;
 *   - les engagements sont MESURES : entretien mensuel reellement du, pas le compte de resultat
 *     du trimestre -- lequel contient les CHANTIERS, donc ferait reagir la tension a la
 *     construction passee au lieu des obligations a venir ;
 *   - le flux reste SIGNE : une ressource qui SE VIDE est la plus contraignante de toutes, et
 *     c'est tout l'interet du temps-avant-epuisement. Un denominateur nul ou negatif produit la
 *     sentinelle entiere TENSION_INFINITE.
 *
 * Cout d'opcodes : tout ce qui ne depend pas du projet est calcule UNE fois par cycle dans
 * OpexTensionContext. La sonde mesure les opcodes ; elle ne doit pas les gaspiller par un
 * parcours de flotte repete a chaque projet.
 */

const TENSION_INFINITE = -1;

/* Contexte branche uniquement quand tension_probe vaut 1. Le logger historique reste ainsi
 * litteralement celui d'avant sur le chemin par defaut. */
TENSION_BUDGET <- null;
TENSION_SAMPLE_DATE <- null;
TENSION_SAMPLE_TICK <- 0;
TENSION_TICKS_PER_DAY <- 0.0;

function OpexTensionEnable(budget)
{
  TENSION_BUDGET = budget;
  TENSION_SAMPLE_DATE = AIDate.GetCurrentDate();
  TENSION_SAMPLE_TICK = AIController.GetTick();
  ::OpexLogPortfolioRank = OpexLogPortfolioRankWithTension;
}

/* Mesure le debit de la VM par mois de jeu sans supposer 74 ticks par jour. La longueur de
 * l'annee courante vient elle aussi de l'API de date. Tant qu'aucun jour n'a passe, le debit
 * reste nul et la tension opcode devient explicitement infinie. */
function OpexTensionOpcodeFlowPerMonth()
{
  local date = AIDate.GetCurrentDate();
  local tick = AIController.GetTick();
  if (TENSION_SAMPLE_DATE == null || date < TENSION_SAMPLE_DATE) {
    TENSION_SAMPLE_DATE = date;
    TENSION_SAMPLE_TICK = tick;
  } else if (date > TENSION_SAMPLE_DATE) {
    local elapsedDays = date - TENSION_SAMPLE_DATE;
    local elapsedTicks = tick - TENSION_SAMPLE_TICK;
    TENSION_TICKS_PER_DAY = elapsedTicks.tofloat() / elapsedDays;
  }

  local tpd = TENSION_TICKS_PER_DAY;
  if (tpd <= 0) tpd = 18.5;
  local year = AIDate.GetYear(date);
  local yearDays = AIDate.GetDate(year + 1, 1, 1) - AIDate.GetDate(year, 1, 1);
  return (OPS_PER_TICK.tofloat() * tpd * yearDays) / 12.0;
}

function OpexTensionModeKey(mode)
{
  if (mode == "rail" || mode == "road" || mode == "air" || mode == "water") return mode;
  if (mode == "fleet") return "air";
  return null;
}

function OpexTensionVehicleSetting(mode)
{
  if (mode == "rail") return "vehicle.max_trains";
  if (mode == "road") return "vehicle.max_roadveh";
  if (mode == "air") return "vehicle.max_aircraft";
  if (mode == "water") return "vehicle.max_ships";
  return null;
}

/* UN SEUL parcours de la flotte par cycle : il rend a la fois les effectifs par type et le cout
 * de fonctionnement. GetRunningCost est annuel (verifie dans script_engine.hpp : "per
 * economy-year"), d'ou la division par 12 -- meme convention qu'OpexCashReserve. */
function OpexTensionFleetScan()
{
  local scan = { rail = 0, road = 0, air = 0, water = 0, runningAnnual = 0 };
  local vehicles = AIVehicleList();
  vehicles.Valuate(AIVehicle.GetRunningCost);
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    scan.runningAnnual += vehicles.GetValue(v);
    local type = AIVehicle.GetVehicleType(v);
    if (type == AIVehicle.VT_RAIL) scan.rail++;
    else if (type == AIVehicle.VT_ROAD) scan.road++;
    else if (type == AIVehicle.VT_AIR) scan.air++;
    else if (type == AIVehicle.VT_WATER) scan.water++;
  }
  return scan;
}

/* Entretien d'infrastructure mensuel, deja mensuel cote API (script_infrastructure.hpp). La
 * doc precise qu'INFRASTRUCTURE_RAIL et _ROAD rendent le total TOUS TYPES confondus : six appels
 * suffisent donc, sans interroger chaque type de rail ou de route. */
function OpexTensionInfraMonthly(company)
{
  if (AIGameSettings.IsValid("economy.infrastructure_maintenance")
      && AIGameSettings.GetValue("economy.infrastructure_maintenance") == 0) return 0;
  local total = 0;
  total += AIInfrastructure.GetMonthlyInfrastructureCosts(company, AIInfrastructure.INFRASTRUCTURE_RAIL);
  total += AIInfrastructure.GetMonthlyInfrastructureCosts(company, AIInfrastructure.INFRASTRUCTURE_SIGNALS);
  total += AIInfrastructure.GetMonthlyInfrastructureCosts(company, AIInfrastructure.INFRASTRUCTURE_ROAD);
  total += AIInfrastructure.GetMonthlyInfrastructureCosts(company, AIInfrastructure.INFRASTRUCTURE_CANAL);
  total += AIInfrastructure.GetMonthlyInfrastructureCosts(company, AIInfrastructure.INFRASTRUCTURE_STATION);
  total += AIInfrastructure.GetMonthlyInfrastructureCosts(company, AIInfrastructure.INFRASTRUCTURE_AIRPORT);
  return total;
}

/* Tout ce qui NE DEPEND PAS du projet, calcule une seule fois par cycle de portefeuille. */
function OpexTensionContext(projects)
{
  local company = AICompany.COMPANY_SELF;
  local scan = OpexTensionFleetScan();
  local infraMonthly = OpexTensionInfraMonthly(company);

  /* Engagements = ce qu'on DOIT le mois prochain quoi qu'il arrive : fonctionnement de la flotte
   * plus entretien d'infrastructure. Surtout PAS les depenses du trimestre, qui contiennent les
   * chantiers : la tension refleterait alors ce qu'on vient de batir, pas ce qu'on doit. */
  local commitments = (scan.runningAnnual / 12) + infraMonthly;

  /* Flux net mensuel, lu sur le dernier trimestre CLOS (CURRENT_QUARTER = 0, donc 1 est le
   * precedent -- verifie dans script_company.hpp:26). Les depenses sont deja signees negatives
   * en 15.3. Les engagements ne sont PAS rededuits du flux : ils y sont deja. */
  local lastQuarter = AICompany.CURRENT_QUARTER + 1;
  local income = AICompany.GetQuarterlyIncome(company, lastQuarter);
  local expenses = AICompany.GetQuarterlyExpenses(company, lastQuarter);
  local monthlyNet = (income.tofloat() + expenses) / 3.0;

  local limits = { rail = 0, road = 0, air = 0, water = 0 };
  foreach (mode, _unused in limits) {
    local key = OpexTensionVehicleSetting(mode);
    if (key != null && AIGameSettings.IsValid(key)) limits[mode] = AIGameSettings.GetValue(key);
  }

  /* FONCIER (revise le 2026-09-03). La premiere version divisait par la TAILLE DU VIVIER du mode,
   * ce qui disait "il reste peu d'idees", pas "il reste peu de place" -- et cette mesure dominait
   * 46 % des evaluations, donc le resultat de tete reposait sur le proxy le plus faible.
   *
   * Le vrai stock etait deja calcule a chaque cycle et jamais lu : le generateur de vivier compte
   * les origines LIBRES, c'est-a-dire les villes et industries qu'aucune de nos gares ne dessert
   * deja (OpexOriginServed / ORIGIN_SEPARATION, candidates.nut:671 et :741). C'est exactement le
   * mur mesure dans docs/opexai_plafonnement.md : chaque gare batie interdit un disque autour
   * d'elle, et l'IA epuise l'espace admissible bien avant la carte.
   *
   * Le stock est une propriete de la CARTE, pas d'un mode : une ville servie par le rail n'est
   * plus une origine libre pour personne. Les trois autres grandeurs (pression de separation,
   * paires produites, taille des viviers) sont journalisees a cote pour pouvoir comparer les
   * mesures entre elles avant d'en figer une. */
  local originsFree = 0;
  local originsServed = 0;
  local pairsTotal = 0;
  local separationRejected = 0;
  local pairsOneServed = 0;
  local pool = { rail = 0, road = 0, air = 0, water = 0 };
  if (projects != null) {
    if (("rail" in projects) && projects.rail != null) {
      if ("candidates" in projects.rail) pool.rail = projects.rail.candidates.len();
      if (("stats" in projects.rail) && projects.rail.stats != null) {
        local st = projects.rail.stats;
        if ("townsUnserved" in st) originsFree += st.townsUnserved;
        if ("industriesUnserved" in st) originsFree += st.industriesUnserved;
        if ("townsServed" in st) originsServed += st.townsServed;
        if ("industriesServed" in st) originsServed += st.industriesServed;
        if ("pairsTotal" in st) pairsTotal = st.pairsTotal;
        if ("pairsOriginServed" in st) separationRejected = st.pairsOriginServed;
        if ("pairsOneServed" in st) pairsOneServed = st.pairsOneServed;
      }
    }
    if (("road" in projects) && projects.road != null && ("candidates" in projects.road)) {
      pool.road = projects.road.candidates.len();
    }
    if (("airPlans" in projects) && projects.airPlans != null) pool.air = projects.airPlans.len();
    if (("waterPlans" in projects) && projects.waterPlans != null) pool.water = projects.waterPlans.len();
  }

  return {
    moneyAvailable = AICompany.GetBankBalance(company)
                     + (AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount()),
    moneyCommitments = commitments, moneyFlow = monthlyNet,
    fleet = scan, limits = limits,
    originsFree = originsFree, originsServed = originsServed,
    pairsTotal = pairsTotal, separationRejected = separationRejected,
    pairsOneServed = pairsOneServed, pool = pool,
    opcodeFlow = OpexTensionOpcodeFlowPerMonth(),
  };
}

function OpexTensionProjectVehicleCount(project)
{
  if (!("payload" in project) || project.payload == null) return 0;
  local payload = project.payload;
  if (project.mode == "fleet") {
    return ("want" in payload) ? payload.want : 1;
  }
  if (project.mode == "rail" || project.mode == "road") {
    return ("trains" in payload) ? payload.trains : 0;
  }
  if (project.mode == "air") {
    if ("planes" in payload) return payload.planes;
    if (("economics" in payload) && payload.economics != null
        && ("planes" in payload.economics)) return payload.economics.planes;
    return 0;
  }
  if (project.mode == "water") {
    if (("economics" in payload) && payload.economics != null
        && ("ship" in payload.economics) && payload.economics.ship != null) return 1;
  }
  return 0;
}

function OpexTensionEntry(resource, cost, available, commitments, flow, tau)
{
  local denominator = available.tofloat() - commitments.tofloat() + flow.tofloat() * tau;
  local tension = denominator <= 0 ? TENSION_INFINITE : cost.tofloat() / denominator;
  return {
    resource = resource, tension = tension, cost = cost, available = available,
    commitments = commitments, flow = flow, tau = tau,
  };
}

function OpexTensionGreater(left, right)
{
  if (left.tension == TENSION_INFINITE) return right.tension != TENSION_INFINITE;
  if (right.tension == TENSION_INFINITE) return false;
  return left.tension > right.tension;
}

/* Rend les quatre tensions, la ressource dominante et l'ecart relatif (premiere - seconde) /
 * premiere. Une seule tension infinie donne l'ecart limite 1 ; deux tensions infinies donnent un
 * ecart nul. tau est exprime en MOIS pour les quatre lignes. */
function OpexTensionVector(project, ctx)
{
  /* tau endogene. Garde explicite : profitAnnual <= 0 est deja ecarte a la creation des projets
   * de candidat (projects.nut, "profitAnnual <= 0 -> null"), mais rien ne le garantit pour tous
   * les modes, et une division par zero ici ferait mourir la sonde -- pas le classement. */
  local cap = ("budgetCapital" in project && project.budgetCapital > 0) ? project.budgetCapital : project.capital;
  local tau = 0.0;
  if (("profitAnnual" in project) && project.profitAnnual > 0) {
    tau = (cap.tofloat() * 12.0) / project.profitAnnual;
  }

  local mode = OpexTensionModeKey(project.mode);
  local fleet = (mode != null && (mode in ctx.fleet)) ? ctx.fleet[mode] : 0;
  local limit = (mode != null && (mode in ctx.limits)) ? ctx.limits[mode] : 0;

  local vector = [
    OpexTensionEntry("argent", cap, ctx.moneyAvailable,
                     ctx.moneyCommitments, ctx.moneyFlow, tau),
    OpexTensionEntry("slots_vehicules", OpexTensionProjectVehicleCount(project),
                     limit - fleet, 0, 0, tau),
    /* Opcodes : debit mensuel de la VM. Contrairement a l'argent, les opcodes ne se stockent pas
     * sur 25 mois : un pathfinder lourd bloque la VM immediatement sur le mois courant (tau = 1). */
    OpexTensionEntry("opcodes", ("expectedOpcodes" in project) ? project.expectedOpcodes : 0,
                     0, 0, ctx.opcodeFlow, 1.0),
    /* Une liaison neuve consomme DEUX origines, une a chaque bout : c'est ce qu'elle retire du
     * stock, et c'est pour ca que le cout n'est pas 1. Le flux est nul -- une origine ne se
     * libere que si une ligne meurt, ce que la fondation de villes ne compense pas au mois. */
    OpexTensionEntry("foncier", 2, ctx.originsFree, 0, 0, tau),
  ];

  local first = null;
  local second = null;
  foreach (entry in vector) {
    if (first == null || OpexTensionGreater(entry, first)) {
      second = first;
      first = entry;
    } else if (second == null || OpexTensionGreater(entry, second)) {
      second = entry;
    }
  }

  local gap = 0.0;
  if (first.tension == TENSION_INFINITE) {
    if (second == null || second.tension != TENSION_INFINITE) gap = 1.0;
  } else if (first.tension > 0 && second != null) {
    gap = (first.tension - second.tension) / first.tension;
  }
  return { vector = vector, dominant = first.resource, gapRelative = gap };
}

/* Calcule les tensions macro-economiques de la compagnie par cycle et determine
 * la contrainte dominante (strict argmax) qui dicte la formule du portefeuille.
 * Regimes possibles :
 *   - "argent"          -> ROI (Profit / Capital)
 *   - "foncier"         -> Abondance : Volume brut de Profit Annuel
 *   - "slots_vehicules" -> Flotte : Profit par Vehicule
 *   - "opcodes"         -> Calcul : Profit par Opcode
 */
function OpexTensionMacroRegime(ctx, projects, planningOps = 0, capitalCeiling = 0)
{
  if (ctx == null) {
    return {
      regime = "argent",
      dominant = "argent",
      maxVal = 1.0,
      tensions = { argent = 1.0, slots_vehicules = 0.0, opcodes = 0.0, foncier = 0.0 }
    };
  }

  // 1. Argent : capacite a financer le projet strategique le plus rentable du vivier (star project)
  // Un projet strategique doit avoir un ROI viable (>= 400, soit 40 %/an) pour ne pas laisser un
  // candidat ferroviaire mediocre et disproportionne (£250k a 35 % de ROI) empoisonner la perception de tresorerie.
  local maxProfit = 0;
  local starCap = 50000;
  if (projects != null) {
    if (("airPlans" in projects) && projects.airPlans != null) {
      foreach (p in projects.airPlans) {
        local cap = ("capital" in p) ? p.capital : 50000;
        if (capitalCeiling > 0 && cap > capitalCeiling) continue;
        local profit = ("economics" in p && "profitAnnual" in p.economics) ? p.economics.profitAnnual : 0;
        local roi = ("economics" in p && "roi" in p.economics) ? p.economics.roi : (cap > 0 ? (profit * 1000) / cap : 0);
        if (roi >= 400 && profit > maxProfit) {
          maxProfit = profit;
          starCap = cap;
        }
      }
    }
    if (("rail" in projects) && projects.rail != null && ("candidates" in projects.rail)) {
      foreach (c in projects.rail.candidates) {
        local cap = ("capital" in c) ? c.capital : 50000;
        if (capitalCeiling > 0 && cap > capitalCeiling) continue;
        local profit = ("profitAnnual" in c) ? c.profitAnnual : 0;
        local roi = ("roi" in c) ? c.roi : (cap > 0 ? (profit * 1000) / cap : 0);
        if (roi >= 400 && profit > maxProfit) {
          maxProfit = profit;
          starCap = cap;
        }
      }
    }
    if (("road" in projects) && projects.road != null && ("candidates" in projects.road)) {
      foreach (c in projects.road.candidates) {
        local cap = ("capital" in c) ? c.capital : 50000;
        if (capitalCeiling > 0 && cap > capitalCeiling) continue;
        local profit = ("profitAnnual" in c) ? c.profitAnnual : 0;
        local roi = ("roi" in c) ? c.roi : (cap > 0 ? (profit * 1000) / cap : 0);
        if (roi >= 400 && profit > maxProfit) {
          maxProfit = profit;
          starCap = cap;
        }
      }
    }
    if (("waterPlans" in projects) && projects.waterPlans != null) {
      foreach (p in projects.waterPlans) {
        local cap = ("capital" in p) ? p.capital : 50000;
        if (capitalCeiling > 0 && cap > capitalCeiling) continue;
        local profit = ("economics" in p && "profitAnnual" in p.economics) ? p.economics.profitAnnual : 0;
        local roi = ("economics" in p && "roi" in p.economics) ? p.economics.roi : (cap > 0 ? (profit * 1000) / cap : 0);
        if (roi >= 400 && profit > maxProfit) {
          maxProfit = profit;
          starCap = cap;
        }
      }
    }
  }

  // Horizon macro : 12 mois de flux net positif
  local flowTerm = ctx.moneyFlow > 0 ? (ctx.moneyFlow.tofloat() * 12.0) : 0.0;
  local denomArgent = ctx.moneyAvailable.tofloat() - ctx.moneyCommitments.tofloat() + flowTerm;
  local t_argent = 0.0;
  if (denomArgent <= 0) {
    t_argent = 999.0;
  } else {
    t_argent = starCap.tofloat() / denomArgent;
  }

  // 2. Slots vehicules : occupation de la flotte par rapport aux plafonds de jeu
  local totalFleet = ctx.fleet.rail + ctx.fleet.road + ctx.fleet.air + ctx.fleet.water;
  local totalLimit = ctx.limits.rail + ctx.limits.road + ctx.limits.air + ctx.limits.water;
  if (totalLimit <= 0) totalLimit = 500;
  local t_slots = totalFleet.tofloat() / totalLimit.tofloat();

  // 3. Opcodes : charge de calcul de la planification face au debit mensuel VM
  local opsDemand = planningOps > 0 ? planningOps.tofloat() : 15000.0;
  local t_opcodes = 0.0;
  if (ctx.opcodeFlow > 0) {
    t_opcodes = opsDemand / ctx.opcodeFlow.tofloat();
  }

  // 4. Foncier : seuil d'abondance (1.0 = capacite a financer le star project)
  // majore par la saturation du foncier cartographique
  local totalOrigins = ctx.originsFree + ctx.originsServed;
  local landSaturation = (totalOrigins > 0) ? (ctx.originsServed.tofloat() / totalOrigins.tofloat()) : 0.0;
  local t_foncier = 1.0 + landSaturation;

  // Selection par strict argmax
  local tensionsList = [
    { res = "argent", val = t_argent },
    { res = "slots_vehicules", val = t_slots },
    { res = "opcodes", val = t_opcodes },
    { res = "foncier", val = t_foncier },
  ];

  local dominant = "argent";
  local maxVal = -1000.0;
  foreach (item in tensionsList) {
    if (item.val > maxVal) {
      maxVal = item.val;
      dominant = item.res;
    }
  }

  return {
    regime = dominant,
    dominant = dominant,
    maxVal = maxVal,
    tensions = {
      argent = t_argent,
      slots_vehicules = t_slots,
      opcodes = t_opcodes,
      foncier = t_foncier
    }
  };
}

/* Calcule le score d'un projet selon la formule dictee par le regime macro de tension. */
function OpexProjectScoreForRegime(project, regime)
{
  if (project == null) return 0.0;
  local profit = ("profitAnnual" in project) ? project.profitAnnual : 0;
  if (profit <= 0) return 0.0;
  local cap = ("budgetCapital" in project && project.budgetCapital > 0) ? project.budgetCapital : project.capital;

  if (regime == "argent") {
    // Formule ROI : Profit / Capital
    return cap > 0 ? (profit.tofloat() * 1000.0) / cap : 0.0;
  }
  if (regime == "slots_vehicules") {
    // Formule Flotte : Profit / Vehicule
    local vehs = OpexTensionProjectVehicleCount(project);
    if (vehs < 1) vehs = 1;
    return (profit.tofloat() * 1000.0) / vehs;
  }
  if (regime == "opcodes") {
    // Formule Opcodes : Profit / Opcode
    local ops = ("expectedOpcodes" in project && project.expectedOpcodes > 0) ? project.expectedOpcodes : 1000;
    return (profit.tofloat() * 1000000.0) / ops;
  }
  // Regime foncier / abondance : Profit Annuel brut (* 1000 pour conserver l'echelle)
  return profit.tofloat() * 1000.0;
}

/* Calcule le prix d'ombre dual d'une contrainte gloutonne par parcours critique (Dantzig 1957).
 * elements : tableau de tables { profit, cost, density }
 * budget : capacite disponible de la ressource. */
function OpexCriticalShadowPrice(elements, budget)
{
  if (elements == null || elements.len() == 0) return 0.0;
  if (budget == null) return 0.0;

  local totalCost = 0.0;
  foreach (item in elements) {
    totalCost += item.cost;
  }
  // Si la demande totale ne depasse pas le budget, la contrainte ne mord pas (complementary slackness)
  if (totalCost <= budget) return 0.0;

  // Tri par densite decroissante
  elements.sort(function(a, b) {
    if (a.density > b.density) return -1;
    if (a.density < b.density) return 1;
    return 0;
  });

  // Si budget <= 0, famine immediate : l'element le plus dense fixe le prix d'ombre
  if (budget <= 0) {
    return elements[0].density;
  }

  // Parcours critique glouton
  local accumulated = 0.0;
  foreach (item in elements) {
    accumulated += item.cost;
    if (accumulated > budget) {
      // Element critique fractionnaire : son rendement marginal est le prix d'ombre dual
      return item.density;
    }
  }
  return 0.0;
}

/* C35.3 : Calcule les prix d'ombre duaux (argent, slots par mode, opcodes, foncier)
 * par parcours critique de Dantzig sur l'ensemble des candidats du vivier multimodal. */
function OpexTensionComputeShadowPrices(ctx, candidates, capitalBudget)
{
  local shadow = {
    argent = 0.0,
    slots = { rail = 0.0, road = 0.0, air = 0.0, water = 0.0 },
    opcodes = 0.0,
    foncier = 0.0,
    budgetArgent = 0.0,
    budgetSlots = { rail = 0.0, road = 0.0, air = 0.0, water = 0.0 },
    budgetOps = 0.0,
    budgetFoncier = 0.0,
  };
  if (candidates == null || candidates.len() == 0) return shadow;

  // 1. ARGENT (£ de capital)
  local argentElements = [];
  foreach (p in candidates) {
    local prof = ("profitAnnual" in p && p.profitAnnual > 0) ? p.profitAnnual.tofloat() : 0.0;
    local cap = ("budgetCapital" in p && p.budgetCapital > 0) ? p.budgetCapital.tofloat()
              : (("capital" in p && p.capital > 0) ? p.capital.tofloat() : 1.0);
    if (prof > 0 && cap > 0) {
      argentElements.append({ profit = prof, cost = cap, density = prof / cap });
    }
  }
  local bArgent = capitalBudget > 0 ? capitalBudget.tofloat()
                : ((ctx != null && ctx.moneyAvailable > 0) ? ctx.moneyAvailable.tofloat() : 1000.0);
  shadow.argent = OpexCriticalShadowPrice(argentElements, bArgent);
  shadow.budgetArgent = bArgent;

  // 2. SLOTS VEHICULES (par mode physique)
  local modes = ["rail", "road", "air", "water"];
  foreach (m in modes) {
    local slotElements = [];
    foreach (p in candidates) {
      local modeKey = OpexTensionModeKey(p.mode);
      if (modeKey != m) continue;
      local prof = ("profitAnnual" in p && p.profitAnnual > 0) ? p.profitAnnual.tofloat() : 0.0;
      local vehs = OpexTensionProjectVehicleCount(p).tofloat();
      if (vehs < 1.0) vehs = 1.0;
      if (prof > 0) {
        slotElements.append({ profit = prof, cost = vehs, density = prof / vehs });
      }
    }
    local lim = (ctx != null && (m in ctx.limits)) ? ctx.limits[m].tofloat() : 500.0;
    local flt = (ctx != null && (m in ctx.fleet)) ? ctx.fleet[m].tofloat() : 0.0;
    local bSlots = lim - flt;
    if (bSlots < 0.0) bSlots = 0.0;
    shadow.slots[m] = OpexCriticalShadowPrice(slotElements, bSlots);
    shadow.budgetSlots[m] = bSlots;
  }

  // 3. OPCODES (debit mensuel VM)
  local opsElements = [];
  foreach (p in candidates) {
    local prof = ("profitAnnual" in p && p.profitAnnual > 0) ? p.profitAnnual.tofloat() : 0.0;
    local ops = ("expectedOpcodes" in p && p.expectedOpcodes > 0) ? p.expectedOpcodes.tofloat() : 1000.0;
    if (prof > 0 && ops > 0) {
      opsElements.append({ profit = prof, cost = ops, density = prof / ops });
    }
  }
  local bOps = (ctx != null && ctx.opcodeFlow > 0) ? ctx.opcodeFlow.tofloat() : 1000000.0;
  shadow.opcodes = OpexCriticalShadowPrice(opsElements, bOps);
  shadow.budgetOps = bOps;

  // 4. FONCIER (origines libres)
  local foncierElements = [];
  foreach (p in candidates) {
    local prof = ("profitAnnual" in p && p.profitAnnual > 0) ? p.profitAnnual.tofloat() : 0.0;
    local orig = (p.mode == "fleet") ? 0.0 : 2.0;
    if (prof > 0 && orig > 0) {
      foncierElements.append({ profit = prof, cost = orig, density = prof / orig });
    }
  }
  local bFoncier = (ctx != null && ctx.originsFree > 0) ? ctx.originsFree.tofloat() : 0.0;
  shadow.foncier = OpexCriticalShadowPrice(foncierElements, bFoncier);
  shadow.budgetFoncier = bFoncier;

  return shadow;
}

/* C35.3 + C35.4 : ProfitAnnuel - sum_r λ_r a_ir pour les contraintes tendues sur
 * le vivier (lambda_r > 0). Si k>1, le prelevement est partage (tax/k) pour ne
 * pas additionner des Dantzig 1D independants. Complementary slackness est une
 * propriete de la ressource, pas de la taille du projet.
 *
 * Limite mesurée (docs/diag_c35_4_weak_3y.json, banc 20×10) : a_ops est
 * incommensurable (air 1e5, route 2.87e5, rail ~3e7) et le Dantzig vivier
 * saturé pose λ_ops > 0 en permanence, ce qui annule le rail sur les graines
 * faibles. Ne pas « corriger » par un filtre densité < λ_argent ni par un
 * surplus absolu capital-seul : les deux ont perdu 7/7 à 6 ans. */
function OpexReducedCostScore(project, shadowPrices)
{
  if (project == null) return 0.0;
  local profit = ("profitAnnual" in project) ? project.profitAnnual.tofloat() : 0.0;
  if (profit <= 0) return 0.0;
  local cap = ("budgetCapital" in project && project.budgetCapital > 0) ? project.budgetCapital.tofloat()
            : (("capital" in project && project.capital > 0) ? project.capital.tofloat() : 1.0);
  local vehs = OpexTensionProjectVehicleCount(project).tofloat();
  if (vehs < 1.0) vehs = 1.0;
  local ops = ("expectedOpcodes" in project && project.expectedOpcodes > 0) ? project.expectedOpcodes.tofloat() : 1000.0;
  local origins = (project.mode == "fleet") ? 0.0 : 2.0;

  local modeKey = OpexTensionModeKey(project.mode);
  local lambdaSlots = (shadowPrices != null && ("slots" in shadowPrices) && (modeKey in shadowPrices.slots))
                      ? shadowPrices.slots[modeKey] : 0.0;
  local lambdaArgent = (shadowPrices != null && ("argent" in shadowPrices)) ? shadowPrices.argent : 0.0;
  local lambdaOps = (shadowPrices != null && ("opcodes" in shadowPrices)) ? shadowPrices.opcodes : 0.0;
  local lambdaFoncier = (shadowPrices != null && ("foncier" in shadowPrices)) ? shadowPrices.foncier : 0.0;

  local tax = 0.0;
  local nActive = 0;
  if (lambdaArgent > 0.0) {
    tax += lambdaArgent * cap;
    nActive++;
  }
  if (lambdaSlots > 0.0) {
    tax += lambdaSlots * vehs;
    nActive++;
  }
  if (lambdaOps > 0.0) {
    tax += lambdaOps * ops;
    nActive++;
  }
  if (lambdaFoncier > 0.0 && origins > 0.0) {
    tax += lambdaFoncier * origins;
    nActive++;
  }
  if (nActive > 1) tax = tax / (nActive * 1.0);
  return profit - tax;
}

/* Score de classement A1 par regime de tension (loi de Liebig) ou C35.3 (cout reduit dual).
 * Sous shadowPrices : Score = ProfitAnnuel - sum_r lambda_r * a_ir (prix d'ombre dual).
 * Sous regime macro Liebig : argent -> ROI, foncier -> profit brut, slots -> profit/vehicule, opcodes -> profit/opcode. */
function OpexTensionScore(project, ctx, decisionFriction = 0.05)
{
  if (project == null) return 0.0;
  if (ctx != null && ("shadowPrices" in ctx)) {
    return OpexReducedCostScore(project, ctx.shadowPrices);
  }
  if (ctx == null) {
    local profit = ("profitAnnual" in project) ? project.profitAnnual : 0;
    local cap = ("budgetCapital" in project && project.budgetCapital > 0) ? project.budgetCapital : project.capital;
    return cap > 0 ? (profit.tofloat() * 1000.0) / cap : 0.0;
  }
  local regime = ("regime" in ctx) ? ctx.regime : "argent";
  return OpexProjectScoreForRegime(project, regime);
}


