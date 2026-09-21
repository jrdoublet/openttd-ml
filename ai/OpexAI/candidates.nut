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
        || (COMPLEX_CARGO && cargo in catalog.townAcceptors);
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
VIVIER_RATIO_FILTER <- true;
CLEAN_DENSITY_SCORE <- true;
PROBE_STASH_K <- 12;
/* "Presque admis" : predit > -1000. L'echelle du plancher MIN_RATIO * iterations/1000
 * pour une ligne courte (~500*310/1000 = 155) est plus petite ; -1000 reste du meme
 * ordre qu'une ligne mediocre, pas un gouffre d'amortissement. */
const PROBE_NEAR_ZERO = -1000;

/* Retuning pax borne (suite item 7). Les 11/11 paires pax <=100 tuiles force-construites
 * avec predit -146..-9 etaient rentables en derniere annee ; au-dela de 100 la mediane
 * reelle est 0. On admet cette famille au classement, rien d'autre : pas le fret, pas
 * le long, pas un decalage de OpexLineEconomics. ratio = 1 les place sous tout candidat
 * qui passe MIN_RATIO. _tryBuild les bride a 1 tentative/an au plafond dur.
 * PAX_NEAR_MIN_PROFIT = -200 couvre l'echantillon (-146) sans ouvrir le gouffre. */
const PAX_NEAR_MAX_DISTANCE = 100;
const PAX_NEAR_MIN_PROFIT = -200;
const PAX_NEAR_MAX_ATTEMPTS_PER_YEAR = 1;
const PAX_NEAR_RATIO = 1;

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

