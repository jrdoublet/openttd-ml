/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Publie a l'entree du mois suivant : ainsi toutes les tranches du mois clos sont attribuees
 * a leur tache effective, y compris une continuation rail qui precede la file. */
function OpexAI::_logC41MonthlyBusyLedger()
{
  if (!C41_MONTHLY_BUSY_LEDGER || this._c41MonthlyBusyLedger == null) return;
  local year = this._c41MonthlyBusyMonth / 12;
  local month = this._c41MonthlyBusyMonth % 12 + 1;
  foreach (task, entry in this._c41MonthlyBusyLedger) {
    OpexC41SchedulerLog("C41_MONTH_BUSY", "year=" + year + " month=" + month + " task=" + task
                        + " calls=" + entry.calls + " ran=" + entry.ran + " ops=" + entry.ops);
  }
}
/* Publication annuelle, hors des passages mesures : au plus une ligne par categorie et par an.
 * Reset apres publication afin que chaque ligne decrive une fenetre comparable. */
function OpexAI::_logC41SlackLedger(year)
{
  if (!C41_SLACK_LEDGER || this._c41SlackLedger == null) return;
  foreach (task, entry in this._c41SlackLedger) {
    OpexC41SchedulerLog("C41_SLACK_LEDGER", "year=" + year + " task=" + task
                        + " calls=" + entry.calls + " ran=" + entry.ran + " ops=" + entry.ops
                        + " slack_ops_available=" + entry.slackAvailable
                        + " slack_ops_used=" + entry.slackUsed
                        + " slack_ops_left=" + entry.slackLeft);
  }
  this._c41SlackLedger = {};
}
/* C41.13 : photographie sans cout de carte ni de catalogue. Les dates sont posees seulement par
 * C41.0 au premier evenement d'une rafale ; une couche sans date ne produit donc pas de faux
 * point de fraicheur. */
function OpexAI::_recordC41StaleOpportunity(slackLeft)
{
  if ((!C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER) || this._staleness == null) return;
  local now = AIDate.GetCurrentDate();
  foreach (layer in ["cargos", "towns", "industries", "rail", "road", "air", "water"]) {
    local since = this._staleness.dirtySince.catalog[layer];
    if (since < 0) continue;
    local key = "catalog." + layer;
    if (C41_OPPORTUNITY_LEDGER && this._c41OpportunityLedger != null) {
      local entry = (key in this._c41OpportunityLedger) ? this._c41OpportunityLedger[key]
          : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
      local age = now - since;
      entry.observations++;
      entry.staleDays += age;
      if (age > entry.maxStaleDays) entry.maxStaleDays = age;
      entry.slackLeft += slackLeft;
      this._c41OpportunityLedger.rawset(key, entry);
    }
    local hint = OpexC41MicrotaskOpsHint(key);
    if (C41_ADMISSION_LEDGER && hint > 0 && this._c41AdmissionLedger != null) {
      local admission = (key in this._c41AdmissionLedger) ? this._c41AdmissionLedger[key]
          : { checks = 0, fits = 0, maxSlackLeft = 0, targetOps = hint };
      admission.checks++;
      if (slackLeft >= hint) admission.fits++;
      if (slackLeft > admission.maxSlackLeft) admission.maxSlackLeft = slackLeft;
      this._c41AdmissionLedger.rawset(key, admission);
    }
  }
  foreach (layer in ["rail", "road", "air", "water"]) {
    local since = this._staleness.dirtySince.candidates[layer];
    if (since < 0) continue;
    local key = "candidates." + layer;
    local entry = (key in this._c41OpportunityLedger) ? this._c41OpportunityLedger[key]
        : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
    local age = now - since;
    entry.observations++;
    entry.staleDays += age;
    if (age > entry.maxStaleDays) entry.maxStaleDays = age;
    entry.slackLeft += slackLeft;
    this._c41OpportunityLedger.rawset(key, entry);
  }
  foreach (layer in ["portfolio", "selection"]) {
    local since = this._staleness.dirtySince[layer];
    if (since < 0) continue;
    local entry = (layer in this._c41OpportunityLedger) ? this._c41OpportunityLedger[layer]
        : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
    local age = now - since;
    entry.observations++;
    entry.staleDays += age;
    if (age > entry.maxStaleDays) entry.maxStaleDays = age;
    entry.slackLeft += slackLeft;
    this._c41OpportunityLedger.rawset(layer, entry);
  }
}
function OpexAI::_logC41AdmissionLedger(year)
{
  if (!C41_ADMISSION_LEDGER || this._c41AdmissionLedger == null) return;
  foreach (layer, entry in this._c41AdmissionLedger) {
    OpexC41SchedulerLog("C41_ADMISSION_LEDGER", "year=" + year + " layer=" + layer
                        + " target_ops=" + entry.targetOps + " checks=" + entry.checks
                        + " fits=" + entry.fits + " max_slack_ops_left=" + entry.maxSlackLeft);
  }
  this._c41AdmissionLedger = {};
}
function OpexAI::_logC41OpportunityLedger(year)
{
  if (!C41_OPPORTUNITY_LEDGER || this._c41OpportunityLedger == null) return;
  foreach (layer, entry in this._c41OpportunityLedger) {
    OpexC41SchedulerLog("C41_OPPORTUNITY_LEDGER", "year=" + year + " layer=" + layer
                        + " observations=" + entry.observations + " stale_days_sum=" + entry.staleDays
                        + " max_stale_days=" + entry.maxStaleDays + " slack_ops_left=" + entry.slackLeft);
  }
  this._c41OpportunityLedger = {};
}
/* C41.46 : accumulateur UNIQUE (pas par categorie, contrairement aux autres ledgers C41) -- il
 * n'existe qu'un seul canal de recherche rail a la fois (this._railSearch), donc rien a ventiler. */
function OpexAI::_recordC41RailSliceLedger(netOps, taskOps, iterDelta, done)
{
  if (this._c41RailSliceLedger == null) {
    this._c41RailSliceLedger = { calls = 0, notDoneCalls = 0, netOps = 0, taskOps = 0, iterDelta = 0 };
  }
  local entry = this._c41RailSliceLedger;
  entry.calls++;
  if (!done) entry.notDoneCalls++;
  entry.netOps += netOps;
  entry.taskOps += taskOps;
  entry.iterDelta += iterDelta;
}
/* Publication annuelle, comme C41.11. `not_done_calls` = tranches qui n'ont PAS atteint
 * slice.done (recherche toujours en "search" apres l'appel) ; calls - not_done_calls = tranches
 * qui ont termine leur recherche (transition vers phase "build") cette annee. */
function OpexAI::_logC41RailSliceLedger(year)
{
  if (!C41_RAIL_SLICE_LEDGER || this._c41RailSliceLedger == null
      || this._c41RailSliceLedger.calls == 0) {
    this._c41RailSliceLedger = null;
    return;
  }
  local entry = this._c41RailSliceLedger;
  OpexC41RailSliceLog("year=" + year + " calls=" + entry.calls
                      + " not_done_calls=" + entry.notDoneCalls
                      + " net_ops=" + entry.netOps + " task_ops=" + entry.taskOps
                      + " iter_delta=" + entry.iterDelta);
  this._c41RailSliceLedger = null;
}
/* C39.6 : accumulateur PAR CLE (contrairement a C41.46, canal rail unique) -- la cle croise le
 * nom de tache de file et la presence d'une tranche A* dans la meme passe. */
function OpexAI::_recordC39PassClockLedger(key, days, ticks, ops, sliceDays, sliceTicks, sliceOps)
{
  if (this._c39PassClockLedger == null) this._c39PassClockLedger = {};
  local entry = (key in this._c39PassClockLedger) ? this._c39PassClockLedger[key]
      : { passes = 0, days = 0, ticks = 0, ops = 0, sliceDays = 0, sliceTicks = 0, sliceOps = 0 };
  entry.passes++;
  entry.days += days;
  entry.ticks += ticks;
  entry.ops += ops;
  entry.sliceDays += sliceDays;
  entry.sliceTicks += sliceTicks;
  entry.sliceOps += sliceOps;
  this._c39PassClockLedger.rawset(key, entry);
}
function OpexAI::_recordTownWorkerSlice(sliceOps, builtCount)
{
  if (this._townWorkerStats == null) {
    this._townWorkerStats = { slices = 0, opsMax = 0, opsTotal = 0, built = 0 };
  }
  this._townWorkerStats.slices++;
  this._townWorkerStats.opsTotal += sliceOps;
  if (sliceOps > this._townWorkerStats.opsMax) this._townWorkerStats.opsMax = sliceOps;
  this._townWorkerStats.built += builtCount;
}

/* Publication annuelle, comme les autres ledgers C39/C41 : une ligne par cle, reset apres
 * publication pour que chaque ligne decrive une fenetre comparable (meme motif que
 * _logC41SlackLedger / _logC41RailSliceLedger). */
function OpexAI::_logC39PassClockLedger(year)
{
  if (!C39_PASS_CLOCK_LEDGER) return;
  if (this._c39PassClockLedger != null) {
    foreach (key, entry in this._c39PassClockLedger) {
      OpexC39PassClockLog("phase=annual year=" + year + " key=" + key
                          + " passes=" + entry.passes + " days=" + entry.days
                          + " ticks=" + entry.ticks + " ops=" + entry.ops
                          + " slice_days=" + entry.sliceDays + " slice_ticks=" + entry.sliceTicks
                          + " slice_ops=" + entry.sliceOps);
    }
    this._c39PassClockLedger = {};
  }
  if (this._townWorkerStats != null && (this._townWorkerStats.slices > 0 || (C80_DOUBLE_REGISTER && C80_WORKER_TOWN))) {
    OpexC39PassClockLog("phase=town_worker_year year=" + year
                        + " slices=" + this._townWorkerStats.slices
                        + " ops_max=" + this._townWorkerStats.opsMax
                        + " ops_total=" + this._townWorkerStats.opsTotal
                        + " built=" + this._townWorkerStats.built);
    this._townWorkerStats = { slices = 0, opsMax = 0, opsTotal = 0, built = 0 };
  }
}

