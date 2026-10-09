/* P0 capital : le cout de construction et le tampon de caisse ont des contrats separes.
 * Les sommes portent sur des constructions TERMINEES, avec leur devis AVANT chantier.
 * Les tentatives echouees sont mesurees a part : leur cout net (apres remboursement)
 * n'est pas le cout d'une ligne achevee et ne peut pas entrainer le calibrage. */
CAPITAL_QUOTE_LEARNING <- false;
OPEX_CAPITAL_QUOTE_SAMPLES <- {};

function OpexCapitalQuoteFamily(mode, subject)
{
  if (subject == null) return null;
  local kind = (("kind" in subject) && subject.kind != null) ? subject.kind : "pax";
  if (mode == "air") {
    local plan = (("payload" in subject) && subject.payload != null)
        ? subject.payload : subject;
    local count = ((("reuseA" in plan) && plan.reuseA) ? 0 : 1)
        + ((("reuseB" in plan) && plan.reuseB) ? 0 : 1);
    local planes = ("planes" in plan) ? plan.planes : 1;
    return "air|" + count + "|planes=" + planes;
  }
  if (mode == "rail" || mode == "road") {
    local vehicleCount = ("trains" in subject) ? subject.trains
        : (("payload" in subject) && subject.payload != null
            && ("trains" in subject.payload) ? subject.payload.trains : 1);
    return mode + "|" + kind + "|vehicles=" + vehicleCount;
  }
  if (mode == "water") return "water|pax";
  return null;
}

function OpexCapitalQuoteDistance(subject)
{
  return (subject != null && ("distance" in subject) && subject.distance > 0)
      ? subject.distance : -1;
}

/* Aucun facteur impose : au demarrage et hors plage observee, coefficient 1.
 * Ratio des SOMMES, pas moyenne des ratios : un petit trajet n'a pas le meme
 * poids monetaire qu'un long. La plage limite l'extrapolation sur les distances
 * et les categories de chantier encore absentes des realisations. */
function OpexCapitalQuoteFactor(mode, subject)
{
  if (!CAPITAL_QUOTE_LEARNING) return 1.0;
  local family = OpexCapitalQuoteFamily(mode, subject);
  if (family == null || !(family in OPEX_CAPITAL_QUOTE_SAMPLES)) return 1.0;
  local s = OPEX_CAPITAL_QUOTE_SAMPLES[family];
  if (s.n <= 0 || s.quoted <= 0) return 1.0;
  local distance = OpexCapitalQuoteDistance(subject);
  if (distance < 0 || distance < s.minDistance || distance > s.maxDistance)
    return 1.0;
  return s.actual.tofloat() / s.quoted.tofloat();
}

/* Devis de construction seul. Le complement (marge de financement et capital
 * immobilise dans le transit) garde strictement sa valeur de politique. */
function OpexCapitalQuoteFinance(project, historicalFinance)
{
  if (project == null || !("mode" in project) || !("capital" in project)
      || project.capital <= 0) return historicalFinance;
  local construction = project.capital;
  local isActual = (("capitalIsActual" in project) && project.capitalIsActual)
      || (("payload" in project) && project.payload != null
          && ("capitalIsActual" in project.payload) && project.payload.capitalIsActual);
  local nonConstruction = project.budgetCapital - construction;
  if (nonConstruction < 0) nonConstruction = 0;
  if (isActual) {
    if (("payload" in project) && project.payload != null
        && ("capitalIsActual" in project.payload) && project.payload.capitalIsActual
        && ("capital" in project.payload) && project.payload.capital > 0)
      construction = project.payload.capital;
    return construction + nonConstruction;
  }
  local factor = OpexCapitalQuoteFactor(project.mode, project);
  return (construction * factor).tointeger() + nonConstruction;
}

/* C111/C118 AIR garde une economie distincte pour le score. On transforme son
 * devis de construction avec la meme observation sans recalibrer le tampon. */
function OpexCapitalQuoteDecisionFinance(project, decisionFinance)
{
  if (!CAPITAL_QUOTE_LEARNING || project == null || project.mode != "air"
      || !("capital" in project) || project.capital <= 0) return decisionFinance;
  local decisionConstruction = (("decisionConstructionCapital" in project)
      && project.decisionConstructionCapital > 0)
      ? project.decisionConstructionCapital : project.capital;
  local nonConstruction = decisionFinance - decisionConstruction;
  if (nonConstruction < 0) nonConstruction = 0;
  return (decisionConstruction * OpexCapitalQuoteFactor("air", project)).tointeger()
      + nonConstruction;
}

function OpexCapitalQuoteAlternativeFinance(project, economics, finance)
{
  if (!CAPITAL_QUOTE_LEARNING || project == null || economics == null
      || !("capital" in economics) || economics.capital <= 0) return finance;
  local marginAndTransit = finance - economics.capital;
  if (marginAndTransit < 0) marginAndTransit = 0;
  return (economics.capital * OpexCapitalQuoteFactor("air", project)).tointeger()
      + marginAndTransit;
}

