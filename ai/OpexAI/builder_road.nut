/* Liaison routiere passagers v1 : une paire de villes proches, deux arrets et un bus.
 *
 * Le trace n'utilise PAS Pathfinder.Road. Sur la graine gelee, l'A* de la bibliotheque a coute
 * 696 794 opcodes pour 500 iterations sur la paire la plus proche (20 tuiles), alors qu'un essai
 * de trace Manhattan coute 121 opcodes. Ici, on echantillonne des arrets dans le rayon de ville,
 * puis on accepte seulement l'un des deux L que BuildRoad valide sous AITestMode. C'est borne,
 * assez court pour le creneau que le rail refuse, et chaque arete reelle est revalidee.
 */

const ROAD_TOWN_MIN_DISTANCE = 5;
const ROAD_TOWN_MAX_DISTANCE = 25;
const ROAD_MAX_TRACE_TILES = 32;
const ROAD_MAX_STOPS_PER_TOWN = 8;
const ROAD_SITE_SEARCH_RADIUS = 16;
const ROAD_MAX_SITE_PROBES = 48;
const ROAD_CAPITAL_MARGIN = 25000;
const ROAD_DEPOT_MIN_STOP_DISTANCE = 3;

function OpexRoadInMap(x, y)
{
  return x >= 0 && y >= 0 && x < AIMap.GetMapSizeX() && y < AIMap.GetMapSizeY();
}

/* Meme ordre stable que les autres modes : population decroissante, puis enumeration OpenTTD. */
function OpexRoadSortedTowns(towns)
{
  local out = [];
  foreach (town in towns) {
    local pos = out.len();
    while (pos > 0 && out[pos - 1].pop < town.pop) pos--;
    out.insert(pos, town);
  }
  return out;
}

function OpexRoadAppendSegment(trace, from, to)
{
  local x = AIMap.GetTileX(from);
  local y = AIMap.GetTileY(from);
  local tx = AIMap.GetTileX(to);
  local ty = AIMap.GetTileY(to);
  while (x != tx) {
    local nx = x + (x < tx ? 1 : -1);
    local next = AIMap.GetTileIndex(nx, y);
    trace.append({ from = AIMap.GetTileIndex(x, y), to = next });
    x = nx;
  }
  while (y != ty) {
    local ny = y + (y < ty ? 1 : -1);
    local next = AIMap.GetTileIndex(x, ny);
    trace.append({ from = AIMap.GetTileIndex(x, y), to = next });
    y = ny;
  }
}

function OpexRoadTrace(from, to, firstHorizontal)
{
  local corner = firstHorizontal
    ? AIMap.GetTileIndex(AIMap.GetTileX(to), AIMap.GetTileY(from))
    : AIMap.GetTileIndex(AIMap.GetTileX(from), AIMap.GetTileY(to));
  local out = [];
  OpexRoadAppendSegment(out, from, corner);
  OpexRoadAppendSegment(out, corner, to);
  return out;
}

/* Un retour positif de BuildRoad n'est jamais une preuve : le predicat est la connectivite.
 * AITestMode ne modifie pas la carte, donc chaque arete est evaluee independamment. C'est
 * suffisant pour un L : une arete n'a pas besoin qu'une autre ait ete posee auparavant. */
function OpexRoadTraceBuildable(trace)
{
  foreach (edge in trace) {
    if (AIRoad.AreRoadTilesConnected(edge.from, edge.to)) continue;
    local buildable = false;
    { local test = AITestMode(); buildable = AIRoad.BuildRoad(edge.from, edge.to); }
    if (!buildable) return false;
  }
  return true;
}

/* Les arrets sont testes avant toute mutation. Etre proche du centre administratif ne prouve pas
 * qu'une maison se trouve dans le bassin : la premiere sonde construisait deux arrets a note -1.
 * GetCargoProduction sur l'empreinte exacte de l'arret elimine ces faux sites avant un seul cout.
 * Les probes BuildRoadStation restent bornees, puis les huit bassins les plus producteurs sont
 * gardes (departage stable par l'ordre des couronnes). */
