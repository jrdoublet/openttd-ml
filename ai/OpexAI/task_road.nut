/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* C38 etape 2 : tentative synchrone route, y compris le siting vivant. */
function OpexAI::_tryBuildRoadProject(year, project, rank, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      if (!ROAD_BUILD_ENABLED || this._catalog.roadType < 0) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = project.src, dst = project.dst, reason = "road_disabled", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }
      local candidate = project.payload;
      local isSubsidy = ("isSubsidy" in candidate) && candidate.isSubsidy;
      if (isSubsidy) {
        local subId = candidate.subsidyId;
        local today = AIDate.GetCurrentDate();
        local oneWay = ("oneWayDays" in candidate) ? candidate.oneWayDays : -1;
        // Au moment de la construction immediate, la latence d'attente de cycle de batch (30j) est deja ecoulee
        local chantier = ("chantierDays" in candidate)
            ? (candidate.chantierDays - 30) : (OpexSubsidyChantierDays(oneWay) - 30);
        if (chantier < 30) chantier = 30;
        if (!AISubsidy.IsValidSubsidy(subId) || AISubsidy.IsAwarded(subId)
            || (AISubsidy.GetExpireDate(subId) - today < chantier)) {
          if (DECISION_LOG || C42_SUBSIDY_LOG) {
            OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road reason=subsidy_lost sub=" + subId);
          }
          if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
            delete this._activeSubsidies[subId];
          }
          this._purgeSubsidyFromProjects(subId);
          this._portfolioInvalidated = true;
          this._hadAbandonsThisPass = true;
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local towns = OpexGetCandidateTownEndpoints(candidate);
      if (C60_TOWN_RATING_PROBE) {
        if (towns.srcTown >= 0) OpexC60ObserveTownRating("road", "build_precheck", towns.srcTown);
        if (towns.dstTown >= 0) OpexC60ObserveTownRating("road", "build_precheck", towns.dstTown);
      }
      if (C60_TOWN_RATING_FILTER) {
        if ((towns.srcTown >= 0 && !OpexTownRatingAllowStation(towns.srcTown)) ||
            (towns.dstTown >= 0 && !OpexTownRatingAllowStation(towns.dstTown))) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_rating_refusal", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      if (candidate.kind == "pax") {
        /* Dernier verrou contre un candidat cache : des qu'une des communes a recu une ligne bus,
         * sa croissance passe exclusivement par une extension de cette ligne. */
        if ((towns.srcTown >= 0 && OpexTownBusPaxServed(this._lines, towns.srcTown)) ||
            (towns.dstTown >= 0 && OpexTownBusPaxServed(this._lines, towns.dstTown))) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
            passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst,
                                  reason = "town_already_bus_served", extra = "" });
          }
          return { outcome = "rejected", discards = passDiscards };
        }
        local alreadyServed = OpexRoadPairServed(this._lines, candidate.src, candidate.dst);
        if (alreadyServed) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "pair_already_served", extra = "" });
          local abandonedKey = OpexAbandonedPairKey(candidate);
          this._markPairAbandoned(abandonedKey);
          return { outcome = "rejected", discards = passDiscards };
        }
        if (OpexTownRoadLineCount(this._lines, candidate.src) >= 4) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (OpexTownRoadLineCount(this._lines, candidate.dst) >= 4) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "town_road_line_cap", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      } else {
        if (C55_FREIGHT_ORIGIN_RELAX && candidate.kind == "freight") {
          local srcServed = OpexOriginServed(this._lines, candidate.src, true);
          local dstServed = OpexOriginServed(this._lines, candidate.dst, true);
          if (srcServed && dstServed) {
            if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "src_origin_served", extra = "" });
            return { outcome = "rejected", discards = passDiscards };
          }
          /* Un index ne rentabiliserait pas son cout pour ce seul candidat vivant : la boucle
           * directe sur les lignes est moins chere ici et dans la revalidation incrementale. */
          if (OpexRoadFreightBusy(this._lines, candidate.cargo, candidate.src) ||
              OpexRoadFreightBusy(this._lines, candidate.cargo, candidate.dst)) {
            if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "freight_endpoint_busy", extra = "" });
            return { outcome = "rejected", discards = passDiscards };
          }
        } else {
          if (OpexOriginServed(this._lines, candidate.src, true)) {
            if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "src_origin_served", extra = "" });
            return { outcome = "rejected", discards = passDiscards };
          }
          if (OpexOriginServed(this._lines, candidate.dst, true)) {
            if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "dst_origin_served", extra = "" });
            return { outcome = "rejected", discards = passDiscards };
          }
        }
      }
      local abandonedKey = OpexAbandonedPairKey(candidate);
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && (abandonedKey in this._abandonedPairs)) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local need = candidate.capital + OpexCashReserve() + ROAD_CAPITAL_MARGIN;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("road", i, candidate.capital, candidate.profitAnnual, candidate.roi, candidate.src, candidate.dst, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|R|" + project.budgetScore + "|" + project.opcodeScore);

      this._budget.begin();
      local planning = OpexRoadPlanFor(this._catalog, candidate);
      local planOps = this._budget.end("build_road_plans");
      local plan = planning.plan;
      local idx = this._nextLineId;
      if (plan == null) {
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({
          rank = i, mode = "road", src = candidate.src, dst = candidate.dst,
          reason = "plan_failed", detail = planning.reason, extra = ""
        });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=plan_failed detail=" + planning.reason);
        }
        if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + planning.reason + "|0");
        OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|0");
        return { outcome = "rejected", discards = passDiscards };
      }
      local actualDist = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
      if (actualDist < 1) actualDist = 1;
      local economics = OpexRoadLineEconomics(this._catalog, candidate.cargo, actualDist,
                                              candidate.monthly, candidate.engine, candidate.kind,
                                              plan.routeDistance);
      if (EQUIPMENT_ROI_PROBE) {
        OpexM3ProbeRoadEquipment(this._catalog, candidate, actualDist, plan.routeDistance,
                                 economics, "post_route");
      }
      if (economics == null || economics.profitAnnual <= 0) {
        if (C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "road", src = candidate.src, dst = candidate.dst, reason = "unprofitable_after_siting", extra = "" });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=unprofitable_after_siting");
        }
        if (ABANDON_MEMORY) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|ECON|0");
        return { outcome = "rejected", discards = passDiscards };
      }
      OpexApplyRoadEconomics(candidate, economics, actualDist);
      if (isSubsidy) {
        candidate.baseRevenueAnnual = economics.revenueAnnual;
        candidate.baseProfitAnnual = economics.profitAnnual;
        candidate.baseRoi = economics.roi;
        local mult = ("effectiveMultiplier" in candidate)
            ? candidate.effectiveMultiplier
            : (("subsidyMultiplier" in candidate) ? candidate.subsidyMultiplier : 1.0);
        local subRev = (economics.revenueAnnual * mult).tointeger();
        local subProfit = subRev - economics.runningAnnual - economics.amortAnnual;
        local freightBonus = ("freightBonus" in candidate) ? candidate.freightBonus : 100;
        local subRoi = (subProfit > 0 && candidate.capital > 0) ? (subProfit * 1000) / candidate.capital : 0;
        if (freightBonus != 100) subRoi = (subRoi * freightBonus) / 100;

        candidate.subsidyRevenueAnnual = subRev;
        candidate.subsidyProfitAnnual = subProfit;
        candidate.subsidyRoi = subRoi;

        // Le candidat actif utilise l'economie subventionnee pour sa premiere annee
        candidate.revenueAnnual = subRev;
        candidate.profitAnnual = subProfit;
        candidate.roi = subRoi;
      }
      if (isSubsidy) {
        local subId = candidate.subsidyId;
        if (!AISubsidy.IsValidSubsidy(subId) || AISubsidy.IsAwarded(subId)) {
          if (DECISION_LOG || C42_SUBSIDY_LOG) {
            OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road reason=subsidy_lost_during_planning sub=" + subId);
          }
          if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
            delete this._activeSubsidies[subId];
          }
          this._purgeSubsidyFromProjects(subId);
          this._portfolioInvalidated = true;
          this._hadAbandonsThisPass = true;
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
      if (C63_INVEST_PROBE) OpexC63RecordSpendResult("road", result, candidate.capital);
      OpexSign(anchor, "RB|" + yy + "|" + idx + "|1|" + planOps + "|" + result.opcodes);
      if (ROAD_COST_PROBE) {
        OpexSign(anchor, "RP|" + idx + "|" + result.plannedCapital + "|" + result.actualCost
                               + "|" + (result.ok ? result.vehicles.len() : 0));
      }
      if (!result.ok) {
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({
          rank = i, mode = "road", src = candidate.src, dst = candidate.dst,
          reason = "build_failed", detail = result.reason, error = result.error, extra = ""
        });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=road src=" + candidate.src + " dst=" + candidate.dst + " reason=build_failed detail=" + result.reason + " error=" + result.error);
        }
        if (ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) this._markPairAbandoned(abandonedKey);
        OpexSign(anchor, "RA|" + yy + "|" + idx + "|1|" + result.reason + "|" + result.error);
        return { outcome = "rejected", discards = passDiscards };
      }

      if (DECISION_LOG) {
        foreach (d in passDiscards) {
          OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
        }
        passDiscards = [];
        local cargoStr = AICargo.GetCargoLabel(candidate.cargo);
        local extraSub = (isSubsidy && ("baseProfitAnnual" in candidate))
            ? (" base_profit=" + candidate.baseProfitAnnual + " base_roi=" + candidate.baseRoi
               + " mult=" + candidate.subsidyMultiplier
               + (("subsidyDuration" in candidate) ? (" dur=" + candidate.subsidyDuration) : "")
               + (("slackDays" in candidate) ? (" slack=" + candidate.slackDays) : ""))
            : "";
        local fleetDiag = ("vehiclesForVolume" in candidate)
            ? (" raw_vehs=" + candidate.vehiclesForVolume
               + " berth_cap=" + (("roadBerthCapacity" in candidate) ? candidate.roadBerthCapacity
                                  : OpexRoadPhysicalVehicleCap(1, 1))
               + " fleet_cap=" + (("roadVehicleCap" in candidate) ? candidate.roadVehicleCap : candidate.trains)
               + " capped_vehs=" + candidate.trains)
            : "";
        OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=road kind=" + candidate.kind + " cargo=" + cargoStr + " src=" + candidate.src + " dst=" + candidate.dst + " dist=" + candidate.distance + " cost=" + candidate.capital + " profit=" + candidate.profitAnnual + " roi=" + candidate.roi + fleetDiag + extraSub);
        OpexDecide("ROAD_BUILD", "line=" + idx + " src=" + candidate.src + " dst=" + candidate.dst + " cargo=" + cargoStr + " dist=" + candidate.distance + " profit=" + candidate.profitAnnual + " cost=" + result.cost + " vehicles=" + result.vehicles.len());
      }

      OpexSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
      OpexSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
      OpexSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
      OpexSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains);
      OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays + "|" + candidate.distance);
      OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                               + "|" + candidate.monthly);
      OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));
      OpexSign(anchor, "PM|" + idx + "|R|" + candidate.distance + "|"
                               + AICargo.GetCargoLabel(candidate.cargo));
      OpexSign(anchor, "RC|" + yy + "|" + idx + "|1|" + result.cost
                               + "|" + result.vehicles.len());
      this._lines.append({
        stationA = result.stopA, stationB = result.stopB,
        originA = candidate.src, originB = candidate.dst,
        cargo = candidate.cargo,
        predicted = candidate.profitAnnual, iterations = candidate.iterations,
        trains = result.vehicles.len(), distance = candidate.distance, year = year,
        predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
        predAmort = candidate.amortAnnual, predCarried = candidate.carried,
        predVehiclesForVolume = ("vehiclesForVolume" in candidate) ? candidate.vehiclesForVolume : candidate.trains,
        predRoadBerthCapacity = ("roadBerthCapacity" in candidate) ? candidate.roadBerthCapacity
                               : OpexRoadPhysicalVehicleCap(1, 1),
        predRoadVehicleCap = ("roadVehicleCap" in candidate) ? candidate.roadVehicleCap : candidate.trains,
        predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
        effectiveSpeed = candidate.effectiveSpeed,
        catalogSpeed = candidate.engine.speed,
        mode = "road", kind = candidate.kind, depot = result.depot,
        nStopsA = result.nStopsA, nStopsB = result.nStopsB,
        capacity = ("capacity" in result) ? result.capacity : 25,
        srcTown = ("srcTown" in candidate) ? candidate.srcTown : -1,
        dstTown = ("dstTown" in candidate) ? candidate.dstTown : -1,
        srcIndustry = (candidate.kind == "freight" && candidate.srcTown < 0)
                      ? AIIndustry.GetIndustryID(candidate.src) : -1,
        dstIndustry = (candidate.kind == "freight" && candidate.dstTown < 0)
                      ? AIIndustry.GetIndustryID(candidate.dst) : -1,
        deadStreak = 0, scrapping = false, scrapVehicles = [],
        isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
        opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
        purpose = "profit",
        isSubsidy = (("isSubsidy" in candidate) && candidate.isSubsidy),
        subsidyId = (("subsidyId" in candidate) ? candidate.subsidyId : -1),
        baseProfit = (isSubsidy && ("baseProfitAnnual" in candidate)) ? candidate.baseProfitAnnual : candidate.profitAnnual,
        baseRevenue = (isSubsidy && ("baseRevenueAnnual" in candidate)) ? candidate.baseRevenueAnnual : candidate.revenueAnnual,
        subsidyProfit = (isSubsidy && ("subsidyProfitAnnual" in candidate)) ? candidate.subsidyProfitAnnual : candidate.profitAnnual,
        subsidyRevenue = (isSubsidy && ("subsidyRevenueAnnual" in candidate)) ? candidate.subsidyRevenueAnnual : candidate.revenueAnnual,
        subsidyMultiplier = (isSubsidy && ("subsidyMultiplier" in candidate)) ? candidate.subsidyMultiplier : 1.0,
        lineId = idx,
      });
      if (("isSubsidy" in candidate) && candidate.isSubsidy) {
        if (this._activeSubsidies != null && (candidate.subsidyId in this._activeSubsidies)) {
          delete this._activeSubsidies[candidate.subsidyId];
        }
        this._purgeSubsidyFromProjects(candidate.subsidyId);
        if (C42_SUBSIDY_LOG || DECISION_LOG) {
          OpexDecide("C42_SUBSIDY_BUILD", "line=" + idx + " sub=" + candidate.subsidyId
                     + " cargo=" + AICargo.GetCargoLabel(candidate.cargo)
                     + " mult=" + (("subsidyMultiplier" in candidate) ? candidate.subsidyMultiplier : 1));
        }
      }
      this._nextLineId++;
      return { outcome = "built", discards = passDiscards };

  return { outcome = "rejected", discards = passDiscards };
}
/* Une ligne routiere a zero (ou trop peu de) vehicules avec arrets et depot encore la :
 * l'infrastructure est payee, auto-renouvellement n'a pas suivi. Mesure, plusieurs campagnes
 * graine 42 : 2 -> 1 -> 0, notes 54 -> -1, plus jamais de reconstitution. On complete jusqu'au
 * predTrains d'origine, borne par les quais de la ligne (2 x min(nStops), sinon
 * MAX_ROAD_VEHICLES). Avant _tryBuild : un camion sur une route
 * deja posee rapporte plus, a l'opcode, qu'une ligne neuve. Panneau RF|year|id|added|after
 * (succes) ou RF|year|id|0|REASON (echec). */
