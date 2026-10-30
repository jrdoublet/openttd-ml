/* ESTIM-only: require() executes in settings AFTER ESTIM is read and BEFORE
 * ESTIM_K_R is initialized and any RAIL/AIR candidate scoring begins. */
ESTIM_K_R_PRIOR.air = 2.00;
ESTIM_K_R_PRIOR.rail = 0.75;
ESTIM_K_R_PRIOR_WEIGHT = 15.0;
/* Loaded only under opt-in ESTIM; no historic OFF bytecode. */
function OpexC121ScanRoutePlaneEnginesFullScan(catalog, plan)
{
  local perf = C121_AIR_PLAN_PERF;
  local scanTick0 = AIController.GetTick();
  local scanOps0 = AIController.GetOpsTillSuspend();
  local scanMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  local evaluated = 0;
  local known = 0;
  local evalOpsTotal = 0;
  local evalOps = 0;
  local evalSameTick = 0;
  local best = null;
  local candidates = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
    if (!OpexC118EngineFitsPlan(plan, plane)) continue;
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    local context = null;
    local upperScore = context == null ? OpexC121InitialEngineUpperScore(catalog, plan, plane)
        : OpexC121InitialEngineUpperScore(catalog, plan, plane, context);
    if (upperScore == null) continue;
    if (context != null) {
      context.upperScore = upperScore;
      candidates.append(context);
    } else candidates.append({ plane = plane, upperScore = upperScore });
  }
  candidates.sort(function(a, b) {
    if (a.upperScore > b.upperScore) return -1;
    if (a.upperScore < b.upperScore) return 1;
    if (a.plane.id < b.plane.id) return -1;
    if (a.plane.id > b.plane.id) return 1;
    return 0;
  });
  if (scanMark != null) OpexSpanAgg("air.c121.scan", scanMark);
  local engTabSeen = 0;
  foreach (candidate in candidates) {
    /* ESTIM: unsafe bound cannot truncate this scan. */
    local plane = candidate.plane;
    local engineMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    local tick0 = AIController.GetTick();
    local ops0 = AIController.GetOpsTillSuspend();
    local context = ("trip" in candidate) ? candidate : null;
    local openingPlanes = 1;
    local evaluatedEconomics = context == null
        ? OpexC121EngineEconomics(catalog, plan, plane, openingPlanes, true, null)
        : OpexC121EngineEconomics(catalog, plan, plane, openingPlanes, true, null, null, context);
    local tick1 = AIController.GetTick();
    local ops = OpexAirCalcDeltaOps(tick0, ops0);
    if (ops >= 0) evalOpsTotal += ops;
    if (tick1 == tick0 && ops >= 0) {
      evalOps += ops;
      evalSameTick++;
    }
    if (engineMark != null) OpexSpanAgg("air.c121.engine", engineMark);
    if (evaluatedEconomics == null || !("decisionScore" in evaluatedEconomics)) {
      continue;
    }
    local economics = (("decisionEconomics" in evaluatedEconomics)
        && evaluatedEconomics.decisionEconomics != null)
        ? evaluatedEconomics.decisionEconomics : evaluatedEconomics;
    evaluated++;
    if (("engineMailKnown" in economics) && economics.engineMailKnown) known++;
    local item = { plane = plane, economics = economics, context = context };
    if (best == null
        || economics.decisionScore > best.economics.decisionScore
        || (economics.decisionScore == best.economics.decisionScore
            && economics.decisionProfitAnnual > best.economics.decisionProfitAnnual)
        || (economics.decisionScore == best.economics.decisionScore
            && economics.decisionProfitAnnual == best.economics.decisionProfitAnnual
            && plane.id < best.plane.id)) best = item;
  }
  local scanTick1 = AIController.GetTick();
  plan.c121EngineScanTicks <- scanTick1 - scanTick0;
  plan.c121EngineScanOps <- OpexAirCalcDeltaOps(scanTick0, scanOps0);
  plan.c121EngineEvalCount <- evaluated;
  plan.c121EngineKnownCount <- known;
  plan.c121EngineEvalOpsTotal <- evalOpsTotal;
  plan.c121EngineEvalOpsSameTick <- evalOps;
  plan.c121EngineEvalSameTickCount <- evalSameTick;
  if (perf != null) {
    if (plan.c121EngineScanOps >= 0) perf.scanOps += plan.c121EngineScanOps;
    perf.scanTicks += plan.c121EngineScanTicks;
    perf.engineEvals += evaluated;
  }
  return best;
}

