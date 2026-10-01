/* Module AIR extrait de builder_air.nut (R11) : revenus C119 et economie physique C121, choix moteur C121. */
/* Revenu par passager transporte. Sous V92, la soute connue remplace le forfait de 15 % :
 * elle est remplie dans la meme proportion que la cabine. Sans mesure, le forfait reste. */
function OpexAirFarePerPax(catalog, plane, distance, incomeDays)
{
  local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, distance, incomeDays);
  local totalIncomePerUnit = paxIncome;
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, distance, incomeDays);
    local mailPct = 15;
    if (V92_AIR_SERVICE_CHOICE && plane != null && ("mailCapacity" in plane)
        && plane.mailCapacity >= 0 && plane.capacity > 0) {
      mailPct = (plane.mailCapacity * 100) / plane.capacity;
    }
    totalIncomePerUnit = paxIncome + (mailIncome * mailPct) / 100;
  }
  return (totalIncomePerUnit * AIR_PAX_REVENUE_CALIBRATION_PCT) / 100.0;
}

/* C119 : temps de paiement uniquement, separe du cycle AIR. */
function OpexC119AirIncomeDays(plane, flightDistance)
{
  if (plane == null || !("id" in plane)) return 1;
  local speed = (("speed" in plane) && plane.speed > 0) ? plane.speed : 0;
  if (speed <= 0) {
    if (!AIEngine.IsValidEngine(plane.id)) return 1;
    speed = AIEngine.GetMaxSpeed(plane.id);
  }
  if (speed < 1) speed = 1;
  local dayLengthFactor = ("GetDayLengthFactor" in AIDate) ? AIDate.GetDayLengthFactor() : 1;
  if (dayLengthFactor < 1) dayLengthFactor = 1;
  local days = ((flightDistance + 30) * 664) / (speed * 24 * dayLengthFactor);
  return days > 0 ? days : 1;
}

/* C121 : type physique de l'aeroport a une extremite du plan. */
function OpexC121EndpointAirportType(plan, which)
{
  if (plan == null || !("airport" in plan) || plan.airport == null) return AIAirport.AT_SMALL;
  local site = which == 0 ? plan.siteA : plan.siteB;
  local reused = which == 0 ? (("reuseA" in plan) && plan.reuseA) : (("reuseB" in plan) && plan.reuseB);
  if (reused && site != null && ("anchor" in site) && AIAirport.IsAirportTile(site.anchor)) {
    return AIAirport.GetAirportType(site.anchor);
  }
  return plan.airport.type;
}

/* C121 : socle physique d'un leg. Ce helper est partage avec la sonde C117
 * afin que le residu appris compare exactement la meme cinematique que celle
 * utilisee au scoring. Aucun terme appris ne depend du moteur. */
function OpexC121PhysicalOneWayDaysFromSpeed(distance, speed, typeA, typeB,
                                             groundTiles = -1.0, ticksPerDay = 0.0)
{
  if (distance <= 0 || speed <= 0) return null;
  local effectiveSpeed = speed.tofloat();
  if (effectiveSpeed < 1.0) effectiveSpeed = 1.0;
  local flightDays = distance.tofloat() / (0.036 * effectiveSpeed);
  local ground = groundTiles;
  if (ground < 0.0) {
    ground = 8.0;
    if (typeA != null && typeB != null && AIAirport.IsValidAirportType(typeA)
        && AIAirport.IsValidAirportType(typeB)) {
      ground = (AIAirport.GetAirportWidth(typeA) + AIAirport.GetAirportHeight(typeA)
                + AIAirport.GetAirportWidth(typeB) + AIAirport.GetAirportHeight(typeB)).tofloat();
      ground = ground * 2.0 / 3.0;
    }
  }
  local tpd = ticksPerDay > 0.0 ? ticksPerDay : OpexTicksPerDay(null);
  local taxiSpeed = effectiveSpeed < 50.0 ? effectiveSpeed : 50.0;
  local maneuverDays = ground * OpexDaysPerTile(taxiSpeed, tpd) + 300.0 / tpd;
  local oneWayDays = flightDays + maneuverDays;
  if (oneWayDays < 1.0) oneWayDays = 1.0;
  return { flightDays = flightDays, maneuverDays = maneuverDays, oneWayDays = oneWayDays };
}

function OpexC121PhysicalOneWayDays(distance, engineId, typeA, typeB)
{
  if (distance <= 0 || !AIEngine.IsValidEngine(engineId)) return null;
  return OpexC121PhysicalOneWayDaysFromSpeed(
      distance, AIEngine.GetMaxSpeed(engineId), typeA, typeB);
}

/* Station reutilisee d'un endpoint de plan. Un site neuf n'a volontairement
 * aucun delai appris : il reste sur le cold-start physique. */
function OpexC121HubStationId(site, reused)
{
  if (!reused || site == null) return -1;
  local stationId = ("stationId" in site) ? site.stationId : -1;
  if (!AIStation.IsValidStation(stationId) && ("anchor" in site)
      && AIMap.IsValidTile(site.anchor)) {
    stationId = AIStation.GetStationID(site.anchor);
  }
  return AIStation.IsValidStation(stationId) ? stationId : -1;
}

function OpexC121HubDelayState(stationId)
{
  if (!AIStation.IsValidStation(stationId) || !(stationId in C121_AIR_HUB_DELAY_STATE)) return null;
  local state = C121_AIR_HUB_DELAY_STATE[stationId];
  if (state == null || !("lastUpdate" in state) || state.lastUpdate < 0
      || !("lastWindowN" in state) || state.lastWindowN < C121_AIR_HUB_DELAY_MIN_OBS) return null;
  return state;
}

function OpexC121HubDelayDays(stationId)
{
  local state = OpexC121HubDelayState(stationId);
  return state != null && ("days" in state) && state.days > 0.0 ? state.days : 0.0;
}

/* Invariants de projet C121 : calcules une seule fois avant le scan moteur.
 * Aucun champ ci-dessous ne depend du moteur ni du nombre d'avions. */
function OpexC121PrepareEngineStatic(catalog, plan)
{
  if (catalog == null || plan == null || !("c121Demand" in plan)
      || !("siteA" in plan) || !("siteB" in plan)
      || !("airport" in plan) || plan.airport == null) return null;
  if (("c121EngineStatic" in plan) && plan.c121EngineStatic != null) {
    return plan.c121EngineStatic;
  }
  local typeA = OpexC121EndpointAirportType(plan, 0);
  local typeB = OpexC121EndpointAirportType(plan, 1);
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  local stationA = OpexC121HubStationId(plan.siteA, reuseA);
  local stationB = OpexC121HubStationId(plan.siteB, reuseB);
  local delayStateA = OpexC121HubDelayState(stationA);
  local delayStateB = OpexC121HubDelayState(stationB);
  local paymentDistance = AIMap.DistanceManhattan(plan.siteA.anchor, plan.siteB.anchor);
  if (paymentDistance < 1) paymentDistance = plan.distance;
  local newAirportCount = (reuseA ? 0 : 1) + (reuseB ? 0 : 1);
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local demand = plan.c121Demand;
  local decisionKDec = OpexC69CachedKDec();
  if (decisionKDec < 0) decisionKDec = 0;
  local runwayServiceDaysA = OpexC121AirportRunwayServiceDays(typeA);
  local runwayServiceDaysB = OpexC121AirportRunwayServiceDays(typeB);
  local emptyService = {
    pickupRate = 0.0, paxRate = 0.0, mailRate = 0.0,
    paxIncome = 0.0, mailIncome = 0.0, lines = 0, vehicles = 0
  };
  local serviceA = ("c121ServiceA" in plan) ? plan.c121ServiceA : emptyService;
  local serviceB = ("c121ServiceB" in plan) ? plan.c121ServiceB : emptyService;
  local runwayRateA = runwayServiceDaysA > 0.0 ? 1.0 / runwayServiceDaysA : 0.0;
  local runwayRateB = runwayServiceDaysB > 0.0 ? 1.0 / runwayServiceDaysB : 0.0;
  local currentPaxRatingA = ("currentPaxRatingA" in demand) ? demand.currentPaxRatingA : 0;
  local currentPaxRatingB = ("currentPaxRatingB" in demand) ? demand.currentPaxRatingB : 0;
  local currentMailRatingA = ("currentMailRatingA" in demand) ? demand.currentMailRatingA : 0;
  local currentMailRatingB = ("currentMailRatingB" in demand) ? demand.currentMailRatingB : 0;
  local paxCompetitionA = ("paxCompetitionA" in demand) ? demand.paxCompetitionA : null;
  local paxCompetitionB = ("paxCompetitionB" in demand) ? demand.paxCompetitionB : null;
  local mailCompetitionA = ("mailCompetitionA" in demand) ? demand.mailCompetitionA : null;
  local mailCompetitionB = ("mailCompetitionB" in demand) ? demand.mailCompetitionB : null;
  local paxRawA = ("paxRawA" in demand) ? demand.paxRawA : demand.paxA;
  local paxRawB = ("paxRawB" in demand) ? demand.paxRawB : demand.paxB;
  local mailRawA = ("mailRawA" in demand) ? demand.mailRawA : demand.mailA;
  local mailRawB = ("mailRawB" in demand) ? demand.mailRawB : demand.mailB;
  local existingPaxBeforeA = reuseA ? OpexC121ExistingMonthlyBefore(
      paxRawA, currentPaxRatingA, paxCompetitionA,
      serviceA.pickupRate, serviceA.paxRate, runwayRateA) : 0.0;
  local existingPaxBeforeB = reuseB ? OpexC121ExistingMonthlyBefore(
      paxRawB, currentPaxRatingB, paxCompetitionB,
      serviceB.pickupRate, serviceB.paxRate, runwayRateB) : 0.0;
  local existingMailBeforeA = reuseA ? OpexC121ExistingMonthlyBefore(
      mailRawA, currentMailRatingA, mailCompetitionA,
      serviceA.pickupRate, serviceA.mailRate, runwayRateA) : 0.0;
  local existingMailBeforeB = reuseB ? OpexC121ExistingMonthlyBefore(
      mailRawB, currentMailRatingB, mailCompetitionB,
      serviceB.pickupRate, serviceB.mailRate, runwayRateB) : 0.0;
  local maneuverGroundTiles = 8.0;
  if (AIAirport.IsValidAirportType(typeA) && AIAirport.IsValidAirportType(typeB)) {
    maneuverGroundTiles = (AIAirport.GetAirportWidth(typeA) + AIAirport.GetAirportHeight(typeA)
        + AIAirport.GetAirportWidth(typeB) + AIAirport.GetAirportHeight(typeB)).tofloat();
    maneuverGroundTiles = maneuverGroundTiles * 2.0 / 3.0;
  }
  local state = {
    airportTypeA = typeA, airportTypeB = typeB,
    hubDelayA = delayStateA != null ? delayStateA.days : 0.0,
    hubDelayB = delayStateB != null ? delayStateB.days : 0.0,
    hubDelayObsA = delayStateA != null ? delayStateA.observations : 0,
    hubDelayObsB = delayStateB != null ? delayStateB.observations : 0,
    hubDelayWindowObsA = delayStateA != null ? delayStateA.lastWindowN : 0,
    hubDelayWindowObsB = delayStateB != null ? delayStateB.lastWindowN : 0,
    hubDelayVarianceA = delayStateA != null ? delayStateA.variance : 0.0,
    hubDelayVarianceB = delayStateB != null ? delayStateB.variance : 0.0,
    paymentDistance = paymentDistance,
    newAirportCount = newAirportCount,
    airportMaintenanceAnnual = infrastructureMaintenance
        ? 12 * newAirportCount * plan.airport.maintenance : 0,
    airportAmortAnnual = (newAirportCount * plan.airport.price * INFRA_AMORT_PCT / 100) / 30,
    airportCapital = newAirportCount * plan.airport.price,
    decisionKDec = decisionKDec,
    statueRatingA = OpexC121StatueRatingPoints(plan.siteA.town),
    statueRatingB = OpexC121StatueRatingPoints(plan.siteB.town),
    runwayServiceDaysA = runwayServiceDaysA,
    runwayServiceDaysB = runwayServiceDaysB,
    runwayRateA = runwayRateA,
    runwayRateB = runwayRateB,
    maneuverGroundTiles = maneuverGroundTiles,
    ticksPerDay = OpexTicksPerDay(null),
    paxRawA = paxRawA, paxRawB = paxRawB,
    mailRawA = mailRawA, mailRawB = mailRawB,
    existingPaxBeforeA = existingPaxBeforeA, existingPaxBeforeB = existingPaxBeforeB,
    existingMailBeforeA = existingMailBeforeA, existingMailBeforeB = existingMailBeforeB,
    existingPaxIncomeA = serviceA.paxIncome, existingPaxIncomeB = serviceB.paxIncome,
    existingMailIncomeA = serviceA.mailIncome, existingMailIncomeB = serviceB.mailIncome,
  };
  plan.c121EngineStatic <- state;
  return state;
}

