/* RAIL-LONG v2 : extension de deux quais fret existants, sans toucher aux
 * voies, ordres ou vehicules. L'integration du selecteur, du tick et du
 * Save/Load est realisee dans main/orchestrator/persist par l'orchestrateur.
 * Les seuls objets physiques ajoutes sont des tuiles de gare vierges. */

RAIL_LONG_V2_CURSOR <- 0;
const RAIL_LONG_V2_SCAN_LIMIT = 24;
const RAIL_LONG_V2_VEHICLE_SCAN_LIMIT = 256;
const RAIL_LONG_V2_RETRY_LIMIT = 24;
const RAIL_LONG_V2_RETRY_DAYS = 365;

function OpexRailLongV2Log(event, lineId, reason)
{
  if (DECISION_LOG) OpexDecide("RAIL_LONG_V2", "event=" + event
      + " line=" + lineId + " reason=" + reason);
}

/* Une gare ne peut etre rallongee que sur le bout oppose a la sortie de
 * voie. La contiguite Manhattan protege contre le wrap des index de carte. */
function OpexRailLongV2ExtendPlan(plan, stationId, target)
{
  if (plan == null || typeof plan != "table"
      || !("anchor" in plan) || !("step" in plan)
      || !("length" in plan) || !("direction" in plan)
      || !("station_exit" in plan) || !("lead" in plan)
      || plan.length < 1 || plan.length > target
      || !AIStation.IsValidStation(stationId)) return null;
  local last = plan.anchor + plan.step * (plan.length - 1);
  if (plan.station_exit != plan.anchor && plan.station_exit != last) return null;
  if (!AIMap.IsValidTile(plan.station_exit) || !AIMap.IsValidTile(plan.lead)
      || AIMap.DistanceManhattan(plan.station_exit, plan.lead) != 1) return null;
  local previous = null;
  for (local i = 0; i < plan.length; i++) {
    local tile = plan.anchor + plan.step * i;
    if (!AIMap.IsValidTile(tile)
        || (previous != null && AIMap.DistanceManhattan(previous, tile) != 1)
        || !AIRail.IsRailStationTile(tile)
        || AIStation.GetStationID(tile) != stationId
        || !AICompany.IsMine(AITile.GetOwner(tile))) return null;
    previous = tile;
  }
  local extra = target - plan.length;
  local frontAtAnchor = plan.station_exit == plan.anchor;
  local nextPlan = clone plan;
  local tiles = [];
  previous = frontAtAnchor ? last : plan.anchor;
  for (local i = 1; i <= extra; i++) {
    local tile = previous + (frontAtAnchor ? plan.step : -plan.step);
    if (!AIMap.IsValidTile(tile)
        || AIMap.DistanceManhattan(previous, tile) != 1
        || !AITile.IsBuildable(tile)
        || AITile.GetSlope(tile) != AITile.SLOPE_FLAT) return null;
    tiles.append(tile);
    previous = tile;
  }
  if (!frontAtAnchor && extra > 0) nextPlan.anchor = previous;
  nextPlan.length = target;
  return { original = clone plan, target = nextPlan, tiles = tiles,
           stationId = stationId };
}

function OpexRailLongV2StationFree(tiles)
{
  foreach (tile in tiles) {
    if (!AIMap.IsValidTile(tile) || AIRail.IsRailStationTile(tile)
        || !AITile.IsBuildable(tile) || AITile.GetSlope(tile) != AITile.SLOPE_FLAT)
      return false;
  }
  return true;
}

function OpexRailLongV2StationBuilt(tiles, stationId)
{
  if (!AIStation.IsValidStation(stationId)) return false;
  foreach (tile in tiles) {
    if (!AIMap.IsValidTile(tile) || !AIRail.IsRailStationTile(tile)
        || AIStation.GetStationID(tile) != stationId
        || !AICompany.IsMine(AITile.GetOwner(tile))) return false;
  }
  return true;
}

function OpexRailLongV2NewAnchor(part)
{
  if (part.tiles.len() == 0) return part.target.anchor;
  return part.target.anchor == part.original.anchor
      ? part.tiles[0] : part.tiles[part.tiles.len() - 1];
}

