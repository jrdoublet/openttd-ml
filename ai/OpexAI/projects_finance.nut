/* Extrait de projects.nut (R14) : Contraintes financieres : capital financable, C120 preparation de selection. Requis depuis projects.nut. */

/* P1 : cout a comparer a la tresorerie mobilisable. budgetCapital reste le
 * cout economique utilise par les scores historiques ; il ne faut pas y injecter
 * un multiplicateur global. Le repli de financabilite applique rail 1,7x et route
 * 1,21x. Si le trace a deja fourni un devis reel, capitalIsActual fait utiliser
 * ce montant. Les marges et le capital immobilise restent inchanges. */
function OpexProjectFinanceCapital(project)
{
  if (project == null || !("budgetCapital" in project)) return 0;
  local financeCapital = project.budgetCapital;
  if (CAPITAL_QUOTE_LEARNING) return OpexCapitalQuoteFinance(project, financeCapital);
  if (!CAPITAL_CALIBRATION || !("mode" in project)) return financeCapital;

  local biasPct = 0;
  if (project.mode == "rail") biasPct = RAIL_FINANCE_BIAS_PCT;
  else if (project.mode == "road") biasPct = 121;
  else return financeCapital;

  /* P0 isolation: only ROAD's funding-side multiplier changes. Economic
   * project.capital, budgetCapital, reserves and physical build stay intact. */
  if (project.mode == "road" && ROAD_FINANCE_UNBIAS_P0) biasPct = 100;

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

function OpexC118SetProjectField(project, field, value)
{
  if (field in project) project[field] = value;
  else project.rawset(field, value);
}

/* C120 : prepare uniquement la cle lexicographique territoriale sur le vivier
 * DEJA genere et revalide. Pas de scan moteur, route ou site ; la finance reste
 * exactement OpexProjectFinanceCapital et l'admission economique C115 n'est pas
 * contournee. */
function OpexC120PrepareSelection(alternatives, capitalBudget)
{
  if (!C120_AIR_TERRITORIAL_RANKING) {
    C120_AIR_SELECTION_SNAPSHOT = null;
    return null;
  }
  local cargo = OpexAirDemandPaxCargo();
  local covered = OpexC118OwnCoveredTownSet(cargo);
  local snapshot = {
    date = AIDate.GetCurrentDate(),
    cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF),
    budget = capitalBudget,
    airCandidates = 0,
    territorial = 0,
    affordableTerritorial = 0,
    fundedTerritorial = 0,
    bestNewTowns = 0,
    bestCost = -1,
    bestAffordableNewTowns = 0,
    bestAffordableCost = -1,
    selectedMode = "none",
    selectedNewTowns = 0,
    selectedCost = 0,
    selectedScore = 0.0,
    selectedEngine = -1,
    selectedSrc = -1,
    selectedDst = -1,
    selectionReason = "none",
  };
  foreach (project in alternatives) {
    if (project == null || !(("mode") in project) || project.mode != "air") continue;
    snapshot.airCandidates++;
    local ids = ((("payload") in project) && project.payload != null)
        ? OpexC118PlanCoverageTowns(project.payload, cargo) : [];
    local newTowns = 0;
    foreach (townId in ids) if (!(townId in covered)) newTowns++;
    OpexC118SetProjectField(project, "c120NewTowns", newTowns);
    if (newTowns <= 0) continue;
    snapshot.territorial++;
    local finance = OpexProjectFinanceCapital(project);
    if (newTowns > snapshot.bestNewTowns
        || (newTowns == snapshot.bestNewTowns
            && (snapshot.bestCost < 0 || finance < snapshot.bestCost))) {
      snapshot.bestNewTowns = newTowns;
      snapshot.bestCost = finance;
    }
    if (finance > capitalBudget) continue;
    snapshot.affordableTerritorial++;
    if (newTowns > snapshot.bestAffordableNewTowns
        || (newTowns == snapshot.bestAffordableNewTowns
            && (snapshot.bestAffordableCost < 0 || finance < snapshot.bestAffordableCost))) {
      snapshot.bestAffordableNewTowns = newTowns;
      snapshot.bestAffordableCost = finance;
    }
  }
  C120_AIR_SELECTION_SNAPSHOT = snapshot;
  return snapshot;
}

