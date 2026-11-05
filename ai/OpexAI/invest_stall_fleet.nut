/* INVEST-STALL v2 / flotte : investissement tardif sur une origine de fret
 * existante et sous-transportee. Transaction persistante V284, sans boucle
 * V284 atLimit sur une voie unique. Le renfort multi-trains reste fail-closed :
 * les attestations disponibles de parcours directionnel concernent des lignes
 * DEJA dotees de deux rames, et ne certifient pas la pose d'une seconde rame. */

function OpexInvestStallFleetLog(event, lineId, fields)
{
  if (DECISION_LOG) OpexDecide("INVEST_STALL", "event=" + event
      + " route=fleet line=" + lineId + " " + fields);
}

/* INVEST-STALL diagnostic seul : pas de nouvel etat décisionnel. Le debut
 * survit au Save/Load avec le pending ; les vieilles sauvegardes sans
 * traceStart restent lisibles via deadline. */
function OpexInvestStallTraceId(pending)
{
  local start = ("traceStart" in pending) ? pending.traceStart : pending.deadline;
  return pending.lineId + "_" + pending.vehicle + "_" + start;
}

/* Miroir READ-ONLY de la marge, appele uniquement si son calcul reel a
 * deja refuse le projet. Le resultat n'est JAMAIS utilise pour investir. */
function OpexInvestStallMarginRejectReason(line, vehicle, wagon, oldWagons, equipment, gap)
{
  if (gap == null || !gap.ok) return "gap_" + (gap == null ? "null" : gap.reason);
  if (oldWagons < 1 || wagon == null || equipment == null
      || !("engine" in equipment)) return "margin_input";
  local oldLoco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
  local newLoco = OpexV257Engine(equipment.engine, line.cargo, false);
  if (oldLoco == null || newLoco == null || newLoco.ageYears <= 0)
    return "margin_engine";
  local dist = (("routeDistance" in line) && line.routeDistance > 0)
      ? line.routeDistance : line.distance;
  if (dist <= 0) return "margin_distance";
  local oldSpeed = OpexRailEffectiveSpeed(oldLoco, wagon, oldWagons, dist);
  local newSpeed = OpexRailEffectiveSpeed(newLoco, wagon, oldWagons + 1, dist);
  if (oldSpeed <= 0 || newSpeed < oldSpeed) return "margin_traction";
  local dwell = OpexRailStationDwellDays(wagon);
  local oldDays = dist / (0.036 * oldSpeed);
  local newDays = dist / (0.036 * newSpeed);
  local oldCycle = 2.0 * oldDays + dwell;
  local newCycle = 2.0 * newDays + dwell;
  if (oldCycle <= 0 || newCycle <= 0) return "margin_cycle";
  local oldCapacity = AIVehicle.GetCapacity(vehicle, line.cargo) * 30.0 / oldCycle;
  local newCapacity = (oldWagons + 1) * wagon.capacity * 30.0 / newCycle;
  local extra = min(newCapacity - oldCapacity,
      gap.production.tofloat() * gap.rating / 100.0 - gap.capacity);
  if (extra <= 0.0) return "margin_no_extra";
  local ratedOffer = gap.production.tofloat() * gap.rating / 100.0;
  if (ratedOffer <= 0.0) return "margin_no_offer";
  local loadDays = (oldWagons + 1) * wagon.capacity * 30.0 / ratedOffer;
  local income = AICargo.GetCargoIncome(line.cargo, line.distance,
      OpexCeilDiv(newDays + loadDays / 2.0, 1));
  if (income <= 0) return "margin_income";
  local price = newLoco.price + (oldWagons + 1) * wagon.price;
  local running = newLoco.runningCost + (oldWagons + 1) * wagon.runningCost
      - AIVehicle.GetRunningCost(vehicle);
  local profit = 12.0 * extra * income - running - price / newLoco.ageYears;
  if (profit <= 0 || price <= 0) return "margin_profit";
  if (OpexAvailableCapital() < price + 50000) return "margin_cash";
  return "margin_unclassified";
}

/* Détail de TOUS les prédicats échoués, dans l'ordre du if original ;
 * aucun raccourci n'est utilisé pour autoriser une action. */
