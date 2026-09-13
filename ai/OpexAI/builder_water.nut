/* Liaison maritime passagers v1 : pas de canal, ecluse ni bouee. */
require("lib_water.nut");

/* WATER_LAKES_CONNECTIVITY : declaree et defaut fixe dans main.nut (pres des autres drapeaux
 * C41_WATER_*), lue depuis le reglage info.nut "water_lakes_connectivity" dans OpexAI::Start().
 * 1 = MinchinWeb.Lakes pour la connectivite (memorisee, sans marge de bounding-box) + distance
 *     Manhattan pour le revenu (corrige le bug de tarification, voir OpexWaterEconomics) et
 *     MinchinWeb.GetDockFrontTiles pour l'acces aux quais (calcul de pente correct au lieu du
 *     scan aveugle des 4 cardinaux).
 * 0 = comportement historique complet (BFS maison pour tout, bug de tarification inclus),
 *     conserve pour A/B. */

WATER_TOWN_POOL <- 12;
/* En mode catalogue, ce n'est plus un filtre des 12 plus grosses villes : c'est la largeur
 * d'une tranche de decouverte. Le curseur persistant avance a chaque portefeuille et les sites
 * trouves dans les tranches precedentes restent disponibles pour les paires. */
WATER_TOWN_DISCOVERY_SLICE <- 12;
WATER_TOWN_MIN_DISTANCE <- 45;
WATER_MAX_SITE_PROBES <- 720;
/* Budget primaire de découverte : tuiles géométriquement inspectées, distinct des AITestMode
 * BuildDock (`WATER_MAX_SITE_PROBES`). Une tranche s'arrête ici et reprend sa ville au tick de
 * portefeuille suivant. */
WATER_MAX_SITE_TILES <- 96;
/* Un premier quai peut être dans le mauvais bassin. Le catalogue conserve plusieurs options
 * géométriques d'une même ville afin que les paires puissent choisir le composant connecté. */
WATER_MAX_SITES_PER_TOWN <- 3;
WATER_MAX_WATER_TILES <- 8;
WATER_MAX_DEPOT_PROBES <- 96;
WATER_BFS_MARGIN <- 24;
WATER_BFS_MAX_NODES <- 12000;
WATER_CAPITAL_MARGIN <- 50000;
WATER_PROJECT_POOL <- 4;

function OpexWaterInMap(x, y)
{
  return x >= 0 && y >= 0 && x < AIMap.GetMapSizeX() && y < AIMap.GetMapSizeY();
}

/* Insertion stable : l'enumeration OpenTTD departage les populations egales. */
function OpexWaterSortedTowns(towns)
{
  local out = [];
  foreach (town in towns) {
    local pos = out.len();
    while (pos > 0 && out[pos - 1].pop < town.pop) pos--;
    out.insert(pos, town);
  }
  return out;
}
function OpexWaterTownServed(town, lines)
{
  if (lines == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "water") continue;
    if (AIMap.DistanceManhattan(town.tile, line.originA) < 15) return true;
    if (AIMap.DistanceManhattan(town.tile, line.originB) < 15) return true;
  }
  return false;
}

/* Une tuile navigable a une vraie arete navigable ; aucun AIWaterTile n'est utilise. */
function OpexWaterIsNavigable(tile)
{
  if (!AITile.IsWaterTile(tile)) return false;
  local x = AIMap.GetTileX(tile);
  local y = AIMap.GetTileY(tile);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (offset in offsets) {
    local nx = x + offset[0];
    local ny = y + offset[1];
    if (!OpexWaterInMap(nx, ny)) continue;
    local next = AIMap.GetTileIndex(nx, ny);
    if (AITile.IsWaterTile(next) && AIMarine.AreWaterTilesConnected(tile, next)) return true;
  }
  return false;
}

function OpexWaterAdjacentTiles(dock)
{
  local out = [];
  local x = AIMap.GetTileX(dock);
  local y = AIMap.GetTileY(dock);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (offset in offsets) {
    if (out.len() >= WATER_MAX_WATER_TILES) break;
    local nx = x + offset[0];
    local ny = y + offset[1];
    if (!OpexWaterInMap(nx, ny)) continue;
    local water = AIMap.GetTileIndex(nx, ny);
    if (OpexWaterIsNavigable(water)) out.append(water);
  }
  return out;
}

/* Fronts que le quai projeté exposera réellement. GetDockFrontTiles est valable avant la
 * construction ; il lit la pente du terrain. Le filtre navigable conserve le contrat des BFS
 * et de Lakes, sans accepter une simple case d'eau isolée. */
function OpexWaterDiscoveryFronts(dock)
{
  if (!WATER_DISCOVERY_REAL_FRONTS) return OpexWaterAdjacentTiles(dock);
  local out = [];
  foreach (front in _MinchinWeb_Marine_.GetDockFrontTiles(dock)) {
    if (out.len() >= WATER_MAX_WATER_TILES) break;
    if (!OpexWaterIsNavigable(front)) continue;
    local duplicate = false;
    foreach (known in out) if (known == front) duplicate = true;
    if (!duplicate) out.append(front);
  }
  return out;
}

/* Acces reel : land et waterPart sont des tuiles de station. Les fronts sont toutes les cases eau
 * cardinales autour de waterPart, sauf land ; aucun test de connectivite ne relie station et eau. */
