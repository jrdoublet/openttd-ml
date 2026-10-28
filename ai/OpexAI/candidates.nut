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
  if (V276_CAND_SLICES > 0 && catalog != null) return OpexV276CargoOrder(catalog);
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
    local hasRail = catalog.wagonByCargo != null && (cargo in catalog.wagonByCargo)
        && (catalog.locoByCargoWagons == null || (cargo in catalog.locoByCargoWagons));
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

function OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, ticksPerDay, probe = null)
{
  local roadMin = (AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP) * 2) + 1;
  if (bestBus == null || bestTrain == null || catalog.paxCargo < 0) {
    if (probe != null) probe.reason = (catalog.paxCargo < 0) ? "no_pax"
        : (bestBus == null ? "no_bus" : "no_train");
    return roadMin;
  }

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
  if (probe != null) {
    probe.deltaM = deltaM;
    probe.num = num;
  }
  if (deltaM <= 0) {
    if (probe != null) probe.reason = "nonpositive_income_edge";
    return roadMin;
  }
  /* GetCargoIncome livre ici le gain TOTAL a refD, pas un gain par tuile.
   * L'equation qui isole d doit soustraire deux coefficients par tuile. */
  local deltaPerTile = deltaM.tofloat() / refD.tofloat();

  /* r_cible = 0,40 : ROI annuel vise pour amortir le capital fixe ferroviaire. */
  local denom = ((12.0 * M * deltaPerTile * 100.0) / 40.0) - cTile;
  if (probe != null) probe.denom = denom;
  if (denom <= 0) {
    if (probe != null) probe.reason = "nonpositive_denom";
    return roadMin;
  }
  if (num <= 0) {
    if (probe != null) probe.reason = "nonpositive_num";
    return roadMin;
  }
  local d = num / denom;
  if (probe != null) {
    probe.rawRoad = d;
    probe.reason = d < roadMin ? "below_road_min"
        : (d.tointeger() == roadMin ? "truncated_to_min" : "computed_road");
  }
  if (d < roadMin) d = roadMin;
  return d.tointeger();
}

function OpexComputeRailToAirDistance(bestTrain, bestPlane, ticksPerDay, airportType, probe = null)
{
  if (bestTrain == null || bestPlane == null) return OpexMapManhattanSpan();
  local planeDiv = OpexPlaneSpeedDivisor();
  local vRail = bestTrain.speed.tofloat();
  local vAir = AIEngine.GetMaxSpeed(bestPlane).tofloat() / planeDiv;
  local tauRail = OpexDaysPerTile(vRail, ticksPerDay);
  local tauAir = OpexDaysPerTile(vAir, ticksPerDay);
  local tFixe = OpexAirManeuverDays(bestPlane, airportType, airportType, ticksPerDay, planeDiv);
  if (probe != null) {
    probe.tauRail = tauRail;
    probe.tauAir = tauAir;
    probe.tFixe = tFixe;
  }
  if (tauRail <= tauAir) {
    if (probe != null) {
      probe.reason = "rail_as_fast";
      probe.rawRailAir = OpexMapManhattanSpan();
    }
    return OpexMapManhattanSpan();
  }
  local d = tFixe / (tauRail - tauAir);
  if (probe != null) {
    probe.rawRailAir = d;
    probe.reason = "physical";
  }
  if (d < 1.0) d = 1.0;
  return d.tointeger();
}

/* FRONT-PAX-2 : comparaison CINEMATIQUE avec les memes jours/tuile pour
 * les deux modes et la vitesse avion API directe. Calcul pur par combinaison
 * de moteur/type d'aeroport (jamais de C121, de sondage ou d'A* par paire).
 * Le chargement AIR et le residu des hubs restent inconnus en amont de C121 :
 * seul le tick initial minimum de chargement est inclus ici. C121 conserve
 * ensuite la validation economique complete, jamais un ROI extrapole. */
function OpexFP2PhysicalBoundary(bounds, planeSpeed, typeA, typeB, wagon)
{
  if (bounds == null || bounds.vRail <= 0 || planeSpeed <= 0 || wagon == null
      || wagon.capacity <= 0 || typeA == null || typeB == null
      || !AIAirport.IsValidAirportType(typeA)
      || !AIAirport.IsValidAirportType(typeB)) return -1;
  local tauRail = 1.0 / (0.036 * bounds.vRail.tofloat());
  local tauAir = 1.0 / (0.036 * planeSpeed.tofloat());
  if (tauRail <= tauAir) return -1;
  local tpd = bounds.ticksPerDay > 0 ? bounds.ticksPerDay : 74.0;
  local taxiSpeed = planeSpeed < 50 ? planeSpeed.tofloat() : 50.0;
  local footprint = (AIAirport.GetAirportWidth(typeA)
      + AIAirport.GetAirportHeight(typeA)
      + AIAirport.GetAirportWidth(typeB)
      + AIAirport.GetAirportHeight(typeB)).tofloat();
  local groundTiles = footprint * 2.0 / 3.0;
  local groundDays = groundTiles * OpexDaysPerTile(taxiSpeed, tpd) + 300.0 / tpd;
  local railDwell = OpexRailStationDwellDays(wagon);
  local numerator = groundDays + 1.0 / tpd - railDwell;
  local crossing = numerator > 0.0 ? numerator / (tauRail - tauAir) : 0.0;
  if (crossing >= bounds.airMin) return -1;
  /* First integral distance where AIR is at least as fast. */
  local first = crossing.tointeger();
  if (first.tofloat() < crossing) first++;
  if (first < bounds.railMin) first = bounds.railMin;
  return first < bounds.airMin ? first : -1;
}

/* Le croisement sur Manhattan ne suffit pas quand les ancres aeroport sont
 * eloignees. Verifier le vrai vol (deja mesure par le scan), sans nouvel appel
 * de C121 ni geometrie; le meme forfait sol est celui de la frontiere. */
function OpexFP2PhysicalPairWins(bounds, planeSpeed, wagon,
                                 manhattan, flightDistance, groundDays)
{
  if (bounds == null || bounds.vRail <= 0 || planeSpeed <= 0 || wagon == null
      || wagon.capacity <= 0 || flightDistance <= 0 || manhattan <= 0
      || groundDays < 0.0) return false;
  local tpd = bounds.ticksPerDay > 0 ? bounds.ticksPerDay : 74.0;
  local airDays = flightDistance.tofloat() / (0.036 * planeSpeed.tofloat())
      + groundDays + 1.0 / tpd;
  local railDays = manhattan.tofloat() / (0.036 * bounds.vRail.tofloat())
      + OpexRailStationDwellDays(wagon);
  return airDays <= railDays;
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

  local fp1Mark = FRONT_PAX1_CLAMP_PROBE ? OpexOpsMeasureBegin() : null;
  local bestBus = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_ROAD, pax) : null;
  local bestTrain = (pax >= 0) ? OpexGetEpochRailProfile(catalog, pax, 20) : null;
  local bestPlane = (pax >= 0) ? OpexGetEpochVehicle(AIVehicle.VT_AIR, pax) : null;

  /* FRONT-PAX-1: sonde locale transitoire, jamais incluse dans catalog,
   * Save/Load, tri, ni construction. Un seul releve par refresh des bornes. */
  local fp1Probe = FRONT_PAX1_CLAMP_PROBE
      ? { reason = "unknown", deltaM = -1, num = -1, denom = -1, rawRoad = -1 }
      : null;
  local roadMax = OpexComputeRoadToRailDistance(catalog, bestBus, bestTrain, tpd, fp1Probe);
  if (roadMax < roadMin) roadMax = roadMin;
  local mapSpan = OpexMapManhattanSpan();
  if (roadMax > mapSpan) roadMax = mapSpan;

  local iterCap = (HARD_ITERATION_CAP * 12) / 10;
  local railMax = OpexRailDistanceForIterations(iterCap);
  /* V168 : la table de noeuds date d'un ancien A* ; au banc rail contre rail du 13/10, les
   * recherches de 80-94 tuiles prennent 2 204 iterations medianes contre 7 745 predites, et
   * AAAHogEx pose ses lignes a 117 tuiles medianes. Le reglage remplace la borne derivee. */
  if (V168_RAIL_MAX_DIST > 0) railMax = V168_RAIL_MAX_DIST;
  if (V294_RAIL_DIST_DECOUPLE > 0) railMax = V294_RAIL_DIST_DECOUPLE;
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
  if (ROAD1Y_DIST_BANDS && ROAD_MAX_TRACE_TILES > roadGenMax) roadGenMax = ROAD_MAX_TRACE_TILES;

  local airportType = (catalog.airport != null) ? catalog.airport.type : null;
  local railAir = railMax;
  local tFixe = 0.0;
  local vRail = 0;
  local vAirEff = 0.0;
  local fp1AirProbe = FRONT_PAX1_CLAMP_PROBE
      ? { reason = "no_plane", tauRail = -1, tauAir = -1, tFixe = -1, rawRailAir = -1 }
      : null;
  if (bestPlane != null && bestTrain != null) {
    railAir = OpexComputeRailToAirDistance(bestTrain, bestPlane, tpd, airportType, fp1AirProbe);
    vRail = bestTrain.speed;
    vAirEff = AIEngine.GetMaxSpeed(bestPlane).tofloat() / OpexPlaneSpeedDivisor();
    tFixe = OpexAirManeuverDays(bestPlane, airportType, airportType, tpd, OpexPlaneSpeedDivisor());
  } else if (bestPlane != null) {
    railAir = roadMax;
    if (fp1AirProbe != null) fp1AirProbe.reason = "no_train";
  }
  local fp1RailAirRaw = FRONT_PAX1_CLAMP_PROBE ? railAir : -1;

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

  if (FRONT_PAX1_CLAMP_PROBE) {
    /* Inclut les calculs de bornes, avant les journaux ; le coût du journal
     * lui-même est distinct. Les valeurs -1 signifient non calculé. */
    local fp1Ops = OpexOpsMeasureEnd(fp1Mark);
    local fp1Clamp = fp1RailAirRaw > mapSpan ? "map_span"
        : (fp1RailAirRaw < roadMax ? "road_max"
        : (fp1RailAirRaw > railMax ? "rail_max" : "none"));
    /* OpexDecide modifie _currentTaskLogged : journaliser directement
     * pour garantir la passivite, y compris pendant un TASK actif. */
    local fp1Date = AIDate.GetCurrentDate();
    AILog.Info("OPEX " + AIDate.GetYear(fp1Date) + "-"
        + AIDate.GetMonth(fp1Date) + "-" + AIDate.GetDayOfMonth(fp1Date)
        + " FRONT_PAX_CLAMP road_reason=" + fp1Probe.reason
        + " road_raw=" + fp1Probe.rawRoad + " road_final=" + roadMax
        + " road_min=" + roadMin + " deltaM=" + fp1Probe.deltaM
        + " num=" + fp1Probe.num + " denom=" + fp1Probe.denom
        + " air_reason=" + fp1AirProbe.reason
        + " air_clamp=" + fp1Clamp
        + " rail_air_raw=" + fp1RailAirRaw
        + " rail_air_physical=" + fp1AirProbe.rawRailAir
        + " rail_air_final=" + railAir + " rail_max=" + railMax
        + " map_span=" + mapSpan + " airport_type="
        + (airportType == null ? -1 : airportType)
        + " rail_speed=" + vRail + " air_speed=" + vAirEff
        + " air_fixed=" + tFixe + " tau_rail=" + fp1AirProbe.tauRail
        + " tau_air=" + fp1AirProbe.tauAir + " tpd=" + tpd
        + " ops=" + fp1Ops);
  }

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
  if (V294_RAIL_DIST_DECOUPLE > 0) railMax = V294_RAIL_DIST_DECOUPLE;
  return {
    roadMin = roadMin, roadMax = roadMin, roadGenMax = railMax, railMin = roadMin,
    railAirOverlapMin = railMax, railMax = railMax, airMax = 0, airMin = railMax,
    ticksPerDay = 74.0, vRail = 0, vAirEff = 0.0, tFixeAir = 0.0, year = 0,
  };
}

/* DIST-BORNES-1 ON : un seul contrat des distances de candidature par mode.
 * Donnees uniquement derives de catalog.bounds, aucune API ni mutation.
 * OFF utilise toujours les anciennes branches de chaque consommateur.
 * maxDistance=-1 designe l'absence de plafond Manhattan (AIR). */
function OpexDistBornesWindow(bounds, mode, pax = false, paxBand = PAX_BAND_ALL)
{
  if (mode == "road") {
    if (ROAD1Y_DIST_BANDS && ROAD1Y_DIST_BAND >= 0) {
      local band = ROAD1Y_DIST_BAND_LIMITS[ROAD1Y_DIST_BAND];
      local bandMin = band[0] > bounds.roadMin ? band[0] : bounds.roadMin;
      return { minDistance = bandMin, maxDistance = band[1], flightMax = 0 };
    }
    local maxDist = ("roadGenMax" in bounds) ? bounds.roadGenMax : bounds.roadMax;
    if (ROAD1Y_DIST_BANDS && ROAD_MAX_TRACE_TILES > maxDist) maxDist = ROAD_MAX_TRACE_TILES;
    return { minDistance = bounds.roadMin,
      maxDistance = maxDist,
      flightMax = 0 };
  }
  if (mode == "rail") {
    if (!pax) {
      local cap = bounds.railMax;
      local relaxed = V269_RAIL_LATE_RELAX > 0 && (V269_RELAXED
          || (("distBornesV269Relaxed" in bounds) && bounds.distBornesV269Relaxed));
      if (relaxed && V269_RAIL_MAX_DIST > cap) cap = V269_RAIL_MAX_DIST;
      return { minDistance = 0, maxDistance = cap, flightMax = 0 };
    }
    if (paxBand == PAX_BAND_AIR_RAIL) {
      return { minDistance = bounds.railAirOverlapMin,
        maxDistance = bounds.railMax, flightMax = 0 };
    }
    if (paxBand == PAX_BAND_RAIL_ONLY) {
      return { minDistance = bounds.railMin,
        maxDistance = bounds.railAirOverlapMin - 1, flightMax = 0 };
    }
    return { minDistance = bounds.railMin, maxDistance = bounds.railMax, flightMax = 0 };
  }
  if (mode == "air") {
    if (paxBand == PAX_BAND_AIR_ONLY) {
      return { minDistance = bounds.railMax + 1,
        maxDistance = -1, flightMax = bounds.airMax };
    }
    if (paxBand == PAX_BAND_AIR_RAIL) {
      return { minDistance = bounds.railAirOverlapMin,
        maxDistance = bounds.railMax, flightMax = bounds.airMax };
    }
    return { minDistance = bounds.airMin, maxDistance = -1, flightMax = bounds.airMax };
  }
  return null;
}

function OpexDistBornesAllows(window, manhattan, flightDistance = 0)
{
  if (window == null || manhattan < window.minDistance) return false;
  if (window.maxDistance >= 0 && manhattan > window.maxDistance) return false;
  if (window.flightMax > 0 && flightDistance > window.flightMax) return false;
  return true;
}