function OpexInvestStallRecheckDiagnostic(owner, line, pending, vehicle,
                                         wagon, gap, margin, homogeneous, waitingNow)
{
  if (!DECISION_LOG) return;
  local failed = [];
  if (!INVEST_STALL) failed.append("disabled");
  if (!OpexInvestStallReady()) failed.append("not_ready");
  if (pending.add) failed.append("add_train");
  if (!homogeneous) failed.append("mixed_wagons");
  if (owner._railLongV2Pending != null) failed.append("rail_long_v2");
  if (owner._railLongV3UpgradePending != null) failed.append("rail_long_v3");
  if (owner._v257Pending != null) failed.append("v257");
  if (owner._v271Pending != null) failed.append("v271");
  if (owner._railExpansion != null) failed.append("rail_expansion");
  if (V233L_STATE != null && V233L_STATE.pending != null) failed.append("v233");
  if (line.vehicles.len() != 1 || line.trains != 1) failed.append("fleet_shape");
  if (line.vehicles[0] != vehicle) failed.append("vehicle_changed");
  if (AIVehicle.GetNumWagons(vehicle) - 1 != pending.oldWagons)
    failed.append("wagon_count_changed");
  if (margin == null) failed.append("margin_null");
  if (pending.wagons != pending.oldWagons + 1) failed.append("target_count");
  local primary = failed.len() > 0 ? failed[0] : "unclassified";
  local all = "";
  foreach (reason in failed) all += (all == "" ? "" : ",") + reason;
  local marginDetail = margin == null
      ? OpexInvestStallMarginRejectReason(line, vehicle, wagon,
          pending.oldWagons, { engine = pending.engine }, gap)
      : "positive";
  local locoCapacity = AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle));
  local mismatchCount = 0;
  local firstMismatch = -1;
  local firstActual = -1;
  for (local w = 1; w <= pending.oldWagons; w++) {
    local actual = AIVehicle.GetWagonEngineType(vehicle, w);
    if (actual != pending.wagon) {
      mismatchCount++;
      if (firstMismatch < 0) { firstMismatch = w; firstActual = actual; }
    }
  }
  OpexInvestStallFleetLog("diagnostic", pending.lineId,
      "kind=wagon reason=invest_stall_recheck primary=" + primary
      + " failed=" + all + " margin_detail=" + marginDetail
      + " txn=" + OpexInvestStallTraceId(pending)
      + " phase=" + pending.phase
      + " elapsed_days=" + (AIDate.GetCurrentDate()
          - (("traceStart" in pending) ? pending.traceStart : AIDate.GetCurrentDate()))
      + " gap=" + gap.reason + " production=" + gap.production
      + " rating=" + gap.rating + " transported=" + gap.pct
      + " capacity_month=" + gap.capacity
      + " rated_offer=" + (gap.production.tofloat() * gap.rating / 100.0)
      + " waiting=" + waitingNow + " cash=" + OpexAvailableCapital()
      + " selected_wagons=" + pending.oldWagons
      + " live_wagons=" + (AIVehicle.GetNumWagons(vehicle) - 1)
      + " loco_capacity=" + locoCapacity
      + " wagon_mismatches=" + mismatchCount + " first_mismatch=" + firstMismatch
      + " expected_wagon_id=" + pending.wagon + " actual_wagon_id=" + firstActual
      + " profit_now=" + (margin == null ? "null" : margin.profit));
}

