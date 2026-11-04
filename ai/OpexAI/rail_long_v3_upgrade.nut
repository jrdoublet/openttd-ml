/* RAIL-LONG v3 / EXISTANT. Aucun appel de ce module dans les modes 0/1/2.
 *
 * Deux quais : reutilise exactement les preflights, intentions journalisees,
 * controles d'occupation et rollback du constructeur transactionnel v2.
 * Flotte : remplacement DIRECT par >=8 wagons et >=200 unites, jamais le
 * chemin V284 qui impose oldWagons+1. Pas de multitraction non certifiee.
 *
 * Hooks a integrer par prime : champ _railLongV3UpgradePending = null,
 * Select en _expandRailLines, Step avant V257/V284, Save/Load brut,
 * Reconcile apres restauration de _lines, et exclusions OFF correspondantes.
 * Les etats ne contiennent que des tables/arrays/scalaires serialisables.
 */

RAIL_LONG_V3_UPGRADE_CURSOR <- 0;
const RAIL_LONG_V3_UPGRADE_SCAN = 24;
const RAIL_LONG_V3_UPGRADE_RETRY_DAYS = 365;
const RAIL_LONG_V3_UPGRADE_ROLLBACK_LIMIT = 24;
const RAIL_LONG_V3_UPGRADE_CASH_RESERVE = 50000;

function OpexRailLongV3UpgradeLog(event, lineId, detail)
{
  if (DECISION_LOG) OpexDecide("RAIL_LONG_V3", "event=upgrade_" + event
      + " line=" + lineId + " " + detail);
}

function OpexRailLongV3UpgradeBusy(owner)
{
  return owner != null && owner._railLongV3UpgradePending != null;
}

/* Capturer l'erreur AVANT toute autre commande. -1 = garde locale, pas
 * une erreur moteur : GetLastError peut appartenir a un ancien chantier. */
function OpexRailLongV3UpgradeTrace(state, event, reason, endName = "", error = -1)
{
  if (!DECISION_LOG) return;
  local vehicle = state.vehicle;
  local valid = AIVehicle.IsValidVehicle(vehicle);
  local plan = endName == "B" ? state.targetB : state.targetA;
  local tiles = endName == "B" ? state.tilesB : state.tilesA;
  OpexRailLongV3UpgradeLog(event, state.lineId,
      "phase=" + state.phase + " reason=" + reason + " end=" + endName
      + " tile=" + (tiles.len() > 0 ? tiles[0] : plan.anchor)
      + " anchor=" + plan.anchor + " dir=" + plan.direction
      + " station=" + (endName == "B" ? state.stationBId : state.stationAId)
      + " depot=" + state.depot + " old=" + vehicle + " new=" + state.newVehicle
      + " vehicle_state=" + (valid ? AIVehicle.GetState(vehicle) : -1)
      + " location=" + (valid ? AIVehicle.GetLocation(vehicle) : -1)
      + " load=" + (valid && ("cargo" in state)
          ? AIVehicle.GetCargoLoad(vehicle, state.cargo) : -1)
      + " error=" + error);
}

function OpexRailLongV3UpgradeWait(state, reason, endName = "")
{
  local now = AIDate.GetCurrentDate();
  if (!("waitReason" in state) || state.waitReason != reason
      || now >= state.waitDay + 30) {
    state.rawset("waitReason", reason);
    state.rawset("waitDay", now);
    OpexRailLongV3UpgradeTrace(state, "wait", reason, endName);
  }
}

/* V2 fournit la geometrie et la pose. V3 ajoute la validation physique de
 * la direction et du raccordement, sans modifier les chemins OFF/v2. */
function OpexRailLongV3UpgradePlatformOK(plan, stationId)
{
  if (OpexRailLongV2ExtendPlan(plan, stationId, plan.length) == null) return false;
  local step = plan.direction == AIRail.RAILTRACK_NE_SW ? 1
      : (plan.direction == AIRail.RAILTRACK_NW_SE ? AIMap.GetMapSizeX() : 0);
  if (step == 0 || plan.step != step) return false;
  local expectedLead = plan.station_exit == plan.anchor
      ? plan.station_exit - step : plan.station_exit + step;
  if (plan.lead != expectedLead) return false;
  for (local i = 0; i < plan.length; i++)
    if (AIRail.GetRailStationDirection(plan.anchor + i * step) != plan.direction)
      return false;
  return true;
}

function OpexRailLongV3UpgradeCommitReason(owner, line, state)
{
  if (line == null || !OpexRailLongV2LineSafe(owner, line)) return "line_unsafe";
  if (line.vehicles[0] != state.vehicle || line.depot != state.depot) return "identity";
  if (AIStation.GetStationID(line.stationA) != state.stationAId
      || AIStation.GetStationID(line.stationB) != state.stationBId) return "station_id";
  if (!OpexRailLongV3UpgradePlatformOK(state.targetA, state.stationAId)) return "platform_a";
  if (!OpexRailLongV3UpgradePlatformOK(state.targetB, state.stationBId)) return "platform_b";
  if (!OpexRailLongV2CommitReady(owner, line, state)) return "metadata";
  return "";
}

/* Un ordre explicite vers LE depot de la ligne evite la recherche du depot
 * le plus proche, dependante de la direction courante du train. Les deux
 * ordres historiques ne sont jamais remplaces. Intention avant AppendOrder,
 * et reconnaissance physique apres Load, sans appel toggle SendToDepot. */
function OpexRailLongV3UpgradeTemporaryOrder(state)
{
  return AIOrder.GetOrderCount(state.vehicle) == 3
      && AIOrder.IsGotoDepotOrder(state.vehicle, 2)
      && AIOrder.GetOrderDestination(state.vehicle, 2) == state.depot
      && AIOrder.GetOrderFlags(state.vehicle, 2)
          == (AIOrder.OF_STOP_IN_DEPOT | AIOrder.OF_NON_STOP_INTERMEDIATE);
}

