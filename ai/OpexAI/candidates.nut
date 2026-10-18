/* Etages 1 et 2 : ce que rapporte un candidat, et ce qu'il coute en opcodes.
 *
 * Etage 1 -- le profit attendu. Changement de fond par rapport a TrainLineAI : la variable n'est
 * plus population_a * population_b / distance (un proxy) mais la PRODUCTION reelle multipliee par
 * le revenu unitaire reel (AICargo.GetCargoIncome), c'est-a-dire la grandeur physique.
 *
 * Etage 2 -- le cout en opcodes attendu. Pour l'instant c'est un modele lineaire grossier ; il
 * sera remplace par une regression ajustee sur les campagnes, ou le nombre reel d'iterations
 * d'A* par ligne est connu.
 *
 * candidates.nut produit les alternatives : projects.nut choisit d'abord le ROI modal, remplit
 * ensuite le budget sur le revenu/capital, puis seulement ordonne sur le revenu/opcode.
 */

/* Les bandes de distance ne sont plus des constantes. OpexRefreshEpochBounds les
 * recalcule a chaque refresh de catalogue (et sur ET_ENGINE_AVAILABLE) dans
 * catalog.bounds : geometrie des bassins, egalite cinematique rail/air, plafond
 * A* inverse. Le reglage `rail_min_distance` n'alimente plus le filtre. */
/* Memo du predicat origin_sitable, keye par (srcTile * 64 + cargo). Slot de table racine, PAS
 * un `local` de fichier : OpexMakeCandidate le lit, et ce depot a deja verifie deux fois
 * qu'une closure ne capture pas une `local` englobante (voir ::REASON_CODES dans
 * ai/TrainLineAI/main.nut). Vide a chaque OpexBuildCandidates, donc jamais stale. */
::OpexSitableCache <- {};

TOP_K <- 20;
MIN_RATIO <- 500;
const PAX_BAND_ALL = 0;
const PAX_BAND_AIR_ONLY = 1;
const PAX_BAND_AIR_RAIL = 2;
const PAX_BAND_RAIL_ONLY = 3;
const PAX_BAND_ROUTE_ONLY = 4;

/* Lots fret dynamiques : les IDs et le nombre de cargos dependent du climat et
 * des NewGRF. La valeur comparee est le revenu brut d'un meme trajet de 20
 * tuiles, sans retard, afin de classer le prix du cargo et non la qualite d'une
 * liaison particuliere. Le cargoId ne sert qu'a rendre les ex-aequo stables. */
function OpexFreightCargoOrder(catalog)
{
  local ranked = [];
  if (catalog == null || catalog.producers == null) return ranked;
  foreach (cargo, sources in catalog.producers) {
    if (sources == null || sources.len() == 0 || cargo == catalog.paxCargo) continue;
    /* Un cargo peut exister dans le climat/NewGRF sans etre encore produit
     * (marchandises avant alimentation d'une usine, par exemple). Il ne doit
     * pas bloquer un lot au seul motif que son tarif est eleve. */
    local active = false;
    foreach (si in sources) {
      if (si >= 0 && si < catalog.industries.len()
          && AIIndustry.GetLastMonthProduction(catalog.industries[si].id, cargo) > 0) {
        active = true;
        break;
      }
    }
    if (!active) continue;
    local hasSink = (cargo in catalog.acceptors)
        || (cargo in catalog.townAcceptors);
    if (!hasSink) continue;
    local hasRail = catalog.wagonByCargo != null && (cargo in catalog.wagonByCargo);
    local hasRoad = catalog.roadEngineByCargo != null && (cargo in catalog.roadEngineByCargo);
    if (!hasRail && !hasRoad) continue;
    ranked.append({ cargo = cargo, price = AICargo.GetCargoIncome(cargo, 20, 0) });
  }
  ranked.sort(function(a, b) {
    if (a.price != b.price) return a.price > b.price ? -1 : 1;
    if (a.cargo == b.cargo) return 0;
    return a.cargo < b.cargo ? -1 : 1;
  });
  local cargos = [];
  foreach (entry in ranked) cargos.append(entry.cargo);
  return cargos;
}

/* Etage 2 : le cout, AJUSTE sur la campagne v3 (1997 lignes reelles, OpenTTD 13.4).
 *
 * La grandeur utile n'est pas "iterations d'une tentative" mais "iterations par ligne REUSSIE",
 * qui absorbe l'echec : iterations_moyennes / P(construite).
 *
 * On garde une table de noeuds avec interpolation lineaire : exacte aux noeuds, entierement
 * en entiers, aucune fonction mathematique flottante en Squirrel.
 *
 *   distance :    23     33     48     63     81    105     150
 *   iterations:  371    673   2188   4066   7745  15308   53951
 *
 */
KNOT_DISTANCE <- [23, 33, 48, 63, 81, 105, 150];
KNOT_ITERATIONS_V1 <- [371, 673, 2188, 4066, 7745, 15308, 53951];

function OpexRailIterations(distance)
{
  local knots = KNOT_ITERATIONS_V1;
  local n = KNOT_DISTANCE.len();
  if (distance <= KNOT_DISTANCE[0]) return knots[0];
  for (local i = 1; i < n; i++) {
    if (distance <= KNOT_DISTANCE[i]) {
      local d0 = KNOT_DISTANCE[i - 1];
      local d1 = KNOT_DISTANCE[i];
      local v0 = knots[i - 1];
      local v1 = knots[i];
      return v0 + ((v1 - v0) * (distance - d0)) / (d1 - d0);
    }
  }
  /* Au-dela du dernier noeud, la complexite empirique d'un pathfinder A* sur grille 2D croit
   * au moins comme le carre de la distance (surface exploree). */
  local dLast = KNOT_DISTANCE[n - 1];
  local vLast = knots[n - 1];
  return (vLast * distance * distance) / (dLast * dLast);
}

/* Inverse de OpexRailIterations : plus grande distance dont les iterations predites
 * restent <= maxIter. Dans la queue, I(D) = I_last * (D / D_last)^2. */
function OpexRailDistanceForIterations(maxIter)
{
  if (maxIter <= 0) return KNOT_DISTANCE[0];
  local knots = KNOT_ITERATIONS_V1;
  local n = KNOT_DISTANCE.len();
  if (maxIter <= knots[0]) return KNOT_DISTANCE[0];
  for (local i = 1; i < n; i++) {
    if (maxIter <= knots[i]) {
      local d0 = KNOT_DISTANCE[i - 1];
      local d1 = KNOT_DISTANCE[i];
      local v0 = knots[i - 1];
      local v1 = knots[i];
      if (v1 == v0) return d1;
      return d0 + ((maxIter - v0) * (d1 - d0)) / (v1 - v0);
    }
  }
  local dLast = KNOT_DISTANCE[n - 1];
  local vLast = knots[n - 1];
  if (vLast <= 0) return dLast;
  return OpexIsqrt((dLast * dLast * maxIter) / vLast);
}

function OpexPlaneSpeedDivisor()
{
  if (AIGameSettings.IsValid("vehicle.plane_speed")) {
    local v = AIGameSettings.GetValue("vehicle.plane_speed");
    if (v > 0) return v.tofloat();
  }
  return 4.0;
}

function OpexTicksPerDay(catalog)
{
  /* AIController.GetTick n'est pas une horloge moteur continue : il n'avance
   * pas pendant toutes les suspensions du script. Le banc 1024^2 donnait ainsi
   * 18 ticks/jour apres le premier refresh contre les 74 ticks calendaires du
   * moteur, quadruplant artificiellement les manoeuvres aeroportuaires. */
  return 74.0;
}

function OpexDaysPerTile(effectiveSpeed, ticksPerDay)
{
  if (effectiveSpeed < 1.0) effectiveSpeed = 1.0;
  local tpd = (ticksPerDay > 0) ? ticksPerDay : 74.0;
  return 4096.0 / (tpd * 1.6 * effectiveSpeed);
}

function OpexGetEpochVehicle(vehicleType, cargoId, railType = -1)
{
  local list = AIEngineList(vehicleType);
  list.Valuate(AIEngine.IsBuildable);
  list.KeepValue(1);
  if (list.IsEmpty()) return null;
  if (vehicleType == AIVehicle.VT_RAIL) {
    list.Valuate(AIEngine.IsWagon);
    list.KeepValue(0);
    if (railType >= 0) {
      list.Valuate(AIEngine.HasPowerOnRail, railType);
      list.KeepValue(1);
    }
  }
  if (cargoId >= 0) {
    list.Valuate(AIEngine.CanRefitCargo, cargoId);
    list.KeepValue(1);
  }
  if (list.IsEmpty()) return null;
  if (vehicleType == AIVehicle.VT_AIR) {
    local best = null;
    local bestSpeed = -1;
    for (local e = list.Begin(); !list.IsEnd(); e = list.Next()) {
      if (AIEngine.GetPlaneType(e) == AIAirport.PT_HELICOPTER) continue;
      local speed = AIEngine.GetMaxSpeed(e);
      if (speed > bestSpeed) {
        best = e;
        bestSpeed = speed;
      }
    }
    return best;
  }
  list.Valuate(AIEngine.GetMaxSpeed);
  return list.Begin();
}

/* Profil ferroviaire pax de reference. Une locomotive ne transporte pas elle-meme
 * les passagers : la filtrer par CanRefitCargo elimine les locomotives ordinaires
 * et ne laisse, selon l'epoque, que les automotrices. Le catalogue a deja resolu
 * locomotive + wagon + vitesse soutenable ; reutiliser cette autorite evite aussi
 * de comparer l'avion a la seule vitesse de pointe d'une locomotive a vide. */
function OpexGetEpochRailProfile(catalog, cargoId, distance = 20)
{
  if (catalog == null || cargoId < 0) return null;
  if (!(cargoId in catalog.wagonByCargo) || !(cargoId in catalog.locoByCargoWagons)) return null;
  local wagon = catalog.wagonByCargo[cargoId];
  local choices = catalog.locoByCargoWagons[cargoId];
  if (wagon == null || choices == null || choices.len() == 0) return null;
  local wagons = choices.len() >= 2 ? 2 : 1;
  local loco = choices[wagons - 1];
  if (loco == null) return null;
  local speed = OpexRailEffectiveSpeed(loco, wagon, wagons, distance);
  if (speed < 1) return null;
  return {
    id = loco.id,
    speed = speed,
    price = loco.price + wagons * wagon.price,
    wagons = wagons,
  };
}

function OpexAirManeuverDays(engineId, srcType, dstType, ticksPerDay, planeDiv)
{
  local maxSpeed = AIEngine.GetMaxSpeed(engineId).tofloat();
  if (maxSpeed < 1.0) maxSpeed = 1.0;
  local taxiSpeed = 150.0;
  if (maxSpeed < taxiSpeed) taxiSpeed = maxSpeed;
  taxiSpeed = taxiSpeed / planeDiv;
  if (taxiSpeed < 1.0) taxiSpeed = 1.0;
  local groundTiles = 12.0;
  if (srcType != null && dstType != null && AIAirport.IsValidAirportType(srcType)
      && AIAirport.IsValidAirportType(dstType)) {
    groundTiles = (AIAirport.GetAirportWidth(srcType) + AIAirport.GetAirportHeight(srcType)
                   + AIAirport.GetAirportWidth(dstType) + AIAirport.GetAirportHeight(dstType)).tofloat();
  }
  local tpd = (ticksPerDay > 0) ? ticksPerDay : 74.0;
  local taxiDays = groundTiles * OpexDaysPerTile(taxiSpeed, tpd);
  local verticalDays = 300.0 / tpd;
  return taxiDays + verticalDays;
}

function OpexCargoTransitHorizon(cargo, distance)
{
  if (cargo < 0 || distance < 1) return 20;
  local maxInc = AICargo.GetCargoIncome(cargo, distance, 0);
  if (maxInc <= 0) return 20;
  local limit = (maxInc * 30) / 100;
  if (limit < 1) limit = 1;
  local lo = 0;
  local hi = 250;
  while (lo < hi) {
    local mid = (lo + hi) / 2;
    local inc = AICargo.GetCargoIncome(cargo, distance, mid);
    if (inc <= limit) hi = mid;
    else lo = mid + 1;
  }
  return lo;
}

function OpexMapManhattanSpan()
{
  local span = AIMap.GetMapSizeX() + AIMap.GetMapSizeY();
  return span > 1 ? span : 1;
}

function OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, ticksPerDay)
{
  local roadMin = (AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP) * 2) + 1;
  if (bestBus == null || bestTrain == null || catalog.paxCargo < 0) return roadMin;

  local kStop = catalog.costRoadBusStop;
  local kGare = catalog.costStation;
  if (catalog.platformLength > 0) kGare = catalog.costStation * catalog.platformLength;
  local cTile = (catalog.costTrackPerTile * RAIL_TERRAIN_FACTOR) / 100;
  local kBus = AIEngine.GetPrice(bestBus);
  local kTrain = bestTrain.price;
  local nBus = 2;
  local num = 2 * (kGare - kStop) + (kTrain - nBus * kBus);

  local meanM = 0;
  local nProd = 0;
  foreach (town in catalog.towns) {
    local p = AITown.GetLastMonthProduction(town.id, catalog.paxCargo);
    if (p > 0) {
      meanM += p;
      nProd++;
    }
  }
  local M = (nProd > 0) ? (meanM / nProd) : 0;
  if (M < 1) M = 1;

  local vBus = AIEngine.GetMaxSpeed(bestBus).tofloat() * 0.8;
  local vRail = bestTrain.speed.tofloat();
  local tauBus = OpexDaysPerTile(vBus, ticksPerDay);
  local tauRail = OpexDaysPerTile(vRail, ticksPerDay);
  local refD = 20;
  local transitBus = ((refD.tofloat() * tauBus) * 2.0) / 5.0;
  local transitRail = ((refD.tofloat() * tauRail) * 2.0) / 5.0;
  local incRail = AICargo.GetCargoIncome(catalog.paxCargo, refD, transitRail.tointeger());
  local incBus = AICargo.GetCargoIncome(catalog.paxCargo, refD, transitBus.tointeger());
  local deltaM = incRail - incBus;
  if (deltaM <= 0) return roadMin;
  /* GetCargoIncome livre ici le gain TOTAL a refD, pas un gain par tuile.
   * L'equation qui isole d doit soustraire deux coefficients par tuile. */
  local deltaPerTile = deltaM.tofloat() / refD.tofloat();

  /* r_cible = 0,40 : ROI annuel vise pour amortir le capital fixe ferroviaire. */
  local denom = ((12.0 * M * deltaPerTile * 100.0) / 40.0) - cTile;
  if (denom <= 0) return roadMin;
  if (num <= 0) return roadMin;
  local d = num / denom;
  if (d < roadMin) d = roadMin;
  return d.tointeger();
}

function OpexComputeRailToAirDistance(bestTrain, bestPlane, ticksPerDay, airportType)
{
  if (bestTrain == null || bestPlane == null) return OpexMapManhattanSpan();
  local planeDiv = OpexPlaneSpeedDivisor();
  local vRail = bestTrain.speed.tofloat();
  local vAir = AIEngine.GetMaxSpeed(bestPlane).tofloat() / planeDiv;
  local tauRail = OpexDaysPerTile(vRail, ticksPerDay);
  local tauAir = OpexDaysPerTile(vAir, ticksPerDay);
  local tFixe = OpexAirManeuverDays(bestPlane, airportType, airportType, ticksPerDay, planeDiv);
  if (tauRail <= tauAir) return OpexMapManhattanSpan();
  local d = tFixe / (tauRail - tauAir);
  if (d < 1.0) d = 1.0;
  return d.tointeger();
}

function OpexComputeAirMaxDistance(bestPlane, ticksPerDay, airportType, paxCargo)
{
  if (bestPlane == null) return 0;
  local planeDiv = OpexPlaneSpeedDivisor();
  local vAir = AIEngine.GetMaxSpeed(bestPlane).tofloat() / planeDiv;
  local tauAir = OpexDaysPerTile(vAir, ticksPerDay);
  local tFixe = OpexAirManeuverDays(bestPlane, airportType, airportType, ticksPerDay, planeDiv);
  local range = AIEngine.GetMaximumOrderDistance(bestPlane);
  local horizon = OpexCargoTransitHorizon(paxCargo, 100);
  local calendarMax = (horizon.tofloat() * 2.5) - tFixe;
  local rentable = OpexMapManhattanSpan();
  if (calendarMax > 0.0 && tauAir > 0.0) {
    rentable = (calendarMax / tauAir).tointeger();
    if (rentable < 1) rentable = 1;
  }
  if (range > 0 && range < rentable) return range;
  return rentable;
}

function OpexRefreshEpochBounds(catalog)
{
  if (catalog == null) return;
  local tpd = OpexTicksPerDay(catalog);
  local pax = catalog.paxCargo;
  local busR = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local roadMin = (busR * 2) + 1;
  if (roadMin < 1) roadMin = 1;

  local bestBus = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_ROAD, pax) : null;
  local bestTrain = (pax >= 0) ? OpexGetEpochRailProfile(catalog, pax, 20) : null;
  local bestPlane = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_AIR, pax) : null;

  local roadMax = OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, tpd);
  if (roadMax < roadMin) roadMax = roadMin;
  local mapSpan = OpexMapManhattanSpan();
  if (roadMax > mapSpan) roadMax = mapSpan;

  local iterCap = (HARD_ITERATION_CAP * 12) / 10;
  local railMax = OpexRailDistanceForIterations(iterCap);
  /* V168 : la table de noeuds date d'un ancien A* ; au banc rail contre rail du 13/10, les
   * recherches de 80-94 tuiles prennent 2 204 iterations medianes contre 7 745 predites, et
   * AAAHogEx pose ses lignes a 117 tuiles medianes. Le reglage remplace la borne derivee. */
  if (V168_RAIL_MAX_DIST > 0) railMax = V168_RAIL_MAX_DIST;
  if (railMax < roadMax) railMax = roadMax;

  /* Si le rail s'amortit des le bassin, la bande exclusive route est vide. On
   * laisse quand meme les camions concourir jusqu'a l'horizon de transit du bus
   * (ROI, pas un plafond magique). */
  local roadGenMax = roadMax;
  if (bestBus != null && pax >= 0) {
    local vBus = AIEngine.GetMaxSpeed(bestBus).tofloat() * 0.8;
    local tauBus = OpexDaysPerTile(vBus, tpd);
    local horizon = OpexCargoTransitHorizon(pax, 25);
    local busHorizon = 0;
    if (tauBus > 0.0) busHorizon = ((horizon.tofloat() * 2.5) / tauBus).tointeger();
    if (busHorizon > roadGenMax) roadGenMax = busHorizon;
  }
  if (roadGenMax > railMax) roadGenMax = railMax;
  if (roadGenMax < roadMin) roadGenMax = roadMin;

  local airportType = (catalog.airport != null) ? catalog.airport.type : null;
  local railAir = railMax;
  local tFixe = 0.0;
  local vRail = 0;
  local vAirEff = 0.0;
  if (bestPlane != null && bestTrain != null) {
    railAir = OpexComputeRailToAirDistance(bestTrain, bestPlane, tpd, airportType);
    vRail = bestTrain.speed;
    vAirEff = AIEngine.GetMaxSpeed(bestPlane).tofloat() / OpexPlaneSpeedDivisor();
    tFixe = OpexAirManeuverDays(bestPlane, airportType, airportType, tpd, OpexPlaneSpeedDivisor());
  } else if (bestPlane != null) {
    railAir = roadMax;
  }

  local airMax = bestPlane ? OpexComputeAirMaxDistance(bestPlane, tpd, airportType, pax) : 0;
  if (airMax > mapSpan) airMax = mapSpan;
  if (railAir > mapSpan) railAir = mapSpan;
  if (railMax > mapSpan) railMax = mapSpan;
  if (railAir < roadMax) railAir = roadMax;
  if (railAir > railMax) railAir = railMax;

  catalog.bounds = {
    roadMin = roadMin,
    roadMax = roadMax,
    roadGenMax = roadGenMax,
    railMin = roadMax,
    railAirOverlapMin = railAir,
    railMax = railMax,
    airMax = airMax,
    airMin = (railAir < railMax) ? railAir : railMax,
    ticksPerDay = tpd,
    vRail = vRail,
    vAirEff = vAirEff,
    tFixeAir = tFixe,
    year = catalog.year,
  };

  if (DECISION_LOG) {
    OpexDecide("EPOCH_BOUNDS", "roadMin=" + roadMin + " roadMax=" + roadMax
               + " roadGen=" + roadGenMax + " railMin=" + roadMax + " railAir=" + railAir
               + " railMax=" + railMax + " airMax=" + airMax
               + " airMin=" + catalog.bounds.airMin
               + " vRail=" + vRail + " vAir=" + vAirEff.tointeger()
               + " tFixe=" + tFixe.tointeger() + " tpd=" + tpd.tointeger());
  }
}

function OpexCatalogBounds(catalog)
{
  if (catalog != null && catalog.bounds != null) return catalog.bounds;
  if (catalog != null) {
    OpexRefreshEpochBounds(catalog);
    if (catalog.bounds != null) return catalog.bounds;
  }
  local busR = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local roadMin = (busR * 2) + 1;
  local railMax = OpexRailDistanceForIterations((HARD_ITERATION_CAP * 12) / 10);
  if (V168_RAIL_MAX_DIST > 0) railMax = V168_RAIL_MAX_DIST;
  return {
    roadMin = roadMin, roadMax = roadMin, roadGenMax = railMax, railMin = roadMin,
    railAirOverlapMin = railMax, railMax = railMax, airMax = 0, airMin = railMax,
    ticksPerDay = 74.0, vRail = 0, vAirEff = 0.0, tFixeAir = 0.0, year = 0,
  };
}

function OpexRoadDistanceAllowed(catalog, distance, stats)
{
  local b = OpexCatalogBounds(catalog);
  if (distance < b.roadMin) {
    stats.roadDistanceShort++;
    return false;
  }
  local roadCap = ("roadGenMax" in b) ? b.roadGenMax : b.roadMax;
  if (distance > roadCap) {
    stats.roadDistanceLong++;
    return false;
  }
  return true;
}

function OpexAirPairInBand(catalog, manhattan, flightDistance, paxBand = PAX_BAND_ALL)
{
  local b = OpexCatalogBounds(catalog);
  if (paxBand == PAX_BAND_AIR_ONLY) {
    if (manhattan <= b.railMax) return false;
  } else if (paxBand == PAX_BAND_AIR_RAIL) {
    if (manhattan < b.railAirOverlapMin || manhattan > b.railMax) return false;
  } else if (manhattan < b.airMin) {
    return false;
  }
  if (b.airMax > 0 && flightDistance > b.airMax) return false;
  return true;
}

function OpexRailPaxPairInBand(bounds, distance, paxBand)
{
  if (paxBand == PAX_BAND_AIR_RAIL) {
    return distance >= bounds.railAirOverlapMin && distance <= bounds.railMax;
  }
  if (paxBand == PAX_BAND_RAIL_ONLY) {
    return distance >= bounds.railMin && distance < bounds.railAirOverlapMin;
  }
  return distance >= bounds.railMin && distance <= bounds.railMax;
}

/* Une origine rail est constructible s'il existe, dans le bassin, une tuile de TERRE qui voit
 * le cargo et qui n'est pas le batiment d'industrie lui-meme. Sans ce test, des origines fret
 * dont tout le bassin est de l'eau (ou du batiment) entraient au TOP_K puis mouraient en SITEA
 * a ~14 M d'opcodes (mesure 2026-08-29, graine 42 : 7 a 15 SITEA fret, nCargo=0, nCmd=0). */
function OpexRailOriginSitable(tile, cargo, coverage, wantProduction)
{
  local radius = coverage + 3;
  for (local r = 0; r <= radius; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local t = tile + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(t)) continue;
        if (AITile.IsWaterTile(t)) continue;
        if (AITile.IsStationTile(t) || AIRail.IsRailTile(t)) continue;
        local industry = AIIndustry.GetIndustryID(t);
        if (AIIndustry.IsValidIndustry(industry)) continue;
        local value = wantProduction
            ? AITile.GetCargoProduction(t, cargo, 1, 1, coverage)
            : AITile.GetCargoAcceptance(t, cargo, 1, 1, coverage);
        if (wantProduction ? (value > 0) : (value >= 8)) return true;
      }
    }
  }
  return false;
}

/* C60 : Rend true si la tolerance municipale est permissive (difficulty.town_council_tolerance == 0).
 * Sous ce reglage de partie, OpenTTD autorise toujours la construction de gares et d'infrastructures
 * independamment de la note de la compagnie. */
function OpexTownCouncilTolerancePermissive()
{
  if (AIGameSettings.IsValid("difficulty.town_council_tolerance")) {
    return AIGameSettings.GetValue("difficulty.town_council_tolerance") == 0;
  }
  return false;
}

/* C60 : Extrait de facon robuste les IDs de ville aux deux extremites d'un candidat ou projet.
 * 1. Lit srcTown/dstTown depuis la charge utile ou le candidat direct (couvre la route,
 *    le rail pax, et le fret a destination/origine urbaine).
 * 2. Pour les liaisons passager, convertit les tuiles via AITile.GetClosestTown si non renseigne.
 * Rend { srcTown = ..., dstTown = ... } avec -1 pour les extremites non urbaines. */
