/* Boundary routing uses explicit doubles, restored before real comparisons. */
FXI_CALLS <- [];
FXI_EPOCHS <- [];
FXI_CAPTURED <- null;
FXI_MISSING <- false;

function FxIEpoch()
{
  local result = FXI_EPOCHS[0];
  FXI_EPOCHS.remove(0);
  return result;
}

function FxIStub(catalog, plan, plane, fixed = 0, compact = false, floor = null, opening = null)
{
  FXI_CALLS.append(fixed);
  if (opening != null && !FXI_MISSING) {
    FXI_CAPTURED = { token = "opening" };
    opening.initial = FXI_CAPTURED;
  }
  return { token = FXI_CALLS.len() };
}

function FxIBoundaries()
{
  local savedEngine = OpexC121EngineEconomics;
  local savedEpoch = OpexC121WinnerTariffEpoch;
  local savedAAA = C121_AAA_LINE;
  C121_AAA_LINE = false;
  OpexC121EngineEconomics = FxIStub;
  OpexC121WinnerTariffEpoch = FxIEpoch;
  FXI_CALLS = []; FXI_EPOCHS = [12, 12];
  local pair = OpexC121WinnerEconomics(null, null, null, true);
  FxWAssert(FxWEqual(FXI_CALLS, [0]) && pair.initial == FXI_CAPTURED && pair.full.token == 1, "stable_epoch");
  FXI_CALLS = []; FXI_EPOCHS = [12, 13];
  pair = OpexC121WinnerEconomics(null, null, null, true);
  FxWAssert(FxWEqual(FXI_CALLS, [0, 0]) && pair.initial == FXI_CAPTURED && pair.full.token == 2, "new_epoch_refresh");
  FXI_CALLS = []; FXI_EPOCHS = [];
  pair = OpexC121WinnerEconomics(null, null, null, false);
  FxWAssert(FxWEqual(FXI_CALLS, [1, 0]), "off_witness");
  FXI_CALLS = []; C121_AAA_LINE = true;
  pair = OpexC121WinnerEconomics(null, null, null, true);
  FxWAssert(FxWEqual(FXI_CALLS, [2, 0]), "aaa_witness");
  FXI_CALLS = []; C121_AAA_LINE = false; FXI_MISSING = true; FXI_EPOCHS = [12];
  pair = OpexC121WinnerEconomics(null, null, null, true);
  FxWAssert(FxWEqual(FXI_CALLS, [0, 1]) && pair.initial.token == 2, "missing_opening");
  FXI_MISSING = false;
  OpexC121EngineEconomics = savedEngine;
  OpexC121WinnerTariffEpoch = savedEpoch;
  C121_AAA_LINE = savedAAA;
  AILog.Info("C121_INTEGRATION_BOUNDARY checks=5 restored=1 pass=1");
}

function FxIPair(catalog, plan, plane, fusion)
{
  local active = FXW_ACTIVE;
  FXW_ACTIVE = false;
  local pair = OpexC121WinnerEconomics(catalog, plan, plane, fusion);
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
