/* Mode 5: reconstructible chain proposals, never an active-chain lock.
 * Native processing multipliers are 256/256 (OpenTTD 15.3). NewGRF callbacks
 * are opaque to NoAI: the forecast is restricted to the native recipe.
 * Qualification requires the native, no-NewGRF campaign configuration. */
function OpexV233ChainFactory(industry)
{
  if (!AIIndustry.IsValidIndustry(industry)) return -1;
  local type = AIIndustry.GetIndustryType(industry);
  local inputs = AIIndustryType.GetAcceptedCargo(type);
  if (inputs.Count() < 3 || !AIIndustryType.IsProcessingIndustry(type)) return -1;
  local outputs = AIIndustryType.GetProducedCargo(type);
  for (local cargo = outputs.Begin(); !outputs.IsEnd(); cargo = outputs.Next())
    if (AICargo.GetCargoLabel(cargo) == "GOOD") return cargo;
  return -1;
}

function OpexV233ChainParts(candidate)
{
  local project = OpexProjectFromCandidate(candidate);
  if (project == null) return { profit = 0.0, capital = 0.0 };
  return { profit = OpexProjectFundProfit(project), capital = OpexProjectFinanceCapital(project) };
}

function OpexV233ChainYield(profit, capital, factory, cargo)
{
  if (profit <= 0 || capital <= 0) return false;
  // The existing measured AIR floor receives the whole investment, not just
  // the first input's capital. No option is included in this comparison.
  local candidate = { mode = "rail", kind = "freight", cargo = cargo,
    src = 0, dst = 0, distance = 0, iterations = 0, capital = capital,
    profitAnnual = profit, revenueAnnual = profit, roi = 0, capitalIsActual = true, v233FactoryId = factory };
  // profit is already calibrated: compensate the common rail factor once.
  local project = OpexProjectFromCandidate(candidate);
  local factor = OpexC70Factor(project);
  if (factor <= 0) return false;
  candidate.profitAnnual = profit / factor;
  return OpexV233AirYieldAllows(candidate);
}

function OpexV233ChainFed(ai, factory)
{
  if (OpexV233ChainFactory(factory) < 0) return false;
  local accepted = AIIndustryType.GetAcceptedCargo(AIIndustry.GetIndustryType(factory));
  local covered = {};
  foreach (line in ai._lines) {
    local support = OpexV233Support(line);
    if (support == null || support.factoryId != factory) continue;
    covered[line.cargo] <- true;
    if (("cargo2" in line) && ("wagons2" in line) && line.wagons2 > 0)
      covered[line.cargo2] <- true;
  }
  local any = false;
  for (local cargo = accepted.Begin(); !accepted.IsEnd(); cargo = accepted.Next()) {
    local label = AICargo.GetCargoLabel(cargo);
    if ((label == "GRAI" || label == "LVST") && !(cargo in covered)) return false;
    if (cargo in covered) any = true;
  }
  return any;
}

function OpexV233ChainVolume(row)
{
  if (row.count != 3 || row.lastMonth != OpexV233eMonth()) return 0;
  return (row.q0 + row.q1 + row.q2) / 3;
}

function OpexV233ChainTrainReady(candidate, row)
{
  // A full dimensioned consist per rotation, after the model's capture rate.
  // No fixed 64-unit gate and no invented multi-wagon minimum.
  local monthly = OpexV233ChainVolume(row);
  return monthly > 0 && monthly * candidate.stationRating / 100.0
    >= candidate.perTrain * candidate.tripsPerMonth;
}

function OpexV233ChainInputLive(ai, candidate)
{
  if (!("v233ChainInput" in candidate)) return false;
  if (AIDate.GetCurrentDate() - candidate.v233ChainDate >= V233_PLAN_TTL_DAYS) return false;
  if (!AIIndustry.IsValidIndustry(candidate.v233InputSource)
      || AIIndustry.GetLocation(candidate.v233InputSource) != candidate.src
      || !AIIndustry.IsValidIndustry(candidate.v233FactoryId)
      || AIIndustry.GetLocation(candidate.v233FactoryId) != candidate.dst) return false;
  if (OpexOriginService(ai._lines, candidate.src) != null) return false;
  if (AIIndustry.GetLastMonthProduction(candidate.v233InputSource, candidate.cargo) < candidate.monthly) return false;
  if (("cargo2" in candidate) && candidate.wagons2 > 0
      && AIIndustry.GetLastMonthProduction(candidate.v233InputSource, candidate.cargo2) < candidate.monthly2) return false;
  if (OpexAbandonedPairKey(candidate) in ai._abandonedPairs) return false;
  return OpexV233ChainInputSpend(candidate);
}

