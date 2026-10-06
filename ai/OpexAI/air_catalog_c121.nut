/* Module AIR extrait de builder_air.nut (R11) : catalogue incremental C121, rejeu et mesures construites. */
/* Le cache est indexe sur la geometrie physique, jamais sur l'ordre du tableau de sites.
 * Les objets economics restent immuables jusqu'a leur copie dans le plan candidat. */
function OpexC121CatalogSiteKey(site)
{
  return site.town.id + ":" + site.anchor + ":"
      + (("stationId" in site) ? site.stationId : -1);
}

/* C76 ne donne que le nom de couche. Comparer les empreintes des stations AIR
 * une fois au bump permet de garder les plans sans lien avec la ligne modifiee. */
function OpexC121CatalogRefreshStationLines(lines)
{
  local nextLines = {};
  local changed = false;
  if (lines != null) foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air"
        || !("stationA" in line) || !("stationB" in line)) continue;
    local a = OpexAirLineStationId(line, 0);
    local b = OpexAirLineStationId(line, 1);
    if (a >= 0) nextLines.rawset(a,
        (a in nextLines ? nextLines[a] : "") + b + ";");
    if (b >= 0) nextLines.rawset(b,
        (b in nextLines ? nextLines[b] : "") + a + ";");
  }
  foreach (stationId, signature in nextLines) {
    if (!(stationId in C121_CATALOG_STATION_LINES)
        || C121_CATALOG_STATION_LINES[stationId] != signature) {
      changed = true;
      C121_CATALOG_STATION_REV.rawset(stationId,
          (stationId in C121_CATALOG_STATION_REV
              ? C121_CATALOG_STATION_REV[stationId] : 0) + 1);
    }
  }
  foreach (stationId, signature in C121_CATALOG_STATION_LINES) {
    if (!(stationId in nextLines)) {
      changed = true;
      C121_CATALOG_STATION_REV.rawset(stationId,
        (stationId in C121_CATALOG_STATION_REV
            ? C121_CATALOG_STATION_REV[stationId] : 0) + 1);
    }
  }
  C121_CATALOG_STATION_LINES = nextLines;
  /* Une autre gare peut concurrencer le catchment de cette extremite.
   * Invalider le cache enfant, pas tous les choix du catalogue parent. */
  if (changed) OpexC121InvalidateEndpointGeometry();
}

function OpexC121CatalogTownPriorityCompare(a, b)
{
  local scoreA = a.id in C121_CATALOG_TOWN_PRIORITY ? C121_CATALOG_TOWN_PRIORITY[a.id] : -1.0;
  local scoreB = b.id in C121_CATALOG_TOWN_PRIORITY ? C121_CATALOG_TOWN_PRIORITY[b.id] : -1.0;
  if (scoreA > scoreB) return -1;
  if (scoreA < scoreB) return 1;
  if (a.pop > b.pop) return -1;
  if (a.pop < b.pop) return 1;
  return a.id < b.id ? -1 : (a.id > b.id ? 1 : 0);
}

function OpexC121CatalogRankDirtyTowns()
{
  C121_CATALOG_TOWN_PRIORITY.clear();
  local today = AIDate.GetCurrentDate();
  foreach (key, entry in C121_CATALOG_CACHE) {
    local dirty = entry.airportRev != (entry.airportType in C121_CATALOG_AIRPORT_REV
        ? C121_CATALOG_AIRPORT_REV[entry.airportType] : 0)
        || entry.townA != (entry.townAId in C121_CATALOG_TOWN_REV
            ? C121_CATALOG_TOWN_REV[entry.townAId] : 0)
        || entry.townB != (entry.townBId in C121_CATALOG_TOWN_REV
            ? C121_CATALOG_TOWN_REV[entry.townBId] : 0)
        || entry.stationRevA != (entry.stationAId in C121_CATALOG_STATION_REV
            ? C121_CATALOG_STATION_REV[entry.stationAId] : 0)
        || entry.stationRevB != (entry.stationBId in C121_CATALOG_STATION_REV
            ? C121_CATALOG_STATION_REV[entry.stationBId] : 0)
        || entry.airportLearn != (entry.airportType in C121_CATALOG_AIRPORT_LEARN_REV
            ? C121_CATALOG_AIRPORT_LEARN_REV[entry.airportType] : 0)
        || entry.hubLearnA != (entry.stationAId in C121_CATALOG_HUB_LEARN_REV
            ? C121_CATALOG_HUB_LEARN_REV[entry.stationAId] : 0)
        || entry.hubLearnB != (entry.stationBId in C121_CATALOG_HUB_LEARN_REV
            ? C121_CATALOG_HUB_LEARN_REV[entry.stationBId] : 0)
        || entry.armLearn != (entry.arm in C121_CATALOG_ARM_LEARN_REV
            ? C121_CATALOG_ARM_LEARN_REV[entry.arm] : 0)
        || today - entry.date >= 365;
    if (!dirty) continue;
    local score = entry.lastScore;
    if (!(entry.townAId in C121_CATALOG_TOWN_PRIORITY)
        || C121_CATALOG_TOWN_PRIORITY[entry.townAId] < score)
      C121_CATALOG_TOWN_PRIORITY.rawset(entry.townAId, score);
    if (!(entry.townBId in C121_CATALOG_TOWN_PRIORITY)
        || C121_CATALOG_TOWN_PRIORITY[entry.townBId] < score)
      C121_CATALOG_TOWN_PRIORITY.rawset(entry.townBId, score);
  }
}

