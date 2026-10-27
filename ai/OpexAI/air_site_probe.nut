/* Loaded only by the early Start branch. No scheduler, loan, vehicle or company
 * command is reachable. Test mode remains alive for the whole diagnostic.
 * No Save/Load contract: fresh solo games only; observations are transient.
 * Cost is the AIR_SITE_SEARCH tick-accounted VM estimate, not native CPU time.
 */
require("air_site_probe_initial.nut");
require("air_site_probe_funnel.nut");

AIR_PROBE_FUNNEL_BATCH <- 5;
AIR_PROBE_FUNNEL_BANDS_ON <- 1;
AIR_PROBE_FUNNEL_BOUND_ON <- 1;
AIR_PROBE_FUNNEL_COST_ON <- 1;
AIR_PROBE_FUNNEL_LIST_ON <- 1;
AIR_PROBE_FUNNEL_KEEP_TOP <- 0;
AIR_PROBE_FUNNEL_SLOPE_PENALTY <- 4;
AIR_PROBE_FUNNEL_COST_CAP <- 16;
AIR_PROBE_FUNNEL_LIST_CAP <- 24;
AIR_PROBE_FUNNEL_DEAD <- {};
AIR_PROBE_FUNNEL_LIST <- {};
AIR_PROBE_FUNNEL_LIST_MONTH <- -1;
AIR_PROBE_FUNNEL_RAW <- {};
AIR_PROBE_FUNNEL_PEN <- {};
AIR_PROBE_EXAMINED <- 0;
AIR_PROBE_CHEAP_LOOP <- OpexAirFootprintCheapOk;
AIR_PROBE_CHEAP_NATIVE <- OpexAirFootprintCheapOkNative;

function OpexAirProbeQuietChoice(town, airport, firstAnchor, firstScore, best, bestScore,
                                 valid, firstValidRing, bestRing, used)
{
  /* Equal quiet C96 logging for every method. Final result scored independently. */
}

function OpexAirProbeClear(owner)
{
  // Historical and coverage caches; no geometry epoch increment.
  OpexAirResetSiteCache(false);
  C121_AIR_ENDPOINT_CACHE = null;
  AIR_DEMAND_PAX_CARGO = -1;
  AIR_SITE_OPS_MARK = null;
  AIR_SITE_SEARCH_OPS = 0;
  AIR_SITE_SEARCH_CALLS = 0;
  // Removed funnel caches, now private to this module.
  AIR_PROBE_FUNNEL_DEAD.clear();
  AIR_PROBE_FUNNEL_LIST.clear();
  AIR_PROBE_FUNNEL_LIST_MONTH = -1;
  AIR_PROBE_FUNNEL_RAW.clear();
  AIR_PROBE_FUNNEL_PEN.clear();
  // PO01C's suspended stack is owned by this job. No generator is resumed here.
  owner._po01cJob = null;
  owner._po01cPending = false;
  owner._po01cLineState = null;
  AIR_PROBE_EXAMINED = 0;
}

function OpexAirProbeTileKind(tile)
{
  if (!AIMap.IsValidTile(tile)) return 0;
  if (AITile.IsWaterTile(tile)) return 1;
  if (AITile.IsCoastTile(tile)) return 2;
  if (AITile.IsRiverTile(tile)) return 3;
  if (AITile.IsHouseTile(tile)) return 4;
  if (AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(tile))) return 5;
  if (AITile.IsStationTile(tile)) return 6;
  if (AIRoad.IsRoadTile(tile)) return 7;
  if (AIRail.IsRailTile(tile)) return 8;
  if (AITile.HasTreeOnTile(tile)) return 9;
  return 10;
}

function OpexAirProbeFingerprint()
{
  local towns = AITownList();
  local population = 0;
  foreach (id, ignored in towns) population += AITown.GetPopulation(id);
  local industries = AIIndustryList();
  local sample = "";
  local size = AIMap.GetMapSize();
  // Exact, reproducible sample string avoids hash collisions in the tile sample.
  for (local i = 0; i < 64; i++) {
    local tile = (i * (size - 1)) / 63;
    sample += ":" + OpexAirProbeTileKind(tile);
    if (AIMap.IsValidTile(tile)) sample += "." + AITile.GetMinHeight(tile) + "." + AITile.GetMaxHeight(tile);
  }
  return towns.Count() + ":" + population + ":" + industries.Count() + sample;
}

function OpexAirProbeBuild(anchor, airport)
{
  if (anchor == null) return { buildable = 0, error = null, quote = null };
  local test = AITestMode();
  local accounting = AIAccounting();
  local ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
  // Read immediately: retain 263 (flat land), and every other native refusal.
  local error = ok ? 0 : AIError.GetLastError();
  return { buildable = ok ? 1 : 0, error = error,
           quote = ok ? accounting.GetCosts() : null };
}

function OpexAirProbeScalar(value)
{
  return value == null ? "null" : value.tostring();
}

