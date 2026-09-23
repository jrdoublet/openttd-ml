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
  if (name != null && name.len() > 31) name = name.slice(0, 31);
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
/* C69 : gate dedie sous probe_portfolio. */
function OpexC69Log(fields)
{
  if (!C69_BOTTLENECK_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C69_BOTTLENECK " + fields);
}
/* C78 etape 2 : journalisation passive sous probe_portfolio. */
function OpexC78Log(tag, fields)
{
  if (!C69_BOTTLENECK_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + tag + " " + fields);
}

function OpexC78CandidateLog(fields)
{
  OpexC78Log("C78_CAND", fields);
}

/* C78 : sonde dediee a la course aux deux slots aeroportuaires d'une ville.
 * AIStation ne permet pas d'inventorier directement les stations adverses. Le chemin fonctionnel
 * C77 utilise AITown.GetAllowedNoise()==1 sous station_noise_level=0 pour savoir qu'un des deux
 * slots est deja occupe ; le harnais shared garde l'inventaire/build_date AAA pour la chronologie.
 * Cette sonde publie l'etat du vivier AIR sans modifier decision ni cadence. */
function OpexC78SlotLog(fields)
{
  if (!C78_SLOT_INTERCEPT_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C78_SLOT " + fields);
}

function OpexC78AirPhysicalTown(site)
{
  if (site == null) return -1;
  if (("anchor" in site) && AIMap.IsValidTile(site.anchor)) {
    local townId = AITile.GetClosestTown(site.anchor);
    if (townId >= 0) return townId;
  }
  if (("town" in site) && site.town != null) {
    if (typeof site.town == "table" && ("id" in site.town)) return site.town.id;
    if (typeof site.town == "integer") return site.town;
  }
  return -1;
}

function OpexC78FundedRank(projects, project)
{
  if (projects == null || !("best" in projects) || projects.best == null) return -1;
  local key = OpexProjectAttemptKey(project);
  for (local i = 0; i < projects.best.len(); i++) {
    local fundedProject = projects.best[i];
    if (fundedProject != null && OpexProjectAttemptKey(fundedProject) == key) return i;
  }
  return -1;
}

function OpexAI::_c78SlotOnProjectsPass()
{
  if (!C78_SLOT_INTERCEPT_PROBE) return;
  C78_SLOT_PASS_COUNTER++;
  local passId = C78_SLOT_PASS_COUNTER;
  local cycle = this._taskCycle;
  local tick = AIController.GetTick();
  local available = OpexAvailableCapital();
  local airCandidates = 0;
  local affordable = 0;
  local funded = 0;

  if (this._projects == null || !("candidateGroups" in this._projects)
      || this._projects.candidateGroups == null) {
    OpexC78SlotLog("phase=projects_pass pass=" + passId
        + " cycle=" + cycle + " tick=" + tick
        + " state=no_projects air_candidates=0 affordable=0 funded=0"
        + " available=" + available);
    return;
  }

  foreach (groupKey, entry in this._projects.candidateGroups) {
    local list = (typeof entry == "array") ? entry : [entry];
    foreach (project in list) {
      if (project == null || !("mode" in project) || project.mode != "air"
          || !("payload" in project) || project.payload == null) continue;
      local plan = project.payload;
      if (!("siteA" in plan) || !("siteB" in plan)) continue;

      local townA = OpexC78AirPhysicalTown(plan.siteA);
      local townB = OpexC78AirPhysicalTown(plan.siteB);
      local capital = ("budgetCapital" in project) ? project.budgetCapital : 0;
      local finance = OpexProjectFinanceCapital(project);
      local isAffordable = finance <= available;
      local rank = OpexC78FundedRank(this._projects, project);
      local score = ("fundScore" in project)
          ? OpexProjectSelectionScore(project, "fundScore") : -1;
      local defensiveClaims = ("defensiveSlotClaims" in project)
          ? project.defensiveSlotClaims : -1;
      local age = ("economicsDate" in project)
          ? AIDate.GetCurrentDate() - project.economicsDate : -1;

      airCandidates++;
      if (isAffordable) affordable++;
      if (rank >= 0) funded++;

      OpexC78SlotLog("phase=project_candidate pass=" + passId
          + " cycle=" + cycle + " tick=" + tick
          + " townA=" + townA + " townB=" + townB
          + " rank=" + rank + " affordable=" + (isAffordable ? 1 : 0)
          + " profit=" + project.profitAnnual + " capital=" + capital + " finance=" + finance
          + " roi=" + project.roi + " score=" + score + " defensive_claims=" + defensiveClaims
          + " age_days=" + age
          + " src=" + project.src + " dst=" + project.dst);
    }
  }

  OpexC78SlotLog("phase=projects_pass pass=" + passId
      + " cycle=" + cycle + " tick=" + tick
      + " state=ok air_candidates=" + airCandidates
      + " affordable=" + affordable + " funded=" + funded + " available=" + available);
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
function OpexC56TaskLog(kind, name, cycle, extra = null)
{
  if (!C56_TASK_TRACE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C56_TASK " + kind + " name=" + name
             + " cycle=" + cycle + " tick=" + AIController.GetTick()
             + " opsclk=" + OpexOpsClock() + (extra != null ? " " + extra : ""));
}
/* C56 : intention reactive de l'orchestrateur, bornee par INTENT_ENTER/INTENT_EXIT. */
function OpexC56DispatchReactive(owner, intention)
{
  if (!C56_TASK_TRACE) return owner._dispatchReactiveIntention(intention);
  local kind = (("kind" in intention) && intention.kind != null) ? intention.kind : "unknown";
  OpexC56TaskLog("INTENT_ENTER", kind, "-");
  local dispatched = owner._dispatchReactiveIntention(intention);
  OpexC56TaskLog("INTENT_EXIT", kind, "-", "dispatched=" + (dispatched ? 1 : 0));
  return dispatched;
}
/* C56 : tranche de travailleur. Une trace par travailleur (WORKER_ENTER a la premiere tranche,
 * WORKER_EXIT a la derniere) et non par tranche : un A* rail en compte des milliers. Les tranches
 * s'intercalent avec la file de fond, d'ou le cumul `step_ops` propre au travailleur. */
function OpexC56WorkerStep(worker, opsBudget, deadlineTick)
{
  if (!C56_TASK_TRACE) return OpexWorkerStep(worker, opsBudget, deadlineTick);
  if (C56_WORKER_ACC == null || C56_WORKER_ACC.worker != worker) {
    ::C56_WORKER_ACC = { worker = worker, kind = worker.kind, steps = 0, ops = 0 };
    OpexC56TaskLog("WORKER_ENTER", worker.kind, "-");
  }
  local acc = C56_WORKER_ACC;
  local mark = OpexOpsMeasureBegin();
  local outcome = OpexWorkerStep(worker, opsBudget, deadlineTick);
  acc.ops += OpexOpsMeasureEnd(mark);
  acc.steps++;
  if (outcome == "done" || outcome == "cancelled") {
    OpexC56TaskLog("WORKER_EXIT", acc.kind, "-", "outcome=" + outcome + " steps=" + acc.steps
                   + " step_ops=" + acc.ops);
    ::C56_WORKER_ACC = null;
  }
  return outcome;
}
/* Horloge d'opcodes monotone, meme convention qu'OpexOpsMeasureEnd : un tick franchi compte pour
 * OPS_PER_TICK. La difference entre deux traces C56 donne le cout d'une etape. */
function OpexOpsClock()
{
  return AIController.GetTick() * OPS_PER_TICK + (OPS_PER_TICK - AIController.GetOpsTillSuspend());
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
/* C55 : observateur des revalidations PAX bloquees par une origine deja servie. */
function OpexC55PaxTraceObserveRevalidated(isOriginBlocked)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.revalidated++;
  if (isOriginBlocked) C55_PAX_TRACE_LEDGER.origin_blocked++;
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

/* C69 : cle d'identite stable d'un candidat ou projet construit */
function OpexC69AttemptKey(p)
{
  if (p == null) return "none";
  if (!("mode" in p) && ("src" in p) && ("dst" in p) && ("cargo" in p) && ("kind" in p)) {
    return "rail|" + p.src + "|" + p.dst + "|" + p.cargo + "|" + p.kind;
  }
  return OpexProjectAttemptKey(p);
}

/* C69 : somme GetProfitLastYear de l'ensemble des vehicules de la compagnie (controle F_veh) */
function OpexC69VehicleProfitLastYear()
{
  local total = 0;
  local vl = AIVehicleList();
  foreach (v, _ in vl) {
    if (AIVehicle.IsValidVehicle(v)) {
      total += AIVehicle.GetProfitLastYear(v);
    }
  }
  return total;
}

/* C69 : mediane d'une liste de nombres reels sans mutation */
function OpexMedianFloat(values)
{
  local n = values.len();
  if (n == 0) return 0.0;
  local copy = [];
  foreach (v in values) copy.append(v);
  for (local i = 1; i < n; i++) {
    local v = copy[i];
    local j = i;
    while (j > 0 && copy[j - 1] > v) {
      copy[j] = copy[j - 1];
      j--;
    }
    copy[j] = v;
  }
  if (n % 2 == 1) return copy[n / 2];
  return (copy[n / 2 - 1] + copy[n / 2]) / 2.0;
}

/* C69/C75 : calcul factorise du flux d'exploitation journalier F sur les 4 derniers trimestres complets */
function OpexComputeOperatingCashFlow(now = null)
{
  if (now == null) now = AIDate.GetCurrentDate();
  local curYear = AIDate.GetYear(now);
  local curMonth = AIDate.GetMonth(now);
  local curQuarterIdx = (curMonth - 1) / 3;
  local totalCompletedQuarters = (curYear - OPEX_START_YEAR) * 4 + curQuarterIdx;

  local F = 0.0;
  local daysCovered = 0;
  if (totalCompletedQuarters > 0) {
    local numQ = totalCompletedQuarters < 4 ? totalCompletedQuarters : 4;
    local curQuarterStartMonth = curQuarterIdx * 3 + 1;
    local curQuarterStartDate = AIDate.GetDate(curYear, curQuarterStartMonth, 1);
    local T = totalCompletedQuarters;
    local windowStartQuarter = T - numQ;
    local windowStartYear = OPEX_START_YEAR + (windowStartQuarter / 4);
    local windowStartMonth = (windowStartQuarter % 4) * 3 + 1;
    local windowStartDate = AIDate.GetDate(windowStartYear, windowStartMonth, 1);
    daysCovered = curQuarterStartDate - windowStartDate;

    if (daysCovered > 0) {
      local sumNet = 0.0;
      for (local q = 1; q <= numQ; q++) {
        local inc = AICompany.GetQuarterlyIncome(AICompany.COMPANY_SELF, q);
        local exp = AICompany.GetQuarterlyExpenses(AICompany.COMPANY_SELF, q);
        sumNet += (inc.tofloat() + exp);
      }
      /* GetQuarterlyIncome + GetQuarterlyExpenses excluent construction et achats de vehicules
       * (mesure C69 : -3,7 k£ de depenses pour 278 k£ investis au meme trimestre) : sumNet est
       * deja le flux d'exploitation. Ajouter I le compterait deux fois. */
      local numerator = sumNet;
      if (numerator > 0.0) {
        F = numerator / daysCovered.tofloat();
      }
    }
  }

  return {
    F = F,
    daysCovered = daysCovered
  };
}

/* C69 : calcul unique de F, tau et K_dec par appel de selection */
function OpexC69ComputeKDec()
{
  local now = AIDate.GetCurrentDate();
  local flow = OpexComputeOperatingCashFlow(now);
  local F = flow.F;
  local daysCovered = flow.daysCovered;

  local startDate = AIDate.GetDate(OPEX_START_YEAR, 1, 1);
  local daysSinceStart = now - startDate;
  if (daysSinceStart < 1) daysSinceStart = 1;
  local D = daysSinceStart < 365 ? daysSinceStart : 365;

  local N = 0;
  if (C69_BUILD_DATES != null) {
    local cutoff = now - D;
    local pruned = [];
    foreach (d in C69_BUILD_DATES) {
      if (d >= cutoff) {
        pruned.append(d);
      }
    }
    C69_BUILD_DATES = pruned;
    N = C69_BUILD_DATES.len();
  }

  local tau = 0.0;
  local K_dec = 0;
  if (N > 0 && F > 0.0) {
    tau = D.tofloat() / N.tofloat();
    K_dec = (F * tau).tointeger();
    if (K_dec < 0) K_dec = 0;
  }

  return {
    F = F,
    tau = tau,
    K_dec = K_dec,
    D = D,
    N = N,
    daysCovered = daysCovered
  };
}

/* C75 : enregistre la date d'une passe de _tryBuildProjects et purge au-dela de la fenetre */
function OpexC75RecordPassDate(now = null)
{
  if (!C75_TRACK_PASSES) return;
  if (C75_PASS_DATES == null) C75_PASS_DATES = [];
  if (now == null) now = AIDate.GetCurrentDate();
  C75_PASS_DATES.append(now);

  local startDate = AIDate.GetDate(OPEX_START_YEAR, 1, 1);
  local daysSinceStart = now - startDate;
  if (daysSinceStart < 1) daysSinceStart = 1;
  local D = daysSinceStart < 365 ? daysSinceStart : 365;

  local cutoff = now - D;
  local pruned = [];
  foreach (d in C75_PASS_DATES) {
    if (d >= cutoff) {
      pruned.append(d);
    }
  }
  C75_PASS_DATES = pruned;
}

/* C75 : calcul de K_pass = F * tau_pass sur la fenetre glissante min(365, jours depuis debut).
 * Moins de 2 passes dans la fenetre => K_pass = 0. */
function OpexC75ComputeKPass(now = null)
{
  if (now == null) now = AIDate.GetCurrentDate();
  local flow = OpexComputeOperatingCashFlow(now);
  local F = flow.F;

  local startDate = AIDate.GetDate(OPEX_START_YEAR, 1, 1);
  local daysSinceStart = now - startDate;
  if (daysSinceStart < 1) daysSinceStart = 1;
  local D = daysSinceStart < 365 ? daysSinceStart : 365;

  local N = 0;
  if (C75_PASS_DATES != null) {
    local cutoff = now - D;
    local pruned = [];
    foreach (d in C75_PASS_DATES) {
      if (d >= cutoff) {
        pruned.append(d);
      }
    }
    C75_PASS_DATES = pruned;
    N = C75_PASS_DATES.len();
  }

  local tau_pass = 0.0;
  local K_pass = 0;
  if (N >= 2 && F > 0.0) {
    tau_pass = D.tofloat() / N.tofloat();
    K_pass = (F * tau_pass).tointeger();
    if (K_pass < 0) K_pass = 0;
  }

  return {
    F = F,
    tau_pass = tau_pass,
    K_pass = K_pass,
    D = D,
    N = N,
    daysCovered = flow.daysCovered
  };
}

/* C75 : reinitialise le registre annuel de passes et chantiers */
function OpexC75ResetYearLedger()
{
  C75_YEAR_LEDGER = {
    passes = 0,
    builds = 0,
    multi_passes = 0
  };
}

/* C75 : enregistre le resultat d'une passe et publie phase=c75_pass si au moins 1 chantier */
function OpexC75RecordPassOutcome(year, builtCount, c75KPassData, stopReason)
{
  if (!C75_TRACK_PASSES) return;
  if (C75_YEAR_LEDGER != null) {
    C75_YEAR_LEDGER.builds += builtCount;
    if (builtCount > 1) C75_YEAR_LEDGER.multi_passes++;
  }
  if (builtCount > 0 && C69_BOTTLENECK_PROBE) {
    local kPass = (c75KPassData != null) ? c75KPassData.K_pass : 0;
    local tauPass = (c75KPassData != null) ? c75KPassData.tau_pass : 0.0;
    local fVal = (c75KPassData != null) ? c75KPassData.F : 0.0;
    local reason = (stopReason != null) ? stopReason : "list_end";
    OpexC69Log("phase=c75_pass year=" + year + " built=" + builtCount
        + " k_pass=" + kPass + " tau_pass=" + tauPass + " F=" + fVal
        + " stop=" + reason);
  }
}

/* C80 tâche 5 : sonde passive sous probe_portfolio comptant les projets rejetés par le filtre marginal */
function OpexC80RecordMarginalDiscard(year, rank, project)
{
  if (!C69_BOTTLENECK_PROBE) return;
  local predProfit = (project != null && ("profitAnnual" in project)) ? project.profitAnnual : 0;
  local calibProfit = (project != null && C70_PROFIT_CALIBRATED) ? OpexCalibratedProfit(project) : predProfit;
  if (C80_MARGINAL_FLOOR_LEDGER != null) {
    C80_MARGINAL_FLOOR_LEDGER.discards++;
    C80_MARGINAL_FLOOR_LEDGER.discard_profit += predProfit;
  }
  local mode = (project != null && ("mode" in project)) ? project.mode : "unknown";
  local financeCap = (project != null) ? OpexProjectFinanceCapital(project) : 0;
  local vehs = OpexProjectVehicleCount(project);
  local calibInt = (calibProfit != null && typeof(calibProfit) == "float") ? calibProfit.tointeger() : calibProfit;
  OpexC69Log("phase=marginal_discard year=" + year + " rank=" + rank + " mode=" + mode
      + " P=" + predProfit + " P_calib=" + calibInt
      + " vehs=" + vehs + " C=" + financeCap
      + " tot_discards=" + (C80_MARGINAL_FLOOR_LEDGER != null ? C80_MARGINAL_FLOOR_LEDGER.discards : 0)
      + " tot_discard_profit=" + (C80_MARGINAL_FLOOR_LEDGER != null ? C80_MARGINAL_FLOOR_LEDGER.discard_profit : 0));
}

/* C75 : publication annuelle du registre de passes et chantiers */
function OpexC75FlushYear(year)
{
  if (!C69_BOTTLENECK_PROBE || C75_YEAR_LEDGER == null) return;
  if (year < 1970) return;

  OpexC69Log("phase=c75_year year=" + year + " passes=" + C75_YEAR_LEDGER.passes
      + " builds=" + C75_YEAR_LEDGER.builds + " multi_passes=" + C75_YEAR_LEDGER.multi_passes);

  if (C80_MARGINAL_FLOOR_LEDGER != null && C80_MARGINAL_FLOOR_LEDGER.discards > 0) {
    OpexC69Log("phase=c80_marginal_year year=" + year
        + " discards=" + C80_MARGINAL_FLOOR_LEDGER.discards
        + " discard_profit=" + C80_MARGINAL_FLOOR_LEDGER.discard_profit);
    C80_MARGINAL_FLOOR_LEDGER.discards = 0;
    C80_MARGINAL_FLOOR_LEDGER.discard_profit = 0;
  }

  OpexC75ResetYearLedger();
}


/* C72 : cache journalier de K_dec pour la sonde passive du choix d'avion */
function OpexC69CachedKDec()
{
  local today = AIDate.GetCurrentDate();
  if (C69_CACHED_KDEC_DATE == today) return C69_CACHED_KDEC_VALUE;
  local data = OpexC69ComputeKDec();
  C69_CACHED_KDEC_DATE = today;
  C69_CACHED_KDEC_VALUE = data.K_dec;
  return C69_CACHED_KDEC_VALUE;
}

/* C72 : nom de l'appareil avec espaces remplaces par des tirets bas pour le parseur de logs */
function OpexPlaneName(engineId)
{
  if (!AIEngine.IsValidEngine(engineId)) return "unknown";
  local rawName = AIEngine.GetName(engineId);
  if (rawName == null || rawName.len() == 0) return "unknown";
  local res = "";
  for (local i = 0; i < rawName.len(); i++) {
    local c = rawName.slice(i, i + 1);
    if (c == " ") res += "_";
    else res += c;
  }
  return res.len() > 0 ? res : "unknown";
}

/* C73 : sonde passive vivier et passes du portefeuille (C69 etape 1) */
function OpexC73NewModeStats()
{
  return {
    examined = 0,
    rejections = {},
    produced = 0,
    after_topk = 0,
    to_select = 0,
    affordable = 0,
    selected = 0
  };
}

function OpexC73ResetLedger()
{
  C73_VIVIER_LEDGER = {
    flushedYear = -1,
    passes = {
      count = 0,
      empty = 0,
      built = 0,
      sum_cash = 0.0,
      sum_avail = 0.0
    },
    modes = {
      rail = OpexC73NewModeStats(),
      road = OpexC73NewModeStats(),
      air = OpexC73NewModeStats(),
      water = OpexC73NewModeStats(),
      fleet = OpexC73NewModeStats()
    }
  };
}

function OpexC73RecordExamined(mode, count = 1)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (!(mode in C73_VIVIER_LEDGER.modes)) return;
  C73_VIVIER_LEDGER.modes[mode].examined += count;
}

function OpexC73RecordRejection(mode, reason, count = 1)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (!(mode in C73_VIVIER_LEDGER.modes)) return;
  local m = C73_VIVIER_LEDGER.modes[mode];
  if (reason in m.rejections) {
    m.rejections[reason] += count;
  } else {
    m.rejections[reason] <- count;
  }
}

function OpexC73RecordProduced(mode, produced, afterTopK)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (!(mode in C73_VIVIER_LEDGER.modes)) return;
  C73_VIVIER_LEDGER.modes[mode].produced += produced;
  C73_VIVIER_LEDGER.modes[mode].after_topk += afterTopK;
}

function OpexC73RecordSelection(toSelectCounts, affordableCounts, selectedCounts)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  foreach (mode, m in C73_VIVIER_LEDGER.modes) {
    if (mode in toSelectCounts) m.to_select += toSelectCounts[mode];
    if (mode in affordableCounts) m.affordable += affordableCounts[mode];
    if (mode in selectedCounts) m.selected += selectedCounts[mode];
  }
}

