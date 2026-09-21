/* Etage 3b : une liaison aerienne passagers, sans pathfinding.
 *
 * L'avion est le contrepoint du rail : il n'y a pas de recherche A*, mais les aires de
 * construction et la compatibilite aeroport/appareil sont des preconditions reelles.
 * Regle : 2 types principaux d'avions et d'aeroports (les gros et les petits).
 * Les gros avions ne vont QUE dans les grands aeroports.
 * La construction elle-meme est transactionnelle : avion vendu, puis aeroports
 * retires, au moindre echec apres le premier aeroport.
 */

AIR_TOWN_POOL <- 24;
AIR_HUB_TOWN_POOL <- 24;
AIR_HUB_NEW_SITE_POOL <- 12;
AIR_SITE_RADIUS <- 25;
AIR_TOWN_MIN_DISTANCE <- 32;
AIR_MAX_SITE_PROBES <- 1500;
AIR_MAX_PLANES_PER_ROUTE <- 16;
AIR_PLAN_DIAG_SEQ <- 0;
/* Plafond de distance aerienne (0 = illimite, docs/taches.md C6 supprime) */
AIR_MAX_DISTANCE <- 0;
/* Cache de sites d'aeroport par ville et type d'aeroport (C33.1) */
AIR_SITE_CACHE_ENABLED <- true;
AIR_SITE_CACHE <- {};
/* C36.3 : Filtre d'emprise sans AITestMode avant la sonde (defaut 1, banc 20x10). */
AIR_CHEAP_SITE <- true;
/* C33.2 : Arrets de bus joints au chantier aeroport */
AIR_JOINED_STOPS <- false;

function OpexAirResetSiteCache()
{
  AIR_SITE_CACHE.clear();
}

/* Un test de site n'est qu'une prediction : si le chantier reel le contredit, ne jamais
 * re-servir exactement cette ancre au prochain rafraichissement. On efface seulement l'entree
 * qui pointe encore vers l'ancre refusee (un autre calcul peut deja l'avoir remplacee), afin de
 * forcer la recherche d'une alternative dans cette meme ville et pour ce meme type d'aeroport. */
function OpexAirInvalidateCachedSite(site, airport)
{
  if (!AIR_SITE_CACHE_ENABLED || site == null) return;
  local key = site.town.id + "_" + airport.type;
  if (key in AIR_SITE_CACHE && AIR_SITE_CACHE[key] == site.anchor) delete AIR_SITE_CACHE[key];
}

/* Distance euclidienne exacte à vol d'oiseau pour la cinématique et le paiement aérien :
 * sqrt(dx^2 + dy^2) approximé par 0.414 * min(dx, dy) + max(dx, dy) */
function OpexFlightDistance(tileA, tileB)
{
  local dx = abs(AIMap.GetTileX(tileA) - AIMap.GetTileX(tileB));
  local dy = abs(AIMap.GetTileY(tileA) - AIMap.GetTileY(tileB));
  local minD = dx < dy ? dx : dy;
  local maxD = dx > dy ? dx : dy;
  local dist = (minD * 414) / 1000 + maxD;
  return dist > 0 ? dist : 1;
}

/* Distance Manhattan d'une tuile au rectangle [anchor, anchor + width/height - 1]. */
function OpexAirDistanceToRect(tile, anchor, width, height)
{
  local x = AIMap.GetTileX(tile);
  local y = AIMap.GetTileY(tile);
  local left = AIMap.GetTileX(anchor);
  local top = AIMap.GetTileY(anchor);
  local right = left + width - 1;
  local bottom = top + height - 1;
  local dx = x < left ? left - x : (x > right ? x - right : 0);
  local dy = y < top ? top - y : (y > bottom ? y - bottom : 0);
  return dx + dy;
}

/* B9/G4 : toutes les demandes AIR sont exprimees en production mensuelle de
 * cargo couverte. Pour un site neuf, l'emprise et le type d'aeroport sont deja
 * connus avant construction, donc cette grandeur est mesurable sans proxy de
 * population. */
function OpexAirAirportCatchmentProduction(airportTile, airportType, cargo)
{
  if (!AIMap.IsValidTile(airportTile) || cargo < 0
      || !AIAirport.IsValidAirportType(airportType)) return 0;
  local w = AIAirport.GetAirportWidth(airportType);
  local h = AIAirport.GetAirportHeight(airportType);
  local radius = AIAirport.GetAirportCoverageRadius(airportType);
  return AITile.GetCargoProduction(airportTile, cargo, w, h, radius);
}

/* Production de l'union reelle d'une station, pieces jointes comprises.
 * Chaque tuile est comptee une fois par AITileList_StationCoverage. */
function OpexAirStationCatchmentProduction(stationId, cargo)
{
  if (!AIStation.IsValidStation(stationId) || cargo < 0) return 0;
  local total = 0;
  local coverageTiles = AITileList_StationCoverage(stationId);
  foreach (coverageTile, value in coverageTiles) {
    total += AITile.GetCargoProduction(coverageTile, cargo, 1, 1, 0);
  }
  return total;
}

function OpexAirJoinedMarginalProduction(stationId, airportTile, airportType, cargo)
{
  local unionProduction = OpexAirStationCatchmentProduction(stationId, cargo);
  local airportProduction = OpexAirAirportCatchmentProduction(airportTile, airportType, cargo);
  local marginal = unionProduction - airportProduction;
  return marginal > 0 ? marginal : 0;
}

function OpexAirCatchmentProbeEndpoint(catalog, stationId, airportTile, townId,
                                      rawJoinedPax, modelJoinedPax, reused, endpoint)
{
  if (!AIR_CATCHMENT_PROBE) return 0;
  if (!AIStation.IsValidStation(stationId) || !AIAirport.IsAirportTile(airportTile)
      || !AITown.IsValidTown(townId)) return 0;
  local t0 = AIController.GetTick();
  local l0 = AIController.GetOpsTillSuspend();
  local airportType = AIAirport.GetAirportType(airportTile);
  local w = AIAirport.GetAirportWidth(airportType);
  local h = AIAirport.GetAirportHeight(airportType);
  local airportRadius = AIAirport.GetAirportCoverageRadius(airportType);
  local townTile = AITown.GetLocation(townId);
  local airportPax = AITile.GetCargoProduction(airportTile, catalog.paxCargo, w, h, airportRadius);
  local airportMail = 0;
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    airportMail = AITile.GetCargoProduction(airportTile, catalog.mailCargo, w, h, airportRadius);
  }
  local unionPax = 0;
  local unionMail = 0;
  local unionTiles = 0;
  local townCenterInUnion = false;
  local coverageTiles = AITileList_StationCoverage(stationId);
  foreach (coverageTile, value in coverageTiles) {
    unionTiles++;
    if (coverageTile == townTile) townCenterInUnion = true;
    unionPax += AITile.GetCargoProduction(coverageTile, catalog.paxCargo, 1, 1, 0);
    if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
      unionMail += AITile.GetCargoProduction(coverageTile, catalog.mailCargo, 1, 1, 0);
    }
  }
  local marginalPax = unionPax - airportPax;
  if (marginalPax < 0) marginalPax = 0;
  local marginalMail = unionMail - airportMail;
  if (marginalMail < 0) marginalMail = 0;
  local rawMinusTrue = reused ? 0 : rawJoinedPax - marginalPax;
  local modelMinusTrue = reused ? 0 : modelJoinedPax - marginalPax;
  local rectDistance = OpexAirDistanceToRect(townTile, airportTile, w, h);
  local airportCenter = airportTile + AIMap.GetTileIndex(w / 2, h / 2);
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - t0;
  local probeOps = elapsed <= 0
      ? l0 - left
      : l0 + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
  OpexAirCatchmentLog("AIR_CATCHMENT_ENDPOINT",
      "endpoint=" + endpoint + " station=" + stationId + " town=" + townId
      + " town_tile=" + townTile + " town_pop=" + AITown.GetPopulation(townId)
      + " airport_tile=" + airportTile + " airport_type=" + airportType
      + " airport_w=" + w + " airport_h=" + h + " airport_radius=" + airportRadius
      + " airport_generic_radius=" + AIStation.GetCoverageRadius(AIStation.STATION_AIRPORT)
      + " bus_radius=" + AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP)
      + " rect_distance=" + rectDistance
      + " center_distance=" + AIMap.DistanceManhattan(townTile, airportCenter)
      + " town_center_airport=" + (rectDistance <= airportRadius ? 1 : 0)
      + " town_center_union=" + (townCenterInUnion ? 1 : 0)
      + " coverage_tiles=" + unionTiles
      + " airport_pax_prod=" + airportPax + " union_pax_prod=" + unionPax
      + " joined_marginal_pax=" + marginalPax
      + " model_joined_pax=" + modelJoinedPax + " raw_joined_pax=" + rawJoinedPax
      + " overlap_overcount_pax=" + (rawMinusTrue > 0 ? rawMinusTrue : 0)
      + " raw_undercount_pax=" + (rawMinusTrue < 0 ? -rawMinusTrue : 0)
      + " model_error_pax=" + modelMinusTrue
      + " airport_mail_prod=" + airportMail + " union_mail_prod=" + unionMail
      + " joined_marginal_mail=" + marginalMail
      + " reused=" + (reused ? 1 : 0) + " probe_ops=" + probeOps);
  return probeOps;
}

/* Les plus grosses villes, sans trier le catalogue lui-meme. L'insertion est deterministe et
 * garde l'ordre d'enumeration d'OpenTTD en cas d'egalite de population. */
function OpexAirSortedTowns(towns)
{
  local out = [];
  foreach (town in towns) {
    local pos = out.len();
    while (pos > 0 && out[pos - 1].pop < town.pop) pos--;
    out.insert(pos, town);
  }
  return out;
}