function OpexC120FinalizeSelection(affordable, capitalBudget)
{
  if (!C120_AIR_TERRITORIAL_RANKING || C120_AIR_SELECTION_SNAPSHOT == null) return;
  local snapshot = C120_AIR_SELECTION_SNAPSHOT;
  foreach (project in affordable) {
    if (project != null && ("mode" in project) && project.mode == "air"
        && ("c120NewTowns" in project) && project.c120NewTowns > 0) {
      snapshot.fundedTerritorial++;
    }
  }
  if (affordable != null && affordable.len() > 0 && affordable[0] != null) {
    local selected = affordable[0];
    snapshot.selectedMode = ("mode" in selected) ? selected.mode : "unknown";
    snapshot.selectedNewTowns = ("c120NewTowns" in selected) ? selected.c120NewTowns : 0;
    snapshot.selectedCost = OpexProjectFinanceCapital(selected);
    snapshot.selectedScore = ("fundScore" in selected) ? selected.fundScore : 0.0;
    snapshot.selectedSrc = ("src" in selected) ? selected.src : -1;
    snapshot.selectedDst = ("dst" in selected) ? selected.dst : -1;
    if (snapshot.selectedMode == "air" && ("payload" in selected)
        && selected.payload != null && ("plane" in selected.payload)
        && selected.payload.plane != null) snapshot.selectedEngine = selected.payload.plane.id;
  }
  if (snapshot.airCandidates <= 0) snapshot.selectionReason = "no_air_candidate";
  else if (snapshot.territorial <= 0) snapshot.selectionReason = "no_territorial_candidate";
  else if (snapshot.affordableTerritorial <= 0) snapshot.selectionReason = "territorial_unaffordable";
  else if (snapshot.fundedTerritorial <= 0) snapshot.selectionReason = "territorial_filtered";
  else if (snapshot.selectedMode == "air" && snapshot.selectedNewTowns > 0) {
    snapshot.selectionReason = "selected_territorial";
  } else snapshot.selectionReason = "other_mode_ranked_higher";
}

/* C120 : conserver EXACTEMENT les slots modaux produits par C115, puis
 * permuter seulement les projets AIR qui occupent ces slots. Le tri est stable :
 * newTowns decroissant, et a egalite l'ordre C115 original reste le departage.
 * Ainsi rail/route/eau/flotte ne gagnent ni ne perdent aucun rang a cause de C120. */
function OpexC120ReorderAffordableAir(affordable)
{
  if (!C120_AIR_TERRITORIAL_RANKING || affordable == null || affordable.len() < 2) return;
  local slots = [];
  local airs = [];
  for (local i = 0; i < affordable.len(); i++) {
    local project = affordable[i];
    if (project == null || !(("mode") in project) || project.mode != "air") continue;
    slots.append(i);
    airs.append(project);
  }
  if (airs.len() < 2) return;

  /* Insertion stable sur la seule cle territoriale. Ne jamais recalculer le
   * score economique : l'ordre d'entree est deja l'ordre C115 exact. */
  for (local i = 1; i < airs.len(); i++) {
    local current = airs[i];
    local currentNew = (("c120NewTowns") in current) ? current.c120NewTowns : 0;
    local j = i;
    while (j > 0) {
      local prior = airs[j - 1];
      local priorNew = (("c120NewTowns") in prior) ? prior.c120NewTowns : 0;
      if (priorNew >= currentNew) break;
      airs[j] = prior;
      j--;
    }
    airs[j] = current;
  }
  for (local i = 0; i < slots.len(); i++) affordable[slots[i]] = airs[i];
}

/* Trace C120 ciblee, emise seulement lorsque l'etat utile change. Le DETAIL
 * lisible vit dans AILog ; quatre panneaux compacts rendent le diagnostic
 * durable pour les sweeps, comme C118. */
