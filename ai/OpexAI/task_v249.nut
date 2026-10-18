/* V249 : une statue par mois quand on est riche. Aucun montant fixe :
 * riche = aucun emprunt, aucune passe projets arretee faute de caisse depuis le
 * mois precedent (V249_CASH_STOP, pose dans task_projects.nut), et apres la
 * statue la caisse couvre encore la reserve et le projet le plus cher du
 * portefeuille. Aucun etat sauvegarde. La statue est un bit du monde
 * (AITown.HasStatue). _v249StatueMonth ne fait que borner la cadence dans la
 * session courante. NoAI 15 n'expose pas AITown.GetActionCost. */

/* Capital du projet le plus cher encore liste : la statue ne doit jamais
 * prendre l'argent d'un projet que le portefeuille veut financer. */
function OpexV249MaxListedCapital(projects)
{
  if (projects == null || !("best" in projects) || projects.best == null) return 0;
  local most = 0;
  foreach (project in projects.best) {
    local capital = OpexProjectFinanceCapital(project);
    if (capital > most) most = capital;
  }
  return most;
}

function OpexV249LineProfit(line)
{
  local stationId = OpexLineStationId(line, "A");
  if (stationId < 0) stationId = OpexLineStationId(line, "B");
  local vehicles = null;
  if (stationId >= 0) {
    vehicles = OpexLineVehicleIds(line, stationId);
  } else if (("vehicles" in line) && line.vehicles != null) {
    vehicles = line.vehicles;
  } else {
    return 0;
  }
  local vehicleType = OpexLineVehicleType(line);
  local profit = 0;
  foreach (v in vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    if (AIVehicle.GetVehicleType(v) != vehicleType) continue;
    profit += AIVehicle.GetProfitLastYear(v);
  }
  return profit;
}

/* Cout que PerformTownAction paierait. AITestMode n'execute pas : la statue
 * n'est pas posee. AIAccounting enregistre le cout de commande simule. */
function OpexV249MeasureStatueCost(townId)
{
  local account = AIAccounting();
  {
    local test = AITestMode();
    AITown.PerformTownAction(townId, AITown.TOWN_ACTION_BUILD_STATUE);
  }
  return account.GetCosts();
}

function OpexAI::_dispatchV249Statue(task, year)
{
  if (!V249_STATUE) return false;
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v249StatueMonth == ym) return false;
  this._v249StatueMonth = ym;

  local cashStop = V249_CASH_STOP;
  ::V249_CASH_STOP = false;
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=loan loan=" + loan);
    return true;
  }
  if (cashStop) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cash_stop");
    return true;
  }

  local byTown = {};
  local nLines = 0;
  if (this._lines != null) {
    foreach (line in this._lines) {
      if (line == null) continue;
      nLines++;
      local profit = OpexV249LineProfit(line);
      local seenTown = {};
      foreach (endName in ["A", "B"]) {
        local stationId = OpexLineStationId(line, endName);
        if (stationId < 0) continue;
        local townId = AIStation.GetNearestTown(stationId);
        if (!AITown.IsValidTown(townId)) continue;
        if (townId in seenTown) continue;
        seenTown[townId] <- 1;
        if (!(townId in byTown)) byTown[townId] <- { profit = 0, lines = 0 };
        byTown[townId].profit += profit;
        byTown[townId].lines++;
      }
    }
  }

  local bestTown = -1;
  local bestProfit = 0;
  local bestLines = 0;
  local found = false;
  local nStatue = 0;
  local nUnavail = 0;
  local nTowns = 0;
  foreach (townId, info in byTown) {
    nTowns++;
    if (AITown.HasStatue(townId)) {
      nStatue++;
      continue;
    }
    if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_BUILD_STATUE)) {
      nUnavail++;
      continue;
    }
    if (!found || info.profit > bestProfit || (info.profit == bestProfit && townId < bestTown)) {
      found = true;
      bestTown = townId;
      bestProfit = info.profit;
      bestLines = info.lines;
    }
  }
  if (!found) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=no_town statue=" + nStatue + " unavailable=" + nUnavail + " towns=" + nTowns + " lines=" + nLines);
    return true;
  }

  local cost = OpexV249MeasureStatueCost(bestTown);
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects);
  if (cost <= 0 || cash - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cost cash=" + cash + " cost=" + cost + " threshold=" + threshold + " town=" + bestTown);
    return true;
  }
  local built = AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_BUILD_STATUE);
  if (!built) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=failed town=" + bestTown + " cost=" + cost + " cash=" + cash + " threshold=" + threshold);
    return true;
  }
  if (DECISION_LOG) OpexDecide("V249_STATUE", "town=" + bestTown + " cost=" + cost + " cash=" + cash + " threshold=" + threshold + " lines=" + bestLines + " profit=" + bestProfit);
  return true;
}
