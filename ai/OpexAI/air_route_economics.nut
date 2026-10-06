/* Module AIR extrait de builder_air.nut (R11) : economie historique des routes et reconciliation de construction. */
/* Economie et dimensionnement optimal de flotte selon les caracteristiques du vehicule.
 * serviceScan (V92) leve le plafond a un avion et retient le meilleur nombre d'appareils. */
function OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
                          infrastructureMaintenance, maxCapital, newAirportCount = 2,
                          opcodePadding = 0, fixedPlanes = 0, targetSizing = false,
                          serviceScan = false, forcePhysicalTiming = false,
                          forceC100RankReplay = false, paymentDistance = 0)
{
  local c119Income = C119_AIR_INCOME_MODEL && paymentDistance > 0;
  local econKey = null;
  local canMemo = C80_AIR_EVAL_FAST && fixedPlanes == 0 && opcodePadding == 0 && !targetSizing && !serviceScan;
  if (canMemo) {
    /* Memo valable seulement dans le mois ou il a ete rempli (prix indexes chaque mois). */
    local nowDate = AIDate.GetCurrentDate();
    if (AIR_MEMO_MONTH != AIDate.GetYear(nowDate) * 12 + AIDate.GetMonth(nowDate)) canMemo = false;
  }
  if (canMemo) {
    econKey = plane.id + "|" + airport.type + "|" + distance + "|" + monthlyPax + "|" + newAirportCount + "|" + maxCapital + "|" + (infrastructureMaintenance ? 1 : 0)
        + "|pt=" + ((C100_AIR_TRIP_PHYSICAL || C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
            || C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
            || forcePhysicalTiming) ? 1 : 0)
        + "|rr=" + ((C114_AIR_C100_FULL_REPLAY || forceC100RankReplay) ? 1 : 0)
        + "|c119=" + (c119Income ? paymentDistance : 0);
    if (econKey in AIR_ECONOMICS_MEMO) {
      return AIR_ECONOMICS_MEMO[econKey];
    }
  }

  local oneWayDays = 0;
  local roundTripDays = 0;
  local tripsPerMonth = 0;
  local capacityPerPlane = 0;
  local incomePerUnit = 0.0;

  if (canMemo) {
    local physicalTiming = C100_AIR_TRIP_PHYSICAL || C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
        || C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
        || forcePhysicalTiming;
    local tripKey = (C114_AIR_C100_FULL_REPLAY || forceC100RankReplay)
        ? ("r|" + plane.id + "|" + airport.type + "|" + distance)
        : (physicalTiming
            ? (plane.id + "|" + airport.type + "|" + distance)
            : ((plane.id * 10000) + distance));
    if (c119Income) tripKey = "c119|" + tripKey + "|pd=" + paymentDistance;
    if (tripKey in AIR_TRIP_MEMO) {
      local tripData = AIR_TRIP_MEMO[tripKey];
      oneWayDays = tripData.oneWayDays;
      roundTripDays = tripData.roundTripDays;
      tripsPerMonth = tripData.tripsPerMonth;
      capacityPerPlane = tripData.capacityPerPlane;
      incomePerUnit = tripData.incomePerUnit;
    } else {
      local trip = OpexAirTripModel(plane.speed, plane.capacity, distance, plane.id, airport.type,
          forcePhysicalTiming, forceC100RankReplay);
      oneWayDays = trip.oneWayDays;
      roundTripDays = trip.roundTripDays;
      tripsPerMonth = trip.tripsPerMonth;
      capacityPerPlane = trip.capacityPerPlane;
      if (capacityPerPlane > 0) {
        local incomeDays = c119Income ? OpexC119AirIncomeDays(plane, distance) : OpexCeilDiv(oneWayDays, 1);
        local incomeDistance = c119Income ? paymentDistance : distance;
        incomePerUnit = OpexAirFarePerPax(catalog, plane, incomeDistance, incomeDays);
      }
      AIR_TRIP_MEMO.rawset(tripKey, {
        oneWayDays = oneWayDays,
        roundTripDays = roundTripDays,
        tripsPerMonth = tripsPerMonth,
        capacityPerPlane = capacityPerPlane,
        incomePerUnit = incomePerUnit
      });
    }
  } else {
    local trip = OpexAirTripModel(plane.speed, plane.capacity, distance, plane.id, airport.type,
        forcePhysicalTiming, forceC100RankReplay);
    oneWayDays = trip.oneWayDays;
    roundTripDays = trip.roundTripDays;
    tripsPerMonth = trip.tripsPerMonth;
    capacityPerPlane = trip.capacityPerPlane;
    if (capacityPerPlane <= 0) return null;
    local incomeDays = c119Income ? OpexC119AirIncomeDays(plane, distance) : OpexCeilDiv(oneWayDays, 1);
    local incomeDistance = c119Income ? paymentDistance : distance;
    /* En soute, sans mesure, ~15 % du tarif postal par passager. V92 utilise la soute reelle. */
    incomePerUnit = OpexAirFarePerPax(catalog, plane, incomeDistance, incomeDays);
  }
  if (capacityPerPlane <= 0) {
    if (canMemo) AIR_ECONOMICS_MEMO.rawset(econKey, null);
    return null;
  }
  local airportMaintenanceAnnual =
      infrastructureMaintenance ? 12 * newAirportCount * airport.maintenance : 0;
  local airportAmortAnnual = (newAirportCount * airport.price * INFRA_AMORT_PCT / 100) / 30;
  local best = null;
  /* Plafond d'appareils initial : le portefeuille flotte demarre a un seul avion. */
  local isSmall = (airport.type == AIAirport.AT_SMALL || airport.type == AIAirport.AT_COMMUTER);
  local multiPlaneMax = (newAirportCount == 2) ? 3 : (isSmall ? 4 : 6);
  local maxAllowed = (targetSizing || serviceScan) ? multiPlaneMax
      : ((OPEX_ECONOMY_OPCODE_COMPAT_FALSE || FLEET_PORTFOLIO) ? 1 : multiPlaneMax);
  if (!targetSizing && !serviceScan && !OPEX_ECONOMY_OPCODE_COMPAT_FALSE && !FLEET_PORTFOLIO && OPEX_AIR_PLAN_PAD && opcodePadding > 0) maxAllowed = opcodePadding;
  /* Dimensionnement cible selon le volume passagers */
  local targetPlanes = OpexCeilDiv(monthlyPax, capacityPerPlane.tointeger());
  if (targetPlanes < 1) targetPlanes = 1;
  if (targetPlanes > maxAllowed) targetPlanes = maxAllowed;
  /* Apres chantier, la flotte existe deja : mesurer son economie ne doit pas proposer un
   * nombre theorique d'avions different de celui effectivement livre. */
  if (fixedPlanes > 0) targetPlanes = fixedPlanes;

  /* air_margin : la marge exigee a l'acceptation (30 000 / 12 000 / 2 000 selon le nombre
   * d'aeroports NEUFS -- autorite locale, terrassement, aleas) doit etre connue ici, sinon
   * _tryBuildAir trouve un plan puis le rejette et gache son cycle. L'appliquer globalement du
   * cote appelant a ete mesure a ÃƒÂ¢Ã‹â€ Ã¢â‚¬â„¢11,5 % (t = ÃƒÂ¢Ã‹â€ Ã¢â‚¬â„¢2,66) le 2026-09-01 : ca rabote aussi le hub-a-hub,
   * dont la marge reelle n'est que 2 000. Ici la marge est appliquee PAR PLAN, au bon grain.
   * L'appelant soustrait deja le plancher de 2 000, on ne compte donc que le supplement.
   * Sous 0 ou maxCapital == 0 (chemin portefeuille), ce bloc ne change rien. Adopte le
   * 2026-09-02 (defaut 1) : mesure NEUTRE, adopte pour la justesse -- voir main.nut. */
  local extraMargin = 0;
  if (AIR_MARGIN && maxCapital > 0) {
    extraMargin = ((newAirportCount == 2) ? 30000 : (newAirportCount == 1 ? 12000 : 2000)) - 2000;
  }

  local firstPlanes = fixedPlanes > 0 ? fixedPlanes : 1;
  for (local planes = firstPlanes; planes <= targetPlanes; planes++) {
    local capital = newAirportCount * airport.price + planes * plane.price;
    if (maxCapital > 0 && capital + extraMargin > maxCapital) break;
    local headwayDays = roundTripDays / planes;
    local stationRating = OpexStationRatingForHeadway(headwayDays);
    local offered = (monthlyPax * stationRating) / 100.0;
    local monthlyCapacity = planes * capacityPerPlane;
    local carried = (offered < monthlyCapacity ? offered : monthlyCapacity).tointeger();
    local revenueAnnual = (12 * carried * incomePerUnit).tointeger();
    local runningAnnual = planes * plane.runningCost + airportMaintenanceAnnual;
    local lifeYears = 20;
    if (V92_AIR_SERVICE_CHOICE && ("ageYears" in plane) && plane.ageYears > 1) lifeYears = plane.ageYears;
    local amortAnnual = planes * plane.price / lifeYears + airportAmortAnnual;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    local immobilise = (TRANSIT_COST_PERMILLE > 0)
        ? (revenueAnnual * roundTripDays * TRANSIT_COST_PERMILLE) / 365000 : 0;
    local totalCapital = capital + immobilise;
    local roi = totalCapital > 0 ? (profitAnnual * 1000) / totalCapital : 0;
    if (best == null || profitAnnual > best.profitAnnual ||
        (profitAnnual == best.profitAnnual && roi > best.roi)) {
      best = {
        planes = planes, profitAnnual = profitAnnual, revenueAnnual = revenueAnnual,
        runningAnnual = runningAnnual, amortAnnual = amortAnnual, capital = capital,
        immobilise = immobilise, roi = roi,
        oneWayDays = oneWayDays, roundTripDays = roundTripDays, headwayDays = headwayDays,
        stationRating = stationRating, tripsPerMonth = tripsPerMonth,
        monthlyCapacity = monthlyCapacity, carried = carried,
      };
    }
  }
  if (canMemo) AIR_ECONOMICS_MEMO.rawset(econKey, best);
  return best;
}

