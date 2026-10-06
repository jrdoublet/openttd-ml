/* Test-only R3 controller; actual catalogue plans, common ranking and executor.
 * No liveness/bypass/cash/API return is replaced. */
FX3 <- { phase = "search", successes = 0, obstacle = false };

function FxOverlap(a, b)
{
  return a.src == b.src || a.src == b.dst || a.dst == b.src || a.dst == b.dst;
}

function FxR3Prepare(ai)
{
  if (FX3.phase != "search" || ai._projects == null) return;
  local pool = [];
  foreach (p in ai._projects.best) {
    if (p.mode != "air" || p.payload.reuseA || p.payload.reuseB) continue;
    if (!OpexAirBatchPlanStillLive(p.payload, ai._lines)) continue;
    pool.append(p);
  }
  if (pool.len() < 3) return;
  local chosen = null;
  for (local i = 1; i < pool.len() && chosen == null; i++) {
    local overlap = FxOverlap(pool[0], pool[i]);
    if ((FX3_SCENARIO == "r3_dead") != overlap) continue;
    for (local j = i + 1; j < pool.len(); j++) {
      if (FxOverlap(pool[0], pool[j]) || FxOverlap(pool[i], pool[j])) continue;
      chosen = [pool[0], pool[i], pool[j]];
      break;
    }
  }
  if (chosen == null) return;
  FxAssert(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()), "R3_loan_max");
  local cash = OpexCashReserve();
  foreach (p in chosen) cash += 2 * OpexProjectFinanceCapital(p);
  FxBank(cash);
  local selected = OpexProjectSelectAffordable(chosen, OpexAvailableCapital(), PROJECT_TOP_K);
  FxAssert(selected.len() == 3, "R3_three_admitted");
  FxAssert((FX3_SCENARIO == "r3_dead") == FxOverlap(selected[0], selected[1])
    && !FxOverlap(selected[0], selected[2]) && !FxOverlap(selected[1], selected[2]), "R3_normal_ranking");
  for (local rank = 0; rank < selected.len(); rank++) {
    local p = selected[rank];
    FxAssert(OpexAirBatchPlanStillLive(p.payload, ai._lines), "R3_initial_liveness");
    FxLog("phase=r3_initial scenario=" + FX3_SCENARIO + " rank=" + rank
      + " id=" + OpexProjectAttemptKey(p) + " live=1 finance=" + OpexProjectFinanceCapital(p));
  }
  ai._projects.best = selected; // fixture input subset; never force rank/order
  FX3.phase = "executing";
  FX3.beforeLines <- ai._lines.len();
  FX3.nextFinance <- OpexProjectFinanceCapital(selected[1]);
}

function FxR3Outcome(ai, project, attempt)
{
  if (FX3.phase != "executing") return;
  if (attempt.outcome == "built") {
    FX3.successes++;
    FxIds(ai._lines.top());
    if (FX3_SCENARIO == "r3_cash" && FX3.successes == 1)
      FxBank(OpexCashReserve() + FX3.nextFinance - 10000);
  }
}

function FxR3Obstacle(plan, level)
{
  if (FX3.phase != "executing" || FX3_SCENARIO != "r3_failure"
    || FX3.successes != 1 || FX3.obstacle) return;
  FxAssert(level.ok, "R3_level_precondition");
  // The normal physical checks/leveling have succeeded. A real world command
  // now occupies the footprint. BuildAirport's actual refusal is untouched.
  FX3.airportsBefore <- AIStationList(AIStation.STATION_AIRPORT).Count();
  FX3.failedAnchor <- plan.siteA.anchor;
  local ok = AICompany.BuildCompanyHQ(plan.siteA.anchor);
  FxLog("phase=r3_obstacle command=BuildCompanyHQ ok=" + (ok ? 1 : 0)
    + " anchor=" + plan.siteA.anchor);
  FxAssert(ok, "R3_real_obstacle_command");
  FX3.obstacle = true;
}

function FxR3Finish(ai)
{
  if (FX3.phase != "executing") return;
  local expected = FX3_SCENARIO == "r3_dead" ? 2 : 1;
  FxAssert(FX3.successes == expected && ai._lines.len() == FX3.beforeLines + expected, "R3_line_count");
  local attached = {};
  foreach (line in ai._lines) {
    if (line.mode != "air") continue;
    foreach (v in FxIds(line)) {
      FxAssert(!(v in attached), "R3_vehicle_unique_line");
      attached.rawset(v, true);
    }
  }
  local all = AIVehicleList();
  for (local v = all.Begin(); !all.IsEnd(); v = all.Next()) {
    if (AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR && AIVehicle.IsPrimaryVehicle(v))
      FxAssert(v in attached, "R3_no_orphan_aircraft");
  }
  if (FX3_SCENARIO == "r3_failure") {
    FxAssert(FX3.obstacle, "R3_obstacle_exposed");
    FxAssert(OPEX_AIR_ROLLBACKS.len() == 0, "R3_no_pending_rollback");
    FxAssert(AIStationList(AIStation.STATION_AIRPORT).Count() == FX3.airportsBefore
      && !AIAirport.IsAirportTile(FX3.failedAnchor), "R3_no_ghost_airport");
    FxLog("phase=r3_rollback pending=0 airports_before=" + FX3.airportsBefore
      + " airports_after=" + AIStationList(AIStation.STATION_AIRPORT).Count());
  }
  FX3.phase = "done";
  FxLog("phase=r3_complete scenario=" + FX3_SCENARIO + " built=" + FX3.successes
    + " attached=" + attached.len() + " no_orphan=1");
  while (true) AIController.Sleep(100);
}