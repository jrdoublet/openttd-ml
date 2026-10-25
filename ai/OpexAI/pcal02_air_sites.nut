/* PCAL-02 prototype OFF. No catalogue, commands only inside AITestMode.
 * Flat footprints only: one tile per step, no synchronous LevelTiles/AIList.
 * These transient globals never enter Save(); Start resets them after Load. */
PCAL02_TICK_BUDGET <- 4000;
PCAL02_SLEEP_RESERVE <- 2000;
PCAL02_ATOM_RESERVE <- 1200;
PCAL02_TAIL_RESERVE <- 600;
PCAL02_MAX_STEPS <- 16;
PCAL02_MAX_ENTRIES <- 8;
PCAL02_TOP_K <- 2;
PCAL02_TTL_DAYS <- 90;
PCAL02_MAX_ANCHORS <- 512;
PCAL02_STATE <- { entries = [], epoch = 0, sequence = 0, catalog = null,
    lastTick = -1, fault = false, totalOps = 0, maxOps = 0 };

function OpexPCAL02Reset()
{
  PCAL02_STATE.entries = [];
  PCAL02_STATE.catalog = null;
  PCAL02_STATE.epoch++;
  PCAL02_STATE.lastTick = -1;
  PCAL02_STATE.fault = false;
  PCAL02_STATE.totalOps = 0;
  PCAL02_STATE.maxOps = 0;
}

function OpexPCAL02Log(action, entry, spent, saved, extra = "")
{
  if (!DECISION_LOG) return;
  OpexDecide("PCAL02", action + " town=" + entry.town.id + " type=" + entry.airport.type
      + " id=" + entry.id + " op_spent=" + spent + " op_saved=" + saved + " " + extra);
}

function OpexPCAL02Combo(airport)
{
  local catalog = PCAL02_STATE.catalog;
  if (catalog == null || catalog.airCombos == null) return null;
  /* The current catalogue contains at most large/small, no engine scan. */
  foreach (combo in catalog.airCombos) {
    if (combo.airport.type == airport.type && combo.airport.width == airport.width
        && combo.airport.height == airport.height
        && AIEngine.IsBuildable(combo.plane.id)
        && OpexAirAirportAcceptsPlane(airport.type, combo.plane.planeType)) return combo;
  }
  return null;
}

function OpexPCAL02Expiry(entry, airport)
{
  local date = AIDate.GetCurrentDate();
  if (date < entry.date) return "date_reversed";
  if (date - entry.date >= PCAL02_TTL_DAYS) return "ttl";
  if (entry.airport.type != airport.type || entry.airport.width != airport.width
      || entry.airport.height != airport.height) return "dimensions";
  if (!AITown.IsValidTown(entry.town.id)) return "town";
  /* A queued demand has no geometry or engine to invalidate. In particular,
   * another line's build must not erase all still-unstarted demands. */
  if (entry.plane == null) return "none";
  if (entry.epoch != PCAL02_STATE.epoch) return "epoch";
  if (AIDate.GetYear(date) != entry.year) return "year";
  local combo = OpexPCAL02Combo(airport);
  /* Catalogue/airCombos tables are replaced during ordinary publication.
   * Only a changed compatible engine matters to this flat geometric search. */
  if (combo == null || combo.plane.id != entry.plane.id) return "engine";
  return "none";
}

function OpexPCAL02Fresh(entry, airport)
{
  return OpexPCAL02Expiry(entry, airport) == "none";
}

/* Demand comes ONLY from the existing C78/V278 site consumer. Priority by
 * population, stable ties; bounded stock, no writes to its batch or towns. */
function OpexPCAL02Request(town, airport)
{
  local stock = PCAL02_STATE.entries;
  foreach (entry in stock) {
    if (entry.town.id == town.id && entry.airport.type == airport.type) return entry;
  }
  local pos = 0;
  while (pos < stock.len() && stock[pos].town.pop >= town.pop) pos++;
  if (pos >= PCAL02_MAX_ENTRIES) return null;
  if (stock.len() >= PCAL02_MAX_ENTRIES) stock.pop();
  PCAL02_STATE.sequence++;
  local date = AIDate.GetCurrentDate();
  local entry = { id = PCAL02_STATE.sequence,
      town = { id = town.id, tile = town.tile, pop = town.pop },
      airport = { type = airport.type, width = airport.width, height = airport.height },
      plane = null, date = date,
      year = AIDate.GetYear(date), epoch = PCAL02_STATE.epoch, ready = false,
      top = [], credited = false, ops = 0, r = 4, dx = -4, dy = -4,
      phase = 0, anchor = -1, tileIndex = 0, z = 0, tested = 0,
      firstRing = -1, valid = 0, cost = 0, pax = 0, mail = 0 };
  stock.insert(pos, entry);
  return entry;
}

