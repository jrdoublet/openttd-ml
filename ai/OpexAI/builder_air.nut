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
AIR_SITE_RADIUS <- 35;
AIR_TOWN_MIN_DISTANCE <- 32;
AIR_MAX_SITE_PROBES <- 1500;
AIR_MAX_PLANES_PER_ROUTE <- 16;
AIR_CAPITAL_MARGIN <- 50000;
/* Plafond empirique de distance aérienne (docs/taches.md C6) : 0 succès mesurés au-delà de 212 tuiles */
AIR_MAX_DISTANCE <- 212;

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
  local allowance = 120;
  probes.townsLeft--;
  local used = 0;
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

        if (used >= allowance || probes.left <= 0) return null;

        local ok = false;
        {
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

  /* Plafond d'appareils initial : jusqu'à 3 sur nouvelle ligne, jusqu'à 6 sur hub existant.
   * marginal_fleet = 1 (2026-09-01) : demarrage MINIMAL, 1 seul avion quel que soit le type
   * d'aeroport -- la croissance se fait ensuite par _resizeAirFleets (main.nut), apres un an
   * d'existence et une charge complete mesuree, jamais en achetant d'emblee tout ce que le modele
   * predit. Sous 0 (defaut), ce bloc ne change rien au calcul existant. */
  local isSmall = (airport.type == AIAirport.AT_SMALL || airport.type == AIAirport.AT_COMMUTER);
  local maxAllowed = MARGINAL_FLEET ? 1 : ((newAirportCount == 2) ? 3 : (isSmall ? 4 : 6));
  /* Dimensionnement cible selon le volume passagers */
  local targetPlanes = OpexCeilDiv(monthlyPax, capacityPerPlane.tointeger());
  if (targetPlanes < 1) targetPlanes = 1;
  if (targetPlanes > maxAllowed) targetPlanes = maxAllowed;

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

  for (local planes = 1; planes <= targetPlanes; planes++) {
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

/* `abandoned` : table des paires dont une construction a deja echoue (cle
 * "air|tileA|tileB", identique a celle de main.nut). null = filtre desactive.
 * Le filtre est place APRES les tests de distance et AVANT OpexAirEconomics : les paires
 * ecartees pour distance ne paient pas la concatenation, et celles qui restent evitent le
 * calcul cher. */
function OpexAirPlans(catalog, lines = null, maxCapital = 0, projects = null, abandoned = null)
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
    local townPool = AIR_TOWN_POOL;
    local limit = towns.len() < townPool ? towns.len() : townPool;
    local minDist = (plane.speed >= 400) ? 32 : 30;
    local sites = [];
    local probes = { left = AIR_MAX_SITE_PROBES, townsLeft = limit };
    for (local i = 0; i < limit; i++) {
      /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
       * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
       * construction aerienne sur une carte partiellement couverte. */
      if (OpexAirTownServed(towns[i], lines)) continue;
      /* Typage selon la population :
       * - Grands aéroports : accessibles dès 600 habitants (suffisant pour alimenter un jet vers un hub)
       * - Petits aéroports : utilisables sur toutes les villes si aucun grand aéroport ne rentre */
      if (combo.kind == "large" && towns[i].pop < 600) continue;
      local site = OpexAirFindSite(towns[i], airport, probes);
      if (site != null) sites.append(site);
    }
    OpexSign(AIMap.GetTileIndex(1, 3), "AS|S=" + sites.len() + "|A=" + airport.name);

    for (local a = 0; a < sites.len(); a++) {
      for (local b = a + 1; b < sites.len(); b++) {
        local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                        sites[a].anchor, sites[b].anchor);
        local flightDistance = OpexFlightDistance(sites[a].anchor, sites[b].anchor);
        if (distance < minDist) continue;
        if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
        if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
          continue;
        }

        if (abandoned != null
            && (("air|" + sites[a].town.tile + "|" + sites[b].town.tile) in abandoned)) continue;

        local popA = sites[a].town.pop;
        local popB = sites[b].town.pop;
        local monthlyPax = ((popA + popB) * 22) / 100;
        if (monthlyPax < 10) monthlyPax = 10;
        if (a == 0 && b == 1) {
          OpexSign(AIMap.GetTileIndex(1, 5), "AX|PA=" + popA + "|PB=" + popB + "|MPX=" + monthlyPax);
        }

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
          /* Typage : grands aéroports dès 600 hab */
          if (combo.kind == "large" && towns[i].pop < 600) continue;
          if (combo.kind == "small" && towns[i].pop >= 2500) continue;
          local extraSite = OpexAirFindSite(towns[i], airport, hubProbes);
          if (extraSite != null) sites.append(extraSite);
        }
      }
      local seenStations = {};
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        if (("deadStreak" in line) && line.deadStreak >= 2) continue;
        local ends = [
          { anchor = line.originA, origin = line.originA, stationId = line.stationA },
          { anchor = line.originB, origin = line.originB, stationId = line.stationB },
        ];
        foreach (end in ends) {
          if (!AIMap.IsValidTile(end.anchor) || !AIAirport.IsAirportTile(end.anchor)) continue;
          local existingType = AIAirport.GetAirportType(end.anchor);
          if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
          local station = AIStation.IsValidStation(end.stationId) ? end.stationId : AIStation.GetStationID(end.anchor);
          if (!AIStation.IsValidStation(station) || (station in seenStations)) continue;

          local routeCount = 0;
          foreach (other in lines) {
            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA);
            local otherB = AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB);
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

    foreach (hub in hubs) {
      foreach (site in sites) {
        local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
        if (distance < 20) continue;
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                        hub.anchor, site.anchor);
        local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
        if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
        if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) continue;
        if (abandoned != null
            && (("air|" + hub.town.tile + "|" + site.town.tile) in abandoned)) continue;
        local hubMonthly = ((hub.town.pop * 22) / 100) / (hub.routes + 1);
        local newMonthly = (site.town.pop * 22) / 100;
        local monthlyPax = hubMonthly + newMonthly;
        if (monthlyPax < 10) monthlyPax = 10;
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
        local st1 = hub1.stationId;
        local st2 = hub2.stationId;
        local alreadyConnected = false;
        foreach (line in lines) {
          if (!("mode" in line) || line.mode != "air") continue;
          local oA = AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA);
          local oB = AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB);
          if ((oA == st1 && oB == st2) || (oA == st2 && oB == st1)) {
            alreadyConnected = true; break;
          }
        }
        if (alreadyConnected) continue;
        local distance = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
        if (distance < 20) continue;
        local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
        local flightDistance = OpexFlightDistance(hub1.anchor, hub2.anchor);
        if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) continue;
        if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) continue;
        if (abandoned != null
            && (("air|" + hub1.town.tile + "|" + hub2.town.tile) in abandoned)) continue;
        local monthly1 = ((hub1.town.pop * 22) / 100) / (hub1.routes + 1);
        local monthly2 = ((hub2.town.pop * 22) / 100) / (hub2.routes + 1);
        local monthlyPax = monthly1 + monthly2;
        if (monthlyPax < 10) monthlyPax = 10;
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
  if (airportB != null && AIAirport.IsAirportTile(airportB)) AIAirport.RemoveAirport(airportB);
  if (airportA != null && AIAirport.IsAirportTile(airportA)) AIAirport.RemoveAirport(airportA);
}

