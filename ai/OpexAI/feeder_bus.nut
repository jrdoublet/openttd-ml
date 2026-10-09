/* feeder_bus.nut -- Chantier V139: feeder bus navette centre-ville vers aeroport.
 * Rabattement des passagers du centre-ville vers l'aeroport OpexAI le plus proche.
 * Ordres de transfert: AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD au terminus aeroport.
 * V139.2:
 *  - Prise en compte de la couverture globale de la station (aeroport + arrets joints).
 *  - Siting aeroport strict a proximite de l'emprise aeroport (pas en ville).
 *  - Decision Utilisateur (5) : deliaison de l'arret joint au centre-ville (Remove + Build STATION_NEW).
 *  - Repli (4) : captage hors couverture de la station existante.
 *  - Modele economique corrige (credits de transfert + allongement du trajet paye + bonus de frequence).
 *  - Raccordement voirie BFS sans restriction de pente artificielle sur voirie ordinaire.
 */

V139_FEEDER_SKIP_LOGGED <- {};
V139_FEEDER_CAND_LOGGED <- {};

function OpexV139LogSkip(airportId, reason)
{
  if ((airportId in V139_FEEDER_SKIP_LOGGED) && V139_FEEDER_SKIP_LOGGED[airportId] == reason) return;
  V139_FEEDER_SKIP_LOGGED[airportId] <- reason;
  AILog.Info("V139_SKIP airport=" + airportId + " reason=" + reason);
}

function OpexV139LogCandidate(airportId, isUnjoined, netProfit, threshold, capital, roi)
{
  if (airportId in V139_FEEDER_CAND_LOGGED) return;
  V139_FEEDER_CAND_LOGGED[airportId] <- true;
  AILog.Info("V139_CANDIDATE airport=" + airportId + " is_unjoined=" + (isUnjoined ? 1 : 0)
             + " estim_profit=" + netProfit + " threshold=" + threshold
             + " capital=" + capital + " roi=" + roi);
}

/* Calcule l'ensemble des tuiles couvertes par tous les composants d'une station
 * (aeroport, arrets de bus joints, camions, trains, quais). */
function OpexStationCoverageTiles(stationId)
{
  local coverageTiles = {};
  if (!AIStation.IsValidStation(stationId)) return coverageTiles;

  local types = [
    { st = AIStation.STATION_AIRPORT, rad = 4 },
    { st = AIStation.STATION_BUS_STOP, rad = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP) },
    { st = AIStation.STATION_TRUCK_STOP, rad = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP) },
    { st = AIStation.STATION_TRAIN, rad = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN) },
    { st = AIStation.STATION_DOCK, rad = AIStation.GetCoverageRadius(AIStation.STATION_DOCK) },
  ];

  foreach (entry in types) {
    if (!AIStation.HasStationType(stationId, entry.st)) continue;
    local stTiles = AITileList_StationType(stationId, entry.st);
    local r = entry.rad;
    if (entry.st == AIStation.STATION_AIRPORT && !stTiles.IsEmpty()) {
      local aType = AIAirport.GetAirportType(stTiles.Begin());
      r = AIAirport.GetAirportCoverageRadius(aType);
    }
    for (local t = stTiles.Begin(); !stTiles.IsEnd(); t = stTiles.Next()) {
      local tx = AIMap.GetTileX(t);
      local ty = AIMap.GetTileY(t);
      for (local dx = -r; dx <= r; dx++) {
        for (local dy = -r; dy <= r; dy++) {
          local tile = AIMap.GetTileIndex(tx + dx, ty + dy);
          if (AIMap.IsValidTile(tile)) {
            coverageTiles.rawset(tile, true);
          }
        }
      }
    }
  }
  return coverageTiles;
}

function OpexAirportIsTownCenterCovered(airportTile, airportType, townCenter)
{
  if (!AIMap.IsValidTile(airportTile) || !AIMap.IsValidTile(townCenter)) return true;
  local w = AIAirport.GetAirportWidth(airportType);
  local h = AIAirport.GetAirportHeight(airportType);
  local r = AIAirport.GetAirportCoverageRadius(airportType);
  return OpexAirB9TileInExpandedRect(townCenter, airportTile, w, h, r);
}

function OpexTownConnectedRoads(startTile, maxTiles = 600)
{
  local roads = {};
  if (!AIMap.IsValidTile(startTile) || !AIRoad.IsRoadTile(startTile)) return roads;
  roads.rawset(startTile, true);
  local q = [startTile];
  local qi = 0;
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  while (qi < q.len() && roads.len() < maxTiles) {
    local cur = q[qi++];
    foreach (d in dirs) {
      local nxt = cur + d;
      if (!AIMap.IsValidTile(nxt) || (nxt in roads)) continue;
      if (!AIRoad.IsRoadTile(nxt)) continue;
      if (!AIRoad.AreRoadTilesConnected(cur, nxt)) continue;
      roads.rawset(nxt, true);
      q.append(nxt);
    }
  }
  return roads;
}

/* Recherche si l'aeroport possede un arret de bus joint situe en ville (centre-ville). */
function OpexFindTownJoinedStop(airportStationId, airportTile, townId, townCenter)
{
  local existingStops = AITileList_StationType(airportStationId, AIStation.STATION_BUS_STOP);
  if (existingStops.IsEmpty()) return null;

  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1),
                AIMap.GetTileIndex(-1, 0), AIMap.GetTileIndex(0, -1)];

  local candStops = [];
  for (local t = existingStops.Begin(); !existingStops.IsEnd(); t = existingStops.Next()) {
    // Un arret deja delie (ou persiste) ne doit JAMAIS etre selectionne ni re-delie
    if (t in V139_UNJOINED_STOPS) continue;

    // Ne pas selectionner un arret pose a l'aeroport meme (distance Manhattan <= 4 de l'ancre)
    local distAir = AIMap.DistanceManhattan(t, airportTile);
    if (distAir <= 4) continue;

    local distCenter = (townCenter != null) ? AIMap.DistanceManhattan(t, townCenter) : 999;
    if (AITile.GetClosestTown(t) != townId && distCenter > 15) continue;

    local front = AIRoad.GetRoadStationFrontTile(t);
    if (!AIMap.IsValidTile(front) || !AIRoad.IsRoadTile(front) || !AIRoad.AreRoadTilesConnected(t, front)) {
      front = null;
      foreach (d in dirs) {
        local tryF = t + d;
        if (AIMap.IsValidTile(tryF) && AIRoad.IsRoadTile(tryF) && AIRoad.AreRoadTilesConnected(t, tryF)) {
          front = tryF;
          break;
        }
      }
    }
    if (front != null) {
      candStops.append({ tile = t, front = front, dist = distCenter });
    }
  }

  if (candStops.len() == 0) return null;
  candStops.sort(function(a, b) {
    if (a.dist < b.dist) return -1;
    if (a.dist > b.dist) return 1;
    return 0;
  });
  return candStops[0];
}

