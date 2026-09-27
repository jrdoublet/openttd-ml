/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexSaveRailExpansion(state)
{
  if (state == null || typeof state != "table") return null;
  /* Le format de sauvegarde NoAI refuse les floats. _continueRailExpansion() n'a besoin
   * que de ces champs ; newSpeed/newOneWayDays sont donc conserves en milli-unites entieres. */
  return {
    lineId = state.lineId,
    vehicle = state.vehicle,
    wagonId = state.wagonId,
    oldWagons = ("oldWagons" in state) ? state.oldWagons : (state.newWagons - 1),
    newWagons = state.newWagons,
    oldTrainLength = ("oldTrainLength" in state) ? state.oldTrainLength : -1,
    oldExpansionCount = ("oldExpansionCount" in state) ? state.oldExpansionCount : 0,
    decisionYear = ("decisionYear" in state) ? state.decisionYear : -1,
    newSpeedMilli = (state.newSpeed * 1000).tointeger(),
    newOneWayMilliDays = (state.newOneWayDays * 1000).tointeger(),
    decisionDate = state.decisionDate,
    waitDays = state.waitDays,
    startDate = state.startDate,
    phase = state.phase,
    dispatchAttempts = state.dispatchAttempts,
    resumeAttempts = ("resumeAttempts" in state) ? state.resumeAttempts : 0,
    temporaryOrder = state.temporaryOrder,
    temporaryOrderPosition = state.temporaryOrderPosition,
    commitStage = ("commitStage" in state) ? state.commitStage : "idle",
    pendingWagon = ("pendingWagon" in state) ? state.pendingWagon : -1,
    ops = state.ops,
    cost = state.cost,
  };
}

function OpexLoadRailExpansion(data)
{
  if (data == null || typeof data != "table") return null;
  local required = ["lineId", "vehicle", "wagonId", "oldWagons", "newWagons",
                    "oldTrainLength", "oldExpansionCount", "decisionYear",
                    "newSpeedMilli", "newOneWayMilliDays", "decisionDate", "waitDays",
                    "startDate", "phase", "dispatchAttempts", "temporaryOrder",
                    "temporaryOrderPosition", "commitStage", "pendingWagon", "ops", "cost"];
  foreach (key in required) {
    if (!(key in data)) return null;
  }
  return {
    lineId = data.lineId,
    vehicle = data.vehicle,
    wagonId = data.wagonId,
    oldWagons = data.oldWagons,
    newWagons = data.newWagons,
    oldTrainLength = data.oldTrainLength,
    oldExpansionCount = data.oldExpansionCount,
    decisionYear = data.decisionYear,
    newSpeed = data.newSpeedMilli.tofloat() / 1000.0,
    newOneWayDays = data.newOneWayMilliDays.tofloat() / 1000.0,
    decisionDate = data.decisionDate,
    waitDays = data.waitDays,
    startDate = data.startDate,
    phase = data.phase,
    dispatchAttempts = data.dispatchAttempts,
    resumeAttempts = ("resumeAttempts" in data) ? data.resumeAttempts : 0,
    temporaryOrder = data.temporaryOrder,
    temporaryOrderPosition = data.temporaryOrderPosition,
    commitStage = data.commitStage,
    pendingWagon = data.pendingWagon,
    ops = data.ops,
    cost = data.cost,
  };
}

/* V88 : Sauvegarde d'une chaine industrielle en cours (sans floats pour NoAI) */
function OpexSaveGoodsChain(chain)
{
  if (chain == null || typeof chain != "table") return null;
  local gc = ("goodsCandidate" in chain && chain.goodsCandidate != null) ? chain.goodsCandidate : null;
  local savedGc = null;
  if (gc != null) {
    savedGc = {
      src = gc.src,
      dst = gc.dst,
      cargo = gc.cargo,
      kind = gc.kind,
      capital = gc.capital.tointeger(),
      profitAnnual = gc.profitAnnual.tointeger(),
      monthly = gc.monthly.tointeger(),
      distance = gc.distance.tointeger(),
      wagons = gc.wagons,
      trains = gc.trains,
      platformLength = gc.platformLength,
      revenueAnnual = gc.revenueAnnual.tointeger(),
      runningAnnual = gc.runningAnnual.tointeger(),
      amortAnnual = gc.amortAnnual.tointeger(),
      carried = gc.carried.tointeger(),
      offered = gc.offered.tointeger(),
      oneWayDays = gc.oneWayDays.tointeger(),
      headwayDays = gc.headwayDays.tointeger(),
      stationRating = gc.stationRating.tointeger(),
      trainsForHeadway = gc.trainsForHeadway,
      monthlyCapacity = gc.monthlyCapacity.tointeger(),
      effectiveSpeed = gc.effectiveSpeed.tointeger(),
      locoId = ("loco" in gc && gc.loco != null && ("id" in gc.loco)) ? gc.loco.id : -1,
    };
  }
  local plat = ("factoryPlatform" in chain && chain.factoryPlatform != null) ? chain.factoryPlatform : null;
  local savedPlat = null;
  if (plat != null) {
    savedPlat = {
      anchor = plat.anchor,
      direction = plat.direction,
      length = plat.length,
      step = plat.step
    };
  }
  return {
    step = chain.step,
    factoryId = chain.factoryId,
    townId = chain.townId,
    inputLineId = chain.inputLineId,
    factoryStationId = chain.factoryStationId,
    factoryPlatform = savedPlat,
    goodsCandidate = savedGc,
    year = ("year" in chain) ? chain.year : 0
  };
}

