/* RLW-04 : enumeration shadow de la SEULE fenetre initiale 224..288.
 * Ne jamais appeler OpexMakeCandidate / OpexV276Publish ni toucher _projects.
 * Chaque source est parcourue avec un curseur reprenable, rotation par cargo
 * et quota explicite de destinations pour les grandes cartes. Le stock est
 * une trace de paires, PAS une liste de candidats admissibles ou financables.
 * RLW-05 gerera les anneaux, invalidations et l'evaluation economique. */

const RLW04_MIN = 224;
const RLW04_MAX = 288;
/* Quota sur les destinations effectivement dans la bande, par source.
 * L'ancienne limite de 128 s'appliquait AVANT le filtre geometrique. */
const RLW04_SOURCE_DEST_CAP = 128;
const RLW04_CELL = 128;
const RLW04_INDEX_BATCH = 4;
const RLW04_SCAN_BATCH = 2;
const RLW04_POOL_CAP = 32;
const RLW04_PAIRS_PER_SLICE = 24;
const RLW04_OPS_BUDGET = 1800;
/* La boucle principale appelle RLW04 apres le travail RAIL. Un appel peut
 * utiliser plusieurs tranches, chacune avec SON propre plafond de 1800. */
const RLW04_OPS_RESERVE = 2150;
const RLW04_MAX_SLICES_CALL = 5;
/* Admission AVANT le prochain travail. Les mesures comprennent aussi le
 * parcours du curseur et l'epilogue ; le premier pas reste conservateur. */
const RLW04_WORK_FLOOR = 650;
const RLW04_SLICE_TAIL = 300;

function OpexRLW04Init(catalog)
{
  local units = [];
  if (catalog.paxCargo >= 0 && catalog.towns != null
      && catalog.locoByCargoWagons != null
      && (catalog.paxCargo in catalog.locoByCargoWagons)) {
    units.append({ family = "pax", cargo = catalog.paxCargo,
        a = 0, checkedSource = 0, done = false, sourceKey = -1,
        cells = {}, indexed = 0, indexReady = false,
        scanX = -1, scanY = -1, minX = 0, maxX = 0, minY = 0, maxY = 0,
        cellOffset = 0, sourceTile = -1, sourceX = 0, sourceY = 0,
        invalidSources = 0,
        scanned = 0, visited = 0, within = 0, low201 = 0, kept = 0,
        sourceCount = catalog.towns.len(), destCount = catalog.towns.len() });
  }
  if (catalog.producers != null && catalog.industries != null) {
    local cargos = [];
    foreach (cargo, sources in catalog.producers) {
      if (cargo == catalog.paxCargo || sources == null || sources.len() == 0) continue;
      if (catalog.locoByCargoWagons == null || !(cargo in catalog.locoByCargoWagons)) continue;
      local nIndustry = (cargo in catalog.acceptors) ? catalog.acceptors[cargo].len() : 0;
      local nTown = (cargo in catalog.townAcceptors) ? catalog.townAcceptors[cargo].len() : 0;
      if (nIndustry + nTown == 0) continue;
      cargos.append(cargo);
    }
    /* Tri de quelques IDs de cargo uniquement. Aucune AIList de paires ni sort global. */
    cargos.sort();
    foreach (cargo in cargos) {
      local nIndustry = (cargo in catalog.acceptors) ? catalog.acceptors[cargo].len() : 0;
      local nTown = (cargo in catalog.townAcceptors) ? catalog.townAcceptors[cargo].len() : 0;
      units.append({ family = "freight", cargo = cargo,
          a = 0, checkedSource = 0, done = false, sourceKey = -1,
          cells = {}, indexed = 0, indexReady = false,
          scanX = -1, scanY = -1, minX = 0, maxX = 0, minY = 0, maxY = 0,
          cellOffset = 0, sourceTile = -1, sourceX = 0, sourceY = 0,
          invalidSources = 0,
          scanned = 0, visited = 0, within = 0, low201 = 0, kept = 0,
          sourceCount = catalog.producers[cargo].len(), destCount = nIndustry + nTown });
    }
  }
  return { units = units, cursor = 0, completed = false,
      gridWidth = (AIMap.GetMapSizeX() + RLW04_CELL - 1) / RLW04_CELL,
      gridHeight = (AIMap.GetMapSizeY() + RLW04_CELL - 1) / RLW04_CELL,
      towns = catalog.towns, industries = catalog.industries,
      producers = catalog.producers, acceptors = catalog.acceptors,
      townAcceptors = catalog.townAcceptors,
      pool = { pax = [], freight = [] },
      pendingUnits = units.len(), refreshes = 0, snapshotEpoch = 0,
      observedTowns = catalog.towns, observedIndustries = catalog.industries,
      observedProducers = catalog.producers, observedAcceptors = catalog.acceptors,
      observedTownAcceptors = catalog.townAcceptors,
      totalSlices = 0, maxOps = 0, overruns = 0, totalOps = 0,
      totalFullOps = 0, totalWorkOps = 0, totalTailOps = 0,
      maxWorkOps = 0, maxTailOps = 0, initOps = 0,
      logOps = 0, maxLogOps = 0, maxEnumLogOps = 0, totalEnumLogOps = 0,
      maxFullOps = 0, invocations = 0, skippedReserve = 0,
      multiSliceCalls = 0, extraSlices = 0,
      maxRefreshOps = 0, totalRefreshOps = 0,
      priorityCursor = -1, prioritySteps = 0, fairSteps = 0,
      indexSteps = 0, indexEntries = 0, scanSteps = 0,
      cellSkips = 0, geometricSkips = 0, sourcesAdvanced = 0,
      totalIndexOps = 0, totalScanOps = 0,
      progressCursor = 0,
      pendingUnitLogs = [],
      totalPairs = 0, totalVisited = 0, totalWithin = 0, totalLow201 = 0,
      sampleCursor = { pax = 0, freight = 0 } };
}

