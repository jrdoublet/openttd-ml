/* Test copy only. Return the old result during natural activity. Directed
 * cap overrides exercise the branch, not the natural cap distribution. */
FXW_ENGINE <- OpexC121EngineEconomics;
FXW_CHOOSE <- OpexC121ChooseRoutePlane;
FXW_SCAN_CAP <- OpexC121AirFleetScanCap;
FXW_CAP <- 0;
FXW_ACTIVE <- false;
FXW_INITIAL <- null;
FXW_PLAN <- null;
FXW_PLANE <- null;
FXW_DATE <- -1;
FXW_MATRIX <- false;
FXW_INPUT <- null;

function FxWAssert(ok, label)
{
  if (!ok) throw "C121_WINNER_ASSERT " + label;
}

function FxWEqual(a, b)
{
  if (typeof a != typeof b) return false;
  if (typeof a == "table" || typeof a == "array") {
    if (a.len() != b.len()) return false;
    foreach (k, v in a) {
      if (!(k in b) || !FxWEqual(v, b[k])) return false;
    }
    return true;
  }
  return a == b;
}

function FxWCopy(initial)
{
  local full = clone initial;
  if (initial.decisionEconomics != null) full.decisionEconomics = clone initial.decisionEconomics;
  return full;
}

function FxWCap(plan, days, pax, mail)
{
  return FXW_CAP > 0 ? FXW_CAP : FXW_SCAN_CAP(plan, days, pax, mail);
}

function FxWPair(catalog, plan, plane, shortcut)
{
  local day = AIDate.GetCurrentDate();
  local initial = FXW_ENGINE(catalog, plan, plane, C121_AAA_LINE ? 2 : 1, false);
  local full = shortcut && !C121_AAA_LINE && initial != null
      && initial.fleetScanCap == 1 && day == AIDate.GetCurrentDate()
      ? FxWCopy(initial) : FXW_ENGINE(catalog, plan, plane, 0, false);
  return { initial = initial, full = full };
}

function FxWMatrix(catalog, plan, plane)
{
  local saved = { aaa = C121_AAA_LINE, depth = C121_AIR_PORTFOLIO_DEPTH_ECONOMICS,
      split = C121_AIR_PORTFOLIO_SPLIT_ECONOMICS, decision = C121_AIR_DECISION_DEPTH_ECONOMICS,
      caps = C121_AIR_ENGINE_CAPACITY_OBS };
  OpexC121AirFleetScanCap = FxWCap;
  local count = 0;
  for (local mail = 0; mail < 3; mail++) {
    C121_AIR_ENGINE_CAPACITY_OBS = clone saved.caps;
    if (plane.id in C121_AIR_ENGINE_CAPACITY_OBS) delete C121_AIR_ENGINE_CAPACITY_OBS[plane.id];
    if (mail > 0) C121_AIR_ENGINE_CAPACITY_OBS.rawset(plane.id,
        { pax = plane.capacity, mail = mail == 1 ? 0 : 20 });
    for (local mode = 0; mode < 4; mode++) {
      C121_AIR_PORTFOLIO_DEPTH_ECONOMICS = mode == 1;
      C121_AIR_PORTFOLIO_SPLIT_ECONOMICS = mode == 2;
      C121_AIR_DECISION_DEPTH_ECONOMICS = mode == 3;
      foreach (cap in [1, 2, 4]) {
        FXW_CAP = cap;
        for (local aaa = 0; aaa < 2; aaa++) {
          C121_AAA_LINE = aaa != 0;
          local oldPair = null;
          local newPair = null;
          local oldOps = 0;
          local newOps = 0;
          local stable = false;
          local attempts = 0;
          /* Suspensions can cross a day. Discard that timing sample and rerun
           * the same directed input, at most eight times; never accept it. */
          for (; attempts < 8; attempts++) {
            local day = AIDate.GetCurrentDate();
            local tick = AIController.GetTick();
            local ops = AIController.GetOpsTillSuspend();
            oldPair = FxWPair(catalog, plan, plane, false);
            oldOps = OpexAirCalcDeltaOps(tick, ops);
            tick = AIController.GetTick();
            ops = AIController.GetOpsTillSuspend();
            newPair = FxWPair(catalog, plan, plane, true);
            newOps = OpexAirCalcDeltaOps(tick, ops);
            stable = day == AIDate.GetCurrentDate();
            if (stable) break;
          }
          FxWAssert(oldPair.initial != null && oldPair.full != null, "matrix_nonnull");
          FxWAssert(stable, "matrix_no_stable_sample");
          FxWAssert(FxWEqual(oldPair, newPair), "matrix_recursive_values");
          local eligible = cap == 1 && aaa == 0;
          if (eligible) {
            local prior = newPair.initial.profitAnnual;
            newPair.full.profitAnnual++;
            FxWAssert(newPair.initial.profitAnnual == prior, "outer_alias");
            prior = newPair.initial.decisionEconomics.profitAnnual;
            newPair.full.decisionEconomics.profitAnnual++;
            FxWAssert(newPair.initial.decisionEconomics.profitAnnual == prior, "nested_alias");
          }
          count++;
          AILog.Info("C121_WINNER_MATRIX case=" + count + " cap=" + cap + " mail=" + mail
              + " mode=" + mode + " aaa=" + aaa + " stable=" + (stable ? 1 : 0)
              + " eligible=" + (eligible ? 1 : 0) + " old_ops=" + oldOps + " new_ops=" + newOps + " pass=1");
          if (attempts > 0) AILog.Info("C121_WINNER_RETRY case=" + count + " discarded=" + attempts);
        }
      }
    }
  }
  FXW_CAP = 0;
  OpexC121AirFleetScanCap = FXW_SCAN_CAP;
  C121_AAA_LINE = saved.aaa;
  C121_AIR_PORTFOLIO_DEPTH_ECONOMICS = saved.depth;
  C121_AIR_PORTFOLIO_SPLIT_ECONOMICS = saved.split;
  C121_AIR_DECISION_DEPTH_ECONOMICS = saved.decision;
  C121_AIR_ENGINE_CAPACITY_OBS = saved.caps;
  FXW_MATRIX = true;
  AILog.Info("C121_WINNER_VM complete=1 cases=" + count + " restored=1");
}

