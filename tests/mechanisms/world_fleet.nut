/* Coordinator only in the copied AI. No replacement of production helpers,
 * cash APIs, liveness or builder returns. Bank setup is a real GS command. */
FX <- { version = 1, phase = "search" };

function FxLog(fields)
{
  AILog.Info("FXWORLD " + fields + " date=" + AIDate.GetCurrentDate()
    + " tick=" + AIController.GetTick());
}

function FxIds(line)
{
  local ids = [];
  local owned = AIVehicleList();
  foreach (v in line.vehicles) {
    FxAssert(AIVehicle.IsValidVehicle(v) && AIVehicle.IsPrimaryVehicle(v), "valid_primary");
    FxAssert(owned.HasItem(v), "owner"); // NoAI 15 has no AIVehicle.GetOwner
    FxAssert(AIOrder.GetOrderCount(v) >= 2, "orders_present");
    local a = false;
    local b = false;
    for (local o = 0; o < AIOrder.GetOrderCount(v); o++) {
      local dest = AIOrder.GetOrderDestination(v, o);
      if (AIStation.GetStationID(dest) == AIStation.GetStationID(line.stationA)) a = true;
      if (AIStation.GetStationID(dest) == AIStation.GetStationID(line.stationB)) b = true;
    }
    FxAssert(a && b, "both_station_orders");
    ids.append(v);
  }
  ids.sort();
  return ids;
}

function FxSame(a, b)
{
  if (a.len() != b.len()) return false;
  for (local i = 0; i < a.len(); i++) if (a[i] != b[i]) return false;
  return true;
}

function FxBank(target)
{
  // Real operating expenses can occur between GS acknowledgement and AI wake.
  // Bounded setup retries issue fresh REAL commands; never override cash reads.
  for (local attempt = 0; attempt < 20; attempt++) {
    local sign = AISign.BuildSign(AIMap.GetTileIndex(1, 2), "FXC:" + target);
    FxAssert(AISign.IsValidSign(sign), "bank_request_sign");
    local until = AIController.GetTick() + 2000;
    while (AISign.GetName(sign) != "FXA:" + target) {
      FxAssert(AIController.GetTick() < until, "GS_bank_timeout");
      AIController.Sleep(1);
    }
    FxAssert(AISign.RemoveSign(sign), "bank_request_cleanup");
    FxLog("phase=bank target=" + target + " actual=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
      + " setup_attempt=" + attempt);
    if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) == target) return;
  }
  FxAssert(false, "exact_bank_balance_unexposed");
}

function FxHold()
{
  FxLog("phase=checkpoint state=" + FX.phase + " line=" + FX.lineId);
  // The next monthly save is AT the mechanism boundary: no executor resumes.
  // Normal services keep running; IDs/cash are revalidated after reload.
  while (true) AIController.Sleep(100);
}

function FxSaveProject(project, line)
{
  local scalars = {};
  foreach (key, value in project) {
    if (typeof value == "integer" || typeof value == "string" || typeof value == "bool")
      scalars.rawset(key, value);
  }
  return { fields = scalars, want = project.payload.want,
    price = project.payload.planePrice, baseVehicles = project.payload.baseVehicles,
    lineId = line.lineId };
}

function FxRestoreProject(line)
{
  local p = clone FX.project.fields;
  p.payload <- { want = FX.project.want, planePrice = FX.project.price,
    baseVehicles = FX.project.baseVehicles, line = line };
  return p;
}

function FxEntry(ai, entry)
{
  if (FX.phase != "search" || entry.want != 4) return;
  local original = OpexProjectFromFleet(entry);
  if (original == null) return;
  FX.phase = "preparing";
  local line = entry.line;
  local before = FxIds(line);
  FxLog("phase=producer want=" + entry.want + " line=" + line.lineId + " base=" + entry.baseVehicles);
  FxAssert(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()), "loan_max");
  local price = AIEngine.GetPrice(AIVehicle.GetEngineType(line.vehicles[0]));
  FxAssert(price == entry.planePrice, "producer_actual_price");
  FxBank(price + OpexCashReserve() + 999);
  local budget = AICompany.GetBankBalance(AICompany.COMPANY_SELF) - OpexCashReserve();
  FxAssert(budget == price + 999, "below_precondition");
  local below = OpexProjectSelectAffordable([original], budget, PROJECT_TOP_K);
  FxAssert(below.len() == 0 && FxSame(before, FxIds(line)), "below_no_admission_or_purchase");
  FxLog("scenario=r1_below pass=1 price=" + price + " budget=" + budget);
  FxBank(price + OpexCashReserve() + 1000);
  budget = AICompany.GetBankBalance(AICompany.COMPANY_SELF) - OpexCashReserve();
  FxAssert(budget == price + 1000, "exact_precondition");
  local selected = OpexProjectSelectAffordable([original], budget, PROJECT_TOP_K);
  FxAssert(selected.len() == 1 && selected[0].payload.want == 1 && entry.want == 4, "selected_four_to_one");
  FX = { version = 1, phase = "selected", lineId = line.lineId,
    project = FxSaveProject(selected[0], line), before = before,
    stationA = line.stationA, stationB = line.stationB,
    selectionDate = AIDate.GetCurrentDate(), originalWant = entry.want };
  FxLog("phase=selected want=1 original=4 rank=0 price=" + price + " budget=" + budget);
  FxHold();
}