/* C121 : cycle physique + adaptation stationnaire distinct du temps de paiement.
 * Un tour complet contient deux legs physiques et une contribution de delai
 * propre a chaque hub. Les deux delais sont identiques pour tous les moteurs. */
function OpexC121AirTripModel(plan, plane)
{
  if (plan == null || plane == null || !("distance" in plan) || plan.distance <= 0
      || !("id" in plane)) return null;
  local engineStatic = ("c121EngineStatic" in plan) ? plan.c121EngineStatic : null;
  local typeA = engineStatic != null ? engineStatic.airportTypeA : OpexC121EndpointAirportType(plan, 0);
  local typeB = engineStatic != null ? engineStatic.airportTypeB : OpexC121EndpointAirportType(plan, 1);
  local speed = (("speed" in plane) && plane.speed > 0) ? plane.speed : 0;
  if (speed <= 0) {
    if (!AIEngine.IsValidEngine(plane.id)) return null;
    speed = AIEngine.GetMaxSpeed(plane.id);
  }
  local physical = engineStatic != null
      ? OpexC121PhysicalOneWayDaysFromSpeed(plan.distance, speed, typeA, typeB,
          engineStatic.maneuverGroundTiles, engineStatic.ticksPerDay)
      : OpexC121PhysicalOneWayDaysFromSpeed(plan.distance, speed, typeA, typeB);
  if (physical == null) return null;
  local delayStateA = null;
  local delayStateB = null;
  local hubDelayA = 0.0;
  local hubDelayB = 0.0;
  if (engineStatic != null) {
    hubDelayA = engineStatic.hubDelayA;
    hubDelayB = engineStatic.hubDelayB;
  } else {
    local reuseA = ("reuseA" in plan) && plan.reuseA;
    local reuseB = ("reuseB" in plan) && plan.reuseB;
    local stationA = OpexC121HubStationId(plan.siteA, reuseA);
    local stationB = OpexC121HubStationId(plan.siteB, reuseB);
    delayStateA = OpexC121HubDelayState(stationA);
    delayStateB = OpexC121HubDelayState(stationB);
    hubDelayA = delayStateA != null ? delayStateA.days : 0.0;
    hubDelayB = delayStateB != null ? delayStateB.days : 0.0;
  }
  local roundTripDays = 2.0 * physical.oneWayDays + hubDelayA + hubDelayB;
  local oneWayDays = roundTripDays / 2.0;
  return {
    flightDays = physical.flightDays, maneuverDays = physical.maneuverDays,
    physicalOneWayDays = physical.oneWayDays,
    hubDelayA = hubDelayA, hubDelayB = hubDelayB,
    hubDelayObsA = engineStatic != null ? engineStatic.hubDelayObsA : (delayStateA != null ? delayStateA.observations : 0),
    hubDelayObsB = engineStatic != null ? engineStatic.hubDelayObsB : (delayStateB != null ? delayStateB.observations : 0),
    hubDelayWindowObsA = engineStatic != null ? engineStatic.hubDelayWindowObsA : (delayStateA != null ? delayStateA.lastWindowN : 0),
    hubDelayWindowObsB = engineStatic != null ? engineStatic.hubDelayWindowObsB : (delayStateB != null ? delayStateB.lastWindowN : 0),
    hubDelayVarianceA = engineStatic != null ? engineStatic.hubDelayVarianceA : (delayStateA != null ? delayStateA.variance : 0.0),
    hubDelayVarianceB = engineStatic != null ? engineStatic.hubDelayVarianceB : (delayStateB != null ? delayStateB.variance : 0.0),
    oneWayDays = oneWayDays, roundTripDays = roundTripDays,
    airportTypeA = typeA, airportTypeB = typeB,
  };
}

/* C121 : temps de service de la ressource piste partagee, derive du source
 * OpenTTD 15.3. Retour 0 si le type n'est pas encore modele : mieux vaut ne
 * pas plafonner que fabriquer une capacite d'aeroport.
 *
 * AT_LARGE (City Airport) possede un unique bloc RunwayInOut. AirportSetBlocks
 * reserve le bloc AVANT d'entrer dans la position suivante et AirportClearBlock
 * le libere des que l'avion atteint la premiere position hors bloc. Le chemin
 * occupe est donc 8->9->10->11 au decollage et 13->14->15->17 a
 * l'atterrissage. Les coordonnees airport_movement donnent, par visite
 * complete, 260 pas pixel axiaux et 30 diagonaux.
 *
 * NoAI n'expose pas l'acceleration AIR. Pour rester mecanique et conservateur,
 * tous les segments occupes sont avances a SPEED_LIMIT_TAXI=50. Dans le vieux
 * mouvement vehicule, UpdateAircraftSpeed est appele deux fois/tick et
 * GetOldAdvanceSpeed applique speed*3/4 (division entiere) sur les axes. */
function OpexC121AirportRunwayServiceDays(airportType)
{
  if (airportType != AIAirport.AT_LARGE) return 0.0;
  local ticksPerDay = OpexTicksPerDay(null).tofloat();
  if (ticksPerDay <= 0.0) return 0.0;
  local taxiSpeed = 50;
  local axialProgress = ((taxiSpeed * 3) / 4).tofloat();
  local diagonalProgress = taxiSpeed.tofloat();
  local axialPixelsPerDay = 2.0 * axialProgress * ticksPerDay / 256.0;
  local diagonalPixelsPerDay = 2.0 * diagonalProgress * ticksPerDay / 256.0;
  if (axialPixelsPerDay <= 0.0 || diagonalPixelsPerDay <= 0.0) return 0.0;
  return 260.0 / axialPixelsPerDay + 30.0 / diagonalPixelsPerDay;
}

/* C121 : service AIR deja present a une gare, exprime en visites/jour et
 * capacite/jour. Cette photo est calculee une fois par plan puis reutilisee
 * pour tous les nombres d'avions candidats. */