/* Le snapshot appartient a une election. Ne jamais recalculer une moitie
 * avec les services/invariants de l'election precedente sur le meme objet. */
function OpexC121CatalogClearPlanSnapshot(plan)
{
  foreach (field in ["c121Demand", "c121ServiceA", "c121ServiceB",
      "c121EngineStatic", "b9ShadowMonthly", "c121ChosenEngine", "c121ChosenMailKnown",
      "c121DemandTicks", "c121DemandOps", "c121EngineStaticTicks", "c121EngineStaticOps",
      "c121EngineScanTicks", "c121EngineScanOps", "c121EngineEvalCount",
      "c121EngineKnownCount", "c121EngineEvalOpsTotal", "c121EngineEvalOpsSameTick",
      "c121EngineEvalSameTickCount", "c121WinnerFullTicks", "c121WinnerFullOps"]) {
    if (field in plan) delete plan[field];
  }
}

function OpexC121CatalogChoice(catalog, plan, lines)
{
  local cacheMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  local key = plan.arm + "|" + plan.airport.type + "|"
      + OpexC121CatalogSiteKey(plan.siteA) + "|"
      + OpexC121CatalogSiteKey(plan.siteB) + "|"
      + (plan.reuseA ? 1 : 0) + "|" + (plan.reuseB ? 1 : 0);
  plan.c121CatalogKey <- key;
  local date = AIDate.GetCurrentDate();
  local revA = plan.siteA.town.id in C121_CATALOG_TOWN_REV
      ? C121_CATALOG_TOWN_REV[plan.siteA.town.id] : 0;
  local revB = plan.siteB.town.id in C121_CATALOG_TOWN_REV
      ? C121_CATALOG_TOWN_REV[plan.siteB.town.id] : 0;
  local airportRev = plan.airport.type in C121_CATALOG_AIRPORT_REV
      ? C121_CATALOG_AIRPORT_REV[plan.airport.type] : 0;
  local airportLearn = plan.airport.type in C121_CATALOG_AIRPORT_LEARN_REV
      ? C121_CATALOG_AIRPORT_LEARN_REV[plan.airport.type] : 0;
  local stationA = OpexC121HubStationId(plan.siteA, plan.reuseA);
  local stationB = OpexC121HubStationId(plan.siteB, plan.reuseB);
  local stationRevA = stationA in C121_CATALOG_STATION_REV
      ? C121_CATALOG_STATION_REV[stationA] : 0;
  local stationRevB = stationB in C121_CATALOG_STATION_REV
      ? C121_CATALOG_STATION_REV[stationB] : 0;
  local hubLearnA = stationA in C121_CATALOG_HUB_LEARN_REV
      ? C121_CATALOG_HUB_LEARN_REV[stationA] : 0;
  local hubLearnB = stationB in C121_CATALOG_HUB_LEARN_REV
      ? C121_CATALOG_HUB_LEARN_REV[stationB] : 0;
  local armLearn = plan.arm in C121_CATALOG_ARM_LEARN_REV
      ? C121_CATALOG_ARM_LEARN_REV[plan.arm] : 0;
  local reason = "new";
  if (key in C121_CATALOG_CACHE) {
    local entry = C121_CATALOG_CACHE[key];
    if (entry.airportRev != airportRev) reason = "engine";
    else if (entry.townA != revA || entry.townB != revB) reason = "town";
    else if (entry.stationRevA != stationRevA || entry.stationRevB != stationRevB
        || entry.routes != plan.hubRoutes) reason = "station";
    else if (entry.airportLearn != airportLearn || entry.hubLearnA != hubLearnA
        || entry.hubLearnB != hubLearnB || entry.armLearn != armLearn) reason = "learning";
    else if (date - entry.date >= 365) reason = "age";
    else if (entry.distance != plan.distance
        || (V93_AIR_DEMAND_PRODUCTION && entry.monthlyPax != plan.monthlyPax)
        || entry.airportPrice != plan.airport.price
        || entry.airportMaintenance != plan.airport.maintenance) reason = "input";
    else {
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.c121CacheHits++;
      OpexC121CatalogClearPlanSnapshot(plan);
      if (entry.demand != null) plan.c121Demand <- entry.demand;
      if (entry.serviceA != null) plan.c121ServiceA <- entry.serviceA;
      if (entry.serviceB != null) plan.c121ServiceB <- entry.serviceB;
      if (entry.engineStatic != null) plan.c121EngineStatic <- entry.engineStatic;
      if (entry.shadowMonthly != null) plan.b9ShadowMonthly <- entry.shadowMonthly;
      if (entry.choice != null) {
        plan.c121ChosenEngine <- entry.choice.plane.id;
        plan.c121ChosenMailKnown <- entry.mailKnown;
      }
      if (cacheMark != null) OpexSpanAgg("air.c121.cache", cacheMark);
      if (PROBE_C121_ENGINE_TABLE) OpexC121EngTabEmitHit(plan);
      return entry.choice;
    }
  }
  if (cacheMark != null) OpexSpanAgg("air.c121.cache", cacheMark);
  if (CATALOG_COST_ACTIVE != null) {
    CATALOG_COST_ACTIVE.c121Recomputed++;
    if (reason == "engine") CATALOG_COST_ACTIVE.c121DirtyEngine++;
    else if (reason == "town") CATALOG_COST_ACTIVE.c121DirtyTown++;
    else if (reason == "station") CATALOG_COST_ACTIVE.c121DirtyStation++;
    else if (reason == "learning") CATALOG_COST_ACTIVE.c121DirtyLearning++;
    else if (reason == "age") CATALOG_COST_ACTIVE.c121DirtyAge++;
    else if (reason == "input") CATALOG_COST_ACTIVE.c121DirtyInput++;
    else if (reason == "new") CATALOG_COST_ACTIVE.c121New++;
  }
  OpexC121CatalogClearPlanSnapshot(plan);
  /* Les revisions locales suffisent pour ville/station. Pour un changement
   * d'entrees ou l'expiration, ne pas laisser le cache enfant annuler le miss.
   * Le flag reste local au calcul, jamais dans le snapshot publie. */
  plan.c121CatalogRefreshEndpoints <- reason == "input" || reason == "age";
  if (plan.c121CatalogRefreshEndpoints) OpexC121InvalidateEndpointGeometry();
  local choice = null;
  try {
    choice = OpexC121ChooseRoutePlane(catalog, plan, lines);
  } catch (error) {
    delete plan.c121CatalogRefreshEndpoints;
    throw error;
  }
  delete plan.c121CatalogRefreshEndpoints;
  C121_CATALOG_CACHE.rawset(key, {
    choice = choice, date = date, airportRev = airportRev,
    townA = revA, townB = revB, stationRevA = stationRevA,
    stationRevB = stationRevB, airportLearn = airportLearn,
    hubLearnA = hubLearnA, hubLearnB = hubLearnB, armLearn = armLearn,
    airportType = plan.airport.type, arm = plan.arm,
    townAId = plan.siteA.town.id, townBId = plan.siteB.town.id,
    stationAId = stationA, stationBId = stationB,
    lastScore = (key in C121_CATALOG_CACHE)
        ? C121_CATALOG_CACHE[key].lastScore
        : (choice != null && choice.economics != null && choice.economics.capital > 0
            ? choice.economics.profitAnnual.tofloat() / choice.economics.capital : 0.0),
    routes = plan.hubRoutes,
    distance = plan.distance, monthlyPax = plan.monthlyPax,
    airportPrice = plan.airport.price,
    airportMaintenance = plan.airport.maintenance,
    demand = ("c121Demand" in plan) ? plan.c121Demand : null,
    serviceA = ("c121ServiceA" in plan) ? plan.c121ServiceA : null,
    serviceB = ("c121ServiceB" in plan) ? plan.c121ServiceB : null,
    engineStatic = ("c121EngineStatic" in plan) ? plan.c121EngineStatic : null,
    shadowMonthly = ("b9ShadowMonthly" in plan) ? plan.b9ShadowMonthly : null,
    mailKnown = ("c121ChosenMailKnown" in plan) ? plan.c121ChosenMailKnown : false,
  });
  return choice;
}

