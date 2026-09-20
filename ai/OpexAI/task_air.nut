/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* C56 follow-up: only airport placement failures identify a bad physical site.
 * A plane/order/cash failure must not poison either endpoint. */
function OpexAI::_markAirFailedSites(plan, result)
{
  if ((!AIR_ABANDON_SITE && !AIR_TOWN_LIMIT_MEMORY) || plan == null || result == null || !("reason" in result)) return;
  if (!("airport" in plan) || plan.airport == null || !("error" in result)) return;
  local reason = result.reason;
  if (AIR_TOWN_LIMIT_MEMORY && result.error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) {
    if ((reason == "PREA" || reason == "AFAIL") && ("siteA" in plan) && plan.siteA != null) {
      this._markPairAbandoned(OpexAirTownLimitAbandonKey(plan.siteA));
    }
    if ((reason == "PREB" || reason == "BFAIL") && ("siteB" in plan) && plan.siteB != null) {
      this._markPairAbandoned(OpexAirTownLimitAbandonKey(plan.siteB));
    }
  }
  if (!AIR_ABANDON_SITE) return;
  /* Only terrain failures survive a different route, date or town rating. */
  if (result.error != AIError.ERR_FLAT_LAND_REQUIRED
      && result.error != AIError.ERR_LAND_SLOPED_WRONG
      && result.error != AIError.ERR_AREA_NOT_CLEAR
      && result.error != AIError.ERR_SITE_UNSUITABLE) return;
  if ((reason == "PREA" || reason == "AFAIL") && ("siteA" in plan) && plan.siteA != null) {
    this._markPairAbandoned(OpexAirSiteAbandonKey(plan.siteA, plan.airport.type));
  }
  if ((reason == "PREB" || reason == "BFAIL") && ("siteB" in plan) && plan.siteB != null) {
    this._markPairAbandoned(OpexAirSiteAbandonKey(plan.siteB, plan.airport.type));
  }
}
/* Liaison aerienne passagers a fort ROI. Deploie la tresorerie excedentaire sans A*. */
function OpexAI::_tryBuildAir(year)
{
  /* La garde testait `airCombos == null && airport == null`. Deux defauts (docs/taches.md
   * S0 sexies) : `_refreshAir` pose TOUJOURS une liste, meme vide (catalog.nut met `[]` avant sa
   * sortie anticipee), donc la garde ne pouvait jamais se declencher sur « aucun avion
   * disponible » et la fonction partait dans sa boucle sur des cartes sans combo ; et le seul etat
   * qu'elle laissait passer -- `airCombos == null` avec `airport != null` -- faisait dereferencer
   * `airCombos.len()` plus bas, ce qui TUE l'IA. On teste desormais la vacuite reelle, et le
   * deref est protege a son propre site. */
  local combos = this._catalog.airCombos;
  if ((combos == null || combos.len() == 0) && this._catalog.airport == null) {
    if (DECISION_LOG) {
      local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
      if (_lastAirRefuseMonth != ym) {
        _lastAirRefuseMonth = ym;
        OpexDecide("AIR_REFUSE", "reason=no_aircraft_and_airport");
      }
    }
    return;
  }
  local maxPerYear = 30;
  local maxTotal = 250;
  local maxBatch = 12;
  local builtCount = 0;
  while (builtCount < maxBatch) {
    local airLinesThisYear = 0;
    local totalAirLines = 0;
    foreach (line in this._lines) {
      if (("mode" in line) && line.mode == "air") {
        totalAirLines++;
        if (line.year == year) airLinesThisYear++;
      }
    }
    if (airLinesThisYear >= maxPerYear || totalAirLines >= maxTotal) {
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=line_cap_reached lines_year=" + airLinesThisYear + " max_year=" + maxPerYear + " total=" + totalAirLines + " max_total=" + maxTotal);
        }
      }
      break;
    }

    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    local borrowable = REBORROW ? (AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount()) : 0;
    if (borrowable < 0) borrowable = 0;
    local baseReserve = OpexCashReserve();
    /* ⚠️ NE PAS « CORRIGER » CE 2 000 EN LE PORTANT A LA MARGE MAXIMALE. Essaye et MESURE le
     * 2026-09-02 (results/bench_lotE_air_marge_3y.json) : -11,5 % de valeur (t = -2,66), -9,8 % de
     * note officielle (t = -3,25), -11,2 % de gares.
     *
     * Le defaut apparent est reel : le test d'acceptation plus bas exige `requiredMargin` (jusqu'a
     * 30 000 pour deux aeroports neufs), donc un plan tombant dans cette bande est trouve puis
     * rejete, et le `break` gache le cycle. Mais `maxCapital` n'est PAS qu'un filtre : c'est le
     * budget avec lequel OpexAirPlans CHOISIT le plan a proposer. Le reduire de 30 000 partout
     * appauvrit la selection dans tous les cas ou l'ancienne marge suffisait -- notamment le
     * hub-a-hub, dont la marge reelle n'est que 2 000. On echange une boucle bloquee rare contre
     * une degradation systematique.
     *
     * La bonne correction passerait par le plan, pas par le budget : soit passer la marge exigee a
     * OpexAirPlans pour qu'il l'applique par plan, soit ne pas `break` sur rejet et reessayer avec
     * un budget rabote. Voir docs/taches.md. */
    local maxCapital = money + borrowable - baseReserve - 2000;
    if (maxCapital <= 0) {
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=insufficient_capital cash=" + money + " reserve=" + baseReserve);
        }
      }
      break;
    }

    this._budget.begin();
    local plan = OpexAirPlans(this._catalog, this._lines, maxCapital, null,
                              (AIR_ABANDON && ABANDON_MEMORY) ? this._abandonedPairs : null);
    local planOps = this._budget.end("build_air_plans");
    if (plan == null) {
      local nCombos = (this._catalog.airCombos == null) ? -1 : this._catalog.airCombos.len();
      if (builtCount == 0) {
        /* airCombos peut etre null : ne jamais dereferencer pour un panneau de diagnostic. */
        OpexSign(AIMap.GetTileIndex(1, 1), "AD|NULL|C=" + nCombos);
      }
      if (DECISION_LOG) {
        local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
        if (_lastAirRefuseMonth != ym) {
          _lastAirRefuseMonth = ym;
          OpexDecide("AIR_REFUSE", "reason=no_candidate combos=" + nCombos);
        }
      }
      break;
    }

    local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
    if (EQUIPMENT_ROI_PROBE) OpexM3ProbeAirEquipment(this._catalog, plan, "direct_selected");
    local requiredMargin = AIR_MARGIN_V2
          ? ((newAirports == 2) ? 15000 : (newAirports == 1 ? 6000 : 0))
          : ((newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000));
    local capital = ("capital" in plan) ? plan.capital : (newAirports * plan.airport.price + plan.plane.price);
    local need = capital + baseReserve + requiredMargin;
    if (money < need) {
      if (REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (DECISION_LOG) {
          local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
          if (_lastAirRefuseMonth != ym) {
            _lastAirRefuseMonth = ym;
            OpexDecide("AIR_REFUSE", "reason=insufficient_cash cash=" + money + " need=" + need + " capital=" + capital + " margin=" + requiredMargin);
          }
        }
        break;
      }
    }

    if (AIR_EQUIPMENT_REGRET_PROBE && ("proxyRescued" in plan) && plan.proxyRescued) {
      OpexSign(AIMap.GetTileIndex(2, 5), "AR3|" + (plan.economics.profitAnnual / 1000));
    }

    local result = OpexBuildAirRoute(this._catalog, this._budget, plan);
    if (C63_INVEST_PROBE) OpexC63RecordSpendResult("air", result, plan.capital);
    local anchor = AIMap.GetTileIndex(1, 1);
    OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
    if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
    if (AIR_COST_PROBE) {
      OpexSign(anchor, "AC|" + this._nextLineId + "|" + result.plannedCapital + "|"
                             + result.actualCost + "|"
                             + (("planes" in plan) ? plan.planes : 1) + "|"
                             + (result.ok ? result.vehicles.len() : 0));
    }
    if (!result.ok) {
      if (DECISION_LOG) {
        OpexDecide("AIR_REFUSE", "reason=build_failed detail=" + result.reason + " error=" + result.error + " error_text=" + result.errorText + " dist=" + plan.distance + " cost=" + result.actualCost);
      }
      /* air_abandon : sans cette memorisation, le cycle suivant re-scanne tous les sites pour
       * reproposer EXACTEMENT le meme bestPlan et echouer de la meme facon. Le chemin
       * portefeuille memorise deja ses echecs (voir plus bas) ; ce chemin-ci ne le faisait pas. */
      if (AIR_ABANDON && ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) {
        this._markPairAbandoned("air|" + plan.siteA.town.tile + "|" + plan.siteB.town.tile);
        this._markAirFailedSites(plan, result);
      }
      break;
    }

    this._airBuilt = true;
    if (DECISION_LOG) {
      OpexDecide("AIR_BUILD", "arm=" + plan.arm + " line=" + this._nextLineId + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id + " dist=" + plan.distance + " profit=" + plan.economics.profitAnnual + " cost=" + plan.capital + " planes=" + result.vehicles.len());
    }
    this._lines.append({
      stationA = result.stationA, stationB = result.stationB,
      originA = plan.siteA.town.tile, originB = plan.siteB.town.tile,
      cargo = this._catalog.paxCargo,
      predicted = ("economics" in plan && "profitAnnual" in plan.economics) ? plan.economics.profitAnnual : 0,
      predRevenue = plan.economics.revenueAnnual, predRunning = plan.economics.runningAnnual,
      predAmort = plan.economics.amortAnnual, predCarried = plan.economics.carried,
      predTrains = plan.planes, predOneWayDays = plan.economics.oneWayDays,
      planeCapacity = plan.plane.capacity,
      sharedAirportA = ("reuseA" in plan) && plan.reuseA,
      hubRoutesAtBuild = ("hubRoutes" in plan) ? plan.hubRoutes : 0,
      joinedStopsA = result.joinedStopsA, joinedStopsB = result.joinedStopsB,
      joinedMonthlyPax = result.joinedMonthlyPax, joinedStopCost = result.joinedStopCost,
      actualCapital = plan.capital,
      iterations = 0, trains = result.vehicles.len(), distance = plan.distance, year = year,
      buildDate = AIDate.GetCurrentDate(),
      mode = "air", vehicle = result.vehicle, vehicles = result.vehicles,
      refleetEngine = AIVehicle.GetEngineType(result.vehicle),
      currentPrimaryEngine = AIVehicle.GetEngineType(result.vehicle),
      preferredEngine = AIVehicle.GetEngineType(result.vehicle),
      targetFleetSize = result.vehicles.len(),
      upgradePending = false, upgradeRemaining = 0,
      upgradeGainAnnual = 0, upgradeGrossCapital = 0, upgradeResaleValue = 0,
      upgradeNetCapital = 0, upgradePaybackMonths = 0,
      lastAirEquipmentEvalDate = AIDate.GetCurrentDate(), airEquipmentDirty = false,
      airEquipmentDirtyReason = "",
      previewCommitment = null,
      vehCount = result.vehicles.len(),
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lastLiveVehicles = result.vehicles.len(), suspectedCrashes = 0,
      isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
      lineId = this._nextLineId,
    });
    OpexSign(anchor, "AF|" + this._nextLineId + "|" + result.vehicles.len() + "|"
                           + plan.economics.profitAnnual);
    OpexSign(anchor, "AH|" + this._nextLineId + "|"
                     + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0) + "|"
                     + plan.capital + "|" + (("hubRoutes" in plan) ? plan.hubRoutes : 0));
    OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                     + AICargo.GetCargoLabel(this._catalog.paxCargo));
    this._nextLineId++;
    builtCount++;
  }
}
/* Revalidation air du batch : un plan garde ses deux sites depuis la generation, mais un succes
 * precedent a pu y poser une gare, une route ou un aeroport. Ce probe ne tourne donc JAMAIS pour
 * le premier projet ; le precedent mesure est maxBatch=1, ou le plan etait encore celui de la
 * generation. Il reprend le test utile de OpexAirFindSite, y compris le nivellement que le vrai
 * constructeur fera, sans relancer OpexAirPlans ni ses panneaux. */