/* Construit une ligne aerienne complete. Le caller a deja mesure la recherche des sites et
 * verifie le budget monetaire. Rend toujours une table, jamais une exception. */
function OpexBuildAirRoute(catalog, budget, plan)
{
  local result = { ok = false, reason = "", opcodes = 0, error = 0, stationA = null,
                   stationB = null, vehicle = null, vehicles = [], actualCost = 0 };
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

  /* air_presite : sonder les DEUX sites avant d'engager la moindre livre. L'ordre historique
   * batissait A, decouvrait B impossible, puis demolissait A -- 4 BFAIL sur 20 tentatives au banc
   * du 2026-09-02, tous en premiere annee, quand la tresorerie est au plus juste (§0 unvicies).
   * Le nivellement des deux sites est deja paye dans le chemin nominal ; ce qu'on economise, c'est
   * l'aeroport bati puis rase. B est sonde en premier : c'est lui qui echoue. */
  if (AIR_PRESITE && !reuseA && !reuseB) {
    local endA = plan.siteA.anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
    local endB = plan.siteB.anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
    if (AIMap.IsValidTile(endA)) AITile.LevelTiles(plan.siteA.anchor, endA);
    if (AIMap.IsValidTile(endB)) AITile.LevelTiles(plan.siteB.anchor, endB);
    local errB = OpexAirSiteRefusal(plan.siteB, airport.type);
    if (errB != 0) {
      result.error = errB;
      result.actualCost = costs != null ? costs.GetCosts() : 0;
      result.opcodes += budget.end("build_airports");
      result.reason = "PREB";
      return result;
    }
    local errA = OpexAirSiteRefusal(plan.siteA, airport.type);
    if (errA != 0) {
      result.error = errA;
      result.actualCost = costs != null ? costs.GetCosts() : 0;
      result.opcodes += budget.end("build_airports");
      result.reason = "PREA";
      return result;
    }
  }

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
    if (!okA && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(plan.siteA.town.id, 800, 40);
      okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
    }
    if (okA && AIAirport.IsAirportTile(plan.siteA.anchor)) airportA = plan.siteA.anchor;
  }
  if (airportA == null) {
    result.error = AIError.GetLastError();
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
    local endB = plan.siteB.anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
    if (AIMap.IsValidTile(endB)) AITile.LevelTiles(plan.siteB.anchor, endB);
    local okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
    if (!okB && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(plan.siteB.town.id, 800, 40);
      okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
    }
    if (okB && AIAirport.IsAirportTile(plan.siteB.anchor)) airportB = plan.siteB.anchor;
  }
  result.opcodes += budget.end("build_airports");
  if (airportB == null) {
    result.error = AIError.GetLastError();
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
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(reuseA ? null : airportA, airportB, []);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
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
      result.opcodes += budget.end("build_aircraft");
      OpexAirRollback(reuseA ? null : airportA, airportB, built);
      result.actualCost = costs != null ? costs.GetCosts() : 0;
      result.reason = "START";
      return result;
    }
  }
  result.opcodes += budget.end("build_aircraft");

  result.actualCost = costs != null ? costs.GetCosts() : 0;
  result.ok = true;
  result.reason = "OK";
  result.stationA = airportA;
  result.stationB = airportB;
  result.vehicle = plane;
  result.vehicles = built;
  result.reusedA <- reuseA;
  return result;
}
