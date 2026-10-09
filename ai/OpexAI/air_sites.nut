/* Module AIR extrait de builder_air.nut (R11) : emprises et recherche de sites (C36/C96/V94). */
/* C36.3 : l'emprise est-elle constructible SANS AITestMode ni LevelTiles ?
 * IsBuildableRectangle accepte Clear + Trees (BuildAirport les rase) et le cote, et refuse
 * maisons, industries, rail, mer, riviere. Le cote passe IsBuildable : on l'exclut a part,
 * avec mer/canal/riviere, sur CHAQUE tuile -- pas seulement les deux coins. C4 (span >= 2)
 * reste. Un hit ici n'est pas encore un site : OpexAirFindSite confirme en une sonde. */
function OpexAirFootprintCheapOk(anchor, airport)
{
  local w = airport.width;
  local h = airport.height;
  if (!AITile.IsBuildableRectangle(anchor, w, h)) return false;
  local minH = AITile.GetMinHeight(anchor);
  local maxH = AITile.GetMaxHeight(anchor);
  local offX = w - 1;
  local offY = h - 1;
  for (local tx = 0; tx <= offX; tx++) {
    for (local ty = 0; ty <= offY; ty++) {
      local t = anchor + AIMap.GetTileIndex(tx, ty);
      if (!AIMap.IsValidTile(t)) return false;
      if (AITile.IsWaterTile(t) || AITile.IsCoastTile(t) || AITile.IsRiverTile(t)) return false;
      local tMin = AITile.GetMinHeight(t);
      local tMax = AITile.GetMaxHeight(t);
      if (tMin < minH) minH = tMin;
      if (tMax > maxH) maxH = tMax;
      if (maxH - minH >= 2) return false;
    }
  }
  return true;
}

function OpexAirFootprintEnd(anchor, airport)
{
  /* AITile.LevelTiles prend le coin terminal de TERRASSEMENT, pas la derniere
   * tuile de l'aeroport. Pour une emprise w x h il est donc a +(w,h) :
   * SuperLib.Tile.CostToFlattern et AAAHogEx::AirStation.Build emploient tous
   * deux cette convention. L'ancienne borne +(w-1,h-1) laissait la rangee et
   * la colonne finales en pente, puis BuildAirport echouait ERR_FLAT_LAND_REQUIRED
   * bien que notre sonde ait annonce le site nivelable. */
  return anchor + AIMap.GetTileIndex(airport.width, airport.height);
}

function OpexAirFootprintIsFlat(anchor, airport)
{
  /* CheckFlatLandAirport compare le z du coin haut de chaque tuile (allowed_z), pas l'absence
   * de pente : min==max par tuile est plus dur que le moteur. */
  local z = AITile.GetMaxHeight(anchor);
  local offX = airport.width - 1;
  local offY = airport.height - 1;
  for (local tx = 0; tx <= offX; tx++) {
    for (local ty = 0; ty <= offY; ty++) {
      local t = anchor + AIMap.GetTileIndex(tx, ty);
      if (!AIMap.IsValidTile(t)) return false;
      if (AITile.GetMaxHeight(t) != z) return false;
    }
  }
  return true;
}

/* BFAIL : photographie pure des tuiles du rectangle de nivellement (w+1 x h+1),
 * sous la seule sonde AIR_BFAIL_PRECHECK_SHADOW. Les cases sont en ordre dx/dy,
 * code min.max.slope avec ! si non constructible. Le bord supplementaire est
 * essentiel : LevelTiles utilise +(w,h), et non la derniere tuile aeroport. */
