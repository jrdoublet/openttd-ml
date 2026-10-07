/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Tous les appels ci-dessous sont sous R1_R3_TEST_ONLY, declare dans le module
 * de selection deja charge. Aucun nouveau membre de classe ni reglage commun. */
function OpexR1R3FleetTrace(ai, project, rank, phase, reason, added = "unknown", replaced = "unknown")
{
  local entry = project.payload;
  local line = entry.line;
  local ids = "";
  local valid = 0;
  if (line != null && ("vehicles" in line)) {
    foreach (vehicle in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(vehicle) || !AIVehicle.IsPrimaryVehicle(vehicle)) continue;
      if (ids != "") ids += ",";
      ids += vehicle;
      valid++;
    }
  }
  OpexR1R3Log("mechanism=R1 phase=" + phase
      + " id=" + (("r1r3Id" in project) ? project.r1r3Id : "unknown")
      + " pass=" + R1_R3_TEST_PASS + " cycle=" + ai._taskCycle + " rank=" + rank
      + " line=" + (line != null && ("lineId" in line) ? line.lineId : -1)
      + " reason=" + reason + " want=" + entry.want
      + " base=" + (("baseVehicles" in entry) ? entry.baseVehicles : "unknown")
      + " inventory=" + (line != null && ("vehicles" in line) ? valid : "unknown")
      + " vehicles=" + (ids != "" ? ids : "none")
      + " cached=" + (line != null && ("vehCount" in line) ? line.vehCount : "unknown")
      + " added=" + added + " replaced=" + replaced + " price=" + entry.planePrice
      + " reserve=" + OpexCashReserve() + " buffer=1000"
      + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
}

function OpexR1R3AirTrace(ai, project, rank, phase, reason, before, after,
    built, threshold, finance = null, available = null, extra = "")
{
  local plan = project.payload;
  OpexR1R3Log("mechanism=R3 phase=" + phase + " pass=" + R1_R3_TEST_PASS
      + " cycle=" + ai._taskCycle + " rank=" + rank
      + " id=" + OpexProjectAttemptKey(project)
      + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile
      + " anchor_a=" + plan.siteA.anchor + " anchor_b=" + plan.siteB.anchor
      + " reason=" + reason + " built=" + built
      + " finance=" + (finance != null ? finance : OpexProjectFinanceCapital(project))
      + " available=" + (available != null ? available : OpexAvailableCapital())
      + " threshold=" + threshold + " bypass_before=" + (before ? 1 : 0)
      + " bypass_after=" + (after ? 1 : 0) + extra);
}

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

/* C42 : Purge immediate d'un projet de subvention devenu invalide dans this._projects */
function OpexAI::_purgeSubsidyFromProjects(subId)
{
  if (subId == null || subId < 0) return;
  if (this._projects == null) return;
  if (("best" in this._projects) && this._projects.best != null) {
    for (local i = this._projects.best.len() - 1; i >= 0; i--) {
      local p = this._projects.best[i];
      if (p != null && ("payload" in p) && p.payload != null &&
          ("isSubsidy" in p.payload) && p.payload.isSubsidy &&
          ("subsidyId" in p.payload) && p.payload.subsidyId == subId) {
        this._projects.best.remove(i);
      }
    }
  }
  if (("road" in this._projects) && this._projects.road != null &&
      ("best" in this._projects.road) && this._projects.road.best != null) {
    for (local i = this._projects.road.best.len() - 1; i >= 0; i--) {
      local p = this._projects.road.best[i];
      if (p != null && ("payload" in p) && p.payload != null &&
          ("isSubsidy" in p.payload) && p.payload.isSubsidy &&
          ("subsidyId" in p.payload) && p.payload.subsidyId == subId) {
        this._projects.road.best.remove(i);
      }
    }
  }
  if (("candidateGroups" in this._projects) && this._projects.candidateGroups != null) {
    local key = "subsidy|" + subId;
    if (key in this._projects.candidateGroups) {
      delete this._projects.candidateGroups[key];
    }
  }
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
  if (R1_R3_TEST_ONLY) OpexR1R3FleetTrace(this, project, i, "execute", "entry");
  /* B8 / G10 : un projet flotte peut devenir stale entre son calcul (ou un cache portefeuille)
   * et son execution. Revalider ici, au dernier site avant OpexAirAddPlane, garantit qu'aucun
   * capital n'est depense sur une ligne qui a entre-temps commence sa liquidation. */
  if (line == null || (("scrapping" in line) && line.scrapping)) {
    if (R1_R3_TEST_ONLY) OpexR1R3FleetTrace(this, project, i, "result", "line_scrapping", 0, 0);
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
  /* R1 : une autre tranche/copie de ce besoin peut avoir deja ete executee.
   * Refuser le snapshot caduc plutot que financer deux fois sa demande. */
  local liveCount = ("vehCount" in line) ? line.vehCount : line.vehicles.len();
  if (("baseVehicles" in entry) && liveCount != entry.baseVehicles) {
    if (R1_R3_TEST_ONLY) OpexR1R3FleetTrace(this, project, i, "result", "fleet_stale", 0, 0);
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
      passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst,
                            reason = "fleet_stale", extra = "" });
    return { outcome = "rejected", discards = passDiscards };
  }
  local need = entry.planePrice + OpexCashReserve();
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    if (R1_R3_TEST_ONLY) OpexR1R3FleetTrace(this, project, i, "result", "insufficient_cash", 0, 0);
    if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("fleet", i, project.capital, project.profitAnnual, project.roi, project.src, project.dst, need, money);
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst, reason = "insufficient_cash", extra = "" });
    return { outcome = "rejected", discards = passDiscards };
  }
  local plannedFull = ("capital" in project && project.capital > 0)
      ? project.capital : (entry.planePrice * entry.want);
  local costs = C63_INVEST_PROBE ? AIAccounting() : null;
  local c121HaveBefore = ("vehCount" in line) ? line.vehCount
      : (("vehicles" in line) ? line.vehicles.len() : 0);
  local c121TrackMarginal = C121_AIR_ECONOMICS && ("targetAirPlanes" in line)
      && line.targetAirPlanes > c121HaveBefore
      && ("lastProfit" in line) && ("lastRevenue" in line);
  local c121BaselineProfit = c121TrackMarginal ? line.lastProfit : 0;
  local c121BaselineRevenue = c121TrackMarginal ? line.lastRevenue : 0;
  local added = 0;
  /* Un REPLACE consomme un achat mais ne fait pas croitre la flotte :
   * compte separe, aligne sur task_air.nut (pas de added). */
  local replaced = 0;
  for (local k = 0; k < entry.want; k++) {
    local grown = OpexAirAddPlane(line, this._catalog);
    if (R1_R3_TEST_ONLY) OpexR1R3Log("mechanism=R1 phase=api_result id="
        + (("r1r3Id" in project) ? project.r1r3Id : "unknown")
        + " pass=" + R1_R3_TEST_PASS + " cycle=" + this._taskCycle + " rank=" + i
        + " unit=" + k + " added=" + grown.added
        + " reason=" + (("reason" in grown) ? grown.reason : "unknown"));
    if (("reason" in grown) && (grown.reason == "REEEQUIP_WAIT" || grown.reason == "REPLACE" || grown.reason == "REEEQUIP_FAIL" || grown.reason == "REEEQUIP_ABORT")) {
      if (grown.reason == "REPLACE" && ("vehCount" in grown)) {
        line.vehCount <- grown.vehCount;
        line.trains = grown.vehCount;
        replaced += 1;
      }
      break;
    }
    if (grown.added <= 0) break;
    added += grown.added;
    local haveNow = (("vehCount" in line) ? line.vehCount : 0) + grown.added;
    line.vehCount <- haveNow;
    line.trains = haveNow;
    if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < need) break;
  }
  local actual = (costs != null) ? costs.GetCosts() : 0;
  if (R1_R3_TEST_ONLY) OpexR1R3FleetTrace(this, project, i, "result",
      added + replaced > 0 ? "built" : "fleet_grow_failed", added, replaced);
  if (added + replaced <= 0) {
    if (C63_INVEST_PROBE) OpexC63RecordSpend("fleet", plannedFull, actual, false);
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
      passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst, reason = "fleet_grow_failed", extra = "" });
    }
    return { outcome = "rejected", discards = passDiscards };
  }
  if (C63_INVEST_PROBE) {
    local plannedAdded = entry.planePrice * (added + replaced);
    if (plannedAdded > plannedFull) plannedAdded = plannedFull;
    OpexC63RecordSpend("fleet", plannedAdded, actual, true);
    local missed = plannedFull - plannedAdded;
    if (missed > 0) OpexC63RecordSpend("fleet", missed, 0, false);
  }

  line.lastAirFleetYear <- year;
  line.lastAirFleetDate <- AIDate.GetCurrentDate();
  if (C121_AIR_OBSERVATION_GROWTH && C121_AIR_ECONOMICS && added > 0
      && ("targetAirPlanes" in line) && line.targetAirPlanes >= line.vehCount) {
    line.c121GrowthReportYear <- this._lastReportYear;
  }
  if (c121TrackMarginal && line.vehCount > c121HaveBefore) {
    line.c121MarginalBaselineProfit <- c121BaselineProfit;
    line.c121MarginalBaselineRevenue <- c121BaselineRevenue;
    line.c121MarginalBaselineVehicles <- c121HaveBefore;
    /* task_report(year) publie le profit de year-1. Un renfort pose pendant
     * year ne dispose donc d'une annee civile complete post-renfort qu'au
     * report year+2. */
    line.c121MarginalObserveYear <- year + 2;
  }
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
  AILog.Info("[FLEET_PROJECT] line=" + line.lineId + " added=" + added + " replaced=" + replaced);
  if (C121_KDEC_COLD_SHADOW && added > 0 && ("c121MarginalSamples" in line)) {
    local date = AIDate.GetCurrentDate();
    AILog.Info("C121_KDEC_COLD_FUNDED line=" + line.lineId + " added=" + added
        + " samples=" + line.c121MarginalSamples + " year=" + AIDate.GetYear(date)
        + " month=" + AIDate.GetMonth(date) + " day=" + AIDate.GetDayOfMonth(date));
  }
  return { outcome = "built", discards = passDiscards };
}

/* C121 cadence : mesure l'opportunity cost d'un premier renfort live.
 * La sonde garde la premiere nouvelle ligne AIR encore classee APRES la flotte. La garde
 * causale, elle, ne consomme ce signal que lorsque cette ligne est IMMEDIATEMENT suivante
 * et qu'aucun chantier n'a encore ete construit dans la passe : on protege ainsi une
 * substitution réellement atteignable, pas un AIR distant qui pourrait etre bloque par
 * un projet intermediaire ou K_pass. */
function OpexC121FirstLiveAirOpportunity(projects, project, rank, lines)
{
  if (projects == null || !("best" in projects) || project == null
      || !("payload" in project) || project.payload == null
      || !("c121FirstLive" in project.payload) || !project.payload.c121FirstLive) return null;
  local available = OpexAvailableCapital();
  local fleetCap = OpexProjectFinanceCapital(project);
  for (local j = rank + 1; j < projects.best.len(); j++) {
    local next = projects.best[j];
    if (next == null || !("mode" in next) || next.mode != "air") continue;
    if (!("payload" in next) || next.payload == null
        || !OpexAirBatchPlanStillLive(next.payload, lines)) continue;
    local airCap = OpexProjectFinanceCapital(next);
    if (airCap <= 0) continue;
    return {
      nextRank = j, available = available, fleetCap = fleetCap, airCap = airCap,
      airFundableNow = airCap <= available,
      displaced = airCap <= available && fleetCap + airCap > available,
    };
  }
  return { nextRank = -1, available = available, fleetCap = fleetCap, airCap = 0,
           airFundableNow = false, displaced = false };
}

/* rail_origin_reuse : cout d'opportunite AIR d'une extension ferroviaire. On reprend le contrat
 * causal borne de C121 : premier AIR vivant classe apres l'extension, et la branche causale ne
 * l'utilise que s'il est IMMEDIATEMENT suivant et qu'aucun chantier n'a encore ete construit.
 * `displaced` signifie : AIR finançable maintenant, mais plus après paiement du rail. */
function OpexRailOriginReuseAirOpportunity(projects, project, rank, lines)
{
  if (projects == null || !("best" in projects) || project == null
      || !("mode" in project) || project.mode != "rail"
      || !("payload" in project) || project.payload == null
      || !("originServed" in project.payload) || !project.payload.originServed) return null;
  local available = OpexAvailableCapital();
  local railCap = OpexProjectFinanceCapital(project);
  for (local j = rank + 1; j < projects.best.len(); j++) {
    local next = projects.best[j];
    if (next == null || !("mode" in next) || next.mode != "air") continue;
    if (!("payload" in next) || next.payload == null
        || !OpexAirBatchPlanStillLive(next.payload, lines)) continue;
    local airCap = OpexProjectFinanceCapital(next);
    if (airCap <= 0) continue;
    return {
      nextRank = j, available = available, railCap = railCap, airCap = airCap,
      airFundableNow = airCap <= available,
      displaced = railCap <= available && airCap <= available && railCap + airCap > available,
    };
  }
  return { nextRank = -1, available = available, railCap = railCap, airCap = 0,
           airFundableNow = false, displaced = false };
}

