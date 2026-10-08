/* C83 local : geometrie connue transitoire, reconstruite au redemarrage du
 * worker apres Load (persist.nut abandonne deja toute tranche AIR inachevee).
 * Ne muter ni les plans en portefeuille ni le cache commercial de la cible. */
function OpexC83RepairSnapshot(projects)
{
  local anchors = {};
  if (projects != null && ("candidateGroups" in projects) && projects.candidateGroups != null) {
    foreach (key, entry in projects.candidateGroups) {
      local list = typeof entry == "array" ? entry : [entry];
      foreach (project in list) {
        if (project == null || project.mode != "air" || !("payload" in project)
            || project.payload == null) continue;
        local plan = project.payload;
        if (!("airport" in plan) || plan.airport == null) continue;
        if (("siteA" in plan) && !(("reuseA" in plan) && plan.reuseA)) {
          anchors.rawset(plan.siteA.town.id + "_" + plan.airport.type, plan.siteA.anchor);
        }
        if (("siteB" in plan) && !(("reuseB" in plan) && plan.reuseB)) {
          anchors.rawset(plan.siteB.town.id + "_" + plan.airport.type, plan.siteB.anchor);
        }
      }
    }
  }
  if (AIR_SITE_CACHE_ENABLED) {
    foreach (key, anchor in AIR_SITE_CACHE) {
      if (anchor != null) anchors.rawset(key, anchor);
    }
  }
  return { anchors = anchors, scan = null, localCombos = 0, fallbackCombos = 0,
    targetKept = 0, targetSearched = 0, partners = 0 };
}

/* Une tranche consomme au moins une ville. Les partenaires absents/infirmes
 * sont exclus, jamais re-sondes ici ; aucun partenaire valide => chemin ancien.
 * Les paires/economics et la fusion ciblee restent celles du planificateur AIR. */
function OpexC83RepairFindSites(ctx, comboIndex, combo, airport, plane)
{
  local repair = ctx.resumeState.c83Repair;
  if (repair.scan == null || repair.scan.combo != comboIndex) {
    repair.scan = { combo = comboIndex, index = 0, sites = [], partners = 0,
      done = false, fallback = false,
      probes = { left = AIR_MAX_SITE_PROBES, townsLeft = 1, tested = 0, cheapSkip = 0,
        stationLimitedTowns = ctx.stationLimitedTowns } };
  }
  local scan = repair.scan;
  if (scan.done) {
    ctx.c83RepairCombo = !scan.fallback;
    if (!scan.fallback) ctx.sites = ctx.resumeState.sites;
    return { handled = !scan.fallback, done = true };
  }
  local startTick = AIController.GetTick();
  local startOps = AIController.GetOpsTillSuspend();
  local testedBefore = scan.probes.tested;
  local cheapBefore = scan.probes.cheapSkip;
  local foundBefore = scan.sites.len();
  local progressed = false;
  while (scan.index < ctx.limit) {
    local used = OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all);
    if (progressed && ((ctx.opsBudget > 0 && used >= ctx.opsBudget)
        || (ctx.deadlineTick > 0 && AIController.GetTick() >= ctx.deadlineTick))) break;
    local town = ctx.towns[scan.index];
    scan.index++;
    progressed = true;
    if (V133_AIR_BUILD_RETRY && OpexV133AirTownSkip(ctx, town.id)) continue;
    if (town.id in ctx.stationLimitedTowns) continue;
    local served = OpexAirTownServed(town, ctx.lines, ctx.servedDiag);
    local secondSlot = served && (town.id in ctx.c83TopTownIds) && OpexAirC83SecondSlotOpen(town);
    if (served && !secondSlot) continue;
    if (!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && town.pop < 600) continue;
    if (V93_AIRPORT_NO_POP_FLOOR && town.pop < V93_AIRPORT_MIN_POP) continue;
    local target = town.id == ctx.targetTownId;
    local key = town.id + "_" + airport.type;
    local site = null;
    if (key in repair.anchors) {
      local anchor = repair.anchors[key];
      local known = { town = town, anchor = anchor };
      if ((!target || OpexAirSlotTownId(anchor) == ctx.targetTownId)
          && OpexAirSiteStillBuildable(known, airport, plane, false, ctx.stationLimitedTowns)) {
        site = known;
        if (target) repair.targetKept++;
      }
    }
    if (target && site == null) {
      repair.targetSearched++;
      scan.probes.townsLeft = 1;
      site = OpexAirFindSite(town, airport, scan.probes, ctx.targetTownId);
      /* Comme le parcours ancien : revalidation apres le scan, qui peut avoir
       * suspendu le script. Pas de publication d'une geometrie infirmee. */
      if (site != null && !OpexAirSiteStillBuildable(site, airport, plane, false,
          ctx.stationLimitedTowns)) site = null;
      if (site != null) repair.anchors.rawset(key, site.anchor);
    }
    if (site != null) {
      if (secondSlot) site.c83OwnSecondSlot <- true;
      if (target) site.c83SlotTown <- ctx.targetTownId;
      scan.sites.append(site);
      if (!target) scan.partners++;
    }
  }
  ctx.perfOpsSites += OpexAirCalcDeltaOps(startTick, startOps);
  ctx.perfProbesCount += scan.probes.tested - testedBefore;
  ctx.perfCheapSkip += scan.probes.cheapSkip - cheapBefore;
  ctx.perfSitesFound += scan.sites.len() - foundBefore;
  ctx.resumeState.perfOpsSites = ctx.perfOpsSites;
  ctx.resumeState.perfProbesCount = ctx.perfProbesCount;
  ctx.resumeState.perfCheapSkip = ctx.perfCheapSkip;
  ctx.resumeState.perfSitesFound = ctx.perfSitesFound;
  if (scan.index < ctx.limit) {
    ctx.resumeState.totalOps += OpexAirCalcDeltaOps(ctx.t0_all, ctx.l0_all);
    return { handled = true, done = false };
  }
  scan.done = true;
  scan.fallback = scan.partners == 0;
  if (scan.fallback) {
    repair.fallbackCombos++;
    return { handled = false, done = true };
  }
  repair.localCombos++;
  repair.partners += scan.partners;
  ctx.c83RepairCombo = true;
  ctx.sites = scan.sites;
  ctx.resumeState.sites = scan.sites;
  return { handled = true, done = true };
}
