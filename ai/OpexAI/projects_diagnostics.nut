/* Extrait de projects.nut (R14) : Sondes passives B6 (causalite, fraicheur, reprix fret). Requis depuis projects.nut. */

/* B6 passive portfolio causality probe. It never changes sorting or admission. */
function OpexB6LogSelectionCausality(path, alternatives, funded, snapshotBudget, snapshotDate,
                                    recycledKeys = null)
{
  if (!DECISION_LOG) return;
  local now = AIDate.GetCurrentDate();
  local liveBudget = OpexAvailableCapital();
  /* 06.5 : rejouer le selecteur courant sur des copies rend le contre-factuel live exact sans
   * modifier les objets projet conserves par le portefeuille (fundScore / early-slot compris). */
  local liveAlternatives = [];
  foreach (p in alternatives) {
    if (p == null) continue;
    local copied = clone p;
    liveAlternatives.push(copied);
  }
  local savedC69 = C69_BOTTLENECK_PROBE;
  C69_BOTTLENECK_PROBE = false;
  local liveFunded = OpexProjectSelectAffordable(
      liveAlternatives, liveBudget, PORTFOLIO_MAX_BATCH);
  C69_BOTTLENECK_PROBE = savedC69;
  local flips = 0;
  local affordable = 0;
  local bestProfit = null;
  foreach (p in alternatives) {
    if (p == null) continue;
    local cap = OpexProjectFinanceCapital(p);
    local snapAffordable = cap <= snapshotBudget;
    local liveAffordable = cap <= liveBudget;
    if (snapAffordable != liveAffordable) flips++;
    if (!snapAffordable) continue;
    affordable++;
    if (bestProfit == null || p.profitAnnual > bestProfit.profitAnnual) bestProfit = p;
  }
  local actual = funded.len() > 0 ? funded[0] : null;
  local liveActual = liveFunded.len() > 0 ? liveFunded[0] : null;
  local actualProfit = actual != null ? actual.profitAnnual : 0;
  local actualCap = actual != null ? OpexProjectFinanceCapital(actual) : 0;
  local actualMode = actual != null ? actual.mode : "none";
  local actualScore = (actual != null && ("fundScore" in actual)) ? actual.fundScore : 0;
  local actualRoi = actual != null ? actual.roi : 0;
  local actualTurnover = (actual != null && ("turnoverBonus" in actual)) ? actual.turnoverBonus : 100;
  local actualGenerationRatio = (actual != null && ("generationRatio" in actual)) ? actual.generationRatio : 0;
  local cfProfit = bestProfit != null ? bestProfit.profitAnnual : 0;
  local cfCap = bestProfit != null ? OpexProjectFinanceCapital(bestProfit) : 0;
  local cfMode = bestProfit != null ? bestProfit.mode : "none";
  local cfScore = (bestProfit != null && ("fundScore" in bestProfit)) ? bestProfit.fundScore : 0;
  local cfRoi = bestProfit != null ? bestProfit.roi : 0;
  local cfTurnover = (bestProfit != null && ("turnoverBonus" in bestProfit)) ? bestProfit.turnoverBonus : 100;
  local cfGenerationRatio = (bestProfit != null && ("generationRatio" in bestProfit)) ? bestProfit.generationRatio : 0;
  local same = (actual != null && bestProfit != null && actual == bestProfit) ? 1 : 0;
  local liveProfit = liveActual != null ? liveActual.profitAnnual : 0;
  local liveCap = liveActual != null ? OpexProjectFinanceCapital(liveActual) : 0;
  local liveMode = liveActual != null ? liveActual.mode : "none";
  local sameLive = 0;
  if (actual == null && liveActual == null) {
    sameLive = 1;
  } else if (actual != null && liveActual != null
      && OpexProjectAttemptKey(actual) == OpexProjectAttemptKey(liveActual)) {
    sameLive = 1;
  }
  local actualLiveAffordable = (actual != null && actualCap <= liveBudget) ? 1 : 0;
  local actualAge = -1;
  if (actual != null && ("economicsDate" in actual)) actualAge = now - actual.economicsDate;
  local actualRecycled = 0;
  local poolRecycled = 0;
  if (recycledKeys != null) {
    if (actual != null && (OpexProjectAttemptKey(actual) in recycledKeys)) actualRecycled = 1;
    foreach (p in funded) {
      if (p != null && (OpexProjectAttemptKey(p) in recycledKeys)) poolRecycled++;
    }
  }
  OpexDecide("B6_PORTFOLIO",
      "path=" + path + " snapshot_budget=" + snapshotBudget + " live_budget=" + liveBudget
      + " budget_delta=" + (liveBudget - snapshotBudget) + " snapshot_age_days=" + (now - snapshotDate)
      + " affordability_flips=" + flips + " alternatives=" + alternatives.len()
      + " affordable_snapshot=" + affordable + " pool_selected=" + funded.len()
      + " max_batch=" + PORTFOLIO_MAX_BATCH + " floor_pct=" + PORTFOLIO_FLOOR_PCT
      + " actual_mode=" + actualMode + " actual_profit=" + actualProfit + " actual_cap=" + actualCap
      + " actual_rank_score=" + actualScore + " actual_roi=" + actualRoi
      + " actual_turnover_bonus=" + actualTurnover + " actual_generation_ratio=" + actualGenerationRatio
      + " cf_mode=" + cfMode + " cf_profit=" + cfProfit + " cf_cap=" + cfCap
      + " cf_rank_score=" + cfScore + " cf_roi=" + cfRoi
      + " cf_turnover_bonus=" + cfTurnover + " cf_generation_ratio=" + cfGenerationRatio
      + " same_profit_choice=" + same + " delta_profit=" + (cfProfit - actualProfit)
      + " live_selected=" + (liveActual != null ? 1 : 0)
      + " live_mode=" + liveMode + " live_profit=" + liveProfit + " live_cap=" + liveCap
      + " same_live_choice=" + sameLive + " live_profit_delta=" + (liveProfit - actualProfit)
      + " actual_live_affordable=" + actualLiveAffordable
      + " actual_age_days=" + actualAge + " actual_recycled=" + actualRecycled
      + " pool_recycled=" + poolRecycled);
}

