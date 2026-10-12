# Rapport d'analyse : Reliquat C76/C77

**Date :** 12 octobre 2026  
**Auteur :** Antigravity (mode lecture seule — aucun conteneur Docker, aucun banc, aucun commit, aucune modification de code)  
**Objet :** Instruction de la ligne « C76/C77 reliquat » de `docs/taches.md` :
> *« Vérifier vivier injecté, invalidation non-AIR, intention mutatrice pendant worker, cycle de subvention et Save/Load. Points 1–5, horloge et premiers selftests déjà codés : ne pas les refaire. Réévaluation légère du vivier reste une piste distincte, pas retour à `lean`/rotation rejetés. »*

---

## 1. Contexte documentaire et repères historiques

La recherche documentaire dans `docs/` (notamment `docs/17_evenements_regeneration.md`, `docs/18_orchestrateur_double_registre.md`, `docs/revue_code_2026-09-22_integrale.md`, `docs/journaux/journal_2026-09-22_transfert_historique.md`, `docs/journaux/23_nuit_2026-09-23.md` et `docs/revue_code_2026-09-30.md`) permet de retracer l'origine exacte des éléments du reliquat :

1. **Socle C76 / C77 / C80 (21–23 septembre 2026) :**
   - **C76** : Routeur d'événements et régénération ciblée par couches (`docs/17_evenements_regeneration.md`).
   - **C77** : Candidats opportunistes réactifs (`docs/18_orchestrateur_double_registre.md` et `journal_2026-09-22.md`).
   - **C80** : Orchestrateur à double registre (file réactive et file de fond, workers résumables).
2. **Points 1 à 5 et selftests initiaux (commit `ec9f91c` du 23/09, branche `c76-pistes-a`) :**
   - *Point 1* : Invalidation budget -> resélection (`c76_lean_invalidation`, rejeté ultérieurement en duel 20×10 avec delta −151 k£/an).
   - *Point 2* : Couche `lines` relevée sans nécessité (town growth, abandon, retrait de ligne).
   - *Point 3* : Subvention perdue -> régénération complète parasite (`task_road.nut:30`).
   - *Point 4* : Matrice de dépendances fausse pour l'eau (`_c76GetModeDeps` : corrigée pour dépendre des villes et non des industries).
   - *Point 5 & Horloge C39.6* : Imputation dans le registre de passe C39.6 des intentions réactives (`reactive|<kind>`) et tranches de workers (`worker|<kind>`) sous `probe_scheduler`.
   - *Premiers selftests* intégrés dans `selftests.nut` (`_c80RunSelfTest` étapes 6, 7, 8 et `_c76RunSelfTest`).