/* V95 item 1 — tours de file selectionnes vs no-op. Piggyback sur
 * _runNextTaskWithSlackLedger (actif uniquement sous probe_scheduler) : opcodes/jours/ticks
 * sont ceux deja mesures par C39.6, sans begin/end supplementaire.
 *
 * Definition de did_work par dispatcher (Issues 2-4) :
 *   catalog: reselection / regeneration / tranche AIR C78 (ran == true).
 *   report: publication annuelle (this._lastReportYear != year).
 *   repay: pret effectivement baisse (curLoan < preLoan).
 *   scrap: vehicule vendu ou ligne retiree (curVehs < preVehs || curLines < preLines).
 *   air: construction aerienne executee (ran == true ; desactive sous AIR_PORTFOLIO).
 *   air_fleet: opportunite injectee dans le vivier (this._projects != preProjects) ou achat.
 *   projects: 3 etats :
 *     - projects_selected_noop : vivier vide (projects_empty, cls=after) ou invalide (projects_invalidated, cls=pred).
 *     - projects_examined_no_effect : vivier examine, aucun effet (cls=after).
 *     - projects_useful : vrai travail (cls=work) -> construction lancee/achevee (built),
 *       A* rail demarre (rail_search_started), A* rail consomme (rail_search_consumed),
 *       reactif C83 consomme (c83_reactive), abandon traite (abandon_handled).
 *       Seul projects_useful compte comme passage utile.
 *   expand: 2e train / wagon ajoute ou recherche/expansion demarree (curVehs > preVehs || railExp || railSearch).
 *   refleet: vehicule ajoute (curVehs > preVehs).
 *   town_growth: travailleur cree ou vehicule/gare/ligne ajoutee.
 *   taches desactivees (c41_water, c41_road, etc.): task_disabled (cls=pred).
 *
 * Invariant : pour chaque tache, did_work + noop == selected.
 * cls=pred : garde pre-dispatch identifiee avant execution bloquant la tache.
 * cls=after : absence d'effet ou garde dynamique constatee apres execution.
 * cls=work : vrai travail observe. */
function OpexAI::_schedIdleEnsure()
{
  if (!V95_SCHED_IDLE_LEDGER) return;
  if (this._schedIdleLastWorkDate == null) this._schedIdleLastWorkDate = {};
  if (this._schedIdleLastWorkTick == null) this._schedIdleLastWorkTick = {};
  if (this._p2PendingBuilds == null) this._p2PendingBuilds = [];
  if (this._p2TasksSinceProjects == null) this._p2TasksSinceProjects = [];
  if (this._p2ProjectsSeq == null) this._p2ProjectsSeq = 0;
  if (this._p2LastProjectsPostBest == null) this._p2LastProjectsPostBest = -1;
  if (this._p2LastProjectsPostCap == null) this._p2LastProjectsPostCap = -1;
  if (this._p5EpisodeActive == null) this._p5EpisodeActive = false;
  if (this._p5EpisodeId == null) this._p5EpisodeId = -1;
  if (this._p5EpisodeUnusedOps == null) this._p5EpisodeUnusedOps = 0;
  if (this._p5EpisodeUsedOps == null) this._p5EpisodeUsedOps = 0;
  if (this._p5EpisodeDispatches == null) this._p5EpisodeDispatches = 0;
  if (this._p5RailSearchSeq == null) this._p5RailSearchSeq = 0;
  if (this._p5ActiveRailSearch == null) this._p5ActiveRailSearch = null;
  if (this._p5LastTrackedRailSearch == null) this._p5LastTrackedRailSearch = null;
  if (this._schedIdlePreMarkLeft == null) this._schedIdlePreMarkLeft = 10000;
}

function OpexAI::_schedIdlePreDispatch()
{
  if (!V95_SCHED_IDLE_LEDGER) return;
  this._schedIdleEnsure();
  this._schedIdlePreMarkLeft = AIController.GetOpsTillSuspend();
  this._schedIdlePeekTask = null;
  this._schedIdlePredReason = null;
  this._schedIdlePredClass = null;

  if (this._taskQueue == null || this._taskQueue.len() == 0) return;

  local task = null;
  local cycle = this._taskCycle;
  for (local index = this._taskCursor; index < this._taskQueue.len(); index++) {
    local candidate = this._taskQueue[index];
    if (candidate.enabled && candidate.dueCycle <= cycle) {
      task = candidate;
      break;
    }
  }
  if (task == null) {
    cycle++;
    for (local index = 0; index < this._taskQueue.len(); index++) {
      local candidate = this._taskQueue[index];
      if (candidate.enabled && candidate.dueCycle <= cycle) {
        task = candidate;
        break;
      }
    }
  }
  if (task == null) return;

  local taskName = task.name;
  this._schedIdlePeekTask = taskName;

  local date = AIDate.GetCurrentDate();
  local tick = AIController.GetTick();
  this._schedIdlePreDate = date;
  this._schedIdlePreTick = tick;

  this._schedIdlePreVehCount = AIVehicleList().Count();
  this._schedIdlePreLinesCount = this._lines.len();
  this._schedIdlePreLoan = AICompany.GetLoanAmount();
  this._schedIdlePreRailSearch = this._railSearch;
  this._schedIdlePreActiveWorker = this._activeWorker;
  this._schedIdlePreProjects = this._projects;
  this._schedIdlePreBestLen = (this._projects != null && ("best" in this._projects) && this._projects.best != null) ? this._projects.best.len() : 0;
  this._schedIdlePreHadAbandons = this._hadAbandonsThisPass;
  this._schedIdlePreC83Preempt = (C83_PREEMPT_OPEN && ("_c83PreemptEnqueued" in this)) ? this._c83PreemptEnqueued : 0;
  this._schedIdlePreC78Rebuild = (("c78AirRebuild" in task) && task.c78AirRebuild != null) ? task.c78AirRebuild : null;
  this._p2PreCapital = OpexAvailableCapital();
  this._p2PreCandidateGroupsLen = (this._projects != null && ("candidateGroups" in this._projects) && this._projects.candidateGroups != null) ? this._projects.candidateGroups.len() : 0;
  this._p2CatalogPreReason = null;

  local curYear = AIDate.GetYear(date);
  local curMonth = AIDate.GetMonth(date);
  local curYm = curYear * 12 + curMonth;

  if (this._projects == null && taskName != "catalog") {
    this._schedIdlePredReason = "projects_null";
    this._schedIdlePredClass = "pred";
    return;
  }

  if (taskName == "report") {
    if (this._lastReportYear == curYear) {
      this._schedIdlePredReason = "report_same_year";
      this._schedIdlePredClass = "pred";
    }
  } else if (taskName == "repay") {
    if (this._lastRepayMonth == curYm) {
      this._schedIdlePredReason = "repay_same_month";
      this._schedIdlePredClass = "pred";
    }
  } else if (taskName == "air") {
    if (AIR_PORTFOLIO) {
      this._schedIdlePredReason = "air_disabled";
      this._schedIdlePredClass = "pred";
    }
  } else if (taskName == "expand") {
    if (!RAIL_EXPAND && !RAIL_REFLEET) {
      this._schedIdlePredReason = "expand_disabled";
      this._schedIdlePredClass = "pred";
    }
  } else if (taskName == "town_growth") {
    if (!TOWN_GROWTH_ENABLED) {
      this._schedIdlePredReason = "town_growth_disabled";
      this._schedIdlePredClass = "pred";
    }
  } else if (taskName == "catalog") {
    if (("c78AirRebuild" in task) && task.c78AirRebuild != null) {
      local s = task.c78AirRebuild;
      if (("partialPending" in s) && s.partialPending) {
        this._schedIdlePredReason = "catalog_c78_partial_pending";
        this._schedIdlePredClass = "pred";
      } else if (s.phase != "apply") {
        this._schedIdlePredReason = "catalog_c78_slice_incomplete";
        this._schedIdlePredClass = "pred";
      }
      this._p2CatalogPreReason = "c78_air";
    } else {
      local stale = false;
      if (this._projects != null) {
        local budgetNow = OpexAvailableCapital();
        local budgetThen = this._projects.capitalBudget;
        local nextCap = ("stats" in this._projects) && this._projects.stats != null
            && ("nextProjectCapital" in this._projects.stats) && this._projects.stats.nextProjectCapital > 0
            ? this._projects.stats.nextProjectCapital : 0;
        if (AIR_EFFICIENCY_RESELECT) {
          if (nextCap > 0 && budgetThen < nextCap && budgetNow >= nextCap) stale = true;
        } else {
          local gainOk = budgetNow > budgetThen + PORTFOLIO_REFRESH_MIN_GAIN;
          local doubleOk = budgetNow > budgetThen * 2;
          if (gainOk && doubleOk) stale = true;
        }
      }
      local isFresh = false;
      if (C76_REGEN_TARGETED) {
        local c76LayerChanged = this._c76AnyLayerChanged();
        local c76PeriodicDue = (this._c76LastRegenQuarter < 0 || curYear > this._c76LastRegenQuarter);
        local c76ReloadDue = this._c76ForceReloadRegen;
        if ((AIR_EFFICIENCY_RESELECT || this._lastCatalogMonth == curYm) && this._projects != null && !stale &&
            !this._portfolioInvalidated && !c76LayerChanged && !c76PeriodicDue && !c76ReloadDue) {
          this._schedIdlePredReason = "catalog_fresh";
          this._schedIdlePredClass = "pred";
          isFresh = true;
        }
      } else {
        if ((AIR_EFFICIENCY_RESELECT || this._lastCatalogMonth == curYm) && this._projects != null && !stale && !this._portfolioInvalidated) {
          this._schedIdlePredReason = "catalog_fresh";
          this._schedIdlePredClass = "pred";
          isFresh = true;
        }
      }
      if (isFresh) {
        this._p2CatalogPreReason = "catalog_fresh";
      } else if (this._portfolioInvalidated) {
        this._p2CatalogPreReason = "invalidation";
      } else if (stale) {
        this._p2CatalogPreReason = "capital";
      } else if (this._lastCatalogMonth != curYm) {
        this._p2CatalogPreReason = "month";
      } else {
        this._p2CatalogPreReason = "catalog_other";
      }
    }
  } else if (taskName == "projects") {
    if (this._portfolioInvalidated) {
      this._schedIdlePredReason = "projects_invalidated";
      this._schedIdlePredClass = "pred";
    }
  } else if (taskName == "c41_water" || taskName == "c41_road" ||
             taskName == "c41_rail_signals" || taskName == "c41_rail_junction") {
    this._schedIdlePredReason = "task_disabled";
    this._schedIdlePredClass = "pred";
  }
}