function OpexC121ExistingStationService(catalog, site, lines)
{
  local out = {
    pickupRate = 0.0, paxRate = 0.0, mailRate = 0.0,
    paxIncome = 0.0, mailIncome = 0.0,
    lines = 0, vehicles = 0
  };
  local paxIncomeWeighted = 0.0;
  local paxIncomeWeight = 0.0;
  local mailIncomeWeighted = 0.0;
  local mailIncomeWeight = 0.0;
  if (catalog == null || site == null || lines == null || !("anchor" in site)
      || !AIMap.IsValidTile(site.anchor)) return out;
  local stationId = ("stationId" in site) ? site.stationId : AIStation.GetStationID(site.anchor);
  if (!AIStation.IsValidStation(stationId)) return out;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "air") continue;
    local sidA = ("stationA" in line) ? OpexAirLineStationId(line, 0) : -1;
    local sidB = ("stationB" in line) ? OpexAirLineStationId(line, 1) : -1;
    if (sidA != stationId && sidB != stationId) continue;
    local distance = ("distance" in line) ? line.distance : 0;
    if (distance <= 0 && ("stationA" in line) && ("stationB" in line)) {
      distance = OpexFlightDistance(line.stationA, line.stationB);
    }
    if (distance <= 0) continue;
    local typeA = (("stationA" in line) && AIAirport.IsAirportTile(line.stationA))
        ? AIAirport.GetAirportType(line.stationA) : AIAirport.AT_SMALL;
    local typeB = (("stationB" in line) && AIAirport.IsAirportTile(line.stationB))
        ? AIAirport.GetAirportType(line.stationB) : AIAirport.AT_SMALL;
    local countedLine = false;
    local vehicles = ("vehicles" in line) && line.vehicles != null
        ? line.vehicles : ((("vehicle" in line) && AIVehicle.IsValidVehicle(line.vehicle)) ? [line.vehicle] : []);
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
      local engine = AIVehicle.GetEngineType(v);
      if (!AIEngine.IsValidEngine(engine)) continue;
      local physical = OpexC121PhysicalOneWayDays(distance, engine, typeA, typeB);
      if (physical == null) continue;
      local hubDelayA = OpexC121HubDelayDays(sidA);
      local hubDelayB = OpexC121HubDelayDays(sidB);
      local roundTrip = 2.0 * physical.oneWayDays + hubDelayA + hubDelayB;
      if (roundTrip <= 0.0) continue;
      local rate = 1.0 / roundTrip;
      local paxCap = AIVehicle.GetCapacity(v, catalog.paxCargo);
      if (paxCap < 0) paxCap = 0;
      local mailCap = (("mailCargo" in catalog) && catalog.mailCargo >= 0)
          ? AIVehicle.GetCapacity(v, catalog.mailCargo) : 0;
      if (mailCap < 0) mailCap = 0;
      local paymentDistance = distance;
      if (("stationA" in line) && ("stationB" in line)
          && AIMap.IsValidTile(line.stationA) && AIMap.IsValidTile(line.stationB)) {
        paymentDistance = AIMap.DistanceManhattan(line.stationA, line.stationB);
      }
      local speed = AIEngine.GetMaxSpeed(engine);
      if (speed < 1) speed = 1;
      local dayLengthFactor = ("GetDayLengthFactor" in AIDate) ? AIDate.GetDayLengthFactor() : 1;
      if (dayLengthFactor < 1) dayLengthFactor = 1;
      local incomeDays = ((distance + 30) * 664) / (speed * 24 * dayLengthFactor);
      if (incomeDays < 1) incomeDays = 1;
      local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, paymentDistance, incomeDays);
      local paxFlow = paxCap * rate;
      if (paxIncome >= 0 && paxFlow > 0.0) {
        paxIncomeWeighted += paxFlow * paxIncome;
        paxIncomeWeight += paxFlow;
      }
      local mailFlow = mailCap * rate;
      if (("mailCargo" in catalog) && catalog.mailCargo >= 0 && mailFlow > 0.0) {
        local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, paymentDistance, incomeDays);
        if (mailIncome >= 0) {
          mailIncomeWeighted += mailFlow * mailIncome;
          mailIncomeWeight += mailFlow;
        }
      }
      out.pickupRate += rate;
      out.paxRate += paxCap * rate;
      out.mailRate += mailCap * rate;
      out.vehicles++;
      countedLine = true;
    }
    if (countedLine) out.lines++;
  }
  if (paxIncomeWeight > 0.0) out.paxIncome = paxIncomeWeighted / paxIncomeWeight;
  if (mailIncomeWeight > 0.0) out.mailIncome = mailIncomeWeighted / mailIncomeWeight;
  return out;
}

/* Debit mensuel que les lignes deja presentes peuvent conserver avant l'ajout
 * du candidat. La demande allouee vient de la note observee de la gare; la
 * capacite vient du snapshot agrege et de la piste. */
function OpexC121ExistingMonthlyBefore(rawMonthly, currentRating, competition,
                                       servicePickupRate, serviceCargoRate, runwayRate)
{
  if (rawMonthly <= 0 || servicePickupRate <= 0.0 || serviceCargoRate <= 0.0) return 0.0;
  local runwayScale = 1.0;
  if (runwayRate > 0.0 && servicePickupRate > runwayRate) runwayScale = runwayRate / servicePickupRate;
  local allocated = OpexC121StationAllocatedMonthly(rawMonthly, currentRating, competition);
  local capacityMonthly = serviceCargoRate * runwayScale * 30.4;
  return allocated < capacityMonthly ? allocated : capacityMonthly;
}

/* C121 : points de rating OpenTTD calculables avant construction.
 * Aucune ancre STATION_RATING_PCT n'entre ici. */
function OpexC121PickupRatingPoints(headwayDays)
{
  if (headwayDays <= 0.0) return 0.0;
  /* OpenTTD 15.3 met le rating a jour tous les 185 ticks, soit 2,5 jours
   * avec 74 ticks/jour. time_since_pickup parcourt donc les paliers
   * 130/95/50/25/0 aux seuils 3/6/12/21 updates entre deux visites.
   * Le projet a besoin du rating moyen sur le cycle, pas du palier atteint
   * juste avant la visite suivante : integrer exactement ces marches sur le
   * headway evite de simuler les updates une par une. */
  local h = headwayDays.tofloat();
  if (h <= 7.5) return 130.0;
  local area = 7.5 * 130.0;
  if (h <= 15.0) return (area + (h - 7.5) * 95.0) / h;
  area += 7.5 * 95.0;
  if (h <= 30.0) return (area + (h - 15.0) * 50.0) / h;
  area += 15.0 * 50.0;
  if (h <= 52.5) return (area + (h - 30.0) * 25.0) / h;
  area += 22.5 * 25.0;
  return area / h;
}

function OpexC121StockRatingPoints(waiting)
{
  local points = -90;
  if (waiting <= 1500) points += 55;
  if (waiting <= 1000) points += 35;
  if (waiting <= 600) points += 10;
  if (waiting <= 300) points += 20;
  if (waiting <= 100) points += 10;
  return points;
}

function OpexC121SpeedRatingPoints(plane)
{
  if (plane == null || !("id" in plane)) return 0;
  /* AIEngine.GetMaxSpeed AIR est deja divise par vehicle.plane_speed.
   * Reconstituer cached_max_speed avant GetSpeedOldUnits() = speed * 10 / 128. */
  local speed = (("speed" in plane) && plane.speed > 0) ? plane.speed.tofloat() : 0.0;
  if (speed <= 0.0) {
    if (!AIEngine.IsValidEngine(plane.id)) return 0;
    speed = AIEngine.GetMaxSpeed(plane.id).tofloat();
  }
  local oldSpeed = (speed
      * OpexPlaneSpeedDivisor() * 10.0 / 128.0).tointeger();
  if (oldSpeed > 255) oldSpeed = 255;
  return oldSpeed > 85 ? (oldSpeed - 85) / 4 : 0;
}

function OpexC121StatueRatingPoints(town)
{
  if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) return 0;
  return AITown.HasStatue(town.id) ? 26 : 0;
}

/* Le rating vise ici l'etat de service d'un vehicule neuf (+33 points d'age).
 * Pour le stock, si une visite peut vider le cargo produit depuis la visite
 * precedente, waitingUpper est une borne mecanique du stock. Sinon le backlog
 * est structurellement croissant et prend la penalite maximale. La recherche
 * est finie car la note est un entier 0..255. Si deux paliers oscillent autour
 * de la saturation, l'etat moyen est fixe par conservation du flux
 * (production offerte = capacite de service), sans coefficient appris. */
function OpexC121RatingTarget(plane, town, capturableMonthly, headwayDays, capacityPerVisit,
                             baseWithoutPickup = null, pointsOnly = false)
{
  local base = baseWithoutPickup;
  if (base == null) {
    base = OpexC121SpeedRatingPoints(plane) + 33 + OpexC121StatueRatingPoints(town);
  }
  base += OpexC121PickupRatingPoints(headwayDays);
  local rating = 175;
  local previous = null;
  local cycled = false;
  /* target(rating) est antitone : plus de rating => plus de stock => un terme
   * stock qui ne peut qu'empirer. Sur une echelle totalement ordonnee, une
   * iteration antitone converge vers un point fixe ou un cycle de periode 2 ;
   * les six paliers de stock bornent en plus strictement le nombre d'etats.
   * Eviter ici la table `seen` supprime une allocation/hash dans le coeur du
   * scan flotte (jusqu'a quatre ratings par N). */
  for (local iter = 0; iter < 8; iter++) {
    local offered = capturableMonthly > 0
        ? capturableMonthly * rating.tofloat() / 255.0 : 0.0;
    local waitingUpper = offered * headwayDays / 30.4;
    /* OpenTTD 15.3 note le stock via ge->max_waiting_cargo = waiting_avg.
     * Meme en distribution manuelle, num_dests + 1 vaut au moins 2 :
     * waiting_avg <= waiting / 2. Garder waitingUpper pour savoir si une
     * visite vide physiquement la gare, mais appliquer au rating la borne
     * source waiting/2 plutot que le stock accumule sur tout le headway. */
    local ratingWaiting = waitingUpper / 2.0;
    local stockPoints = (capacityPerVisit > 0 && waitingUpper <= capacityPerVisit)
        ? OpexC121StockRatingPoints(ratingWaiting) : -90;
    local target = base + stockPoints;
    if (target < 0) target = 0;
    if (target > 255) target = 255;
    if (target == rating) break;
    if (previous != null && target == previous) {
      cycled = true;
      /* Si les paliers oscillent autour de la saturation, la note moyenne est
       * imposee par la conservation du flux : production offerte = capacite. */
      if (capturableMonthly > 0 && headwayDays > 0 && capacityPerVisit > 0) {
        rating = (capacityPerVisit * 30.4 * 255.0
            / (capturableMonthly * headwayDays)).tointeger();
        if (rating < 0) rating = 0;
        if (rating > 255) rating = 255;
      } else if (target < rating) {
        rating = target;
      }
      break;
    }
    previous = rating;
    rating = target;
  }
  local offered = capturableMonthly > 0
      ? capturableMonthly * rating.tofloat() / 255.0 : 0.0;
  local waitingUpper = offered * headwayDays / 30.4;
  if (pointsOnly) return rating;
  return {
    points = rating, offered = offered, waitingUpper = waitingUpper,
    ratingWaiting = waitingUpper / 2.0, cycled = cycled
  };
}

