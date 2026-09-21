/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexAI::_c63RecordPassAndProbe(builtCount, best, passDiscards, railSearching)
{
  if (!C63_INVEST_PROBE) return;
  OpexC63NotePass(builtCount, best, passDiscards, railSearching, this._projects);
  local kind = (C63_INVEST_LEDGER != null) ? C63_INVEST_LEDGER.lastKind : "";
  local emptyNow = (kind == "absent" || kind == "unaffordable");
  if (emptyNow && this._projects != null) {
    local curDate = AIDate.GetCurrentDate();
    local curMonth = AIDate.GetYear(curDate) * 12 + AIDate.GetMonth(curDate);
    if (this._lastBestCount > 0 || curMonth != this._lastEmptyProbeMonth) {
      this._lastEmptyProbeMonth = curMonth;
      local stage = ("generationStage" in this._projects && this._projects.generationStage != null)
          ? this._projects.generationStage : this._generationStage;
      local cargo = ("freightCargo" in this._projects && this._projects.freightCargo != null)
          ? this._projects.freightCargo : -1;
      OpexC63RecordEmptyProbe(this._projects, stage, cargo, this._abandonedPairs);
    }
  }
  this._lastBestCount = emptyNow ? 0 : 1;
}

function OpexAI::_recordMonthlyFunnelPass(builtCount, best, passDiscards, attempted)
{
  if (!MONTHLY_FUNNEL) return;
  local considered = -1;
  local accepted = 0;
  if (this._projects != null) {
    if (("stats" in this._projects) && this._projects.stats != null
        && ("budgetConsidered" in this._projects.stats)) {
      considered = this._projects.stats.budgetConsidered;
    }
    if (("best" in this._projects) && this._projects.best != null) {
      accepted = this._projects.best.len();
    } else if (best != null) {
      accepted = best.len();
    }
  } else if (best != null) {
    accepted = best.len();
  }
  local rejectFields = "";
  local cashRejects = 0;
  local rejectDetails = {};
  if (passDiscards != null) {
    local counts = {};
    for (local k = 0; k < passDiscards.len(); k++) {
      local reason = ("reason" in passDiscards[k]) ? passDiscards[k].reason : "unknown";
      if (reason == null || reason == "") reason = "unknown";
      if (reason in counts) counts[reason]++;
      else counts[reason] <- 1;
      if (reason == "insufficient_cash" || reason == "cash_at_build") cashRejects++;
      if ((reason == "build_failed" || reason == "plan_failed")
          && ("detail" in passDiscards[k]) && passDiscards[k].detail != null
          && passDiscards[k].detail != "") {
        local mode = ("mode" in passDiscards[k]) ? passDiscards[k].mode : "unknown";
        local detailKey = reason + "_" + mode + "_" + passDiscards[k].detail;
        if (detailKey in rejectDetails) rejectDetails[detailKey]++;
        else rejectDetails[detailKey] <- 1;
      }
      if (reason == "build_failed" && ("error" in passDiscards[k])
          && passDiscards[k].error != null && passDiscards[k].error != 0) {
        local mode = ("mode" in passDiscards[k]) ? passDiscards[k].mode : "unknown";
        local errorKey = "build_error_" + mode + "_" + passDiscards[k].error;
        if (errorKey in rejectDetails) rejectDetails[errorKey]++;
        else rejectDetails[errorKey] <- 1;
        /* C63/C58 : en duel partage, 771 == ERR_STATION_TOO_MANY_STATIONS_IN_TOWN.
         * Pour l'air, OpenTTD rattache la limite a la ville la plus proche de l'ANCRE physique
         * de l'aeroport, pas necessairement a la ville cible du plan. task_air calcule donc
         * error_town depuis siteA/siteB.anchor. Sonde pure, sous MONTHLY_FUNNEL. */
        if (mode == "air" && passDiscards[k].error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN
            && ("detail" in passDiscards[k])) {
          local ownAirports = ("error_own_airports" in passDiscards[k])
              ? passDiscards[k].error_own_airports : -1;
          if (ownAirports >= 0) {
            local ownKey = "build_error_air_own_airports_" + ownAirports;
            if (ownKey in rejectDetails) rejectDetails[ownKey]++;
            else rejectDetails[ownKey] <- 1;
          }
          local townTile = null;
          if (passDiscards[k].detail == "AFAIL" || passDiscards[k].detail == "PREA") {
            townTile = passDiscards[k].src;
          } else if (passDiscards[k].detail == "BFAIL" || passDiscards[k].detail == "PREB") {
            townTile = passDiscards[k].dst;
          }
          if (townTile != null) {
            local townKey = "build_error_air_town_limit_" + townTile;
            if (townKey in rejectDetails) rejectDetails[townKey]++;
            else rejectDetails[townKey] <- 1;
            local townId = ("error_town" in passDiscards[k]) ? passDiscards[k].error_town : -1;
            if (townId < 0) townId = AITile.GetClosestTown(townTile);
            if (townId >= 0) {
              local townIdKey = "build_error_air_town_id_" + townId;
              if (townIdKey in rejectDetails) rejectDetails[townIdKey]++;
              else rejectDetails[townIdKey] <- 1;
            }
          }
        }
      }
    }
    foreach (reason, n in counts) {
      rejectFields += " r_" + reason + "=" + n;
    }
    foreach (reason, n in rejectDetails) {
      rejectFields += " r_" + reason + "=" + n;
    }
  }
  local funded = attempted - cashRejects;
  if (funded < 0) funded = 0;
  OpexMonthlyFunnelLog("considered=" + considered + " accepted=" + accepted
      + " funded=" + funded + " attempted=" + attempted + " built=" + builtCount
      + rejectFields);
}