/* C60 : Extrait un ID de ville valide depuis une extremite (ID, tuile, ou table). */
function OpexTownIdFromEndpoint(endpoint)
{
  if (endpoint == null) return -1;
  if (typeof endpoint == "table") {
    if ("town" in endpoint && "id" in endpoint.town) return endpoint.town.id;
    if ("srcTown" in endpoint && endpoint.srcTown >= 0) return endpoint.srcTown;
    if ("dstTown" in endpoint && endpoint.dstTown >= 0) return endpoint.dstTown;
    if ("tile" in endpoint) return AITile.GetClosestTown(endpoint.tile);
  }
  if (AITown.IsValidTown(endpoint)) return endpoint;
  if (AIMap.IsValidTile(endpoint)) return AITile.GetClosestTown(endpoint);
  return -1;
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

/* C60 : Rend true si la commune est sans espoir immediat pour la construction de gare.
 * 1. Si mode permissif (tolerance == 0) : jamais de refus municipal, donc jamais sans espoir.
 * 2. Le palier TOWN_RATING_APPALLING couvre les notes brutes de -1000 a -400. Or 40 arbres
 *    apportent jusqu'a +280 points : une note entre -479 et -400 remonte ainsi au-dessus du
 *    seuil de -200 (dans TOWN_RATING_POOR). L'API NoAI ne fournissant pas la note brute,
 *    declarer APPALLING irrecuperable ecarterait des communes que la plantation d'arbres
 *    reactive peut sauver. On rend donc false pour preserver le recours reactif. */
function OpexTownRatingHopeless(townId)
{
  return false;
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

function OpexMakeCandidate(catalog, kind, cargo, srcTile, dstTile, monthly, originServed, stats, isTransformer = false, profile = null, cruiseCache = null)
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
    if (distance > bounds.railMax) {
      stats.distanceLong++;
      return null;
    }
  } else if (distance > bounds.railMax) {
    stats.distanceLong++;
    return null;
  }
  /* Plafond A* avant l'economie : les paires trop longues etaient evaluees puis rejetees. */
  local iterations = OpexRailIterations(distance);
  if (iterations > (HARD_ITERATION_CAP * 12) / 10) {
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
   * ⚠️ profile.paxSitableCalls compte desormais les CALCULS reels, pas les invocations : c'est
   * ce qu'on veut mesurer, mais ce n'est plus comparable aux releves anterieurs au memo.
   *
   * MESURE (2026-09-09, 3 graines x 2 ans, 256x256, c41_rail_pax_candidate_profile=1) :
   * graine 42 865 calculs pour 4 298 appels (5,0x), graine 100 920 pour 4 398 (4,8x),
   * graine 7 1 148 pour 6 197 (5,4x) -- ~100 opcodes par calcul reel. Le facteur de
   * reutilisation est borne par le nombre de voisins a portee d'une ville source : il vaut
   * ~5 sur 256x256 et croit avec la taille de carte, donc le gain est le plus grand la ou il
   * sert le plus (C46, cartes 1024x1024). */
  local sitable = true;
  if (ORIGIN_SITABLE) {
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

  local economicsMark = profile != null ? OpexOpsMeasureBegin() : null;
  /* C41.33 donne le total ; C41.34 le republie avec ses sous-phases afin que les sorties
   * précoces de OpexLineEconomics restent visibles comme reliquat de préparation. */
  local freightEconomicsMark = (kind == "freight" && (C41_RAIL_FREIGHT_ECONOMICS_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE)) ? OpexOpsMeasureBegin() : null;
  local economics = OpexLineEconomics(catalog, cargo, distance, monthly, kind, 0, null, profile, cruiseCache);
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
  /* Un candidat dont le profit annuel attendu est negatif ne merite AUCUN opcode,
   * SAUF la famille pax_near (pax, <=100 tuiles, predit > -200) : le sondage a
   * 40 000 iterations a trouve 11/11 rentables en derniere annee, et le long non.
   * Derriere probe_negative=1, les AUTRES rejets sont ranges pour le force-build. */
  if (economics.profitAnnual <= 0) {
    if (PAX_NEAR && kind == "pax" && distance <= PAX_NEAR_MAX_DISTANCE
        && economics.profitAnnual > PAX_NEAR_MIN_PROFIT) {
      return OpexMakePaxNearCandidate(kind, cargo, srcTile, dstTile, monthly, originServed,
                                      distance, economics, stats);
    }
    stats.profitNonPositive++;
    if (PROBE_NEGATIVE) OpexStashNegative(stats, kind, cargo, srcTile, dstTile, monthly,
                                          originServed, distance, economics);
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
    if (VIVIER_RATIO_FILTER) return null;
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
   * qu'ils faussaient un diagnostic entier. Sous flat_bonus = 0 (defaut), tous les modes concourent
   * sur leur ROI estime. */
  local freightBonus = 100;
  if (FLAT_BONUS && kind == "freight") {
    freightBonus = 140;
    if (isTransformer) freightBonus = (freightBonus * 135) / 100;
  }
  local adjustedRoi = (((economics.roi * turnoverBonus) / 100) * freightBonus) / 100;
  local ratio = opcodeRatio + (adjustedRoi * 15);
  local effectiveRoi = (economics.roi * freightBonus) / 100;

  stats.accepted++;
  return {
    mode = "rail",
    kind = kind,            // "pax" ou "freight"
    cargo = cargo,
    /* Vrai quand UNE des deux extremites reutilise une origine deja desservie : ce candidat n'est
     * constructible que si _tooClose lui trouve un quai joint (cf. OpexOriginService ci-dessous).
     * Sert a l'instrumentation, pas a la decision -- l'autorite reste _tooClose. */
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
}

/* Famille pax_near : meme tableau qu'un candidat classe, ratio = 1 (sous MIN_RATIO),
 * slot paxNear pour que _tryBuild bride a une tentative/an au plafond dur.
 * Un helper evite de copier 30 champs dans le chemin profit>0. */
function OpexMakePaxNearCandidate(kind, cargo, srcTile, dstTile, monthly, originServed,
                                  distance, economics, stats)
{
  stats.paxNearAdmitted++;
  stats.accepted++;
  local candidate = {
    mode = "rail", kind = kind, cargo = cargo, originServed = originServed,
    src = srcTile, dst = dstTile, distance = distance, monthly = monthly,
    trains = economics.trains, wagons = economics.wagons, perTrain = economics.perTrain,
    platformLength = economics.platformLength, loco = economics.loco,
    effectiveSpeed = economics.effectiveSpeed, tripsPerMonth = economics.tripsPerMonth,
    headwayDays = economics.headwayDays, stationRating = economics.stationRating,
    offered = economics.offered, monthlyCapacity = economics.monthlyCapacity,
    trainsForHeadway = economics.trainsForHeadway, trainsForVolume = economics.trainsForVolume,
    carried = economics.carried, capital = economics.capital, roi = economics.roi,
    profitAnnual = economics.profitAnnual, revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual, amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    iterations = OpexRailIterations(distance),
    ratio = PAX_NEAR_RATIO,
  };
  candidate.paxNear <- true;
  return candidate;
}

/* Histogramme de TOUTES les paires a profit <= 0, plus les PROBE_STASH_K moins negatives.
 * Appele seulement si probe_negative = 1 : a 0, OpexMakeCandidate rend null comme avant
 * et le classement ne paie aucune de ces recopies. */
function OpexStashNegative(stats, kind, cargo, srcTile, dstTile, monthly, originServed,
                           distance, economics)
{
  if (kind == "pax") stats.negPax++; else stats.negFreight++;
  if (distance < 50) stats.negBand50++;
  else if (distance < 75) stats.negBand75++;
  else if (distance < 100) stats.negBand100++;
  else stats.negBand200++;
  if (economics.profitAnnual > PROBE_NEAR_ZERO) stats.negNear++;
  stats.negSum += economics.profitAnnual;
  if (stats.profitNonPositive == 1 || economics.profitAnnual < stats.negMin) {
    stats.negMin = economics.profitAnnual;
  }

  local profit = economics.profitAnnual;
  local stash = stats.negativeStash;
  if (stash.len() >= PROBE_STASH_K && profit <= stash[stash.len() - 1].profitAnnual) return;
  local candidate = {
    kind = kind,
    cargo = cargo,
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
    profitAnnual = profit,
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    /* Inutilise pour le budget : _tryProbeNegative passe alternativeRatio 0
     * (chemin Z, HARD_ITERATION_CAP). ratio = 0 pour qu'un probe ne puisse jamais
     * gagner un TOP_K s'il fuyait dans `all`. */
    iterations = 0,
    ratio = 0,
    probe = true,
  };
  local pos = stash.len();
  while (pos > 0 && stash[pos - 1].profitAnnual < profit) pos--;
  stash.insert(pos, candidate);
  if (stash.len() > PROBE_STASH_K) stash.pop();
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

/* C55 etape 2 : le fret route remplace la proximite geometrique (< ORIGIN_SEPARATION,
 * toutes lignes et tous cargos) par l'identite exacte (cargo, tuile) : c'est bien la regle
 * voulue, un raccordement par origine. Une source et un puits ne portent donc chacun qu'une
 * ligne par cargo ; aucun decompte de production restante n'est necessaire ici, et il reste
 * deliberement hors sujet : ne jamais changer deux choses a la fois.
 * PROPRIETE CLE : busy(cargo, tile) implique une origine route/rail a distance 0, donc
 * OpexOriginServed(lines, tile, true). Le chemin ON ne peut ainsi rejeter que des candidats
 * deja rejetes OFF : il en ajoute, sans jamais en retirer. L'index est construit une fois par
 * generation seulement quand le reglage est actif, jamais dans la boucle cargo x origine x puits. */
function OpexRoadFreightBusyIndex(lines)
{
  local busy = {};
  foreach (line in lines) {
    if (!(("mode" in line) && (line.mode == "rail" || line.mode == "road"))) continue;
    if (!("cargo" in line) || !("originA" in line) || !("originB" in line)) continue;
    busy.rawset(line.cargo + "|" + line.originA, true);
    busy.rawset(line.cargo + "|" + line.originB, true);
  }
  return busy;
}

/* Les revalidations incrementale et de construction ne visitent qu'un candidat : parcourir
 * lines ici evite de payer un index temporaire. */
function OpexRoadFreightBusy(lines, cargo, tile)
{
  foreach (line in lines) {
    if (!(("mode" in line) && (line.mode == "rail" || line.mode == "road"))) continue;
    if (("cargo" in line) && line.cargo == cargo &&
        ((("originA" in line) && line.originA == tile)
         || (("originB" in line) && line.originB == tile))) return true;
  }
  return false;
}

/* C41.20 : les villes qui n'acceptent pas une unite pleine ne pourront jamais devenir un puits
 * fret. La liste est construite une fois par cargo et garde l'ordre croissant historique des
 * villes ; la boucle source->ville conserve donc l'ordre de tous les candidats admissibles. */
function OpexRoadFreightAcceptedTowns(towns, servedTown, cargo, truckCoverage, busy = null)
{
  local accepted = [];
  for (local t = 0; t < towns.len(); t++) {
    if (busy != null ? (cargo + "|" + towns[t].tile in busy) : servedTown[t]) continue;
    local acceptance = AITile.GetCargoAcceptance(towns[t].tile, cargo, 1, 1, truckCoverage);
    if (acceptance >= ROAD_ACCEPTANCE_FULL_UNIT) accepted.append(t);
  }
  return accepted;
}

/* Une origine rail deja servie exclut la paire avant l'etage economique. */

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
      if (found == null) {
        found = { line = line, lineEnd = lineEnd, stationId = stationId, blocked = false };
      } else if (found.stationId != stationId) {
        return { line = null, lineEnd = "", stationId = -1, blocked = true };
      }
    }
  }
  return found;
}

/* Combien de lignes RAIL utilisent deja ce StationID pour ce cargo. Les modes avec un champ
 * `mode` (air, eau, route) n'ont pas de quai rail a partager. */
function OpexStationCargoLineCount(lines, stationId, cargo)
{
  if (stationId < 0) return 0;
  local n = 0;
  foreach (line in lines) {
    if (("mode" in line)) continue;
    if (!("cargo" in line) || line.cargo != cargo) continue;
    if (OpexLineStationId(line, "A") == stationId || OpexLineStationId(line, "B") == stationId) n++;
  }
  return n;
}

/* La part du nouvel arrivant : 1/(n+1) de la production de CETTE extremite, n = lignes deja
 * la. n = 0 (StationID invalide) laisse le montant intact. */
function OpexShareBasin(amount, lines, stationId, cargo)
{
  local n = OpexStationCargoLineCount(lines, stationId, cargo);
  return amount / (n + 1);
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
function OpexPaxCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, candidateProfile = null, cruiseCache = null, paxBand = PAX_BAND_ALL)
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
      local pairDistance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (!OpexRailPaxPairInBand(bounds, pairDistance, paxBand)) continue;
      if (C60_TOWN_RATING_PROBE) {
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[a].id);
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[b].id);
      }
      if (C60_TOWN_RATING_FILTER) {
        if (!OpexTownRatingAllowStation(towns[a].id) || !OpexTownRatingAllowStation(towns[b].id)) continue;
      }
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null) {
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
      local monthly = ((prodA + prodB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
      local candidate = OpexMakeCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile,
                                          monthly, false, stats, false, candidateProfile, cruiseCache);
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
function OpexFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null)
{
  /* C41.44 : les lignes sont immuables pendant une generation ; une ville peut donc reutiliser
   * exactement son resultat OpexOriginService, y compris null et l'etat blocked. */
  local townServiceCache = C41_RAIL_FREIGHT_TOWN_SERVICE_CACHE ? {} : null;
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
    local hasTownSinks = COMPLEX_CARGO && (cargo in catalog.townAcceptors);
    if (!hasIndustrySinks && !hasTownSinks) continue;
    local sinks = hasIndustrySinks ? catalog.acceptors[cargo] : [];

    foreach (si in sources) {
      local source = industries[si];
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local ss = served[si];
      /* Source seulement : le puits n'a pas de production a partager. */
      if (BASIN_SHARE && ss != null) {
        monthly = OpexShareBasin(monthly, lines, ss.stationId, cargo);
      }
      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
        local di = sinks[k];
        if (di == si) continue;
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null) {
          local pairKey = "freight|" + cargo + "|" + source.id + "|" + industries[di].id;
          if (pairKey in abandonedPairs) continue;
        }
        stats.pairsTotal++;
        local sd = served[di];
        if (ss != null || sd != null) {
          stats.pairsOriginServed++;
          continue;
        }
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
        local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                            industries[di].tile, monthly, false, stats, isTransformer, profile, cruiseCache);
        if (profile != null) {
          profile.freightIndustryCandidateOps += OpexOpsMeasureEnd(candidateMark);
          profile.freightIndustryCandidateCalls++;
        }
        if (candidate != null) out.append(candidate);
      }
      if (profile != null) profile.freightIndustryOps += OpexOpsMeasureEnd(industryMark);

      /* Livraison des marchandises complexes aux villes acceptatrices (Goods, Food, Mail, etc.) */
      if (hasTownSinks) {
        local townMark = profile != null ? OpexOpsMeasureBegin() : null;
        local townSinks = catalog.townAcceptors[cargo];
        for (local k = 0; k < townSinks.len(); k++) {
          local town = townSinks[k];
          local townGuardMark = (profile != null && C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE) ? OpexOpsMeasureBegin() : null;
          if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null) {
            /* G9§1 : utiliser "t" + town.id au lieu de GetIndustryID (qui retourne -1
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
          if (C60_TOWN_RATING_FILTER) {
            if (!OpexTownRatingAllowStation(town.id)) continue;
          }
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
function OpexBuildCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, paxProfile = null, paxCandidateProfile = null, paxCruiseCache = null, freightCruiseCache = null, generatePax = true, generateFreight = true, paxBand = PAX_BAND_ALL, freightCargo = null)
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
  local stats = {
    townsServed = 0, townsUnserved = 0, industriesServed = 0, industriesUnserved = 0,
    pairsTotal = 0, pairsOriginServed = 0,
    noMonthly = 0, unsitable = 0,
    distanceShort = 0, distanceLong = 0, economicsUnavailable = 0,
    profitNonPositive = 0, ratioTooLow = 0, accepted = 0, topKOmitted = 0,
  };
  /* Slots de l'item 7 : `<-` seulement a probe_negative=1. A 0, la table de stats
   * est bit a bit celle d'avant ce commit, et OpexMakeCandidate ne les touche pas. */
  if (PROBE_NEGATIVE) {
    stats.negativeStash <- [];
    stats.negBand50 <- 0;
    stats.negBand75 <- 0;
    stats.negBand100 <- 0;
    stats.negBand200 <- 0;
    stats.negPax <- 0;
    stats.negFreight <- 0;
    stats.negNear <- 0;
    stats.negSum <- 0;
    stats.negMin <- 0;
  }
  if (PAX_NEAR) stats.paxNearAdmitted <- 0;

  local paxMark = profile != null ? OpexOpsMeasureBegin() : null;
  budget.begin();
  if (generatePax) {
    OpexPaxCandidates(catalog, lines, all, stats, abandonedPairs, paxProfile, paxCandidateProfile, paxCruiseCache, paxBand);
  }
  local opsPax = budget.end("cand_pax");
  if (profile != null) profile.paxOps += OpexOpsMeasureEnd(paxMark);

  local freightMark = profile != null ? OpexOpsMeasureBegin() : null;
  budget.begin();
  if (generateFreight) {
    OpexFreightCandidates(catalog, lines, all, stats, abandonedPairs, profile, freightCruiseCache, freightCargo);
  }
  local opsFreight = budget.end("cand_freight");
  if (profile != null) profile.freightOps += OpexOpsMeasureEnd(freightMark);

  local topKMark = profile != null ? OpexOpsMeasureBegin() : null;
  budget.begin();
  local best = OpexTopK(all, TOP_K);
  local opsRank = budget.end("cand_rank");
  if (profile != null) profile.topKOps += OpexOpsMeasureEnd(topKMark);

  stats.topKOmitted = all.len() - best.len();

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

  return { all = all.len(), candidates = all, best = best,
           bands = OpexBands(all), stats = stats, opcodes = opsPax + opsFreight + opsRank,
           profile = profile };
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
  if (FLAT_BONUS && kind == "freight") {   /* C32 : voir OpexMakeCandidate */
    freightBonus = 140;
    if (isTransformer) freightBonus = (freightBonus * 135) / 100;
  }
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

/* C23 : Modélisation physique du bassin de captage d'un arrêt de bus (rayon 3 tuiles).
 *
 * Un arrêt de bus OpenTTD possède un rayon de couverture de 3 tuiles, soit une empreinte
 * de 7x7 = 49 tuiles. Compte tenu du réseau viaire et des espaces publics, un arrêt couvre
 * physiquement au maximum ~20 maisons (ROAD_STOP_CATCHMENT_HOUSES = 20).
 * La part de captage d'une ville ayant H maisons est donc bornée par :
 *   pct = min(ROAD_PAX_CATCHMENT_SHARE_PCT, (ROAD_STOP_CATCHMENT_HOUSES * 100) / H)
 * Si H <= 0 ou non disponible, repli physique sur pop / 25.
 */
function OpexTownBusCatchment(town, marginalProd)
{
  if (marginalProd <= 0) return 0;
  local houses = ("houses" in town && town.houses > 0) ? town.houses : (town.pop / 25);
  if (houses <= 0) houses = 1;
  local pct = (ROAD_STOP_CATCHMENT_HOUSES * 100) / houses;
  if (pct > ROAD_PAX_CATCHMENT_SHARE_PCT) pct = ROAD_PAX_CATCHMENT_SHARE_PCT;
  if (pct < 1) pct = 1;
  local captured = (marginalProd * pct) / 100;
  return captured > 0 ? captured : 1;
}

/* Famille 1 : ville <-> ville, passagers. */
function OpexRoadPaxCandidates(catalog, lines, out, stats, abandonedPairs = null)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local roadLinesPerTown = [];
  local busServed = [];
  for (local i = 0; i < n; i++) {
    local p = AITown.GetLastMonthProduction(towns[i].id, cargo);
    /* D4 : Calibrage physique de la production mensuelle moyenne de passagers par habitant (~15 % en OpenGFX/OpenTTD) */
    if (p <= 0 && towns[i].pop > 0) p = (towns[i].pop * 15) / 100;
    produced.append(p);
    roadLinesPerTown.append(OpexTownRoadLineCount(lines, towns[i].tile));
    busServed.append(OpexTownBusPaxServed(lines, towns[i].id));
  }
  local roadBounds = OpexCatalogBounds(catalog);
  local roadCell = ("roadGenMax" in roadBounds) ? roadBounds.roadGenMax : roadBounds.roadMax;
  if (roadCell < 1) roadCell = 1;
  local roadGrid = OpexSpatialGrid();
  roadGrid.Build(towns, roadCell);
  for (local a = 0; a < n; a++) {
    if (busServed[a]) continue;
    local maxLinesA = 4 + (towns[a].pop / 300);
    if (roadLinesPerTown[a] >= maxLinesA) continue;
    local neighbors = roadGrid.GetCandidatesFor(a);
    foreach (b in neighbors) {
      if (busServed[b]) continue;
      local maxLinesB = 4 + (towns[b].pop / 300);
      if (roadLinesPerTown[b] >= maxLinesB) continue;
      if (OpexRoadPairServed(lines, towns[a].tile, towns[b].tile)) continue;
      if (C60_TOWN_RATING_PROBE) {
        OpexC60ObserveTownRating("road", "candidate_gen", towns[a].id);
        OpexC60ObserveTownRating("road", "candidate_gen", towns[b].id);
      }
      if (C60_TOWN_RATING_FILTER) {
        if (!OpexTownRatingAllowStation(towns[a].id) || !OpexTownRatingAllowStation(towns[b].id)) continue;
      }
      local distance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (distance < roadBounds.roadMin || distance > roadBounds.roadMax) {
        if (distance < roadBounds.roadMin) stats.roadDistanceShort++;
        else stats.roadDistanceLong++;
        continue;
      }
      if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null) {
        local tA = towns[a].id;
        local tB = towns[b].id;
        if (tA > tB) { local swap = tA; tA = tB; tB = swap; }
        local pairKey = "pax|" + cargo + "|" + tA + "|" + tB;
        if (pairKey in abandonedPairs) continue;
      }
      stats.pairsInBand++;
      local marginalA = produced[a] - (roadLinesPerTown[a] * 40);
      if (marginalA < 25) marginalA = 25;
      local marginalB = produced[b] - (roadLinesPerTown[b] * 40);
      if (marginalB < 25) marginalB = 25;
      local capturedA = OpexTownBusCatchment(towns[a], marginalA);
      local capturedB = OpexTownBusCatchment(towns[b], marginalB);
      local monthly = ROAD_PAX_OVERLAP
          ? OpexRoadPaxUniqueMonthly(capturedA, capturedB, distance)
          : capturedA + capturedB;
      if (monthly <= 0) { stats.noMonthly++; continue; }
      local candidate = OpexMakeRoadCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile,
                                              towns[a].id, towns[b].id, distance, monthly, stats);
      if (candidate != null) out.append(candidate);
    }
  }
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
function OpexRoadFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, freightCargo = null)
{
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local towns = catalog.towns;
  local servedIndex = C41_ROAD_FREIGHT_SERVED_INDEX ? OpexRoadFreightServedIndex(lines) : null;
  local freightBusy = C55_FREIGHT_ORIGIN_RELAX ? OpexRoadFreightBusyIndex(lines) : null;
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
    local townTargets = C41_ROAD_FREIGHT_ACCEPTANCE_INDEX
        ? OpexRoadFreightAcceptedTowns(towns, servedTown, cargo, truckCoverage, freightBusy) : null;
    if (townTargets != null) stats.townAcceptancePrefiltered += towns.len() - townTargets.len();

    foreach (si in sources) {
      if (freightBusy == null && servedIndustry[si]) {
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
      local sourceBusy = freightBusy != null && (cargo + "|" + source.tile in freightBusy);
      /* Une source occupee voit DEJA toutes ses paires rejetees plus bas (le "|| sourceBusy" des
       * deux boucles) : les enumerer quand meme couterait puits + villes opcodes pour rien, dans
       * la boucle la plus chaude de la generation. Sortir ici ne change aucun candidat produit.
       * Inerte a reglage 0 : freightBusy y vaut null, donc sourceBusy est toujours faux. */
      if (sourceBusy) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      if (monthly <= 0) { stats.noMonthly++; continue; }

      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
        local di = sinks[k];
        if (di == si) continue;
        if (C55_ORIGIN_RELAX_PROBE) OpexC55OriginRelaxObserve("freight", lines,
            source.tile, industries[di].tile, sourceBusy, servedIndustry[di]);
        if (freightBusy != null
            ? ((servedIndustry[si] && servedIndustry[di]) || sourceBusy ||
               (cargo + "|" + industries[di].tile in freightBusy)) : servedIndustry[di]) {
          continue;
        }
        local distance = AIMap.DistanceManhattan(source.tile, industries[di].tile);
        if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null) {
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
              sourceBusy, servedTown[ti]);
        }
      }
      local townPool = (townTargets != null) ? townTargets : towns;
      for (local k = 0; k < townPool.len(); k++) {
        local ti = k;
        local t = (townTargets != null) ? townTargets[ti] : ti;
        if (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE) profile.freightTownScanned++;
        if (C55_ORIGIN_RELAX_PROBE && townTargets == null) OpexC55OriginRelaxObserve("freight",
            lines, source.tile, towns[t].tile, sourceBusy, servedTown[t]);
        if (freightBusy != null) {
          if ((servedIndustry[si] && servedTown[t]) || sourceBusy ||
              (cargo + "|" + towns[t].tile in freightBusy)) continue;
        } else if (townTargets == null && servedTown[t]) {
          continue;
        }
        local distance = AIMap.DistanceManhattan(source.tile, towns[t].tile);
        if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
        if (ABANDON_GEN_FILTER && ABANDON_MEMORY && abandonedPairs != null) {
          /* G9§1 : "t" + towns[t].id, en coherence avec OpexAbandonedPairKey. */
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
        if (C60_TOWN_RATING_FILTER) {
          if (!OpexTownRatingAllowStation(towns[t].id)) continue;
        }
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
function OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, freightCargo = null)
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
  /* L'option n'exclut que les nouvelles liaisons bus pax ville-a-ville. Les camions restent
   * dans le portefeuille. */
  if (ROAD_PAX_BUILD_ENABLED) {
    local mark = profile != null ? OpexOpsMeasureBegin() : null;
    OpexRoadPaxCandidates(catalog, lines, all, stats, abandonedPairs);
    if (profile != null) profile.paxOps += OpexOpsMeasureEnd(mark);
  }
  /* Les marques C41.17 internes ne doivent jamais etre imbriquees dans une mesure globale :
   * un suspend peut sinon faire compter le tick-frontiere deux fois. C41.16 porte deja le total
   * fret de reference ; C41.17 ne publie que ses intervalles disjoints. */
  local freightMark = (profile != null && !C41_ROAD_FREIGHT_PROFILE && !C41_ROAD_FREIGHT_TOWN_PROFILE)
      ? OpexOpsMeasureBegin() : null;
  OpexRoadFreightCandidates(catalog, lines, all, stats, abandonedPairs, profile, freightCargo);
  if (freightMark != null) {
    profile.freightOps += OpexOpsMeasureEnd(freightMark);
  }
  local ops = budget.end("cand_road");

  local topKMark = profile != null ? OpexOpsMeasureBegin() : null;
  local best = OpexTopK(all, ROAD_TOP_K);
  if (profile != null) profile.topKOps += OpexOpsMeasureEnd(topKMark);

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
 * Cout : ~40 £ par arbre, gain : +7 points de note par arbre plante (plafond standard +220).
 * Empeche le blocage ERR_LOCAL_AUTHORITY_REFUSES lors des constructions urbaines. */
function OpexBoostTownRating(townId, targetRating = 700, maxTrees = 35)
{
  if (!AITown.IsValidTown(townId)) return;
  /* ⚠️ AITown.GetRating rend un ENUM de 0 a 8 (script_town.hpp:83 : NONE, APPALLING, VERY_POOR,
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