function OpexC121ChooseRoutePlaneFullScan(catalog, plan, lines = null)
{
  if (catalog == null || plan == null
      || !("airport" in plan) || plan.airport == null
      || !("distance" in plan)
      || catalog.airPlaneChoicesByAirport == null
      || !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return null;
  local perf = C121_AIR_PLAN_PERF;
  if (perf != null) perf.calls++;
  local demandMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  OpexC121PrepareDemandShadow(catalog, plan, lines);
  if (demandMark != null) OpexSpanAgg("air.c121.demand", demandMark);
  if (perf != null && ("c121DemandOps" in plan)) {
    if (plan.c121DemandOps >= 0) perf.demandOps += plan.c121DemandOps;
    perf.demandTicks += ("c121DemandTicks" in plan) ? plan.c121DemandTicks : 0;
  }
  if (!("c121Demand" in plan)) return null;
  local staticTick0 = AIController.GetTick();
  local staticOps0 = AIController.GetOpsTillSuspend();
  local staticMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  OpexC121PrepareEngineStatic(catalog, plan);
  if (staticMark != null) OpexSpanAgg("air.c121.static", staticMark);
  local staticTick1 = AIController.GetTick();
  plan.c121EngineStaticTicks <- staticTick1 - staticTick0;
  plan.c121EngineStaticOps <- OpexAirCalcDeltaOps(staticTick0, staticOps0);
  if (perf != null) {
    if (plan.c121EngineStaticOps >= 0) perf.staticOps += plan.c121EngineStaticOps;
    perf.staticTicks += plan.c121EngineStaticTicks;
  }

  local geMode = 0;
  local geEst = -1;
  local best = null;
  local geState = null;
  /* Historical GE shortcut only runs in the untouched OFF chooser.
   * FullScan must never bypass another engine under ESTIM. */
  if ((ESTIM_UNIFIE & 1) == 0) {
    local airportType = plan.airport.type;
    geState = OpexC121GameEngineState(airportType);
    OpexC121GameEngineSyncRevs(geState, airportType);
    if (geState.established) {
      geEst = geState.engine;
      geState.sinceCheck = geState.sinceCheck + 1;
      if (geState.sinceCheck >= C121_GAME_ENGINE_CHECK_EVERY) {
        geState.sinceCheck = 0;
        geMode = 2;
      } else {
        local geScanTick0 = AIController.GetTick();
        local geScanOps0 = AIController.GetOpsTillSuspend();
        local geScanMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
        local shortcut = OpexC121GameEngineTryShortcut(catalog, plan, geState.engine);
        if (geScanMark != null) OpexSpanAgg("air.c121.scan", geScanMark);
        if (shortcut != null) {
          /* ge=1 : aucune ligne ENG ; E seul, sans decisionOnly. */
          geMode = 1;
          best = { plane = shortcut.plane, economics = null, context = shortcut.context };
          local geScanTick1 = AIController.GetTick();
          plan.c121EngineScanTicks <- geScanTick1 - geScanTick0;
          plan.c121EngineScanOps <- OpexAirCalcDeltaOps(geScanTick0, geScanOps0);
          plan.c121EngineEvalCount <- 0;
          plan.c121EngineKnownCount <- 0;
          plan.c121EngineEvalOpsTotal <- 0;
          plan.c121EngineEvalOpsSameTick <- 0;
          plan.c121EngineEvalSameTickCount <- 0;
          if (perf != null) {
            if (plan.c121EngineScanOps >= 0) perf.scanOps += plan.c121EngineScanOps;
            perf.scanTicks += plan.c121EngineScanTicks;
          }
        } else {
          geMode = 3;
          OpexC121GameEngineLog("fallback", airportType, geState.engine, geState.engine, geState.streak);
        }
      }
    }
  }

  /* Un seul test du reglage par choix. A 0, les deux if sont sautes :
   * le scan complet reste le corps historique, le raccourci ne pose pas
   * AIR_ENGINE_DEPTH_SCAN. */

  if (geMode != 1) {
  local scanTick0 = AIController.GetTick();
  local scanOps0 = AIController.GetOpsTillSuspend();
  local scanMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  local evaluated = 0;
  local known = 0;
  local evalOpsTotal = 0;
  local evalOps = 0;
  local evalSameTick = 0;
  local candidates = [];
  foreach (plane in catalog.airPlaneChoicesByAirport[plan.airport.type]) {
    if (!AIEngine.IsValidEngine(plane.id) || !AIEngine.IsBuildable(plane.id)) continue;
    if (!OpexC118EngineFitsPlan(plan, plane)) continue;
    if (!OpexAirPlaneInRange(plane, plan.distance)) continue;
    local context = null;
    local upperScore = context == null ? OpexC121InitialEngineUpperScore(catalog, plan, plane)
        : OpexC121InitialEngineUpperScore(catalog, plan, plane, context);
    if (upperScore == null) continue;
    if (context != null) {
      context.upperScore = upperScore;
      candidates.append(context);
    } else candidates.append({ plane = plane, upperScore = upperScore });
  }
  candidates.sort(function(a, b) {
    if (a.upperScore > b.upperScore) return -1;
    if (a.upperScore < b.upperScore) return 1;
    if (a.plane.id < b.plane.id) return -1;
    if (a.plane.id > b.plane.id) return 1;
    return 0;
  });
  if (scanMark != null) OpexSpanAgg("air.c121.scan", scanMark);
  local engTabSeen = 0;
  foreach (candidate in candidates) {
    /* ESTIM: unsafe bound cannot truncate this scan. */
    local plane = candidate.plane;
    local engineMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    local tick0 = AIController.GetTick();
    local ops0 = AIController.GetOpsTillSuspend();
    local context = ("trip" in candidate) ? candidate : null;
    local openingPlanes = 1;
    local evaluatedEconomics = context == null
        ? OpexC121EngineEconomics(catalog, plan, plane, openingPlanes, true, null)
        : OpexC121EngineEconomics(catalog, plan, plane, openingPlanes, true, null, null, context);
    local tick1 = AIController.GetTick();
    local ops = OpexAirCalcDeltaOps(tick0, ops0);
    if (ops >= 0) evalOpsTotal += ops;
    if (tick1 == tick0 && ops >= 0) {
      evalOps += ops;
      evalSameTick++;
    }
    if (engineMark != null) OpexSpanAgg("air.c121.engine", engineMark);
    if (evaluatedEconomics == null || !("decisionScore" in evaluatedEconomics)) {
      continue;
    }
    local economics = (("decisionEconomics" in evaluatedEconomics)
        && evaluatedEconomics.decisionEconomics != null)
        ? evaluatedEconomics.decisionEconomics : evaluatedEconomics;
    evaluated++;
    if (("engineMailKnown" in economics) && economics.engineMailKnown) known++;
    local item = { plane = plane, economics = economics, context = context };
    if (best == null
        || economics.decisionScore > best.economics.decisionScore
        || (economics.decisionScore == best.economics.decisionScore
            && economics.decisionProfitAnnual > best.economics.decisionProfitAnnual)
        || (economics.decisionScore == best.economics.decisionScore
            && economics.decisionProfitAnnual == best.economics.decisionProfitAnnual
            && plane.id < best.plane.id)) best = item;
  }
  local scanTick1 = AIController.GetTick();
  plan.c121EngineScanTicks <- scanTick1 - scanTick0;
  plan.c121EngineScanOps <- OpexAirCalcDeltaOps(scanTick0, scanOps0);
  plan.c121EngineEvalCount <- evaluated;
  plan.c121EngineKnownCount <- known;
  plan.c121EngineEvalOpsTotal <- evalOpsTotal;
  plan.c121EngineEvalOpsSameTick <- evalOps;
  plan.c121EngineEvalSameTickCount <- evalSameTick;
  if (perf != null) {
    if (plan.c121EngineScanOps >= 0) perf.scanOps += plan.c121EngineScanOps;
    perf.scanTicks += plan.c121EngineScanTicks;
    perf.engineEvals += evaluated;
  }
  {
    OpexC121GameEngineAfterScan(plan.airport.type, best, geMode);
    geState = OpexC121GameEngineState(plan.airport.type);
    geEst = geState.established ? geState.engine : -1;
  }
  }
  if (best == null) {
    if (perf != null) perf.noWinner++;
    return null;
  }
  /* Le scan decisionOnly choisit le moteur sur le chantier N=1. Pour ne pas
   * sous-evaluer les lignes dont la valeur vient de leur montee en charge, on
   * calcule ensuite UNE seule croisiere max-profit pour le moteur gagnant. Elle
   * sert uniquement au classement economique ; le chantier reste N=1 et la
   * cible exacte sera recalculee apres construction avec PASS/MAIL observes. */
  local fullTick0 = AIController.GetTick();
  local fullOps0 = AIController.GetOpsTillSuspend();
  local winnerMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  local winnerEconomics = best.context == null
      ? OpexC121WinnerEconomics(catalog, plan, best.plane)
      : OpexC121WinnerEconomics(catalog, plan, best.plane, best.context);
  local initialEconomics = winnerEconomics.initial;
  local fullBest = winnerEconomics.full;
  local fullTick1 = AIController.GetTick();
  plan.c121WinnerFullTicks <- fullTick1 - fullTick0;
  plan.c121WinnerFullOps <- OpexAirCalcDeltaOps(fullTick0, fullOps0);
  if (perf != null) {
    if (plan.c121WinnerFullOps >= 0) perf.winnerOps += plan.c121WinnerFullOps;
    perf.winnerTicks += plan.c121WinnerFullTicks;
  }
  if (initialEconomics == null) {
    if (geMode == 1) {
      OpexC121GameEngineLog("fallback", plan.airport.type, best.plane.id, best.plane.id,
          OpexC121GameEngineState(plan.airport.type).streak);
      geMode = 3;
      best = OpexC121ScanRoutePlaneEnginesFullScan(catalog, plan);
      {
        OpexC121GameEngineAfterScan(plan.airport.type, best, geMode);
        geState = OpexC121GameEngineState(plan.airport.type);
        geEst = geState.established ? geState.engine : -1;
      }
      if (best == null) {
        if (perf != null) perf.noWinner++;
        if (winnerMark != null) OpexSpanAgg("air.c121.winner", winnerMark);
        return null;
      }
      local retryTick0 = AIController.GetTick();
      local retryOps0 = AIController.GetOpsTillSuspend();
      winnerEconomics = best.context == null
          ? OpexC121WinnerEconomics(catalog, plan, best.plane)
          : OpexC121WinnerEconomics(catalog, plan, best.plane, best.context);
      initialEconomics = winnerEconomics.initial;
      fullBest = winnerEconomics.full;
      local retryTick1 = AIController.GetTick();
      plan.c121WinnerFullTicks <- plan.c121WinnerFullTicks + (retryTick1 - retryTick0);
      local retryOps = OpexAirCalcDeltaOps(retryTick0, retryOps0);
      if (retryOps >= 0) {
        if (plan.c121WinnerFullOps >= 0) plan.c121WinnerFullOps += retryOps;
        else plan.c121WinnerFullOps <- retryOps;
      }
      if (perf != null) {
        if (retryOps >= 0) perf.winnerOps += retryOps;
        perf.winnerTicks += retryTick1 - retryTick0;
      }
    }
    if (initialEconomics == null) {
      if (winnerMark != null) OpexSpanAgg("air.c121.winner", winnerMark);
      return null;
    }
  }
  if (fullBest == null) fullBest = initialEconomics;
  local decisionEconomics = fullBest;
  local portfolioEconomics = null;
  plan.c121ChosenEngine <- best.plane.id;
  plan.c121ChosenMailKnown <- (("engineMailKnown" in initialEconomics) && initialEconomics.engineMailKnown);
  if (winnerMark != null) OpexSpanAgg("air.c121.winner", winnerMark);
  local routeChoice = { plane = best.plane, economics = initialEconomics, decisionEconomics = decisionEconomics,
      portfolioEconomics = portfolioEconomics, targetPlanes = initialEconomics.planes };
  return routeChoice;
}
