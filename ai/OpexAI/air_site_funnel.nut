/* Entonnoir de sites AIR (air_site_funnel=1). Le defaut 0 laisse la spirale.
 * Bandes de Chebyshev 4..8, 9..14 puis 15..AIR_SITE_RADIUS. Chaque bande est
 * l'intersection du domaine historique (distance de Manhattan au rectangle
 * <= AIR_SITE_RADIUS, noyau r < 4 retire) avec l'anneau. La coupe Manhattan
 * reste le rayon historique, pas le rayon de la bande.
 * Pour un grand aeroport (portee >= 9) les deux premieres bandes sont un seul
 * Valuate 4..14 : la bande 9 peut encore couvrir le centre, la couper en deux
 * paierait les filtres deux fois. On ne value 15..25 que si aucun site retenu
 * ne couvre le centre a rang maximal. La ville 31 du smoke 3 gagne dix tuiles
 * a l'anneau 10, donc 4..14 reste entier.
 * IsBuildableRectangle en tete. Le rectangle de nivellement est (w+1) x (h+1) :
 * un bord hors carte, non constructible, eau ou denivelee >= 2 est ecarte.
 * Une denivelee de 1 coute AIR_SITE_FUNNEL_SLOPE_PENALTY. L'ancre 21013 ne
 * perd pas sur cette penalite (29 - 4 reste au-dessus d'un site plat a 14) :
 * c'est le bord non constructible qui l'ecarte. Les sondes ne courent que
 * dans l'ordre du rang, par lots, et le premier succes est retenu.
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

function OpexAirFunnelTrace(town, airport, tiles, afterNative, checked, probesUsed, ok, score, bestPossible, reason, band = -1, pen = 0, peak = -1, listHit = 0)
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
      + " reason=" + reason
      + " band=" + band
      + " pen=" + pen
      + " peak=" + peak
      + " list=" + listHit);
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

function OpexAirFunnelBox(townX, townY, offX, offY, mapX, mapY, radius)
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

/* Noyau Chebyshev <= inner. La spirale commence a r = 4, donc inner = 3. */
function OpexAirFunnelDropCore(tiles, townX, townY, minX, minY, maxX, maxY, inner)
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

function OpexAirFunnelTiles(town, airport, requiredSlotTownId, paxCargo, rInner, rOuter)
{
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);
  local box = OpexAirFunnelBox(townX, townY, offX, offY, mapX, mapY, rOuter);
  if (box == null) return null;
  box = OpexAirFunnelInsetVoid(box, mapX, mapY);
  if (box == null) return null;
  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(box.minX, box.minY), AIMap.GetTileIndex(box.maxX, box.maxY));
  OpexAirFunnelDropCore(tiles, townX, townY, box.minX, box.minY, box.maxX, box.maxY, rInner - 1);
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
  if (AIR_SITE_FUNNEL_KEEP_TOP > 0) tiles.KeepTop(AIR_SITE_FUNNEL_KEEP_TOP);
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

/* Portee Chebyshev d'une ancre qui peut encore couvrir le centre.
 * OpenTTD etend le rectangle de radius sur X et sur Y. */
function OpexAirFunnelReach(airport)
{
  local radius = AIAirport.GetAirportCoverageRadius(airport.type);
  local reachX = airport.width - 1 + radius;
  local reachY = airport.height - 1 + radius;
  if (reachX > reachY) return reachX;
  return reachY;
}

function OpexAirFunnelCoversTown(anchor, townTile, airport)
{
  local radius = AIAirport.GetAirportCoverageRadius(airport.type);
  return OpexAirB9TileInExpandedRect(townTile, anchor, airport.width, airport.height, radius);
}

function OpexAirFunnelOuterStop(anchor, townTile, airport, chosenAdj, peakAdj, nextMin)
{
  if (AIR_SITE_FUNNEL_BOUND_ON <= 0) return false;
  if (anchor == null) return false;
  local reach = OpexAirFunnelReach(airport);
  /* Hors de portee, la bande suivante ne couvre plus le centre. Un pic
   * non retenu est deja dans la bande courante : ne pas la revaluer. */
  if (nextMin <= reach) return false;
  return OpexAirFunnelCoversTown(anchor, townTile, airport);
}

/* -1 : bord hors carte, non constructible, eau, ou denivelee >= 2.
 * 0 : bord plat et constructible. Sinon penalite de pente douce.
 * L'ancre 21013 (ville 6, score 29) n'a qu'une denivelee de 1 : la penalite
 * 4 ne la depasse pas, et le chantier echoue en 263. Le bord non constructible
 * l'ecarte. Ce rejet sur toute la boite r <= 25 vidait des villes (19
 * aeroports) : il ne s'applique qu'aux tuiles deja triees, dans la boite 4..14. */