function OpexAirTownServed(town, lines, diag = null)
{
  /* Keep the non-diagnostic path byte-for-byte equivalent in its tests and short-circuiting. */
  if (!DECISION_LOG || diag == null) {
    if (lines == null) return false;
    foreach (line in lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      if (AIMap.DistanceManhattan(town.tile, line.originA) < 15) return true;
      if (AIMap.DistanceManhattan(town.tile, line.originB) < 15) return true;
    }
    return false;
  }

  if (lines == null) {
    diag.nullCalls++;
    diag.falseCalls++;
    if (DECISION_LOG && !diag.noAirLogged) {
      diag.noAirLogged = true;
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=null line_count=0"
                 + " air_line_count=0 verdict=0 comparisons=none");
    }
    return false;
  }
  if (lines.len() == 0) diag.emptyCalls++;
  else diag.nonemptyCalls++;

  local comparisons = "";
  local airLineCount = 0;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    local distanceA = AIMap.DistanceManhattan(town.tile, line.originA);
    if (distanceA < 15) {
      diag.trueCalls++;
      return true;
    }
    local distanceB = AIMap.DistanceManhattan(town.tile, line.originB);
    if (distanceB < 15) {
      diag.trueCalls++;
      return true;
    }
    comparisons += " line" + airLineCount
        + "_id=" + (("lineId" in line) ? line.lineId : "none")
        + " line" + airLineCount + "_originA=" + line.originA
        + " line" + airLineCount + "_originB=" + line.originB
        + " line" + airLineCount + "_distA=" + distanceA
        + " line" + airLineCount + "_distB=" + distanceB;
    airLineCount++;
  }
  diag.falseCalls++;
  if (airLineCount == 0 && !diag.noAirLogged) {
    diag.noAirLogged = true;
    if (DECISION_LOG) {
      local linesState = lines.len() == 0 ? "empty" : "nonempty";
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=" + linesState
                 + " line_count=" + lines.len()
                 + " air_line_count=0 verdict=0 comparisons=none");
    }
  }
  /* One record per failed town per OpexAirPlans invocation: repeated combo/site scans compare
   * the same immutable town and lines, so suppressing duplicates loses no comparison. */
  if (airLineCount > 0 && !(town.id in diag.loggedFalseTowns)) {
    diag.loggedFalseTowns[town.id] <- true;
    diag.loggedFalseCount++;
    if (DECISION_LOG) {
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=nonempty line_count=" + lines.len()
                 + " air_line_count=" + airLineCount + " verdict=0" + comparisons);
    }
  }
  return false;
}

/* 🔴 Une ligne aerienne stocke des TUILES d'aeroport dans stationA/stationB, malgre leur nom :
 * OpexBuildAirRoute calcule bien les StationID (`:831-832`) puis rend `result.stationA = airportA`,
 * la tuile. main.nut lit ces champs comme des tuiles partout (`GetStationID(line.stationA)` en
 * :1046, :1319, :2034) -- la convention "tuile" est donc la bonne. Seul le code de hub ci-dessous
 * les prenait pour des StationID deja resolus, avec trois consequences mesurees le 2026-09-03 :
 *   1. la garde `alreadyConnected` comparait un StationID a une tuile : TOUJOURS fausse, d'ou
 *      NEUF liaisons sur la meme paire de villes (graine 42, 1970-1972) ;
 *   2. la decouverte de hub testait `IsAirportTile()` sur un CENTRE-VILLE : toujours fausse, donc
 *      tous les aeroports tombaient dans le repli "orphelins" avec `routes = 0` code en dur ;
 *   3. `routes = 0` rendait le plafond `maxRoutes` inoperant ET annulait la decote de saturation
 *      `hubMonthly / (routes + 1)`, qui divisait donc toujours par 1.
 * Resoudre la tuile en StationID repare les trois d'un coup. */
function OpexAirLineStationId(line, which)
{
  local tile = (which == 0) ? line.stationA : line.stationB;
  if (tile == null || !AIMap.IsValidTile(tile)) return -1;
  return AIStation.GetStationID(tile);
}

/* Modele unique de temps de vol pour l'economie et le plafond de demande. */
function OpexAirTripModel(speed, capacity, distance)
{
  local effectiveSpeed = speed / 4.0;
  if (effectiveSpeed < 1.0) effectiveSpeed = 1.0;
  local flightDays = distance.tofloat() / (0.036 * effectiveSpeed);
  local airportDelayDays = 3.0;
  local oneWayDays = flightDays + airportDelayDays;
  if (oneWayDays < 1.0) oneWayDays = 1.0;
  local roundTripDays = 2.0 * oneWayDays;
  local tripsPerMonth = 30.4 / oneWayDays;
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

/* C16 : Plafond physique de flotte aerienne derive de la CADENCE et non de la demande (docs/taches.md C16).
 * Calcule le nombre maximal d'avions qui peuvent tourner sur la ligne sans creer d'embouteillage
 * dans le ciel (holding pattern), compte tenu de la rotation aller-retour et du partage de piste. */
function OpexAirCadenceCap(line, catalog, lines)
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

  local routesA = OpexAirLiveRoutesAtAirport(line.stationA, lines);
  local routesB = OpexAirLiveRoutesAtAirport(line.stationB, lines);
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

function OpexAirAirportAcceptsPlane(airportType, planeType)
{
  if (planeType == AIAirport.PT_SMALL_PLANE) return true;
  return airportType != AIAirport.AT_SMALL && airportType != AIAirport.AT_COMMUTER;
}

/* C36.3 : l'emprise est-elle constructible SANS AITestMode ni LevelTiles ?
 * IsBuildableRectangle accepte Clear + Trees (BuildAirport les rase) et le cote, et refuse
 * maisons, industries, rail, mer, riviere. Le cote passe IsBuildable : on l'exclut a part,
 * avec mer/canal/riviere, sur CHAQUE tuile -- pas seulement les deux coins. C4 (span >= 2)
 * reste. Un hit ici n'est pas encore un site : OpexAirFindSite confirme en une sonde. */
function OpexAirFootprintCheapOk(anchor, airport)
{
  local w = airport.width;
  local h = airport.height;
  if (!AITile.IsBuildableRectangle(anchor, w, h)) return false;
  local minH = AITile.GetMinHeight(anchor);
  local maxH = AITile.GetMaxHeight(anchor);
  local offX = w - 1;
  local offY = h - 1;
  for (local tx = 0; tx <= offX; tx++) {
    for (local ty = 0; ty <= offY; ty++) {
      local t = anchor + AIMap.GetTileIndex(tx, ty);
      if (!AIMap.IsValidTile(t)) return false;
      if (AITile.IsWaterTile(t) || AITile.IsCoastTile(t) || AITile.IsRiverTile(t)) return false;
      local tMin = AITile.GetMinHeight(t);
      local tMax = AITile.GetMaxHeight(t);
      if (tMin < minH) minH = tMin;
      if (tMax > maxH) maxH = tMax;
      if (maxH - minH >= 2) return false;
    }
  }
  return true;
}

function OpexAirFootprintEnd(anchor, airport)
{
  /* AITile.LevelTiles prend le coin terminal de TERRASSEMENT, pas la derniere
   * tuile de l'aeroport. Pour une emprise w x h il est donc a +(w,h) :
   * SuperLib.Tile.CostToFlattern et AAAHogEx::AirStation.Build emploient tous
   * deux cette convention. L'ancienne borne +(w-1,h-1) laissait la rangee et
   * la colonne finales en pente, puis BuildAirport echouait ERR_FLAT_LAND_REQUIRED
   * bien que notre sonde ait annonce le site nivelable. */
  return anchor + AIMap.GetTileIndex(airport.width, airport.height);
}

function OpexAirFootprintIsFlat(anchor, airport)
{
  /* CheckFlatLandAirport compare le z du coin haut de chaque tuile (allowed_z), pas l'absence
   * de pente : min==max par tuile est plus dur que le moteur. */
  local z = AITile.GetMaxHeight(anchor);
  local offX = airport.width - 1;
  local offY = airport.height - 1;
  for (local tx = 0; tx <= offX; tx++) {
    for (local ty = 0; ty <= offY; ty++) {
      local t = anchor + AIMap.GetTileIndex(tx, ty);
      if (!AIMap.IsValidTile(t)) return false;
      if (AITile.GetMaxHeight(t) != z) return false;
    }
  }
  return true;
}

/* G7§2 : Sonde AITestMode de nivelabilite, sans modifier la carte ni depenser de tresorerie.
 * Retourne true si LevelTiles REUSSIRAIT (terrain deja plat, ou nivelable, ou autorisation
 * achetable). Utilise par OpexAirFindSite pendant la generation, avant election. */
function OpexAirCanLevelFootprint(anchor, airport, townId = -1)
{
  local end = OpexAirFootprintEnd(anchor, airport);
  if (!AIMap.IsValidTile(end)) return false;
  if (OpexAirFootprintIsFlat(anchor, airport)) return true;
  local probe = AITestMode();
  if (AITile.LevelTiles(anchor, end)) return true;
  local err = AIError.GetLastError();
  if (err == AITile.ERR_AREA_ALREADY_FLAT) return true;
  /* L'autorite locale refuse mais un boost arbre le resoudrait au moment de construire. */
  if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES && townId >= 0) return true;
  return false;
}

/* Nivellement REEL (pas AITestMode) de l'emprise exacte, puis verification min=max.
 * LevelTiles en test ne change pas la carte ; BuildAirport ne terrasse pas. */
