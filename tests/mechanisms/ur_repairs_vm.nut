/* Test-only synthetic API doubles, restored before natural play. */
FXUR_CASE <- "rail";
FXUR_FAILAT <- 1;
FXUR_CALLS <- 0;
FXUR_ERR <- 401;
FXUR_CHECKS <- 0;

function FxURAssert(ok, name)
{
  if (!ok) throw "UR_REPAIRS_ASSERT " + name;
  FXUR_CHECKS++;
}

function FxURRead(value) { FXUR_ERR = 999; return value; }
function FxURBuild(prev, cur, next)
{
  FXUR_CALLS++;
  FXUR_ERR = 401;
  return FXUR_CASE == "connect" || (FXUR_FAILAT != 0 && FXUR_CALLS != FXUR_FAILAT);
}
function FxURConnected(prev, cur, next)
{
  local ok = FXUR_CASE != "connect" || FXUR_CALLS != FXUR_FAILAT;
  if (!ok) FXUR_ERR = 404;
  return ok;
}
function FxURRunRailMatrix()
{
  local saved = { rail = AIRail, road = AIRoad, tile = AITile, map = AIMap,
    error = AIError, tunnel = AITunnel, bridge = AIBridge,
    bridgeList = AIBridgeList_Length, planned = OpexPlannedStructureKind };
  ::AIRail = { BuildRail = FxURBuild, AreTilesConnected = FxURConnected,
    IsRailTile = function(t) { return FxURRead(true); },
    IsRailStationTile = function(t) { return FxURRead(false); } };
  ::AIRoad = { IsRoadTile = function(t) { return FxURRead(false); } };
  ::AITile = { IsBuildable = function(t) { return FxURRead(false); },
    IsWaterTile = function(t) { return FxURRead(false); },
    GetOwner = function(t) { return FxURRead(AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)); },
    GetSlope = function(t) { return FxURRead(0); } };
  ::AIMap = { DistanceManhattan = function(a, b) { return FxURRead(abs(a-b)); } };
  ::AIError = { GetLastError = function() { return FXUR_ERR; } };
  ::AITunnel = { GetOtherTunnelEnd = function(t) { return FxURRead(-1); },
    BuildTunnel = function(v, t) { FXUR_ERR = 403; return false; } };
  ::AIBridge = { GetMaxSpeed = function(b) { return 100; },
    BuildBridge = function(v, b, a, t) { FXUR_ERR = 402; return false; } };
  ::AIBridgeList_Length = function(n) { return {
    Valuate = function(f) {}, Sort = function(k, d) {},
    IsEmpty = function() { return false; }, Begin = function() { return 0; } }; };
  ::OpexPlannedStructureKind = function(s, a, b) {
    return FXUR_CASE == "tunnel" ? "tunnel" : "bridge";
  };
  local thrown = null;
  try {
    foreach (scenario in ["rail", "connect", "bridge", "tunnel", "duplicate", "multiple", "success"]) {
      FXUR_CASE = scenario;
      FXUR_FAILAT = scenario == "duplicate" ? 2 : (scenario == "multiple" ? 0 : (scenario == "success" ? 999 : 1));
      local tiles = scenario == "bridge" || scenario == "tunnel" ? [1,2,5,6] : [1,2,3,2,1];
      local oldFailure = {}, newFailure = {};
      FXUR_CALLS = 0; FXUR_ERR = 401;
      local oldCount = FxURLegacy(tiles, null, oldFailure);
      FXUR_CALLS = 0; FXUR_ERR = 401;
      local newCount = OpexBuildTrack(tiles, null, newFailure);
      FxURAssert(oldCount == newCount, scenario + " count");
      FxURAssert(oldFailure.len() == newFailure.len(), scenario + " fields");
      foreach (key, value in oldFailure) {
        FxURAssert((key in newFailure) && newFailure[key] == value, scenario + " " + key);
      }
      if (scenario != "success") {
        FxURAssert(newFailure.len() == 14, scenario + " complete");
        FxURAssert(newFailure.error == (scenario == "bridge" ? 402 : (scenario == "tunnel" ? 403 : (scenario == "connect" ? 404 : 401))), scenario + " error_saved");
        FxURAssert(newFailure.kind == (scenario == "duplicate" || scenario == "multiple" ? "rail" : scenario), scenario + " kind");
        FxURAssert(newFailure.dup_index == (scenario == "duplicate" ? 1 : -1), scenario + " first_duplicate");
      }
      FXUR_CALLS = 0; FXUR_ERR = 401;
      OpexBuildTrack(tiles, null, null);
      local preset = { index = 77 };
      FXUR_CALLS = 0; FXUR_ERR = 401;
      OpexBuildTrack(tiles, null, preset);
      FxURAssert(preset.len() == 1 && preset.index == 77, scenario + " first_failure_kept");
      AILog.Info("UR_REPAIRS_RAIL case=" + scenario + " pass=1");
    }
  } catch (error) { thrown = error; }
  ::AIRail = saved.rail; ::AIRoad = saved.road; ::AITile = saved.tile;
  ::AIMap = saved.map; ::AIError = saved.error; ::AITunnel = saved.tunnel;
  ::AIBridge = saved.bridge; ::AIBridgeList_Length = saved.bridgeList;
  ::OpexPlannedStructureKind = saved.planned;
  if (thrown != null) throw thrown;
}

function FxTLStart(owner)
{
  foreach (decode in [FxURYear0, FxURYear1, FxURYear2, FxURYear3, FxURYear4]) {
    foreach (year in [0,1970,1999,2000]) {
      for (local month = 1; month <= 12; month++)
        FxURAssert(decode(year * 12 + month) == year, "calendar");
    }
  }
  FxURRunRailMatrix();
  local december = 1970 * 12 + 12;
  if (owner._loadedFromSave)
    FxURAssert(owner._generationStageMonth == december, "december_stamp_loaded");
  else owner._generationStageMonth = december;
  FxURAssert(FxURYear0(owner._generationStageMonth) == 1970, "december_year");
  AILog.Info("UR_REPAIRS_MATRIX pass=1 checks=" + FXUR_CHECKS);
  AILog.Info("UR_REPAIRS_WORLD pass=1 loaded=" + (owner._loadedFromSave ? 1 : 0)
             + " stamp=" + owner._generationStageMonth);
}
function FxTLWorld(owner) {}
