/* v201_branches.nut — Branches fret sur tronc double inspirées de HogNet.
 *
 * Implémente :
 * 1. Jonctions à 4 branches sur tronc double V198 (côté source, distance >= 12 tuiles des deux gares,
 *    respect du sens des signaux uniques PBS_ONEWAY, rails et signaux PBS).
 * 2. Génération de candidats branche : industrie productrice non desservie à <= 60 tuiles de la jonction,
 *    même cargo (ou acceptée par la destination du tronc), kind "freight" avec branch=1.
 *    Devis = gare + branche courte ; profit prédit basé sur la distance réelle source->destination.
 *    Plafond 5 branches par tronc, plafond trains par gare de destination (v201_max_dest_trains).
 * 3. Dépôt de branche sur la boucle de gare source (pas de demi-tour pour aller au dépôt).
 * 4. Détection de trains bloqués dans la gorge de gare (vitesse = 0 depuis >= v201_stuck_days) :
 *    envoi au dépôt sans toggle intempestif, journalisation OpexDecide("V201", "step=stuck...").
 * 5. Rollback propre sans casser le tronc double.
 */

class OpexV201RightDivergeJunction {
  originTile = null;
  flipY = null;
  flipX = null;
  rotate = null;

  constructor(tile, flipY_ = false, flipX_ = false, rotate_ = false) {
    this.originTile = tile;
    this.flipY = flipY_;
    this.flipX = flipX_;
    this.rotate = rotate_;
  }

  function Transform(x, y) {
    local fx = rotate ? (flipY ? (-y)     : y)
                      : (flipX ? (-x + 1) : x);
    local fy = rotate ? (flipX ? (-x + 1) : x)
                      : (flipY ? (-y)      : y);
    return [fx, fy];
  }

  function TransformDir(dx, dy) {
    local fdx = rotate ? (flipY ? (-dy) : dy)
                       : (flipX ? (-dx) : dx);
    local fdy = rotate ? (flipX ? (-dx) : dx)
                       : (flipY ? (-dy) : dy);
    return [fdx, fdy];
  }

  function At(x, y) {
    local t = Transform(x, y);
    return AIMap.GetTileIndex(
      AIMap.GetTileX(originTile) + t[0],
      AIMap.GetTileY(originTile) + t[1]);
  }

  function BuildSignals(x, y, dx, dy, pbs) {
    local t  = Transform(x, y);
    local fx = t[0];
    local fy = t[1];
    local d  = TransformDir(dx, dy);
    local fdx = d[0];
    local fdy = d[1];
    local px = fx + fdx;
    local py = fy + fdy;
    local reflections = (rotate ? 1 : 0) + (flipX ? 1 : 0) + (flipY ? 1 : 0);
    if (reflections % 2 == 1) {
      local nx = -fdy;
      local ny =  fdx;
      fx += nx;
      fy += ny;
      px += nx;
      py += ny;
    }
    local sigTile = AIMap.GetTileIndex(AIMap.GetTileX(originTile) + fx, AIMap.GetTileY(originTile) + fy);
    local frontTile = AIMap.GetTileIndex(AIMap.GetTileX(originTile) + px, AIMap.GetTileY(originTile) + py);
    if (AIMap.IsValidTile(sigTile) && AIMap.IsValidTile(frontTile)) {
      if (AIRail.GetSignalType(sigTile, frontTile) != AIRail.SIGNALTYPE_NONE) {
        AIRail.RemoveSignal(sigTile, frontTile);
      }
      AIRail.BuildSignal(sigTile, frontTile, pbs);
    }
  }

  function GetRails() {
    return [
      // Branche entrant depuis l'ouest vers voie principale sens nord
      [[0,-1],[0,0],[1,0]],
      [[0,0],[1,0],[1,1]],
      [[1,0],[1,1],[2,1]],
      [[1,1],[2,1],[2,2]],
      // Branche sortant vers l'ouest depuis voie principale sens sud
      [[1,-1],[1,0],[2,0]],
      [[1,0],[2,0],[2,1]],
      [[2,0],[2,1],[3,1]],
      [[2,1],[3,1],[3,2]],
    ];
  }

  function GetRequiredTiles() {
    return [
      [0,-2],[0,-1],[0,0],[0,1],[0,2],
      [1,-2],[1,-1],[1,0],[1,1],[1,2],
      [2,0],[2,1],[2,2],
      [3,1],[3,2],
    ];
  }