function OpexAirLevelFootprint(anchor, airport, townId = -1)
{
  local end = OpexAirFootprintEnd(anchor, airport);
  if (!AIMap.IsValidTile(end)) return false;
  if (OpexAirFootprintIsFlat(anchor, airport)) return true;
  if (!AITile.LevelTiles(anchor, end)) {
    local err = AIError.GetLastError();
    if (err == AITile.ERR_AREA_ALREADY_FLAT) return OpexAirFootprintIsFlat(anchor, airport);
    if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES && townId >= 0) {
      OpexBoostTownRating(townId, 800, 40);
      if (!AITile.LevelTiles(anchor, end)) return false;
    } else {
      return false;
    }
  }
  return OpexAirFootprintIsFlat(anchor, airport);
}

/* Trouve la premiere ancre constructible, par couronnes autour de la ville. L'ancre est bien le
 * coin haut-gauche attendu par BuildAirport. La couverture est testee contre le rectangle entier,
 * pas seulement contre son coin. */
function OpexAirFindSite(town, airport, probes)
{
  if (C60_TOWN_RATING_PROBE) {
    OpexC60ObserveTownRating("air", "find_site", town.id);
  }
  if (C60_TOWN_RATING_FILTER && OpexTownRatingHopeless(town.id)) {
    return null;
  }
  local key = town.id + "_" + airport.type;
  if (AIR_SITE_CACHE_ENABLED && (key in AIR_SITE_CACHE)) {
    local cachedAnchor = AIR_SITE_CACHE[key];
    if (cachedAnchor == null) {
      return null;
    }
    local offX = airport.width - 1;
    local offY = airport.height - 1;
    local mapX = AIMap.GetMapSizeX();
    local mapY = AIMap.GetMapSizeY();
    local ax = AIMap.GetTileX(cachedAnchor);
    local ay = AIMap.GetTileY(cachedAnchor);
    if (ax + offX < mapX && ay + offY < mapY) {
      local c4 = cachedAnchor + AIMap.GetTileIndex(offX, offY);
      if (!AITile.IsWaterTile(cachedAnchor) && !AITile.IsCoastTile(cachedAnchor) &&
          !AITile.IsWaterTile(c4) && !AITile.IsCoastTile(c4) &&
          AIAirport.GetNearestTown(cachedAnchor, airport.type) == town.id &&
          (!AIR_CHEAP_SITE || OpexAirFootprintCheapOk(cachedAnchor, airport))) {
        local ok = false;
        if (AIR_CHEAP_SITE) {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(cachedAnchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       OpexAirCanLevelFootprint(cachedAnchor, airport, town.id)) {
              /* G7§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              ok = true;
            }
          }
        } else {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          if (!ok) {
            local err = AIError.GetLastError();
            if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(cachedAnchor, c4);
              ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
              if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
            }
          }
        }
        if ("tested" in probes) probes.tested++;
        if (ok) return { town = town, anchor = cachedAnchor };
      }
    }
    delete AIR_SITE_CACHE[key];
  }

  local allowance = 120;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local anchor = town.tile + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(anchor)) continue;
        local ax = AIMap.GetTileX(anchor);
        local ay = AIMap.GetTileY(anchor);
        if (ax + offX >= mapX || ay + offY >= mapY) continue;
        if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
        if (AITile.IsWaterTile(anchor) || AITile.IsCoastTile(anchor)) continue;
        local c4 = anchor + AIMap.GetTileIndex(offX, offY);
        if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;
        if (AIAirport.GetNearestTown(anchor, airport.type) != town.id) continue;

        if (AIR_CHEAP_SITE) {
          /* Eau/riviere/cote sur toute l'emprise, C4, et IsBuildableRectangle : sans AITestMode.
           * La sonde ci-dessous ne tourne plus que sur un hit cheap. */
          if (!OpexAirFootprintCheapOk(anchor, airport)) {
            if ("cheapSkip" in probes) probes.cheapSkip++;
            continue;
          }
        } else {
          /* Filtre de platitude préalable (docs/taches.md §0 tervicies point 5 & C4, façon AAAHogEx) :
           * Si l'écart d'altitude au sein de l'emprise dépasse 1 niveau, le terrassement échoue
           * massivement ou coûte trop cher. Rejet éliminatoire avant d'entrer en AITestMode. */
          local minH = AITile.GetMinHeight(anchor);
          local maxH = AITile.GetMaxHeight(anchor);
          local tooSteep = false;
          for (local tx = 0; tx <= offX; tx++) {
            for (local ty = 0; ty <= offY; ty++) {
              local t = anchor + AIMap.GetTileIndex(tx, ty);
              local tMin = AITile.GetMinHeight(t);
              local tMax = AITile.GetMaxHeight(t);
              if (tMin < minH) minH = tMin;
              if (tMax > maxH) maxH = tMax;
              if (maxH - minH >= 2) { tooSteep = true; break; }
            }
            if (tooSteep) break;
          }
          if (tooSteep) continue;
        }

        if (used >= allowance) {
          if (AIR_SITE_CACHE_ENABLED) AIR_SITE_CACHE[key] <- null;
          return null;
        }
        if (probes.left <= 0) return null;

        local ok = false;
        if (AIR_CHEAP_SITE) {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(anchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       execLevels < 3) {
              execLevels++;
              /* G7§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              if (OpexAirCanLevelFootprint(anchor, airport, town.id)) {
                ok = true;
              }
            }
          }
        } else {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          if (!ok) {
            local err = AIError.GetLastError();
            if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(anchor, c4);
              ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
              if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
            }
          }
        }
        used++;
        probes.left--;
        if ("tested" in probes) probes.tested++;
        if (ok) {
          if (AIR_SITE_CACHE_ENABLED) AIR_SITE_CACHE[key] <- anchor;
          return { town = town, anchor = anchor };
        }
      }
    }
  }
  if (AIR_SITE_CACHE_ENABLED && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  return null;
}

/* Economie et dimensionnement optimal de flotte selon les caracteristiques du vehicule. */
function OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
                          infrastructureMaintenance, maxCapital, newAirportCount = 2,
                          fixedPlanes = 0)
{
  local trip = OpexAirTripModel(plane.speed, plane.capacity, distance);
  local oneWayDays = trip.oneWayDays;
  local roundTripDays = trip.roundTripDays;
  local tripsPerMonth = trip.tripsPerMonth;
  local capacityPerPlane = trip.capacityPerPlane;
  if (capacityPerPlane <= 0) return null;
  local incomeDays = OpexCeilDiv(oneWayDays, 1);
  local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, distance, incomeDays);
  local totalIncomePerUnit = paxIncome;
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, distance, incomeDays);
    /* En soute, les avions de ligne transportent ~15% de fret postal sans refit */
    totalIncomePerUnit = paxIncome + (mailIncome * 15) / 100;
  }
  /* D4 par mode : le tarif moteur est exact, mais le rendement observe des
   * lignes air|pax depasse de 4,27 % la prediction mediane. Corriger ici,
   * avant revenu/profit/ROI, conserve une seule economie coherente pour le
   * classement, le chantier et la reconciliation post-construction. */
  local incomePerUnit = (totalIncomePerUnit * AIR_PAX_REVENUE_CALIBRATION_PCT) / 100.0;
  local airportMaintenanceAnnual =
      infrastructureMaintenance ? 12 * newAirportCount * airport.maintenance : 0;
  local airportAmortAnnual = (newAirportCount * airport.price * INFRA_AMORT_PCT / 100) / 30;
  local best = null;

  /* Plafond d'appareils initial : jusqu'a 3 sur nouvelle ligne, jusqu'a 6 sur hub existant.
   * marginal_fleet = 1 : demarrage minimal, 1 seul avion ; la croissance vient ensuite. */
  local isSmall = (airport.type == AIAirport.AT_SMALL || airport.type == AIAirport.AT_COMMUTER);
  local maxAllowed = (MARGINAL_FLEET || FLEET_PORTFOLIO) ? 1 : ((newAirportCount == 2) ? 3 : (isSmall ? 4 : 6));
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
   * cote appelant a ete mesure a −11,5 % (t = −2,66) le 2026-09-01 : ca rabote aussi le hub-a-hub,
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
    local amortAnnual = planes * plane.price / 20 + airportAmortAnnual;
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
  return best;
}

/* G4 : Reconcile le contrat economique d'une ligne air avec ce qui a ete effectivement pose.
 * Les arrets joints n'ajoutent que leur bassin marginal hors couverture de l'aeroport et la flotte
 * est figee au nombre reellement construit. Le cout comptable final remplace le capital estime,
 * puis amortissement, profit et ROI sont derives ensemble. */
function OpexAirReconcileActualBuild(catalog, plan, result)
{
  if (plan == null || result == null || !("economics" in plan)) return;
  local actualPlanes = ("vehicles" in result && result.vehicles != null) ? result.vehicles.len() : 0;
  if (actualPlanes <= 0) return;
  local baseMonthly = ("monthlyPax" in plan) ? plan.monthlyPax : 0;
  local monthlyPax = baseMonthly;
  if (monthlyPax < 10) monthlyPax = 10;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local economics = OpexAirEconomics(catalog, plan.airport, plan.plane, plan.distance, monthlyPax,
                                      AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0,
                                      0, newAirports, actualPlanes);
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

/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees. */
function OpexAirAddPlane(line)
{
  local result = { added = 0, reason = "" };
  if (!("vehicles" in line) || line.vehicles.len() == 0) {
    result.reason = "NOVEH"; return result;
  }
  local airportTile = ("originA" in line) && AIAirport.IsAirportTile(line.originA)
      ? line.originA
      : (AIAirport.IsAirportTile(line.stationA) ? line.stationA : null);
  if (airportTile == null) {
    result.reason = "NOAIR"; return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(airportTile);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    result.reason = "HANG"; return result;
  }
  local template = null;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) {
      template = v; break;
    }
  }
  if (template == null) { result.reason = "NOLIVE"; return result; }
  local price = AIEngine.GetPrice(AIVehicle.GetEngineType(template));
  if (price <= 0) { result.reason = "PRICE"; return result; }
  local need = price + OpexCashReserve() + 1000;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    if (REBORROW) money = OpexTryReborrow(need, money);
    if (money < need) {
      result.reason = "CASH"; return result;
    }
  }
  local extra = AIVehicle.CloneVehicle(hangar, template, true);
  if (!AIVehicle.IsValidVehicle(extra)) {
    local engine = AIVehicle.GetEngineType(template);
    local cargo = ("cargo" in line) ? line.cargo : 0;
    extra = AIVehicle.BuildVehicleWithRefit(hangar, engine, cargo);
    if (AIVehicle.IsValidVehicle(extra)) {
      AIOrder.ShareOrders(extra, template);
    }
  }
  if (!AIVehicle.IsValidVehicle(extra)) {
    result.reason = "CLONE|" + AIError.GetLastError();
    return result;
  }
  if (!AIVehicle.StartStopVehicle(extra)) {
    if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
    result.reason = "START"; return result;
  }
  line.vehicles.append(extra);
  result.added = 1;
  result.reason = "OK";
  return result;
}

/* Reconstitue un avion perdu sans dependre d'un appareil encore vivant. Le moteur
 * est memorise dans la ligne a sa construction; les deux aeroports sont des
 * destinations durables, donc les ordres peuvent etre recrees sans clonage. */
function OpexAirRefleetCrashedPlane(line)
{
  local result = { added = 0, reason = "" };
  if (!(("refleetEngine" in line) && line.refleetEngine >= 0)) {
    result.reason = "NOENGINE"; return result;
  }
  if (!AIAirport.IsAirportTile(line.stationA) || !AIAirport.IsAirportTile(line.stationB)) {
    result.reason = "NOAIRPORT"; return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(line.stationA);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    result.reason = "HANGAR"; return result;
  }
  if (AIVehicle.GetBuildWithRefitCapacity(hangar, line.refleetEngine, line.cargo) <= 0) {
    result.reason = "REFIT"; return result;
  }
  local price = AIEngine.GetPrice(line.refleetEngine);
  if (price <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + OpexCashReserve()) {
    result.reason = "CASH"; return result;
  }
  local plane = AIVehicle.BuildVehicleWithRefit(hangar, line.refleetEngine, line.cargo);
  if (!AIVehicle.IsValidVehicle(plane)) { result.reason = "BUILD"; return result; }
  local flags = AIOrder.OF_NONE;
  if (!AIOrder.AppendOrder(plane, line.stationA, flags) ||
      !AIOrder.AppendOrder(plane, line.stationB, flags) || AIOrder.GetOrderCount(plane) != 2) {
    AIVehicle.SellVehicle(plane); result.reason = "ORDER"; return result;
  }
  if (!AIVehicle.StartStopVehicle(plane)) {
    if (AIVehicle.IsStoppedInDepot(plane)) AIVehicle.SellVehicle(plane);
    result.reason = "START"; return result;
  }
  if (!("vehicles" in line)) line.vehicles <- [];
  else if (line.vehicles == null) line.vehicles = [];
  line.vehicles.append(plane);
  if ("vehicle" in line) line.vehicle = plane;
  else line.vehicle <- plane;
  result.added = 1; result.reason = "OK";
  return result;
}

/* Evalue et planifie la meilleure liaison aerienne en testant les combinaisons
 * grand aeroport (+gros/petit avion) et petit aeroport (+petit avion strictement). */
function OpexAirPlanBetter(plan, bestPlan)
{
  if (bestPlan == null) return true;
  /* Arbitrage ROI vs Volume : si un plan offre un ROI significativement superieur (>25% d'ecart),
   * il deploie le capital plus vite et permet de batir plus de lignes. */
  if (plan.economics.roi > (bestPlan.economics.roi * 1.25).tointeger()) return true;
  if (bestPlan.economics.roi > (plan.economics.roi * 1.25).tointeger()) return false;
  return plan.economics.profitAnnual > bestPlan.economics.profitAnnual;
}

/* C68 : transforme le contre-factuel passif M3 en intervention minimale. Le caller a deja choisi
 * le type d'aeroport, les sites, la paire et la demande avec le chemin historique. Sous le switch,
 * on ne change donc que l'appareil et l'economie de cette route, avec exactement le meme modele
 * OpexAirEconomics que M3. Sous 0, le resultat est strictement le couple historique. */
function OpexAirChooseRoutePlane(catalog, airport, selectedPlane, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount)
{
  local selectedEconomics = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount);
  if (!AIR_ROUTE_PLANE_SELECTION || !(airport.type in catalog.airPlaneChoicesByAirport)) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }

  local bestPlane = selectedPlane;
  local bestEconomics = selectedEconomics;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount);
    if (economics == null) continue;
    if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
        (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
      bestPlane = plane;
      bestEconomics = economics;
    }
  }
  return { plane = bestPlane, economics = bestEconomics };
}