function OpexLoadGoodsChain(data, catalog = null)
{
  if (data == null || typeof data != "table") return null;
  if (!("step" in data) || !("factoryId" in data) || !("townId" in data)) return null;
  local chain = {
    step = data.step,
    factoryId = data.factoryId,
    townId = data.townId,
    inputLineId = ("inputLineId" in data) ? data.inputLineId : -1,
    factoryStationId = ("factoryStationId" in data) ? data.factoryStationId : -1,
    factoryPlatform = ("factoryPlatform" in data) ? data.factoryPlatform : null,
    goodsCandidate = null,
    year = ("year" in data) ? data.year : 0
  };
  if (("goodsCandidate" in data) && data.goodsCandidate != null) {
    local gc = data.goodsCandidate;
    local loco = null;
    if (catalog != null && ("bestLocoByCargo" in catalog) && (gc.cargo in catalog.bestLocoByCargo)) {
      loco = catalog.bestLocoByCargo[gc.cargo];
    } else if (catalog != null && ("locos" in catalog) && ("locoId" in gc) && gc.locoId >= 0) {
      foreach (l in catalog.locos) {
        if (l.id == gc.locoId) { loco = l; break; }
      }
    }
    chain.goodsCandidate = {
      mode = "rail",
      kind = gc.kind,
      src = gc.src,
      dst = gc.dst,
      cargo = gc.cargo,
      capital = gc.capital,
      profitAnnual = gc.profitAnnual,
      monthly = gc.monthly,
      distance = gc.distance,
      wagons = gc.wagons,
      trains = gc.trains,
      platformLength = gc.platformLength,
      revenueAnnual = gc.revenueAnnual,
      runningAnnual = gc.runningAnnual,
      amortAnnual = gc.amortAnnual,
      carried = gc.carried,
      offered = gc.offered,
      oneWayDays = gc.oneWayDays,
      headwayDays = gc.headwayDays,
      stationRating = gc.stationRating,
      trainsForHeadway = gc.trainsForHeadway,
      monthlyCapacity = gc.monthlyCapacity,
      effectiveSpeed = gc.effectiveSpeed,
      loco = loco,
      isChainStep2 = true,
      factoryId = chain.factoryId,
      townId = chain.townId
    };
  }
  return chain;
}

function OpexCopyBoolTable(source)
{
  local out = {};
  if (source == null) return out;
  foreach (key, val in source) out.rawset(key, val ? true : false);
  return out;
}

function OpexSaveReactiveQueue(queue)
{
  if (queue == null) return [];
  local rawList = (typeof queue == "instance" && ("toArray" in queue)) ? queue.toArray() : queue;
  if (rawList == null || typeof rawList != "array") return [];
  local out = [];
  foreach (item in rawList) {
    if (item == null || typeof item != "table") continue;
    if (!("key" in item) || !("kind" in item)) continue;
    out.append({
      key = item.key,
      kind = item.kind,
      payload = ("payload" in item) ? item.payload : null,
      enqueuedDate = ("enqueuedDate" in item) ? item.enqueuedDate : 0,
      count = ("count" in item) ? item.count : 1
    });
  }
  return out;
}

function OpexLoadReactiveQueue(data)
{
  local q = OpexReactiveQueue();
  if (data == null || typeof data != "array") return q;
  foreach (item in data) {
    if (item == null || typeof item != "table") continue;
    if (!("key" in item) || !("kind" in item)) continue;
    local enqueuedDate = ("enqueuedDate" in item) ? item.enqueuedDate : AIDate.GetCurrentDate();
    local count = ("count" in item) ? item.count : 1;
    local payload = ("payload" in item) ? item.payload : null;
    q.restoreItem(item.key, item.kind, payload, enqueuedDate, count);
  }
  return q;
}

function OpexSaveActiveWorker(worker)
{
  if (worker == null || typeof worker != "table") return null;
  if (!("kind" in worker) || !("state" in worker) || worker.state == null || typeof worker.state != "table") return null;
  if (worker.kind == "rail_search") {
    /* C80 tranche 1 : _railSearch contient un pathfinder C++ non sérialisable.
     * On ne sauvegarde pas le pathfinder dans le savegame. */
    return {
      kind = worker.kind,
      state = {}
    };
  }
  if (worker.kind == "town_growth") {
    /* C80 tranche 2 : le state de town_growth ne contient que des entiers et tableaux d'entiers. */
    local s = worker.state;
    local townsCopy = [];
    if ("servedTownsList" in s && s.servedTownsList != null) {
      foreach (t in s.servedTownsList) townsCopy.append(t);
    }
    return {
      kind = worker.kind,
      state = {
        cursorTownIndex = ("cursorTownIndex" in s) ? s.cursorTownIndex : 0,
        servedTownsList = townsCopy,
        year = ("year" in s) ? s.year : 0
      }
    };
  }
  if (worker.kind == "regen_candidates") {
    /* C78.4 : la tranche AIR contient temporairement des plans/economics avec
     * des flottants, interdits par le format de sauvegarde. Rien n'est publie
     * dans candidateGroups avant DONE : on peut donc jeter uniquement la
     * tranche AIR en cours et reprendre ce mode depuis son debut apres Load. */
    local s = worker.state;
    local modesCopy = [];
    if (("modes" in s) && s.modes != null && typeof s.modes == "array") {
      foreach (mode in s.modes) modesCopy.append(mode);
    }
    return {
      kind = worker.kind,
      state = {
        modes = modesCopy,
        cursor = ("cursor" in s) ? s.cursor : 0,
        targeted = ("targeted" in s) ? s.targeted : false,
        entityKind = ("entityKind" in s) ? s.entityKind : null,
        entityId = ("entityId" in s) ? s.entityId : -1,
        buildAfter = ("buildAfter" in s) ? s.buildAfter : false,
        reason = ("reason" in s) ? s.reason : "event",
      }
    };
  }
  return {
    kind = worker.kind,
    state = worker.state
  };
}

