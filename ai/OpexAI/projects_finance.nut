/* Extrait de projects.nut (R14) : Contraintes financieres : capital financable, C118/C120 preparation de selection. Requis depuis projects.nut. */

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

function OpexC118ProjectC68Economics(project)
{
  if (project == null || !(("payload") in project) || project.payload == null) return null;
  local plan = project.payload;
  if (("c118C68Economics" in plan) && plan.c118C68Economics != null) return plan.c118C68Economics;
  return ("economics" in plan) ? plan.economics : null;
}

function OpexC118ProjectC68FinanceCapital(project)
{
  local economics = OpexC118ProjectC68Economics(project);
  if (economics == null || economics.capital <= 0 || !(("payload") in project)
      || project.payload == null) return 0;
  local plan = project.payload;
  local newAirports = ((("reuseA") in plan) && plan.reuseA ? 0 : 1)
      + ((("reuseB") in plan) && plan.reuseB ? 0 : 1);
  local margin = newAirports == 2 ? 30000 : (newAirports == 1 ? 12000 : 2000);
  local finance = economics.capital + margin;
  if (("immobilise" in economics) && economics.immobilise > 0) finance += economics.immobilise;
  return OpexCapitalQuoteAlternativeFinance(project, economics, finance);
}

function OpexC118ProjectC68SpendCapital(project)
{
  local economics = OpexC118ProjectC68Economics(project);
  if (economics == null || economics.capital <= 0) return 0;
  local spend = economics.capital;
  if (("immobilise" in economics) && economics.immobilise > 0) spend += economics.immobilise;
  return spend;
}

function OpexC118TownInList(ids, townId)
{
  if (ids == null) return false;
  foreach (id in ids) if (id == townId) return true;
  return false;
}

function OpexC118SetProjectField(project, field, value)
{
  if (field in project) project[field] = value;
  else project.rawset(field, value);
}

function OpexC118EconomicsSpendCapital(economics)
{
  if (economics == null || economics.capital <= 0) return 0;
  local spend = economics.capital;
  if (("immobilise" in economics) && economics.immobilise > 0) spend += economics.immobilise;
  return spend;
}

function OpexC118ProjectMinFinance(project)
{
  if (project == null || !("payload" in project) || project.payload == null) {
    return OpexProjectFinanceCapital(project);
  }
  local plan = project.payload;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local best = 0;
  if (("c118EngineChoices" in plan) && plan.c118EngineChoices != null) {
    foreach (item in plan.c118EngineChoices) {
      if (item == null || !("plane" in item) || item.plane == null
          || !("economics" in item) || item.economics == null
          || item.economics.profitAnnual <= 0
          || !OpexC118EngineFitsPlan(plan, item.plane)) continue;
      local finance = OpexCapitalQuoteAlternativeFinance(project, item.economics,
          OpexC116RouteFinanceCapital(item.economics, newAirports));
      if (finance > 0 && (best <= 0 || finance < best)) best = finance;
    }
  }
  return best > 0 ? best : OpexProjectFinanceCapital(project);
}

/* Temps de financement en jours, sans seuil monetaire ni epsilon invente.
 * nextCapital <= 0 signifie qu'apres le projet courant il ne reste plus de
 * projet territorial connu : la phase couverture se termine naturellement.
 * -1 ne sert que de sentinelle de classement pour un flux non positif. */
function OpexC118TimeToNextDays(available, currentSpend, flowPerDay, profitAnnual, nextCapital)
{
  if (nextCapital <= 0) return 0.0;
  local cashAfter = available - currentSpend;
  if (cashAfter < 0) cashAfter = 0;
  local gap = nextCapital - cashAfter;
  if (gap <= 0) return 0.0;
  local flowAfter = flowPerDay + profitAnnual.tofloat() / 365.0;
  if (flowAfter <= 0.0) return -1.0;
  return gap.tofloat() / flowAfter;
}

/* Prepare une seule fois la politique territoriale pour toute la passe.
 * Le seul scan physique est celui des catchments Opex existants ; les projets
 * reutilisent les TownID deja derives de leurs sites trouves. townMin contient
 * pour chaque ville encore neuve le projet AIR au capital C68 minimal qui la
 * couvrirait : cela suffit pour obtenir K_next sans O(n^2). */
