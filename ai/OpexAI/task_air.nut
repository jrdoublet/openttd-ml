/* Revalidation air : un plan garde ses sites depuis la generation, mais le monde peut changer
 * avant son classement puis son chantier. Rejouer les preconditions utiles de
 * OpexAirFindSite sans relancer le balayage des villes. */
function OpexAirBatchSiteStillBuildable(site, airport, plane, reuse)
{
  return OpexAirSiteStillBuildable(site, airport, plane, reuse);
}
/* Un hub garde une limite de routes liee a son aeroport. La generation l'avait controlee sur
 * l'ancien this._lines ; apres un succes de batch, seul ce comptage vivant peut dire si le plan
 * reste admissible. Pas de controle de taille de flotte ici : plan.planes ne depend d'aucun etat
 * modifie par le chantier precedent et le relire serait du cout d'opcodes sans information. */
function OpexAirBatchHubHasCapacity(anchor, plane, lines)
{
  if (!AIAirport.IsAirportTile(anchor) ||
      !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(anchor), plane.planeType)) return false;
  local station = AIStation.GetStationID(anchor);
  if (!AIStation.IsValidStation(station)) return false;
  local routes = 0;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    /* this._lines garde les tuiles d'aeroport, pas les StationID. Comparer les tuiles au
     * StationID du hub laisserait passer le plafond apres le premier succes du batch. */
    if (AIStation.GetStationID(line.stationA) == station ||
        AIStation.GetStationID(line.stationB) == station) routes++;
  }
  local airportType = AIAirport.GetAirportType(anchor);
  local maxRoutes = OpexAirAirportMaxRoutes(airportType);
  return routes < maxRoutes;
}
/* La paire O/D et les bouts nouveaux etaient valides lors de la generation. Avant toute tentative,
 * revalider l'etat vivant : une autre construction ou le monde peut avoir rendu le plan caduc. */
function OpexAirBatchPlanStillLive(plan, lines)
{
  if (OpexAirRecoveryBlocksPlan(plan)) return false;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  local c83OwnSecondA = ("c83OwnSecondSlotA" in plan) && plan.c83OwnSecondSlotA;
  local c83OwnSecondB = ("c83OwnSecondSlotB" in plan) && plan.c83OwnSecondSlotB;
  if (!reuseA) {
    local servedA = OpexAirTownServed(plan.siteA.town, lines);
    if (c83OwnSecondA) {
      if (!servedA || !OpexAirC83SecondSlotOpen(plan.siteA.town)) return false;
    } else if (servedA) {
      return false;
    }
  }
  if (!reuseB) {
    local servedB = OpexAirTownServed(plan.siteB.town, lines);
    if (c83OwnSecondB) {
      if (!servedB || !OpexAirC83SecondSlotOpen(plan.siteB.town)) return false;
    } else if (servedB) {
      return false;
    }
  }
  if (reuseA && !OpexAirBatchHubHasCapacity(plan.siteA.anchor, plan.plane, lines)) return false;
  if (reuseB && !OpexAirBatchHubHasCapacity(plan.siteB.anchor, plan.plane, lines)) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if ((line.originA == plan.siteA.town.tile && line.originB == plan.siteB.town.tile) ||
        (line.originA == plan.siteB.town.tile && line.originB == plan.siteA.town.tile)) return false;
  }
  return true;
}

/* V156 : version indexee et memoisee de OpexAirTownServed par town.tile. */
function OpexAirTownServedIndexed(town, lines, ctx)
{
  if (town == null || !("tile" in town)) return false;
  if (town.tile in ctx.airTownServed) return ctx.airTownServed[town.tile];
  local served = false;
  if (lines != null) {
    foreach (orig in ctx.airOrigins) {
      if (AIMap.DistanceManhattan(town.tile, orig) < 15) {
        served = true;
        break;
      }
    }
  }
  ctx.airTownServed.rawset(town.tile, served);
  return served;
}

/* V156 : version indexee de OpexAirBatchHubHasCapacity via airHubRouteCounts precalcule. */
function OpexAirBatchHubHasCapacityIndexed(anchor, plane, ctx)
{
  if (!AIAirport.IsAirportTile(anchor) ||
      !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(anchor), plane.planeType)) return false;
  local station = AIStation.GetStationID(anchor);
  if (!AIStation.IsValidStation(station)) return false;
  local routes = (station in ctx.airHubRouteCounts) ? ctx.airHubRouteCounts[station] : 0;
  local airportType = AIAirport.GetAirportType(anchor);
  local maxRoutes = OpexAirAirportMaxRoutes(airportType);
  return routes < maxRoutes;
}

/* V156 : version memoisee de la constructibilite de site air par cle (reuse|airport.type|plane.planeType|anchor). */
function OpexAirSiteStillBuildableIndexed(site, airport, plane, reuse, ctx)
{
  if (site == null || airport == null || plane == null || !("anchor" in site)) return false;
  local key = (reuse ? "R|" : "N|") + airport.type + "|" + plane.planeType + "|" + site.anchor;
  /* Cache limite a l'appel et sondage vivant sans villes plafonnees : meme predicat que
   * OpexAirBatchSiteStillBuildable. Le cache mensuel AIR0310 gardait valides des sites devenus
   * inconstructibles dans le mois (66 ecarts hist=0 idx=1 au controle v157_check_3x4). */
  if (key in ctx.airSiteValidity) return ctx.airSiteValidity[key];
  local ok = OpexAirSiteStillBuildable(site, airport, plane, reuse);
  ctx.airSiteValidity.rawset(key, ok);
  return ok;
}

