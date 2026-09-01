/* Etage 3b : une liaison aerienne passagers, sans pathfinding.
 *
 * L'avion est le contrepoint du rail : il n'y a pas de recherche A*, mais les aires de
 * construction et la compatibilite aeroport/appareil sont des preconditions reelles.
 * Regle : 2 types principaux d'avions et d'aeroports (les gros et les petits).
 * Les gros avions ne vont QUE dans les grands aeroports.
 * La construction elle-meme est transactionnelle : avion vendu, puis aeroports
 * retires, au moindre echec apres le premier aeroport.
 */

const AIR_TOWN_POOL = 100;
const AIR_HUB_TOWN_POOL = 100;
const AIR_HUB_NEW_SITE_POOL = 25;
const AIR_SITE_RADIUS = 35;
const AIR_TOWN_MIN_DISTANCE = 32;
const AIR_MAX_SITE_PROBES = 25000;
/* Une piste AT_LARGE ne doit pas recevoir une flotte sans borne. */
const AIR_MAX_PLANES_PER_ROUTE = 10;

/* GetPrice ne comprend pas le nettoyage eventuel du terrain. Cette marge s'ajoute a la reserve
 * generale dans main.nut avant le premier BuildAirport. */
const AIR_CAPITAL_MARGIN = 50000;

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

function OpexAirTownServed(town, lines)
{
  if (lines == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if (AIMap.DistanceManhattan(town.tile, line.originA) < 15) return true;
    if (AIMap.DistanceManhattan(town.tile, line.originB) < 15) return true;
  }
  return false;
}

function OpexAirAirportAcceptsPlane(airportType, planeType)
{
  if (planeType == AIAirport.PT_SMALL_PLANE) return true;
  return airportType != AIAirport.AT_SMALL && airportType != AIAirport.AT_COMMUTER;
}

/* Trouve la premiere ancre constructible, par couronnes autour de la ville. L'ancre est bien le
 * coin haut-gauche attendu par BuildAirport. La couverture est testee contre le rectangle entier,
 * pas seulement contre son coin. */
function OpexAirFindSite(town, airport, probes)
{
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
          if (!ok) {
            local endTile = anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
            if (AIMap.IsValidTile(endTile)) {
              AITile.LevelTiles(anchor, endTile);
              ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
            }
          }
        }
        used++;
        probes.left--;
        if (ok) return { town = town, anchor = anchor };
      }
    }
  }
  return null;
}