function OpexRoadDistanceAllowed(catalog, distance, stats)
{
  local b = OpexCatalogBounds(catalog);
  /* ROAD1Y : pendant une generation par bandes, seule la bande courante compte. */
  if (ROAD1Y_DIST_BANDS && ROAD1Y_DIST_BAND >= 0) {
    local band = ROAD1Y_DIST_BAND_LIMITS[ROAD1Y_DIST_BAND];
    local bandMin = band[0] > b.roadMin ? band[0] : b.roadMin;
    if (distance < bandMin) { stats.roadDistanceShort++; return false; }
    if (distance > band[1]) { stats.roadDistanceLong++; return false; }
    return true;
  }
  if (DIST_BORNES_UNIFIED) {
    local w = OpexDistBornesWindow(b, "road");
    if (distance < w.minDistance) { stats.roadDistanceShort++; return false; }
    if (distance > w.maxDistance) { stats.roadDistanceLong++; return false; }
    return true;
  }
  if (distance < b.roadMin) {
    stats.roadDistanceShort++;
    return false;
  }
  local roadCap = ("roadGenMax" in b) ? b.roadGenMax : b.roadMax;
  if (ROAD1Y_DIST_BANDS && ROAD_MAX_TRACE_TILES > roadCap) roadCap = ROAD_MAX_TRACE_TILES;
  if (distance > roadCap) {
    stats.roadDistanceLong++;
    return false;
  }
  return true;
}

function OpexAirPairInBand(catalog, manhattan, flightDistance, paxBand = PAX_BAND_ALL)
{
  local b = OpexCatalogBounds(catalog);
  if (DIST_BORNES_UNIFIED)
    return OpexDistBornesAllows(OpexDistBornesWindow(b, "air", true, paxBand),
        manhattan, flightDistance);
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
  if (DIST_BORNES_UNIFIED)
    return OpexDistBornesAllows(OpexDistBornesWindow(bounds, "rail", true, paxBand), distance);
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

function OpexMakeCandidate(catalog, kind, cargo, srcTile, dstTile, monthly, originServed, stats, isTransformer = false, profile = null, cruiseCache = null, secondary = null, longGood = false)
{
  if (monthly <= 0) {
    stats.noMonthly++;
    return null;
  }
  local distance = AIMap.DistanceManhattan(srcTile, dstTile);
  local bounds = OpexCatalogBounds(catalog);
  if (V233_LONG_GOOD > 0 && longGood) {
    if (distance < 150 || distance > 300) { stats.distanceLong++; return null; }
  } else if (DIST_BORNES_UNIFIED) {
    local w = OpexDistBornesWindow(bounds, "rail", kind == "pax");
    if (distance < w.minDistance) {
      stats.distanceShort++;
      return null;
    }
    if (distance > w.maxDistance) {
      stats.distanceLong++;
      return null;
    }
  } else if (kind == "pax") {
    if (distance < bounds.railMin) {
      stats.distanceShort++;
      return null;
    }
    if (distance > bounds.railMax) {
      stats.distanceLong++;
      return null;
    }
  } else if (distance > ((V269_RAIL_LATE_RELAX > 0
      && (V269_RELAXED || (DIST_BORNES_V276_FREIGHT
          && ("distBornesV269Relaxed" in bounds) && bounds.distBornesV269Relaxed))
      && V269_RAIL_MAX_DIST > bounds.railMax) ? V269_RAIL_MAX_DIST : bounds.railMax)) {
    stats.distanceLong++;
    return null;
  }
  local iterations = OpexRailIterations(distance);
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
                                      null, null, secondary, longGood);
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

/* P1 : le balayage industriel normal voit deja les paires, y compris celles rejetees
 * par railMax. Garder seulement les metadonnees du meilleur long trajet : aucun
 * calcul economique, cache de site ou A* en shadow ; un unique calcul en ON apres
 * la passe. Le produit en flottant evite un debordement entier sur grosse industrie. */
function OpexP1LongOffer(state, catalog, cargo, source, sink, monthly, transformer)
{
  if (state == null || monthly <= 0) return false;
  /* Au plus 4096 comparaisons proxy sur le passage C121 existant : un
   * catalogue dense n'introduit pas un nouveau budget d'opcodes non borne. */
  if (state.scanned >= 4096) return false;
  state.scanned++;
  local dist = AIMap.DistanceManhattan(source.tile, sink.tile);
  if (dist < 160 || dist > 300 || dist <= OpexCatalogBounds(catalog).railMax) return false;
  state.observed++;
  local score = monthly.tofloat() * dist;
  local prev = state.best;
  if (prev == null || score > prev.score
      || (score == prev.score && (source.tile < prev.src
          || (source.tile == prev.src && (sink.tile < prev.dst
              || (sink.tile == prev.dst && cargo < prev.cargo)))))) {
    state.best = { cargo = cargo, src = source.tile, dst = sink.tile,
                   monthly = monthly, transformer = transformer,
                   distance = dist, score = score };
  }
  return true;
}

/* Une seule evaluation de modele de profit/site par generation C121 ; la source
 * et le puits sont toujours des industries, admissibles au worker C80. */
function OpexP1LongEvaluate(catalog, state, stats)
{
  if (state == null || state.best == null || P1_RAIL_LONG_VALUE_RANK != 2
      || OpexV190Active()) return null;
  local pair = state.best;
  /* Une copie locale de la borne admise uniquement pour le devis de cette
   * paire : le catalogue du jeu, son railMax et ses bornes AIR restent intacts.
   * Le chemin historique OpexMakeCandidate garde sa signature et ses octets. */
  local localCatalog = clone catalog;
  localCatalog.bounds = clone OpexCatalogBounds(catalog);
  localCatalog.bounds.railMax = pair.distance;
  local candidate = OpexMakeCandidate(localCatalog, "freight", pair.cargo, pair.src, pair.dst,
      pair.monthly, false, stats, pair.transformer);
  if (candidate == null || candidate.trains != 1 || candidate.profitAnnual < 25000
      || candidate.roi < 150) return null;
  candidate.p1Long <- true;
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
function OpexRoadFreightServedIndex(lines, cargoFilter = null)
{
  local served = {};
  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  local radius = ORIGIN_SEPARATION - 1;
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "rail" && line.mode != "road") continue;
    /* ROAD100-22 : une gare COAL n'epuise ni WOOD ni IORE. Une ligne
     * legacy sans cargo reste conservativement bloquante. */
    if (cargoFilter != null && ("cargo" in line) && line.cargo != cargoFilter) continue;
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

/* ROAD100-22 : autorite au dernier moment pour les projets fret. Ne
 * relache jamais un second projet du MEME cargo sur une origine servie. */
function OpexRoadFreightOriginServedCargo(lines, tile, cargo)
{
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "road" && line.mode != "rail") continue;
    if (("cargo" in line) && line.cargo != cargo) continue;
    if (AIMap.DistanceManhattan(tile, line.originA) < ORIGIN_SEPARATION ||
        AIMap.DistanceManhattan(tile, line.originB) < ORIGIN_SEPARATION) return true;
  }
  return false;
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
  if (catalog.locoByCargoWagons != null && !(cargo in catalog.locoByCargoWagons)) return;
  /* V275 bit 4 retire le 24/10 (decision utilisateur) : plus d'attente du rail voyageurs ; les priorites passent par la calibration. */
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local served = [];
  /* V275 bit 1 : villes ou nous avons deja un aeroport. Le rail y partagerait les memes
   * maisons que nos avions (V216 : 84 % du deficit rail voyageurs vient de nos modes). */
  local airTowns = null;
  if (V275_RAIL_PAX_MM & 1) {
    airTowns = {};
    foreach (line in lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      if (("scrapping" in line) && line.scrapping) continue;
      airTowns.rawset(line.originA, true);
      airTowns.rawset(line.originB, true);
    }
  }
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  for (local i = 0; i < n; i++) {
    local p = AITown.GetLastMonthProduction(towns[i].id, cargo);
    if (p <= 0 && towns[i].pop > 0) p = (towns[i].pop * 22) / 100;
    if ((ESTIM_UNIFIE & 8) != 0 && !OpexOriginServed(lines, towns[i].tile, true))
      p = OpexEstimRivalAvailableMonthly(p,
          AITown.GetLastMonthTransportedPercentage(towns[i].id, cargo));
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
      if ((ESTIM_UNIFIE & 8) != 0 && !OpexOriginServed(lines, towns[i].tile, true))
        mp = OpexEstimRivalAvailableMonthly(mp,
            AITown.GetLastMonthTransportedPercentage(towns[i].id, catalog.mailCargo));
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
      if (airTowns != null && ((towns[a].tile in airTowns) || (towns[b].tile in airTowns))) {
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

/* V264 : une source rail neuve peut livrer une industrie deja desservie, sur la gare
 * existante. Politique V264 figee active. Pas de filtre
 * isTransformer : une centrale (IT_POWER_STATION) n'en est pas une et reste un puits
 * de charbon. Les puits urbains ne passent pas ici. */
function OpexV264ConvergentService(lines, service, cargo, srcTile)
{
  if (service == null || service.blocked) return null;
  local stationId = service.stationId;
  if (stationId < 0 || !AIStation.IsValidStation(stationId)) return null;
  if (!AIStation.HasStationType(stationId, AIStation.STATION_TRAIN)) return null;
  if (!("line" in service) || service.line == null || !("lineEnd" in service)) return null;
  if (!("lineId" in service.line)) return null;
  local platformKey = service.lineEnd == "A" ? "platformA" : "platformB";
  if (!(platformKey in service.line) || service.line[platformKey] == null) return null;
  local platform = service.line[platformKey];
  if (!("direction" in platform) || !("length" in platform)
      || !("anchor" in platform) || !("step" in platform)) return null;
  if (platform.length < 1) return null;
  /* Meme comparaison que _tooClose : tuile d'industrie contre la tuile de gare
   * enregistree, seuil MIN_SEPARATION (main.nut:74). ORIGIN_SEPARATION (main.nut:83)
   * est deja faux : l'appelant exige ss == null via OpexOriginService. */
  foreach (line in lines) {
    if (("mode" in line) && line.mode != "rail") continue;
    foreach (lineEnd in ["A", "B"]) {
      local sid = OpexLineStationId(line, lineEnd);
      if (sid < 0) continue;
      local stationTile = lineEnd == "A" ? line.stationA : line.stationB;
      if (AIMap.DistanceManhattan(srcTile, stationTile) < MIN_SEPARATION) return null;
    }
  }
  local accepting = AICargoList_StationAccepting(stationId);
  if (!accepting.HasItem(cargo)) return null;
  return { platform = platform, stationId = stationId, lineId = service.line.lineId };
}

/* V264 : meme economie que la paire libre (OpexMakeCandidate), puis le quai a joindre.
 * joinLineId n'est pas pose : _tooClose sauterait toute la ligne, y compris l'extremite A. */
function OpexV264EmitConvergent(catalog, stats, profile, cruiseCache, cargo, source, destIndustry, monthly, others2, attached)
{
  local isTransformer = ("isTransformer" in destIndustry) && destIndustry.isTransformer;
  local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
  local secondary = null;
  local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                      destIndustry.tile, monthly, false, stats, isTransformer, profile, cruiseCache,
                                      secondary);
  if (profile != null) {
    profile.freightIndustryCandidateOps += OpexOpsMeasureEnd(candidateMark);
    profile.freightIndustryCandidateCalls++;
  }
  if (candidate == null) return null;
  candidate.convergent_dest <- 1;
  candidate.joinPlatform <- attached.platform;
  candidate.joinStationId <- attached.stationId;
  candidate.joinEnd <- "B";
  /* Cle deja creee par OpexMakeCandidate. Une gare reutilisee : tension.nut compte 1 origine. */
  candidate.originServed = true;
  if (DECISION_LOG) {
    local label = AICargo.IsValidCargo(cargo) ? AICargo.GetCargoLabel(cargo) : "?";
    OpexDecide("V264_KEEP", "cargo=" + label + " src=" + source.tile
        + " dst=" + destIndustry.tile + " station=" + attached.stationId
        + " line=" + attached.lineId);
  }
  return candidate;
}

/* Industries : on n'apparie que des couples producteur/accepteur du MEME cargo, ce qui garde
 * l'etage 1 lineaire en nombre d'industries plutot que quadratique sur tout le catalogue. */
function OpexFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1, p1LongState = null)
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
    if (catalog.locoByCargoWagons != null && !(cargo in catalog.locoByCargoWagons)) continue;
    local hasIndustrySinks = (cargo in catalog.acceptors);
    local hasTownSinks = (cargo in catalog.townAcceptors);
    if (!hasIndustrySinks && !hasTownSinks) continue;
    local sinks = hasIndustrySinks ? catalog.acceptors[cargo] : [];

    foreach (si in sources) {
      local source = industries[si];
      if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local ss = served[si];
      if ((ESTIM_UNIFIE & 8) != 0 && ss == null)
        monthly = OpexEstimRivalAvailableMonthly(monthly,
            AIIndustry.GetLastMonthTransportedPercentage(source.id, cargo));
      local longGood = V233_LONG_GOOD > 0 ? OpexV233LSource(source, cargo, lines) : null;
      local others2 = null;
      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
        if (longGood != null) continue;
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
        /* V179 : source neuve, destination deja desservie : on garde la paire, V178 la rattache.
         * Ce chemin n'est pas marque convergent : V264 ne s'execute que dans l'exclusion. */
        local v179Keep = ss == null && sd != null;
        if (!v179Keep && (ss != null || sd != null)) {
          /* Paires deja rejetees. A 0 le drapeau est faux : aucun appel, pairsOriginServed. */
          local attached = null;
          if (ss == null && sd != null) {
            attached = OpexV264ConvergentService(lines, sd, cargo, source.tile);
          }
          if (attached == null) {
            stats.pairsOriginServed++;
            continue;
          }
          local kept = OpexV264EmitConvergent(catalog, stats, profile, cruiseCache, cargo,
                                              source, industries[di], monthly, others2, attached);
          if (kept != null) out.append(kept);
          continue;
        }
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        /* P1 : les paires hors railMax ne doivent pas evincer les courtes du TopK
         * papier. En shadow les stats historiques restent identiques. */
        if (p1LongState != null && monthly > 0
            && OpexP1LongOffer(p1LongState, catalog, cargo, source, industries[di],
                               monthly, isTransformer)) {
          stats.distanceLong++;
          continue;
        }
        local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
        local secondary = null;
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
          if (longGood != null && (k >= V233L_TOWNS || longGood.ops >= V233L_SLICE_OPS)) break;
          local town = townSinks[longGood != null ? (k + longGood.townStart) % townSinks.len() : k];
          if (longGood != null && !OpexV233LAdmit(longGood, source, town)) continue;
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
          if ((ss != null && longGood == null) || st != null) {
            if (longGood != null && DECISION_LOG) OpexV233LLog("REJECT", "industry=" + source.id + " town=" + town.id + " reason=destination_served");
            stats.pairsOriginServed++;
            if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
            continue;
          }
          local townMonthly = longGood != null ? longGood.monthly : monthly;
          if (townMonthly <= 0) {
            if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
            continue;
          }
          if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
          if (C60_TOWN_RATING_PROBE) {
            OpexC60ObserveTownRating("rail", "candidate_gen", town.id);
          }
          local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
          local v233Mark = longGood != null ? OpexOpsMeasureBegin() : null;
          local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                              town.tile, townMonthly, longGood != null, stats, false, profile, cruiseCache, null, longGood != null);
          if (longGood != null) longGood.ops += OpexOpsMeasureEnd(v233Mark);
          if (profile != null) {
            profile.freightTownCandidateOps += OpexOpsMeasureEnd(candidateMark);
            profile.freightTownCandidateCalls++;
          }
          if (candidate != null) {
            candidate.dstTown <- town.id;
            if (longGood != null) {
              candidate.v233LongGood <- true;
              candidate.v233InputStation <- longGood.row.station;
              local siteMark = OpexOpsMeasureBegin();
              local siteCheck = OpexV233LPreflight(catalog, candidate);
              longGood.ops += OpexOpsMeasureEnd(siteMark);
              if (!siteCheck.ready) {
                stats.unsitable++;
                stats.accepted--;
                if (DECISION_LOG) OpexV233LLog("REJECT", "industry=" + source.id + " town=" + town.id
                    + " reason=" + siteCheck.reason + " sitable=0 phase=admission");
                /* Reprendre cette ville au prochain passage si le scan est incomplet. */
                if (siteCheck.pending) { longGood.visits--; break; }
                continue;
              }
              if (DECISION_LOG) OpexV233LLog("CANDIDATE", "industry=" + source.id + " town=" + town.id
                  + " distance=" + candidate.distance + " monthly=" + townMonthly + " trains=" + candidate.trains
                  + " wagons=" + candidate.wagons + " profit=" + candidate.profitAnnual + " capital=" + candidate.capital);
            }
            out.append(candidate);
          } else if (longGood != null && DECISION_LOG) {
            OpexV233LLog("REJECT", "industry=" + source.id + " town=" + town.id
                + " reason=economics_or_site no_model=" + stats.economicsUnavailable
                + " profit=" + stats.profitNonPositive + " ratio=" + stats.ratioTooLow + " sitable=" + stats.unsitable);
          }
        }
        if (profile != null) profile.freightTownOps += OpexOpsMeasureEnd(townMark);
        if (longGood != null) OpexV233LSourceEnd(longGood, source);

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

function OpexBuildCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, paxProfile = null, paxCandidateProfile = null, paxCruiseCache = null, freightCruiseCache = null, generatePax = true, generateFreight = true, paxBand = PAX_BAND_ALL, freightCargo = null, targetKind = null, targetId = -1, p1LongState = null)
{
  if (V276_CAND_SLICES > 0) return OpexV276Published(catalog, targetKind, targetId);
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
                          freightCargo, targetKind, targetId, p1LongState);
  }
  local opsFreight = budget.end("cand_freight");
  if (profile != null) profile.freightOps += OpexOpsMeasureEnd(freightMark);

  /* P1 : l'economie n'est calculee qu'APRES le scan, pour l'unique meilleur
   * proxy. Le candidat reste hors `all` et hors `best` jusqu'a la preuve C80. */
  if (p1LongState != null && p1LongState.best != null) {
    if (P1_RAIL_LONG_VALUE_RANK == 2)
      p1LongState.candidate = OpexP1LongEvaluate(catalog, p1LongState, stats);
    if (DECISION_LOG) OpexDecide("P1_LONG_SHADOW", "mode=" + P1_RAIL_LONG_VALUE_RANK
        + " count=" + p1LongState.observed + " cargo=" + p1LongState.best.cargo
        + " src=" + p1LongState.best.src + " dst=" + p1LongState.best.dst
        + " dist=" + p1LongState.best.distance
        + " candidate=" + (p1LongState.candidate != null ? 1 : 0));
  }

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
                               monthly, stats, isTransformer = false, fleetCapOverride = 0)
{
  local engine = (cargo in catalog.roadEngineByCargo) ? catalog.roadEngineByCargo[cargo] : null;
  if (engine == null) {
    stats.noEngine++;
    return null;
  }
  local economics = OpexRoadLineEconomics(catalog, cargo, distance, monthly, engine, kind,
                                          null, fleetCapOverride);
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

/* ROAD100 : candidats PAX destines aux seuls bancs ROAD. La selection et le chantier
 * continuent d'utiliser le portefeuille normal ; la garde de ville deja servie
 * reste en place. Trier par demande des villes evite de consacrer le vivier aux
 * premieres villes dans l'ordre du catalogue. Aucun etat persistant. */
function OpexRoad100SortTownDemand(a, b)
{
  if (a.captured != b.captured) return a.captured > b.captured ? -1 : 1;
  if (a.id != b.id) return a.id < b.id ? -1 : 1;
  return 0;
}

/* Filtre géographique bon marché AVANT les sondes de 64 arrêts et le BFS.
 * Le score est uniquement une priorité de visite, jamais un refus de profit :
 * les vrais sites peuvent inverser le jugement du modèle théorique. */
function OpexRoad100SortSitePreview(a, b)
{
  if (a.score != b.score) return a.score > b.score ? -1 : 1;
  if (a.distance != b.distance) return a.distance < b.distance ? -1 : 1;
  if (a.src.id != b.src.id) return a.src.id < b.src.id ? -1 : 1;
  return a.dst.id < b.dst.id ? -1 : (a.dst.id > b.dst.id ? 1 : 0);
}

/* ROAD100-12 : un couple dont le proxy urbain est positif, mais dont le
 * trajet est court, a moins de voies a poser ou a contourner. Prioriser la
 * faisabilite de l'etude physique, sans toucher a l'economie du projet. */
function OpexRoad100SortSiteNear(a, b)
{
  local aPositive = a.score > 0;
  local bPositive = b.score > 0;
  if (aPositive != bPositive) return aPositive ? -1 : 1;
  if (a.distance != b.distance) return a.distance < b.distance ? -1 : 1;
  return OpexRoad100SortSitePreview(a, b);
}

/* ROAD100-16 shadow : comparer deux paires par demande urbaine PROXY sans
 * trier tout le produit cartesien des 40 villes. Le vrai volume appartient
 * au preflight physique, jamais a ce classement exploratoire. */
function OpexRoad100LongShadowBetter(a, b)
{
  if (a.proxy != b.proxy) return a.proxy > b.proxy;
  if (a.distance != b.distance) return a.distance < b.distance;
  if (a.idLo != b.idLo) return a.idLo < b.idLo;
  return a.idHi < b.idHi;
}

/* V7 LONG BUILD seulement : un proxy 'dix maisons' favorise de petites
 * villes et peut cacher les très gros bassins réels. La production totale
 * mensuelle sert UNIQUEMENT à ouvrir la recherche ; jamais au ROI. */
function OpexRoad100LongSortTownTotal(a, b)
{
  if (a.total != b.total) return a.total > b.total ? -1 : 1;
  if (a.captured != b.captured) return a.captured > b.captured ? -1 : 1;
  if (a.id != b.id) return a.id < b.id ? -1 : 1;
  return 0;
}

/* ROAD100-16 v5 : deux territoires indépendants, pas deux projets
 * compétiteurs du même hub urbain. Même proxy non économique et même
 * départage déterministe que v4b ; explorer le meilleur second couple
 * disjoint, et ne revenir au deuxième global qu'en dernier recours.
 * Une seule passe supplémentaire sur au plus C(40,2)=780 paires. */
function OpexRoad100LongSelectDiverse(pool)
{
  local chosen = [];
  local first = null;
  foreach (item in pool) {
    if (first == null || OpexRoad100LongShadowBetter(item, first)) first = item;
  }
  if (first == null) return chosen;
  chosen.append(first);
  local second = null;
  foreach (item in pool) {
    if (item.idLo == first.idLo || item.idLo == first.idHi ||
        item.idHi == first.idLo || item.idHi == first.idHi) continue;
    if (second == null || OpexRoad100LongShadowBetter(item, second)) second = item;
  }
  if (second == null) {
    foreach (item in pool) {
      if (item.idLo == first.idLo && item.idHi == first.idHi) continue;
      if (second == null || OpexRoad100LongShadowBetter(item, second)) second = item;
    }
  }
  if (second != null) chosen.append(second);
  return chosen;
}

/* V6 : empreinte d'ordre des aretes pour refuser un chantier dont le plan
 * physique a derive depuis l'admission. Multiplications bornées (<30M)
 * et somme réduite modulo 1e9+7 pour éviter l'overflow 32-bit Squirrel. */
function OpexRoad100LongTraceHash(trace)
{
  if (trace == null || trace.len() == 0) return -1;
  local checksum = 0;
  local pos = 1;
  foreach (edge in trace) {
    checksum = (checksum + pos * (17 * (edge.from % 4093)
        + 19 * (edge.to % 4093))) % 1000000007;
    pos++;
  }
  return checksum;
}

/* Le devis du constructeur LONG peut dépasser le poste d'infrastructure
 * standard (routeDistance * prix par tuile). Imputer STRICTEMENT le
 * supplément aux coûts/amortissements, sans toucher aux recettes ; sinon
 * un corridor de 136 arêtes pourrait sembler rentable à tort. */
function OpexRoad100LongQuotedEconomics(catalog, economics, plan)
{
  if (economics == null || plan == null || !("roadQuoteCost" in plan)
      || plan.roadQuoteCost < 0 || plan.routeDistance < 1) return null;
  local provision = plan.routeDistance * catalog.costRoadPerTile;
  local quoted = plan.roadQuoteCost + 3 * catalog.costRoadPerTile;
  local extra = quoted > provision ? quoted - provision : 0;
  economics.capital += extra;
  economics.amortAnnual += ((extra * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS);
  economics.profitAnnual = economics.revenueAnnual
      - economics.runningAnnual - economics.amortAnnual;
  local total = economics.capital + economics.immobilise;
  economics.roi = economics.profitAnnual > 0 && total > 0
      ? (economics.profitAnnual * 1000) / total : 0;
  return economics;
}

/* V6 : exposer UNIQUEMENT un plan LONG réellement préflighté, avec les
 * deux producteurs locaux et un prix conservateur. Ni le proxy de ville
 * ni un chemin PATH_ONLY ne donnent droit à du profit fictif. */
function OpexRoad100LongBuildCandidate(catalog, preliminary, plan, stats)
{
  if (!ROAD100_LONG_BUILD || plan == null || plan.trace == null ||
      plan.depot == null || plan.stopA == null || plan.stopB == null) return null;
  local monthly = plan.stopA.value + plan.stopB.value;
  /* ROAD100-32 : GetCargoProduction donne des producteurs, PAS des
   * PASS/mois. Le branchement segmenté convertit uniquement les vrais
   * arrêts racines en fractions conservatrices de la production mensuelle
   * de leur ville. Aucun satellite ni retour virtuel n'est crédité. */
  local segmentedUnits = ROAD100_SEGMENTED_CORRIDOR
      && ("road100Segmented" in plan) && plan.road100Segmented;
  local graphUnits = ROAD100_PAX_GRAPH_BRIDGE
      && ("road100Graph" in plan) && plan.road100Graph;
  local sparseUnits = (ROAD100_SPARSE_CORRIDOR
      && ("road100Sparse" in plan) && plan.road100Sparse) || graphUnits;
  local convertLongUnits = ROAD100_PAX_PRODUCER_UNITS
      || ROAD100_SEGMENTED_CORRIDOR
      || ROAD100_SPARSE_CORRIDOR
      || ROAD100_PAX_GRAPH_BRIDGE;
  if (convertLongUnits) {
    local radius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    local unitsA = OpexRoad100PaxSiteMonthly(preliminary.srcTown,
        preliminary.cargo, plan.stopA.tile, radius);
    local unitsB = OpexRoad100PaxSiteMonthly(preliminary.dstTown,
        preliminary.cargo, plan.stopB.tile, radius);
    monthly = unitsA.monthly + unitsB.monthly;
    if (DECISION_LOG) OpexDecide(sparseUnits ? "ROAD100_SPARSE" : "ROAD100_SEGMENTED",
        "phase=market town_a=" + preliminary.srcTown
        + " town_b=" + preliminary.dstTown
        + " producers_a=" + unitsA.siteProducers
        + " producers_b=" + unitsB.siteProducers
        + " town_producers_a=" + unitsA.townProducers
        + " town_producers_b=" + unitsB.townProducers
        + " town_monthly_a=" + unitsA.townMonthly
        + " town_monthly_b=" + unitsB.townMonthly
        + " root_monthly_a=" + unitsA.monthly
        + " root_monthly_b=" + unitsB.monthly
        + " ops=" + (unitsA.ops + unitsB.ops));
  }
  local minimumGraph = graphUnits ? 43 : 80;
  if (monthly <= 0 || plan.routeDistance < minimumGraph || plan.routeDistance > 190) {
    if (DECISION_LOG) OpexDecide("ROAD100_LONG_ADMIT",
        "reason=MONTHLY_OR_TRACE monthly=" + monthly + " route=" + plan.routeDistance);
    return null;
  }
  local distance = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
  if (distance < minimumGraph || distance > 190) {
    if (DECISION_LOG) OpexDecide("ROAD100_LONG_ADMIT",
        "reason=DISTANCE distance=" + distance);
    return null;
  }
  local economics = OpexRoad100LongQuotedEconomics(catalog,
      OpexRoadLineEconomics(catalog, preliminary.cargo, distance,
          monthly, preliminary.engine, "pax", plan.routeDistance), plan);
  if (economics == null || economics.profitAnnual <= 0) {
    if (DECISION_LOG) OpexDecide("ROAD100_LONG_ADMIT",
        "reason=NEG_PROFIT monthly=" + monthly + " distance=" + distance
        + " route=" + plan.routeDistance + " road_quote=" + plan.roadQuoteCost
        + " pred_profit=" + (economics != null ? economics.profitAnnual : -1));
    return null;
  }
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = OpexEstimFinanceCapital("road", economics.capital, distance,
      false, economics.immobilise);
  if (cash < need + 50000 ||
      (("road100LongCashNeed" in plan) && cash < plan.road100LongCashNeed) ||
      !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, economics.trains)) {
    if (DECISION_LOG) OpexDecide("ROAD100_LONG_ADMIT",
        "reason=FINANCE_OR_SLOT monthly=" + monthly
        + " pred_profit=" + economics.profitAnnual
        + " capital=" + economics.capital + " trains=" + economics.trains
        + " cash=" + cash + " need=" + need
        + " long_need=" + (("road100LongCashNeed" in plan)
            ? plan.road100LongCashNeed : -1));
    return null;
  }
  local candidate = OpexMakeRoadCandidate(catalog, "pax", preliminary.cargo,
      preliminary.src, preliminary.dst, preliminary.srcTown,
      preliminary.dstTown, distance, monthly, stats);
  if (candidate == null) {
    if (DECISION_LOG) OpexDecide("ROAD100_LONG_ADMIT",
        "reason=MAKE_CANDIDATE monthly=" + monthly
        + " pred_profit=" + economics.profitAnnual);
    return null;
  }
  candidate.road100SiteFirst <- true;
  candidate.road100LongBuild <- true;
  if (graphUnits) candidate.road100GraphRequested <- true;
  if (segmentedUnits) candidate.road100SegmentedUnits <- true;
  if (sparseUnits && !graphUnits) candidate.road100SparseUnits <- true;
  /* V35 : un projet sauve sous la sonde portail ne doit pas changer
   * silencieusement de mode ou de trace a la reprise du chantier. */
  if (ROAD100_PORTAL_STITCH) candidate.road100PortalRequested <- true;
  if (("road100Portal" in plan) && plan.road100Portal)
    candidate.road100PortalUnits <- true;
  if (convertLongUnits) candidate.road100LongUnits <- true;
  if (ROAD100_PAX_PRODUCER_UNITS) candidate.road100PaxProducerUnits <- true;
  if (("road100MultiCatchment" in preliminary) && preliminary.road100MultiCatchment)
    candidate.road100MultiCatchment <- true;
  candidate.road100SiteMonthly <- monthly;
  candidate.road100GenSiteA <- plan.stopA.tile;
  candidate.road100GenSiteB <- plan.stopB.tile;
  candidate.road100GenFrontA <- plan.stopA.front;
  candidate.road100GenFrontB <- plan.stopB.front;
  candidate.road100GenDepot <- plan.depot.tile;
  candidate.road100GenRoute <- plan.routeDistance;
  candidate.road100GenTraceHash <- OpexRoad100LongTraceHash(plan.trace);
  candidate.road100GenRoadQuote <- plan.roadQuoteCost;
  candidate.road100GenCashNeed <- ("road100LongCashNeed" in plan)
      ? plan.road100LongCashNeed : need + 50000;
  candidate.road100StoredPlan <- plan;
  candidate.monthly = monthly;
  OpexApplyRoadEconomics(candidate, economics, distance);
  candidate.immobilise = economics.immobilise;
  candidate.iterations = OpexRoadIterations(distance);
  candidate.ratio = (economics.profitAnnual * 1000) / candidate.iterations;
  if (DECISION_LOG) OpexDecide("ROAD100_LONG_ADMIT",
      "reason=OK monthly=" + monthly + " pred_profit=" + economics.profitAnnual
      + " capital=" + economics.capital + " cash=" + cash
      + " need=" + need + " trains=" + economics.trains);
  return candidate;
}

/* ROAD100-7 : le calcul économique et le classement sont établis AVANT le
 * portefeuille, sur un plan de stations physiquement réalisable. Seulement
 * six plans au plus par génération (et un budget d'opcodes), jamais de
 * Pathfinder.Road non borné. Une présélection par distance élimine les
 * villes distantes de 100-200 cases qui ont saturé le smoke v1 (12 TRACEX).
 * Les sites sont à nouveau validés au chantier : aucune géométrie en cache. */
function OpexRoad100SiteFirstGenerator(catalog, lines, out, stats,
                                      abandonedPairs = null, targetKind = null, targetId = -1)
{
  if (!ROAD100_SITE_FIRST || (targetKind != null && targetKind != "town")) return;
  local cargo = catalog.paxCargo;
  if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) return;
  local roadEngine = catalog.roadEngineByCargo[cargo];
  local ranked = [];
  foreach (i, town in catalog.towns) {
    if ((!ROAD100_MULTICATCHMENT && OpexTownBusPaxServed(lines, town.id))
        || OpexTownRoadLineCount(lines, town.tile) >= 4) continue;
    local monthly = AITown.GetLastMonthProduction(town.id, cargo);
    if (monthly <= 0 && town.pop > 0) monthly = (town.pop * 15) / 100;
    if (monthly <= 0) continue;
    local houses = ("houses" in town && town.houses > 0) ? town.houses : town.pop / 25;
    if (houses < 1) houses = 1;
    local share = (10 * 100) / houses;
    if (share > 86) share = 86;
    if (share < 1) share = 1;
    local captured = (monthly * share) / 100;
    if (captured < 1) captured = 1;
    ranked.append({ index = i, id = town.id, captured = captured, total = monthly });
  }
  ranked.sort(OpexRoad100SortTownDemand);
  local n = ranked.len();
  if (n > 40) n = 40;
  local examined = 0;
  local plans = 0;
  local accepted = 0;
  local noPlan = 0;
  local noSite = 0;
  local noProfit = 0;
  local ops = 0;
  local nearby = [];
  for (local a = 0; a < n; a++) {
    for (local b = a + 1; b < n; b++) {
      local src = ranked[a];
      local dst = ranked[b];
      if (targetKind == "town" && targetId >= 0
          && src.id != targetId && dst.id != targetId) continue;
      examined++;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("road", 1);
      local townA = catalog.towns[src.index];
      local townB = catalog.towns[dst.index];
      if (OpexRoadPairServed(lines, townA.tile, townB.tile)) continue;
      local distance = AIMap.DistanceManhattan(townA.tile, townB.tile);
      /* Les liaisons sont bornees par ROAD_MAX_TRACE_TILES (128 sur cette branche). */
      if (distance < 12 || distance > ROAD_MAX_TRACE_TILES) continue;
      if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
      if (abandonedPairs != null) {
        local idA = src.id;
        local idB = dst.id;
        if (idA > idB) { local swapId = idA; idA = idB; idB = swapId; }
        local pairKey = "pax|" + cargo + "|" + idA + "|" + idB;
        if (pairKey in abandonedPairs) continue;
      }
      local proxy = OpexRoadLineEconomics(catalog, cargo, distance,
          src.captured + dst.captured, roadEngine, "pax");
      local score = proxy != null ? proxy.profitAnnual : -999999;
      nearby.append({ src = src, dst = dst, distance = distance, score = score });
    }
  }
  if (ROAD100_SITE_NEAR) nearby.sort(OpexRoad100SortSiteNear);
  else nearby.sort(OpexRoad100SortSitePreview);
  local shortlisted = nearby.len();
  /* ROAD100-11 : les paires aux premiers rangs TRACEX consommaient le meme
   * preflight (~500 k opcodes) lors de plusieurs regenerations successives.
   * Conserver la meilleure paire, puis tourner une fenetre deterministe sur
   * les autres rangs. Le budget et tous les refus physiques restent identiques. */
  local siteWindowOffset = 0;
  if (ROAD100_SITE_WINDOW && shortlisted > 1) {
    local today = AIDate.GetCurrentDate();
    siteWindowOffset = ((AIDate.GetYear(today) % 10) * 5
        + (AIDate.GetMonth(today) - 1) / 3) % (shortlisted - 1);
  }
  for (local k = 0; k < shortlisted && plans < 6 && ops < 2500000; k++) {
      /* PO01C : la régénération coopérative laisse la main entre projets.
       * La voie synchrone déroule explicitement le générateur. */
      yield null;
      local rank = ROAD100_SITE_WINDOW && k > 0 && shortlisted > 1
          ? 1 + ((siteWindowOffset + k - 1) % (shortlisted - 1)) : k;
      local src = nearby[rank].src;
      local dst = nearby[rank].dst;
      local townA = catalog.towns[src.index];
      local townB = catalog.towns[dst.index];
      local distance = nearby[rank].distance;
      stats.pairsInBand++;
      /* Ne jamais filtrer sur le profit tiré des villes avant le vrai site :
       * le premier modèle pourrait condamner un meilleur couple d'arrêts. */
      local preliminary = { mode = "road", kind = "pax", cargo = cargo,
          src = townA.tile, dst = townB.tile, srcTown = src.id, dstTown = dst.id,
          distance = distance, monthly = src.captured + dst.captured,
          engine = roadEngine, road100SiteFirst = true,
          road100PaxPortfolio = ROAD100_PAX_PORTFOLIO,
          road100MultiCatchment = ROAD100_MULTICATCHMENT };
      plans++;
      local planMark = OpexOpsMeasureBegin();
      local siting = OpexRoadPlanFor(catalog, preliminary);
      ops += OpexOpsMeasureEnd(planMark);
      if (siting.plan == null) {
        noPlan++;
        if (DECISION_LOG) OpexDecide("ROAD100_SITE_FIRST",
            "phase=reject reason=plan" + (ROAD100_SITE_WINDOW ? " rank=" + rank : "")
            + " src=" + preliminary.src + " dst=" + preliminary.dst
            + " detail=" + siting.reason);
        continue;
      }
      local plan = siting.plan;
      local siteMonthly = plan.stopA.value + plan.stopB.value;
      if (ROAD100_PAX_PRODUCER_UNITS) {
        if (!("road100PaxUnitsMonthly" in plan)) {
          noSite++;
          continue;
        }
        siteMonthly = plan.road100PaxUnitsMonthly;
        if (DECISION_LOG) {
          local a = plan.road100PaxUnitA;
          local b = plan.road100PaxUnitB;
          OpexDecide("ROAD100_PAX_UNITS",
              "phase=generator src_town=" + src.id + " dst_town=" + dst.id
              + " producers_a=" + a.siteProducers + " producers_b=" + b.siteProducers
              + " producers_total_a=" + a.townProducers
              + " producers_total_b=" + b.townProducers
              + " city_monthly_a=" + a.townMonthly
              + " city_monthly_b=" + b.townMonthly
              + " site_monthly_a=" + a.monthly + " site_monthly_b=" + b.monthly
              + " ops=" + (a.ops + b.ops));
        }
      }
      if (siteMonthly <= 0) { noSite++; continue; }
      /* ROAD100-20 : l'union preconstruction de plusieurs quartiers reste un
       * potentiel de classement. Le revenu reel ne sera credite qu'apres
       * pose effective des quais joints ; jamais dans candidate.monthly ni
       * dans les besoins d'achat des bus initiaux. */
      local portfolioPreview = null;
      if (ROAD100_PAX_PORTFOLIO) {
        portfolioPreview = OpexRoad100PaxPortfolioPreview(catalog, preliminary, plan);
        if (portfolioPreview != null && ("ops" in portfolioPreview))
          ops += portfolioPreview.ops;
        if (DECISION_LOG && portfolioPreview != null)
          OpexDecide("ROAD100_PAX_PORTFOLIO",
              "phase=preview src=" + preliminary.src + " dst=" + preliminary.dst
              + " root=" + siteMonthly + " union=" + portfolioPreview.monthly
              + " marginal_a=" + portfolioPreview.marginalA
              + " marginal_b=" + portfolioPreview.marginalB
              + " ops=" + portfolioPreview.ops + " reason=" + portfolioPreview.reason);
      }
      local actualDistance = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
      if (actualDistance < 1) actualDistance = 1;
      local economics = OpexRoadLineEconomics(catalog, cargo, actualDistance,
          siteMonthly, roadEngine, "pax", plan.routeDistance);
      if (economics == null || economics.profitAnnual <= 0) { noProfit++; continue; }
      local candidate = OpexMakeRoadCandidate(catalog, "pax", cargo, townA.tile,
          townB.tile, src.id, dst.id, actualDistance, siteMonthly, stats);
      if (candidate == null) { noProfit++; continue; }
      candidate.road100SiteFirst <- true;
      if (ROAD100_PAX_PRODUCER_UNITS) candidate.road100PaxProducerUnits <- true;
      if (ROAD100_PAX_PORTFOLIO) {
        candidate.road100PaxPortfolio <- true;
        candidate.road100PaxPortfolioPreview <- portfolioPreview;
      }
      if (ROAD100_JOINED_STOPS) candidate.road100JoinedStops <- true;
      if (ROAD100_MULTICATCHMENT) candidate.road100MultiCatchment <- true;
      candidate.monthly = siteMonthly;
      OpexApplyRoadEconomics(candidate, economics, actualDistance);
      candidate.immobilise = economics.immobilise;
      candidate.iterations = OpexRoadIterations(actualDistance);
      candidate.ratio = (economics.profitAnnual * 1000) / candidate.iterations;
      if (ROAD100_PAX_PORTFOLIO) {
        /* V20e : le shadow de satellites n'a apporte aucun gain de
         * profit_year en 5x5 et a erode le classement des lignes fret.
         * Ne jamais avancer une ligne sur un benefice NON CONSTRUIT :
         * la capture physique est gardee, le rang reste celui des racines. */
        candidate.road100PaxPortfolioRankDelta <- 0;
      }
      candidate.road100SiteMonthly <- siteMonthly;
      candidate.road100GenSiteA <- plan.stopA.tile;
      candidate.road100GenSiteB <- plan.stopB.tile;
      candidate.road100GenFrontA <- plan.stopA.front;
      candidate.road100GenFrontB <- plan.stopB.front;
      candidate.road100GenDepot <- plan.depot.tile;
      candidate.road100GenRoute <- plan.routeDistance;
      out.append(candidate);
      accepted++;
      if (DECISION_LOG) OpexDecide("ROAD100_SITE_FIRST",
          "phase=admit" + (ROAD100_SITE_WINDOW ? " rank=" + rank : "")
          + " src=" + candidate.src + " dst=" + candidate.dst
          + " siteA=" + plan.stopA.tile + " siteB=" + plan.stopB.tile
          + " monthly=" + siteMonthly + " city_monthly=" + (src.captured + dst.captured)
          + " dist=" + actualDistance + " route=" + plan.routeDistance
          + " vehicles=" + economics.trains + " profit=" + economics.profitAnnual
          + " capital=" + economics.capital + " roi=" + economics.roi
          + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
    }
  if (DECISION_LOG) OpexDecide("ROAD100_SITE_FIRST",
      "phase=summary towns=" + n + " examined=" + examined
      + " nearby=" + shortlisted
      + (ROAD100_SITE_WINDOW ? " window=" + siteWindowOffset : "")
      + " plans=" + plans + " accepted=" + accepted + " no_plan=" + noPlan
      + " no_site=" + noSite + " no_profit=" + noProfit + " ops=" + ops);

  /* ROAD100-16 : la voie longue reste OFF sauf opt-in explicite. En shadow
   * aucun candidat n'entre au portefeuille ; ROAD100_LONG_BUILD est un
   * deuxième réglage distinct, avec chantier seulement après préflight.
   * Le verrou annuel ne s'applique qu'à la recherche globale et n'est posé
   * qu'au terme complet de celle-ci (jamais avant les yield ni sur targetId). */
  local isGlobalSearch = (targetKind == null || targetId < 0);
  if (ROAD100_LONG_INTERCITY
      && (!isGlobalSearch || ROAD100_LONG_SHADOW_YEAR != AIDate.GetYear(AIDate.GetCurrentDate()))) {
    local longBest = [];
    local longPool = [];
    local longExamined = 0;
    local longInBand = 0;
    local longOps = 0;
    local longAttempts = 0;
    local longOk = 0;
    local longAdmitted = 0;
    local longCap = ROAD100_LONG_BUILD ? 400000 : 250000;
    local longRanked = ranked;
    local longCount = n;
    if (ROAD100_LONG_BUILD) {
      /* Un autre classement n'affecte PAS le générateur 12..42 déjà
       * produit plus haut. Aucun appel natif supplémentaire : total est
       * lu du cache AITown.GetLastMonthProduction de ranked. */
      local rankMark = OpexOpsMeasureBegin();
      longRanked = [];
      foreach (longCity in ranked) longRanked.append(longCity);
      longRanked.sort(OpexRoad100LongSortTownTotal);
      longCount = longRanked.len() < 40 ? longRanked.len() : 40;
      longOps += OpexOpsMeasureEnd(rankMark);
    }
    for (local la = 0; la < longCount && longOps < longCap; la++) {
      /* PO01C reprend le generateur entre deux tranches de classement. */
      yield null;
      local scanMark = OpexOpsMeasureBegin();
      local longSrc = longRanked[la];
      local longTownA = catalog.towns[longSrc.index];
      for (local lb = la + 1; lb < longCount; lb++) {
        local longDst = longRanked[lb];
        if (targetKind == "town" && targetId >= 0
            && longSrc.id != targetId && longDst.id != targetId) continue;
        longExamined++;
        local longTownB = catalog.towns[longDst.index];
        local longDistance = AIMap.DistanceManhattan(longTownA.tile, longTownB.tile);
        if (longDistance < (ROAD100_PAX_GRAPH_BRIDGE ? 43 : 80)
            || longDistance > 170) continue;
        longInBand++;
        if (OpexRoadPairServed(lines, longTownA.tile, longTownB.tile)) continue;
        local longIdLo = longSrc.id < longDst.id ? longSrc.id : longDst.id;
        local longIdHi = longSrc.id > longDst.id ? longSrc.id : longDst.id;
        if (abandonedPairs != null) {
          local longKey = "pax|" + cargo + "|" + longIdLo + "|" + longIdHi;
          if (longKey in abandonedPairs) continue;
        }
        local searchProxy = ROAD100_LONG_BUILD
            ? longSrc.total + longDst.total
            : longSrc.captured + longDst.captured;
        local preview = { src = longSrc, dst = longDst,
            distance = longDistance, proxy = searchProxy,
            idLo = longIdLo, idHi = longIdHi };
        longPool.append(preview);
      }
      longOps += OpexOpsMeasureEnd(scanMark);
    }
    if (longOps < longCap) {
      local choiceMark = OpexOpsMeasureBegin();
      if (ROAD100_PAX_GRAPH_BRIDGE)
        longBest = OpexRoad100GBSelectDiverseMarkets(longPool);
      else
        longBest = OpexRoad100LongSelectDiverse(longPool);
      longOps += OpexOpsMeasureEnd(choiceMark);
    }
    for (local li = 0; li < longBest.len() && longOps < longCap; li++) {
      yield null;
      local selected = longBest[li];
      local selectedA = catalog.towns[selected.src.index];
      local selectedB = catalog.towns[selected.dst.index];
      local preliminaryLong = {
        mode = "road", kind = "pax", cargo = cargo,
        src = selectedA.tile, dst = selectedB.tile,
        srcTown = selected.src.id, dstTown = selected.dst.id,
        distance = selected.distance, monthly = selected.proxy,
        engine = roadEngine, road100SiteFirst = true,
        road100LongIntercity = true,
        road100LongBuild = ROAD100_LONG_BUILD,
        road100MultiCatchment = ROAD100_MULTICATCHMENT
      };
      if (ROAD100_LONG_BUILD) {
        /* Le planificateur v6 exige le type routier choisi ; ne jamais
         * changer le type dans le helper ni toucher le chemin OFF. */
        AIRoad.SetCurrentRoadType(catalog.roadType);
        /* Le constructeur LONG reçoit LE RELIQUAT de la recherche totale
         * de l'année ; jamais 400k renouvelés par paire. Sous erreur ou
         * plan non physique, aucun candidat ni projet n'est publié. */
        /* ROAD100-16 v14 : le premier couple ne peut plus consommer à
         * lui seul tout le reliquat : réserver au second au moins sa
         * tranche de scan+trace, sans augmenter le cap annuel 400k.
         * Sur un seul couple, le reliquat habituel reste inchangé. */
        local attemptLimit = longCap - longOps;
        if (li + 1 < longBest.len() && attemptLimit > 180000)
          attemptLimit = 180000;
        if (ROAD100_PORTAL_STITCH && attemptLimit > 180000)
          attemptLimit = 180000;
        if (ROAD100_PAX_GRAPH_BRIDGE && attemptLimit > 180000)
          attemptLimit = 180000;
        /* Le plafond V35 par couple couvre aussi admission et calcul de
         * demande, pas uniquement le planificateur physique. */
        local buildMark = OpexOpsMeasureBegin();
        local physical = OpexRoad100LongConstructPlan(catalog, preliminaryLong,
            attemptLimit);
        local planOps = OpexOpsMeasureEnd(buildMark);
        longAttempts++;
        local admittedLong = null;
        if (physical != null && (!(ROAD100_PORTAL_STITCH || ROAD100_PAX_GRAPH_BRIDGE) ||
            planOps < attemptLimit - 12000)) {
          admittedLong = OpexRoad100LongBuildCandidate(catalog,
              preliminaryLong, physical, stats);
        }
        local pairOps = OpexOpsMeasureEnd(buildMark);
        longOps += pairOps;
        if ((ROAD100_PORTAL_STITCH || ROAD100_PAX_GRAPH_BRIDGE)
            && pairOps >= attemptLimit)
          admittedLong = null; // Ne publier aucun projet hors enveloppe.
        if (admittedLong != null) {
          out.append(admittedLong);
          longAdmitted++;
          longOk++;
        }
        if (DECISION_LOG) OpexDecide("ROAD100_LONG_BUILD",
            "phase=preflight rank=" + li
            + " town_a=" + preliminaryLong.srcTown
            + " town_b=" + preliminaryLong.dstTown
            + " centre_dist=" + selected.distance
            + " physical=" + (physical != null ? 1 : 0)
            + " admitted=" + (admittedLong != null ? 1 : 0)
            + " siteA=" + (physical != null ? physical.stopA.tile : -1)
            + " siteB=" + (physical != null ? physical.stopB.tile : -1)
            + " monthly=" + (physical != null
                ? physical.stopA.value + physical.stopB.value : -1)
            + " route=" + (physical != null ? physical.routeDistance : -1)
            + " missing=" + (physical != null && ("roadMissingCount" in physical)
                ? physical.roadMissingCount : -1)
            + " road_quote=" + (physical != null && ("roadQuoteCost" in physical)
                ? physical.roadQuoteCost : -1)
            + " pred_profit=" + (admittedLong != null ? admittedLong.profitAnnual : -1)
            + " pred_capital=" + (admittedLong != null ? admittedLong.capital : -1)
            + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
             + " plan_ops=" + planOps + " pair_ops=" + pairOps
             + " attempt_cap=" + attemptLimit
             + " total_ops=" + longOps);
        continue;
      }
      /* Ce point est l'unique appel physique LONG. Une tentative indivisible
       * peut depasser la borne soft ; la suivante ne demarre alors jamais. */
      local longMark = OpexOpsMeasureBegin();
      local shadow = OpexRoad100LongCorridorShadow(catalog, preliminaryLong,
          250000 - longOps);
      local measuredOps = OpexOpsMeasureEnd(longMark);
      longOps += measuredOps;
      longAttempts++;
      local shadowOk = shadow != null && ("ok" in shadow) && shadow.ok;
      if (shadowOk) longOk++;
      if (DECISION_LOG) {
        local reason = shadow != null && ("reason" in shadow) &&
            typeof shadow.reason == "string" ? shadow.reason : "NO_RESULT";
        local siteA = -1;
        local siteB = -1;
        local monthly = -1;
        local route = -1;
        local helperOps = -1;
        local tested = -1;
        local fleet = -1;
        local predictedProfit = -1;
        local predictedCapital = -1;
        local cash = -1;
        local maxSiteA = -1;
        local maxSiteB = -1;
        local maxPairMonthly = -1;
        local siteCountA = -1;
        local siteCountB = -1;
        local unionA = -1;
        local unionB = -1;
        local unionSingleA = -1;
        local unionSingleB = -1;
        local unionDeltaA = -1;
        local unionDeltaB = -1;
        local unionSatA = -1;
        local unionSatB = -1;
        local unionCombosA = -1;
        local unionCombosB = -1;
        local joinValidated = 0;
        if (shadow != null) {
          if ("siteA" in shadow) {
            if (typeof shadow.siteA == "integer") siteA = shadow.siteA;
            else if (typeof shadow.siteA == "table" && ("tile" in shadow.siteA))
              siteA = shadow.siteA.tile;
          }
          if ("siteB" in shadow) {
            if (typeof shadow.siteB == "integer") siteB = shadow.siteB;
            else if (typeof shadow.siteB == "table" && ("tile" in shadow.siteB))
              siteB = shadow.siteB.tile;
          }
          if ("monthly" in shadow && typeof shadow.monthly == "integer") monthly = shadow.monthly;
          if ("route" in shadow) {
            if (typeof shadow.route == "integer") route = shadow.route;
            else if (typeof shadow.route == "array") route = shadow.route.len();
          }
          if ("ops" in shadow && typeof shadow.ops == "integer") helperOps = shadow.ops;
          if ("tested" in shadow && typeof shadow.tested == "integer") tested = shadow.tested;
          if ("fleet" in shadow && typeof shadow.fleet == "integer") fleet = shadow.fleet;
          if ("pred_profit" in shadow && typeof shadow.pred_profit == "integer")
            predictedProfit = shadow.pred_profit;
          if ("pred_capital" in shadow && typeof shadow.pred_capital == "integer")
            predictedCapital = shadow.pred_capital;
          if ("cash" in shadow && typeof shadow.cash == "integer") cash = shadow.cash;
          if ("max_site_a" in shadow) maxSiteA = shadow.max_site_a;
          if ("max_site_b" in shadow) maxSiteB = shadow.max_site_b;
          if ("max_pair_monthly" in shadow) maxPairMonthly = shadow.max_pair_monthly;
          if ("sites_a" in shadow) siteCountA = shadow.sites_a;
          if ("sites_b" in shadow) siteCountB = shadow.sites_b;
          if ("max_union_a" in shadow) unionA = shadow.max_union_a;
          if ("max_union_b" in shadow) unionB = shadow.max_union_b;
          if ("union_single_a" in shadow) unionSingleA = shadow.union_single_a;
          if ("union_single_b" in shadow) unionSingleB = shadow.union_single_b;
          if ("delta_single_a" in shadow) unionDeltaA = shadow.delta_single_a;
          if ("delta_single_b" in shadow) unionDeltaB = shadow.delta_single_b;
          if ("union_satellites_a" in shadow) unionSatA = shadow.union_satellites_a;
          if ("union_satellites_b" in shadow) unionSatB = shadow.union_satellites_b;
          if ("union_combos_a" in shadow) unionCombosA = shadow.union_combos_a;
          if ("union_combos_b" in shadow) unionCombosB = shadow.union_combos_b;
          if ("join_validated" in shadow && shadow.join_validated) joinValidated = 1;
        }
        OpexDecide("ROAD100_LONG", "phase=shadow rank=" + li
            + " src=" + preliminaryLong.src + " dst=" + preliminaryLong.dst
            + " town_a=" + preliminaryLong.srcTown + " town_b=" + preliminaryLong.dstTown
            + " centre_dist=" + selected.distance + " proxy_monthly=" + selected.proxy
            + " ok=" + (shadowOk ? 1 : 0) + " reason=" + reason
            + " siteA=" + siteA + " siteB=" + siteB + " site_monthly=" + monthly
            + " route=" + route + " tested=" + tested + " fleet=" + fleet
            + " pred_profit=" + predictedProfit + " pred_capital=" + predictedCapital
            + " cash=" + cash + " helper_ops=" + helperOps
            + " max_site_a=" + maxSiteA + " max_site_b=" + maxSiteB
            + " max_pair_monthly=" + maxPairMonthly
            + " sites_a=" + siteCountA + " sites_b=" + siteCountB
            + " union_a=" + unionA + " union_b=" + unionB
            + " union_single_a=" + unionSingleA + " union_single_b=" + unionSingleB
            + " union_delta_a=" + unionDeltaA + " union_delta_b=" + unionDeltaB
            + " union_sat_a=" + unionSatA + " union_sat_b=" + unionSatB
            + " union_combos_a=" + unionCombosA + " union_combos_b=" + unionCombosB
            + " join_validated=" + joinValidated
            + " measured_ops=" + measuredOps + " total_ops=" + longOps);
      }
    }
    if (DECISION_LOG) OpexDecide("ROAD100_LONG", "phase=summary towns=" + longCount
        + " examined=" + longExamined + " in_band=" + longInBand
        + " shortlisted=" + longBest.len() + " attempts=" + longAttempts
        + " physical_ok=" + longOk + " ops=" + longOps
        + " opcap=" + (longOps >= longCap ? 1 : 0)
        + " admitted=" + longAdmitted
        + " build=" + (ROAD100_LONG_BUILD ? 1 : 0));
    /* Verrou annuel posé seulement au terme complet d'une recherche globale. */
    if (isGlobalSearch) {
      ROAD100_LONG_SHADOW_YEAR = AIDate.GetYear(AIDate.GetCurrentDate());
    }
  }
}

function OpexRoad100SiteFirstCandidates(catalog, lines, out, stats,
                                       abandonedPairs = null, targetKind = null, targetId = -1)
{
  local iterator = OpexRoad100SiteFirstGenerator(catalog, lines, out, stats,
                                                abandonedPairs, targetKind, targetId);
  while (iterator.getstatus() != "dead") resume iterator;
}

function OpexRoad100SoloPaxCandidates(catalog, lines, out, stats,
                                      abandonedPairs = null, targetKind = null, targetId = -1)
{
  if (!ROAD100_SOLO_PAX || (targetKind != null && targetKind != "town")) return;
  if (ROAD100_SITE_FIRST) {
    OpexRoad100SiteFirstCandidates(catalog, lines, out, stats, abandonedPairs, targetKind, targetId);
    return;
  }
  local cargo = catalog.paxCargo;
  if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) return;
  local towns = catalog.towns;
  local ranked = [];
  foreach (i, town in towns) {
    if (OpexTownBusPaxServed(lines, town.id)
        || OpexTownRoadLineCount(lines, town.tile) >= 4) continue;
    local monthly = AITown.GetLastMonthProduction(town.id, cargo);
    if (monthly <= 0 && town.pop > 0) monthly = (town.pop * 15) / 100;
    if (monthly <= 0) continue;
    local houses = ("houses" in town && town.houses > 0) ? town.houses : (town.pop / 25);
    if (houses < 1) houses = 1;
    /* Meme capture prudente que le generateur de bus historique V231 :
     * une dizaine de maisons dans le rayon de l'arret, au plus 86 % du flux.
     * Le site reel devra encore etre valide par le constructeur. */
    local pct = (10 * 100) / houses;
    if (pct > 86) pct = 86;
    if (pct < 1) pct = 1;
    local captured = (monthly * pct) / 100;
    if (captured < 1) continue;
    ranked.append({ index = i, id = town.id, captured = captured, totalMonthly = monthly });
  }
  ranked.sort(OpexRoad100SortTownDemand);
  local n = ranked.len();
  if (n > 40) n = 40;
  local examined = 0;
  local positive = 0;
  for (local a = 0; a < n; a++) {
    local found = 0;
    for (local b = a + 1; b < n && found < 12; b++) {
      local src = ranked[a];
      local dst = ranked[b];
      if (targetKind == "town" && targetId >= 0
          && src.id != targetId && dst.id != targetId) continue;
      examined++;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("road", 1);
      local townA = towns[src.index];
      local townB = towns[dst.index];
      if (OpexRoadPairServed(lines, townA.tile, townB.tile)) continue;
      local distance = AIMap.DistanceManhattan(townA.tile, townB.tile);
      if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
      if (abandonedPairs != null) {
        local idA = src.id;
        local idB = dst.id;
        if (idA > idB) { local swapId = idA; idA = idB; idB = swapId; }
        local pairKey = "pax|" + cargo + "|" + idA + "|" + idB;
        if (pairKey in abandonedPairs) continue;
      }
      stats.pairsInBand++;
      local monthly = ROAD100_INTERCITY_SITE_FLEET
          ? (src.totalMonthly + dst.totalMonthly) : (src.captured + dst.captured);
      local candidate = OpexMakeRoadCandidate(catalog, "pax", cargo, townA.tile,
          townB.tile, src.id, dst.id, distance, monthly, stats, false,
          ROAD100_INTERCITY_SITE_FLEET ? 30 : 0);
      if (candidate != null) {
        if (ROAD100_INTERCITY_SITE_FLEET) {
          candidate.road100FleetCap <- 30;
          candidate.road100IntercitySiteFleet <- true;
        }
        out.append(candidate);
        positive++;
        found++;
      }
    }
  }
  if (DECISION_LOG) {
    OpexDecide("ROAD100_PAX_GEN", "towns=" + n + " examined=" + examined
        + " positive=" + positive + " kept_total=" + out.len());
  }
}

