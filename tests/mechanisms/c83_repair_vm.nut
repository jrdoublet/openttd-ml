/* Exercices diriges du helper de production, dans une COPIE de l'IA seulement. */
FXC83 <- null;
function FxC83Assert(ok, label) { if (!ok) throw "C83_REPAIR_ASSERT " + label; }
function FxC83Context(anchors, budget = 0) {
  local repair = { anchors = anchors, scan = null, localCombos = 0, fallbackCombos = 0,
    targetKept = 0, targetSearched = 0, partners = 0 };
  return { sliced = true, resumeState = { c83Repair = repair, sites = null, totalOps = 0,
      perfOpsSites = 0, perfProbesCount = 0, perfCheapSkip = 0, perfSitesFound = 0 },
    targetTownId = 1, towns = [{ id = 1, pop = 1000 }, { id = 2, pop = 1000 }, { id = 3, pop = 1000 }],
    limit = 3, lines = [], servedDiag = null, c83TopTownIds = {}, stationLimitedTowns = {},
    opsBudget = budget, deadlineTick = 0, t0_all = 0, l0_all = 0, c83RepairCombo = false,
    perfOpsSites = 0, perfProbesCount = 0, perfCheapSkip = 0, perfSitesFound = 0, sites = [] };
}
function FxC83Start(ai) {
  local saved = { slot = OpexAirSlotTownId, live = OpexAirSiteStillBuildable,
    find = OpexAirFindSite, served = OpexAirTownServed, second = OpexAirC83SecondSlotOpen,
    ops = OpexAirCalcDeltaOps, cache = AIR_SITE_CACHE, cacheOn = AIR_SITE_CACHE_ENABLED,
    pop = V93_AIRPORT_NO_POP_FLOOR };
  OpexAirSlotTownId = function(anchor) { return anchor == 101 ? 9 : 1; };
  OpexAirSiteStillBuildable = function(site, airport, plane, reuse, limited = null) {
    return !(site.anchor in FXC83.invalid);
  };
  OpexAirFindSite = function(town, airport, probes, required = -1) {
    FxC83Assert(town.id == 1 && required == 1, "only_target_searched");
    FXC83.finds++;
    probes.tested++;
    return { town = town, anchor = 110 };
  };
  OpexAirTownServed = function(town, lines, diag = null) { return false; };
  OpexAirC83SecondSlotOpen = function(town) { return false; };
  OpexAirCalcDeltaOps = function(tick, ops) { FXC83.ops += 5; return FXC83.ops; };
  V93_AIRPORT_NO_POP_FLOOR = false;
  local combo = { kind = "large" };
  local airport = { type = 1 };
  for (local caseId = 1; caseId <= 7; caseId++) {
    FXC83 = { invalid = {}, finds = 0, ops = 0 };
    local anchors = { ["1_1"] = 100, ["2_1"] = 200, ["3_1"] = 300 };
    if (caseId == 2) FXC83.invalid.rawset(100, true);
    if (caseId == 3) anchors.rawset("1_1", 101); // commercial town != physical slot
    if (caseId == 4) anchors = { ["1_1"] = 100 };
    if (caseId == 5) { FXC83.invalid.rawset(200, true); FXC83.invalid.rawset(300, true); }
    if (caseId == 7) { delete anchors["1_1"]; FXC83.invalid.rawset(110, true); }
    local ctx = FxC83Context(anchors, caseId == 6 ? 5 : 0);
    local outcome = OpexC83RepairFindSites(ctx, 0, combo, airport, {});
    if (caseId == 6) {
      FxC83Assert(outcome.handled && !outcome.done && ctx.resumeState.sites == null, "yield_atomic");
      for (local guard = 0; guard < 5 && !outcome.done; guard++) {
        FXC83.ops = 0;
        outcome = OpexC83RepairFindSites(ctx, 0, combo, airport, {});
      }
      FxC83Assert(outcome.done && FXC83.finds == 0, "resume_without_rescan");
    }
    if (caseId == 4 || caseId == 5) {
      FxC83Assert(!outcome.handled && outcome.done && !ctx.c83RepairCombo, "fallback");
    } else {
      FxC83Assert(outcome.handled && outcome.done && ctx.c83RepairCombo, "local");
      if (caseId == 7) FxC83Assert(ctx.sites.len() == 2, "invalid_search_not_published");
      else FxC83Assert(ctx.sites.len() == 3 && ctx.sites[0].town.id == 1, "target_first_partners_preserved");
      if (caseId == 2 || caseId == 3) FxC83Assert(ctx.sites[0].anchor == 110 && FXC83.finds == 1, "replaced");
    }
    if (caseId == 1 || caseId == 4 || caseId == 5) FxC83Assert(FXC83.finds == 0, "valid_target_not_searched");
    AILog.Info("C83_REPAIR_VM case=" + caseId + " pass=1");
  }
  AIR_SITE_CACHE_ENABLED = true;
  AIR_SITE_CACHE = { ["2_1"] = 222, ["3_1"] = null };
  local old = { mode = "air", payload = { airport = airport,
    siteA = { town = { id = 1 }, anchor = 100 }, siteB = { town = { id = 2 }, anchor = 200 }, reuseA = true } };
  local snap = OpexC83RepairSnapshot({ candidateGroups = { route = [old] } });
  FxC83Assert(!("1_1" in snap.anchors) && snap.anchors["2_1"] == 222 && !("3_1" in snap.anchors), "snapshot");
  FxC83Assert(old.payload.siteB.anchor == 200, "no_alias_mutation");
  OpexAirSlotTownId = saved.slot; OpexAirSiteStillBuildable = saved.live;
  OpexAirFindSite = saved.find; OpexAirTownServed = saved.served;
  OpexAirC83SecondSlotOpen = saved.second; OpexAirCalcDeltaOps = saved.ops;
  AIR_SITE_CACHE = saved.cache; AIR_SITE_CACHE_ENABLED = saved.cacheOn;
  V93_AIRPORT_NO_POP_FLOOR = saved.pop;
  FXC83 = null;
  AILog.Info("C83_REPAIR_VM complete=1 cases=8 restored=1");
}