/* Nombre maximal de points de flotte qu'il est utile de scanner :
 * - assez de capacite directionnelle pour toute la production brute ;
 * - assez de frequence pour atteindre le meilleur palier de ramassage (<7,5 j).
 * Au-dela, ni la demande brute ni le rating de ramassage ne peuvent augmenter.
 * Pas de borne globale historique ni de cadence copiee d'un autre AI. */
function OpexC121AirFleetScanCap(plan, roundTripDays, paxCapacity, mailCapacity)
{
  if (plan == null || !("c121Demand" in plan) || roundTripDays <= 0 || paxCapacity <= 0) return 1;
  local demand = plan.c121Demand;
  local paxPerPlaneDirection = paxCapacity * 30.4 / roundTripDays;
  local maxPax = demand.paxA > demand.paxB ? demand.paxA : demand.paxB;
  local cap = OpexCeilDiv(maxPax, paxPerPlaneDirection);
  local frequencyPlanes = OpexCeilDiv(roundTripDays, 7.5);
  if (frequencyPlanes > cap) cap = frequencyPlanes;
  if (mailCapacity > 0) {
    local mailPerPlaneDirection = mailCapacity * 30.4 / roundTripDays;
    local maxMail = demand.mailA > demand.mailB ? demand.mailA : demand.mailB;
    local mailPlanes = OpexCeilDiv(maxMail, mailPerPlaneDirection);
    if (mailPlanes > cap) cap = mailPlanes;
  }
  return cap > 0 ? cap : 1;
}

