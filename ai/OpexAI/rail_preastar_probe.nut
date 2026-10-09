/* Diagnostic seulement : relie les quais disponibles AVANT FindPath a l'issue
 * A* et a la pose. Aucun predicteur, aucune exclusion ni nouveau chemin.
 * Toutes les fonctions sont appelees uniquement si RAIL_PREASTAR_PROBE est actif. */
function OpexRailPreAstarLog(event, fields)
{
  if (!RAIL_PREASTAR_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
      + AIDate.GetDayOfMonth(date) + " RAIL_PREASTAR_" + event + " " + fields);
}

/* Profil local O(nPlans*4), sans A* auxiliaire. Les cases adjacentes libres
 * servent UNIQUEMENT de covariable : un pont ou tunnel peut contourner un
 * voisin ferme, donc un compteur nul n'est pas une preuve d'impossibilite. */
function OpexRailPreAstarAccess(plans)
{
  local entries = [];
  local minFree = 4;
  local maxFree = 0;
  local zeroFree = 0;
  local minWater = 4;
  local width = AIMap.GetMapSizeX();
  local height = AIMap.GetMapSizeY();
  foreach (plan in plans) {
    local x = AIMap.GetTileX(plan.lead);
    local y = AIMap.GetTileY(plan.lead);
    local free = 0;
    local water = 0;
    local rail = 0;
    local neighbors = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    foreach (offset in neighbors) {
      local nx = x + offset[0];
      local ny = y + offset[1];
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
      local tile = AIMap.GetTileIndex(nx, ny);
      if (tile == plan.station_exit) continue;
      if (AITile.IsBuildable(tile)) free++;
      if (AITile.IsWaterTile(tile)) water++;
      if (AIRail.IsRailTile(tile)) rail++;
    }
    if (free < minFree) minFree = free;
    if (free > maxFree) maxFree = free;
    if (water < minWater) minWater = water;
    if (free == 0) zeroFree++;
    entries.append(plan.lead + ":" + plan.station_exit + ":" + free + ":" + water + ":" + rail);
  }
  local signature = "-";
  if (entries.len() > 0) {
    signature = "";
    for (local i = 0; i < entries.len(); i++) {
      if (i > 0) signature += ",";
      signature += entries[i];
    }
  } else {
    minFree = -1;
    minWater = -1;
  }
  return { n = entries.len(), min = minFree, max = maxFree, zero = zeroFree,
           minwater = minWater, plans = signature };
}

function OpexRailPreAstarStart(state, mode, plansA, plansB)
{
  if (!RAIL_PREASTAR_PROBE) return;
  local costMark = OpexOpsMeasureBegin();
  RAIL_PREASTAR_SEQ++;
  local rid = AIController.GetTick() + "_" + RAIL_PREASTAR_SEQ;
  state.preastarRid <- rid;
  if (("segmented" in state) && state.segmented != null)
    state.segmented.preastarRid <- rid;
  local candidate = ("candidate" in state) ? state.candidate : null;
  local line = ("line" in state) ? state.line : null;
  if (candidate != null) candidate.rawset("railPreastarRid", rid);
  local item = candidate != null ? candidate : line;
  local kind = item != null && ("kind" in item) ? item.kind : "-";
  local cargo = item != null && ("cargo" in item) && AICargo.IsValidCargo(item.cargo)
      ? AICargo.GetCargoLabel(item.cargo) : "-";
  local src = item != null && ("src" in item) ? item.src : -1;
  local dst = item != null && ("dst" in item) ? item.dst : -1;
  local lineId = line != null && ("lineId" in line) ? line.lineId : -1;
  local a = OpexRailPreAstarAccess(plansA);
  local b = OpexRailPreAstarAccess(plansB);
  local length = plansA.len() > 0 && ("length" in plansA[0]) ? plansA[0].length : -1;
  local probeOps = OpexOpsMeasureEnd(costMark);
  OpexRailPreAstarLog("START", "rid=" + rid + " mode=" + mode
      + " kind=" + kind + " cargo=" + cargo + " src=" + src + " dst=" + dst
      + " line=" + lineId + " budget=" + state.iterationBudget + " length=" + length
      + " na=" + a.n + " nb=" + b.n + " amin=" + a.min + " amax=" + a.max
      + " azero=" + a.zero + " awater=" + a.minwater + " bmin=" + b.min
      + " bmax=" + b.max + " bzero=" + b.zero + " bwater=" + b.minwater
      + " aps=" + a.plans + " bps=" + b.plans + " probe_ops=" + probeOps);
}

