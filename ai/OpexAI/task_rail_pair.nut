/* RAIL-PAIR : transaction V271b recuperee du commit 9403c73.
 * Une seule rame circule sur la voie unique a la fois ; le second quai source
 * permet a l'autre rame de charger. Une gare source peut avoir des quais de
 * lignes soeurs ; chaque ligne conserve un quai et une voie propres. */

function OpexV271Log(state, action, reason)
{
  if (!DECISION_LOG) return;
  OpexDecide("RAIL_PAIR", "action=" + action + " reason=" + reason
      + " phase=" + (("phase" in state) ? state.phase : "selection") + " line=" + state.lineId
      + " cargo=" + state.cargo + " note=" + state.rating + " waiting="
      + (("waiting" in state) ? state.waiting : -1) + " capacity="
      + (("capacity" in state) ? state.capacity : -1)
      + " last_waiting=" + (("lastWaiting" in state) ? state.lastWaiting : -1)
      + " station_trains=" + (("stationTrains" in state) ? state.stationTrains : -1)
      + " station_capacity=" + (("stationCapacity" in state) ? state.stationCapacity : -1)
      + " threshold=" + (("threshold" in state) ? state.threshold : -1)
      + " fill_pct=" + (("fillPct" in state) ? state.fillPct : -1)
      + " eligible=" + (("eligible" in state) ? state.eligible : -1)
      + " near_reason=" + (("nearReason" in state) ? state.nearReason : "-")
      + " gain=" + state.gain + " cost=" + state.cost);
}

/* Sous RAIL-PAIR seulement, suivre mensuellement la source apres mise en service.
 * La note est fournie en pourcentage par NoAI ; les capacites sont celles des rames reelles. */
function OpexRailPairReview(owner)
{
  if (!DECISION_LOG || owner._lines == null) return;
  local month = AIDate.GetYear(AIDate.GetCurrentDate()) * 12
      + AIDate.GetMonth(AIDate.GetCurrentDate());
  foreach (line in owner._lines) {
    if (!("v271Tandem" in line) || !line.v271Tandem
        || !("stationA" in line) || !("cargo" in line)) continue;
    if (("railPairLastMonth" in line) && line.railPairLastMonth == month) continue;
    line.railPairLastMonth <- month;
    local station = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(station)) continue;
    local rating = AIStation.HasCargoRating(station, line.cargo)
        ? AIStation.GetCargoRating(station, line.cargo) : -1;
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    local capacity = 0;
    foreach (vehicle in line.vehicles)
      if (AIVehicle.IsValidVehicle(vehicle)) capacity += AIVehicle.GetCapacity(vehicle, line.cargo);
    local stationFleet = OpexRailPairStationFleet(station, line.cargo);
    OpexDecide("RAIL_PAIR", "action=review line=" + line.lineId
        + " rating_before=" + (("railPairBeforeRating" in line) ? line.railPairBeforeRating : -1)
        + " rating_after=" + rating + " waiting=" + waiting + " capacity_total=" + capacity
        + " trains=" + line.vehicles.len() + " station_trains=" + stationFleet.trains
        + " station_capacity=" + stationFleet.capacity + " profit="
        + (("lastProfit" in line) ? line.lastProfit : -1));
  }
}

/* Nombre de rames desservant effectivement la gare A et capacite pour ce cargo.
 * La liste de station couvre aussi les soeurs (non presentes dans line.vehicles).
 * Pour un cargo different, la rame compte pour l'occupation mais pas le stock. */
function OpexRailPairStationFleet(station, cargo)
{
  local result = { trains = 0, capacity = 0 };
  local vehicles = AIVehicleList_Station(station);
  for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
    if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL) continue;
    result.trains++;
    result.capacity += max(0, AIVehicle.GetCapacity(vehicle, cargo));
  }
  return result;
}