/* ROAD100-2 : une liaison courte entre deux quartiers de la MEME ville.
 * Le financement, l'economie reelle et le rejet de la ville deja desservie
 * restent ceux de la route commune. Par construction ce vivier n'existe
 * qu'en route seule et seulement lorsque le reglage vaut 1. */
function OpexRoad100TownBusCandidates(catalog, lines, out, stats,
                                      abandonedPairs = null, targetKind = null, targetId = -1)
{
  if (!ROAD100_TOWN_BUS || (targetKind != null && targetKind != "town")) return;
  local cargo = catalog.paxCargo;
  if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) return;
  local nTowns = 0;
  local nPositive = 0;
  local nInBand = 0;
  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  foreach (town in catalog.towns) {
    if (targetKind == "town" && targetId >= 0 && town.id != targetId) continue;
    if (OpexTownBusPaxServed(lines, town.id) || OpexTownRoadLineCount(lines, town.tile) >= 4)
      continue;
    local monthly = AITown.GetLastMonthProduction(town.id, cargo);
    if (monthly <= 0 && town.pop > 0) monthly = (town.pop * 15) / 100;
    if (monthly <= 0) continue;
    local houses = ("houses" in town && town.houses > 0) ? town.houses : town.pop / 25;
    if (houses < 1) houses = 1;
    local pct = (20 * 100) / houses;
    if (pct > 86) pct = 86;
    if (pct < 1) pct = 1;
    local captured = (monthly * pct) / 100;
    if (captured < 1) continue;
    local cx = AIMap.GetTileX(town.tile);
    local cy = AIMap.GetTileY(town.tile);
    local ends = null;
    for (local axis = 0; axis < 2 && ends == null; axis++) {
      local ax = cx - (axis == 0 ? 5 : 0);
      local bx = cx + (axis == 0 ? 5 : 0);
      local ay = cy - (axis == 1 ? 5 : 0);
      local by = cy + (axis == 1 ? 5 : 0);
      if (ax < 0 || ay < 0 || bx >= width || by >= height) continue;
      local src = AIMap.GetTileIndex(ax, ay);
      local dst = AIMap.GetTileIndex(bx, by);
      if (AITile.GetClosestTown(src) != town.id || AITile.GetClosestTown(dst) != town.id)
        continue;
      ends = { src = src, dst = dst };
    }
    if (ends == null) continue;
    nTowns++;
    if (OpexRoadPairServed(lines, ends.src, ends.dst)) continue;
    local distance = AIMap.DistanceManhattan(ends.src, ends.dst);
    if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
    nInBand++;
    if (abandonedPairs != null) {
      local pairKey = "pax|" + cargo + "|" + town.id + "|" + town.id;
      if (pairKey in abandonedPairs) continue;
    }
    stats.pairsInBand++;
    if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("road", 1);
    local candidate = OpexMakeRoadCandidate(catalog, "pax", cargo, ends.src,
        ends.dst, town.id, town.id, distance, captured, stats, false,
        ROAD100_PAX_FLEET_CAP);
    if (candidate != null) {
      if (ROAD100_PAX_FLEET_CAP > 0)
        candidate.road100FleetCap <- ROAD100_PAX_FLEET_CAP;
      out.append(candidate);
      nPositive++;
    }
  }
  if (DECISION_LOG) {
    OpexDecide("ROAD100_TOWN_GEN", "towns=" + nTowns + " in_band=" + nInBand
        + " positive=" + nPositive + " kept_total=" + out.len());
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
/* ROAD100-21 : la meme liste d'admission est utilisee par les chemins
 * synchrones ET PO01C, sans multiplier les appels au generateur PAX.
 * V276 possede deja ses propres unites fret par cargo : ne pas les doubler. */
function OpexRoad100FreightDiverseCargoSet(catalog, primary)
{
  local allowed = {};
  if (primary == null) return allowed;
  allowed.rawset(primary, true);
  if (!ROAD100_FREIGHT_DIVERSITY || !MODE_ROAD || MODE_RAIL || MODE_AIR ||
      MODE_WATER || V276_CAND_SLICES > 0) return allowed;
  local order = OpexFreightCargoOrder(catalog);
  local first = -1;
  for (local i = 0; i < order.len(); i++) {
    if (order[i] == primary) { first = i; break; }
  }
  local extras = 0;
  for (local offset = 1; offset < order.len() && extras < 2; offset++) {
    local index = first >= 0 ? (first + offset) % order.len() : offset - 1;
    local cargo = order[index];
    if (cargo == primary || cargo == catalog.paxCargo ||
        !(cargo in catalog.roadEngineByCargo) ||
        !(cargo in catalog.producers) || catalog.producers[cargo].len() == 0)
      continue;
    allowed.rawset(cargo, true);
    extras++;
  }
  return allowed;
}

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
  local diversityCargos = (ROAD100_FREIGHT_DIVERSITY && freightCargo != null &&
      V276_CAND_SLICES <= 0) ? OpexRoad100FreightDiverseCargoSet(catalog, freightCargo) : null;
  /* Rayon d'une aire de chargement : c'est bien l'empreinte de la gare qu'on projette de poser,
   * pas un rayon arbitraire autour du centre administratif. Lu une fois, il ne change jamais. */
  local truckCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
  if (profile != null) profile.freightPreparationOps += OpexOpsMeasureEnd(preparationMark);

  foreach (cargo, sources in catalog.producers) {
    if (freightCargo != null && cargo != freightCargo &&
        (diversityCargos == null || !(cargo in diversityCargos))) continue;
    if (!(cargo in catalog.roadEngineByCargo)) { stats.noEngine++; continue; }
    /* Les passagers sont traites par la famille 1 : les inclure ici apparierait une industrie a
     * une ville pour un cargo qu'aucune industrie ne produit utilement en volume. */
    if (cargo == catalog.paxCargo) continue;
    local servedIndustryCargo = servedIndustry;
    local servedTownCargo = servedTown;
    if (ROAD100_FREIGHT_CARGO_ORIGIN && V276_CAND_SLICES <= 0) {
      /* Un index per-cargo, sans valuation de terrain et sans double scan PAX. */
      local sameCargoIndex = OpexRoadFreightServedIndex(lines, cargo);
      servedIndustryCargo = [];
      servedTownCargo = [];
      foreach (industry in industries) {
        servedIndustryCargo.append(industry.tile in sameCargoIndex);
      }
      foreach (town in towns) {
        servedTownCargo.append(town.tile in sameCargoIndex);
      }
    }
    local sinks = (cargo in catalog.acceptors) ? catalog.acceptors[cargo] : [];
    /* C41.20 : la liste est locale au cargo et a cette generation. Les appels API anticipes sont
     * purs ; ils ne changent ni l'industrie, ni le filtre de distance, ni l'ordre des candidats. */
    local townTargets = OpexRoadFreightAcceptedTowns(towns, servedTownCargo, cargo, truckCoverage);
    if (townTargets != null) stats.townAcceptancePrefiltered += towns.len() - townTargets.len();

    foreach (si in sources) {
      if (servedIndustryCargo[si]) {
        /* Le code livre saute toute la source. Sous sonde, enumerer seulement les paires
         * qu'il aurait sautees permet de compter ce filtre sans changer son continue. */
        if (C55_ORIGIN_RELAX_PROBE) {
          local source = industries[si];
          foreach (di in sinks) {
            if (di != si) OpexC55OriginRelaxObserve("freight", lines, source.tile,
                industries[di].tile, true, servedIndustryCargo[di]);
          }
          for (local ti = 0; ti < towns.len(); ti++) {
            OpexC55OriginRelaxObserve("freight", lines, source.tile, towns[ti].tile,
                true, servedTownCargo[ti]);
          }
        }
        continue;
      }
      local source = industries[si];
      if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      if ((ESTIM_UNIFIE & 8) != 0 && !OpexOriginServed(lines, source.tile, true))
        monthly = OpexEstimRivalAvailableMonthly(monthly,
            AIIndustry.GetLastMonthTransportedPercentage(source.id, cargo));
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
            source.tile, industries[di].tile, false, servedIndustryCargo[di]);
        if (servedIndustryCargo[di]) {
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
              false, servedTownCargo[ti]);
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
            lines, source.tile, towns[t].tile, false, servedTownCargo[t]);
        if (townTargets == null && servedTownCargo[t]) {
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

/* MULTI-1 : observation privee d'un cargo ROUTE absent du lot courant.
 * Ce curseur ne publie AUCUN projet et ne construit rien. Le cout est decoupe
 * entre deux tours de boucle ; un plan routier individuel demeure atomique. */
function OpexMulti1RoadCargoShadowLog(fields)
{
  /* OpexDecide modifierait _currentTaskLogged ; une sonde ne doit jamais
   * consommer le marqueur de la decision active. */
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date)
      + "-" + AIDate.GetDayOfMonth(date) + " MULTI1_ROAD_CARGO_SHADOW " + fields);
}

