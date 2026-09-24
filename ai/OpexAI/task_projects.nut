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
    local grown = OpexAirAddPlane(line, this._catalog);
    if (("reason" in grown) && (grown.reason == "REEEQUIP_WAIT" || grown.reason == "REPLACE" || grown.reason == "REEEQUIP_FAIL" || grown.reason == "REEEQUIP_ABORT")) {
      if (grown.reason == "REPLACE" && ("vehCount" in grown)) {
        line.vehCount <- grown.vehCount;
        line.trains = grown.vehCount;
        added += 1;
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

function OpexC83LogSlotClosure(townId, previous, remaining, ownPresent, ownCount)
{
  if (!C78_SLOT_INTERCEPT_PROBE || remaining != 0) return;
  if (previous != 1 && previous != 11 && previous != 2) return;
  local claimed = (previous == 11) ? (ownCount >= 2) : ownPresent;
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

function OpexC83WatchOneTown(ai, townId, ownCounts, today, rearmDays)
{
  local remaining = AITown.GetAllowedNoise(townId);
  local ownCount = (townId in ownCounts) ? ownCounts[townId] : 0;
  local ownPresent = ownCount > 0;
  local state = remaining + (ownPresent ? 10 : 0);
  local previous = (townId in ai._c83SlotWatch) ? ai._c83SlotWatch[townId] : 2;
  OpexC83LogSlotClosure(townId, previous, remaining, ownPresent, ownCount);

  if (ownPresent || remaining != 1) {
    ai._c83SlotWatch.rawset(townId, state);
    /* La course n'est plus l'etat 1 : le plafond de rearm ne doit pas
     * bloquer une prochaine ouverture de ce slot. */
    if (townId in ai._c83SlotRace) delete ai._c83SlotRace[townId];
    return 0;
  }

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
    ai._c83SlotRace.rawset(townId, today);
    ai._c83SlotWatch.rawset(townId, state);
    if (C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=c83_slot_watch town=" + townId
          + " previous=" + previous + " remaining=1 action=targeted_regen");
    }
    return 1;
  }
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

/* C83.1 : equivalent d'un evenement "un concurrent vient de prendre le premier
 * slot", absent de NoAI. On ne surveille que les K grandes villes early-slot et
 * GetAllowedNoise est O(1). Le cache encode (slots restants + 10 si Opex y est
 * deja present), afin de reagir aussi si notre aeroport disparait alors que le
 * total reste a un slot. La regeneration C77 est ciblee sur UNE ville et sa cle
 * reactive assure la coalescence. */
function OpexAI::_c83WatchAirSlotTransitions()
{
  if (this._catalog == null || !OpexAirC83SlotSignalEnabled()) return 0;
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
      enqueued++;
      if (C78_SLOT_INTERCEPT_PROBE) {
        OpexC78SlotLog("phase=c83_slot_watch town=" + town.id
            + " previous=" + previous + " remaining=1 action=targeted_regen");
      }
    } else if (C78_SLOT_INTERCEPT_PROBE) {
      OpexC78SlotLog("phase=c83_slot_watch town=" + town.id
          + " previous=" + previous + " remaining=1 action=enqueue_failed");
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
  local c80DiscardsThisPass = 0;

  /* C83.1 : detecter d'abord une transition de slot qui exige un candidat absent,
   * puis reevaluer le petit portefeuille deja finance avant toute depense. */
  if (this._projects != null) {
    local c83TargetedRegens = this._c83WatchAirSlotTransitions();
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

  /* A4 : un A* termine au tour precedent a depose un railPlan sur le candidat stocke. On le
   * consomme AVANT le balayage du portefeuille, qui a pu etre regenere entre-temps. */
  if (RAIL_SEARCH_RESUMABLE && this._railSearch != null &&
      this._railSearch.kind == "primary" && this._railSearch.phase == "build"
      && !c77DeferCompletedRail) {
    local railCandidate = this._railSearch.candidate;
    local c78DiscardsLenRail = (C69_BOTTLENECK_PROBE && passDiscards != null) ? passDiscards.len() : 0;
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
      }
    }
  }

  /* V88 : reprise prioritaire de l'etape 2 d'une chaine de biens en attente */
  if (V88_GOODS_CHAIN && this._activeGoodsChain != null && this._activeGoodsChain.step == 2
      && this._railSearch != null) {
    local v88Own = (("candidate" in this._railSearch) && this._railSearch.candidate != null
        && ("isChainStep2" in this._railSearch.candidate) && this._railSearch.candidate.isChainStep2) ? 1 : 0;
    OpexV88Log("CHAIN_WAIT", "step=2 reason=rail_search own=" + v88Own
               + " kind=" + (("kind" in this._railSearch) ? this._railSearch.kind : "?"));
  }
  if (V88_GOODS_CHAIN && this._activeGoodsChain != null && this._activeGoodsChain.step == 2 && this._railSearch == null) {
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
  for (local i = 0; i < this._projects.best.len(); i++) {
    local project = this._projects.best[i];
    if (project == null) continue;

    if (C75_MULTI_BUILD && (OpexC69AttemptKey(project) in c75BuiltKeys)) continue;

    if (C75_MULTI_BUILD && builtCount > 0) {
      local projCap = OpexProjectFinanceCapital(project);
      local c75KPass = (c75KPassData != null) ? c75KPassData.K_pass : 0;
      if (projCap >= c75KPass) {
        c75StopReason = "k_pass";
        if (C78_SLOT_INTERCEPT_PROBE) {
          OpexC78SlotLog("phase=pass_stop pass=" + C78_SLOT_PASS_COUNTER
              + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
              + " reason=k_pass next_rank=" + i + " next_mode=" + project.mode
              + " finance=" + projCap + " threshold=" + c75KPass);
        }
        break;
      }
      local availCap = OpexAvailableCapital();
      if (projCap > availCap) {
        c75StopReason = "cash";
        if (C78_SLOT_INTERCEPT_PROBE) {
          OpexC78SlotLog("phase=pass_stop pass=" + C78_SLOT_PASS_COUNTER
              + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
              + " reason=cash next_rank=" + i + " next_mode=" + project.mode
              + " finance=" + projCap + " available=" + availCap);
        }
        break;
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
        if (!C75_MULTI_BUILD && builtCount >= maxBatch) break;
      }
      continue;
    }

    if (mode == "air") {
      if (C49_SCARCITY_LEDGER) c49AttemptedRanks.rawset(i, true);
      local c78DiscardStart = C78_SLOT_INTERCEPT_PROBE ? passDiscards.len() : 0;
      local c78DiscardsLen = (C69_BOTTLENECK_PROBE && passDiscards != null) ? passDiscards.len() : 0;
      if (C78_SLOT_INTERCEPT_PROBE) {
        local c78Plan = project.payload;
        local c78AirportType = (("airport" in c78Plan) && c78Plan.airport != null
            && ("type" in c78Plan.airport)) ? c78Plan.airport.type : -1;
        OpexC78SlotLog("phase=air_attempt pass=" + C78_SLOT_PASS_COUNTER
            + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
            + " rank=" + i + " townA=" + OpexC78AirSlotTown(c78Plan.siteA, c78AirportType)
            + " townB=" + OpexC78AirSlotTown(c78Plan.siteB, c78AirportType)
            + " closestA=" + OpexC78AirPhysicalTown(c78Plan.siteA)
            + " closestB=" + OpexC78AirPhysicalTown(c78Plan.siteB)
            + " src=" + project.src + " dst=" + project.dst
            + " defensive_claims=" + (("defensiveSlotClaims" in project) ? project.defensiveSlotClaims : -1)
            + " defensive_competitor_claims=" + (("defensiveCompetitorClaims" in project) ? project.defensiveCompetitorClaims : -1)
            + " defensive_own_claims=" + (("defensiveOwnClaims" in project) ? project.defensiveOwnClaims : -1)
            + " finance=" + OpexProjectFinanceCapital(project)
            + " available=" + OpexAvailableCapital() + " built_before=" + liveBuiltCount);
      }
      local attempt = this._tryBuildAirProject(year, project, i, liveBuiltCount, passDiscards,
                                                anchor, yy);
      passDiscards = attempt.discards;
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
        local c78Plan = project.payload;
        local c78AirportType = (("airport" in c78Plan) && c78Plan.airport != null
            && ("type" in c78Plan.airport)) ? c78Plan.airport.type : -1;
        OpexC78SlotLog("phase=air_outcome pass=" + C78_SLOT_PASS_COUNTER
            + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
            + " rank=" + i + " townA=" + OpexC78AirSlotTown(c78Plan.siteA, c78AirportType)
            + " townB=" + OpexC78AirSlotTown(c78Plan.siteB, c78AirportType)
            + " closestA=" + OpexC78AirPhysicalTown(c78Plan.siteA)
            + " closestB=" + OpexC78AirPhysicalTown(c78Plan.siteB)
            + " src=" + project.src + " dst=" + project.dst
            + " defensive_claims=" + (("defensiveSlotClaims" in project) ? project.defensiveSlotClaims : -1)
            + " defensive_competitor_claims=" + (("defensiveCompetitorClaims" in project) ? project.defensiveCompetitorClaims : -1)
            + " defensive_own_claims=" + (("defensiveOwnClaims" in project) ? project.defensiveOwnClaims : -1)
            + " outcome=" + attempt.outcome + " reason=" + c78Reason
            + " detail=" + c78Detail + " error=" + c78Error);
      }
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
        if (airTouchedTowns == null) airTouchedTowns = {};
        local plan = project.payload;
        local tA = ("siteA" in plan && "town" in plan.siteA && "id" in plan.siteA.town) ? plan.siteA.town.id : -1;
        local tB = ("siteB" in plan && "town" in plan.siteB && "id" in plan.siteB.town) ? plan.siteB.town.id : -1;
        if (tA >= 0) airTouchedTowns.rawset(tA, true);
        if (tB >= 0) airTouchedTowns.rawset(tB, true);
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
        if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
        if (C63_INVEST_PROBE) {
          local railSearching = this._railSearch != null && this._railSearch.phase == "search";
          this._c63RecordPassAndProbe(builtCount, c49Best, passDiscards, railSearching);
        }
        if (C69_BOTTLENECK_PROBE) {
          local built = builtCount > 0;
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

  if (C49_SCARCITY_LEDGER) this._recordC49ScarcityPass(c49Best, c49BuiltRanks, c49AttemptedRanks, passDiscards);
  if (C63_INVEST_PROBE) {
    local railSearching = this._railSearch != null && this._railSearch.phase == "search";
    this._c63RecordPassAndProbe(builtCount, c49Best, passDiscards, railSearching);
  }
  if (C69_BOTTLENECK_PROBE) {
    local built = builtCount > 0;
    local empty = (c49Best == null || c49Best.len() == 0);
    OpexC73RecordPass(built, empty, c73Cash, c73Avail);
    if (C78_SLOT_INTERCEPT_PROBE) {
      local c78ExitStop = c75StopReason;
      if (c78ExitStop == null && builtCount > 0) {
        c78ExitStop = (!C75_MULTI_BUILD) ? "single" : "list_end";
      }
      OpexC78SlotLog("phase=projects_exit pass=" + C78_SLOT_PASS_COUNTER
          + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
          + " built_count=" + builtCount
          + " stop=" + (c78ExitStop != null ? c78ExitStop : "none"));
    }
    if (C78_SLOT_INTERCEPT_PROBE && builtCount > 0) {
      OpexC78SlotLog("phase=build pass=" + C78_SLOT_PASS_COUNTER
          + " cycle=" + this._taskCycle + " tick=" + AIController.GetTick()
          + " built_count=" + builtCount);
    }
  }
  this._recordMonthlyFunnelPass(builtCount, c49Best, passDiscards, funnelAttempted);
  if (C69_TRACK_BUILDS && builtCount > 0) {
    this._recordC69BuildingPass(year, c69PassProjects != null ? c69PassProjects : this._projects, c69BuiltProjects);
  }
  if (C75_TRACK_PASSES) {
    if (builtCount > 0 && c75StopReason == null) {
      if (c80DiscardsThisPass > 0) {
        c75StopReason = "marginal_floor";
      } else {
        c75StopReason = (!C75_MULTI_BUILD) ? "single" : "list_end";
      }
    }
    OpexC75RecordPassOutcome(year, builtCount, c75KPassData, c75StopReason);
  }

  /* G4§1 : l'ancien chemin deduisait hadAbandons de passDiscards, dont le remplissage
   * est garde par DECISION_LOG (defaut 0). Le drapeau _hadAbandonsThisPass est pose
   * directement par _markPairAbandoned, couvrant tous les chemins (air, route, rail
   * bloquant et reprenable via _consumeRailSearch). */
  local hadAbandons = this._hadAbandonsThisPass;
  if (builtCount > 0 || hadAbandons) {
    local fleetPlan = null;
    if (FLEET_PORTFOLIO) {
      /* Mode a blanc : meme decision que la tache air_fleet, sans achat ni test de tresorerie. */
      fleetPlan = [];
      this._resizeAirFleets(AIDate.GetYear(AIDate.GetCurrentDate()), fleetPlan);
    }
    if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) {
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      this._rebuildProjects(fleetPlan);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = (c76Ops + 93000) / 186000;
        this._c76RecordRegen("full", c76Ops, c76Days, year, "staged");
      }
    } else if (PORTFOLIO_CACHE && this._projects != null && ("candidateGroups" in this._projects)) {
      local budgetNow = OpexAvailableCapital();
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      this._projects = OpexIncrementalUpdateProjects(this._projects, this._catalog, this._budget, this._lines, budgetNow, fleetPlan, this._abandonedPairs, airTouchedTowns);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = (c76Ops + 93000) / 186000;
        this._c76RecordRegen("incremental", c76Ops, c76Days, year, "post_build");
      }
      /* C76 : la mise a jour incrementale vient d'integrer la ligne construite ; acquitter la
       * couche `lines` evite qu'elle declenche a elle seule une regeneration complete au tour
       * suivant (mesure : 109 regenerations "layers" sur 133). Les autres couches restent dues. */
      if (C76_REGEN_TARGETED && this._c76AckRevisions != null && this._c76Revisions != null) {
        this._c76AckRevisions.lines = this._c76Revisions.lines;
      }
    } else {
      local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
      this._rebuildProjects(fleetPlan);
      if (C39_INVALIDATION_PROBE) {
        local c76Ops = OpexOpsMeasureEnd(c76Mark);
        local c76Days = (c76Ops + 93000) / 186000;
        this._c76RecordRegen("full", c76Ops, c76Days, year, "post_build");
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
             + this._projects.stats.selectedCapital + "|B" + builtCount);
    /* L'abandon a maintenant ete consomme par la reelection/reconstruction. */
    if (hadAbandons) this._hadAbandonsThisPass = false;
    return true;
  }
  return false;
}
function OpexAI::_rebuildProjects(fleetPlan, airOverride = null, advanceStage = true)
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
  this._projects = OpexBuildProjects(this._catalog, this._budget, this._lines,
      fleetPlan, this._abandonedPairs, stage, prior,
      freightCargo, freightCargos, this._activeSubsidies,
      airOverride);
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
