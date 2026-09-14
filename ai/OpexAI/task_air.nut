/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* C56 follow-up: only airport placement failures identify a bad physical site.
 * A plane/order/cash failure must not poison either endpoint. */
function OpexAI::_markAirFailedSites(plan, result)
{
  if (!AIR_ABANDON_SITE || plan == null || result == null || !("reason" in result)) return;
  if (!("airport" in plan) || plan.airport == null || !("error" in result)) return;
  /* Only terrain failures survive a different route, date or town rating. */
  if (result.error != AIError.ERR_FLAT_LAND_REQUIRED
      && result.error != AIError.ERR_LAND_SLOPED_WRONG
      && result.error != AIError.ERR_AREA_NOT_CLEAR
      && result.error != AIError.ERR_SITE_UNSUITABLE) return;
  local reason = result.reason;
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
      if (builtCount > 0) {
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
      if (ABANDON_MEMORY && ((abandonedKey in this._abandonedPairs)
          || (AIR_ABANDON_SITE && ((abandonedSiteA in this._abandonedPairs)
              || (abandonedSiteB in this._abandonedPairs))))) {
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "abandoned_pair", extra = "" });
        return { outcome = "rejected", discards = passDiscards };
      }

      local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1) + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
      local requiredMargin = AIR_MARGIN_V2
          ? ((newAirports == 2) ? 15000 : (newAirports == 1 ? 6000 : 0))
          : ((newAirports == 2) ? 30000 : (newAirports == 1 ? 12000 : 2000));
      local capital = ("capital" in plan) ? plan.capital : (newAirports * plan.airport.price + plan.plane.price);
      local need = capital + OpexCashReserve() + requiredMargin;
      if (money < need && REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        if (C50_CHRONOLOGY_PROBE) this._logC50CashRefusal("air", i, capital, plan.economics.profitAnnual, project.roi, plan.siteA.town.tile, plan.siteB.town.tile, need, money);
        if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
        return { outcome = "rejected", discards = passDiscards };
      }

      OpexSign(anchor, "IP|" + yy + "|A|" + project.budgetScore + "|" + project.opcodeScore);

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
        if (C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL) passDiscards.append({ rank = i, mode = "air", src = plan.siteA.town.tile, dst = plan.siteB.town.tile, reason = "build_failed", extra = "" });
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
 * S un an de mauvaise sante, M tresorerie, X l'achat a echoue. */
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
/* Comparateur de tete de file pour la croissance aerienne : meilleur rendement d'abord.
 * Fonction NOMMEE au niveau module, comme OpexFeederCandidateCompare : dans cet environnement
 * Squirrel une closure imbriquee ne capture jamais les locales englobantes. */
function OpexAirFleetPriorityCompare(a, b)
{
  local ya = OpexAirFleetYield(a);
  local yb = OpexAirFleetYield(b);
  if (ya > yb) return -1;
  if (ya < yb) return 1;
  return 0;
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
  /* air_roi_order : servir la ligne qui rembourse le plus vite, pas la plus ancienne. Le tri
   * porte sur une COPIE de references : _lines garde son ordre, dont depend l'indexation de
   * _scrapDeadLines (retrait par position). */
  local airLines = [];
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode == "air") airLines.append(line);
  }
  if (AIR_ROI_ORDER) airLines.sort(OpexAirFleetPriorityCompare);
  foreach (line in airLines) {
    /* Reconstitution de crash : elle passe avant les gardes de croissance
     * (have=0, profit ancien negatif, cadence), sinon le dernier avion ne peut
     * jamais redevenir un template. OpexAirRefleetCrashedPlane reconstruit les
     * ordres depuis les metadonnees durables de la ligne. */
    if (("needsRefleet" in line) && line.needsRefleet) {
      local recovered = OpexAirRefleetCrashedPlane(line);
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
      } else {
        OpexAirFleetRefusal(line, year, "R");
      }
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

    // Condition 1 : Les appareils existants ne doivent pas etre deficitaires
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
    if (("deadStreak" in line) && line.deadStreak >= 1) { OpexAirFleetRefusal(line, year, "S"); continue; }
    if (("lastProfit" in line) && line.lastProfit < 0) { OpexAirFleetRefusal(line, year, "L"); continue; }

    /* fleet_fix : cette garde pricait le MEILLEUR avion du catalogue, alors qu'OpexAirAddPlane
     * clone le gabarit de LA LIGNE (builder_air.nut:224, prix lu sur l'engin du vehicule existant).
     * Une ligne a helices desservant un petit aeroport, face a un catalogue passe au gros jet,
     * voyait donc `need` plusieurs fois trop grand : `money < need` -> break, et une ligne
     * rentable ne grandissait jamais alors que la tresorerie etait la. La garde interne
     * d'OpexAirAddPlane etant correcte, celle-ci ne produisait que des FAUX NEGATIFS
     * (docs/taches.md S0 nonies). On price desormais l'avion qu'on va reellement acheter. */
    local planePrice = (this._catalog.plane != null) ? this._catalog.plane.price : 30000;
    if ((FLEET_FIX || AIR_FLEET_LINE_PRICE) && ("vehicles" in line)) {
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
        plan.append({ line = line, want = want, planePrice = planePrice });
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
      local grown = OpexAirAddPlane(line);
      if (grown.added <= 0) { OpexAirFleetRefusal(line, year, "X"); break; }
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
  return true;
}