/* V156 : version indexee de OpexAirBatchPlanStillLive utilisant les index de ctx. */
function OpexAirBatchPlanStillLiveIndexed(plan, lines, ctx)
{
  if (OpexAirRecoveryBlocksPlan(plan)) return false;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  local c83OwnSecondA = ("c83OwnSecondSlotA" in plan) && plan.c83OwnSecondSlotA;
  local c83OwnSecondB = ("c83OwnSecondSlotB" in plan) && plan.c83OwnSecondSlotB;
  if (!reuseA) {
    local servedA = OpexAirTownServedIndexed(plan.siteA.town, lines, ctx);
    if (c83OwnSecondA) {
      if (!servedA || !OpexAirC83SecondSlotOpen(plan.siteA.town)) return false;
    } else if (servedA) {
      return false;
    }
  }
  if (!reuseB) {
    local servedB = OpexAirTownServedIndexed(plan.siteB.town, lines, ctx);
    if (c83OwnSecondB) {
      if (!servedB || !OpexAirC83SecondSlotOpen(plan.siteB.town)) return false;
    } else if (servedB) {
      return false;
    }
  }
  if (reuseA && !OpexAirBatchHubHasCapacityIndexed(plan.siteA.anchor, plan.plane, ctx)) return false;
  if (reuseB && !OpexAirBatchHubHasCapacityIndexed(plan.siteB.anchor, plan.plane, ctx)) return false;
  local pairKey = plan.siteA.town.tile + "|" + plan.siteB.town.tile;
  if (pairKey in ctx.airLinePairs) return false;
  return true;
}
/* C38 etape 2 : tentative synchrone air, incluant les gardes de site et de flotte. */
function OpexAI::_tryBuildAirProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      local plan = project.payload;
      if (!OpexAirBatchPlanStillLive(plan, this._lines)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
              || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "batch_plan_dead", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
      }
      if (!OpexAirBatchSiteStillBuildable(plan.siteA, plan.airport, plan.plane,
                                             ("reuseA" in plan) && plan.reuseA)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
              || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteA_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      if (!OpexAirBatchSiteStillBuildable(plan.siteB, plan.airport, plan.plane,
                                             ("reuseB" in plan) && plan.reuseB)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
              || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteB_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      local townAId = ("siteA" in plan && "town" in plan.siteA && "id" in plan.siteA.town) ? plan.siteA.town.id : -1;
      local townBId = ("siteB" in plan && "town" in plan.siteB && "id" in plan.siteB.town) ? plan.siteB.town.id : -1;
      if (C60_TOWN_RATING_PROBE) {
        if (townAId >= 0) OpexC60ObserveTownRating("air", "build_precheck", townAId);
        if (townBId >= 0) OpexC60ObserveTownRating("air", "build_precheck", townBId);
      }
      local maxPerYear = 30;
      local maxTotal = 250;
      local airLinesThisYear = 0;
      local totalAirLines = 0;
      foreach (line in this._lines) {
        if (("mode" in line) && line.mode == "air") {
          totalAirLines++;
          if (line.year == year) airLinesThisYear++;
        }
      }
      if (airLinesThisYear >= maxPerYear || totalAirLines >= maxTotal) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
            || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "line_cap_reached", extra = "lines_year=" + airLinesThisYear + " total=" + totalAirLines });
        return { outcome = "rejected", discards = passDiscards };
      }
      local abandonedKey = OpexAirPairKey(plan.siteA, plan.siteB);
      if (OpexAirPairIsAbandoned(this._abandonedPairs, plan.siteA, plan.siteB)) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
            || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local spChoose = PROBE_SPAN_TRACE ? OpexSpanBegin("build.air.choose_plan") : null;
      local buildPlan = plan;
      if (spChoose != null) OpexSpanEnd(spChoose);

      local spCash = PROBE_SPAN_TRACE ? OpexSpanBegin("build.air.cash") : null;
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
      if (EQUIPMENT_ROI_PROBE) OpexM3ProbeAirEquipment(this._catalog, plan, "portfolio_selected");
      local requiredMargin = OpexAirRequiredMargin(newAirports, buildPlan);
      local capital = ("capital" in buildPlan) ? buildPlan.capital
          : (newAirports * buildPlan.airport.price + buildPlan.plane.price);
      local need = capital + OpexCashReserve() + requiredMargin;
      if (spCash != null) OpexSpanEnd(spCash);
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("air", i, capital, plan.economics.profitAnnual, project.roi, plan.siteA.town.tile, plan.siteB.town.tile, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE
            || C122_AIR_THREAT_PROBE) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|A|" + project.budgetScore + "|" + project.opcodeScore);
      if (("earlySlotBonusPct" in project) && project.earlySlotBonusPct > 0) {
        local earlyTownA = ("earlySlotTownA" in project) ? project.earlySlotTownA : townAId;
        local earlyTownB = ("earlySlotTownB" in project) ? project.earlySlotTownB : townBId;
        OpexSign(anchor, "SK|" + yy + "|" + earlyTownA + "|" + earlyTownB + "|"
                         + project.earlySlotBonusPct);
        if (DECISION_LOG) {
          local earlyScoreKey = "fundScore";
          local earlyBaseScore = project[earlyScoreKey];
          local earlyBoostedScore = OpexProjectSelectionScore(project, earlyScoreKey);
          local popA = ("earlySlotPopA" in project) ? project.earlySlotPopA : -1;
          local popB = ("earlySlotPopB" in project) ? project.earlySlotPopB : -1;
          OpexDecide("EARLY_SLOT_SELECT", "town_a=" + earlyTownA + " pop_a=" + popA
                     + " town_b=" + earlyTownB + " pop_b=" + popB
                     + " claims=" + project.earlySlotClaims
                     + " bonus_claims=" + project.earlySlotBonusClaims
                     + " secured_before=" + project.earlySlotServedBefore
                     + " target=" + AIR_EARLY_SLOT_TARGET_TOWNS
                     + " bonus_pct=" + project.earlySlotBonusPct
                     + " base_score=" + earlyBaseScore
                     + " boosted_score=" + earlyBoostedScore);
        }
      }

      local planOps = ("planningOpcodes" in project) ? project.planningOpcodes : 0;
      OpexC121PrepareDemandShadow(this._catalog, buildPlan, this._lines);
      local quotePlanes = ("planes" in buildPlan) ? buildPlan.planes : 1;
      local result = OpexBuildAirRoute(this._catalog, this._budget, buildPlan);
      if (PROBE_SPAN_TRACE) {
        local evtTowns = plan.siteA.town.id + "," + plan.siteB.town.id;
        local evtPlanes = result.ok ? result.vehicles.len() : 0;
        local evtCap = ("capital" in buildPlan) ? buildPlan.capital : 0;
        if (result.ok) OpexSpanEvent("line_built", "mode=air towns=" + evtTowns + " capital=" + evtCap + " planes=" + evtPlanes);
        else OpexSpanEvent("build_fail", "mode=air towns=" + evtTowns + " capital=" + evtCap + " planes=" + evtPlanes + " reason=" + result.reason);
      }
      if (C63_INVEST_PROBE) OpexC63RecordSpendResult("air", result, buildPlan.capital);
      OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
      if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
      if (AIR_COST_PROBE) {
        OpexSign(anchor, "AC|" + this._nextLineId + "|" + result.plannedCapital + "|"
                               + result.actualCost + "|"
                               + (("planes" in buildPlan) ? buildPlan.planes : 1) + "|"
                               + (result.ok ? result.vehicles.len() : 0));
      }
      if (!result.ok) {
        local errorAnchor = null;
        if ((result.reason == "PREA" || result.reason == "AFAIL") && plan.siteA != null) {
          errorAnchor = plan.siteA.anchor;
        } else if ((result.reason == "PREB" || result.reason == "BFAIL") && plan.siteB != null) {
          errorAnchor = plan.siteB.anchor;
        }
        local errorTown = (errorAnchor != null && AIMap.IsValidTile(errorAnchor))
            ? AITile.GetClosestTown(errorAnchor) : -1;
        local errorOwnAirports = -1;
        if (result.error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN && errorTown >= 0
            && (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE)) {
          local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
          ownAirports.Valuate(AIStation.GetNearestTown);
          ownAirports.KeepValue(errorTown);
          errorOwnAirports = ownAirports.Count();
        }
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL || C78_SLOT_INTERCEPT_PROBE || C122_AIR_THREAT_PROBE) passDiscards.append({
          rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile,
          reason = "build_failed", detail = result.reason, error = result.error,
          error_anchor = errorAnchor, error_town = errorTown,
          error_own_airports = errorOwnAirports, extra = ""
        });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=air src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " reason=build_failed detail=" + result.reason + " error=" + result.error + " error_text=" + result.errorText);
        }
        if (OpexBuildFailureIsAbandonable(result)) {
          this._markPairAbandoned(abandonedKey);
        }
        local ret = { outcome = "rejected", discards = passDiscards };
        if (C69_BOTTLENECK_PROBE) ret.reason <- result.reason;
        return ret;
      }
      if (result.ok) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(this._catalog.paxCargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=air cargo=" + cargoStr + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " dist=" + plan.distance + " cost=" + plan.capital + " profit=" + plan.economics.profitAnnual + " roi=" + project.roi);
          OpexDecide("AIR_BUILD", "arm=" + plan.arm + " line=" + this._nextLineId + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id + " dist=" + plan.distance + " profit=" + buildPlan.economics.profitAnnual + " cost=" + buildPlan.capital + " planes=" + result.vehicles.len() + " engine=" + buildPlan.plane.id);
        }
        if (C56_TASK_TRACE) OpexC56TaskLog("AIR_BUILT", ("arm" in plan) ? plan.arm : "unknown", "-",
            "line=" + this._nextLineId + " profit=" + buildPlan.economics.profitAnnual + " cost=" + buildPlan.capital
            + " stA=" + AIStation.GetStationID(result.stationA) + " stB=" + AIStation.GetStationID(result.stationB));
        this._airBuilt = true;
        OpexAir0310InvalidateSiteValidity();
        this._lines.append({
          stationA = result.stationA, stationB = result.stationB,
          originA = plan.siteA.town.tile, originB = plan.siteB.town.tile,
          cargo = this._catalog.paxCargo,
          predicted = ("economics" in buildPlan && "profitAnnual" in buildPlan.economics) ? buildPlan.economics.profitAnnual : 0,
          predRevenue = buildPlan.economics.revenueAnnual, predRunning = buildPlan.economics.runningAnnual,
          predVehicleRunning = buildPlan.planes * buildPlan.plane.runningCost,
          predAmort = buildPlan.economics.amortAnnual, predCarried = buildPlan.economics.carried,
          predTrains = buildPlan.planes, predOneWayDays = buildPlan.economics.oneWayDays,
          planeCapacity = buildPlan.plane.capacity,
          planeId = buildPlan.plane.id,
          sharedAirportA = ("reuseA" in plan) && plan.reuseA,
          hubRoutesAtBuild = ("hubRoutes" in plan) ? plan.hubRoutes : 0,
          joinedStopsA = result.joinedStopsA, joinedStopsB = result.joinedStopsB,
          joinedMonthlyPax = result.joinedMonthlyPax, joinedStopCost = result.joinedStopCost,
          actualCapital = buildPlan.capital,
          iterations = 0, trains = result.vehicles.len(), trains0 = result.vehicles.len(), distance = plan.distance, year = year,
          buildDate = AIDate.GetCurrentDate(),
          mode = "air", vehicle = result.vehicle, vehicles = result.vehicles,
          refleetEngine = AIVehicle.GetEngineType(result.vehicle),
          vehCount = result.vehicles.len(),
          deadStreak = 0, scrapping = false, scrapVehicles = [],
          lastLiveVehicles = result.vehicles.len(), suspectedCrashes = 0,
          isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
          lineId = this._nextLineId,
        });
        if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;
        OpexC121AttachLineShadow(this._lines[this._lines.len() - 1], this._nextLineId, buildPlan, result);
        local builtLine = this._lines[this._lines.len() - 1];
        builtLine.targetAirPlanes <- ("c121TargetPlanes" in builtLine)
            ? builtLine.c121TargetPlanes
            : (("targetPlanes" in buildPlan) ? buildPlan.targetPlanes : result.vehicles.len());
        this._lines[this._lines.len() - 1].airMonthlyPax <- ("monthlyPax" in buildPlan) ? buildPlan.monthlyPax : 0;
        OpexSign(anchor, "AF|" + this._nextLineId + "|" + result.vehicles.len() + "|"
                               + buildPlan.economics.profitAnnual);
        OpexSign(anchor, "AH|" + this._nextLineId + "|"
                         + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0) + "|"
                         + buildPlan.capital + "|" + (("hubRoutes" in plan) ? plan.hubRoutes : 0));
        OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                         + AICargo.GetCargoLabel(this._catalog.paxCargo));
        if (("earlySlotBonusPct" in project) && project.earlySlotBonusPct > 0) {
          local earlyTownA = ("earlySlotTownA" in project) ? project.earlySlotTownA : townAId;
          local earlyTownB = ("earlySlotTownB" in project) ? project.earlySlotTownB : townBId;
          OpexSign(anchor, "SB|" + yy + "|" + earlyTownA + "|" + earlyTownB + "|"
                           + project.earlySlotClaims);
          if (DECISION_LOG) {
            OpexDecide("EARLY_SLOT_BUILD", "line=" + this._nextLineId
                       + " town_a=" + earlyTownA + " town_b=" + earlyTownB
                       + " claims=" + project.earlySlotClaims
                       + " bonus_claims=" + project.earlySlotBonusClaims
                       + " secured_before=" + project.earlySlotServedBefore
                       + " secured_after=" + (project.earlySlotServedBefore + project.earlySlotClaims)
                       + " target=" + AIR_EARLY_SLOT_TARGET_TOWNS
                       + " bonus_pct=" + project.earlySlotBonusPct);
          }
        }
        this._nextLineId++;
        this._c76BumpLayer("lines", false);
        return { outcome = "built", discards = passDiscards };
      }

  return { outcome = "rejected", discards = passDiscards };
}
/* Dimensionnement progressif de l'air. Une prediction de population ne peut plus acheter une
 * flotte entiere au demarrage. Apres au moins une annee, on ajoute au plus UN avion par ligne et
 * par an si (1) les appareils existants gagnent de l'argent et (2) au moins une charge utile
 * complete attend dans les deux aeroports. Un echec de cash est reporte a l'annee suivante : la
 * file ne le resonde pas a chaque cycle et ne gaspille donc pas d'opcodes. */
