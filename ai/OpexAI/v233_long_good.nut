/* V233L : sorties GOOD longues, independantes des anciennes greffes V233.
 * Toutes les entrees sont court-circuitees par V233_LONG_GOOD. Fenetres de
 * six mois CLOS consecutifs ; ni stock transforme en debit, ni croissance promise.
 * Budget cooperatif : une unite native/economique peut depasser le plafond. */
const V233L_WINDOW = 6;
const V233L_MAX_FACTORIES = 64;
const V233L_SLICE_OPS = 20000;
const V233L_TOWNS = 8;

function OpexV233LIs(candidate)
{
  return V233_LONG_GOOD > 0 && candidate != null
      && ("v233LongGood" in candidate) && candidate.v233LongGood;
}

function OpexV233LLog(event, fields)
{
  if (DECISION_LOG) OpexDecide("V233L_" + event, fields);
}

function OpexV233LNewState()
{
  return { month = -1, cursor = 0, rows = {}, growth = {}, pending = null };
}

function OpexV233LGoodCargo()
{
  local cargos = AICargoList();
  for (local cargo = cargos.Begin(); !cargos.IsEnd(); cargo = cargos.Next())
    if (AICargo.GetCargoLabel(cargo) == "GOOD") return cargo;
  return -1;
}

function OpexV233LMonth()
{
  local today = AIDate.GetCurrentDate();
  return AIDate.GetYear(today) * 12 + AIDate.GetMonth(today);
}

/* Le bassin doit toucher CETTE usine, pas seulement produire le meme cargo. */
function OpexV233LTouches(plan, industry, producing, coverage)
{
  local tiles = producing ? AITileList_IndustryProducing(industry, coverage)
                         : AITileList_IndustryAccepting(industry, coverage);
  for (local i = 0; i < plan.length; i++)
    if (tiles.HasItem(plan.anchor + i * plan.step)) return true;
  return false;
}

function OpexV233LCargoValue(anchor, step, length, cargo, coverage, producing)
{
  local horizontal = abs(step) == 1;
  return producing ? AITile.GetCargoProduction(anchor, cargo,
      horizontal ? length : 1, horizontal ? 1 : length, coverage)
      : AITile.GetCargoAcceptance(anchor, cargo,
      horizontal ? length : 1, horizontal ? 1 : length, coverage);
}

function OpexV233LInput(line, cargo)
{
  if (line == null || !("mode" in line) || line.mode != "rail"
      || !("kind" in line) || line.kind != "freight" || line.cargo == cargo
      || !("platformB" in line) || line.platformB == null
      || !("vehicles" in line) || line.vehicles.len() == 0
      || (("scrapping" in line) && line.scrapping)) return -1;
  local industry = AIIndustry.GetIndustryID(line.originB);
  if (!AIIndustry.IsValidIndustry(industry)
      || !AIIndustryType.IsProcessingIndustry(AIIndustry.GetIndustryType(industry))) return -1;
  local producing = AICargoList_IndustryProducing(industry);
  local accepting = AICargoList_IndustryAccepting(industry);
  if (!producing.HasItem(cargo) || !accepting.HasItem(line.cargo)) return -1;
  local station = OpexLineStationId(line, "B");
  if (station < 0 || AITile.GetOwner(line.stationB) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) return -1;
  if (!OpexV233LTouches(line.platformB, industry, false,
      AIStation.GetCoverageRadius(AIStation.STATION_TRAIN))) return -1;
  local vehicle = line.vehicles[0];
  if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetCapacity(vehicle, line.cargo) <= 0
      || !OpexVehicleServesStation(vehicle, station)) return -1;
  return industry;
}