/* M3/G12 : comparaison PASSIVE du plan air deja elu contre les autres appareils compatibles avec
 * le meme type d'aeroport, sur la meme distance/demande et avec le meme nombre initial d'avions. */
function OpexM3ProbeAirEquipment(catalog, plan, phase)
{
  if (!EQUIPMENT_ROI_PROBE || plan == null || !("airport" in plan) || !("plane" in plan) ||
      !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return;
  local alternatives = catalog.airPlaneChoicesByAirport[plan.airport.type];
  if (alternatives.len() == 0) return;
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local fixedPlanes = ("planes" in plan) && plan.planes > 0 ? plan.planes : 1;
  local bestProfit = null, bestProfitId = -1;
  local bestRoi = null, bestRoiId = -1;
  local bestNativeProfit = null, bestNativeProfitId = -1;
  local bestNativeRoi = null, bestNativeRoiId = -1;
  local viable = 0, nativeChoices = 0, refitProxyChoices = 0;
  foreach (plane in alternatives) {
    if (plane.maxOrderDistance > 0 && plan.distance > plane.maxOrderDistance) continue;
    local native = plane.defaultCargo == catalog.paxCargo;
    if (native) nativeChoices++; else refitProxyChoices++;
    local economics = OpexAirEconomics(catalog, plan.airport, plane, plan.distance, plan.monthlyPax,
        infrastructureMaintenance, 0, newAirports, fixedPlanes);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = plane.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = plane.id;
    }
    if (native && (bestNativeProfit == null || economics.profitAnnual > bestNativeProfit.profitAnnual ||
        (economics.profitAnnual == bestNativeProfit.profitAnnual && economics.roi > bestNativeProfit.roi))) {
      bestNativeProfit = economics; bestNativeProfitId = plane.id;
    }
    if (native && (bestNativeRoi == null || economics.roi > bestNativeRoi.roi ||
        (economics.roi == bestNativeRoi.roi && economics.profitAnnual > bestNativeRoi.profitAnnual))) {
      bestNativeRoi = economics; bestNativeRoiId = plane.id;
    }
  }
  OpexM3EquipmentLog("mode=air phase=" + phase + " airport_type=" + plan.airport.type
      + " choices=" + alternatives.len() + " viable=" + viable + " native_choices=" + nativeChoices
      + " refit_proxy_choices=" + refitProxyChoices + " selected=" + plan.plane.id
      + " selected_refit=" + (plan.plane.defaultCargo != catalog.paxCargo ? 1 : 0)
      + " selected_profit=" + plan.economics.profitAnnual + " selected_roi=" + plan.economics.roi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_roi_id=" + bestRoiId + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_native_profit_id=" + bestNativeProfitId
      + " best_native_profit=" + (bestNativeProfit != null ? bestNativeProfit.profitAnnual : -999999999)
      + " best_native_roi_id=" + bestNativeRoiId
      + " best_native_roi=" + (bestNativeRoi != null ? bestNativeRoi.roi : -1));
}

function OpexM3ProbeAirPreAdmission(catalog, airport, selectedPlane, distance, monthlyPax,
                                    infrastructureMaintenance, maxCapital, newAirportCount,
                                    selectedEconomics, phase)
{
  if (!EQUIPMENT_ROI_PROBE || airport == null || selectedPlane == null ||
      !(airport.type in catalog.airPlaneChoicesByAirport)) return;
  local alternatives = catalog.airPlaneChoicesByAirport[airport.type];
  if (alternatives.len() == 0) return;
  local bestProfit = null, bestProfitId = -1;
  local bestRoi = null, bestRoiId = -1;
  local bestNativeProfit = null, bestNativeProfitId = -1;
  local bestNativeRoi = null, bestNativeRoiId = -1;
  local viable = 0, nativeChoices = 0, refitProxyChoices = 0;
  foreach (plane in alternatives) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local native = plane.defaultCargo == catalog.paxCargo;
    if (native) nativeChoices++; else refitProxyChoices++;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = plane.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = plane.id;
    }
    if (native && (bestNativeProfit == null || economics.profitAnnual > bestNativeProfit.profitAnnual ||
        (economics.profitAnnual == bestNativeProfit.profitAnnual && economics.roi > bestNativeProfit.roi))) {
      bestNativeProfit = economics; bestNativeProfitId = plane.id;
    }
    if (native && (bestNativeRoi == null || economics.roi > bestNativeRoi.roi ||
        (economics.roi == bestNativeRoi.roi && economics.profitAnnual > bestNativeRoi.profitAnnual))) {
      bestNativeRoi = economics; bestNativeRoiId = plane.id;
    }
  }
  local selectedProfit = selectedEconomics != null ? selectedEconomics.profitAnnual : -999999999;
  local selectedRoi = selectedEconomics != null ? selectedEconomics.roi : -1;
  local selectedPositive = selectedEconomics != null && selectedEconomics.profitAnnual > 0;
  OpexM3EquipmentLog("mode=air phase=" + phase + " airport_type=" + airport.type
      + " choices=" + alternatives.len() + " viable=" + viable + " native_choices=" + nativeChoices
      + " refit_proxy_choices=" + refitProxyChoices + " selected=" + selectedPlane.id
      + " selected_refit=" + (selectedPlane.defaultCargo != catalog.paxCargo ? 1 : 0)
      + " selected_ok=" + (selectedEconomics != null ? 1 : 0)
      + " selected_profit=" + selectedProfit + " selected_roi=" + selectedRoi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_roi_id=" + bestRoiId + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_native_profit_id=" + bestNativeProfitId
      + " best_native_profit=" + (bestNativeProfit != null ? bestNativeProfit.profitAnnual : -999999999)
      + " best_native_roi_id=" + bestNativeRoiId
      + " best_native_roi=" + (bestNativeRoi != null ? bestNativeRoi.roi : -1)
      + " admission_flip=" + ((!selectedPositive && bestProfit != null && bestProfit.profitAnnual > 0) ? 1 : 0)
      + " native_admission_flip="
      + ((!selectedPositive && bestNativeProfit != null && bestNativeProfit.profitAnnual > 0) ? 1 : 0));
}