/* Shadow de stabilite du classement, execute seulement lorsqu'un nouveau moteur
 * vient d'apprendre son couple PASS/MAIL. Le classement PASS-only et le
 * classement PASS+MAIL portent exactement sur le meme sous-ensemble de moteurs
 * observes ; la couverture partielle est exposee explicitement. */
function OpexC121ReplayEngineChoice(catalog, plan, result, newlyObserved)
{
  if (!C121_AIR_ENGINE_REPLAY_SHADOW || catalog == null || plan == null || result == null
      || !newlyObserved || !("plane" in plan) || plan.plane == null
      || !("airport" in plan) || plan.airport == null) return null;
  if (catalog.airPlaneChoicesByAirport == null
      || !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return null;

  local tick0 = AIController.GetTick();
  local ops0 = AIController.GetOpsTillSuspend();
  local total = 0;
  local known = 0;
  local evaluated = 0;
  local bestPass = null;
  local bestMail = null;
  local chosenPass = null;
  local chosenMail = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    /* Le catalogue peut conserver une entree historique apres expiration. */
    if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
    if (!OpexC118EngineFitsPlan(plan, plane)) continue;
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    total++;
    if (!(plane.id in C121_AIR_ENGINE_CAPACITY_OBS)) continue;
    local caps = C121_AIR_ENGINE_CAPACITY_OBS[plane.id];
    if (caps == null || caps.pax <= 0 || caps.mail < 0) continue;
    known++;
    local passEconomics = OpexC121AirEconomics(catalog, plan, plane, caps.pax, 0, 0);
    local mailEconomics = OpexC121EngineEconomics(catalog, plan, plane, 0);
    if (passEconomics == null || mailEconomics == null
        || !("decisionScore" in passEconomics) || !("decisionScore" in mailEconomics)) continue;
    evaluated++;
    local passItem = { plane = plane, economics = passEconomics };
    local mailItem = { plane = plane, economics = mailEconomics };
    if (plane.id == plan.plane.id) {
      chosenPass = passItem;
      chosenMail = mailItem;
    }
    if (bestPass == null
        || passEconomics.decisionScore > bestPass.economics.decisionScore
        || (passEconomics.decisionScore == bestPass.economics.decisionScore
            && passEconomics.decisionProfitAnnual > bestPass.economics.decisionProfitAnnual)) {
      bestPass = passItem;
    }
    if (bestMail == null
        || mailEconomics.decisionScore > bestMail.economics.decisionScore
        || (mailEconomics.decisionScore == bestMail.economics.decisionScore
            && mailEconomics.decisionProfitAnnual > bestMail.economics.decisionProfitAnnual)) {
      bestMail = mailItem;
    }
  }
  local tick1 = AIController.GetTick();
  return {
    total = total, known = known, evaluated = evaluated, complete = known == total,
    bestPass = bestPass, bestMail = bestMail, chosenPass = chosenPass, chosenMail = chosenMail,
    changed = bestPass != null && bestMail != null && bestPass.plane.id != bestMail.plane.id,
    ticks = tick1 - tick0, ops = OpexAirCalcDeltaOps(tick0, ops0)
  };
}