function OpexAirProbeStrict(anchor, airport, town, probes, execLevels)
{
  local result = OpexAirProbeBuild(anchor, airport);
  return { ok = result.buildable == 1, limited = false, execLevels = execLevels };
}

AIR_PROBE_ORIGINAL_FUNNEL_TEST <- OpexAirProbeFunnelProbe;

function OpexAirProbeOracle(town, airport, probes)
{
  local tx = AIMap.GetTileX(town.tile);
  local ty = AIMap.GetTileY(town.tile);
  local mx = AIMap.GetMapSizeX();
  local my = AIMap.GetMapSizeY();
  local pax = OpexAirDemandPaxCargo();
  local best = null;
  local bestScore = -1;
  // Enumerate every playable anchor in the historical domain. No cheap terrain
  // filter, budget, first-ring stop, or speculative LevelTiles admission.
  for (local dx = -AIR_SITE_RADIUS; dx <= AIR_SITE_RADIUS; dx++) {
    for (local dy = -AIR_SITE_RADIUS; dy <= AIR_SITE_RADIUS; dy++) {
      if (dx > -4 && dx < 4 && dy > -4 && dy < 4) continue;
      local x = tx + dx;
      local y = ty + dy;
      if (x < 0 || y < 0 || x + airport.width > mx || y + airport.height > my) continue;
      local anchor = AIMap.GetTileIndex(x, y);
      if (!AIMap.IsValidTile(anchor)) continue;
      if (OpexAirDistanceToRect(town.tile, anchor, airport.width, airport.height) > AIR_SITE_RADIUS) continue;
      if (AIAirport.GetNearestTown(anchor, airport.type) != town.id) continue;
      AIR_PROBE_EXAMINED++;
      local result = OpexAirProbeBuild(anchor, airport);
      probes.tested++;
      if (result.buildable != 1) continue;
      local score = OpexAirC96SiteCatchmentScore(anchor, airport, pax);
      if (score > bestScore) { bestScore = score; best = { town = town, anchor = anchor }; }
    }
  }
  return best;
}

function OpexAirProbeMethod(owner, town, airport, method)
{
  OpexAirProbeClear(owner);
  ::OpexAirFootprintCheapOk <- AIR_PROBE_CHEAP_LOOP;
  ::OpexAirProbeFunnelProbe <- AIR_PROBE_ORIGINAL_FUNNEL_TEST;
  AIR_PROBE_FUNNEL_BANDS_ON = 1;
  AIR_PROBE_FUNNEL_BOUND_ON = 1;
  AIR_PROBE_FUNNEL_COST_ON = 1;
  AIR_PROBE_FUNNEL_LIST_ON = 1;
  AIR_PROBE_FUNNEL_SLOPE_PENALTY = 4;
  if (method == "hybrid") ::OpexAirFootprintCheapOk <- AIR_PROBE_CHEAP_NATIVE;
  if (method == "bands") AIR_PROBE_FUNNEL_COST_ON = 0;
  if (method == "border") AIR_PROBE_FUNNEL_SLOPE_PENALTY = 0;
  if (method == "strict" || method == "strict_full") {
    ::OpexAirProbeFunnelProbe <- OpexAirProbeStrict;
    AIR_PROBE_FUNNEL_COST_ON = 0;
    AIR_PROBE_FUNNEL_LIST_ON = 0;
  }
  if (method == "strict_full") { AIR_PROBE_FUNNEL_BANDS_ON = 0; AIR_PROBE_FUNNEL_BOUND_ON = 0; }
  // A fresh per-town search gets the full historical cap, explicitly independent
  // of planner order. This diagnostic does not qualify the shared planner budget.
  local probes = { left = AIR_MAX_SITE_PROBES, townsLeft = 1, tested = 0,
                   cheapSkip = 0, deadCatchment = 0, stationLimitedTowns = {} };
  local beginDate = AIDate.GetCurrentDate();
  local mark = OpexOpsMeasureBegin();
  local site = null;
  if (method == "spiral" || method == "hybrid") site = OpexAirFindSiteSpiral(town, airport, probes);
  else if (method == "initial") site = OpexAirProbeFindInitial(town, airport, probes);
  else if (method == "oracle") site = OpexAirProbeOracle(town, airport, probes);
  else site = OpexAirProbeFindFunnel(town, airport, probes);
  local ops = OpexOpsMeasureEnd(mark);
  local endDate = AIDate.GetCurrentDate();
  local anchor = site == null ? null : site.anchor;
  local result = OpexAirProbeBuild(anchor, airport);
  result.method <- method;
  result.anchor <- anchor;
  result.score <- anchor == null ? null : OpexAirC96SiteCatchmentScore(anchor, airport, OpexAirDemandPaxCargo());
  result.center <- anchor != null && OpexAirProbeFunnelCoversTown(anchor, town.tile, airport) ? 1 : 0;
  result.ops <- ops;
  result.tiles <- AIR_PROBE_EXAMINED;
  result.tested <- probes.tested;
  result.begin_date <- beginDate;
  result.end_date <- endDate;
  return result;
}

