/* Module AIR extrait de builder_air.nut (R11) : caches, couverture, catchment et shadow de demande B9/C118/C121. */
/* Generation transitoire : les curseurs gardent leur table entre tranches,
 * mais pas le droit de reutiliser une geometrie/concurrence invalidee. */
C121_CATALOG_ENDPOINT_EPOCH <- 0;

function OpexC121InvalidateEndpointGeometry()
{
  if (!C121_CATALOG_INCREMENTAL) return;
  C121_CATALOG_ENDPOINT_EPOCH++;
  AIR_C121_STATION_COVERAGE_CACHE.clear();
}

function OpexAirResetSiteCache()
{
  AIR_SITE_CACHE.clear();
  AIR_TERRITORIAL_COVERAGE_CACHE.clear();
  AIR_TERRITORIAL_COVERAGE_HITS = 0;
  AIR_TERRITORIAL_COVERAGE_MISSES = 0;
  AIR_STATION_COVERAGE_TOWN_CACHE.clear();
  AIR_C121_STATION_COVERAGE_CACHE.clear();
  if (C121_CATALOG_INCREMENTAL) OpexC121InvalidateEndpointGeometry();
  AIR_STATION_COVERAGE_HITS = 0;
  AIR_STATION_COVERAGE_MISSES = 0;
  if (AIR0310_SITE_VALIDITY_CACHE) OpexAir0310InvalidateSiteValidity();
}

function OpexAirResetTerritorialCoverageCache()
{
  AIR_TERRITORIAL_COVERAGE_CACHE.clear();
}

function OpexAirResetStationCoverageTownCache()
{
  AIR_STATION_COVERAGE_TOWN_CACHE.clear();
  AIR_C121_STATION_COVERAGE_CACHE.clear();
  if (C121_CATALOG_INCREMENTAL) OpexC121InvalidateEndpointGeometry();
}

/* V122 : validite OpexAirSiteStillBuildable par cle keyA/keyB.
 * month = annee * 12 + mois. entries[cle] = bool. limited = villes deja
 * au plafond ERR_STATION_TOO_MANY_STATIONS_IN_TOWN. Ce plafond est une
 * propriete de ville, mutee pendant le filtre : on le rejoue seulement
 * pour les cles absentes. Une reponse deja stockee, vraie ou fausse,
 * reste jusqu'au mois suivant ou jusqu'a un chantier/demolition d'OpexAI.
 * Un concurrent qui occupe ou libere la tuile n'est pas vu avant. Le
 * chantier sur un true perime passe par OpexAirLevelFootprint (depense
 * reelle possible) puis BuildAirport : echec AFAIL/BFAIL, sans aeroport
 * laisse par l'echec de pose ; rollback de A si B echoue ensuite, sauf
 * infrastructure_maintenance a 0. */
function OpexAir0310SiteValidityMonth()
{
  local date = AIDate.GetCurrentDate();
  return AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
}

function OpexAir0310InvalidateSiteValidity()
{
  if (!AIR0310_SITE_VALIDITY_CACHE) return;
  AIR0310_SITE_VALIDITY_STATE = null;
}

function OpexAir0310SiteValidityBegin(stationLimitedTowns)
{
  local month = OpexAir0310SiteValidityMonth();
  local state = AIR0310_SITE_VALIDITY_STATE;
  if (state == null || state.month != month) {
    state = { month = month, entries = {}, limited = {} };
    AIR0310_SITE_VALIDITY_STATE = state;
  }
  foreach (townId, ignored in state.limited) stationLimitedTowns.rawset(townId, true);
  return state;
}

function OpexAir0310SiteValidityOk(state, key, site, airport, plane, reuse, stationLimitedTowns)
{
  if (key in state.entries) return state.entries[key];
  local ok = OpexAirSiteStillBuildable(site, airport, plane, reuse, stationLimitedTowns);
  state.entries.rawset(key, ok);
  if (!reuse && !ok && site != null && ("town" in site) && site.town != null
      && ("id" in site.town) && (site.town.id in stationLimitedTowns)) {
    state.limited.rawset(site.town.id, true);
  }
  return ok;
}

/* Un test de site n'est qu'une prediction : si le chantier reel le contredit, ne jamais
 * re-servir exactement cette ancre au prochain rafraichissement. On efface seulement l'entree
 * qui pointe encore vers l'ancre refusee (un autre calcul peut deja l'avoir remplacee), afin de
 * forcer la recherche d'une alternative dans cette meme ville et pour ce meme type d'aeroport. */
function OpexAirInvalidateCachedSite(site, airport)
{
  if (!AIR_SITE_CACHE_ENABLED || site == null) return;
  local key = site.town.id + "_" + airport.type;
  if (key in AIR_SITE_CACHE && AIR_SITE_CACHE[key] == site.anchor) {
    delete AIR_SITE_CACHE[key];
    OpexAirResetTerritorialCoverageCache();
  }
}

/* Distance euclidienne exacte ÃƒÆ’Ã‚Â  vol d'oiseau pour la cinÃƒÆ’Ã‚Â©matique et le paiement aÃƒÆ’Ã‚Â©rien :
 * sqrt(dx^2 + dy^2) approximÃƒÆ’Ã‚Â© par 0.414 * min(dx, dy) + max(dx, dy) */
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

/* B9/G4 mesure uniquement : appartenance au catchment reel d'une emprise.
 * OpenTTD etend TileArea(width,height) de radius sur X et Y independamment ;
 * ce n'est pas le losange Manhattan utilise ailleurs pour le classement. */
