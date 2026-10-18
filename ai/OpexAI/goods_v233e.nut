/* V233e, policy 3 ONLY. Modes 0/1/2 retain their observer and generator.
 * Production is global, not evidence of our marginal contribution. A live input
 * rail line and a positive last closed month replace the three-month gate.
 * OpexMakeCandidate remains the authority for train sizing and profitability. */
function OpexV233eMonth()
{
  local date = AIDate.GetCurrentDate();
  return AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
}

function OpexV233eGoodsStep(ai)
{
  local month = OpexV233eMonth();
  local work = ai._v233GoodsWork;
  local gen = ai._v233Generation;
  // A not-yet-started generator is not a completed one: even an index finishing
  // on the last day of a month must get its first generation turn before reset.
  local generated = work != null && gen != null && gen.current == null && gen.cursor >= work.keys.len();
  // Finish a bounded sweep AND its destinations across calendar boundaries.
  // New fleet revisions do not restart the cursor. Each support is checked live.
  if (work == null || (work.phase == "done" && work.month != month && generated)) {
    work = { month = month, revision = ai._v233WorldRevision(), phase = "index",
      lineCursor = 0, lineLimit = ai._lines.len(), rows = {}, keys = [],
      cursor = 0, supports = {}, outputs = {} };
    ai._v233GoodsWork = work;
    ai._v233Generation = null;
    ai._v233NeedsPublish = true;
  }
  if (work.phase != "index") return;
  if (ai._v233GoodsObservations == null) ai._v233GoodsObservations = {};
  for (local n = 0; n < 8 && work.lineCursor < work.lineLimit
       && work.lineCursor < ai._lines.len(); n++) {
    local line = ai._lines[work.lineCursor++];
    local support = OpexV233Support(line);
    if (support == null) continue;
    local produced = AIIndustryType.GetProducedCargo(AIIndustry.GetIndustryType(support.factoryId));
    for (local cargo = produced.Begin(); !produced.IsEnd(); cargo = produced.Next()) {
      if (!(cargo in ai._catalog.wagonByCargo)) continue;
      local key = OpexV233ObservationKey(support.factoryId, cargo, support.stationId);
      if (key in work.rows) continue;
      local quantity = AIIndustry.GetLastMonthProduction(support.factoryId, cargo);
      if (quantity < 0) continue; // unknown is never zero
      local row = null;
      if (key in ai._v233GoodsObservations) {
        local saved = ai._v233GoodsObservations[key];
        if (saved.factoryTile == support.factoryTile && saved.stationTile == support.stationTile
            && saved.lastMonth <= month) row = saved;
      }
      if (row == null) row = { factoryId = support.factoryId, factoryTile = support.factoryTile,
        cargo = cargo, stationId = support.stationId, stationTile = support.stationTile,
        lastMonth = -1, q0 = 0, q1 = 0, q2 = 0, count = 0 };
      OpexV233Sample(row, month, quantity);
      // Persist immediately; a later interruption cannot erase an observed month.
      ai._v233GoodsObservations[key] <- row;
      work.rows[key] <- row;
      work.supports[key] <- line;
      work.keys.append(key);
      if (DECISION_LOG) OpexDecide("V233_OBS", "factory=" + row.factoryId + " cargo=" + cargo
        + " station=" + row.stationId + " month=" + month + " global_output=" + quantity
        + " support_line=" + line.lineId + " count=" + row.count
        + " q0=" + row.q0 + " q1=" + row.q1 + " q2=" + row.q2
        + " policy=3 eligible_quantity=" + quantity);
      if (DECISION_LOG && quantity > 0) OpexDecide("V233_ELIGIBLE", "factory=" + row.factoryId
        + " cargo=" + cargo + " station=" + row.stationId + " month=" + month + " quantity=" + quantity);
    }
  }
  if (work.lineCursor >= work.lineLimit || work.lineCursor >= ai._lines.len()) {
    work.phase = "done";
    ai._v233GoodsObservations = work.rows;
  }
}

function OpexV233eSupport(ai, context)
{
  foreach (line in ai._lines) {
    if (line.lineId != context.joinLineId) continue;
    local support = OpexV233Support(line);
    if (support == null || support.factoryId != context.v233FactoryId
        || support.factoryTile != context.src || support.stationId != context.joinStationId
        || support.stationTile != context.v233StationTile) return null;
    local p = line.platformB;
    local old = context.joinPlatform;
    if (p.anchor != old.anchor || p.direction != old.direction || p.length != old.length) return null;
    return support;
  }
  return null;
}