/* C121 : economie PASS/MAIL directionnelle, sans forfait mail ni plein retour. */
function OpexC121AirEconomics(catalog, plan, plane, paxCapacity, mailCapacity, fixedPlanes = 0,
                             decisionOnly = false, decisionScoreFloor = null)
{
  if (catalog == null || plan == null || plane == null || !("c121Demand" in plan)) return null;
  if (paxCapacity <= 0 || mailCapacity < 0 || catalog.paxCargo < 0) return null;
  /* Cold start C121 : tant que la sous-capacite MAIL exacte du refit PASS n'a
   * jamais ete observee, mailCapacity=0 signifie explicitement PASS-only. Ne
   * pas inventer de ratio MAIL et ne pas faire participer le cargo MAIL aux
   * ratings, parts de route ou bornes de flotte. */
  local useMail = mailCapacity > 0 && ("mailCargo" in catalog) && catalog.mailCargo >= 0;
  local trip = OpexC121AirTripModel(plan, plane);
  if (trip == null || trip.roundTripDays <= 0) return null;
  local engineStatic = ("c121EngineStatic" in plan) ? plan.c121EngineStatic : null;
  local paymentDistance = engineStatic != null ? engineStatic.paymentDistance
      : AIMap.DistanceManhattan(plan.siteA.anchor, plan.siteB.anchor);
  if (paymentDistance < 1) paymentDistance = plan.distance;
  local incomeDays = OpexC119AirIncomeDays(plane, plan.distance);
  local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, paymentDistance, incomeDays);
  local mailIncome = useMail ? AICargo.GetCargoIncome(catalog.mailCargo, paymentDistance, incomeDays) : 0;
  if (paxIncome < 0 || (useMail && mailIncome < 0)) return null;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  local newAirportCount = engineStatic != null ? engineStatic.newAirportCount : (reuseA ? 0 : 1) + (reuseB ? 0 : 1);
  local airportMaintenanceAnnual = engineStatic != null ? engineStatic.airportMaintenanceAnnual
      : (AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0
          ? 12 * newAirportCount * plan.airport.maintenance : 0);
  local airportAmortAnnual = engineStatic != null ? engineStatic.airportAmortAnnual
      : (newAirportCount * plan.airport.price * INFRA_AMORT_PCT / 100) / 30;
  local lifeYears = (("ageYears" in plane) && plane.ageYears > 0)
      ? plane.ageYears : (AIEngine.GetMaxAge(plane.id) / 365);
  local vehicleAmortPerPlane = lifeYears > 0 ? plane.price / lifeYears : 0;
  local airportCapital = engineStatic != null ? engineStatic.airportCapital : newAirportCount * plan.airport.price;
  local fleetScanCap = OpexC121AirFleetScanCap(plan, trip.roundTripDays, paxCapacity, mailCapacity);
  local maxAllowed = fixedPlanes > 0 ? fixedPlanes : fleetScanCap;
  local firstPlanes = fixedPlanes > 0 ? fixedPlanes : 1;
  local best = null;
  local scoreBest = null;
  local decisionKDec = engineStatic != null ? engineStatic.decisionKDec : OpexC69CachedKDec();
  if (decisionKDec < 0) decisionKDec = 0;
  local demand = plan.c121Demand;
  local emptyService = { pickupRate = 0.0, paxRate = 0.0, mailRate = 0.0, lines = 0, vehicles = 0 };
  local serviceA = ("c121ServiceA" in plan) ? plan.c121ServiceA : emptyService;
  local serviceB = ("c121ServiceB" in plan) ? plan.c121ServiceB : emptyService;
  local speedRating = OpexC121SpeedRatingPoints(plane);
  local ratingBaseA = speedRating + 33
      + (engineStatic != null ? engineStatic.statueRatingA : OpexC121StatueRatingPoints(plan.siteA.town));
  local ratingBaseB = speedRating + 33
      + (engineStatic != null ? engineStatic.statueRatingB : OpexC121StatueRatingPoints(plan.siteB.town));
  local runwayServiceDaysA = engineStatic != null ? engineStatic.runwayServiceDaysA
      : OpexC121AirportRunwayServiceDays(trip.airportTypeA);
  local runwayServiceDaysB = engineStatic != null ? engineStatic.runwayServiceDaysB
      : OpexC121AirportRunwayServiceDays(trip.airportTypeB);
  local runwayRateA = engineStatic != null ? engineStatic.runwayRateA
      : (runwayServiceDaysA > 0.0 ? 1.0 / runwayServiceDaysA : 0.0);
  local runwayRateB = engineStatic != null ? engineStatic.runwayRateB
      : (runwayServiceDaysB > 0.0 ? 1.0 / runwayServiceDaysB : 0.0);
  local paxRawA = engineStatic != null ? engineStatic.paxRawA : (("paxRawA" in demand) ? demand.paxRawA : demand.paxA);
  local paxRawB = engineStatic != null ? engineStatic.paxRawB : (("paxRawB" in demand) ? demand.paxRawB : demand.paxB);
  local mailRawA = useMail ? (engineStatic != null ? engineStatic.mailRawA
      : (("mailRawA" in demand) ? demand.mailRawA : demand.mailA)) : 0;
  local mailRawB = useMail ? (engineStatic != null ? engineStatic.mailRawB
      : (("mailRawB" in demand) ? demand.mailRawB : demand.mailB)) : 0;
  local realizationFactor = OpexC121RealizationFactor(plan);
  local existingPaxBeforeA = engineStatic != null ? engineStatic.existingPaxBeforeA : 0.0;
  local existingPaxBeforeB = engineStatic != null ? engineStatic.existingPaxBeforeB : 0.0;
  local existingMailBeforeA = engineStatic != null ? engineStatic.existingMailBeforeA : 0.0;
  local existingMailBeforeB = engineStatic != null ? engineStatic.existingMailBeforeB : 0.0;
  local existingPaxIncomeA = engineStatic != null ? engineStatic.existingPaxIncomeA : 0.0;
  local existingPaxIncomeB = engineStatic != null ? engineStatic.existingPaxIncomeB : 0.0;
  local existingMailIncomeA = engineStatic != null ? engineStatic.existingMailIncomeA : 0.0;
  local existingMailIncomeB = engineStatic != null ? engineStatic.existingMailIncomeB : 0.0;
  local rawMaxRevenueUpper = (12.0 * (paxRawA + paxRawB).tofloat() * paxIncome
      + 12.0 * (mailRawA + mailRawB).tofloat() * mailIncome).tointeger();
  local maxRevenueUpper = (rawMaxRevenueUpper.tofloat() * realizationFactor).tointeger();
  /* Borne exacte pour l'argmax moteur : meme en transportant 100 % de la
   * production brute, sans perte de rating/partage/capacite, le score ne peut
   * depasser ce rendement. Les couts et le capital croissent avec N, donc la
   * borne N=1 domine aussi tous les N suivants. Strict < conserve les egalites,
   * car le chooser departage alors au profit. */
  if (decisionOnly && decisionScoreFloor != null && decisionScoreFloor >= 0.0
      && fixedPlanes <= 0 && plane.price > 0) {
    local upperProfitOne = maxRevenueUpper - (plane.runningCost + airportMaintenanceAnnual)
        - (vehicleAmortPerPlane + airportAmortAnnual);
    local upperCapitalOne = airportCapital + plane.price;
    local upperScoreOne = upperCapitalOne > 0
        ? upperProfitOne.tofloat() * 1000.0 / upperCapitalOne.tofloat() : 0.0;
    if (upperScoreOne < decisionScoreFloor) return null;
  }
  local fleetEvaluated = 0;
  for (local planes = firstPlanes; planes <= maxAllowed; planes++) {
    fleetEvaluated++;
    local requestedCandidatePickupRate = planes.tofloat() / trip.roundTripDays;
    local requestedStationPickupRateA = serviceA.pickupRate + requestedCandidatePickupRate;
    local requestedStationPickupRateB = serviceB.pickupRate + requestedCandidatePickupRate;
    local runwayScaleA = 1.0;
    local runwayScaleB = 1.0;
    if (runwayRateA > 0.0 && requestedStationPickupRateA > runwayRateA) {
      runwayScaleA = runwayRateA / requestedStationPickupRateA;
    }
    if (runwayRateB > 0.0 && requestedStationPickupRateB > runwayRateB) {
      runwayScaleB = runwayRateB / requestedStationPickupRateB;
    }
    /* Une rotation doit franchir les deux aeroports : sa cadence est bornee par
     * l'extremite la plus saturee. Les services deja presents partagent, eux,
     * la ressource locale de leur propre hub. C'est une conservation de debit,
     * pas une decote empirique de revenu. */
    local candidateRunwayScale = runwayScaleA < runwayScaleB ? runwayScaleA : runwayScaleB;
    local candidatePickupRate = requestedCandidatePickupRate * candidateRunwayScale;
    if (candidatePickupRate <= 0.0) continue;
    local existingPickupRateA = serviceA.pickupRate * runwayScaleA;
    local existingPickupRateB = serviceB.pickupRate * runwayScaleB;
    local existingPaxRateA = serviceA.paxRate * runwayScaleA;
    local existingPaxRateB = serviceB.paxRate * runwayScaleB;
    local existingMailRateA = useMail ? serviceA.mailRate * runwayScaleA : 0.0;
    local existingMailRateB = useMail ? serviceB.mailRate * runwayScaleB : 0.0;
    local headwayDays = 1.0 / candidatePickupRate;
    local stationPickupRateA = existingPickupRateA + candidatePickupRate;
    local stationPickupRateB = existingPickupRateB + candidatePickupRate;
    local candidatePaxRate = paxCapacity * candidatePickupRate;
    local candidateMailRate = useMail ? mailCapacity * candidatePickupRate : 0.0;
    local routeSharePaxA = existingPaxRateA > 0.0
        ? candidatePaxRate / (existingPaxRateA + candidatePaxRate) : 1.0;
    local routeSharePaxB = existingPaxRateB > 0.0
        ? candidatePaxRate / (existingPaxRateB + candidatePaxRate) : 1.0;
    local routeShareMailA = useMail
        ? (existingMailRateA > 0.0 ? candidateMailRate / (existingMailRateA + candidateMailRate) : 1.0)
        : 0.0;
    local routeShareMailB = useMail
        ? (existingMailRateB > 0.0 ? candidateMailRate / (existingMailRateB + candidateMailRate) : 1.0)
        : 0.0;
    local stationHeadwayA = stationPickupRateA > 0.0 ? 1.0 / stationPickupRateA : headwayDays;
    local stationHeadwayB = stationPickupRateB > 0.0 ? 1.0 / stationPickupRateB : headwayDays;
    local paxVisitCapA = stationPickupRateA > 0.0
        ? (existingPaxRateA + paxCapacity * candidatePickupRate) / stationPickupRateA : paxCapacity;
    local paxVisitCapB = stationPickupRateB > 0.0
        ? (existingPaxRateB + paxCapacity * candidatePickupRate) / stationPickupRateB : paxCapacity;
    local mailVisitCapA = useMail && stationPickupRateA > 0.0
        ? (existingMailRateA + mailCapacity * candidatePickupRate) / stationPickupRateA : 0.0;
    local mailVisitCapB = useMail && stationPickupRateB > 0.0
        ? (existingMailRateB + mailCapacity * candidatePickupRate) / stationPickupRateB : 0.0;
    local paxRatingA = OpexC121RatingTarget(
        plane, plan.siteA.town, paxRawA, stationHeadwayA, paxVisitCapA, ratingBaseA, decisionOnly);
    local paxRatingB = OpexC121RatingTarget(
        plane, plan.siteB.town, paxRawB, stationHeadwayB, paxVisitCapB, ratingBaseB, decisionOnly);
    local noMailRating = decisionOnly ? 0
        : { points = 0, offered = 0.0, waitingUpper = 0.0, ratingWaiting = 0.0, cycled = false };
    local mailRatingA = useMail ? OpexC121RatingTarget(
        plane, plan.siteA.town, mailRawA, stationHeadwayA, mailVisitCapA, ratingBaseA, decisionOnly) : noMailRating;
    local mailRatingB = useMail ? OpexC121RatingTarget(
        plane, plan.siteB.town, mailRawB, stationHeadwayB, mailVisitCapB, ratingBaseB, decisionOnly) : noMailRating;
    local paxRatingPointsA = decisionOnly ? paxRatingA : paxRatingA.points;
    local paxRatingPointsB = decisionOnly ? paxRatingB : paxRatingB.points;
    local mailRatingPointsA = decisionOnly ? mailRatingA : mailRatingA.points;
    local mailRatingPointsB = decisionOnly ? mailRatingB : mailRatingB.points;
    local stationPaxA = OpexC121StationAllocatedMonthly(
        paxRawA, paxRatingPointsA, ("paxCompetitionA" in demand) ? demand.paxCompetitionA : null);
    local stationPaxB = OpexC121StationAllocatedMonthly(
        paxRawB, paxRatingPointsB, ("paxCompetitionB" in demand) ? demand.paxCompetitionB : null);
    local stationMailA = useMail ? OpexC121StationAllocatedMonthly(
        mailRawA, mailRatingPointsA, ("mailCompetitionA" in demand) ? demand.mailCompetitionA : null) : 0.0;
    local stationMailB = useMail ? OpexC121StationAllocatedMonthly(
        mailRawB, mailRatingPointsB, ("mailCompetitionB" in demand) ? demand.mailCompetitionB : null) : 0.0;
    local offeredPaxA = stationPaxA * routeSharePaxA;
    local offeredPaxB = stationPaxB * routeSharePaxB;
    local offeredMailA = stationMailA * routeShareMailA;
    local offeredMailB = stationMailB * routeShareMailB;
    /* La capacite physique doit employer la cadence effectivement admise par
     * les deux pistes, pas la cadence demandee par N avions. Sinon le cap FTA
     * reduit le rating/partage mais laisse encore transporter du cargo sur des
     * rotations qui ne peuvent pas avoir lieu. */
    local departuresPerDirectionMonth = 30.4 * candidatePickupRate;
    local paxDirectionCapacity = paxCapacity.tofloat() * departuresPerDirectionMonth;
    local mailDirectionCapacity = useMail ? mailCapacity.tofloat() * departuresPerDirectionMonth : 0.0;
    local carriedPaxA = (offeredPaxA < paxDirectionCapacity ? offeredPaxA : paxDirectionCapacity).tointeger();
    local carriedPaxB = (offeredPaxB < paxDirectionCapacity ? offeredPaxB : paxDirectionCapacity).tointeger();
    local carriedMailA = (offeredMailA < mailDirectionCapacity ? offeredMailA : mailDirectionCapacity).tointeger();
    local carriedMailB = (offeredMailB < mailDirectionCapacity ? offeredMailB : mailDirectionCapacity).tointeger();
    local carriedPax = carriedPaxA + carriedPaxB;
    local carriedMail = carriedMailA + carriedMailB;
    /* Externalite C121 : une nouvelle ligne sur une gare existante ne cree pas
     * tout son trafic. Une partie est detournee des lignes deja presentes et la
     * congestion de piste peut aussi reduire leur debit. Comparer le trafic
     * existant avant le candidat a ce qu'il lui reste apres partage, puis
     * valoriser la perte au revenu moyen par unite DES lignes du hub. */
    local existingPaxAfterA = stationPaxA * (1.0 - routeSharePaxA);
    local existingPaxAfterB = stationPaxB * (1.0 - routeSharePaxB);
    local existingPaxCapacityA = existingPaxRateA * 30.4;
    local existingPaxCapacityB = existingPaxRateB * 30.4;
    if (existingPaxAfterA > existingPaxCapacityA) existingPaxAfterA = existingPaxCapacityA;
    if (existingPaxAfterB > existingPaxCapacityB) existingPaxAfterB = existingPaxCapacityB;
    local lostPaxA = existingPaxBeforeA > existingPaxAfterA ? existingPaxBeforeA - existingPaxAfterA : 0.0;
    local lostPaxB = existingPaxBeforeB > existingPaxAfterB ? existingPaxBeforeB - existingPaxAfterB : 0.0;
    local existingMailAfterA = existingMailBeforeA;
    local existingMailAfterB = existingMailBeforeB;
    if (useMail) {
      existingMailAfterA = stationMailA * (1.0 - routeShareMailA);
      existingMailAfterB = stationMailB * (1.0 - routeShareMailB);
      local existingMailCapacityA = existingMailRateA * 30.4;
      local existingMailCapacityB = existingMailRateB * 30.4;
      if (existingMailAfterA > existingMailCapacityA) existingMailAfterA = existingMailCapacityA;
      if (existingMailAfterB > existingMailCapacityB) existingMailAfterB = existingMailCapacityB;
    }
    local lostMailA = existingMailBeforeA > existingMailAfterA ? existingMailBeforeA - existingMailAfterA : 0.0;
    local lostMailB = existingMailBeforeB > existingMailAfterB ? existingMailBeforeB - existingMailAfterB : 0.0;
    local rawCannibalLossAnnual = (12.0 * (lostPaxA * existingPaxIncomeA
        + lostPaxB * existingPaxIncomeB + lostMailA * existingMailIncomeA
        + lostMailB * existingMailIncomeB)).tointeger();
    local cannibalLossAnnual = rawCannibalLossAnnual > 0
        ? (rawCannibalLossAnnual.tofloat() * realizationFactor).tointeger() : 0;
    local rawRevenuePaxAnnual = (12.0 * carriedPax.tofloat() * paxIncome).tointeger();
    local rawRevenueMailAnnual = (12.0 * carriedMail.tofloat() * mailIncome).tointeger();
    local rawRevenueAnnual = rawRevenuePaxAnnual + rawRevenueMailAnnual;
    local revenuePaxAnnual = (rawRevenuePaxAnnual.tofloat() * realizationFactor).tointeger();
    local revenueMailAnnual = (rawRevenueMailAnnual.tofloat() * realizationFactor).tointeger();
    local revenueAnnual = revenuePaxAnnual + revenueMailAnnual - cannibalLossAnnual;
    local vehicleRunningAnnual = planes * plane.runningCost;
    local runningAnnual = vehicleRunningAnnual + airportMaintenanceAnnual;
    local vehicleAmortAnnual = planes * vehicleAmortPerPlane;
    local amortAnnual = vehicleAmortAnnual + airportAmortAnnual;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    local capital = airportCapital + planes * plane.price;
    local immobilise = (TRANSIT_COST_PERMILLE > 0) ? (revenueAnnual * trip.roundTripDays * TRANSIT_COST_PERMILLE) / 365000 : 0;
    local totalCapital = capital + immobilise;
    local roi = totalCapital > 0 ? (profitAnnual * 1000) / totalCapital : 0;
    /* La profondeur de flotte est une optimisation interne au projet, pas un
     * arbitrage entre projets concurrents. K_dec mesure le budget d'opportunite
     * du portefeuille (C69) et ne doit donc pas creer une zone de capital
     * "gratuit" sous son seuil. Pour la flotte, comparer le rendement du capital
     * reellement immobilise par le projet. K_dec reste attache au resultat pour
     * le futur classement portefeuille C121. */
    local decisionScore = totalCapital > 0
        ? (profitAnnual.tofloat() * 1000.0) / totalCapital.tofloat() : 0.0;
    if (scoreBest == null || decisionScore > scoreBest.score
        || (decisionScore == scoreBest.score && profitAnnual > scoreBest.profitAnnual)) {
      if (decisionOnly) {
        /* Le chooser moteur n'a besoin que d'un petit tuple de classement.
         * L'economie complete du gagnant est reconstruite une seule fois apres
         * l'argmax : ne pas allouer ici le gros snapshot C121 a chaque moteur. */
        scoreBest = {
          planes = planes, targetPlanes = planes, score = decisionScore,
          profitAnnual = profitAnnual, revenueAnnual = revenueAnnual,
          capital = capital, immobilise = immobilise, roi = roi,
          rawRevenueAnnual = rawRevenueAnnual, realizationFactor = realizationFactor,
          cannibalLossAnnual = cannibalLossAnnual,
          c121RealizationApplied = C121_AIR_ECONOMICS,
          fleetScanCap = fleetScanCap,
        };
      } else {
        scoreBest = {
        planes = planes, targetPlanes = planes, score = decisionScore,
        profitAnnual = profitAnnual, revenueAnnual = revenueAnnual,
        revenuePaxAnnual = revenuePaxAnnual, revenueMailAnnual = revenueMailAnnual,
        rawRevenueAnnual = rawRevenueAnnual, realizationFactor = realizationFactor,
        cannibalLossAnnual = cannibalLossAnnual,
        lostPaxA = lostPaxA, lostPaxB = lostPaxB,
        lostMailA = lostMailA, lostMailB = lostMailB,
        c121RealizationApplied = C121_AIR_ECONOMICS,
        runningAnnual = runningAnnual, vehicleRunningAnnual = vehicleRunningAnnual,
        infraRunningAnnual = airportMaintenanceAnnual,
        amortAnnual = amortAnnual, vehicleAmortAnnual = vehicleAmortAnnual,
        infraAmortAnnual = airportAmortAnnual, capital = capital, immobilise = immobilise, roi = roi,
        planePrice = plane.price, lifeYears = lifeYears,
        airportCapital = airportCapital, newAirportCount = newAirportCount,
        ratingBaseA = ratingBaseA, ratingBaseB = ratingBaseB,
        flightDays = trip.flightDays, maneuverDays = trip.maneuverDays,
        physicalOneWayDays = trip.physicalOneWayDays,
        hubDelayA = trip.hubDelayA, hubDelayB = trip.hubDelayB,
        hubDelayObsA = trip.hubDelayObsA, hubDelayObsB = trip.hubDelayObsB,
        hubDelayWindowObsA = trip.hubDelayWindowObsA, hubDelayWindowObsB = trip.hubDelayWindowObsB,
        hubDelayVarianceA = trip.hubDelayVarianceA, hubDelayVarianceB = trip.hubDelayVarianceB,
        oneWayDays = trip.oneWayDays, roundTripDays = trip.roundTripDays, headwayDays = headwayDays,
        stationHeadwayA = stationHeadwayA, stationHeadwayB = stationHeadwayB,
        existingPickupRateA = serviceA.pickupRate, existingPickupRateB = serviceB.pickupRate,
        existingPaxRateA = serviceA.paxRate, existingPaxRateB = serviceB.paxRate,
        existingMailRateA = serviceA.mailRate, existingMailRateB = serviceB.mailRate,
        runwayServiceDaysA = runwayServiceDaysA, runwayServiceDaysB = runwayServiceDaysB,
        runwayScaleA = runwayScaleA, runwayScaleB = runwayScaleB,
        requestedPickupRate = requestedCandidatePickupRate, pickupRate = candidatePickupRate,
        stationRating = ((paxRatingPointsA + paxRatingPointsB) * 50.0 / 255.0),
        ratingPaxA = paxRatingPointsA, ratingPaxB = paxRatingPointsB,
        ratingMailA = mailRatingPointsA, ratingMailB = mailRatingPointsB,
        routeSharePaxA = routeSharePaxA, routeSharePaxB = routeSharePaxB,
        routeShareMailA = routeShareMailA, routeShareMailB = routeShareMailB,
        waitingPaxA = paxRatingA.waitingUpper, waitingPaxB = paxRatingB.waitingUpper,
        waitingMailA = mailRatingA.waitingUpper, waitingMailB = mailRatingB.waitingUpper,
        ratingCycle = paxRatingA.cycled || paxRatingB.cycled || mailRatingA.cycled || mailRatingB.cycled,
        paymentDistance = paymentDistance, incomeDays = incomeDays, paxIncome = paxIncome, mailIncome = mailIncome,
        paxCapacity = paxCapacity, mailCapacity = mailCapacity, mailKnown = useMail,
        departuresPerDirectionMonth = departuresPerDirectionMonth,
        paxDirectionCapacity = paxDirectionCapacity, mailDirectionCapacity = mailDirectionCapacity,
        offeredPaxA = offeredPaxA, offeredPaxB = offeredPaxB, offeredMailA = offeredMailA, offeredMailB = offeredMailB,
        carriedPaxA = carriedPaxA, carriedPaxB = carriedPaxB, carriedMailA = carriedMailA, carriedMailB = carriedMailB,
        carriedPax = carriedPax, carriedMail = carriedMail, carried = carriedPax + carriedMail,
          fleetScanCap = fleetScanCap,
        };
      }
    }
    if (!decisionOnly && (best == null || profitAnnual > best.profitAnnual || (profitAnnual == best.profitAnnual && roi > best.roi))) {
      best = {
        planes = planes, targetPlanes = planes, profitAnnual = profitAnnual, revenueAnnual = revenueAnnual,
        revenuePaxAnnual = revenuePaxAnnual, revenueMailAnnual = revenueMailAnnual,
        rawRevenueAnnual = rawRevenueAnnual, realizationFactor = realizationFactor,
        cannibalLossAnnual = cannibalLossAnnual,
        lostPaxA = lostPaxA, lostPaxB = lostPaxB,
        lostMailA = lostMailA, lostMailB = lostMailB,
        c121RealizationApplied = C121_AIR_ECONOMICS,
        runningAnnual = runningAnnual, vehicleRunningAnnual = vehicleRunningAnnual,
        infraRunningAnnual = airportMaintenanceAnnual,
        amortAnnual = amortAnnual, vehicleAmortAnnual = vehicleAmortAnnual,
        infraAmortAnnual = airportAmortAnnual, capital = capital, immobilise = immobilise, roi = roi,
        planePrice = plane.price, lifeYears = lifeYears,
        airportCapital = airportCapital, newAirportCount = newAirportCount,
        ratingBaseA = ratingBaseA, ratingBaseB = ratingBaseB,
        flightDays = trip.flightDays, maneuverDays = trip.maneuverDays,
        physicalOneWayDays = trip.physicalOneWayDays,
        hubDelayA = trip.hubDelayA, hubDelayB = trip.hubDelayB,
        hubDelayObsA = trip.hubDelayObsA, hubDelayObsB = trip.hubDelayObsB,
        hubDelayWindowObsA = trip.hubDelayWindowObsA, hubDelayWindowObsB = trip.hubDelayWindowObsB,
        hubDelayVarianceA = trip.hubDelayVarianceA, hubDelayVarianceB = trip.hubDelayVarianceB,
        oneWayDays = trip.oneWayDays, roundTripDays = trip.roundTripDays, headwayDays = headwayDays,
        stationHeadwayA = stationHeadwayA, stationHeadwayB = stationHeadwayB,
        existingPickupRateA = serviceA.pickupRate, existingPickupRateB = serviceB.pickupRate,
        existingPaxRateA = serviceA.paxRate, existingPaxRateB = serviceB.paxRate,
        existingMailRateA = serviceA.mailRate, existingMailRateB = serviceB.mailRate,
        runwayServiceDaysA = runwayServiceDaysA, runwayServiceDaysB = runwayServiceDaysB,
        runwayScaleA = runwayScaleA, runwayScaleB = runwayScaleB,
        requestedPickupRate = requestedCandidatePickupRate, pickupRate = candidatePickupRate,
        stationRating = ((paxRatingPointsA + paxRatingPointsB) * 50.0 / 255.0),
        ratingPaxA = paxRatingPointsA, ratingPaxB = paxRatingPointsB,
        ratingMailA = mailRatingPointsA, ratingMailB = mailRatingPointsB,
        routeSharePaxA = routeSharePaxA, routeSharePaxB = routeSharePaxB,
        routeShareMailA = routeShareMailA, routeShareMailB = routeShareMailB,
        waitingPaxA = paxRatingA.waitingUpper, waitingPaxB = paxRatingB.waitingUpper,
        waitingMailA = mailRatingA.waitingUpper, waitingMailB = mailRatingB.waitingUpper,
        ratingCycle = paxRatingA.cycled || paxRatingB.cycled || mailRatingA.cycled || mailRatingB.cycled,
        paymentDistance = paymentDistance, incomeDays = incomeDays, paxIncome = paxIncome, mailIncome = mailIncome,
        paxCapacity = paxCapacity, mailCapacity = mailCapacity, mailKnown = useMail,
        departuresPerDirectionMonth = departuresPerDirectionMonth,
        paxDirectionCapacity = paxDirectionCapacity, mailDirectionCapacity = mailDirectionCapacity,
        offeredPaxA = offeredPaxA, offeredPaxB = offeredPaxB, offeredMailA = offeredMailA, offeredMailB = offeredMailB,
        carriedPaxA = carriedPaxA, carriedPaxB = carriedPaxB, carriedMailA = carriedMailA, carriedMailB = carriedMailB,
        carriedPax = carriedPax, carriedMail = carriedMail, carried = carriedPax + carriedMail,
        fleetScanCap = fleetScanCap,
      };
    }
    if (decisionOnly && fixedPlanes <= 0 && planes < maxAllowed && scoreBest != null
        && plane.price > 0 && plane.runningCost >= 0 && vehicleAmortPerPlane >= 0) {
      local nextPlanes = planes + 1;
      local upperProfit = maxRevenueUpper
          - (nextPlanes * plane.runningCost + airportMaintenanceAnnual)
          - (nextPlanes * vehicleAmortPerPlane + airportAmortAnnual);
      local nextCapital = airportCapital + nextPlanes * plane.price;
      local upperScore = nextCapital > 0
          ? upperProfit.tofloat() * 1000.0 / nextCapital.tofloat() : 0.0;
      if (upperScore <= scoreBest.score) break;
    }
  }
  if (decisionOnly) {
    if (scoreBest != null) {
      scoreBest.fleetEvaluated <- fleetEvaluated;
      scoreBest.fleetBoundPruned <- fixedPlanes <= 0 && fleetEvaluated < fleetScanCap;
      scoreBest.decisionKDec <- decisionKDec;
      scoreBest.decisionPlanes <- scoreBest.planes;
      scoreBest.decisionScore <- scoreBest.score;
      scoreBest.decisionProfitAnnual <- scoreBest.profitAnnual;
      scoreBest.decisionRevenueAnnual <- scoreBest.revenueAnnual;
      scoreBest.decisionCapital <- scoreBest.capital;
    }
    return scoreBest;
  }
  if (best != null && scoreBest != null) {
    scoreBest.fleetEvaluated <- fleetEvaluated;
    scoreBest.fleetBoundPruned <- decisionOnly && fixedPlanes <= 0 && fleetEvaluated < fleetScanCap;
    scoreBest.decisionKDec <- decisionKDec;
    scoreBest.decisionPlanes <- scoreBest.planes;
    scoreBest.decisionScore <- scoreBest.score;
    scoreBest.decisionProfitAnnual <- scoreBest.profitAnnual;
    scoreBest.decisionRevenueAnnual <- scoreBest.revenueAnnual;
    scoreBest.decisionCapital <- scoreBest.capital;
    scoreBest.decisionCarriedPax <- scoreBest.carriedPax;
    scoreBest.decisionCarriedMail <- scoreBest.carriedMail;
    scoreBest.decisionCarried <- scoreBest.carried;
    scoreBest.decisionStationRating <- scoreBest.stationRating;
    scoreBest.decisionHeadwayDays <- scoreBest.headwayDays;
    scoreBest.decisionRunwayScaleA <- scoreBest.runwayScaleA;
    scoreBest.decisionRunwayScaleB <- scoreBest.runwayScaleB;
    scoreBest.decisionRequestedPickupRate <- scoreBest.requestedPickupRate;
    scoreBest.decisionPickupRate <- scoreBest.pickupRate;
    best.decisionKDec <- decisionKDec;
    best.decisionPlanes <- scoreBest.planes;
    best.decisionScore <- scoreBest.score;
    best.decisionProfitAnnual <- scoreBest.profitAnnual;
    best.decisionRevenueAnnual <- scoreBest.revenueAnnual;
    best.decisionCapital <- scoreBest.capital;
    best.decisionCarriedPax <- scoreBest.carriedPax;
    best.decisionCarriedMail <- scoreBest.carriedMail;
    best.decisionCarried <- scoreBest.carried;
    best.decisionStationRating <- scoreBest.stationRating;
    best.decisionHeadwayDays <- scoreBest.headwayDays;
    best.decisionRunwayScaleA <- scoreBest.runwayScaleA;
    best.decisionRunwayScaleB <- scoreBest.runwayScaleB;
    best.decisionRequestedPickupRate <- scoreBest.requestedPickupRate;
    best.decisionPickupRate <- scoreBest.pickupRate;
    best.decisionEconomics <- scoreBest;
  }
  return best;
}