function OpexWaterFindDockAccess(land)
{
  if (!AIMarine.IsDockTile(land)) return null;
  local station = AIStation.GetStationID(land);
  if (!AIStation.IsValidStation(station)) return null;
  local x = AIMap.GetTileX(land);
  local y = AIMap.GetTileY(land);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (offset in offsets) {
    local px = x + offset[0];
    local py = y + offset[1];
    if (!OpexWaterInMap(px, py)) continue;
    local waterPart = AIMap.GetTileIndex(px, py);
    if (!AIMarine.IsDockTile(waterPart)) continue;
    if (AIStation.GetStationID(waterPart) != station) continue;
    local fronts = [];
    foreach (side in offsets) {
      local fx = px + side[0];
      local fy = py + side[1];
      if (!OpexWaterInMap(fx, fy) || (fx == x && fy == y)) continue;
      local front = AIMap.GetTileIndex(fx, fy);
      if (!AITile.IsWaterTile(front) ||
          !AITile.HasTransportType(front, AITile.TRANSPORT_WATER)) continue;
      local navigable = false;
      foreach (near in offsets) {
        local qx = fx + near[0];
        local qy = fy + near[1];
        if (!OpexWaterInMap(qx, qy) || (qx == px && qy == py)) continue;
        local q = AIMap.GetTileIndex(qx, qy);
        if (AITile.IsWaterTile(q) && AIMarine.AreWaterTilesConnected(front, q)) {
          navigable = true;
          break;
        }
      }
      if (!navigable) continue;
      local duplicate = false;
      foreach (known in fronts) if (known == front) duplicate = true;
      if (!duplicate) fronts.append(front);
    }
    if (fronts.len() > 0) return { waterPart = waterPart, fronts = fronts };
  }
  return null;
}

/* Bascule sur le calcul de pente de MinchinWeb.GetDockFrontTiles (lib_water.nut) plutot que le
 * scan aveugle des 4 cardinaux de OpexWaterFindDockAccess -- une gare exige une pente cotiere
 * orientee vers l'eau, GetDockFrontTiles la derive de AITile.GetSlope(land) au lieu de la
 * deviner. Seul `.fronts` du retour de OpexWaterFindDockAccess est utilise par les appelants
 * (verifie) : la forme de retour ({fronts=[...]}) reste donc compatible sans adapter les
 * appelants. `waterPart` n'a jamais ete lu ailleurs, absent du chemin neuf. */
function OpexWaterDockAccess(land)
{
  if (WATER_LAKES_CONNECTIVITY) {
    local fronts = _MinchinWeb_Marine_.GetDockFrontTiles(land);
    if (fronts.len() == 0) return null;
    return { fronts = fronts };
  }
  return OpexWaterFindDockAccess(land);
}

/* Les probes sont partagees equitablement : une cote sans dock ne mange pas tout le budget.
 * `complete` est indispensable au catalogue persistant : une ville interrompue par le budget
 * n'est pas une ville sans quai. */
function OpexWaterFindSiteLegacy(town, probes, profile = null)
{
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_DOCK);
  local allowance = probes.townsLeft > 0
      ? (probes.left + probes.townsLeft - 1) / probes.townsLeft : 0;
  probes.townsLeft--;
  local used = 0;
  local tx = AIMap.GetTileX(town.tile);
  local ty = AIMap.GetTileY(town.tile);
  for (local r = 0; r <= coverage; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local x = tx + dx;
        local y = ty + dy;
        if (!OpexWaterInMap(x, y)) continue;
        local dock = AIMap.GetTileIndex(x, y);
        if (!AITile.IsCoastTile(dock)) continue;
        if (profile != null) profile.coast_candidates++;
        if (AIMap.DistanceManhattan(town.tile, dock) > coverage) continue;
        local waterTiles = OpexWaterDiscoveryFronts(dock);
        if (waterTiles.len() == 0) continue;
        if (profile != null) profile.navigable_coast_candidates++;
        if (used >= allowance || probes.left <= 0) return { site = null, complete = false };
        local ok = false;
        local testMark = profile != null ? OpexOpsMeasureBegin() : null;
        { local probe = AITestMode(); ok = AIMarine.BuildDock(dock, AIStation.STATION_NEW); }
        if (profile != null) {
          profile.dock_test_ops += OpexOpsMeasureEnd(testMark);
          profile.dock_tests++;
        }
        used++;
        probes.left--;
        if (ok) return { site = { town = town, dock = dock, waterTiles = waterTiles }, complete = true };
      }
    }
  }
  return { site = null, complete = true };
}

/* Découverte reprise au tile près. Le losange est énuméré directement : une tuile hors du
 * catchment ne peut donc jamais atteindre IsCoastTile. `scan` est sérialisable et ne contient
 * que la position dans le losange. */
function OpexWaterFindSiteSlice(town, probes, scan, slots, profile = null)
{
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_DOCK);
  local tx = AIMap.GetTileX(town.tile);
  local ty = AIMap.GetTileY(town.tile);
  local visited = 0;
  local sites = [];
  while (scan.r <= coverage && visited < WATER_MAX_SITE_TILES && sites.len() < slots) {
    local dy = scan.r - abs(scan.dx);
    local signedDy = scan.side == 0 ? dy : -dy;
    local x = tx + scan.dx;
    local y = ty + signedDy;
    /* Avancer avant les appels API : tout retour par budget reprend à la tuile suivante sans
     * rebalayer les filtres déjà payés. */
    if (dy != 0 && scan.side == 0) {
      scan.side = 1;
    } else {
      scan.side = 0;
      scan.dx++;
      if (scan.dx > scan.r) { scan.r++; scan.dx = -scan.r; }
    }
    if (!OpexWaterInMap(x, y)) continue;
    visited++;
    if (profile != null) profile.site_tiles_visited++;
    local dock = AIMap.GetTileIndex(x, y);
    if (!AITile.IsCoastTile(dock)) continue;
    if (profile != null) profile.coast_candidates++;
    local waterTiles = OpexWaterDiscoveryFronts(dock);
    if (waterTiles.len() == 0) continue;
    if (profile != null) profile.navigable_coast_candidates++;
    if (probes.left <= 0) return { sites = sites, complete = false, scan = scan };
    local ok = false;
    local testMark = profile != null ? OpexOpsMeasureBegin() : null;
    { local probe = AITestMode(); ok = AIMarine.BuildDock(dock, AIStation.STATION_NEW); }
    if (profile != null) {
      profile.dock_test_ops += OpexOpsMeasureEnd(testMark);
      profile.dock_tests++;
    }
    probes.left--;
    if (ok) sites.append({ town = town, dock = dock, waterTiles = waterTiles });
  }
  return { sites = sites, complete = scan.r > coverage || sites.len() >= slots, scan = scan };
}

