/* FLEET-ARB: admission only. Writers retain their validation, commands and rollback.
 * Queue/grants contain live references and are deliberately purged at Load.
 * Only scalar locks survive; ongoing native transactions keep their own journals. */
const FLEET_ARB_QUEUE_LIMIT = 64;
const FLEET_ARB_ACTION_LIMIT = 8;
const FLEET_ARB_HOLD_DAYS = 90;
const FLEET_ARB_RESERVE = 50000;
const FLEET_ARB_OPS = 12000;

function OpexFleetState()
{
  if (FLEET_ARB_STATE == null)
    FLEET_ARB_STATE = { month = -1, queue = [], grants = {}, active = {}, locks = {}, serial = 0 };
  return FLEET_ARB_STATE;
}

function OpexFleetKey(line, mode)
{
  if (line == null) return null;
  if (("lineId" in line) && line.lineId >= 0) return "line:" + line.lineId;
  if (("src" in line) && ("dst" in line) && ("cargo" in line))
    return mode + ":" + line.src + ":" + line.dst + ":" + line.cargo;
  if (("townA" in line) && ("townB" in line))
    return mode + ":town:" + line.townA + ":" + line.townB;
  if (("siteA" in line) && ("siteB" in line) && line.siteA != null && line.siteB != null
      && ("town" in line.siteA) && ("town" in line.siteB)
      && line.siteA.town != null && line.siteB.town != null)
    return mode + ":town:" + line.siteA.town.id + ":" + line.siteB.town.id;
  return null;
}

function OpexFleetLog(event, action, reason)
{
  if (DECISION_LOG) OpexDecide("FLEET_ARB", "event=" + event
      + " line=" + action.key + " mode=" + action.mode + " kind=" + action.kind
      + " source=" + action.source + " cost=" + action.cost
      + " marginal_profit_year=" + action.marginalProfitYear + " reason=" + reason);
}

/* Named comparator: no captured locals, stable FIFO for equal yields.
 * Zero-cost positive savings rank first; sale receipts never finance purchases. */
function OpexFleetCompare(a, b)
{
  if (a.cost == 0 && b.cost > 0) return -1;
  if (b.cost == 0 && a.cost > 0) return 1;
  local left = a.marginalProfitYear.tofloat() * b.cost;
  local right = b.marginalProfitYear.tofloat() * a.cost;
  if (left > right) return -1;
  if (left < right) return 1;
  return a.serial < b.serial ? -1 : (a.serial > b.serial ? 1 : 0);
}

function OpexFleetPending(owner, line)
{
  if (owner == null || line == null || !("lineId" in line)) return false;
  local id = line.lineId;
  foreach (name in ["_v257Pending", "_v271Pending", "_railExpansion",
      "_railLongV2Pending", "_railLongV3UpgradePending", "_railLoopState"]) {
    if (!(name in owner) || owner[name] == null) continue;
    local pending = owner[name];
    if (("lineId" in pending) && pending.lineId == id) return true;
    if (("line" in pending) && pending.line == line) return true;
  }
  if (owner._v284State != null && owner._v284State.pending != null
      && owner._v284State.pending.lineId == id) return true;
  if (V233L_STATE != null && ("pending" in V233L_STATE) && V233L_STATE.pending != null
      && ("lineId" in V233L_STATE.pending) && V233L_STATE.pending.lineId == id) return true;
  if (("scrapping" in line) && line.scrapping) return true;
  if (owner._vehiclesToRetire != null) {
    if (owner._vehiclesToRetire.len() > 64) return true;
    foreach (vehicle, ticket in owner._vehiclesToRetire) {
      local retiredLine = typeof ticket == "table" ? ticket.lineId : ticket;
      if (retiredLine == id) return true;
    }
  }
  return false;
}

/* A small physical fingerprint, not len(VEHS). Unsupported huge consists fail closed. */
function OpexFleetStamp(line)
{
  if (line == null || !("vehicles" in line) || line.vehicles == null) return "none";
  if (line.vehicles.len() > 64) return null;
  local stamp = "";
  foreach (vehicle in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(vehicle)) continue;
    stamp += ":" + vehicle + "/" + AIVehicle.GetEngineType(vehicle);
    if (("cargo" in line)) stamp += "/" + AIVehicle.GetCapacity(vehicle, line.cargo);
    if (AIVehicle.GetVehicleType(vehicle) == AIVehicle.VT_RAIL)
      stamp += "/" + AIVehicle.GetNumWagons(vehicle);
  }
  return stamp;
}

function OpexFleetReserved(exceptKey = null)
{
  local total = 0;
  foreach (key, lock in OpexFleetState().locks)
    if (key != exceptKey && ("reserved" in lock)) total += lock.reserved;
  return total;
}

/* Native transactions recheck this immediately before buying. Restored scalar
 * reservations remain valid; a transaction from an old save may only finish
 * under the live cash floor. Never restart it through the monthly queue. */