function OpexRailLongV3UpgradeRestoreOrders(state)
{
  if (!AIVehicle.IsValidVehicle(state.vehicle)) return true;
  if (("explicitDetour" in state) && state.explicitDetour) {
    if (AIOrder.GetOrderCount(state.vehicle) == 3) {
      if (!OpexRailLongV3UpgradeTemporaryOrder(state)) return false;
      if (!AIOrder.RemoveOrder(state.vehicle, 2)) {
        local error = AIError.GetLastError();
        OpexRailLongV3UpgradeTrace(state, "wait", "remove_depot_order", "", error);
        return false;
      }
    }
    if (AIOrder.GetOrderCount(state.vehicle) != 2) return false;
    /* RemoveOrder restaure l'index normal. Aucun Skip de l'ordre de
     * dechargement historique et aucun remplacement de ses drapeaux. */
    state.detourIssued = false;
    return true;
  }
  /* Migration d'une transaction ancienne : n'annuler que l'ordre depot
   * effectivement courant. Un envoi refuse ne doit pas CREER un detour. */
  if (state.detourIssued && !AIVehicle.IsStoppedInDepot(state.vehicle)
      && AIOrder.IsGotoDepotOrder(state.vehicle, AIOrder.ORDER_CURRENT)) {
    if (!AIVehicle.SendVehicleToDepot(state.vehicle)) return false;
  }
  state.detourIssued = false;
  return true;
}

/* Un chantier secondaire ne doit jamais concurrencer un investissement
 * ferroviaire principal, ni V257, V284, V271, V190 ou la transaction v2. */
function OpexRailLongV3UpgradeSlotFree(owner)
{
  return owner != null && owner._railLongV3UpgradePending == null
      && owner._railLongV2Pending == null
      && owner._v257Pending == null && owner._v271Pending == null
      && owner._railExpansion == null && owner._railSearch == null
      && owner._activeWorker == null && !owner._po01cPending
      && !OpexV284Busy(owner)
      && !OpexV190Active() && !OpexV198Active();
}

/* La garde v2 exclut deja gare partagee, V190/doubles, wagons2, ligne mixte,
 * variantes de deuxieme quai et rame multiple. Ici une seule locomotive
 * reelle est en plus exigee : GetNumWagons seul ne suffit pas a le prouver. */
function OpexRailLongV3UpgradeLineSafe(owner, line)
{
  if (!OpexRailLongV2LineSafe(owner, line)
      || line.platformLength < 1 || line.platformLength > 7
      || line.platformA.length != line.platformLength
      || line.platformB.length != line.platformLength
      || !(line.cargo in owner._catalog.wagonByCargo)
      || !("srcIndustry" in line) || !AIIndustry.IsValidIndustry(line.srcIndustry)
      || !(("lastProfit" in line) && line.lastProfit > 0)) return false;
  local vehicle = line.vehicles[0];
  local oldCount = AIVehicle.GetNumWagons(vehicle) - 1;
  if (oldCount < 1 || AIVehicle.HasSharedOrders(vehicle)
      || AIEngine.IsWagon(AIVehicle.GetEngineType(vehicle))
      || AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle)) > 0) return false;
  local firstWagon = AIVehicle.GetWagonEngineType(vehicle, 1);
  for (local i = 1; i <= oldCount; i++) {
    local part = AIVehicle.GetWagonEngineType(vehicle, i);
    if (!AIEngine.IsWagon(part) || AIEngine.GetCargoType(part) != line.cargo
        || part != firstWagon)
      return false;
  }
  return true;
}

function OpexRailLongV3UpgradeOrdersOK(vehicle, line)
{
  if (!AIVehicle.IsValidVehicle(vehicle)
      || AIOrder.GetOrderCount(vehicle) != 2
      || !AIOrder.IsGotoStationOrder(vehicle, 0)
      || !AIOrder.IsGotoStationOrder(vehicle, 1)
      || AIStation.GetStationID(AIOrder.GetOrderDestination(vehicle, 0))
          != AIStation.GetStationID(line.stationA)
      || AIStation.GetStationID(AIOrder.GetOrderDestination(vehicle, 1))
          != AIStation.GetStationID(line.stationB)
      || (AIOrder.GetOrderFlags(vehicle, 0) & AIOrder.OF_FULL_LOAD_ANY) == 0)
    return false;
  return true;
}

/* Choisir le PLUS GRAND convoi dont la locomotive unique maintient une
 * vitesse et une traction raisonnables avec masse de fret PLEINE. Le
 * catalogue deja calcule fournit une motrice distincte par nombre de wagons.
 * Si aucune motrice simple ne passe, ne PAS simuler deux/trois locos. */
