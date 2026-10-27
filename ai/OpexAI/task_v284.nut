/* V284 : port du declencheur V270 c71b707, fret existant seulement.
 * Approche non bloquante du depot comme _continueRailExpansion ; assemblage
 * par OpexBuildTrains pour pouvoir redimensionner la locomotive. La rame
 * ancienne n'est jamais vendue avant validation de la nouvelle.
 * Aucune closure, aucun etat flottant sauvegarde, aucun appel au chemin OFF. */

function OpexV284Busy(owner)
{
  return owner._v284State != null && owner._v284State.pending != null;
}

function OpexV284Limit(line)
{
  local length = line.platformLength;
  local limit = AIGameSettings.GetValue("vehicle.max_train_length");
  if (limit < length) length = limit;
  return length;
}

function OpexV284Log(action, fields)
{
  if (DECISION_LOG) OpexDecide("V284", "action=" + action + " " + fields);
}

/* Le modele C41 courant compare les deux compositions sur la meme distance.
 * Garder la vitesse, pas seulement 85 % de la vitesse du passage precedent :
 * aucune erosion multiplicative a chaque ajout. */
function OpexV284Equipment(line, vehicle, wagon, number)
{
  local current = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
  local oldNumber = AIVehicle.GetNumWagons(vehicle) - 1;
  local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
  local speed = OpexRailEffectiveSpeed(current, wagon, oldNumber, distance);
  local railType = AIRail.GetRailType(line.depot);
  local best = null;
  local engines = AIEngineList(AIVehicle.VT_RAIL);
  /* OPCODE-AILIST L6 : eliminer les wagons en natif avant les gardes metier. */
  engines.Valuate(AIEngine.IsWagon);
  engines.KeepValue(0);
  for (local engine = engines.Begin(); !engines.IsEnd(); engine = engines.Next()) {
    if (!AIEngine.IsBuildable(engine) || AIEngine.GetCapacity(engine) > 0 || AIEngine.GetPower(engine) <= 0
        || AIEngine.GetMaxSpeed(engine) <= 0 || AIEngine.GetMaxTractiveEffort(engine) <= 0
        || !AIEngine.CanRunOnRail(engine, railType) || !AIEngine.HasPowerOnRail(engine, railType)) continue;
    local loco = OpexV257Engine(engine, line.cargo, false);
    local nextSpeed = OpexRailEffectiveSpeed(loco, wagon, number, distance);
    if (nextSpeed < speed || loco.speed < current.speed) continue;
    /* A vitesse suffisante, minimiser achat + cinq ans d'entretien. */
    local cost = loco.price + 5 * loco.runningCost;
    if (best == null || cost < best.cost) best = {
      engine = engine, cost = cost, speed = nextSpeed, oldSpeed = speed
    };
  }
  return best;
}