function OpexAI::_refleetRoadLines(year)
{
  if (!ROAD_REFLEET) return;
  local anchor = AIMap.GetTileIndex(1, 1);
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (("expandBlocked" in line) && line.expandBlocked) continue;
    if (("expandRetryCycle" in line) && line.expandRetryCycle > this._taskCycle) continue;
    if (!("depot" in line) || !AIRoad.IsRoadDepotTile(line.depot)) continue;
    if (("deadStreak" in line) && line.deadStreak > 0) continue;
    /* fleet_fix : `vehCount` n'est ecrit que par _reportLines, au plus UNE fois par an, et les
     * dicts de ligne routiere n'en portent pas a la construction. Or la file execute `projects`
     * puis `refleet` DANS LE MEME CYCLE : une ligne tout juste batie arrivait donc ici avec
     * have = 0 face a un target valant sa flotte reelle, et OpexRoadRefleet repartait -- en
     * sautant la reprise de gabarit faute de have > 0, donc en creant un vehicule avec sa PROPRE
     * liste d'ordres puis en clonant le reste. Toute ligne routiere neuve achetait ainsi une
     * seconde flotte complete (docs/taches.md S0 nonies, trouvaille 2). Le repli est desormais la
     * flotte reellement posee a la construction, pas zero. */
    local have = 0;
    if ("vehCount" in line) {
      have = line.vehCount;
    } else if ((FLEET_FIX || ROAD_FLEET_FIX) && ("trains" in line)) {
      have = line.trains;
    }
    local target = ("predTrains" in line) ? line.predTrains : (("trains" in line) ? line.trains : 1);
    if (("trains" in line) && line.trains > target) target = line.trains;
    if (target < 1) target = 1;

    // Dimensionnement dynamique intelligent basé sur les flux physiques
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    local waitingA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoWaiting(stationA, line.cargo) : 0;
    local waitingB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoWaiting(stationB, line.cargo) : 0;
    local ratingA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoRating(stationA, line.cargo) : 100;
    local ratingB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoRating(stationB, line.cargo) : 100;
    local minRating = (ratingA < ratingB) ? ratingA : ratingB;
    local totalWaiting = waitingA + waitingB;

    // Analyse des véhicules de la ligne : y en a-t-il qui attendent à l'arrêt ?
    local vehicles = OpexLineVehicleIds(line, stationA);
    local isAnyWaiting = false;
    local movingCount = 0;
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (AIVehicle.GetCurrentSpeed(v) == 0) {
        /* fleet_fix : « vitesse nulle » n'est PAS un embouteillage -- c'est l'etat NORMAL d'un
         * vehicule en cours de chargement a un arret, et les lignes de fret routier sont baties
         * avec OF_FULL_LOAD_ANY, donc un camion y passe la majeure partie de son cycle. Les trois
         * heuristiques de croissance plus bas exigeant toutes !isAnyWaiting, la situation qui
         * devrait declencher la croissance -- du cargo qui s'accumule pendant qu'un camion fait le
         * plein -- etait lue comme « deja sature, ne pas grandir ». Le signal etait donc inverse
         * par rapport a son intention (docs/taches.md S0 nonies, trouvaille 3). On ne compte
         * desormais comme bloque qu'un vehicule arrete EN LIGNE, pas a quai. */
        if ((!FLEET_FIX && !ROAD_LOADING_FIX) || AIVehicle.GetState(v) != AIVehicle.VS_AT_STATION) isAnyWaiting = true;
        else movingCount++;
      } else movingCount++;
    }

    local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
    local dedupRoad = false;
    if (!("c50_road_ym" in line) || line.c50_road_ym != ym) {
      line.c50_road_ym <- ym;
      dedupRoad = true;
    }

    if (("lastProfit" in line) && line.lastProfit < -200 && have >= 2) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null) {
        C50_NON_EXPANSION_LEDGER.road.loss_hit++;
      }
      continue;
    }
    /* marginal_fleet = 1 : le profit marginal attendu du vehicule supplementaire doit etre
     * positif -- pas de lastProfit connu et STRICTEMENT positif, pas de croissance au-dela de la
     * reconstitution du parc d'origine (missing/target calcules plus haut, jamais touches ici).
     * Sous 0 (defaut) ce garde-fou n'existe pas et les trois heuristiques ci-dessous restent
     * exactement ce qu'elles etaient. */
    if (MARGINAL_FLEET && (!("lastProfit" in line) || line.lastProfit <= 0)) continue;

    local capacity = ("capacity" in line && line.capacity > 0) ? line.capacity : 25;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local extraNeeded = 0;

    /* Chemin historique conservé littéralement sous switch 0. */
    local physicalCap = OpexRoadPhysicalVehicleCap(
        ("nStopsA" in line) ? line.nStopsA : 1, ("nStopsB" in line) ? line.nStopsB : 1);
    if (ROAD_TIME_SCALED_CAP &&
        ("kind" in line) && line.kind == "pax") {
      local nStopsA = ("nStopsA" in line) ? line.nStopsA : 1;
      local nStopsB = ("nStopsB" in line) ? line.nStopsB : 1;
      local oneWayDays = ("predOneWayDays" in line) ? line.predOneWayDays : 0;
      physicalCap = OpexRoadFleetVehicleCap(nStopsA, nStopsB, oneWayDays, line.kind);
    }
    if (have >= physicalCap) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null) {
        C50_NON_EXPANSION_LEDGER.road.physical_cap_hit++;
      }
    } else if (isAnyWaiting) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null) {
        C50_NON_EXPANSION_LEDGER.road.congestion_hit++;
      }
    }

    // 1. S'il y a du stock en attente et que les véhicules circulent bien
    if (totalWaiting >= capacity && !isAnyWaiting) {
      extraNeeded = totalWaiting / capacity;
      if (extraNeeded > 3) extraNeeded = 3;
    }
    // 2. Si la note de station s'effondre faute de fréquence (distance longue)
    else if (minRating < 65 && have < physicalCap && !isAnyWaiting && money > 35000) {
      extraNeeded = 1;
    }
    // 3. Si la ligne est très rentable (> 1000 £) et qu'on a du cash
    else if (("lastProfit" in line) && line.lastProfit > 1000 && have < physicalCap && money > 60000 && !isAnyWaiting) {
      extraNeeded = 1;
    }

    /* B3 : `physicalCap` garde son ancien nom pour préserver le chemin 0 ; sous le switch pax,
     * sa valeur devient le plafond temporel de flotte. La capacité de quai reste reportée à part. */
    if (have + extraNeeded > physicalCap) extraNeeded = physicalCap - have;
    if (extraNeeded < 0) extraNeeded = 0;

    if (have + extraNeeded > target) target = have + extraNeeded;
    if (target > physicalCap) target = physicalCap;
    if (have >= target) {
      if (C50_CHRONOLOGY_PROBE && dedupRoad && C50_NON_EXPANSION_LEDGER != null && have < physicalCap && !isAnyWaiting) {
        C50_NON_EXPANSION_LEDGER.road.no_demand++;
      }
      if (("needsRefleet" in line) && line.needsRefleet) line.needsRefleet = false;
      continue;
    }
    local refill = OpexRoadRefleet(this._catalog, line, have, target);
    if (refill.added > 0) {
      line.vehCount <- refill.after;
      if (("trains" in line) && line.trains < refill.after) line.trains = refill.after;
      if (refill.after >= target && ("needsRefleet" in line)) line.needsRefleet = false;
      if (C50_CHRONOLOGY_PROBE) {
        if (C50_NON_EXPANSION_LEDGER != null) C50_NON_EXPANSION_LEDGER.road.refill_built += refill.added;
        OpexC50ChronologyLog("phase=fleet_built mode=road line=" + line.lineId + " added=" + refill.added + " total=" + refill.after + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      }
    } else if (C50_CHRONOLOGY_PROBE) {
      if (C50_NON_EXPANSION_LEDGER != null) {
        if (refill.reason == "CASH") C50_NON_EXPANSION_LEDGER.road.cash_refused++;
        else C50_NON_EXPANSION_LEDGER.road.other_refused++;
      }
      if (refill.reason == "CASH") {
        this._logC50CashRefusal("road_refleet", line.lineId, 0, 0, 0, line.stationA, line.stationB, 0, AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      }
    }
    if (DECISION_LOG) {
      if (refill.added > 0) {
        OpexDecide("ROAD_REFLEET", "action=refill line=" + line.lineId + " added=" + refill.added + " total=" + refill.after);
      } else {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (!("lastRefleetRefuseMonth" in line) || line.lastRefleetRefuseMonth != ym) {
          line.lastRefleetRefuseMonth <- ym;
          OpexDecide("ROAD_REFLEET", "action=refuse line=" + line.lineId + " reason=" + refill.reason + " have=" + have + " target=" + target);
        }
      }
    }
    OpexSign(anchor, "RF|" + year + "|" + line.lineId + "|" + refill.added + "|"
                     + (refill.added > 0 ? refill.after : refill.reason));
  }
}