function OpexRLW04AdvanceSource(u)
{
  u.a++;
  u.scanX = -1;
  u.scanY = -1;
  u.cellOffset = 0;
  u.sourceTile = -1;
  u.sourceKey = -1;
  u.checkedSource = 0;
  if (u.a >= u.sourceCount) u.done = true;
}

/* Choix de cadence seulement : la petite unite restante recoit trois pas
 * sur quatre. Le quatrieme reste un passage equitable entre toutes les
 * unites : aucune source/cargo valide n'est definitivement affamee. */
function OpexRLW04ChoosePriority(s)
{
  local best = -1;
  local bestCost = -1;
  for (local i = 0; i < s.units.len(); i++) {
    local u = s.units[i];
    if (u.done) continue;
    local remainingSources = u.sourceCount - u.a;
    local cost = remainingSources * (u.indexReady ? 1 : 2) + (u.destCount - u.indexed);
    if (best < 0 || cost < bestCost) { best = i; bestCost = cost; }
  }
  return best;
}

/* Acces au snapshot de puits, sans reconstruction au refresh. */
function OpexRLW04Sink(s, u, b)
{
  if (u.family == "pax") return s.towns[b];
  local industrySinks = (u.cargo in s.acceptors) ? s.acceptors[u.cargo] : [];
  if (b < industrySinks.len()) return s.industries[industrySinks[b]];
  return s.townAcceptors[u.cargo][b - industrySinks.len()];
}

/* Indexation repartie sur des pas mesures, sans tri global/AIList. Chaque
 * cellule stocke uniquement des coordonnees et l'index du puits snapshot. */
function OpexRLW04IndexStep(s, u)
{
  local end = u.indexed + RLW04_INDEX_BATCH;
  if (end > u.destCount) end = u.destCount;
  while (u.indexed < end) {
    local b = u.indexed++;
    local dst = OpexRLW04Sink(s, u, b);
    if (dst == null || !AIMap.IsValidTile(dst.tile)) continue;
    local x = AIMap.GetTileX(dst.tile);
    local y = AIMap.GetTileY(dst.tile);
    local key = x / RLW04_CELL + (y / RLW04_CELL) * s.gridWidth;
    if (!(key in u.cells)) u.cells[key] <- [];
    u.cells[key].append({ b = b, x = x, y = y });
    s.indexEntries++;
  }
  if (u.indexed >= u.destCount) u.indexReady = true;
  s.indexSteps++;
  return true;
}