function OpexGetCandidateTownEndpoints(candidate)
{
  local res = { srcTown = -1, dstTown = -1 };
  if (candidate == null) return res;

  local cand = ("payload" in candidate && candidate.payload != null) ? candidate.payload : candidate;

  if (("srcTown" in cand) && cand.srcTown >= 0) res.srcTown = cand.srcTown;
  if (("dstTown" in cand) && cand.dstTown >= 0) res.dstTown = cand.dstTown;

  local isPax = (("kind" in candidate) && candidate.kind == "pax") ||
                (("kind" in cand) && cand.kind == "pax");

  if (isPax) {
    if (res.srcTown < 0) {
      local sTile = ("src" in candidate) ? candidate.src : (("src" in cand) ? cand.src : -1);
      if (AIMap.IsValidTile(sTile)) res.srcTown = AITile.GetClosestTown(sTile);
    }
    if (res.dstTown < 0) {
      local dTile = ("dst" in candidate) ? candidate.dst : (("dst" in cand) ? cand.dst : -1);
      if (AIMap.IsValidTile(dTile)) res.dstTown = AITile.GetClosestTown(dTile);
    }
  }

  return res;
}

/* C60 : Verifie si la note municipale autorise la construction d'une gare.
 * Adapte de SuperLib.Town::TownRatingAllowStationBuilding.
 * 1. Si town_council_tolerance == 0 (permissif), OpenTTD autorise toujours la construction.
 * 2. Sinon, en OpenTTD (town_cmd.cpp), une commune refuse la construction de gare
 *    (ERR_LOCAL_AUTHORITY_REFUSES) si la note de la compagnie est <= TOWN_RATING_VERY_POOR
 *    (<= -200 en note brute).
 * Rend true si tolerance permissive, note == TOWN_RATING_NONE (aucun historique),
 * ou note > TOWN_RATING_VERY_POOR (POOR, MEDIOCRE, GOOD, etc.). */
function OpexTownRatingAllowStation(townId)
{
  if (OpexTownCouncilTolerancePermissive()) return true;
  if (!AITown.IsValidTown(townId)) return false;
  local rating = AITown.GetRating(townId, AICompany.COMPANY_SELF);
  return rating == AITown.TOWN_RATING_NONE || rating > AITown.TOWN_RATING_VERY_POOR;
}

/* C60 : Sonde d'observation d'exposition aux notes municipales. */
function OpexC60ObserveTownRating(mode, phase, townId)
{
  if (!AITown.IsValidTown(townId)) return true;
  local rating = AITown.GetRating(townId, AICompany.COMPANY_SELF);
  /* La sonde doit mesurer exactement le predicat comportemental. En particulier,
   * town_council_tolerance=0 rend la construction permissive quelle que soit la note :
   * compter alors VERY_POOR/APPALLING comme des refus cree une fausse exposition C60. */
  local allowed = OpexTownRatingAllowStation(townId);

  if (C60_TOWN_RATING_LEDGER != null) {
    C60_TOWN_RATING_LEDGER.checks++;
    if (rating == AITown.TOWN_RATING_NONE) C60_TOWN_RATING_LEDGER.none++;
    else if (rating == AITown.TOWN_RATING_APPALLING) C60_TOWN_RATING_LEDGER.appalling++;
    else if (rating == AITown.TOWN_RATING_VERY_POOR) C60_TOWN_RATING_LEDGER.very_poor++;
    else C60_TOWN_RATING_LEDGER.ok++;

    if (mode in C60_TOWN_RATING_LEDGER.by_mode) {
      C60_TOWN_RATING_LEDGER.by_mode[mode].checks++;
      if (!allowed) C60_TOWN_RATING_LEDGER.by_mode[mode].refused++;
    }
  }

  if (!allowed || (DECISION_LOG && rating != AITown.TOWN_RATING_NONE)) {
    local rName = (rating == AITown.TOWN_RATING_NONE) ? "none"
                : ((rating == AITown.TOWN_RATING_APPALLING) ? "appalling"
                : ((rating == AITown.TOWN_RATING_VERY_POOR) ? "very_poor"
                : ((rating == AITown.TOWN_RATING_POOR) ? "poor"
                : ((rating == AITown.TOWN_RATING_MEDIOCRE) ? "mediocre"
                : ((rating == AITown.TOWN_RATING_GOOD) ? "good"
                : ((rating == AITown.TOWN_RATING_VERY_GOOD) ? "very_good"
                : ((rating == AITown.TOWN_RATING_EXCELLENT) ? "excellent"
                : "outstanding")))))));
    OpexDecide("TOWN_RATING_EXPOSURE", "mode=" + mode + " phase=" + phase + " town=" + townId + " rating=" + rating + " rating_name=" + rName + " allow=" + (allowed ? 1 : 0));
  }

  return allowed;
}

function OpexMakeCandidate(catalog, kind, cargo, srcTile, dstTile, monthly, originServed, stats, isTransformer = false, profile = null, cruiseCache = null, secondary = null, joinContext = null)
{
  if (monthly <= 0) {
    stats.noMonthly++;
    return null;
  }
  local distance = AIMap.DistanceManhattan(srcTile, dstTile);
  local bounds = OpexCatalogBounds(catalog);
  if (kind == "pax") {
    if (distance < bounds.railMin) {
      stats.distanceShort++;
      return null;
    }
    /* V177 : en rail seul, les lignes pax courtes rendent 0,19 du capital contre 0,69 pour le
     * fret long (banc railseul_origin_reuse_10x3_20261014) ; 0 = inerte. */
    if (V177_RAIL_PAX_MIN_DIST > 0 && distance < V177_RAIL_PAX_MIN_DIST) {
      stats.distanceShort++;
      return null;
    }
    if (distance > bounds.railMax) {
      stats.distanceLong++;
      return null;
    }
  } else if (distance > bounds.railMax) {
    stats.distanceLong++;
    return null;
  } else if (V182_RAIL_FREIGHT_MIN_DIST > 0 && distance < V182_RAIL_FREIGHT_MIN_DIST
             && !(V195_V182_YEARS > 0 && AIDate.GetYear(AIDate.GetCurrentDate()) >= OPEX_START_YEAR + V195_V182_YEARS)) {
    /* V182 : fret long 47 k/an par ligne contre 30 k pour le court (v181_railseul, 1972). */
    stats.distanceShort++;
    return null;
  }
  /* Plafond A* avant l'economie : les paires trop longues etaient evaluees puis rejetees. */
  local iterations = OpexRailIterations(distance);
  if (V168_RAIL_MAX_DIST <= 0 && iterations > (HARD_ITERATION_CAP * 12) / 10) {
    stats.distanceLong++;
    return null;
  }
  /* Source seulement, et seulement si origin_sitable = 1. Les 7 a 15 SITEA mesures etaient
   * tous du fret a nCargo=0 cote A. Filtrer aussi le puits enlevait des paires urbaines encore
   * constructibles. A 0, le classement est celui d'avant le filtre (SITEA reste possible).
   *
   * MEMO (2026-09-09) : le predicat ne depend que de (srcTile, cargo), jamais de dstTile. Dans
   * la boucle de paires, srcTile est invariant sur toute la liste de voisins d'une meme ville
   * source : sans memo, le balayage en anneaux (jusqu'a ~225 tuiles, un appel natif chacune)
   * etait refait une fois PAR PAIRE au lieu d'une fois par source. Table videe a chaque
   * OpexBuildCandidates -- aucune donnee stale possible : une gare ou un rail bati pres de la
   * source change le resultat, et la generation suivante le recalcule.
   * Cle entiere plutot que chaine : NUM_CARGO <= 64 dans OpenTTD, donc srcTile * 64 + cargo est
   * injectif, et evite de construire une chaine a chaque paire (ce qui aurait coute presque
   * aussi cher que le cas ou le predicat repond des le premier anneau).
   * âš ï¸ profile.paxSitableCalls compte desormais les CALCULS reels, pas les invocations : c'est
   * ce qu'on veut mesurer, mais ce n'est plus comparable aux releves anterieurs au memo.
   *
   * MESURE (2026-09-09, 3 graines x 2 ans, 256x256, c41_rail_pax_candidate_profile=1) :
   * graine 42 865 calculs pour 4 298 appels (5,0x), graine 100 920 pour 4 398 (4,8x),
   * graine 7 1 148 pour 6 197 (5,4x) -- ~100 opcodes par calcul reel. Le facteur de
   * reutilisation est borne par le nombre de voisins a portee d'une ville source : il vaut
   * ~5 sur 256x256 et croit avec la taille de carte, donc le gain est le plus grand la ou il
   * sert le plus (C46, cartes 1024x1024). */
  local sitable = true;
  if (V233_GOODS_GRAFT && joinContext != null) {
    sitable = OpexV233JoinContextValid(joinContext, cargo, srcTile, catalog.railCoverage);
  } else {
    local sitableKey = srcTile * 64 + cargo;
    if (sitableKey in ::OpexSitableCache) {
      sitable = ::OpexSitableCache[sitableKey];
    } else {
      local sitableMark = profile != null ? OpexOpsMeasureBegin() : null;
      sitable = OpexRailOriginSitable(srcTile, cargo, catalog.railCoverage, true);
      if (profile != null) {
        profile.paxSitableOps += OpexOpsMeasureEnd(sitableMark);
        profile.paxSitableCalls++;
      }
      ::OpexSitableCache[sitableKey] <- sitable;
    }
  }
  if (!sitable) {
    stats.unsitable++;
    return null;
  }

  if (V216A_GHOST_DEMAND > 0 && kind == "pax") {
    monthly = OpexV216aScaleDemand(srcTile, dstTile, cargo, monthly);
    if (secondary != null)
      secondary = { cargo = secondary.cargo,
                    monthly = OpexV216aScaleDemand(srcTile, dstTile, secondary.cargo, secondary.monthly) };
    if (monthly <= 0) {
      stats.noMonthly++;
      return null;
    }
  }
  local economicsMark = profile != null ? OpexOpsMeasureBegin() : null;
  /* C41.33 donne le total ; C41.34 le republie avec ses sous-phases afin que les sorties
   * prÃ©coces de OpexLineEconomics restent visibles comme reliquat de prÃ©paration. */
  local freightEconomicsMark = (profile != null && kind == "freight" && (C41_RAIL_FREIGHT_ECONOMICS_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE)) ? OpexOpsMeasureBegin() : null;
  local economics = OpexLineEconomics(catalog, cargo, distance, monthly, kind, 0, null, profile, cruiseCache,
                                      null, null, secondary);
  if (profile != null) {
    profile.paxEconomicsOps += OpexOpsMeasureEnd(economicsMark);
    profile.paxEconomicsCalls++;
  }
  if (freightEconomicsMark != null) {
    profile.freightEconomicsOps += OpexOpsMeasureEnd(freightEconomicsMark);
    profile.freightEconomicsCalls++;
  }
  if (EQUIPMENT_ROI_PROBE) {
    local m3Candidate = { cargo = cargo, distance = distance, monthly = monthly, kind = kind };
    OpexM3ProbeRailEquipment(catalog, m3Candidate, 0, null, economics, "pre_admission");
  }
  if (economics == null) {
    stats.economicsUnavailable++;
    return null;
  }
  /* Un candidat dont le profit annuel attendu est negatif ne merite aucun opcode.
   * L'ancienne famille pax_near (PAX_NEAR fige a false) n'admet plus rien. */
  if (economics.profitAnnual <= 0) {
    stats.profitNonPositive++;
    if (V216_PROBE) OpexV216NoteReject("profit", kind, srcTile, dstTile, monthly, economics);
    if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
    return null;
  }

  local opcodeRatio = (economics.profitAnnual * 1000) / iterations;
  /* MIN_RATIO reste une mesure et le cout d'opportunite terminal du pathfinder, mais il ne peut
   * plus eliminer un mode AVANT l'arbitrage par couple O/D. La contrainte d'opcodes est appliquee
   * apres la contrainte de capital dans projects.nut. */
  local minRatio = (kind == "freight") ? 200 : MIN_RATIO;
  local isLowRatio = (opcodeRatio < minRatio);
  if (isLowRatio) {
    stats.ratioTooLow++;
    if (V216_PROBE) OpexV216NoteReject("ratio", kind, srcTile, dstTile, monthly, economics);
    return null;
  }

  /* Score composite : priorise le fort ROI et le retour sur investissement rapide (cash turnover).
   * Une rotation rapide (oneWayDays court) reinjecte du cash rapidement pour financer les lignes suivantes. */
  local turnoverBonus = 100;
  if (economics.oneWayDays <= 12) turnoverBonus = 130;
  else if (economics.oneWayDays <= 25) turnoverBonus = 115;
  else if (economics.oneWayDays <= 45) turnoverBonus = 100;
  else turnoverBonus = 60;
  /* C32 : un forfait n'est pas une estimation. Le monopole (+40 %) et la chaine (+35 %) deplacaient
   * le classement sans rien predire, et C27 avait deja du les sortir du numerateur de densite parce
   * qu'ils faussaient un diagnostic entier. Tous les modes concourent desormais
   * sur leur ROI estime. */
  local freightBonus = 100;
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE && kind == "freight") {}
  local adjustedRoi = (((economics.roi * turnoverBonus) / 100) * freightBonus) / 100;
  local ratio = opcodeRatio + (adjustedRoi * 15);
  local effectiveRoi = (economics.roi * freightBonus) / 100;

  stats.accepted++;
  local candidate = {
    mode = "rail",
    kind = kind,            // "pax" ou "freight"
    cargo = cargo,
    /* Vrai quand UNE des deux extremites reutilise une origine deja desservie ; le champ
     * alimente le cout de tension fonciere (une seule origine libre consommee). */
    originServed = originServed,
    src = srcTile,
    dst = dstTile,
    distance = distance,
    monthly = monthly,
    trains = economics.trains,
    wagons = economics.wagons,
    perTrain = economics.perTrain,
    platformLength = economics.platformLength,
    loco = economics.loco,
    effectiveSpeed = economics.effectiveSpeed,
    tripsPerMonth = economics.tripsPerMonth,
    headwayDays = economics.headwayDays,
    stationRating = economics.stationRating,
    offered = economics.offered,
    monthlyCapacity = economics.monthlyCapacity,
    trainsForHeadway = economics.trainsForHeadway,
    trainsForVolume = economics.trainsForVolume,
    carried = economics.carried,
    capital = economics.capital,
    vehicleCost = economics.vehicleCost,
    immobilise = ("immobilise" in economics) ? economics.immobilise : 0,
    roi = effectiveRoi,
    /* B6 diagnostic : le bonus de rotation agit sur ratio/TopK en amont, pas sur ce roi. */
    turnoverBonus = turnoverBonus,
    freightBonus = freightBonus,
    isTransformer = isTransformer,
    profitAnnual = economics.profitAnnual,
    /* Detail du calcul, garde pour l'instrumentation predit-vs-reel (cf. main.nut). */
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    iterations = iterations,
    ratio = ratio,
    opcodeRatio = opcodeRatio,
    isLowRatio = isLowRatio,
  };
  /* V163 : le second cargo n'est garde que s'il a trouve place dans la rame. */
  if (("wagons2" in economics) && economics.wagons2 > 0) {
    candidate.cargo2 <- economics.cargo2;
    candidate.monthly2 <- economics.monthly2;
    candidate.wagons2 <- economics.wagons2;
    candidate.perTrain2 <- economics.perTrain2;
    candidate.carried2 <- economics.carried2;
    candidate.revenue2 <- economics.revenue2;
  }
  return candidate;
}

