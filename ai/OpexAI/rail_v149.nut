/* V149 : debloquer le rail (decision utilisateur du 13/10).
 *
 * Le reglage maitre v149_rail_pipeline est a 0 par defaut. A 1, settings.nut arme la gate et
 * le worker C80 (un projet rail n'est eligible qu'avec un trace pret dans _railReadyStock) et ce
 * fichier ajoute :
 *  - un stock de V149_STOCK_SIZE traces (OpexRailStockCapacity, 1 hors V149) ;
 *  - un worker qui saute les candidats refuses par _tooClose ou trop pres d'un trace deja stocke ;
 *  - une revalidation periodique des traces stockes (tuiles seulement, ni caisse ni vehicule) ;
 *  - une file de reparation (nouvel A* sur la carte vivante, 2 au plus par paire, puis retrait
 *    365 jours), alimentee par la revalidation et par les echecs de pose ;
 *  - une passe projects avancee quand un trace financable est depose ;
 *  - la retenue des traces pendant l'annee AIR (jamais de rail devant l'aerien en 1970).
 * Le stock, la file et les compteurs sont transitoires (non sauves), comme _railReadyStock.
 */

/* Partage des opcodes avec le catalogue AIR (diag 5x3 du 13/10 : sans ce partage, une recherche
 * du stock presque permanente bloquait la poursuite du catalogue AIR incremental, qui exige
 * _railSearch == null, et videait le reliquat de chaque tick : 0 jeu de plans AIR en 1971,
 * chantiers AIR divises par 2 a 8, profit -444 k/an sur 5/5 graines). */
function OpexV149AirCatalogBusy(ai)
{
  if (ai._taskQueue == null) return false;
  foreach (t in ai._taskQueue) {
    if (t.name == "catalog") return ("c78AirRebuild" in t) && t.c78AirRebuild != null;
  }
  return false;
}

/* La recherche en cours est une recherche du stock (neuve, reparation ou preparation C121),
 * menee par le worker rail_stock ou en attente de lui. */
function OpexV149CatalogMayPassRail(owner)
{
  if (owner._activeWorker != null && owner._activeWorker.kind != "rail_stock") return false;
  local search = owner._railSearch;
  return search == null || (("isStockSearch" in search) && search.isStockSearch);
}

/* Meme admission que OpexC121CatalogCanContinue, sauf qu'une recherche du stock ne bloque pas. */
function OpexV149CatalogCanContinue(owner, continuationTick)
{
  if (!C121_CATALOG_INCREMENTAL || owner._railExpansion != null) return false;
  if ((owner._activeWorker != null || owner._railSearch != null)
      && !OpexV149CatalogMayPassRail(owner)) return false;
  return AIController.GetTick() == continuationTick
      && AIController.GetOpsTillSuspend() > 2000;
}

/* Poursuite du catalogue AIR dans le meme tick, apres la boucle de main.nut (meme corps). */
function OpexAI::_v149ContinueCatalog(continuationTick)
{
  local catalogPending = true;
  while (catalogPending && OpexV149CatalogCanContinue(this, continuationTick)) {
    catalogPending = false;
    foreach (queuedTask in this._taskQueue) {
      if (queuedTask.name == "catalog" && ("c78AirRebuild" in queuedTask)
          && queuedTask.c78AirRebuild != null) {
        catalogPending = true;
        if (V147_AIR_CATALOG_TASKS) {
          local phaseTask = OpexV147PhaseTask(this);
          if (phaseTask != null) this._dispatchAirCatalogPhase(phaseTask, AIDate.GetYear(AIDate.GetCurrentDate()));
        } else this._dispatchCatalog(queuedTask, AIDate.GetYear(AIDate.GetCurrentDate()));
        break;
      }
    }
    if (catalogPending) this._runOrchestratorTick();
  }
}

/* Capacite unique du stock de traces prets : remplace les anciens tests `len() >= 1`. */
function OpexRailStockCapacity()
{
  return V149_RAIL_PIPELINE ? V149_STOCK_SIZE : 1;
}

/* Annee AIR : meme test que les traces de preparation C121 dans _tryBuildRailProject.
 * V149_FIRST_YEAR est la copie globale de l'annee de _generationStageMonth, pour les
 * fonctions de selection qui n'ont pas l'instance. */
