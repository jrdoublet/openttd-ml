FXVN_DONE <- false;
FXVN_DATE <- -1;
function FxTLStart(ai) { FXVN_DONE = false; FXVN_DATE = -1; }
function FxVNOps(tick, ops)
{
  local elapsed = AIController.GetTick() - tick;
  local left = AIController.GetOpsTillSuspend();
  return elapsed <= 0 ? ops-left : ops+(elapsed-1)*OPS_PER_TICK+(OPS_PER_TICK-left);
}
function FxTLWorld(ai)
{
  if (FXVN_DONE || ai._catalog == null || ai._catalog.paxCargo < 0) return;
  local now = AIDate.GetCurrentDate();
  if (FXVN_DATE >= 0 && now-FXVN_DATE < 30) return;
  FXVN_DATE = now;
  local airports = AITileList();
  airports.AddRectangle(AIMap.GetTileIndex(1, 1),
      AIMap.GetTileIndex(AIMap.GetMapSizeX()-2, AIMap.GetMapSizeY()-2));
  airports.Valuate(AIAirport.IsAirportTile);
  airports.KeepValue(1);
  local self = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local seen = {};
  if (ai._catalog.airport == null) return;
  local type = ai._catalog.airport.type;
  local airport = { type = type, width = AIAirport.GetAirportWidth(type),
      height = AIAirport.GetAirportHeight(type), price = AIAirport.GetPrice(type),
      maintenance = AIAirport.GetMonthlyMaintenanceCost(type) };
  local foreignCount = 0;
  local freeCount = 0;
  local buildCount = 0;
  local quoteCount = 0;
  foreach (foreign, unused in airports) {
    local owner = AITile.GetOwner(foreign);
    if (owner == self || owner == AICompany.COMPANY_INVALID) continue;
    local sid = AIStation.GetStationID(foreign);
    if (sid in seen) continue;
    seen.rawset(sid, true);
    foreignCount++;
    local townId = AITile.GetClosestTown(foreign);
    local town = { id = townId, tile = AITown.GetLocation(townId), pop = AITown.GetPopulation(townId) };
    local fx = AIMap.GetTileX(foreign);
    local fy = AIMap.GetTileY(foreign);
    for (local y = fy-12; y <= fy+12; y++) for (local x = fx-12; x <= fx+12; x++) {
      if (x < 1 || y < 1 || x+airport.width >= AIMap.GetMapSizeX()-1
          || y+airport.height >= AIMap.GetMapSizeY()-1) continue;
      local anchor = AIMap.GetTileIndex(x, y);
      if (!OpexAirFootprintCheapOk(anchor, airport) || !OpexAirFootprintIsFlat(anchor, airport)) continue;
      freeCount++;
      local test = AITestMode();
      local buildable = AIAirport.BuildAirport(anchor, type, AIStation.STATION_NEW);
      test = null;
      if (!buildable) continue;
      buildCount++;
      local site = { anchor = anchor, town = town, stationId = -1 };
      local plan = { airport = airport, siteA = site, reuseA = false, arm = "newpair" };
      // Full production endpoint path, including predicted joined stops.
      C121_AIR_ENDPOINT_CACHE.clear();
      local endpoint = OpexAirB9DemandShadowEndpointCargo(ai._catalog, plan, site, false, ai._catalog.paxCargo);
      quoteCount++;
      if (endpoint.unionMonthly <= 0 || endpoint.competition.rivalWeight <= 0) continue;
      local producers = AITileList();
      producers.AddList(endpoint.coverageTiles);
      producers.Valuate(AITile.GetCargoProduction, ai._catalog.paxCargo, 1, 1, 0);
      producers.KeepAboveValue(0);
      local ownedTown = AITileList();
      ownedTown.AddList(producers);
      ownedTown.Valuate(AITile.GetClosestTown);
      ownedTown.KeepValue(townId);
      producers.KeepList(ownedTown);
      local saved = C121_AIR_VISIBLE_COMPETITION;
      local baseline = null;
      local candidate = null;
      local offOps = 0;
      local coldOps = 0;
      local warmOps = 0;
      try {
        C121_AIR_VISIBLE_COMPETITION = false;
        local tick = AIController.GetTick(); local ops = AIController.GetOpsTillSuspend();
        baseline = OpexC121StationCompetitionBuckets(town, ai._catalog.paxCargo, producers, -1);
        offOps = FxVNOps(tick, ops);
        C121_AIR_VISIBLE_COMPETITION = true;
        C121_VISIBLE_AIRPORT_CACHE.clear();
        tick = AIController.GetTick(); ops = AIController.GetOpsTillSuspend();
        candidate = OpexC121StationCompetitionBuckets(town, ai._catalog.paxCargo, producers, -1);
        coldOps = FxVNOps(tick, ops);
        tick = AIController.GetTick(); ops = AIController.GetOpsTillSuspend();
        OpexC121StationCompetitionBuckets(town, ai._catalog.paxCargo, producers, -1);
        warmOps = FxVNOps(tick, ops);
      } catch (error) { C121_AIR_VISIBLE_COMPETITION = saved; throw error; }
      C121_AIR_VISIBLE_COMPETITION = saved;
      local before = OpexC121StationAllocatedMonthly(endpoint.unionMonthly, 127, baseline);
      local after = OpexC121StationAllocatedMonthly(endpoint.unionMonthly, 127, candidate);
      if (!(before > after && after > 0 && candidate.rivalWeight > 0
          && !AIAirport.IsAirportTile(anchor))) throw "C121_NEWSITE_ASSERT capture";
      FXVN_DONE = true;
      AILog.Info("C121_NEWSITE_WORLD pass=1 arm=newpair station_id=-1 reuse=0 buildable=1"
          + " anchor=" + anchor + " rival_station=" + sid + " rival_owner=" + owner
          + " rival_weight=" + candidate.rivalWeight + " total_weight=" + candidate.totalWeight
          + " raw=" + endpoint.unionMonthly + " before=" + before + " after=" + after
          + " bucket_ops_off=" + offOps + " bucket_ops_cold=" + coldOps + " bucket_ops_warm=" + warmOps);
      return;
    }
  }
  AILog.Info("C121_NEWSITE_SEARCH type=" + type + " foreign=" + foreignCount
      + " free=" + freeCount + " buildable=" + buildCount + " quotes=" + quoteCount);
}