/* Cause du refus de croissance d'une flotte aerienne, une seule fois par ligne et par an.
 * Codes : Y deja grandie cette annee, V aucun avion vivant, D ligne morte, L profit negatif,
 * C plafond physique de l'aeroport atteint, S un an de mauvaise sante,
 * K ligne en cours de rebut, M tresorerie, X l'achat a echoue. */
function OpexAirFleetRefusal(line, year, code)
{
  if (C50_CHRONOLOGY_PROBE) {
    if (code == "M") {
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local stA = ("stationA" in line) ? line.stationA : 0;
      local stB = ("stationB" in line) ? line.stationB : 0;
      OpexC50LogCashRefusal("air_fleet", line.lineId, 30000, 0, 0, stA, stB, 30000, money);
    }
    if (C50_NON_EXPANSION_LEDGER != null && ("air" in C50_NON_EXPANSION_LEDGER)) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      local dedupKey = "c50_ref_" + code;
      if (!(dedupKey in line) || line[dedupKey] != ym) {
        line[dedupKey] <- ym;
        local k = "ref_" + code;
        if (k in C50_NON_EXPANSION_LEDGER.air) C50_NON_EXPANSION_LEDGER.air[k]++;
        else C50_NON_EXPANSION_LEDGER.air[k] <- 1;
      }
    }
  }
  if (!AIR_FLEET_PROBE && !DECISION_LOG) return;
  if (!("lineId" in line)) return;
  /* rabattage_diag (2026-09-02) : dedup resserre au MOIS, pas a l'annee -- le dedup annuel
   * masquait un blocage de plusieurs mois derriere un seul motif fige au premier refus de
   * l'annee, alors que la tresorerie disponible changeait entre-temps. Diagnostic uniquement. */
  local month = AIDate.GetMonth(AIDate.GetCurrentDate());
  local ym = year * 12 + month;
  if (("lastFleetProbeMonth" in line) && line.lastFleetProbeMonth == ym) return;
  line.lastFleetProbeMonth <- ym;
  if (AIR_FLEET_PROBE) {
    OpexSign(AIMap.GetTileIndex(2, 10 + line.lineId),
             "FR|" + (year % 100) + (month < 10 ? "0" + month : "" + month) + "|" + line.lineId + "|" + code);
  }
  if (DECISION_LOG) {
    local yieldVal = OpexAirFleetYield(line);
    local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
    local reasonStr = code;
    if (code == "Y") reasonStr = "already_grown_this_year";
    else if (code == "V") reasonStr = "no_live_aircraft";
    else if (code == "D") reasonStr = "dead_line";
    else if (code == "L") reasonStr = "negative_profit";
    else if (code == "C") reasonStr = "airport_capacity_reached";
    else if (code == "S") reasonStr = "poor_health_streak";
    else if (code == "K") reasonStr = "scrapping";
    else if (code == "M") reasonStr = "insufficient_cash";
    else if (code == "X") reasonStr = "purchase_failed";
    OpexDecide("AIR_FLEET", "action=refuse line=" + line.lineId + " reason=" + reasonStr + " planes=" + have + " yield=" + yieldVal);
  }
}
/* Rendement marginal d'une ligne aerienne : profit PAR APPAREIL deja en service. C'est le
 * predicteur du remboursement de l'appareil SUIVANT -- une ligne qui gagne 100 k£ avec 2 avions
 * rembourse deux fois plus vite que celle qui gagne 100 k£ avec 8. `lastProfit` (mesure ecrite
 * par _reportLines) prime sur `predicted` (modele) des qu'il existe ; une ligne neuve jamais
 * rapportee tombe donc sur sa prevision plutot que sur zero, sinon elle serait servie en dernier
 * pendant toute sa premiere annee. */