function OpexPCAL02Drop(index, reason)
{
  local entry = PCAL02_STATE.entries[index];
  OpexPCAL02Log("stale", entry, 0, 0, "reason=" + reason
      + " cause=" + OpexPCAL02Expiry(entry, entry.airport)
      + " age_days=" + (AIDate.GetCurrentDate() - entry.date) + " prepared_ops=" + entry.ops);
  PCAL02_STATE.entries.remove(index);
}

/* Lookup is not a build. Provenance travels with the immutable chosen anchor
 * through C121 and is checked again at the physical AIR construction. */
function OpexPCAL02FindSite(town, airport, probes)
{
  local mark = OpexOpsMeasureBegin();
  local stock = PCAL02_STATE.entries;
  for (local i = 0; i < stock.len(); i++) {
    local entry = stock[i];
    if (entry.town.id != town.id || entry.airport.type != airport.type) continue;
    if (!OpexPCAL02Fresh(entry, airport)) {
      OpexPCAL02Drop(i, "lookup_expired");
      break;
    }
    if (!entry.ready) break;
    if (entry.top.len() == 0) break;
    foreach (item in entry.top) {
      local site = { town = town, anchor = item.anchor };
      local limited = probes != null && ("stationLimitedTowns" in probes)
          ? probes.stationLimitedTowns : null;
      if (!OpexAirSiteStillBuildable(site, airport, entry.plane, false, limited)
          || !OpexAirSiteHasCatchment(site.anchor, airport, OpexAirDemandPaxCargo())) continue;
      if (!OpexPCAL02Fresh(entry, airport)) break;
      site.pcal02 <- { id = entry.id, date = entry.date, year = entry.year,
          epoch = entry.epoch, engine = entry.plane.id, type = airport.type,
          cost = item.cost, preparedOps = entry.ops };
      AIR_SITE_CACHE.rawset(town.id + "_" + airport.type, site.anchor);
      local spent = OpexOpsMeasureEnd(mark);
      local saved = entry.credited ? 0 : entry.ops - spent;
      entry.credited = true;
      OpexPCAL02Log("hit", entry, spent, saved,
          "phase=lookup anchor=" + site.anchor + " saved_kind=prepared_proxy");
      return site;
    }
    OpexPCAL02Drop(i, "lookup_unbuildable");
    break;
  }
  local requested = OpexPCAL02Request(town, airport);
  if (requested != null) OpexPCAL02Log("miss", requested, OpexOpsMeasureEnd(mark), 0, "phase=lookup");
  return null;
}

function OpexPCAL02Room(mark)
{
  if (AIController.GetTick() != mark.tick) return false;
  local left = AIController.GetOpsTillSuspend();
  return left >= PCAL02_SLEEP_RESERVE + PCAL02_ATOM_RESERVE + PCAL02_TAIL_RESERVE
      && mark.left - left + PCAL02_ATOM_RESERVE + PCAL02_TAIL_RESERVE <= PCAL02_TICK_BUDGET;
}

/* Observe the next dispatch without moving either queue. Non-rail workers
 * return before the background queue; rail workers deliberately fall through.
 * A raw airPlan is never an executable project. C78 and PO01c may coexist
 * with a published selection, so their mere presence says nothing either. */
