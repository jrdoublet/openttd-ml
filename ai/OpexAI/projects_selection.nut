/* Extrait de projects.nut (R14) : Politiques de selection : slots early/defensifs, C121/C122, reserve AIR, selection financable. Requis depuis projects.nut. */

/* Diagnostic R1/R3, jamais un reglage de politique. Le harnais active uniquement
 * cette constante dans une COPIE test-only identifiee et hachee. Etat transitoire,
 * non persiste : les identites doivent etre namespacees par flux/phase au lecteur. */
const R1_R3_TEST_ONLY = 0;
R1_R3_TEST_SEQ <- 0;
R1_R3_TEST_PASS <- 0;

/* C121 autopsie causale : sonde compile-time uniquement, jamais un reglage de
 * politique. Elle serialise exclusivement l'etat deja calcule par le selecteur ;
 * pas de second tri, pas de nouveau modele economique, pas de scan de carte. */
const C121_AUTOPSY_TEST_ONLY = 0;
C121_AUTOPSY_SELECTION_SEQ <- 0;
C121_AUTOPSY_DONE <- false;

require("selection_diagnostics.nut");

function OpexR1R3Log(fields)
{
  if (!R1_R3_TEST_ONLY) return;
  AILog.Info("R1R3 test_only=1 date=" + AIDate.GetCurrentDate()
      + " tick=" + AIController.GetTick() + " " + fields);
}

function OpexC121AutopsyLog(kind, fields)
{
  if (!C121_AUTOPSY_TEST_ONLY) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("C121_AUTOPSY kind=" + kind + " date=" + date
      + " y=" + AIDate.GetYear(date) + " m=" + AIDate.GetMonth(date)
      + " d=" + AIDate.GetDayOfMonth(date) + " tick=" + AIController.GetTick()
      + " " + fields);
}

function OpexC121AutopsyIsAirRelated(project)
{
  if (project == null || !("mode" in project)) return false;
  if (project.mode == "air") return true;
  if (project.mode != "fleet" || !("payload" in project) || project.payload == null
      || !("line" in project.payload) || project.payload.line == null) return false;
  local line = project.payload.line;
  return ("mode" in line) && line.mode == "air";
}

function OpexC121AutopsyProjectFields(project, rank, seq)
{
  if (project == null || !("mode" in project)) return "seq=" + seq + " rank=" + rank + " mode=unknown";
  local mode = project.mode;
  local fields = "seq=" + seq + " rank=" + rank + " mode=" + mode
      + " key=" + OpexProjectAttemptKey(project)
      + " profit=" + (("profitAnnual" in project) ? project.profitAnnual : 0)
      + " revenue=" + (("revenueAnnual" in project) ? project.revenueAnnual : 0)
      + " finance=" + OpexProjectFinanceCapital(project)
      + " decision_finance=" + (("decisionFinanceCapital" in project) ? project.decisionFinanceCapital : -1)
      + " portfolio_finance=" + (("portfolioDecisionFinanceCapital" in project) ? project.portfolioDecisionFinanceCapital : -1)
      + " portfolio_profit=" + (("portfolioProfitAnnual" in project) ? project.portfolioProfitAnnual : -1)
      + " fund_score=" + (("fundScore" in project) ? project.fundScore : 0)
      + " early_bonus=" + (("earlySlotBonusPct" in project) ? project.earlySlotBonusPct : 0)
      + " defensive_comp=" + (("defensiveCompetitorClaims" in project) ? project.defensiveCompetitorClaims : 0)
      + " defensive_own=" + (("defensiveOwnClaims" in project) ? project.defensiveOwnClaims : 0)
      + " defensive_new=" + (("defensiveNewTownClaims" in project) ? project.defensiveNewTownClaims : 0);

  if (mode == "air" && ("payload" in project) && project.payload != null) {
    local plan = project.payload;
    local econ = ("economics" in plan) ? plan.economics : null;
    local dec = ("decisionEconomics" in plan) ? plan.decisionEconomics : null;
    local port = ("portfolioEconomics" in plan) ? plan.portfolioEconomics : null;
    local demand = ("c121Demand" in plan) ? plan.c121Demand : null;
    local townA = ("siteA" in plan && plan.siteA != null && "town" in plan.siteA
        && plan.siteA.town != null && "id" in plan.siteA.town) ? plan.siteA.town.id : -1;
    local townB = ("siteB" in plan && plan.siteB != null && "town" in plan.siteB
        && plan.siteB.town != null && "id" in plan.siteB.town) ? plan.siteB.town.id : -1;
    fields += " arm=" + (("arm" in plan) ? plan.arm : "unknown")
        + " town_a=" + townA + " town_b=" + townB
        + " distance=" + (("distance" in plan) ? plan.distance : (("distance" in project) ? project.distance : -1))
        + " monthly_pax=" + (("monthlyPax" in plan) ? plan.monthlyPax : -1)
        + " demand_pax_a=" + (demand != null && ("paxA" in demand) ? demand.paxA : -1)
        + " demand_pax_b=" + (demand != null && ("paxB" in demand) ? demand.paxB : -1)
        + " demand_mail_a=" + (demand != null && ("mailA" in demand) ? demand.mailA : -1)
        + " demand_mail_b=" + (demand != null && ("mailB" in demand) ? demand.mailB : -1)
        + " econ_profit=" + (econ != null && ("profitAnnual" in econ) ? econ.profitAnnual : -1)
        + " econ_capital=" + (econ != null && ("capital" in econ) ? econ.capital : -1)
        + " econ_planes=" + (econ != null && ("planes" in econ) ? econ.planes : -1)
        + " decision_profit=" + (dec != null && ("profitAnnual" in dec) ? dec.profitAnnual : -1)
        + " decision_capital=" + (dec != null && ("capital" in dec) ? dec.capital : -1)
        + " decision_planes=" + (dec != null && ("planes" in dec) ? dec.planes : -1)
        + " portfolio_econ_profit=" + (port != null && ("profitAnnual" in port) ? port.profitAnnual : -1)
        + " portfolio_econ_capital=" + (port != null && ("capital" in port) ? port.capital : -1)
        + " target_planes=" + (("targetPlanes" in plan) ? plan.targetPlanes : -1)
        + " plane_price=" + (("plane" in plan) && plan.plane != null && ("price" in plan.plane) ? plan.plane.price : -1)
        + " airport_price=" + (("airport" in plan) && plan.airport != null && ("price" in plan.airport) ? plan.airport.price : -1)
        + " reuse_a=" + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0)
        + " reuse_b=" + ((("reuseB" in plan) && plan.reuseB) ? 1 : 0)
        + " defensive_town_a=" + (("defensiveSlotTownA" in project) ? project.defensiveSlotTownA : -1)
        + " defensive_town_b=" + (("defensiveSlotTownB" in project) ? project.defensiveSlotTownB : -1);
  } else if (mode == "fleet" && OpexC121AutopsyIsAirRelated(project)) {
    local entry = project.payload;
    local line = entry.line;
    fields += " line=" + (("lineId" in line) ? line.lineId : -1)
        + " want=" + (("want" in entry) ? entry.want : -1)
        + " have=" + (("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : -1))
        + " target_planes=" + (("targetAirPlanes" in line) ? line.targetAirPlanes : -1)
        + " marginal_samples=" + (("c121MarginalSamples" in line) ? line.c121MarginalSamples : -1)
        + " marginal_profit=" + (("c121MarginalProfit" in line) ? line.c121MarginalProfit : -1)
        + " marginal_revenue=" + (("c121MarginalRevenue" in line) ? line.c121MarginalRevenue : -1)
        + " plane_price=" + (("planePrice" in entry) ? entry.planePrice : -1);
  }
  return fields;
}

function OpexC121AutopsySelection(affordable, capitalBudget, kDec, kDecData, floorProfit)
{
  if (!C121_AUTOPSY_TEST_ONLY || affordable == null || affordable.len() == 0) return;
  local n = affordable.len() < 8 ? affordable.len() : 8;
  local interesting = false;
  for (local i = 0; i < n; i++) {
    if (OpexC121AutopsyIsAirRelated(affordable[i])) { interesting = true; break; }
  }
  if (!interesting) return;

  C121_AUTOPSY_SELECTION_SEQ++;
  local seq = C121_AUTOPSY_SELECTION_SEQ;
  OpexC121AutopsyLog("SEL", "seq=" + seq + " budget=" + capitalBudget
      + " k_dec=" + kDec + " floor=" + floorProfit + " affordable=" + affordable.len()
      + " F=" + (kDecData != null && ("F" in kDecData) ? kDecData.F : -1)
      + " tau=" + (kDecData != null && ("tau" in kDecData) ? kDecData.tau : -1)
      + " N=" + (kDecData != null && ("N" in kDecData) ? kDecData.N : -1));
  for (local i = 0; i < n; i++) {
    OpexC121AutopsyLog("CAND", OpexC121AutopsyProjectFields(affordable[i], i, seq));
  }
}

/* Observation du retour EXISTANT du fit, pas de seconde evaluation. Ne touche
 * ni au vivier ni a son payload : seule la copie admise porte la filiation. */
function OpexR1R3FitTrace(project, fitted, budget)
{
  if (project == null || project.mode != "fleet") return fitted;
  R1_R3_TEST_SEQ++;
  local entry = project.payload;
  local line = entry.line;
  local id = "f" + R1_R3_TEST_SEQ;
  local fields = "mechanism=R1 phase=fit id=" + id
      + " line=" + (line != null && ("lineId" in line) ? line.lineId : -1)
      + " src=" + project.src + " dst=" + project.dst
      + " original=" + entry.want + " fitted=" + (fitted != null ? fitted.payload.want : "unknown")
      + " admitted=" + (fitted != null ? 1 : 0)
      + " base=" + (("baseVehicles" in entry) ? entry.baseVehicles : "unknown")
      + " have=" + (line != null ? (("vehCount" in line) ? line.vehCount : line.vehicles.len()) : "unknown")
      + " scrapping=" + (line == null || (("scrapping" in line) && line.scrapping) ? 1 : 0)
      + " budget=" + budget + " price=" + entry.planePrice
      + " reserve=" + OpexCashReserve() + " buffer=1000"
      + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  OpexR1R3Log(fields);
  if (fitted == null) return null;
  local traced = clone fitted;
  traced.r1r3Id <- id;
  return traced;
}

/* Early-slot doit observer l'etat VIVANT au moment du choix final, pas au moment
 * ou OpexAirPlans a genere le candidat. Un vivier peut etre reutilise/reselecte
 * apres un chantier : une annotation faite plus tot deviendrait alors perimee et
 * pourrait continuer a bonifier une ville deja securisee. On scanne donc les
 * aeroports physiques Opex une seule fois par passe de selection. */
function OpexEarlySlotSelectionState()
{
  local state = { servedTowns = {}, servedCount = 0 };
  if (!AIR_EARLY_SLOT) return state;

  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local townId = AIStation.GetNearestTown(st);
    if (C83_FIXES) {
      local slotTown = OpexAirSlotTownId(AIStation.GetLocation(st));
      if (slotTown >= 0) townId = slotTown;
    }
    if (townId < 0 || !AITown.IsValidTown(townId)) continue;
    if (AITown.GetPopulation(townId) < AIR_EARLY_SLOT_MIN_POP) continue;
    if (townId in state.servedTowns) continue;
    state.servedTowns.rawset(townId, true);
    state.servedCount++;
  }
  return state;
}

/* C121 territoire d'abord : villes ou OpexAI a deja un aeroport (sans seuil de population). */
function OpexC121ServedAirTowns()
{
  local served = {};
  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local townId = AIStation.GetNearestTown(st);
    if (townId >= 0) served.rawset(townId, true);
  }
  return served;
}

/* Un projet AIR est territorial s'il pose un aeroport neuf dans une ville sans aeroport Opex. */
function OpexC121ProjectIsTerritorial(project, served)
{
  if (project == null || !("mode" in project) || project.mode != "air"
      || !("payload" in project) || project.payload == null) return false;
  local plan = project.payload;
  foreach (side in ["A", "B"]) {
    local site = ("site" + side) in plan ? plan["site" + side] : null;
    local reused = ("reuse" + side) in plan && plan["reuse" + side];
    if (site == null || reused || !("town" in site) || site.town == null) continue;
    if (!(site.town.id in served)) return true;
  }
  return false;
}