/* An anchor only describes the north-west corner. Its buildability depends on
 * the airport footprint, so the airport type is part of the durable-site key. */
function OpexAirSiteAbandonKey(site, airportType)
{
  return "air_site|" + airportType + "|" + site.anchor;
}

function OpexAirTownLimitAbandonKey(site)
{
  return "air_town_limit|" + site.town.tile;
}

/* `abandoned` : table des paires dont une construction a deja echoue (cle
 * "air|tileA|tileB", identique a celle de main.nut), et optionnellement des
 * sites exacts et types ("air_site|airportType|anchor"). null = filtre desactive.
 * Le filtre est place APRES les tests de distance et AVANT OpexAirEconomics : les paires
 * ecartees pour distance ne paient pas la concatenation, et celles qui restent evitent le
 * calcul cher. */
function OpexAirPlans(catalog, lines = null, maxCapital = 0, projects = null, abandoned = null, paxBand = PAX_BAND_ALL)
{
  local t0_all = AIController.GetTick();
  local l0_all = AIController.GetOpsTillSuspend();
  local _calcDeltaOps = function(t0, l0) {
    local left = AIController.GetOpsTillSuspend();
    local elapsed = AIController.GetTick() - t0;
    return elapsed <= 0
      ? l0 - left
      : l0 + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
  };
  local perfOpsSites = 0;
  local perfOpsEval = 0;
  local perfProbesCount = 0;
  local perfCheapSkip = 0;
  local perfSitesFound = 0;

  local combos = (("airCombos" in catalog) && catalog.airCombos != null && catalog.airCombos.len() > 0)
      ? catalog.airCombos
      : (catalog.airport != null && catalog.plane != null ? [{ airport = catalog.airport, plane = catalog.plane }] : []);
  local servedDiag = null;
  if (DECISION_LOG) {
    AIR_PLAN_DIAG_SEQ++;
    servedDiag = {
      scan = AIR_PLAN_DIAG_SEQ,
      nullCalls = 0, emptyCalls = 0, nonemptyCalls = 0,
      trueCalls = 0, falseCalls = 0,
      loggedFalseTowns = {}, loggedFalseCount = 0, noAirLogged = false,
    };
    local linesState = lines == null ? "null" : (lines.len() == 0 ? "empty" : "nonempty");
    local lineCount = lines == null ? 0 : lines.len();
    local airLineCount = 0;
    if (lines != null) {
      foreach (line in lines) {
        if (("mode" in line) && line.mode == "air") airLineCount++;
      }
    }
    OpexDecide("AIR_PLAN_INPUT", "scan=" + servedDiag.scan + " lines_state=" + linesState
               + " line_count=" + lineCount + " air_line_count=" + airLineCount
               + " combos=" + combos.len());
  }
  if (combos.len() == 0) {
    if (DECISION_LOG) {
      OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
                 + " null_calls=0 empty_calls=0 nonempty_calls=0 true_calls=0 false_calls=0"
                 + " false_towns_logged=0");
    }
    return null;
  }

  local towns = OpexAirSortedTowns(catalog.towns);
  local limit = towns.len() < AIR_TOWN_POOL ? towns.len() : AIR_TOWN_POOL;
  local bestPlan = null;
  /* GetMonthlyMaintenanceCost expose le tarif potentiel, pas une depense toujours active.
   * CompaniesGenStatistics ne le debite que si le reglage de partie est arme. La configuration
   * gelee le laisse a false : compter ce tarif rendait toutes les paires de la graine 42
   * artificiellement deficitaires (270 000/an pour deux AT_LARGE). */
  local infrastructureMaintenance =
      AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  foreach (combo in combos) {
    local airport = combo.airport;
    local plane = combo.plane;
    local townPool = AIR_TOWN_POOL;
    local limit = towns.len() < townPool ? towns.len() : townPool;
    local minDist = (plane.speed >= 400) ? 32 : 30;
    local sites = [];
    local probes = { left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0 };
    local tSites0 = AIController.GetTick();
    local lSites0 = AIController.GetOpsTillSuspend();
    for (local i = 0; i < limit; i++) {
      /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
       * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
       * construction aerienne sur une carte partiellement couverte. */
      local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
      if (isServed) continue;
      /* Typage selon la population :
       * - Grands aéroports : accessibles dès 600 habitants (suffisant pour alimenter un jet vers un hub)
       * - Petits aéroports : utilisables sur toutes les villes si aucun grand aéroport ne rentre */
      if (combo.kind == "large" && towns[i].pop < 600) continue;
      local site = OpexAirFindSite(towns[i], airport, probes);
      if (site != null) sites.append(site);
    }
    perfOpsSites += _calcDeltaOps(tSites0, lSites0);
    perfProbesCount += probes.tested;
    if ("cheapSkip" in probes) perfCheapSkip += probes.cheapSkip;
    perfSitesFound += sites.len();
    OpexSign(AIMap.GetTileIndex(1, 3), "AS|S=" + sites.len() + "|A=" + airport.name);

    local tEval0 = AIController.GetTick();
    local lEval0 = AIController.GetOpsTillSuspend();
    for (local a = 0; a < sites.len(); a++) {
      for (local b = a + 1; b < sites.len(); b++) {
        local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                        sites[a].anchor, sites[b].anchor);
        local flightDistance = OpexFlightDistance(sites[a].anchor, sites[b].anchor);
        if (distance < minDist) continue;
        if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) continue;
        if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
        if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
          continue;
        }

        if (abandoned != null) {
          local pairKey = "air|" + sites[a].town.tile + "|" + sites[b].town.tile;
          if ((pairKey in abandoned)
              || (AIR_TOWN_LIMIT_MEMORY && ((OpexAirTownLimitAbandonKey(sites[a]) in abandoned)
                  || (OpexAirTownLimitAbandonKey(sites[b]) in abandoned)))
              || (AIR_ABANDON_SITE && ((OpexAirSiteAbandonKey(sites[a], airport.type) in abandoned)
                  || (OpexAirSiteAbandonKey(sites[b], airport.type) in abandoned)))) continue;
        }

        local popA = sites[a].town.pop;
        local popB = sites[b].town.pop;
        local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
        if (monthlyPax < 10) monthlyPax = 10;
        if (a == 0 && b == 1) {
          OpexSign(AIMap.GetTileIndex(1, 5), "AX|PA=" + popA + "|PB=" + popB + "|MPX=" + monthlyPax);
        }

        local routeChoice = OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
                                                    infrastructureMaintenance, maxCapital, 2);
        local routePlane = routeChoice.plane;
        local economics = routeChoice.economics;
        if (EQUIPMENT_ROI_PROBE) {
          OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 2, economics, "pre_admission_newpair");
        }
        if (economics == null) continue;

        local plan = {
          siteA = sites[a], siteB = sites[b], distance = flightDistance,
          orderDistance = orderDistance,
          airport = airport, plane = routePlane,
          monthlyPax = monthlyPax, planes = economics.planes, capital = economics.capital, economics = economics,
          reuseA = false, hubRoutes = 0, arm = "newpair",
        };
        OpexAirReserveJoinedStops(catalog, plan);

        if (a == 0 && b == 1) {
          OpexSign(AIMap.GetTileIndex(1, 8), "AY|" + economics.capital + "|"
                                                + economics.profitAnnual);
          OpexSign(AIMap.GetTileIndex(1, 9), "AV|" + routePlane.speed + "|" + routePlane.capacity
                                                + "|" + economics.planes + "|"
                                                + economics.oneWayDays.tointeger());
        }
        if (economics.profitAnnual > 0) {
          if (projects != null) projects.append(plan);
          if (OpexAirPlanBetter(plan, bestPlan)) {
            bestPlan = plan;
          }
        }
      }
    }
    perfOpsEval += _calcDeltaOps(tEval0, lEval0);

    /* Bras hub : un aeroport existant, rentable et non sature (max 8 routes), plus UNE destination. */
    local hubs = [];
    if (AIR_HUB && lines != null) {
      if (sites.len() < AIR_HUB_NEW_SITE_POOL) {
        local hubProbes = { left = AIR_MAX_SITE_PROBES, townsLeft = towns.len(), tested = 0, cheapSkip = 0 };
        local tHubSites0 = AIController.GetTick();
        local lHubSites0 = AIController.GetOpsTillSuspend();
        for (local i = 0; i < towns.len() && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
          local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
          if (isServed) continue;
          /* Typage : grands aéroports dès 600 hab */
          if (combo.kind == "large" && towns[i].pop < 600) continue;
          if (combo.kind == "small" && towns[i].pop >= 2500) continue;
          local extraSite = OpexAirFindSite(towns[i], airport, hubProbes);
          if (extraSite != null) {
            sites.append(extraSite);
            perfSitesFound++;
          }
        }
        perfOpsSites += _calcDeltaOps(tHubSites0, lHubSites0);
        perfProbesCount += hubProbes.tested;
        if ("cheapSkip" in hubProbes) perfCheapSkip += hubProbes.cheapSkip;
      }
      local seenStations = {};
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        if (("deadStreak" in line) && line.deadStreak >= 2) continue;
        /* air_hub_fix : l'ancre d'un hub est la TUILE D'AEROPORT (line.stationA/B), pas le
         * centre-ville (line.originA/B). Sous 0, on rejoue litteralement le comportement casse. */
        local ends = null;
        if (AIR_HUB_FIX) {
          ends = [
            { anchor = line.stationA, origin = line.originA, stationId = line.stationA },
            { anchor = line.stationB, origin = line.originB, stationId = line.stationB },
          ];
        } else {
          ends = [
            { anchor = line.originA, origin = line.originA, stationId = line.stationA },
            { anchor = line.originB, origin = line.originB, stationId = line.stationB },
          ];
        }
        foreach (end in ends) {
          if (!AIMap.IsValidTile(end.anchor) || !AIAirport.IsAirportTile(end.anchor)) continue;
          local existingType = AIAirport.GetAirportType(end.anchor);
          if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
          /* Resolution non ambigue : `end.stationId` est une tuile, et `IsValidStation(tuile)`
           * peut etre vrai par pure collision d'indices. On resout toujours depuis l'ancre. */
          local station = AIR_HUB_FIX
              ? AIStation.GetStationID(end.anchor)
              : (AIStation.IsValidStation(end.stationId) ? end.stationId : AIStation.GetStationID(end.anchor));
          if (!AIStation.IsValidStation(station) || (station in seenStations)) continue;

          local routeCount = 0;
          foreach (other in lines) {
            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
                : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
            local otherB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
                : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
            if (otherA == station || otherB == station) routeCount++;
          }
          local maxRoutes = (existingType == AIAirport.AT_SMALL || existingType == AIAirport.AT_COMMUTER) ? 4 : 12;
          if (routeCount >= maxRoutes) continue;
          local townId = AITile.GetClosestTown(end.origin);
          if (townId < 0) continue;
          local hubTown = null;
          foreach (town in towns) {
            if (town.id == townId) { hubTown = town; break; }
          }
          if (hubTown == null) {
            hubTown = { id = townId, tile = end.origin, pop = AITown.GetPopulation(townId) };
          }
          seenStations.rawset(station, true);
          hubs.append({ town = hubTown, anchor = end.anchor, stationId = station, routes = routeCount });
        }
      }
      /* Aéroports orphelins : aéroports bâtis sans ligne active (ex: issu d'un BFAIL conservé). */
      local orphanList = AIStationList(AIStation.STATION_AIRPORT);
      for (local st = orphanList.Begin(); !orphanList.IsEnd(); st = orphanList.Next()) {
        if (st in seenStations) continue;
        local loc = AIStation.GetLocation(st);
        if (!AIMap.IsValidTile(loc) || !AIAirport.IsAirportTile(loc)) continue;
        local existingType = AIAirport.GetAirportType(loc);
        if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
        local townId = AITile.GetClosestTown(loc);
        if (townId < 0) continue;
        local hubTown = null;
        foreach (town in towns) {
          if (town.id == townId) { hubTown = town; break; }
        }
        if (hubTown == null) {
          hubTown = { id = townId, tile = loc, pop = AITown.GetPopulation(townId) };
        }
        seenStations.rawset(st, true);
        hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 });
      }
    }

    if (DECISION_LOG) {
      local siteFields = sites.len() == 0 ? "none" : "";
      foreach (site in sites) {
        if (siteFields != "") siteFields += ",";
        siteFields += site.town.id + ":" + site.town.tile;
      }
      local hubFields = hubs.len() == 0 ? "none" : "";
      foreach (hub in hubs) {
        if (hubFields != "") hubFields += ",";
        hubFields += hub.town.id + ":" + hub.town.tile;
      }
      OpexDecide("AIR_PLAN_SETS", "scan=" + servedDiag.scan + " combo=" + combo.kind
                 + " airport_type=" + airport.type + " plane=" + plane.id
                 + " sites_count=" + sites.len() + " sites=" + siteFields
                 + " hubs_count=" + hubs.len() + " hubs=" + hubFields);
    }

    local tHubEval0 = AIController.GetTick();
    local lHubEval0 = AIController.GetOpsTillSuspend();
    foreach (hub in hubs) {
      foreach (site in sites) {
        local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
        if (distance < 20) continue;
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                        hub.anchor, site.anchor);
        local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
        if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) continue;
        if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
        if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) continue;
        if (abandoned != null) {
          local pairKey = "air|" + hub.town.tile + "|" + site.town.tile;
          if ((pairKey in abandoned)
              || (AIR_TOWN_LIMIT_MEMORY && (OpexAirTownLimitAbandonKey(site) in abandoned))
              || (AIR_ABANDON_SITE && (OpexAirSiteAbandonKey(site, airport.type) in abandoned))) continue;
        }
        local hubMonthly = ((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1);
        local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
        local monthlyPax = hubMonthly + newMonthly;
        if (monthlyPax < 10) monthlyPax = 10;
        local routeChoice = OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
                                                    infrastructureMaintenance, maxCapital, 1);
        local routePlane = routeChoice.plane;
        local economics = routeChoice.economics;
        if (EQUIPMENT_ROI_PROBE) {
          OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 1, economics, "pre_admission_hubsite");
        }
        if (economics == null || economics.profitAnnual <= 0) continue;
        local plan = {
          siteA = hub, siteB = site, distance = flightDistance, orderDistance = orderDistance,
          airport = airport, plane = routePlane, monthlyPax = monthlyPax, planes = economics.planes,
          capital = economics.capital, economics = economics,
          reuseA = true, hubRoutes = hub.routes, arm = "hubsite",
        };
        OpexAirReserveJoinedStops(catalog, plan);
        if (plan.economics.profitAnnual <= 0) continue;
        if (projects != null) projects.append(plan);
        if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
      }
    }

    /* Liaisons Hub-a-Hub directes entre deux aeroports existants (capital = 1 avion seul) */
    for (local i = 0; i < hubs.len(); i++) {
      for (local j = i + 1; j < hubs.len(); j++) {
        local hub1 = hubs[i];
        local hub2 = hubs[j];
        local st1 = hub1.stationId;
        local st2 = hub2.stationId;
        local alreadyConnected = false;
        foreach (line in lines) {
          if (!("mode" in line) || line.mode != "air") continue;
          /* air_hub_fix : c'est CETTE comparaison qui etait morte -- un StationID (st1/st2, issus
           * de la decouverte de hub) contre une tuile d'aeroport (line.stationA/B). */
          local oA = AIR_HUB_FIX ? OpexAirLineStationId(line, 0)
              : (AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA));
          local oB = AIR_HUB_FIX ? OpexAirLineStationId(line, 1)
              : (AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB));
          if (!AIStation.IsValidStation(oA) || !AIStation.IsValidStation(oB)) continue;
          if ((oA == st1 && oB == st2) || (oA == st2 && oB == st1)) {
            alreadyConnected = true; break;
          }
        }
        if (alreadyConnected) continue;
        local distance = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
        if (distance < 20) continue;
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
        local flightDistance = OpexFlightDistance(hub1.anchor, hub2.anchor);
        if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) continue;
        if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
        if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) continue;
        if (abandoned != null
            && (("air|" + hub1.town.tile + "|" + hub2.town.tile) in abandoned)) continue;
        local monthly1 = ((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1);
        local monthly2 = ((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1);
        local monthlyPax = monthly1 + monthly2;
        if (monthlyPax < 10) monthlyPax = 10;
        local routeChoice = OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
                                                    infrastructureMaintenance, maxCapital, 0);
        local routePlane = routeChoice.plane;
        local economics = routeChoice.economics;
        if (EQUIPMENT_ROI_PROBE) {
          OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 0, economics, "pre_admission_hubhub");
        }
        if (economics == null || economics.profitAnnual <= 0) continue;
        local plan = {
          siteA = hub1, siteB = hub2, distance = flightDistance, orderDistance = orderDistance,
          airport = airport, plane = routePlane, monthlyPax = monthlyPax, planes = economics.planes,
          capital = economics.capital, economics = economics,
          reuseA = true, reuseB = true, hubRoutes = hub1.routes + hub2.routes,
          arm = "hubhub",
        };
        OpexAirReserveJoinedStops(catalog, plan);
        if (plan.economics.profitAnnual <= 0) continue;
        if (projects != null) projects.append(plan);
        if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
      }
    }
    perfOpsEval += _calcDeltaOps(tHubEval0, lHubEval0);
    if (AIR_HUB && hubs.len() > 0) {
      OpexSign(AIMap.GetTileIndex(1, 6), "AU|" + hubs.len() + "|"
               + (bestPlan != null && bestPlan.reuseA ? 1 : 0));
    }
    OpexSign(AIMap.GetTileIndex(1, 4), "AE|S=" + sites.len() + "|B=" + (bestPlan != null ? bestPlan.economics.profitAnnual : "NO"));
    if (bestPlan != null && bestPlan.airport.allowBig) break;
  }
  if (DECISION_LOG) {
    OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
               + " null_calls=" + servedDiag.nullCalls + " empty_calls=" + servedDiag.emptyCalls
               + " nonempty_calls=" + servedDiag.nonemptyCalls + " true_calls=" + servedDiag.trueCalls
               + " false_calls=" + servedDiag.falseCalls
               + " false_towns_logged=" + servedDiag.loggedFalseCount);
  }
  local totalOps = _calcDeltaOps(t0_all, l0_all);
  local elapsedTicks = AIController.GetTick() - t0_all;
  local elapsedDays = elapsedTicks / 74;
  if (DECISION_LOG) {
    local scanNum = (servedDiag != null && ("scan" in servedDiag)) ? servedDiag.scan : 0;
    OpexDecide("AIR_PLAN_PERF", "scan=" + scanNum + " total_ops=" + totalOps
               + " ops_sites=" + perfOpsSites + " ops_eval=" + perfOpsEval
               + " ticks=" + elapsedTicks + " days=" + elapsedDays
               + " probes=" + perfProbesCount + " cheap_skip=" + perfCheapSkip
               + " sites=" + perfSitesFound
               + " combos=" + combos.len()
               + " plans=" + (projects != null ? projects.len() : (bestPlan != null ? 1 : 0)));
  }
  AILog.Info("AIR_PLAN_PERF: total_ops=" + totalOps + " ops_sites=" + perfOpsSites
             + " ops_eval=" + perfOpsEval + " ticks=" + elapsedTicks + " days=" + elapsedDays
             + " probes=" + perfProbesCount + " cheap_skip=" + perfCheapSkip
             + " sites=" + perfSitesFound);
  OpexSign(AIMap.GetTileIndex(1, 2), "AP|T=" + totalOps + "|S=" + perfOpsSites + "|E=" + perfOpsEval + "|TK=" + elapsedTicks);
  return bestPlan;
}