/* Post-chantier : mesure exacte des deux capacites du vehicule refitte PASS. */
function OpexC121MeasureBuiltEconomics(catalog, plan, result)
{
  if ((!C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS) || plan == null || result == null
      || !("c121Demand" in plan) || !("vehicle" in result) || !AIVehicle.IsValidVehicle(result.vehicle)) return;
  local paxCapacity = AIVehicle.GetCapacity(result.vehicle, catalog.paxCargo);
  local mailCapacity = (("mailCargo" in catalog) && catalog.mailCargo >= 0)
      ? AIVehicle.GetCapacity(result.vehicle, catalog.mailCargo) : -1;
  if (paxCapacity <= 0 || mailCapacity < 0) return;
  local engineId = AIVehicle.GetEngineType(result.vehicle);
  local newlyObserved = !(engineId in C121_AIR_ENGINE_CAPACITY_OBS);
  local priorMail = newlyObserved ? -1 : C121_AIR_ENGINE_CAPACITY_OBS[engineId].mail;
  C121_AIR_ENGINE_CAPACITY_OBS.rawset(engineId, { pax = paxCapacity, mail = mailCapacity });
  if (C121_CATALOG_INCREMENTAL && priorMail != mailCapacity
      && catalog != null && catalog.airPlaneChoicesByAirport != null) {
    foreach (airportType, choices in catalog.airPlaneChoicesByAirport) {
      foreach (candidatePlane in choices) {
        if (candidatePlane.id != engineId) continue;
        C121_CATALOG_AIRPORT_LEARN_REV.rawset(airportType,
            (airportType in C121_CATALOG_AIRPORT_LEARN_REV
                ? C121_CATALOG_AIRPORT_LEARN_REV[airportType] : 0) + 1);
        break;
      }
    }
  }
  local tick0 = AIController.GetTick();
  local ops0 = AIController.GetOpsTillSuspend();
  local actualN = ("vehicles" in result) && result.vehicles != null ? result.vehicles.len() : 1;
  /* Le shadow est descriptif : scanner toute la flotte optimale ne change aucune
   * decision et peut suspendre le script. Garder ce cout uniquement pour le futur
   * chemin causal C121 ; le shadow mesure la flotte effectivement construite. */
  local target = C121_AIR_ECONOMICS
      ? OpexC121EngineEconomics(catalog, plan, plan.plane, 0)
      : null;
  local actual = OpexC121AirEconomics(catalog, plan, plan.plane, paxCapacity, mailCapacity, actualN);
  local next = null;
  if (C121_AIR_ECONOMICS && target != null && actual != null && actualN < target.planes) {
    next = OpexC121AirEconomics(
        catalog, plan, plan.plane, paxCapacity, mailCapacity, actualN + 1);
  }
  local engineReplay = OpexC121ReplayEngineChoice(catalog, plan, result, newlyObserved);
  local tick1 = AIController.GetTick();
  local ops1 = AIController.GetOpsTillSuspend();
  result.c121PaxCapacity <- paxCapacity;
  result.c121MailCapacity <- mailCapacity;
  result.c121TargetEconomics <- target;
  result.c121ActualEconomics <- actual;
  result.c121MarginalProfit <- (next != null && actual != null)
      ? next.profitAnnual - actual.profitAnnual : 0;
  result.c121MarginalRevenue <- (next != null && actual != null)
      ? next.revenueAnnual - actual.revenueAnnual : 0;
  result.c121EngineReplay <- engineReplay;
  result.c121EvalTicks <- tick1 - tick0;
  result.c121EvalOps <- OpexAirCalcDeltaOps(tick0, ops0);
}