/* Ne lire qu'une quantite bornee de vehicules. Si l'inventaire est plus
 * grand, l'absence de rame proche ne peut pas etre attestee. La longueur
 * reelle en seiziemes de tuile borne la position possible des wagons :
 * une locomotive eloignee de plus de cette distance Manhattan ne peut pas
 * avoir de wagon sur les nouvelles tuiles. */
function OpexRailLongV2NoVehicleNear(tiles)
{
  if (tiles.len() == 0) return true;
  local vehicles = AIVehicleList();
  local checked = 0;
  for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
    checked++;
    if (checked > RAIL_LONG_V2_VEHICLE_SCAN_LIMIT) return false;
    if (!AIVehicle.IsValidVehicle(vehicle)
        || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL) continue;
    local locoTile = AIVehicle.GetLocation(vehicle);
    local length = AIVehicle.GetLength(vehicle);
    if (!AIMap.IsValidTile(locoTile) || length < 0) return false;
    local reach = (length + 15) / 16 + 2;
    foreach (tile in tiles)
      if (AIMap.DistanceManhattan(locoTile, tile) <= reach) return false;
  }
  return true;
}

function OpexRailLongV2LineSafe(owner, line)
{
  if (owner == null || line == null || typeof line != "table"
      || !("lineId" in line) || typeof line.lineId != "integer"
      || !("mode" in line) || line.mode != "rail"
      || !("kind" in line) || line.kind != "freight"
      || !("platformA" in line) || !("platformB" in line)
      || !("platformLength" in line) || typeof line.platformLength != "integer"
      || !("stationA" in line) || !("stationB" in line)
      || typeof line.stationA != "integer" || typeof line.stationB != "integer"
      || !("depot" in line) || !("vehicles" in line)
      || typeof line.depot != "integer" || typeof line.vehicles != "array"
      || !("trains" in line) || line.trains != 1
      || line.vehicles == null || line.vehicles.len() != 1
      || !("cargo" in line)
      || !("wagons" in line) || !("distance" in line)
      || (("wagons2" in line) && line.wagons2 > 0)
      || (("doubleTrack" in line) && line.doubleTrack != 0)
      || (("v181Loop" in line) && line.v181Loop)
      || (("v190Directional" in line) && line.v190Directional)
      || (("v190Independent" in line) && line.v190Independent)
      || (("v271Tandem" in line) && line.v271Tandem)
      || (("scrapping" in line) && line.scrapping)
      || (("stationA2" in line) && line.stationA2 != null)
      || (("stationB2" in line) && line.stationB2 != null)
      || (("platformA2" in line) && line.platformA2 != null)
      || (("platformB2" in line) && line.platformB2 != null)
      || !AIRail.IsRailDepotTile(line.depot)
      || !AIVehicle.IsValidVehicle(line.vehicles[0])
      || AIVehicle.GetVehicleType(line.vehicles[0]) != AIVehicle.VT_RAIL) return false;
  if (line.platformA == null || line.platformB == null
      || typeof line.platformA != "table" || typeof line.platformB != "table"
      || !("length" in line.platformA) || !("length" in line.platformB))
    return false;
  if ((("v307RoomPlatforms" in line.platformA) && line.platformA.v307RoomPlatforms > 1)
      || (("v307RoomPlatforms" in line.platformB) && line.platformB.v307RoomPlatforms > 1))
    return false;
  local stationA = AIStation.GetStationID(line.stationA);
  local stationB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)
      || stationA == stationB || !AICompany.IsMine(AITile.GetOwner(line.stationA))
      || !AICompany.IsMine(AITile.GetOwner(line.stationB))) return false;
  /* Une autre ligne partageant l'une des gares rendrait l'absence de rames
   * sur les nouveaux quais impossible a certifier simplement. */
  foreach (other in owner._lines) {
    if (other == line || other == null || typeof other != "table") continue;
    local a = ("stationA" in other) && typeof other.stationA == "integer"
        && AIMap.IsValidTile(other.stationA)
        ? AIStation.GetStationID(other.stationA) : AIStation.STATION_INVALID;
    local b = ("stationB" in other) && typeof other.stationB == "integer"
        && AIMap.IsValidTile(other.stationB)
        ? AIStation.GetStationID(other.stationB) : AIStation.STATION_INVALID;
    if (a == stationA || a == stationB || b == stationA || b == stationB) return false;
  }
  return true;
}