/* C38 etape 2 : une croissance de flotte est une tentative synchrone de portefeuille. */
function OpexAI::_tryBuildFleetProject(year, project, rank, passDiscards)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
  /* C34.2 : les gardes de refus ont deja ete franchies en mode a blanc ; il ne reste que le
   * test de tresorerie du portefeuille, sans droit de tirage anticipe. */
  local entry = project.payload;
  local line = entry.line;
  /* B8 / G10 : un projet flotte peut devenir stale entre son calcul (ou un cache portefeuille)
   * et son execution. Revalider ici, au dernier site avant OpexAirAddPlane, garantit qu'aucun
   * capital n'est depense sur une ligne qui a entre-temps commence sa liquidation. */
  if (line == null || (("scrapping" in line) && line.scrapping)) {
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
      passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst,
                            reason = "line_scrapping", extra = "" });
    }
    if (DECISION_LOG) {
      OpexDecide("FLEET_PROJECT", "action=refuse line="
                 + ((line != null && ("lineId" in line)) ? line.lineId : -1)
                 + " reason=scrapping");
    }
    return { outcome = "rejected", discards = passDiscards };
  }
  local need = entry.planePrice + OpexCashReserve();
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need && REBORROW) money = OpexTryReborrow(need, money);
  if (money < need) {
    if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("fleet", i, project.capital, project.profitAnnual, project.roi, project.src, project.dst, need, money);
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst, reason = "insufficient_cash", extra = "" });
    return { outcome = "rejected", discards = passDiscards };
  }
  local plannedFull = ("capital" in project && project.capital > 0)
      ? project.capital : (entry.planePrice * entry.want);
  local costs = C63_INVEST_PROBE ? AIAccounting() : null;
  local added = 0;
  for (local k = 0; k < entry.want; k++) {
    local grown = OpexAirAddPlane(line);
    if (grown.added <= 0) break;
    added += grown.added;
    local haveNow = (("vehCount" in line) ? line.vehCount : 0) + grown.added;
    line.vehCount <- haveNow;
    line.trains = haveNow;
    if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < need) break;
  }
  local actual = (costs != null) ? costs.GetCosts() : 0;
  if (added <= 0) {
    if (C63_INVEST_PROBE) OpexC63RecordSpend("fleet", plannedFull, actual, false);
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
      passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst, reason = "fleet_grow_failed", extra = "" });
    }
    return { outcome = "rejected", discards = passDiscards };
  }
  if (C63_INVEST_PROBE) {
    local plannedAdded = entry.planePrice * added;
    if (plannedAdded > plannedFull) plannedAdded = plannedFull;
    OpexC63RecordSpend("fleet", plannedAdded, actual, true);
    local missed = plannedFull - plannedAdded;
    if (missed > 0) OpexC63RecordSpend("fleet", missed, 0, false);
  }

  line.lastAirFleetYear <- year;
  line.lastAirFleetDate <- AIDate.GetCurrentDate();
  if (C50_CHRONOLOGY_PROBE) {
    OpexC50ChronologyLog("phase=fleet_built mode=air line=" + line.lineId
        + " added=" + added + " total=" + line.vehCount + " want=" + entry.want
        + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
  }
  if (DECISION_LOG) {
    OpexDecide("FLEET_PROJECT", "action=grow line=" + line.lineId + " added=" + added
               + " want=" + entry.want + " price=" + entry.planePrice
               + " profit=" + project.profitAnnual + " roi=" + project.roi);
  }
  AILog.Info("[FLEET_PROJECT] line=" + line.lineId + " added=" + added);
  return { outcome = "built", discards = passDiscards };
}
function OpexAI::_refreshDynamicBatch()
{
  local capitalNow = OpexAvailableCapital();
  this._projects = OpexDynamicBatchReselect(this._projects, this._lines,
      this._dynamicBatch.attempted, capitalNow, this._abandonedPairs);
  this._ranked = this._projects.rail;
  local remaining = this._projects.best.len();
  if (DECISION_LOG) {
    OpexDecide("DYNAMIC_BATCH", "action=continue reason=success built="
               + this._dynamicBatch.built + " attempted=" + this._dynamicBatch.attemptedCount
               + " budget_current=" + capitalNow
               + " remaining=" + remaining);
  }
}
function OpexAI::_dynamicBatchBuilt()
{
  this._dynamicBatch.built++;
  this._dynamicBatch.consecutiveRejects = 0;
  this._refreshDynamicBatch();
}
/* P2 : seul un refus effectivement tente compte. Une recherche rail pending
 * rend la main sans appeler ce helper ; un succes remet la serie a zero. */
