/* V288: transient publication cache. Start/Load deliberately discard it: the
 * existing reload reconstruction remains mandatory. Never save owner pointers.
 * An admission snapshot is consumed only after the whole generation completes. */
function OpexV288Snapshot(mode)
{
  local revisions = {};
  foreach (layer in V288_OWNER._c76GetModeDeps(mode))
    revisions.rawset(layer, V288_OWNER._c76GetLayerRevision(layer));
  revisions.rawset("abandon", OPEX_ABANDON_REVISION);
  if (mode != "fleet") revisions.rawset("production", V288_PRODUCTION_REV);
  if (mode == "rail" || mode == "road")
    revisions.rawset("industry_production", V288_INDUSTRY_REV);
  if (mode == "air") revisions.rawset("rollback", OPEX_AIR_ROLLBACK_REVISION);
  return revisions;
}

function OpexV288Log(mode, action, cause, age, ops)
{
  if (DECISION_LOG) OpexDecide("V288_POOL", "mode=" + mode + " action=" + action
      + " cause=" + cause + " age=" + age + " ops=" + ops);
}

function OpexV288Insufficient(projects, mode)
{
  if (mode == "fleet") return false;
  if (projects == null || !("candidateGroups" in projects)) return true;
  local count = 0;
  foreach (key, list in projects.candidateGroups) {
    foreach (p in list) {
      if (p == null || p.mode != mode) continue;
      if (OpexCandidateIsAbandoned(p, V288_OWNER._abandonedPairs)) continue;
      if ((mode == "rail" || mode == "road")
          && !OpexStagedCandidateStillValid(p.payload, V288_OWNER._lines,
                                          V288_OWNER._abandonedPairs)) continue;
      if (mode == "air" && !OpexAirBatchPlanStillLive(p.payload, V288_OWNER._lines)) continue;
      count++;
      if (count >= (mode == "rail" ? 2 : 1)) return false;
    }
  }
  return true;
}

/* Called by the ordinary catalogue path only, after its in-flight C78 branch.
 * Never insert an annual rail/road refresh in the middle of an AIR scan (V143). */
function OpexV288NeedsRefill(owner)
{
  if (owner._projects == null || owner._generationStage < OPEX_STAGE_COMPLETE) return false;
  foreach (mode, state in V288_POOLS) {
    if (mode != "fleet" && state.pending
        && AIDate.GetCurrentDate() - state.date >= V288_POOL_STALENESS) return true;
  }
  if (MODE_AIR && OpexV288Insufficient(owner._projects, "air")) return true;
  if (MODE_AIR && AIDate.GetYear(AIDate.GetCurrentDate()) == OPEX_START_YEAR) return false;
  if (MODE_RAIL && OpexV288Insufficient(owner._projects, "rail")) return true;
  if (MODE_ROAD && OpexV288Insufficient(owner._projects, "road")) return true;
  if (MODE_WATER && OpexV288Insufficient(owner._projects, "water")) return true;
  return false;
}

/* null means coalesced; pending is retained until a later request is admitted.
 * Empty/insufficient is independent of the event which caused the request. */
function OpexV288Begin(mode, projects, event = null)
{
  local mark = OpexOpsMeasureBegin();
  local now = AIDate.GetCurrentDate();
  local state = mode in V288_POOLS ? V288_POOLS[mode] : null;
  local age = state == null ? -1 : now - state.date;
  local revisions = OpexV288Snapshot(mode);
  local cause = null;
  if (event != null) cause = "event:" + event;
  else if (V288_OWNER._c76ForceReloadRegen) cause = "event:load";
  else if (state == null) cause = "empty";
  else {
    foreach (layer, revision in revisions) {
      if (!(layer in state.revisions) || state.revisions[layer] != revision) {
        cause = "event:" + layer;
        break;
      }
    }
  }
  if (cause == null && age >= V288_POOL_STALENESS) cause = "age";
  if (cause == null && OpexV288Insufficient(projects, mode)) cause = "empty";
  if (cause == null) {
    state.pending = true;
    OpexV288Log(mode, "defer", "age", age, OpexOpsMeasureEnd(mark));
    return null;
  }
  return { mode = mode, revisions = revisions, cause = cause, age = age, mark = mark };
}

