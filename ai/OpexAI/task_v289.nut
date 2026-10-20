/* V289 : Travailleurs de reliquat de tick.
 *
 * Repartit les opcodes restants en fin de boucle principale avant Sleep(1).
 * Bitmask v289_slack_workers :
 *   - bit 1 : worker rail (A* de preparation dans un creneau dedie, trace au stock)
 *   - bit 2 : cartographie (un pas de _c67TerrainSlackStep)
 *   - bit 4 : croissance urbaine (TOWN_ACTION_FUND_BUILDINGS sous garde de richesse, mensuel)
 *
 * Contrat d'opcodes :
 * - Arret immediat si GetOpsTillSuspend() < V289_SLACK_MIN (2500).
 * - Cout de chaque pas borne et memorise dans _v289EstOps (analogue a _v89EstimatedSliceOps).
 * - Une tranche d'A* ne franchit pas le tick ; le demarrage d'un A* et le pas
 *   mensuel de la ville peuvent le franchir (rares).
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
                 + " skipped_low=" + this._v289SkippedLow
                 + " rail_year1=" + this._v289RailWhy.year1 + " rail_full=" + this._v289RailWhy.full
                 + " rail_low=" + this._v289RailWhy.low + " rail_none=" + this._v289RailWhy.none
                 + " stock=" + (this._railReadyStock != null ? this._railReadyStock.len() : -1)
                 + " rail_flight=" + (this._v289RailSearch != null ? 1 : 0));
    }
    this._v289LastStatsMonth = curMonth;
    this._v289Calls = 0;
    this._v289OpsRail = 0;
    this._v289OpsMap = 0;
    this._v289OpsTown = 0;
    this._v289SkippedLow = 0;
    this._v289RailWhy = { year1 = 0, full = 0, low = 0, none = 0 };
  }
}

/* Vrai si ce candidat peut recevoir un A* de reliquat : pas deja en stock ni en
 * recherche dans le creneau principal, pas de trace attache. */
function OpexAI::_v289RailPrepEligible(candidate, curDate)
{
  if (candidate == null) return false;
  if (("railPlan" in candidate) && candidate.railPlan != null) return false;
  if (OpexC121RailPrepCandidateBlocked(this, candidate, curDate)) return false;
  local main = this._railSearch;
  if (main != null && ("candidate" in main) && main.candidate != null
      && ("kind" in main.candidate) && ("cargo" in main.candidate)
      && OpexProjectPairKey(main.candidate.kind, main.candidate.cargo, main.candidate.src, main.candidate.dst)
         == OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst)) return false;
  return true;
}

/* Le premier candidat rail eligible : best tel quel (jamais de re-selection
 * depuis le reliquat), puis la tete du vivier rail. null si aucun. */
function OpexAI::_v289PickRailCandidate(curDate)
{
  if (this._projects == null) return null;
  if (("best" in this._projects) && this._projects.best != null) {
    foreach (project in this._projects.best) {
      if (project == null || !("mode" in project) || project.mode != "rail") continue;
      if (!("payload" in project) || project.payload == null) continue;
      if (this._v289RailPrepEligible(project.payload, curDate)) return project.payload;
    }
  }
  if (("rail" in this._projects) && this._projects.rail != null
      && ("candidates" in this._projects.rail) && this._projects.rail.candidates != null) {
    local list = this._projects.rail.candidates;
    local limit = list.len() < TOP_K ? list.len() : TOP_K;
    for (local i = 0; i < limit; i++) {
      if (this._v289RailPrepEligible(list[i], curDate)) return list[i];
    }
  }
  return null;
}

/* Les traces deposes par le reliquat vieillissent : passe V289_STOCK_TTL_DAYS,
 * la carte a change et la paire n'a pas ete retenue, on libere la place. */