/* Ne garder que les K meilleurs, sans trier les autres.
 *
 * Mesure du 2026-08-28 : trier les 687 candidats coutait 96 803 opcodes, soit 56 % du cout annuel
 * total de l'IA -- alors qu'on ne consomme jamais que la tete du classement. Contrairement au
 * catalogue (ou la mesure a REFUTE l'optimisation), ici elle la justifie. */
function OpexTopK(all, k)
{
  local best = [];
  local floor = 0;      // ratio minimal present dans best, une fois best plein
  foreach (candidate in all) {
    if (best.len() >= k && candidate.ratio <= floor) continue;
    local pos = best.len();
    while (pos > 0 && best[pos - 1].ratio < candidate.ratio) pos--;
    best.insert(pos, candidate);
    if (best.len() > k) best.pop();
    if (best.len() >= k) floor = best[best.len() - 1].ratio;
  }
  return best;
}


/* Exclusion a la GENERATION plutot qu'au FILTRAGE (2026-08-28). Mesure sur graine 42/20 ans
 * (results/opex_full_campaign_20y.json) : les stalles restants de la campagne sont 20/20 candidats du
 * TOP_K rejetes par _tooClose (main.nut) pour la MEME raison -- une origine deja desservie, jamais
 * une proximite physique (near=20/far=0 a chaque annee bloquee). Le classement n'a alors aucune
 * chance de contenir un candidat constructible : TOP_K entier gaspille sur des origines mortes.
 * Exclure ici, avant OpexMakeCandidate, libere le TOP_K pour des candidats reellement
 * constructibles et evite le calcul economique (OpexLineEconomics) sur un candidat deja perdu.
 * Duplique deliberement le test ORIGIN_SEPARATION de _tooClose (meme rayon, meme regle "un seul
 * raccordement par origine") plutot que de changer sa signature : ORIGIN_SEPARATION reste une
 * const globale definie dans main.nut, visible ici car require()d avant toute execution (les
 * fonctions de ce fichier ne s'executent qu'apres que main.nut a fini de se charger).
 *
 * ATTENTION, cette exclusion a ete RAMENEE a son noyau le 2026-08-29 : elle ne vaut plus que pour
 * les paires dont les DEUX extremites sont servies. Une seule extremite servie passe desormais et
 * doit etre recuperee par un quai joint -- voir OpexOriginService plus bas, qui remplace l'appel
 * direct a OpexOriginServed dans les deux generateurs. _tooClose redevient l'autorite sur les deux
 * tests, MIN_SEPARATION comme identite d'origine.
 *
 * `includeRoad` (2026-08-29) : les lignes ROUTIERES vivent dans le meme tableau _lines que le rail
 * (pour etre rapportees et mises au rebut par le meme code), mais elles ne doivent PAS verrouiller
 * une ville pour une liaison rail interurbaine -- une desserte de bus sur 12 tuiles n'epuise pas
 * une ville, et le rail vaut bien davantage par ligne. Les generateurs rail passent donc false, et
 * seul le generateur routier passe true : lui doit s'exclure du rail ET de ses propres lignes,
 * sans quoi il rebatirait chaque annee la meme paire. */
function OpexOriginServed(lines, tile, includeRoad)
{
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "rail" && (!includeRoad || line.mode != "road")) continue;
    if (AIMap.DistanceManhattan(tile, line.originA) < ORIGIN_SEPARATION) return true;
    if (AIMap.DistanceManhattan(tile, line.originB) < ORIGIN_SEPARATION) return true;
  }
  return false;
}

/* C41.18 : index spatial exact de la meme predicate que OpexOriginServed(..., true).
 * ORIGIN_SEPARATION = 3 est petit : materialiser son losange de rayon 2 pour chaque extremite
 * economise les appels DistanceManhattan repetees sur toutes les villes et industries. Ce helper
 * est volontairement local au fret route ; rail et controles de construction gardent
 * l'autorite historique OpexOriginServed. */
function OpexRoadFreightServedIndex(lines)
{
  local served = {};
  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  local radius = ORIGIN_SEPARATION - 1;
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "rail" && line.mode != "road") continue;
    local origins = [line.originA, line.originB];
    foreach (origin in origins) {
      local ox = AIMap.GetTileX(origin);
      local oy = AIMap.GetTileY(origin);
      for (local dx = -radius; dx <= radius; dx++) {
        local x = ox + dx;
        if (x < 0 || x >= width) continue;
        local dyLimit = radius - abs(dx);
        for (local dy = -dyLimit; dy <= dyLimit; dy++) {
          local y = oy + dy;
          if (y < 0 || y >= height) continue;
          served.rawset(AIMap.GetTileIndex(x, y), true);
        }
      }
    }
  }
  return served;
}

/* C41.20 : les villes qui n'acceptent pas une unite pleine ne pourront jamais devenir un puits
 * fret. La liste est construite une fois par cargo et garde l'ordre croissant historique des
 * villes ; la boucle source->ville conserve donc l'ordre de tous les candidats admissibles. */
function OpexRoadFreightAcceptedTowns(towns, servedTown, cargo, truckCoverage)
{
  local accepted = [];
  for (local t = 0; t < towns.len(); t++) {
    if (servedTown[t]) continue;
    local acceptance = AITile.GetCargoAcceptance(towns[t].tile, cargo, 1, 1, truckCoverage);
    if (acceptance >= ROAD_ACCEPTANCE_FULL_UNIT) accepted.append(t);
  }
  return accepted;
}

/* Etat d'une origine face aux lignes RAIL deja baties. Rend null si elle est libre, sinon la ligne
 * qui la sert et l'extremite concernee -- ou une table dont `blocked` est vrai quand plusieurs
 * gares DISTINCTES la servent. Les lignes non ferroviaires sont ignorees. */
function OpexOriginService(lines, tile)
{
  local found = null;
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    foreach (lineEnd in ["A", "B"]) {
      local originTile = lineEnd == "A" ? line.originA : line.originB;
      if (AIMap.DistanceManhattan(tile, originTile) >= ORIGIN_SEPARATION) continue;
      local stationId = OpexLineStationId(line, lineEnd);
      local service = { line = line, lineEnd = lineEnd, stationId = stationId, blocked = false };
      if (found == null) {
        found = service;
      } else if (found.stationId != stationId) {
        return { line = null, lineEnd = "", stationId = -1, blocked = true };
      }
    }
  }
  return found;
}

/* Part de la production TOTALE d'une ville qui tombe dans le rayon de couverture d'UNE gare.
 * CALIBRE le 2026-08-28 (meme mesure que STATION_RATING_PCT ci-dessus) : en isolant le facteur
 * note de gare (mesure separement via AIStation.GetCargoRating), le residu -- production reelle
 * ayant atteint la gare divisee par AITown.GetLastMonthProduction -- vaut 8 a 37 % selon la
 * ligne, moyenne 22 % sur 9 lignes pax reelles. C'etait le biais deja signale, non calibre, dans
 * le commentaire precedent : AITown.GetLastMonthProduction porte sur la ville ENTIERE, une gare
 * n'en couvre qu'un rayon local. Domine le gap x10 predit/reel bien plus que STATION_RATING_PCT
 * (~1,4x seulement) : voir results/opex_predict_vs_actual.json.
 * Ne s'applique QU'aux paires de villes : une industrie produit depuis une seule tuile, elle n'a
 * pas cette dilution geometrique -- non mesure ici, donc non touche. */
const TOWN_CATCHMENT_SHARE_PCT = 22;

/* Paires de villes pour les passagers. */
function OpexPaxCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, candidateProfile = null, cruiseCache = null, paxBand = PAX_BAND_ALL, targetKind = null, targetId = -1)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local served = [];
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  for (local i = 0; i < n; i++) {
    local p = AITown.GetLastMonthProduction(towns[i].id, cargo);
    if (p <= 0 && towns[i].pop > 0) p = (towns[i].pop * 22) / 100;
    produced.append(p);
    local service = OpexOriginService(lines, towns[i].tile);
    served.append(service);
    if (service != null) stats.townsServed++; else stats.townsUnserved++;
  }
  local hasMail = V207_RAIL_MAIL && catalog.mailCargo >= 0 && (catalog.mailCargo in catalog.wagonByCargo);
  local mailProduced = null;
  if (hasMail) {
    mailProduced = [];
    for (local i = 0; i < n; i++) {
      local mp = AITown.GetLastMonthProduction(towns[i].id, catalog.mailCargo);
      if (mp < 0) mp = 0;
      mailProduced.append(mp);
    }
  }
  if (profile != null) profile.paxPreparationOps += OpexOpsMeasureEnd(preparationMark);
  local pairTotalMark = profile != null ? OpexOpsMeasureBegin() : null;
  local bounds = OpexCatalogBounds(catalog);
  local cellSize = bounds.railMax;
  if (cellSize < 1) cellSize = 1;
  local grid = OpexSpatialGrid();
  grid.Build(towns, cellSize);
  for (local a = 0; a < n; a++) {
    local neighbors = grid.GetCandidatesFor(a);
    foreach (b in neighbors) {
      if (targetKind == "town" && targetId >= 0
          && towns[a].id != targetId && towns[b].id != targetId) continue;
      local pairDistance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (!OpexRailPaxPairInBand(bounds, pairDistance, paxBand)) continue;
      if (C60_TOWN_RATING_PROBE) {
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[a].id);
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[b].id);
      }
      if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
      if (abandonedPairs != null) {
        local tA = towns[a].id;
        local tB = towns[b].id;
        if (tA > tB) { local swap = tA; tA = tB; tB = swap; }
        local pairKey = "pax|" + cargo + "|" + tA + "|" + tB;
        if (pairKey in abandonedPairs) continue;
      }
      stats.pairsTotal++;
      if (profile != null) profile.paxPairsScanned++;
      local sa = served[a];
      local sb = served[b];
      if (sa != null || sb != null) {
        stats.pairsOriginServed++;
        continue;
      }
      /* Une ligne dessert les deux sens, et chaque sens transporte la production de SON
       * origine : le debit utile est la somme, pas le minimum. On ignore encore la croissance de
       * la ville que la desserte provoque (sous-estimation non calibree, plus petite que le
       * facteur ci-dessus d'apres la mesure). */
      local prodA = produced[a];
      local prodB = produced[b];
      local part = V207_RAIL_PAX_SHARE_PCT > 0 ? V207_RAIL_PAX_SHARE_PCT : TOWN_CATCHMENT_SHARE_PCT;
      local monthly = ((prodA + prodB) * part) / 100;
      local secondary = null;
      if (hasMail) {
        local mailA = mailProduced[a];
        local mailB = mailProduced[b];
        local mailMonthly = ((mailA + mailB) * part) / 100;
        secondary = { cargo = catalog.mailCargo, monthly = mailMonthly };
      }
      local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
      local candidate = OpexMakeCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile,
                                          monthly, false, stats, false, candidateProfile, cruiseCache,
                                          secondary);
      if (profile != null) {
        profile.paxCandidateOps += OpexOpsMeasureEnd(candidateMark);
        profile.paxCandidateCalls++;
      }
      if (candidate != null) {
        candidate.srcTown <- towns[a].id;
        candidate.dstTown <- towns[b].id;
        out.append(candidate);
      }
    }
  }
  if (profile != null) profile.paxPairTotalOps += OpexOpsMeasureEnd(pairTotalMark);
}