function OpexAirBLevelTerrainSnapshot(anchor, airport)
{
  local ax = AIMap.GetTileX(anchor);
  local ay = AIMap.GetTileY(anchor);
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local grid = "";
  local minH = 999;
  local maxH = -1;
  local slopes = 0;
  local blocked = 0;
  local invalid = 0;
  local mismatched = 0;
  local airportZ = AITile.GetMaxHeight(anchor);
  for (local dx = 0; dx <= airport.width; dx++) {
    for (local dy = 0; dy <= airport.height; dy++) {
      if (grid != "") grid += ",";
      if (ax + dx >= mapX || ay + dy >= mapY) {
        grid += "X";
        invalid++;
        continue;
      }
      local tile = AIMap.GetTileIndex(ax + dx, ay + dy);
      /* La derniere colonne/ligne physique est hors carte jouable, meme
       * lorsque l'index lineaire reste inferieur a GetMapSize(). */
      if (!AIMap.IsValidTile(tile)) {
        grid += "X";
        invalid++;
        continue;
      }
      local lo = AITile.GetMinHeight(tile);
      local hi = AITile.GetMaxHeight(tile);
      local slope = AITile.GetSlope(tile);
      local buildable = AITile.IsBuildable(tile);
      grid += lo + "." + hi + "." + slope + (buildable ? "" : "!");
      if (lo < minH) minH = lo;
      if (hi > maxH) maxH = hi;
      if (slope != AITile.SLOPE_FLAT) slopes++;
      if (!buildable) blocked++;
      if (dx < airport.width && dy < airport.height && hi != airportZ) mismatched++;
    }
  }
  return { grid = grid, minH = minH, maxH = maxH, slopes = slopes,
           blocked = blocked, invalid = invalid, mismatched = mismatched,
           x = ax, y = ay, target = AITile.GetCornerHeight(anchor, AITile.CORNER_N) };
}

/* G7Ãƒâ€šÃ‚Â§2 : Sonde AITestMode de nivelabilite, sans modifier la carte ni depenser de tresorerie.
 * Retourne true si LevelTiles REUSSIRAIT (terrain deja plat, ou nivelable, ou autorisation
 * achetable). Utilise par OpexAirFindSite pendant la generation, avant election. */
function OpexAirCanLevelFootprint(anchor, airport, townId = -1)
{
  local end = OpexAirFootprintEnd(anchor, airport);
  if (!AIMap.IsValidTile(end)) return false;
  if (OpexAirFootprintIsFlat(anchor, airport)) return true;
  local probe = AITestMode();
  if (AITile.LevelTiles(anchor, end)) return true;
  local err = AIError.GetLastError();
  if (err == AITile.ERR_AREA_ALREADY_FLAT) return true;
  /* L'autorite locale refuse mais un boost arbre le resoudrait au moment de construire. */
  if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES && townId >= 0) return true;
  return false;
}

/* Nivellement REEL (pas AITestMode) de l'emprise exacte, puis verification min=max.
 * LevelTiles en test ne change pas la carte ; BuildAirport ne terrasse pas. */
function OpexAirLevelFootprint(anchor, airport, townId = -1, shadow = null)
{
  local end = OpexAirFootprintEnd(anchor, airport);
  /* R18 : ne pas relire une erreur moteur apres une autre commande (boost,
   * aeroport, invalidation ou rollback). Les echecs geometriques sont explicites. */
  if (!AIMap.IsValidTile(end)) {
    if (shadow != null) shadow.phase <- "invalid_end";
    return { ok = false, error = AIError.ERR_PRECONDITION_FAILED,
             errorText = "invalid airport footprint" };
  }
  if (OpexAirFootprintIsFlat(anchor, airport)) {
    if (shadow != null) shadow.phase <- "already_flat";
    return { ok = true, error = 0, errorText = "" };
  }
  if (!AITile.LevelTiles(anchor, end)) {
    local err = AIError.GetLastError();
    local errorText = AIError.GetLastErrorString();
    if (shadow != null) { shadow.command <- "failed"; shadow.commandError <- err; }
    if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES && townId >= 0) {
      OpexBoostTownRating(townId, 800, 40);
      if (!AITile.LevelTiles(anchor, end)) {
        err = AIError.GetLastError();
        errorText = AIError.GetLastErrorString();
        if (shadow != null) shadow.retryError <- err;
        if (err != AITile.ERR_AREA_ALREADY_FLAT) {
          if (shadow != null) shadow.phase <- "retry_failed";
          return { ok = false, error = err, errorText = errorText };
        }
      } else if (shadow != null) {
        shadow.retryError <- 0;
      }
    } else if (err != AITile.ERR_AREA_ALREADY_FLAT) {
      if (shadow != null) shadow.phase <- "command_failed";
      return { ok = false, error = err, errorText = errorText };
    }
  } else if (shadow != null) {
    shadow.command <- "ok";
    shadow.commandError <- 0;
  }
  if (!OpexAirFootprintIsFlat(anchor, airport)) {
    if (shadow != null) shadow.phase <- "postcheck_nonflat";
    return { ok = false, error = AIError.ERR_FLAT_LAND_REQUIRED,
             errorText = "airport footprint remains non-flat" };
  }
  if (shadow != null) shadow.phase <- "success";
  return { ok = true, error = 0, errorText = "" };
}

