/* Etage 3b : une liaison aerienne passagers, sans pathfinding.
 *
 * L'avion est le contrepoint du rail : il n'y a pas de recherche A*, mais les aires de
 * construction et la compatibilite aeroport/appareil sont des preconditions reelles.
 * Regle : 2 types principaux d'avions et d'aeroports (les gros et les petits).
 * Les gros avions ne vont QUE dans les grands aeroports.
 * La construction elle-meme est transactionnelle : avion vendu, puis aeroports
 * retires, au moindre echec apres le premier aeroport.
 */

AIR_HUB_NEW_SITE_POOL <- 12;
AIR_SITE_RADIUS <- 25;
AIR_TOWN_MIN_DISTANCE <- 32;
AIR_MAX_SITE_PROBES <- 1500;
/* C78.4 : une tranche AIR grande carte peut traverser plusieurs suspensions
 * automatiques NoAI, mais reste bornee a environ un jour de jeu. Les mesures
 * C39/C76 utilisent ~186k opcodes/jour ; 180k garde une petite marge. */
AIR_PLAN_SLICE_OPS <- 180000;
AIR_MAX_PLANES_PER_ROUTE <- 16;
AIR_PLAN_DIAG_SEQ <- 0;
/* Plafond de distance aerienne (0 = illimite, docs/taches.md C6 supprime) */
AIR_MAX_DISTANCE <- 0;
/* Ordre de chargement passagers aerien (0 = aucun, 1 = deux extremites, 2 = premiere extremite seulement, comme AAAHogEx) */
AIR_FULL_LOAD <- 0;
/* Cache de sites d'aeroport par ville et type d'aeroport (C33.1) */
AIR_SITE_CACHE_ENABLED <- true;
AIR_SITE_CACHE <- {};
/* C118/C120 : cache exact de la liste des villes presentes dans le catchment
 * d'une emprise neuve. Contrairement au cache historique attache a l'objet
 * `site`, cette cle survit aux objets site recrees pour chaque combo moteur ET
 * aux regenerations suivantes. C'est coherent avec AIR_SITE_CACHE : tant que
 * ville/type pointe vers la meme ancre, rescanner son rectangle a chaque build
 * ne change pas la geometrie mais peut suspendre l'IA pendant des semaines.
 * Le cache est invalide avec le cache de site ; un site reel construit passe
 * ensuite par AITileList_StationCoverage, donc n'utilise plus cette prediction. */
AIR_TERRITORIAL_COVERAGE_CACHE <- {};
AIR_TERRITORIAL_COVERAGE_HITS <- 0;
AIR_TERRITORIAL_COVERAGE_MISSES <- 0;
/* Cache court pour les hubs existants : exact pendant une generation AIR,
 * invalide avant la generation suivante car une construction jointe peut
 * agrandir le catchment de station. */
AIR_STATION_COVERAGE_TOWN_CACHE <- {};
AIR_STATION_COVERAGE_HITS <- 0;
AIR_STATION_COVERAGE_MISSES <- 0;
/* C121 : topologie exacte station -> catchment. Elle est independante du cargo
 * et de la ville : la construire une seule fois par station permet aux quatre
 * evaluations endpoint x PASS/MAIL de reutiliser exactement le meme ensemble
 * AITileList_StationCoverage. Les ratings ne sont volontairement pas caches. */
AIR_C121_STATION_COVERAGE_CACHE <- {};
/* C36.3 : Filtre d'emprise sans AITestMode avant la sonde (defaut 1, banc 20x10). */
AIR_CHEAP_SITE <- true;
/* C33.2 : Arrets de bus joints au chantier aeroport */
AIR_JOINED_STOPS <- false;

function OpexAirResetSiteCache()
{
  AIR_SITE_CACHE.clear();
  AIR_TERRITORIAL_COVERAGE_CACHE.clear();
  AIR_TERRITORIAL_COVERAGE_HITS = 0;
  AIR_TERRITORIAL_COVERAGE_MISSES = 0;
  AIR_STATION_COVERAGE_TOWN_CACHE.clear();
  AIR_C121_STATION_COVERAGE_CACHE.clear();
  AIR_STATION_COVERAGE_HITS = 0;
  AIR_STATION_COVERAGE_MISSES = 0;
}

function OpexAirResetTerritorialCoverageCache()
{
  AIR_TERRITORIAL_COVERAGE_CACHE.clear();
}

function OpexAirResetStationCoverageTownCache()
{
  AIR_STATION_COVERAGE_TOWN_CACHE.clear();
  AIR_C121_STATION_COVERAGE_CACHE.clear();
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
function OpexC121StationCompetitionBuckets(town, cargo, cargoTiles, candidateStationId = -1)
{
  local result = { buckets = [], totalWeight = 0, competingWeight = 0, competingStations = 0 };
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
  foreach (tile, producedHere in cargoTiles) {
    if (producedHere <= 0) continue;
    local sum = (tile in sums) ? sums[tile] : 0;
    local maxRating = (tile in maxima) ? maxima[tile] : 0;
    if (sum > 0) result.competingWeight += producedHere;
    local key = sum + "|" + maxRating;
    if (!(key in grouped)) grouped.rawset(key, { sum = sum, maxRating = maxRating, weight = 0 });
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
    weighted += bucket.weight.tofloat() * sourceFraction * stationShare;
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
  if (C121_AIR_ECONOMICS && C121_AIR_ENDPOINT_CACHE != null) {
    local anchorKey = ("anchor" in site) ? site.anchor : -1;
    local townKey = ("town" in site) && site.town != null && ("id" in site.town) ? site.town.id : -1;
    local routesKey = reused && ("routes" in site) ? site.routes : 0;
    local stationKey = reused && ("stationId" in site) ? site.stationId : -1;
    cacheKey = cargo + "|" + airportType + "|" + anchorKey + "|" + townKey
        + "|" + (reused ? 1 : 0) + "|" + routesKey + "|" + stationKey;
    if (cacheKey in C121_AIR_ENDPOINT_CACHE) {
      if (C121_AIR_PLAN_PERF != null) C121_AIR_PLAN_PERF.endpointHits++;
      return C121_AIR_ENDPOINT_CACHE[cacheKey];
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
  result.stopTiles = stops;
  result.coverageTiles = coverageTiles;
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

/* C78.3 : le vivier aerien n'a plus de plafond arbitraire en nombre de villes.
 * La capacite spatiale garde le plafond en cellules utile aux petites cartes,
 * puis ajoute une borne lineaire en perimetre pour eviter O(n^2) sur 1024+. */
function OpexAirTownPoolLimit(towns)
{
  if (towns == null || towns.len() == 0) return 0;
  local minDistance = AIR_TOWN_MIN_DISTANCE > 0 ? AIR_TOWN_MIN_DISTANCE : 1;
  local cellsX = (AIMap.GetMapSizeX() + minDistance - 1) / minDistance;
  local cellsY = (AIMap.GetMapSizeY() + minDistance - 1) / minDistance;
  local gridCapacity = cellsX * cellsY;
  local perimeterCapacity = 4 * (cellsX + cellsY);
  local spatialCapacity = gridCapacity < perimeterCapacity ? gridCapacity : perimeterCapacity;
  if (spatialCapacity < 2 && towns.len() >= 2) spatialCapacity = 2;
  return towns.len() < spatialCapacity ? towns.len() : spatialCapacity;
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

/* C83.1 : avec la limite historique de deux aeroports par ville, ce signal
 * donne directement le nombre de slots restants. Il n'est valable que lorsque
 * la regle de bruit est desactivee et que le conseil municipal n'est pas en
 * mode permissif (qui leve la limite). */
function OpexAirC83SlotSignalEnabled()
{
  return AIGameSettings.IsValid("economy.station_noise_level")
      && AIGameSettings.GetValue("economy.station_noise_level") == 0
      && AIGameSettings.IsValid("difficulty.town_council_tolerance")
      && AIGameSettings.GetValue("difficulty.town_council_tolerance") != 3;
}

function OpexAirC83SecondSlotOpen(town)
{
  if (!OpexAirC83SlotSignalEnabled() || town == null
      || !("id" in town) || !AITown.IsValidTown(town.id)) return false;
  if (AITown.GetPopulation(town.id) < AIR_EARLY_SLOT_MIN_POP) return false;
  return AITown.GetAllowedNoise(town.id) == 1;
}

/* Plancher des grands aeroports (combo large), 600 aujourd'hui. Point unique :
 * un futur reglage du type V93_AIRPORT_MIN_POP se brancherait ici. */
function OpexAirLargeAirportMinPop()
{
  return 600;
}

/* Plancher de la preemption C83. Le plancher historique reste 600. Si V93 est
 * arme, le plancher minimal de ce reglage remplace les 600, et seulement ici. */
function OpexAirPreemptMinPop()
{
  if (V93_AIRPORT_NO_POP_FLOOR) return V93_AIRPORT_MIN_POP;
  return OpexAirLargeAirportMinPop();
}

/* Plus grande ville encore vide : deux slots libres, population au plancher,
 * aucun aeroport Opex impute a cette ville. Une seule cible. */
function OpexAirPreemptPickTown(towns, ownCounts)
{
  if (!C83_PREEMPT_OPEN || !OpexAirC83SlotSignalEnabled() || towns == null) return null;
  local floor = OpexAirPreemptMinPop();
  local best = null;
  local bestPop = -1;
  foreach (town in towns) {
    if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) continue;
    local pop = AITown.GetPopulation(town.id);
    if (pop < floor) continue;
    if (AITown.GetAllowedNoise(town.id) != 2) continue;
    if (ownCounts != null && (town.id in ownCounts)) continue;
    if (best == null || pop > bestPop || (pop == bestPop && town.id < best.id)) {
      best = town;
      bestPop = pop;
    }
  }
  return best;
}

/* Ville debitÃƒÆ’Ã‚Â©e par le moteur pour un aeroport : ClosestTown de l'ancre
 * (CmdBuildAirport), pas GetNearestTown ni la ville commerciale du site. */
function OpexAirSlotTownId(anchor)
{
  if (anchor == null || !AIMap.IsValidTile(anchor)) return -1;
  local townId = AITile.GetClosestTown(anchor);
  if (townId >= 0 && AITown.IsValidTown(townId)) return townId;
  return -1;
}

function OpexAirOwnSlotTownCounts()
{
  local counts = {};
  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local townId = OpexAirSlotTownId(AIStation.GetLocation(st));
    if (townId < 0) continue;
    local n = (townId in counts) ? counts[townId] : 0;
    counts.rawset(townId, n + 1);
  }
  return counts;
}

/* V95 causal : le second slot doit etre encore libre et le premier doit etre
 * detenu par un tiers. Avec station_noise_level=0, slots=1 et zero aeroport
 * Opex sur la ville physique impliquent exactement un aeroport concurrent. */
function OpexAirV95CompetitorSecondSlotOpen(town, anchor = null)
{
  if (!OpexAirC83SlotSignalEnabled() || town == null || !("id" in town)
      || !AITown.IsValidTown(town.id)) return false;
  if (anchor != null && OpexAirSlotTownId(anchor) != town.id) return false;
  if (AITown.GetAllowedNoise(town.id) != 1) return false;
  local ownCounts = OpexAirOwnSlotTownCounts();
  return !(town.id in ownCounts) || ownCounts[town.id] == 0;
}

/* Ville encore disputable : population du plancher grand aeroport, au moins un
 * slot, et aucun aeroport Opex dont l'ancre est imputee a cette ville. */
function OpexAirC83TownContestable(town, ownCounts)
{
  if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) return false;
  if (AITown.GetPopulation(town.id) < OpexAirLargeAirportMinPop()) return false;
  if (AITown.GetAllowedNoise(town.id) < 1) return false;
  if (ownCounts != null && (town.id in ownCounts)) return false;
  return true;
}

/* Meme predicat que la derniere boucle de OpexAirBatchPlanStillLive : une ligne
 * aerienne relie deja les centres-villes (originA/originB), pas les tuiles d'aeroport. */
function OpexAirTownCentersLinked(tileA, tileB, lines)
{
  if (lines == null || tileA == null || tileB == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if ((line.originA == tileA && line.originB == tileB) ||
        (line.originA == tileB && line.originB == tileA)) return true;
  }
  return false;
}

function OpexAirC78NoteNoSite(probes, reason)
{
  if (!C69_BOTTLENECK_PROBE || probes == null) return;
  if ("c78NoSite" in probes) probes.c78NoSite = reason;
  else probes.c78NoSite <- reason;
}

/* C83.1 : petit ensemble surveille par la course reactive. Contrairement a
 * OpexAirSortedTowns, ce helper ne trie jamais tout le catalogue : il maintient
 * seulement les K plus grandes villes, donc O(n*K) avec K=6 au defaut. */
function OpexAirC83WatchTowns(towns)
{
  local best = [];
  if (!OpexAirC83SlotSignalEnabled() || towns == null || AIR_C83_TARGET_TOWNS <= 0) {
    return best;
  }
  local ownCounts = null;
  if (C83_FIXES) ownCounts = OpexAirOwnSlotTownCounts();
  foreach (town in towns) {
    if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) continue;
    local pop = AITown.GetPopulation(town.id);
    if (C83_FIXES) {
      if (!OpexAirC83TownContestable(town, ownCounts)) continue;
    } else if (pop < AIR_EARLY_SLOT_MIN_POP) continue;
    local item = { town = town, pop = pop };
    local pos = best.len();
    while (pos > 0 && best[pos - 1].pop < pop) pos--;
    if (pos >= AIR_C83_TARGET_TOWNS) continue;
    best.insert(pos, item);
    if (best.len() > AIR_C83_TARGET_TOWNS) best.pop();
  }
  local out = [];
  foreach (item in best) out.append(item.town);
  return out;
}

/* ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´ Une ligne aerienne stocke des TUILES d'aeroport dans stationA/stationB, malgre leur nom :
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
  /* C99: NoAI 15.3 applique deja vehicle.plane_speed a GetMaxSpeed.
   * C100 implique cette correction, mais ajoute surtout les manoeuvres physiques. */
  local physicalTiming = C100_AIR_TRIP_PHYSICAL || C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      || C108_AIR_ONESTEP_PHYSICAL_ECONOMICS || C109_AIR_SPEED_ELASTICITY_PHYSICAL
      || C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL
      || forcePhysicalTiming;
  /* C114 reproduit la cellule historique complete du premier C100 : meme
   * vitesse NoAI directe, mais ancien helper OpexAirManeuverDays partout dans
   * l'economie AIR. C103/C104 gardent le meme replay local via force*. */
  local c100ReplayTiming = C114_AIR_C100_FULL_REPLAY || forceC100RankReplay;
  local directSpeed = physicalTiming || c100ReplayTiming;
  local effectiveSpeed = (C99_AIR_SPEED_API_FIX || directSpeed)
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

/* V86 Variante B : plafond de routes autorisees par type d'aeroport.
 * Si air_hub_max_routes vaut N > 0, le plafond devient min(plafond actuel, N). */
function OpexAirAirportMaxRoutes(airportType)
{
  local defaultCap = (airportType == AIAirport.AT_SMALL || airportType == AIAirport.AT_COMMUTER) ? 4 : 12;
  if (AIR_HUB_MAX_ROUTES > 0) {
    return AIR_HUB_MAX_ROUTES < defaultCap ? AIR_HUB_MAX_ROUTES : defaultCap;
  }
  return defaultCap;
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

/* G7Ãƒâ€šÃ‚Â§2 : Sonde AITestMode de nivelabilite, sans modifier la carte ni depenser de tresorerie.
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

/* C78.2 : ERR_STATION_TOO_MANY_STATIONS_IN_TOWN est une propriete de la ville,
 * pas de l'ancre testee. Une seule reponse du moteur suffit donc a exclure cette
 * ville pour tout le scan courant, y compris pour les autres types d'aeroport. */
function OpexAirRememberTownStationLimit(probes, town, error)
{
  if (error != AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) return false;
  if (probes != null && ("stationLimitedTowns" in probes)) {
    probes.stationLimitedTowns.rawset(town.id, true);
  }
  OpexAirC78NoteNoSite(probes, "no_site_slot");
  return true;
}

/* Copie les compteurs de sondes. stationLimitedTowns est une table partagee avec
 * l'appelant : la copie est independante pour qu'un second scan ne la mute pas. */
function OpexAirCopySiteProbes(probes)
{
  local copy = {};
  foreach (k, v in probes) {
    if (typeof v == "table") {
      local inner = {};
      foreach (ik, iv in v) inner.rawset(ik, iv);
      copy.rawset(k, inner);
    } else {
      copy.rawset(k, v);
    }
  }
  return copy;
}

/* Un seul anneau r. Carre [villeÃƒâ€šÃ‚Â±r] moins [villeÃƒâ€šÃ‚Â±(r-1)], meme clamp carte/emprise
 * que le rejet ax+offX >= mapX. Equivalent a DistanceMax(ancre, ville) == r,
 * sans valuer l'interieur.
 * IsWaterTile / IsCoastTile : (tuile) -> bool, 0/1 dans Valuate.
 * GetClosestTown : (tuile) -> TownID. GetNearestTown : (tuile, type) -> TownID.
 * Ordre natif : Valuate(AIMap.GetTileX) puis Sort(VALUE, ASCENDING).
 * ScriptList range son set par paire (valeur, index). A X egal, l'index croissant
 * est Y croissant (index = y * mapX + x), soit (dx, dy) dans l'anneau.
 * Aucune table Squirrel par ancre. */
function OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY)
{
  local minX = townX - r;
  if (minX < 0) minX = 0;
  local minY = townY - r;
  if (minY < 0) minY = 0;
  local maxX = townX + r;
  local fitX = mapX - offX - 1;
  if (maxX > fitX) maxX = fitX;
  if (maxX >= mapX) maxX = mapX - 1;
  local maxY = townY + r;
  local fitY = mapY - offY - 1;
  if (maxY > fitY) maxY = fitY;
  if (maxY >= mapY) maxY = mapY - 1;
  if (minX > maxX || minY > maxY) return null;

  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(minX, minY), AIMap.GetTileIndex(maxX, maxY));

  local inner = r - 1;
  local inMinX = townX - inner;
  if (inMinX < minX) inMinX = minX;
  local inMinY = townY - inner;
  if (inMinY < minY) inMinY = minY;
  local inMaxX = townX + inner;
  if (inMaxX > maxX) inMaxX = maxX;
  local inMaxY = townY + inner;
  if (inMaxY > maxY) inMaxY = maxY;
  if (inMinX <= inMaxX && inMinY <= inMaxY) {
    tiles.RemoveRectangle(AIMap.GetTileIndex(inMinX, inMinY), AIMap.GetTileIndex(inMaxX, inMaxY));
  }
  if (tiles.Count() == 0) return null;

  tiles.Valuate(AITile.IsWaterTile);
  tiles.KeepValue(0);
  tiles.Valuate(AITile.IsCoastTile);
  tiles.KeepValue(0);
  if (requiredSlotTownId >= 0) {
    tiles.Valuate(AITile.GetClosestTown);
    tiles.KeepValue(requiredSlotTownId);
  }
  tiles.Valuate(AIAirport.GetNearestTown, airport.type);
  tiles.KeepValue(town.id);
  if (tiles.Count() == 0) return null;

  tiles.Valuate(AIMap.GetTileX);
  tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
  return tiles;
}

/* Anneaux r = 4..AIR_SITE_RADIUS, un par un. Le return historique sort tout de suite :
 * les anneaux suivants ne sont pas construits. useSiteCache faux : le mode check
 * ne reecrit pas AIR_SITE_CACHE. */
function OpexAirFindSiteListed(town, airport, probes, requiredSlotTownId, key, useSiteCache)
{
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    local ring = OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY);
    if (ring == null) continue;
    foreach (anchor, anchorX in ring) {
      if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
      local c4 = anchor + AIMap.GetTileIndex(offX, offY);
      if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;

      if (AIR_CHEAP_SITE) {
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
          continue;
        }
      } else {
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
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        if (useSiteCache) AIR_SITE_CACHE[key] <- null;
        return { site = null, used = used, execLevels = execLevels, allowance = allowance };
      }
      if (probes.left <= 0) {
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        return { site = null, used = used, execLevels = execLevels, allowance = allowance };
      }

      local ok = false;
      if (AIR_CHEAP_SITE) {
        {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        }
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            return { site = null, used = used, execLevels = execLevels, allowance = allowance };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
              OpexAirFootprintIsFlat(anchor, airport)) {
            ok = true;
          } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                      err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                     execLevels < 3) {
            execLevels++;
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
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            return { site = null, used = used, execLevels = execLevels, allowance = allowance };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
            ok = true;
          } else {
            AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
            if (!ok) {
              local retryErr = AIError.GetLastError();
              if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                if (useSiteCache) AIR_SITE_CACHE[key] <- null;
                return { site = null, used = used, execLevels = execLevels, allowance = allowance };
              }
              if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
            }
          }
        }
      }
      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (ok) {
        if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
        return {
          site = { town = town, anchor = anchor },
          used = used, execLevels = execLevels, allowance = allowance
        };
      }
    }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  return { site = null, used = used, execLevels = execLevels, allowance = allowance };
}

/* C96 : score relatif de placement uniquement. GetCargoProduction est utilise
 * ici comme compte de tuiles productrices dans le catchment physique ; ce
 * score ne devient jamais une demande mensuelle et n'entre pas dans C68. */
function OpexAirC96SiteCatchmentScore(anchor, airport, paxCargo)
{
  if (paxCargo < 0) return 0;
  return OpexAirAirportCatchmentProduction(anchor, airport.type, paxCargo);
}

function OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
                            valid, firstValidRing, bestRing, used)
{
  if (best == null) return;
  local firstDist = OpexAirDistanceToRect(town.tile, firstAnchor, airport.width, airport.height);
  local bestDist = OpexAirDistanceToRect(town.tile, best.anchor, airport.width, airport.height);
  AILog.Info("C96_SITE town=" + town.id
      + " pop=" + AITown.GetPopulation(town.id)
      + " type=" + airport.type
      + " first=" + firstAnchor + " first_score=" + firstScore
      + " best=" + best.anchor + " best_score=" + bestScore
      + " gain=" + (bestScore - firstScore)
      + " first_dist=" + firstDist + " best_dist=" + bestDist
      + " valid=" + valid + " first_ring=" + firstValidRing
      + " best_ring=" + bestRing + " probes=" + used);
}

/* C96 : meme vivier physique que V94, mais ne retourne pas le premier succes.
 * A partir du premier anneau constructible, conserver au plus MAX_VALID sites
 * valides et regarder au plus EXTRA_RINGS anneaux supplementaires. Le meilleur
 * compte de tuiles productrices PASS gagne ; a score egal, le premier site de
 * l'ordre V94 reste choisi. Demande, avion, economie et classement restent
 * strictement en aval et inchanges. */
function OpexAirFindSiteCatchmentListed(town, airport, probes, requiredSlotTownId, key, useSiteCache)
{
  local paxCargo = OpexAirDemandPaxCargo();
  if (paxCargo < 0) {
    return OpexAirFindSiteListed(town, airport, probes, requiredSlotTownId, key, useSiteCache);
  }

  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);
  local best = null;
  local bestScore = -1;
  local firstAnchor = -1;
  local firstScore = -1;
  local valid = 0;
  local firstValidRing = -1;
  local bestRing = -1;

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    if (firstValidRing >= 0 && r > firstValidRing + C96_AIR_SITE_EXTRA_RINGS) break;
    local ring = OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY);
    if (ring == null) continue;
    foreach (anchor, anchorX in ring) {
      if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
      local c4 = anchor + AIMap.GetTileIndex(offX, offY);
      if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;

      if (AIR_CHEAP_SITE) {
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
          continue;
        }
      } else {
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

      if (used >= allowance || probes.left <= 0) {
        if (best != null) {
          OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
              valid, firstValidRing, bestRing, used);
          if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
          return { site = best, used = used, execLevels = execLevels, allowance = allowance };
        }
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        if (useSiteCache && used >= allowance) AIR_SITE_CACHE[key] <- null;
        return { site = null, used = used, execLevels = execLevels, allowance = allowance };
      }

      local ok = false;
      if (AIR_CHEAP_SITE) {
        {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        }
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            return { site = null, used = used, execLevels = execLevels, allowance = allowance };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
              OpexAirFootprintIsFlat(anchor, airport)) {
            ok = true;
          } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                      err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                     execLevels < 3) {
            execLevels++;
            if (OpexAirCanLevelFootprint(anchor, airport, town.id)) ok = true;
          }
        }
      } else {
        local probe = AITestMode();
        ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            return { site = null, used = used, execLevels = execLevels, allowance = allowance };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
            ok = true;
          } else {
            AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
            if (!ok) {
              local retryErr = AIError.GetLastError();
              if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                if (useSiteCache) AIR_SITE_CACHE[key] <- null;
                return { site = null, used = used, execLevels = execLevels, allowance = allowance };
              }
              if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
            }
          }
        }
      }

      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (!ok) continue;

      if (firstValidRing < 0) firstValidRing = r;
      local score = OpexAirC96SiteCatchmentScore(anchor, airport, paxCargo);
      valid++;
      if (firstAnchor < 0) {
        firstAnchor = anchor;
        firstScore = score;
      }
      if (best == null || score > bestScore) {
        best = { town = town, anchor = anchor };
        bestScore = score;
        bestRing = r;
      }
      if (valid >= C96_AIR_SITE_MAX_VALID) {
        OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
            valid, firstValidRing, bestRing, used);
        if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
        return { site = best, used = used, execLevels = execLevels, allowance = allowance };
      }
    }
  }

  if (best != null) {
    OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
        valid, firstValidRing, bestRing, used);
    if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
    return { site = best, used = used, execLevels = execLevels, allowance = allowance };
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) AIR_SITE_CACHE[key] <- null;
  return { site = null, used = used, execLevels = execLevels, allowance = allowance };
}

function OpexAirV94Report(town, legacy, listed, probes, copy)
{
  local ancL = legacy.site == null ? -1 : legacy.site.anchor;
  local ancN = listed.site == null ? -1 : listed.site.anchor;
  local cheapL = ("cheapSkip" in probes) ? probes.cheapSkip : -1;
  local cheapN = ("cheapSkip" in copy) ? copy.cheapSkip : -1;
  local testedL = ("tested" in probes) ? probes.tested : -1;
  local testedN = ("tested" in copy) ? copy.tested : -1;
  local limL = 0;
  local limN = 0;
  if (("stationLimitedTowns" in probes) && (town.id in probes.stationLimitedTowns)) limL = 1;
  if (("stationLimitedTowns" in copy) && (town.id in copy.stationLimitedTowns)) limN = 1;
  local same = ancL == ancN && legacy.used == listed.used && legacy.execLevels == listed.execLevels
      && legacy.allowance == listed.allowance
      && probes.left == copy.left && probes.townsLeft == copy.townsLeft
      && cheapL == cheapN && testedL == testedN && limL == limN;
  AILog.Info("V94_CHECK " + (same ? "OK" : "DIFF")
      + " town=" + town.id
      + " anchor=" + ancL + "/" + ancN
      + " used=" + legacy.used + "/" + listed.used
      + " left=" + probes.left + "/" + copy.left
      + " tested=" + testedL + "/" + testedN
      + " cheap=" + cheapL + "/" + cheapN
      + " exec=" + legacy.execLevels + "/" + listed.execLevels
      + " allow=" + legacy.allowance + "/" + listed.allowance
      + " lim=" + limL + "/" + limN);
}

/* Le scan historique a deja decide. Le second passage ne touche pas le cache
 * et travaille sur la copie des sondes prise avant ce scan. */
function OpexAirV94Finish(town, airport, requiredSlotTownId, probes, copy, key, site, used, execLevels, allowance)
{
  local legacy = { site = site, used = used, execLevels = execLevels, allowance = allowance };
  local listed = OpexAirFindSiteListed(town, airport, copy, requiredSlotTownId, key, false);
  OpexAirV94Report(town, legacy, listed, probes, copy);
  return site;
}

/* Trouve la premiere ancre constructible, par couronnes autour de la ville. L'ancre est bien le
 * coin haut-gauche attendu par BuildAirport. La couverture est testee contre le rectangle entier,
 * pas seulement contre son coin. */