function OpexRailLongV2TransactionsFree(owner)
{
  return owner._railSearch == null && owner._railExpansion == null
      && owner._v257Pending == null && owner._v271Pending == null
      && !OpexV284Busy(owner);
}

function OpexRailLongV2Quote(left, right, depot)
{
  if (!AIRail.IsRailDepotTile(depot)) return -1;
  local priorType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(depot));
  local cost = -1;
  {
    local accounting = AIAccounting();
    local testMode = AITestMode();
    local ok = true;
    if (left.tiles.len() > 0)
      ok = AIRail.BuildRailStation(OpexRailLongV2NewAnchor(left),
          left.target.direction, 1, left.tiles.len(), left.stationId);
    if (right.tiles.len() > 0)
      ok = AIRail.BuildRailStation(OpexRailLongV2NewAnchor(right),
          right.target.direction, 1, right.tiles.len(), right.stationId) && ok;
    if (ok) cost = accounting.GetCosts();
  }
  AIRail.SetCurrentRailType(priorType);
  return cost;
}

/* Initialisation INVEST-STALL du meme contrat transactionnel. La provenance
 * est dans l'intention AVANT sa publication : une sauvegarde ne peut la
 * confondre avec RAIL-LONG v2. */
function OpexRailLongV2Begin(owner, line, planA, planB, target, quote, provenance = null)
{
  local now = AIDate.GetCurrentDate();
  local state = {
    lineId = line.lineId, vehicle = line.vehicles[0], depot = line.depot,
    stationAId = planA.stationId, stationBId = planB.stationId,
    oldA = planA.original, oldB = planB.original,
    targetA = planA.target, targetB = planB.target,
    tilesA = planA.tiles, tilesB = planB.tiles,
    beforeA = [], beforeB = [], intentA = false, intentB = false,
    targetLength = target, quotedCost = quote,
    phase = "ready", startDate = now, deadline = now + 365,
    rollbackAttempts = 0, lastRollbackDay = -1, reason = ""
  };
  if (provenance != null) foreach (key, value in provenance) state.rawset(key, value);
  owner._railLongV2Pending = state;
  owner._saveProjection = null;
}

function OpexRailLongV2TransactionLog(state, event, reason)
{
  if (("investStall" in state) && state.investStall) {
    OpexInvestStallFleetLog(event, state.lineId, "kind=platform reason=" + reason
        + " len_a=" + state.oldA.length + " len_b=" + state.oldB.length
        + " target=" + state.targetLength + " quote=" + state.quotedCost
        + " cost_a=" + (("costA" in state) ? state.costA : "unknown")
        + " cost_b=" + (("costB" in state) ? state.costB : "unknown"));
  } else OpexRailLongV2Log(event, state.lineId, reason);
}

/* Selection mensuelle via _expandRailLines ; parcours tournant et borne,
 * sans nouveau champ persistant ni dependance sur INVEST_STALL. */
