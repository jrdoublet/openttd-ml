/* Diagnostic copy only. Bounded counterfactual gates on identical current inputs.
 * These logs establish exposure, never an economic result or final ranking change. */
QN_COUNTS <- {};
function QnLog(kind, value) {
  local n = (kind in QN_COUNTS) ? QN_COUNTS[kind] : 0;
  if (n >= 8) return;
  QN_COUNTS.rawset(kind, n + 1);
  AILog.Info("QUAL_NUMERIC mechanism=" + kind + " affected=1 value=" + value);
}

function QnEarlyBonus(project, state, target, minpop, bonus) {
  if (!AIR_EARLY_SLOT || !("mode" in project) || project.mode != "air"
      || !("payload" in project) || project.payload == null
      || state.servedCount >= target) return 0;
  local plan = project.payload;
  local claimed = {};
  local count = 0;
  foreach (side in ["A", "B"]) {
    local siteKey = "site" + side;
    local reuseKey = "reuse" + side;
    if ((reuseKey in plan) && plan[reuseKey]) continue;
    if (!(siteKey in plan) || plan[siteKey] == null || !("town" in plan[siteKey])) continue;
    local site = plan[siteKey];
    local town = AITile.GetClosestTown(site.anchor);
    if (town < 0) town = site.town.id;
    if (town < 0 || !AITown.IsValidTown(town)) continue;
    if (AITown.GetPopulation(town) < minpop || town in state.servedTowns || town in claimed) continue;
    claimed.rawset(town, true);
    count++;
  }
  local remaining = target - state.servedCount;
  if (count > remaining) count = remaining;
  return bonus * count;
}

function QnEarly(project, state, actualBonus) {
  if (AIR_EARLY_SLOT_TARGET_TOWNS != 6
      && actualBonus != QnEarlyBonus(project, state, 6, AIR_EARLY_SLOT_MIN_POP, AIR_EARLY_SLOT_BONUS_PCT))
    QnLog("num_target", AIR_EARLY_SLOT_TARGET_TOWNS);
  if (AIR_EARLY_SLOT_BONUS_PCT != 50
      && actualBonus != QnEarlyBonus(project, state, AIR_EARLY_SLOT_TARGET_TOWNS, AIR_EARLY_SLOT_MIN_POP, 50))
    QnLog("num_bonus", AIR_EARLY_SLOT_BONUS_PCT);
  if (AIR_EARLY_SLOT_MIN_POP != 1000
      && actualBonus != QnEarlyBonus(project, state, AIR_EARLY_SLOT_TARGET_TOWNS, 1000, AIR_EARLY_SLOT_BONUS_PCT))
    QnLog("num_pop", AIR_EARLY_SLOT_MIN_POP);
}

function QnCadence(line) {
  if (AIR_FLEET_CADENCE_DAYS <= 7) return;
  local last = ("lastAirFleetDate" in line) ? line.lastAirFleetDate
      : (("buildDate" in line) ? line.buildDate : 0);
  if (last > 0 && AIDate.GetCurrentDate() - last >= 7
      && AIDate.GetCurrentDate() - last < AIR_FLEET_CADENCE_DAYS)
    QnLog("num_cadence", AIR_FLEET_CADENCE_DAYS);
}

function QnPhase(line, below, have, year) {
  if (!below || !C121_AIR_FIRST_LIVE_GROWTH || have != 1
      || ("lastAirFleetYear" in line) || C121_FLEET_STOCK_GROWTH
      || C121_AIR_OBSERVATION_GROWTH || C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS == 4) return;
  local elapsed = year - OPEX_START_YEAR;
  local active = C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS <= 0
      || elapsed < C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS;
  if (active == (elapsed < 4)) return;
  local age = ("year" in line) ? year - line.year : -1;
  /* Otherwise the historical fallback already admits the same reinforcement. */
  if (age >= 2 && ("lastProfit" in line) && line.lastProfit > 0) return;
  if (OpexC121FirstLiveBalanced90(line)) QnLog("num_phase", C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS);
}
