/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexC50ResetNonExpansionLedger()
{
  C50_NON_EXPANSION_LEDGER = {
    air = {
      want_sum = 0,
      ref_Y = 0,
      ref_V = 0,
      ref_D = 0,
      ref_L = 0,
      ref_C = 0,
      ref_Q = 0,
      ref_S = 0,
      ref_W = 0,
      ref_M = 0,
      ref_X = 0,
      ref_R = 0
    },
    rail = {
      cash_refused = 0,
      prep_failed = 0,
      upgrade_failed = 0,
      second_built = 0,
      double_built = 0
    },
    road = {
      physical_cap_hit = 0,
      congestion_hit = 0,
      no_demand = 0,
      loss_hit = 0,
      cash_refused = 0,
      other_refused = 0,
      refill_built = 0
    }
  };
}
function OpexSign(anchor, name)
{
  if (!DEBUG_SIGNS) return;
  AISign.BuildSign(anchor, name);
}
function OpexDecide(kind, fields)
{
  local date = AIDate.GetCurrentDate();
  if (_currentTaskName != null && !_currentTaskLogged && kind != "TASK") {
    _currentTaskLogged = true;
    local cur = _currentTaskName;
    _currentTaskName = null;
    OpexDecide("TASK", "name=" + cur);
    _currentTaskName = cur;
  }
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* B9/G4 : gate dedie au diagnostic catchment. Ne pas reutiliser DECISION_LOG :
 * il instrumente toute l'IA et son cout a deja ete mesure comme perturbant. */
function OpexAirCatchmentLog(kind, fields)
{
  if (!AIR_CATCHMENT_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C39.0 : le journal de la sonde est indépendant de DECISION_LOG. Ce dernier instrumente toute
 * l'IA et change son budget d'opcodes ; C39 doit pouvoir observer le seul routeur passif. */
function OpexC39Log(kind, fields)
{
  if (!C39_INVALIDATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C41.11 reste lisible sans activer le bus C39 : il mesure le scheduler historique lui-meme. */
function OpexC41SchedulerLog(kind, fields)
{
  if (!C41_SLACK_LEDGER && !C41_MONTHLY_BUSY_LEDGER
      && !C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C41.46 : sonde independante de la famille C41.11/13/14 -- son propre gate, comme les sondes
 * rail-lost ci-dessous. OpexC41SchedulerLog aurait silencieusement avale ces lignes tant qu'aucun
 * des trois autres flags n'est actif (piege trouve au premier smoke test). */
function OpexC41RailSliceLog(fields)
{
  if (!C41_RAIL_SLICE_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_SLICE_LEDGER " + fields);
}
/* C49 : gate dedie. Ne jamais reutiliser celui de C48/C39/C41 : armer seulement cette sonde
 * doit suffire a publier ses lignes. */
function OpexC49ScarcityLog(fields)
{
  if (!C49_SCARCITY_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C49_SCARCITY " + fields);
}
/* Tunnel mensuel : gate dedie, independant de C63/C48/decision_log. Un AILog par passe
 * pour ne pas perdre le mois courant (le jeu s'arrete souvent au 1er decembre). */
function OpexMonthlyFunnelLog(fields)
{
  if (!MONTHLY_FUNNEL) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " MONTHLY_FUNNEL " + fields);
}

/* C63+C58 : gate dedie. Compteurs memoire en boucle chaude, AILog seulement au flush annuel. */
function OpexC63InvestLog(fields)
{
  if (!C63_INVEST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C63_INVEST " + fields);
}

function OpexC63ModeSpend()
{
  return { planned_ok = 0, actual_ok = 0, n_ok = 0, planned_fail = 0, actual_fail = 0, n_fail = 0 };
}

function OpexC63OppBucket()
{
  return { n = 0, days = 0 };
}

function OpexC63ResetLedger()
{
  C63_INVEST_LEDGER = {
    spend = {
      rail = OpexC63ModeSpend(), road = OpexC63ModeSpend(),
      air = OpexC63ModeSpend(), water = OpexC63ModeSpend(), fleet = OpexC63ModeSpend()
    },
    opp = {
      absent = OpexC63OppBucket(), invalid = OpexC63OppBucket(),
      unaffordable = OpexC63OppBucket(), demand = OpexC63OppBucket(),
      waiting_compute = OpexC63OppBucket(), launched = OpexC63OppBucket()
    },
    absent_causes = {
      empty_pool = OpexC63OppBucket(),
      unprofitable = OpexC63OppBucket(),
      already_served = OpexC63OppBucket(),
      no_site = OpexC63OppBucket(),
      mode_cargo_filter = OpexC63OppBucket(),
      selection_empty = OpexC63OppBucket(),
      stage_empty = OpexC63OppBucket(),
      cache_exhausted = OpexC63OppBucket(),
      abandon_filtered = OpexC63OppBucket()
    },
    lastDate = -1,
    lastKind = "",
    lastAbsentCause = "",
    ledgerYear = -1,
    flushedYear = -1,
    cachedTick = -1,
    cachedDate = -1,
    cachedAvailable = 0,
    lines = []
  };
}

function OpexC63SpendSlot(mode)
{
  if (C63_INVEST_LEDGER == null || C63_INVEST_LEDGER.spend == null) return null;
  if (mode in C63_INVEST_LEDGER.spend) return C63_INVEST_LEDGER.spend[mode];
  return C63_INVEST_LEDGER.spend.fleet;
}

function OpexC63RecordSpend(mode, planned, actual, ok)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  OpexC63EnsureYear(AIDate.GetYear(AIDate.GetCurrentDate()));
  local slot = OpexC63SpendSlot(mode);
  if (slot == null) return;
  if (ok) {
    slot.planned_ok += planned;
    slot.actual_ok += actual;
    slot.n_ok++;
  } else {
    slot.planned_fail += planned;
    slot.actual_fail += actual;
    slot.n_fail++;
  }
}

function OpexC63ChildLen(root, key, inner)
{
  if (root == null || !(key in root) || root[key] == null) return -1;
  local node = root[key];
  if (inner == null || inner == "") {
    return node.len();
  }
  if (!(inner in node) || node[inner] == null) return -1;
  return node[inner].len();
}

function OpexC63StatCount(st, key, fallback)
{
  if (st != null && (key in st) && st[key] != null) return st[key];
  return fallback;
}

function OpexC63ClassifyAbsent(projects)
{
  if (projects == null) return "empty_pool";
  local st = ("stats" in projects) ? projects.stats : null;
  if (st != null && ("emptyCause" in st) && st.emptyCause != null && st.emptyCause != "" && st.emptyCause != "all_unaffordable") {
    return st.emptyCause;
  }
  local considered = (st != null && ("budgetConsidered" in st)) ? st.budgetConsidered : 0;
  if (considered > 0) return "selection_empty";

  if (st != null) {
    local cacheScanned = OpexC63StatCount(st, "cacheScanned", -1);
    local cacheRetained = OpexC63StatCount(st, "cacheRetained", -1);
    if (cacheScanned > 0 && cacheRetained == 0) {
      return "cache_exhausted";
    }
    local abandonFiltered = OpexC63StatCount(st, "abandonFiltered", -1);
    local modeCandidates = OpexC63StatCount(st, "modeCandidates", -1);
    if (abandonFiltered > 0 && modeCandidates == 0) {
      return "abandon_filtered";
    }
    local railC = OpexC63StatCount(st, "railCandidates", OpexC63ChildLen(projects, "rail", "candidates"));
    local roadC = OpexC63StatCount(st, "roadCandidates", OpexC63ChildLen(projects, "road", "candidates"));
    local airP = OpexC63StatCount(st, "airPlansCount", OpexC63ChildLen(projects, "airPlans", ""));
    local waterP = OpexC63StatCount(st, "waterPlansCount", OpexC63ChildLen(projects, "waterPlans", ""));
    if (railC == 0 && roadC == 0 && airP == 0 && waterP == 0) {
      return "stage_empty";
    }
  }

  local unprofitable = 0;
  local alreadyServed = 0;
  local noSite = 0;
  local modeCargoFilter = 0;
  local pairsTotal = 0;

  if (("rail" in projects) && projects.rail != null && ("stats" in projects.rail) && projects.rail.stats != null) {
    local rst = projects.rail.stats;
    if ("pairsTotal" in rst) pairsTotal += rst.pairsTotal;
    if ("profitNonPositive" in rst) unprofitable += rst.profitNonPositive;
    if ("ratioTooLow" in rst) unprofitable += rst.ratioTooLow;
    if ("pairsOriginServed" in rst) alreadyServed += rst.pairsOriginServed;
    if ("unsitable" in rst) noSite += rst.unsitable;
    if ("pairsJoinImpossible" in rst) noSite += rst.pairsJoinImpossible;
    if ("distanceShort" in rst) modeCargoFilter += rst.distanceShort;
    if ("distanceLong" in rst) modeCargoFilter += rst.distanceLong;
  }

  if (("road" in projects) && projects.road != null && ("stats" in projects.road) && projects.road.stats != null) {
    local rdst = projects.road.stats;
    if ("pairsInBand" in rdst) pairsTotal += rdst.pairsInBand;
    /* M1 : un candidat positif sous le repere ROAD_MIN_PROFIT_ANNUAL est conserve,
     * donc il ne doit pas expliquer un vivier vide comme "unprofitable". */
    if ("profitNonPositive" in rdst) unprofitable += rdst.profitNonPositive;
    else if ("profitTooLow" in rdst) unprofitable += rdst.profitTooLow; // vieille forme de sauvegarde
    if ("townRejected" in rdst) alreadyServed += rdst.townRejected;
    if ("roadDistanceShort" in rdst) modeCargoFilter += rdst.roadDistanceShort;
    if ("roadDistanceLong" in rdst) modeCargoFilter += rdst.roadDistanceLong;
  }

  if (pairsTotal == 0) return "empty_pool";

  local maxCount = unprofitable;
  local bestReason = "unprofitable";
  if (alreadyServed > maxCount) {
    maxCount = alreadyServed;
    bestReason = "already_served";
  }
  if (noSite > maxCount) {
    maxCount = noSite;
    bestReason = "no_site";
  }
  if (modeCargoFilter > maxCount) {
    maxCount = modeCargoFilter;
    bestReason = "mode_cargo_filter";
  }
  if (maxCount == 0) return "empty_pool";
  return bestReason;
}

function OpexC63ClassifyOpportunity(reason, available, need, railSearch)
{
  if (railSearch) return "waiting_compute";
  if (need > available) return "unaffordable";
  if (reason == "insufficient_cash" || reason == "cash_at_build") return "unaffordable";
  if (reason == "search_in_progress") return "waiting_compute";
  if (reason == "line_cap_reached" || reason == "town_road_line_cap" || reason == "no_demand") return "demand";
  if (reason == null || reason == "") return "invalid";
  return "invalid";
}

function OpexC63RecordOpportunity(kind, daysForKind, absentCause = "")
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  if (!(kind in C63_INVEST_LEDGER.opp)) return;
  C63_INVEST_LEDGER.opp[kind].n++;
  if (kind == "absent" && absentCause != "" && ("absent_causes" in C63_INVEST_LEDGER)
      && (absentCause in C63_INVEST_LEDGER.absent_causes)) {
    C63_INVEST_LEDGER.absent_causes[absentCause].n++;
  }
  OpexC63AddOpportunityDays(kind, daysForKind, absentCause);
}

/* Les observations et le temps passe ne sont pas la meme grandeur. Une nouvelle passe compte
 * l'etat observe MAINTENANT, mais l'intervalle depuis la passe precedente appartient a l'etat
 * precedent. Cette fonction ajoute donc uniquement une duree, sans fabriquer un compteur n. */
function OpexC63AddOpportunityDays(kind, daysForKind, absentCause = "")
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null || daysForKind <= 0) return;
  if (!(kind in C63_INVEST_LEDGER.opp)) return;
  C63_INVEST_LEDGER.opp[kind].days += daysForKind;
  if (kind == "absent" && absentCause != "" && ("absent_causes" in C63_INVEST_LEDGER)
      && (absentCause in C63_INVEST_LEDGER.absent_causes)) {
    C63_INVEST_LEDGER.absent_causes[absentCause].days += daysForKind;
  }
}

function OpexC63RecordLine(mode, age, predProfit, realProfit, predRev, realRev, vehCount, lineId, year)
{
  if (!C63_INVEST_PROBE) return;
  OpexC63InvestLog("phase=line year=" + year + " line=" + lineId + " mode=" + mode
      + " age=" + age + " pred_p=" + predProfit + " real_p=" + realProfit
      + " pred_r=" + predRev + " real_r=" + realRev + " vehs=" + vehCount);
}

function OpexC63RecordSpendResult(mode, result, plannedFallback)
{
  if (!C63_INVEST_PROBE || result == null) return;
  local planned = plannedFallback;
  if ("plannedCapital" in result) planned = result.plannedCapital;
  else if ("capital" in result) planned = result.capital;
  local actual = ("actualCost" in result) ? result.actualCost : 0;
  OpexC63RecordSpend(mode, planned, actual, result.ok);
}

function OpexC63CachedAvailable()
{
  local today = AIDate.GetCurrentDate();
  if (C63_INVEST_LEDGER.cachedDate == today) return C63_INVEST_LEDGER.cachedAvailable;
  local available = OpexAvailableCapital();
  C63_INVEST_LEDGER.cachedDate = today;
  C63_INVEST_LEDGER.cachedAvailable = available;
  return available;
}

function OpexC63YearStart(year)
{
  return AIDate.GetDate(year, 1, 1);
}

function OpexC63EnsureYear(nowYear)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  if (nowYear < 1970) return;
  if (C63_INVEST_LEDGER.ledgerYear < 0) {
    C63_INVEST_LEDGER.ledgerYear = nowYear;
    return;
  }
  while (C63_INVEST_LEDGER.ledgerYear < nowYear) {
    local oldYear = C63_INVEST_LEDGER.ledgerYear;
    local nextStart = OpexC63YearStart(oldYear + 1);
    local carryKind = C63_INVEST_LEDGER.lastKind;
    local carryAbsentCause = C63_INVEST_LEDGER.lastAbsentCause;
    if (C63_INVEST_LEDGER.lastDate >= 0 && C63_INVEST_LEDGER.lastKind != "") {
      local tail = nextStart - C63_INVEST_LEDGER.lastDate - 1;
      if (tail > 0) OpexC63AddOpportunityDays(C63_INVEST_LEDGER.lastKind, tail, C63_INVEST_LEDGER.lastAbsentCause);
    }
    OpexC63FlushLedger(oldYear);
    if (C63_INVEST_LEDGER.ledgerYear <= oldYear) C63_INVEST_LEDGER.ledgerYear = oldYear + 1;
    C63_INVEST_LEDGER.lastDate = nextStart;
    C63_INVEST_LEDGER.lastKind = carryKind;
    C63_INVEST_LEDGER.lastAbsentCause = carryAbsentCause;
  }
}

function OpexC63NotePass(builtCount, best, passDiscards, railSearching, projects = null)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  local now = AIDate.GetCurrentDate();
  local nowYear = AIDate.GetYear(now);
  OpexC63EnsureYear(nowYear);
  local days = 0;
  if (C63_INVEST_LEDGER.lastDate >= 0 && now >= C63_INVEST_LEDGER.lastDate) {
    days = now - C63_INVEST_LEDGER.lastDate;
  }
  local previousKind = C63_INVEST_LEDGER.lastKind;
  local previousAbsentCause = C63_INVEST_LEDGER.lastAbsentCause;
  local kind;
  local absentCause = "";
  if (builtCount > 0) kind = "launched";
  else if (best == null || best.len() == 0) {
    local st = (projects != null && ("stats" in projects)) ? projects.stats : null;
    local considered = (st != null && ("budgetConsidered" in st)) ? st.budgetConsidered : 0;
    local minCap = (st != null && ("minCapital" in st)) ? st.minCapital : -1;
    local avail = OpexC63CachedAvailable();

    if (considered > 0 && minCap > 0 && minCap > avail) {
      kind = "unaffordable";
      absentCause = "";
    } else {
      kind = "absent";
      absentCause = OpexC63ClassifyAbsent(projects);
    }
  } else {
    local target = null;
    local leftoverRank = -1;
    for (local i = 0; i < best.len(); i++) {
      if (best[i] != null) { leftoverRank = i; target = best[i]; break; }
    }
    if (target == null) {
      local st = (projects != null && ("stats" in projects)) ? projects.stats : null;
      local considered = (st != null && ("budgetConsidered" in st)) ? st.budgetConsidered : 0;
      local minCap = (st != null && ("minCapital" in st)) ? st.minCapital : -1;
      local avail = OpexC63CachedAvailable();
      if (considered > 0 && minCap > 0 && minCap > avail) {
        kind = "unaffordable";
        absentCause = "";
      } else {
        kind = "absent";
        absentCause = OpexC63ClassifyAbsent(projects);
      }
    } else {
      local reason = "";
      if (passDiscards != null) {
        for (local k = 0; k < passDiscards.len(); k++) {
          if (("rank" in passDiscards[k]) && passDiscards[k].rank == leftoverRank) {
            reason = passDiscards[k].reason;
            break;
          }
        }
        if (reason == "" && passDiscards.len() > 0) reason = passDiscards[0].reason;
      }
      local waitingOnly = railSearching && (reason == "" || reason == "search_in_progress");
      local need = ("capital" in target) ? target.capital : 0;
      kind = OpexC63ClassifyOpportunity(reason, OpexC63CachedAvailable(), need, waitingOnly);
    }
  }
  /* 02.1 : days decrit le temps ecoule AVANT cette observation. Le crediter au nouvel etat
   * decalait tout le ledger d'une passe (absent -> launched devenait du temps launched, etc.).
   * Compter l'observation courante sans duree, puis attribuer l'intervalle a l'etat precedent. */
  OpexC63RecordOpportunity(kind, 0, absentCause);
  if (previousKind != "") OpexC63AddOpportunityDays(previousKind, days, previousAbsentCause);
  C63_INVEST_LEDGER.lastDate = now;
  C63_INVEST_LEDGER.lastKind = kind;
  C63_INVEST_LEDGER.lastAbsentCause = absentCause;
}

function OpexC63RecordEmptyProbe(projects, stage, freightCargo, abandonedPairs)
{
  if (!C63_INVEST_PROBE) return;
  if (projects == null) return;
  local st = ("stats" in projects) ? projects.stats : null;
  local railCand = OpexC63StatCount(st, "railCandidates", OpexC63ChildLen(projects, "rail", "candidates"));
  local roadCand = OpexC63StatCount(st, "roadCandidates", OpexC63ChildLen(projects, "road", "candidates"));
  local airPlans = OpexC63StatCount(st, "airPlansCount", OpexC63ChildLen(projects, "airPlans", ""));
  local waterPlans = OpexC63StatCount(st, "waterPlansCount", OpexC63ChildLen(projects, "waterPlans", ""));
  local modeCand = OpexC63StatCount(st, "modeCandidates", -1);
  local considered = OpexC63StatCount(st, "budgetConsidered", -1);
  local selected = OpexC63StatCount(st, "budgetSelected", -1);
  local minCap = OpexC63StatCount(st, "minCapital", -1);
  local availCap = OpexAvailableCapital();
  local cacheScanned = OpexC63StatCount(st, "cacheScanned", -1);
  local cacheRetained = OpexC63StatCount(st, "cacheRetained", -1);
  local abandonFiltered = OpexC63StatCount(st, "abandonFiltered", -1);
  local abandonPairs = (abandonedPairs != null) ? abandonedPairs.len() : 0;
  local emptyCause = "";
  if (st != null && ("emptyCause" in st) && st.emptyCause != null && st.emptyCause != "") {
    emptyCause = st.emptyCause;
  } else {
    emptyCause = OpexC63ClassifyAbsent(projects);
  }

  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  OpexC63InvestLog("phase=empty_probe year=" + year + " stage=" + stage + " cargo=" + freightCargo
      + " rail_c=" + railCand + " road_c=" + roadCand + " air_p=" + airPlans + " water_p=" + waterPlans
      + " mode_c=" + modeCand + " considered=" + considered + " selected=" + selected
      + " min_cap=" + minCap + " avail_cap=" + availCap
      + " cache_scanned=" + cacheScanned + " cache_retained=" + cacheRetained
      + " abandon_filtered=" + abandonFiltered + " abandon_pairs=" + abandonPairs
      + " cause=" + emptyCause);
}

function OpexC63FlushLedger(year)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  if (year < 1970) return;
  if (C63_INVEST_LEDGER.flushedYear == year) return;
  foreach (mode, slot in C63_INVEST_LEDGER.spend) {
    OpexC63InvestLog("phase=spend year=" + year + " mode=" + mode
        + " planned_ok=" + slot.planned_ok + " actual_ok=" + slot.actual_ok + " n_ok=" + slot.n_ok
        + " planned_fail=" + slot.planned_fail + " actual_fail=" + slot.actual_fail
        + " n_fail=" + slot.n_fail);
  }
  local o = C63_INVEST_LEDGER.opp;
  OpexC63InvestLog("phase=opp year=" + year
      + " absent_n=" + o.absent.n + " absent_d=" + o.absent.days
      + " invalid_n=" + o.invalid.n + " invalid_d=" + o.invalid.days
      + " unaffordable_n=" + o.unaffordable.n + " unaffordable_d=" + o.unaffordable.days
      + " demand_n=" + o.demand.n + " demand_d=" + o.demand.days
      + " waiting_compute_n=" + o.waiting_compute.n + " waiting_compute_d=" + o.waiting_compute.days
      + " launched_n=" + o.launched.n + " launched_d=" + o.launched.days);
  if ("absent_causes" in C63_INVEST_LEDGER) {
    local ac = C63_INVEST_LEDGER.absent_causes;
    OpexC63InvestLog("phase=opp_absent year=" + year
        + " empty_pool_n=" + ac.empty_pool.n + " empty_pool_d=" + ac.empty_pool.days
        + " unprofitable_n=" + ac.unprofitable.n + " unprofitable_d=" + ac.unprofitable.days
        + " already_served_n=" + ac.already_served.n + " already_served_d=" + ac.already_served.days
        + " no_site_n=" + ac.no_site.n + " no_site_d=" + ac.no_site.days
        + " mode_cargo_filter_n=" + ac.mode_cargo_filter.n + " mode_cargo_filter_d=" + ac.mode_cargo_filter.days
        + " selection_empty_n=" + ac.selection_empty.n + " selection_empty_d=" + ac.selection_empty.days
        + " stage_empty_n=" + ac.stage_empty.n + " stage_empty_d=" + ac.stage_empty.days
        + " cache_exhausted_n=" + ac.cache_exhausted.n + " cache_exhausted_d=" + ac.cache_exhausted.days
        + " abandon_filtered_n=" + ac.abandon_filtered.n + " abandon_filtered_d=" + ac.abandon_filtered.days);
  }
  OpexC63ResetLedger();
  C63_INVEST_LEDGER.flushedYear = year;
  C63_INVEST_LEDGER.ledgerYear = year + 1;
  C63_INVEST_LEDGER.lastDate = OpexC63YearStart(year + 1);
  C63_INVEST_LEDGER.lastKind = "";
  C63_INVEST_LEDGER.lastAbsentCause = "";
}

/* C50 : gate dedie pour la sonde chronologique legere (tresorerie, profit par ligne,
 * projets batis avec cout/ROI, projets refuses pour tresorerie avec ROI).
 * Autonome : fonctionne avec decision_log=0. */
function OpexC50ChronologyLog(fields)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C50_CHRONO " + fields);
}
/* C50 : enregistrement deduplique des refus de tresorerie (au plus un log par mois calendaire et par candidat). */
function OpexC50LogCashRefusal(mode, rank, cost, profit, roi, src, dst, need, money)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  local ym = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  local key = mode + "|" + src + "|" + dst;
  if ((key in C50_REFUSE_CACHE) && C50_REFUSE_CACHE[key] == ym) return;
  C50_REFUSE_CACHE[key] <- ym;

  local available = OpexAvailableCapital();
  local loan = AICompany.GetLoanAmount();
  OpexC50ChronologyLog("phase=refused_cash mode=" + mode + " rank=" + rank
      + " cost=" + cost + " profit=" + profit + " roi=" + roi
      + " need=" + need + " cash=" + money + " loan=" + loan + " available=" + available);
}
/* C55 : gate dedie et autonome. Ne jamais reutiliser le gate C49 : la sonde doit publier seule. */
function OpexC55OriginRelaxLog(fields)
{
  if (!C55_ORIGIN_RELAX_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C55_ORIGIN_RELAX " + fields);
}
/* C55 : gate autonome pour la tracabilite causale PAX. */
function OpexC55PaxTraceLog(kind, fields)
{
  if (!C55_PAX_TRACE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C56 : gate dedie et autonome. Lecture des traces :
 * - dernier TASK_ENTER name=X sans TASK_EXIT name=X : X ne rend pas la main, blocage dedans ;
 * - dernier STAGE_ENTER name=c56_stage_X sans STAGE_EXIT : blocage dans cette phase du portefeuille ;
 * - les phases sautees emettent aussi STAGE_EXIT : un jalon manquant signifie toujours un blocage ;
 * - TASK_ENTER/TASK_EXIT apparies jusqu'au bout puis plus rien : blocage hors tache ;
 * - LOOP_TICK continu sans TASK_ENTER : boucle active, ordonnanceur sans selection ;
 * - plus aucune trace : script lui-meme plus execute par le moteur. */
function OpexC56TaskLog(kind, name, cycle)
{
  if (!C56_TASK_TRACE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C56_TASK " + kind + " name=" + name
             + " cycle=" + cycle);
}
/* C52 : gate dedie et autonome. La sonde observe aussi quand la reparation est desarmee. */
function OpexC52AutoreplaceLog(fields)
{
  if (!C52_AUTOREPLACE_LOG) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C52_AUTOREPLACE " + fields);
}
/* C52 : gate dedie et autonome. La sonde ne publie que son propre ledger annuel. */
function OpexC52EventExposureLog(fields)
{
  if (!C52_EVENT_EXPOSURE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C52_EVENT_EXPOSURE " + fields);
}
/* Observe une paire au point meme ou le filtre d'origine route la voit. Cette fonction ne
 * retourne rien et n'ecrit que le ledger de sonde ; elle ne participe a aucun predicat. */
function OpexC55OriginRelaxObserve(kind, lines, src, dst, srcServed, dstServed)
{
  if (!C55_ORIGIN_RELAX_PROBE || C55_ORIGIN_RELAX_LEDGER == null) return;
  C55_ORIGIN_RELAX_LEDGER.candidates_seen++;
  if (!srcServed && !dstServed) return;
  C55_ORIGIN_RELAX_LEDGER.rejected_total++;
  if (srcServed && dstServed) {
    C55_ORIGIN_RELAX_LEDGER.both_served++;
    return;
  }
  C55_ORIGIN_RELAX_LEDGER.one_served++;
  if (kind == "pax") C55_ORIGIN_RELAX_LEDGER.one_served_pax++;
  else C55_ORIGIN_RELAX_LEDGER.one_served_freight++;
  /* Cle disponible ici : meme paire geometrique, dans un sens ou dans l'autre, a moins de
   * ORIGIN_SEPARATION des deux originA/originB d'une ligne route existante. */
  if (OpexRoadPairServed(lines, src, dst)) C55_ORIGIN_RELAX_LEDGER.duplicate_exact++;
}
/* C55 : observateurs pour la tracabilite causale PAX */
function OpexC55PaxTraceObserveRevalidated(isOriginBlocked)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.revalidated++;
  if (isOriginBlocked) C55_PAX_TRACE_LEDGER.origin_blocked++;
}
function OpexC55PaxTraceObserveSpared()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.spared++;
}
function OpexC55PaxTraceObserveAttempted()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.attempted++;
}
function OpexC55PaxTraceObservePrecheckOk()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.precheck_ok++;
}
function OpexC55PaxTraceObserveFinanceable()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.financeable++;
}
function OpexC55PaxTraceObservePlanned()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.planned++;
}
function OpexC55PaxTraceObserveViable()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.viable++;
}
function OpexC55PaxTraceObserveBuilt(profit)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.built++;
  C55_PAX_TRACE_LEDGER.built_profit += profit;
}
function OpexC49VehicleType(mode)
{
  if (mode == "rail") return AIVehicle.VT_RAIL;
  if (mode == "road") return AIVehicle.VT_ROAD;
  if (mode == "air" || mode == "fleet") return AIVehicle.VT_AIR;
  if (mode == "water") return AIVehicle.VT_WATER;
  return -1;
}
function OpexC49IsMapFailure(passDiscards, rank)
{
  foreach (discard in passDiscards) {
    if (discard.rank != rank) continue;
    if (discard.reason == "build_failed" || discard.reason == "plan_failed"
        || discard.reason == "too_close" || discard.reason == "too_close_hard"
        || discard.reason == "too_close_no_join") return true;
  }
  return false;
}
/* C41.47 : un evenement par liberation, pas un accumulateur annuel -- les liberations sont
 * rares (motif observe : quelques par partie), la mesure interessante est LEQUEL candidat et
 * QUAND, pas un total. */