function OpexAirB9TileInExpandedRect(tile, anchor, width, height, radius)
{
  if (!AIMap.IsValidTile(tile) || !AIMap.IsValidTile(anchor)) return false;
  local x = AIMap.GetTileX(tile);
  local y = AIMap.GetTileY(tile);
  local left = AIMap.GetTileX(anchor) - radius;
  local top = AIMap.GetTileY(anchor) - radius;
  local right = AIMap.GetTileX(anchor) + width - 1 + radius;
  local bottom = AIMap.GetTileY(anchor) + height - 1 + radius;
  return x >= left && x <= right && y >= top && y <= bottom;
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

/* C118 : couverture territoriale reelle, mais bornee au catchment deja choisi.
 * Une ville compte seulement si au moins une tuile productrice de passagers qui
 * lui appartient tombe dans le catchment. On ne parcourt jamais TownList. */
function OpexC118RememberTown(ids, seen, townId)
{
  if (townId < 0 || !AITown.IsValidTown(townId) || (townId in seen)) return;
  seen.rawset(townId, true);
  ids.append(townId);
}

function OpexC118StationCoverageTowns(stationId, cargo)
{
  local ids = [];
  if (stationId < 0 || !AIStation.IsValidStation(stationId) || cargo < 0) return ids;
  local key = stationId + "|" + cargo;
  if (key in AIR_STATION_COVERAGE_TOWN_CACHE) {
    AIR_STATION_COVERAGE_HITS++;
    return AIR_STATION_COVERAGE_TOWN_CACHE[key];
  }
  AIR_STATION_COVERAGE_MISSES++;
  local seen = {};
  local coverageTiles = AITileList_StationCoverage(stationId);
  coverageTiles.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
  coverageTiles.KeepAboveValue(0);
  coverageTiles.Valuate(AITile.GetClosestTown);
  foreach (tile, townId in coverageTiles) OpexC118RememberTown(ids, seen, townId);
  AIR_STATION_COVERAGE_TOWN_CACHE.rawset(key, ids);
  return ids;
}

function OpexC118EndpointCoverageTowns(site, airport, cargo, reused)
{
  local ids = [];
  if ((!C118_AIR_TERRITORIAL_EXPANSION && !C118_AIR_COVERAGE_PROBE
      && !C120_AIR_TERRITORIAL_RANKING)
      || site == null || airport == null || cargo < 0) return ids;
  local airportType = airport.type;
  if (reused && AIAirport.IsAirportTile(site.anchor)) airportType = AIAirport.GetAirportType(site.anchor);
  local cacheKey = reused ? "c118StationCoverageTowns"
      : "c118AirportCoverageTowns_" + airportType;
  if (cacheKey in site) return site[cacheKey];

  local seen = {};
  local stationId = (reused && ("stationId" in site)) ? site.stationId : -1;
  if (stationId >= 0 && AIStation.IsValidStation(stationId)) {
    ids = OpexC118StationCoverageTowns(stationId, cargo);
  } else {
    if (AIMap.IsValidTile(site.anchor) && AIAirport.IsValidAirportType(airportType)) {
      local globalKey = site.anchor + "|" + airportType + "|" + cargo;
      if (globalKey in AIR_TERRITORIAL_COVERAGE_CACHE) {
        AIR_TERRITORIAL_COVERAGE_HITS++;
        local cachedIds = AIR_TERRITORIAL_COVERAGE_CACHE[globalKey];
        site.rawset(cacheKey, cachedIds);
        return cachedIds;
      }
      AIR_TERRITORIAL_COVERAGE_MISSES++;
      local w = AIAirport.GetAirportWidth(airportType);
      local h = AIAirport.GetAirportHeight(airportType);
      local radius = AIAirport.GetAirportCoverageRadius(airportType);
      local ax = AIMap.GetTileX(site.anchor);
      local ay = AIMap.GetTileY(site.anchor);
      local minX = ax - radius;
      local minY = ay - radius;
      local maxX = ax + w - 1 + radius;
      local maxY = ay + h - 1 + radius;
      local mapX = AIMap.GetMapSizeX();
      local mapY = AIMap.GetMapSizeY();
      if (minX < 0) minX = 0;
      if (minY < 0) minY = 0;
      if (maxX >= mapX) maxX = mapX - 1;
      if (maxY >= mapY) maxY = mapY - 1;
      /* Meme rectangle et meme predicate que la double boucle historique, mais
       * l'evaluation du cargo est deleguee a AIList/Valuate. La boucle Squirrel
       * restante ne parcourt plus que les tuiles effectivement productrices. */
      local coverageTiles = AITileList();
      coverageTiles.AddRectangle(
          AIMap.GetTileIndex(minX, minY), AIMap.GetTileIndex(maxX, maxY));
      coverageTiles.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
      coverageTiles.KeepAboveValue(0);
      coverageTiles.Valuate(AITile.GetClosestTown);
      foreach (tile, townId in coverageTiles) {
        OpexC118RememberTown(ids, seen, townId);
      }
      AIR_TERRITORIAL_COVERAGE_CACHE.rawset(globalKey, ids);
    }
  }
  site.rawset(cacheKey, ids);
  return ids;
}

function OpexC118PlanCoverageTowns(plan, cargo)
{
  local ids = [];
  if ((!C118_AIR_TERRITORIAL_EXPANSION && !C118_AIR_COVERAGE_PROBE
      && !C120_AIR_TERRITORIAL_RANKING)
      || plan == null || !(("siteA") in plan)
      || !(("siteB") in plan) || !(("airport") in plan)) return ids;
  local seen = {};
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  foreach (townId in OpexC118EndpointCoverageTowns(plan.siteA, plan.airport, cargo, reuseA)) {
    OpexC118RememberTown(ids, seen, townId);
  }
  foreach (townId in OpexC118EndpointCoverageTowns(plan.siteB, plan.airport, cargo, reuseB)) {
    OpexC118RememberTown(ids, seen, townId);
  }
  return ids;
}

function OpexC118EngineFitsPlan(plan, plane)
{
  if (plan == null || plane == null) return false;
  if (("reuseA" in plan) && plan.reuseA && AIAirport.IsAirportTile(plan.siteA.anchor)
      && !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteA.anchor), plane.planeType)) return false;
  if (("reuseB" in plan) && plan.reuseB && AIAirport.IsAirportTile(plan.siteB.anchor)
      && !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteB.anchor), plane.planeType)) return false;
  return true;
}

function OpexC118OwnCoveredTownSet(cargo)
{
  local covered = {};
  if ((!C118_AIR_TERRITORIAL_EXPANSION && !C118_AIR_COVERAGE_PROBE
      && !C120_AIR_TERRITORIAL_RANKING) || cargo < 0) return covered;
  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    foreach (townId in OpexC118StationCoverageTowns(st, cargo)) covered.rawset(townId, true);
  }
  return covered;
}

/* Production de l'union reelle d'une station, pieces jointes comprises.
 * Chaque tuile est comptee une fois par AITileList_StationCoverage. */