function OpexV233LObserve(owner)
{
  local state = V233L_STATE;
  local month = OpexV233LMonth();
  if (state.month != month) { state.month = month; state.cursor = 0; }
  if (owner._lines == null || state.cursor >= owner._lines.len()) return;
  local mark = OpexOpsMeasureBegin();
  local cargo = OpexV233LGoodCargo();
  if (cargo < 0) { state.cursor = owner._lines.len(); return; }
  local count = 0;
  while (state.cursor < owner._lines.len() && count < 8
      && OpexOpsMeasureEnd(mark) < V233L_SLICE_OPS) {
    local line = owner._lines[state.cursor++];
    count++;
    OpexV233LObserveBacklog(line, month);
    local industry = OpexV233LInput(line, cargo);
    if (industry < 0) continue;
    if (!(industry in state.rows)) {
      if (state.rows.len() >= V233L_MAX_FACTORIES) continue;
      state.rows.rawset(industry, { month = -1, tile = line.originB,
        production = [], residual = [], inputLine = line.lineId, station = -1, townCursor = 0,
        exportLine = -1, exportMonth = -1 });
    }
    local row = state.rows[industry];
    if (row.tile != line.originB) { row.production = []; row.residual = []; row.month = -1; }
    row.tile = line.originB;
    row.inputLine = line.lineId;
    row.station = OpexLineStationId(line, "B");
    if (row.month == month - 1) continue; // plusieurs intrants : un seul mois observe.
    if (row.month != month - 2) { row.production = []; row.residual = []; }
    local production = AIIndustry.GetLastMonthProduction(industry, cargo);
    local transported = AIIndustry.GetLastMonthTransported(industry, cargo);
    if (OpexV233LMonth() != month) break; // ne pas etiqueter un mois nouveau avec l'ancien.
    local residual = production - transported;
    if (residual < 0) residual = 0;
    row.production.append(production);
    row.residual.append(residual);
    if (row.production.len() > V233L_WINDOW) { row.production.remove(0); row.residual.remove(0); }
    row.month = month - 1;
    if (DECISION_LOG) OpexV233LLog("PRODUCTION", "industry=" + industry + " month=" + row.month
        + " produced=" + production + " transported=" + transported + " residual=" + residual
        + " samples=" + row.production.len() + " station=" + row.station
        + " input_cargo=" + AICargo.GetCargoLabel(line.cargo)
        + " good_rating=" + AIStation.GetCargoRating(row.station, cargo));
  }
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=observe units=" + count
      + " ops=" + OpexOpsMeasureEnd(mark) + " budget=" + V233L_SLICE_OPS);
}

function OpexV233LMin(values)
{
  local result = null;
  foreach (value in values) if (result == null || value < result) result = value;
  return result == null ? 0 : result;
}

function OpexV233LMean(values)
{
  local total = 0;
  foreach (value in values) total += value;
  return values.len() > 0 ? total / values.len() : 0;
}

/* Une secondaire produit a la livraison : des mois nuls entre deux trains
 * sont normaux. Six mois observes, au moins deux livraisons productives et
 * une production dans la demi-fenetre recente, sans imputer les mois absents. */
function OpexV233LDurable(values)
{
  if (values.len() != V233L_WINDOW) return false;
  local positive = 0;
  local recent = 0;
  for (local i = 0; i < values.len(); i++) {
    if (values[i] > 0) positive++;
    if (i >= 3) recent += values[i];
  }
  return positive >= 2 && recent > 0;
}

/* Appel une fois par source, jamais une fois par ville. Le service existant
 * NON-GOOD est distinct du depart GOOD ; une sortie deja exploitee est exclue. */
function OpexV233LSource(source, cargo, lines)
{
  if (!SAVE_FULL_STATE || V233L_STATE == null || AICargo.GetCargoLabel(cargo) != "GOOD"
      || !(source.id in V233L_STATE.rows)) return null;
  local row = V233L_STATE.rows[source.id];
  local mark = OpexOpsMeasureBegin();
  local ready = row.tile == source.tile && row.month == OpexV233LMonth() - 1
      && OpexV233LDurable(row.production);
  local inputLive = false;
  foreach (line in lines) {
    if (OpexOpsMeasureEnd(mark) >= V233L_SLICE_OPS) { ready = false; break; }
    if (("lineId" in line) && line.lineId == row.inputLine
        && OpexV233LInput(line, cargo) == source.id) inputLive = true;
    if (("cargo" in line) && line.cargo == cargo && ("originA" in line)
        && line.originA == source.tile && (!("scrapping" in line) || !line.scrapping)) ready = false;
  }
  ready = ready && inputLive && OpexV233LMean(row.residual) > 0;
  return { ready = ready, row = row, monthly = OpexV233LMean(row.residual),
    ops = OpexOpsMeasureEnd(mark), townStart = row.townCursor, visits = 0 };
}