function OpexLoadActiveWorker(data)
{
  if (data == null || typeof data != "table") return null;
  if (!("kind" in data) || !("state" in data) || data.state == null || typeof data.state != "table") return null;
  local kind = data.kind;
  if (!(kind in OPEX_WORKER_REGISTRY)) {
    AILog.Warning("C80: dropped active worker of unknown kind: " + kind);
    return null;
  }
  return {
    kind = kind,
    state = data.state
  };
}

function OpexAI::_railLineHasVehicle(line, vehicle)
{
  if (line == null || !("vehicles" in line) || line.vehicles == null) return false;
  foreach (known in line.vehicles) {
    if (known == vehicle) return true;
  }
  return false;
}

function OpexAI::_removePersistedRailTemporaryOrder(state, line)
{
  if (state == null || !("temporaryOrder" in state) || !state.temporaryOrder ||
      !AIVehicle.IsValidVehicle(state.vehicle)) return true;
  local pos = state.temporaryOrderPosition;
  if (pos < 0 || !AIOrder.IsValidVehicleOrder(state.vehicle, pos) ||
      !AIOrder.IsGotoDepotOrder(state.vehicle, pos)) {
    state.temporaryOrder = false;
    state.temporaryOrderPosition = -1;
    return false;
  }
  if (line != null && ("depot" in line) &&
      AIOrder.GetOrderDestination(state.vehicle, pos) != line.depot) {
    state.temporaryOrder = false;
    state.temporaryOrderPosition = -1;
    return false;
  }
  if (!AIOrder.RemoveOrder(state.vehicle, pos)) return false;
  state.temporaryOrder = false;
  state.temporaryOrderPosition = -1;
  return true;
}

function OpexAI::_commitPersistedRailExpansionMetadata(line, state)
{
  /* Idempotent : utiliser l'ancien compteur memorise plutot que += 1 empeche un double comptage
   * si le save tombe sur la frontiere physique/metadata de la transaction. */
  line.wagons = state.newWagons;
  line.wagonId <- state.wagonId;
  line.effectiveSpeed = state.newSpeed;
  line.predOneWayDays = state.newOneWayDays;
  line.headwayDays = 2 * state.newOneWayDays;
  line.expandStreak <- 0;
  line.railExpansions <- state.oldExpansionCount + 1;
  line.lastExpansionYear <- state.decisionYear;
}

function OpexAI::_abortPersistedRailExpansion(state, line)
{
  if (state != null && ("pendingWagon" in state) && state.pendingWagon >= 0 &&
      AIVehicle.IsValidVehicle(state.pendingWagon) &&
      !AIVehicle.IsPrimaryVehicle(state.pendingWagon)) {
    AIVehicle.SellVehicle(state.pendingWagon);
    state.pendingWagon = -1;
  }
  if (state != null && ("vehicle" in state) && AIVehicle.IsValidVehicle(state.vehicle)) {
    local hadTemporaryOrder = ("temporaryOrder" in state) && state.temporaryOrder;
    this._removePersistedRailTemporaryOrder(state, line);
    if (AIVehicle.IsStoppedInDepot(state.vehicle)) {
      AIVehicle.StartStopVehicle(state.vehicle);
    } else if (!hadTemporaryOrder && line != null && ("depot" in line)) {
      /* SendVehicleToDepot est un toggle : ne l'utiliser comme annulation que si l'ordre courant
       * est bien NOTRE diversion vers ce depot. */
      local pos = AIOrder.ResolveOrderPosition(state.vehicle, AIOrder.ORDER_CURRENT);
      if (pos != AIOrder.ORDER_INVALID && AIOrder.IsValidVehicleOrder(state.vehicle, pos) &&
          AIOrder.IsGotoDepotOrder(state.vehicle, pos) &&
          AIOrder.GetOrderDestination(state.vehicle, pos) == line.depot) {
        AIVehicle.SendVehicleToDepot(state.vehicle);
      }
    }
  }
  if (line != null) {
    line.expandStreak <- 0;
    line.expandRetryCycle <- this._taskCycle + 3;
  }
  this._railExpansion = null;
}