function OpexPCAL02BuildTurn(owner, mark)
{
  if (owner._activeWorker != null && owner._activeWorker.kind != "rail_search"
      && owner._activeWorker.kind != "rail_stock") return "worker_wait";
  if (owner._projects == null || owner._portfolioInvalidated) return "portfolio_wait";
  local queue = owner._reactiveQueue;
  if (queue != null && !queue.isEmpty()) {
    local intention = queue.get(queue._order[queue._head]);
    if (intention != null && intention.kind == "c77_build"
        && !(C77_INTENT_DEFER && (owner._activeWorker != null
            || (C77_INTENT_DEFER_SUBSIDY && PO01C_REGEN_SPLIT
                && (owner._po01cPending || owner._po01cJob != null))))) return "reactive";
  }
  /* Same suffix / next-cycle search as _runNextTask. Inspect only; neither
   * dueCycle nor the cursor is changed, and every iteration is budgeted. */
  for (local index = owner._taskCursor; index < owner._taskQueue.len(); index++) {
    if (!OpexPCAL02Room(mark)) return "room";
    local task = owner._taskQueue[index];
    if (task.enabled && task.dueCycle <= owner._taskCycle)
      return task.name == "projects" ? "projects" : "queue_wait";
  }
  foreach (task in owner._taskQueue) {
    if (!OpexPCAL02Room(mark)) return "room";
    if (task.enabled && task.dueCycle <= owner._taskCycle + 1)
      return task.name == "projects" ? "projects" : "queue_wait";
  }
  return "queue_wait";
}

/* Fail closed if the readiness check cannot finish. Only the selected AIR
 * projects with an available dispatch path veto background geometry; waiting
 * workers/lots and merely fundable airPlans must leave the spare tick usable.
 * This is a conservative veto, not a second selection or builder preflight. */
function OpexPCAL02Admit(owner, mark)
{
  if (!MODE_AIR) return "mode_off";
  if (owner._catalog == null) return "catalog_missing";
  if (!OpexPCAL02Room(mark)) return "room";
  local turn = OpexPCAL02BuildTurn(owner, mark);
  if (turn == "room") return "room";
  if (turn != "projects" && turn != "reactive") return "none";
  /* OpexCashReserve scans the entire fleet. MIN is a lower bound on the
   * live reserve: overestimate available cash to reject MORE background work,
   * never miss an AIR project merely because a snapshot reserve is stale. */
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF) - CASH_RESERVE_MIN;
  foreach (project in owner._projects.best) {
    if (!OpexPCAL02Room(mark)) return "room";
    if (project != null && project.mode == "air"
        && OpexProjectFinanceCapital(project) <= cash) return "best_air";
  }
  return OpexPCAL02Room(mark) ? "none" : "room";
}

/* Advance exactly one perimeter anchor, X then Y like FindSiteListed. */
function OpexPCAL02Next(entry)
{
  if (abs(entry.dx) == entry.r) entry.dy++;
  else entry.dy = entry.dy < entry.r ? entry.r : entry.r + 1;
  if (entry.dy > entry.r) { entry.dx++; entry.dy = -entry.r; }
  if (entry.dx > entry.r) { entry.r++; entry.dx = -entry.r; entry.dy = -entry.r; }
  entry.phase = 0;
}

function OpexPCAL02Keep(entry)
{
  local item = { anchor = entry.anchor, pax = entry.pax, mail = entry.mail, cost = entry.cost };
  local at = 0;
  while (at < entry.top.len()) {
    local other = entry.top[at];
    if (item.pax > other.pax || (item.pax == other.pax && item.mail > other.mail)
        || (item.pax == other.pax && item.mail == other.mail && item.cost < other.cost)) break;
    at++;
  }
  if (at < PCAL02_TOP_K) {
    entry.top.insert(at, item);
    if (entry.top.len() > PCAL02_TOP_K) entry.top.pop();
  }
  entry.valid++;
  if (entry.firstRing < 0) entry.firstRing = entry.r;
}

/* Every branch is a fixed-size native operation or ONE footprint tile.
 * No AITestMode/AIAccounting object survives a step or a suspension. */