function OpexRailLongV2Select(owner, year)
{
  if (!RAIL_LONG_V2 || !SAVE_FULL_STATE || owner == null
      || owner._catalog == null || owner._lines == null
      || owner._lines.len() == 0) return false;
  if (owner._railLongV2Pending != null) return true;
  if (!OpexRailLongV2TransactionsFree(owner)) return false;
  local spread = AIGameSettings.GetValue("station.station_spread");
  local maxLength = AIGameSettings.GetValue("vehicle.max_train_length");
  local target = min(7, min(spread, maxLength));
  if (target < 6) return false;
  local count = owner._lines.len();
  local scans = min(count, RAIL_LONG_V2_SCAN_LIMIT);
  local now = AIDate.GetCurrentDate();
  for (local i = 0; i < scans; i++) {
    local line = owner._lines[(RAIL_LONG_V2_CURSOR + i) % count];
    if (!OpexRailLongV2LineSafe(owner, line)
        || line.platformA.length != line.platformLength
        || line.platformB.length != line.platformLength
        || line.platformLength >= target
        || (("railLongV2RetryDate" in line) && now < line.railLongV2RetryDate)
        || !("lastProfit" in line) || line.lastProfit <= 0) continue;
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    local planA = OpexRailLongV2ExtendPlan(line.platformA, stationA, target);
    local planB = OpexRailLongV2ExtendPlan(line.platformB, stationB, target);
    if (planA == null || planB == null
        || (planA.tiles.len() == 0 && planB.tiles.len() == 0)) continue;
    local overlaps = false;
    foreach (tileA in planA.tiles)
      foreach (tileB in planB.tiles)
        if (tileA == tileB) overlaps = true;
    if (overlaps) continue;
    local vehicle = line.vehicles[0];
    local capacity = AIVehicle.GetCapacity(vehicle, line.cargo);
    local waiting = AIStation.GetCargoWaiting(stationA, line.cargo);
    if (capacity <= 0 || waiting < max(1, capacity / 2)) continue;
    local quote = OpexRailLongV2Quote(planA, planB, line.depot);
    if (quote < 0 || OpexAvailableCapital() < quote * 1.10 + 50000) continue;
    line.rawset("railLongV2RetryDate", now + RAIL_LONG_V2_RETRY_DAYS);
    owner._railLongV2Pending = {
      lineId = line.lineId, vehicle = vehicle, depot = line.depot,
      stationAId = stationA, stationBId = stationB,
      oldA = planA.original, oldB = planB.original,
      targetA = planA.target, targetB = planB.target,
      tilesA = planA.tiles, tilesB = planB.tiles,
      beforeA = [], beforeB = [],
      intentA = false, intentB = false,
      targetLength = target, quotedCost = quote,
      phase = "ready", startDate = now, deadline = now + 365,
      rollbackAttempts = 0, lastRollbackDay = -1, reason = ""
    };
    owner._saveProjection = null;
    RAIL_LONG_V2_CURSOR = (RAIL_LONG_V2_CURSOR + i + 1) % count;
    OpexRailLongV2Log("pick", line.lineId, "target=" + target
        + " cost=" + quote + " waiting=" + waiting);
    return true;
  }
  RAIL_LONG_V2_CURSOR = (RAIL_LONG_V2_CURSOR + scans) % count;
  return false;
}

function OpexRailLongV2OriginalValid(state)
{
  return OpexRailLongV2ExtendPlan(state.oldA, state.stationAId,
             state.oldA.length) != null
      && OpexRailLongV2ExtendPlan(state.oldB, state.stationBId,
             state.oldB.length) != null;
}

function OpexRailLongV2BuildPart(state, endName)
{
  local tiles = endName == "A" ? state.tilesA : state.tilesB;
  local stationId = endName == "A" ? state.stationAId : state.stationBId;
  local plan = endName == "A" ? state.targetA : state.targetB;
  if (OpexRailLongV2StationBuilt(tiles, stationId)) return true;
  if (!OpexRailLongV2StationFree(tiles) || !OpexRailLongV2NoVehicleNear(tiles))
    return false;
  local previousType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(state.depot));
  /* La liste est construite depuis l'extremite historique ; BuildRailStation
   * doit recevoir l'ancre basse des tuiles, sans demolir le quai existant. */
  local original = endName == "A" ? state.oldA : state.oldB;
  local anchor = OpexRailLongV2NewAnchor({
    original = original, target = plan, tiles = tiles
  });
  local accounting = (("investStall" in state) && state.investStall) ? AIAccounting() : null;
  local done = tiles.len() == 0
      || AIRail.BuildRailStation(anchor, plan.direction, 1, tiles.len(), stationId);
  if (accounting != null) {
    state.rawset(endName == "A" ? "costA" : "costB", accounting.GetCosts());
    OpexRailLongV2TransactionLog(state, "build", "end=" + endName + " ok=" + done);
  }
  AIRail.SetCurrentRailType(previousType);
  return done && OpexRailLongV2StationBuilt(tiles, stationId);
}