/* Deux lignes peuvent partager la gare SOURCE et le depot, si leurs quais et
 * leurs sorties A sont physiquement distincts. Une gare B partagee, ou un depot
 * partage avec une ligne d'une AUTRE source, ne prouve pas l'isolement. Refaire
 * cette verification au depot et au clonage car RAIL-SIBLING peut construire
 * une ligne pendant le trajet de la rame historique. */
function OpexRailPairStationsFree(owner, line)
{
  if (line == null || !("stationA" in line) || !("stationB" in line)
      || !("depot" in line) || !("platformA" in line) || line.platformA == null) return false;
  local a = AIStation.GetStationID(line.stationA);
  local b = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(a) || !AIStation.IsValidStation(b)) return false;
  foreach (other in owner._lines) {
    if (other == line || !("mode" in other) || other.mode != "rail") continue;
    local otherA = OpexLineStationId(other, "A");
    if (OpexLineStationId(other, "A") == b || OpexLineStationId(other, "B") == b
        || OpexLineStationId(other, "B") == a) return false;
    if (otherA != a) {
      if ((("depot" in other) && other.depot == line.depot)
          || (("depot2" in other) && other.depot2 == line.depot)) return false;
      continue;
    }
    if (!("platformA" in other) || other.platformA == null) return false;
    local own = line.platformA;
    local sibling = other.platformA;
    if (!("anchor" in own) || !("step" in own) || !("length" in own)
        || !("anchor" in sibling) || !("step" in sibling) || !("length" in sibling)
        || !("lead" in own) || !("lead" in sibling)) return false;
    if (own.lead == sibling.lead) return false;
    if (!("station_exit" in own) || !("station_exit" in sibling)
        || own.station_exit == sibling.station_exit) return false;
    for (local i = 0; i < own.length; i++) {
      local tile = own.anchor + i * own.step;
      for (local j = 0; j < sibling.length; j++)
        if (tile == sibling.anchor + j * sibling.step) return false;
    }
  }
  return true;
}

function OpexRailPairFreightOrders(vehicle)
{
  return AIVehicle.IsValidVehicle(vehicle)
      && AIVehicle.GetVehicleType(vehicle) == AIVehicle.VT_RAIL
      && AIOrder.GetOrderCount(vehicle) == 2
      && AIOrder.IsGotoStationOrder(vehicle, 0)
      && AIOrder.IsGotoStationOrder(vehicle, 1)
      && (AIOrder.GetOrderFlags(vehicle, 0) & AIOrder.OF_FULL_LOAD_ANY) != 0;
}

