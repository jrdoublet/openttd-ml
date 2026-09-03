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

  if (TENSION_TICKS_PER_DAY <= 0) return 0.0;
  local year = AIDate.GetYear(date);
  local yearDays = AIDate.GetDate(year + 1, 1, 1) - AIDate.GetDate(year, 1, 1);
  return (OPS_PER_TICK.tofloat() * TENSION_TICKS_PER_DAY * yearDays) / 12.0;
}

function OpexTensionModeKey(mode)
{
  if (mode == "rail" || mode == "road" || mode == "air" || mode == "water") return mode;
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
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    scan.runningAnnual += AIVehicle.GetRunningCost(v);
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

  /* Foncier : les candidats survivants du MEME mode que le projet. Sommer les quatre modes
   * compterait deux fois une paire proposee en rail et en route, et ne dirait rien de l'espace
   * reellement disponible pour l'action evaluee. */
  local land = { rail = 0, road = 0, air = 0, water = 0 };
  local separationRejected = 0;
  if (projects != null) {
    if (("rail" in projects) && projects.rail != null && ("candidates" in projects.rail)) {
      land.rail = projects.rail.candidates.len();
      if (("stats" in projects.rail) && projects.rail.stats != null
          && ("pairsOriginServed" in projects.rail.stats)) {
        separationRejected = projects.rail.stats.pairsOriginServed;
      }
    }
    if (("road" in projects) && projects.road != null && ("candidates" in projects.road)) {
      land.road = projects.road.candidates.len();
    }
    if (("airPlans" in projects) && projects.airPlans != null) land.air = projects.airPlans.len();
    if (("waterPlans" in projects) && projects.waterPlans != null) land.water = projects.waterPlans.len();
  }

  return {
    moneyAvailable = AICompany.GetBankBalance(company)
                     + (AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount()),
    moneyCommitments = commitments, moneyFlow = monthlyNet,
    fleet = scan, limits = limits, land = land,
    separationRejected = separationRejected,
    opcodeFlow = OpexTensionOpcodeFlowPerMonth(),
  };
}

function OpexTensionProjectVehicleCount(project)
{
  if (!("payload" in project) || project.payload == null) return 0;
  local payload = project.payload;
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
  local tau = 0.0;
  if (("profitAnnual" in project) && project.profitAnnual > 0) {
    tau = (project.capital.tofloat() * 12.0) / project.profitAnnual;
  }

  local mode = OpexTensionModeKey(project.mode);
  local fleet = (mode != null) ? ctx.fleet[mode] : 0;
  local limit = (mode != null) ? ctx.limits[mode] : 0;
  local landAvailable = (mode != null) ? ctx.land[mode] : 0;

  local vector = [
    OpexTensionEntry("argent", project.capital, ctx.moneyAvailable,
                     ctx.moneyCommitments, ctx.moneyFlow, tau),
    OpexTensionEntry("slots_vehicules", OpexTensionProjectVehicleCount(project),
                     limit - fleet, 0, 0, tau),
    OpexTensionEntry("opcodes", ("expectedOpcodes" in project) ? project.expectedOpcodes : 0,
                     0, 0, ctx.opcodeFlow, tau),
    OpexTensionEntry("foncier", 1, landAvailable, 0, 0, tau),
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