/* Industries : on n'apparie que des couples producteur/accepteur du MEME cargo, ce qui garde
 * l'etage 1 lineaire en nombre d'industries plutot que quadratique sur tout le catalogue. */
function OpexFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1)
{
  /* C41.44 : les lignes sont immuables pendant une generation ; une ville peut donc reutiliser
   * exactement son resultat OpexOriginService, y compris null et l'etat blocked. */
  local townServiceCache = {};
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local served = [];
  for (local i = 0; i < industries.len(); i++) {
    local service = OpexOriginService(lines, industries[i].tile);
    served.append(service);
    if (service != null) stats.industriesServed++; else stats.industriesUnserved++;
  }
  if (profile != null) profile.freightPreparationOps += OpexOpsMeasureEnd(preparationMark);
  foreach (cargo, sources in catalog.producers) {
    if (freightCargo != null && cargo != freightCargo) continue;
    local hasIndustrySinks = (cargo in catalog.acceptors);
    local hasTownSinks = (cargo in catalog.townAcceptors);
    if (!hasIndustrySinks && !hasTownSinks) continue;
    local sinks = hasIndustrySinks ? catalog.acceptors[cargo] : [];

    foreach (si in sources) {
      local source = industries[si];
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local ss = served[si];
      local others2 = V163_MULTI_CARGO ? OpexV163SourceOtherCargos(catalog, source.id, cargo) : null;
      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
        local di = sinks[k];
        if (di == si) continue;
        if (targetKind == "town") continue;
        if (targetKind == "industry" && targetId >= 0
            && source.id != targetId && industries[di].id != targetId) continue;
        if (abandonedPairs != null) {
          local pairKey = "freight|" + cargo + "|" + source.id + "|" + industries[di].id;
          if (pairKey in abandonedPairs) continue;
        }
        stats.pairsTotal++;
        local sd = served[di];
        /* V179 : source neuve, destination deja desservie : on garde la paire, V178 la rattache. */
        local v179Keep = V179_RAIL_GEN_DEST_SERVED && ss == null && sd != null;
        if (!v179Keep && (ss != null || sd != null)) {
          stats.pairsOriginServed++;
          continue;
        }
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
        local secondary = (others2 != null && others2.len() > 0)
            ? OpexV163SecondaryCargo(others2, industries[di].id) : null;
        local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                            industries[di].tile, monthly, false, stats, isTransformer, profile, cruiseCache,
                                            secondary);
        if (profile != null) {
          profile.freightIndustryCandidateOps += OpexOpsMeasureEnd(candidateMark);
          profile.freightIndustryCandidateCalls++;
        }
        if (candidate != null) {
          if (v179Keep) candidate.v179DestServed <- 1;
          out.append(candidate);
        }
      }
      if (profile != null) profile.freightIndustryOps += OpexOpsMeasureEnd(industryMark);

      /* Livraison des marchandises complexes aux villes acceptatrices (Goods, Food, Mail, etc.) */
      if (hasTownSinks) {
        local townMark = profile != null ? OpexOpsMeasureBegin() : null;
        local townSinks = catalog.townAcceptors[cargo];
        for (local k = 0; k < townSinks.len(); k++) {
          local town = townSinks[k];
          if (targetKind == "industry" && targetId >= 0 && source.id != targetId) continue;
          if (targetKind == "town" && targetId >= 0 && town.id != targetId) continue;
          local townGuardMark = (profile != null && C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE) ? OpexOpsMeasureBegin() : null;
          if (abandonedPairs != null) {
            /* G9Â§1 : utiliser "t" + town.id au lieu de GetIndustryID (qui retourne -1
             * pour une ville), en coherence avec OpexAbandonedPairKey. */
            local pairKey = "freight|" + cargo + "|" + source.id + "|t" + town.id;
            if (pairKey in abandonedPairs) {
              if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
              continue;
            }
          }
          stats.pairsTotal++;
          local townServiceMark = (profile != null && C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE) ? OpexOpsMeasureBegin() : null;
          local st = null;
          if (townServiceCache != null && town.id in townServiceCache) st = townServiceCache[town.id];
          else {
            st = OpexOriginService(lines, town.tile);
            if (townServiceCache != null) townServiceCache[town.id] <- st;
          }
          if (townServiceMark != null) { profile.freightTownServiceOps += OpexOpsMeasureEnd(townServiceMark); profile.freightTownServiceCalls++; }
          if (ss != null || st != null) {
            stats.pairsOriginServed++;
            if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
            continue;
          }
          local townMonthly = monthly;
          if (townMonthly <= 0) {
            if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
            continue;
          }
          if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
          if (C60_TOWN_RATING_PROBE) {
            OpexC60ObserveTownRating("rail", "candidate_gen", town.id);
          }
          if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
          local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
          local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                              town.tile, townMonthly, false, stats, false, profile, cruiseCache);
          if (profile != null) {
            profile.freightTownCandidateOps += OpexOpsMeasureEnd(candidateMark);
            profile.freightTownCandidateCalls++;
          }
          if (candidate != null) {
            candidate.dstTown <- town.id;
            out.append(candidate);
          }
        }
        if (profile != null) profile.freightTownOps += OpexOpsMeasureEnd(townMark);

      }
    }
  }
}

/* Construit et classe tous les candidats. Rend la liste triee par rapport decroissant.
 * `lines` (this._lines de main.nut) sert a exclure les origines deja desservies avant meme de
 * calculer un candidat -- voir OpexOriginServed ci-dessus. */
function OpexRailCandidateStats()
{
  local stats = {
    townsServed = 0, townsUnserved = 0, industriesServed = 0, industriesUnserved = 0,
    pairsTotal = 0, pairsOriginServed = 0,
    noMonthly = 0, unsitable = 0,
    distanceShort = 0, distanceLong = 0, economicsUnavailable = 0,
    profitNonPositive = 0, ratioTooLow = 0, accepted = 0, topKOmitted = 0,
  };
  return stats;
}

function OpexBuildCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, paxProfile = null, paxCandidateProfile = null, paxCruiseCache = null, freightCruiseCache = null, generatePax = true, generateFreight = true, paxBand = PAX_BAND_ALL, freightCargo = null, targetKind = null, targetId = -1)
{
  /* Memo origin_sitable vide a chaque passe de generation : une gare ou un rail bati depuis la
   * derniere passe change le predicat, donc rien n'est reporte d'une passe a l'autre. Portee
   * volontairement plus courte que celle des caches de croisiere (crees dans OpexBuildProjects
   * et passes en parametre) : ici on evite de toucher dix signatures pour un gain deja capte a
   * l'interieur d'une seule passe, ou srcTile est invariant sur toute la liste de voisins. */
  ::OpexSitableCache = {};

  local all = [];
  /* Comptes de rejet : ils se trouvent ici, avant que TOP_K ne masque les candidats restants.
   * Une table explicite evite une closure imbriquee, non portable dans le Squirrel du scenario. */
  local stats = OpexRailCandidateStats();
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}

  /* V166 : seul point d'entree des candidats rail (pax, fret). */
  if (!MODE_RAIL) {
    generatePax = false;
    generateFreight = false;
  }
  local paxMark = profile != null ? OpexOpsMeasureBegin() : null;
  budget.begin();
  if (generatePax) {
    OpexPaxCandidates(catalog, lines, all, stats, abandonedPairs, paxProfile, paxCandidateProfile,
                      paxCruiseCache, paxBand, targetKind, targetId);
  }
  local opsPax = budget.end("cand_pax");
  if (profile != null) profile.paxOps += OpexOpsMeasureEnd(paxMark);

  local freightMark = profile != null ? OpexOpsMeasureBegin() : null;
  budget.begin();
  if (generateFreight) {
    OpexFreightCandidates(catalog, lines, all, stats, abandonedPairs, profile, freightCruiseCache,
                          freightCargo, targetKind, targetId);
  }
  local opsFreight = budget.end("cand_freight");
  if (profile != null) profile.freightOps += OpexOpsMeasureEnd(freightMark);

  if (targetKind != null && targetId >= 0) {
    local targeted = [];
    foreach (candidate in all) {
      local touches = false;
      if (targetKind == "town") {
        touches = (("srcTown" in candidate) && candidate.srcTown == targetId)
            || (("dstTown" in candidate) && candidate.dstTown == targetId)
            || (("extensionTown" in candidate) && candidate.extensionTown == targetId);
      } else if (targetKind == "industry") {
        touches = (("srcIndustry" in candidate) && candidate.srcIndustry == targetId)
            || (("dstIndustry" in candidate) && candidate.dstIndustry == targetId)
            || (("src" in candidate) && AIMap.IsValidTile(candidate.src)
                && AIIndustry.GetIndustryID(candidate.src) == targetId)
            || (("dst" in candidate) && AIMap.IsValidTile(candidate.dst)
                && AIIndustry.GetIndustryID(candidate.dst) == targetId);
      }
      if (touches) targeted.append(candidate);
    }
    all = targeted;
  }

  local topKMark = profile != null ? OpexOpsMeasureBegin() : null;
  budget.begin();
  local best = OpexTopK(all, TOP_K);
  local opsRank = budget.end("cand_rank");
  if (profile != null) profile.topKOps += OpexOpsMeasureEnd(topKMark);

  stats.topKOmitted = all.len() - best.len();

  if (C69_BOTTLENECK_PROBE) {
    OpexC73RecordExamined("rail", stats.pairsTotal);
    if (stats.pairsOriginServed > 0) OpexC73RecordRejection("rail", "origin_served", stats.pairsOriginServed);
    if (stats.noMonthly > 0) OpexC73RecordRejection("rail", "no_monthly", stats.noMonthly);
    if (stats.unsitable > 0) OpexC73RecordRejection("rail", "unsitable", stats.unsitable);
    if (stats.distanceShort > 0) OpexC73RecordRejection("rail", "distance_short", stats.distanceShort);
    if (stats.distanceLong > 0) OpexC73RecordRejection("rail", "distance_long", stats.distanceLong);
    if (stats.economicsUnavailable > 0) OpexC73RecordRejection("rail", "economics_unavailable", stats.economicsUnavailable);
    if (stats.profitNonPositive > 0) OpexC73RecordRejection("rail", "profit_nonpositive", stats.profitNonPositive);
    if (stats.ratioTooLow > 0) OpexC73RecordRejection("rail", "ratio_floor", stats.ratioTooLow);
    OpexC73RecordProduced("rail", all.len(), best.len());
  }

  if (DECISION_LOG) {
    OpexDecide("VIVIER_GEN", "mode=rail produced=" + stats.pairsTotal + " kept=" + all.len());
    if (stats.pairsOriginServed > 0) {
      OpexDecide("VIVIER_REJECT", "reason=origin_served n=" + stats.pairsOriginServed);
    }
    if (stats.noMonthly > 0) {
      OpexDecide("VIVIER_REJECT", "reason=no_monthly n=" + stats.noMonthly);
    }
    if (stats.unsitable > 0) {
      OpexDecide("VIVIER_REJECT", "reason=unsitable n=" + stats.unsitable);
    }
    if (stats.distanceShort > 0) {
      OpexDecide("VIVIER_REJECT", "reason=distance_short n=" + stats.distanceShort);
    }
    if (stats.distanceLong > 0) {
      OpexDecide("VIVIER_REJECT", "reason=distance_long n=" + stats.distanceLong);
    }
    if (stats.economicsUnavailable > 0) {
      OpexDecide("VIVIER_REJECT", "reason=economics_unavailable n=" + stats.economicsUnavailable);
    }
    if (stats.profitNonPositive > 0) {
      OpexDecide("VIVIER_REJECT", "reason=profit_non_positive n=" + stats.profitNonPositive);
    }
    if (stats.ratioTooLow > 0) {
      OpexDecide("VIVIER_REJECT", "reason=ratio_too_low n=" + stats.ratioTooLow);
    }
  }
  if (V216_PROBE) OpexV216FlushRejects();

  return { all = all.len(), candidates = all, best = best,
           bands = OpexBands(all), stats = stats,
           opcodes = opsPax + opsFreight + opsRank, profile = profile };
}

/* Meilleur rapport atteint dans chaque bande de distance.
 *
 * Diagnostic, pas decision : il sert a confronter la FORME de notre modele a la courbe mesuree
 * sur la campagne v3 (optimum profit/iteration a 48-63 tuiles, results/opex_cost_model.json). Si
 * notre modele prefere systematiquement une autre bande, c'est lui qui est faux, pas la mesure. */
BAND_EDGES <- [25, 45, 70, 110, 200];

function OpexBands(all)
{
  local best = [0, 0, 0, 0];
  foreach (candidate in all) {
    for (local i = 0; i < 4; i++) {
      if (candidate.distance >= BAND_EDGES[i] && candidate.distance < BAND_EDGES[i + 1]) {
        if (candidate.ratio > best[i]) best[i] = candidate.ratio;
        break;
      }
    }
  }
  return best;
}

