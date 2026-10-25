/* RLW-06 : A* shadow du fret long decouvert par RLW-04b.
 * Aucune insertion dans _projects/_railReadyStock/_railSearch, aucun constructeur.
 * Un seul job prive, trois etapes atomiques mesurees avant FindPath reprenable.
 * Priorite stricte a la file existante, aux recherches et a tout projet finançable.
 * Le stock prive expire et n'est pas serialise. */
const RLW06_PROBE_BIT = 33554432;
const RLW06_MIN_LEFT = 5000;
const RLW06_SEARCH_LEFT = 3000;
/* Une seule expansion AyStar par tranche : les quatre expansions precedentes
 * pouvaient depasser 13k opcodes et franchir un tick. */
const RLW06_SLICE_ITERS = 1;
const RLW06_TTL_DAYS = 365;
const RLW06_SEARCH_DAYS = 365;
const RLW06_REPORT_DAYS = 90;
const RLW06_SITE_RADIUS = 8;
const RLW06_SITE_CAP = 3;

/* Un seul branchement dans la boucle principale, commun a RLW-04b et RLW-06.
 * OFF, le nombre d'instructions de la boucle est identique au port RLW-04b. */
function OpexAI::_rlw04bAnd06Step()
{
  this._rlw04bStep();
  if (RLW06_SHADOW) this._rlw06Step();
}

function OpexRLW06PairKey(p)
{
  return p.cargo + "|" + p.srcId + "|" + p.dstId;
}

function OpexRLW06Stats()
{
  return { starts = 0, failed = 0, searches = 0, ready = 0,
      reused = 0, expired = 0, deferred = 0, slices = 0,
      ops = 0, initOps = 0, searchOps = 0, finalizeOps = 0,
      ticks = 0, crossed = 0, maxSliceOps = 0, maxInitOps = 0,
      lastDate = -1 };
}

function OpexRLW06Event(event, job, extra = "")
{
  local key = job == null ? "-" : job.key;
  OpexDecide("RLW06_" + event, "key=" + key + " " + extra);
}

/* Une seule base de spirale par tranche. La recherche historique de gares
 * balaye jusqu'a 30 anneaux de facon atomique (jusqu'a 296k opcodes observes).
 * Cette sonde prend au plus huit anneaux et trois options par extremite ;
 * RLW-07 revalidera les sites et la constructibilite du plan. */