/* Recherche d'arrets potentiels A L'AEROPORT (autour de l'emprise piste/terminal). */
function OpexFindAirportFeederStopSites(airportStationId, airportTile, airportType, townCenter)
{
  local sites = [];
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1),
                AIMap.GetTileIndex(-1, 0), AIMap.GetTileIndex(0, -1)];

  local ax = AIMap.GetTileX(airportTile);
  local ay = AIMap.GetTileY(airportTile);
  local w = AIAirport.GetAirportWidth(airportType);
  local h = AIAirport.GetAirportHeight(airportType);

  // 1. Verifier si l'aeroport possede deja un arret de bus existant A L'AEROPORT
  local existingStops = AITileList_StationType(airportStationId, AIStation.STATION_BUS_STOP);
  if (!existingStops.IsEmpty()) {
    for (local t = existingStops.Begin(); !existingStops.IsEnd(); t = existingStops.Next()) {
      if (AIMap.DistanceManhattan(t, airportTile) > 3) continue;
      foreach (d in dirs) {
        local f = t + d;
        if (AIMap.IsValidTile(f) && AIRoad.IsRoadTile(f) && AIRoad.AreRoadTilesConnected(t, f)) {
          local distVal = (townCenter != null) ? AIMap.DistanceManhattan(t, townCenter) : 0;
          sites.append({ tile = t, front = f, existing = true, needsRoad = false, dist = distVal });
          break;
        }
      }
    }
  }

  // 2. Chercher sur la voirie existante dans le perimetre d'extension de la gare
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();

  local minX = ax - 4; if (minX < 1) minX = 1;
  local maxX = ax + w + 4; if (maxX >= mapX - 1) maxX = mapX - 2;
  local minY = ay - 4; if (minY < 1) minY = 1;
  local maxY = ay + h + 4; if (maxY >= mapY - 1) maxY = mapY - 2;

  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(minX, minY), AIMap.GetTileIndex(maxX, maxY));
  tiles.Valuate(AIRoad.IsRoadTile);
  tiles.KeepValue(1);
  tiles.Valuate(AIRoad.IsRoadStationTile);
  tiles.KeepValue(0);
  tiles.Valuate(AIRoad.IsRoadDepotTile);
  tiles.KeepValue(0);

  for (local t = tiles.Begin(); !tiles.IsEnd(); t = tiles.Next()) {
    foreach (d in dirs) {
      local f = t + d;
      if (!AIMap.IsValidTile(f) || !AIRoad.IsRoadTile(f) || !AIRoad.AreRoadTilesConnected(t, f)) continue;
      local testMode = AITestMode();
      local ok = AIRoad.BuildDriveThroughRoadStation(t, f, AIRoad.ROADVEHTYPE_BUS, airportStationId);
      testMode = null;
      if (ok) {
        local distVal = (townCenter != null) ? AIMap.DistanceManhattan(t, townCenter) : 0;
        sites.append({ tile = t, front = f, existing = false, needsRoad = false, dist = distVal });
        break;
      }
    }
  }

  // 3. Chercher sur les tuiles immediatement adjacentes a l'emprise de l'aeroport (contact direct)
  local perimeter = [];
  for (local x = ax; x < ax + w; x++) {
    if (ay > 1) {
      local pTile = AIMap.GetTileIndex(x, ay - 1);
      local pDist = (townCenter != null) ? AIMap.DistanceManhattan(pTile, townCenter) : 0;
      perimeter.append({ tile = pTile, dist = pDist });
    }
    if (ay + h < mapY - 2) {
      local pTile = AIMap.GetTileIndex(x, ay + h);
      local pDist = (townCenter != null) ? AIMap.DistanceManhattan(pTile, townCenter) : 0;
      perimeter.append({ tile = pTile, dist = pDist });
    }
  }
  for (local y = ay; y < ay + h; y++) {
    if (ax > 1) {
      local pTile = AIMap.GetTileIndex(ax - 1, y);
      local pDist = (townCenter != null) ? AIMap.DistanceManhattan(pTile, townCenter) : 0;
      perimeter.append({ tile = pTile, dist = pDist });
    }
    if (ax + w < mapX - 2) {
      local pTile = AIMap.GetTileIndex(ax + w, y);
      local pDist = (townCenter != null) ? AIMap.DistanceManhattan(pTile, townCenter) : 0;
      perimeter.append({ tile = pTile, dist = pDist });
    }
  }

  perimeter.sort(function(a, b) {
    if (a.dist < b.dist) return -1;
    if (a.dist > b.dist) return 1;
    return 0;
  });

  foreach (entry in perimeter) {
    local cand = entry.tile;
    if (!AIMap.IsValidTile(cand) || (!AITile.IsBuildable(cand) && !AIRoad.IsRoadTile(cand)) || !OpexRoadIsFlat(cand)) continue;

    local candDirs = [];
    foreach (d in dirs) {
      local f = cand + d;
      local dDist = (townCenter != null) ? AIMap.DistanceManhattan(f, townCenter) : 0;
      candDirs.append({ dir = d, dist = dDist });
    }
    candDirs.sort(function(a, b) {
      if (a.dist < b.dist) return -1;
      if (a.dist > b.dist) return 1;
      return 0;
    });

    foreach (dEntry in candDirs) {
      local f = cand + dEntry.dir;
      if (!AIMap.IsValidTile(f) || (!AITile.IsBuildable(f) && !AIRoad.IsRoadTile(f)) || !OpexRoadIsFlat(f)) continue;
      local testMode = AITestMode();
      local okRoad = AIRoad.BuildRoad(cand, f) || AIRoad.AreRoadTilesConnected(cand, f);
      if (!okRoad && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) okRoad = true;
      local okSt = false;
      if (okRoad) {
        okSt = AIRoad.BuildDriveThroughRoadStation(cand, f, AIRoad.ROADVEHTYPE_BUS, airportStationId);
        if (!okSt && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) okSt = true;
      }
      testMode = null;
      if (okRoad && okSt) {
        sites.append({ tile = cand, front = f, existing = false, needsRoad = !AIRoad.AreRoadTilesConnected(cand, f), dist = entry.dist });
        break;
      }
    }
  }

  return sites;
}