/* B6/06.11 -- oracle passif "cache vs generation fraiche".
 *
 * Ne jamais recalculer ici une economie a la main : les familles speciales
 * (subvention, extension, joins) ont des constructeurs differents et le
 * precedent essai de refresh en perdait certaines. A la place, _rebuildProjects
 * conserve le vivier cache juste avant la regeneration complete normale puis
 * appelle ce helper avec le vivier fraichement produit. Les deux cotes passent
 * donc par les generateurs reels du jeu. Une cle absente ou non unique est
 * mesuree mais jamais forcee ni interpretee comme equivalente. */
function OpexB6FreshClass(p)
{
  if (p == null) return "unknown";
  if (("payload" in p) && p.payload != null) {
    if (("isSubsidy" in p.payload) && p.payload.isSubsidy) return "subsidy";
    if (("isRoadExtension" in p.payload) && p.payload.isRoadExtension) return "road_extension";
  }
  local mode = ("mode" in p) ? p.mode : "unknown";
  local kind = ("kind" in p) ? p.kind : "";
  if ((mode == "rail" || mode == "road" || mode == "water" || mode == "air") && kind != "") {
    return mode + "_" + kind;
  }
  return mode;
}

function OpexB6FreshBucket(groups, recycledOnly = false)
{
  local buckets = {};
  if (groups == null) return buckets;
  foreach (groupKey, entry in groups) {
    local list = (typeof entry == "array") ? entry : [entry];
    foreach (p in list) {
      if (p == null) continue;
      if (recycledOnly && (!("b6RecycledSinceFresh" in p) || !p.b6RecycledSinceFresh)) continue;
      local key = OpexProjectAttemptKey(p);
      if (!(key in buckets)) buckets.rawset(key, []);
      buckets[key].append(p);
    }
  }
  return buckets;
}

function OpexB6FreshStats(stats, scope)
{
  if (!(scope in stats)) {
    stats.rawset(scope, {
      stale = 0, matched = 0, missing = 0, ambiguous = 0,
      aged = 0, ageSum = 0, ageMax = 0,
      profitChanged = 0, profitDeltaSum = 0, profitAbsSum = 0, profitAbsMax = 0,
      capitalDeltaSum = 0, capitalAbsSum = 0, capitalAbsMax = 0,
      financeDeltaSum = 0, financeAbsSum = 0, financeAbsMax = 0,
      roiDeltaSum = 0, roiAbsSum = 0, roiAbsMax = 0,
    });
  }
  return stats[scope];
}