function OpexDefensiveSlotSelectionState(earlySlotState = null)
{
  local state = {
    servedTowns = {}, servedCount = 0,
    slotRemaining = {}, defensiveSlotSignal = false,
  };

  if (earlySlotState != null) {
    state.servedTowns = earlySlotState.servedTowns;
    state.servedCount = earlySlotState.servedCount;
  } else {
    local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
    for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
      local townId = AIStation.GetNearestTown(st);
      if (C83_FIXES) {
        local slotTown = OpexAirSlotTownId(AIStation.GetLocation(st));
        if (slotTown >= 0) townId = slotTown;
      }
      if (townId < 0 || !AITown.IsValidTown(townId)) continue;
      if (AITown.GetPopulation(townId) < AIR_EARLY_SLOT_MIN_POP) continue;
      if (townId in state.servedTowns) continue;
      state.servedTowns.rawset(townId, true);
      state.servedCount++;
    }
  }

  state.defensiveSlotSignal = OpexAirC83SlotSignalEnabled();
  return state;
}

function OpexC83TownSlotsRemaining(townId, state)
{
  if (state == null || townId < 0 || !AITown.IsValidTown(townId)) return -1;
  if (!("defensiveSlotSignal" in state) || !state.defensiveSlotSignal) return -1;
  if (!(townId in state.slotRemaining)) {
    state.slotRemaining.rawset(townId, AITown.GetAllowedNoise(townId));
  }
  return state.slotRemaining[townId];
}

function OpexC121PressureNewAccum(year)
{
  return { year = year, towns = {}, samples = 0 };
}

/* Cloture l'annee de pression avant le premier scoring de la suivante. Le
 * classifieur adaptatif lit donc toujours une annee complete et stable. */
function OpexC121PressureAdvanceYear()
{
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (C121_AIR_PRESSURE_ACCUM == null) {
    C121_AIR_PRESSURE_ACCUM = OpexC121PressureNewAccum(year);
    return;
  }
  if (C121_AIR_PRESSURE_ACCUM.year == year) return;
  local open = 0;
  local competitor = 0;
  local locked = 0;
  local other = 0;
  foreach (townId, remaining in C121_AIR_PRESSURE_ACCUM.towns) {
    if (remaining >= 2) open++;
    else if (remaining == 1) competitor++;
    else if (remaining == 0) locked++;
    else other++;
  }
  local pressured = competitor + locked;
  local contestablePermille = pressured > 0
      ? (competitor * 1000) / pressured : -1;
  local observedUseful = open + pressured;
  local openPermille = observedUseful > 0
      ? (open * 1000) / observedUseful : -1;
  C121_AIR_PRESSURE_PREV = {
    year = C121_AIR_PRESSURE_ACCUM.year,
    open = open,
    competitor = competitor,
    locked = locked,
    other = other,
    uniqueTowns = C121_AIR_PRESSURE_ACCUM.towns.len(),
    samples = C121_AIR_PRESSURE_ACCUM.samples,
    pressured = pressured,
    contestablePermille = contestablePermille,
    openPermille = openPermille,
  };
  C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED++;
  if (C121_AIR_PRESSURE_PROBE) {
    AILog.Info("C121_PRESSURE_YEAR year=" + C121_AIR_PRESSURE_PREV.year
        + " unique=" + C121_AIR_PRESSURE_PREV.uniqueTowns
        + " open=" + C121_AIR_PRESSURE_PREV.open
        + " competitor=" + C121_AIR_PRESSURE_PREV.competitor
        + " locked=" + C121_AIR_PRESSURE_PREV.locked
        + " pressured=" + pressured
        + " contestable_permille=" + contestablePermille
        + " open_permille=" + openPermille
        + " samples=" + C121_AIR_PRESSURE_PREV.samples);
  }
  if (C121_AIR_PROJECT_REALIZATION_ADAPTIVE || C122_AIR_REGIME_PRIORITY
      || C122_AIR_REGIME_SHADOW) {
    if (C121_AIR_PROJECT_REALIZATION_REGIME < 0
        && C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED
            >= C121_AIR_PROJECT_REALIZATION_CLASSIFY_YEARS) {
      local efficiency = pressured >= C121_AIR_PROJECT_REALIZATION_MIN_PRESSURED
          && contestablePermille >= C121_AIR_PROJECT_REALIZATION_MIN_CONTESTABLE_PERMILLE
          && openPermille >= 0
          && openPermille <= C121_AIR_PROJECT_REALIZATION_MAX_OPEN_PERMILLE;
      C121_AIR_PROJECT_REALIZATION_REGIME = efficiency ? 1 : 0;
      /* Le regime agit sur l'admission au portefeuille, qui est recalculee
       * lors de la publication, et non sur le choix moteur memoise. */
      AILog.Info("C121_STRATEGY_LOCK source_year=" + C121_AIR_PRESSURE_PREV.year
          + " observed_years=" + C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED
          + " pressured=" + pressured + " contestable_permille=" + contestablePermille
          + " open_permille=" + openPermille
          + " regime=" + (efficiency ? "efficiency" : "race"));
    } else {
      local regimeName = C121_AIR_PROJECT_REALIZATION_REGIME < 0 ? "observe"
          : (C121_AIR_PROJECT_REALIZATION_REGIME == 1 ? "efficiency" : "race");
      AILog.Info("C121_STRATEGY source_year=" + C121_AIR_PRESSURE_PREV.year
          + " observed_years=" + C121_AIR_PROJECT_REALIZATION_YEARS_OBSERVED
          + " regime=" + regimeName + " locked="
          + (C121_AIR_PROJECT_REALIZATION_REGIME >= 0 ? 1 : 0));
    }
  }
  C121_AIR_PRESSURE_ACCUM = OpexC121PressureNewAccum(year);
}

/* Probe passive C121 : resume la pression concurrentielle uniquement sur les
 * villes que la selection vient deja de consulter via C83. Aucun scan de carte,
 * aucune lecture API supplementaire du bruit/slot. Le snapshot pourra
 * servir plus tard a choisir un regime AIR au cycle suivant, mais ici il ne
 * participe a aucune decision. */
function OpexC121RecordPressureSnapshot(state)
{
  if ((!C121_AIR_PRESSURE_PROBE && !C121_AIR_PROJECT_REALIZATION_ADAPTIVE
      && !C122_AIR_REGIME_PRIORITY && !C122_AIR_REGIME_SHADOW)
      || state == null || !("slotRemaining" in state)) return;
  OpexC121PressureAdvanceYear();
  local open = 0;
  local competitor = 0;
  local locked = 0;
  local other = 0;
  foreach (townId, remaining in state.slotRemaining) {
    if (remaining >= 2) open++;
    else if (remaining == 1) competitor++;
    else if (remaining == 0) locked++;
    else other++;
    if (!(townId in C121_AIR_PRESSURE_ACCUM.towns)) {
      C121_AIR_PRESSURE_ACCUM.towns.rawset(townId, remaining);
    } else if (remaining < C121_AIR_PRESSURE_ACCUM.towns[townId]) {
      C121_AIR_PRESSURE_ACCUM.towns[townId] = remaining;
    }
  }
  local observed = open + competitor + locked + other;
  C121_AIR_PRESSURE_ACCUM.samples++;
  C121_AIR_PRESSURE_SNAPSHOT = {
    date = AIDate.GetCurrentDate(), observed = observed,
    open = open, competitor = competitor, locked = locked, other = other,
    served = ("servedCount" in state) ? state.servedCount : 0,
  };
  if (C121_AIR_PRESSURE_PROBE) {
    AILog.Info("C121_PRESSURE year=" + AIDate.GetYear(C121_AIR_PRESSURE_SNAPSHOT.date)
        + " observed=" + observed + " open=" + open
        + " competitor=" + competitor + " locked=" + locked
        + " served=" + C121_AIR_PRESSURE_SNAPSHOT.served);
  }
}

/* C78 / course defensive : avec station_noise_level=0 (configuration du duel),
 * OpenTTD implemente AITown.GetAllowedNoise() comme max(0, 2 - nombre d'aeroports)
 * pour TOUTES les compagnies de cette ville. C'est donc directement le nombre de
 * slots physiques restants : 2=libre, 1=un concurrent deja present, 0=verrouille.
 * La ville est deja exclue plus haut si Opex y possede un aeroport. Un seul appel
 * O(1) par ville et par passe remplace ainsi tout scan de carte. Sous la regle de
 * bruit active, ce retour change de semantique ; avec le conseil permissif (=3),
 * le plafond des deux aeroports est lui-meme desactive. Dans ces deux cas on ne
 * declenche pas cette politique. */
function OpexC78TownHasCompetitorAirport(townId, state)
{
  local remaining = OpexC83TownSlotsRemaining(townId, state);
  if (remaining == 1 && C78_SLOT_INTERCEPT_PROBE) {
    OpexC78SlotLog("phase=competitor_airport town=" + townId + " slots_remaining=1");
  }
  return remaining == 1;
}

function OpexProjectSetEarlySlotField(project, field, value)
{
  if (field in project) project[field] = value;
  else project[field] <- value;
}

/* Classe uniquement les projets air DEJA rentables. Le town associe au slot est
 * derive du site physique (meme convention que le diagnostic 771), ce qui evite
 * de confondre la ville cible commerciale avec la ville qui porte réellement la
 * limite des deux aeroports. Aucun champ economique n'est modifie. */
function OpexProjectRefreshEarlySlot(project, state)
{
  if (project == null || state == null) return;

  local physicalClaims = 0;
  local bonusClaims = 0;
  local claimPopulation = 0;
  local townA = -1;
  local townB = -1;
  local popA = -1;
  local popB = -1;

  if (AIR_EARLY_SLOT && ("mode" in project) && project.mode == "air"
      && ("payload" in project) && project.payload != null
      && state.servedCount < AIR_EARLY_SLOT_TARGET_TOWNS) {
    local plan = project.payload;
    local reuseA = ("reuseA" in plan) && plan.reuseA;
    local reuseB = ("reuseB" in plan) && plan.reuseB;
    local claimedTowns = {};

    if (("siteA" in plan) && plan.siteA != null && ("town" in plan.siteA)) {
      townA = AITile.GetClosestTown(plan.siteA.anchor);
      if (townA < 0) townA = plan.siteA.town.id;
      if (townA >= 0 && AITown.IsValidTown(townA)) popA = AITown.GetPopulation(townA);
      if (!reuseA && popA >= AIR_EARLY_SLOT_MIN_POP
          && !(townA in state.servedTowns) && !(townA in claimedTowns)) {
        claimedTowns.rawset(townA, true);
        physicalClaims++;
        claimPopulation += popA;
      }
    }

    if (("siteB" in plan) && plan.siteB != null && ("town" in plan.siteB)) {
      townB = AITile.GetClosestTown(plan.siteB.anchor);
      if (townB < 0) townB = plan.siteB.town.id;
      if (townB >= 0 && AITown.IsValidTown(townB)) popB = AITown.GetPopulation(townB);
      if (!reuseB && popB >= AIR_EARLY_SLOT_MIN_POP
          && !(townB in state.servedTowns) && !(townB in claimedTowns)) {
        claimedTowns.rawset(townB, true);
        physicalClaims++;
        claimPopulation += popB;
      }
    }

    local remaining = AIR_EARLY_SLOT_TARGET_TOWNS - state.servedCount;
    bonusClaims = physicalClaims;
    if (bonusClaims > remaining) bonusClaims = remaining;
  }

  /* Les claims physiques decrivent ce que le chantier securisera reellement.
   * Les bonus claims sont bornes par la cible et seuls eux pilotent la prime. */
  OpexProjectSetEarlySlotField(project, "earlySlotClaims", physicalClaims);
  OpexProjectSetEarlySlotField(project, "earlySlotBonusClaims", bonusClaims);
  OpexProjectSetEarlySlotField(project, "earlySlotClaimPopulation", claimPopulation);
  OpexProjectSetEarlySlotField(project, "earlySlotServedBefore", state.servedCount);
  OpexProjectSetEarlySlotField(project, "earlySlotBonusPct", AIR_EARLY_SLOT_BONUS_PCT * bonusClaims);
  OpexProjectSetEarlySlotField(project, "earlySlotTownA", townA);
  OpexProjectSetEarlySlotField(project, "earlySlotTownB", townB);
  OpexProjectSetEarlySlotField(project, "earlySlotPopA", popA);
  OpexProjectSetEarlySlotField(project, "earlySlotPopB", popB);
}