function OpexV233LAdmit(context, source, town)
{
  local mark = OpexOpsMeasureBegin();
  context.visits++;
  local distance = AIMap.DistanceManhattan(source.tile, town.tile);
  local reason = !context.ready ? "production_or_export" :
      (distance < 150 || distance > 300 ? "distance" : "OK");
  if (reason != "OK" && DECISION_LOG) OpexV233LLog("REJECT",
      "industry=" + source.id + " town=" + town.id + " reason=" + reason + " distance=" + distance);
  context.ops += OpexOpsMeasureEnd(mark);
  return reason == "OK";
}

function OpexV233LSourceEnd(context, source)
{
  context.row.townCursor = (context.row.townCursor + context.visits) % 65536;
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=candidates industry=" + source.id
      + " towns=" + context.visits + " ops=" + context.ops
      + " budget=" + V233L_SLICE_OPS);
}

/* Source propre d'abord si elle capte effectivement l'usine. Une jointure
 * native au quai d'intrants est aussi possible : pas de voie d'intrants reutilisee.
 * Le cargo de ce quai n'est jamais assimile a GOOD. */
function OpexV233LPlatformPlans(catalog, candidate)
{
  local mark = OpexOpsMeasureBegin();
  local statsA = { nClear = 0, nCargo = 0, nCmd = 0 };
  local statsB = { nClear = 0, nCargo = 0, nCmd = 0 };
  local industry = AIIndustry.GetIndustryID(candidate.src);
  local wanted = candidate.platformLength;
  for (local length = wanted; length >= OpexRailMinimumPlatformLength(); length--) {
    if (OpexOpsMeasureEnd(mark) >= V233L_SLICE_OPS) break;
    local rawA = OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS,
        length, MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, true, statsA, true, 0, true, mark);
    local plansA = [];
    foreach (p in rawA) {
      if (!OpexV233LTouches(p, industry, true, catalog.railCoverage)) continue;
      local station = candidate.v233InputStation;
      /* Meme captage, StationID partage si le moteur l'autorise. Une note GOOD
       * deja active est relevee au recalcul, pas la note du cargo entrant. */
      local shared = false;
      local goodRating = AIStation.IsValidStation(station) ? AIStation.GetCargoRating(station, candidate.cargo) : -1;
      if (AIStation.IsValidStation(station) && (goodRating <= 0 || goodRating >= candidate.stationRating)) {
        local accounting = AIAccounting();
        local test = AITestMode();
        shared = AIRail.BuildRailStation(p.anchor, p.direction, 1, p.length, station);
      }
      if (shared) p.stationId <- station;
      plansA.append(p);
    }
    local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS,
        length, MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, false, statsB, true, 0, true, mark);
    if (plansA.len() > 0 && plansB.len() > 0) return {
      plansA = plansA, plansB = plansB, length = length, slopeRelaxed = 0,
      reason = "OK", statsA = statsA, statsB = statsB };
  }
  return { plansA = null, plansB = null, length = wanted, slopeRelaxed = 0,
    reason = OpexRailSiteReason(statsA.nCmd > 0, statsB.nCmd > 0), statsA = statsA, statsB = statsB };
}

/* Seule exception de proximite : cote A, quai NON-GOOD livrant exactement
 * cette usine. Cote B et tous les autres voisins restent controles. */
function OpexV233LSourceNeighbour(candidate, line, end)
{
  return OpexV233LIs(candidate) && end == "A" && line.originB == candidate.src
      && line.cargo != candidate.cargo;
}

function OpexV233LTick(owner)
{
  if (!SAVE_FULL_STATE) return; // transactions et identites exigent la sauvegarde complete.
  if (V233L_STATE == null) V233L_STATE = OpexV233LNewState();
  OpexV233LObserve(owner);
  OpexV233LContinueGrowth(owner);
}

