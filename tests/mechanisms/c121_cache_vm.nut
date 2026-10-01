/* Test-only VM fixtures. Chooser/geography doubles below use synthetic inputs;
 * they do NOT validate the physical model. Restored before the real game. */
FXC_COUNT <- 0;
FXC_CHOOSER_CALLS <- 0;
FXC_UNION_CALLS <- 0;
FXC_THROW <- false;
FXC_NO_CHOICE <- false;

function FxCAssert(ok, name)
{
  if (!ok) throw "C121_CACHE_ASSERT " + name;
  FXC_COUNT++;
}

function FxCPlan()
{
  return { arm = "newpair", airport = { type = 1, price = 100, maintenance = 3 },
    siteA = { town = { id = 1 }, anchor = 101 },
    siteB = { town = { id = 2 }, anchor = 202 },
    reuseA = false, reuseB = false, hubRoutes = 0, distance = 100, monthlyPax = 50 };
}

function FxCChooser(catalog, plan, lines)
{
  FxCAssert(!("c121Demand" in plan) && !("c121ServiceA" in plan)
      && !("c121ServiceB" in plan) && !("c121EngineStatic" in plan), "miss_clears_snapshot");
  FXC_CHOOSER_CALLS++;
  if (FXC_THROW) throw "C121_CACHE_EXPECTED_ERROR";
  if (FXC_NO_CHOICE) return null;
  plan.c121Demand <- { paxA = FXC_CHOOSER_CALLS };
  plan.c121ServiceA <- { rate = 7 };
  plan.c121ServiceB <- { rate = 9 };
  plan.c121EngineStatic <- { demand = plan.c121Demand };
  plan.b9ShadowMonthly <- 100;
  plan.c121ChosenEngine <- 7;
  plan.c121ChosenMailKnown <- true;
  return { plane = { id = 7 }, economics = { capital = 100, profitAnnual = 30 } };
}

function FxCUnion(town, tile, airport, cargo, stops, station, geometry)
{
  FXC_UNION_CALLS++;
  return { monthly = FXC_UNION_CALLS, produced = 100, townTiles = 10,
      coveredTiles = 5, competition = { buckets = [], totalWeight = 0 } };
}