/* C78 : annotation strictement separee d'early-slot. Ce helper n'est appele
 * que sous C77, afin de ne pas ajouter de travail par candidat au chemin par
 * defaut air_early_slot=1. */
function OpexProjectRefreshDefensiveSlot(project, state)
{
  if (project == null || state == null) return;

  local claims = 0;
  local competitorClaims = 0;
  local ownClaims = 0;
  local newTownClaims = 0;
  local observeNewTowns = C121_AIR_PRESSURE_PROBE || C122_AIR_REGIME_PRIORITY
      || C122_AIR_REGIME_SHADOW;
  local townA = -1;
  local townB = -1;
  if (("mode" in project) && project.mode == "air"
      && ("payload" in project) && project.payload != null) {
    local plan = project.payload;
    local reuseA = ("reuseA" in plan) && plan.reuseA;
    local reuseB = ("reuseB" in plan) && plan.reuseB;
    local ownSecondA = ("c83OwnSecondSlotA" in plan) && plan.c83OwnSecondSlotA;
    local ownSecondB = ("c83OwnSecondSlotB" in plan) && plan.c83OwnSecondSlotB;
    local claimedTowns = {};
    local newTowns = observeNewTowns ? {} : null;

    if (("siteA" in plan) && plan.siteA != null && ("town" in plan.siteA)) {
      if (("anchor" in plan.siteA) && AIMap.IsValidTile(plan.siteA.anchor)) {
        townA = AITile.GetClosestTown(plan.siteA.anchor);
      }
      if (townA < 0) townA = plan.siteA.town.id;
      if (!reuseA && townA >= 0 && AITown.IsValidTown(townA)
          && AITown.GetPopulation(townA) >= AIR_EARLY_SLOT_MIN_POP
          && !(townA in claimedTowns)) {
        if (observeNewTowns
            && !(townA in state.servedTowns) && !(townA in newTowns)) {
          newTowns.rawset(townA, true);
          newTownClaims++;
        }
        if (ownSecondA && (townA in state.servedTowns)
            && OpexC83TownSlotsRemaining(townA, state) == 1) {
          claimedTowns.rawset(townA, true);
          claims++;
          ownClaims++;
        } else if (!(townA in state.servedTowns)
            && OpexC78TownHasCompetitorAirport(townA, state)) {
          claimedTowns.rawset(townA, true);
          claims++;
          competitorClaims++;
        }
      }
    }

    if (("siteB" in plan) && plan.siteB != null && ("town" in plan.siteB)) {
      if (("anchor" in plan.siteB) && AIMap.IsValidTile(plan.siteB.anchor)) {
        townB = AITile.GetClosestTown(plan.siteB.anchor);
      }
      if (townB < 0) townB = plan.siteB.town.id;
      if (!reuseB && townB >= 0 && AITown.IsValidTown(townB)
          && AITown.GetPopulation(townB) >= AIR_EARLY_SLOT_MIN_POP
          && !(townB in claimedTowns)) {
        if (observeNewTowns
            && !(townB in state.servedTowns) && !(townB in newTowns)) {
          newTowns.rawset(townB, true);
          newTownClaims++;
        }
        if (ownSecondB && (townB in state.servedTowns)
            && OpexC83TownSlotsRemaining(townB, state) == 1) {
          claimedTowns.rawset(townB, true);
          claims++;
          ownClaims++;
        } else if (!(townB in state.servedTowns)
            && OpexC78TownHasCompetitorAirport(townB, state)) {
          claimedTowns.rawset(townB, true);
          claims++;
          competitorClaims++;
        }
      }
    }

    /* Ville de slot = ClosestTown(ancre), pas la ville commerciale. Seule une
     * extremite neuve (pas un hub reutilise) peut preempter. */
    if (C83_PREEMPT_OPEN && C83_PREEMPT_TOWN >= 0) {
      local preemptClaims = 0;
      if (!reuseA && ("siteA" in plan) && plan.siteA != null && ("anchor" in plan.siteA)
          && OpexAirSlotTownId(plan.siteA.anchor) == C83_PREEMPT_TOWN) preemptClaims++;
      if (!reuseB && ("siteB" in plan) && plan.siteB != null && ("anchor" in plan.siteB)
          && OpexAirSlotTownId(plan.siteB.anchor) == C83_PREEMPT_TOWN) {
        if (preemptClaims == 0) preemptClaims++;
      }
      if (preemptClaims > 0) OpexProjectSetEarlySlotField(project, "preemptClaims", preemptClaims);
    }
  }

  OpexProjectSetEarlySlotField(project, "defensiveSlotClaims", claims);
  OpexProjectSetEarlySlotField(project, "defensiveCompetitorClaims", competitorClaims);
  OpexProjectSetEarlySlotField(project, "defensiveOwnClaims", ownClaims);
  if (observeNewTowns) {
    OpexProjectSetEarlySlotField(project, "defensiveNewTownClaims", newTownClaims);
  }
  OpexProjectSetEarlySlotField(project, "defensiveSlotTownA", townA);
  OpexProjectSetEarlySlotField(project, "defensiveSlotTownB", townB);
}

/* C78 / course defensive au second slot : sous C77, une grande ville ou un
 * concurrent a deja un aeroport et ou Opex peut encore en poser un est une
 * ressource perissable. Aucun champ economique n'est modifie : cette information
 * sert seulement de classe lexicographique devant les projets ordinaires. */
function OpexProjectDefensiveAirPriority(project)
{
  if (project == null) return 0;
  if (!("mode" in project) || project.mode != "air") return 0;
  if (!("profitAnnual" in project) || project.profitAnnual <= 0) return 0;
  local competitorClaims = ("defensiveCompetitorClaims" in project)
      ? project.defensiveCompetitorClaims : 0;
  if (competitorClaims > 0) return 2;
  /* Meme classe defensive que la course au second slot, donc devant hub a hub
   * (rang 0) et devant le second aeroport deja a nous (rang 1). Le test de
   * profit ci-dessus reste obligatoire : un aeroport vide ou deficitaire
   * ne monte pas. */
  if (C83_PREEMPT_OPEN && ("preemptClaims" in project) && project.preemptClaims > 0) return 2;
  local ownClaims = ("defensiveOwnClaims" in project) ? project.defensiveOwnClaims : 0;
  if (ownClaims > 0) return 1;
  return 0;
}

/* C122.2 : strategie AIR par regime, strictement comme cle d'ordre entre
 * projets AIR deja viables/financables. Aucun champ economique n'est modifie.
 *
 * C77 porte deja le vrai signal perissable de second slot concurrent et reste
 * compare avant C122. En race, C122 ne rajoute donc qu'un signal distinct :
 * une extremite neuve dans une ville que l'etat defensif deja calcule marque
 * comme encore non servie par Opex. Cette annotation reste disponible apres la
 * fenetre early-slot et ne demande aucun scan/appel API supplementaire. En
 * observation / efficiency, l'ordre economique C121 reste brut. Aucun arm
 * topologique n'est favorise en soi.
 *
 * L'appelant ne compare cette priorite que pour AIR<->AIR afin de ne jamais
 * promouvoir AIR devant rail/route/eau sur un simple choix de regime. */
function OpexC122AirRegimeTier(project)
{
  if (C121_AIR_PROJECT_REALIZATION_REGIME != 0) return 0;
  if (project == null || !("mode" in project) || project.mode != "air") return 0;
  local newTownClaims = ("defensiveNewTownClaims" in project) ? project.defensiveNewTownClaims : 0;
  if (newTownClaims > 0) return 1;
  return 0;
}

function OpexC122AirRegimePriority(project)
{
  if (!C122_AIR_REGIME_PRIORITY) return 0;
  return OpexC122AirRegimeTier(project);
}

/* Trace seulement un departage C122 qui inverse l'ordre economique brut. Cela
 * repond a "quel projet territorial a ete promu devant quel projet" sans loguer
 * chaque comparaison de candidats. */
function OpexC122TracePromotion(winner, project, prior, projectC77Tier, priorC77Tier,
                                projectRegimeTier, priorRegimeTier, field)
{
  if (!C122_AIR_REGIME_PRIORITY || field != "fundScore") return;
  ::C122_AIR_PROMOTION_COUNT = C122_AIR_PROMOTION_COUNT + 1;
  if (C122_AIR_PROMOTION_LOG_COUNT >= C122_AIR_PROMOTION_LOG_MAX) return;
  ::C122_AIR_PROMOTION_LOG_COUNT = C122_AIR_PROMOTION_LOG_COUNT + 1;
  local projectArm = (("payload" in project) && project.payload != null
      && ("arm" in project.payload)) ? project.payload.arm : "none";
  local priorArm = (("payload" in prior) && prior.payload != null
      && ("arm" in prior.payload)) ? prior.payload.arm : "none";
  AILog.Info("C122_PROMOTE regime=race reason=new_opex_slot_town winner=" + winner
      + " project_arm=" + projectArm + " prior_arm=" + priorArm
      + " c77_project=" + projectC77Tier + " c77_prior=" + priorC77Tier
      + " c122_project=" + projectRegimeTier + " c122_prior=" + priorRegimeTier
      + " project_early=" + (("earlySlotClaims" in project) ? project.earlySlotClaims : 0)
      + " prior_early=" + (("earlySlotClaims" in prior) ? prior.earlySlotClaims : 0)
      + " project_new=" + (("defensiveNewTownClaims" in project) ? project.defensiveNewTownClaims : 0)
      + " prior_new=" + (("defensiveNewTownClaims" in prior) ? prior.defensiveNewTownClaims : 0)
      + " project_comp=" + (("defensiveCompetitorClaims" in project) ? project.defensiveCompetitorClaims : 0)
      + " prior_comp=" + (("defensiveCompetitorClaims" in prior) ? prior.defensiveCompetitorClaims : 0)
      + " project_own=" + (("defensiveOwnClaims" in project) ? project.defensiveOwnClaims : 0)
      + " prior_own=" + (("defensiveOwnClaims" in prior) ? prior.defensiveOwnClaims : 0)
      + " project_preempt=" + (("preemptClaims" in project) ? project.preemptClaims : 0)
      + " prior_preempt=" + (("preemptClaims" in prior) ? prior.preemptClaims : 0)
      + " project_score=" + project[field] + " prior_score=" + prior[field]);
}

function OpexC122TraceShadow(winner, project, prior, projectC77Tier, priorC77Tier,
                             projectRegimeTier, priorRegimeTier, field)
{
  if (!C122_AIR_REGIME_SHADOW || C122_AIR_REGIME_PRIORITY || field != "fundScore") return;
  local projectArm = (("payload" in project) && project.payload != null
      && ("arm" in project.payload)) ? project.payload.arm : "none";
  local priorArm = (("payload" in prior) && prior.payload != null
      && ("arm" in prior.payload)) ? prior.payload.arm : "none";
  AILog.Info("C122_SHADOW regime=race reason=new_opex_slot_town winner=" + winner
      + " project_arm=" + projectArm + " prior_arm=" + priorArm
      + " c77_project=" + projectC77Tier + " c77_prior=" + priorC77Tier
      + " c122_project=" + projectRegimeTier + " c122_prior=" + priorRegimeTier
      + " project_new=" + (("defensiveNewTownClaims" in project) ? project.defensiveNewTownClaims : 0)
      + " prior_new=" + (("defensiveNewTownClaims" in prior) ? prior.defensiveNewTownClaims : 0)
      + " project_score=" + project[field] + " prior_score=" + prior[field]);
}

/* C122.3 diagnostic : mesurer l'exposition de defensiveNewTownClaims dans le
 * portefeuille deja finance/classe. La sonde reutilise c121_air_pressure_probe :
 * meme etat territorial, aucun nouveau scan. Elle tourne dans les deux bras des
 * smokes matched-shadow afin de ne pas creer un cout de mesure asymetrique.
 * `same_tier_blockers` compte les projets AIR sans nouvelle ville, deja devant le
 * meilleur candidat territorial dans la meme classe lexicographique C77/V88 ;
 * c'est exactement la population que C122 devrait depasser pour changer un choix. */