function OpexAirStationCatchmentProduction(stationId, cargo)
{
  if (!AIStation.IsValidStation(stationId) || cargo < 0) return 0;
  if (EXP_OPCODE_EXACT_ON) return OpexAirStationCatchmentProductionActive(stationId, cargo);
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

/* B9/G4 : prediction passive des arrets joints d'un site neuf.
 * Meme geometrie, meme tri et meme anti-chevauchement que le chantier reel,
 * mais aucun ordre n'est execute. Le AITestMode ne sert qu'a eliminer les
 * orientations impossibles ; AIAccounting imbrique jette leur cout simule. */
function OpexAirB9PredictJoinedStops(site, airport, town, paxCargo)
{
  local chosen = [];
  if ((!B9_AIR_DEMAND_SHADOW && !C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS)
      || !AIR_JOINED_STOPS || AIR_JOINED_STOP_LIMIT <= 0
      || site == null || town == null || paxCargo < 0) return chosen;

  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local spread = AIGameSettings.GetValue("station.station_spread");
  if (spread < 4) spread = 12;
  local airportTile = site.anchor;
  local w = airport.width;
  local h = airport.height;
  local ax = AIMap.GetTileX(airportTile);
  local ay = AIMap.GetTileY(airportTile);
  local center = airportTile + AIMap.GetTileIndex(w / 2, h / 2);
  local minX = ax + w - spread;
  if (minX < 1) minX = 1;
  local maxX = ax + spread - 1;
  if (maxX >= mapX - 1) maxX = mapX - 2;
  local minY = ay + h - spread;
  if (minY < 1) minY = 1;
  local maxY = ay + spread - 1;
  if (maxY >= mapY - 1) maxY = mapY - 2;
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local airportCoverage = AIAirport.GetAirportCoverageRadius(airport.type);
  local dirs = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1),
    AIMap.GetTileIndex(-1, 0), AIMap.GetTileIndex(0, -1)
  ];
  local candidates = [];

  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(minX, minY), AIMap.GetTileIndex(maxX, maxY));
  tiles.Valuate(AIRoad.IsRoadTile);
  tiles.KeepValue(1);
  tiles.Valuate(AIRoad.IsRoadStationTile);
  tiles.KeepValue(0);
  tiles.Valuate(AIRoad.IsRoadDepotTile);
  tiles.KeepValue(0);
  tiles.Valuate(AITile.IsStationTile);
  tiles.KeepValue(0);
  tiles.Valuate(AITile.GetCargoProduction, paxCargo, 1, 1, coverage);
  tiles.KeepAboveValue(0);
  /* Meme intersection qu'avant, mais GetClosestTown ne tourne plus que sur
   * les routes productrices. KeepList conserve la valeur cargo de tiles. */
  local townRoad = AITileList();
  townRoad.AddList(tiles);
  townRoad.Valuate(AITile.GetClosestTown);
  townRoad.KeepValue(town.id);
  tiles.KeepList(townRoad);
  foreach (tile, val in tiles) {
    if (AIMap.DistanceManhattan(tile, center) < 3) continue;
    if (OpexAirDistanceToRect(tile, airportTile, w, h) <= airportCoverage) continue;
    candidates.append({
      tile = tile,
      value = val,
      dist = AIMap.DistanceManhattan(tile, town.tile)
    });
  }

  candidates.sort(function(a, b) {
    if (a.value > b.value) return -1;
    if (a.value < b.value) return 1;
    if (a.dist < b.dist) return -1;
    if (a.dist > b.dist) return 1;
    return 0;
  });
  local maxStops = AIR_JOINED_STOP_LIMIT;
  if (maxStops > 2) maxStops = 2;
  foreach (cand in candidates) {
    if (chosen.len() >= maxStops) break;
    local overlaps = false;
    foreach (prev in chosen) {
      if (AIMap.DistanceManhattan(cand.tile, prev) <= 2 * coverage) {
        overlaps = true;
        break;
      }
    }
    if (overlaps) continue;
    local buildable = false;
    foreach (dir in dirs) {
      local front = cand.tile + dir;
      if (!AIMap.IsValidTile(front) || !AIRoad.IsRoadTile(front)) continue;
      if (!AIRoad.AreRoadTilesConnected(cand.tile, front)) continue;
      local shield = AIAccounting();
      local test = AITestMode();
      local ok = AIRoad.BuildDriveThroughRoadStation(
          cand.tile, front, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
      test = null;
      shield = null;
      if (ok) {
        buildable = true;
        break;
      }
    }
    if (buildable) chosen.append(cand.tile);
  }
  return chosen;
}

/* Production mensuelle de LA ville couverte par l'union pre-build.
 * stationId >= 0 : union exacte d'un hub existant.
 * stationId < 0  : union geometrique aeroport + stops predicts du site neuf. */
function OpexAirB9TownCoverageTiles(town, airportTile, airportType, stopTiles, stationId = -1)
{
  local coverageTiles = AITileList();
  if (town == null || !AITown.IsValidTown(town.id)) return coverageTiles;
  if (stationId >= 0 && AIStation.IsValidStation(stationId)) {
    coverageTiles.AddList(AITileList_StationCoverage(stationId));
  } else {
    if (!AIMap.IsValidTile(airportTile) || !AIAirport.IsValidAirportType(airportType)) return coverageTiles;
    local w = AIAirport.GetAirportWidth(airportType);
    local h = AIAirport.GetAirportHeight(airportType);
    local airportRadius = AIAirport.GetAirportCoverageRadius(airportType);
    local busRadius = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    local mapX = AIMap.GetMapSizeX();
    local mapY = AIMap.GetMapSizeY();
    local left = AIMap.GetTileX(airportTile) - airportRadius;
    local right = AIMap.GetTileX(airportTile) + w - 1 + airportRadius;
    local top = AIMap.GetTileY(airportTile) - airportRadius;
    local bottom = AIMap.GetTileY(airportTile) + h - 1 + airportRadius;
    if (left < 0) left = 0;
    if (top < 0) top = 0;
    if (right >= mapX) right = mapX - 1;
    if (bottom >= mapY) bottom = mapY - 1;
    coverageTiles.AddRectangle(
        AIMap.GetTileIndex(left, top), AIMap.GetTileIndex(right, bottom));
    foreach (stop in stopTiles) {
      local sx = AIMap.GetTileX(stop);
      local sy = AIMap.GetTileY(stop);
      local stopLeft = sx - busRadius;
      local stopRight = sx + busRadius;
      local stopTop = sy - busRadius;
      local stopBottom = sy + busRadius;
      if (stopLeft < 0) stopLeft = 0;
      if (stopTop < 0) stopTop = 0;
      if (stopRight >= mapX) stopRight = mapX - 1;
      if (stopBottom >= mapY) stopBottom = mapY - 1;
      coverageTiles.AddRectangle(
          AIMap.GetTileIndex(stopLeft, stopTop), AIMap.GetTileIndex(stopRight, stopBottom));
    }
  }
  return coverageTiles;
}

/* NoAI expose le rating gare+cargo en pourcentage via ToPercent8(byte).
 * Inverser l'intervalle exact et prendre son milieu minimise l'erreur rendue
 * inevitable par l'API (au plus quelques points sur 255), sans calibration. */
function OpexC121RatingPercentToByteMid(pct)
{
  if (pct < 0) return 0;
  if (pct > 100) pct = 100;
  local low = (pct * 256 + 100) / 101;
  local high = (((pct + 1) * 256 + 100) / 101) - 1;
  if (low < 0) low = 0;
  if (high > 255) high = 255;
  if (high < low) high = low;
  return (low + high) / 2;
}