function OpexC120TracePass(stopReason, airAttempts, airBuilt,
                           airRejectReason = null, passStopReason = null)
{
  if (!C120_AIR_TERRITORIAL_RANKING || C120_AIR_SELECTION_SNAPSHOT == null) return;
  local s = C120_AIR_SELECTION_SNAPSHOT;
  local now = AIDate.GetCurrentDate();
  local key = now + "|" + s.budget + "|" + s.airCandidates + "|" + s.territorial
      + "|" + s.fundedTerritorial + "|" + s.selectedMode + "|" + s.selectedNewTowns
      + "|" + stopReason + "|" + airAttempts + "|" + (airBuilt ? 1 : 0)
      + "|" + (airRejectReason != null ? airRejectReason : "-")
      + "|" + (passStopReason != null ? passStopReason : "-");
  if (key == C120_AIR_LAST_TRACE_KEY) return;
  C120_AIR_LAST_TRACE_KEY = key;
  C120_AIR_SELECT_SEQ++;
  local seq = C120_AIR_SELECT_SEQ;
  AILog.Info("C120_SELECT date=" + now
      + " cash=" + s.cash + " available=" + s.budget
      + " prefilterAir=" + (C120_AIR_FILTER_SNAPSHOT != null ? C120_AIR_FILTER_SNAPSHOT.inputAir : -1)
      + " filteredAir=" + (C120_AIR_FILTER_SNAPSHOT != null ? C120_AIR_FILTER_SNAPSHOT.filteredAir : -1)
      + " airCandidates=" + s.airCandidates + " territorial=" + s.territorial
      + " affordableTerritorial=" + s.affordableTerritorial
      + " fundedTerritorial=" + s.fundedTerritorial
      + " bestNewTowns=" + s.bestNewTowns + " bestCost=" + s.bestCost
      + " bestAffordableNewTowns=" + s.bestAffordableNewTowns
      + " bestAffordableCost=" + s.bestAffordableCost
      + " selected=" + s.selectedMode + " selectedNewTowns=" + s.selectedNewTowns
      + " selectedCost=" + s.selectedCost + " selectedScore=" + s.selectedScore
      + " selectedEngine=" + s.selectedEngine
      + " selectedSrc=" + s.selectedSrc + " selectedDst=" + s.selectedDst
      + " selectReason=" + s.selectionReason
      + " airAttempts=" + airAttempts + " airBuilt=" + (airBuilt ? 1 : 0)
      + " rejectReason=" + (airRejectReason != null ? airRejectReason : "-")
      + " passStop=" + (passStopReason != null ? passStopReason : "-")
      + " stopReason=" + stopReason);
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = AIDate.GetYear(now) % 100;
  OpexSign(anchor, "C0S|" + seq + "|" + yy + "|" + AIDate.GetMonth(now) + "|"
      + AIDate.GetDayOfMonth(now) + "|" + (s.budget / 1000) + "|" + s.airCandidates);
  OpexSign(anchor, "C0T|" + seq + "|" + s.territorial + "|" + s.fundedTerritorial
      + "|" + s.bestNewTowns + "|" + (s.bestCost / 1000));
  OpexSign(anchor, "C0P|" + seq + "|" + s.selectedNewTowns + "|" + (s.selectedCost / 1000)
      + "|" + s.selectedEngine + "|" + airAttempts + "|" + (airBuilt ? 1 : 0)
      + "|" + s.selectedSrc + "|" + s.selectedDst);
  OpexSign(anchor, "C0R|" + seq + "|" + stopReason
      + "|" + (airRejectReason != null ? airRejectReason : "-")
      + "|" + (passStopReason != null ? passStopReason : "-"));
  OpexSign(anchor, "C0C|" + seq + "|" + AIR_TERRITORIAL_COVERAGE_HITS
      + "|" + AIR_TERRITORIAL_COVERAGE_MISSES + "|" + AIR_TERRITORIAL_COVERAGE_CACHE.len()
      + "|" + AIR_STATION_COVERAGE_HITS + "|" + AIR_STATION_COVERAGE_MISSES
      + "|" + AIR_STATION_COVERAGE_TOWN_CACHE.len());
}