function OpexMulti1RoadCargoSortProfit(a, b)
{
  if (a.profitAnnual != b.profitAnnual) return a.profitAnnual > b.profitAnnual ? -1 : 1;
  if (a.src != b.src) return a.src < b.src ? -1 : 1;
  if (a.dst != b.dst) return a.dst < b.dst ? -1 : 1;
  return 0;
}

function OpexMulti1RoadCargoSample(list, count, stamp)
{
  local out = [];
  if (list == null || list.len() == 0) return out;
  local start = stamp % list.len();
  for (local i = 0; i < count && i < list.len(); i++)
    out.append(list[(start + i) % list.len()]);
  return out;
}

function OpexMulti1RoadCargoShadowArm(catalog, lines, abandonedPairs, freightCargo, ordinary)
{
  if (MULTI1_ROAD_CARGO_SHADOW != 1 || !DECISION_LOG || !MODE_AIR || !MODE_RAIL
      || !MODE_ROAD || !ROAD_BUILD_ENABLED || V276_CAND_SLICES > 0
      || catalog == null || catalog.roadType < 0 || freightCargo == null
      || MULTI1_ROAD_CARGO_PENDING != null) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (year < 1971 || year > 1973) return;
  local stamp = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (stamp == MULTI1_ROAD_CARGO_LAST_MONTH) return;
  MULTI1_ROAD_CARGO_LAST_MONTH = stamp;

  /* La caisse financant deja un candidat normal signifie qu'il n'y a
   * pas de trou a combler dans le lot courant. C'est le seul test
   * supplementaire paye lors de la generation historique. */
  local available = OpexAvailableCapital();
  if (ordinary != null) foreach (candidate in ordinary) {
    local project = OpexProjectFromCandidate(candidate);
    if (project != null && OpexProjectFinanceCapital(project) <= available) {
      OpexMulti1RoadCargoShadowLog("phase=skip year=" + year
          + " month=" + stamp + " reason=ordinary_financeable");
      return;
    }
  }

  local order = OpexFreightCargoOrder(catalog);
  local start = -1;
  for (local i = 0; i < order.len(); i++)
    if (order[i] == freightCargo) { start = i; break; }
  local alternate = -1;
  for (local offset = 1; offset < order.len(); offset++) {
    local idx = start >= 0 ? (start + offset) % order.len() : offset - 1;
    local cargo = order[idx];
    if (cargo != freightCargo && catalog.roadEngineByCargo != null
        && cargo in catalog.roadEngineByCargo) { alternate = cargo; break; }
  }
  if (alternate < 0) {
    OpexMulti1RoadCargoShadowLog("phase=skip year=" + year
        + " month=" + stamp + " reason=no_secondary_road_cargo");
    return;
  }

  local snapshot = clone catalog;
  snapshot.towns = clone catalog.towns;
  snapshot.industries = clone catalog.industries;
  snapshot.producers = clone catalog.producers;
  snapshot.acceptors = clone catalog.acceptors;
  local sources = OpexMulti1RoadCargoSample(catalog.producers[alternate], 2, stamp);
  local sinks = (alternate in catalog.acceptors)
      ? OpexMulti1RoadCargoSample(catalog.acceptors[alternate], 4, stamp + 1) : [];
  local destinations = [];
  foreach (industryIndex in sinks)
    destinations.append({ kind = "industry", industryIndex = industryIndex });
  foreach (town in OpexMulti1RoadCargoSample(catalog.towns, 4, stamp + 2))
    destinations.append({ kind = "town", town = town });

  MULTI1_ROAD_CARGO_PENDING = {
    catalog = snapshot, lines = lines != null ? OpexPO01CCopyLines(lines) : [],
    abandoned = abandonedPairs != null ? clone abandonedPairs : {},
    cargo = alternate, ordinaryCargo = freightCargo, year = year, stamp = stamp,
    sources = sources, destinations = destinations, pairCursor = 0,
    phase = "pairs", financeableCandidates = [], planCursor = 0,
    examined = 0, economic = 0, financeable = 0, plans = 0, planned = 0,
    positivePlans = 0, predictedProfit = 0, stale = 0,
    totalOps = 0, censored = false,
    stats = { noEngine = 0, noMonthly = 0, pairsInBand = 0,
      townRejected = 0, profitTooLow = 0, profitNonPositive = 0,
      profitBelowFloorKept = 0, accepted = 0, economicsUnavailable = 0,
      roadDistanceShort = 0, roadDistanceLong = 0 }
  };
  OpexMulti1RoadCargoShadowLog("phase=arm year=" + year
      + " month=" + stamp + " original=" + freightCargo
      + " cargo=" + alternate + " sources=" + sources.len()
      + " destinations=" + destinations.len() + " cash=" + available);
}