function OpexAirBatchSiteStillBuildable(site, airport, plane, reuse)
{
  if (reuse) {
    return AIAirport.IsAirportTile(site.anchor) &&
           OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(site.anchor), plane.planeType);
  }
  local end = site.anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
  if (!AIMap.IsValidTile(end)) return false;
  local ok = false;
  {
    local probe = AITestMode();
    ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW);
    if (!ok) {
      local error = AIError.GetLastError();
      if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
      else {
        AITile.LevelTiles(site.anchor, end);
        ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW);
        if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
      }
    }
  }
  return ok;
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
  local maxRoutes = (airportType == AIAirport.AT_SMALL || airportType == AIAirport.AT_COMMUTER) ? 4 : 12;
  return routes < maxRoutes;
}
/* La paire O/D et les bouts nouveaux etaient valides dans le portefeuille fige. Apres un succes,
 * ils peuvent desormais etre deja servis ; on les ecarte plutot que de laisser le constructeur
 * detruire puis echouer. Les scans sont bornes par PORTFOLIO_MAX_BATCH <= 8 et absents du controle
 * maxBatch=1, pour ne pas recreer le cout de panneaux qui avait deplace les frontieres de ticks. */
function OpexAirBatchPlanStillLive(plan, lines)
{
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (!reuseA && OpexAirTownServed(plan.siteA.town, lines)) return false;
  if (!reuseB && OpexAirTownServed(plan.siteB.town, lines)) return false;
  if (reuseA && !OpexAirBatchHubHasCapacity(plan.siteA.anchor, plan.plane, lines)) return false;
  if (reuseB && !OpexAirBatchHubHasCapacity(plan.siteB.anchor, plan.plane, lines)) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if ((line.originA == plan.siteA.town.tile && line.originB == plan.siteB.town.tile) ||
        (line.originA == plan.siteB.town.tile && line.originB == plan.siteA.town.tile)) return false;
  }
  return true;
}
/* C48 : Verification O(1) directe par lookup spatial dans idx.airServedTiles. */
function OpexAirTownServedIndexed(town, idx)
{
  if (idx == null || town == null) return false;
  return (town.tile in idx.airServedTiles);
}
/* C48 : Verification O(1) de la capacite du hub aerien via idx.airStationRoutes. */
function OpexAirBatchHubHasCapacityIndexed(anchor, plane, idx)
{
  if (!AIAirport.IsAirportTile(anchor) ||
      !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(anchor), plane.planeType)) return false;
  local station = AIStation.GetStationID(anchor);
  if (!AIStation.IsValidStation(station)) return false;
  local routes = (station in idx.airStationRoutes) ? idx.airStationRoutes[station] : 0;
  local airportType = AIAirport.GetAirportType(anchor);
  local maxRoutes = (airportType == AIAirport.AT_SMALL || airportType == AIAirport.AT_COMMUTER) ? 4 : 12;
  return routes < maxRoutes;
}
/* C48 : Version O(1) de OpexAirBatchPlanStillLive utilisant la structure d'indexation. */
function OpexAirBatchPlanStillLiveIndexed(plan, idx)
{
  if (idx == null || plan == null) return false;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  if (!reuseA && OpexAirTownServedIndexed(plan.siteA.town, idx)) return false;
  if (!reuseB && OpexAirTownServedIndexed(plan.siteB.town, idx)) return false;
  if (reuseA && !OpexAirBatchHubHasCapacityIndexed(plan.siteA.anchor, plan.plane, idx)) return false;
  if (reuseB && !OpexAirBatchHubHasCapacityIndexed(plan.siteB.anchor, plan.plane, idx)) return false;
  local a = plan.siteA.town.tile;
  local b = plan.siteB.town.tile;
  local pairKey = (a < b) ? (a + "|" + b) : (b + "|" + a);
  if (pairKey in idx.airPairs) return false;
  return true;
}
/* C38 etape 2 : tentative synchrone air, incluant les gardes de site et de flotte. */
function OpexAI::_tryBuildAirProject(year, project, rank, builtCount, passDiscards, anchor, yy)
{
  if (project == null) return { outcome = "no_candidate", discards = passDiscards };
  local i = rank;
      local plan = project.payload;
      local useCapitalFrontier = AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT;
      /* Un seul lambda par portfolio/pass. Ne pas invalider le choix sur une
       * variation de caisse intra-pass : la garde de financement ci-dessous
       * utilise toujours la tresorerie vivante, tandis que la revalidation
       * economique frontier reste obligatoire juste avant la construction. */
      if (builtCount > 0 || useCapitalFrontier) {
        if (!OpexAirBatchPlanStillLive(plan, this._lines)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "batch_plan_dead", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (!OpexAirBatchSiteStillBuildable(plan.siteA, plan.airport, plan.plane,
                                             ("reuseA" in plan) && plan.reuseA)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteA_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
        if (!OpexAirBatchSiteStillBuildable(plan.siteB, plan.airport, plan.plane,
                                             ("reuseB" in plan) && plan.reuseB)) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "siteB_unbuildable", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
      }
      local townAId = ("siteA" in plan && "town" in plan.siteA && "id" in plan.siteA.town) ? plan.siteA.town.id : -1;
      local townBId = ("siteB" in plan && "town" in plan.siteB && "id" in plan.siteB.town) ? plan.siteB.town.id : -1;
      if (C60_TOWN_RATING_PROBE) {
        if (townAId >= 0) OpexC60ObserveTownRating("air", "build_precheck", townAId);
        if (townBId >= 0) OpexC60ObserveTownRating("air", "build_precheck", townBId);
      }
      if (C60_TOWN_RATING_FILTER) {
        if ((townAId >= 0 && OpexTownRatingHopeless(townAId)) ||
            (townBId >= 0 && OpexTownRatingHopeless(townBId))) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "town_rating_appalling", extra = "" });
          return { outcome = "rejected", discards = passDiscards };
        }
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
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "line_cap_reached", extra = "lines_year=" + airLinesThisYear + " total=" + totalAirLines });
        return { outcome = "rejected", discards = passDiscards };
      }
      local abandonedKey = "air|" + plan.siteA.town.tile + "|" + plan.siteB.town.tile;
      local abandonedSiteA = OpexAirSiteAbandonKey(plan.siteA, plan.airport.type);
      local abandonedSiteB = OpexAirSiteAbandonKey(plan.siteB, plan.airport.type);
      local abandonedTownA = OpexAirTownLimitAbandonKey(plan.siteA);
      local abandonedTownB = OpexAirTownLimitAbandonKey(plan.siteB);
      if (ABANDON_MEMORY && ((abandonedKey in this._abandonedPairs)
          || (AIR_TOWN_LIMIT_MEMORY && ((!(("reuseA" in plan) && plan.reuseA) && (abandonedTownA in this._abandonedPairs))
              || (!(("reuseB" in plan) && plan.reuseB) && (abandonedTownB in this._abandonedPairs))))
          || (AIR_ABANDON_SITE && ((abandonedSiteA in this._abandonedPairs)
              || (abandonedSiteB in this._abandonedPairs))))) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      if (useCapitalFrontier) {
        local freshSelection = OpexAirFreshSelectedProjectEconomics(
            project, this._catalog, this._lines);
        local selectedProfit = ("frontierSelectionProfit" in project)
            ? project.frontierSelectionProfit : OpexCapitalFrontierProjectProfit(project);
        local selectedShadowCapital = ("frontierSelectionShadowCapital" in project)
            ? project.frontierSelectionShadowCapital : OpexProjectShadowCapital(project);
        local selectedFinanceCapital = ("frontierSelectionFinanceCapital" in project)
            ? project.frontierSelectionFinanceCapital : OpexProjectFinanceCapital(project);
        if (!freshSelection.ok
            || freshSelection.networkProfit != selectedProfit
            || freshSelection.shadowCapital != selectedShadowCapital
            || freshSelection.financeCapital != selectedFinanceCapital) {
          if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL)
            passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile,
                                  dst = plan.siteB.town.tile, reason = "frontier_reselect",
                                  extra = "economics" });
          return { outcome = "reselect", discards = passDiscards,
                   reselectReason = "economics", refreshEconomics = true };
        }
      }

      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
      if (EQUIPMENT_ROI_PROBE) OpexM3ProbeAirEquipment(this._catalog, plan, "portfolio_selected");
      local requiredMargin = OpexAirProjectSafetyMargin(newAirports);
      local capital = ("capital" in plan) ? plan.capital : (newAirports * plan.airport.price + plan.plane.price);
      local need = capital + OpexCashReserve() + requiredMargin;
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("air", i, capital, plan.economics.profitAnnual, project.roi, plan.siteA.town.tile, plan.siteB.town.tile, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      if (AIR_EQUIPMENT_REGRET_PROBE && ("proxyRescued" in plan) && plan.proxyRescued) {
        OpexSign(AIMap.GetTileIndex(2, 5), "AR3|" + (plan.economics.profitAnnual / 1000));
      }

      OpexSign(anchor, "IP|" + yy + "|A|" + project.budgetScore + "|" + project.opcodeScore);
      if (AIR_EARLY_SLOT && ("earlySlotBonusPct" in project) && project.earlySlotBonusPct > 0) {
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
      local result = OpexBuildAirRoute(this._catalog, this._budget, plan);
      if (C63_INVEST_PROBE) OpexC63RecordSpendResult("air", result, plan.capital);
      OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
      if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
      if (AIR_COST_PROBE) {
        OpexSign(anchor, "AC|" + this._nextLineId + "|" + result.plannedCapital + "|"
                               + result.actualCost + "|"
                               + (("planes" in plan) ? plan.planes : 1) + "|"
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
            && (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL)) {
          local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
          ownAirports.Valuate(AIStation.GetNearestTown);
          ownAirports.KeepValue(errorTown);
          errorOwnAirports = ownAirports.Count();
        }
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({
          rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile,
          reason = "build_failed", detail = result.reason, error = result.error,
          error_anchor = errorAnchor, error_town = errorTown,
          error_own_airports = errorOwnAirports, extra = ""
        });
        if (DECISION_LOG) {
          OpexDecide("PROJECT_DISCARD", "rank=" + i + " mode=air src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " reason=build_failed detail=" + result.reason + " error=" + result.error + " error_text=" + result.errorText);
        }
        if (ABANDON_MEMORY && OpexBuildFailureIsAbandonable(result)) {
          this._markPairAbandoned(abandonedKey);
          this._markAirFailedSites(plan, result);
        }
        return { outcome = "rejected", discards = passDiscards };
      }
      if (result.ok) {
        if (DECISION_LOG) {
          foreach (d in passDiscards) {
            OpexDecide("PROJECT_DISCARD", "rank=" + d.rank + " mode=" + d.mode + " src=" + d.src + " dst=" + d.dst + " reason=" + d.reason + (d.extra != "" ? " " + d.extra : ""));
          }
          passDiscards = [];
          local cargoStr = AICargo.GetCargoLabel(this._catalog.paxCargo);
          OpexDecide("PROJECT_CHOSEN", "rank=" + i + " mode=air cargo=" + cargoStr + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " dist=" + plan.distance + " cost=" + plan.capital + " profit=" + plan.economics.profitAnnual + " roi=" + project.roi);
          OpexDecide("AIR_BUILD", "arm=" + plan.arm + " line=" + this._nextLineId + " src=" + plan.siteA.town.tile + " dst=" + plan.siteB.town.tile + " src_town=" + plan.siteA.town.id + " dst_town=" + plan.siteB.town.id + " dist=" + plan.distance + " profit=" + plan.economics.profitAnnual + " cost=" + plan.capital + " planes=" + result.vehicles.len());
        }
        this._airBuilt = true;
        this._lines.append({
          stationA = result.stationA, stationB = result.stationB,
          originA = plan.siteA.town.tile, originB = plan.siteB.town.tile,
          cargo = this._catalog.paxCargo,
          predicted = ("economics" in plan && "profitAnnual" in plan.economics) ? plan.economics.profitAnnual : 0,
          predRevenue = plan.economics.revenueAnnual, predRunning = plan.economics.runningAnnual,
          predAmort = plan.economics.amortAnnual, predCarried = plan.economics.carried,
          predTrains = plan.planes, predOneWayDays = plan.economics.oneWayDays,
          planeCapacity = plan.plane.capacity,
          sharedAirportA = ("reuseA" in plan) && plan.reuseA,
          hubRoutesAtBuild = ("hubRoutes" in plan) ? plan.hubRoutes : 0,
          joinedStopsA = result.joinedStopsA, joinedStopsB = result.joinedStopsB,
          joinedMonthlyPax = result.joinedMonthlyPax, joinedStopCost = result.joinedStopCost,
          actualCapital = plan.capital,
          iterations = 0, trains = result.vehicles.len(), distance = plan.distance, year = year,
          buildDate = AIDate.GetCurrentDate(),
          mode = "air", vehicle = result.vehicle, vehicles = result.vehicles,
          refleetEngine = AIVehicle.GetEngineType(result.vehicle),
          currentPrimaryEngine = AIVehicle.GetEngineType(result.vehicle),
          preferredEngine = AIVehicle.GetEngineType(result.vehicle),
          targetFleetSize = result.vehicles.len(),
          upgradePending = false, upgradeRemaining = 0,
          upgradeGainAnnual = 0, upgradeGrossCapital = 0, upgradeResaleValue = 0,
          upgradeNetCapital = 0, upgradePaybackMonths = 0,
          lastAirEquipmentEvalDate = AIDate.GetCurrentDate(), airEquipmentDirty = false,
          airEquipmentDirtyReason = "",
          previewCommitment = null,
          vehCount = result.vehicles.len(),
          deadStreak = 0, scrapping = false, scrapVehicles = [],
          lastLiveVehicles = result.vehicles.len(), suspectedCrashes = 0,
          isLowRatio = false, opcodeRatio = -1,   /* plan, pas de candidat : sans objet */
          lineId = this._nextLineId,
        });
        OpexSign(anchor, "AF|" + this._nextLineId + "|" + result.vehicles.len() + "|"
                               + plan.economics.profitAnnual);
        OpexSign(anchor, "AH|" + this._nextLineId + "|"
                         + ((("reuseA" in plan) && plan.reuseA) ? 1 : 0) + "|"
                         + plan.capital + "|" + (("hubRoutes" in plan) ? plan.hubRoutes : 0));
        OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                         + AICargo.GetCargoLabel(this._catalog.paxCargo));
        if (AIR_EARLY_SLOT && ("earlySlotBonusPct" in project) && project.earlySlotBonusPct > 0) {
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
 * C plafond physique de l'aeroport atteint, Q plafond de demande atteint,
 * S un an de mauvaise sante, K ligne en cours de rebut, M tresorerie, X l'achat a echoue. */
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
    else if (code == "Q") reasonStr = "demand_cap_reached";
    else if (code == "S") reasonStr = "poor_health_streak";
    else if (code == "K") reasonStr = "scrapping";
    else if (code == "M") reasonStr = "insufficient_cash";
    else if (code == "X") reasonStr = "purchase_failed";
    else if (code == "T") reasonStr = "target_equipment_missing";
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
/* Comparateur de tete de file pour la croissance aerienne : meilleur rendement d'abord.
 * Fonction NOMMEE au niveau module : dans cet environnement
 * Squirrel une closure imbriquee ne capture jamais les locales englobantes. */
function OpexAirFleetPriorityCompare(a, b)
{
  local ya = OpexAirFleetYield(a);
  local yb = OpexAirFleetYield(b);
  if (ya > yb) return -1;
  if (ya < yb) return 1;
  return 0;
}

function OpexAirApplyLineAssessment(line, assessment)
{
  if (line == null || assessment == null || !assessment.ok) return false;
  line.rawset("currentPrimaryEngine", assessment.currentEngine);
  line.rawset("preferredEngine", assessment.preferredEngine);
  line.rawset("targetFleetSize", assessment.targetFleetSize);
  line.rawset("upgradePending", assessment.upgradePending);
  line.rawset("upgradeRemaining", assessment.upgradeRemaining);
  line.rawset("upgradeGainAnnual", assessment.gainAnnual);
  local upgradeUnitGain = assessment.gainAnnual;
  if (assessment.upgradeRemaining > 0) {
    upgradeUnitGain = assessment.gainAnnual / assessment.upgradeRemaining;
  }
  line.rawset("upgradeUnitGainAnnual", upgradeUnitGain);
  line.rawset("upgradeGrossCapital", ("grossReplacement" in assessment) ? assessment.grossReplacement : 0);
  line.rawset("upgradeResaleValue", ("resaleValue" in assessment) ? assessment.resaleValue : 0);
  line.rawset("upgradeNetCapital", assessment.netCapital);
  line.rawset("upgradePaybackMonths", assessment.paybackMonths);
  line.rawset("currentModelProfitAnnual", assessment.currentEconomics != null
      ? assessment.currentEconomics.profitAnnual : 0);
  line.rawset("lastAirEquipmentEvalDate", AIDate.GetCurrentDate());
  line.rawset("airEquipmentDirty", false);
  line.rawset("airEquipmentDirtyReason", "");
  /* `refleetEngine` reste la metadonnee historique de reconstruction C68. Sous le candidat,
   * preferredEngine est la seule cible et doit rester distincte de l'ancien moteur memorise. */
  if (!AIR_BEST_EQUIPMENT && assessment.preferredEngine >= 0) line.rawset("refleetEngine", assessment.preferredEngine);
  if (assessment.targetEconomics != null) {
    line.rawset("targetHeadwayDays", assessment.targetEconomics.headwayDays.tointeger());
    line.rawset("targetMonthlyCapacity", assessment.targetEconomics.monthlyCapacity.tointeger());
    line.rawset("targetStationRating", assessment.targetEconomics.stationRating.tointeger());
    line.rawset("targetProfitAnnual", assessment.targetEconomics.profitAnnual);
  }
  return true;
}

/* Frontier lifecycle P1 : une evaluation produit un VIVIER de transactions et non
 * une cible durable. Le vivier est garde sur la ligne jusqu'a la prochaine
 * invalidation afin que deux reconstructions successives du portefeuille voient
 * exactement les memes occasions. Ne stocker ici que des scalaires serialisables :
 * les tables economics contiennent des floats et ne doivent jamais entrer dans le
 * save NoAI via line. */
function OpexAirClearFrontierTransactions(line)
{
  if (line == null) return;
  if ("airFrontierTransactions" in line) delete line["airFrontierTransactions"];
  if ("airFrontierRevisionDate" in line) delete line["airFrontierRevisionDate"];
  if ("airFrontierRevisionReason" in line) delete line["airFrontierRevisionReason"];
}

function OpexAirStoreFrontierTransactions(line, frontierOptions, now, reason)
{
  if (line == null) return 0;
  local revision = ("airFrontierRevision" in line) ? line.airFrontierRevision + 1 : 1;
  local transactions = [];
  if (frontierOptions != null) {
    foreach (option in frontierOptions) {
      if (option == null) continue;
      local payback = option.capitalCommitted > 0
          ? OpexCeilDiv(option.capitalCommitted * 12, option.profitDeltaAnnual) : 0;
      transactions.append({
        kind = option.stepKind == "grow" ? "growth" : "upgrade",
        want = 1,
        targetEngine = option.targetEngine,
        targetFleetSize = option.targetFleetSize,
        retireOnly = option.retireOnly,
        planePrice = option.planePrice,
        cashRequired = option.cashRequired,
        safetyMargin = option.safetyMargin,
        capitalCommitted = option.capitalCommitted,
        expectedResale = option.expectedResale,
        transitDelta = option.transitDelta,
        profitDeltaAnnual = option.profitDeltaAnnual,
        profitAnnual = option.profitDeltaAnnual,
        netCapital = option.capitalCommitted,
        paybackMonths = payback,
        planningOps = 0,
        executionOps = PROJECT_ROAD_TRANSACTION_OPS,
        frontierStepKind = option.stepKind,
        frontierRevision = revision,
        frontierTransaction = true,
      });
    }
  }
  line.rawset("airFrontierRevision", revision);
  line.rawset("airFrontierRevisionDate", now);
  line.rawset("airFrontierRevisionReason", reason);
  line.rawset("airFrontierTransactions", transactions);
  return transactions.len();
}

function OpexAirAppendFrontierTransactions(line, plan)
{
  if (line == null || plan == null || !("airFrontierTransactions" in line)
      || line.airFrontierTransactions == null) return 0;
  local revision = ("airFrontierRevision" in line) ? line.airFrontierRevision : 0;
  local appended = 0;
  foreach (transaction in line.airFrontierTransactions) {
    if (transaction == null || !("frontierRevision" in transaction)
        || transaction.frontierRevision != revision) continue;
    plan.append({
      kind = transaction.kind,
      line = line,
      want = transaction.want,
      targetEngine = transaction.targetEngine,
      targetFleetSize = transaction.targetFleetSize,
      retireOnly = transaction.retireOnly,
      planePrice = transaction.planePrice,
      cashRequired = transaction.cashRequired,
      safetyMargin = transaction.safetyMargin,
      capitalCommitted = transaction.capitalCommitted,
      expectedResale = transaction.expectedResale,
      transitDelta = transaction.transitDelta,
      profitDeltaAnnual = transaction.profitDeltaAnnual,
      profitAnnual = transaction.profitAnnual,
      netCapital = transaction.netCapital,
      paybackMonths = transaction.paybackMonths,
      planningOps = transaction.planningOps,
      executionOps = transaction.executionOps,
      frontierStepKind = transaction.frontierStepKind,
      frontierRevision = transaction.frontierRevision,
      frontierTransaction = true,
    });
    appended++;
  }
  return appended;
}

function OpexAI::_queueAirRetirement(line, vehicle, reason, replacementVehicle = -1)
{
  if (line == null || !AIVehicle.IsValidVehicle(vehicle)) return false;
  if (!AIVehicle.SendVehicleToDepot(vehicle)) return false;
  local now = AIDate.GetCurrentDate();
  if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
  this._vehiclesToRetire.rawset(vehicle, {
    lineId = line.lineId, startedDate = now, lastSendDate = now, attempts = 1, reason = reason,
    replacementVehicle = replacementVehicle
  });
  if (("vehicles" in line) && line.vehicles != null) {
    for (local i = 0; i < line.vehicles.len(); i++) {
      if (line.vehicles[i] == vehicle) { line.vehicles.remove(i); break; }
    }
  }
  if (("vehicle" in line) && line.vehicle == vehicle) {
    local replacement = -1;
    if (("vehicles" in line) && line.vehicles != null) {
      foreach (candidate in line.vehicles) {
        if (AIVehicle.IsValidVehicle(candidate)) { replacement = candidate; break; }
      }
    }
    line.vehicle = replacement;
  }
  local live = (("vehicles" in line) && line.vehicles != null) ? line.vehicles.len() : 0;
  line.rawset("vehCount", live);
  line.rawset("trains", live);
  if (AIR_BEST_EQUIPMENT) AIR_LIFECYCLE_LEDGER.retireQueued++;
  return true;
}

function OpexAI::_abandonAirPreviewCommitment(line, reason, cause = "runtime")
{
  if (line == null || !("previewCommitment" in line) || line.previewCommitment == null) return false;
  AIR_LIFECYCLE_LEDGER.previewAbandoned++;
  if (reason == "not_preferred_by_common_engine") AIR_LIFECYCLE_LEDGER.previewAbandonCommon++;
  if (reason == "timeout") AIR_LIFECYCLE_LEDGER.previewAbandonTimeout++;
  if (DECISION_LOG) {
    OpexDecide("AIR_PREVIEW_COMMITMENT", "action=abandon line=" + line.lineId
               + " cause=" + cause + " reason=" + reason);
  }
  line.previewCommitment = null;
  return true;
}

/* Convertit l'identite d'un preview en engagement executable APRES la reevaluation normale de
 * ligne. L'economie n'est jamais recalculee ici : `assessment` vient obligatoirement de
 * OpexAirAssessExistingLine -> OpexAirBestEquipment -> OpexAirEconomics. Ainsi
 * ET_ENGINE_AVAILABLE ne cree aucune seconde politique avion x flotte. */
function OpexAI::_resolveAirPreviewCommitment(line, engine, assessment, cause = "engine_available")
{
  if (line == null || !("previewCommitment" in line) || line.previewCommitment == null) return false;
  local commitment = line.previewCommitment;
  if (!("resolvedEngine" in commitment) || commitment.resolvedEngine != engine) return false;
  if (!OpexAirPreviewMatchesEngine(commitment, engine)) {
    this._abandonAirPreviewCommitment(line, "engine_identity_mismatch", cause);
    return false;
  }
  if (!AIEngine.IsValidEngine(engine) || !AIEngine.IsBuildable(engine)
      || !OpexAirEngineRelevantToLine(engine, line)) {
    this._abandonAirPreviewCommitment(line, "resolved_engine_unavailable", cause);
    return false;
  }
  if (assessment == null || !assessment.ok) {
    this._abandonAirPreviewCommitment(line,
        assessment == null ? "assessment_missing" : assessment.reason, cause);
    return false;
  }
  if (assessment.preferredEngine != engine) {
    /* Le moteur commun a tranche pour une autre configuration : la promesse preview est
     * explicitement abandonnee, tandis que la cible normale deja appliquee reste autoritaire. */
    this._abandonAirPreviewCommitment(line, "not_preferred_by_common_engine", cause);
    return false;
  }
  local have = 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) have++;
    }
  }
  local hasConcreteUse = assessment.upgradeRemaining > 0 || assessment.targetFleetSize > have;
  if (!hasConcreteUse) {
    this._abandonAirPreviewCommitment(line, "no_concrete_use", cause);
    return false;
  }
  local wasResolved = ("status" in commitment) && commitment.status == "resolved";
  /* Une reevaluation ulterieure ne doit pas repousser indefiniment l'echeance
   * d'un engagement deja resolu. */
  if (!wasResolved) commitment.rawset("resolvedDate", AIDate.GetCurrentDate());
  commitment.rawset("status", "resolved");
  if (!wasResolved) AIR_LIFECYCLE_LEDGER.previewMatched++;
  if (DECISION_LOG) {
    OpexDecide("AIR_PREVIEW_COMMITMENT", "action=resolve line=" + line.lineId
               + " cause=" + cause + " engine=" + engine + " target_fleet=" + assessment.targetFleetSize
               + " gain=" + assessment.gainAnnual + " net_capital=" + assessment.netCapital
               + " payback_months=" + assessment.paybackMonths);
  }
  return true;
}

/* Un engagement est considere honore au premier achat REEL du moteur promis. La modernisation
 * peut ensuite continuer progressivement via l'etat normal de ligne sans conserver une politique
 * preview parallele. */
function OpexAI::_honorAirPreviewCommitment(line, engine, kind)
{
  if (!AIR_BEST_EQUIPMENT || line == null || !("previewCommitment" in line)
      || line.previewCommitment == null) return false;
  local commitment = line.previewCommitment;
  if (!("status" in commitment) || commitment.status != "resolved"
      || !("resolvedEngine" in commitment) || commitment.resolvedEngine != engine) return false;
  AIR_LIFECYCLE_LEDGER.previewExecuted++;
  if (DECISION_LOG) {
    OpexDecide("AIR_PREVIEW_COMMITMENT", "action=honor line=" + line.lineId
               + " kind=" + kind + " engine=" + engine);
  }
  line.previewCommitment = null;
  return true;
}
/* C34.2 : `plan` non nul = MODE A BLANC. La fonction traverse exactement les memes treize gardes
 * de refus, mais au lieu d'acheter elle enregistre ce qu'elle achererait dans `plan`, sous la forme
 * { line, want, planePrice }. C'est volontairement une reutilisation et non une extraction : les
 * gardes sont trop nombreuses et trop calibrees pour etre dupliquees sans divergence silencieuse.
 * Le portefeuille appelle ainsi la meme decision que la tache, puis l'arbitre contre les lignes
 * neuves au lieu de la servir d'office avant elles. */
function OpexAI::_resizeAirFleets(year, plan = null)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local lifecycleEvalsThisPass = 0;
  /* air_roi_order : servir la ligne qui rembourse le plus vite, pas la plus ancienne. Le tri
   * porte sur une COPIE de references : _lines garde son ordre, dont depend l'indexation de
   * _scrapDeadLines (retrait par position). */
  local airLines = [];
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode == "air") airLines.append(line);
  }
  if (AIR_ROI_ORDER) airLines.sort(OpexAirFleetPriorityCompare);
  if (AIR_BEST_EQUIPMENT) {
    /* Les invalidations ciblees et engagements preview passent avant le filet periodique : avec
     * un seul calcul economique autorise par passage, une ligne simplement due ne doit jamais
     * consommer le slot avant un evenement moteur/restauration/crash deja signale. */
    local urgent = [];
    local background = [];
    foreach (candidate in airLines) {
      local isDirty = ("airEquipmentDirty" in candidate) && candidate.airEquipmentDirty;
      local hasCommitment = ("previewCommitment" in candidate) && candidate.previewCommitment != null;
      if (isDirty || hasCommitment) urgent.append(candidate);
      else background.append(candidate);
    }
    foreach (candidate in background) urgent.append(candidate);
    airLines = urgent;
  }
  foreach (line in airLines) {
    /* B8 / G10 : une ligne en liquidation ne peut recevoir aucun appareil neuf, y compris une
     * reconstitution de crash. Ce garde doit preceder needsRefleet : pendant la fenetre de vente,
     * les avions encore vivants peuvent redevenir profitables et remettre deadStreak a zero. */
    if (("scrapping" in line) && line.scrapping) {
      OpexAirFleetRefusal(line, year, "K");
      continue;
    }
    /* AIR lifecycle : event moteur ou filet periodique ne font qu'invalider la ligne ;
     * toute l'economie reste ici, dans OpexAirAssessExistingLine -> BestEquipment/Economics. */
    if (AIR_BEST_EQUIPMENT) {
      local now = AIDate.GetCurrentDate();
      local commitmentLocksTarget = false;
      if (("previewCommitment" in line) && line.previewCommitment != null) {
        local commitment = line.previewCommitment;
        local resolvedEngine = ("resolvedEngine" in commitment) ? commitment.resolvedEngine : -1;
        if (resolvedEngine >= 0) {
          if (!AIEngine.IsValidEngine(resolvedEngine) || !AIEngine.IsBuildable(resolvedEngine)
              || !OpexAirEngineRelevantToLine(resolvedEngine, line)) {
            this._abandonAirPreviewCommitment(line, "resolved_engine_unavailable", "periodic");
            line.rawset("airEquipmentDirty", true);
            line.rawset("airEquipmentDirtyReason", "preview");
          } else if (("status" in commitment) && commitment.status == "resolved") {
            local resolvedDate = ("resolvedDate" in commitment) ? commitment.resolvedDate
                : (("acceptedDate" in commitment) ? commitment.acceptedDate : now);
            if (now - resolvedDate >= AIR_PREVIEW_COMMITMENT_MAX_DAYS) {
              this._abandonAirPreviewCommitment(line, "timeout", "periodic");
              line.rawset("airEquipmentDirty", true);
              line.rawset("airEquipmentDirtyReason", "periodic");
            } else {
              commitmentLocksTarget = true;
            }
          } else {
            /* L'identite est connue mais la cible economique n'est pas encore engagee. Le prochain
             * slot lifecycle doit passer par le moteur commun avant toute construction. */
            line.rawset("airEquipmentDirty", true);
            if (!("airEquipmentDirtyReason" in line) || line.airEquipmentDirtyReason == "") {
              line.rawset("airEquipmentDirtyReason", "preview");
            }
          }
        } else {
          local matched = OpexAirFindPreviewCommitmentEngine(this._catalog, line, commitment);
          if (matched >= 0) {
            commitment.rawset("resolvedEngine", matched);
            commitment.rawset("resolvedDate", now);
            commitment.rawset("status", "available");
            line.rawset("airEquipmentDirty", true);
            line.rawset("airEquipmentDirtyReason", "preview");
          } else {
            local acceptedDate = ("acceptedDate" in commitment) ? commitment.acceptedDate : now;
            if (now - acceptedDate >= AIR_PREVIEW_COMMITMENT_MAX_DAYS) {
              this._abandonAirPreviewCommitment(line, "timeout", "periodic");
              line.rawset("airEquipmentDirty", true);
              line.rawset("airEquipmentDirtyReason", "periodic");
            }
          }
        }
      }
      local dirty = ("airEquipmentDirty" in line) && line.airEquipmentDirty;
      /* Une invalidation rend toute la revision precedente ineligible, meme si un
       * objet project deja classe la reference encore. Le garde d'execution verifie
       * aussi la revision : effacer ici fixe la duree de vie du cache a
       * [evaluation, invalidation[. */
      if (AIR_CAPITAL_FRONTIER && dirty) OpexAirClearFrontierTransactions(line);
      local lastEval = ("lastAirEquipmentEvalDate" in line) ? line.lastAirEquipmentEvalDate : 0;
      local periodic = lastEval <= 0 || (now - lastEval) >= AIR_EQUIPMENT_REEVAL_MONTHS * 30;
      if ((dirty || periodic) && (!commitmentLocksTarget || dirty)) {
        local evalReason = dirty && ("airEquipmentDirtyReason" in line) && line.airEquipmentDirtyReason != ""
            ? line.airEquipmentDirtyReason : (dirty ? "event" : "periodic");
        if (lifecycleEvalsThisPass >= AIR_EQUIPMENT_REEVAL_MAX_PER_PASS
            || AIController.GetOpsTillSuspend() < AIR_EQUIPMENT_REEVAL_MIN_OPS) {
          AIR_LIFECYCLE_LEDGER.deferredEvaluations++;
        } else {
        lifecycleEvalsThisPass++;
        local tick0 = AIController.GetTick();
        local ops0 = AIController.GetOpsTillSuspend();
        local frontierOptions = null;
        local hasPreviewCommitment = ("previewCommitment" in line) && line.previewCommitment != null;
        local frontierReason = evalReason == "periodic" || evalReason == "engine_available"
            || evalReason == "growth" || evalReason == "upgrade" || evalReason == "event"
            || evalReason == "preview"
            || evalReason == "frontier_step" || evalReason == "frontier_stale"
            || evalReason == "frontier_failed"
            || evalReason == "restore" || evalReason == "retire_rollback";
        local useFrontierEval = AIR_CAPITAL_FRONTIER && frontierReason
            && (!("needsRefleet" in line) || !line.needsRefleet);
        local assessment = null;
        if (useFrontierEval) {
          frontierOptions = OpexAirExistingLineFrontier(this._catalog, this._lines, line, evalReason);
        } else {
          assessment = OpexAirAssessExistingLine(this._catalog, this._lines, line, evalReason);
        }
        local tick1 = AIController.GetTick();
        local ops1 = AIController.GetOpsTillSuspend();
        local evalOps = tick1 == tick0 ? ops0 - ops1
            : ops0 + (tick1 - tick0 - 1) * OPS_PER_TICK + (OPS_PER_TICK - ops1);
        if (evalOps < 0) evalOps = 0;
        AIR_LIFECYCLE_LEDGER.evaluations++;
        AIR_LIFECYCLE_LEDGER.evalOpcodes += evalOps;
        if (dirty) {
          AIR_LIFECYCLE_LEDGER.eventInvalidations++;
          AIR_LIFECYCLE_LEDGER.eventEvalOpcodes += evalOps;
          if (evalReason == "engine_available") AIR_LIFECYCLE_LEDGER.engineAvailableEvaluations++;
          else if (evalReason == "preview") AIR_LIFECYCLE_LEDGER.previewEvaluations++;
          else if (evalReason == "crash") AIR_LIFECYCLE_LEDGER.crashEvaluations++;
          else if (evalReason == "growth") AIR_LIFECYCLE_LEDGER.growthEvaluations++;
          else if (evalReason == "upgrade" || evalReason == "retire_rollback") AIR_LIFECYCLE_LEDGER.upgradeEvaluations++;
          else if (evalReason == "restore") AIR_LIFECYCLE_LEDGER.restoreEvaluations++;
        } else {
          AIR_LIFECYCLE_LEDGER.periodicEvaluations++;
          AIR_LIFECYCLE_LEDGER.periodicEvalOpcodes += evalOps;
        }
        if (useFrontierEval) {
          line.rawset("lastAirEquipmentEvalDate", now);
          line.rawset("airEquipmentDirty", false);
          line.rawset("airEquipmentDirtyReason", "");
          OpexAirStoreFrontierTransactions(line, frontierOptions, now, evalReason);
          OpexAirAppendFrontierTransactions(line, plan);
          /* Un preview n'est pas une seconde politique sous frontier. Une fois le
           * vrai EngineID connu, le moteur commun doit retrouver cet engin dans la
           * frontiere. L'engagement ne fait que suivre cette identite ; s'il n'y a
           * plus de transaction positive pour elle, il est abandonne explicitement. */
          if (hasPreviewCommitment && ("resolvedEngine" in line.previewCommitment)) {
            local resolvedEngine = line.previewCommitment.resolvedEngine;
            local previewAssessment = null;
            if (frontierOptions != null) {
              foreach (option in frontierOptions) {
                if (option.targetEngine == resolvedEngine) {
                  previewAssessment = option.assessment;
                  break;
                }
              }
            }
            if (previewAssessment != null) {
              this._resolveAirPreviewCommitment(line, resolvedEngine, previewAssessment, evalReason);
            } else {
              this._abandonAirPreviewCommitment(line, "not_preferred_by_common_engine", evalReason);
            }
          }
          if (DECISION_LOG) {
            OpexDecide("AIR_FRONTIER", "action=evaluate line=" + line.lineId
                       + " cause=" + evalReason
                       + " alternatives=" + (frontierOptions != null ? frontierOptions.len() : 0)
                       + " ops=" + evalOps);
          }
          /* Les alternatives injectees remplacent pour CETTE ligne les chemins
           * upgrade/growth historiques de la suite de la boucle. */
          continue;
        }
        if (assessment.ok) {
          OpexAirApplyLineAssessment(line, assessment);
          AIR_LIFECYCLE_LEDGER.assessmentAccepted++;
          AIR_LIFECYCLE_LEDGER.expectedGainAnnual += assessment.gainAnnual;
          AIR_LIFECYCLE_LEDGER.expectedNetCapital += assessment.netCapital;
          AIR_LIFECYCLE_LEDGER.expectedPaybackMonths += assessment.paybackMonths;
          if (assessment.upgradePending) AIR_LIFECYCLE_LEDGER.upgradePlanned++;
          if (("previewCommitment" in line) && line.previewCommitment != null
              && ("resolvedEngine" in line.previewCommitment)) {
            this._resolveAirPreviewCommitment(line, line.previewCommitment.resolvedEngine,
                                              assessment, evalReason);
          }
          if (DECISION_LOG) {
            OpexDecide("AIR_REEVAL", "cause=" + evalReason + " line=" + line.lineId
                       + " current_engine=" + assessment.currentEngine
                       + " preferred_engine=" + assessment.preferredEngine
                       + " target_fleet=" + assessment.targetFleetSize
                       + " gain=" + assessment.gainAnnual + " net_capital=" + assessment.netCapital
                       + " payback_months=" + assessment.paybackMonths
                       + " target_headway=" + assessment.targetEconomics.headwayDays.tointeger()
                       + " target_capacity=" + assessment.targetEconomics.monthlyCapacity.tointeger()
                       + " ops=" + evalOps);
          }
        } else {
          if (("previewCommitment" in line) && line.previewCommitment != null
              && ("resolvedEngine" in line.previewCommitment)) {
            this._resolveAirPreviewCommitment(line, line.previewCommitment.resolvedEngine,
                                              assessment, evalReason);
          }
          /* Un crash ne peut jamais retomber sur une cible persistee apres echec
           * de l'evaluation commune. Garder l'invalidation force une nouvelle
           * tentative au prochain slot lifecycle, sans politique de secours. */
          if (evalReason == "crash") {
            line.rawset("airEquipmentDirty", true);
            line.rawset("airEquipmentDirtyReason", "crash");
          } else {
            line.rawset("airEquipmentDirty", false);
            line.rawset("airEquipmentDirtyReason", "");
          }
          line.rawset("lastAirEquipmentEvalDate", now);
          if (DECISION_LOG) OpexDecide("AIR_REEVAL", "cause=" + evalReason + " line=" + line.lineId
                                      + " status=refuse reason=" + assessment.reason + " ops=" + evalOps);
        }
        }
      }
    }
    /* Sous la frontiere, une cible n'est jamais une autorisation durable. Si la
     * reevaluation demandee n'a pas pu s'executer (slot/opcodes), aucun ancien
     * upgrade/growth persiste ne peut passer en dessous et contourner l'election. */
    if (AIR_CAPITAL_FRONTIER && ("airEquipmentDirty" in line) && line.airEquipmentDirty) {
      OpexAirFleetRefusal(line, year, "T");
      continue;
    }
    /* Reconstitution de crash : elle passe avant les gardes de croissance
     * (have=0, profit ancien negatif, cadence), sinon le dernier avion ne peut
     * jamais redevenir un template. OpexAirRefleetCrashedPlane reconstruit les
     * ordres depuis les metadonnees durables de la ligne. */
    if (("needsRefleet" in line) && line.needsRefleet) {
      local crashEngine = -1;
      local crashLive = 0;
      if (("vehicles" in line) && line.vehicles != null) {
        foreach (v in line.vehicles) {
          if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) crashLive++;
        }
      }
      if (AIR_BEST_EQUIPMENT) {
        /* Le refleet candidat n'est autorise qu'apres reevaluation commune du
         * moteur ET de la profondeur. Un slot differe garde donc le crash en attente. */
        if (("airEquipmentDirty" in line) && line.airEquipmentDirty) {
          OpexAirFleetRefusal(line, year, "T");
          continue;
        }
        local crashTarget = ("targetFleetSize" in line) ? line.targetFleetSize : 0;
        if (crashTarget <= 0) {
          line.rawset("airEquipmentDirty", true);
          line.rawset("airEquipmentDirtyReason", "crash");
          OpexAirFleetRefusal(line, year, "T");
          continue;
        }
        /* Le crash peut suffire a atteindre une profondeur inferieure deja
         * decidee (shrink). Reconstruire ici recreerait un N+1. */
        if (crashLive >= crashTarget) {
          line.rawset("vehCount", crashLive);
          line.rawset("trains", crashLive);
          line.needsRefleet = false;
          if (AIR_CAPITAL_FRONTIER) {
            OpexAirClearFrontierTransactions(line);
            line.rawset("airEquipmentDirty", true);
            line.rawset("airEquipmentDirtyReason", "frontier_step");
          }
          if (DECISION_LOG || C52_CRASH_LOG) {
            OpexDecide("CRASH_REFLEET", "mode=air line=" + line.lineId
                       + " action=skip_target_reached live=" + crashLive
                       + " target=" + crashTarget);
          }
          continue;
        }
        if (("preferredEngine" in line) && line.preferredEngine >= 0
            && AIEngine.IsValidEngine(line.preferredEngine)
            && AIEngine.IsBuildable(line.preferredEngine)
            && OpexAirEngineRelevantToLine(line.preferredEngine, line)) {
          crashEngine = line.preferredEngine;
        } else {
          line.rawset("airEquipmentDirty", true);
          line.rawset("airEquipmentDirtyReason", "crash");
          OpexAirFleetRefusal(line, year, "T");
          continue;
        }
      }
      local recovered = OpexAirRefleetCrashedPlane(line, crashEngine);
      if (recovered.added > 0) {
        local afterCrash = crashLive + recovered.added;
        if ("vehCount" in line) line.vehCount = afterCrash;
        else line.vehCount <- afterCrash;
        if ("trains" in line) line.trains = afterCrash;
        else line.trains <- afterCrash;
        line.needsRefleet = false;
        if (AIR_BEST_EQUIPMENT) {
          /* Un crash du remplacant d'un ticket air_upgrade a ete marque par le
           * handler d'evenement. Le nouvel appareil construit reprend cette
           * identite pour empecher un faux rollback au timeout. */
          if (this._vehiclesToRetire != null && recovered.vehicle >= 0) {
            foreach (retiredVehicle, retireTicket in this._vehiclesToRetire) {
              if (typeof retireTicket != "table"
                  || !("replacementCrashed" in retireTicket) || !retireTicket.replacementCrashed
                  || !("lineId" in retireTicket) || retireTicket.lineId != line.lineId) continue;
              retireTicket.rawset("replacementVehicle", recovered.vehicle);
              retireTicket.replacementCrashed = false;
            }
          }
          line.rawset("currentPrimaryEngine", OpexAirCurrentPrimaryEngine(line));
          AIR_LIFECYCLE_LEDGER.crashExecuted++;
          if (AIR_CAPITAL_FRONTIER) {
            OpexAirClearFrontierTransactions(line);
            line.rawset("airEquipmentDirty", true);
            line.rawset("airEquipmentDirtyReason", "frontier_step");
          }
        }
        if (DECISION_LOG || C52_CRASH_LOG) {
          OpexDecide("CRASH_REFLEET", "mode=air line=" + line.lineId + " vehicle=" + line.vehicle);
        }
      } else {
        OpexAirFleetRefusal(line, year, "R");
      }
      continue;
    }
    /* Sous la nouvelle politique, une ligne propre ne retombe JAMAIS sur
     * upgradePending/targetProfitAnnual. Sa derniere frontiere reste son unique
     * representation dans le portefeuille jusqu'a invalidation. Une frontiere
     * vide est elle aussi une decision durable : elle emet zero transaction. */
    if (AIR_CAPITAL_FRONTIER) {
      if (!("airFrontierTransactions" in line) || line.airFrontierTransactions == null) {
        line.rawset("airEquipmentDirty", true);
        line.rawset("airEquipmentDirtyReason", "frontier_stale");
        OpexAirFleetRefusal(line, year, "T");
        continue;
      }
      OpexAirAppendFrontierTransactions(line, plan);
      continue;
    }
    /* C15 : Cadence d'extension de flotte aerienne.
     * Si AIR_FLEET_CADENCE_DAYS >= 365 : conservation exacte du verrou annuel historique.
     * Sinon : verrou glissant en jours depuis la derniere extension (ou la creation de la ligne). */
    if (AIR_FLEET_CADENCE_DAYS >= 365) {
      if (("lastAirFleetYear" in line) && line.lastAirFleetYear == year) { OpexAirFleetRefusal(line, year, "Y"); continue; }
    } else {
      local lastDate = ("lastAirFleetDate" in line) ? line.lastAirFleetDate : (("buildDate" in line) ? line.buildDate : 0);
      if (lastDate > 0 && (AIDate.GetCurrentDate() - lastDate) < AIR_FLEET_CADENCE_DAYS) {
        OpexAirFleetRefusal(line, year, "Y");
        continue;
      }
    }
    local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
    if (have < 1) { OpexAirFleetRefusal(line, year, "V"); continue; }
    if (("deadStreak" in line) && line.deadStreak >= 2) { OpexAirFleetRefusal(line, year, "D"); continue; }

    /* Modernisation technologique : une seule cellule de flotte par passage. Elle est prioritaire
     * sur la croissance, mais utilise le meme arbitrage portefeuille en mode a blanc. */
    if (AIR_BEST_EQUIPMENT && ("upgradePending" in line) && line.upgradePending
        && ("upgradeRemaining" in line) && line.upgradeRemaining > 0
        && ("preferredEngine" in line) && line.preferredEngine >= 0) {
      local upgradeEngine = line.preferredEngine;
      if (("previewCommitment" in line) && line.previewCommitment != null
          && ("resolvedEngine" in line.previewCommitment)) {
        if (line.previewCommitment.resolvedEngine != upgradeEngine) {
          this._abandonAirPreviewCommitment(line, "target_changed", "upgrade");
        } else if (!AIEngine.IsValidEngine(upgradeEngine) || !AIEngine.IsBuildable(upgradeEngine)
            || !OpexAirEngineRelevantToLine(upgradeEngine, line)) {
          this._abandonAirPreviewCommitment(line, "target_unavailable", "upgrade");
          line.rawset("airEquipmentDirty", true);
          line.rawset("airEquipmentDirtyReason", "upgrade");
          continue;
        }
      }
      local upgradePrice = AIEngine.IsValidEngine(upgradeEngine) ? AIEngine.GetPrice(upgradeEngine) : 0;
      if (upgradePrice > 0) {
        local upgradeTargetFleet = ("targetFleetSize" in line) ? line.targetFleetSize : 0;
        local upgradeNeedsBuild = OpexAirUpgradeStepNeedsBuild(line, upgradeEngine, upgradeTargetFleet);
        /* Fige par assessment : upgradeRemaining est un etat d'execution et ne
         * doit pas rendre artificiellement chaque cellule suivante plus rentable. */
        local unitGain = ("upgradeUnitGainAnnual" in line) ? line.upgradeUnitGainAnnual : 0;
        if (unitGain < 1) unitGain = 1;
        if (plan != null) {
          plan.append({
            kind = "upgrade", line = line, want = 1, targetEngine = upgradeEngine,
            targetFleetSize = upgradeTargetFleet, retireOnly = !upgradeNeedsBuild,
            planePrice = upgradePrice, profitAnnual = unitGain,
            netCapital = ("upgradeNetCapital" in line) ? line.upgradeNetCapital : upgradePrice,
            paybackMonths = ("upgradePaybackMonths" in line) ? line.upgradePaybackMonths : 0,
          });
          AIR_LIFECYCLE_LEDGER.upgradePlanned++;
          continue;
        }
        if (upgradeNeedsBuild) {
          local upgradeNeed = upgradePrice + OpexCashReserve();
          local upgradeMoney = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          if (upgradeMoney < upgradeNeed && REBORROW) upgradeMoney = OpexTryReborrow(upgradeNeed, upgradeMoney);
          if (upgradeMoney < upgradeNeed) { OpexAirFleetRefusal(line, year, "M"); continue; }
        }
        local upgraded = OpexAirUpgradeOnePlane(line, upgradeEngine, upgradeTargetFleet);
        if (upgraded.retireOnly && this._queueAirRetirement(line, upgraded.oldVehicle,
                                                             "air_upgrade_shrink")) {
          line.upgradeRemaining--;
          if (line.upgradeRemaining <= 0) {
            line.upgradePending = false;
            if (AIEngine.IsValidEngine(upgradeEngine)) line.rawset("planeCapacity", AIEngine.GetCapacity(upgradeEngine));
          }
          line.rawset("currentPrimaryEngine", OpexAirCurrentPrimaryEngine(line));
          line.rawset("lastAirFleetYear", year);
          line.rawset("lastAirFleetDate", AIDate.GetCurrentDate());
          AIR_LIFECYCLE_LEDGER.upgradeExecuted++;
          if (DECISION_LOG) OpexDecide("AIR_LIFECYCLE", "action=upgrade_retire line=" + line.lineId
                                      + " engine=" + upgradeEngine + " remaining=" + line.upgradeRemaining);
        } else if (upgraded.added > 0 && this._queueAirRetirement(line, upgraded.oldVehicle, "air_upgrade",
                                                                  upgraded.newVehicle)) {
          line.upgradeRemaining--;
          if (line.upgradeRemaining <= 0) {
            line.upgradePending = false;
            if (AIEngine.IsValidEngine(upgradeEngine)) line.rawset("planeCapacity", AIEngine.GetCapacity(upgradeEngine));
          }
          line.rawset("currentPrimaryEngine", OpexAirCurrentPrimaryEngine(line));
          line.rawset("lastAirFleetYear", year);
          line.rawset("lastAirFleetDate", AIDate.GetCurrentDate());
          AIR_LIFECYCLE_LEDGER.upgradeExecuted++;
          this._honorAirPreviewCommitment(line, upgradeEngine, "upgrade");
          if (DECISION_LOG) OpexDecide("AIR_LIFECYCLE", "action=upgrade line=" + line.lineId
                                      + " engine=" + upgradeEngine + " remaining=" + line.upgradeRemaining
                                      + " gain=" + unitGain);
        } else {
          if (upgraded.added > 0 && AIVehicle.IsValidVehicle(upgraded.newVehicle)) {
            if (this._queueAirRetirement(line, upgraded.newVehicle, "air_upgrade_rollback")) {
              AIR_LIFECYCLE_LEDGER.retireRollback++;
            }
          }
          OpexAirFleetRefusal(line, year, "X");
        }
      }
      continue;
    }

    /* La rentabilite realisee bloque la CROISSANCE, pas une modernisation deja justifiee par le
     * moteur economique commun. Une technologie meilleure doit pouvoir reparer une ligne en recul. */
    if (("lastProfit" in line) && line.lastProfit < 0) { OpexAirFleetRefusal(line, year, "L"); continue; }

    /* marginal_fleet = 1 (2026-09-01) : dimensionnement marginal STRICT de l'air. Le commentaire
     * de cette fonction promettait deja d'attendre un an, d'exiger une charge complete en attente
     * et de ne jamais ajouter plus d'un avion par an -- mais rien ci-dessus ni ci-dessous ne
     * verifiait l'age de la ligne ou le fret en attente, et la boucle plus bas autorisait jusqu'a
     * 4 avions en un seul passage (addedThisPass < 4). Sous 0 (defaut), ce bloc ne change RIEN :
     * il ajoute seulement des refus supplementaires, jamais un chemin different pour les
     * conditions deja verifiees plus haut (have, deadStreak, lastProfit < 0). */
    if (MARGINAL_FLEET && AIR_FLEET_BUFFER < 0) {
      // (a) la ligne a au moins un an d'existence revolu
      if (!("year" in line) || (year - line.year) < 1) continue;
      // (b) lastProfit disponible ET strictement positif (pas seulement "pas negatif")
      if (!("lastProfit" in line) || line.lastProfit <= 0) continue;
      // (c) au moins une capacite complete d'avion attend REELLEMENT dans une des deux gares
      local planeCap = ("planeCapacity" in line && line.planeCapacity > 0) ? line.planeCapacity : 0;
      if (planeCap <= 0) continue;
      /* Pas de AIStation.STATION_INVALID ici : jamais utilise ailleurs dans ce projet, on prefere
       * garder le meme garde-fou "hasB" que le reste du fichier (cf. lastWaitingB plus haut). */
      local stA = AIStation.GetStationID(line.stationA);
      local hasB = ("stationB" in line) && line.stationB != null;
      local stB = hasB ? AIStation.GetStationID(line.stationB) : 0;
      local waitA = AIStation.IsValidStation(stA) ? AIStation.GetCargoWaiting(stA, line.cargo) : 0;
      local waitB = (hasB && AIStation.IsValidStation(stB)) ? AIStation.GetCargoWaiting(stB, line.cargo) : 0;
      if (waitA < planeCap && waitB < planeCap) continue;
    }

    local isSmallAirport = false;
    if ((AIAirport.IsAirportTile(line.stationA) && AIAirport.GetAirportType(line.stationA) == AIAirport.AT_SMALL) ||
        (AIAirport.IsAirportTile(line.stationB) && AIAirport.GetAirportType(line.stationB) == AIAirport.AT_SMALL)) {
      isSmallAirport = true;
    }
    local physicalMaxPlanes = isSmallAirport ? 4 : AIR_MAX_PLANES_PER_ROUTE;
    if (AIR_CADENCE_CAP) {
      physicalMaxPlanes = OpexAirCadenceCap(line, this._catalog, this._lines);
    }
    local maxPlanesForAirport = physicalMaxPlanes;
    if (have >= physicalMaxPlanes) { OpexAirFleetRefusal(line, year, "C"); continue; }
    if (AIR_DEMAND_CAP) {
      local demand = OpexAirDemandCap(line, this._catalog, this._lines);
      if (demand.cap < maxPlanesForAirport) maxPlanesForAirport = demand.cap;
      if (DECISION_LOG) {
        OpexDecide("AIR_DEMAND_CAP", "line=" + line.lineId + " cap=" + demand.cap
                   + " monthly_demand=" + demand.monthlyDemand
                   + " capacity_per_plane=" + demand.capacityPerPlane
                   + " routes_a=" + demand.routesA + " routes_b=" + demand.routesB
                   + " planes=" + have + " physical_cap=" + physicalMaxPlanes
                   + " applied_cap=" + maxPlanesForAirport);
      }
      if (have >= maxPlanesForAirport) { OpexAirFleetRefusal(line, year, "Q"); continue; }
    }
    if (AIR_BEST_EQUIPMENT && ("targetFleetSize" in line) && line.targetFleetSize > 0) {
      if (line.targetFleetSize < maxPlanesForAirport) maxPlanesForAirport = line.targetFleetSize;
      if (have >= maxPlanesForAirport) { OpexAirFleetRefusal(line, year, "Q"); continue; }
    }
    if (("deadStreak" in line) && line.deadStreak >= 1) { OpexAirFleetRefusal(line, year, "S"); continue; }
    if (("lastProfit" in line) && line.lastProfit < 0) { OpexAirFleetRefusal(line, year, "L"); continue; }

    /* fleet_fix : cette garde pricait le MEILLEUR avion du catalogue, alors qu'OpexAirAddPlane
     * clone le gabarit de LA LIGNE (builder_air.nut:224, prix lu sur l'engin du vehicule existant).
     * Une ligne a helices desservant un petit aeroport, face a un catalogue passe au gros jet,
     * voyait donc `need` plusieurs fois trop grand : `money < need` -> break, et une ligne
     * rentable ne grandissait jamais alors que la tresorerie etait la. La garde interne
     * d'OpexAirAddPlane etant correcte, celle-ci ne produisait que des FAUX NEGATIFS
     * (docs/taches.md S0 nonies). On price desormais l'avion qu'on va reellement acheter. */
    local growthEngine = -1;
    local planePrice = 30000;
    if (AIR_BEST_EQUIPMENT) {
      if (("preferredEngine" in line) && line.preferredEngine >= 0
          && AIEngine.IsValidEngine(line.preferredEngine) && AIEngine.IsBuildable(line.preferredEngine)
          && OpexAirEngineRelevantToLine(line.preferredEngine, line)) {
        growthEngine = line.preferredEngine;
        planePrice = AIEngine.GetPrice(growthEngine);
      } else {
        line.rawset("airEquipmentDirty", true);
        line.rawset("airEquipmentDirtyReason", "growth");
        OpexAirFleetRefusal(line, year, "T");
        continue;
      }
    } else {
      planePrice = (this._catalog.plane != null) ? this._catalog.plane.price : 30000;
    }
    if (!AIR_BEST_EQUIPMENT && (FLEET_FIX || AIR_FLEET_LINE_PRICE) && ("vehicles" in line)) {
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
    local need = planePrice + OpexCashReserve() + (AIR_MARGIN_V2 ? 0 : 2000);
    local addedThisPass = 0;
    // (d) au plus un avion par ligne et par an sous marginal_fleet=1 ; 4 (repli actuel) sous 0.
    local maxAddedPerPass = MARGINAL_FLEET ? 1 : 4;
    /* C14 : Dimensionnement dynamique de flotte par le stock au sol (AAAHogEx route.nut:2896-2921).
     * Si AIR_FLEET_BUFFER >= 0 : calcule buildNum = (maxWait - bottom) / capacity.
     * Si buildNum < 1 : refus W (pas assez de cargo au sol).
     * Sinon : autorise jusqu'a min(buildNum, 4) avions dans ce passage. */
    if (AIR_FLEET_BUFFER >= 0) {
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
        OpexAirFleetRefusal(line, year, "W");
        continue;
      }
      maxAddedPerPass = (buildNum < 4) ? buildNum : 4;
    }
    if (plan != null) {
      /* Mode a blanc : on ne touche ni a la tresorerie ni a la ligne. Le test de capital est celui
       * du portefeuille, pas celui d'ici -- c'est tout l'objet de l'arbitrage. */
      local room = maxPlanesForAirport - have;
      local want = (room < maxAddedPerPass) ? room : maxAddedPerPass;
      if (want > 0) {
        local growthGain = 0;
        if (AIR_BEST_EQUIPMENT && ("targetProfitAnnual" in line)) {
          local currentModel = ("currentModelProfitAnnual" in line) ? line.currentModelProfitAnnual
              : (("predicted" in line) ? line.predicted : 0);
          local totalGain = line.targetProfitAnnual - currentModel;
          local totalRoom = maxPlanesForAirport - have;
          if (totalRoom > 0) growthGain = totalGain / totalRoom;
        }
        plan.append({ line = line, want = want, planePrice = planePrice,
                      kind = AIR_BEST_EQUIPMENT ? "growth" : "legacy",
                      targetEngine = growthEngine, profitAnnual = growthGain });
        if (AIR_BEST_EQUIPMENT) AIR_LIFECYCLE_LEDGER.growthPlanned += want;
        if (C50_CHRONOLOGY_PROBE && C50_NON_EXPANSION_LEDGER != null) {
          local ym = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
          if (!("c50_want_ym" in line) || line.c50_want_ym != ym) {
            line.c50_want_ym <- ym;
            C50_NON_EXPANSION_LEDGER.air.want_sum += want;
          }
        }
      }
      continue;
    }
    while (have < maxPlanesForAirport && addedThisPass < maxAddedPerPass) {
      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) { OpexAirFleetRefusal(line, year, "M"); break; }
      local grown = OpexAirAddPlane(line, AIR_BEST_EQUIPMENT ? growthEngine : -1);
      if (grown.added <= 0) { OpexAirFleetRefusal(line, year, "X"); break; }
      have += grown.added;
      addedThisPass += grown.added;
      line.vehCount <- have;
      line.trains = have;
    }
    if (addedThisPass > 0) {
      if (AIR_BEST_EQUIPMENT) {
        AIR_LIFECYCLE_LEDGER.growthExecuted += addedThisPass;
        line.rawset("currentPrimaryEngine", OpexAirCurrentPrimaryEngine(line));
        this._honorAirPreviewCommitment(line, growthEngine, "growth");
      }
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
  if (AIR_BEST_EQUIPMENT) {
    local paretoRaw = (this._catalog != null && ("airParetoStats" in this._catalog)
        && this._catalog.airParetoStats != null) ? this._catalog.airParetoStats.raw : 0;
    local paretoKept = (this._catalog != null && ("airParetoStats" in this._catalog)
        && this._catalog.airParetoStats != null) ? this._catalog.airParetoStats.kept : 0;
    local paretoPruned = (this._catalog != null && ("airParetoStats" in this._catalog)
        && this._catalog.airParetoStats != null) ? this._catalog.airParetoStats.pruned : 0;
    OpexSign(AIMap.GetTileIndex(2, 9), "AL0|" + AIR_LIFECYCLE_LEDGER.evaluations + "|"
             + AIR_LIFECYCLE_LEDGER.assessmentAccepted + "|" + AIR_LIFECYCLE_LEDGER.periodicEvaluations + "|"
             + AIR_LIFECYCLE_LEDGER.deferredEvaluations);
    OpexSign(AIMap.GetTileIndex(3, 9), "AL1|" + AIR_LIFECYCLE_LEDGER.eventInvalidations + "|"
             + AIR_LIFECYCLE_LEDGER.engineAvailableEvents + "|" + AIR_LIFECYCLE_LEDGER.engineAvailableAffected + "|"
             + (AIR_LIFECYCLE_LEDGER.evalOpcodes / 1000));
    OpexSign(AIMap.GetTileIndex(4, 9), "AL2|" + AIR_LIFECYCLE_LEDGER.growthPlanned + "|"
             + AIR_LIFECYCLE_LEDGER.growthExecuted + "|" + AIR_LIFECYCLE_LEDGER.upgradePlanned + "|"
             + AIR_LIFECYCLE_LEDGER.upgradeExecuted);
    OpexSign(AIMap.GetTileIndex(5, 9), "AL3|" + AIR_LIFECYCLE_LEDGER.crashExecuted + "|"
             + AIR_LIFECYCLE_LEDGER.previewSeen + "|" + AIR_LIFECYCLE_LEDGER.previewAccepted + "|"
             + AIR_LIFECYCLE_LEDGER.previewMatched);
    OpexSign(AIMap.GetTileIndex(6, 9), "AL4|" + AIR_LIFECYCLE_LEDGER.previewExecuted + "|"
             + AIR_LIFECYCLE_LEDGER.previewAbandoned + "|" + AIR_LIFECYCLE_LEDGER.retireQueued + "|"
             + AIR_LIFECYCLE_LEDGER.retireRollback);
    OpexSign(AIMap.GetTileIndex(7, 9), "AL5|" + (AIR_LIFECYCLE_LEDGER.expectedGainAnnual / 1000) + "|"
             + (AIR_LIFECYCLE_LEDGER.expectedNetCapital / 1000) + "|"
             + AIR_LIFECYCLE_LEDGER.expectedPaybackMonths);
    OpexSign(AIMap.GetTileIndex(8, 9), "AL6|" + (AIR_LIFECYCLE_LEDGER.eventEvalOpcodes / 1000) + "|"
             + (AIR_LIFECYCLE_LEDGER.periodicEvalOpcodes / 1000) + "|"
             + (AIR_LIFECYCLE_LEDGER.engineEventOpcodes / 1000) + "|"
             + (AIR_LIFECYCLE_LEDGER.previewOpcodes / 1000));
    OpexSign(AIMap.GetTileIndex(9, 8), "AL7|" + AIR_LIFECYCLE_LEDGER.previewIdResolved + "|"
             + AIR_LIFECYCLE_LEDGER.previewIdMiss + "|" + AIR_LIFECYCLE_LEDGER.previewAbandonCommon + "|"
             + AIR_LIFECYCLE_LEDGER.previewAbandonTimeout);
    OpexSign(AIMap.GetTileIndex(10, 8), "AL8|" + AIR_LIFECYCLE_LEDGER.engineAvailableEvaluations + "|"
             + AIR_LIFECYCLE_LEDGER.previewEvaluations + "|" + AIR_LIFECYCLE_LEDGER.crashEvaluations + "|"
             + AIR_LIFECYCLE_LEDGER.growthEvaluations);
    OpexSign(AIMap.GetTileIndex(11, 8), "AL9|" + AIR_LIFECYCLE_LEDGER.upgradeEvaluations + "|"
             + AIR_LIFECYCLE_LEDGER.restoreEvaluations);
    OpexSign(AIMap.GetTileIndex(9, 9), "AQ|" + paretoRaw + "|" + paretoKept + "|" + paretoPruned);
    if (AIR_CAPITAL_FRONTIER_PROBE) {
      OpexSign(AIMap.GetTileIndex(12, 8), "CF0|" + AIR_CAPITAL_FRONTIER_LEDGER.routeRaw + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.routeKept + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.lifecycleRaw + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.lifecycleKept);
      OpexSign(AIMap.GetTileIndex(13, 8), "CF1|" + AIR_CAPITAL_FRONTIER_LEDGER.selected + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.replaceSelected + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growSelected + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.retireSelected);
      // CF2/CF4 gardent un zero reserve pour le format des anciens diagnostics.
      OpexSign(AIMap.GetTileIndex(14, 8), "CF2|" + AIR_CAPITAL_FRONTIER_LEDGER.staleRejected + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.cashRejected + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.failedRejected + "|"
               + 0);
      OpexSign(AIMap.GetTileIndex(15, 8), "CF3|" + AIR_CAPITAL_FRONTIER_LEDGER.portfolioRaw + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.portfolioAffordable + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.portfolioTopSelections + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.portfolioTopAirSelections);
      OpexSign(AIMap.GetTileIndex(16, 8), "CF4|"
               + 0 + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.portfolioTopCapital / 1000) + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.portfolioTopProfit / 1000));
      OpexSign(AIMap.GetTileIndex(24, 8), "CF12|"
               + AIR_CAPITAL_FRONTIER_LEDGER.assignCalls + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.assignExternalityOps + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.assignBuildOps + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.assignScoreOps);
      OpexSign(AIMap.GetTileIndex(27, 8), "CF15|"
               + AIR_CAPITAL_FRONTIER_LEDGER.capitalPriceSamples + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.capitalPricePositiveSamples + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.capitalPriceBpsSum + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.capitalPriceBpsMax + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.capitalPriceFullDemandK + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.capitalPriceBudgetK);
    }
    if (AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT) {
      OpexSign(AIMap.GetTileIndex(28, 8), "CF16|"
               + AIR_SELECTION_LEDGER.calls + "|" + AIR_SELECTION_LEDGER.productionCalls + "|"
               + AIR_SELECTION_LEDGER.diagnosticCalls + "|"
               + AIR_SELECTION_LEDGER.diagnosticCounterfactualCalls);
      OpexSign(AIMap.GetTileIndex(29, 8), "CF17|"
               + AIR_SELECTION_LEDGER.generationCalls + "|"
               + AIR_SELECTION_LEDGER.lifecycleCalls + "|"
               + AIR_SELECTION_LEDGER.budgetReselectCalls + "|"
               + AIR_SELECTION_LEDGER.dynamicBatchCalls + "|"
               + AIR_SELECTION_LEDGER.executionCalls);
      OpexSign(AIMap.GetTileIndex(30, 8), "CF18|"
               + AIR_SELECTION_LEDGER.productionOps + "|" + AIR_SELECTION_LEDGER.productionDays + "|"
               + AIR_SELECTION_LEDGER.diagnosticOps + "|" + AIR_SELECTION_LEDGER.diagnosticDays);
      OpexSign(AIMap.GetTileIndex(31, 8), "CF19|"
               + AIR_SELECTION_LEDGER.externalityOps + "|"
               + AIR_SELECTION_LEDGER.relaxationOps + "|"
               + AIR_SELECTION_LEDGER.rankingOps);
      OpexSign(AIMap.GetTileIndex(32, 8), "CF20|"
               + AIR_SELECTION_LEDGER.externalityDays + "|"
               + AIR_SELECTION_LEDGER.relaxationDays + "|"
               + AIR_SELECTION_LEDGER.rankingDays);
      OpexSign(AIMap.GetTileIndex(33, 8), "CF21|"
               + AIR_SELECTION_LEDGER.prepareOps + "|" + AIR_SELECTION_LEDGER.prepareDays + "|"
               + AIR_SELECTION_LEDGER.preparedBuilds + "|" + AIR_SELECTION_LEDGER.preparedHits);
      OpexSign(AIMap.GetTileIndex(34, 8), "CF22|"
               + AIR_SELECTION_LEDGER.envelopeBuilds + "|" + AIR_SELECTION_LEDGER.envelopeHits + "|"
               + AIR_SELECTION_LEDGER.externalityCacheHits);
      OpexSign(AIMap.GetTileIndex(35, 8), "CF23|"
               + AIR_SELECTION_LEDGER.diagnosticPrepareOps + "|"
               + AIR_SELECTION_LEDGER.diagnosticExternalityOps + "|"
               + AIR_SELECTION_LEDGER.diagnosticRelaxationOps + "|"
               + AIR_SELECTION_LEDGER.diagnosticRankingOps);
      OpexSign(AIMap.GetTileIndex(36, 8), "CF24|"
               + AIR_SELECTION_LEDGER.diagnosticPrepareDays + "|"
               + AIR_SELECTION_LEDGER.diagnosticExternalityDays + "|"
               + AIR_SELECTION_LEDGER.diagnosticRelaxationDays + "|"
               + AIR_SELECTION_LEDGER.diagnosticRankingDays);
      /* TEMP_GROW_COMPARE_BEGIN: repurpose CF25..27 for one diagnostic run. */
      OpexSign(AIMap.GetTileIndex(37, 8), "CF25|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growCompareSamples + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopAir + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowProfit / 1000) + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowCapital / 1000));
      OpexSign(AIMap.GetTileIndex(38, 8), "CF26|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowScore / 1000) + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopProfit / 1000) + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopCapital / 1000));
      OpexSign(AIMap.GetTileIndex(39, 8), "CF27|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopScore / 1000) + "|0|"
               + AIR_SELECTION_LEDGER.coverMissing + "|" + AIR_SELECTION_LEDGER.coverBudgetBelow + "|"
               + AIR_SELECTION_LEDGER.coverBudgetAbove + "|"
               + AIR_SELECTION_LEDGER.coverRawStateMismatch + "|"
               + AIR_SELECTION_LEDGER.coverSemanticHits + "|"
               + AIR_SELECTION_LEDGER.coverStateMismatch);
      /* TEMP_GROW_COMPARE_END */
    }
  }
  return true;
}