/* P5 : observatoire de scan du vivier de candidats (sous probe_scheduler). */
function OpexAI::_p5ScanCandidatePool(projects, availableCapital)
{
  local res = {
    nAlts = 0,
    nRail = 0,
    nAir = 0,
    nRoad = 0,
    nFleet = 0,
    nWater = 0,
    bestRail = null,
    bestRailRank = -1,
    bestRailScore = 0.0,
    bestRailFinanceCap = 0,
    bestRailDeficit = 0,
    bestRailKind = "none",
    bestRailSrc = -1,
    bestRailDst = -1,
    bestRailProfit = 0,
    bestRailRoi = 0,
    bestRailIters = -1,
    aheadAir = 0,
    aheadRoad = 0,
    aheadFleet = 0,
    bestNonRailMode = "none",
    bestNonRailScore = 0.0,
    bestNonRailCap = 0,
    bestRailCfFinanceCap = 0,
    bestRailCfDeficit = 0,
    bestRailCfScore = 0.0,
    bestRailCfRank = -1
  };

  if (projects == null || !("candidateGroups" in projects) || projects.candidateGroups == null) {
    return res;
  }

  local alts = [];
  foreach (key, list in projects.candidateGroups) {
    if (list == null) continue;
    foreach (p in list) {
      if (p == null) continue;
      alts.append(p);
    }
  }
  res.nAlts = alts.len();
  if (res.nAlts == 0) return res;

  local scored = [];
  local bestRailCand = null;
  local bestRailScore = -1.0;
  local bestRailFinanceCap = 0;

  foreach (p in alts) {
    local mode = ("mode" in p) ? p.mode : "unknown";
    if (mode == "rail") res.nRail++;
    else if (mode == "air") res.nAir++;
    else if (mode == "road") res.nRoad++;
    else if (mode == "fleet") res.nFleet++;
    else if (mode == "water") res.nWater++;

    local financeCap = OpexProjectFinanceCapital(p);
    local profit = (C70_PROFIT_CALIBRATED) ? OpexCalibratedProfit(p) : (("profitAnnual" in p) ? p.profitAnnual : 0);
    local score = OpexProjectScore(profit, financeCap);

    scored.append({
      p = p,
      mode = mode,
      score = score,
      financeCap = financeCap,
      profit = profit
    });

    if (mode == "rail") {
      if (score > bestRailScore || (score == bestRailScore && bestRailCand != null && profit > bestRailCand.profitAnnual)) {
        bestRailScore = score;
        bestRailCand = p;
        bestRailFinanceCap = financeCap;
      }
    } else {
      if (score > res.bestNonRailScore) {
        res.bestNonRailScore = score;
        res.bestNonRailMode = mode;
        res.bestNonRailCap = financeCap;
      }
    }
  }

  if (bestRailCand != null) {
    res.bestRail = bestRailCand;
    res.bestRailScore = bestRailScore;
    res.bestRailFinanceCap = bestRailFinanceCap;
    res.bestRailDeficit = (bestRailFinanceCap > availableCapital) ? (bestRailFinanceCap - availableCapital) : 0;
    res.bestRailKind = ("kind" in bestRailCand) ? bestRailCand.kind : "unknown";
    res.bestRailSrc = ("src" in bestRailCand) ? bestRailCand.src : -1;
    res.bestRailDst = ("dst" in bestRailCand) ? bestRailCand.dst : -1;
    res.bestRailProfit = ("profitAnnual" in bestRailCand) ? bestRailCand.profitAnnual : 0;
    res.bestRailRoi = ("roi" in bestRailCand) ? bestRailCand.roi : 0;
    res.bestRailIters = (("payload" in bestRailCand) && bestRailCand.payload != null && ("iterations" in bestRailCand.payload))
        ? bestRailCand.payload.iterations : -1;

    local rank = 0;
    foreach (s in scored) {
      if (s.score > bestRailScore) {
        rank++;
        if (s.mode == "air") res.aheadAir++;
        else if (s.mode == "road") res.aheadRoad++;
        else if (s.mode == "fleet") res.aheadFleet++;
      }
    }
    res.bestRailRank = rank;

    local cfFinanceCap = (bestRailFinanceCap * 96) / 170;
    local cfScore = OpexProjectScore(res.bestRailProfit, cfFinanceCap);
    res.bestRailCfFinanceCap = cfFinanceCap;
    res.bestRailCfDeficit = (cfFinanceCap > availableCapital) ? (cfFinanceCap - availableCapital) : 0;
    res.bestRailCfScore = cfScore;

    local cfRank = 0;
    foreach (s in scored) {
      if (s.score > cfScore) cfRank++;
    }
    res.bestRailCfRank = cfRank;
  }

  return res;
}

function OpexAI::_p5OnRailSearchStart(kind, cand, budget)
{
  if (!V95_SCHED_IDLE_LEDGER) return;
  this._schedIdleEnsure();
  if (this._p5ActiveRailSearch != null) {
    this._p5OnRailSearchEnd(null, "cancelled", "none");
  }
  this._p5RailSearchSeq++;
  this._p5ActiveRailSearch = {
    id = this._p5RailSearchSeq,
    kind = kind,
    src = (cand != null && ("src" in cand)) ? cand.src : -1,
    dst = (cand != null && ("dst" in cand)) ? cand.dst : -1,
    startDate = AIDate.GetCurrentDate(),
    startTick = AIController.GetTick(),
    budget = budget,
    iters = 0,
    ops = 0,
    slices = 0
  };
}

function OpexAI::_p5OnRailSearchEnd(state, outcome, result)
{
  if (!V95_SCHED_IDLE_LEDGER) return;
  if (this._p5ActiveRailSearch == null) return;

  local curDate = AIDate.GetCurrentDate();
  local curTick = AIController.GetTick();
  local sDays = curDate - this._p5ActiveRailSearch.startDate;
  local sTicks = curTick - this._p5ActiveRailSearch.startTick;

  local finalIters = this._p5ActiveRailSearch.iters;
  if (state != null && ("spent" in state) && state.spent > finalIters) {
    finalIters = state.spent;
  }

  OpexSchedIdleLog("P5_RAIL_SEARCH", "id=" + this._p5ActiveRailSearch.id
      + " kind=" + this._p5ActiveRailSearch.kind
      + " src=" + this._p5ActiveRailSearch.src + " dst=" + this._p5ActiveRailSearch.dst
      + " iters=" + finalIters + " ops=" + this._p5ActiveRailSearch.ops
      + " slices=" + this._p5ActiveRailSearch.slices
      + " days=" + sDays + " ticks=" + sTicks
      + " outcome=" + outcome + " result=" + result
      + " budget=" + this._p5ActiveRailSearch.budget);

  this._p5ActiveRailSearch = null;
}