function OpexV233LRecheck(candidate, plan)
{
  local industry = AIIndustry.GetIndustryID(candidate.src);
  if (V233L_STATE == null || !(industry in V233L_STATE.rows) || plan.doubleTrack != 1
      || plan.planA == null || plan.planB == null) return false;
  local row = V233L_STATE.rows[industry];
  if (row.month != OpexV233LMonth() - 1 || row.residual.len() != V233L_WINDOW
      || !OpexV233LDurable(row.production) || OpexV233LMean(row.residual) < candidate.monthly) return false;
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  if (!OpexV233LTouches(plan.planA, industry, true, coverage)
      || OpexV233LCargoValue(plan.planB.anchor, plan.planB.step, plan.planB.length,
          candidate.cargo, coverage, false) < 8) return false;
  local sourceTile = ("stationId" in plan.planA) ? AIStation.GetLocation(plan.planA.stationId) : plan.planA.anchor;
  local distance = AIMap.DistanceManhattan(sourceTile, plan.planB.anchor);
  return distance >= 150 && distance <= 300;
}

function OpexV233LInputTarget(line)
{
  if (V233L_STATE == null || line == null || !("originB" in line)) return false;
  local industry = AIIndustry.GetIndustryID(line.originB);
  if (!(industry in V233L_STATE.rows)) return false;
  local row = V233L_STATE.rows[industry];
  if (row.exportLine < 0 || row.exportMonth < OpexV233LMonth() - 1) return false;
  if (row.month != OpexV233LMonth() - 1 || !OpexV233LDurable(row.production)) return false;
  return OpexV233LInput(line, OpexV233LGoodCargo()) == industry;
}

function OpexV233LObserveBacklog(line, month)
{
  if (line == null || !("mode" in line) || line.mode != "rail"
      || !("vehicles" in line) || line.vehicles.len() == 0 || !("lineId" in line)) return;
  if (OpexV233LIs(line) && (!("scrapping" in line) || !line.scrapping)
      && AIVehicle.IsValidVehicle(line.vehicles[0])) {
    local industry = AIIndustry.GetIndustryID(line.originA);
    if (industry in V233L_STATE.rows) {
      V233L_STATE.rows[industry].exportLine = line.lineId;
      V233L_STATE.rows[industry].exportMonth = month;
    }
  }
  if (!OpexV233LIs(line) && !OpexV233LInputTarget(line)) return;
  local station = OpexLineStationId(line, "A");
  if (station < 0) return;
  local growth = V233L_STATE.growth;
  if (!(line.lineId in growth)) {
    if (growth.len() >= 128) return;
    growth.rawset(line.lineId, { month = -1, waiting = [], nextMonth = -1 });
  }
  local row = growth[line.lineId];
  if (row.month == month) return;
  if (row.month != month - 1) row.waiting = [];
  row.month = month;
  row.waiting.append(AIStation.GetCargoWaiting(station, line.cargo));
  if (row.waiting.len() > 3) row.waiting.remove(0);
}

function OpexV233LBacklog(line, waiting, required)
{
  if (V233L_STATE == null || !(line.lineId in V233L_STATE.growth)) return false;
  local row = V233L_STATE.growth[line.lineId];
  return row.month == OpexV233LMonth() && row.month >= row.nextMonth
      && row.waiting.len() == 3 && waiting >= required && OpexV233LMin(row.waiting) >= required;
}

/* Capacite mensuelle et tarif issus de la physique C41 et de l'API du jeu.
 * Le stock confirme l'exposition, il n'est jamais annualise. */