/* Le littoral ne depend ni des moteurs ni de l'economie. Ce catalogue, possede par OpexAI et
 * persiste dans Save(), evite donc de repayer le scan a chaque reconstruction mensuelle. On ne
 * memorise un negatif que si toute la zone de couverture a ete parcourue ; sinon le budget de
 * probes reprend legitimement la recherche lors d'une passe ulterieure. Les objets `town` eux-
 * memes sont recrees par catalog.nut : le cache ne conserve que la geometrie stable. */
function OpexWaterCatalogSites(town, siteCatalog, probes, profile = null)
{
  if (siteCatalog == null) {
    local legacy = OpexWaterFindSiteLegacy(town, probes, profile);
    return legacy.site != null ? [legacy.site] : [];
  }
  if (town.id in siteCatalog.towns && ("complete" in siteCatalog.towns[town.id])
      && siteCatalog.towns[town.id].complete) {
    if (profile != null) profile.site_cache_hits++;
    local saved = siteCatalog.towns[town.id];
    local out = [];
    foreach (entry in saved.sites) {
      out.append({ town = town, dock = entry.dock, waterTiles = entry.waterTiles });
    }
    return out;
  }

  if (profile != null) profile.site_cache_misses++;
  local saved = (town.id in siteCatalog.towns) ? siteCatalog.towns[town.id]
      : { sites = [], complete = false, scan = { r = 0, dx = 0, side = 0 } };
  /* Migration des sauvegardes du premier prototype de cache, qui ne portait pas de curseur. */
  if (!("complete" in saved)) saved.complete <- saved.sites.len() > 0;
  if (!("scan" in saved)) saved.scan <- { r = 0, dx = 0, side = 0 };
  local slots = WATER_MAX_SITES_PER_TOWN - saved.sites.len();
  if (slots <= 0) { saved.complete = true; return []; }
  local found = OpexWaterFindSiteSlice(town, probes, saved.scan, slots,
                                        C41_WATER_SITE_PROFILE ? profile : null);
  saved.scan = found.scan;
  local sites = [];
  foreach (site in found.sites) {
    sites.append(site);
    saved.sites.append({ dock = site.dock, waterTiles = site.waterTiles });
  }
  if (found.complete || saved.sites.len() >= WATER_MAX_SITES_PER_TOWN) {
    /* Une entrée vide n'est négative qu'après le losange entier. */
    saved.complete = true;
  }
  siteCatalog.towns.rawset(town.id, saved);
  return sites;
}

/* Tous les sites positifs deja trouves participent aux paires. Les objets ville sont toujours
 * ceux du catalogue courant : aucune reference perimee n'est conservee dans la sauvegarde. */
function OpexWaterCatalogKnownSites(towns, lines, siteCatalog)
{
  local sites = [];
  if (siteCatalog == null) return sites;
  foreach (town in towns) {
    if (OpexWaterTownServed(town, lines) || !(town.id in siteCatalog.towns)) continue;
    foreach (entry in siteCatalog.towns[town.id].sites) {
      sites.append({ town = town, dock = entry.dock, waterTiles = entry.waterTiles });
    }
  }
  return sites;
}

function OpexWaterContains(tiles, tile)
{
  foreach (entry in tiles) if (entry == tile) return true;
  return false;
}

/* La portee est filtree avant le BFS ; le depot ne sera sonde qu apres les docks reels. */
function OpexWaterHasRange(catalog, orderDistance)
{
  foreach (ship in catalog.ships) {
    if (ship.maxOrderDistance <= 0 || orderDistance <= ship.maxOrderDistance) return true;
  }
  return false;
}

/* BFS 4 voisins avec rectangle x/y explicite. Retourne la longueur navigable minimale en
 * tuiles d'eau, ou -1 si les deux acces ne sont pas connectes dans le budget borne. */
function OpexWaterFindConnection(siteA, siteB)
{
  local ax = AIMap.GetTileX(siteA.dock);
  local ay = AIMap.GetTileY(siteA.dock);
  local bx = AIMap.GetTileX(siteB.dock);
  local by = AIMap.GetTileY(siteB.dock);
  local minX = max(0, min(ax, bx) - WATER_BFS_MARGIN);
  local minY = max(0, min(ay, by) - WATER_BFS_MARGIN);
  local maxX = min(AIMap.GetMapSizeX() - 1, max(ax, bx) + WATER_BFS_MARGIN);
  local maxY = min(AIMap.GetMapSizeY() - 1, max(ay, by) + WATER_BFS_MARGIN);
  local queue = [];
  local seen = {};
  foreach (water in siteA.waterTiles) { queue.append(water); seen.rawset(water, 0); }
  local head = 0;
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < queue.len() && head < WATER_BFS_MAX_NODES) {
    local current = queue[head++];
    local distance = seen[current];
    if (OpexWaterContains(siteB.waterTiles, current)) return distance;
    local x = AIMap.GetTileX(current);
    local y = AIMap.GetTileY(current);
    foreach (offset in offsets) {
      local nx = x + offset[0];
      local ny = y + offset[1];
      if (nx < minX || nx > maxX || ny < minY || ny > maxY) continue;
      local next = AIMap.GetTileIndex(nx, ny);
      if (!AITile.IsWaterTile(next)) continue;
      if (!AIMarine.AreWaterTilesConnected(current, next)) continue;
      if (!(next in seen)) { seen.rawset(next, distance + 1); queue.append(next); }
    }
  }
  return -1;
}