/* Fixe la fenetre rectangulaire de cellules autour d'une source, une fois.
 * Le Manhattan exact reste controle avant les appels API de validite. */
function OpexRLW04StartSource(s, u)
{
  local src = u.family == "pax" ? s.towns[u.a]
      : s.industries[s.producers[u.cargo][u.a]];
  if (src == null || !AIMap.IsValidTile(src.tile)) return false;
  if (u.sourceKey >= 0 && u.sourceKey != src.id) return false;
  u.sourceKey = src.id;
  if (u.family == "pax") {
    if (!AITown.IsValidTown(src.id)) return false;
  } else if (!AIIndustry.IsValidIndustry(src.id) || !AICargo.IsValidCargo(u.cargo)) return false;
  u.sourceTile = src.tile;
  u.sourceX = AIMap.GetTileX(src.tile);
  u.sourceY = AIMap.GetTileY(src.tile);
  u.minX = (u.sourceX > RLW04_MAX ? u.sourceX - RLW04_MAX : 0) / RLW04_CELL;
  u.minY = (u.sourceY > RLW04_MAX ? u.sourceY - RLW04_MAX : 0) / RLW04_CELL;
  local maxX = u.sourceX + RLW04_MAX;
  local maxY = u.sourceY + RLW04_MAX;
  u.maxX = (maxX / RLW04_CELL) < s.gridWidth ? (maxX / RLW04_CELL) : s.gridWidth - 1;
  u.maxY = (maxY / RLW04_CELL) < s.gridHeight ? (maxY / RLW04_CELL) : s.gridHeight - 1;
  u.scanX = u.minX;
  u.scanY = u.minY;
  u.cellOffset = 0;
  return true;
}

/* Avance la cellule dans la rectangle source, et elimine ses sous-regions
 * dont la distance minimale depasse 288 ou la maximale est inferieure a 224. */
function OpexRLW04NextCell(s, u)
{
  u.scanX++;
  if (u.scanX > u.maxX) { u.scanX = u.minX; u.scanY++; }
  u.cellOffset = 0;
}

/* Un pas traite au plus deux destinations spatiales. Aucune API de
 * validite ou Manhattan n'est appelee hors de l'anneau. */
function OpexRLW04Pair(s, u)
{
  if (u.done) return false;
  if (u.a >= u.sourceCount || u.destCount == 0) { u.done = true; return false; }
  if (!u.indexReady) return OpexRLW04IndexStep(s, u);
  if (u.scanX < 0) {
    if (!OpexRLW04StartSource(s, u)) {
      u.invalidSources++;
      OpexRLW04AdvanceSource(u);
    }
    return true;
  }
  local checked = 0;
  /* On saute autant de cellules vides que necessaire : 25 maximum pour
   * CELL=128, bande 288. Un seul lot de puits reels par etape. */
  /* Le premier pic au-dessus de 850 sur grande carte reduit le lot suivant.
   * Le pic historique ne doit pas geler tout l'ordonnanceur. */
  local scanCap = s.maxWorkOps >= 850 ? 1 : RLW04_SCAN_BATCH;
  while (u.scanY <= u.maxY && checked < scanCap) {
    local key = u.scanX + u.scanY * s.gridWidth;
    if (!(key in u.cells)) { s.cellSkips++; OpexRLW04NextCell(s, u); continue; }
    local bucket = u.cells[key];
    if (u.cellOffset >= bucket.len()) { OpexRLW04NextCell(s, u); continue; }
    local rec = bucket[u.cellOffset++];
    checked++;
    if (u.family == "pax" && rec.b <= u.a) continue;
    local dist = abs(rec.x - u.sourceX) + abs(rec.y - u.sourceY);
    if (dist < RLW04_MIN || dist > RLW04_MAX) { s.geometricSkips++; continue; }
    if (u.checkedSource >= RLW04_SOURCE_DEST_CAP) { u.scanY = u.maxY + 1; break; }
    u.checkedSource++;
    u.visited++;
    s.totalVisited++;
    local dst = OpexRLW04Sink(s, u, rec.b);
    if (dst == null || dst.tile == u.sourceTile || !AIMap.IsValidTile(dst.tile)) continue;
    if (u.family == "pax") {
      if (!AITown.IsValidTown(dst.id)) continue;
    } else {
      local nIndustry = (u.cargo in s.acceptors) ? s.acceptors[u.cargo].len() : 0;
      if (rec.b < nIndustry && !AIIndustry.IsValidIndustry(dst.id)) continue;
      if (rec.b >= nIndustry && !AITown.IsValidTown(dst.id)) continue;
    }
    u.scanned++;
    s.totalPairs++;
    u.within++;
    s.totalWithin++;
    local family = u.family;
    local stock = s.pool[family];
    local pair = { family = family, cargo = u.cargo,
        src = u.sourceTile, dst = dst.tile, srcId = u.sourceKey, dstId = dst.id,
        distance = dist, sourceIndex = u.a };
    if (stock.len() < RLW04_POOL_CAP) stock.append(pair);
    else {
      stock[s.sampleCursor[family]] = pair;
      s.sampleCursor[family] = (s.sampleCursor[family] + 1) % RLW04_POOL_CAP;
    }
    u.kept++;
  }
  s.scanSteps++;
  if (u.scanY > u.maxY) { OpexRLW04AdvanceSource(u); s.sourcesAdvanced++; }
  return true;
}