function OpexRLW06SiteStep(job, catalog)
{
  local s = job.site;
  local center = s.side == 0 ? job.candidate.src : job.candidate.dst;
  local production = s.side == 0;
  if (s.r > RLW06_SITE_RADIUS || s.plans.len() >= RLW06_SITE_CAP) return true;
  local r = s.r, idx = s.idx, dx = 0, dy = 0;
  if (r > 0) {
    if (idx < 2 * r) { dx = -r + idx; dy = -r; }
    else if (idx < 4 * r) { dx = r; dy = -r + idx - 2 * r; }
    else if (idx < 6 * r) { dx = r - (idx - 4 * r); dy = r; }
    else { dx = -r; dy = r - (idx - 6 * r); }
  }
  s.idx++;
  if ((r == 0 && s.idx >= 1) || (r > 0 && s.idx >= 8 * r)) {
    s.r++;
    s.idx = 0;
  }
  local x = AIMap.GetTileX(center) + dx, y = AIMap.GetTileY(center) + dy;
  if (x <= 0 || y <= 0 || x >= AIMap.GetMapSizeX() - 1 || y >= AIMap.GetMapSizeY() - 1)
    return false;
  local base = AIMap.GetTileIndex(x, y);
  if (!AITile.IsBuildable(base) || AITile.GetSlope(base) != AITile.SLOPE_FLAT) return false;
  local axes = [[AIRail.RAILTRACK_NE_SW, AIMap.GetTileIndex(1, 0)],
                [AIRail.RAILTRACK_NW_SE, AIMap.GetTileIndex(0, 1)]];
  foreach (axis in axes) {
    for (local sign = -1; sign <= 1; sign += 2) {
      local step = axis[1], length = s.length;
      local anchor = sign > 0 ? base : base - step * (length - 1);
      local stationExit = sign > 0 ? anchor + step * (length - 1) : anchor;
      local lead = sign > 0 ? stationExit + step : stationExit - step;
      local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead)
          && AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
      for (local i = 0; i < length && usable; i++) {
        local t = anchor + step * i;
        usable = AIMap.IsValidTile(t) && AITile.IsBuildable(t)
            && AITile.GetSlope(t) == AITile.SLOPE_FLAT;
      }
      if (!usable) continue;
      local cargoValue = OpexRailPlatformCargoValue(anchor, step, length,
          job.candidate.cargo, catalog.railCoverage, production);
      if (production ? cargoValue <= 0 : cargoValue < 8) continue;
      local stationOk = false;
      {
        local probe = AITestMode();
        stationOk = AIRail.BuildRailStation(anchor, axis[0], 1, length,
            AIStation.STATION_NEW);
      }
      if (!stationOk) continue;
      s.plans.push({ anchor = anchor, station_exit = stationExit, lead = lead,
          direction = axis[0], step = step, length = length, cargoValue = cargoValue });
      if (s.plans.len() >= RLW06_SITE_CAP) break;
    }
    if (s.plans.len() >= RLW06_SITE_CAP) break;
  }
  return s.r > RLW06_SITE_RADIUS || s.plans.len() >= RLW06_SITE_CAP;
}

