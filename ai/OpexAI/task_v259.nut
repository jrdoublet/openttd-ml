/* V259 : renouvellement des ponts dont la vitesse limite bride les vehicules.
 * Declenche a l'apparition d'un nouveau type de pont (AIBridgeList comparee a la precedente).
 * Au plus un pont evalue/remplace par passage de la file reactive (curseur).
 * Decision economique sans nombre arbitraire :
 *   - remplacer si vitesse pont < vitesse max des vehicules ET si un modele plus rapide existe pour la longueur
 *   - gain = temps gagne par rotation * profit des vehicules de la ligne (part du cycle sur le pont)
 *   - payer si gain * vie restante des vehicules >= cout mesure (AITestMode + AIAccounting)
 *   - priorite aux ponts des lignes les plus rentables
 * Zero opcode au defaut hors garde O(1). */

function OpexV259CompareBridges(a, b)
{
  if (a.profit > b.profit) return -1;
  if (a.profit < b.profit) return 1;
  return 0;
}

function OpexV259SaveQueue(queue)
{
  if (queue == null) return [];
  local out = [];
  foreach (item in queue) {
    if (item == null || !("bridge" in item) || item.bridge == null) continue;
    local b = item.bridge;
    out.append({
      lineId = ("lineId" in item) ? item.lineId : -1,
      profit = ("profit" in item) ? item.profit : 0,
      start = b.start,
      end = b.end,
      vtype = b.vtype,
      railType = ("railType" in b) ? b.railType : -1
    });
  }
  return out;
}

function OpexV259LoadQueue(data, lines)
{
  if (data == null) return [];
  local out = [];
  local self = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  foreach (item in data) {
    if (item == null || !("start" in item) || !("end" in item)) continue;
    if (!AIBridge.IsBridgeTile(item.start) || AIBridge.GetOtherBridgeEnd(item.start) != item.end) continue;
    if (AITile.GetOwner(item.start) != self) continue;
    local line = null;
    if (lines != null) {
      foreach (l in lines) {
        if (l != null && ("lineId" in l) && l.lineId == item.lineId) {
          line = l;
          break;
        }
      }
    }
    if (line == null) continue;
    out.append({
      bridge = { start = item.start, end = item.end, vtype = item.vtype, railType = item.railType },
      line = line,
      lineId = item.lineId,
      profit = item.profit
    });
  }
  return out;
}

function OpexV259LineProfit(line)
{
  if (line == null) return 0;
  local profit = 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v)) profit += AIVehicle.GetProfitLastYear(v);
    }
  }
  if (profit <= 0 && ("predicted" in line) && line.predicted != null && line.predicted > 0) {
    profit = line.predicted;
  }
  return profit;
}

function OpexV259LineMaxVehicleSpeed(line)
{
  if (line == null) return 0;
  local maxSp = 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v)) {
        local sp = AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v));
        if (sp > maxSp) maxSp = sp;
      }
    }
  }
  if (maxSp <= 0 && ("loco" in line) && line.loco != null) {
    maxSp = AIEngine.GetMaxSpeed(line.loco);
  }
  if (maxSp <= 0 && ("effectiveSpeed" in line) && line.effectiveSpeed != null) {
    maxSp = line.effectiveSpeed;
  }
  return maxSp;
}

function OpexV259LineRemainingYears(line)
{
  if (line == null) return 0.0;
  local sumYears = 0.0;
  local nVeh = 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v)) {
        local remDays = AIVehicle.GetMaxAge(v) - AIVehicle.GetAge(v);
        if (remDays > 0) sumYears += remDays.tofloat() / 365.0;
        nVeh++;
      }
    }
  }
  if (nVeh > 0) return sumYears / nVeh.tofloat();
  if (("loco" in line) && line.loco != null) {
    return AIEngine.GetMaxAge(line.loco).tofloat() / 365.0;
  }
  return 0.0;
}

