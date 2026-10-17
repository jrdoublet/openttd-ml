/* Directed NoAI VM contracts. The runner supplies byte-for-byte legacy helpers
 * from c68d50a (renamed only). No production file loads this fixture. */
function FxKAssert(condition, label)
{
  if (!condition) {
    AILog.Error("C121_KDEC_VM_ASSERT " + label);
    throw "C121 cold K_dec VM contract failed";
  }
}

function FxKStart()
{
  FxKAssert(C121_AIR_ECONOMICS, "economics setting loaded");
  local oldEconomics = C121_AIR_ECONOMICS;
  local oldFactor = C70_MODE_FACTOR.air;
  local oldCalibration = C70_MODE_CALIBRATION;
  C121_AIR_ECONOMICS = true;
  C70_MODE_CALIBRATION = true;
  C70_MODE_FACTOR.air = 0.25;
  local checks = 1;
  foreach (sample in [-2, 0, 1, 8]) {
    foreach (present in [false, true]) {
      foreach (margin in [false, true]) {
        local line = { mode = "air", c121MarginalRevenue = 200 };
        if (present) line.c121MarginalSamples <- sample;
        if (margin) line.c121MarginalProfit <- 100;
        local project = { mode = "fleet", payload = { line = line },
            profitAnnual = 100, profitIsObserved = false };
        FxKAssert(OpexC121ProjectHasRealization(project) == FxKLegacyHasRealization(project), "decision gate");
        FxKAssert(OpexC70Profit(project) == FxKLegacyC70Profit(project), "C70 numerator");
        checks += 2;
      }
    }
  }
  foreach (realized in [false, true]) {
    local project = { mode = "air", payload = { economics = { c121RealizationApplied = realized } } };
    FxKAssert(OpexC121ProjectHasRealization(project) == FxKLegacyHasRealization(project), "AIR unchanged");
    checks++;
  }
  FxKAssert(OpexC121ProjectHasRealization(null) == false, "null project");
  checks++;
  C121_AIR_ECONOMICS = false;
  local offProject = { mode = "fleet", payload = { line = {
      c121MarginalSamples = 1, c121MarginalProfit = 100, c121MarginalRevenue = 200 } } };
  FxKAssert(OpexC121ProjectHasRealization(offProject) == FxKLegacyHasRealization(offProject), "C121 disabled");
  checks++;
  C121_AIR_ECONOMICS = oldEconomics;
  C70_MODE_FACTOR.air = oldFactor;
  C70_MODE_CALIBRATION = oldCalibration;
  AILog.Info("C121_KDEC_VM complete=1 checks=" + checks + " restored=1");
}