/* Explicite la cause du test de surete v2 sans le remplacer. */
function OpexInvestStallLineSafetyReason(owner, line)
{
  if (owner == null || line == null || typeof line != "table") return "no_line";
  if (!("lineId" in line) || !("mode" in line) || !("kind" in line)
      || !("platformA" in line) || !("platformB" in line)
      || !("platformLength" in line) || !("stationA" in line)
      || !("stationB" in line) || !("depot" in line)
      || !("vehicles" in line) || !("trains" in line)
      || !("cargo" in line) || !("wagons" in line)
      || !("distance" in line)) return "shape";
  if (line.mode != "rail" || line.kind != "freight") return "mode";
  if (typeof line.lineId != "integer" || typeof line.platformLength != "integer"
      || typeof line.stationA != "integer" || typeof line.stationB != "integer"
      || typeof line.depot != "integer" || typeof line.vehicles != "array")
    return "types";
  if (line.vehicles == null || line.trains != 1 || line.vehicles.len() != 1)
    return "fleet";
  if ((("wagons2" in line) && line.wagons2 > 0)
      || (("doubleTrack" in line) && line.doubleTrack != 0)
      || (("v181Loop" in line) && line.v181Loop)
      || (("v190Directional" in line) && line.v190Directional)
      || (("v190Independent" in line) && line.v190Independent)
      || (("v271Tandem" in line) && line.v271Tandem)
      || (("scrapping" in line) && line.scrapping)
      || (("stationA2" in line) && line.stationA2 != null)
      || (("stationB2" in line) && line.stationB2 != null)
      || (("platformA2" in line) && line.platformA2 != null)
      || (("platformB2" in line) && line.platformB2 != null)) return "complex_line";
  if (!AIRail.IsRailDepotTile(line.depot)
      || !AIVehicle.IsValidVehicle(line.vehicles[0])
      || AIVehicle.GetVehicleType(line.vehicles[0]) != AIVehicle.VT_RAIL)
    return "invalid_depot_vehicle";
  if (line.platformA == null || line.platformB == null
      || typeof line.platformA != "table" || typeof line.platformB != "table"
      || !("length" in line.platformA) || !("length" in line.platformB))
    return "plan_shape";
  if ((("v307RoomPlatforms" in line.platformA) && line.platformA.v307RoomPlatforms > 1)
      || (("v307RoomPlatforms" in line.platformB) && line.platformB.v307RoomPlatforms > 1))
    return "multi_platform";
  local a = AIStation.GetStationID(line.stationA);
  local b = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(a) || !AIStation.IsValidStation(b)
      || a == b || !AICompany.IsMine(AITile.GetOwner(line.stationA))
      || !AICompany.IsMine(AITile.GetOwner(line.stationB))) return "station_invalid";
  foreach (other in owner._lines) {
    if (other == line || other == null || typeof other != "table") continue;
    local x = ("stationA" in other) && typeof other.stationA == "integer"
        && AIMap.IsValidTile(other.stationA)
        ? AIStation.GetStationID(other.stationA) : AIStation.STATION_INVALID;
    local y = ("stationB" in other) && typeof other.stationB == "integer"
        && AIMap.IsValidTile(other.stationB)
        ? AIStation.GetStationID(other.stationB) : AIStation.STATION_INVALID;
    if (x == a || y == a) return "shared_station_a";
    if (x == b || y == b) return "shared_station_b";
  }
  return "unclassified";
}

function OpexInvestStallPlatformDiagnostic(owner, line)
{
  if (!DECISION_LOG) return;
  local failed = [];
  if (owner._railSearch != null) failed.append("rail_search");
  if (owner._railExpansion != null) failed.append("rail_expansion");
  if (owner._v257Pending != null) failed.append("v257");
  if (owner._v271Pending != null) failed.append("v271");
  if (OpexV284Busy(owner)) failed.append("v284");
  if (owner._railLongV3UpgradePending != null) failed.append("rail_long_v3");
  if (owner._activeWorker != null) failed.append("active_worker");
  if (owner._po01cPending) failed.append("po01c");
  if (V233L_STATE != null && V233L_STATE.pending != null) failed.append("v233");
  if (!OpexRailLongV2LineSafe(owner, line))
    failed.append("unsafe_" + OpexInvestStallLineSafetyReason(owner, line));
  if (line.platformA.length != line.platformLength) failed.append("plan_a_mismatch");
  if (line.platformB.length != line.platformLength) failed.append("plan_b_mismatch");
  local primary = failed.len() > 0 ? failed[0] : "unclassified";
  local all = "";
  foreach (reason in failed) all += (all == "" ? "" : ",") + reason;
  local target = min(7, min(AIGameSettings.GetValue("station.station_spread"),
      AIGameSettings.GetValue("vehicle.max_train_length")));
  OpexInvestStallFleetLog("diagnostic", line.lineId,
      "kind=platform reason=unsafe_or_busy primary=" + primary
      + " failed=" + all + " target=" + target
      + " len_a=" + line.platformA.length + " len_b=" + line.platformB.length
      + " platform=" + line.platformLength
      + " at_target=" + (line.platformLength >= target ? 1 : 0)
      + " worker=" + (owner._activeWorker == null ? "none" : owner._activeWorker.kind));
}

/* Une distance exploitable, une offre mesurable et la capacite de TOUTES les
 * lignes de la meme industrie : une nouvelle rame ne peut pas revendre une
 * production deja transportee par une autre ligne Opex. L'ancien train
 * continue a rouler jusqu'au remplacement physique. La valeur de revente est
 * ignoree : cout d'achat integral = devis conservateur. */