/* C78.2 : ERR_STATION_TOO_MANY_STATIONS_IN_TOWN est une propriete de la ville,
 * pas de l'ancre testee. Une seule reponse du moteur suffit donc a exclure cette
 * ville pour tout le scan courant, y compris pour les autres types d'aeroport. */
function OpexAirRememberTownStationLimit(probes, town, error)
{
  if (error != AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) return false;
  if (probes != null && ("stationLimitedTowns" in probes)) {
    probes.stationLimitedTowns.rawset(town.id, true);
  }
  OpexAirC78NoteNoSite(probes, "no_site_slot");
  return true;
}

/* Copie les compteurs de sondes. stationLimitedTowns est une table partagee avec
 * l'appelant : la copie est independante pour qu'un second scan ne la mute pas. */
function OpexAirCopySiteProbes(probes)
{
  local copy = {};
  foreach (k, v in probes) {
    if (typeof v == "table") {
      local inner = {};
      foreach (ik, iv in v) inner.rawset(ik, iv);
      copy.rawset(k, inner);
    } else {
      copy.rawset(k, v);
    }
  }
  return copy;
}

/* Un seul anneau r. Carre [villeÃƒâ€šÃ‚Â±r] moins [villeÃƒâ€šÃ‚Â±(r-1)], meme clamp carte/emprise
 * que le rejet ax+offX >= mapX. Equivalent a DistanceMax(ancre, ville) == r,
 * sans valuer l'interieur.
 * IsWaterTile / IsCoastTile : (tuile) -> bool, 0/1 dans Valuate.
 * GetClosestTown : (tuile) -> TownID. GetNearestTown : (tuile, type) -> TownID.
 * Ordre natif : Valuate(AIMap.GetTileX) puis Sort(VALUE, ASCENDING).
 * ScriptList range son set par paire (valeur, index). A X egal, l'index croissant
 * est Y croissant (index = y * mapX + x), soit (dx, dy) dans l'anneau.
 * Aucune table Squirrel par ancre. */
function OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY)
{
  local minX = townX - r;
  if (minX < 0) minX = 0;
  local minY = townY - r;
  if (minY < 0) minY = 0;
  local maxX = townX + r;
  local fitX = mapX - offX - 1;
  if (maxX > fitX) maxX = fitX;
  if (maxX >= mapX) maxX = mapX - 1;
  local maxY = townY + r;
  local fitY = mapY - offY - 1;
  if (maxY > fitY) maxY = fitY;
  if (maxY >= mapY) maxY = mapY - 1;
  if (minX > maxX || minY > maxY) return null;

  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(minX, minY), AIMap.GetTileIndex(maxX, maxY));

  local inner = r - 1;
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
  if (tiles.Count() == 0) return null;

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
  if (tiles.Count() == 0) return null;

  tiles.Valuate(AIMap.GetTileX);
  tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
  return tiles;
}

/* Anneaux r = 4..AIR_SITE_RADIUS, un par un. Le return historique sort tout de suite :
 * les anneaux suivants ne sont pas construits. useSiteCache faux : le mode check
 * ne reecrit pas AIR_SITE_CACHE. */