function OpexFindAirportFeederStopSite(airportStationId, airportTile, airportType)
{
  local sites = OpexFindAirportFeederStopSites(airportStationId, airportTile, airportType, null);
  if (sites.len() > 0) return sites[0];
  return null;
}

/* Recherche d'arret centre-ville captant HORS de la zone deja couverte par la station. */
function OpexFindTownFeederStopSite(townCenter, townId, catalog, airportTile, stationCoverage = null)
{
  local busCoverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local townSites = OpexRoadPaxVoirieSites(townCenter, townId, catalog.paxCargo, AIRoad.ROADVEHTYPE_BUS, busCoverage, airportTile, true);
  if (townSites.len() == 0) {
    townSites = OpexRoadPaxVoirieSites(townCenter, townId, catalog.paxCargo, AIRoad.ROADVEHTYPE_BUS, busCoverage, airportTile, false);
  }
  if (townSites.len() == 0) return null;

  if (stationCoverage == null || stationCoverage.len() == 0) {
    local res = townSites[0];
    res.uncoveredPax <- AITile.GetCargoProduction(res.tile, catalog.paxCargo, 1, 1, busCoverage);
    return res;
  }

  local bestSite = null;
  local bestUncovered = 0;

  foreach (site in townSites) {
    local sx = AIMap.GetTileX(site.tile);
    local sy = AIMap.GetTileY(site.tile);
    local uncoveredVal = 0;

    for (local dx = -busCoverage; dx <= busCoverage; dx++) {
      for (local dy = -busCoverage; dy <= busCoverage; dy++) {
        local t = AIMap.GetTileIndex(sx + dx, sy + dy);
        if (!AIMap.IsValidTile(t)) continue;
        if (t in stationCoverage) continue;
        local p = AITile.GetCargoProduction(t, catalog.paxCargo, 1, 1, 0);
        if (p > 0) uncoveredVal += p;
      }
    }

    if (uncoveredVal > bestUncovered) {
      bestUncovered = uncoveredVal;
      bestSite = site;
      bestSite.uncoveredPax <- uncoveredVal;
    }
  }

  if (bestSite == null || bestUncovered < 12) return null;
  return bestSite;
}

function OpexFindFeederDepot(siteTown, siteAirport, trace, targetRoad, townRoads = null)
{
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];

  local roadCandidates = [siteAirport.front];
  local seen = {};
  seen.rawset(siteAirport.front, true);
  foreach (edge in trace) {
    if (!(edge.to in seen)) { seen.rawset(edge.to, true); roadCandidates.append(edge.to); }
    if (!(edge.from in seen)) { seen.rawset(edge.from, true); roadCandidates.append(edge.from); }
  }
  if (targetRoad != null && !(targetRoad in seen)) {
    seen.rawset(targetRoad, true);
    roadCandidates.append(targetRoad);
  }

  local forbidden = {};
  forbidden.rawset(siteTown.tile, true);
  forbidden.rawset(siteTown.front, true);
  forbidden.rawset(siteAirport.tile, true);
  forbidden.rawset(siteAirport.front, true);
  foreach (edge in trace) {
    forbidden.rawset(edge.from, true);
    forbidden.rawset(edge.to, true);
  }

  local testMode = AITestMode();
  foreach (roadTile in roadCandidates) {
    if (!AIMap.IsValidTile(roadTile)) continue;
    foreach (d in dirs) {
      local depotTile = roadTile + d;
      if (!AIMap.IsValidTile(depotTile)) continue;
      if (depotTile in forbidden) continue;
      if (AITile.IsStationTile(depotTile)) continue;
      if (!OpexRoadIsFlat(depotTile)) continue;
      if (!AITile.IsBuildable(depotTile)) continue;

      local okRoad = AIRoad.BuildRoad(roadTile, depotTile) || AIRoad.AreRoadTilesConnected(roadTile, depotTile);
      if (!okRoad && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) okRoad = true;
      local okDepot = false;
      if (okRoad) {
        okDepot = AIRoad.BuildRoadDepot(depotTile, roadTile);
        if (!okDepot && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) okDepot = true;
      }
      if (okRoad && okDepot) {
        testMode = null;
        return { tile = depotTile, front = roadTile };
      }
    }
  }

  if (townRoads != null) {
    local checkCenters = [];
    if (targetRoad != null) checkCenters.append(targetRoad);
    checkCenters.append(siteTown.tile);

    foreach (cTile in checkCenters) {
      foreach (rTile, _ in townRoads) {
        if (AIMap.DistanceManhattan(rTile, cTile) > 5) continue;
        foreach (d in dirs) {
          local depotTile = rTile + d;
          if (!AIMap.IsValidTile(depotTile) || (depotTile in forbidden)) continue;
          if (AITile.IsStationTile(depotTile) || !OpexRoadIsFlat(depotTile) || !AITile.IsBuildable(depotTile)) continue;
          local okRoad = AIRoad.BuildRoad(rTile, depotTile) || AIRoad.AreRoadTilesConnected(rTile, depotTile);
          if (!okRoad && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) okRoad = true;
          local okDepot = false;
          if (okRoad) {
            okDepot = AIRoad.BuildRoadDepot(depotTile, rTile);
            if (!okDepot && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) okDepot = true;
          }
          if (okRoad && okDepot) {
            testMode = null;
            return { tile = depotTile, front = rTile };
          }
        }
      }
    }
  }

  testMode = null;
  return null;
}