function OpexInvestStallFleetMargin(line, vehicle, wagon, oldWagons, equipment, gap)
{
  if (gap == null || !gap.ok || oldWagons < 1 || wagon == null
      || equipment == null || !("engine" in equipment)) return null;
  local oldLoco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
  local newLoco = OpexV257Engine(equipment.engine, line.cargo, false);
  if (oldLoco == null || newLoco == null || newLoco.ageYears <= 0) return null;
  local dist = (("routeDistance" in line) && line.routeDistance > 0)
      ? line.routeDistance : line.distance;
  if (dist <= 0) return null;
  local oldSpeed = OpexRailEffectiveSpeed(oldLoco, wagon, oldWagons, dist);
  local newSpeed = OpexRailEffectiveSpeed(newLoco, wagon, oldWagons + 1, dist);
  if (oldSpeed <= 0 || newSpeed < oldSpeed) return null;
  local dwell = OpexRailStationDwellDays(wagon);
  local oldDays = dist / (0.036 * oldSpeed);
  local newDays = dist / (0.036 * newSpeed);
  local oldCycle = 2.0 * oldDays + dwell;
  local newCycle = 2.0 * newDays + dwell;
  if (oldCycle <= 0 || newCycle <= 0) return null;
  local oldCapacity = AIVehicle.GetCapacity(vehicle, line.cargo) * 30.0 / oldCycle;
  local newCapacity = (oldWagons + 1) * wagon.capacity * 30.0 / newCycle;
  local extra = newCapacity - oldCapacity;
  local free = gap.production.tofloat() * gap.rating / 100.0 - gap.capacity;
  if (extra > free) extra = free;
  if (extra <= 0.0) return null;
  local loadDays = (oldWagons + 1) * wagon.capacity * 30.0
      / (gap.production.tofloat() * gap.rating / 100.0);
  local income = AICargo.GetCargoIncome(line.cargo, line.distance,
      OpexCeilDiv(newDays + loadDays / 2.0, 1));
  if (income <= 0) return null;
  local price = newLoco.price + (oldWagons + 1) * wagon.price;
  local running = newLoco.runningCost + (oldWagons + 1) * wagon.runningCost
      - AIVehicle.GetRunningCost(vehicle);
  local profit = 12.0 * extra * income - running - price / newLoco.ageYears;
  if (profit <= 0 || price <= 0 || OpexAvailableCapital() < price + 50000)
    return null;
  return { profit = profit, cost = price, monthly = extra, score = profit / price };
}

/* Une simple marque doubleTrack ou v181Loop ne certifie rien. Toute voie
 * supplementaire exigerait un parcours physique bidirectionnel protege PBS,
 * les deux depots, et des ordres/waypoints prouves avant de lancer un train.
 * Aucune des anciennes routes V284 atLimit n'apporte cette certification.
 * La selection refuse donc explicitement l'achat d'un train additionnel. */
function OpexInvestStallFleetTrainCertified(line)
{
  return false;
}

/* La transaction de quais emprunte le moteur v2, jamais son selecteur ni
 * son reglage. Une recherche/construction et les autres flottes ont priorite. */
function OpexInvestStallPlatformSlotFree(owner)
{
  return OpexRailLongV2TransactionsFree(owner)
      && owner._railLongV3UpgradePending == null && owner._activeWorker == null
      && !owner._po01cPending
      && !(V233L_STATE != null && V233L_STATE.pending != null);
}

function OpexInvestStallPlatformMargin(line, vehicle, wagon, oldWagons, equipment, gap, quote)
{
  local margin = OpexInvestStallFleetMargin(line, vehicle, wagon, oldWagons, equipment, gap);
  if (margin == null || quote < 0) return null;
  local loco = OpexV257Engine(equipment.engine, line.cargo, false);
  /* Cout complet du remplacement et des DEUX quais, sans credit de revente.
   * Amortir aussi les quais sur la vie du moteur est conservateur. */
  local construction = quote * 1.10;
  local profit = margin.profit - construction / loco.ageYears;
  local cost = margin.cost + construction;
  if (profit <= 0 || OpexAvailableCapital() < cost + 50000) return null;
  return { profit = profit, cost = cost, monthly = margin.monthly, score = profit / cost };
}

