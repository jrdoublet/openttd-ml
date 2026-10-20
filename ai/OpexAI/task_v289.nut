/* V289 : Travailleurs de reliquat de tick.
 *
 * Repartit les opcodes restants en fin de boucle principale avant Sleep(1).
 * Bitmask v289_slack_workers :
 *   - bit 1 : worker rail (A* de preparation dans un creneau dedie, trace au stock)
 *   - bit 2 : cartographie (un pas de _c67TerrainSlackStep)
 *   - bit 4 : croissance urbaine (TOWN_ACTION_FUND_BUILDINGS si le gain predit couvre le cout, mensuel)
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
                 + " rail_year1=" + this._v289RailWhy.year1 + " rail_air=" + this._v289RailWhy.air + " rail_full=" + this._v289RailWhy.full
                 + " rail_gap=" + this._v289RailWhy.gap + " rail_low=" + this._v289RailWhy.low + " rail_none=" + this._v289RailWhy.none
                 + " stock=" + (this._railReadyStock != null ? this._railReadyStock.len() : -1)
                 + " rail_flight=" + (this._v289RailSearch != null ? 1 : 0)
                 + " ops_per_iter=" + this._v289OpsPerIter);
    }
    this._v289LastStatsMonth = curMonth;
    this._v289Calls = 0;
    this._v289OpsRail = 0;
    this._v289OpsMap = 0;
    this._v289OpsTown = 0;
    this._v289SkippedLow = 0;
    this._v289RailWhy = { year1 = 0, air = 0, full = 0, gap = 0, low = 0, none = 0 };
  }
}

/* Vrai si une extremite du candidat est deja prise : ligne rail posee, recherche du
 * creneau principal ou trace en stock. Seule exception, la destination fret partagee
 * (V179 joint la gare). Sans cette garde, le reliquat stockait des paires qu'un chantier
 * voisin rendait too_close_hard ou too_close_no_join a la pose (smoke v289f). */
function OpexAI::_v289EndpointTaken(candidate, ownPairKey)
{
  local reserved = [];
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    reserved.append([line.originA, line.originB, ("kind" in line) ? line.kind : ""]);
  }
  local main = this._railSearch;
  if (main != null && ("candidate" in main) && main.candidate != null && ("src" in main.candidate))
    reserved.append([main.candidate.src, main.candidate.dst, ("kind" in main.candidate) ? main.candidate.kind : ""]);
  foreach (key, entry in this._railReadyStock) {
    if (key == ownPairKey || entry.candidate == null || !("src" in entry.candidate)) continue;
    reserved.append([entry.candidate.src, entry.candidate.dst, ("kind" in entry.candidate) ? entry.candidate.kind : ""]);
  }
  foreach (r in reserved) {
    if (AIMap.DistanceManhattan(candidate.src, r[0]) < ORIGIN_SEPARATION
        || AIMap.DistanceManhattan(candidate.src, r[1]) < ORIGIN_SEPARATION) return true;
    local shareDest = candidate.kind != "pax" && r[2] != "pax";
    if (shareDest && AIMap.DistanceManhattan(candidate.dst, r[1]) < ORIGIN_SEPARATION) continue;
    if (AIMap.DistanceManhattan(candidate.dst, r[0]) < ORIGIN_SEPARATION
        || AIMap.DistanceManhattan(candidate.dst, r[1]) < ORIGIN_SEPARATION) return true;
  }
  return false;
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
  if (this._v289EndpointTaken(candidate, null)) return false;
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

/* Bit 8 : phase d'expansion aerienne. Tant qu'une ville du premier quartile de
 * population n'est ni desservie par une de nos lignes AIR ni notee par un concurrent,
 * l'AIR a encore des villes a prendre : le rail attend. Recalcule une fois par mois.
 * Sans AIR, la porte est ouverte. */