/* Topologie exacte d'une gare existante. Le filtrage ville/cargo est deja fait
 * sur `weights` par B9 ; refaire GetCargoProduction + GetClosestTown ici serait
 * redondant et multipliait le cout par endpoint et cargo. */
function OpexC121StationCoverageTiles(stationId)
{
  local empty = [];
  if (!AIStation.IsValidStation(stationId)) return empty;
  if (stationId in AIR_C121_STATION_COVERAGE_CACHE) return AIR_C121_STATION_COVERAGE_CACHE[stationId];

  local out = [];
  local tiles = AITileList_StationCoverage(stationId);
  foreach (tile, value in tiles) out.append(tile);
  AIR_C121_STATION_COVERAGE_CACHE.rawset(stationId, out);
  return out;
}

/* OpenTTD 15.3 MoveGoodsToStation, cas mono-compagnie du banc C121 :
 * - le meilleur rating de la compagnie determine la fraction de production
 *   qui entre dans son reseau ;
 * - a l'interieur de la compagnie, les gares couvrant la tuile se partagent
 *   cette production proportionnellement a leur rating.
 *
 * B9 groupe ici les tuiles productrices par (somme,max) des ratings des gares
 * EXISTANTES concurrentes. La gare candidate est exclue si elle est reutilisee
 * car son rating projete la remplacera dans OpexC121StationAllocatedMonthly(). */
/* Foreign GetAirportType/GetCargoRating are unavailable. This candidate uses
 * only visible airport tiles and owners, a small-airport catchment prior and
 * equal company-best ratings. Potential coverage, not exact service eligibility.
 * A company is counted once per source, regardless of its number of airports. */
function OpexC121VisibleAirportOwners(minX, minY, maxX, maxY)
{
  local key = minX + "|" + minY + "|" + maxX + "|" + maxY;
  local now = AIDate.GetCurrentDate();
  if (key in C121_VISIBLE_AIRPORT_CACHE) {
    local cached = C121_VISIBLE_AIRPORT_CACHE[key];
    if (now >= cached.date && now - cached.date < 30) return cached.owners;
  }
  local radius = AIAirport.GetAirportCoverageRadius(AIAirport.AT_SMALL);
  local owners = {};
  if (radius < 0) return owners;
  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  local tiles = AITileList();
  /* AddRectangle rejects the entire list if either corner is an invalid map
   * border tile. Producers/airport facilities cannot occupy these borders. */
  tiles.AddRectangle(AIMap.GetTileIndex(minX-radius < 1 ? 1 : minX-radius,
      minY-radius < 1 ? 1 : minY-radius),
      AIMap.GetTileIndex(maxX+radius >= width-1 ? width-2 : maxX+radius,
      maxY+radius >= height-1 ? height-2 : maxY+radius));
  tiles.Valuate(AIAirport.IsAirportTile);
  tiles.KeepValue(1);
  local self = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  foreach (tile, unused in tiles) {
    local owner = AITile.GetOwner(tile);
    if (owner == self || owner == AICompany.COMPANY_INVALID
        || AICompany.ResolveCompanyID(owner) != owner) continue;
    local x = AIMap.GetTileX(tile);
    local y = AIMap.GetTileY(tile);
    local left = x-radius > minX ? x-radius : minX;
    local right = x+radius < maxX ? x+radius : maxX;
    local top = y-radius > minY ? y-radius : minY;
    local bottom = y+radius < maxY ? y+radius : maxY;
    for (local yy = top; yy <= bottom; yy++) for (local xx = left; xx <= right; xx++) {
      local source = AIMap.GetTileIndex(xx, yy);
      if (!(source in owners)) owners.rawset(source, {});
      owners[source].rawset(owner, true);
    }
  }
  if (C121_VISIBLE_AIRPORT_CACHE.len() >= 256) C121_VISIBLE_AIRPORT_CACHE.clear();
  C121_VISIBLE_AIRPORT_CACHE.rawset(key, { date = now, owners = owners });
  return owners;
}

function OpexC121StationCompetitionBuckets(town, cargo, cargoTiles, candidateStationId = -1)
{
  local result = { buckets = [], totalWeight = 0, competingWeight = 0, competingStations = 0, rivalWeight = 0 };
  if ((!C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS)
      || town == null || !AITown.IsValidTown(town.id) || cargo < 0 || cargoTiles == null) return result;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local minX = mapX;
  local minY = mapY;
  local maxX = -1;
  local maxY = -1;
  foreach (tile, producedHere in cargoTiles) {
    if (producedHere <= 0) continue;
    result.totalWeight += producedHere;
    local x = AIMap.GetTileX(tile);
    local y = AIMap.GetTileY(tile);
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  if (result.totalWeight <= 0 || maxX < minX || maxY < minY) return result;

  /* BaseStation::xy est le premier facility tile de la gare. OpenTTD refuse
   * ensuite toute extension dont le rectangle depasse station_spread. Meme si
   * ce premier tile est retire plus tard, chaque facility qui subsiste a donc
   * ete construit a au plus spread-1 cases par axe de xy. En ajoutant le rayon
   * de catchment reel de la gare, on obtient une borne spatiale conservatrice
   * exacte avant de materialiser son AITileList_StationCoverage. */
  local spread = AIGameSettings.GetValue("station.station_spread");
  if (spread < 1) spread = 1;
  local sums = {};
  local maxima = {};
  local stations = AIStationList(AIStation.STATION_ANY);
  for (local st = stations.Begin(); !stations.IsEnd(); st = stations.Next()) {
    if (st == candidateStationId || !AIStation.HasCargoRating(st, cargo)) continue;
    local pct = AIStation.GetCargoRating(st, cargo);
    if (pct < 0) continue;
    local rating = OpexC121RatingPercentToByteMid(pct);
    if (rating <= 0) continue;
    local loc = AIStation.GetLocation(st);
    if (!AIMap.IsValidTile(loc)) continue;
    local radius = AIStation.GetStationCoverageRadius(st);
    if (radius < 0) radius = 0;
    local reach = (spread - 1) + radius;
    local sx = AIMap.GetTileX(loc);
    local sy = AIMap.GetTileY(loc);
    if (sx + reach < minX || sx - reach > maxX || sy + reach < minY || sy - reach > maxY) continue;

    local touched = false;
    foreach (tile in OpexC121StationCoverageTiles(st)) {
      if (!cargoTiles.HasItem(tile)) continue;
      local sum = (tile in sums) ? sums[tile] : 0;
      sums.rawset(tile, sum + rating);
      local oldMax = (tile in maxima) ? maxima[tile] : 0;
      if (rating > oldMax) maxima.rawset(tile, rating);
      touched = true;
    }
    if (touched) result.competingStations++;
  }

  local grouped = {};
  local rivalOwners = (C121_AIR_VISIBLE_COMPETITION && AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS))
      ? OpexC121VisibleAirportOwners(minX, minY, maxX, maxY) : {};
  result.rivalWeight = 0;
  foreach (tile, producedHere in cargoTiles) {
    if (producedHere <= 0) continue;
    local sum = (tile in sums) ? sums[tile] : 0;
    local maxRating = (tile in maxima) ? maxima[tile] : 0;
    if (sum > 0) result.competingWeight += producedHere;
    local rivals = tile in rivalOwners ? rivalOwners[tile].len() : 0;
    if (rivals > 0) result.rivalWeight += producedHere;
    local key = sum + "|" + maxRating + "|" + rivals;
    if (!(key in grouped)) grouped.rawset(key, { sum = sum, maxRating = maxRating, weight = 0, rivals = rivals });
    grouped[key].weight += producedHere;
  }
  foreach (key, bucket in grouped) result.buckets.append(bucket);
  return result;
}