function FxCMatrix()
{
  local saved = { incremental = C121_CATALOG_INCREMENTAL, economics = C121_AIR_ECONOMICS,
    cache = C121_CATALOG_CACHE, townRev = C121_CATALOG_TOWN_REV,
    stationRev = C121_CATALOG_STATION_REV, stationLines = C121_CATALOG_STATION_LINES,
    airportRev = C121_CATALOG_AIRPORT_REV, airportLearn = C121_CATALOG_AIRPORT_LEARN_REV,
    hubLearn = C121_CATALOG_HUB_LEARN_REV, armLearn = C121_CATALOG_ARM_LEARN_REV,
    epoch = C121_CATALOG_ENDPOINT_EPOCH, endpoints = C121_AIR_ENDPOINT_CACHE,
    geometry = AIR_C121_STATION_COVERAGE_CACHE, cost = CATALOG_COST_ACTIVE,
    perf = C121_AIR_PLAN_PERF, catchment = AIR_CATCHMENT_PROBE,
    production = V93_AIR_DEMAND_PRODUCTION, chooser = OpexC121ChooseRoutePlane,
    unionMonthly = OpexAirB9TownUnionMonthly };
  C121_CATALOG_INCREMENTAL = true;
  C121_AIR_ECONOMICS = true;
  AIR_CATCHMENT_PROBE = false;
  V93_AIR_DEMAND_PRODUCTION = false;
  CATALOG_COST_ACTIVE = null;
  C121_AIR_PLAN_PERF = null;
  C121_CATALOG_CACHE = {};
  C121_CATALOG_TOWN_REV = {};
  C121_CATALOG_STATION_REV = {};
  C121_CATALOG_STATION_LINES = {};
  C121_CATALOG_AIRPORT_REV = {};
  C121_CATALOG_AIRPORT_LEARN_REV = {};
  C121_CATALOG_HUB_LEARN_REV = {};
  C121_CATALOG_ARM_LEARN_REV = {};
  C121_AIR_ENDPOINT_CACHE = {};
  AIR_C121_STATION_COVERAGE_CACHE = {};
  OpexC121ChooseRoutePlane = FxCChooser;
  OpexAirB9TownUnionMonthly = FxCUnion;

  local p = FxCPlan();
  local first = OpexC121CatalogChoice({}, p, null);
  local demand = p.c121Demand;
  local serviceA = p.c121ServiceA;
  local serviceB = p.c121ServiceB;
  local engineStatic = p.c121EngineStatic;
  local hit = FxCPlan();
  hit.c121WinnerFullOps <- 99;
  FxCAssert(OpexC121CatalogChoice({}, hit, null) == first, "choice_identity");
  FxCAssert(FXC_CHOOSER_CALLS == 1 && hit.c121Demand == demand
      && hit.c121ServiceA == serviceA && hit.c121ServiceB == serviceB
      && hit.c121EngineStatic == engineStatic, "complete_hit");
  FxCAssert(hit.b9ShadowMonthly == 100 && hit.c121ChosenEngine == 7
      && hit.c121ChosenMailKnown && !("c121WinnerFullOps" in hit), "metadata_hit");
  FxCAssert(OpexC121PrepareDemandShadow({}, hit, null) == 100
      && hit.c121Demand == demand && hit.c121EngineStatic == engineStatic, "build_keeps_snapshot");
  foreach (revision in [
      { values = C121_CATALOG_TOWN_REV, key = 1 },
      { values = C121_CATALOG_AIRPORT_REV, key = 1 },
      { values = C121_CATALOG_AIRPORT_LEARN_REV, key = 1 },
      { values = C121_CATALOG_ARM_LEARN_REV, key = "newpair" }]) {
    revision.values.rawset(revision.key, 1);
    local calls = FXC_CHOOSER_CALLS;
    local oldDemand = hit.c121Demand;
    OpexC121CatalogChoice({}, hit, null);
    FxCAssert(FXC_CHOOSER_CALLS == calls + 1 && hit.c121Demand != oldDemand
        && hit.c121EngineStatic.demand == hit.c121Demand, "revision_recompute");
  }
  local calls = FXC_CHOOSER_CALLS;
  hit.distance++;
  OpexC121CatalogChoice({}, hit, null);
  FxCAssert(FXC_CHOOSER_CALLS == calls + 1 && !("c121CatalogRefreshEndpoints" in hit), "input_recompute");
  C121_CATALOG_CACHE[hit.c121CatalogKey].date -= 365;
  OpexC121CatalogChoice({}, hit, null);
  FxCAssert(FXC_CHOOSER_CALLS == calls + 2, "age_recompute");
  hit.distance++;
  FXC_THROW = true;
  local caught = false;
  try { OpexC121CatalogChoice({}, hit, null); }
  catch (error) { caught = error == "C121_CACHE_EXPECTED_ERROR"; }
  FXC_THROW = false;
  FxCAssert(caught && !("c121CatalogRefreshEndpoints" in hit), "exception_cleanup");
  FXC_NO_CHOICE = true;
  FxCAssert(OpexC121CatalogChoice({}, hit, null) == null, "negative_miss");
  calls = FXC_CHOOSER_CALLS;
  hit.c121Demand <- { stale = true };
  FxCAssert(OpexC121CatalogChoice({}, hit, null) == null
      && FXC_CHOOSER_CALLS == calls && !("c121Demand" in hit), "negative_hit_no_stale_state");
  FXC_NO_CHOICE = false;

  /* Real endpoint cache path, synthetic union/geometry: no fake ID enters NoAI. */
  local ep = FxCPlan();
  local geo = {};
  local a = OpexAirB9DemandShadowEndpointCargo({}, ep, ep.siteA, false, 0, [], geo);
  local b = OpexAirB9DemandShadowEndpointCargo({}, ep, ep.siteA, false, 0, [], geo);
  FxCAssert(a == b && FXC_UNION_CALLS == 1, "endpoint_hit");
  C121_CATALOG_TOWN_REV[1]++;
  b = OpexAirB9DemandShadowEndpointCargo({}, ep, ep.siteA, false, 0, [], geo);
  FxCAssert(a != b && FXC_UNION_CALLS == 2 && C121_AIR_ENDPOINT_CACHE.len() == 1, "endpoint_town_replace");
  local oldEpoch = C121_CATALOG_ENDPOINT_EPOCH;
  AIR_C121_STATION_COVERAGE_CACHE.rawset(9, [10]);
  C121_CATALOG_STATION_LINES.rawset(9, "removed");
  OpexC121CatalogRefreshStationLines([]);
  FxCAssert(C121_CATALOG_ENDPOINT_EPOCH == oldEpoch + 1
      && AIR_C121_STATION_COVERAGE_CACHE.len() == 0, "other_station_invalidates_geometry");
  oldEpoch = C121_CATALOG_ENDPOINT_EPOCH;
  OpexC121CatalogRefreshStationLines([]);
  FxCAssert(C121_CATALOG_ENDPOINT_EPOCH == oldEpoch, "unchanged_station_no_invalidation");
  a = OpexAirB9DemandShadowEndpointCargo({}, ep, ep.siteA, false, 0, [], geo);
  FxCAssert(a != b && FXC_UNION_CALLS == 3, "endpoint_geometry_recompute");
  a.catalogStamp.date -= 365;
  b = OpexAirB9DemandShadowEndpointCargo({}, ep, ep.siteA, false, 0, [], geo);
  FxCAssert(a != b && FXC_UNION_CALLS == 4, "endpoint_expired");
  ep.c121CatalogRefreshEndpoints <- true;
  a = OpexAirB9DemandShadowEndpointCargo({}, ep, ep.siteA, false, 0, [], geo);
  FxCAssert(a != b && FXC_UNION_CALLS == 5, "endpoint_input_forces_miss");
  delete ep.c121CatalogRefreshEndpoints;
  local stamp = OpexC121EndpointCacheStamp(1, 9);
  local result = { catalogStamp = stamp };
  C121_CATALOG_STATION_REV[9]++;
  FxCAssert(!OpexC121EndpointCacheFresh(result, OpexC121EndpointCacheStamp(1, 9)), "endpoint_station_revision");
  stamp = OpexC121EndpointCacheStamp(1, 9);
  result.catalogStamp = clone stamp;
  result.catalogStamp.date++;
  FxCAssert(!OpexC121EndpointCacheFresh(result, stamp), "endpoint_future_date");
  FxCAssert(!OpexC121EndpointCacheFresh({}, stamp), "endpoint_unversioned");
  C121_CATALOG_INCREMENTAL = saved.incremental;
  C121_AIR_ECONOMICS = saved.economics;
  C121_CATALOG_CACHE = saved.cache;
  C121_CATALOG_TOWN_REV = saved.townRev;
  C121_CATALOG_STATION_REV = saved.stationRev;
  C121_CATALOG_STATION_LINES = saved.stationLines;
  C121_CATALOG_AIRPORT_REV = saved.airportRev;
  C121_CATALOG_AIRPORT_LEARN_REV = saved.airportLearn;
  C121_CATALOG_HUB_LEARN_REV = saved.hubLearn;
  C121_CATALOG_ARM_LEARN_REV = saved.armLearn;
  C121_CATALOG_ENDPOINT_EPOCH = saved.epoch;
  C121_AIR_ENDPOINT_CACHE = saved.endpoints;
  AIR_C121_STATION_COVERAGE_CACHE = saved.geometry;
  CATALOG_COST_ACTIVE = saved.cost;
  C121_AIR_PLAN_PERF = saved.perf;
  AIR_CATCHMENT_PROBE = saved.catchment;
  V93_AIR_DEMAND_PRODUCTION = saved.production;
  OpexC121ChooseRoutePlane = saved.chooser;
  OpexAirB9TownUnionMonthly = saved.unionMonthly;
  AILog.Info("C121_CACHE_VM complete=1 checks=" + FXC_COUNT + " restored=1");
}

