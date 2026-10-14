/* rail_templates.nut — Gabarits de gare d'AAAHogEx pour double voie V198
 *
 * Implémente :
 * 1. Gabarit source à boucle de retournement arrière (1 quai départ + 1 quai arrivée, longueur L)
 *    modélisé d'après AAAHogEx SrcRailStation (station.nut:4612-4830) :
 *    - 2 voies x=0 (départ) et x=2 (arrivée) séparées d'une tuile (x=1)
 *    - boucle arrière (0,1)-(0,0)-(1,0)-(2,0)-(2,1)
 *    - avant-gare avec rails fixes (bloc 'a') et dépôt sur la boucle source (1, L+2) ouvrant sur (2, L+2)
 *    - signaux PBS à sens unique (2,0) et (0,L)
 *    - points de raccord : arrivée [(2, L+3), (2, L+2)], départ [(0, L+2), (0, L+1)]
 * 2. Gabarit destination traversant (1 quai, longueur L)
 *    modélisé d'après AAAHogEx DestRailStation (station.nut:4057-4414) :
 *    - gare traversante à 1 quai
 *    - arrivée par un bout : [(0, 0), (0, 1)]
 *    - départ par l'autre bout : [(0, L+2), (0, L+1)]
 *    - signal PBS à sens unique à la sortie (0, L+1)
 * 3. Gestion des 4 orientations (NW, NE, SW, SE).
 * 4. Test en AITestMode avec bouclier AIAccounting, pose réelle, démolition atomique.
 * 5. Recherche d'emplacement près des industries avec couverture de capture.
 * 6. Ordonnancement complet V198 : gares -> voie 1 (outwardSide) -> voie 2 (guideTiles)
 *    -> pose voies -> signaux de cantonnement tous les ~7 tuiles -> 1 train -> rollback
 *    propre et repli voie unique si échec.
 */

const OPEX_ORIENT_NW = 0;
const OPEX_ORIENT_NE = 1;
const OPEX_ORIENT_SW = 2;
const OPEX_ORIENT_SE = 3;
const OPEX_TEMPLATE_SIGNAL_INTERVAL = 7;

/* Calcule la tuile decalee de (dx, dy) selon l'orientation de la gare (repere local). */
function OpexTemplateMoveTile(originTile, dx, dy, orientation)
{
  switch (orientation) {
    case OPEX_ORIENT_SE:
      return OpexV190MakeTile(originTile, dx, dy);
    case OPEX_ORIENT_SW:
      return OpexV190MakeTile(originTile, dy, -dx);
    case OPEX_ORIENT_NW:
      return OpexV190MakeTile(originTile, -dx, -dy);
    case OPEX_ORIENT_NE:
      return OpexV190MakeTile(originTile, -dy, dx);
  }
  return null;
}

/* Direction de rail associee a l'orientation de quai. */
function OpexTemplateOrientationTrack(orientation)
{
  switch (orientation) {
    case OPEX_ORIENT_SE:
    case OPEX_ORIENT_NW:
      return AIRail.RAILTRACK_NW_SE;
    case OPEX_ORIENT_NE:
    case OPEX_ORIENT_SW:
      return AIRail.RAILTRACK_NE_SW;
  }
  return AIRail.RAILTRACK_NW_SE;
}

/* Coordonnees locales pour le gabarit source a boucle (AAAHogEx SrcRailStation). */
function OpexSourceAt(originTile, x, y, orientation)
{
  return OpexTemplateMoveTile(originTile, -x + 3, y, orientation);
}

/* Calcule originTile a partir de platformTile pour le gabarit source. */
function OpexSourceOriginFromPlatform(platformTile, orientation, length)
{
  switch (orientation) {
    case OPEX_ORIENT_SE:
      return OpexTemplateMoveTile(platformTile, -1, -1, orientation);
    case OPEX_ORIENT_NW:
      return OpexTemplateMoveTile(platformTile, -2, -length, orientation);
    case OPEX_ORIENT_NE:
      return OpexTemplateMoveTile(platformTile, -1, -length, orientation);
    case OPEX_ORIENT_SW:
      return OpexTemplateMoveTile(platformTile, -2, -1, orientation);
  }
  return null;
}