function OpexPCAL02Step(entry, catalog)
{
  if (entry.phase == 0) {
    if (entry.r > AIR_SITE_RADIUS || entry.tested >= PCAL02_MAX_ANCHORS
        || entry.valid >= C96_AIR_SITE_MAX_VALID
        || (entry.firstRing >= 0 && entry.r > entry.firstRing + C96_AIR_SITE_EXTRA_RINGS)) {
      entry.ready = true;
      return;
    }
    entry.tested++;
    local x = AIMap.GetTileX(entry.town.tile) + entry.dx;
    local y = AIMap.GetTileY(entry.town.tile) + entry.dy;
    local ap = entry.airport;
    /* Include the LevelTiles terminal boundary, even though this worker is flat-only. */
    if (x < 1 || y < 1 || x + ap.width >= AIMap.GetMapSizeX() - 1
        || y + ap.height >= AIMap.GetMapSizeY() - 1) { OpexPCAL02Next(entry); return; }
    entry.anchor = AIMap.GetTileIndex(x, y);
    if (OpexAirDistanceToRect(entry.town.tile, entry.anchor, ap.width, ap.height) > 25
        || AIAirport.GetNearestTown(entry.anchor, ap.type) != entry.town.id
        || !AITile.IsBuildableRectangle(entry.anchor, ap.width, ap.height)) {
      OpexPCAL02Next(entry); return;
    }
    entry.z = AITile.GetMaxHeight(entry.anchor);
    entry.tileIndex = 0;
    entry.phase = 1;
  } else if (entry.phase == 1) {
    local ap = entry.airport;
    local tile = entry.anchor + AIMap.GetTileIndex(entry.tileIndex % ap.width, entry.tileIndex / ap.width);
    /* Same cheap footprint predicates; stricter flat-only subset of C36/C4. */
    if (AITile.IsWaterTile(tile) || AITile.IsCoastTile(tile) || AITile.IsRiverTile(tile)
        || AITile.GetMaxHeight(tile) != entry.z || entry.z - AITile.GetMinHeight(tile) >= 2) {
      OpexPCAL02Next(entry); return;
    }
    entry.tileIndex++;
    if (entry.tileIndex >= ap.width * ap.height) entry.phase = 2;
  } else if (entry.phase == 2) {
    local ok = false;
    local error = 0;
    {
      local shield = AIAccounting();
      local test = AITestMode();
      ok = AIAirport.BuildAirport(entry.anchor, entry.airport.type, AIStation.STATION_NEW);
      if (ok) entry.cost = shield.GetCosts();
      else error = AIError.GetLastError();
    }
    if (error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) entry.ready = true;
    else if (!ok) OpexPCAL02Next(entry);
    else entry.phase = 3;
  } else if (entry.phase == 3) {
    if (catalog.paxCargo < 0 || !OpexAirSiteHasCatchment(entry.anchor, entry.airport, catalog.paxCargo)) {
      OpexPCAL02Next(entry); return;
    }
    entry.pax = OpexAirC96SiteCatchmentScore(entry.anchor, entry.airport, catalog.paxCargo);
    entry.phase = 4;
  } else {
    entry.mail = catalog.mailCargo < 0 ? 0
        : OpexAirAirportCatchmentProduction(entry.anchor, entry.airport.type, catalog.mailCargo);
    OpexPCAL02Keep(entry);
    OpexPCAL02Next(entry);
  }
}

