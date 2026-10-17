/* V249 : une statue par mois quand la caisse nette depasse un seuil indexe.
 * Aucun etat sauvegarde. La statue est un bit du monde (AITown.HasStatue).
 * _v249StatueMonth ne fait que borner la cadence dans la session courante ;
 * V249_BASE_MAX_LOAN est relu depuis difficulty.max_loan a chaque Start.
 * NoAI 15 n'expose pas AITown.GetActionCost (script_town.hpp, release/15). */

function OpexV249Threshold()
{
  /* Meme principe qu'AAAHogEx GetInflatedMoney : montant * emprunt max courant
   * / difficulty.max_loan, tronque vers zero. */
  local pounds = V249_STATUE_CASH * 1000;
  local loanBase = V249_BASE_MAX_LOAN;
  if (loanBase <= 0) return pounds;
  local maxLoan = AICompany.GetMaxLoanAmount();
  if (maxLoan <= 0) return pounds;
  return (pounds.tofloat() * maxLoan.tofloat() / loanBase.tofloat()).tointeger();
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
  if (V249_STATUE_CASH <= 0) return false;
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v249StatueMonth == ym) return false;
  this._v249StatueMonth = ym;

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local loan = AICompany.GetLoanAmount();
  local net = cash - loan;
  local threshold = OpexV249Threshold();
  if (net <= threshold) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cash cash=" + net + " threshold=" + threshold);
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
  cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  loan = AICompany.GetLoanAmount();
  net = cash - loan;
  if (cost <= 0 || net - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cost cash=" + net + " cost=" + cost + " threshold=" + threshold + " town=" + bestTown);
    return true;
  }
  local built = AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_BUILD_STATUE);
  if (!built) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=failed town=" + bestTown + " cost=" + cost + " cash=" + net + " threshold=" + threshold);
    return true;
  }
  if (DECISION_LOG) OpexDecide("V249_STATUE", "town=" + bestTown + " cost=" + cost + " cash=" + net + " threshold=" + threshold + " lines=" + bestLines + " profit=" + bestProfit);
  return true;
}