function OpexV149AirYear()
{
  if (C121_CATALOG_FIRST_YEAR_ACTIVE) return true;
  return V149_FIRST_YEAR >= 0 && AIDate.GetYear(AIDate.GetCurrentDate()) == V149_FIRST_YEAR;
}

function OpexAI::_v149AirYearActive()
{
  if (V149_FIRST_YEAR < 0 && this._generationStageMonth >= 0)
    V149_FIRST_YEAR = (this._generationStageMonth - 1) / 12;
  return OpexV149AirYear();
}

/* Journal sous DECISION_LOG seulement : les chaines ne sont construites qu'ici. */
function OpexV149Log(ai, action, candidate, reason)
{
  if (!DECISION_LOG) return;
  local where = "";
  if (candidate != null) {
    where = " src=" + candidate.src + " dst=" + candidate.dst + " kind=" + candidate.kind
        + " cargo=" + AICargo.GetCargoLabel(candidate.cargo);
  }
  OpexDecide("V149_STOCK", "action=" + action + where
      + " size=" + ai._railReadyStock.len() + " queue=" + ai._v149RepairQueue.len()
      + " reason=" + reason);
}

/* Echecs de pose dus a la carte (un nouvel A* peut les contourner). CASH n'arrive jamais ici
 * (refus cash_at_build en amont) ; ECON, NOWAGON, TRAINFAIL... ne se reparent pas. */
function OpexV149RepairableBuildFailure(reason)
{
  if (reason == null) return false;
  if (reason == "TRKFAIL" || reason == "TRACKFAIL" || reason == "STNFAIL" || reason == "STATIONFAIL"
      || reason == "DEPFAIL" || reason == "DEPOTFAIL" || reason == "NOPATH" || reason == "OVERLAP") return true;
  return reason.len() >= 4 && reason.slice(0, 4) == "SITE";
}

/* Deux candidats dont une extremite est a moins de MIN_SEPARATION de l'autre se bloqueraient
 * (too_close_no_join) : le second pose serait refuse. */
function OpexV149EndsClose(a, b)
{
  if (a == null || b == null) return false;
  return AIMap.DistanceManhattan(a.src, b.src) < MIN_SEPARATION
      || AIMap.DistanceManhattan(a.src, b.dst) < MIN_SEPARATION
      || AIMap.DistanceManhattan(a.dst, b.src) < MIN_SEPARATION
      || AIMap.DistanceManhattan(a.dst, b.dst) < MIN_SEPARATION;
}

function OpexAI::_v149NearStocked(candidate)
{
  foreach (pairKey, entry in this._railReadyStock) {
    if (entry != null && ("candidate" in entry) && OpexV149EndsClose(candidate, entry.candidate)) return true;
  }
  foreach (item in this._v149RepairQueue) {
    if (OpexV149EndsClose(candidate, item.candidate)) return true;
  }
  return false;
}

/* Point 2 : sauts du worker, apres les filtres et le seuil historiques. Une paire tout juste
 * posee est couverte par _tooClose (ses origines et ses gares sont dans _lines). */
function OpexAI::_v149WorkerSkip(candidate)
{
  local close = this._tooClose(candidate);
  if (close.hard >= 0 || close.blocking >= 0) {
    this._v149SkipClose++;
    return true;
  }
  if (this._v149NearStocked(candidate)) {
    this._v149SkipNear++;
    return true;
  }
  return false;
}

/* Point 4 : met une paire en file de reparation. Au plus 2 reparations par paire, ensuite
 * retrait 365 jours. Une paire marquee abandonnee (STNFAIL, SITE*...) n'est pas reparee : la
 * memoire d'abandon refuserait de toute facon la pose. */
function OpexAI::_v149QueueRepair(candidate, pairKey, reason)
{
  if (candidate == null) return false;
  local count = (pairKey in this._v149RepairCount) ? this._v149RepairCount[pairKey] : 0;
  if (count >= 2) {
    this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
    OpexV149Log(this, "repair_fail", candidate, "exhausted_" + reason);
    return false;
  }
  if (this._abandonedPairs != null && (OpexAbandonedPairKey(candidate) in this._abandonedPairs)) {
    OpexV149Log(this, "drop", candidate, "abandoned_" + reason);
    return false;
  }
  foreach (item in this._v149RepairQueue) {
    if (item.key == pairKey) return true;
  }
  this._v149RepairQueue.append({ key = pairKey, candidate = candidate, reason = reason });
  return true;
}

