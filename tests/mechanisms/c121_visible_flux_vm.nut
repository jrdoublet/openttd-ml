FXVL_DONE <- false;
FXVL_COUNT <- 0;
function FxVLAssert(ok, name)
{
  if (!ok) throw "C121_VISIBLE_ASSERT " + name;
  FXVL_COUNT++;
}
function FxTLStart(ai)
{
  FxVLAssert(C121_AIR_VISIBLE_COMPETITION, "setting_loaded");
  local alone = { totalWeight = 10, buckets = [{ sum = 0, maxRating = 0, weight = 10, rivals = 0 }] };
  local one = { totalWeight = 10, buckets = [{ sum = 0, maxRating = 0, weight = 10, rivals = 1 }] };
  local two = { totalWeight = 10, buckets = [{ sum = 0, maxRating = 0, weight = 10, rivals = 2 }] };
  local mixed = { totalWeight = 10, buckets = [{ sum = 0, maxRating = 0, weight = 6, rivals = 0 },
      { sum = 0, maxRating = 0, weight = 4, rivals = 1 }] };
  local baseline = OpexC121StationAllocatedMonthly(256.0, 127, alone);
  FxVLAssert(baseline == 128.0, "no_rival_same_capture");
  FxVLAssert(OpexC121StationAllocatedMonthly(256.0, 127, one) == baseline/2, "one_company");
  FxVLAssert(abs(OpexC121StationAllocatedMonthly(256.0, 127, two)-baseline/3) < 0.01, "two_companies");
  FxVLAssert(abs(OpexC121StationAllocatedMonthly(256.0, 127, mixed)-baseline*0.8) < 0.01, "only_shared_sources");
  FXVL_DONE = false;
  AILog.Info("C121_VISIBLE_MATRIX pass=1 assertions=" + FXVL_COUNT);
}
function FxTLWorld(ai)
{
  if (FXVL_DONE) return;
  foreach (line in ai._lines) {
    if (!("mode" in line) || line.mode != "air" || !("c121MarginalProfit" in line)
        || !("c121MarginalRevenue" in line) || line.vehicles.len() == 0) continue;
    local savedSamples = line.c121MarginalSamples;
    local savedProfit = line.c121MarginalProfit;
    local savedRevenue = line.c121MarginalRevenue;
    line.c121MarginalSamples = 1;
    line.c121MarginalProfit = 12345;
    line.c121MarginalRevenue = 23456;
    try {
      OpexC121RefreshVisibleFleet(ai._catalog, line, ai._lines, true);
      FxVLAssert(line.lineId in C121_VISIBLE_FLEET_CACHE, "live_fleet_model_called");
      FxVLAssert(line.targetAirPlanes > 0, "live_target");
      FxVLAssert(line.c121MarginalProfit == 12345 && line.c121MarginalRevenue == 23456,
          "observed_marginal_preserved");
    } catch (error) {
      line.c121MarginalSamples = savedSamples;
      line.c121MarginalProfit = savedProfit;
      line.c121MarginalRevenue = savedRevenue;
      throw error;
    }
    line.c121MarginalSamples = savedSamples;
    line.c121MarginalProfit = savedProfit;
    line.c121MarginalRevenue = savedRevenue;
    OpexC121RefreshVisibleFleet(ai._catalog, line, ai._lines, true);
    FXVL_DONE = true;
    AILog.Info("C121_VISIBLE_WORLD pass=1 assertions=" + FXVL_COUNT);
    return;
  }
}
