/* OpexAI -- orchestrator.nut
 * C80 : Orchestrateur à double registre (intentions / exécution).
 * Tranche 0 : Socle architectural sans modification de la logique de jeu.
 *
 * Deux registres découplés :
 * 1. Registre des intentions :
 *    - File RÉACTIVE (haute priorité) : table d'intentions avec déduplication/coalescence par clé.
 *      En tranche 0 : aucun producteur (C76 étape 2 et C77 viendront l'alimenter).
 *    - File de FOND (périodique / maintenance) : enveloppe sans modification la file historique
 *      _taskQueue / _runNextTaskWithSlackLedger().
 * 2. Registre d'exécution :
 *    - Au plus un travailleur actif (_activeWorker = { kind, state }).
 *    - Fonctions libres de pas (step) et d'annulation (cancel) dispatchées par kind.
 *    - En tranche 0 : aucun travailleur réel enregistré (l'A* rail migre en tranche 1) ;
 *      fournit le travailleur test "noop" pour le selftest de démarrage.
 */

/* ============================================================================
 * 1. File RÉACTIVE (OpexReactiveQueue)
 * ============================================================================ */

class OpexReactiveQueue
{
  _items = null;  // table key -> { key, kind, payload, enqueuedDate, count }
  _order = null;  // tableau de clés dans l'ordre d'arrivée (FIFO)

  constructor()
  {
    this._items = {};
    this._order = [];
  }

  /* API enqueue(key, kind, payload) :
   * Si la clé existe déjà, fusionne en incrémentant count et mettant à jour le payload.
   * Sinon, insère en fin d'ordre d'arrivée avec count = 1. */
  function enqueue(key, kind, payload)
  {
    if (key in this._items) {
      local existing = this._items[key];
      existing.count++;
      if (payload != null) existing.payload = payload;
      return existing;
    }
    local item = {
      key = key,
      kind = kind,
      payload = payload,
      enqueuedDate = AIDate.GetCurrentDate(),
      count = 1
    };
    this._items.rawset(key, item);
    this._order.append(key);
    return item;
  }

  /* API pop() :
   * Dépile et renvoie l'intention la plus ancienne dans l'ordre d'arrivée.
   * Supprime l'entrée de la table des clés. */
  function pop()
  {
    if (this._order.len() == 0) return null;
    local key = this._order.remove(0);
    if (!(key in this._items)) return null;
    local item = this._items[key];
    delete this._items[key];
    return item;
  }

  function len()
  {
    return this._order.len();
  }

  function isEmpty()
  {
    return this._order.len() == 0;
  }

  function clear()
  {
    this._items = {};
    this._order = [];
  }

  function toArray()
  {
    local out = [];
    foreach (key in this._order) {
      if (key in this._items) {
        out.append(this._items[key]);
      }
    }
    return out;
  }

  function has(key)
  {
    return (key in this._items);
  }

  function get(key)
  {
    return (key in this._items) ? this._items[key] : null;
  }

  function getItems()
  {
    return this._items;
  }

  function restoreItem(key, kind, payload, enqueuedDate, count)
  {
    if (key in this._items) {
      local existing = this._items[key];
      existing.count += count;
      return existing;
    }
    local item = {
      key = key,
      kind = kind,
      payload = payload,
      enqueuedDate = enqueuedDate,
      count = count
    };
    this._items.rawset(key, item);
    this._order.append(key);
    return item;
  }
}

/* ============================================================================
 * 2. Registre d'EXÉCUTION et Travailleurs résumables
 * ============================================================================ */

/* Table de dispatch des travailleurs par kind. */
OPEX_WORKER_REGISTRY <- {};

function OpexRegisterWorker(kind, stepFn, cancelFn)
{
  OPEX_WORKER_REGISTRY.rawset(kind, {
    step = stepFn,
    cancel = cancelFn
  });
}

function OpexWorkerStep(worker, opsBudget, deadlineTick)
{
  if (worker == null || typeof worker != "table" || !("kind" in worker)) return "cancelled";
  local kind = worker.kind;
  if (!(kind in OPEX_WORKER_REGISTRY)) {
    AILog.Warning("C80: unknown worker kind: " + kind);
    return "cancelled";
  }
  return OPEX_WORKER_REGISTRY[kind].step(worker, opsBudget, deadlineTick);
}

function OpexWorkerCancel(worker)
{
  if (worker == null || typeof worker != "table" || !("kind" in worker)) return;
  local kind = worker.kind;
  if (kind in OPEX_WORKER_REGISTRY) {
    OPEX_WORKER_REGISTRY[kind].cancel(worker);
  }
}

