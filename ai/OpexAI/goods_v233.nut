/* V233: bounded observation of GLOBAL factory output, not proof of our contribution.
 * No projects are inserted by this observer. No API calls from the save codec. */
function OpexV233ObservationKey(factory, cargo, station)
{
  return factory + "|" + cargo + "|" + station;
}

function OpexV233Sample(row, month, quantity)
{
  if (row.lastMonth == month) return false;
  if (row.lastMonth != month - 1) {
    row.count = 0;
    row.q0 = 0; row.q1 = 0; row.q2 = 0;
  }
  row.q2 = row.q1; row.q1 = row.q0; row.q0 = quantity;
  row.count = row.count < 3 ? row.count + 1 : 3;
  row.lastMonth = month;
  return true;
}

function OpexV233Quantity(row, month)
{
  if (row == null || row.count != 3 || row.lastMonth != month) return 0;
  local q = row.q0 < row.q1 ? row.q0 : row.q1;
  if (row.q2 < q) q = row.q2;
  return q >= V233_GOODS_MIN_MONTHLY ? q : 0;
}

function OpexV233Support(line)
{
  if (line == null || !("mode" in line) || line.mode != "rail"
      || !("kind" in line) || line.kind != "freight"
      || (("scrapping" in line) && line.scrapping)
      || !("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0
      || !AIVehicle.IsValidVehicle(line.vehicles[0])
      || !("dstIndustry" in line) || !AIIndustry.IsValidIndustry(line.dstIndustry)
      || !("platformB" in line) || line.platformB == null) return null;
  local station = OpexLineStationId(line, "B");
  if (station < 0 || !AIStation.IsValidStation(station)
      || !AICompany.IsMine(AITile.GetOwner(line.stationB))) return null;
  local accepting = AICargoList_StationAccepting(station);
  if (!accepting.HasItem(line.cargo)) return null;
  local accepted = AIIndustryType.GetAcceptedCargo(AIIndustry.GetIndustryType(line.dstIndustry));
  if (!accepted.HasItem(line.cargo)) return null;
  local factoryCatchment = AITileList_IndustryAccepting(line.dstIndustry,
    AIStation.GetCoverageRadius(AIStation.STATION_TRAIN));
  local reachesFactory = false;
  for (local i = 0; i < line.platformB.length; i++)
    if (factoryCatchment.HasItem(line.platformB.anchor + line.platformB.step * i)) reachesFactory = true;
  if (!reachesFactory) return null;
  return { factoryId = line.dstIndustry, factoryTile = AIIndustry.GetLocation(line.dstIndustry),
           stationId = station, stationTile = line.stationB, line = line };
}

function OpexV233SaveObservations(rows)
{
  local out = [];
  if (rows != null) foreach (key, row in rows) {
    if (row.count < 1 || row.lastMonth < 0) continue;
    out.append([row.factoryId, row.factoryTile, row.cargo, row.stationId, row.stationTile,
                row.lastMonth, row.q0, row.q1, row.q2, row.count]);
  }
  return { version = 1, rows = out };
}

function OpexV233LoadObservations(data)
{
  local out = {};
  if (data == null || typeof data != "table" || !("version" in data) || data.version != 1
      || !("rows" in data) || typeof data.rows != "array") return out;
  foreach (tuple in data.rows) {
    if (typeof tuple != "array" || tuple.len() != 10) continue;
    local valid = true;
    foreach (value in tuple) if (typeof value != "integer" || value < 0) valid = false;
    if (!valid || tuple[9] < 1 || tuple[9] > 3) continue;
    local row = { factoryId = tuple[0], factoryTile = tuple[1], cargo = tuple[2],
                  stationId = tuple[3], stationTile = tuple[4], lastMonth = tuple[5],
                  q0 = tuple[6], q1 = tuple[7], q2 = tuple[8], count = tuple[9] };
    out[OpexV233ObservationKey(row.factoryId, row.cargo, row.stationId)] <- row;
  }
  return out;
}

function OpexAI::_v233WorldRevision()
{
  return this._c76GetLayerRevision("lines") + "|" + this._c76GetLayerRevision("industries")
    + "|" + this._c76GetLayerRevision("towns") + "|" + this._c76GetLayerRevision("engines.rail");
}

function OpexAI::_v233GoodsStep()
{
  local date = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  local work = this._v233GoodsWork;
  local revision = this._v233WorldRevision();
  if (work == null || work.month != month || work.revision != revision) {
    if (DECISION_LOG && work != null && work.phase != "done")
      OpexDecide("V233_DROP", "reason=month_coverage month=" + work.month);
    work = { month = month, revision = revision, phase = "index", lineCursor = 0, rows = {},
             keys = [], cursor = 0, supports = {}, outputs = {} };
    this._v233GoodsWork = work;
    this._v233Generation = null;
    this._v233NeedsPublish = true;
  }
  if (work.phase == "index") {
    /* Rebuild monthly even if fleet is unchanged. Eight lines maximum per invocation.
     * Cargo enumeration is bounded by the engine's cargo limit (64). */
    for (local n = 0; n < 8 && work.lineCursor < this._lines.len(); n++) {
      local line = this._lines[work.lineCursor++];
      /* Any existing mode drawing this output blocks another allocation, including
       * ordinary goods lines predating V233. A scrapping line still owns its trains. */
      if (("cargo" in line) && ("originA" in line))
        work.outputs[line.originA + "|" + line.cargo] <- true;
      local support = OpexV233Support(line);
      if (support == null) continue;
      local produced = AIIndustryType.GetProducedCargo(AIIndustry.GetIndustryType(support.factoryId));
      for (local cargo = produced.Begin(); !produced.IsEnd(); cargo = produced.Next()) {
        if (AICargo.GetTownEffect(cargo) != AICargo.TE_GOODS) continue;
        if (!OpexV233FactoryCovered(support.line.platformB, support.factoryId, cargo, this._catalog.railCoverage)) continue;
        local key = OpexV233ObservationKey(support.factoryId, cargo, support.stationId);
        if (key in work.rows) continue;
        local row = null;
        if (this._v233GoodsObservations != null && key in this._v233GoodsObservations) {
          local saved = this._v233GoodsObservations[key];
          if (saved.factoryTile == support.factoryTile && saved.stationTile == support.stationTile
              && saved.lastMonth <= month) row = saved;
        }
        if (row == null) row = { factoryId = support.factoryId, factoryTile = support.factoryTile,
          cargo = cargo, stationId = support.stationId, stationTile = support.stationTile,
          lastMonth = -1, q0 = 0, q1 = 0, q2 = 0, count = 0 };
        work.rows[key] <- row;
        work.supports[key] <- support.line;
        work.keys.append(key);
      }
    }
    if (work.lineCursor < this._lines.len()) return;
    this._v233GoodsObservations = work.rows;
    work.phase = "observe";
    return;
  }
  if (work.phase != "observe") return;
  if (work.cursor >= work.keys.len()) { work.phase = "done"; return; }
  local key = work.keys[work.cursor++];
  local row = work.rows[key];
  local support = OpexV233Support(work.supports[key]);
  if (support == null || support.factoryTile != row.factoryTile
      || support.stationId != row.stationId || support.stationTile != row.stationTile) {
    delete work.rows[key];
    return;
  }
  local quantity = AIIndustry.GetLastMonthProduction(row.factoryId, row.cargo);
  if (quantity < 0) { delete work.rows[key]; return; }
  if (!OpexV233Sample(row, month, quantity)) return;
  if (DECISION_LOG) {
    OpexDecide("V233_OBS", "factory=" + row.factoryId + " cargo=" + row.cargo
      + " station=" + row.stationId + " month=" + month + " global_output=" + quantity
      + " support_line=" + work.supports[key].lineId + " count=" + row.count);
    if (OpexV233Quantity(row, month) > 0)
      OpexDecide("V233_ELIGIBLE", "factory=" + row.factoryId + " cargo=" + row.cargo
        + " station=" + row.stationId + " month=" + month + " quantity=" + OpexV233Quantity(row, month));
  }
}

function OpexV233IsGraft(candidate)
{
  return candidate != null && ("v233Graft" in candidate) && candidate.v233Graft;
}

function OpexV233PlanKey(candidate)
{
  return OpexProjectPairKey(candidate.kind, candidate.cargo, candidate.src, candidate.dst)
    + "|" + candidate.joinStationId;
}

function OpexV233JoinContextValid(context, cargo, source, coverage)
{
  if (!("strictJoin" in context) || !context.strictJoin || context.joinEnd != "A"
      || !AIIndustry.IsValidIndustry(context.v233FactoryId)
      || AIIndustry.GetLocation(context.v233FactoryId) != source
      || !AIStation.IsValidStation(context.joinStationId)
      || !AIMap.IsValidTile(context.v233StationTile)
      || AIStation.GetStationID(context.v233StationTile) != context.joinStationId
      || !AICompany.IsMine(AITile.GetOwner(context.v233StationTile))) return false;
  local produced = AIIndustryType.GetProducedCargo(AIIndustry.GetIndustryType(context.v233FactoryId));
  if (!produced.HasItem(cargo) || AICargo.GetTownEffect(cargo) != AICargo.TE_GOODS) return false;
  local p = context.joinPlatform;
  if (p == null) return false;
  for (local i = 0; i < p.length; i++) {
    local tile = p.anchor + p.step * i;
    if (!AIRail.IsRailStationTile(tile) || AIStation.GetStationID(tile) != context.joinStationId
        || !AICompany.IsMine(AITile.GetOwner(tile))) return false;
  }
  return OpexV233FactoryCovered(p, context.v233FactoryId, cargo, coverage);
}

function OpexV233FactoryCovered(platform, factory, cargo, coverage)
{
  /* Unlike a general production sum, this native list identifies THIS factory. */
  local producing = AITileList_IndustryProducing(factory, coverage);
  for (local i = 0; i < platform.length; i++)
    if (producing.HasItem(platform.anchor + platform.step * i))
      return OpexV207PlatformUnionValue(platform, cargo, coverage) > 0;
  return false;
}

function OpexAI::_v233CandidateLive(candidate)
{
  if (!V233_GOODS_GRAFT || !OpexV233IsGraft(candidate)) return false;
  local work = this._v233GoodsWork;
  local date = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  if (work == null || work.month != month || work.phase != "done"
      || work.revision != this._v233WorldRevision() || candidate.v233Revision != work.revision) return false;
  local key = OpexV233ObservationKey(candidate.v233FactoryId, candidate.cargo, candidate.joinStationId);
  if (!(key in work.rows) || !(key in work.supports)) return false;
  local row = work.rows[key];
  if (OpexV233Quantity(row, month) != candidate.monthly) return false;
  if ((candidate.src + "|" + candidate.cargo) in work.outputs) return false;
  local support = OpexV233Support(work.supports[key]);
  if (support == null || support.stationId != row.stationId || support.factoryTile != row.factoryTile) return false;
  if (!OpexV233JoinContextValid(candidate, candidate.cargo, candidate.src, this._catalog.railCoverage)) return false;
  if (AIIndustry.GetLastMonthProduction(row.factoryId, row.cargo) < V233_GOODS_MIN_MONTHLY) return false;
  if (!AITown.IsValidTown(candidate.dstTown) || AITown.GetLocation(candidate.dstTown) != candidate.dst) return false;
  if (OpexAbandonedPairKey(candidate) in this._abandonedPairs) return false;
  return true;
}

function OpexAI::_v233GraftStep()
{
  local work = this._v233GoodsWork;
  if (work == null || work.phase != "done" || this._projects == null) return;
  if (this._v233Offers == null) this._v233Offers = {};
  if (this._v233Plans == null) this._v233Plans = {};
  local gen = this._v233Generation;
  if (gen == null) {
    gen = { cursor = 0, current = null, seen = {} };
    this._v233Generation = gen;
  }
  if (gen.current == null) {
    if (gen.cursor >= work.keys.len()) return;
    local key = work.keys[gen.cursor++];
    if (!(key in work.rows)) return;
    local row = work.rows[key];
    local outputKey = row.factoryTile + "|" + row.cargo;
    if (outputKey in gen.seen) return;
    gen.seen[outputKey] <- true;
    if (outputKey in work.outputs || OpexV233Quantity(row, work.month) == 0) return;
    if (outputKey in this._v233Offers) {
      if (this._v233CandidateLive(this._v233Offers[outputKey])) return;
      this._v233ForgetPlan(this._v233Offers[outputKey], "observation_changed");
      delete this._v233Offers[outputKey];
      this._v233NeedsPublish = true;
    }
    if (!(row.cargo in this._catalog.townAcceptors)) return;
    local line = work.supports[key];
    local support = OpexV233Support(line);
    if (support == null) return;
    local p = line.platformB;
    local context = { strictJoin = true, joinEnd = "A", joinStationId = row.stationId,
      joinLineId = line.lineId, v233FactoryId = row.factoryId, v233StationTile = row.stationTile,
      v233Revision = work.revision,
      joinPlatform = { anchor = p.anchor, direction = p.direction, step = p.step,
                       length = p.length, station_exit = p.station_exit, lead = p.lead } };
    gen.current = { row = row, outputKey = outputKey, towns = this._catalog.townAcceptors[row.cargo],
                    cursor = 0, nearest = [], evaluate = 0, preferred = null, context = context };
    return;
  }
  local state = gen.current;
  /* Eight town inspections, keeping only three. No factory x source product. */
  if (state.cursor < state.towns.len()) {
    local bounds = OpexCatalogBounds(this._catalog);
    for (local n = 0; n < 8 && state.cursor < state.towns.len(); n++) {
      local town = state.towns[state.cursor++];
      local d = AIMap.DistanceManhattan(state.row.factoryTile, town.tile);
      if (d < bounds.railMin || d > bounds.railMax) continue;
      local entry = { town = town, distance = d };
      local pos = 0;
      while (pos < state.nearest.len() && (state.nearest[pos].distance < d
          || (state.nearest[pos].distance == d && state.nearest[pos].town.id < town.id))) pos++;
      state.nearest.insert(pos, entry);
      if (state.nearest.len() > 3) state.nearest.pop();
    }
    return;
  }
  if (state.evaluate < state.nearest.len()) {
    local town = state.nearest[state.evaluate++].town;
    local pair = "freight|" + state.row.cargo + "|" + state.row.factoryId + "|t" + town.id;
    if (pair in this._abandonedPairs || OpexOriginService(this._lines, town.tile) != null) return;
    /* At most ONE normal economic evaluation per invocation, with all common filters. */
    local candidate = OpexMakeCandidate(this._catalog, "freight", state.row.cargo,
      state.row.factoryTile, town.tile, OpexV233Quantity(state.row, work.month), true,
      OpexRailCandidateStats(), false, null, null, null, state.context);
    if (candidate == null) return;
    foreach (key, value in state.context) candidate[key] <- value;
    candidate.v233Graft <- true;
    candidate.dstTown <- town.id;
    if (!this._v233CandidateLive(candidate) || this._tooClose(candidate).hard >= 0
        || this._tooClose(candidate).blocking >= 0) return;
    if (state.preferred == null || candidate.roi > state.preferred.roi) state.preferred = candidate;
    return;
  }
  if (state.preferred != null) {
    this._v233Offers[state.outputKey] <- state.preferred;
    this._v233NeedsPublish = true;
    if (DECISION_LOG) OpexDecide("V233_GRAFT", "state=candidate factory=" + state.row.factoryId
      + " cargo=" + state.row.cargo + " station=" + state.row.stationId + " town=" + state.preferred.dstTown
      + " quantity=" + state.preferred.monthly + " profit=" + state.preferred.profitAnnual);
  }
  gen.current = null;
}

function OpexAI::_v233ForgetPlan(candidate, reason)
{
  local key = OpexV233PlanKey(candidate);
  if (this._v233Plans != null && key in this._v233Plans) delete this._v233Plans[key];
  if ("railPlan" in candidate) candidate.railPlan = null;
  this._v233NeedsPublish = true;
  if (DECISION_LOG) OpexDecide("V233_DROP", "reason=" + reason + " key=" + key
    + " factory=" + candidate.v233FactoryId + " cargo=" + candidate.cargo + " station=" + candidate.joinStationId);
}

function OpexAI::_v233StorePlan(candidate, plan)
{
  if (this._v233Plans == null) this._v233Plans = {};
  if ("railPlan" in candidate) candidate.railPlan = null;
  if (plan == null || !plan.ok || this._v233Plans.len() >= V233_PLAN_LIMIT) {
    this._v233ForgetPlan(candidate, "search_failed_or_stock_full");
    return;
  }
  local key = OpexV233PlanKey(candidate);
  this._v233Plans[key] <- { candidate = candidate, plan = plan, date = AIDate.GetCurrentDate(),
    revision = this._v233WorldRevision(), phase = "platforms", cursor = 1 };
  this._v233NeedsPublish = true;
  if (DECISION_LOG) OpexDecide("V233_SEARCH", "state=stock key=" + key
    + " factory=" + candidate.v233FactoryId + " cargo=" + candidate.cargo + " station=" + candidate.joinStationId);
}

/* Only touches prospective NEW infrastructure; never clears an existing rail tile.
 * This also makes rollback on the ordinary builders safe for a joint station. */
function OpexV233NewPlatform(p)
{
  if (p == null) return false;
  for (local i = 0; i < p.length; i++) {
    local tile = p.anchor + p.step * i;
    if (!AITile.IsBuildable(tile)) return false;
  }
  return true;
}

/* Last live check immediately before the ordinary transaction's first spend.
 * Stock validation is sliced; the final native command checks protect against competitors
 * changing tiles between slices. Snapshot shared station tiles for every rollback path. */
function OpexV233SpendAllowed(catalog, candidate, plan)
{
  if (!OpexV233JoinContextValid(candidate, candidate.cargo, candidate.src, catalog.railCoverage)
      || AIIndustry.GetLastMonthProduction(candidate.v233FactoryId, candidate.cargo) < V233_GOODS_MIN_MONTHLY
      || !("stationId" in plan.planA) || plan.planA.stationId != candidate.joinStationId
      || !OpexV131PlatformCargoOk(plan.planB, candidate, catalog, false)
      || !OpexV233FactoryCovered(plan.planA, candidate.v233FactoryId, candidate.cargo, catalog.railCoverage)) return false;
  local protectedTiles = {};
  local existing = AITileList_StationType(candidate.joinStationId, AIStation.STATION_TRAIN);
  for (local tile = existing.Begin(); !existing.IsEnd(); tile = existing.Next()) protectedTiles[tile] <- true;
  local platforms = [plan.planA, plan.planB];
  if (("planA2" in plan) && plan.planA2 != null) platforms.append(plan.planA2);
  if (("planB2" in plan) && plan.planB2 != null) platforms.append(plan.planB2);
  foreach (p in platforms) {
    if (!OpexV233NewPlatform(p)) return false;
    p.v233Protected <- protectedTiles;
  }
  local paths = [plan.tiles];
  if (("tiles2" in plan) && plan.tiles2 != null) paths.append(plan.tiles2);
  foreach (tiles in paths) {
    for (local i = 1; i < tiles.len() - 1; i++) {
      local tile = tiles[i];
      if (tile in protectedTiles || AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile)
          || AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) return false;
    }
  }
  return true;
}

