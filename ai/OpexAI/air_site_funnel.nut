/* Entonnoir de sites AIR (air_site_funnel=1). Le defaut 0 laisse la spirale.
 * Une AITileList sur la boite de Chebyshev r <= AIR_SITE_RADIUS, noyau r < 4
 * retire comme la spirale (anneaux a partir de r = 4). La distance au rectangle
 * est coupee par rangees avant les Valuate : meme ensemble que
 * OpexAirDistanceToRect > AIR_SITE_RADIUS, sans valuer chaque ancre.
 * IsBuildableRectangle en tete ne retire que les tuiles que CheapOk refuse
 * avant tout nivellement (maisons, industries, rail, mer, riviere). Le cote,
 * la denivelee et le refus d'autorite restent juges ensuite, tuile a tuile.
 * Les sondes ne courent que sur les meilleurs scores, par lots, et le premier
 * succes est le meilleur score possible.
 */
OpexAirFindSiteSpiral <- OpexAirFindSite;

function OpexAirFindSite(town, airport, probes, requiredSlotTownId = -1)
{
  local mark = OpexOpsMeasureBegin();
  AIR_SITE_OPS_MARK = mark;
  if (AIR_SITE_FUNNEL > 0) {
    return OpexAirFindSiteFunnel(town, airport, probes, requiredSlotTownId);
  }
  return OpexAirFindSiteSpiral(town, airport, probes, requiredSlotTownId);
}

function OpexAirFunnelInstall()
{
  if (AIR_SITE_FUNNEL <= 0) return;
  ::OpexPO01CAirFindSite <- OpexPO01CAirFindSiteFunnel;
}

function OpexAirFunnelTrace(town, airport, tiles, afterNative, checked, probesUsed, ok, score, bestPossible, reason)
{
  local ops = -1;
  if (AIR_SITE_OPS_MARK != null) ops = OpexOpsMeasureEnd(AIR_SITE_OPS_MARK);
  AILog.Info("AIR_SITE_FUNNEL town=" + town.id
      + " type=" + airport.type
      + " tiles=" + tiles
      + " after_native=" + afterNative
      + " checked=" + checked
      + " probes=" + probesUsed
      + " ok=" + ok
      + " score=" + score
      + " best_possible=" + bestPossible
      + " ops=" + ops
      + " reason=" + reason);
}

function OpexAirFunnelChebyshev(anchor, townTile)
{
  local dx = AIMap.GetTileX(anchor) - AIMap.GetTileX(townTile);
  if (dx < 0) dx = -dx;
  local dy = AIMap.GetTileY(anchor) - AIMap.GetTileY(townTile);
  if (dy < 0) dy = -dy;
  if (dx > dy) return dx;
  return dy;
}

function OpexAirFunnelBox(townX, townY, offX, offY, mapX, mapY)
{
  local radius = AIR_SITE_RADIUS;
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
function OpexAirFunnelInsetVoid(box, mapX, mapY)
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

/* Noyau r < 4 : la spirale commence a r = 4, donc town +/- 3. */
function OpexAirFunnelDropCore(tiles, townX, townY, minX, minY, maxX, maxY)
{
  local inMinX = townX - 3;
  if (inMinX < minX) inMinX = minX;
  local inMinY = townY - 3;
  if (inMinY < minY) inMinY = minY;
  local inMaxX = townX + 3;
  if (inMaxX > maxX) inMaxX = maxX;
  local inMaxY = townY + 3;
  if (inMaxY > maxY) inMaxY = maxY;
  if (inMinX <= inMaxX && inMinY <= inMaxY) {
    tiles.RemoveRectangle(AIMap.GetTileIndex(inMinX, inMinY), AIMap.GetTileIndex(inMaxX, inMaxY));
  }
}

/* Pour la rangee y, ancres dont la distance de Manhattan au rectangle <= rayon.
 * ax dans [townX - (w-1) - (R-dy), townX + (R-dy)], puis intersection avec la boite.
 */
function OpexAirFunnelClipDistance(tiles, townX, townY, minX, minY, maxX, maxY, w, h)
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

function OpexAirFunnelTiles(town, airport, requiredSlotTownId, paxCargo)
{
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);
  local box = OpexAirFunnelBox(townX, townY, offX, offY, mapX, mapY);
  if (box == null) return null;
  box = OpexAirFunnelInsetVoid(box, mapX, mapY);
  if (box == null) return null;
  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(box.minX, box.minY), AIMap.GetTileIndex(box.maxX, box.maxY));
  OpexAirFunnelDropCore(tiles, townX, townY, box.minX, box.minY, box.maxX, box.maxY);
  if (tiles.Count() == 0) return null;
  OpexAirFunnelClipDistance(tiles, townX, townY, box.minX, box.minY, box.maxX, box.maxY, w, h);
  local raw = tiles.Count();
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
function OpexAirFunnelProbe(anchor, airport, town, probes, execLevels)
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