/* Fraction mensuelle allouee a la gare candidate par MoveGoodsToStation.
 * rawMonthly est la production B9 situee dans son catchment avant rating.
 * Pour une tuile sans autre gare : (r+1)/256.
 * Avec d'autres gares de la meme compagnie :
 *   (max(r,m)+1)/256 * r/(r+S).
 * Aucune constante ajustee aux seeds n'intervient. */
function OpexC121StationAllocatedMonthly(rawMonthly, rating, competition)
{
  if (rawMonthly <= 0.0 || rating <= 0) return 0.0;
  if (competition == null || !("totalWeight" in competition)
      || competition.totalWeight <= 0 || !("buckets" in competition)) {
    return rawMonthly.tofloat() * (rating + 1).tofloat() / 256.0;
  }
  local weighted = 0.0;
  foreach (bucket in competition.buckets) {
    if (bucket == null || bucket.weight <= 0) continue;
    local best = rating > bucket.maxRating ? rating : bucket.maxRating;
    local denom = rating + bucket.sum;
    if (denom <= 0) continue;
    local sourceFraction = (best + 1).tofloat() / 256.0;
    local stationShare = rating.tofloat() / denom.tofloat();
    local companies = ("rivals" in bucket) ? 1 + bucket.rivals : 1;
    weighted += bucket.weight.tofloat() * sourceFraction * stationShare / companies.tofloat();
  }
  return rawMonthly.tofloat() * weighted / competition.totalWeight.tofloat();
}

function OpexAirB9TownUnionMonthly(town, airportTile, airportType, cargo, stopTiles,
                                  stationId = -1, sharedCoverageTiles = null)
{
  local out = {
    monthly = 0, produced = 0, townTiles = 0, coveredTiles = 0,
    competition = null
  };
  if (town == null || !AITown.IsValidTown(town.id) || cargo < 0) return out;
  local pop = AITown.GetPopulation(town.id);
  local townRadius = 4 + (sqrt(pop > 0 ? pop : 0) / 8).tointeger();
  if (townRadius > 20) townRadius = 20;
  local townTile = AITown.GetLocation(town.id);
  out.townTiles = AITile.GetCargoProduction(townTile, cargo, 1, 1, townRadius);
  if (out.townTiles < 0) out.townTiles = 0;
  out.produced = AITown.GetLastMonthProduction(town.id, cargo);
  if (out.produced < 0) out.produced = 0;

  local geometry = sharedCoverageTiles;
  if (geometry == null) {
    geometry = OpexAirB9TownCoverageTiles(
        town, airportTile, airportType, stopTiles, stationId);
  }
  local cargoTiles = AITileList();
  cargoTiles.AddList(geometry);
  cargoTiles.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
  cargoTiles.KeepAboveValue(0);
  /* Ne demander GetClosestTown qu'aux tuiles qui produisent reellement ce
   * cargo. KeepList conserve les valeurs de production de cargoTiles. Cela
   * donne exactement geometry ∩ producer ∩ target-town, mais evite de
   * valoriser toutes les tuiles vides du catchment. */
  local townOwned = AITileList();
  townOwned.AddList(cargoTiles);
  townOwned.Valuate(AITile.GetClosestTown);
  townOwned.KeepValue(town.id);
  cargoTiles.KeepList(townOwned);
  foreach (tile, producedHere in cargoTiles) out.coveredTiles += producedHere;
  out.competition = OpexC121StationCompetitionBuckets(town, cargo, cargoTiles, stationId);
  local usable = out.coveredTiles;
  if (out.townTiles > 0 && usable > out.townTiles) usable = out.townTiles;
  if (out.townTiles > 0) out.monthly = (out.produced * usable) / out.townTiles;
  return out;
}

/* Metadonnees separees de la cle physique : remplacer une entree perimee
 * plutot qu'accumuler une entree par revision pendant un long scan. */
function OpexC121EndpointCacheStamp(townId, stationId)
{
  return {
    town = townId in C121_CATALOG_TOWN_REV ? C121_CATALOG_TOWN_REV[townId] : 0,
    station = stationId in C121_CATALOG_STATION_REV ? C121_CATALOG_STATION_REV[stationId] : 0,
    geometry = C121_CATALOG_ENDPOINT_EPOCH,
    date = AIDate.GetCurrentDate(),
  };
}

function OpexC121EndpointCacheFresh(result, stamp)
{
  if (!("catalogStamp" in result)) return false;
  local old = result.catalogStamp;
  return old.town == stamp.town && old.station == stamp.station
      && old.geometry == stamp.geometry && stamp.date >= old.date
      && stamp.date - old.date < 365;
}