function OpexV233eOutputAllocated(ai, source, cargo)
{
  foreach (line in ai._lines)
    if (("originA" in line) && ("cargo" in line)
        && line.originA == source && line.cargo == cargo) return true;
  return false;
}

function OpexV233eCandidateLive(ai, candidate)
{
  if (!("v233EngineRevision" in candidate)
      || candidate.v233EngineRevision != ai._c76GetLayerRevision("engines.rail")) return false;
  if (OpexV233eSupport(ai, candidate) == null
      || !OpexV233JoinContextValid(candidate, candidate.cargo, candidate.src, ai._catalog.railCoverage)) return false;
  // Conservative offer: a rise does not reprice it; a fall below its priced flow does.
  if (AIIndustry.GetLastMonthProduction(candidate.v233FactoryId, candidate.cargo) < candidate.monthly) return false;
  if (OpexV233eOutputAllocated(ai, candidate.src, candidate.cargo)) return false;
  if (candidate.dstTown >= 0) {
    if (!AITown.IsValidTown(candidate.dstTown) || AITown.GetLocation(candidate.dstTown) != candidate.dst) return false;
  } else {
    if (!AIIndustry.IsValidIndustry(candidate.v233DstIndustry)
        || AIIndustry.GetLocation(candidate.v233DstIndustry) != candidate.dst
        || !AIIndustryType.GetAcceptedCargo(AIIndustry.GetIndustryType(candidate.v233DstIndustry)).HasItem(candidate.cargo)) return false;
  }
  if (OpexAbandonedPairKey(candidate) in ai._abandonedPairs
      || OpexV233SourceSiteKey(candidate, candidate.cargo) in ai._abandonedPairs) return false;
  return true;
}

/* Require the named industry, rather than aggregate acceptance from a neighbour.
 * For a joined station its existing facilities may provide the catchment. */
function OpexV233eDestinationCargoOk(p, candidate, coverage)
{
  if (candidate.dstTown >= 0) return true; // ordinary full-rectangle/station guard below
  local industry = candidate.v233DstIndustry;
  if (!AIIndustry.IsValidIndustry(industry)
      || AIIndustry.GetLocation(industry) != candidate.dst
      || !AIIndustryType.GetAcceptedCargo(AIIndustry.GetIndustryType(industry)).HasItem(candidate.cargo)) return false;
  local catchment = AITileList_IndustryAccepting(industry, coverage);
  for (local i = 0; i < p.length; i++)
    if (catchment.HasItem(p.anchor + p.step * i)) return true;
  if ("stationId" in p) {
    local tiles = AITileList_StationType(p.stationId, AIStation.STATION_ANY);
    for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next())
      if (catchment.HasItem(tile)) return true;
  }
  return false;
}

function OpexV233eInitSiteStats(stats)
{
  stats.tiles <- 0; stats.tried <- 0;
  stats.last <- "not_searched"; stats.lastError <- -1; stats.bestAcceptance <- -1;
}