function OpexRailLongV3UpgradeConsist(owner, line, targetLength)
{
  if (!OpexRailLongV3UpgradeLineSafe(owner, line)
      || targetLength < 6 || targetLength < line.platformLength
      || targetLength > AIGameSettings.GetValue("station.station_spread")
      || targetLength > AIGameSettings.GetValue("vehicle.max_train_length"))
    return null;
  local oldVehicle = line.vehicles[0];
  if (!OpexRailLongV3UpgradeOrdersOK(oldVehicle, line)) return null;
  local wagon = owner._catalog.wagonByCargo[line.cargo];
  if (wagon == null || wagon.capacity <= 0
      || !AIEngine.IsBuildable(wagon.id)) return null;
  local minimum = OpexRailLongV3WagonFloor(wagon, targetLength);
  if (minimum < 8) return null;
  local choices = (line.cargo in owner._catalog.locoByCargoWagons)
      ? owner._catalog.locoByCargoWagons[line.cargo] : null;
  if (choices == null || typeof choices != "array") return null;
  local station = AIStation.GetStationID(line.stationA);
  local waiting = AIStation.IsValidStation(station)
      ? AIStation.GetCargoWaiting(station, line.cargo) : -1;
  local rating = AIStation.IsValidStation(station)
      ? AIStation.GetCargoRating(station, line.cargo) : -1;
  local oldCapacity = AIVehicle.GetCapacity(oldVehicle, line.cargo);
  if (waiting < max(oldCapacity, 2 * wagon.capacity) || rating <= 0
      || rating > 100 || oldCapacity <= 0) return null;
  local production = AIIndustry.GetLastMonthProduction(line.srcIndustry, line.cargo);
  if (production <= 0) return null;
  local demand = production.tofloat() * rating / 100.0;
  if (("monthly" in line) && line.monthly > demand) demand = line.monthly;
  demand += waiting.tofloat() / 12.0; // stock, pas revenu perpetuel.
  local oldLoco = OpexV257Engine(AIVehicle.GetEngineType(oldVehicle), line.cargo, false);
  local oldWagon = OpexV257Engine(AIVehicle.GetWagonEngineType(oldVehicle, 1), line.cargo, true);
  local oldCount = AIVehicle.GetNumWagons(oldVehicle) - 1;
  local wagonLimits = OpexV257WagonSpeedLimits();
  local serviceSpeed = OpexV257ConsistLastSpeed(oldLoco, oldWagon, wagonLimits);
  local oldPlan = OpexV257Plan(line, oldLoco, oldWagon, oldCount,
      demand, rating, serviceSpeed, wagonLimits);
  local oldRunning = AIVehicle.GetRunningCost(oldVehicle);
  local realRevenue = AIVehicle.GetProfitLastYear(oldVehicle) + oldRunning;
  if (oldPlan == null || oldPlan.revenue <= 0 || realRevenue <= 0) return null;
  local oldSpeed = OpexRailEffectiveSpeed(oldLoco, oldWagon, oldCount,
      (("routeDistance" in line) && line.routeDistance > 0)
          ? line.routeDistance : line.distance);
  if (oldSpeed <= 0) return null;
  local railType = AIRail.GetRailType(line.depot);
  local upper = min(OpexRailNominalMaxWagons(targetLength), choices.len());
  for (local count = upper; count >= minimum; count--) {
    if (count <= oldCount) continue;
    local loco = choices[count - 1];
    if (loco == null || loco.price <= 0 || loco.runningCost < 0
        || !AIEngine.IsBuildable(loco.id)
        || AIEngine.IsWagon(loco.id)
        || AIEngine.GetCapacity(loco.id) > 0
        || !AIEngine.CanRunOnRail(loco.id, railType)
        || !AIEngine.HasPowerOnRail(loco.id, railType)
        || !AIEngine.CanRunOnRail(wagon.id, railType)
        || !OpexRailLongV3SingleTractionOK(loco, wagon, count)) continue;
    local speed = OpexRailEffectiveSpeed(loco, wagon, count,
        (("routeDistance" in line) && line.routeDistance > 0)
            ? line.routeDistance : line.distance);
    if (speed < 25 || speed < oldSpeed * 0.85) continue;
    local target = OpexV257Plan(line, loco, wagon, count,
        demand, rating, serviceSpeed, wagonLimits);
    if (target == null || target.revenue <= oldPlan.revenue) continue;
    local gain = realRevenue * (target.revenue / oldPlan.revenue - 1.0)
        + oldRunning - target.running;
    local grossPrice = loco.price + count * wagon.price;
    local life = AIEngine.GetMaxAge(loco.id).tofloat() / 365.0;
    local resale = AIVehicle.GetCurrentValue(oldVehicle);
    if (resale < 0) resale = 0;
    /* NoAI min() n'accepte que des entiers ; life est une duree flottante. */
    local economicYears = life < 10.0 ? life : 10.0;
    if (gain <= 0 || life <= 0 || gain * economicYears <= grossPrice - resale)
      continue;
    return { engine = loco.id, wagon = wagon.id, wagons = count,
             oldWagons = oldCount, capacity = count * wagon.capacity,
             grossPrice = grossPrice, gain = gain.tointeger(),
             speedMilli = (speed * 1000).tointeger(),
             waiting = waiting, production = production, rating = rating };
  }
  return null;
}

/* Un plan de quais est etabli AVANT de detourner l'ancienne rame. 7, sinon
 * 6, sinon quai EXISTANT (si deja >=6). Pas de demolitions a la selection. */