/* Sondage pur d'un site : rend 0 s'il accepte l'aeroport, sinon le code d'erreur. Ne depense
 * rien et NE LAISSE AUCUNE TRACE dans la comptabilite du caller.
 *
 * ⚠️ Les deux pieges de ce sondage, mesures dans le source de 15.3 :
 *
 * 1. AIAccounting compte AUSSI les commandes jouees en AITestMode --
 *    `if (estimate_only) IncreaseDoCommandCosts(res.GetCost())`, script_object.cpp:299-302.
 *    Un sondage d'aeroport ajoute donc son prix SIMULE au compteur sans qu'une livre sorte :
 *    +35 000 £ par ligne au premier essai du 2026-09-02 (ratio cout/modele 1,02 -> 1,38).
 *    Le bouclier est un AIAccounting IMBRIQUE : son destructeur RESTAURE le total du niveau
 *    superieur (script_accounting.cpp), donc tout ce qui entre dedans est jete.
 *
 * 2. AITestMode lit le terrain REEL. Les 8 echecs mesures sont 7 x ERR_FLAT_LAND_REQUIRED et
 *    1 x ERR_AREA_NOT_CLEAR : sonder avant de niveler rejetterait tous les bons sites.
 *    A n'appeler qu'APRES LevelTiles.
 *
 * CmdBuildAirport appelle CheckIfAuthorityAllowsNewStation en tout premier
 * (station_cmd.cpp:2637), et NoTestTownRating n'est pose que par la generation interne du jeu :
 * le refus municipal remonte donc bien jusqu'ici. */