function OpexB6FreshAbs(v)
{
  return v < 0 ? -v : v;
}

function OpexB6FreshObserve(stats, scope, stale, fresh, now)
{
  local s = OpexB6FreshStats(stats, scope);
  s.matched++;
  local age = ("economicsDate" in stale) ? now - stale.economicsDate : -1;
  if (age >= 0) {
    s.aged++;
    s.ageSum += age;
    if (age > s.ageMax) s.ageMax = age;
  }
  local dp = fresh.profitAnnual - stale.profitAnnual;
  local dc = fresh.capital - stale.capital;
  local df = OpexProjectFinanceCapital(fresh) - OpexProjectFinanceCapital(stale);
  local dr = fresh.roi - stale.roi;
  local ap = OpexB6FreshAbs(dp);
  local ac = OpexB6FreshAbs(dc);
  local af = OpexB6FreshAbs(df);
  local ar = OpexB6FreshAbs(dr);
  if (dp != 0) s.profitChanged++;
  s.profitDeltaSum += dp; s.profitAbsSum += ap; if (ap > s.profitAbsMax) s.profitAbsMax = ap;
  s.capitalDeltaSum += dc; s.capitalAbsSum += ac; if (ac > s.capitalAbsMax) s.capitalAbsMax = ac;
  s.financeDeltaSum += df; s.financeAbsSum += af; if (af > s.financeAbsMax) s.financeAbsMax = af;
  s.roiDeltaSum += dr; s.roiAbsSum += ar; if (ar > s.roiAbsMax) s.roiAbsMax = ar;
}

function OpexB6LogFreshEquivalence(staleProjects, freshProjects, snapshotDate)
{
  if (!DECISION_LOG || staleProjects == null || freshProjects == null) return;
  if (!("candidateGroups" in staleProjects) || staleProjects.candidateGroups == null) return;
  if (!("candidateGroups" in freshProjects) || freshProjects.candidateGroups == null) return;

  /* 06.11 porte sur le replay incremental : ignorer les projets simplement
   * presents avant le rebuild mais jamais recycles depuis leur generation. */
  local staleBuckets = OpexB6FreshBucket(staleProjects.candidateGroups, true);
  local freshBuckets = OpexB6FreshBucket(freshProjects.candidateGroups, false);
  local stats = {};
  local now = AIDate.GetCurrentDate();
  local topKey = null;
  if (("best" in staleProjects) && staleProjects.best != null && staleProjects.best.len() > 0
      && staleProjects.best[0] != null) {
    topKey = OpexProjectAttemptKey(staleProjects.best[0]);
  }

  foreach (key, oldList in staleBuckets) {
    local oldProject = oldList.len() > 0 ? oldList[0] : null;
    local scope = OpexB6FreshClass(oldProject);
    foreach (label in ["all", scope]) OpexB6FreshStats(stats, label).stale++;
    if (oldList.len() != 1) {
      foreach (label in ["all", scope]) OpexB6FreshStats(stats, label).ambiguous++;
      continue;
    }
    if (!(key in freshBuckets)) {
      foreach (label in ["all", scope]) OpexB6FreshStats(stats, label).missing++;
      if (topKey != null && key == topKey) {
        OpexDecide("B6_FRESH_TOP", "status=missing scope=" + scope
                   + " age_days=" + (("economicsDate" in oldProject) ? now - oldProject.economicsDate : -1));
      }
      continue;
    }
    local freshList = freshBuckets[key];
    if (freshList.len() != 1) {
      foreach (label in ["all", scope]) OpexB6FreshStats(stats, label).ambiguous++;
      if (topKey != null && key == topKey) {
        OpexDecide("B6_FRESH_TOP", "status=ambiguous scope=" + scope
                   + " old_n=1 fresh_n=" + freshList.len());
      }
      continue;
    }
    local freshProject = freshList[0];
    foreach (label in ["all", scope]) OpexB6FreshObserve(stats, label, oldProject, freshProject, now);
    if (topKey != null && key == topKey) {
      local age = ("economicsDate" in oldProject) ? now - oldProject.economicsDate : -1;
      OpexDecide("B6_FRESH_TOP", "status=matched scope=" + scope + " age_days=" + age
                 + " stale_profit=" + oldProject.profitAnnual + " fresh_profit=" + freshProject.profitAnnual
                 + " delta_profit=" + (freshProject.profitAnnual - oldProject.profitAnnual)
                 + " stale_capital=" + oldProject.capital + " fresh_capital=" + freshProject.capital
                 + " delta_capital=" + (freshProject.capital - oldProject.capital)
                 + " stale_finance=" + OpexProjectFinanceCapital(oldProject)
                 + " fresh_finance=" + OpexProjectFinanceCapital(freshProject)
                 + " stale_roi=" + oldProject.roi + " fresh_roi=" + freshProject.roi
                 + " rebuild_days=" + (now - snapshotDate));
    }
  }

  foreach (scope, s in stats) {
    OpexDecide("B6_FRESH_EQ", "scope=" + scope + " stale=" + s.stale
               + " matched=" + s.matched + " missing=" + s.missing + " ambiguous=" + s.ambiguous
               + " aged=" + s.aged + " age_sum=" + s.ageSum + " age_max=" + s.ageMax
               + " profit_changed=" + s.profitChanged + " profit_delta_sum=" + s.profitDeltaSum
               + " profit_abs_sum=" + s.profitAbsSum + " profit_abs_max=" + s.profitAbsMax
               + " capital_delta_sum=" + s.capitalDeltaSum + " capital_abs_sum=" + s.capitalAbsSum
               + " capital_abs_max=" + s.capitalAbsMax
               + " finance_delta_sum=" + s.financeDeltaSum + " finance_abs_sum=" + s.financeAbsSum
               + " finance_abs_max=" + s.financeAbsMax
               + " roi_delta_sum=" + s.roiDeltaSum + " roi_abs_sum=" + s.roiAbsSum
               + " roi_abs_max=" + s.roiAbsMax + " rebuild_days=" + (now - snapshotDate));
  }
}