/* C84 : economie de croisiere utilisee uniquement pour memoriser une cible de flotte pour
 * l'appareil deja choisi par la politique courante. Elle ignore le capital disponible de la passe
 * courante : la construction initiale
 * reste financee comme aujourd'hui avec un seul avion et les renforts restent marginaux. */
function OpexAirTargetEconomics(catalog, airport, plane, distance, monthlyPax,
                                infrastructureMaintenance, newAirportCount, opcodePadding = 0)
{
  return OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
      infrastructureMaintenance, 0, newAirportCount, opcodePadding, 0, true);
}

/* C84 : score marginal d'un renfort d'une ligne EXISTANTE. Le moteur est celui du premier
 * appareil vivant, exactement comme OpexAirAddPlane ; aucun choix d'equipement n'est refait.
 * fixedPlanes force OpexAirEconomics a evaluer un seul point, et newAirportCount=0 annule les
 * couts d'infrastructure constants : la difference mesure donc uniquement have -> have+want. */
function OpexAirExistingLineMarginalEconomics(catalog, line, have, want)
{
  if (line == null || have < 1 || want < 1 || !("airMonthlyPax" in line)
      || line.airMonthlyPax <= 0 || !("distance" in line) || line.distance <= 0
      || !("vehicles" in line) || line.vehicles.len() == 0) return null;

  local template = null;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) {
      template = v;
      break;
    }
  }
  if (template == null) return null;

  local engine = AIVehicle.GetEngineType(template);
  local capacity = AIEngine.GetCapacity(engine);
  local speed = AIEngine.GetMaxSpeed(engine);
  local price = AIEngine.GetPrice(engine);
  local runningCost = AIEngine.GetRunningCost(engine);
  if (capacity <= 0 || speed <= 0 || price <= 0 || runningCost < 0) return null;

  local airportTile = AIAirport.IsAirportTile(line.stationA) ? line.stationA
      : ((("stationB" in line) && AIAirport.IsAirportTile(line.stationB)) ? line.stationB : null);
  if (airportTile == null) return null;
  local airportType = AIAirport.GetAirportType(airportTile);
  if (!AIAirport.IsValidAirportType(airportType)) return null;

  local airport = {
    type = airportType,
    price = AIAirport.GetPrice(airportType),
    maintenance = AIAirport.GetMonthlyMaintenanceCost(airportType),
  };
  local plane = {
    id = engine,
    capacity = capacity,
    speed = speed,
    price = price,
    runningCost = runningCost,
  };
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local before = OpexAirEconomics(catalog, airport, plane, line.distance, line.airMonthlyPax,
      infrastructureMaintenance, 0, 0, 0, have);
  local after = OpexAirEconomics(catalog, airport, plane, line.distance, line.airMonthlyPax,
      infrastructureMaintenance, 0, 0, 0, have + want);
  if (before == null || after == null) return null;
  return {
    profitAnnual = after.profitAnnual - before.profitAnnual,
    revenueAnnual = after.revenueAnnual - before.revenueAnnual,
  };
}