function OpexRailLongV3UpgradeSelect(owner, year)
{
  if (!RAIL_LONG_V3 || !SAVE_FULL_STATE || owner == null
      || owner._catalog == null || owner._lines == null
      || owner._lines.len() == 0 || !OpexRailLongV3UpgradeSlotFree(owner))
    return false;
  local count = owner._lines.len();
  local scans = min(count, RAIL_LONG_V3_UPGRADE_SCAN);
  local now = AIDate.GetCurrentDate();
  local trainLimit = min(AIGameSettings.GetValue("station.station_spread"),
                         AIGameSettings.GetValue("vehicle.max_train_length"));
  for (local i = 0; i < scans; i++) {
    local line = owner._lines[(RAIL_LONG_V3_UPGRADE_CURSOR + i) % count];
    if (!OpexRailLongV3UpgradeLineSafe(owner, line)
        || (("railLongV3UpgradeRetry" in line) && now < line.railLongV3UpgradeRetry))
      continue;
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    local top = min(7, trainLimit);
    for (local length = top; length >= max(6, line.platformLength); length--) {
      local a = OpexRailLongV2ExtendPlan(line.platformA, stationA, length);
      local b = OpexRailLongV2ExtendPlan(line.platformB, stationB, length);
      if (a == null || b == null) continue;
      if (!OpexRailLongV3UpgradePlatformOK(a.original, stationA)
          || !OpexRailLongV3UpgradePlatformOK(b.original, stationB)) continue;
      local overlaps = false;
      foreach (tileA in a.tiles)
        foreach (tileB in b.tiles)
          if (tileA == tileB) overlaps = true;
      if (overlaps) continue;
      local consist = OpexRailLongV3UpgradeConsist(owner, line, length);
      if (consist == null) continue;
      local quote = OpexRailLongV2Quote(a, b, line.depot);
      if (quote < 0 || OpexAvailableCapital() <
          (quote + consist.grossPrice) * 1.10 + RAIL_LONG_V3_UPGRADE_CASH_RESERVE)
        continue;
      line.rawset("railLongV3UpgradeRetry", now + RAIL_LONG_V3_UPGRADE_RETRY_DAYS);
      owner._railLongV3UpgradePending = {
        lineId = line.lineId, vehicle = line.vehicles[0], depot = line.depot,
        stationAId = stationA, stationBId = stationB,
        oldA = a.original, oldB = b.original,
        targetA = a.target, targetB = b.target,
        tilesA = a.tiles, tilesB = b.tiles,
        beforeA = [], beforeB = [], intentA = false, intentB = false,
        targetLength = length, quotedCost = quote,
        engine = consist.engine, wagon = consist.wagon,
        wagons = consist.wagons, oldWagons = consist.oldWagons,
        expectedCapacity = consist.capacity, quotedPrice = consist.grossPrice,
        speedMilli = consist.speedMilli, predictedGain = consist.gain,
        newVehicle = -1, beforeDepot = [], order = 0,
        buildStarted = false, detourIssued = false, explicitDetour = false,
        cargo = line.cargo,
        phase = "ready", rollbackAttempts = 0, lastRollbackDay = -1,
        startDate = now, deadline = now + 730, reason = ""
      };
      owner._saveProjection = null;
      RAIL_LONG_V3_UPGRADE_CURSOR = (RAIL_LONG_V3_UPGRADE_CURSOR + i + 1) % count;
      OpexRailLongV3UpgradeLog("pick", line.lineId,
          "platform=" + length + " wagons=" + consist.wagons
          + " cap=" + consist.capacity + " quote=" + quote
          + " vehicle_price=" + consist.grossPrice);
      return true;
    }
  }
  RAIL_LONG_V3_UPGRADE_CURSOR = (RAIL_LONG_V3_UPGRADE_CURSOR + scans) % count;
  return false;
}

function OpexRailLongV3UpgradeAbort(state, reason, endName = "", error = -1)
{
  OpexRailLongV3UpgradeTrace(state, "fail", reason, endName, error);
  state.reason = reason;
  state.phase = "rollback";
}

/* Revalider l'identite complete avant tout changement de la ligne ; c'est
 * OpexRailLongV2CommitReady qui tolere les metadonnees old/target apres Save.
 * Une fois la tete adoptee, seules les identites explicitement connues de
 * la transaction sont acceptees. */
function OpexRailLongV3UpgradeMetadataSafe(owner, line, state)
{
  if (line == null || !OpexRailLongV2LineSafe(owner, line)
      || line.depot != state.depot || line.vehicles.len() != 1
      || (line.vehicles[0] != state.vehicle
          && line.vehicles[0] != state.newVehicle)
      || AIStation.GetStationID(line.stationA) != state.stationAId
      || AIStation.GetStationID(line.stationB) != state.stationBId
      || !OpexRailLongV2StationBuilt(state.tilesA, state.stationAId)
      || !OpexRailLongV2StationBuilt(state.tilesB, state.stationBId)
      || !OpexRailLongV3UpgradePlatformOK(state.targetA, state.stationAId)
      || !OpexRailLongV3UpgradePlatformOK(state.targetB, state.stationBId)
      || !(OpexRailLongV2PlanMatches(line.platformA, state.oldA)
          || OpexRailLongV2PlanMatches(line.platformA, state.targetA))
      || !(OpexRailLongV2PlanMatches(line.platformB, state.oldB)
          || OpexRailLongV2PlanMatches(line.platformB, state.targetB))
      || (line.platformLength != state.oldA.length
          && line.platformLength != state.targetLength))
    return false;
  return true;
}

function OpexRailLongV3UpgradeVehicleCertified(state, line)
{
  local train = state.newVehicle;
  if (!AIVehicle.IsValidVehicle(train)
      || AIVehicle.GetVehicleType(train) != AIVehicle.VT_RAIL
      || AIVehicle.GetEngineType(train) != state.engine
      || AIVehicle.GetNumWagons(train) != state.wagons + 1
      || AIVehicle.GetLength(train) <= 0
      || AIVehicle.GetLength(train) > state.targetLength * 16
      || AIVehicle.GetCapacity(train, line.cargo) < state.expectedCapacity
      || AIVehicle.GetCapacity(train, line.cargo) < 200)
    return false;
  /* Reject any second locomotive, mixed wagon or V301 partial trim. */
  for (local i = 1; i <= state.wagons; i++) {
    local part = AIVehicle.GetWagonEngineType(train, i);
    if (!AIEngine.IsWagon(part) || part != state.wagon) return false;
  }
  return true;
}

/* Reprise apres Start : la rame deja partie n'est JAMAIS vendue. Commit des
 * deux quais et de la flotte idempotent meme si Save s'intercale entre les
 * affectations line.platformA, line.vehicles et line.wagons. */