/* Travailleur de test "noop" pour le selftest de tranche 0.
 * Se termine en 3 étapes :
 * - appel 1 -> "running"
 * - appel 2 -> "running"
 * - appel 3 -> "done"
 */
function OpexWorkerNoopStep(worker, opsBudget, deadlineTick)
{
  if (worker == null || !("state" in worker) || worker.state == null || typeof worker.state != "table") {
    return "cancelled";
  }
  local s = worker.state;
  if (!("stepCount" in s)) s.stepCount <- 0;
  if (!("targetSteps" in s)) s.targetSteps <- 3;
  s.stepCount++;
  if (s.stepCount >= s.targetSteps) {
    return "done";
  }
  return "running";
}

function OpexWorkerNoopCancel(worker)
{
  if (worker != null && ("state" in worker) && worker.state != null && typeof worker.state == "table") {
    worker.state.cancelled <- true;
  }
}

// Enregistrement du travailleur test noop
OpexRegisterWorker("noop", OpexWorkerNoopStep, OpexWorkerNoopCancel);

/* Travailleur "rail_search" (Tranche 1 de C80) :
 * Son state référence la recherche existante (this._railSearch reste la source de vérité).
 * Step : avance d'une tranche via _advanceRailSearchSliceWithLedgers() (le même appel
 *        _continueRailSearch avec les mêmes ledgers C41.46/C39.6 qu'aujourd'hui).
 *        "done" quand la recherche quitte la phase "search" ou que this._railSearch devient null.
 * Cancel : même effet qu'un abandon actuel de recherche (réutilise le chemin existant,
 *          remet this._railSearch à null).
 */
function OpexWorkerRailSearchStep(worker, opsBudget, deadlineTick)
{
  if (worker == null || !("state" in worker) || worker.state == null || typeof worker.state != "table") {
    return "cancelled";
  }
  local ai = ("ai" in worker.state) ? worker.state.ai : null;
  if (ai == null || ai._railSearch == null) {
    return "done";
  }
  ai._advanceRailSearchSliceWithLedgers();
  if (ai._railSearch == null || ai._railSearch.phase != "search") {
    return "done";
  }
  return "running";
}

function OpexWorkerRailSearchCancel(worker)
{
  if (worker == null || !("state" in worker) || worker.state == null || typeof worker.state != "table") {
    return;
  }
  local ai = ("ai" in worker.state) ? worker.state.ai : null;
  if (ai != null) {
    ai._railSearch = null;
  }
  if ("search" in worker.state) {
    worker.state.search = null;
  }
}

// Enregistrement du travailleur rail_search
OpexRegisterWorker("rail_search", OpexWorkerRailSearchStep, OpexWorkerRailSearchCancel);

/* Travailleur "town_growth" (Tranche 2 de C80) :
 * Découpe la croissance urbaine en 1 ville par tranche.
 * Son state contient uniquement des entiers et tableaux d'entiers :
 *   { cursorTownIndex, servedTownsList, year }
 * Step : traite 1 seule ville éligible.
 *        "done" si une ligne a été construite ou si toutes les villes ont été examinées.
 *        "running" s'il reste des villes à examiner.
 * Cancel : annulation propre.
 */
function OpexWorkerTownGrowthStep(worker, opsBudget, deadlineTick)
{
  if (worker == null || !("state" in worker) || worker.state == null || typeof worker.state != "table") {
    return "cancelled";
  }
  local s = worker.state;
  if (!("cursorTownIndex" in s)) s.cursorTownIndex <- 0;
  if (!("servedTownsList" in s) || s.servedTownsList == null) return "done";
  local towns = s.servedTownsList;

  local isMock = ("mockResults" in s && s.mockResults != null);
  if (!isMock) {
    while (s.cursorTownIndex < towns.len() && !AITown.IsValidTown(towns[s.cursorTownIndex])) {
      s.cursorTownIndex++;
    }
  }
  if (s.cursorTownIndex >= towns.len()) return "done";

  local townId = towns[s.cursorTownIndex];
  s.cursorTownIndex++;

  local built = false;
  if (isMock && (townId in s.mockResults)) {
    built = s.mockResults[townId];
  } else {
    local ai = ("ai" in worker) ? worker.ai : (("ai" in s) ? s.ai : null);
    if (ai == null) return "cancelled";
    local measureMark = C39_PASS_CLOCK_LEDGER ? OpexOpsMeasureBegin() : null;
    local year = ("year" in s) ? s.year : AIDate.GetYear(AIDate.GetCurrentDate());
    built = ai._tryTownGrowthCity(townId, year);
    if (measureMark != null) {
      local sliceOps = OpexOpsMeasureEnd(measureMark);
      ai._recordTownWorkerSlice(sliceOps, built ? 1 : 0);
    }
  }

  if (built) return "done";
  if (!isMock) {
    while (s.cursorTownIndex < towns.len() && !AITown.IsValidTown(towns[s.cursorTownIndex])) {
      s.cursorTownIndex++;
    }
  }
  if (s.cursorTownIndex >= towns.len()) return "done";
  return "running";
}

