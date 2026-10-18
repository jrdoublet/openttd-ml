/* task_v265.nut — Prolongement d'une ligne ferroviaire par embranchement (modèle AAAHogEx).
 * Réglage : v265_branch_extension (défaut 0).
 * Modèle : AAAHogEx TrainRouteExtendBuilder (trainroute.nut:3161), CombineByFork (railbuilder.nut:930),
 * et anti-blocage de quai saturé (trainroute.nut:2385).
 * Au défaut 0, strictement aucun calcul n'est exécuté (coût d'opcodes nul).
 */

/* Vérifie si une tuile d'industrie est déjà couverte par une de nos gares ferroviaires. */
function OpexV265IndustryCoveredByTrain(industryTile)
{
  if (!AIMap.IsValidTile(industryTile)) return true;
  local stations = AIStationList(AIStation.STATION_TRAIN);
  for (local st = stations.Begin(); !stations.IsEnd(); st = stations.Next()) {
    if (AIStation.HasStationInCoverage(st, industryTile)) return true;
  }
  return false;
}

/* Vérifie si une ville a déjà une gare ferroviaire de notre compagnie. */
function OpexV265TownServedByTrain(townId)
{
  if (!AITown.IsValidTown(townId)) return true;
  local stations = AIStationList(AIStation.STATION_TRAIN);
  for (local st = stations.Begin(); !stations.IsEnd(); st = stations.Next()) {
    if (AIStation.GetNearestTown(st) == townId) return true;
  }
  return false;
}

/* Recherche un emplacement constructible pour une gare terminus simple à la nouvelle destination C.
 * Longueur bornée par la longueur de quai nominale (typiquement 3 tuiles, builder_rail.nut:2631). */
function OpexV265FindStationSite(centerTile, platformLength, railType)
{
  if (!AIMap.IsValidTile(centerTile)) return null;
  /* Rayon de recherche de site : 4 tuiles autour de l'industrie ou du centre-ville
   * (AIStation.GetCoverageRadius(AIStation.STATION_TRAIN) = 4, candidates.nut:352). */
  local searchRadius = 4;
  local centerX = AIMap.GetTileX(centerTile);
  local centerY = AIMap.GetTileY(centerTile);

  for (local dx = -searchRadius; dx <= searchRadius; dx++) {
    for (local dy = -searchRadius; dy <= searchRadius; dy++) {
      local t = AIMap.GetTileIndex(centerX + dx, centerY + dy);
      if (!AIMap.IsValidTile(t)) continue;
      if (AITile.GetSlope(t) != AITile.SLOPE_FLAT) continue;

      /* Essai dans les deux directions cardinales (X puis Y) */
      local dirs = [AIRail.RAILTRACK_NE_SW, AIRail.RAILTRACK_NW_SE];
      foreach (dir in dirs) {
        local step = (dir == AIRail.RAILTRACK_NE_SW) ? AIMap.GetTileIndex(1, 0) - AIMap.GetTileIndex(0, 0)
                                                     : AIMap.GetTileIndex(0, 1) - AIMap.GetTileIndex(0, 0);
        local canBuild = true;
        for (local k = 0; k < platformLength; k++) {
          local platTile = t + (step * k);
          if (!AIMap.IsValidTile(platTile) || !AITile.IsBuildable(platTile) || AITile.GetSlope(platTile) != AITile.SLOPE_FLAT) {
            canBuild = false;
            break;
          }
        }
        if (canBuild) {
          local exitTile = t + (step * platformLength);
          if (AIMap.IsValidTile(exitTile) && AITile.IsBuildable(exitTile)) {
            return { anchor = t, direction = dir, step = step, length = platformLength, station_exit = exitTile };
          }
        }
      }
    }
  }
  return null;
}