3. **Correctifs C77 (commit `50c63bb` du 23/09) :**
   - `c77_targeted_build` (vérifie que la tête du vivier touche l'entité avant de construire).
   - `c77_fixes` (invalidation historique si fermeture d'industrie sans C76, clé de coalescence par entité, report N=3 des intentions si `_projects == null`, régénération synchrone derrière `rail_search` / `town_growth`).
4. **Revue du 30 septembre (Finding R5, commit `d15a5f4` / PR consolidation) :**
   - Exclusion des autotests C80/C76 après rechargement (`_loadedFromSave`) pour éviter l'écrasement de la file réactive et du worker restauré.

---

## 2. Analyse détaillée des 5 thèmes

### Thème 1 : Vivier injecté (candidats opportunistes C77 face aux régénérations complètes)

* **Documentation d'origine :** `docs/journaux/journal_2026-09-22_transfert_historique.md:87`, `journal_2026-09-22.md:52`, `revue_code_2026-09-22_integrale.md:262` (*« Limite connue : sous C77 sans C76, une régénération complète perd les candidats injectés. »*).
* **État du code actuel (fichier:lignes vérifiés) :**
  - `ai/OpexAI/orchestrator.nut:714–719` : L'intention réactive `c77_entity` instancie le worker `regen_candidates` (`state = intention.payload`).
  - `ai/OpexAI/orchestrator.nut:571–585` & `projects_generation.nut:184–189` : Le worker appelle `OpexRegenerateModeProjects`, qui délègue à `OpexApplyGeneratedModeProjects` (`projects_generation.nut:132–175`).
  - `ai/OpexAI/projects_generation.nut:146–148` : Lors d'une régénération ciblée (`targeted == true`), seuls les projets touchant l'entité sont remplacés. En revanche, lors d'une régénération de mode non-ciblée, la condition `local remove = project.mode == mode && !OpexProjectIsPersistentSpecial(project);` supprime tous les anciens projets du mode. Les candidats injectés par C77 ne sont pas protégés par `OpexProjectIsPersistentSpecial` (qui ne protège que les subventions, extensions routières et feeders, `projects_selection.nut:2087–2094`).
  - `ai/OpexAI/task_projects.nut:2204–2291` : Lors d'une régénération complète du vivier (`_rebuildProjects`), en régime de croisière (`stage == OPEX_STAGE_COMPLETE`), `prior` est forcé à `null` (ligne 2217). `OpexBuildProjects` reconstruit l'intégralité de `this._projects` à partir de zéro.
  - `ai/OpexAI/scheduler_tasks.nut:456–472` : Par défaut (`c76_regen_targeted=0`, `info.nut:350–357`), la tâche de fond `catalog` exécute inconditionnellement `this._rebuildProjects(fleetPlan)` à chaque passage (tous les ~30–45 jours).
* **Ce qui est déjà couvert par un test / selftest :**
  - `ai/OpexAI/selftests.nut:215–364` (selftest C80 étape 6) : Vérifie la sérialisation / désérialisation de l'intention `c77_entity` et du worker `regen_candidates` (absence de float, fidélité des tables).
  - `sweeps/test_c77_air_defensive_slot.py` : Valide la politique de priorité lexicographique du second créneau d'aéroport.
  - **Non couvert :** Aucun test ne vérifie le cycle de vie ou la rétention en mémoire des candidats injectés lors d'une régénération globale ultérieure.
* **Défaut concret & scénario reproductible :**
  - *Scénario :* Avec `c77_opportunistic_candidates=1` et `c76_regen_targeted=0` (défaut).
  - Une nouvelle industrie apparaît (`IndustryOpen`). L'événement injecte des candidats fret rail/route dans `this._projects.candidateGroups`.
  - Si cette opportunité n'est pas immédiatement finançable ou se classe derrière un autre projet prioritaire dans `best`, elle reste en attente dans le vivier.
  - 15 à 30 jours plus tard, la tâche de fond `catalog` est exécutée par l'ordonnanceur. Elle appelle `_rebuildProjects`.
  - `_rebuildProjects` écrase entièrement `this._projects`. Le candidat opportuniste injecté est **définitivement perdu**.
  - Si le fret ferroviaire n'est pas synchronisé sur le cargo de cette industrie (`this._lastFreightCargo` tournant sur un seul cargo à la fois), l'opportunité disparaît pour des mois ou des années.
* **Plus petite vérification ou fixture pour trancher :**
  - Fixture Python statique simulant l'injection d'un projet avec clé artificielle dans `projects.candidateGroups`, appel de `_rebuildProjects` avec `prior=null`, et vérification de la présence de la clé dans le résultat.
* **Signalement hors-périmètre :** N'interfère pas avec `air_catalog_c121.nut` (le catalogue AIR possède sa propre structure `OpexAirPlans`), mais les projets AIR opportunistes injectés subissent le même effacement global dans `_projects`.

---

### Thème 2 : Invalidation non-AIR (dépendances des modes rail, route, eau, matrices et invalidation historique)

* **Documentation d'origine :** `docs/17_evenements_regeneration.md` §2 & §6, `docs/18_orchestrateur_double_registre.md` §5.2, `docs/taches.md` (commit `ec9f91c`, points 2 et 4, et corrections mineures).
* **État du code actuel (fichier:lignes vérifiés) :**
  - `ai/OpexAI/orchestrator.nut:1108–1121` : Matrice `_c76GetModeDeps(mode)` :
    - `air` : `["towns", "engines.air", "lines"]`.
    - `rail_pax` : `["towns", "engines.rail", "lines"]`.
    - `rail_freight` : `["industries", "engines.rail", "lines"]`.
    - `road_pax` : `["towns", "engines.road", "lines"]`.
    - `road_freight` : `["industries", "engines.road", "lines"]`.
    - `water` : `["towns", "engines.water", "lines"]`. *(Vérifié : le Point 4 historique est bien corrigé, l'eau ne dépend plus des industries)*.
    - `rail` : `["towns", "industries", "engines.rail", "lines"]`.
    - `road` : `["towns", "industries", "engines.road", "lines"]`.
  - `ai/OpexAI/orchestrator.nut:1370–1388` : Prédicat `_c80ModeRegenModes()` :
    - Ne filtre que les couches `industries` et moteurs non-AIR.
    - Ligne 1375 : `if (r.towns > a.towns || r.lines > a.lines || r.engines.air > a.engines.air) return null;`. Si `lines` ou `towns` bouge, la régénération par mode est abandonnée et replie sur une régénération complète de tous les modes !
  - `ai/OpexAI/event_handlers.nut:305–326` : Dans `_onIndustryClose`, le correctif du commit `50c63bb` est bien présent : sous `!C76_REGEN_TARGETED`, l'invalidation historique (`_catalog._refreshIndustries()`, `_portfolioInvalidated = true`, réarmement de `catalog`/`projects` à `dueCycle=0`) est préservée.
  - `ai/OpexAI/task_air.nut:536, 973` et `task_road.nut:367` : Toute nouvelle ligne construite incrémente la couche `lines` (`_c76BumpLayer("lines", false)`).
* **Ce qui est déjà couvert par un test / selftest :**
  - `ai/OpexAI/selftests.nut:560–687` (`_c76RunSelfTest`) :
    - Lignes 603–620 : Bump de `towns` -> vérifie que `air` et `water` demandent une régénération.
    - Lignes 639–656 : Bump de `industries` -> vérifie formellement que `water` et `air` ne demandent PAS de régénération. Ce test valide directement l'exactitude de la matrice non-AIR.
* **Défaut concret & scénario reproductible :**
  - *Scénario :* Sous `C76_REGEN_TARGETED=1` et `C80_MODE_REGEN=1`.
  - Une ligne de bus urbain ou une extension est posée (`lines` est incrémentée).
  - Une nouvelle industrie ouvre (`industries` est incrémentée).
  - L'ordonnanceur évalue `_c80ModeRegenModes()` (`orchestrator.nut:1375`). Constatant que `r.lines > a.lines`, la fonction renvoie `null`.
  - L'ordonnanceur retombe sur `c76NeedFullRegen = true` (`scheduler_tasks.nut:393, 409`).
  - Conséquence : toute construction physique annule immédiatement le bénéfice du partitionnement non-AIR et déclenche une régénération globale exhaustive (coût plein de ~2,8 Mop).
* **Plus petite vérification ou fixture pour trancher :**
  - Test statique Python évaluant `_c80ModeRegenModes()` avec une fixture où `r.lines = 1, a.lines = 0` et `r.industries = 1, a.industries = 0`, démontrant le repli non désiré sur `null`.
* **Signalement hors-périmètre :** Aucun impact sur les modules internes du catalogue AIR isolé.

---

### Thème 3 : Intention mutatrice pendant worker actif

* **Documentation d'origine :** `docs/18_orchestrateur_double_registre.md` §3.1 & §14, `docs/taches.md` (commit `ec9f91c`, selftests à ajouter), `docs/journaux/23_nuit_2026-09-23.md:11` (commit `50c63bb`).
* **État du code actuel (fichier:lignes vérifiés) :**
  - `ai/OpexAI/orchestrator.nut:670–795` (`_dispatchReactiveIntention`) :
    - Lignes 674–687 : Si `intention.kind == "regen" && C76_REGEN_TARGETED`, la régénération s'exécute immédiatement en synchrone (`_c76DoFullRegen` ou `_c80DoModeRegen`), **avant** d'inspecter si un worker est actif.
    - Lignes 692–713 : Si `this._activeWorker != null` :
      - Seul `_activeWorker.kind == "regen_candidates"" renvoie `false` pour différer toutes les intentions via `_enqueueReactive`.
      - Si `intention.kind == "c77_entity"" et que le worker actif est `rail_search` ou `town_growth`, `OpexRegenEntitySync` est exécuté de manière synchrone (jusqu'à 10 000 pas) sans différer.
    - Lignes 720–741 (`c77_subsidy`) : **Aucune garde sur `this._activeWorker`**. Si `this._activeWorker` est `rail_search` ou `rail_stock`, `_c77InjectSubsidy` s'exécute immédiatement et mute `this._projects` et `this._ranked`.
    - Lignes 742–793 (`c77_build`) : **Aucune garde sur `this._activeWorker`**. Si un worker est actif, `c77_build` appelle immédiatement `this._tryBuildProjects`, pouvant lancer une construction physique et consommer la trésorerie.
* **Ce qui est déjà couvert par un test / selftest :**
  - `ai/OpexAI/selftests.nut:370–449` (`_c80RunSelfTest` étape 7) :
    - Teste l'injection d'une intention `kind = "regen"" pendant qu'un worker factice `noop` est actif.
    - **Limite majeure vérifiée :** Le test est conditionné par `if (!C76_REGEN_TARGETED)`. Or, sous `!C76_REGEN_TARGETED`, l'intention `regen` ne fait rien du tout (fallthrough ligne 794 renvoyant `true`). Le test valide donc un no-op.
    - Aucun test ne couvre l'arrivée d'une intention mutatrice réelle (`c77_subsidy`, `c77_build`) pendant qu'un vrai worker (`rail_search`, `rail_stock`) occupe le registre.
* **Défaut concret & scénario reproductible :**
  - *Scénario 1 (Concurrence trésorerie et état vivier) :*
    1. L'ordonnanceur lance un long A* rail (`_activeWorker.kind == "rail_search"`).
    2. Un événement `ET_SUBSIDY_OFFER` est reçu. `c77_subsidy` est enfilé.
    3. Au tick suivant, `_dispatchReactiveIntention` traite `c77_subsidy`. Faute de garde sur `_activeWorker`, `_c77InjectSubsidy` reconstruit le vivier et enfile `c77_build`.
    4. Au tick d'après, `c77_build` est dépilé et appelle `_tryBuildProjects`. La subvention est construite, consommant 50 k£ à 150 k£ de trésorerie.
    5. Lorsque `rail_search` achève son calcul A*, il tente de poser la ligne ferroviaire, mais la trésorerie a été préemptée -> échec `ERR_NOT_ENOUGH_CASH` après avoir dépensé des milliers d'opcodes de recherche.
  - *Scénario 2 (Écrasement sous C76) :*
    Sous `C76_REGEN_TARGETED=1`, une intention `regen` reçue pendant que le worker `regen_candidates` tourne exécute immédiatement `_c76DoFullRegen`, remplaçant `this._projects` sous les pieds du worker en cours.
* **Plus petite vérification ou fixture pour trancher :**
  - Test statique Python vérifiant que dans `_dispatchReactiveIntention`, toute intention mutatrice (`c77_subsidy`, `c77_build`, `regen`) vérifie `if (this._activeWorker != null)` et est correctement différée par `_enqueueReactive` au lieu d'être exécutée en parallèle.
* **Signalement hors-périmètre :** `c77_build` non différé peut déclencher un chantier AIR (construction d'aéroport) en concurrence avec une recherche rail active.

---

### Thème 4 : Cycle de subvention (injection, purge, cycle de vie et constructibilité)

* **Documentation d'origine :** `docs/17_evenements_regeneration.md` §6, `docs/journaux/journal_2026-09-22_transfert_historique.md:84`, `docs/taches.md` (commit `ec9f91c`, point 3 et selftests ; adoption du 11/10 de `subsidy_reselect_if_purged`).
* **État du code actuel (fichier:lignes vérifiés) :**
  - `ai/OpexAI/event_handlers.nut:329–350` : `_onSubsidyOffer` enregistre la subvention dans `this._activeSubsidies` et enfile `c77_subsidy`.
  - `ai/OpexAI/orchestrator.nut:900–935` : `_c77InjectSubsidy` :
    - Ligne 906 : `if (C121_CATALOG_AIR_FIRST_YEAR && C121_CATALOG_FIRST_YEAR_ACTIVE) return false;` (garde première année AIR).
    - Lignes 917–924 : génère les candidats via `OpexGenerateSubsidyCandidates`, les intègre dans `candidateGroups`, recompte et resélectionne.
    - Ligne 933 : enfile `c77_build` avec le `subsidyId`.
  - `ai/OpexAI/orchestrator.nut:763–793` : `c77_build` filtre la construction : elle n'a lieu que si la tête du vivier (`best[0]`) correspond bien au `subsidyId` concerné (`c77_targeted_build`).
  - `ai/OpexAI/event_handlers.nut:353–366` : `_c77RemoveSubsidy(subId)` supprime l'offre de `_activeSubsidies` et appelle `_purgeSubsidyFromProjects(subId)`.
  - Ligne 359 : `if (SUBSIDY_RESELECT_IF_PURGED && purged <= 0) return;` (adopté le 11/10 : court-circuite `OpexReselectProjects` si aucun candidat n'a été retiré).
  - `ai/OpexAI/task_road.nut:33–35` : Si une subvention est jugée périmée ou non rentable lors de la tentative de construction, `_portfolioInvalidated = true;` reste armé sous `!C76_LEAN_INVALIDATION`.
* **Ce qui est déjà couvert par un test / selftest :**
  - `ai/OpexAI/selftests.nut:451–558` (`_c80RunSelfTest` étape 8) :
    - Teste `_c77InjectSubsidy(999)` avec `_projects = null` -> renvoie bien `false` sans exception.
    - Teste `_purgeSubsidyFromProjects(77)` sur un vivier factice -> suppression chirurgicale de `best`, `road.best` et `candidateGroups["subsidy|77"]`.
    - Teste la résilience aux IDs invalides (`-1`, `null`, `999`).
  - `sweeps/test_c45_subsidy_persistence.py` : Valide la sérialisation de `activeSubsidies` dans `Save()` / `Load()` sous `save_full_state=1` et l'absence de drapeaux résiduels C42.
  - `sweeps/test_subsidy_reselect_if_purged.py` : Valide la déclaration et le fonctionnement du court-circuit de resélection sous `SUBSIDY_RESELECT_IF_PURGED`.
* **Défaut concret & scénario reproductible :**
  - *Scénario 1 (Perte silencieuse en première année AIR) :*
    Pendant l'an 1 (`C121_CATALOG_FIRST_YEAR_ACTIVE == true`), une subvention apparaît.
    `_onSubsidyOffer` l'enregistre et enfile `c77_subsidy`.
    Lorsque `c77_subsidy` est dépilé, `_c77InjectSubsidy` renvoie `false` (ligne 906).
    Mais dans `_dispatchReactiveIntention` (lignes 728–737), le retry n'est déclenché que si `!injected && this._projects == null`.
    Comme `this._projects` n'est pas `null` (le vivier AIR initial existe), l'intention n'est pas ré-enfilée : elle est définitivement acquittée (`return true;`, ligne 740).
    L'offre reste inscrite dans `this._activeSubsidies`, mais aucun candidat n'est généré et aucune tentative de construction n'aura lieu.
  - *Scénario 2 (Régénération complète parasite lors d'un échec routier) :*
    Sous `c76_lean_invalidation=0` (défaut), si la subvention expire pendant le devis de route (`task_road.nut:25`), `_portfolioInvalidated = true` force une reconstruction complète inutile du vivier.
* **Plus petite vérification ou fixture pour trancher :**
  - Fixture Python simulant le dispatch de `c77_subsidy` lorsque `C121_CATALOG_FIRST_YEAR_ACTIVE = true` et `_projects != null`, démontrant l'absence de retry et la perte de l'intention.
* **Signalement hors-périmètre :** Lien direct avec le module `C121_CATALOG_AIR_FIRST_YEAR` de `air_catalog_c121.nut` / `air_planning.nut`.

---

### Thème 5 : Save/Load (sérialisation de la file réactive, worker, révisions, intentions et autotests)

* **Documentation d'origine :** `docs/18_orchestrateur_double_registre.md` §9 & §10, `docs/19_rechargement_partie.md:27`, `docs/revue_code_2026-09-30.md:203–225, 1349` (Finding R5), `docs/journaux/23_nuit_2026-09-23.md:11` (commit `50c63bb`).
* **État du code actuel (fichier:lignes vérifiés) :**
  - `ai/OpexAI/persist.nut:190–223` : `OpexSaveReactiveQueue` et `OpexLoadReactiveQueue`.
  - `ai/OpexAI/persist.nut:225–280` & `282–295` : `OpexSaveActiveWorker` et `OpexLoadActiveWorker`.
  - `ai/OpexAI/persist.nut:836–840` : `Save()` persiste `saveObj.c80ReactiveQueue`, `saveObj.c80ActiveWorker`, et `saveObj.c76Revisions`.
  - `ai/OpexAI/persist.nut:756–758` : Dans `shortSave` (`save_full_state=0`), `c80ReactiveQueue` et `c80ActiveWorker` ne sont pas sauvés.
  - `ai/OpexAI/persist.nut:909–917` : `Load()` restaure la file, le worker et les révisions C76.
  - `ai/OpexAI/persist.nut:1057–1058` : `_reconcileAfterLoad()` réattache `this._activeWorker.ai <- this;` pour `regen_candidates`.
  - `ai/OpexAI/persist.nut:1128` : `_reconcileAfterLoad()` arme `this._c76ForceReloadRegen = true;` sous `C76_REGEN_TARGETED`.
  - `ai/OpexAI/selftests.nut:16–19, 563–565` : Gardes R5 : `if (this._loadedFromSave) return true;` empêchant les autotests d'écraser la file ou le worker restauré.
  - `ai/OpexAI/orchestrator.nut:728–737, 747–758` : Lors d'un reload, `this._projects` est `null`. Les intentions `c77_subsidy` et `c77_build` sont ré-enfilées jusqu'à 3 fois (`retries < 3`).
* **Ce qui est déjà couvert par un test / selftest :**
  - `sweeps/test_r5_reload_selftests.py` : Teste rigoureusement la présence et l'antériorité de la garde `_loadedFromSave` dans `_c80RunSelfTest` et `_c76RunSelfTest`, l'ordre d'initialisation dans `Start()`, et la reconnexion de `ai <- this`.
  - `ai/OpexAI/selftests.nut:215–369` (`_c80RunSelfTest` étape 6) : Aller-retour en mémoire de la sérialisation sans floats.
* **Défaut concret & scénario reproductible :**
  - *Scénario (Épuisement immédiat des 3 reports au rechargement) :*
    1. Une sauvegarde est effectuée avec une intention réactive en attente (`c77_build` ou `c77_subsidy`).
    2. La partie est rechargée. `Load()` restaure l'intention dans `_reactiveQueue`. `this._projects` vaut `null` (non sérialisé par conception).
    3. Au tick 1 de `Start()`, `_runOrchestratorTick` dépile l'intention. Constatant `_projects == null`, elle la ré-enfile avec `retries = 1`.
    4. Au tick 2, elle est re-dépilée : `retries = 2`.
    5. Au tick 3, re-dépilée : `retries = 3`.
    6. Au tick 4, `retries < 3` est FAUX : l'intention est considérée comme expirée et abandonnée (`return true;`, ligne 757).
    7. Or la reconstruction de `this._projects` par la tâche de fond `catalog` requiert un tour d'ordonnanceur complet (plusieurs dizaines de ticks à plusieurs jours de jeu).
    8. **Conséquence :** Les 3 reports s'épuisent en 4 ticks moteur (< 0,1 jour de jeu), bien avant que `catalog` ne s'exécute. Toute intention réactive sauvegardée est donc **systématiquement détruite** au rechargement.
* **Plus petite vérification ou fixture pour trancher :**
  - Test unitaire Python simulant `_runOrchestratorTick` sur 5 pas successifs avec `_projects == null` et une intention en file : compter le nombre de ticks avant disparition de l'intention.
* **Signalement hors-périmètre :** Aucun impact sur `air_catalog_c121.nut`.

---

## 3. Classement des 5 thèmes par risque réel

| Rang | Thème | Niveau de risque | Justification causale |
|:---:|---|:---:|---|
| **1** | **Thème 5 : Save/Load** | **ÉLEVÉ** | **Défaut structurel avéré à l'exécution :** Le mécanisme de report à 3 retries (`retries < 3`) s'épuise en 4 ticks de boucle principale, alors que la reconstruction de `_projects` par la file de fond prend des dizaines de ticks ou de jours. Toute intention `c77_build` ou `c77_subsidy` restaurée depuis une sauvegarde est donc systématiquement purgée et perdue. |
| **2** | **Thème 3 : Intention mutatrice pendant worker** | **ÉLEVÉ** | **Concurrence destructrice mémoire et trésorerie :** `c77_subsidy` et `c77_build` ne vérifient pas `_activeWorker`. Elles peuvent muter `_projects` et déclencher des chantiers physiques pendant qu'un long A* ferroviaire (`rail_search`) ou un worker de stock (`rail_stock`) calcule, provoquant des échecs de trésorerie sur le rail. De plus, sous C76, `regen` synchrone écrase le vivier en cours de régénération. |
| **3** | **Thème 1 : Vivier injecté** | **MOYEN** | **Écrasement silencieux des opportunités :** Dès que la tâche de fond `catalog` passe, `_rebuildProjects` réinitialise le vivier de zéro sans conserver les candidats ciblés injectés par `c77_entity`. Atténué au défaut courant car C77 est désactivé (`c77_opportunistic_candidates=0`), mais bloquant pour toute activation future de C77. |
| **4** | **Thème 4 : Cycle de subvention** | **MOYEN** | **Abandon silencieux en an 1 et régénération parasite :** Pendant l'an 1 AIR, `c77_subsidy` est rejeté sans retry car `_projects != null`, laissant l'offre inactive. Sous `c76_lean_invalidation=0`, toute subvention périmée pendant un devis route arme `_portfolioInvalidated=true` et force une régénération complète parasite. |
| **5** | **Thème 2 : Invalidation non-AIR** | **FAIBLE** | **Inefficacité en opcodes sans corruption d'état :** La matrice des dépendances non-AIR est saine (le bug de l'eau est corrigé et testé dans `_c76RunSelfTest`, et l'invalidation historique d'industrie fermée est restaurée). Le seul défaut est un repli excessif sur la régénération complète dès que la couche `lines` est incrémentée. |

---

## 4. Synthèse des vérifications / fixtures recommandées

Pour trancher formellement ces 5 points sans banc Docker coûteux :

1. **Fixture Save/Load (Thème 5) :** Micro-test simulant 10 ticks de `_runOrchestratorTick` avec `_projects = null` démontrant la perte de `c77_build` au 4ᵉ tick. Remplacement préconisé : ne pas décompter les retries par tick moteur, mais reporter tant que `this._projects == null` (ou borner par un délai en jours de calendrier).
2. **Fixture Intention mutatrice (Thème 3) :** Test statique d'assertion sur `orchestrator.nut` vérifiant que `c77_subsidy` et `c77_build` diffèrent leur exécution si `this._activeWorker != null` (comme le fait déjà `regen_candidates`).
3. **Fixture Vivier injecté (Thème 1) :** Test unitaire de `_rebuildProjects` vérifiant la préservation des entrées `c77|*` de `candidateGroups` au lieu de repartir d'un `prior=null` absolu.
4. **Fixture Subvention an 1 (Thème 4) :** Test unitaire simulant `_dispatchReactiveIntention("c77_subsidy")` sous `C121_CATALOG_FIRST_YEAR_ACTIVE=true` pour vérifier si l'intention doit être différée jusqu'à la fin de la première année plutôt que rejetée.
5. **Fixture Prédicat de mode (Thème 2) :** Vérification statique de `_c80ModeRegenModes()` pour autoriser `["rail", "road"]` même si `lines` a changé, dès lors qu'uniquement des lignes routières/ferroviaires ont été modifiées.

---

## Note de relecture (Claude, 12/10)

- **Vérifié dans `orchestrator.nut` (≈ l. 692–760)** : seul un worker `regen_candidates` fait différer les intentions ; `c77_subsidy` et `c77_build` s'exécutent pendant un `rail_search`/`rail_stock` (thème 3) ; les reports après rechargement sont comptés par passage dans la file réactive, borne 3, sans lien avec la reconstruction du vivier (thème 5).
- **Portée économique non mesurée.** Le thème 5 ne touche que les parties rechargées (aucune dans nos bancs). Pour le thème 3, que la construction C77 prenne la caisse d'un tracé rail en cours reste une hypothèse : il faudrait compter dans les journaux les `RAIL_ATTEMPT` refusés pour caisse juste après un `c77_build`.
- **Ordre proposé** : (1) mesure d'exposition du thème 3 sur les journaux existants ; (2) correctif thème 5 (report tant que `_projects == null`, borné en jours), sans effet sur les bancs, qualifiable par fixture + Save/Load ; (3) thème 4 an 1 (subvention perdue pendant la première année AIR). Thèmes 1 et 2 : bas.
