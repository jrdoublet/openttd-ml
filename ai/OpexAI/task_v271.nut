/* V271, 19/10 : tandem fret a la source. OFF : seul le test entier dans
 * _expandRailLines est execute. Transaction persistante, une commande/stage
 * rejouable ; aucune attente bloquante, aucun parcours de carte. */

function OpexV271Log(state, action, reason)
{
  if (!DECISION_LOG) return;
  OpexDecide("V271", "action=" + action + " reason=" + reason + " line=" + state.lineId
      + " cargo=" + state.cargo + " note=" + state.rating + " gain=" + state.gain + " cost=" + state.cost);
}

function OpexAI::_v271TandemSource(year)
{
  if (this._v271Pending != null) { this._v271Continue(); return true; }
  if (!SAVE_FULL_STATE || year < OPEX_START_YEAR + V271_RAIL_TANDEM_SOURCE ||
      year >= OPEX_START_YEAR + 10 || OpexAvailableCapital() < V270_IDLE_CASH_MIN) return false;
  /* 19/10 : quota mensuel (une ligne par an plafonnait a 5 tandems par partie). */
  local quotaKey = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (this._v271Year == quotaKey || this._railExpansion != null || this._v257Pending != null ||
      this._railSearch != null || this._catalog == null) return false;
  local best = null;
  foreach (line in this._lines) {
    if (!("mode" in line) || line.mode != "rail" || line.kind != "freight" ||
        line.trains != 1 || line.vehicles.len() != 1) continue;
    if ((("doubleTrack" in line) && line.doubleTrack != 0) ||
        (("scrapping" in line) && line.scrapping) ||
        (("expandBlocked" in line) && line.expandBlocked) ||
        (("v271Tandem" in line) && line.v271Tandem) ||
        (("v271Failed" in line) && line.v271Failed)) continue;
    if (!("lastProfit" in line) || line.lastProfit <= 0 || line.depot == null ||
        !AIRail.IsRailDepotTile(line.depot) || line.platformA == null || line.platformB == null) continue;
    if (!("lead" in line.platformA) || !("station_exit" in line.platformA)) continue;
    local vehicle = line.vehicles[0];
    if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL) continue;
    if (AIOrder.GetOrderCount(vehicle) != 2 || !AIOrder.IsGotoStationOrder(vehicle, 0) ||
        !AIOrder.IsGotoStationOrder(vehicle, 1) ||
        (AIOrder.GetOrderFlags(vehicle, 0) & AIOrder.OF_FULL_LOAD_ANY) == 0) continue;
    local stationA = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(stationA) || !AIStation.HasCargoRating(stationA, line.cargo)) continue;
    local rating = AIStation.GetCargoRating(stationA, line.cargo);
    /* Inconnu (-1) et zero ne donnent pas un ratio de gain defini. */
    if (rating <= 0 || rating >= 75) continue;
    local gain = line.lastProfit * (min(rating + 20, 85).tofloat() / rating - 1.0);
    if (best == null || gain > best.gain) best = { line = line, vehicle = vehicle, rating = rating, gain = gain };
  }
  this._v271Year = quotaKey;
  local state = { lineId = -1, cargo = -1, rating = -1, gain = 0, cost = 0 };
  if (best == null) { OpexV271Log(state, "skip", "no_candidate"); return false; }
  local line = best.line;
  state.lineId = line.lineId;
  state.cargo = line.cargo;
  state.rating = best.rating;
  state.gain = best.gain.tointeger();
  /* Meme StationID partage avec une autre ligne = topologie non isolee. */
  local stationA = AIStation.GetStationID(line.stationA);
  local stationB = AIStation.GetStationID(line.stationB);
  foreach (other in this._lines) {
    if (other == line || !("mode" in other) || other.mode != "rail") continue;
    if (OpexLineStationId(other, "A") == stationA || OpexLineStationId(other, "B") == stationA ||
        OpexLineStationId(other, "A") == stationB || OpexLineStationId(other, "B") == stationB) {
      OpexV271Log(state, "skip", "shared_station"); return false;
    }
  }
  if (!OpexV271IsolatedRoute(line)) { OpexV271Log(state, "skip", "route_or_signals"); return false; }
  local previousType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(line.depot));
  local geometry = OpexV271PlatformPlan(line);
  AIRail.SetCurrentRailType(previousType);
  if (geometry == null) {
    line.v271Failed <- true;
    this._saveProjection = null;
    OpexV271Log(state, "fail", "no_parallel_connection"); return false;
  }
  /* Cout de marche des moteurs REELS, pas le wagon du catalogue courant. */
  local running = 0;
  local units = AIVehicle.GetNumWagons(best.vehicle);
  for (local unit = 0; unit < units; unit++) {
    running += AIEngine.GetRunningCost(AIVehicle.GetWagonEngineType(best.vehicle, unit));
  }
  AIRail.SetCurrentRailType(AIRail.GetRailType(line.depot));
  local quoted = true;
  {
    local accounting = AIAccounting();
    local testMode = AITestMode();
    if (AIVehicle.CloneVehicle(line.depot, best.vehicle, false) != 0) quoted = false;
    local plan = geometry.platform;
    if (!AIRail.BuildRailStation(plan.anchor, plan.direction, 1, plan.length, stationA)) quoted = false;
    local path = geometry.tiles;
    for (local i = 1; i + 1 < path.len(); i++) {
      if (!AIRail.BuildRail(path[i - 1], path[i], path[i + 1])) quoted = false;
    }
    state.cost = accounting.GetCosts() + 2 * AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_SIGNAL);
  }
  AIRail.SetCurrentRailType(previousType);
  local remaining = OPEX_START_YEAR + 10 - year;
  /* Payback sur gain NET de marche ; strictement avant l'horizon. */
  if (!quoted || state.gain <= running || state.cost >= (state.gain - running) * remaining ||
      OpexAvailableCapital() < state.cost + OpexCashReserve()) {
    OpexV271Log(state, "skip", "running_payback_or_cash"); return false;
  }
  state.vehicle <- best.vehicle;
  state.depot <- line.depot;
  state.newVehicle <- -1;
  state.stationId <- stationA;
  state.platform <- geometry.platform;
  state.tiles <- geometry.tiles;
  state.lead <- geometry.signalTile;
  state.exit <- geometry.signalFront;
  state.phase <- "dispatch";
  state.date <- AIDate.GetCurrentDate();
  state.order <- AIOrder.ResolveOrderPosition(best.vehicle, AIOrder.ORDER_CURRENT);
  state.temporary <- false;
  state.stationIntent <- false;
  state.signalsIntent <- false;
  state.snapshots <- [];
  state.before <- [];
  state.reason <- "";
  state.failureLogged <- false;
  this._v271Pending = state;
  this._saveProjection = null;
  OpexV271Log(state, "pick", "payback");
  return true;
}