/* Calcule platformTile a partir d'originTile pour le gabarit source. */
function OpexSourcePlatformFromOrigin(originTile, orientation, length)
{
  switch (orientation) {
    case OPEX_ORIENT_SE:
      return OpexTemplateMoveTile(originTile, 1, 1, orientation);
    case OPEX_ORIENT_NW:
      return OpexTemplateMoveTile(originTile, 2, length, orientation);
    case OPEX_ORIENT_NE:
      return OpexTemplateMoveTile(originTile, 1, length, orientation);
    case OPEX_ORIENT_SW:
      return OpexTemplateMoveTile(originTile, 2, 1, orientation);
  }
  return null;
}

/* Coordonnees locales pour le gabarit destination traversant (AAAHogEx DestRailStation). */
function OpexDestAt(originTile, x, y, orientation, length)
{
  return OpexTemplateMoveTile(originTile, -x, (length + 2) - y, orientation);
}

/* Calcule originTile a partir de platformTile pour le gabarit destination. */
function OpexDestOriginFromPlatform(platformTile, orientation, length)
{
  switch (orientation) {
    case OPEX_ORIENT_SE:
      return OpexTemplateMoveTile(platformTile, 0, -2, orientation);
    case OPEX_ORIENT_NW:
      return OpexTemplateMoveTile(platformTile, 0, -length - 1, orientation);
    case OPEX_ORIENT_NE:
      return OpexTemplateMoveTile(platformTile, 0, -length - 1, orientation);
    case OPEX_ORIENT_SW:
      return OpexTemplateMoveTile(platformTile, 0, -2, orientation);
  }
  return null;
}

/* Calcule platformTile a partir d'originTile pour le gabarit destination. */
function OpexDestPlatformFromOrigin(originTile, orientation, length)
{
  switch (orientation) {
    case OPEX_ORIENT_SE:
      return OpexTemplateMoveTile(originTile, 0, 2, orientation);
    case OPEX_ORIENT_NW:
      return OpexTemplateMoveTile(originTile, 0, length + 1, orientation);
    case OPEX_ORIENT_NE:
      return OpexTemplateMoveTile(originTile, 0, length + 1, orientation);
    case OPEX_ORIENT_SW:
      return OpexTemplateMoveTile(originTile, 0, 2, orientation);
  }
  return null;
}

/* Liste de toutes les tuiles necessaires au gabarit source. */
function OpexSourceTemplateTiles(originTile, orientation, length)
{
  local tiles = [];
  local seen = {};
  for (local x = 0; x < 3; x++) {
    for (local y = 0; y <= length + 3; y++) {
      local t = OpexSourceAt(originTile, x, y, orientation);
      if (t == null || !AIMap.IsValidTile(t)) return null;
      if (!(t in seen)) { seen[t] <- true; tiles.append(t); }
    }
  }
  local extraDepot = OpexSourceAt(originTile, 3, length + 2, orientation);
  if (extraDepot != null && AIMap.IsValidTile(extraDepot) && !(extraDepot in seen)) {
    seen[extraDepot] <- true;
    tiles.append(extraDepot);
  }
  return tiles;
}

/* Liste de toutes les tuiles necessaires au gabarit destination traversant. */
function OpexDestTemplateTiles(originTile, orientation, length)
{
  local tiles = [];
  local seen = {};
  for (local y = 0; y <= length + 2; y++) {
    local t = OpexDestAt(originTile, 0, y, orientation, length);
    if (t == null || !AIMap.IsValidTile(t)) return null;
    if (!(t in seen)) { seen[t] <- true; tiles.append(t); }
  }
  return tiles;
}

/* Verifie la constructibilite et la platitude (ou nivelabilite via LevelTiles). */
function OpexTemplateCheckOrLevel(tiles, isRealMode = false)
{
  local allFlat = true;
  local minX = 2147483647;
  local minY = 2147483647;
  local maxX = -1;
  local maxY = -1;
  foreach (t in tiles) {
    if (!AIMap.IsValidTile(t) || !AITile.IsBuildable(t)) return false;
    if (AITile.GetSlope(t) != AITile.SLOPE_FLAT) allFlat = false;
    local tx = AIMap.GetTileX(t);
    local ty = AIMap.GetTileY(t);
    if (tx < minX) minX = tx;
    if (ty < minY) minY = ty;
    if (tx > maxX) maxX = tx;
    if (ty > maxY) maxY = ty;
  }
  if (allFlat) return true;
  local startTile = AIMap.GetTileIndex(minX, minY);
  // LevelTiles nivelle les COINS : le coin oppose est (maxX+1, maxY+1), comme AAA (d1,d2,d3).
  local endTile = AIMap.GetTileIndex(maxX + 1, maxY + 1);
  if (!AIMap.IsValidTile(startTile) || !AIMap.IsValidTile(endTile)) return false;
  if (!isRealMode) {
    if (AITile.LevelTiles(startTile, endTile)) return true;
    local err = AIError.GetLastError();
    if (err == AITile.ERR_AREA_ALREADY_FLAT) return true;
    return false;
  }
  // Nivellement au mieux : les poses de quai et de rail (fondations) tranchent ensuite.
  AITile.LevelTiles(startTile, endTile);
  return true;
}