function OpexMulti1RoadCargoShadowPair(s)
{
  if (s.destinations.len() == 0) return;
  local index = s.pairCursor;
  s.pairCursor++;
  local sourceIndex = s.sources[(index / s.destinations.len()).tointeger()];
  if (sourceIndex < 0 || sourceIndex >= s.catalog.industries.len()) return;
  local source = s.catalog.industries[sourceIndex];
  if (OpexOriginServed(s.lines, source.tile, true)) return;
  if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) return;
  local monthly = AIIndustry.GetLastMonthProduction(source.id, s.cargo);
  if ((ESTIM_UNIFIE & 8) != 0)
    monthly = OpexEstimRivalAvailableMonthly(monthly,
        AIIndustry.GetLastMonthTransportedPercentage(source.id, s.cargo));
  if (monthly <= 0) { s.stats.noMonthly++; return; }
  local dest = s.destinations[index % s.destinations.len()];
  local dstTile, dstTown = -1, pairKey, isTransformer = false;
  if (dest.kind == "industry") {
    if (dest.industryIndex < 0 || dest.industryIndex >= s.catalog.industries.len()
        || dest.industryIndex == sourceIndex) return;
    local industry = s.catalog.industries[dest.industryIndex];
    dstTile = industry.tile;
    pairKey = "freight|" + s.cargo + "|" + source.id + "|" + industry.id;
    isTransformer = ("isTransformer" in industry) && industry.isTransformer;
  } else {
    dstTile = dest.town.tile;
    dstTown = dest.town.id;
    pairKey = "freight|" + s.cargo + "|" + source.id + "|t" + dstTown;
    local coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
    if (AITile.GetCargoAcceptance(dstTile, s.cargo, 1, 1, coverage)
        < ROAD_ACCEPTANCE_FULL_UNIT) { s.stats.townRejected++; return; }
  }
  if (OpexOriginServed(s.lines, dstTile, true) || pairKey in s.abandoned) return;
  local distance = AIMap.DistanceManhattan(source.tile, dstTile);
  if (!OpexRoadDistanceAllowed(s.catalog, distance, s.stats)) return;
  s.examined++;
  local candidate = OpexMakeRoadCandidate(s.catalog, "freight", s.cargo,
      source.tile, dstTile, -1, dstTown, distance, monthly, s.stats, isTransformer);
  if (candidate == null) return;
  s.economic++;
  local project = OpexProjectFromCandidate(candidate);
  if (project == null || OpexProjectFinanceCapital(project) > OpexAvailableCapital()) return;
  s.financeable++;
  s.financeableCandidates.append(candidate);
}