function OpexAI::_schedIdlePostDispatch(taskName, ran, ops, days, ticks)
{
  if (!V95_SCHED_IDLE_LEDGER) return;
  if (taskName == null) taskName = "idle";
  this._schedIdleEnsure();
  if (this._schedIdlePeekTask != taskName) this._schedIdlePredReason = null;

  /* P5 : comptabilite opcodes et reliquat d'attente */
  local markLeft = (this._schedIdlePreMarkLeft != null) ? this._schedIdlePreMarkLeft : 10000;
  local unused = (ticks <= 0) ? (ops < markLeft ? markLeft - ops : 0) : ((markLeft + ticks * 10000) - ops);
  if (unused < 0) unused = 0;
  if (this._p5EpisodeActive) {
    this._p5EpisodeUnusedOps += unused;
    this._p5EpisodeUsedOps += ops;
    this._p5EpisodeDispatches++;
  }

  /* P5 : detecter le demarrage d'une recherche rail */
  if (this._railSearch != null && this._p5ActiveRailSearch == null) {
    local rs = this._railSearch;
    local kind = ("kind" in rs) ? rs.kind : "primary";
    local cand = ("candidate" in rs) ? rs.candidate : (("line" in rs) ? rs.line : null);
    local budget = ("iterationBudget" in rs) ? rs.iterationBudget : 0;
    this._p5OnRailSearchStart(kind, cand, budget);
  }

  /* P5 : cumuler les opcodes et iterations de la tranche executee dans ce tick */
  if (this._p5ActiveRailSearch != null && this._c41RailSliceLastOps >= 0) {
    this._p5ActiveRailSearch.ops += this._c41RailSliceLastOps;
    this._p5ActiveRailSearch.iters += this._c41RailSliceLastIterDelta;
    this._p5ActiveRailSearch.slices++;
  }

  /* P5 : detecter la fin d'une recherche rail */
  if (this._p5ActiveRailSearch != null && (this._railSearch == null || this._railSearch.phase != "search")) {
    if (this._railSearch == null) {
      this._p5OnRailSearchEnd(null, "cancelled", "none");
    } else {
      local finalOutcome = "none";
      local finalResult = "none";
      if (this._railSearch.kind == "primary") {
        local plan = ("candidate" in this._railSearch && this._railSearch.candidate != null && ("railPlan" in this._railSearch.candidate))
            ? this._railSearch.candidate.railPlan
            : (("plan" in this._railSearch) ? this._railSearch.plan : null);
        if (plan != null) {
          if (("ok" in plan) && plan.ok) {
            finalOutcome = "OK";
            finalResult = "found";
          } else if (("reason" in plan) && plan.reason != null && plan.reason != "") {
            finalOutcome = plan.reason;
            finalResult = (finalOutcome == "ABND" || finalOutcome == "DEAD") ? "cap" : "none";
          }
        }
      } else if (this._railSearch.kind == "upgrade") {
        local slice = ("search" in this._railSearch) ? this._railSearch.search : null;
        finalOutcome = (slice != null && ("stop" in slice)) ? slice.stop : "OK";
        finalResult = (finalOutcome == "OK") ? "found" : ((finalOutcome == "ABND" || finalOutcome == "DEAD") ? "cap" : "none");
      }
      this._p5OnRailSearchEnd(this._railSearch, finalOutcome, finalResult);
    }
  }

  local didWork = false;
  local reason = "unspecified_noop";
  local skipClass = "after";
  local subField = "none";
  local curVehs = AIVehicleList().Count();
  local curLines = this._lines.len();
  local builtLine = curLines > this._schedIdlePreLinesCount;
  local builtVeh = curVehs > this._schedIdlePreVehCount;

  if (taskName == "projects") {
    if (this._schedIdlePredReason == "projects_invalidated") {
      if (!ran) {
        didWork = false; reason = "projects_invalidated"; skipClass = "pred"; subField = "invalidated";
      } else {
        didWork = true; reason = "projects_mismatch"; skipClass = "work"; subField = "mismatch";
      }
    } else if (this._schedIdlePreBestLen == 0) {
      didWork = false; reason = "projects_empty"; skipClass = "after"; subField = "empty";
    } else {
      local railSearchStarted = this._railSearch != null && this._schedIdlePreRailSearch == null;
      local railSearchConsumed = this._schedIdlePreRailSearch != null && (this._railSearch == null || this._railSearch != this._schedIdlePreRailSearch);
      local c83Reactive = C83_PREEMPT_OPEN && ("_c83PreemptEnqueued" in this) && this._c83PreemptEnqueued > this._schedIdlePreC83Preempt;
      local abandonHandled = this._hadAbandonsThisPass != this._schedIdlePreHadAbandons || (this._hadAbandonsThisPass == true);

      if (builtLine || builtVeh || railSearchStarted || railSearchConsumed || c83Reactive || abandonHandled) {
        didWork = true;
        reason = "projects_useful";
        skipClass = "work";
        if (builtLine || builtVeh) subField = "built";
        else if (railSearchStarted) subField = "rail_search_started";
        else if (railSearchConsumed) subField = "rail_search_consumed";
        else if (c83Reactive) subField = "c83_reactive";
        else if (abandonHandled) subField = "abandon_handled";
        else subField = "useful_other";
      } else {
        didWork = false;
        reason = "projects_examined_no_effect";
        skipClass = "after";
        subField = "no_effect";
      }
    }
  } else if (taskName == "report") {
    if (this._schedIdlePredReason == "report_same_year") {
      if (!ran) { didWork = false; reason = "report_same_year"; skipClass = "pred"; }
      else { didWork = true; reason = "report_mismatch"; skipClass = "work"; }
    } else {
      if (ran) { didWork = true; reason = "report_work"; skipClass = "work"; }
      else { didWork = false; reason = "report_mismatch"; skipClass = "after"; }
    }
  } else if (taskName == "repay") {
    if (this._schedIdlePredReason == "repay_same_month") {
      if (!ran) { didWork = false; reason = "repay_same_month"; skipClass = "pred"; }
      else { didWork = true; reason = "repay_mismatch"; skipClass = "work"; }
    } else {
      local curLoan = AICompany.GetLoanAmount();
      if (curLoan < this._schedIdlePreLoan) {
        didWork = true; reason = "repay_work"; skipClass = "work";
      } else {
        didWork = false; reason = "repay_no_work"; skipClass = "after";
      }
    }
  } else if (taskName == "catalog") {
    if (this._schedIdlePredReason != null) {
      if (!ran) { didWork = false; reason = this._schedIdlePredReason; skipClass = "pred"; }
      else { didWork = true; reason = "catalog_mismatch"; skipClass = "work"; }
    } else {
      if (ran) {
        didWork = true; reason = "catalog_refresh"; skipClass = "work";
      } else {
        local c78Now = (("c78AirRebuild" in this._taskQueue[0]) && this._taskQueue[0].c78AirRebuild != null);
        if (c78Now && this._schedIdlePreC78Rebuild == null) {
          didWork = false; reason = "catalog_c78_started"; skipClass = "after";
        } else {
          didWork = false; reason = "catalog_mismatch"; skipClass = "after";
        }
      }
    }
  } else if (taskName == "air") {
    if (this._schedIdlePredReason == "air_disabled") {
      if (!ran) { didWork = false; reason = "air_disabled"; skipClass = "pred"; }
      else { didWork = true; reason = "air_mismatch"; skipClass = "work"; }
    } else {
      didWork = ran; reason = ran ? "air_work" : "air_no_work"; skipClass = ran ? "work" : "after";
    }
  } else if (taskName == "air_fleet") {
    local curVehs = AIVehicleList().Count();
    if (FLEET_PORTFOLIO) {
      if (this._projects != this._schedIdlePreProjects || curVehs != this._schedIdlePreVehCount) {
        didWork = true; reason = "air_fleet_injected"; skipClass = "work";
      } else {
        didWork = false; reason = "air_fleet_no_work"; skipClass = "after";
      }
    } else {
      if (ran || curVehs != this._schedIdlePreVehCount) {
        didWork = true; reason = "air_fleet_work"; skipClass = "work";
      } else {
        didWork = false; reason = "air_fleet_no_work"; skipClass = "after";
      }
    }
  } else if (taskName == "scrap") {
    local curVehs = AIVehicleList().Count();
    local curLines = this._lines.len();
    if (curVehs < this._schedIdlePreVehCount || curLines < this._schedIdlePreLinesCount) {
      didWork = true; reason = "scrap_work"; skipClass = "work";
    } else {
      didWork = false; reason = "scrap_no_work"; skipClass = "after";
    }
  } else if (taskName == "expand") {
    if (this._schedIdlePredReason == "expand_disabled") {
      if (!ran) { didWork = false; reason = "expand_disabled"; skipClass = "pred"; }
      else { didWork = true; reason = "expand_mismatch"; skipClass = "work"; }
    } else {
      local curVehs = AIVehicleList().Count();
      local railExp = this._railExpansion != null;
      local railSearch = this._railSearch != null && this._schedIdlePreRailSearch == null;
      if (curVehs > this._schedIdlePreVehCount || railExp || railSearch) {
        didWork = true; reason = "expand_work"; skipClass = "work";
      } else {
        didWork = false; reason = "expand_no_work"; skipClass = "after";
      }
    }
  } else if (taskName == "refleet") {
    local curVehs = AIVehicleList().Count();
    if (curVehs > this._schedIdlePreVehCount) {
      didWork = true; reason = "refleet_work"; skipClass = "work";
    } else {
      didWork = false; reason = "refleet_no_work"; skipClass = "after";
    }
  } else if (taskName == "town_growth") {
    if (this._schedIdlePredReason == "town_growth_disabled") {
      if (!ran) { didWork = false; reason = "town_growth_disabled"; skipClass = "pred"; }
      else { didWork = true; reason = "town_growth_mismatch"; skipClass = "work"; }
    } else {
      local curVehs = AIVehicleList().Count();
      local curLines = this._lines.len();
      local worker = this._activeWorker != null && this._schedIdlePreActiveWorker == null;
      if (curVehs > this._schedIdlePreVehCount || curLines > this._schedIdlePreLinesCount || worker) {
        didWork = true; reason = "town_growth_work"; skipClass = "work";
      } else {
        didWork = false; reason = "town_growth_no_work"; skipClass = "after";
      }
    }
  } else {
    if (this._schedIdlePredReason != null) {
      didWork = false; reason = this._schedIdlePredReason; skipClass = "pred";
    } else {
      didWork = ran; reason = ran ? "unspecified_work" : "unspecified_noop"; skipClass = ran ? "work" : "after";
    }
  }

  if (didWork) {
    skipClass = "work";
  } else {
    if (skipClass == "work") skipClass = "after";
  }

  local now = AIDate.GetCurrentDate();
  local tick = AIController.GetTick();
  local lastDate = (taskName in this._schedIdleLastWorkDate) ? this._schedIdleLastWorkDate[taskName] : -1;
  local lastTick = (taskName in this._schedIdleLastWorkTick) ? this._schedIdleLastWorkTick[taskName] : -1;
  local ageDays = lastDate >= 0 ? now - lastDate : -1;
  local ageTicks = lastTick >= 0 ? tick - lastTick : -1;

  if (didWork) {
    this._schedIdleLastWorkDate.rawset(taskName, now);
    this._schedIdleLastWorkTick.rawset(taskName, tick);
  }

  local gapDays = -1;
  local gapTicks = -1;
  local bg = -1;
  local bgw = -1;
  if (taskName == "projects") {
    if (didWork) {
      gapDays = this._schedIdleProjectsLastDate >= 0 ? now - this._schedIdleProjectsLastDate : -1;
      gapTicks = this._schedIdleProjectsLastTick >= 0 ? tick - this._schedIdleProjectsLastTick : -1;
      bg = this._schedIdleSinceProjectsSel;
      bgw = this._schedIdleSinceProjectsWork;
      this._schedIdleProjectsLastDate = now;
      this._schedIdleProjectsLastTick = tick;
      this._schedIdleSinceProjectsSel = 0;
      this._schedIdleSinceProjectsWork = 0;
    } else {
      this._schedIdleSinceProjectsSel++;
    }
  } else {
    this._schedIdleSinceProjectsSel++;
    if (didWork) this._schedIdleSinceProjectsWork++;
  }

  local extra = "";
  if (taskName == "projects" && didWork && gapDays >= 0) {
    extra = " gap_d=" + gapDays + " gap_tk=" + gapTicks + " bg=" + bg + " bgw=" + bgw;
  }

  OpexSchedIdleLog("SCHED_IDLE", "t=" + taskName + " w=" + (didWork ? 1 : 0)
                   + " r=" + reason + " cls=" + skipClass
                   + " op=" + ops + " d=" + days + " tk=" + ticks
                   + " ad=" + ageDays + " at=" + ageTicks + extra);

  if (taskName != "projects") {
    local taskDesc = taskName + ":" + reason + ":" + (didWork ? "1" : "0");
    if (this._p2TasksSinceProjects == null) this._p2TasksSinceProjects = [];
    this._p2TasksSinceProjects.append(taskDesc);
  }

  /* P2 : observatoire du cycle de vie du portefeuille post-build */
  if (taskName == "projects" && (builtLine || builtVeh)) {
    this._p2BuildSeq++;
    local buildId = this._p2BuildSeq;
    local curDate = AIDate.GetCurrentDate();
    local curTick = AIController.GetTick();
    local nBuiltLines = curLines - this._schedIdlePreLinesCount;
    local nBuiltFleet = (nBuiltLines == 0 && curVehs > this._schedIdlePreVehCount) ? (curVehs - this._schedIdlePreVehCount) : 0;
    local nBuilt = nBuiltLines + nBuiltFleet;
    local builtMode = "unknown";
    if (nBuiltLines > 0) {
      local newLine = this._lines[curLines - 1];
      builtMode = ("mode" in newLine) ? newLine.mode : "unknown";
    } else if (nBuiltFleet > 0) {
      builtMode = "fleet";
    }
    local postCap = OpexAvailableCapital();
    local postCgLen = (this._projects != null && ("candidateGroups" in this._projects) && this._projects.candidateGroups != null) ? this._projects.candidateGroups.len() : 0;
    local postBestLen = (this._projects != null && ("best" in this._projects) && this._projects.best != null) ? this._projects.best.len() : 0;
    local st = (this._projects != null && ("stats" in this._projects)) ? this._projects.stats : null;
    local scanned = (st != null && ("cacheScanned" in st)) ? st.cacheScanned : 0;
    local retained = (st != null && ("cacheRetained" in st)) ? st.cacheRetained : 0;
    local abandon = (st != null && ("abandonFiltered" in st)) ? st.abandonFiltered : 0;
    local alts = (st != null && ("budgetConsidered" in st)) ? st.budgetConsidered : 0;
    local funded = postBestLen;
    local cause = (st != null && ("emptyCause" in st) && st.emptyCause != null && st.emptyCause != "") ? st.emptyCause : (funded > 0 ? "none" : "unknown");
    local nextCap = (st != null && ("nextProjectCapital" in st) && st.nextProjectCapital > 0) ? st.nextProjectCapital : ((st != null && ("minCapital" in st) && st.minCapital > 0) ? st.minCapital : 0);
    local bStop = (nBuilt > 0) ? "list_end" : "none";

    OpexSchedIdleLog("P2_BUILD", "id=" + buildId + " mode=" + builtMode + " n_built=" + nBuilt
        + " cap_before=" + this._p2PreCapital + " cap_after=" + postCap
        + " cg_before=" + this._p2PreCandidateGroupsLen + " cg_after=" + postCgLen
        + " scanned=" + scanned + " retained=" + retained + " abandon=" + abandon
        + " alts=" + alts + " funded=" + funded + " cause=" + cause + " next_k=" + nextCap
        + " stop=" + bStop);

    if (nBuiltLines > 0 && this._lines.len() > 0) {
      local startIdx = this._lines.len() - nBuiltLines;
      if (startIdx < 0) startIdx = 0;
      for (local li = startIdx; li < this._lines.len(); li++) {
        local newLine = this._lines[li];
        local lSrc = ("src" in newLine) ? newLine.src : (("originA" in newLine) ? newLine.originA : -1);
        local lDst = ("dst" in newLine) ? newLine.dst : (("originB" in newLine) ? newLine.originB : -1);
        local lCap = ("capital" in newLine) ? newLine.capital : (("predCapital" in newLine) ? newLine.predCapital : 0);
        local lMode = ("mode" in newLine) ? newLine.mode : builtMode;
        OpexSchedIdleLog("P5_BUILD_LINE", "id=" + buildId + " mode=" + lMode
            + " src=" + lSrc + " dst=" + lDst + " cap=" + lCap);
      }
    }

    if (postBestLen > 0) {
      OpexSchedIdleLog("P2_RESOLVE", "id=" + buildId + " days=0 ticks=0 ret_reason=immediate ret_task=projects ret_date="
          + AIDate.GetYear(curDate) + "-" + AIDate.GetMonth(curDate) + "-" + AIDate.GetDayOfMonth(curDate)
          + " funded=" + postBestLen + " cause=none");
    } else {
      local scan = this._p5ScanCandidatePool(this._projects, postCap);
      this._p5EpisodeActive = true;
      this._p5EpisodeId = buildId;
      this._p5EpisodeUnusedOps = 0;
      this._p5EpisodeUsedOps = 0;
      this._p5EpisodeDispatches = 0;

      local curDateStr = AIDate.GetYear(curDate) + "-" + AIDate.GetMonth(curDate) + "-" + AIDate.GetDayOfMonth(curDate);
      local extraRail = "";
      if (scan.nRail > 0) {
        extraRail = " rail_rank=" + scan.bestRailRank
            + " rail_kind=" + scan.bestRailKind
            + " rail_src=" + scan.bestRailSrc
            + " rail_dst=" + scan.bestRailDst
            + " rail_cap=" + scan.bestRail.capital
            + " rail_fin_cap=" + scan.bestRailFinanceCap
            + " rail_def=" + scan.bestRailDeficit
            + " rail_prof=" + scan.bestRailProfit
            + " rail_roi=" + scan.bestRailRoi
            + " rail_score=" + scan.bestRailScore
            + " rail_cf_cap=" + scan.bestRailCfFinanceCap
            + " rail_cf_def=" + scan.bestRailCfDeficit
            + " rail_cf_rank=" + scan.bestRailCfRank
            + " rail_iters=" + scan.bestRailIters
            + " ahead_air=" + scan.aheadAir
            + " ahead_road=" + scan.aheadRoad
            + " ahead_fleet=" + scan.aheadFleet;
      } else {
        extraRail = " rail_rank=-1";
      }

      OpexSchedIdleLog("P5_WAIT_START", "id=" + buildId + " date=" + curDateStr + " tick=" + curTick
          + " cap=" + postCap + " alts=" + scan.nAlts
          + " n_rail=" + scan.nRail + " n_air=" + scan.nAir + " n_road=" + scan.nRoad + " n_fleet=" + scan.nFleet
          + extraRail);

      if (this._p2PendingBuilds == null) this._p2PendingBuilds = [];
      this._p2PendingBuilds.append({
        id = buildId,
        buildDate = curDate,
        buildTick = curTick,
        cause = cause
      });
    }
  }

  /* P2 bis : observatoire de reconciliation des passages projects */
  if (taskName == "projects") {
    this._p2ProjectsSeq++;
    local passId = this._p2ProjectsSeq;
    local curDate = AIDate.GetCurrentDate();
    local curTick = AIController.GetTick();
    local inBest = this._schedIdlePreBestLen;
    local inCap = this._p2PreCapital;
    local postBest = (this._projects != null && ("best" in this._projects) && this._projects.best != null) ? this._projects.best.len() : 0;
    local postCap = OpexAvailableCapital();
    local nBuiltLines = curLines - this._schedIdlePreLinesCount;
    local nBuiltFleet = (nBuiltLines == 0 && curVehs > this._schedIdlePreVehCount) ? (curVehs - this._schedIdlePreVehCount) : 0;
    local nBuilt = nBuiltLines + nBuiltFleet;
    local passBuiltMode = "none";
    if (nBuiltLines > 0) {
      local newLine = this._lines[curLines - 1];
      passBuiltMode = ("mode" in newLine) ? newLine.mode : "unknown";
    } else if (nBuiltFleet > 0) {
      passBuiltMode = "fleet";
    }
    local passStop = (reason == "projects_invalidated") ? "invalidated"
        : (inBest == 0 ? "empty_pool" : (nBuilt > 0 ? "list_end" : "no_candidate_built"));

    local tasksSince = "";
    if (this._p2TasksSinceProjects != null && this._p2TasksSinceProjects.len() > 0) {
      foreach (idx, item in this._p2TasksSinceProjects) {
        if (idx > 0) tasksSince += ";";
        tasksSince += item;
      }
    } else {
      tasksSince = "none";
    }

    local dCap = (this._p2LastProjectsPostCap >= 0) ? (inCap - this._p2LastProjectsPostCap) : 0;
    local dBest = (this._p2LastProjectsPostBest >= 0) ? (inBest - this._p2LastProjectsPostBest) : 0;

    OpexSchedIdleLog("P2_PASS", "pass=" + passId
        + " date=" + AIDate.GetYear(curDate) + "-" + AIDate.GetMonth(curDate) + "-" + AIDate.GetDayOfMonth(curDate)
        + " tick=" + curTick + " in_best=" + inBest + " in_cap=" + inCap
        + " n_built=" + nBuilt + " stop=" + passStop
        + " post_best=" + postBest + " post_cap=" + postCap
        + " d_cap=" + dCap + " d_best=" + dBest
        + " tasks_since=" + tasksSince);

    local passScan = this._p5ScanCandidatePool(this._projects, inCap);
    local nRailInBest = 0;
    local nNonRailInBest = 0;
    if (this._projects != null && ("best" in this._projects) && this._projects.best != null) {
      foreach (bp in this._projects.best) {
        if (bp != null && ("mode" in bp)) {
          if (bp.mode == "rail") nRailInBest++;
          else nNonRailInBest++;
        }
      }
    }
    local nRailBuilt = (passBuiltMode == "rail" ? nBuilt : 0);
    local passDateStr = AIDate.GetYear(curDate) + "-" + AIDate.GetMonth(curDate) + "-" + AIDate.GetDayOfMonth(curDate);
    local p5PassExtra = "";
    if (passScan.nRail > 0) {
      p5PassExtra = " best_rail_def=" + passScan.bestRailDeficit
          + " best_rail_cap=" + passScan.bestRailFinanceCap
          + " best_rail_prof=" + passScan.bestRailProfit
          + " best_rail_score=" + passScan.bestRailScore
          + " best_rail_cf_def=" + passScan.bestRailCfDeficit
          + " best_rail_cf_cap=" + passScan.bestRailCfFinanceCap
          + " best_rail_cf_rank=" + passScan.bestRailCfRank
          + " best_rail_kind=" + passScan.bestRailKind
          + " best_rail_rank=" + passScan.bestRailRank;
    } else {
      p5PassExtra = " best_rail_rank=-1";
    }
    OpexSchedIdleLog("P5_RAIL_PASS", "pass=" + passId + " date=" + passDateStr + " in_cap=" + inCap
        + " alts=" + passScan.nAlts + " rail_alts=" + passScan.nRail
        + " rail_aff=" + (passScan.bestRailDeficit == 0 && passScan.nRail > 0 ? 1 : 0)
        + " rail_in_best=" + nRailInBest + " nonrail_in_best=" + nNonRailInBest
        + " rail_built=" + nRailBuilt + " stop=" + passStop
        + p5PassExtra
        + " best_nonrail_mode=" + passScan.bestNonRailMode
        + " best_nonrail_score=" + passScan.bestNonRailScore
        + " best_nonrail_cap=" + passScan.bestNonRailCap);

    this._p2TasksSinceProjects = [];
    this._p2LastProjectsPostBest = postBest;
    this._p2LastProjectsPostCap = postCap;
  }

  if (this._p2PendingBuilds != null && this._p2PendingBuilds.len() > 0) {
    local curBestLen = (this._projects != null && ("best" in this._projects) && this._projects.best != null) ? this._projects.best.len() : 0;
    if (curBestLen > 0) {
      local curDate = AIDate.GetCurrentDate();
      local curTick = AIController.GetTick();
      local retReason = "other";
      if (taskName == "catalog") {
        if (this._p2CatalogPreReason != null && this._p2CatalogPreReason != "catalog_fresh") {
          retReason = this._p2CatalogPreReason;
        } else {
          retReason = "catalog_other";
        }
      } else if (taskName == "air_fleet") {
        retReason = "air_fleet";
      } else if (taskName == "projects") {
        retReason = "targeted_air";
      } else {
        retReason = taskName;
      }
      local curSt = (this._projects != null && ("stats" in this._projects)) ? this._projects.stats : null;
      local curCause = (curSt != null && ("emptyCause" in curSt) && curSt.emptyCause != null && curSt.emptyCause != "") ? curSt.emptyCause : "none";
      local retDateStr = AIDate.GetYear(curDate) + "-" + AIDate.GetMonth(curDate) + "-" + AIDate.GetDayOfMonth(curDate);
      foreach (item in this._p2PendingBuilds) {
        local pDays = curDate - item.buildDate;
        local pTicks = curTick - item.buildTick;
        OpexSchedIdleLog("P2_RESOLVE", "id=" + item.id + " days=" + pDays + " ticks=" + pTicks
            + " ret_reason=" + retReason + " ret_task=" + taskName + " ret_date=" + retDateStr
            + " funded=" + curBestLen + " cause=" + curCause);
        OpexSchedIdleLog("P5_WAIT_END", "id=" + item.id + " days=" + pDays + " ticks=" + pTicks
            + " dispatches=" + this._p5EpisodeDispatches
            + " unused_ops=" + this._p5EpisodeUnusedOps
            + " used_ops=" + this._p5EpisodeUsedOps
            + " ret_reason=" + retReason + " ret_task=" + taskName + " funded=" + curBestLen);
      }
      this._p2PendingBuilds = [];
      this._p5EpisodeActive = false;
    }
  }
}