function OpexAI::_v271TandemSource(year)
{
  if (this._v271Pending != null) { this._v271Continue(); return true; }
  if (!SAVE_FULL_STATE || year < OPEX_START_YEAR || year >= OPEX_START_YEAR + 10) return false;
  /* 19/10 : quota mensuel (une ligne par an plafonnait a 5 tandems par partie). */
  local quotaKey = year * 12 + AIDate.GetMonth(AIDate.GetCurrentDate());
  if (this._v271Year == quotaKey || this._railExpansion != null || this._v257Pending != null ||
      this._railSearch != null || this._catalog == null || !OpexRailVehicleSlotAvailable()
      || OpexV284Busy(this)) return false;
  local best = null;
  local near = null;
  local eligible = 0;
  foreach (line in this._lines) {
    if (!("mode" in line) || line.mode != "rail" || line.kind != "freight" ||
        line.trains != 1 || line.vehicles.len() != 1) continue;
    if ((("doubleTrack" in line) && line.doubleTrack != 0) ||
        (("scrapping" in line) && line.scrapping) ||
        (("expandBlocked" in line) && line.expandBlocked) ||
        (("v271Tandem" in line) && line.v271Tandem) ||
        (("v271Failed" in line) && line.v271Failed) ||
        (("v271SkipYear" in line) && line.v271SkipYear == year)) continue;
    local profitable = ("lastProfit" in line) && line.lastProfit > 0;
    local mature = ("buildDate" in line) && AIDate.GetCurrentDate() - line.buildDate >= 180;
    if ((!profitable && !mature) || line.depot == null ||
        !AIRail.IsRailDepotTile(line.depot) || line.platformA == null || line.platformB == null) continue;
    if (!("lead" in line.platformA) || !("station_exit" in line.platformA)
        || !("lead" in line.platformB) || !("station_exit" in line.platformB)) continue;
    local vehicle = line.vehicles[0];
    if (!OpexRailPairFreightOrders(vehicle)) continue;
    local stationA = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(stationA) || !AIStation.HasCargoRating(stationA, line.cargo)) continue;
    local rating = AIStation.GetCargoRating(stationA, line.cargo);
    local waiting = AIStation.GetCargoWaiting(stationA, line.cargo);
    local capacity = AIVehicle.GetCapacity(vehicle, line.cargo);
    if (capacity <= 0 || rating < 0 || waiting < 0) continue;
    local fleet = OpexRailPairStationFleet(stationA, line.cargo);
    local threshold = max(capacity, fleet.capacity);
    eligible++;
    if (waiting < threshold && rating >= 60) {
      /* Trace la ligne la plus proche d'une rame complete, en distinguant
       * le stock instantane de lastWaitingA (releve au dernier rapport). */
      if (near == null || waiting.tofloat() / threshold > near.waiting.tofloat() / near.threshold)
        near = { line = line, rating = rating, waiting = waiting, capacity = capacity,
            lastWaiting = ("lastWaitingA" in line) ? line.lastWaitingA : -1,
            stationTrains = fleet.trains, stationCapacity = fleet.capacity,
            threshold = threshold };
      continue;
    }
    /* Plancher 30 % pour eviter le devis artificiel de V271 a 5 %.
     * Une rame complete en attente donne aussi un gain de rotation marginal. */
    local gain = max(1, (("lastProfit" in line) ? line.lastProfit : 0))
        * (min(rating + 20, 85).tofloat() / max(30, rating) - 1.0);
    if (waiting >= threshold) gain += max(0, (("lastProfit" in line) ? line.lastProfit : 0)) * 0.15;
    if (best == null || gain > best.gain) best = { line = line, vehicle = vehicle,
        rating = rating, waiting = waiting, capacity = capacity, gain = gain,
        stationTrains = fleet.trains, stationCapacity = fleet.capacity, threshold = threshold };
  }
  this._v271Year = quotaKey;
  local state = { lineId = -1, cargo = -1, rating = -1, gain = 0, cost = 0 };
  state.eligible <- eligible;
  if (best == null) {
    if (near != null) {
      state.lineId = near.line.lineId;
      state.cargo = near.line.cargo;
      state.rating = near.rating;
      state.waiting <- near.waiting;
      state.capacity <- near.capacity;
      state.lastWaiting <- near.lastWaiting;
      state.stationTrains <- near.stationTrains;
      state.stationCapacity <- near.stationCapacity;
      state.threshold <- near.threshold;
      state.fillPct <- (100 * near.waiting / max(1, near.threshold)).tointeger();
      state.nearReason <- "waiting_lt_station_capacity_and_rating_gte_60";
    } else state.nearReason <- "no_eligible_single_train_freight";
    OpexV271Log(state, "skip", "no_candidate"); return false;
  }
  local line = best.line;
  state.lineId = line.lineId;
  state.cargo = line.cargo;
  state.rating = best.rating;
  state.waiting <- best.waiting;
  state.capacity <- best.capacity;
  state.lastWaiting <- ("lastWaitingA" in line) ? line.lastWaitingA : -1;
  state.stationTrains <- best.stationTrains;
  state.stationCapacity <- best.stationCapacity;
  state.threshold <- best.threshold;
  state.fillPct <- (100 * best.waiting / max(1, best.threshold)).tointeger();
  state.gain = best.gain.tointeger();
  /* La gare A commune est admise avec quais et sorties distincts, depot partage possible. */
  local stationA = AIStation.GetStationID(line.stationA);
  if (!OpexRailPairStationsFree(this, line)) {
    line.v271Failed <- true; this._saveProjection = null;
    OpexV271Log(state, "skip", "shared_station_or_depot"); return false;
  }
  /* 19/10 : marquer la ligne, sinon la meilleure ligne refusee bloque toutes les autres chaque mois. */
  local routeIssue = OpexV271RouteIssue(line);
  if (routeIssue != "") {
    line.v271Failed <- true; this._saveProjection = null;
    if (DECISION_LOG && V271_LAST_TRACE_DETAIL != "")
      OpexDecide("RAIL_PAIR_TRACE", "line=" + line.lineId + " issue=" + routeIssue
          + " " + V271_LAST_TRACE_DETAIL);
    OpexV271Log(state, "skip", "route_" + routeIssue); return false;
  }
  local previousType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(line.depot));
  local geometry = OpexV271PlatformPlan(line);
  AIRail.SetCurrentRailType(previousType);
  if (geometry == null) {
    line.v271Failed <- true;
    this._saveProjection = null;
    OpexV271Log(state, "fail", "geometry_" + V271_LAST_GEOMETRY_ISSUE); return false;
  }
  /* Cout de marche des moteurs REELS, pas le wagon du catalogue courant. */
  local running = 0;
  local units = AIVehicle.GetNumWagons(best.vehicle);
  for (local unit = 0; unit < units; unit++) {
    running += AIEngine.GetRunningCost(AIVehicle.GetWagonEngineType(best.vehicle, unit));
  }
  AIRail.SetCurrentRailType(AIRail.GetRailType(line.depot));
  local quoted = true;
  local quoteReason = "";
  {
    local accounting = AIAccounting();
    local testMode = AITestMode();
    if (AIVehicle.CloneVehicle(line.depot, best.vehicle, false) != 0) {
      quoted = false; quoteReason = "quote_clone";
    }
    /* Le PBS en B doit deja etre possible sur une voie droite simple. Le
     * detecter avant d'arreter le train historique evite un mois de perte. */
    if (!AIRail.IsRailTile(line.platformB.lead)
        || OpexTileTrackCount(line.platformB.lead) != 1
        || AIRail.GetSignalType(line.platformB.lead, line.platformB.station_exit) != AIRail.SIGNALTYPE_NONE
        || !AIRail.BuildSignal(line.platformB.lead, line.platformB.station_exit,
                              AIRail.SIGNALTYPE_PBS)) {
      quoted = false; if (quoteReason == "") quoteReason = "quote_b_signal";
    }
    local plan = geometry.platform;
    if (!AIRail.BuildRailStation(plan.anchor, plan.direction, 1, plan.length, stationA)) {
      quoted = false; if (quoteReason == "") quoteReason = "quote_station";
    }
    local path = geometry.tiles;
    for (local i = 1; i + 1 < path.len(); i++) {
      if (!AIRail.BuildRail(path[i - 1], path[i], path[i + 1])) {
        quoted = false; if (quoteReason == "") quoteReason = "quote_track";
      }
    }
    /* Le signal B est deja compris dans le sondage ci-dessus. */
    state.cost = accounting.GetCosts() + 2 * AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_SIGNAL);
  }
  AIRail.SetCurrentRailType(previousType);
  local remaining = OPEX_START_YEAR + 10 - year;
  /* Payback sur gain NET de marche ; strictement avant l'horizon. */
  if (!quoted) {
    line.v271Failed <- true;
    this._saveProjection = null;
    OpexV271Log(state, "fail", quoteReason);
    return false;
  }
  /* La reserve statique a ete retiree du moteur : OpexAvailableCapital()
   * est la caisse mobilisable, sans reserve supplementaire implicite. */
  if (state.gain <= running || state.cost >= (state.gain - running) * remaining ||
      OpexAvailableCapital() < state.cost) {
    line.v271SkipYear <- year;
    OpexV271Log(state, "skip", "running_payback_or_cash"); return false;
  }
  if (FLEET_ARB && !OpexFleetRequest(line, "rail", "add_vehicle", state.cost,
      state.gain - running, "RAIL_PAIR")) return false;
  state.vehicle <- best.vehicle;
  state.depot <- line.depot;
  state.newVehicle <- -1;
  state.stationId <- stationA;
  state.platform <- geometry.platform;
  state.tiles <- geometry.tiles;
  state.lead <- geometry.signalTile;
  state.exit <- geometry.signalFront;
  state.destLead <- line.platformB.lead;
  state.destExit <- line.platformB.station_exit;
  /* Capturer les signaux preexistants AVANT toute pose. La sortie A2 est
   * une voie neuve et ne peut donc porter de signal historique. */
  state.signalBefore <- [
      { tile = state.lead, front = state.exit,
        original = AIRail.GetSignalType(state.lead, state.exit), built = false },
      { tile = state.platform.lead, front = state.platform.station_exit,
        original = AIRail.SIGNALTYPE_NONE, built = false },
      { tile = state.destLead, front = state.destExit,
        original = AIRail.GetSignalType(state.destLead, state.destExit), built = false }
  ];
  state.phase <- "dispatch";
  state.date <- AIDate.GetCurrentDate();
  state.order <- AIOrder.ResolveOrderPosition(best.vehicle, AIOrder.ORDER_CURRENT);
  if (!AIOrder.IsValidVehicleOrder(best.vehicle, state.order)) {
    OpexV271Log(state, "fail", "source_order_invalid");
    return false;
  }
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