function OpexAirFindSite(town, airport, probes, requiredSlotTownId = -1)
{
  if (C60_TOWN_RATING_PROBE) {
    OpexC60ObserveTownRating("air", "find_site", town.id);
  }
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
  if (probes != null && ("stationLimitedTowns" in probes)
      && (town.id in probes.stationLimitedTowns)) return null;
  local key = town.id + "_" + airport.type;
  /* C83 cible : le cache historique est indexe par ville commerciale/type.
   * Une course au slot exige en plus ClosestTown(anchor)==ville cible ; ne pas
   * reutiliser ni ecrire ce cache dans ce chemin rare. */
  local useSiteCache = AIR_SITE_CACHE_ENABLED && requiredSlotTownId < 0;
  if (useSiteCache && (key in AIR_SITE_CACHE)) {
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
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(cachedAnchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       OpexAirCanLevelFootprint(cachedAnchor, airport, town.id)) {
              /* G7Ãƒâ€šÃ‚Â§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              ok = true;
            }
          }
        } else {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(cachedAnchor, OpexAirFootprintEnd(cachedAnchor, airport));
              ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
              if (!ok) {
                local retryErr = AIError.GetLastError();
                if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                  AIR_SITE_CACHE[key] <- null;
                  return null;
                }
                if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
              }
            }
          }
        }
        if ("tested" in probes) probes.tested++;
        if (ok) return { town = town, anchor = cachedAnchor };
      }
    }
    delete AIR_SITE_CACHE[key];
  }

  /* V94 : defaut 1, la liste decide ; a 0, le balayage ci-dessous (origine). Le check
   * execute ce balayage comme decision, puis la liste sur une copie. */
  local v94Copy = null;
  if (V94_AIR_SITE_CHECK) v94Copy = OpexAirCopySiteProbes(probes);
  if (C96_AIR_SITE_CATCHMENT) {
    return OpexAirFindSiteCatchmentListed(town, airport, probes, requiredSlotTownId, key, useSiteCache).site;
  }
  if (V94_AIR_SITE_LIST && !V94_AIR_SITE_CHECK) {
    return OpexAirFindSiteListed(town, airport, probes, requiredSlotTownId, key, useSiteCache).site;
  }

  /* Le budget global reste borne, mais il est partage entre les villes encore
   * a sonder. Elargir le vivier ne peut donc pas multiplier sans borne les
   * AITestMode : davantage de villes donne moins de sondes par ville. */
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
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
        if (requiredSlotTownId >= 0 && AITile.GetClosestTown(anchor) != requiredSlotTownId) continue;
        if (AIAirport.GetNearestTown(anchor, airport.type) != town.id) continue;

        if (AIR_CHEAP_SITE) {
          /* Eau/riviere/cote sur toute l'emprise, C4, et IsBuildableRectangle : sans AITestMode.
           * La sonde ci-dessous ne tourne plus que sur un hit cheap. */
          if (!OpexAirFootprintCheapOk(anchor, airport)) {
            if ("cheapSkip" in probes) probes.cheapSkip++;
            continue;
          }
        } else {
          /* Filtre de platitude prÃƒÆ’Ã‚Â©alable (docs/taches.md Ãƒâ€šÃ‚Â§0 tervicies point 5 & C4, faÃƒÆ’Ã‚Â§on AAAHogEx) :
           * Si l'ÃƒÆ’Ã‚Â©cart d'altitude au sein de l'emprise dÃƒÆ’Ã‚Â©passe 1 niveau, le terrassement ÃƒÆ’Ã‚Â©choue
           * massivement ou coÃƒÆ’Ã‚Â»te trop cher. Rejet ÃƒÆ’Ã‚Â©liminatoire avant d'entrer en AITestMode. */
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
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          if (useSiteCache) AIR_SITE_CACHE[key] <- null;
          if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
          return null;
        }
        if (probes.left <= 0) {
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
          return null;
        }

        local ok = false;
        if (AIR_CHEAP_SITE) {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              if (useSiteCache) AIR_SITE_CACHE[key] <- null;
              if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(anchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       execLevels < 3) {
              execLevels++;
              /* G7Ãƒâ€šÃ‚Â§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
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
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              if (useSiteCache) AIR_SITE_CACHE[key] <- null;
              if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
              ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
              if (!ok) {
                local retryErr = AIError.GetLastError();
                if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                  if (useSiteCache) AIR_SITE_CACHE[key] <- null;
                  if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
                  return null;
                }
                if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
              }
            }
          }
        }
        used++;
        probes.left--;
        if ("tested" in probes) probes.tested++;
        if (ok) {
          if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
          local found = { town = town, anchor = anchor };
          if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, found, used, execLevels, allowance);
          return found;
        }
      }
    }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
  return null;
}

/* C78.2 : revalidation legere d'un site deja trouve. Le scan complet peut
 * suspendre pendant que la carte evolue ; ce predicat est donc rejoue juste
 * avant le classement, puis par le portefeuille avant sa propre selection. */
function OpexAirSiteStillBuildable(site, airport, plane, reuse, stationLimitedTowns = null)
{
  if (site == null || airport == null || plane == null || !AIMap.IsValidTile(site.anchor)) return false;
  if (reuse) {
    return AIAirport.IsAirportTile(site.anchor)
        && OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(site.anchor), plane.planeType);
  }
  if (!("town" in site) || site.town == null || !("id" in site.town)) return false;
  if (stationLimitedTowns != null && (site.town.id in stationLimitedTowns)) return false;
  if (AIAirport.GetNearestTown(site.anchor, airport.type) != site.town.id) return false;
  /* C83 : l'identite physique du creneau (ClosestTown de l'ancre) ne contraint que les sites
   * issus d'une course vers un creneau precis (c83SlotTown). Un site AIR ordinaire garde le seul
   * critere historique GetNearestTown : l'appliquer partout freinait l'expansion aerienne
   * (20x10 du 2026-09-24 : -2,1 creneaux, -13 % de vehicules, fail_primary). */
  if (C83_FIXES && ("c83SlotTown" in site) && site.c83SlotTown >= 0
      && OpexAirSlotTownId(site.anchor) != site.c83SlotTown) return false;
  if (AIR_CHEAP_SITE && !OpexAirFootprintCheapOk(site.anchor, airport)) return false;

  local ok = false;
  local error = 0;
  {
    local probe = AITestMode();
    ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW);
    if (!ok) error = AIError.GetLastError();
  }
  if (ok) return true;

  if (error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) {
    if (stationLimitedTowns != null) stationLimitedTowns.rawset(site.town.id, true);
    return false;
  }
  if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES
      && OpexAirFootprintIsFlat(site.anchor, airport)) return true;
  if ((error == AIError.ERR_LOCAL_AUTHORITY_REFUSES || error == AIError.ERR_FLAT_LAND_REQUIRED)
      && OpexAirCanLevelFootprint(site.anchor, airport, site.town.id)) return true;
  return false;
}

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
      C121_CATALOG_STATION_REV.rawset(stationId,
          (stationId in C121_CATALOG_STATION_REV
              ? C121_CATALOG_STATION_REV[stationId] : 0) + 1);
    }
  }
  foreach (stationId, signature in C121_CATALOG_STATION_LINES) {
    if (!(stationId in nextLines)) C121_CATALOG_STATION_REV.rawset(stationId,
        (stationId in C121_CATALOG_STATION_REV
            ? C121_CATALOG_STATION_REV[stationId] : 0) + 1);
  }
  C121_CATALOG_STATION_LINES = nextLines;
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

function OpexC121CatalogChoice(catalog, plan, lines)
{
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
      if (entry.demand != null) plan.c121Demand <- entry.demand;
      if (entry.engineStatic != null) plan.c121EngineStatic <- entry.engineStatic;
      if (entry.choice != null) {
        plan.c121ChosenEngine <- entry.choice.plane.id;
        plan.c121ChosenMailKnown <- entry.mailKnown;
      }
      return entry.choice;
    }
  }
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
  local choice = OpexC121ChooseRoutePlane(catalog, plan, lines);
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
    engineStatic = ("c121EngineStatic" in plan) ? plan.c121EngineStatic : null,
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

function OpexAirLineSellValue(line)
{
  local total = 0;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v)) total += AIVehicle.GetCurrentValue(v);
  }
  return total;
}

function OpexAirLineReequipPending(line)
{
  return line != null && ("v92PendingEngine" in line) && line.v92PendingEngine >= 0;
}

function OpexAirClearReequip(line)
{
  if (line == null) return;
  if ("v92PendingEngine" in line) delete line.v92PendingEngine;
  if ("v92PendingCount" in line) delete line.v92PendingCount;
  if ("v92SentToHangar" in line) line.v92SentToHangar = [];
}

function OpexAirAlreadySentToHangar(line, vehicle)
{
  if (!("v92SentToHangar" in line) || line.v92SentToHangar == null) return false;
  foreach (id in line.v92SentToHangar) {
    if (id == vehicle) return true;
  }
  return false;
}

/* SendVehicleToDepot est une bascule, et l'ordre manuel n'est pas dans la liste
 * d'ordres. On memorise les vehicules deja envoyes et on ne les renvoie jamais.
 * Le hangar d'arrivee est le plus proche, pas forcement celui de l'aeroport A. */
function OpexAirSendLineToHangar(line, hangar)
{
  local waiting = false;
  foreach (v in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(v) || AIVehicle.IsStoppedInDepot(v)) continue;
    waiting = true;
    if (OpexAirAlreadySentToHangar(line, v)) continue;
    if (!AIVehicle.SendVehicleToDepot(v)) continue;
    if (!("v92SentToHangar" in line) || line.v92SentToHangar == null) line.v92SentToHangar <- [];
    line.v92SentToHangar.append(v);
  }
  return waiting;
}

function OpexAirReleaseHangarHold(line)
{
  if (line == null || !("vehicles" in line) || line.vehicles == null) {
    OpexAirClearReequip(line);
    return;
  }
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsStoppedInDepot(v)) AIVehicle.StartStopVehicle(v);
  }
  OpexAirClearReequip(line);
}

/* Repose `count` appareils d'un moteur deja vendu. Retourne le nombre rÃƒÆ’Ã‚Â©ellement relancÃƒÆ’Ã‚Â©. */
function OpexAirRebuildFleet(line, hangar, engineId, count, cargo)
{
  if (engineId < 0 || count < 1) return 0;
  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local restored = [];
  for (local i = 0; i < count; i++) {
    local aircraft = AIVehicle.BuildVehicleWithRefit(hangar, engineId, cargo);
    if (!AIVehicle.IsValidVehicle(aircraft)) break;
    local ordersOk = true;
    if (restored.len() == 0) {
      ordersOk = AIOrder.AppendOrder(aircraft, line.stationA, airFlagsA)
          && AIOrder.AppendOrder(aircraft, line.stationB, airFlagsB)
          && AIOrder.GetOrderCount(aircraft) == 2;
    } else {
      ordersOk = AIOrder.ShareOrders(aircraft, restored[0]);
    }
    if (!ordersOk || !AIVehicle.StartStopVehicle(aircraft)) {
      if (AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
      break;
    }
    restored.append(aircraft);
  }
  if (restored.len() == 0) return 0;
  line.vehicles = restored;
  line.vehicle = restored[0];
  line.refleetEngine = engineId;
  line.vehCount <- restored.len();
  line.trains = restored.len();
  return restored.len();
}

function OpexAirLineAllInHangar(line)
{
  local any = false;
  foreach (v in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    any = true;
    if (!AIVehicle.IsStoppedInDepot(v)) return false;
  }
  return any;
}

/* Vend la flotte et pose `count` appareils du nouveau moteur. En echec, rachete l'ancien. */
function OpexAirReplaceFleet(line, hangar, catalog, plane, count)
{
  if (plane == null || count < 1 || !OpexAirLineAllInHangar(line)) return null;
  local cargo = ("cargo" in line) ? line.cargo : catalog.paxCargo;
  local oldEngine = ("refleetEngine" in line) ? line.refleetEngine : -1;
  if (!AIEngine.IsBuildable(plane.id) || (oldEngine >= 0 && !AIEngine.IsBuildable(oldEngine))) {
    return { added = 0, reason = "ABORT" };
  }
  local sell = OpexAirLineSellValue(line);
  local cost = count * plane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money + sell < cost + OpexCashReserve()) return { added = 0, reason = "ABORT" };
  local old = [];
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v)) old.append(v);
  }
  local oldCount = old.len();
  local kept = [];
  foreach (v in old) {
    if (!AIVehicle.SellVehicle(v)) kept.append(v);
  }
  if (kept.len() > 0) {
    line.vehicles = kept;
    line.vehicle = kept[0];
    line.vehCount <- kept.len();
    line.trains = kept.len();
    return null;
  }
  local built = [];
  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local failed = false;
  for (local i = 0; i < count; i++) {
    local aircraft = AIVehicle.BuildVehicleWithRefit(hangar, plane.id, cargo);
    if (!AIVehicle.IsValidVehicle(aircraft)) { failed = true; break; }
    local ordersOk = true;
    if (built.len() == 0) {
      ordersOk = AIOrder.AppendOrder(aircraft, line.stationA, airFlagsA)
          && AIOrder.AppendOrder(aircraft, line.stationB, airFlagsB)
          && AIOrder.GetOrderCount(aircraft) == 2;
    } else {
      ordersOk = AIOrder.ShareOrders(aircraft, built[0]);
    }
    if (!ordersOk) {
      if (AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
      failed = true;
      break;
    }
    built.append(aircraft);
  }
  if (failed || built.len() != count) {
    foreach (aircraft in built) {
      if (AIVehicle.IsValidVehicle(aircraft) && AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
    }
    if (OpexAirRebuildFleet(line, hangar, oldEngine, oldCount, cargo) <= 0) {
      line.vehicles = [];
      line.vehicle = -1;
      line.vehCount <- 0;
      line.trains = 0;
    }
    return null;
  }
  local started = true;
  foreach (aircraft in built) {
    if (!AIVehicle.StartStopVehicle(aircraft)) {
      foreach (sold in built) {
        if (AIVehicle.IsValidVehicle(sold) && AIVehicle.IsStoppedInDepot(sold)) AIVehicle.SellVehicle(sold);
      }
      started = false;
      break;
    }
  }
  if (!started) {
    if (OpexAirRebuildFleet(line, hangar, oldEngine, oldCount, cargo) <= 0) {
      line.vehicles = [];
      line.vehicle = -1;
      line.vehCount <- 0;
      line.trains = 0;
    }
    return null;
  }
  line.vehicles = built;
  line.vehicle = built[0];
  line.refleetEngine = plane.id;
  line.planeId = plane.id;
  line.planeCapacity = plane.capacity;
  line.vehCount <- built.len();
  line.trains = built.len();
  line.v92LastReplaceYear <- AIDate.GetYear(AIDate.GetCurrentDate());
  OpexAirClearReequip(line);
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local mail = AIVehicle.GetCapacity(built[0], catalog.mailCargo);
    if (mail >= 0) AIR_MAIL_CAP.rawset(plane.id, mail);
  }
  return { added = 0, reason = "REPLACE", vehCount = built.len() };
}

/* Un autre moteur au meilleur nombre bat un appareil de plus du moteur actuel. */
function OpexAirConsiderReplace(line, catalog, airportTile)
{
  if (("scrapping" in line) && line.scrapping) return null;
  if (!("distance" in line) || line.distance <= 0) return null;
  if (!("airMonthlyPax" in line) || line.airMonthlyPax <= 0) return null;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (("v92LastReplaceYear" in line) && year - line.v92LastReplaceYear < 2) return null;
  local airportType = AIAirport.GetAirportType(airportTile);
  if (!AIAirport.IsValidAirportType(airportType)) return null;
  local currentId = ("refleetEngine" in line) ? line.refleetEngine : -1;
  if (currentId < 0) return null;
  local have = 0;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) have++;
  }
  if (have < 1) return null;
  OpexAirLearnMailCaps(catalog);
  local airport = {
    type = airportType,
    price = AIAirport.GetPrice(airportType),
    maintenance = AIAirport.GetMonthlyMaintenanceCost(airportType),
  };
  local infrastructure = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local current = OpexAirCatalogPlane(catalog, airportType, currentId);
  if (current == null) return null;
  OpexAirApplyKnownMail(current);
  local keep = OpexAirEconomics(catalog, airport, current, line.distance, line.airMonthlyPax,
      infrastructure, 0, 0, 0, have + 1, false, false);
  if (catalog.airPlaneChoicesByAirport == null
      || !(airportType in catalog.airPlaneChoicesByAirport)) return null;
  local bestPlane = null;
  local bestEcon = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airportType]) {
    if (plane.id == currentId || !OpexAirPlaneInRange(plane, line.distance)) continue;
    OpexAirApplyKnownMail(plane);
    local econ = OpexAirEconomics(catalog, airport, plane, line.distance, line.airMonthlyPax,
        infrastructure, 0, 0, 0, 0, false, true);
    if (OpexAirServiceBetter(econ, bestEcon)) {
      bestPlane = plane;
      bestEcon = econ;
    }
  }
  if (bestPlane == null) return null;
  local cap = OpexAirCadenceCap(line, catalog, null);
  if (cap < 1) cap = 1;
  if (bestEcon.planes > cap) {
    bestEcon = OpexAirEconomics(catalog, airport, bestPlane, line.distance, line.airMonthlyPax,
        infrastructure, 0, 0, 0, cap, false, false);
  }
  if (!OpexAirServiceBetter(bestEcon, keep)) return null;
  local sell = OpexAirLineSellValue(line);
  local cost = bestEcon.planes * bestPlane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money + sell < cost + OpexCashReserve()) return null;
  return { plane = bestPlane, count = bestEcon.planes };
}

function OpexAirMaybeReequip(line, catalog, hangar, airportTile)
{
  if (("v92PendingEngine" in line) && line.v92PendingEngine >= 0) {
    if (!OpexAirLineAllInHangar(line)) {
      OpexAirSendLineToHangar(line, hangar);
      return { added = 0, reason = "REEEQUIP_WAIT" };
    }
    local airportType = AIAirport.GetAirportType(airportTile);
    local plane = OpexAirCatalogPlane(catalog, airportType, line.v92PendingEngine);
    local count = ("v92PendingCount" in line) ? line.v92PendingCount : 1;
    local swapped = OpexAirReplaceFleet(line, hangar, catalog, plane, count);
    if (swapped != null && swapped.reason == "ABORT") {
      OpexAirReleaseHangarHold(line);
      return { added = 0, reason = "REEEQUIP_ABORT" };
    }
    if (swapped != null) return swapped;
    OpexAirClearReequip(line);
    return { added = 0, reason = "REEEQUIP_FAIL" };
  }
  local decision = OpexAirConsiderReplace(line, catalog, airportTile);
  if (decision == null) return null;
  line.v92PendingEngine <- decision.plane.id;
  line.v92PendingCount <- decision.count;
  OpexAirSendLineToHangar(line, hangar);
  if (OpexAirLineAllInHangar(line)) {
    local swapped = OpexAirReplaceFleet(line, hangar, catalog, decision.plane, decision.count);
    if (swapped != null && swapped.reason == "ABORT") {
      OpexAirReleaseHangarHold(line);
      return { added = 0, reason = "REEEQUIP_ABORT" };
    }
    if (swapped != null) return swapped;
    OpexAirClearReequip(line);
    return { added = 0, reason = "REEEQUIP_FAIL" };
  }
  return { added = 0, reason = "REEEQUIP_WAIT" };
}

/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees.
 * Sous V92, un autre service peut remplacer la flotte avant ce clonage. */
function OpexAirAddPlane(line, catalog = null)
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
  if (V92_AIR_SERVICE_CHOICE && catalog != null) {
    local swapped = OpexAirMaybeReequip(line, catalog, hangar, airportTile);
    if (swapped != null) return swapped;
  }
  local price = AIEngine.GetPrice(AIVehicle.GetEngineType(template));
  if (price <= 0) { result.reason = "PRICE"; return result; }
  local need = price + OpexCashReserve() + 1000;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
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
      if (!AIOrder.ShareOrders(extra, template)) {
        if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
        result.reason = "ORDER"; return result;
      }
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
  local flagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local flagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  if (!AIOrder.AppendOrder(plane, line.stationA, flagsA) ||
      !AIOrder.AppendOrder(plane, line.stationB, flagsB) || AIOrder.GetOrderCount(plane) != 2) {
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
  if (!C111_AIR_C100_DECISION_SHADOW && !C121_AIR_ECONOMICS) {
    if (plan.economics.roi > (bestPlan.economics.roi * 1.25).tointeger()) return true;
    if (bestPlan.economics.roi > (plan.economics.roi * 1.25).tointeger()) return false;
    return plan.economics.profitAnnual > bestPlan.economics.profitAnnual;
  }
  local planEconomics = (("decisionEconomics" in plan) && plan.decisionEconomics != null)
      ? plan.decisionEconomics : plan.economics;
  local bestEconomics = (("decisionEconomics" in bestPlan) && bestPlan.decisionEconomics != null)
      ? bestPlan.decisionEconomics : bestPlan.economics;
  /* Arbitrage ROI vs Volume : si un plan offre un ROI significativement superieur (>25% d'ecart),
   * il deploie le capital plus vite et permet de batir plus de lignes. */
  if (planEconomics.roi > (bestEconomics.roi * 1.25).tointeger()) return true;
  if (bestEconomics.roi > (planEconomics.roi * 1.25).tointeger()) return false;
  return planEconomics.profitAnnual > bestEconomics.profitAnnual;
}

/* V92 : pose le service retenu et, s'il differe, la variante a un appareil bon marche.
 * Les deux portent la meme cle de paire pour qu'un seul soit construit. */
function OpexAirV92PairBlocked(lines, plan)
{
  if (!V92_AIR_SERVICE_CHOICE || plan == null || !("v92PairKey" in plan)) return false;
  if (plan.v92PairKey in V92_CLOSED_PAIRS) return true;
  if (lines == null || !("siteA" in plan) || !("siteB" in plan)) return false;
  local tileA = plan.siteA.town.tile;
  local tileB = plan.siteB.town.tile;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    local originA = ("originA" in line) ? line.originA : -1;
    local originB = ("originB" in line) ? line.originB : -1;
    if ((originA == tileA && originB == tileB) || (originA == tileB && originB == tileA)) return true;
  }
  return false;
}

/* C97 : capital et profit d'un point virtuel passes par EXACTEMENT le meme
 * chemin que le projet AIR reel. Cela reutilise donc la marge AIR,
 * l'immobilisation et la calibration C70/C82 du portefeuille, sans definition
 * parallele du cout. */
function OpexC97AirPoint(catalog, plan, plane, economics, kDec)
{
  if (catalog == null || plan == null || plane == null || economics == null
      || economics.profitAnnual <= 0) return null;
  local virtualPlan = clone plan;
  virtualPlan.plane = plane;
  virtualPlan.economics = economics;
  virtualPlan.planes = economics.planes;
  virtualPlan.capital = economics.capital;
  local project = OpexProjectFromAir(catalog, virtualPlan, 0);
  if (project == null) return null;
  local financeCapital = OpexProjectFinanceCapital(project);
  if (financeCapital <= 0) return null;
  local calibratedProfit = C70_PROFIT_CALIBRATED
      ? OpexCalibratedProfit(project) : project.profitAnnual;
  local denom = financeCapital > kDec ? financeCapital : kDec;
  return {
    plane = plane,
    economics = economics,
    financeCapital = financeCapital,
    calibratedProfit = calibratedProfit,
    score = OpexProjectScore(calibratedProfit, denom),
  };
}

/* Le score C69 est l'objectif primaire. Les departages ne changent jamais le
 * maximum du score : profit calibre, capital moindre, moteur puis profondeur
 * donnent seulement un ordre deterministe. */
function OpexC97AirPointBetter(candidate, incumbent)
{
  if (candidate == null) return false;
  if (incumbent == null) return true;
  if (candidate.score > incumbent.score) return true;
  if (candidate.score < incumbent.score) return false;
  if (candidate.calibratedProfit > incumbent.calibratedProfit) return true;
  if (candidate.calibratedProfit < incumbent.calibratedProfit) return false;
  if (candidate.financeCapital < incumbent.financeCapital) return true;
  if (candidate.financeCapital > incumbent.financeCapital) return false;
  if (candidate.plane.id < incumbent.plane.id) return true;
  if (candidate.plane.id > incumbent.plane.id) return false;
  return candidate.economics.planes < incumbent.economics.planes;
}

function OpexC97AirMaxPlanes(airport, newAirportCount)
{
  local isSmall = (airport.type == AIAirport.AT_SMALL || airport.type == AIAirport.AT_COMMUTER);
  return (newAirportCount == 2) ? 3 : (isSmall ? 4 : 6);
}

/* C97 : contrairement a V92.2, aucun moteur n'est d'abord reduit a son n de
 * profit maximal. Chaque point (moteur,n) est score directement. fixedPlanes=n
 * est volontaire : serviceScan ferait precisement la reduction V92 a eviter. */
function OpexC97AirFindBest(catalog, plan, kDec)
{
  if (catalog == null || plan == null || !("airport" in plan) || plan.airport == null
      || !("distance" in plan) || !("monthlyPax" in plan)
      || catalog.airPlaneChoicesByAirport == null
      || !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return null;
  local newAirportCount = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local maxPlanes = OpexC97AirMaxPlanes(plan.airport, newAirportCount);
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local best = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    for (local n = 1; n <= maxPlanes; n++) {
      local economics = OpexAirEconomics(catalog, plan.airport, plane, plan.distance, plan.monthlyPax,
          infrastructureMaintenance, 0, newAirportCount, 0, n, false, false);
      local point = OpexC97AirPoint(catalog, plan, plane, economics, kDec);
      if (OpexC97AirPointBetter(point, best)) best = point;
    }
  }
  return best;
}

function OpexC97ProbeAirEngine(catalog, plan)
{
  if (!C97_AIR_C69_ENGINE_PROBE || catalog == null || plan == null
      || !("plane" in plan) || plan.plane == null
      || !("economics" in plan) || plan.economics == null) return;
  local kDec = OpexC69CachedKDec();
  local baseline = OpexC97AirPoint(catalog, plan, plan.plane, plan.economics, kDec);
  local best = OpexC97AirFindBest(catalog, plan, kDec);
  if (baseline == null || best == null) return;
  local src = (("siteA" in plan) && plan.siteA != null && ("town" in plan.siteA)
      && plan.siteA.town != null && ("id" in plan.siteA.town)) ? plan.siteA.town.id : -1;
  local dst = (("siteB" in plan) && plan.siteB != null && ("town" in plan.siteB)
      && plan.siteB.town != null && ("id" in plan.siteB.town)) ? plan.siteB.town.id : -1;
  local route = ("arm" in plan) ? plan.arm : "unknown";
  local disagree = baseline.plane.id != best.plane.id ? 1 : 0;
  AILog.Info("C97_ENGINE route=" + route + " src=" + src + " dst=" + dst
      + " airport_type=" + plan.airport.type
      + " default_engine=" + baseline.plane.id
      + " default_name=" + OpexPlaneName(baseline.plane.id)
      + " default_n=" + baseline.economics.planes
      + " c97_engine=" + best.plane.id + " c97_name=" + OpexPlaneName(best.plane.id)
      + " c97_n=" + best.economics.planes
      + " K_dec=" + kDec + " disagree=" + disagree
      + " default_P=" + baseline.economics.profitAnnual
      + " default_P_cal=" + baseline.calibratedProfit
      + " default_C=" + baseline.financeCapital + " default_score=" + baseline.score
      + " c97_P=" + best.economics.profitAnnual + " c97_P_cal=" + best.calibratedProfit
      + " c97_C=" + best.financeCapital + " c97_score=" + best.score
      + " default_price=" + baseline.plane.price + " c97_price=" + best.plane.price
      + " default_capacity=" + baseline.plane.capacity + " c97_capacity=" + best.plane.capacity
      + " default_speed=" + baseline.plane.speed + " c97_speed=" + best.plane.speed
      + " default_big=" + (("isBig" in baseline.plane) && baseline.plane.isBig ? 1 : 0)
      + " c97_big=" + (("isBig" in best.plane) && best.plane.isBig ? 1 : 0));
}

function OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan)
{
  if (V92_AIR_SERVICE_CHOICE && routeChoice != null && ("alternate" in routeChoice)
      && routeChoice.alternate != null && routeChoice.alternate.economics != null
      && routeChoice.alternate.economics.profitAnnual > 0) {
    local alt = routeChoice.alternate;
    local townA = plan.siteA.town.id;
    local townB = plan.siteB.town.id;
    if (townA > townB) {
      local swap = townA;
      townA = townB;
      townB = swap;
    }
    local key = townA + "|" + townB + "|" + plan.airport.type;
    plan.v92PairKey <- key;
    plan.v92Role <- "service";
    local cheap = {};
    foreach (k, v in plan) cheap[k] <- v;
    cheap.plane = alt.plane;
    cheap.economics = alt.economics;
    cheap.planes = alt.economics.planes;
    cheap.capital = alt.economics.capital;
    cheap.v92Role = "cheap";
    if ("targetPlanes" in cheap) cheap.targetPlanes = alt.economics.planes;
    if (projects != null) projects.append(cheap);
    if (OpexAirPlanBetter(cheap, bestPlan)) bestPlan = cheap;
  }
  if (projects != null) projects.append(plan);
  if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
  return bestPlan;
}

/* C82 : arbitrage d'appareil par route evalue sur les profits et ROI calibres par moteur.
 * L'objet economics renvoye reste brut (non modifie). */