function OpexC122ProbeExposure(affordable)
{
  if (!C121_AIR_PRESSURE_PROBE || affordable == null) return;

  local airCount = 0;
  local newCount = 0;
  local potentialInversions = 0;
  local topAirGlobalRank = -1;
  local topAirScore = 0.0;
  local bestNewGlobalRank = -1;
  local bestNewAirRank = -1;
  local bestNewClaims = 0;
  local bestNewScore = 0.0;
  local bestNewTier = -1;
  local bestNewBlockers = 0;
  local plainAheadByTier = {};

  for (local i = 0; i < affordable.len(); i++) {
    local project = affordable[i];
    if (project == null || !("mode" in project) || project.mode != "air") continue;
    local airRank = airCount;
    airCount++;
    local tier = OpexProjectDefensiveAirPriority(project)
        + ((V88_CHAIN_FORCE && OpexProjectIsForcedChain(project)) ? 1000 : 0);
    local score = AIR_EARLY_SLOT ? OpexProjectSelectionScore(project, "fundScore")
        : project.fundScore;
    local newClaims = ("defensiveNewTownClaims" in project)
        ? project.defensiveNewTownClaims : 0;

    if (topAirGlobalRank < 0) {
      topAirGlobalRank = i;
      topAirScore = score;
    }

    if (newClaims > 0) {
      newCount++;
      local blockers = (tier in plainAheadByTier) ? plainAheadByTier[tier] : 0;
      if (blockers > 0) potentialInversions++;
      if (bestNewGlobalRank < 0) {
        bestNewGlobalRank = i;
        bestNewAirRank = airRank;
        bestNewClaims = newClaims;
        bestNewScore = score;
        bestNewTier = tier;
        bestNewBlockers = blockers;
      }
    } else {
      if (tier in plainAheadByTier) plainAheadByTier[tier]++;
      else plainAheadByTier.rawset(tier, 1);
    }
  }

  if (airCount <= 0) return;
  AILog.Info("C122_EXPOSURE date=" + AIDate.GetCurrentDate()
      + " air=" + airCount + " new=" + newCount
      + " potential_inversions=" + potentialInversions
      + " top_air_global_rank=" + topAirGlobalRank
      + " top_air_score=" + topAirScore
      + " best_new_global_rank=" + bestNewGlobalRank
      + " best_new_air_rank=" + bestNewAirRank
      + " best_new_claims=" + bestNewClaims
      + " best_new_score=" + bestNewScore
      + " best_new_tier=" + bestNewTier
      + " same_tier_blockers=" + bestNewBlockers
      + " promotions=" + C122_AIR_PROMOTION_COUNT);
}

/* Villes de slot d'un projet aerien pour les extremites neuves seulement.
 * Un hub reutilise (reuse) ne reserve pas sa ville. */
function OpexAirProjectNewSlotTowns(project)
{
  local towns = [];
  if (project == null || !("mode" in project) || project.mode != "air") return towns;
  if (!("payload" in project) || project.payload == null) return towns;
  local plan = project.payload;
  if (!("siteA" in plan) || plan.siteA == null || !("siteB" in plan) || plan.siteB == null) return towns;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (!reuseA) {
    local id = -1;
    if (("anchor" in plan.siteA)) id = OpexAirSlotTownId(plan.siteA.anchor);
    if (id < 0 && ("town" in plan.siteA) && plan.siteA.town != null && ("id" in plan.siteA.town)) {
      id = plan.siteA.town.id;
    }
    if (id >= 0) towns.append(id);
  }
  if (!reuseB) {
    local id = -1;
    if (("anchor" in plan.siteB)) id = OpexAirSlotTownId(plan.siteB.anchor);
    if (id < 0 && ("town" in plan.siteB) && plan.siteB.town != null && ("id" in plan.siteB.town)) {
      id = plan.siteB.town.id;
    }
    if (id >= 0) {
      local seen = false;
      foreach (prev in towns) if (prev == id) seen = true;
      if (!seen) towns.append(id);
    }
  }
  return towns;
}

/* Sonde d'exposition : retraits de la reserve, et batch_plan_dead encore observes.
 * Les compteurs ne bougent que si une sonde deja existante est armee. */
function OpexAirBatchTownReserveNote(kind, n)
{
  if (!C69_BOTTLENECK_PROBE && !C78_SLOT_INTERCEPT_PROBE) return;
  if (kind == "batch_plan_dead") {
    ::AIR_BATCH_TOWN_RESERVE_DEAD = AIR_BATCH_TOWN_RESERVE_DEAD + n;
  } else {
    ::AIR_BATCH_TOWN_RESERVE_DROPPED = AIR_BATCH_TOWN_RESERVE_DROPPED + n;
  }
  local fields = "phase=air_batch_town_reserve kind=" + kind + " n=" + n
      + " dropped=" + AIR_BATCH_TOWN_RESERVE_DROPPED
      + " batch_plan_dead=" + AIR_BATCH_TOWN_RESERVE_DEAD;
  if (C78_SLOT_INTERCEPT_PROBE) OpexC78SlotLog(fields);
  else OpexC69Log(fields);
}

/* Le classement est deja le meilleur d'abord. On garde le premier projet qui
 * ouvre chaque ville neuve. Les autres restent dans le vivier d'alternatives :
 * cette fonction ne touche que la liste financee passee en argument. */
function OpexAirBatchTownReserveCompact(best)
{
  if (!AIR_BATCH_TOWN_RESERVE || best == null) return 0;
  local claimed = {};
  local kept = [];
  local dropped = 0;
  foreach (project in best) {
    local towns = OpexAirProjectNewSlotTowns(project);
    local blocked = false;
    foreach (id in towns) {
      if (id in claimed) blocked = true;
    }
    if (blocked) {
      dropped++;
      continue;
    }
    foreach (id in towns) claimed.rawset(id, true);
    kept.append(project);
  }
  if (dropped <= 0) return 0;
  best.resize(0);
  foreach (project in kept) best.append(project);
  OpexAirBatchTownReserveNote("dropped", dropped);
  return dropped;
}

/* Vrai si une ville neuve de ce projet est deja prise par un projet mieux classe
 * de la meme passe. Sinon la ville est reservee pour ce projet. */
function OpexAirBatchTownReserveHit(claimed, project)
{
  if (claimed == null || project == null) return false;
  local towns = OpexAirProjectNewSlotTowns(project);
  foreach (id in towns) {
    if (id in claimed) return true;
  }
  foreach (id in towns) claimed.rawset(id, true);
  return false;
}

/* C116.2 : memoriser les trois premiers projets AIR deja finançables/classes.
 * Le cout est borne a PROJECT_TOP_K (64 par defaut), sans generation, economie
 * ni recherche de site supplementaire. Le snapshot sert au diagnostic moteur
 * de la generation AIR suivante et reste volontairement reconstructible. */
function OpexC116InsertPortfolioOpportunity(frontier, point)
{
  foreach (prior in frontier) {
    if (prior.gap <= point.gap && prior.hurdle >= point.hurdle) return;
  }
  for (local i = frontier.len() - 1; i >= 0; i--) {
    local prior = frontier[i];
    if (point.gap <= prior.gap && point.hurdle >= prior.hurdle) frontier.remove(i);
  }
  frontier.append(point);
}

function OpexC116ObserveAirPortfolioOpportunity(snapshot, project, financeCapital, capitalBudget)
{
  if (snapshot == null || project == null || !("mode" in project)) return;
  if (!("profitAnnual" in project) || project.profitAnnual <= 0 || financeCapital <= capitalBudget) return;
  local gap = financeCapital - capitalBudget;
  local hurdle = (project.profitAnnual.tofloat() * 1000.0) / financeCapital.tofloat();
  local point = { mode = project.mode, gap = gap, profit = project.profitAnnual, finance = financeCapital,
      hurdle = hurdle, roi = ("roi" in project) ? project.roi : 0.0,
      distance = ("distance" in project) ? project.distance : 0 };
  if (C104_AIR_C100_COMPARE_PROBE || C116_AIR_PROJECT_PROBE) {
    OpexC116InsertPortfolioOpportunity(snapshot.unlockableAny, point);
  }
  if (project.mode == "air") OpexC116InsertPortfolioOpportunity(snapshot.unlockable, point);
}