  function CollectAndRemoveSignals() {
    local mapW = AIMap.GetMapSizeX();
    local saved = [];
    foreach (xy in GetRequiredTiles()) {
      local t = At(xy[0], xy[1]);
      if (!AIMap.IsValidTile(t) || !AIRail.IsRailTile(t)) continue;
      local neighbors = [t + 1, t - 1, t + mapW, t - mapW];
      foreach (nb in neighbors) {
        if (!AIMap.IsValidTile(nb)) continue;
        local stype = AIRail.GetSignalType(t, nb);
        if (stype != AIRail.SIGNALTYPE_NONE) {
          saved.push([t, nb, stype]);
          AIRail.RemoveSignal(t, nb);
        }
      }
    }
    return saved;
  }

  function RestoreSignals(saved) {
    if (saved == null) return;
    foreach (sig in saved) {
      if (AIMap.IsValidTile(sig[0]) && AIMap.IsValidTile(sig[1])) {
        AIRail.BuildSignal(sig[0], sig[1], sig[2]);
      }
    }
  }

  function Build(isTestMode = true) {
    foreach (xy in GetRequiredTiles()) {
      local t = At(xy[0], xy[1]);
      if (!AIMap.IsValidTile(t)) return false;
      if (!AITile.IsBuildable(t) && !AIRail.IsRailTile(t)) return false;
    }
    if (isTestMode) return true;

    local branchTiles = [
      At( 1, 1), At( 2, 1), At( 2, 2),
      At( 2, 0), At( 3, 1), At( 3, 2)
    ];
    if (!OpexTemplateCheckOrLevel(branchTiles, true)) return false;

    local savedSignals = CollectAndRemoveSignals();
    local builtRails = [];

    foreach (r in GetRails()) {
      local a = At(r[0][0], r[0][1]);
      local b = At(r[1][0], r[1][1]);
      local c = At(r[2][0], r[2][1]);
      if (!AIMap.IsValidTile(a) || !AIMap.IsValidTile(b) || !AIMap.IsValidTile(c)) {
        foreach (built in builtRails) AIRail.RemoveRail(built[0], built[1], built[2]);
        RestoreSignals(savedSignals);
        return false;
      }
      if (AIRail.BuildRail(a, b, c)) {
        builtRails.push([a, b, c]);
      } else if (AIError.GetLastError() == AIError.ERR_ALREADY_BUILT) {
        // Rail deja present sur le tronc
      } else {
        foreach (built in builtRails) AIRail.RemoveRail(built[0], built[1], built[2]);
        RestoreSignals(savedSignals);
        return false;
      }
    }

    local pbs = ("SIGNALTYPE_PBS_ONEWAY" in AIRail) ? AIRail.SIGNALTYPE_PBS_ONEWAY : AIRail.SIGNALTYPE_PBS;
    local pbsTwoWay = AIRail.SIGNALTYPE_PBS;
    BuildSignals(0, 2, 0, 1, pbs);
    BuildSignals(1, -1, 0, -1, pbs);
    BuildSignals(2, 1, 0, 1, pbsTwoWay);
    return true;
  }

  function GetBranchEndTile() {
    return At(3, 1);
  }

  function GetBranchPath() {
    return [At(3, 1), At(2, 1), At(2, 0), At(1, 0), At(1, -1)];
  }

  function GetInboundBranchPath() {
    return [At(2, 2), At(2, 1), At(1, 1), At(1, 0), At(0, 0), At(0, -1)];
  }
}

class OpexV201FourWayJunction {
  static function _IsLeftHandSide(pathDx, pathDy, parallelOffX, parallelOffY) {
    local rightX = -pathDy;
    local rightY = pathDx;
    return parallelOffX == rightX && parallelOffY == rightY;
  }

  static function _HasInvertedOneWaySignal(pathTiles, startIndex, endIndex) {
    local start = startIndex > 1 ? startIndex : 1;
    local maxEnd = pathTiles.len() - 2;
    local end = endIndex < maxEnd ? endIndex : maxEnd;
    for (local i = start; i <= end; i++) {
      local prev = pathTiles[i - 1];
      local tile = pathTiles[i];
      local next = pathTiles[i + 1];
      if (AIMap.DistanceManhattan(prev, tile) != 1 || AIMap.DistanceManhattan(tile, next) != 1) continue;
      local forwardSignal = AIRail.GetSignalType(tile, next);
      local backwardSignal = AIRail.GetSignalType(tile, prev);
      if ("SIGNALTYPE_PBS_ONEWAY" in AIRail) {
        if (forwardSignal == AIRail.SIGNALTYPE_NONE && backwardSignal == AIRail.SIGNALTYPE_PBS_ONEWAY) return true;
      }
    }
    return false;
  }