/* G4 : Reconcile le contrat economique d'une ligne air avec ce qui a ete effectivement pose.
 * Les arrets joints n'ajoutent que leur bassin marginal hors couverture de l'aeroport et la flotte
 * est figee au nombre reellement construit. Le cout comptable final remplace le capital estime,
 * puis amortissement, profit et ROI sont derives ensemble. */
function OpexAirReconcileActualBuild(catalog, plan, result, lines = null)
{
  if (plan == null || result == null || !("economics" in plan)) return;
  local actualPlanes = ("vehicles" in result && result.vehicles != null) ? result.vehicles.len() : 0;
  if (actualPlanes <= 0) return;
  local baseMonthly = ("monthlyPax" in plan) ? plan.monthlyPax : 0;
  local joinedMonthly = OPEX_AIR_PLAN_PAD && ("joinedMonthlyPax" in result)
      ? result.joinedMonthlyPax : 0;
  local monthlyPax = baseMonthly + joinedMonthly;
  if (monthlyPax < 10) monthlyPax = 10;
  if (V93_AIR_DEMAND_PRODUCTION) {
    /* Meme unite qu'avant : passagers mensuels de la paire, somme des deux bouts,
     * plus le bassin marginal des arrets joints. Le plancher de 10 ne s'applique pas. */
    if (catalog != null) AIR_DEMAND_PAX_CARGO = catalog.paxCargo;
    local airport = ("airport" in plan) ? plan.airport : null;
    local demandA = 0;
    local demandB = 0;
    if (("siteA" in plan) && plan.siteA != null && ("town" in plan.siteA)) {
      local anchorA = ("anchor" in plan.siteA) ? plan.siteA.anchor : null;
      demandA = OpexAirTownMonthlyPax(plan.siteA.town, anchorA, airport, lines);
    }
    if (("siteB" in plan) && plan.siteB != null && ("town" in plan.siteB)) {
      local anchorB = ("anchor" in plan.siteB) ? plan.siteB.anchor : null;
      demandB = OpexAirTownMonthlyPax(plan.siteB.town, anchorB, airport, lines);
    }
    monthlyPax = demandA + demandB + joinedMonthly;
  }
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  /* C121 causal ne doit jamais etre reecrit par l'economie AIR legacy apres le
   * chantier. OpexBuildAirRoute vient de publier la soute PASS/MAIL exacte dans
   * C121_AIR_ENGINE_CAPACITY_OBS : reutiliser donc le meme modele C121, flotte
   * figee au nombre effectivement construit. */
  local economics = (C121_AIR_ECONOMICS && ("c121Demand" in plan))
      ? OpexC121EngineEconomics(catalog, plan, plan.plane, actualPlanes)
      : OpexAirEconomics(catalog, plan.airport, plan.plane, plan.distance, monthlyPax,
          AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0,
          0, newAirports, 0, actualPlanes);
  if (economics == null) return;

  if (("actualCost" in result) && result.actualCost > 0) {
    local vehicleFloor = actualPlanes * plan.plane.price;
    local actualCapital = result.actualCost;
    if (actualCapital < vehicleFloor) actualCapital = vehicleFloor;
    local capitalDelta = actualCapital - economics.capital;
    economics.capital = actualCapital;
    economics.amortAnnual += ((capitalDelta * INFRA_AMORT_PCT / 100) / 30);
    economics.profitAnnual = economics.revenueAnnual - economics.runningAnnual - economics.amortAnnual;
    local totalCapital = economics.capital + economics.immobilise;
    economics.roi = totalCapital > 0 ? (economics.profitAnnual * 1000) / totalCapital : 0;
  }
  plan.monthlyPax = monthlyPax;
  plan.planes = actualPlanes;
  plan.capital = economics.capital;
  plan.economics = economics;
}