function OpexAI::_v289ExpireStock(curDate)
{
  if (this._railReadyStock == null) return;
  local stale = [];
  foreach (pairKey, entry in this._railReadyStock) {
    if (entry == null || !("v289" in entry) || !entry.v289) continue;
    if (curDate - entry.readyDate > V289_STOCK_TTL_DAYS) stale.append(pairKey);
  }
  foreach (pairKey in stale) {
    local entry = this._railReadyStock[pairKey];
    delete this._railReadyStock[pairKey];
    if (entry.candidate != null) {
      if ("railPlan" in entry.candidate) entry.candidate.railPlan = null;
      if ("c121PrepStock" in entry.candidate) entry.candidate.c121PrepStock = false;
    }
    if (DECISION_LOG) OpexDecide("V289_STOCK_EXPIRE", "pair=" + pairKey + " age=" + (curDate - entry.readyDate));
  }
  if (stale.len() > 0) this._c121RailPrepRememberStock();
}

/* Worker rail : un A* de preparation dans son PROPRE creneau _v289RailSearch.
 * Le creneau principal _railSearch n'est echange que le temps de la tranche :
 * les chantiers reels ne voient jamais cette recherche, ne l'avancent pas et ne
 * la consomment pas ; elle n'avance que sur le reliquat. Le trace termine va au
 * stock (_railReadyStock), que la passe projects pose sans nouvel A*.
 * L'annee AIR de C121 garde le creneau principal pour sa propre preparation. */
function OpexAI::_v289StepRail()
{
  if (!MODE_RAIL || C121_CATALOG_FIRST_YEAR_ACTIVE) { this._v289RailWhy.year1++; return false; }
  if (this._railReadyStock == null || this._catalog == null || this._lines == null) return false;
  local curDate = AIDate.GetCurrentDate();
  local slot = this._v289RailSearch;
  if (slot == null) {
    this._v289ExpireStock(curDate);
    if (this._railReadyStock.len() >= C121_RAIL_PREP_MAX) { this._v289RailWhy.full++; return false; }
    if (AIController.GetOpsTillSuspend() < V289_RAIL_START_MIN) { this._v289RailWhy.low++; return false; }
    local candidate = this._v289PickRailCandidate(curDate);
    if (candidate == null) { this._v289RailWhy.none++; return false; }
    local savedSearch = this._railSearch;
    local savedWorker = this._activeWorker;
    this._railSearch = null;
    local started = this._startRailStockSearch(candidate);
    this._v289RailSearch = started ? this._railSearch : null;
    this._railSearch = savedSearch;
    this._activeWorker = savedWorker;
    if (started && DECISION_LOG) OpexDecide("V289_RAIL_START", "src=" + candidate.src + " dst=" + candidate.dst
        + " kind=" + candidate.kind + " budget=" + this._v289RailSearch.iterationBudget);
    return started;
  }
  /* Le chantier reel a pris la meme paire : la preparation ne sert plus. */
  local c = slot.candidate;
  if (!this._v289RailPrepEligibleInFlight(c, curDate)) {
    this._v289RailSearch = null;
    if (DECISION_LOG) OpexDecide("V289_RAIL_DROP", "src=" + c.src + " dst=" + c.dst + " reason=taken");
    return true;
  }
  local savedSearch = this._railSearch;
  local savedWorker = this._activeWorker;
  this._railSearch = slot;
  if (curDate - slot.startDate > V289_STOCK_TTL_DAYS) {
    if (DECISION_LOG) OpexDecide("V289_RAIL_TIMEOUT", "src=" + c.src + " dst=" + c.dst + " iters=" + slot.spent);
    this._handleRailStockSearchTimeout();
  } else {
    if (slot.phase == "search") this._continueRailSearch();
    if (this._railSearch != null && this._railSearch.phase == "build") {
      local cand = this._railSearch.candidate;
      local pairKey = OpexProjectPairKey(cand.kind, cand.cargo, cand.src, cand.dst);
      this._handleRailStockSearchCompleted();
      if (pairKey in this._railReadyStock) {
        local entry = this._railReadyStock[pairKey];
        entry.rawset("v289", true);
        cand.rawset("c121PrepStock", true);
        this._c121RailPrepRememberStock();
        if (DECISION_LOG) OpexDecide("V289_RAIL_DEPOSIT", "src=" + cand.src + " dst=" + cand.dst
            + " iters=" + slot.spent + " days=" + (curDate - slot.startDate) + " stock=" + this._railReadyStock.len());
      } else if (DECISION_LOG) {
        OpexDecide("V289_RAIL_FAIL", "src=" + cand.src + " dst=" + cand.dst + " iters=" + slot.spent);
      }
    }
  }
  this._v289RailSearch = this._railSearch;
  this._railSearch = savedSearch;
  this._activeWorker = savedWorker;
  return true;
}