function OpexV233eStationPlans(center, length, cargo, coverage, stats, stationId = AIStation.STATION_NEW,
                          sourceIndustry = -1, destination = null)
{
  local plans = [];
  local joining = stationId != AIStation.STATION_NEW;
  local radius = STATION_SEARCH_RADIUS;
  // Mode 3 explores peripheral acceptance without changing the ordinary rail finder.
  if (V233_GOODS_POLICY == 3) radius += coverage + length - 1;
  if (joining) radius = AIGameSettings.GetValue("station.station_spread") - 1;
  local axes = [[AIRail.RAILTRACK_NE_SW, AIMap.GetTileIndex(1, 0)],
                [AIRail.RAILTRACK_NW_SE, AIMap.GetTileIndex(0, 1)]];
  for (local r = 0; r <= radius && plans.len() < MAX_STATION_PLANS; r++) {
    for (local dx = -r; dx <= r && plans.len() < MAX_STATION_PLANS; dx++) {
      for (local dy = -r; dy <= r && plans.len() < MAX_STATION_PLANS; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local x = AIMap.GetTileX(center) + dx;
        local y = AIMap.GetTileY(center) + dy;
        if (x < 0 || y < 0 || x >= AIMap.GetMapSizeX() || y >= AIMap.GetMapSizeY()) continue;
        local endpoint = AIMap.GetTileIndex(x, y);
        stats.tiles++;
        foreach (axis in axes) {
          for (local sign = -1; sign <= 1; sign += 2) {
            stats.tried++;
            stats.last = "bounds";
            local anchor = sign > 0 ? endpoint : endpoint - axis[1] * (length - 1);
            local stationExit = sign > 0 ? anchor + axis[1] * (length - 1) : anchor;
            local lead = sign > 0 ? stationExit + axis[1] : stationExit - axis[1];
            if (!AIMap.IsValidTile(anchor) || !AIMap.IsValidTile(lead)
                || !AIMap.IsValidTile(anchor + axis[1] * (length - 1))) continue;
            /* Linear tile arithmetic must not wrap into the next map row. */
            if (AIMap.DistanceManhattan(anchor, lead) != (sign > 0 ? length : 1)
                || AIMap.DistanceManhattan(anchor, anchor + axis[1] * (length - 1)) != length - 1) continue;
            local usable = true;
            for (local i = -1; i < length && usable; i++) {
              local tile = i < 0 ? lead : anchor + axis[1] * i;
              if (!AITile.IsBuildable(tile)) { stats.last = "occupied"; usable = false; }
              else if (AITile.GetSlope(tile) != AITile.SLOPE_FLAT) { stats.last = "slope"; usable = false; }
            }
            if (!usable) continue;
            stats.nClear++;
            local p = { anchor = anchor, station_exit = stationExit, lead = lead,
                        direction = axis[0], step = axis[1], length = length };
            if (V233_GOODS_POLICY == 3 && joining) p.stationId <- stationId;
            if (sourceIndustry != -1
                && !OpexV233FactoryCovered(p, sourceIndustry, cargo, coverage)) {
              stats.last = "source_coverage";
              continue;
            }
            if (destination != null && !OpexV233eDestinationCargoOk(p, destination, coverage)) {
              stats.last = "destination_coverage";
              continue;
            }
            local acceptance = OpexV233TownAcceptance(p, cargo, coverage);
            if (acceptance > stats.bestAcceptance) stats.bestAcceptance = acceptance;
            if (!joining && acceptance < 8) { stats.last = "acceptance"; continue; }
            stats.nCargo++;
            local unionOnly = false;
            if (DECISION_LOG && !joining) unionOnly = OpexRailPlatformCargoValue(anchor, axis[1], length,
              cargo, coverage, false) < 8;
            local ok = false;
            {
              local accounting = AIAccounting(); // discard simulated costs
              local probe = AITestMode();
              ok = AIRail.BuildRailStation(anchor, axis[0], 1, length, stationId);
              if (!ok) stats.lastError = AIError.GetLastError();
            }
            if (!ok) { stats.last = "command"; continue; }
            stats.nCmd++;
            if (DECISION_LOG && unionOnly) OpexDecide("V233_SITE", "state=union_recovered center=" + center
              + " anchor=" + anchor + " length=" + length + " direction=" + axis[0]
              + " acceptance=" + acceptance);
            p.cargoValue <- acceptance;
            if (joining) {
              p.stationId <- stationId;
              p.v233StationTile <- center;
            }
            plans.append(p);
            if (plans.len() >= MAX_STATION_PLANS) break;
          }
          if (plans.len() >= MAX_STATION_PLANS) break;
        }
      }
    }
  }
  return plans;
}