function OpexAirFunnelTerraPenalty(anchor, airport)
{
  if (anchor in AIR_SITE_FUNNEL_DEAD) return -1;
  local w = airport.width;
  local h = airport.height;
  local ax = AIMap.GetTileX(anchor);
  local ay = AIMap.GetTileY(anchor);
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  if (ax + w >= mapX || ay + h >= mapY) return -1;
  local endTile = anchor + AIMap.GetTileIndex(w, h);
  if (!AIMap.IsValidTile(endTile)) return -1;
  /* Bord seulement. Une maison sur sol plat se demolit ; une maison sur
   * une pente, ou une denivelee >= 2, laisse l'emprise non plate (erreur 263).
   * Rejeter tout bord non constructible vidait la ville 17. */
  local minH = AITile.GetMinHeight(anchor);
  local maxH = AITile.GetMaxHeight(anchor);
  local blocked = false;
  for (local dx = 0; dx <= w; dx++) {
    for (local dy = 0; dy <= h; dy++) {
      if (dx < w && dy < h) continue;
      if (ax + dx >= mapX || ay + dy >= mapY) return -1;
      local t = AIMap.GetTileIndex(ax + dx, ay + dy);
      if (!AIMap.IsValidTile(t)) return -1;
      if (AITile.IsWaterTile(t) || AITile.IsCoastTile(t) || AITile.IsRiverTile(t)) blocked = true;
      else if (!AITile.IsBuildable(t)) blocked = true;
      local lo = AITile.GetMinHeight(t);
      local hi = AITile.GetMaxHeight(t);
      if (lo < minH) minH = lo;
      if (hi > maxH) maxH = hi;
      if (maxH - minH >= 2) return -1;
    }
  }
  if (blocked && maxH - minH >= 1) return -1;
  if (maxH - minH >= 1) return AIR_SITE_FUNNEL_SLOPE_PENALTY;
  return 0;
}

function OpexAirFunnelPenalty(anchor, airport)
{
  if (anchor in AIR_SITE_FUNNEL_PEN) return AIR_SITE_FUNNEL_PEN[anchor];
  local pen = OpexAirFunnelTerraPenalty(anchor, airport);
  AIR_SITE_FUNNEL_PEN.rawset(anchor, pen);
  return pen;
}

function OpexAirFunnelRawOf(anchor, fallback)
{
  if (anchor in AIR_SITE_FUNNEL_RAW) return AIR_SITE_FUNNEL_RAW[anchor];
  return fallback;
}

/* Prefixe trie par production brute. SetValue apres le parcours : il
 * reordonne la liste. On s'arrete quand la production brute ne peut plus
 * battre le meilleur rang deja classe, ou au plafond de controles. */
function OpexAirFunnelRank(tiles, airport)
{
  if (AIR_SITE_FUNNEL_COST_ON <= 0) return;
  local anchors = [];
  local raws = [];
  local pens = [];
  local bestAdj = -1;
  local anchor = tiles.Begin();
  local guard = 0;
  while (!tiles.IsEnd() && guard < AIR_SITE_FUNNEL_COST_CAP) {
    local raw = tiles.GetValue(anchor);
    if (bestAdj >= 0 && raw < bestAdj) break;
    local pen = OpexAirFunnelPenalty(anchor, airport);
    anchors.append(anchor);
    raws.append(raw);
    pens.append(pen);
    AIR_SITE_FUNNEL_RAW.rawset(anchor, raw);
    if (pen >= 0) {
      local adj = raw - pen;
      if (adj > bestAdj) bestAdj = adj;
    }
    guard++;
    anchor = tiles.Next();
  }
  for (local i = 0; i < anchors.len(); i++) {
    if (pens[i] < 0) tiles.SetValue(anchors[i], -1);
    else tiles.SetValue(anchors[i], raws[i] - pens[i]);
  }
  tiles.KeepAboveValue(-1);
  tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
}

function OpexAirFunnelBandAt(index)
{
  if (AIR_SITE_FUNNEL_BANDS_ON <= 0) {
    if (index == 0) return { inner = 4, outer = AIR_SITE_RADIUS };
    return null;
  }
  if (index == 0) return { inner = 4, outer = 8 };
  if (index == 1) return { inner = 9, outer = 14 };
  if (index == 2) return { inner = 15, outer = AIR_SITE_RADIUS };
  return null;
}