/* Le depot est cherche apres la pose des docks, dans le composant deja prouve. AITestMode voit
 * donc les empreintes effectivement occupees par les docks. */
function OpexWaterFindDepot(siteA, siteB)
{
  local ax = AIMap.GetTileX(siteA.dock);
  local ay = AIMap.GetTileY(siteA.dock);
  local bx = AIMap.GetTileX(siteB.dock);
  local by = AIMap.GetTileY(siteB.dock);
  local minX = max(0, min(ax, bx) - WATER_BFS_MARGIN);
  local minY = max(0, min(ay, by) - WATER_BFS_MARGIN);
  local maxX = min(AIMap.GetMapSizeX() - 1, max(ax, bx) + WATER_BFS_MARGIN);
  local maxY = min(AIMap.GetMapSizeY() - 1, max(ay, by) + WATER_BFS_MARGIN);
  local queue = [];
  local seen = {};
  foreach (water in siteA.waterTiles) { queue.append(water); seen.rawset(water, true); }
  local head = 0;
  local probes = 0;
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < queue.len() && head < WATER_BFS_MAX_NODES && probes < WATER_MAX_DEPOT_PROBES) {
    local current = queue[head++];
    local x = AIMap.GetTileX(current);
    local y = AIMap.GetTileY(current);
    foreach (offset in offsets) {
      if (probes >= WATER_MAX_DEPOT_PROBES) break;
      local nx = x + offset[0];
      local ny = y + offset[1];
      if (nx < minX || nx > maxX || ny < minY || ny > maxY) continue;
      local next = AIMap.GetTileIndex(nx, ny);
      if (!AITile.IsWaterTile(next) || !AIMarine.AreWaterTilesConnected(current, next)) continue;
      local depotOk = false;
      { local probe = AITestMode(); depotOk = AIMarine.BuildWaterDepot(current, next); }
      probes++;
      if (depotOk) return { tile = current, front = next };
      if (!(next in seen)) { seen.rawset(next, true); queue.append(next); }
    }
  }
  return null;
}

/* Economie maritime avant construction. La capacite du catalogue est une approximation de refit,
 * comme pour la route ; le constructeur relit la capacite exacte dans le depot. */
/* `navigableDistance` (tuiles d'eau reellement parcourues, ex-BFS/desormais Lakes+BFS reduit)
 * sert au temps de trajet -- un detour cotier doit rester lent. `tariffDistance` (Manhattan
 * entre les deux quais) sert UNIQUEMENT au revenu : le jeu paie sur la distance a vol d'oiseau
 * entre stations, jamais sur la distance parcourue (bug corrige le 2026-09-09, voir
 * docs/taches.md -- avant ce correctif, `AICargo.GetCargoIncome` etait appele avec la distance
 * navigable, surpayant systematiquement les routes maritimes sinueuses). */
