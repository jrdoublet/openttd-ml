/* Module AIR extrait de builder_air.nut (R11) : modele de trajet, cadence et capacites des aeroports. */
/* C100.1 : cout de manoeuvre faible charge, isole du helper historique
 * OpexAirManeuverDays utilise aussi par le decoupage modal.
 *
 * OpenTTD 15.3 limite le roulage a SPEED_LIMIT_TAXI=50. La limite est
 * multipliee par vehicle.plane_speed dans UpdateAircraftSpeed puis le
 * deplacement est redivise par ce meme facteur : cote NoAI, l'equivalent est
 * donc 50, sans nouveau / plane_speed.
 *
 * Le proxy W+H historique compte tout le demi-perimetre des deux emprises.
 * La FTA AT_LARGE 6x6 n'en parcourt qu'environ 2/3 sur un aller complet
 * (taxi terminal->piste + sortie de piste->terminal). Ce facteur ramene le
 * socle AT_LARGE a ~15 j, coherent avec la sonde timetable faible charge,
 * tout en restant fonction de la geometrie de l'aeroport et non d'un EngineID. */
function OpexC100AirManeuverDays(engineId, srcType, dstType)
{
  local maxSpeed = AIEngine.GetMaxSpeed(engineId).tofloat();
  if (maxSpeed < 1.0) maxSpeed = 1.0;
  local taxiSpeed = maxSpeed < 50.0 ? maxSpeed : 50.0;
  local groundTiles = 8.0;
  if (srcType != null && dstType != null && AIAirport.IsValidAirportType(srcType)
      && AIAirport.IsValidAirportType(dstType)) {
    groundTiles = (AIAirport.GetAirportWidth(srcType) + AIAirport.GetAirportHeight(srcType)
                   + AIAirport.GetAirportWidth(dstType) + AIAirport.GetAirportHeight(dstType)).tofloat();
    groundTiles = groundTiles * 2.0 / 3.0;
  }
  local ticksPerDay = OpexTicksPerDay(null);
  local taxiDays = groundTiles * OpexDaysPerTile(taxiSpeed, ticksPerDay);
  local verticalDays = 300.0 / ticksPerDay;
  return taxiDays + verticalDays;
}

/* Modele unique de temps de vol pour l'economie et le plafond de demande.
 * C100 isole uniquement la cinematique AIR : vitesse NoAI directe + manoeuvres
 * physiques deja utilisees par le decoupage modal. Le chargement reste separe
 * et n'est volontairement PAS introduit dans ce premier bras causal. */
function OpexAirTripModel(speed, capacity, distance, engineId = -1, airportType = -1,
                          forcePhysicalTiming = false, forceC100RankReplay = false)
{
  /* Timing physique (vitesse NoAI directe + manoeuvres) : seulement sur demande
   * explicite des sondes. Au defaut, vitesse historique /4. */
  local physicalTiming = forcePhysicalTiming;
  /* C114 reproduit la cellule historique complete du premier C100 : meme
   * vitesse NoAI directe, mais ancien helper OpexAirManeuverDays partout dans
   * l'economie AIR. C103/C104 gardent le meme replay local via force*. */
  local c100ReplayTiming = forceC100RankReplay;
  local directSpeed = physicalTiming || c100ReplayTiming;
  local effectiveSpeed = directSpeed
      ? speed.tofloat() : speed / 4.0;
  if (effectiveSpeed < 1.0) effectiveSpeed = 1.0;
  local flightDays = distance.tofloat() / (0.036 * effectiveSpeed);
  local airportDelayDays = 3.0;
  if (c100ReplayTiming && engineId >= 0 && airportType >= 0
      && AIEngine.IsValidEngine(engineId) && AIAirport.IsValidAirportType(airportType)) {
    /* C103 reproduit EXACTEMENT le regularisateur implicite du premier C100 :
     * vitesse API directe, mais helper de manoeuvre historique. Ce temps n'est
     * pas presente comme physique et ne quitte jamais le chooser C103. */
    airportDelayDays = OpexAirManeuverDays(engineId, airportType, airportType,
        OpexTicksPerDay(null), OpexPlaneSpeedDivisor());
  } else if (physicalTiming && engineId >= 0 && airportType >= 0
      && AIEngine.IsValidEngine(engineId) && AIAirport.IsValidAirportType(airportType)) {
    airportDelayDays = OpexC100AirManeuverDays(engineId, airportType, airportType);
  }
  local oneWayDays = flightDays + airportDelayDays;
  if (oneWayDays < 1.0) oneWayDays = 1.0;
  local roundTripDays = 2.0 * oneWayDays;
  local tripsPerMonth = OpexEstimMonthDays(30.4) / oneWayDays;
  return {
    effectiveSpeed = effectiveSpeed, flightDays = flightDays,
    airportDelayDays = airportDelayDays, oneWayDays = oneWayDays,
    roundTripDays = roundTripDays, tripsPerMonth = tripsPerMonth,
    capacityPerPlane = capacity * tripsPerMonth,
  };
}