function OpexAirFindSiteListed(town, airport, probes, requiredSlotTownId, key, useSiteCache)
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
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    local ring = OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY);
    if (ring == null) continue;
    foreach (anchor, anchorX in ring) {
      if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
      local c4 = anchor + AIMap.GetTileIndex(offX, offY);
      if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;

      if (AIR_CHEAP_SITE) {
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
          continue;
        }
      } else {
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
      }

      if (used >= allowance) {
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        if (useSiteCache) AIR_SITE_CACHE[key] <- null;
        return { site = null, used = used, execLevels = execLevels, allowance = allowance };
      }
      if (probes.left <= 0) {
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        return { site = null, used = used, execLevels = execLevels, allowance = allowance };
      }

      local ok = false;
      if (AIR_CHEAP_SITE) {
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
            if (OpexAirCanLevelFootprint(anchor, airport, town.id)) {
              ok = true;
            }
          }
        }
      } else {
        local probe = AITestMode();
        ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            return { site = null, used = used, execLevels = execLevels, allowance = allowance };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
            ok = true;
          } else {
            AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
            if (!ok) {
              local retryErr = AIError.GetLastError();
              if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                if (useSiteCache) AIR_SITE_CACHE[key] <- null;
                return { site = null, used = used, execLevels = execLevels, allowance = allowance };
              }
              if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
            }
          }
        }
      }
      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (ok) {
        if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
        return {
          site = { town = town, anchor = anchor },
          used = used, execLevels = execLevels, allowance = allowance
        };
      }
    }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  return { site = null, used = used, execLevels = execLevels, allowance = allowance };
}

/* C96 : score relatif de placement uniquement. GetCargoProduction est utilise
 * ici comme compte de tuiles productrices dans le catchment physique ; ce
 * score ne devient jamais une demande mensuelle et n'entre pas dans C68. */
function OpexAirC96SiteCatchmentScore(anchor, airport, paxCargo)
{
  if (paxCargo < 0) return 0;
  return OpexAirAirportCatchmentProduction(anchor, airport.type, paxCargo);
}

/* V125 : un aeroport dont le catchment ne produit ni n'accepte de passagers ne
 * transporte rien (vu en jeu le 06/10 : « Accepte : Rien »). Seuil d'acceptation
 * OpenTTD = 8. Production comptee en tuiles, comme C96. */
function OpexAirSiteHasCatchment(anchor, airport, paxCargo)
{
  if (paxCargo < 0) return true;
  local radius = AIAirport.GetAirportCoverageRadius(airport.type);
  if (AITile.GetCargoAcceptance(anchor, paxCargo, airport.width, airport.height, radius) < 8) return false;
  return OpexAirAirportCatchmentProduction(anchor, airport.type, paxCargo) > 0;
}

function OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
                            valid, firstValidRing, bestRing, used)
{
  if (best == null) return;
  local firstDist = OpexAirDistanceToRect(town.tile, firstAnchor, airport.width, airport.height);
  local bestDist = OpexAirDistanceToRect(town.tile, best.anchor, airport.width, airport.height);
  AILog.Info("C96_SITE town=" + town.id
      + " pop=" + AITown.GetPopulation(town.id)
      + " type=" + airport.type
      + " first=" + firstAnchor + " first_score=" + firstScore
      + " best=" + best.anchor + " best_score=" + bestScore
      + " gain=" + (bestScore - firstScore)
      + " first_dist=" + firstDist + " best_dist=" + bestDist
      + " valid=" + valid + " first_ring=" + firstValidRing
      + " best_ring=" + bestRing + " probes=" + used);
}

/* C96 : meme vivier physique que V94, mais ne retourne pas le premier succes.
 * A partir du premier anneau constructible, conserver au plus MAX_VALID sites
 * valides et regarder au plus EXTRA_RINGS anneaux supplementaires. Le meilleur
 * compte de tuiles productrices PASS gagne ; a score egal, le premier site de
 * l'ordre V94 reste choisi. Demande, avion, economie et classement restent
 * strictement en aval et inchanges. */