/* Point 4 : demarre la premiere reparation encore valable. Appele par _tryStartRailStockWorker
 * avant toute nouvelle recherche, creneau libre et stock non plein. */
function OpexAI::_v149StartRepair()
{
  local curDate = AIDate.GetCurrentDate();
  while (this._v149RepairQueue.len() > 0) {
    local item = this._v149RepairQueue.remove(0);
    local cand = item.candidate;
    if (item.key in this._railReadyStock) continue;
    if ((item.key in this._railStockCooldown) && curDate <= this._railStockCooldown[item.key]) continue;
    if (this._abandonedPairs != null && (OpexAbandonedPairKey(cand) in this._abandonedPairs)) continue;
    if (cand.kind != "pax") {
      /* src/dst sont des tuiles (OpexMakeCandidate), pas des IndustryID. */
      if (!AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(cand.src))
          || !AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(cand.dst))) {
        this._railStockCooldown[item.key] <- curDate + 365;
        OpexV149Log(this, "drop", cand, "industry_closed");
        continue;
      }
    }
    local close = this._tooClose(cand);
    if (close.hard >= 0 || close.blocking >= 0) {
      this._railStockCooldown[item.key] <- curDate + 365;
      OpexV149Log(this, "drop", cand, "too_close");
      continue;
    }
    local count = ((item.key in this._v149RepairCount) ? this._v149RepairCount[item.key] : 0) + 1;
    this._v149RepairCount[item.key] <- count;
    this._v149RepairsStarted++;
    if ("railPlan" in cand) cand.railPlan = null;
    OpexV149Log(this, "repair_start", cand, item.reason + " n=" + count);
    if (this._startRailStockSearch(cand, true, item.reason)) return true;
    OpexV149Log(this, "repair_fail", cand, "prepare");
  }
  return false;
}

/* Point 3 : test des tuiles d'un trace stocke, comme _revalidateRailStockPlan mais sans la
 * caisse ni la place vehicule (testees a la pose). null si le trace est posable. */
function OpexAI::_v149RevalidateTiles(candidate, plan)
{
  if (candidate.kind != "pax") {
    if (!AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(candidate.src))
        || !AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(candidate.dst))) return "industry_closed";
  }
  local close = this._tooClose(candidate);
  if (close.hard >= 0 || close.blocking >= 0) return "too_close";
  if (!("planA" in plan) || !("planB" in plan) || !("tiles" in plan)) return "invalid_plan_structure";
  local planA = plan.planA;
  local planB = plan.planB;
  local tiles = plan.tiles;
  if (planA == null || planB == null || tiles == null || tiles.len() < 3) return "invalid_plan_structure";

  local testMode = AITestMode();
  local stIdA = ("stationId" in planA) ? planA.stationId : AIStation.STATION_NEW;
  local stIdB = ("stationId" in planB) ? planB.stationId : AIStation.STATION_NEW;
  if (!AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length, stIdA)
      || !AIRail.BuildRailStation(planB.anchor, planB.direction, 1, planB.length, stIdB)) return "station_blocked";
  local trackRes = OpexTestRailTrack(tiles, (("structures" in plan) ? plan.structures : null));
  if (trackRes.failed > 0) return "track_blocked";
  local offsets = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
    AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)
  ];
  for (local idx = 1; idx < tiles.len() - 1; idx++) {
    local anchor = tiles[idx];
    foreach (offset in offsets) {
      local cand = anchor + offset;
      if (AIMap.IsValidTile(cand) && AIRail.BuildRailDepot(cand, anchor)) return null;
    }
  }
  return "depot_blocked";
}

/* Retire un trace du stock. Fermeture d'industrie, separation et filet de 365 jours : retrait
 * de la paire ; carte bloquee : file de reparation. */
function OpexAI::_v149DropStockEntry(pairKey, entry, reason)
{
  if (pairKey in this._railReadyStock) delete this._railReadyStock[pairKey];
  local cand = (entry != null && ("candidate" in entry)) ? entry.candidate : null;
  if (RAIL_PREASTAR_PROBE && entry != null && ("plan" in entry) && entry.plan != null
      && ("railPreastarRid" in entry.plan)) {
    OpexRailPreAstarLog("BUILD", "rid=" + entry.plan.railPreastarRid
        + " reason=" + reason + " ok=0 status=v149_dropped");
  }
  if (cand != null && ("railPlan" in cand)) cand.railPlan = null;
  local curDate = AIDate.GetCurrentDate();
  if (reason == "expire") {
    this._railStockCooldown[pairKey] <- curDate + 180;
    OpexV149Log(this, "expire", cand, reason);
  } else if (reason == "industry_closed" || reason == "too_close" || cand == null) {
    this._railStockCooldown[pairKey] <- curDate + 365;
    OpexV149Log(this, "drop", cand, reason);
  } else {
    OpexV149Log(this, "revalidate_fail", cand, reason);
    this._v149QueueRepair(cand, pairKey, reason);
  }
}