function OpexWaterEconomics(catalog, navigableDistance, tariffDistance, orderDistance, monthlyPax)
{
  local best = null;
  foreach (ship in catalog.ships) {
    if (ship.capacity <= 0 || ship.speed <= 0) continue;
    if (ship.maxOrderDistance > 0 && orderDistance > ship.maxOrderDistance) continue;
    local effectiveSpeed = ship.speed / 2;
    if (effectiveSpeed < 1) effectiveSpeed = 1;
    local oneWayDays = (navigableDistance * 1000) / (36 * effectiveSpeed);
    if (oneWayDays < 1) oneWayDays = 1;
    local roundTripDays = 2 * oneWayDays;
    local headwayDays = roundTripDays;
    /* Division entiere Squirrel corrigee (bug 2026-09-09) : un aller simple de 35 jours donnait
     * 30/35 = 0, force a 1, ce qui triplait la capacite transportee sur les longs trajets. */
    local tripsPerMonth = 30.0 / oneWayDays.tofloat();
    if (tripsPerMonth < 1.0) tripsPerMonth = 1.0;
    local stationRating = OpexStationRatingForHeadway(headwayDays);
    local offered = (monthlyPax * stationRating) / 100;
    local monthlyCapacity = (ship.capacity * tripsPerMonth).tointeger();
    local carried = offered < monthlyCapacity ? offered : monthlyCapacity;
    local income = AICargo.GetCargoIncome(catalog.paxCargo, tariffDistance, oneWayDays);
    local revenueAnnual = 12 * carried * income;
    local infraCapital = 2 * catalog.costDock + catalog.costWaterDepot;
    local capital = infraCapital + ship.price;
    local runningAnnual = ship.runningCost;
    local amortAnnual = ((infraCapital * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS) + ship.price / 20;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    local immobilise = (TRANSIT_COST_PERMILLE > 0)
        ? (revenueAnnual * roundTripDays * TRANSIT_COST_PERMILLE) / 365000 : 0;
    local totalCapital = capital + immobilise;
    local roi = (profitAnnual > 0 && totalCapital > 0)
        ? (profitAnnual * 1000) / totalCapital : 0;
    local economics = {
      ship = ship, oneWayDays = oneWayDays, roundTripDays = roundTripDays,
      headwayDays = headwayDays, stationRating = stationRating,
      carried = carried,
      revenueAnnual = revenueAnnual, runningAnnual = runningAnnual,
      amortAnnual = amortAnnual, profitAnnual = profitAnnual,
      capital = capital, immobilise = immobilise, roi = roi,
    };
    if (best == null || economics.roi > best.roi ||
        (economics.roi == best.roi && economics.profitAnnual > best.profitAnnual)) {
      best = economics;
    }
  }
  return best;
}

function OpexWaterPlans(catalog, lines = null, projects = null, profile = null, siteCatalog = null)
{
  if (catalog.ships.len() == 0 || catalog.paxCargo < 0) return null;
  local mark = profile != null ? OpexOpsMeasureBegin() : null;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "water_town_sort", "-");
  local towns = OpexWaterSortedTowns(catalog.towns);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "water_town_sort", "-");
  if (profile != null) profile.town_sort_ops = OpexOpsMeasureEnd(mark);
  local historical = siteCatalog == null;
  local limit = towns.len() < (historical ? WATER_TOWN_POOL : WATER_TOWN_DISCOVERY_SLICE)
      ? towns.len() : (historical ? WATER_TOWN_POOL : WATER_TOWN_DISCOVERY_SLICE);
  local sites = historical ? [] : OpexWaterCatalogKnownSites(towns, lines, siteCatalog);
  local probes = { left = WATER_MAX_SITE_PROBES, townsLeft = limit };
  mark = profile != null ? OpexOpsMeasureBegin() : null;
  local start = 0;
  if (!historical && towns.len() > 0 && ("cursor" in siteCatalog)) {
    start = siteCatalog.cursor % towns.len();
  }
  local c56TownsScanned = 0;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "water_site_scan", "-");
  for (local step = 0; step < limit; step++) {
    if (C56_TASK_TRACE) c56TownsScanned++;
    local i = historical ? step : (start + step) % towns.len();
    if (profile != null) profile.towns_considered++;
    if (OpexWaterTownServed(towns[i], lines)) continue;
    local wasKnownComplete = !historical && (towns[i].id in siteCatalog.towns)
        && siteCatalog.towns[towns[i].id].complete;
    local townSites = OpexWaterCatalogSites(towns[i], siteCatalog, probes,
                                             C41_WATER_SITE_PROFILE ? profile : null);
    /* Une entree deja connue est deja dans `sites`; ne pas la dupliquer. */
    if (historical || !wasKnownComplete) foreach (site in townSites) sites.append(site);
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "water_site_scan",
                                      "- towns=" + c56TownsScanned);
  if (!historical && towns.len() > 0) siteCatalog.cursor <- (start + limit) % towns.len();
  if (profile != null) {
    profile.site_ops = OpexOpsMeasureEnd(mark);
    profile.site_scan_filter_ops = profile.site_ops - profile.dock_test_ops;
    profile.sites_found = sites.len();
    /* Champs neufs (2026-09-09) : main.nut construit la table `profile` avec un ensemble figé
     * de cles a zero (isolation en cours, ce fichier ne peut pas y ajouter les siennes) --
     * on les cree ici au besoin, avant tout `=`/`+=` dessus dans lib_water.nut, sinon
     * "the index 'lakes_init_ops' does not exist" au premier profilage. */
    if (!("lakes_init_ops" in profile)) {
      profile.lakes_init_ops <- 0;
      profile.lakes_query_ops <- 0;
      profile.lakes_queries <- 0;
      profile.lakes_connected <- 0;
      profile.lakes_fallback_navigable <- 0;
      /* Calibration de WATER_LAKES_ITERATIONS (2026-09-09) : combien d'iterations reelles
       * FindPath consomme, ventile par issue -- un budget correctement dimensionne doit
       * couvrir le max des cas "connecte" sans jamais approcher "exhausted". */
      profile.lakes_iterations_connected_sum <- 0;
      profile.lakes_iterations_connected_n <- 0;
      profile.lakes_iterations_connected_max <- 0;
      profile.lakes_iterations_no_path_sum <- 0;
      profile.lakes_iterations_no_path_n <- 0;
      profile.lakes_iterations_no_path_max <- 0;
      profile.lakes_iterations_exhausted_n <- 0;
    }
    mark = OpexOpsMeasureBegin();
  }
  /* G11 : le BFS sert aussi a l'economie. Le limiter apres un classement Manhattan pouvait
   * elire un detour cotier comme s'il etait direct et ecarter une paire reellement meilleure.
   * Le bassin est deja borne par WATER_TOWN_POOL ; chaque paire admissible est donc chiffree
   * avec sa longueur navigable avant son classement. */
  local ranked = [];
  local c56PairsExamined = 0;
  local c56LakesIn = 0;
  local c56LakesOut = 0;
  local c56BfsIn = 0;
  local c56BfsOut = 0;
  /* Si lakes_in > lakes_out, le gel est dans MinchinWeb ; si bfs_in > bfs_out,
   * il est dans le BFS maison. */
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "water_pair_loop", "-");
  for (local a = 0; a < sites.len(); a++) {
    for (local b = a + 1; b < sites.len(); b++) {
      /* Intervalle ramene de 500 a 10 le 2026-09-11 : a 500, la ligne n'etait JAMAIS atteinte
       * avant le gel, et la sonde restait muette sur le cas meme qu'elle devait diagnostiquer.
       * Un appel sain examine 0 paire (moins de deux sites), donc ce pas fin ne coute rien. */
      if (C56_TASK_TRACE) {
        c56PairsExamined++;
        if (c56PairsExamined % 10 == 0) {
          OpexC56TaskLog("WATER_PROBE_COUNTERS", "water_probe_counters",
                         "- pairs=" + c56PairsExamined + " lakes_in=" + c56LakesIn
                         + " lakes_out=" + c56LakesOut + " bfs_in=" + c56BfsIn
                         + " bfs_out=" + c56BfsOut);
        }
      }
      if (profile != null) profile.pairs_considered++;
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
      if (distance < WATER_TOWN_MIN_DISTANCE) continue;
      local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_WATER,
                                                      sites[a].dock, sites[b].dock);
      if (orderDistance < 0 || !OpexWaterHasRange(catalog, orderDistance)) continue;
      if (profile != null) profile.pairs_after_range++;
      local monthlyPax = ((sites[a].town.pop + sites[b].town.pop) * 22) / 100;

      /* Distance TARIFAIRE (Manhattan entre quais, pas entre centres-villes) : corrige
       * inconditionnellement (bug independant du choix Lakes/BFS ci-dessous), voir
       * OpexWaterEconomics. */
      local tariffDistance = AIMap.DistanceManhattan(sites[a].dock, sites[b].dock);
      local navigableDistance = -1;

      if (WATER_LAKES_CONNECTIVITY) {
        /* Etage 1 : connectivite memorisee par bassin (MinchinWeb.Lakes), sans marge de
         * bounding-box -- une paire au-dela de l'ancien WATER_BFS_MARGIN=24 n'est plus ecartee
         * a tort. Instance persistante pour toute la partie (voir lib_water.nut). */
        /* Jalon a CHAQUE paire, pas a intervalle : quand le gel coupe le journal, seule la
         * DERNIERE ligne ecrite nomme l'etage fautif. Un compteur periodique ne dit rien de la
         * paire en cours -- c'est l'erreur payee au premier essai. */
        if (C56_TASK_TRACE) { c56LakesIn++; OpexC56TaskLog("PAIR", "lakes_enter", "- pair=" + c56PairsExamined); }
        local connected = OpexWaterLakesConnected(sites[a].waterTiles, sites[b].waterTiles, profile);
        if (C56_TASK_TRACE) { c56LakesOut++; OpexC56TaskLog("PAIR", "lakes_exit", "- pair=" + c56PairsExamined); }
        if (connected != true) continue;
        if (profile != null) profile.lakes_connected++;
        /* Etage 2 : la paire est deja confirmee connectee -- ce BFS ne sert plus qu'a chiffrer
         * la distance navigable reelle pour le temps de trajet ; sa marge fixe WATER_BFS_MARGIN
         * n'est plus un point de defaillance de connectivite, seulement un plafond de precision
         * sur la mesure. */
        local bfsMark = profile != null ? OpexOpsMeasureBegin() : null;
        if (C56_TASK_TRACE) { c56BfsIn++; OpexC56TaskLog("PAIR", "bfs_enter", "- pair=" + c56PairsExamined); }
        navigableDistance = OpexWaterFindConnection(sites[a], sites[b]);
        if (C56_TASK_TRACE) { c56BfsOut++; OpexC56TaskLog("PAIR", "bfs_exit", "- pair=" + c56PairsExamined); }
        if (profile != null) {
          profile.bfs_ops += OpexOpsMeasureEnd(bfsMark);
          profile.bfs_attempts++;
        }
        if (navigableDistance < 0) {
          /* Rare : Lakes prouve la connexion (recherche non bornee geographiquement) mais le
           * BFS borne n'a pas trouve le chemin dans sa fenetre WATER_BFS_MARGIN/WATER_BFS_MAX_NODES.
           * Repli conservateur : la distance tarifaire (Manhattan, toujours <= la distance
           * navigable reelle) sert de plancher plutot que d'abandonner une paire deja
           * confirmee viable et deja payee en sondage de sites. */
          navigableDistance = tariffDistance;
          if (profile != null) profile.lakes_fallback_navigable++;
        } else if (profile != null) {
          profile.bfs_connected++;
        }
      } else {
        /* Comportement historique : un seul BFS fait connectivite ET distance, les deux
         * bornees par WATER_BFS_MARGIN. */
        local bfsMark = profile != null ? OpexOpsMeasureBegin() : null;
        if (C56_TASK_TRACE) { c56BfsIn++; OpexC56TaskLog("PAIR", "bfs_enter", "- pair=" + c56PairsExamined); }
        navigableDistance = OpexWaterFindConnection(sites[a], sites[b]);
        if (C56_TASK_TRACE) { c56BfsOut++; OpexC56TaskLog("PAIR", "bfs_exit", "- pair=" + c56PairsExamined); }
        if (profile != null) {
          profile.bfs_ops += OpexOpsMeasureEnd(bfsMark);
          profile.bfs_attempts++;
        }
        if (navigableDistance < 0) continue;
        if (profile != null) profile.bfs_connected++;
      }

      local economicsMark = profile != null ? OpexOpsMeasureBegin() : null;
      local economics = OpexWaterEconomics(catalog, navigableDistance, tariffDistance,
                                            orderDistance, monthlyPax);
      if (profile != null) {
        profile.economics_ops += OpexOpsMeasureEnd(economicsMark);
        profile.economics_attempts++;
      }
      if (economics == null || economics.profitAnnual <= 0) continue;
      if (profile != null) profile.positive_economics++;
      local plan = { siteA = sites[a], siteB = sites[b], distance = navigableDistance,
                     tariffDistance = tariffDistance,
                     orderDistance = orderDistance, economics = economics };
      local pos = ranked.len();
      while (pos > 0 && (ranked[pos - 1].economics.roi < economics.roi ||
             (ranked[pos - 1].economics.roi == economics.roi &&
              ranked[pos - 1].economics.profitAnnual < economics.profitAnnual))) pos--;
      ranked.insert(pos, plan);
      if (ranked.len() > WATER_PROJECT_POOL) ranked.pop();
    }
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "water_pair_loop",
                                      "- pairs=" + c56PairsExamined);
  if (profile != null) {
    profile.pair_total_ops = OpexOpsMeasureEnd(mark);
    profile.pair_filter_rank_ops = profile.pair_total_ops - profile.bfs_ops - profile.economics_ops;
  }
  local best = null;
  foreach (plan in ranked) {
    if (projects != null) projects.append(plan);
    if (best == null) best = plan;
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("WATER_PROBE_COUNTERS", "water_probe_counters",
                                      "- pairs=" + c56PairsExamined + " lakes_in=" + c56LakesIn
                                      + " lakes_out=" + c56LakesOut + " bfs_in=" + c56BfsIn
                                      + " bfs_out=" + c56BfsOut);
  return best;
}