function OpexV284Select(owner, year, v233Input = false)
{
  if (OpexV284Busy(owner)) return true;
  if (!SAVE_FULL_STATE || owner._v257Pending != null || owner._railExpansion != null
      || owner._catalog == null || owner._lines == null) return false;
  if (owner._railSearch != null && owner._railSearch.kind == "upgrade") return false;
  if (!v233Input && (year < OPEX_START_YEAR + V284_RAIL_GROWTH || OpexAvailableCapital() < 1000000)) return false;
  if (owner._v284State == null) owner._v284State = { nextDate = 0, dates = {}, loops = {}, pending = null };
  local state = owner._v284State;
  local date = AIDate.GetCurrentDate();
  if (!v233Input && date < state.nextDate) return false;
  if (!v233Input) state.nextDate = date + 30; // au plus un choix/mois, pas une recherche de fenetre par tick.
  local best = null;
  local v233Mark = v233Input ? OpexOpsMeasureBegin() : null;
  foreach (line in owner._lines) {
    if (v233Input && OpexOpsMeasureEnd(v233Mark) >= V233L_SLICE_OPS) break;
    if (v233Input && !OpexV233LInputTarget(line)) continue;
    if (!("mode" in line) || line.mode != "rail" || !("kind" in line) || line.kind != "freight"
        || !("platformLength" in line) || !("depot" in line) || !("distance" in line)) continue;
    if (line.vehicles.len() != 1 || line.trains != 1 || OpexV163Wagons2(line) > 0) continue;
    if (("doubleTrack" in line) && line.doubleTrack != 0) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("lastProfit" in line) || line.lastProfit <= 0) continue;
    if ((line.lineId in state.dates) && date < state.dates[line.lineId]) continue;
    if (line.depot == null || !AIRail.IsRailDepotTile(line.depot)) continue;
    local vehicle = line.vehicles[0];
    if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL) continue;
    if (owner._vehiclesToRetire != null && (vehicle in owner._vehiclesToRetire)) continue;
    local number = AIVehicle.GetNumWagons(vehicle) - 1;
    if (number < 1 || AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle)) > 0) continue;
    local wagonId = AIVehicle.GetWagonEngineType(vehicle, 1);
    if (!AIEngine.IsWagon(wagonId) || AIEngine.GetCargoType(wagonId) != line.cargo) continue;
    local homogeneous = true;
    for (local index = 1; index <= number; index++)
      if (AIVehicle.GetWagonEngineType(vehicle, index) != wagonId) homogeneous = false;
    if (!homogeneous || !AIEngine.IsBuildable(wagonId)) continue;
    local station = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(station)) continue;
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    local capacity = AIVehicle.GetCapacity(vehicle, line.cargo);
    local wagon = OpexV257Engine(wagonId, line.cargo, true);
    if (capacity <= 0 || wagon.capacity <= 0 || waiting < wagon.capacity) continue;
    local length = OpexV284Limit(line);
    local maxWagons = OpexRailNominalMaxWagons(length);
    /* La longueur mesuree protege aussi les compositions NewGRF plus longues. */
    local atLimit = number >= maxWagons || AIVehicle.GetLength(vehicle) + 8 > length * 16;
    if (v233Input && !OpexV233LBacklog(line, waiting, atLimit ? capacity : wagon.capacity)) continue;
    if (atLimit && (waiting < capacity || !OpexRailVehicleSlotAvailable())) continue;
    if (atLimit && (line.lineId in state.loops)) continue;
    local score = line.distance.tofloat() * waiting / capacity;
    if (best == null || score > best.score) best = {
      line = line, vehicle = vehicle, wagon = wagon, number = number,
      waiting = waiting, capacity = capacity, add = atLimit, score = score
    };
  }
  if (best == null) return false;
  local line = best.line;
  state.dates.rawset(line.lineId, date + 90); // quota de croissance par ligne.
  local number = best.number + (best.add ? 0 : 1);
  local equipment = OpexV284Equipment(line, best.vehicle, best.wagon, number);
  if (equipment == null) {
    state.dates.rawset(line.lineId, date + 365);
    OpexV284Log("skip", "line=" + line.lineId + " reason=traction");
    return false;
  }
  local loopPlan = null;
  if (best.add) {
    local previousType = AIRail.GetCurrentRailType();
    AIRail.SetCurrentRailType(AIRail.GetRailType(line.depot));
    loopPlan = OpexV284LoopPlan(line, AIVehicle.GetLength(best.vehicle));
    AIRail.SetCurrentRailType(previousType);
    if (loopPlan == null) {
      state.dates.rawset(line.lineId, date + 365);
      OpexV284Log("skip", "line=" + line.lineId + " reason=geometry waiting=" + best.waiting);
      return false;
    }
  }
  if (v233Input && !OpexV233LInputMargin(line, best, equipment, number, loopPlan)) return false;
  local oneWay = line.distance.tofloat() / (0.036 * equipment.speed);
  local waitDays = (2 * oneWay).tointeger() + 60;
  if (waitDays < 120) waitDays = 120;
  if (waitDays > 730) waitDays = 730;
  state.pending = {
    lineId = line.lineId, vehicle = best.vehicle, newVehicle = -1,
    engine = equipment.engine, wagon = best.wagon.id, wagons = number,
    oldWagons = best.number, add = best.add, loopPlan = loopPlan,
    speedMilli = (equipment.speed * 1000).tointeger(),
    oldSpeedMilli = (equipment.oldSpeed * 1000).tointeger(),
    phase = "approach", deadline = date + waitDays, before = null,
    depot = line.depot, waiting = best.waiting, cashBefore = 0
  };
  if (v233Input) state.pending.v233Input <- true;
  OpexV284Log("pick", "line=" + line.lineId + " kind=" + (best.add ? "train" : "wagon")
      + " waiting=" + best.waiting + " capacity=" + best.capacity + " distance=" + line.distance
      + " old_wagons=" + best.number + " new_wagons=" + number + " engine=" + equipment.engine
      + " old_engine=" + AIVehicle.GetEngineType(best.vehicle)
      + " speed=" + equipment.oldSpeed.tointeger() + " new_speed=" + equipment.speed.tointeger());
  return true;
}

