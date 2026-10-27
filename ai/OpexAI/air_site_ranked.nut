/* air_site_ranked=1 (default OFF): native score-ranked bands, then C96 spiral.
 * Adapted from ff419e15 geometry; no slope penalty or flat-only rejection.
 * Same total per-town BuildAirport allowance and <=3 leveling admissions across
 * BOTH phases. Only shared historical AIR_SITE_CACHE is retained; no new Save state.
 * Loaded and installed only ON, or loaded without installation by the solo probe.
 */

/* Equivalent to production's max-height flat predicate, using a native list.
 * This is a fast ACCEPT path for foundations, never a flat-only prefilter. */
function OpexAirRankedFlat(anchor, airport)
{
  local endTile = anchor + AIMap.GetTileIndex(airport.width - 1, airport.height - 1);
  if (!AIMap.IsValidTile(anchor) || !AIMap.IsValidTile(endTile)) return false;
  local tiles = AITileList();
  tiles.AddRectangle(anchor, endTile);
  tiles.Valuate(AITile.GetMaxHeight);
  tiles.KeepValue(AITile.GetMaxHeight(anchor));
  return tiles.Count() == airport.width * airport.height;
}

function OpexAirRankedMovingCorners(anchor, airport)
{
  local ax = AIMap.GetTileX(anchor);
  local ay = AIMap.GetTileY(anchor);
  if (ax + airport.width >= AIMap.GetMapSizeX() || ay + airport.height >= AIMap.GetMapSizeY()) return null;
  local endTile = OpexAirFootprintEnd(anchor, airport);
  if (!AIMap.IsValidTile(anchor) || !AIMap.IsValidTile(endTile)) return null;
  local corners = AITileList();
  corners.AddRectangle(anchor, endTile);
  if (corners.Count() != (airport.width + 1) * (airport.height + 1)) return null;
  corners.Valuate(AITile.GetCornerHeight, AITile.CORNER_N);
  corners.RemoveValue(AITile.GetCornerHeight(anchor, AITile.CORNER_N));
  return corners;
}

/* Independent autoslope tests around roads/houses do not compose. Require clear
 * outside tiles only where a boundary corner actually has to move. Interior
 * terrain has already passed native CheapOk; unchanged boundary corners pass. */
function OpexAirRankedBoundaryClear(anchor, airport, corners)
{
  if (corners == null) return false;
  local mapX = AIMap.GetMapSizeX();
  local ax = AIMap.GetTileX(anchor);
  local ay = AIMap.GetTileY(anchor);
  foreach (tile, height in corners) {
    local dx = (tile - anchor) % mapX;
    local dy = (tile - anchor) / mapX;
    if (dx > 0 && dy > 0 && dx < airport.width && dy < airport.height) continue;
    for (local ox = -1; ox <= 0; ox++) {
      for (local oy = -1; oy <= 0; oy++) {
        local rx = dx + ox;
        local ry = dy + oy;
        if (rx >= 0 && ry >= 0 && rx < airport.width && ry < airport.height) continue;
        if (ax + rx < 0 || ay + ry < 0) return false;
        local adjacent = AIMap.GetTileIndex(ax + rx, ay + ry);
        if (!AIMap.IsValidTile(adjacent) || !AITile.IsBuildable(adjacent)
            || AITile.IsWaterTile(adjacent) || AITile.IsCoastTile(adjacent) || AITile.IsRiverTile(adjacent)) {
          if (DECISION_LOG) AILog.Info("AIR_RANKED_LEVEL_REJECT tile=" + anchor + " type=" + airport.type
              + " corner=" + tile + " height=" + height
              + " obstacle=" + adjacent + " reason=changed_border");
          return false;
        }
      }
    }
  }
  return true;
}

