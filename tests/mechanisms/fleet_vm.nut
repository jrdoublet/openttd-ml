/* Test-only: loaded solely in a copied AI by run_mechanism_fixtures.py.
 * Real production functions in OpenTTD's VM, synthetic arithmetic inputs.
 * This matrix proves no world mutation or economic benefit. */
function FxAssert(ok, name)
{
  if (!ok) throw "FIXTURE_ASSERT " + name;
}

function FxMatrix()
{
  local saved = { c70 = C70_PROFIT_CALIBRATED, mode = C70_MODE_CALIBRATION,
    engine = C82_ENGINE_CALIBRATION, v92 = V92_AIR_SERVICE_CHOICE,
    c84 = C84_AIR_TARGET_FLEET, c121 = C121_AIR_ECONOMICS,
    factors = clone C70_MODE_FACTOR, engines = clone C82_ENGINE_FACTOR,
    calibrate = OpexCalibratedProfit };
  C84_AIR_TARGET_FLEET = false;
  C121_AIR_ECONOMICS = false;
  C70_PROFIT_CALIBRATED = true;
  C70_MODE_CALIBRATION = true;
  C82_ENGINE_CALIBRATION = true;
  local cases = 0;
  foreach (calibration in ["C70", "C82"]) {
    OpexCalibratedProfit = calibration == "C70" ? OpexC70Profit : OpexC82Profit;
    foreach (factor in [0.5, 1.0, 1.5]) {
      C70_MODE_FACTOR.air = factor;
      C82_ENGINE_FACTOR.rawset(7, factor); // synthetic engine ID, never used in an API
      foreach (observed in [false, true]) {
        foreach (quantity in [1, 4]) {
          foreach (life in [20, 13]) {
            V92_AIR_SERVICE_CHOICE = life != 20;
            local line = { mode = "air", lineId = 1, vehCount = 1,
              stationA = 1, stationB = 2, cargo = 0, planeId = 7,
              lastProfit = observed ? 10000 : 0, predRevenue = 12000,
              predRunning = 2000, predTrains = 1 };
            local entry = { line = line, want = quantity, planePrice = 30007, baseVehicles = 1 };
            local p = OpexProjectFromFleet(entry);
            FxAssert(p != null && p.profitIsObserved == observed, "provenance");
            local before = p.profitAnnual;
            local shadow = OpexFleetAmortShadow(p, true, { ageYears = life });
            local amort = quantity * 30007 / life;
            local net = before - amort;
            local expected = observed ? net : net * factor;
            FxAssert(shadow.addedAmortAnnual == amort, "multiply_before_divide");
            FxAssert(shadow.netProfitAnnual == net && shadow.calibratedProfitAnnual == expected,
              "calibration_once");
            FxAssert(p.profitAnnual == before && entry.want == quantity && p.payload == entry,
              "immutable_input");
            if (quantity == 4) {
              local fitted = OpexProjectFitFleetToBudget(p, 31007);
              FxAssert(fitted != null && fitted.payload.want == 1 && entry.want == 4, "R1_4_to_1");
              local reduced = OpexFleetAmortShadow(fitted, true, { ageYears = life });
              FxAssert(reduced.quantity == 1 && reduced.addedAmortAnnual == 30007 / life,
                "R1_recompute_amort");
              FxAssert(OpexProjectFitFleetToBudget(p, 31006) == null, "R1_below");
              FxAssert(fitted.profitIsObserved == observed, "R2_after_R1");
            }
            cases++;
            AILog.Info("FXVM case=" + cases + " calibration=" + calibration + " factor=" + factor
              + " observed=" + (observed ? 1 : 0) + " quantity=" + quantity + " life=" + life
              + " amort=" + amort + " net=" + net + " calibrated=" + expected + " pass=1");
          }
        }
      }
    }
  }
  V92_AIR_SERVICE_CHOICE = false;
  local p = { mode = "fleet", profitAnnual = 100, profitIsObserved = false,
    payload = { want = 1, planePrice = 2000, line = { mode = "air" } } };
  FxAssert(OpexFleetAmortShadow(p) == null, "OFF");
  FxAssert(OpexFleetAmortShadow(p, true).netProfitAnnual == 0, "zero_net");
  p.profitAnnual = 99;
  FxAssert(OpexFleetAmortShadow(p, true).netProfitAnnual == -1, "negative_net");
  FxAssert(OpexProjectScore(-1, 10) == 0.0, "negative_score");
  C70_PROFIT_CALIBRATED = false;
  FxAssert(OpexFleetAmortShadow(p, true).calibratedProfitAnnual == -1, "calibration_OFF");
  V92_AIR_SERVICE_CHOICE = true;
  FxAssert(OpexFleetAmortShadow(p, true) == null, "V92_missing_plane");
  FxAssert(OpexFleetAmortShadow(p, true, { ageYears = 1 }).lifeYears == 20, "V92_fallback");
  C84_AIR_TARGET_FLEET = true;
  FxAssert(OpexFleetAmortShadow(p, true, {}) == null, "C84_excluded");
  C84_AIR_TARGET_FLEET = false;
  C121_AIR_ECONOMICS = true;
  FxAssert(OpexFleetAmortShadow(p, true, {}) == null, "C121_excluded");
  C70_PROFIT_CALIBRATED = saved.c70;
  C70_MODE_CALIBRATION = saved.mode;
  C82_ENGINE_CALIBRATION = saved.engine;
  V92_AIR_SERVICE_CHOICE = saved.v92;
  C84_AIR_TARGET_FLEET = saved.c84;
  C121_AIR_ECONOMICS = saved.c121;
  C70_MODE_FACTOR = saved.factors;
  C82_ENGINE_FACTOR = saved.engines;
  OpexCalibratedProfit = saved.calibrate;
  AILog.Info("FXVM complete=1 cases=" + cases + " boundary_checks=9 settings_restored=1");
}