function OpexAirB9DemandShadowEndpointCargo(catalog, plan, site, reused, cargo,
                                           stopTiles = null, sharedCoverageTiles = null)
{
  local result = {
    airportMonthly = 0, unionMonthly = 0, unionAllocated = 0,
    routeDiv = 1, predictedStops = 0, produced = 0,
    townTiles = 0, unionTiles = 0, stopTiles = [], coverageTiles = null,
    competition = null,
    predictTicks = 0, coverageTicks = 0, unionTicks = 0
  };
  if (site == null || !("town" in site) || site.town == null || cargo < 0) return result;
  local airportType = plan.airport.type;
  if (reused && AIAirport.IsAirportTile(site.anchor)) {
    airportType = AIAirport.GetAirportType(site.anchor);
  }
  local cacheKey = null;
  local cacheStamp = null;
  local cached = null;
  local forceRefresh = false;
  if (C121_AIR_ECONOMICS && C121_AIR_ENDPOINT_CACHE != null) {
    local anchorKey = ("anchor" in site) ? site.anchor : -1;
    local townKey = ("town" in site) && site.town != null && ("id" in site.town) ? site.town.id : -1;
    local routesKey = reused && ("routes" in site) ? site.routes : 0;
    local stationKey = reused && ("stationId" in site) ? site.stationId : -1;
    cacheKey = cargo + "|" + airportType + "|" + anchorKey + "|" + townKey
        + "|" + (reused ? 1 : 0) + "|" + routesKey + "|" + stationKey;
    if (C121_CATALOG_INCREMENTAL) cacheStamp = OpexC121EndpointCacheStamp(townKey, stationKey);
    forceRefresh = C121_CATALOG_INCREMENTAL
      && ("c121CatalogRefreshEndpoints" in plan) && plan.c121CatalogRefreshEndpoints;
    if (cacheKey in C121_AIR_ENDPOINT_CACHE) cached = C121_AIR_ENDPOINT_CACHE[cacheKey];
    if (!forceRefresh && cached != null
      && (cacheStamp == null || OpexC121EndpointCacheFresh(cached, cacheStamp))
      && (!C121_AIR_VISIBLE_COMPETITION || ("visibleDate" in cached)
          && AIDate.GetCurrentDate() >= cached.visibleDate && AIDate.GetCurrentDate() - cached.visibleDate < 30)) {
      if (C121_AIR_PLAN_PERF != null) C121_AIR_PLAN_PERF.endpointHits++;
      return cached;
    }
    if (C121_AIR_PLAN_PERF != null) C121_AIR_PLAN_PERF.endpointMisses++;
  }
  /* airportOnly ne sert qu'au log/probe B9. Le recalculer dans le shadow
   * C121 pur doublait le scan geometrique pour chaque cargo et extremite. */
  local airportOnly = { monthly = 0 };
  if (AIR_CATCHMENT_PROBE) {
    airportOnly = OpexAirB9TownUnionMonthly(
        site.town, site.anchor, airportType, cargo, [], -1);
  }
  local stops = stopTiles == null ? [] : stopTiles;
  local stationId = -1;
  if (reused) {
    if ("stationId" in site) stationId = site.stationId;
  } else if (stopTiles == null) {
    /* Les arrets reels sont choisis sur les passagers. Le MAIL doit reutiliser
     * exactement cette meme geometrie de station, pas choisir ses propres stops. */
    local tPredict0 = AIController.GetTick();
    stops = OpexAirB9PredictJoinedStops(site, plan.airport, site.town, catalog.paxCargo);
    result.predictTicks = AIController.GetTick() - tPredict0;
  }
  local coverageTiles = sharedCoverageTiles;
  if (coverageTiles == null) {
    local tCoverage0 = AIController.GetTick();
    coverageTiles = OpexAirB9TownCoverageTiles(
        site.town, site.anchor, airportType, stops, stationId);
    result.coverageTicks = AIController.GetTick() - tCoverage0;
  }
  local tUnion0 = AIController.GetTick();
  local union = OpexAirB9TownUnionMonthly(
      site.town, site.anchor, airportType, cargo, stops, stationId, coverageTiles);
  result.unionTicks = AIController.GetTick() - tUnion0;
  local routeDiv = reused && ("routes" in site) ? site.routes + 1 : 1;
  result.airportMonthly = airportOnly.monthly / routeDiv;
  result.unionMonthly = union.monthly;
  result.unionAllocated = union.monthly / routeDiv;
  result.routeDiv = routeDiv;
  result.predictedStops = stops.len();
  result.produced = union.produced;
  result.townTiles = union.townTiles;
  result.unionTiles = union.coveredTiles;
  result.competition = union.competition;
  if (C121_AIR_VISIBLE_COMPETITION) result.visibleDate <- AIDate.GetCurrentDate();
  result.stopTiles = stops;
  result.coverageTiles = coverageTiles;
  if (cacheStamp != null) result.catalogStamp <- cacheStamp;
  if (cacheKey != null) C121_AIR_ENDPOINT_CACHE.rawset(cacheKey, result);
  return result;
}

function OpexAirB9DemandShadowEndpoint(catalog, plan, site, reused)
{
  return OpexAirB9DemandShadowEndpointCargo(
      catalog, plan, site, reused, catalog.paxCargo, null);
}

/* C121 : observation O(1) du rating gare+cargo deja en place.
 * Elle ne sert qu'aux hubs reutilises ; une gare neuve n'a pas encore de rating. */
function OpexC121ExistingStationRating(site, reused, cargo)
{
  if (!reused || site == null || cargo < 0) return -1;
  local stationId = ("stationId" in site) ? site.stationId : -1;
  if (!AIStation.IsValidStation(stationId) && ("anchor" in site)
      && AIMap.IsValidTile(site.anchor)) {
    stationId = AIStation.GetStationID(site.anchor);
  }
  if (!AIStation.IsValidStation(stationId)) return -1;
  return AIStation.GetCargoRating(stationId, cargo);
}