/* Point 3 : tous les V149_REVALIDATE_DAYS, chaque trace stocke est reteste ; un trace de plus
 * de 365 jours jamais consomme est retire (filet de securite, remplace l'expiration a 180). */
function OpexAI::_v149RevalidateStock(curDate)
{
  if (curDate < this._v149NextRevalidate) return;
  this._v149NextRevalidate = curDate + V149_REVALIDATE_DAYS;
  if (this._railReadyStock.len() == 0) return;
  local failed = [];
  foreach (pairKey, entry in this._railReadyStock) {
    if (entry == null || !("plan" in entry) || entry.plan == null
        || !("candidate" in entry) || entry.candidate == null) {
      failed.append({ key = pairKey, entry = entry, reason = "invalid_plan_structure" });
      continue;
    }
    if (("readyDate" in entry) && curDate - entry.readyDate > 365) {
      failed.append({ key = pairKey, entry = entry, reason = "expire" });
      continue;
    }
    local reason = this._v149RevalidateTiles(entry.candidate, entry.plan);
    if (reason == null) {
      OpexV149Log(this, "revalidate_ok", entry.candidate, "age=" + (curDate - entry.readyDate));
    } else {
      failed.append({ key = pairKey, entry = entry, reason = reason });
    }
  }
  foreach (f in failed) this._v149DropStockEntry(f.key, f.entry, f.reason);
}

/* Trace stocke refuse par la separation a la pose : retire tout de suite plutot qu'a la
 * prochaine revalidation (il occuperait une place du stock). */
function OpexAI::_v149DropTooClose(candidate)
{
  local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
  if (pairKey in this._railReadyStock) this._v149DropStockEntry(pairKey, this._railReadyStock[pairKey], "too_close");
}

/* Echec de revalidation a la pose (trace deja retire du stock par l'appelant). */
function OpexAI::_v149OnRevalidateFail(candidate, reason)
{
  local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
  if (reason == "industry_closed") {
    this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
    OpexV149Log(this, "drop", candidate, reason);
    return;
  }
  OpexV149Log(this, "revalidate_fail", candidate, "at_build_" + reason);
  this._v149QueueRepair(candidate, pairKey, "at_build_" + reason);
}

/* Apres OpexBuildLine sur un trace stocke : consommation, ou reparation au lieu du retrait
 * historique de 365 jours. Le trace est retire du stock ici, avant le nettoyage C121/C80. */
function OpexAI::_v149AfterBuildAttempt(candidate, result, recorded)
{
  local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
  if (!(pairKey in this._railReadyStock)) return;
  local entry = this._railReadyStock[pairKey];
  delete this._railReadyStock[pairKey];
  local delayDays = (entry != null && ("readyDate" in entry)) ? AIDate.GetCurrentDate() - entry.readyDate : -1;
  if (recorded) {
    if (C56_TASK_TRACE) {
      OpexC56TaskLog("RAIL_STOCK_CONSUME", "rail_stock", this._taskCycle,
                     "src=" + candidate.src + " dst=" + candidate.dst + " delay_days=" + delayDays);
    }
    OpexV149Log(this, "consume", candidate, "delay=" + delayDays);
    return;
  }
  local reason = (result != null && ("reason" in result) && result.reason != null) ? result.reason : "";
  if (OpexV149RepairableBuildFailure(reason)) {
    OpexV149Log(this, "drop", candidate, "build_" + reason);
    this._v149QueueRepair(candidate, pairKey, "build_" + reason);
  } else {
    this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;
    OpexV149Log(this, "drop", candidate, "build_" + reason);
  }
}