function OpexC116RememberAirPortfolioOpportunity(affordable, capitalBudget, snapshot)
{
  if (!C104_AIR_C100_COMPARE_PROBE && !C116_AIR_MARGINAL_CAPITAL && !C116_AIR_PROJECT_PROBE) return;
  if (snapshot == null) snapshot = { date = AIDate.GetCurrentDate(), budget = capitalBudget,
      topMode = "none", top = null, air = [], unlockable = [], unlockableAny = [] };
  if ((C104_AIR_C100_COMPARE_PROBE || C116_AIR_PROJECT_PROBE)
      && affordable != null && affordable.len() > 0) {
    local top = affordable[0];
    if (top != null && ("mode" in top)) {
      snapshot.topMode = top.mode;
      local topFinance = OpexProjectFinanceCapital(top);
      snapshot.top = {
        mode = top.mode,
        profit = ("profitAnnual" in top) ? top.profitAnnual : 0,
        finance = topFinance,
        hurdle = (topFinance > 0 && ("profitAnnual" in top) && top.profitAnnual > 0)
            ? (top.profitAnnual.tofloat() * 1000.0) / topFinance.tofloat() : 0.0,
        score = ("fundScore" in top) ? top.fundScore : 0.0,
      };
    }
    for (local i = 0; i < affordable.len() && snapshot.air.len() < 3; i++) {
      local project = affordable[i];
      if (project == null || !("mode" in project) || project.mode != "air") continue;
      snapshot.air.append({
        rank = i,
        profit = ("profitAnnual" in project) ? project.profitAnnual : 0,
        finance = OpexProjectFinanceCapital(project),
        score = ("fundScore" in project) ? project.fundScore : 0.0,
        roi = ("roi" in project) ? project.roi : 0.0,
        distance = ("distance" in project) ? project.distance : 0,
      });
    }
  }
  C116_AIR_PROJECT_SNAPSHOT = snapshot;
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
function OpexProjectFitFleetToBudget(project, capitalBudget)
{
  if (project == null || project.mode != "fleet") return project;
  local entry = project.payload;
  local line = entry.line;
  if (line == null || (("scrapping" in line) && line.scrapping)) return null;
  local have = ("vehCount" in line) ? line.vehCount : line.vehicles.len();
  if (("baseVehicles" in entry) && have != entry.baseVehicles) return null;
  if (C121_AIR_ECONOMICS && C121_AIR_TARGET_LIMIT
      && (!("targetAirPlanes" in line) || have + entry.want > line.targetAirPlanes)) return null;
  local purchaseBudget = capitalBudget - 1000; // tampon d'OpexAirAddPlane
  if (entry.planePrice <= 0 || entry.want <= 0 || purchaseBudget < entry.planePrice) return null;
  local quantity = (purchaseBudget / entry.planePrice).tointeger();
  if (quantity >= entry.want) return project;

  /* Une seule tranche par demande, jamais des +1 concurrents pour la meme ligne.
   * Ne pas modifier le vivier : une reelection avec davantage de capital doit
   * encore voir la demande complete. R2 : conserver la provenance du profit. */
  local fitted = clone project;
  local reduced = clone entry;
  reduced.want = quantity;
  fitted.payload = reduced;
  fitted.capital = quantity * entry.planePrice;
  fitted.budgetCapital = fitted.capital + 1000;
  local c121BelowTarget = C121_AIR_ECONOMICS && ("targetAirPlanes" in line)
      && line.targetAirPlanes > have;
  if (!c121BelowTarget && C84_AIR_TARGET_FLEET && ("targetAirPlanes" in line)
      && line.targetAirPlanes > have) {
    /* La courbe C84 n'est pas lineaire : recalculer have -> have+quantity,
     * et non multiplier la marge du lot complet par une fraction. */
    if (!("c84Catalog" in entry)) return null;
    local marginal = OpexAirExistingLineMarginalEconomics(entry.c84Catalog, line, have, quantity);
    if (marginal == null || marginal.profitAnnual <= 0) return null;
    reduced.c84MarginalProfit <- marginal.profitAnnual;
    reduced.c84MarginalRevenue <- marginal.revenueAnnual;
    fitted.profitAnnual = marginal.profitAnnual;
    fitted.revenueAnnual = marginal.revenueAnnual > 0 ? marginal.revenueAnnual : marginal.profitAnnual;
  } else {
    fitted.profitAnnual = (project.profitAnnual / entry.want) * quantity;
    fitted.revenueAnnual = (project.revenueAnnual / entry.want) * quantity;
  }
  if (fitted.profitAnnual <= 0) return null;
  fitted.roi = (fitted.profitAnnual * 1000) / fitted.capital;
  fitted.budgetScore = OpexProjectScore(fitted.revenueAnnual, fitted.budgetCapital);
  fitted.opcodeScore = OpexProjectScore(fitted.revenueAnnual, fitted.expectedOpcodes);
  return fitted;
}

/* C121 split : le plancher absolu continue de lire project.profitAnnual, qui
 * represente la valeur long terme max-profit. Seul le classement fundScore peut
 * consommer la profondeur portfolio. La calibration C70/C82 est multiplicative
 * pour un meme projet/moteur : appliquer au profit portfolio le meme facteur que
 * celui mesure sur le profit long terme preserve exactement ce calibrage. */
function OpexProjectFundProfit(project)
{
  local calibMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  local calibrated = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(project) : project.profitAnnual;
  if (calibMark != null) OpexSpanAgg("pub.select.calibrate", calibMark);
  return calibrated;
}

/* C121 cadence : mesurer le biais de cold-start K_dec sans toucher au projet
 * vivant. Le builder marque explicitement samples<=0 comme non observe ; la
 * presence de c121MarginalProfit/Revenue seule ne constitue donc pas une
 * realisation. On capture ici le score contrefactuel qui conserverait
 * l'exemption C69 jusqu'au premier sample reel. */
function OpexC121KDecColdShadowCandidate(rows, project, financeCapital, kDec)
{
  if (rows == null || project == null || !("mode" in project) || project.mode != "fleet"
      || !("payload" in project) || project.payload == null || !("line" in project.payload)
      || project.payload.line == null) return;
  local line = project.payload.line;
  if (!("mode" in line) || line.mode != "air") return;
  if (!("c121MarginalProfit" in line) || !("c121MarginalRevenue" in line)) return;

  local samples = ("c121MarginalSamples" in line) ? line.c121MarginalSamples : 0;
  local currentExempt = C69_FLEET_EXEMPT && !OpexC121ProjectHasRealization(project);
  local currentDenom = (C69_DECISION_BOTTLENECK && kDec > financeCapital && !currentExempt)
      ? kDec : financeCapital;
  local coldExempt = C69_FLEET_EXEMPT && samples <= 0;
  local coldDenom = (C69_DECISION_BOTTLENECK && kDec > financeCapital && !coldExempt)
      ? kDec : financeCapital;
  local profit = OpexProjectFundProfit(project);
  local currentScore = ("fundScore" in project) ? project.fundScore
      : OpexProjectScore(profit, currentDenom);
  local coldScore = samples <= 0 ? OpexProjectScore(profit, coldDenom) : currentScore;
  rows.append({ project = project, samples = samples, finance = financeCapital,
      currentDenom = currentDenom, coldDenom = coldDenom,
      currentScore = currentScore, coldScore = coldScore });
}

/* Reutilise l'ordre deja trie et ne reinserre que le seul candidat cold dans une
 * copie superficielle bornee a PROJECT_TOP_K. Ce n'est pas un second tri du
 * catalogue et aucun champ du portefeuille vivant n'est modifie. */
function OpexC121KDecColdShadowEnd(rows, affordable, limit, kDec)
{
  if (!C121_KDEC_COLD_SHADOW || rows == null) return;
  local cold = 0;
  local warm = 0;
  local affected = 0;
  local rankUp = 0;
  local entered = 0;
  local headFlip = 0;
  /* Date de la passe, commune aux candidats et au resume. L'horodatage moteur
   * est celui du PC, pas celui de la partie. Aucun OpexDecide (etat TASK). */
  local date = AIDate.GetCurrentDate();
  local stamp = " year=" + AIDate.GetYear(date) + " month=" + AIDate.GetMonth(date)
      + " day=" + AIDate.GetDayOfMonth(date);
  local headMode = (affordable != null && affordable.len() > 0 && ("mode" in affordable[0]))
      ? affordable[0].mode : "none";

  foreach (row in rows) {
    local project = row.project;
    local currentRank = -1;
    if (affordable != null) {
      for (local i = 0; i < affordable.len(); i++) {
        if (affordable[i] == project) { currentRank = i; break; }
      }
    }
    local coldRank = currentRank;
    local changed = row.samples <= 0 && row.coldDenom != row.currentDenom;
    if (row.samples <= 0) cold++;
    else warm++;

    if (changed && affordable != null) {
      affected++;
      local shadowOrder = [];
      for (local i = 0; i < affordable.len(); i++) {
        if (i != currentRank) shadowOrder.append(affordable[i]);
      }
      local shadowProject = clone project;
      shadowProject.fundScore = row.coldScore;
      OpexProjectInsertDefensive(shadowOrder, shadowProject, "fundScore", limit, AIR_EARLY_SLOT);
      coldRank = -1;
      for (local i = 0; i < shadowOrder.len(); i++) {
        if (shadowOrder[i] == shadowProject) { coldRank = i; break; }
      }
      if (coldRank >= 0 && (currentRank < 0 || coldRank < currentRank)) rankUp++;
      if (currentRank < 0 && coldRank >= 0) entered++;
      if (currentRank != 0 && coldRank == 0) headFlip++;
    }

    local line = project.payload.line;
    local lineId = ("lineId" in line) ? line.lineId : -1;
    AILog.Info("C121_KDEC_COLD_SHADOW state=" + (row.samples <= 0 ? "cold" : "warm")
        + " line=" + lineId + " samples=" + row.samples
        + " finance=" + row.finance + " k_dec=" + kDec
        + " denom=" + row.currentDenom + " cold_denom=" + row.coldDenom
        + " score=" + row.currentScore + " cold_score=" + row.coldScore
        + " rank=" + currentRank + " cold_rank=" + coldRank
        + " affected=" + (changed ? 1 : 0)
        + " head_flip=" + ((currentRank != 0 && coldRank == 0) ? 1 : 0) + stamp);
  }
  AILog.Info("C121_KDEC_COLD_SUMMARY cold=" + cold + " warm=" + warm
      + " affected=" + affected + " rank_up=" + rankUp + " entered=" + entered
      + " head_flip=" + headFlip + " head_mode=" + headMode + " k_dec=" + kDec + stamp);
}

function OpexProjectSelectAffordable(alternatives, capitalBudget, limit)
{
  local spSelect = PROBE_SPAN_TRACE ? OpexSpanBegin("select.full") : null;
  local amortProbe = FLEET_AMORT_SHADOW_PROBE > 0 ? OpexAmortProbeBegin(capitalBudget) : null;
  local c121KDecColdRows = C121_KDEC_COLD_SHADOW ? [] : null;
  /* R1 : dimensionnement AVANT plancher, sondes et classement commun a tous
   * les modes. Le budget fourni a deja soustrait la reserve de tresorerie. */
  local fittedAlternatives = [];
  foreach (project in alternatives) {
    local fitMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    local fitted = OpexProjectFitFleetToBudget(project, capitalBudget);
    if (R1_R3_TEST_ONLY) fitted = OpexR1R3FitTrace(project, fitted, capitalBudget);
    if (amortProbe != null && fitted != null && project.mode == "fleet")
      amortProbe.originals.append({ project = fitted, quantity = project.payload.want });
    if (fitted != null) fittedAlternatives.append(fitted);
    if (fitMark != null) OpexSpanAgg("pub.select.score.fit", fitMark);
  }
  alternatives = fittedAlternatives;
  local spStates = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.score.states") : null;
  /* Avant plancher, preparation territoriale et filtre. */
  OpexC118PrepareSelection(alternatives, capitalBudget);
  OpexC120PrepareSelection(alternatives, capitalBudget);
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
  local floorProfit = 0;
  if (PORTFOLIO_FLOOR_PCT > 0) {
    local bestProfit = 0;
    foreach (project in alternatives) {
      local financeCapital = OpexProjectFinanceCapital(project);
      if (financeCapital > capitalBudget) continue;
      if (project.profitAnnual > bestProfit) bestProfit = project.profitAnnual;
    }
    if (bestProfit > 0) floorProfit = bestProfit * PORTFOLIO_FLOOR_PCT / 100;
  }

  local affordable = [];
  local c116Snapshot = (C104_AIR_C100_COMPARE_PROBE || C116_AIR_MARGINAL_CAPITAL || C116_AIR_PROJECT_PROBE)
      ? { date = AIDate.GetCurrentDate(), budget = capitalBudget,
          topMode = "none", top = null, air = [], unlockable = [], unlockableAny = [] }
      : null;
  local earlySlotState = AIR_EARLY_SLOT ? OpexEarlySlotSelectionState() : null;
  local defensiveSlotState = OpexDefensiveSlotSelectionState(earlySlotState);
  local scoreKey = "fundScore";
  local c111DecisionShadow = C111_AIR_C100_DECISION_SHADOW;

  local kDec = 0;
  local kDecData = null;
  local c69Affordable = null;
  local airPairBest = {};
  if (C69_TRACK_BUILDS) {
    kDecData = OpexC69ComputeKDec();
    kDec = kDecData.K_dec;
    if (C69_BOTTLENECK_PROBE) c69Affordable = [];
  }
  if (spStates != null) OpexSpanEnd(spStates);

  foreach (project in alternatives) {
    local fundMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    local slotMark = null;
    local insertMark = null;
    local financeCapital = OpexProjectFinanceCapital(project);
    OpexC116ObserveAirPortfolioOpportunity(c116Snapshot, project, financeCapital, capitalBudget);
    local c118Territorial = C118_AIR_TERRITORIAL_EXPANSION && project.mode == "air"
        && (("c118NewTowns") in project) && project.c118NewTowns > 0;
    if (c118Territorial && ("c118MinFinance" in project) && project.c118MinFinance > 0) {
      financeCapital = project.c118MinFinance;
    }
    if (fundMark != null) {
      OpexSpanAgg("pub.select.score.fund_score", fundMark);
      fundMark = null;
    }
    if (financeCapital > capitalBudget) continue;
    local c121DefensivePrepared = C121_AIR_ECONOMICS && C121_AIR_DEFENSIVE_FLOOR
        && project.mode == "air";
    local c121DefensiveTier = 0;
    local c121DefensiveFloor = floorProfit;
    if (c121DefensivePrepared) {
      slotMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      if (AIR_EARLY_SLOT) OpexProjectRefreshEarlySlot(project, earlySlotState);
      OpexProjectRefreshDefensiveSlot(project, defensiveSlotState);
      if (slotMark != null) {
        OpexSpanAgg("pub.select.score.refresh_slots", slotMark);
        slotMark = null;
      }
      fundMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      c121DefensiveTier = OpexProjectDefensiveAirPriority(project);
      /* C121 anti-monopole : ne plus supprimer completement le garde-fou de
       * profit. Une course au second slot concurrent (tier 2) accepte la moitie
       * du plancher normal ; consolider notre propre slot (tier 1) en exige les
       * trois quarts. Les projets ordinaires gardent le floor integral. */
      if (c121DefensiveTier >= 2) c121DefensiveFloor = floorProfit / 2;
      else if (c121DefensiveTier == 1) c121DefensiveFloor = floorProfit * 3 / 4;
    }
    if (project.profitAnnual < c121DefensiveFloor && !c118Territorial
        && !(V88_CHAIN_FORCE && OpexProjectIsForcedChain(project))) {
      if (fundMark != null) {
        OpexSpanAgg("pub.select.score.fund_score", fundMark);
        fundMark = null;
      }
      continue;
    }
    if (!c121DefensivePrepared) {
      slotMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      if (AIR_EARLY_SLOT) OpexProjectRefreshEarlySlot(project, earlySlotState);
      OpexProjectRefreshDefensiveSlot(project, defensiveSlotState);
      if (slotMark != null) {
        OpexSpanAgg("pub.select.score.refresh_slots", slotMark);
        slotMark = null;
      }
      fundMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    }
    local decisionFinanceCapital = financeCapital;
    if (project.mode == "air" && ("decisionFinanceCapital" in project)
        && project.decisionFinanceCapital > 0) decisionFinanceCapital = project.decisionFinanceCapital;
    local scoreDecisionFinanceCapital = decisionFinanceCapital;
    /* C121 : un renfort d'avion est un vrai projet economique concurrent d'une
     * nouvelle ligne. L'exemption historique C69 lui donnerait un denominateur
     * ~= prix avion alors que les lignes AIR sont bornees par K_dec, ce qui
     * surclasse artificiellement les +1 avion. Conserver l'exemption pour les
     * chemins legacy/C84, mais pas pour une flotte portant une marge C121. */
    local fleetExemptDecision = C69_FLEET_EXEMPT && project.mode == "fleet"
        && !OpexC121ProjectHasRealization(project);
    project.fundScore <- OpexProjectScore(OpexProjectFundProfit(project),
        (C69_DECISION_BOTTLENECK && kDec > scoreDecisionFinanceCapital && !fleetExemptDecision)
            ? kDec : scoreDecisionFinanceCapital);
    OpexC121KDecColdShadowCandidate(c121KDecColdRows, project, financeCapital, kDec);
    if (C121_CATALOG_INCREMENTAL && project.mode == "air"
        && ("payload" in project) && project.payload != null
        && ("c121CatalogKey" in project.payload)
        && project.payload.c121CatalogKey in C121_CATALOG_CACHE)
      C121_CATALOG_CACHE[project.payload.c121CatalogKey].lastScore = project.fundScore;
    if (fundMark != null) {
      OpexSpanAgg("pub.select.score.fund_score", fundMark);
      fundMark = null;
    }
    insertMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    if (C69_BOTTLENECK_PROBE) {
      local denom = financeCapital > kDec ? financeCapital : kDec;
      project.c69Score <- OpexProjectScore(OpexCalibratedProfit(project), denom);
      OpexProjectInsertDefensive(c69Affordable, project, "c69Score", limit, AIR_EARLY_SLOT);
    }
    if (amortProbe != null) OpexAmortProbeCandidate(amortProbe, project, financeCapital,
      (C69_DECISION_BOTTLENECK && kDec > scoreDecisionFinanceCapital && !fleetExemptDecision)
          ? kDec : scoreDecisionFinanceCapital);
    if (AIR_EFFICIENCY_DEDUPE && project.mode == "air") {
      local pairKey = OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
      if (pairKey in airPairBest) {
        local prior = airPairBest[pairKey];
        local pairBest = [prior];
        OpexProjectInsertDefensive(pairBest, project, scoreKey, 1, AIR_EARLY_SLOT);
        if (pairBest[0] != prior) {
          airPairBest[pairKey] = pairBest[0];
          for (local ai = affordable.len() - 1; ai >= 0; ai--) {
            if (affordable[ai] == prior) { affordable.remove(ai); break; }
          }
          OpexProjectInsertDefensive(affordable, pairBest[0], scoreKey, limit, AIR_EARLY_SLOT);
        }
      } else {
        airPairBest.rawset(pairKey, project);
        OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);
      }
    } else {
      OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);
    }
    if (insertMark != null) {
      OpexSpanAgg("pub.select.score.insert", insertMark);
      insertMark = null;
    }
  }
  /* Filet de securite : si le plancher a tout ecarte -- il ne le peut pas puisque le meilleur
   * projet l'atteint par construction, mais un profitAnnual nul ou negatif rendrait bestProfit nul
   * et le plancher inoperant -- on retombe sur l'ensemble finançable brut plutot que de ne rien
   * batir du tout. */
  if (affordable.len() == 0 && floorProfit > 0) {
    if (amortProbe != null) amortProbe.rows = [];
    if (C69_BOTTLENECK_PROBE) c69Affordable = [];
    airPairBest = {};
    if (c121KDecColdRows != null) c121KDecColdRows.clear();
    foreach (project in alternatives) {
      local fundMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      local slotMark = null;
      local insertMark = null;
      local c118Territorial = C118_AIR_TERRITORIAL_EXPANSION && project.mode == "air"
          && (("c118NewTowns") in project) && project.c118NewTowns > 0;
      local normalFinanceCapital = OpexProjectFinanceCapital(project);
      local financeCapital = (c118Territorial && ("c118MinFinance" in project)
          && project.c118MinFinance > 0) ? project.c118MinFinance : normalFinanceCapital;
      if (fundMark != null) {
        OpexSpanAgg("pub.select.score.fund_score", fundMark);
        fundMark = null;
      }
      if (financeCapital > capitalBudget) continue;
      slotMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      if (AIR_EARLY_SLOT) OpexProjectRefreshEarlySlot(project, earlySlotState);
      OpexProjectRefreshDefensiveSlot(project, defensiveSlotState);
      if (slotMark != null) {
        OpexSpanAgg("pub.select.score.refresh_slots", slotMark);
        slotMark = null;
      }
      fundMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      local decisionFinanceCapital = financeCapital;
      if (project.mode == "air" && ("decisionFinanceCapital" in project)
          && project.decisionFinanceCapital > 0) decisionFinanceCapital = project.decisionFinanceCapital;
      local scoreDecisionFinanceCapital = decisionFinanceCapital;
      local fleetExemptDecision = C69_FLEET_EXEMPT && project.mode == "fleet"
          && !OpexC121ProjectHasRealization(project);
      project.fundScore <- OpexProjectScore(OpexProjectFundProfit(project),
          (C69_DECISION_BOTTLENECK && kDec > scoreDecisionFinanceCapital && !fleetExemptDecision)
              ? kDec : scoreDecisionFinanceCapital);
      OpexC121KDecColdShadowCandidate(c121KDecColdRows, project, financeCapital, kDec);
      if (fundMark != null) {
        OpexSpanAgg("pub.select.score.fund_score", fundMark);
        fundMark = null;
      }
      insertMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      if (C69_BOTTLENECK_PROBE) {
        local denom = financeCapital > kDec ? financeCapital : kDec;
        project.c69Score <- OpexProjectScore(OpexCalibratedProfit(project), denom);
        OpexProjectInsertDefensive(c69Affordable, project, "c69Score", limit, AIR_EARLY_SLOT);
      }
        if (amortProbe != null) OpexAmortProbeCandidate(amortProbe, project, financeCapital,
          (C69_DECISION_BOTTLENECK && kDec > scoreDecisionFinanceCapital && !fleetExemptDecision)
              ? kDec : scoreDecisionFinanceCapital);
        if (AIR_EFFICIENCY_DEDUPE && project.mode == "air") {
          local pairKey = OpexProjectPairKey(project.kind, project.cargo, project.src, project.dst);
          if (pairKey in airPairBest) {
            local prior = airPairBest[pairKey];
            local pairBest = [prior];
            OpexProjectInsertDefensive(pairBest, project, scoreKey, 1, AIR_EARLY_SLOT);
            if (pairBest[0] != prior) {
              airPairBest[pairKey] = pairBest[0];
              for (local ai = affordable.len() - 1; ai >= 0; ai--) {
                if (affordable[ai] == prior) { affordable.remove(ai); break; }
              }
              OpexProjectInsertDefensive(affordable, pairBest[0], scoreKey, limit, AIR_EARLY_SLOT);
            }
          } else {
            airPairBest.rawset(pairKey, project);
            OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);
          }
        } else {
          OpexProjectInsertDefensive(affordable, project, scoreKey, limit, AIR_EARLY_SLOT);
        }
      if (insertMark != null) {
        OpexSpanAgg("pub.select.score.insert", insertMark);
        insertMark = null;
      }
    }
  }
  local spEpilogue = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.score.epilogue") : null;
  if (amortProbe != null) OpexAmortProbeEnd(amortProbe, affordable);
  OpexC121KDecColdShadowEnd(c121KDecColdRows, affordable, limit, kDec);
  OpexC122ProbeExposure(affordable);
  OpexC120ReorderAffordableAir(affordable);
  if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveCompact(affordable);
  if (C69_BOTTLENECK_PROBE) {
    ::C69_LAST_AFFORDABLE = c69Affordable;
    ::C69_LAST_KDEC_DATA = kDecData;
    local toSel = { rail = 0, road = 0, air = 0, water = 0, fleet = 0 };
    local aff = { rail = 0, road = 0, air = 0, water = 0, fleet = 0 };
    local sel = { rail = 0, road = 0, air = 0, water = 0, fleet = 0 };
    foreach (p in alternatives) {
      local m = ("mode" in p) ? p.mode : "unknown";
      if (m in toSel) toSel[m]++;
      local fc = OpexProjectFinanceCapital(p);
      if (fc <= capitalBudget && (floorProfit <= 0 || p.profitAnnual >= floorProfit)) {
        if (m in aff) aff[m]++;
      }
    }
    foreach (p in affordable) {
      local m = ("mode" in p) ? p.mode : "unknown";
      if (m in sel) sel[m]++;
    }
    OpexC73RecordSelection(toSel, aff, sel);
  }
  OpexC120FinalizeSelection(affordable, capitalBudget);
  OpexC121RecordPressureSnapshot(defensiveSlotState);
  OpexC116RememberAirPortfolioOpportunity(affordable, capitalBudget, c116Snapshot);
  if (R1_R3_TEST_ONLY) {
    foreach (project in alternatives) {
      if (!("r1r3Id" in project)) continue;
      local rank = -1;
      for (local k = 0; k < affordable.len(); k++) {
        if (affordable[k] == project) { rank = k; break; }
      }
      OpexR1R3Log("mechanism=R1 phase=rank id=" + project.r1r3Id
          + " rank=" + rank + " score=" + (("fundScore" in project) ? project.fundScore : "unknown")
          + " finance=" + OpexProjectFinanceCapital(project) + " budget=" + capitalBudget);
    }
  }
  if (PROBE_AIR_FINANCE_MARGIN) OpexAirFinanceMarginLogSelect(alternatives, affordable, capitalBudget);
  if (spEpilogue != null) OpexSpanEnd(spEpilogue);
  if (spSelect != null) OpexSpanEnd(spSelect);
  return affordable;
}