function OpexAI::_reconcileRailExpansionAfterLoad()
{
  local result = { restored = 0, completed = 0, dropped = 0, promoted = 0,
                   pending_recovered = 0, ambiguous_aborted = 0 };
  if (this._railExpansion == null) return result;
  local state = this._railExpansion;
  local line = ("lineId" in state) ? this._findLineById(state.lineId) : null;
  local vehicleValid = ("vehicle" in state) && AIVehicle.IsValidVehicle(state.vehicle) &&
      AIVehicle.IsPrimaryVehicle(state.vehicle) &&
      AIVehicle.GetVehicleType(state.vehicle) == AIVehicle.VT_RAIL;
  local phaseValid = ("phase" in state) &&
      (state.phase == "approach" || state.phase == "depot" || state.phase == "resume");
  local stageValid = ("commitStage" in state) &&
      (state.commitStage == "idle" || state.commitStage == "build_started" ||
       state.commitStage == "wagon_built" || state.commitStage == "wagon_moved" ||
       state.commitStage == "metadata_done");
  local shapeValid = ("oldWagons" in state) && ("newWagons" in state) &&
      state.newWagons == state.oldWagons + 1;
  local lineValid = line != null && ("mode" in line) && line.mode == "rail" &&
      this._railLineHasVehicle(line, state.vehicle);
  local depotValid = lineValid && ("depot" in line) && AIMap.IsValidTile(line.depot) &&
      AIRail.IsRailDepotTile(line.depot);

  if (!vehicleValid || !phaseValid || !stageValid || !shapeValid || !lineValid ||
      (state.phase != "resume" && !depotValid)) {
    /* Nettoyage best-effort : ne pas laisser notre ordre temporaire ni une rame arretee si le
     * descriptor n'est plus reconciliable avec le monde charge. */
    this._abortPersistedRailExpansion(state, line);
    result.dropped++;
    return result;
  }

  local currentLength = AIVehicle.GetLength(state.vehicle);
  local physicalCommitted =
      (("wagons" in line) && line.wagons == state.newWagons) ||
      (state.oldTrainLength >= 0 && currentLength > state.oldTrainLength);

  if (!physicalCommitted && state.commitStage == "wagon_built") {
    local pending = state.pendingWagon;
    local pendingValid = pending >= 0 && AIVehicle.IsValidVehicle(pending) &&
        !AIVehicle.IsPrimaryVehicle(pending) &&
        AIVehicle.GetVehicleType(pending) == AIVehicle.VT_RAIL &&
        AIVehicle.GetEngineType(pending) == state.wagonId &&
        AIVehicle.GetLocation(pending) == line.depot;
    local fits = pendingValid &&
        AIVehicle.GetLength(state.vehicle) + AIVehicle.GetLength(pending) <= line.platformLength * 16;
    if (fits && AIVehicle.MoveWagon(pending, 0, state.vehicle, 0)) {
      state.pendingWagon = -1;
      state.commitStage = "wagon_moved";
      currentLength = AIVehicle.GetLength(state.vehicle);
      physicalCommitted = state.oldTrainLength < 0 || currentLength > state.oldTrainLength;
      result.pending_recovered++;
    } else {
      this._abortPersistedRailExpansion(state, line);
      result.dropped++;
      return result;
    }
  }

  if (!physicalCommitted && state.commitStage == "build_started") {
    /* Etat ambigu : la commande peut avoir ete executee sans que son VehicleID ait encore ete
     * stocke. Ne jamais relancer BuildVehicle au reload, donc jamais de double wagon. */
    this._abortPersistedRailExpansion(state, line);
    result.dropped++;
    result.ambiguous_aborted++;
    return result;
  }

  if (!physicalCommitted &&
      (state.commitStage == "wagon_moved" || state.commitStage == "metadata_done")) {
    this._abortPersistedRailExpansion(state, line);
    result.dropped++;
    return result;
  }

  if (physicalCommitted) {
    this._commitPersistedRailExpansionMetadata(line, state);
    state.pendingWagon = -1;
    state.commitStage = "metadata_done";
    state.phase = "resume";
    result.promoted++;
    /* Si la rame a deja quitte le depot, la reprise a donc deja reussi : surtout ne pas
     * rappeler StartStopVehicle(), qui la stopperait a nouveau. */
    if (!AIVehicle.IsStoppedInDepot(state.vehicle)) {
      this._removePersistedRailTemporaryOrder(state, line);
      this._railExpansion = null;
      result.completed++;
      return result;
    }
    this._removePersistedRailTemporaryOrder(state, line);
    result.restored++;
    return result;
  }

  /* Une sauvegarde prise entre l'insertion de l'ordre depot et l'affectation phase="depot" est
   * improbable (le callback script est atomique), mais cette normalisation rend la reprise sure
   * meme dans ce cas. */
  if (state.temporaryOrder) {
    local pos = state.temporaryOrderPosition;
    local orderValid = pos >= 0 && AIOrder.IsValidVehicleOrder(state.vehicle, pos) &&
        AIOrder.IsGotoDepotOrder(state.vehicle, pos) &&
        AIOrder.GetOrderDestination(state.vehicle, pos) == line.depot;
    if (orderValid) {
      state.phase = "depot";
    } else {
      state.temporaryOrder = false;
      state.temporaryOrderPosition = -1;
      state.phase = "approach";
    }
  }
  result.restored++;
  return result;
}

function OpexAI::_filterPersistedRailRepairQueue(source)
{
  local out = {};
  if (source == null) return out;
  foreach (key, ignored in source) {
    local lineId = key.tointeger();
    local line = this._findLineById(lineId);
    if (line != null && ("mode" in line) && line.mode == "rail" &&
        ("doubleTrack" in line) && line.doubleTrack == 1) {
      out.rawset("" + lineId, true);
    }
  }
  return out;
}