function OpexWaterRollback(dockA, dockB, depot, ship)
{
  if (ship != null && AIVehicle.IsValidVehicle(ship)) AIVehicle.SellVehicle(ship);
  if (depot != null && AIMarine.IsWaterDepotTile(depot)) AIMarine.RemoveWaterDepot(depot);
  if (dockB != null && AIMarine.IsDockTile(dockB)) AIMarine.RemoveDock(dockB);
  if (dockA != null && AIMarine.IsDockTile(dockA)) AIMarine.RemoveDock(dockA);
}

function OpexWaterStampCost(result, costs)
{
  result.actualCost = (costs != null) ? costs.GetCosts() : 0;
  return result;
}

function OpexWaterPlannedCapital(catalog, plan)
{
  local shipPrice = catalog.maxShipPrice;
  if (("economics" in plan) && plan.economics != null && ("ship" in plan.economics)
      && plan.economics.ship != null && ("price" in plan.economics.ship)) {
    shipPrice = plan.economics.ship.price;
  }
  return 2 * catalog.costDock + catalog.costWaterDepot + shipPrice;
}

/* Chaque retour ferme le budget ouvert et retourne une table. */
function OpexBuildWaterRoute(catalog, budget, plan)
{
  local result = { ok = false, reason = "", opcodes = 0, error = 0, dockA = null,
                   dockB = null, stationA = null, stationB = null, depot = null, vehicle = null,
                   actualCost = 0, plannedCapital = OpexWaterPlannedCapital(catalog, plan) };
  local costs = AIAccounting();
  local dockA = null;
  local dockB = null;
  local depot = null;
  local ship = null;
  budget.begin();
  local okA = AIMarine.BuildDock(plan.siteA.dock, AIStation.STATION_NEW);
  local errorA = okA ? 0 : AIError.GetLastError();
  if (okA && AIMarine.IsDockTile(plan.siteA.dock)) dockA = plan.siteA.dock;
  if (dockA == null) {
    result.error = errorA; result.opcodes += budget.end("build_docks"); result.reason = "ADOCK";
    return OpexWaterStampCost(result, costs);
  }
  local okB = AIMarine.BuildDock(plan.siteB.dock, AIStation.STATION_NEW);
  local errorB = okB ? 0 : AIError.GetLastError();
  if (okB && AIMarine.IsDockTile(plan.siteB.dock)) dockB = plan.siteB.dock;
  result.opcodes += budget.end("build_docks");
  if (dockB == null) {
    result.error = errorB; OpexWaterRollback(dockA, null, null, null); result.reason = "BDOCK";
    return OpexWaterStampCost(result, costs);
  }
  local stationA = AIStation.GetStationID(dockA);
  local stationB = AIStation.GetStationID(dockB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) || stationA == stationB) {
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "STATION"; return OpexWaterStampCost(result, costs);
  }

  local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_WATER, dockA, dockB);
  if (orderDistance < 0 || !OpexWaterHasRange(catalog, orderDistance)) {
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "RANGE"; return OpexWaterStampCost(result, costs);
  }

  /* Les fronts et leur composant sont relus apres les constructions reelles. */
  budget.begin();
  local accessA = OpexWaterDockAccess(dockA);
  local accessB = OpexWaterDockAccess(dockB);
  if (accessA == null || accessB == null) {
    result.opcodes += budget.end("build_water_depot");
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "NOWATER"; return OpexWaterStampCost(result, costs);
  }
  local realA = { dock = dockA, waterTiles = accessA.fronts };
  local realB = { dock = dockB, waterTiles = accessB.fronts };
  /* Volontairement laisse sur le BFS existant, pas OpexWaterLakesConnected : ici on reverifie
   * la geometrie EXACTE des quais reellement construits (fronts issus de la pente reelle),
   * pas seulement les tuiles de quai deja validees par Lakes en amont -- les deux docks sont
   * les memes tuiles que celles interrogees au tri des paires, donc une nouvelle requete Lakes
   * ne ferait qu'un hit de cache sans rien verifier de neuf ici. */
  if (OpexWaterFindConnection(realA, realB) < 0) {
    result.opcodes += budget.end("build_water_depot");
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "NOWATER"; return OpexWaterStampCost(result, costs);
  }
  local depotPlan = OpexWaterFindDepot(realA, realB);
  if (depotPlan == null) {
    result.opcodes += budget.end("build_water_depot");
    OpexWaterRollback(dockA, dockB, null, null); result.reason = "NOWATER"; return OpexWaterStampCost(result, costs);
  }
  local depotOk = AIMarine.BuildWaterDepot(depotPlan.tile, depotPlan.front);
  local depotError = depotOk ? 0 : AIError.GetLastError();
  if (depotOk && AIMarine.IsWaterDepotTile(depotPlan.tile)) depot = depotPlan.tile;
  result.opcodes += budget.end("build_water_depot");
  if (depot == null) {
    result.error = depotError; OpexWaterRollback(dockA, dockB, null, null); result.reason = "DEPOT";
    return OpexWaterStampCost(result, costs);
  }

  budget.begin();
  /* G7§4 : utiliser le navire elu par OpexWaterEconomics (meilleur ROI), pas le plus gros.
   * L'ancien code choisissait par capacite maximale, ce qui pouvait elire un navire lent
   * et cher dont le ROI n'avait jamais ete chiffre par le portefeuille. On valide la
   * capacite reelle de refit dans le depot et on retombe sur le scan uniquement en echec. */
  local chosen = null;
  local chosenCapacity = 0;
  if (("economics" in plan) && plan.economics != null && ("ship" in plan.economics)) {
    local elected = plan.economics.ship;
    if (elected.maxOrderDistance <= 0 || orderDistance <= elected.maxOrderDistance) {
      local cap = AIVehicle.GetBuildWithRefitCapacity(depot, elected.id, catalog.paxCargo);
      if (cap > 0) {
        chosen = elected;
        chosenCapacity = cap;
      }
    }
  }
  if (chosen == null) {
    foreach (candidate in catalog.ships) {
      if (candidate.maxOrderDistance > 0 && orderDistance > candidate.maxOrderDistance) continue;
      local capacity = AIVehicle.GetBuildWithRefitCapacity(depot, candidate.id, catalog.paxCargo);
      if (capacity > chosenCapacity ||
          (capacity == chosenCapacity && capacity > 0 &&
           (chosen == null || candidate.speed > chosen.speed ||
            (candidate.speed == chosen.speed && candidate.price < chosen.price)))) {
        chosen = candidate;
        chosenCapacity = capacity;
      }
    }
  }
  if (chosen == null || chosenCapacity <= 0) {
    result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, null); result.reason = "REFIT"; return OpexWaterStampCost(result, costs);
  }
  ship = AIVehicle.BuildVehicleWithRefit(depot, chosen.id, catalog.paxCargo);
  local shipError = AIError.GetLastError();
  if (!AIVehicle.IsValidVehicle(ship)) {
    result.error = shipError; result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, null); result.reason = "SHIP"; return OpexWaterStampCost(result, costs);
  }
  if (AIVehicle.GetCapacity(ship, catalog.paxCargo) <= 0) {
    result.opcodes += budget.end("build_ships"); OpexWaterRollback(dockA, dockB, depot, ship);
    result.reason = "PAX"; return OpexWaterStampCost(result, costs);
  }
  local maxOrderDistance = AIEngine.GetMaximumOrderDistance(chosen.id);
  if (maxOrderDistance > 0 && orderDistance > maxOrderDistance) {
    result.opcodes += budget.end("build_ships"); OpexWaterRollback(dockA, dockB, depot, ship);
    result.reason = "RANGE"; return OpexWaterStampCost(result, costs);
  }
  local orderA = AIOrder.AppendOrder(ship, dockA, AIOrder.OF_NONE);
  local errorOrderA = orderA ? 0 : AIError.GetLastError();
  local orderB = AIOrder.AppendOrder(ship, dockB, AIOrder.OF_NONE);
  local errorOrderB = orderB ? 0 : AIError.GetLastError();
  if (!orderA || !orderB || AIOrder.GetOrderCount(ship) != 2) {
    result.error = !orderA ? errorOrderA : errorOrderB; result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, ship); result.reason = "ORDERS"; return OpexWaterStampCost(result, costs);
  }
  local started = AIVehicle.StartStopVehicle(ship);
  local startError = started ? 0 : AIError.GetLastError();
  if (!started) {
    result.error = startError; result.opcodes += budget.end("build_ships");
    OpexWaterRollback(dockA, dockB, depot, ship); result.reason = "START"; return OpexWaterStampCost(result, costs);
  }
  result.opcodes += budget.end("build_ships");
  result.ok = true; result.reason = "OK"; result.dockA = dockA; result.dockB = dockB;
  result.stationA = stationA; result.stationB = stationB; result.depot = depot; result.vehicle = ship;
  return OpexWaterStampCost(result, costs);
}