function OpexC82ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding)
{
  local bestPlane = selectedPlane;
  local bestEconomics = selectedEconomics;
  local bestK = (selectedPlane != null) ? OpexC82EngineFactor(selectedPlane.id) : 1.0;
  local bestCalProfit = (selectedEconomics != null) ? (selectedEconomics.profitAnnual * bestK) : 0.0;
  local bestCalRoi = (selectedEconomics != null) ? (selectedEconomics.roi * bestK) : 0.0;
  local bestScore = 0.0;

  local kDec = 0;
  if (C69_BOTTLENECK_PROBE || C72_PLANE_CHOICE == 2) {
    kDec = OpexC69CachedKDec();
  }

  if (C72_PLANE_CHOICE == 2 && selectedEconomics != null) {
    local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
    bestScore = denom > 0 ? (bestCalProfit.tofloat() * 1000.0) / denom : 0.0;
  }

  local rawPlane = null;
  local rawEconomics = null;
  local rawScore = 0.0;
  local evalCount = 0;

  if (C69_BOTTLENECK_PROBE) {
    if (selectedEconomics != null) {
      evalCount = 1;
      rawPlane = selectedPlane;
      rawEconomics = selectedEconomics;
      local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
      rawScore = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
    }
  }

  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, false, false, paymentDistance);
    if (economics == null) continue;

    local k = OpexC82EngineFactor(plane.id);
    local calProfit = economics.profitAnnual * k;
    local calRoi = economics.roi * k;

    if (C72_PLANE_CHOICE == 1) {
      if (bestEconomics == null || calRoi > bestCalRoi ||
          (calRoi == bestCalRoi && calProfit > bestCalProfit)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    } else if (C72_PLANE_CHOICE == 2) {
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (calProfit.tofloat() * 1000.0) / curDenom : 0.0;
      if (bestEconomics == null || curScore > bestScore ||
          (curScore == bestScore && calProfit > bestCalProfit)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestScore = curScore;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    } else {
      if (bestEconomics == null || calProfit > bestCalProfit ||
          (calProfit == bestCalProfit && calRoi > bestCalRoi)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    }

    if (C69_BOTTLENECK_PROBE) {
      evalCount++;
      if (C72_PLANE_CHOICE == 1) {
        if (rawEconomics == null || economics.roi > rawEconomics.roi ||
            (economics.roi == rawEconomics.roi && economics.profitAnnual > rawEconomics.profitAnnual)) {
          rawPlane = plane;
          rawEconomics = economics;
        }
      } else if (C72_PLANE_CHOICE == 2) {
        local curDenom = economics.capital > kDec ? economics.capital : kDec;
        local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
        if (rawEconomics == null || curScore > rawScore ||
            (curScore == rawScore && economics.profitAnnual > rawEconomics.profitAnnual)) {
          rawPlane = plane;
          rawEconomics = economics;
          rawScore = curScore;
        }
      } else {
        if (rawEconomics == null || economics.profitAnnual > rawEconomics.profitAnnual ||
            (economics.profitAnnual == rawEconomics.profitAnnual && economics.roi > rawEconomics.roi)) {
          rawPlane = plane;
          rawEconomics = economics;
        }
      }
    }
  }

  if (C69_BOTTLENECK_PROBE && evalCount >= 2) {
    C82_CHOICE_CALLS++;
    local idBrut = (rawPlane != null) ? rawPlane.id : -1;
    local idCalibre = (bestPlane != null) ? bestPlane.id : -1;
    if (idCalibre != idBrut) {
      C82_CHOICE_DIFFER++;
      local kBrut = (idBrut >= 0) ? OpexC82EngineFactor(idBrut) : 1.0;
      local kCalibre = (idCalibre >= 0) ? OpexC82EngineFactor(idCalibre) : 1.0;
      OpexC69Log("phase=c82_choice raw=" + idBrut + " cal=" + idCalibre
          + " k_raw=" + kBrut + " k_cal=" + kCalibre + " c72=" + C72_PLANE_CHOICE);
    }
  }

  return { plane = bestPlane, economics = bestEconomics };
}

/* C68 : transforme le contre-factuel passif M3 en intervention minimale. Le caller a deja choisi
 * le type d'aeroport, les sites, la paire et la demande avec le chemin historique. Sous le switch,
 * on ne change donc que l'appareil et l'economie de cette route, avec exactement le meme modele
 * OpexAirEconomics que M3. Sous 0, le resultat est strictement le couple historique. */
/* C80 tranche 5 : `memoKey` identifie la route (villes ou gares, type d'aeroport, avion du combo).
 * Etat 1 (generation complete) : choix complet, memorise. Etat 2 (mise a jour apres chantier) :
 * seule l'economie de l'avion memorise est recalculee ; sans memo valide, choix complet memorise.
 * Un appel plafonne en capital (construction, `maxCapital` > 0) ne lit ni n'ecrit le memo. */
function OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
                                  newAirportCount, opcodePadding, choice)
{
  if (choice == null || choice.plane == null || choice.economics == null) return choice;
  local targetEconomics = OpexAirTargetEconomics(catalog, airport, choice.plane, distance, monthlyPax,
      infrastructureMaintenance, newAirportCount, opcodePadding);
  if (targetEconomics != null) {
    choice.targetEconomics <- targetEconomics;
    choice.targetPlanes <- targetEconomics.planes;
  }
  return choice;
}

/* Lit la soute des avions deja en vol de cette compagnie, une fois par mois.
 * AIVehicleList ne voit pas les avions des autres compagnies. */
function OpexAirLearnMailCaps(catalog)
{
  if (catalog == null || !("mailCargo" in catalog) || catalog.mailCargo < 0
      || !("paxCargo" in catalog) || catalog.paxCargo < 0) return;
  local now = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now);
  if (AIR_MAIL_LEARN_MONTH == month) return;
  AIR_MAIL_LEARN_MONTH = month;
  local list = AIVehicleList();
  list.Valuate(AIVehicle.GetVehicleType);
  list.KeepValue(AIVehicle.VT_AIR);
  for (local v = list.Begin(); !list.IsEnd(); v = list.Next()) {
    local engine = AIVehicle.GetEngineType(v);
    if (engine < 0 || (engine in AIR_MAIL_CAP)) continue;
    local pax = AIVehicle.GetCapacity(v, catalog.paxCargo);
    local mail = AIVehicle.GetCapacity(v, catalog.mailCargo);
    if (pax > 0 && mail >= 0) AIR_MAIL_CAP.rawset(engine, mail);
  }
}

function OpexAirApplyKnownMail(plane)
{
  if (plane == null || !("id" in plane)) return;
  if (plane.id in AIR_MAIL_CAP) plane.mailCapacity = AIR_MAIL_CAP[plane.id];
}

function OpexAirPlaneInRange(plane, distance)
{
  return plane != null && !(plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance);
}

function OpexAirServiceBetter(candidate, incumbent)
{
  if (candidate == null || candidate.profitAnnual <= 0) return false;
  if (incumbent == null) return true;
  if (candidate.profitAnnual > incumbent.profitAnnual) return true;
  if (candidate.profitAnnual == incumbent.profitAnnual && candidate.roi > incumbent.roi) return true;
  return false;
}

/* V92 : pour chaque moteur compatible, le nombre d'appareils au meilleur profit,
 * puis la meilleure variante a un seul appareil dont le prix ne depasse pas
 * le gros jet le moins cher (ou le moins cher tout court sur un petit aeroport). */
function OpexAirChooseRouteService(catalog, airport, selectedPlane, distance, monthlyPax,
                                   infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
                                   paymentDistance = 0)
{
  OpexAirLearnMailCaps(catalog);
  local bestPlane = null;
  local bestEcon = null;
  local cheapPlane = null;
  local cheapEcon = null;
  if (airport == null || catalog == null || catalog.airPlaneChoicesByAirport == null
      || !(airport.type in catalog.airPlaneChoicesByAirport)) {
    local econ = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        1, false, false, false, false, paymentDistance);
    return { plane = selectedPlane, economics = econ };
  }
  local choices = catalog.airPlaneChoicesByAirport[airport.type];
  local cheapLimit = -1;
  local anyPrice = -1;
  foreach (plane in choices) {
    if (!OpexAirPlaneInRange(plane, distance)) continue;
    OpexAirApplyKnownMail(plane);
    if (anyPrice < 0 || plane.price < anyPrice) anyPrice = plane.price;
    if (("isBig" in plane) && plane.isBig && (cheapLimit < 0 || plane.price < cheapLimit)) {
      cheapLimit = plane.price;
    }
  }
  if (cheapLimit < 0) cheapLimit = anyPrice;
  if (selectedPlane != null) OpexAirApplyKnownMail(selectedPlane);

  foreach (plane in choices) {
    if (!OpexAirPlaneInRange(plane, distance)) continue;
    local scanned = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, true, false, false, paymentDistance);
    if (OpexAirServiceBetter(scanned, bestEcon)) {
      bestPlane = plane;
      bestEcon = scanned;
    }
    if (cheapLimit >= 0 && plane.price <= cheapLimit) {
      local one = (scanned != null && scanned.planes == 1) ? scanned
          : OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
              infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
              1, false, false, false, false, paymentDistance);
      if (OpexAirServiceBetter(one, cheapEcon)) {
        cheapPlane = plane;
        cheapEcon = one;
      }
    }
  }
  if (bestPlane == null && selectedPlane != null) {
    bestEcon = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        1, false, false, false, false, paymentDistance);
    bestPlane = selectedPlane;
  }
  local choice = { plane = bestPlane, economics = bestEcon };
  if (cheapPlane != null && bestPlane != null && cheapEcon != null
      && (cheapPlane.id != bestPlane.id || cheapEcon.planes != bestEcon.planes)) {
    choice.alternate <- { plane = cheapPlane, economics = cheapEcon };
  }
  return choice;
}

function OpexAirChooseRoutePlane(catalog, airport, selectedPlane, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount,
                                 opcodePadding, memoKey = null, paymentDistance = 0)
{
  if (V92_AIR_SERVICE_CHOICE) {
    return OpexAirChooseRouteService(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, paymentDistance);
  }
  /* Le memo historique ne stocke qu'un EngineID : il perdrait decisionEconomics
   * (C111) et l'economie replay conditionnelle C115. C116.4 ne change plus
   * l'economie de generation : il doit donc reutiliser exactement le memo C68. */
  if (C111_AIR_C100_DECISION_SHADOW
      || (C115_AIR_C100_CAPITAL_REPLAY && !C116_AIR_MARGINAL_CAPITAL)
      || !C80_AIR_CHOICE_MEMO || memoKey == null
      || maxCapital != 0 || AIR_CHOICE_MEMO_STATE == 0) {
    local choice = OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, paymentDistance);
    if (C84_AIR_TARGET_FLEET) {
      return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
          newAirportCount, opcodePadding, choice);
    }
    return choice;
  }
  if (AIR_CHOICE_MEMO_STATE == 2 && (memoKey in AIR_CHOICE_MEMO)) {
    local planeId = AIR_CHOICE_MEMO[memoKey];
    local memoPlane = null;
    if (planeId == selectedPlane.id) {
      memoPlane = selectedPlane;
    } else if (airport.type in catalog.airPlaneChoicesByAirport) {
      foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
        if (plane.id == planeId) { memoPlane = plane; break; }
      }
    }
    if (memoPlane != null && (memoPlane.maxOrderDistance <= 0 || distance <= memoPlane.maxOrderDistance)) {
      local economics = OpexAirEconomics(catalog, airport, memoPlane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, false, false, paymentDistance);
      if (economics != null) {
        local choice = { plane = memoPlane, economics = economics };
        if (C84_AIR_TARGET_FLEET) {
          return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
              newAirportCount, opcodePadding, choice);
        }
        return choice;
      }
    }
  }
  local choice = OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, paymentDistance);
  if (choice.plane != null) AIR_CHOICE_MEMO.rawset(memoKey, choice.plane.id);
  if (C84_AIR_TARGET_FLEET) {
    return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
        newAirportCount, opcodePadding, choice);
  }
  return choice;
}

/* C101 : corrige uniquement le CHOIX DU MOTEUR. Chaque appareil doit d'abord
 * rester viable sous l'economie historique ; le classement entre appareils se
 * fait ensuite avec le timing physique C100.1. L'economie retournee au plan est
 * toujours l'economie historique du moteur gagnant : admission, capital, score
 * projet et expansion restent donc sur le modele du defaut. */
function OpexC101ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local viable = [];
  local rawPlane = selectedEconomics != null ? selectedPlane : null;
  local rawLegacy = selectedEconomics;

  if (selectedPlane != null && selectedEconomics != null) {
    viable.append({ plane = selectedPlane, legacy = selectedEconomics });
  }

  local choices = catalog.airPlaneChoicesByAirport[airport.type];
  foreach (plane in choices) {
    if (selectedPlane != null && plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;

    /* La viabilite/admission reste volontairement celle du defaut. */
    local legacy = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (legacy == null) continue;
    viable.append({ plane = plane, legacy = legacy });
    if (rawLegacy == null || legacy.profitAnnual > rawLegacy.profitAnnual ||
        (legacy.profitAnnual == rawLegacy.profitAnnual && legacy.roi > rawLegacy.roi)) {
      rawPlane = plane;
      rawLegacy = legacy;
    }
  }

  if (rawPlane == null || rawLegacy == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }

  local bestPlane = rawPlane;
  local bestLegacy = rawLegacy;
  local bestPhysical = null;
  foreach (item in viable) {
    /* Le gagnant C68 maximise deja le profit legacy. Un candidat qui exige
     * davantage de capital ne peut donc pas justifier sa substitution sans
     * ralentir l'expansion : C101 reste strictement capital-neutre. */
    if (item.legacy.capital > rawLegacy.capital) continue;
    local physical = OpexAirEconomics(catalog, airport, item.plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true);
    if (physical == null) continue;
    if (bestPhysical == null || physical.profitAnnual > bestPhysical.profitAnnual ||
        (physical.profitAnnual == bestPhysical.profitAnnual && physical.roi > bestPhysical.roi)) {
      bestPlane = item.plane;
      bestLegacy = item.legacy;
      bestPhysical = physical;
    }
  }

  if (bestPhysical == null) return { plane = rawPlane, economics = rawLegacy };
  if (C69_BOTTLENECK_PROBE && rawPlane != null && rawLegacy != null
      && rawPlane.id != bestPlane.id) {
    OpexC69Log("phase=c101_choice policy=capital_neutral dist=" + distance
        + " raw_id=" + rawPlane.id + " raw_name=" + OpexPlaneName(rawPlane.id)
        + " raw_price=" + rawPlane.price + " raw_P=" + rawLegacy.profitAnnual
        + " raw_C=" + rawLegacy.capital + " raw_roi=" + rawLegacy.roi
        + " pick_id=" + bestPlane.id + " pick_name=" + OpexPlaneName(bestPlane.id)
        + " pick_price=" + bestPlane.price + " pick_legacy_P=" + bestLegacy.profitAnnual
        + " pick_legacy_C=" + bestLegacy.capital + " pick_legacy_roi=" + bestLegacy.roi
        + " pick_physical_P=" + bestPhysical.profitAnnual + " pick_physical_C=" + bestPhysical.capital
        + " pick_physical_roi=" + bestPhysical.roi);
  }
  return { plane = bestPlane, economics = bestLegacy };
}

/* C103 : isolation causale du signal du premier C100 positif.
 *
 * On rejoue uniquement son CLASSEMENT moteur : vitesse NoAI directe et ancien
 * helper de manoeuvre pessimiste. Ce score n'est jamais retourne au portefeuille.
 * Chaque candidat doit rester calculable sous l'economie legacy, et le gagnant
 * retourne son objet legacy : admission, capital et score projet restent donc
 * strictement ceux du defaut. Contrairement a C101, aucun filtre capital-neutre
 * n'est ajoute, afin de reproduire fidelement l'argmax du premier C100. */
function OpexC103ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local bestPlane = null;
  local bestLegacy = null;
  local bestReplay = null;
  local rawPlane = selectedEconomics != null ? selectedPlane : null;
  local rawLegacy = selectedEconomics;

  local choices = catalog.airPlaneChoicesByAirport[airport.type];
  foreach (plane in choices) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;

    local legacy = null;
    if (selectedPlane != null && plane.id == selectedPlane.id) {
      legacy = selectedEconomics;
    } else {
      legacy = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    }
    if (legacy == null) continue;

    if (rawLegacy == null || legacy.profitAnnual > rawLegacy.profitAnnual ||
        (legacy.profitAnnual == rawLegacy.profitAnnual && legacy.roi > rawLegacy.roi)) {
      rawPlane = plane;
      rawLegacy = legacy;
    }

    local replay = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, false, true);
    if (replay == null) continue;
    if (bestReplay == null || replay.profitAnnual > bestReplay.profitAnnual ||
        (replay.profitAnnual == bestReplay.profitAnnual && replay.roi > bestReplay.roi)) {
      bestPlane = plane;
      bestLegacy = legacy;
      bestReplay = replay;
    }
  }

  if (bestPlane == null || bestLegacy == null || bestReplay == null) {
    return { plane = rawPlane, economics = rawLegacy };
  }
  if (C69_BOTTLENECK_PROBE && rawPlane != null && rawLegacy != null
      && rawPlane.id != bestPlane.id) {
    OpexC69Log("phase=c103_choice policy=c100_rank_replay dist=" + distance
        + " raw_id=" + rawPlane.id + " raw_name=" + OpexPlaneName(rawPlane.id)
        + " raw_price=" + rawPlane.price + " raw_P=" + rawLegacy.profitAnnual
        + " raw_C=" + rawLegacy.capital + " raw_roi=" + rawLegacy.roi
        + " pick_id=" + bestPlane.id + " pick_name=" + OpexPlaneName(bestPlane.id)
        + " pick_price=" + bestPlane.price + " pick_legacy_P=" + bestLegacy.profitAnnual
        + " pick_legacy_C=" + bestLegacy.capital + " pick_legacy_roi=" + bestLegacy.roi
        + " pick_replay_P=" + bestReplay.profitAnnual + " pick_replay_C=" + bestReplay.capital
        + " pick_replay_roi=" + bestReplay.roi);
  }
  return { plane = bestPlane, economics = bestLegacy };
}

/* C104 : argmax profit/ROI sous un timing force, sans jamais retourner ce choix
 * au chemin decisionnel. mode=0 legacy, 1 replay du premier C100, 2 C100.1. */
function OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
                              infrastructureMaintenance, maxCapital,
                              newAirportCount, opcodePadding, mode, paymentDistance = 0)
{
  local bestPlane = null;
  local bestEconomics = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = null;
    if (mode == 1) {
      economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, false, true, paymentDistance);
    } else if (mode == 2) {
      economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, true, false, paymentDistance);
    } else {
      economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
          0, false, false, false, false, paymentDistance);
    }
    if (economics == null) continue;
    if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
        (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
      bestPlane = plane;
      bestEconomics = economics;
    }
  }
  if (bestPlane == null || bestEconomics == null) return null;
  return { plane = bestPlane, economics = bestEconomics };
}

/* C106 candidat : frontiere marginale purement relative sur l'economie C100.1.
 * On part du profit physique maximal. Tant qu'un palier moins capitalistique
 * offre le meilleur profit sous ce capital et que le ROI marginal de l'upgrade
 * reste inferieur au ROI de ce palier, on redescend. Aucun montant de caisse,
 * EngineID ni seuil de richesse n'intervient ; le seul seuil est l'egalite des
 * deux rendements (ratio dimensionless = 1). Son usage reste passif sous C104. */
function OpexC106MarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
                                        infrastructureMaintenance, maxCapital,
                                        newAirportCount, opcodePadding,
                                        relativeRoiPermille = 1000)
{
  local items = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics != null && economics.profitAnnual > 0) {
      items.append({ plane = plane, economics = economics });
    }
  }
  if (items.len() == 0) return null;

  local current = null;
  foreach (item in items) {
    if (current == null || item.economics.profitAnnual > current.economics.profitAnnual ||
        (item.economics.profitAnnual == current.economics.profitAnnual
         && item.economics.roi > current.economics.roi)) current = item;
  }

  while (true) {
    local runner = null;
    foreach (item in items) {
      if (item.economics.capital >= current.economics.capital) continue;
      if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual ||
          (item.economics.profitAnnual == runner.economics.profitAnnual
           && item.economics.roi > runner.economics.roi)) runner = item;
    }
    if (runner == null) return current;
    local deltaCapital = current.economics.capital - runner.economics.capital;
    local deltaProfit = current.economics.profitAnnual - runner.economics.profitAnnual;
    if (deltaCapital <= 0 || deltaProfit <= 0) return runner;
    local marginalRoi = (deltaProfit * 1000.0) / deltaCapital;
    if (marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille) return current;
    current = runner;
  }
}

/* C107 candidat passif : meme test marginal que C106, mais une seule marche.
 * Partir de l'argmax profit C100.1, prendre le meilleur profit strictement moins
 * capitalistique, puis refuser l'upgrade si son rendement marginal est inferieur
 * au ROI du palier moins cher. Pas de recursion : on evite ainsi de descendre
 * 218 -> 217 -> 216 quand seul le premier upgrade est mal remunere. */
function OpexC107OneStepMarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
                                               infrastructureMaintenance, maxCapital,
                                               newAirportCount, opcodePadding,
                                               relativeRoiPermille = 1000)
{
  local items = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics != null && economics.profitAnnual > 0) {
      items.append({ plane = plane, economics = economics });
    }
  }
  if (items.len() == 0) return null;

  local current = null;
  foreach (item in items) {
    if (current == null || item.economics.profitAnnual > current.economics.profitAnnual ||
        (item.economics.profitAnnual == current.economics.profitAnnual
         && item.economics.roi > current.economics.roi)) current = item;
  }

  local runner = null;
  foreach (item in items) {
    if (item.economics.capital >= current.economics.capital) continue;
    if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual ||
        (item.economics.profitAnnual == runner.economics.profitAnnual
         && item.economics.roi > runner.economics.roi)) runner = item;
  }
  if (runner == null) return current;
  local deltaCapital = current.economics.capital - runner.economics.capital;
  local deltaProfit = current.economics.profitAnnual - runner.economics.profitAnnual;
  if (deltaCapital <= 0 || deltaProfit <= 0) return runner;
  local marginalRoi = (deltaProfit * 1000.0) / deltaCapital;
  if (marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille) return current;
  return runner;
}

/* C106 actif : le rendement marginal ne sert qu'au choix du moteur. Comme C103,
 * le portefeuille recoit ensuite l'economie legacy du moteur retenu afin de ne
 * pas confondre choix d'equipement et requalification globale du modele AIR. */
function OpexC106ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local choice = OpexC106MarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  if (choice == null || !("plane" in choice) || choice.plane == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  local legacy = null;
  if (selectedPlane != null && selectedEconomics != null && choice.plane.id == selectedPlane.id) {
    legacy = selectedEconomics;
  } else {
    legacy = OpexAirEconomics(catalog, airport, choice.plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (legacy == null) return { plane = selectedPlane, economics = selectedEconomics };
  return { plane = choice.plane, economics = legacy };
}

/* C106 candidat principal : score C69 sur l'economie C100.1. */
function OpexC106PhysicalC69Choice(catalog, airport, distance, monthlyPax,
                                   infrastructureMaintenance, maxCapital,
                                   newAirportCount, opcodePadding)
{
  local kDec = C69_DECISION_BOTTLENECK ? OpexC69CachedKDec() : 0;
  local margin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local best = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics == null || economics.profitAnnual <= 0) continue;
    local financeCapital = economics.capital + margin;
    if (("immobilise" in economics) && economics.immobilise > 0) financeCapital += economics.immobilise;
    local denom = financeCapital > kDec ? financeCapital : kDec;
    if (denom <= 0) continue;
    local score = OpexProjectScore(economics.profitAnnual, denom);
    local point = { plane = plane, economics = economics, financeCapital = financeCapital, score = score };
    if (best == null || point.score > best.score
        || (point.score == best.score && economics.profitAnnual > best.economics.profitAnnual)
        || (point.score == best.score && economics.profitAnnual == best.economics.profitAnnual
            && financeCapital < best.financeCapital)) best = point;
  }
  return best;
}

/* C106 : interpolation continue entre profit pur (alpha=0) et ROI-like
 * (alpha=1), sur le capital de financement AIR. alpha est code en seiziemes
 * afin de n'utiliser que sqrt(), deja disponible dans NoAI/Squirrel. */
function OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
                                     infrastructureMaintenance, maxCapital,
                                     newAirportCount, opcodePadding, alpha16)
{
  local margin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local best = null;
  local bestScore = -1.0;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics == null || economics.profitAnnual <= 0) continue;
    local financeCapital = economics.capital + margin;
    if (("immobilise" in economics) && economics.immobilise > 0) financeCapital += economics.immobilise;
    if (financeCapital <= 0) continue;
    local c = financeCapital.tofloat();
    local r2 = sqrt(c);
    local r4 = sqrt(r2);
    local r8 = sqrt(r4);
    local r16 = sqrt(r8);
    local denom = 1.0;
    if ((alpha16 & 8) != 0) denom *= r2;
    if ((alpha16 & 4) != 0) denom *= r4;
    if ((alpha16 & 2) != 0) denom *= r8;
    if ((alpha16 & 1) != 0) denom *= r16;
    local score = economics.profitAnnual.tofloat() / denom;
    if (best == null || score > bestScore
        || (score == bestScore && economics.profitAnnual > best.economics.profitAnnual)
        || (score == bestScore && economics.profitAnnual == best.economics.profitAnnual
            && financeCapital < best.financeCapital)) {
      best = { plane = plane, economics = economics, financeCapital = financeCapital, score = score };
      bestScore = score;
    }
  }
  return best;
}

/* C108 candidat passif : regularisation de l'avantage de vitesse, sans capital
 * ni seuil de richesse. Le score est P / v^beta avec beta en quarts. Comme le
 * facteur d'unite de vitesse est commun a tous les moteurs, le classement est
 * invariant a un changement d'unite ; il s'agit d'une penalite relative, pas
 * d'un nouveau modele physique de temps de trajet. */
function OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
                                         infrastructureMaintenance, maxCapital,
                                         newAirportCount, opcodePadding, beta4)
{
  local best = null;
  local bestScore = -1.0;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    if (plane.speed <= 0) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics == null || economics.profitAnnual <= 0) continue;
    local v = plane.speed.tofloat();
    local r2 = sqrt(v);
    local r4 = sqrt(r2);
    local denom = 1.0;
    if (beta4 == 1) denom = r4;
    else if (beta4 == 2) denom = r2;
    else if (beta4 == 3) denom = r2 * r4;
    else if (beta4 == 4) denom = v;
    local score = economics.profitAnnual.tofloat() / denom;
    if (best == null || score > bestScore
        || (score == bestScore && economics.profitAnnual > best.economics.profitAnnual)
        || (score == bestScore && economics.profitAnnual == best.economics.profitAnnual
            && economics.capital < best.economics.capital)) {
      best = { plane = plane, economics = economics, score = score };
      bestScore = score;
    }
  }
  return best;
}

/* C109 candidat passif : elasticite du profit au gain de vitesse.
 * On compare l'argmax de profit C100.1 au meilleur moteur strictement plus lent.
 * L'upgrade rapide n'est retenu que si (dP/P) / (dv/v) depasse un seuil relatif.
 * Aucun prix, capital, montant de caisse, EngineID ou temps fixe n'intervient. */
function OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
                                             infrastructureMaintenance, maxCapital,
                                             newAirportCount, opcodePadding,
                                             relativeElasticityPermille = 1000)
{
  local items = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    if (plane.speed <= 0) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, true, false);
    if (economics != null && economics.profitAnnual > 0) {
      items.append({ plane = plane, economics = economics });
    }
  }
  if (items.len() == 0) return null;

  local current = null;
  foreach (item in items) {
    if (current == null || item.economics.profitAnnual > current.economics.profitAnnual ||
        (item.economics.profitAnnual == current.economics.profitAnnual
         && item.economics.roi > current.economics.roi)) current = item;
  }

  local runner = null;
  foreach (item in items) {
    if (item.plane.speed >= current.plane.speed) continue;
    if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual ||
        (item.economics.profitAnnual == runner.economics.profitAnnual
         && item.economics.roi > runner.economics.roi)) runner = item;
  }
  if (runner == null) return current;
  local deltaProfit = current.economics.profitAnnual - runner.economics.profitAnnual;
  local deltaSpeed = current.plane.speed - runner.plane.speed;
  if (deltaProfit <= 0 || deltaSpeed <= 0 || runner.economics.profitAnnual <= 0 || runner.plane.speed <= 0) {
    return runner;
  }
  local profitGainPermille = (deltaProfit * 1000.0) / runner.economics.profitAnnual;
  local speedGainPermille = (deltaSpeed * 1000.0) / runner.plane.speed;
  if (profitGainPermille * 1000.0 >= speedGainPermille * relativeElasticityPermille) return current;
  return runner;
}