/* Retrait conservateur : seul un ajout dont l'intention a ete sauvee et
 * dont chaque tuile est encore notre gare est candidat. Les tuiles
 * historiques, des voies, signaux et vehicules ne sont jamais alteres. */
function OpexRailLongV2RollbackPart(state, endName)
{
  local intent = endName == "A" ? state.intentA : state.intentB;
  if (!intent) return true;
  local tiles = endName == "A" ? state.tilesA : state.tilesB;
  local stationId = endName == "A" ? state.stationAId : state.stationBId;
  local before = endName == "A" ? state.beforeA : state.beforeB;
  if (before.len() != tiles.len()) return false;
  foreach (entry in before) if (entry) return false;
  foreach (tile in tiles) {
    if (!AIMap.IsValidTile(tile)) return false;
    if (AIRail.IsRailStationTile(tile) &&
        (AIStation.GetStationID(tile) != stationId
         || !AICompany.IsMine(AITile.GetOwner(tile)))) return false;
  }
  if (!OpexRailLongV2NoVehicleNear(tiles)) return false;
  for (local i = tiles.len() - 1; i >= 0; i--) {
    local tile = tiles[i];
    if (AIRail.IsRailStationTile(tile)) {
      /* Chaque commande de demontage peut suspendre le script : verifier a
       * nouveau la vacance, l'identite et la propriete entre deux tuiles. */
      if (!OpexRailLongV2NoVehicleNear(tiles)
          || AIStation.GetStationID(tile) != stationId
          || !AICompany.IsMine(AITile.GetOwner(tile))
          || !AIRail.RemoveRailStationTileRectangle(tile, tile, false))
        return false;
    }
  }
  return true;
}

function OpexRailLongV2PlanMatches(left, right)
{
  return left != null && right != null
      && ("anchor" in left) && ("anchor" in right)
      && ("step" in left) && ("step" in right)
      && ("direction" in left) && ("direction" in right)
      && ("length" in left) && ("length" in right)
      && ("station_exit" in left) && ("station_exit" in right)
      && ("lead" in left) && ("lead" in right)
      && left.anchor == right.anchor && left.step == right.step
      && left.direction == right.direction && left.length == right.length
      && left.station_exit == right.station_exit && left.lead == right.lead;
}

/* Save peut se placer entre deux affectations de line.platformA,
 * line.platformB et line.platformLength. Accepter l'ancien OU le nouveau
 * plan pour chaque bout, mais uniquement si les DEUX poses sont certifiees. */
function OpexRailLongV2CommitReady(owner, line, state)
{
  if (line == null || !OpexRailLongV2LineSafe(owner, line)
      || line.vehicles[0] != state.vehicle || line.depot != state.depot
      || AIStation.GetStationID(line.stationA) != state.stationAId
      || AIStation.GetStationID(line.stationB) != state.stationBId
      || !OpexRailLongV2OriginalValid(state)
      || !OpexRailLongV2StationBuilt(state.tilesA, state.stationAId)
      || !OpexRailLongV2StationBuilt(state.tilesB, state.stationBId)
      || (line.platformLength != state.oldA.length
          && line.platformLength != state.targetLength)
      || !(OpexRailLongV2PlanMatches(line.platformA, state.oldA)
          || OpexRailLongV2PlanMatches(line.platformA, state.targetA))
      || !(OpexRailLongV2PlanMatches(line.platformB, state.oldB)
          || OpexRailLongV2PlanMatches(line.platformB, state.targetB)))
    return false;
  return true;
}

function OpexRailLongV2Cancel(state, reason)
{
  state.reason = reason;
  state.phase = "rollback";
  OpexRailLongV2TransactionLog(state, "fail", reason);
}