/* Evaluation C121 avec l'etat de connaissance courant d'un moteur : le premier
 * contact utilise la capacite PASS du catalogue et MAIL=0 ; apres la premiere
 * construction/refit PASS, le couple PASS/MAIL exact observe remplace ce cold
 * start. Aucun catalogue OpenGFX externe ni pourcentage MAIL n'intervient. */
function OpexC121EngineEconomics(catalog, plan, plane, fixedPlanes = 0, decisionOnly = false,
                                 decisionScoreFloor = null)
{
  if (plane == null) return null;
  local paxCapacity = plane.capacity;
  local mailCapacity = 0;
  local mailKnown = false;
  if (plane.id in C121_AIR_ENGINE_CAPACITY_OBS) {
    local caps = C121_AIR_ENGINE_CAPACITY_OBS[plane.id];
    if (caps != null && caps.pax > 0 && caps.mail >= 0) {
      paxCapacity = caps.pax;
      mailCapacity = caps.mail;
      mailKnown = true;
    }
  }
  local economics = OpexC121AirEconomics(
      catalog, plan, plane, paxCapacity, mailCapacity, fixedPlanes, decisionOnly, decisionScoreFloor);
  if (economics != null && decisionOnly && C121_AIR_ENGINE_REALIZATION) {
    local factor = OpexC121EngineDecisionRealizationFactor(plan);
    if (factor != 1.0) {
      local oldRevenue = economics.revenueAnnual;
      local annualCosts = oldRevenue - economics.profitAnnual;
      local adjustedRevenue = (oldRevenue.tofloat() * factor).tointeger();
      local adjustedProfit = adjustedRevenue - annualCosts;
      local adjustedImmobilise = (economics.immobilise.tofloat() * factor).tointeger();
      local adjustedTotalCapital = economics.capital + adjustedImmobilise;
      local adjustedScore = adjustedTotalCapital > 0
          ? adjustedProfit.tofloat() * 1000.0 / adjustedTotalCapital.tofloat() : 0.0;
      economics.revenueAnnual = adjustedRevenue;
      economics.profitAnnual = adjustedProfit;
      economics.immobilise = adjustedImmobilise;
      economics.roi = adjustedTotalCapital > 0
          ? (adjustedProfit * 1000) / adjustedTotalCapital : 0;
      economics.score = adjustedScore;
      economics.decisionRevenueAnnual = adjustedRevenue;
      economics.decisionProfitAnnual = adjustedProfit;
      economics.decisionScore = adjustedScore;
      economics.engineDecisionRealizationFactor <- factor;
    }
  }
  if (economics != null) {
    economics.engineMailKnown <- mailKnown;
    if (("decisionEconomics" in economics) && economics.decisionEconomics != null) {
      economics.decisionEconomics.engineMailKnown <- mailKnown;
    }
  }
  return economics;
}

