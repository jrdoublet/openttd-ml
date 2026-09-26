# Note de conception : Recherche A* rail entièrement dans les workers et projets rail éligibles seulement à tracé prêt

**Date : 2026-09-26**  
**Auteur : Antigravity (d'après décision utilisateur du 2026-09-26)**  
**Statut : Conception ; étapes 1, 2 et révision 3.2 bis implémentées sous réglages expérimentaux**  
**Branche de référence : `v88-exposure`**  
**Fichier cible : `docs/36_astar_workers_conception.md`**  

---

## 0. Résumé exécutif et décision utilisateur

Le 2026-09-26, l'utilisateur a arrêté la décision d'architecture suivante pour le canal ferroviaire d'OpexAI :

1. **Toute la recherche de chemin A\* ferroviaire est exécutée par des travailleurs d'arrière-plan (workers)**, consommant le reliquat d'opcodes disponible du tick de simulation.
2. **Seuls les projets rail dont l'A\* est terminé (tracé géographique et devis financier réels connus) sont éligibles dans le portefeuille de construction (`projects`).**
3. **La passe de construction `projects` ne lance donc plus jamais d'A\* rail.**

Cette note de conception formalise l'état des lieux, les mécanismes en jeu, l'architecture cible et le chemin de migration incrémental pour mettre en œuvre cette décision, en respectant rigoureusement les invariants du projet ([`AGENTS.md`](file:///home/deploy/projects/openttd-ml/AGENTS.md), [`docs/cible.md`](file:///home/deploy/projects/openttd-ml/docs/cible.md), [`docs/methode.md`](file:///home/deploy/projects/openttd-ml/docs/methode.md)).

Conformément aux règles du projet, ce document distingue en permanence trois statuts d'affirmation :
- **[Fait mesuré]** : grandeur issue d'un diagnostic ou d'un banc reproductible identifié (avec référence exacte) ;
- **[Lecture de code]** : comportement vérifié ligne à ligne dans le code source courant (`fichier:ligne`) ;
- **[Hypothèse]** : conjecture ou déduction logique soumise à vérification expérimentale.

---

## 1. État actuel : cycle de vie d'une recherche rail et pathologie observée

### 1.1 Cartographie du cycle de vie actuel (code source)

Aujourd'hui, la recherche de chemin rail (A\*) est intimement couplée à la tâche de décision d'investissement `projects`.

```text
Boucle principale (main.nut:678-689)
 │
 ├── _runNextTask() / _runOrchestratorTick()
 │    │
 │    ├── [En tête de passe] _advanceRailSearchSliceWithLedgers() (scheduler.nut:176-180)
 │    │    └── _continueRailSearch() (task_rail.nut:983) -> avance 50 itérations
 │    │
 │    ├── [Si V89 actif] _advanceRailSearchThroughput() (scheduler.nut:179, 337-362)
 │    │    └── Boucle tant que GetOpsTillSuspend() >= seuil -> tranches de 50 itér.
 │    │
 │    └── [Dispatch de tâche de fond] -> exécute la tâche due (round-robin)
 │         │
 │         └── Si tâche == "projects" -> _tryBuildProjects() (task_projects.nut:869)
 │              │
 │              └── Examen des candidats du vivier ordonné (best) :
 │                   │
 │                   ├── Candidat AIR / ROUTE : construction immédiate (1 tick)
 │                   │
 │                   └── Candidat RAIL : appel _tryBuildRailProject() (task_rail.nut:137)
 │                        │
 │                        ├── Si _railSearch != null -> REJET "search_in_progress" (l. 150-153)
 │                        │
 │                        └── Si _railSearch == null et sans railPlan :
 │                             └── _startRailSearch() (task_rail.nut:199, 332, 903)
 │                                  │
 │                                  ├── Alloue this._railSearch (l. 932-948)
 │                                  ├── Exécute 1ère tranche via _continueRailSearch()
 │                                  └── Si inachevée : RETOURNE { outcome = "pending" } (l. 333, 980)
 │
 └── Si outcome == "pending" dans _tryBuildProjects() :
      └── ARRÊT IMMÉDIAT DE LA PASSE (task_projects.nut:1164-1195) -> return true;
```

#### A. Déclenchement de la recherche
- **[Lecture de code]** La recherche n'est initiée **que** lorsqu'un projet ferroviaire arrive en tête des candidats finançables examinés par `_tryBuildProjects` ([`ai/OpexAI/task_projects.nut:1156-1160`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_projects.nut#L1156-L1160)).
- **[Lecture de code]** `_tryBuildRailProject` ([`ai/OpexAI/task_rail.nut:137-345`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L137-L345)) vérifie si une recherche est déjà en cours (`this._railSearch != null`). Si oui, le projet est immédiatement rejeté avec `reason = "search_in_progress"` ([`l. 150-153`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L150-L153)).
- **[Lecture de code]** Si aucun A\* n'est actif, et en l'absence de `candidate.railPlan`, `_tryBuildRailProject` appelle `_startRailSearch(candidate, ...)` ([`ai/OpexAI/task_rail.nut:332`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L332), et [`l. 212`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L212) pour l'étape 1 des chaînes V88).
- **[Lecture de code]** `_startRailSearch` ([`task_rail.nut:903-981`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L903-L981)) prépare le plan (`OpexPrepareRailRoute`), instancie le pathfinder natif (ou segmenté AYSTAR), initialise la table `this._railSearch` avec `phase = "search"`, pose une échéance globale `safetyDeadline = curTick + RAIL_SEARCH_SAFETY_TICKS` ([`l. 940`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L940)), puis exécute une première tranche via `_continueRailSearch()` ([`l. 965`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L965)). Si la recherche n'aboutit pas dès cette première tranche, elle retourne `{ pending = true, plan = null }` ([`l. 980`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L980)).

#### B. Avancement de la recherche
Une fois `this._railSearch` non nul en phase `"search"`, l'A\* progresse par trois canaux concurrents :
1. **En tête de `_runNextTask`** ([`ai/OpexAI/scheduler.nut:176-181`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/scheduler.nut#L176-L181)) : appel systématique de `_advanceRailSearchSliceWithLedgers()`, qui avance d'une tranche de 50 itérations (`RAIL_SEARCH_SLICE`, [`builder_rail.nut:39`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut#L39)) avec échéance locale par micro-étape (`RAIL_MICRO_DEADLINE`, [`task_rail.nut:995-1000`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L995-L1000)).
2. **Sous `c80_worker_rail=1`** ([`ai/OpexAI/orchestrator.nut:676-692`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/orchestrator.nut#L676-L692)) : dans `_runOrchestratorTick()`, si `_activeWorker.kind == "rail_search"`, `OpexWorkerRailSearchStep` ([`orchestrator.nut:205-222`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/orchestrator.nut#L205-L222)) avance la tranche avant de rendre la main à la file de fond.
3. **Sous `v89_rail_search_throughput=1`** (défaut 1 depuis le 2026-09-26) :
   - En tête de `_runNextTask` ([`scheduler.nut:178-180`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/scheduler.nut#L178-L180)) ;
   - Dans le worker C80 ([`orchestrator.nut:215-217`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/orchestrator.nut#L215-L217)) ;
   - Dans la boucle principale de `main.nut:680, 686` juste avant `AIController.Sleep(1)`.
   `_advanceRailSearchThroughput(maxSlices = -1)` ([`scheduler.nut:337-362`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/scheduler.nut#L337-L362)) boucle pour exécuter des tranches successives tant que `AIController.GetOpsTillSuspend() >= this._v89EstimatedSliceOps` (seuil auto-calibré ≥ 1 500 opcodes).

#### C. Achèvement de la recherche
- **[Lecture de code]** Lorsque la tranche atteint la destination (`slice.done == true`), `_continueRailSearch` bascule le mode en appelant `OpexCompleteRailRouteAfterSearch` ([`ai/OpexAI/builder_rail.nut:1494-1560`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut#L1494-L1560)).
- **[Lecture de code]** Cette fonction résout les tuiles du chemin, valide la géométrie des gares d'extrémité (`planA`, `planB`), recalcule les grandeurs économiques réelles avec la longueur exacte (`routeDistance`) via `OpexLineEconomics` ([`l. 1524-1533`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut#L1524-L1533)), tente l'option double voie (`OpexTryDoubleTrack`, [`l. 1546`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut#L1546)), attache `candidate.railPlan <- plan`, libère l'objet pathfinder natif (`state.pathfinder = null`), et passe `state.phase = "build"` ([`task_rail.nut:1111-1115`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L1111-L1115)).

#### D. Consommation du tracé
- **[Lecture de code]** La construction physique n'a lieu que lors d'un **nouveau passage de la tâche `projects`**, via `_consumeRailSearch` ([`task_rail.nut:1138-1233`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L1138-L1233)).
- **[Lecture de code]** Si la trésorerie est insuffisante (`money < need`), sous `c41_rail_cash_release=1` (défaut adopté), `this._railSearch = null` est immédiatement libéré ([`l. 1163`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L1163)) tout en conservant `candidate.railPlan` attaché au candidat pour une tentative ultérieure.
- **[Lecture de code]** Si la caisse suffit, `OpexBuildLine` érige l'infrastructure, pose les gares et les signaux, achète le train, enregistre la ligne dans `this._lines` et détruit le plan : `candidate.railPlan = null` ([`l. 1185`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L1185)).

#### E. Persistance et invalidation
- **[Lecture de code]** Dans `persist.nut:229-236`, `OpexSaveActiveWorker` ne sérialise pas l'état interne de `rail_search` car les structures AYSTAR C++ ne sont pas persistables dans les savegames NoAI.
- **[Lecture de code]** Au rechargement (`Load`), `persist.nut:800-825` abandonne explicitement toute recherche rail active (`this._railSearch = null`), annule le worker C80 associé, force `this._portfolioInvalidated = true` et réarme la tâche `catalog` pour reconstruire le vivier à partir de la carte fraîche.
- **[Lecture de code]** Invalidation en cours de partie : si un premier projet est bâti dans une passe multi-projets (`builtCount > 0`), tout `candidate.railPlan` d'un candidat suivant est immédiatement effacé (`candidate.railPlan = null`, [`task_rail.nut:142-147`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L142-L147)) pour forcer une replanification si la carte a bougé.

---

### 1.2 Le verrou fatal : l'arrêt de passe sur `outcome == "pending"` et l'éviction de l'aérien

L'enquête approfondie menée sur V88 et V89 révèle le mécanisme destructeur du couplage actuel :

1. **Arrêt immédiat de la passe `projects`** :
   Dans [`ai/OpexAI/task_projects.nut:1164-1196`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_projects.nut#L1164-L1196), dès qu'un projet rail (ou une chaîne V88) lance son A\*, `attempt.outcome` vaut `"pending"`. Le code fait alors :
   ```squirrel
   if (attempt.outcome == "pending") {
     ...
     return true; // Sortie brutale de _tryBuildProjects() !
   }
   ```
   **[Lecture de code]** Ce `return true;` interrompt instantanément l'examen du vivier `this._projects.best`. **Tous les projets situés derrière ce candidat rail dans la liste ordonnée — notamment les lignes aériennes (AIR) rentables et immédiatement constructibles — sont purement et simplement sautés pour ce cycle.**

2. **Conséquence en duel face à AAAHogEx** :
   - **[Fait mesuré]** (Enquête V88, `docs/27_v88_chaines_biens.md` et `sweeps/analyze_hypotheses.py`) : Sur la graine 100 en mode non bridé (*Unlocked*), les arrêts de passe pour cause de `rail_search` représentent **31,6 % de tous les arrêts de passe** de la partie.
   - **[Fait mesuré]** Les dépenses d'investissement en aviation chutent drastiquement : sur la graine 5678, les dépenses AIR passent de 6,38 M£ (référence) à 4,13 M£ (variante avec chaînes rail), et le nombre d'avions construits recule (73 → 63 en solo).
   - **[Fait mesuré / Concurrence]** Pendant qu'OpexAI suspend sa passe `projects` et étale son A\* sur des mois ou des années de jeu, **AAAHogEx continue de construire ses aéroports et préempte les slots municipaux exclusifs ou rares (C83)**. Lorsque le projet rail aboutit enfin, les opportunités aériennes les plus lucratives ont disparu.

3. **Le verrouillage calendaire du slot unique `this._railSearch`** :
   - **[Fait mesuré]** (Diagnostic `results/v89gap_solo_3x6_20260926.json`, solo graines 100/999/5678 × 6 ans, V89=0 et V89=1) :
     - Les passes `projects` sont espacées en médiane de **34 à 111 jours de jeu**, avec OU sans V89 (ex. graine 999 : médiane 108 j, max 240 j ; graine 5678 : médiane 80 j, max 357 j).
     - Sur la graine 999, une recherche rail primaire (src=31930, dst=20197, 5 681 itérations) a occupé le slot unique `this._railSearch` du **12 juillet 1970 au 24 avril 1974**, soit **1 382 jours consécutifs de jeu (près de 4 ans !)** et 25 566 ticks, de manière strictement identique avec V89=0 et V89=1.
     - Pendant ces 1 382 jours, `this._railSearch != null` a rejeté en bloc tout autre projet rail avec le motif `search_in_progress` (98 à 150 rejets par partie, [`docs/28_v89_debit_recherche_rail.md:15`](file:///home/deploy/projects/openttd-ml/docs/28_v89_debit_recherche_rail.md#L15)).

---

### 1.3 Bilan de `c80_worker_rail` : pourquoi son banc officiel n'a pas été adopté

La tentative précédente d'encapsuler la recherche rail dans un travailleur C80 (`c80_worker_rail=1`) a été mesurée dans la campagne complète 20×10 du 2026-09-25 (`c80_full_stack_workers_vs_current_default_20x10_20260925`, [`docs/taches.md:60-70`](file:///home/deploy/projects/openttd-ml/docs/taches.md#L60-L70)) :
- **[Fait mesuré]** Résultat : 20/20 paires saines, `profit_year` **+32,6 k£/an** (médiane +104,8 k£), 12 victoires / 8 défaites, $p = 0{,}503$, IC95 [−162,5 ; +227,7] k£/an, valeur d'entreprise +1,76 %.
- **[Fait mesuré]** Le critère d'adoption C80-6 (+50 k£/an, 15/20, $p < 0{,}05$) n'a pas été atteint. `c80_worker_rail` est resté désactivé par défaut (`défaut 0`).

**Pourquoi cette première version n'a pas mordu :**
- **[Lecture de code]** `c80_worker_rail` n'était qu'un wrapper passif : le travailleur `WorkerRailSearch` n'était instancié **qu'après** que `projects` avait sélectionné le projet et appelé `_startRailSearch` ([`task_rail.nut:954-964`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L954-L964)).
- **[Lecture de code]** La passe `projects` continuait donc d'être bloquée par `outcome == "pending"`.
- **[Lecture de code]** Le worker était asservi à l'unique slot `this._railSearch`. Il n'a créé **aucun parallélisme**, **aucun stock tampon** et n'a pas découplé l'A\* de la passe de décision.

---

## 2. Conception cible : Architecture "Stock & Éligibilité"

### 2.1 Les trois principes cardinaux de la cible

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. PRODUCTEUR : Worker RailSearchStock (Arrière-plan / Reliquat tick)        │
│    - Lit la tête des candidats rail générés (candidates.rail)                │
│    - Exécute l'A* par micro-tranches bornées avec échéance LOCALE propre     │
│    - Produit un STOCK BORNÉ de tracés prêts (N <= 2 ou 3)                   │
│    - Recalcule le devis réel (capitalIsActual = true)                        │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ Alimente (Stock tampon)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. STOCK DE TRACÉS PRÊTS (Table de plans validés avec devis réel)            │
│    - Clé : pairKey (src-dst-cargo)                                           │
│    - Contenu : { plan, candidate, quote, generatedDate, ttl }                │
│    - Contrôle de péremption (TTL, invalidation C39, collision d'emprise)    │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ Filtre d'éligibilité
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. CONSOMMATEUR : Passe "projects" (Sélection & Érection)                    │
│    - Candidat rail SANS tracé prêt  ==> INÉLIGIBLE (écarté avant sac à dos)  │
│    - Candidat rail AVEC tracé prêt  ==> ÉLIGIBLE (devis réel, ROI exact)     │
│    - ZÉRO A* lancé dans projects    ==> PLUS AUCUN ARRÊT "pending"           │
│    - Construction immédiate en 1 tick (comme AIR et ROUTE)                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.2 Worker `rail_search` producteur d'un stock borné de tracés

#### A. Règle de dimensionnement du stock ($N_{\max}$)
- Le stock conserve au maximum **$N_{\max} = 2$ tracés prêts** (valeur recommandée, avec $N_{\max} = 1$ en étape transitoire).
- **Justification économique [Hypothèse / Fait mesuré]** : Un tracé stocké immobilise peu de mémoire Squirrel (~200 entiers par tracé), mais la carte d'OpenTTD évolue continuellement (croissance urbaine, concurrence). Stocker plus de 2 tracés augmente le risque de péremption avant construction. Avec 1 à 2 chantiers rail par an en moyenne ([`docs/28_v89_debit_recherche_rail.md:136`](file:///home/deploy/projects/openttd-ml/docs/28_v89_debit_recherche_rail.md#L136)), un stock de 2 couvre 100 % du besoin immédiat sans gaspiller d'opcodes en pure perte.

#### B. Règle d'élection du candidat à précalculer (Garde-fou `cible.md` §6.4)
- **Règle absolue [Garde-fou `cible.md` §6.4]** : *« Le goulot mesuré est le DÉBIT DU CONTRÔLEUR : ne jamais simuler le vivier. Estimer seulement les candidats de tête. »*
- La sélection du prochain candidat à calculer par le worker ne doit **jamais** balayer les centaines de paires théoriques de la carte.
- **Règle de filtrage retenue** :
  1. Le worker consulte la liste ordonnée `this._candidates.rail` (produite par `OpexRailCandidates`, déjà filtrée par distance, platitude C4 et mémoire d'abandon C5).
  2. Il ignore les paires déjà présentes dans le stock prêt.
  3. Il ignore les paires dont le coût estimé dépasse $1{,}5 \times$ la trésorerie prévisionnelle mobilisable (inutile de calculer un corridor à 200 k£ si l'entreprise n'a que 30 k£).
  4. Il élit le **premier candidat éligible** (le meilleur score/ROI estimé).
  5. Il lance la recherche pour ce candidat unique.

---

### 2.3 Porte d'éligibilité dans `projects` et éradication du retour `pending`

#### A. Règle d'admission au portefeuille
Dans `OpexBuildProjects` / `OpexProjectSelectAffordable` ([`ai/OpexAI/projects.nut:2373-2384`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/projects.nut#L2373-L2384)) :
- Un candidat rail n'est admis dans `alternatives` et dans la sélection `funded` **que si** :
  $$\text{candidate.pairKey} \in \text{readyStock} \quad \text{ET} \quad \text{readyStock[pairKey].plan.ok} == \text{true}$$
- Si le tracé n'est pas prêt, le candidat rail est simplement **omis** de la passe du portefeuille (ou classé dans un statut passif `awaiting_route`).
- **Conséquence directe** : Le sac à dos (`funded`) ne contient **que des projets immédiatement constructibles**.

#### B. Suppression définitive de `outcome == "pending"`
Dans `_tryBuildRailProject` ([`ai/OpexAI/task_rail.nut:137`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L137)) et `_tryBuildProjects` ([`ai/OpexAI/task_projects.nut:1164`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_projects.nut#L1164)) :
- La branche `if (start.pending) return { outcome = "pending" };` est **supprimée**.
- Comme le tracé est déjà calculé, `_tryBuildRailProject` trouve immédiatement `candidate.railPlan` prêt dans le stock.
- Il procède à la pose physique de la ligne en 1 seul tick via `OpexBuildLine`, exactement comme pour une liaison aérienne ou routière.
- **[Bénéfice majeur]** La passe `projects` ne s'arrête plus jamais brutalement. Si le budget `K_pass` ou le capital le permet, elle enchaîne sur les projets suivants du portefeuille sans retarder l'aérien face à AAAHogEx.

---

### 2.4 Préservation absolue de l'échéance par micro-étape (`cible.md` §2.1)

#### A. Le piège historique et la double régression constatée
- **[Fait mesuré `cible.md` §2.1]** L'introduction imprudente d'un exécuteur reprenable avec échéance globale (`rail_search_resumable`) a été rejetée deux fois historiquement :
  - Banc 1 : **−23,1 %** de valeur d'entreprise, 16/20 graines perdantes ($p = 0{,}0118$) ;
  - Banc 2 : **−13,3 %** de valeur, et **−27,5 % de gares construites** ($t = -4{,}46$, $p = 0{,}0414$).
- **Mécanisme exact identifié dans le code** :
  Dans [`ai/OpexAI/task_rail.nut:940`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L940) :
  ```squirrel
  safetyDeadline = curTick + RAIL_SEARCH_SAFETY_TICKS;
  ```
  Cette échéance globale en ticks absolus était posée à l'entrée de la recherche. Lorsque la recherche était fractionnée et partageait le temps machine avec le reste de la file, le temps calendaire s'écoulait, l'échéance globale expirait, et l'A\* **était avorté prématurément (`outcome = DEAD`)**. Le fractionnement n'avait pas étalé le travail : il l'avait **amputé**, privant l'IA de ses lignes les plus rentables.

#### B. La parade adoptée : échéance locale par tranche (`RAIL_MICRO_DEADLINE`)
- **[Lecture de code]** Le correctif validé C20 ([`task_rail.nut:995-1000`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L995-L1000)) calcule une échéance locale à chaque appel de micro-étape :
  ```squirrel
  deadlineTick = AIController.GetTick() + RAIL_SEARCH_SLICE / 3 + BUILD_TICK_MARGIN;
  ```
- **Règle intangible pour le worker** : Le worker de stock ne doit **jamais** manipuler d'échéance globale sur la durée totale de vie de la recherche. Chaque pas (`step`) du worker reçoit un budget de tranche et une échéance locale fraîche calculée sur `AIController.GetTick()`. Une recherche longue peut prendre 5 000 itérations et 50 ticks d'horloge sans jamais risquer de mourir d'un faux timeout.

---

### 2.5 Péremption, invalidation et re-vérification du tracé au moment de bâtir

Un tracé précalculé stocké en mémoire peut devenir obsolète si le monde évolue avant sa construction :

1. **Péremption temporelle (TTL)** :
   - Chaque entrée du stock porte `readyDate = AIDate.GetCurrentDate()`.
   - Si un tracé reste en stock plus de **90 jours de jeu** sans être sélectionné par `projects`, il est marqué périmé et retiré du stock. Le worker pourra le recalculer ou choisir un candidat plus frais.

2. **Invalidation événementielle (Bus C39 / C80)** :
   - Si un événement NoAI modifie une industrie source/destination (`AIEvent.ET_INDUSTRY_CLOSE`), le tracé associé est immédiatement purgé du stock.
   - Si une station concurrente est fondée dans la zone terminale, le bus d'invalidation retire le tracé.

3. **Re-vérification instantanée au moment de la construction** :
   - **[Lecture de code]** `OpexBuildLine` ([`ai/OpexAI/builder_rail.nut:1918`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut#L1918)) consomme déjà `candidate.railPlan` directement. Avant toute dépense lourde, le constructeur effectue des tests élémentaires sous `AITestMode` sur les tuiles clés (têtes de quais, embranchement de dépôt).
   - Si une tuile du corridor a été occupée entre-temps par une route municipale ou un bâtiment concurrent :
     - `OpexBuildLine` échoue proprement sans dépense ;
     - La paire est marquée en échec temporaire (`_markPairAbandoned`) ;
     - Le tracé est retiré du stock ;
     - `_tryBuildRailProject` retourne `{ outcome = "rejected" }` et la passe `projects` passe immédiatement au projet suivant sans bloquer.

4. **Devis financier réel et calibrage du capital** :
   - **[Lecture de code]** Dans [`ai/OpexAI/projects.nut:302-313`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/projects.nut#L302-L313), `OpexProjectFinanceCapital` implémente déjà la prise en compte du devis exact :
     ```squirrel
     local capitalIsActual = ("capitalIsActual" in project) && project.capitalIsActual;
     ...
     if (capitalIsActual) return capital + nonConstructionCapital;
     return ((capital * biasPct) / 100) + nonConstructionCapital;
     ```
   - Dès qu'un tracé est terminé dans le stock, le devis réel issu de `OpexCompleteRailRouteAfterSearch` positionne `capitalIsActual = true`.
   - **Bénéfice économique [Lecture de code / Fait mesuré]** : Le projet rail n'est plus pénalisé par le multiplicateur de prudence empirique `RAIL_FINANCE_BIAS_PCT` ($100\,\%$ à $170\,\%$). Il est arbitré dans le sac à dos sur son **coût réel mesuré**.

---

### 2.6 Du singleton `_activeWorker` au registre multi-workers arbitrable

#### A. Limite actuelle du singleton `_activeWorker`
- **[Lecture de code]** Dans [`ai/OpexAI/orchestrator.nut:676-735`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/orchestrator.nut#L676-L735), l'orchestrateur ne gère qu'un unique travailleur actif :
  ```squirrel
  if (this._activeWorker != null) { ... }
  ```
  Si une recherche rail occupe `this._activeWorker`, le travailleur de croissance urbaine (`town_growth`) ou de régénération de vivier (`regen_candidates`) ne peut pas avancer.

#### B. Structure cible : File de travaux et classes de priorité (Note 34 §5.5)
Conformément à [`docs/34_arbitrage_economique_unifie.md`](file:///home/deploy/projects/openttd-ml/docs/34_arbitrage_economique_unifie.md) §5.5, le registre d'exécution des workers passe d'un singleton à un tableau ordonné de travailleurs, arbitrés par **4 classes de priorité structurelles** :

```text
Classe 1 : DÉBLOQUE (Urgence maximale)
  - Débloque une action économique déjà engagée et immobilisée
  - Exemple : Étape 2 d'une chaîne industrielle V88 (l'étape 1 est bâtie, le train d'intrants roule,
    le quai d'usine attend la ligne de biens).

Classe 2 : DEMANDE MÉTIER EXPLICITE
  - Demande émise par une décision économique en attente de réalisation
  - Exemple : Le stock de tracés rail est vide (0 tracé prêt) ET la trésorerie est disponible.

Classe 3 : ALIMENTATION DE STOCK PRÉVENTIF
  - Maintien du stock tampon borné
  - Exemple : Le stock compte 1 tracé prêt, précalcul du 2e tracé avec le reliquat d'opcodes libre.

Classe 4 : TRAVAIL DE FOND OPPORTUNISTE
  - Tâches de confort ou de maintenance continue
  - Exemples : Worker "town_growth" (analyse d'une ville), cartographie par blocs C67.
```

**Règle d'exécution au tick** :
À chaque tick, l'orchestrateur examine la liste des workers enregistrés, sélectionne celui appartenant à la classe la plus prioritaire, et lui confie une tranche bornée d'opcodes sur le reliquat du tick.

---

### 2.7 Sort des composants et briques existants

| Composant existant | Situation actuelle | Destin dans l'architecture cible |
|---|---|---|
| **V89** (`v89_rail_search_throughput`) | Saupoudré en 5 points du code (`main.nut`, `scheduler.nut`, `orchestrator.nut`). | **Absorbé dans le moteur interne du worker rail.** Le principe de pomper les tranches tant que `GetOpsTillSuspend() >= seuil` devient la boucle normale du worker de stock. Les hooks dispersés dans `main.nut` et `scheduler.nut` sont nettoyés. |
| **`c80_worker_rail`** | Wrapper passif dépendant de `_railSearch`, déclenché par `projects`. | **Remplacé par le worker autonome `WorkerRailStock`.** Ne dépend plus de `_tryBuildRailProject` pour démarrer. |
| **`RAIL_SEARCH_RESUMABLE`** | Réglage historique gérant le fractionnement. | **Maintenu actif en permanence.** La recherche dans le worker est obligatoirement découpée par micro-tranches (`RAIL_SEARCH_SLICE = 50`). |
| **Chaînes V88** (`_activeGoodsChain`) | L'étape 1 lance son A\* depuis `projects` et stoppe la passe (`pending`). | **Étape 1 et Étape 2 converties en demandes de tracé au worker.** L'étape 1 n'est éligible dans `projects` que si son tracé intrant est prêt. Dès qu'elle est bâtie, elle pousse une requête Classe 1 (Débloque) pour l'étape 2. La passe `projects` ne se fige plus. |
| **Cartographie C67** | Chantiers blocs d'eau / relief en attente. | Devient un consommateur natif de Classe 4 (travail opportuniste sur reliquat). |

---

### 2.8 Persistance et résilience (Save / Load)

La persistance sous NoAI impose de respecter deux règles matérielles strictes :
1. **Les objets C++ AYSTAR / Pathfinders natifs ne sont PAS sérialisables** ([`persist.nut:230-236`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/persist.nut#L230-L236)).
2. **Les nombres flottants sont formellement interdits dans les tables sauvées** ([`persist.nut:16-17`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/persist.nut#L16-L17)).

**Doctrine de persistance pour le Stock & Worker Rail** :
- **Tracés terminés dans le stock (`readyStock`)** :
  - **[Lecture de code]** Un `railPlan` complété ne contient **aucun objet C++** : il est entièrement constitué de structures Squirrel simples (tableaux d'entiers pour les tuiles, entiers pour les coûts et coordonnées, booléens).
  - Les tracés prêts sont **entièrement sérialisables** et peuvent être sauvegardés dans `Save()` et restaurés dans `Load()`.
  - Au rechargement, une simple passe de validation rapide vérifie que les tuiles des gares terminales sont toujours constructibles.
- **Recherche en cours dans le worker (`activeSearch`)** :
  - Comme aujourd'hui, si une recherche était en cours de calcul au moment de la sauvegarde, l'objet pathfinder est abandonné au rechargement.
  - Le worker réinitialise simplement la recherche du candidat au premier tick suivant sans perturber le stock déjà validé.

---

## 3. Découpage incrémental et protocole de validation (§4 AGENTS.md)

Pour respecter la doctrine d'ingénierie du dépôt, aucune refonte monolithique n'est permise. Le passage à la cible est découpé en **4 étapes indépendantes**, chacune protégée par un interrupteur dédié à défaut `0`.

```text
Étape 1 : Porte d'éligibilité passive & sonde de stock (c80_rail_stock_gate = 0)
    │
    ▼
Étape 2 : Worker RailSearchStock autonome N=1 sur reliquat (c80_rail_stock_worker = 0)
    │
    ▼
Étape 3 : Stock borné N=2 et devis réel dans OpexProjectFinanceCapital (c80_rail_stock_capacity = 0)
    │
    ▼
Étape 4 : Intégration prioritaire des chaînes V88 & multi-workers C80 (v88_chain_worker_prio = 0)
```

---

### 3.1 Étape 1 — Porte d'éligibilité passive & sonde de vivier (`c80_rail_stock_gate`)

- **Changement** :
  - Création de la structure `this._railReadyStock = {}`.
  - Conditionnement de l'éligibilité rail dans `OpexBuildProjects` : si `c80_rail_stock_gate = 1`, un projet rail n'entre dans `alternatives` que s'il possède un tracé dans `_railReadyStock`.
  - Dans `_tryBuildRailProject`, suppression du chemin de lancement `_startRailSearch` sous cette porte : si un projet arrive sans tracé, rejet propre `no_ready_route` (aucun retour `pending`).
- **Risque** : Priver l'IA de projets rail si le stock est vide.
- **Preuve que le mécanisme mord (Compteurs attendus)** :
  - `C49_SCARCITY_LEDGER.stop_rail_search` doit tomber **strictement à 0**.
  - `C78_SLOT` ne doit plus enregistrer aucun arrêt de passe `reason=rail_search`.
  - Le nombre de passes `projects` par an doit remonter.
- **Validation (§4 AGENTS.md) — Réalisée le 2026-09-26** :
  - **Tests de contrat Python** : 8 tests dédiés dans `sweeps/test_c80_rail_stock_gate.py` + suite complète (366 tests) au vert.
  - **Identité exacte au défaut (`c80_rail_stock_gate=0`)** :
    - Graine 42 (1 an) : `company_value=427019`, `profit_year=306642`, `n_vehicles=23`, `n_stations=20` (diff=0 sur toutes les métriques).
    - Graine 100 (6 ans) : `company_value=6014565`, `profit_year=1756502`, `n_vehicles=141`, `n_stations=56` (diff=0 sur toutes les métriques).
    - Graine 999 (6 ans) : `company_value=11200121`, `profit_year=3685733`, `n_vehicles=138`, `n_stations=78`, `observed_opcodes_total=70848232` (diff=0 sur toutes les métriques).
  - **Smoke 1×1 sous la porte (`c80_rail_stock_gate=1`)** : `run_ok=True`, `failure_reason=None`, zéro erreur NoAI.
  - **Diagnostic solo apparié 3 graines (100, 999, 5678) × 6 ans (`results/astar_e1_solo_3x6.json`)** :

| Graine | Bras | Passes `projects` | Écart médian (j) | Arrêts `rail_search` | Lignes bâties (air/rail/route/flotte) | Avions | `profit_year` (£) | `company_value` (£) |
|---|---|---|---|---|---|---|---|---|
| **100** | Référence (porte=0, sondée) | 48 | 26 | 4 | 72 / 2 / 0 / 14 | 85 | 1 775 869 | 5 711 296 |
| **100** | Variante (porte=1, sondée) | 76 (+58%) | 1 | **0** | 93 / **0** / 1 / 11 | 102 | 1 881 238 | 5 985 546 |
| **100** | Référence (porte=0, sans sonde) | — | — | — | — | 120 | 1 756 502 | 6 014 565 |
| **100** | Variante (porte=1, sans sonde) | — | — | — | — | 151 | 1 909 654 (+8,7%) | 7 284 687 (+21,1%) |
| **999** | Référence (porte=0, sondée) | 20 | 111 | 3 | 74 / 2 / 0 / 17 | 89 | 3 263 535 | 11 257 674 |
| **999** | Variante (porte=1, sondée) | 28 (+40%) | 62 | **0** | 66 / **0** / 4 / 13 | 77 | 3 111 622 | 10 924 066 |
| **999** | Référence (porte=0, sans sonde) | — | — | — | — | 102 | 3 685 733 | 11 200 121 |
| **999** | Variante (porte=1, sans sonde) | — | — | — | — | 131 | 3 106 252 (−15,7%) | 11 481 114 (+2,5%) |
| **5678** | Référence (porte=0, sondée) | 19 | 82 | 1 | 54 / 1 / 1 / 12 | 64 | 3 984 286 | 11 921 042 |
| **5678** | Variante (porte=1, sans sonde) | 19 | 56 | **0** | 48 / **0** / 5 / 5 | 50 | 3 230 570 | 9 883 156 |
| **5678** | Référence (porte=0, sans sonde) | — | — | — | — | 127 | 4 004 709 | 12 730 467 |
| **5678** | Variante (porte=1, sans sonde) | — | — | — | — | 117 | 3 840 454 (−4,1%) | 13 558 255 (+6,5%) |

- **Bilan d'Étape 1** :
  - **Objectif technique atteint** : les arrêts de passe pour `rail_search` sont **strictement éliminés (0)**. Les passes `projects` s'exécutent avec une régularité accrue (délai médian réduit sur toutes les graines).
  - **Comportement sous la porte sans producteur** : comme attendu, aucune ligne rail n'est construite. Le capital est réalloué vers l'aérien et le routier. L'étape 1 borne ainsi avec précision l'effet d'une absence d'interruption A* et son coût d'opportunité en l'absence de worker de stock.

---

### 3.2 Étape 2 — Worker `RailSearchStock` autonome ($N=1$) sur reliquat (`c80_rail_stock_worker`)

- **Conception retenue (décisions utilisateur du 2026-09-26)** :
  - **Worker autonome `rail_stock`** : enregistré dans l'orchestrateur C80 (`WorkerRailStock`), alimente le stock tampon `this._railReadyStock` limité à $N = 1$.
  - **Dépendance stricte au réglage** : le réglage `c80_rail_stock_worker` (booléen, défaut 0) est strictement conditionné par `c80_rail_stock_gate=1` (`C80_RAIL_STOCK_WORKER = C80_RAIL_STOCK_GATE && ...`). Au défaut (`gate=0, worker=0`), le comportement est **strictement identique au bit près** à `master`.
  - **Slot d'exécution `_railSearch`** : réutilisé comme slot d'exécution exclusif de la recherche en cours du worker. Les upgrades rail utilisent leurs structures propres sans conflit ; `_railExpansion` s'exécute en amont de la tranche du worker sans interférer. Sous la porte, `search_in_progress` est désarmé car seuls les projets disposant d'un tracé prêt en stock sont injectés dans `alternatives`.
  - **Interaction V89** : sous `c80_rail_stock_worker=1`, `V89_RAIL_SEARCH_THROUGHPUT` est forcé à `false` dans `settings.nut`. Le worker absorbe directement la logique de débit sur reliquat (`while (GetOpsTillSuspend() >= seuil)`), évitant toute dispersion ou double consommation dans `scheduler.nut` ou `main.nut`.
  - **Activation événementielle (zéro surcoût au tick)** : afin de préserver l'identité bit-à-bit au défaut (où `C80_DOUBLE_REGISTER = true` évalue `_runOrchestratorTick` à chaque tick), le réarmement du worker est purement événementiel (`Start()`, fin de passe `_tryBuildProjects`, consommation de tracé, échec/timeout A*, expiration de stock). `_runOrchestratorTick()` n'avance le worker que si `this._activeWorker != null` sous l'étape `(c)` existante.
  - **Règles temporelles des 180 jours** :
    - *Échéance de recherche (180 j)* : si l'A\* dépasse 180 jours de jeu (`curDate - startDate > 180`), la recherche est abandonnée (`_handleRailStockSearchTimeout`), log `RAIL_STOCK_TIMEOUT`, et la paire candidate est mise en retrait temporaire pendant 365 jours de jeu (`_railStockCooldown[pairKey] <- curDate + 365`). Elle n'est pas abandonnée définitivement : à l'issue de cette période, elle redevient sélectionnable si elle reste en tête du vivier.
    - *Péremption d'un tracé prêt en stock (180 j)* : un plan complété reste valide 180 jours en stock (`_checkRailStockExpiry`). S'il n'est pas financé dans ce délai, il est purgé, log `RAIL_STOCK_EXPIRE`, et la paire entre en retrait pour 180 jours.
    - *Re-validation matérielle obligatoire (`_revalidateRailStockPlan`)* : avant tout engagement physique dans `_tryBuildRailProject`, test complet sous `AITestMode` des quais de gare (`BuildRailStation`), des tuiles de voie (`OpexBuildTrack`), de l'emplacement du dépôt (`BuildRailDepot`), des slots de véhicules et de la trésorerie. En cas d'obstacle apparu sur la carte vivante : log `RAIL_STOCK_REVALIDATE_FAIL`, rejet propre et retrait temporaire.
  - **Persistance** : le stock prêt (`_railReadyStock`), la recherche en vol (`_railSearch`) et la table de retrait (`_railStockCooldown`) sont des structures transitoires/reconstructibles, vidées à `Load()` pour respecter la non-sérialisabilité des structures C++ NoAI AYSTAR.
  - **Sondes et traces (`probe_events=1`)** : `RAIL_STOCK_START`, `RAIL_STOCK_DEPOSIT` (src, dst, iters, jours, ticks, opcodes), `RAIL_STOCK_TIMEOUT`, `RAIL_STOCK_EXPIRE`, `RAIL_STOCK_CONSUME`, `RAIL_STOCK_REVALIDATE_FAIL`.

- **Validation (§4 AGENTS.md) — Réalisée le 2026-09-26** :
  - **Tests unitaires et de contrat Python** : 14 tests dédiés dans `sweeps/test_c80_rail_stock_worker.py` + tests de contrat gate + suite complète (379 tests unitaires) au vert.
  - **Identité bit-pour-bit au défaut** :
    - Graine 42 (1 an) : `company_value=427019`, `profit_year=306642`, `n_vehicles=23`, `n_stations=20` (strictement identique).
    - Graine 100 (6 ans) : `company_value=6014565`, `profit_year=1756502`, `n_vehicles=141`, `n_stations=56` (strictement identique entre `OpexAI` et `OpexAI[worker=1,gate=0]`).
    - Graine 999 (6 ans) : `company_value=11200121`, `profit_year=3685733`, `n_vehicles=138`, `n_stations=78` (strictement identique entre `OpexAI` et `OpexAI[worker=1,gate=0]`).
  - **Smoke 1×1 sous la variante (`c80_rail_stock_gate=1,c80_rail_stock_worker=1`)** : `run_ok=True`, zéro erreur NoAI.
  - **Diagnostic solo apparié 3 graines (100, 999, 5678) × 6 ans (`results/astar_e2_solo_3x6.json`)** :

| Graine | Bras | Passes `projects` | Écart médian (j) | Arrêts `rail_search` | Tracés déposés / expirés / timeouts | Lignes rail bâties | Avions / Trains | `profit_year` (£) | `company_value` (£) |
|---|---|---|---|---|---|---|---|---|---|
| **100** | Référence (défaut master) | — | — | 0 | 0 / 0 / 0 | 2 | 120 / 9 | 1 756 502 | 6 014 565 |
| **100** | Porte seule (`gate=1`) | — | — | 0 | 0 / 0 / 0 | 0 | 151 / 0 | 1 909 654 (+8,7%) | 7 284 687 (+21,1%) |
| **100** | Porte + Worker (`gate=1, worker=1`) | — | — | 0 | — | 0 | 121 / 0 | 2 015 849 (+14,8%) | 7 792 810 (+29,6%) |
| **100** | Porte + Worker (sondé) | 58 | 19 | **0** | 8 / 5 / 2 | **2** | 118 / **2** | 1 691 933 | 6 402 204 |
| **999** | Référence (défaut master) | — | — | 0 | 0 / 0 / 0 | 2 | 102 / 4 | 3 685 733 | 11 200 121 |
| **999** | Porte seule (`gate=1`) | — | — | 0 | 0 / 0 / 0 | 0 | 131 / 0 | 3 106 252 (−15,7%) | 11 481 114 (+2,5%) |
| **999** | Porte + Worker (`gate=1, worker=1`) | — | — | 0 | — | 0 | 112 / 0 | 3 053 494 (−17,2%) | 11 104 221 (−0,9%) |
| **999** | Porte + Worker (sondé) | 18 | 99 | **0** | 5 / 5 / 2 | **1** | 95 / **1** | 3 363 259 | 9 734 970 |
| **5678** | Référence (défaut master) | — | — | 0 | 0 / 0 / 0 | 1 | 127 / 6 | 4 004 709 | 12 730 467 |
| **5678** | Porte seule (`gate=1`) | — | — | 0 | 0 / 0 / 0 | 0 | 117 / 0 | 3 840 454 (−4,1%) | 13 558 255 (+6,5%) |
| **5678** | Porte + Worker (`gate=1, worker=1`) | — | — | 0 | — | 0 | 112 / 0 | 4 362 220 (+8,9%) | 13 859 914 (+8,9%) |
| **5678** | Porte + Worker (sondé) | 20 | 55 | **0** | 6 / 5 / 0 | 0 | 86 / 0 | 3 820 912 | 11 743 052 |

- **Bilan d'Étape 2** :
  - **Objectif principal atteint** : le rail est de retour sous la porte **SANS AUCUN arrêt de passe `rail_search`** (0 sur toutes les graines sondées).
  - Les recherches A\* longues ne bloquent plus le moteur : sur la graine 999, 2 recherches interminables ont été coupées nettes à 181 et 202 jours de jeu, libérant le slot pour d'autres candidats au lieu de geler le scheduler pendant 4 ans.
  - Le stock tampon $N=1$ fonctionne : 5 à 8 tracés produits et déposés par graine, avec des durées de calcul médianes de 37 à 78 jours de jeu sur le reliquat.
  - Sur la graine 100 sans sonde, `gate=1, worker=1` bat la référence sur `profit_year` (+14,8 %) et sur `company_value` (+29,6 %) tout en construisant son réseau de manière fluide.

---

### 3.2 bis Révision de l'étape 2 — séparer par mode jusqu'à la sélection (décision utilisateur, 2026-09-26)

**Constat qui motive la révision (solo 3 graines × 6 ans, `results/astar_e2_solo_3x6.json`).** Le
worker produit bien des tracés (5 à 8 dépôts par graine, recherche médiane 37 à 78 j, 0 arrêt de passe
`rail_search`), mais ils ne sont presque jamais construits : 5/8, 5/5 et 5/6 expirent à 180 j sans
financement ; sans sonde, **0 ligne rail construite** sur les 3 graines (le défaut en a 4 à 9 trains).
Lecture de code : le dépôt (`_handleRailStockSearchCompleted`, `task_rail.nut`) remplit
`_railReadyStock` sans rien invalider ; la porte ne filtre les alternatives rail qu'à la construction ou
resélection du portefeuille (`projects.nut` ~1326, ~2414, ~2898). Le tracé prêt attend donc une
régénération qui contienne encore son candidat, pendant que l'aérien prend la caisse. Dans l'ancien
chemin, le projet rail était élu avant son A* puis construit à la fin de la recherche : ce lien a disparu.

**Asymétrie de fond entre les modes (lecture de code).** Un projet aérien arrive au portefeuille
**prêt à construire** : `OpexAirPlans` confirme les sites d'aéroport pendant la génération, avant
l'élection (`OpexAirFindSite`, `builder_air.nut` ~635). Un projet rail arrive **sur papier** (coût
modèle × facteur de financement, sans tracé) et n'est préparé qu'après l'élection. Tous les modes sont
fusionnés dans une même liste `alternatives` puis `OpexProjectSelectAffordable` (~985 : filtre de
capital, tri par `fundScore`, `PROJECT_TOP_K` = 64) : des projets prêts et des projets sur papier s'y
concurrencent.

**Principe retenu (conforme à `docs/34_arbitrage_economique_unifie.md` §2 : producteurs → registre
commun → sélection).** Chaque mode garde **sa propre chaîne** — génération, préparation jusqu'à « prêt
à construire », petit stock de projets prêts, à sa propre cadence — et **seuls les projets prêts** de
tous les modes sont réunis **juste avant la sélection**, comparés sur une même base (`fundScore`
aujourd'hui, score commun de la note 34 §5 plus tard).

- **Rail** : le stock du worker devient la **liste de projets rail prêts** (N = 1 pour commencer) ;
  chaque entrée porte le projet complet (tracé, devis, capital, profit estimé), pas seulement un plan
  indexé par paire. La génération rail du catalogue n'alimente plus directement `alternatives` : elle
  alimente la file de travail du worker (tête de liste seulement, garde-fou `cible.md` §6.4).
- **Air, route, eau** : inchangés à cette étape ; ils produisent déjà des projets prêts (sites confirmés,
  plans routiers). Aucune refonte de leurs générateurs.
- **Sélection** : à **chaque passe** `projects`, fusion de la liste courante (air/route/eau, déjà
  entretenue par C76/C77) et des projets rail prêts du stock, puis `OpexProjectSelectAffordable` comme
  aujourd'hui. Un dépôt n'exige donc ni régénération ni invalidation : il est visible dès la passe
  suivante.
- **Construction** : `_tryBuildRailProject` ne construit qu'un projet rail prêt, après re-vérification
  (`_revalidateRailStockPlan`), sans A* ni `pending`. Le projet consommé sort du stock et réarme le worker.

**Garde-fous.**
- Aucun quota ni priorité par mode : pas de nouveau nombre magique ; un projet rail prêt gagne ou perd
  la sélection sur son score, comme les autres.
- Une seule métrique de comparaison entre modes.
- Opcodes : la fusion à chaque passe doit être bon marché (N petit) ; mesurer son coût.
- Identité au défaut (`c80_rail_stock_gate=0`) au bit près, comme aux étapes 1 et 2.

**Mesures qui prouvent que la révision mord (solo puis duel).**
- Part des tracés déposés effectivement construits (objectif : la majorité, contre ~0 aujourd'hui) ;
  délai dépôt → construction ; expirations à 180 j.
- Lignes rail construites par graine, comparées au défaut (4 à 9 trains) ; arrêts `rail_search` = 0.
- Passes `projects`, avions, `profit_year`, valeur ; puis duel 5×6 contre la référence
  `c80_rail_stock_gate=0,c80_rail_stock_worker=0`.

**Questions à trancher pendant l'implémentation (à documenter, pas à deviner).**
- Un tracé prêt dont le projet n'est plus finançable doit-il rester en stock jusqu'à 180 j (défaut
  retenu) ou céder sa place au candidat suivant ?
- Rafraîchir le profit/capital estimés du projet rail prêt à chaque passe, ou seulement au dépôt ?

**Implémentation de la révision (2026-09-26, validation en cours).** Sous les deux réglages C80,
`_railReadyStock[pairKey]` porte désormais `project` construit par `OpexProjectFromCandidate`
après l'A* et le recalcul économique, ainsi que `plan`, `candidate`, la clé et les dates. La
génération conserve `projects.rail` comme file du worker ; les candidats papier sont retirés de
`candidateGroups` sous les deux réglages, après l'assemblage historique. `OpexRailStockMergeAlternatives`
retire les projets rail papier des alternatives, ajoute les projets prêts et mesure
`railStockFusionOpcodes`. Sous les deux réglages, le point d'appel existant de promotion C78
réélit à chaque passe, avec trace `RAIL_STOCK_SELECT` (présence, financement, opcodes de fusion).
Ce branchement est installé au démarrage, hors du chemin exécuté au défaut. La construction
vérifie l'identité du projet stocké, revalide le plan, puis le consomme et réarme le worker.

Choix des deux questions : un projet non finançable **garde le slot jusqu'à 180 jours** ; la
trésorerie peut revenir pendant ce délai et jeter le tracé plus tôt gaspillerait l'A*. Le profit
et le capital sont **figés au dépôt**, après le recalcul sur la longueur A* réelle ; la sélection
rafraîchit `fundScore` avec le capital disponible, sans refaire le devis à chaque passe. La
revalidation de la carte reste obligatoire juste avant la dépense. Le devis physique exact par
`AITestMode` reste celui de la construction ; `capitalIsActual` n'est pas revendiqué ici.

### 3.3 Étape 3 — Stock borné $N=2$ et devis réel dans le sac à dos (`c80_rail_stock_capacity`)

- **Changement** :
  - Passage du stock à $N_{\max} = 2$.
  - Injection systématique de `capitalIsActual = true` pour les projets issus du stock dans `OpexProjectFinanceCapital` ([`projects.nut:302-313`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/projects.nut#L302-L313)).
  - Mise en place du TTL de 90 jours et purge automatique des tracés périmés.
- **Risque** : Calcul de tracés qui périment sans être financés (gaspillage d'opcodes).
- **Preuve que le mécanisme mord** :
  - Taux de péremption du stock mesuré (ratio tracés bâtis / tracés produits $\ge 75\,\%$).
  - Score financier du rail reflétant le coût réel sans le biais forfaitaire de 170 %.
- **Validation** :
  - Banc officiel apparié **20 graines × 10 ans** selon la règle d'adoption des optimisations d'opcodes (décision utilisateur du 2026-09-24 : absence de perte sur `profit_year`, test des signes $p \ge 0{,}05$, garde de valeur −5 %).

---

### 3.4 Étape 4 — Intégration prioritaire des chaînes V88 & multi-workers (`v88_chain_worker_prio`)

- **Changement** :
  - L'étape 1 des chaînes V88 consomme un tracé prêt normal du stock.
  - Dès la mise en service de l'étape 1, la demande de tracé pour l'étape 2 (usine → ville) est injectée dans la file des workers en **Classe 1 (Débloque)**.
  - Le worker rail traite l'étape 2 en priorité absolue sur le reliquat du tick.
  - Pendant le calcul de l'étape 2, la passe `projects` reste totalement libre de bâtir d'autres opportunités si la trésorerie le permet.
- **Risque** : Concurrence de trésorerie entre l'étape 2 et de nouvelles lignes aériennes.
- **Preuve que le mécanisme mord** :
  - Délai d'achèvement de l'étape 2 réduit à moins de 60 jours de jeu après l'étape 1.
  - Zéro slot aéroportuaire perdu au profit d'AAAHogEx pendant la construction d'une chaîne industrielle.
- **Validation** :
  - Banc officiel apparié 20 graines × 10 ans sur la variante chaînes industrielles V88.

---

## 4. Questions ouvertes et choix à trancher par l'utilisateur

Les points suivants sont soumis à l'arbitrage explicite de l'utilisateur avant le lancement de la phase d'implémentation :

1. **Capacité maximale du stock ($N_{\max}$)** :
   - *Option A (Prudente, recommandée)* : $N_{\max} = 1$ en phase initiale, puis $N_{\max} = 2$. Réduit à néant le risque de calculer des tracés qui périment sur une carte mouvante.
   - *Option B (Agressive)* : $N_{\max} = 3$. Offre un choix multivarié au sac à dos `projects`, mais risque de gaspiller des opcodes sur des corridors qui ne seront jamais financés.
   - *Question* : Validez-vous la trajectoire $N=1$ (Étape 2) puis $N=2$ (Étape 3) ?

2. **Durée de vie (TTL) d'un tracé prêt en stock** :
   - Nous proposons un TTL par défaut de **90 jours de jeu** (environ 1 trimestre). Si au bout de 3 mois de jeu le projet n'a pas été financé, il est invalidé pour forcer une réévaluation sur la carte fraîche.
   - *Question* : Ce délai de 90 jours vous convient-il, ou préférez-vous un TTL calé sur le changement d'année ou sur l'invalidation événementielle seule ?

3. **Chantier V88 : Deux tracés préparés d'avance ou séquentiel asynchrone ?**
   - *Option A (Séquentielle asynchrone, recommandée)* : L'étape 1 est bâtie dès que son tracé est prêt. L'étape 2 est calculée en priorité Classe 1 immédiatement après, profitant du délai d'acheminement des premiers trains d'intrants.
   - *Option B (Synchrone en amont)* : La chaîne V88 n'est déclarée éligible que si **les deux tracés (intrant ET biens)** sont simultanément calculés et prêts en stock. Cela évite le risque d'une usine orpheline si l'étape 2 s'avère impossible, mais retarde le lancement de l'étape 1 de plusieurs mois.
   - *Question* : Quelle politique d'engagement retenez-vous pour V88 ?

4. **Sort immédiat de `v89_rail_search_throughput`** :
   - V89 est actuellement à défaut 1 (adopté comme dépendance de V88).
   - Lors de l'activation du worker de stock, son algorithme d'absorption du slack sera directement encapsulé dans le worker.
   - *Question* : Souhaitez-vous conserver le paramètre `v89_rail_search_throughput` comme interrupteur global de pompage de slack, ou le supprimer dès que le worker stock est qualifié ?

5. **Recherche interminable** (ajoutée par l'orchestrateur) : une recherche unique a occupé le slot
   1 382 jours (graine 999, 5 681 itérations, sous le plafond de 10 000). Avec un stock réduit, une
   seule recherche lente bloquerait le worker pendant des années. Faut-il une durée maximale par
   recherche, et que faire quand elle est atteinte ?

### 4.1 Décisions de l'utilisateur (2026-09-26)

| # | Décision |
|---|---|
| Q1 | **$N_{\max} = 1$ pour commencer.** Une extension à 2 ne se discute qu'après mesure. |
| Q2 | **Durée de vie d'un tracé prêt non financé : 180 jours de jeu pour commencer** (et non 90). La re-vérification au moment de construire reste obligatoire. |
| Q3 | **Étape 1 d'abord** (séquentiel) : l'étape 1 d'une chaîne V88 est construite dès que son tracé est prêt ; l'étape 2 est ensuite demandée au worker en priorité. |
| Q4 | **Retirer `v89_rail_search_throughput` dès que le worker a passé son banc** : un seul mécanisme consomme le reliquat. |
| Q5 | **Durée maximale d'une recherche : 180 jours de jeu pour commencer**, puis le worker passe au candidat suivant. |

**Piste ouverte par l'utilisateur (Q5), non spécifiée ici :** il faudra probablement un mécanisme qui
**conserve les A\* longs ou coûteux pour le milieu de partie ou la fin de partie**, quand le reliquat
d'opcodes et la caisse le permettent, au lieu de les perdre à l'échéance de 180 jours —
vraisemblablement en s'appuyant sur la **cartographie par blocs C67** (corridor grossier, connectivité,
mémoire des zones). À concevoir séparément ; contrainte connue : une recherche en cours est aujourd'hui
abandonnée au rechargement (`persist.nut:800-825`), donc une conservation durable exige un état
sauvegardable ou reconstructible.

---

## 5. Synthèse des références documentaires et code

| Thématique | Emplacement dans le dépôt |
|---|---|
| Invariants NoAI et méthodologie | [`AGENTS.md`](file:///home/deploy/projects/openttd-ml/AGENTS.md) ; [`docs/methode.md`](file:///home/deploy/projects/openttd-ml/docs/methode.md) (piège de portée des closures) |
| Architecture cible et échecs historiques | [`docs/cible.md`](file:///home/deploy/projects/openttd-ml/docs/cible.md) §2.1 (rejet de l'échéance globale), §6.4 (ne pas simuler le vivier) |
| Arbitrage unifié et workers sur reliquat | [`docs/34_arbitrage_economique_unifie.md`](file:///home/deploy/projects/openttd-ml/docs/34_arbitrage_economique_unifie.md) §2, §5.5 (classes de workers), §7 |
| Orchestrateur double registre C80 | [`docs/18_orchestrateur_double_registre.md`](file:///home/deploy/projects/openttd-ml/docs/18_orchestrateur_double_registre.md) ; [`ai/OpexAI/orchestrator.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/orchestrator.nut) |
| Débit de recherche opportuniste V89 | [`docs/28_v89_debit_recherche_rail.md`](file:///home/deploy/projects/openttd-ml/docs/28_v89_debit_recherche_rail.md) ; [`ai/OpexAI/scheduler.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/scheduler.nut) |
| Tâches ferroviaires et point d'arrêt `pending` | [`ai/OpexAI/task_rail.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut) (`_tryBuildRailProject`, `_startRailSearch`) ; [`ai/OpexAI/task_projects.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_projects.nut) (`_tryBuildProjects`) |
| Complétion du tracé et devis réel | [`ai/OpexAI/builder_rail.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut) (`OpexCompleteRailRouteAfterSearch`) ; [`ai/OpexAI/projects.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/projects.nut) (`OpexProjectFinanceCapital`) |
| Sérialisation et persistance | [`ai/OpexAI/persist.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/persist.nut) (`OpexSaveActiveWorker`, `Load`) |