/* Une etape courte par passage, et aucun appel bloquant au depot. */
function OpexRailLongV2Step(owner)
{
  if (owner == null || owner._railLongV2Pending == null) return false;
  local state = owner._railLongV2Pending;
  local line = owner._findLineById(state.lineId);
  local investStall = ("investStall" in state) && state.investStall;
  /* Reprise idempotente : apres une sauvegarde pendant le commit, les
   * metadonnees peuvent etre partiellement ou totalement adoptees. */
  if (OpexRailLongV2CommitReady(owner, line, state)) state.phase = "commit";
  if (state.phase != "rollback" && state.phase != "commit" &&
      ((investStall ? !INVEST_STALL : !RAIL_LONG_V2)
       || line == null || !OpexRailLongV2LineSafe(owner, line)
       || line.vehicles[0] != state.vehicle
       || line.depot != state.depot
       || !AIRail.IsRailDepotTile(state.depot)
       || AIDate.GetCurrentDate() >= state.deadline)) {
    OpexRailLongV2Cancel(state, "context_changed");
  }
  if (state.phase == "rollback") {
    local now = AIDate.GetCurrentDate();
    if (!("lastRollbackDay" in state)) state.lastRollbackDay <- -1;
    if (state.lastRollbackDay >= 0 && now < state.lastRollbackDay + 15)
      return true;
    state.lastRollbackDay = now;
    if (OpexRailLongV2RollbackPart(state, "B")
        && OpexRailLongV2RollbackPart(state, "A")) {
      OpexRailLongV2TransactionLog(state, "rolled_back", state.reason);
      owner._railLongV2Pending = null;
    } else {
      state.rollbackAttempts++;
      if (state.rollbackAttempts >= RAIL_LONG_V2_RETRY_LIMIT) {
        /* Un quai occupe ou transforme par un tiers reste en place ;
         * son ancienne longueur de ligne demeure la borne des rames. */
        OpexRailLongV2TransactionLog(state, "orphan_safe", state.reason);
        owner._railLongV2Pending = null;
      }
    }
    return true;
  }
  if (!OpexRailLongV2OriginalValid(state)) {
    OpexRailLongV2Cancel(state, "original_changed"); return true;
  }
  if (state.phase != "commit" && !OpexRailLongV2TransactionsFree(owner)) {
    OpexRailLongV2Cancel(state, "another_transaction"); return true;
  }
  if (investStall && state.phase != "commit"
      && !OpexInvestStallPlatformRecheck(owner, line, state)) {
    OpexRailLongV2Cancel(state, "invest_stall_recheck"); return true;
  }
  if (state.phase == "ready") {
    if (!OpexRailLongV2StationFree(state.tilesA)
        || !OpexRailLongV2StationFree(state.tilesB)) {
      OpexRailLongV2Cancel(state, "site_changed"); return true;
    }
    state.beforeA = [];
    foreach (tile in state.tilesA) state.beforeA.append(AIRail.IsRailStationTile(tile));
    state.intentA = true;
    state.phase = "intent_a";
    return true;
  }
  if (state.phase == "intent_a") {
    if (!OpexRailLongV2BuildPart(state, "A")) {
      OpexRailLongV2Cancel(state, "build_a"); return true;
    }
    state.beforeB = [];
    foreach (tile in state.tilesB) state.beforeB.append(AIRail.IsRailStationTile(tile));
    foreach (entry in state.beforeB) if (entry) {
      OpexRailLongV2Cancel(state, "site_b_changed"); return true;
    }
    state.intentB = true;
    state.phase = "intent_b";
    return true;
  }
  if (state.phase == "intent_b") {
    if (!OpexRailLongV2BuildPart(state, "B")) {
      OpexRailLongV2Cancel(state, "build_b"); return true;
    }
    state.phase = "commit";
    return true;
  }
  if (state.phase == "commit") {
    if (!OpexRailLongV2CommitReady(owner, line, state)) {
      OpexRailLongV2Cancel(state, "commit_recheck"); return true;
    }
    /* Ne pas modifier les tables imbriquees du cache Save existant. */
    line.platformA = clone state.targetA;
    line.platformB = clone state.targetB;
    line.platformLength = state.targetLength;
    if (!investStall) {
      line.rawset("railLongV2", true);
      line.rawset("railLongV2BuildDate", AIDate.GetCurrentDate());
    }
    owner._saveProjection = null;
    owner._v257Cache = null;
    OpexRailLongV2TransactionLog(state, "done", "len=" + state.targetLength
        + " cost=" + state.quotedCost);
    owner._railLongV2Pending = null;
    return true;
  }
  OpexRailLongV2Cancel(state, "bad_phase");
  return true;
}

