/* RVA : observation seule. Aucun etat ajoute aux lignes ou a Save/Load.
 * Un item (ligne/vehicule) de la file existante par passage d'ordonnanceur.
 * La composition est lue un element par visite, sans boucle sur la flotte.
 * Le lecteur conserve les intervalles d'echantillonnage, jamais des temps exacts. */
RVA_CYCLE_STATE <- null;
RVA_CYCLE_OPS <- 0;
RVA_CYCLE_CALLS <- 0;
RVA_CYCLE_SKIPS <- 0;
RVA_CYCLE_MODEL_OPS <- 0;

function OpexRvaCycleValue(row, key)
{
  return (key in row) ? row[key] : "na";
}

/* Sous le bloc DECISION_LOG existant, apres construction reussie : valeurs du
 * candidat execute, pas une economie recalculee plus tard. */
function OpexRvaCycleModel(lineId, candidate, result)
{
  if (candidate.kind != "pax") return;
  local mark = OpexOpsMeasureBegin();
  OpexDecide("RVA_MODEL", "v=1 line=" + lineId + " model_date=" + AIDate.GetCurrentDate()
      + " a=" + AIStation.GetStationID(result.stationA) + " b=" + AIStation.GetStationID(result.stationB)
      + " one_way_days=" + candidate.oneWayDays
      + " trips_month=" + candidate.tripsPerMonth + " headway_days=" + candidate.headwayDays
      + " income_days=" + OpexCeilDiv(candidate.oneWayDays, 1)
      + " per_train=" + candidate.perTrain + " trains=" + candidate.trains
      + " monthly_capacity=" + candidate.monthlyCapacity
      + " dwell_model_days=" + (30.0 / candidate.tripsPerMonth - candidate.oneWayDays)
      + " per_train2=" + OpexRvaCycleValue(candidate, "perTrain2")
      + " cargo=" + candidate.cargo + " cargo2=" + OpexRvaCycleValue(candidate, "cargo2")
      + " dwell_pct=" + V216F_DWELL_PCT);
  OpexDecide("RVA_MODEL_COST", "line=" + lineId + " ops_prefix=" + OpexOpsMeasureEnd(mark));
  RVA_CYCLE_MODEL_OPS += OpexOpsMeasureEnd(mark);
}

function OpexRvaCycleSample(lines, work)
{
  if (lines == null || lines.len() == 0) return;
  if (work.li >= lines.len()) {
    work.li = 0;
    work.vi = 0;
    work.sweep++;
    OpexDecide("RVA_SWEEP", "sweep=" + work.sweep + " lines=" + lines.len()
        + " eligible=" + work.eligible + " sampled=" + work.sampled + " lost=" + work.lost);
    work.eligible = 0;
    work.sampled = 0;
    work.lost = 0;
    return;
  }
  local line = lines[work.li];
  if (!("mode" in line) || line.mode != "rail" || !("kind" in line) || line.kind != "pax"
      || !("vehicles" in line) || line.vehicles == null || work.vi >= line.vehicles.len()) {
    work.li++;
    work.vi = 0;
    return;
  }
  if (work.vi == 0) work.eligible++;
  local vehicle = line.vehicles[work.vi++];
  local fields = "v=1 seq=" + work.seq + " sweep=" + work.sweep
      + " line=" + line.lineId + " vehicle=" + vehicle + " build_date=" + OpexRvaCycleValue(line, "buildDate")
      + " tick=" + AIController.GetTick() + " date=" + AIDate.GetCurrentDate();
  if (!AIVehicle.IsValidVehicle(vehicle)) {
    work.lost++;
    OpexDecide("RVA_LOST", fields);
    return;
  }
  work.sampled++;
  local tile = AIVehicle.GetLocation(vehicle);
  local state = AIVehicle.GetState(vehicle);
  local station = AIRail.IsRailStationTile(tile) ? AIStation.GetStationID(tile) : AIStation.STATION_INVALID;
  local a = AIStation.GetStationID(line.stationA), b = AIStation.GetStationID(line.stationB);
  local phase = AIVehicle.IsInDepot(vehicle) ? "D" : "R";
  if (state == AIVehicle.VS_AT_STATION) phase = station == a ? "A" : (station == b ? "B" : "X");
  if (state == AIVehicle.VS_CRASHED || state == AIVehicle.VS_INVALID) phase = "X";
  local count = AIVehicle.GetNumWagons(vehicle);
  local wi = count > 0 ? work.sweep % count : -1;
  local cargo = line.cargo;
  local cargo2 = ("cargo2" in line) && AICargo.IsValidCargo(line.cargo2) ? line.cargo2 : work.mail;
  fields += " phase=" + phase + " state=" + state + " tile=" + tile + " a=" + a + " b=" + b
      + " engine=" + AIVehicle.GetEngineType(vehicle) + " age_days=" + AIVehicle.GetAge(vehicle)
      + " length_16tile=" + AIVehicle.GetLength(vehicle) + " parts=" + count
      + " part=" + wi + " part_engine=" + (wi >= 0 ? AIVehicle.GetWagonEngineType(vehicle, wi) : "na")
      + " cargo=" + cargo + " cap=" + AIVehicle.GetCapacity(vehicle, cargo)
      + " load=" + AIVehicle.GetCargoLoad(vehicle, cargo)
      + " cargo2=" + (cargo2 != null ? cargo2 : "na")
      + " cap2=" + (cargo2 != null ? AIVehicle.GetCapacity(vehicle, cargo2) : "na")
      + " load2=" + (cargo2 != null ? AIVehicle.GetCargoLoad(vehicle, cargo2) : "na");
  fields += " order_tile=" + AIOrder.GetOrderDestination(vehicle, AIOrder.ORDER_CURRENT);
  fields += " tick_end=" + AIController.GetTick();
  OpexDecide("RVA_SAMPLE", fields);
}