function OpexWorkerTownGrowthCancel(worker)
{
  if (worker != null && ("state" in worker) && worker.state != null && typeof worker.state == "table") {
    worker.state.cancelled <- true;
  }
}

// Enregistrement du travailleur town_growth
OpexRegisterWorker("town_growth", OpexWorkerTownGrowthStep, OpexWorkerTownGrowthCancel);

/* ============================================================================
 * 3. Intégration dans OpexAI (File de fond, boucle ordonnancée, selftest)
 * ============================================================================ */

/* File de FOND : enveloppe l'ordonnanceur existant sans en modifier l'ordre,
 * les dueCycle, le curseur ni les compteurs de file. */
function OpexAI::_runBackgroundQueue()
{
  return this._runNextTaskWithSlackLedger();
}

function OpexAI::_enqueueReactive(key, kind, payload)
{
  if (this._reactiveQueue == null) this._reactiveQueue = OpexReactiveQueue();
  return this._reactiveQueue.enqueue(key, kind, payload);
}

function OpexAI::_popReactive()
{
  if (this._reactiveQueue == null) return null;
  return this._reactiveQueue.pop();
}

function OpexAI::_hasReactiveIntentions()
{
  return this._reactiveQueue != null && !this._reactiveQueue.isEmpty();
}

function OpexAI::_clearReactiveQueue()
{
  if (this._reactiveQueue != null) this._reactiveQueue.clear();
}

function OpexAI::enqueue(key, kind, payload)
{
  return this._enqueueReactive(key, kind, payload);
}

function OpexAI::pop()
{
  return this._popReactive();
}

function OpexAI::_dispatchReactiveIntention(intention)
{
  if (intention == null) return false;
  if (intention.key == "regen" || intention.kind == "regen") {
    if (C76_REGEN_TARGETED) {
      local date = AIDate.GetCurrentDate();
      local year = AIDate.GetYear(date);
      this._c76DoFullRegen("reactive", year);
      return true;
    }
  }
  return true;
}

/* BOUCLE ORDONNANCÉE C80 TRANCHE 0 :
 * Appelée à la place de l'appel actuel à la file quand C80_DOUBLE_REGISTER est vrai.
 * (a) Événements : traités dans main.nut par this._processEvents() à chaque itération (inchangé).
 * (b) Une intention réactive si la file réactive n'est pas vide (en tranche 0 elle est toujours vide).
 * (c) Une tranche du travailleur actif s'il y en a un.
 * (d) Sinon la file de fond = l'appel EXISTANT (le même que sans le réglage,
 *     y compris la tranche A* rail actuelle).
 *
 * ANTI-FAMINE (Contrat 18_orchestrateur_double_registre.md §3.1.3) :
 * NE PAS introduire de constante N_max en tranche 0 (point ouvert du contrat §3.1.3,
 * décision utilisateur en attente). La file réactive n'ayant aucun producteur en
 * tranche 0, l'absence de N_max est sans impact immédiat et préserve l'arbitrage
 * futur sur la règle de partage (constante vs ratio mesuré).
 */
function OpexAI::_runOrchestratorTick()
{
  this._railWorkerSteppedThisTick = false;

  // (b) Intention réactive
  if (this._hasReactiveIntentions()) {
    local intention = this._popReactive();
    if (intention != null) {
      this._dispatchReactiveIntention(intention);
      return true;
    }
  }

  // (c) Tranche du travailleur actif s'il y en a un
  if (this._activeWorker != null) {
    if (this._activeWorker.kind == "rail_search") {
      /* Ordre d'aujourd'hui (_runNextTask) : l'extension rail avance AVANT la tranche A*. */
      if (this._railExpansion != null) this._continueRailExpansion();
      this._railWorkerSteppedThisTick = true;
      local opsBudget = AIController.GetOpsTillSuspend();
      local deadlineTick = AIController.GetTick() + BUILD_TICK_MARGIN;
      local outcome = OpexWorkerStep(this._activeWorker, opsBudget, deadlineTick);
      if (outcome == "done" || outcome == "cancelled") {
        this._activeWorker = null;
      }
      // ORDRE PRÉSERVÉ (Contrat C80 tranche 1 §3) :
      // Après la tranche du travailleur rail, on enchaîne avec la file de fond
      // dans le MÊME tick (pas de return true ici).
    } else if (this._activeWorker.kind == "town_growth") {
      local opsBudget = AIController.GetOpsTillSuspend();
      local deadlineTick = AIController.GetTick() + BUILD_TICK_MARGIN;
      local outcome = OpexWorkerStep(this._activeWorker, opsBudget, deadlineTick);
      if (outcome == "done" || outcome == "cancelled") {
        this._activeWorker = null;
      }
      // ORDRE PRÉSERVÉ (Contrat C80 tranche 2 §3) :
      // Comme rail_search, la tranche town_growth est jouée puis la file de fond
      // enchaîne dans le MÊME tick (pas de return true ici).
    } else {
      local opsBudget = AIController.GetOpsTillSuspend();
      local deadlineTick = AIController.GetTick() + BUILD_TICK_MARGIN;
      local outcome = OpexWorkerStep(this._activeWorker, opsBudget, deadlineTick);
      if (outcome == "done" || outcome == "cancelled") {
        this._activeWorker = null;
      }
      return true;
    }
  }

  // (d) Sinon file de fond = appel existant
  return this._runBackgroundQueue();
}