function OpexB6RepriceFreightTop(catalog, lines, project)
{
  if (project == null || !("payload" in project) || project.payload == null) return { status = "unsupported", monthly = 0 };
  if (!("kind" in project) || project.kind != "freight"
      || !("mode" in project) || (project.mode != "rail" && project.mode != "road")) {
    return { status = "unsupported", monthly = 0 };
  }
  local cand = project.payload;
  local srcIndustry = AIIndustry.GetIndustryID(cand.src);
  if (!AIIndustry.IsValidIndustry(srcIndustry)) return { status = "no_source_industry", monthly = 0 };
  local monthly = AIIndustry.GetLastMonthProduction(srcIndustry, cand.cargo);
  if (project.mode == "rail") {
    local srcService = OpexOriginService(lines, cand.src);
    if (BASIN_SHARE && srcService != null) monthly = OpexShareBasin(monthly, lines, srcService.stationId, cand.cargo);
    if (monthly <= 0 && srcService != null && ("dstTown" in cand) && cand.dstTown >= 0) monthly = 45;
  }
  if (monthly <= 0) return { status = "not_generated_monthly", monthly = monthly };
  local economics = null;
  if (project.mode == "rail") {
    economics = OpexLineEconomics(catalog, cand.cargo, cand.distance, monthly, cand.kind);
  } else {
    local engine = (cand.cargo in catalog.roadEngineByCargo) ? catalog.roadEngineByCargo[cand.cargo] : null;
    if (engine == null) return { status = "not_generated_engine", monthly = monthly };
    economics = OpexRoadLineEconomics(catalog, cand.cargo, cand.distance, monthly, engine, cand.kind);
  }
  if (economics == null) return { status = "not_generated_economics", monthly = monthly };
  if (economics.profitAnnual <= 0) return { status = "not_generated_profit", monthly = monthly, freshProfit = economics.profitAnnual };
  if (project.mode == "rail") {
    local iterations = OpexRailIterations(cand.distance);
    local opcodeRatio = (economics.profitAnnual * 1000) / iterations;
    if (VIVIER_RATIO_FILTER && opcodeRatio < 200) return { status = "not_generated_ratio", monthly = monthly, freshProfit = economics.profitAnnual };
  }
  local freshRoi = economics.roi;
  local margin = project.mode == "road" ? ROAD_CAPITAL_MARGIN : 0;
  local immobilise = ("immobilise" in economics) ? economics.immobilise : 0;
  local freshProject = { mode = project.mode, capital = economics.capital,
    budgetCapital = economics.capital + margin + immobilise, payload = null };
  return { status = "ok", monthly = monthly, freshProfit = economics.profitAnnual,
    freshRevenue = economics.revenueAnnual, freshCapital = economics.capital,
    freshFinance = OpexProjectFinanceCapital(freshProject), freshRoi = freshRoi };
}