  static function GetWeightedPathDistances(tiles) {
    local dists = [];
    local total = 0.0;
    for (local i = 0; i < tiles.len(); i++) {
      if (i > 0) {
        local d = AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
        total += (d > 1) ? d : 1.0;
      }
      dists.push(total);
    }
    return dists;
  }

  static function TryBuildNearStation(mainTiles, parallelTiles, minDist, maxDist, nearSrc = true) {
    local p2Set = {};
    foreach (t in parallelTiles) p2Set[t] <- true;
    local weightedDistances = OpexV201FourWayJunction.GetWeightedPathDistances(mainTiles);
    local leftTile = -1;
    local rightTile = -1;
    local leftPath = null;
    local rightPath = null;
    local leftInboundPath = null;
    local rightInboundPath = null;
    local leftAllowedTiles = null;
    local rightAllowedTiles = null;
    local chosenOrigin = -1;

    for (local i = 2; i + 3 < mainTiles.len(); i++) {
      if (weightedDistances[i] < minDist) continue;
      if (weightedDistances[i] > maxDist) break;
      if (leftTile != -1 || rightTile != -1) break;

      local mm1 = mainTiles[i - 2];
      local m0 = mainTiles[i - 1];
      local m1 = mainTiles[i];
      local m2 = mainTiles[i + 1];
      local m3 = mainTiles[i + 2];
      local m4 = mainTiles[i + 3];

      local isNS = true;
      local dy = AIMap.GetTileY(m1) - AIMap.GetTileY(m0);
      if (AIMap.GetTileX(m1) != AIMap.GetTileX(m0) || dy == 0) isNS = false;
      if (AIMap.GetTileX(mm1) != AIMap.GetTileX(m0) || AIMap.GetTileY(mm1) - AIMap.GetTileY(m0) != -dy) isNS = false;
      if (AIMap.GetTileX(m2) != AIMap.GetTileX(m1) || AIMap.GetTileY(m2) - AIMap.GetTileY(m1) != dy) isNS = false;
      if (AIMap.GetTileX(m3) != AIMap.GetTileX(m2) || AIMap.GetTileY(m3) - AIMap.GetTileY(m2) != dy) isNS = false;
      if (AIMap.GetTileX(m4) != AIMap.GetTileX(m3) || AIMap.GetTileY(m4) - AIMap.GetTileY(m3) != dy) isNS = false;

      local isEW = true;
      local dx = AIMap.GetTileX(m1) - AIMap.GetTileX(m0);
      if (AIMap.GetTileY(m1) != AIMap.GetTileY(m0) || dx == 0) isEW = false;
      if (AIMap.GetTileY(mm1) != AIMap.GetTileY(m0) || AIMap.GetTileX(mm1) - AIMap.GetTileX(m0) != -dx) isEW = false;
      if (AIMap.GetTileY(m2) != AIMap.GetTileY(m1) || AIMap.GetTileX(m2) - AIMap.GetTileX(m1) != dx) isEW = false;
      if (AIMap.GetTileY(m3) != AIMap.GetTileY(m2) || AIMap.GetTileX(m3) - AIMap.GetTileX(m2) != dx) isEW = false;
      if (AIMap.GetTileY(m4) != AIMap.GetTileY(m3) || AIMap.GetTileX(m4) - AIMap.GetTileX(m3) != dx) isEW = false;

      if (!isNS && !isEW) continue;

      local offX = (dx == 0) ? 1 : 0;
      local offY = (dy == 0) ? 1 : 0;
      local offset = null;
      local parallelOk = true;

      foreach (mt in [m0, m1, m2, m3]) {
        local found = false;
        foreach (sign in [-1, 1]) {
          local candidate = AIMap.GetTileIndex(AIMap.GetTileX(mt) + sign * offX, AIMap.GetTileY(mt) + sign * offY);
          if (candidate in p2Set) {
            if (offset == null) offset = sign;
            if (sign == offset) { found = true; break; }
          }
        }
        if (!found) { parallelOk = false; break; }
      }
      if (!parallelOk || offset == null) continue;

      local parallelOffX = offset * offX;
      local parallelOffY = offset * offY;
      if (OpexV201FourWayJunction._IsLeftHandSide(dx, dy, parallelOffX, parallelOffY)) continue;
      if (OpexV201FourWayJunction._HasInvertedOneWaySignal(mainTiles, i - 2, i + 3)) continue;

      local levelOk = true;
      local baseHeight = AITile.GetMinHeight(m1);
      foreach (mt in [mm1, m0, m1, m2, m3]) {
        if (AITile.GetMinHeight(mt) != baseHeight) { levelOk = false; break; }
        local par = AIMap.GetTileIndex(AIMap.GetTileX(mt) + offset * offX, AIMap.GetTileY(mt) + offset * offY);
        if (!AIMap.IsValidTile(par) || AITile.GetMinHeight(par) != baseHeight) { levelOk = false; break; }
      }
      if (!levelOk) continue;

      local noBranchOk = true;
      foreach (mt in [mm1, m0, m4]) {
        local par = AIMap.GetTileIndex(AIMap.GetTileX(mt) + offset * offX, AIMap.GetTileY(mt) + offset * offY);
        foreach (t in [mt, par]) {
          if (!AIRail.IsRailTile(t)) continue;
          local tracks = AIRail.GetRailTracks(t);
          local expectedTrack = isNS ? AIRail.RAILTRACK_NW_SE : AIRail.RAILTRACK_NE_SW;
          if ((tracks & ~expectedTrack) != 0) { noBranchOk = false; break; }
        }
        if (!noBranchOk) break;
      }
      if (!noBranchOk) continue;

      local pm1 = AIMap.GetTileIndex(AIMap.GetTileX(m1) + offset * offX, AIMap.GetTileY(m1) + offset * offY);
      local minX = AIMap.GetTileX(m1) < AIMap.GetTileX(pm1) ? AIMap.GetTileX(m1) : AIMap.GetTileX(pm1);
      local minY = AIMap.GetTileY(m1) < AIMap.GetTileY(pm1) ? AIMap.GetTileY(m1) : AIMap.GetTileY(pm1);
      local origin = AIMap.GetTileIndex(minX, minY);
      local rotate = (dx != 0);
      local flipY = rotate ? (dx < 0) : (dy < 0);
      if (nearSrc) flipY = !flipY;

      // Essayer branche a droite (RightDivergeJunction)
      local rightJ = OpexV201RightDivergeJunction(origin, flipY, flipY, rotate);
      if (rightJ.Build(true)) {
        if (rightJ.Build(false)) {
          rightTile = rightJ.GetBranchEndTile();
          rightPath = rightJ.GetBranchPath();
          rightInboundPath = rightJ.GetInboundBranchPath();
          rightAllowedTiles = [];
          foreach (xy in rightJ.GetRequiredTiles()) rightAllowedTiles.append(rightJ.At(xy[0], xy[1]));
          chosenOrigin = origin;
        }
      }

      // Essayer branche a gauche (LeftDivergeJunction)
      local leftJ = OpexV201RightDivergeJunction(origin, flipY, !flipY, rotate);
      if (leftJ.Build(true)) {
        if (leftJ.Build(false)) {
          leftTile = leftJ.GetBranchEndTile();
          leftPath = leftJ.GetBranchPath();
          leftInboundPath = leftJ.GetInboundBranchPath();
          leftAllowedTiles = [];
          foreach (xy in leftJ.GetRequiredTiles()) leftAllowedTiles.append(leftJ.At(xy[0], xy[1]));
          chosenOrigin = origin;
        }
      }
    }

    return {
      originTile = chosenOrigin,
      leftTile = leftTile, rightTile = rightTile,
      leftPath = leftPath, rightPath = rightPath,
      leftInboundPath = leftInboundPath, rightInboundPath = rightInboundPath,
      leftAllowedTiles = leftAllowedTiles, rightAllowedTiles = rightAllowedTiles
    };
  }
}