/* Compte les lignes aeriennes vivantes qui touchent CET aeroport. Les champs stationA/B sont
 * des TUILES : chaque comparaison passe donc par GetStationID, comme le controle des hubs de
 * batch dans main.nut. */
function OpexAirLiveRoutesAtAirport(airportTile, lines)
{
  if (airportTile == null || !AIMap.IsValidTile(airportTile) || lines == null) return 0;
  local station = AIStation.GetStationID(airportTile);
  if (!AIStation.IsValidStation(station)) return 0;
  local routes = 0;
  foreach (other in lines) {
    if (!("mode" in other) || other.mode != "air") continue;
    local live = false;
    if (("vehicles" in other) && other.vehicles != null) {
      foreach (v in other.vehicles) {
        if (AIVehicle.IsValidVehicle(v)) { live = true; break; }
      }
    } else if (("vehicle" in other) && AIVehicle.IsValidVehicle(other.vehicle)) {
      live = true;
    }
    if (!live) continue;
    local otherA = ("stationA" in other) ? OpexAirLineStationId(other, 0) : -1;
    local otherB = ("stationB" in other) ? OpexAirLineStationId(other, 1) : -1;
    if (otherA == station || otherB == station) routes++;
  }
  return routes;
}

/* C16 : Creneau physique d'absorption de la piste (en jours par atterrissage).
 * Tire du modele de cadence d'AAAHogEx (air.nut:10-75). */
function OpexAirportStationDateSpan(airportType)
{
  switch (airportType) {
    case AIAirport.AT_SMALL: return 20;
    case AIAirport.AT_COMMUTER: return 16;
    case AIAirport.AT_LARGE: return 10;
    case AIAirport.AT_METROPOLITAN: return 8;
    case AIAirport.AT_INTERNATIONAL: return 5;
    case AIAirport.AT_INTERCON: return 4;
    default: return 12;
  }
}

/* V160 : Construit une table StationID -> nombre de lignes air vivantes qui la desservent.
 * Prédicat strictement identique à OpexAirLiveRoutesAtAirport.
 * Une ligne reliant la même station aux deux bouts ne compte qu'une seule fois. */
function OpexAirBuildRoutesIndex(lines)
{
  local index = {};
  if (lines == null) return index;
  foreach (other in lines) {
    if (!("mode" in other) || other.mode != "air") continue;
    local live = false;
    if (("vehicles" in other) && other.vehicles != null) {
      foreach (v in other.vehicles) {
        if (AIVehicle.IsValidVehicle(v)) { live = true; break; }
      }
    } else if (("vehicle" in other) && AIVehicle.IsValidVehicle(other.vehicle)) {
      live = true;
    }
    if (!live) continue;
    local otherA = ("stationA" in other) ? OpexAirLineStationId(other, 0) : -1;
    local otherB = ("stationB" in other) ? OpexAirLineStationId(other, 1) : -1;
    local validA = AIStation.IsValidStation(otherA);
    local validB = AIStation.IsValidStation(otherB);
    if (validA) {
      if (otherA in index) index[otherA]++;
      else index.rawset(otherA, 1);
    }
    if (validB && (!validA || otherB != otherA)) {
      if (otherB in index) index[otherB]++;
      else index.rawset(otherB, 1);
    }
  }
  return index;
}