/* En vol, seul compte que la paire n'ait pas ete prise par le creneau principal
 * ni deja deposee au stock. */
function OpexAI::_v289RailPrepEligibleInFlight(candidate, curDate)
{
  if (candidate == null) return false;
  local pairKey = OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst);
  if (pairKey in this._railReadyStock) return false;
  local main = this._railSearch;
  if (main != null && ("candidate" in main) && main.candidate != null && ("kind" in main.candidate)
      && ("cargo" in main.candidate)
      && OpexProjectPairKey(main.candidate.kind, main.candidate.cargo, main.candidate.src, main.candidate.dst) == pairKey)
    return false;
  if (this._abandonedPairs != null && (OpexAbandonedPairKey(candidate) in this._abandonedPairs)) return false;
  return true;
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
  /* Une seule tentative par mois : le parcours des lignes et la sonde de cout
   * (AITestMode) ne se repetent pas a chaque reliquat. */
  local today = AIDate.GetCurrentDate();
  local stamp = AIDate.GetYear(today) * 12 + AIDate.GetMonth(today);
  if (this._v289TownMonth == stamp) return false;
  this._v289TownMonth = stamp;
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) {
    if (DECISION_LOG) OpexDecide("V289_TOWN_SKIP", "reason=loan loan=" + loan);
    return false;
  }

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

  if (!found) {
    if (DECISION_LOG) OpexDecide("V289_TOWN_SKIP", "reason=no_town towns=" + byTown.len());
    return false;
  }

  local account = AIAccounting();
  {
    local test = AITestMode();
    AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_FUND_BUILDINGS);
  }
  local cost = account.GetCosts();
  if (cost <= 0) return false;

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects);
  if (cash - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V289_TOWN_SKIP", "reason=cash cash=" + cash + " cost=" + cost
                                 + " threshold=" + threshold);
    return false;
  }

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
      local inFlight = this._v289RailSearch != null && this._v289RailSearch.phase == "search";
      local mark = OpexOpsMeasureBegin();
      worked = this._v289StepRail();
      local ops = OpexOpsMeasureEnd(mark);
      if (sp != null) OpexSpanEnd(sp);
      this._v289OpsRail += ops;
      /* Seule une tranche d'A* en vol renseigne l'estimation : un demarrage (quais)
       * coute davantage et a son propre seuil V289_RAIL_START_MIN. */
      if (inFlight && ops > 0) {
        local nextEst = ops + 500;
        if (nextEst < 1500) nextEst = 1500;
        /* Une tranche qui a franchi le tick ne doit pas geler le worker : borne. */
        if (nextEst > V289_RAIL_START_MIN) nextEst = V289_RAIL_START_MIN;
        this._v289EstOps[1] = nextEst;
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
        if (nextEst > C67_SLACK_MIN) nextEst = C67_SLACK_MIN;
        this._v289EstOps[2] = nextEst;
      }
    } else if (workerId == 4) {
      local sp = PROBE_SPAN_TRACE ? OpexSpanBegin("slack.town") : null;
      local mark = OpexOpsMeasureBegin();
      worked = this._v289StepTown();
      local ops = OpexOpsMeasureEnd(mark);
      if (sp != null) OpexSpanEnd(sp);
      /* Pas d'estimation : le pas est mensuel, son cout ne predit pas le suivant. */
      this._v289OpsTown += ops;
    }

    if (worked) {
      idleCount = 0;
    } else {
      idleCount++;
      if (idleCount >= nActive) break;
    }
  }
}