function OpexCapitalQuoteObserve(mode, subject, result, quoteOverride = -1,
                                 expectedPlanes = -1, expectedVehicles = -1)
{
  if (!CAPITAL_QUOTE_LEARNING || result == null) return;
  local family = OpexCapitalQuoteFamily(mode, subject);
  if (family == null) return;
  local quote = quoteOverride > 0 ? quoteOverride
      : (("plannedCapital" in result) ? result.plannedCapital
          : (("capital" in subject) ? subject.capital : -1));
  local actual = ("actualCost" in result) ? result.actualCost : 0;
  local success = ("ok" in result) && result.ok;
  local distance = OpexCapitalQuoteDistance(subject);
  local comparable = true;
  if (mode == "air" && expectedPlanes > 0) {
    comparable = ("vehicles" in result) && result.vehicles != null
        && result.vehicles.len() == expectedPlanes;
    local newAirports = ((("reuseA" in subject) && subject.reuseA) ? 0 : 1)
        + ((("reuseB" in subject) && subject.reuseB) ? 0 : 1);
    family = "air|" + newAirports + "|planes=" + expectedPlanes;
  }
  if (mode == "rail" && success && ("trains" in subject) && ("trains" in result))
    comparable = result.trains == (expectedVehicles > 0 ? expectedVehicles : subject.trains);
  if (mode == "road" && success && ("vehicles" in result)
      && ("payload" in subject) && subject.payload != null
      && ("trains" in subject.payload))
    comparable = result.vehicles.len() == (expectedVehicles > 0
        ? expectedVehicles : subject.payload.trains);
  if ((mode == "rail" || mode == "road") && expectedVehicles > 0) {
    local kind = (("kind" in subject) && subject.kind != null) ? subject.kind : "pax";
    family = mode + "|" + kind + "|vehicles=" + expectedVehicles;
  }
  if (mode == "water" && success && ("vehicle" in result)
      && result.vehicle != null && ("payload" in subject)
      && subject.payload != null && ("economics" in subject.payload)
      && subject.payload.economics != null
      && ("ship" in subject.payload.economics)
      && subject.payload.economics.ship != null)
    comparable = AIVehicle.GetEngineType(result.vehicle) == subject.payload.economics.ship.id;
  if (!(family in OPEX_CAPITAL_QUOTE_SAMPLES)) {
    OPEX_CAPITAL_QUOTE_SAMPLES[family] <- {
      n = 0, quoted = 0, actual = 0, minDistance = 2147483647, maxDistance = -1,
      failed = 0, failedNet = 0
    };
  }
  local sample = OPEX_CAPITAL_QUOTE_SAMPLES[family];
  if (success && comparable && quote > 0 && actual > 0 && distance >= 0) {
    sample.n++;
    sample.quoted += quote;
    sample.actual += actual;
    if (distance < sample.minDistance) sample.minDistance = distance;
    if (distance > sample.maxDistance) sample.maxDistance = distance;
  } else if (!success) {
    sample.failed++;
    sample.failedNet += actual;
  }
  /* Sonde compacte par tentative, y compris succes sans devis comparable ou
   * echec avec remboursement. La raison detaillee reste dans les sondes metier. */
  local tag = mode == "air" ? "A" : (mode == "rail" ? "R" : (mode == "road" ? "D" : "W"));
  if (RAIL_COST_PROBE || AIR_COST_PROBE || ROAD_COST_PROBE || C63_INVEST_PROBE)
    OpexSign(AIMap.GetTileIndex(1, 1), "CQ|" + tag + "|" + quote + "|"
        + actual + "|" + (success ? 1 : 0) + "|" + sample.n);
  if (DECISION_LOG) OpexDecide("CAPITAL_QUOTE", "family=" + family + " distance=" + distance
      + " quote=" + quote + " actual_recorded=" + actual + " ok=" + (success ? 1 : 0)
      + " comparable=" + (comparable ? 1 : 0)
      + " successes=" + sample.n + " failures=" + sample.failed);
}

function OpexCapitalQuoteLoad(data)
{
  OPEX_CAPITAL_QUOTE_SAMPLES = {};
  if (data == null || typeof data != "table") return;
  foreach (family, sample in data) {
    if (typeof family != "string" || typeof sample != "table") continue;
    if (!("n" in sample) || !("quoted" in sample) || !("actual" in sample)
        || !("minDistance" in sample) || !("maxDistance" in sample)
        || !("failed" in sample) || !("failedNet" in sample)) continue;
    if (sample.n < 0 || sample.quoted < 0 || sample.actual < 0
        || sample.failed < 0) continue;
    OPEX_CAPITAL_QUOTE_SAMPLES[family] <- {
      n = sample.n, quoted = sample.quoted, actual = sample.actual,
      minDistance = sample.minDistance, maxDistance = sample.maxDistance,
      failed = sample.failed, failedNet = sample.failedNet
    };
  }
}