/* C16 : Plafond physique de flotte aerienne derive de la CADENCE et non de la demande (docs/taches.md C16).
 * Calcule le nombre maximal d'avions qui peuvent tourner sur la ligne sans creer d'embouteillage
 * dans le ciel (holding pattern), compte tenu de la rotation aller-retour et du partage de piste. */
function OpexAirCadenceCap(line, catalog, lines, routesIndex = null)
{
  local speed = (("plane" in catalog) && catalog.plane != null) ? catalog.plane.speed : 1;
  local capacity = ("planeCapacity" in line) ? line.planeCapacity : 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      speed = AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v));
      if (capacity <= 0) capacity = AIVehicle.GetCapacity(v, line.cargo);
      break;
    }
  } else if (("vehicle" in line) && AIVehicle.IsValidVehicle(line.vehicle)) {
    speed = AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(line.vehicle));
    if (capacity <= 0) capacity = AIVehicle.GetCapacity(line.vehicle, line.cargo);
  }
  if (capacity <= 0 && ("plane" in catalog) && catalog.plane != null) {
    capacity = catalog.plane.capacity;
  }
  local distance = OpexFlightDistance(line.stationA, line.stationB);
  local trip = OpexAirTripModel(speed, capacity, distance);
  local roundTripDays = trip.roundTripDays;

  local routesA = (routesIndex != null) ? OpexAirRoutesIndexAt(line.stationA, routesIndex)
      : OpexAirLiveRoutesAtAirport(line.stationA, lines);
  local routesB = (routesIndex != null) ? OpexAirRoutesIndexAt(line.stationB, routesIndex)
      : OpexAirLiveRoutesAtAirport(line.stationB, lines);
  if (routesA < 1) routesA = 1;
  if (routesB < 1) routesB = 1;

  local typeA = (line.stationA != null && AIAirport.IsAirportTile(line.stationA))
      ? AIAirport.GetAirportType(line.stationA) : AIAirport.AT_SMALL;
  local typeB = (line.stationB != null && AIAirport.IsAirportTile(line.stationB))
      ? AIAirport.GetAirportType(line.stationB) : AIAirport.AT_SMALL;
  local spanA = OpexAirportStationDateSpan(typeA) * routesA;
  local spanB = OpexAirportStationDateSpan(typeB) * routesB;
  local effectiveSpan = (spanA > spanB) ? spanA : spanB;
  if (effectiveSpan < 1) effectiveSpan = 1;

  local cap = (roundTripDays / effectiveSpan.tofloat()).tointeger() + 1;
  if (cap < 1) cap = 1;
  if (cap > AIR_MAX_PLANES_PER_ROUTE) cap = AIR_MAX_PLANES_PER_ROUTE;
  return cap;
}

/* V160 : Variante indexee de OpexAirCadenceCap. routesIndex est une table StationID -> count
 * construite par OpexAirBuildRoutesIndex ; null retombe sur le comptage direct. */
function OpexAirCadenceCapIndexed(line, catalog, lines, routesIndex)
{
  return OpexAirCadenceCap(line, catalog, lines, routesIndex);
}

function OpexAirRoutesIndexAt(airportTile, routesIndex)
{
  if (airportTile == null || !AIMap.IsValidTile(airportTile)) return 0;
  local station = AIStation.GetStationID(airportTile);
  if (!AIStation.IsValidStation(station) || !(station in routesIndex)) return 0;
  return routesIndex[station];
}

function OpexAirAirportAcceptsPlane(airportType, planeType)
{
  if (planeType == AIAirport.PT_SMALL_PLANE) return true;
  return airportType != AIAirport.AT_SMALL && airportType != AIAirport.AT_COMMUTER;
}

/* V86 Variante B : plafond de routes autorisees par type d'aeroport.
 * AIR_HUB_MAX_ROUTES vaut N = 3 (ancien reglage air_hub_max_routes, retire en V236), le plafond devient min(plafond actuel, N). */
function OpexAirAirportMaxRoutes(airportType)
{
  local defaultCap = (airportType == AIAirport.AT_SMALL || airportType == AIAirport.AT_COMMUTER) ? 4 : 12;
  if (AIR_HUB_MAX_ROUTES > 0) {
    return AIR_HUB_MAX_ROUTES < defaultCap ? AIR_HUB_MAX_ROUTES : defaultCap;
  }
  return defaultCap;
}