/* C116 passif : regularisation du C68 legacy sur le cout incremental de
 * l'upgrade, sans timing C100/C100.1. */
function OpexC116LegacyIncrementalCandidates(catalog, airport, distance, monthlyPax,
                                             infrastructureMaintenance, maxCapital,
                                             newAirportCount, opcodePadding, legacy)
{
  if (legacy == null || legacy.plane == null || legacy.economics == null
      || legacy.economics.capital <= 0 || legacy.economics.profitAnnual <= 0) return null;
  local runner = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null || economics.capital <= 0 || economics.profitAnnual <= 0
        || economics.capital >= legacy.economics.capital) continue;
    if (runner == null || economics.profitAnnual > runner.economics.profitAnnual
        || (economics.profitAnnual == runner.economics.profitAnnual
            && economics.roi > runner.economics.roi)) runner = { plane = plane, economics = economics };
  }
  if (runner == null) return { runner = legacy, gate = legacy, score = legacy, marginal = legacy,
      opportunity = legacy, opportunitySteps = 0,
      deltaCapital = 0, deltaProfit = 0, kDec = OpexC69CachedKDec(), legacyScore = 0.0,
      runnerScore = 0.0, marginalRoi = 0.0 };

  local kDec = OpexC69CachedKDec();
  local deltaCapital = legacy.economics.capital - runner.economics.capital;
  local deltaProfit = legacy.economics.profitAnnual - runner.economics.profitAnnual;
  local legacyDenom = legacy.economics.capital > kDec ? legacy.economics.capital : kDec;
  local runnerDenom = runner.economics.capital > kDec ? runner.economics.capital : kDec;
  local legacyScore = legacyDenom > 0 ? (legacy.economics.profitAnnual.tofloat() * 1000.0) / legacyDenom : 0.0;
  local runnerScore = runnerDenom > 0 ? (runner.economics.profitAnnual.tofloat() * 1000.0) / runnerDenom : 0.0;
  local marginalRoi = deltaCapital > 0 ? (deltaProfit.tofloat() * 1000.0) / deltaCapital : 0.0;
  local gateChoice = legacy;
  local scoreChoice = legacy;
  local marginalChoice = legacy;
  local opportunityChoice = legacy;
  local opportunitySteps = 0;
  if (kDec > 0) {
    if (deltaCapital > kDec) gateChoice = runner;
    if (runnerScore > legacyScore) scoreChoice = runner;
    if (deltaCapital > kDec && deltaProfit > 0 && marginalRoi < runnerScore) marginalChoice = runner;

    /* C116.1 passif : cout d'opportunite relatif a chaque cran de la frontiere.
     * Refuser l'upgrade si son gain relatif de profit est inferieur a la part
     * d'un budget de decision K_dec qu'il immobilise : dP/P_runner < dC/K_dec. */
    local current = legacy;
    while (true) {
      local next = null;
      foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
        if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
        local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
            infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
        if (economics == null || economics.capital <= 0 || economics.profitAnnual <= 0
            || economics.capital >= current.economics.capital) continue;
        if (next == null || economics.profitAnnual > next.economics.profitAnnual
            || (economics.profitAnnual == next.economics.profitAnnual
                && economics.roi > next.economics.roi)) next = { plane = plane, economics = economics };
      }
      if (next == null) break;
      local stepCapital = current.economics.capital - next.economics.capital;
      local stepProfit = current.economics.profitAnnual - next.economics.profitAnnual;
      local relativeProfit = next.economics.profitAnnual > 0
          ? stepProfit.tofloat() / next.economics.profitAnnual.tofloat() : 0.0;
      local relativeCapital = stepCapital.tofloat() / kDec.tofloat();
      if (!(stepProfit > 0 && relativeProfit < relativeCapital)) break;
      current = next;
      opportunitySteps++;
    }
    opportunityChoice = current;
  }
  return { runner = runner, gate = gateChoice, score = scoreChoice, marginal = marginalChoice,
      opportunity = opportunityChoice, opportunitySteps = opportunitySteps,
      deltaCapital = deltaCapital, deltaProfit = deltaProfit, kDec = kDec,
      legacyScore = legacyScore, runnerScore = runnerScore, marginalRoi = marginalRoi };
}

function OpexC104FormatAirChoice(prefix, choice)
{
  if (choice == null || !("economics" in choice) || choice.economics == null) return prefix + "_id=-1";
  local p = choice.plane;
  local e = choice.economics;
  return prefix + "_id=" + p.id
      + " " + prefix + "_price=" + p.price
      + " " + prefix + "_cap=" + p.capacity
      + " " + prefix + "_speed=" + p.speed
      + " " + prefix + "_n=" + e.planes
      + " " + prefix + "_P=" + e.profitAnnual
      + " " + prefix + "_R=" + e.revenueAnnual
      + " " + prefix + "_run=" + e.runningAnnual
      + " " + prefix + "_amort=" + e.amortAnnual
      + " " + prefix + "_C=" + e.capital
      + " " + prefix + "_imm=" + e.immobilise
      + " " + prefix + "_roi=" + e.roi
      + " " + prefix + "_days=" + e.oneWayDays
      + " " + prefix + "_trips=" + e.tripsPerMonth
      + " " + prefix + "_rating=" + e.stationRating
      + " " + prefix + "_mcap=" + e.monthlyCapacity
      + " " + prefix + "_carried=" + e.carried;
}

/* C116.2 passif : serialisation du snapshot du portefeuille precedent. Aucun
 * calcul de projet n'est declenche ici ; seules des valeurs deja memorisees sont
 * lues. p1/p2/p3 sont les trois premiers projets AIR finançables dans l'ordre
 * reel du portefeuille au dernier OpexProjectSelectAffordable. */
function OpexC116SnapshotBest(frontier, deltaCapital)
{
  if (frontier == null || deltaCapital <= 0) return null;
  local best = null;
  foreach (point in frontier) {
    if (point.gap > deltaCapital) continue;
    if (best == null || point.hurdle > best.hurdle
        || (point.hurdle == best.hurdle && point.profit > best.profit)) best = point;
  }
  return best;
}

function OpexC116FormatSnapshotPoint(prefix, point, frontierN)
{
  local out = " " + prefix + "_n=" + frontierN;
  if (point == null) return out + " " + prefix + "_gap=-1";
  return out + " " + prefix + "_gap=" + point.gap
      + " " + prefix + "_mode=" + point.mode
      + " " + prefix + "_P=" + point.profit
      + " " + prefix + "_C=" + point.finance
      + " " + prefix + "_hurdle=" + point.hurdle
      + " " + prefix + "_roi=" + point.roi
      + " " + prefix + "_dist=" + point.distance;
}

function OpexC116BestUnlockedAirProject(deltaCapital)
{
  local snapshot = C116_AIR_PROJECT_SNAPSHOT;
  if (snapshot == null || !("unlockable" in snapshot) || deltaCapital <= 0) return null;
  local unlocked = null;
  foreach (point in snapshot.unlockable) {
    if (point.gap > deltaCapital) continue;
    if (unlocked == null || point.hurdle > unlocked.hurdle
        || (point.hurdle == unlocked.hurdle && point.profit > unlocked.profit)) unlocked = point;
  }
  return unlocked;
}

function OpexC116FormatProjectSnapshot(deltaCapital)
{
  local snapshot = C116_AIR_PROJECT_SNAPSHOT;
  if (snapshot == null) return " c116p_age=-1 c116p_budget=0 c116p_top_mode=none c116p_n=0 c116u_n=0 c116u_gap=-1 c116g_n=0 c116g_gap=-1";
  local age = AIDate.GetCurrentDate() - snapshot.date;
  local out = " c116p_age=" + age + " c116p_budget=" + snapshot.budget
      + " c116p_top_mode=" + snapshot.topMode + " c116p_n=" + snapshot.air.len();
  if (("top" in snapshot) && snapshot.top != null) {
    out += " c116t_mode=" + snapshot.top.mode
        + " c116t_P=" + snapshot.top.profit
        + " c116t_C=" + snapshot.top.finance
        + " c116t_hurdle=" + snapshot.top.hurdle
        + " c116t_score=" + snapshot.top.score;
  } else {
    out += " c116t_mode=none c116t_P=0 c116t_C=0 c116t_hurdle=0 c116t_score=0";
  }
  for (local i = 0; i < snapshot.air.len() && i < 3; i++) {
    local p = snapshot.air[i];
    local prefix = "c116p" + (i + 1);
    out += " " + prefix + "_rank=" + p.rank
        + " " + prefix + "_P=" + p.profit
        + " " + prefix + "_C=" + p.finance
        + " " + prefix + "_score=" + p.score
        + " " + prefix + "_roi=" + p.roi
        + " " + prefix + "_dist=" + p.distance;
  }
  local airN = ("unlockable" in snapshot) ? snapshot.unlockable.len() : 0;
  local airPoint = ("unlockable" in snapshot) ? OpexC116SnapshotBest(snapshot.unlockable, deltaCapital) : null;
  out += OpexC116FormatSnapshotPoint("c116u", airPoint, airN);
  local globalN = ("unlockableAny" in snapshot) ? snapshot.unlockableAny.len() : 0;
  local globalPoint = ("unlockableAny" in snapshot) ? OpexC116SnapshotBest(snapshot.unlockableAny, deltaCapital) : null;
  out += OpexC116FormatSnapshotPoint("c116g", globalPoint, globalN);
  return out;
}

function OpexC104ProbeAirEngineCompare(catalog, airport, distance, monthlyPax,
                                      infrastructureMaintenance, maxCapital,
                                      newAirportCount, opcodePadding)
{
  if (!C104_AIR_C100_COMPARE_PROBE || C104_AIR_C100_COMPARE_COUNT >= 600) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (!("__year" in C104_AIR_C100_COMPARE_SEEN) || C104_AIR_C100_COMPARE_SEEN["__year"] != year) {
    C104_AIR_C100_COMPARE_SEEN.rawset("__year", year);
    C104_AIR_C100_COMPARE_SEEN.rawset("__year_count", 0);
  }
  if (C104_AIR_C100_COMPARE_SEEN["__year_count"] >= 150) return;
  local key = airport.type + "|" + distance + "|" + monthlyPax + "|" + newAirportCount
      + "|" + maxCapital + "|" + opcodePadding;
  if (key in C104_AIR_C100_COMPARE_SEEN) return;
  C104_AIR_C100_COMPARE_SEEN.rawset(key, true);
  C104_AIR_C100_COMPARE_COUNT++;
  C104_AIR_C100_COMPARE_SEEN["__year_count"] = C104_AIR_C100_COMPARE_SEEN["__year_count"] + 1;

  local legacy = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 0);
  local replay = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1);
  local physical = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 2);
  local c69Physical = OpexC106PhysicalC69Choice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local marginal = OpexC106MarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local oneStep = OpexC107OneStepMarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local power7 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 7);
  local power8 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 8);
  local power9 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 9);
  local power10 = OpexC106PhysicalPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 10);
  local speed1 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1);
  local speed2 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 2);
  local speed3 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 3);
  local speed4 = OpexC108PhysicalSpeedPowerChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 4);
  local elastic25 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 250);
  local elastic50 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 500);
  local elastic75 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 750);
  local elastic100 = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1000);
  local c116 = OpexC116LegacyIncrementalCandidates(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, legacy);
  if (legacy == null || replay == null || physical == null || c69Physical == null || marginal == null
      || oneStep == null
      || power7 == null || power8 == null || power9 == null || power10 == null
      || speed1 == null || speed2 == null || speed3 == null || speed4 == null
      || elastic25 == null || elastic50 == null || elastic75 == null || elastic100 == null
      || c116 == null) return;
  local replayLegacy = OpexAirEconomics(catalog, airport, replay.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local replayPhysical = OpexAirEconomics(catalog, airport, replay.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, true, false);
  local physicalLegacy = OpexAirEconomics(catalog, airport, physical.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local physicalReplay = OpexAirEconomics(catalog, airport, physical.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, false, true);
  local marginalLegacy = OpexAirEconomics(catalog, airport, marginal.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  local arm = newAirportCount == 2 ? "newpair" : (newAirportCount == 1 ? "hubsite" : "hubhub");
  local kDec = C69_DECISION_BOTTLENECK ? OpexC69CachedKDec() : 0;
  local available = OpexAvailableCapital();
  local financeMargin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local legacyFinance = legacy.economics.capital + financeMargin;
  if (("immobilise" in legacy.economics) && legacy.economics.immobilise > 0) legacyFinance += legacy.economics.immobilise;
  local runnerFinance = c116.runner.economics.capital + financeMargin;
  if (("immobilise" in c116.runner.economics) && c116.runner.economics.immobilise > 0) runnerFinance += c116.runner.economics.immobilise;
  local selfGap = legacyFinance > available ? legacyFinance - available : 0;
  local selfUnlock = legacyFinance > available && runnerFinance <= available ? 1 : 0;
  AILog.Warning("C104_COMPARE year=" + year + " arm=" + arm + " airport=" + airport.type
      + " dist=" + distance + " pax=" + monthlyPax + " maxC=" + maxCapital + " kdec=" + kDec
      + " " + OpexC104FormatAirChoice("legacy", legacy)
      + " " + OpexC104FormatAirChoice("replay", replay)
      + " " + OpexC104FormatAirChoice("physical", physical)
      + " " + OpexC104FormatAirChoice("c69phys", c69Physical)
      + " " + OpexC104FormatAirChoice("marginal", marginal)
      + " " + OpexC104FormatAirChoice("onestep", oneStep)
      + " " + OpexC104FormatAirChoice("p7", power7)
      + " " + OpexC104FormatAirChoice("p8", power8)
      + " " + OpexC104FormatAirChoice("p9", power9)
      + " " + OpexC104FormatAirChoice("p10", power10)
      + " " + OpexC104FormatAirChoice("s1", speed1)
      + " " + OpexC104FormatAirChoice("s2", speed2)
      + " " + OpexC104FormatAirChoice("s3", speed3)
      + " " + OpexC104FormatAirChoice("s4", speed4)
      + " " + OpexC104FormatAirChoice("e25", elastic25)
      + " " + OpexC104FormatAirChoice("e50", elastic50)
      + " " + OpexC104FormatAirChoice("e75", elastic75)
      + " " + OpexC104FormatAirChoice("e100", elastic100)
      + " " + OpexC104FormatAirChoice("replay_legacy", { plane = replay.plane, economics = replayLegacy })
      + " " + OpexC104FormatAirChoice("replay_physical", { plane = replay.plane, economics = replayPhysical })
      + " " + OpexC104FormatAirChoice("physical_legacy", { plane = physical.plane, economics = physicalLegacy })
      + " " + OpexC104FormatAirChoice("physical_replay", { plane = physical.plane, economics = physicalReplay })
      + " " + OpexC104FormatAirChoice("marginal_legacy", { plane = marginal.plane, economics = marginalLegacy })
      + " " + OpexC104FormatAirChoice("c116_runner", c116.runner)
      + " " + OpexC104FormatAirChoice("c116_gate", c116.gate)
      + " " + OpexC104FormatAirChoice("c116_score", c116.score)
      + " " + OpexC104FormatAirChoice("c116_marg", c116.marginal)
      + " " + OpexC104FormatAirChoice("c116_opp", c116.opportunity)
      + " c116_dC=" + c116.deltaCapital + " c116_dP=" + c116.deltaProfit
      + " c116_lscore=" + c116.legacyScore + " c116_rscore=" + c116.runnerScore
      + " c116_mroi=" + c116.marginalRoi + " c116_opp_steps=" + c116.opportunitySteps
      + " c116_avail=" + available + " c116_legacy_fin=" + legacyFinance
      + " c116_runner_fin=" + runnerFinance + " c116_self_gap=" + selfGap
      + " c116_self_unlock=" + selfUnlock
      + OpexC116FormatProjectSnapshot(c116.deltaCapital));
}

/* C105 : cellule manquante du factoriel C100/C103.
 * Le timing global est C100.1 via C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS,
 * mais le moteur est classe avec le replay du premier C100. L'economie rendue
 * au portefeuille est ensuite recalculee en C100.1 pour CE moteur. */
function OpexC105ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local replay = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1);
  if (replay == null) return { plane = selectedPlane, economics = selectedEconomics };
  local physical = OpexAirEconomics(catalog, airport, replay.plane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, true, false);
  if (physical == null) return { plane = selectedPlane, economics = selectedEconomics };
  return { plane = replay.plane, economics = physical };
}

/* C109 actif : le timing/economie du portefeuille reste C100.1 et le moteur est
 * choisi uniquement par elasticite relative profit/vitesse, seuil e50 = 0.5. */
function OpexC109ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local choice = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 500);
  if (choice == null || !("plane" in choice) || !("economics" in choice) || choice.economics == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  return { plane = choice.plane, economics = choice.economics };
}

/* C112 : meme economie physique que C109, mais seuil d'elasticite e75. C104
 * montre que ce seuil est le plus proche du replay C100 en 1970 et sur newpair. */
function OpexC112ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local choice = OpexC109OneStepSpeedElasticityChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 750);
  if (choice == null || !("plane" in choice) || !("economics" in choice) || choice.economics == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  return { plane = choice.plane, economics = choice.economics };
}

/* C111 : cellule d'isolation manquante apres C103/C109.
 * - equipement : meme replay moteur que le premier C100 positif (C103), avec
 *   economie LEGACY du moteur effectivement achete ;
 * - decision : argmax C68 legacy conserve dans decisionEconomics.
 * Le portefeuille peut donc garder sa valeur de marche C68 tandis que la caisse
 * et le constructeur voient le vrai moteur choisi. */
function OpexC111ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local decision = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 0);
  if (decision == null || decision.plane == null || decision.economics == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  local equipment = OpexC103ChooseRoutePlane(catalog, airport, decision.plane, decision.economics,
      distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  if (equipment == null || equipment.plane == null || equipment.economics == null
      || equipment.economics.revenueAnnual <= 0 || equipment.economics.capital <= 0
      || (!C113_AIR_C100_FULL_DECISION_SHADOW && equipment.economics.profitAnnual <= 0)) {
    return { plane = decision.plane, economics = decision.economics,
        decisionEconomics = decision.economics };
  }
  return { plane = equipment.plane, economics = equipment.economics,
      decisionEconomics = decision.economics };
}

/* C108 : economie C100.1 partout + choix moteur marginal relatif en une seule
 * marche. Le chooser passif C107 evite la sur-descente recursive de C106. */
function OpexC108ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding)
{
  local choice = OpexC107OneStepMarginalPhysicalChoice(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1000);
  if (choice == null || !("plane" in choice) || !("economics" in choice) || choice.economics == null) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  return { plane = choice.plane, economics = choice.economics };
}

/* C116.3 passif : reproduit l'argmax C68 et conserve les evaluations pour
 * trouver le meilleur runner moins capitalistique sans second scan moteur. */
function OpexC116LegacyDecisionRunner(catalog, airport, distance, monthlyPax,
                                      infrastructureMaintenance, maxCapital,
                                      newAirportCount, opcodePadding, paymentDistance = 0)
{
  local items = [];
  local decision = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        0, false, false, false, false, paymentDistance);
    if (economics == null) continue;
    local item = { plane = plane, economics = economics };
    items.append(item);
    if (decision == null || economics.profitAnnual > decision.economics.profitAnnual
        || (economics.profitAnnual == decision.economics.profitAnnual
            && economics.roi > decision.economics.roi)) decision = item;
  }
  if (decision == null) return null;
  local runner = null;
  foreach (item in items) {
    if (item.economics.capital >= decision.economics.capital) continue;
    if (runner == null || item.economics.profitAnnual > runner.economics.profitAnnual
        || (item.economics.profitAnnual == runner.economics.profitAnnual
            && item.economics.roi > runner.economics.roi)) runner = item;
  }
  return { decision = decision, runner = runner, items = items };
}

function OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
                                 newAirportCount, opcodePadding,
                                 scan, chosen, kDec, replayUsed)
{
  if (!C116_AIR_PROJECT_PROBE || scan == null || scan.decision == null || chosen == null) return;
  if (C116_AIR_PROJECT_SNAPSHOT == null) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (C116_AIR_PROJECT_PROBE_YEAR != year) {
    C116_AIR_PROJECT_PROBE_YEAR = year;
    C116_AIR_PROJECT_PROBE_YEAR_COUNT = 0;
  }
  if (C116_AIR_PROJECT_PROBE_COUNT >= 600 || C116_AIR_PROJECT_PROBE_YEAR_COUNT >= 150) return;
  local key = year + "|" + airport.type + "|" + distance + "|" + monthlyPax + "|"
      + newAirportCount + "|" + maxCapital + "|" + opcodePadding;
  if (key in C116_AIR_PROJECT_PROBE_SEEN) return;
  C116_AIR_PROJECT_PROBE_SEEN.rawset(key, true);
  C116_AIR_PROJECT_PROBE_COUNT++;
  C116_AIR_PROJECT_PROBE_YEAR_COUNT++;

  local decision = scan.decision;
  local runner = scan.runner;
  local deltaCapital = 0;
  local deltaProfit = 0;
  local marginalRoi = 0.0;
  if (runner != null) {
    deltaCapital = decision.economics.capital - runner.economics.capital;
    deltaProfit = decision.economics.profitAnnual - runner.economics.profitAnnual;
    if (deltaCapital > 0) marginalRoi = (deltaProfit.tofloat() * 1000.0) / deltaCapital.tofloat();
  }
  local available = OpexAvailableCapital();
  local financeMargin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local legacyFinance = decision.economics.capital + financeMargin;
  if (("immobilise" in decision.economics) && decision.economics.immobilise > 0) legacyFinance += decision.economics.immobilise;
  local runnerFinance = runner != null ? runner.economics.capital + financeMargin : legacyFinance;
  if (runner != null && ("immobilise" in runner.economics) && runner.economics.immobilise > 0) runnerFinance += runner.economics.immobilise;
  local selfGap = legacyFinance > available ? legacyFinance - available : 0;
  local selfUnlock = runner != null && legacyFinance > available && runnerFinance <= available ? 1 : 0;
  local arm = newAirportCount == 2 ? "newpair" : (newAirportCount == 1 ? "hubsite" : "hubhub");
  local runnerText = runner != null ? OpexC104FormatAirChoice("runner", runner) : "runner_id=-1";
  AILog.Warning("C116_PROJECT year=" + year + " arm=" + arm + " airport=" + airport.type
      + " dist=" + distance + " pax=" + monthlyPax + " maxC=" + maxCapital
      + " kdec=" + kDec + " avail=" + available + " replay_used=" + replayUsed
      + " " + OpexC104FormatAirChoice("legacy", decision)
      + " " + OpexC104FormatAirChoice("c115", chosen)
      + " " + runnerText
      + " dC=" + deltaCapital + " dP=" + deltaProfit + " mroi=" + marginalRoi
      + " legacy_fin=" + legacyFinance + " runner_fin=" + runnerFinance
      + " self_gap=" + selfGap + " self_unlock=" + selfUnlock
      + OpexC116FormatProjectSnapshot(deltaCapital));
}

/* C115 : conserver le couplage choix moteur + economie de route qui porte le
 * signal C114, mais seulement lorsque le capital est encore le goulot de la
 * decision. K_dec = flux * temps entre constructions : si K_dec >= C68.capital,
 * economiser davantage de capital n'augmente plus le debit d'investissement et
 * on garde donc le profit absolu C68. Sinon on utilise le replay exact du premier
 * C100, sans constante de richesse ni seuil temporel. */
function OpexC115ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
                                  distance, monthlyPax, infrastructureMaintenance,
                                  maxCapital, newAirportCount, opcodePadding, paymentDistance = 0)
{
  /* selectedEconomics est seulement l'economie de l'appareil d'entree de
   * OpexAirChooseRoutePlaneFull. Recalculer explicitement l'argmax C68 avant de
   * tester le goulot, sinon K_dec serait compare au mauvais capital. */
  local scan = (C116_AIR_PROJECT_PROBE || C118_AIR_TERRITORIAL_EXPANSION)
      ? OpexC116LegacyDecisionRunner(catalog, airport, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, paymentDistance)
      : null;
  local decision = scan != null ? scan.decision
      : OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 0, paymentDistance);
  if (decision == null || decision.plane == null || decision.economics == null
      || decision.economics.capital <= 0) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  local kDec = OpexC69CachedKDec();
  if (kDec >= decision.economics.capital) {
    if (C116_AIR_PROJECT_PROBE) OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
        newAirportCount, opcodePadding, scan, decision, kDec, 0);
    local result = { plane = decision.plane, economics = decision.economics,
        c118C68Plane = decision.plane, c118C68Economics = decision.economics };
    if (C118_AIR_TERRITORIAL_EXPANSION && scan != null && ("items" in scan)) result.c118EngineChoices <- scan.items;
    return result;
  }
  local replay = OpexC104BestAirEngine(catalog, airport, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1, paymentDistance);
  if (replay == null || replay.plane == null || replay.economics == null) {
    if (C116_AIR_PROJECT_PROBE) OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
        newAirportCount, opcodePadding, scan, decision, kDec, 0);
    local result = { plane = decision.plane, economics = decision.economics,
        c118C68Plane = decision.plane, c118C68Economics = decision.economics };
    if (C118_AIR_TERRITORIAL_EXPANSION && scan != null && ("items" in scan)) result.c118EngineChoices <- scan.items;
    return result;
  }
  if (C116_AIR_PROJECT_PROBE) OpexC116LogProjectProbe(airport, distance, monthlyPax, maxCapital,
      newAirportCount, opcodePadding, scan, replay, kDec, 1);
  local result = { plane = replay.plane, economics = replay.economics,
      c118C68Plane = decision.plane, c118C68Economics = decision.economics };
  if (C118_AIR_TERRITORIAL_EXPANSION && scan != null && ("items" in scan)) result.c118EngineChoices <- scan.items;
  return result;
}

function OpexC116RouteFinanceCapital(economics, newAirportCount)
{
  if (economics == null || economics.capital <= 0) return 0;
  local margin = newAirportCount == 2 ? 30000 : (newAirportCount == 1 ? 12000 : 2000);
  local finance = economics.capital + margin;
  if (("immobilise" in economics) && economics.immobilise > 0) finance += economics.immobilise;
  return finance;
}

function OpexC118NextTerritorialPoint(project)
{
  if (!C118_AIR_TERRITORIAL_EXPANSION || project == null
      || C118_AIR_PROJECT_SNAPSHOT == null
      || !("active" in C118_AIR_PROJECT_SNAPSHOT) || !C118_AIR_PROJECT_SNAPSHOT.active
      || !("townMin" in C118_AIR_PROJECT_SNAPSHOT)
      || !("coveredTowns" in C118_AIR_PROJECT_SNAPSHOT)) return null;
  local ids = ("c118TownIds" in project) ? project.c118TownIds : [];
  local best = null;
  foreach (townId, point in C118_AIR_PROJECT_SNAPSHOT.townMin) {
    if (townId in C118_AIR_PROJECT_SNAPSHOT.coveredTowns) continue;
    local currentCovers = false;
    foreach (id in ids) {
      if (id == townId) { currentCovers = true; break; }
    }
    if (currentCovers) continue;
    if (best == null || point.capital < best.capital) best = point;
  }
  return best;
}

function OpexC118TownCoverageCount(cargo)
{
  local set = OpexC118OwnCoveredTownSet(cargo);
  return set.len();
}

/* C116.2 : rendement du meilleur projet AIR actuellement non finançable que
 * `deltaCapital` rendrait finançable. La frontière a été construite pendant la
 * sélection portefeuille précédente ; aucune nouvelle recherche n'est faite ici. */
function OpexC116UnlockedProjectOpportunity(deltaCapital)
{
  if (deltaCapital <= 0 || C116_AIR_PROJECT_SNAPSHOT == null
      || !("unlockable" in C116_AIR_PROJECT_SNAPSHOT)) return null;
  local best = null;
  foreach (point in C116_AIR_PROJECT_SNAPSHOT.unlockable) {
    if (point.gap > deltaCapital) continue;
    if (best == null || point.hurdle > best.hurdle
        || (point.hurdle == best.hurdle && point.profit > best.profit)) best = point;
  }
  return best;
}

/* C116.4 : le projet portefeuille reste strictement C68. Le snapshot courant
 * ne sert qu'apres selection du projet, au moment d'acheter l'equipement. */
function OpexC116BestPendingAirProject()
{
  if (C116_AIR_PROJECT_SNAPSHOT == null
      || !("unlockable" in C116_AIR_PROJECT_SNAPSHOT)
      || C116_AIR_PROJECT_SNAPSHOT.unlockable.len() == 0) return null;
  local best = null;
  foreach (point in C116_AIR_PROJECT_SNAPSHOT.unlockable) {
    if (point.gap <= 0) continue;
    if (best == null || point.hurdle > best.hurdle
        || (point.hurdle == best.hurdle && point.profit > best.profit)) best = point;
  }
  return best;
}