/* C49 : une seule cause, pour le premier rang non bati de LA passe. La tresorerie est lue ici,
 * a la fin : la question est MARGINALE — « given what we just did, what blocked the next one? ».
 * Une construction qui a consomme du cash rend donc correctement le rang suivant bloque par
 * TRESORERIE. Un projet non tente ne peut pas etre teste sur la carte sans changer la decision
 * et consommer des opcodes : `site` n'est attribue qu'a un echec carte deja observe ; `decision`
 * absorbe ces echecs carte non observes. C'est une limite acceptee, pas une omission. */
function OpexAI::_recordC49ScarcityPass(best, builtRanks, attemptedRanks, passDiscards)
{
  if (!C49_SCARCITY_LEDGER || this._c49ScarcityLedger == null) return;
  this._c49ScarcityLedger.passes++;
  if (best == null || best.len() == 0) {
    this._c49ScarcityLedger.none++;
    return;
  }

  local targetRank = -1;
  for (local i = 0; i < best.len(); i++) {
    if (!(i in builtRanks)) {
      targetRank = i;
      break;
    }
  }
  if (targetRank < 0) {
    this._c49ScarcityLedger.none++;
    return;
  }

  local project = best[targetRank];
  if (project == null) {
    this._c49ScarcityLedger.none++;
    return;
  }
  local available = OpexAvailableCapital();
  if (project.capital > available) {
    this._c49ScarcityLedger.cash++;
    return;
  }

  local vehicleType = OpexC49VehicleType(project.mode);
  local vehicleMode = project.mode == "fleet" ? "air" : project.mode;
  local setting = OpexTensionVehicleSetting(vehicleMode);
  if (vehicleType >= 0 && setting != null && AIGameSettings.IsValid(setting)) {
    local planned = OpexTensionProjectVehicleCount(project);
    local cap = AIGameSettings.GetValue(setting);
    if (AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, vehicleType) + planned > cap) {
      this._c49ScarcityLedger.vehicles++;
      return;
    }
  }

  if (OpexC49IsMapFailure(passDiscards, targetRank)) {
    this._c49ScarcityLedger.site++;
    return;
  }
  if (targetRank in attemptedRanks) this._c49ScarcityLedger.decision_attempted++;
  else this._c49ScarcityLedger.decision_unattempted++;
}
/* La tache report publie au premier passage de l'annee suivante : year=1971 decrit donc 1970,
 * et la derniere annee de partie n'est jamais publiee (~82 % de couverture sur six ans). */
