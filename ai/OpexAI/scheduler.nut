/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* C41.11 : enveloppe strictement observatoire. `slack_ops_used` est borne au reliquat disponible
 * au debut du passage : un calcul qui franchit un tick ne transforme pas les ticks suivants en
 * slack retroactif. Les continuations rail precedant la selection sont rangees explicitement par
 * nature, afin de ne pas les attribuer abusivement a la tache choisie ensuite. Si les deux etats
 * coexistent, une categorie jointe conserve l'incertitude plutot que de fabriquer une attribution. */
function OpexAI::_runNextTaskWithSlackLedger()
{
  if ((!C41_SLACK_LEDGER && !C41_MONTHLY_BUSY_LEDGER && !C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER
       && !C41_RAIL_SLICE_LEDGER && !C39_PASS_CLOCK_LEDGER)
      || this._c41SlackLedger == null) {
    local res = this._runNextTask();
    this._railWorkerSteppedThisTick = false;
    return res;
  }
  if (C41_MONTHLY_BUSY_LEDGER) {
    local date = AIDate.GetCurrentDate();
    local ym = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
    if (this._c41MonthlyBusyMonth != ym) {
      if (this._c41MonthlyBusyMonth >= 0) this._logC41MonthlyBusyLedger();
      this._c41MonthlyBusyMonth = ym;
      this._c41MonthlyBusyLedger = {};
    }
  }
  local mark = OpexOpsMeasureBegin();
  /* C39.6 : date AVANT l'appel mesure, pour le delta jours de la passe entiere. mark.tick sert
   * aussi de tick de depart : pas de second AIController.GetTick(), c'est deja celui capture par
   * OpexOpsMeasureBegin() ci-dessus. */
  local c39DateBefore = C39_PASS_CLOCK_LEDGER ? AIDate.GetCurrentDate() : -1;
  local continuationCategory = null;
  if (this._railExpansion != null && this._railSearch != null) {
    continuationCategory = "rail_expansion+rail_search";
  } else if (this._railSearch != null) {
    continuationCategory = "rail_search";
  } else if (this._railExpansion != null) {
    continuationCategory = "rail_expansion";
  }
  if (V95_SCHED_IDLE_LEDGER) {
    this._schedIdlePreDispatch();
  }
  local ran = this._runNextTask();
  local ops = OpexOpsMeasureEnd(mark);
  if (this._railWorkerSteppedThisTick) {
    if (this._c41RailSliceLastOps >= 0) {
      ops += this._c41RailSliceLastOps;
    } else if (C39_PASS_CLOCK_LEDGER && this._c39PassClockSliceOps >= 0) {
      ops += this._c39PassClockSliceOps;
    }
  }
  local category = continuationCategory != null ? continuationCategory : this._c41LastTaskName;
  if (category == null) category = "idle";
  if (C41_SLACK_LEDGER) {
    local entry = (category in this._c41SlackLedger) ? this._c41SlackLedger[category]
        : { calls = 0, ran = 0, ops = 0, slackAvailable = 0, slackUsed = 0, slackLeft = 0 };
    entry.calls++;
    if (ran) entry.ran++;
    entry.ops += ops;
    entry.slackAvailable += mark.left;
    entry.slackUsed += ops < mark.left ? ops : mark.left;
    entry.slackLeft += ops < mark.left ? mark.left - ops : 0;
    this._c41SlackLedger.rawset(category, entry);
  }
  if (C41_MONTHLY_BUSY_LEDGER) {
    local entry = (category in this._c41MonthlyBusyLedger) ? this._c41MonthlyBusyLedger[category]
        : { calls = 0, ran = 0, ops = 0 };
    entry.calls++;
    if (ran) entry.ran++;
    entry.ops += ops;
    this._c41MonthlyBusyLedger.rawset(category, entry);
  }
  /* C41.46 : this._c41RailSliceLastOps a ete mesure INDEPENDAMMENT dans _runNextTask, pendant le
   * meme appel que `ops` ci-dessus (OpexOpsMeasureBegin/End ne partagent aucun etat -- imbrication
   * sure, voir budget.nut). Sentinelle -1 = aucune tranche A* cette passe. La difference donne les
   * opcodes de la tache de file jouee dans la MEME passe, jamais mesures separement jusqu'ici. */
  if (C41_RAIL_SLICE_LEDGER && this._c41RailSliceLastOps >= 0) {
    local taskOps = ops - this._c41RailSliceLastOps;
    if (taskOps < 0) taskOps = 0;
    this._recordC41RailSliceLedger(this._c41RailSliceLastOps, taskOps,
                                   this._c41RailSliceLastIterDelta, this._c41RailSliceLastDone);
  }
  /* C39.6 : this._c39PassClockSlice{Days,Ticks,Ops} ont ete mesures INDEPENDAMMENT dans
   * _runNextTask, pendant le meme appel que `ops`/`c39DateBefore` ci-dessus (meme garantie de
   * non-partage d'etat que C41.46). Sentinelle -1 sur _c39PassClockSliceOps = aucune tranche A*
   * cette passe -- la cle "|slice" contre "|noslice" porte cette information, les trois champs
   * slice_* valent alors 0. La cle est this._c41LastTaskName ("idle" si nul), PAS `category` :
   * `category` fusionne les continuations rail (C41.11), alors qu'ici la tranche est deja portee
   * separement par la cle slice/noslice et on veut le nom de la VRAIE tache de file. La boucle
   * principale fait un Sleep(1) APRES cet appel mesure : ce
   * Sleep n'est donc jamais compte dans days/ticks. A 74 ticks/jour c'est negligeable devant les
   * 3,6 jours mesures (docs/05_cadence_projects_rail_search.md §4.3), mais le prochain lecteur
   * doit le savoir. */
  if (C39_PASS_CLOCK_LEDGER) {
    local passDays = AIDate.GetCurrentDate() - c39DateBefore;
    local passTicks = AIController.GetTick() - mark.tick;
    if (this._railWorkerSteppedThisTick) {
      if (this._c39PassClockSliceTicks >= 0) passTicks += this._c39PassClockSliceTicks;
      if (this._c39PassClockSliceDays >= 0) passDays += this._c39PassClockSliceDays;
    }
    local hasSlice = this._c39PassClockSliceOps >= 0;
    local taskName = this._c41LastTaskName != null ? this._c41LastTaskName : "idle";
    local c39Key = taskName + "|" + (hasSlice ? "slice" : "noslice");
    this._recordC39PassClockLedger(c39Key, passDays, passTicks, ops,
        hasSlice ? this._c39PassClockSliceDays : 0,
        hasSlice ? this._c39PassClockSliceTicks : 0,
        hasSlice ? this._c39PassClockSliceOps : 0);
    if (V95_SCHED_IDLE_LEDGER) {
      local taskOps = ops;
      if (hasSlice && this._c41RailSliceLastOps >= 0) {
        taskOps = ops - this._c41RailSliceLastOps;
        if (taskOps < 0) taskOps = 0;
      }
      this._schedIdlePostDispatch(taskName, ran, taskOps, passDays, passTicks);
    }
  }
  /* C41.13 : apres la tache historique, seules les couches encore sales sont admissibles au
   * delestage. Une meme tranche peut etre une opportunite pour plusieurs couches : le total par
   * couche n'est donc volontairement pas un budget global, mais une borne superieure par choix. */
  this._recordC41StaleOpportunity(ops < mark.left ? mark.left - ops : 0);
  this._railWorkerSteppedThisTick = false;
  return ran;
}
/* P7 experimental, raccordement globals_pre/settings/info :
 * globals_pre : EXP_SCHEDULER_SKIP_NOT_DUE <- false;
 * settings : exp_scheduler_skip_not_due != 0 (reglage bool, quatre defauts 0).
 * Helpers libres : aucune declaration de methode/etat dans main, aucun nouvel etat Save/Load.
 * Liste blanche volontairement minimale, verifiee contre scheduler_tasks.nut.
 * catalog_fresh est EXCLU : avant sa garde, C121 met a jour son etat et le lot de production,
 * un rebuild C78 peut avancer/publier, et les sondes de capital ont des effets observables.
 * projects_null, air/expand disabled, town_growth et les workers ne sont pas des filtres P7. */