function OpexAirFindSiteCatchmentListed(town, airport, probes, requiredSlotTownId, key, useSiteCache)
{
  local paxCargo = OpexAirDemandPaxCargo();
  if (paxCargo < 0) {
    return OpexAirFindSiteListed(town, airport, probes, requiredSlotTownId, key, useSiteCache);
  }

  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
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

      if (AIR_CHEAP_SITE) {
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
          continue;
        }
      } else {
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
      if (AIR_CHEAP_SITE) {
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
      } else {
        local probe = AITestMode();
        ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            return { site = null, used = used, execLevels = execLevels, allowance = allowance };
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
            ok = true;
          } else {
            AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
            if (!ok) {
              local retryErr = AIError.GetLastError();
              if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                if (useSiteCache) AIR_SITE_CACHE[key] <- null;
                return { site = null, used = used, execLevels = execLevels, allowance = allowance };
              }
              if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
            }
          }
        }
      }

      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (!ok) continue;

      if (AIR_SITE_MIN_CATCHMENT && !OpexAirSiteHasCatchment(anchor, airport, paxCargo)) {
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

function OpexAirV94Report(town, legacy, listed, probes, copy)
{
  local ancL = legacy.site == null ? -1 : legacy.site.anchor;
  local ancN = listed.site == null ? -1 : listed.site.anchor;
  local cheapL = ("cheapSkip" in probes) ? probes.cheapSkip : -1;
  local cheapN = ("cheapSkip" in copy) ? copy.cheapSkip : -1;
  local testedL = ("tested" in probes) ? probes.tested : -1;
  local testedN = ("tested" in copy) ? copy.tested : -1;
  local limL = 0;
  local limN = 0;
  if (("stationLimitedTowns" in probes) && (town.id in probes.stationLimitedTowns)) limL = 1;
  if (("stationLimitedTowns" in copy) && (town.id in copy.stationLimitedTowns)) limN = 1;
  local same = ancL == ancN && legacy.used == listed.used && legacy.execLevels == listed.execLevels
      && legacy.allowance == listed.allowance
      && probes.left == copy.left && probes.townsLeft == copy.townsLeft
      && cheapL == cheapN && testedL == testedN && limL == limN;
  AILog.Info("V94_CHECK " + (same ? "OK" : "DIFF")
      + " town=" + town.id
      + " anchor=" + ancL + "/" + ancN
      + " used=" + legacy.used + "/" + listed.used
      + " left=" + probes.left + "/" + copy.left
      + " tested=" + testedL + "/" + testedN
      + " cheap=" + cheapL + "/" + cheapN
      + " exec=" + legacy.execLevels + "/" + listed.execLevels
      + " allow=" + legacy.allowance + "/" + listed.allowance
      + " lim=" + limL + "/" + limN);
}

/* Le scan historique a deja decide. Le second passage ne touche pas le cache
 * et travaille sur la copie des sondes prise avant ce scan. */
function OpexAirV94Finish(town, airport, requiredSlotTownId, probes, copy, key, site, used, execLevels, allowance)
{
  local legacy = { site = site, used = used, execLevels = execLevels, allowance = allowance };
  local listed = OpexAirFindSiteListed(town, airport, copy, requiredSlotTownId, key, false);
  OpexAirV94Report(town, legacy, listed, probes, copy);
  return site;
}

/* Trouve la premiere ancre constructible, par couronnes autour de la ville. L'ancre est bien le
 * coin haut-gauche attendu par BuildAirport. La couverture est testee contre le rectangle entier,
 * pas seulement contre son coin. */
function OpexAirFindSite(town, airport, probes, requiredSlotTownId = -1)
{
  if (C60_TOWN_RATING_PROBE) {
    OpexC60ObserveTownRating("air", "find_site", town.id);
  }
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
  if (probes != null && ("stationLimitedTowns" in probes)
      && (town.id in probes.stationLimitedTowns)) return null;
  local key = town.id + "_" + airport.type;
  /* C83 cible : le cache historique est indexe par ville commerciale/type.
   * Une course au slot exige en plus ClosestTown(anchor)==ville cible ; ne pas
   * reutiliser ni ecrire ce cache dans ce chemin rare. */
  local useSiteCache = AIR_SITE_CACHE_ENABLED && requiredSlotTownId < 0;
  if (useSiteCache && (key in AIR_SITE_CACHE)) {
    local cachedAnchor = AIR_SITE_CACHE[key];
    if (cachedAnchor == null) {
      return null;
    }
    local offX = airport.width - 1;
    local offY = airport.height - 1;
    local mapX = AIMap.GetMapSizeX();
    local mapY = AIMap.GetMapSizeY();
    local ax = AIMap.GetTileX(cachedAnchor);
    local ay = AIMap.GetTileY(cachedAnchor);
    if (ax + offX < mapX && ay + offY < mapY) {
      local c4 = cachedAnchor + AIMap.GetTileIndex(offX, offY);
      if (!AITile.IsWaterTile(cachedAnchor) && !AITile.IsCoastTile(cachedAnchor) &&
          !AITile.IsWaterTile(c4) && !AITile.IsCoastTile(c4) &&
          AIAirport.GetNearestTown(cachedAnchor, airport.type) == town.id &&
          (!AIR_CHEAP_SITE || OpexAirFootprintCheapOk(cachedAnchor, airport)) &&
          (!AIR_SITE_MIN_CATCHMENT
           || OpexAirSiteHasCatchment(cachedAnchor, airport, OpexAirDemandPaxCargo()))) {
        local ok = false;
        if (AIR_CHEAP_SITE) {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(cachedAnchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       OpexAirCanLevelFootprint(cachedAnchor, airport, town.id)) {
              /* G7Ãƒâ€šÃ‚Â§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              ok = true;
            }
          }
        } else {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(cachedAnchor, OpexAirFootprintEnd(cachedAnchor, airport));
              ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
              if (!ok) {
                local retryErr = AIError.GetLastError();
                if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                  AIR_SITE_CACHE[key] <- null;
                  return null;
                }
                if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
              }
            }
          }
        }
        if ("tested" in probes) probes.tested++;
        if (ok) return { town = town, anchor = cachedAnchor };
      }
    }
    delete AIR_SITE_CACHE[key];
  }

  /* V94 : defaut 1, la liste decide ; a 0, le balayage ci-dessous (origine). Le check
   * execute ce balayage comme decision, puis la liste sur une copie. */
  local v94Copy = null;
  if (V94_AIR_SITE_CHECK) v94Copy = OpexAirCopySiteProbes(probes);
  if (C96_AIR_SITE_CATCHMENT) {
    return OpexAirFindSiteCatchmentListed(town, airport, probes, requiredSlotTownId, key, useSiteCache).site;
  }
  if (V94_AIR_SITE_LIST && !V94_AIR_SITE_CHECK) {
    return OpexAirFindSiteListed(town, airport, probes, requiredSlotTownId, key, useSiteCache).site;
  }

  /* Le budget global reste borne, mais il est partage entre les villes encore
   * a sonder. Elargir le vivier ne peut donc pas multiplier sans borne les
   * AITestMode : davantage de villes donne moins de sondes par ville. */
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
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
        if (requiredSlotTownId >= 0 && AITile.GetClosestTown(anchor) != requiredSlotTownId) continue;
        if (AIAirport.GetNearestTown(anchor, airport.type) != town.id) continue;

        if (AIR_CHEAP_SITE) {
          /* Eau/riviere/cote sur toute l'emprise, C4, et IsBuildableRectangle : sans AITestMode.
           * La sonde ci-dessous ne tourne plus que sur un hit cheap. */
          if (!OpexAirFootprintCheapOk(anchor, airport)) {
            if ("cheapSkip" in probes) probes.cheapSkip++;
            continue;
          }
        } else {
          /* Filtre de platitude prÃƒÆ’Ã‚Â©alable (docs/taches.md Ãƒâ€šÃ‚Â§0 tervicies point 5 & C4, faÃƒÆ’Ã‚Â§on AAAHogEx) :
           * Si l'ÃƒÆ’Ã‚Â©cart d'altitude au sein de l'emprise dÃƒÆ’Ã‚Â©passe 1 niveau, le terrassement ÃƒÆ’Ã‚Â©choue
           * massivement ou coÃƒÆ’Ã‚Â»te trop cher. Rejet ÃƒÆ’Ã‚Â©liminatoire avant d'entrer en AITestMode. */
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
        }

        if (used >= allowance) {
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          if (useSiteCache) AIR_SITE_CACHE[key] <- null;
          if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
          return null;
        }
        if (probes.left <= 0) {
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
          return null;
        }

        local ok = false;
        if (AIR_CHEAP_SITE) {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              if (useSiteCache) AIR_SITE_CACHE[key] <- null;
              if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(anchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       execLevels < 3) {
              execLevels++;
              /* G7Ãƒâ€šÃ‚Â§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              if (OpexAirCanLevelFootprint(anchor, airport, town.id)) {
                ok = true;
              }
            }
          }
        } else {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              if (useSiteCache) AIR_SITE_CACHE[key] <- null;
              if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
              ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
              if (!ok) {
                local retryErr = AIError.GetLastError();
                if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                  if (useSiteCache) AIR_SITE_CACHE[key] <- null;
                  if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
                  return null;
                }
                if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
              }
            }
          }
        }
        used++;
        probes.left--;
        if ("tested" in probes) probes.tested++;
        if (ok) {
          if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
          local found = { town = town, anchor = anchor };
          if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, found, used, execLevels, allowance);
          return found;
        }
      }
    }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  if (V94_AIR_SITE_CHECK) return OpexAirV94Finish(town, airport, requiredSlotTownId, probes, v94Copy, key, null, used, execLevels, allowance);
  return null;
}

/* C78.2 : revalidation legere d'un site deja trouve. Le scan complet peut
 * suspendre pendant que la carte evolue ; ce predicat est donc rejoue juste
 * avant le classement, puis par le portefeuille avant sa propre selection. */
function OpexAirSiteStillBuildable(site, airport, plane, reuse, stationLimitedTowns = null)
{
  /* V133 : a 0, seul ce booleen. Le code n'est lu que si le reglage est actif. */
  if (V133_AIR_BUILD_RETRY) V133_AIR_LAST_SITE_ERROR = 0;
  if (site == null || airport == null || plane == null || !AIMap.IsValidTile(site.anchor)) return false;
  if (OpexAirRecoveryOwnsAirport(site.anchor)) return false;
  if (reuse) {
    return AIAirport.IsAirportTile(site.anchor)
        && OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(site.anchor), plane.planeType);
  }
  if (!("town" in site) || site.town == null || !("id" in site.town)) return false;
  if (stationLimitedTowns != null && (site.town.id in stationLimitedTowns)) return false;
  if (AIAirport.GetNearestTown(site.anchor, airport.type) != site.town.id) return false;
  /* C83 : l'identite physique du creneau (ClosestTown de l'ancre) ne contraint que les sites
   * issus d'une course vers un creneau precis (c83SlotTown). Un site AIR ordinaire garde le seul
   * critere historique GetNearestTown : l'appliquer partout freinait l'expansion aerienne
   * (20x10 du 2026-09-24 : -2,1 creneaux, -13 % de vehicules, fail_primary). */
  if (C83_FIXES && ("c83SlotTown" in site) && site.c83SlotTown >= 0
      && OpexAirSlotTownId(site.anchor) != site.c83SlotTown) return false;
  if (AIR_CHEAP_SITE && !OpexAirFootprintCheapOk(site.anchor, airport)) return false;

  local ok = false;
  local error = 0;
  {
    local probe = AITestMode();
    ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW);
    if (!ok) error = AIError.GetLastError();
  }
  if (ok) return true;

  if (error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) {
    if (stationLimitedTowns != null) stationLimitedTowns.rawset(site.town.id, true);
    if (V133_AIR_BUILD_RETRY) V133_AIR_LAST_SITE_ERROR = error;
    return false;
  }
  if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES
      && OpexAirFootprintIsFlat(site.anchor, airport)) return true;
  if ((error == AIError.ERR_LOCAL_AUTHORITY_REFUSES || error == AIError.ERR_FLAT_LAND_REQUIRED)
      && OpexAirCanLevelFootprint(site.anchor, airport, site.town.id)) return true;
  if (V133_AIR_BUILD_RETRY) V133_AIR_LAST_SITE_ERROR = error;
  return false;
}