function FxWEngine(catalog, plan, plane, fixed = 0, compact = false, floor = null)
{
  local day = AIDate.GetCurrentDate();
  local tick = AIController.GetTick();
  local ops = AIController.GetOpsTillSuspend();
  local result = FXW_ENGINE(catalog, plan, plane, fixed, compact, floor);
  local used = OpexAirCalcDeltaOps(tick, ops);
  if (!FXW_ACTIVE || compact) return result;
  if (fixed > 0) {
    FXW_INITIAL = result;
    FXW_PLAN = plan;
    FXW_PLANE = plane;
    FXW_DATE = day;
  } else if (result != null) {
    local stable = day == AIDate.GetCurrentDate() && day == FXW_DATE;
    local eligible = !C121_AAA_LINE && result.fleetScanCap == 1 && FXW_INITIAL != null
        && FXW_INITIAL.fleetScanCap == 1 && FXW_PLAN == plan && FXW_PLANE == plane && stable;
    local copyOps = -1;
    if (eligible) {
      tick = AIController.GetTick();
      ops = AIController.GetOpsTillSuspend();
      local candidate = FxWCopy(FXW_INITIAL);
      copyOps = OpexAirCalcDeltaOps(tick, ops);
      FxWAssert(FxWEqual(result, candidate), "live_recursive_values");
    }
    AILog.Info("C121_WINNER_LIVE arm=" + plan.arm + " cap=" + result.fleetScanCap
        + " mail=" + (result.engineMailKnown ? (result.mailKnown ? "positive" : "zero") : "unknown")
        + " eligible=" + (eligible ? 1 : 0) + " stable=" + (stable ? 1 : 0)
        + " full_ops=" + used + " copy_ops=" + copyOps + " pass=1");
    if (FXW_INPUT == null) FXW_INPUT = { catalog = catalog, plan = plan, plane = plane };
  }
  return result;
}

function FxWChoose(catalog, plan, lines = null)
{
  FXW_ACTIVE = true;
  FXW_INITIAL = null;
  local choice = FXW_CHOOSE(catalog, plan, lines);
  FXW_ACTIVE = false;
  if (!FXW_MATRIX && FXW_INPUT != null) FxWMatrix(FXW_INPUT.catalog, FXW_INPUT.plan, FXW_INPUT.plane);
  return choice;
}

function FxWStart(owner)
{
  FxWAssert(!owner._loadedFromSave, "fresh_game_only");
  OpexC121EngineEconomics = FxWEngine;
  OpexC121ChooseRoutePlane = FxWChoose;
  AILog.Info("C121_WINNER_START active=1 production_result=old");
}