function OpexRoadStopSites(town, cargo)
{
  local out = [];
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local tx = AIMap.GetTileX(town.tile);
  local ty = AIMap.GetTileY(town.tile);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local probes = 0;
  for (local r = 0; r <= ROAD_SITE_SEARCH_RADIUS && probes < ROAD_MAX_SITE_PROBES; r++) {
    for (local dx = -r; dx <= r && probes < ROAD_MAX_SITE_PROBES; dx++) {
      for (local dy = -r; dy <= r && probes < ROAD_MAX_SITE_PROBES; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local x = tx + dx;
        local y = ty + dy;
        if (!OpexRoadInMap(x, y)) continue;
        local tile = AIMap.GetTileIndex(x, y);
        if (AITile.GetClosestTown(tile) != town.id) continue;
        local producers = AITile.GetCargoProduction(tile, cargo, 1, 1, coverage);
        if (producers <= 0) continue;
        foreach (offset in offsets) {
          local fx = x + offset[0];
          local fy = y + offset[1];
          if (!OpexRoadInMap(fx, fy)) continue;
          local front = AIMap.GetTileIndex(fx, fy);
          /* Un arret s'ancre d'abord sur la route municipale existante. Cela evite de chercher
           * une sortie a travers les maisons depuis le centre de ville, et reserve nos appels
           * BuildRoad aux seules cases interurbaines manquantes. */
          if (!AIRoad.IsRoadTile(front)) continue;
          /* Bug jumeau de celui du depot (2026-08-28, cf. commentaire sur OpexRoadFindDepot) :
           * CmdBuildRoadStop ne construit/verifie rien sur "front" non plus (station_cmd.cpp,
           * CheckFlatLandRoadStop ne regarde QUE la tuile de l'arret). Rien ne garantit que la
           * route municipale existante a deja le bit tourne vers l'arret. Teste donc aussi
           * BuildRoad(front, tile) : c'est le raccord que OpexBuildRoadRoute devra poser pour de
           * vrai avant de batir l'arret. */
          local ok = false;
          { local test = AITestMode();
            ok = AIRoad.BuildRoad(front, tile) &&
                 AIRoad.BuildRoadStation(tile, front, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
          probes++;
          if (ok) {
            local site = { tile = tile, front = front, producers = producers };
            local pos = out.len();
            while (pos > 0 && out[pos - 1].producers < site.producers) pos--;
            out.insert(pos, site);
            if (out.len() > ROAD_MAX_STOPS_PER_TOWN) out.pop();
          }
        }
      }
    }
  }
  return out;
}

function OpexRoadIsForbidden(tile, stopA, stopB)
{
  return tile == stopA.tile || tile == stopB.tile;
}

/* Bug mesure le 2026-08-28 (docs/opex_bus_diag_*.json, signs RT/RL/RQ) : sur la paire 27<->33,
 * siteA.front == (54,27), siteA.tile == (55,27), et le trace horizontal siteA.front -> corner
 * (56,27) marche PRECISEMENT sur siteA.tile au passage. AITestMode/BuildRoad valident cette case
 * comme route plate ordinaire (rien n'y est encore construit), mais BuildRoadStation la remplace
 * ensuite par un arret NON traversant (cul-de-sac, entree/sortie par la seule facade) -- la
 * continuite du trace vers l'autre arret est donc coupee exactement au point le plus critique.
 * Mesure : le bus ne depasse jamais l'ordre 0 (rating -1 4 ans durant, RW=0, jamais AT_STATION).
 * Le filet : aucune tuile du trace (hors les deux facades, qui sont TOUJOURS des tuiles OK) ne
 * doit coincider avec le corps d'un des deux arrets. */
function OpexRoadTraceHitsStop(trace, stopTile)
{
  foreach (edge in trace) {
    if (edge.from == stopTile || edge.to == stopTile) return true;
  }
  return false;
}

/* Le depot est decide sur le L planifie mais pose apres lui. Il n'est pas construit dans une
 * boucle de gare : deux arrets simples suffisent a l'increment, la boucle est une amelioration de
 * capacite a mesurer plus tard, pas un pretexte a ajouter des stations.
 *
 * Bug racine du bus fige (2026-08-28, prouve dans le source du jeu, road_cmd.cpp:1151 /
 * script_road.cpp:524) : CmdBuildRoadDepot ne construit QUE sur sa propre tuile ; il ne touche
 * jamais "front". AIRoad.BuildRoadDepot(tile, front) se contente de calculer une DiagDirection a
 * partir de la geometrie tile/front et de la passer a cette commande -- "front" ne recoit donc
 * JAMAIS le bit de route perpendiculaire dont le depot a besoin, sauf si quelque chose d'autre l'a
 * deja construit. Comme "front" est ici toujours l'interieur d'un segment DROIT du trace, seuls
 * les deux bits dans l'axe du trace y existent (poses par OpexRoadBuildTrace) -- jamais le bit
 * perpendiculaire vers le depot. D'ou la mesure : bus fige EXACTEMENT sur la tuile du depot (RL),
 * vitesse qui oscille sans jamais avancer (RV/RQ) -- il ne peut litteralement pas monter sur
 * "front", quel que soit le nombre d'annees. Chaque site candidat doit donc AUSSI poser ce bit
 * manquant avec BuildRoad(front, tile) avant BuildRoadDepot -- cf. OpexBuildRoadRoute. */
function OpexRoadFindDepot(trace, stopA, stopB)
{
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local seen = {};
  /* Experience du 2026-08-28 (cf. docs/opex_bus_diag_*.json) : chercher a partir de la fin du trace
   * (cote siteB) plutot que du debut echoue purement et simplement (DEPOT, aucun site
   * constructible sur toute cette moitie) -- le terrain degage n'existe qu'aux abords immediats
   * des arrets, pas au milieu du trace. Le depot doit donc rester cherche depuis le debut. */
  foreach (edge in trace) {
    local fronts = [edge.from, edge.to];
    foreach (front in fronts) {
      if (front in seen) continue;
      seen.rawset(front, true);
      /* Mesure du 2026-08-28 : meme apres avoir evite que le trace ne traverse le CORPS d'un
       * arret (OpexRoadTraceHitsStop), la premiere facade du trace est TOUJOURS siteA.front (le
       * trace commence toujours la), donc sans ce filet le depot s'y accroche systematiquement --
       * meme facade que l'arret, puis a 1 seule tuile d'elle une fois ce cas exclu. Le bus ne
       * chargeait toujours rien apres 4 ans dans les deux configurations (rating -1, RW=0
       * constant, ordre bloque sur stopA, campagne graine 42 -- docs/opex_bus_diag_*.json). Le
       * trace a 24 tuiles de facades candidates ; ROAD_DEPOT_MIN_STOP_DISTANCE ecarte tout le
       * voisinage immediat des deux arrets, pas seulement leur facade exacte. */
      if (AIMap.DistanceManhattan(front, stopA.front) < ROAD_DEPOT_MIN_STOP_DISTANCE) continue;
      if (AIMap.DistanceManhattan(front, stopB.front) < ROAD_DEPOT_MIN_STOP_DISTANCE) continue;
      local x = AIMap.GetTileX(front);
      local y = AIMap.GetTileY(front);
      foreach (offset in offsets) {
        local x2 = x + offset[0];
        local y2 = y + offset[1];
        if (!OpexRoadInMap(x2, y2)) continue;
        local tile = AIMap.GetTileIndex(x2, y2);
        if (OpexRoadIsForbidden(tile, stopA, stopB)) continue;
        /* Les deux commandes doivent passer sous AITestMode : BuildRoad(front, tile) prouve que le
         * raccord manquant (cf. commentaire ci-dessus) est constructible, BuildRoadDepot(tile,
         * front) que le depot lui-meme l'est. Ni l'une ni l'autre seule ne suffit. */
        local ok = false;
        { local test = AITestMode();
          ok = AIRoad.BuildRoad(front, tile) && AIRoad.BuildRoadDepot(tile, front); }
        if (ok) return { tile = tile, front = front };
      }
    }
  }
  return null;
}

/* Une paire est dans le creneau du bus par les centres de villes, et le trace concret a sa propre
 * borne (les arrets peuvent s'ecarter de quelques cases dans leur rayon de couverture). */
function OpexRoadPlans(catalog)
{
  if (catalog.roadBuses.len() == 0 || catalog.paxCargo < 0 || catalog.roadType < 0) return null;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local towns = OpexRoadSortedTowns(catalog.towns);
  local pairs = [];
  for (local a = 0; a < towns.len(); a++) {
    for (local b = a + 1; b < towns.len(); b++) {
      local distance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (distance < ROAD_TOWN_MIN_DISTANCE || distance > ROAD_TOWN_MAX_DISTANCE) continue;
      /* Les seules villes qui meritent les AITestMode de gare sont celles qui forment une paire
       * dans la bande route. Insertion stable par population totale. */
      local pair = { townA = towns[a], townB = towns[b], distance = distance,
                     population = towns[a].pop + towns[b].pop };
      local pos = pairs.len();
      while (pos > 0 && pairs[pos - 1].population < pair.population) pos--;
      pairs.insert(pos, pair);
    }
  }
  foreach (pair in pairs) {
    local sitesA = OpexRoadStopSites(pair.townA, catalog.paxCargo);
    local sitesB = OpexRoadStopSites(pair.townB, catalog.paxCargo);
    if (sitesA.len() == 0 || sitesB.len() == 0) continue;
    foreach (siteA in sitesA) {
      foreach (siteB in sitesB) {
        for (local shape = 0; shape < 2; shape++) {
          local trace = OpexRoadTrace(siteA.front, siteB.front, shape == 0);
          if (trace.len() == 0 || trace.len() > ROAD_MAX_TRACE_TILES) continue;
          /* cf. commentaire sur OpexRoadTraceHitsStop : le trace ne doit jamais retraverser le
           * corps d'un des deux arrets qu'il relie, sous peine d'etre coupe une fois l'arret
           * construit par-dessus. */
          if (OpexRoadTraceHitsStop(trace, siteA.tile) || OpexRoadTraceHitsStop(trace, siteB.tile)) continue;
          if (!OpexRoadTraceBuildable(trace)) continue;
          local depot = OpexRoadFindDepot(trace, siteA, siteB);
          if (depot == null) continue;
          return { townA = pair.townA, townB = pair.townB, stopA = siteA, stopB = siteB,
                   trace = trace, depot = depot, distance = pair.distance,
                   routeDistance = trace.len(), shape = shape };
        }
      }
    }
  }
  return null;
}

/* La liste added ne contient que les aretes dont la connexion n'existait pas avant notre appel.
 * Le rollback ne supprime donc jamais une route de ville preexistante. */
function OpexRoadRollback(stopA, stopB, depot, bus, added)
{
  if (bus != null && AIVehicle.IsValidVehicle(bus)) AIVehicle.SellVehicle(bus);
  if (depot != null && AIRoad.IsRoadDepotTile(depot)) AIRoad.RemoveRoadDepot(depot);
  if (stopB != null && AIRoad.IsRoadStationTile(stopB)) AIRoad.RemoveRoadStation(stopB);
  if (stopA != null && AIRoad.IsRoadStationTile(stopA)) AIRoad.RemoveRoadStation(stopA);
  for (local i = added.len() - 1; i >= 0; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
}

function OpexRoadBuildTrace(trace, added)
{
  foreach (edge in trace) {
    if (AIRoad.AreRoadTilesConnected(edge.from, edge.to)) continue;
    local ok = AIRoad.BuildRoad(edge.from, edge.to);
    /* L'API peut repondre ERR_ALREADY_BUILT alors que l'arete etait deja presente : seul le test
     * de connectivite decide. Si nous avons vraiment construit, elle est marquee pour rollback. */
    local connected = AIRoad.AreRoadTilesConnected(edge.from, edge.to);
    if (!connected) return false;
    if (ok) added.append(edge);
  }
  return true;
}

function OpexRoadChooseBus(catalog, depot)
{
  local best = null;
  local bestCapacity = 0;
  foreach (candidate in catalog.roadBuses) {
    local capacity = AIVehicle.GetBuildWithRefitCapacity(depot, candidate.id, catalog.paxCargo);
    if (capacity > bestCapacity ||
        (capacity == bestCapacity && capacity > 0 &&
         (best == null || candidate.speed > best.speed ||
          (candidate.speed == best.speed && candidate.price < best.price)))) {
      best = candidate;
      bestCapacity = capacity;
    }
  }
  return best == null || bestCapacity <= 0 ? null : { engine = best, capacity = bestCapacity };
}

/* Transaction complete. Le bus ne demarre qu'apres les ordres et toutes les connexions valides,
 * donc il peut toujours etre vendu dans le depot pendant le rollback. */
function OpexBuildRoadRoute(catalog, budget, plan)
{
  local result = { ok = false, reason = "", error = 0, stopA = null, stopB = null,
                   stationA = null, stationB = null, depot = null, vehicle = null, cost = 0,
                   capacity = 0, opcodes = 0 };
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local balanceBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local added = [];
  local stopA = null;
  local stopB = null;
  local depot = null;
  local bus = null;

  budget.begin();
  if (!OpexRoadBuildTrace(plan.trace, added)) {
    result.error = AIError.GetLastError();
    result.opcodes = budget.end("build_roads");
    OpexRoadRollback(null, null, null, null, added); result.reason = "ROAD"; return result;
  }
  result.opcodes = budget.end("build_roads");

  budget.begin();
  /* Meme bug que le depot (cf. commentaire sur OpexRoadFindDepot et sur OpexRoadStopSites) :
   * CmdBuildRoadStop ne pose ni ne verifie rien sur "front". Le raccord doit donc etre construit
   * explicitement AVANT l'arret, pendant que la tuile de l'arret est encore une route ordinaire
   * clairable -- CMD_LANDSCAPE_CLEAR interne de CmdBuildRoadStop la remplace ensuite, "front"
   * garde le bit. Chaque arete n'est ajoutee a `added` que si elle est reellement connectee. */
  local stubOkA = AIRoad.BuildRoad(plan.stopA.front, plan.stopA.tile);
  local stubConnectedA = AIRoad.AreRoadTilesConnected(plan.stopA.front, plan.stopA.tile);
  if (stubConnectedA) added.append({ from = plan.stopA.front, to = plan.stopA.tile });
  local okA = stubConnectedA && AIRoad.BuildRoadStation(plan.stopA.tile, plan.stopA.front,
                                                        AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
  /* Bout en bout : GetRoadStationFrontTile, comme GetRoadDepotFrontTile, n'est que la geometrie
   * DECLAREE (station + offset), jamais une preuve de connexion reelle. Contrairement a ce que
   * supposait un commentaire precedent, AreRoadTilesConnected gere correctement les tuiles
   * MP_STATION (GetAnyRoadBits en fait un cas explicite, verifie dans road_map.cpp) : c'est donc le
   * seul predicat qui prouve que l'arret est reellement raccorde a "front", pas seulement pose. */
  if (okA && AIRoad.IsRoadStationTile(plan.stopA.tile) &&
      AIRoad.GetRoadStationFrontTile(plan.stopA.tile) == plan.stopA.front &&
      AIRoad.AreRoadTilesConnected(plan.stopA.tile, plan.stopA.front)) stopA = plan.stopA.tile;
  if (stopA == null) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_road_stops");
    OpexRoadRollback(null, null, null, null, added); result.reason = "ASTOP"; return result;
  }
  local stubOkB = AIRoad.BuildRoad(plan.stopB.front, plan.stopB.tile);
  local stubConnectedB = AIRoad.AreRoadTilesConnected(plan.stopB.front, plan.stopB.tile);
  if (stubConnectedB) added.append({ from = plan.stopB.front, to = plan.stopB.tile });
  local okB = stubConnectedB && AIRoad.BuildRoadStation(plan.stopB.tile, plan.stopB.front,
                                                        AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
  if (okB && AIRoad.IsRoadStationTile(plan.stopB.tile) &&
      AIRoad.GetRoadStationFrontTile(plan.stopB.tile) == plan.stopB.front &&
      AIRoad.AreRoadTilesConnected(plan.stopB.tile, plan.stopB.front)) stopB = plan.stopB.tile;
  result.opcodes += budget.end("build_road_stops");
  if (stopB == null) {
    result.error = AIError.GetLastError(); OpexRoadRollback(stopA, null, null, null, added);
    result.reason = "BSTOP"; return result;
  }
  local stationA = AIStation.GetStationID(stopA);
  local stationB = AIStation.GetStationID(stopB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) || stationA == stationB) {
    OpexRoadRollback(stopA, stopB, null, null, added); result.reason = "STATION"; return result;
  }

  budget.begin();
  /* Le vrai bug (2026-08-28, prouve dans road_cmd.cpp:1151/script_road.cpp:524, cf. commentaire
   * sur OpexRoadFindDepot) : CmdBuildRoadDepot ne construit RIEN sur "front", seulement sur sa
   * propre tuile. Sans ce raccord explicite, "front" ne recoit jamais le bit de route
   * perpendiculaire vers le depot -- le bus reste physiquement incapable de monter dessus (mesure :
   * RL fige exactement sur la tuile du depot, RV/RQ oscillent sans avancer). Ce BuildRoad pose ce
   * bit manquant AVANT le depot, pendant que la tuile du depot est encore une route ordinaire
   * clairable ; BuildRoadDepot la remplace ensuite (CMD_LANDSCAPE_CLEAR interne), "front" garde le
   * bit. L'arete est ajoutee a `added` (donc demontee par le rollback) des qu'elle est reellement
   * connectee -- avant meme de savoir si le depot suivra. */
  local stubOk = AIRoad.BuildRoad(plan.depot.front, plan.depot.tile);
  local stubConnected = AIRoad.AreRoadTilesConnected(plan.depot.front, plan.depot.tile);
  if (stubConnected) added.append({ from = plan.depot.front, to = plan.depot.tile });
  local depotOk = stubConnected && AIRoad.BuildRoadDepot(plan.depot.tile, plan.depot.front);
  /* Comme pour le rail : un "reussi" de l'API n'est jamais une preuve de connexion. Contrairement a
   * ce que supposait un commentaire precedent, AreRoadTilesConnected gere correctement le cas
   * ROAD_TILE_DEPOT (GetAnyRoadBits renvoie DiagDirToRoadBits(GetRoadDepotDirection(tile)), verifie
   * dans road_map.cpp) : c'est donc le seul predicat qui prouve que le depot est reellement
   * raccorde au trace, pas seulement pose avec la bonne geometrie declaree
   * (IsRoadDepotTile/GetRoadDepotFrontTile). */
  if (depotOk && AIRoad.IsRoadDepotTile(plan.depot.tile) &&
      AIRoad.GetRoadDepotFrontTile(plan.depot.tile) == plan.depot.front &&
      AIRoad.AreRoadTilesConnected(plan.depot.tile, plan.depot.front)) depot = plan.depot.tile;
  result.opcodes += budget.end("build_road_depot");
  if (depot == null) {
    result.error = AIError.GetLastError(); OpexRoadRollback(stopA, stopB, null, null, added);
    result.reason = "DEPOT"; return result;
  }

  budget.begin();
  local choice = OpexRoadChooseBus(catalog, depot);
  if (choice == null) {
    result.opcodes += budget.end("build_buses"); OpexRoadRollback(stopA, stopB, depot, null, added);
    result.reason = "REFIT"; return result;
  }
  bus = AIVehicle.BuildVehicleWithRefit(depot, choice.engine.id, catalog.paxCargo);
  if (!AIVehicle.IsValidVehicle(bus)) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_buses");
    OpexRoadRollback(stopA, stopB, depot, null, added); result.reason = "BUS"; return result;
  }
  if (AIVehicle.GetCapacity(bus, catalog.paxCargo) <= 0 ||
      !AIEngine.CanRunOnRoad(choice.engine.id, catalog.roadType) ||
      !AIEngine.HasPowerOnRoad(choice.engine.id, catalog.roadType) ||
      !AIRoad.RoadVehHasPowerOnRoad(AIVehicle.GetRoadType(bus), catalog.roadType)) {
    result.opcodes += budget.end("build_buses"); OpexRoadRollback(stopA, stopB, depot, bus, added);
    result.reason = "PAX"; return result;
  }
  local orderA = AIOrder.AppendOrder(bus, stopA, AIOrder.OF_NONE);
  local errorA = orderA ? 0 : AIError.GetLastError();
  local orderB = AIOrder.AppendOrder(bus, stopB, AIOrder.OF_NONE);
  local errorB = orderB ? 0 : AIError.GetLastError();
  if (!orderA || !orderB || AIOrder.GetOrderCount(bus) != 2) {
    result.error = !orderA ? errorA : errorB; result.opcodes += budget.end("build_buses");
    OpexRoadRollback(stopA, stopB, depot, bus, added); result.reason = "ORDERS"; return result;
  }
  if (!AIVehicle.StartStopVehicle(bus)) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_buses");
    OpexRoadRollback(stopA, stopB, depot, bus, added); result.reason = "START"; return result;
  }
  result.opcodes += budget.end("build_buses");

  result.ok = true; result.reason = "OK"; result.stopA = stopA; result.stopB = stopB;
  result.stationA = stationA; result.stationB = stationB; result.depot = depot; result.vehicle = bus;
  result.capacity = AIVehicle.GetCapacity(bus, catalog.paxCargo);
  result.cost = balanceBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  return result;
}