/* --- Candidats ROUTIERS (2026-08-29) ---------------------------------------------------------
 *
 * Le creneau route reste borne a 5--25 tuiles, mais le rail descend maintenant a 5 : ce
 * chevauchement est volontaire. Une gare, une voie et une locomotive amortissent souvent moins
 * bien une liaison courte qu'un camion sans voie ni signaux ; projects.nut mesure pourtant les
 * deux au lieu de graver cette conclusion dans une bande de distance. Les modes se disputent donc
 * bien la meme PAIRE, et le gagnant est celui au meilleur ROI. Le revenu/capital remplit ensuite
 * le budget commun, puis le revenu/opcodes ordonne seulement les projets finances.
 *
 * Trois familles de candidats, la deuxieme et la troisieme etant l'objet meme de la manoeuvre --
 * "des petites lignes courtes avec du cargo" :
 *   1. ville <-> ville, passagers (l'ancienne liaison bus v1, desormais une famille parmi trois) ;
 *   2. industrie -> industrie, un cargo produit par l'une et accepte par l'autre ;
 *   3. industrie -> ville, pour les cargos qu'une ville accepte (biens, nourriture...) -- la
 *      famille la plus dense sur nos cartes, parce que les villes sont nombreuses et proches des
 *      industries de transformation, la ou deux industries appariables sont rarement voisines.
 */
/* ROAD_MIN_DISTANCE / ROAD_MAX_DISTANCE : remplacees par catalog.bounds.roadMin / roadMax. */

/* TOP_K reste une vue de diagnostic propre a la route. La decision d'investissement utilise la
 * liste complete candidates et le portefeuille commun de projects.nut ; ce plafond ne peut donc
 * plus imposer une priorite modale. */
ROAD_TOP_K <- 48;

/* Repere historique de profit, conserve pour RS et les campagnes comparables. Il ne coupe plus
 * aucun candidat rentable avant l'arbitrage modal : profitNonPositive compte le seul rejet
 * economique, profitBelowFloorKept compte les projets positifs sous ce repere qui RESTENT dans
 * le vivier. profitTooLow reste un agregat legacy interne pour compatibilite. Mesure 2026-08-30
 * (results/opex_road_predict_vs_actual.json) : 12 pax, mediane reel/predit 3,91 ; fret temoin 1,21.
 * La valeur n'est donc plus un parametre de decision.
 */
const ROAD_MIN_PROFIT_ANNUAL = 1000;

/* Pas un plancher de calibration -- une regle moteur. AITile.GetCargoAcceptance rend une
 * acceptation en huitiemes d'unite ; le moteur exige 8 (une unite pleine) pour livrer quoi que
 * ce soit. En dessous la gare accepterait le cargo a l'affichage sans que la livraison paie.
 * Renomme le 2026-09-08 (ex ROAD_ACCEPTANCE_MIN) apres avoir failli etre confondu avec les
 * planchers reglables de la famille 2 de l'audit C43/E3 (docs/taches.md) -- jamais expose en
 * reglage, et ne doit pas l'etre : l'abaisser ferait construire des lignes qui ne paient jamais. */
const ROAD_ACCEPTANCE_FULL_UNIT = 8;

/* Cout en "iterations equivalentes" d'une tentative routiere, pour rester dans la meme unite que
 * le rail (1 iteration ~ 2 700 opcodes).
 *
 * Mesure 2026-08-30 (results/opex_road_rb_calibrate.json, panneau RB, campagne TRACEX 5 graines,
 * n = 10). Plan OK mediane 31 440 opcodes (~11,7 iter) contre 20+d ~ 42,5 (rapport 0,29).
 * BASE impliquee plan seul : -9. TRACEX 70-107 k. Le build (mediane 287 k) est maintenant inclus
 * dans expectedOpcodes, comme la transaction rail : l'unite commune ne sert qu'a ordonner sous
 * contrainte de calcul APRES le choix modal par ROI et la selection sous capital.
 */
const ROAD_PLAN_ITERATIONS_BASE = 20;

function OpexRoadIterations(distance)
{
  return ROAD_PLAN_ITERATIONS_BASE + distance;
}

/* Un candidat routier porte les memes champs que son homologue rail (le constructeur de ligne, le
 * rapport annuel et la mise au rebut sont communs), plus ce qu'il faut pour retrouver les sites
 * d'arret : le role de chaque extremite (ville ou industrie) et, pour une ville, son identifiant. */
function OpexMakeRoadCandidate(catalog, kind, cargo, src, dst, srcTown, dstTown, distance,
                               monthly, stats, isTransformer = false)
{
  local engine = (cargo in catalog.roadEngineByCargo) ? catalog.roadEngineByCargo[cargo] : null;
  if (engine == null) {
    stats.noEngine++;
    return null;
  }
  local economics = OpexRoadLineEconomics(catalog, cargo, distance, monthly, engine, kind);
  if (EQUIPMENT_ROI_PROBE) {
    local m3Candidate = {
      cargo = cargo, distance = distance, monthly = monthly, kind = kind, engine = engine
    };
    OpexM3ProbeRoadEquipment(catalog, m3Candidate, distance, null, economics, "pre_admission");
  }
  if (economics == null) {
    stats.economicsUnavailable++;
    return null;
  }
  /* Le plancher historique reste telemetre mais ne peut plus eliminer un mode avant le ROI. */
  if (economics.profitAnnual <= 0) {
    stats.profitTooLow++;
    if ("profitNonPositive" in stats) stats.profitNonPositive++;
    return null;
  }
  if (economics.profitAnnual < ROAD_MIN_PROFIT_ANNUAL) {
    stats.profitTooLow++;
    if ("profitBelowFloorKept" in stats) stats.profitBelowFloorKept++;
  }
  local iterations = OpexRoadIterations(distance);
  local freightBonus = 100;
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE && kind == "freight") {}
  local effectiveRoi = (economics.roi * freightBonus) / 100;
  stats.accepted++;
  return {
    mode = "road",
    kind = kind,
    cargo = cargo,
    src = src,
    dst = dst,
    /* -1 = extremite industrielle : le site d'arret se cherche dans un petit rayon autour de la
     * tuile de l'industrie. Un identifiant de ville >= 0 contraint au contraire la recherche a
     * rester dans cette ville (AITile.GetClosestTown), comme le faisait la v1. */
    srcTown = srcTown,
    dstTown = dstTown,
    distance = distance,
    monthly = monthly,
    engine = engine,
    /* B3 diagnostic-only : garder la cible brute sans remplacer la cible comportementale. */
    vehiclesForVolume = economics.vehiclesForVolume,
    roadBerthCapacity = economics.roadBerthCapacity,
    roadVehicleCap = economics.roadVehicleCap,
    trains = economics.trains,
    carried = economics.carried,
    capital = economics.capital,
    immobilise = ("immobilise" in economics) ? economics.immobilise : 0,
    roi = effectiveRoi,
    freightBonus = freightBonus,
    isTransformer = isTransformer,
    profitAnnual = economics.profitAnnual,
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    effectiveSpeed = economics.effectiveSpeed,
    iterations = iterations,
    ratio = (economics.profitAnnual * 1000) / iterations,
  };
}

function OpexRoadPairServed(lines, tileA, tileB)
{
  if (lines == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if ((AIMap.DistanceManhattan(tileA, line.originA) < ORIGIN_SEPARATION &&
         AIMap.DistanceManhattan(tileB, line.originB) < ORIGIN_SEPARATION) ||
        (AIMap.DistanceManhattan(tileA, line.originB) < ORIGIN_SEPARATION &&
         AIMap.DistanceManhattan(tileB, line.originA) < ORIGIN_SEPARATION)) {
      return true;
    }
  }
  return false;
}

function OpexTownRoadLineCount(lines, townTile)
{
  local count = 0;
  if (lines == null) return 0;
  local townId = AITile.GetClosestTown(townTile);
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if (("cargo" in line) && line.cargo >= 0 && !AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)) continue;
    if (AITile.GetClosestTown(line.originA) == townId ||
        AITile.GetClosestTown(line.originB) == townId) {
      count++;
    }
  }
  return count;
}

/* Une commune passagers appartient a une seule ligne bus de base. Toute croissance ulterieure
 * passe par un projet d'extension de CETTE ligne, jamais par une seconde paire qui cannibalise
 * les memes maisons. */
function OpexTownBusPaxServed(lines, townId)
{
  if (lines == null || townId < 0) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("cargo" in line) || line.cargo < 0 ||
        !AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)) continue;
    local srcTown = ("srcTown" in line && line.srcTown >= 0)
        ? line.srcTown : AITile.GetClosestTown(line.originA);
    if (srcTown == townId) return true;
    local dstTown = ("dstTown" in line && line.dstTown >= 0)
        ? line.dstTown : AITile.GetClosestTown(line.originB);
    if (dstTown == townId) return true;
  }
  return false;
}

/* Familles 2 et 3 : industrie -> industrie, et industrie -> ville.
 *
 * Le sens est ORIENTE (un producteur vers un accepteur) : contrairement au pax, rien ne revient.
 * C'est exactement la lecon du fret rail du 2026-08-28 -- poser OF_FULL_LOAD_ANY au puits d'une
 * ligne a sens unique y bloquait le convoi pour toujours -- et builder_road.nut applique la meme
 * regle aux camions.
 *
 * Aucune dilution de bassin n'est appliquee au producteur : une industrie produit depuis une seule
 * tuile, elle n'a pas la dilution geometrique d'une ville (cf. TOWN_CATCHMENT_SHARE_PCT). */
/* C41.17 : `profile` ne sert qu'a separer le cout du fret en checkpoints candidats. Les trois
 * tranches restent synchrones : aucune ne modifie le vivier ni n'est reprise entre deux tours. */
function OpexRoadFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, freightCargo = null, targetKind = null, targetId = -1)
{
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local towns = catalog.towns;
  local servedIndex = OpexRoadFreightServedIndex(lines);
  local servedIndustry = [];
  for (local i = 0; i < industries.len(); i++) {
    servedIndustry.append(servedIndex != null
        ? (industries[i].tile in servedIndex) : OpexOriginServed(lines, industries[i].tile, true));
  }
  local servedTown = [];
  for (local i = 0; i < towns.len(); i++) {
    servedTown.append(servedIndex != null
        ? (towns[i].tile in servedIndex) : OpexOriginServed(lines, towns[i].tile, true));
  }

  /* L'acceptation d'une ville ne depend que du couple (ville, cargo) : la calculer une fois par
   * couple, et non par paire industrie-ville, evite de repayer AITile.GetCargoAcceptance pour
   * chaque producteur du meme cargo. Cle chaine plutot que table imbriquee : une seule table. */
  local acceptanceCache = {};
  /* Rayon d'une aire de chargement : c'est bien l'empreinte de la gare qu'on projette de poser,
   * pas un rayon arbitraire autour du centre administratif. Lu une fois, il ne change jamais. */
  local truckCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
  if (profile != null) profile.freightPreparationOps += OpexOpsMeasureEnd(preparationMark);

  foreach (cargo, sources in catalog.producers) {
    if (freightCargo != null && cargo != freightCargo) continue;
    if (!(cargo in catalog.roadEngineByCargo)) { stats.noEngine++; continue; }
    /* Les passagers sont traites par la famille 1 : les inclure ici apparierait une industrie a
     * une ville pour un cargo qu'aucune industrie ne produit utilement en volume. */
    if (cargo == catalog.paxCargo) continue;
    local sinks = (cargo in catalog.acceptors) ? catalog.acceptors[cargo] : [];
    /* C41.20 : la liste est locale au cargo et a cette generation. Les appels API anticipes sont
     * purs ; ils ne changent ni l'industrie, ni le filtre de distance, ni l'ordre des candidats. */
    local townTargets = OpexRoadFreightAcceptedTowns(towns, servedTown, cargo, truckCoverage);
    if (townTargets != null) stats.townAcceptancePrefiltered += towns.len() - townTargets.len();

    foreach (si in sources) {
      if (servedIndustry[si]) {
        /* Le code livre saute toute la source. Sous sonde, enumerer seulement les paires
         * qu'il aurait sautees permet de compter ce filtre sans changer son continue. */
        if (C55_ORIGIN_RELAX_PROBE) {
          local source = industries[si];
          foreach (di in sinks) {
            if (di != si) OpexC55OriginRelaxObserve("freight", lines, source.tile,
                industries[di].tile, true, servedIndustry[di]);
          }
          for (local ti = 0; ti < towns.len(); ti++) {
            OpexC55OriginRelaxObserve("freight", lines, source.tile, towns[ti].tile,
                true, servedTown[ti]);
          }
        }
        continue;
      }
      local source = industries[si];
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      if (monthly <= 0) { stats.noMonthly++; continue; }

      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
        local di = sinks[k];
        if (di == si) continue;
        if (targetKind == "town") continue;
        if (targetKind == "industry" && targetId >= 0
            && source.id != targetId && industries[di].id != targetId) continue;
        if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("road", 1);
        if (C55_ORIGIN_RELAX_PROBE) OpexC55OriginRelaxObserve("freight", lines,
            source.tile, industries[di].tile, false, servedIndustry[di]);
        if (servedIndustry[di]) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("road", "origin_served", 1);
          continue;
        }
        local distance = AIMap.DistanceManhattan(source.tile, industries[di].tile);
        if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
        if (abandonedPairs != null) {
          local pairKey = "freight|" + cargo + "|" + source.id + "|" + industries[di].id;
          if (pairKey in abandonedPairs) continue;
        }
        stats.pairsInBand++;
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo, source.tile,
                                                industries[di].tile, -1, -1, distance, monthly,
                                                stats, isTransformer);
        if (candidate != null) out.append(candidate);
      }
      if (profile != null) profile.freightIndustryOps += OpexOpsMeasureEnd(industryMark);

      /* C41.19 pose des marques internes autour des deux appels chers : ne jamais les imbriquer
       * dans la mesure globale town, qui peut traverser un suspend. */
      local townMark = (profile != null && !C41_ROAD_FREIGHT_TOWN_PROFILE)
          ? OpexOpsMeasureBegin() : null;
      /* L'index C41.20 saute les villes deja servies avant la boucle. Les enumerer ici sous
       * sonde conserve exactement cet index et rend ce second site de rejet visible. */
      if (C55_ORIGIN_RELAX_PROBE && townTargets != null) {
        for (local ti = 0; ti < towns.len(); ti++) {
          OpexC55OriginRelaxObserve("freight", lines, source.tile, towns[ti].tile,
              false, servedTown[ti]);
        }
      }
      local townPool = (townTargets != null) ? townTargets : towns;
      for (local k = 0; k < townPool.len(); k++) {
        local ti = k;
        local t = (townTargets != null) ? townTargets[ti] : ti;
        if (targetKind == "industry" && targetId >= 0 && source.id != targetId) continue;
        if (targetKind == "town" && targetId >= 0 && towns[t].id != targetId) continue;
        if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("road", 1);
        if (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE) profile.freightTownScanned++;
        if (C55_ORIGIN_RELAX_PROBE && townTargets == null) OpexC55OriginRelaxObserve("freight",
            lines, source.tile, towns[t].tile, false, servedTown[t]);
        if (townTargets == null && servedTown[t]) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("road", "origin_served", 1);
          continue;
        }
        local distance = AIMap.DistanceManhattan(source.tile, towns[t].tile);
        if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
        if (abandonedPairs != null) {
          /* G9Â§1 : "t" + towns[t].id, en coherence avec OpexAbandonedPairKey. */
          local pairKey = "freight|" + cargo + "|" + source.id + "|t" + towns[t].id;
          if (pairKey in abandonedPairs) continue;
        }
        local acceptance;
        if (townTargets != null) {
          /* L'index a deja verifie acceptance >= 8. Ne pas reecrire townRejected : son compteur
           * historique de paires filtrees n'est pertinent que sur le chemin exhaustif OFF. */
          acceptance = ROAD_ACCEPTANCE_FULL_UNIT;
        } else {
          local key = t + "|" + cargo;
          if (key in acceptanceCache) {
            acceptance = acceptanceCache[key];
            if (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE) profile.freightTownAcceptanceHits++;
          } else {
            local acceptanceMark = (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE)
                ? OpexOpsMeasureBegin() : null;
            acceptance = AITile.GetCargoAcceptance(towns[t].tile, cargo, 1, 1, truckCoverage);
            acceptanceCache.rawset(key, acceptance);
            if (acceptanceMark != null) {
              profile.freightTownAcceptanceOps += OpexOpsMeasureEnd(acceptanceMark);
              profile.freightTownAcceptanceMisses++;
            }
          }
        }
        if (acceptance < ROAD_ACCEPTANCE_FULL_UNIT) { stats.townRejected++; continue; }
        stats.pairsInBand++;
        if (C60_TOWN_RATING_PROBE) {
          OpexC60ObserveTownRating("road", "candidate_gen", towns[t].id);
        }
        if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
        local candidateMark = (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE)
            ? OpexOpsMeasureBegin() : null;
        local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo, source.tile,
                                                towns[t].tile, -1, towns[t].id, distance, monthly,
                                                stats);
        if (candidateMark != null) {
          profile.freightTownCandidateOps += OpexOpsMeasureEnd(candidateMark);
          profile.freightTownAcceptedPairs++;
        }
        if (candidate != null) out.append(candidate);
      }
      if (townMark != null) profile.freightTownOps += OpexOpsMeasureEnd(townMark);

    }
  }
}

/* Classement routier complet. Rendu a part de celui du rail : les deux ne partagent ni leur unite
 * de cout (cf. ROAD_PLAN_ITERATIONS_BASE) ni leur phase de construction. */
/* C41.16 : `profile` est fourni seulement par la sonde du scheduler. Il n'influence jamais les
 * filtres, l'ordre ni le vivier ; les compteurs mesurent les trois familles et le TopK qui suit
 * le budget historique. */
function OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, freightCargo = null, targetKind = null, targetId = -1)
{
  local all = [];
  local stats = {
    pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0, townAcceptancePrefiltered = 0,
    economicsUnavailable = 0, profitTooLow = 0, profitNonPositive = 0,
    profitBelowFloorKept = 0, accepted = 0,
    /* C43/E3 famille 2 : ROAD_MIN_DISTANCE/ROAD_MAX_DISTANCE mordent-elles ? */
    roadDistanceShort = 0, roadDistanceLong = 0,
  };
  if (catalog.roadType < 0) return { all = 0, best = [], stats = stats, opcodes = 0 };

  budget.begin();
  /* Les marques C41.17 internes ne doivent jamais etre imbriquees dans une mesure globale :
   * un suspend peut sinon faire compter le tick-frontiere deux fois. C41.16 porte deja le total
   * fret de reference ; C41.17 ne publie que ses intervalles disjoints. */
  local freightMark = (profile != null && !C41_ROAD_FREIGHT_PROFILE && !C41_ROAD_FREIGHT_TOWN_PROFILE)
      ? OpexOpsMeasureBegin() : null;
  OpexRoadFreightCandidates(catalog, lines, all, stats, abandonedPairs, profile, freightCargo,
                            targetKind, targetId);
  if (freightMark != null) {
    profile.freightOps += OpexOpsMeasureEnd(freightMark);
  }
  local ops = budget.end("cand_road");

  if (targetKind != null && targetId >= 0) {
    local targeted = [];
    foreach (candidate in all) {
      local touches = false;
      if (targetKind == "town") {
        touches = (("srcTown" in candidate) && candidate.srcTown == targetId)
            || (("dstTown" in candidate) && candidate.dstTown == targetId)
            || (("extensionTown" in candidate) && candidate.extensionTown == targetId);
      } else if (targetKind == "industry") {
        touches = (("srcIndustry" in candidate) && candidate.srcIndustry == targetId)
            || (("dstIndustry" in candidate) && candidate.dstIndustry == targetId)
            || (("src" in candidate) && AIMap.IsValidTile(candidate.src)
                && AIIndustry.GetIndustryID(candidate.src) == targetId)
            || (("dst" in candidate) && AIMap.IsValidTile(candidate.dst)
                && AIIndustry.GetIndustryID(candidate.dst) == targetId);
      }
      if (touches) targeted.append(candidate);
    }
    all = targeted;
  }

  local topKMark = profile != null ? OpexOpsMeasureBegin() : null;
  local best = OpexTopK(all, ROAD_TOP_K);
  if (profile != null) profile.topKOps += OpexOpsMeasureEnd(topKMark);

  if (C69_BOTTLENECK_PROBE) {
    if (stats.noMonthly > 0) OpexC73RecordRejection("road", "no_monthly", stats.noMonthly);
    if (stats.noEngine > 0) OpexC73RecordRejection("road", "no_engine", stats.noEngine);
    if (stats.townRejected > 0) OpexC73RecordRejection("road", "town_rejected", stats.townRejected);
    if (stats.townAcceptancePrefiltered > 0) OpexC73RecordRejection("road", "town_rejected", stats.townAcceptancePrefiltered);
    if (stats.economicsUnavailable > 0) OpexC73RecordRejection("road", "economics_unavailable", stats.economicsUnavailable);
    if (stats.profitNonPositive > 0) OpexC73RecordRejection("road", "profit_nonpositive", stats.profitNonPositive);
    if (stats.roadDistanceShort > 0) OpexC73RecordRejection("road", "distance_short", stats.roadDistanceShort);
    if (stats.roadDistanceLong > 0) OpexC73RecordRejection("road", "distance_long", stats.roadDistanceLong);
    OpexC73RecordProduced("road", all.len(), best.len());
  }

  if (DECISION_LOG) {
    OpexDecide("VIVIER_GEN", "mode=road produced=" + stats.pairsInBand + " kept=" + all.len());
    if (stats.noMonthly > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_no_monthly n=" + stats.noMonthly);
    }
    if (stats.noEngine > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_no_engine n=" + stats.noEngine);
    }
    if (stats.townRejected > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_town_rejected n=" + stats.townRejected);
    }
    if (stats.townAcceptancePrefiltered > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_town_acceptance_prefiltered n=" + stats.townAcceptancePrefiltered);
    }
    if (stats.economicsUnavailable > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_economics_unavailable n=" + stats.economicsUnavailable);
    }
    if (stats.profitNonPositive > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_profit_non_positive n=" + stats.profitNonPositive);
    }
    if (stats.profitBelowFloorKept > 0) {
      OpexDecide("VIVIER_RETAINED", "reason=road_profit_below_floor n=" + stats.profitBelowFloorKept);
    }
    if (stats.roadDistanceShort > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_distance_short n=" + stats.roadDistanceShort);
    }
    if (stats.roadDistanceLong > 0) {
      OpexDecide("VIVIER_REJECT", "reason=road_distance_long n=" + stats.roadDistanceLong);
    }
  }

  /* Le cout de CETTE annee, pas le cumul : budget.get() totalise depuis le debut de la partie, et
   * c'est le debit annuel qui dit si la generation routiere merite sa place. Il est paye meme les
   * annees ou rien n'est bati, donc le panneau RN le porte sans condition (main.nut). */
  return { all = all.len(), candidates = all, best = best,
           stats = stats, opcodes = ops, profile = profile };
}

/* Rehausse la reputation municipale aupres de l'autorite locale en plantant des arbres.
 * Cout : ~40 Â£ par arbre, gain : +7 points de note par arbre plante (plafond standard +220).
 * Empeche le blocage ERR_LOCAL_AUTHORITY_REFUSES lors des constructions urbaines. */
function OpexBoostTownRating(townId, targetRating = 700, maxTrees = 35)
{
  if (!AITown.IsValidTown(townId)) return;
  /* âš ï¸ AITown.GetRating rend un ENUM de 0 a 8 (script_town.hpp:83 : NONE, APPALLING, VERY_POOR,
   * POOR, MEDIOCRE, GOOD, VERY_GOOD, EXCELLENT, OUTSTANDING), PAS la note brute -1000..1000.
   * Le garde historique comparait cet enum aux `targetRating` 100/700/800 passes par les
   * appelants : la condition etait donc TOUJOURS fausse et la fonction plantait `maxTrees`
   * arbres a chaque appel, quelle que soit la note deja acquise.
   *
   * Planter ne sert qu'en dessous de RATING_TREE_MAXIMUM = 220 en note brute : tree_cmd.cpp:591
   * appelle ChangeTownRating(t, +7, 220), qui ne monte la note que `if (rating < max)`. Au-dessus,
   * chaque arbre est une depense a rendement strictement nul. 220 tombe juste au-dessus de
   * l'echelon MEDIOCRE (note brute <= 200), d'ou le plafond ci-dessous.
   *
   * `targetRating` n'est plus lu : aucun appelant ne peut exprimer un seuil utile sur cette
   * echelle. Le parametre reste dans la signature pour ne pas toucher aux quatre sites d'appel.
   *
   * Effet au reglage par defaut : AUCUN. La plantation preventive est coupee (tree_planting = 0)
   * et le seul appel vivant est le recours reactif de builder_air.nut, ou la ville vient
   * precisement de refuser -- donc note brute <= -200, tres en dessous du plafond. Ce correctif
   * repare la plantation preventive pour le jour ou on la remesure : c'est le garde mort qui
   * explique mecaniquement son -22,1 % de valeur (info.nut, tree_planting). */
  local currentRating = AITown.GetRating(townId, AICompany.COMPANY_SELF);
  if (currentRating != AITown.TOWN_RATING_NONE &&
      currentRating > AITown.TOWN_RATING_MEDIOCRE) return;

  local center = AITown.GetLocation(townId);
  local planted = 0;
  local radius = 7;

  for (local dx = -radius; dx <= radius && planted < maxTrees; dx++) {
    for (local dy = -radius; dy <= radius && planted < maxTrees; dy++) {
      local tile = center + AIMap.GetTileIndex(dx, dy);
      if (!AIMap.IsValidTile(tile)) continue;
      if (AITile.GetClosestTown(tile) != townId) continue;
      if (AITile.IsBuildable(tile)) {
        if (AITile.PlantTree(tile)) {
          planted++;
        }
      }
    }
  }
}