function OpexMulti1RoadCargoShadowTick(owner)
{
  local s = MULTI1_ROAD_CARGO_PENDING;
  if (s == null || MULTI1_ROAD_CARGO_SHADOW != 1) return false;
  local mark = OpexOpsMeasureBegin();
  local tick = AIController.GetTick();
  while (AIController.GetTick() == tick && AIController.GetOpsTillSuspend() > 2000
      && OpexOpsMeasureEnd(mark) < 40000) {
    if (s.totalOps + OpexOpsMeasureEnd(mark) >= 200000) {
      s.censored = true;
      s.phase = "done";
    }
    if (s.phase == "pairs") {
      if (s.pairCursor < s.sources.len() * s.destinations.len()) {
        OpexMulti1RoadCargoShadowPair(s);
        continue;
      }
      s.financeableCandidates.sort(OpexMulti1RoadCargoSortProfit);
      s.phase = "plans";
    } else if (s.phase == "plans") {
      if (s.planCursor >= s.financeableCandidates.len() || s.planCursor >= 3) {
        s.phase = "done";
        continue;
      }
      local candidate = s.financeableCandidates[s.planCursor++];
      /* Une generation PO01c peut durer plusieurs jours. Si la ligne est
       * apparue entre temps, ce plan n'est plus une occasion additionnelle. */
      if (owner._lines == null
          || OpexOriginServed(owner._lines, candidate.src, true)
          || OpexOriginServed(owner._lines, candidate.dst, true)
          || OpexCandidateIsAbandoned(candidate, owner._abandonedPairs)) {
        s.stale++;
        OpexMulti1RoadCargoShadowLog("phase=plan month=" + s.stamp
            + " cargo=" + s.cargo + " src=" + candidate.src + " dst=" + candidate.dst
            + " reason=STALE profit=0 plan_ops=0");
        continue;
      }
      local planMark = OpexOpsMeasureBegin();
      local roadTypeBefore = AIRoad.GetCurrentRoadType();
      local siteNameBefore = OPCODE_EXACT_SITE_NAME;
      local planning = OpexRoadPlanFor(s.catalog, candidate);
      AIRoad.SetCurrentRoadType(roadTypeBefore);
      OPCODE_EXACT_SITE_NAME = siteNameBefore;
      local planOps = OpexOpsMeasureEnd(planMark);
      s.plans++;
      local realProfit = 0;
      if (planning != null && planning.plan != null) {
        s.planned++;
        local plan = planning.plan;
        local actualDistance = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
        if (actualDistance < 1) actualDistance = 1;
        local economics = OpexRoadLineEconomics(s.catalog, candidate.cargo, actualDistance,
            candidate.monthly, candidate.engine, candidate.kind, plan.routeDistance);
        if (economics != null && economics.profitAnnual > 0) {
          realProfit = economics.profitAnnual;
          s.positivePlans++;
          /* Plusieurs projets peuvent partager une origine ou un puits :
           * leur somme n'est pas un gain marginal simultanement realisable. */
          if (realProfit > s.predictedProfit) s.predictedProfit = realProfit;
        }
      }
      OpexMulti1RoadCargoShadowLog("phase=plan month=" + s.stamp
          + " cargo=" + s.cargo + " src=" + candidate.src
          + " dst=" + candidate.dst + " reason="
          + (planning != null ? planning.reason : "NO_PLAN")
          + " profit=" + realProfit + " plan_ops=" + planOps);
    } else {
      break;
    }
  }
  s.totalOps += OpexOpsMeasureEnd(mark);
  if (s.phase == "done") {
    OpexMulti1RoadCargoShadowLog("phase=done month=" + s.stamp
        + " original=" + s.ordinaryCargo + " cargo=" + s.cargo
        + " pairs=" + s.examined + " economic=" + s.economic
        + " financeable=" + s.financeable + " plans=" + s.plans
        + " planned=" + s.planned + " positive=" + s.positivePlans
        + " stale=" + s.stale + " best_profit=" + s.predictedProfit + " ops=" + s.totalOps
        + " sampled=1 censored=" + (s.censored ? 1 : 0));
    MULTI1_ROAD_CARGO_PENDING = null;
  }
  return true;
}

/* Classement routier complet. Rendu a part de celui du rail : les deux ne partagent ni leur unite
 * de cout (cf. ROAD_PLAN_ITERATIONS_BASE) ni leur phase de construction. */
/* C41.16 : `profile` est fourni seulement par la sonde du scheduler. Il n'influence jamais les
 * filtres, l'ordre ni le vivier ; les compteurs mesurent les trois familles et le TopK qui suit
 * le budget historique. */
/* ROAD100-27 : un marche absent de la famille de fret industrielle : le
 * courrier PRODUIT par une ville et ACCEPTE par une seconde. Une vraie
 * gare camion, un depot, une route et la capture exacte du site A sont
 * obligatoires avant le classement. Le retour B->A n'est PAS valorise.
 * Un seul iterateur est utilise par le calendrier sync et PO01C. */
function OpexRoad100MailOwnedCoverage()
{
  local covered = AITileList();
  local ids = AIStationList(AIStation.STATION_ANY);
  for (local id = ids.Begin(); !ids.IsEnd(); id = ids.Next()) {
    if (!AIStation.IsValidStation(id)) continue;
    covered.AddList(AITileList_StationCoverage(id));
  }
  return covered;
}

/* Ce scan est sur la couverture REELLE de la tuile où sera la station,
 * pas la production de la ville ou l'attente d'une ligne AAA. Une tuile
 * de production déjà captée par une station propre n'est jamais recomptée.
 * Le même helper est invoqué à l'admission ET au chantier. */
function OpexRoad100MailMarginalSource(cargo, stopTile, covered)
{
  if (cargo < 0 || !AIMap.IsValidTile(stopTile)) return 0;
  local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
  if (radius < 1) return 0;
  local x = AIMap.GetTileX(stopTile);
  local y = AIMap.GetTileY(stopTile);
  local x0 = x - radius; if (x0 < 0) x0 = 0;
  local y0 = y - radius; if (y0 < 0) y0 = 0;
  local x1 = x + radius;
  if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
  local y1 = y + radius;
  if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
  local sources = AITileList();
  sources.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
  sources.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
  sources.KeepAboveValue(0);
  local total = 0;
  foreach (tile, amount in sources) {
    if (covered != null && covered.HasItem(tile)) continue;
    total += amount;
  }
  return total;
}

function OpexRoad100MailPairSort(a, b)
{
  if (ROAD100_MAIL_LONG_EXISTING) {
    local longA = a.distance >= 43;
    local longB = b.distance >= 43;
    if (longA != longB) return longA ? -1 : 1;
  }
  if (a.sourceMonthly != b.sourceMonthly)
    return a.sourceMonthly > b.sourceMonthly ? -1 : 1;
  if (a.distance != b.distance) return a.distance < b.distance ? -1 : 1;
  if (a.from.id != b.from.id) return a.from.id < b.from.id ? -1 : 1;
  return a.to.id < b.to.id ? -1 : (a.to.id > b.to.id ? 1 : 0);
}

/* ROAD100-29 : prioritisation de visite seulement, jamais score portefeuille.
 * L'ordre interurbain est determine par la production native des villes,
 * tandis que tout debit financier sera borne aux vrais producteurs du site A. */
function OpexRoad100PaxRootsSortPair(a, b)
{
  if (a.priority != b.priority) return a.priority > b.priority ? -1 : 1;
  if (a.distance != b.distance) return a.distance < b.distance ? -1 : 1;
  if (a.from.id != b.from.id) return a.from.id < b.from.id ? -1 : 1;
  return a.to.id < b.to.id ? -1 : (a.to.id > b.to.id ? 1 : 0);
}

/* Bus et camion ne sont PAS supposes partager le rayon de couverture.
 * Produits des tuiles source, et non total du centre-ville, moins TOUTE
 * couverture propre. Une tuile productrice n'est sommee qu'une fois. */
function OpexRoad100PaxRootsMarginalSource(cargo, stopTile, covered)
{
  if (cargo < 0 || !AIMap.IsValidTile(stopTile)) return 0;
  local radius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  if (radius < 1) return 0;
  local x = AIMap.GetTileX(stopTile);
  local y = AIMap.GetTileY(stopTile);
  local x0 = x - radius; if (x0 < 0) x0 = 0;
  local y0 = y - radius; if (y0 < 0) y0 = 0;
  local x1 = x + radius;
  local y1 = y + radius;
  if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
  if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
  local producers = AITileList();
  producers.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
  producers.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
  producers.KeepAboveValue(0);
  local total = 0;
  foreach (tile, volume in producers) {
    if (covered != null && covered.HasItem(tile)) continue;
    total += volume;
  }
  return total;
}

/* Prescreen MINIMAL : uniquement des routes deja presentes, avec facade
 * bidirectionnelle et BuildDriveThroughRoadStation(STATION_NEW) en AITest.
 * 12 tuiles de route visitees par ville, 2 essais de station maximum.
 * Le test ne construit RIEN et ne certifie ni nouveau StationID effectif,
 * ni depot, ni corridor interurbain continu. Ces lacunes sont loguees.
 * La capture est marginale a TOUTES nos stations, jamais une demande-ville. */
