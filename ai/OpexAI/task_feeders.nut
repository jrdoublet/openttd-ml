/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Le coeur de l'allocation : on descend le classement tant qu'il reste de l'argent, et chaque
 * tentative recoit un budget d'iterations egal a ce qu'il faut pour continuer a battre le
 * candidat SUIVANT. Pour le dernier, l'alternative reelle n'est pas l'absence de travail : c'est
 * attendre le prochain rafraichissement annuel et son classement. MIN_RATIO est precisement le
 * plus petit rapport acceptable dans ce classement ; il remplace donc le suivant absent, sans
 * introduire de seuil propre a l'arret. */
/* Construction multimodale du portefeuille ROI. Parcourt les projets finances ordonnes par opcodeScore,
 * emet le panneau de decision IP et dispatch vers le constructeur specialise. En cas de succes, le portefeuille
 * est immediatement regenere car le capital et les origines ont change. */
function OpexFeederCandidateCompare(a, b)
{
  /* C29.4 : Priorité absolue à la première desserte de chaque ville (slot 0)
   * sur les extensions secondaires multi-arrêts (slot >= 1) */
  local slotA = ("feederSlot" in a) ? a.feederSlot : 0;
  local slotB = ("feederSlot" in b) ? b.feederSlot : 0;
  if (slotA != slotB) {
    if (slotA < slotB) return -1;
    return 1;
  }
  if (a.roi > b.roi) return -1;
  if (a.roi < b.roi) return 1;
  local aProf = a.profitAnnual + (("networkProfit" in a) ? a.networkProfit : 0);
  local bProf = b.profitAnnual + (("networkProfit" in b) ? b.networkProfit : 0);
  if (aProf > bProf) return -1;
  if (aProf < bProf) return 1;
  return 0;
}
/* Tâche dédiée de rabattage bus (feeders) vers les hubs aéroportuaires et ferroviaires (docs/taches.md C1).
 * Décloisonnée du sac à dos principal pour ne pas être écrasée par l'opcodeScore des lignes aériennes. */
