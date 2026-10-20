/* V289 : Travailleurs de reliquat de tick.
 *
 * Repartit les opcodes restants en fin de boucle principale avant Sleep(1).
 * Bitmask v289_slack_workers :
 *   - bit 1 : worker rail (preparation de traces A* sans pose)
 *   - bit 2 : cartographie (un pas de _c67TerrainSlackStep)
 *   - bit 4 : croissance urbaine (TOWN_ACTION_FUND_BUILDINGS sous garde de richesse)
 *
 * Contrat d'opcodes :
 * - Arret immediat si GetOpsTillSuspend() < V289_SLACK_MIN (2500).
 * - Cout de chaque pas borne et memorise dans _v289EstOps (analogue a _v89EstimatedSliceOps).
 * - Ne franchit jamais le tick.
 * - Au defaut 0 : inerte (aucun travail, aucun appel d'API de jeu).
 */

function OpexAI::_v289CheckMonthlyLog()
{
  local date = AIDate.GetCurrentDate();
  local curMonth = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  if (this._v289LastStatsMonth < 0) {
    this._v289LastStatsMonth = curMonth;
    return;
  }
  if (curMonth != this._v289LastStatsMonth) {
    if (DECISION_LOG) {
      OpexDecide("V289_SLACK", "month=" + this._v289LastStatsMonth
                 + " calls=" + this._v289Calls
                 + " ops_rail=" + this._v289OpsRail
                 + " ops_map=" + this._v289OpsMap
                 + " ops_town=" + this._v289OpsTown
                 + " skipped_low=" + this._v289SkippedLow);
    }
    this._v289LastStatsMonth = curMonth;
    this._v289Calls = 0;
    this._v289OpsRail = 0;
    this._v289OpsMap = 0;
    this._v289OpsTown = 0;
    this._v289SkippedLow = 0;
  }
}

function OpexAI::_v289StepRail()
{
  // 1. Si une recherche est deja en vol
  if (this._railSearch != null) {
    if (this._c121RailPrepHold) return false;
    if (this._railSearch.phase == "search") {
      this._advanceRailSearchSliceWithLedgers();
      return true;
    }
    if (this._railSearch.phase == "build") {
      local isStock = (("isStockSearch" in this._railSearch) && this._railSearch.isStockSearch)
          || (("isC121RailPrep" in this._railSearch) && this._railSearch.isC121RailPrep);
      if (isStock) {
        this._handleRailStockSearchCompleted();
        return true;
      }
    }
    return false;
  }

  // 2. Si aucune recherche en vol, amorcer la preparation du prochain candidat de tete
  if (this._railReadyStock != null && this._railReadyStock.len() >= C121_RAIL_PREP_MAX) {
    return false;
  }

  local curDate = AIDate.GetCurrentDate();

  // Priorite 1 : candidat rail selectionne dans this._projects.best non encore prepare
  if (this._projects != null) {
    this._ensureSelection();
    if (("best" in this._projects) && this._projects.best != null) {
      foreach (project in this._projects.best) {
        if (project == null || !("mode" in project) || project.mode != "rail") continue;
        if (!("payload" in project) || project.payload == null) continue;
        local candidate = project.payload;
        if (("railPlan" in candidate) && candidate.railPlan != null) continue;
        if (OpexC121RailPrepCandidateBlocked(this, candidate, curDate)) continue;
        if (this._startRailStockSearch(candidate)) {
          if (this._railSearch != null) this._railSearch.isC121RailPrep <- true;
          this._c121RailPrepHold = false;
          this._c121RailPrepYieldLogged = false;
          return true;
        }
      }
    }
  }

  // Priorite 2 : candidat rail du vivier (this._projects.rail.candidates)
  if (this._projects != null && ("rail" in this._projects) && this._projects.rail != null
      && ("candidates" in this._projects.rail) && this._projects.rail.candidates != null) {
    local list = this._projects.rail.candidates;
    local limit = list.len() < TOP_K ? list.len() : TOP_K;
    for (local i = 0; i < limit; i++) {
      local candidate = list[i];
      if (candidate == null) continue;
      if (("railPlan" in candidate) && candidate.railPlan != null) continue;
      if (OpexC121RailPrepCandidateBlocked(this, candidate, curDate)) continue;
      if (this._startRailStockSearch(candidate)) {
        if (this._railSearch != null) this._railSearch.isC121RailPrep <- true;
        this._c121RailPrepHold = false;
        this._c121RailPrepYieldLogged = false;
        return true;
      }
    }
  }

  // Priorite 3 : vivier prepare de l'annee 1 (_c121RailPrepCandidates)
  if (this._c121RailPrepCandidates != null) {
    local list = this._c121RailPrepCandidates;
    local limit = list.len() < TOP_K ? list.len() : TOP_K;
    for (local i = 0; i < limit; i++) {
      local candidate = list[i];
      if (candidate == null) continue;
      if (("railPlan" in candidate) && candidate.railPlan != null) continue;
      if (OpexC121RailPrepCandidateBlocked(this, candidate, curDate)) continue;
      if (this._startRailStockSearch(candidate)) {
        if (this._railSearch != null) this._railSearch.isC121RailPrep <- true;
        this._c121RailPrepHold = false;
        this._c121RailPrepYieldLogged = false;
        return true;
      }
    }
  }

  return false;
}

