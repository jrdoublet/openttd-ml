/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexC50ResetNonExpansionLedger()
{
  C50_NON_EXPANSION_LEDGER = {
    air = {
      want_sum = 0,
      ref_Y = 0,
      ref_V = 0,
      ref_D = 0,
      ref_L = 0,
      ref_C = 0,
      ref_S = 0,
      ref_W = 0,
      ref_M = 0,
      ref_X = 0,
      ref_R = 0
    },
    rail = {
      cash_refused = 0,
      prep_failed = 0,
      upgrade_failed = 0,
      second_built = 0,
      double_built = 0
    },
    road = {
      physical_cap_hit = 0,
      congestion_hit = 0,
      no_demand = 0,
      loss_hit = 0,
      cash_refused = 0,
      other_refused = 0,
      refill_built = 0
    }
  };
}
function OpexSign(anchor, name)
{
  if (!DEBUG_SIGNS) return;
  if (name != null && name.len() > 31) name = name.slice(0, 31);
  AISign.BuildSign(anchor, name);
}
/* V88 : evenements de chaine de biens, sous decision_log ou probe_events (moins perturbant). */
function OpexV88Log(kind, fields)
{
  if (!DECISION_LOG && !C56_TASK_TRACE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexDecide(kind, fields)
{
  local date = AIDate.GetCurrentDate();
  if (_currentTaskName != null && !_currentTaskLogged && kind != "TASK") {
    _currentTaskLogged = true;
    local cur = _currentTaskName;
    _currentTaskName = null;
    OpexDecide("TASK", "name=" + cur);
    _currentTaskName = cur;
  }
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* B9/G4 : gate dedie au diagnostic catchment. Ne pas reutiliser DECISION_LOG :
 * il instrumente toute l'IA et son cout a deja ete mesure comme perturbant. */
function OpexAirCatchmentLog(kind, fields)
{
  if (!AIR_CATCHMENT_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}

/* C117 : debit AIR reel reconstruit passivement depuis les deux ordres A<->B. */
function OpexC117Log(fields)
{
  if (!C117_AIR_THROUGHPUT_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
      + AIDate.GetDayOfMonth(date) + " C117_AIR_THROUGHPUT " + fields);
}

function OpexC121FirstLiveLog(fields)
{
  if (!C121_AIR_FIRST_LIVE_SHADOW) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
      + AIDate.GetDayOfMonth(date) + " C121_FIRST_LIVE " + fields);
}

function OpexC121HubDelayLog(fields)
{
  if (!C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
      + AIDate.GetDayOfMonth(date) + " C121_HUB_DELAY " + fields);
}

/* C121 : physique C117 mise en cache au changement de moteur. Le calcul couteux
 * (vitesse/type aeroport) ne doit pas etre refait a chaque transition d'ordre. */
function OpexC121ProbePhysicalOneWay(line, engine)
{
  if (line == null || !AIEngine.IsValidEngine(engine)) return -1.0;
  local distance = ("distance" in line) ? line.distance : 0;
  if (distance <= 0 && ("stationA" in line) && ("stationB" in line)
      && AIMap.IsValidTile(line.stationA) && AIMap.IsValidTile(line.stationB)) {
    distance = OpexFlightDistance(line.stationA, line.stationB);
  }
  if (distance <= 0) return -1.0;
  local typeA = (("stationA" in line) && AIAirport.IsAirportTile(line.stationA))
      ? AIAirport.GetAirportType(line.stationA) : AIAirport.AT_SMALL;
  local typeB = (("stationB" in line) && AIAirport.IsAirportTile(line.stationB))
      ? AIAirport.GetAirportType(line.stationB) : AIAirport.AT_SMALL;
  local physical = OpexC121PhysicalOneWayDays(distance, engine, typeA, typeB);
  return physical != null ? physical.oneWayDays : -1.0;
}

/* C121 : fusion d'un lot de residus deja mesures par C117. Les residus restent
 * signes jusqu'a la publication pour ne pas biaiser la quantification a 2 jours. */
function OpexC121HubDelayObserveBatch(stationId, residualSum, residualSq, residualN,
                                      windowStart, now)
{
  if ((!C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS)
      || !AIStation.IsValidStation(stationId) || residualN <= 0) return null;
  local state = (stationId in C121_AIR_HUB_DELAY_STATE) ? C121_AIR_HUB_DELAY_STATE[stationId] : null;
  if (state == null) {
    state = {
      days = 0.0, rawDays = 0.0, variance = 0.0,
      observations = 0, lastWindowN = 0, lastUpdate = -1,
      windowStart = windowStart, windowSum = 0.0, windowSq = 0.0, windowN = 0,
    };
    C121_AIR_HUB_DELAY_STATE.rawset(stationId, state);
  }
  local published = null;
  if (state.windowN > 0 && now - state.windowStart >= C121_AIR_HUB_DELAY_WINDOW_DAYS) {
    local n = state.windowN;
    local mean = state.windowSum / n.tofloat();
    local variance = state.windowSq / n.tofloat() - mean * mean;
    if (variance < 0.0) variance = 0.0;
    if (n >= C121_AIR_HUB_DELAY_MIN_OBS) {
      state.rawDays = mean;
      state.days = mean > 0.0 ? mean : 0.0;
      state.variance = variance;
      state.lastWindowN = n;
      state.lastUpdate = now;
      if (C121_CATALOG_INCREMENTAL) C121_CATALOG_HUB_LEARN_REV.rawset(stationId,
          (stationId in C121_CATALOG_HUB_LEARN_REV
              ? C121_CATALOG_HUB_LEARN_REV[stationId] : 0) + 1);
      published = {
        station = stationId, days = state.days, rawDays = mean,
        variance = variance, windowN = n, observations = state.observations,
        lastUpdate = now,
      };
    }
    state.windowStart = now;
    state.windowSum = 0.0;
    state.windowSq = 0.0;
    state.windowN = 0;
  }
  state.windowSum += residualSum;
  state.windowSq += residualSq;
  state.windowN += residualN;
  state.observations += residualN;
  return published;
}

function OpexC121HubDelayFlushLine(line, state)
{
  if ((!C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS) || line == null || state == null) return;
  local totalN = state.hubResidualAN + state.hubResidualBN;
  if (totalN <= 0) return;
  local tick0 = AIController.GetTick();
  local ops0 = AIController.GetOpsTillSuspend();
  local stationA = OpexAirLineStationId(line, 0);
  local stationB = OpexAirLineStationId(line, 1);
  local publishedA = OpexC121HubDelayObserveBatch(
      stationA, state.hubResidualASum, state.hubResidualASq, state.hubResidualAN,
      state.startDate, state.lastDate);
  local publishedB = OpexC121HubDelayObserveBatch(
      stationB, state.hubResidualBSum, state.hubResidualBSq, state.hubResidualBN,
      state.startDate, state.lastDate);
  C121_AIR_HUB_DELAY_UPDATE_OPS += OpexAirCalcDeltaOps(tick0, ops0);
  C121_AIR_HUB_DELAY_UPDATE_SAMPLES += totalN;
  foreach (published in [publishedA, publishedB]) {
    if (published == null) continue;
    OpexC121HubDelayLog("station=" + published.station
        + " days=" + published.days + " raw_days=" + published.rawDays
        + " window_n=" + published.windowN
        + " observations=" + published.observations
        + " variance=" + published.variance
        + " last_update=" + published.lastUpdate
        + " update_ops_total=" + C121_AIR_HUB_DELAY_UPDATE_OPS
        + " update_samples=" + C121_AIR_HUB_DELAY_UPDATE_SAMPLES
        + " update_ops_mean=" + (C121_AIR_HUB_DELAY_UPDATE_SAMPLES > 0
            ? C121_AIR_HUB_DELAY_UPDATE_OPS.tofloat()
                / C121_AIR_HUB_DELAY_UPDATE_SAMPLES.tofloat() : 0.0));
  }
}

function OpexC117NewLineState(bucket, startDate)
{
  return {
    bucket = bucket, startDate = startDate, lastDate = startDate,
    pax = 0, seatLegs = 0, mail = 0, mailSeatLegs = 0,
    paxA = 0, seatLegsA = 0, mailA = 0, mailSeatLegsA = 0,
    paxB = 0, seatLegsB = 0, mailB = 0, mailSeatLegsB = 0,
    trips = 0, tripsA = 0, tripsB = 0,
    legDays = 0, legDaysN = 0, legDaysMin = -1, legDaysMax = 0,
    hubResidualASum = 0.0, hubResidualASq = 0.0, hubResidualAN = 0,
    hubResidualBSum = 0.0, hubResidualBSq = 0.0, hubResidualBN = 0,
    profit = 0, runEst = 0.0,
    samples = 0, liveSum = 0, capSum = 0,
    waitASum = 0, waitAN = 0, waitBSum = 0, waitBN = 0,
    ratingASum = 0, ratingAN = 0, ratingBSum = 0, ratingBN = 0,
    lastLive = 0, lastCap = 0, lastEngine = -1, engineChanges = 0,
    mixedEngineSamples = 0, invalidOrderSamples = 0, unobservedTransitions = 0
  };
}

function OpexC121FirstLiveAggregate(history, count)
{
  if (history == null || count <= 0 || history.len() < count) return null;
  local start = history.len() - count;
  local days = 0;
  local trips = 0;
  local tripsA = 0;
  local tripsB = 0;
  local profit = 0;
  local pax = 0;
  local seats = 0;
  local waitASum = 0;
  local waitAN = 0;
  local waitBSum = 0;
  local waitBN = 0;
  for (local i = start; i < history.len(); i++) {
    local w = history[i];
    days += w.days;
    trips += w.trips;
    tripsA += w.tripsA;
    tripsB += w.tripsB;
    profit += w.profit;
    pax += w.pax;
    seats += w.seats;
    waitASum += w.waitASum;
    waitAN += w.waitAN;
    waitBSum += w.waitBSum;
    waitBN += w.waitBN;
  }
  local load = seats > 0 ? pax.tofloat() / seats.tofloat() : -1.0;
  local waitA = waitAN > 0 ? waitASum.tofloat() / waitAN.tofloat() : -1.0;
  local waitB = waitBN > 0 ? waitBSum.tofloat() / waitBN.tofloat() : -1.0;
  local cap = history[history.len() - 1].cap;
  local maxWait = waitA > waitB ? waitA : waitB;
  local waitNorm = cap > 0 && maxWait >= 0.0 ? maxWait / cap.tofloat() : -1.0;
  return {
    days = days, trips = trips, tripsA = tripsA, tripsB = tripsB,
    profit = profit,
    profitPm = days > 0 ? profit.tofloat() * 30.4 / days.tofloat() : 0.0,
    load = load, waitA = waitA, waitB = waitB, waitNorm = waitNorm,
    cap = cap,
  };
}

/* C121 cadence : reutilise les fenetres mensuelles deja produites par C117.
 * Aucun scan vehicule supplementaire, aucune lecture par le portefeuille et
 * aucune mutation de ligne : uniquement trois petits snapshots par LineID. */
function OpexC121FirstLiveObserve(line, state, ageDays)
{
  if ((!C121_AIR_FIRST_LIVE_SHADOW && !C121_AIR_FIRST_LIVE_GROWTH)
      || line == null || state == null
      || !("lineId" in line)) return;
  local tick0 = AIController.GetTick();
  local ops0 = AIController.GetOpsTillSuspend();
  local key = line.lineId;
  if (state.lastLive != 1 || ageDays < 0 || ageDays > 365
      || ("lastAirFleetYear" in line)) {
    if (key in C121_AIR_FIRST_LIVE_STATE) delete C121_AIR_FIRST_LIVE_STATE[key];
    return;
  }
  local targetN = ("c121TargetPlanes" in line) ? line.c121TargetPlanes : -1;
  if (targetN >= 0 && targetN <= 1) {
    if (key in C121_AIR_FIRST_LIVE_STATE) delete C121_AIR_FIRST_LIVE_STATE[key];
    return;
  }

  local holder = (key in C121_AIR_FIRST_LIVE_STATE)
      ? C121_AIR_FIRST_LIVE_STATE[key] : { history = [] };
  holder.history.append({
    date = state.lastDate,
    days = state.lastDate - state.startDate > 0 ? state.lastDate - state.startDate : 1,
    trips = state.trips, tripsA = state.tripsA, tripsB = state.tripsB,
    profit = state.profit, pax = state.pax, seats = state.seatLegs,
    waitASum = state.waitASum, waitAN = state.waitAN,
    waitBSum = state.waitBSum, waitBN = state.waitBN,
    cap = state.lastCap,
  });
  while (holder.history.len() > 3) holder.history.remove(0);
  C121_AIR_FIRST_LIVE_STATE.rawset(key, holder);

  if (ageDays < 60) return;
  local r60 = OpexC121FirstLiveAggregate(holder.history, 2);
  local r90 = OpexC121FirstLiveAggregate(holder.history, 3);
  local balanced60 = r60 != null && r60.days >= 45 && r60.trips >= 2
      && r60.profit > 0 && (r60.load >= 0.40 || r60.waitNorm >= 0.50);
  local balanced90 = r90 != null && r90.days >= 50 && r90.trips >= 2
      && r90.profit > 0 && (r90.load >= 0.40 || r90.waitNorm >= 0.50);
  local strict90 = ageDays >= 75 && r90 != null && r90.days >= 60 && r90.trips >= 2
      && r90.tripsA >= 1 && r90.tripsB >= 1 && r90.profit > 0
      && (r90.load >= 0.55 || r90.waitNorm >= 0.75);
  local dual90 = r90 != null && r90.days >= 50 && r90.trips >= 2
      && r90.profit > 0 && r90.load >= 0.30 && r90.waitNorm >= 0.25;
  if ("balanced90" in holder) holder.balanced90 = balanced90;
  else holder.balanced90 <- balanced90;
  if ("lastEvidenceDate" in holder) holder.lastEvidenceDate = state.lastDate;
  else holder.lastEvidenceDate <- state.lastDate;
  C121_AIR_FIRST_LIVE_STATE.rawset(key, holder);
  local shadowOps = OpexAirCalcDeltaOps(tick0, ops0);
  C121_AIR_FIRST_LIVE_OPS += shadowOps;
  C121_AIR_FIRST_LIVE_SAMPLES++;

  OpexC121FirstLiveLog("line=" + line.lineId
      + " arm=" + (("c117Arm" in line) ? line.c117Arm : "unknown")
      + " age_days=" + ageDays + " target_n=" + targetN
      + " cold_marginal_profit=" + (("c121MarginalProfit" in line) ? line.c121MarginalProfit : -1)
      + " marginal_samples=" + (("c121MarginalSamples" in line) ? line.c121MarginalSamples : -1)
      + " last_profit=" + (("lastProfit" in line) ? line.lastProfit : -1)
      + " r60_days=" + (r60 != null ? r60.days : 0)
      + " r60_trips=" + (r60 != null ? r60.trips : 0)
      + " r60_profit_pm=" + (r60 != null ? r60.profitPm : 0.0)
      + " r60_load=" + (r60 != null ? r60.load : -1.0)
      + " r60_wait_norm=" + (r60 != null ? r60.waitNorm : -1.0)
      + " r90_days=" + (r90 != null ? r90.days : 0)
      + " r90_trips=" + (r90 != null ? r90.trips : 0)
      + " r90_trips_a=" + (r90 != null ? r90.tripsA : 0)
      + " r90_trips_b=" + (r90 != null ? r90.tripsB : 0)
      + " r90_profit_pm=" + (r90 != null ? r90.profitPm : 0.0)
      + " r90_load=" + (r90 != null ? r90.load : -1.0)
      + " r90_wait_norm=" + (r90 != null ? r90.waitNorm : -1.0)
      + " rule_bal60=" + (balanced60 ? 1 : 0)
      + " rule_bal90=" + (balanced90 ? 1 : 0)
      + " rule_strict90=" + (strict90 ? 1 : 0)
      + " rule_dual90=" + (dual90 ? 1 : 0)
      + " shadow_ops=" + shadowOps
      + " shadow_ops_total=" + C121_AIR_FIRST_LIVE_OPS
      + " shadow_samples=" + C121_AIR_FIRST_LIVE_SAMPLES
      + " shadow_ops_mean=" + (C121_AIR_FIRST_LIVE_SAMPLES > 0
          ? C121_AIR_FIRST_LIVE_OPS.tofloat() / C121_AIR_FIRST_LIVE_SAMPLES.tofloat() : 0.0));
}

function OpexC121FirstLiveBalanced90(line)
{
  if (line == null || !("lineId" in line)) return false;
  local key = line.lineId;
  if (!(key in C121_AIR_FIRST_LIVE_STATE)) return false;
  local holder = C121_AIR_FIRST_LIVE_STATE[key];
  return ("balanced90" in holder) && holder.balanced90;
}

function OpexC117FlushLine(line, state)
{
  if (state == null || state.samples <= 0) return;
  OpexC121HubDelayFlushLine(line, state);
  local days = state.lastDate - state.startDate;
  if (days <= 0) days = 1;
  local paxPm = state.pax.tofloat() * 30.4 / days.tofloat();
  local seatsPm = state.seatLegs.tofloat() * 30.4 / days.tofloat();
  local loadFactor = state.seatLegs > 0 ? state.pax.tofloat() / state.seatLegs.tofloat() : -1.0;
  local mailPm = state.mail.tofloat() * 30.4 / days.tofloat();
  local mailSeatsPm = state.mailSeatLegs.tofloat() * 30.4 / days.tofloat();
  local mailLoadFactor = state.mailSeatLegs > 0
      ? state.mail.tofloat() / state.mailSeatLegs.tofloat() : -1.0;
  local headway = state.trips > 0 ? (2.0 * days.tofloat()) / state.trips.tofloat() : -1.0;
  local profitPm = state.profit.tofloat() * 30.4 / days.tofloat();
  local runPm = state.runEst * 30.4 / days.tofloat();
  local revenuePm = profitPm + runPm;
  local liveAvg = state.liveSum.tofloat() / state.samples.tofloat();
  local capAvg = state.capSum.tofloat() / state.samples.tofloat();
  local waitA = state.waitAN > 0 ? state.waitASum.tofloat() / state.waitAN.tofloat() : -1.0;
  local waitB = state.waitBN > 0 ? state.waitBSum.tofloat() / state.waitBN.tofloat() : -1.0;
  local ratingA = state.ratingAN > 0 ? state.ratingASum.tofloat() / state.ratingAN.tofloat() : -1.0;
  local ratingB = state.ratingBN > 0 ? state.ratingBSum.tofloat() / state.ratingBN.tofloat() : -1.0;
  local ageDays = ("buildDate" in line) ? (state.lastDate - line.buildDate) : -1;
  local capital = ("actualCapital" in line) ? line.actualCapital : -1;
  local profitCapitalPm = capital > 0 ? profitPm / capital.tofloat() : -1.0;
  OpexC121FirstLiveObserve(line, state, ageDays);
  /* C119 diagnostic passif : distance Manhattan disponible avant toute decision. */
  local paymentDistance = -1;
  local airportTypeA = -1;
  local airportTypeB = -1;
  local airportSpanA = -1;
  local airportSpanB = -1;
  if (("stationA" in line) && ("stationB" in line)
      && AIMap.IsValidTile(line.stationA) && AIMap.IsValidTile(line.stationB)) {
    paymentDistance = AIMap.DistanceManhattan(line.stationA, line.stationB);
    if (AIAirport.IsAirportTile(line.stationA)) {
      airportTypeA = AIAirport.GetAirportType(line.stationA);
      airportSpanA = OpexAirportStationDateSpan(airportTypeA);
    }
    if (AIAirport.IsAirportTile(line.stationB)) {
      airportTypeB = AIAirport.GetAirportType(line.stationB);
      airportSpanB = OpexAirportStationDateSpan(airportTypeB);
    }
  }
  local c121StationA = OpexAirLineStationId(line, 0);
  local c121StationB = OpexAirLineStationId(line, 1);
  local c121HubA = OpexC121HubDelayState(c121StationA);
  local c121HubB = OpexC121HubDelayState(c121StationB);
  local c121DelayA = c121HubA != null ? c121HubA.days : 0.0;
  local c121DelayB = c121HubB != null ? c121HubB.days : 0.0;
  local c121PhysicalOneWay = OpexC121ProbePhysicalOneWay(line, state.lastEngine);
  local c121AdaptedOneWay = c121PhysicalOneWay > 0.0
      ? c121PhysicalOneWay + (c121DelayA + c121DelayB) / 2.0 : -1.0;

  OpexC117Log("line=" + line.lineId
      + " arm=" + (("c117Arm" in line) ? line.c117Arm : "unknown")
      + " age_bucket=" + state.bucket + " age_days=" + ageDays
      + " period_days=" + days + " sample_days=" + C117_AIR_SAMPLE_DAYS
      + " build_date=" + (("buildDate" in line) ? line.buildDate : -1)
      + " distance=" + (("distance" in line) ? line.distance : -1)
      + " payment_distance=" + paymentDistance
      + " airport_type_a=" + airportTypeA + " airport_type_b=" + airportTypeB
      + " airport_span_a=" + airportSpanA + " airport_span_b=" + airportSpanB
      + " build_engine=" + (("planeId" in line) ? line.planeId : -1)
      + " engine=" + state.lastEngine + " engine_changes=" + state.engineChanges
      + " mixed_engine_samples=" + state.mixedEngineSamples
      + " base_monthly=" + (("airMonthlyPax" in line) ? line.airMonthlyPax : -1)
      + " shadow_monthly=" + (("c117ShadowMonthly" in line) ? line.c117ShadowMonthly : -1)
      + " pred_carried=" + (("predCarried" in line) ? line.predCarried : -1)
      + " pred_revenue_y=" + (("predRevenue" in line) ? line.predRevenue : -1)
      + " pred_profit_y=" + (("predicted" in line) ? line.predicted : -1)
      + " pred_running_y=" + (("predRunning" in line) ? line.predRunning : -1)
      + " pred_vehicle_running_y=" + (("predVehicleRunning" in line) ? line.predVehicleRunning : -1)
      + " pred_amort_y=" + (("predAmort" in line) ? line.predAmort : -1)
      + " pred_n=" + (("predTrains" in line) ? line.predTrains : -1)
      + " pred_oneway_days=" + (("predOneWayDays" in line) ? line.predOneWayDays : -1)
      + " build_capacity=" + (("planeCapacity" in line) ? line.planeCapacity : -1)
      + " c121_pax_cap=" + (("c121PaxCapacity" in line) ? line.c121PaxCapacity : -1)
      + " c121_mail_cap=" + (("c121MailCapacity" in line) ? line.c121MailCapacity : -1)
      + " c121_actual_pax_pm=" + (("c121ActualCarriedPax" in line) ? line.c121ActualCarriedPax : -1)
      + " c121_actual_mail_pm=" + (("c121ActualCarriedMail" in line) ? line.c121ActualCarriedMail : -1)
      + " c121_actual_total_pm=" + (("c121ActualCarried" in line) ? line.c121ActualCarried : -1)
      + " c121_actual_revenue_y=" + (("c121ActualRevenueAnnual" in line) ? line.c121ActualRevenueAnnual : -1)
      + " c121_actual_profit_y=" + (("c121ActualProfitAnnual" in line) ? line.c121ActualProfitAnnual : -1)
      + " c121_actual_running_y=" + (("c121ActualRunningAnnual" in line) ? line.c121ActualRunningAnnual : -1)
      + " c121_actual_vehicle_running_y=" + (("c121ActualVehicleRunningAnnual" in line) ? line.c121ActualVehicleRunningAnnual : -1)
      + " c121_actual_amort_y=" + (("c121ActualAmortAnnual" in line) ? line.c121ActualAmortAnnual : -1)
      + " c121_actual_n=" + (("c121ActualPlanes" in line) ? line.c121ActualPlanes : -1)
      + " c121_actual_oneway_days=" + (("c121ActualOneWayDays" in line) ? line.c121ActualOneWayDays : -1)
      + " c121_actual_headway_days=" + (("c121ActualHeadwayDays" in line) ? line.c121ActualHeadwayDays : -1)
      + " c121_actual_rating=" + (("c121ActualStationRating" in line) ? line.c121ActualStationRating : -1)
      + " c121_target_pax_pm=" + (("c121TargetCarriedPax" in line) ? line.c121TargetCarriedPax : -1)
      + " c121_target_mail_pm=" + (("c121TargetCarriedMail" in line) ? line.c121TargetCarriedMail : -1)
      + " c121_target_total_pm=" + (("c121TargetCarried" in line) ? line.c121TargetCarried : -1)
      + " c121_target_revenue_y=" + (("c121TargetRevenueAnnual" in line) ? line.c121TargetRevenueAnnual : -1)
      + " c121_target_profit_y=" + (("c121TargetProfitAnnual" in line) ? line.c121TargetProfitAnnual : -1)
      + " c121_target_n=" + (("c121TargetPlanes" in line) ? line.c121TargetPlanes : -1)
      + " capital=" + capital
      + " pax=" + state.pax + " pax_pm=" + paxPm
      + " seat_legs=" + state.seatLegs + " seats_pm=" + seatsPm
      + " load_factor=" + loadFactor
      + " mail=" + state.mail + " mail_pm=" + mailPm
      + " mail_seat_legs=" + state.mailSeatLegs + " mail_seats_pm=" + mailSeatsPm
      + " mail_load_factor=" + mailLoadFactor
      + " trips=" + state.trips + " trips_a=" + state.tripsA + " trips_b=" + state.tripsB
      + " pax_a=" + state.paxA + " seats_a=" + state.seatLegsA
      + " mail_a=" + state.mailA + " mail_seats_a=" + state.mailSeatLegsA
      + " pax_b=" + state.paxB + " seats_b=" + state.seatLegsB
      + " mail_b=" + state.mailB + " mail_seats_b=" + state.mailSeatLegsB
      + " headway_days=" + headway
      + " leg_days_n=" + state.legDaysN + " leg_days_sum=" + state.legDays
      + " leg_days_min=" + state.legDaysMin + " leg_days_max=" + state.legDaysMax
      + " c121_physical_oneway_days=" + c121PhysicalOneWay
      + " c121_hub_delay_a=" + c121DelayA + " c121_hub_delay_b=" + c121DelayB
      + " c121_hub_delay_n_a=" + (c121HubA != null ? c121HubA.lastWindowN : 0)
      + " c121_hub_delay_n_b=" + (c121HubB != null ? c121HubB.lastWindowN : 0)
      + " c121_adapted_oneway_days=" + c121AdaptedOneWay
      + " profit=" + state.profit + " profit_pm=" + profitPm
      + " run_est=" + state.runEst + " run_pm=" + runPm
      + " revenue_est_pm=" + revenuePm + " profit_capital_pm=" + profitCapitalPm
      + " samples=" + state.samples + " live_avg=" + liveAvg + " cap_avg=" + capAvg
      + " live_last=" + state.lastLive + " cap_last=" + state.lastCap
      + " wait_a=" + waitA + " wait_b=" + waitB
      + " rating_a=" + ratingA + " rating_b=" + ratingB
      + " invalid_order_samples=" + state.invalidOrderSamples
      + " unobserved_transitions=" + state.unobservedTransitions);
}

function OpexC117AirThroughputStep(lines, catalog)
{
  if ((!C117_AIR_THROUGHPUT_PROBE && !C121_AIR_ECONOMICS_SHADOW && !C121_AIR_ECONOMICS)
      || lines == null || catalog == null) return;
  local now = AIDate.GetCurrentDate();
  if (C117_AIR_LAST_DATE >= 0 && now - C117_AIR_LAST_DATE < C117_AIR_SAMPLE_DAYS) return;
  C117_AIR_LAST_DATE = now;
  local nowYear = AIDate.GetYear(now);

  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "air"
        || !("lineId" in line) || !("buildDate" in line)) continue;
    local ageDays = now - line.buildDate;
    if (ageDays < 0) continue;
    local bucket = ageDays / 30;
    local lineKey = line.lineId;
    local state = (lineKey in C117_AIR_LINE_STATE) ? C117_AIR_LINE_STATE[lineKey] : null;
    if (state == null) {
      state = OpexC117NewLineState(bucket, now);
      C117_AIR_LINE_STATE.rawset(lineKey, state);
    } else if (state.bucket != bucket) {
      local bridgeStart = state.lastDate;
      OpexC117FlushLine(line, state);
      state = OpexC117NewLineState(bucket, bridgeStart);
      C117_AIR_LINE_STATE.rawset(lineKey, state);
    }

    local live = 0;
    local totalCap = 0;
    local firstEngine = -1;
    local mixedEngine = false;
    if (("vehicles" in line) && line.vehicles != null) {
      foreach (v in line.vehicles) {
        if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
        live++;
        local engine = AIVehicle.GetEngineType(v);
        if (firstEngine < 0) firstEngine = engine;
        else if (engine != firstEngine) mixedEngine = true;
        local cap = AIVehicle.GetCapacity(v, line.cargo);
        if (cap < 0) cap = 0;
        totalCap += cap;
        local load = cap > 0 ? AIVehicle.GetCargoLoad(v, line.cargo) : 0;
        local mailCap = 0;
        local mailLoad = 0;
        if (("mailCargo" in catalog) && catalog.mailCargo >= 0
            && AICargo.IsValidCargo(catalog.mailCargo)) {
          mailCap = AIVehicle.GetCapacity(v, catalog.mailCargo);
          if (mailCap < 0) mailCap = 0;
          mailLoad = mailCap > 0 ? AIVehicle.GetCargoLoad(v, catalog.mailCargo) : 0;
        }
        local inOrderList = AIOrder.IsCurrentOrderPartOfOrderList(v);
        local curOrder = inOrderList
            ? AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT) : AIOrder.ORDER_INVALID;
        local vehicleRunning = AIVehicle.GetState(v) == AIVehicle.VS_RUNNING;
        local thisProfit = AIVehicle.GetProfitThisYear(v);
        local vehicleState = (v in C117_AIR_VEHICLE_STATE) ? C117_AIR_VEHICLE_STATE[v] : null;
        if (vehicleState == null || vehicleState.lineId != line.lineId
            || vehicleState.engine != engine) {
          local c121PhysicalOneWay = (C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS)
              ? OpexC121ProbePhysicalOneWay(line, engine) : -1.0;
          C117_AIR_VEHICLE_STATE.rawset(v, {
            lineId = line.lineId, engine = engine, order = curOrder,
            legPaxMax = vehicleRunning ? load : 0, legCap = vehicleRunning ? cap : 0,
            legMailMax = vehicleRunning ? mailLoad : 0,
            legMailCap = vehicleRunning ? mailCap : 0,
            legMoving = vehicleRunning, legStartDate = now, seenTransition = false,
            c121PhysicalOneWay = c121PhysicalOneWay,
            profitYear = nowYear, profitThisYear = thisProfit, lastDate = now
          });
          continue;
        }

        local deltaDays = now - vehicleState.lastDate;
        if (deltaDays > 0) {
          local profitDelta = 0;
          if (vehicleState.profitYear == nowYear) {
            profitDelta = thisProfit - vehicleState.profitThisYear;
          } else if (vehicleState.profitYear + 1 == nowYear) {
            profitDelta = (AIVehicle.GetProfitLastYear(v) - vehicleState.profitThisYear) + thisProfit;
          }
          state.profit += profitDelta;
          state.runEst += AIVehicle.GetRunningCost(v).tofloat() * deltaDays.tofloat() / 365.25;
        }
        vehicleState.profitYear = nowYear;
        vehicleState.profitThisYear = thisProfit;
        vehicleState.lastDate = now;

        if (curOrder == AIOrder.ORDER_INVALID || curOrder < 0 || curOrder > 1) {
          state.invalidOrderSamples++;
          if (vehicleRunning) {
            vehicleState.legMoving = true;
            if (load > vehicleState.legPaxMax) vehicleState.legPaxMax = load;
            if (cap > vehicleState.legCap) vehicleState.legCap = cap;
            if (mailLoad > vehicleState.legMailMax) vehicleState.legMailMax = mailLoad;
            if (mailCap > vehicleState.legMailCap) vehicleState.legMailCap = mailCap;
          }
          continue;
        }
        if (vehicleState.order == AIOrder.ORDER_INVALID || vehicleState.order < 0
            || vehicleState.order > 1) {
          vehicleState.order = curOrder;
          vehicleState.legPaxMax = vehicleRunning ? load : 0;
          vehicleState.legCap = vehicleRunning ? cap : 0;
          vehicleState.legMailMax = vehicleRunning ? mailLoad : 0;
          vehicleState.legMailCap = vehicleRunning ? mailCap : 0;
          vehicleState.legMoving = vehicleRunning;
          vehicleState.legStartDate = now;
          vehicleState.seenTransition = false;
          continue;
        }
        if (curOrder == vehicleState.order) {
          if (vehicleRunning) {
            vehicleState.legMoving = true;
            if (load > vehicleState.legPaxMax) vehicleState.legPaxMax = load;
            if (cap > vehicleState.legCap) vehicleState.legCap = cap;
            if (mailLoad > vehicleState.legMailMax) vehicleState.legMailMax = mailLoad;
            if (mailCap > vehicleState.legMailCap) vehicleState.legMailCap = mailCap;
          }
          continue;
        }

        if (vehicleState.legMoving) {
          state.pax += vehicleState.legPaxMax;
          state.seatLegs += vehicleState.legCap;
          state.mail += vehicleState.legMailMax;
          state.mailSeatLegs += vehicleState.legMailCap;
          state.trips++;
          if (vehicleState.order == 0) {
            state.tripsA++;
            state.paxA += vehicleState.legPaxMax;
            state.seatLegsA += vehicleState.legCap;
            state.mailA += vehicleState.legMailMax;
            state.mailSeatLegsA += vehicleState.legMailCap;
          } else if (vehicleState.order == 1) {
            state.tripsB++;
            state.paxB += vehicleState.legPaxMax;
            state.seatLegsB += vehicleState.legCap;
            state.mailB += vehicleState.legMailMax;
            state.mailSeatLegsB += vehicleState.legMailCap;
          }
          if (vehicleState.seenTransition) {
            local legDays = now - vehicleState.legStartDate;
            if (legDays > 0) {
              state.legDays += legDays;
              state.legDaysN++;
              if (state.legDaysMin < 0 || legDays < state.legDaysMin) state.legDaysMin = legDays;
              if (legDays > state.legDaysMax) state.legDaysMax = legDays;
              local physical = ("c121PhysicalOneWay" in vehicleState)
                  ? vehicleState.c121PhysicalOneWay : -1.0;
              if ((C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) && physical > 0.0) {
                local residual = legDays.tofloat() - physical;
                if (vehicleState.order == 0) {
                  state.hubResidualASum += residual;
                  state.hubResidualASq += residual * residual;
                  state.hubResidualAN++;
                } else if (vehicleState.order == 1) {
                  state.hubResidualBSum += residual;
                  state.hubResidualBSq += residual * residual;
                  state.hubResidualBN++;
                }
              }
            }
          }
        } else {
          state.unobservedTransitions++;
        }
        vehicleState.order = curOrder;
        vehicleState.legPaxMax = vehicleRunning ? load : 0;
        vehicleState.legCap = vehicleRunning ? cap : 0;
        vehicleState.legMailMax = vehicleRunning ? mailLoad : 0;
        vehicleState.legMailCap = vehicleRunning ? mailCap : 0;
        vehicleState.legMoving = vehicleRunning;
        vehicleState.legStartDate = now;
        vehicleState.seenTransition = true;
      }
    }

    if (state.lastEngine >= 0 && firstEngine >= 0 && firstEngine != state.lastEngine) state.engineChanges++;
    if (firstEngine >= 0) state.lastEngine = firstEngine;
    if (mixedEngine) state.mixedEngineSamples++;
    state.samples++;
    state.liveSum += live;
    state.capSum += totalCap;
    state.lastLive = live;
    state.lastCap = totalCap;
    state.lastDate = now;

    local stationA = OpexAirLineStationId(line, 0);
    local stationB = OpexAirLineStationId(line, 1);
    if (AIStation.IsValidStation(stationA)) {
      local waitA = AIStation.GetCargoWaiting(stationA, line.cargo);
      if (waitA >= 0) { state.waitASum += waitA; state.waitAN++; }
      local ratingA = AIStation.GetCargoRating(stationA, line.cargo);
      if (ratingA >= 0) { state.ratingASum += ratingA; state.ratingAN++; }
    }
    if (AIStation.IsValidStation(stationB)) {
      local waitB = AIStation.GetCargoWaiting(stationB, line.cargo);
      if (waitB >= 0) { state.waitBSum += waitB; state.waitBN++; }
      local ratingB = AIStation.GetCargoRating(stationB, line.cargo);
      if (ratingB >= 0) { state.ratingBSum += ratingB; state.ratingBN++; }
    }
  }
}
/* C39.0 : le journal de la sonde est indépendant de DECISION_LOG. Ce dernier instrumente toute
 * l'IA et change son budget d'opcodes ; C39 doit pouvoir observer le seul routeur passif. */
