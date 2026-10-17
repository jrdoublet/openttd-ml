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
    engine = C82_ENGINE_CALIBRATION, v161 = V161_FLEET_NET_MARGINAL,
    factors = clone C70_MODE_FACTOR, engines = clone C82_ENGINE_FACTOR,
    calibrate = OpexCalibratedProfit };
  /* V161 (defaut 1 depuis le 13/10) plafonne par les voisines reelles : hors champ de cette matrice. */
  V161_FLEET_NET_MARGINAL = 0;
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
            local line = { mode = "air", lineId = 1, vehCount = 1,
              stationA = 1, stationB = 2, cargo = 0, planeId = 7,
              lastProfit = observed ? 10000 : 0, predRevenue = 12000,
              predRunning = 2000, predTrains = 1 };
            local entry = { line = line, want = quantity, planePrice = 30007, baseVehicles = 1 };
            local p = OpexProjectFromFleet(entry);
            FxAssert(p != null && p.profitIsObserved == observed, "provenance");
            local before = p.profitAnnual;
            local expected = observed ? before : OpexCalibratedProfit(p);
            FxAssert(p.profitAnnual == before && entry.want == quantity && p.payload == entry,
              "immutable_input");
            if (quantity == 4) {
              local fitted = OpexProjectFitFleetToBudget(p, 31007);
              FxAssert(fitted != null && fitted.payload.want == 1 && entry.want == 4, "R1_4_to_1");
              FxAssert(OpexProjectFitFleetToBudget(p, 31006) == null, "R1_below");
              FxAssert(fitted.profitIsObserved == observed, "R2_after_R1");
            }
            cases++;
            AILog.Info("FXVM case=" + cases + " calibration=" + calibration + " factor=" + factor
              + " observed=" + (observed ? 1 : 0) + " quantity=" + quantity + " life=" + life
              + " calibrated=" + expected + " pass=1");
          }
        }
      }
    }
  }
  FxAssert(OpexProjectScore(-1, 10) == 0.0, "negative_score");
  C70_PROFIT_CALIBRATED = saved.c70;
  C70_MODE_CALIBRATION = saved.mode;
  C82_ENGINE_CALIBRATION = saved.engine;
  V161_FLEET_NET_MARGINAL = saved.v161;
  C70_MODE_FACTOR = saved.factors;
  C82_ENGINE_FACTOR = saved.engines;
  OpexCalibratedProfit = saved.calibrate;
  AILog.Info("FXVM complete=1 cases=" + cases + " boundary_checks=1 settings_restored=1");
}