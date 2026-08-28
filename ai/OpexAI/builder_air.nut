/* Etage 3b : une liaison aerienne passagers, sans pathfinding.
 *
 * L'avion est le contrepoint du rail : il n'y a pas de recherche A*, mais les aires de
 * construction et la compatibilite aeroport/appareil sont des preconditions reelles. On choisit
 * donc les deux plus grosses villes pour lesquelles les DEUX aeroports passent AITestMode avant
 * toute mutation. La construction elle-meme est transactionnelle : avion vendu, puis aeroports
 * retires, au moindre echec apres le premier aeroport.
 */

const AIR_TOWN_POOL = 12;
const AIR_SITE_RADIUS = 35;
const AIR_TOWN_MIN_DISTANCE = 30;
const AIR_MAX_SITE_PROBES = 1200;

/* GetPrice ne comprend pas le nettoyage eventuel du terrain. Cette marge s'ajoute a la reserve
 * generale dans main.nut avant le premier BuildAirport. */
const AIR_CAPITAL_MARGIN = 50000;

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

/* Trouve la premiere ancre constructible, par couronnes autour de la ville. L'ancre est bien le
 * coin haut-gauche attendu par BuildAirport. La couverture est testee contre le rectangle entier,
 * pas seulement contre son coin. */
function OpexAirFindSite(town, airport, probes)
{
  /* Chaque ville recoit sa part arrondie vers le haut du reliquat. Une ville dont le premier
   * emplacement est bon rend donc les probes inutilisees aux suivantes, sans que les premieres
   * puissent accaparer le budget global. */
  local allowance = probes.townsLeft > 0
      ? (probes.left + probes.townsLeft - 1) / probes.townsLeft : 0;
  probes.townsLeft--;
  local used = 0;
  for (local r = 0; r <= AIR_SITE_RADIUS; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local anchor = town.tile + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(anchor)) continue;
        if (OpexAirDistanceToRect(town.tile, anchor, airport.width, airport.height) >
            airport.coverage) continue;
        if (AIAirport.GetNearestTown(anchor, airport.type) != town.id) continue;
        if (used >= allowance || probes.left <= 0) return null;

        local ok = false;
        {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        }
        used++;
        probes.left--;
        if (ok) return { town = town, anchor = anchor };
      }
    }
  }
  return null;
}

/* Les deux villes les plus peuplees qui ont chacune un site, sont suffisamment disjointes, et
 * sont a portee de l'appareil retenu. GetOrderDistance est la seule unite comparable a la portee
 * fournie par GetMaximumOrderDistance. */
function OpexAirPlans(catalog)
{
  if (catalog.airport == null || catalog.plane == null) return null;
  local towns = OpexAirSortedTowns(catalog.towns);
  local limit = towns.len() < AIR_TOWN_POOL ? towns.len() : AIR_TOWN_POOL;
  local sites = [];
  local probes = { left = AIR_MAX_SITE_PROBES, townsLeft = limit };
  for (local i = 0; i < limit; i++) {
    local site = OpexAirFindSite(towns[i], catalog.airport, probes);
    if (site != null) sites.append(site);
  }

  for (local a = 0; a < sites.len(); a++) {
    for (local b = a + 1; b < sites.len(); b++) {
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
      if (distance < AIR_TOWN_MIN_DISTANCE) continue;
      local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      sites[a].anchor, sites[b].anchor);
      if (catalog.plane.maxOrderDistance > 0 && orderDistance > catalog.plane.maxOrderDistance) {
        continue;
      }
      return { siteA = sites[a], siteB = sites[b], distance = distance,
               orderDistance = orderDistance };
    }
  }
  return null;
}

function OpexAirRollback(airportA, airportB, plane)
{
  /* L'avion n'est demarre qu'apres les ordres valides : il est donc encore dans le hangar et peut
   * etre vendu avant que ce hangar ne disparaisse. */
  if (plane != null && AIVehicle.IsValidVehicle(plane)) AIVehicle.SellVehicle(plane);
  if (airportB != null && AIAirport.IsAirportTile(airportB)) AIAirport.RemoveAirport(airportB);
  if (airportA != null && AIAirport.IsAirportTile(airportA)) AIAirport.RemoveAirport(airportA);
}

/* Construit une ligne aerienne complete. Le caller a deja mesure la recherche des sites et
 * verifie le budget monetaire. Rend toujours une table, jamais une exception. */
function OpexBuildAirRoute(catalog, budget, plan)
{
  local result = { ok = false, reason = "", opcodes = 0, error = 0, stationA = null,
                   stationB = null, vehicle = null };
  local airportA = null;
  local airportB = null;
  local plane = null;

  budget.begin();
  local okA = AIAirport.BuildAirport(plan.siteA.anchor, catalog.airport.type, AIStation.STATION_NEW);
  if (okA && AIAirport.IsAirportTile(plan.siteA.anchor)) airportA = plan.siteA.anchor;
  if (airportA == null) {
    result.error = AIError.GetLastError();
    result.opcodes += budget.end("build_airports");
    result.reason = "AFAIL";
    return result;
  }

  local okB = AIAirport.BuildAirport(plan.siteB.anchor, catalog.airport.type, AIStation.STATION_NEW);
  if (okB && AIAirport.IsAirportTile(plan.siteB.anchor)) airportB = plan.siteB.anchor;
  result.opcodes += budget.end("build_airports");
  if (airportB == null) {
    result.error = AIError.GetLastError();
    OpexAirRollback(airportA, null, null);
    result.reason = "BFAIL";
    return result;
  }

  local stationA = AIStation.GetStationID(airportA);
  local stationB = AIStation.GetStationID(airportB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) {
    OpexAirRollback(airportA, airportB, null);
    result.reason = "STNFAIL";
    return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(airportA);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    OpexAirRollback(airportA, airportB, null);
    result.reason = "HANGAR";
    return result;
  }

  budget.begin();
  plane = AIVehicle.BuildVehicleWithRefit(hangar, catalog.plane.id, catalog.paxCargo);
  if (!AIVehicle.IsValidVehicle(plane)) {
    result.error = AIError.GetLastError();
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(airportA, airportB, null);
    result.reason = "PLANE";
    return result;
  }

  local okOrderA = AIOrder.AppendOrder(plane, airportA, AIOrder.OF_NONE);
  local errorA = okOrderA ? 0 : AIError.GetLastError();
  local okOrderB = AIOrder.AppendOrder(plane, airportB, AIOrder.OF_NONE);
  local errorB = okOrderB ? 0 : AIError.GetLastError();
  local ordersOk = okOrderA && okOrderB && AIOrder.GetOrderCount(plane) == 2;
  if (!ordersOk) {
    result.error = !okOrderA ? errorA : errorB;
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(airportA, airportB, plane);
    result.reason = "ORDFAIL";
    return result;
  }
  if (!AIVehicle.StartStopVehicle(plane)) {
    result.error = AIError.GetLastError();
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(airportA, airportB, plane);
    result.reason = "START";
    return result;
  }
  result.opcodes += budget.end("build_aircraft");

  result.ok = true;
  result.reason = "OK";
  result.stationA = airportA;
  result.stationB = airportB;
  result.vehicle = plane;
  return result;
}