function OpexAirB9DemandShadow(catalog, plan)
{
  if ((!B9_AIR_DEMAND_SHADOW && !C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS)
      || plan == null
      || !("siteA" in plan) || !("siteB" in plan)) return null;
  if (!AIR_CATCHMENT_PROBE && !C117_AIR_THROUGHPUT_PROBE
      && !C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS) return null;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;
  local tA0 = AIController.GetTick();
  local oA0 = AIController.GetOpsTillSuspend();
  local a = OpexAirB9DemandShadowEndpoint(catalog, plan, plan.siteA, reuseA);
  local tA1 = AIController.GetTick();
  local oA1 = AIController.GetOpsTillSuspend();
  local tB0 = tA1;
  local oB0 = oA1;
  local b = OpexAirB9DemandShadowEndpoint(catalog, plan, plan.siteB, reuseB);
  local tB1 = AIController.GetTick();
  local oB1 = AIController.GetOpsTillSuspend();
  local shadowMonthly = a.unionAllocated + b.unionAllocated;
  plan.b9ShadowMonthly <- shadowMonthly;
  if (C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
    local mailCargo = ("mailCargo" in catalog) ? catalog.mailCargo : -1;
    local tMa0 = tB1;
    local oMa0 = oB1;
    local ma = OpexAirB9DemandShadowEndpointCargo(
        catalog, plan, plan.siteA, reuseA, mailCargo, a.stopTiles, a.coverageTiles);
    local tMa1 = AIController.GetTick();
    local oMa1 = AIController.GetOpsTillSuspend();
    local tMb0 = tMa1;
    local oMb0 = oMa1;
    local mb = OpexAirB9DemandShadowEndpointCargo(
        catalog, plan, plan.siteB, reuseB, mailCargo, b.stopTiles, b.coverageTiles);
    local tMb1 = AIController.GetTick();
    local oMb1 = AIController.GetOpsTillSuspend();
    local currentPaxRatingA = OpexC121ExistingStationRating(plan.siteA, reuseA, catalog.paxCargo);
    local currentPaxRatingB = OpexC121ExistingStationRating(plan.siteB, reuseB, catalog.paxCargo);
    local currentMailRatingA = OpexC121ExistingStationRating(plan.siteA, reuseA, mailCargo);
    local currentMailRatingB = OpexC121ExistingStationRating(plan.siteB, reuseB, mailCargo);
    plan.c121Demand <- {
      paxA = a.unionAllocated, paxB = b.unionAllocated,
      mailA = ma.unionAllocated, mailB = mb.unionAllocated,
      paxRawA = a.unionMonthly, paxRawB = b.unionMonthly,
      mailRawA = ma.unionMonthly, mailRawB = mb.unionMonthly,
      paxProducedA = a.produced, paxProducedB = b.produced,
      mailProducedA = ma.produced, mailProducedB = mb.produced,
      routeDivA = a.routeDiv, routeDivB = b.routeDiv,
      paxTownTilesA = a.townTiles, paxTownTilesB = b.townTiles,
      mailTownTilesA = ma.townTiles, mailTownTilesB = mb.townTiles,
      paxUnionTilesA = a.unionTiles, paxUnionTilesB = b.unionTiles,
      mailUnionTilesA = ma.unionTiles, mailUnionTilesB = mb.unionTiles,
      predictedStopsA = a.predictedStops, predictedStopsB = b.predictedStops,
      currentPaxRatingA = currentPaxRatingA, currentPaxRatingB = currentPaxRatingB,
      currentMailRatingA = currentMailRatingA, currentMailRatingB = currentMailRatingB,
      paxCompetitionA = a.competition, paxCompetitionB = b.competition,
      mailCompetitionA = ma.competition, mailCompetitionB = mb.competition,
      paxPredictTicksA = a.predictTicks, paxPredictTicksB = b.predictTicks,
      paxCoverageTicksA = a.coverageTicks, paxCoverageTicksB = b.coverageTicks,
      paxUnionTicksA = a.unionTicks, paxUnionTicksB = b.unionTicks,
      mailUnionTicksA = ma.unionTicks, mailUnionTicksB = mb.unionTicks,
      paxTicksA = tA1 - tA0, paxTicksB = tB1 - tB0,
      mailTicksA = tMa1 - tMa0, mailTicksB = tMb1 - tMb0,
      paxOpsA = tA1 == tA0 ? oA0 - oA1 : -1,
      paxOpsB = tB1 == tB0 ? oB0 - oB1 : -1,
      mailOpsA = tMa1 == tMa0 ? oMa0 - oMa1 : -1,
      mailOpsB = tMb1 == tMb0 ? oMb0 - oMb1 : -1,
    };
  }
  if (AIR_CATCHMENT_PROBE) OpexAirCatchmentLog("AIR_DEMAND_SHADOW",
      "arm=" + (("arm" in plan) ? plan.arm : "unknown")
      + " town_a=" + plan.siteA.town.id + " town_b=" + plan.siteB.town.id
      + " anchor_a=" + plan.siteA.anchor + " anchor_b=" + plan.siteB.anchor
      + " reuse_a=" + (reuseA ? 1 : 0) + " reuse_b=" + (reuseB ? 1 : 0)
      + " route_div_a=" + a.routeDiv + " route_div_b=" + b.routeDiv
      + " base_monthly=" + plan.monthlyPax
      + " airport_monthly_a=" + a.airportMonthly + " airport_monthly_b=" + b.airportMonthly
      + " union_monthly_a=" + a.unionAllocated + " union_monthly_b=" + b.unionAllocated
      + " shadow_monthly=" + shadowMonthly
      + " raw_union_a=" + a.unionMonthly + " raw_union_b=" + b.unionMonthly
      + " predicted_stops_a=" + a.predictedStops + " predicted_stops_b=" + b.predictedStops
      + " town_prod_a=" + a.produced + " town_prod_b=" + b.produced
      + " town_tiles_a=" + a.townTiles + " town_tiles_b=" + b.townTiles
      + " union_tiles_a=" + a.unionTiles + " union_tiles_b=" + b.unionTiles);
  return shadowMonthly;
}