/* Une ligne eau ne porte qu'un navire. Son depot, son moteur et ses deux quais
 * sont conserves dans la ligne, ce qui permet de reconstruire apres un crash
 * sans template vivant ni replanification geometrique. */
function OpexWaterRefleetCrashedShip(line)
{
  local result = { added = 0, reason = "" };
  if (!(("refleetEngine" in line) && line.refleetEngine >= 0) ||
      !("depot" in line) || !AIMarine.IsWaterDepotTile(line.depot)) {
    result.reason = "NOMETADATA"; return result;
  }
  if (!AIMarine.IsDockTile(line.stationA) || !AIMarine.IsDockTile(line.stationB)) {
    result.reason = "NODOCK"; return result;
  }
  if (AIVehicle.GetBuildWithRefitCapacity(line.depot, line.refleetEngine, line.cargo) <= 0) {
    result.reason = "REFIT"; return result;
  }
  local price = AIEngine.GetPrice(line.refleetEngine);
  if (price <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + OpexCashReserve()) {
    result.reason = "CASH"; return result;
  }
  local ship = AIVehicle.BuildVehicleWithRefit(line.depot, line.refleetEngine, line.cargo);
  if (!AIVehicle.IsValidVehicle(ship)) { result.reason = "BUILD"; return result; }
  if (!AIOrder.AppendOrder(ship, line.stationA, AIOrder.OF_NONE) ||
      !AIOrder.AppendOrder(ship, line.stationB, AIOrder.OF_NONE) || AIOrder.GetOrderCount(ship) != 2) {
    AIVehicle.SellVehicle(ship); result.reason = "ORDER"; return result;
  }
  if (!AIVehicle.StartStopVehicle(ship)) {
    if (AIVehicle.IsStoppedInDepot(ship)) AIVehicle.SellVehicle(ship);
    result.reason = "START"; return result;
  }
  if (!("vehicles" in line)) line.vehicles <- [];
  else if (line.vehicles == null) line.vehicles = [];
  line.vehicles.append(ship);
  if ("vehicle" in line) line.vehicle = ship;
  else line.vehicle <- ship;
  result.added = 1; result.reason = "OK";
  return result;
}