function OpexV233LFleetMargin(line, vehicle, added, newLoco, newWagons, extraCost = 0)
{
  local industry = AIIndustry.GetIndustryID(line.originA);
  if (!AIIndustry.IsValidIndustry(industry)) return null;
  local production = AIIndustry.GetLastMonthProduction(industry, line.cargo);
  local station = OpexLineStationId(line, "A");
  if (station < 0 || production <= 0) return null;
  local rating = AIStation.GetCargoRating(station, line.cargo);
  if (rating <= 0) return null;
  local wagon = OpexV257Engine(AIVehicle.GetWagonEngineType(vehicle, 1), line.cargo, true);
  local oldLoco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
  local oldWagons = AIVehicle.GetNumWagons(vehicle) - 1;
  local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
  local oldSpeed = OpexRailEffectiveSpeed(oldLoco, wagon, oldWagons, distance);
  local newSpeed = OpexRailEffectiveSpeed(newLoco, wagon, newWagons, distance);
  if (oldSpeed <= 0 || newSpeed < oldSpeed) return null;
  local oldDays = distance / (0.036 * oldSpeed);
  local newDays = distance / (0.036 * newSpeed);
  local dwell = OpexRailStationDwellDays(wagon);
  local oldCapacity = AIVehicle.GetCapacity(vehicle, line.cargo) * 30.0 / (2 * oldDays + dwell);
  local newCapacity = newWagons * wagon.capacity * 30.0 / (2 * newDays + dwell);
  local offered = production * rating / 100.0;
  /* Pour une sortie neuve, ne pas promettre les flux pris par les rivaux. */
  if (OpexV233LIs(line)) {
    local factory = AIIndustry.GetIndustryID(line.originA);
    if (!(factory in V233L_STATE.rows)) return null;
    local row = V233L_STATE.rows[factory];
    if (row.month != OpexV233LMonth() - 1 || !OpexV233LDurable(row.production)) return null;
    offered = OpexV233LMean(row.production) * rating / 100.0;
  }
  local before = line.vehicles.len() * oldCapacity;
  local after = added ? before + newCapacity : before - oldCapacity + newCapacity;
  if (before > offered) before = offered;
  if (after > offered) after = offered;
  local delta = after - before;
  if (delta <= 0) return null;
  local loadDays = newWagons * wagon.capacity * 30.0 / offered;
  local income = AICargo.GetCargoIncome(line.cargo, line.distance, OpexCeilDiv(newDays + loadDays / 2, 1));
  local cost = newLoco.price + newWagons * wagon.price + extraCost;
  local running = newLoco.runningCost - (added ? 0 : oldLoco.runningCost);
  local profit = 12 * delta * income - running - cost / (newLoco.ageYears > 0 ? newLoco.ageYears : 20);
  if (profit <= 0 || OpexAvailableCapital() < cost + OpexCashReserve()) return null;
  return { profit = profit, cost = cost, monthly = delta };
}

function OpexV233LInputMargin(line, selected, equipment, number, loopPlan)
{
  local loco = OpexV257Engine(equipment.engine, line.cargo, false);
  local infrastructure = loopPlan == null ? 0 : loopPlan.pieces.len() * AIRail.GetBuildCost(
      AIRail.GetRailType(line.depot), AIRail.BT_TRACK);
  local margin = OpexV233LFleetMargin(line, selected.vehicle, selected.add, loco, number, infrastructure);
  if (margin == null) {
    if (DECISION_LOG) OpexV233LLog("REJECT", "line=" + line.lineId + " reason=input_margin");
    return false;
  }
  V233L_STATE.growth[line.lineId].nextMonth = OpexV233LMonth() + 3;
  if (DECISION_LOG) OpexV233LLog("INPUT_PICK", "line=" + line.lineId + " monthly=" + margin.monthly + " profit=" + margin.profit);
  return true;
}