function OpexAirRankedCheapOk(anchor, airport)
{
  if (!OpexAirFootprintCheapOkNative(anchor, airport)) return false;
  if (OpexAirRankedFlat(anchor, airport)) return true;
  // Pure geometry rejection must not consume one of the three native leveling
  // attempts. Applies identically to ranked bands, fallback and cache validation.
  return OpexAirRankedBoundaryClear(anchor, airport, OpexAirRankedMovingCorners(anchor, airport));
}

/* CmdLevelLand15.3 succeeds when ANY corner was changed, even if others failed.
 * Check every required atomic move, including the w/h boundary, under test mode.
 * CheapOk bounds the relief to one step; authority remains conditional on boost.
 * AITestMode cannot compose multi-step terrain changes: larger deltas fail closed.
 */
function OpexAirRankedCanLevelFootprint(anchor, airport, townId = -1)
{
  local corners = OpexAirRankedMovingCorners(anchor, airport);
  if (corners == null) return false;
  if (OpexAirRankedFlat(anchor, airport)) return true;
  if (!OpexAirRankedBoundaryClear(anchor, airport, corners)) return false;
  local target = AITile.GetCornerHeight(anchor, AITile.CORNER_N);
  local shield = AIAccounting();
  local test = AITestMode();
  foreach (tile, height in corners) {
    if (abs(height - target) > 1) return false;
    local ok = height < target ? AITile.RaiseTile(tile, AITile.SLOPE_N)
                              : AITile.LowerTile(tile, AITile.SLOPE_N);
    if (ok) continue;
    local error = AIError.GetLastError();
    if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES && townId >= 0) continue;
    if (DECISION_LOG) {
      local bulkOk = AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
      AILog.Info("AIR_RANKED_LEVEL_REJECT tile=" + anchor + " type=" + airport.type
          + " corner=" + tile + " height=" + height + " target=" + target
          + " error=" + error + " bulk_ok=" + (bulkOk ? 1 : 0));
    }
    return false;
  }
  return true;
}

function OpexAirRankedBox(townX, townY, offX, offY, mapX, mapY, radius)
{
  local minX = townX - radius;
  if (minX < 0) minX = 0;
  local minY = townY - radius;
  if (minY < 0) minY = 0;
  local maxX = townX + radius;
  local fitX = mapX - offX - 1;
  if (maxX > fitX) maxX = fitX;
  if (maxX >= mapX) maxX = mapX - 1;
  local maxY = townY + radius;
  local fitY = mapY - offY - 1;
  if (maxY > fitY) maxY = fitY;
  if (maxY >= mapY) maxY = mapY - 1;
  if (minX > maxX || minY > maxY) return null;
  return { minX = minX, minY = minY, maxX = maxX, maxY = maxY };
}

/* AddRectangle et RemoveRectangle ne font rien si un coin est MP_VOID :
 * la liste reste vide. Le bord nord (x=0 ou y=0) l'est quand freeform_edges
 * est actif ; les bords sud et est le sont toujours. On rentre la boite
 * jusqu'a deux coins valides, sans changer le domaine jouable. */
function OpexAirRankedInsetVoid(box, mapX, mapY)
{
  local minX = box.minX;
  local minY = box.minY;
  local maxX = box.maxX;
  local maxY = box.maxY;
  local north = 0;
  if (mapX > 2 && mapY > 2 && !AIMap.IsValidTile(AIMap.GetTileIndex(0, 1))) north = 1;
  if (minX < north) minX = north;
  if (minY < north) minY = north;
  local probeY = north == 0 ? 0 : 1;
  local probeX = north == 0 ? 0 : 1;
  local limitX = mapX - 1;
  local limitY = mapY - 1;
  if (mapX > 2 && !AIMap.IsValidTile(AIMap.GetTileIndex(mapX - 1, probeY))) limitX = mapX - 2;
  if (mapY > 2 && !AIMap.IsValidTile(AIMap.GetTileIndex(probeX, mapY - 1))) limitY = mapY - 2;
  if (maxX > limitX) maxX = limitX;
  if (maxY > limitY) maxY = limitY;
  if (minX > maxX || minY > maxY) return null;
  return { minX = minX, minY = minY, maxX = maxX, maxY = maxY };
}