/* Pose un tracé direct simple entre le point de bifurcation et la gare C sous ATestMode ou AIExecMode. */
function OpexV265BuildBranchTrack(fromTile, toTile)
{
  if (!AIMap.IsValidTile(fromTile) || !AIMap.IsValidTile(toTile)) return false;
  local cur = fromTile;
  local maxSteps = 100;
  local steps = 0;

  while (cur != toTile && steps < maxSteps) {
    steps++;
    local curX = AIMap.GetTileX(cur);
    local curY = AIMap.GetTileY(cur);
    local toX = AIMap.GetTileX(toTile);
    local toY = AIMap.GetTileY(toTile);
    local nextTile = cur;

    if (curX < toX) nextTile = AIMap.GetTileIndex(curX + 1, curY);
    else if (curX > toX) nextTile = AIMap.GetTileIndex(curX - 1, curY);
    else if (curY < toY) nextTile = AIMap.GetTileIndex(curX, curY + 1);
    else if (curY > toY) nextTile = AIMap.GetTileIndex(curX, curY - 1);

    if (!AIMap.IsValidTile(nextTile)) return false;
    if (!AIRail.IsRailTile(nextTile) && !AITile.IsBuildable(nextTile)) return false;

    local ok = AIRail.BuildRail(cur, cur, nextTile);
    if (!ok && !AIRail.AreTilesConnected(cur, cur, nextTile)) return false;
    cur = nextTile;
  }
  return cur == toTile;
}

/* Anti-blocage en gare commune ou terminus (modèle AAAHogEx trainroute.nut:2385).
 * Lorsqu'une gare partagée a tous ses quais occupés par des convois à l'arrêt,
 * renvoie le premier convoi au dépôt pour libérer le quai et éviter le blocage face-à-face.
 */
function OpexAI::_v265AntiBlockStep()
{
  if (!V265_BRANCH_EXTENSION) return;
  if (this._lines == null || this._lines.len() == 0) return;

  foreach (line in this._lines) {
    if (line == null || !("v265Branched" in line) || !line.v265Branched) continue;
    if (!("stationA" in line) || line.stationA == null) continue;

    local stA = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(stA)) continue;

    local srcStationStops = [];
    if ("vehicles" in line && line.vehicles != null) {
      foreach (v in line.vehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;
        local loc = AIVehicle.GetLocation(v);
        if (AIMap.IsValidTile(loc) && AIStation.GetStationID(loc) == stA) {
          if (AIVehicle.GetState(v) == AIVehicle.VS_AT_STATION) {
            srcStationStops.append(v);
          }
        }
      }
    }

    /* Nombre de quais effectifs à la station A (défaut 1 quai pour voie unique, 2 pour double voie). */
    local platformNum = (("doubleTrack" in line) && line.doubleTrack == 1) ? 2 : 1;

    /* Règle AAAHogEx trainroute.nut:2385 : si tous les quais sont saturés par des rames à l'arrêt */
    if (srcStationStops.len() >= platformNum && srcStationStops.len() > 0) {
      local vehToSend = srcStationStops[0];
      /* R22 (task_report.nut:818) : ne pas envoyer si un ordre dépôt est déjà actif pour ne pas le toggler */
      if (!AIOrder.IsGotoDepotOrder(vehToSend, AIOrder.ORDER_CURRENT)) {
        if (AIVehicle.SendVehicleToDepot(vehToSend)) {
          if (DECISION_LOG) {
            OpexDecide("V265_ANTIBLOCK", "action=send_depot line=" + line.lineId
                       + " station=" + stA + " vehicle=" + vehToSend
                       + " stopped=" + srcStationStops.len() + " platforms=" + platformNum);
          }
        }
      }
    }

    /* Décongestion réussie : si une rame est à l'arrêt au dépôt et qu'un quai s'est libéré, la relancer */
    if ("vehicles" in line && line.vehicles != null && srcStationStops.len() < platformNum) {
      foreach (v in line.vehicles) {
        if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsStoppedInDepot(v)) {
          if (AIVehicle.StartStopVehicle(v)) {
            if (DECISION_LOG) {
              OpexDecide("V265_ANTIBLOCK", "action=resume line=" + line.lineId + " vehicle=" + v);
            }
          }
        }
      }
    }
  }
}

/* Point d'entrée de dispatch de l'ordonnanceur. */
function OpexAI::_dispatchV265BranchExtension(task, year)
{
  if (!V265_BRANCH_EXTENSION) return false;
  return this._v265ScanAndBranchLine(year);
}