/* Rails a poser pour le gabarit source a boucle. */
function OpexSourceRails(originTile, orientation, length)
{
  local rails = [];
  rails.append([OpexSourceAt(originTile, 0, 1, orientation),
                OpexSourceAt(originTile, 0, 0, orientation),
                OpexSourceAt(originTile, 1, 0, orientation)]);
  rails.append([OpexSourceAt(originTile, 0, 0, orientation),
                OpexSourceAt(originTile, 1, 0, orientation),
                OpexSourceAt(originTile, 2, 0, orientation)]);
  rails.append([OpexSourceAt(originTile, 1, 0, orientation),
                OpexSourceAt(originTile, 2, 0, orientation),
                OpexSourceAt(originTile, 2, 1, orientation)]);

  for (local i = 1; i < length + 2; i++) {
    rails.append([OpexSourceAt(originTile, 0, i - 1, orientation),
                  OpexSourceAt(originTile, 0, i, orientation),
                  OpexSourceAt(originTile, 0, i + 1, orientation)]);
  }

  local a = [
    [[2, 0], [2, 1], [2, 2]],
    [[1, 1], [2, 1], [2, 2]],
    [[2, 1], [2, 2], [1, 2]],
    [[2, 1], [2, 2], [3, 2]],
    [[2, 3], [2, 2], [1, 2]],
    [[2, 3], [2, 2], [3, 2]],
    [[1, 0], [1, 1], [2, 1]],
    [[1, 0], [1, 1], [0, 1]],
    [[0, 1], [1, 1], [2, 1]],
    [[1, 1], [0, 1], [0, 2]],
    [[1, 1], [0, 1], [0, 0]]
  ];
  foreach (r in a) {
    rails.append([OpexSourceAt(originTile, r[0][0], r[0][1] + length, orientation),
                  OpexSourceAt(originTile, r[1][0], r[1][1] + length, orientation),
                  OpexSourceAt(originTile, r[2][0], r[2][1] + length, orientation)]);
  }
  return rails;
}

/* Rails a poser pour le gabarit destination traversant. */
function OpexDestRails(originTile, orientation, length)
{
  local rails = [];
  rails.append([OpexDestAt(originTile, 0, length, orientation, length),
                OpexDestAt(originTile, 0, length + 1, orientation, length),
                OpexDestAt(originTile, 0, length + 2, orientation, length)]);
  return rails;
}

/* Teste la faisabilite du gabarit source en mode test (AITestMode + AIAccounting). */
function OpexTestSourceTemplate(originTile, orientation, length)
{
  local tiles = OpexSourceTemplateTiles(originTile, orientation, length);
  if (tiles == null) return false;
  local probe = AITestMode();
  local accounting = AIAccounting();

  if (!OpexTemplateCheckOrLevel(tiles, false)) return false;

  local platformTile = OpexSourcePlatformFromOrigin(originTile, orientation, length);
  if (platformTile == null || !AIMap.IsValidTile(platformTile)) return false;
  local track = OpexTemplateOrientationTrack(orientation);
  if (!AIRail.BuildRailStation(platformTile, track, 2, length, AIStation.STATION_NEW)) return false;

  local depotTile = OpexSourceAt(originTile, 1, length + 2, orientation);
  local depotFront = OpexSourceAt(originTile, 2, length + 2, orientation);
  if (depotTile == null || depotFront == null) return false;
  if (!AIRail.BuildRailDepot(depotTile, depotFront)) return false;
  return true;
}