function OpexPCAL02Tick(owner)
{
  if (PCAL02_STATE.fault || PCAL02_STATE.entries.len() == 0
      || AIController.GetOpsTillSuspend() < PCAL02_TICK_BUDGET + PCAL02_SLEEP_RESERVE) return;
  local mark = OpexOpsMeasureBegin();
  /* The precheck may finish on a new tick. Compare the measured interval
   * with its own mark, never with a tick sampled before that precheck. */
  local tick = mark.tick;
  if (PCAL02_STATE.lastTick == tick) return;
  PCAL02_STATE.lastTick = tick;
  PCAL02_STATE.catalog = owner._catalog;
  local entry = null;
  local observed = null;
  local deny = "stock_ready";
  for (local i = 0; i < PCAL02_STATE.entries.len(); i++) {
    if (!OpexPCAL02Room(mark)) { deny = "room"; break; }
    local candidate = PCAL02_STATE.entries[i];
    observed = candidate;
    if (!OpexPCAL02Fresh(candidate, candidate.airport)) {
      OpexPCAL02Drop(i, "worker_expired");
      deny = "entry_expired";
      break;
    }
    if (!candidate.ready) { entry = candidate; break; }
  }
  if (entry != null) deny = OpexPCAL02Admit(owner, mark);
  local admitted = deny == "none";
  local workMark = OpexOpsMeasureBegin();
  if (admitted && entry.plane == null) {
    local combo = OpexPCAL02Combo(entry.airport);
    if (combo == null) entry.ready = true;
    else {
      entry.plane = combo.plane;
      entry.epoch = PCAL02_STATE.epoch;
      entry.year = AIDate.GetYear(AIDate.GetCurrentDate());
    }
  }
  local steps = 0;
  while (admitted && !entry.ready && OpexPCAL02Room(mark) && steps < PCAL02_MAX_STEPS) {
    OpexPCAL02Step(entry, owner._catalog);
    steps++;
  }
  if (admitted) entry.ops += OpexOpsMeasureEnd(workMark);
  local spent = OpexOpsMeasureEnd(mark);
  local logEntry = entry != null ? entry : observed;
  if (logEntry != null) {
    OpexPCAL02Log("calc", logEntry, spent, 0, "steps=" + steps + " ready=" + (logEntry.ready ? 1 : 0)
        + " admitted=" + (admitted ? 1 : 0) + " deny=" + deny
        + " tick0=" + tick + " tick1=" + AIController.GetTick()
        + " left0=" + mark.left + " left1=" + AIController.GetOpsTillSuspend()
        + " total_ops_before=" + PCAL02_STATE.totalOps);
  }
  /* Includes this call's diagnostic emission; the log's op_spent precedes
   * its own emission. Provision is falsifiable, never silently raised. */
  local total = OpexOpsMeasureEnd(mark);
  PCAL02_STATE.totalOps += total;
  if (total > PCAL02_STATE.maxOps) PCAL02_STATE.maxOps = total;
  if (AIController.GetTick() != tick || total > PCAL02_TICK_BUDGET
      || AIController.GetOpsTillSuspend() < PCAL02_SLEEP_RESERVE) {
    PCAL02_STATE.fault = true;
    if (logEntry != null) OpexPCAL02Log("stale", logEntry, total, 0, "reason=budget_overrun");
  }
}

/* Physical consumer: never change anchors/economics after C121 admission. */
function OpexPCAL02BuildSiteOk(site, airport, plane, catalog)
{
  if (!("pcal02" in site)) return true;
  local mark = OpexOpsMeasureBegin();
  local proof = site.pcal02;
  local date = AIDate.GetCurrentDate();
  local ok = proof.epoch == PCAL02_STATE.epoch && date >= proof.date
      && date - proof.date < PCAL02_TTL_DAYS && AIDate.GetYear(date) == proof.year
      && proof.type == airport.type && proof.engine == plane.id && AIEngine.IsBuildable(plane.id)
      && OpexAirAirportAcceptsPlane(airport.type, plane.planeType)
      && (!OPEX_LEVEL_LIMITS || OpexTownAirportAllowedByLevel(site.town, null, -1, catalog))
      && OpexAirSiteStillBuildable(site, airport, plane, false)
      && OpexAirSiteHasCatchment(site.anchor, airport, catalog.paxCargo);
  if (ok) {
    /* Shield simulation from the builder's outer accounting, including failures. */
    local shield = AIAccounting();
    local test = AITestMode();
    ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW)
        && shield.GetCosts() <= proof.cost;
  }
  local entry = { town = site.town, airport = airport, id = proof.id };
  if (!ok) {
    OpexPCAL02Log("stale", entry, OpexOpsMeasureEnd(mark), 0, "reason=build_revalidation anchor=" + site.anchor);
    OpexAirInvalidateCachedSite(site, airport);
  } else OpexPCAL02Log("hit", entry, OpexOpsMeasureEnd(mark), 0, "phase=build anchor=" + site.anchor);
  return ok;
}

function OpexPCAL02Built(site, airport)
{
  if (!("pcal02" in site) || !AIAirport.IsAirportTile(site.anchor)
      || !AICompany.IsMine(AITile.GetOwner(site.anchor))
      || AIAirport.GetAirportType(site.anchor) != airport.type) return;
  local entry = { town = site.town, airport = airport, id = site.pcal02.id };
  OpexPCAL02Log("built", entry, 0, 0, "anchor=" + site.anchor
      + " prepared_ops=" + site.pcal02.preparedOps);
}