/* Live check: a real cached choice must keep the exact economic snapshot at
 * build preparation. At most one check per topology, not a permanent probe. */
FXC_REAL_CHOICE <- OpexC121CatalogChoice;
FXC_SEEN_ARMS <- {};
function FxCLiveChoice(catalog, plan, lines)
{
  local choice = FXC_REAL_CHOICE(catalog, plan, lines);
  if (choice == null || plan.arm in FXC_SEEN_ARMS) return choice;
  local copy = clone plan;
  OpexC121CatalogClearPlanSnapshot(copy);
  local calls = C121_AIR_PLAN_PERF == null ? -1 : C121_AIR_PLAN_PERF.calls;
  local cached = FXC_REAL_CHOICE(catalog, copy, lines);
  FxCAssert(cached == choice && copy.c121Demand == plan.c121Demand
      && copy.c121ServiceA == plan.c121ServiceA && copy.c121ServiceB == plan.c121ServiceB
      && copy.c121EngineStatic == plan.c121EngineStatic, "live_hit_snapshot");
  FxCAssert(OpexC121PrepareDemandShadow(catalog, copy, lines) == plan.b9ShadowMonthly
      && copy.c121Demand == plan.c121Demand && copy.c121EngineStatic == plan.c121EngineStatic
      && (calls < 0 || C121_AIR_PLAN_PERF.calls == calls), "live_no_second_model");
  FXC_SEEN_ARMS.rawset(plan.arm, true);
  AILog.Info("C121_CACHE_LIVE arm=" + plan.arm + " pass=1");
  return choice;
}

FXC_BOUNDARY <- false;
function FxCSaveBoundary(owner)
{
  if (!C121_CATALOG_INCREMENTAL || owner._taskQueue == null) return;
  foreach (task in owner._taskQueue) {
    if (!("c78AirRebuild" in task) || task.c78AirRebuild == null) continue;
    local scan = task.c78AirRebuild;
    if (!("cursor" in scan) || !("done" in scan.cursor) || scan.cursor.done
        || !("c121EndpointCache" in scan.cursor) || scan.cursor.c121EndpointCache.len() == 0) continue;
    FXC_BOUNDARY = true;
    AILog.Info("C121_CACHE_BOUNDARY active=1 entries=" + scan.cursor.c121EndpointCache.len()
        + " date=" + AIDate.GetCurrentDate());
    return;
  }
}

function FxCStart(owner)
{
  if (!owner._loadedFromSave) FxCMatrix();
  else {
    FxCAssert(C121_CATALOG_CACHE.len() == 0 && C121_AIR_ENDPOINT_CACHE == null,
        "reload_discards_derived_caches");
    AILog.Info("C121_CACHE_RELOAD empty=1");
  }
  if (C121_CATALOG_INCREMENTAL) OpexC121CatalogChoice = FxCLiveChoice;
}