function OpexAI::_v289StepMap()
{
  if (this._c67Terrain == null) {
    if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) return false;
    this._c67TerrainInit();
    return true;
  }
  if (this._c67Terrain.PendingCount() == 0 && this._c67BgIdle) return false;
  local hooksBefore = (this._c67Ledger != null && ("hooks" in this._c67Ledger)) ? this._c67Ledger.hooks : 0;
  this._c67TerrainSlackStep();
  local hooksAfter = (this._c67Ledger != null && ("hooks" in this._c67Ledger)) ? this._c67Ledger.hooks : 0;
  return hooksAfter > hooksBefore;
}

function OpexAI::_v289StepTown()
{
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) return false;

  local curDate = AIDate.GetCurrentDate();
  if (this._v289TownFundDate == null) this._v289TownFundDate = {};

  local byTown = {};
  if (this._lines != null) {
    foreach (line in this._lines) {
      if (line == null) continue;
      local profit = OpexV249LineProfit(line);
      local seenTown = {};
      foreach (endName in ["A", "B"]) {
        local stationId = OpexLineStationId(line, endName);
        if (stationId < 0) continue;
        local townId = AIStation.GetNearestTown(stationId);
        if (!AITown.IsValidTown(townId)) continue;
        if (townId in seenTown) continue;
        seenTown[townId] <- 1;
        if (!(townId in byTown)) byTown[townId] <- { profit = 0, lines = 0 };
        byTown[townId].profit += profit;
        byTown[townId].lines++;
      }
    }
  }

  local bestTown = -1;
  local bestProfit = 0;
  local found = false;
  foreach (townId, info in byTown) {
    if ((townId in this._v289TownFundDate) && (curDate - this._v289TownFundDate[townId] < 182)) {
      continue;
    }
    if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_FUND_BUILDINGS)) {
      continue;
    }
    if (!found || info.profit > bestProfit || (info.profit == bestProfit && townId < bestTown)) {
      found = true;
      bestTown = townId;
      bestProfit = info.profit;
    }
  }

  if (!found) return false;

  local account = AIAccounting();
  {
    local test = AITestMode();
    AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_FUND_BUILDINGS);
  }
  local cost = account.GetCosts();
  if (cost <= 0) return false;

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects);
  if (cash - cost < threshold) return false;

  local executed = AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_FUND_BUILDINGS);
  if (executed) {
    this._v289TownFundDate[bestTown] <- curDate;
    if (DECISION_LOG) {
      OpexDecide("V289_TOWN", "town=" + bestTown + " cost=" + cost + " cash=" + cash
                 + " threshold=" + threshold + " profit=" + bestProfit);
    }
    return true;
  }
  return false;
}

function OpexAI::_v289SlackWorkers()
{
  if (V289_SLACK_WORKERS == 0) return;

  this._v289CheckMonthlyLog();
  this._v289Calls++;

  if (AIController.GetOpsTillSuspend() < V289_SLACK_MIN) {
    this._v289SkippedLow++;
    return;
  }

  local active = [];
  if (V289_SLACK_WORKERS & 1) active.append(1);
  if (V289_SLACK_WORKERS & 2) active.append(2);
  if (V289_SLACK_WORKERS & 4) active.append(4);
  local nActive = active.len();
  if (nActive == 0) return;

  if (this._v289EstOps == null) {
    local railEst = (this._v89EstimatedSliceOps > 1500) ? this._v89EstimatedSliceOps : 2000;
    this._v289EstOps = { [1] = railEst, [2] = 2500, [4] = 1500 };
  }

  local idleCount = 0;
  while (AIController.GetOpsTillSuspend() >= V289_SLACK_MIN) {
    local workerId = active[this._v289WorkerCursor % nActive];
    this._v289WorkerCursor++;

    local est = (workerId in this._v289EstOps) ? this._v289EstOps[workerId] : 2000;
    if (est < V289_SLACK_MIN) est = V289_SLACK_MIN;
    if (AIController.GetOpsTillSuspend() < est) break;

    local worked = false;
    if (workerId == 1) {
      local sp = PROBE_SPAN_TRACE ? OpexSpanBegin("slack.rail") : null;
      local mark = OpexOpsMeasureBegin();
      worked = this._v289StepRail();
      local ops = OpexOpsMeasureEnd(mark);
      if (sp != null) OpexSpanEnd(sp);
      this._v289OpsRail += ops;
      if (ops > 0) {
        local nextEst = ops + 500;
        if (nextEst < 1500) nextEst = 1500;
        this._v289EstOps[1] = nextEst;
        this._v89EstimatedSliceOps = nextEst;
      }
    } else if (workerId == 2) {
      local sp = PROBE_SPAN_TRACE ? OpexSpanBegin("slack.map") : null;
      local mark = OpexOpsMeasureBegin();
      worked = this._v289StepMap();
      local ops = OpexOpsMeasureEnd(mark);
      if (sp != null) OpexSpanEnd(sp);
      this._v289OpsMap += ops;
      if (ops > 0) {
        local nextEst = ops + 500;
        if (nextEst < 1500) nextEst = 1500;
        this._v289EstOps[2] = nextEst;
      }
    } else if (workerId == 4) {
      local sp = PROBE_SPAN_TRACE ? OpexSpanBegin("slack.town") : null;
      local mark = OpexOpsMeasureBegin();
      worked = this._v289StepTown();
      local ops = OpexOpsMeasureEnd(mark);
      if (sp != null) OpexSpanEnd(sp);
      this._v289OpsTown += ops;
      if (ops > 0) {
        local nextEst = ops + 500;
        if (nextEst < 1500) nextEst = 1500;
        this._v289EstOps[4] = nextEst;
      }
    }

    if (worked) {
      idleCount = 0;
    } else {
      idleCount++;
      if (idleCount >= nActive) break;
    }
  }
}