function OpexAI::_rearmPersistedRailRepairTasks()
{
  if (this._taskQueue == null) return;
  foreach (task in this._taskQueue) {
    if (task.name == "c41_rail_signals") {
      local active = C41_RAIL_LOST_SIGNAL_REPAIR && this._c41RailSignalLines != null &&
          this._c41RailSignalLines.len() > 0;
      task.enabled = active;
      task.dueCycle = active ? this._taskCycle : 2147483647;
    } else if (task.name == "c41_rail_junction") {
      local active = C41_RAIL_LOST_JUNCTION_REPAIR && this._c41RailJunctionLines != null &&
          this._c41RailJunctionLines.len() > 0;
      task.enabled = active;
      task.dueCycle = active ? this._taskCycle : 2147483647;
    }
  }
}

/* Cles ajoutees seulement quand c83_preempt_open est arme : a 0 le format
 * historique de Save() ne gagne aucun champ. */
function OpexSaveC83Preempt(saveObj, ai)
{
  if (!C83_PREEMPT_OPEN || saveObj == null || ai == null) return;
  saveObj.c83PreemptTown <- C83_PREEMPT_TOWN;
  saveObj.c83PreemptStopped <- C83_PREEMPT_STOPPED ? 1 : 0;
  saveObj.c83PreemptQueued <- ai._c83PreemptQueued;
  local race = {};
  if (ai._c83PreemptRace != null) {
    foreach (townId, when in ai._c83PreemptRace) race.rawset(townId, when);
  }
  saveObj.c83PreemptRace <- race;
}