function OpexRLW04Log(s, phase, ops, ticks)
{
  if (!DECISION_LOG) return;
  /* Une unite differente a chaque checkpoint : les dix curseurs sont
   * observables sans journaliser des milliers de sources individuellement. */
  local u = s.units.len() > 0 ? s.units[s.progressCursor] : null;
  local progress = u == null ? "" :
      " unit_index=" + s.progressCursor + " unit_family=" + u.family
      + " unit_cargo=" + u.cargo + " unit_source=" + u.a
      + " unit_sources=" + u.sourceCount + " unit_visited=" + u.visited
      + " unit_done=" + (u.done ? 1 : 0);
  OpexDecide("RLW04_ENUM", "phase=" + phase
      + " slices=" + s.totalSlices + " unit=" + s.cursor
      + " units=" + s.units.len() + " visited=" + s.totalVisited
      + " scanned=" + s.totalPairs
      + " band224_288=" + s.totalWithin + " outside201_223=" + s.totalLow201
      + " stock_pax=" + s.pool.pax.len() + " stock_freight=" + s.pool.freight.len()
      + " ops=" + ops + " max_ops=" + s.maxOps + " ticks=" + ticks
      + " overrun=" + s.overruns + " budget=" + RLW04_OPS_BUDGET
      + " refreshes=" + s.refreshes + " pending=" + s.pendingUnits
      + " max_work_ops=" + s.maxWorkOps + " max_tail_ops=" + s.maxTailOps
      + " init_ops=" + s.initOps + " max_log_ops=" + s.maxLogOps
      + " max_enum_log_ops=" + s.maxEnumLogOps
      + " max_full_ops=" + s.maxFullOps
      + " max_refresh_ops=" + s.maxRefreshOps
      + " total_refresh_ops=" + s.totalRefreshOps
      + " calls=" + s.invocations + " low_reserve=" + s.skippedReserve
      + " multislice=" + s.multiSliceCalls + " extra_slices=" + s.extraSlices
      + " priority_steps=" + s.prioritySteps + " fair_steps=" + s.fairSteps
      + " priority_unit=" + s.priorityCursor
      + " total_full_ops=" + s.totalFullOps + " total_work_ops=" + s.totalWorkOps
      + " total_tail_ops=" + s.totalTailOps + " total_enum_log_ops=" + s.totalEnumLogOps
      + " total_unit_log_ops=" + s.logOps
      + " index_steps=" + s.indexSteps + " indexed=" + s.indexEntries
      + " scan_steps=" + s.scanSteps + " sources_advanced=" + s.sourcesAdvanced
      + " cell_skips=" + s.cellSkips + " geo_skips=" + s.geometricSkips
      + " index_ops=" + s.totalIndexOps + " scan_ops=" + s.totalScanOps
      + progress);
  if (u != null) s.progressCursor = (s.progressCursor + 1) % s.units.len();
}

