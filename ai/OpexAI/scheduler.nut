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
    return this._runNextTask();
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
  local ran = this._runNextTask();
  local ops = OpexOpsMeasureEnd(mark);
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
   * separement par la cle slice/noslice et on veut le nom de la VRAIE tache de file. ⚠️ Sous
   * loop_budget=0 (defaut), la boucle principale fait un Sleep(1) APRES cet appel mesure : ce
   * Sleep n'est donc jamais compte dans days/ticks. A 74 ticks/jour c'est negligeable devant les
   * 3,6 jours mesures (docs/05_cadence_projects_rail_search.md §4.3), mais le prochain lecteur
   * doit le savoir. */
  if (C39_PASS_CLOCK_LEDGER) {
    local passDays = AIDate.GetCurrentDate() - c39DateBefore;
    local passTicks = AIController.GetTick() - mark.tick;
    local hasSlice = this._c39PassClockSliceOps >= 0;
    local taskName = this._c41LastTaskName != null ? this._c41LastTaskName : "idle";
    local c39Key = taskName + "|" + (hasSlice ? "slice" : "noslice");
    this._recordC39PassClockLedger(c39Key, passDays, passTicks, ops,
        hasSlice ? this._c39PassClockSliceDays : 0,
        hasSlice ? this._c39PassClockSliceTicks : 0,
        hasSlice ? this._c39PassClockSliceOps : 0);
  }
  /* C41.13 : apres la tache historique, seules les couches encore sales sont admissibles au
   * delestage. Une meme tranche peut etre une opportunite pour plusieurs couches : le total par
   * couche n'est donc volontairement pas un budget global, mais une borne superieure par choix. */
  this._recordC41StaleOpportunity(ops < mark.left ? mark.left - ops : 0);
  return ran;
}
/* File CONTINUE : le scan reprend apres la derniere tache choisie, meme si un A* a franchi le
 * changement d'annee. Le calendrier ne decide plus RIEN : quand le suffixe de la table est fini,
 * _taskCycle avance et le scan repart a zero. Chaque tache se reporte par dueCycle, donc aucun
 * item ne peut affamer ceux places apres lui et le dernier rend litteralement la main au premier. */
function OpexAI::_runNextTask()
{
  if (C41_SLACK_LEDGER || C41_MONTHLY_BUSY_LEDGER || C41_OPPORTUNITY_LEDGER || C41_ADMISSION_LEDGER || C39_PASS_CLOCK_LEDGER) this._c41LastTaskName = "idle";
  /* C41.46 : sentinelle -1 = aucune tranche A* mesuree cette passe. Remise a chaque passage,
   * lue par _runNextTaskWithSlackLedger juste apres le retour de cette fonction. */
  if (C41_RAIL_SLICE_LEDGER) this._c41RailSliceLastOps = -1;
  /* C39.6 : meme patron, scratch INDEPENDANT des champs _c41RailSliceLast* ci-dessus. */
  if (C39_PASS_CLOCK_LEDGER) {
    this._c39PassClockSliceDays = -1;
    this._c39PassClockSliceTicks = -1;
    this._c39PassClockSliceOps = -1;
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
  if (this._railExpansion != null) this._continueRailExpansion();
  /* A4 : avancer l'A* d'une tranche PUIS continuer la file, comme _railExpansion. Retourner
   * ici sans encherner les autres taches reconstituerait le gel (rien d'autre ne tourne tant
   * que la recherche n'a pas fini). */
  if (this._railSearch != null) {
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
      this._continueRailSearch();
      /* C39.6 reutilise ce MEME sliceOps que C41.46 -- pas de second begin()/end() pour la meme
       * tranche, les deux sondes partagent la seule mesure d'opcodes necessaire. */
      local sliceOps = OpexOpsMeasureEnd(sliceMark);
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
      this._continueRailSearch();
    }
  }
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  local task = null;
  local taskIndex = -1;
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

  if (task.name == "catalog") return this._dispatchCatalog(task, year);
  if (task.name == "c41_water") return this._dispatchC41Water(task, year);
  if (task.name == "c41_road") return this._dispatchC41Road(task, year);
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
  if (task.name == "report") return this._dispatchReport(task, year);
  if (task.name == "scrap") return this._dispatchScrap(task, year);
  if (task.name == "air") return this._dispatchAir(task, year);
  if (task.name == "air_fleet") return this._dispatchAirFleet(task, year);
  if (task.name == "feeders") return this._dispatchFeeders(task, year);
  if (task.name == "projects") return this._dispatchProjects(task, year);
  if (task.name == "expand") return this._dispatchExpand(task, year);
  if (task.name == "refleet") return this._dispatchRefleet(task, year);
  if (task.name == "town_growth") return this._dispatchTownGrowth(task, year);
  if (task.name == "repay") return this._dispatchRepay(task, year);
  AILog.Error("Unknown scheduler task name: " + task.name);
  task.enabled = false;
  if (C56_TASK_TRACE) OpexC56TaskLog("TASK_EXIT", task.name, this._taskCycle);
  return false;
}