/* C116.4 : le portefeuille doit voir strictement le plan C68. Cette fonction
 * n'est donc appelee qu'apres selection/revalidation du projet, juste avant le
 * test de tresorerie et le chantier. Elle ne recherche ni route ni site : elle
 * relit seulement le snapshot portefeuille et scanne une fois les moteurs du
 * type d'aeroport deja choisi.
 *
 * Le plan original reste immuable. En cas de bascule, un clone porte le moteur
 * et l'economie effectivement achetes ; le projet classe garde ainsi son
 * profit/capital/ROI/fundScore C68 meme si l'equipement final est moins cher. */
function OpexC116ChooseBuildPlan(catalog, plan)
{
  local unchanged = { plan = plan, changed = false, target = null,
      deltaCapital = 0, deltaProfit = 0 };
  /* C121 porte deja un contrat moteur/flotte/economie complet jusqu'au
   * portefeuille. C121 ne doit pas substituer un moteur legacy apres classement. */
  if (C121_AIR_ECONOMICS) return unchanged;
  if (!C116_AIR_MARGINAL_CAPITAL || catalog == null || plan == null
      || !("airport" in plan) || plan.airport == null
      || !("plane" in plan) || plan.plane == null
      || !("economics" in plan) || plan.economics == null
      || !("distance" in plan) || !("monthlyPax" in plan)
      || catalog.airPlaneChoicesByAirport == null
      || !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return unchanged;

  /* C116 qualifie uniquement le C68 normal. Ne pas superposer une seconde
   * politique d'equipement a C85/V92/C82/etc. C115 est l'exception volontaire :
   * quand C116=1, son replay est deja neutralise dans le chooser de generation. */
  if (V92_AIR_SERVICE_CHOICE || C72_PLANE_CHOICE != 0
      || C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY
      || C85_AIR_EQUIPMENT_FRONTIER || C99_AIR_SPEED_API_FIX || C100_AIR_TRIP_PHYSICAL
      || C101_AIR_PHYSICAL_ENGINE_CHOICE || C103_AIR_C100_RANK_REPLAY
      || C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      || C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE || C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      || C109_AIR_SPEED_ELASTICITY_PHYSICAL || C111_AIR_C100_DECISION_SHADOW
      || C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL || C114_AIR_C100_FULL_REPLAY) return unchanged;

  /* Le modele hub-hub marginal retranche une cannibalisation apres le chooser
   * et ne conserve pas ses composantes dans le plan. Ne pas comparer un C68
   * penalise a un runner brut si cette option experimentale est active. */
  if (AIR_HUBHUB_MARGINAL && ("arm" in plan) && plan.arm == "hubhub") return unchanged;

  local target = OpexC116BestPendingAirProject();
  if (target == null || target.gap <= 0) return unchanged;
  unchanged.target = target;

  local baselinePlane = ("c118C68Plane" in plan) ? plan.c118C68Plane : plan.plane;
  local baselineEconomics = ("c118C68Economics" in plan) ? plan.c118C68Economics : plan.economics;
  if (baselineEconomics.capital <= 0 || baselineEconomics.profitAnnual <= 0) return unchanged;
  local newAirportCount = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local runner = null;

  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (plane.id == baselinePlane.id || plane.price >= baselinePlane.price) continue;
    if (plane.maxOrderDistance > 0 && plan.distance > plane.maxOrderDistance) continue;
    if (("reuseA" in plan) && plan.reuseA && AIAirport.IsAirportTile(plan.siteA.anchor)
        && !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteA.anchor), plane.planeType)) continue;
    if (("reuseB" in plan) && plan.reuseB && AIAirport.IsAirportTile(plan.siteB.anchor)
        && !OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteB.anchor), plane.planeType)) continue;

    local economics = OpexAirEconomics(catalog, plan.airport, plane, plan.distance, plan.monthlyPax,
        infrastructureMaintenance, 0, newAirportCount, 0);
    if (economics == null || economics.profitAnnual <= 0
        || economics.capital >= baselineEconomics.capital) continue;
    local deltaCapital = baselineEconomics.capital - economics.capital;
    if (deltaCapital < target.gap) continue;
    if (runner == null || economics.profitAnnual > runner.economics.profitAnnual
        || (economics.profitAnnual == runner.economics.profitAnnual
            && economics.roi > runner.economics.roi)) runner = { plane = plane, economics = economics };
  }
  if (runner == null) return unchanged;

  local buildPlan = {};
  foreach (k, v in plan) buildPlan[k] <- v;
  buildPlan.plane = runner.plane;
  buildPlan.economics = runner.economics;
  buildPlan.planes = runner.economics.planes;
  buildPlan.capital = runner.economics.capital;
  if (C84_AIR_TARGET_FLEET) {
    local targetEconomics = OpexAirTargetEconomics(catalog, buildPlan.airport, buildPlan.plane,
        buildPlan.distance, buildPlan.monthlyPax, infrastructureMaintenance, newAirportCount, 0);
    local targetPlanes = targetEconomics != null ? targetEconomics.planes : runner.economics.planes;
    if ("targetPlanes" in buildPlan) buildPlan.targetPlanes = targetPlanes;
    else buildPlan.targetPlanes <- targetPlanes;
  }
  buildPlan.c116BaselineEngine <- baselinePlane.id;
  buildPlan.c116BaselineCapital <- baselineEconomics.capital;
  buildPlan.c116BaselineProfit <- baselineEconomics.profitAnnual;
  buildPlan.c116TargetGap <- target.gap;
  return { plan = buildPlan, changed = true, target = target,
      deltaCapital = baselineEconomics.capital - runner.economics.capital,
      deltaProfit = baselineEconomics.profitAnnual - runner.economics.profitAnnual };
}

/* C118 : apres que le portefeuille a choisi une route territoriale, comparer
 * l'equipement sur la meme grandeur que le classement : nombre de jours avant
 * que le prochain projet couvrant encore une ville devienne finançable.
 *
 * Aucune route/site n'est regenere. K_next vient du snapshot construit pendant
 * OpexProjectSelectAffordable et les economies moteur sont celles deja evaluees
 * par le scan C115/C68 de generation : aucun second scan moteur n'est necessaire.
 * Contrairement a C116.4, un moteur plus cher peut gagner s'il ajoute assez de
 * profit annuel pour financer le chantier suivant plus vite. */
function OpexC118ChooseBuildPlan(catalog, plan, project)
{
  local unchanged = {
    plan = plan, changed = false, active = false,
    newTowns = (project != null && ("c118NewTowns" in project)) ? project.c118NewTowns : 0,
    nextCapital = (project != null && ("c118NextCapital" in project)) ? project.c118NextCapital : 0,
    nextTown = (project != null && ("c118NextTown" in project)) ? project.c118NextTown : -1,
    available = 0, flowDaily = 0.0,
    baselineFinance = 0, chosenFinance = 0,
    baselineProfit = 0, chosenProfit = 0,
    baselineCashAfter = 0, chosenCashAfter = 0,
    baselineFlowAfter = 0.0, chosenFlowAfter = 0.0,
    baselineDays = 0.0, chosenDays = 0.0, baselineEngine = -1,
  };
  /* Conserver C118 comme signal territorial/portfolio, mais pas comme second
   * chooser d'equipement : sous C121 le plan classe doit etre le plan construit. */
  if (C121_AIR_ECONOMICS) return unchanged;
  if (!C118_AIR_TERRITORIAL_EXPANSION || project == null
      || !("c118NewTowns" in project) || project.c118NewTowns <= 0
      || C118_AIR_PROJECT_SNAPSHOT == null || !("active" in C118_AIR_PROJECT_SNAPSHOT)
      || !C118_AIR_PROJECT_SNAPSHOT.active || catalog == null || plan == null
      || !("airport" in plan) || plan.airport == null
      || !("plane" in plan) || plan.plane == null
      || !("economics" in plan) || plan.economics == null
      || !("distance" in plan) || !("monthlyPax" in plan)
      || catalog.airPlaneChoicesByAirport == null
      || !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return unchanged;

  /* Ne pas superposer C118 aux anciennes experiences de moteur. C115 reste le
   * temoin normal du portefeuille ; son chooser expose son argmax C68 en shadow
   * sans scan supplementaire, et C118 utilise ce shadow comme baseline. */
  if (V92_AIR_SERVICE_CHOICE || C72_PLANE_CHOICE != 0
      || C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY
      || C85_AIR_EQUIPMENT_FRONTIER || C99_AIR_SPEED_API_FIX || C100_AIR_TRIP_PHYSICAL
      || C101_AIR_PHYSICAL_ENGINE_CHOICE || C103_AIR_C100_RANK_REPLAY
      || C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      || C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE || C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      || C109_AIR_SPEED_ELASTICITY_PHYSICAL || C111_AIR_C100_DECISION_SHADOW
      || C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL || C114_AIR_C100_FULL_REPLAY) return unchanged;
  if (AIR_HUBHUB_MARGINAL && ("arm" in plan) && plan.arm == "hubhub") return unchanged;

  local baselinePlane = (("c118C68Plane" in plan) && plan.c118C68Plane != null)
      ? plan.c118C68Plane : plan.plane;
  local baselineEconomics = (("c118C68Economics" in plan) && plan.c118C68Economics != null)
      ? plan.c118C68Economics : plan.economics;
  if (baselineEconomics.capital <= 0 || baselineEconomics.profitAnnual <= 0) return unchanged;
  local newAirportCount = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local available = OpexAvailableCapital();
  local flow = OpexComputeOperatingCashFlow();
  local flowDaily = flow.F;
  local nextCapital = unchanged.nextCapital;
  local baselineFinance = OpexC116RouteFinanceCapital(baselineEconomics, newAirportCount);
  local baselineAffordable = baselineFinance > 0 && baselineFinance <= available;
  local baselineSpend = baselineEconomics.capital
      + ((("immobilise" in baselineEconomics) && baselineEconomics.immobilise > 0)
          ? baselineEconomics.immobilise : 0);
  local baselineCashAfter = available - baselineSpend;
  if (baselineCashAfter < 0) baselineCashAfter = 0;
  local baselineFlowAfter = flowDaily + baselineEconomics.profitAnnual.tofloat() / 365.0;
  local baselineDays = OpexC118TimeToNextDays(available, baselineSpend, flowDaily,
      baselineEconomics.profitAnnual, nextCapital);

  unchanged.active = true;
  unchanged.baselineEngine = baselinePlane.id;
  unchanged.available = available;
  unchanged.flowDaily = flowDaily;
  unchanged.baselineFinance = baselineFinance;
  unchanged.chosenFinance = baselineFinance;
  unchanged.baselineProfit = baselineEconomics.profitAnnual;
  unchanged.chosenProfit = baselineEconomics.profitAnnual;
  unchanged.baselineCashAfter = baselineCashAfter;
  unchanged.chosenCashAfter = baselineCashAfter;
  unchanged.baselineFlowAfter = baselineFlowAfter;
  unchanged.chosenFlowAfter = baselineFlowAfter;
  unchanged.baselineDays = baselineDays;
  unchanged.chosenDays = baselineDays;

  /* Si ce projet est le dernier territorial connu, tous les moteurs ont
   * timeToNext=0 : le departage profit/ROI ci-dessous retrouve naturellement C68. */
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local bestPlane = baselineAffordable ? baselinePlane : null;
  local bestEconomics = baselineAffordable ? baselineEconomics : null;
  local bestFinance = baselineAffordable ? baselineFinance : 0;
  local bestDays = baselineAffordable ? baselineDays : -1.0;

  local choices = (("c118EngineChoices" in plan) && plan.c118EngineChoices != null)
      ? plan.c118EngineChoices : [];
  if (choices.len() == 0) choices.append({ plane = baselinePlane, economics = baselineEconomics });
  foreach (item in choices) {
    if (item == null || !("plane" in item) || item.plane == null
        || !("economics" in item) || item.economics == null) continue;
    local plane = item.plane;
    local economics = item.economics;
    if (!OpexC118EngineFitsPlan(plan, plane)) continue;
    if (economics == null || economics.capital <= 0 || economics.profitAnnual <= 0) continue;
    local finance = OpexC116RouteFinanceCapital(economics, newAirportCount);
    if (finance <= 0 || finance > available) continue;
    local spend = OpexC118EconomicsSpendCapital(economics);
    local days = OpexC118TimeToNextDays(available, spend, flowDaily,
        economics.profitAnnual, nextCapital);
    if (days < 0) continue;

    local better = bestPlane == null || bestDays < 0 || days < bestDays;
    if (!better && days == bestDays) {
      better = economics.profitAnnual > bestEconomics.profitAnnual
          || (economics.profitAnnual == bestEconomics.profitAnnual
              && economics.roi > bestEconomics.roi);
    }
    if (better) {
      bestPlane = plane;
      bestEconomics = economics;
      bestFinance = finance;
      bestDays = days;
    }
  }
  if (bestPlane == null || bestEconomics == null) return unchanged;

  local bestSpend = OpexC118EconomicsSpendCapital(bestEconomics);
  local bestCashAfter = available - bestSpend;
  if (bestCashAfter < 0) bestCashAfter = 0;
  local bestFlowAfter = flowDaily + bestEconomics.profitAnnual.tofloat() / 365.0;
  unchanged.chosenFinance = bestFinance;
  unchanged.chosenProfit = bestEconomics.profitAnnual;
  unchanged.chosenCashAfter = bestCashAfter;
  unchanged.chosenFlowAfter = bestFlowAfter;
  unchanged.chosenDays = bestDays;
  local sameAsPlan = bestPlane.id == plan.plane.id
      && bestEconomics.capital == plan.economics.capital
      && bestEconomics.profitAnnual == plan.economics.profitAnnual
      && bestEconomics.planes == plan.economics.planes;
  if (sameAsPlan) return unchanged;

  local buildPlan = {};
  foreach (k, v in plan) buildPlan[k] <- v;
  buildPlan.plane = bestPlane;
  buildPlan.economics = bestEconomics;
  buildPlan.planes = bestEconomics.planes;
  buildPlan.capital = bestEconomics.capital;
  if (C84_AIR_TARGET_FLEET) {
    local targetEconomics = OpexAirTargetEconomics(catalog, buildPlan.airport, buildPlan.plane,
        buildPlan.distance, buildPlan.monthlyPax, infrastructureMaintenance, newAirportCount, 0);
    local targetPlanes = targetEconomics != null ? targetEconomics.planes : bestEconomics.planes;
    if ("targetPlanes" in buildPlan) buildPlan.targetPlanes = targetPlanes;
    else buildPlan.targetPlanes <- targetPlanes;
  }
  unchanged.plan = buildPlan;
  unchanged.changed = true;
  return unchanged;
}

function OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
                                     infrastructureMaintenance, maxCapital, newAirportCount,
                                     opcodePadding, paymentDistance = 0)
{
  local selectedEconomics = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
      0, false, false, false, false, paymentDistance);
  if (!AIR_ROUTE_PLANE_SELECTION || !(airport.type in catalog.airPlaneChoicesByAirport)) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  if (C104_AIR_C100_COMPARE_PROBE && !C115_AIR_C100_CAPITAL_REPLAY
      && C72_PLANE_CHOICE == 0 && !C82_ENGINE_CALIBRATION
      && !C85_AIR_EQUIPMENT_FRONTIER && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE
      && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    OpexC104ProbeAirEngineCompare(catalog, airport, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C85_AIR_EQUIPMENT_FRONTIER
      && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE
      && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    return OpexC105ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C85_AIR_EQUIPMENT_FRONTIER
      && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    return OpexC106ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C108_AIR_ONESTEP_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C85_AIR_EQUIPMENT_FRONTIER
      && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    return OpexC108ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C109_AIR_SPEED_ELASTICITY_PHYSICAL && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C85_AIR_EQUIPMENT_FRONTIER
      && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C104_AIR_C100_COMPARE_PROBE && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE
      && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    return OpexC109ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C111_AIR_C100_DECISION_SHADOW && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION
      && !C85_AIR_EQUIPMENT_FRONTIER && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C104_AIR_C100_COMPARE_PROBE && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    return OpexC111ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY
      && !C85_AIR_EQUIPMENT_FRONTIER && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C104_AIR_C100_COMPARE_PROBE && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW) {
    return OpexC112ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C115_AIR_C100_CAPITAL_REPLAY && C72_PLANE_CHOICE == 0
      && !C82_ENGINE_CALIBRATION && !C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY
      && !C85_AIR_EQUIPMENT_FRONTIER && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C101_AIR_PHYSICAL_ENGINE_CHOICE && !C103_AIR_C100_RANK_REPLAY
      && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL && !C114_AIR_C100_FULL_REPLAY
      && !C116_AIR_MARGINAL_CAPITAL) {
    return OpexC115ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding,
        paymentDistance);
  }
  if (C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY) {
    return OpexC82ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics, distance,
        monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C103_AIR_C100_RANK_REPLAY && C72_PLANE_CHOICE == 0
      && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C85_AIR_EQUIPMENT_FRONTIER && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE
      && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    return OpexC103ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (C101_AIR_PHYSICAL_ENGINE_CHOICE && C72_PLANE_CHOICE == 0
      && !C99_AIR_SPEED_API_FIX && !C100_AIR_TRIP_PHYSICAL
      && !C85_AIR_EQUIPMENT_FRONTIER && !C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS
      && !C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE
      && !C108_AIR_ONESTEP_PHYSICAL_ECONOMICS
      && !C109_AIR_SPEED_ELASTICITY_PHYSICAL && !C111_AIR_C100_DECISION_SHADOW
      && !C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL) {
    return OpexC101ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics,
        distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }

  local bestPlane = selectedPlane;
  local bestEconomics = selectedEconomics;
  local bestScore = 0.0;

  local kDec = 0;
  if (C69_BOTTLENECK_PROBE || C72_PLANE_CHOICE == 2) {
    kDec = OpexC69CachedKDec();
  }

  if (C72_PLANE_CHOICE == 2 && selectedEconomics != null) {
    local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
    bestScore = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
  }

  local r_plane = null;
  local r_econ = null;
  local c_plane = null;
  local c_econ = null;
  local c_score = 0.0;
  local evalCount = 0;

  if (C69_BOTTLENECK_PROBE) {
    if (selectedEconomics != null) {
      evalCount = 1;
      r_plane = selectedPlane;
      r_econ = selectedEconomics;
      c_plane = selectedPlane;
      c_econ = selectedEconomics;
      local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
      c_score = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
    }
  }

  local routePlaneChoices = catalog.airPlaneChoicesByAirport[airport.type];
  /* C85 ne change que l'objectif C68 historique (profit max). Les modes C72/C82 ont des
   * objectifs differents ; ils conservent volontairement la liste complete. Le selectedPlane
   * reste evalue separement ci-dessus, meme s'il est domine et absent de la frontier. */
  if (C85_AIR_EQUIPMENT_FRONTIER && C72_PLANE_CHOICE == 0 && !C82_ENGINE_CALIBRATION
      && ("airPlaneFrontierByAirport" in catalog)
      && airport.type in catalog.airPlaneFrontierByAirport
      && catalog.airPlaneFrontierByAirport[airport.type].len() > 0) {
    routePlaneChoices = catalog.airPlaneFrontierByAirport[airport.type];
  }

  foreach (plane in routePlaneChoices) {
    if (plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null) continue;
    if (C72_PLANE_CHOICE == 1) {
      if (bestEconomics == null || economics.roi > bestEconomics.roi ||
          (economics.roi == bestEconomics.roi && economics.profitAnnual > bestEconomics.profitAnnual)) {
        bestPlane = plane;
        bestEconomics = economics;
      }
    } else if (C72_PLANE_CHOICE == 2) {
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
      if (bestEconomics == null || curScore > bestScore ||
          (curScore == bestScore && economics.profitAnnual > bestEconomics.profitAnnual)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestScore = curScore;
      }
    } else {
      if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
          (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
        bestPlane = plane;
        bestEconomics = economics;
      }
    }
    if (C69_BOTTLENECK_PROBE) {
      evalCount++;
      if (r_econ == null || economics.roi > r_econ.roi ||
          (economics.roi == r_econ.roi && economics.profitAnnual > r_econ.profitAnnual)) {
        r_plane = plane;
        r_econ = economics;
      }
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
      if (c_econ == null || curScore > c_score ||
          (curScore == c_score && economics.profitAnnual > c_econ.profitAnnual)) {
        c_plane = plane;
        c_econ = economics;
        c_score = curScore;
      }
    }
  }

  if (C69_BOTTLENECK_PROBE && evalCount >= 2) {
    C69_PLANE_CHOICE_CALLS++;
    if (r_plane.id != bestPlane.id) C69_PLANE_CHOICE_DIFFER_ROI++;
    if (c_plane.id != bestPlane.id) C69_PLANE_CHOICE_DIFFER_C69++;

    if (r_plane.id != bestPlane.id || c_plane.id != bestPlane.id) {
      local avail = OpexAvailableCapital();
      local p_name = OpexPlaneName(bestPlane.id);
      local r_name = OpexPlaneName(r_plane.id);
      local c_name = OpexPlaneName(c_plane.id);
      OpexC69Log("phase=plane_choice dist=" + distance + " kdec=" + kDec + " avail=" + avail
          + " nplanes=" + evalCount
          + " p_id=" + bestPlane.id + " p_name=" + p_name + " p_P=" + bestEconomics.profitAnnual
          + " p_C=" + bestEconomics.capital + " p_roi=" + bestEconomics.roi
          + " r_id=" + r_plane.id + " r_name=" + r_name + " r_P=" + r_econ.profitAnnual
          + " r_C=" + r_econ.capital + " r_roi=" + r_econ.roi
          + " c_id=" + c_plane.id + " c_name=" + c_name + " c_P=" + c_econ.profitAnnual
          + " c_C=" + c_econ.capital + " c_roi=" + c_econ.roi);
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
        infrastructureMaintenance, 0, newAirports, 0, fixedPlanes);
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
                                    opcodePadding, selectedEconomics, phase)
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
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
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
function OpexAirSitePaddingKey(site, airportType)
{
  return "air_site|" + airportType + "|" + site.anchor;
}

function OpexAirTownPaddingKey(site)
{
  return "air_town_limit|" + site.town.tile;
}

/* C78.2 : une paire AIR est non orientee. Generation et chantier ecrivent
 * exactement la meme cle, meme si un hub inverse l'ordre des extremites. */
function OpexAirPairKey(siteA, siteB)
{
  local a = siteA.town.tile;
  local b = siteB.town.tile;
  if (a > b) {
    local swap = a;
    a = b;
    b = swap;
  }
  return "air|" + a + "|" + b;
}

/* Compatibilite des sauvegardes anterieures a C78.2 : les anciennes cles
 * pouvaient avoir ete ecrites dans l'autre sens. */
function OpexAirPairIsAbandoned(abandoned, siteA, siteB)
{
  if (abandoned == null || siteA == null || siteB == null) return false;
  local canonical = OpexAirPairKey(siteA, siteB);
  if (canonical in abandoned) return true;
  local legacyForward = "air|" + siteA.town.tile + "|" + siteB.town.tile;
  if (legacyForward != canonical && (legacyForward in abandoned)) return true;
  local legacyReverse = "air|" + siteB.town.tile + "|" + siteA.town.tile;
  return legacyReverse != canonical && (legacyReverse in abandoned);
}

/* C78 etape 2 : identification de la ville d'un hub aerien. */
function OpexC78HubTownId(h)
{
  if (h != null) {
    if (("town" in h) && h.town != null && ("id" in h.town)) return h.town.id;
    if (("anchor" in h) && AIMap.IsValidTile(h.anchor)) return AITile.GetClosestTown(h.anchor);
  }
  return -1;
}

/* Calcul du delta d'opcodes consommes depuis (t0, l0). */
function OpexAirCalcDeltaOps(t0, l0)
{
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - t0;
  return elapsed <= 0
    ? l0 - left
    : l0 + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
}

/* 1. Preparation : combos, villes, OpexAirTownPoolLimit, indices et reprise. */
function OpexAirPlansPrepare(ctx)
{
  local catalog = ctx.catalog;
  local lines = ctx.lines;
  local targetTownId = ctx.targetTownId;
  if (V93_AIR_DEMAND_PRODUCTION) AIR_DEMAND_PAX_CARGO = catalog.paxCargo;
  local resumeState = ctx.resumeState;
  local t0_all = ctx.t0_all;
  local sliced = ctx.sliced;

  if (!sliced) {
    OpexAirResetStationCoverageTownCache();
  } else if (!("stationCoverageTownCacheInit" in resumeState)) {
    OpexAirResetStationCoverageTownCache();
    resumeState.stationCoverageTownCacheInit <- true;
  }

  if (C80_AIR_EVAL_FAST) {
    /* Les prix changent au debut de chaque mois (inflation) : une planification decoupee qui
     * enjambe un changement de mois repart avec des memos vides pour rester exacte. */
    local memoDate = AIDate.GetCurrentDate();
    local memoMonth = AIDate.GetYear(memoDate) * 12 + AIDate.GetMonth(memoDate);
    if (!sliced || !("airFastInit" in resumeState) || AIR_MEMO_MONTH != memoMonth) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
      if (sliced) resumeState.airFastInit <- true;
    }
    AIR_MEMO_MONTH = memoMonth;
  }
  if (sliced) {
    if (!("done" in resumeState)) resumeState.done <- false;
    if (resumeState.done) {
      ctx.bestPlan = ("bestPlan" in resumeState) ? resumeState.bestPlan : null;
      return false;
    }
    if (!("combo" in resumeState)) resumeState.combo <- 0;
    if (!("a" in resumeState)) resumeState.a <- 0;
    if (!("b" in resumeState)) resumeState.b <- 1;
    if (!("sites" in resumeState)) resumeState.sites <- null;
    if (!("bestPlan" in resumeState)) resumeState.bestPlan <- null;
    if (!("stationLimitedTowns" in resumeState)) resumeState.stationLimitedTowns <- {};
    if (!("perfOpsSites" in resumeState)) resumeState.perfOpsSites <- 0;
    if (!("perfOpsEval" in resumeState)) resumeState.perfOpsEval <- 0;
    if (!("perfProbesCount" in resumeState)) resumeState.perfProbesCount <- 0;
    if (!("perfCheapSkip" in resumeState)) resumeState.perfCheapSkip <- 0;
    if (!("perfSitesFound" in resumeState)) resumeState.perfSitesFound <- 0;
    if (!("totalOps" in resumeState)) resumeState.totalOps <- 0;
    if (!("startTick" in resumeState)) resumeState.startTick <- t0_all;
    if (!("towns" in resumeState)) resumeState.towns <- null;
    if (!("combos" in resumeState)) resumeState.combos <- null;
    if (!("townLimit" in resumeState)) resumeState.townLimit <- -1;
    if (!("scanIndex" in resumeState)) resumeState.scanIndex <- 0;
    if (!("scanSites" in resumeState)) resumeState.scanSites <- [];
    if (!("scanProbes" in resumeState)) resumeState.scanProbes <- null;
    if (!("rankIndex" in resumeState)) resumeState.rankIndex <- 0;
    if (!("rankSites" in resumeState)) resumeState.rankSites <- [];
    if (!("c83TopTownIds" in resumeState)) resumeState.c83TopTownIds <- null;
  }
  if (C121_AIR_ECONOMICS) {
    if (sliced) {
      if (!("c121PlanPerf" in resumeState)) {
        resumeState.c121PlanPerf <- { calls = 0, demandOps = 0, demandTicks = 0,
            staticOps = 0, staticTicks = 0, scanOps = 0, scanTicks = 0,
            engineEvals = 0, winnerOps = 0, winnerTicks = 0, noWinner = 0,
            endpointHits = 0, endpointMisses = 0 };
      }
      if (!("c121EndpointCache" in resumeState)) resumeState.c121EndpointCache <- {};
      C121_AIR_PLAN_PERF = resumeState.c121PlanPerf;
      C121_AIR_ENDPOINT_CACHE = resumeState.c121EndpointCache;
    } else {
      C121_AIR_PLAN_PERF = { calls = 0, demandOps = 0, demandTicks = 0,
          staticOps = 0, staticTicks = 0, scanOps = 0, scanTicks = 0,
          engineEvals = 0, winnerOps = 0, winnerTicks = 0, noWinner = 0,
          endpointHits = 0, endpointMisses = 0 };
      C121_AIR_ENDPOINT_CACHE = {};
    }
  } else {
    C121_AIR_PLAN_PERF = null;
    C121_AIR_ENDPOINT_CACHE = null;
  }
  local perfOpsSites = sliced ? resumeState.perfOpsSites : 0;
  local perfOpsEval = sliced ? resumeState.perfOpsEval : 0;
  local perfProbesCount = sliced ? resumeState.perfProbesCount : 0;
  local perfCheapSkip = sliced ? resumeState.perfCheapSkip : 0;
  local perfSitesFound = sliced ? resumeState.perfSitesFound : 0;

  local combos = sliced && resumeState.combos != null
      ? resumeState.combos
      : ((("airCombos" in catalog) && catalog.airCombos != null && catalog.airCombos.len() > 0)
          ? catalog.airCombos
          : (catalog.airport != null && catalog.plane != null ? [{ airport = catalog.airport, plane = catalog.plane }] : []));
  if (sliced && resumeState.combos == null) resumeState.combos = combos;
  local servedDiag = sliced && ("servedDiag" in resumeState) ? resumeState.servedDiag : null;
  if (DECISION_LOG && servedDiag == null) {
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
    if (sliced) resumeState.servedDiag <- servedDiag;
  }
  if (combos.len() == 0) {
    if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "no_engine", 1);
    if (DECISION_LOG) {
      OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
                 + " null_calls=0 empty_calls=0 nonempty_calls=0 true_calls=0 false_calls=0"
                 + " false_towns_logged=0");
    }
    if (sliced) {
      resumeState.bestPlan = null;
      resumeState.sites = null;
      resumeState.done = true;
    }
    if (C80_AIR_EVAL_FAST) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
    }
    ctx.bestPlan = null;
    return false;
  }

  /* C80 tranche 5 bis : index exacts des lignes aeriennes, construits une fois par appel (les
   * lignes ne changent pas pendant la planification). Memes resolutions de gare que les boucles
   * qu'ils remplacent : nombre de routes par gare (decouverte des hubs) et paires deja reliees
   * (hub a hub), au lieu d'un parcours de toutes les lignes par hub et par paire de hubs. */
  local hubIndex = null;
  if (C80_AIR_HUB_INDEX && AIR_HUB && lines != null) {
    hubIndex = { routes = {}, pairs = {} };
    foreach (other in lines) {
      if (!("mode" in other) || other.mode != "air") continue;
      local oA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
          : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
      local oB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
          : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
      hubIndex.routes.rawset(oA, ((oA in hubIndex.routes) ? hubIndex.routes[oA] : 0) + 1);
      if (oB != oA) hubIndex.routes.rawset(oB, ((oB in hubIndex.routes) ? hubIndex.routes[oB] : 0) + 1);
      if (AIStation.IsValidStation(oA) && AIStation.IsValidStation(oB)) {
        hubIndex.pairs.rawset(oA + "|" + oB, true);
        hubIndex.pairs.rawset(oB + "|" + oA, true);
      }
    }
  }

  local c83TopTownIds = sliced && resumeState.c83TopTownIds != null
      ? resumeState.c83TopTownIds
      : {};
  local towns = sliced && resumeState.towns != null
      ? resumeState.towns
      : OpexAirSortedTowns(catalog.towns);
  if (!sliced || resumeState.towns == null) {
    /* C83.1 : la double prise proactive ne concerne que les plus grandes
     * villes deja couvertes par la politique early-slot. Calculer ce rang
     * avant une eventuelle remise en tete targetTownId preserve le vrai
     * classement par population. */
    if (OpexAirC83SlotSignalEnabled() && AIR_C83_TARGET_TOWNS > 0) {
      /* c83_fixes ne retouche pas cette liste : elle autorise le second slot
       * proactif d'une ville DEJA servie par Opex (C83.1 adopte). Le filtre
       * Ãƒâ€šÃ‚Â« ville encore disputable, Opex absent Ãƒâ€šÃ‚Â» ne concerne que le watcher. */
      local c83TopLimit = towns.len() < AIR_C83_TARGET_TOWNS
          ? towns.len() : AIR_C83_TARGET_TOWNS;
      for (local c83i = 0; c83i < c83TopLimit; c83i++) {
        if (towns[c83i].pop >= AIR_EARLY_SLOT_MIN_POP) {
          c83TopTownIds.rawset(towns[c83i].id, true);
        }
      }
    }
    if (sliced) resumeState.c83TopTownIds = c83TopTownIds;
    if (targetTownId >= 0) {
      local targetedTowns = [];
      foreach (town in towns) if (town.id == targetTownId) targetedTowns.append(town);
      foreach (town in towns) if (town.id != targetTownId) targetedTowns.append(town);
      towns = targetedTowns;
    } else if (C121_CATALOG_INCREMENTAL && sliced) {
      OpexC121CatalogRankDirtyTowns();
      towns.sort(OpexC121CatalogTownPriorityCompare);
    }
    if (sliced) resumeState.towns = towns;
  }
  local limit = sliced && resumeState.townLimit >= 0
      ? resumeState.townLimit
      : OpexAirTownPoolLimit(towns);
  if (sliced) resumeState.townLimit = limit;
  /* C78 etape 2 : une generation complete journalisee par an, sous sonde seulement (aucun appel
   * d'API au defaut). Les bornes et les tuiles permettent de situer toute paire d'AAAHogEx par
   * rapport aux bandes de distance (airMin = bascule rail/avion). En mode reprenable (C78.4),
   * la decision est prise a la premiere tranche et conservee dans resumeState. */
  local c78Year = -1;
  local c78Gen = false;
  if (sliced && ("c78Gen" in resumeState)) {
    c78Year = resumeState.c78Year;
    c78Gen = resumeState.c78Gen;
  } else {
    if (C69_BOTTLENECK_PROBE && targetTownId < 0) {
      c78Year = AIDate.GetYear(AIDate.GetCurrentDate());
      c78Gen = C78_GEN_LOG_YEAR != c78Year;
    }
    if (c78Gen) {
      C78_GEN_LOG_YEAR = c78Year;
      local poolLimit = towns.len() < 120 ? towns.len() : 120;
      local townsStr = "";
      for (local idx = 0; idx < poolLimit; idx++) {
        if (idx > 0) townsStr += ",";
        townsStr += towns[idx].id + ":" + towns[idx].pop + ":" + towns[idx].tile;
      }
      local c78B = OpexCatalogBounds(catalog);
      OpexC78Log("C78_AIRPOOL", "year=" + c78Year + " pool=" + limit
          + " mapx=" + AIMap.GetMapSizeX() + " airMin=" + c78B.airMin + " airMax=" + c78B.airMax
          + " railMin=" + c78B.railMin + " railMax=" + c78B.railMax
          + " overlap=" + c78B.railAirOverlapMin
          + " e_cash=" + AIError.ERR_NOT_ENOUGH_CASH + " e_authority=" + AIError.ERR_LOCAL_AUTHORITY_REFUSES
          + " e_clear=" + AIError.ERR_AREA_NOT_CLEAR + " e_flat=" + AIError.ERR_FLAT_LAND_REQUIRED
          + " e_site=" + AIError.ERR_SITE_UNSUITABLE
          + " e_town_stations=" + AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN
          + " e_too_close=" + AIStation.ERR_STATION_TOO_CLOSE_TO_ANOTHER_STATION
          + " towns=" + townsStr);
    }
    if (sliced) {
      resumeState.c78Year <- c78Year;
      resumeState.c78Gen <- c78Gen;
    }
  }
  local stationLimitedTowns = sliced ? resumeState.stationLimitedTowns : {};
  local bestPlan = sliced ? resumeState.bestPlan : null;
  /* GetMonthlyMaintenanceCost expose le tarif potentiel, pas une depense toujours active.
   * CompaniesGenStatistics ne le debite que si le reglage de partie est arme. La configuration
   * gelee le laisse a false : compter ce tarif rendait toutes les paires de la graine 42
   * artificiellement deficitaires (270 000/an pour deux AT_LARGE). */
  local infrastructureMaintenance =
      AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local comboStart = sliced ? resumeState.combo : 0;

  ctx.combos = combos;
  ctx.servedDiag = servedDiag;
  ctx.hubIndex = hubIndex;
  ctx.c83TopTownIds = c83TopTownIds;
  ctx.towns = towns;
  ctx.limit = limit;
  ctx.c78Year = c78Year;
  ctx.c78Gen = c78Gen;
  ctx.stationLimitedTowns = stationLimitedTowns;
  ctx.bestPlan = bestPlan;
  ctx.infrastructureMaintenance = infrastructureMaintenance;
  ctx.comboStart = comboStart;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;

  return true;
}