function OpexRLW04LogUnit(u)
{
  if (!DECISION_LOG) return;
  local cargoLabel = AICargo.IsValidCargo(u.cargo) ? AICargo.GetCargoLabel(u.cargo) : ("" + u.cargo);
  OpexDecide("RLW04_UNIT", "family=" + u.family + " cargo=" + cargoLabel
      + " sources=" + u.sourceCount + " sinks=" + u.destCount
      + " cell=" + RLW04_CELL
      + " checked=" + u.scanned + " visited=" + u.visited
      + " indexed=" + u.indexed
      + " band224_288=" + u.within
      + " outside201_223=" + u.low201 + " stocked_occurrences=" + u.kept
      + " invalid_sources=" + u.invalidSources);
}

function OpexAI::_rlw04Step()
{
  if (!RLW04_SHADOW || !MODE_RAIL || this._catalog == null
      || this._catalog.bounds == null) return;
  if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) return;
  if (OPEX_START_YEAR < 0 || AIDate.GetYear(AIDate.GetCurrentDate()) < OPEX_START_YEAR + 2) return;
  if (this._rlw04State == null) {
    if (AIController.GetOpsTillSuspend() < RLW04_OPS_RESERVE) return;
    local initMark = OpexOpsMeasureBegin();
    this._rlw04State = OpexRLW04Init(this._catalog);
    this._rlw04State.initOps = OpexOpsMeasureEnd(initMark);
    /* L'initialisation est un evenement unique, mesure separement et
     * jamais suivi d'un balayage dans le meme appel. */
    return;
  }
  local s = this._rlw04State;
  if (s.completed) {
    /* Plusieurs unites peuvent finir dans une tranche. Eviter de perdre les
     * derniers journaux apres le dernier checkpoint de fin de passe. */
    if (DECISION_LOG && s.pendingUnitLogs.len() > 0
        && AIController.GetOpsTillSuspend() >= RLW04_OPS_RESERVE) {
      OpexRLW04LogUnit(s.pendingUnitLogs[0]);
      s.pendingUnitLogs.remove(0);
    }
    return;
  }
  s.invocations++;
  if (AIController.GetOpsTillSuspend() < RLW04_OPS_RESERVE) {
    s.skippedReserve++;
    return;
  }
  /* Une passe vise les IDs sources/cargos de son snapshot initial. Les
   * nouvelles collections ne re-indexent jamais une source deja avancee.
   * Les sources detruites sont seules ignorees dans OpexRLW04Pair ; aucune
   * remise a zero globale sur PO01C/catalogue reactif. */
  if (s.observedTowns != this._catalog.towns || s.observedIndustries != this._catalog.industries
      || s.observedProducers != this._catalog.producers || s.observedAcceptors != this._catalog.acceptors
      || s.observedTownAcceptors != this._catalog.townAcceptors) {
    local refreshMark = OpexOpsMeasureBegin();
    s.observedTowns = this._catalog.towns;
    s.observedIndustries = this._catalog.industries;
    s.observedProducers = this._catalog.producers;
    s.observedAcceptors = this._catalog.acceptors;
    s.observedTownAcceptors = this._catalog.townAcceptors;
    s.refreshes++;
    local refreshUsed = OpexOpsMeasureEnd(refreshMark);
    s.totalRefreshOps += refreshUsed;
    if (refreshUsed > s.maxRefreshOps) s.maxRefreshOps = refreshUsed;
  }
  local slicesThisCall = 0;
  while (slicesThisCall < RLW04_MAX_SLICES_CALL && !s.completed
      && AIController.GetOpsTillSuspend() >= RLW04_OPS_RESERVE) {
    local mark = OpexOpsMeasureBegin();
    local processed = 0;
    while (processed < RLW04_PAIRS_PER_SLICE && s.pendingUnits > 0
        && AIController.GetTick() == mark.tick) {
      local usedBefore = OpexOpsMeasureEnd(mark);
      /* Le pic mesure couvre un pas complet. Au-dela de 850, les pas de scan
       * se reduisent a un puits ; un pic ancien a deux puits ne doit jamais
       * provoquer de starvation permanente de l'admission. */
      local estimated = (s.maxWorkOps > 850 ? 850 : s.maxWorkOps) + 140;
      if (estimated < RLW04_WORK_FLOOR) estimated = RLW04_WORK_FLOOR;
      /* La reserve couvre le prochain pas ET la sortie/journalisation.
       * Chaque tour de cette boucle externe repart d'un nouveau mark. */
      if (usedBefore + estimated + RLW04_SLICE_TAIL > RLW04_OPS_BUDGET) break;
      if (AIController.GetOpsTillSuspend() < RLW04_OPS_RESERVE - RLW04_OPS_BUDGET
          + estimated + RLW04_SLICE_TAIL) break;
      if (s.priorityCursor < 0 || s.units[s.priorityCursor].done)
        s.priorityCursor = OpexRLW04ChoosePriority(s);
      local usePriority = s.priorityCursor >= 0 && s.totalVisited % 4 != 0;
      local chosenIndex = usePriority ? s.priorityCursor : s.cursor;
      local u = s.units[chosenIndex];
      if (usePriority) s.prioritySteps++;
      else s.fairSteps++;
      if (!u.done) {
        local workMark = OpexOpsMeasureBegin();
        local wasIndex = !u.indexReady;
        if (OpexRLW04Pair(s, u)) processed++;
        local workOps = OpexOpsMeasureEnd(workMark);
        if (workOps > s.maxWorkOps) s.maxWorkOps = workOps;
        s.totalWorkOps += workOps;
        if (wasIndex) s.totalIndexOps += workOps;
        else s.totalScanOps += workOps;
        if (u.done) {
          s.pendingUnits--;
          s.pendingUnitLogs.append(u);
        }
      }
      s.cursor++;
      if (s.cursor >= s.units.len()) s.cursor = 0;
    }
    if (processed == 0 && s.pendingUnits > 0) break;
    local beforeTail = OpexOpsMeasureEnd(mark);
    if (s.pendingUnits == 0) s.completed = true;
    local used = OpexOpsMeasureEnd(mark);
    local tailOps = used - beforeTail;
    if (tailOps > s.maxTailOps) s.maxTailOps = tailOps;
    s.totalTailOps += tailOps;
    s.totalSlices++;
    s.totalOps += used;
    if (used > s.maxOps) s.maxOps = used;
    slicesThisCall++;
    if (slicesThisCall > 1) s.extraSlices++;
    /* Journaux amortis, au plus une fin d'unite par tranche. L'epilogue
     * reserve 300 opcodes pour un seul message ; les suivants attendent. */
    if (DECISION_LOG && s.pendingUnitLogs.len() > 0
        && OpexOpsMeasureEnd(mark) + RLW04_SLICE_TAIL < RLW04_OPS_BUDGET) {
      local logMark = OpexOpsMeasureBegin();
      OpexRLW04LogUnit(s.pendingUnitLogs[0]);
      s.pendingUnitLogs.remove(0);
      local logUsed = OpexOpsMeasureEnd(logMark);
      s.logOps += logUsed;
      if (logUsed > s.maxLogOps) s.maxLogOps = logUsed;
    }
    /* Le log ENUM et le calcul partagent maintenant la meme mesure. */
    if (s.completed || s.totalSlices % 16 == 0) {
      local logMark = OpexOpsMeasureBegin();
      OpexRLW04Log(s, s.completed ? "done" : "slice", used,
          AIController.GetTick() - mark.tick);
      local enumOps = OpexOpsMeasureEnd(logMark);
      if (enumOps > s.maxEnumLogOps) s.maxEnumLogOps = enumOps;
      s.totalEnumLogOps += enumOps;
    }
    local fullOps = OpexOpsMeasureEnd(mark);
    s.totalFullOps += fullOps;
    if (fullOps > s.maxFullOps) s.maxFullOps = fullOps;
    if (fullOps > RLW04_OPS_BUDGET || AIController.GetTick() != mark.tick) {
      s.overruns++;
      /* Une fin de passe peut ne jamais avoir de checkpoint suivant. */
      if (s.completed) OpexRLW04Log(s, "budget_violation", fullOps, AIController.GetTick() - mark.tick);
    }
  }
  if (slicesThisCall > 1) s.multiSliceCalls++;
}