/* Tente de poser une jonction a 4 branches sur le tronc V198 avant la mise en service des trains. */
function OpexV201TryBuildJunction(tiles1, tiles2, builtSrc, builtDst, platformLength)
{
  if (tiles1 == null || tiles2 == null) return null;
  local pathLen = tiles1.len();
  if (pathLen < 24) {
    if (DECISION_LOG) OpexDecide("V201", "step=junction ok=0 reason=TOO_SHORT len=" + pathLen);
    return null;
  }

  local jMinDist = 12;
  local jMaxDist = pathLen - 12;

  // Construire tiles2FromSrc : track retour ordonne depuis l'extremite source vers dest
  local tiles2FromSrc = [];
  for (local i = tiles2.len() - 1; i >= 0; i--) tiles2FromSrc.push(tiles2[i]);

  local result = OpexV201FourWayJunction.TryBuildNearStation(tiles2FromSrc, tiles1, jMinDist, jMaxDist, true);

  local srcToDestSet = {};
  foreach (t in tiles1) srcToDestSet[t] <- true;
  local legs = null;
  local chosenTile = -1;
  local chosenAllowed = null;

  if (result.leftTile != -1) {
    local ap = result.leftPath;
    local ip = result.leftInboundPath;
    if (ap != null && ip != null) {
      local deepestInbound = ip[ip.len() - 1];
      local deepestArm = ap[ap.len() - 1];
      if (deepestInbound in srcToDestSet) legs = { leg1Path = ip, leg2Path = ap };
      else if (deepestArm in srcToDestSet) legs = { leg1Path = ap, leg2Path = ip };
    }
    if (legs != null) {
      chosenTile = result.leftTile;
      chosenAllowed = result.leftAllowedTiles;
    }
  }

  if (legs == null && result.rightTile != -1) {
    local ap = result.rightPath;
    local ip = result.rightInboundPath;
    if (ap != null && ip != null) {
      local deepestInbound = ip[ip.len() - 1];
      local deepestArm = ap[ap.len() - 1];
      if (deepestInbound in srcToDestSet) legs = { leg1Path = ip, leg2Path = ap };
      else if (deepestArm in srcToDestSet) legs = { leg1Path = ap, leg2Path = ip };
    }
    if (legs != null) {
      chosenTile = result.rightTile;
      chosenAllowed = result.rightAllowedTiles;
    }
  }

  if (legs != null && chosenTile != -1) {
    local juncObj = {
      tile = result.originTile,
      mergeTile = chosenTile,
      leg1Path = legs.leg1Path,
      leg2Path = legs.leg2Path,
      allowedTiles = chosenAllowed,
      branchCount = 0
    };
    if (DECISION_LOG) {
      OpexDecide("V201", "step=junction ok=1 tile=" + result.originTile + " mergeTile=" + chosenTile);
    }
    return juncObj;
  }

  if (DECISION_LOG) {
    OpexDecide("V201", "step=junction ok=0 reason=NO_SITE");
  }
  return null;
}