/* Teste la faisabilite du gabarit destination en mode test (AITestMode + AIAccounting). */
function OpexTestDestTemplate(originTile, orientation, length)
{
  local tiles = OpexDestTemplateTiles(originTile, orientation, length);
  if (tiles == null) return false;
  local probe = AITestMode();
  local accounting = AIAccounting();

  if (!OpexTemplateCheckOrLevel(tiles, false)) return false;

  local platformTile = OpexDestPlatformFromOrigin(originTile, orientation, length);
  if (platformTile == null || !AIMap.IsValidTile(platformTile)) return false;
  local track = OpexTemplateOrientationTrack(orientation);
  if (!AIRail.BuildRailStation(platformTile, track, 1, length, AIStation.STATION_NEW)) return false;
  return true;
}

/* Recherche d'emplacement pour le gabarit source pres de l'industrie source. */
function OpexFindSourceTemplateSite(catalog, candidate, length, maxRadius = 10)
{
  local orientations = [OPEX_ORIENT_SE, OPEX_ORIENT_SW, OPEX_ORIENT_NW, OPEX_ORIENT_NE];
  for (local r = 0; r <= maxRadius; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local platformBase = candidate.src + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(platformBase)) continue;
        local cargoVal = OpexRailPlatformCargoValue(platformBase, AIMap.GetTileIndex(0, 1), length,
                                                    candidate.cargo, catalog.railCoverage, true);
        if (cargoVal <= 0) continue;
        foreach (orient in orientations) {
          local origin = OpexSourceOriginFromPlatform(platformBase, orient, length);
          if (origin == null || !AIMap.IsValidTile(origin)) continue;
          if (OpexTestSourceTemplate(origin, orient, length)) {
            return { originTile = origin, orientation = orient, length = length,
                     platformTile = platformBase, cargoValue = cargoVal };
          }
        }
      }
    }
  }
  return null;
}

/* Recherche d'emplacement pour le gabarit destination pres de l'industrie/ville destination. */
function OpexFindDestTemplateSite(catalog, candidate, length, maxRadius = 10)
{
  local orientations = [OPEX_ORIENT_SE, OPEX_ORIENT_SW, OPEX_ORIENT_NW, OPEX_ORIENT_NE];
  for (local r = 0; r <= maxRadius; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local platformBase = candidate.dst + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(platformBase)) continue;
        local cargoVal = OpexRailPlatformCargoValue(platformBase, AIMap.GetTileIndex(0, 1), length,
                                                    candidate.cargo, catalog.railCoverage, false);
        if (cargoVal < 8) continue;
        foreach (orient in orientations) {
          local origin = OpexDestOriginFromPlatform(platformBase, orient, length);
          if (origin == null || !AIMap.IsValidTile(origin)) continue;
          if (OpexTestDestTemplate(origin, orient, length)) {
            return { originTile = origin, orientation = orient, length = length,
                     platformTile = platformBase, cargoValue = cargoVal };
          }
        }
      }
    }
  }
  return null;
}