/* Borne superieure bon marche du score initial C121 a un avion. Elle ignore
 * rating, partage de route et saturation de piste, mais respecte la capacite
 * physique d'UN avion a sa cadence de rotation exacte. Elle reste donc
 * optimiste sans pretendre qu'un petit avion peut transporter 100 % d'une
 * grosse ville. Utilisee seulement pour ordonner/pruner le scan moteur sans
 * changer l'argmax exact. */
function OpexC121InitialEngineUpperScore(catalog, plan, plane)
{
  if (catalog == null || plan == null || plane == null || !("c121Demand" in plan)
      || !("c121EngineStatic" in plan) || plan.c121EngineStatic == null
      || plane.price <= 0 || plane.runningCost < 0) return null;
  local st = plan.c121EngineStatic;
  local paxCapacity = plane.capacity;
  local mailCapacity = 0;
  local incomeDays = OpexC119AirIncomeDays(plane, plan.distance);
  local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, st.paymentDistance, incomeDays);
  if (paxIncome < 0) return null;
  local useMail = false;
  if (plane.id in C121_AIR_ENGINE_CAPACITY_OBS) {
    local caps = C121_AIR_ENGINE_CAPACITY_OBS[plane.id];
    if (caps != null && caps.pax > 0 && caps.mail >= 0) {
      paxCapacity = caps.pax;
      mailCapacity = caps.mail;
      useMail = mailCapacity > 0 && ("mailCargo" in catalog) && catalog.mailCargo >= 0;
    }
  }
  if (paxCapacity <= 0) return null;
  local mailIncome = useMail ? AICargo.GetCargoIncome(catalog.mailCargo, st.paymentDistance, incomeDays) : 0;
  if (useMail && mailIncome < 0) return null;
  local trip = OpexC121AirTripModel(plan, plane);
  if (trip == null || trip.roundTripDays <= 0.0) return null;
  local departuresPerDirectionMonth = 30.4 / trip.roundTripDays;
  local paxDirectionCapacity = paxCapacity.tofloat() * departuresPerDirectionMonth;
  local paxUpperA = st.paxRawA.tofloat() < paxDirectionCapacity ? st.paxRawA.tofloat() : paxDirectionCapacity;
  local paxUpperB = st.paxRawB.tofloat() < paxDirectionCapacity ? st.paxRawB.tofloat() : paxDirectionCapacity;
  local mailUpperA = 0.0;
  local mailUpperB = 0.0;
  if (useMail) {
    local mailDirectionCapacity = mailCapacity.tofloat() * departuresPerDirectionMonth;
    mailUpperA = st.mailRawA.tofloat() < mailDirectionCapacity ? st.mailRawA.tofloat() : mailDirectionCapacity;
    mailUpperB = st.mailRawB.tofloat() < mailDirectionCapacity ? st.mailRawB.tofloat() : mailDirectionCapacity;
  }
  local rawRevenueUpper = (12.0 * (paxUpperA + paxUpperB) * paxIncome
      + 12.0 * (mailUpperA + mailUpperB) * mailIncome).tointeger();
  local revenueUpper = (rawRevenueUpper.tofloat()
      * OpexC121EngineDecisionRealizationFactor(plan)).tointeger();
  local lifeYears = (("ageYears" in plane) && plane.ageYears > 0)
      ? plane.ageYears : (AIEngine.GetMaxAge(plane.id) / 365);
  local amort = lifeYears > 0 ? plane.price / lifeYears : 0;
  local profitUpper = revenueUpper - plane.runningCost - st.airportMaintenanceAnnual
      - amort - st.airportAmortAnnual;
  local capital = st.airportCapital + plane.price;
  return capital > 0 ? profitUpper.tofloat() * 1000.0 / capital.tofloat() : 0.0;
}

