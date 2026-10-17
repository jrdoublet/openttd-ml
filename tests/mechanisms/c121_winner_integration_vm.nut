/* The permanent winner route delegates once to the fused N=1/N=2 kernel.
 * Explicit doubles are restored before the numeric fixture comparisons. */
require("c121_fusion_vm.nut");
FXI_CALLS <- 0;
FXI_CAPTURED <- null;

function FxIStub(catalog, plan, plane)
{
  FXI_CALLS++;
  FXI_CAPTURED = { initial = plan, full = plane };
  return FXI_CAPTURED;
}

function FxIBoundaries()
{
  local savedFused = OpexC121OneOrTwoFused;
  OpexC121OneOrTwoFused = FxIStub;
  FXI_CALLS = 0;
  local expectedInitial = { token = "initial" };
  local expectedFull = { token = "full" };
  local pair = OpexC121WinnerEconomics(null, expectedInitial, expectedFull);
  FxWAssert(FXI_CALLS == 1, "single_fused_call");
  FxWAssert(pair == FXI_CAPTURED, "same_result");
  FxWAssert(pair.initial == expectedInitial, "initial_forwarded");
  FxWAssert(pair.full == expectedFull, "full_forwarded");
  OpexC121OneOrTwoFused = savedFused;
  AILog.Info("C121_INTEGRATION_BOUNDARY checks=4 restored=1 pass=1");
}

function FxIPair(catalog, plan, plane, fusion)
{
  local active = FXW_ACTIVE;
  FXW_ACTIVE = false;
  local pair = OpexC121WinnerEconomics(catalog, plan, plane);
  FXW_ACTIVE = active;
  return pair;
}

function FxIStart(owner)
{
  FxIBoundaries();
  FxFStart(owner);
  FxFPair = FxIPair;
  FxWPair = FxIPair;
  AILog.Info("C121_INTEGRATION_START pass=1");
}