function OpexRailLongV3UpgradeAdopt(owner, line, state)
{
  if (!AIVehicle.IsValidVehicle(state.newVehicle)
      || AIVehicle.IsStoppedInDepot(state.newVehicle)
      || !OpexRailLongV3UpgradeMetadataSafe(owner, line, state)
      || !OpexRailLongV3UpgradeVehicleCertified(state, line)
      || !OpexRailLongV3UpgradeOrdersOK(state.newVehicle, line))
    return false;
  state.phase = "adopt";
  line.platformA = clone state.targetA;
  line.platformB = clone state.targetB;
  line.platformLength = state.targetLength;
  line.vehicles[0] = state.newVehicle;
  line.trains = 1;
  line.vehCount <- 1;
  line.loco = OpexV257Engine(state.engine, line.cargo, false);
  line.wagons = state.wagons;
  line.wagonId <- state.wagon;
  line.effectiveSpeed = state.speedMilli / 1000.0;
  if (line.effectiveSpeed > 0) {
    line.predOneWayDays <- line.distance.tofloat() / (0.036 * line.effectiveSpeed);
    line.headwayDays <- 2 * line.predOneWayDays;
  }
  line.rawset("railLongV3Upgrade", true);
  line.rawset("railLongV3", true);
  owner._saveProjection = null;
  owner._v257Cache = null;
  /* L'ancienne rame n'est maintenant plus necessaire ; ne la vendre qu'a
   * l'arret, sinon confier son retrait au mecanisme historique V257. */
  if (AIVehicle.IsValidVehicle(state.vehicle)) {
    if (!AIVehicle.IsStoppedInDepot(state.vehicle)
        || !AIVehicle.SellVehicle(state.vehicle)) {
      if (owner._vehiclesToRetire == null) owner._vehiclesToRetire = {};
      owner._vehiclesToRetire.rawset(state.vehicle, {
        lineId = line.lineId, startedDate = AIDate.GetCurrentDate(),
        lastSendDate = AIDate.GetCurrentDate(), attempts = 1
      });
    }
  }
  OpexRailLongV3UpgradeLog("done", state.lineId,
      "old=" + state.vehicle + " new=" + state.newVehicle
      + " length=" + state.targetLength + " wagons=" + state.wagons
      + " capacity=" + AIVehicle.GetCapacity(state.newVehicle, line.cargo)
      + " length16=" + AIVehicle.GetLength(state.newVehicle)
      + " station_a=" + state.stationAId + " station_b=" + state.stationBId
      + " anchor_a=" + state.targetA.anchor + " anchor_b=" + state.targetB.anchor
      + " step_a=" + state.targetA.step + " step_b=" + state.targetB.step
      + " platforms_verified=1 orders_verified=1");
  owner._railLongV3UpgradePending = null;
  return true;
}

/* Recuperation des wagons/tetes CREES apres snapshot pre-build, jamais des
 * vehicules deja presents dans ce depot. Ne pas vendre d'element mouvant ;
 * V257Discard conserve en retraite les ventes moteur refusees. */
function OpexRailLongV3UpgradeCleanup(owner, state)
{
  if (!state.buildStarted) return true;
  local vehicles = AIVehicleList();
  local success = true;
  for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
    if (vehicle == state.vehicle || OpexWaterContains(state.beforeDepot, vehicle))
      continue;
    if (AIVehicle.GetLocation(vehicle) != state.depot) continue;
    /* Une autre rame peut arriver au depot entre le snapshot et le rollback.
     * L'absence de son ID dans beforeDepot ne nous rend PAS proprietaire de
     * cette rame : la liste courante des lignes a priorite sur la difference
     * des identites du depot. */
    local assigned = false;
    foreach (other in owner._lines) {
      if (other == null || !("vehicles" in other)
          || other.vehicles == null) continue;
      if (OpexWaterContains(other.vehicles, vehicle)) {
        assigned = true;
        break;
      }
    }
    if (assigned) continue;
    if (!AIVehicle.IsStoppedInDepot(vehicle)) {
      success = false;
      continue;
    }
    OpexV257Discard(owner, vehicle);
  }
  return success;
}

/* On ne retire les tuiles nouvellement creees qu'apres avoir conserve ou
 * redemarre l'ancienne rame, puis avec V2RollbackPart et ses controles de
 * contiguite/owner/station et exclusion des trains proches. */
function OpexRailLongV3UpgradeRollback(owner, line, state)
{
  local now = AIDate.GetCurrentDate();
  if (state.lastRollbackDay >= 0 && now < state.lastRollbackDay + 15)
    return true;
  state.lastRollbackDay = now;
  local cleaned = OpexRailLongV3UpgradeCleanup(owner, state);
  if (AIVehicle.IsValidVehicle(state.vehicle)) {
    if (!OpexRailLongV3UpgradeRestoreOrders(state)) return true;
    local wasStopped = AIVehicle.IsStoppedInDepot(state.vehicle);
    if (wasStopped && !AIVehicle.StartStopVehicle(state.vehicle)) return true;
  }
  if (cleaned && OpexRailLongV2RollbackPart(state, "B")
      && OpexRailLongV2RollbackPart(state, "A")) {
    OpexRailLongV3UpgradeLog("rolled_back", state.lineId,
        "reason=" + state.reason);
    owner._railLongV3UpgradePending = null;
    owner._saveProjection = null;
    return true;
  }
  state.rollbackAttempts++;
  if (state.rollbackAttempts >= RAIL_LONG_V3_UPGRADE_ROLLBACK_LIMIT) {
    /* Quais et pieces non retirees restent hors longueur de rame declaree.
     * Pas de demolition aventureuse ni de perte de l'ancien train. */
    OpexRailLongV3UpgradeLog("orphan_safe", state.lineId,
        "reason=" + state.reason);
    owner._railLongV3UpgradePending = null;
    owner._saveProjection = null;
  }
  return true;
}

/* Recontrole au depot : les 8+ wagons sont un remplacement UNIQUE. Le
 * revenu predit doit encore couvrir le capital SANS pre-vendre l'ancienne
 * rame. Revalidation du devis juste avant BuildVehicle. */
