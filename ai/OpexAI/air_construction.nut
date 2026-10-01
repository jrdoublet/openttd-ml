/* Module AIR extrait de builder_air.nut (R11) : sondage, construction physique et rollback. */
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

function OpexAirRollback(airportA, airportB, planes, pairKey = "")
{
  local airports = [];
  if (airportB != null) airports.append(airportB);
  if (airportA != null && airportA != airportB) airports.append(airportA);
  local ticket = { version = 1, vehicles = clone planes, airports = airports,
      pairKey = pairKey, nextDate = 0 };
  /* Enregistrer AVANT toute commande susceptible de suspendre / sauvegarder. */
  OPEX_AIR_ROLLBACKS.append(ticket);
  if (OpexAirContinueRollback(ticket)) {
    OPEX_AIR_ROLLBACKS.pop();
    AILog.Info("AIR_ROLLBACK_DONE pair=" + pairKey + " immediate=1");
  }
  else AILog.Warning("AIR_ROLLBACK_PENDING pair=" + pairKey
      + " vehicles=" + ticket.vehicles.len() + " airports=" + ticket.airports.len());
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
  /* R19 : un retry ne doit pas dupliquer le service ni reutiliser un aeroport
   * promis a la demolition pendant la liquidation du chantier precedent. */
  if (OpexAirRecoveryBlocksPlan(plan)) {
    result.reason = "RECOVERY";
    return result;
  }
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
    local levelA = OpexAirLevelFootprint(plan.siteA.anchor, airport, plan.siteA.town.id);
    local okA = levelA.ok && AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
    if (!levelA.ok) {
      airportErrorA = levelA.error;
      airportErrorTextA = levelA.errorText;
    } else if (!okA) {
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
    local levelB = OpexAirLevelFootprint(plan.siteB.anchor, airport, plan.siteB.town.id);
    local okB = levelB.ok && AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
    if (!levelB.ok) {
      airportErrorB = levelB.error;
      airportErrorTextB = levelB.errorText;
    } else if (!okB) {
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
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, [plane],
      OpexAirPairKey(plan.siteA, plan.siteB));
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
        OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built,
          OpexAirPairKey(plan.siteA, plan.siteB));
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
        OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built,
          OpexAirPairKey(plan.siteA, plan.siteB));
      result.actualCost = costs != null ? costs.GetCosts() : 0;
      result.reason = "START";
      return result;
    }
  }
  if (R19_FAULT_INJECT > 0) {
    R19_FAULT_ROUTE_SEQ++;
    if (R19_FAULT_ROUTE_SEQ == R19_FAULT_INJECT) {
      AILog.Warning("R19_FAULT_INJECT route=" + R19_FAULT_ROUTE_SEQ
          + " planes=" + built.len() + " pair=" + OpexAirPairKey(plan.siteA, plan.siteB));
      result.error = -1;
      result.errorText = "R19_FAULT_INJECT";
      result.opcodes += budget.end("build_aircraft");
      OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built,
        OpexAirPairKey(plan.siteA, plan.siteB));
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