function OpexC39Log(kind, fields)
{
  if (!C39_INVALIDATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* Une seule ligne par regeneration catalogue terminee. Le record reste sur la tache
 * pendant C78.4 ; Save/Load abandonne deja ce curseur et recommence la passe. */
function OpexCatalogCostNew(reason)
{
  return { reason = reason, path = "full", refreshOps = 0, engineRefreshOps = 0, engineChoices = 0,
    catalogTowns = 0, catalogIndustries = 0,
    modeRegenOps = 0, reselectOps = 0,
    railOps = 0, roadOps = 0,
    airOps = 0, waterOps = 0, assemblyOps = 0, selectionOps = 0,
    railCandidates = 0, roadCandidates = 0, waterPlans = 0,
    airPlans = 0, modeAlternatives = 0, considered = 0, selected = 0,
    airScans = 0, airTowns = 0, airCombos = 0, airPairs = 0,
    airHubSitePairs = 0, airHubHubPairs = 0,
    airSiteProbes = 0, airSites = 0, airSiteOps = 0, airEvalOps = 0,
    c121Calls = 0, c121DemandOps = 0, c121StaticOps = 0,
    c121ScanOps = 0, c121EngineEvals = 0, c121WinnerOps = 0,
    c121CacheHits = 0, c121Recomputed = 0, c121DirtyEngine = 0,
    c121DirtyTown = 0, c121DirtyStation = 0, c121DirtyLearning = 0,
    c121DirtyAge = 0, c121DirtyInput = 0, c121New = 0,
    c121Slices = 0, c121LastSliceOps = 0,
    c121MaxSliceOps = 0 };
}

function OpexProjectsCostLog(pcost, builtCount, stopReason)
{
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
      + AIDate.GetDayOfMonth(date) + " PROJECTS_COST build_ops=" + pcost.buildOps
      + " fleet_ops=" + pcost.fleetOps + " regen_ops=" + pcost.regenOps
      + " regen=" + pcost.regenKind + " built=" + builtCount
      + " stop=" + (stopReason != null ? stopReason : "none"));
}

function OpexCatalogCostLog(cost)
{
  local date = AIDate.GetCurrentDate();
  /* Sous-etapes disjointes ; les compteurs AIR/C121 ci-dessous sont inclus dans air_ops. */
  local total = cost.refreshOps + cost.railOps + cost.roadOps + cost.airOps
      + cost.waterOps + cost.assemblyOps + cost.selectionOps
      + cost.modeRegenOps + cost.reselectOps;
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
    + AIDate.GetDayOfMonth(date) + " CATALOG_COST reason=" + cost.reason
    + " total_ops=" + total
    + " path=" + cost.path + " mode_regen_ops=" + cost.modeRegenOps
    + " reselect_ops=" + cost.reselectOps
    + " refresh_ops=" + cost.refreshOps
    + " catalog_towns=" + cost.catalogTowns
    + " catalog_industries=" + cost.catalogIndustries
    + " engine_refresh_ops=" + cost.engineRefreshOps
    + " engine_choices=" + cost.engineChoices
    + " rail_ops=" + cost.railOps + " rail_candidates=" + cost.railCandidates
    + " road_ops=" + cost.roadOps + " road_candidates=" + cost.roadCandidates
    + " air_ops=" + cost.airOps + " air_plans=" + cost.airPlans
    + " water_ops=" + cost.waterOps + " water_plans=" + cost.waterPlans
    + " assembly_ops=" + cost.assemblyOps + " mode_alternatives=" + cost.modeAlternatives
    + " selection_ops=" + cost.selectionOps + " considered=" + cost.considered
    + " selected=" + cost.selected + " air_scans=" + cost.airScans
    + " air_towns=" + cost.airTowns + " air_combos=" + cost.airCombos
    + " air_new_pairs=" + cost.airPairs
    + " air_hub_site_pairs=" + cost.airHubSitePairs
    + " air_hub_hub_pairs=" + cost.airHubHubPairs
    + " air_site_probes=" + cost.airSiteProbes
    + " air_sites=" + cost.airSites + " air_site_ops=" + cost.airSiteOps
    + " air_eval_ops=" + cost.airEvalOps + " c121_calls=" + cost.c121Calls
    + " c121_demand_ops=" + cost.c121DemandOps
    + " c121_static_ops=" + cost.c121StaticOps
    + " c121_scan_ops=" + cost.c121ScanOps
    + " c121_engine_evals=" + cost.c121EngineEvals
    + " c121_winner_ops=" + cost.c121WinnerOps
    + " c121_cache_hits=" + cost.c121CacheHits
    + " c121_recomputed=" + cost.c121Recomputed
    + " c121_dirty_engine=" + cost.c121DirtyEngine
    + " c121_dirty_town=" + cost.c121DirtyTown
    + " c121_dirty_station=" + cost.c121DirtyStation
    + " c121_dirty_learning=" + cost.c121DirtyLearning
    + " c121_dirty_age=" + cost.c121DirtyAge
    + " c121_dirty_input=" + cost.c121DirtyInput
    + " c121_new=" + cost.c121New
    + " c121_slices=" + cost.c121Slices
    + " c121_last_slice_ops=" + cost.c121LastSliceOps
    + " c121_max_slice_ops=" + cost.c121MaxSliceOps);
}
function OpexCatalogCostSliceLog(cost, scan, sliceOps)
{
  if (!C121_CATALOG_INCREMENTAL || !CATALOG_COST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  local examined = cost.c121CacheHits + cost.c121Recomputed;
  local reusePct = examined > 0 ? cost.c121CacheHits * 100 / examined : 0;
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
    + AIDate.GetDayOfMonth(date) + " CATALOG_COST_SLICE"
    + " cache=" + C121_CATALOG_CACHE.len()
    + " hits=" + cost.c121CacheHits + " recalculated=" + cost.c121Recomputed
    + " reuse_pct=" + reusePct
    + " dirty_engine=" + cost.c121DirtyEngine + " dirty_town=" + cost.c121DirtyTown
    + " dirty_station=" + cost.c121DirtyStation + " dirty_learning=" + cost.c121DirtyLearning
    + " dirty_age=" + cost.c121DirtyAge
    + " dirty_input=" + cost.c121DirtyInput + " new=" + cost.c121New
    + " same_tick_slices=" + scan.tickSlices
    + " chained_slices=" + (scan.tickSlices - 1) + " slice_ops=" + sliceOps
    + " partial=" + (scan.published ? 1 : 0)
    + " partial_pending=" + (scan.partialPending ? 1 : 0)
    + " published_plans=" + scan.lastPublishedCount + " evaluated_plans=" + scan.plans.len());
}
/* C41.11 reste lisible sans activer le bus C39 : il mesure le scheduler historique lui-meme. */
function OpexC41SchedulerLog(kind, fields)
{
  if (!C41_SLACK_LEDGER && !C41_MONTHLY_BUSY_LEDGER
      && !C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C41.46 : sonde independante de la famille C41.11/13/14 -- son propre gate, comme les sondes
 * rail-lost ci-dessous. OpexC41SchedulerLog aurait silencieusement avale ces lignes tant qu'aucun
 * des trois autres flags n'est actif (piege trouve au premier smoke test). */
function OpexC41RailSliceLog(fields)
{
  if (!C41_RAIL_SLICE_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_SLICE_LEDGER " + fields);
}
/* C49 : gate dedie. Ne jamais reutiliser celui de C48/C39/C41 : armer seulement cette sonde
 * doit suffire a publier ses lignes. */
function OpexC49ScarcityLog(fields)
{
  if (!C49_SCARCITY_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C49_SCARCITY " + fields);
}
/* C69 : gate dedie sous probe_portfolio. */
function OpexC69Log(fields)
{
  if (!C69_BOTTLENECK_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C69_BOTTLENECK " + fields);
}
/* C78 etape 2 : journalisation passive sous probe_portfolio. */
function OpexC78Log(tag, fields)
{
  if (!C69_BOTTLENECK_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + tag + " " + fields);
}

function OpexC78CandidateLog(fields)
{
  OpexC78Log("C78_CAND", fields);
}

/* C78 : sonde dediee a la course aux deux slots aeroportuaires d'une ville.
 * AIStation ne permet pas d'inventorier directement les stations adverses. Le chemin fonctionnel
 * C77 utilise AITown.GetAllowedNoise()==1 sous station_noise_level=0 pour savoir qu'un des deux
 * slots est deja occupe ; le harnais shared garde l'inventaire/build_date AAA pour la chronologie.
 * Cette sonde publie l'etat du vivier AIR sans modifier decision ni cadence. */
function OpexC78SlotLog(fields)
{
  if (!C78_SLOT_INTERCEPT_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C78_SLOT " + fields);
}

function OpexC78AirPhysicalTown(site)
{
  if (site == null) return -1;
  if (("anchor" in site) && AIMap.IsValidTile(site.anchor)) {
    local townId = AITile.GetClosestTown(site.anchor);
    if (townId >= 0) return townId;
  }
  if (("town" in site) && site.town != null) {
    if (typeof site.town == "table" && ("id" in site.town)) return site.town.id;
    if (typeof site.town == "integer") return site.town;
  }
  return -1;
}

/* C83.1 : avec station_noise_level=0, la limite historique de deux aeroports
 * est portee par la ville de la tuile d'ancrage (ClosestTownFromTile dans
 * CmdBuildAirport), pas par la ville de bruit de l'emprise aeroportuaire. */
function OpexC78AirSlotTown(site, airportType)
{
  if (site == null) return -1;
  if (("anchor" in site) && AIMap.IsValidTile(site.anchor)) {
    local townId = AITile.GetClosestTown(site.anchor);
    if (townId >= 0) return townId;
  }
  if (("town" in site) && site.town != null) {
    if (typeof site.town == "table" && ("id" in site.town)) return site.town.id;
    if (typeof site.town == "integer") return site.town;
  }
  return -1;
}

function OpexC78FundedRank(projects, project)
{
  if (projects == null || !("best" in projects) || projects.best == null) return -1;
  local key = OpexProjectAttemptKey(project);
  for (local i = 0; i < projects.best.len(); i++) {
    local fundedProject = projects.best[i];
    if (fundedProject != null && OpexProjectAttemptKey(fundedProject) == key) return i;
  }
  return -1;
}

function OpexAI::_c78SlotOnProjectsPass()
{
  if (!C78_SLOT_INTERCEPT_PROBE) return;
  C78_SLOT_PASS_COUNTER++;
  local passId = C78_SLOT_PASS_COUNTER;
  local cycle = this._taskCycle;
  local tick = AIController.GetTick();
  local available = OpexAvailableCapital();
  local airCandidates = 0;
  local affordable = 0;
  local funded = 0;

  if (this._projects == null || !("candidateGroups" in this._projects)
      || this._projects.candidateGroups == null) {
    OpexC78SlotLog("phase=projects_pass pass=" + passId
        + " cycle=" + cycle + " tick=" + tick
        + " state=no_projects air_candidates=0 affordable=0 funded=0"
        + " available=" + available);
    return;
  }

  foreach (groupKey, entry in this._projects.candidateGroups) {
    local list = (typeof entry == "array") ? entry : [entry];
    foreach (project in list) {
      if (project == null || !("mode" in project) || project.mode != "air"
          || !("payload" in project) || project.payload == null) continue;
      local plan = project.payload;
      if (!("siteA" in plan) || !("siteB" in plan)) continue;

      local airportType = (("airport" in plan) && plan.airport != null && ("type" in plan.airport))
          ? plan.airport.type : -1;
      local townA = OpexC78AirSlotTown(plan.siteA, airportType);
      local townB = OpexC78AirSlotTown(plan.siteB, airportType);
      local closestTownA = OpexC78AirPhysicalTown(plan.siteA);
      local closestTownB = OpexC78AirPhysicalTown(plan.siteB);
      local capital = ("budgetCapital" in project) ? project.budgetCapital : 0;
      local finance = OpexProjectFinanceCapital(project);
      local isAffordable = finance <= available;
      local rank = OpexC78FundedRank(this._projects, project);
      local score = ("fundScore" in project)
          ? OpexProjectSelectionScore(project, "fundScore") : -1;
      local defensiveClaims = ("defensiveSlotClaims" in project)
          ? project.defensiveSlotClaims : -1;
      local defensiveCompetitorClaims = ("defensiveCompetitorClaims" in project)
          ? project.defensiveCompetitorClaims : -1;
      local defensiveOwnClaims = ("defensiveOwnClaims" in project)
          ? project.defensiveOwnClaims : -1;
      local age = ("economicsDate" in project)
          ? AIDate.GetCurrentDate() - project.economicsDate : -1;

      airCandidates++;
      if (isAffordable) affordable++;
      if (rank >= 0) funded++;

      OpexC78SlotLog("phase=project_candidate pass=" + passId
          + " cycle=" + cycle + " tick=" + tick
          + " townA=" + townA + " townB=" + townB
          + " closestA=" + closestTownA + " closestB=" + closestTownB
          + " rank=" + rank + " affordable=" + (isAffordable ? 1 : 0)
          + " profit=" + project.profitAnnual + " capital=" + capital + " finance=" + finance
          + " roi=" + project.roi + " score=" + score + " defensive_claims=" + defensiveClaims
          + " defensive_competitor_claims=" + defensiveCompetitorClaims
          + " defensive_own_claims=" + defensiveOwnClaims
          + " age_days=" + age
          + " src=" + project.src + " dst=" + project.dst);
    }
  }

  OpexC78SlotLog("phase=projects_pass pass=" + passId
      + " cycle=" + cycle + " tick=" + tick
      + " state=ok air_candidates=" + airCandidates
      + " affordable=" + affordable + " funded=" + funded + " available=" + available);
}

/* Tunnel mensuel : gate dedie, independant de C63/C48/decision_log. Un AILog par passe
 * pour ne pas perdre le mois courant (le jeu s'arrete souvent au 1er decembre). */
function OpexMonthlyFunnelLog(fields)
{
  if (!MONTHLY_FUNNEL) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " MONTHLY_FUNNEL " + fields);
}

/* C63+C58 : gate dedie. Compteurs memoire en boucle chaude, AILog seulement au flush annuel. */
function OpexC63InvestLog(fields)
{
  if (!C63_INVEST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C63_INVEST " + fields);
}

function OpexC63ModeSpend()
{
  return { planned_ok = 0, actual_ok = 0, n_ok = 0, planned_fail = 0, actual_fail = 0, n_fail = 0 };
}

function OpexC63OppBucket()
{
  return { n = 0, days = 0 };
}

function OpexC63ResetLedger()
{
  C63_INVEST_LEDGER = {
    spend = {
      rail = OpexC63ModeSpend(), road = OpexC63ModeSpend(),
      air = OpexC63ModeSpend(), water = OpexC63ModeSpend(), fleet = OpexC63ModeSpend()
    },
    opp = {
      absent = OpexC63OppBucket(), invalid = OpexC63OppBucket(),
      unaffordable = OpexC63OppBucket(), demand = OpexC63OppBucket(),
      waiting_compute = OpexC63OppBucket(), launched = OpexC63OppBucket()
    },
    absent_causes = {
      empty_pool = OpexC63OppBucket(),
      unprofitable = OpexC63OppBucket(),
      already_served = OpexC63OppBucket(),
      no_site = OpexC63OppBucket(),
      mode_cargo_filter = OpexC63OppBucket(),
      selection_empty = OpexC63OppBucket(),
      stage_empty = OpexC63OppBucket(),
      cache_exhausted = OpexC63OppBucket(),
      abandon_filtered = OpexC63OppBucket()
    },
    lastDate = -1,
    lastKind = "",
    lastAbsentCause = "",
    ledgerYear = -1,
    flushedYear = -1,
    cachedTick = -1,
    cachedDate = -1,
    cachedAvailable = 0,
    lines = []
  };
}

function OpexC63SpendSlot(mode)
{
  if (C63_INVEST_LEDGER == null || C63_INVEST_LEDGER.spend == null) return null;
  if (mode in C63_INVEST_LEDGER.spend) return C63_INVEST_LEDGER.spend[mode];
  return C63_INVEST_LEDGER.spend.fleet;
}

function OpexC63RecordSpend(mode, planned, actual, ok)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  OpexC63EnsureYear(AIDate.GetYear(AIDate.GetCurrentDate()));
  local slot = OpexC63SpendSlot(mode);
  if (slot == null) return;
  if (ok) {
    slot.planned_ok += planned;
    slot.actual_ok += actual;
    slot.n_ok++;
  } else {
    slot.planned_fail += planned;
    slot.actual_fail += actual;
    slot.n_fail++;
  }
}

function OpexC63ChildLen(root, key, inner)
{
  if (root == null || !(key in root) || root[key] == null) return -1;
  local node = root[key];
  if (inner == null || inner == "") {
    return node.len();
  }
  if (!(inner in node) || node[inner] == null) return -1;
  return node[inner].len();
}

function OpexC63StatCount(st, key, fallback)
{
  if (st != null && (key in st) && st[key] != null) return st[key];
  return fallback;
}

function OpexC63ClassifyAbsent(projects)
{
  if (projects == null) return "empty_pool";
  local st = ("stats" in projects) ? projects.stats : null;
  if (st != null && ("emptyCause" in st) && st.emptyCause != null && st.emptyCause != "" && st.emptyCause != "all_unaffordable") {
    return st.emptyCause;
  }
  local considered = (st != null && ("budgetConsidered" in st)) ? st.budgetConsidered : 0;
  if (considered > 0) return "selection_empty";

  if (st != null) {
    local cacheScanned = OpexC63StatCount(st, "cacheScanned", -1);
    local cacheRetained = OpexC63StatCount(st, "cacheRetained", -1);
    if (cacheScanned > 0 && cacheRetained == 0) {
      return "cache_exhausted";
    }
    local abandonFiltered = OpexC63StatCount(st, "abandonFiltered", -1);
    local modeCandidates = OpexC63StatCount(st, "modeCandidates", -1);
    if (abandonFiltered > 0 && modeCandidates == 0) {
      return "abandon_filtered";
    }
    local railC = OpexC63StatCount(st, "railCandidates", OpexC63ChildLen(projects, "rail", "candidates"));
    local roadC = OpexC63StatCount(st, "roadCandidates", OpexC63ChildLen(projects, "road", "candidates"));
    local airP = OpexC63StatCount(st, "airPlansCount", OpexC63ChildLen(projects, "airPlans", ""));
    local waterP = OpexC63StatCount(st, "waterPlansCount", OpexC63ChildLen(projects, "waterPlans", ""));
    if (railC == 0 && roadC == 0 && airP == 0 && waterP == 0) {
      return "stage_empty";
    }
  }

  local unprofitable = 0;
  local alreadyServed = 0;
  local noSite = 0;
  local modeCargoFilter = 0;
  local pairsTotal = 0;

  if (("rail" in projects) && projects.rail != null && ("stats" in projects.rail) && projects.rail.stats != null) {
    local rst = projects.rail.stats;
    if ("pairsTotal" in rst) pairsTotal += rst.pairsTotal;
    if ("profitNonPositive" in rst) unprofitable += rst.profitNonPositive;
    if ("ratioTooLow" in rst) unprofitable += rst.ratioTooLow;
    if ("pairsOriginServed" in rst) alreadyServed += rst.pairsOriginServed;
    if ("unsitable" in rst) noSite += rst.unsitable;
    if ("distanceShort" in rst) modeCargoFilter += rst.distanceShort;
    if ("distanceLong" in rst) modeCargoFilter += rst.distanceLong;
  }

  if (("road" in projects) && projects.road != null && ("stats" in projects.road) && projects.road.stats != null) {
    local rdst = projects.road.stats;
    if ("pairsInBand" in rdst) pairsTotal += rdst.pairsInBand;
    /* M1 : un candidat positif sous le repere ROAD_MIN_PROFIT_ANNUAL est conserve,
     * donc il ne doit pas expliquer un vivier vide comme "unprofitable". */
    if ("profitNonPositive" in rdst) unprofitable += rdst.profitNonPositive;
    else if ("profitTooLow" in rdst) unprofitable += rdst.profitTooLow; // vieille forme de sauvegarde
    if ("townRejected" in rdst) alreadyServed += rdst.townRejected;
    if ("roadDistanceShort" in rdst) modeCargoFilter += rdst.roadDistanceShort;
    if ("roadDistanceLong" in rdst) modeCargoFilter += rdst.roadDistanceLong;
  }

  if (pairsTotal == 0) return "empty_pool";

  local maxCount = unprofitable;
  local bestReason = "unprofitable";
  if (alreadyServed > maxCount) {
    maxCount = alreadyServed;
    bestReason = "already_served";
  }
  if (noSite > maxCount) {
    maxCount = noSite;
    bestReason = "no_site";
  }
  if (modeCargoFilter > maxCount) {
    maxCount = modeCargoFilter;
    bestReason = "mode_cargo_filter";
  }
  if (maxCount == 0) return "empty_pool";
  return bestReason;
}

function OpexC63ClassifyOpportunity(reason, available, need, railSearch)
{
  if (railSearch) return "waiting_compute";
  if (need > available) return "unaffordable";
  if (reason == "insufficient_cash" || reason == "cash_at_build") return "unaffordable";
  if (reason == "search_in_progress") return "waiting_compute";
  if (reason == "line_cap_reached" || reason == "town_road_line_cap" || reason == "no_demand") return "demand";
  if (reason == null || reason == "") return "invalid";
  return "invalid";
}

function OpexC63RecordOpportunity(kind, daysForKind, absentCause = "")
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  if (!(kind in C63_INVEST_LEDGER.opp)) return;
  C63_INVEST_LEDGER.opp[kind].n++;
  if (kind == "absent" && absentCause != "" && ("absent_causes" in C63_INVEST_LEDGER)
      && (absentCause in C63_INVEST_LEDGER.absent_causes)) {
    C63_INVEST_LEDGER.absent_causes[absentCause].n++;
  }
  OpexC63AddOpportunityDays(kind, daysForKind, absentCause);
}

/* Les observations et le temps passe ne sont pas la meme grandeur. Une nouvelle passe compte
 * l'etat observe MAINTENANT, mais l'intervalle depuis la passe precedente appartient a l'etat
 * precedent. Cette fonction ajoute donc uniquement une duree, sans fabriquer un compteur n. */
function OpexC63AddOpportunityDays(kind, daysForKind, absentCause = "")
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null || daysForKind <= 0) return;
  if (!(kind in C63_INVEST_LEDGER.opp)) return;
  C63_INVEST_LEDGER.opp[kind].days += daysForKind;
  if (kind == "absent" && absentCause != "" && ("absent_causes" in C63_INVEST_LEDGER)
      && (absentCause in C63_INVEST_LEDGER.absent_causes)) {
    C63_INVEST_LEDGER.absent_causes[absentCause].days += daysForKind;
  }
}

function OpexC63RecordLine(mode, age, predProfit, realProfit, predRev, realRev, vehCount, lineId, year)
{
  if (!C63_INVEST_PROBE) return;
  OpexC63InvestLog("phase=line year=" + year + " line=" + lineId + " mode=" + mode
      + " age=" + age + " pred_p=" + predProfit + " real_p=" + realProfit
      + " pred_r=" + predRev + " real_r=" + realRev + " vehs=" + vehCount);
}

function OpexC63RecordSpendResult(mode, result, plannedFallback)
{
  if (!C63_INVEST_PROBE || result == null) return;
  local planned = plannedFallback;
  if ("plannedCapital" in result) planned = result.plannedCapital;
  else if ("capital" in result) planned = result.capital;
  local actual = ("actualCost" in result) ? result.actualCost : 0;
  OpexC63RecordSpend(mode, planned, actual, result.ok);
}

function OpexC63CachedAvailable()
{
  local today = AIDate.GetCurrentDate();
  if (C63_INVEST_LEDGER.cachedDate == today) return C63_INVEST_LEDGER.cachedAvailable;
  local available = OpexAvailableCapital();
  C63_INVEST_LEDGER.cachedDate = today;
  C63_INVEST_LEDGER.cachedAvailable = available;
  return available;
}

function OpexC63YearStart(year)
{
  return AIDate.GetDate(year, 1, 1);
}

function OpexC63EnsureYear(nowYear)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  if (nowYear < 1970) return;
  if (C63_INVEST_LEDGER.ledgerYear < 0) {
    C63_INVEST_LEDGER.ledgerYear = nowYear;
    return;
  }
  while (C63_INVEST_LEDGER.ledgerYear < nowYear) {
    local oldYear = C63_INVEST_LEDGER.ledgerYear;
    local nextStart = OpexC63YearStart(oldYear + 1);
    local carryKind = C63_INVEST_LEDGER.lastKind;
    local carryAbsentCause = C63_INVEST_LEDGER.lastAbsentCause;
    if (C63_INVEST_LEDGER.lastDate >= 0 && C63_INVEST_LEDGER.lastKind != "") {
      local tail = nextStart - C63_INVEST_LEDGER.lastDate - 1;
      if (tail > 0) OpexC63AddOpportunityDays(C63_INVEST_LEDGER.lastKind, tail, C63_INVEST_LEDGER.lastAbsentCause);
    }
    OpexC63FlushLedger(oldYear);
    if (C63_INVEST_LEDGER.ledgerYear <= oldYear) C63_INVEST_LEDGER.ledgerYear = oldYear + 1;
    C63_INVEST_LEDGER.lastDate = nextStart;
    C63_INVEST_LEDGER.lastKind = carryKind;
    C63_INVEST_LEDGER.lastAbsentCause = carryAbsentCause;
  }
}

function OpexC63NotePass(builtCount, best, passDiscards, railSearching, projects = null)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  local now = AIDate.GetCurrentDate();
  local nowYear = AIDate.GetYear(now);
  OpexC63EnsureYear(nowYear);
  local days = 0;
  if (C63_INVEST_LEDGER.lastDate >= 0 && now >= C63_INVEST_LEDGER.lastDate) {
    days = now - C63_INVEST_LEDGER.lastDate;
  }
  local previousKind = C63_INVEST_LEDGER.lastKind;
  local previousAbsentCause = C63_INVEST_LEDGER.lastAbsentCause;
  local kind;
  local absentCause = "";
  if (builtCount > 0) kind = "launched";
  else if (best == null || best.len() == 0) {
    local st = (projects != null && ("stats" in projects)) ? projects.stats : null;
    local considered = (st != null && ("budgetConsidered" in st)) ? st.budgetConsidered : 0;
    local minCap = (st != null && ("minCapital" in st)) ? st.minCapital : -1;
    local avail = OpexC63CachedAvailable();

    if (considered > 0 && minCap > 0 && minCap > avail) {
      kind = "unaffordable";
      absentCause = "";
    } else {
      kind = "absent";
      absentCause = OpexC63ClassifyAbsent(projects);
    }
  } else {
    local target = null;
    local leftoverRank = -1;
    for (local i = 0; i < best.len(); i++) {
      if (best[i] != null) { leftoverRank = i; target = best[i]; break; }
    }
    if (target == null) {
      local st = (projects != null && ("stats" in projects)) ? projects.stats : null;
      local considered = (st != null && ("budgetConsidered" in st)) ? st.budgetConsidered : 0;
      local minCap = (st != null && ("minCapital" in st)) ? st.minCapital : -1;
      local avail = OpexC63CachedAvailable();
      if (considered > 0 && minCap > 0 && minCap > avail) {
        kind = "unaffordable";
        absentCause = "";
      } else {
        kind = "absent";
        absentCause = OpexC63ClassifyAbsent(projects);
      }
    } else {
      local reason = "";
      if (passDiscards != null) {
        for (local k = 0; k < passDiscards.len(); k++) {
          if (("rank" in passDiscards[k]) && passDiscards[k].rank == leftoverRank) {
            reason = passDiscards[k].reason;
            break;
          }
        }
        if (reason == "" && passDiscards.len() > 0) reason = passDiscards[0].reason;
      }
      local waitingOnly = railSearching && (reason == "" || reason == "search_in_progress");
      local need = ("capital" in target) ? target.capital : 0;
      kind = OpexC63ClassifyOpportunity(reason, OpexC63CachedAvailable(), need, waitingOnly);
    }
  }
  /* 02.1 : days decrit le temps ecoule AVANT cette observation. Le crediter au nouvel etat
   * decalait tout le ledger d'une passe (absent -> launched devenait du temps launched, etc.).
   * Compter l'observation courante sans duree, puis attribuer l'intervalle a l'etat precedent. */
  OpexC63RecordOpportunity(kind, 0, absentCause);
  if (previousKind != "") OpexC63AddOpportunityDays(previousKind, days, previousAbsentCause);
  C63_INVEST_LEDGER.lastDate = now;
  C63_INVEST_LEDGER.lastKind = kind;
  C63_INVEST_LEDGER.lastAbsentCause = absentCause;
}