/* Load() ne lit aucun objet du monde. Cette reconciliation est appelee
 * APRES la reconstitution de _lines dans _reconcileAfterLoad(). */
function OpexRailLongV2Reconcile(owner)
{
  if (owner == null || owner._railLongV2Pending == null) return;
  local state = owner._railLongV2Pending;
  local required = ["lineId", "vehicle", "depot", "stationAId", "stationBId",
                    "oldA", "oldB", "targetA", "targetB",
                    "tilesA", "tilesB", "beforeA", "beforeB",
                    "intentA", "intentB", "phase", "targetLength",
                    "rollbackAttempts", "deadline", "quotedCost",
                    "startDate", "reason"];
  if (typeof state != "table") { owner._railLongV2Pending = null; return; }
  foreach (key in required) {
    if (!(key in state)) { owner._railLongV2Pending = null; return; }
  }
  if (typeof state.tilesA != "array" || typeof state.tilesB != "array"
      || typeof state.beforeA != "array" || typeof state.beforeB != "array"
      || typeof state.oldA != "table" || typeof state.oldB != "table"
      || typeof state.targetA != "table" || typeof state.targetB != "table"
      || typeof state.phase != "string"
      || state.tilesA.len() > 7 || state.tilesB.len() > 7) {
    owner._railLongV2Pending = null; return;
  }
  foreach (value in [state.lineId, state.vehicle, state.depot,
                     state.stationAId, state.stationBId,
                     state.targetLength, state.rollbackAttempts, state.deadline,
                     state.quotedCost, state.startDate]) {
    if (typeof value != "integer") {
      owner._railLongV2Pending = null; return;
    }
  }
  foreach (plan in [state.oldA, state.oldB, state.targetA, state.targetB]) {
    foreach (key in ["anchor", "step", "direction", "length", "station_exit", "lead"]) {
      if (!(key in plan) || typeof plan[key] != "integer") {
        owner._railLongV2Pending = null; return;
      }
    }
  }
  foreach (tiles in [state.tilesA, state.tilesB]) {
    foreach (tile in tiles) if (typeof tile != "integer") {
      owner._railLongV2Pending = null; return;
    }
  }
  foreach (prior in [state.beforeA, state.beforeB]) {
    foreach (entry in prior) if (typeof entry != "bool") {
      owner._railLongV2Pending = null; return;
    }
  }
  if (typeof state.intentA != "bool" || typeof state.intentB != "bool"
      || typeof state.reason != "string"
      || state.targetLength < 6 || state.targetLength > 7
      || state.rollbackAttempts < 0
      || (state.phase != "ready" && state.phase != "intent_a"
          && state.phase != "intent_b" && state.phase != "commit"
          && state.phase != "rollback")) {
    owner._railLongV2Pending = null; return;
  }
  if (!("lastRollbackDay" in state) || typeof state.lastRollbackDay != "integer")
    state.rawset("lastRollbackDay", -1);
  local investStall = ("investStall" in state) && state.investStall;
  if (investStall) {
    foreach (key in ["engine", "wagon", "oldWagons"]) {
      if (!(key in state) || typeof state[key] != "integer") {
        state.phase = "rollback";
        state.reason = "invest_stall_invalid_intent";
      }
    }
    foreach (key in ["costA", "costB"]) {
      if ((key in state) && typeof state[key] != "integer") {
        state.rawset(key, 0);
        state.phase = "rollback";
        state.reason = "invest_stall_invalid_cost";
      }
    }
  }
  if ((investStall ? !INVEST_STALL : !RAIL_LONG_V2) && state.phase != "rollback") {
    if (OpexRailLongV2StationBuilt(state.tilesA, state.stationAId)
        && OpexRailLongV2StationBuilt(state.tilesB, state.stationBId))
      state.phase = "commit";
    else state.phase = "rollback";
  }
  owner._saveProjection = null;
}