function OpexAI::_tryBuildFeeders(year)
{
  if (!ROAD_BUILD_ENABLED || this._catalog.roadType < 0) return false;
  if (this._lines.len() == 0) return false;

  local candidates = [];
  local stats = {
    pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0,
    economicsUnavailable = 0, profitTooLow = 0, accepted = 0,
    feederHubs = 0, feederCandidates = 0,
    roadDistanceShort = 0, roadDistanceLong = 0,
  };
  /* C31.2 : la generation de feeders etait comptabilisee tant qu'elle vivait dans
   * OpexBuildRoadCandidates (budget "cand_road"). C29.3 l'en a sortie -- a juste titre, pour
   * supprimer la collision d'OD -- mais l'appelait NUE, alors que la fonction avait triple de
   * taille. Sur un projet ou l'opcode est une ressource, la seule fonction qui grossit ne peut pas
   * etre celle qu'on cesse de mesurer. */
  this._budget.begin();
  OpexRoadFeederCandidates(this._catalog, this._lines, candidates, stats);
  local feederGenOps = this._budget.end("cand_feeders");
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  AILog.Info("FD|" + yy + "|" + stats.feederHubs + "|" + stats.feederCandidates + "|" + candidates.len());
  OpexSign(anchor, "FD|" + yy + "|" + stats.feederHubs + "|" + stats.feederCandidates + "|" + candidates.len());
  if (DECISION_LOG) {
    OpexDecide("FEEDER_GEN", "hubs=" + stats.feederHubs + " towns_scanned=" + this._catalog.towns.len()
               + " candidates=" + stats.feederCandidates + " opcodes=" + feederGenOps);
  }
  if (candidates.len() == 0) {
    if (DECISION_LOG && stats.feederHubs > 0) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      if (_lastFeederRefuseMonth != ym) {
        _lastFeederRefuseMonth = ym;
        OpexDecide("FEEDER_REFUSE", "reason=no_candidates hubs=" + stats.feederHubs + " pairs_in_band=" + stats.pairsInBand + " no_monthly=" + stats.noMonthly + " profit_too_low=" + stats.profitTooLow);
      }
    }
    return false;
  }

  candidates.sort(OpexFeederCandidateCompare);

  /* rabattage_diag (2026-09-02) : n_feeders reste a 0 sur les 5 graines du banc alors que
   * feederCandidates > 0 chaque annee -- ce compteur dit a QUELLE garde de cette boucle les
   * candidats meurent. Ajoute pour diagnostic, pas pour changer le comportement. */
  local rejectStats = {
    served = 0, townCount = 0, abandoned = 0, cash = 0, planNull = 0, buildFail = 0,
    hubNew = 0, hubSaturated = 0,
  };

  foreach (candidate in candidates) {
    local isHubTown = ("isHubTown" in candidate) ? candidate.isHubTown : false;
    if (FEEDER_UNLOCK) {
      local maxFeeders = 1;
      if (isHubTown && FEEDER_TOWN_COVERAGE) {
        local tId = ("srcTown" in candidate && candidate.srcTown >= 0) ? candidate.srcTown : AITile.GetClosestTown(candidate.src);
        local houses = AITown.IsValidTown(tId) ? AITown.GetHouseCount(tId) : 0;
        if (houses <= 0 && AITown.IsValidTown(tId)) houses = AITown.GetPopulation(tId) / 25;
        maxFeeders = OpexCeilDiv(houses, ROAD_STOP_CATCHMENT_HOUSES);
        if (maxFeeders > 4) maxFeeders = 4;
        if (maxFeeders < 1) maxFeeders = 1;
      }
      if (OpexTownFeederCount(this._lines, candidate.src, candidate.hubStationId) >= maxFeeders) { rejectStats.served++; continue; }
    } else {
      if (OpexRoadPairServed(this._lines, candidate.src, candidate.dst)) { rejectStats.served++; continue; }
    }
    if (!isHubTown && OpexTownRoadLineCount(this._lines, candidate.src) >= 4) { rejectStats.townCount++; continue; }

    local abandonedKey = OpexAbandonedPairKey(candidate);
    if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) { rejectStats.abandoned++; continue; }

    local slot = ("feederSlot" in candidate) ? candidate.feederSlot : 0;
    local yearsElapsed = (this._startYear >= 0) ? (year - this._startYear) : 0;
    if (slot >= 1 && yearsElapsed < 2) { rejectStats.served++; continue; }

    if (FEEDER_HUB_CHECK && ("hubStationId" in candidate) && AIStation.IsValidStation(candidate.hubStationId)) {
      /* Trouver la ligne reliant ce hub, son age et sa capacite */
      local hubAgeDays = -1;
      local hubCapacity = 25;
      foreach (line in this._lines) {
        if (("stationA" in line) && ("stationB" in line)) {
          local stA = OpexLineStationId(line, "A");
          local stB = OpexLineStationId(line, "B");
          if (stA == candidate.hubStationId || stB == candidate.hubStationId) {
            if ("buildDate" in line) {
              local age = AIDate.GetCurrentDate() - line.buildDate;
              if (hubAgeDays < 0 || age < hubAgeDays) hubAgeDays = age;
            }
            if (("capacity" in line) && line.capacity > hubCapacity) {
              hubCapacity = line.capacity;
            }
          }
        }
      }

      local hubPaxRating = AIStation.GetCargoRating(candidate.hubStationId, this._catalog.paxCargo);
      local hubPaxWait = AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.paxCargo);

      /* 1. Hub immature : ligne trop jeune (< FEEDER_HUB_MIN_DAYS) ou aucune rotation achevee (rating < 0) */
      if ((hubAgeDays >= 0 && hubAgeDays < FEEDER_HUB_MIN_DAYS) || hubPaxRating < 0) {
        if (DECISION_LOG) {
          OpexDecide("FEEDER_REJECT", "reason=hub_immature hub=" + candidate.hubStationId + " age=" + hubAgeDays + " min_days=" + FEEDER_HUB_MIN_DAYS + " rating=" + hubPaxRating);
        }
        rejectStats.hubNew++;
        continue;
      }

      /* 2. Hub deja pourvu de passagers : le stock en attente depasse la capacite ou le seuil.
       * Inutile d'investir le cash de demarrage dans un feeder quand le tarmac a deja assez de clients. */
      local maxWait = (FEEDER_HUB_WAIT_MAX > 0) ? FEEDER_HUB_WAIT_MAX : (hubCapacity * 2);
      if (hubPaxWait >= maxWait) {
        if (DECISION_LOG) {
          OpexDecide("FEEDER_REJECT", "reason=hub_saturated hub=" + candidate.hubStationId + " wait=" + hubPaxWait + " max=" + maxWait);
        }
        rejectStats.hubSaturated++;
        continue;
      }
    }

    local need = candidate.capital + OpexCashReserve() + ROAD_CAPITAL_MARGIN;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (slot >= 1) {
      /* C29.4 : Un arrêt secondaire ne s'endette jamais pour se construire :
       * il exige que l'entreprise dispose du cash disponible. */
      if (money < need) { rejectStats.cash++; continue; }
    } else {
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) { rejectStats.cash++; continue; }
    }

    this._budget.begin();
    local planning = OpexRoadPlanFor(this._catalog, candidate);
    local planOps = this._budget.end("build_road_plans");
    local plan = planning.plan;
    local idx = this._nextLineId;
    if (plan == null) {
      if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
      AILog.Info("PLAN_FAIL: cand=" + candidate.src + "->" + candidate.dst + " slot=" + slot + " reason=" + planning.reason);
      OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + planning.reason + "|0");
      rejectStats.planNull++;
      continue;
    }
    local actualDist = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
    if (actualDist < 1) actualDist = 1;
    local economics = OpexRoadLineEconomics(this._catalog, candidate.cargo, actualDist,
                                            candidate.monthly, candidate.engine, candidate.kind,
                                            plan.routeDistance);
    if (economics != null) {
      local netProfit = ("networkProfit" in candidate) ? candidate.networkProfit : 0;
      local netRev = ("networkRevenue" in candidate) ? candidate.networkRevenue : 0;
      OpexApplyRoadEconomics(candidate, economics, actualDist);
      if (netProfit > 0) {
        candidate.profitAnnual += netProfit;
        candidate.revenueAnnual += netRev;
        if (candidate.capital > 0) {
          candidate.roi = (candidate.profitAnnual * 1000) / candidate.capital;
        }
      }
    }
    local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
    if (ROAD_COST_PROBE) {
      OpexSign(anchor, "RP|" + idx + "|" + result.plannedCapital + "|" + result.actualCost
                             + "|" + (result.ok ? result.vehicles.len() : 0));
    }
    if (!result.ok) {
      if (ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) this._markPairAbandoned(abandonedKey);
      OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + result.reason + "|" + result.error);
      rejectStats.buildFail++;
      continue;
    }

    this._lines.append({
      stationA = result.stopA, stationB = result.stopB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = candidate.profitAnnual,
      predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
      predAmort = candidate.amortAnnual, predCarried = candidate.carried,
      predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
      iterations = candidate.iterations, trains = candidate.trains, distance = candidate.distance,
      year = year, mode = "road",
      vehicles = result.vehicles,
      depot = result.depot,
      capacity = result.capacity,
      nStopsA = result.nStopsA,
      nStopsB = result.nStopsB,
      isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
      opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
      lineId = this._nextLineId,
      isFeeder = true,
      /* Un feeder DECHARGE dans un hub : son revenu propre n'est pas sa raison d'etre, et le
       * comparer a une liaison interurbaine n'a pas de sens. Motif explicite pour que le
       * diagnostic predit/reel le separe au lieu de le noyer dans la route pax. */
      purpose = "feeder",
      hubStationId = candidate.hubStationId,
      srcTown = candidate.srcTown,
      feederSlot = ("feederSlot" in candidate) ? candidate.feederSlot : 0,
    });
    if (DECISION_LOG) {
      local hubMode = ("hubMode" in candidate) ? candidate.hubMode : "unknown";
      local slot = ("feederSlot" in candidate) ? candidate.feederSlot : 0;
      local hubPaxWait = AIStation.IsValidStation(candidate.hubStationId) ? AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.paxCargo) : -1;
      local hubPaxRating = AIStation.IsValidStation(candidate.hubStationId) ? AIStation.GetCargoRating(candidate.hubStationId, this._catalog.paxCargo) : -1;
      local hubMailWait = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.mailCargo) : -1;
      local hubMailRating = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoRating(candidate.hubStationId, this._catalog.mailCargo) : -1;
      OpexDecide("FEEDER_BUILD", "line=" + this._nextLineId + " hub=" + candidate.hubStationId + " hub_mode=" + hubMode + " src=" + candidate.src + " dst=" + candidate.dst + " slot=" + slot + " dist=" + candidate.distance + " profit=" + candidate.profitAnnual + " cost=" + candidate.capital + " hub_pax_wait=" + hubPaxWait + " hub_pax_rating=" + hubPaxRating + " hub_mail_wait=" + hubMailWait + " hub_mail_rating=" + hubMailRating);
    }
    AILog.Info("FE|" + yy + "|" + this._nextLineId + "|" + candidate.distance + "|" + candidate.profitAnnual);
    OpexSign(anchor, "FE|" + yy + "|" + this._nextLineId + "|" + candidate.distance + "|" + candidate.profitAnnual);
    this._nextLineId++;

    /* C29.5 : Duplication automatique des bus de rabattement par des camions postaux (modele AAAHogEx #M1) */
    if (FEEDER_MAIL_DUPLICATE) {
      this._tryBuildMailFeeder(candidate, result, year);
    }

    return true;
  }
  if (DECISION_LOG) {
    local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
    if (_lastFeederRefuseMonth != ym) {
      _lastFeederRefuseMonth = ym;
      OpexDecide("FEEDER_REFUSE", "reason=all_rejected hubs=" + stats.feederHubs + " candidates=" + stats.feederCandidates + " served=" + rejectStats.served + " town_limit=" + rejectStats.townCount + " abandoned=" + rejectStats.abandoned + " cash=" + rejectStats.cash + " hub_immature=" + rejectStats.hubNew + " hub_saturated=" + rejectStats.hubSaturated + " no_plan=" + rejectStats.planNull + " build_fail=" + rejectStats.buildFail);
    }
  }
  OpexSign(anchor, "FZ|" + yy + "|" + rejectStats.served + "|" + rejectStats.townCount + "|"
                         + rejectStats.abandoned + "|" + rejectStats.cash + "|"
                         + rejectStats.planNull + "|" + rejectStats.buildFail);
  return false;
}
/* G11 : le placement d'un arret camion peut ajouter une ou deux aretes. Les supprimer a partir
 * de la liste exacte, en ordre inverse, evite de laisser une branche orpheline tout en ne touchant
 * jamais la voirie qui precedait la tentative. */