function OpexAirFunnelReuse(town, airport, probes, key)
{
  local cachedAnchor = AIR_SITE_CACHE[key];
  if (cachedAnchor == null) return { kind = "negative", site = null };
  local offX = airport.width - 1;
  local offY = airport.height - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local ax = AIMap.GetTileX(cachedAnchor);
  local ay = AIMap.GetTileY(cachedAnchor);
  if (ax + offX < mapX && ay + offY < mapY) {
    local c4 = cachedAnchor + AIMap.GetTileIndex(offX, offY);
    if (!AITile.IsWaterTile(cachedAnchor) && !AITile.IsCoastTile(cachedAnchor) && !AITile.IsWaterTile(c4)
        && !AITile.IsCoastTile(c4) && AIAirport.GetNearestTown(cachedAnchor, airport.type) == town.id
        && (OpexAirFootprintCheapOk(cachedAnchor, airport))
        && (OpexAirSiteHasCatchment(cachedAnchor, airport, OpexAirDemandPaxCargo()))) {
      local ok = false;
      {
        {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
        }
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            AIR_SITE_CACHE[key] <- null;
            return { kind = "limited", site = null };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
              OpexAirFootprintIsFlat(cachedAnchor, airport)) {
            ok = true;
          } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                      err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                     OpexAirCanLevelFootprint(cachedAnchor, airport, town.id)) {
            ok = true;
          }
        }
      }
      if ("tested" in probes) probes.tested++;
      if (ok) return { kind = "site", site = { town = town, anchor = cachedAnchor } };
    }
  }
  delete AIR_SITE_CACHE[key];
  return { kind = "miss", site = null };
}

function OpexAirFunnelStoreMiss(key, useSiteCache, used, allowance, probesLeft)
{
  if (useSiteCache && (used >= allowance || probesLeft > 0)) AIR_SITE_CACHE[key] <- null;
}

function OpexAirFunnelBudget(town, airport, probes, key, useSiteCache, used, allowance, tilesN, afterNative, checked)
{
  OpexAirC78NoteNoSite(probes, "no_site_budget");
  if (useSiteCache && used >= allowance) AIR_SITE_CACHE[key] <- null;
  OpexAirFunnelTrace(town, airport, tilesN, afterNative, checked, used, 0, -1, 0, "budget");
}