/* Choix causal C121. Les invariants de route sont prepares une seule fois par
 * projet, puis chaque moteur relit seulement cet etat et le cache de soute. */
function OpexC121ChooseRoutePlane(catalog, plan, lines = null)
{
  if (!C121_AIR_ECONOMICS || catalog == null || plan == null
      || !("airport" in plan) || plan.airport == null
      || !("distance" in plan)
      || catalog.airPlaneChoicesByAirport == null
      || !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return null;
  local perf = C121_AIR_PLAN_PERF;
  if (perf != null) perf.calls++;
  OpexC121PrepareDemandShadow(catalog, plan, lines);
  if (perf != null && ("c121DemandOps" in plan)) {
    if (plan.c121DemandOps >= 0) perf.demandOps += plan.c121DemandOps;
    perf.demandTicks += ("c121DemandTicks" in plan) ? plan.c121DemandTicks : 0;
  }
  if (!("c121Demand" in plan)) return null;
  local staticTick0 = AIController.GetTick();
  local staticOps0 = AIController.GetOpsTillSuspend();
  OpexC121PrepareEngineStatic(catalog, plan);
  local staticTick1 = AIController.GetTick();
  plan.c121EngineStaticTicks <- staticTick1 - staticTick0;
  plan.c121EngineStaticOps <- OpexAirCalcDeltaOps(staticTick0, staticOps0);
  if (perf != null) {
    if (plan.c121EngineStaticOps >= 0) perf.staticOps += plan.c121EngineStaticOps;
    perf.staticTicks += plan.c121EngineStaticTicks;
  }

  local scanTick0 = AIController.GetTick();
  local scanOps0 = AIController.GetOpsTillSuspend();
  local evaluated = 0;
  local known = 0;
  local evalOpsTotal = 0;
  local evalOps = 0;
  local evalSameTick = 0;
  local best = null;
  local candidates = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
    if (!OpexC118EngineFitsPlan(plan, plane)) continue;
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    local upperScore = OpexC121InitialEngineUpperScore(catalog, plan, plane);
    if (upperScore == null) continue;
    candidates.append({ plane = plane, upperScore = upperScore });
  }
  candidates.sort(function(a, b) {
    if (a.upperScore > b.upperScore) return -1;
    if (a.upperScore < b.upperScore) return 1;
    if (a.plane.id < b.plane.id) return -1;
    if (a.plane.id > b.plane.id) return 1;
    return 0;
  });
  foreach (candidate in candidates) {
    if (best != null && candidate.upperScore < best.economics.decisionScore) break;
    local plane = candidate.plane;
    local tick0 = AIController.GetTick();
    local ops0 = AIController.GetOpsTillSuspend();
    local evaluatedEconomics = OpexC121EngineEconomics(catalog, plan, plane, C121_AAA_LINE ? 2 : 1, true, null);
    local tick1 = AIController.GetTick();
    local ops = OpexAirCalcDeltaOps(tick0, ops0);
    if (ops >= 0) evalOpsTotal += ops;
    if (tick1 == tick0 && ops >= 0) {
      evalOps += ops;
      evalSameTick++;
    }
    if (evaluatedEconomics == null || !("decisionScore" in evaluatedEconomics)) continue;
    local economics = (("decisionEconomics" in evaluatedEconomics)
        && evaluatedEconomics.decisionEconomics != null)
        ? evaluatedEconomics.decisionEconomics : evaluatedEconomics;
    evaluated++;
    if (("engineMailKnown" in economics) && economics.engineMailKnown) known++;
    local item = { plane = plane, economics = economics };
    if (best == null
        || economics.decisionScore > best.economics.decisionScore
        || (economics.decisionScore == best.economics.decisionScore
            && economics.decisionProfitAnnual > best.economics.decisionProfitAnnual)
        || (economics.decisionScore == best.economics.decisionScore
            && economics.decisionProfitAnnual == best.economics.decisionProfitAnnual
            && plane.id < best.plane.id)) best = item;
  }
  local scanTick1 = AIController.GetTick();
  plan.c121EngineScanTicks <- scanTick1 - scanTick0;
  plan.c121EngineScanOps <- OpexAirCalcDeltaOps(scanTick0, scanOps0);
  plan.c121EngineEvalCount <- evaluated;
  plan.c121EngineKnownCount <- known;
  plan.c121EngineEvalOpsTotal <- evalOpsTotal;
  plan.c121EngineEvalOpsSameTick <- evalOps;
  plan.c121EngineEvalSameTickCount <- evalSameTick;
  if (perf != null) {
    if (plan.c121EngineScanOps >= 0) perf.scanOps += plan.c121EngineScanOps;
    perf.scanTicks += plan.c121EngineScanTicks;
    perf.engineEvals += evaluated;
  }
  if (best == null) {
    if (perf != null) perf.noWinner++;
    return null;
  }
  /* Le scan decisionOnly choisit le moteur sur le chantier N=1. Pour ne pas
   * sous-evaluer les lignes dont la valeur vient de leur montee en charge, on
   * calcule ensuite UNE seule croisiere max-profit pour le moteur gagnant. Elle
   * sert uniquement au classement economique ; le chantier reste N=1 et la
   * cible exacte sera recalculee apres construction avec PASS/MAIL observes. */
  local fullTick0 = AIController.GetTick();
  local fullOps0 = AIController.GetOpsTillSuspend();
  local initialEconomics = OpexC121EngineEconomics(catalog, plan, best.plane, C121_AAA_LINE ? 2 : 1, false);
  local decisionEconomics = OpexC121EngineEconomics(catalog, plan, best.plane, 0, false);
  local fullTick1 = AIController.GetTick();
  plan.c121WinnerFullTicks <- fullTick1 - fullTick0;
  plan.c121WinnerFullOps <- OpexAirCalcDeltaOps(fullTick0, fullOps0);
  if (perf != null) {
    if (plan.c121WinnerFullOps >= 0) perf.winnerOps += plan.c121WinnerFullOps;
    perf.winnerTicks += plan.c121WinnerFullTicks;
  }
  if (initialEconomics == null) return null;
  if (decisionEconomics == null) decisionEconomics = initialEconomics;
  plan.c121ChosenEngine <- best.plane.id;
  plan.c121ChosenMailKnown <- (("engineMailKnown" in initialEconomics) && initialEconomics.engineMailKnown);
  return { plane = best.plane, economics = initialEconomics, decisionEconomics = decisionEconomics,
      targetPlanes = initialEconomics.planes };
}