/* Economie et dimensionnement optimal de flotte selon les caracteristiques du vehicule. */
function OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
                          infrastructureMaintenance, maxCapital, newAirportCount = 2)
{
  local effectiveSpeed = plane.speed / 4.0;
  if (effectiveSpeed < 1.0) effectiveSpeed = 1.0;
  local flightDays = distance.tofloat() / (0.036 * effectiveSpeed);
  local airportDelayDays = 3.0;
  local oneWayDays = flightDays + airportDelayDays;
  if (oneWayDays < 1.0) oneWayDays = 1.0;
  local roundTripDays = 2.0 * oneWayDays;
  local tripsPerMonth = 30.4 / oneWayDays;
  local capacityPerPlane = plane.capacity * tripsPerMonth;
  if (capacityPerPlane <= 0) return null;
  local incomeDays = OpexCeilDiv(oneWayDays, 1);
  local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, distance, incomeDays);
  local totalIncomePerUnit = paxIncome;
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, distance, incomeDays);
    /* En soute, les avions de ligne transportent ~15% de fret postal sans refit */
    totalIncomePerUnit = paxIncome + (mailIncome * 15) / 100;
  }
  local incomePerUnit = totalIncomePerUnit;
  local airportMaintenanceAnnual =
      infrastructureMaintenance ? 12 * newAirportCount * airport.maintenance : 0;
  local airportAmortAnnual = newAirportCount * airport.price / 30;
  local best = null;

  /* Plafond d'appareils initial : 2 sur nouvelle ligne 2 aéroports (diversification de capital), jusqu'à 4 sur hub existant */
  local isSmall = (airport.type == AIAirport.AT_SMALL || airport.type == AIAirport.AT_COMMUTER);
  local maxAllowed = (newAirportCount == 2) ? 2 : (isSmall ? 3 : 4);
  /* Dimensionnement cible selon le volume passagers */
  local targetPlanes = OpexCeilDiv(monthlyPax, capacityPerPlane.tointeger());
  if (targetPlanes < 1) targetPlanes = 1;
  if (targetPlanes > maxAllowed) targetPlanes = maxAllowed;

  for (local planes = 1; planes <= targetPlanes; planes++) {
    local capital = newAirportCount * airport.price + planes * plane.price;
    if (maxCapital > 0 && capital > maxCapital) break;
    local headwayDays = roundTripDays / planes;
    local stationRating = OpexStationRatingForHeadway(headwayDays);
    local offered = (monthlyPax * stationRating) / 100.0;
    local monthlyCapacity = planes * capacityPerPlane;
    local carried = (offered < monthlyCapacity ? offered : monthlyCapacity).tointeger();
    local revenueAnnual = (12 * carried * incomePerUnit).tointeger();
    local runningAnnual = planes * plane.runningCost + airportMaintenanceAnnual;
    local amortAnnual = planes * plane.price / 20 + airportAmortAnnual;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    local roi = capital > 0 ? (profitAnnual * 1000) / capital : 0;
    if (best == null || profitAnnual > best.profitAnnual ||
        (profitAnnual == best.profitAnnual && roi > best.roi)) {
      best = {
        planes = planes, profitAnnual = profitAnnual, revenueAnnual = revenueAnnual,
        runningAnnual = runningAnnual, amortAnnual = amortAnnual, capital = capital, roi = roi,
        oneWayDays = oneWayDays, roundTripDays = roundTripDays, headwayDays = headwayDays,
        stationRating = stationRating, tripsPerMonth = tripsPerMonth,
        monthlyCapacity = monthlyCapacity, carried = carried,
      };
    }
  }
  return best;
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
  if (!AIAirport.IsAirportTile(line.stationA)) {
    result.reason = "NOAIR"; return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(line.stationA);
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
  if (!AIVehicle.IsValidVehicle(extra)) { result.reason = "CLONE"; return result; }
  if (!AIVehicle.StartStopVehicle(extra)) {
    if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
    result.reason = "START"; return result;
  }
  line.vehicles.append(extra);
  result.added = 1;
  result.reason = "OK";
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

function OpexAirPlans(catalog, lines = null, maxCapital = 0, projects = null)
{
  local combos = (("airCombos" in catalog) && catalog.airCombos != null && catalog.airCombos.len() > 0)
      ? catalog.airCombos
      : (catalog.airport != null && catalog.plane != null ? [{ airport = catalog.airport, plane = catalog.plane }] : []);
  if (combos.len() == 0) return null;

  local towns = OpexAirSortedTowns(catalog.towns);
  local limit = towns.len() < AIR_TOWN_POOL ? towns.len() : AIR_TOWN_POOL;
  local bestPlan = null;
  /* GetMonthlyMaintenanceCost expose le tarif potentiel, pas une depense toujours active.
   * CompaniesGenStatistics ne le debite que si le reglage de partie est arme. La configuration
   * gelee le laisse a false : compter ce tarif rendait toutes les paires de la graine 42
   * artificiellement deficitaires (270 000/an pour deux AT_LARGE). */
  local infrastructureMaintenance =
      AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  AILog.Info("OpexAirPlans: combos=" + combos.len() + " towns=" + towns.len());

  foreach (combo in combos) {
    local airport = combo.airport;
    local plane = combo.plane;
    local townPool = (plane.speed >= 400) ? AIR_TOWN_POOL : 40;
    local limit = towns.len() < townPool ? towns.len() : townPool;
    local minDist = (plane.speed >= 400) ? 32 : 40;
    local sites = [];
    local probes = { left = AIR_MAX_SITE_PROBES, townsLeft = limit };
    for (local i = 0; i < limit; i++) {
      /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
       * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
       * construction aerienne sur une carte partiellement couverte. */
      if (OpexAirTownServed(towns[i], lines)) continue;
      /* Typage strict selon la strate de population :
       * - Grands aéroports : réservés aux villes >= 1200 habitants
       * - Petits aéroports : adaptés aux villes < 2500 habitants */
      if (combo.kind == "large" && towns[i].pop < 1200) continue;
      if (combo.kind == "small" && towns[i].pop >= 2500) continue;
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
          OpexSign(AIMap.GetTileIndex(1, 7), "AZ|D=" + distance + "|OD=" + orderDistance + "|MO=" + plane.maxOrderDistance + "|MIN=" + minDist);
        }
        if (distance < minDist) continue;
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

        local flightDistance = OpexFlightDistance(sites[a].anchor, sites[b].anchor);
        local economics = OpexAirEconomics(catalog, airport, plane, flightDistance, monthlyPax,
                                            infrastructureMaintenance, maxCapital, 2);
        if (economics == null) continue;

        local plan = {
          siteA = sites[a], siteB = sites[b], distance = flightDistance,
          orderDistance = orderDistance,
          airport = airport, plane = plane,
          planes = economics.planes, capital = economics.capital, economics = economics,
          reuseA = false, hubRoutes = 0,
        };

        if (a == 0 && b == 1) {
          OpexSign(AIMap.GetTileIndex(1, 8), "AY|" + economics.capital + "|"
                                                + economics.profitAnnual);
          OpexSign(AIMap.GetTileIndex(1, 9), "AV|" + plane.speed + "|" + plane.capacity
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

    /* Bras hub : un aeroport existant, rentable et non sature (max 8 routes), plus UNE destination. */
    local hubs = [];
    if (AIR_HUB && lines != null) {
      if (sites.len() < AIR_HUB_NEW_SITE_POOL) {
        local hubProbes = { left = AIR_MAX_SITE_PROBES, townsLeft = towns.len() };
        for (local i = 0; i < towns.len() && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
          if (OpexAirTownServed(towns[i], lines)) continue;
          /* Typage strict : les petits aéroports pour les villes secondaires */
          if (combo.kind == "large" && towns[i].pop < 1200) continue;
          if (combo.kind == "small" && towns[i].pop >= 2500) continue;
          local extraSite = OpexAirFindSite(towns[i], airport, hubProbes);
          if (extraSite != null) sites.append(extraSite);
        }
      }
      local seenStations = {};
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        if (("lastProfit" in line) && line.lastProfit < 0) continue;
        local ends = [
          { anchor = line.stationA, origin = line.originA },
          { anchor = line.stationB, origin = line.originB },
        ];
        foreach (end in ends) {
          if (!AIAirport.IsAirportTile(end.anchor)) continue;
          local existingType = AIAirport.GetAirportType(end.anchor);
          if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
          local station = AIStation.GetStationID(end.anchor);
          if (!AIStation.IsValidStation(station) || station in seenStations) continue;

          local routeCount = 0;
          foreach (other in lines) {
            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = AIStation.GetStationID(other.stationA);
            local otherB = AIStation.GetStationID(other.stationB);
            if (otherA == station || otherB == station) routeCount++;
          }
          local maxRoutes = (existingType == AIAirport.AT_SMALL || existingType == AIAirport.AT_COMMUTER) ? 4 : 8;
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
          hubs.append({ town = hubTown, anchor = end.anchor, routes = routeCount });
        }
      }
    }

    foreach (hub in hubs) {
      foreach (site in sites) {
        local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
        if (distance < 35) continue;
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                        hub.anchor, site.anchor);
        if (plane.maxOrderDistance > 0 && orderDistance > plane.maxOrderDistance) continue;
        local hubMonthly = ((hub.town.pop * 22) / 100) / (hub.routes + 1);
        local newMonthly = (site.town.pop * 22) / 100;
        local monthlyPax = hubMonthly + newMonthly;
        if (monthlyPax < 10) monthlyPax = 10;
        local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
        local economics = OpexAirEconomics(catalog, airport, plane, flightDistance, monthlyPax,
                                            infrastructureMaintenance, maxCapital, 1);
        if (economics == null || economics.profitAnnual <= 0) continue;
        local plan = {
          siteA = hub, siteB = site, distance = flightDistance, orderDistance = orderDistance,
          airport = airport, plane = plane, planes = economics.planes,
          capital = economics.capital, economics = economics,
          reuseA = true, hubRoutes = hub.routes,
        };
        if (projects != null) projects.append(plan);
        if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
      }
    }

    /* Liaisons Hub-a-Hub directes entre deux aeroports existants (capital = 1 avion seul) */
    for (local i = 0; i < hubs.len(); i++) {
      for (local j = i + 1; j < hubs.len(); j++) {
        local hub1 = hubs[i];
        local hub2 = hubs[j];
        local st1 = AIStation.GetStationID(hub1.anchor);
        local st2 = AIStation.GetStationID(hub2.anchor);
        local alreadyConnected = false;
        foreach (line in lines) {
          if (!("mode" in line) || line.mode != "air") continue;
          local oA = AIStation.GetStationID(line.stationA);
          local oB = AIStation.GetStationID(line.stationB);
          if ((oA == st1 && oB == st2) || (oA == st2 && oB == st1)) {
            alreadyConnected = true; break;
          }
        }
        if (alreadyConnected) continue;
        local distance = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
        if (distance < 35) continue;
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
        if (plane.maxOrderDistance > 0 && orderDistance > plane.maxOrderDistance) continue;
        local monthly1 = ((hub1.town.pop * 22) / 100) / (hub1.routes + 1);
        local monthly2 = ((hub2.town.pop * 22) / 100) / (hub2.routes + 1);
        local monthlyPax = monthly1 + monthly2;
        if (monthlyPax < 10) monthlyPax = 10;
        local flightDistance = OpexFlightDistance(hub1.anchor, hub2.anchor);
        local economics = OpexAirEconomics(catalog, airport, plane, flightDistance, monthlyPax,
                                            infrastructureMaintenance, maxCapital, 0);
        if (economics == null || economics.profitAnnual <= 0) continue;
        local plan = {
          siteA = hub1, siteB = hub2, distance = flightDistance, orderDistance = orderDistance,
          airport = airport, plane = plane, planes = economics.planes,
          capital = economics.capital, economics = economics,
          reuseA = true, reuseB = true, hubRoutes = hub1.routes + hub2.routes,
        };
        if (projects != null) projects.append(plan);
        if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
      }
    }
    if (AIR_HUB && hubs.len() > 0) {
      OpexSign(AIMap.GetTileIndex(1, 6), "AU|" + hubs.len() + "|"
               + (bestPlan != null && bestPlan.reuseA ? 1 : 0));
    }
    OpexSign(AIMap.GetTileIndex(1, 4), "AE|S=" + sites.len() + "|B=" + (bestPlan != null ? bestPlan.economics.profitAnnual : "NO"));
    if (bestPlan != null && bestPlan.airport.allowBig) break;
  }
  return bestPlan;
}

function OpexAirRollback(airportA, airportB, planes)
{
  /* La flotte n'est demarree qu'apres tous les clones et ordres valides : elle est donc encore
   * dans le hangar et peut etre vendue avant que ce hangar ne disparaisse. */
  foreach (plane in planes) {
    if (AIVehicle.IsValidVehicle(plane)) AIVehicle.SellVehicle(plane);
  }
  if (airportB != null && AIAirport.IsAirportTile(airportB)) AIAirport.RemoveAirport(airportB);
  if (airportA != null && AIAirport.IsAirportTile(airportA)) AIAirport.RemoveAirport(airportA);
}

/* Construit une ligne aerienne complete. Le caller a deja mesure la recherche des sites et
 * verifie le budget monetaire. Rend toujours une table, jamais une exception. */
function OpexBuildAirRoute(catalog, budget, plan)
{
  local result = { ok = false, reason = "", opcodes = 0, error = 0, stationA = null,
                   stationB = null, vehicle = null, vehicles = [] };
  local airportA = null;
  local airportB = null;
  local plane = null;

  local airport = ("airport" in plan) ? plan.airport : catalog.airport;
  local planeChoice = ("plane" in plan) ? plan.plane : catalog.plane;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;

  budget.begin();
  if (reuseA) {
    if (AIAirport.IsAirportTile(plan.siteA.anchor) &&
        OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteA.anchor),
                                   planeChoice.planeType)) {
      airportA = plan.siteA.anchor;
    }
  } else {
    local endA = plan.siteA.anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
    if (AIMap.IsValidTile(endA)) AITile.LevelTiles(plan.siteA.anchor, endA);
    local okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
    if (okA && AIAirport.IsAirportTile(plan.siteA.anchor)) airportA = plan.siteA.anchor;
  }
  if (airportA == null) {
    result.error = AIError.GetLastError();
    result.opcodes += budget.end("build_airports");
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
    local endB = plan.siteB.anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
    if (AIMap.IsValidTile(endB)) AITile.LevelTiles(plan.siteB.anchor, endB);
    local okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
    if (okB && AIAirport.IsAirportTile(plan.siteB.anchor)) airportB = plan.siteB.anchor;
  }
  result.opcodes += budget.end("build_airports");
  if (airportB == null) {
    result.error = AIError.GetLastError();
    OpexAirRollback(reuseA ? null : airportA, null, []);
    result.reason = reuseB ? "HUBB" : "BFAIL";
    return result;
  }

  local stationA = AIStation.GetStationID(airportA);
  local stationB = AIStation.GetStationID(airportB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) {
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.reason = "STNFAIL";
    return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(airportA);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.reason = "HANGAR";
    return result;
  }

  budget.begin();
  plane = AIVehicle.BuildVehicleWithRefit(hangar, planeChoice.id, catalog.paxCargo);
  if (!AIVehicle.IsValidVehicle(plane)) {
    result.error = AIError.GetLastError();
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(reuseA ? null : airportA, airportB, []);
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
    OpexAirRollback(reuseA ? null : airportA, airportB, [plane]);
    result.reason = "ORDFAIL";
    return result;
  }
  local built = [plane];
  local wanted = ("planes" in plan) ? plan.planes : 1;
  for (local i = 1; i < wanted; i++) {
    local extra = AIVehicle.CloneVehicle(hangar, plane, true);
    if (!AIVehicle.IsValidVehicle(extra)) {
      result.error = AIError.GetLastError();
      result.opcodes += budget.end("build_aircraft");
      OpexAirRollback(reuseA ? null : airportA, airportB, built);
      result.reason = "CLONE";
      return result;
    }
    built.append(extra);
  }
  foreach (aircraft in built) {
    if (!AIVehicle.StartStopVehicle(aircraft)) {
      result.error = AIError.GetLastError();
      result.opcodes += budget.end("build_aircraft");
      OpexAirRollback(reuseA ? null : airportA, airportB, built);
      result.reason = "START";
      return result;
    }
  }
  result.opcodes += budget.end("build_aircraft");

  result.ok = true;
  result.reason = "OK";
  result.stationA = airportA;
  result.stationB = airportB;
  result.vehicle = plane;
  result.vehicles = built;
  result.reusedA <- reuseA;
  return result;
}