function OpexAI::_v289AirPhaseOpen()
{
  if (!(V289_SLACK_WORKERS & 8) || !MODE_AIR) return false;
  local today = AIDate.GetCurrentDate();
  local stamp = AIDate.GetYear(today) * 12 + AIDate.GetMonth(today);
  if (this._v289PhaseMonth == stamp) return this._v289AirPhase;
  this._v289PhaseMonth = stamp;
  local airTiles = {};
  if (this._lines != null) {
    foreach (line in this._lines) {
      if (line == null || !("mode" in line) || line.mode != "air") continue;
      airTiles.rawset(line.originA, true);
      airTiles.rawset(line.originB, true);
    }
  }
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, false);
  local quartile = (towns.Count() + 3) / 4;
  local seen = 0, free = 0;
  foreach (town, pop in towns) {
    if (seen >= quartile) break;
    seen++;
    if (AITown.GetLocation(town) in airTiles) continue;
    local taken = false;
    for (local c = AICompany.COMPANY_FIRST; c <= AICompany.COMPANY_LAST && !taken; c++) {
      if (AICompany.ResolveCompanyID(c) == AICompany.COMPANY_INVALID) continue;
      if (AICompany.IsMine(c)) continue;
      if (AITown.GetRating(town, c) != AITown.TOWN_RATING_NONE) taken = true;
    }
    if (!taken) free++;
  }
  local phase = free > 0;
  if (DECISION_LOG && phase != this._v289AirPhase)
    OpexDecide("V289_PHASE", "air_phase=" + (phase ? 1 : 0) + " q1=" + quartile + " free=" + free);
  this._v289AirPhase = phase;
  return phase;
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
    this._railStockCooldown[pairKey] <- curDate + V289_STOCK_TTL_DAYS;
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
  if (this._v289RailSearch == null && this._v289AirPhaseOpen()) { this._v289RailWhy.air++; return false; }
  if (this._railReadyStock == null || this._catalog == null || this._lines == null) return false;
  local curDate = AIDate.GetCurrentDate();
  local slot = this._v289RailSearch;
  if (slot == null) {
    this._v289ExpireStock(curDate);
    if (this._railReadyStock.len() >= V289_STOCK_MAX) { this._v289RailWhy.full++; return false; }
    /* Un demarrage (quais + plans) coute ~190 k opcodes mesures : il franchit le
     * tick. Un seul essai par V289_RAIL_START_GAP_DAYS, reussi ou non. */
    if (this._v289RailStartDate >= 0 && curDate - this._v289RailStartDate < V289_RAIL_START_GAP_DAYS) {
      this._v289RailWhy.gap++;
      return false;
    }
    if (AIController.GetOpsTillSuspend() < V289_RAIL_START_MIN) { this._v289RailWhy.low++; return false; }
    local candidate = this._v289PickRailCandidate(curDate);
    if (candidate == null) { this._v289RailWhy.none++; return false; }
    this._v289RailStartDate = curDate;
    local startMark = OpexOpsMeasureBegin();
    local savedSearch = this._railSearch;
    local savedWorker = this._activeWorker;
    this._railSearch = null;
    local started = this._startRailStockSearch(candidate);
    this._v289RailSearch = started ? this._railSearch : null;
    this._railSearch = savedSearch;
    this._activeWorker = savedWorker;
    local startOps = OpexOpsMeasureEnd(startMark);
    if (DECISION_LOG) OpexDecide("V289_RAIL_START", "src=" + candidate.src + " dst=" + candidate.dst
        + " kind=" + candidate.kind + " ok=" + (started ? 1 : 0) + " ops=" + startOps
        + " budget=" + (started ? this._v289RailSearch.iterationBudget : 0));
    return started;
  }
  /* Le chantier reel a pris la meme paire : la preparation ne sert plus. */
  local c = slot.candidate;
  if (!this._v289RailPrepEligibleInFlight(c, curDate)) {
    this._v289RailSearch = null;
    if (DECISION_LOG) OpexDecide("V289_RAIL_DROP", "src=" + c.src + " dst=" + c.dst + " reason=taken_or_endpoint");
    return true;
  }
  local savedSearch = this._railSearch;
  local savedWorker = this._activeWorker;
  this._railSearch = slot;
  if (curDate - slot.startDate > V289_SEARCH_TTL_DAYS) {
    if (DECISION_LOG) OpexDecide("V289_RAIL_TIMEOUT", "src=" + c.src + " dst=" + c.dst + " iters=" + slot.spent);
    this._handleRailStockSearchTimeout();
  } else {
    if (slot.phase == "search") {
      /* Iterations que le reliquat paie au cout mesure d'une iteration, marge de 1 500. */
      local left = AIController.GetOpsTillSuspend() - 1500;
      local iters = (this._v289OpsPerIter > 0) ? left / this._v289OpsPerIter : 5;
      if (iters < 1) iters = 1;
      if (iters > RAIL_SEARCH_SLICE) iters = RAIL_SEARCH_SLICE;
      local spentBefore = slot.spent;
      local sliceMark = OpexOpsMeasureBegin();
      this._continueRailSearch(iters);
      local sliceOps = OpexOpsMeasureEnd(sliceMark);
      local done = slot.spent - spentBefore;
      if (done > 0) {
        local perIter = sliceOps / done;
        if (perIter < 20) perIter = 20;
        /* Moyenne glissante : un segment neuf coute plus que les iterations suivantes. */
        this._v289OpsPerIter = (this._v289OpsPerIter > 0) ? (this._v289OpsPerIter * 3 + perIter) / 4 : perIter;
      }
    }
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
  if (this._v289EndpointTaken(candidate, pairKey)) return false;
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

/* Maisons gagnees par 3 mois de FUND_BUILDINGS, d'apres GetNormalGrowthRate (town_cmd.cpp:3836-3859) :
 * intervalle m(gares actives n) >> 1 (town_growth_rate = 2), /2 pour une metropole, / (maisons/50 + 1),
 * en ticks de croissance (70 ticks de jeu, 74 par jour). n n'est pas expose : on retient celui dont
 * l'intervalle normal predit est le plus proche de GetGrowthRate. */
function OpexV289FundExtraHouses(townId)
{
  local houses = AITown.GetHouseCount(townId);
  local rate = AITown.GetGrowthRate(townId);
  if (houses <= 0 || rate <= 0) return 0.0;
  local normal = [320, 420, 300, 220, 160, 100];
  local funded = [120, 120, 120, 100, 80, 60];
  local div = houses / 50 + 1;
  local city = AITown.IsCity(townId);
  local best = -1, bestErr = 0, bestNormal = 0.0, bestFunded = 0.0;
  for (local n = 0; n < 6; n++) {
    local mn = normal[n] >> 1, mf = funded[n] >> 1;
    if (city) { mn /= 2; mf /= 2; }
    local dn = ((mn / div) + 1) * 70.0 / 74.0;
    local df = ((mf / div) + 1) * 70.0 / 74.0;
    local err = dn > rate ? dn - rate : rate - dn;
    if (best < 0 || err < bestErr) { best = n; bestErr = err; bestNormal = dn; bestFunded = df; }
  }
  /* Le financement ne descend pas sous une maison par 2 x 70 ticks (town_cmd.cpp:3564). */
  if (bestFunded < 140.0 / 74.0) bestFunded = 140.0 / 74.0;
  local extra = 90.0 / bestFunded - 90.0 / bestNormal;
  return extra > 0 ? extra : 0.0;
}

/* Bit 4 : au plus un financement par mois, dans la ville ou le gain predit est le plus grand,
 * seulement s'il couvre le cout sur V289_TOWN_HORIZON_YEARS. Pas de reserve de caisse (decision
 * utilisateur du 20/10) ; la caisse restante doit seulement couvrir le projet le plus cher encore
 * liste, pour ne jamais prendre l'argent d'un chantier du portefeuille. Zero achat est valide. */
function OpexAI::_v289StepTown()
{
  local today = AIDate.GetCurrentDate();
  local stamp = AIDate.GetYear(today) * 12 + AIDate.GetMonth(today);
  if (this._v289TownMonth == stamp) return false;
  this._v289TownMonth = stamp;
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) {
    if (DECISION_LOG) OpexDecide("V289_TOWN_SKIP", "reason=loan loan=" + loan);
    return false;
  }
  if (this._v289TownFundDate == null) this._v289TownFundDate = {};

  /* Recette annuelle de nos lignes voyageurs/courrier par ville : chaque extremite charge,
   * le profit de la ligne est partage entre ses deux villes. Le fret ne depend pas des maisons. */
  local byTown = {};
  if (this._lines != null) {
    foreach (line in this._lines) {
      if (line == null || (("kind" in line) && line.kind == "freight")) continue;
      local profit = OpexV249LineProfit(line);
      if (profit <= 0) continue;
      local towns = [];
      foreach (endName in ["A", "B"]) {
        local stationId = OpexLineStationId(line, endName);
        if (stationId < 0) continue;
        local townId = AIStation.GetNearestTown(stationId);
        if (AITown.IsValidTown(townId) && (towns.len() == 0 || towns[0] != townId)) towns.append(townId);
      }
      if (towns.len() == 0) continue;
      local share = profit / 2;
      foreach (townId in towns) {
        if (!(townId in byTown)) byTown[townId] <- 0;
        byTown[townId] += share;
      }
    }
  }

  local bestTown = -1, bestGain = 0, bestExtra = 0.0, bestProfit = 0;
  foreach (townId, profit in byTown) {
    if ((townId in this._v289TownFundDate) && (today - this._v289TownFundDate[townId] < 90)) continue;
    if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_FUND_BUILDINGS)) continue;
    local pop = AITown.GetPopulation(townId);
    local houses = AITown.GetHouseCount(townId);
    if (pop <= 0 || houses <= 0) continue;
    local extra = OpexV289FundExtraHouses(townId);
    local gain = (extra * pop / houses * profit / pop * V289_TOWN_CATCH_PCT / 100).tointeger();
    if (gain > bestGain) { bestTown = townId; bestGain = gain; bestExtra = extra; bestProfit = profit; }
  }
  if (bestTown < 0) {
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
  local value = bestGain * V289_TOWN_HORIZON_YEARS;
  local detail = "town=" + bestTown + " pop=" + AITown.GetPopulation(bestTown)
      + " houses=" + AITown.GetHouseCount(bestTown) + " rate=" + AITown.GetGrowthRate(bestTown)
      + " extra_houses=" + (bestExtra * 10).tointeger() / 10.0 + " profit=" + bestProfit
      + " gain_y=" + bestGain + " value=" + value + " cost=" + cost;
  if (value < cost) {
    if (DECISION_LOG) OpexDecide("V289_TOWN_SKIP", "reason=unprofitable " + detail);
    return false;
  }
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexV249MaxListedCapital(this._projects);
  if (cash - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V289_TOWN_SKIP", "reason=cash cash=" + cash + " threshold=" + threshold + " " + detail);
    return false;
  }
  if (!AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_FUND_BUILDINGS)) return false;
  this._v289TownFundDate[bestTown] <- today;
  if (DECISION_LOG) OpexDecide("V289_TOWN", "cash=" + cash + " threshold=" + threshold + " " + detail);
  return true;
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

  /* Un pas qui franchit le tick remet GetOpsTillSuspend() a plein : sans cette
   * borne, le repartiteur continuerait sur le budget du tick suivant. */
  local tick0 = AIController.GetTick();
  local idleCount = 0;
  while (AIController.GetTick() == tick0 && AIController.GetOpsTillSuspend() >= V289_SLACK_MIN) {
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

/* La passe principale choisit une paire que le reliquat cherche : elle prend son etat
 * (meme recherche segmentee, memes quais) dans le creneau principal. Sans cela, 12
 * recherches sur 17 etaient jetees au smoke v289g, la passe refaisant l'A* de zero. */
function OpexAI::_v289AdoptRailSearch(candidate, alternativeRatio, hardCap, posPacked)
{
  local slot = this._v289RailSearch;
  if (slot == null || this._railSearch != null || slot.phase != "search") return false;
  local c = slot.candidate;
  if (c == null || !("kind" in candidate) || !("cargo" in candidate)) return false;
  if (OpexProjectPairKey(c.kind, c.cargo, c.src, c.dst)
      != OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst)) return false;
  this._v289RailSearch = null;
  slot.candidate = candidate;
  slot.alternativeRatio = alternativeRatio;
  slot.hardCap = hardCap;
  slot.posPacked = posPacked;
  slot.isStockSearch = false;
  slot.safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS;
  if (!("slotIndex" in slot)) slot.slotIndex <- 0;
  candidate.searchWeight <- slot.weight;
  this._railSearch = slot;
  if (DECISION_LOG) OpexDecide("V289_RAIL_ADOPT", "src=" + candidate.src + " dst=" + candidate.dst
      + " iters=" + slot.spent + " days=" + (AIDate.GetCurrentDate() - slot.startDate));
  return true;
}