/* Demolition propre des rails de jonction en cas d'echec aval sur le tronc. */
function OpexV201DemolishJunction(junc)
{
  if (junc == null) return;
  local selfCompany = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  if (("leg1Path" in junc) && junc.leg1Path != null) {
    foreach (t in junc.leg1Path) {
      if (AIMap.IsValidTile(t) && AITile.GetOwner(t) == selfCompany) {
        AIRail.RemoveRail(t, t, t);
      }
    }
  }
  if (("leg2Path" in junc) && junc.leg2Path != null) {
    foreach (t in junc.leg2Path) {
      if (AIMap.IsValidTile(t) && AITile.GetOwner(t) == selfCompany) {
        AIRail.RemoveRail(t, t, t);
      }
    }
  }
}

/* Generation des candidats branche vers une industrie non desservie proche de la jonction (<= 60 tuiles). */
function OpexV201BranchCandidates(catalog, lines, outCandidates, stats, abandonedPairs)
{
  if (lines == null || lines.len() == 0) return;
  local allIndustries = AIIndustryList();

  foreach (line in lines) {
    if (line.mode != "rail" || line.kind != "freight") continue;
    if (!("v201Junction" in line) || line.v201Junction == null) continue;
    local junc = line.v201Junction;

    local bCount = ("v201BranchCount" in line) ? line.v201BranchCount : 0;
    if (bCount >= 5) continue;

    local destTrains = 0;
    foreach (l in lines) {
      if (l.stationB == line.stationB) destTrains += l.trains;
    }
    if (destTrains >= V201_MAX_DEST_TRAINS) continue;

    local cargo = line.cargo;
    local dstInd = line.dstIndustry;
    local dstLoc = line.originB;
    local juncTile = junc.mergeTile;

    foreach (ind, _ in allIndustries) {
      local indLoc = AIIndustry.GetLocation(ind);
      if (OpexOriginServed(lines, indLoc, false)) continue;

      local matchCargo = -1;
      local indType = AIIndustry.GetIndustryType(ind);
      local produced = AIIndustryType.GetProducedCargo(indType);
      foreach (c, _ in produced) {
        if (c == cargo) { matchCargo = c; break; }
        if (AIIndustry.IsValidIndustry(dstInd)) {
          local accepted = AIIndustryType.GetAcceptedCargo(AIIndustry.GetIndustryType(dstInd));
          if (c in accepted) { matchCargo = c; break; }
        }
      }
      if (matchCargo == -1) continue;

      local monthly = AIIndustry.GetLastMonthProduction(ind, matchCargo);
      if (monthly <= 0) continue;

      local distJunc = AIMap.DistanceManhattan(indLoc, juncTile);
      if (distJunc > 60 || distJunc < 8) continue;

      local pairKey = OpexProjectPairKey("freight", matchCargo, indLoc, dstLoc);
      if (abandonedPairs != null && (pairKey in abandonedPairs)) continue;

      local realDist = AIMap.DistanceManhattan(indLoc, dstLoc);
      local loco = OpexGetEpochVehicle(AIVehicle.VT_RAIL, matchCargo);
      if (loco == null) continue;

      local wagons = ("wagons" in line) ? line.wagons : 3;
      local econ = OpexRailFixedConsist(catalog, matchCargo, realDist, "freight", loco, wagons);
      if (econ == null || econ.profitAnnual <= 0) continue;

      local currentRailType = AIRail.GetCurrentRailType();
      local trackCostPerTile = AIRail.GetBuildCost(currentRailType, AIRail.BT_TRACK);
      local branchTrackCost = 2 * distJunc * trackCostPerTile + 2000;
      local stationCost = 15000;
      local wagonPrice = (matchCargo in catalog.wagonByCargo) ? catalog.wagonByCargo[matchCargo].price : 0;
      local trainCost = loco.price + wagons * wagonPrice;
      local branchCapital = stationCost + branchTrackCost + trainCost;
      local roi = (branchCapital > 0) ? (econ.profitAnnual.tofloat() / branchCapital) : 0.0;

      local cand = {
        kind = "freight",
        branch = 1,
        v201Branch = true,
        cargo = matchCargo,
        src = indLoc,
        dst = dstLoc,
        srcIndustry = ind,
        dstIndustry = dstInd,
        distance = realDist,
        distJunc = distJunc,
        monthly = monthly,
        capital = branchCapital,
        profitAnnual = econ.profitAnnual,
        revenueAnnual = econ.revenueAnnual,
        runningAnnual = econ.runningAnnual,
        amortAnnual = econ.amortAnnual,
        roi = roi,
        loco = loco,
        wagons = wagons,
        platformLength = line.platformLength,
        trunkLine = line,
        trunkLineId = line.lineId,
        junction = junc,
        iterations = OpexRailIterations(distJunc),
        carried = econ.capacityAnnual,
        trains = 1,
        perTrain = econ.capacityAnnual,
        headwayDays = 30,
        stationRating = 70,
        trainsForHeadway = 1,
        oneWayDays = (realDist * 2),
        effectiveSpeed = loco.speed
      };

      if (DECISION_LOG) {
        OpexDecide("V201", "step=branch_cand ok=1 src=" + indLoc + " dst=" + dstLoc
                   + " trunk=" + line.lineId + " dist_junc=" + distJunc + " dist=" + realDist
                   + " capital=" + branchCapital + " profit=" + econ.profitAnnual + " roi=" + roi);
      }
      outCandidates.append(cand);
    }
  }
}