function FxResume(ai)
{
  if (FX.phase != "selected" && FX.phase != "purchased") return;
  local line = null;
  foreach (candidate in ai._lines) if (candidate.lineId == FX.lineId) line = candidate;
  FxAssert(line != null && line.stationA == FX.stationA && line.stationB == FX.stationB, "reload_line_mapping");
  local ids = FxIds(line);
  local p = FxRestoreProject(line);
  FxLog("phase=reload state=" + FX.phase + " line=" + line.lineId + " base=" + p.payload.baseVehicles
    + " inventory=" + ids.len() + " request=" + p.r1r3Id);
  if (FX.phase == "selected") {
    FxAssert(FxSame(ids, FX.before), "reload_before_ids");
    local price = AIEngine.GetPrice(AIVehicle.GetEngineType(line.vehicles[0]));
    FxAssert(price == p.payload.planePrice, "reload_price_unchanged");
    FxAssert(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()), "reload_loan_max");
    FxBank(price + OpexCashReserve() + 1000);
    R1_R3_TEST_PASS++;
    local attempt = ai._tryBuildFleetProject(AIDate.GetYear(AIDate.GetCurrentDate()), p, 0, []);
    local after = FxIds(line);
    FxAssert(attempt.outcome == "built" && after.len() == ids.len() + 1, "real_one_purchase");
    FxAssert(line.vehCount == after.len(), "purchase_cache");
    foreach (v in ids) {
      local present = false;
      foreach (other in after) if (other == v) present = true;
      FxAssert(present, "no_replacement");
    }
    FX.after <- after;
    FX.phase = "purchased";
    FxLog("scenario=r1_exact pass=1 added=1 before=" + ids.len() + " after=" + after.len());
    FxHold();
  }
  FxAssert(FxSame(ids, FX.after), "reload_after_ids");
  R1_R3_TEST_PASS++;
  local repeated = ai._tryBuildFleetProject(AIDate.GetYear(AIDate.GetCurrentDate()), p, 0, []);
  FxAssert(repeated.outcome == "rejected" && repeated.discards.len() > 0
    && repeated.discards.top().reason == "fleet_stale" && FxSame(ids, FxIds(line)), "same_snapshot_no_duplicate");
  FxLog("scenario=r1_repeat pass=1 reason=fleet_stale");
  FxLog("scenario=r1_reload pass=1 boundaries=2");
  // Independent stale snapshot: admit against current inventory, mutate using
  // the real aircraft helper, reconcile from real IDs, then submit unchanged.
  local entry = { line = line, want = 1, planePrice = p.payload.planePrice, baseVehicles = ids.len() };
  FxBank(entry.planePrice * 3 + OpexCashReserve() + 1000);
  local selected = OpexProjectSelectAffordable([OpexProjectFromFleet(entry)], OpexAvailableCapital(), PROJECT_TOP_K);
  FxAssert(selected.len() == 1, "stale_selected");
  local mutation = OpexAirAddPlane(line, ai._catalog);
  FxAssert(mutation.added == 1, "stale_real_api_mutation");
  local mutated = FxIds(line);
  line.vehCount = mutated.len();
  line.trains = mutated.len();
  R1_R3_TEST_PASS++;
  local refused = ai._tryBuildFleetProject(AIDate.GetYear(AIDate.GetCurrentDate()), selected[0], 0, []);
  FxAssert(refused.outcome == "rejected" && refused.discards.top().reason == "fleet_stale"
    && FxSame(mutated, FxIds(line)), "stale_no_purchase");
  FxLog("scenario=r1_stale pass=1 real_mutation=1");
  FX.phase = "done";
  FxHold();
}