/* Early-slot ne falsifie ni profitAnnual ni revenueAnnual. Le bonus n'existe
 * qu'au moment du classement, afin de payer temporairement une prime strategique
 * pour securiser des slots aeroportuaires dans les grandes villes. */
function OpexProjectSelectionScore(project, field)
{
  if (project == null) return 0.0;
  local score = project[field];
  if (!AIR_EARLY_SLOT || !("mode" in project) || project.mode != "air") return score;
  if (!("earlySlotBonusPct" in project)) return score;
  local bonusPct = project.earlySlotBonusPct;
  if (bonusPct <= 0) return score;
  local factor = (100.0 + bonusPct.tofloat()) / 100.0;
  return score * factor;
}

/* V88 test (v88_chain_force) : projet chaine force en tete du classement. */
function OpexProjectIsForcedChain(project)
{
  return V88_CHAIN_FORCE && project != null && ("isChain" in project) && project.isChain;
}

/* Insertion bornee et stable avec classe defensive C77 permanente. */
function OpexProjectInsertDefensive(best, project, field, limit, applyEarlySlot = false)
{
  local projectC77Tier = OpexProjectDefensiveAirPriority(project);
  local projectTier = projectC77Tier
      + ((V88_CHAIN_FORCE && OpexProjectIsForcedChain(project)) ? 1000 : 0);
  local projectScore = applyEarlySlot ? OpexProjectSelectionScore(project, field) : project[field];
  local pos = best.len();
  while (pos > 0) {
    local prior = best[pos - 1];
    local priorC77Tier = OpexProjectDefensiveAirPriority(prior);
    local priorTier = priorC77Tier
        + ((V88_CHAIN_FORCE && OpexProjectIsForcedChain(prior)) ? 1000 : 0);
    local c118Active = C118_AIR_TERRITORIAL_EXPANSION
        && C118_AIR_PROJECT_SNAPSHOT != null
        && ("active" in C118_AIR_PROJECT_SNAPSHOT) && C118_AIR_PROJECT_SNAPSHOT.active;
    if (c118Active) {
      local projectAir = ("mode" in project) && project.mode == "air";
      local priorAir = ("mode" in prior) && prior.mode == "air";
      local projectNew = ("c118NewTowns" in project) ? project.c118NewTowns : 0;
      local priorNew = ("c118NewTowns" in prior) ? prior.c118NewTowns : 0;
      if (projectNew > 0 || priorNew > 0) {
        if (priorNew > projectNew) break;
        if (priorNew < projectNew) {
          pos--;
          continue;
        }
      }
      if (projectAir && priorAir) {
        local projectDays = ("c118NextDays" in project) ? project.c118NextDays : -1.0;
        local priorDays = ("c118NextDays" in prior) ? prior.c118NextDays : -1.0;
        if (projectDays >= 0 && priorDays >= 0 && priorDays != projectDays) {
          if (priorDays < projectDays) break;
          pos--;
          continue;
        }
        if (priorDays >= 0 && projectDays < 0) break;
        if (priorDays < 0 && projectDays >= 0) {
          pos--;
          continue;
        }
        local projectProfit = ("c118C68Profit" in project) ? project.c118C68Profit : project.profitAnnual;
        local priorProfit = ("c118C68Profit" in prior) ? prior.c118C68Profit : prior.profitAnnual;
        if (priorProfit > projectProfit) break;
        if (priorProfit < projectProfit) {
          pos--;
          continue;
        }
        local projectRoi = ("c118C68Roi" in project) ? project.c118C68Roi : project.roi;
        local priorRoi = ("c118C68Roi" in prior) ? prior.c118C68Roi : prior.roi;
        if (priorRoi > projectRoi) break;
        if (priorRoi < projectRoi) {
          pos--;
          continue;
        }
      }
    }
    if (priorTier > projectTier) break;
    if (priorTier < projectTier) {
      pos--;
      continue;
    }
    local priorScore = applyEarlySlot ? OpexProjectSelectionScore(prior, field) : prior[field];
    local projectAir = ("mode" in project) && project.mode == "air";
    local priorAir = ("mode" in prior) && prior.mode == "air";
    /* Ne payer/comparer C122 qu'une fois le regime race verrouille. Le shadow
     * execute la meme comparaison mais laisse ensuite l'ordre economique intact. */
    if ((C122_AIR_REGIME_PRIORITY || C122_AIR_REGIME_SHADOW)
        && C121_AIR_PROJECT_REALIZATION_REGIME == 0 && projectAir && priorAir) {
      local projectRegimeTier = OpexC122AirRegimeTier(project);
      local priorRegimeTier = OpexC122AirRegimeTier(prior);
      local economicKeepsPrior = priorScore > projectScore
          || (priorScore == projectScore && prior.revenueAnnual >= project.revenueAnnual);
      if (C122_AIR_REGIME_SHADOW && !C122_AIR_REGIME_PRIORITY) {
        if (priorRegimeTier > projectRegimeTier && !economicKeepsPrior) {
          OpexC122TraceShadow("prior", project, prior, projectC77Tier, priorC77Tier,
              projectRegimeTier, priorRegimeTier, field);
        } else if (priorRegimeTier < projectRegimeTier && economicKeepsPrior) {
          OpexC122TraceShadow("project", project, prior, projectC77Tier, priorC77Tier,
              projectRegimeTier, priorRegimeTier, field);
        }
      } else if (priorRegimeTier > projectRegimeTier) {
        if (!economicKeepsPrior) {
          OpexC122TracePromotion("prior", project, prior, projectC77Tier, priorC77Tier,
              projectRegimeTier, priorRegimeTier, field);
        }
        break;
      } else if (priorRegimeTier < projectRegimeTier) {
        if (economicKeepsPrior) {
          OpexC122TracePromotion("project", project, prior, projectC77Tier, priorC77Tier,
              projectRegimeTier, priorRegimeTier, field);
        }
        pos--;
        continue;
      }
    }
    if (priorScore > projectScore) break;
    if (priorScore == projectScore && prior.revenueAnnual >= project.revenueAnnual) break;
    pos--;
  }
  best.insert(pos, project);
  if (best.len() > limit) best.pop();
}