function OpexPlanFeederRoute(siteTown, siteAirport, townRoads = null)
{
  if (townRoads == null) {
    townRoads = OpexTownConnectedRoads(siteTown.tile, 600);
  }

  local trace = [];
  local targetRoad = null;
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];

  // Cas 1 : siteAirport est deja sur la voirie municipale connectee
  if ((siteAirport.tile in townRoads) || (siteAirport.front in townRoads)) {
    targetRoad = (siteAirport.tile in townRoads) ? siteAirport.tile : siteAirport.front;
    trace = [];
  } else {
    // Cas 2 : recherche BFS / A* du raccordement le plus court entre siteAirport.front et townRoads
    local cameFrom = {};
    cameFrom.rawset(siteAirport.front, siteAirport.front);
    local q = [siteAirport.front];
    local qi = 0;
    local found = null;
    local testMode = AITestMode();

    while (qi < q.len() && qi < 500) {
      local cur = q[qi++];
      if (cur in townRoads) {
        found = cur;
        break;
      }

      local candNxt = [];
      foreach (d in dirs) {
        local nxt = cur + d;
        if (!AIMap.IsValidTile(nxt) || (nxt in cameFrom)) continue;
        if (nxt == siteAirport.tile) continue;
        candNxt.append({ tile = nxt, dist = AIMap.DistanceManhattan(nxt, siteTown.tile) });
      }
      candNxt.sort(function(a, b) {
        if (a.dist < b.dist) return -1;
        if (a.dist > b.dist) return 1;
        return 0;
      });

      foreach (cEntry in candNxt) {
        local nxt = cEntry.tile;
        if (nxt in townRoads) {
          if (AIRoad.BuildRoad(cur, nxt) || AIRoad.AreRoadTilesConnected(cur, nxt)) {
            cameFrom.rawset(nxt, cur);
            found = nxt;
            break;
          }
        } else {
          if (AITile.IsStationTile(nxt)) continue;
          if (!AITile.IsBuildable(nxt) && !AIRoad.IsRoadTile(nxt)) continue;
          if (AIRoad.BuildRoad(cur, nxt) || AIRoad.AreRoadTilesConnected(cur, nxt)) {
            cameFrom.rawset(nxt, cur);
            q.append(nxt);
          }
        }
      }
      if (found != null) break;
    }
    testMode = null;

    if (found == null) return null;

    local t = found;
    while (t != siteAirport.front) {
      local p = cameFrom[t];
      trace.insert(0, { from = p, to = t });
      t = p;
    }
    targetRoad = found;
  }

  local depot = OpexFindFeederDepot(siteTown, siteAirport, trace, targetRoad, townRoads);
  if (depot == null) return null;

  local routeDist = trace.len() + AIMap.DistanceManhattan(siteTown.tile, targetRoad);
  if (routeDist < 1) routeDist = 1;

  return {
    trace = trace,
    depot = depot,
    targetRoad = targetRoad,
    driveThrough = true,
    routeDistance = routeDist,
  };
}