/* Point 5 : rendre la passe projects due tout de suite. Si elle n'a pas encore tourne dans ce
 * cycle, elle arrive de toute facon ; sinon le curseur revient sur elle (les taches entre elle et
 * l'ancien curseur ont deja tourne et ne sont pas dues : aucune n'est sautee). La selection est
 * marquee perimee pour que le trace entre dans best (OpexEnsureSelection lit le stock). */
function OpexAI::_v149ExpediteProjects()
{
  if (this._projects != null) this._projects.rawset("selectionStale", true);
  if (this._taskQueue == null) return;
  for (local i = 0; i < this._taskQueue.len(); i++) {
    local t = this._taskQueue[i];
    if (t.name != "projects") continue;
    if (t.enabled && i < this._taskCursor) {
      t.dueCycle = this._taskCycle;
      this._taskCursor = i;
    }
    return;
  }
}

/* Depot d'un trace par le worker (recherche neuve ou reparation). */
function OpexAI::_v149OnDeposit(candidate, fundScore, isRepair)
{
  OpexV149Log(this, isRepair ? "repair_ok" : "deposit", candidate, "score=" + fundScore);
  if (this._v149AirYearActive()) return;
  if (this._railStockLastFundedScore > 0.0 && fundScore < this._railStockLastFundedScore) return;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < candidate.capital + OpexCashReserve()) return;
  OpexV149Log(this, "expedite", candidate, "score=" + fundScore);
  this._v149ExpediteProjects();
}

/* Point 0 : regeneration mensuelle du vivier rail (cargo fret tournant), hors de la tache
 * catalogue. Sous le catalogue AIR incremental, la tache catalogue reste dans sa reconstruction
 * AIR : le portefeuille complet (rail et route) n'est reconstruit qu'en janvier 1972 au plus tot
 * (diag 5x5 du 13/10) et la rotation C76 n'est jamais atteinte. projects.rail, que lit le worker,
 * reste donc vide toute l'annee 1971. Meme appel que _c76RotateFreight, rail seulement (la route
 * n'est pas un chantier autonome). Pendant l'annee AIR, a partir d'octobre seulement : le stock
 * se remplit pour janvier, la gate garde les projets rail sans trace hors de la selection. */
function OpexAI::_v149MaybeRegenRail()
{
  if (!V149_FREIGHT_ROTATION) return;
  local date = AIDate.GetCurrentDate();
  local month = AIDate.GetMonth(date);
  local ym = AIDate.GetYear(date) * 12 + month;
  if (ym == this._v149RegenMonth) return;
  if (this._v149AirYearActive() && month < 10) return;
  if (this._projects == null || !("candidateGroups" in this._projects)
      || this._projects.candidateGroups == null || this._catalog == null) return;
  this._v149RegenMonth = ym;
  local freightCargos = OpexFreightCargoOrder(this._catalog);
  if (freightCargos.len() > 0) {
    local nextCargo = 0;
    if (this._lastFreightCargo >= 0) {
      for (local i = 0; i < freightCargos.len(); i++) {
        if (freightCargos[i] == this._lastFreightCargo) {
          nextCargo = (i + 1) % freightCargos.len();
          break;
        }
      }
    }
    this._projects.rawset("freightCargo", freightCargos[nextCargo]);
  }
  local mark = DECISION_LOG ? OpexOpsMeasureBegin() : null;
  this._projects = OpexRegenerateModeProjects(this._projects, this._catalog, this._budget,
      this._lines, this._abandonedPairs, "rail", null, null, -1);
  if (freightCargos.len() > 0 && ("freightCargo" in this._projects) && this._projects.freightCargo != null)
    this._lastFreightCargo = this._projects.freightCargo;
  this._ranked = this._projects.rail;
  this._v149RegenCount++;
  if (mark != null) {
    local ops = OpexOpsMeasureEnd(mark);
    local n = (this._projects.rail != null && ("candidates" in this._projects.rail)
        && this._projects.rail.candidates != null) ? this._projects.rail.candidates.len() : -1;
    local cargo = (("freightCargo" in this._projects) && this._projects.freightCargo != null)
        ? AICargo.GetCargoLabel(this._projects.freightCargo) : "none";
    OpexDecide("V149_RAIL_REGEN", "cargo=" + cargo + " candidates=" + n + " ops=" + ops
        + " n=" + this._v149RegenCount);
  }
}

/* Diagnostic mensuel (DECISION_LOG seulement) : pourquoi le worker ne demarre pas. Rejoue les
 * filtres de _tryStartRailStockWorker sans rien modifier ; le worker lui-meme n'est pas touche. */