function OpexB6LogRepricedFreightTop(catalog, lines, funded, recycledKeys, capitalBudget)
{
  if (!DECISION_LOG || funded == null || funded.len() == 0 || recycledKeys == null) return;
  local project = funded[0];
  if (project == null) return;
  local key = OpexProjectAttemptKey(project);
  if (!(key in recycledKeys)) return;
  if (!("kind" in project) || project.kind != "freight") return;
  if (!("mode" in project) || (project.mode != "rail" && project.mode != "road")) return;
  local fresh = OpexB6RepriceFreightTop(catalog, lines, project);
  local age = ("economicsDate" in project) ? AIDate.GetCurrentDate() - project.economicsDate : -1;
  local staleFinance = OpexProjectFinanceCapital(project);
  local freshProfit = ("freshProfit" in fresh) ? fresh.freshProfit : 0;
  local freshRevenue = ("freshRevenue" in fresh) ? fresh.freshRevenue : 0;
  local freshCapital = ("freshCapital" in fresh) ? fresh.freshCapital : 0;
  local freshFinance = ("freshFinance" in fresh) ? fresh.freshFinance : 0;
  local freshRoi = ("freshRoi" in fresh) ? fresh.freshRoi : 0;
  local freshScore = (fresh.status == "ok" && freshFinance > 0)
      ? OpexProjectScore(freshProfit, freshFinance) : 0.0;
  local runner = funded.len() > 1 ? funded[1] : null;
  local runnerScore = (runner != null && ("fundScore" in runner))
      ? OpexProjectSelectionScore(runner, "fundScore") : 0.0;
  local runnerRevenue = runner != null ? runner.revenueAnnual : 0;
  local decision = "unsupported";
  if (fresh.status == "ok") {
    if (freshFinance > capitalBudget) decision = "change_unaffordable";
    else if (runner == null) decision = "keep";
    else if (freshScore > runnerScore) decision = "keep";
    else if (freshScore < runnerScore) decision = "change_rank";
    else if (freshRevenue > runnerRevenue) decision = "keep";
    else if (freshRevenue < runnerRevenue) decision = "change_tie_revenue";
    else decision = "ambiguous_exact_tie";
  } else if (fresh.status == "not_generated_monthly"
      || fresh.status == "not_generated_engine"
      || fresh.status == "not_generated_economics"
      || fresh.status == "not_generated_profit"
      || fresh.status == "not_generated_ratio") {
    decision = "change_not_generated";
  }
  OpexDecide("B6_RECYCLE_TOP_PRICE", "status=" + fresh.status + " mode=" + project.mode
             + " decision=" + decision
             + " age_days=" + age + " monthly=" + fresh.monthly
             + " stale_profit=" + project.profitAnnual + " fresh_profit=" + freshProfit
             + " fresh_revenue=" + freshRevenue
             + " delta_profit=" + (freshProfit - project.profitAnnual)
             + " stale_capital=" + project.capital + " fresh_capital=" + freshCapital
             + " delta_capital=" + (freshCapital - project.capital)
             + " stale_finance=" + staleFinance + " fresh_finance=" + freshFinance
             + " stale_roi=" + project.roi + " fresh_roi=" + freshRoi
             + " fresh_score=" + freshScore + " runner_score=" + runnerScore
             + " runner_mode=" + (runner != null ? runner.mode : "none")
             + " budget=" + capitalBudget);
}