/* Pose reelle du gabarit source a boucle. */
function OpexBuildSourceTemplateReal(templateInfo)
{
  local originTile = templateInfo.originTile;
  local orientation = templateInfo.orientation;
  local length = templateInfo.length;
  local allTiles = OpexSourceTemplateTiles(originTile, orientation, length);
  if (allTiles == null) return { ok = false, reason = "TILE_INVALID" };

  if (!OpexTemplateCheckOrLevel(allTiles, true)) {
    return { ok = false, reason = "LEVEL_FAIL" };
  }

  foreach (t in allTiles) {
    AITile.DemolishTile(t);
  }

  local platformTile = OpexSourcePlatformFromOrigin(originTile, orientation, length);
  local track = OpexTemplateOrientationTrack(orientation);
  local stId = AIRail.BuildRailStation(platformTile, track, 2, length, AIStation.STATION_NEW);
  if (!stId) {
    return { ok = false, reason = "STN_FAIL" };
  }

  local depotTile = OpexSourceAt(originTile, 1, length + 2, orientation);
  local depotFront = OpexSourceAt(originTile, 2, length + 2, orientation);
  if (!AIRail.BuildRailDepot(depotTile, depotFront)) {
    return { ok = false, reason = "DEPOT_FAIL", stationId = stId, platformTile = platformTile };
  }

  local rails = OpexSourceRails(originTile, orientation, length);
  local railTiles = [];
  foreach (seg in rails) {
    if (!AIRail.BuildRail(seg[0], seg[1], seg[2])) {
      return { ok = false, reason = "RAIL_FAIL", stationId = stId, platformTile = platformTile,
               depotTile = depotTile, railTiles = railTiles };
    }
    railTiles.append(seg[1]);
  }

  local sig1Tile = OpexSourceAt(originTile, 2, 0, orientation);
  local sig1Front = OpexSourceAt(originTile, 2, 1, orientation);
  local sig2Tile = OpexSourceAt(originTile, 0, length, orientation);
  local sig2Front = OpexSourceAt(originTile, 0, length - 1, orientation);

  if ("SIGNALTYPE_PBS_ONEWAY" in AIRail) {
    AIRail.BuildSignal(sig1Tile, sig1Front, AIRail.SIGNALTYPE_PBS_ONEWAY);
    AIRail.BuildSignal(sig2Tile, sig2Front, AIRail.SIGNALTYPE_PBS_ONEWAY);
  } else {
    AIRail.BuildSignal(sig1Tile, sig1Front, AIRail.SIGNALTYPE_PBS);
    AIRail.BuildSignal(sig2Tile, sig2Front, AIRail.SIGNALTYPE_PBS);
  }

  local depTile = OpexSourceAt(originTile, 0, length + 2, orientation);
  local depPrev = OpexSourceAt(originTile, 0, length + 1, orientation);
  local arrTile = OpexSourceAt(originTile, 2, length + 3, orientation);
  local arrNext = OpexSourceAt(originTile, 2, length + 2, orientation);

  local platformTiles = [];
  for (local i = 0; i < length; i++) {
    platformTiles.append(OpexSourceAt(originTile, 1, 1 + i, orientation));
    platformTiles.append(OpexSourceAt(originTile, 2, 1 + i, orientation));
  }

  return {
    ok = true,
    reason = "OK",
    stationId = stId,
    platformTile = platformTile,
    depotTile = depotTile,
    depotFront = depotFront,
    depTile = depTile,
    depPrev = depPrev,
    arrTile = arrTile,
    arrNext = arrNext,
    allTiles = allTiles,
    railTiles = railTiles,
    platformTiles = platformTiles,
    sig1 = { tile = sig1Tile, front = sig1Front },
    sig2 = { tile = sig2Tile, front = sig2Front }
  };
}

/* Pose reelle du gabarit destination traversant. */
function OpexBuildDestTemplateReal(templateInfo)
{
  local originTile = templateInfo.originTile;
  local orientation = templateInfo.orientation;
  local length = templateInfo.length;
  local allTiles = OpexDestTemplateTiles(originTile, orientation, length);
  if (allTiles == null) return { ok = false, reason = "TILE_INVALID" };

  if (!OpexTemplateCheckOrLevel(allTiles, true)) {
    return { ok = false, reason = "LEVEL_FAIL" };
  }

  foreach (t in allTiles) {
    AITile.DemolishTile(t);
  }

  local platformTile = OpexDestPlatformFromOrigin(originTile, orientation, length);
  local track = OpexTemplateOrientationTrack(orientation);
  local stId = AIRail.BuildRailStation(platformTile, track, 1, length, AIStation.STATION_NEW);
  if (!stId) {
    return { ok = false, reason = "STN_FAIL" };
  }

  local rails = OpexDestRails(originTile, orientation, length);
  local railTiles = [];
  foreach (seg in rails) {
    if (!AIRail.BuildRail(seg[0], seg[1], seg[2])) {
      return { ok = false, reason = "RAIL_FAIL", stationId = stId, platformTile = platformTile,
               railTiles = railTiles };
    }
    railTiles.append(seg[1]);
  }

  local sigTile = OpexDestAt(originTile, 0, length + 1, orientation, length);
  local sigFront = OpexDestAt(originTile, 0, length, orientation, length);
  if ("SIGNALTYPE_PBS_ONEWAY" in AIRail) {
    AIRail.BuildSignal(sigTile, sigFront, AIRail.SIGNALTYPE_PBS_ONEWAY);
  } else {
    AIRail.BuildSignal(sigTile, sigFront, AIRail.SIGNALTYPE_PBS);
  }

  local arrTile = OpexDestAt(originTile, 0, 0, orientation, length);
  local arrNext = OpexDestAt(originTile, 0, 1, orientation, length);
  local depTile = OpexDestAt(originTile, 0, length + 2, orientation, length);
  local depPrev = OpexDestAt(originTile, 0, length + 1, orientation, length);

  local platformTiles = [];
  for (local i = 0; i < length; i++) {
    platformTiles.append(OpexDestAt(originTile, 0, 1 + i, orientation, length));
  }

  return {
    ok = true,
    reason = "OK",
    stationId = stId,
    platformTile = platformTile,
    arrTile = arrTile,
    arrNext = arrNext,
    depTile = depTile,
    depPrev = depPrev,
    allTiles = allTiles,
    railTiles = railTiles,
    platformTiles = platformTiles,
    sig = { tile = sigTile, front = sigFront }
  };
}