/* C121 cadence : shadow borné du premier arrêt de passe C75/K_pass.
 * Le journal montre ce qui bloque maintenant et ce que la boucle aurait vu ensuite
 * si elle n'avait pas break. Aucun tri, aucune mutation, aucun changement de décision. */
function OpexC121KPassShadow(projects, project, rank, projCap, kPass, available, reason)
{
  if (!C121_KPASS_SHADOW || projects == null || !("best" in projects)
      || project == null) return;
  local lineId = -1;
  if (project.mode == "fleet" && ("payload" in project) && project.payload != null
      && ("line" in project.payload) && project.payload.line != null
      && ("lineId" in project.payload.line)) lineId = project.payload.line.lineId;
  local tail = "";
  local end = rank + 6;
  if (end > projects.best.len()) end = projects.best.len();
  for (local j = rank + 1; j < end; j++) {
    local next = projects.best[j];
    if (next == null) continue;
    local cap = OpexProjectFinanceCapital(next);
    tail += " p" + j + "=" + next.mode + ":" + cap + ":" + (cap <= available ? 1 : 0);
  }
  AILog.Info("C121_KPASS_SHADOW reason=" + reason + " next_mode=" + project.mode
      + " rank=" + rank + " line=" + lineId + " finance=" + projCap
      + " k_pass=" + kPass + " available=" + available + tail);
}

/* C121 cadence : look-ahead pur et borne pour le causal K_pass. Il ne reordonne rien :
 * il dit seulement si, dans les cinq rangs qui suivent un bloqueur fleet, une nouvelle
 * ligne AIR encore vivante est deja finançable avec la caisse courante. */
function OpexC121KPassFundableAirAhead(projects, rank, available, lines)
{
  if (projects == null || !("best" in projects) || projects.best == null || available < 0) return null;
  local end = rank + 6;
  if (end > projects.best.len()) end = projects.best.len();
  for (local j = rank + 1; j < end; j++) {
    local next = projects.best[j];
    if (next == null || !("mode" in next) || next.mode != "air") continue;
    if (!("payload" in next) || next.payload == null
        || !OpexAirBatchPlanStillLive(next.payload, lines)) continue;
    local cap = OpexProjectFinanceCapital(next);
    if (cap > 0 && cap <= available) return { rank = j, cap = cap };
  }
  return null;
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

/* Projet finance, non-reuse, dont l'ancre est imputee a la ville surveillee
 * et qui passe encore OpexAirBatchPlanStillLive. */
function OpexAirC83FundedRaceCoversTown(projects, lines, townId)
{
  if (projects == null || !("best" in projects) || projects.best == null || lines == null) return false;
  local limit = projects.best.len() < PROJECT_TOP_K ? projects.best.len() : PROJECT_TOP_K;
  for (local i = 0; i < limit; i++) {
    local project = projects.best[i];
    if (project == null || !("mode" in project) || project.mode != "air") continue;
    if (!("profitAnnual" in project) || project.profitAnnual <= 0) continue;
    if (OpexProjectFinanceCapital(project) > OpexAvailableCapital()) continue;
    if (!("payload" in project) || project.payload == null) continue;
    local plan = project.payload;
    if (!("siteA" in plan) || plan.siteA == null || !("siteB" in plan) || plan.siteB == null) continue;
    if (!OpexAirBatchPlanStillLive(plan, lines)) continue;
    local reuseA = ("reuseA" in plan) && plan.reuseA;
    local reuseB = ("reuseB" in plan) && plan.reuseB;
    if (!reuseA && ("anchor" in plan.siteA) && OpexAirSlotTownId(plan.siteA.anchor) == townId) return true;
    if (!reuseB && ("anchor" in plan.siteB) && OpexAirSlotTownId(plan.siteB.anchor) == townId) return true;
  }
  return false;
}

/* C122.4 shadow : meme filtre que OpexAirC83FundedRaceCoversTown, mais uniquement
 * sous la sonde et en retournant le projet/rang pour expliquer la decision locale.
 * Aucun scan carte : au plus PROJECT_TOP_K projets deja finances et leurs ancres
 * physiques deja calculees. */
function OpexC122ThreatFundedMatch(projects, lines, townId)
{
  if (!C122_AIR_THREAT_PROBE || projects == null || !("best" in projects)
      || projects.best == null || lines == null) return null;
  local limit = projects.best.len() < PROJECT_TOP_K ? projects.best.len() : PROJECT_TOP_K;
  for (local i = 0; i < limit; i++) {
    local project = projects.best[i];
    if (project == null || !("mode" in project) || project.mode != "air") continue;
    if (!("profitAnnual" in project) || project.profitAnnual <= 0) continue;
    if (OpexProjectFinanceCapital(project) > OpexAvailableCapital()) continue;
    if (!("payload" in project) || project.payload == null) continue;
    local plan = project.payload;
    if (!("siteA" in plan) || plan.siteA == null || !("siteB" in plan) || plan.siteB == null) continue;
    if (!OpexAirBatchPlanStillLive(plan, lines)) continue;
    local reuseA = ("reuseA" in plan) && plan.reuseA;
    local reuseB = ("reuseB" in plan) && plan.reuseB;
    local hits = (!reuseA && ("anchor" in plan.siteA)
        && OpexAirSlotTownId(plan.siteA.anchor) == townId)
        || (!reuseB && ("anchor" in plan.siteB)
        && OpexAirSlotTownId(plan.siteB.anchor) == townId);
    if (hits) return { project = project, rank = i };
  }
  return null;
}

function OpexC122ThreatLog(fields)
{
  if (!C122_AIR_THREAT_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("C1224_THREAT date=" + date + " " + fields);
}

function OpexC122ThreatRegister(ai, townId, previous)
{
  if (!C122_AIR_THREAT_PROBE || ai == null || townId < 0) return;
  if (townId in C122_AIR_THREAT_WATCH) return;
  local match = OpexC122ThreatFundedMatch(ai._projects, ai._lines, townId);
  local head = (ai._projects != null && ("best" in ai._projects)
      && ai._projects.best != null && ai._projects.best.len() > 0)
      ? ai._projects.best[0] : null;
  local rank = match != null ? match.rank : -1;
  local project = match != null ? match.project : null;
  local projectKey = project != null ? OpexProjectAttemptKey(project) : "none";
  local blocker = (rank > 0) ? head : null;
  local blockerKey = blocker != null ? OpexProjectAttemptKey(blocker) : "none";
  local blockerMode = (blocker != null && ("mode" in blocker)) ? blocker.mode : "none";
  local projectScore = (project != null && ("fundScore" in project)) ? project.fundScore : 0.0;
  local blockerScore = (blocker != null && ("fundScore" in blocker)) ? blocker.fundScore : 0.0;
  local finance = project != null ? OpexProjectFinanceCapital(project) : -1;
  local today = AIDate.GetCurrentDate();
  C122_AIR_THREAT_SEQ++;
  C122_AIR_THREAT_WATCH.rawset(townId, {
    seq = C122_AIR_THREAT_SEQ,
    detected = today,
    rank = rank,
    projectKey = projectKey,
    blockerKey = blockerKey,
    blockerMode = blockerMode,
    funded = match != null,
    attempts = 0,
    retries = 0,
  });
  OpexC122ThreatLog("phase=detected seq=" + C122_AIR_THREAT_SEQ
      + " town=" + townId + " previous=" + previous + " remaining=1"
      + " funded=" + (match != null ? 1 : 0) + " rank=" + rank
      + " project=" + projectKey + " finance=" + finance
      + " available=" + OpexAvailableCapital() + " project_score=" + projectScore
      + " blocker_mode=" + blockerMode + " blocker=" + blockerKey
      + " blocker_score=" + blockerScore);
}

/* La menace peut preceder la regeneration C77 qui cree le projet actionnable.
 * Rejouer seulement PROJECT_TOP_K permet de dater cette transition sans scan
 * carte/site/moteur et sans modifier l'ordre du portefeuille. */
function OpexC122ThreatRefreshFunded(ai, townId)
{
  if (!C122_AIR_THREAT_PROBE || ai == null || !(townId in C122_AIR_THREAT_WATCH)) return;
  local watch = C122_AIR_THREAT_WATCH[townId];
  if (watch.funded) return;
  local match = OpexC122ThreatFundedMatch(ai._projects, ai._lines, townId);
  if (match == null) return;
  local project = match.project;
  local head = (ai._projects != null && ("best" in ai._projects)
      && ai._projects.best != null && ai._projects.best.len() > 0)
      ? ai._projects.best[0] : null;
  local blocker = match.rank > 0 ? head : null;
  watch.funded = true;
  watch.rank = match.rank;
  watch.projectKey = OpexProjectAttemptKey(project);
  watch.blockerKey = blocker != null ? OpexProjectAttemptKey(blocker) : "none";
  watch.blockerMode = (blocker != null && ("mode" in blocker)) ? blocker.mode : "none";
  local today = AIDate.GetCurrentDate();
  OpexC122ThreatLog("phase=funded seq=" + watch.seq + " town=" + townId
      + " days=" + (today - watch.detected) + " rank=" + match.rank
      + " project=" + watch.projectKey + " finance=" + OpexProjectFinanceCapital(project)
      + " available=" + OpexAvailableCapital()
      + " project_score=" + (("fundScore" in project) ? project.fundScore : 0.0)
      + " blocker_mode=" + watch.blockerMode + " blocker=" + watch.blockerKey
      + " blocker_score=" + ((blocker != null && ("fundScore" in blocker)) ? blocker.fundScore : 0.0));
}

function OpexC122ThreatClose(townId, previous, ownPresent, ownCount)
{
  if (!C122_AIR_THREAT_PROBE || !(townId in C122_AIR_THREAT_WATCH)) return;
  local watch = C122_AIR_THREAT_WATCH[townId];
  local today = AIDate.GetCurrentDate();
  local claimed = (previous == 11) ? (ownCount >= 2) : ownPresent;
  OpexC122ThreatLog("phase=closed seq=" + watch.seq + " town=" + townId
      + " result=" + (claimed ? "opex_claimed" : "competitor_monopoly")
      + " previous=" + previous + " remaining=0 own=" + (ownPresent ? 1 : 0)
      + " days=" + (today - watch.detected) + " funded=" + (watch.funded ? 1 : 0)
      + " rank=" + watch.rank + " project=" + watch.projectKey
      + " attempts=" + watch.attempts + " retries=" + watch.retries
      + " blocker_mode=" + watch.blockerMode + " blocker=" + watch.blockerKey);
  delete C122_AIR_THREAT_WATCH[townId];
}

function OpexC122ThreatCancel(townId, reason)
{
  if (!C122_AIR_THREAT_PROBE || !(townId in C122_AIR_THREAT_WATCH)) return;
  local watch = C122_AIR_THREAT_WATCH[townId];
  local today = AIDate.GetCurrentDate();
  OpexC122ThreatLog("phase=closed seq=" + watch.seq + " town=" + townId
      + " result=" + reason + " days=" + (today - watch.detected)
      + " funded=" + (watch.funded ? 1 : 0) + " rank=" + watch.rank
      + " attempts=" + watch.attempts + " retries=" + watch.retries + " project=" + watch.projectKey
      + " blocker_mode=" + watch.blockerMode + " blocker=" + watch.blockerKey);
  delete C122_AIR_THREAT_WATCH[townId];
}

function OpexC122ThreatProjectTowns(project)
{
  local towns = [];
  if (!C122_AIR_THREAT_PROBE || project == null || !("mode" in project)
      || project.mode != "air" || !("payload" in project) || project.payload == null) return towns;
  local plan = project.payload;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (("siteA" in plan) && plan.siteA != null && !reuseA
      && ("anchor" in plan.siteA)) {
    local townA = OpexAirSlotTownId(plan.siteA.anchor);
    if (townA in C122_AIR_THREAT_WATCH) towns.append(townA);
  }
  if (("siteB" in plan) && plan.siteB != null && !reuseB
      && ("anchor" in plan.siteB)) {
    local townB = OpexAirSlotTownId(plan.siteB.anchor);
    if (townB in C122_AIR_THREAT_WATCH) {
      local duplicate = false;
      foreach (id in towns) if (id == townB) duplicate = true;
      if (!duplicate) towns.append(townB);
    }
  }
  return towns;
}

function OpexC122ThreatNoteAttempt(project, rank, builtBefore)
{
  if (!C122_AIR_THREAT_PROBE) return;
  local towns = OpexC122ThreatProjectTowns(project);
  foreach (townId in towns) {
    local watch = C122_AIR_THREAT_WATCH[townId];
    watch.attempts++;
    OpexC122ThreatLog("phase=attempt seq=" + watch.seq + " town=" + townId
        + " rank=" + rank + " built_before=" + builtBefore
        + " attempt=" + watch.attempts + " project=" + OpexProjectAttemptKey(project)
        + " finance=" + OpexProjectFinanceCapital(project)
        + " available=" + OpexAvailableCapital());
  }
}

function OpexC122ThreatNoteOutcome(project, rank, attempt)
{
  if (!C122_AIR_THREAT_PROBE) return;
  local reason = "none";
  local detail = "";
  local error = 0;
  if (("discards" in attempt) && attempt.discards != null) {
    for (local i = attempt.discards.len() - 1; i >= 0; i--) {
      local discard = attempt.discards[i];
      if (discard == null || !("mode" in discard) || discard.mode != "air"
          || !("rank" in discard) || discard.rank != rank) continue;
      reason = ("reason" in discard) ? discard.reason : "unknown";
      detail = ("detail" in discard) ? discard.detail : "";
      error = ("error" in discard) ? discard.error : 0;
      break;
    }
  }
  local towns = OpexC122ThreatProjectTowns(project);
  foreach (townId in towns) {
    local watch = C122_AIR_THREAT_WATCH[townId];
    OpexC122ThreatLog("phase=outcome seq=" + watch.seq + " town=" + townId
      + " rank=" + rank + " outcome=" + attempt.outcome
        + " reason=" + reason + " detail=" + detail + " error=" + error
        + " project=" + OpexProjectAttemptKey(project)
        + " available=" + OpexAvailableCapital());
  }
}

/* C122.4 actif : le seul trou causal observe est un projet menace deja rang 0
 * dont un endpoint devient physiquement non constructible entre selection et
 * tentative. Ne pas changer le score : relancer une fois le C77 cible sur le
 * TownID exact de l'endpoint invalide afin de chercher un nouveau site. */
function OpexC122ThreatRetryUnbuildable(ai, project, rank, attempt)
{
  if (!C122_AIR_THREAT_RETRY || ai == null || project == null || attempt == null
      || !("outcome" in attempt) || attempt.outcome != "rejected"
      || !("discards" in attempt) || attempt.discards == null
      || !("payload" in project) || project.payload == null) return false;

  local reason = null;
  for (local i = attempt.discards.len() - 1; i >= 0; i--) {
    local discard = attempt.discards[i];
    if (discard == null || !("mode" in discard) || discard.mode != "air"
        || !("rank" in discard) || discard.rank != rank || !("reason" in discard)) continue;
    if (discard.reason == "siteA_unbuildable" || discard.reason == "siteB_unbuildable") {
      reason = discard.reason;
    }
    break;
  }
  if (reason == null) return false;

  local plan = project.payload;
  local site = reason == "siteA_unbuildable" ? plan.siteA : plan.siteB;
  local reuse = reason == "siteA_unbuildable"
      ? (("reuseA" in plan) && plan.reuseA)
      : (("reuseB" in plan) && plan.reuseB);
  if (reuse || site == null || !("anchor" in site)) return false;
  local townId = OpexAirSlotTownId(site.anchor);
  if (!(townId in C122_AIR_THREAT_WATCH)) return false;
  local watch = C122_AIR_THREAT_WATCH[townId];
  if (watch.retries >= 1) return false;

  local key = "c77|town|" + townId + "|air";
  local alreadyQueued = ai._reactiveQueue != null && ai._reactiveQueue.has(key);
  local queued = false;
  if (!alreadyQueued) {
    queued = ai._c77EnqueueEntity(["air"], "town", townId, true, "c122_threat_retry");
  }
  if (queued) {
    watch.retries++;
    C122_AIR_THREAT_RETRY_COUNT++;
    ai._c83SlotRace.rawset(townId, AIDate.GetCurrentDate());
  }
  OpexC122ThreatLog("phase=retry seq=" + watch.seq + " town=" + townId
      + " reason=" + reason + " queued=" + (queued ? 1 : 0)
      + " coalesced=" + (alreadyQueued ? 1 : 0)
      + " count=" + C122_AIR_THREAT_RETRY_COUNT
      + " project=" + OpexProjectAttemptKey(project));
  return queued;
}

function OpexC83LogSlotClosure(townId, previous, remaining, ownPresent, ownCount)
{
  if (remaining != 0) return;
  if (previous != 1 && previous != 11 && previous != 2) return;
  local claimed = (previous == 11) ? (ownCount >= 2) : ownPresent;
  OpexC122ThreatClose(townId, previous, ownPresent, ownCount);
  if (!C78_SLOT_INTERCEPT_PROBE) return;
  local fields = "phase=" + (claimed ? "c83_slot_claimed" : "c83_slot_lost")
      + " town=" + townId + " previous=" + previous + " remaining=0 own=" + (ownPresent ? 1 : 0);
  if (previous == 2) fields += " jump=1";
  OpexC78SlotLog(fields);
}

/* Une ville sortie du top contestable : journaliser la fermeture, garder
 * l'observation d'un slot 11, sinon oublier l'entree. */
function OpexC83WatchDroppedTown(ai, townId, ownCounts)
{
  if (!AITown.IsValidTown(townId)) {
    delete ai._c83SlotWatch[townId];
    if (townId in ai._c83SlotRace) delete ai._c83SlotRace[townId];
    return;
  }
  local remaining = AITown.GetAllowedNoise(townId);
  local ownCount = (townId in ownCounts) ? ownCounts[townId] : 0;
  local ownPresent = ownCount > 0;
  local state = remaining + (ownPresent ? 10 : 0);
  local previous = (townId in ai._c83SlotWatch) ? ai._c83SlotWatch[townId] : 2;
  OpexC83LogSlotClosure(townId, previous, remaining, ownPresent, ownCount);
  if (previous == 1 && remaining > 1) OpexC122ThreatCancel(townId, "threat_cleared");
  else if (previous == 1 && ownPresent && remaining > 0) OpexC122ThreatCancel(townId, "opex_served");
  if (remaining == 0) {
    delete ai._c83SlotWatch[townId];
    if (townId in ai._c83SlotRace) delete ai._c83SlotRace[townId];
  } else if (state == 1 || state == 11) {
    ai._c83SlotWatch.rawset(townId, state);
    if (state == 11 && (townId in ai._c83SlotRace)) delete ai._c83SlotRace[townId];
  } else {
    delete ai._c83SlotWatch[townId];
    if (townId in ai._c83SlotRace) delete ai._c83SlotRace[townId];
  }
}

/* Trace rare, commune aux deux bras, independante des sondes portefeuille
 * couteuses. --script-debug permet au banc de collecter les intentions et les
 * suppressions ; aucune nouvelle horloge, file ou donnee de Save/Load. */
function OpexC83ReactionLog(townId, action)
{
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
      + AIDate.GetDayOfMonth(date) + " C83_REACTION enabled=1"
      + " town=" + townId + " action=" + action);
}

function OpexC83WatchOneTown(ai, townId, ownCounts, today, rearmDays)
{
  local remaining = AITown.GetAllowedNoise(townId);
  local ownCount = (townId in ownCounts) ? ownCounts[townId] : 0;
  local ownPresent = ownCount > 0;
  local state = remaining + (ownPresent ? 10 : 0);
  local previous = (townId in ai._c83SlotWatch) ? ai._c83SlotWatch[townId] : 2;
  OpexC83LogSlotClosure(townId, previous, remaining, ownPresent, ownCount);
  if (previous == 1 && remaining > 1) OpexC122ThreatCancel(townId, "threat_cleared");
  else if (previous == 1 && ownPresent && remaining > 0) OpexC122ThreatCancel(townId, "opex_served");

  if (ownPresent || remaining != 1) {
    ai._c83SlotWatch.rawset(townId, state);
    /* La course n'est plus l'etat 1 : le plafond de rearm ne doit pas
     * bloquer une prochaine ouverture de ce slot. */
    if (townId in ai._c83SlotRace) delete ai._c83SlotRace[townId];
    return 0;
  }

  OpexC122ThreatRegister(ai, townId, previous);
  OpexC122ThreatRefreshFunded(ai, townId);

  /* Etat 1 sans aeroport Opex : la course reste armee. Le recu d'enqueue
   * (_c83SlotRace) n'est ecrit qu'apres un enqueue reussi. */
  if (OpexAirC83FundedRaceCoversTown(ai._projects, ai._lines, townId)) {
    if (C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=c83_slot_watch town=" + townId
          + " previous=" + previous + " remaining=1 action=already_funded");
    }
    ai._c83SlotWatch.rawset(townId, state);
    return 0;
  }

  local raceKey = "c77|town|" + townId + "|air";
  if (ai._reactiveQueue != null && ai._reactiveQueue.has(raceKey)) {
    if (C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=c83_slot_watch town=" + townId
          + " previous=" + previous + " remaining=1 action=coalesced");
    }
    ai._c83SlotWatch.rawset(townId, state);
    return 0;
  }

  local lastEnqueue = (townId in ai._c83SlotRace) ? ai._c83SlotRace[townId] : -1;
  if (lastEnqueue >= 0 && today - lastEnqueue < rearmDays) {
    if (C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=c83_slot_watch town=" + townId
          + " previous=" + previous + " remaining=1 action=rearm_capped");
    }
    ai._c83SlotWatch.rawset(townId, state);
    return 0;
  }

  if (ai._c77EnqueueEntity(["air"], "town", townId, true, "c83_slot_race")) {
    OpexC83ReactionLog(townId, "enqueued");
    ai._c83SlotRace.rawset(townId, today);
    ai._c83SlotWatch.rawset(townId, state);
    if (C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=c83_slot_watch town=" + townId
          + " previous=" + previous + " remaining=1 action=targeted_regen");
    }
    return 1;
  }
  OpexC83ReactionLog(townId, "enqueue_failed");
  if (C78_SLOT_INTERCEPT_PROBE) {
    OpexC78SlotLog("phase=c83_slot_watch town=" + townId
        + " previous=" + previous + " remaining=1 action=enqueue_failed");
  }
  return 0;
}