/* C78 / course defensive live : `best` peut survivre plusieurs passages projects
 * sans repasser par OpexReselectProjects. Rafraichir uniquement ce petit ensemble
 * deja finance (PROJECT_TOP_K, 64 par defaut) permet donc de reagir a l'arrivee
 * d'un premier aeroport concurrent sans regenerer ni rescanner tout le vivier.
 * Les projets non AIR gardent leur ordre ; parmi les AIR defensifs, on conserve le
 * meme score/tie-break que la selection finale. */
function OpexPromoteLiveDefensiveAir(projects, capitalBudget)
{
  if (projects == null || !("best" in projects)
      || projects.best == null || projects.best.len() == 0) return null;
  /* C120 a deja classe le petit portefeuille finance. Ne laisser la promotion
   * defensive court-circuiter cet ordre que lorsqu'il n'existe PAS de tete
   * territoriale ; dans ce cas le comportement C115 reste strictement normal. */
  if (C120_AIR_TERRITORIAL_RANKING
      && ("c120NewTowns" in projects.best[0]) && projects.best[0].c120NewTowns > 0) {
    return projects.best[0];
  }
  /* C118 a deja impose son ordre lexicographique sur ce meme petit portefeuille.
   * Une promotion defensive executee ensuite contournerait l'objectif territorial
   * (et peut remettre un projet newTowns=0 devant un projet expansif). Tant que
   * le snapshot contient au moins une opportunite territoriale, garder la tete
   * C118 telle quelle. Des que la frontiere devient vide, le comportement
   * defensif historique reprend naturellement. */
  if (C118_AIR_TERRITORIAL_EXPANSION && C118_AIR_PROJECT_SNAPSHOT != null
      && ("active" in C118_AIR_PROJECT_SNAPSHOT) && C118_AIR_PROJECT_SNAPSHOT.active) {
    return projects.best[0];
  }

  local earlyState = null;
  local defensiveState = null;
  local bestIndex = -1;
  local bestTier = 0;
  local bestScore = 0.0;
  local bestRevenue = 0;
  local limit = projects.best.len() < PROJECT_TOP_K ? projects.best.len() : PROJECT_TOP_K;

  for (local i = 0; i < limit; i++) {
    local project = projects.best[i];
    if (project == null || !("mode" in project) || project.mode != "air") continue;
    if (!("profitAnnual" in project) || project.profitAnnual <= 0) continue;
    if (OpexProjectFinanceCapital(project) > capitalBudget) continue;

    if (defensiveState == null) {
      if (AIR_EARLY_SLOT) earlyState = OpexEarlySlotSelectionState();
      defensiveState = OpexDefensiveSlotSelectionState(earlyState);
    }
    if (AIR_EARLY_SLOT) OpexProjectRefreshEarlySlot(project, earlyState);
    OpexProjectRefreshDefensiveSlot(project, defensiveState);
    local tier = OpexProjectDefensiveAirPriority(project);
    if (tier <= 0) continue;

    local score = ("fundScore" in project)
        ? OpexProjectSelectionScore(project, "fundScore") : project.budgetScore;
    local revenue = ("revenueAnnual" in project) ? project.revenueAnnual : 0;
    if (bestIndex < 0 || tier > bestTier
        || (tier == bestTier && (score > bestScore
            || (score == bestScore && revenue > bestRevenue)))) {
      bestIndex = i;
      bestTier = tier;
      bestScore = score;
      bestRevenue = revenue;
    }
  }

  if (bestIndex < 0) return null;
  local chosen = projects.best[bestIndex];
  if (bestIndex > 0) {
    projects.best.remove(bestIndex);
    projects.best.insert(0, chosen);
    if (C78_SLOT_INTERCEPT_PROBE) {
      local defensiveTownA = ("defensiveSlotTownA" in chosen) ? chosen.defensiveSlotTownA : -1;
      local defensiveTownB = ("defensiveSlotTownB" in chosen) ? chosen.defensiveSlotTownB : -1;
      OpexC78SlotLog("phase=defensive_priority action=promote from_rank=" + bestIndex
          + " tick=" + AIController.GetTick()
          + " finance=" + OpexProjectFinanceCapital(chosen)
          + " tier=" + bestTier
          + " townA=" + defensiveTownA + " townB=" + defensiveTownB
          + " defensive_claims=" + chosen.defensiveSlotClaims
          + " competitor_claims=" + (("defensiveCompetitorClaims" in chosen)
              ? chosen.defensiveCompetitorClaims : 0)
          + " own_claims=" + (("defensiveOwnClaims" in chosen) ? chosen.defensiveOwnClaims : 0));
    }
  }
  return chosen;
}

/* Active uniquement au demarrage sous les deux reglages C80. Le point d'appel
 * existant dans projects re-selectionne alors le registre courant avant C78. */
function OpexPromoteLiveDefensiveAirStock(projects, capitalBudget)
{
  if (projects != null && ("candidateGroups" in projects) && ("railStockAI" in projects)) {
    local ai = projects.railStockAI;
    ai._checkRailStockExpiry();
    OpexReselectProjects(projects, capitalBudget, ai._abandonedPairs, ai._lines, ai._railReadyStock);
    ai._updateRailStockSelectionThreshold();
    if (C56_TASK_TRACE) {
      local funded = 0;
      foreach (p in projects.best) if (p.mode == "rail") funded++;
      local ready = ("railReadyStock" in projects) && projects.railReadyStock != null
          ? projects.railReadyStock.len() : 0;
      local extraLog = "";
      if (ready > 0 && funded == 0) {
        local lastFunded = (projects.best != null && projects.best.len() > 0)
            ? projects.best[projects.best.len() - 1] : null;
        local lastScore = (lastFunded != null && ("fundScore" in lastFunded)) ? lastFunded.fundScore : 0.0;
        local lastCap = (lastFunded != null) ? OpexProjectFinanceCapital(lastFunded) : 0;
        local railScore = 0.0;
        local railCap = 0;
        foreach (k, stockEntry in projects.railReadyStock) {
          if (stockEntry != null && ("project" in stockEntry) && stockEntry.project != null) {
            local rp = stockEntry.project;
            railScore = ("fundScore" in rp) ? rp.fundScore : 0.0;
            railCap = OpexProjectFinanceCapital(rp);
            break;
          }
        }
        extraLog = " rail_score=" + railScore + " rail_cap=" + railCap
                 + " budget=" + capitalBudget + " last_score=" + lastScore + " last_cap=" + lastCap;
      }
      OpexC56TaskLog("RAIL_STOCK_SELECT", "projects", "-",
          "ready=" + ready + " funded=" + funded
          + " merge_ops=" + projects.stats.railStockFusionOpcodes + extraLog);
    }
  }
  return OpexPromoteLiveDefensiveAirBase(projects, capitalBudget);
}


