# C80 — Orchestrateur à double registre (intentions / exécution)

> **Relecture du 2026-09-21 (Claude).** Contrat rédigé par agy ; références au code vérifiées par
> échantillon (`task_rail.nut:814-826`, `main.nut:297`, `main.nut:541`, `task_town.nut:63-75`,
> `persist.nut:8-17` : justes). Corrigés en place : rythme des événements (source erronée),
> description de l'échec de `portfolio_max_batch`, critère C80-6 ramené au profit annuel. N_max :
> tranché le 2026-09-21 (§3.1.3, option 3 : pas de constante, sonde à la place). Les objectifs chiffrés (tour ≤ 20 j,
> tranche `town_growth` ≤ 150 k opcodes) sont des **cibles**, pas des mesures.


**Contrat d'architecture écrit avant code, 2026-09-21. Aucun code de décision, aucun banc, aucun diagnostic dans ce document.**
Dépôt : `/home/deploy/projects/openttd-ml/.wt_c69` (worktree git, branche `c69-goulot-decision`).
Premier client de l'architecture : **C76 étape 2** (régénération ciblée du vivier par mode et sous-catalogues).

---

## 0. Synthèse et mandat

| Axe | Constat / Décision | Source |
|---|---|---|
| **Problème mesuré** | Un tour de file dure **45 à 52 jours** (et jusqu'à **120 jours** avec C75) ; l'IA ne prend que **4 à 9 décisions de construction par an** pendant que sa trésorerie monte à **11,5 M£**. | [`docs/16_bilan_volume.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md) §6-§7 |
| **Goulot d'exécution** | Trois tâches monolithiques de 2,2 à 2,8 Mop chacune remplissent le tour : `catalog` (31 % du temps), `town_growth` (28 %), `projects` (23 %). | [`docs/16_bilan_volume.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md) §7 |
| **Gaspillage mesuré** | **53 à 76 %** des régénérations du vivier s'exécutent sans aucun changement de dépendance, consommant **~145 à 180 jours de jeu par an** à recalculer l'identique. | [`docs/17_evenements_regeneration.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/17_evenements_regeneration.md) §6 |
| **Option retenue** | **Option 2 : Double registre** (Séparation stricte entre le choix de la décision et le moteur d'exécution). | Décision utilisateur du 2026-09-21 |
| **Premier client** | **C76 étape 2** : révisions par sous-catalogue, régénération ciblée par mode, filet périodique de réconciliation. | [`docs/17_evenements_regeneration.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/17_evenements_regeneration.md) §6 |
| **Règle absolue** | **Aucun changement du score de classement.** `ROI` ou `P / max(C, F·τ)` reste rigoureusement intact. Tout nouveau code est gardé derrière un réglage à défaut 0 (`c80_double_register = 0`). | Mandat C80 |

---

## 1. Problème mesuré et objectif

### 1.1 Le goulot du volume : décisions rares et caisse oisive

La comparaison directe contre l'adversaire de référence AAAHogEx (duel 20 graines × 5 ans sur carte partagée, [`results/bench_1v1_5y_20seeds_reference.json`](file:///home/deploy/projects/openttd-ml/.wt_c69/results/bench_1v1_5y_20seeds_reference.json), consigné dans [`ai/OpexAI/CLAUDE.md:15-20`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/CLAUDE.md#L15-L20)) montre une défaite à 0/20 pour OpexAI sur toutes les métriques :
- Valeur de compagnie : −71,6 % ;
- Profit annuel : −83,1 % ;
- Flotte active : 102 véhicules contre 564 pour AAAHogEx (à 10 ans : 158 contre 1 077).

Pourtant, le rendement économique par véhicule en service atteint 93 % de celui d'AAAHogEx ([`ai/OpexAI/CLAUDE.md:19`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/CLAUDE.md#L19)). **L'écart est presque intégralement un déficit de volume.**

Les mesures instrumentées du 2026-09-21 établissent la cause exacte de ce déficit :
1. **La caisse dort sans blocage de capital** ([`docs/16_bilan_volume.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md) §6, sonde C73 sur 3 graines × 10 ans) :
   - À partir de 1971, aucune passe du portefeuille ne trouve de vivier vide, tous les candidats sont finançables, et chaque passe construit.
   - La trésorerie disponible s'accumule sans emploi : **0,08 M£ en 1970**, **1,0 M£ en 1972**, **5,5 M£ en 1975**, et **11,5 M£ en 1978**.
   - Pourtant, l'IA ne réalise que **4 à 9 passes de construction par an et par partie** (11,7 en 1970 ; 8,7 en 1972 ; 7,7 en 1975 ; 6,0 en 1978 ; 5,3 en 1979). Chaque renfort de flotte aérienne (`FLEET_PORTFOLIO`) consomme l'une de ces rares opportunités.

2. **Où passe le temps de l'année de jeu** ([`docs/16_bilan_volume.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md) §7, sonde C74 / `C39_PASS_CLOCK` sur 3 graines × 10 ans) :
   - Le nombre de tours de la file d'ordonnancement par an s'effondre : **31 tours en 1971**, **8 en 1975**, **7 en 1979**.
   - Un tour complet dure **45 à 52 jours de jeu** à partir de 1975, absorbé par trois blocs monolithiques :
     - `catalog` : **108 à 111 jours/an** (30 à 32 % du temps, **2,76 Mop** par passe) pour rafraîchir en bloc tout le catalogue et reconstruire entièrement le vivier ;
     - `town_growth` : **93 à 103 jours/an** (27 à 28 % du temps, **2,73 Mop** par passe) pour scanner séquentiellement toutes les villes desservies de la carte dans un seul appel ;
     - `projects` : **81 à 95 jours/an** (23 à 27 % du temps, **2,21 Mop** par passe) pour la mise à jour incrémentale, la sélection et l'érection d'un seul chantier ;
     - `air_fleet` : **45 à 46 jours/an** (12 à 13 % du temps, **1,18 Mop** par passe).

3. **L'échec de la multiplication brute des chantiers sans nouvel ordonnanceur** ([`docs/16_bilan_volume.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md) §8, sonde C75 sur 3 graines × 10 ans) :
   - Construire plusieurs projets par passe sous `K_pass` accélère le démarrage (×3 à ×3,5 chantiers en 1972-1973), mais **allonge la durée du tour $\tau_{\text{pass}}$ de 30 jours à 91-122 jours**.
   - Chaque ligne possédée alourdit le coût de régénération (~38 k opcodes par ligne, [`docs/11_goulot_decision.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/11_goulot_decision.md) §1). Dès 1976, la fréquence tombe à 1 à 4 passes par an, et la liste classée s'épuise par manque de rafraîchissement opportuniste.

4. **Le constat d'invalidation C76 étape 1** ([`docs/17_evenements_regeneration.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/17_evenements_regeneration.md) §6, 3 graines × 10 ans) :
   - **53 à 76 %** des régénérations du vivier ne font suite à aucun événement ni modification de dépendance structurelle (ville, industrie, moteur, ligne).
   - Les clés de candidats sont stables à 99,5–100 % en mode aérien et 86–96 % en rail.
   - Ce calcul redondant coûte **81 à 100 M opcodes par an** (27 à 33 M par partie), soit **~145 à 180 jours de jeu par an** gaspillés.

### 1.2 Objectif de C80

L'objectif de C80 est de concevoir un **orchestrateur à double registre** permettant de :
1. **Découpler le choix décisionnel de l'effort de calcul** : séparer l'arbitrage (*quelle action lancer*) du découpage temporel (*comment fractionner les opcodes*).
2. **Raccourcir drastiquement le tour de file** : ramener l'intervalle moyen de décision $\tau_{\text{pass}}$ de 45–120 jours à **moins de 15 jours de jeu**.
3. **Rendre l'IA réactive aux événements du monde** : insérer une micro-action d'un seul tick dès qu'un événement survient, sans attendre la fin d'un calcul lourd (tel qu'un long A* ferroviaire).
4. **Fournir l'infrastructure d'exécution pour C76 étape 2** (régénération ciblée par mode) et **C77** (candidats opportunistes).
5. **Préserver strictement la logique de classement** : aucune modification de formule mathématique, aucun changement d'heuristique NoAI.

### 1.3 Analyse des options d'ordonnancement et justification du choix

Quatre options architecturales ont été évaluées :

| Option | Description | Motif d'écartement ou d'adoption |
|---|---|---|
| **1. File unique + slot actif** | Une file unique ordonnance tâches de fond et événements. Un slot actif unique reçoit la tâche longue élue. | **Écartée par l'utilisateur.** Mélange l'urgence événementielle et les scans de maintenance. Un événement prioritaire doit soit attendre son tour round-robin, soit court-circuiter brutalement le pointeur de file par des heuristiques complexes. |
| **2. Double registre (Option retenue)** | **Deux files d'intentions** (une file RÉACTIVE prioritaire et une file de FOND périodique) + **un registre d'exécution de travailleurs résumables** dotés d'échéances locales propres. | **Retenue.** Découplage strict. Les événements coupent la file sans fausser les compteurs périodiques. Les calculs lourds sont découpés en travailleurs reprenables. Une micro-action réactive peut s'intercaler entre deux tranches d'A*. |
| **3. Crédits DRR (Deficit Round Robin)** | Allocation d'un quantum d'opcodes à chaque famille de tâches avec report du déficit. | **Écartée par l'utilisateur.** Introduit des constantes arbitraires de quanta par mode (rail, route, catalogue). Très sensible au calibrage et ne résout pas la latence d'intercalation d'un événement critique. |
| **4. MLFQ (Multi-Level Feedback Queue)** | Files prioritaires multiples avec rétrogradation des tâches consommatrices de CPU et vieillissement. | **Écartée par l'utilisateur.** Complexité disproportionnée en Squirrel NoAI. Multiplie les seuils arbitraires d'anti-famine, rend l'ordonnancement non-déterministe et difficile à persister. |

---

## 2. État du code (vérifié fichier et ligne)

L'audit exhaustif du code au 2026-09-21 établit l'état de l'ordonnanceur existant :

| Composant | Fichier et lignes | Comportement constaté |
|---|---|---|
| **Boucle principale** | [`main.nut:532-566`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/main.nut#L532-L566) | Exécute à chaque itération : (1) `this._processEvents()`, puis (2) `this._runNextTaskWithSlackLedger()` sous `LOOP_BUDGET=0` (défaut), suivi de (3) `AIController.Sleep(1)`. |
| **File statique historique** | [`main.nut:297-332`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/main.nut#L297-L332) | Déclare `this._taskQueue` sous forme d'un tableau plat de 13 tables `{ name, dueCycle, enabled }`. Ordre : `catalog`, `c41_water`, `c41_road`, `c41_rail_signals`, `c41_rail_junction`, `report`, `scrap`, `air`, `air_fleet`, `projects`, `expand`, `refleet`, `town_growth`, `repay`. |
| **Ordonnanceur round-robin** | [`scheduler.nut:101-203`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler.nut#L101-L203) | `_runNextTask` scanne `_taskQueue` à partir de `_taskCursor`. Si une tâche a `enabled == true` et `dueCycle <= _taskCycle`, elle est sélectionnée, `task.dueCycle` est incrémenté de 1 ([`scheduler.nut:206`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler.nut#L206)), et `_taskCursor` avance. Si aucune tâche n'est due, `_taskCycle` s'incrémente et le curseur repart à 0. |
| **Interposition prioritaire A* rail** | [`scheduler.nut:140-177`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler.nut#L140-L177) | Avant de scanner `_taskQueue`, `_runNextTask` exécute obligatoirement `_continueRailExpansion()` (si non nul) puis `_continueRailSearch()` (si non nul). Ce travail s'exécute dans la *même* passe de scheduler que la tâche de file suivante. |
| **Dispatch des tâches** | [`scheduler.nut:214-239`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler.nut#L214-L239) | Route par comparaison de chaînes vers les handlers de [`scheduler_tasks.nut`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut). |
| **Catalogue monolithique** | [`scheduler_tasks.nut:35-66`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L35-L66) | `_dispatchCatalog` vérifie si le mois a changé ou si `_portfolioInvalidated == true`. Il appelle `this._catalog.refresh(this._budget, year)` ([`catalog.nut:932-986`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/catalog.nut#L932-L986)) qui rafraîchit toutes les couches en bloc, puis `this._rebuildProjects(fleetPlan)` ([`task_projects.nut:1058-1127`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_projects.nut#L1058-L1127)). |
| **Génération vivier (complet)** | [`projects.nut:2088-2589`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/projects.nut#L2088-L2589) | `OpexBuildProjects` scanne séquentiellement tous les modes : rail (`:2159`), route (`:2256`), air (`:2280`), eau (`:2336`), puis assemble `candidateGroups` et exécute la sélection sous capital (`:2378-2550`). Coût : ~2,8 Mop par passe. |
| **Croissance urbaine bloquante** | [`task_town.nut:53-220`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_town.nut#L53-L220) | `_tryTownGrowth` énumère toutes les villes desservies ([`task_town.nut:63-68`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_town.nut#L63-L68)), calcule un plan routier (`:126-128`) et tente de bâtir une ligne de bus à profit nul. Coût : 2,73 Mop d'un seul bloc, sans fractionnement. |
| **Travailleur A* rail existant** | [`task_rail.nut:751-899`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_rail.nut#L751-L899) | `_railSearch` est un état résumable (`{ kind, phase, pathfinder, segmented, spent, iterationBudget, safetyDeadline, plan, candidate, ... }`). Découpé en tranches de `RAIL_SEARCH_SLICE = 50` itérations ([`builder_rail.nut:39`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/builder_rail.nut#L39)) avec échéance locale `rail_micro_deadline` ([`task_rail.nut:814-819`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_rail.nut#L814-L819)). Consommé ensuite dans `_tryBuildProjects` via `_consumeRailSearch` ([`task_projects.nut:477`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_projects.nut#L477)). |
| **Routage d'événements** | [`events.nut:280-357`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/events.nut#L280-L357) | `_processEvents` lit la file NoAI. Handlers dans [`event_handlers.nut:690-785`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/event_handlers.nut#L690-L785). L'état passif `_markDirty` ([`events.nut:40-142`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/events.nut#L40-L142)) n'est consommé par aucune tâche. Le seul impact réel est `_portfolioInvalidated = true` et `dueCycle = 0`, qui forcent des régénérations complètes au lieu d'en éviter. |
| **Persistance et exclusions** | [`persist.nut:302-407`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/persist.nut#L302-L407) | `Save()` et `Load()` sérialisent l'état sous `SAVE_FULL_STATE=1`. `_railSearch` et `_dynamicBatch` sont **explicitement abandonnés au chargement** ([`persist.nut:518-538`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/persist.nut#L518-L538)) car les objets natifs C++ AYSTAR ne peuvent être sauvés ; `catalog` est alors réarmé au cycle courant. |

### 2.1 Les précédents d'ordonnancement (tentés, adoptés ou refusés)

Il est capital de documenter ce qui a déjà été expérimenté afin de ne pas répéter d'erreurs passées :

1. **`loop_budget` (drainage continu de tick sans sleep)** :
   - Déclaré dans [`info.nut:1923`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/info.nut#L1923), implémenté dans [`main.nut:541-562`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/main.nut#L541-L562).
   - Tentative de vider les opcodes résiduels d'un tick en enchaînant plusieurs tâches de file sans `Sleep(1)`.
   - **Résultat : CLOS / NON ADOPTÉ** ([`docs/taches.md:655-661`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/taches.md#L655-L661), [`docs/taches.md:1213`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/taches.md#L1213)). Rejoué sur [`results/review_h5_loop_budget_5x6.json`](file:///home/deploy/projects/openttd-ml/.wt_c69/results/review_h5_loop_budget_5x6.json) (5 graines × 6 ans) : 5/5 égalités exactes sur valeur, profit, score, flotte et opcodes. Le drainage continu brûlait du CPU sans faire progresser le jeu et créait un risque de famine NoAI. Défaut 0 conservé.
2. **Admission opportuniste sur reliquat de tick (C41.11–C41.14)** :
   - Profilé dans [`docs/cible.md:532-538`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/cible.md#L532-L538) et [`docs/journal_2026-09-13.md:306-317`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/journal_2026-09-13.md#L306-L317).
   - Les ledgers passifs C41.11/C41.12 avaient mesuré 28,1 % d'opcodes initiaux non utilisés. Mais C41.13/C41.14 ont établi que ce slack n'était **jamais disponible dans le même tick** que les 56 fenêtres où une micro-tâche ciblée devait être admise (0 admission sur 56 fenêtres).
   - **Conclusion de conception gravée** : Ne jamais bâtir un ordonnanceur sur « utiliser le reliquat ». Une micro-tâche doit posséder son propre tour de scheduler et une échéance locale propre.
3. **Multi-construction brute (`portfolio_max_batch` / `portfolio_dynamic_batch`)** :
   - Évalué le 2026-09-02 ([`docs/16_bilan_volume.md:171-173`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md#L171-L173), [`docs/taches.md:1194`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/taches.md#L1194)).
   - Échec historique (banc de 3 ans, avant le 2026-09-09) : un succès régénérait le vivier et fusionnait deux cycles en un, et la caisse était vide pendant la phase pauvre de 1970-1972 (le 1er chantier la vidait). Jamais testé en phase riche avant C75.
4. **Saut de passe `town_growth_skip_noop`** :
   - Banc officiel 20×10 ([`docs/journal_2026-09-13.md:318-327`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/journal_2026-09-13.md#L318-L327), [`results/bench_town_growth_skip_noop_correct_10y_20seeds.json`](file:///home/deploy/projects/openttd-ml/.wt_c69/results/bench_town_growth_skip_noop_correct_10y_20seeds.json)).
   - Résultat neutre (valeur −233 k£, 12/20 non significatif). Le skip ne supprimait pas le coût des recherches de voirie `OpexRoadPlanFor` déjà consommées dans l'appel : seul un découpage de la tâche en micro-tranches peut amortir son impact.

---

## 3. Architecture cible détaillée : Le double registre

L'architecture repose sur la séparation stricte de deux responsabilités :
1. **Registre des intentions** : Décide *quoi* faire (arbitrage événementiel vs maintenance périodique).
2. **Registre d'exécution** : Décide *comment* fractionner le calcul (exécution par tranches bornées via des travailleurs résumables).

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                            BOUCLE PRINCIPALE (tick)                          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                         1. _processEvents() (NoAI)
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       REGISTRE 1 : FILES D'INTENTIONS                        │
│                                                                              │
│   [ File RÉACTIVE (prioritaire) ]            [ File de FOND (périodique) ]   │
│   - Coalescence par clé unique                - Scans de maintenance         │
│   - Événements NoAI (ville, industrie)        - Filet périodique de rec.     │
│   - Alertes, pannes, subventions              - Rapports, amortissements     │
│   - Micro-actions immédiates (1 tick)         - dueCycle non altéré par C76  │
└──────────────────────┬───────────────────────────────────────┬───────────────┘
                       │                                       │
     (Micro-action 1 tick intercalaire)                        │
     Exécutée immédiatement si registre actif occupé           │
                       │                                       │
                       ▼                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       REGISTRE 2 : MOTEUR D'EXÉCUTION                        │
│                                                                              │
│   [ Registre Actif : Travailleur Résumable (Worker) ]                        │
│   - Au plus 1 travailleur actif (ou suspendu proprement)                     │
│   - Interface formelle : init, step(budget, deadline), done, cancel          │
│   - Échéance locale propre : AIController.GetTick() + sliceBudget + marge    │
│   - État sérialisable en table plate Squirrel (pas de coroutine native)      │
│                                                                              │
│   Instances types :                                                          │
│   * WorkerRailSearch      (A* ferroviaire, tranches de 50 itérations)        │
│   * WorkerRegenCandidates (C76 : régénération ciblée par mode)               │
│   * WorkerTownGrowth      (croissance urbaine découpée ville par ville)      │
│   * WorkerPortfolioAssembly (sélection et scoring sous capital)              │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                             AIController.Sleep(1)
```

### 3.1 Les deux files d'intentions

#### 3.1.1 File RÉACTIVE (haute priorité)
- **Rôle** : Répondre sans délai aux sollicitations du jeu.
- **Alimentation** : `_processEvents()` pousse des intentions réactives lors de la réception d'événements :
  - `AIEvent.ET_INDUSTRY_OPEN` / `CLOSE` → invalidation et génération de lignes de fret ;
  - `AIEvent.ET_TOWN_FOUNDED` ou seuil de population franchi → opportunités aéroport/bus ;
  - `AIEvent.ET_ENGINE_AVAILABLE` → mise à jour matériel ciblée ;
  - `AIEvent.ET_SUBSIDY_OFFER` → évaluation du candidat subventionné ;
  - `AIEvent.ET_VEHICLE_LOST` → réparation PBS (`c41_rail_signals`) ;
  - `AIEvent.ET_VEHICLE_WAITING_IN_DEPOT` / `CRASHED` → mise à la casse ou remplacement.
- **Structure de données** :
  ```squirrel
  this._reactiveQueue = []; // Liste ordonnée FIFO d'intentions
  this._reactiveKeys = {};  // Table de coalescence pour déduplication instantanée
  ```
- **Clés de coalescence** : Chaque intention réactive porte une clé textuelle déterministe. Si un événement survient alors qu'une intention identique est déjà en attente, les données sont fusionnées sans créer de doublon.
  - Exemple : `"industry:<id>"`, `"engine:<id>"`, `"town:<id>"`, `"signal_repair:<lineId>"`, `"regen_mode:<mode>"`.
- **Priorité** : La file réactive est toujours dépouillée avant la file de fond.

#### 3.1.2 File de FOND (périodique / maintenance)
- **Rôle** : Assurer l'entretien du réseau, les scans périodiques et la réconciliation économique.
- **Structure** : Reprend le mécanisme robuste de `dueCycle` et de round-robin existant dans [`scheduler.nut:181-202`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler.nut#L181-L202), mais allégé de ses tâches événementielles.
- **Tâches hébergées** :
  - `reconciliation_net` : filet périodique (annuel/semestriel) de mise à jour des populations et productions ;
  - `report` : bilan comptable annuel ([`scheduler_tasks.nut:500`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L500)) ;
  - `scrap` : purge des lignes déficitaires et matériels obsolètes ([`scheduler_tasks.nut:555`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L555)) ;
  - `repay` : remboursement mensuel d'emprunt ([`scheduler_tasks.nut:676`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L676)) ;
  - `town_growth` : balayage de fond pour la croissance urbaine (instancie un travailleur découpé) ;
  - `catalog_background` : audit périodique des prix et bornes d'époques.
- **Invariance des compteurs** : Les insertions dans la file réactive n'altèrent ni `_taskCycle`, ni `dueCycle`, ni les compteurs temporels de la file de fond.

#### 3.1.3 Anti-famine sans constante arbitraire
Pour éviter qu'une tempête d'événements n'affame la file de fond sans introduire de quantum magique :
1. **Borne naturelle NoAI** : le flux d'événements est faible. La sonde C76 compte **35 à 60 événements par an pour 3 parties** (tous types, soit 12 à 20 par partie ; `17_evenements_regeneration.md` §6) ; C41.0 en comptait 47 sur 5 parties × 6 ans pour les seuls événements de catalogue (`cible.md:474`).
2. **Coalescence stricte** : Une rafale d'événements sur la même entité (ex. 5 notifications de fret) produit une seule entrée par clé dans `_reactiveQueue`.
3. **Règle structurelle de vidage** :
   - Une micro-action réactive ne consomme qu'**un seul tick**.
   - Une intention réactive lourde instancie un travailleur résumable qui s'exécute par tranches d'opcodes bornées.
   - **Pas de règle de saturation (décision utilisateur du 2026-09-21, option 3).** Aucune constante $N_{\max}$ n'est introduite : avec 12 à 20 événements par an et par partie (sonde C76), la file réactive ne devrait jamais rester pleine plusieurs ticks d'affilée, et une règle qui ne se déclenche pas n'est que du code à maintenir.
   - **Sonde à la place** : dès qu'un producteur alimente la file réactive (C76 étape 2, C77), l'orchestrateur compte, sous sonde, le plus long enchaînement de ticks consécutifs servis à la file réactive et le nombre de ticks où la file de fond a attendu. Une règle anti-famine ne sera écrite que si cette sonde mesure une saturation.

---

### 3.2 Le registre d'exécution (Worker Engine)

Le registre d'exécution maintient la référence vers le travailleur résumable en cours :
```squirrel
this._activeWorker = null;
```

#### 3.2.1 Interface formelle d'un Travailleur Résumable (`OpexWorker`)
Chaque tâche longue doit implémenter une table d'état respectant l'interface suivante :

```squirrel
// Interface contractuelle d'un travailleur résumable C80
class OpexWorker
{
  // 1. Initialisation avec contexte et paramètres (instanciation immédiate sans calcul lourd)
  function init(context, params);

  // 2. Avancement d'un pas d'exécution
  // budgetOps : opcodes alloués pour la tranche
  // deadlineTick : échéance temporelle locale stricte
  // Retourne : { done = bool, outcome = string, ... }
  function step(budgetOps, deadlineTick);

  // 3. Prédicat d'état
  function isDone();

  // 4. Annulation propre (libération de verrous, remise à propre du monde ou de la trésorerie)
  function cancel();

  // 5. Sérialisation (retourne une table plate Squirrel sans float ni closure)
  function serialize();

  // 6. Restauration depuis une sauvegarde
  function restore(data);
}
```

#### 3.2.2 Échéance locale propre (`local_deadline`)
L'un des échecs majeurs des tentatives antérieures de fractionnement était l'usage d'un timeout global partagé avec le scheduler, qui provoquait des abandons intempestifs si d'autres tâches avaient consommé du temps auparavant ([`docs/cible.md:560`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/cible.md#L560)).

Dans C80, chaque appel à `worker.step()` calcule son échéance locale sur le tick courant :
$$\text{deadlineTick} = \text{AIController.GetTick()} + \text{SliceTicks} + \text{BUILD\_TICK\_MARGIN}$$
Ce modèle reprend la solution validée de `RAIL_MICRO_DEADLINE` ([`task_rail.nut:814-819`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_rail.nut#L814-L819)) : la micro-étape dispose d'une marge de sécurité contre les blocages locaux sans jamais subir le temps passé par la file d'attente.

---

### 3.3 La boucle principale ordonnancée et l'intercalation d'une micro-action

La boucle principale de [`main.nut`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/main.nut#L532-L566) devient :

```squirrel
while (true) {
  // 1. Dépouillement des événements NoAI (très léger, routage en file réactive)
  this._processEvents();

  // 2. Gestion des micro-actions intercalaires (intercalation critique d'un seul tick)
  // Si la file réactive contient une micro-action d'un seul tick (réparation signal,
  // acquittement subvention, clôture d'industrie), on l'exécute immédiatement,
  // MÊME SI un long A* est en cours dans this._activeWorker.
  if (this._hasPendingReactiveMicroAction()) {
    this._executeOneReactiveMicroAction();
    // On rend la main pour que le jeu simule ce tick
    AIController.Sleep(1);
    continue;
  }

  // 3. Avancement du travailleur résumable actif (s'il y en a un)
  if (this._activeWorker != null) {
    local deadline = AIController.GetTick() + this._activeWorker.getSliceTicks() + BUILD_TICK_MARGIN;
    local result = this._activeWorker.step(this._activeWorker.getSliceOps(), deadline);
    if (this._activeWorker.isDone()) {
      this._finalizeActiveWorker(result);
      this._activeWorker = null;
    }
    AIController.Sleep(1);
    continue;
  }

  // 4. Élection d'une nouvelle intention (le registre actif est libre)
  local elected = null;
  if (this._reactiveQueue.len() > 0) {
    elected = this._popReactiveIntention();
  } else {
    elected = this._pickNextDueBackgroundIntention();
  }

  if (elected != null) {
    if (elected.isMicroAction) {
      // Action directe d'un seul tick
      elected.execute(this);
    } else {
      // Intention lourde -> instanciation du travailleur résumable associé
      this._activeWorker = elected.createWorker(this);
      // Exécution immédiate de sa première tranche
      local deadline = AIController.GetTick() + this._activeWorker.getSliceTicks() + BUILD_TICK_MARGIN;
      local result = this._activeWorker.step(this._activeWorker.getSliceOps(), deadline);
      if (this._activeWorker.isDone()) {
        this._finalizeActiveWorker(result);
        this._activeWorker = null;
      }
    }
  }

  AIController.Sleep(1);
}
```

#### 3.3.1 Mécanisme de l'intercalation pendant un long A*
Lorsqu'une recherche ferroviaire de 2 000 itérations est en cours :
1. Au tick $T$, `this._activeWorker` (de type `WorkerRailSearch`) exécute sa tranche de 50 itérations ([`task_rail.nut:818-826`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_rail.nut#L818-L826)).
2. Un événement `AIEvent.ET_INDUSTRY_CLOSE` ou `AIEvent.ET_VEHICLE_LOST` arrive pendant le tick.
3. Au tick $T+1$, `_processEvents()` l'enregistre et pousse une micro-action dans `_reactiveQueue`.
4. L'étape 2 détecte cette micro-action d'un tick (ex. pose de signal PBS [`scheduler_tasks.nut:436`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L436) ou purge d'une industrie fermée du vivier) et l'exécute immédiatement.
5. Au tick $T+2$, le registre actif `_activeWorker` reprend exactement son A* à l'itération 51.
6. **Bénéfice** : L'A* n'a été ni annulé, ni réinitialisé, et l'événement n'a pas attendu 50 jours de jeu.

---

## 4. Inventaire des tâches actuelles et leur destin

Chacune des 13 tâches de [`main.nut:297-332`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/main.nut#L297-L332) et les continuations rail de [`scheduler.nut:140-177`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler.nut#L140-L177) reçoit une affectation nette :

| Tâche actuelle | Fichier et lignes | Rôle actuel | Destin dans C80 | Nature et découpage proposé |
|---|---|---|---|---|
| `railSearch` | [`task_rail.nut:751-899`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_rail.nut#L751-L899) | A* ferroviaire reprenable | **Travailleur résumable actif** (`WorkerRailSearch`) | Devient un travailleur de premier rang dans le registre actif. Conserve ses tranches de 50 itérations (`RAIL_SEARCH_SLICE`) et `rail_micro_deadline`. |
| `railExpansion` | [`scheduler.nut:140`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler.nut#L140), [`task_rail.nut:366`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_rail.nut#L366) | Extension de rame en dépôt | **Travailleur résumable actif** (`WorkerRailExpansion`) | Travailleur multi-étapes réutilisant la machine d'état déjà persistée dans `persist.nut:8-30`. |
| `catalog` | [`scheduler_tasks.nut:3-81`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L3-L81) | Rafraîchissement total + rebuild vivier | **Éclaté en intentions ciblées + travailleurs** | (1) Sous-catalogues rafraîchis à la demande en 1 tick ; (2) Rebuild remplacé par `WorkerRegen<Mode>` ; (3) Filet périodique en file de fond. |
| `projects` | [`scheduler_tasks.nut:603-639`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L603-L639) | Sélection et construction d'un chantier | **Intention réactive ou de fond** | Quand élue : si le meilleur projet est routier/aérien, construction en 1 tick ; si ferroviaire, instanciation de `WorkerRailSearch`. |
| `town_growth` | [`task_town.nut:53-220`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_town.nut#L53-L220) | Croissance urbaine (2,73 Mop d'un coup) | **Travailleur résumable de fond** (`WorkerTownGrowth`) | Découpé en étapes : **1 ville traitée par tranche** (tranche de ~80–120 k opcodes) avec relâchement de la main entre deux villes. |
| `air` | [`scheduler_tasks.nut:564-575`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L564-L575) | Construction aérienne hors portefeuille | **Supprimé / Fusionné** | Déjà désactivé sous `AIR_PORTFOLIO=1` ([`scheduler_tasks.nut:573`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L573)). Intégré aux intentions de construction du vivier. |
| `air_fleet` | [`scheduler_tasks.nut:576-602`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L576-L602) | Redimensionnement de flotte aérienne | **Intention de fond périodique** | Audit mensuel léger. Si renforts mûrs : injection directe dans le portefeuille via micro-action. |
| `c41_water` | [`scheduler_tasks.nut:315-386`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L315-L386) | Rafraîchissement catalogue eau ciblé | **Intention réactive (1 tick)** | Retiré de la file statique ; inséré dans `_reactiveQueue` uniquement sur `EngineAvailable` eau. |
| `c41_road` | [`scheduler_tasks.nut:387-416`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L387-L416) | Rafraîchissement catalogue route ciblé | **Intention réactive (1 tick)** | Retiré de la file statique ; inséré dans `_reactiveQueue` uniquement sur `EngineAvailable` route. |
| `c41_rail_signals` | [`scheduler_tasks.nut:417-448`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L417-L448) | Réparation signaux PBS sur véhicule perdu | **Micro-action réactive (1 tick)** | Retiré de la file statique ; exécuté immédiatement en intercalaire à la réception de l'alerte. |
| `c41_rail_junction` | [`scheduler_tasks.nut:449-499`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L449-L499) | Réparation raccord double voie | **Micro-action réactive (1 tick)** | Idem `c41_rail_signals`. |
| `report` | [`scheduler_tasks.nut:500-554`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L500-L554) | Rapport annuel comptable | **Intention de fond périodique** | Exécutée une fois par an en début d'exercice (1 tick). |
| `scrap` | [`scheduler_tasks.nut:555-563`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L555-L563) | Purge véhicules obsolètes et déficitaires | **Intention de fond + micro-action** | Scan annuel de fond + micro-action réactive sur `VEHICLE_WAITING_IN_DEPOT`. |
| `expand` | [`scheduler_tasks.nut:640-651`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L640-L651) | Doublement voie / second train rail | **Intention de fond périodique** | Scan périodique trimestriel. Si opportunité : instancie `WorkerRailExpansion`. |
| `refleet` | [`scheduler_tasks.nut:652-659`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L652-L659) | Renouvellement flotte route/eau | **Intention de fond périodique** | Maintenance trimestrielle de fond (1 tick). |
| `repay` | [`scheduler_tasks.nut:676-686`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/scheduler_tasks.nut#L676-L686) | Remboursement d'emprunt mensuel | **Intention de fond périodique** | Micro-action mensuelle (1 tick). |

### 4.1 Découpage détaillé des quatre travailleurs résumables critiques

#### 1. `WorkerRailSearch` (A* ferroviaire)
- **Point de départ** : Structure existante `_railSearch` ([`task_rail.nut:773`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_rail.nut#L773)).
- **Étape 1 (Préparation)** : `OpexPrepareRailRoute` (1 tick).
- **Étape 2 (Recherche A*)** : Tranches de 50 itérations (`RAIL_SEARCH_SLICE`) avec `rail_micro_deadline`. À chaque tranche, vérification de complétion ou de timeout local.
- **Étape 3 (Finalisation)** : `OpexCompleteRailRouteAfterSearch`. Le plan complet est transmis pour érection.

#### 2. `WorkerTownGrowth` (Croissance urbaine découpée)
- **Problème résolu** : Fait passer la tâche de 2,73 Mop monolithiques à une série de tranches de < 150 k opcodes.
- **État sérialisable** : `{ cursorTownIndex, servedTownsList, year }`.
- **Étape par pas (`step`)** :
  - Dépile **1 seule ville** de la liste des villes desservies.
  - Exécute les filtres de présence et de station ([`task_town.nut:69-75`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/task_town.nut#L69-L75)).
  - Si éligible : exécute `OpexRoadPlanFor` et `OpexBuildRoadRoute`.
  - Si construction réussie ou fin de liste : passe à l'état `done`. Sinon, incrémente le curseur et rend la main pour le tick suivant.

#### 3. `WorkerRegenCandidates` (Régénération ciblée C76/C80)
- **État sérialisable** : `{ mode, stage, entityCursor, currentBatch, partialCandidates }`.
- **Étape 1** : Rafraîchissement du sous-catalogue du mode concerné (1 tick).
- **Étape 2** : Scan par paquets d'origines (ex. 10 villes ou 10 industries par tranche).
- **Étape 3** : Évaluation économique et scoring des candidats découverts.
- **Étape 4** : Insertion dans `candidateGroups` du vivier et réévaluation du TopK.

#### 4. `WorkerPortfolioAssembly` (Fusion et sélection sous capital)
- **Rôle** : Réalise l'arbitrage multimodal et le sac à dos (`OpexProjectFinanceCapital`).
- **Découpage** :
  - Tranche 1 : Fusion des candidats gagnants des différents modes (`winners`).
  - Tranche 2 : Tri et sélection sous contrainte de capital (`funded`).
  - Tranche 3 : Émission des signatures de diagnostic et horodatage de finançabilité.

---

## 5. C76 étape 2 comme premier client de l'architecture

Le chantier **C76 étape 2** est le premier bénéficiaire direct de l'orchestrateur à double registre.

### 5.1 Architecture des sous-catalogues et révisions C76
Au lieu d'un appel global `OpexCatalog::refresh` ([`catalog.nut:932`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/catalog.nut#L932)), chaque couche conserve son couple de révisions sérialisables : `revision` (incrémenté sur modification du monde) et `acknowledgedRevision` (mis à jour lors de la régénération effective) :

```squirrel
this._staleness = {
  revisions = {
    catalog = { cargos = 0, towns = 0, industries = 0, rail = 0, road = 0, air = 0, water = 0 },
    candidates = { rail = 0, road = 0, air = 0, water = 0, fleet = 0 },
    portfolio = 0
  },
  acknowledged = {
    catalog = { cargos = 0, towns = 0, industries = 0, rail = 0, road = 0, air = 0, water = 0 },
    candidates = { rail = 0, road = 0, air = 0, water = 0, fleet = 0 },
    portfolio = 0
  }
};
```

### 5.2 Matrice des dépendances modales (`mode ← couches`)

Un travailleur de régénération modale n'est instancié que si au moins une de ses couches sources présente `revision > acknowledgedRevision` :

| Mode de candidats | Couches de sous-catalogue requises | Dépendances réseau | Déclencheurs NoAI (File réactive) |
|---|---|---|---|
| `candidates.air` | `catalog.cargos`, `catalog.towns`, `catalog.air` | Lignes aériennes | `TownFounded`, `EngineAvailable(air)`, ville franchissant seuil aéroportuaire |
| `candidates.rail_pax` | `catalog.cargos`, `catalog.towns`, `catalog.rail` | Réseau ferré | `TownFounded`, `EngineAvailable(rail)` |
| `candidates.rail_freight` | `catalog.cargos`, `catalog.industries`, `catalog.rail` | Réseau ferré | `IndustryOpen`, `IndustryClose`, `EngineAvailable(rail)` |
| `candidates.road_pax` | `catalog.cargos`, `catalog.towns`, `catalog.road` | Voirie urbaine | `TownFounded`, `EngineAvailable(road)` |
| `candidates.road_freight` | `catalog.cargos`, `catalog.industries`, `catalog.road` | Réseau routier | `IndustryOpen`, `IndustryClose`, `EngineAvailable(road)` |
| `candidates.water` | `catalog.cargos`, `catalog.industries`, `catalog.water` | Bassins côtiers | `IndustryOpen`, `EngineAvailable(water)` |
| `candidates.fleet` | `lines`, matériel du mode concerné | Flotte en service | Allongement des files d'attente aux stations |

### 5.3 Le filet périodique de réconciliation (obligatoire)

OpenTTD ne génère **aucun événement NoAI** pour :
1. La variation mensuelle de la population urbaine (croissance naturelle ou induite) ;
2. La fluctuation de production des industries primaires (mines, fermes, puits) ;
3. Le vieillissement des véhicules en exploitation ;
4. La reprise d'une sauvegarde (la file d'événements NoAI est vide au rechargement).

**Doctrine C76/C80** : *Événements pour l'immédiat + Filet périodique pour la dérive continue.*
Le filet périodique s'exécute en **file de fond** à cadence semestrielle ou annuelle. Il met à jour les grandeurs volumétriques (`pop`, `production`) et réévalue économiquement les candidats existants en mémoire, **sans relancer de recherche spatiale de route**.

### 5.4 Ce que C77 réutilisera directement

Le chantier **C77** (« déclenchement des candidats opportunistes », [`docs/taches.md:84-98`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/taches.md#L84-L98)) s'appuiera nativement sur le double registre de C80 :
- Dès qu'un événement survient (ex. `IndustryOpen` ou ouverture d'un second aéroport dans une ville par AAAHogEx), C77 ne réveillera même pas le régénérateur complet du mode : il créera directement une **intention réactive unitaire** ciblant l'entité touchée.
- Cette intention unitaire générera immédiatement les candidats de la nouvelle entité, les injectera dans `candidateGroups`, et déclenchera une tentative de construction sous 1 tick.

---

## 6. Sérialisation et persistance

La persistance sous NoAI obéit à des contraintes physiques absolues imposées par le moteur C++ d'OpenTTD :
- **Interdiction des flottants** : Le format de sauvegarde NoAI rejette les floats (`Save()` échoue). Toutes les valeurs doivent être en entiers ou milli-unités ([`persist.nut:16-17`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/persist.nut#L16-L17)).
- **Interdiction formelle des coroutines natives Squirrel** : Les coroutines (`newthread` / `yield`) ne peuvent pas être sérialisées par le moteur d'OpenTTD, créent des fuites mémoires silencieuses et peuvent geler la VM. Toute tâche longue doit être un **objet d'état plat** sérialisable.

### 6.1 Ce qui est persisté dans `Save()`
Dans [`persist.nut:302-407`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/persist.nut#L302-L407), les structures C80 suivantes sont sauvegardées :
1. `reactiveQueue` : liste des intentions réactives non traitées (tableaux de dictionnaires d'entiers et chaînes).
2. `backgroundQueue` : états de `dueCycle`, `taskCursor` et `taskCycle`.
3. `revisions` et `acknowledged` : registres d'invalidation C76.
4. `activeWorkerState` : si un travailleur est actif, son type et son état sérialisé via `worker.serialize()`.

### 6.2 Ce qui est reconstruit ou abandonné dans `Load()` et `_reconcileAfterLoad()`

| Élément | Comportement au rechargement | Justification technique |
|---|---|---|
| `WorkerTownGrowth` | **Restauré et repris** | État 100 % Squirrel (curseur d'entier, liste d'IDs de villes). Reprend à la ville suivante. |
| `WorkerRegenCandidates` | **Restauré ou relancé** | État 100 % Squirrel. Peut reprendre ou régénérer le mode propre. |
| `WorkerRailSearch` | **ABANDONNÉ PROPREMENT** | Contient des objets natifs C++ AYSTAR non sérialisables. Conformément au comportement éprouvé de [`persist.nut:518-538`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/persist.nut#L518-L538), l'état est annulé proprement (`cancel()`), `_railSearch = null`, et l'intention ferroviaire est réinjectée dans la file pour reprise propre sans fuite de mémoire. |
| `File d'événements NoAI` | **Vide à la reprise** | OpenTTD vide la file d'événements. `_reconcileAfterLoad()` force une révision complète du filet périodique pour réconcilier l'état du monde avec la mémoire de l'IA. |

---

## 7. Plan de livraison par morceaux et protocole de banc

Chaque morceau est développé et livré de façon incrémentale, isolé derrière un réglage d'expérience à **défaut 0** dans [`info.nut`](file:///home/deploy/projects/openttd-ml/.wt_c69/ai/OpexAI/info.nut).

### 7.1 Découpage des tranches de livraison

```text
Tranche 0 : Socle double registre (drapeau c80_double_register = 0)
   ├── Infrastructure des deux files (réactive + fond)
   ├── Machine d'état du registre d'exécution
   └── Validation par smoke test technique (2 graines × 3 ans)
         │
         ▼
Tranche 1 : Migration du travailleur A* rail (c80_worker_rail = 0)
   ├── Enrobage de _railSearch dans l'interface OpexWorker
   ├── Intercalation des micro-actions réactives (1 tick) pendant l'A*
   └── Diagnostic apparié 5×6 (vérification de stricte non-régression)
         │
         ▼
Tranche 2 : Fractionnement de la croissance urbaine (c80_worker_town = 0)
   ├── Découpage de _tryTownGrowth en WorkerTownGrowth (1 ville/tranche)
   ├── Suppression du pic de 2,73 Mop
   └── Mesure du raccourcissement du tour de file (sonde C74)
         │
         ▼
Tranche 3 : C76 étape 2 sur double registre (c76_regen_targeted = 0)
   ├── Sous-catalogues indépendants et matrice de dépendances
   ├── WorkerRegenCandidates par mode + filet périodique de réconciliation
   └── BANC OFFICIEL D'AUTORITÉ 20×10 EN DUEL CONTRE AAAHogEx
```

### 7.2 Le banc d'autorité officiel : 20×10 en duel

⚠️ **Rappel méthodologique fondamental de la fiche C66** ([`docs/taches.md:116-117`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/taches.md#L116-L117), [`docs/17_evenements_regeneration.md:116-117`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/17_evenements_regeneration.md#L116-L117)) :
- **Le 5×6 solo ne prédit pas le duel.**
  Les retours d'expérience C49 (scarcity), C69 (goulot de décision) et C72 (choix d'avion) ont prouvé que des gains solo de +100 k£ à +290 k£ s'annulent ou deviennent négatifs en duel. En solo, le foncier abonde et la caisse ne subit aucune concurrence. En duel, AAAHogEx sature les aéroports municipaux (limités à 2 par ville, erreur 771, [`docs/16_bilan_volume.md`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md) §3) et capte le trafic si le rythme décisionnel n'est pas coordonné.
- **Le duel n'est pas déterministe.**
  Les interactions asynchrones et les micro-variations de calendrier modifient la trajectoire.
- **Protocole d'arbitrage** :
  - Script d'autorité : `sweeps/run_c66_reference.py` (20 graines canoniques × 10 ans sur carte partagée contre AAAHogEx).
  - Décision d'adoption lue impérativement au **test des signes d'abord** : au moins **15 victoires sur 20** ($p < 0,05$), moyennes ensuite.

---

## 8. Critères de passage écrits d'avance

Chaque étape dispose de seuils de passage quantitatifs vérifiables par les sondes existantes :

| ID | Métrique | Seuil de passage | Sonde / Outil de mesure | Interprétation |
|---|---|---|---|---|
| **C80-1** | Durée moyenne du tour de file ($\tau_{\text{pass}}$) | **$\le 20$ jours** (défaut actuel : 45–52 j, et jusqu'à 120 j) | Sonde C74 (`probe_scheduler=1`, `C39_PASS_CLOCK`) | Le cycle de décision est accéléré d'un facteur 2,5 à 3. |
| **C80-2** | Passes de décision/construction utiles par an | **$\ge 18$ chantiers/an** (défaut actuel : 6 à 9 chantiers/an) | Sonde C73 (`probe_portfolio=1`, `diag_c73_vivier`) | L'IA transforme sa trésorerie oisive en volume d'infrastructures. |
| **C80-3** | Latence de prise en compte d'un événement réactif | **$\le 2$ ticks de jeu** (défaut actuel : jusqu'à 45 jours) | Sonde passante sur `_reactiveQueue` | L'intercalation d'une micro-action pendant l'A* fonctionne sans attendre le tour complet. |
| **C80-4** | Plafond d'opcodes par tranche de `town_growth` | **$\le 150\ 000$ opcodes** (défaut actuel : 2,73 Mop en un bloc) | `OpexOpsMeasure` sur `WorkerTownGrowth` | La croissance urbaine ne gèle plus l'IA pendant un mois entier. |
| **C80-5** | Régénérations de vivier évitées (C76 étape 2) | **$\ge 50\ \%$** des passes de catalog/projects | Sonde C76 (`probe_catalogue=1`, `C76_REGEN`) | Le travail redondant mesuré à l'étape 1 est effectivement éliminé. |
| **C80-6** | Banc officiel 20×10 en duel contre AAAHogEx | **Signe $\ge 15/20$** sur le profit annuel (p < 0,05), écart moyen > +50 k£/an, garde −5 % sur la valeur | `sweeps/run_c66_reference.py` | L'accélération du débit se traduit par un gain net face à l'adversaire. |

---

## 9. Risques identifiés, garde-fous et levée de consigne

### 9.1 Risques identifiés et garde-fous

1. **Risque de famine de la file de fond par une cascade d'événements** :
   - *Garde-fou* : Règle structurelle (§3.1.3) accordant le tour à la file de fond après au plus 5 ticks réactifs consécutifs, et coalescence stricte des clés.
2. **Risque d'asynchronisme et de désynchronisation multimodale** :
   - Si un mode est régénéré avec des coûts récents pendant qu'un autre conserve des estimations anciennes, le sac à dos peut subir un biais d'âge.
   - *Garde-fou* : Le filet périodique de fond réévalue périodiquement tous les candidats retenus en mémoire sur la même base de capital et d'amortissement.
3. **Risque de corruption à la sauvegarde d'un travailleur en cours** :
   - *Garde-fou* : Interdiction formelle des coroutines natives. Seules des tables plates d'entiers sont sérialisées. Si un travailleur porte des pointeurs C++ (`WorkerRailSearch`), il est proprement annulé à la sauvegarde et réinstancié à la reprise.

### 9.2 Ce que le contrat ne fait pas

- **Aucune modification de la formule de score** : `fundScore = P × 1000 / financeCapital` ou `P / max(C, F·τ)` reste strictement identique.
- **Aucune modification des algorithmes de pathfinding** : AYSTAR rail et road conservent exactement leurs profils et heuristiques.
- **Aucune modification de la réserve de trésorerie** : `OpexCashReserve()` et la politique d'emprunt restent intactes.
- **Aucun contournement du budget d'opcodes NoAI** : Le script ne modifie pas les limites NoAI de la plateforme.

### 9.3 Levée explicite de l'ancienne consigne de `taches.md`

Dans [`docs/taches.md:228-230`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/taches.md#L228-L230) et [`docs/taches.md:1194-1200`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/taches.md#L1194-L1200), figurait la consigne suivante :
> *« Ne pas lancer simultanément une nouvelle famille de plafonds, un nouveau score et un orchestrateur général [...] sur la seule foi d'anciens profils. »*

Cette consigne est **formellement levée ce 2026-09-21**, sur la base des preuves expérimentales fraîches obtenues sur le code courant :
1. **La prémisse de l'interdiction est réfutée** : La clôture de C39.5 reposait sur l'observation que le vivier était vide dans 58,6 % des tours ([`docs/16_bilan_volume.md:162-167`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/16_bilan_volume.md#L162-L167)) ; accélérer le scheduler semblait donc inutile. Or la sonde C73 démontre que sur le code actuel (sans feeders, post-C68), le vivier n'est **jamais vide après 1970**, tous les projets sont finançables, et chaque passe construit.
2. **Le goulot physique mesuré est le tour de file** : La sonde C74 prouve que le tour de file dure 45 à 52 jours (7 à 8 chantiers/an) pendant que la caisse dort à 11,5 M£.
3. **Le gaspillage est quantifié et validé** : La sonde C76 étape 1 mesure que 53 à 76 % des régénérations sont redondantes (~145 à 180 jours de jeu/an gaspillés), et l'utilisateur a expressément validé C76 pour entrer en étape 2 ([`docs/17_evenements_regeneration.md:197-200`](file:///home/deploy/projects/openttd-ml/.wt_c69/docs/17_evenements_regeneration.md#L197-L200)).
4. **Conclusion** : L'orchestrateur général n'est plus une spéculation abstraite basée sur d'anciens profils périmés, mais la **réponse causale directe, mesurée et exigée** pour débloquer le volume décisionnel d'OpexAI face à AAAHogEx.

---

## 10. Tranche 0 livrée (2026-09-21)

Implémentée par agy (commit `97936c9`, message provisoire « non relue »), relue ensuite :
`orchestrator.nut` (file réactive avec coalescence, sans producteur ; registre d'exécution à un
travailleur, dispatch par `kind` ; travailleur de test `noop`), bascule dans la boucle de
`main.nut`, sauvegarde et rechargement dans `persist.nut`, réglage `c80_double_register` (défaut 0).
Pas de constante N_max (point ouvert, §3.1.3).

**Relecture.** Au défaut, la boucle est inchangée à un test de drapeau près. Sous le réglage, sans
intention ni travailleur, l'orchestrateur appelle `_runNextTaskWithSlackLedger()` puis `Sleep(1)`,
exactement comme la branche par défaut (`LOOP_BUDGET` désactivé).

**Smoke** (2 graines × 3 ans, 0 échec) : selftest `C80 selftest ok` sur les deux graines ;
graine 100 **identique au bit près** entre réglage 0 et 1 (1 803 818 £) ; graine 42 différente
(2,52 contre 2,74 M£), attendu : l'appel supplémentaire décale les opcodes et la trajectoire est
chaotique (fiche 11 §13.4). `results/c80_smoke_2x3.json`, `results/c80_smoke_on.json`.

## 11. Tranche 1 livrée : l'A* rail dans le registre (2026-09-21)

Implémentée par agy, relue. Réglage `c80_worker_rail` (défaut 0, effectif seulement sous
`c80_double_register=1`). Le travailleur `rail_search` référence `_railSearch` (seule source de
vérité) ; sa tranche passe par `_advanceRailSearchSliceWithLedgers()` (mêmes ledgers C41.46/C39.6),
puis la file de fond enchaîne dans le même tick ; `_railWorkerSteppedThisTick` empêche
`_runNextTask` de rejouer la tranche. Correction de relecture : l'extension rail reste avant la
tranche A*, comme aujourd'hui. Sauvegarde : le pathfinder n'est pas sauvegardé (comme avant), le
travailleur est abandonné proprement au rechargement. Selftest étendu (intercalation d'une
intention entre deux tranches) : `C80 selftest ok` sur les deux graines.

**Smoke** (2 × 3 ans, 0 échec) : le bras `c80_double_register=1` seul reproduit au bit près la
tranche 0 (chemin historique intact). Avec le travailleur : graine 100 1,78 contre 1,80 M£,
graine 42 2,84 contre 2,74 M£. **Identité non démontrée** : le travailleur ajoute quelques
centaines d'opcodes par tick pendant une recherche et décale la trajectoire (même effet qu'au §13.4
de la fiche 11) ; aucune différence de logique n'a été trouvée à la relecture.

## 12. Tranche 2 livrée : découpage de la croissance urbaine (2026-09-21)

Implémentée par agy. Réglage `c80_worker_town` (défaut 0, effectif seulement sous `c80_double_register=1`).
Découpage de `_tryTownGrowth` en deux morceaux partagés : préparation (`_prepareTownGrowth`) et traitement unitaire (`_tryTownGrowthCity`), préservant strictement le chemin monolithique historique au défaut.
Le travailleur `town_growth` parcourt les mêmes villes dans le même ordre, 1 ville par tranche (`cursorTownIndex`, liste de villes `servedTownsList` figée à l'initialisation).
Arrêt immédiat ("done") dès qu'une ligne est construite, ou quand toutes les villes sont parcourues sans construction.
Enchaînement tick : comme `rail_search`, sa tranche est jouée puis la file de fond enchaîne dans le même tick.
Quand la file de fond arrive sur la tâche `town_growth` alors qu'un travailleur `town_growth` tourne déjà, la tâche laisse avancer la file (mécanique noop).
Registre à emplacement unique : si le registre est occupé par un autre travailleur (ex. `rail_search`), la tâche `town_growth` retombe sur le chemin monolithique historique pour ce passage.
Persistance : `cursorTownIndex`, `servedTownsList`, `year` (entiers et tableaux d'entiers uniquement) ; au rechargement, les villes devenues invalides sont sautées et `ai` est réattaché.
Sonde C80-4 : mesure des opcodes par tranche sous `probe_scheduler` (`C39_PASS_CLOCK_LEDGER`), publication annuelle via `OpexC39PassClockLog(phase=town_worker_year year=.. slices=.. ops_max=.. ops_total=.. built=..)`.
Selftest : cas 5 ajouté (simulation de 3 villes avec arrêt après la première construction), `C80 selftest ok` reste l'unique ligne journalisée.
Au défaut : code exécuté inchangé à des tests de drapeaux près.

## 12. Tranche 2 : `town_growth` en travailleur, mesure (2026-09-21)

Implémentée par agy, relue (§ revue à venir, étape 3). Réglage `c80_worker_town` (défaut 0).
Mesure 3 graines × 10 ans en solo, sur le **nouveau défaut** (C75 + C69 bis + C70), horloge C39.6,
avec et sans travailleur (`results/c80t2_on.json`, `results/c80t2_off.json`, 0 échec, selftest ok
sur les 3 graines).

| par partie | 1972 sans → avec | 1975 | 1978 |
|---|---|---|---|
| passes `projects` par an | 15,7 → **23,7** | 4,3 → 4,7 | 2,7 → 3,7 |
| jours de file imputés à `town_growth` | 97 → 3 | 90 → 4 | 69 → 3 |

- **Le tour raccourcit surtout en début de partie** (+50 % de passes en 1972), peu ensuite : sous
  C75, les passes sont déjà rares (4 par an en 1975) et c'est la régénération qui domine.
- ⚠️ Les jours imputés à `town_growth` chutent parce que le travail est passé dans les tranches du
  travailleur, que l'horloge C39.6 n'impute à aucune tâche ; la baisse n'est pas un gain net.
- ❌ **Critère C80-4 non tenu** : une tranche (une ville) coûte jusqu'à **0,24 à 1,39 M opcodes**,
  pas ≤ 150 k : planifier et bâtir une ligne de bus dans une ville est déjà lourd.
- **Identité au défaut non tenue** : graine 42 identique à l'état d'avant la tranche (3 153 311 £),
  graine 100 différente (2 144 974 contre 2 078 509 £). Le refactor de `_tryTownGrowth` est exécuté
  au défaut : à examiner en priorité à l'étape 3 de la revue (`revue_code_2026-09-21_plan.md`).

## 13. Tranche 3 : C76 étape 2, régénération pilotée par les couches (2026-09-21)

Implémentée par agy (réglage `c76_regen_targeted`, défaut 0 ; fonctionne sans C80 ; sous
`c80_double_register`, un événement enfile une intention réactive « regen »). `_dispatchCatalog`
ne régénère que si une couche a changé, si le vivier est invalidé, si le budget a doublé, au
filet trimestriel ou au rechargement ; sinon il resélectionne le vivier existant contre le capital
du moment. Selftest `C76 selftest ok`. Sonde : champ « jours » corrigé, raisons publiées.

**Correctif de relecture (Claude).** Chaque ligne construite incrémente la couche `lines`, dont
dépendent tous les modes : la régénération complète repartait presque à chaque tour, alors que la
mise à jour incrémentale qui suit un chantier a déjà intégré la ligne. La couche `lines` est
désormais acquittée après cette mise à jour.

Mesure 3 graines × 6 ans, solo, `probe_catalogue` (`results/c80t3.json`, `results/c80t3b.json`) :

| version | complètes | évitées | part évitée | raisons des complètes |
|---|--:|--:|--:|---|
| agy | 133 | 26 | 16 % | couches 109, trimestre 17, démarrage 6, budget 1 |
| + acquittement de `lines` | 103 | 48 | **32 %** | couches 49, **trimestre 42**, démarrage 6, budget 6 |

**Critère C80-5 (≥ 50 %) non atteint.** Le filet trimestriel est devenu la première cause : avec un
tour de ~45 jours, il force une régénération complète à peu près un tour sur deux. Le contrat
(§5.3) prévoyait une cadence **semestrielle ou annuelle** ; la consigne de la tranche disait
trimestrielle. Décision utilisateur requise sur la période du filet.

**Décision utilisateur du 2026-09-21 : filet périodique ANNUEL.** Mesure (3 × 6 ans,
`results/c80t3c.json`) : **68 complètes, 79 évitées, 54 %** ; raisons des complètes : couches 45,
annuel 9, budget 8, démarrage 6. **Critère C80-5 atteint.** Correctif associé : l'orchestrateur
enregistrait la dernière régénération réactive en numéro de trimestre (~7 900) alors que la tâche
catalogue compare des années (~1 975) : sous C80, le filet aurait été désactivé pour toujours
après la première régénération sur événement. Les deux utilisent désormais l'année.