/* Trace locale de la voie existante, pas un A*. Les tetes de pont/tunnel
 * ne sont pas IsRailTile : elles doivent rester traversables (lecon V271). */
function OpexV284Trace(line)
{
  if (!("platformA" in line) || line.platformA == null) return null;
  local lead = OpexC41RailApproachLead(line.platformA, line.stationA);
  if (lead == null) return null;
  local tiles = [line.stationA, lead];
  local visited = {};
  local previous = line.stationA;
  local current = lead;
  local offsets = [1, -1, AIMap.GetMapSizeX(), -AIMap.GetMapSizeX()];
  for (local step = 0; step < 2000; step++) {
    if (current == line.stationB) return tiles;
    if (current in visited) return null;
    visited.rawset(current, true);
    local next = null;
    if (AITile.GetOwner(current) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) return null;
    if (AIBridge.IsBridgeTile(current) || AITunnel.IsTunnelTile(current)) {
      local other = AIBridge.IsBridgeTile(current) ? AIBridge.GetOtherBridgeEnd(current)
                                                  : AITunnel.GetOtherTunnelEnd(current);
      local span = AIMap.DistanceManhattan(current, other);
      if (span <= 1) return null;
      local direction = (other - current) / span;
      if (AIMap.DistanceManhattan(previous, current) == 1) {
        if (previous != current - direction) return null;
        next = other;
      } else {
        if (previous != other) return null;
        next = current - direction; // sortie dans l'axe, AreTilesConnected exclut les tetes.
        if (!AIMap.IsValidTile(next) || !AIRail.IsRailTile(next)) return null;
      }
    } else {
      foreach (offset in offsets) {
        local tile = current + offset;
        if (!AIMap.IsValidTile(tile) || AIMap.DistanceManhattan(current, tile) != 1 || tile == previous) continue;
        if (AIRail.IsRailDepotTile(tile)) continue;
        if (!AIRail.IsRailTile(tile) && !AIBridge.IsBridgeTile(tile) && !AITunnel.IsTunnelTile(tile)) continue;
        if (AIRail.AreTilesConnected(previous, current, tile)) {
          if (next != null) return null; // pas de reseau partage/aiguillage ambigu.
          next = tile;
        }
      }
    }
    if (next == null) return null;
    previous = current; current = next; tiles.append(current);
  }
  return null;
}

/* Geometrie Opex V202 (70dde94), politique et transaction nouvelles :
 * fenetre L+6, deux branches opposees, pas de modification d'un signal
 * preexistant. Liste exacte des pieces ajoutees pour retour arriere/Load. */
