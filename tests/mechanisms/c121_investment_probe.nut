/* Copy-only C121 investment trace.
 * Loaded only by sweeps/diag_c121_investment.py; never imported by production.
 * Unknown observations are written as "na", never coerced to zero. */

C121_INVEST_SEQ <- 0;
C121_INVEST_FLEET_SEEN <- {};

function C121InvestValue(obj, key)
{
  return obj != null && (key in obj) ? obj[key] : "na";
}

function C121InvestLog(event, tail = "")
{
  C121_INVEST_SEQ++;
  local now = AIDate.GetCurrentDate();
  AILog.Info("C121_INVEST v=1 seq=" + C121_INVEST_SEQ
      + " event=" + event + " day=" + now + " tick=" + AIController.GetTick() + tail);
}

function C121InvestSource()
{
  C121InvestLog("source", " econ=" + (C121_AIR_ECONOMICS ? 1 : 0)
      + " catalog=" + (C121_CATALOG_INCREMENTAL ? 1 : 0)
      + " initial=" + (C121_AIR_INITIAL_PROJECT_ECONOMICS ? 1 : 0));
}

function C121InvestProject(project, rank, phase, outcome = "na", lineId = -1)
{
  if (!C121_AIR_ECONOMICS || project == null || !("mode" in project) || project.mode != "air"
      || !("payload" in project) || project.payload == null) return;
  local plan = project.payload;
  if (!("economics" in plan) || plan.economics == null) return;
  local initial = plan.economics;
  local target = ("decisionEconomics" in plan) ? plan.decisionEconomics : null;
  local decision = target != null && ("decisionEconomics" in target) ? target.decisionEconomics : null;
  local available = OpexAvailableCapital();
  C121InvestLog("project", " phase=" + phase + " key=" + OpexProjectAttemptKey(project)
      + " rank=" + rank + " outcome=" + outcome + " line=" + (lineId >= 0 ? lineId : "na")
      + " arm=" + C121InvestValue(plan, "arm")
      + " initial_n=" + C121InvestValue(initial, "planes")
      + " target_n=" + C121InvestValue(target, "planes")
      + " decision_n=" + C121InvestValue(decision, "planes")
      + " initial_profit=" + C121InvestValue(initial, "profitAnnual")
      + " target_profit=" + C121InvestValue(target, "profitAnnual")
      + " decision_profit=" + C121InvestValue(decision, "profitAnnual")
      + " finance_now=" + OpexProjectFinanceCapital(project)
      + " finance_score=" + C121InvestValue(project, "decisionFinanceCapital")
      + " available=" + available
      + " fund_score=" + C121InvestValue(project, "fundScore"));
}

function C121InvestFleetSnapshot(line, year, event, reason, before = -1, after = -1, added = 0)
{
  if (!C121_AIR_ECONOMICS || line == null || !("mode" in line) || line.mode != "air") return;
  local lineId = ("lineId" in line) ? line.lineId : -1;
  /* Un seul instantane par ligne/annee/motif suffit pour attribuer la garde.
   * La version mensuelle perturbait nettement les trajectoires par son cout en
   * opcodes : ce probe doit rester descriptif et aussi leger que possible. */
  local dedup = lineId + "|" + year + "|" + event + "|" + reason;
  if (dedup in C121_INVEST_FLEET_SEEN) return;
  C121_INVEST_FLEET_SEEN.rawset(dedup, true);

  local have = before >= 0 ? before : (("vehCount" in line) ? line.vehCount
      : (("vehicles" in line) && line.vehicles != null ? line.vehicles.len() : -1));
  local target = ("targetAirPlanes" in line) ? line.targetAirPlanes : -1;
  local age = ("year" in line) ? year - line.year : -1;
  local lastProfit = ("lastProfit" in line) ? line.lastProfit : "na";
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local reserve = OpexCashReserve();
  local waitA = "na";
  local waitB = "na";
  if (("cargo" in line) && ("stationA" in line)) {
    local stA = AIStation.GetStationID(line.stationA);
    if (AIStation.IsValidStation(stA)) waitA = AIStation.GetCargoWaiting(stA, line.cargo);
    if (("stationB" in line)) {
      local stB = AIStation.GetStationID(line.stationB);
      if (AIStation.IsValidStation(stB)) waitB = AIStation.GetCargoWaiting(stB, line.cargo);
    }
  }
  local planePrice = "na";
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
      local p = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
      if (p > 0) planePrice = p;
      break;
    }
  }
  local need = typeof planePrice == "integer" ? planePrice + reserve + 2000 : "na";
  C121InvestLog("fleet", " phase=" + event + " line=" + lineId + " reason=" + reason
      + " year=" + year + " age=" + age + " have=" + have + " target=" + target
      + " after=" + (after >= 0 ? after : "na") + " added=" + added
      + " last_profit=" + lastProfit + " cash=" + money + " reserve=" + reserve
      + " plane_price=" + planePrice + " need=" + need
      + " wait_a=" + waitA + " wait_b=" + waitB);
}

function C121InvestAnnual(line, year, vehCount, profit, revenue, stationA, stationB, ratingA, ratingB)
{
  if (!C121_AIR_ECONOMICS || line == null || !("mode" in line) || line.mode != "air") return;
  local waitA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoWaiting(stationA, line.cargo) : "na";
  local waitB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoWaiting(stationB, line.cargo) : "na";
  local age = ("year" in line) ? year - line.year : -1;
  local fullYear = ("year" in line) && line.year <= year - 2;
  C121InvestLog("annual", " line=" + C121InvestValue(line, "lineId")
      + " report_year=" + year + " profit_year=" + (year - 1) + " age=" + age
      + " full_year=" + (fullYear ? 1 : 0) + " vehs=" + vehCount
      + " profit=" + profit + " revenue=" + revenue
      + " wait_a=" + waitA + " wait_b=" + waitB
      + " rating_a=" + ratingA + " rating_b=" + ratingB);
}