function OpexC63RecordEmptyProbe(projects, stage, freightCargo, abandonedPairs)
{
  if (!C63_INVEST_PROBE) return;
  if (projects == null) return;
  local st = ("stats" in projects) ? projects.stats : null;
  local railCand = OpexC63StatCount(st, "railCandidates", OpexC63ChildLen(projects, "rail", "candidates"));
  local roadCand = OpexC63StatCount(st, "roadCandidates", OpexC63ChildLen(projects, "road", "candidates"));
  local airPlans = OpexC63StatCount(st, "airPlansCount", OpexC63ChildLen(projects, "airPlans", ""));
  local waterPlans = OpexC63StatCount(st, "waterPlansCount", OpexC63ChildLen(projects, "waterPlans", ""));
  local modeCand = OpexC63StatCount(st, "modeCandidates", -1);
  local considered = OpexC63StatCount(st, "budgetConsidered", -1);
  local selected = OpexC63StatCount(st, "budgetSelected", -1);
  local minCap = OpexC63StatCount(st, "minCapital", -1);
  local availCap = OpexAvailableCapital();
  local cacheScanned = OpexC63StatCount(st, "cacheScanned", -1);
  local cacheRetained = OpexC63StatCount(st, "cacheRetained", -1);
  local abandonFiltered = OpexC63StatCount(st, "abandonFiltered", -1);
  local abandonPairs = (abandonedPairs != null) ? abandonedPairs.len() : 0;
  local emptyCause = "";
  if (st != null && ("emptyCause" in st) && st.emptyCause != null && st.emptyCause != "") {
    emptyCause = st.emptyCause;
  } else {
    emptyCause = OpexC63ClassifyAbsent(projects);
  }

  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  OpexC63InvestLog("phase=empty_probe year=" + year + " stage=" + stage + " cargo=" + freightCargo
      + " rail_c=" + railCand + " road_c=" + roadCand + " air_p=" + airPlans + " water_p=" + waterPlans
      + " mode_c=" + modeCand + " considered=" + considered + " selected=" + selected
      + " min_cap=" + minCap + " avail_cap=" + availCap
      + " cache_scanned=" + cacheScanned + " cache_retained=" + cacheRetained
      + " abandon_filtered=" + abandonFiltered + " abandon_pairs=" + abandonPairs
      + " cause=" + emptyCause);
}