/* Selftest C80 tranche 0 :
 * Déclenché une seule fois au démarrage si C80_DOUBLE_REGISTER est vrai.
 * 1. Enfile deux intentions de même clé (vérifie la coalescence).
 * 2. Enregistre le travailleur "noop" qui se termine en 3 étapes, vérifie les transitions.
 * 3. Vide tout et vérifie qu'aucun état ne subsiste.
 * Journalise "C80 selftest ok" ou "C80 selftest FAIL <raison>" via AILog.Info.
 */
function OpexAI::_c80RunSelfTest()
{
  // 1. Enfiler deux intentions de même clé et vérifier la coalescence
  local testKey = "c80_selftest_key";
  local item1 = this._enqueueReactive(testKey, "noop", { step = 1 });
  if (item1 == null || item1.count != 1) {
    AILog.Info("C80 selftest FAIL initial enqueue failed");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local item2 = this._enqueueReactive(testKey, "noop", { step = 2 });
  if (item2 == null || item2.count != 2) {
    local gotCount = (item2 != null) ? item2.count : "null";
    AILog.Info("C80 selftest FAIL coalesce count expected 2, got " + gotCount);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  if (this._reactiveQueue.len() != 1) {
    AILog.Info("C80 selftest FAIL queue length expected 1, got " + this._reactiveQueue.len());
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  // 2. Enregistrer le travailleur "noop" et vérifier les 3 étapes
  local worker = {
    kind = "noop",
    state = {
      stepCount = 0,
      targetSteps = 3
    }
  };
  this._activeWorker = worker;

  local budgetOps = 10000;
  local deadlineTick = AIController.GetTick() + 100;

  local r1 = OpexWorkerStep(this._activeWorker, budgetOps, deadlineTick);
  if (r1 != "running") {
    AILog.Info("C80 selftest FAIL step 1 expected running, got " + r1);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local r2 = OpexWorkerStep(this._activeWorker, budgetOps, deadlineTick);
  if (r2 != "running") {
    AILog.Info("C80 selftest FAIL step 2 expected running, got " + r2);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local r3 = OpexWorkerStep(this._activeWorker, budgetOps, deadlineTick);
  if (r3 != "done") {
    AILog.Info("C80 selftest FAIL step 3 expected done, got " + r3);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  // 3. Vider tout
  local popped = this._popReactive();
  if (popped == null || popped.key != testKey || popped.count != 2) {
    AILog.Info("C80 selftest FAIL pop coalesced item failed");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  this._clearReactiveQueue();
  this._activeWorker = null;

  if (this._reactiveQueue.len() != 0 || this._activeWorker != null) {
    AILog.Info("C80 selftest FAIL state not clean after selftest");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  // 4. Test d'intercalation (Tranche 1) :
  // Vérifier qu'une intention réactive s'intercale AVANT la tranche suivante
  // d'un travailleur actif, et que le travailleur reprend ensuite.
  local interWorker = {
    kind = "noop",
    state = {
      stepCount = 0,
      targetSteps = 2
    }
  };
  this._activeWorker = interWorker;

  local ir1 = OpexWorkerStep(this._activeWorker, budgetOps, deadlineTick);
  if (ir1 != "running" || interWorker.state.stepCount != 1) {
    AILog.Info("C80 selftest FAIL intercalation worker initial step failed");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local interKey = "c80_intercalation_key";
  this._enqueueReactive(interKey, "noop", { test = true });

  local tickResult = this._runOrchestratorTick();
  if (!tickResult) {
    AILog.Info("C80 selftest FAIL intercalation tick returned false");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }
  if (this._reactiveQueue.has(interKey)) {
    AILog.Info("C80 selftest FAIL reactive intention was not processed first");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }
  if (this._activeWorker == null || this._activeWorker.state.stepCount != 1) {
    local sc = (this._activeWorker != null) ? this._activeWorker.state.stepCount : "null";
    AILog.Info("C80 selftest FAIL worker advanced during reactive tick, stepCount=" + sc);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local ir2 = OpexWorkerStep(this._activeWorker, budgetOps, deadlineTick);
  if (ir2 != "done" || interWorker.state.stepCount != 2) {
    local sc = interWorker.state.stepCount;
    AILog.Info("C80 selftest FAIL worker resume failed, got " + ir2 + " stepCount=" + sc);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }
  this._activeWorker = null;

  this._clearReactiveQueue();
  this._activeWorker = null;

  if (this._reactiveQueue.len() != 0 || this._activeWorker != null) {
    AILog.Info("C80 selftest FAIL state not clean after intercalation test");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  // 5. Test du travailleur town_growth (Tranche 2) :
  // Travailleur de test qui simule 3 villes, vérifie qu'il s'arrête après la première "construction" et qu'il est "done".
  local townWorker = {
    kind = "town_growth",
    state = {
      cursorTownIndex = 0,
      servedTownsList = [101, 102, 103],
      year = 1970,
      mockResults = {}
    }
  };
  townWorker.state.mockResults.rawset(101, false);
  townWorker.state.mockResults.rawset(102, true);
  townWorker.state.mockResults.rawset(103, false);
  this._activeWorker = townWorker;

  local tr1 = OpexWorkerStep(this._activeWorker, budgetOps, deadlineTick);
  if (tr1 != "running" || townWorker.state.cursorTownIndex != 1) {
    AILog.Info("C80 selftest FAIL town worker step 1 expected running with cursor 1, got " + tr1);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local tr2 = OpexWorkerStep(this._activeWorker, budgetOps, deadlineTick);
  if (tr2 != "done") {
    AILog.Info("C80 selftest FAIL town worker step 2 expected done, got " + tr2);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  if (townWorker.state.cursorTownIndex != 2) {
    AILog.Info("C80 selftest FAIL town worker did not stop after first build, cursor=" + townWorker.state.cursorTownIndex);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  this._activeWorker = null;
  this._clearReactiveQueue();

  if (this._reactiveQueue.len() != 0 || this._activeWorker != null) {
    AILog.Info("C80 selftest FAIL state not clean after town worker test");
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  AILog.Info("C80 selftest ok");
  return true;
}

/* ============================================================================
 * 4. C76 Étape 2 / C80 Tranche 3 : Révisions réelles et régénération ciblée
 * ============================================================================ */

function OpexAI::_c76BumpLayer(layer, isEvent = false)
{
  if (!C76_REGEN_TARGETED || this._c76Revisions == null) return;
  if (layer == "towns") {
    this._c76Revisions.towns++;
  } else if (layer == "industries") {
    this._c76Revisions.industries++;
  } else if (layer == "lines") {
    this._c76Revisions.lines++;
  } else if (layer == "engines.rail" || layer == "rail") {
    this._c76Revisions.engines.rail++;
  } else if (layer == "engines.road" || layer == "road") {
    this._c76Revisions.engines.road++;
  } else if (layer == "engines.air" || layer == "air") {
    this._c76Revisions.engines.air++;
  } else if (layer == "engines.water" || layer == "water") {
    this._c76Revisions.engines.water++;
  }

  // Si C80_DOUBLE_REGISTER est actif et qu'il s'agit d'un événement externe :
  // enfiler une intention réactive de clé "regen" (coalescée)
  if (isEvent && C80_DOUBLE_REGISTER) {
    this._enqueueReactive("regen", "regen", null);
  }
}

function OpexAI::_c76GetLayerRevision(layer)
{
  if (this._c76Revisions == null) return 0;
  if (layer == "towns") return this._c76Revisions.towns;
  if (layer == "industries") return this._c76Revisions.industries;
  if (layer == "lines") return this._c76Revisions.lines;
  if (layer == "engines.rail") return this._c76Revisions.engines.rail;
  if (layer == "engines.road") return this._c76Revisions.engines.road;
  if (layer == "engines.air") return this._c76Revisions.engines.air;
  if (layer == "engines.water") return this._c76Revisions.engines.water;
  return 0;
}

function OpexAI::_c76GetModeDeps(mode)
{
  // Matrice mode <- couches selon contrat 18_orchestrateur_double_registre.md §5.2
  if (mode == "air") return ["towns", "engines.air", "lines"];
  if (mode == "rail_pax") return ["towns", "engines.rail", "lines"];
  if (mode == "rail_freight") return ["industries", "engines.rail", "lines"];
  if (mode == "road_pax") return ["towns", "engines.road", "lines"];
  if (mode == "road_freight") return ["industries", "engines.road", "lines"];
  if (mode == "water") return ["industries", "engines.water", "lines"];
  if (mode == "fleet") return ["lines", "engines.rail", "engines.road", "engines.air", "engines.water"];
  if (mode == "rail") return ["towns", "industries", "engines.rail", "lines"];
  if (mode == "road") return ["towns", "industries", "engines.road", "lines"];
  return [];
}

function OpexAI::_c76ModeNeedsRegen(mode)
{
  if (!C76_REGEN_TARGETED || this._c76Revisions == null) return true;
  local deps = this._c76GetModeDeps(mode);
  local consumed = (mode in this._c76ModeConsumed) ? this._c76ModeConsumed[mode] : {};
  foreach (layer in deps) {
    local cur = this._c76GetLayerRevision(layer);
    local ack = (layer in consumed) ? consumed[layer] : -1;
    if (cur > ack) return true;
  }
  return false;
}

function OpexAI::_c76AnyLayerChanged()
{
  if (!C76_REGEN_TARGETED || this._c76Revisions == null || this._c76AckRevisions == null) return false;
  if (this._c76Revisions.towns > this._c76AckRevisions.towns) return true;
  if (this._c76Revisions.industries > this._c76AckRevisions.industries) return true;
  if (this._c76Revisions.lines > this._c76AckRevisions.lines) return true;
  if (this._c76Revisions.engines.rail > this._c76AckRevisions.engines.rail) return true;
  if (this._c76Revisions.engines.road > this._c76AckRevisions.engines.road) return true;
  if (this._c76Revisions.engines.air > this._c76AckRevisions.engines.air) return true;
  if (this._c76Revisions.engines.water > this._c76AckRevisions.engines.water) return true;
  return false;
}

function OpexAI::_c76AcknowledgeAllLayers()
{
  if (this._c76Revisions == null) return;
  if (this._c76AckRevisions == null) {
    this._c76AckRevisions = {
      towns = 0, industries = 0, lines = 0,
      engines = { rail = 0, road = 0, air = 0, water = 0 }
    };
  }
  this._c76AckRevisions.towns = this._c76Revisions.towns;
  this._c76AckRevisions.industries = this._c76Revisions.industries;
  this._c76AckRevisions.lines = this._c76Revisions.lines;
  this._c76AckRevisions.engines.rail = this._c76Revisions.engines.rail;
  this._c76AckRevisions.engines.road = this._c76Revisions.engines.road;
  this._c76AckRevisions.engines.air = this._c76Revisions.engines.air;
  this._c76AckRevisions.engines.water = this._c76Revisions.engines.water;

  local modes = ["air", "rail_pax", "rail_freight", "road_pax", "road_freight", "water", "fleet", "rail", "road"];
  foreach (mode in modes) {
    local deps = this._c76GetModeDeps(mode);
    if (!(mode in this._c76ModeConsumed)) this._c76ModeConsumed.rawset(mode, {});
    local sumRev = 0;
    foreach (layer in deps) {
      local rev = this._c76GetLayerRevision(layer);
      this._c76ModeConsumed[mode].rawset(layer, rev);
      sumRev += rev;
    }
    this._c76ModeConsumedRevision.rawset(mode, sumRev);
  }
}

function OpexAI::_c76DoFullRegen(reason, year)
{
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  /* Meme unite que _dispatchCatalog : filet annuel, la variable porte l'annee. */
  local curQuarter = year;

  this._lastCatalogMonth = ym;
  this._pruneAbandonedPairs(date);

  if (PORTFOLIO_REFRESH_PROBE) {
    local refreshMark = OpexOpsMeasureBegin();
    this._catalog.refresh(this._budget, year);
    PORTFOLIO_REFRESH_PROBE_REFRESH_OPS += OpexOpsMeasureEnd(refreshMark);
    PORTFOLIO_REFRESH_PROBE_REFRESH_COUNT++;
  } else {
    this._catalog.refresh(this._budget, year);
  }

  local fleetPlan = null;
  if (FLEET_PORTFOLIO) {
    fleetPlan = [];
    this._resizeAirFleets(AIDate.GetYear(date), fleetPlan);
  }

  if (this._recomputeEpochBounds) {
    OpexRefreshEpochBounds(this._catalog);
    this._recomputeEpochBounds = false;
  }

  local c76Mark = C39_INVALIDATION_PROBE ? OpexOpsMeasureBegin() : null;
  this._rebuildProjects(fleetPlan);
  if (C39_INVALIDATION_PROBE) {
    local c76Ops = OpexOpsMeasureEnd(c76Mark);
    local c76Days = (c76Ops + 93000) / 186000;
    this._c76RecordRegen("full", c76Ops, c76Days, year, reason);
  }

  this._c76AcknowledgeAllLayers();
  this._c76LastRegenQuarter = curQuarter;
  this._c76ForceReloadRegen = false;
  this._portfolioInvalidated = false;

  if (C39_PROJECTS_CADENCE_PROBE) this._c39StampFinanceable();
  if (this._catalog != null && this._catalog.bounds != null) {
    local b = this._catalog.bounds;
    OpexSign(AIMap.GetTileIndex(1, 2), "EB|" + b.roadMin + "|" + b.railMin
             + "|" + b.railAirOverlapMin + "|" + b.railMax);
  }

  this._logStalenessRefresh(reason);
  this._ranked = this._projects.rail;

  if (PORTFOLIO_LOG) {
    if (this._projects != null && this._projects.best != null && this._projects.best.len() > 0) {
      OpexLogPortfolioRank(this._projects);
    } else if (DECISION_LOG) {
      local cBudget = (this._projects != null) ? this._projects.capitalBudget : 0;
      OpexDecide("PORTFOLIO_EMPTY", "budget=" + cBudget);
    }
  }

  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;
  OpexSign(anchor, "IG|" + yy + "|" + this._projects.stats.modeCandidates + "|"
           + this._projects.stats.odProjects + "|" + this._projects.stats.budgetSelected
           + "|" + (this._projects.stats.knapsackExact ? 0 : 1)
           + "|" + this._budget.nested + "|" + (this._projects.stats.selectionOpcodes / 1000));
  OpexSign(anchor, "IB|" + yy + "|" + this._projects.capitalBudget + "|"
           + this._projects.stats.selectedCapital + "|B0");
}

function OpexAI::_c76SaveRevisions()
{
  local consumedCopy = {};
  if (this._c76ModeConsumed != null) {
    foreach (mode, layers in this._c76ModeConsumed) {
      local mTable = {};
      if (typeof layers == "table") {
        foreach (layer, rev in layers) {
          mTable.rawset(layer, rev);
        }
      }
      consumedCopy.rawset(mode, mTable);
    }
  }

  local consumedRevCopy = {};
  if (this._c76ModeConsumedRevision != null) {
    foreach (mode, rev in this._c76ModeConsumedRevision) {
      consumedRevCopy.rawset(mode, rev);
    }
  }

  return {
    towns = this._c76Revisions.towns,
    industries = this._c76Revisions.industries,
    lines = this._c76Revisions.lines,
    engines_rail = this._c76Revisions.engines.rail,
    engines_road = this._c76Revisions.engines.road,
    engines_air = this._c76Revisions.engines.air,
    engines_water = this._c76Revisions.engines.water,

    ack_towns = this._c76AckRevisions.towns,
    ack_industries = this._c76AckRevisions.industries,
    ack_lines = this._c76AckRevisions.lines,
    ack_engines_rail = this._c76AckRevisions.engines.rail,
    ack_engines_road = this._c76AckRevisions.engines.road,
    ack_engines_air = this._c76AckRevisions.engines.air,
    ack_engines_water = this._c76AckRevisions.engines.water,

    modeConsumed = consumedCopy,
    modeConsumedRev = consumedRevCopy,
    lastRegenQuarter = this._c76LastRegenQuarter
  };
}

function OpexAI::_c76LoadRevisions(data)
{
  if (data == null || typeof data != "table") return;
  if ("towns" in data) this._c76Revisions.towns = data.towns;
  if ("industries" in data) this._c76Revisions.industries = data.industries;
  if ("lines" in data) this._c76Revisions.lines = data.lines;
  if ("engines_rail" in data) this._c76Revisions.engines.rail = data.engines_rail;
  if ("engines_road" in data) this._c76Revisions.engines.road = data.engines_road;
  if ("engines_air" in data) this._c76Revisions.engines.air = data.engines_air;
  if ("engines_water" in data) this._c76Revisions.engines.water = data.engines_water;

  if ("ack_towns" in data) this._c76AckRevisions.towns = data.ack_towns;
  if ("ack_industries" in data) this._c76AckRevisions.industries = data.ack_industries;
  if ("ack_lines" in data) this._c76AckRevisions.lines = data.ack_lines;
  if ("ack_engines_rail" in data) this._c76AckRevisions.engines.rail = data.ack_engines_rail;
  if ("ack_engines_road" in data) this._c76AckRevisions.engines.road = data.ack_engines_road;
  if ("ack_engines_air" in data) this._c76AckRevisions.engines.air = data.ack_engines_air;
  if ("ack_engines_water" in data) this._c76AckRevisions.engines.water = data.ack_engines_water;

  if ("modeConsumed" in data && typeof data.modeConsumed == "table") {
    foreach (mode, layers in data.modeConsumed) {
      if (!(mode in this._c76ModeConsumed)) this._c76ModeConsumed.rawset(mode, {});
      if (typeof layers == "table") {
        foreach (layer, rev in layers) {
          this._c76ModeConsumed[mode].rawset(layer, rev);
        }
      }
    }
  }
  if ("modeConsumedRev" in data && typeof data.modeConsumedRev == "table") {
    foreach (mode, rev in data.modeConsumedRev) {
      this._c76ModeConsumedRevision.rawset(mode, rev);
    }
  }
  if ("lastRegenQuarter" in data) this._c76LastRegenQuarter = data.lastRegenQuarter;

  // Point 4 : forcer la régénération au chargement
  this._c76ForceReloadRegen = true;
}

function OpexAI::_c76RunSelfTest()
{
  local savedRevs = this._c76SaveRevisions();
  local savedForceReload = this._c76ForceReloadRegen;

  // Réinitialiser à un état neutre
  this._c76Revisions = {
    towns = 0,
    industries = 0,
    lines = 0,
    engines = { rail = 0, road = 0, air = 0, water = 0 }
  };
  this._c76AckRevisions = {
    towns = 0,
    industries = 0,
    lines = 0,
    engines = { rail = 0, road = 0, air = 0, water = 0 }
  };
  this._c76ModeConsumed = {};
  this._c76ModeConsumedRevision = {};
  this._c76AcknowledgeAllLayers();
  this._c76ForceReloadRegen = false;

  // 1. Aucune couche incrémentée -> régénération évitée
  if (this._c76AnyLayerChanged()) {
    AILog.Info("C76 selftest FAIL: initial state reports layer changed");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }
  if (this._c76ModeNeedsRegen("air") || this._c76ModeNeedsRegen("water") || this._c76ModeNeedsRegen("rail_pax")) {
    AILog.Info("C76 selftest FAIL: initial state reports mode needs regen");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }

  // 2. Incrément de la couche towns -> régénération demandée pour air/rail_pax, pas pour water
  this._c76BumpLayer("towns", false);
  if (!this._c76AnyLayerChanged()) {
    AILog.Info("C76 selftest FAIL: towns bump did not mark any layer changed");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }
  if (!this._c76ModeNeedsRegen("air")) {
    AILog.Info("C76 selftest FAIL: air did not need regen after towns bump");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }
  if (this._c76ModeNeedsRegen("water")) {
    AILog.Info("C76 selftest FAIL: water needed regen after towns bump (unexpected)");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }

  // 3. Acquittement complet -> régénération évitée à nouveau
  this._c76AcknowledgeAllLayers();
  if (this._c76AnyLayerChanged()) {
    AILog.Info("C76 selftest FAIL: layers still changed after acknowledge");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }
  if (this._c76ModeNeedsRegen("air")) {
    AILog.Info("C76 selftest FAIL: air still needs regen after acknowledge");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }

  // 4. Incrément de industries -> water demande regen, air non
  this._c76BumpLayer("industries", false);
  if (!this._c76AnyLayerChanged()) {
    AILog.Info("C76 selftest FAIL: industries bump did not mark layer changed");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }
  if (!this._c76ModeNeedsRegen("water")) {
    AILog.Info("C76 selftest FAIL: water did not need regen after industries bump");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }
  if (this._c76ModeNeedsRegen("air")) {
    AILog.Info("C76 selftest FAIL: air needed regen after industries bump (unexpected)");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }

  // 5. Test de la file réactive sous C80_DOUBLE_REGISTER
  if (C80_DOUBLE_REGISTER) {
    this._clearReactiveQueue();
    this._c76BumpLayer("towns", true); // isEvent = true
    if (!this._hasReactiveIntentions()) {
      AILog.Info("C76 selftest FAIL: event bump did not enqueue reactive regen");
      this._clearReactiveQueue();
      this._c76LoadRevisions(savedRevs);
      this._c76ForceReloadRegen = savedForceReload;
      return false;
    }
    local popped = this._popReactive();
    if (popped == null || popped.key != "regen") {
      local pk = (popped != null) ? popped.key : "null";
      AILog.Info("C76 selftest FAIL: expected key regen, got " + pk);
      this._clearReactiveQueue();
      this._c76LoadRevisions(savedRevs);
      this._c76ForceReloadRegen = savedForceReload;
      return false;
    }
    this._clearReactiveQueue();
  }

  // Restauration propre de l'état
  this._c76LoadRevisions(savedRevs);
  this._c76ForceReloadRegen = savedForceReload;

  AILog.Info("C76 selftest ok");
  return true;
}