function OpexV259MeasureBridgeCost(vtype, newBridgeType, start, end)
{
  local currentRailType = (vtype == AIVehicle.VT_RAIL) ? AIRail.GetCurrentRailType() : null;
  local bridgeRailType = (vtype == AIVehicle.VT_RAIL) ? AIRail.GetRailType(start) : null;
  if (vtype == AIVehicle.VT_RAIL && bridgeRailType != null && currentRailType != bridgeRailType) {
    AIRail.SetCurrentRailType(bridgeRailType);
  }
  local account = AIAccounting();
  {
    local testMode = AITestMode();
    AIBridge.BuildBridge(vtype, newBridgeType, start, end);
  }
  local cost = account.GetCosts();
  if (vtype == AIVehicle.VT_RAIL && currentRailType != null && currentRailType != bridgeRailType) {
    AIRail.SetCurrentRailType(currentRailType);
  }
  return cost;
}

function OpexAI::_v259CheckNewBridges()
{
  if (V259_BRIDGE_RENEW == 0) return;
  local date = AIDate.GetCurrentDate();
  local ym = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  if (this._v259LastCheckMonth == ym) return;
  this._v259LastCheckMonth = ym;

  local bridgeList = AIBridgeList();
  local curCount = bridgeList.Count();
  if (this._v259KnownBridgesCount < 0) {
    this._v259KnownBridgesCount = curCount;
    return;
  }
  if (curCount > this._v259KnownBridgesCount) {
    this._v259KnownBridgesCount = curCount;
    this._v259PrepareBridgeQueue();
    this._enqueueReactive("v259_bridge", "v259_bridge", null);
  }
}

function OpexAI::_v259PrepareBridgeQueue()
{
  this._v259Queue = [];
  this._v259Cursor = 0;
  if (this._lines == null) return;

  local self = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  foreach (line in this._lines) {
    if (line == null) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("bridges" in line) || line.bridges == null || line.bridges.len() == 0) continue;

    local profit = OpexV259LineProfit(line);
    local lineId = ("lineId" in line) ? line.lineId : -1;
    foreach (b in line.bridges) {
      if (b == null) continue;
      if (!AIBridge.IsBridgeTile(b.start) || AIBridge.GetOtherBridgeEnd(b.start) != b.end) continue;
      if (AITile.GetOwner(b.start) != self) continue;
      this._v259Queue.append({
        bridge = b,
        line = line,
        lineId = lineId,
        profit = profit
      });
    }
  }

  this._v259Queue.sort(OpexV259CompareBridges);
}

function OpexAI::_v259StepBridgeRenew()
{
  if (V259_BRIDGE_RENEW == 0) return true;
  if (this._v259Queue == null || this._v259Cursor >= this._v259Queue.len()) {
    this._v259Queue = [];
    this._v259Cursor = 0;
    return true;
  }

  local item = this._v259Queue[this._v259Cursor];
  this._v259Cursor++;

  this._v259EvaluateAndRenew(item);

  if (this._v259Cursor < this._v259Queue.len()) {
    this._enqueueReactive("v259_bridge", "v259_bridge", null);
  } else {
    this._v259Queue = [];
    this._v259Cursor = 0;
  }
  return true;
}