function OpexC41RailCashReleaseLog(fields)
{
  if (!C41_RAIL_CASH_RELEASE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_CASH_RELEASE " + fields);
}
/* C41.48 : un evenement par frontiere de tranche -- la frequence de declenchement EST la
 * mesure (repond a "sur combien de frontieres le test C41.49 aurait-il seulement l'occasion
 * de s'appliquer ?"), donc pas d'agregat qui la masquerait. */
function OpexC41RailDominationLog(fields)
{
  if (!C41_RAIL_DOMINATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_DOMINATION_PROBE " + fields);
}
/* C41.49 : son propre gate, comme C41.46/C41.47/C41.48 -- OpexC41SchedulerLog et
 * OpexC41RailDominationLog l'auraient sinon silencieusement avale (piege deja trouve trois fois). */
function OpexC41ProjectsFallthroughLog(fields)
{
  if (!C41_PROJECTS_FALLTHROUGH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_PROJECTS_FALLTHROUGH_PROBE " + fields);
}
/* C39.5 : gate propre -- ne jamais reutiliser celui d'une autre sonde, sinon armer seulement
 * c39_projects_cadence_probe rendrait le canal silencieux. */
function OpexC39ProjectsCadenceLog(fields)
{
  if (!C39_PROJECTS_CADENCE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PROJECTS_CADENCE " + fields);
}
/* C39.6 : gate propre, INDEPENDANT de C39_PROJECTS_CADENCE_PROBE et de C41_RAIL_SLICE_LEDGER --
 * ne jamais reutiliser le gate d'une autre sonde (piege deja trouve trois fois dans ce depot :
 * un canal reutilise reste silencieux tant que SA propre variante n'est pas armee). */
function OpexC39PassClockLog(fields)
{
  if (!C39_PASS_CLOCK_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PASS_CLOCK " + fields);
}
function OpexC41StalenessLog(kind, fields)
{
  if (!C41_STALENESS_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* Contrat C41.14 : le hint est une borne prudente d'admission, pas une moyenne ni un budget
 * reservé. Le scheduler ne le lit pas encore pour executer : cette phase mesure seulement si le
 * point d'entree cible pourrait tenir dans le reliquat du tick courant. */
function OpexC41MicrotaskOpsHint(layer)
{
  if (layer == "catalog.water") return 350;
  return -1;
}
/* C41.4 reste observable sans armer C39 : c'est un inventaire de l'evenement, pas une
 * invalidation de catalogue. */
function OpexC41VehicleLostLog(fields)
{
  if (!C41_VEHICLE_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_VEHICLE_LOST " + fields);
}
function OpexC41RailLostLog(fields)
{
  if (!C41_RAIL_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST " + fields);
}
/* Gate C54 autonome : AIDate et AILog ne sont atteignables que si le reglage C54 est actif. */
function OpexC54VehicleOrdersLog(fields)
{
  if (!C54_VEHICLE_ORDERS_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C54_VEHICLE_ORDERS " + fields);
}
function OpexC41RailLostTopologyLog(fields)
{
  if (!C41_RAIL_LOST_TOPOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_TOPOLOGY " + fields);
}
function OpexC41RailLostPhysicalLog(fields)
{
  if (!C41_RAIL_LOST_PHYSICAL_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_PHYSICAL " + fields);
}
function OpexC41RailSignalRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_SIGNAL_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexC41RailLostConnectivityLog(fields)
{
  if (!C41_RAIL_LOST_CONNECTIVITY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_CONNECTIVITY " + fields);
}
function OpexC41RailJunctionRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_JUNCTION_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexC39ProjectSignature(projects)
{
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) {
    return "none";
  }
  local project = projects.best[0];
  return project.mode + ":" + project.src + ":" + project.dst;
}
function OpexC41RevisionSnapshot(revisions)
{
  return "c=" + revisions.catalog.cargos + "," + revisions.catalog.towns + ","
         + revisions.catalog.industries + "," + revisions.catalog.rail + ","
         + revisions.catalog.road + "," + revisions.catalog.air + ","
         + revisions.catalog.water + " d=" + revisions.candidates.rail + ","
         + revisions.candidates.road + "," + revisions.candidates.air + ","
         + revisions.candidates.water + " p=" + revisions.portfolio + " s="
         + revisions.selection;
}
/* Le moteur a-t-il survécu au filtre propre à son mode ? Ce n'est pas une décision de
 * construction : C39.3 mesure précisément si le catalogue aurait une raison de propager l'event. */
function OpexC39CatalogUsesEngine(catalog, engine, mode)
{
  if (catalog == null) return false;
  if (mode == "rail") {
    if (catalog.railLocos != null) foreach (loco in catalog.railLocos) if (loco.id == engine) return true;
    if (catalog.wagonByCargo != null) foreach (cargo, wagon in catalog.wagonByCargo) if (wagon.id == engine) return true;
  } else if (mode == "road") {
    if (catalog.roadEngineByCargo != null) foreach (cargo, vehicle in catalog.roadEngineByCargo) if (vehicle.id == engine) return true;
  } else if (mode == "air") {
    if (catalog.plane != null && catalog.plane.id == engine) return true;
    if (catalog.airCombos != null) foreach (combo in catalog.airCombos) if (combo.plane.id == engine) return true;
  } else if (mode == "water") {
    if (catalog.ships != null) foreach (ship in catalog.ships) if (ship.id == engine) return true;
  }
  return false;
}
/* `retained=0` air signifie seulement que le moteur n'est pas le gagnant de `airCombos`.
 * Cette sonde separe les filtres eliminatoires de la domination capacite/vitesse, sans modifier
 * l'algorithme de selection. */
function OpexC39AirEngineReason(catalog, engine)
{
  if (catalog == null || !AIEngine.IsValidEngine(engine)) return "invalid";
  if (!AIEngine.IsBuildable(engine)) return "not_buildable";
  if (catalog.paxCargo < 0 || !AIEngine.CanRefitCargo(engine, catalog.paxCargo)) return "no_pax_refit";
  local planeType = AIEngine.GetPlaneType(engine);
  if (planeType != AIAirport.PT_SMALL_PLANE && planeType != AIAirport.PT_BIG_PLANE) return "unsupported_type";
  if (AIEngine.GetCapacity(engine) <= 0) return "zero_capacity";
  if (OpexC39CatalogUsesEngine(catalog, engine, "air")) return "selected";
  return "dominated";
}
function OpexCashReserveProbeLog(fields)
{
  if (!CASH_RESERVE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " CASH_RESERVE_PROBE " + fields);
}
function OpexPortfolioRefreshProbeLog(fields)
{
  if (!PORTFOLIO_REFRESH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " PORTFOLIO_REFRESH_PROBE " + fields);
}
