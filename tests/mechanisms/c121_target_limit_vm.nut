/* Tests de contrat dans la vraie VM. Les bornes synthetiques ne qualifient
 * pas le modele physique. Tous les reglages/champs modifies sont restaures. */
FXTL_DONE <- false;
FXTL_COUNT <- 0;

function FxTLAssert(ok, name)
{
  if (!ok) throw "C121_TARGET_ASSERT " + name;
  FXTL_COUNT++;
}

function FxTLStart(ai)
{
  FxTLAssert(C121_AIR_ECONOMICS && C121_AIR_TARGET_LIMIT, "settings_loaded");
  FxTLAssert(OpexC121AirTargetLimit(null, 3) == 0, "missing_line");
  FxTLAssert(OpexC121AirTargetLimit({}, 3) == 0, "old_save_missing_target");
  FxTLAssert(OpexC121AirTargetLimit({ targetAirPlanes = 0 }, 3) == 0, "zero_target");
  FxTLAssert(OpexC121AirTargetLimit({ targetAirPlanes = -1 }, 3) == 0, "negative_target");
  FxTLAssert(OpexC121AirTargetLimit({ targetAirPlanes = 16 }, 0) == 0, "zero_physical");
  local oldLine = { targetAirPlanes = 100 };
  FxTLAssert(OpexC121AirTargetLimit(oldLine, 3) == 3, "old_save_high_target");
  FxTLAssert(oldLine.targetAirPlanes == 100, "no_save_mutation");
  FxTLAssert(OpexC121AirTargetLimit({ targetAirPlanes = 2 }, 16) == 2, "economic_limit");
  FxTLAssert(OpexC121AirTargetLimit({ targetAirPlanes = 3 }, 3) == 3, "equal_limits");
  FXTL_DONE = false;
  AILog.Info("C121_TARGET_MATRIX pass=1 assertions=" + FXTL_COUNT);
}

function FxTLWorld(ai)
{
  if (FXTL_DONE) return;
  foreach (line in ai._lines) {
    if (!("mode" in line) || line.mode != "air" || !("vehicles" in line)
        || line.vehicles.len() == 0 || !("targetAirPlanes" in line)) continue;
    local have = 0;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) have++;
    }
    if (have < 1) continue;
    local savedTarget = line.targetAirPlanes;
    local savedV92 = V92_AIR_SERVICE_CHOICE;
    local savedCount = ("vehCount" in line) ? line.vehCount : null;
    local savedFlag = C121_AIR_TARGET_LIMIT;
    local countBefore = line.vehicles.len();
    V92_AIR_SERVICE_CHOICE = false;
    line.targetAirPlanes = have;
    line.vehCount <- have;
    local entry = { line = line, want = 1, planePrice = 100, baseVehicles = have };
    FxTLAssert(OpexProjectFromFleet(entry) == null, "target_reached_no_project");
    FxTLAssert(OpexProjectFitFleetToBudget({ mode = "fleet", payload = entry }, 100000) == null,
        "cached_project_rejected");
    local result = OpexAirAddPlane(line, ai._catalog, ai._lines);
    FxTLAssert(result.added == 0 && result.reason == "TARGET", "final_purchase_guard");
    FxTLAssert(line.vehicles.len() == countBefore, "no_purchase");
    line.targetAirPlanes = 10000;
    local physicalTarget = OpexC121AirPhysicalTarget(line, ai._catalog, ai._lines);
    FxTLAssert(physicalTarget > 0 && physicalTarget <= AIR_MAX_PLANES_PER_ROUTE, "real_physical_cap");
    line.targetAirPlanes = have - 1;
    FxTLAssert(OpexC121AirPhysicalTarget(line, ai._catalog, ai._lines) < have, "already_above_limit");
    FxTLAssert(line.vehicles.len() == countBefore, "no_implicit_sale");
    line.targetAirPlanes = savedTarget;
    V92_AIR_SERVICE_CHOICE = savedV92;
    C121_AIR_TARGET_LIMIT = savedFlag;
    if (savedCount == null) delete line.vehCount;
    else line.vehCount = savedCount;
    FXTL_DONE = true;
    AILog.Info("C121_TARGET_WORLD pass=1 line=" + line.lineId + " assertions=" + FXTL_COUNT);
    return;
  }
}
