/* Test copy only: bounded hub-hub replays on identical captured inputs.
 * No fixture output is used for construction or economic qualification. */
FQE_HUB <- OpexAirPlansHubToHub;
FQE_COUNT <- 0;
function FqeCopy(x) {
  if (typeof x == "table") {
    local y = {};
    foreach (k, v in x) y.rawset(k, FqeCopy(v));
    return y;
  }
  if (typeof x == "array") {
    local y = []; foreach (v in x) y.append(FqeCopy(v)); return y;
  }
  return x;
}
function FqeEqual(a, b) {
  if (typeof a != typeof b) return false;
  if (typeof a == "table" || typeof a == "array") {
    if (a.len() != b.len()) return false;
    foreach (k, v in a) if (!(k in b) || !FqeEqual(v, b[k])) return false;
    return true;
  }
  return a == b;
}
function FqeSignature(plans) {
  local result = [];
  foreach (p in plans) {
    local row = {};
    foreach (k in ["arm", "distance", "monthlyPax", "planes", "targetPlanes",
        "capital", "economics", "decisionEconomics", "reuseA", "reuseB"]) {
      if (k in p) row.rawset(k, FqeCopy(p[k]));
    }
    if ("plane" in p) row.engine <- p.plane.id;
    if ("airport" in p) row.airport <- p.airport.type;
    if ("siteA" in p) row.a <- p.siteA.anchor;
    if ("siteB" in p) row.b <- p.siteB.anchor;
    result.append(row);
  }
  return result;
}
function FqeReplay(input, combo, airport, plane, fast) {
  local ctx = clone input;
  ctx.catalog = FqeCopy(input.catalog);
  ctx.hubs = [];
  for (local i=0; i<input.hubs.len() && i<4; i++) ctx.hubs.append(FqeCopy(input.hubs[i]));
  ctx.projects = [];
  ctx.bestPlan = null;
  ctx.sliced = false;
  ctx.resumeState = {};
  ctx.opsBudget = 0;
  ctx.deadlineTick = 0;
  C80_AIR_EVAL_FAST = fast;
  AIR_ECONOMICS_MEMO = {};
  AIR_TRIP_MEMO = {};
  AIR_MEMO_MONTH = AIDate.GetYear(AIDate.GetCurrentDate())*12+AIDate.GetMonth(AIDate.GetCurrentDate());
  C121_AIR_ENDPOINT_CACHE = {};
  C121_AIR_PLAN_PERF = null;
  ctx.t0_all = AIController.GetTick();
  ctx.l0_all = AIController.GetOpsTillSuspend();
  local tick = AIController.GetTick();
  local ops = AIController.GetOpsTillSuspend();
  FQE_HUB(ctx, combo, airport, plane);
  local used = OpexAirCalcDeltaOps(tick, ops);
  return { ops=used, rows=FqeSignature(ctx.projects) };
}
function FqeHub(ctx, combo, airport, plane) {
  if (FQE_COUNT < 8 && ctx.hubs.len() >= 2) {
    FQE_COUNT++;
    local saved = { fast=C80_AIR_EVAL_FAST, econ=AIR_ECONOMICS_MEMO,
      trip=AIR_TRIP_MEMO, month=AIR_MEMO_MONTH,
      endpoint=C121_AIR_ENDPOINT_CACHE, perf=C121_AIR_PLAN_PERF };
    local date = AIDate.GetCurrentDate();
    /* Alternate order; both paths start with fresh caches. */
    local old = null; local fresh = null;
    if (FQE_COUNT % 2 == 1) {
      old = FqeReplay(ctx, combo, airport, plane, false);
      fresh = FqeReplay(ctx, combo, airport, plane, true);
    } else {
      fresh = FqeReplay(ctx, combo, airport, plane, true);
      old = FqeReplay(ctx, combo, airport, plane, false);
    }
    local stable = date == AIDate.GetCurrentDate();
    local equal = FqeEqual(old.rows, fresh.rows);
    C80_AIR_EVAL_FAST = saved.fast;
    AIR_ECONOMICS_MEMO = saved.econ; AIR_TRIP_MEMO = saved.trip;
    AIR_MEMO_MONTH = saved.month;
    C121_AIR_ENDPOINT_CACHE = saved.endpoint; C121_AIR_PLAN_PERF = saved.perf;
    AILog.Info("EVAL_FAST_FIXTURE phase=hub_hub checked=" + (stable?1:0)
      + " equivalent=" + (equal?1:0) + " old_ops=" + old.ops + " new_ops=" + fresh.ops
      + " plans=" + old.rows.len() + " order=" + (FQE_COUNT % 2));
  }
  return FQE_HUB(ctx, combo, airport, plane);
}
function FqeStart() {
  OpexAirPlansHubToHub = FqeHub;
  AILog.Info("EVAL_FAST_FIXTURE_START active=1 bounded_hubs=4 cold_caches=1");
}