function OpexAirFleetYield(line)
{
  local fleet = ("vehCount" in line) ? line.vehCount
              : (("vehicles" in line) ? line.vehicles.len() : 1);
  if (fleet < 1) fleet = 1;
  local profit = ("lastProfit" in line) ? line.lastProfit
               : (("predicted" in line) ? line.predicted : 0);
  return profit / fleet;
}
/* C34.2 : `plan` non nul = MODE A BLANC. La fonction traverse exactement les memes treize gardes
 * de refus, mais au lieu d'acheter elle enregistre ce qu'elle achererait dans `plan`, sous la forme
 * { line, want, planePrice }. C'est volontairement une reutilisation et non une extraction : les
 * gardes sont trop nombreuses et trop calibrees pour etre dupliquees sans divergence silencieuse.
 * Le portefeuille appelle ainsi la meme decision que la tache, puis l'arbitre contre les lignes
 * neuves au lieu de la servir d'office avant elles. */
function OpexAI::_resizeAirFleets(year, plan = null)
{
  local spFleet = PROBE_SPAN_TRACE ? OpexSpanBegin("fleet.resize") : null;
  local anchor = AIMap.GetTileIndex(1, 1);
  /* air_roi_order : servir la ligne qui rembourse le plus vite, pas la plus ancienne. Le tri
   * porte sur une COPIE de references : _lines garde son ordre, dont depend l'indexation de
   * _scrapDeadLines (retrait par position). */
  local airLines = [];
  foreach (line in this._lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    /* Opcode optimisation: a line still inside the growth cooldown cannot
     * contribute a fleet project and used to pay the ROI sort cost anyway.
     * Keep the pre-cadence priority paths in the list: scrapping must
     * reject before refleet, and a crash refleet bypasses the growth cadence. */
    local priorityPath = (("scrapping" in line) && line.scrapping)
        || (("needsRefleet" in line) && line.needsRefleet);
    if (!priorityPath) {
      local lastDate = ("lastAirFleetDate" in line) ? line.lastAirFleetDate
          : (("buildDate" in line) ? line.buildDate : 0);
      local cooldown = lastDate > 0
          && (AIDate.GetCurrentDate() - lastDate) < AIR_FLEET_CADENCE_DAYS;
      if (cooldown) {
        local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        OpexAirFleetRefusal(line, year, "Y");
        if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
        if (plan != null && C69_BOTTLENECK_PROBE)
          OpexC73RecordRejection("fleet", "already_grown_this_year", 1);
        continue;
      }
    }
    airLines.append(line);
  }
  {
    local spSort = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    airLines = OpexAirFleetSortSelect(airLines);
    if (spSort != null) OpexSpanAgg("fleet.sort", spSort);
  }

  local routesIndex = null;

  foreach (line in airLines) {
    if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordExamined("fleet", 1);
    /* B8 / G10 : une ligne en liquidation ne peut recevoir aucun appareil neuf, y compris une
     * reconstitution de crash. Ce garde doit preceder needsRefleet : pendant la fenetre de vente,
     * les avions encore vivants peuvent redevenir profitables et remettre deadStreak a zero. */
    if (("scrapping" in line) && line.scrapping) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "K");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "scrapping", 1);
      continue;
    }
    /* Reconstitution de crash : elle passe avant les gardes de croissance
     * (have=0, profit ancien negatif, cadence), sinon le dernier avion ne peut
     * jamais redevenir un template. OpexAirRefleetCrashedPlane reconstruit les
     * ordres depuis les metadonnees durables de la ligne. */
    if (("needsRefleet" in line) && line.needsRefleet) {
      local recovered = OpexAirRefleetCrashedPlane(line, this._catalog);
      routesIndex = null;
      if (recovered.added > 0) {
        local afterCrash = (("vehCount" in line) ? line.vehCount : 0) + recovered.added;
        if ("vehCount" in line) line.vehCount = afterCrash;
        else line.vehCount <- afterCrash;
        if ("trains" in line) line.trains = afterCrash;
        else line.trains <- afterCrash;
        line.needsRefleet = false;
        if (DECISION_LOG || C52_CRASH_LOG) {
          OpexDecide("CRASH_REFLEET", "mode=air line=" + line.lineId + " vehicle=" + line.vehicle);
        }
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "crash_refleeted", 1);
      } else {
        local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        OpexAirFleetRefusal(line, year, "R");
        if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "refleet_failed", 1);
      }
      continue;
    }
    /* C15 : Cadence d'extension de flotte aerienne. Verrou glissant en jours depuis la derniere extension (ou la creation de la ligne). */
    local lastDate = ("lastAirFleetDate" in line) ? line.lastAirFleetDate : (("buildDate" in line) ? line.buildDate : 0);
    if (lastDate > 0 && (AIDate.GetCurrentDate() - lastDate) < AIR_FLEET_CADENCE_DAYS) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "Y");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "already_grown_this_year", 1);
      continue;
    }
    local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
    if (have < 1) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "V");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "no_live_aircraft", 1);
      continue;
    }
    local c121BelowTarget = ("targetAirPlanes" in line)
        && line.targetAirPlanes > have;
    local c121FirstLiveEntry = false;
    if (c121BelowTarget && (C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS <= 0
            || year - OPEX_START_YEAR < C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS) && have == 1 && !("lastAirFleetYear" in line)) {
      /* C121 cadence live : seul 1->2 est avance, sur preuve d'exploitation
       * recente deja agregee passivement par C117. Le projet reste un +1 normal
       * et passe ensuite par exactement le meme portefeuille/financement.
       * IMPORTANT : le signal live est uniquement un raccourci. S'il n'est pas
       * pret, la garde C121 historique reprend la main a deux ans ; cette
       * experience ne doit jamais retarder un 1->2 que le baseline accepterait. */
      local spFirstLive = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      local firstLiveOk = OpexC121FirstLiveBalanced90(line);
      if (spFirstLive != null) OpexSpanAgg("fleet.first_live", spFirstLive);
      if (!firstLiveOk) {
        local c121Age = ("year" in line) ? year - line.year : -1;
        if (c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0) {
          local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
          OpexAirFleetRefusal(line, year, "O");
          if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
          if (plan != null && C69_BOTTLENECK_PROBE)
            OpexC73RecordRejection("fleet", "c121_first_live_not_ready", 1);
          continue;
        }
      }
      c121FirstLiveEntry = true;
    } else if (c121BelowTarget) {
      /* Une mesure annuelle complete est le premier feedback fiable apres le
       * cold-start C121. Ne jamais acheter plusieurs renforts sur la meme
       * observation : une nouvelle annee doit confirmer le palier suivant. */
      local c121Age = ("year" in line) ? year - line.year : -1;
      if (c121Age < 2 || !("lastProfit" in line) || line.lastProfit <= 0) {
        local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        OpexAirFleetRefusal(line, year, "O");
        if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "c121_no_full_year_observation", 1);
        continue;
      }
      if (("lastAirFleetYear" in line) && (year - line.lastAirFleetYear) < 2) {
        local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        OpexAirFleetRefusal(line, year, "Y");
        if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "c121_wait_full_year_after_growth", 1);
        continue;
      }
    }
    if (("deadStreak" in line) && line.deadStreak >= 2) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "D");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "dead_line", 1);
      continue;
    }

    // Condition 1 : Les appareils existants ne doivent pas etre deficitaires
    if (!c121BelowTarget && ("lastProfit" in line) && line.lastProfit < 0) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "L");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "negative_profit", 1);
      continue;
    }

    local isSmallAirport = false;
    if ((AIAirport.IsAirportTile(line.stationA) && AIAirport.GetAirportType(line.stationA) == AIAirport.AT_SMALL) ||
        (AIAirport.IsAirportTile(line.stationB) && AIAirport.GetAirportType(line.stationB) == AIAirport.AT_SMALL)) {
      isSmallAirport = true;
    }
    local physicalMaxPlanes = isSmallAirport ? 4 : AIR_MAX_PLANES_PER_ROUTE;
    {
      local spCap = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      {
        if (routesIndex == null) routesIndex = OpexAirBuildRoutesIndex(this._lines);
        physicalMaxPlanes = OpexAirCadenceCapIndexed(line, this._catalog, this._lines, routesIndex);
      }
      if (spCap != null) OpexSpanAgg("fleet.cadence_cap", spCap);
    }
    if (have >= physicalMaxPlanes) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "C");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "airport_capacity_reached", 1);
      continue;
    }
    local maxPlanesForAirport = physicalMaxPlanes;
    if (!c121BelowTarget && ("deadStreak" in line) && line.deadStreak >= 1) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "S");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "poor_health_streak", 1);
      continue;
    }
    if (!c121BelowTarget && ("lastProfit" in line) && line.lastProfit < 0) {
      local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      OpexAirFleetRefusal(line, year, "L");
      if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
      if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "negative_profit", 1);
      continue;
    }

    local planePrice = (this._catalog.plane != null) ? this._catalog.plane.price : 30000;
    if (("vehicles" in line)) {
      foreach (v in line.vehicles) {
        if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
        local ownPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(v));
        if (ownPrice > 0) planePrice = ownPrice;
        break;
      }
    }
    /* Croissance d'une ligne aerienne EXISTANTE : aucun aeroport a batir, donc rien que
     * cette marge doive couvrir. 88 refus insufficient_cash pour 3 acceptations mesures
     * sur 3 parties x 2 ans (results/diag_1v1_decisions.json). */
    local need = planePrice + OpexCashReserve() + 2000;
    local addedThisPass = 0;
    local maxAddedPerPass = 4;
    /* C14 : Dimensionnement dynamique de flotte par le stock au sol (AAAHogEx route.nut:2896-2921).
     * Si AIR_FLEET_BUFFER >= 0 : calcule buildNum = (maxWait - bottom) / capacity.
     * Si buildNum < 1 : refus W (pas assez de cargo au sol).
     * Sinon : autorise jusqu'a min(buildNum, 4). */
    if (c121BelowTarget) {
      /* C121 dimensionne sur flux + rating : attendre une capacite entiere au
       * sol cree une boucle morte (faible frequence -> faible rating -> faible
       * stock). Le portefeuille arbitre donc un seul renfort a la fois jusqu'a
       * la cible, avec le marginal C121 compact publie sur la ligne. */
      maxAddedPerPass = 1;
    } else if (AIR_FLEET_BUFFER >= 0) {
      local planeCap = ("planeCapacity" in line && line.planeCapacity > 0) ? line.planeCapacity : 0;
      if (planeCap <= 0 && ("vehicles" in line)) {
        foreach (v in line.vehicles) {
          if (AIVehicle.IsValidVehicle(v)) {
            planeCap = AIVehicle.GetCapacity(v, line.cargo);
            if (planeCap > 0) { line.planeCapacity <- planeCap; break; }
          }
        }
      }
      local stA = AIStation.GetStationID(line.stationA);
      local hasB = ("stationB" in line) && line.stationB != null;
      local stB = hasB ? AIStation.GetStationID(line.stationB) : 0;
      local waitA = AIStation.IsValidStation(stA) ? AIStation.GetCargoWaiting(stA, line.cargo) : 0;
      local waitB = (hasB && AIStation.IsValidStation(stB)) ? AIStation.GetCargoWaiting(stB, line.cargo) : 0;
      local maxWait = (waitA > waitB) ? waitA : waitB;

      local bottom = (AIR_FLEET_BUFFER < planeCap) ? AIR_FLEET_BUFFER : planeCap;
      local buildNum = 0;
      if (maxWait > bottom && planeCap > 0) {
        buildNum = (maxWait - bottom) / planeCap;
      }
      if (buildNum < 1) {
        local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        OpexAirFleetRefusal(line, year, "W");
        if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
        if (plan != null && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("fleet", "low_stock_buffer", 1);
        continue;
      }
      maxAddedPerPass = (buildNum < 4) ? buildNum : 4;
    }
    if (c121BelowTarget) {
      local targetNeed = line.targetAirPlanes - have;
      if (targetNeed > 0 && maxAddedPerPass > targetNeed) maxAddedPerPass = targetNeed;
    }
    if (plan != null) {
      /* Mode a blanc : on ne touche ni a la tresorerie ni a la ligne. Le test de capital est celui
       * du portefeuille, pas celui d'ici -- c'est tout l'objet de l'arbitrage. */
      local room = maxPlanesForAirport - have;
      local want = (room < maxAddedPerPass) ? room : maxAddedPerPass;
      if (want > 0) {
        local fleetEntry = { line = line, want = want, planePrice = planePrice, baseVehicles = have };
        if (c121FirstLiveEntry) fleetEntry.c121FirstLive <- true;
        {
          /* V161 : voisines AIR vivantes partageant une gare, pour l'a priori. Index
           * construit une fois par passe (aucun achat en mode a blanc). */
          if (routesIndex == null) routesIndex = OpexAirBuildRoutesIndex(this._lines);
          local v161A = OpexAirLineStationId(line, 0);
          local v161B = OpexAirLineStationId(line, 1);
          local v161Nb = 0;
          if (v161A in routesIndex) v161Nb += routesIndex[v161A] - 1;
          if (v161B != v161A && (v161B in routesIndex)) v161Nb += routesIndex[v161B] - 1;
          fleetEntry.v161Neighbours <- v161Nb > 0 ? v161Nb : 0;
        }
        if (AIR_GROW_MARGINAL > 0) {
          fleetEntry.airGrowMarginal <- OpexAirGrowMarginal(line, this._catalog, this._lines, "pending_v161");
          if (AIR_GROW_MARGINAL == 2 && fleetEntry.airGrowMarginal.fallback == "none") {
            if (fleetEntry.airGrowMarginal.dp <= 0) continue;
            fleetEntry.want = 1;
            fleetEntry.planePrice = fleetEntry.airGrowMarginal.price;
          }
        }
        plan.append(fleetEntry);
        if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
          local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
          if (!("c50_want_ym" in line) || line.c50_want_ym != ym) {
            line.c50_want_ym <- ym;
            C50_NON_EXPANSION_LEDGER.air.want_sum += want;
          }
        }
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("fleet", "no_room", 1);
      }
      continue;
    }
    while (have < maxPlanesForAirport && addedThisPass < maxAddedPerPass) {
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need) {
        local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        OpexAirFleetRefusal(line, year, "M");
        if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
        break;
      }
      if (AIR_GROW_MARGINAL > 0) {
        local marginal = OpexAirGrowMarginal(line, this._catalog, this._lines, "direct");
        if (AIR_GROW_MARGINAL == 2 && marginal.fallback == "none" && marginal.dp <= 0) break;
        if (AIR_GROW_MARGINAL == 2 && marginal.fallback == "none") maxAddedPerPass = 1;
      }
      local spAdd = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
      local grown = OpexAirAddPlane(line, this._catalog, this._lines);
      if (spAdd != null) OpexSpanAgg("fleet.add_plane", spAdd);
      routesIndex = null;
      if (("reason" in grown) && (grown.reason == "REEEQUIP_WAIT" || grown.reason == "REPLACE" || grown.reason == "REEEQUIP_FAIL" || grown.reason == "REEEQUIP_ABORT")) {
        if (grown.reason == "REPLACE" && ("vehCount" in grown)) {
          have = grown.vehCount;
          line.vehCount <- have;
          line.trains = have;
        }
        break;
      }
      if (grown.added <= 0) {
        local spRef = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        OpexAirFleetRefusal(line, year, "X");
        if (spRef != null) OpexSpanAgg("fleet.refusal", spRef);
        break;
      }
      have += grown.added;
      addedThisPass += grown.added;
      line.vehCount <- have;
      line.trains = have;
    }
    if (addedThisPass > 0) {
      line.lastAirFleetYear <- year;
      line.lastAirFleetDate <- AIDate.GetCurrentDate();
      if (DECISION_LOG) {
        local yieldVal = OpexAirFleetYield(line);
        OpexDecide("AIR_FLEET", "action=grow line=" + line.lineId + " yield=" + yieldVal + " planes_before=" + (have - addedThisPass) + " planes_after=" + have + " added=" + addedThisPass);
      }
      AILog.Info("[AIR_FLEET] line=" + line.lineId + " added=" + addedThisPass + " total=" + have);
      OpexSign(AIMap.GetTileIndex(1, 10 + line.lineId), "FG|" + (year % 100) + "|" + line.lineId + "|" + have + "|K");
    }
  }

  if (spFleet != null) OpexSpanEnd(spFleet);
  return true;
}