/* Grand aeroport : un Valuate 4..14, puis 15..25 seulement si le centre
 * n'est pas couvert. Petit aeroport : 4..8 peut s'arreter (portee 7 < 9). */
function OpexAirFunnelSchedule(airport)
{
  local bands = [];
  if (AIR_SITE_FUNNEL_BANDS_ON <= 0) {
    bands.append(OpexAirFunnelBandAt(0));
    return bands;
  }
  local reach = 0;
  if (AIR_SITE_FUNNEL_BOUND_ON > 0) reach = OpexAirFunnelReach(airport);
  if (reach >= 9) {
    bands.append({ inner = 4, outer = 14 });
    bands.append(OpexAirFunnelBandAt(2));
    return bands;
  }
  bands.append(OpexAirFunnelBandAt(0));
  bands.append(OpexAirFunnelBandAt(1));
  bands.append(OpexAirFunnelBandAt(2));
  return bands;
}

function OpexAirFunnelListFresh()
{
  local month = OpexAir0310SiteValidityMonth();
  if (month != AIR_SITE_FUNNEL_LIST_MONTH) {
    AIR_SITE_FUNNEL_LIST.clear();
    AIR_SITE_FUNNEL_LIST_MONTH = month;
  }
}

function OpexAirFunnelCollect(tiles, anchors, scores)
{
  local room = AIR_SITE_FUNNEL_LIST_CAP - anchors.len();
  if (room > 8) room = 8;
  if (room <= 0) return;
  local anchor = tiles.Begin();
  local n = 0;
  while (!tiles.IsEnd() && n < room) {
    anchors.append(anchor);
    scores.append(OpexAirFunnelRawOf(anchor, tiles.GetValue(anchor)));
    n++;
    anchor = tiles.Next();
  }
}

function OpexAirFunnelRememberList(key, anchors, scores, bestAnchor, bestRaw)
{
  if (AIR_SITE_FUNNEL_LIST_ON <= 0) return;
  if (bestAnchor == null) return;
  local month = OpexAir0310SiteValidityMonth();
  if (month != AIR_SITE_FUNNEL_LIST_MONTH) return;
  /* Le site retenu d'abord : un rejeu ne doit pas reeligir une bande
   * precedente deja battue. */
  local outA = [];
  local outS = [];
  outA.append(bestAnchor);
  outS.append(bestRaw);
  for (local i = 0; i < anchors.len(); i++) {
    if (outA.len() >= AIR_SITE_FUNNEL_LIST_CAP) break;
    if (anchors[i] == bestAnchor) continue;
    outA.append(anchors[i]);
    outS.append(scores[i]);
  }
  AIR_SITE_FUNNEL_LIST.rawset(key, { anchors = outA, scores = outS });
}

function OpexAirFunnelCommit(town, airport, anchor, score, used, rawTiles, afterNative, checked, band, pen, peak, listHit, key, useSiteCache)
{
  local site = { town = town, anchor = anchor };
  local ring = OpexAirFunnelChebyshev(anchor, town.tile);
  OpexAirC96LogChoice(town, airport, anchor, score, site, score, 1, ring, ring, used);
  if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
  OpexAirFunnelTrace(town, airport, rawTiles, afterNative, checked, used, 1, score, 1, "ok", band, pen, peak, listHit);
  return site;
}

function OpexAirFunnelTryAnchor(anchor, town, airport, probes, paxCargo, allowance, used, execLevels)
{
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  if (OpexAirDistanceToRect(town.tile, anchor, w, h) > AIR_SITE_RADIUS) {
    return { kind = "skip", used = used, execLevels = execLevels, pen = 0 };
  }
  local c4 = anchor + AIMap.GetTileIndex(offX, offY);
  if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) {
    return { kind = "skip", used = used, execLevels = execLevels, pen = 0 };
  }
  local pen = 0;
  if (AIR_SITE_FUNNEL_COST_ON > 0) {
    pen = OpexAirFunnelPenalty(anchor, airport);
    if (pen < 0) return { kind = "skip", used = used, execLevels = execLevels, pen = pen };
  }
  if (!OpexAirFootprintCheapOk(anchor, airport)) {
    if ("cheapSkip" in probes) probes.cheapSkip++;
    return { kind = "cheap", used = used, execLevels = execLevels, pen = pen };
  }
  if (used >= allowance || probes.left <= 0) {
    return { kind = "budget", used = used, execLevels = execLevels, pen = pen };
  }
  local probed = OpexAirFunnelProbe(anchor, airport, town, probes, execLevels);
  execLevels = probed.execLevels;
  if (probed.limited) {
    return { kind = "limited", used = used, execLevels = execLevels, pen = pen };
  }
  used++;
  probes.left--;
  if ("tested" in probes) probes.tested++;
  if (probed.ok && OpexAirSiteHasCatchment(anchor, airport, paxCargo)) {
    return { kind = "site", used = used, execLevels = execLevels, pen = pen };
  }
  if (probed.ok && ("deadCatchment" in probes)) probes.deadCatchment++;
  return { kind = "fail", used = used, execLevels = execLevels, pen = pen };
}