/* G4/B9 : contrat pre-chantier des arrets joints.
 * Les arrets sont optionnels et leur cout exact depend du site et d'eventuelles depenses
 * d'autorite locale. Le 5x6 B9 a invalide BT_BUS_STOP comme estimateur du cout traversant.
 * On ne melange donc plus un faux cout connu avec une demande inconnue : les deux restent
 * nuls a l'election et sont remplaces par leurs valeurs mesurees apres chantier. */
function OpexAirReserveJoinedStops(catalog, plan)
{
  if (!AIR_JOINED_STOPS || plan == null || !("economics" in plan)) return;
  /* B9/08.6 : extension optionnelle apres le coeur aeroport+avion. Le 5x6
   * mesure 450..2250 GBP par arret selon le site/autorite : BT_BUS_STOP n'est
   * pas une reserve exacte. Avant chantier, cout ET demande joints restent a
   * zero ; apres chantier, actualCost et catchment union reel sont reconcilies. */
  plan.joinedStopReserve <- 0;
}

function OpexAirCatalogPlane(catalog, airportType, engineId)
{
  if (catalog != null && catalog.airPlaneChoicesByAirport != null
      && (airportType in catalog.airPlaneChoicesByAirport)) {
    foreach (plane in catalog.airPlaneChoicesByAirport[airportType]) {
      if (plane.id == engineId) return plane;
    }
  }
  if (!AIEngine.IsValidEngine(engineId)) return null;
  return {
    id = engineId,
    capacity = AIEngine.GetCapacity(engineId),
    speed = AIEngine.GetMaxSpeed(engineId),
    price = AIEngine.GetPrice(engineId),
    runningCost = AIEngine.GetRunningCost(engineId),
    maxOrderDistance = AIEngine.GetMaximumOrderDistance(engineId),
    ageYears = AIEngine.GetMaxAge(engineId) / 365,
    mailCapacity = -1,
    isBig = false,
  };
}