function OpexC83WatchAirSlots(ai)
{
  if (ai._c83SlotWatch == null || typeof ai._c83SlotWatch != "table") {
    ai._c83SlotWatch = {};
  }
  if (ai._c83SlotRace == null || typeof ai._c83SlotRace != "table") {
    ai._c83SlotRace = {};
  }

  local enqueued = 0;
  local watched = OpexAirC83WatchTowns(ai._catalog.towns);
  local ownCounts = OpexAirOwnSlotTownCounts();
  local seen = {};
  local today = AIDate.GetCurrentDate();
  local rearmDays = 365;
  foreach (town in watched) {
    seen.rawset(town.id, true);
    enqueued += OpexC83WatchOneTown(ai, town.id, ownCounts, today, rearmDays);
  }

  local stale = [];
  foreach (townId, prevState in ai._c83SlotWatch) {
    if (!(townId in seen)) stale.append(townId);
  }
  foreach (townId in stale) OpexC83WatchDroppedTown(ai, townId, ownCounts);
  return enqueued;
}

/* Une seule grande ville encore vide. On s'arrete quand elle est servie ou
 * verrouillee. La regeneration reutilise la file C83 : coalescence toujours,
 * plafond de rearm seulement quand c83_fixes est arme. */
function OpexC83PreemptWatch(ai)
{
  if (!C83_PREEMPT_OPEN || C83_PREEMPT_STOPPED || !OpexAirC83SlotSignalEnabled()) return 0;
  if (ai == null || ai._catalog == null || ai._catalog.towns == null) return 0;
  if (ai._c83PreemptRace == null || typeof ai._c83PreemptRace != "table") ai._c83PreemptRace = {};

  local ownCounts = OpexAirOwnSlotTownCounts();
  local prev = C83_PREEMPT_TOWN;
  if (prev >= 0) {
    local own = (prev in ownCounts);
    local valid = AITown.IsValidTown(prev);
    local noise = valid ? AITown.GetAllowedNoise(prev) : 0;
    local pop = valid ? AITown.GetPopulation(prev) : 0;
    if (own) {
      if (C78_SLOT_INTERCEPT_PROBE) OpexC78SlotLog("phase=c83_preempt_built town=" + prev);
      ::C83_PREEMPT_TOWN = -1;
      ::C83_PREEMPT_STOPPED = true;
      return 0;
    }
    if (!valid || noise != 2 || pop < OpexAirPreemptMinPop()) {
      if (C78_SLOT_INTERCEPT_PROBE) {
        OpexC78SlotLog("phase=c83_preempt_lost town=" + prev + " noise=" + noise);
      }
      ::C83_PREEMPT_TOWN = -1;
      ::C83_PREEMPT_STOPPED = true;
      return 0;
    }
  }

  local newly = false;
  local townId = C83_PREEMPT_TOWN;
  if (townId < 0) {
    local picked = OpexAirPreemptPickTown(ai._catalog.towns, ownCounts);
    if (picked == null) return 0;
    townId = picked.id;
    ::C83_PREEMPT_TOWN = townId;
    newly = true;
  }

  local action = "watch";
  local enqueued = 0;
  if (OpexAirC83FundedRaceCoversTown(ai._projects, ai._lines, townId)) {
    action = "already_funded";
  } else {
    local raceKey = "c77|town|" + townId + "|air";
    local blocked = false;
    local today = AIDate.GetCurrentDate();
    if (ai._reactiveQueue != null && ai._reactiveQueue.has(raceKey)) {
      action = "coalesced";
      blocked = true;
    } else if (C83_FIXES) {
      local lastEnqueue = (townId in ai._c83PreemptRace) ? ai._c83PreemptRace[townId] : -1;
      if (lastEnqueue >= 0 && today - lastEnqueue < 365) {
        action = "rearm_capped";
        blocked = true;
      }
    } else if (ai._c83PreemptQueued == townId) {
      action = "already_queued";
      blocked = true;
    }
    if (!blocked) {
      if (ai._c77EnqueueEntity(["air"], "town", townId, true, "c83_preempt")) {
        if (C83_FIXES) {
          ai._c83PreemptRace.rawset(townId, today);
        } else {
          ai._c83PreemptQueued = townId;
        }
        action = "targeted_regen";
        enqueued = 1;
      } else {
        action = "enqueue_failed";
      }
    }
  }
  if (newly && C78_SLOT_INTERCEPT_PROBE) {
    local popNow = AITown.IsValidTown(townId) ? AITown.GetPopulation(townId) : -1;
    OpexC78SlotLog("phase=c83_preempt_target town=" + townId + " pop=" + popNow
        + " action=" + action);
  }
  return enqueued;
}