function OpexAI::_logC49ScarcityLedger(year)
{
  if (!C49_SCARCITY_LEDGER || this._c49ScarcityLedger == null) return;
  local entry = this._c49ScarcityLedger;
  local regime = this._c49ScarcityRegime;
  local best = entry.cash;
  local decision = entry.decision_attempted + entry.decision_unattempted;
  foreach (resource in ["vehicles", "site"]) {
    if (entry[resource] > best) best = entry[resource];
  }
  if (decision > best) best = decision;
  local leaders = 0;
  foreach (resource in ["cash", "vehicles", "site"]) {
    if (entry[resource] == best) leaders++;
  }
  if (decision == best) leaders++;
  if (leaders == 1) {
    foreach (resource in ["cash", "vehicles", "site"]) {
      if (entry[resource] == best) {
        regime = resource;
        break;
      }
    }
    if (decision == best) regime = "decision";
  }
  /* Egalite : ne pas remplacer le regime precedent, hysteresis sans constante. */
  this._c49ScarcityRegime = regime;
  OpexC49ScarcityLog("phase=annual year=" + year + " passes=" + entry.passes
      + " cash=" + entry.cash + " vehicles=" + entry.vehicles + " site=" + entry.site
      + " decision_attempted=" + entry.decision_attempted
      + " decision_unattempted=" + entry.decision_unattempted
      + " none=" + entry.none + " regime=" + regime);
  this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
      decision_attempted = 0, decision_unattempted = 0, none = 0,
      stop_k_pass = 0, stop_cash = 0, stop_rail_search = 0, stop_list_end = 0, stop_other = 0 };
}
/* C50 : suivi mensuel de la tresorerie. 12 lignes par an, leger et sans allocation inutile. */
function OpexAI::_checkC50MonthlyTreasury(year)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local c50Date = AIDate.GetCurrentDate();
  local c50Ym = AIDate.GetYear(c50Date) * 12 + AIDate.GetMonth(c50Date);
  if (this._c50LastTreasuryMonth == c50Ym) return;
  this._c50LastTreasuryMonth = c50Ym;

  local bank = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local loan = AICompany.GetLoanAmount();
  local available = OpexAvailableCapital();
  OpexC50ChronologyLog("phase=treasury_monthly year=" + AIDate.GetYear(c50Date) + " month=" + AIDate.GetMonth(c50Date)
      + " cash=" + bank + " loan=" + loan + " available=" + available);
}
/* C50 : synthese annuelle de tresorerie au tour de report. */
function OpexAI::_logC50AnnualReport(year)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local bank = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local loan = AICompany.GetLoanAmount();
  local maxLoan = AICompany.GetMaxLoanAmount();
  local available = OpexAvailableCapital();
  /* M1 : GetCompanyValue a disparu de l'API NoAI. Le canal annuel doit publier
   * la valeur observee du trimestre courant, pas un zero sentinelle. */
  local val = AICompany.GetQuarterlyCompanyValue(
      AICompany.COMPANY_SELF, AICompany.CURRENT_QUARTER);
  OpexC50ChronologyLog("phase=treasury_annual year=" + year + " cash=" + bank
      + " loan=" + loan + " max_loan=" + maxLoan + " available=" + available
      + " company_value=" + val + " lines=" + this._lines.len());
  this._c50RefuseCache = {};
  C50_REFUSE_CACHE.clear();

  if (C50_NON_EXPANSION_LEDGER != null) {
    // --- AIR DIAGNOSTIC ---
    local airLines = 0;
    local airPlanes = 0;
    local airCapPhys = 0;
    local airLinesAtCap = 0;
    foreach (line in this._lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      airLines++;
      local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
      airPlanes += have;
      local isSmall = (AIAirport.IsAirportTile(line.stationA) && AIAirport.GetAirportType(line.stationA) == AIAirport.AT_SMALL) ||
                      (AIAirport.IsAirportTile(line.stationB) && AIAirport.GetAirportType(line.stationB) == AIAirport.AT_SMALL);
      local physCap = isSmall ? 4 : AIR_MAX_PLANES_PER_ROUTE;
      if (AIR_CADENCE_CAP) physCap = OpexAirCadenceCap(line, this._catalog, this._lines);
      airCapPhys += physCap;
      if (have >= physCap) airLinesAtCap++;
    }

    local la = C50_NON_EXPANSION_LEDGER.air;
    OpexC50ChronologyLog("phase=c50b_non_expansion mode=air year=" + year
        + " lines=" + airLines + " planes_total=" + airPlanes
        + " cap_physical=" + airCapPhys
        + " lines_at_cap=" + airLinesAtCap + " want_sum=" + la.want_sum
        + " ref_Y=" + la.ref_Y + " ref_C=" + la.ref_C
        + " ref_L=" + la.ref_L + " ref_M=" + la.ref_M + " ref_W=" + la.ref_W
        + " ref_D=" + la.ref_D + " ref_V=" + la.ref_V + " ref_S=" + la.ref_S
        + " ref_X=" + la.ref_X + " ref_R=" + la.ref_R);

    // --- RAIL DIAGNOSTIC ---
    local railLines = 0;
    local railTrains = 0;
    local rail1Train = 0;
    local rail2Trains = 0;
    local railSingle = 0;
    local railDouble = 0;
    local railProfitable = 0;
    local railBacklogMet = 0;
    foreach (line in this._lines) {
      if (!("mode" in line) || line.mode != "rail") continue;
      railLines++;
      local trains = ("trains" in line) ? line.trains : (("vehicles" in line) ? line.vehicles.len() : 0);
      railTrains += trains;
      if (trains >= 2) rail2Trains++;
      else rail1Train++;
      if (("doubleTrack" in line) && line.doubleTrack == 1) railDouble++;
      else railSingle++;
      if (("lastProfit" in line) && line.lastProfit > 0) railProfitable++;

      if (line.cargo in this._catalog.wagonByCargo) {
        local wagon = this._catalog.wagonByCargo[line.cargo];
        local wA = ("lastWaitingA" in line) ? line.lastWaitingA : 0;
        local wB = ("lastWaitingB" in line) ? line.lastWaitingB : 0;
        local waiting = (("kind" in line) && line.kind == "freight") ? wA : (wA + wB);
        local thresh = (("kind" in line) && line.kind == "freight") ? (2 * wagon.capacity) : (4 * wagon.capacity);
        if (waiting >= thresh) railBacklogMet++;
      }
    }

    local lr = C50_NON_EXPANSION_LEDGER.rail;
    OpexC50ChronologyLog("phase=c50b_non_expansion mode=rail year=" + year
        + " lines=" + railLines + " trains_total=" + railTrains
        + " lines_1train=" + rail1Train + " lines_2trains=" + rail2Trains
        + " single_track=" + railSingle + " double_track=" + railDouble
        + " profitable=" + railProfitable + " backlog_met=" + railBacklogMet
        + " cash_refused=" + lr.cash_refused + " prep_failed=" + lr.prep_failed
        + " upgrade_failed=" + lr.upgrade_failed + " second_built=" + lr.second_built
        + " double_built=" + lr.double_built);

    // --- ROAD DIAGNOSTIC ---
    local roadLines = 0;
    local roadVehs = 0;
    foreach (line in this._lines) {
      if (!("mode" in line) || line.mode != "road") continue;
      roadLines++;
      local vehs = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
      roadVehs += vehs;
    }

    local lrd = C50_NON_EXPANSION_LEDGER.road;
    OpexC50ChronologyLog("phase=c50b_non_expansion mode=road year=" + year
        + " lines=" + roadLines + " vehs_total=" + roadVehs
        + " physical_cap_hit=" + lrd.physical_cap_hit + " congestion_hit=" + lrd.congestion_hit
        + " no_demand=" + lrd.no_demand + " loss_hit=" + lrd.loss_hit
        + " cash_refused=" + lrd.cash_refused + " other_refused=" + lrd.other_refused
        + " refill_built=" + lrd.refill_built);

    OpexC50ResetNonExpansionLedger();
  }
}
/* C50 : enregistrement deduplique des refus de tresorerie (au plus un log par mois calendaire et par candidat). */
function OpexAI::_logC50CashRefusal(mode, rank, cost, profit, roi, src, dst, need, money)
{
  OpexC50LogCashRefusal(mode, rank, cost, profit, roi, src, dst, need, money);
}
/* C55 : le report de debut d'annee publie l'annee ecoulee. La ligne summary est cumulative ;
 * la derniere ligne du log est donc aussi la synthese de fin de partie lisible sans jointure. */