function OpexAI::_v259EvaluateAndRenew(item)
{
  if (item == null || !("bridge" in item) || item.bridge == null || !("line" in item) || item.line == null) return;
  local b = item.bridge;
  local line = item.line;
  local lineId = item.lineId;
  local start = b.start;
  local end = b.end;
  local vtype = b.vtype;

  local self = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  if (!AIBridge.IsBridgeTile(start) || AIBridge.GetOtherBridgeEnd(start) != end || AITile.GetOwner(start) != self) return;

  local oldBridgeType = AIBridge.GetBridgeType(start);
  local oldSpeed = AIBridge.GetMaxSpeed(oldBridgeType);
  local maxVehSpeed = OpexV259LineMaxVehicleSpeed(line);

  local len = AIMap.DistanceManhattan(start, end) + 1;
  local bridges = AIBridgeList_Length(len);
  if (bridges.IsEmpty()) {
    if (DECISION_LOG) OpexDecide("V259_BRIDGE", "line=" + lineId + " tiles=" + start + "->" + end
      + " old_type=" + oldBridgeType + " old_speed=" + oldSpeed
      + " new_type=-1 new_speed=-1 cost=0 gain=0 decision=skip_speed");
    return;
  }
  bridges.Valuate(AIBridge.GetMaxSpeed);
  bridges.Sort(AIList.SORT_BY_VALUE, false);
  local bestBridgeType = bridges.Begin();
  local bestSpeed = AIBridge.GetMaxSpeed(bestBridgeType);

  if (oldSpeed >= maxVehSpeed || bestSpeed <= oldSpeed) {
    if (DECISION_LOG) OpexDecide("V259_BRIDGE", "line=" + lineId + " tiles=" + start + "->" + end
      + " old_type=" + oldBridgeType + " old_speed=" + oldSpeed
      + " new_type=" + bestBridgeType + " new_speed=" + bestSpeed
      + " cost=0 gain=0 decision=skip_speed");
    return;
  }

  local newSpeed = (bestSpeed < maxVehSpeed) ? bestSpeed : maxVehSpeed;
  if (newSpeed <= oldSpeed) {
    if (DECISION_LOG) OpexDecide("V259_BRIDGE", "line=" + lineId + " tiles=" + start + "->" + end
      + " old_type=" + oldBridgeType + " old_speed=" + oldSpeed
      + " new_type=" + bestBridgeType + " new_speed=" + bestSpeed
      + " cost=0 gain=0 decision=skip_speed");
    return;
  }

  local bridgeDist = AIMap.DistanceManhattan(start, end);
  local traversals = (("doubleTrack" in line) && line.doubleTrack == 1) ? 1 : 2;
  local oldDays = (traversals * bridgeDist).tofloat() / (0.036 * oldSpeed);
  local newDays = (traversals * bridgeDist).tofloat() / (0.036 * newSpeed);
  local savedDays = oldDays - newDays;

  local cycleDays = 0.0;
  if (("predOneWayDays" in line) && line.predOneWayDays != null && line.predOneWayDays > 0) {
    cycleDays = 2.0 * line.predOneWayDays;
  } else if (("distance" in line) && line.distance > 0 && maxVehSpeed > 0) {
    cycleDays = (2.0 * line.distance).tofloat() / (0.036 * maxVehSpeed);
  }
  if (cycleDays < 1.0) cycleDays = 1.0;

  local cycleFraction = savedDays / cycleDays;
  local lineProfit = OpexV259LineProfit(line);
  local gain = (cycleFraction * lineProfit).tointeger();
  local remainingYears = OpexV259LineRemainingYears(line);

  local cost = OpexV259MeasureBridgeCost(vtype, bestBridgeType, start, end);
  if (cost <= 0) cost = AIBridge.GetPrice(bestBridgeType, len);

  local totalGain = gain.tofloat() * remainingYears;
  if (totalGain < cost.tofloat()) {
    if (DECISION_LOG) OpexDecide("V259_BRIDGE", "line=" + lineId + " tiles=" + start + "->" + end
      + " old_type=" + oldBridgeType + " old_speed=" + oldSpeed
      + " new_type=" + bestBridgeType + " new_speed=" + bestSpeed
      + " cost=" + cost + " gain=" + gain + " decision=skip_unprofitable");
    return;
  }

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexCashReserve();
  if (cost > 0 && cash - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V259_BRIDGE", "line=" + lineId + " tiles=" + start + "->" + end
      + " old_type=" + oldBridgeType + " old_speed=" + oldSpeed
      + " new_type=" + bestBridgeType + " new_speed=" + bestSpeed
      + " cost=" + cost + " gain=" + gain + " decision=skip_cash");
    return;
  }

  local currentRailType = (vtype == AIVehicle.VT_RAIL) ? AIRail.GetCurrentRailType() : null;
  local bridgeRailType = (vtype == AIVehicle.VT_RAIL) ? AIRail.GetRailType(start) : null;
  if (vtype == AIVehicle.VT_RAIL && bridgeRailType != null && currentRailType != bridgeRailType) {
    AIRail.SetCurrentRailType(bridgeRailType);
  }
  local built = AIBridge.BuildBridge(vtype, bestBridgeType, start, end);
  if (vtype == AIVehicle.VT_RAIL && currentRailType != null && currentRailType != bridgeRailType) {
    AIRail.SetCurrentRailType(currentRailType);
  }

  local decision = built ? "renew" : "failed";
  if (DECISION_LOG) OpexDecide("V259_BRIDGE", "line=" + lineId + " tiles=" + start + "->" + end
    + " old_type=" + oldBridgeType + " old_speed=" + oldSpeed
    + " new_type=" + bestBridgeType + " new_speed=" + bestSpeed
    + " cost=" + cost + " gain=" + gain + " decision=" + decision);
}