function OpexAirFunnelWalk(tiles, town, airport, probes, paxCargo, allowance, used, execLevels, bestAdj)
{
  local checked = 0;
  local anchor = tiles.Begin();
  while (!tiles.IsEnd()) {
    if (used >= allowance || probes.left <= 0) {
      return { kind = "budget", used = used, execLevels = execLevels, checked = checked, anchor = null, pen = 0, adj = -1 };
    }
    if (bestAdj >= 0 && tiles.GetValue(anchor) <= bestAdj) break;
    local batch = 0;
    local stop = false;
    while (batch < AIR_SITE_FUNNEL_BATCH && !tiles.IsEnd()) {
      if (bestAdj >= 0 && tiles.GetValue(anchor) <= bestAdj) {
        stop = true;
        break;
      }
      local tried = OpexAirFunnelTryAnchor(anchor, town, airport, probes, paxCargo, allowance, used, execLevels);
      used = tried.used;
      execLevels = tried.execLevels;
      if (tried.kind == "skip") {
        anchor = tiles.Next();
        continue;
      }
      batch++;
      checked++;
      if (tried.kind == "budget") {
        return { kind = "budget", used = used, execLevels = execLevels, checked = checked, anchor = null, pen = 0, adj = -1 };
      }
      if (tried.kind == "limited") {
        return { kind = "limited", used = used, execLevels = execLevels, checked = checked, anchor = anchor, pen = tried.pen, adj = -1 };
      }
      if (tried.kind == "site") {
        return { kind = "site", used = used, execLevels = execLevels, checked = checked,
            anchor = anchor, pen = tried.pen, adj = tiles.GetValue(anchor) };
      }
      anchor = tiles.Next();
    }
    if (stop) break;
  }
  return { kind = "none", used = used, execLevels = execLevels, checked = checked, anchor = null, pen = 0, adj = -1 };
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

function OpexAirFunnelReplay(town, airport, probes, key, useSiteCache, paxCargo, allowance, used, execLevels)
{
  local packed = AIR_SITE_FUNNEL_LIST[key];
  local anchors = packed.anchors;
  local scores = packed.scores;
  local checked = 0;
  for (local i = 0; i < anchors.len(); i++) {
    local anchor = anchors[i];
    if (used >= allowance || probes.left <= 0) {
      return { kind = "budget", used = used, execLevels = execLevels, checked = checked };
    }
    local tried = OpexAirFunnelTryAnchor(anchor, town, airport, probes, paxCargo, allowance, used, execLevels);
    used = tried.used;
    execLevels = tried.execLevels;
    if (tried.kind == "skip") continue;
    checked++;
    if (tried.kind == "budget") {
      return { kind = "budget", used = used, execLevels = execLevels, checked = checked };
    }
    if (tried.kind == "limited") {
      if (useSiteCache) AIR_SITE_CACHE[key] <- null;
      OpexAirFunnelTrace(town, airport, 0, anchors.len(), checked, used, 0, -1, 0, "station_limit", -1, 0, -1, 1);
      return { kind = "limited", used = used, execLevels = execLevels, checked = checked };
    }
    if (tried.kind == "site") {
      local site = OpexAirFunnelCommit(town, airport, anchor, scores[i], used, 0, anchors.len(), checked, -1, tried.pen, scores[i], 1, key, useSiteCache);
      return { kind = "site", site = site, used = used, execLevels = execLevels, checked = checked };
    }
  }
  if (key in AIR_SITE_FUNNEL_LIST) delete AIR_SITE_FUNNEL_LIST[key];
  return { kind = "miss", used = used, execLevels = execLevels, checked = checked };
}

function OpexAirFunnelSearch(town, airport, probes, requiredSlotTownId, key, useSiteCache, paxCargo)
{
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  AIR_SITE_FUNNEL_RAW.clear();
  AIR_SITE_FUNNEL_PEN.clear();
  if (AIR_SITE_FUNNEL_LIST_ON > 0 && requiredSlotTownId < 0) {
    OpexAirFunnelListFresh();
    if (key in AIR_SITE_FUNNEL_LIST) {
      local replay = OpexAirFunnelReplay(town, airport, probes, key, useSiteCache, paxCargo, allowance, used, execLevels);
      if (replay.kind == "site") return replay.site;
      if (replay.kind == "limited") return null;
      if (replay.kind == "budget") {
        OpexAirFunnelBudget(town, airport, probes, key, useSiteCache, replay.used, allowance, 0, 0, replay.checked);
        return null;
      }
      used = replay.used;
      execLevels = replay.execLevels;
    }
  }
  local bestAnchor = null;
  local bestRaw = -1;
  local bestAdj = -1;
  local bestPen = 0;
  local bestBand = -1;
  local peakAdj = -1;
  local tilesN = 0;
  local afterNative = 0;
  local checked = 0;
  local storedA = [];
  local storedS = [];
  local bands = OpexAirFunnelSchedule(airport);
  for (local index = 0; index < bands.len(); index++) {
    local band = bands[index];
    if (band == null) continue;
    if (band.inner > band.outer) continue;
    /* Avant de valuer la bande : un site deja admis couvre le centre et
     * cette bande ne peut plus le couvrir. On ne paie pas ses Valuate. */
    if (bestAnchor != null && OpexAirFunnelOuterStop(bestAnchor, town.tile, airport, bestAdj, peakAdj, band.inner)) {
      OpexAirFunnelRememberList(key, storedA, storedS, bestAnchor, bestRaw);
      return OpexAirFunnelCommit(town, airport, bestAnchor, bestRaw, used, tilesN, afterNative, checked, bestBand, bestPen, peakAdj, 0, key, useSiteCache);
    }
    local packed = OpexAirFunnelTiles(town, airport, requiredSlotTownId, paxCargo, band.inner, band.outer);
    if (packed == null) continue;
    tilesN += packed.raw;
    local tiles = packed.tiles;
    local nativeCount = tiles.Count();
    afterNative += nativeCount;
    if (nativeCount == 0) continue;
    OpexAirFunnelRank(tiles, airport);
    if (tiles.Count() == 0) continue;
    local bandPeak = tiles.GetValue(tiles.Begin());
    if (bandPeak > peakAdj) peakAdj = bandPeak;
    if (AIR_SITE_FUNNEL_LIST_ON > 0) OpexAirFunnelCollect(tiles, storedA, storedS);
    local walked = OpexAirFunnelWalk(tiles, town, airport, probes, paxCargo, allowance, used, execLevels, bestAdj);
    used = walked.used;
    execLevels = walked.execLevels;
    checked += walked.checked;
    if (walked.kind == "limited") {
      if (useSiteCache) AIR_SITE_CACHE[key] <- null;
      OpexAirFunnelTrace(town, airport, tilesN, afterNative, checked, used, 0, -1, 0, "station_limit", band.outer, 0, peakAdj, 0);
      return null;
    }
    if (walked.kind == "budget") {
      if (bestAnchor != null) {
        OpexAirFunnelRememberList(key, storedA, storedS, bestAnchor, bestRaw);
        return OpexAirFunnelCommit(town, airport, bestAnchor, bestRaw, used, tilesN, afterNative, checked, bestBand, bestPen, peakAdj, 0, key, useSiteCache);
      }
      OpexAirFunnelBudget(town, airport, probes, key, useSiteCache, used, allowance, tilesN, afterNative, checked);
      return null;
    }
    if (walked.kind == "site") {
      bestAnchor = walked.anchor;
      bestRaw = OpexAirFunnelRawOf(walked.anchor, tiles.GetValue(walked.anchor));
      bestAdj = walked.adj;
      bestPen = walked.pen;
      bestBand = band.outer;
    }
  }
  if (bestAnchor != null) {
    OpexAirFunnelRememberList(key, storedA, storedS, bestAnchor, bestRaw);
    return OpexAirFunnelCommit(town, airport, bestAnchor, bestRaw, used, tilesN, afterNative, checked, bestBand, bestPen, peakAdj, 0, key, useSiteCache);
  }
  OpexAirFunnelStoreMiss(key, useSiteCache, used, allowance, probes.left);
  local reason = "exhausted";
  if (tilesN == 0) reason = "empty";
  else if (afterNative == 0) reason = "no_native";
  OpexAirFunnelTrace(town, airport, tilesN, afterNative, checked, used, 0, -1, 1, reason);
  return null;
}