/* Construction de la ligne de branche courte jusqu'a la jonction du tronc double. */
function OpexV201ExecuteBranchPlan(catalog, budget, candidate, plan, cashReserve)
{
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = candidate.capital + cashReserve;
  if (money < need) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=CASH need=" + need + " money=" + money);
    return { ok = false, reason = "CASH" };
  }
  if (!OpexRailVehicleSlotAvailable()) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=NOTRAIN");
    return { ok = false, reason = "NOTRAIN" };
  }

  local trunkLine = candidate.trunkLine;
  local junc = candidate.junction;
  if (trunkLine == null || junc == null) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=TRUNK_LOST");
    return { ok = false, reason = "TRUNK_LOST" };
  }

  local bCount = ("v201BranchCount" in trunkLine) ? trunkLine.v201BranchCount : 0;
  if (bCount >= 5) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=MAX_BRANCHES branches=" + bCount);
    return { ok = false, reason = "MAX_BRANCHES" };
  }

  local pLen = candidate.platformLength;
  local srcTemplate = OpexFindSourceTemplateSite(catalog, candidate, pLen);
  if (srcTemplate == null) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=NOSRC");
    return { ok = false, reason = "NOSRC" };
  }

  local costs = AIAccounting();
  local searchCostV201 = 0;
  local builtSrc = OpexBuildSourceTemplateReal(srcTemplate);
  if (!builtSrc.ok) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=" + builtSrc.reason);
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = builtSrc.reason };
  }

  local leg1Start = junc.leg1Path[0];
  local leg1Next = junc.leg1Path[1];
  local plansA1 = [{ lead = builtSrc.depTile, station_exit = builtSrc.depPrev }];
  local plansB1 = [{ lead = leg1Start, station_exit = leg1Next }];
  local deadlineTick = AIController.GetTick() + 5000 + BUILD_TICK_MARGIN;
  local preCost1 = costs.GetCosts();
  local search1 = OpexV198ShieldedSearch(plansA1, plansB1, 5000, deadlineTick, null, null, 1, null);
  searchCostV201 += costs.GetCosts() - preCost1;

  if (search1.path == null || search1.path == false) {
    local stopReason = ("stop" in search1) ? search1.stop : "NOPA1";
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=" + stopReason);
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = stopReason };
  }

  local tiles1 = OpexResolveSearchTiles(search1);
  local structures1 = OpexResolveSearchStructures(search1);
  if (tiles1 == null || tiles1.len() < 3) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=SHORT1");
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = "SHORT1" };
  }

  local leg2Start = junc.leg2Path[0];
  local leg2Next = junc.leg2Path[1];
  local plansA2 = [{ lead = leg2Start, station_exit = leg2Next }];
  local plansB2 = [{ lead = builtSrc.arrTile, station_exit = builtSrc.arrNext }];

  local forbidden = {};
  foreach (t in tiles1) forbidden[t] <- true;
  foreach (t in builtSrc.allTiles) forbidden[t] <- true;
  if (leg2Start in forbidden) delete forbidden[leg2Start];
  if (builtSrc.arrTile in forbidden) delete forbidden[builtSrc.arrTile];
  if (builtSrc.arrNext in forbidden) delete forbidden[builtSrc.arrNext];

  local ignored2 = [];
  foreach (t, _ in forbidden) ignored2.append(t);
  local guideTiles = OpexV197BuildGuideTiles(tiles1, 1, forbidden);

  deadlineTick = AIController.GetTick() + 5000 + BUILD_TICK_MARGIN;
  local preCost2 = costs.GetCosts();
  local search2 = OpexV198ShieldedSearch(plansA2, plansB2, 5000, deadlineTick, ignored2, null, null, guideTiles);
  searchCostV201 += costs.GetCosts() - preCost2;

  if (search2.path == null || search2.path == false) {
    local stopReason = ("stop" in search2) ? search2.stop : "NOPA2";
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=" + stopReason);
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = stopReason };
  }

  local tiles2 = OpexResolveSearchTiles(search2);
  local structures2 = OpexResolveSearchStructures(search2);
  if (tiles2 == null || tiles2.len() < 3) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=SHORT2");
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = "SHORT2" };
  }

  local trackOpt1 = { isDouble = true, trainLength = pLen, initialBudget = 5000, accounting = costs, retrySearchCost = 0 };
  local fail1 = OpexBuildTrack(tiles1, structures1, null, trackOpt1);
  if (fail1 > 0) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=TRKFAIL1 failed=" + fail1);
    OpexDemolishTrack(tiles1);
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = "TRKFAIL1" };
  }

  if (V199_ROBUST_BUILD) {
    OpexV199RebuildForHomeward(tiles1, 1, V199_LEVEL_BUDGET_K);
  }

  local trackOpt2 = { isDouble = true, trainLength = pLen, initialBudget = 5000, accounting = costs, retrySearchCost = 0 };
  local fail2 = OpexBuildTrack(tiles2, structures2, null, trackOpt2);
  if (fail2 > 0) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=TRKFAIL2 failed=" + fail2);
    OpexDemolishTrack(tiles2);
    OpexDemolishTrack(tiles1);
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = "TRKFAIL2" };
  }

  OpexBuildBlockSignals(tiles1, OPEX_TEMPLATE_SIGNAL_INTERVAL);
  OpexBuildBlockSignals(tiles2, OPEX_TEMPLATE_SIGNAL_INTERVAL);

  local exitA = builtSrc.platformTile;
  local exitB = trunkLine.stationB;
  local trains = OpexBuildTrains(catalog, candidate.cargo, "freight", builtSrc.depotTile,
                                 exitA, exitB, 1, candidate.loco, candidate.wagons,
                                 pLen, true,
                                 OpexV163Cargo2(candidate), OpexV163Wagons2(candidate));
  if (trains.failed || trains.built == 0) {
    if (DECISION_LOG) OpexDecide("V201", "step=branch_build ok=0 reason=TRAINFAIL");
    if (("rollbackVehicles" in trains) && trains.rollbackVehicles != null) {
      foreach (v in trains.rollbackVehicles) {
        if (AIVehicle.IsValidVehicle(v)) AIVehicle.SellVehicle(v);
      }
    }
    if (("vehicles" in trains) && trains.vehicles != null) {
      foreach (v in trains.vehicles) {
        if (AIVehicle.IsValidVehicle(v)) AIVehicle.SellVehicle(v);
      }
    }
    OpexDemolishTrack(tiles2);
    OpexDemolishTrack(tiles1);
    OpexDemolishSourceTemplate(builtSrc);
    return { ok = false, reason = "TRAINFAIL" };
  }

  trunkLine.v201BranchCount <- bCount + 1;
  local actualCost = costs.GetCosts() - searchCostV201;

  if (DECISION_LOG) {
    OpexDecide("V201", "step=branch_build ok=1 branch_src=" + candidate.src
               + " trunk=" + trunkLine.lineId + " cost=" + actualCost
               + " branches=" + trunkLine.v201BranchCount);
  }

  return {
    ok = true,
    reason = "OK",
    trains = trains.built,
    vehicles = trains.vehicles,
    trainLength = trains.trainLength,
    locoLength = trains.locoLength,
    wagonLength = trains.wagonLength,
    error = trains.error,
    diag = trains.diag,
    actualCost = actualCost,
    capital = actualCost,
    stationA = builtSrc.platformTile,
    stationB = trunkLine.stationB,
    depot = builtSrc.depotTile,
    doubleTrack = 1,
    loop = 1,
    v181Loop = true,
    v201Branch = true,
    trunkLineId = trunkLine.lineId,
    platformA = { anchor = builtSrc.platformTile, length = pLen, direction = null, step = null,
                  station_exit = builtSrc.depPrev, lead = builtSrc.depTile },
    platformB = trunkLine.platformB,
    platformA2 = null,
    platformB2 = null,
    platformLength = pLen,
    wagons = candidate.wagons,
    wantedPlatformLength = pLen,
    plansA = 1,
    plansB = 1,
    slopeRelaxed = false,
    siteClear = true,
    siteCargo = true,
    siteCmd = true,
    siteKind = "F",
    iterations = candidate.iterations,
    opcodes = 0,
    tiles = tiles1,
    tiles2 = tiles2
  };
}