function OpexBuildFeederCandidates(catalog, lines)
{
  /* Sanctuarisation de la phase de croissance aerienne primaire : aucun feeder avant 1973 (post-1972).
   * Mesure smoke 5 (results/v139_smoke5_2x3_20261009*) : a 3 ans (1970-1972), le rabattement devie
   * 170k+ £ de capital et des slots d'ordonnancement critiques de l'expansion aerienne primaire (ROI 2 000),
   * creusant un ecart de -20 avions et -584k £/an sur graine 42. Les feeders s'activent apres 1972 (annee 4+)
   * une fois le reseau aerien etabli (>35 aeroports, >50 avions, tresorerie saturee >1 M£). */
  local currentYear = AIDate.GetYear(AIDate.GetCurrentDate());
  if (currentYear <= 1972) return [];
  if (catalog == null || catalog.roadType < 0 || catalog.roadEngineByCargo == null || !(catalog.paxCargo in catalog.roadEngineByCargo)) return [];
  local busEngine = catalog.roadEngineByCargo[catalog.paxCargo];
  if (busEngine == null) return [];

  local candidates = [];
  local feederAirports = {};
  if (lines != null) {
    foreach (line in lines) {
      if (line != null && ("mode" in line) && line.mode == "road"
          && ("isFeeder" in line) && line.isFeeder
          && ("airportStationId" in line)) {
        feederAirports.rawset(line.airportStationId, true);
      }
    }
  }

  local stList = AIStationList(AIStation.STATION_AIRPORT);

  for (local stId = stList.Begin(); !stList.IsEnd(); stId = stList.Next()) {
    if (!AIStation.IsValidStation(stId)) continue;
    if (stId in feederAirports) {
      OpexV139LogSkip(stId, "already_has_feeder");
      continue;
    }

    local airportTiles = AITileList_StationType(stId, AIStation.STATION_AIRPORT);
    if (airportTiles.IsEmpty()) continue;
    local airportTile = airportTiles.Begin();
    local airportType = AIAirport.GetAirportType(airportTile);
    local townId = AIStation.GetNearestTown(stId);
    if (!AITown.IsValidTown(townId)) continue;
    local townCenter = AITown.GetLocation(townId);

    // 1. Couverture du centre-ville par l'infrastructure aeroportuaire elle-meme uniquement
    // Seul le centre couvert par l'aeroport lui-meme justifie le skip
    if (OpexAirportIsTownCenterCovered(airportTile, airportType, townCenter)) {
      OpexV139LogSkip(stId, "town_covered");
      continue;
    }

    // 2. Couverture globale de la station (aeroport + arrets joints)
    local stationCoverage = OpexStationCoverageTiles(stId);

    // 3. Decision Utilisateur (5) : arret joint au centre-ville a delier (V139_UNJOIN)
    local joinedStop = OpexFindTownJoinedStop(stId, airportTile, townId, townCenter);
    local siteTown = null;
    local isUnjoined = false;

    if (joinedStop != null) {
      siteTown = {
        tile = joinedStop.tile,
        front = joinedStop.front,
        isUnjoined = true,
        needsUnjoin = true,
        uncoveredPax = AITile.GetCargoProduction(joinedStop.tile, catalog.paxCargo, 1, 1, 3)
      };
      isUnjoined = true;
    } else {
      // Aucun arret joint existant : recherche d'un site neuf hors couverture globale (Cas 4)
      siteTown = OpexFindTownFeederStopSite(townCenter, townId, catalog, airportTile, stationCoverage);
      if (siteTown == null) {
        OpexV139LogSkip(stId, "low_marginal_gain");
        continue;
      }
      siteTown.isUnjoined <- false;
      siteTown.needsUnjoin <- false;
    }

    // 3. Identifier la voirie municipale connectee
    local townRoads = OpexTownConnectedRoads(siteTown.tile, 600);

    // 4. Enumerer les sites d'arrets potentiels A L'AEROPORT
    local airportSites = OpexFindAirportFeederStopSites(stId, airportTile, airportType, townCenter);
    if (airportSites.len() == 0) {
      OpexV139LogSkip(stId, "no_airport_site");
      continue;
    }

    // 5. Planifier le trace et le depot
    local bestPlan = null;
    local bestSiteAirport = null;
    foreach (siteCand in airportSites) {
      if (siteCand.tile == siteTown.tile) continue;
      if (AIMap.DistanceManhattan(siteTown.tile, siteCand.tile) < 3) continue;
      local plan = OpexPlanFeederRoute(siteTown, siteCand, townRoads);
      if (plan != null) {
        bestPlan = plan;
        bestSiteAirport = siteCand;
        break;
      }
    }

    if (bestPlan == null) {
      OpexV139LogSkip(stId, "no_route_or_depot");
      continue;
    }

    // 6. Plafond raisonnable de bus (1 ou 2, max 3)
    local pop = AITown.GetPopulation(townId);
    local busCount = (pop >= 1000) ? 2 : 1;
    if (pop >= 3000) busCount = 3;

    // 7. Modele economique corrige (confrontation smoke 2)
    local busSpeed = ("speed" in busEngine && busEngine.speed > 0) ? busEngine.speed : 40;
    local oneWayDays = (bestPlan.routeDistance.tofloat() / (0.036 * busSpeed)).tointeger();
    if (oneWayDays < 1) oneWayDays = 1;
    local roundTripDays = 2 * oneWayDays + 4;
    local tripsPerYear = (365 / roundTripDays).tointeger();
    local busCap = ("capacity" in busEngine && busEngine.capacity > 0) ? busEngine.capacity : 30;
    local maxAnnualPax = busCount * busCap * tripsPerYear;

    local annualPax = 0;
    local airFare = AICargo.GetCargoIncome(catalog.paxCargo, 200, 20);
    if (airFare <= 0) airFare = 45;

    local busFare = AICargo.GetCargoIncome(catalog.paxCargo, bestPlan.routeDistance, oneWayDays);
    if (busFare < 2) busFare = 2;

    local extraRevenue = 0;
    local busRunCost = ("runningCost" in busEngine) ? busEngine.runningCost : 1000;
    local runningAnnual = busCount * busRunCost;

    if (isUnjoined) {
      // Arret delie : gain = credits transfert + allongement du trajet paye + gain note/frequence
      local stopPaxProd = siteTown.uncoveredPax;
      if (stopPaxProd <= 0) stopPaxProd = 15;
      annualPax = stopPaxProd * 8 * 12;
      if (annualPax > maxAnnualPax) annualPax = maxAnnualPax;
      if (annualPax < 250) annualPax = 250;

      local transferRev = annualPax * busFare;
      local elongationFare = AICargo.GetCargoIncome(catalog.paxCargo, bestPlan.routeDistance, 5);
      if (elongationFare < 2) elongationFare = 2;
      local elongationRev = annualPax * elongationFare;

      local extraPaxAir = (annualPax * 0.25).tointeger();
      local airMargin = (extraPaxAir * (airFare * 0.3)).tointeger();

      extraRevenue = transferRev + elongationRev + airMargin;
    } else {
      // Nouvelle couverture (Cas 4) : passagers reellement nouveaux
      local uncoveredPaxProd = siteTown.uncoveredPax;
      annualPax = uncoveredPaxProd * 8 * 12;
      if (annualPax > maxAnnualPax) annualPax = maxAnnualPax;
      if (annualPax < 200) annualPax = 200;

      local transferRev = annualPax * busFare;
      local airMargin = (annualPax * (airFare * 0.35)).tointeger();
      extraRevenue = transferRev + airMargin;
    }

    local netProfit = extraRevenue - runningAnnual;
    local minProfitThreshold = 1000;
    if (netProfit < minProfitThreshold) {
      OpexV139LogSkip(stId, "unprofitable (estim=" + netProfit + " threshold=" + minProfitThreshold + ")");
      continue;
    }

    local busPrice = ("price" in busEngine) ? busEngine.price : 2500;
    local infraCost = (bestSiteAirport.existing ? 1000 : 1800) + (bestPlan.trace.len() * 50);
    if (isUnjoined) infraCost += 400;
    local capital = busCount * busPrice + infraCost;
    local roi = (netProfit * 1000) / capital;

    OpexV139LogCandidate(stId, isUnjoined, netProfit, minProfitThreshold, capital, roi);

    local cand = {
      mode = "road",
      kind = "feeder",
      isFeeder = true,
      cargo = catalog.paxCargo,
      airportStationId = stId,
      airportTile = airportTile,
      townId = townId,
      townCenter = townCenter,
      src = stId,
      dst = townId,
      srcTown = townId,
      dstTown = townId,
      srcIndustry = -1,
      dstIndustry = -1,
      engine = busEngine,
      trains = busCount,
      vehiclesForVolume = busCount,
      roadBerthCapacity = 2,
      roadVehicleCap = busCount,
      carried = (annualPax / 12).tointeger(),
      monthly = (annualPax / 12).tointeger(),
      distance = bestPlan.routeDistance,
      iterations = bestPlan.routeDistance,
      capital = capital,
      revenueAnnual = extraRevenue,
      profitAnnual = netProfit,
      runningAnnual = runningAnnual,
      amortAnnual = 0,
      baseProfitAnnual = netProfit,
      baseRevenueAnnual = extraRevenue,
      baseRoi = roi,
      roi = roi,
      oneWayDays = oneWayDays,
      effectiveSpeed = busSpeed,
      ratio = (netProfit * 1000) / (bestPlan.routeDistance > 0 ? bestPlan.routeDistance : 1),
      plan = bestPlan,
      siteTown = siteTown,
      siteAirport = bestSiteAirport,
      isSubsidy = false,
      subsidyId = -1,
      isChain = false,
      isRoadExtension = false,
      capitalIsActual = false,
      originServed = false,
      turnoverBonus = 100,
      immobilise = 0,
      freightBonus = 100,
      isTransformer = false,
      chantierDays = 30,
      economics = null,
    };
    candidates.append(cand);
  }

  return candidates;
}