function OpexAI::Save()
{
  local abandoned = {};
  if (this._abandonedPairs != null) {
    foreach (key, val in this._abandonedPairs) abandoned[key] <- val;
  }
  /* A 0, conserver exactement le format historique : la charge complete est experimentale et
   * le serialiseur execute Save() sous budget d'opcodes. */
  if (!SAVE_FULL_STATE) {
    local shortSave = {
      version = 1,
      generationStage = this._generationStage,
      generationStageMonth = this._generationStageMonth,
      lastFreightCargo = this._lastFreightCargo,
      bootstrapFreightCargo = this._bootstrapFreightCargo,
      nextLineId = this._nextLineId,
      lastCatalogMonth = this._lastCatalogMonth,
      lastReportYear = this._lastReportYear,
      startYear = this._startYear,
      abandonedPairs = abandoned,
      airBuilt = this._airBuilt,
      waterBuilt = this._waterBuilt,
    };
    if (this._activeGoodsChain != null) {
      shortSave.activeGoodsChain <- OpexSaveGoodsChain(this._activeGoodsChain);
    }
    if (C76_REGEN_TARGETED) {
      shortSave.c76Revisions <- this._c76SaveRevisions();
    }
    if (C83_PREEMPT_OPEN) OpexSaveC83Preempt(shortSave, this);
    return shortSave;
  }

  local taskDue = {};
  if (this._taskQueue != null) {
    foreach (task in this._taskQueue) taskDue[task.name] <- task.dueCycle;
  }
  /* Certains modeles economiques (surtout air) laissent des flottants dans des metriques
   * predites, type que le format de sauvegarde OpenTTD refuse. Toujours projeter chaque ligne
   * en UN SEUL passage : l'ancien probe "faut-il projeter ?" reparcourait ensuite presque toutes
   * les lignes et finissait par epuiser le budget de 100k opcodes de Save() sur les grosses
   * flottes. Les champs scalarises restants sont serialisables; les tableaux (VehicleID) et
   * tables des lignes actuelles ne contiennent que des entiers/booleens/null. */
  local saveLines = this._lines;
  if (this._lines != null) {
    local projectedLines = [];
    foreach (line in this._lines) {
      if (line == null || typeof line != "table") {
        projectedLines.append(line);
        continue;
      }
      local serializableLine = {};
      foreach (key, val in line) {
        local valType = typeof val;
        if (valType == "integer" || valType == "string" || valType == "bool" ||
            valType == "null" || valType == "array" || valType == "table") {
          serializableLine[key] <- val;
        } else if (valType == "float") {
          /* Le format de sauvegarde n'admet pas le flottant : arrondir CONSERVE le champ (une
           * metrique predite), alors que le jeter le perdrait en silence au rechargement. */
          serializableLine[key] <- val.tointeger();
        }
      }
      projectedLines.append(serializableLine);
    }
    saveLines = projectedLines;
  }
  local saveObj = {
    version = 1,
    /* C69/C75 : sans ces dates, tau repart de 0 chantier sur une fenetre de 365 jours et K_dec /
     * K_pass explosent pendant un an apres chargement (docs/19_rechargement_partie.md). Entiers. */
    c69BuildDates = C69_BUILD_DATES,
    c75PassDates = C75_PASS_DATES,
    generationStage = this._generationStage,
    generationStageMonth = this._generationStageMonth,
    lastFreightCargo = this._lastFreightCargo,
    bootstrapFreightCargo = this._bootstrapFreightCargo,
    nextLineId = this._nextLineId,
    lastCatalogMonth = this._lastCatalogMonth,
    lastReportYear = this._lastReportYear,
    startYear = this._startYear,
    abandonedPairs = abandoned,
    airBuilt = this._airBuilt,
    waterBuilt = this._waterBuilt,
    lines = saveLines,
    abandonCounts = this._abandonCounts,
    lastRepayMonth = this._lastRepayMonth,
    taskCycle = this._taskCycle,
    taskCursor = this._taskCursor,
    vehiclesToRetire = this._vehiclesToRetire,
    unprofitableStreaks = this._unprofitableStreaks,
    activeSubsidies = this._activeSubsidies,
    taskDue = taskDue,
    railExpansion = OpexSaveRailExpansion(this._railExpansion),
    railSearchPending = this._railSearch != null,
    c41RailSignalLines = OpexCopyBoolTable(this._c41RailSignalLines),
    c41RailJunctionLines = OpexCopyBoolTable(this._c41RailJunctionLines),
    activeGoodsChain = OpexSaveGoodsChain(this._activeGoodsChain),
    stateVersion = 2,
  };
  if (C80_DOUBLE_REGISTER) {
    saveObj.c80ReactiveQueue <- OpexSaveReactiveQueue(this._reactiveQueue);
    saveObj.c80ActiveWorker <- OpexSaveActiveWorker(this._activeWorker);
  }
  if (C76_REGEN_TARGETED) {
    saveObj.c76Revisions <- this._c76SaveRevisions();
  }
  if (C83_PREEMPT_OPEN) OpexSaveC83Preempt(saveObj, this);
  return saveObj;
}
function OpexAI::Load(version, data)
{
  this._loadedFromSave = true;
  if (data == null) return;
  this._reloadC69BuildDates = ("c69BuildDates" in data) ? data.c69BuildDates : null;
  this._reloadC75PassDates = ("c75PassDates" in data) ? data.c75PassDates : null;
  if ("generationStage" in data) this._generationStage = data.generationStage;
  if ("generationStageMonth" in data) this._generationStageMonth = data.generationStageMonth;
  if ("lastFreightCargo" in data) this._lastFreightCargo = data.lastFreightCargo;
  if ("bootstrapFreightCargo" in data) this._bootstrapFreightCargo = data.bootstrapFreightCargo;
  if ("nextLineId" in data) this._nextLineId = data.nextLineId;
  if ("lastCatalogMonth" in data) this._lastCatalogMonth = data.lastCatalogMonth;
  if ("lastReportYear" in data) this._lastReportYear = data.lastReportYear;
  if ("startYear" in data) this._startYear = data.startYear;
  if ("airBuilt" in data) this._airBuilt = data.airBuilt;
  if ("waterBuilt" in data) this._waterBuilt = data.waterBuilt;
  if ("abandonedPairs" in data && data.abandonedPairs != null) {
    this._abandonedPairs = {};
    foreach (key, val in data.abandonedPairs) this._abandonedPairs[key] <- val;
  }
  if ("lines" in data) this._pendingLines = data.lines;
  if ("abandonCounts" in data && data.abandonCounts != null) this._abandonCounts = data.abandonCounts;
  if ("lastRepayMonth" in data) this._lastRepayMonth = data.lastRepayMonth;
  if ("taskCycle" in data) this._taskCycle = data.taskCycle;
  if ("taskCursor" in data) this._taskCursor = data.taskCursor;
  if ("vehiclesToRetire" in data && data.vehiclesToRetire != null) this._vehiclesToRetire = data.vehiclesToRetire;
  if ("unprofitableStreaks" in data && data.unprofitableStreaks != null) this._unprofitableStreaks = data.unprofitableStreaks;
  if ("activeSubsidies" in data && data.activeSubsidies != null) this._activeSubsidies = data.activeSubsidies;
  /* 11.6/11.7 : aucune lecture du monde ici. Les validations VehicleID/LineID attendent
   * _reconcileAfterLoad(), appelé depuis Start() après OpexLoadSettings(). Les sauvegardes
   * stateVersion=1 n'ont simplement pas ces champs et gardent les valeurs constructeur. */
  if ("railExpansion" in data) this._railExpansion = OpexLoadRailExpansion(data.railExpansion);
  this._reloadDroppedRailSearch = ("railSearchPending" in data) && data.railSearchPending;
  if (("dynamicBatchPending" in data) && data.dynamicBatchPending) {
    this._projects = null;
    this._ranked = null;
    this._portfolioInvalidated = true;
  }
  if ("c41RailSignalLines" in data && data.c41RailSignalLines != null) {
    this._c41RailSignalLines = OpexCopyBoolTable(data.c41RailSignalLines);
  }
  if ("c41RailJunctionLines" in data && data.c41RailJunctionLines != null) {
    this._c41RailJunctionLines = OpexCopyBoolTable(data.c41RailJunctionLines);
  }
  if ("activeGoodsChain" in data) this._activeGoodsChain = OpexLoadGoodsChain(data.activeGoodsChain, this._catalog);
  /* Cle par nom : l'ordre de la file peut evoluer entre deux versions de l'IA. */
  if ("taskDue" in data && data.taskDue != null && this._taskQueue != null) {
    foreach (task in this._taskQueue) {
      if (task.name in data.taskDue) task.dueCycle = data.taskDue[task.name];
    }
  }
  /* Load() precede OpexLoadSettings() : ne jamais conditionner la restauration
   * C80/C76 aux drapeaux runtime, encore a leurs valeurs globales false ici. */
  if ("c80ReactiveQueue" in data && data.c80ReactiveQueue != null) {
    this._reactiveQueue = OpexLoadReactiveQueue(data.c80ReactiveQueue);
  }
  if ("c80ActiveWorker" in data && data.c80ActiveWorker != null) {
    this._activeWorker = OpexLoadActiveWorker(data.c80ActiveWorker);
  }
  if ("c76Revisions" in data && data.c76Revisions != null) {
    this._c76LoadRevisions(data.c76Revisions);
  }
  if ("c83PreemptTown" in data) this._reloadC83PreemptTown = data.c83PreemptTown;
  if ("c83PreemptStopped" in data) this._reloadC83PreemptStopped = data.c83PreemptStopped;
  if ("c83PreemptQueued" in data) this._reloadC83PreemptQueued = data.c83PreemptQueued;
  if ("c83PreemptRace" in data) this._reloadC83PreemptRace = data.c83PreemptRace;
}
/* Load tourne trop tot et sous DisableDoCommandScope : la verification du monde est donc faite
 * ici, apres les reglages. Les stationA/stationB sont des TUILES, jamais des StationID. */