function OpexRailLongV3UpgradeDepotReady(owner, line, state)
{
  if (!RAIL_LONG_V3 || !OpexRailLongV3UpgradeLineSafe(owner, line)
      || line.vehicles[0] != state.vehicle
      || !OpexRailLongV3UpgradeOrdersOK(state.vehicle, line)
      || !OpexRailLongV3UpgradeMetadataSafe(owner, line, state)
      || !AIVehicle.IsStoppedInDepot(state.vehicle)
      || AIVehicle.GetCargoLoad(state.vehicle, line.cargo) != 0
      || !AIRail.IsRailDepotTile(state.depot)
      || AIVehicle.GetLocation(state.vehicle) != state.depot
      || AIVehicle.GetNumWagons(state.vehicle) - 1 != state.oldWagons)
    return false;
  local refreshed = OpexRailLongV3UpgradeConsist(owner, line, state.targetLength);
  if (refreshed == null || refreshed.engine != state.engine
      || refreshed.wagon != state.wagon
      || refreshed.wagons < state.wagons
      || refreshed.gain <= 0 || refreshed.capacity < state.expectedCapacity)
    return false;
  local loco = OpexV257Engine(state.engine, line.cargo, false);
  local wagon = OpexV257Engine(state.wagon, line.cargo, true);
  local price = loco.price + state.wagons * wagon.price;
  local type = AIRail.GetRailType(state.depot);
  return AIEngine.IsBuildable(state.engine) && AIEngine.IsBuildable(state.wagon)
      && AIEngine.CanRunOnRail(state.engine, type)
      && AIEngine.HasPowerOnRail(state.engine, type)
      && AIEngine.CanRunOnRail(state.wagon, type)
      && OpexRailLongV3SingleTractionOK(loco, wagon, state.wagons)
      && OpexAvailableCapital() >= price * 1.10 + RAIL_LONG_V3_UPGRADE_CASH_RESERVE
      && AICompany.GetBankBalance(AICompany.COMPANY_SELF)
          >= price + RAIL_LONG_V3_UPGRADE_CASH_RESERVE;
}

/* Une transaction sauvegardee avant demarrage peut reprendre sur sa phase ;
 * un builder interrompt entre commandes => rollback plutot que reconstruire.
 * Toute action de monde a une intention persistante prealable. */