/* 2. Recherche des sites : sondage des villes candidates et revalidation avant classement. */
function OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo)
{
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local opsBudget = ctx.opsBudget;
  local deadlineTick = ctx.deadlineTick;
  local limit = ctx.limit;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local towns = ctx.towns;
  local lines = ctx.lines;
  local targetTownId = ctx.targetTownId;
  local servedDiag = ctx.servedDiag;
  local c83TopTownIds = ctx.c83TopTownIds;
  local c78Gen = ctx.c78Gen;
  local c78Year = ctx.c78Year;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local bestPlan = ctx.bestPlan;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  local sites = resumingCombo ? resumeState.sites : [];
  if (!resumingCombo) {
    local scanSites = sliced ? resumeState.scanSites : [];
    local probes = sliced && resumeState.scanProbes != null
        ? resumeState.scanProbes
        : {
            left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
            stationLimitedTowns = stationLimitedTowns
          };
    local scanStart = sliced ? resumeState.scanIndex : 0;
    local scanEnd = limit;
    if (C83_FIXES && targetTownId >= 0) {
      scanEnd = scanStart;
      for (local c83Scan = scanStart; c83Scan < limit; c83Scan++) {
        if (towns[c83Scan].id == targetTownId) {
          scanEnd = c83Scan + 1;
          break;
        }
      }
    }
    local testedBefore = probes.tested;
    local cheapBefore = ("cheapSkip" in probes) ? probes.cheapSkip : 0;
    local foundBefore = scanSites.len();
    local tSites0 = AIController.GetTick();
    local lSites0 = AIController.GetOpsTillSuspend();
    for (local i = scanStart; i < scanEnd; i++) {
      probes.townsLeft = limit - i;
      if (C83_FIXES && targetTownId >= 0) probes.townsLeft = scanEnd - i;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      if (towns[i].id in stationLimitedTowns) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_station_limit", 1);
        if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_station_limit");
      } else {
        /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
         * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
         * construction aerienne sur une carte partiellement couverte. */
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        if (isServed && !c83OwnSecondSlot) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "origin_served", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=origin_served");
        } else if (!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600) {
          /* Grands aeroports : accessibles des 600 habitants. A 0, le booleen
           * est le seul test ajoute sur ce chemin. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_small", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_small");
        } else if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP) {
          /* V93 : plancher minimal, grand ou petit. A 0 ce test est faux. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_v93", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_v93");
        } else {
          local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
              ? targetTownId : -1;
          if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
            c83RequiredSlotTown = towns[i].id;
          }
          if (c78Gen && ("c78NoSite" in probes)) probes.c78NoSite = null;
          local site = OpexAirFindSite(towns[i], airport, probes, c83RequiredSlotTown);
          if (site != null) {
            if (c83OwnSecondSlot) site.c83OwnSecondSlot <- true;
            if (C83_FIXES && c83RequiredSlotTown >= 0) site.c83SlotTown <- c83RequiredSlotTown;
            scanSites.append(site);
            if (c78Gen) {
              if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < 600) {
                OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site v93=1 pop=" + towns[i].pop);
              } else {
                OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site");
              }
            }
          }
          else {
            if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "no_site", 1);
            if (c78Gen) {
              local c78Outcome = "no_site_terrain";
              if (("c78NoSite" in probes) && probes.c78NoSite != null) c78Outcome = probes.c78NoSite;
              if (c78Outcome != "no_site_slot" && OpexAirC83SlotSignalEnabled()
                  && AITown.GetAllowedNoise(towns[i].id) < 1) {
                c78Outcome = "no_site_slot";
              }
              OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=" + c78Outcome);
            }
          }
        }
      }
      if (sliced) {
        resumeState.combo = comboIndex;
        resumeState.scanIndex = i + 1;
        resumeState.scanSites = scanSites;
        resumeState.scanProbes = probes;
        local scanSliceOps = _calcDeltaOps(t0_all, l0_all);
        if ((opsBudget > 0 && scanSliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
          perfOpsSites += _calcDeltaOps(tSites0, lSites0);
          perfProbesCount += probes.tested - testedBefore;
          perfCheapSkip += (("cheapSkip" in probes) ? probes.cheapSkip : 0) - cheapBefore;
          perfSitesFound += scanSites.len() - foundBefore;
          resumeState.bestPlan = bestPlan;
          resumeState.stationLimitedTowns = stationLimitedTowns;
          resumeState.perfOpsSites = perfOpsSites;
          resumeState.perfOpsEval = perfOpsEval;
          resumeState.perfProbesCount = perfProbesCount;
          resumeState.perfCheapSkip = perfCheapSkip;
          resumeState.perfSitesFound = perfSitesFound;
          resumeState.totalOps += scanSliceOps;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          return false;
        }
      }
    }
    perfOpsSites += _calcDeltaOps(tSites0, lSites0);
    if (sliced) {
      perfProbesCount += probes.tested - testedBefore;
      perfCheapSkip += (("cheapSkip" in probes) ? probes.cheapSkip : 0) - cheapBefore;
      perfSitesFound += scanSites.len() - foundBefore;
    } else {
      perfProbesCount += probes.tested;
      if ("cheapSkip" in probes) perfCheapSkip += probes.cheapSkip;
      perfSitesFound += scanSites.len();
    }

    /* C78.4 : la revalidation peut elle aussi consommer plusieurs ticks. Elle
     * reprend par index de site ; aucun site valide n'est sonde deux fois juste
     * parce qu'une tranche a rendu la main. */
    local rankableSites = sliced ? resumeState.rankSites : [];
    local rankStart = sliced ? resumeState.rankIndex : 0;
    for (local rankIndex = rankStart; rankIndex < scanSites.len(); rankIndex++) {
      local site = scanSites[rankIndex];
      if (OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
        rankableSites.append(site);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("air", "site_stale_before_rank", 1);
      }
      if (sliced) {
        resumeState.combo = comboIndex;
        resumeState.rankIndex = rankIndex + 1;
        resumeState.rankSites = rankableSites;
        local rankSliceOps = _calcDeltaOps(t0_all, l0_all);
        if ((opsBudget > 0 && rankSliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
          resumeState.bestPlan = bestPlan;
          resumeState.stationLimitedTowns = stationLimitedTowns;
          resumeState.perfOpsSites = perfOpsSites;
          resumeState.perfOpsEval = perfOpsEval;
          resumeState.perfProbesCount = perfProbesCount;
          resumeState.perfCheapSkip = perfCheapSkip;
          resumeState.perfSitesFound = perfSitesFound;
          resumeState.totalOps += rankSliceOps;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          return false;
        }
      }
    }
    sites = rankableSites;
    if (sliced) {
      resumeState.combo = comboIndex;
      resumeState.a = 0;
      resumeState.b = 1;
      resumeState.sites = sites;
      resumeState.scanIndex = 0;
      resumeState.scanSites = [];
      resumeState.scanProbes = null;
      resumeState.rankIndex = 0;
      resumeState.rankSites = [];
    }
  }
  /* En mode reprenable, ne pas reconstruire le meme panneau a chaque
   * tranche de paires. Outre la pollution de SIGN, AISign.BuildSign consomme
   * des opcodes et faisait de la reprise elle-meme une part majeure du cout. */
  if (!sliced || !resumingCombo) {
    OpexSign(AIMap.GetTileIndex(1, 3), "AS|S=" + sites.len() + "|A=" + airport.name);
  }

  ctx.sites = sites;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;
  return true;
}

/* 3. Arm Ãƒâ€šÃ‚Â« nouvelles paires Ãƒâ€šÃ‚Â» : evaluation de toutes les paires (a, b) de sites neufs. */
function OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo)
{
  local sites = ctx.sites;
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local opsBudget = ctx.opsBudget;
  local deadlineTick = ctx.deadlineTick;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local targetTownId = ctx.targetTownId;
  local lines = ctx.lines;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local projects = ctx.projects;
  local c78Gen = ctx.c78Gen;
  local c78Year = ctx.c78Year;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local bestPlan = ctx.bestPlan;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  local tEval0 = AIController.GetTick();
  local lEval0 = AIController.GetOpsTillSuspend();
  local siteValidity = {};
  /* Une regeneration AIR ciblee sur une ville ne conservera plus tard que les
   * projets qui touchent cette ville. OpexAirPlansPrepare met deja la cible en
   * tete : dans le cas normal, evaluer seulement a=0 transforme C(n,2) en O(n)
   * sans changer l'ensemble de candidats finalement reinjecte. Si l'invariant
   * ne tient pas, repli exact sur le parcours complet + filtre historique. */
  local targetSiteIndex = -1;
  if (targetTownId >= 0) {
    for (local targetIndex = 0; targetIndex < sites.len(); targetIndex++) {
      if (sites[targetIndex].town.id == targetTownId) {
        targetSiteIndex = targetIndex;
        break;
      }
    }
  }
  local pairOuterLimit = sites.len();
  if (targetTownId >= 0 && targetSiteIndex < 0) pairOuterLimit = 0;
  else if (targetTownId >= 0 && targetSiteIndex == 0) pairOuterLimit = 1;
  local startA = sliced && resumeState.combo == comboIndex ? resumeState.a : 0;
  local pairProgress = false;
  for (local a = startA; a < pairOuterLimit; a++) {
    local startB = sliced && resumeState.combo == comboIndex && a == startA
        ? resumeState.b : a + 1;
    for (local b = startB; b < sites.len(); b++) {
      if (sliced) {
        resumeState.bestPlan = bestPlan;
        resumeState.perfOpsSites = perfOpsSites;
        resumeState.perfOpsEval = perfOpsEval + _calcDeltaOps(tEval0, lEval0);
        resumeState.perfProbesCount = perfProbesCount;
        resumeState.perfCheapSkip = perfCheapSkip;
        resumeState.perfSitesFound = perfSitesFound;
        local sliceOps = _calcDeltaOps(t0_all, l0_all);
        /* Toujours consommer au moins UNE paire par appel. Le cout fixe de
         * reprise peut depasser le reliquat du tick ; rendre la main avant la
         * premiere paire bloquait alors eternellement sur le meme curseur. */
        if (pairProgress && ((opsBudget > 0 && sliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick))) {
          resumeState.totalOps += sliceOps;
          ctx.bestPlan = bestPlan;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          return false;
        }
        resumeState.combo = comboIndex;
        resumeState.sites = sites;
        local nextA = a;
        local nextB = b + 1;
        if (nextB >= sites.len()) {
          nextA = a + 1;
          nextB = nextA + 1;
        }
        resumeState.a = nextA;
        resumeState.b = nextB;
        pairProgress = true;
        if (resumingCombo) {
          local keyA = sites[a].anchor;
          local keyB = sites[b].anchor;
          if (!(keyA in siteValidity)) {
            siteValidity.rawset(keyA, OpexAirSiteStillBuildable(
                sites[a], airport, plane, false, stationLimitedTowns));
          }
          if (!siteValidity[keyA]) continue;
          if (!(keyB in siteValidity)) {
            siteValidity.rawset(keyB, OpexAirSiteStillBuildable(
                sites[b], airport, plane, false, stationLimitedTowns));
          }
          if (!siteValidity[keyB]) continue;
        }
      }
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airPairs++;
      if (targetTownId >= 0
          && sites[a].town.id != targetTownId && sites[b].town.id != targetTownId) continue;
      if (C83_FIXES && OpexAirTownCentersLinked(sites[a].town.tile, sites[b].town.tile, lines)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "batch_plan_dead", 1);
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + linkedDist + " outcome=batch_plan_dead P=-1 C=-1");
        }
        continue;
      }
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
      if (C80_AIR_EVAL_FAST) {
        if (distance < minDist) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
          continue;
        }
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      sites[a].anchor, sites[b].anchor);
      local flightDistance = OpexFlightDistance(sites[a].anchor, sites[b].anchor);
      if (!C80_AIR_EVAL_FAST && distance < minDist) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }

      if (abandoned != null) {
        if (OpexAirPairIsAbandoned(abandoned, sites[a], sites[b])
            || (OPEX_AIR_TOWN_PAD && ((OpexAirTownPaddingKey(sites[a]) in abandoned)
                || (OpexAirTownPaddingKey(sites[b]) in abandoned)))
            || (OPEX_AIR_SITE_PAD && ((OpexAirSitePaddingKey(sites[a], airport.type) in abandoned)
                || (OpexAirSitePaddingKey(sites[b], airport.type) in abandoned)))) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }

      local popA = sites[a].town.pop;
      local popB = sites[b].town.pop;
      local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthlyPax = OpexAirTownMonthlyPax(sites[a].town, sites[a].anchor, airport, ctx.lines)
            + OpexAirTownMonthlyPax(sites[b].town, sites[b].anchor, airport, ctx.lines);
      }
      if (a == 0 && b == 1) {
        OpexSign(AIMap.GetTileIndex(1, 5), "AX|PA=" + popA + "|PB=" + popB + "|MPX=" + monthlyPax);
      }

      local plan = {
        siteA = sites[a], siteB = sites[b], distance = flightDistance,
        orderDistance = orderDistance,
        airport = airport, plane = plane,
        monthlyPax = monthlyPax, planes = 1, capital = 0, economics = null,
        reuseA = false, reuseB = false, hubRoutes = 0, arm = "newpair",
        c83OwnSecondSlotA = ("c83OwnSecondSlot" in sites[a]) && sites[a].c83OwnSecondSlot,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in sites[b]) && sites[b].c83OwnSecondSlot,
      };
      local routeChoice = C121_AIR_ECONOMICS
          ? (C121_CATALOG_INCREMENTAL
              ? OpexC121CatalogChoice(catalog, plan, ctx.lines)
              : OpexC121ChooseRoutePlane(catalog, plan, ctx.lines))
          : OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 2, opcodePadding,
              C80_AIR_CHOICE_MEMO ? ("n|" + sites[a].town.id + "|" + sites[b].town.id
                  + "|" + airport.type + "|" + plane.id) : null,
              C119_AIR_INCOME_MODEL
                  ? AIMap.DistanceManhattan(sites[a].anchor, sites[b].anchor) : 0);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      local admissionEconomics = (C113_AIR_C100_FULL_DECISION_SHADOW && decisionEconomics != null)
          ? decisionEconomics : economics;
      if (EQUIPMENT_ROI_PROBE && routePlane != null && economics != null) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 2, opcodePadding, economics, "pre_admission_newpair");
      }
      if (economics == null) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "economics_unavailable", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
        continue;
      }

      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, sites[a].anchor, sites[b].anchor);
      }
      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (C118_AIR_TERRITORIAL_EXPANSION && ("c118C68Plane" in routeChoice)
          && ("c118C68Economics" in routeChoice)) {
        plan.c118C68Plane <- routeChoice.c118C68Plane;
        plan.c118C68Economics <- routeChoice.c118C68Economics;
        if ("c118EngineChoices" in routeChoice) plan.c118EngineChoices <- routeChoice.c118EngineChoices;
      }
      if (C121_AIR_ECONOMICS) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      } else if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);

      if (a == 0 && b == 1) {
        OpexSign(AIMap.GetTileIndex(1, 8), "AY|" + economics.capital + "|"
                                              + economics.profitAnnual);
        OpexSign(AIMap.GetTileIndex(1, 9), "AV|" + routePlane.speed + "|" + routePlane.capacity
                                              + "|" + economics.planes + "|"
                                              + economics.oneWayDays.tointeger());
      }
      if (admissionEconomics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "profit_nonpositive", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
      } else {
        if (c78Gen) {
          if (V93_AIR_DEMAND_PRODUCTION) {
            local paxOld = ((sites[a].town.pop + sites[b].town.pop) * TOWN_CATCHMENT_SHARE_PCT) / 100;
            if (paxOld < 10) paxOld = 10;
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        if (C97_AIR_C69_ENGINE_PROBE) OpexC97ProbeAirEngine(catalog, plan);
        bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
      }
    }
  }
  perfOpsEval += _calcDeltaOps(tEval0, lEval0);
  if (sliced) {
    resumeState.a = sites.len();
    resumeState.b = sites.len();
    resumeState.bestPlan = bestPlan;
    resumeState.perfOpsEval = perfOpsEval;
    local pairSliceOps = _calcDeltaOps(t0_all, l0_all);
    if ((opsBudget > 0 && pairSliceOps >= opsBudget)
        || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
      resumeState.perfOpsSites = perfOpsSites;
      resumeState.perfProbesCount = perfProbesCount;
      resumeState.perfCheapSkip = perfCheapSkip;
      resumeState.perfSitesFound = perfSitesFound;
      resumeState.totalOps += pairSliceOps;
      ctx.bestPlan = bestPlan;
      ctx.perfOpsSites = perfOpsSites;
      ctx.perfOpsEval = perfOpsEval;
      ctx.perfProbesCount = perfProbesCount;
      ctx.perfCheapSkip = perfCheapSkip;
      ctx.perfSitesFound = perfSitesFound;
      return false;
    }
  }

  ctx.bestPlan = bestPlan;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;
  return true;
}