function OpexV233LSelectGrowth(owner, year)
{
  if (!SAVE_FULL_STATE || V233L_STATE == null || owner._lines == null || owner._v257Pending != null
      || owner._railExpansion != null || OpexV284Busy(owner) || V233L_STATE.pending != null) return false;
  local mark = OpexOpsMeasureBegin();
  local best = null;
  foreach (line in owner._lines) {
    if (OpexOpsMeasureEnd(mark) >= V233L_SLICE_OPS) break;
    local exportGood = OpexV233LIs(line);
    local input = !exportGood && OpexV233LInputTarget(line);
    if ((!exportGood && !input) || line.vehicles.len() < 2 || line.vehicles.len() >= 14
        || !("v181Loop" in line) || !line.v181Loop || line.doubleTrack != 1
        || (("scrapping" in line) && line.scrapping) || OpexV163Wagons2(line) > 0) continue;
    local vehicle = line.vehicles[0];
    if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetNumWagons(vehicle) < 2) continue;
    local wagonId = AIVehicle.GetWagonEngineType(vehicle, 1);
    if (!AIEngine.IsWagon(wagonId) || !AIEngine.IsBuildable(wagonId)
        || AIEngine.GetCargoType(wagonId) != line.cargo
        || AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle)) > 0
        || AIVehicle.GetLength(vehicle) > OpexV284Limit(line) * 16) continue;
    local homogeneous = true;
    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetEngineType(v) != AIVehicle.GetEngineType(vehicle)
          || AIVehicle.GetNumWagons(v) != AIVehicle.GetNumWagons(vehicle)
          || AIVehicle.GetCapacity(v, line.cargo) != AIVehicle.GetCapacity(vehicle, line.cargo)) homogeneous = false;
      if (!AIVehicle.IsValidVehicle(v)) continue;
      for (local w = 1; w < AIVehicle.GetNumWagons(v); w++)
        if (AIVehicle.GetWagonEngineType(v, w) != wagonId) homogeneous = false;
    }
    if (!homogeneous) continue;
    local station = OpexLineStationId(line, "A");
    if (station < 0) continue;
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    if (!OpexV233LBacklog(line, waiting, AIVehicle.GetCapacity(vehicle, line.cargo))) continue;
    local loco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
    local number = AIVehicle.GetNumWagons(vehicle) - 1;
    local margin = OpexV233LFleetMargin(line, vehicle, true, loco, number);
    if (margin == null) {
      if (DECISION_LOG) OpexV233LLog("REJECT", "line=" + line.lineId + " reason=export_margin");
      continue;
    }
    if (best == null || margin.profit / margin.cost > best.score) best = {
      line = line, vehicle = vehicle, score = margin.profit / margin.cost, margin = margin };
  }
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=growth ops=" + OpexOpsMeasureEnd(mark) + " budget=" + V233L_SLICE_OPS);
  if (best == null) return OpexV284Select(owner, year, true);
  if (!OpexRailVehicleSlotAvailable() || !AIRail.IsRailDepotTile(best.line.depot)) return false;
  V233L_STATE.pending = { lineId = best.line.lineId, vehicle = best.vehicle,
    newVehicle = -1, depot = best.line.depot, phase = "prepare", before = null };
  V233L_STATE.growth[best.line.lineId].nextMonth = OpexV233LMonth() + 3;
  if (DECISION_LOG) OpexV233LLog("GROW_PICK", "line=" + best.line.lineId + " monthly=" + best.margin.monthly
      + " profit=" + best.margin.profit + " cost=" + best.margin.cost);
  return true;
}

/* Transaction de renfort GOOD : identite avant lancement, adoption idempotente
 * et nettoyage des vehicules crees au depot si Save interrompt la construction. */
function OpexV233LContinueGrowth(owner)
{
  if (V233L_STATE.pending == null) return;
  local mark = OpexOpsMeasureBegin();
  OpexV233LGrowthStep(owner);
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=growth_execute ops=" + OpexOpsMeasureEnd(mark));
}