/* CloneVehicle est atomique mais Save peut se produire avant son retour.
 * L'inventaire du depot avant la commande retrouve alors sa creation. */
function OpexV271FindNewVehicle(state, depot)
{
  local vehicles = AIVehicleList();
  for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
    if (vehicle == state.vehicle || AIVehicle.GetLocation(vehicle) != depot || OpexWaterContains(state.before, vehicle)) continue;
    return vehicle;
  }
  return -1;
}

/* RemoveOrder peut etre interrompu par Save APRES la commande. Ne retirer
 * que notre ordre depot, jamais l'ordre station qui a repris sa position. */
function OpexV271RemoveTemporary(state)
{
  if (!state.temporary || !AIVehicle.IsValidVehicle(state.vehicle)) return true;
  if (AIOrder.IsValidVehicleOrder(state.vehicle, state.order) &&
      AIOrder.IsGotoDepotOrder(state.vehicle, state.order) &&
      AIOrder.GetOrderDestination(state.vehicle, state.order) == state.depot) {
    if (!AIOrder.RemoveOrder(state.vehicle, state.order)) return false;
  }
  state.temporary = false;
  return true;
}

function OpexAI::_v271Continue()
{
  local state = this._v271Pending;
  if (state == null) return;
  local line = this._findLineById(state.lineId);
  if (line == null && state.phase != "commit") {
    state.reason = "line_lost"; state.phase = "rollback";
  }
  this._saveProjection = null; // marqueurs et identites exacts, y compris apres Load.
  if (state.phase == "commit") {
    if (line == null) { OpexV271Log(state, "fail", "committed_line_lost"); this._v271Pending = null; return; }
    /* Une fois un train lance, ne JAMAIS retirer l'infrastructure sous lui.
     * Rejouer le commit apres Load est sans effet sur les trains deja partis. */
    /* Squirrel d'OpenTTD : pas de array.find (plantage du smoke du 19/10). */
    if (!OpexWaterContains(line.vehicles, state.newVehicle)) line.vehicles.append(state.newVehicle);
    line.trains = line.vehicles.len();
    line.vehCount <- line.trains;
    line.lastLiveVehicles <- line.trains;
    line.v271Tandem <- true;
    line.platformA2 <- state.platform;
    line.stationA2 <- state.platform.station_exit;
    local started = true;
    foreach (vehicle in [state.vehicle, state.newVehicle]) {
      if (!AIVehicle.IsValidVehicle(vehicle)) continue;
      if (AIVehicle.IsStoppedInDepot(vehicle)) {
        /* Les deux mises en service visent A, pas deux directions opposees
         * depuis un depot au milieu de la ligne. Le moteur reserve la sortie. */
        local current = AIOrder.ResolveOrderPosition(vehicle, AIOrder.ORDER_CURRENT);
        if (current != 0 && !AIOrder.SkipToOrder(vehicle, 0)) { started = false; continue; }
        if (!AIVehicle.StartStopVehicle(vehicle)) started = false;
      }
    }
    if (started) {
      OpexV271Log(state, "done", "tandem");
      this._v271Pending = null;
    }
    return;
  }
  if (!AIVehicle.IsValidVehicle(state.vehicle)) {
    state.reason = "template_lost"; state.phase = "rollback";
  }
  if (AIDate.GetCurrentDate() - state.date > 730 && state.phase != "rollback") {
    state.reason = "timeout"; state.phase = "rollback";
  }
  if (state.phase == "rollback") {
    if (!state.failureLogged) { OpexV271Log(state, "fail", state.reason); state.failureLogged = true; }
    if (line != null) line.v271Failed <- true;
    if (state.newVehicle < 0 && state.before.len() > 0)
      state.newVehicle = OpexV271FindNewVehicle(state, state.depot);
    /* Tout nouveau vehicule reste arrete au depot avant commit. */
    if (state.newVehicle >= 0 && AIVehicle.IsValidVehicle(state.newVehicle) && !AIVehicle.SellVehicle(state.newVehicle)) return;
    local ok = true;
    if (state.signalsIntent) {
      foreach (pair in [[state.lead, state.exit], [state.platform.lead, state.platform.station_exit]]) {
        if (AIRail.GetSignalType(pair[0], pair[1]) != AIRail.SIGNALTYPE_NONE &&
            !AIRail.RemoveSignal(pair[0], pair[1])) ok = false;
      }
    }
    if (!OpexV271RestoreTracks(state.snapshots)) ok = false;
    if (state.stationIntent) {
      for (local i = 0; i < state.platform.length; i++) {
        local tile = state.platform.anchor + i * state.platform.step;
        if (AIRail.IsRailStationTile(tile) && AIStation.GetStationID(tile) == state.stationId &&
            !AIRail.RemoveRailStationTileRectangle(tile, tile, false)) ok = false;
      }
    }
    if (!OpexV271RemoveTemporary(state)) ok = false;
    if (!ok) return;
    if (AIVehicle.IsValidVehicle(state.vehicle) && AIVehicle.IsStoppedInDepot(state.vehicle) &&
        !AIVehicle.StartStopVehicle(state.vehicle)) return;
    this._v271Pending = null;
    return;
  }
  if (state.phase == "dispatch") {
    if (AIVehicle.IsStoppedInDepot(state.vehicle)) { state.phase = "station"; return; }
    /* L'intention precede la commande, pour un Save pendant InsertOrder. */
    state.phase = "dispatch_intent";
    return;
  }
  if (state.phase == "dispatch_intent") {
    state.temporary = true;
    if (!AIOrder.IsGotoDepotOrder(state.vehicle, state.order)) {
      if (!AIOrder.InsertOrder(state.vehicle, state.order, line.depot, AIOrder.OF_STOP_IN_DEPOT)) {
        state.reason = "depot_order"; state.phase = "rollback"; return;
      }
    }
    state.temporary = true;
    local current = AIOrder.ResolveOrderPosition(state.vehicle, AIOrder.ORDER_CURRENT);
    if (current != state.order && !AIOrder.SkipToOrder(state.vehicle, state.order)) {
      state.reason = "depot_skip"; state.phase = "rollback"; return;
    }
    state.phase = "wait";
    return;
  }
  if (state.phase == "wait") {
    if (AIVehicle.IsStoppedInDepot(state.vehicle)) state.phase = "station";
    return;
  }
  if (!AIVehicle.IsStoppedInDepot(state.vehicle) || AIVehicle.GetLocation(state.vehicle) != line.depot) {
    state.reason = "wrong_depot"; state.phase = "rollback"; return;
  }
  local previousType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(line.depot));
  if (state.phase == "station") {
    /* Revalidation avant toute mutation : le premier train ne circule plus. */
    local clear = true;
    for (local i = 0; i < state.platform.length; i++) {
      if (!AITile.IsBuildable(state.platform.anchor + i * state.platform.step)) clear = false;
    }
    for (local i = 1; i + 2 < state.tiles.len(); i++) {
      if (!AITile.IsBuildable(state.tiles[i])) clear = false;
    }
    if (!clear || !OpexV271IsolatedRoute(line)) {
      state.reason = "route_changed"; state.phase = "rollback";
    } else {
      state.phase = "station_intent";
      state.stationIntent = true;
      OpexV271Log(state, "build", "depot_stopped");
    }
  } else if (state.phase == "station_intent") {
    local plan = state.platform;
    if (!AIRail.IsRailStationTile(plan.anchor) &&
        !AIRail.BuildRailStation(plan.anchor, plan.direction, 1, plan.length, state.stationId)) {
      state.reason = "station"; state.phase = "rollback";
    } else if (AIStation.GetStationID(plan.anchor) != state.stationId) {
      state.reason = "station_join"; state.phase = "rollback";
    } else {
      local touched = [state.lead];
      for (local i = 1; i + 1 < state.tiles.len(); i++) touched.append(state.tiles[i]);
      foreach (tile in touched) {
        state.snapshots.append({ tile = tile, tracks = AIRail.IsRailTile(tile) ? AIRail.GetRailTracks(tile) : 0 });
      }
      state.phase = "track";
    }
  } else if (state.phase == "track") {
    local connected = true;
    for (local i = 1; i + 1 < state.tiles.len(); i++) {
      local path = state.tiles;
      if (!AIRail.AreTilesConnected(path[i - 1], path[i], path[i + 1]) &&
          !AIRail.BuildRail(path[i - 1], path[i], path[i + 1])) connected = false;
      if (!AIRail.AreTilesConnected(path[i - 1], path[i], path[i + 1])) connected = false;
    }
    if (!connected) { state.reason = "track"; state.phase = "rollback"; }
    else { state.signalsIntent = true; state.phase = "signals"; }
  } else if (state.phase == "signals") {
    /* front = voisin cote QUAI : _possible_trackdirs dans script_rail.cpp
     * donne le trackdir d'un train venant de ce voisin, donc QUITTANT A.
     * Ce helper strict ne possede aucun repli vers un signal de bloc. */
    local a = OpexC41BuildPbsAtApproach({ lead = state.lead, station_exit = state.exit });
    local a2 = OpexC41BuildPbsAtApproach(state.platform);
    if (a < 1 || a2 < 1 || AIRail.GetSignalType(state.lead, state.exit) != AIRail.SIGNALTYPE_PBS ||
        AIRail.GetSignalType(state.platform.lead, state.platform.station_exit) != AIRail.SIGNALTYPE_PBS) {
      state.reason = "signals"; state.phase = "rollback";
    } else {
      if (state.temporary) {
        if (!OpexV271RemoveTemporary(state)) {
          AIRail.SetCurrentRailType(previousType); return;
        }
      }
      local vehicles = AIVehicleList();
      for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
        if (AIVehicle.GetLocation(vehicle) == line.depot) state.before.append(vehicle);
      }
      state.phase = "clone_intent";
      OpexV271Log(state, "build", "infrastructure_ready");
    }
  } else if (state.phase == "clone_intent") {
    state.newVehicle = OpexV271FindNewVehicle(state, line.depot);
    if (state.newVehicle < 0) state.newVehicle = AIVehicle.CloneVehicle(line.depot, state.vehicle, false);
    if (!AIVehicle.IsValidVehicle(state.newVehicle)) {
      state.reason = "clone"; state.phase = "rollback";
    } else if (AIVehicle.GetLength(state.newVehicle) > state.platform.length * 16) {
      state.reason = "length"; state.phase = "rollback";
    } else {
      /* Premier ordre = A, meme si l'ancien train etait en route vers B.
       * Aucun partage d'ordres temporaire avec le train historique. */
      local current = AIOrder.ResolveOrderPosition(state.newVehicle, AIOrder.ORDER_CURRENT);
      if (current != 0 && !AIOrder.SkipToOrder(state.newVehicle, 0)) {
        state.reason = "source_order"; state.phase = "rollback";
      } else state.phase = "commit";
    }
  }
  AIRail.SetCurrentRailType(previousType);
}