function OpexExpSchedulerSkipReason(owner, candidate, year)
{
  if (owner._projects == null) return null;
  if (candidate.name == "report" && owner._lastReportYear == year) return "report_same_year";
  if (candidate.name == "repay") {
    /* Meme cle que _dispatchRepay : annee du dispatch, mois lu au moment du predicat.
     * Aucun test de cash/dette : meme un essai sans remboursement consomme son mois. */
    local date = AIDate.GetCurrentDate();
    local ym = year * 12 + AIDate.GetMonth(date);
    if (owner._lastRepayMonth == ym) return "repay_same_month";
  }
  return null;
}

function OpexExpSchedulerSelectTask(owner, year)
{
  local count = owner._taskQueue.len();
  local index = owner._taskCursor;
  local startCursor = index;
  local startCycle = owner._taskCycle;
  local selected = -1;
  local scanned = 0;
  local reportSkips = 0;
  local repaySkips = 0;
  /* Au plus UN tour de la file, pas un tour de dispatchs ni une recursion.
   * Le suffixe est lu au cycle courant, le prefixe au suivant. A la borne, les entrees
   * du suffixe devenues dues attendent l'appel suivant : ne jamais les relire ici.
   * Cela peut rendre false une fois avant une echeance, mais ne peut affamer une entree. */
  for (local visited = 0; visited < count; visited++) {
    if (index >= count) {
      owner._taskCycle++;
      index = 0;
    }
    local candidate = owner._taskQueue[index];
    scanned++;
    if (candidate.enabled && candidate.dueCycle <= owner._taskCycle) {
      local reason = OpexExpSchedulerSkipReason(owner, candidate, year);
      if (reason == null) {
        selected = index;
        break;
      }
      /* Consommer exactement l'echeance du dispatch no-op, sans toucher son horloge
       * metier (_lastReportYear/_lastRepayMonth), enabled, ni les autres echeances. */
      owner._taskCursor = (index + 1) % count;
      candidate.dueCycle = owner._taskCycle + 1;
      if (C56_TASK_TRACE) OpexC56TaskLog("TASK_ENTER", candidate.name, owner._taskCycle);
      if (C50_CHRONOLOGY_PROBE) owner._checkC50MonthlyTreasury(year);
      if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", candidate.name, owner._taskCycle);
      if (reason == "report_same_year") reportSkips++;
      else repaySkips++;
    }
    index++;
  }
  if (index >= count) {
    owner._taskCycle++;
    index = 0;
  }
  owner._taskCursor = index;
  /* Une seule ligne agregee par scan avec skips, aucun scan de vehicules/villes/projets.
   * SCHED_IDLE conserve son peek historique (avant continuations) ; cette preuve P7
   * explicite les skips reels et la selection finale, sans modifier les mesures P5. */
  if ((V95_SCHED_IDLE_LEDGER || DECISION_LOG) && reportSkips + repaySkips > 0) {
    local fields = "report_same_year=" + reportSkips + " repay_same_month=" + repaySkips
        + " scanned=" + scanned + " limit=" + count + " cursor_from=" + startCursor
        + " cycle_from=" + startCycle + " cycle=" + owner._taskCycle
        + " next=" + (selected >= 0 ? owner._taskQueue[selected].name : "idle");
    if (V95_SCHED_IDLE_LEDGER) OpexSchedIdleLog("P7_SCHED_SKIP", fields);
    else OpexDecide("P7_SCHED_SKIP", fields);
  }
  return selected;
}

