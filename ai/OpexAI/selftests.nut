/* OpexAI -- selftests.nut
 * R16 : autotests C80/C76 extraits de orchestrator.nut, corps inchanges.
 * Requis apres la classe OpexAI ; appeles depuis OpexAI::Start sous les memes gardes. */

/* Selftest C80 tranche 0 :
 * Déclenché une seule fois au démarrage si C80_DOUBLE_REGISTER est vrai.
 * 1. Enfile deux intentions de même clé (vérifie la coalescence).
 * 2. Enregistre le travailleur "noop" qui se termine en 3 étapes, vérifie les transitions.
 * 3. Vide tout et vérifie qu'aucun état ne subsiste.
 * Journalise "C80 selftest ok" ou "C80 selftest FAIL <raison>" via AILog.Info.
 */
function OpexAI::_c80RunSelfTest()
{
  /* R5 : les sous-tests mutent les files et workers vivants. Au reload, ne
   * toucher a aucun etat restaure, meme si la file est vide mais un worker vit. */
  if (this._loadedFromSave) {
    AILog.Info("C80 selftest skipped: loaded game");
    return true;
  }
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

  // 6. Test (a) Aller-retour Save/Load en memoire de la file reactive et d'un travailleur regen_candidates
  local savedOrigQueue = (this._reactiveQueue != null) ? OpexSaveReactiveQueue(this._reactiveQueue) : null;
  local savedOrigWorker = this._activeWorker;

  this._clearReactiveQueue();
  this._enqueueReactive("test_regen", "regen", null);
  this._enqueueReactive("test_entity", "c77_entity", {
    modes = ["air", "rail"], cursor = 0, targeted = true,
    entityKind = "town", entityId = 10, buildAfter = true, reason = "event"
  });
  this._enqueueReactive("test_subsidy", "c77_subsidy", { subsidyId = 7 });
  this._enqueueReactive("test_build", "c77_build", { reason = "subsidy_offer" });
  this._enqueueReactive("test_noop", "noop", { step = 1 });
  // Coalescence : re-enfiler test_regen pour verifier count = 2
  this._enqueueReactive("test_regen", "regen", null);

  local testRegenWorker = {
    kind = "regen_candidates",
    state = {
      modes = ["air", "rail", "road"],
      cursor = 1,
      targeted = true,
      entityKind = "town",
      entityId = 10,
      buildAfter = true,
      reason = "event"
    },
    ai = this
  };

  local savedQData = OpexSaveReactiveQueue(this._reactiveQueue);
  local savedWData = OpexSaveActiveWorker(testRegenWorker);

  local hasFloat = function(val, rec) {
    if (typeof val == "float") return true;
    if (typeof val == "table") {
      foreach (k, v in val) {
        if (typeof k == "float") return true;
        if (rec(v, rec)) return true;
      }
    } else if (typeof val == "array") {
      foreach (v in val) {
        if (rec(v, rec)) return true;
      }
    }
    return false;
  };

  if (hasFloat(savedQData, hasFloat)) {
    AILog.Info("C80 selftest FAIL reactive queue save contains float");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (hasFloat(savedWData, hasFloat)) {
    AILog.Info("C80 selftest FAIL active worker save contains float");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  local loadedQ = OpexLoadReactiveQueue(savedQData);
  local loadedW = OpexLoadActiveWorker(savedWData);

  if (loadedQ.len() != 5) {
    AILog.Info("C80 selftest FAIL loaded queue len expected 5, got " + loadedQ.len());
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  local qItem1 = loadedQ.pop();
  if (qItem1 == null || qItem1.key != "test_regen" || qItem1.kind != "regen" || qItem1.count != 2) {
    AILog.Info("C80 selftest FAIL loaded queue item 1 mismatch");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  local qItem2 = loadedQ.pop();
  if (qItem2 == null || qItem2.key != "test_entity" || qItem2.kind != "c77_entity" || qItem2.count != 1
      || qItem2.payload == null || qItem2.payload.entityId != 10) {
    AILog.Info("C80 selftest FAIL loaded queue item 2 mismatch");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  local qItem3 = loadedQ.pop();
  if (qItem3 == null || qItem3.key != "test_subsidy" || qItem3.kind != "c77_subsidy" || qItem3.count != 1
      || qItem3.payload == null || qItem3.payload.subsidyId != 7) {
    AILog.Info("C80 selftest FAIL loaded queue item 3 mismatch");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  local qItem4 = loadedQ.pop();
  if (qItem4 == null || qItem4.key != "test_build" || qItem4.kind != "c77_build" || qItem4.count != 1
      || qItem4.payload == null || qItem4.payload.reason != "subsidy_offer") {
    AILog.Info("C80 selftest FAIL loaded queue item 4 mismatch");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  local qItem5 = loadedQ.pop();
  if (qItem5 == null || qItem5.key != "test_noop" || qItem5.kind != "noop" || qItem5.count != 1
      || qItem5.payload == null || qItem5.payload.step != 1) {
    AILog.Info("C80 selftest FAIL loaded queue item 5 mismatch");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (!loadedQ.isEmpty()) {
    AILog.Info("C80 selftest FAIL loaded queue not empty after popping all items");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (loadedW == null || loadedW.kind != "regen_candidates" || loadedW.state == null) {
    AILog.Info("C80 selftest FAIL loaded worker header mismatch");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (loadedW.state.cursor != 1 || loadedW.state.modes.len() != 3 || loadedW.state.modes[0] != "air"
      || loadedW.state.targeted != true || loadedW.state.entityKind != "town" || loadedW.state.entityId != 10
      || loadedW.state.buildAfter != true || loadedW.state.reason != "event") {
    AILog.Info("C80 selftest FAIL loaded worker state mismatch");
    if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
    else this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  // Nettoyage etape 6
  if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
  else this._clearReactiveQueue();
  this._activeWorker = savedOrigWorker;

  // 7. Test (b) Intention mutatrice (kind regen) pendant qu'un travailleur noop tient le registre.
  /* Hors C76 seulement : sous C76, l'intention regen lance une vraie regeneration complete
   * (catalogue, rotation du cargo fret, elagage des abandons) que la restauration ne defait pas. */
  if (!C76_REGEN_TARGETED) {
  /* Comportement ACTUEL documente : _dispatchReactiveIntention traite l'intention "regen"
   * immediatement (renvoie true) sans deferer, meme lorsqu'un travailleur "noop" occupe le registre,
   * car seul regen_candidates detient un verrou d'ecriture exclusif sur le vivier. Le travailleur
   * actif n'est ni ecrase ni annule et conserve son etat intact. */
  local mutNoopWorker = {
    kind = "noop",
    state = {
      stepCount = 0,
      targetSteps = 3
    }
  };
  this._activeWorker = mutNoopWorker;
  this._clearReactiveQueue();

  local savedC76Revs = this._c76SaveRevisions();
  local savedC76Force = this._c76ForceReloadRegen;
  local savedProjectsBeforeMut = this._projects;
  local savedLastCatalog = this._lastCatalogMonth;

  local regenIntention = { key = "regen", kind = "regen", payload = null };
  local dispatchedRegen = this._dispatchReactiveIntention(regenIntention);
  if (!dispatchedRegen) {
    AILog.Info("C80 selftest FAIL mutating intention regen dispatch returned false");
    this._c76LoadRevisions(savedC76Revs);
    this._c76ForceReloadRegen = savedC76Force;
    this._projects = savedProjectsBeforeMut;
    this._lastCatalogMonth = savedLastCatalog;
    this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (this._activeWorker == null || this._activeWorker.kind != "noop"
      || this._activeWorker.state.stepCount != 0) {
    AILog.Info("C80 selftest FAIL mutating intention corrupted active worker");
    this._c76LoadRevisions(savedC76Revs);
    this._c76ForceReloadRegen = savedC76Force;
    this._projects = savedProjectsBeforeMut;
    this._lastCatalogMonth = savedLastCatalog;
    this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (this._hasReactiveIntentions()) {
    AILog.Info("C80 selftest FAIL mutating intention was deferred unexpectedly");
    this._c76LoadRevisions(savedC76Revs);
    this._c76ForceReloadRegen = savedC76Force;
    this._projects = savedProjectsBeforeMut;
    this._lastCatalogMonth = savedLastCatalog;
    this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  local mutStepOutcome = OpexWorkerStep(this._activeWorker, 10000, AIController.GetTick() + 100);
  if (mutStepOutcome != "running" || this._activeWorker.state.stepCount != 1) {
    AILog.Info("C80 selftest FAIL worker step failed after mutating intention dispatch");
    this._c76LoadRevisions(savedC76Revs);
    this._c76ForceReloadRegen = savedC76Force;
    this._projects = savedProjectsBeforeMut;
    this._lastCatalogMonth = savedLastCatalog;
    this._clearReactiveQueue();
    this._activeWorker = savedOrigWorker;
    return false;
  }

  // Nettoyage etape 7
  this._c76LoadRevisions(savedC76Revs);
  this._c76ForceReloadRegen = savedC76Force;
  this._projects = savedProjectsBeforeMut;
  this._lastCatalogMonth = savedLastCatalog;
  this._clearReactiveQueue();
  this._activeWorker = savedOrigWorker;

  }

  // 8. Test (c) Cycle de vie d'une subvention C77 (chemins purs sans creation d'objets de jeu)
  local savedProjectsForSub = this._projects;
  local savedSubsidies = this._activeSubsidies;

  // Chemin pur 1 : sans vivier, _c77InjectSubsidy doit renvoyer false sans planter
  this._projects = null;
  local injectNullResult = this._c77InjectSubsidy(999);
  if (injectNullResult != false) {
    AILog.Info("C80 selftest FAIL inject subsidy without projects expected false");
    this._projects = savedProjectsForSub;
    this._activeSubsidies = savedSubsidies;
    this._activeWorker = savedOrigWorker;
    return false;
  }

  // Chemin pur 2 : purge _purgeSubsidyFromProjects sur un vivier factice
  local dummySubProject1 = {
    payload = { isSubsidy = true, subsidyId = 77 }
  };
  local dummyNormalProject = {
    payload = { isSubsidy = false, subsidyId = -1 }
  };
  local dummySubProject2 = {
    payload = { isSubsidy = true, subsidyId = 88 }
  };
  local dummyRoadSubProject = {
    payload = { isSubsidy = true, subsidyId = 77 }
  };
  local dummyRoadNormalProject = {
    payload = { isSubsidy = false, subsidyId = -1 }
  };

  this._projects = {
    best = [dummySubProject1, dummyNormalProject, dummySubProject2],
    road = {
      best = [dummyRoadSubProject, dummyRoadNormalProject]
    },
    candidateGroups = {
      ["subsidy|77"] = dummySubProject1,
      ["subsidy|88"] = dummySubProject2,
      ["other|normal"] = dummyNormalProject
    }
  };

  this._purgeSubsidyFromProjects(77);

  if (this._projects.best.len() != 2) {
    AILog.Info("C80 selftest FAIL purge subsidy best len expected 2, got " + this._projects.best.len());
    this._projects = savedProjectsForSub;
    this._activeSubsidies = savedSubsidies;
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (this._projects.best[0].payload.subsidyId == 77 || this._projects.best[1].payload.subsidyId == 77) {
    AILog.Info("C80 selftest FAIL purge subsidy did not remove subsidy 77 from best");
    this._projects = savedProjectsForSub;
    this._activeSubsidies = savedSubsidies;
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (this._projects.road.best.len() != 1 || this._projects.road.best[0].payload.subsidyId == 77) {
    AILog.Info("C80 selftest FAIL purge subsidy did not remove subsidy 77 from road.best");
    this._projects = savedProjectsForSub;
    this._activeSubsidies = savedSubsidies;
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if ("subsidy|77" in this._projects.candidateGroups) {
    AILog.Info("C80 selftest FAIL purge subsidy did not delete candidateGroups entry");
    this._projects = savedProjectsForSub;
    this._activeSubsidies = savedSubsidies;
    this._activeWorker = savedOrigWorker;
    return false;
  }

  if (!("subsidy|88" in this._projects.candidateGroups) || !("other|normal" in this._projects.candidateGroups)) {
    AILog.Info("C80 selftest FAIL purge subsidy deleted unrelated candidateGroups entries");
    this._projects = savedProjectsForSub;
    this._activeSubsidies = savedSubsidies;
    this._activeWorker = savedOrigWorker;
    return false;
  }

  // Purge avec des entrees neutralisees (null, negatif, id inexistant)
  this._purgeSubsidyFromProjects(-1);
  this._purgeSubsidyFromProjects(null);
  this._purgeSubsidyFromProjects(999);
  if (this._projects.best.len() != 2 || this._projects.road.best.len() != 1) {
    AILog.Info("C80 selftest FAIL purge subsidy with neutral inputs corrupted projects");
    this._projects = savedProjectsForSub;
    this._activeSubsidies = savedSubsidies;
    this._activeWorker = savedOrigWorker;
    return false;
  }

  // Restauration complete de l'etat
  this._projects = savedProjectsForSub;
  this._activeSubsidies = savedSubsidies;
  this._activeWorker = savedOrigWorker;
  if (savedOrigQueue != null) this._reactiveQueue = OpexLoadReactiveQueue(savedOrigQueue);
  else this._clearReactiveQueue();

  AILog.Info("C80 selftest ok");
  return true;
}

function OpexAI::_c76RunSelfTest()
{
  /* R5 : ce test efface aussi la file reactive, independamment du test C80. */
  if (this._loadedFromSave) {
    AILog.Info("C76 selftest skipped: loaded game");
    return true;
  }
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

  // 2. Increment de la couche towns -> regeneration demandee pour air/rail_pax/water
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
  if (!this._c76ModeNeedsRegen("water")) {
    AILog.Info("C76 selftest FAIL: water did not need regen after towns bump");
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

  // 4. Increment de industries -> rail_freight demande regen, air et water non
  this._c76BumpLayer("industries", false);
  if (!this._c76AnyLayerChanged()) {
    AILog.Info("C76 selftest FAIL: industries bump did not mark layer changed");
    this._c76LoadRevisions(savedRevs);
    this._c76ForceReloadRegen = savedForceReload;
    return false;
  }
  if (this._c76ModeNeedsRegen("water")) {
    AILog.Info("C76 selftest FAIL: water needed regen after industries bump (unexpected)");
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