function OpexAI::_logC55OriginRelaxLedger(year)
{
  if (!C55_ORIGIN_RELAX_PROBE || C55_ORIGIN_RELAX_LEDGER == null) return;
  local entry = C55_ORIGIN_RELAX_LEDGER;
  OpexC55OriginRelaxLog("phase=annual year=" + year + " candidates_seen=" + entry.candidates_seen
      + " rejected_total=" + entry.rejected_total + " both_served=" + entry.both_served
      + " one_served=" + entry.one_served + " one_served_pax=" + entry.one_served_pax
      + " one_served_freight=" + entry.one_served_freight
      + " duplicate_exact=" + entry.duplicate_exact);
  entry.total_candidates_seen += entry.candidates_seen;
  entry.total_rejected_total += entry.rejected_total;
  entry.total_both_served += entry.both_served;
  entry.total_one_served += entry.one_served;
  entry.total_one_served_pax += entry.one_served_pax;
  entry.total_one_served_freight += entry.one_served_freight;
  entry.total_duplicate_exact += entry.duplicate_exact;
  OpexC55OriginRelaxLog("phase=summary year=" + year + " candidates_seen=" + entry.total_candidates_seen
      + " rejected_total=" + entry.total_rejected_total + " both_served=" + entry.total_both_served
      + " one_served=" + entry.total_one_served + " one_served_pax=" + entry.total_one_served_pax
      + " one_served_freight=" + entry.total_one_served_freight
      + " duplicate_exact=" + entry.total_duplicate_exact);
  C55_ORIGIN_RELAX_LEDGER = {
    candidates_seen = 0, rejected_total = 0, both_served = 0, one_served = 0,
    one_served_pax = 0, one_served_freight = 0, duplicate_exact = 0,
    total_candidates_seen = entry.total_candidates_seen, total_rejected_total = entry.total_rejected_total,
    total_both_served = entry.total_both_served, total_one_served = entry.total_one_served,
    total_one_served_pax = entry.total_one_served_pax,
    total_one_served_freight = entry.total_one_served_freight,
    total_duplicate_exact = entry.total_duplicate_exact,
  };
}
/* C55 : sonde de tracabilite causale PAX routier. */
function OpexAI::_logC55PaxTraceLedger(year)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  local entry = C55_PAX_TRACE_LEDGER;
  entry.total_revalidated += entry.revalidated;
  entry.total_origin_blocked += entry.origin_blocked;

  OpexC55PaxTraceLog("C55_PAX_TRACE", "phase=annual year=" + year
      + " revalidated=" + entry.revalidated
      + " origin_blocked=" + entry.origin_blocked);

  OpexC55PaxTraceLog("C55_PAX_TRACE", "phase=summary year=" + year
      + " revalidated=" + entry.total_revalidated
      + " origin_blocked=" + entry.total_origin_blocked);

  C55_PAX_TRACE_LEDGER = {
    revalidated = 0, origin_blocked = 0,
    total_revalidated = entry.total_revalidated,
    total_origin_blocked = entry.total_origin_blocked,
  };
}
/* C60 : Le rapport annuel publie le bilan d'exposition aux notes municipales. */
function OpexAI::_logC60TownRatingLedger(year)
{
  if (!C60_TOWN_RATING_PROBE || C60_TOWN_RATING_LEDGER == null) return;
  local entry = C60_TOWN_RATING_LEDGER;
  OpexDecide("C60_TOWN_RATING_SUMMARY", "year=" + year
      + " checks=" + entry.checks
      + " none=" + entry.none
      + " ok=" + entry.ok
      + " very_poor=" + entry.very_poor
      + " appalling=" + entry.appalling
      + " road_checks=" + entry.by_mode.road.checks
      + " road_refused=" + entry.by_mode.road.refused
      + " rail_checks=" + entry.by_mode.rail.checks
      + " rail_refused=" + entry.by_mode.rail.refused
      + " air_checks=" + entry.by_mode.air.checks
      + " air_refused=" + entry.by_mode.air.refused);
}
/* C52 : le report de debut d'annee publie l'annee ecoulee et conserve un resume cumulatif. */
function OpexAI::_logC52AutoreplaceLedger(year)
{
  if (!C52_AUTOREPLACE_LOG || C52_AUTOREPLACE_LEDGER == null) return;
  local entry = C52_AUTOREPLACE_LEDGER;
  OpexC52AutoreplaceLog("phase=annual year=" + year + " events=" + entry.events
      + " remap_line_vehicles=" + entry.remap_line_vehicles
      + " remap_line_vehicle=" + entry.remap_line_vehicle
      + " remap_scrap_vehicles=" + entry.remap_scrap_vehicles
      + " untracked=" + entry.untracked
      + " rail=" + entry.rail + " road=" + entry.road + " air=" + entry.air
      + " water=" + entry.water + " unknown=" + entry.unknown
      + " line_rail=" + entry.line_rail + " line_road=" + entry.line_road
      + " line_air=" + entry.line_air + " line_water=" + entry.line_water);
  entry.total_events += entry.events;
  entry.total_remap_line_vehicles += entry.remap_line_vehicles;
  entry.total_remap_line_vehicle += entry.remap_line_vehicle;
  entry.total_remap_scrap_vehicles += entry.remap_scrap_vehicles;
  entry.total_untracked += entry.untracked;
  entry.total_rail += entry.rail;
  entry.total_road += entry.road;
  entry.total_air += entry.air;
  entry.total_water += entry.water;
  entry.total_unknown += entry.unknown;
  OpexC52AutoreplaceLog("phase=summary year=" + year + " events=" + entry.total_events
      + " remap_line_vehicles=" + entry.total_remap_line_vehicles
      + " remap_line_vehicle=" + entry.total_remap_line_vehicle
      + " remap_scrap_vehicles=" + entry.total_remap_scrap_vehicles
      + " untracked=" + entry.total_untracked + " rail=" + entry.total_rail
      + " road=" + entry.total_road + " air=" + entry.total_air
      + " water=" + entry.total_water + " unknown=" + entry.total_unknown);
  C52_AUTOREPLACE_LEDGER = {
    events = 0, remap_line_vehicles = 0, remap_line_vehicle = 0, remap_scrap_vehicles = 0,
    untracked = 0, rail = 0, road = 0, air = 0, water = 0, unknown = 0,
    line_rail = 0, line_road = 0, line_air = 0, line_water = 0,
    total_events = entry.total_events, total_remap_line_vehicles = entry.total_remap_line_vehicles,
    total_remap_line_vehicle = entry.total_remap_line_vehicle,
    total_remap_scrap_vehicles = entry.total_remap_scrap_vehicles,
    total_untracked = entry.total_untracked,
    total_rail = entry.total_rail, total_road = entry.total_road, total_air = entry.total_air,
    total_water = entry.total_water, total_unknown = entry.total_unknown,
  };
}
function OpexC52EventExposureFields(fields, values)
{
  local text = "";
  foreach (field in fields) text += " " + field + "=" + values[field];
  return text;
}
/* C52 : le report de debut d'annee publie la fenetre ecoulee, puis conserve son cumul. */
function OpexAI::_logC52EventExposureLedger(year)
{
  if (!C52_EVENT_EXPOSURE_PROBE || C52_EVENT_EXPOSURE_LEDGER == null) return;
  local entry = C52_EVENT_EXPOSURE_LEDGER;
  entry.vehicle_unprofitable_distinct = entry.unprofitable_vehicles.len();
  OpexC52EventExposureLog("phase=annual year=" + year
                          + OpexC52EventExposureFields(entry.fields, entry));
  foreach (field in entry.fields) entry.totals[field] += entry[field];
  OpexC52EventExposureLog("phase=summary year=" + year
                          + OpexC52EventExposureFields(entry.fields, entry.totals));
  C52_EVENT_EXPOSURE_LEDGER = {
    fields = entry.fields, totals = entry.totals, unprofitable_vehicles = {},
    vehicle_crashed = 0, crashed_train = 0, crashed_other = 0, vehicle_waiting_in_depot = 0,
    industry_open = 0, industry_close = 0, town_founded = 0, engine_available = 0,
    vehicle_lost = 0, subsidy_offer = 0, subsidy_offer_expired = 0, subsidy_awarded = 0,
    subsidy_expired = 0, vehicle_autoreplaced = 0, vehicle_unprofitable = 0,
    vehicle_unprofitable_distinct = 0, aircraft_dest_too_far = 0, station_first_vehicle = 0,
    road_reconstruction = 0, engine_preview = 0, exclusive_transport_rights = 0, other = 0,
  };
}
/* La tache "report" publie au premier passage de l'annee suivante : year=1971 decrit donc
 * l'annee de jeu 1970, et la derniere annee de la partie n'est jamais publiee. Tous les appels
 * API couteux sont apres ce garde C54, afin que le defaut false n'atteigne aucune API ajoutee. */