/* Recherche une opportunité de prolongation par embranchement et réalise la bifurcation. */
function OpexAI::_v265ScanAndBranchLine(year)
{
  if (!V265_BRANCH_EXTENSION) return false;

  /* Cadence de scan : trimestrielle (V265_BRANCH_SCAN_COOLDOWN_DAYS = 90) */
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v265LastMonth == ym) return false;
  this._v265LastMonth = ym;

  /* 1. Verrou temporel d'amorçage : sanctuarise le capital pour l'aérien en 1970-1971 (V149/V207) */
  if (year < OPEX_START_YEAR + 2) {
    if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=early_year year=" + year);
    return false;
  }

  /* 2. Condition de désendettement : aucun emprunt actif toléré */
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) {
    if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=loan loan=" + loan);
    return false;
  }

  /* 3. Slot de pathfinding A* libre : ne pas entrer en concurrence avec le portefeuille */
  if (this._railSearch != null || this._railExpansion != null) {
    if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=search_busy");
    return false;
  }

  /* 4. Solvabilité minimale : réserve d'aérien (V265_BRANCH_AIR_CAPITAL_GUARD) + OpexCashReserve() */
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local minRequired = V265_BRANCH_AIR_CAPITAL_GUARD + OpexCashReserve();
  if (money < minRequired) {
    if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=insufficient_cash min=" + minRequired + " cash=" + money);
    return false;
  }

  if (this._lines == null || this._lines.len() == 0 || this._catalog == null) return false;

  local candidateLine = null;
  local targetLocation = null;
  local targetEntityId = -1;
  local targetKind = "";

  /* Recherche d'une ligne éligible : rentable, active, non branchée */
  foreach (line in this._lines) {
    if (line == null) continue;
    if (!("mode" in line) || line.mode != "rail") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (("v265Branched" in line) && line.v265Branched) continue;
    if (!("platformA" in line) || !("platformB" in line) || line.platformA == null || line.platformB == null) continue;
    if (!("lastProfit" in line) || line.lastProfit <= 0) continue;
    if (!("cargo" in line) || line.cargo < 0) continue;

    local bounds = OpexCatalogBounds(this._catalog);
    local exitB = line.platformB.station_exit;
    if (!AIMap.IsValidTile(exitB)) continue;

    if (line.kind == "freight") {
      local indList = AIIndustryList_CargoAccepting(line.cargo);
      for (local ind = indList.Begin(); !indList.IsEnd(); ind = indList.Next()) {
        local indTile = AIIndustry.GetLocation(ind);
        if (OpexV265IndustryCoveredByTrain(indTile)) continue;
        local distB = AIMap.DistanceManhattan(exitB, indTile);
        local distA = AIMap.DistanceManhattan(line.platformA.station_exit, indTile);
        if (distB >= V265_MIN_BRANCH_TILES && distA <= bounds.railMax) {
          candidateLine = line;
          targetLocation = indTile;
          targetEntityId = ind;
          targetKind = "freight";
          break;
        }
      }
    } else if (line.kind == "pax") {
      local townList = AITownList();
      for (local town = townList.Begin(); !townList.IsEnd(); town = townList.Next()) {
        if (OpexV265TownServedByTrain(town)) continue;
        local townTile = AITown.GetLocation(town);
        local distB = AIMap.DistanceManhattan(exitB, townTile);
        local distA = AIMap.DistanceManhattan(line.platformA.station_exit, townTile);
        if (distB >= V265_MIN_BRANCH_TILES && distA <= bounds.railMax) {
          candidateLine = line;
          targetLocation = townTile;
          targetEntityId = town;
          targetKind = "pax";
          break;
        }
      }
    }
    if (candidateLine != null) break;
  }

  if (candidateLine == null) {
    if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=no_candidate");
    return false;
  }

  /* Point d'embranchement F : choisi au lead de la gare B ou sur la voie d'approche */
  local forkTile = candidateLine.platformB.lead;
  if (!AIMap.IsValidTile(forkTile)) forkTile = candidateLine.platformB.station_exit;

  local platLen = ("platformLength" in candidateLine) ? candidateLine.platformLength : 3;
  local railType = AIRail.GetCurrentRailType();

  /* Recherche du site de la gare terminus C */
  local siteC = OpexV265FindStationSite(targetLocation, platLen, railType);
  if (siteC == null) {
    if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=site_c_failed target=" + targetEntityId);
    return false;
  }

  if (DECISION_LOG) {
    OpexDecide("V265_CANDIDATE", "line=" + candidateLine.lineId + " cargo=" + candidateLine.cargo
               + " target=" + targetEntityId + " kind=" + targetKind
               + " fork=" + forkTile + " exit_c=" + siteC.station_exit);
  }

  /* Évaluation des coûts sous ATestMode */
  local estimatedCost = 0;
  {
    local testCost = AIAccounting();
    local testMode = AITestMode();
    local okStn = AIRail.BuildRailStation(siteC.anchor, siteC.direction, 1, siteC.length, AIStation.STATION_NEW);
    local okTrack = okStn && OpexV265BuildBranchTrack(forkTile, siteC.station_exit);
    estimatedCost = testCost.GetCosts();
    if (!okTrack) {
      if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=test_track_failed");
      return false;
    }
  }

  /* Garde financière stricte : devis + cash reserve + réserve d'achat avion */
  local totalNeed = estimatedCost + OpexCashReserve() + V265_BRANCH_AIR_CAPITAL_GUARD;
  if (money < totalNeed) {
    if (DECISION_LOG) OpexDecide("V265_SKIP", "reason=reserve_guard cost=" + estimatedCost + " cash=" + money + " need=" + totalNeed);
    return false;
  }

  /* Construction effective sous AIExecMode */
  local actualCosts = AIAccounting();
  local okStation = AIRail.BuildRailStation(siteC.anchor, siteC.direction, 1, siteC.length, AIStation.STATION_NEW);
  if (!okStation) {
    if (DECISION_LOG) OpexDecide("V265_BUILD_FAIL", "reason=station_build error=" + AIError.GetLastError());
    return false;
  }

  local newStationId = AIStation.GetStationID(siteC.anchor);
  local okBranchTrack = OpexV265BuildBranchTrack(forkTile, siteC.station_exit);
  if (!okBranchTrack) {
    /* Rollback gare C */
    for (local k = 0; k < siteC.length; k++) AITile.DemolishTile(siteC.anchor + (siteC.step * k));
    if (DECISION_LOG) OpexDecide("V265_BUILD_FAIL", "reason=track_build");
    return false;
  }

  /* Aiguillage sur la voie vive au point d'embranchement F */
  AIRail.BuildRail(candidateLine.platformB.station_exit, forkTile, siteC.station_exit);

  /* Protection par signaux PBS (modèle builder_rail.nut:2755 OpexTryBuildSignal) :
   * Les signaux sont posés sur les branches approchant le point d'aiguillage F,
   * jamais sur la tuile F elle-même (TracksOverlap). */
  local sig1 = OpexTryBuildSignal(siteC.station_exit, forkTile);
  local sig2 = OpexTryBuildSignal(candidateLine.platformB.station_exit, forkTile);

  /* Mise à jour des ordres de la rame pour desservir la nouvelle gare C prolongée
   * (modèle AAAHogEx ChangeDestination / InsertOrder trainroute.nut:1502) */
  if ("vehicles" in candidateLine && candidateLine.vehicles != null && candidateLine.vehicles.len() > 0) {
    local leadVeh = candidateLine.vehicles[0];
    if (AIVehicle.IsValidVehicle(leadVeh)) {
      local orderFlags = AIOrder.OF_NON_STOP_INTERMEDIATE | ((candidateLine.kind == "freight") ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY);
      AIOrder.InsertOrder(leadVeh, 2, siteC.station_exit, orderFlags);
    }
  }

  /* Enregistrement de l'état d'extension sur la ligne */
  candidateLine.v265Branched <- true;
  candidateLine.v265StationC <- siteC.station_exit;
  candidateLine.v265ForkTile <- forkTile;
  candidateLine.v265StationCId <- newStationId;

  local spent = actualCosts.GetCosts();
  if (DECISION_LOG) {
    OpexDecide("V265_BUILD", "line=" + candidateLine.lineId + " src=" + candidateLine.stationA
               + " old_dst=" + candidateLine.stationB + " new_dst=" + siteC.station_exit
               + " station_id=" + newStationId + " cost=" + spent);
    OpexDecide("V265_FORK", "line=" + candidateLine.lineId + " fork=" + forkTile + " pbs1=" + sig1 + " pbs2=" + sig2);
  }

  return true;
}