function OpexC63FlushLedger(year)
{
  if (!C63_INVEST_PROBE || C63_INVEST_LEDGER == null) return;
  if (year < 1970) return;
  if (C63_INVEST_LEDGER.flushedYear == year) return;
  foreach (mode, slot in C63_INVEST_LEDGER.spend) {
    OpexC63InvestLog("phase=spend year=" + year + " mode=" + mode
        + " planned_ok=" + slot.planned_ok + " actual_ok=" + slot.actual_ok + " n_ok=" + slot.n_ok
        + " planned_fail=" + slot.planned_fail + " actual_fail=" + slot.actual_fail
        + " n_fail=" + slot.n_fail);
  }
  local o = C63_INVEST_LEDGER.opp;
  OpexC63InvestLog("phase=opp year=" + year
      + " absent_n=" + o.absent.n + " absent_d=" + o.absent.days
      + " invalid_n=" + o.invalid.n + " invalid_d=" + o.invalid.days
      + " unaffordable_n=" + o.unaffordable.n + " unaffordable_d=" + o.unaffordable.days
      + " demand_n=" + o.demand.n + " demand_d=" + o.demand.days
      + " waiting_compute_n=" + o.waiting_compute.n + " waiting_compute_d=" + o.waiting_compute.days
      + " launched_n=" + o.launched.n + " launched_d=" + o.launched.days);
  if ("absent_causes" in C63_INVEST_LEDGER) {
    local ac = C63_INVEST_LEDGER.absent_causes;
    OpexC63InvestLog("phase=opp_absent year=" + year
        + " empty_pool_n=" + ac.empty_pool.n + " empty_pool_d=" + ac.empty_pool.days
        + " unprofitable_n=" + ac.unprofitable.n + " unprofitable_d=" + ac.unprofitable.days
        + " already_served_n=" + ac.already_served.n + " already_served_d=" + ac.already_served.days
        + " no_site_n=" + ac.no_site.n + " no_site_d=" + ac.no_site.days
        + " mode_cargo_filter_n=" + ac.mode_cargo_filter.n + " mode_cargo_filter_d=" + ac.mode_cargo_filter.days
        + " selection_empty_n=" + ac.selection_empty.n + " selection_empty_d=" + ac.selection_empty.days
        + " stage_empty_n=" + ac.stage_empty.n + " stage_empty_d=" + ac.stage_empty.days
        + " cache_exhausted_n=" + ac.cache_exhausted.n + " cache_exhausted_d=" + ac.cache_exhausted.days
        + " abandon_filtered_n=" + ac.abandon_filtered.n + " abandon_filtered_d=" + ac.abandon_filtered.days);
  }
  OpexC63ResetLedger();
  C63_INVEST_LEDGER.flushedYear = year;
  C63_INVEST_LEDGER.ledgerYear = year + 1;
  C63_INVEST_LEDGER.lastDate = OpexC63YearStart(year + 1);
  C63_INVEST_LEDGER.lastKind = "";
  C63_INVEST_LEDGER.lastAbsentCause = "";
}