function OpexV284LoopPlan(line, trainLength)
{
  local tiles = OpexV284Trace(line);
  if (tiles == null) return null;
  local length = (trainLength + 15) / 16;
  local width = length + 6;
  if (tiles.len() < width + 6) return null;
  local ownerId = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local middle = (tiles.len() - width) / 2;
  /* 32 fenetres maximum, autour du milieu : pas de scan exhaustif repete. */
  for (local attempt = 0; attempt < 32; attempt++) {
    local start = middle + ((attempt % 2 == 0) ? attempt / 2 : -(attempt + 1) / 2);
    if (start < 2 || start + width >= tiles.len() - 1) continue;
    local direction = tiles[start + 1] - tiles[start];
    if (abs(direction) != 1 && abs(direction) != AIMap.GetMapSizeX()) continue;
    local straight = true;
    for (local k = 0; k < width; k++) {
      local tile = tiles[start + k];
      if (tile != tiles[start] + k * direction || !AIRail.IsRailTile(tile)
          || AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)
          || AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)
          || AITile.GetOwner(tile) != ownerId || OpexTileTrackCount(tile) != 1
          || AITile.GetSlope(tile) != AITile.SLOPE_FLAT
          || (k > 0 && AIMap.DistanceManhattan(tile, tiles[start + k - 1]) != 1)) {
        straight = false; break;
      }
      if (k > 0 && k < width - 1 &&
          (AIRail.GetSignalType(tile, tiles[start + k - 1]) != AIRail.SIGNALTYPE_NONE
           || AIRail.GetSignalType(tile, tiles[start + k + 1]) != AIRail.SIGNALTYPE_NONE)) {
        straight = false; break;
      }
    }
    if (!straight) continue;
    local side = abs(direction) == 1 ? AIMap.GetMapSizeX() : 1;
    foreach (offset in [side, -side]) {
      local clear = true;
      for (local k = 1; k <= length + 4; k++) {
        local tile = tiles[start + k] + offset;
        if (!AIMap.IsValidTile(tile) || AIMap.DistanceManhattan(tile, tiles[start + k]) != 1
            || !AITile.IsBuildable(tile) || AITile.GetSlope(tile) != AITile.SLOPE_FLAT) {
          clear = false; break;
        }
      }
      if (!clear) continue;
      local first = tiles[start + 1];
      local last = tiles[start + length + 4];
      local pieces = [
        { prev = tiles[start], cur = first, next = first + offset },
        { prev = first, cur = first + offset, next = first + offset + direction }
      ];
      for (local k = 2; k <= length + 3; k++) pieces.append({
        prev = tiles[start + k - 1] + offset, cur = tiles[start + k] + offset,
        next = tiles[start + k + 1] + offset
      });
      pieces.append({ prev = last + offset - direction, cur = last + offset, next = last });
      pieces.append({ prev = last + offset, cur = last, next = last + direction });
      foreach (piece in pieces) {
        piece.before <- AIRail.IsRailTile(piece.cur) ? AIRail.GetRailTracks(piece.cur) : 0;
      }
      local signals = [
        { tile = first + direction, front = first, type = AIRail.SIGNALTYPE_PBS_ONEWAY },
        { tile = last - direction, front = last - 2 * direction, type = AIRail.SIGNALTYPE_PBS_ONEWAY },
        { tile = last + offset - direction, front = last + offset, type = AIRail.SIGNALTYPE_PBS_ONEWAY },
        { tile = first + offset + direction, front = first + offset + 2 * direction, type = AIRail.SIGNALTYPE_PBS_ONEWAY },
        { tile = tiles[1], front = tiles[0], type = AIRail.SIGNALTYPE_PBS },
        { tile = tiles[tiles.len()-2], front = tiles[tiles.len()-1], type = AIRail.SIGNALTYPE_PBS }
      ];
      local compatible = true;
      foreach (signal in signals) {
        signal.before <- AIRail.GetSignalType(signal.tile, signal.front);
        if (signal.before != AIRail.SIGNALTYPE_NONE && signal.before != signal.type) compatible = false;
      }
      if (!compatible) continue;
      /* AITestMode ne compose pas les mutations : les signaux sur la future
       * voie laterale sont verifies a la pose, avant tout lancement de train. */
      local possible = true;
      {
        local shield = AIAccounting();
        local test = AITestMode();
        foreach (piece in pieces)
          if (!AIRail.BuildRail(piece.prev, piece.cur, piece.next)) { possible = false; break; }
      }
      if (possible) return { pieces = pieces, signals = signals, started = false, ready = false };
    }
  }
  return null;
}