function OpexAirProbePass(owner, target, method)
{
  local beginDate = AIDate.GetCurrentDate();
  local before = OpexAirProbeFingerprint();
  local fingerprintEnd = AIDate.GetCurrentDate();
  local count = 0;
  local cases = [];
  local towns = AITownList();
  // All available buildable land-airport types, without the planner's plane,
  // portfolio or small-airport population cuts. Helipads/oil rigs are excluded.
  local types = [AIAirport.AT_SMALL, AIAirport.AT_LARGE, AIAirport.AT_METROPOLITAN,
                AIAirport.AT_INTERNATIONAL, AIAirport.AT_COMMUTER, AIAirport.AT_INTERCON];
  // Freeze eligibility before any search. Case order is the native town list
  // order for every game, then the same airport-type order.
  foreach (id, ignored in towns) {
    local town = { id = id, tile = AITown.GetLocation(id), pop = AITown.GetPopulation(id) };
    if (town.pop < V93_AIRPORT_MIN_POP || (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(town))) continue;
    foreach (type in types) {
      if (!AIAirport.IsValidAirportType(type)) continue;
      local airport = { type = type, width = AIAirport.GetAirportWidth(type), height = AIAirport.GetAirportHeight(type) };
      cases.append({ town = town, airport = airport });
    }
  }
  AILog.Info("AIR_PROBE_PASS v=2 edge=begin method=" + method + " target=" + target
      + " date=" + beginDate + " fingerprint_end_date=" + fingerprintEnd
      + " fingerprint=" + before + " cases=" + cases.len());
  foreach (item in cases) {
    local row = OpexAirProbeMethod(owner, item.town, item.airport, method);
    // Oracle fields are joined from the separate oracle game by the reader.
    AILog.Info("AIR_SITE_PROBE v=2 target=" + target + " town=" + item.town.id + " type=" + item.airport.type
        + " method=" + row.method + " tile=" + OpexAirProbeScalar(row.anchor) + " score=" + OpexAirProbeScalar(row.score)
        + " oracle=null oracle_tile=null"
        + " center=" + row.center + " buildable=" + row.buildable + " error=" + OpexAirProbeScalar(row.error)
        + " quote=" + OpexAirProbeScalar(row.quote) + " ops=" + row.ops + " tiles=" + row.tiles + " tested=" + row.tested
        + " begin=" + row.begin_date + " end=" + row.end_date);
    count++;
  }
  local after = OpexAirProbeFingerprint();
  local endDate = AIDate.GetCurrentDate();
  AILog.Info("AIR_PROBE_PASS v=2 edge=end method=" + method + " target=" + target + " date=" + endDate
      + " fingerprint=" + after + " stable=" + (before == after ? 1 : 0)
      + " truncated=0 rows=" + count + " vehicles=" + AIVehicleList().Count()
      + " stations=" + AIStationList(AIStation.STATION_ANY).Count()
      + " loan=" + AICompany.GetLoanAmount());
}

function OpexAirSiteProbeRun(owner)
{
  local test = AITestMode();
  OpexLoadSettings();
  // Settings may install the hybrid predicate; restore explicit methods below.
  ::OpexAirC96LogChoice <- OpexAirProbeQuietChoice;
  ::OpexAirFindSiteRing <- OpexAirProbeCountedRing;
  local companies = 0;
  for (local id = AICompany.COMPANY_FIRST; id <= AICompany.COMPANY_LAST; id++) {
    if (AICompany.ResolveCompanyID(id) != AICompany.COMPANY_INVALID) companies++;
  }
  if (companies != 1 || owner._loadedFromSave) {
    AILog.Error("AIR_PROBE_ABORT reason=fresh_solo_required");
    while (true) AIController.Sleep(74);
  }
  local methods = ["spiral", "hybrid", "initial", "bands", "border", "funnel", "strict", "strict_full", "oracle"];
  local method = methods[AIR_SITE_PROBE - 1];
  AILog.Info("AIR_PROBE_START v=2 method=" + method + " loan=" + AICompany.GetLoanAmount() + " ops_per_tick=" + OPS_PER_TICK);
  local dates = [AIDate.GetDate(1970, 1, 2), AIDate.GetDate(1972, 1, 1), AIDate.GetDate(1975, 1, 1)];
  foreach (target in dates) {
    while (AIDate.GetCurrentDate() < target) AIController.Sleep(1);
    OpexAirProbePass(owner, target, method);
  }
  AILog.Info("AIR_PROBE_DONE v=2 method=" + method);
  while (true) AIController.Sleep(74);
}

/* Original ring, with one raw candidate counter before native filters. */
function OpexAirProbeCountedRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY)
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

  AIR_PROBE_EXAMINED += tiles.Count();
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