function OpexRoad100PaxRootsTownSite(town, cargo, covered, mark, budget)
{
  local result = { tile = -1, front = -1, marginal = 0,
      acceptance = 0, roads = 0, tests = 0, reason = "NO_SITE" };
  local radius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  if (radius < 1) { result.reason = "COVERAGE"; return result; }
  local cx = AIMap.GetTileX(town.tile);
  local cy = AIMap.GetTileY(town.tile);
  local r = 8;
  local x0 = cx - r; if (x0 < 0) x0 = 0;
  local y0 = cy - r; if (y0 < 0) y0 = 0;
  local x1 = cx + r;
  local y1 = cy + r;
  if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
  if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
  local roads = AITileList();
  roads.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
  roads.Valuate(AIRoad.IsRoadTile);
  roads.KeepAboveValue(0);
  local directions = [1, -1, AIMap.GetMapSizeX(), -AIMap.GetMapSizeX()];
  for (local tile = roads.Begin(); !roads.IsEnd() && result.roads < 12;
       tile = roads.Next()) {
    if (OpexOpsMeasureEnd(mark) >= budget - 15000) {
      result.reason = "OPCAP"; return result;
    }
    result.roads++;
    if (AITile.IsStationTile(tile) || AIRoad.IsRoadDepotTile(tile)
        || covered.HasItem(tile) || AITile.GetClosestTown(tile) != town.id) continue;
    local marginal = OpexRoad100PaxRootsMarginalSource(cargo, tile, covered);
    if (marginal <= result.marginal) continue;
    for (local di = 0; di < directions.len() && result.tests < 2; di++) {
      if (OpexOpsMeasureEnd(mark) >= budget - 10000) {
        result.reason = "OPCAP"; return result;
      }
      local front = tile + directions[di];
      if (!AIMap.IsValidTile(front) || AIMap.DistanceManhattan(tile, front) != 1
          || !AIRoad.IsRoadTile(front)
          || !AIRoad.AreRoadTilesConnected(tile, front)
          || !AIRoad.AreRoadTilesConnected(front, tile)) continue;
      local buildable = false;
      result.tests++;
      { local test = AITestMode();
        buildable = AIRoad.BuildDriveThroughRoadStation(tile, front,
            AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
      if (!buildable) continue;
      result.tile = tile;
      result.front = front;
      result.marginal = marginal;
      result.acceptance = AITile.GetCargoAcceptance(tile, cargo, 1, 1, radius);
      result.reason = "FRONT_ONLY";
      break;
    }
    if (result.tests >= 2) break;
  }
  return result;
}

/* ROAD100-29 : SHADOW NON CONSTRUCTEUR. Partage par les chemins synchrone
 * et PO01C via le MEME generateur ; PO01C reprend entre paires. Budget
 * annuel transitoire (un scan par annee/processus) : <= 2 vrais couples,
 * <= 200k opcodes soft, aucun A*, BFS, projet, ranking ou chantier.
 * Le ROI reel est -1 (non quote) : les facades A/B, meme constructibles,
 * ne prouvent PAS une liaison, un depot ou deux StationID distincts.
 * Un plafond de revenu A->B est chiffre sans retour, sans satellite,
 * sans attendre AAA ; le cout plancher n'est PAS un devis complet. */
function OpexRoad100PaxRootsShadowGenerator(catalog)
{
  if (!ROAD100_PAX_INTERCITY_ROOTS) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (ROAD100_PAX_ROOTS_LAST_YEAR == year) return;
  ROAD100_PAX_ROOTS_LAST_YEAR = year;
  local mark = OpexOpsMeasureBegin();
  local limit = 200000;
  local towns = [];
  local pairs = [];
  local seen = 0;
  local inBand = 0;
  local scans = 0;
  local tested = 0;
  local facades = 0;
  local reason = "PRECHECK";
  local cargo = catalog != null ? catalog.paxCargo : -1;
  do {
    if (catalog == null || catalog.roadType < 0 || cargo < 0
        || !(cargo in catalog.roadEngineByCargo)) {
      reason = "NO_ENGINE"; break;
    }
    if (AIRoad.GetCurrentRoadType() != catalog.roadType) {
      reason = "ROAD_TYPE_MISMATCH"; break;
    }
    local radius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    local stopCost = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP);
    local engine = catalog.roadEngineByCargo[cargo];
    if (radius < 1 || stopCost <= 0 || engine == null || engine.price <= 0) {
      reason = "NO_PRICE"; break;
    }
    foreach (town in catalog.towns) {
      if (OpexOpsMeasureEnd(mark) >= limit - 20000) { reason = "OPCAP"; break; }
      local produced = AITown.GetLastMonthProduction(town.id, cargo);
      if (produced > 0) towns.append({ id = town.id, tile = town.tile,
          captured = produced });
    }
    if (reason == "OPCAP") break;
    towns.sort(OpexRoad100SortTownDemand);
    if (towns.len() > 12) towns.resize(12);
    for (local a = 0; a < towns.len(); a++) {
      if (OpexOpsMeasureEnd(mark) >= limit - 20000) { reason = "OPCAP"; break; }
      for (local b = a + 1; b < towns.len(); b++) {
        seen++;
        local distance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
        if (distance < 43 || distance > 80) continue;
        inBand++;
        pairs.append({ from = towns[a], to = towns[b], distance = distance,
            priority = towns[a].captured + towns[b].captured });
      }
    }
    if (reason == "OPCAP") break;
    pairs.sort(OpexRoad100PaxRootsSortPair);
    if (pairs.len() < 1) { reason = "NO_PAIR"; break; }
    /* Construire une seule union des couvertures EXISTANTES, dont les
     * gares rail/air/eau, pour eviter toute double production Opex. */
    local covered = AITileList();
    local stations = AIStationList(AIStation.STATION_ANY);
    for (local id = stations.Begin(); !stations.IsEnd(); id = stations.Next()) {
      if (OpexOpsMeasureEnd(mark) >= limit - 20000) { reason = "OPCAP"; break; }
      if (AIStation.IsValidStation(id)) covered.AddList(AITileList_StationCoverage(id));
    }
    if (reason == "OPCAP") break;
    local costFloor = engine.price + 2 * stopCost + catalog.costRoadDepot;
    if (costFloor <= 0) { reason = "NO_PRICE"; break; }
    /* Deux previsualisations ne sont pas deux marches independants si
     * elles reutilisent la MEME facade productrice. Pas de somme fictive. */
    local seenRootSites = {};
    for (local k = 0; k < pairs.len() && tested < 2; k++) {
      if (OpexOpsMeasureEnd(mark) >= limit - 20000) { reason = "OPCAP"; break; }
      yield null;
      local pair = pairs[k];
      tested++;
      local aSite = OpexRoad100PaxRootsTownSite(pair.from, cargo, covered,
          mark, limit);
      scans += aSite.roads;
      if (aSite.reason == "OPCAP") { reason = "OPCAP"; break; }
      yield null;
      local bSite = OpexRoad100PaxRootsTownSite(pair.to, cargo, covered,
          mark, limit);
      scans += bSite.roads;
      if (bSite.reason == "OPCAP") { reason = "OPCAP"; break; }
      local status = "NO_SITE";
      local revenueUpper = 0;
      local roiUpper = -1;
      if (aSite.tile >= 0 && bSite.tile >= 0) {
        facades++;
        status = "FRONT_ONLY_UNCONNECTED";
        if ((aSite.tile in seenRootSites) || (bSite.tile in seenRootSites))
          status = "REUSED_ROOT_NO_INCREMENT";
        else if (aSite.marginal <= 0) status = "NO_SOURCE";
        else if (bSite.acceptance < ROAD_ACCEPTANCE_FULL_UNIT) status = "NO_ACCEPT";
        else {
          /* Sur-estimation DECLAREE : tous les PASS source livrés avec
           * 0 jour de transit, sans temps de rotation ni bouchon.
           * B->A ne contribue en rien ; A seulement et 1 bus theorique. */
          local fareMax = AICargo.GetCargoIncome(cargo, pair.distance, 0);
          revenueUpper = 12 * aSite.marginal * fareMax;
          roiUpper = ((revenueUpper - engine.runningCost) * 1000) / costFloor;
          status = "UPPER_ONLY_NO_ROUTE_QUOTE";
        }
        seenRootSites.rawset(aSite.tile, true);
        seenRootSites.rawset(bSite.tile, true);
      }
      AILog.Info("ROAD100_PAX_ROOTS phase=pair year=" + year
          + " srcTown=" + pair.from.id + " dstTown=" + pair.to.id
          + " center_dist=" + pair.distance + " siteA=" + aSite.tile
          + " siteB=" + bSite.tile + " frontA=" + aSite.front
          + " frontB=" + bSite.front + " roadsA=" + aSite.roads
          + " roadsB=" + bSite.roads + " tests=" + (aSite.tests + bSite.tests)
          + " site_status_a=" + aSite.reason + " site_status_b=" + bSite.reason
          + " prod_a=" + aSite.marginal + " prod_b=" + bSite.marginal
          + " accept_b=" + bSite.acceptance + " cost_floor=" + costFloor
          + " cost_quote=-1 revenue_cap_a_to_b=" + revenueUpper
          + " roi=-1 roi_upper=" + roiUpper + " status=" + status
          + " ops=" + OpexOpsMeasureEnd(mark));
    }
    if (reason != "OPCAP") reason = facades > 0 ? "FRONTS_ONLY" : "NO_FRONT_PAIR";
  } while (false);
  AILog.Info("ROAD100_PAX_ROOTS phase=summary year=" + year
      + " status=" + reason + " towns=" + towns.len()
      + " pairs_scanned=" + seen + " in_band=" + inBand
      + " pairs_ranked=" + pairs.len() + " pairs_tested=" + tested
      + " roads_scanned=" + scans + " facade_pairs=" + facades
      + " ops=" + OpexOpsMeasureEnd(mark)
      + " admitted=0 built=0 route_quoted=0");
}

function OpexRoad100MailIntertownGenerator(catalog, lines, out, stats,
    abandonedPairs = null, targetKind = null, targetId = -1)
{
  if (!ROAD100_MAIL_INTERTOWN || catalog == null || catalog.mailCargo < 0
      || !(catalog.mailCargo in catalog.roadEngineByCargo)
      || (targetKind != null && targetKind != "town")) return;
  local cargo = catalog.mailCargo;
  local towns = [];
  foreach (town in catalog.towns) {
    local produced = AITown.GetLastMonthProduction(town.id, cargo);
    if (produced <= 0 || OpexOriginServed(lines, town.tile, true)) continue;
    towns.append({ id = town.id, tile = town.tile, monthly = produced });
  }
  towns.sort(function(a, b) {
    if (a.monthly != b.monthly) return a.monthly > b.monthly ? -1 : 1;
    return a.id < b.id ? -1 : (a.id > b.id ? 1 : 0);
  });
  if (towns.len() > 16) towns.resize(16);
  local pairs = [];
  foreach (from in towns) {
    foreach (to in towns) {
      if (from.id == to.id) continue;
      if (targetKind == "town" && targetId >= 0
          && from.id != targetId && to.id != targetId) continue;
      local d = AIMap.DistanceManhattan(from.tile, to.tile);
      if (d < (ROAD100_MAIL_LONG_EXISTING ? 43 : 12)
          || d > (ROAD100_MAIL_LONG_EXISTING ? 80 : 42)
          || OpexRoadPairServed(lines, from.tile, to.tile)) continue;
      if (abandonedPairs != null) {
        local key = "freight|" + cargo + "|t" + from.id + "|t" + to.id;
        if (key in abandonedPairs) continue;
      }
      pairs.append({ from = from, to = to, sourceMonthly = from.monthly,
          distance = d });
    }
  }
  pairs.sort(OpexRoad100MailPairSort);
  local covered = OpexRoad100MailOwnedCoverage();
  local tested = 0;
  local admitted = 0;
  local noPlan = 0;
  local noProfit = 0;
  local mark = OpexOpsMeasureBegin();
  foreach (pair in pairs) {
    if (tested >= 3 || OpexOpsMeasureEnd(mark) >= 200000) break;
    yield null;
    /* Proxy de ville pour LOCALISER le site uniquement, pas pour classer
     * une recette annuelle. Le planner ne reconnait du MAIL que sur son
     * site source, et l'acceptation pleine sur le site B. */
    local mailLong = ROAD100_MAIL_LONG_EXISTING;
    local preliminary = { mode = "road", kind = "freight", cargo = cargo,
        src = pair.from.tile, dst = pair.to.tile,
        srcTown = pair.from.id, dstTown = pair.to.id };
    if (mailLong) preliminary.road100MailLongExisting <- true;
    local siting = OpexRoadPlanFor(catalog, preliminary);
    tested++;
    if (siting.plan == null) { noPlan++; continue; }
    local plan = siting.plan;
    if (plan.vehType != AIRoad.ROADVEHTYPE_TRUCK
        || plan.stationType != AIStation.STATION_TRUCK_STOP
        || plan.stopA.value <= 0
        || plan.stopB.value < ROAD_ACCEPTANCE_FULL_UNIT) {
      noPlan++;
      continue;
    }
    local marginal = OpexRoad100MailMarginalSource(cargo, plan.stopA.tile, covered);
    if (marginal <= 0) { noPlan++; continue; }
    local realDistance = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
    if (realDistance < 1) { noPlan++; continue; }
    local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo,
        pair.from.tile, pair.to.tile, pair.from.id, pair.to.id,
        realDistance, marginal, stats);
    if (candidate == null) { noProfit++; continue; }
    local economics = OpexRoadLineEconomics(catalog, cargo, realDistance,
        marginal, candidate.engine, "freight", plan.routeDistance);
    if (mailLong)
      economics = OpexRoad100MailExistingEconomics(catalog, economics, plan);
    if (economics == null || economics.profitAnnual <= 0) {
      noProfit++;
      continue;
    }
    if (ROAD100_MAIL_LONG_EXISTING &&
        (economics.profitAnnual < 3000 || economics.roi < 250)) {
      noProfit++;
      continue;
    }
    OpexApplyRoadEconomics(candidate, economics, realDistance);
    candidate.road100SiteFirst <- true;
    candidate.road100MailIntertown <- true;
    if (mailLong) candidate.road100MailLongExisting <- true;
    candidate.road100SiteMonthly <- marginal;
    candidate.road100GenSiteA <- plan.stopA.tile;
    candidate.road100GenSiteB <- plan.stopB.tile;
    candidate.road100GenDepot <- plan.depot.tile;
    candidate.road100GenRoute <- plan.routeDistance;
    candidate.immobilise = economics.immobilise;
    out.append(candidate);
    admitted++;
    if (DECISION_LOG) OpexDecide("ROAD100_MAIL",
        "phase=admit srcTown=" + pair.from.id + " dstTown=" + pair.to.id
        + " source_monthly=" + marginal + " accept=" + plan.stopB.value
        + " distance=" + realDistance + " route=" + plan.routeDistance
        + " existing_long=" + (mailLong ? 1 : 0)
        + " profit=" + economics.profitAnnual + " vehicles=" + economics.trains);
  }
  if (DECISION_LOG) OpexDecide("ROAD100_MAIL",
      "phase=summary towns=" + towns.len() + " pairs=" + pairs.len()
      + " tested=" + tested + " admitted=" + admitted + " no_plan=" + noPlan
      + " no_profit=" + noProfit + " ops=" + OpexOpsMeasureEnd(mark));
}

function OpexBuildRoadCandidates(catalog, budget, lines, abandonedPairs = null, profile = null, freightCargo = null, targetKind = null, targetId = -1, v276Pair = false)
{
  if (V276_CAND_SLICES > 0 && !v276Pair) {
    OpexV276Request(catalog, targetKind, targetId);
    if (V276_CATALOG_TASK != null && ("v276Road" in V276_CATALOG_TASK))
      return OpexV276CopyResult(V276_CATALOG_TASK.v276Road);
    return OpexProjectEmptyRoad();
  }
  local all = [];
  local stats = {
    pairsInBand = 0, noMonthly = 0, noEngine = 0, townRejected = 0, townAcceptancePrefiltered = 0,
    economicsUnavailable = 0, profitTooLow = 0, profitNonPositive = 0,
    profitBelowFloorKept = 0, accepted = 0,
    /* C43/E3 famille 2 : ROAD_MIN_DISTANCE/ROAD_MAX_DISTANCE mordent-elles ? */
    roadDistanceShort = 0, roadDistanceLong = 0,
  };
  if (catalog.roadType < 0 || (catalog.roadEngineByCargo != null && catalog.roadEngineByCargo.len() == 0)) return { all = 0, candidates = [], best = [], stats = stats, opcodes = 0, profile = profile };

  budget.begin();
  /* Les marques C41.17 internes ne doivent jamais etre imbriquees dans une mesure globale :
   * un suspend peut sinon faire compter le tick-frontiere deux fois. C41.16 porte deja le total
   * fret de reference ; C41.17 ne publie que ses intervalles disjoints. */
  local freightMark = (profile != null && !C41_ROAD_FREIGHT_PROFILE && !C41_ROAD_FREIGHT_TOWN_PROFILE)
      ? OpexOpsMeasureBegin() : null;
  if (ROAD1Y_DIST_BANDS && targetKind == null && targetId < 0) {
    /* ROAD1Y : bandes longues d'abord ; la premiere bande non vide l'emporte. */
    try {
      for (local band = 0; band < ROAD1Y_DIST_BAND_LIMITS.len(); band++) {
        local before = all.len();
        ROAD1Y_DIST_BAND = band;
        OpexRoadFreightCandidates(catalog, lines, all, stats, abandonedPairs, profile, freightCargo,
                                  targetKind, targetId);
        ROAD1Y_DIST_BAND = -1;
        if (all.len() > before) break;
      }
    } catch (e) {
      ROAD1Y_DIST_BAND = -1;
      throw e;
    }
  } else {
    ROAD1Y_DIST_BAND = -1;
    OpexRoadFreightCandidates(catalog, lines, all, stats, abandonedPairs, profile, freightCargo,
                              targetKind, targetId);
  }
  if (ROAD100_SOLO_PAX)
    OpexRoad100SoloPaxCandidates(catalog, lines, all, stats, abandonedPairs, targetKind, targetId);
  if (ROAD100_TOWN_BUS)
    OpexRoad100TownBusCandidates(catalog, lines, all, stats, abandonedPairs, targetKind, targetId);
  if (ROAD100_MAIL_INTERTOWN) {
    local mailIterator = OpexRoad100MailIntertownGenerator(
        catalog, lines, all, stats, abandonedPairs, targetKind, targetId);
    while (mailIterator.getstatus() != "dead") resume mailIterator;
  }
  /* ROAD100-29 : diagnostics seulement. Aucun ajout dans `all`, donc TopK,
   * classement, projet et chantier restent exactement ceux d'avant. */
  if (ROAD100_PAX_INTERCITY_ROOTS && targetKind == null) {
    local rootsIterator = OpexRoad100PaxRootsShadowGenerator(catalog);
    while (rootsIterator.getstatus() != "dead") resume rootsIterator;
  }
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
  if (MULTI1_ROAD_CARGO_SHADOW == 1 && targetKind == null && targetId < 0)
    OpexMulti1RoadCargoShadowArm(catalog, lines, abandonedPairs, freightCargo, all);
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
      if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(sub.srcId, srcTile)) continue;
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
    if (DIST_BORNES_UNIFIED) {
      if (!OpexDistBornesAllows(OpexDistBornesWindow(roadBounds, "road"), distance)) continue;
    } else if (distance < roadBounds.roadMin || distance > maxDist) continue;

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