/* C83.1 : equivalent d'un evenement "un concurrent vient de prendre le premier
 * slot", absent de NoAI. On ne surveille que les K grandes villes early-slot et
 * GetAllowedNoise est O(1). Le cache encode (slots restants + 10 si Opex y est
 * deja present), afin de reagir aussi si notre aeroport disparait alors que le
 * total reste a un slot. La regeneration C77 est ciblee sur UNE ville et sa cle
 * reactive assure la coalescence. */
function OpexAI::_c83WatchAirSlotTransitions()
{
  if (this._catalog == null || !OpexAirC83SlotSignalEnabled()) return 0;
  if (C83_PREEMPT_OPEN) this._c83PreemptEnqueued = OpexC83PreemptWatch(this);
  if (C83_FIXES) return OpexC83WatchAirSlots(this);
  if (this._c83SlotWatch == null || typeof this._c83SlotWatch != "table") {
    this._c83SlotWatch = {};
  }

  local enqueued = 0;
  local watched = OpexAirC83WatchTowns(this._catalog.towns);
  /* C83.1 : "present" doit signifier qu'Opex occupe physiquement un slot de
   * CETTE ville, pas seulement qu'une origine commerciale de ligne est proche.
   * OpexAirTownServed() est volontairement plus large (<15 Manhattan autour des
   * originA/B) et peut donc masquer a tort l'arrivee du premier aeroport adverse.
   * Construire l'ensemble une fois par passage garde le cout O(nb aeroports),
   * au lieu de reparcourir toutes les lignes pour chacune des K villes suivies. */
  local ownAirportTowns = {};
  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local ownLoc = AIStation.GetLocation(st);
    local ownTownId = AIMap.IsValidTile(ownLoc) ? AITile.GetClosestTown(ownLoc) : -1;
    if (ownTownId >= 0 && AITown.IsValidTown(ownTownId)) ownAirportTowns.rawset(ownTownId, true);
  }
  foreach (town in watched) {
    local remaining = AITown.GetAllowedNoise(town.id);
    local ownPresent = town.id in ownAirportTowns;
    local state = remaining + (ownPresent ? 10 : 0);
    local previous = (town.id in this._c83SlotWatch) ? this._c83SlotWatch[town.id] : 2;
    this._c83SlotWatch.rawset(town.id, state);

    if (previous == 1 && remaining > 1) OpexC122ThreatCancel(town.id, "threat_cleared");
    else if (previous == 1 && ownPresent && remaining > 0) OpexC122ThreatCancel(town.id, "opex_served");

    if (previous == 1 && remaining == 0 && C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=" + (ownPresent ? "c83_slot_claimed" : "c83_slot_lost")
          + " town=" + town.id + " previous=1 remaining=0 own=" + (ownPresent ? 1 : 0));
    } else if (C78_SLOT_INTERCEPT_PROBE && remaining == 0 && (previous == 11 || previous == 2)) {
      local ownCount = ownPresent ? 1 : 0;
      if (previous == 11) {
        local closureCounts = OpexAirOwnSlotTownCounts();
        ownCount = (town.id in closureCounts) ? closureCounts[town.id] : 0;
      }
      local claimed = (previous == 11) ? (ownCount >= 2) : ownPresent;
      local jump = (previous == 2) ? " jump=1" : "";
      OpexC78SlotLog("phase=" + (claimed ? "c83_slot_claimed" : "c83_slot_lost")
          + " town=" + town.id + " previous=" + previous + " remaining=0 own=" + (ownPresent ? 1 : 0) + jump);
    }

    if (remaining == 0 && (previous == 1 || previous == 11 || previous == 2)) {
      local ownCountForThreat = ownPresent ? 1 : 0;
      if (previous == 11) {
        local threatClosureCounts = OpexAirOwnSlotTownCounts();
        ownCountForThreat = (town.id in threatClosureCounts) ? threatClosureCounts[town.id] : 0;
      }
      OpexC122ThreatClose(town.id, previous, ownPresent, ownCountForThreat);
    }

    if (state == 1) {
      OpexC122ThreatRegister(this, town.id, previous);
      OpexC122ThreatRefreshFunded(this, town.id);
    }
    if (state != 1 || previous == 1) continue;
    local alreadyFunded = false;
    if (this._projects != null && ("best" in this._projects) && this._projects.best != null) {
      local limit = this._projects.best.len() < PROJECT_TOP_K ? this._projects.best.len() : PROJECT_TOP_K;
      for (local i = 0; i < limit; i++) {
        local project = this._projects.best[i];
        if (project == null || !("mode" in project) || project.mode != "air") continue;
        if (!("profitAnnual" in project) || project.profitAnnual <= 0) continue;
        if (OpexProjectFinanceCapital(project) > OpexAvailableCapital()) continue;
        if (OpexProjectTouchesEntity(project, "town", town.id)) {
          alreadyFunded = true;
          break;
        }
      }
    }
    if (alreadyFunded) {
      if (C78_SLOT_INTERCEPT_PROBE) {
        OpexC78SlotLog("phase=c83_slot_watch town=" + town.id
            + " previous=" + previous + " remaining=1 action=already_funded");
      }
      continue;
    }
    if (this._c77EnqueueEntity(["air"], "town", town.id, true, "c83_slot_race")) {
      OpexC83ReactionLog(town.id, "enqueued");
      enqueued++;
      if (C78_SLOT_INTERCEPT_PROBE) {
        OpexC78SlotLog("phase=c83_slot_watch town=" + town.id
            + " previous=" + previous + " remaining=1 action=targeted_regen");
      }
    } else {
      OpexC83ReactionLog(town.id, "enqueue_failed");
      if (C78_SLOT_INTERCEPT_PROBE) {
        OpexC78SlotLog("phase=c83_slot_watch town=" + town.id
            + " previous=" + previous + " remaining=1 action=enqueue_failed");
      }
    }
  }
  return enqueued;
}

/* C78 etape 2 : journalisation passive d'une tentative de construction d'un projet. */
function OpexC78LogBuild(year, rank, mode, project, attempt, passDiscards, discardsLenBefore)
{
  if (!C69_BOTTLENECK_PROBE) return;
  local outcome = (attempt != null && ("outcome" in attempt)) ? attempt.outcome : "-";
  local reason = "-";
  local detail = "-";
  local error = "-";
  if (passDiscards != null && passDiscards.len() > discardsLenBefore) {
    local lastEntry = passDiscards[passDiscards.len() - 1];
    if (("reason" in lastEntry) && lastEntry.reason != null && lastEntry.reason != "") {
      reason = lastEntry.reason;
    }
    /* Code du constructeur (PREA, AFAIL...) et erreur de l'API, quand l'entree les porte. */
    if (("detail" in lastEntry) && lastEntry.detail != null && lastEntry.detail != "") detail = lastEntry.detail;
    if (("error" in lastEntry) && lastEntry.error != null) error = lastEntry.error;
  } else if (attempt != null && ("reason" in attempt) && attempt.reason != null && attempt.reason != "") {
    reason = attempt.reason;
  }
  local towns = OpexC78ProjectTowns(project);
  local pP = (project != null && ("profitAnnual" in project)) ? project.profitAnnual : 0;
  local pC = (project != null) ? OpexProjectFinanceCapital(project) : 0;
  local fields = "year=" + year + " rank=" + rank + " mode=" + mode
               + " townA=" + towns.townA + " townB=" + towns.townB
               + " indA=" + towns.indA + " indB=" + towns.indB
               + " P=" + pP + " C=" + pC
               + " outcome=" + outcome + " reason=" + reason
               + " detail=" + detail + " error=" + error;
  OpexC78Log("C78_BUILD", fields);
}

/* C75 bis : seuls les modes qui ouvrent une ligne sont eligibles. La liste
 * explicite evite qu'un futur mode de maintenance beneficie du bypass par defaut. */
function OpexC75KPassBypassIsNewLine(project)
{
  if (project == null || !("mode" in project)) return false;
  return project.mode == "air" || project.mode == "rail"
      || project.mode == "road" || project.mode == "water";
}

/* R12 : helpers extraits de _tryBuildProjects, sans changement de comportement.
 * Les etats de passe restent des locaux de l'orchestrateur, passes explicitement. */

/* Rang d'une cle de tentative dans le portefeuille courant, -1 si absente. */
function OpexAI::_projectsRankOfAttemptKey(key)
{
  if (this._projects != null && this._projects.best != null) {
    for (local i = 0; i < this._projects.best.len(); i++) {
      local project = this._projects.best[i];
      if (project != null && OpexProjectAttemptKey(project) == key) return i;
    }
  }
  return -1;
}

/* C39.5b : entry porte since/topSince/turns/topTurns (cf. _c39StampFinanceable) au lieu
 * d'une date seule, pour separer cadence, file d'attente par rang et concurrence caisse.
 * L'appelant garde C39_PROJECTS_CADENCE_PROBE. */
function OpexAI::_c39LogProjectBuilt(key, mode, rank, railSearchFlag)
{
  local entry = (key in this._c39FinanceableSince) ? this._c39FinanceableSince[key] : null;
  local daysSinceFinanceable = (entry != null)
      ? AIDate.GetCurrentDate() - entry.since : -1;
  local daysSinceTop = (entry != null && entry.topSince != -1)
      ? AIDate.GetCurrentDate() - entry.topSince : -1;
  local turnsSinceFinanceable = (entry != null) ? entry.turns : -1;
  local turnsSinceTop = (entry != null && entry.topSince != -1) ? entry.topTurns : -1;
  OpexC39ProjectsCadenceLog("phase=built mode=" + mode + " rank=" + rank
      + " days_since_financeable=" + daysSinceFinanceable + " days_since_top=" + daysSinceTop
      + " turns_since_financeable=" + turnsSinceFinanceable + " turns_since_top=" + turnsSinceTop
      + " rail_search=" + railSearchFlag + " capital_after=" + OpexAvailableCapital());
}

/* Traitement commun apres succes d'un projet du portefeuille (fleet/air/road/rail/water) :
 * journaux C39/C50 puis suivi C75/C69. builtCount++ et l'arret du batch restent dans la
 * boucle appelante (break/continue non deplaces). Appele une fois par construction. */
function OpexAI::_recordPortfolioProjectBuilt(project, rank, c75BuiltKeys, c69BuiltProjects)
{
  /* Autopsie C115/C121 : tracer UNE premiere construction de nouvelle ligne AIR,
   * uniquement APRES son succes physique. Ainsi aucune allocation, boucle ou chaine de
   * diagnostic ne peut modifier la decision que ce snapshot cherche a expliquer. Les
   * consequences futures sont mesurees dans le jumeau non instrumente. */
  if (C121_AUTOPSY_TEST_ONLY && !C121_AUTOPSY_DONE && project != null && project.mode == "air") {
    C121_AUTOPSY_DONE = true;
    C121_AUTOPSY_SELECTION_SEQ++;
    local autopsySeq = C121_AUTOPSY_SELECTION_SEQ;
    OpexC121AutopsyLog("BUILD_SNAPSHOT", "seq=" + autopsySeq + " rank=" + rank
        + " key=" + OpexProjectAttemptKey(project) + " line=" + (this._nextLineId - 1)
        + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
        + " available_after=" + OpexAvailableCapital()
        + " portfolio_len=" + ((this._projects != null && "best" in this._projects)
            ? this._projects.best.len() : -1));
    if (this._projects != null && "best" in this._projects && this._projects.best != null) {
      local autopsyN = this._projects.best.len() < 8 ? this._projects.best.len() : 8;
      for (local autopsyI = 0; autopsyI < autopsyN; autopsyI++) {
        OpexC121AutopsyLog("POST_CAND",
            OpexC121AutopsyProjectFields(this._projects.best[autopsyI], autopsyI, autopsySeq));
      }
    }
  }
  if (C39_PROJECTS_CADENCE_PROBE) {
    this._c39LogProjectBuilt(OpexProjectAttemptKey(project), project.mode, rank,
                             this._railSearch != null ? 1 : 0);
  }
  if (C50_CHRONOLOGY_PROBE) {
    local lineId;
    if (project.mode == "fleet") {
      lineId = ("payload" in project && "line" in project.payload && "lineId" in project.payload.line) ? project.payload.line.lineId : -1;
    } else {
      lineId = this._nextLineId - 1;
    }
    OpexC50ChronologyLog("phase=project_built mode=" + project.mode + " rank=" + rank + " line=" + lineId
        + " cost=" + project.capital + " profit=" + project.profitAnnual + " roi=" + project.roi
        + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
        + " available=" + OpexAvailableCapital());
  }
  if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(project)] <- true;
  if (C69_TRACK_BUILDS) c69BuiltProjects.append(project);
}