/* Detection et resolution des trains bloques dans la gorge de gare sur lignes V198/V201. */
function OpexV201CheckStuckTrains(lines, currentDate, stuckVehicles)
{
  if (lines == null || stuckVehicles == null) return;

  foreach (line in lines) {
    local isV198OrV201 = (("v201Branch" in line) && line.v201Branch)
                         || (("v198" in line) && line.v198)
                         || (("v201Junction" in line) && line.v201Junction != null);
    if (!isV198OrV201) continue;
    if (!("vehicles" in line) || line.vehicles == null) continue;

    local stIdA = ("stationA" in line && line.stationA != null) ? AIStation.GetStationID(line.stationA) : -1;
    local stIdB = ("stationB" in line && line.stationB != null) ? AIStation.GetStationID(line.stationB) : -1;

    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (AIVehicle.IsStoppedInDepot(v)) {
        if (v in stuckVehicles) delete stuckVehicles[v];
        continue;
      }

      local speed = AIVehicle.GetCurrentSpeed(v);
      if (speed > 0) {
        if (v in stuckVehicles) delete stuckVehicles[v];
        continue;
      }

      local loc = AIVehicle.GetLocation(v);
      local inThroat = false;
      if (AIMap.IsValidTile(loc)) {
        local locStId = AIStation.GetStationID(loc);
        if (locStId == stIdA || locStId == stIdB) {
          inThroat = true;
        } else {
          local distA = (line.stationA != null) ? AIMap.DistanceManhattan(loc, line.stationA) : 999;
          local distB = (line.stationB != null) ? AIMap.DistanceManhattan(loc, line.stationB) : 999;
          if (distA <= 3 || distB <= 3) inThroat = true;
        }
      }

      if (!inThroat) {
        if (v in stuckVehicles) delete stuckVehicles[v];
        continue;
      }

      if (!(v in stuckVehicles)) {
        stuckVehicles[v] <- { tile = loc, date = currentDate };
      } else {
        local entry = stuckVehicles[v];
        if (entry.tile != loc) {
          entry.tile = loc;
          entry.date = currentDate;
        } else {
          local days = currentDate - entry.date;
          if (days >= V201_STUCK_DAYS) {
            local halted = false;
            if (AIOrder.IsGotoDepotOrder(v, AIOrder.ORDER_CURRENT)) {
              local flags = AIOrder.GetOrderFlags(v, AIOrder.ORDER_CURRENT);
              halted = (flags == AIOrder.OF_INVALID) || ((flags & AIOrder.OF_STOP_IN_DEPOT) != 0);
            }
            if (!halted) {
              local sent = AIVehicle.SendVehicleToDepot(v);
              if (sent) {
                if (DECISION_LOG) {
                  OpexDecide("V201", "step=stuck ok=1 vehicle=" + v + " line=" + line.lineId + " days=" + days + " tile=" + loc);
                }
              } else {
                if (DECISION_LOG) {
                  OpexDecide("V201", "step=stuck ok=0 vehicle=" + v + " line=" + line.lineId + " days=" + days + " reason=SEND_FAIL");
                }
              }
            }
            entry.date = currentDate;
          }
        }
      }
    }
  }
}
