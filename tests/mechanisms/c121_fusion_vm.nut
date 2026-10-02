/* Requires original winner fixture helpers; no production function replaced
 * by the candidate. Both paths run on the same prepared route. */
FXF_INITIAL_OPS <- 0;

function FxFPair(catalog, plan, plane, fusion)
{
  if (!fusion || C121_AAA_LINE) {
    local initial = FXW_ENGINE(catalog, plan, plane, C121_AAA_LINE ? 2 : 1, false);
    local full = FXW_ENGINE(catalog, plan, plane, 0, false);
    return { initial = initial, full = full };
  }
  local holder = { initial = null };
  local full = FxFEngineEconomics(catalog, plan, plane, 0, false, null, holder);
  return { initial = holder.initial, full = full };
}

function FxFIsolation(pair)
{
  if (pair.initial == null || pair.full == null || C121_AAA_LINE) return;
  local profit = pair.initial.profitAnnual;
  pair.full.profitAnnual++;
  FxWAssert(pair.initial.profitAnnual == profit, "fusion_outer_alias");
  pair.full.profitAnnual--;
  profit = pair.initial.decisionEconomics.profitAnnual;
  pair.full.decisionEconomics.profitAnnual++;
  FxWAssert(pair.initial.decisionEconomics.profitAnnual == profit, "fusion_score_alias");
  pair.full.decisionEconomics.profitAnnual--;
}

function FxFEngine(catalog, plan, plane, fixed = 0, compact = false, floor = null, openingOut = null)
{
  local day = AIDate.GetCurrentDate();
  local tick = AIController.GetTick();
  local ops = AIController.GetOpsTillSuspend();
  local result = openingOut == null ? FXW_ENGINE(catalog, plan, plane, fixed, compact, floor)
      : FXW_ENGINE(catalog, plan, plane, fixed, compact, floor, openingOut);
  local used = OpexAirCalcDeltaOps(tick, ops);
  if (!FXW_ACTIVE || compact) return result;
  if (fixed > 0) {
    FXW_INITIAL = result;
    FXW_DATE = day;
    FXW_PLAN = plan;
    FXW_PLANE = plane;
    FXF_INITIAL_OPS = used;
  } else if (result != null) {
    tick = AIController.GetTick();
    ops = AIController.GetOpsTillSuspend();
    local candidate = FxFPair(catalog, plan, plane, true);
    local newOps = OpexAirCalcDeltaOps(tick, ops);
    local stable = day == AIDate.GetCurrentDate() && day == FXW_DATE;
    local checked = stable && FXW_PLAN == plan && FXW_PLANE == plane;
    FxFIsolation(candidate);
    if (checked) FxWAssert(FxWEqual({ initial = FXW_INITIAL, full = result }, candidate), "fusion_live_recursive_values");
    AILog.Info("C121_FUSION_LIVE arm=" + plan.arm + " cap=" + result.fleetScanCap
        + " mail=" + (result.engineMailKnown ? (result.mailKnown ? "positive" : "zero") : "unknown")
        + " checked=" + (checked ? 1 : 0) + " old_ops=" + (FXF_INITIAL_OPS + used)
        + " new_ops=" + newOps + " pass=1");
    if (FXW_INPUT == null) FXW_INPUT = { catalog = catalog, plan = plan, plane = plane };
  }
  return result;
}

function FxFStart(owner)
{
  FxWAssert(!owner._loadedFromSave, "fusion_fresh_game");
  FxWPair = FxFPair;
  OpexC121EngineEconomics = FxFEngine;
  OpexC121ChooseRoutePlane = FxWChoose;
  FxWAssert(FxWEqual(FxFPair(null, null, null, false), FxFPair(null, null, null, true)), "fusion_null");
  AILog.Info("C121_FUSION_NULL pass=1");
  AILog.Info("C121_FUSION_START active=1 production_result=old");
}