function OpexInvestStallPlatformPlan(owner, line, vehicle, wagon, oldWagons, equipment, gap)
{
  if (!OpexInvestStallPlatformSlotFree(owner) || !OpexRailLongV2LineSafe(owner, line)
      || line.platformA.length != line.platformLength
      || line.platformB.length != line.platformLength) {
    if (DECISION_LOG) OpexInvestStallPlatformDiagnostic(owner, line);
    OpexInvestStallFleetLog("skip", line.lineId, "kind=platform reason=unsafe_or_busy");
    return null;
  }
  local maxLength = min(7, min(AIGameSettings.GetValue("station.station_spread"),
      AIGameSettings.GetValue("vehicle.max_train_length")));
  for (local target = maxLength; target >= 6 && target > line.platformLength; target--) {
    if (oldWagons + 1 > OpexRailNominalMaxWagons(target)
        || AIVehicle.GetLength(vehicle) + 8 > target * 16) continue;
    local planA = OpexRailLongV2ExtendPlan(line.platformA,
        AIStation.GetStationID(line.stationA), target);
    local planB = OpexRailLongV2ExtendPlan(line.platformB,
        AIStation.GetStationID(line.stationB), target);
    if (planA == null || planB == null) {
      OpexInvestStallFleetLog("skip", line.lineId,
          "kind=platform reason=geometry target=" + target);
      continue;
    }
    local overlaps = false;
    foreach (a in planA.tiles) foreach (b in planB.tiles) if (a == b) overlaps = true;
    if (overlaps) continue;
    local quote = OpexRailLongV2Quote(planA, planB, line.depot);
    local margin = OpexInvestStallPlatformMargin(line, vehicle, wagon, oldWagons,
        equipment, gap, quote);
    OpexInvestStallFleetLog(margin == null ? "skip" : "screen", line.lineId,
        "kind=platform reason=" + (margin == null ? "quote_or_margin_or_cash" : "eligible")
        + " len_a=" + line.platformA.length + " len_b=" + line.platformB.length
        + " target=" + target + " quote=" + quote + " cash=" + OpexAvailableCapital()
        + " profit=" + (margin != null ? margin.profit : "unknown")
        + " production=" + gap.production + " rating=" + gap.rating
        + " capacity_month=" + gap.capacity);
    if (margin != null) return { planA = planA, planB = planB, target = target,
        quote = quote, margin = margin };
  }
  return null;
}

/* Relecture avant chaque pose, y compris apres Load. Seules les tuiles
 * encore absentes entrent dans le devis ; les intentions restent au moteur v2. */
function OpexInvestStallPlatformRecheck(owner, line, state)
{
  if (!OpexInvestStallReady() || !OpexInvestStallPlatformSlotFree(owner)
      || !("engine" in state) || !("wagon" in state) || !("oldWagons" in state)
      || !OpexRailLongV2LineSafe(owner, line)
      || line.vehicles[0] != state.vehicle || line.depot != state.depot
      || AIStation.GetStationID(line.stationA) != state.stationAId
      || AIStation.GetStationID(line.stationB) != state.stationBId
      || !OpexRailLongV2PlanMatches(line.platformA, state.oldA)
      || !OpexRailLongV2PlanMatches(line.platformB, state.oldB)
      || state.targetLength > AIGameSettings.GetValue("station.station_spread")
      || state.targetLength > AIGameSettings.GetValue("vehicle.max_train_length")
      || AIVehicle.GetNumWagons(state.vehicle) - 1 != state.oldWagons
      || AIEngine.GetCapacity(AIVehicle.GetEngineType(state.vehicle)) > 0
      || !AIEngine.IsBuildable(state.engine) || !AIEngine.IsBuildable(state.wagon)
      || !AIEngine.IsWagon(state.wagon) || AIEngine.GetCargoType(state.wagon) != line.cargo
      || !AIEngine.CanRunOnRail(state.engine, AIRail.GetRailType(state.depot))
      || !AIEngine.HasPowerOnRail(state.engine, AIRail.GetRailType(state.depot))) return false;
  for (local w = 1; w <= state.oldWagons; w++)
    if (AIVehicle.GetWagonEngineType(state.vehicle, w) != state.wagon) return false;
  local left = { original = state.oldA, target = state.targetA,
      tiles = state.tilesA, stationId = state.stationAId };
  local right = { original = state.oldB, target = state.targetB,
      tiles = state.tilesB, stationId = state.stationBId };
  if (OpexRailLongV2StationBuilt(left.tiles, left.stationId)) left.tiles = [];
  if (OpexRailLongV2StationBuilt(right.tiles, right.stationId)) right.tiles = [];
  local quote = OpexRailLongV2Quote(left, right, state.depot);
  if (quote < 0) return false;
  local spent = (("costA" in state) ? state.costA : 0)
      + (("costB" in state) ? state.costB : 0);
  local gap = OpexInvestStallSourceGap(owner, line);
  local wagon = OpexV257Engine(state.wagon, line.cargo, true);
  local margin = OpexInvestStallPlatformMargin(line, state.vehicle, wagon,
      state.oldWagons, { engine = state.engine }, gap, max(state.quotedCost, spent + quote));
  OpexInvestStallFleetLog("recheck", line.lineId,
      "kind=platform phase=" + state.phase + " quote_remaining=" + quote
      + " accounted_spent=" + spent + " profit=" + (margin != null ? margin.profit : "unknown")
      + " production=" + gap.production + " rating=" + gap.rating
      + " capacity_month=" + gap.capacity + " cash=" + OpexAvailableCapital());
  return margin != null;
}