/* Une coupure reellement atteinte par la recherche segmentee. Les nombres
 * proviennent de la frontiere EXISTANTE : aucun nouveau FindPath ni tri. */
function OpexRailPreAstarFrontier(seg, openCount, sampled, viable)
{
  if (!RAIL_PREASTAR_PROBE || !("preastarRid" in seg)) return;
  local prefixLen = seg.prefix == null ? 0 : seg.prefix.len();
  OpexRailPreAstarLog("FRONTIER", "rid=" + seg.preastarRid
      + " segment=" + seg.segments + " iters=" + seg.iterations
      + " used=" + seg.segmentUsed + " open=" + openCount
      + " sampled=" + sampled + " viable=" + viable
      + " backtracks=" + seg.backtracks + " prefix=" + prefixLen);
}

function OpexRailPreAstarEnd(state, stop)
{
  if (!RAIL_PREASTAR_PROBE || !("preastarRid" in state)) return;
  if (("preastarEnded" in state) && state.preastarEnded) return;
  state.preastarEnded <- true;
  local detail = "";
  if (("segmented" in state) && state.segmented != null) {
    local seg = state.segmented;
    local activeOpen = -1;
    if (seg.pathfinder != null && seg.pathfinder._pathfinder != null
        && seg.pathfinder._pathfinder._open != null)
      activeOpen = seg.pathfinder._pathfinder._open.Count();
    detail = " segments=" + seg.segments + " backtracks=" + seg.backtracks
        + " choices=" + seg.localChoices
        + " alternatives=" + seg.alternatives.len()
        + " prefix=" + (seg.prefix == null ? 0 : seg.prefix.len())
        + " active_open=" + activeOpen + " segment_used=" + seg.segmentUsed;
  }
  OpexRailPreAstarLog("END", "rid=" + state.preastarRid + " stop=" + stop
      + " iters=" + state.spent + " budget=" + state.iterationBudget + detail);
}

function OpexRailPreAstarBuild(candidate, result)
{
  if (!RAIL_PREASTAR_PROBE || !("railPreastarRid" in candidate)
      || candidate.railPreastarRid == null) return;
  local reason = result.ok ? "OK" : result.reason;
  OpexRailPreAstarLog("BUILD", "rid=" + candidate.railPreastarRid
      + " reason=" + reason + " ok=" + (result.ok ? 1 : 0)
      + " status=" + (result.ok ? "built" : "failed"));
  candidate.railPreastarRid = null;
}

function OpexRailPreAstarUpgradeBuild(state, result)
{
  if (!RAIL_PREASTAR_PROBE || !("preastarRid" in state)) return;
  OpexRailPreAstarLog("BUILD", "rid=" + state.preastarRid
      + " reason=" + result.reason + " ok=" + (result.ok ? 1 : 0)
      + " status=" + (result.reason == "CASH" ? "cash" : (result.ok ? "built" : "failed")));
}

function OpexRailPreAstarStockReady(state, ready)
{
  if (!RAIL_PREASTAR_PROBE || !("preastarRid" in state)) return;
  OpexRailPreAstarLog("BUILD", "rid=" + state.preastarRid
      + " reason=" + (ready ? "READY" : "STOCK_FAIL")
      + " ok=0 status=" + (ready ? "ready" : "failed"));
}