/* Identifier le clone strictement : Save peut se produire entre CloneVehicle
 * et l'enregistrement de son identifiant. Un vehicule d'une autre ligne apparu
 * au depot dans cet intervalle ne doit JAMAIS etre vendu par le rollback. */
function OpexV271MatchesClone(state, vehicle)
{
  if (!AIVehicle.IsValidVehicle(vehicle) || !AIVehicle.IsValidVehicle(state.vehicle)
      || vehicle == state.vehicle || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL
      || AIVehicle.GetEngineType(vehicle) != AIVehicle.GetEngineType(state.vehicle)
      || AIVehicle.GetNumWagons(vehicle) != AIVehicle.GetNumWagons(state.vehicle)
      || !OpexRailPairFreightOrders(vehicle) || !OpexRailPairFreightOrders(state.vehicle)) return false;
  for (local wagon = 0; wagon < AIVehicle.GetNumWagons(vehicle); wagon++)
    if (AIVehicle.GetWagonEngineType(vehicle, wagon)
        != AIVehicle.GetWagonEngineType(state.vehicle, wagon)) return false;
  for (local i = 0; i < 2; i++) {
    if (AIOrder.GetOrderDestination(vehicle, i) != AIOrder.GetOrderDestination(state.vehicle, i)
        || AIOrder.GetOrderFlags(vehicle, i) != AIOrder.GetOrderFlags(state.vehicle, i)) return false;
  }
  return true;
}