function OpexRailLongV3UpgradeStep(owner)
{
  if (!OpexRailLongV3UpgradeBusy(owner)) return false;
  local state = owner._railLongV3UpgradePending;
  local line = owner._findLineById(state.lineId);
  if (state.newVehicle >= 0 && AIVehicle.IsValidVehicle(state.newVehicle)
      && !AIVehicle.IsStoppedInDepot(state.newVehicle)) {
    state.phase = "adopt";
  }
  if (state.phase == "adopt") {
    if (!OpexRailLongV3UpgradeAdopt(owner, line, state)) {
      /* Une rame a deja demarre : ne JAMAIS supprimer son identite. */
      OpexRailLongV3UpgradeLog("orphan_safe", state.lineId,
          "reason=running_vehicle_adoption_failed");
      return true;
    }
    return true;
  }
  if (state.phase == "rollback")
    return OpexRailLongV3UpgradeRollback(owner, line, state);
  if (AIDate.GetCurrentDate() >= state.deadline) {
    OpexRailLongV3UpgradeAbort(state, state.phase == "depot"
        ? "depot_timeout" : "timeout_" + state.phase);
    return true;
  }
  /* Apres Load, _catalog est reconstruit plus tard par la tache catalog.
   * Un wagon absent du catalogue VIDE n'est pas un refus physique. Attendre
   * le premier refresh, borne par la deadline persistante de la transaction. */
  if (RAIL_LONG_V3 && (owner._catalog == null
      || owner._catalog.platformLength <= 0)) {
    OpexRailLongV3UpgradeWait(state, "catalog_after_load");
    return true;
  }
  if (!RAIL_LONG_V3 || line == null
      || !OpexRailLongV3UpgradeLineSafe(owner, line)
      || line.vehicles[0] != state.vehicle || line.depot != state.depot
      || !OpexRailLongV2OriginalValid(state)
      || owner._railLongV2Pending != null
      || owner._v257Pending != null || owner._v271Pending != null
      || OpexV284Busy(owner)) {
    local reason = !RAIL_LONG_V3 ? "disabled" : (line == null ? "line_missing"
        : (!OpexRailLongV3UpgradeLineSafe(owner, line) ? "line_unsafe"
        : (line.vehicles[0] != state.vehicle ? "vehicle_changed"
        : (line.depot != state.depot ? "depot_changed"
        : (!OpexRailLongV2OriginalValid(state) ? "original_changed"
        : (owner._railLongV2Pending != null ? "v2_busy"
        : (owner._v257Pending != null ? "v257_busy"
        : (owner._v271Pending != null ? "v271_busy" : "v284_busy"))))))));
    OpexRailLongV3UpgradeAbort(state, reason);
    return true;
  }
  if (state.phase == "ready") {
    if (!OpexRailLongV2StationFree(state.tilesA)
        || !OpexRailLongV2StationFree(state.tilesB)
        || OpexAvailableCapital() <
            (state.quotedCost + state.quotedPrice) * 1.10
                + RAIL_LONG_V3_UPGRADE_CASH_RESERVE) {
      OpexRailLongV3UpgradeAbort(state, "site_changed");
      return true;
    }
    state.beforeA = [];
    foreach (tile in state.tilesA) state.beforeA.append(AIRail.IsRailStationTile(tile));
    state.intentA = true;
    state.phase = "intent_a";
    return true;
  }
  if (state.phase == "intent_a") {
    if (!OpexRailLongV2StationBuilt(state.tilesA, state.stationAId)
        && !OpexRailLongV2StationFree(state.tilesA)) {
      OpexRailLongV3UpgradeAbort(state, "build_a_site_changed", "A"); return true;
    }
    if (!OpexRailLongV2StationBuilt(state.tilesA, state.stationAId)
        && OpexRailLongV2StationFree(state.tilesA)
        && !OpexRailLongV2NoVehicleNear(state.tilesA)) {
      OpexRailLongV3UpgradeWait(state, "vehicle_near_a", "A"); return true;
    }
    if (!OpexRailLongV2BuildPart(state, "A")) {
      local error = AIError.GetLastError();
      OpexRailLongV3UpgradeAbort(state, "build_a", "A", error); return true;
    }
    state.beforeB = [];
    foreach (tile in state.tilesB) state.beforeB.append(AIRail.IsRailStationTile(tile));
    foreach (entry in state.beforeB) if (entry) {
      OpexRailLongV3UpgradeAbort(state, "site_b_changed"); return true;
    }
    state.intentB = true;
    state.phase = "intent_b";
    return true;
  }
  if (state.phase == "intent_b") {
    if (!OpexRailLongV2StationBuilt(state.tilesB, state.stationBId)
        && !OpexRailLongV2StationFree(state.tilesB)) {
      OpexRailLongV3UpgradeAbort(state, "build_b_site_changed", "B"); return true;
    }
    if (!OpexRailLongV2StationBuilt(state.tilesB, state.stationBId)
        && OpexRailLongV2StationFree(state.tilesB)
        && !OpexRailLongV2NoVehicleNear(state.tilesB)) {
      OpexRailLongV3UpgradeWait(state, "vehicle_near_b", "B"); return true;
    }
    if (!OpexRailLongV2BuildPart(state, "B")) {
      local error = AIError.GetLastError();
      OpexRailLongV3UpgradeAbort(state, "build_b", "B", error); return true;
    }
    local reason = OpexRailLongV3UpgradeCommitReason(owner, line, state);
    if (reason != "") {
      OpexRailLongV3UpgradeAbort(state, "commit_" + reason); return true;
    }
    state.phase = "approach";
    OpexRailLongV3UpgradeTrace(state, "platforms_ready", "both_verified");
    return true;
  }
  if (state.phase == "approach") {
    local reason = OpexRailLongV3UpgradeCommitReason(owner, line, state);
    if (reason != "") {
      OpexRailLongV3UpgradeAbort(state, "commit_" + reason); return true;
    }
    if (!OpexRailLongV3UpgradeOrdersOK(state.vehicle, line)) {
      OpexRailLongV3UpgradeAbort(state, "old_orders_changed"); return true;
    }
    /* Laisser finir le dechargement, puis cibler le depot exact. La distance
     * Manhattan a un depot n'atteste ni acces ni orientation de la rame. */
    if (AIVehicle.GetCargoLoad(state.vehicle, line.cargo) != 0
        || AIVehicle.GetState(state.vehicle) == AIVehicle.VS_AT_STATION) {
      OpexRailLongV3UpgradeWait(state, "unloading"); return true;
    }
    if (AIVehicle.IsStoppedInDepot(state.vehicle)) {
      state.phase = "depot";
      state.deadline = AIDate.GetCurrentDate() + RAIL_EXPAND_TIMEOUT_DAYS;
      return true;
    }
    local front = AIRail.GetRailDepotFrontTile(state.depot);
    if (!AICompany.IsMine(AITile.GetOwner(state.depot))
        || !AIMap.IsValidTile(front) || !AIRail.IsRailTile(front)
        || !AIEngine.HasPowerOnRail(AIVehicle.GetEngineType(state.vehicle),
            AIRail.GetRailType(state.depot))) {
      OpexRailLongV3UpgradeAbort(state, "depot_access_changed"); return true;
    }
    state.order = AIOrder.ResolveOrderPosition(state.vehicle, AIOrder.ORDER_CURRENT);
    state.explicitDetour = true;
    state.phase = "detour_order";
    state.deadline = AIDate.GetCurrentDate() + RAIL_EXPAND_TIMEOUT_DAYS;
    return true;
  }
  if (state.phase == "detour_order") {
    if (!OpexRailLongV3UpgradeTemporaryOrder(state)) {
      if (!OpexRailLongV3UpgradeOrdersOK(state.vehicle, line)) {
        OpexRailLongV3UpgradeAbort(state, "detour_orders_changed"); return true;
      }
      if (!AIOrder.AppendOrder(state.vehicle, state.depot,
          AIOrder.OF_STOP_IN_DEPOT | AIOrder.OF_NON_STOP_INTERMEDIATE)) {
        local error = AIError.GetLastError();
        OpexRailLongV3UpgradeAbort(state, "append_depot_order", "", error); return true;
      }
    }
    state.phase = "detour_route";
    return true;
  }
  if (state.phase == "detour_route") {
    if (!OpexRailLongV3UpgradeTemporaryOrder(state)
        || AIVehicle.GetCargoLoad(state.vehicle, line.cargo) != 0) {
      OpexRailLongV3UpgradeAbort(state, "detour_changed_or_loaded"); return true;
    }
    if (AIOrder.ResolveOrderPosition(state.vehicle, AIOrder.ORDER_CURRENT) != 2
        && !AIOrder.SkipToOrder(state.vehicle, 2)) {
      local error = AIError.GetLastError();
      OpexRailLongV3UpgradeAbort(state, "skip_depot_order", "", error); return true;
    }
    state.detourIssued = true;
    state.phase = "depot";
    OpexRailLongV3UpgradeTrace(state, "depot_order", "accepted");
    return true;
  }
  if (state.phase == "depot") {
    if (!AIVehicle.IsStoppedInDepot(state.vehicle)) {
      OpexRailLongV3UpgradeWait(state, "depot_arrival");
      return true;
    }
    if (!OpexRailLongV3UpgradeRestoreOrders(state)) {
      OpexRailLongV3UpgradeAbort(state, "restore_orders"); return true;
    }
    if (!OpexRailLongV3UpgradeDepotReady(owner, line, state)) {
      OpexRailLongV3UpgradeAbort(state, "depot_quote_changed"); return true;
    }
    state.beforeDepot = [];
    local before = AIVehicleList();
    /* Tous les vehicules preexistants, meme ailleurs : une rame arrivant
     * pendant BuildTrains n'est jamais une creation de cette transaction. */
    for (local vehicle = before.Begin(); !before.IsEnd(); vehicle = before.Next())
      state.beforeDepot.append(vehicle);
    state.buildStarted = true;
    state.phase = "building";
    local oldType = AIRail.GetCurrentRailType();
    AIRail.SetCurrentRailType(AIRail.GetRailType(state.depot));
    local wagon = OpexV257Engine(state.wagon, line.cargo, true);
    local loco = OpexV257Engine(state.engine, line.cargo, false);
    local equipment = { wagonByCargo = {} };
    equipment.wagonByCargo.rawset(line.cargo, wagon);
    local built = OpexBuildTrains(equipment, line.cargo, line.kind, state.depot,
        line.stationA, line.stationB, 1, loco, state.wagons, state.targetLength, false);
    AIRail.SetCurrentRailType(oldType);
    state.newVehicle = built.vehicles.len() > 0 ? built.vehicles[0] : -1;
    if (built.failed || built.built != 1
        || !OpexRailLongV3UpgradeVehicleCertified(state, line)
        || !AIVehicle.IsStoppedInDepot(state.newVehicle)) {
      OpexRailLongV3UpgradeAbort(state, "build_or_length"); return true;
    }
    state.phase = "prepared";
    return true;
  }
  if (state.phase == "prepared") {
    if (!OpexRailLongV3UpgradeVehicleCertified(state, line)
        || !OpexRailLongV2CommitReady(owner, line, state)
        || !AIOrder.CopyOrders(state.newVehicle, state.vehicle)) {
      OpexRailLongV3UpgradeAbort(state, "copy_orders"); return true;
    }
    state.phase = "ordered";
    return true;
  }
  if (state.phase == "ordered") {
    if (!OpexRailLongV3UpgradeOrdersOK(state.newVehicle, line)
        || !OpexRailLongV3UpgradeVehicleCertified(state, line)
        || (AIOrder.ResolveOrderPosition(state.newVehicle, AIOrder.ORDER_CURRENT) != 0
            && !AIOrder.SkipToOrder(state.newVehicle, 0))) {
      OpexRailLongV3UpgradeAbort(state, "order_or_consist"); return true;
    }
    state.phase = "starting";
    return true;
  }
  if (state.phase == "starting") {
    if (!OpexRailLongV3UpgradeVehicleCertified(state, line)
        || !OpexRailLongV3UpgradeOrdersOK(state.newVehicle, line)
        || !OpexRailLongV2CommitReady(owner, line, state)
        || !AIVehicle.StartStopVehicle(state.newVehicle)) {
      OpexRailLongV3UpgradeAbort(state, "start_failed"); return true;
    }
    state.phase = "adopt";
    return true;
  }
  OpexRailLongV3UpgradeAbort(state, "unknown_phase");
  return true;
}