function OpexAirProbeSite(site, airportType)
{
  local shield = AIAccounting();
  local test = AITestMode();
  local ok = AIAirport.BuildAirport(site.anchor, airportType, AIStation.STATION_NEW);
  local err = ok ? 0 : AIError.GetLastError();
  test = null;
  shield = null;
  return err;
}

/* Le refus municipal est le seul cas rattrapable : on plante alors des arbres -- HORS bouclier,
 * cette depense-la est reelle -- et on resonde. ERR_LOCAL_AUTHORITY_REFUSES couvre AUSSI le
 * plafond de bruit (script_error.hpp), que les arbres ne reparent pas : le second sondage tranche
 * entre les deux au lieu de le deviner. */
function OpexAirSiteRefusal(site, airportType)
{
  local err = OpexAirProbeSite(site, airportType);
  if (err != AIError.ERR_LOCAL_AUTHORITY_REFUSES) return err;
  OpexBoostTownRating(site.town.id, 800, 40);
  return OpexAirProbeSite(site, airportType);
}

function OpexAirRollback(airportA, airportB, planes)
{
  /* La flotte n'est demarree qu'apres tous les clones et ordres valides : elle est donc encore
   * dans le hangar et peut etre vendue avant que ce hangar ne disparaisse. */
  foreach (plane in planes) {
    if (AIVehicle.IsValidVehicle(plane)) AIVehicle.SellVehicle(plane);
  }
  /* G7§1 : l'ancien code ne retirait que airportB. airportA -- toujours passe en premier
   * argument par les appelants quand il est neuf -- n'etait jamais retire, laissant un
   * aeroport orphelin sur la carte apres chaque echec BFAIL/STNFAIL/HANGAR/PLANE/ORDFAIL/START. */
  if (airportB != null && AIAirport.IsAirportTile(airportB)) AIAirport.RemoveAirport(airportB);
  if (airportA != null && AIAirport.IsAirportTile(airportA)) AIAirport.RemoveAirport(airportA);
}

/* C33.2 : Pose d'arrets de bus traversants joints a la gare de l'aeroport (modele AAAHogEx piece stations).
 * Ces arrets etendent l'aire de captage de l'aeroport jusqu'au coeur de la ville hote,
 * captant les passagers directement a l'aeroport sans aucun vehicule routier ni frais de transfert. */
function OpexAirBuildJoinedStops(airportTile, stationId, airport, town, paxCargo)
{
  local summary = { count = 0, monthlyPax = 0 };
  if (!AIR_JOINED_STOPS || !AIStation.IsValidStation(stationId)) return summary;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local spread = AIGameSettings.GetValue("station.station_spread");
  if (spread < 4) spread = 12;

  local w = airport.width;
  local h = airport.height;
  local ax = AIMap.GetTileX(airportTile);
  local ay = AIMap.GetTileY(airportTile);
  local center = airportTile + AIMap.GetTileIndex(w / 2, h / 2);

  /* Boite permise par station_spread autour de l'emprise de l'aeroport */
  local minX = ax + w - spread;
  if (minX < 1) minX = 1;
  local maxX = ax + spread - 1;
  if (maxX >= mapX - 1) maxX = mapX - 2;

  local minY = ay + h - spread;
  if (minY < 1) minY = 1;
  local maxY = ay + spread - 1;
  if (maxY >= mapY - 1) maxY = mapY - 2;

  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local airportCoverage = AIStation.GetCoverageRadius(AIStation.STATION_AIRPORT);
  local dirs = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1),
    AIMap.GetTileIndex(-1, 0), AIMap.GetTileIndex(0, -1)
  ];

  local candidates = [];
  for (local x = minX; x <= maxX; x++) {
    for (local y = minY; y <= maxY; y++) {
      local tile = AIMap.GetTileIndex(x, y);
      if (!AIMap.IsValidTile(tile)) continue;
      if (AITile.GetClosestTown(tile) != town.id) continue;
      if (!AIRoad.IsRoadTile(tile)) continue;
      if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile) || AITile.IsStationTile(tile)) continue;
      if (AIMap.DistanceManhattan(tile, center) < 3) continue;

      /* C33.2 / G4 : un arret dans la couverture deja assuree par l'emprise aeroport ne
       * rapporte aucune demande marginale. Distance minimale au rectangle de l'aeroport,
       * pas seulement a son coin d'ancrage. */
      local dx = 0;
      if (x < ax) dx = ax - x;
      else if (x >= ax + w) dx = x - (ax + w - 1);
      local dy = 0;
      if (y < ay) dy = ay - y;
      else if (y >= ay + h) dy = y - (ay + h - 1);
      if (dx + dy <= airportCoverage) continue;

      local val = AITile.GetCargoProduction(tile, paxCargo, 1, 1, coverage);
      if (val <= 0) continue;

      foreach (dir in dirs) {
        local front = tile + dir;
        if (!AIMap.IsValidTile(front) || !AIRoad.IsRoadTile(front)) continue;
        local ok = false;
        {
          local test = AITestMode();
          ok = AIRoad.BuildDriveThroughRoadStation(tile, front, AIRoad.ROADVEHTYPE_BUS, stationId);
        }
        if (ok) {
          candidates.append({ tile = tile, front = front, value = val, dist = AIMap.DistanceManhattan(tile, town.tile) });
          break;
        }
      }
    }
  }

  if (candidates.len() == 0) return summary;

  candidates.sort(function(a, b) {
    if (a.value > b.value) return -1;
    if (a.value < b.value) return 1;
    if (a.dist < b.dist) return -1;
    if (a.dist > b.dist) return 1;
    return 0;
  });

  local builtStops = [];
  local maxStops = AIR_JOINED_STOP_LIMIT;
  if (maxStops < 0) maxStops = 0;
  if (maxStops > 2) maxStops = 2;

  foreach (cand in candidates) {
    if (builtStops.len() >= maxStops) break;

    local tooClose = false;
    foreach (prev in builtStops) {
      /* Deux rayons de collecte qui se recouvrent ne sont pas additionnables. */
      if (AIMap.DistanceManhattan(cand.tile, prev) <= 2 * coverage) {
        tooClose = true;
        break;
      }
    }
    if (tooClose) continue;

    local ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, cand.front, AIRoad.ROADVEHTYPE_BUS, stationId);
    if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(town.id, 800, 40);
      ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, cand.front, AIRoad.ROADVEHTYPE_BUS, stationId);
    }

    if (ok) {
      builtStops.append(cand.tile);
      summary.count++;
      summary.monthlyPax += cand.value;
      if (DECISION_LOG) {
        OpexDecide("AIR_JOINED_STOP", "station=" + stationId + " town=" + town.id + " tile=" + cand.tile + " val=" + cand.value);
      }
    }
  }

  return summary;
}

/* Construit une ligne aerienne complete. Le caller a deja mesure la recherche des sites et
 * verifie le budget monetaire. Rend toujours une table, jamais une exception. */