function OpexRvaCycleStep(lines)
{
  local mark = OpexOpsMeasureBegin();
  RVA_CYCLE_CALLS++;
  // Plancher et reserve des tranches existantes, sans modifier C67.
  if (AIController.GetOpsTillSuspend() < C67_SLACK_MIN) {
    RVA_CYCLE_SKIPS++;
    RVA_CYCLE_OPS += OpexOpsMeasureEnd(mark);
    return;
  }
  if (RVA_CYCLE_STATE == null) {
    local cargos = AICargoList();
    RVA_CYCLE_STATE = { li = 0, vi = 0, sweep = 0, seq = 0, lastOps = null, peakOps = 0,
        eligible = 0, sampled = 0, lost = 0,
        cargos = cargos, cargoCursor = cargos.Begin(), mail = null, mailCount = 0 };
    local units = AIGameSettings.IsValid("economy.timekeeping_units")
        ? AIGameSettings.GetValue("economy.timekeeping_units") : "na";
    OpexDecide("RVA_BEGIN", "v=1 clock=controller_ticks date_clock=calendar_days timekeeping=" + units
        + " model_ticks_day=74 model_days_month=30 length_unit=1/16_tile reset=load_or_start");
  }
  local work = RVA_CYCLE_STATE;
  if (AIController.GetOpsTillSuspend() < work.peakOps + C67_SLACK_RESERVE) {
    RVA_CYCLE_SKIPS++;
    RVA_CYCLE_OPS += OpexOpsMeasureEnd(mark);
    return;
  }
  work.seq++;
  if (work.cargos != null) {
    if (work.cargos.IsEnd()) {
      work.cargos = null;
      OpexDecide("RVA_CARGOS", "mail=" + (work.mail != null ? work.mail : "na")
          + " mail_classes=" + work.mailCount + " scope=line_cargos_and_first_mail");
    } else {
      if (AICargo.HasCargoClass(work.cargoCursor, AICargo.CC_MAIL)) {
        if (work.mail == null) work.mail = work.cargoCursor;
        work.mailCount++;
      }
      work.cargoCursor = work.cargos.Next();
    }
  } else OpexRvaCycleSample(lines, work);
  OpexDecide("RVA_COST", "seq=" + work.seq + " ops_prefix=" + OpexOpsMeasureEnd(mark)
      + " previous_total=" + (work.lastOps != null ? work.lastOps : "na")
      + " completed_ops=" + RVA_CYCLE_OPS + " calls=" + RVA_CYCLE_CALLS
      + " skipped=" + RVA_CYCLE_SKIPS + " model_completed_ops=" + RVA_CYCLE_MODEL_OPS);
  work.lastOps = OpexOpsMeasureEnd(mark);
  RVA_CYCLE_OPS += work.lastOps;
  if (work.lastOps > work.peakOps) work.peakOps = work.lastOps;
}