function OpexC73RecordPass(built, empty, cash, avail)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  local p = C73_VIVIER_LEDGER.passes;
  p.count++;
  if (built) p.built++;
  if (empty) p.empty++;
  p.sum_cash += cash.tofloat();
  p.sum_avail += avail.tofloat();
}

function OpexC73FlushLedger(year)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (year < 1970) return;
  if (C73_VIVIER_LEDGER.flushedYear == year) return;

  local modeOrder = ["rail", "road", "air", "water", "fleet"];
  foreach (mode in modeOrder) {
    local m = C73_VIVIER_LEDGER.modes[mode];
    local line = "phase=vivier_year year=" + year + " mode=" + mode + " examined=" + m.examined;
    foreach (reason, cnt in m.rejections) {
      line += " rej_" + reason + "=" + cnt;
    }
    line += " produced=" + m.produced + " after_topk=" + m.after_topk
          + " to_select=" + m.to_select + " affordable=" + m.affordable + " selected=" + m.selected;
    OpexC69Log(line);
  }

  local p = C73_VIVIER_LEDGER.passes;
  local avgCash = p.count > 0 ? (p.sum_cash / p.count).tointeger() : 0;
  local avgAvail = p.count > 0 ? (p.sum_avail / p.count).tointeger() : 0;
  OpexC69Log("phase=passes_year year=" + year + " passes=" + p.count + " empty=" + p.empty
      + " built=" + p.built + " avg_cash=" + avgCash + " avg_avail=" + avgAvail);

  OpexC73ResetLedger();
  C73_VIVIER_LEDGER.flushedYear = year;
}