/* Le Load brut doit preceder les settings, cette reconciliation doit suivre
 * _lines. Une machine incomplente n'est JAMAIS reprise en plein builder :
 * ses seuls ajouts identifiables sont nettoyes en rollback. */
function OpexRailLongV3UpgradeReconcile(owner)
{
  if (!OpexRailLongV3UpgradeBusy(owner)) return;
  local state = owner._railLongV3UpgradePending;
  if (typeof state != "table") {
    owner._railLongV3UpgradePending = null;
    return;
  }
  local required = ["lineId", "vehicle", "depot", "stationAId", "stationBId",
    "oldA", "oldB", "targetA", "targetB", "tilesA", "tilesB",
    "beforeA", "beforeB", "intentA", "intentB", "targetLength",
    "quotedCost", "engine", "wagon", "wagons", "oldWagons",
    "expectedCapacity", "quotedPrice", "speedMilli", "predictedGain",
    "newVehicle", "beforeDepot", "order", "phase", "rollbackAttempts",
    "lastRollbackDay", "startDate", "deadline", "reason"];
  foreach (key in required) if (!(key in state)) {
    OpexRailLongV3UpgradeLog("orphan_safe", -1, "reason=invalid_save_schema");
    owner._railLongV3UpgradePending = null;
    return;
  }
  if (typeof state.tilesA != "array" || typeof state.tilesB != "array"
      || typeof state.beforeA != "array" || typeof state.beforeB != "array"
      || typeof state.beforeDepot != "array"
      || typeof state.oldA != "table" || typeof state.oldB != "table"
      || typeof state.targetA != "table" || typeof state.targetB != "table"
      || typeof state.phase != "string" || typeof state.reason != "string"
      || state.targetLength < 6 || state.targetLength > 7
      || state.wagons < 8 || state.expectedCapacity < 200
      || state.tilesA.len() > 7 || state.tilesB.len() > 7) {
    OpexRailLongV3UpgradeLog("orphan_safe", state.lineId, "reason=invalid_save_types");
    owner._railLongV3UpgradePending = null;
    return;
  }
  if (!("buildStarted" in state) || typeof state.buildStarted != "bool")
    state.rawset("buildStarted", false);
  if (!("detourIssued" in state) || typeof state.detourIssued != "bool")
    state.rawset("detourIssued", false);
  if (!("explicitDetour" in state) || typeof state.explicitDetour != "bool")
    state.rawset("explicitDetour", false);
  if (state.newVehicle >= 0 && AIVehicle.IsValidVehicle(state.newVehicle)
      && !AIVehicle.IsStoppedInDepot(state.newVehicle)) {
    state.phase = "adopt";
  } else if (state.phase == "building" || state.phase == "starting") {
    OpexRailLongV3UpgradeAbort(state, "load_during_builder");
  } else if (!RAIL_LONG_V3 && state.phase != "adopt") {
    OpexRailLongV3UpgradeAbort(state, "disabled_after_load");
  }
  /* _lastCatalogMonth est persiste, mais le catalogue natif ne l'est pas.
   * Rendre la tache catalog exigible pour cette transaction reprise. */
  if (RAIL_LONG_V3 && owner._catalog != null
      && owner._catalog.platformLength <= 0)
    owner._lastCatalogMonth = -1;
  owner._saveProjection = null;
}