/* File CONTINUE : le scan reprend apres la derniere tache choisie, meme si un A* a franchi le
 * changement d'annee. Le calendrier ne decide plus RIEN : quand le suffixe de la table est fini,
 * _taskCycle avance et le scan repart a zero. Chaque tache se reporte par dueCycle, donc aucun
 * item ne peut affamer ceux places apres lui et le dernier rend litteralement la main au premier. */
function OpexAI::_runNextTask()
{
  if (C41_SLACK_LEDGER || C41_MONTHLY_BUSY_LEDGER || C41_OPPORTUNITY_LEDGER || C41_ADMISSION_LEDGER || C39_PASS_CLOCK_LEDGER) this._c41LastTaskName = "idle";
  if (!this._railWorkerSteppedThisTick) {
    /* C41.46 : sentinelle -1 = aucune tranche A* mesuree cette passe. Remise a chaque passage,
     * lue par _runNextTaskWithSlackLedger juste apres le retour de cette fonction. */
    if (C41_RAIL_SLICE_LEDGER) this._c41RailSliceLastOps = -1;
    /* C39.6 : meme patron, scratch INDEPENDANT des champs _c41RailSliceLast* ci-dessus. */
    if (C39_PASS_CLOCK_LEDGER) {
      this._c39PassClockSliceDays = -1;
      this._c39PassClockSliceTicks = -1;
      this._c39PassClockSliceOps = -1;
    }
  }
  if (DECISION_LOG) {
    _currentTaskName = null;
    _currentTaskLogged = false;
  }
  if (C55_PAX_TRACE_PROBE) {
    local now = AIDate.GetCurrentDate();
    local curY = AIDate.GetYear(now);
    local curM = AIDate.GetMonth(now);
    local curD = AIDate.GetDayOfMonth(now);
    if (this._c55PaxLastYear < 0) {
      this._c55PaxLastYear = curY;
    } else if (curY > this._c55PaxLastYear) {
      this._logC55PaxTraceLedger(this._c55PaxLastYear);
      this._c55PaxLastYear = curY;
      this._c55PaxLastFlushedYear = -1;
    } else if (curM == 12 && curD >= 28 && this._c55PaxLastFlushedYear != curY) {
      this._c55PaxLastFlushedYear = curY;
      this._logC55PaxTraceLedger(curY);
    }
  }
  if (C63_INVEST_PROBE && C63_INVEST_LEDGER != null) {
    OpexC63EnsureYear(AIDate.GetYear(AIDate.GetCurrentDate()));
  }
  if (this._taskQueue == null || this._taskQueue.len() == 0) return false;
  /* Sonder d'abord la transaction, puis CONTINUER la file dans le meme passage. Retourner ici
   * affamait de nouveau le scheduler pendant tout le trajet vers le depot (jusqu'a un an mesure),
   * alors que ce trajet ne consomme aucun opcode de l'IA. */
  if (C56_TASK_TRACE) this._v89TrackSearchDays(AIDate.GetCurrentDate());
  if (this._railExpansion != null && !this._railWorkerSteppedThisTick) this._continueRailExpansion();
  /* A4 : avancer l'A* d'une tranche PUIS continuer la file, comme _railExpansion. Retourner
   * ici sans encherner les autres taches reconstituerait le gel (rien d'autre ne tourne tant
   * que la recherche n'a pas fini).
   * C80 tranche 1 : sous c80_worker_rail=1, la tranche est exécutée par le travailleur dans
   * _runOrchestratorTick (étape c) avant la file de fond ; elle n'est pas refaite ici.
   * V89 : sous v89_rail_search_throughput=1, avance des tranches supplémentaires sur le
   * budget d'opcodes disponible du tick. */
  if (this._railSearch != null && !this._railWorkerSteppedThisTick
      && !(C121_AIR_FIRST_YEAR_RAIL_PREP && this._c121RailPrepHold)) {
    this._advanceRailSearchSliceWithLedgers();
    if (V89_RAIL_SEARCH_THROUGHPUT) {
      this._advanceRailSearchThroughput();
    }
  }
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  local task = null;
  local taskIndex = -1;
  if (EXP_SCHEDULER_SKIP_NOT_DUE) {
    taskIndex = OpexExpSchedulerSelectTask(this, year);
    if (taskIndex >= 0) task = this._taskQueue[taskIndex];
  } else {
    /* Chemin temoin conserve : meme scan suffixe puis file entiere au cycle suivant. */
    for (local index = this._taskCursor; index < this._taskQueue.len(); index++) {
      local candidate = this._taskQueue[index];
      if (candidate.enabled && candidate.dueCycle <= this._taskCycle) {
        task = candidate;
        taskIndex = index;
        break;
      }
    }
    if (task == null) {
      this._taskCycle++;
      this._taskCursor = 0;
      for (local index = 0; index < this._taskQueue.len(); index++) {
        local candidate = this._taskQueue[index];
        if (candidate.enabled && candidate.dueCycle <= this._taskCycle) {
          task = candidate;
          taskIndex = index;
          break;
        }
      }
    }
  }
  if (task == null) return false;
  this._taskCursor = (taskIndex + 1) % this._taskQueue.len();
  if (C41_SLACK_LEDGER || C41_MONTHLY_BUSY_LEDGER || C41_OPPORTUNITY_LEDGER || C41_ADMISSION_LEDGER || C39_PASS_CLOCK_LEDGER) this._c41LastTaskName = task.name;

  /* Defaut : exactement une execution par tour continu. Une tache inutile peut choisir plus loin. */
  task.dueCycle = this._taskCycle + 1;
  if (DECISION_LOG) {
    _currentTaskName = task.name;
    _currentTaskLogged = false;
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_ENTER", task.name, this._taskCycle);
  if (C50_CHRONOLOGY_PROBE) this._checkC50MonthlyTreasury(year);

  local spTask = null;
  local ranTask = false;
  if (task.name == "catalog") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.catalog") : null;
    ranTask = this._dispatchCatalog(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "c41_water") return false;
  if (this._projects == null) {
    /* `_taskCycle` (et non `+ 1`) laissait la tache due au cycle COURANT. Or le cycle n'avance que
     * lorsque le balayage depuis _taskCursor ne trouve plus rien de du : une tache qui reste
     * eternellement due empeche donc `_taskCycle` d'avancer, et `catalog` -- differe a
     * `_taskCycle + 1` -- ne tourne plus JAMAIS. L'IA tournerait alors a vide pour le reste de la
     * partie avec `_projects` null a jamais. Inatteignable aujourd'hui puisque OpexBuildProjects
     * ne rend jamais null, mais un seul `return` ajoute la-bas gelait l'IA (docs/taches.md
     * S0 sexies). */
    task.dueCycle = this._taskCycle + 1;
    if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
    return false;
  }
  if (task.name == "c41_rail_signals") return this._dispatchC41RailSignals(task, year);
  if (task.name == "c41_rail_junction") return this._dispatchC41RailJunction(task, year);
  if (task.name == "report") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.report") : null;
    ranTask = this._dispatchReport(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "scrap") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.scrap") : null;
    ranTask = this._dispatchScrap(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "air") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.air") : null;
    ranTask = this._dispatchAir(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "air_fleet") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.air_fleet") : null;
    ranTask = this._dispatchAirFleet(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "projects") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.projects") : null;
    ranTask = this._dispatchProjects(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "expand") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.expand") : null;
    ranTask = this._dispatchExpand(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "refleet") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.refleet") : null;
    ranTask = this._dispatchRefleet(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "town_growth") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.town_growth") : null;
    ranTask = this._dispatchTownGrowth(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  if (task.name == "repay") {
    spTask = PROBE_SPAN_TRACE ? OpexSpanBegin("task.repay") : null;
    ranTask = this._dispatchRepay(task, year);
    if (spTask != null) OpexSpanEnd(spTask);
    return ranTask;
  }
  AILog.Error("Unknown scheduler task name: " + task.name);
  task.enabled = false;
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return false;
}

/* C80 tranche 1 : avance d'une tranche A* avec les ledgers C41.46 et C39.6.
 * Partagé entre le travailleur "rail_search" (orchestrateur) et le chemin legacy. */
function OpexAI::_advanceRailSearchSliceWithLedgers()
{
  if (this._railSearch == null) return;
  local spanSlice = null;
  /* C41.46 : n'encadrer que les passes qui font REELLEMENT avancer l'A* -- phase == "search".
   * phase == "build" retourne immediatement pour kind == "primary" (le cout reel est ailleurs,
   * dans _consumeRailSearch via la tache "projects") ou execute _consumeRailUpgrade() pour
   * kind == "upgrade", qui n'est pas une tranche de recherche. Aucun des deux n'est comptabilise
   * dans ce ledger : le confondre fausserait "iterations cumulees" et "tranches non terminees". */
  if ((C41_RAIL_SLICE_LEDGER || C39_PASS_CLOCK_LEDGER) && this._railSearch.phase == "search") {
    local sliceState = this._railSearch;
    local spentBefore = sliceState.spent;
    /* C39.6 : date/tick AVANT l'appel, pour le delta de la SEULE tranche. sliceMark.tick sert
     * de tick de depart -- pas de second AIController.GetTick(). */
    local c39SliceDateBefore = C39_PASS_CLOCK_LEDGER ? AIDate.GetCurrentDate() : -1;
    local sliceMark = OpexOpsMeasureBegin();
    spanSlice = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    this._continueRailSearch();
    /* C39.6 reutilise ce MEME sliceOps que C41.46 -- pas de second begin()/end() pour la meme
     * tranche, les deux sondes partagent la seule mesure d'opcodes necessaire. */
    local sliceOps = OpexOpsMeasureEnd(sliceMark);
    if (sliceOps > 0) {
      local nextEst = sliceOps + 500;
      if (nextEst < 1500) nextEst = 1500;
      this._v89EstimatedSliceOps = nextEst;
    }
    if (C41_RAIL_SLICE_LEDGER) {
      this._c41RailSliceLastOps = sliceOps;
      this._c41RailSliceLastIterDelta = sliceState.spent - spentBefore;
      /* sliceState reste la MEME table (mutee en place par _continueRailSearch) : phase !=
       * "search" signifie que cette tranche a atteint slice.done et fait basculer la recherche
       * en "build". */
      this._c41RailSliceLastDone = (sliceState.phase != "search");
    }
    if (C39_PASS_CLOCK_LEDGER) {
      this._c39PassClockSliceDays = AIDate.GetCurrentDate() - c39SliceDateBefore;
      this._c39PassClockSliceTicks = AIController.GetTick() - sliceMark.tick;
      this._c39PassClockSliceOps = sliceOps;
    }
  } else {
    local sliceMark = (V89_RAIL_SEARCH_THROUGHPUT && this._railSearch.phase == "search")
        ? OpexOpsMeasureBegin() : null;
    if (this._railSearch.phase == "search") spanSlice = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    this._continueRailSearch();
    if (sliceMark != null) {
      local sliceOps = OpexOpsMeasureEnd(sliceMark);
      if (sliceOps > 0) {
        local nextEst = sliceOps + 500;
        if (nextEst < 1500) nextEst = 1500;
        this._v89EstimatedSliceOps = nextEst;
      }
    }
  }
  if (spanSlice != null) OpexSpanAgg("astar.slice", spanSlice);
  if (PROBE_SPAN_TRACE && this._railSearch != null && this._railSearch.phase == "build") {
    OpexSpanEvent("astar_ready", "kind=" + this._railSearch.kind);
  }
}

/* V89 : suivi passif des jours de jeu passés avec une recherche en phase "search". */
function OpexAI::_v89TrackSearchDays(now)
{
  if (this._v89LastDay < 0) {
    this._v89LastDay = now;
    return;
  }
  if (now > this._v89LastDay) {
    local deltaDays = now - this._v89LastDay;
    if (this._railSearch != null && this._railSearch.phase == "search") {
      this._v89SearchDaysThisYear += deltaDays;
    }
    this._v89LastDay = now;
  }
}

/* V89 : journalise le bilan annuel A* rail sous probe_events (C56_TASK_TRACE). */
function OpexAI::_logC89AnnualRail(year)
{
  if (!C56_TASK_TRACE) return;
  local activeSearch = (this._railSearch != null && this._railSearch.phase == "search") ? 1 : 0;
  OpexC56TaskLog("RAIL_ANNUAL", "rail", this._taskCycle,
                 "year=" + year + " year_iters=" + this._v89YearIters
                 + " year_slices=" + this._v89YearSlices
                 + " search_days=" + this._v89SearchDaysThisYear
                 + " active_search=" + activeSearch + " est_slice_ops=" + this._v89EstimatedSliceOps);
  this._v89YearIters = 0;
  this._v89YearSlices = 0;
  this._v89SearchDaysThisYear = 0;
}

/* V89 : débit de recherche A* rail opportuniste.
 * Avance des tranches supplémentaires tant que GetOpsTillSuspend() dépasse le coût estimé
 * d'une tranche, chacune avec sa propre échéance locale via RAIL_MICRO_DEADLINE. */
function OpexAI::_advanceRailSearchThroughput(maxSlices = -1)
{
  if (!V89_RAIL_SEARCH_THROUGHPUT) return 0;
  if (this._railSearch == null || this._railSearch.phase != "search") return 0;
  /* Hold pose seulement par la preparation C121 quand l'AIR est finançable.
   * Sans recherche en cours, la ligne precedente a deja rendu la main. */
  if (C121_AIR_FIRST_YEAR_RAIL_PREP && this._c121RailPrepHold) return 0;
  local spThru = PROBE_SPAN_TRACE ? OpexSpanBegin("astar.throughput") : null;

  local slicesRan = 0;
  local minThreshold = (this._v89EstimatedSliceOps > 1500) ? this._v89EstimatedSliceOps : 1500;
  if (V88_STEP2_RAIL_PRIO && minThreshold > 2500 && ("candidate" in this._railSearch) && this._railSearch.candidate != null
      && ((("isChainStep1" in this._railSearch.candidate) && this._railSearch.candidate.isChainStep1)
          || (("isChainStep2" in this._railSearch.candidate) && this._railSearch.candidate.isChainStep2))) {
    minThreshold = 2500;
  }
  while (this._railSearch != null && this._railSearch.phase == "search"
         && AIController.GetOpsTillSuspend() >= minThreshold) {
    if (maxSlices > 0 && slicesRan >= maxSlices) break;
    this._advanceRailSearchSliceWithLedgers();
    slicesRan++;
    minThreshold = (this._v89EstimatedSliceOps > 1500) ? this._v89EstimatedSliceOps : 1500;
    /* daycap peut avoir libere le creneau dans la tranche : ne pas lire une table nulle. */
    if (V88_STEP2_RAIL_PRIO && minThreshold > 2500 && this._railSearch != null && ("candidate" in this._railSearch) && this._railSearch.candidate != null
        && ((("isChainStep1" in this._railSearch.candidate) && this._railSearch.candidate.isChainStep1)
            || (("isChainStep2" in this._railSearch.candidate) && this._railSearch.candidate.isChainStep2))) {
      minThreshold = 2500;
    }
  }
  if (spThru != null) OpexSpanEnd(spThru);
  return slicesRan;
}