function OpexV284BuildLoop(plan)
{
  /* La rame a pu mettre des mois a revenir au depot. Ne pas enlever au
   * rollback une piece construite entretemps par un autre chantier. */
  foreach (piece in plan.pieces) {
    local tracks = AIRail.IsRailTile(piece.cur) ? AIRail.GetRailTracks(piece.cur) : 0;
    if (tracks != piece.before || (tracks == 0 && !AITile.IsBuildable(piece.cur))) return false;
  }
  foreach (signal in plan.signals)
    if (AIRail.GetSignalType(signal.tile, signal.front) != signal.before) return false;
  plan.started = true; // ecrit AVANT la premiere commande, pour Save/Load.
  foreach (piece in plan.pieces) {
    if (!AIRail.BuildRail(piece.prev, piece.cur, piece.next)
        || !AIRail.AreTilesConnected(piece.prev, piece.cur, piece.next)) return false;
  }
  foreach (signal in plan.signals) {
    if (signal.before == signal.type) continue;
    if (!AIRail.BuildSignal(signal.tile, signal.front, signal.type)
        || AIRail.GetSignalType(signal.tile, signal.front) != signal.type) return false;
  }
  plan.ready = true;
  return true;
}

function OpexV284RollbackLoop(plan)
{
  if (plan == null || !plan.started) return true;
  local ok = true;
  foreach (signal in plan.signals) {
    if (signal.before == AIRail.SIGNALTYPE_NONE
        && AIRail.GetSignalType(signal.tile, signal.front) == signal.type)
      if (!AIRail.RemoveSignal(signal.tile, signal.front)) ok = false;
  }
  for (local i = plan.pieces.len() - 1; i >= 0; i--) {
    local piece = plan.pieces[i];
    if (AIRail.AreTilesConnected(piece.prev, piece.cur, piece.next))
      if (!AIRail.RemoveRail(piece.prev, piece.cur, piece.next)) ok = false;
  }
  /* Jamais DemolishTile : les deux pieces droites initiales restent intactes. */
  if (ok) { plan.started = false; plan.ready = false; }
  return ok;
}

function OpexV284Adopt(owner, line, pending)
{
  local newVehicle = pending.newVehicle;
  local present = OpexWaterContains(line.vehicles, newVehicle);
  if (pending.add) {
    if (!present) line.vehicles.append(newVehicle);
    owner._v284State.loops.rawset(line.lineId, pending.loopPlan);
  } else {
    for (local index = line.vehicles.len() - 1; index >= 0; index--) {
      if (line.vehicles[index] != pending.vehicle) continue;
      if (present) line.vehicles.remove(index);
      else { line.vehicles[index] = newVehicle; present = true; }
    }
    if (!present) line.vehicles.append(newVehicle);
    line.loco = OpexV257Engine(pending.engine, line.cargo, false);
    line.wagons = pending.wagons;
    line.wagonId <- pending.wagon;
    line.effectiveSpeed = pending.speedMilli / 1000.0;
    line.predOneWayDays <- line.distance.tofloat() / (0.036 * line.effectiveSpeed);
    line.headwayDays <- 2 * line.predOneWayDays;
  }
  line.trains = line.vehicles.len();
  line.vehCount <- line.trains;
  owner._saveProjection = null;
  if (V233_LONG_GOOD > 0 && ("v233Input" in pending) && DECISION_LOG)
    OpexV233LLog("INPUT_GROW", "line=" + line.lineId + " trains=" + line.trains + " wagons=" + line.wagons);
}