function OpexV233LGrowthStep(owner)
{
  local pending = V233L_STATE.pending;
  if (pending == null) return;
  local line = owner._findLineById(pending.lineId);
  if (pending.phase == "rollback") {
    if (AIVehicle.IsValidVehicle(pending.newVehicle)) OpexV257Discard(owner, pending.newVehicle);
    if (pending.before != null) {
      local vehicles = AIVehicleList();
      for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next())
        if (AIVehicle.IsStoppedInDepot(v) && AIVehicle.GetLocation(v) == pending.depot
            && !OpexWaterContains(pending.before, v)
            && OpexFindLineForVehicle(owner._lines, v) == null) OpexV257Discard(owner, v);
    }
    V233L_STATE.pending = null;
    return;
  }
  if (line == null || !AIVehicle.IsValidVehicle(pending.vehicle)
      || (("scrapping" in line) && line.scrapping)) { pending.phase = "rollback"; return; }
  if (pending.phase == "prepare") {
    if (!OpexRailVehicleSlotAvailable() || !AIRail.IsRailDepotTile(pending.depot)) { V233L_STATE.pending = null; return; }
    local loco = OpexV257Engine(AIVehicle.GetEngineType(pending.vehicle), line.cargo, false);
    local wagons = AIVehicle.GetNumWagons(pending.vehicle) - 1;
    local margin = OpexV233LFleetMargin(line, pending.vehicle, true, loco, wagons);
    if (margin == null || !AIEngine.IsBuildable(loco.id)) { V233L_STATE.pending = null; return; }
    local vehicles = AIVehicleList();
    if (vehicles.Count() > 2048) { V233L_STATE.pending = null; return; }
    pending.before = [];
    for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next())
      if (AIVehicle.GetLocation(v) == pending.depot) pending.before.append(v);
    pending.phase = "building";
    pending.newVehicle = AIVehicle.CloneVehicle(pending.depot, pending.vehicle, true);
    if (!AIVehicle.IsValidVehicle(pending.newVehicle)) { pending.phase = "rollback"; return; }
    pending.phase = "starting";
  }
  if (pending.phase == "starting") {
    if (!AIVehicle.IsValidVehicle(pending.newVehicle)) { pending.phase = "rollback"; return; }
    if (AIVehicle.IsStoppedInDepot(pending.newVehicle) && !AIVehicle.StartStopVehicle(pending.newVehicle)) {
      pending.phase = "rollback"; return;
    }
    if (!OpexWaterContains(line.vehicles, pending.newVehicle)) line.vehicles.append(pending.newVehicle);
    line.trains = line.vehicles.len();
    line.vehCount <- line.trains;
    owner._saveProjection = null;
    owner._saveProjectionMonth = -1;
    if (DECISION_LOG) OpexV233LLog(OpexV233LIs(line) ? "GOOD_GROW" : "INPUT_GROW",
        "line=" + line.lineId + " trains=" + line.trains + " vehicle=" + pending.newVehicle);
    V233L_STATE.pending = null;
  }
}

function OpexV233LLoad(data)
{
  local state = OpexV233LNewState();
  if (data == null || typeof data != "table") return state;
  if (!("month" in data) || typeof data.month != "integer"
      || !("cursor" in data) || typeof data.cursor != "integer" || data.cursor < 0
      || !("rows" in data) || typeof data.rows != "table" || data.rows.len() > V233L_MAX_FACTORIES
      || !("growth" in data) || typeof data.growth != "table" || data.growth.len() > 128
      || !("pending" in data)) return state;
  foreach (id, row in data.rows) {
    if (typeof id != "integer" || typeof row != "table") return state;
    foreach (key in ["month", "tile", "inputLine", "station", "townCursor", "exportLine", "exportMonth"])
      if (!(key in row) || typeof row[key] != "integer") return state;
    foreach (key in ["production", "residual"]) {
      if (!(key in row) || typeof row[key] != "array" || row[key].len() > V233L_WINDOW) return state;
      foreach (value in row[key]) if (typeof value != "integer" || value < 0) return state;
    }
    if (row.production.len() != row.residual.len() || row.townCursor < 0) return state;
  }
  foreach (id, row in data.growth) {
    if (typeof id != "integer" || typeof row != "table") return state;
    foreach (key in ["month", "nextMonth"])
      if (!(key in row) || typeof row[key] != "integer") return state;
    if (!("waiting" in row) || typeof row.waiting != "array" || row.waiting.len() > 3) return state;
    foreach (value in row.waiting) if (typeof value != "integer" || value < 0) return state;
  }
  if (("pending" in data) && data.pending != null) {
    local pending = data.pending;
    if (typeof pending != "table") return state;
    foreach (key in ["lineId", "vehicle", "newVehicle", "depot"])
      if (!(key in pending) || typeof pending[key] != "integer") return state;
    if (!("phase" in pending) || typeof pending.phase != "string"
        || !("before" in pending) || (pending.before != null && typeof pending.before != "array")) return state;
    if (pending.before != null) foreach (v in pending.before) if (typeof v != "integer") return state;
    if (pending.phase != "prepare" && pending.phase != "building"
        && pending.phase != "starting" && pending.phase != "rollback") return state;
    if (pending.phase != "prepare" && pending.before == null) return state;
  }
  return data;
}

function OpexV233LReconcile(owner)
{
  if (V233L_STATE == null || V233L_STATE.pending == null) return;
  local pending = V233L_STATE.pending;
  if (pending.phase == "building") pending.phase = "rollback";
  /* starting est repris par identite : un train deja parti n'est pas recrée. */
}