function OpexAI::_dynamicBatchRejected()
{
  if (!PORTFOLIO_DYNAMIC_BATCH || this._dynamicBatch == null) return false;
  this._dynamicBatch.consecutiveRejects++;
  if (DYNAMIC_BATCH_REJECT_LIMIT > 0
      && this._dynamicBatch.consecutiveRejects >= DYNAMIC_BATCH_REJECT_LIMIT) {
    this._dynamicBatch.stopReason = "consecutive_rejects";
    return true;
  }
  return false;
}
function OpexAI::_stopDynamicBatch(reason, year)
{
  if (!PORTFOLIO_DYNAMIC_BATCH || this._dynamicBatch == null) return;
  local after = OpexAvailableCapital();
  local remaining = (this._projects != null && ("best" in this._projects))
      ? this._projects.best.len() : 0;
  if (DECISION_LOG) {
    OpexDecide("DYNAMIC_BATCH", "action=stop reason=" + reason + " built="
               + this._dynamicBatch.built + " attempted=" + this._dynamicBatch.attemptedCount
               + " rejects=" + this._dynamicBatch.consecutiveRejects
               + " ops_floor=" + this._dynamicBatch.opsFloor
               + " budget_before=" + this._dynamicBatch.initialBudget + " budget_after=" + after
               + " remaining=" + remaining);
  }
  local built = this._dynamicBatch.built;
  if (this._projects != null) {
    if (this._dynamicBatch.sourceCandidateGroups != null) {
      this._projects.candidateGroups = this._dynamicBatch.sourceCandidateGroups;
    }
  }
  this._dynamicBatch = null;
  /* Le filtre attempted mutile volontairement le vivier de travail. Une reconstruction
   * incrementale unique a la cloture restaure les candidats encore valides pour le cycle
   * suivant, sans liste noire persistante. */
  if (built > 0 && this._projects != null) {
    local fleetPlan = null;
    if (FLEET_PORTFOLIO) {
      fleetPlan = [];
      this._resizeAirFleets(year, fleetPlan);
    }
    this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget,
        this._lines, OpexAvailableCapital(), fleetPlan, this._abandonedPairs);
    this._ranked = this._projects.rail;
  }
}
/* C39.5 : conserve, par cle stable, le premier jour de la fenetre courante ou un projet du
 * vivier est finançable. La table neuve purge les projets sortis du vivier et borne la memoire.
 *
 * C39.5b : chaque valeur est desormais une table {since, topSince, turns, topTurns} au lieu
 * d'une date seule, pour separer les trois causes du delai D2 (cadence / file par rang /
 * concurrence caisse) :
 *   - since    : date du premier jour finançable (comportement d'origine, inchange) ;
 *   - topSince : date du premier jour ou ce projet etait le MEILLEUR projet finançable, i.e. le
 *                premier de this._projects.best (indice le plus bas) dont capital <= available ;
 *                -1 tant qu'il ne l'a jamais ete. Meme definition que bestRank de C41.48
 *                (C41_RAIL_DOMINATION_PROBE) : rester comparable entre les deux sondes ;
 *   - turns / topTurns : nombre de dispatches de la tache `projects` observes depuis since /
 *                topSince. Incrementes uniquement quand isProjectsTurn est vrai, pour ne compter
 *                que les tours de `projects` et pas l'appel fait depuis la tache `catalog`
 *                (qui, lui, ne fait qu'horodater since/topSince avant le premier tour utile).
 *
 * capital : optionnel. L'appelant du site de dispatch de `projects` a deja calcule
 * OpexAvailableCapital() pour sa propre ligne de journal (capital=) ; le lui laisser passer evite
 * de le recalculer ici. L'appel depuis la tache `catalog` (qui n'emet aucun log) continue de le
 * calculer lui-meme en laissant capital a null. */