function OpexV233ePlatformPlans(catalog, candidate, statsA, statsB)
{
  OpexV233eInitSiteStats(statsA);
  OpexV233eInitSiteStats(statsB);
  local wanted = candidate.platformLength;
  if (wanted > candidate.joinPlatform.length) wanted = candidate.joinPlatform.length;
  if (wanted > catalog.platformLength) wanted = catalog.platformLength;
  local sources = {};
  local sawA = false;
  foreach (joinB in [true, false]) {
    for (local length = wanted; length >= OpexRailMinimumPlatformLength(); length--) {
      if (!(length in sources)) {
        // Two axes, both exits, whole legal station spread. No old track reuse.
        sources[length] <- OpexV233eStationPlans(candidate.v233StationTile, length, candidate.cargo,
          catalog.railCoverage, statsA, candidate.joinStationId, candidate.v233FactoryId);
      }
      local plansA = sources[length];
      if (plansA.len() == 0) continue;
      sawA = true;
      local plansB = [];
      if (joinB) {
        local stations = AIStationList(AIStation.STATION_ANY);
        for (local station = stations.Begin(); !stations.IsEnd(); station = stations.Next()) {
          if (station == candidate.joinStationId) continue;
          if (candidate.dstTown >= 0 && AIStation.GetNearestTown(station) != candidate.dstTown) continue;
          local tile = AIStation.GetLocation(station);
          if (!OpexV233AcceptingStation(station, tile, candidate.cargo)) continue;
          // Industry joins must reach that industry's catchment, not a distant outlet.
          local identity = { anchor = tile, step = 0, length = 1, stationId = station };
          if (!OpexV233eDestinationCargoOk(identity, candidate, catalog.railCoverage)) continue;
          plansB = OpexV233eStationPlans(tile, length, candidate.cargo, catalog.railCoverage,
            statsB, station, -1, candidate);
          if (plansB.len() > 0) break;
        }
      } else {
        plansB = OpexV233eStationPlans(candidate.dst, length, candidate.cargo, catalog.railCoverage,
          statsB, AIStation.STATION_NEW, -1, candidate);
      }
      if (plansB.len() == 0) continue;
      candidate.v233JoinB <- joinB ? plansB[0].stationId : -1;
      if (DECISION_LOG) OpexDecide("V233_SITE", "factory=" + candidate.v233FactoryId
        + " town=" + candidate.dstTown + " industry=" + candidate.v233DstIndustry
        + (joinB ? " joinB=" + candidate.v233JoinB : " newB"));
      return { plansA = plansA, plansB = plansB, length = length, slopeRelaxed = 0,
               reason = "OK", statsA = statsA, statsB = statsB };
    }
    if (!sawA) break;
  }
  return { plansA = null, plansB = null, length = wanted, slopeRelaxed = 0,
    reason = OpexRailSiteReason(sawA, false), sourceFailed = !sawA, statsA = statsA, statsB = statsB };
}