function OpexC121PrepareDemandShadow(catalog, plan, lines = null)
{
  if ((!B9_AIR_DEMAND_SHADOW && !C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS)
      || plan == null) return null;
  /* En mode causal, la generation du projet a deja paye ce calcul avant le
   * choix moteur. Le build doit reutiliser exactement le meme etat, pas rescanner
   * les catchments/gares quelques ticks plus tard et casser le contrat
   * moteur -> flotte -> economie -> projet. */
  if (C121_AIR_ECONOMICS && ("c121Demand" in plan)
      && ("c121ServiceA" in plan) && ("c121ServiceB" in plan)) {
    return ("b9ShadowMonthly" in plan) ? plan.b9ShadowMonthly : null;
  }
  local tick0 = AIController.GetTick();
  local ops0 = AIController.GetOpsTillSuspend();
  local value = OpexAirB9DemandShadow(catalog, plan);
  if (C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
    plan.c121ServiceA <- OpexC121ExistingStationService(catalog, plan.siteA, lines);
    plan.c121ServiceB <- OpexC121ExistingStationService(catalog, plan.siteB, lines);
    local tick1 = AIController.GetTick();
    local ops1 = AIController.GetOpsTillSuspend();
    plan.c121DemandTicks <- tick1 - tick0;
    plan.c121DemandOps <- OpexAirCalcDeltaOps(tick0, ops0);
  }
  return value;
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
  local townAirportPaxTiles = 0;
  local townAirportMailTiles = 0;
  local townUnionPaxTiles = 0;
  local townUnionMailTiles = 0;
  local unionTiles = 0;
  local townCenterInUnion = false;
  local coverageTiles = AITileList_StationCoverage(stationId);
  foreach (coverageTile, value in coverageTiles) {
    unionTiles++;
    if (coverageTile == townTile) townCenterInUnion = true;
    local paxHere = AITile.GetCargoProduction(coverageTile, catalog.paxCargo, 1, 1, 0);
    unionPax += paxHere;
    local mailHere = 0;
    if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
      mailHere = AITile.GetCargoProduction(coverageTile, catalog.mailCargo, 1, 1, 0);
      unionMail += mailHere;
    }
    /* GetCargoProduction compte des tuiles productrices, pas un volume mensuel.
     * Estimer passivement la part de production de cette ville captee par le site. */
    if (AITile.GetClosestTown(coverageTile) == townId) {
      townUnionPaxTiles += paxHere;
      townUnionMailTiles += mailHere;
      if (OpexAirB9TileInExpandedRect(
          coverageTile, airportTile, w, h, airportRadius)) {
        townAirportPaxTiles += paxHere;
        townAirportMailTiles += mailHere;
      }
    }
  }
  local townPop = AITown.GetPopulation(townId);
  local townRadius = 4 + (sqrt(townPop > 0 ? townPop : 0) / 8).tointeger();
  if (townRadius > 20) townRadius = 20;
  local townPaxTiles = AITile.GetCargoProduction(townTile, catalog.paxCargo, 1, 1, townRadius);
  if (townPaxTiles < 0) townPaxTiles = 0;
  local townPaxMonth = AITown.GetLastMonthProduction(townId, catalog.paxCargo);
  if (townPaxMonth < 0) townPaxMonth = 0;
  local townPaxTransportedPct = AITown.GetLastMonthTransportedPercentage(townId, catalog.paxCargo);
  if (townPaxTransportedPct < 0) townPaxTransportedPct = 0;
  local townMailTiles = 0;
  local townMailMonth = 0;
  local townMailTransportedPct = 0;
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    townMailTiles = AITile.GetCargoProduction(townTile, catalog.mailCargo, 1, 1, townRadius);
    if (townMailTiles < 0) townMailTiles = 0;
    townMailMonth = AITown.GetLastMonthProduction(townId, catalog.mailCargo);
    if (townMailMonth < 0) townMailMonth = 0;
    townMailTransportedPct = AITown.GetLastMonthTransportedPercentage(townId, catalog.mailCargo);
    if (townMailTransportedPct < 0) townMailTransportedPct = 0;
  }
  local airportPaxTilesForEstimate = townAirportPaxTiles;
  if (townPaxTiles > 0 && airportPaxTilesForEstimate > townPaxTiles) airportPaxTilesForEstimate = townPaxTiles;
  local unionPaxTilesForEstimate = townUnionPaxTiles;
  if (townPaxTiles > 0 && unionPaxTilesForEstimate > townPaxTiles) unionPaxTilesForEstimate = townPaxTiles;
  local airportPaxMonthEst = townPaxTiles > 0 ? (townPaxMonth * airportPaxTilesForEstimate) / townPaxTiles : 0;
  local unionPaxMonthEst = townPaxTiles > 0 ? (townPaxMonth * unionPaxTilesForEstimate) / townPaxTiles : 0;
  local airportMailTilesForEstimate = townAirportMailTiles;
  if (townMailTiles > 0 && airportMailTilesForEstimate > townMailTiles) airportMailTilesForEstimate = townMailTiles;
  local unionMailTilesForEstimate = townUnionMailTiles;
  if (townMailTiles > 0 && unionMailTilesForEstimate > townMailTiles) unionMailTilesForEstimate = townMailTiles;
  local airportMailMonthEst = townMailTiles > 0 ? (townMailMonth * airportMailTilesForEstimate) / townMailTiles : 0;
  local unionMailMonthEst = townMailTiles > 0 ? (townMailMonth * unionMailTilesForEstimate) / townMailTiles : 0;
  local marginalPax = unionPax - airportPax;
  if (marginalPax < 0) marginalPax = 0;
  local marginalMail = unionMail - airportMail;
  if (marginalMail < 0) marginalMail = 0;
  local rawMinusTrue = reused ? 0 : rawJoinedPax - marginalPax;
  local modelMinusTrue = reused ? 0 : modelJoinedPax - marginalPax;
  local rectDistance = OpexAirDistanceToRect(townTile, airportTile, w, h);
  local townCenterInAirport = OpexAirB9TileInExpandedRect(
      townTile, airportTile, w, h, airportRadius);
  local airportCenter = airportTile + AIMap.GetTileIndex(w / 2, h / 2);
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - t0;
  local probeOps = elapsed <= 0
      ? l0 - left
      : l0 + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
  OpexAirCatchmentLog("AIR_CATCHMENT_ENDPOINT",
      "endpoint=" + endpoint + " station=" + stationId + " town=" + townId
      + " town_tile=" + townTile + " town_pop=" + townPop
      + " airport_tile=" + airportTile + " airport_type=" + airportType
      + " airport_w=" + w + " airport_h=" + h + " airport_radius=" + airportRadius
      + " airport_generic_radius=" + AIStation.GetCoverageRadius(AIStation.STATION_AIRPORT)
      + " bus_radius=" + AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP)
      + " rect_distance=" + rectDistance
      + " center_distance=" + AIMap.DistanceManhattan(townTile, airportCenter)
      + " town_center_airport=" + (townCenterInAirport ? 1 : 0)
      + " town_center_union=" + (townCenterInUnion ? 1 : 0)
      + " coverage_tiles=" + unionTiles
      + " airport_pax_prod=" + airportPax + " union_pax_prod=" + unionPax
      + " airport_pax_tiles=" + airportPax + " union_pax_tiles=" + unionPax
      + " town_pax_tiles=" + townPaxTiles
      + " town_airport_pax_tiles=" + townAirportPaxTiles
      + " town_union_pax_tiles=" + townUnionPaxTiles
      + " town_pax_month=" + townPaxMonth
      + " town_pax_transported_pct=" + townPaxTransportedPct
      + " airport_pax_month_est=" + airportPaxMonthEst
      + " union_pax_month_est=" + unionPaxMonthEst
      + " joined_marginal_pax=" + marginalPax
      + " joined_marginal_pax_tiles=" + marginalPax
      + " model_joined_pax=" + modelJoinedPax + " raw_joined_pax=" + rawJoinedPax
      + " model_joined_pax_tiles=" + modelJoinedPax + " raw_joined_pax_tiles=" + rawJoinedPax
      + " overlap_overcount_pax=" + (rawMinusTrue > 0 ? rawMinusTrue : 0)
      + " raw_undercount_pax=" + (rawMinusTrue < 0 ? -rawMinusTrue : 0)
      + " model_error_pax=" + modelMinusTrue
      + " airport_mail_prod=" + airportMail + " union_mail_prod=" + unionMail
      + " airport_mail_tiles=" + airportMail + " union_mail_tiles=" + unionMail
      + " town_mail_tiles=" + townMailTiles
      + " town_airport_mail_tiles=" + townAirportMailTiles
      + " town_union_mail_tiles=" + townUnionMailTiles
      + " town_mail_month=" + townMailMonth
      + " town_mail_transported_pct=" + townMailTransportedPct
      + " airport_mail_month_est=" + airportMailMonthEst
      + " union_mail_month_est=" + unionMailMonthEst
      + " joined_marginal_mail=" + marginalMail
      + " reused=" + (reused ? 1 : 0) + " probe_ops=" + probeOps);
  return probeOps;
}