function OpexAI::_v233PlanStep()
{
  if (this._v233Plans == null) return false;
  local stale = [];
  local chosen = null;
  local now = AIDate.GetCurrentDate();
  foreach (key, entry in this._v233Plans) {
    if (now - entry.date >= V233_PLAN_TTL_DAYS || !this._v233CandidateLive(entry.candidate)) stale.append(entry.candidate);
    else if (chosen == null && entry.phase != "ready") chosen = entry;
  }
  foreach (candidate in stale) this._v233ForgetPlan(candidate, "expired_or_not_live");
  if (chosen == null) return false;
  local entry = chosen;
  local plan = entry.plan;
  local candidate = entry.candidate;
  if (entry.revision != this._v233WorldRevision()) {
    entry.revision = this._v233WorldRevision();
    entry.phase = "platforms"; entry.cursor = 1;
  }
  if (entry.phase == "platforms") {
    if (plan.planA == null || plan.planB == null || plan.tiles == null || plan.tiles.len() < 3
        || !("stationId" in plan.planA) || plan.planA.stationId != candidate.joinStationId
        || !OpexV233NewPlatform(plan.planA) || !OpexV233NewPlatform(plan.planB)
        || !OpexV233FactoryCovered(plan.planA, candidate.v233FactoryId, candidate.cargo, this._catalog.railCoverage)
        || !OpexV131PlatformCargoOk(plan.planB, candidate, this._catalog, false)) {
      this._v233ForgetPlan(candidate, "platform_changed"); return true;
    }
    entry.phase = "track";
    return true;
  }
  if (entry.phase == "track") {
    /* Slice the route revalidation. Native track tests see the same triples as the builder. */
    local chunk = [plan.tiles[entry.cursor - 1]];
    for (local n = 0; n < 16 && entry.cursor < plan.tiles.len() - 1; n++) {
      local tile = plan.tiles[entry.cursor++];
      if (AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile)
          || AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) {
        this._v233ForgetPlan(candidate, "existing_infrastructure"); return true;
      }
      chunk.append(tile);
    }
    chunk.append(plan.tiles[entry.cursor]);
    local tested = OpexTestRailTrack(chunk, ("structures" in plan) ? plan.structures : null);
    if (tested.failed > 0) { this._v233ForgetPlan(candidate, "track_changed"); return true; }
    if (entry.cursor >= plan.tiles.len() - 1) entry.phase = "quote";
    return true;
  }
  /* One quote, on its own invocation. Price is published BEFORE ordinary selection. */
  local failure = {};
  local capital = OpexQuoteRailCapital(this._catalog, candidate, plan, failure);
  if (capital == null || capital <= 0) { this._v233ForgetPlan(candidate, "quote_failed"); return true; }
  OpexApplyRailActualCapital(candidate, capital);
  plan.capital = candidate.capital;
  entry.phase = "ready";
  plan.v233RankCapital <- candidate.capital;
  this._v233NeedsPublish = true;
  if (DECISION_LOG) OpexDecide("V233_SEARCH", "state=ready factory=" + candidate.v233FactoryId
    + " cargo=" + candidate.cargo + " station=" + candidate.joinStationId
    + " capital=" + candidate.capital + " profit=" + candidate.profitAnnual + " revision=" + entry.revision);
  return true;
}