function OpexV271FindNewVehicle(owner, state, depot)
{
  if (state.before.len() == 0) return -1;
  local found = -1;
  local vehicles = AIVehicleList();
  for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
    if (AIVehicle.GetLocation(vehicle) != depot || OpexWaterContains(state.before, vehicle)
        || !OpexV271MatchesClone(state, vehicle)) continue;
    local claimed = false;
    foreach (line in owner._lines) {
      if (!("vehicles" in line)) continue;
      if (OpexWaterContains(line.vehicles, vehicle)) claimed = true;
    }
    if (claimed) continue;
    if (found >= 0) return -2; // ambiguite : ne choisir aucun vehicule.
    found = vehicle;
  }
  return found;
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
    if (OpexWaterContains(state.before, state.newVehicle)
        || !OpexV271MatchesClone(state, state.newVehicle)
        || !OpexRailPairFreightOrders(state.vehicle)) {
      state.reason = "clone_invalid_at_commit";
      if (!("v271Tandem" in line) || !line.v271Tandem) {
        state.phase = "rollback";
      } else {
        line.v271Failed <- true;
        local survivors = [];
        foreach (vehicle in line.vehicles)
          if (AIVehicle.IsValidVehicle(vehicle)) survivors.append(vehicle);
        line.vehicles = survivors;
        line.trains = survivors.len();
        line.vehCount <- line.trains;
        line.lastLiveVehicles <- line.trains;
        OpexV271Log(state, "fail", state.reason);
        this._v271Pending = null; // materiel deja lance : ne retirer aucun rail.
      }
      return;
    }
    /* Une fois un train lance, ne JAMAIS retirer l'infrastructure sous lui.
     * Rejouer le commit apres Load est sans effet sur les trains deja partis. */
    /* Squirrel d'OpenTTD : pas de array.find (plantage du smoke du 19/10). */
    if (!OpexWaterContains(line.vehicles, state.newVehicle)) line.vehicles.append(state.newVehicle);
    line.trains = line.vehicles.len();
    line.vehCount <- line.trains;
    line.lastLiveVehicles <- line.trains;
    line.v271Tandem <- true;
    line.railPairBeforeRating <- state.rating;
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
      state.newVehicle = OpexV271FindNewVehicle(this, state, state.depot);
    /* Ne vendre qu'un clone reconnu, encore arrete a NOTRE depot. Un ID
     * recycle ou une nouvelle rame etrangere ne donne jamais droit a la vente. */
    if (state.newVehicle >= 0 && AIVehicle.IsValidVehicle(state.newVehicle)) {
      if (!OpexWaterContains(state.before, state.newVehicle)
          && OpexV271MatchesClone(state, state.newVehicle)) {
        if (AIVehicle.GetLocation(state.newVehicle) != state.depot
            || !AIVehicle.IsStoppedInDepot(state.newVehicle)) return;
        local claimed = false;
        foreach (other in this._lines)
          if (("vehicles" in other) && OpexWaterContains(other.vehicles, state.newVehicle)) claimed = true;
        if (!claimed && !AIVehicle.SellVehicle(state.newVehicle)) return;
      }
      state.newVehicle = -1;
    }
    local ok = true;
    if (state.signalsIntent) {
      foreach (snapshot in state.signalBefore) {
        /* Retirer uniquement un PBS pose pendant notre transaction ; ne
         * jamais effacer un signal d'une autre ligne ou d'un autre type. */
        if (snapshot.original == AIRail.SIGNALTYPE_NONE &&
            ("built" in snapshot) && snapshot.built &&
            AIRail.GetSignalType(snapshot.tile, snapshot.front) == AIRail.SIGNALTYPE_PBS &&
            !AIRail.RemoveSignal(snapshot.tile, snapshot.front)) ok = false;
      }
    }
    if (!OpexV271RestoreTracks(state.snapshots)) ok = false;
    if (state.stationIntent) {
      for (local i = 0; i < state.platform.length; i++) {
        /* Une tuile sans preuve de vacance avant construction est protegee. */
        if (!("stationBefore" in state) || i >= state.stationBefore.len()
            || state.stationBefore[i]) continue;
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
    if (!AIOrder.IsValidVehicleOrder(state.vehicle, state.order)) {
      state.reason = "depot_order_invalid"; state.phase = "rollback"; return;
    }
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
    /* V271b : entre devis et arret au depot, conserver les deux supports
     * primaires droits et simples, ainsi que l'orientation vers B du merge. */
    local merge = state.tiles[state.tiles.len() - 2];
    local next = state.tiles[state.tiles.len() - 1];
    if (OpexTileTrackCount(state.lead) != 1 || OpexTileTrackCount(merge) != 1 ||
        !AIRail.AreTilesConnected(state.exit, state.lead, state.lead + (state.lead - state.exit)) ||
        !AIRail.AreTilesConnected(merge - (next - merge), merge, next)) clear = false;
    if (!clear || !OpexRailPairStationsFree(this, line) || !OpexV271IsolatedRoute(line)) {
      state.reason = "route_changed"; state.phase = "rollback";
    } else {
      state.phase = "station_intent";
      state.stationBefore <- [];
      for (local i = 0; i < state.platform.length; i++)
        state.stationBefore.append(AIRail.IsRailStationTile(state.platform.anchor + i * state.platform.step));
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
      foreach (snapshot in state.snapshots)
        if (snapshot.tile == path[i]) snapshot.added <- AIRail.IsRailTile(snapshot.tile)
            ? (AIRail.GetRailTracks(snapshot.tile) & ~snapshot.tracks) : 0;
    }
    if (!connected) { state.reason = "track"; state.phase = "rollback"; }
    else {
      foreach (snapshot in state.snapshots)
        snapshot.added <- AIRail.IsRailTile(snapshot.tile)
            ? (AIRail.GetRailTracks(snapshot.tile) & ~snapshot.tracks) : 0;
      state.signalsIntent = true; state.phase = "signals";
    }
  } else if (state.phase == "signals") {
    if (state.signalBefore[0].original != AIRail.SIGNALTYPE_NONE ||
        state.signalBefore[2].original != AIRail.SIGNALTYPE_NONE) {
      state.reason = "signals_preexisting"; state.phase = "rollback";
      AIRail.SetCurrentRailType(previousType); return;
    }
    /* front = voisin cote QUAI : _possible_trackdirs dans script_rail.cpp
     * donne le trackdir d'un train venant de ce voisin, donc QUITTANT A.
     * Ce helper strict ne possede aucun repli vers un signal de bloc. */
    local a = OpexC41BuildPbsAtApproach({ lead = state.lead, station_exit = state.exit });
    if (a == 1 && AIRail.GetSignalType(state.lead, state.exit) == AIRail.SIGNALTYPE_PBS)
      state.signalBefore[0].built = true;
    local a2 = OpexC41BuildPbsAtApproach(state.platform);
    if (a2 == 1 && AIRail.GetSignalType(state.platform.lead, state.platform.station_exit) == AIRail.SIGNALTYPE_PBS)
      state.signalBefore[1].built = true;
    local b = OpexC41BuildPbsAtApproach({ lead = state.destLead, station_exit = state.destExit });
    if (b == 1 && AIRail.GetSignalType(state.destLead, state.destExit) == AIRail.SIGNALTYPE_PBS)
      state.signalBefore[2].built = true;
    if (a < 1 || a2 < 1 || b < 1
        || AIRail.GetSignalType(state.lead, state.exit) != AIRail.SIGNALTYPE_PBS
        || AIRail.GetSignalType(state.platform.lead, state.platform.station_exit) != AIRail.SIGNALTYPE_PBS
        || AIRail.GetSignalType(state.destLead, state.destExit) != AIRail.SIGNALTYPE_PBS) {
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
    if (!OpexRailPairStationsFree(this, line)) {
      state.reason = "station_or_depot_shared_before_clone"; state.phase = "rollback";
      AIRail.SetCurrentRailType(previousType); return;
    }
    if (!OpexRailVehicleSlotAvailable()) {
      state.reason = "no_train_slot"; state.phase = "rollback";
      AIRail.SetCurrentRailType(previousType); return;
    }
    state.newVehicle = OpexV271FindNewVehicle(this, state, line.depot);
    if (state.newVehicle == -2) {
      state.reason = "clone_recovery_ambiguous"; state.phase = "rollback";
      AIRail.SetCurrentRailType(previousType); return;
    }
    if (state.newVehicle < 0) state.newVehicle = AIVehicle.CloneVehicle(line.depot, state.vehicle, false);
    if (!AIVehicle.IsValidVehicle(state.newVehicle)) {
      state.reason = "clone"; state.phase = "rollback";
    } else if (!OpexV271MatchesClone(state, state.newVehicle)) {
      state.reason = "clone_orders"; state.phase = "rollback";
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