function OpexAI::_v149IdleDiag()
{
  local why = "free";
  if (this._activeWorker != null) why = "worker_" + this._activeWorker.kind;
  else if (this._railSearch != null) why = "searching";
  else if (this._railReadyStock.len() >= OpexRailStockCapacity()) why = "full";
  else if (this._v149AirYearActive() && this._c121RailPrepAirFundableCheap()) why = "air_hold";
  local n = 0, stock = 0, cool = 0, abnd = 0, cost = 0, ind = 0, thr = 0, close = 0, near = 0, ok = 0;
  local list = null;
  if (this._projects != null && ("rail" in this._projects) && this._projects.rail != null) {
    if (("best" in this._projects.rail) && this._projects.rail.best != null && this._projects.rail.best.len() > 0)
      list = this._projects.rail.best;
    else if (("candidates" in this._projects.rail) && this._projects.rail.candidates != null)
      list = this._projects.rail.candidates;
  }
  if (list != null) {
    local curDate = AIDate.GetCurrentDate();
    local maxCost = (OpexAvailableCapital() * 3) / 2;
    if (maxCost < 30000) maxCost = 30000;
    local threshold = this._railStockLastFundedScore;
    foreach (c in list) {
      if (c == null) continue;
      n++;
      local key = OpexProjectPairKey(c.kind, c.cargo, c.src, c.dst);
      if (key in this._railReadyStock) { stock++; continue; }
      if ((key in this._railStockCooldown) && curDate <= this._railStockCooldown[key]) { cool++; continue; }
      if (OpexAbandonedPairKey(c) in this._abandonedPairs) { abnd++; continue; }
      if (c.capital > maxCost) { cost++; continue; }
      if (c.kind != "pax" && (!AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(c.src))
          || !AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(c.dst)))) { ind++; continue; }
      local paper = OpexProjectFromCandidate(c);
      if (paper == null) { ind++; continue; }
      local profit = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(paper) : paper.profitAnnual;
      if (threshold > 0.0 && OpexProjectScore(profit, OpexProjectFinanceCapital(paper)) < threshold) { thr++; continue; }
      local tc = this._tooClose(c);
      if (tc.hard >= 0 || tc.blocking >= 0) { close++; continue; }
      if (this._v149NearStocked(c)) { near++; continue; }
      ok++;
    }
  }
  return "idle=" + why + " cands=" + (list == null ? -1 : n) + " f_stock=" + stock + " f_cool=" + cool
      + " f_abnd=" + abnd + " f_cost=" + cost + " f_ind=" + ind + " f_thr=" + thr
      + " f_close=" + close + " f_near=" + near + " eligible=" + ok
      + " threshold=" + this._railStockLastFundedScore;
}

/* Fin de passe projects (avant le demarrage du worker) : minimum AIR de l'annee AIR,
 * regeneration mensuelle du vivier rail, revalidation periodique, ligne mensuelle. */
function OpexAI::_v149AfterProjectsPass()
{
  local curDate = AIDate.GetCurrentDate();
  /* Le worker cede a l'AIR finançable (_c121RailPrepAirFundableCheap) : rafraichir le minimum
   * quand la preparation C121 ne le fait pas (reglage coupe, ou stock deja a son maximum). */
  if (this._v149AirYearActive()
      && (!C121_AIR_FIRST_YEAR_RAIL_PREP || this._railReadyStock.len() >= C121_RAIL_PREP_MAX)) {
    this._c121CheapestLivingAirCap();
  }
  this._v149MaybeRegenRail();
  this._v149RevalidateStock(curDate);
  if (DECISION_LOG) {
    local ym = AIDate.GetYear(curDate) * 12 + AIDate.GetMonth(curDate);
    if (ym != this._v149LogMonth) {
      this._v149LogMonth = ym;
      OpexDecide("V149_STOCK_MONTH", "size=" + this._railReadyStock.len()
          + " cap=" + OpexRailStockCapacity() + " queue=" + this._v149RepairQueue.len()
          + " repairs=" + this._v149RepairsStarted
          + " searching=" + (this._railSearch != null ? 1 : 0)
          + " held=" + (this._v149AirYearActive() ? 1 : 0)
          + " skip_close=" + this._v149SkipClose + " skip_near=" + this._v149SkipNear
          + " " + this._v149IdleDiag());
    }
  }
}