function OpexAirFindSiteFunnel(town, airport, probes, requiredSlotTownId = -1)
{
  if (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(town)) {
    OpexAirFunnelTrace(town, airport, 0, 0, 0, 0, 0, -1, 0, "level");
    return null;
  }
  if (C60_TOWN_RATING_PROBE) {
    OpexC60ObserveTownRating("air", "find_site", town.id);
  }
  if (probes != null && ("stationLimitedTowns" in probes)
      && (town.id in probes.stationLimitedTowns)) {
    OpexAirFunnelTrace(town, airport, 0, 0, 0, 0, 0, -1, 0, "already_limited");
    return null;
  }
  local key = town.id + "_" + airport.type;
  local useSiteCache = AIR_SITE_CACHE_ENABLED && requiredSlotTownId < 0;
  if (useSiteCache && (key in AIR_SITE_CACHE)) {
    local reused = OpexAirFunnelReuse(town, airport, probes, key);
    if (reused.kind == "negative") {
      OpexAirFunnelTrace(town, airport, 0, 0, 0, 0, 0, -1, 0, "negative_cache");
      return null;
    }
    if (reused.kind == "limited") {
      OpexAirFunnelTrace(town, airport, 0, 0, 0, 0, 0, -1, 0, "station_limit");
      return null;
    }
    if (reused.kind == "site") {
      local score = OpexAirC96SiteCatchmentScore(reused.site.anchor, airport, OpexAirDemandPaxCargo());
      OpexAirFunnelTrace(town, airport, 0, 0, 0, 0, 1, score, 0, "cache");
      return reused.site;
    }
  }
  local paxCargo = OpexAirDemandPaxCargo();
  if (paxCargo < 0) {
    local listed = OpexAirFindSiteListed(town, airport, probes, requiredSlotTownId, key, useSiteCache);
    local found = listed.site != null ? 1 : 0;
    OpexAirFunnelTrace(town, airport, 0, 0, 0, listed.used, found, -1, 0, "no_pax");
    return listed.site;
  }
  return OpexAirFunnelSearch(town, airport, probes, requiredSlotTownId, key, useSiteCache, paxCargo);
}

function OpexAirFunnelSearch(town, airport, probes, requiredSlotTownId, key, useSiteCache, paxCargo)
{
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local packed = OpexAirFunnelTiles(town, airport, requiredSlotTownId, paxCargo);
  if (packed == null) {
    OpexAirFunnelStoreMiss(key, useSiteCache, used, allowance, probes.left);
    OpexAirFunnelTrace(town, airport, 0, 0, 0, used, 0, -1, 1, "empty");
    return null;
  }
  local tiles = packed.tiles;
  local raw = packed.raw;
  local afterNative = tiles.Count();
  if (afterNative == 0) {
    OpexAirFunnelStoreMiss(key, useSiteCache, used, allowance, probes.left);
    OpexAirFunnelTrace(town, airport, raw, 0, 0, used, 0, -1, 1, "no_native");
    return null;
  }
  local checked = 0;
  local anchor = tiles.Begin();
  while (!tiles.IsEnd()) {
    if (used >= allowance || probes.left <= 0) {
      OpexAirFunnelBudget(town, airport, probes, key, useSiteCache, used, allowance, raw, afterNative, checked);
      return null;
    }
    local batch = 0;
    while (batch < AIR_SITE_FUNNEL_BATCH && !tiles.IsEnd()) {
      local skip = OpexAirDistanceToRect(town.tile, anchor, w, h) > AIR_SITE_RADIUS;
      if (!skip) {
        local c4 = anchor + AIMap.GetTileIndex(offX, offY);
        if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) skip = true;
      }
      if (!skip) {
        batch++;
        checked++;
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
        } else if (used >= allowance || probes.left <= 0) {
          OpexAirFunnelBudget(town, airport, probes, key, useSiteCache, used, allowance, raw, afterNative, checked);
          return null;
        } else {
          local probed = OpexAirFunnelProbe(anchor, airport, town, probes, execLevels);
          execLevels = probed.execLevels;
          if (probed.limited) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            OpexAirFunnelTrace(town, airport, raw, afterNative, checked, used, 0, -1, 0, "station_limit");
            return null;
          }
          used++;
          probes.left--;
          if ("tested" in probes) probes.tested++;
          if (probed.ok && OpexAirSiteHasCatchment(anchor, airport, paxCargo)) {
            local score = tiles.GetValue(anchor);
            local site = { town = town, anchor = anchor };
            local ring = OpexAirFunnelChebyshev(anchor, town.tile);
            OpexAirC96LogChoice(town, airport, anchor, score, site, score, 1, ring, ring, used);
            if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
            OpexAirFunnelTrace(town, airport, raw, afterNative, checked, used, 1, score, 1, "ok");
            return site;
          }
          if (probed.ok && ("deadCatchment" in probes)) probes.deadCatchment++;
        }
      }
      anchor = tiles.Next();
    }
  }
  OpexAirFunnelStoreMiss(key, useSiteCache, used, allowance, probes.left);
  OpexAirFunnelTrace(town, airport, raw, afterNative, checked, used, 0, -1, 1, "exhausted");
  return null;
}