function OpexMailRollbackStop(stop)
{
  if (stop == null || !stop.isNew) return;
  if (AIRoad.IsRoadStationTile(stop.tile)) AIRoad.RemoveRoadStation(stop.tile);
  if ("added" in stop) {
    for (local i = stop.added.len() - 1; i >= 0; i--) {
      AIRoad.RemoveRoad(stop.added[i].from, stop.added[i].to);
    }
  }
}
function OpexMailRollbackStops(stopA, stopB)
{
  OpexMailRollbackStop(stopB);
  OpexMailRollbackStop(stopA);
}
function OpexAI::_tryBuildMailFeeder(candidate, paxResult, year)
{
  if (!FEEDER_MAIL_DUPLICATE) return false;
  if (this._catalog.mailCargo < 0) return false;
  if (!(this._catalog.mailCargo in this._catalog.roadEngineByCargo)) return false;
  if (paxResult == null || paxResult.stopA == null || paxResult.stopB == null || paxResult.depot == null) return false;

  local mailCargo = this._catalog.mailCargo;
  local mailEngine = this._catalog.roadEngineByCargo[mailCargo];
  local costEstimate = mailEngine.price + 2000;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < costEstimate + OpexCashReserve()) {
    if (REBORROW) money = OpexTryReborrow(costEstimate + OpexCashReserve(), money);
    if (money < costEstimate + OpexCashReserve()) return false;
  }

  local stopA = paxResult.stopA;
  local stopB = paxResult.stopB;
  local frontA = AIRoad.GetRoadStationFrontTile(stopA);
  local frontB = AIRoad.GetRoadStationFrontTile(stopB);
  local stationA = AIStation.GetStationID(stopA);
  local stationB = AIStation.GetStationID(stopB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) return false;

  // 1. Trouver ou construire l'arret camion cote ville (A)
  local mailStopA = OpexRoadFindOrBuildTruckStop(this._catalog, stopA, frontA, stationA);
  if (mailStopA == null) return false;

  // 2. Trouver ou construire l'arret camion cote hub (B)
  local mailStopB = OpexRoadFindOrBuildTruckStop(this._catalog, stopB, frontB, stationB);
  if (mailStopB == null) {
    OpexMailRollbackStops(mailStopA, null);
    return false;
  }

  // 3. Verifier la capacite refit
  local capacity = OpexRoadRefitCapacity(paxResult.depot, mailEngine, mailCargo);
  if (capacity <= 0) {
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 4. Construire le camion postal dans le depot partage
  local truck = AIVehicle.BuildVehicleWithRefit(paxResult.depot, mailEngine.id, mailCargo);
  if (!AIVehicle.IsValidVehicle(truck)) {
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 5. Ordres : ramassage ville (OF_NONE) -> dechargement transfert hub (OF_TRANSFER)
  local nonstopFlag = C53_ORDER_NONSTOP ? AIOrder.OF_NON_STOP_INTERMEDIATE : 0;
  local noloadFlag = C53_ORDER_NOLOAD ? AIOrder.OF_NO_LOAD : 0;
  local orderA = AIOrder.AppendOrder(truck, mailStopA.tile, AIOrder.OF_NONE | nonstopFlag);
  local orderB = AIOrder.AppendOrder(truck, mailStopB.tile, AIOrder.OF_TRANSFER | noloadFlag | nonstopFlag);
  if (!orderA || !orderB || AIOrder.GetOrderCount(truck) != 2) {
    AIVehicle.SellVehicle(truck);
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 6. Demarrer le camion postal
  if (!AIVehicle.StartStopVehicle(truck)) {
    AIVehicle.SellVehicle(truck);
    OpexMailRollbackStops(mailStopA, mailStopB);
    return false;
  }

  // 7. Enregistrer la ligne postale
  local yy = year % 100;
  local anchor = AIMap.GetTileIndex(1, 1);
  this._lines.append({
    stationA = mailStopA.tile, stationB = mailStopB.tile,
    originA = candidate.src, originB = candidate.dst,
    cargo = mailCargo,
    predicted = candidate.profitAnnual / 4,
    predRevenue = candidate.revenueAnnual / 4, predRunning = mailEngine.runningCost * 2,
    predAmort = 0, predCarried = candidate.carried / 4,
    predTrains = 1, predOneWayDays = candidate.oneWayDays,
    iterations = 1, trains = 1, distance = candidate.distance,
    year = year, mode = "road",
    vehicles = [truck],
    depot = paxResult.depot,
    capacity = capacity,
    nStopsA = 1, nStopsB = 1,
    isLowRatio = false,
    opcodeRatio = -1,
    lineId = this._nextLineId,
    isFeeder = true,
    purpose = "feeder_mail",
    hubStationId = candidate.hubStationId,
    srcTown = candidate.srcTown,
    feederSlot = ("feederSlot" in candidate) ? candidate.feederSlot : 0,
  });
  if (DECISION_LOG) {
    local hubMailWait = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoWaiting(candidate.hubStationId, this._catalog.mailCargo) : -1;
    local hubMailRating = (this._catalog.mailCargo >= 0 && AIStation.IsValidStation(candidate.hubStationId)) ? AIStation.GetCargoRating(candidate.hubStationId, this._catalog.mailCargo) : -1;
    OpexDecide("FEEDER_MAIL_BUILD", "line=" + this._nextLineId + " hub=" + candidate.hubStationId
               + " src=" + candidate.src + " dst=" + candidate.dst + " truck=" + truck
               + " hub_mail_wait=" + hubMailWait + " hub_mail_rating=" + hubMailRating);
  }
  AILog.Info("FM|" + yy + "|" + this._nextLineId + "|" + candidate.distance);
  OpexSign(anchor, "FM|" + yy + "|" + this._nextLineId + "|" + candidate.distance);
  this._nextLineId++;
  return true;
}