/* Demolition propre du gabarit source en cas d'echec. */
function OpexDemolishSourceTemplate(info)
{
  if (info == null) return;
  local selfCompany = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  if ("sig1" in info && info.sig1 != null) {
    AIRail.RemoveSignal(info.sig1.tile, info.sig1.front);
  }
  if ("sig2" in info && info.sig2 != null) {
    AIRail.RemoveSignal(info.sig2.tile, info.sig2.front);
  }
  if ("depotTile" in info && info.depotTile != null && AIMap.IsValidTile(info.depotTile)) {
    if (AIRail.IsRailDepotTile(info.depotTile) && AITile.GetOwner(info.depotTile) == selfCompany) {
      AITile.DemolishTile(info.depotTile);
    }
  }
  if ("railTiles" in info && info.railTiles != null) {
    foreach (t in info.railTiles) {
      if (AIMap.IsValidTile(t) && AITile.GetOwner(t) == selfCompany) {
        AITile.DemolishTile(t);
      }
    }
  }
  if ("platformTiles" in info && info.platformTiles != null) {
    foreach (t in info.platformTiles) {
      if (AIMap.IsValidTile(t) && AITile.GetOwner(t) == selfCompany && AIRail.IsRailStationTile(t)) {
        AIRail.RemoveRailStationTileRectangle(t, t, false);
      }
    }
  }
}

/* Demolition propre du gabarit destination en cas d'echec. */
function OpexDemolishDestTemplate(info)
{
  if (info == null) return;
  local selfCompany = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  if ("sig" in info && info.sig != null) {
    AIRail.RemoveSignal(info.sig.tile, info.sig.front);
  }
  if ("railTiles" in info && info.railTiles != null) {
    foreach (t in info.railTiles) {
      if (AIMap.IsValidTile(t) && AITile.GetOwner(t) == selfCompany) {
        AITile.DemolishTile(t);
      }
    }
  }
  if ("platformTiles" in info && info.platformTiles != null) {
    foreach (t in info.platformTiles) {
      if (AIMap.IsValidTile(t) && AITile.GetOwner(t) == selfCompany && AIRail.IsRailStationTile(t)) {
        AIRail.RemoveRailStationTileRectangle(t, t, false);
      }
    }
  }
}

/* Demolition d'un trace de voie complet. */
function OpexDemolishTrack(tiles)
{
  if (tiles == null) return;
  local selfCompany = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  for (local i = tiles.len() - 1; i >= 0; i--) {
    local t = tiles[i];
    if (!AIMap.IsValidTile(t)) continue;
    if (AITile.GetOwner(t) != selfCompany) continue;
    if (AIRail.IsRailStationTile(t)) {
      AIRail.RemoveRailStationTileRectangle(t, t, false);
    } else if (AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t)) {
      AITile.DemolishTile(t);
    }
  }
}

/* Pose des signaux de cantonnement a sens unique tous les N tuiles. */
function OpexBuildBlockSignals(tiles, interval = 7)
{
  if (tiles == null || tiles.len() < 3) return;
  for (local i = interval; i < tiles.len() - 2; i += interval) {
    local cur = tiles[i];
    local prev = tiles[i - 1];
    if (AIMap.DistanceManhattan(prev, cur) == 1 && AIRail.IsRailTile(cur)) {
      if (AIRail.GetSignalType(cur, prev) != AIRail.SIGNALTYPE_NONE) {
        AIRail.RemoveSignal(cur, prev);
      }
      if ("SIGNALTYPE_PBS_ONEWAY" in AIRail) {
        AIRail.BuildSignal(cur, prev, AIRail.SIGNALTYPE_PBS_ONEWAY);
      } else {
        AIRail.BuildSignal(cur, prev, AIRail.SIGNALTYPE_PBS);
      }
    }
  }
}

/* Repli gracieux en voie unique classique en cas d'echec V198. */
function OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, failReason)
{
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = plan.capital + cashReserve;
  if (money < need) {
    if (DECISION_LOG) {
      OpexDecide("V198", "step=fallback_single ok=0 reason=CASH need=" + need + " money=" + money);
    }
    return { ok = false, reason = "CASH", trains = 0, actualCost = 0 };
  }
  if (DECISION_LOG) {
    OpexDecide("V198", "step=fallback_single ok=1 reason=" + failReason);
  }
  return OpexExecuteRailPlan(catalog, budget, candidate, plan, cashReserve);
}