/* C42 : Verifie si une offre de subvention est deja couverte par une ligne du reseau (tout mode).
 * Recherche toujours dynamiquement dans les lignes actives vivantes (sans cache fige pour survivre a la mise au rebut). */
function OpexSubsidyMatchingLineId(sub, lines)
{
  if (sub == null || lines == null) return -1;

  local cargo = sub.cargo;
  local srcType = sub.srcType;
  local srcId = sub.srcId;
  local dstType = sub.dstType;
  local dstId = sub.dstId;

  foreach (line in lines) {
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("cargo" in line) || line.cargo != cargo) continue;
    local tA = ("srcTown" in line && line.srcTown >= 0) ? line.srcTown : (("originA" in line && AIMap.IsValidTile(line.originA)) ? AITile.GetClosestTown(line.originA) : -1);
    local tB = ("dstTown" in line && line.dstTown >= 0) ? line.dstTown : (("originB" in line && AIMap.IsValidTile(line.originB)) ? AITile.GetClosestTown(line.originB) : -1);

    // Liaison ville <-> ville (passagers, courrier, valeurs) : verification bidirectionnelle
    if (srcType == AISubsidy.SPT_TOWN && dstType == AISubsidy.SPT_TOWN) {
      if ((tA == srcId && tB == dstId) || (tA == dstId && tB == srcId)) return line.lineId;
    } else {
      local mSrc = false;
      local mDst = false;
      if (srcType == AISubsidy.SPT_INDUSTRY && ("srcIndustry" in line) && line.srcIndustry == srcId) mSrc = true;
      else if (srcType == AISubsidy.SPT_TOWN && tA == srcId) mSrc = true;
      if (dstType == AISubsidy.SPT_INDUSTRY && ("dstIndustry" in line) && line.dstIndustry == dstId) mDst = true;
      else if (dstType == AISubsidy.SPT_TOWN && tB == dstId) mDst = true;
      if (mSrc && mDst) return line.lineId;
    }
  }
  return -1;
}

/* C42 : Estimation physique du delai de mise en service jusqu'a la 1ere livraison (spec C42, docs/cible.md §5-6) :
 * - 30j de latence d'arbitrage portefeuille (attente du tour de batch mensuel)
 * - 30j pour sortie depot et premier chargement complet a l'arret source
 * - 10j de marge de voirie, carrefours et trafic
 * - oneWayDays : temps de trajet physique aller simple calcule par OpexRoadLineEconomics.
 * Repli minimum si oneWayDays inconnu : 75j. */
function OpexSubsidyChantierDays(oneWayDays = -1)
{
  local setupDays = 70; // 30j cycle + 30j chargement/depot + 10j marge
  if (oneWayDays > 0) return setupDays + oneWayDays;
  return 75;
}

/* C42 : Genere des candidats de portefeuille pour les offres de subvention actives.
 * Une subvention multiplie les revenus par subsidy_multiplier (1.5x a 4x) pendant
 * difficulty.subsidy_duration annees (0 a 5000 annees, defaut 1 an) des la premiere livraison. */
function OpexGenerateSubsidyCandidates(catalog, lines, activeSubsidies, stats, abandonedPairs)
{
  local candidates = [];
  if (activeSubsidies == null || activeSubsidies.len() == 0) return candidates;
  local today = AIDate.GetCurrentDate();
  local roadBounds = OpexCatalogBounds(catalog);

  // Multiplicateur de la partie : difficulty.subsidy_multiplier (0->1.5x, 1->2x, 2->3x, 3->4x)
  local rawMult = AIGameSettings.IsValid("difficulty.subsidy_multiplier")
      ? AIGameSettings.GetValue("difficulty.subsidy_multiplier") : 1;
  local multiplier = (rawMult == 0) ? 1.5 : (rawMult + 1.0);

  // Duree de la subvention : difficulty.subsidy_duration (0 a 5000 annees, defaut 1 an)
  local subsidyDuration = AIGameSettings.IsValid("difficulty.subsidy_duration")
      ? AIGameSettings.GetValue("difficulty.subsidy_duration") : 1;
  if (subsidyDuration <= 0) {
    multiplier = 1.0;
    subsidyDuration = 0;
  }

  foreach (subId, sub in activeSubsidies) {
    if (!AISubsidy.IsValidSubsidy(subId) || AISubsidy.IsAwarded(subId)) continue;

    // Garde 1 : Verification rapide de peremption absolue (> 30j minimum)
    local daysLeft = sub.expDate - today;
    if (daysLeft <= 30) continue;

    // Garde 2 : Disponibilite du vehicule dans le catalogue routier
    local cargo = sub.cargo;
    if (!(cargo in catalog.roadEngineByCargo)) continue;
    local engine = catalog.roadEngineByCargo[cargo];
    if (engine == null) continue;

    // Garde 3 : Localisation source et destination
    local srcTile = -1;
    local dstTile = -1;
    local srcTown = -1;
    local dstTown = -1;

    if (sub.srcType == AISubsidy.SPT_TOWN) {
      if (!AITown.IsValidTown(sub.srcId)) continue;
      srcTile = AITown.GetLocation(sub.srcId);
      srcTown = sub.srcId;
    } else if (sub.srcType == AISubsidy.SPT_INDUSTRY) {
      if (!AIIndustry.IsValidIndustry(sub.srcId)) continue;
      srcTile = AIIndustry.GetLocation(sub.srcId);
    }

    if (sub.dstType == AISubsidy.SPT_TOWN) {
      if (!AITown.IsValidTown(sub.dstId)) continue;
      dstTile = AITown.GetLocation(sub.dstId);
      dstTown = sub.dstId;
    } else if (sub.dstType == AISubsidy.SPT_INDUSTRY) {
      if (!AIIndustry.IsValidIndustry(sub.dstId)) continue;
      dstTile = AIIndustry.GetLocation(sub.dstId);
    }

    if (!AIMap.IsValidTile(srcTile) || !AIMap.IsValidTile(dstTile)) continue;

    // Garde 4 : Production source et acceptation destination
    local isPax = AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS);
    local kind = isPax ? "pax" : "freight";
    local monthlyProd = 0;

    // 4a. Production a la source
    if (sub.srcType == AISubsidy.SPT_INDUSTRY) {
      monthlyProd = AIIndustry.GetLastMonthProduction(sub.srcId, cargo);
      if (monthlyProd <= 0) continue;
    } else {
      local pop = AITown.GetPopulation(sub.srcId);
      if (pop < 150) continue;
      monthlyProd = AITown.GetLastMonthProduction(sub.srcId, cargo);
      if (monthlyProd <= 0) {
        monthlyProd = isPax ? (pop * 15) / 100 : 20;
      }
      if (monthlyProd <= 0) monthlyProd = 20;
    }

    // 4b. Acceptation a la destination (systematique, cf. C42 revue [P2])
    if (sub.dstType == AISubsidy.SPT_INDUSTRY) {
      if (!AIIndustry.IsCargoAccepted(sub.dstId, cargo)) continue;
    } else if (sub.dstType == AISubsidy.SPT_TOWN && !isPax) {
      local truckRadius = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
      if (AITile.GetCargoAcceptance(dstTile, cargo, 1, 1, truckRadius) < ROAD_ACCEPTANCE_FULL_UNIT) continue;
    }

    // Garde 5 : Distance Manhattan dans les bornes routieres
    local distance = AIMap.DistanceManhattan(srcTile, dstTile);
    local maxDist = ("roadGenMax" in roadBounds) ? roadBounds.roadGenMax : roadBounds.roadMax;
    if (distance < roadBounds.roadMin || distance > maxDist) continue;

    // Garde 6 : Liaison deja desservie par le reseau ou abandonnee
    if (abandonedPairs != null) {
      local aKey = "subsidy|" + subId;
      if (aKey in abandonedPairs) continue;
    }

    // 6a. Offre deja couverte par une ligne existante (tout mode confondu : air, rail, route)
    local matched = OpexSubsidyMatchingLineId(sub, lines);
    if (matched >= 0) continue;

    // 6b. Ligne de meme subId deja batie par OpexAI
    local alreadyServed = false;
    foreach (l in lines) {
      if (("isSubsidy" in l) && l.isSubsidy && ("subsidyId" in l) && l.subsidyId == subId) {
        alreadyServed = true;
        break;
      }
    }
    if (alreadyServed) continue;

    // 6c. Gardes physiques routieres : ne pas generer de candidat qui sera refuse au batch
    if (isPax) {
      if (OpexRoadPairServed(lines, srcTile, dstTile)) continue;
      if (OpexTownRoadLineCount(lines, srcTile) >= 4 || OpexTownRoadLineCount(lines, dstTile) >= 4) continue;
    } else {
      if (OpexOriginServed(lines, srcTile, true) || OpexOriginServed(lines, dstTile, true)) continue;
    }

    // Evaluation economique de base
    local economics = OpexRoadLineEconomics(catalog, cargo, distance, monthlyProd, engine, kind);
    if (economics == null || economics.profitAnnual <= 0) continue;

    // Garde temporelle physique : comparaison au temps de chantier estime (spec C42)
    local chantierDays = OpexSubsidyChantierDays(economics.oneWayDays);
    if (daysLeft < chantierDays) continue;
    local slackDays = daysLeft - chantierDays;

    // Horizon d'amortissement (tau) du projet pour lisser le bonus temporaire
    local baseRev = economics.revenueAnnual;
    local baseProfit = economics.profitAnnual;
    local totalCapital = economics.capital + (("immobilise" in economics) ? economics.immobilise : 0);
    local tauYears = (baseProfit > 0 && totalCapital > 0) ? (totalCapital.tofloat() / baseProfit) : 1.0;
    if (tauYears < 1.0) tauYears = 1.0;

    // Couverture du bonus sur l'horizon d'amortissement :
    // Si subsidyDuration >= tau, le bonus couvre 100% de la periode de retour sur investissement.
    // Si subsidyDuration < tau, le bonus n'est percu que sur une fraction (subsidyDuration / tau) de l'horizon.
    local bonusCoverage = (subsidyDuration > 0)
        ? ((subsidyDuration.tofloat() < tauYears) ? (subsidyDuration.tofloat() / tauYears) : 1.0)
        : 0.0;
    local effectiveMultiplier = 1.0 + (multiplier - 1.0) * bonusCoverage;

    local subRev = (baseRev * effectiveMultiplier).tointeger();
    local subProfit = subRev - economics.runningAnnual - economics.amortAnnual;
    if (subProfit <= 0) continue;

    local freightBonus = 100;
    local effectiveRoi = (subProfit > 0 && totalCapital > 0) ? (subProfit * 1000) / totalCapital : 0;
    local iterations = OpexRoadIterations(distance);

    candidates.append({
      mode = "road",
      kind = kind,
      cargo = cargo,
      src = srcTile,
      dst = dstTile,
      srcTown = srcTown,
      dstTown = dstTown,
      distance = distance,
      monthly = monthlyProd,
      engine = engine,
      vehiclesForVolume = economics.vehiclesForVolume,
      roadBerthCapacity = economics.roadBerthCapacity,
      roadVehicleCap = economics.roadVehicleCap,
      trains = economics.trains,
      carried = economics.carried,
      capital = economics.capital,
      immobilise = ("immobilise" in economics) ? economics.immobilise : 0,
      roi = effectiveRoi,
      freightBonus = freightBonus,
      isTransformer = false,
      baseProfitAnnual = economics.profitAnnual,
      baseRevenueAnnual = economics.revenueAnnual,
      baseRoi = economics.roi,
      subsidyProfitAnnual = subProfit,
      subsidyRevenueAnnual = subRev,
      subsidyRoi = effectiveRoi,
      profitAnnual = subProfit,
      revenueAnnual = subRev,
      runningAnnual = economics.runningAnnual,
      amortAnnual = economics.amortAnnual,
      oneWayDays = economics.oneWayDays,
      effectiveSpeed = economics.effectiveSpeed,
      iterations = iterations,
      ratio = iterations > 0 ? (subProfit * 1000) / iterations : 0,
      isSubsidy = true,
      subsidyId = subId,
      subsidyMultiplier = multiplier,
      subsidyDuration = subsidyDuration,
      effectiveMultiplier = effectiveMultiplier,
      daysLeft = daysLeft,
      chantierDays = chantierDays,
      slackDays = slackDays
    });

    if (DECISION_LOG) {
      OpexDecide("SUBSIDY_CANDIDATE", "sub=" + subId + " cargo=" + AICargo.GetCargoLabel(cargo)
                 + " dist=" + distance + " mult=" + multiplier + " dur=" + subsidyDuration
                 + " effMult=" + effectiveMultiplier + " daysLeft=" + daysLeft
                 + " chantier=" + chantierDays + " slack=" + slackDays
                 + " profit=" + subProfit + " roi=" + effectiveRoi + " cap=" + economics.capital);
    }
  }

  return candidates;
}