/* Publication is only called at a pass boundary. It never runs inside best's traversal. */
function OpexAI::_v233Publish()
{
  if (this._projects == null || this._v233Offers == null) return;
  if (this._v233PublishedProjects == this._projects
      && this._v233PublishedGroups == this._projects.candidateGroups && !this._v233NeedsPublish) return;
  foreach (key, group in this._projects.candidateGroups) {
    for (local i = group.len() - 1; i >= 0; i--)
      if (OpexV233IsGraft(group[i].payload)) group.remove(i);
  }
  local dead = [];
  local stats = { modeCandidates = 0, modeAlternatives = 0 };
  foreach (key, candidate in this._v233Offers) {
    if (!this._v233CandidateLive(candidate)) {
      /* A monthly/revision rebuild is a temporary suspension, not an invalid observation. */
      if (this._v233GoodsWork != null && this._v233GoodsWork.phase == "done") dead.append(key);
      continue;
    }
    local planKey = OpexV233PlanKey(candidate);
    if (this._v233Plans != null && planKey in this._v233Plans) {
      local entry = this._v233Plans[planKey];
      if (entry.phase != "ready") continue;
      candidate.railPlan <- entry.plan;
    }
    OpexProjectRememberAll(this._projects.candidateGroups, OpexProjectFromCandidate(candidate), stats);
  }
  foreach (key in dead) {
    this._v233ForgetPlan(this._v233Offers[key], "publication_not_live");
    delete this._v233Offers[key];
  }
  OpexProjectsRecountGroups(this._projects);
  OpexReselectProjects(this._projects, OpexAvailableCapital(), this._abandonedPairs, this._lines);
  this._v233PublishedProjects = this._projects;
  this._v233PublishedGroups = this._projects.candidateGroups;
  this._v233NeedsPublish = false;
}