function OpexFleetSpendAllowed(line, cost)
{
  local key = OpexFleetKey(line, "rail");
  local state = OpexFleetState();
  if (cost < 0 || cost > OpexAvailableCapital() - FLEET_ARB_RESERVE - OpexFleetReserved(key)) return false;
  if (key != null && (key in state.locks) && ("reserved" in state.locks[key]))
    return cost <= state.locks[key].reserved;
  return OpexFleetPending(FLEET_ARB_OWNER, line);
}

function OpexFleetFinish(line, source, success, reason = "transaction")
{
  if (FLEET_ARB_STATE == null) return;
  local state = FLEET_ARB_STATE;
  foreach (key, action in state.active) {
    if (action.line != line || action.source != source) continue;
    OpexFleetLog(success ? "executed" : "failed", action, reason);
    /* Keep the lock even after failure: a partial rollback may have spent cash. */
    state.locks[key].until = AIDate.GetCurrentDate() + FLEET_ARB_HOLD_DAYS;
    state.locks[key].reserved = 0;
    delete state.active[key];
    return;
  }
}

function OpexFleetResult(line, source, result)
{
  local success = ("ok" in result) ? result.ok : (("added" in result) && result.added > 0);
  OpexFleetFinish(line, source, success, ("reason" in result) ? result.reason : "result");
  return result;
}

/* Runs at the common scheduler entry, including the profiled main loop.
 * Selection is bounded to 64 offers / eight grants per calendar month.
 * Execution stays in the original writer, under its own opcode/transaction budget. */
function OpexFleetTick(owner)
{
  FLEET_ARB_OWNER = owner;
  local state = OpexFleetState();
  local now = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now);
  if (state.month == month) return;
  local mark = OpexOpsMeasureBegin();
  local finished = [];
  foreach (key, action in state.active) {
    if (OpexOpsMeasureEnd(mark) >= FLEET_ARB_OPS) break;
    if ((("lineId" in action.line) && owner._findLineById(action.line.lineId) == null)
        || !OpexFleetPending(owner, action.line)) finished.append(action);
  }
  foreach (action in finished)
    OpexFleetFinish(action.line, action.source,
        OpexFleetStamp(action.line) != action.stamp, "native_transaction_finished");
  /* Reconcile reservations restored without live action references. They cannot
   * be spent by a new writer; release only after its native journal is gone. */
  foreach (key, lock in state.locks) {
    if (!("reserved" in lock) || lock.reserved <= 0 || (key in state.active)) continue;
    local line = lock.lineId >= 0 ? owner._findLineById(lock.lineId) : null;
    if (line != null && OpexFleetPending(owner, line)) continue;
    lock.reserved = 0;
    lock.until = now + FLEET_ARB_HOLD_DAYS;
    if (DECISION_LOG) OpexDecide("FLEET_ARB", "event=refused line=" + key
        + " source=" + lock.source + " reason=load_intent_purged");
  }
  foreach (key, action in state.grants) OpexFleetLog("refused", action, "grant_expired");
  state.grants = {};
  state.month = month;
  local expired = [];
  foreach (key, lock in state.locks)
    if (lock.until <= now && lock.month != month && !(key in state.active)
        && (!("reserved" in lock) || lock.reserved == 0)) expired.append(key);
  foreach (key in expired) delete state.locks[key];
  local budget = OpexAvailableCapital() - FLEET_ARB_RESERVE - OpexFleetReserved();
  state.queue.sort(OpexFleetCompare);
  local selected = 0;
  local deferred = [];
  foreach (action in state.queue) {
    if (OpexOpsMeasureEnd(mark) >= FLEET_ARB_OPS) {
      deferred.append(action);
      continue;
    }
    local reason = "";
    if (now - action.date > 62) reason = "stale";
    else if ((action.key in state.locks) || (action.key in state.grants)
        || OpexFleetPending(owner, action.line)) reason = "line_locked";
    else if (selected >= FLEET_ARB_ACTION_LIMIT) reason = "action_limit";
    else if (action.cost > budget) reason = "budget";
    if (reason != "") { OpexFleetLog("refused", action, reason); continue; }
    state.grants.rawset(action.key, action);
    budget -= action.cost;
    selected++;
    OpexFleetLog("retained", action, "monthly_yield");
  }
  state.queue = deferred;
}

/* Public API: false means deferred/refused and MUST precede any side effect.
 * A true result consumes one grant, freezes a reservation and acquires a line lock.
 * The writer re-quotes on every retry; no saved callback or stale payload is executed. */
