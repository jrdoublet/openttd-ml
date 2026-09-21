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

function OpexCopyBoolTable(source)
{
  local out = {};
  if (source == null) return out;
  foreach (key, val in source) out.rawset(key, val ? true : false);
  return out;
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

function OpexAI::Save()
{
  local abandoned = {};
  if (this._abandonedPairs != null) {
    foreach (key, val in this._abandonedPairs) abandoned[key] <- val;
  }
  /* A 0, conserver exactement le format historique : la charge complete est experimentale et
   * le serialiseur execute Save() sous budget d'opcodes. */
  if (!SAVE_FULL_STATE) return {
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

  local taskDue = {};
  if (this._taskQueue != null) {
    foreach (task in this._taskQueue) taskDue[task.name] <- task.dueCycle;
  }
  /* Les lignes sont normalement donnees telles quelles au serialiseur. Certains modeles
   * economiques (surtout air) laissent toutefois des flottants dans des metriques predites,
   * type que le format de sauvegarde OpenTTD refuse. Une projection superficielle n'est faite
   * que dans ce cas : les champs scalarises restants sont tous serialisables; les tableaux
   * (VehicleID) et tables des lignes actuelles ne contiennent que des entiers/booleens/null. */
  local saveLines = this._lines;
  local projectedLines = null;
  if (this._lines != null) {
    for (local i = 0; i < this._lines.len(); i++) {
      local line = this._lines[i];
      local needsProjection = line != null && typeof line == "table";
      if (needsProjection) {
        needsProjection = false;
        foreach (key, val in line) {
          local valType = typeof val;
          if (valType != "integer" && valType != "string" && valType != "bool" &&
              valType != "null" && valType != "array" && valType != "table") {
            needsProjection = true;
            break;
          }
        }
      }
      if (needsProjection) {
        if (projectedLines == null) {
          projectedLines = [];
          for (local prior = 0; prior < i; prior++) projectedLines.append(this._lines[prior]);
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
      } else if (projectedLines != null) {
        projectedLines.append(line);
      }
    }
  }
  if (projectedLines != null) saveLines = projectedLines;
  return {
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
    lines = saveLines,
    abandonCounts = this._abandonCounts,
    lastRepayMonth = this._lastRepayMonth,
    taskCycle = this._taskCycle,
    taskCursor = this._taskCursor,
    vehiclesToScrap = this._vehiclesToScrap,
    vehiclesToRetire = this._vehiclesToRetire,
    unprofitableStreaks = this._unprofitableStreaks,
    activeSubsidies = this._activeSubsidies,
    taskDue = taskDue,
    railExpansion = OpexSaveRailExpansion(this._railExpansion),
    railSearchPending = this._railSearch != null,
    dynamicBatchPending = this._dynamicBatch != null,
    c41RailSignalLines = OpexCopyBoolTable(this._c41RailSignalLines),
    c41RailJunctionLines = OpexCopyBoolTable(this._c41RailJunctionLines),
    stateVersion = 2,
  };
}
function OpexAI::Load(version, data)
{
  this._loadedFromSave = true;
  if (data == null) return;
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
  if ("vehiclesToScrap" in data && data.vehiclesToScrap != null) this._vehiclesToScrap = data.vehiclesToScrap;
  if ("vehiclesToRetire" in data && data.vehiclesToRetire != null) this._vehiclesToRetire = data.vehiclesToRetire;
  if ("unprofitableStreaks" in data && data.unprofitableStreaks != null) this._unprofitableStreaks = data.unprofitableStreaks;
  if ("activeSubsidies" in data && data.activeSubsidies != null) this._activeSubsidies = data.activeSubsidies;
  /* 11.6/11.7 : aucune lecture du monde ici. Les validations VehicleID/LineID attendent
   * _reconcileAfterLoad(), appelé depuis Start() après OpexLoadSettings(). Les sauvegardes
   * stateVersion=1 n'ont simplement pas ces champs et gardent les valeurs constructeur. */
  if ("railExpansion" in data) this._railExpansion = OpexLoadRailExpansion(data.railExpansion);
  this._reloadDroppedRailSearch = ("railSearchPending" in data) && data.railSearchPending;
  this._reloadDroppedDynamicBatch = ("dynamicBatchPending" in data) && data.dynamicBatchPending;
  if ("c41RailSignalLines" in data && data.c41RailSignalLines != null) {
    this._c41RailSignalLines = OpexCopyBoolTable(data.c41RailSignalLines);
  }
  if ("c41RailJunctionLines" in data && data.c41RailJunctionLines != null) {
    this._c41RailJunctionLines = OpexCopyBoolTable(data.c41RailJunctionLines);
  }
  /* Cle par nom : l'ordre de la file peut evoluer entre deux versions de l'IA. */
  if ("taskDue" in data && data.taskDue != null && this._taskQueue != null) {
    foreach (task in this._taskQueue) {
      if (task.name in data.taskDue) task.dueCycle = data.taskDue[task.name];
    }
  }
}
/* Load tourne trop tot et sous DisableDoCommandScope : la verification du monde est donc faite
 * ici, apres les reglages. Les stationA/stationB sont des TUILES, jamais des StationID. */
function OpexAI::_reconcileAfterLoad()
{
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

  local railExpansion = this._reconcileRailExpansionAfterLoad();

  /* _railSearch contient un pathfinder/segmented search vivant et _dynamicBatch depend de
   * _projects, qui n'est pas persiste. On ne fabrique pas de pseudo-serialisation de ces objets :
   * si Save() les a vus actifs, abandon explicite puis reconstruction immediate du portefeuille. */
  local droppedRailSearch = this._reloadDroppedRailSearch ? 1 : 0;
  local droppedDynamicBatch = this._reloadDroppedDynamicBatch ? 1 : 0;
  if (this._reloadDroppedRailSearch || this._reloadDroppedDynamicBatch) {
    this._railSearch = null;
    this._dynamicBatch = null;
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
  this._reloadDroppedDynamicBatch = false;

  this._c41RailSignalLines = this._filterPersistedRailRepairQueue(this._c41RailSignalLines);
  this._c41RailJunctionLines = this._filterPersistedRailRepairQueue(this._c41RailJunctionLines);
  this._rearmPersistedRailRepairTasks();

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
  if (this._vehiclesToScrap != null) {
    local staleScrapTickets = [];
    foreach (vehicle, ignored in this._vehiclesToScrap) {
      if (!AIVehicle.IsValidVehicle(vehicle)) staleScrapTickets.append(vehicle);
    }
    foreach (vehicle in staleScrapTickets) {
      if (vehicle in this._vehiclesToScrap) delete this._vehiclesToScrap[vehicle];
    }
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
             + " dynamic_batch_dropped=" + droppedDynamicBatch
             + " rail_signal_queue=" + this._c41RailSignalLines.len()
             + " rail_junction_queue=" + this._c41RailJunctionLines.len());
}
