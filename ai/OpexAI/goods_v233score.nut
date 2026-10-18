/* V233 mode 4: opportunity floor from our own aircraft, rebuilt from live API
 * data on every admission and immediately before spending. No saved estimator.
 * This is a measured average return on equipment, not a predicted marginal
 * gain from a V252 replacement. No airport capital is spent for a reinforcement.
 */
function OpexV233AirYieldAllows(candidate)
{
  local date = AIDate.GetCurrentDate();
  local fullYearStart = AIDate.GetDate(AIDate.GetYear(date) - 1, 1, 1);
  local cohorts = {};
  foreach (vehicle, unused in AIVehicleList()) {
    if (!AIVehicle.IsValidVehicle(vehicle)
        || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_AIR) continue;
    // Last year's profit is complete only if the aircraft existed on Jan 1.
    if (AIVehicle.GetAge(vehicle) < date - fullYearStart) continue;
    local engine = AIVehicle.GetEngineType(vehicle);
    if (!AIEngine.IsValidEngine(engine) || !AIEngine.IsBuildable(engine)) continue;
    local price = AIEngine.GetPrice(engine);
    local life = AIEngine.GetMaxAge(engine);
    if (price <= 0 || life <= 0) continue;
    if (!(engine in cohorts)) cohorts[engine] <- { profit = 0.0, capital = 0.0, count = 0 };
    local row = cohorts[engine];
    // Vehicle profit already subtracts running costs, but not depreciation.
    // Include losing aircraft too; a cohort must not select only its winners.
    row.profit += AIVehicle.GetProfitLastYear(vehicle).tofloat() - price.tofloat() * 365.0 / life;
    row.capital += price.tofloat();
    row.count++;
  }
  local best = null;
  local bestEngine = -1;
  local samples = 0;
  foreach (engine, row in cohorts) {
    local observedYield = row.profit / row.capital;
    if (best == null || observedYield > best) {
      best = observedYield;
      bestEngine = engine;
      samples = row.count;
    }
  }
  local project = OpexProjectFromCandidate(candidate);
  local profit = project != null ? OpexProjectFundProfit(project) : 0;
  local capital = project != null ? OpexProjectFinanceCapital(project) : 0;
  // Unknown alternative: wait for measurement, never invent a fallback rate.
  local allowed = best != null && capital > 0 && profit > 0
      && profit.tofloat() / capital.tofloat() >= best;
  if (DECISION_LOG) OpexDecide("V233_YIELD", "factory=" + candidate.v233FactoryId
    + " cargo=" + candidate.cargo + " profit=" + profit + " capital=" + capital
    + " air_yield=" + (best != null ? best.tostring() : "unknown")
    + " engine=" + bestEngine + " samples=" + samples + " allowed=" + allowed);
  return allowed;
}