function OpexLogVivier(path, candidates, stats, capitalBudget, capitalRemaining)
{
  if (!DECISION_LOG) return;
  if (DECISION_LOG) {
    local poolCapital = ("selectionPoolCapital" in stats) ? stats.selectionPoolCapital
        : (("selectedCapital" in stats) ? stats.selectedCapital : 0);
    local nextCapital = ("nextProjectCapital" in stats) ? stats.nextProjectCapital : 0;
    OpexDecide("VIVIER", "path=" + path + " considered=" + stats.budgetConsidered
               + " selected=" + stats.budgetSelected + " pool_selected=" + stats.budgetSelected
               + " rejected=" + stats.budgetRejected + " not_selected=" + stats.budgetRejected
               + " budget=" + capitalBudget + " selection_pool_capital=" + poolCapital
               + " next_capital=" + nextCapital + " remaining=" + capitalRemaining
               + " pool_headroom=" + capitalRemaining
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

function OpexProjectsStampSelectionStats(stats, projects, alternatives, funded, capitalBudget, extras)
{
  local minCap = -1;
  local nextCap = -1;
  foreach (p in alternatives) {
    local cap = OpexProjectFinanceCapital(p);
    if (("mode" in p) && p.mode == "fleet" && ("payload" in p) && p.payload != null
        && ("planePrice" in p.payload) && p.payload.planePrice > 0) {
      local planePrice = p.payload.planePrice;
      local want = ("want" in p.payload) ? p.payload.want : 1;
      local fitQty = ((capitalBudget - 1000) / planePrice).tointeger();
      if (fitQty < 0) fitQty = 0;
      if (fitQty < want) cap = (fitQty + 1) * planePrice + 1000;
    } else if (C118_AIR_TERRITORIAL_EXPANSION && ("mode" in p) && p.mode == "air"
        && ("c118MinFinance" in p) && p.c118MinFinance > 0) {
      cap = p.c118MinFinance;
    }
    if (cap > capitalBudget && (nextCap < 0 || cap < nextCap)) nextCap = cap;
  }
  stats.nextProjectCapital = nextCap;
  /* minCapital ne sert qu'a expliquer une selection vide. Eviter de
   * rescanner tout le vivier quand un projet financable existe deja. */
  if (funded.len() == 0) {
    foreach (p in alternatives) {
      local cap = OpexProjectFinanceCapital(p);
      if (minCap < 0 || cap < minCap) minCap = cap;
    }
  }
  stats.minCapital <- minCap;
  stats.railCandidates <- (("rail" in projects) && projects.rail != null && ("candidates" in projects.rail) && projects.rail.candidates != null) ? projects.rail.candidates.len() : 0;
  stats.roadCandidates <- (("road" in projects) && projects.road != null && ("candidates" in projects.road) && projects.road.candidates != null) ? projects.road.candidates.len() : 0;
  stats.airPlansCount <- (("airPlans" in projects) && projects.airPlans != null) ? projects.airPlans.len() : 0;
  stats.waterPlansCount <- (("waterPlans" in projects) && projects.waterPlans != null) ? projects.waterPlans.len() : 0;
  if (extras != null) {
    stats.abandonFiltered <- ("abandonFiltered" in extras) ? extras.abandonFiltered : 0;
    stats.abandonedPairsCount <- ("abandonedPairsCount" in extras) ? extras.abandonedPairsCount : 0;
    stats.cacheScanned <- ("cacheScanned" in extras) ? extras.cacheScanned : 0;
    stats.cacheRetained <- ("cacheRetained" in extras) ? extras.cacheRetained : 0;
  } else {
    if (!("abandonFiltered" in stats)) stats.abandonFiltered <- 0;
    if (!("abandonedPairsCount" in stats)) stats.abandonedPairsCount <- 0;
    if (!("cacheScanned" in stats)) stats.cacheScanned <- 0;
    if (!("cacheRetained" in stats)) stats.cacheRetained <- 0;
  }
  local emptyCause = "";
  if (funded.len() == 0) {
    if (alternatives.len() == 0) {
      local cacheScanned = stats.cacheScanned;
      local cacheRetained = stats.cacheRetained;
      local abandonFiltered = stats.abandonFiltered;
      local modeC = ("modeCandidates" in stats) ? stats.modeCandidates : 0;
      if (cacheScanned > 0 && cacheRetained == 0) {
        emptyCause = (abandonFiltered > 0) ? "abandon_filtered" : "cache_exhausted";
      } else if (abandonFiltered > 0 && modeC == 0) {
        emptyCause = "abandon_filtered";
      } else if (modeC == 0) {
        emptyCause = "stage_empty";
      } else {
        emptyCause = "empty_pool";
      }
    } else if (minCap > capitalBudget) {
      emptyCause = "all_unaffordable";
    } else {
      emptyCause = "selection_empty";
    }
  }
  stats.emptyCause <- emptyCause;
}

/* Rejoue UNIQUEMENT la contrainte de capital sur les projets deja produits par le catalogue.
 * candidateGroups porte le vivier ; cette fonction se contente de reaplatir ses alternatives et
 * de retester le capital. Aucune planification rail, recherche de site aerien ou generation de
 * route ne repasse ici. Les statistiques sont remplacees ensemble car IG| et IB| doivent decrire
 * la meme solution que best, y compris lorsque la selection n'a pas prouve son optimum. */
function OpexReselectProjects(projects, capitalBudget, abandonedPairs = null, lines = null, railReadyStock = null)
{
  local spReselect = PROBE_SPAN_TRACE ? OpexSpanBegin("select.reselect") : null;
  if (C80_RAIL_STOCK_GATE && railReadyStock == null && projects != null && ("railReadyStock" in projects)) {
    railReadyStock = projects.railReadyStock;
  }
  local b6BudgetDate = AIDate.GetCurrentDate();
  local funded = null;
  local considered = 0;
  local selectionLight = CATALOG_COST_PROBE ? OpexSelectionLightBegin() : null;
  local opsMark = OpexOpsMeasureBegin();
  local alternatives = [];
  local spPubFlat = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.flatten") : null;
  foreach (key, list in projects.candidateGroups) {
    foreach (project in list) alternatives.push(project);
  }
  if (spPubFlat != null) OpexSpanEnd(spPubFlat);
  local spPubMerge = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.merge") : null;
  if (C80_RAIL_STOCK_GATE) alternatives = OpexRailStockMergeAlternatives(alternatives, railReadyStock, projects.stats);
  if (C121_AIR_FIRST_YEAR_RAIL_PREP && !C121_CATALOG_FIRST_YEAR_ACTIVE) {
    if (railReadyStock == null && ("railReadyStock" in projects) && projects.railReadyStock != null)
      railReadyStock = projects.railReadyStock;
    alternatives = OpexRailPrepMergeAlternatives(alternatives, railReadyStock);
  }
  if (spPubMerge != null) OpexSpanEnd(spPubMerge);
  local spPubFilt = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.filter") : null;
  alternatives = OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines);
  if (spPubFilt != null) OpexSpanEnd(spPubFilt);
  local spPubScore = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.score") : null;
  funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);
  if (spPubScore != null) OpexSpanEnd(spPubScore);
  considered = alternatives.len();
  projects.stats.knapsackNodes = 0;
  projects.stats.knapsackExact = false;
  projects.stats.selectionOpcodes <- OpexOpsMeasureEnd(opsMark);
  if (selectionLight != null) OpexSelectionLightEnd(selectionLight, "reselect",
      projects.stats.selectionOpcodes, considered, funded.len());
  local spPubLog = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.log") : null;
  OpexB6LogSelectionCausality("reselect", alternatives, funded, capitalBudget, b6BudgetDate);
  if (spPubLog != null) OpexSpanEnd(spPubLog);

  local spPubStats = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.stats") : null;
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
  if ("selectionPoolCapital" in projects.stats) projects.stats.selectionPoolCapital = selectedCap;
  else projects.stats.selectionPoolCapital <- selectedCap;
  local nextProjectCapital = funded.len() > 0 ? OpexProjectFinanceCapital(funded[0]) : 0;
  if ("nextProjectCapital" in projects.stats) projects.stats.nextProjectCapital = nextProjectCapital;
  else projects.stats.nextProjectCapital <- nextProjectCapital;

  projects.capitalBudget = capitalBudget;
  projects.capitalRemaining = capitalBudget - selectedCap;
  if (projects.capitalRemaining < 0) projects.capitalRemaining = 0;

  OpexProjectsStampSelectionStats(projects.stats, projects, alternatives, funded, capitalBudget, null);

  projects.best = funded;
  if (C80_RAIL_STOCK_GATE) projects.railReadyStock <- railReadyStock;
  else if (C121_AIR_FIRST_YEAR_RAIL_PREP && railReadyStock != null) {
    if ("railReadyStock" in projects) projects.railReadyStock = railReadyStock;
    else projects.railReadyStock <- railReadyStock;
  }
  if (C69_BOTTLENECK_PROBE) {
    projects.c69Best <- ::C69_LAST_AFFORDABLE;
    projects.c69KDecData <- ::C69_LAST_KDEC_DATA;
  }
  if (spPubStats != null) OpexSpanEnd(spPubStats);

  local spPubVivier = PROBE_SPAN_TRACE ? OpexSpanBegin("pub.select.vivier") : null;
  if (DECISION_LOG) {
    local vivierPool = [];
    if (("candidateGroups" in projects) && projects.candidateGroups != null) {
      foreach (key, list in projects.candidateGroups) {
        foreach (project in list) vivierPool.push(project);
      }
    }
    OpexLogVivier("reselect", vivierPool, projects.stats, projects.capitalBudget, projects.capitalRemaining);
  }
  if (spPubVivier != null) OpexSpanEnd(spPubVivier);

  if (spReselect != null) OpexSpanEnd(spReselect);
  return projects;
}

/* C76/C77 : reconstruit une seule famille modale et la reinjecte dans le vivier
 * existant. Le classement final reste OpexProjectSelectAffordable via
 * OpexReselectProjects ; aucun score n'est redefini ici. */
function OpexProjectTouchesEntity(project, entityKind, entityId)
{
  if (project == null || entityKind == null || entityId < 0) return false;
  local payload = (("payload" in project) && project.payload != null) ? project.payload : null;
  if (entityKind == "town") {
    if (payload != null) {
      if (("srcTown" in payload) && payload.srcTown == entityId) return true;
      if (("dstTown" in payload) && payload.dstTown == entityId) return true;
      if (("siteA" in payload) && payload.siteA != null && ("town" in payload.siteA)
          && payload.siteA.town != null && ("id" in payload.siteA.town)
          && payload.siteA.town.id == entityId) return true;
      if (("siteB" in payload) && payload.siteB != null && ("town" in payload.siteB)
          && payload.siteB.town != null && ("id" in payload.siteB.town)
          && payload.siteB.town.id == entityId) return true;
    }
    return false;
  }
  if (entityKind == "industry") {
    if (payload != null) {
      if (("srcIndustry" in payload) && payload.srcIndustry == entityId) return true;
      if (("dstIndustry" in payload) && payload.dstIndustry == entityId) return true;
    }
    if (("src" in project) && AIMap.IsValidTile(project.src)
        && AIIndustry.GetIndustryID(project.src) == entityId) return true;
    if (("dst" in project) && AIMap.IsValidTile(project.dst)
        && AIIndustry.GetIndustryID(project.dst) == entityId) return true;
    return false;
  }
  if (entityKind == "subsidy" && payload != null
      && ("isSubsidy" in payload) && payload.isSubsidy
      && ("subsidyId" in payload)) {
    return payload.subsidyId == entityId;
  }
  return false;
}

function OpexProjectIsPersistentSpecial(project)
{
  if (project == null || !(("payload" in project)) || project.payload == null) return false;
  if (("isSubsidy" in project.payload) && project.payload.isSubsidy) return true;
  if (("isRoadExtension" in project.payload) && project.payload.isRoadExtension) return true;
  return false;
}

function OpexProjectsRecountGroups(projects)
{
  if (projects == null || !(("candidateGroups" in projects)) || projects.candidateGroups == null) return;
  local od = 0;
  local n = 0;
  local alternatives = 0;
  foreach (key, list in projects.candidateGroups) {
    if (list == null || list.len() == 0) continue;
    od++;
    n += list.len();
    if (list.len() > 1) alternatives += list.len() - 1;
  }
  projects.all = od;
  if (projects.stats != null) {
    projects.stats.odProjects = od;
    projects.stats.modeCandidates = n;
    projects.stats.modeAlternatives = alternatives;
  }
}

/* Exposition seulement (probe_air_finance_margin) : projets AIR ecartes par la
 * seule marge de financement (capital + immobilisation finançable, marge non). */
function OpexAirFinanceMarginLogSelect(alternatives, affordable, capitalBudget)
{
  local air = 0, blocked = 0, blockedCapital = 0, bestBlocked = null;
  foreach (project in alternatives) {
    if (project == null || !("mode" in project) || project.mode != "air") continue;
    air++;
    local finance = OpexProjectFinanceCapital(project);
    if (finance <= capitalBudget) continue;
    local plan = ("payload" in project) ? project.payload : null;
    local newAirports = (plan != null && ("reuseA" in plan) && plan.reuseA ? 0 : 1)
        + (plan != null && ("reuseB" in plan) && plan.reuseB ? 0 : 1);
    if (finance - OpexAirRequiredMargin(newAirports, plan) <= capitalBudget) {
      blocked++;
      if (bestBlocked == null || project.profitAnnual > bestBlocked.profitAnnual) bestBlocked = project;
    } else blockedCapital++;
  }
  local top = affordable.len() > 0 ? affordable[0] : null;
  local msg = "AIR_FINANCE_SELECT date=" + OpexAirFinanceMarginDate(AIDate.GetCurrentDate())
      + " budget=" + capitalBudget + " air=" + air + " blocked_margin=" + blocked
      + " blocked_capital=" + blockedCapital
      + " top_mode=" + (top != null ? top.mode : "none")
      + " top_profit=" + (top != null ? top.profitAnnual : 0)
      + " top_score=" + (top != null && ("budgetScore" in top) ? top.budgetScore : 0);
  if (bestBlocked != null) msg += " blk_profit=" + bestBlocked.profitAnnual
      + " blk_finance=" + OpexProjectFinanceCapital(bestBlocked)
      + " blk_score=" + (("budgetScore" in bestBlocked) ? bestBlocked.budgetScore : 0);
  AILog.Info(msg);
}