function OpexAI::_reconcileAfterLoad()
{
  /* C69/C75/C70 : restaurer APRES OpexLoadSettings() et les remises a zero de Start(). */
  if (C69_TRACK_BUILDS && this._reloadC69BuildDates != null && typeof this._reloadC69BuildDates == "array") {
    C69_BUILD_DATES = this._reloadC69BuildDates;
  }
  if (C75_TRACK_PASSES && this._reloadC75PassDates != null && typeof this._reloadC75PassDates == "array") {
    C75_PASS_DATES = this._reloadC75PassDates;
  }
  if (C83_PREEMPT_OPEN) {
    if (this._reloadC83PreemptTown != null) ::C83_PREEMPT_TOWN = this._reloadC83PreemptTown;
    if (this._reloadC83PreemptStopped != null) ::C83_PREEMPT_STOPPED = this._reloadC83PreemptStopped != 0;
    if (this._reloadC83PreemptQueued != null) this._c83PreemptQueued = this._reloadC83PreemptQueued;
    if (this._reloadC83PreemptRace != null && typeof this._reloadC83PreemptRace == "table") {
      this._c83PreemptRace = {};
      foreach (townId, when in this._reloadC83PreemptRace) this._c83PreemptRace.rawset(townId, when);
    }
  }
  this._reloadC83PreemptTown = null;
  this._reloadC83PreemptStopped = null;
  this._reloadC83PreemptQueued = null;
  this._reloadC83PreemptRace = null;
  this._reloadC69BuildDates = null;
  this._reloadC75PassDates = null;

  local saved = 0;
  local kept = 0;
  local dropped = 0;
  local purgedVehicles = 0;
  local liveLines = [];
  if (this._pendingLines != null) {
    foreach (line in this._pendingLines) {
      saved++;
      if (line == null || !("stationA" in line) || !("stationB" in line) ||
          !AIMap.IsValidTile(line.stationA) || !AIMap.IsValidTile(line.stationB)) {
        dropped++;
        continue;
      }
      local stationA = AIStation.GetStationID(line.stationA);
      local stationB = AIStation.GetStationID(line.stationB);
      if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) ||
          !AICompany.IsMine(AITile.GetOwner(line.stationA)) ||
          !AICompany.IsMine(AITile.GetOwner(line.stationB))) {
        dropped++;
        continue;
      }
      /* Les camions sont identifies par leurs ordres : ne pas reecrire le champ vehicles d'une
       * ligne route, meme si une ancienne version l'a laisse dans la table. */
      if ((!("mode" in line) || line.mode != "road") && ("vehicles" in line) && line.vehicles != null) {
        local liveVehicles = [];
        foreach (vehicle in line.vehicles) {
          if (AIVehicle.IsValidVehicle(vehicle)) liveVehicles.append(vehicle);
          else purgedVehicles++;
        }
        line.vehicles = liveVehicles;
      }
      /* Les sauvegardes anterieures a C52 ne portent pas le moteur de secours.
       * Tant qu'un appareil/navire vit encore, migrer cette metadonnee ici pour
       * qu'un prochain crash puisse etre reconstruit sans template. */
      if ((("mode" in line) && (line.mode == "air" || line.mode == "water")) &&
          !(("refleetEngine" in line) && line.refleetEngine >= 0)) {
        local template = null;
        if (("vehicles" in line) && line.vehicles != null) {
          foreach (vehicle in line.vehicles) {
            if (AIVehicle.IsValidVehicle(vehicle)) { template = vehicle; break; }
          }
        }
        if (template == null && ("vehicle" in line) && AIVehicle.IsValidVehicle(line.vehicle)) {
          template = line.vehicle;
        }
        if (template != null) line.refleetEngine <- AIVehicle.GetEngineType(template);
      }
      liveLines.append(line);
      kept++;
    }
  }
  this._lines = liveLines;
  this._pendingLines = null;
  /* C70/C82 : recalcul des facteurs APRES la reconstitution de this._lines. Appele plus haut, il
   * tournait sur la liste encore vide et remettait tous les facteurs a 1 (mesure 2026-09-22). */
  if (C70_MODE_CALIBRATION) OpexC70RecomputeFactors(this._lines);
  if (C82_ENGINE_CALIBRATION || C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY) OpexC82RecomputeFactors(this._lines);

  local railExpansion = this._reconcileRailExpansionAfterLoad();

  /* _railSearch contient un pathfinder/segmented search vivant, qui n'est pas persiste.
   * Si Save() l'a vu actif, abandon explicite puis reconstruction immediate du portefeuille. */
  local droppedRailSearch = this._reloadDroppedRailSearch ? 1 : 0;
  if (this._reloadDroppedRailSearch) {
    this._railSearch = null;
    this._projects = null;
    this._ranked = null;
    this._portfolioInvalidated = true;
    if (this._taskQueue != null) {
      foreach (task in this._taskQueue) {
        if (task.name == "catalog") {
          task.enabled = true;
          task.dueCycle = this._taskCycle;
          break;
        }
      }
    }
  }
  this._reloadDroppedRailSearch = false;

  /* C80 tranche 1 : au rechargement, un travailleur "rail_search" restauré sans
   * _railSearch (qui n'est pas sauvegardé) doit être abandonné proprement. */
  if (this._activeWorker != null && this._activeWorker.kind == "rail_search" && this._railSearch == null) {
    OpexWorkerCancel(this._activeWorker);
    this._activeWorker = null;
  }

  /* C77 : le travailleur regen_candidates retrouve son instance (non sauvegardee). */
  if (this._activeWorker != null && this._activeWorker.kind == "regen_candidates") {
    this._activeWorker.ai <- this;
  }

  /* C80 tranche 2 : au rechargement, un travailleur "town_growth" reprend à la ville suivante
   * en sautant les villes devenues invalides. */
  if (this._activeWorker != null && this._activeWorker.kind == "town_growth") {
    this._activeWorker.ai <- this;
    if ("state" in this._activeWorker && this._activeWorker.state != null) {
      local s = this._activeWorker.state;
      if (!("cursorTownIndex" in s)) s.cursorTownIndex <- 0;
      if (!("servedTownsList" in s) || s.servedTownsList == null) {
        this._activeWorker = null;
      } else {
        while (s.cursorTownIndex < s.servedTownsList.len() && !AITown.IsValidTown(s.servedTownsList[s.cursorTownIndex])) {
          s.cursorTownIndex++;
        }
        if (s.cursorTownIndex >= s.servedTownsList.len()) {
          this._activeWorker = null;
        }
      }
    } else {
      this._activeWorker = null;
    }
  }

  this._c41RailSignalLines = this._filterPersistedRailRepairQueue(this._c41RailSignalLines);
  this._c41RailJunctionLines = this._filterPersistedRailRepairQueue(this._c41RailJunctionLines);
  this._rearmPersistedRailRepairTasks();

  /* V88 : Réconciliation d'une chaine industrielle en cours */
  if (this._activeGoodsChain != null) {
    local validChain = true;
    if (!AIIndustry.IsValidIndustry(this._activeGoodsChain.factoryId)) validChain = false;
    if (!AITown.IsValidTown(this._activeGoodsChain.townId)) validChain = false;
    if (this._activeGoodsChain.step == 2) {
      local inputLineFound = false;
      foreach (line in this._lines) {
        if (line.lineId == this._activeGoodsChain.inputLineId) {
          inputLineFound = true;
          break;
        }
      }
      if (!inputLineFound) validChain = false;
      if (!AIStation.IsValidStation(this._activeGoodsChain.factoryStationId)) validChain = false;
    }
    if (!validChain) {
      this._activeGoodsChain = null;
    } else if (this._activeGoodsChain.goodsCandidate != null && this._activeGoodsChain.goodsCandidate.loco == null && this._catalog != null) {
      if (this._activeGoodsChain.goodsCandidate.cargo in this._catalog.bestLocoByCargo) {
        this._activeGoodsChain.goodsCandidate.loco = this._catalog.bestLocoByCargo[this._activeGoodsChain.goodsCandidate.cargo];
      }
    }
  }

  this._purgeUnprofitableStreaks();
  if (this._vehiclesToRetire != null) {
    local staleRetireTickets = [];
    foreach (vehicle, ignored in this._vehiclesToRetire) {
      if (!AIVehicle.IsValidVehicle(vehicle)) staleRetireTickets.append(vehicle);
    }
    foreach (vehicle in staleRetireTickets) {
      if (vehicle in this._vehiclesToRetire) delete this._vehiclesToRetire[vehicle];
    }
  }
  if (C76_REGEN_TARGETED) {
    this._c76ForceReloadRegen = true;
  }
  /* Sans sonde : cette unique preuve doit toujours accompagner un rechargement, jamais une partie neuve. */
  OpexDecide("LOAD_RECONCILE", "saved=" + saved + " kept=" + kept + " dropped=" + dropped
             + " vehicles_purged=" + purgedVehicles
             + " rail_expansion_restored=" + railExpansion.restored
             + " rail_expansion_completed=" + railExpansion.completed
             + " rail_expansion_dropped=" + railExpansion.dropped
             + " rail_expansion_promoted=" + railExpansion.promoted
             + " rail_expansion_pending_recovered=" + railExpansion.pending_recovered
             + " rail_expansion_ambiguous_aborted=" + railExpansion.ambiguous_aborted
             + " rail_search_dropped=" + droppedRailSearch
             + " goods_chain=" + (this._activeGoodsChain != null ? this._activeGoodsChain.step : 0)
             + " rail_signal_queue=" + this._c41RailSignalLines.len()
             + " rail_junction_queue=" + this._c41RailJunctionLines.len());
}