/* Noyau Chebyshev <= inner. La spirale commence a r = 4, donc inner = 3. */
function OpexAirRankedDropCore(tiles, townX, townY, minX, minY, maxX, maxY, inner)
{
  local inMinX = townX - inner;
  if (inMinX < minX) inMinX = minX;
  local inMinY = townY - inner;
  if (inMinY < minY) inMinY = minY;
  local inMaxX = townX + inner;
  if (inMaxX > maxX) inMaxX = maxX;
  local inMaxY = townY + inner;
  if (inMaxY > maxY) inMaxY = maxY;
  if (inMinX <= inMaxX && inMinY <= inMaxY) {
    tiles.RemoveRectangle(AIMap.GetTileIndex(inMinX, inMinY), AIMap.GetTileIndex(inMaxX, inMaxY));
  }
}

/* Pour la rangee y, ancres dont la distance de Manhattan au rectangle <= rayon.
 * ax dans [townX - (w-1) - (R-dy), townX + (R-dy)], puis intersection avec la boite.
 */
function OpexAirRankedClipDistance(tiles, townX, townY, minX, minY, maxX, maxY, w, h)
{
  local radius = AIR_SITE_RADIUS;
  local span = h - 1;
  local widthGap = w - 1;
  for (local y = minY; y <= maxY; y++) {
    local bottom = y + span;
    local dy = 0;
    if (townY < y) dy = y - townY;
    else if (townY > bottom) dy = townY - bottom;
    if (dy > radius) {
      tiles.RemoveRectangle(AIMap.GetTileIndex(minX, y), AIMap.GetTileIndex(maxX, y));
      continue;
    }
    local budget = radius - dy;
    local axLo = townX - widthGap - budget;
    local axHi = townX + budget;
    if (axLo > maxX || axHi < minX) {
      tiles.RemoveRectangle(AIMap.GetTileIndex(minX, y), AIMap.GetTileIndex(maxX, y));
      continue;
    }
    if (axLo > minX) {
      tiles.RemoveRectangle(AIMap.GetTileIndex(minX, y), AIMap.GetTileIndex(axLo - 1, y));
    }
    if (axHi < maxX) {
      tiles.RemoveRectangle(AIMap.GetTileIndex(axHi + 1, y), AIMap.GetTileIndex(maxX, y));
    }
  }
}

function OpexAirRankedTiles(town, airport, requiredSlotTownId, paxCargo, rInner, rOuter, probes)
{
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);
  local box = OpexAirRankedBox(townX, townY, offX, offY, mapX, mapY, rOuter);
  if (box == null) return null;
  box = OpexAirRankedInsetVoid(box, mapX, mapY);
  if (box == null) return null;
  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(box.minX, box.minY), AIMap.GetTileIndex(box.maxX, box.maxY));
  OpexAirRankedDropCore(tiles, townX, townY, box.minX, box.minY, box.maxX, box.maxY, rInner - 1);
  if (tiles.Count() == 0) return null;
  OpexAirRankedClipDistance(tiles, townX, townY, box.minX, box.minY, box.maxX, box.maxY, w, h);
  local raw = tiles.Count();
  if ("examined" in probes) probes.examined += raw;
  if (raw == 0) return null;
  local radius = AIAirport.GetAirportCoverageRadius(airport.type);
  tiles.Valuate(AITile.IsBuildableRectangle, w, h);
  tiles.KeepValue(1);
  tiles.Valuate(AITile.IsWaterTile);
  tiles.KeepValue(0);
  tiles.Valuate(AITile.IsCoastTile);
  tiles.KeepValue(0);
  if (requiredSlotTownId >= 0) {
    tiles.Valuate(AITile.GetClosestTown);
    tiles.KeepValue(requiredSlotTownId);
  }
  tiles.Valuate(AIAirport.GetNearestTown, airport.type);
  tiles.KeepValue(town.id);
  tiles.Valuate(AITile.GetCargoAcceptance, paxCargo, w, h, radius);
  tiles.KeepAboveValue(7);
  tiles.Valuate(AITile.GetCargoProduction, paxCargo, w, h, radius);
  tiles.KeepAboveValue(0);
  tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
  return { tiles = tiles, raw = raw };
}