/* C78 : ligne commune air_attempt/air_outcome ; l'appelant garde C78_SLOT_INTERCEPT_PROBE. */
function OpexAI::_c78LogAirSlotLine(phase, project, rank, tail)
{
  local c78Plan = project.payload;
  local c78AirportType = (("airport" in c78Plan) && c78Plan.airport != null
      && ("type" in c78Plan.airport)) ? c78Plan.airport.type : -1;
  OpexC78SlotLog("phase=" + phase + " pass=" + C78_SLOT_PASS_COUNTER
      + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
      + " rank=" + rank + " townA=" + OpexC78AirSlotTown(c78Plan.siteA, c78AirportType)
      + " townB=" + OpexC78AirSlotTown(c78Plan.siteB, c78AirportType)
      + " closestA=" + OpexC78AirPhysicalTown(c78Plan.siteA)
      + " closestB=" + OpexC78AirPhysicalTown(c78Plan.siteB)
      + " src=" + project.src + " dst=" + project.dst
      + " defensive_claims=" + (("defensiveSlotClaims" in project) ? project.defensiveSlotClaims : -1)
      + " defensive_competitor_claims=" + (("defensiveCompetitorClaims" in project) ? project.defensiveCompetitorClaims : -1)
      + " defensive_own_claims=" + (("defensiveOwnClaims" in project) ? project.defensiveOwnClaims : -1)
      + tail);
}

/* A4 : consomme l'A* rail reprenable termine au tour precedent. Retourne true si une
 * ligne a ete construite ; l'appelant incremente builtCount/funnelAttempted. Les tables
 * passDiscards, c75BuiltKeys, c69BuiltProjects et c49BuiltRanks sont mutees en place. */
