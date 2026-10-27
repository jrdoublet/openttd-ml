/* air_site_funnel=1 : meme spirale que le defaut (anneaux, choix C96,
 * budgets, cache historique, generateur PO01C). Seul le predicat d'emprise
 * tuile par tuile est rebranche sur une AITileList. Le booleen reste celui
 * de OpexAirFootprintCheapOk : rectangle constructible, aucune tuile invalide,
 * eau, cote ou riviere, et max(GetMaxHeight) - min(GetMinHeight) < 2.
 * L'ancre est dans le rectangle, donc l'initialisation min/max sur l'ancre
 * ne change pas le booleen.
 * AIR_SITE_SEARCH_OPS cumule chaque OpexAirFindSite, scan finalise ou non.
 * La ligne AIR_SITE_SEARCH est ecrite apres la mesure : elle n'entre pas
 * dans le cumul. Pas de Save : telemetrie de partie. */
OpexAirFindSiteSpiral <- OpexAirFindSite;

function OpexAirSiteSearchNote(reason)
{
  local date = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  AILog.Info("AIR_SITE_SEARCH ops=" + AIR_SITE_SEARCH_OPS
      + " calls=" + AIR_SITE_SEARCH_CALLS
      + " month=" + month
      + " reason=" + reason);
}

function OpexAirFindSite(town, airport, probes, requiredSlotTownId = -1)
{
  local mark = OpexOpsMeasureBegin();
  AIR_SITE_OPS_MARK = mark;
  local site = OpexAirFindSiteSpiral(town, airport, probes, requiredSlotTownId);
  local spent = OpexOpsMeasureEnd(mark);
  if (spent > 0) AIR_SITE_SEARCH_OPS += spent;
  AIR_SITE_SEARCH_CALLS++;
  OpexAirSiteSearchNote("call");
  return site;
}

/* Meme porte que la boucle Squirrel. IsBuildableRectangle d'abord : il
 * refuse maisons, industries, rail, mer et riviere, et laisse passer le
 * cote. Le cote, l'eau et la riviere sont repris sur chaque tuile. */
function OpexAirFootprintCheapOkNative(anchor, airport)
{
  local w = airport.width;
  local h = airport.height;
  if (!AITile.IsBuildableRectangle(anchor, w, h)) return false;
  local endTile = anchor + AIMap.GetTileIndex(w - 1, h - 1);
  if (!AIMap.IsValidTile(anchor) || !AIMap.IsValidTile(endTile)) return false;
  local tiles = AITileList();
  tiles.AddRectangle(anchor, endTile);
  local need = w * h;
  if (tiles.Count() != need) return false;
  tiles.Valuate(AITile.IsWaterTile);
  tiles.KeepValue(0);
  if (tiles.Count() != need) return false;
  tiles.Valuate(AITile.IsCoastTile);
  tiles.KeepValue(0);
  if (tiles.Count() != need) return false;
  tiles.Valuate(AITile.IsRiverTile);
  tiles.KeepValue(0);
  if (tiles.Count() != need) return false;
  tiles.Valuate(AITile.GetMinHeight);
  tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
  local minH = tiles.GetValue(tiles.Begin());
  tiles.Valuate(AITile.GetMaxHeight);
  tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
  local maxH = tiles.GetValue(tiles.Begin());
  if (maxH - minH >= 2) return false;
  return true;
}

function OpexAirFunnelInstall()
{
  if (AIR_SITE_FUNNEL <= 0) return;
  ::OpexAirFootprintCheapOk <- OpexAirFootprintCheapOkNative;
}