function OpexV284Cancel(owner, pending, reason)
{
  OpexV284Log("fail", "line=" + pending.lineId + " reason=" + reason + " error=" + AIError.GetLastError());
  pending.phase = "rollback";
}

function OpexV284Tick(owner)
{
  if (!OpexV284Busy(owner)) return;
  local pending = owner._v284State.pending;
  local line = owner._findLineById(pending.lineId);
  local oldVehicle = pending.vehicle;
  if ((line == null || !AIVehicle.IsValidVehicle(oldVehicle)) && pending.phase != "committed") {
    pending.phase = "rollback";
  } else if (line != null && ("scrapping" in line) && line.scrapping && pending.phase != "committed") {
    pending.phase = "rollback";
  }
  if (pending.phase == "rollback") {
    /* Retrouver aussi les wagons libres d'un builder interrompu par Save. */
    if (pending.before != null) {
      local vehicles = AIVehicleList();
      for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
        if (AIVehicle.GetLocation(vehicle) == pending.depot
            && !OpexWaterContains(pending.before, vehicle)) OpexV257Discard(owner, vehicle);
      }
    }
    if (!OpexV284RollbackLoop(pending.loopPlan)) return;
    pending.phase = "resume";
  }
  if (pending.phase == "resume" || pending.phase == "committed") {
    if (AIVehicle.IsValidVehicle(oldVehicle) && AIVehicle.IsStoppedInDepot(oldVehicle)) {
      if (pending.phase == "committed" && !pending.add) OpexV257Discard(owner, oldVehicle);
      else if (!AIVehicle.StartStopVehicle(oldVehicle)) return;
    }
    owner._v284State.pending = null;
    return;
  }
  if (pending.phase == "approach") {
    if (AIDate.GetCurrentDate() > pending.deadline) {
      OpexV284Log("skip", "line=" + pending.lineId + " reason=approach_timeout");
      owner._v284State.pending = null; return;
    }
    /* Un retour a vide evite de jeter le chargement d'une rame remplacee. */
    if (AIVehicle.GetCargoLoad(oldVehicle, line.cargo) > 0
        || AIMap.DistanceManhattan(AIVehicle.GetLocation(oldVehicle), line.depot) > RAIL_EXPAND_APPROACH_TILES) return;
    if (!AIVehicle.IsStoppedInDepot(oldVehicle) && !AIVehicle.SendVehicleToDepot(oldVehicle)) return;
    pending.phase = "depot";
    pending.deadline = AIDate.GetCurrentDate() + RAIL_EXPAND_TIMEOUT_DAYS;
    return;
  }
  if (!AIVehicle.IsStoppedInDepot(oldVehicle)) {
    if (AIDate.GetCurrentDate() > pending.deadline) {
      AIVehicle.SendVehicleToDepot(oldVehicle); // annule le detournement temporaire.
      OpexV284Log("skip", "line=" + pending.lineId + " reason=depot_timeout");
      owner._v284State.pending = null;
    }
    return;
  }
  pending.depot = AIVehicle.GetLocation(oldVehicle);
  local wagon = OpexV257Engine(pending.wagon, line.cargo, true);
  local loco = OpexV257Engine(pending.engine, line.cargo, false);
  local price = loco.price + pending.wagons * wagon.price;
  local limit = OpexV284Limit(line);
  local station = AIStation.GetStationID(line.stationA);
  local waitingNow = AIStation.IsValidStation(station) ? AIStation.GetCargoWaiting(station, line.cargo) : -1;
  local requiredWaiting = pending.add ? AIVehicle.GetCapacity(oldVehicle, line.cargo) : wagon.capacity;
  if (waitingNow < requiredWaiting || !AIEngine.IsBuildable(pending.engine) || !AIEngine.IsBuildable(pending.wagon)
      || !AIRail.IsRailDepotTile(pending.depot)
      || !AIEngine.HasPowerOnRail(pending.engine, AIRail.GetRailType(pending.depot))
      || pending.wagons > OpexRailNominalMaxWagons(limit)
      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + OpexCashReserve() + 50000) {
    OpexV284Cancel(owner, pending, "depot_recheck"); return;
  }
  pending.cashBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  pending.before = [];
  local vehicles = AIVehicleList();
  for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next())
    if (AIVehicle.GetLocation(vehicle) == pending.depot) pending.before.append(vehicle);
  pending.phase = "building";
  local previousType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(pending.depot));
  if (pending.add && !OpexV284BuildLoop(pending.loopPlan)) {
    AIRail.SetCurrentRailType(previousType);
    OpexV284Cancel(owner, pending, "loop_build"); return;
  }
  local equipment = { wagonByCargo = {} };
  equipment.wagonByCargo.rawset(line.cargo, wagon);
  local built = OpexBuildTrains(equipment, line.cargo, line.kind, pending.depot,
      line.stationA, line.stationB, 1, loco, pending.wagons, limit, false);
  AIRail.SetCurrentRailType(previousType);
  pending.newVehicle = built.vehicles.len() > 0 ? built.vehicles[0] : -1;
  if (built.failed || !AIOrder.CopyOrders(pending.newVehicle, oldVehicle)) {
    OpexV284Cancel(owner, pending, built.failed ? "build" : "orders"); return;
  }
  /* Le train vide reprend a la source ; aucun ordre depot temporaire copie. */
  if (AIOrder.ResolveOrderPosition(pending.newVehicle, AIOrder.ORDER_CURRENT) != 0
      && !AIOrder.SkipToOrder(pending.newVehicle, 0)) {
    OpexV284Cancel(owner, pending, "source_order"); return;
  }
  pending.phase = "starting";
  if (!AIVehicle.StartStopVehicle(pending.newVehicle)) {
    OpexV284Cancel(owner, pending, "start"); return;
  }
  OpexV284Adopt(owner, line, pending);
  pending.phase = "committed";
  OpexV284Log("done", "line=" + line.lineId + " kind=" + (pending.add ? "train" : "wagon")
      + " old_vehicle=" + oldVehicle + " new_vehicle=" + pending.newVehicle
      + " wagons=" + pending.wagons + " trains=" + line.trains
      + " capacity=" + AIVehicle.GetCapacity(pending.newVehicle, line.cargo)
      + " length=" + AIVehicle.GetLength(pending.newVehicle) + " limit=" + limit * 16
      + " speed=" + pending.oldSpeedMilli / 1000 + " new_speed=" + pending.speedMilli / 1000
      + " engine_speed=" + AIEngine.GetMaxSpeed(pending.engine)
      + " gross_cost=" + (pending.cashBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF)));
}

function OpexV284Reconcile(owner)
{
  if (!OpexV284Busy(owner)) return;
  local pending = owner._v284State.pending;
  local line = owner._findLineById(pending.lineId);
  /* Le moteur peut sauvegarder juste apres StartStop et avant la mise a jour
   * de la flotte. L'identite moteur decide, jamais un clonage supplementaire. */
  if (line != null && AIVehicle.IsValidVehicle(pending.newVehicle)
      && !AIVehicle.IsStoppedInDepot(pending.newVehicle)) {
    OpexV284Adopt(owner, line, pending);
    pending.phase = "committed";
  } else if (pending.phase != "approach" && pending.phase != "depot"
             && pending.phase != "resume") {
    pending.phase = "rollback";
  }
  owner._saveProjection = null;
}