/* 4. Decouverte des hubs : lignes existantes et aeroports orphelins. */
function OpexAirPlansDiscoverHubs(ctx, combo, airport, plane)
{
  /* Bras hub : un aeroport existant, rentable et non sature (max 8 routes), plus UNE destination. */
  local hubs = [];
  local sites = ctx.sites;
  local lines = ctx.lines;
  local limit = ctx.limit;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local towns = ctx.towns;
  local targetTownId = ctx.targetTownId;
  local servedDiag = ctx.servedDiag;
  local c83TopTownIds = ctx.c83TopTownIds;
  local hubIndex = ctx.hubIndex;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  if (AIR_HUB && lines != null) {
    if (sites.len() < AIR_HUB_NEW_SITE_POOL) {
      local hubProbes = {
        left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
        stationLimitedTowns = stationLimitedTowns
      };
      local tHubSites0 = AIController.GetTick();
      local lHubSites0 = AIController.GetOpsTillSuspend();
      local hubScanEnd = limit;
      if (C83_FIXES && targetTownId >= 0) {
        hubScanEnd = 0;
        for (local c83Scan = 0; c83Scan < limit; c83Scan++) {
          if (towns[c83Scan].id == targetTownId) {
            hubScanEnd = c83Scan + 1;
            break;
          }
        }
      }
      for (local i = 0; i < hubScanEnd && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
        hubProbes.townsLeft = limit - i;
        if (C83_FIXES && targetTownId >= 0) hubProbes.townsLeft = hubScanEnd - i;
        if (towns[i].id in stationLimitedTowns) {
          continue;
        }
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        if (isServed && !c83OwnSecondSlot) continue;
        /* Typage : grands aeroports des 600 hab. A 0, seul le booleen est ajoute. */
        if (!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600) continue;
        if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP) continue;
        if (combo.kind == "small" && towns[i].pop >= 2500) continue;
        local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
            ? targetTownId : -1;
        if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
          c83RequiredSlotTown = towns[i].id;
        }
        local extraSite = OpexAirFindSite(towns[i], airport, hubProbes, c83RequiredSlotTown);
        if (extraSite != null) {
          if (c83OwnSecondSlot) extraSite.c83OwnSecondSlot <- true;
          if (C83_FIXES && c83RequiredSlotTown >= 0) extraSite.c83SlotTown <- c83RequiredSlotTown;
          /* v93=1 seulement si le scan principal n'a pas deja retenu cette ville. */
          if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < 600 && ("c78Gen" in ctx) && ctx.c78Gen) {
            local v93Already = false;
            foreach (prev in sites) {
              if (("town" in prev) && prev.town != null && ("id" in prev.town) && prev.town.id == towns[i].id) {
                v93Already = true;
                break;
              }
            }
            if (!v93Already) {
              OpexC78Log("C78_AIRTOWN", "year=" + ctx.c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site v93=1 pop=" + towns[i].pop);
            }
          }
          sites.append(extraSite);
          ctx.perfSitesFound++;
        }
      }
      ctx.perfOpsSites += _calcDeltaOps(tHubSites0, lHubSites0);
      ctx.perfProbesCount += hubProbes.tested;
      if ("cheapSkip" in hubProbes) ctx.perfCheapSkip += hubProbes.cheapSkip;
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
        if (hubIndex != null) {
          if (station in hubIndex.routes) routeCount = hubIndex.routes[station];
        } else {
          foreach (other in lines) {
            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
                : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
            local otherB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
                : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
            if (otherA == station || otherB == station) routeCount++;
          }
        }
        local maxRoutes = OpexAirAirportMaxRoutes(existingType);
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
    /* AÃƒÆ’Ã‚Â©roports orphelins : aÃƒÆ’Ã‚Â©roports bÃƒÆ’Ã‚Â¢tis sans ligne active (ex: issu d'un BFAIL conservÃƒÆ’Ã‚Â©). */
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

  /* La decouverte des hubs et des sites supplementaires peut elle aussi
   * suspendre. Revalider les destinations neuves au dernier moment avant
   * le classement hub-site. */
  if (sites.len() > 0) {
    local liveHubSites = [];
    foreach (site in sites) {
      if (OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
        liveHubSites.append(site);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("air", "site_stale_before_rank", 1);
      }
    }
    sites = liveHubSites;
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

  ctx.sites = sites;
  ctx.hubs = hubs;
}

/* 5. Arm Ãƒâ€šÃ‚Â« hub vers site Ãƒâ€šÃ‚Â» : evaluation des paires (hub existant, site neuf). */
function OpexAirPlansHubToSite(ctx, combo, airport, plane)
{
  local hubs = ctx.hubs;
  local sites = ctx.sites;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local c78Year = ctx.c78Year;
  local c78Gen = ctx.c78Gen;
  local projects = ctx.projects;
  local bestPlan = ctx.bestPlan;
  local targetTownId = ctx.targetTownId;
  local lines = ctx.lines;

  local incrementalSlice = ctx.sliced && C121_CATALOG_INCREMENTAL;
  local resumeHub = incrementalSlice && ("hubSiteI" in ctx.resumeState)
      ? ctx.resumeState.hubSiteI : 0;
  local resumeSite = incrementalSlice && ("hubSiteJ" in ctx.resumeState)
      ? ctx.resumeState.hubSiteJ : 0;
  local progressed = false;
  for (local hi = resumeHub; hi < hubs.len(); hi++) {
    local hub = hubs[hi];
    local hubMonthlyPre = C80_AIR_EVAL_FAST
        ? (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1))
        : 0;
    for (local sj = hi == resumeHub ? resumeSite : 0; sj < sites.len(); sj++) {
      if (incrementalSlice) {
        local used = OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all);
        if (progressed && ((ctx.opsBudget > 0 && used >= ctx.opsBudget)
            || (ctx.deadlineTick > 0 && AIController.GetTick() >= ctx.deadlineTick))) {
          ctx.resumeState.hubSiteI <- hi;
          ctx.resumeState.hubSiteJ <- sj;
          ctx.bestPlan = bestPlan;
          return false;
        }
        progressed = true;
      }
      local site = sites[sj];
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airHubSitePairs++;
      if (targetTownId >= 0
          && hub.town.id != targetTownId && site.town.id != targetTownId) continue;
      if (C83_FIXES && OpexAirTownCentersLinked(hub.town.tile, site.town.tile, lines)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "batch_plan_dead", 1);
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + linkedDist + " outcome=batch_plan_dead P=-1 C=-1");
        }
        continue;
      }
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
      if (distance < 20) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      hub.anchor, site.anchor);
      local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }
      if (abandoned != null) {
        if (OpexAirPairIsAbandoned(abandoned, hub, site)
            || (OPEX_AIR_TOWN_PAD && (OpexAirTownPaddingKey(site) in abandoned))
            || (OPEX_AIR_SITE_PAD && (OpexAirSitePaddingKey(site, airport.type) in abandoned))) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }
      local hubMonthly = C80_AIR_EVAL_FAST
          ? hubMonthlyPre
          : (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1));
      local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local monthlyPax = hubMonthly + newMonthly;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthlyPax = OpexAirTownMonthlyPax(hub.town, hub.anchor, airport, ctx.lines)
            + OpexAirTownMonthlyPax(site.town, site.anchor, airport, ctx.lines);
      }
      local plan = {
        siteA = hub, siteB = site, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = plane, monthlyPax = monthlyPax, planes = 1,
        capital = 0, economics = null,
        reuseA = true, reuseB = false, hubRoutes = hub.routes, arm = "hubsite",
        c83OwnSecondSlotA = false,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in site) && site.c83OwnSecondSlot,
      };
      local routeChoice = C121_AIR_ECONOMICS
          ? (C121_CATALOG_INCREMENTAL
              ? OpexC121CatalogChoice(catalog, plan, ctx.lines)
              : OpexC121ChooseRoutePlane(catalog, plan, ctx.lines))
          : OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 1, opcodePadding,
              C80_AIR_CHOICE_MEMO ? ("h|" + hub.stationId + "|" + site.town.id
                  + "|" + airport.type + "|" + plane.id) : null,
              C119_AIR_INCOME_MODEL
                  ? AIMap.DistanceManhattan(hub.anchor, site.anchor) : 0);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      local admissionEconomics = (C113_AIR_C100_FULL_DECISION_SHADOW && decisionEconomics != null)
          ? decisionEconomics : economics;
      if (EQUIPMENT_ROI_PROBE && routePlane != null && economics != null) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 1, opcodePadding, economics, "pre_admission_hubsite");
      }
      if (economics == null || admissionEconomics == null || admissionEconomics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) {
          if (economics == null) OpexC73RecordRejection("air", "economics_unavailable", 1);
          else OpexC73RecordRejection("air", "profit_nonpositive", 1);
        }
        if (c78Gen) {
          if (economics == null) {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        continue;
      }
      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub.anchor, site.anchor);
      }
      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (C118_AIR_TERRITORIAL_EXPANSION && ("c118C68Plane" in routeChoice)
          && ("c118C68Economics" in routeChoice)) {
        plan.c118C68Plane <- routeChoice.c118C68Plane;
        plan.c118C68Economics <- routeChoice.c118C68Economics;
        if ("c118EngineChoices" in routeChoice) plan.c118EngineChoices <- routeChoice.c118EngineChoices;
      }
      if (C121_AIR_ECONOMICS) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      } else if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);
      if (admissionEconomics.profitAnnual <= 0) continue;
      if (c78Gen) {
        if (V93_AIR_DEMAND_PRODUCTION) {
          local paxOld = (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1))
              + ((site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100);
          if (paxOld < 10) paxOld = 10;
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
        } else {
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
        }
      }
      if (C97_AIR_C69_ENGINE_PROBE) OpexC97ProbeAirEngine(catalog, plan);
      bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
    }
  }
  ctx.bestPlan = bestPlan;
  if (incrementalSlice) {
    ctx.resumeState.hubSiteI <- hubs.len();
    ctx.resumeState.hubSiteJ <- 0;
  }
  return true;
}

/* 6. Arm Ãƒâ€šÃ‚Â« hub vers hub Ãƒâ€šÃ‚Â» : liaisons directes entre deux aeroports existants. */
function OpexAirPlansHubToHub(ctx, combo, airport, plane)
{
  /* Liaisons Hub-a-Hub directes entre deux aeroports existants (capital = 1 avion seul) */
  local hubs = ctx.hubs;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local c78Year = ctx.c78Year;
  local c78Gen = ctx.c78Gen;
  local projects = ctx.projects;
  local lines = ctx.lines;
  local hubIndex = ctx.hubIndex;
  local bestPlan = ctx.bestPlan;
  local targetTownId = ctx.targetTownId;

  local hubAvgIncome = [];
  if (AIR_HUBHUB_MARGINAL) {
    for (local h = 0; h < hubs.len(); h++) hubAvgIncome.append(0.0);
    if (lines != null && hubs.len() > 0) {
      local hubIndexByStation = {};
      for (local h = 0; h < hubs.len(); h++) {
        hubIndexByStation.rawset(hubs[h].stationId, h);
      }
      local hubLinesCount = [];
      local hubLinesIncomeSum = [];
      for (local h = 0; h < hubs.len(); h++) {
        hubLinesCount.append(0);
        hubLinesIncomeSum.append(0.0);
      }
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        if (("deadStreak" in line) && line.deadStreak >= 2) continue;
        local stA = AIR_HUB_FIX ? OpexAirLineStationId(line, 0)
            : (AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA));
        local stB = AIR_HUB_FIX ? OpexAirLineStationId(line, 1)
            : (AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB));
        if (!AIStation.IsValidStation(stA) || !AIStation.IsValidStation(stB)) continue;

        local dist = ("distance" in line && line.distance > 0)
            ? line.distance
            : (AIMap.IsValidTile(line.stationA) && AIMap.IsValidTile(line.stationB)
                ? OpexFlightDistance(line.stationA, line.stationB) : 0);
        if (dist <= 0) continue;
        local days = ("predOneWayDays" in line && line.predOneWayDays > 0) ? line.predOneWayDays : 0;
        local incomeDays = OpexCeilDiv(days, 1);
        if (incomeDays < 1) incomeDays = 1;
        local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, dist, incomeDays);
        local totalIncomePerUnit = paxIncome;
        if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
          local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, dist, incomeDays);
          totalIncomePerUnit = paxIncome + (mailIncome * 15) / 100;
        }
        local incomePerUnit = (totalIncomePerUnit * AIR_PAX_REVENUE_CALIBRATION_PCT) / 100.0;

        if (stA in hubIndexByStation) {
          local h = hubIndexByStation[stA];
          hubLinesCount[h]++;
          hubLinesIncomeSum[h] += incomePerUnit;
        }
        if (stB in hubIndexByStation && stB != stA) {
          local h = hubIndexByStation[stB];
          hubLinesCount[h]++;
          hubLinesIncomeSum[h] += incomePerUnit;
        }
      }
      for (local h = 0; h < hubs.len(); h++) {
        if (hubLinesCount[h] > 0) {
          hubAvgIncome[h] = hubLinesIncomeSum[h] / hubLinesCount[h];
        }
      }
    }
  }

  local incrementalSlice = ctx.sliced && C121_CATALOG_INCREMENTAL;
  local resumeI = incrementalSlice && ("hubHubI" in ctx.resumeState)
      ? ctx.resumeState.hubHubI : 0;
  local resumeJ = incrementalSlice && ("hubHubJ" in ctx.resumeState)
      ? ctx.resumeState.hubHubJ : 1;
  local progressed = false;
  for (local i = resumeI; i < hubs.len(); i++) {
    local hub1MonthlyPre = C80_AIR_EVAL_FAST
        ? (((hubs[i].town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hubs[i].routes + 1))
        : 0;
    for (local j = i == resumeI ? resumeJ : i + 1; j < hubs.len(); j++) {
      if (incrementalSlice) {
        local used = OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all);
        if (progressed && ((ctx.opsBudget > 0 && used >= ctx.opsBudget)
            || (ctx.deadlineTick > 0 && AIController.GetTick() >= ctx.deadlineTick))) {
          ctx.resumeState.hubHubI <- i;
          ctx.resumeState.hubHubJ <- j;
          ctx.bestPlan = bestPlan;
          return false;
        }
        progressed = true;
      }
      if (CATALOG_COST_ACTIVE != null) CATALOG_COST_ACTIVE.airHubHubPairs++;
      local hub1 = hubs[i];
      local hub2 = hubs[j];
      if (targetTownId >= 0
          && hub1.town.id != targetTownId && hub2.town.id != targetTownId) continue;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local st1 = hub1.stationId;
      local st2 = hub2.stationId;
      local alreadyConnected = false;
      if (hubIndex != null) {
        alreadyConnected = (st1 + "|" + st2) in hubIndex.pairs;
      } else
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
      if (alreadyConnected) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "already_connected", 1);
        if (c78Gen) {
          local c78Dist = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + c78Dist + " outcome=already_connected P=-1 C=-1");
        }
        continue;
      }
      local distance = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
      if (distance < 20) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
      local flightDistance = OpexFlightDistance(hub1.anchor, hub2.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }
      if (OpexAirPairIsAbandoned(abandoned, hub1, hub2)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
        continue;
      }
      local monthly1 = C80_AIR_EVAL_FAST
          ? hub1MonthlyPre
          : (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1));
      local monthly2 = ((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1);
      local monthlyPax = monthly1 + monthly2;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthly1 = OpexAirTownMonthlyPax(hub1.town, hub1.anchor, airport, lines);
        monthly2 = OpexAirTownMonthlyPax(hub2.town, hub2.anchor, airport, lines);
        monthlyPax = monthly1 + monthly2;
      }
      local plan = {
        siteA = hub1, siteB = hub2, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = plane, monthlyPax = monthlyPax, planes = 1,
        capital = 0, economics = null,
        reuseA = true, reuseB = true, hubRoutes = hub1.routes + hub2.routes,
        arm = "hubhub",
      };
      local routeChoice = C121_AIR_ECONOMICS
          ? (C121_CATALOG_INCREMENTAL
              ? OpexC121CatalogChoice(catalog, plan, lines)
              : OpexC121ChooseRoutePlane(catalog, plan, lines))
          : OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
              infrastructureMaintenance, maxCapital, 0, opcodePadding,
              C80_AIR_CHOICE_MEMO ? ("hh|" + hub1.stationId + "|" + hub2.stationId
                  + "|" + airport.type + "|" + plane.id) : null,
              C119_AIR_INCOME_MODEL
                  ? AIMap.DistanceManhattan(hub1.anchor, hub2.anchor) : 0);
      local routePlane = routeChoice != null ? routeChoice.plane : null;
      local economics = routeChoice != null ? routeChoice.economics : null;
      local decisionEconomics = (routeChoice != null && ("decisionEconomics" in routeChoice) && routeChoice.decisionEconomics != null)
          ? routeChoice.decisionEconomics : null;
      if (EQUIPMENT_ROI_PROBE && routePlane != null && economics != null) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 0, opcodePadding, economics, "pre_admission_hubhub");
      }
      if (AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS
          && economics != null && economics.profitAnnual > 0) {
        /* V86 Variante A : retrancher la perte de revenu annuel des lignes aeriennes existantes.
         * Hypothese : CargoDist etant desactive (DT_MANUAL), les passagers montent dans le premier avion
         * quelle que soit sa destination. La nouvelle ligne hub->hub cannibalise les passagers des lignes
         * existantes des deux hubs. Aucun gain de note de gare (station rating) n'est modelise. */
        local pax1 = (monthlyPax > 0) ? (economics.carried.tofloat() * monthly1) / monthlyPax : 0.0;
        if (pax1 > monthly1) pax1 = monthly1.tofloat();
        local pax2 = (monthlyPax > 0) ? (economics.carried.tofloat() * monthly2) / monthlyPax : 0.0;
        if (pax2 > monthly2) pax2 = monthly2.tofloat();
        local lossAnnual = (12.0 * (pax1 * hubAvgIncome[i] + pax2 * hubAvgIncome[j])).tointeger();
        if (lossAnnual > 0) {
          economics = clone economics;
          economics.profitAnnual -= lossAnnual;
          local totalCapital = economics.capital + economics.immobilise;
          economics.roi = totalCapital > 0 ? (economics.profitAnnual * 1000) / totalCapital : 0;
        }
      }
      if (AIR_HUBHUB_MARGINAL && !C121_AIR_ECONOMICS
          && decisionEconomics != null && decisionEconomics.profitAnnual > 0) {
        local decisionPax1 = (monthlyPax > 0) ? (decisionEconomics.carried.tofloat() * monthly1) / monthlyPax : 0.0;
        if (decisionPax1 > monthly1) decisionPax1 = monthly1.tofloat();
        local decisionPax2 = (monthlyPax > 0) ? (decisionEconomics.carried.tofloat() * monthly2) / monthlyPax : 0.0;
        if (decisionPax2 > monthly2) decisionPax2 = monthly2.tofloat();
        local decisionLossAnnual = (12.0 * (decisionPax1 * hubAvgIncome[i] + decisionPax2 * hubAvgIncome[j])).tointeger();
        if (decisionLossAnnual > 0) {
          decisionEconomics = clone decisionEconomics;
          decisionEconomics.profitAnnual -= decisionLossAnnual;
          local decisionTotalCapital = decisionEconomics.capital + decisionEconomics.immobilise;
          decisionEconomics.roi = decisionTotalCapital > 0
              ? (decisionEconomics.profitAnnual * 1000) / decisionTotalCapital : 0;
        }
      }
      local admissionEconomics = (C113_AIR_C100_FULL_DECISION_SHADOW && decisionEconomics != null)
          ? decisionEconomics : economics;
      if (economics == null || admissionEconomics == null || admissionEconomics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) {
          if (economics == null) OpexC73RecordRejection("air", "economics_unavailable", 1);
          else OpexC73RecordRejection("air", "profit_nonpositive", 1);
        }
        if (c78Gen) {
          if (economics == null) {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        continue;
      }
      if (decisionEconomics != null && decisionEconomics.profitAnnual <= 0) continue;
      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
      }
      plan.orderDistance = orderDistance;
      plan.plane = routePlane;
      plan.planes = economics.planes;
      plan.capital = economics.capital;
      plan.economics = economics;
      if (decisionEconomics != null) plan.decisionEconomics <- decisionEconomics;
      if (C118_AIR_TERRITORIAL_EXPANSION && ("c118C68Plane" in routeChoice)
          && ("c118C68Economics" in routeChoice)) {
        plan.c118C68Plane <- routeChoice.c118C68Plane;
        plan.c118C68Economics <- routeChoice.c118C68Economics;
        if ("c118EngineChoices" in routeChoice) plan.c118EngineChoices <- routeChoice.c118EngineChoices;
      }
      if (C121_AIR_ECONOMICS) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      } else if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);
      /* C113 : l'admission a deja ete arbitree sur le shadow C68. Le profit
       * legacy du moteur replay peut etre negatif sans invalider le marche de
       * decision ; hors C113, admissionEconomics == economics et le contrat
       * historique reste strictement identique. */
      if (admissionEconomics.profitAnnual <= 0) continue;
      if (c78Gen) {
        if (V93_AIR_DEMAND_PRODUCTION) {
          local paxOld = (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1))
              + (((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1));
          if (paxOld < 10) paxOld = 10;
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
        } else {
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
        }
      }
      if (C97_AIR_C69_ENGINE_PROBE) OpexC97ProbeAirEngine(catalog, plan);
      bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
    }
  }
  ctx.bestPlan = bestPlan;
  if (incrementalSlice) {
    ctx.resumeState.hubHubI <- hubs.len();
    ctx.resumeState.hubHubJ <- 0;
  }
  return true;
}

/* V95 : diagnostic annuel, strictement passif, des occasions que le scan courant
 * n'atteint pas parce que la ville est deja servie ou sous le plancher de 600.
 * La sonde ne remplit ni AIR_SITE_CACHE, ni ctx.sites, ni le portefeuille. */
function OpexAirV95Log(fields)
{
  if (!V95_AIR_POST73_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("V95_AIR_POST73 year=" + AIDate.GetYear(date)
      + " month=" + AIDate.GetMonth(date) + " " + fields);
}

/* Cout de terrassement estime seul. AITestMode ne modifie pas le terrain, donc
 * on ne peut pas enchainer dessus un BuildAirport fiable ; le cout de site publie
 * separement airport.price + ce terrassement, sans pretendre inclure les arbres. */
function OpexAirV95LevelCost(site, airport)
{
  if (site == null || airport == null) return -1;
  if (OpexAirFootprintIsFlat(site.anchor, airport)) return 0;
  local accounting = AIAccounting();
  local ok = false;
  {
    local test = AITestMode();
    ok = AITile.LevelTiles(site.anchor, OpexAirFootprintEnd(site.anchor, airport));
  }
  if (!ok) return -1;
  local cost = accounting.GetCosts();
  if (cost < 0) cost = -cost;
  return cost;
}

/* Meilleur raccordement du site ignore vers un hub Opex existant, avec les memes
 * filtres et le meme proxy de demande que le bras hub->site courant. On ne memoise
 * pas le choix d'avion : c'est une lecture ponctuelle du C68 courant. */
function OpexAirV95BestHubRoute(ctx, site, airport, plane)
{
  local result = { best = null, reject = "no_hub" };
  if (ctx.hubs == null || ctx.hubs.len() == 0) return result;
  result.reject = "distance_or_band";
  foreach (hub in ctx.hubs) {
    /* La revalidation de chantier refuse toujours une paire de centres deja
     * reliee, meme quand c83_fixes=0. Le shadow doit appliquer le meme contrat,
     * sinon il surestime les extensions V95 qui mourraient avant tentative. */
    if (OpexAirTownCentersLinked(hub.town.tile, site.town.tile, ctx.lines)) {
      result.reject = "already_linked";
      continue;
    }
    local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
    if (distance < 20) continue;
    local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
    if (!OpexAirPairInBand(ctx.catalog, distance, flightDistance, ctx.paxBand)) continue;
    if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
    if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) continue;
    if (ctx.abandoned != null
        && (OpexAirPairIsAbandoned(ctx.abandoned, hub, site)
            || (OPEX_AIR_TOWN_PAD && (OpexAirTownPaddingKey(site) in ctx.abandoned))
            || (OPEX_AIR_SITE_PAD && (OpexAirSitePaddingKey(site, airport.type) in ctx.abandoned)))) {
      result.reject = "abandoned";
      continue;
    }

    local hubMonthly = ((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1);
    local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
    local monthlyPax = hubMonthly + newMonthly;
    if (monthlyPax < 10) monthlyPax = 10;
    local choice = OpexAirChooseRoutePlane(ctx.catalog, airport, plane, flightDistance, monthlyPax,
        ctx.infrastructureMaintenance, 0, 1, 0, null,
        C119_AIR_INCOME_MODEL ? AIMap.DistanceManhattan(hub.anchor, site.anchor) : 0);
    local econ = choice != null ? choice.economics : null;
    if (econ == null) {
      result.reject = "economics_unavailable";
      continue;
    }
    if (econ.profitAnnual <= 0) {
      result.reject = "profit_nonpositive";
      continue;
    }
    if (result.best == null || econ.profitAnnual > result.best.economics.profitAnnual
        || (econ.profitAnnual == result.best.economics.profitAnnual
            && econ.roi > result.best.economics.roi)) {
      result.best = {
        hub = hub, choice = choice, economics = econ,
        distance = flightDistance, monthlyPax = monthlyPax
      };
      result.reject = "candidate";
    }
  }
  return result;
}

function OpexAirV95Post73Probe(ctx, combo, airport, plane)
{
  if (!V95_AIR_POST73_PROBE || ctx.targetTownId >= 0) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (year < 1973 || V95_AIR_POST73_YEAR == year) return;
  if (!(("kind" in combo) && combo.kind == "large")) return;
  V95_AIR_POST73_YEAR = year;

  local ownCounts = OpexAirOwnSlotTownCounts();
  local available = OpexAvailableCapital();
  local smallCount = 0;
  local secondCount = 0;
  local siteCount = 0;
  local profitableCount = 0;
  local affordableCount = 0;
  local scanLimit = ctx.limit < ctx.towns.len() ? ctx.limit : ctx.towns.len();

  for (local i = 0; i < scanLimit; i++) {
    local town = ctx.towns[i];
    local served = OpexAirTownServed(town, ctx.lines);
    local c83OwnSecond = served && (town.id in ctx.c83TopTownIds)
        && OpexAirC83SecondSlotOpen(town);
    local isSmall = town.pop < OpexAirLargeAirportMinPop();
    local isSecond = served && !c83OwnSecond;
    if (!isSmall && !isSecond) continue;

    local currentReject = "";
    if (town.id in ctx.stationLimitedTowns) {
      currentReject = "station_limit";
    } else if (isSecond) {
      currentReject = "origin_served";
    } else if (!V93_AIRPORT_NO_POP_FLOOR && isSmall) {
      currentReject = "pop_floor";
    } else {
      continue;
    }

    if (isSmall) smallCount++;
    if (isSecond) secondCount++;
    local family = isSmall ? (isSecond ? "small_second" : "small") : "second";

    local requiredSlotTown = isSecond ? town.id : -1;
    local preSlots = OpexAirC83SlotSignalEnabled() ? AITown.GetAllowedNoise(town.id) : -1;
    local preOwn = (town.id in ownCounts) ? ownCounts[town.id] : 0;
    if (requiredSlotTown >= 0 && preSlots == 0) {
      OpexAirV95Log("phase=town family=" + family + " town=" + town.id + " pop=" + town.pop
          + " current_reject=" + currentReject
          + " shadow_reject=slot_closed served=" + (served ? 1 : 0)
          + " slot_town=" + town.id + " slots_remaining=0 own_airports=" + preOwn
          + " competitor_airports=" + (2 - preOwn));
      continue;
    }

    local probes = {
      left = AIR_MAX_SITE_PROBES, townsLeft = 1, tested = 0, cheapSkip = 0,
      stationLimitedTowns = {}
    };
    local key = "v95|" + year + "|" + town.id + "|" + airport.type;
    local found = OpexAirFindSiteListed(town, airport, probes, requiredSlotTown, key, false);
    local site = found.site;
    if (site == null) {
      local reason = probes.left <= 0 ? "site_budget" : "site_terrain";
      if (town.id in probes.stationLimitedTowns) reason = "site_slot";
      OpexAirV95Log("phase=town family=" + family + " town=" + town.id + " pop=" + town.pop
          + " current_reject=" + currentReject + " shadow_reject=" + reason
          + " served=" + (served ? 1 : 0) + " slots_remaining=" + preSlots
          + " own_airports=" + preOwn + " probes=" + found.used);
      continue;
    }
    siteCount++;

    local slotTown = OpexAirSlotTownId(site.anchor);
    local slotsRemaining = (slotTown >= 0 && OpexAirC83SlotSignalEnabled())
        ? AITown.GetAllowedNoise(slotTown) : -1;
    local ownAirports = (slotTown in ownCounts) ? ownCounts[slotTown] : 0;
    local occupied = slotsRemaining >= 0 ? 2 - slotsRemaining : -1;
    local competitors = occupied >= 0 ? occupied - ownAirports : -1;
    if (competitors < 0 && occupied >= 0) competitors = 0;

    local paxProd = AITown.GetLastMonthProduction(town.id, ctx.catalog.paxCargo);
    if (paxProd < 0) paxProd = 0;
    local mailProd = -1;
    if (("mailCargo" in ctx.catalog) && ctx.catalog.mailCargo >= 0) {
      mailProd = AITown.GetLastMonthProduction(town.id, ctx.catalog.mailCargo);
      if (mailProd < 0) mailProd = 0;
    }
    local paxTiles = OpexAirAirportCatchmentProduction(site.anchor, airport.type, ctx.catalog.paxCargo);
    local mailTiles = -1;
    if (("mailCargo" in ctx.catalog) && ctx.catalog.mailCargo >= 0) {
      mailTiles = OpexAirAirportCatchmentProduction(site.anchor, airport.type, ctx.catalog.mailCargo);
    }
    local houses = AITown.GetHouseCount(town.id);
    if (houses < 1) houses = 1;
    local paxSiteEst = (paxTiles * paxProd) / houses;
    local mailSiteEst = mailProd >= 0 && mailTiles >= 0 ? (mailTiles * mailProd) / houses : -1;
    local levelCost = OpexAirV95LevelCost(site, airport);
    local siteCost = airport.price + (levelCost > 0 ? levelCost : 0);

    local route = OpexAirV95BestHubRoute(ctx, site, airport, plane);
    local shadowReject = route.reject;
    local planeId = -1;
    local profit = -1;
    local capital = -1;
    local roi = -1;
    local hubTown = -1;
    local monthlyProxy = -1;
    local measuredMonthly = -1;
    local measuredPlaneId = -1;
    local measuredProfit = -1;
    local measuredCapital = -1;
    local measuredRoi = -1;
    local hubOnlyMonthly = -1;
    local hubOnlyPlaneId = -1;
    local hubOnlyProfit = -1;
    if (route.best != null) {
      profitableCount++;
      planeId = route.best.choice.plane != null ? route.best.choice.plane.id : -1;
      profit = route.best.economics.profitAnnual;
      capital = route.best.economics.capital;
      roi = route.best.economics.roi;
      hubTown = route.best.hub.town.id;
      monthlyProxy = route.best.monthlyPax;
      if (capital > available) {
        shadowReject = "cash";
      } else {
        shadowReject = "candidate";
        affordableCount++;
      }

      /* Contre-factuel diagnostic minimal : meme site, meme hub et meme C68,
       * mais la demande du nouveau site est remplacee par la production de
       * bassin estimee ci-dessus. Le hub existant garde son proxy courant. */
      local hubMonthlyMeasured = ((route.best.hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100)
          / (route.best.hub.routes + 1);
      measuredMonthly = hubMonthlyMeasured + paxSiteEst;
      if (measuredMonthly < 10) measuredMonthly = 10;
      local measuredChoice = OpexAirChooseRoutePlane(ctx.catalog, airport, plane,
          route.best.distance, measuredMonthly, ctx.infrastructureMaintenance, 0, 1, 0, null);
      if (measuredChoice != null && measuredChoice.economics != null) {
        measuredPlaneId = measuredChoice.plane != null ? measuredChoice.plane.id : -1;
        measuredProfit = measuredChoice.economics.profitAnnual;
        measuredCapital = measuredChoice.economics.capital;
        measuredRoi = measuredChoice.economics.roi;
      }
      hubOnlyMonthly = hubMonthlyMeasured;
      if (hubOnlyMonthly < 10) hubOnlyMonthly = 10;
      local hubOnlyChoice = OpexAirChooseRoutePlane(ctx.catalog, airport, plane,
          route.best.distance, hubOnlyMonthly, ctx.infrastructureMaintenance, 0, 1, 0, null);
      if (hubOnlyChoice != null && hubOnlyChoice.economics != null) {
        hubOnlyPlaneId = hubOnlyChoice.plane != null ? hubOnlyChoice.plane.id : -1;
        hubOnlyProfit = hubOnlyChoice.economics.profitAnnual;
      }
    }

    OpexAirV95Log("phase=town family=" + family + " town=" + town.id + " pop=" + town.pop
        + " current_reject=" + currentReject + " shadow_reject=" + shadowReject
        + " served=" + (served ? 1 : 0)
        + " anchor=" + site.anchor + " slot_town=" + slotTown
        + " slots_remaining=" + slotsRemaining + " own_airports=" + ownAirports
        + " competitor_airports=" + competitors
        + " pax_prod=" + paxProd + " mail_prod=" + mailProd
        + " pax_tiles=" + paxTiles + " mail_tiles=" + mailTiles
        + " pax_site_est=" + paxSiteEst + " mail_site_est=" + mailSiteEst
        + " airport_price=" + airport.price + " level_cost=" + levelCost
        + " site_cost_est=" + siteCost
        + " hub_town=" + hubTown + " plane=" + planeId
        + " monthly_proxy=" + monthlyProxy + " profit=" + profit
        + " capital=" + capital + " roi=" + roi + " available=" + available
        + " measured_monthly=" + measuredMonthly + " measured_plane=" + measuredPlaneId
        + " measured_profit=" + measuredProfit + " measured_capital=" + measuredCapital
        + " measured_roi=" + measuredRoi
        + " hub_only_monthly=" + hubOnlyMonthly + " hub_only_plane=" + hubOnlyPlaneId
        + " hub_only_profit=" + hubOnlyProfit
        + " probes=" + found.used);
  }
  OpexAirV95Log("phase=summary towns=" + scanLimit + " small=" + smallCount
      + " second=" + secondCount + " sites=" + siteCount
      + " profitable=" + profitableCount + " affordable=" + affordableCount
      + " hubs=" + ctx.hubs.len() + " available=" + available);
}

/* 7. Finalisation : enregistrement des perf, sondes et nettoyage de la reprise. */
function OpexAirPlansFinalize(ctx)
{
  local servedDiag = ctx.servedDiag;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local bestPlan = ctx.bestPlan;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local combos = ctx.combos;
  local projects = ctx.projects;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  if (DECISION_LOG) {
    OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
               + " null_calls=" + servedDiag.nullCalls + " empty_calls=" + servedDiag.emptyCalls
               + " nonempty_calls=" + servedDiag.nonemptyCalls + " true_calls=" + servedDiag.trueCalls
               + " false_calls=" + servedDiag.falseCalls
               + " false_towns_logged=" + servedDiag.loggedFalseCount);
  }
  local totalOps = _calcDeltaOps(t0_all, l0_all);
  if (CATALOG_COST_ACTIVE != null) {
    local cost = CATALOG_COST_ACTIVE;
    cost.airScans++;
    cost.airTowns += ctx.limit;
    cost.airCombos += combos.len();
    cost.airSiteProbes += perfProbesCount;
    cost.airSites += perfSitesFound;
    cost.airSiteOps += perfOpsSites;
    cost.airEvalOps += perfOpsEval;
    if (C121_AIR_PLAN_PERF != null) {
      cost.c121Calls += C121_AIR_PLAN_PERF.calls;
      cost.c121DemandOps += C121_AIR_PLAN_PERF.demandOps;
      cost.c121StaticOps += C121_AIR_PLAN_PERF.staticOps;
      cost.c121ScanOps += C121_AIR_PLAN_PERF.scanOps;
      cost.c121EngineEvals += C121_AIR_PLAN_PERF.engineEvals;
      cost.c121WinnerOps += C121_AIR_PLAN_PERF.winnerOps;
    }
  }
  local elapsedTicks = AIController.GetTick() - t0_all;
  if (sliced) {
    totalOps += resumeState.totalOps;
    elapsedTicks = AIController.GetTick() - resumeState.startTick;
    resumeState.totalOps = totalOps;
    resumeState.bestPlan = bestPlan;
    resumeState.done = true;
    resumeState.sites = null;
    resumeState.towns = null;
    resumeState.combos = null;
    if (C80_AIR_EVAL_FAST) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
    }
  }
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
             + " sites=" + perfSitesFound
             + " c121_calls=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.calls : 0)
             + " c121_demand_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.demandOps : 0)
             + " c121_demand_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.demandTicks : 0)
             + " c121_static_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.staticOps : 0)
             + " c121_static_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.staticTicks : 0)
             + " c121_scan_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.scanOps : 0)
             + " c121_scan_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.scanTicks : 0)
             + " c121_engine_evals=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.engineEvals : 0)
             + " c121_winner_ops=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.winnerOps : 0)
             + " c121_winner_ticks=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.winnerTicks : 0)
             + " c121_no_winner=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.noWinner : 0)
             + " c121_endpoint_hits=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.endpointHits : 0)
             + " c121_endpoint_misses=" + (C121_AIR_PLAN_PERF != null ? C121_AIR_PLAN_PERF.endpointMisses : 0));
  OpexSign(AIMap.GetTileIndex(1, 2), "AP|T=" + totalOps + "|S=" + perfOpsSites + "|E=" + perfOpsEval + "|TK=" + elapsedTicks);
  if (C69_BOTTLENECK_PROBE) {
    local actualPlans = (projects != null) ? projects.len() : (bestPlan != null ? 1 : 0);
    OpexC73RecordProduced("air", actualPlans, actualPlans);
  }
  if (C80_AIR_EVAL_FAST && !sliced) {
    AIR_ECONOMICS_MEMO = {};
    AIR_TRIP_MEMO = {};
  }
  return bestPlan;
}

