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

function OpexWorkerStep(owner, worker, opsBudget, deadlineTick)
{
  if (worker == null || typeof worker != "table" || !("kind" in worker)) return "cancelled";
  local kind = worker.kind;
  if (!(kind in OPEX_WORKER_REGISTRY)) {
    AILog.Warning("C80: unknown worker kind: " + kind);
    return "cancelled";
  }
  return OPEX_WORKER_REGISTRY[kind].step(owner, worker, opsBudget, deadlineTick);
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
function OpexWorkerNoopStep(owner, worker, opsBudget, deadlineTick)
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

function OpexWorkerRegenCandidatesStep(owner, worker, opsBudget, deadlineTick)
{
  if (owner == null || worker == null || !("state" in worker)
      || worker.state == null || typeof worker.state != "table") return "cancelled";
  local s = worker.state;
  if (!("modes" in s) || s.modes == null || typeof s.modes != "array") return "cancelled";
  if (!("cursor" in s)) s.cursor <- 0;
  if (s.cursor >= s.modes.len()) return "done";
  local mode = s.modes[s.cursor];
  owner._c76RefreshModeCatalog(mode);
  if (owner._projects == null) {
    owner._catalog.refresh(owner._budget, AIDate.GetYear(AIDate.GetCurrentDate()));
    owner._rebuildProjects(null);
  } else {
    local targeted = ("targeted" in s) && s.targeted;
    local entityKind = targeted && ("entityKind" in s) ? s.entityKind : null;
    local entityId = targeted && ("entityId" in s) ? s.entityId : -1;
    owner._projects = OpexRegenerateModeProjects(owner._projects, owner._catalog, owner._budget,
        owner._lines, owner._abandonedPairs, mode, null, entityKind, entityId);
  }
  if (owner._projects != null) owner._ranked = owner._projects.rail;
  if (!(("targeted" in s) && s.targeted)) owner._c76AcknowledgeMode(mode);
  s.cursor++;
  if (s.cursor >= s.modes.len()) {
    if (("buildAfter" in s) && s.buildAfter) {
      local reason = ("reason" in s) ? s.reason : "event";
      owner._enqueueReactive("c77|build|" + reason, "c77_build", { reason = reason });
    }
    return "done";
  }
  return "running";
}

function OpexWorkerRegenCandidatesCancel(worker)
{
  if (worker != null && ("state" in worker) && worker.state != null
      && typeof worker.state == "table") worker.state.cancelled <- true;
}

OpexRegisterWorker("regen_candidates", OpexWorkerRegenCandidatesStep, OpexWorkerRegenCandidatesCancel);

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
  /* Toutes les intentions C76/C77 mutent le catalogue, le vivier ou construisent.
   * Un travailleur de regeneration actif detient donc le droit d'ecriture jusqu'a
   * la fin de sa tranche. Replacer l'intention en queue permet de l'intercaler
   * entre les tranches sans modifier le vivier concurremment. */
  if (this._activeWorker != null) {
    this._enqueueReactive(intention.key, intention.kind, intention.payload);
    return false;
  }
  if (intention.kind == "c76_regen" || intention.kind == "c77_entity") {
    this._activeWorker = { kind = "regen_candidates", state = intention.payload };
    return true;
  }
  if (intention.kind == "c77_build") {
    if (this._projects != null && !this._portfolioInvalidated) {
      this._tryBuildProjects(AIDate.GetYear(AIDate.GetCurrentDate()));
    }
    return true;
  }
  return true;
}

function OpexAI::_c76EnqueueRegen(modes, entityKind = null, entityId = -1, targeted = false,
                                  buildAfter = false, reason = "event")
{
  if (!C80_DOUBLE_REGISTER || modes == null) return false;
  local validModes = [];
  local key = targeted ? ("c77|" + entityKind + "|" + entityId) : ("c76|" + reason);
  foreach (mode in modes) {
    if (mode != "rail" && mode != "road" && mode != "air" && mode != "water") continue;
    validModes.append(mode);
    key += "|" + mode;
  }
  if (validModes.len() == 0) return false;
  local payload = {
    modes = validModes, cursor = 0, targeted = targeted,
    entityKind = entityKind, entityId = entityId,
    buildAfter = buildAfter,
    reason = reason,
  };
  this._enqueueReactive(key, targeted ? "c77_entity" : "c76_regen", payload);
  return true;
}

