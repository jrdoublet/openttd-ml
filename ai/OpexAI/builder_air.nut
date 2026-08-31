/* Etage 3b : une liaison aerienne passagers, sans pathfinding.
 *
 * L'avion est le contrepoint du rail : il n'y a pas de recherche A*, mais les aires de
 * construction et la compatibilite aeroport/appareil sont des preconditions reelles.
 * Regle : 2 types principaux d'avions et d'aeroports (les gros et les petits).
 * Les gros avions ne vont QUE dans les grands aeroports.
 * La construction elle-meme est transactionnelle : avion vendu, puis aeroports
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
  local allowance = 400;
  probes.townsLeft--;
  local used = 0;
  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local anchor = town.tile + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(anchor)) continue;
        if (OpexAirDistanceToRect(town.tile, anchor, airport.width, airport.height) > 25) continue;
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

/* Evalue et planifie la meilleure liaison aerienne en testant les combinaisons
 * grand aeroport (+gros/petit avion) et petit aeroport (+petit avion strictement).
 * Privilegie le plus fort ROI avec retour sur investissement rapide. */
function OpexAirPlans(catalog, lines = null)
{
  local combos = (("airCombos" in catalog) && catalog.airCombos != null && catalog.airCombos.len() > 0)
      ? catalog.airCombos
      : (catalog.airport != null && catalog.plane != null ? [{ airport = catalog.airport, plane = catalog.plane }] : []);
  if (combos.len() == 0) return null;

  local towns = OpexAirSortedTowns(catalog.towns);
  local limit = towns.len() < AIR_TOWN_POOL ? towns.len() : AIR_TOWN_POOL;
  local bestPlan = null;
  AILog.Info("OpexAirPlans: combos=" + combos.len() + " towns=" + towns.len());

  foreach (combo in combos) {
    local airport = combo.airport;
    local plane = combo.plane;
    local sites = [];
    local probes = { left = AIR_MAX_SITE_PROBES, townsLeft = limit };
    for (local i = 0; i < limit; i++) {
      /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
       * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
       * construction aerienne sur une carte partiellement couverte. */
      local airServed = false;
      if (lines != null) {
        foreach (line in lines) {
          if (!("mode" in line) || line.mode != "air") continue;
          if (AIMap.DistanceManhattan(towns[i].tile, line.originA) < 15) { airServed = true; break; }
          if (AIMap.DistanceManhattan(towns[i].tile, line.originB) < 15) { airServed = true; break; }
        }
      }
      if (airServed) continue;
      local site = OpexAirFindSite(towns[i], airport, probes);
      if (site != null) sites.append(site);
    }
    OpexSign(AIMap.GetTileIndex(1, 3), "AS|S=" + sites.len() + "|A=" + airport.name);

    for (local a = 0; a < sites.len(); a++) {
      for (local b = a + 1; b < sites.len(); b++) {
        local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                        sites[a].anchor, sites[b].anchor);
        if (a == 0 && b == 1) {
          OpexSign(AIMap.GetTileIndex(1, 7), "AZ|D=" + distance + "|OD=" + orderDistance + "|MO=" + plane.maxOrderDistance + "|MIN=" + AIR_TOWN_MIN_DISTANCE);
        }
        if (distance < AIR_TOWN_MIN_DISTANCE) continue;
        if (plane.maxOrderDistance > 0 && orderDistance > plane.maxOrderDistance) {
          continue;
        }

        local popA = sites[a].town.pop;
        local popB = sites[b].town.pop;
        local monthlyPax = ((popA + popB) * 22) / 100;
        if (monthlyPax < 10) monthlyPax = 10;
        if (a == 0 && b == 1) {
          OpexSign(AIMap.GetTileIndex(1, 5), "AX|PA=" + popA + "|PB=" + popB + "|MPX=" + monthlyPax);
        }

        // Vitesse effective de l'avion (facteur 4 de OpenTTD plane_speed)
        local effectiveSpeed = plane.speed / 4.0;
        if (effectiveSpeed < 1.0) effectiveSpeed = 1.0;
        local oneWayDays = distance.tofloat() / (0.036 * effectiveSpeed);
        if (oneWayDays < 1.0) oneWayDays = 1.0;
        local tripsPerMonth = 30.0 / oneWayDays;
        local monthlyCapacity = (plane.capacity * tripsPerMonth).tointeger();
        local carried = monthlyPax < monthlyCapacity ? monthlyPax : monthlyCapacity;
        local incomeDays = OpexCeilDiv(oneWayDays, 1);
        local revenueAnnual = (12 * carried * AICargo.GetCargoIncome(catalog.paxCargo, distance, incomeDays)).tointeger();
        local runningAnnual = plane.runningCost + 24 * airport.maintenance;
        local amortAnnual = plane.price / 20 + 2 * airport.price / 30;
        local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
        local capital = 2 * airport.price + plane.price;
        local roi = capital > 0 ? (profitAnnual * 1000) / capital : 0;

        local plan = {
          siteA = sites[a], siteB = sites[b], distance = distance,
          orderDistance = orderDistance,
          airport = airport, plane = plane,
          capital = capital,
          economics = {
            profitAnnual = profitAnnual,
            revenueAnnual = revenueAnnual,
            runningAnnual = runningAnnual,
            amortAnnual = amortAnnual,
            roi = roi,
            oneWayDays = oneWayDays,
            carried = carried,
          }
        };

        if (a == 0 && b == 1) {
          OpexSign(AIMap.GetTileIndex(1, 8), "AW|R=" + revenueAnnual + "|C=" + runningAnnual + "|A=" + amortAnnual + "|P=" + profitAnnual);
          OpexSign(AIMap.GetTileIndex(1, 9), "AV|SP=" + plane.speed + "|CP=" + plane.capacity + "|OWD=" + oneWayDays + "|TC=" + tripsPerMonth);
        }
        if (profitAnnual > 0) {
          if (bestPlan == null || roi > bestPlan.economics.roi) {
            bestPlan = plan;
          }
        }
      }
    }
    OpexSign(AIMap.GetTileIndex(1, 4), "AE|S=" + sites.len() + "|B=" + (bestPlan != null ? bestPlan.economics.profitAnnual : "NO"));
    // Si on a trouve un plan rentable pour le grand aeroport a gros avion, on le retient
    if (bestPlan != null && bestPlan.airport.allowBig) break;
  }
  return bestPlan;
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

  local airport = ("airport" in plan) ? plan.airport : catalog.airport;
  local planeChoice = ("plane" in plan) ? plan.plane : catalog.plane;

  budget.begin();
  local okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
  if (okA && AIAirport.IsAirportTile(plan.siteA.anchor)) airportA = plan.siteA.anchor;
  if (airportA == null) {
    result.error = AIError.GetLastError();
    result.opcodes += budget.end("build_airports");
    result.reason = "AFAIL";
    return result;
  }

  local okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
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
  plane = AIVehicle.BuildVehicleWithRefit(hangar, planeChoice.id, catalog.paxCargo);
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