function OpexC121AttachLineShadow(line, lineId, plan, result)
{
  if ((!C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS) || line == null || plan == null
      || result == null || !("c121Demand" in plan)) return;
  local paxCapacity = ("c121PaxCapacity" in result) ? result.c121PaxCapacity : -1;
  local mailCapacity = ("c121MailCapacity" in result) ? result.c121MailCapacity : -1;
  local demandOps = ("c121DemandOps" in plan) ? plan.c121DemandOps : -1;
  local demandTicks = ("c121DemandTicks" in plan) ? plan.c121DemandTicks : -1;
  local evalOps = ("c121EvalOps" in result) ? result.c121EvalOps : -1;
  local evalTicks = ("c121EvalTicks" in result) ? result.c121EvalTicks : -1;
  local target = ("c121TargetEconomics" in result) ? result.c121TargetEconomics : null;
  local actual = ("c121ActualEconomics" in result) ? result.c121ActualEconomics : null;
  local keepLineDiagnostics = C121_AIR_ECONOMICS_SHADOW || C121_AIR_ENGINE_REPLAY_SHADOW;
  /* C121 ne garde jamais ses tables riches dans line. SAVE_FULL_STATE projette
   * seulement les floats top-level : une table c121Demand/economics contenant
   * des floats imbriques fait refuser le savegame par OpenTTD. Les decisions ne
   * relisent pas ces tables apres le build ; conserver uniquement les scalaires
   * necessaires au probe maintient la telemetry et un graphe de sauvegarde plat. */
  if (C121_AIR_ECONOMICS) {
    line.c121Arm <- ("arm" in plan) ? plan.arm : "unknown";
    line.c121MarginalProfit <- ("c121MarginalProfit" in result) ? result.c121MarginalProfit : 0;
    line.c121MarginalRevenue <- ("c121MarginalRevenue" in result) ? result.c121MarginalRevenue : 0;
    /* 0 = aucune marge reelle encore observee. Le cold-start physique reste
     * disponible dans c121Marginal*, mais la premiere observation complete le
     * remplace ; seules les observations reelles suivantes sont moyennees. */
    line.c121MarginalSamples <- 0;
    if (actual != null) {
      line.c121RawRevenueAnnual <- ("rawRevenueAnnual" in actual) ? actual.rawRevenueAnnual : actual.revenueAnnual;
      local realization = ("realizationFactor" in actual) ? actual.realizationFactor : 1.0;
      line.c121RealizationPmAtBuild <- (realization * 1000.0).tointeger();
      line.c121VehicleAmortPerPlane <- actual.planes > 0
          ? actual.vehicleAmortAnnual / actual.planes : 0;
    }
    if (target != null) {
      line.c121TargetPlanes <- target.planes;
    }
    /* Les scalaires ci-dessous ne pilotent aucune decision. Les garder sur
     * chaque ligne en causal normal faisait depasser le budget d'opcodes de
     * Save() vers 100+ lignes AIR. Les shadows peuvent encore les conserver. */
    if (keepLineDiagnostics) {
      if (("plane" in plan) && plan.plane != null) line.c121EngineId <- plan.plane.id;
      line.c121PaxCapacity <- paxCapacity;
      line.c121MailCapacity <- mailCapacity;
      line.c121DemandOps <- demandOps;
      line.c121DemandTicks <- demandTicks;
      line.c121EvalOps <- evalOps;
      line.c121EvalTicks <- evalTicks;
      if (actual != null) {
        line.c121ActualCarriedPax <- actual.carriedPax;
        line.c121ActualCarriedMail <- actual.carriedMail;
        line.c121ActualCarried <- actual.carried;
        line.c121ActualRevenueAnnual <- actual.revenueAnnual;
        line.c121ActualProfitAnnual <- actual.profitAnnual;
        line.c121ActualRunningAnnual <- actual.runningAnnual;
        line.c121ActualVehicleRunningAnnual <- actual.vehicleRunningAnnual;
        line.c121ActualAmortAnnual <- actual.amortAnnual;
        line.c121ActualPlanes <- actual.planes;
        line.c121ActualOneWayDays <- actual.oneWayDays;
        line.c121ActualHeadwayDays <- actual.headwayDays;
        line.c121ActualStationRating <- actual.stationRating;
      }
      if (target != null) {
        line.c121TargetCarriedPax <- target.carriedPax;
        line.c121TargetCarriedMail <- target.carriedMail;
        line.c121TargetCarried <- target.carried;
        line.c121TargetRevenueAnnual <- target.revenueAnnual;
        line.c121TargetProfitAnnual <- target.profitAnnual;
      }
    }
  }
  local engineReplay = ("c121EngineReplay" in result) ? result.c121EngineReplay : null;
  local replayPass = engineReplay != null ? engineReplay.bestPass : null;
  local replayMail = engineReplay != null ? engineReplay.bestMail : null;
  local replayChosenPass = engineReplay != null ? engineReplay.chosenPass : null;
  local replayChosenMail = engineReplay != null ? engineReplay.chosenMail : null;
  AILog.Info("C121_BUILD line=" + lineId
      + " arm=" + (("arm" in plan) ? plan.arm : "unknown") + " engine=" + plan.plane.id
      + " station_id_a=" + AIStation.GetStationID(result.stationA)
      + " station_id_b=" + AIStation.GetStationID(result.stationB)
      + " pax_a=" + plan.c121Demand.paxA + " pax_b=" + plan.c121Demand.paxB
      + " mail_a=" + plan.c121Demand.mailA + " mail_b=" + plan.c121Demand.mailB
      + " pax_raw_a=" + plan.c121Demand.paxRawA + " pax_raw_b=" + plan.c121Demand.paxRawB
      + " mail_raw_a=" + plan.c121Demand.mailRawA + " mail_raw_b=" + plan.c121Demand.mailRawB
      + " route_div_a=" + plan.c121Demand.routeDivA + " route_div_b=" + plan.c121Demand.routeDivB
      + " current_pax_rating_a=" + plan.c121Demand.currentPaxRatingA
      + " current_pax_rating_b=" + plan.c121Demand.currentPaxRatingB
      + " current_mail_rating_a=" + plan.c121Demand.currentMailRatingA
      + " current_mail_rating_b=" + plan.c121Demand.currentMailRatingB
      + " pax_ticks_a=" + plan.c121Demand.paxTicksA + " pax_ticks_b=" + plan.c121Demand.paxTicksB
      + " mail_ticks_a=" + plan.c121Demand.mailTicksA + " mail_ticks_b=" + plan.c121Demand.mailTicksB
      + " pax_ops_a=" + plan.c121Demand.paxOpsA + " pax_ops_b=" + plan.c121Demand.paxOpsB
      + " mail_ops_a=" + plan.c121Demand.mailOpsA + " mail_ops_b=" + plan.c121Demand.mailOpsB
      + " pax_predict_ticks_a=" + plan.c121Demand.paxPredictTicksA
      + " pax_predict_ticks_b=" + plan.c121Demand.paxPredictTicksB
      + " pax_coverage_ticks_a=" + plan.c121Demand.paxCoverageTicksA
      + " pax_coverage_ticks_b=" + plan.c121Demand.paxCoverageTicksB
      + " pax_union_ticks_a=" + plan.c121Demand.paxUnionTicksA
      + " pax_union_ticks_b=" + plan.c121Demand.paxUnionTicksB
      + " mail_union_ticks_a=" + plan.c121Demand.mailUnionTicksA
      + " mail_union_ticks_b=" + plan.c121Demand.mailUnionTicksB
      + " pax_cap=" + paxCapacity + " mail_cap=" + mailCapacity
      + " demand_ops=" + demandOps + " demand_ticks=" + demandTicks
      + " eval_ops=" + evalOps + " eval_ticks=" + evalTicks
      + " causal_scan_ops=" + (("c121EngineScanOps" in plan) ? plan.c121EngineScanOps : -1)
      + " causal_scan_ticks=" + (("c121EngineScanTicks" in plan) ? plan.c121EngineScanTicks : -1)
      + " causal_static_ops=" + (("c121EngineStaticOps" in plan) ? plan.c121EngineStaticOps : -1)
      + " causal_static_ticks=" + (("c121EngineStaticTicks" in plan) ? plan.c121EngineStaticTicks : -1)
      + " causal_engine_evals=" + (("c121EngineEvalCount" in plan) ? plan.c121EngineEvalCount : -1)
      + " causal_engine_known=" + (("c121EngineKnownCount" in plan) ? plan.c121EngineKnownCount : -1)
      + " causal_eval_ops_total=" + (("c121EngineEvalOpsTotal" in plan) ? plan.c121EngineEvalOpsTotal : -1)
      + " causal_eval_ops_same_tick=" + (("c121EngineEvalOpsSameTick" in plan) ? plan.c121EngineEvalOpsSameTick : -1)
      + " causal_eval_same_tick_count=" + (("c121EngineEvalSameTickCount" in plan) ? plan.c121EngineEvalSameTickCount : -1)
      + " causal_winner_full_ops=" + (("c121WinnerFullOps" in plan) ? plan.c121WinnerFullOps : -1)
      + " causal_winner_full_ticks=" + (("c121WinnerFullTicks" in plan) ? plan.c121WinnerFullTicks : -1)
      + " causal_choice_mail_known=" + (("c121ChosenMailKnown" in plan) && plan.c121ChosenMailKnown ? 1 : 0)
      + " postbuild_mail_known=" + (target != null && ("engineMailKnown" in target) && target.engineMailKnown ? 1 : 0)
      + " replay_engine_total=" + (engineReplay != null ? engineReplay.total : -1)
      + " replay_engine_known=" + (engineReplay != null ? engineReplay.known : -1)
      + " replay_engine_evaluated=" + (engineReplay != null ? engineReplay.evaluated : -1)
      + " replay_engine_complete=" + (engineReplay != null && engineReplay.complete ? 1 : 0)
      + " replay_shadow_ticks=" + (engineReplay != null ? engineReplay.ticks : -1)
      + " replay_shadow_ops=" + (engineReplay != null ? engineReplay.ops : -1)
      + " replay_pass_engine=" + (replayPass != null ? replayPass.plane.id : -1)
      + " replay_pass_n=" + (replayPass != null ? replayPass.economics.decisionPlanes : -1)
      + " replay_pass_revenue=" + (replayPass != null ? replayPass.economics.decisionRevenueAnnual : -1)
      + " replay_pass_profit=" + (replayPass != null ? replayPass.economics.decisionProfitAnnual : -1)
      + " replay_pass_score=" + (replayPass != null ? replayPass.economics.decisionScore : -1)
      + " replay_mail_engine=" + (replayMail != null ? replayMail.plane.id : -1)
      + " replay_mail_n=" + (replayMail != null ? replayMail.economics.decisionPlanes : -1)
      + " replay_mail_revenue=" + (replayMail != null ? replayMail.economics.decisionRevenueAnnual : -1)
      + " replay_mail_profit=" + (replayMail != null ? replayMail.economics.decisionProfitAnnual : -1)
      + " replay_mail_score=" + (replayMail != null ? replayMail.economics.decisionScore : -1)
      + " replay_mail_changed=" + (engineReplay != null ? (engineReplay.changed ? 1 : 0) : -1)
      + " replay_chosen_pass_score=" + (replayChosenPass != null ? replayChosenPass.economics.decisionScore : -1)
      + " replay_chosen_mail_score=" + (replayChosenMail != null ? replayChosenMail.economics.decisionScore : -1)
      /* Alias historiques du meilleur score complet, conserves pour les outils
       * d'analyse existants ; la nouvelle source de verite est replay_mail_*. */
      + " replay_score_engine=" + (replayMail != null ? replayMail.plane.id : -1)
      + " replay_score_n=" + (replayMail != null ? replayMail.economics.decisionPlanes : -1)
      + " replay_score_revenue=" + (replayMail != null ? replayMail.economics.decisionRevenueAnnual : -1)
      + " replay_score_profit=" + (replayMail != null ? replayMail.economics.decisionProfitAnnual : -1)
      + " replay_score_value=" + (replayMail != null ? replayMail.economics.decisionScore : -1)
      + " replay_chosen_n=" + (replayChosenMail != null ? replayChosenMail.economics.decisionPlanes : -1)
      + " replay_chosen_revenue=" + (replayChosenMail != null ? replayChosenMail.economics.decisionRevenueAnnual : -1)
      + " replay_chosen_profit=" + (replayChosenMail != null ? replayChosenMail.economics.decisionProfitAnnual : -1)
      + " replay_chosen_score=" + (replayChosenMail != null ? replayChosenMail.economics.decisionScore : -1)
      + " legacy_n=" + (("planes" in plan) ? plan.planes : -1)
      + " target_n=" + (target != null ? target.planes : -1)
      + " target_pax=" + (target != null ? target.carriedPax : -1)
      + " target_mail=" + (target != null ? target.carriedMail : -1)
      + " target_revenue=" + (target != null ? target.revenueAnnual : -1)
      + " target_revenue_pax=" + (target != null ? target.revenuePaxAnnual : -1)
      + " target_revenue_mail=" + (target != null ? target.revenueMailAnnual : -1)
      + " target_profit=" + (target != null ? target.profitAnnual : -1)
      + " target_running=" + (target != null ? target.runningAnnual : -1)
      + " target_vehicle_running=" + (target != null ? target.vehicleRunningAnnual : -1)
      + " target_amort=" + (target != null ? target.amortAnnual : -1)
      + " decision_kdec=" + (target != null && ("decisionKDec" in target) ? target.decisionKDec : -1)
      + " decision_n=" + (target != null && ("decisionPlanes" in target) ? target.decisionPlanes : -1)
      + " decision_score=" + (target != null && ("decisionScore" in target) ? target.decisionScore : -1)
      + " decision_pax=" + (target != null && ("decisionCarriedPax" in target) ? target.decisionCarriedPax : -1)
      + " decision_mail=" + (target != null && ("decisionCarriedMail" in target) ? target.decisionCarriedMail : -1)
      + " decision_revenue=" + (target != null && ("decisionRevenueAnnual" in target) ? target.decisionRevenueAnnual : -1)
      + " decision_profit=" + (target != null && ("decisionProfitAnnual" in target) ? target.decisionProfitAnnual : -1)
      + " decision_capital=" + (target != null && ("decisionCapital" in target) ? target.decisionCapital : -1)
      + " decision_rating=" + (target != null && ("decisionStationRating" in target) ? target.decisionStationRating : -1)
      + " decision_headway=" + (target != null && ("decisionHeadwayDays" in target) ? target.decisionHeadwayDays : -1)
      + " actual_n=" + (actual != null ? actual.planes : -1)
      + " actual_pax=" + (actual != null ? actual.carriedPax : -1)
      + " actual_mail=" + (actual != null ? actual.carriedMail : -1)
      + " actual_revenue=" + (actual != null ? actual.revenueAnnual : -1)
      + " actual_profit=" + (actual != null ? actual.profitAnnual : -1)
      + " actual_running=" + (actual != null ? actual.runningAnnual : -1)
      + " actual_vehicle_running=" + (actual != null ? actual.vehicleRunningAnnual : -1)
      + " actual_amort=" + (actual != null ? actual.amortAnnual : -1)
      + " actual_vehicle_amort=" + (actual != null ? actual.vehicleAmortAnnual : -1)
      + " actual_infra_running=" + (actual != null ? actual.infraRunningAnnual : -1)
      + " actual_infra_amort=" + (actual != null ? actual.infraAmortAnnual : -1)
      + " plane_price=" + (actual != null ? actual.planePrice : -1)
      + " life_years=" + (actual != null ? actual.lifeYears : -1)
      + " airport_capital=" + (actual != null ? actual.airportCapital : -1)
      + " new_airports=" + (actual != null ? actual.newAirportCount : -1)
      + " rating_base_a=" + (actual != null ? actual.ratingBaseA : -1)
      + " rating_base_b=" + (actual != null ? actual.ratingBaseB : -1)
      + " model_kdec=" + (actual != null && ("decisionKDec" in actual) ? actual.decisionKDec : -1)
      + " pax_income=" + (actual != null ? actual.paxIncome : -1)
      + " mail_income=" + (actual != null ? actual.mailIncome : -1)
      + " flight_days=" + (actual != null ? actual.flightDays : -1)
      + " maneuver_days=" + (actual != null ? actual.maneuverDays : -1)
      + " physical_one_way_days=" + (actual != null ? actual.physicalOneWayDays : -1)
      + " hub_delay_a=" + (actual != null ? actual.hubDelayA : -1)
      + " hub_delay_b=" + (actual != null ? actual.hubDelayB : -1)
      + " hub_delay_obs_a=" + (actual != null ? actual.hubDelayObsA : -1)
      + " hub_delay_obs_b=" + (actual != null ? actual.hubDelayObsB : -1)
      + " hub_delay_window_obs_a=" + (actual != null ? actual.hubDelayWindowObsA : -1)
      + " hub_delay_window_obs_b=" + (actual != null ? actual.hubDelayWindowObsB : -1)
      + " hub_delay_var_a=" + (actual != null ? actual.hubDelayVarianceA : -1)
      + " hub_delay_var_b=" + (actual != null ? actual.hubDelayVarianceB : -1)
      + " one_way_days=" + (actual != null ? actual.oneWayDays : -1)
      + " round_trip_days=" + (actual != null ? actual.roundTripDays : -1)
      + " headway_days=" + (actual != null ? actual.headwayDays : -1)
      + " station_headway_a=" + (actual != null ? actual.stationHeadwayA : -1)
      + " station_headway_b=" + (actual != null ? actual.stationHeadwayB : -1)
      + " existing_pickup_a=" + (actual != null ? actual.existingPickupRateA : -1)
      + " existing_pickup_b=" + (actual != null ? actual.existingPickupRateB : -1)
      + " existing_pax_rate_a=" + (actual != null ? actual.existingPaxRateA : -1)
      + " existing_pax_rate_b=" + (actual != null ? actual.existingPaxRateB : -1)
      + " existing_mail_rate_a=" + (actual != null ? actual.existingMailRateA : -1)
      + " existing_mail_rate_b=" + (actual != null ? actual.existingMailRateB : -1)
      + " runway_service_a=" + (actual != null && ("runwayServiceDaysA" in actual) ? actual.runwayServiceDaysA : -1)
      + " runway_service_b=" + (actual != null && ("runwayServiceDaysB" in actual) ? actual.runwayServiceDaysB : -1)
      + " runway_scale_a=" + (actual != null && ("runwayScaleA" in actual) ? actual.runwayScaleA : -1)
      + " runway_scale_b=" + (actual != null && ("runwayScaleB" in actual) ? actual.runwayScaleB : -1)
      + " requested_pickup=" + (actual != null && ("requestedPickupRate" in actual) ? actual.requestedPickupRate : -1)
      + " effective_pickup=" + (actual != null && ("pickupRate" in actual) ? actual.pickupRate : -1)
      + " rating=" + (actual != null ? actual.stationRating : -1)
      + " rating_pax_a=" + (actual != null ? actual.ratingPaxA : -1)
      + " rating_pax_b=" + (actual != null ? actual.ratingPaxB : -1)
      + " rating_mail_a=" + (actual != null ? actual.ratingMailA : -1)
      + " rating_mail_b=" + (actual != null ? actual.ratingMailB : -1)
      + " rating_cycle=" + (actual != null && actual.ratingCycle ? 1 : 0)
      + " fleet_scan_cap=" + (actual != null ? actual.fleetScanCap : -1)
      + " pax_dir_capacity=" + (actual != null ? actual.paxDirectionCapacity : -1)
      + " mail_dir_capacity=" + (actual != null ? actual.mailDirectionCapacity : -1)
      + " payment_distance=" + (actual != null ? actual.paymentDistance : -1)
      + " income_days=" + (actual != null ? actual.incomeDays : -1));
  if (C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS) {
    if ("c121Demand" in line) delete line.c121Demand;
    if ("c121TargetEconomics" in line) delete line.c121TargetEconomics;
    if ("c121ActualEconomics" in line) delete line.c121ActualEconomics;
    if ("c121PaxCapacity" in line) delete line.c121PaxCapacity;
    if ("c121MailCapacity" in line) delete line.c121MailCapacity;
    if ("c121DemandOps" in line) delete line.c121DemandOps;
    if ("c121DemandTicks" in line) delete line.c121DemandTicks;
    if ("c121EvalOps" in line) delete line.c121EvalOps;
    if ("c121EvalTicks" in line) delete line.c121EvalTicks;
  }
}