function OpexV233ChainInputSpend(candidate)
{
  if (AIDate.GetCurrentDate() - candidate.v233ChainDate >= V233_PLAN_TTL_DAYS
      || OpexV233ChainFactory(candidate.v233FactoryId) < 0
      || AIIndustry.GetLocation(candidate.v233FactoryId) != candidate.dst
      || !AIIndustry.IsValidIndustry(candidate.v233InputSource)
      || AIIndustry.GetLocation(candidate.v233InputSource) != candidate.src
      || AIIndustry.GetLastMonthProduction(candidate.v233InputSource, candidate.cargo) < candidate.monthly) return false;
  if (("cargo2" in candidate) && candidate.wagons2 > 0
      && AIIndustry.GetLastMonthProduction(candidate.v233InputSource, candidate.cargo2) < candidate.monthly2) return false;
  local own = OpexV233ChainParts(candidate);
  if (own.profit <= 0 || own.capital <= 0) return false;
  local factor = OpexC70Factor(OpexProjectFromCandidate(candidate));
  return OpexV233ChainYield((candidate.v233ChainProfit - candidate.v233InitialProfit)
      * factor / candidate.v233ChainFactor + own.profit,
    candidate.v233ChainCapital - candidate.v233InitialCapital + own.capital,
    candidate.v233FactoryId, candidate.cargo);
}

function OpexV233ChainInputPlan(candidate, plan, coverage)
{
  local accepted = AIIndustryType.GetAcceptedCargo(AIIndustry.GetIndustryType(candidate.v233FactoryId));
  if (!accepted.HasItem(candidate.cargo)
      || (("cargo2" in candidate) && candidate.wagons2 > 0 && !accepted.HasItem(candidate.cargo2))) return false;
  local catchment = AITileList_IndustryAccepting(candidate.v233FactoryId, coverage);
  for (local i = 0; i < plan.planB.length; i++)
    if (catchment.HasItem(plan.planB.anchor + plan.planB.step * i)) return true;
  return false;
}

function OpexV233ChainGraftLive(ai, candidate)
{
  if (!OpexV233ChainFed(ai, candidate.v233FactoryId) || ai._v233GoodsObservations == null) return false;
  local key = OpexV233ObservationKey(candidate.v233FactoryId, candidate.cargo, candidate.joinStationId);
  if (!(key in ai._v233GoodsObservations)) return false;
  local row = ai._v233GoodsObservations[key];
  return OpexV233ChainVolume(row) >= candidate.monthly
    && OpexV233ChainTrainReady(candidate, row) && OpexV233AirYieldAllows(candidate);
}

function OpexV233ChainScore(project, kDec)
{
  local c = project.payload;
  if (!("v233ChainInput" in c)) return project.fundScore;
  local own = OpexV233ChainParts(c);
  local totalCapital = c.v233ChainCapital - c.v233InitialCapital + own.capital;
  local factor = OpexC70Factor(project) / c.v233ChainFactor;
  local totalProfit = (c.v233ChainProfit - c.v233InitialProfit) * factor + own.profit;
  local totalDenom = totalCapital > kDec ? totalCapital : kDec;
  local chainScore = OpexProjectScore(totalProfit, totalDenom);
  local bonus = 0.0;
  if (c.v233OptionRepresentative) {
    local a = 3.79078677; // sum(1/1.1^t), t=1..5, approved conception §3(a)
    local value = c.v233GoodsCash * factor * a - c.v233GoodsCapital;
    if (value > 0) {
      local annual = 0.25 * value / (1.21 * a);
      local denom = c.v233GoodsCapital > kDec ? c.v233GoodsCapital : kDec;
      bonus = OpexProjectScore(annual, denom);
      if (bonus > project.fundScore * 0.10) bonus = project.fundScore * 0.10;
    }
  }
  local score = project.fundScore + bonus;
  return score < chainScore ? score : chainScore;
}