function OpexAI::_c76RefreshModeCatalog(mode)
{
  if (this._catalog == null) return;
  this._catalog.year = AIDate.GetYear(AIDate.GetCurrentDate());
  this._catalog._refreshCargos();
  if (mode == "air") {
    this._catalog._refreshTowns();
    this._catalog._refreshAir();
  } else if (mode == "rail") {
    this._catalog._refreshTowns();
    this._catalog._refreshIndustries();
    this._catalog._refreshRail();
  } else if (mode == "road") {
    this._catalog._refreshTowns();
    this._catalog._refreshIndustries();
    if (ROAD_BUILD_ENABLED) this._catalog._refreshRoad();
  } else if (mode == "water") {
    this._catalog._refreshTowns();
    this._catalog._refreshWater();
  }
  if (this._recomputeEpochBounds) {
    OpexRefreshEpochBounds(this._catalog);
    this._recomputeEpochBounds = false;
  }
}

function OpexAI::_c76AcknowledgeMode(mode)
{
  if (this._staleness == null) return;
  local layers = ["cargos"];
  if (mode == "air") {
    layers.append("towns"); layers.append("air");
  } else if (mode == "rail") {
    layers.append("towns"); layers.append("industries"); layers.append("rail");
  } else if (mode == "road") {
    layers.append("towns"); layers.append("industries"); layers.append("road");
  } else if (mode == "water") {
    layers.append("towns"); layers.append("water");
  }
  foreach (layer in layers) {
    if (layer in this._staleness.revisions.catalog) {
      this._staleness.acknowledged.catalog[layer] = this._staleness.revisions.catalog[layer];
      this._staleness.catalog[layer] = false;
      this._staleness.dirtySince.catalog[layer] = -1;
    }
  }
  if (mode in this._staleness.revisions.candidates) {
    this._staleness.acknowledged.candidates[mode] = this._staleness.revisions.candidates[mode];
    this._staleness.candidates[mode] = false;
    this._staleness.dirtySince.candidates[mode] = -1;
  }
  this._staleness.acknowledged.portfolio = this._staleness.revisions.portfolio;
  this._staleness.acknowledged.selection = this._staleness.revisions.selection;
  this._staleness.portfolio = false;
  this._staleness.selection = false;
}

function OpexAI::_c76PeriodicReconcile(yearMonth)
{
  if (!C76_REGEN_TARGETED || !C80_DOUBLE_REGISTER || this._projects == null) return false;
  if (this._c76LastReconcileMonth < 0) {
    this._c76LastReconcileMonth = yearMonth;
    return false;
  }
  if (yearMonth - this._c76LastReconcileMonth < C76_RECONCILE_MONTHS) return false;
  this._c76LastReconcileMonth = yearMonth;
  /* Filet de fond : volume uniquement, aucune découverte de paire/site. */
  this._catalog._refreshTowns();
  this._catalog._refreshIndustries();
  this._projects = OpexC76RepriceProjects(this._projects, this._catalog, this._lines,
                                          this._abandonedPairs);
  this._ranked = this._projects.rail;
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
  // (b) Intention réactive
  if (this._hasReactiveIntentions()) {
    local intention = this._popReactive();
    if (intention != null) {
      if (this._dispatchReactiveIntention(intention)) return true;
    }
  }

  // (c) Tranche du travailleur actif s'il y en a un
  if (this._activeWorker != null) {
    local opsBudget = AIController.GetOpsTillSuspend();
    local deadlineTick = AIController.GetTick() + BUILD_TICK_MARGIN;
    local outcome = OpexWorkerStep(this, this._activeWorker, opsBudget, deadlineTick);
    if (outcome == "done" || outcome == "cancelled") {
      this._activeWorker = null;
    }
    return true;
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

  local r1 = OpexWorkerStep(this, this._activeWorker, budgetOps, deadlineTick);
  if (r1 != "running") {
    AILog.Info("C80 selftest FAIL step 1 expected running, got " + r1);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local r2 = OpexWorkerStep(this, this._activeWorker, budgetOps, deadlineTick);
  if (r2 != "running") {
    AILog.Info("C80 selftest FAIL step 2 expected running, got " + r2);
    this._clearReactiveQueue();
    this._activeWorker = null;
    return false;
  }

  local r3 = OpexWorkerStep(this, this._activeWorker, budgetOps, deadlineTick);
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

  AILog.Info("C80 selftest ok");
  return true;
}