function OpexV288Complete(ticket)
{
  if (ticket == null) return;
  if (ticket.mode != "fleet") V288_PUBLICATION_REV++;
  V288_POOLS.rawset(ticket.mode, { date = AIDate.GetCurrentDate(),
      revisions = ticket.revisions, pending = false });
  OpexV288Log(ticket.mode, "serve", ticket.cause, ticket.age,
      ("ops" in ticket) ? ticket.ops : OpexOpsMeasureEnd(ticket.mark));
}

/* Check raw alternatives before AIR validity/scoring. A filtered minimum could
 * hide a newly valid cheap project. Fleet can be bought partially: its threshold
 * is one vehicle, not the capital for the requested quantity. No nonempty
 * portfolio is memoized; its head retains normal revalidation. */
function OpexV288EmptySelection(projects, alternatives, capitalBudget)
{
  local mark = OpexOpsMeasureBegin();
  if (projects.best == null || projects.best.len() != 0) return false;
  if (!("v288EmptyInputs" in projects)
      || projects.v288EmptyInputs.len() != alternatives.len()) return false;
  if (!("v288PoolRevision" in projects)
      || projects.v288PoolRevision != V288_PUBLICATION_REV) return false;
  local i = 0;
  local cheapest = -1;
  foreach (p in alternatives) {
    local cap = OpexProjectFinanceCapital(p);
    if (p.mode == "fleet" && p.payload != null && ("planePrice" in p.payload)
        && p.payload.planePrice > 0) cap = p.payload.planePrice + 1000;
    local previous = projects.v288EmptyInputs[i++];
    if (previous.key != OpexProjectKeyFor(p) || previous.capital != cap) return false;
    if (cheapest < 0 || cap < cheapest) cheapest = cap;
  }
  if (cheapest >= 0 && capitalBudget >= cheapest) return false;
  projects.capitalBudget = capitalBudget;
  projects.capitalRemaining = capitalBudget;
  OpexV288Log("selection", "defer", "event:capital_below_min", 0, OpexOpsMeasureEnd(mark));
  return true;
}

function OpexV288IndustryProduction(industry, cargo)
{
  local key = industry + "|" + cargo;
  local monthly = AIIndustry.GetLastMonthProduction(industry, cargo);
  if (!(key in V288_INDUSTRY_PRODUCTION)) {
    V288_INDUSTRY_PRODUCTION.rawset(key, monthly);
    return;
  }
  local previous = V288_INDUSTRY_PRODUCTION[key];
  if (abs(monthly - previous) >= 10 && abs(monthly - previous) * 100 >= previous * 20) {
    V288_INDUSTRY_PRODUCTION[key] = monthly;
    V288_INDUSTRY_REV++;
  }
}

function OpexV288SelectionInputs(alternatives)
{
  local inputs = [];
  foreach (p in alternatives) {
    local cap = OpexProjectFinanceCapital(p);
    if (p.mode == "fleet" && p.payload != null && ("planePrice" in p.payload)
        && p.payload.planePrice > 0) cap = p.payload.planePrice + 1000;
    inputs.append({ key = OpexProjectKeyFor(p), capital = cap });
  }
  return inputs;
}

/* A periodic repeat of the same fleet demand is not an event. Compute each
 * small fleet offer once, then reuse it if publication is admitted. Snapshot
 * values rather than mutable project references (C70 changes scores in place). */
function OpexV288FleetOffers(fleetPlan)
{
  local offers = [];
  local signature = [];
  if (fleetPlan != null) foreach (entry in fleetPlan) {
    local p = OpexProjectFromFleet(entry);
    offers.append(p);
    if (p == null) continue;
    signature.append(OpexProjectAttemptKey(p) + "|" + p.capital + "|"
        + p.profitAnnual + "|" + p.revenueAnnual + "|" + entry.want + "|"
        + (("baseVehicles" in entry) ? entry.baseVehicles : -1) + "|"
        + (("profitIsObserved" in p) && p.profitIsObserved ? 1 : 0) + "|"
        + (("v161Source" in p) ? p.v161Source : ""));
  }
  signature.sort();
  local changed = V288_FLEET_SIGNATURE == null
      || signature.len() != V288_FLEET_SIGNATURE.len();
  if (!changed) for (local i = 0; i < signature.len(); i++) {
    if (signature[i] != V288_FLEET_SIGNATURE[i]) { changed = true; break; }
  }
  return { offers = offers, signature = signature, changed = changed };
}