function OpexAI::_buildFeederRoute(catalog, budget, candidate)
{
  local plan = candidate.plan;
  local added = [];
  local built = [];
  local costs = AIAccounting();
  local stopTown = null;
  local unjoinedSuccess = false;

  local stopAirport = null;
  local depot = null;
  local unjoinedSuccess = false;

  // =========================================================================
  // ETAPE 0 : PRE-VERIFICATION COMPLETE EN TEST MODE
  // Aucune action reelle (Remove/Build) n'est effectuee si la suite echoue ici.
  // =========================================================================
  {
    local testMode = AITestMode();
    local precheckOk = true;
    local precheckReason = "";

    // 0a. Verification de la route de raccord a l'aeroport (si requise)
    if (("needsRoad" in candidate.siteAirport) && candidate.siteAirport.needsRoad) {
      if (!AIRoad.BuildRoad(candidate.siteAirport.front, candidate.siteAirport.tile)
          && !AIRoad.AreRoadTilesConnected(candidate.siteAirport.front, candidate.siteAirport.tile)) {
        precheckOk = false;
        precheckReason = "test_airport_stub_failed";
      }
    }

    // 0b. Verification du trace de voirie
    if (precheckOk && plan.trace.len() > 0) {
      foreach (edge in plan.trace) {
        if (!AIRoad.BuildRoad(edge.from, edge.to)
            && !AIRoad.AreRoadTilesConnected(edge.from, edge.to)) {
          precheckOk = false;
          precheckReason = "test_trace_failed";
          break;
        }
      }
    }

    // 0c. Verification de l'arret a l'aeroport (si nouveau)
    if (precheckOk && !candidate.siteAirport.existing) {
      if (!AIRoad.BuildDriveThroughRoadStation(candidate.siteAirport.tile, candidate.siteAirport.front,
                                               AIRoad.ROADVEHTYPE_BUS, candidate.airportStationId)) {
        precheckOk = false;
        precheckReason = "test_airport_stop_failed";
      }
    }

    // 0d. Verification du depot
    if (precheckOk) {
      local okDepotRoad = AIRoad.BuildRoad(plan.depot.front, plan.depot.tile)
                          || AIRoad.AreRoadTilesConnected(plan.depot.front, plan.depot.tile);
      local okDepotBuild = okDepotRoad && AIRoad.BuildRoadDepot(plan.depot.tile, plan.depot.front);
      if (!okDepotBuild) {
        precheckOk = false;
        precheckReason = "test_depot_failed";
      }
    }

    // 0e. Verification de faisabilite de l'arret en ville
    if (precheckOk) {
      if (("needsUnjoin" in candidate.siteTown) && candidate.siteTown.needsUnjoin) {
        if (!(candidate.siteTown.tile in V139_UNJOINED_STOPS)) {
          if (!AIRoad.RemoveRoadStation(candidate.siteTown.tile)) {
            precheckOk = false;
            precheckReason = "test_unjoin_remove_failed";
          }
        }
      } else {
        if (!AIRoad.BuildDriveThroughRoadStation(candidate.siteTown.tile, candidate.siteTown.front,
                                                 AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW)) {
          precheckOk = false;
          precheckReason = "test_town_stop_failed";
        }
      }
    }

    testMode = null;

    if (!precheckOk) {
      return { ok = false, reason = precheckReason };
    }
  }

  // =========================================================================
  // ETAPE 1 : CONSTRUCTION DE L'INFRASTRUCTURE AEROPORT, TRACE ET DEPOT D'ABORD
  // L'arret du centre-ville joint a l'aeroport reste 100% INTACT tant que la suite
  // n'est pas construite et confirmee avec succes !
  // =========================================================================

  // 1a. Pose de la route de raccord a l'aeroport si requise
  if (("needsRoad" in candidate.siteAirport) && candidate.siteAirport.needsRoad) {
    local stubAir = AIRoad.BuildRoad(candidate.siteAirport.front, candidate.siteAirport.tile);
    if (!stubAir && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(candidate.townId, 800, 40);
      stubAir = AIRoad.BuildRoad(candidate.siteAirport.front, candidate.siteAirport.tile);
    }
    if (!stubAir && !AIRoad.AreRoadTilesConnected(candidate.siteAirport.front, candidate.siteAirport.tile)) {
      OpexRoadRollback(null, null, null, built, added);
      return { ok = false, reason = "airport_stub_failed" };
    }
    added.append({ from = candidate.siteAirport.front, to = candidate.siteAirport.tile });
  }

  // 1b. Trace de voirie (liaison entre aeroport et voirie municipale)
  if (plan.trace.len() > 0) {
    if (!OpexRoadBuildTrace(plan.trace, added)) {
      if (AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
        OpexBoostTownRating(candidate.townId, 800, 40);
        if (!OpexRoadBuildTrace(plan.trace, added)) {
          OpexRoadRollback(null, null, null, built, added);
          return { ok = false, reason = "trace_failed" };
        }
      } else {
        OpexRoadRollback(null, null, null, built, added);
        return { ok = false, reason = "trace_failed" };
      }
    }
  }

  // 1c. Arret de bus a l'aeroport (reutilise ou pose en station join)
  if (candidate.siteAirport.existing) {
    stopAirport = candidate.siteAirport.tile;
  } else {
    local okAir = AIRoad.BuildDriveThroughRoadStation(candidate.siteAirport.tile, candidate.siteAirport.front,
                                                     AIRoad.ROADVEHTYPE_BUS, candidate.airportStationId);
    if (!okAir && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(candidate.townId, 800, 40);
      okAir = AIRoad.BuildDriveThroughRoadStation(candidate.siteAirport.tile, candidate.siteAirport.front,
                                                 AIRoad.ROADVEHTYPE_BUS, candidate.airportStationId);
    }
    if (!okAir) {
      OpexRoadRollback(null, null, null, built, added);
      return { ok = false, reason = "airport_stop_failed" };
    }
    stopAirport = candidate.siteAirport.tile;
  }

  // 1d. Depot routier
  AIRoad.BuildRoad(plan.depot.front, plan.depot.tile);
  local stubDepot = AIRoad.AreRoadTilesConnected(plan.depot.front, plan.depot.tile);
  if (!stubDepot && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
    OpexBoostTownRating(candidate.townId, 800, 40);
    AIRoad.BuildRoad(plan.depot.front, plan.depot.tile);
    stubDepot = AIRoad.AreRoadTilesConnected(plan.depot.front, plan.depot.tile);
  }
  if (stubDepot) added.append({ from = plan.depot.front, to = plan.depot.tile });
  local depotOk = stubDepot && AIRoad.BuildRoadDepot(plan.depot.tile, plan.depot.front);
  if (!depotOk && stubDepot && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
    OpexBoostTownRating(candidate.townId, 800, 40);
    depotOk = AIRoad.BuildRoadDepot(plan.depot.tile, plan.depot.front);
  }
  if (!depotOk) {
    OpexRoadRollback(null, candidate.siteAirport.existing ? null : stopAirport, null, built, added);
    return { ok = false, reason = "depot_failed" };
  }
  depot = plan.depot.tile;

  // =========================================================================
  // ETAPE 2 : DELIER EN DERNIER (ARRET EN VILLE)
  // L'infrastructure route/aeroport/depot etant pleinement validee et construite,
  // on ne delie l'arret centre-ville qu'a cet instant precis !
  // =========================================================================
  if (("needsUnjoin" in candidate.siteTown) && candidate.siteTown.needsUnjoin) {
    local unjoinTile = candidate.siteTown.tile;
    local unjoinFront = candidate.siteTown.front;
    if (unjoinTile in V139_UNJOINED_STOPS) {
      // Arret deja delie precedemment et persiste : ne JAMAIS re-delier !
      stopTown = unjoinTile;
      unjoinedSuccess = true;
    } else {
      // Delier UNE fois : Remove puis Build DRIVE_THROUGH en STATION_NEW
      AIRoad.RemoveRoadStation(unjoinTile);
      local okRebuild = AIRoad.BuildDriveThroughRoadStation(unjoinTile, unjoinFront,
                                                          AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
      if (!okRebuild && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
        OpexBoostTownRating(candidate.townId, 800, 40);
        okRebuild = AIRoad.BuildDriveThroughRoadStation(unjoinTile, unjoinFront,
                                                        AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
      }
      if (!okRebuild) {
        // Echec de reconstruction en station neuve : restaurer immediatement l'arret joint
        AIRoad.BuildDriveThroughRoadStation(unjoinTile, unjoinFront,
                                            AIRoad.ROADVEHTYPE_BUS, candidate.airportStationId);
        AILog.Info("V139_UNJOIN airport=" + candidate.airportStationId + " tile=" + unjoinTile + " ok=0");
        OpexRoadRollback(null, candidate.siteAirport.existing ? null : stopAirport, depot, built, added);
        return { ok = false, reason = "unjoin_rebuild_failed" };
      }
      AILog.Info("V139_UNJOIN airport=" + candidate.airportStationId + " tile=" + unjoinTile + " ok=1");
      V139_UNJOINED_STOPS.rawset(unjoinTile, candidate.airportStationId);
      stopTown = unjoinTile;
      unjoinedSuccess = true;
    }
  } else {
    // Pose neuve en ville (sans deliaison)
    local okTown = AIRoad.BuildDriveThroughRoadStation(candidate.siteTown.tile, candidate.siteTown.front,
                                                      AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
    if (!okTown && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(candidate.townId, 800, 40);
      okTown = AIRoad.BuildDriveThroughRoadStation(candidate.siteTown.tile, candidate.siteTown.front,
                                                  AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
    }
    if (!okTown) {
      OpexRoadRollback(null, candidate.siteAirport.existing ? null : stopAirport, depot, built, added);
      return { ok = false, reason = "town_stop_failed" };
    }
    stopTown = candidate.siteTown.tile;
  }

  // =========================================================================
  // ETAPE 3 : VEHICULES ET ORDRES
  // =========================================================================
  local first = AIVehicle.BuildVehicleWithRefit(depot, candidate.engine.id, candidate.cargo);
  if (!AIVehicle.IsValidVehicle(first)) {
    if (unjoinedSuccess && (stopTown in V139_UNJOINED_STOPS)) {
      delete V139_UNJOINED_STOPS[stopTown];
      AIRoad.RemoveRoadStation(stopTown);
      AIRoad.BuildDriveThroughRoadStation(stopTown, candidate.siteTown.front, AIRoad.ROADVEHTYPE_BUS, candidate.airportStationId);
    } else if (!("needsUnjoin" in candidate.siteTown) || !candidate.siteTown.needsUnjoin) {
      AIRoad.RemoveRoadStation(stopTown);
    }
    OpexRoadRollback(null, candidate.siteAirport.existing ? null : stopAirport, depot, built, added);
    return { ok = false, reason = "vehicle_failed" };
  }
  built.append(first);

  local nonstopFlag = C53_ORDER_NONSTOP ? AIOrder.OF_NON_STOP_INTERMEDIATE : 0;
  local okOrd1 = AIOrder.AppendOrder(first, stopTown, nonstopFlag | AIOrder.OF_NONE);
  local okOrd2 = AIOrder.AppendOrder(first, stopAirport, nonstopFlag | AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD);
  if (!okOrd1 || !okOrd2) {
    if (unjoinedSuccess && (stopTown in V139_UNJOINED_STOPS)) {
      delete V139_UNJOINED_STOPS[stopTown];
      AIRoad.RemoveRoadStation(stopTown);
      AIRoad.BuildDriveThroughRoadStation(stopTown, candidate.siteTown.front, AIRoad.ROADVEHTYPE_BUS, candidate.airportStationId);
    } else if (!("needsUnjoin" in candidate.siteTown) || !candidate.siteTown.needsUnjoin) {
      AIRoad.RemoveRoadStation(stopTown);
    }
    OpexRoadRollback(null, candidate.siteAirport.existing ? null : stopAirport, depot, built, added);
    return { ok = false, reason = "orders_failed" };
  }

  for (local i = 1; i < candidate.trains; i++) {
    local extra = AIVehicle.CloneVehicle(depot, first, true);
    if (!AIVehicle.IsValidVehicle(extra)) break;
    built.append(extra);
  }

  local startFailed = false;
  foreach (v in built) {
    if (!AIVehicle.StartStopVehicle(v)) {
      startFailed = true;
      break;
    }
  }
  if (startFailed) {
    if (unjoinedSuccess && (stopTown in V139_UNJOINED_STOPS)) {
      delete V139_UNJOINED_STOPS[stopTown];
      AIRoad.RemoveRoadStation(stopTown);
      AIRoad.BuildDriveThroughRoadStation(stopTown, candidate.siteTown.front, AIRoad.ROADVEHTYPE_BUS, candidate.airportStationId);
    } else if (!("needsUnjoin" in candidate.siteTown) || !candidate.siteTown.needsUnjoin) {
      AIRoad.RemoveRoadStation(stopTown);
    }
    OpexRoadRollback(null, candidate.siteAirport.existing ? null : stopAirport, depot, built, added);
    return { ok = false, reason = "start_failed" };
  }

  return {
    ok = true,
    actualCost = costs.GetCosts(),
    vehicles = built,
    stopTown = stopTown,
    stopAirport = stopAirport,
    depot = depot,
  };
}

function OpexAI::_tryBuildFeederProject(year, project, rank, passDiscards, anchor, yy)
{
  local candidate = project.payload;
  local abandonedKey = OpexAbandonedPairKey(candidate);
  if (ABANDON_GEN_FILTER && ABANDON_MEMORY && this._abandonedPairs != null && (abandonedKey in this._abandonedPairs)) {
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
      passDiscards.append({ rank = rank, mode = "road", src = candidate.src, dst = candidate.dst,
                            reason = "abandoned_pair", extra = "" });
    }
    return { outcome = "rejected", discards = passDiscards };
  }

  local need = candidate.capital + OpexCashReserve() + ROAD_CAPITAL_MARGIN;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    OpexV139LogSkip(candidate.airportStationId, "insufficient_cash");
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
      passDiscards.append({ rank = rank, mode = "road", src = candidate.src, dst = candidate.dst,
                            reason = "insufficient_cash", extra = "need=" + need + " cash=" + money });
    }
    return { outcome = "rejected", discards = passDiscards };
  }

  local result = this._buildFeederRoute(this._catalog, this._budget, candidate);
  if (!result.ok) {
    OpexV139LogSkip(candidate.airportStationId, result.reason);
    if (ABANDON_MEMORY && this._abandonedPairs != null) {
      this._markPairAbandoned(abandonedKey);
    }
    this._hadAbandonsThisPass = true;
    if (DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL) {
      passDiscards.append({ rank = rank, mode = "road", src = candidate.src, dst = candidate.dst,
                            reason = "feeder_build_failed", extra = result.reason });
    }
    return { outcome = "rejected", discards = passDiscards };
  }

  local line = {
    lineId = this._nextLineId,
    mode = "road",
    kind = "feeder",
    isFeeder = true,
    airportStationId = candidate.airportStationId,
    townId = candidate.townId,
    stationA = result.stopTown,
    stationB = result.stopAirport,
    originA = candidate.src,
    originB = candidate.dst,
    cargo = candidate.cargo,
    predicted = candidate.profitAnnual,
    iterations = candidate.iterations,
    trains = result.vehicles.len(),
    trains0 = result.vehicles.len(),
    distance = candidate.distance,
    year = year,
    predRevenue = candidate.revenueAnnual,
    predRunning = candidate.runningAnnual,
    predAmort = candidate.amortAnnual,
    predCarried = candidate.carried,
    predVehiclesForVolume = candidate.vehiclesForVolume,
    predRoadBerthCapacity = candidate.roadBerthCapacity,
    predRoadVehicleCap = candidate.roadVehicleCap,
    predTrains = candidate.trains,
    predOneWayDays = candidate.oneWayDays,
    effectiveSpeed = candidate.effectiveSpeed,
    catalogSpeed = candidate.engine.speed,
    depot = result.depot,
    nStopsA = 1,
    nStopsB = 1,
    capacity = ("capacity" in candidate.engine && candidate.engine.capacity > 0) ? candidate.engine.capacity : 30,
    srcTown = candidate.townId,
    dstTown = candidate.townId,
    srcIndustry = -1,
    dstIndustry = -1,
    deadStreak = 0,
    scrapping = false,
    scrapVehicles = [],
    isLowRatio = false,
    opcodeRatio = -1,
    purpose = "profit",
    isSubsidy = false,
    subsidyId = -1,
    baseProfit = candidate.profitAnnual,
    baseRevenue = candidate.revenueAnnual,
    subsidyProfit = candidate.profitAnnual,
    subsidyRevenue = candidate.revenueAnnual,
    subsidyMultiplier = 1.0,
    c70Pred = candidate.profitAnnual,
    c70Real = 0,
  };
  this._lines.append(line);
  if (anchor != null) {
    OpexSign(anchor, "OF|" + this._nextLineId + "|" + candidate.revenueAnnual);
    OpexSign(anchor, "OJ|" + this._nextLineId + "|" + candidate.runningAnnual);
    OpexSign(anchor, "OT|" + this._nextLineId + "|" + candidate.oneWayDays + "|" + candidate.distance);
  }
  if (AIR0310_SITE_VALIDITY_CACHE) OpexAir0310InvalidateSiteValidity();

  AILog.Info("V139_FEEDER airport=" + candidate.airportStationId + " town=" + candidate.townId
             + " cost=" + result.actualCost + " buses=" + result.vehicles.len()
             + " estim=" + candidate.profitAnnual);
  this._nextLineId++;
  return { outcome = "built", discards = passDiscards };
}