function OpexAI::_c39StampFinanceable(capital = null, isProjectsTurn = false)
{
  if (!C39_PROJECTS_CADENCE_PROBE) return 0;
  local available = (capital != null) ? capital : OpexAvailableCapital();
  local date = AIDate.GetCurrentDate();
  local stamped = {};
  local topFound = false;
  if (this._projects != null && this._projects.best != null) {
    local limit = this._projects.best.len() < 64 ? this._projects.best.len() : 64;
    for (local i = 0; i < limit; i++) {
      local project = this._projects.best[i];
      if (project == null || project.capital > available) continue;
      local isTop = !topFound;
      topFound = true;
      local key = OpexProjectAttemptKey(project);
      local prev = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
      local since = (prev != null) ? prev.since : date;
      local topSince = (prev != null) ? prev.topSince : -1;
      if (isTop && topSince == -1) topSince = date;
      local turns = (prev != null) ? prev.turns : 0;
      local topTurns = (prev != null) ? prev.topTurns : 0;
      if (isProjectsTurn) {
        turns++;
        if (isTop) topTurns++;
      }
      stamped[key] <- { since = since, topSince = topSince, turns = turns, topTurns = topTurns };
    }
  }
  this._c39FinanceableSince = stamped;
  return stamped.len();
}
function OpexAI::_tryBuildProjects(year)
{
  local c75KPassData = null;
  local c75StopReason = null;
  local c75BuiltKeys = {};
  if (C75_TRACK_PASSES) {
    local now = AIDate.GetCurrentDate();
    OpexC75RecordPassDate(now);
    c75KPassData = OpexC75ComputeKPass(now);
    if (C75_YEAR_LEDGER != null) C75_YEAR_LEDGER.passes++;
  }
  local c73Cash = 0;
  local c73Avail = 0;
  if (C69_BOTTLENECK_PROBE) {
    c73Cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    c73Avail = OpexAvailableCapital();
  }
  local c49Best = null;
  local c49BuiltRanks = null;
  local c49AttemptedRanks = null;
  /* C38 : l'etat ne nait que pour le bras experimental. Il survivra a un A* suspendu ; le
   * bras livre ne fait aucune allocation ni lecture supplementaire. */
  if (PORTFOLIO_DYNAMIC_BATCH && this._dynamicBatch == null) {
    this._dynamicBatch = {
      attempted = {}, attemptedCount = 0, built = 0,
      consecutiveRejects = 0,
      initialBudget = OpexAvailableCapital(), opsFloor = DYNAMIC_BATCH_OPS_FLOOR,
      stopReason = null, pendingLogged = false,
      sourceCandidateGroups = (this._projects != null && ("candidateGroups" in this._projects))
          ? this._projects.candidateGroups : null,
    };
  }
  /* G4§1 : le drapeau peut etre pose entre deux passes par _consumeRailSearch.
   * Ne pas le remettre a zero ici : la passe suivante doit alors re-elire le
   * portefeuille avec la nouvelle memoire d'abandon. */
  if (PORTFOLIO_FRESH_BUDGET && this._projects != null) {
    local initialBudget = this._projects.generationCapitalBudget;
    local budgetNow = OpexAvailableCapital();
    this._projects = OpexReselectProjects(this._projects, budgetNow);
    /* 30 caracteres au pire : FB|99|2147483647|2147483647|64. */
    OpexSign(AIMap.GetTileIndex(1, 1), "FB|" + (year % 100) + "|" + initialBudget
             + "|" + budgetNow + "|" + this._projects.stats.budgetSelected);
  }
  c49Best = (this._projects != null && this._projects.best != null) ? this._projects.best : null;
  if (C49_SCARCITY_LEDGER) {
    c49BuiltRanks = {};
    c49AttemptedRanks = {};
  }
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  local builtCount = 0;
  local funnelAttempted = 0;
  local passDiscards = [];
  local c69BuiltProjects = C69_TRACK_BUILDS ? [] : null;
  local c69PassProjects = null;
  if (C69_BOTTLENECK_PROBE && this._projects != null) {
    /* Instantane : OpexReselectProjects remplace projects.best en place pendant la passe. */
    c69PassProjects = {
      best = ("best" in this._projects) ? this._projects.best : null,
      c69Best = ("c69Best" in this._projects) ? this._projects.c69Best : null,
      c69KDecData = ("c69KDecData" in this._projects) ? this._projects.c69KDecData : null
    };
  }
  /* P2 : fractionner le tick. Le plancher historique protege toujours les
   * autres taches quand le pourcentage est nul ou que le tick est deja court. */
  local dynamicOpsFloor = DYNAMIC_BATCH_OPS_FLOOR;
  if (PORTFOLIO_DYNAMIC_BATCH && DYNAMIC_BATCH_OPS_BUDGET_PCT > 0) {
    local opsNow = AIController.GetOpsTillSuspend();
    local reserved = (opsNow * (100 - DYNAMIC_BATCH_OPS_BUDGET_PCT)) / 100;
    if (reserved > dynamicOpsFloor) dynamicOpsFloor = reserved;
  }
  if (PORTFOLIO_DYNAMIC_BATCH) this._dynamicBatch.opsFloor = dynamicOpsFloor;
  /* 1 conserve le break historique. Au-dela, chaque candidat apres le premier succes passe les
   * revalidations de son mode contre this._lines, la carte et la tresorerie vivantes. */
  local maxBatch = PORTFOLIO_MAX_BATCH;

  /* C41.49 : meme garde que C41.48 (kind=="primary", phase=="search") -- la sonde ne regarde
   * que la fenetre ou l'A* rail est en vol, pas la phase "build" (deja couverte par
   * _consumeRailSearch/C41.47) ni un upgrade. Rien n'est coupe : fallthroughAttempted/Built
   * comptent ce que la boucle ci-dessous fait DEJA des candidats non-rail. */
  local fallthroughProbeActive = C41_PROJECTS_FALLTHROUGH_PROBE && this._railSearch != null
      && this._railSearch.kind == "primary" && this._railSearch.phase == "search";
  local fallthroughAttempted = 0;
  local fallthroughBuilt = 0;
  if (fallthroughProbeActive) {
    OpexC41ProjectsFallthroughLog("phase=entry invalidated="
        + (this._portfolioInvalidated ? 1 : 0) + " best_len="
        + ((this._projects != null) ? this._projects.best.len() : -1));
  }

  /* A4 : un A* termine au tour precedent a depose un railPlan sur le candidat stocke. On le
   * consomme AVANT le balayage du portefeuille, qui a pu etre regenere entre-temps. */
  if (PORTFOLIO_DYNAMIC_BATCH && RAIL_SEARCH_RESUMABLE && this._railSearch != null &&
      this._railSearch.kind == "primary" && this._railSearch.phase != "build") {
    if (DECISION_LOG && !this._dynamicBatch.pendingLogged) {
      this._dynamicBatch.pendingLogged = true;
      OpexDecide("DYNAMIC_BATCH", "action=stop reason=rail_pending built="
                 + this._dynamicBatch.built + " attempted=" + this._dynamicBatch.attemptedCount
                 + " budget_before=" + this._dynamicBatch.initialBudget + " budget_after="
                 + OpexAvailableCapital() + " remaining=" + this._projects.best.len());
    }
    if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
    if (C63_INVEST_PROBE) this._c63RecordPassAndProbe(0, c49Best, passDiscards, true);
    if (C69_BOTTLENECK_PROBE) {
      local empty = (c49Best == null || c49Best.len() == 0);
      OpexC73RecordPass(false, empty, c73Cash, c73Avail);
    }
    this._recordMonthlyFunnelPass(0, c49Best, passDiscards, funnelAttempted);
    return true;
  }
  if (RAIL_SEARCH_RESUMABLE && this._railSearch != null &&
      this._railSearch.kind == "primary" && this._railSearch.phase == "build") {
    local railCandidate = this._railSearch.candidate;
    local railResult = this._consumeRailSearch(year);
    local outcome = railResult.outcome;
    if (MONTHLY_FUNNEL) funnelAttempted++;
    if ((outcome == "failed" || outcome == "cash")
        && (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL)) {
      local failRank = -1;
      if (this._projects != null && this._projects.best != null) {
        local failKey = "rail|" + railCandidate.src + "|" + railCandidate.dst + "|"
            + railCandidate.cargo + "|" + railCandidate.kind;
        for (local i = 0; i < this._projects.best.len(); i++) {
          local project = this._projects.best[i];
          if (project != null && OpexProjectAttemptKey(project) == failKey) {
            failRank = i;
            break;
          }
        }
      }
      passDiscards.append({ rank = failRank, mode = "rail", src = railCandidate.src,
                            dst = railCandidate.dst, reason = railResult.reason,
                            extra = "", error = railResult.error });
    }
    /* Atteignable seulement avec portfolio_dynamic_batch=1 (non-defaut) : conserver le ledger. */
    if (PORTFOLIO_DYNAMIC_BATCH && outcome == "cash") {
      if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
      if (C63_INVEST_PROBE) this._c63RecordPassAndProbe(0, c49Best, passDiscards, false);
      if (C69_BOTTLENECK_PROBE) {
        local empty = (c49Best == null || c49Best.len() == 0);
        OpexC73RecordPass(false, empty, c73Cash, c73Avail);
      }
      this._recordMonthlyFunnelPass(0, c49Best, passDiscards, funnelAttempted);
      return true;
    }
    if (outcome != "cash") {
      if (C39_PROJECTS_CADENCE_PROBE && outcome == "built") {
        /* railCandidate est le payload brut, pas le projet : il n'a pas de slot mode, donc
         * OpexProjectAttemptKey() produirait la cle incompatible unknown|... au lieu de rail|.... */
        local key = "rail|" + railCandidate.src + "|" + railCandidate.dst + "|"
            + railCandidate.cargo + "|" + railCandidate.kind;
        local railRank = -1;
        if (this._projects != null && this._projects.best != null) {
          for (local i = 0; i < this._projects.best.len(); i++) {
            local project = this._projects.best[i];
            if (project != null && OpexProjectAttemptKey(project) == key) {
              railRank = i;
              break;
            }
          }
        }
        /* C39.5b : meme forme d'entry que les 5 sites generiques ; la cle reste construite a la
         * main (commentaire ci-dessus), seul le contenu lu change. */
        local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
        local daysSinceFinanceable = (entry != null)
            ? AIDate.GetCurrentDate() - entry.since : -1;
        local daysSinceTop = (entry != null && entry.topSince != -1)
            ? AIDate.GetCurrentDate() - entry.topSince : -1;
        local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
        local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
        OpexC39ProjectsCadenceLog("phase=built mode=rail rank=" + railRank
            + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
            + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
            + " rail_search=1 capital_after=" + OpexAvailableCapital());
      }
      local c49RailCandidate = C49_SCARCITY_LEDGER ? railCandidate : null;
      if (PORTFOLIO_DYNAMIC_BATCH) this._dynamicBatch.pendingLogged = false;
      this._railSearch = null;
      if (outcome == "built") {
        builtCount++;
        if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(railCandidate)] <- true;
        if (C69_TRACK_BUILDS) c69BuiltProjects.append(railCandidate);
        if (C50_CHRONOLOGY_PROBE && railCandidate != null) {
          local railRank = -1;
          if (this._projects != null && this._projects.best != null) {
            local key = "rail|" + railCandidate.src + "|" + railCandidate.dst + "|"
                + railCandidate.cargo + "|" + railCandidate.kind;
            for (local i = 0; i < this._projects.best.len(); i++) {
              local project = this._projects.best[i];
              if (project != null && OpexProjectAttemptKey(project) == key) {
                railRank = i;
                break;
              }
            }
          }
          local railCost = ("capital" in railCandidate) ? railCandidate.capital : 0;
          local railProf = ("profitAnnual" in railCandidate) ? railCandidate.profitAnnual : 0;
          local railRoi = ("roi" in railCandidate) ? railCandidate.roi : 0;
          OpexC50ChronologyLog("phase=project_built mode=rail rank=" + railRank + " line=" + (this._nextLineId - 1)
              + " cost=" + railCost + " profit=" + railProf + " roi=" + railRoi
              + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
              + " available=" + OpexAvailableCapital());
        }
        if (C49_SCARCITY_LEDGER && c49Best != null) {
          local railCandidate = c49RailCandidate;
          for (local i = 0; i < c49Best.len(); i++) {
            local project = c49Best[i];
            if (project != null && project.mode == "rail" && project.payload.src == railCandidate.src
                && project.payload.dst == railCandidate.dst && project.payload.cargo == railCandidate.cargo
                && project.payload.kind == railCandidate.kind) {
              c49BuiltRanks.rawset(i, true);
              break;
            }
          }
        }
        if (PORTFOLIO_DYNAMIC_BATCH) this._dynamicBatchBuilt();
      } else if (PORTFOLIO_DYNAMIC_BATCH && outcome == "failed") {
        this._dynamicBatchRejected();
      }
    }
  }

  if ((PORTFOLIO_DYNAMIC_BATCH || C75_MULTI_BUILD || builtCount < maxBatch)
      && this._projects != null && this._projects.best.len() > 0
      && (!PORTFOLIO_DYNAMIC_BATCH || this._dynamicBatch.stopReason == null)) {
  local logDiscardsThisPass = false;
  /* Le calcul du mois courant coute DEUX appels d'API et tournait a chaque passage, reglage
   * eteint compris. Ici le comportement depend des opcodes consommes : tout ce qui ne sert
   * qu'a journaliser doit vivre DANS la garde, pas seulement l'appel a OpexDecide. */
  if (DECISION_LOG) {
    local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
    if (_lastProjectScanMonth != ym) {
      _lastProjectScanMonth = ym;
      logDiscardsThisPass = true;
    }
  }
  for (local i = 0; i < this._projects.best.len(); i++) {
    local project = this._projects.best[i];
    if (project == null) continue;

    if (C75_MULTI_BUILD && (OpexC69AttemptKey(project) in c75BuiltKeys)) continue;

    if (C75_MULTI_BUILD && builtCount > 0) {
      local projCap = OpexProjectFinanceCapital(project);
      local c75KPass = (c75KPassData != null) ? c75KPassData.K_pass : 0;
      if (projCap >= c75KPass) {
        c75StopReason = "k_pass";
        break;
      }
      local availCap = OpexAvailableCapital();
      if (projCap > availCap) {
        c75StopReason = "cash";
        break;
      }
    }

    if (PORTFOLIO_DYNAMIC_BATCH) {
      if (AIController.GetOpsTillSuspend() < dynamicOpsFloor) {
        this._dynamicBatch.stopReason = "opcode_budget";
        break;
      }
      local projectKey = OpexProjectAttemptKey(project);
      if (projectKey in this._dynamicBatch.attempted) continue;
      this._dynamicBatch.attempted[projectKey] <- true;
      this._dynamicBatch.attemptedCount++;
    }

    local mode = project.mode;
    local modeChar = mode == "rail" ? "T" : (mode == "road" ? "R" : (mode == "air" ? "A" : "W"));
    local liveBuiltCount = PORTFOLIO_DYNAMIC_BATCH ? this._dynamicBatch.built : builtCount;
    if (MONTHLY_FUNNEL) funnelAttempted++;

    if (mode == "fleet") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local attempt = this._tryBuildFleetProject(year, project, i, passDiscards);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        if (C50_CHRONOLOGY_PROBE) {
          local lineId = ("payload" in project && "line" in project.payload && "lineId" in project.payload.line) ? project.payload.line.lineId : -1;
          OpexC50ChronologyLog("phase=project_built mode=fleet rank=" + i + " line=" + lineId
              + " cost=" + project.capital + " profit=" + project.profitAnnual + " roi=" + project.roi
              + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
              + " available=" + OpexAvailableCapital());
        }
        builtCount++;
        if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(project)] <- true;
        if (C69_TRACK_BUILDS) c69BuiltProjects.append(project);
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt();
          i = -1;
        } else if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
      continue;
    }

    if (mode == "air") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local attempt = this._tryBuildAirProject(year, project, i, liveBuiltCount, passDiscards,
                                                anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        if (C50_CHRONOLOGY_PROBE) {
          OpexC50ChronologyLog("phase=project_built mode=air rank=" + i + " line=" + (this._nextLineId - 1)
              + " cost=" + project.capital + " profit=" + project.profitAnnual + " roi=" + project.roi
              + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
              + " available=" + OpexAvailableCapital());
        }
        builtCount++;
        if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(project)] <- true;
        if (C69_TRACK_BUILDS) c69BuiltProjects.append(project);
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt();
          i = -1;
        } else if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    } else if (mode == "road") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local attempt = this._tryBuildRoadProject(year, project, i, passDiscards, anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        if (C50_CHRONOLOGY_PROBE) {
          OpexC50ChronologyLog("phase=project_built mode=road rank=" + i + " line=" + (this._nextLineId - 1)
              + " cost=" + project.capital + " profit=" + project.profitAnnual + " roi=" + project.roi
              + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
              + " available=" + OpexAvailableCapital());
        }
        builtCount++;
        if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(project)] <- true;
        if (C69_TRACK_BUILDS) c69BuiltProjects.append(project);
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt();
          i = -1;
        } else if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    } else if (mode == "rail") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local attempt = this._tryBuildRailProject(year, project, i, liveBuiltCount, passDiscards,
                                                 anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (attempt.outcome == "pending") {
        /* En batch historique > 1, le portefeuille doit etre regenere avant de reprendre un
         * A* suspendu. Le defaut unitaire conserve le retour immediat d'origine. */
        if (!PORTFOLIO_DYNAMIC_BATCH && builtCount > 0) {
          if (C75_TRACK_PASSES) c75StopReason = "rail_search";
          break;
        }
        if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
        if (C63_INVEST_PROBE) {
          local railSearching = this._railSearch != null && this._railSearch.phase == "search";
          this._c63RecordPassAndProbe(builtCount, c49Best, passDiscards, railSearching);
        }
        if (C69_BOTTLENECK_PROBE) {
          local built = builtCount > 0 || (PORTFOLIO_DYNAMIC_BATCH && this._dynamicBatch != null && this._dynamicBatch.built > 0);
          local empty = (c49Best == null || c49Best.len() == 0);
          OpexC73RecordPass(built, empty, c73Cash, c73Avail);
        }
        this._recordMonthlyFunnelPass(builtCount, c49Best, passDiscards, funnelAttempted);
        if (C75_TRACK_PASSES && builtCount > 0) {
          OpexC75RecordPassOutcome(year, builtCount, c75KPassData, "rail_search");
        }
        return true;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        if (C50_CHRONOLOGY_PROBE) {
          OpexC50ChronologyLog("phase=project_built mode=rail rank=" + i + " line=" + (this._nextLineId - 1)
              + " cost=" + project.capital + " profit=" + project.profitAnnual + " roi=" + project.roi
              + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
              + " available=" + OpexAvailableCapital());
        }
        builtCount++;
        if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(project)] <- true;
        if (C69_TRACK_BUILDS) c69BuiltProjects.append(project);
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt();
          i = -1;
        } else if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    } else if (mode == "water") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local attempt = this._tryBuildWaterProject(year, project, i, liveBuiltCount, passDiscards,
                                                  anchor, yy);
      passDiscards = attempt.discards;
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (C39_PROJECTS_CADENCE_PROBE) {
          local key = OpexProjectAttemptKey(project);
          /* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
           * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse. */
          local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
          local daysSinceFinanceable = (entry != null)
              ? AIDate.GetCurrentDate() - entry.since : -1;
          local daysSinceTop = (entry != null && entry.topSince != -1)
              ? AIDate.GetCurrentDate() - entry.topSince : -1;
          local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
          local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
          OpexC39ProjectsCadenceLog("phase=built mode=" + project.mode + " rank=" + i
              + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
              + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
              + " rail_search=" + (this._railSearch != null ? 1 : 0) + " capital_after=" + OpexAvailableCapital());
        }
        if (C50_CHRONOLOGY_PROBE) {
          OpexC50ChronologyLog("phase=project_built mode=water rank=" + i + " line=" + (this._nextLineId - 1)
              + " cost=" + project.capital + " profit=" + project.profitAnnual + " roi=" + project.roi
              + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
              + " available=" + OpexAvailableCapital());
        }
        builtCount++;
        if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(project)] <- true;
        if (C69_TRACK_BUILDS) c69BuiltProjects.append(project);
        if (PORTFOLIO_DYNAMIC_BATCH) {
          this._dynamicBatchBuilt();
          i = -1;
        } else if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      } else if (PORTFOLIO_DYNAMIC_BATCH && attempt.outcome == "rejected"
                 && this._dynamicBatchRejected()) {
        break;
      }
    }
  }
  if (fallthroughProbeActive) {
    OpexC41ProjectsFallthroughLog("phase=exit invalidated="
        + (this._portfolioInvalidated ? 1 : 0) + " attempted=" + fallthroughAttempted
        + " built=" + fallthroughBuilt);
  }
  if (DECISION_LOG && builtCount == 0 && logDiscardsThisPass && passDiscards.len() > 0) {
    local maxLog = passDiscards.len() < 3 ? passDiscards.len() : 3;
    for (local k = 0; k < maxLog; k++) {
      local d = passDiscards[k];
      OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
    }
  }
  }

  if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
  if (C63_INVEST_PROBE) {
    local railSearching = this._railSearch != null && this._railSearch.phase == "search";
    this._c63RecordPassAndProbe(builtCount, c49Best, passDiscards, railSearching);
  }
  if (C69_BOTTLENECK_PROBE) {
    local built = builtCount > 0 || (PORTFOLIO_DYNAMIC_BATCH && this._dynamicBatch != null && this._dynamicBatch.built > 0);
    local empty = (c49Best == null || c49Best.len() == 0);
    OpexC73RecordPass(built, empty, c73Cash, c73Avail);
  }
  this._recordMonthlyFunnelPass(builtCount, c49Best, passDiscards, funnelAttempted);
  if (C69_TRACK_BUILDS && (builtCount > 0 || (PORTFOLIO_DYNAMIC_BATCH && this._dynamicBatch != null && this._dynamicBatch.built > 0))) {
    this._recordC69BuildingPass(year, c69PassProjects != null ? c69PassProjects : this._projects, c69BuiltProjects);
  }
  if (C75_TRACK_PASSES) {
    if (builtCount > 0 && c75StopReason == null) {
      c75StopReason = (!C75_MULTI_BUILD) ? "single" : "list_end";
    }
    OpexC75RecordPassOutcome(year, builtCount, c75KPassData, c75StopReason);
  }

  /* G4§1 : l'ancien chemin deduisait hadAbandons de passDiscards, dont le remplissage
   * est garde par DECISION_LOG (defaut 0). Le drapeau _hadAbandonsThisPass est pose
   * directement par _markPairAbandoned, couvrant tous les chemins (air, route, rail
   * bloquant et reprenable via _consumeRailSearch). */
  local hadAbandons = this._hadAbandonsThisPass;
  local batchBuilt = PORTFOLIO_DYNAMIC_BATCH && this._dynamicBatch != null
      ? this._dynamicBatch.built : builtCount;

  if (builtCount > 0 || hadAbandons || batchBuilt > 0) {
    local fleetPlan = null;
    if (!PORTFOLIO_DYNAMIC_BATCH && FLEET_PORTFOLIO) {
      /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
      fleetPlan = [];
      this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    }
    if (PORTFOLIO_DYNAMIC_BATCH && batchBuilt > 0) {
      /* Chaque succes a deja filtre et re-classe sur le budget vivant. */
    } else if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      local c76StartDay = C39_INVALIDATION_PROBE ? AIDate.GetCurrentDate() : 0;
      this._rebuildProjects(fleetPlan);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = AIDate.GetCurrentDate() - c76StartDay;
        this._c76RecordRegen("full", c76Ops, c76Days, year);
      }
    } else if (PORTFOLIO_CACHE && this._projects != null && ("candidateGroups" in this._projects)) {
      local budgetNow = OpexAvailableCapital();
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      local c76StartDay = C39_INVALIDATION_PROBE ? AIDate.GetCurrentDate() : 0;
      this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = AIDate.GetCurrentDate() - c76StartDay;
        this._c76RecordRegen("incremental", c76Ops, c76Days, year);
      }
    } else {
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      local c76StartDay = C39_INVALIDATION_PROBE ? AIDate.GetCurrentDate() : 0;
      this._rebuildProjects(fleetPlan);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = AIDate.GetCurrentDate() - c76StartDay;
        this._c76RecordRegen("full", c76Ops, c76Days, year);
      }
    }
    this._ranked = this._projects.rail;
    if (PORTFOLIO_LOG) OpexLogPortfolioRank(this._projects);
    /* Champ knapsackExact legacy : aucun solveur knapsack/B&B n'existe encore. projects.nut
     * le force donc a false afin que ce panneau ne publie jamais un « optimum prouve » fictif.
     * Le slot est conserve pour compatibilite des parseurs de panneaux existants. */
    /* H5 : meme schema IG que le chemin scheduler. Le cout de selection est
     * publie en milliers d'opcodes, sans nouveau panneau. */
    OpexSign(anchor, "IG|" + yy + "|" + this._projects.stats.modeCandidates + "|"
             + this._projects.stats.odProjects + "|" + this._projects.stats.budgetSelected
             + "|" + (this._projects.stats.knapsackExact ? 0 : 1)
             + "|" + this._budget.nested + "|" + (this._projects.stats.selectionOpcodes / 1000));
    /* M1 : le 3e champ historique est le capital du POOL de selection (jusqu'a PROJECT_TOP_K),
     * pas un engagement de depense. Sa position reste intacte pour les parseurs historiques.
     * B est le nombre reellement construit dans CE passage. */
    OpexSign(anchor, "IB|" + yy + "|" + this._projects.capitalBudget + "|"
             + this._projects.stats.selectedCapital + "|B" + batchBuilt);
    /* L'abandon a maintenant ete consomme par la reelection/reconstruction. */
    if (hadAbandons) this._hadAbandonsThisPass = false;
    if (PORTFOLIO_DYNAMIC_BATCH) {
      local reason = this._dynamicBatch.stopReason != null
          ? this._dynamicBatch.stopReason : "no_financeable";
      this._stopDynamicBatch(reason, year);
    }
    return true;
  }
  if (PORTFOLIO_DYNAMIC_BATCH) {
    local reason = this._dynamicBatch.stopReason != null
        ? this._dynamicBatch.stopReason : "no_success";
    this._stopDynamicBatch(reason, year);
  }
  return false;
}
function OpexAI::_rebuildProjects(fleetPlan)
{
  /* B6/06.11 : conserver le vivier cache uniquement comme oracle passif. Le
   * rebuild normal reste l'unique producteur du nouveau portefeuille. */
  local b6StaleProjects = (DECISION_LOG && PORTFOLIO_CACHE) ? this._projects : null;
  local b6StaleDate = AIDate.GetCurrentDate();
  local stage = OPEX_STAGE_COMPLETE;
  local prior = null;
  if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
    stage = this._generationStage;
    prior = this._projects;
    if (this._generationStageMonth < 0) {
      local date = AIDate.GetCurrentDate();
      this._generationStageMonth = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
    }
  }
  local freightCargo = null;
  local freightCargos = OpexFreightCargoOrder(this._catalog);
  if (freightCargos.len() > 0) {
    if (stage > OPEX_STAGE_AIR_ONLY && stage <= OPEX_STAGE_ROUTE_ONLY
        && this._bootstrapFreightCargo >= 0) {
      freightCargo = this._bootstrapFreightCargo;
    } else {
      local nextCargo = 0;
      if (this._lastFreightCargo >= 0) {
        for (local i = 0; i < freightCargos.len(); i++) {
          if (freightCargos[i] == this._lastFreightCargo) {
            nextCargo = (i + 1) % freightCargos.len();
            break;
          }
        }
      }
      freightCargo = freightCargos[nextCargo];
    }
  }
  this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines,
      fleetPlan, this._abandonedPairs, stage, prior,
      freightCargo, freightCargos);
  if (stage == OPEX_STAGE_COMPLETE && b6StaleProjects != null) {
    OpexB6LogFreshEquivalence(b6StaleProjects, this._projects, b6StaleDate);
  }
  local actualFreightCargo = (this._projects != null && ("freightCargo" in this._projects))
      ? this._projects.freightCargo : freightCargo;
  if (stage == OPEX_STAGE_AIR_ONLY && actualFreightCargo != null) {
    this._bootstrapFreightCargo = actualFreightCargo;
  }
  /* Le bootstrap utilise le meme premier cargo pour son rail (etape 0) puis
   * sa route (etape 3). Ensuite chaque passe complete ne porte que sur le
   * cargo suivant : prior reste null en regime complet, donc le portefeuille
   * ne regrossit jamais par accumulation des anciens lots fret. */
  if (freightCargos.len() > 0
      && (stage == OPEX_STAGE_ROUTE_ONLY || stage == OPEX_STAGE_COMPLETE)) {
    if (actualFreightCargo != null) this._lastFreightCargo = actualFreightCargo;
    if (stage == OPEX_STAGE_ROUTE_ONLY) this._bootstrapFreightCargo = -1;
  }
  if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
    this._generationStage++;
    if (DECISION_LOG) {
      OpexDecide("BOOTSTRAP_ADVANCE", "next=" + this._generationStage
                 + " funded=" + this._projects.best.len());
    }
    local b = (this._catalog != null && this._catalog.bounds != null)
        ? this._catalog.bounds : null;
    if (b != null) {
      OpexSign(AIMap.GetTileIndex(1, 2), "BS|" + (this._generationStage - 1)
               + "|" + b.railMin + "|" + b.railMax + "|" + b.airMin);
    }
  }
}