function OpexFleetPropose(action)
{
  if (!FLEET_ARB) return true;
  local state = OpexFleetState();
  local now = AIDate.GetCurrentDate();
  action.rawset("key", OpexFleetKey(action.line, action.mode));
  /* Nested initial-build fallback is part of the SAME synchronous transaction. */
  if (action.source == "BUILD_RAIL" && action.key != null && (action.key in state.active)) {
    local running = state.active[action.key];
    if (running.source == action.source && running.line == action.line
        && action.cost != null && action.cost <= running.cost) return true;
  }
  local reason = "";
  if (action.key == null) reason = "line_identity";
  else if (action.kind != "add_vehicle" && action.kind != "add_wagons"
      && action.kind != "sell" && action.kind != "replace" && action.kind != "refit") reason = "kind";
  else if (action.cost == null || action.cost < 0) reason = "cost_unknown";
  else if (action.marginalProfitYear == null) reason = "margin_unknown";
  else if (action.marginalProfitYear <= 0) reason = "nonpositive_margin";
  else if (action.key in state.locks) reason = "recent_action";
  else if (state.locks.len() >= 88) reason = "lock_limit";
  else if (OpexFleetPending(FLEET_ARB_OWNER, action.line)) reason = "transaction_busy";
  if (reason != "") { OpexFleetLog("refused", action, reason); return false; }
  action.cost = action.cost.tointeger();
  if (action.key in state.grants) {
    local granted = state.grants[action.key];
    if (granted.source == action.source && granted.kind == action.kind) {
      delete state.grants[action.key];
      if (action.cost > granted.cost || action.marginalProfitYear < granted.marginalProfitYear
          || OpexFleetStamp(action.line) != granted.stamp) {
        OpexFleetLog("refused", action, "quote_changed");
      } else if (action.cost > OpexAvailableCapital() - FLEET_ARB_RESERVE - OpexFleetReserved()) {
        OpexFleetLog("refused", action, "cash_recheck");
      } else {
        action.rawset("stamp", granted.stamp);
        state.active.rawset(action.key, action);
        state.locks.rawset(action.key, { source = action.source, kind = action.kind,
            until = now + FLEET_ARB_HOLD_DAYS, month = state.month,
            reserved = action.cost, lineId = ("lineId" in action.line) ? action.line.lineId : -1 });
        OpexFleetLog("started", action, "live_revalidation");
        return true;
      }
    }
  }
  foreach (offered in state.queue) {
    if (offered.key != action.key || offered.source != action.source || offered.kind != action.kind) continue;
    offered.cost = action.cost;
    offered.marginalProfitYear = action.marginalProfitYear;
    offered.line = action.line;
    offered.stamp = OpexFleetStamp(action.line);
    offered.date = now;
    return false;
  }
  if (state.queue.len() >= FLEET_ARB_QUEUE_LIMIT) {
    OpexFleetLog("refused", action, "queue_limit"); return false;
  }
  action.rawset("date", now);
  action.rawset("serial", state.serial++);
  action.rawset("stamp", OpexFleetStamp(action.line));
  if (action.stamp == null) { OpexFleetLog("refused", action, "fleet_limit"); return false; }
  state.queue.append(action);
  OpexFleetLog("proposed", action, "queued");
  return false;
}

function OpexFleetBorn(line)
{
  if (line == null || !("lineId" in line)) return;
  local now = AIDate.GetCurrentDate();
  OpexFleetState().locks.rawset("line:" + line.lineId,
      { source = "BUILD", kind = "add_vehicle", until = now + FLEET_ARB_HOLD_DAYS,
        month = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now) });
}

function OpexFleetRequest(line, mode, kind, cost, profit, source)
{
  return OpexFleetPropose({ line = line, mode = mode, kind = kind, cost = cost,
      marginalProfitYear = profit, source = source });
}

function OpexFleetSave()
{
  local out = { version = 1, locks = {} };
  if (FLEET_ARB_STATE == null) return out;
  foreach (key, lock in FLEET_ARB_STATE.locks)
    out.locks.rawset(key, { source = lock.source, kind = lock.kind,
        until = lock.until, month = lock.month,
        reserved = ("reserved" in lock) ? lock.reserved : 0,
        lineId = ("lineId" in lock) ? lock.lineId : -1 });
  return out;
}

function OpexFleetLoad(data)
{
  /* Load precedes settings. Never query the world or trust saved object references. */
  FLEET_ARB_STATE = null;
  FLEET_ARB_OWNER = null;
  local state = OpexFleetState();
  if (data == null || typeof data != "table" || !("version" in data) || data.version != 1
      || !("locks" in data) || typeof data.locks != "table") return;
  foreach (key, lock in data.locks) {
    if (state.locks.len() >= 96) break;
    if (typeof key != "string" || typeof lock != "table"
        || !("source" in lock) || typeof lock.source != "string"
        || !("kind" in lock) || typeof lock.kind != "string"
        || !("until" in lock) || typeof lock.until != "integer"
        || !("month" in lock) || typeof lock.month != "integer") continue;
    state.locks.rawset(key, { source = lock.source, kind = lock.kind,
        until = lock.until, month = lock.month,
        reserved = ("reserved" in lock) && typeof lock.reserved == "integer" && lock.reserved > 0
            ? lock.reserved : 0,
        lineId = ("lineId" in lock) && typeof lock.lineId == "integer" ? lock.lineId : -1 });
  }
}