function OpexAI::_logC54VehicleOrders(year)
{
  if (!C54_VEHICLE_ORDERS_PROBE) return;
  local vehicles = AIVehicleList();
  foreach (vehicle, _ in vehicles) {
    local vehicleType = AIVehicle.GetVehicleType(vehicle);
    local mode = vehicleType == AIVehicle.VT_RAIL ? "rail"
        : vehicleType == AIVehicle.VT_ROAD ? "road"
        : vehicleType == AIVehicle.VT_AIR ? "air"
        : vehicleType == AIVehicle.VT_WATER ? "water" : "invalid";
    local orders = AIOrder.GetOrderCount(vehicle);
    local destinations = {};
    for (local position = 0; position < orders; position++) {
      /* IsGotoStationOrder exclut depot, waypoint et conditionnel avant GetOrderDestination. */
      if (!AIOrder.IsGotoStationOrder(vehicle, position)) continue;
      local destination = AIOrder.GetOrderDestination(vehicle, position);
      destinations.rawset(destination, true);
    }
    local line = OpexC41PersistedLineForVehicle(this._lines, vehicle);
    local lineId = line != null && ("lineId" in line) ? line.lineId : -1;
    /* GetProfit* est en livres reelles via API, contrairement a VEHS (~256 x livres). */
    OpexC54VehicleOrdersLog("phase=vehicle year=" + year + " vid=" + vehicle
        + " mode=" + mode + " engine=" + AIVehicle.GetEngineType(vehicle)
        + " age=" + AIVehicle.GetAge(vehicle) + " max_age=" + AIVehicle.GetMaxAge(vehicle)
        + " orders=" + orders + " distinct_dest=" + destinations.len()
        + " profit_last=" + AIVehicle.GetProfitLastYear(vehicle)
        + " profit_this=" + AIVehicle.GetProfitThisYear(vehicle)
        + " in_depot=" + (AIVehicle.IsStoppedInDepot(vehicle) ? 1 : 0)
        + " line=" + lineId);
  }
}
/* C69 etape 1 : enregistrement et publication a chaque passe qui construit */
function OpexAI::_recordC69BuildingPass(year, projects, builtProjects)
{
  if (!C69_TRACK_BUILDS) return;
  if (C69_BUILD_DATES == null) C69_BUILD_DATES = [];
  if (C69_PENDING_FOLLOWUPS == null) C69_PENDING_FOLLOWUPS = [];

  local now = AIDate.GetCurrentDate();
  if (builtProjects != null) {
    foreach (p in builtProjects) {
      C69_BUILD_DATES.append(now);
    }
  }
  if (!C69_BOTTLENECK_PROBE) return;

  local builtKeys = {};
  if (builtProjects != null) {
    foreach (p in builtProjects) {
      builtKeys[OpexC69AttemptKey(p)] <- true;
    }
  }

  /* Evaluer les suivis C3 en attente des passes precedentes */
  local activeFollowups = [];
  foreach (item in C69_PENDING_FOLLOWUPS) {
    item.passesWaited++;
    if (item.c69Key in builtKeys) {
      item.builtNext = 1;
      item.resolved = true;
      OpexC69Log("phase=c3_check pass=" + item.passId + " built_next=1 passes_waited=" + item.passesWaited + " target=" + item.c69Key);
    } else if (item.passesWaited >= item.maxPasses) {
      item.builtNext = 0;
      item.resolved = true;
      OpexC69Log("phase=c3_check pass=" + item.passId + " built_next=0 passes_waited=" + item.passesWaited + " target=" + item.c69Key);
    } else {
      activeFollowups.append(item);
    }
  }
  C69_PENDING_FOLLOWUPS = activeFollowups;

  /* Evaluer et journaliser la passe courante */
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) {
    return;
  }

  local actualTop = projects.best[0];
  local c69Top = (("c69Best" in projects) && projects.c69Best != null && projects.c69Best.len() > 0)
      ? projects.c69Best[0] : actualTop;

  local c69RankInActual = -1;
  local c69Key = OpexC69AttemptKey(c69Top);
  for (local r = 0; r < projects.best.len(); r++) {
    if (OpexC69AttemptKey(projects.best[r]) == c69Key) {
      c69RankInActual = r;
      break;
    }
  }

  local kData = (("c69KDecData" in projects) && projects.c69KDecData != null)
      ? projects.c69KDecData : OpexC69ComputeKDec();
  local fVeh = OpexC69VehicleProfitLastYear();

  C69_BUILD_PASS_COUNT++;
  local passId = C69_BUILD_PASS_COUNT;
  local actualCap = OpexProjectFinanceCapital(actualTop);
  local c69Cap = OpexProjectFinanceCapital(c69Top);
  local diff = (c69RankInActual != 0) ? 1 : 0;

  OpexC69Log("phase=build pass=" + passId + " year=" + year
      + " F=" + kData.F + " F_veh=" + fVeh + " tau=" + kData.tau + " K_dec=" + kData.K_dec
      + " actual_mode=" + actualTop.mode + " actual_P=" + actualTop.profitAnnual
      + " actual_C=" + actualCap
      + " c69_mode=" + c69Top.mode + " c69_P=" + c69Top.profitAnnual
      + " c69_C=" + c69Cap
      + " c69_rank_in_actual=" + c69RankInActual
      + " diff=" + diff);

  if (diff == 1) {
    if (c69Key in builtKeys) {
      OpexC69Log("phase=c3_check pass=" + passId + " built_next=1 passes_waited=0 target=" + c69Key);
    } else {
      C69_PENDING_FOLLOWUPS.append({
        passId = passId,
        c69Key = c69Key,
        passesWaited = 0,
        maxPasses = 2,
        resolved = false,
        builtNext = 0
      });
    }
  }
}