function OpexBuildAirRoute(catalog, budget, plan)
{
  local result = { ok = false, reason = "", opcodes = 0, error = 0, errorText = "", stationA = null,
                   stationB = null, vehicle = null, vehicles = [], actualCost = 0,
                   plannedCapital = (("capital" in plan) ? plan.capital : 0),
                   joinedStopsA = 0, joinedStopsB = 0, joinedMonthlyPax = 0,
                   joinedMonthlyPaxA = 0, joinedMonthlyPaxB = 0,
                   joinedRawMonthlyPax = 0, joinedRawMonthlyPaxA = 0, joinedRawMonthlyPaxB = 0,
                   joinedStopCost = 0 };
  local airportA = null;
  local airportB = null;
  local plane = null;

  local airport = ("airport" in plan) ? plan.airport : catalog.airport;
  local planeChoice = ("plane" in plan) ? plan.plane : catalog.plane;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;

  /* air_cost_probe : le cout REEL de la ligne aerienne, nivellement, aeroports, avions et
   * demolitions de repli compris. Symetrique du `costs` de builder_rail.nut. Le seul
   * AIAccounting imbrique en dessous est le bouclier d'OpexAirProbeSite, et c'est voulu : il
   * jette le cout SIMULE des sondages au lieu de le laisser gonfler ce compteur. */
  local costs = AIAccounting();

  budget.begin();

  if (reuseA) {
    if (AIAirport.IsAirportTile(plan.siteA.anchor) &&
        OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteA.anchor),
                                   planeChoice.planeType)) {
      airportA = plan.siteA.anchor;
    }
  } else {
    OpexAirLevelFootprint(plan.siteA.anchor, airport, plan.siteA.town.id);
    local okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
    if (!okA && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(plan.siteA.town.id, 800, 40);
      okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
    }
    if (okA && AIAirport.IsAirportTile(plan.siteA.anchor)) airportA = plan.siteA.anchor;
  }
  if (airportA == null) {
    if (!reuseA) OpexAirInvalidateCachedSite(plan.siteA, airport);
    result.error = AIError.GetLastError();
    result.errorText = AIError.GetLastErrorString();
    result.opcodes += budget.end("build_airports");
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = reuseA ? "HUB" : "AFAIL";
    return result;
  }

  if (reuseB) {
    if (AIAirport.IsAirportTile(plan.siteB.anchor) &&
        OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteB.anchor),
                                   planeChoice.planeType)) {
      airportB = plan.siteB.anchor;
    }
  } else {
    OpexAirLevelFootprint(plan.siteB.anchor, airport, plan.siteB.town.id);
    local okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
    if (!okB && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(plan.siteB.town.id, 800, 40);
      okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
    }
    if (okB && AIAirport.IsAirportTile(plan.siteB.anchor)) airportB = plan.siteB.anchor;
  }
  result.opcodes += budget.end("build_airports");
  if (airportB == null) {
    if (!reuseB) OpexAirInvalidateCachedSite(plan.siteB, airport);
    result.error = AIError.GetLastError();
    result.errorText = AIError.GetLastErrorString();
    local keepOrphan = (AIGameSettings.GetValue("economy.infrastructure_maintenance") == 0);
    if (!keepOrphan) {
      OpexAirRollback(reuseA ? null : airportA, null, []);
    }
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = reuseB ? "HUBB" : "BFAIL";
    return result;
  }

  local stationA = AIStation.GetStationID(airportA);
  local stationB = AIStation.GetStationID(airportB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) {
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "STNFAIL";
    return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(airportA);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "HANGAR";
    return result;
  }

  budget.begin();
  plane = AIVehicle.BuildVehicleWithRefit(hangar, planeChoice.id, catalog.paxCargo);
  if (!AIVehicle.IsValidVehicle(plane)) {
    result.error = AIError.GetLastError();
    result.errorText = AIError.GetLastErrorString();
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "PLANE";
    return result;
  }

  local airFlags = AIOrder.OF_NONE;
  local okOrderA = AIOrder.AppendOrder(plane, airportA, airFlags);
  local errorA = okOrderA ? 0 : AIError.GetLastError();
  local okOrderB = AIOrder.AppendOrder(plane, airportB, airFlags);
  local errorB = okOrderB ? 0 : AIError.GetLastError();
  local ordersOk = okOrderA && okOrderB && AIOrder.GetOrderCount(plane) == 2;
  if (!ordersOk) {
    result.error = !okOrderA ? errorA : errorB;
    result.errorText = AIError.GetLastErrorString();
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, [plane]);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "ORDFAIL";
    return result;
  }
  local built = [plane];
  local wanted = ("planes" in plan) ? plan.planes : 1;
  for (local i = 1; i < wanted; i++) {
    local extra = AIVehicle.CloneVehicle(hangar, plane, true);
    if (!AIVehicle.IsValidVehicle(extra)) {
      local engine = AIVehicle.GetEngineType(plane);
      extra = AIVehicle.BuildVehicleWithRefit(hangar, engine, catalog.paxCargo);
      if (AIVehicle.IsValidVehicle(extra)) AIOrder.ShareOrders(extra, plane);
    }
    if (!AIVehicle.IsValidVehicle(extra)) break;
    built.append(extra);
  }
  foreach (aircraft in built) {
    if (!AIVehicle.StartStopVehicle(aircraft)) {
      result.error = AIError.GetLastError();
      result.errorText = AIError.GetLastErrorString();
      result.opcodes += budget.end("build_aircraft");
      OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built);
      result.actualCost = costs != null ? costs.GetCosts() : 0;
      result.reason = "START";
      return result;
    }
  }
  result.opcodes += budget.end("build_aircraft");

  if (AIR_JOINED_STOPS) {
    local beforeStops = costs != null ? costs.GetCosts() : 0;
    if (!reuseA) {
      local joinedA = OpexAirBuildJoinedStops(airportA, stationA, airport, plan.siteA.town, catalog.paxCargo);
      result.joinedStopsA = joinedA.count;
      result.joinedRawMonthlyPaxA = joinedA.monthlyPax;
      result.joinedRawMonthlyPax += joinedA.monthlyPax;
      result.joinedMonthlyPaxA = OpexAirJoinedMarginalProduction(
          stationA, airportA, airport.type, catalog.paxCargo);
      result.joinedMonthlyPax += result.joinedMonthlyPaxA;
    }
    if (!reuseB) {
      local joinedB = OpexAirBuildJoinedStops(airportB, stationB, airport, plan.siteB.town, catalog.paxCargo);
      result.joinedStopsB = joinedB.count;
      result.joinedRawMonthlyPaxB = joinedB.monthlyPax;
      result.joinedRawMonthlyPax += joinedB.monthlyPax;
      result.joinedMonthlyPaxB = OpexAirJoinedMarginalProduction(
          stationB, airportB, airport.type, catalog.paxCargo);
      result.joinedMonthlyPax += result.joinedMonthlyPaxB;
    }
    local afterStops = costs != null ? costs.GetCosts() : beforeStops;
    result.joinedStopCost = afterStops - beforeStops;
    if (result.joinedStopCost < 0) result.joinedStopCost = 0;
  }

  result.actualCost = costs != null ? costs.GetCosts() : 0;
  result.ok = true;
  result.reason = "OK";
  result.stationA = airportA;
  result.stationB = airportB;
  result.vehicle = plane;
  result.vehicles = built;
  result.capacity <- AIVehicle.GetCapacity(plane, catalog.paxCargo);
  if (EQUIPMENT_ROI_PROBE) {
    OpexM3EquipmentLog("mode=air phase=post_refit selected=" + planeChoice.id
        + " cargo=" + catalog.paxCargo
        + " selected_refit=" + (planeChoice.defaultCargo != catalog.paxCargo ? 1 : 0)
        + " catalog_capacity=" + planeChoice.capacity + " actual_capacity=" + result.capacity
        + " capacity_delta=" + (result.capacity - planeChoice.capacity));
  }
  result.reusedA <- reuseA;
  if (AIR_CATCHMENT_PROBE) {
    local probeOps = 0;
    probeOps += OpexAirCatchmentProbeEndpoint(catalog, stationA, airportA, plan.siteA.town.id,
                                             result.joinedRawMonthlyPaxA,
                                             result.joinedMonthlyPaxA, reuseA, "A");
    probeOps += OpexAirCatchmentProbeEndpoint(catalog, stationB, airportB, plan.siteB.town.id,
                                             result.joinedRawMonthlyPaxB,
                                             result.joinedMonthlyPaxB, reuseB, "B");
    OpexAirCatchmentLog("AIR_CATCHMENT_BUILD",
        "arm=" + (("arm" in plan) ? plan.arm : "unknown")
        + " base_monthly=" + plan.monthlyPax
        + " reserve_stop_cost=" + (("joinedStopReserve" in plan) ? plan.joinedStopReserve : 0)
        + " actual_stop_cost=" + result.joinedStopCost + " stop_limit=" + AIR_JOINED_STOP_LIMIT
        + " stops_a=" + result.joinedStopsA + " stops_b=" + result.joinedStopsB
        + " model_joined_a=" + result.joinedMonthlyPaxA
        + " model_joined_b=" + result.joinedMonthlyPaxB
        + " model_joined_total=" + result.joinedMonthlyPax
        + " raw_joined_a=" + result.joinedRawMonthlyPaxA
        + " raw_joined_b=" + result.joinedRawMonthlyPaxB
        + " raw_joined_total=" + result.joinedRawMonthlyPax
        + " reuse_a=" + (reuseA ? 1 : 0) + " reuse_b=" + (reuseB ? 1 : 0)
        + " planned_capital=" + result.plannedCapital + " actual_cost=" + result.actualCost
        + " probe_ops=" + probeOps);
  }
  OpexAirReconcileActualBuild(catalog, plan, result);
  return result;
}