function OpexAI::_rlw06Step()
{
  if (!RLW06_SHADOW || !MODE_RAIL || this._catalog == null
      || this._rlw04bState == null || !this._rlw04bState.initialized
      || this._rlw04bState.sources < 64
      || this._rlw04bState.best.len() == 0) return;
  if (this._rlw06Stats == null) this._rlw06Stats = OpexRLW06Stats();
  local stats = this._rlw06Stats;
  local today = AIDate.GetCurrentDate();
  if (stats.lastDate < 0 || today - stats.lastDate >= RLW06_REPORT_DAYS) {
    stats.lastDate = today;
    OpexRLW06Event("SUMMARY", null,
        "best=" + this._rlw04bState.best.len()
        + " enum_sources=" + this._rlw04bState.sources
        + " enum_done=" + (this._rlw04bState.completed ? 1 : 0)
        + " starts=" + stats.starts
        + " failed=" + stats.failed + " searches=" + stats.searches
        + " ready=" + stats.ready + " stored=" + this._rlw06Ready.len()
        + " reused=" + stats.reused + " expired=" + stats.expired
        + " deferred=" + stats.deferred + " slices=" + stats.slices
        + " init_ops=" + stats.initOps + " astar_ops=" + stats.searchOps
        + " finalize_ops=" + stats.finalizeOps + " total_ops=" + stats.ops
        + " ticks=" + stats.ticks + " cross=" + stats.crossed
        + " max_init=" + stats.maxInitOps + " max_slice=" + stats.maxSliceOps);
  }

  /* Une seule verification de stock par passage : la relecture prouve la
   * reutilisation en shadow, sans donner le plan a un constructeur. */
  foreach (key, entry in this._rlw06Ready) {
    if (today > entry.expiry) {
      delete this._rlw06Ready[key];
      stats.expired++;
      OpexRLW06Event("EXPIRE", null, "pair=" + key + " age=" + (today - entry.readyDate));
    } else if (!entry.reused && entry.plan != null && entry.plan.ok
        && entry.plan.tiles != null && entry.plan.tiles.len() > 2) {
      entry.reused = true;
      stats.reused++;
      OpexRLW06Event("REUSE", null, "pair=" + key + " len=" + entry.plan.tiles.len()
          + " age=" + (today - entry.readyDate) + " shadow=1");
    }
    break;
  }

  /* Ces priorites s'appliquent aussi entre deux tranches du MEME A*.
   * Le chemin de production a deja eu sa passe dans cette boucle. */
  if (this._activeWorker != null || this._railSearch != null
      || this._hasReactiveIntentions() || this._po01cJob != null || this._po01cPending
      || this._projects == null || this._projects.best == null) {
    stats.deferred++;
    return;
  }
  if (this._c121RailPrepAirFundableCheap()) {
    stats.deferred++;
    return;
  }
  /* Le portefeuille a deja eu son arbitrage et sa tranche par l'orchestrateur
   * du tick. Les projets vivants n'ont pas le droit de detourner leur prochain
   * tour de file : RLW06 n'utilise que les opcodes AVANT Sleep(1).
   * Le cas d'une transaction/recherche active est bloque ci-dessus. */
  if (AIController.GetOpsTillSuspend() < RLW06_MIN_LEFT) {
    stats.deferred++;
    return;
  }

  if (this._rlw06Job == null) {
    local best = this._rlw04bState.best;
    for (local i = 0; i < best.len(); i++) {
      local p = best[i];
      local key = OpexRLW06PairKey(p);
      if (key in this._rlw06Seen || key in this._rlw06Ready) continue;
      this._rlw06Seen[key] <- true;
      if (!AIIndustry.IsValidIndustry(p.srcId) || !AIIndustry.IsValidIndustry(p.dstId)) continue;
      this._rlw06Cursor = i + 1;
      this._rlw06Job = { key = key, pair = p, phase = "economics",
          candidate = null, plan = null, segmented = null, pathfinder = null,
          search = null, spent = 0, ops = 0, slices = 0,
          startDate = today, startTick = AIController.GetTick() };
      stats.starts++;
      OpexRLW06Event("PAIR", this._rlw06Job,
          "rank=" + this._rlw06Cursor + " score=" + p.score
          + " enum_sources=" + this._rlw04bState.sources
          + " provisional=" + (this._rlw04bState.completed ? 0 : 1)
          + " cargo=" + AICargo.GetCargoLabel(p.cargo) + " production=" + p.production
          + " src=" + p.srcId + " dst=" + p.dstId + " distance=" + p.distance);
      break;
    }
    if (this._rlw06Job == null) return;
  }
  local job = this._rlw06Job;
  if (today - job.startDate > RLW06_SEARCH_DAYS) {
    OpexRLW06Event("END", job, "reason=timeout iters=" + job.spent
        + " days=" + (today - job.startDate) + " opcodes=" + job.ops);
    stats.failed++;
    this._rlw06Job = null;
    return;
  }
  local required = job.phase == "search" ? RLW06_SEARCH_LEFT : RLW06_MIN_LEFT;
  if (AIController.GetOpsTillSuspend() < required) return;
  local mark = OpexOpsMeasureBegin();
  local stage = job.phase;
  local reason = "continue";

  if (stage == "economics") {
    local p = job.pair;
    local monthly = AIIndustry.GetLastMonthProduction(p.srcId, p.cargo);
    if (monthly <= 0) reason = "no_production";
    else {
      local economics = OpexLineEconomics(this._catalog, p.cargo, p.distance,
          monthly, "freight", 0);
      if (economics == null || economics.profitAnnual <= 0) reason = "economics";
      else {
        /* OpexApplyRailEconomics utilise '=' pour chacun des champs : il
         * attend un vrai candidat complet (creé par OpexMakeCandidate).
         * Partir du contrat economique complet sans la generation couteuse. */
        local candidate = clone economics;
        candidate.mode <- "rail";
        candidate.kind <- "freight";
        candidate.cargo <- p.cargo;
        candidate.src <- AIIndustry.GetLocation(p.srcId);
        candidate.dst <- AIIndustry.GetLocation(p.dstId);
        candidate.distance <- p.distance;
        candidate.monthly <- monthly;
        candidate.originServed <- false;
        job.candidate = candidate;
        job.phase = "platforms";
      }
    }
  } else if (stage == "platforms") {
    if (!("site" in job)) job.site <- { side = 0, r = 0, idx = 0,
        length = job.candidate.platformLength > this._catalog.platformLength
            ? this._catalog.platformLength : job.candidate.platformLength,
        plans = [], plansA = null };
    local site = job.site;
    if (OpexRLW06SiteStep(job, this._catalog)) {
      if (site.plans.len() == 0) reason = site.side == 0 ? "SITEA" : "SITEB";
      else if (site.side == 0) {
        site.plansA = site.plans;
        site.plans = [];
        site.side = 1;
        site.r = 0;
        site.idx = 0;
      } else {
        local economics = OpexLineEconomics(this._catalog, job.candidate.cargo,
            job.candidate.distance, job.candidate.monthly, "freight", site.length);
        if (economics == null) reason = "site_economics";
        else {
          OpexApplyRailEconomics(job.candidate, economics);
          local budgetInfo = OpexIterationBudget(job.candidate.profitAnnual,
              MIN_RATIO, HARD_ITERATION_CAP);
          job.plan = { plansA = site.plansA, plansB = site.plans,
              length = site.length, iterationBudget = budgetInfo.budget,
              capital = job.candidate.capital, opcodes = 0, ok = false,
              tiles = null, structures = null, planA = null, planB = null,
              iterations = 0, reason = "SEARCH" };
          job.phase = "setup";
          job.site = null;
        }
      }
    }
  } else if (stage == "setup") {
    local candidate = job.candidate;
    local plan = job.plan;
    local ignored = V131_TOWN_CLEARANCE ? OpexV131BuildTownClearance(candidate, plan.plansA, plan.plansB) : null;
    if (OpexV190Active()) ignored = OpexV190MergeIgnoredTiles(ignored, plan.plansA, plan.plansB);
    local side = V197_GUIDED_DOUBLE && OpexV190Active() ? 1 : null;
    local weight = OpexRailAstarWeight(candidate.distance);
    local engine = OpexRailEngineOf(candidate);
    if (V294_RAIL_CONTINUOUS > 0)
      job.pathfinder = OpexCreateRailPathfinder(plan.plansA, plan.plansB, ignored, weight, side, null, engine);
    else
      job.segmented = OpexCreateSegmentedSearch(plan.plansA, plan.plansB, plan.iterationBudget, ignored, weight, side, null, engine);
    if (job.pathfinder == null && job.segmented == null) reason = "setup";
    else {
      stats.searches++;
      job.phase = "search";
      OpexRLW06Event("ASTAR", job, "iteration_budget=" + plan.iterationBudget
          + " segmented=" + (job.segmented != null ? 1 : 0));
    }
  } else if (stage == "search") {
    /* Remplir le reliquat avec jusqu'a 16 expansions REPRENABLES. Mesurer
     * chacune, recalibrer l'admission avec le pire cout observe et ne jamais
     * entamer une nouvelle expansion apres franchissement du tick. */
    local originTick = AIController.GetTick();
    local deadline = originTick + 10;
    local steps = 0;
    while (steps < 16 && job.phase == "search"
        && AIController.GetTick() == originTick) {
      local threshold = RLW06_SEARCH_LEFT;
      local priorWorst = ("worstIterOps" in job) ? job.worstIterOps : 0;
      if (priorWorst + 700 > threshold) threshold = priorWorst + 700;
      if (AIController.GetOpsTillSuspend() < threshold) break;
      local singleMark = OpexOpsMeasureBegin();
      local slice = job.segmented != null
          ? OpexAdvanceSegmentedSearch(job.segmented, RLW06_SLICE_ITERS, deadline)
          : OpexAdvanceRailPathfinder(job.pathfinder, job.spent, job.plan.iterationBudget,
                deadline, RLW06_SLICE_ITERS);
      local singleOps = OpexOpsMeasureEnd(singleMark);
      if (!("worstIterOps" in job)) job.worstIterOps <- singleOps;
      else if (singleOps > job.worstIterOps) job.worstIterOps = singleOps;
      job.spent = slice.iterations;
      job.slices++;
      stats.slices++;
      steps++;
      if (slice.done) {
        job.search = slice;
        job.phase = "finalize";
        reason = slice.stop;
      }
    }
  } else if (stage == "finalize") {
    local search = job.search;
    if (search.stop != "OK") reason = search.stop;
    else {
      /* Assemblage du plan de voie unique seulement. Le prepareur complet
       * peut ouvrir un SECOND A* bloquant pour la double voie : RLW-06
       * interdit ce travail non interruptible sur son chemin shadow. */
      local plan = job.plan;
      local tiles = OpexResolveSearchTiles(search);
      if (tiles == null || tiles.len() < 3) reason = "short_path";
      else {
        local last = tiles.len() - 1;
        local a = RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_EXACT_IDENTITY
            ? OpexMatchPlanExact(plan.plansA, tiles[0], tiles[1])
            : OpexMatchPlan(plan.plansA, tiles[0]);
        local b = RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_EXACT_IDENTITY
            ? OpexMatchPlanExact(plan.plansB, tiles[last], tiles[last - 1])
            : OpexMatchPlan(plan.plansB, tiles[last]);
        if (a == null || b == null) reason = "no_match";
        else {
          plan.planA = a;
          plan.planB = b;
          plan.tiles = tiles;
          plan.structures = OpexResolveSearchStructures(search);
          plan.iterations = job.spent;
          plan.ok = true;
          plan.reason = "OK";
          this._rlw06Ready[job.key] <- { plan = plan, pair = job.pair,
              readyDate = today, expiry = today + RLW06_TTL_DAYS, reused = false };
          stats.ready++;
          reason = "ready";
        }
      }
    }
  }
  local spentOps = OpexOpsMeasureEnd(mark);
  local crossed = AIController.GetTick() - mark.tick;
  job.ops += spentOps;
  stats.ops += spentOps;
  stats.ticks += crossed;
  if (crossed > 0) stats.crossed++;
  if (spentOps > stats.maxSliceOps) stats.maxSliceOps = spentOps;
  if (stage == "search") stats.searchOps += spentOps;
  else if (stage == "finalize") stats.finalizeOps += spentOps;
  else {
    stats.initOps += spentOps;
    if (spentOps > stats.maxInitOps) stats.maxInitOps = spentOps;
  }
  if (stage != "search" || job.slices % 32 == 0 || reason != "continue")
    OpexRLW06Event("STEP", job, "stage=" + stage + " next=" + job.phase
        + " reason=" + reason + " iters=" + job.spent
        + " opcodes=" + spentOps + " ticks=" + crossed
        + " left=" + AIController.GetOpsTillSuspend());
  if (reason != "continue" && reason != "ready"
      && !(stage == "search" && reason == "OK")) {
    stats.failed++;
    OpexRLW06Event("END", job, "reason=" + reason + " iters=" + job.spent
        + " opcodes=" + job.ops + " days=" + (today - job.startDate));
    this._rlw06Job = null;
  } else if (reason == "ready") {
    OpexRLW06Event("READY", job, "source=" + job.pair.srcId
        + " sink=" + job.pair.dstId + " len=" + job.plan.tiles.len()
        + " iters=" + job.spent + " opcodes=" + job.ops
        + " days=" + (today - job.startDate) + " ttl=" + RLW06_TTL_DAYS
        + " shadow=1");
    job.segmented = null;
    job.pathfinder = null;
    this._rlw06Job = null;
  }
}