/* Appel depuis _expandRailLines APRES ses gardes de transaction, AVANT la
 * selection V284 classique. Les cooldowns sont entiers dans _v284State :
 * persist.nut doit sauver/reconcilier cet etat si INVEST_STALL est actif. */
function OpexInvestStallFleetSelect(owner, year)
{
  if (!INVEST_STALL || year < OPEX_START_YEAR + 4 || !OpexInvestStallReady()
      || owner == null || !SAVE_FULL_STATE || owner._catalog == null
      || owner._lines == null || owner._v257Pending != null
      || owner._v271Pending != null || owner._railExpansion != null) return false;
  if (owner._railLongV2Pending != null || owner._railLongV3UpgradePending != null) return true;
  if (V233_LONG_GOOD > 0 && V233L_STATE != null && V233L_STATE.pending != null)
    return false;
  if (OpexV284Busy(owner)) return true;
  if (owner._railSearch != null && owner._railSearch.kind == "upgrade") return false;
  if (owner._v284State == null)
    owner._v284State = { nextDate = 0, dates = {}, loops = {}, pending = null };
  local state = owner._v284State;
  local now = AIDate.GetCurrentDate();
  if (("investStallNextDate" in state) && now < state.investStallNextDate) return false;
  state.rawset("investStallNextDate", now + 30);
  if (!("investStallDates" in state) || state.investStallDates == null)
    state.rawset("investStallDates", {});

  local best = null;
  foreach (line in owner._lines) {
    if (OpexRailLongV3MultiLine(line)) continue;
    if (line == null || !("lineId" in line) || !("mode" in line)
        || line.mode != "rail" || !("kind" in line) || line.kind != "freight")
      continue;
    local gap = OpexInvestStallSourceGap(owner, line);
    if (!gap.ok) {
      OpexInvestStallFleetLog("screen", line.lineId, "ok=0 reason=" + gap.reason);
      continue;
    }
    if (!("platformLength" in line) || !("depot" in line)
        || !("distance" in line) || !("vehicles" in line) || line.vehicles == null
        || line.vehicles.len() != 1 || !("trains" in line) || line.trains != 1
        || OpexV163Wagons2(line) > 0
        || (("v271Tandem" in line) && line.v271Tandem)) {
      OpexInvestStallFleetLog("skip", line.lineId, "reason=unsupported_consist");
      continue;
    }
    if ((line.lineId in state.investStallDates)
        && now < state.investStallDates[line.lineId]) continue;
    local vehicle = line.vehicles[0];
    if (line.depot == null || !AIRail.IsRailDepotTile(line.depot)
        || !AIVehicle.IsValidVehicle(vehicle)
        || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_RAIL
        || (owner._vehiclesToRetire != null && (vehicle in owner._vehiclesToRetire))) {
      OpexInvestStallFleetLog("skip", line.lineId, "reason=vehicle_or_depot");
      continue;
    }
    local oldWagons = AIVehicle.GetNumWagons(vehicle) - 1;
    if (oldWagons < 1 || AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle)) > 0)
      continue;
    local wagonId = AIVehicle.GetWagonEngineType(vehicle, 1);
    if (!AIEngine.IsWagon(wagonId) || !AIEngine.IsBuildable(wagonId)
        || AIEngine.GetCargoType(wagonId) != line.cargo) continue;
    local homogeneous = true;
    for (local w = 1; w <= oldWagons; w++)
      if (AIVehicle.GetWagonEngineType(vehicle, w) != wagonId) homogeneous = false;
    if (!homogeneous) continue;
    local wagon = OpexV257Engine(wagonId, line.cargo, true);
    if (wagon == null || wagon.capacity <= 0) continue;
    local limit = OpexV284Limit(line);
    local atLimit = oldWagons >= OpexRailNominalMaxWagons(limit)
        || AIVehicle.GetLength(vehicle) + 8 > limit * 16;
    local equipment = OpexV284Equipment(line, vehicle, wagon,
        oldWagons + 1, false, gap.waiting);
    local extension = null;
    if (atLimit) {
      extension = OpexInvestStallPlatformPlan(owner, line, vehicle, wagon,
          oldWagons, equipment, gap);
      if (extension == null) {
        OpexInvestStallFleetLog("skip", line.lineId,
            "reason=at_limit_train_uncertified double_track="
            + ((("doubleTrack" in line) && line.doubleTrack == 1) ? 1 : 0)
            + " train_certified=" + (OpexInvestStallFleetTrainCertified(line) ? 1 : 0));
        continue;
      }
    }
    local margin = extension != null ? extension.margin
        : OpexInvestStallFleetMargin(line, vehicle, wagon, oldWagons, equipment, gap);
    if (margin == null) {
      OpexInvestStallFleetLog("skip", line.lineId,
          "reason=nonpositive_margin_or_traction production=" + gap.production
          + " capacity_month=" + gap.capacity + " rating=" + gap.rating);
      continue;
    }
    OpexInvestStallFleetLog("screen", line.lineId,
        "ok=1 action=" + (extension != null ? "platform" : "wagon")
        + " profit=" + margin.profit + " cost=" + margin.cost
        + " monthly_gain=" + margin.monthly + " pct=" + gap.pct);
    if (best == null || margin.score > best.margin.score)
      best = { line = line, vehicle = vehicle, wagon = wagon,
          oldWagons = oldWagons, equipment = equipment, margin = margin, gap = gap,
          extension = extension };
  }
  if (best == null) return false;

  local line = best.line;
  state.investStallDates.rawset(line.lineId, now + 90);
  if (best.extension != null) {
    local ext = best.extension;
    OpexRailLongV2Begin(owner, line, ext.planA, ext.planB, ext.target, ext.quote,
        { investStall = true, engine = best.equipment.engine,
          wagon = best.wagon.id, oldWagons = best.oldWagons });
    OpexInvestStallFleetLog("pick", line.lineId,
        "kind=platform len_a=" + line.platformA.length + " len_b=" + line.platformB.length
        + " target=" + ext.target + " quote=" + ext.quote
        + " total_cost=" + best.margin.cost + " profit=" + best.margin.profit
        + " monthly_gain=" + best.margin.monthly + " cash=" + OpexAvailableCapital()
        + " txn=" + line.lineId + "_" + best.vehicle + "_" + now);
    return true;
  }
  local waitDays = (2.0 * line.distance / (0.036 * best.equipment.speed)).tointeger() + 60;
  if (waitDays < 120) waitDays = 120;
  if (waitDays > 730) waitDays = 730;
  state.pending = {
    lineId = line.lineId, vehicle = best.vehicle, newVehicle = -1,
    engine = best.equipment.engine, wagon = best.wagon.id, wagons = best.oldWagons + 1,
    oldWagons = best.oldWagons, add = false, loopPlan = null,
    speedMilli = (best.equipment.speed * 1000).tointeger(),
    oldSpeedMilli = (best.equipment.oldSpeed * 1000).tointeger(),
    phase = "approach", deadline = now + waitDays, before = null,
    depot = line.depot, waiting = best.gap.waiting, cashBefore = 0,
    investStall = true, traceStart = now
  };
  OpexInvestStallFleetLog("pick", line.lineId,
      "kind=wagon old_wagons=" + best.oldWagons + " new_wagons=" + (best.oldWagons + 1)
      + " profit=" + best.margin.profit + " cost=" + best.margin.cost
      + " production=" + best.gap.production + " capacity_month=" + best.gap.capacity
      + " txn=" + OpexInvestStallTraceId(state.pending));
  return true;
}