/* C50 : gate dedie pour la sonde chronologique legere (tresorerie, profit par ligne,
 * projets batis avec cout/ROI, projets refuses pour tresorerie avec ROI).
 * Autonome : fonctionne avec decision_log=0. */
function OpexC50ChronologyLog(fields)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C50_CHRONO " + fields);
}
/* C50 : enregistrement deduplique des refus de tresorerie (au plus un log par mois calendaire et par candidat). */
function OpexC50LogCashRefusal(mode, rank, cost, profit, roi, src, dst, need, money)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  local ym = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  local key = mode + "|" + src + "|" + dst;
  if ((key in C50_REFUSE_CACHE) && C50_REFUSE_CACHE[key] == ym) return;
  C50_REFUSE_CACHE[key] <- ym;

  local available = OpexAvailableCapital();
  local loan = AICompany.GetLoanAmount();
  OpexC50ChronologyLog("phase=refused_cash mode=" + mode + " rank=" + rank
      + " cost=" + cost + " profit=" + profit + " roi=" + roi
      + " need=" + need + " cash=" + money + " loan=" + loan + " available=" + available);
}
/* C55 : gate dedie et autonome. Ne jamais reutiliser le gate C49 : la sonde doit publier seule. */
function OpexC55OriginRelaxLog(fields)
{
  if (!C55_ORIGIN_RELAX_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C55_ORIGIN_RELAX " + fields);
}
/* C55 : gate autonome pour la tracabilite causale PAX. */
function OpexC55PaxTraceLog(kind, fields)
{
  if (!C55_PAX_TRACE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C56 : gate dedie et autonome. Lecture des traces :
 * - dernier TASK_ENTER name=X sans TASK_EXIT name=X : X ne rend pas la main, blocage dedans ;
 * - dernier STAGE_ENTER name=c56_stage_X sans STAGE_EXIT : blocage dans cette phase du portefeuille ;
 * - les phases sautees emettent aussi STAGE_EXIT : un jalon manquant signifie toujours un blocage ;
 * - TASK_ENTER/TASK_EXIT apparies jusqu'au bout puis plus rien : blocage hors tache ;
 * - LOOP_TICK continu sans TASK_ENTER : boucle active, ordonnanceur sans selection ;
 * - plus aucune trace : script lui-meme plus execute par le moteur. */
function OpexC56TaskLog(kind, name, cycle, extra = null)
{
  if (!C56_TASK_TRACE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C56_TASK " + kind + " name=" + name
             + " cycle=" + cycle + " tick=" + AIController.GetTick()
             + " opsclk=" + OpexOpsClock() + (extra != null ? " " + extra : ""));
}
/* C56 : intention reactive de l'orchestrateur, bornee par INTENT_ENTER/INTENT_EXIT. */
function OpexC56DispatchReactive(owner, intention)
{
  if (!C56_TASK_TRACE) return owner._dispatchReactiveIntention(intention);
  local kind = (("kind" in intention) && intention.kind != null) ? intention.kind : "unknown";
  OpexC56TaskLog("INTENT_ENTER", kind, "-");
  local dispatched = owner._dispatchReactiveIntention(intention);
  OpexC56TaskLog("INTENT_EXIT", kind, "-", "dispatched=" + (dispatched ? 1 : 0));
  return dispatched;
}
/* C56 : tranche de travailleur. Une trace par travailleur (WORKER_ENTER a la premiere tranche,
 * WORKER_EXIT a la derniere) et non par tranche : un A* rail en compte des milliers. Les tranches
 * s'intercalent avec la file de fond, d'ou le cumul `step_ops` propre au travailleur. */
function OpexC56WorkerStep(worker, opsBudget, deadlineTick)
{
  if (!C56_TASK_TRACE) return OpexWorkerStep(worker, opsBudget, deadlineTick);
  if (C56_WORKER_ACC == null || C56_WORKER_ACC.worker != worker) {
    ::C56_WORKER_ACC = { worker = worker, kind = worker.kind, steps = 0, ops = 0 };
    OpexC56TaskLog("WORKER_ENTER", worker.kind, "-");
  }
  local acc = C56_WORKER_ACC;
  local mark = OpexOpsMeasureBegin();
  local outcome = OpexWorkerStep(worker, opsBudget, deadlineTick);
  acc.ops += OpexOpsMeasureEnd(mark);
  acc.steps++;
  if (outcome == "done" || outcome == "cancelled") {
    OpexC56TaskLog("WORKER_EXIT", acc.kind, "-", "outcome=" + outcome + " steps=" + acc.steps
                   + " step_ops=" + acc.ops);
    ::C56_WORKER_ACC = null;
  }
  return outcome;
}
/* Horloge d'opcodes monotone, meme convention qu'OpexOpsMeasureEnd : un tick franchi compte pour
 * OPS_PER_TICK. La difference entre deux traces C56 donne le cout d'une etape. */
function OpexOpsClock()
{
  return AIController.GetTick() * OPS_PER_TICK + (OPS_PER_TICK - AIController.GetOpsTillSuspend());
}
/* C52 : gate dedie et autonome. La sonde observe aussi quand la reparation est desarmee. */
function OpexC52AutoreplaceLog(fields)
{
  if (!C52_AUTOREPLACE_LOG) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C52_AUTOREPLACE " + fields);
}
/* C52 : gate dedie et autonome. La sonde ne publie que son propre ledger annuel. */
function OpexC52EventExposureLog(fields)
{
  if (!C52_EVENT_EXPOSURE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C52_EVENT_EXPOSURE " + fields);
}
/* Observe une paire au point meme ou le filtre d'origine route la voit. Cette fonction ne
 * retourne rien et n'ecrit que le ledger de sonde ; elle ne participe a aucun predicat. */
function OpexC55OriginRelaxObserve(kind, lines, src, dst, srcServed, dstServed)
{
  if (!C55_ORIGIN_RELAX_PROBE || C55_ORIGIN_RELAX_LEDGER == null) return;
  C55_ORIGIN_RELAX_LEDGER.candidates_seen++;
  if (!srcServed && !dstServed) return;
  C55_ORIGIN_RELAX_LEDGER.rejected_total++;
  if (srcServed && dstServed) {
    C55_ORIGIN_RELAX_LEDGER.both_served++;
    return;
  }
  C55_ORIGIN_RELAX_LEDGER.one_served++;
  if (kind == "pax") C55_ORIGIN_RELAX_LEDGER.one_served_pax++;
  else C55_ORIGIN_RELAX_LEDGER.one_served_freight++;
  /* Cle disponible ici : meme paire geometrique, dans un sens ou dans l'autre, a moins de
   * ORIGIN_SEPARATION des deux originA/originB d'une ligne route existante. */
  if (OpexRoadPairServed(lines, src, dst)) C55_ORIGIN_RELAX_LEDGER.duplicate_exact++;
}
/* C55 : observateur des revalidations PAX bloquees par une origine deja servie. */
function OpexC55PaxTraceObserveRevalidated(isOriginBlocked)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.revalidated++;
  if (isOriginBlocked) C55_PAX_TRACE_LEDGER.origin_blocked++;
}
function OpexC49VehicleType(mode)
{
  if (mode == "rail") return AIVehicle.VT_RAIL;
  if (mode == "road") return AIVehicle.VT_ROAD;
  if (mode == "air" || mode == "fleet") return AIVehicle.VT_AIR;
  if (mode == "water") return AIVehicle.VT_WATER;
  return -1;
}
function OpexC49IsMapFailure(passDiscards, rank)
{
  foreach (discard in passDiscards) {
    if (discard.rank != rank) continue;
    if (discard.reason == "build_failed" || discard.reason == "plan_failed"
        || discard.reason == "too_close" || discard.reason == "too_close_hard"
        || discard.reason == "too_close_no_join") return true;
  }
  return false;
}
/* C41.47 : un evenement par liberation, pas un accumulateur annuel -- les liberations sont
 * rares (motif observe : quelques par partie), la mesure interessante est LEQUEL candidat et
 * QUAND, pas un total. */
function OpexC41RailCashReleaseLog(fields)
{
  if (!C41_RAIL_CASH_RELEASE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_CASH_RELEASE " + fields);
}
/* C41.48 : un evenement par frontiere de tranche -- la frequence de declenchement EST la
 * mesure (repond a "sur combien de frontieres le test C41.49 aurait-il seulement l'occasion
 * de s'appliquer ?"), donc pas d'agregat qui la masquerait. */
function OpexC41RailDominationLog(fields)
{
  if (!C41_RAIL_DOMINATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_DOMINATION_PROBE " + fields);
}
/* C41.49 : son propre gate, comme C41.46/C41.47/C41.48 -- OpexC41SchedulerLog et
 * OpexC41RailDominationLog l'auraient sinon silencieusement avale (piege deja trouve trois fois). */
function OpexC41ProjectsFallthroughLog(fields)
{
  if (!C41_PROJECTS_FALLTHROUGH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_PROJECTS_FALLTHROUGH_PROBE " + fields);
}
/* C39.5 : gate propre -- ne jamais reutiliser celui d'une autre sonde, sinon armer seulement
 * c39_projects_cadence_probe rendrait le canal silencieux. */
function OpexC39ProjectsCadenceLog(fields)
{
  if (!C39_PROJECTS_CADENCE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PROJECTS_CADENCE " + fields);
}
/* C39.6 : gate propre, INDEPENDANT de C39_PROJECTS_CADENCE_PROBE et de C41_RAIL_SLICE_LEDGER --
 * ne jamais reutiliser le gate d'une autre sonde (piege deja trouve trois fois dans ce depot :
 * un canal reutilise reste silencieux tant que SA propre variante n'est pas armee). */
function OpexC39PassClockLog(fields)
{
  if (!C39_PASS_CLOCK_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PASS_CLOCK " + fields);
}
/* V95 item 1 : gate propre sous probe_scheduler. Ne pas reutiliser OpexC41SchedulerLog :
 * ce dernier reste silencieux si seuls certains flags C41 sont actifs. */
function OpexSchedIdleLog(kind, fields)
{
  if (!V95_SCHED_IDLE_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexC41StalenessLog(kind, fields)
{
  if (!C41_STALENESS_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* Contrat C41.14 : le hint est une borne prudente d'admission, pas une moyenne ni un budget
 * reservé. Le scheduler ne le lit pas encore pour executer : cette phase mesure seulement si le
 * point d'entree cible pourrait tenir dans le reliquat du tick courant. */
function OpexC41MicrotaskOpsHint(layer)
{
  if (layer == "catalog.water") return 350;
  return -1;
}
/* C41.4 reste observable sans armer C39 : c'est un inventaire de l'evenement, pas une
 * invalidation de catalogue. */
function OpexC41VehicleLostLog(fields)
{
  if (!C41_VEHICLE_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_VEHICLE_LOST " + fields);
}
function OpexC41RailLostLog(fields)
{
  if (!C41_RAIL_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST " + fields);
}
/* Gate C54 autonome : AIDate et AILog ne sont atteignables que si le reglage C54 est actif. */
function OpexC54VehicleOrdersLog(fields)
{
  if (!C54_VEHICLE_ORDERS_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C54_VEHICLE_ORDERS " + fields);
}
function OpexC41RailLostTopologyLog(fields)
{
  if (!C41_RAIL_LOST_TOPOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_TOPOLOGY " + fields);
}
function OpexC41RailLostPhysicalLog(fields)
{
  if (!C41_RAIL_LOST_PHYSICAL_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_PHYSICAL " + fields);
}
function OpexC41RailSignalRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_SIGNAL_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexC41RailLostConnectivityLog(fields)
{
  if (!C41_RAIL_LOST_CONNECTIVITY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_CONNECTIVITY " + fields);
}
function OpexC41RailJunctionRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_JUNCTION_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexC39ProjectSignature(projects)
{
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) {
    return "none";
  }
  local project = projects.best[0];
  return project.mode + ":" + project.src + ":" + project.dst;
}
function OpexC41RevisionSnapshot(revisions)
{
  return "c=" + revisions.catalog.cargos + "," + revisions.catalog.towns + ","
         + revisions.catalog.industries + "," + revisions.catalog.rail + ","
         + revisions.catalog.road + "," + revisions.catalog.air + ","
         + revisions.catalog.water + " d=" + revisions.candidates.rail + ","
         + revisions.candidates.road + "," + revisions.candidates.air + ","
         + revisions.candidates.water + " p=" + revisions.portfolio + " s="
         + revisions.selection;
}
/* Le moteur a-t-il survécu au filtre propre à son mode ? Ce n'est pas une décision de
 * construction : C39.3 mesure précisément si le catalogue aurait une raison de propager l'event. */
function OpexC39CatalogUsesEngine(catalog, engine, mode)
{
  if (catalog == null) return false;
  if (mode == "rail") {
    if (catalog.railLocos != null) foreach (loco in catalog.railLocos) if (loco.id == engine) return true;
    if (catalog.wagonByCargo != null) foreach (cargo, wagon in catalog.wagonByCargo) if (wagon.id == engine) return true;
  } else if (mode == "road") {
    if (catalog.roadEngineByCargo != null) foreach (cargo, vehicle in catalog.roadEngineByCargo) if (vehicle.id == engine) return true;
  } else if (mode == "air") {
    if (catalog.plane != null && catalog.plane.id == engine) return true;
    if (catalog.airCombos != null) foreach (combo in catalog.airCombos) if (combo.plane.id == engine) return true;
  } else if (mode == "water") {
    if (catalog.ships != null) foreach (ship in catalog.ships) if (ship.id == engine) return true;
  }
  return false;
}
/* `retained=0` air signifie seulement que le moteur n'est pas le gagnant de `airCombos`.
 * Cette sonde separe les filtres eliminatoires de la domination capacite/vitesse, sans modifier
 * l'algorithme de selection. */
function OpexC39AirEngineReason(catalog, engine)
{
  if (catalog == null || !AIEngine.IsValidEngine(engine)) return "invalid";
  if (!AIEngine.IsBuildable(engine)) return "not_buildable";
  if (catalog.paxCargo < 0 || !AIEngine.CanRefitCargo(engine, catalog.paxCargo)) return "no_pax_refit";
  local planeType = AIEngine.GetPlaneType(engine);
  if (planeType != AIAirport.PT_SMALL_PLANE && planeType != AIAirport.PT_BIG_PLANE) return "unsupported_type";
  if (AIEngine.GetCapacity(engine) <= 0) return "zero_capacity";
  if (OpexC39CatalogUsesEngine(catalog, engine, "air")) return "selected";
  return "dominated";
}
function OpexCashReserveProbeLog(fields)
{
  if (!CASH_RESERVE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " CASH_RESERVE_PROBE " + fields);
}
function OpexPortfolioRefreshProbeLog(fields)
{
  if (!PORTFOLIO_REFRESH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " PORTFOLIO_REFRESH_PROBE " + fields);
}

/* C69 : cle d'identite stable d'un candidat ou projet construit */
function OpexC69AttemptKey(p)
{
  if (p == null) return "none";
  if (!("mode" in p) && ("src" in p) && ("dst" in p) && ("cargo" in p) && ("kind" in p)) {
    return "rail|" + p.src + "|" + p.dst + "|" + p.cargo + "|" + p.kind;
  }
  return OpexProjectAttemptKey(p);
}

/* C69 : somme GetProfitLastYear de l'ensemble des vehicules de la compagnie (controle F_veh) */
function OpexC69VehicleProfitLastYear()
{
  local total = 0;
  local vl = AIVehicleList();
  foreach (v, _ in vl) {
    if (AIVehicle.IsValidVehicle(v)) {
      total += AIVehicle.GetProfitLastYear(v);
    }
  }
  return total;
}

/* C69 : mediane d'une liste de nombres reels sans mutation */
function OpexMedianFloat(values)
{
  local n = values.len();
  if (n == 0) return 0.0;
  local copy = [];
  foreach (v in values) copy.append(v);
  for (local i = 1; i < n; i++) {
    local v = copy[i];
    local j = i;
    while (j > 0 && copy[j - 1] > v) {
      copy[j] = copy[j - 1];
      j--;
    }
    copy[j] = v;
  }
  if (n % 2 == 1) return copy[n / 2];
  return (copy[n / 2 - 1] + copy[n / 2]) / 2.0;
}

/* C69/C75 : calcul factorise du flux d'exploitation journalier F sur les 4 derniers trimestres complets */
function OpexComputeOperatingCashFlow(now = null)
{
  if (now == null) now = AIDate.GetCurrentDate();
  local curYear = AIDate.GetYear(now);
  local curMonth = AIDate.GetMonth(now);
  local curQuarterIdx = (curMonth - 1) / 3;
  local totalCompletedQuarters = (curYear - OPEX_START_YEAR) * 4 + curQuarterIdx;

  local F = 0.0;
  local daysCovered = 0;
  if (totalCompletedQuarters > 0) {
    local numQ = totalCompletedQuarters < 4 ? totalCompletedQuarters : 4;
    local curQuarterStartMonth = curQuarterIdx * 3 + 1;
    local curQuarterStartDate = AIDate.GetDate(curYear, curQuarterStartMonth, 1);
    local T = totalCompletedQuarters;
    local windowStartQuarter = T - numQ;
    local windowStartYear = OPEX_START_YEAR + (windowStartQuarter / 4);
    local windowStartMonth = (windowStartQuarter % 4) * 3 + 1;
    local windowStartDate = AIDate.GetDate(windowStartYear, windowStartMonth, 1);
    daysCovered = curQuarterStartDate - windowStartDate;

    if (daysCovered > 0) {
      local sumNet = 0.0;
      for (local q = 1; q <= numQ; q++) {
        local inc = AICompany.GetQuarterlyIncome(AICompany.COMPANY_SELF, q);
        local exp = AICompany.GetQuarterlyExpenses(AICompany.COMPANY_SELF, q);
        sumNet += (inc.tofloat() + exp);
      }
      /* GetQuarterlyIncome + GetQuarterlyExpenses excluent construction et achats de vehicules
       * (mesure C69 : -3,7 k£ de depenses pour 278 k£ investis au meme trimestre) : sumNet est
       * deja le flux d'exploitation. Ajouter I le compterait deux fois. */
      local numerator = sumNet;
      if (numerator > 0.0) {
        F = numerator / daysCovered.tofloat();
      }
    }
  }

  return {
    F = F,
    daysCovered = daysCovered
  };
}

/* C69 : calcul unique de F, tau et K_dec par appel de selection */
function OpexC69ComputeKDec()
{
  local now = AIDate.GetCurrentDate();
  local flow = OpexComputeOperatingCashFlow(now);
  local F = flow.F;
  local daysCovered = flow.daysCovered;

  local startDate = AIDate.GetDate(OPEX_START_YEAR, 1, 1);
  local daysSinceStart = now - startDate;
  if (daysSinceStart < 1) daysSinceStart = 1;
  local D = daysSinceStart < 365 ? daysSinceStart : 365;

  local N = 0;
  if (C69_BUILD_DATES != null) {
    local cutoff = now - D;
    local pruned = [];
    foreach (d in C69_BUILD_DATES) {
      if (d >= cutoff) {
        pruned.append(d);
      }
    }
    C69_BUILD_DATES = pruned;
    N = C69_BUILD_DATES.len();
  }

  local tau = 0.0;
  local K_dec = 0;
  if (N > 0 && F > 0.0) {
    tau = D.tofloat() / N.tofloat();
    K_dec = (F * tau).tointeger();
    if (K_dec < 0) K_dec = 0;
  }

  return {
    F = F,
    tau = tau,
    K_dec = K_dec,
    D = D,
    N = N,
    daysCovered = daysCovered
  };
}

/* C75 : enregistre la date d'une passe de _tryBuildProjects et purge au-dela de la fenetre */
function OpexC75RecordPassDate(now = null)
{
  if (!C75_TRACK_PASSES) return;
  if (C75_PASS_DATES == null) C75_PASS_DATES = [];
  if (now == null) now = AIDate.GetCurrentDate();
  C75_PASS_DATES.append(now);

  local startDate = AIDate.GetDate(OPEX_START_YEAR, 1, 1);
  local daysSinceStart = now - startDate;
  if (daysSinceStart < 1) daysSinceStart = 1;
  local D = daysSinceStart < 365 ? daysSinceStart : 365;

  local cutoff = now - D;
  local pruned = [];
  foreach (d in C75_PASS_DATES) {
    if (d >= cutoff) {
      pruned.append(d);
    }
  }
  C75_PASS_DATES = pruned;
}

/* C75 : calcul de K_pass = F * tau_pass sur la fenetre glissante min(365, jours depuis debut).
 * Moins de 2 passes dans la fenetre => K_pass = 0. */
function OpexC75ComputeKPass(now = null)
{
  if (now == null) now = AIDate.GetCurrentDate();
  local flow = OpexComputeOperatingCashFlow(now);
  local F = flow.F;

  local startDate = AIDate.GetDate(OPEX_START_YEAR, 1, 1);
  local daysSinceStart = now - startDate;
  if (daysSinceStart < 1) daysSinceStart = 1;
  local D = daysSinceStart < 365 ? daysSinceStart : 365;

  local N = 0;
  if (C75_PASS_DATES != null) {
    local cutoff = now - D;
    local pruned = [];
    foreach (d in C75_PASS_DATES) {
      if (d >= cutoff) {
        pruned.append(d);
      }
    }
    C75_PASS_DATES = pruned;
    N = C75_PASS_DATES.len();
  }

  local tau_pass = 0.0;
  local K_pass = 0;
  if (N >= 2 && F > 0.0) {
    tau_pass = D.tofloat() / N.tofloat();
    K_pass = (F * tau_pass).tointeger();
    if (K_pass < 0) K_pass = 0;
  }

  return {
    F = F,
    tau_pass = tau_pass,
    K_pass = K_pass,
    D = D,
    N = N,
    daysCovered = flow.daysCovered
  };
}

/* C75 : reinitialise le registre annuel de passes et chantiers */
function OpexC75ResetYearLedger()
{
  C75_YEAR_LEDGER = {
    passes = 0,
    builds = 0,
    multi_passes = 0
  };
}

/* C75 bis : registre separe pour que le chemin c75_kpass_bypass=0 ne fasse
 * aucun comptage supplementaire a chaque passe. */
function OpexC75BypassResetYearLedger(year = -1)
{
  C75_KPASS_BYPASS_LEDGER = {
    eligible = 0,
    consumed = 0,
    fleet_consumed = 0,
    stop_k_pass = 0,
    stop_cash = 0,
    stop_rail_search = 0,
    stop_list_end = 0,
    stop_other = 0
  };
  C75_KPASS_BYPASS_LEDGER_YEAR = year;
}

function OpexC75BypassEnsureYear(year)
{
  if (!C75_KPASS_BYPASS) return;
  if (C75_KPASS_BYPASS_LEDGER == null) {
    OpexC75BypassResetYearLedger(year);
    return;
  }
  if (C75_KPASS_BYPASS_LEDGER_YEAR < 0) {
    C75_KPASS_BYPASS_LEDGER_YEAR = year;
    return;
  }
  if (C75_KPASS_BYPASS_LEDGER_YEAR != year) {
    OpexC75BypassFlushYear(C75_KPASS_BYPASS_LEDGER_YEAR);
    C75_KPASS_BYPASS_LEDGER_YEAR = year;
  }
}

function OpexC75BypassProjectKind(project)
{
  if (project == null) return "unknown";
  if (("kind" in project) && project.kind != null) return project.kind;
  if (("payload" in project) && project.payload != null &&
      ("kind" in project.payload) && project.payload.kind != null) return project.payload.kind;
  return "unknown";
}

function OpexC75BypassModeCode(project)
{
  if (project == null || !("mode" in project)) return "?";
  if (project.mode == "air") return "A";
  if (project.mode == "rail") return "T";
  if (project.mode == "road") return "R";
  if (project.mode == "water") return "W";
  if (project.mode == "fleet") return "F";
  return "?";
}

function OpexC75BypassKindCode(project)
{
  local kind = OpexC75BypassProjectKind(project);
  if (kind == "pax") return "P";
  if (kind == "freight") return "F";
  if (kind == "fleet") return "L";
  return "U";
}

function OpexC75BypassRecordEligible(year, project, financeCapital, availableCapital, kPass, builtBefore, alreadyConsumed)
{
  if (!C75_KPASS_BYPASS) return;
  if (C75_KPASS_BYPASS_LEDGER == null) OpexC75BypassResetYearLedger();
  local mode = (project != null && ("mode" in project)) ? project.mode : "unknown";
  local isFleet = mode == "fleet" ? 1 : 0;
  C75_KPASS_BYPASS_LEDGER.eligible++;
  AILog.Info("C75_BYPASS phase=eligible year=" + year
      + " mode=" + mode
      + " kind=" + OpexC75BypassProjectKind(project)
      + " capital=" + financeCapital
      + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
      + " available=" + availableCapital
      + " k_pass=" + kPass + " built_before=" + builtBefore
      + " already_consumed=" + (alreadyConsumed ? 1 : 0)
      + " fleet=" + isFleet);
}

function OpexC75BypassRecordConsumed(year, project, financeCapital, availableCapital, kPass, builtBefore)
{
  if (!C75_KPASS_BYPASS) return;
  if (C75_KPASS_BYPASS_LEDGER == null) OpexC75BypassResetYearLedger();
  local mode = (project != null && ("mode" in project)) ? project.mode : "unknown";
  local isFleet = mode == "fleet" ? 1 : 0;
  local modeChar = OpexC75BypassModeCode(project);
  local kindChar = OpexC75BypassKindCode(project);
  C75_KPASS_BYPASS_LEDGER.consumed++;
  C75_KPASS_BYPASS_LEDGER.fleet_consumed += isFleet;
  AILog.Info("C75_BYPASS phase=consumed year=" + year
      + " mode=" + mode
      + " kind=" + OpexC75BypassProjectKind(project)
      + " capital=" + financeCapital
      + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
      + " available=" + availableCapital
      + " k_pass=" + kPass + " built_before=" + builtBefore
      + " fleet=" + isFleet);
  OpexSign(AIMap.GetTileIndex(3, 7), "C7C|" + (year % 100) + "|" + modeChar + "|" + kindChar
      + "|" + (financeCapital / 1000) + "|" + (availableCapital / 1000)
      + "|" + (kPass / 1000));
}

function OpexC75BypassRecordStop(stopReason)
{
  if (!C75_KPASS_BYPASS || C75_KPASS_BYPASS_LEDGER == null || stopReason == null) return;
  if (stopReason == "k_pass") C75_KPASS_BYPASS_LEDGER.stop_k_pass++;
  else if (stopReason == "cash") C75_KPASS_BYPASS_LEDGER.stop_cash++;
  else if (stopReason == "rail_search") C75_KPASS_BYPASS_LEDGER.stop_rail_search++;
  else if (stopReason == "list_end") C75_KPASS_BYPASS_LEDGER.stop_list_end++;
  else C75_KPASS_BYPASS_LEDGER.stop_other++;
}

function OpexC75BypassFlushYear(year)
{
  if (!C75_KPASS_BYPASS || C75_KPASS_BYPASS_LEDGER == null) return;
  AILog.Info("C75_BYPASS phase=year year=" + year
      + " eligible=" + C75_KPASS_BYPASS_LEDGER.eligible
      + " consumed=" + C75_KPASS_BYPASS_LEDGER.consumed
      + " fleet_consumed=" + C75_KPASS_BYPASS_LEDGER.fleet_consumed
      + " stop_k_pass=" + C75_KPASS_BYPASS_LEDGER.stop_k_pass
      + " stop_cash=" + C75_KPASS_BYPASS_LEDGER.stop_cash
      + " stop_rail_search=" + C75_KPASS_BYPASS_LEDGER.stop_rail_search
      + " stop_list_end=" + C75_KPASS_BYPASS_LEDGER.stop_list_end
      + " stop_other=" + C75_KPASS_BYPASS_LEDGER.stop_other);
  OpexSign(AIMap.GetTileIndex(3, 8), "C7Y|" + (year % 100)
      + "|" + C75_KPASS_BYPASS_LEDGER.eligible
      + "|" + C75_KPASS_BYPASS_LEDGER.consumed
      + "|" + C75_KPASS_BYPASS_LEDGER.fleet_consumed);
  OpexSign(AIMap.GetTileIndex(3, 9), "C7S|" + (year % 100)
      + "|" + C75_KPASS_BYPASS_LEDGER.stop_k_pass
      + "|" + C75_KPASS_BYPASS_LEDGER.stop_cash
      + "|" + C75_KPASS_BYPASS_LEDGER.stop_rail_search
      + "|" + C75_KPASS_BYPASS_LEDGER.stop_list_end
      + "|" + C75_KPASS_BYPASS_LEDGER.stop_other);
  OpexC75BypassResetYearLedger();
}

/* C75 : enregistre le resultat d'une passe et publie phase=c75_pass si au moins 1 chantier */
function OpexC75RecordPassOutcome(year, builtCount, c75KPassData, stopReason)
{
  if (!C75_TRACK_PASSES) return;
  if (C75_YEAR_LEDGER != null) {
    C75_YEAR_LEDGER.builds += builtCount;
    if (builtCount > 1) C75_YEAR_LEDGER.multi_passes++;
  }
  if (builtCount > 0 && C69_BOTTLENECK_PROBE) {
    local kPass = (c75KPassData != null) ? c75KPassData.K_pass : 0;
    local tauPass = (c75KPassData != null) ? c75KPassData.tau_pass : 0.0;
    local fVal = (c75KPassData != null) ? c75KPassData.F : 0.0;
    local reason = (stopReason != null) ? stopReason : "list_end";
    OpexC69Log("phase=c75_pass year=" + year + " built=" + builtCount
        + " k_pass=" + kPass + " tau_pass=" + tauPass + " F=" + fVal
        + " stop=" + reason);
  }
}

/* C80 tâche 5 : sonde passive sous probe_portfolio comptant les projets rejetés par le filtre marginal */
function OpexC80RecordMarginalDiscard(year, rank, project)
{
  if (!C69_BOTTLENECK_PROBE) return;
  local predProfit = (project != null && ("profitAnnual" in project)) ? project.profitAnnual : 0;
  local calibProfit = (project != null && C70_PROFIT_CALIBRATED) ? OpexCalibratedProfit(project) : predProfit;
  if (C80_MARGINAL_FLOOR_LEDGER != null) {
    C80_MARGINAL_FLOOR_LEDGER.discards++;
    C80_MARGINAL_FLOOR_LEDGER.discard_profit += predProfit;
  }
  local mode = (project != null && ("mode" in project)) ? project.mode : "unknown";
  local financeCap = (project != null) ? OpexProjectFinanceCapital(project) : 0;
  local vehs = OpexProjectVehicleCount(project);
  local calibInt = (calibProfit != null && typeof(calibProfit) == "float") ? calibProfit.tointeger() : calibProfit;
  OpexC69Log("phase=marginal_discard year=" + year + " rank=" + rank + " mode=" + mode
      + " P=" + predProfit + " P_calib=" + calibInt
      + " vehs=" + vehs + " C=" + financeCap
      + " tot_discards=" + (C80_MARGINAL_FLOOR_LEDGER != null ? C80_MARGINAL_FLOOR_LEDGER.discards : 0)
      + " tot_discard_profit=" + (C80_MARGINAL_FLOOR_LEDGER != null ? C80_MARGINAL_FLOOR_LEDGER.discard_profit : 0));
}

/* C75 : publication annuelle du registre de passes et chantiers */
function OpexC75FlushYear(year)
{
  if (!C69_BOTTLENECK_PROBE || C75_YEAR_LEDGER == null) return;
  if (year < 1970) return;

  OpexC69Log("phase=c75_year year=" + year + " passes=" + C75_YEAR_LEDGER.passes
      + " builds=" + C75_YEAR_LEDGER.builds + " multi_passes=" + C75_YEAR_LEDGER.multi_passes);

  if (C80_MARGINAL_FLOOR_LEDGER != null && C80_MARGINAL_FLOOR_LEDGER.discards > 0) {
    OpexC69Log("phase=c80_marginal_year year=" + year
        + " discards=" + C80_MARGINAL_FLOOR_LEDGER.discards
        + " discard_profit=" + C80_MARGINAL_FLOOR_LEDGER.discard_profit);
    C80_MARGINAL_FLOOR_LEDGER.discards = 0;
    C80_MARGINAL_FLOOR_LEDGER.discard_profit = 0;
  }

  OpexC75ResetYearLedger();
}


/* C72 : cache journalier de K_dec pour la sonde passive du choix d'avion */
function OpexC69CachedKDec()
{
  local today = AIDate.GetCurrentDate();
  if (C69_CACHED_KDEC_DATE == today) return C69_CACHED_KDEC_VALUE;
  local data = OpexC69ComputeKDec();
  C69_CACHED_KDEC_DATE = today;
  C69_CACHED_KDEC_VALUE = data.K_dec;
  return C69_CACHED_KDEC_VALUE;
}

/* C72 : nom de l'appareil avec espaces remplaces par des tirets bas pour le parseur de logs */
function OpexPlaneName(engineId)
{
  if (!AIEngine.IsValidEngine(engineId)) return "unknown";
  local rawName = AIEngine.GetName(engineId);
  if (rawName == null || rawName.len() == 0) return "unknown";
  local res = "";
  for (local i = 0; i < rawName.len(); i++) {
    local c = rawName.slice(i, i + 1);
    if (c == " ") res += "_";
    else res += c;
  }
  return res.len() > 0 ? res : "unknown";
}

/* C73 : sonde passive vivier et passes du portefeuille (C69 etape 1) */
function OpexC73NewModeStats()
{
  return {
    examined = 0,
    rejections = {},
    produced = 0,
    after_topk = 0,
    to_select = 0,
    affordable = 0,
    selected = 0
  };
}

function OpexC73ResetLedger()
{
  C73_VIVIER_LEDGER = {
    flushedYear = -1,
    passes = {
      count = 0,
      empty = 0,
      built = 0,
      sum_cash = 0.0,
      sum_avail = 0.0
    },
    modes = {
      rail = OpexC73NewModeStats(),
      road = OpexC73NewModeStats(),
      air = OpexC73NewModeStats(),
      water = OpexC73NewModeStats(),
      fleet = OpexC73NewModeStats()
    }
  };
}

function OpexC73RecordExamined(mode, count = 1)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (!(mode in C73_VIVIER_LEDGER.modes)) return;
  C73_VIVIER_LEDGER.modes[mode].examined += count;
}

function OpexC73RecordRejection(mode, reason, count = 1)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (!(mode in C73_VIVIER_LEDGER.modes)) return;
  local m = C73_VIVIER_LEDGER.modes[mode];
  if (reason in m.rejections) {
    m.rejections[reason] += count;
  } else {
    m.rejections[reason] <- count;
  }
}

function OpexC73RecordProduced(mode, produced, afterTopK)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (!(mode in C73_VIVIER_LEDGER.modes)) return;
  C73_VIVIER_LEDGER.modes[mode].produced += produced;
  C73_VIVIER_LEDGER.modes[mode].after_topk += afterTopK;
}

function OpexC73RecordSelection(toSelectCounts, affordableCounts, selectedCounts)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  foreach (mode, m in C73_VIVIER_LEDGER.modes) {
    if (mode in toSelectCounts) m.to_select += toSelectCounts[mode];
    if (mode in affordableCounts) m.affordable += affordableCounts[mode];
    if (mode in selectedCounts) m.selected += selectedCounts[mode];
  }
}

function OpexC73RecordPass(built, empty, cash, avail)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  local p = C73_VIVIER_LEDGER.passes;
  p.count++;
  if (built) p.built++;
  if (empty) p.empty++;
  p.sum_cash += cash.tofloat();
  p.sum_avail += avail.tofloat();
}

function OpexC73FlushLedger(year)
{
  if (!C69_BOTTLENECK_PROBE || C73_VIVIER_LEDGER == null) return;
  if (year < 1970) return;
  if (C73_VIVIER_LEDGER.flushedYear == year) return;

  local modeOrder = ["rail", "road", "air", "water", "fleet"];
  foreach (mode in modeOrder) {
    local m = C73_VIVIER_LEDGER.modes[mode];
    local line = "phase=vivier_year year=" + year + " mode=" + mode + " examined=" + m.examined;
    foreach (reason, cnt in m.rejections) {
      line += " rej_" + reason + "=" + cnt;
    }
    line += " produced=" + m.produced + " after_topk=" + m.after_topk
          + " to_select=" + m.to_select + " affordable=" + m.affordable + " selected=" + m.selected;
    OpexC69Log(line);
  }

  local p = C73_VIVIER_LEDGER.passes;
  local avgCash = p.count > 0 ? (p.sum_cash / p.count).tointeger() : 0;
  local avgAvail = p.count > 0 ? (p.sum_avail / p.count).tointeger() : 0;
  OpexC69Log("phase=passes_year year=" + year + " passes=" + p.count + " empty=" + p.empty
      + " built=" + p.built + " avg_cash=" + avgCash + " avg_avail=" + avgAvail);

  OpexC73ResetLedger();
  C73_VIVIER_LEDGER.flushedYear = year;
}

/* C80 : sonde incrementale air sous probe_portfolio */
function OpexC80RecordAirIncremental(kind)
{
  if (!C69_BOTTLENECK_PROBE) return;
  if (kind in C80_AIR_INC_COUNTS) {
    C80_AIR_INC_COUNTS[kind]++;
  }
}

function OpexC80FlushAirIncremental(year)
{
  if (!C69_BOTTLENECK_PROBE) return;
  OpexC69Log("phase=air_incremental_year year=" + year
      + " full=" + C80_AIR_INC_COUNTS.full
      + " targeted=" + C80_AIR_INC_COUNTS.targeted
      + " none=" + C80_AIR_INC_COUNTS.none);
  C80_AIR_INC_COUNTS.full = 0;
  C80_AIR_INC_COUNTS.targeted = 0;
  C80_AIR_INC_COUNTS.none = 0;
}

/* C76 : sonde passive sous C39_INVALIDATION_PROBE (probe_catalogue). */
function OpexC76Log(fields)
{
  if (!C39_INVALIDATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C76_REGEN " + fields);
}

function OpexC76Reset()
{
  C76_PREV_STATE = null;
  C76_YEAR_LEDGER = {};
  C76_EVENTS_SINCE_PREV = { total = 0, by_type = {} };
}

function OpexC76ObserveEvent(eventType)
{
  if (!C39_INVALIDATION_PROBE || C76_EVENTS_SINCE_PREV == null) return;
  C76_EVENTS_SINCE_PREV.total++;
  local typeName = "other";
  if (eventType == AIEvent.ET_ENGINE_AVAILABLE || eventType == AIEvent.ET_ENGINE_PREVIEW) typeName = "engine";
  else if (eventType == AIEvent.ET_INDUSTRY_OPEN) typeName = "ind_open";
  else if (eventType == AIEvent.ET_INDUSTRY_CLOSE) typeName = "ind_close";
  else if (eventType == AIEvent.ET_TOWN_FOUNDED) typeName = "town_founded";
  else if (eventType == AIEvent.ET_SUBSIDY_OFFER || eventType == AIEvent.ET_SUBSIDY_OFFER_EXPIRED
           || eventType == AIEvent.ET_SUBSIDY_AWARDED || eventType == AIEvent.ET_SUBSIDY_EXPIRED) typeName = "subsidy";
  else if (eventType == AIEvent.ET_VEHICLE_CRASHED || eventType == AIEvent.ET_VEHICLE_LOST
           || eventType == AIEvent.ET_VEHICLE_WAITING_IN_DEPOT || eventType == AIEvent.ET_VEHICLE_UNPROFITABLE
           || eventType == AIEvent.ET_VEHICLE_AUTOREPLACED) typeName = "vehicle";
  else if (eventType == AIEvent.ET_STATION_FIRST_VEHICLE) typeName = "station";

  if (typeName in C76_EVENTS_SINCE_PREV.by_type) {
    C76_EVENTS_SINCE_PREV.by_type[typeName]++;
  } else {
    C76_EVENTS_SINCE_PREV.by_type.rawset(typeName, 1);
  }
}

function OpexC76FormatPct(curr, prev)
{
  if (prev == null || prev == 0) return "0.00";
  local delta = (curr.tofloat() - prev.tofloat()) * 100.0 / prev.tofloat();
  local sign = "";
  if (delta < 0.0) {
    sign = "-";
    delta = -delta;
  }
  local whole = delta.tointeger();
  local frac = ((delta - whole) * 100.0 + 0.5).tointeger();
  if (frac >= 100) {
    whole += 1;
    frac -= 100;
  }
  local fracStr = frac < 10 ? "0" + frac : "" + frac;
  return sign + whole + "." + fracStr;
}

function OpexC76FormatRatioPct(num, den)
{
  if (den == null || den <= 0) return (num == 0) ? "100.00" : "0.00";
  local pct = (num.tofloat() * 100.0) / den.tofloat();
  if (pct > 100.0) pct = 100.0;
  if (pct < 0.0) pct = 0.0;
  local whole = pct.tointeger();
  local frac = ((pct - whole) * 100.0 + 0.5).tointeger();
  if (frac >= 100) {
    whole += 1;
    frac -= 100;
  }
  local fracStr = frac < 10 ? "0" + frac : "" + frac;
  return "" + whole + "." + fracStr;
}

function OpexC76GetBuildableEngines(vehicleType)
{
  local res = {};
  local list = AIEngineList(vehicleType);
  for (local e = list.Begin(); !list.IsEnd(); e = list.Next()) {
    if (AIEngine.IsBuildable(e)) {
      res.rawset(e, true);
    }
  }
  return res;
}

function OpexC76CountEngineChanges(curr, prev)
{
  if (prev == null) return 0;
  local count = 0;
  foreach (e, _ in curr) {
    if (!(e in prev)) count++;
  }
  foreach (e, _ in prev) {
    if (!(e in curr)) count++;
  }
  return count;
}

function OpexC76FlushYear(year)
{
  if (!C39_INVALIDATION_PROBE || C76_YEAR_LEDGER == null) return;
  if (year < 1970) return;
  local rec = (year in C76_YEAR_LEDGER) ? C76_YEAR_LEDGER[year] : {
    full = 0, incremental = 0, avoided = 0, ops_total = 0, days_total = 0,
    unchanged_deps = 0, top1_unchanged = 0, reasons = {}
  };
  local avoided = ("avoided" in rec) ? rec.avoided : 0;
  local reasonsStr = "";
  if ("reasons" in rec && typeof rec.reasons == "table") {
    local rList = [];
    foreach (r, count in rec.reasons) {
      rList.append(r + ":" + count);
    }
    if (rList.len() > 0) {
      reasonsStr = " reasons=" + rList[0];
      for (local i = 1; i < rList.len(); i++) {
        reasonsStr += "," + rList[i];
      }
    }
  }
  OpexC76Log("phase=regen_year year=" + year
             + " full=" + rec.full
             + " avoided=" + avoided
             + " incremental=" + rec.incremental
             + " ops_total=" + rec.ops_total
             + " days_total=" + rec.days_total
             + " unchanged_deps=" + rec.unchanged_deps
             + " top1_unchanged=" + rec.top1_unchanged
             + reasonsStr);
}

/* Sonde probe_loop_ops (diagnostic, defaut 0) : agregats annuels de la boucle principale.
 * ops = formule OpexOpsMeasureEnd : un tick traverse compte 10 000 opcodes, y compris un tick
 * passe a attendre une commande de construction. tk = ticks traverses, pour le distinguer.
 * sleep_left = opcodes restants du tick au moment du Sleep(1), donc perdus. */
function OpexLoopProfAddRaw(post, ops, ticks)
{
  if (OPEX_LOOP_PROF == null) OPEX_LOOP_PROF = {};
  local e = (post in OPEX_LOOP_PROF) ? OPEX_LOOP_PROF[post] : null;
  if (e == null) {
    e = { n = 0, ops = 0, ticks = 0, max = 0 };
    OPEX_LOOP_PROF.rawset(post, e);
  }
  e.n++;
  e.ops += ops;
  e.ticks += ticks;
  if (ops > e.max) e.max = ops;
}

function OpexLoopProfAdd(post, mark)
{
  OpexLoopProfAddRaw(post, OpexOpsMeasureEnd(mark), AIController.GetTick() - mark.tick);
}

function OpexLoopProfFlushIfNewYear()
{
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (OPEX_LOOP_PROF_YEAR < 0) {
    OPEX_LOOP_PROF_YEAR = year;
    OPEX_LOOP_PROF_TICK0 = AIController.GetTick();
    return;
  }
  if (year == OPEX_LOOP_PROF_YEAR) return;
  local tick = AIController.GetTick();
  AILog.Info("LOOP_OPS y=" + OPEX_LOOP_PROF_YEAR + " post=_year n=1 ops=0 tk="
      + (tick - OPEX_LOOP_PROF_TICK0) + " max=0");
  if (OPEX_LOOP_PROF != null) {
    foreach (post, e in OPEX_LOOP_PROF) {
      AILog.Info("LOOP_OPS y=" + OPEX_LOOP_PROF_YEAR + " post=" + post + " n=" + e.n
          + " ops=" + e.ops + " tk=" + e.ticks + " max=" + e.max);
    }
  }
  OPEX_LOOP_PROF = {};
  OPEX_LOOP_PROF_YEAR = year;
  OPEX_LOOP_PROF_TICK0 = tick;
}

/* Copie instrumentee de la boucle de main.nut, appelee
 * uniquement sous probe_loop_ops=1 : le chemin par defaut reste celui de main.nut. */
function OpexAI::_mainLoopProfiled()
{
  while (true) {
    if (PROBE_SPAN_TRACE) {
      OpexSpanRescueOrphans();
      OpexSpanYearRoll();
    }
    OpexLoopProfFlushIfNewYear();
    if (C56_TASK_TRACE) {
      C56_LOOP_TICK_COUNT++;
      if (C56_LOOP_TICK_COUNT % 200 == 0) {
        OpexC56TaskLog("LOOP_TICK", "-", this._taskCycle);
      }
    }
    local mark = OpexOpsMeasureBegin();
    local spEvents = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.events") : null;
    this._processEvents();
    if (spEvents != null) OpexSpanEnd(spEvents);
    OpexLoopProfAdd("events", mark);
    if (C121_STATION_FLUX_PROBE) OpexC121StationFluxStep(this._catalog);
    if (C117_AIR_THROUGHPUT_PROBE || C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
      local before = C117_AIR_LAST_DATE;
      mark = OpexOpsMeasureBegin();
      local spC117 = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.c117") : null;
      OpexC117AirThroughputStep(this._lines, this._catalog);
      if (spC117 != null) OpexSpanEnd(spC117);
      OpexLoopProfAdd(C117_AIR_LAST_DATE != before ? "c117_sample" : "c117_skip", mark);
    }
    if (C56_TASK_TRACE) this._v89TrackSearchDays(AIDate.GetCurrentDate());
    mark = OpexOpsMeasureBegin();
    local spOrch = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.orch") : null;
    this._runOrchestratorTick();
    if (spOrch != null) OpexSpanEnd(spOrch);
    OpexLoopProfAdd("orchestrator", mark);
    if (C121_CATALOG_INCREMENTAL) {
      mark = OpexOpsMeasureBegin();
      local continued = false;
      local spResume = null;
      local catalogPending = true;
      local continuationTick = AIController.GetTick();
      while (catalogPending && OpexC121CatalogCanContinue(this, continuationTick)) {
        catalogPending = false;
        foreach (queuedTask in this._taskQueue) {
          if (queuedTask.name == "catalog" && ("c78AirRebuild" in queuedTask)
              && queuedTask.c78AirRebuild != null) {
            if (spResume == null && PROBE_SPAN_TRACE) spResume = OpexSpanBegin("loop.c121_catalog_resume");
            catalogPending = true;
            continued = true;
            local spCat = PROBE_SPAN_TRACE ? OpexSpanBegin("task.catalog") : null;
            this._dispatchCatalog(queuedTask, AIDate.GetYear(AIDate.GetCurrentDate()));
            if (spCat != null) OpexSpanEnd(spCat);
            break;
          }
        }
        if (catalogPending) {
          local spMid = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.orch") : null;
          this._runOrchestratorTick();
          if (spMid != null) OpexSpanEnd(spMid);
        }
      }
      if (spResume != null) OpexSpanEnd(spResume);
      OpexLoopProfAdd(continued ? "catalog_continuation" : "catalog_continuation_check", mark);
    }
    if (V89_RAIL_SEARCH_THROUGHPUT) {
      mark = OpexOpsMeasureBegin();
      local spAstar = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.astar_v89") : null;
      this._advanceRailSearchThroughput();
      if (spAstar != null) OpexSpanEnd(spAstar);
      OpexLoopProfAdd("rail_throughput", mark);
    }
    if (C67_SLACK_HOOK) {
      mark = OpexOpsMeasureBegin();
      local spC67 = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.c67") : null;
      this._c67SlackHook();
      if (spC67 != null) OpexSpanEnd(spC67);
      OpexLoopProfAdd("c67_hook", mark);
    }
    OpexLoopProfAddRaw("sleep_left", AIController.GetOpsTillSuspend(), 0);
    local spSleep = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.sleep") : null;
    AIController.Sleep(1);
    if (spSleep != null) OpexSpanEnd(spSleep);
  }
}

/* probe_span_trace (defaut 0). Jeton = entier >= 1, jamais un objet : pas de
 * destructeur Squirrel. Le parent inclut les opcodes des enfants, y compris
 * les ticks passes a attendre une commande. Eteint : les sites lisent seulement
 * le global. Les tables ne sont pas sauvees sur l'instance. */
function OpexSpanDateText(date)
{
  return AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-" + AIDate.GetDayOfMonth(date);
}

function OpexSpanEventKind(eventType)
{
  if (eventType == AIEvent.ET_VEHICLE_CRASHED) return "event.vehicle_crashed";
  if (eventType == AIEvent.ET_VEHICLE_WAITING_IN_DEPOT) return "event.vehicle_waiting";
  if (eventType == AIEvent.ET_VEHICLE_AUTOREPLACED) return "event.vehicle_autoreplaced";
  if (eventType == AIEvent.ET_VEHICLE_UNPROFITABLE) return "event.vehicle_unprofitable";
  if (eventType == AIEvent.ET_INDUSTRY_CLOSE) return "event.industry_close";
  if (eventType == AIEvent.ET_SUBSIDY_OFFER) return "event.subsidy_offer";
  if (eventType == AIEvent.ET_SUBSIDY_OFFER_EXPIRED) return "event.subsidy_offer_expired";
  if (eventType == AIEvent.ET_SUBSIDY_AWARDED) return "event.subsidy_awarded";
  if (eventType == AIEvent.ET_SUBSIDY_EXPIRED) return "event.subsidy_expired";
  if (eventType == AIEvent.ET_VEHICLE_LOST) return "event.vehicle_lost";
  if (eventType == AIEvent.ET_INDUSTRY_OPEN) return "event.industry_open";
  if (eventType == AIEvent.ET_TOWN_FOUNDED) return "event.town_founded";
  if (eventType == AIEvent.ET_ENGINE_AVAILABLE) return "event.engine_available";
  if (eventType == AIEvent.ET_ENGINE_PREVIEW) return "event.engine_preview";
  if (eventType == AIEvent.ET_STATION_FIRST_VEHICLE) return "event.station_first_vehicle";
  return "event.type_" + eventType;
}

function OpexSpanFlushAgg(rec)
{
  if (rec == null || rec.agg == null) return;
  local date = AIDate.GetCurrentDate();
  local head = "OPEX " + OpexSpanDateText(date) + " SPAN_AGG par=" + rec.id + " ";
  foreach (name, bucket in rec.agg) {
    AILog.Info(head + "n=" + name + " cnt=" + bucket.cnt + " tk=" + bucket.tk + " op=" + bucket.op);
    SPAN_AGG_LINES = SPAN_AGG_LINES + 1;
  }
  rec.agg = null;
}

function OpexSpanEmit(rec, extra)
{
  local op = OpexOpsMeasureEnd(rec.mark);
  local tk = AIController.GetTick() - rec.tick;
  local line = "OPEX " + OpexSpanDateText(AIDate.GetCurrentDate())
      + " SPAN id=" + rec.id
      + " par=" + rec.parentId
      + " dep=" + rec.depth
      + " n=" + rec.name
      + " ds=" + OpexSpanDateText(rec.date)
      + " t0=" + rec.tick
      + " tk=" + tk
      + " op=" + op;
  if (extra != null && extra != "") line = line + " " + extra;
  AILog.Info(line);
  SPAN_LINES = SPAN_LINES + 1;
  OpexSpanFlushAgg(rec);
}

function OpexSpanBegin(name)
{
  if (SPAN_STACK == null) SPAN_STACK = [];
  if (SPAN_BY_ID == null) SPAN_BY_ID = {};
  local parentId = 0;
  local depth = 0;
  if (SPAN_STACK.len() > 0) {
    local top = SPAN_STACK[SPAN_STACK.len() - 1];
    parentId = top.id;
    depth = top.depth + 1;
  }
  local id = SPAN_NEXT_ID;
  SPAN_NEXT_ID = id + 1;
  if (SPAN_NEXT_ID < 1) SPAN_NEXT_ID = 1;
  local rec = {
    id = id,
    parentId = parentId,
    depth = depth,
    name = name,
    date = AIDate.GetCurrentDate(),
    tick = AIController.GetTick(),
    mark = OpexOpsMeasureBegin(),
    agg = null,
    closed = false
  };
  SPAN_STACK.append(rec);
  SPAN_BY_ID.rawset(id, rec);
  return id;
}

function OpexSpanEnd(token, extra = "")
{
  if (token == null || SPAN_BY_ID == null || !(token in SPAN_BY_ID)) return;
  local rec = SPAN_BY_ID[token];
  if (rec.closed) return;
  if (SPAN_STACK != null) {
    while (SPAN_STACK.len() > 0) {
      local top = SPAN_STACK[SPAN_STACK.len() - 1];
      if (top.id == token) break;
      SPAN_STACK.pop();
      if (!top.closed) {
        top.closed = true;
        OpexSpanEmit(top, "orphan=1");
      }
      delete SPAN_BY_ID[top.id];
    }
    if (SPAN_STACK.len() > 0 && SPAN_STACK[SPAN_STACK.len() - 1].id == token) SPAN_STACK.pop();
  }
  rec.closed = true;
  OpexSpanEmit(rec, extra);
  delete SPAN_BY_ID[token];
}

function OpexSpanRescueOrphans()
{
  if (!PROBE_SPAN_TRACE) return;
  if (SPAN_STACK != null) {
    while (SPAN_STACK.len() > 0) {
      local top = SPAN_STACK[SPAN_STACK.len() - 1];
      OpexSpanEnd(top.id, "orphan=1");
    }
  }
  if (SPAN_ROOT_AGG != null) {
    OpexSpanFlushAgg({ id = 0, agg = SPAN_ROOT_AGG });
    SPAN_ROOT_AGG = null;
  }
}

function OpexSpanAgg(name, mark)
{
  if (!PROBE_SPAN_TRACE || mark == null) return;
  local ops = OpexOpsMeasureEnd(mark);
  local tk = AIController.GetTick() - mark.tick;
  local ownerAgg = null;
  if (SPAN_STACK != null && SPAN_STACK.len() > 0) {
    local top = SPAN_STACK[SPAN_STACK.len() - 1];
    if (top.agg == null) top.agg = {};
    ownerAgg = top.agg;
  } else {
    if (SPAN_ROOT_AGG == null) SPAN_ROOT_AGG = {};
    ownerAgg = SPAN_ROOT_AGG;
  }
  local bucket = (name in ownerAgg) ? ownerAgg[name] : null;
  if (bucket == null) {
    bucket = { cnt = 0, tk = 0, op = 0 };
    ownerAgg.rawset(name, bucket);
  }
  bucket.cnt = bucket.cnt + 1;
  bucket.tk = bucket.tk + tk;
  bucket.op = bucket.op + ops;
}

function OpexSpanEvent(kind, fields)
{
  if (!PROBE_SPAN_TRACE) return;
  local line = "OPEX " + OpexSpanDateText(AIDate.GetCurrentDate())
      + " EVT k=" + kind + " t0=" + AIController.GetTick();
  if (fields != null && fields != "") line = line + " " + fields;
  AILog.Info(line);
}

function OpexSpanYearRoll()
{
  if (!PROBE_SPAN_TRACE) return;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (SPAN_YEAR < 0) {
    SPAN_YEAR = year;
    return;
  }
  if (year == SPAN_YEAR) return;
  AILog.Info("OPEX " + OpexSpanDateText(AIDate.GetCurrentDate())
      + " SPAN_SELF lines=" + SPAN_LINES + " agg_lines=" + SPAN_AGG_LINES);
  SPAN_LINES = 0;
  SPAN_AGG_LINES = 0;
  SPAN_YEAR = year;
}

/* V101 : rugosite du segment droit entre deux tuiles, au demarrage d'une recherche
 * rail. Mesure seule, aucun seuil et aucun rejet. Inerte si probe_rail_terrain = 0 :
 * retour avant tout appel d'API. Les tuiles invalides ne comptent pas ; steps et
 * rough comparent les points valides consecutifs dans l'ordre du segment. */
function OpexRailTerrainProbe(src, dst)
{
  if (!RAIL_TERRAIN_PROBE) return;
  local srcX = AIMap.GetTileX(src);
  local srcY = AIMap.GetTileY(src);
  local dstX = AIMap.GetTileX(dst);
  local dstY = AIMap.GetTileY(dst);
  local n = 0;
  local flat = 0;
  local water = 0;
  local bld = 0;
  local hmin = 0;
  local hmax = 0;
  local steps = 0;
  local rough = 0;
  local prevH = null;
  /* 16 points, i = 0 et i = 15 inclus : les deux extremites du segment. */
  for (local i = 0; i < 16; i++) {
    local x = (srcX * (15 - i) + dstX * i) / 15;
    local y = (srcY * (15 - i) + dstY * i) / 15;
    local t = AIMap.GetTileIndex(x, y);
    if (!AIMap.IsValidTile(t)) continue;
    local h = AITile.GetMinHeight(t);
    n++;
    if (AITile.GetSlope(t) == AITile.SLOPE_FLAT) flat++;
    if (AITile.IsWaterTile(t)) water++;
    if (AITile.IsBuildable(t)) bld++;
    if (n == 1) {
      hmin = h;
      hmax = h;
    } else {
      if (h < hmin) hmin = h;
      if (h > hmax) hmax = h;
    }
    if (prevH != null) {
      local dh = h - prevH;
      if (dh != 0) steps++;
      if (dh < 0) dh = -dh;
      rough += dh;
    }
    prevH = h;
  }
  OpexDecide("RAIL_TERRAIN", "src=" + src + " dst=" + dst + " n=" + n
     + " flat=" + flat + " water=" + water + " bld=" + bld
     + " hmin=" + hmin + " hmax=" + hmax + " hspread=" + (hmax - hmin)
     + " steps=" + steps + " rough=" + rough);
}