/* Meme sonde que la spirale, plafond execLevels < 3 compris. Le cache n'utilise
 * pas cette fonction : son rejeu de nivellement n'a pas ce plafond. */
function OpexAirRankedProbe(anchor, airport, town, probes, execLevels)
{
  local ok = false;
  local limited = false;
  {
    {
      local probe = AITestMode();
      ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
    }
    if (!ok) {
      local err = AIError.GetLastError();
      if (OpexAirRememberTownStationLimit(probes, town, err)) {
        limited = true;
      } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
          OpexAirFootprintIsFlat(anchor, airport)) {
        ok = true;
      } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                  err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                 execLevels < 3) {
        execLevels++;
        if (OpexAirCanLevelFootprint(anchor, airport, town.id)) ok = true;
      }
    }
  }
  return { ok = ok, limited = limited, execLevels = execLevels };
}

function OpexAirRankedSpiralRest(town, airport, probes, requiredSlotTownId, key, useSiteCache, allowance, used, execLevels)
{
  local paxCargo = OpexAirDemandPaxCargo();
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);
  local best = null;
  local bestScore = -1;
  local firstAnchor = -1;
  local firstScore = -1;
  local valid = 0;
  local firstValidRing = -1;
  local bestRing = -1;

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    if (firstValidRing >= 0 && r > firstValidRing + C96_AIR_SITE_EXTRA_RINGS) break;
    local ring = OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY);
    if (ring == null) continue;
    foreach (anchor, anchorX in ring) {
      if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
      local c4 = anchor + AIMap.GetTileIndex(offX, offY);
      if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;

      {
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
          continue;
        }
      }

      if (used >= allowance || probes.left <= 0) {
        if (best != null) {
          OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
              valid, firstValidRing, bestRing, used);
          if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
          return { site = best, used = used, execLevels = execLevels, allowance = allowance };
        }
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        if (useSiteCache && used >= allowance) AIR_SITE_CACHE[key] <- null;
        return { site = null, used = used, execLevels = execLevels, allowance = allowance };
      }

      local ok = false;
      {
        {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        }
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            return { site = null, used = used, execLevels = execLevels, allowance = allowance };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
              OpexAirFootprintIsFlat(anchor, airport)) {
            ok = true;
          } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                      err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                     execLevels < 3) {
            execLevels++;
            if (OpexAirCanLevelFootprint(anchor, airport, town.id)) ok = true;
          }
        }
      }

      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (!ok) continue;

      if (!OpexAirSiteHasCatchment(anchor, airport, paxCargo)) {
        if ("deadCatchment" in probes) probes.deadCatchment++;
        continue;
      }
      if (firstValidRing < 0) firstValidRing = r;
      local score = OpexAirC96SiteCatchmentScore(anchor, airport, paxCargo);
      valid++;
      if (firstAnchor < 0) {
        firstAnchor = anchor;
        firstScore = score;
      }
      if (best == null || score > bestScore) {
        best = { town = town, anchor = anchor };
        bestScore = score;
        bestRing = r;
      }
      if (valid >= C96_AIR_SITE_MAX_VALID) {
        OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
            valid, firstValidRing, bestRing, used);
        if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
        return { site = best, used = used, execLevels = execLevels, allowance = allowance };
      }
    }
  }

  if (best != null) {
    OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
        valid, firstValidRing, bestRing, used);
    if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
    return { site = best, used = used, execLevels = execLevels, allowance = allowance };
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) AIR_SITE_CACHE[key] <- null;
  return { site = null, used = used, execLevels = execLevels, allowance = allowance };
}