/* C80 : sonde incrementale air sous probe_portfolio */
function OpexC80RecordAirIncremental(kind)
{
  if (!C69_BOTTLENECK_PROBE) return;
  if (kind in C80_AIR_INC_COUNTS) {
    C80_AIR_INC_COUNTS[kind]++;
  }
}

function OpexC80FlushAirIncremental(year)
{
  if (!C69_BOTTLENECK_PROBE) return;
  OpexC69Log("phase=air_incremental_year year=" + year
      + " full=" + C80_AIR_INC_COUNTS.full
      + " targeted=" + C80_AIR_INC_COUNTS.targeted
      + " none=" + C80_AIR_INC_COUNTS.none);
  C80_AIR_INC_COUNTS.full = 0;
  C80_AIR_INC_COUNTS.targeted = 0;
  C80_AIR_INC_COUNTS.none = 0;
}

/* C76 : sonde passive sous C39_INVALIDATION_PROBE (probe_catalogue). */
function OpexC76Log(fields)
{
  if (!C39_INVALIDATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C76_REGEN " + fields);
}

function OpexC76Reset()
{
  C76_PREV_STATE = null;
  C76_YEAR_LEDGER = {};
  C76_EVENTS_SINCE_PREV = { total = 0, by_type = {} };
}

function OpexC76ObserveEvent(eventType)
{
  if (!C39_INVALIDATION_PROBE || C76_EVENTS_SINCE_PREV == null) return;
  C76_EVENTS_SINCE_PREV.total++;
  local typeName = "other";
  if (eventType == AIEvent.ET_ENGINE_AVAILABLE || eventType == AIEvent.ET_ENGINE_PREVIEW) typeName = "engine";
  else if (eventType == AIEvent.ET_INDUSTRY_OPEN) typeName = "ind_open";
  else if (eventType == AIEvent.ET_INDUSTRY_CLOSE) typeName = "ind_close";
  else if (eventType == AIEvent.ET_TOWN_FOUNDED) typeName = "town_founded";
  else if (eventType == AIEvent.ET_SUBSIDY_OFFER || eventType == AIEvent.ET_SUBSIDY_OFFER_EXPIRED
           || eventType == AIEvent.ET_SUBSIDY_AWARDED || eventType == AIEvent.ET_SUBSIDY_EXPIRED) typeName = "subsidy";
  else if (eventType == AIEvent.ET_VEHICLE_CRASHED || eventType == AIEvent.ET_VEHICLE_LOST
           || eventType == AIEvent.ET_VEHICLE_WAITING_IN_DEPOT || eventType == AIEvent.ET_VEHICLE_UNPROFITABLE
           || eventType == AIEvent.ET_VEHICLE_AUTOREPLACED) typeName = "vehicle";
  else if (eventType == AIEvent.ET_STATION_FIRST_VEHICLE) typeName = "station";

  if (typeName in C76_EVENTS_SINCE_PREV.by_type) {
    C76_EVENTS_SINCE_PREV.by_type[typeName]++;
  } else {
    C76_EVENTS_SINCE_PREV.by_type.rawset(typeName, 1);
  }
}

function OpexC76FormatPct(curr, prev)
{
  if (prev == null || prev == 0) return "0.00";
  local delta = (curr.tofloat() - prev.tofloat()) * 100.0 / prev.tofloat();
  local sign = "";
  if (delta < 0.0) {
    sign = "-";
    delta = -delta;
  }
  local whole = delta.tointeger();
  local frac = ((delta - whole) * 100.0 + 0.5).tointeger();
  if (frac >= 100) {
    whole += 1;
    frac -= 100;
  }
  local fracStr = frac < 10 ? "0" + frac : "" + frac;
  return sign + whole + "." + fracStr;
}

function OpexC76FormatRatioPct(num, den)
{
  if (den == null || den <= 0) return (num == 0) ? "100.00" : "0.00";
  local pct = (num.tofloat() * 100.0) / den.tofloat();
  if (pct > 100.0) pct = 100.0;
  if (pct < 0.0) pct = 0.0;
  local whole = pct.tointeger();
  local frac = ((pct - whole) * 100.0 + 0.5).tointeger();
  if (frac >= 100) {
    whole += 1;
    frac -= 100;
  }
  local fracStr = frac < 10 ? "0" + frac : "" + frac;
  return "" + whole + "." + fracStr;
}

function OpexC76GetBuildableEngines(vehicleType)
{
  local res = {};
  local list = AIEngineList(vehicleType);
  for (local e = list.Begin(); !list.IsEnd(); e = list.Next()) {
    if (AIEngine.IsBuildable(e)) {
      res.rawset(e, true);
    }
  }
  return res;
}

function OpexC76CountEngineChanges(curr, prev)
{
  if (prev == null) return 0;
  local count = 0;
  foreach (e, _ in curr) {
    if (!(e in prev)) count++;
  }
  foreach (e, _ in prev) {
    if (!(e in curr)) count++;
  }
  return count;
}

function OpexC76FlushYear(year)
{
  if (!C39_INVALIDATION_PROBE || C76_YEAR_LEDGER == null) return;
  if (year < 1970) return;
  local rec = (year in C76_YEAR_LEDGER) ? C76_YEAR_LEDGER[year] : {
    full = 0, incremental = 0, avoided = 0, ops_total = 0, days_total = 0,
    unchanged_deps = 0, top1_unchanged = 0, reasons = {}
  };
  local avoided = ("avoided" in rec) ? rec.avoided : 0;
  local reasonsStr = "";
  if ("reasons" in rec && typeof rec.reasons == "table") {
    local rList = [];
    foreach (r, count in rec.reasons) {
      rList.append(r + ":" + count);
    }
    if (rList.len() > 0) {
      reasonsStr = " reasons=" + rList[0];
      for (local i = 1; i < rList.len(); i++) {
        reasonsStr += "," + rList[i];
      }
    }
  }
  OpexC76Log("phase=regen_year year=" + year
             + " full=" + rec.full
             + " avoided=" + avoided
             + " incremental=" + rec.incremental
             + " ops_total=" + rec.ops_total
             + " days_total=" + rec.days_total
             + " unchanged_deps=" + rec.unchanged_deps
             + " top1_unchanged=" + rec.top1_unchanged
             + reasonsStr);
}