/* Index du prochain combo kind=small apres comboIndex, ou -1. Aucun appel d'API. */
function OpexAirV93NextSmallCombo(combos, comboIndex)
{
  local nextSmall = comboIndex + 1;
  while (nextSmall < combos.len()) {
    local candidate = combos[nextSmall];
    if (("kind" in candidate) && candidate.kind == "small") return nextSmall;
    nextSmall++;
  }
  return -1;
}

/* `abandoned` : table des paires dont une construction a deja echoue (cle
 * canonique OpexAirPairKey), et optionnellement des
 * sites exacts et types ("air_site|airportType|anchor"). null = filtre desactive.
 * Le filtre est place APRES les tests de distance et AVANT OpexAirEconomics : les paires
 * ecartees pour distance ne paient pas la concatenation, et celles qui restent evitent le
 * calcul cher. */
function OpexAirPlans(catalog, lines = null, maxCapital = 0, projects = null, abandoned = null,
                      paxBand = PAX_BAND_ALL, targetTownId = -1,
                      resumeState = null, opsBudget = 0, deadlineTick = 0)
{
  local t0_all = AIController.GetTick();
  local l0_all = AIController.GetOpsTillSuspend();
  local _calcDeltaOps = OpexAirCalcDeltaOps;
  local ctx = {
    catalog = catalog,
    lines = lines,
    maxCapital = maxCapital,
    projects = projects,
    abandoned = abandoned,
    paxBand = paxBand,
    targetTownId = targetTownId,
    resumeState = resumeState,
    opsBudget = opsBudget,
    deadlineTick = deadlineTick,
    t0_all = t0_all,
    l0_all = l0_all,
    sliced = resumeState != null,
    combos = null,
    servedDiag = null,
    hubIndex = null,
    c83TopTownIds = null,
    towns = null,
    limit = 0,
    c78Year = -1,
    c78Gen = false,
    stationLimitedTowns = null,
    bestPlan = null,
    infrastructureMaintenance = false,
    comboStart = 0,
    perfOpsSites = 0,
    perfOpsEval = 0,
    perfProbesCount = 0,
    perfCheapSkip = 0,
    perfSitesFound = 0,
    sites = [],
    hubs = []
  };

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_prepare", "-");
  local prepared = OpexAirPlansPrepare(ctx);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_prepare", "-",
      "combos=" + (ctx.combos != null ? ctx.combos.len() : 0) + " towns=" + (ctx.towns != null ? ctx.towns.len() : 0)
      + " target=" + targetTownId);
  if (!prepared) {
    return ctx.bestPlan;
  }

  for (local comboIndex = ctx.comboStart; comboIndex < ctx.combos.len(); comboIndex++) {
    local combo = ctx.combos[comboIndex];
    local airport = combo.airport;
    local plane = combo.plane;
    local minDist = (plane.speed >= 400) ? 32 : 30;
    local resumingCombo = ctx.sliced && ctx.resumeState.combo == comboIndex && ctx.resumeState.sites != null;

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_find_sites", "-");
    local sitesOk = OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_find_sites", "-",
        "combo=" + comboIndex + " sites=" + ctx.sites.len() + " probes=" + ctx.perfProbesCount);
    if (!sitesOk) {
      return ctx.bestPlan;
    }

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_new_pairs", "-");
    local pairsOk = OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_new_pairs", "-",
        "combo=" + comboIndex + " plans=" + (ctx.projects != null ? ctx.projects.len() : -1));
    if (!pairsOk) {
      return ctx.bestPlan;
    }

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hubs", "-");
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_discover", "-");
    OpexAirPlansDiscoverHubs(ctx, combo, airport, plane);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_discover", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len());
    OpexAirV95Post73Probe(ctx, combo, airport, plane);

    local c56PlansBefore = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_site", "-");
    local tHubEval0 = AIController.GetTick();
    local lHubEval0 = AIController.GetOpsTillSuspend();
    if (!ctx.sliced || !C121_CATALOG_INCREMENTAL
        || !("hubPhase" in ctx.resumeState) || ctx.resumeState.hubPhase < 1) {
      if (!OpexAirPlansHubToSite(ctx, combo, airport, plane)) return ctx.bestPlan;
      if (ctx.sliced && C121_CATALOG_INCREMENTAL) ctx.resumeState.hubPhase <- 1;
    }
    local c56PlansMid = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_site", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len() + " admitted=" + (c56PlansMid - c56PlansBefore));
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_hub", "-");
    if (!OpexAirPlansHubToHub(ctx, combo, airport, plane)) return ctx.bestPlan;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_hub", "-",
        "hubs=" + ctx.hubs.len() + " admitted=" + (((ctx.projects != null) ? ctx.projects.len() : 0) - c56PlansMid));
    ctx.perfOpsEval += _calcDeltaOps(tHubEval0, lHubEval0);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hubs", "-", "hubs=" + ctx.hubs.len());

    if (AIR_HUB && ctx.hubs.len() > 0) {
      OpexSign(AIMap.GetTileIndex(1, 6), "AU|" + ctx.hubs.len() + "|"
               + (ctx.bestPlan != null && ctx.bestPlan.reuseA ? 1 : 0));
    }
    OpexSign(AIMap.GetTileIndex(1, 4), "AE|S=" + ctx.sites.len() + "|B=" + (ctx.bestPlan != null ? ctx.bestPlan.economics.profitAnnual : "NO"));
    if (ctx.sliced) {
      ctx.resumeState.combo = comboIndex + 1;
      ctx.resumeState.a = 0;
      ctx.resumeState.b = 1;
      ctx.resumeState.sites = null;
      ctx.resumeState.scanIndex = 0;
      ctx.resumeState.scanSites = [];
      ctx.resumeState.scanProbes = null;
      ctx.resumeState.rankIndex = 0;
      ctx.resumeState.rankSites = [];
      if (C121_CATALOG_INCREMENTAL) {
        ctx.resumeState.hubPhase <- 0;
        ctx.resumeState.hubSiteI <- 0;
        ctx.resumeState.hubSiteJ <- 0;
        ctx.resumeState.hubHubI <- 0;
        ctx.resumeState.hubHubJ <- 1;
      }
      ctx.resumeState.bestPlan = ctx.bestPlan;
      ctx.resumeState.stationLimitedTowns = ctx.stationLimitedTowns;
      ctx.resumeState.perfOpsSites = ctx.perfOpsSites;
      ctx.resumeState.perfOpsEval = ctx.perfOpsEval;
      ctx.resumeState.perfProbesCount = ctx.perfProbesCount;
      ctx.resumeState.perfCheapSkip = ctx.perfCheapSkip;
      ctx.resumeState.perfSitesFound = ctx.perfSitesFound;
    }
    /* Un plan grand arrete la boucle. Sous V93, les combos petits qui suivent
     * sont quand meme parcourus ; les grands suivants restent sautes. A 0, le
     * booleen provoque le meme break, sans helper ni appel d'API. */
    local bestPlan = ctx.bestPlan;
    if (bestPlan != null && bestPlan.airport.allowBig) {
      if (!V93_AIRPORT_NO_POP_FLOOR) break;
      if (!(("kind" in combo) && combo.kind == "small")) {
        local nextSmall = OpexAirV93NextSmallCombo(ctx.combos, comboIndex);
        if (nextSmall < 0) break;
        if (ctx.sliced) ctx.resumeState.combo = nextSmall;
        comboIndex = nextSmall - 1;
      }
    }
  }

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_finalize", "-");
  local finalPlan = OpexAirPlansFinalize(ctx);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_finalize", "-");
  return finalPlan;
}

/* Sondage pur d'un site : rend 0 s'il accepte l'aeroport, sinon le code d'erreur. Ne depense
 * rien et NE LAISSE AUCUNE TRACE dans la comptabilite du caller.
 *
 * ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Les deux pieges de ce sondage, mesures dans le source de 15.3 :
 *
 * 1. AIAccounting compte AUSSI les commandes jouees en AITestMode --
 *    `if (estimate_only) IncreaseDoCommandCosts(res.GetCost())`, script_object.cpp:299-302.
 *    Un sondage d'aeroport ajoute donc son prix SIMULE au compteur sans qu'une livre sorte :
 *    +35 000 Ãƒâ€šÃ‚Â£ par ligne au premier essai du 2026-09-02 (ratio cout/modele 1,02 -> 1,38).
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
  /* G7Ãƒâ€šÃ‚Â§1 : l'ancien code ne retirait que airportB. airportA -- toujours passe en premier
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

      candidates.append({ tile = tile, value = val, dist = AIMap.DistanceManhattan(tile, town.tile) });
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

    local front = null;
    foreach (dir in dirs) {
      local tryFront = cand.tile + dir;
      if (!AIMap.IsValidTile(tryFront) || !AIRoad.IsRoadTile(tryFront)) continue;
      if (!AIRoad.AreRoadTilesConnected(cand.tile, tryFront)) continue;
      local testOk = false;
      {
        local test = AITestMode();
        testOk = AIRoad.BuildDriveThroughRoadStation(
            cand.tile, tryFront, AIRoad.ROADVEHTYPE_BUS, stationId);
      }
      if (testOk) {
        front = tryFront;
        break;
      }
    }
    if (front == null) continue;

    local ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, front, AIRoad.ROADVEHTYPE_BUS, stationId);
    if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(town.id, 800, 40);
      ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, front, AIRoad.ROADVEHTYPE_BUS, stationId);
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
function OpexBuildAirRoute(catalog, budget, plan, lines = null)
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
  local airportErrorA = 0;
  local airportErrorTextA = "";
  local airportErrorB = 0;
  local airportErrorTextB = "";

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
    if (!okA) {
      local errorA = AIError.GetLastError();
      if (errorA == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
        OpexBoostTownRating(plan.siteA.town.id, 800, 40);
        okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
        if (!okA) {
          airportErrorA = AIError.GetLastError();
          airportErrorTextA = AIError.GetLastErrorString();
        }
      } else {
        airportErrorA = errorA;
        airportErrorTextA = AIError.GetLastErrorString();
      }
    }
    if (okA && AIAirport.IsAirportTile(plan.siteA.anchor)) airportA = plan.siteA.anchor;
  }
  if (airportA == null) {
    if (!reuseA) {
      OpexAirInvalidateCachedSite(plan.siteA, airport);
      result.error = airportErrorA;
      result.errorText = airportErrorTextA;
    }
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
    if (!okB) {
      local errorB = AIError.GetLastError();
      if (errorB == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
        OpexBoostTownRating(plan.siteB.town.id, 800, 40);
        okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
        if (!okB) {
          airportErrorB = AIError.GetLastError();
          airportErrorTextB = AIError.GetLastErrorString();
        }
      } else {
        airportErrorB = errorB;
        airportErrorTextB = AIError.GetLastErrorString();
      }
    }
    if (okB && AIAirport.IsAirportTile(plan.siteB.anchor)) airportB = plan.siteB.anchor;
  }
  result.opcodes += budget.end("build_airports");
  if (airportB == null) {
    if (!reuseB) {
      OpexAirInvalidateCachedSite(plan.siteB, airport);
      result.error = airportErrorB;
      result.errorText = airportErrorTextB;
    }
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

  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local okOrderA = AIOrder.AppendOrder(plane, airportA, airFlagsA);
  local errorA = okOrderA ? 0 : AIError.GetLastError();
  local okOrderB = AIOrder.AppendOrder(plane, airportB, airFlagsB);
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
  /* c121_aaa_line : le second avion part du hangar de l'aeroport B et commence par le
   * trajet retour, comme AAAHogEx (route.nut:2232-2237). */
  local hangarB = C121_AAA_LINE ? AIAirport.GetHangarOfAirport(airportB) : null;
  for (local i = 1; i < wanted; i++) {
    local fromB = (i % 2 == 1) && hangarB != null && AIMap.IsValidTile(hangarB)
        && AIAirport.IsHangarTile(hangarB);
    local extra = AIVehicle.CloneVehicle(fromB ? hangarB : hangar, plane, true);
    if (fromB && AIVehicle.IsValidVehicle(extra)) AIOrder.SkipToOrder(extra, 1);
    if (!AIVehicle.IsValidVehicle(extra)) {
      local engine = AIVehicle.GetEngineType(plane);
      extra = AIVehicle.BuildVehicleWithRefit(hangar, engine, catalog.paxCargo);
      if (AIVehicle.IsValidVehicle(extra) && !AIOrder.ShareOrders(extra, plane)) {
        result.error = AIError.GetLastError();
        result.errorText = AIError.GetLastErrorString();
        built.append(extra);
        result.opcodes += budget.end("build_aircraft");
        OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built);
        result.actualCost = costs != null ? costs.GetCosts() : 0;
        result.reason = "ORDFAIL";
        return result;
      }
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
  if (C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
    OpexC121MeasureBuiltEconomics(catalog, plan, result);
  }
  if (V92_AIR_SERVICE_CHOICE && ("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local builtMail = AIVehicle.GetCapacity(plane, catalog.mailCargo);
    if (builtMail >= 0 && planeChoice != null) AIR_MAIL_CAP.rawset(planeChoice.id, builtMail);
  }
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
    local predictedAnnualProfit = (("economics" in plan) && plan.economics != null
        && ("profitAnnual" in plan.economics)) ? plan.economics.profitAnnual : 0;
    local predictedAnnualRevenue = (("economics" in plan) && plan.economics != null
        && ("revenueAnnual" in plan.economics)) ? plan.economics.revenueAnnual : 0;
    local routeDivA = reuseA && ("routes" in plan.siteA) ? plan.siteA.routes + 1 : 1;
    local routeDivB = reuseB && ("routes" in plan.siteB) ? plan.siteB.routes + 1 : 1;
    OpexAirCatchmentLog("AIR_CATCHMENT_BUILD",
        "arm=" + (("arm" in plan) ? plan.arm : "unknown")
        + " base_source=" + (OPEX_AIR_PLAN_PAD ? "demand_plan" : "town_population_proxy")
        + " base_monthly=" + plan.monthlyPax
        + " route_div_a=" + routeDivA + " route_div_b=" + routeDivB
        + " reserve_stop_cost=" + (("joinedStopReserve" in plan) ? plan.joinedStopReserve : 0)
        + " actual_stop_cost=" + result.joinedStopCost + " stop_limit=" + AIR_JOINED_STOP_LIMIT
        + " stops_a=" + result.joinedStopsA + " stops_b=" + result.joinedStopsB
        + " model_joined_a=" + result.joinedMonthlyPaxA
        + " model_joined_b=" + result.joinedMonthlyPaxB
        + " model_joined_total=" + result.joinedMonthlyPax
        + " predicted_annual_profit=" + predictedAnnualProfit
        + " predicted_annual_revenue=" + predictedAnnualRevenue
        + " raw_joined_a=" + result.joinedRawMonthlyPaxA
        + " raw_joined_b=" + result.joinedRawMonthlyPaxB
        + " raw_joined_total=" + result.joinedRawMonthlyPax
        + " reuse_a=" + (reuseA ? 1 : 0) + " reuse_b=" + (reuseB ? 1 : 0)
        + " planned_capital=" + result.plannedCapital + " actual_cost=" + result.actualCost
        + " probe_ops=" + probeOps);
  }
  if (V93_AIR_DEMAND_PRODUCTION) OpexAirReconcileActualBuild(catalog, plan, result, lines);
  else OpexAirReconcileActualBuild(catalog, plan, result);
  return result;
}

/* V93.1 : memos du mois, meme horloge que C80 (AIR_MEMO_MONTH / AIR_ECONOMICS_MEMO).
 * Les cles v93t| et v93c| ne collisionnent pas avec les cles d'economie. */
function OpexAirDemandTouchMemo()
{
  local nowDate = AIDate.GetCurrentDate();
  if (nowDate == AIR_DEMAND_MEMO_DATE) return;
  AIR_DEMAND_MEMO_DATE = nowDate;
  local month = AIDate.GetYear(nowDate) * 12 + AIDate.GetMonth(nowDate);
  if (AIR_MEMO_MONTH != month) {
    AIR_ECONOMICS_MEMO = {};
    AIR_TRIP_MEMO = {};
    AIR_MEMO_MONTH = month;
  }
}

/* Cargo passagers du catalogue. Repli : premiere classe CC_PASSENGERS, sans identifiant fixe. */
function OpexAirDemandPaxCargo()
{
  if (AIR_DEMAND_PAX_CARGO >= 0) return AIR_DEMAND_PAX_CARGO;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    if (AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) {
      AIR_DEMAND_PAX_CARGO = c;
      return c;
    }
  }
  return -1;
}

function OpexAirDemandTownRecord(town, paxCargo)
{
  local townId = town.id;
  local key = "v93t|" + townId;
  if (key in AIR_ECONOMICS_MEMO) return AIR_ECONOMICS_MEMO[key];
  if (!AITown.IsValidTown(townId)) return null;
  local pop = ("pop" in town) ? town.pop : AITown.GetPopulation(townId);
  local produced = AITown.GetLastMonthProduction(townId, paxCargo);
  if (pop >= 0 && produced > pop) produced = pop / 8;
  if (produced < 0) produced = 0;
  local transported = AITown.GetLastMonthTransportedPercentage(townId, paxCargo);
  if (transported < 0) transported = 0;
  /* AITile.GetCargoProduction compte des tuiles productrices, pas des passagers :
   * on ne s'en sert que comme proportion (tuiles couvertes par l'aeroport / tuiles
   * productrices de la ville), rayon croissant avec la population. */
  local townRadius = 4 + (sqrt(pop > 0 ? pop : 0) / 8).tointeger();
  if (townRadius > 20) townRadius = 20;
  local producerTiles = AITile.GetCargoProduction(AITown.GetLocation(townId), paxCargo, 1, 1, townRadius);
  if (producerTiles < 0) producerTiles = 0;
  local record = { produced = produced, transported = transported, pop = pop, producerTiles = producerTiles };
  AIR_ECONOMICS_MEMO.rawset(key, record);
  return record;
}

/* Lignes aeriennes Opex qui partent de cette ville (origin = centre-ville) ou de cet
 * aeroport (station = tuile d'aeroport). Le compte est stable tant que la liste ne change
 * pas de longueur : la boucle de paires ne la reparcourt pas. */
function OpexAirDemandOwnLines(town, siteAnchor, lines)
{
  if (lines == null) return 0;
  local nLines = lines.len();
  if (AIR_DEMAND_LINE_MEMO_LEN != nLines) {
    AIR_DEMAND_LINE_MEMO = {};
    AIR_DEMAND_LINE_MEMO_LEN = nLines;
  }
  local townId = ("id" in town) ? town.id : -1;
  local anchorKey = siteAnchor == null ? -1 : siteAnchor;
  local cacheKey = townId + "|" + anchorKey;
  if (cacheKey in AIR_DEMAND_LINE_MEMO) return AIR_DEMAND_LINE_MEMO[cacheKey];
  local townTile = ("tile" in town) ? town.tile : -1;
  local n = 0;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "air") continue;
    local hit = false;
    if (townTile >= 0) {
      if (("originA" in line) && line.originA == townTile) hit = true;
      else if (("originB" in line) && line.originB == townTile) hit = true;
    }
    if (!hit && siteAnchor != null) {
      if (("stationA" in line) && line.stationA == siteAnchor) hit = true;
      else if (("stationB" in line) && line.stationB == siteAnchor) hit = true;
    }
    if (hit) n++;
  }
  AIR_DEMAND_LINE_MEMO.rawset(cacheKey, n);
  return n;
}

/* Type reel si l'ancre est deja un aeroport, sinon le type que l'on s'apprete a poser.
 * -1 dans le memo : ancre encore libre, le type vient de l'argument. */
function OpexAirDemandAirportType(siteAnchor, airport)
{
  if (airport == null || !("type" in airport)) return -1;
  if (siteAnchor == null) return airport.type;
  local key = "v93a|" + siteAnchor;
  if (key in AIR_ECONOMICS_MEMO) {
    local cached = AIR_ECONOMICS_MEMO[key];
    if (cached >= 0) return cached;
    return airport.type;
  }
  local resolved = -1;
  if (AIAirport.IsAirportTile(siteAnchor)) {
    local existing = AIAirport.GetAirportType(siteAnchor);
    if (AIAirport.IsValidAirportType(existing)) resolved = existing;
  }
  AIR_ECONOMICS_MEMO.rawset(key, resolved);
  if (resolved >= 0) return resolved;
  return airport.type;
}

/* -1 si l'ancre est inconnue : pas de borne. Sinon le nombre de tuiles productrices
 * du bassin (GetCargoProduction compte des producteurs), en cache par ancre et par
 * type pour le mois. */
function OpexAirDemandCatchment(siteAnchor, airportType, paxCargo)
{
  if (siteAnchor == null || airportType < 0) return -1;
  local key = "v93c|" + siteAnchor + "|" + airportType + "|" + paxCargo;
  if (key in AIR_ECONOMICS_MEMO) return AIR_ECONOMICS_MEMO[key];
  if (!AIMap.IsValidTile(siteAnchor) || !AIAirport.IsValidAirportType(airportType)) return -1;
  local sum = OpexAirAirportCatchmentProduction(siteAnchor, airportType, paxCargo);
  if (sum < 0) sum = 0;
  AIR_ECONOMICS_MEMO.rawset(key, sum);
  return sum;
}

/* Passagers mensuels d'une extremite. Appele pour les deux bouts quand
 * V93_AIR_DEMAND_PRODUCTION est arme. Sans ligne Opex au depart, la part deja
 * transporte est celle des autres : production * 70 / (pourcentage + 70).
 * Avec des lignes, ce pourcentage melange nos avions : on partage seulement
 * la production par (lignes + 1). Le / (lignes + 1) est toujours applique
 * (il vaut 1 tant qu'aucune ligne ne part). Puis part des tuiles productrices captees, puis
 * plafond de ligne (200, ou 100 sous 700 habitants). */
function OpexAirTownMonthlyPax(town, siteAnchor, airport, lines)
{
  if (town == null || !("id" in town)) return 0;
  local paxCargo = OpexAirDemandPaxCargo();
  if (paxCargo < 0) return 0;
  OpexAirDemandTouchMemo();
  local record = OpexAirDemandTownRecord(town, paxCargo);
  if (record == null) return 0;
  local ownLines = OpexAirDemandOwnLines(town, siteAnchor, lines);
  local pax = record.produced;
  if (ownLines == 0) {
    pax = (record.produced * V93_AIR_COMPETITOR_WEIGHT) / (record.transported + V93_AIR_COMPETITOR_WEIGHT);
  }
  pax = pax / (ownLines + 1);
  /* Part de la ville reellement captee par l'emprise : proportion de ses tuiles
   * productrices dans le rayon de l'aeroport (unite commune, tuiles). */
  local catchment = OpexAirDemandCatchment(siteAnchor, OpexAirDemandAirportType(siteAnchor, airport), paxCargo);
  if (catchment >= 0 && record.producerTiles > 0 && catchment < record.producerTiles) {
    pax = (pax * catchment) / record.producerTiles;
  }
  local cap = V93_AIR_LINE_PAX_CAP;
  if (record.pop >= 0 && record.pop < V93_AIR_LINE_PAX_SMALL_POP) cap = V93_AIR_LINE_PAX_CAP / 2;
  if (pax > cap) pax = cap;
  if (pax < 0) pax = 0;
  return pax;
}