function OpexAirRankedListed(town, airport, probes, requiredSlotTownId, key, useSiteCache)
{
  local pax = OpexAirDemandPaxCargo();
  if (pax < 0) return OpexAirRankedOriginalListed(town, airport, probes, requiredSlotTownId, key, useSiteCache);
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local levels = 0;
  // Reserve half of a small allowance for the fallback. At most twelve native
  // construction tests in the ranked phase; rejected CheapOk anchors cost none.
  local cap = allowance / 2;
  if (cap > 12) cap = 12;
  local best = null;
  local bestScore = -1;
  local bands = [[4, 14], [15, AIR_SITE_RADIUS]];
  foreach (band in bands) {
    if (used >= cap || probes.left <= 0) break;
    local built = OpexAirRankedTiles(town, airport, requiredSlotTownId, pax, band[0], band[1], probes);
    if (built == null) continue;
    foreach (anchor, score in built.tiles) {
      if (score <= bestScore || used >= cap || probes.left <= 0) break;
      if (!OpexAirRankedCheapOk(anchor, airport)) {
        if ("cheapSkip" in probes) probes.cheapSkip++;
        continue;
      }
      local result = OpexAirRankedProbe(anchor, airport, town, probes, levels);
      levels = result.execLevels;
      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (result.limited) {
        if (useSiteCache) AIR_SITE_CACHE[key] <- null;
        return { site = null, used = used, execLevels = levels, allowance = allowance };
      }
      if (!result.ok) continue;
      best = { town = town, anchor = anchor };
      bestScore = score;
      break; // Native list is sorted by descending C96 production.
    }
    if (best != null && OpexAirB9TileInExpandedRect(town.tile, best.anchor,
        airport.width, airport.height, AIAirport.GetAirportCoverageRadius(airport.type))) break;
  }
  if (best != null) {
    if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
    if (DECISION_LOG) AILog.Info("AIR_RANKED_SITE town=" + town.id + " type=" + airport.type
        + " tile=" + best.anchor + " score=" + bestScore + " tested=" + used + " fallback=0");
    return { site = best, used = used, execLevels = levels, allowance = allowance };
  }
  if ("fallback" in probes) probes.fallback++;
  if (DECISION_LOG) AILog.Info("AIR_RANKED_SITE town=" + town.id + " type=" + airport.type
      + " tested=" + used + " fallback=1");
  // No negative cache write before the fallback. Continue the same budget and
  // leveling cap; do not reset either, or decrement townsLeft a second time.
  return OpexAirRankedSpiralRest(town, airport, probes, requiredSlotTownId, key, useSiteCache, allowance, used, levels);
}

// PO01C normally calls its own generator copy, bypassing OpexAirFindSite.
// Retain its generator/result contract and explicit checkpoint, then use the
// same cache, eligibility checks and measured dispatcher as synchronous callers.
function OpexPO01CAirRankedFindSite(result, town, airport, probes, requiredSlotTownId = -1)
{
  yield null; // PO01C_CHECKPOINT
  result.value = OpexAirFindSite(town, airport, probes, requiredSlotTownId);
}

OpexAirRankedOriginalListed <- OpexAirFindSiteCatchmentListed;
OpexAirRankedOriginalCanLevel <- OpexAirCanLevelFootprint;

function OpexAirRankedInstall()
{
  ::OpexAirFindSiteCatchmentListed <- OpexAirRankedListed;
  ::OpexPO01CAirFindSite <- OpexPO01CAirRankedFindSite;
  ::OpexAirFootprintCheapOk <- OpexAirRankedCheapOk;
  // Also protect the historical cache revalidation and spiral fallback ON.
  ::OpexAirCanLevelFootprint <- OpexAirRankedCanLevelFootprint;
}
