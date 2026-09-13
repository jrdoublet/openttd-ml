/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
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
    waterSiteCatalog = this._waterSiteCatalog,
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
    waterSiteCatalog = this._waterSiteCatalog,
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
    stateVersion = 1,
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
  if ("waterSiteCatalog" in data && data.waterSiteCatalog != null &&
      ("towns" in data.waterSiteCatalog)) {
    this._waterSiteCatalog = data.waterSiteCatalog;
  }
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
  OpexDecide("LOAD_RECONCILE", "saved=" + saved + " kept=" + kept + " dropped=" + dropped + " vehicles_purged=" + purgedVehicles);
}
