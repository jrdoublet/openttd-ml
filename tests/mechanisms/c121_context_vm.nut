/* Copy-only observer. Both chooser paths see the same prepared pair snapshot;
 * natural decisions return the OFF witness. Production functions are tested. */
FXCTX_DEMAND <- OpexC121PrepareDemandShadow;
FXCTX_TRIP <- OpexC121AirTripModel;
FXCTX_TRIP_COUNT <- 0;
FXCTX_COUNT_TRIPS <- false;
FXCTX_DONE <- false;

function FxCtxTrip(plan, plane)
{
  if (FXCTX_COUNT_TRIPS) FXCTX_TRIP_COUNT++;
  return FXCTX_TRIP(plan, plane);
}

function FxCtxPreparedDemand(catalog, plan, lines = null)
{
  return plan.c121Demand;
}

function FxCtxPair(catalog, plan, plane, enabled)
{
  local ctx = enabled ? OpexC121PrepareEngineContext(catalog, plan, plane) : null;
  local upper = OpexC121InitialEngineUpperScore(catalog, plan, plane, ctx);
  local compact = OpexC121EngineEconomics(catalog, plan, plane,
      C121_AAA_LINE ? 2 : 1, true, null, null, ctx);
  local pair = OpexC121WinnerEconomics(catalog, plan, plane, C121_AIR_WINNER_FUSION, ctx);
  pair.upperScore <- upper;
  pair.compact <- compact;
  return pair;
}

function FxCtxGuards(catalog, plan, plane)
{
  local ctx = OpexC121PrepareEngineContext(catalog, plan, plane);
  FxWAssert(ctx != null, "context_nonnull");
  FxWAssert(OpexC121EngineContextMatches(ctx, catalog, plan, plane), "context_fresh");
  FXCTX_COUNT_TRIPS = true;
  FXCTX_TRIP_COUNT = 0;
  OpexC121EngineEconomics(catalog, plan, plane, 1, false, null, null, ctx);
  FxWAssert(FXCTX_TRIP_COUNT == 0, "context_trip_reused");
  FXCTX_COUNT_TRIPS = false;
  local cases = 0;
  foreach (key in ["date", "distance", "price", "incomeDays", "paxCapacity", "mailCapacity"]) {
    local stale = clone ctx;
    stale[key] = stale[key] - 1;
    FxWAssert(!OpexC121EngineContextMatches(stale, catalog, plan, plane), "context_reject_" + key);
    FXCTX_COUNT_TRIPS = true;
    FXCTX_TRIP_COUNT = 0;
    local withStale = OpexC121EngineEconomics(catalog, plan, plane, 1, false, null, null, stale);
    FxWAssert(FXCTX_TRIP_COUNT == 1, "context_fallback_" + key);
    FXCTX_COUNT_TRIPS = false;
    local expected = OpexC121EngineEconomics(catalog, plan, plane, 1, false);
    FxWAssert(FxWEqual(withStale, expected), "context_fallback_values_" + key);
    cases++;
  }
  FxWAssert(!OpexC121EngineContextMatches(ctx, catalog, clone plan, plane), "context_pair_identity");
  FxWAssert(!OpexC121EngineContextMatches(ctx, clone catalog, plan, plane), "context_catalog_identity");
  FxWAssert(!OpexC121EngineContextMatches(ctx, catalog, plan, clone plane), "context_engine_identity");
  local st = plan.c121EngineStatic;
  plan.c121EngineStatic = clone st;
  FxWAssert(!OpexC121EngineContextMatches(ctx, catalog, plan, plane), "context_parent_revision");
  plan.c121EngineStatic = st;
  local demand = plan.c121Demand;
  plan.c121Demand = clone demand;
  FxWAssert(!OpexC121EngineContextMatches(ctx, catalog, plan, plane), "context_demand_revision");
  plan.c121Demand = demand;
  local caps = C121_AIR_ENGINE_CAPACITY_OBS;
  C121_AIR_ENGINE_CAPACITY_OBS = clone caps;
  C121_AIR_ENGINE_CAPACITY_OBS.rawset(plane.id, { pax = ctx.paxCapacity, mail = ctx.mailCapacity + 1 });
  FxWAssert(!OpexC121EngineContextMatches(ctx, catalog, plan, plane), "context_capacity_revision");
  C121_AIR_ENGINE_CAPACITY_OBS = caps;
  ctx = OpexC121PrepareEngineContext(catalog, plan, plane);
  FxWAssert(OpexC121EngineContextMatches(ctx, catalog, plan, plane), "context_restored");
  AILog.Info("C121_CONTEXT_GUARDS checks=" + (cases + 6) + " reused=1 restored=1 pass=1");
}

function FxCtxChoose(catalog, plan, lines = null)
{
  local day = AIDate.GetCurrentDate();
  C121_AIR_ENGINE_CONTEXT = false;
  local old = FXW_CHOOSE(catalog, plan, lines);
  local oldOps = (("c121EngineScanOps" in plan) ? plan.c121EngineScanOps : 0)
      + (("c121WinnerFullOps" in plan) ? plan.c121WinnerFullOps : 0);
  local prepared = clone plan;
  OpexC121PrepareDemandShadow = FxCtxPreparedDemand;
  C121_AIR_ENGINE_CONTEXT = true;
  local candidate = FXW_CHOOSE(catalog, prepared, lines);
  C121_AIR_ENGINE_CONTEXT = false;
  OpexC121PrepareDemandShadow = FXCTX_DEMAND;
  local newOps = (("c121EngineScanOps" in prepared) ? prepared.c121EngineScanOps : 0)
      + (("c121WinnerFullOps" in prepared) ? prepared.c121WinnerFullOps : 0);
  local checked = day == AIDate.GetCurrentDate() && old != null && candidate != null;
  if (checked) FxWAssert(FxWEqual(old, candidate), "context_chooser_recursive_values");
  AILog.Info("C121_CONTEXT_LIVE arm=" + plan.arm + " checked=" + (checked ? 1 : 0)
      + " old_ops=" + oldOps + " new_ops=" + newOps + " pass=1");
  if (!FXCTX_DONE && checked) {
    FxCtxGuards(catalog, plan, old.plane);
    FxWPair = FxCtxPair;
    FxWMatrix(catalog, plan, old.plane);
    FXCTX_DONE = true;
  }
  return old;
}

function FxCtxStart(owner)
{
  FxWAssert(!owner._loadedFromSave && !C121_AIR_ENGINE_CONTEXT, "context_fresh_off_witness");
  OpexC121AirTripModel = FxCtxTrip;
  OpexC121ChooseRoutePlane = FxCtxChoose;
  FxWAssert(OpexC121PrepareEngineContext(null, null, null) == null, "context_null");
  AILog.Info("C121_CONTEXT_START fusion=" + (C121_AIR_WINNER_FUSION ? 1 : 0) + " witness=0 pass=1");
}