/* Construction d'une ligne complete V198 avec gabarits de gare et double voie guidee. */
function OpexV198ExecuteRailPlan(catalog, budget, candidate, plan, cashReserve)
{
  local result = { ok = false, reason = "", trains = 0, vehicles = [], actualCost = 0,
                   capital = candidate.capital };

  // 1. Recherche et validation des emplacements des deux gabarits
  local srcTemplate = OpexFindSourceTemplateSite(catalog, candidate, plan.length);
  if (srcTemplate == null) {
    if (DECISION_LOG) OpexDecide("V198", "step=place_src ok=0 reason=NOSRC");
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, "NOSRC");
  }
  if (DECISION_LOG) OpexDecide("V198", "step=place_src ok=1 reason=OK");

  local dstTemplate = OpexFindDestTemplateSite(catalog, candidate, plan.length);
  if (dstTemplate == null) {
    if (DECISION_LOG) OpexDecide("V198", "step=place_dst ok=0 reason=NODST");
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, "NODST");
  }
  if (DECISION_LOG) OpexDecide("V198", "step=place_dst ok=1 reason=OK");

  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = candidate.capital + cashReserve;
  if (money < need) {
    result.reason = "CASH";
    if (DECISION_LOG) OpexDecide("V198", "step=budget ok=0 reason=CASH need=" + need + " money=" + money);
    return result;
  }
  if (!OpexRailVehicleSlotAvailable()) {
    result.reason = "NOTRAIN";
    return result;
  }

  // 2. Pose reelle des deux gares
  local costs = AIAccounting();
  local builtSrc = OpexBuildSourceTemplateReal(srcTemplate);
  if (!builtSrc.ok) {
    if (DECISION_LOG) OpexDecide("V198", "step=build_src ok=0 reason=" + builtSrc.reason);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, builtSrc.reason);
  }

  local builtDst = OpexBuildDestTemplateReal(dstTemplate);
  if (!builtDst.ok) {
    if (DECISION_LOG) OpexDecide("V198", "step=build_dst ok=0 reason=" + builtDst.reason);
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, builtDst.reason);
  }

  // 3. Voie 1 : A* de source.depart vers dest.arrivee avec outwardSide (V197)
  local plansA1 = [{ lead = builtSrc.depTile, station_exit = builtSrc.depPrev }];
  local plansB1 = [{ lead = builtDst.arrTile, station_exit = builtDst.arrNext }];
  local deadlineTick = AIController.GetTick() + plan.iterationBudget / 3 + BUILD_TICK_MARGIN;
  local search1 = OpexSearchPath(plansA1, plansB1, plan.iterationBudget, deadlineTick, null, null, 1, null);
  if (search1.path == null || search1.path == false) {
    local stopReason = ("stop" in search1) ? search1.stop : "NOPA1";
    if (DECISION_LOG) OpexDecide("V198", "step=path_track1 ok=0 reason=" + stopReason);
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, stopReason);
  }
  local tiles1 = OpexResolveSearchTiles(search1);
  local structures1 = OpexResolveSearchStructures(search1);
  if (tiles1 == null || tiles1.len() < 3) {
    if (DECISION_LOG) OpexDecide("V198", "step=path_track1 ok=0 reason=SHORT1");
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, "SHORT1");
  }
  if (DECISION_LOG) OpexDecide("V198", "step=path_track1 ok=1 reason=OK len=" + tiles1.len());

  // 4. Voie 2 : A* de dest.depart vers source.arrivee avec guideTiles et tuiles interdites
  local forbidden = {};
  foreach (t in tiles1) forbidden[t] <- true;
  foreach (t in builtSrc.allTiles) forbidden[t] <- true;
  foreach (t in builtDst.allTiles) forbidden[t] <- true;
  // Les extremites de la voie 2 appartiennent aux gabarits : ne pas les interdire.
  foreach (t in [builtDst.depTile, builtDst.depPrev, builtSrc.arrTile, builtSrc.arrNext]) {
    if (t != null && (t in forbidden)) delete forbidden[t];
  }
  local ignored2 = [];
  foreach (t, _ in forbidden) ignored2.append(t);
  // Echeance propre a la voie 2 (celle de la voie 1 est deja consommee).
  deadlineTick = AIController.GetTick() + plan.iterationBudget / 3 + BUILD_TICK_MARGIN;

  local guideTiles = OpexV197BuildGuideTiles(tiles1, 1, forbidden);
  local plansA2 = [{ lead = builtDst.depTile, station_exit = builtDst.depPrev }];
  local plansB2 = [{ lead = builtSrc.arrTile, station_exit = builtSrc.arrNext }];
  local search2 = OpexSearchPath(plansA2, plansB2, plan.iterationBudget, deadlineTick, ignored2, null, null, guideTiles);
  if (search2.path == null || search2.path == false) {
    local stopReason = ("stop" in search2) ? search2.stop : "NOPA2";
    if (DECISION_LOG) OpexDecide("V198", "step=path_track2 ok=0 reason=" + stopReason);
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, stopReason);
  }
  local tiles2 = OpexResolveSearchTiles(search2);
  local structures2 = OpexResolveSearchStructures(search2);
  if (tiles2 == null || tiles2.len() < 3) {
    if (DECISION_LOG) OpexDecide("V198", "step=path_track2 ok=0 reason=SHORT2");
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, "SHORT2");
  }
  if (DECISION_LOG) OpexDecide("V198", "step=path_track2 ok=1 reason=OK len=" + tiles2.len());

  // 5. Pose des voies 1 et 2
  local fail1 = OpexBuildTrack(tiles1, structures1);
  if (fail1 > 0) {
    if (DECISION_LOG) OpexDecide("V198", "step=build_track1 ok=0 reason=TRKFAIL1 failed=" + fail1);
    OpexDemolishTrack(tiles1);
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, "TRKFAIL1");
  }

  local fail2 = OpexBuildTrack(tiles2, structures2);
  if (fail2 > 0) {
    if (DECISION_LOG) OpexDecide("V198", "step=build_track2 ok=0 reason=TRKFAIL2 failed=" + fail2);
    OpexDemolishTrack(tiles2);
    OpexDemolishTrack(tiles1);
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, "TRKFAIL2");
  }

  // 6. Signaux de cantonnement a sens unique tous les ~7 tuiles
  OpexBuildBlockSignals(tiles1, OPEX_TEMPLATE_SIGNAL_INTERVAL);
  OpexBuildBlockSignals(tiles2, OPEX_TEMPLATE_SIGNAL_INTERVAL);

  // 7. Construction d'un train avec ordres : plein chargement source, dechargement destination
  local exitA = builtSrc.platformTile;
  local exitB = builtDst.platformTile;
  local trains = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, builtSrc.depotTile,
                                 exitA, exitB, 1, candidate.loco, candidate.wagons,
                                 plan.length, true,
                                 OpexV163Cargo2(candidate), OpexV163Wagons2(candidate));
  if (trains.failed || trains.built == 0) {
    if (DECISION_LOG) OpexDecide("V198", "step=build_train ok=0 reason=TRAINFAIL");
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
    OpexDemolishDestTemplate(builtDst);
    OpexDemolishSourceTemplate(builtSrc);
    return OpexV198FallbackSingle(catalog, budget, candidate, plan, cashReserve, "TRAINFAIL");
  }

  // 8. Finalisation et metadonnees pour le clonage et l'expansion
  result.ok = true;
  result.reason = "OK";
  result.trains = trains.built;
  result.vehicles = trains.vehicles;
  result.actualCost = costs.GetCosts();
  result.capital = result.actualCost;
  result.stationA = builtSrc.platformTile;
  result.stationB = builtDst.platformTile;
  result.depot = builtSrc.depotTile;
  result.doubleTrack <- 1;
  result.loop <- 1;
  result.v181Loop <- true;
  result.stationA2 <- builtSrc.platformTile;
  result.stationB2 <- builtDst.platformTile;
  result.depot2 <- builtSrc.depotTile;
  result.platformA <- { anchor = builtSrc.platformTile, length = plan.length };
  result.platformB <- { anchor = builtDst.platformTile, length = plan.length };
  result.platformA2 <- result.platformA;
  result.platformB2 <- result.platformB;
  result.tiles <- tiles1;
  result.tiles2 <- tiles2;

  if (DECISION_LOG) {
    OpexDecide("V198", "step=complete ok=1 trains=1 cost=" + result.actualCost);
  }
  return result;
}