function OpexV233eGraftStep(ai)
{
  local work = ai._v233GoodsWork;
  if (work == null || work.phase != "done" || ai._projects == null) return;
  if (ai._v233Offers == null) ai._v233Offers = {};
  if (ai._v233Plans == null) ai._v233Plans = {};
  if (ai._v233Generation == null) ai._v233Generation = { cursor = 0, current = null, seen = {} };
  local gen = ai._v233Generation;
  if (gen.current == null) {
    if (gen.cursor >= work.keys.len()) return;
    local key = work.keys[gen.cursor++];
    local row = work.rows[key];
    local outputKey = row.factoryTile + "|" + row.cargo;
    if (outputKey in gen.seen) return;
    gen.seen[outputKey] <- true;
    if (OpexV233eOutputAllocated(ai, row.factoryTile, row.cargo)) return;
    if (outputKey in ai._v233Offers) {
      if (ai._v233CandidateLive(ai._v233Offers[outputKey])) return;
      ai._v233ForgetPlan(ai._v233Offers[outputKey], "observation_changed");
      delete ai._v233Offers[outputKey];
    }
    local line = work.supports[key];
    local support = OpexV233Support(line);
    if (support == null) return;
    local p = line.platformB;
    local context = { strictJoin = true, joinEnd = "A", joinStationId = row.stationId, src = row.factoryTile,
      joinLineId = line.lineId, v233FactoryId = row.factoryId, v233StationTile = row.stationTile,
      v233Revision = work.revision, v233EngineRevision = ai._c76GetLayerRevision("engines.rail"),
      joinPlatform = { anchor = p.anchor, direction = p.direction, step = p.step,
        length = p.length, station_exit = p.station_exit, lead = p.lead } };
    // TownEffect is a hint only. The catalog also detects NewGRF urban cargos
    // without a town effect. Full footprint acceptance is always checked later.
    local towns = (AICargo.GetTownEffect(row.cargo) != AICargo.TE_NONE
      || row.cargo in ai._catalog.townAcceptors) ? ai._catalog.towns : [];
    local industries = row.cargo in ai._catalog.acceptors ? ai._catalog.acceptors[row.cargo] : [];
    gen.current = { row = row, outputKey = outputKey, context = context, towns = towns,
      industries = industries, industryRows = ai._catalog.industries,
      cursor = 0, nearest = [], evaluate = 0, preferred = null };
    return;
  }
  local state = gen.current;
  local total = state.towns.len() + state.industries.len();
  if (state.cursor < total) {
    local bounds = OpexCatalogBounds(ai._catalog);
    // Existing eight-item slice, but no arbitrary three-destination truncation.
    for (local n = 0; n < 8 && state.cursor < total; n++) {
      local index = state.cursor++;
      local town = index < state.towns.len();
      local sink = town ? state.towns[index] : state.industryRows[state.industries[index - state.towns.len()]];
      if (!town && sink.id == state.row.factoryId) continue;
      local distance = AIMap.DistanceManhattan(state.row.factoryTile, sink.tile);
      if (distance > bounds.railMax) continue;
      local entry = { id = sink.id, tile = sink.tile, town = town, distance = distance,
        transformer = !town && ("isTransformer" in sink) && sink.isTransformer };
      local pos = 0;
      // Urban destinations first; industrial fallback if no urban site/economics.
      while (pos < state.nearest.len() && ((state.nearest[pos].town && !town)
          || (state.nearest[pos].town == town && state.nearest[pos].distance <= distance))) pos++;
      state.nearest.insert(pos, entry);
    }
    return;
  }
  if (state.evaluate < state.nearest.len()) {
    local sink = state.nearest[state.evaluate++];
    if (!sink.town && state.preferred != null && state.preferred.dstTown >= 0) {
      state.evaluate = state.nearest.len();
      return;
    }
    local pair = "freight|" + state.row.cargo + "|" + state.row.factoryId
      + "|" + (sink.town ? "t" + sink.id : sink.id.tostring());
    if (pair in ai._abandonedPairs) return;
    if (OpexV233SourceSiteKey(state.context, state.row.cargo) in ai._abandonedPairs) { gen.current = null; return; }
    if (OpexV233eSupport(ai, state.context) == null
        || !OpexV233JoinContextValid(state.context, state.row.cargo, state.row.factoryTile, ai._catalog.railCoverage)) {
      gen.current = null;
      return;
    }
    local monthly = AIIndustry.GetLastMonthProduction(state.row.factoryId, state.row.cargo);
    if (monthly <= 0) { gen.current = null; return; }
    // Economic admission sizes a real train, checks profit, ROI and distance.
    local candidate = OpexMakeCandidate(ai._catalog, "freight", state.row.cargo,
      state.row.factoryTile, sink.tile, monthly, true, OpexRailCandidateStats(), sink.transformer,
      null, null, null, state.context);
    if (candidate == null) return;
    foreach (key, value in state.context) candidate[key] <- value;
    candidate.v233Graft <- true;
    candidate.dstTown <- sink.town ? sink.id : -1;
    candidate.v233DstIndustry <- sink.town ? -1 : sink.id;
    if (!ai._v233CandidateLive(candidate)) return;
    local sites = OpexRailPlatformPlans(ai._catalog, candidate);
    if (sites.reason != "OK") {
      if (DECISION_LOG) OpexDecide("V233_GRAFT", "state=site_rejected factory=" + candidate.v233FactoryId
        + " cargo=" + candidate.cargo + " town=" + candidate.dstTown + " industry=" + candidate.v233DstIndustry
        + " reason=" + sites.reason + " clearA=" + sites.statsA.nClear + " commandA=" + sites.statsA.nCmd
        + " lastA=" + sites.statsA.last + " errorA=" + sites.statsA.lastError
        + " clearB=" + sites.statsB.nClear + " cargoB=" + sites.statsB.nCargo
        + " commandB=" + sites.statsB.nCmd + " tilesB=" + sites.statsB.tiles
        + " triedB=" + sites.statsB.tried + " lastB=" + sites.statsB.last
        + " errorB=" + sites.statsB.lastError + " best_acceptanceB=" + sites.statsB.bestAcceptance);
      if (("sourceFailed" in sites) && sites.sourceFailed) {
        ai._markPairAbandoned(OpexV233SourceSiteKey(candidate, candidate.cargo));
        gen.current = null;
      } else ai._markPairAbandoned(OpexAbandonedPairKey(candidate));
      return;
    }
    if (ai._tooClose(candidate).hard >= 0 || ai._tooClose(candidate).blocking >= 0) return;
    // One output, one ordinary offer. Continue to another town on a rejection,
    // but publish the first feasible destination rather than exhaust all towns
    // before giving the other supported industries their scheduler turn.
    state.preferred = candidate;
    state.evaluate = state.nearest.len();
    return;
  }
  if (state.preferred != null && ai._v233CandidateLive(state.preferred)) {
    ai._v233Offers[state.outputKey] <- state.preferred;
    ai._v233NeedsPublish = true;
    if (DECISION_LOG) OpexDecide("V233_GRAFT", "state=candidate factory=" + state.row.factoryId
      + " cargo=" + state.row.cargo + " station=" + state.row.stationId + " town=" + state.preferred.dstTown
      + " industry=" + state.preferred.v233DstIndustry + " quantity=" + state.preferred.monthly
      + " profit=" + state.preferred.profitAnnual);
  }
  gen.current = null;
}