function OpexC118PrepareSelection(alternatives, capitalBudget)
{
  if (!C118_AIR_TERRITORIAL_EXPANSION) {
    C118_AIR_PROJECT_SNAPSHOT = null;
    return null;
  }
  local cargo = OpexAirDemandPaxCargo();
  local covered = OpexC118OwnCoveredTownSet(cargo);
  local townMin = {};
  local flow = OpexComputeOperatingCashFlow();
  local flowPerDay = flow.F;
  local territorialProjects = 0;

  foreach (project in alternatives) {
    if (project == null || !(("mode") in project) || project.mode != "air"
        || !(("profitAnnual") in project) || project.profitAnnual <= 0
        || !(("payload") in project) || project.payload == null) continue;
    local ids = ("c118TownIds" in project) ? project.c118TownIds
        : OpexC118PlanCoverageTowns(project.payload, cargo);
    OpexC118SetProjectField(project, "c118TownIds", ids);
    local newTowns = 0;
    foreach (townId in ids) if (!(townId in covered)) newTowns++;
    OpexC118SetProjectField(project, "c118NewTowns", newTowns);
    local c68 = OpexC118ProjectC68Economics(project);
    local c68Finance = OpexC118ProjectC68FinanceCapital(project);
    local c68Profit = c68 != null ? c68.profitAnnual : project.profitAnnual;
    local c68Roi = c68 != null ? c68.roi : project.roi;
    OpexC118SetProjectField(project, "c118C68Finance", c68Finance);
    OpexC118SetProjectField(project, "c118C68Profit", c68Profit);
    OpexC118SetProjectField(project, "c118C68Roi", c68Roi);
    local minFinance = OpexC118ProjectMinFinance(project);
    OpexC118SetProjectField(project, "c118MinFinance", minFinance);
    if (newTowns <= 0 || minFinance <= 0) continue;
    territorialProjects++;
    foreach (townId in ids) {
      if (townId in covered) continue;
      if (!(townId in townMin) || minFinance < townMin[townId].capital) {
        townMin.rawset(townId, {
          town = townId, capital = minFinance, project = project,
          src = ("src" in project) ? project.src : -1,
          dst = ("dst" in project) ? project.dst : -1,
        });
      }
    }
  }

  local active = townMin.len() > 0;
  if (active) {
    foreach (project in alternatives) {
      if (project == null || !(("mode") in project) || project.mode != "air"
          || !(("c118TownIds") in project)) continue;
      local ids = project.c118TownIds;
      local nextCapital = 0;
      local nextPoint = null;
      foreach (townId, point in townMin) {
        if (townId in covered || OpexC118TownInList(ids, townId)) continue;
        if (nextCapital <= 0 || point.capital < nextCapital) {
          nextCapital = point.capital;
          nextPoint = point;
        }
      }
      local plan = project.payload;
      local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
          + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
      local bestDays = -1.0;
      local bestProfit = -2147483647;
      local bestRoi = -2147483647;
      local bestEngine = -1;
      if (("c118EngineChoices" in plan) && plan.c118EngineChoices != null) {
        foreach (item in plan.c118EngineChoices) {
          if (item == null || !("plane" in item) || item.plane == null
              || !("economics" in item) || item.economics == null
              || item.economics.profitAnnual <= 0
              || !OpexC118EngineFitsPlan(plan, item.plane)) continue;
          local finance = OpexCapitalQuoteAlternativeFinance(project, item.economics,
              OpexC116RouteFinanceCapital(item.economics, newAirports));
          if (finance <= 0 || finance > capitalBudget) continue;
          local days = OpexC118TimeToNextDays(capitalBudget,
              OpexC118EconomicsSpendCapital(item.economics), flowPerDay,
              item.economics.profitAnnual, nextCapital);
          if (days < 0) continue;
          if (bestDays < 0 || days < bestDays
              || (days == bestDays && (item.economics.profitAnnual > bestProfit
                  || (item.economics.profitAnnual == bestProfit && item.economics.roi > bestRoi)))) {
            bestDays = days;
            bestProfit = item.economics.profitAnnual;
            bestRoi = item.economics.roi;
            bestEngine = item.plane.id;
          }
        }
      }
      if (bestDays < 0) {
        local c68 = OpexC118ProjectC68Economics(project);
        local c68Profit = c68 != null ? c68.profitAnnual : project.profitAnnual;
        local c68Spend = OpexC118ProjectC68SpendCapital(project);
        bestDays = OpexC118TimeToNextDays(capitalBudget, c68Spend, flowPerDay,
            c68Profit, nextCapital);
        bestEngine = (("c118C68Plane" in plan) && plan.c118C68Plane != null)
            ? plan.c118C68Plane.id : (("plane" in plan) && plan.plane != null ? plan.plane.id : -1);
      }
      OpexC118SetProjectField(project, "c118NextCapital", nextCapital);
      OpexC118SetProjectField(project, "c118NextDays", bestDays);
      OpexC118SetProjectField(project, "c118NextTown", nextPoint != null ? nextPoint.town : -1);
      OpexC118SetProjectField(project, "c118PreferredEngine", bestEngine);
    }
  }
  C118_AIR_PROJECT_SNAPSHOT = {
    date = AIDate.GetCurrentDate(), budget = capitalBudget,
    flowPerDay = flowPerDay, coveredTowns = covered, townMin = townMin,
    active = active, territorialProjects = territorialProjects,
  };
  return C118_AIR_PROJECT_SNAPSHOT;
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