function OpexAI::_consumeResumableRailAtPassStart(year, passDiscards, c49Best, c49BuiltRanks,
                                                  c75BuiltKeys, c69BuiltProjects)
{
  /* Un A* de preparation depose son trace dans le stock. Le consommer ici
   * construirait le rail, y compris pendant l'annee reservee a l'AIR. */
  if (C121_AIR_FIRST_YEAR_RAIL_PREP && this._railSearch != null
      && ("isC121RailPrep" in this._railSearch) && this._railSearch.isC121RailPrep) {
    if (this._railSearch.phase == "build") this._handleRailStockSearchCompleted();
    return false;
  }
  local railCandidate = this._railSearch.candidate;
  local c78DiscardsLenRail = (C69_BOTTLENECK_PROBE && passDiscards != null) ? passDiscards.len() : 0;
  local railResult = this._consumeRailSearch(year);
  local outcome = railResult.outcome;
  if ((outcome == "failed" || outcome == "cash")
      && (DECISION_LOG || C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL)) {
    local failKey = "rail|" + railCandidate.src + "|" + railCandidate.dst + "|"
        + railCandidate.cargo + "|" + railCandidate.kind;
    local failRank = this._projectsRankOfAttemptKey(failKey);
    passDiscards.append({ rank = failRank, mode = "rail", src = railCandidate.src,
                          dst = railCandidate.dst, reason = railResult.reason,
                          extra = "", error = railResult.error });
  }
  if (C69_BOTTLENECK_PROBE) {
    /* C78 etape 2 : rang et projet du classement, recherches sous sonde seulement. */
    local c78Rank = -1;
    local c78Project = null;
    if (this._projects != null && this._projects.best != null) {
      local c78Key = "rail|" + railCandidate.src + "|" + railCandidate.dst + "|"
          + railCandidate.cargo + "|" + railCandidate.kind;
      for (local i = 0; i < this._projects.best.len(); i++) {
        local project = this._projects.best[i];
        if (project != null && OpexProjectAttemptKey(project) == c78Key) {
          c78Rank = i;
          c78Project = project;
          break;
        }
      }
    }
    local projToLog = (c78Project != null) ? c78Project : { mode = "rail", payload = railCandidate, profitAnnual = (("profitAnnual" in railCandidate) ? railCandidate.profitAnnual : 0), budgetCapital = (("capital" in railCandidate) ? railCandidate.capital : 0) };
    OpexC78LogBuild(year, c78Rank, "rail", projToLog, railResult, passDiscards, c78DiscardsLenRail);
  }
  if (outcome == "cash") return false;
  if (C39_PROJECTS_CADENCE_PROBE && outcome == "built") {
    /* railCandidate est le payload brut, pas le projet : il n'a pas de slot mode, donc
     * OpexProjectAttemptKey() produirait la cle incompatible unknown|... au lieu de rail|.... */
    local key = "rail|" + railCandidate.src + "|" + railCandidate.dst + "|"
        + railCandidate.cargo + "|" + railCandidate.kind;
    local railRank = this._projectsRankOfAttemptKey(key);
    /* C39.5b : meme forme d'entry que les 5 sites generiques ; la cle reste construite a la
     * main (commentaire ci-dessus), seul le contenu lu change. */
    this._c39LogProjectBuilt(key, "rail", railRank, 1);
  }
  this._railSearch = null;
  if (outcome != "built") return false;
  if (C75_MULTI_BUILD) c75BuiltKeys[OpexC69AttemptKey(railCandidate)] <- true;
  if (C69_TRACK_BUILDS) c69BuiltProjects.append(railCandidate);
  if (C50_CHRONOLOGY_PROBE && railCandidate != null) {
    local railRank = this._projectsRankOfAttemptKey("rail|" + railCandidate.src + "|"
        + railCandidate.dst + "|" + railCandidate.cargo + "|" + railCandidate.kind);
    local railCost = ("capital" in railCandidate) ? railCandidate.capital : 0;
    local railProf = ("profitAnnual" in railCandidate) ? railCandidate.profitAnnual : 0;
    local railRoi = ("roi" in railCandidate) ? railCandidate.roi : 0;
    OpexC50ChronologyLog("phase=project_built mode=rail rank=" + railRank + " line=" + (this._nextLineId - 1)
        + " cost=" + railCost + " profit=" + railProf + " roi=" + railRoi
        + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
        + " available=" + OpexAvailableCapital());
  }
  if (C49_SCARCITY_LEDGER && c49Best != null) {
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
  return true;
}

/* Diagnostics communs de fin de passe (C49, C63, C69/C73 puis entonnoir mensuel).
 * withC78Exit ajoute les journaux C78 de sortie normale, absents du retour rail pending. */
function OpexAI::_finalizeProjectsPassDiagnostics(builtCount, c49Best, c49BuiltRanks,
    c49AttemptedRanks, passDiscards, c73Cash, c73Avail, funnelAttempted, withC78Exit,
    c75StopReason)
{
  if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
  if (C63_INVEST_PROBE) {
    local railSearching = this._railSearch != null && this._railSearch.phase == "search";
    this._c63RecordPassAndProbe(builtCount, c49Best, passDiscards, railSearching);
  }
  if (C69_BOTTLENECK_PROBE) {
    local built = builtCount > 0;
    local empty = (c49Best == null || c49Best.len() == 0);
    OpexC73RecordPass(built, empty, c73Cash, c73Avail);
    if (withC78Exit && C78_SLOT_INTERCEPT_PROBE) {
      local c78ExitStop = c75StopReason;
      if (c78ExitStop == null && builtCount > 0) {
        c78ExitStop = (!C75_MULTI_BUILD) ? "single" : "list_end";
      }
      OpexC78SlotLog("phase=projects_exit pass=" + C78_SLOT_PASS_COUNTER
          + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
          + " built_count=" + builtCount
          + " stop=" + (c78ExitStop != null ? c78ExitStop : "none"));
    }
    if (withC78Exit && C78_SLOT_INTERCEPT_PROBE && builtCount > 0) {
      OpexC78SlotLog("phase=build pass=" + C78_SLOT_PASS_COUNTER
          + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
          + " built_count=" + builtCount);
    }
  }
  this._recordMonthlyFunnelPass(builtCount, c49Best, passDiscards, funnelAttempted);
}

/* C120 : motif d'arret de la passe pour la trace territoriale AIR. */
function OpexC120FinalizeProjectsPass(c120AirBuilt, c120AirAttempts, c120AirLastReason,
                                      c120AirLastReject, c75StopReason, builtCount)
{
  local c120StopReason = null;
  if (c120AirBuilt) c120StopReason = "built";
  else if (c120AirAttempts > 0 && c120AirLastReason != null) c120StopReason = c120AirLastReason;
  else if (c75StopReason != null) c120StopReason = c75StopReason;
  else if (builtCount > 0) c120StopReason = "other_mode_built";
  else if (C120_AIR_SELECTION_SNAPSHOT != null) c120StopReason = C120_AIR_SELECTION_SNAPSHOT.selectionReason;
  else c120StopReason = "no_snapshot";
  OpexC120TracePass(c120StopReason, c120AirAttempts, c120AirBuilt,
      c120AirLastReject, c75StopReason);
}

/* C75 : resout le motif d'arret de fin de passe, alimente C49/C75 et le retourne
 * (il sert ensuite a la sonde PROJECTS_COST). L'appelant garde C75_TRACK_PASSES. */
function OpexAI::_finalizeC75PassOutcome(year, builtCount, c75KPassData, c75StopReason,
                                         c80DiscardsThisPass)
{
  if (builtCount > 0 && c75StopReason == null) {
    if (c80DiscardsThisPass > 0) {
      c75StopReason = "marginal_floor";
    } else {
      c75StopReason = (!C75_MULTI_BUILD) ? "single" : "list_end";
    }
  }
  if (C49_SCARCITY_LEDGER && this._c49ScarcityLedger != null && builtCount > 0) {
    if (c75StopReason == "k_pass") this._c49ScarcityLedger.stop_k_pass++;
    else if (c75StopReason == "cash") this._c49ScarcityLedger.stop_cash++;
    else if (c75StopReason == "rail_search") this._c49ScarcityLedger.stop_rail_search++;
    else if (c75StopReason == "list_end") this._c49ScarcityLedger.stop_list_end++;
    else this._c49ScarcityLedger.stop_other++;
  }
  if (C75_KPASS_BYPASS && builtCount > 0) OpexC75BypassRecordStop(c75StopReason);
  OpexC75RecordPassOutcome(year, builtCount, c75KPassData, c75StopReason);
  return c75StopReason;
}

function OpexAI::_tryBuildProjects(year)
{
  local spPass = PROBE_SPAN_TRACE ? OpexSpanBegin("projects.pass") : null;
  if (R1_R3_TEST_ONLY) R1_R3_TEST_PASS++;
  local c75KPassData = null;
  local c75StopReason = null;
  local c75BuiltKeys = {};
  local c75BypassConsumed = false;
  local c121FirstYearAirBatch = C121_CATALOG_AIR_FIRST_YEAR
      && this._generationStageMonth >= 0
      && year == this._generationStageMonth / 12;
  local c121AirBuilt = 0;
  local c121AirChained = 0;
  local c121DeadSkipped = 0;
  /* Sonde PROJECTS_COST (catalog_cost_probe) : repartition des opcodes d'une passe. */
  local pcost = CATALOG_COST_PROBE
      ? { mark = OpexOpsMeasureBegin(), buildOps = 0, fleetOps = 0, regenOps = 0, regenKind = "none" }
      : null;
  if (C75_KPASS_BYPASS) OpexC75BypassEnsureYear(year);
  if (C75_TRACK_PASSES) {
    local now = AIDate.GetCurrentDate();
    OpexC75RecordPassDate(now);
    c75KPassData = OpexC75ComputeKPass(now);
    if (C75_YEAR_LEDGER != null) C75_YEAR_LEDGER.passes++;
  }
  if (spPass != null) {
    local beginCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local beginAvail = OpexAvailableCapital();
    local beginK = (c75KPassData != null && ("K_pass" in c75KPassData)) ? c75KPassData.K_pass : -1;
    local beginPool = (this._projects != null && this._projects.best != null) ? this._projects.best.len() : 0;
    OpexSpanEvent("projects_begin", "cash=" + beginCash + " avail=" + beginAvail + " k_pass=" + beginK + " pool=" + beginPool);
  }
  local c80DiscardsThisPass = 0;

  /* C83.1 : detecter d'abord une transition de slot qui exige un candidat absent,
   * puis reevaluer le petit portefeuille deja finance avant toute depense. */
  if (this._projects != null) {
    if (C83_PREEMPT_OPEN) this._c83PreemptEnqueued = 0;
    local c83TargetedRegens = 0;
    c83TargetedRegens = this._c83WatchAirSlotTransitions();
    if (C83_PREEMPT_OPEN && this._c83PreemptEnqueued > 0) {
      c83TargetedRegens += this._c83PreemptEnqueued;
    }
    if (spPass != null && c83TargetedRegens > 0) {
      OpexSpanEvent("projects_stop", "reason=c83_preempt");
      OpexSpanEnd(spPass);
    }
    if (c83TargetedRegens > 0) return true;
    OpexPromoteLiveDefensiveAir(this._projects, OpexAvailableCapital());
  }

  local c73Cash = 0;
  local c73Avail = 0;
  if (C69_BOTTLENECK_PROBE) {
    c73Cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    c73Avail = OpexAvailableCapital();
    if (C78_SLOT_INTERCEPT_PROBE) this._c78SlotOnProjectsPass();
  }
  local c49Best = null;
  local c49BuiltRanks = null;
  local c49AttemptedRanks = null;
  /* G4§1 : le drapeau peut etre pose entre deux passes par _consumeRailSearch.
   * Ne pas le remettre a zero ici : la passe suivante doit alors re-elire le
   * portefeuille avec la nouvelle memoire d'abandon. */
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
  local c120AirAttempts = 0;
  local c120AirBuilt = false;
  local c120AirLastReason = null;
  local c120AirLastReject = null;
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

  /* C78 / course defensive : le selecteur place un AIR rentable et finançable
   * touchant une grande ville encore prenable en tete. Si un A* rail a deja fini
   * son calcul, lui laisser consommer la caisse ici annulerait cette priorite
   * avant meme la boucle portefeuille. Il cede exactement une passe ; le marqueur
   * vit seulement dans _railSearch (etat deja transitoire et non serialise). */
  local c77DefensiveHead = null;
  if (this._projects != null && this._projects.best != null && this._projects.best.len() > 0) {
    local head = this._projects.best[0];
    if (OpexProjectDefensiveAirPriority(head) > 0
        && OpexProjectFinanceCapital(head) <= OpexAvailableCapital()) {
      c77DefensiveHead = head;
    }
  }
  local c77DeferCompletedRail = c77DefensiveHead != null
      && RAIL_SEARCH_RESUMABLE && this._railSearch != null
      && this._railSearch.kind == "primary" && this._railSearch.phase == "build"
      && !("c77DefensiveDeferred" in this._railSearch);
  if (c77DeferCompletedRail) {
    this._railSearch.c77DefensiveDeferred <- true;
    if (C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=defensive_priority pass=" + C78_SLOT_PASS_COUNTER
          + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
          + " action=defer_rail finance=" + OpexProjectFinanceCapital(c77DefensiveHead)
          + " available=" + OpexAvailableCapital());
    }
  }

  /* La preparation rail cede la passe si l'AIR est finançable, et depose un A*
   * termine avant que la consommation historique ne le construise. */
  if (C121_AIR_FIRST_YEAR_RAIL_PREP) this._c121RailPrepOnPassStart();

  /* A4 : un A* termine au tour precedent a depose un railPlan sur le candidat stocke. On le
   * consomme AVANT le balayage du portefeuille, qui a pu etre regenere entre-temps. */
  if (RAIL_SEARCH_RESUMABLE && this._railSearch != null &&
      this._railSearch.kind == "primary" && this._railSearch.phase == "build"
      && !c77DeferCompletedRail) {
    local spAstarBuild = PROBE_SPAN_TRACE ? OpexSpanBegin("astar.build") : null;
    local railBuilt = this._consumeResumableRailAtPassStart(year, passDiscards, c49Best,
        c49BuiltRanks, c75BuiltKeys, c69BuiltProjects);
    if (spAstarBuild != null) OpexSpanEnd(spAstarBuild);
    if (railBuilt && PROBE_SPAN_TRACE) OpexSpanEvent("line_built", "mode=rail built=1");
    if (MONTHLY_FUNNEL) funnelAttempted++;
    if (railBuilt) builtCount++;
  }

  /* V88 : reprise prioritaire de l'etape 2 d'une chaine de biens en attente.
   * ("cle" in null) tue le script : ne lire la chaine que si elle existe. */
  local step2CanRun = this._railSearch == null;
  if (!step2CanRun && V88_STEP2_PLAN_IMMEDIATE && this._activeGoodsChain != null
      && ("goodsCandidate" in this._activeGoodsChain) && this._activeGoodsChain.goodsCandidate != null
      && ("railPlan" in this._activeGoodsChain.goodsCandidate)
      && this._activeGoodsChain.goodsCandidate.railPlan != null) {
    step2CanRun = true;
  }
  if (V88_GOODS_CHAIN && this._activeGoodsChain != null && this._activeGoodsChain.step == 2
      && this._railSearch != null && !step2CanRun) {
    local v88Own = (("candidate" in this._railSearch) && this._railSearch.candidate != null
        && ("isChainStep2" in this._railSearch.candidate) && this._railSearch.candidate.isChainStep2) ? 1 : 0;
    OpexV88Log("CHAIN_WAIT", "step=2 reason=rail_search own=" + v88Own
               + " kind=" + (("kind" in this._railSearch) ? this._railSearch.kind : "?"));
  }
  if (V88_GOODS_CHAIN && this._activeGoodsChain != null && this._activeGoodsChain.step == 2 && step2CanRun) {
    local step2Built = this._tryBuildGoodsChainStep2(year, passDiscards, anchor, yy);
    if (step2Built) {
      builtCount++;
      if (C69_TRACK_BUILDS && this._lines.len() > 0) {
        c69BuiltProjects.append(this._lines[this._lines.len() - 1]);
      }
    }
  }

  local airTouchedTowns = null;
  if ((C75_MULTI_BUILD || builtCount < maxBatch)
      && this._projects != null && this._projects.best.len() > 0) {
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
  local airReserveTowns = null;
  if (AIR_BATCH_TOWN_RESERVE) airReserveTowns = {};
  local c121Served = C121_TERRITORY_FIRST ? OpexC121ServedAirTowns() : null;
  for (local i = 0; i < this._projects.best.len(); i++) {
    local project = this._projects.best[i];
    if (project == null) continue;
    local railReuseAirOpp = null;
    local railReuseAirShouldDefer = false;
    if ((RAIL_ORIGIN_REUSE_AIR_PRIORITY_SHADOW || RAIL_ORIGIN_REUSE_AIR_PRIORITY)
        && project.mode == "rail"
        && ("payload" in project) && project.payload != null
        && ("originServed" in project.payload) && project.payload.originServed) {
      railReuseAirOpp = OpexRailOriginReuseAirOpportunity(this._projects, project, i, this._lines);
      railReuseAirShouldDefer = railReuseAirOpp != null && railReuseAirOpp.displaced
          && railReuseAirOpp.nextRank == i + 1 && builtCount == 0;
      if (RAIL_ORIGIN_REUSE_AIR_PRIORITY_SHADOW && railReuseAirOpp != null) {
        AILog.Info("RAIL_ORIGIN_REUSE_AIR_PRIORITY rank=" + i
            + " rail_cap=" + railReuseAirOpp.railCap + " available=" + railReuseAirOpp.available
            + " next_air_rank=" + railReuseAirOpp.nextRank + " air_cap=" + railReuseAirOpp.airCap
            + " air_fundable=" + (railReuseAirOpp.airFundableNow ? 1 : 0)
            + " displaced=" + (railReuseAirOpp.displaced ? 1 : 0)
            + " immediate=" + (railReuseAirOpp.nextRank == i + 1 ? 1 : 0)
            + " built_before=" + builtCount);
      }
      if (railReuseAirShouldDefer && RAIL_ORIGIN_REUSE_AIR_PRIORITY) {
        AILog.Info("RAIL_ORIGIN_REUSE_AIR_PRIORITY_DEFER rank=" + i
            + " next_air_rank=" + railReuseAirOpp.nextRank
            + " rail_cap=" + railReuseAirOpp.railCap + " air_cap=" + railReuseAirOpp.airCap
            + " available=" + railReuseAirOpp.available + " built_before=" + builtCount);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
          passDiscards.append({ rank = i, mode = "rail", src = project.src, dst = project.dst,
                                reason = "rail_origin_reuse_air_priority",
                                extra = "next_air_rank=" + railReuseAirOpp.nextRank
                                    + " air_cap=" + railReuseAirOpp.airCap });
        continue;
      }
    }
    local c121LiveOpp = null;
    local c121LiveShouldDefer = false;
    if ((C121_AIR_FIRST_LIVE_SHADOW || C121_AIR_FIRST_LIVE_AIR_PRIORITY)
        && project.mode == "fleet"
        && ("payload" in project) && project.payload != null
        && ("c121FirstLive" in project.payload) && project.payload.c121FirstLive) {
      c121LiveOpp = OpexC121FirstLiveAirOpportunity(this._projects, project, i, this._lines);
      /* Calculer la condition complete dans les DEUX bras quand le shadow est actif.
       * Sinon le simple toggle ON paie davantage d'opcodes avant toute defer réelle et
       * peut déplacer la cadence du scheduler. Le seul chemin divergent doit commencer
       * au moment où une substitution immédiate est effectivement disponible. */
      c121LiveShouldDefer = c121LiveOpp != null && c121LiveOpp.displaced
          && c121LiveOpp.nextRank == i + 1 && builtCount == 0;
      if (C121_AIR_FIRST_LIVE_SHADOW && c121LiveOpp != null) {
        local liveLine = project.payload.line;
        local liveLineId = (liveLine != null && ("lineId" in liveLine)) ? liveLine.lineId : -1;
        local liveSig = c121LiveOpp.nextRank + ":" + (c121LiveOpp.airFundableNow ? 1 : 0)
            + ":" + (c121LiveOpp.displaced ? 1 : 0);
        if (!(liveLineId in C121_AIR_FIRST_LIVE_PRIORITY_STATE)
            || C121_AIR_FIRST_LIVE_PRIORITY_STATE[liveLineId] != liveSig) {
          C121_AIR_FIRST_LIVE_PRIORITY_STATE.rawset(liveLineId, liveSig);
          AILog.Info("C121_FIRST_LIVE_PRIORITY line=" + liveLineId + " rank=" + i
              + " fleet_cap=" + c121LiveOpp.fleetCap + " available=" + c121LiveOpp.available
              + " next_air_rank=" + c121LiveOpp.nextRank + " air_cap=" + c121LiveOpp.airCap
              + " air_fundable=" + (c121LiveOpp.airFundableNow ? 1 : 0)
              + " displaced=" + (c121LiveOpp.displaced ? 1 : 0)
              + " immediate=" + (c121LiveOpp.nextRank == i + 1 ? 1 : 0)
              + " built_before=" + builtCount);
        }
      }
      if (c121LiveShouldDefer) {
        if (C121_AIR_FIRST_LIVE_AIR_PRIORITY) {
          AILog.Info("C121_FIRST_LIVE_PRIORITY_DEFER line="
              + (("payload" in project) && project.payload != null
                  && ("line" in project.payload) && project.payload.line != null
                  && ("lineId" in project.payload.line) ? project.payload.line.lineId : -1)
              + " rank=" + i + " next_air_rank=" + c121LiveOpp.nextRank
              + " fleet_cap=" + c121LiveOpp.fleetCap + " air_cap=" + c121LiveOpp.airCap
              + " available=" + c121LiveOpp.available + " built_before=" + builtCount);
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
            passDiscards.append({ rank = i, mode = "fleet", src = project.src, dst = project.dst,
                                  reason = "c121_first_live_air_priority",
                                  extra = "next_air_rank=" + c121LiveOpp.nextRank
                                      + " air_cap=" + c121LiveOpp.airCap });
          continue;
        }
      }
    }
    if (c121Served != null && !OpexC121ProjectIsTerritorial(project, c121Served)) {
      /* Territoire d'abord : reserver le financement du prochain projet territorial
       * encore a tenter dans cette passe ; les autres chantiers se font sur le reste. */
      local reserve = 0;
      for (local j = i + 1; j < this._projects.best.len(); j++) {
        local next = this._projects.best[j];
        if (next != null && OpexC121ProjectIsTerritorial(next, c121Served)) {
          reserve = OpexProjectFinanceCapital(next);
          break;
        }
      }
      if (reserve > 0 && OpexAvailableCapital() - OpexProjectFinanceCapital(project) < reserve) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
          passDiscards.append({ rank = i, mode = project.mode,
                                src = ("src" in project) ? project.src : -1,
                                dst = ("dst" in project) ? project.dst : -1,
                                reason = "c121_territory_reserve", extra = "reserve=" + reserve });
        continue;
      }
    }

    if (C75_MULTI_BUILD && (OpexC69AttemptKey(project) in c75BuiltKeys)) continue;

    local r1r3BypassBefore = false;
    local r1r3Threshold = 0;
    if (R1_R3_TEST_ONLY && project.mode == "air") {
      r1r3BypassBefore = c75BypassConsumed;
      r1r3Threshold = c75KPassData != null ? c75KPassData.K_pass : 0;
      OpexR1R3AirTrace(this, project, i, "examine", "entry", r1r3BypassBefore,
          r1r3BypassBefore, builtCount, r1r3Threshold);
    }

    /* Un site pris par un chantier precedent rend les autres plans de ce
     * portefeuille caducs. R3 : les ecarter avant K_pass et son bypass aussi
     * au defaut, pas uniquement dans le batch C121 de premiere annee. */
    if (project.mode == "air"
        && !OpexAirBatchPlanStillLive(project.payload, this._lines)) {
      if (R1_R3_TEST_ONLY) OpexR1R3AirTrace(this, project, i, "reject", "batch_plan_dead",
          r1r3BypassBefore, r1r3BypassBefore, builtCount, r1r3Threshold);
      if (c121FirstYearAirBatch) c121DeadSkipped++;
      if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveNote("batch_plan_dead", 1);
      if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
          || C120_AIR_TERRITORIAL_RANKING || C122_AIR_THREAT_PROBE) {
        local plan = project.payload;
        passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile,
                              dst = plan.siteB.town.tile, reason = "batch_plan_dead", extra = "" });
      }
      continue;
    }

    local c121ChainAttempt = false;
    if (C75_MULTI_BUILD && builtCount > 0) {
      local projCap = OpexProjectFinanceCapital(project);
      local c75KPass = (c75KPassData != null) ? c75KPassData.K_pass : 0;
      local availCap = -1;
      if (projCap >= c75KPass) {
        local c75BypassThisProject = false;
        if (c121FirstYearAirBatch && project.mode == "air") {
          availCap = OpexAvailableCapital();
          if (projCap <= availCap) {
            c75BypassThisProject = true;
            c121ChainAttempt = true;
          }
        } else if (C75_KPASS_BYPASS && OpexC75KPassBypassIsNewLine(project)) {
          availCap = OpexAvailableCapital();
          if (projCap <= availCap) {
            OpexC75BypassRecordEligible(year, project, projCap, availCap, c75KPass,
                                        builtCount, c75BypassConsumed);
            if (!c75BypassConsumed) {
              c75BypassConsumed = true;
              c75BypassThisProject = true;
                if (R1_R3_TEST_ONLY && project.mode == "air") OpexR1R3AirTrace(this, project, i,
                  "consume", "eligible", false, c75BypassConsumed, builtCount, c75KPass, projCap, availCap);
              OpexC75BypassRecordConsumed(year, project, projCap, availCap, c75KPass, builtCount);
            }
          }
        }
          if (!c75BypassThisProject) {
            c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";
            if (R1_R3_TEST_ONLY && project.mode == "air") OpexR1R3AirTrace(this, project, i,
              "stop", c75StopReason, c75BypassConsumed, c75BypassConsumed,
              builtCount, c75KPass, projCap, availCap >= 0 ? availCap : null);
          if (C78_SLOT_INTERCEPT_PROBE) {
            OpexC78SlotLog("phase=pass_stop pass=" + C78_SLOT_PASS_COUNTER
                + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
                + " reason=" + c75StopReason + " next_rank=" + i + " next_mode=" + project.mode
                + " finance=" + projCap + " threshold=" + c75KPass
                + (availCap >= 0 ? " available=" + availCap : ""));
          }
          local c121KPassAirAhead = null;
          local c121StopAvailable = -1;
          if (C121_KPASS_SHADOW || C121_KPASS_AIR_CONTINUE) {
            c121StopAvailable = availCap >= 0 ? availCap : OpexAvailableCapital();
            if (c75StopReason == "k_pass" && project.mode == "fleet") {
              c121KPassAirAhead = OpexC121KPassFundableAirAhead(
                  this._projects, i, c121StopAvailable, this._lines);
            }
          }
          if (C121_KPASS_SHADOW) {
            OpexC121KPassShadow(this._projects, project, i, projCap, c75KPass,
                               c121StopAvailable, c75StopReason);
          }
          if (c121KPassAirAhead != null && C121_KPASS_AIR_CONTINUE) {
            AILog.Info("C121_KPASS_AIR_CONTINUE fleet_rank=" + i
                + " air_rank=" + c121KPassAirAhead.rank + " fleet_cap=" + projCap
                + " air_cap=" + c121KPassAirAhead.cap + " k_pass=" + c75KPass
                + " available=" + c121StopAvailable);
            continue;
          }
          break;
        }
      }
      if (availCap < 0) availCap = OpexAvailableCapital();
      if (projCap > availCap) {
        c75StopReason = "cash";
        if (R1_R3_TEST_ONLY && project.mode == "air") OpexR1R3AirTrace(this, project, i,
            "cash_note", "cash", c75BypassConsumed, c75BypassConsumed,
            builtCount, c75KPass, projCap, availCap);
        if (C78_SLOT_INTERCEPT_PROBE) {
          OpexC78SlotLog("phase=pass_stop pass=" + C78_SLOT_PASS_COUNTER
              + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
              + " reason=cash next_rank=" + i + " next_mode=" + project.mode
              + " finance=" + projCap + " available=" + availCap);
        }
      }
      if (C80_MARGINAL_FLOOR) {
        if (OpexC80ProjectBelowMarginalFloor(this._lines, project)) {
          c80DiscardsThisPass++;
          if (C69_BOTTLENECK_PROBE) {
            OpexC80RecordMarginalDiscard(year, i, project);
          }
          continue;
        }
      }
    }

    local mode = project.mode;
    local modeChar = mode == "rail" ? "T" : (mode == "road" ? "R" : (mode == "air" ? "A" : "W"));
    local liveBuiltCount = builtCount;
    if (MONTHLY_FUNNEL) funnelAttempted++;

    if (mode == "fleet") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local c78DiscardsLen = (C69_BOTTLENECK_PROBE && passDiscards != null) ? passDiscards.len() : 0;
      local attempt = this._tryBuildFleetProject(year, project, i, passDiscards);
      passDiscards = attempt.discards;
      if (C69_BOTTLENECK_PROBE) OpexC78LogBuild(year, i, mode, project, attempt, passDiscards, c78DiscardsLen);
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "pending") {
        if (C49_SCARCITY_LEDGER && this._c49ScarcityLedger != null) {
          this._c49ScarcityLedger.stop_rail_search++;
        }
        if (C78_SLOT_INTERCEPT_PROBE) {
          OpexC78SlotLog("phase=pass_stop pass=" + C78_SLOT_PASS_COUNTER
              + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
              + " reason=rail_search blocker_rank=" + i + " blocker_mode=fleet"
              + " built_before=" + builtCount);
        }
        /* Le creneau de recherche est pris. Une passe deja productive regenere
         * d'abord ; sinon on rend la main tout de suite, comme une ligne neuve. */
        if (builtCount > 0) {
          if (C75_TRACK_PASSES) c75StopReason = "rail_search";
          break;
        }
        this._finalizeProjectsPassDiagnostics(builtCount, c49Best, c49BuiltRanks,
            c49AttemptedRanks, passDiscards, c73Cash, c73Avail, funnelAttempted, false,
            c75StopReason);
        if (C75_TRACK_PASSES && builtCount > 0) {
          if (C75_KPASS_BYPASS) OpexC75BypassRecordStop("rail_search");
          OpexC75RecordPassOutcome(year, builtCount, c75KPassData, "rail_search");
        }
        if (spPass != null) {
          OpexSpanEvent("projects_stop", "reason=rail_search");
          OpexSpanEnd(spPass);
        }
        /* Parentheses : le diagnostic post-build ancre l'unique retour rail. */
        return (true);
      }
      if (attempt.outcome == "built") {
        this._recordPortfolioProjectBuilt(project, i, c75BuiltKeys, c69BuiltProjects);
        builtCount++;
        if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      }
      continue;
    }

    if (mode == "air") {
      if (AIR_BATCH_TOWN_RESERVE && airReserveTowns != null
          && OpexAirBatchTownReserveHit(airReserveTowns, project)) {
        OpexAirBatchTownReserveNote("dropped", 1);
        continue;
      }
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local c120DiscardStart = C120_AIR_TERRITORIAL_RANKING ? passDiscards.len() : 0;
      if (C120_AIR_TERRITORIAL_RANKING) c120AirAttempts++;
      local c78DiscardStart = C78_SLOT_INTERCEPT_PROBE ? passDiscards.len() : 0;
      local c78DiscardsLen = (C69_BOTTLENECK_PROBE && passDiscards != null) ? passDiscards.len() : 0;
      if (C78_SLOT_INTERCEPT_PROBE) {
        this._c78LogAirSlotLine("air_attempt", project, i,
            " finance=" + OpexProjectFinanceCapital(project)
            + " available=" + OpexAvailableCapital() + " built_before=" + liveBuiltCount);
      }
      OpexC122ThreatNoteAttempt(project, i, liveBuiltCount);
      local r1r3DiscardStart = R1_R3_TEST_ONLY ? passDiscards.len() : 0;
      local r1r3LinesBefore = R1_R3_TEST_ONLY ? this._lines.len() : 0;
      if (R1_R3_TEST_ONLY) OpexR1R3AirTrace(this, project, i, "attempt", "executor",
          c75BypassConsumed, c75BypassConsumed, liveBuiltCount, r1r3Threshold);
      local attempt = this._tryBuildAirProject(year, project, i, liveBuiltCount, passDiscards,
                                                anchor, yy);
      if (R1_R3_TEST_ONLY) {
        local reason = attempt.outcome;
        local error = "unknown";
        local detail = "unknown";
        for (local k = r1r3DiscardStart; k < attempt.discards.len(); k++) {
          local discard = attempt.discards[k];
          if (discard.mode != "air" || discard.rank != i) continue;
          reason = discard.reason;
          if ("error" in discard) error = discard.error;
          if ("detail" in discard) detail = discard.detail;
        }
        OpexR1R3AirTrace(this, project, i, "result", reason,
            c75BypassConsumed, c75BypassConsumed, liveBuiltCount, r1r3Threshold, null, null,
            " outcome=" + attempt.outcome + " error=" + error + " detail=" + detail
            + " lines_before=" + r1r3LinesBefore + " lines_after=" + this._lines.len());
      }
      OpexC122ThreatNoteOutcome(project, i, attempt);
      OpexC122ThreatRetryUnbuildable(this, project, i, attempt);
      passDiscards = attempt.discards;
      if (C120_AIR_TERRITORIAL_RANKING) {
        if (attempt.outcome == "built") {
          c120AirBuilt = true;
          c120AirLastReason = "built";
        } else {
          c120AirLastReason = attempt.outcome;
          for (local c120k = c120DiscardStart; c120k < passDiscards.len(); c120k++) {
            local c120d = passDiscards[c120k];
            if (c120d != null && ("mode" in c120d) && c120d.mode == "air"
                && ("rank" in c120d) && c120d.rank == i && ("reason" in c120d)) {
              c120AirLastReason = c120d.reason;
            }
          }
          c120AirLastReject = c120AirLastReason;
        }
      }
      if (C69_BOTTLENECK_PROBE) OpexC78LogBuild(year, i, mode, project, attempt, passDiscards, c78DiscardsLen);
      if (C78_SLOT_INTERCEPT_PROBE) {
        local c78Reason = (attempt.outcome == "built") ? "built" : "unknown";
        local c78Detail = "";
        local c78Error = 0;
        for (local k = c78DiscardStart; k < passDiscards.len(); k++) {
          local d = passDiscards[k];
          if (d != null && d.mode == "air" && d.rank == i) {
            c78Reason = d.reason;
            c78Detail = ("detail" in d) ? d.detail : "";
            c78Error = ("error" in d) ? d.error : 0;
          }
        }
        this._c78LogAirSlotLine("air_outcome", project, i,
            " outcome=" + attempt.outcome + " reason=" + c78Reason
            + " detail=" + c78Detail + " error=" + c78Error);
      }
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (c121FirstYearAirBatch) {
          c121AirBuilt++;
          if (c121ChainAttempt) c121AirChained++;
        }
        this._recordPortfolioProjectBuilt(project, i, c75BuiltKeys, c69BuiltProjects);
        builtCount++;
        if (airTouchedTowns == null) airTouchedTowns = {};
        local plan = project.payload;
        local tA = ("siteA" in plan && "town" in plan.siteA && "id" in plan.siteA.town) ? plan.siteA.town.id : -1;
        local tB = ("siteB" in plan && "town" in plan.siteB && "id" in plan.siteB.town) ? plan.siteB.town.id : -1;
        if (tA >= 0) airTouchedTowns.rawset(tA, true);
        if (tB >= 0) airTouchedTowns.rawset(tB, true);
        if (PROBE_SPAN_TRACE) {
          local airPlanes = ("planes" in plan) ? plan.planes : 0;
          /* task_air emet deja line_built ; ici, le capital de financement de la passe. */
          OpexSpanEvent("air_pass_built", "towns=" + tA + "," + tB
              + " finance=" + OpexProjectFinanceCapital(project) + " planes=" + airPlanes);
        }
        if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      }
    } else if (mode == "road") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local c78DiscardsLen = (C69_BOTTLENECK_PROBE && passDiscards != null) ? passDiscards.len() : 0;
      local attempt = this._tryBuildRoadProject(year, project, i, passDiscards, anchor, yy);
      passDiscards = attempt.discards;
      if (C69_BOTTLENECK_PROBE) OpexC78LogBuild(year, i, mode, project, attempt, passDiscards, c78DiscardsLen);
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (fallthroughProbeActive) {
        fallthroughAttempted++;
        if (attempt.outcome == "built") fallthroughBuilt++;
      }
      if (attempt.outcome == "built") {
        if (PROBE_SPAN_TRACE) OpexSpanEvent("line_built", "mode=road built=1");
        this._recordPortfolioProjectBuilt(project, i, c75BuiltKeys, c69BuiltProjects);
        builtCount++;
        if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      }
    } else if (mode == "rail") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local c78DiscardsLen = (C69_BOTTLENECK_PROBE && passDiscards != null) ? passDiscards.len() : 0;
      local attempt = this._tryBuildRailProject(year, project, i, liveBuiltCount, passDiscards,
                                                 anchor, yy);
      passDiscards = attempt.discards;
      if (C69_BOTTLENECK_PROBE) OpexC78LogBuild(year, i, mode, project, attempt, passDiscards, c78DiscardsLen);
      if (C49_SCARCITY_LEDGER && attempt.outcome == "built") c49BuiltRanks.rawset(i, true);
      if (attempt.outcome == "pending") {
        if (C49_SCARCITY_LEDGER && this._c49ScarcityLedger != null) {
          this._c49ScarcityLedger.stop_rail_search++;
        }
        if (C78_SLOT_INTERCEPT_PROBE) {
          OpexC78SlotLog("phase=pass_stop pass=" + C78_SLOT_PASS_COUNTER
              + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
              + " reason=rail_search blocker_rank=" + i + " blocker_mode=rail"
              + " built_before=" + builtCount);
        }
        /* En batch historique > 1, le portefeuille doit etre regenere avant de reprendre un
         * A* suspendu. Le defaut unitaire conserve le retour immediat d'origine. */
        if (builtCount > 0) {
          if (C75_TRACK_PASSES) c75StopReason = "rail_search";
          break;
        }
        this._finalizeProjectsPassDiagnostics(builtCount, c49Best, c49BuiltRanks,
            c49AttemptedRanks, passDiscards, c73Cash, c73Avail, funnelAttempted, false,
            c75StopReason);
        if (C75_TRACK_PASSES && builtCount > 0) {
          if (C75_KPASS_BYPASS) OpexC75BypassRecordStop("rail_search");
          OpexC75RecordPassOutcome(year, builtCount, c75KPassData, "rail_search");
        }
        if (spPass != null) {
          OpexSpanEvent("projects_stop", "reason=rail_search");
          OpexSpanEnd(spPass);
        }
        return true;
      }
      if (attempt.outcome == "built") {
        if (PROBE_SPAN_TRACE) OpexSpanEvent("line_built", "mode=rail built=1");
        this._recordPortfolioProjectBuilt(project, i, c75BuiltKeys, c69BuiltProjects);
        builtCount++;
        if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
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
        if (PROBE_SPAN_TRACE) OpexSpanEvent("line_built", "mode=water built=1");
        this._recordPortfolioProjectBuilt(project, i, c75BuiltKeys, c69BuiltProjects);
        builtCount++;
        if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      }
    }
    if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();
  }
  if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();
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

  if (C120_AIR_TERRITORIAL_RANKING) {
    OpexC120FinalizeProjectsPass(c120AirBuilt, c120AirAttempts, c120AirLastReason,
        c120AirLastReject, c75StopReason, builtCount);
  }

  this._finalizeProjectsPassDiagnostics(builtCount, c49Best, c49BuiltRanks,
      c49AttemptedRanks, passDiscards, c73Cash, c73Avail, funnelAttempted, true,
      c75StopReason);
  if (c121FirstYearAirBatch && CATALOG_COST_PROBE) {
    local c121Date = AIDate.GetCurrentDate();
    AILog.Info("OPEX " + AIDate.GetYear(c121Date) + "-"
        + AIDate.GetMonth(c121Date) + "-" + AIDate.GetDayOfMonth(c121Date)
        + " C121_AIR_CHAIN_PASS built_air=" + c121AirBuilt
        + " chained_air=" + c121AirChained
        + " dead_skipped=" + c121DeadSkipped
        + " total_built=" + builtCount
        + " stop=" + (c75StopReason != null ? c75StopReason : "none"));
  }
  if (C69_TRACK_BUILDS && builtCount > 0) {
    this._recordC69BuildingPass(year, c69PassProjects != null ? c69PassProjects : this._projects, c69BuiltProjects);
  }
  if (C75_TRACK_PASSES) {
    c75StopReason = this._finalizeC75PassOutcome(year, builtCount, c75KPassData,
        c75StopReason, c80DiscardsThisPass);
  }

  /* G4§1 : l'ancien chemin deduisait hadAbandons de passDiscards, dont le remplissage
   * est garde par DECISION_LOG (defaut 0). Le drapeau _hadAbandonsThisPass est pose
   * directement par _markPairAbandoned, couvrant tous les chemins (air, route, rail
   * bloquant et reprenable via _consumeRailSearch). */
  local hadAbandons = this._hadAbandonsThisPass;
  if (pcost != null) {
    pcost.buildOps = OpexOpsMeasureEnd(pcost.mark);
    pcost.mark = OpexOpsMeasureBegin();
  }
  if (builtCount > 0 || hadAbandons) {
    local fleetPlan = null;
    if (FLEET_PORTFOLIO) {
      /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
      fleetPlan = [];
      this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    }
    if (pcost != null) {
      pcost.fleetOps = OpexOpsMeasureEnd(pcost.mark);
      pcost.mark = OpexOpsMeasureBegin();
      pcost.regenKind = (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) ? "staged_full"
          : ((PORTFOLIO_CACHE && this._projects != null && ("candidateGroups" in this._projects))
              ? "incremental" : "full");
    }
    local spPost = null;
    if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      spPost = PROBE_SPAN_TRACE ? OpexSpanBegin("projects.post_regen.staged_full") : null;
      this._rebuildProjects(fleetPlan);
      if (spPost != null) OpexSpanEnd(spPost);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = (c76Ops + 93000) / 186000;
        this._c76RecordRegen("full", c76Ops, c76Days, year, "staged");
      }
    } else if (PORTFOLIO_CACHE && this._projects != null && ("candidateGroups" in this._projects)) {
      local budgetNow = OpexAvailableCapital();
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      spPost = PROBE_SPAN_TRACE ? OpexSpanBegin("projects.post_regen.incremental") : null;
      if (C80_RAIL_STOCK_GATE) {
        if (C80_RAIL_STOCK_WORKER)
          this._projects.candidateGroups = OpexRailStockStripCandidateGroups(this._projects.candidateGroups);
        this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs, airTouchedTowns, this._railReadyStock);
      } else if (C121_AIR_FIRST_YEAR_RAIL_PREP) {
        this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs, airTouchedTowns, this._railReadyStock);
      } else {
        this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs, airTouchedTowns);
      }
      if (spPost != null) OpexSpanEnd(spPost);
      if (PROBE_SPAN_TRACE && C121_CATALOG_INCREMENTAL
          && airTouchedTowns != null && airTouchedTowns.len() > 0) {
        OpexSpanEvent("c121_deferred_regen", "towns=" + airTouchedTowns.len());
      }
      if (C80_RAIL_STOCK_WORKER && C80_RAIL_STOCK_GATE) this._updateRailStockSelectionThreshold();
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = (c76Ops + 93000) / 186000;
        this._c76RecordRegen("incremental", c76Ops, c76Days, year, "post_build");
      }
      /* C76 : la mise a jour incrementale vient d'integrer la ligne construite ; acquitter la
       * couche `lines` evite qu'elle declenche a elle seule une regeneration complete au tour
       * suivant (mesure : 109 regenerations "layers" sur 133). Les autres couches restent dues. */
      if (C76_REGEN_TARGETED && this._c76AckRevisions != null && this._c76Revisions != null
          && !(C121_CATALOG_INCREMENTAL && airTouchedTowns != null && airTouchedTowns.len() > 0)) {
        this._c76AckRevisions.lines = this._c76Revisions.lines;
      }
    } else {
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      spPost = PROBE_SPAN_TRACE ? OpexSpanBegin("projects.post_regen.full") : null;
      this._rebuildProjects(fleetPlan);
      if (spPost != null) OpexSpanEnd(spPost);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = (c76Ops + 93000) / 186000;
        this._c76RecordRegen("full", c76Ops, c76Days, year, "post_build");
      }
    }
    if (pcost != null) pcost.regenOps = OpexOpsMeasureEnd(pcost.mark);
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
             + this._projects.stats.selectedCapital + "|B" + builtCount);
    /* L'abandon a maintenant ete consomme par la reelection/reconstruction. */
    if (hadAbandons) this._hadAbandonsThisPass = false;
    if (C80_RAIL_STOCK_GATE && C80_RAIL_STOCK_WORKER && this._activeWorker == null && this._railReadyStock.len() < 1) {
      this._tryStartRailStockWorker();
    }
    if (pcost != null) OpexProjectsCostLog(pcost, builtCount, c75StopReason);
    if (spPass != null) {
      local stopTok = c75StopReason != null ? c75StopReason : (builtCount > 0 ? "built" : "list_end");
      OpexSpanEvent("projects_stop", "reason=" + stopTok);
      OpexSpanEnd(spPass);
    }
    if (C121_AIR_FIRST_YEAR_RAIL_PREP) {
      local spPrep = PROBE_SPAN_TRACE ? OpexSpanBegin("railprep.after_pass") : null;
      this._c121RailPrepAfterProjectsPass();
      if (spPrep != null) OpexSpanEnd(spPrep);
    }
    return true;
  }
  if (pcost != null) OpexProjectsCostLog(pcost, builtCount, c75StopReason);
  if (C80_RAIL_STOCK_GATE && C80_RAIL_STOCK_WORKER && this._activeWorker == null && this._railReadyStock.len() < 1) {
    this._tryStartRailStockWorker();
  }
  if (spPass != null) {
    local stopTokIdle = c75StopReason != null ? c75StopReason : (builtCount > 0 ? "built" : "list_end");
    OpexSpanEvent("projects_stop", "reason=" + stopTokIdle);
    OpexSpanEnd(spPass);
  }
  if (C121_AIR_FIRST_YEAR_RAIL_PREP) {
    local spPrep = PROBE_SPAN_TRACE ? OpexSpanBegin("railprep.after_pass") : null;
    this._c121RailPrepAfterProjectsPass();
    if (spPrep != null) OpexSpanEnd(spPrep);
  }
  return false;
}
function OpexAI::_rebuildProjects(fleetPlan, airOverride = null, advanceStage = true)
{
  if (C121_CATALOG_AIR_FIRST_YEAR) {
    local yearNow = AIDate.GetYear(AIDate.GetCurrentDate());
    if (this._generationStageMonth < 0)
      this._generationStageMonth = yearNow * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
    C121_CATALOG_FIRST_YEAR_ACTIVE = yearNow == this._generationStageMonth / 12;
  }
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
  /* C78.4 : pendant un parcours AIR grande carte encore actif, un rebuild
   * post-chantier ne doit jamais retomber dans OpexAirPlans synchrone. Recycler
   * le lot AIR du portefeuille courant pendant que le curseur catalogue produit
   * le prochain lot en prive. Le bootstrap reste sur la meme etape jusqu'a la
   * fin du scan. */
  if (airOverride == null && this._catalog != null && ("towns" in this._catalog)
      && this._catalog.towns != null
      && OpexAirTownPoolLimit(this._catalog.towns) > 64
      && this._projects != null && this._taskQueue != null) {
    local c78Pending = false;
    foreach (task in this._taskQueue) {
      if (task != null && ("name" in task) && task.name == "catalog"
          && ("c78AirRebuild" in task) && task.c78AirRebuild != null) {
        c78Pending = true;
        break;
      }
    }
    if (c78Pending) {
      airOverride = {
        complete = true,
        airPlan = ("airPlan" in this._projects) ? this._projects.airPlan : null,
        airPlans = ("airPlans" in this._projects) ? this._projects.airPlans : [],
        airOps = ("airPlanningOpcodes" in this._projects) ? this._projects.airPlanningOpcodes : 0,
      };
      advanceStage = false;
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
  if (C80_RAIL_STOCK_GATE) {
    this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines,
        fleetPlan, this._abandonedPairs, stage, prior,
        freightCargo, freightCargos, this._activeSubsidies,
        airOverride, this._railReadyStock);
    if (C80_RAIL_STOCK_WORKER) {
      this._projects.railStockAI <- this;
      this._updateRailStockSelectionThreshold();
    }
  } else if (C121_AIR_FIRST_YEAR_RAIL_PREP) {
    this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines,
        fleetPlan, this._abandonedPairs, stage, prior,
        freightCargo, freightCargos, this._activeSubsidies,
        airOverride, this._railReadyStock);
  } else {
    this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines,
        fleetPlan, this._abandonedPairs, stage, prior,
        freightCargo, freightCargos, this._activeSubsidies,
        airOverride);
  }
  if (stage == OPEX_STAGE_COMPLETE && b6StaleProjects != null) {
    OpexB6LogFreshEquivalence(b6StaleProjects, this._projects, b6StaleDate);
  }
  local actualFreightCargo = (this._projects != null && ("freightCargo" in this._projects))
      ? this._projects.freightCargo : freightCargo;
  if (advanceStage && stage == OPEX_STAGE_AIR_ONLY && actualFreightCargo != null) {
    this._bootstrapFreightCargo = actualFreightCargo;
  }
  /* Le bootstrap utilise le meme premier cargo pour son rail (etape 0) puis
   * sa route (etape 3). Ensuite chaque passe complete ne porte que sur le
   * cargo suivant : prior reste null en regime complet, donc le portefeuille
   * ne regrossit jamais par accumulation des anciens lots fret. */
  if (advanceStage && freightCargos.len() > 0
      && (stage == OPEX_STAGE_ROUTE_ONLY || stage == OPEX_STAGE_COMPLETE)) {
    if (actualFreightCargo != null) this._lastFreightCargo = actualFreightCargo;
    if (stage == OPEX_STAGE_ROUTE_ONLY) this._bootstrapFreightCargo = -1;
  }
  if (advanceStage && STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
    local fromStage = this._generationStage;
    this._generationStage++;
    if (PROBE_SPAN_TRACE) OpexSpanEvent("bootstrap_stage", "from=" + fromStage + " to=" + this._generationStage);
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
