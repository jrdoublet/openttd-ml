/* Compare the retained settings against the pre-removal helper with the
 * abandoned project-realization switch OFF. Runner supplies that helper. */
function FxPStart()
{
  local oldAdaptive = C121_AIR_PROJECT_REALIZATION_ADAPTIVE;
  local oldDirectActive = AIR_P0_DIRECT_REALIZATION_ACTIVE;
  local oldLearned = clone C121_AIR_REALIZATION_FACTOR;
  local oldDirect = clone C121_AIR_P0_DIRECT_FACTOR;
  local checks = 0;
  foreach (adaptive in [false, true]) {
    C121_AIR_PROJECT_REALIZATION_ADAPTIVE = adaptive;
    foreach (active in [false, true]) {
      AIR_P0_DIRECT_REALIZATION_ACTIVE = active;
      foreach (arm in ["newpair", "hubsite", "hubhub", "unknown"]) {
        foreach (learned in [-0.1, 0.0, 0.7, 1.0, 1.2]) {
          if (arm in C121_AIR_REALIZATION_FACTOR) C121_AIR_REALIZATION_FACTOR[arm] = learned;
          foreach (direct in [0.7, 1.2]) {
            if (arm in C121_AIR_P0_DIRECT_FACTOR) C121_AIR_P0_DIRECT_FACTOR[arm] = direct;
            local plan = { arm = arm };
            FxKAssert(OpexC121RealizationFactor(plan) == FxPLegacyRealizationFactor(plan), "project factor parity");
            checks++;
          }
        }
      }
    }
  }
  foreach (plan in [null, {}]) {
    FxKAssert(OpexC121RealizationFactor(plan) == FxPLegacyRealizationFactor(plan), "invalid plan parity");
    checks++;
  }
  C121_AIR_PROJECT_REALIZATION_ADAPTIVE = oldAdaptive;
  AIR_P0_DIRECT_REALIZATION_ACTIVE = oldDirectActive;
  C121_AIR_REALIZATION_FACTOR = oldLearned;
  C121_AIR_P0_DIRECT_FACTOR = oldDirect;
  AILog.Info("C121_PROJECT_CLEANUP_VM complete=1 checks=" + checks + " restored=1");
}