function OpexV233ChainStep(ai)
{
  if (!V233_GOODS_CHAIN || !MODE_RAIL || ai._projects == null) return;
  if (ai._v233Offers == null) ai._v233Offers = {};
  local work = ai._v233ChainWork;
  local month = OpexV233eMonth();
  if (work == null || (work.current == null && work.cursor >= work.rows.len() && work.month != month)) {
    work = { month = month, rows = ai._catalog.industries, cursor = 0, current = null };
    ai._v233ChainWork = work;
    if (ai._v233ChainOffers == null) ai._v233ChainOffers = {};
  }
  if (work.current == null) {
    if (work.cursor >= work.rows.len()) return;
    local factory = work.rows[work.cursor++];
    local goods = OpexV233ChainFactory(factory.id);
    if (goods < 0 || OpexV233eOutputAllocated(ai, factory.tile, goods)) return;
    local inputs = [];
    local list = AIIndustryType.GetAcceptedCargo(factory.type);
    for (local cargo = list.Begin(); !list.IsEnd(); cargo = list.Next()) inputs.append(cargo);
    work.current = { factory = factory, goods = goods, inputs = inputs, input = 0,
      source = 0, inputChoices = {}, chosen = [], line = 0, phase = "lines", town = 0,
      covered = {}, sources = {}, profit = 0.0, capital = 0.0, volume = 0, downstream = null };
    return;
  }
  local state = work.current;
  if (!AIIndustry.IsValidIndustry(state.factory.id)
      || AIIndustry.GetLocation(state.factory.id) != state.factory.tile) { work.current = null; return; }
  if (state.phase == "lines") {
    if (state.line < ai._lines.len()) {
      local line = ai._lines[state.line++];
      local support = OpexV233Support(line);
      if (support != null && support.factoryId == state.factory.id && ("v233InputCapital" in line)) {
        state.profit += line.v233InputProfit * OpexC70Factor({ mode = "rail" });
        state.capital += line.v233InputCapital;
        state.volume += line.predCarried;
        state.covered[line.cargo] <- true;
        if (("cargo2" in line) && line.wagons2 > 0) {
          state.volume += line.v233InputCarried2;
          state.covered[line.cargo2] <- true;
        }
        state.sources[line.originA] <- true;
      }
      return;
    }
    state.phase = "inputs";
  }
  if (state.phase == "inputs") {
    if (state.input < state.inputs.len()) {
      local cargo = state.inputs[state.input];
      local sources = cargo in ai._catalog.producers ? ai._catalog.producers[cargo] : [];
      if (state.source >= sources.len()) { state.input++; state.source = 0; return; }
      local si = sources[state.source++];
      local out = [];
      // A fresh physical source test; the ordinary generator owns this cache.
      local cacheKey = ai._catalog.industries[si].tile * 64 + cargo;
      if (cacheKey in ::OpexSitableCache) delete ::OpexSitableCache[cacheKey];
      OpexFreightCandidates(ai._catalog, ai._lines, out, OpexRailCandidateStats(), ai._abandonedPairs,
        null, null, cargo, "industry", state.factory.id, { source = si, factory = state.factory.id });
      foreach (candidate in out) {
        local parts = OpexV233ChainParts(candidate);
        if (!(cargo in state.inputChoices) || parts.profit / parts.capital > state.inputChoices[cargo].yieldValue)
          state.inputChoices[cargo] <- { candidate = candidate, yieldValue = parts.profit / parts.capital };
      }
      return;
    }
    // At most the API's accepted-cargo count, not all source combinations.
    foreach (cargo in state.inputs) {
      if (cargo in state.covered || !(cargo in state.inputChoices)) continue;
      local c = state.inputChoices[cargo].candidate;
      if (c.src in state.sources) continue;
      local parts = OpexV233ChainParts(c);
      state.profit += parts.profit; state.capital += parts.capital;
      state.volume += c.carried;
      state.covered[c.cargo] <- true; state.sources[c.src] <- true;
      if (("cargo2" in c) && c.wagons2 > 0) {
        state.volume += c.carried2; state.covered[c.cargo2] <- true;
      }
      state.chosen.append(c);
    }
    foreach (cargo in state.inputs) {
      local label = AICargo.GetCargoLabel(cargo);
      if ((label == "GRAI" || label == "LVST") && !(cargo in state.covered)) { work.current = null; return; }
    }
    if (state.chosen.len() == 0 || state.volume <= 0) { work.current = null; return; }
    state.phase = "towns";
  }
  if (state.phase == "towns") {
    local towns = state.goods in ai._catalog.townAcceptors ? ai._catalog.townAcceptors[state.goods] : [];
    if (state.town < towns.len()) {
      local town = towns[state.town++];
      local distance = AIMap.DistanceManhattan(state.factory.tile, town.tile);
      if (distance > OpexCatalogBounds(ai._catalog).railMax) return;
      // Same rail economy as the graft; no speculative site search or A*.
      local e = OpexLineEconomics(ai._catalog, state.goods, distance, state.volume, "freight");
      if (e == null || e.profitAnnual <= 0) return;
      local c = clone e;
      c.mode <- "rail"; c.kind <- "freight"; c.cargo <- state.goods;
      c.src <- state.factory.tile; c.dst <- town.tile; c.distance <- distance; c.iterations <- 0;
      local parts = OpexV233ChainParts(c);
      if (state.downstream == null || parts.profit / parts.capital > state.downstream.yieldValue)
        state.downstream = { parts = parts, economics = e, town = town.id,
          yieldValue = parts.profit / parts.capital };
      return;
    }
    local downstream = state.downstream;
    // One current option representative per factory, even after a changed plan.
    local obsolete = [];
    foreach (key, offer in ai._v233ChainOffers)
      if (offer.v233FactoryId == state.factory.id) obsolete.append(key);
    foreach (key in obsolete) delete ai._v233ChainOffers[key];
    if (obsolete.len() > 0) ai._v233NeedsPublish = true;
    if (downstream != null) {
      local profit = state.profit + downstream.parts.profit;
      local capital = state.capital + downstream.parts.capital;
      local allowed = OpexV233ChainYield(profit, capital, state.factory.id, state.goods);
      if (DECISION_LOG) OpexDecide("V233_CHAIN", "state=candidate factory=" + state.factory.id
        + " inputs=" + state.chosen.len() + " input_profit=" + state.profit + " input_capital=" + state.capital
        + " goods_profit=" + downstream.parts.profit + " goods_capital=" + downstream.parts.capital
        + " total_profit=" + profit + " total_capital=" + capital + " yield=" + profit / capital
        + " goods_monthly=" + state.volume + " town_hint=" + downstream.town + " allowed=" + allowed);
      if (allowed) {
        for (local i = 0; i < state.chosen.len(); i++) {
          local c = state.chosen[i];
          c.v233ChainInput <- true; c.v233FactoryId <- state.factory.id;
          c.v233InputSource <- AIIndustry.GetIndustryID(c.src);
          c.v233ChainDate <- AIDate.GetCurrentDate();
          c.v233ChainProfit <- profit; c.v233ChainCapital <- capital;
          c.v233ChainFactor <- OpexC70Factor(OpexProjectFromCandidate(c));
          local own = OpexV233ChainParts(c);
          c.v233InitialProfit <- own.profit; c.v233InitialCapital <- own.capital;
          c.v233GoodsCash <- (downstream.economics.profitAnnual + downstream.economics.amortAnnual)
            * downstream.parts.profit / downstream.economics.profitAnnual;
          c.v233GoodsCapital <- downstream.parts.capital;
          c.v233OptionRepresentative <- i == 0;
          ai._v233ChainOffers[OpexAbandonedPairKey(c)] <- c;
        }
        ai._v233NeedsPublish = true;
      }
    }
    work.current = null;
  }
}

function OpexV233ChainPublish(ai, stats)
{
  if (ai._v233ChainOffers == null) return;
  local dead = [];
  foreach (key, candidate in ai._v233ChainOffers) {
    if (!OpexV233ChainInputLive(ai, candidate)) { dead.append(key); continue; }
    local project = OpexProjectFromCandidate(candidate);
    local pair = OpexProjectKeyFor(project);
    // The ordinary generator may already contain this exact rail pair. Keep
    // one rail offer carrying its chain contract; road alternatives stay intact.
    if (pair in ai._projects.candidateGroups) {
      local group = ai._projects.candidateGroups[pair];
      for (local i = group.len() - 1; i >= 0; i--)
        if (group[i].mode == "rail") group.remove(i);
    }
    OpexProjectRememberAll(ai._projects.candidateGroups, project, stats);
  }
  foreach (key in dead) delete ai._v233ChainOffers[key];
}
