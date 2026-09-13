# Architecture d'`ai/OpexAI/` — schémas

État relevé le 2026-09-13 après la clôture de C65 (passes 1 à 3) : 34 fichiers `.nut`,
27 266 lignes, `main.nut` réduit à 540 lignes. Les arêtes des schémas viennent du graphe
d'appels extrait par grep (symbole défini dans A, référencé dans le code de B) ; l'annexe donne
la matrice complète. Les tailles sont en lignes.

## Rôle de chaque fichier

| Couche | Fichier | Lignes | Rôle et symboles d'entrée |
|---|---|---:|---|
| Entrée | `info.nut` | 2 643 | `OpexAIInfo` : déclaration des réglages et drapeaux d'expérience (`AddSetting`) |
| Entrée | `main.nut` | 540 | En-tête, `import`, 17 `const`, deux blocs `require`, classe `OpexAI` (champs, constructeur = file des 15 tâches, prototypes), `Start()` |
| Entrée | `globals_pre.nut` | 414 | 174 globales `X <-` chargées **avant** les modules du bloc 1 |
| Entrée | `globals_post.nut` | 269 | 51 globales chargées **après** le bloc 1 (`CASH_CANDIDATE_SCAN_LIMIT <- TOP_K` dépend de `candidates.nut`) |
| Entrée | `settings.nut` | 336 | `OpexLoadSettings()` : 213 `AIController.GetSetting` → globales, appelée par `Start()` |
| Boucle | `events.nut` | 357 | `_processEvents` (dispatch des `AIEvent`), `_markDirty`, `_logStalenessRefresh`, `OpexC52EventExposureObserve` |
| Boucle | `event_handlers.nut` | 822 | 14 handlers `_onVehicleCrashed` … `_onStationFirstVehicle` |
| Boucle | `scheduler.nut` | 241 | `_runNextTaskWithSlackLedger`, `_runNextTask` : tête reprenable (rail) puis dispatch par `task.name` |
| Boucle | `scheduler_tasks.nut` | 703 | 15 dispatchs `_dispatchCatalog` … `_dispatchRepay` |
| Tâche | `task_air.nut` | 737 | `_tryBuildAir`, `_tryBuildAirProject`, `_resizeAirFleets`, `_markAirFailedSites`, `OpexAirBatch*`, `OpexAirFleet*` |
| Tâche | `task_rail.nut` | 1 102 | `_tryBuildRailProject`, `_expandRailLines`, `_startRailSearch` / `_continueRailSearch` / `_consumeRailSearch`, `_continueRailExpansion`, `_recordRailAttempt`, `_startRailUpgradeSearch` / `_consumeRailUpgrade`, helpers de réparation `OpexC41Rail*` |
| Tâche | `task_road.nut` | 491 | `_tryBuildRoadProject`, `_refleetRoadLines` |
| Tâche | `task_water.nut` | 103 | `_tryBuildWaterProject`, `_refleetCrashedWaterLines`, `OpexWaterBatchSiteStillBuildable` |
| Tâche | `task_feeders.nut` | 382 | `_tryBuildFeeders`, `_tryBuildMailFeeder`, `OpexFeederCandidateCompare`, `OpexMailRollbackStop(s)` |
| Tâche | `task_projects.nut` | 846 | `_tryBuildProjects`, `_rebuildProjects`, lot dynamique (`_refreshDynamicBatch`, `_dynamicBatchBuilt`, `_dynamicBatchRejected`, `_stopDynamicBatch`), `_tryBuildFleetProject`, `_c39StampFinanceable`, `_purgeSubsidyFromProjects` |
| Tâche | `task_town.nut` | 213 | `_tryTownGrowth`, `OpexCountTownStations`, `OpexGetServedTowns` |
| Tâche | `task_report.nut` | 666 | `_reportYear`, `_reportLines`, `_scrapDeadLines`, `_scrapRetiredVehicles`, `_purgeUnprofitableStreaks`, `_triggerScrapLine` |
| Constructeur | `builder_rail.nut` | 2 144 | Pose du rail : `OpexPrepareRailRoute`, A* segmenté reprenable (`OpexCreateSegmentedSearch`, `OpexAdvanceSegmentedSearch`, `RAIL_SEARCH_SLICE`), `OpexBuildLine`, `OpexQuoteRailCapital`, `OpexUpgradeRailLineToDoubleTrack` |
| Constructeur | `builder_air.nut` | 1 727 | Aéroports et lignes : `OpexAirPlans`, `OpexBuildAirRoute`, `OpexAirAddPlane`, `OpexAirTripModel`, `OpexAirCadenceCap`, `OpexAirDemandCap` |
| Constructeur | `builder_road.nut` | 1 388 | Routes, arrêts, dépôts : `OpexRoadPlanFor`, `OpexBuildRoadRoute`, `OpexRoadRefleet`, `OpexRoadFindOrBuildTruckStop` |
| Constructeur | `builder_water.nut` | 846 | Quais et navires : `OpexWaterPlans`, `OpexBuildWaterRoute`, `OpexWaterRefleetCrashedShip` (chantier non fini) |
| Constructeur | `lib_water.nut` | 610 | Transcription MinchinWeb Lakes : `OpexWaterLakesConnected`, `OpexWaterLakesInstance` ; `import("queue.fibonacci_heap")` |
| Modèle | `catalog.nut` | 884 | `OpexCatalog` : villes, industries, cargos, matériel roulant (`refresh`, `refreshWater`, `refreshRoad`), physique rail (`OpexRailEffectiveSpeed`) |
| Modèle | `candidates.nut` | 3 282 | Génération des candidats : `OpexBuildCandidates` (rail/air/eau), `OpexBuildRoadCandidates`, `OpexRoadFeederCandidates`, `OpexGenerateSubsidyCandidates`, bandes de distance, note municipale (C60) |
| Modèle | `economy.nut` | 704 | Économie d'une ligne : `OpexLineEconomics`, `OpexRoadLineEconomics`, `OpexRoadPhysicalVehicleCap`, `OpexStationRatingForHeadway` |
| Modèle | `projects.nut` | 1 914 | Portefeuille : `OpexBuildProjects`, `OpexProjectScore`, `OpexProjectFinanceCapital` (biais ×1,70 rail / ×1,21 route), `OpexPrequoteRailCandidates`, `OpexIncrementalUpdateProjects` |
| Modèle | `tension.nut` | 689 | Score de tension et prix fictifs : `OpexTensionScore`, `OpexTensionComputeShadowPrices`, `OpexTensionEnable` |
| Modèle | `spatial.nut` | 183 | `OpexSpatialGrid`, `OpexDirectedSpatialGrid` (index des origines fret, C46) |
| Modèle | `capital.nut` | 136 | `OpexCashReserve`, `OpexAvailableCapital`, `OpexTryReborrow`, `_tryRepayLoan` |
| Modèle | `budget.nut` | 92 | `OpexBudget`, `OpexOpsMeasureBegin` / `OpexOpsMeasureEnd` (mesure d'opcodes) |
| Transverse | `lines.nut` | 429 | Identité et registre des lignes : `OpexFindLineForVehicle`, `OpexLineVehicleIds`, `OpexFindStationJoin`, `OpexAbandonedPairKey`, `_markPairAbandoned`, `_tooClose`, `_findLineById` |
| Transverse | `probes.nut` | 447 | Canal de mesure : `OpexSign` (panneaux `AISign`), `OpexDecide` (journal `AILog`), tous les `OpexC*Log` / `Observe` |
| Transverse | `ledgers.nut` | 707 | Registres annuels C39/C41/C48/C49/C50/C52/C54/C55/C60 (`_record*`, `_log*`), `_checkC50MonthlyTreasury` |
| Transverse | `persist.nut` | 219 | `Save` (13 clés courtes / 23 complètes), `Load`, `_reconcileAfterLoad` |

## D1 — Vue en couches

```mermaid
flowchart TB
  classDef moteur fill:#D9DED4,stroke:#4A5A50,color:#18231D
  classDef entree fill:#E4E9F2,stroke:#3B5A8A,color:#18231D
  classDef boucle fill:#F3E3CF,stroke:#B5602A,color:#18231D
  classDef tache fill:#F8ECD9,stroke:#B5602A,color:#18231D
  classDef build fill:#DCEBE1,stroke:#2F7A56,color:#18231D
  classDef modele fill:#D8E8EE,stroke:#1F6F8B,color:#18231D
  classDef trans fill:#ECE6F1,stroke:#6B4E8E,color:#18231D
  classDef sortie fill:#F5F7F2,stroke:#5B6B60,color:#18231D,stroke-dasharray:4 3

  OT["Moteur OpenTTD<br/>API NoAI · AIEvent · budget d'opcodes par tick · Save/Load"]:::moteur

  subgraph E["Entrée"]
    info["info.nut (2 643)<br/>réglages"]:::entree
    main["main.nut (540)<br/>const · classe OpexAI · Start()"]:::entree
    glob["globals_pre.nut (414) · globals_post.nut (269)<br/>225 globales"]:::entree
    settings["settings.nut (336)<br/>OpexLoadSettings"]:::entree
  end

  subgraph B["Boucle de jeu"]
    events["events.nut (357)<br/>_processEvents · _markDirty"]:::boucle
    handlers["event_handlers.nut (822)<br/>14 handlers _onXxx"]:::boucle
    sched["scheduler.nut (241)<br/>_runNextTask"]:::boucle
    dispatch["scheduler_tasks.nut (703)<br/>15 dispatchs _dispatchXxx"]:::boucle
  end

  subgraph T["Tâches (une famille par fichier)"]
    t_air["task_air (737)"]:::tache
    t_rail["task_rail (1 102)"]:::tache
    t_road["task_road (491)"]:::tache
    t_water["task_water (103)"]:::tache
    t_feed["task_feeders (382)"]:::tache
    t_proj["task_projects (846)"]:::tache
    t_town["task_town (213)"]:::tache
    t_rep["task_report (666)"]:::tache
  end

  subgraph C["Constructeurs"]
    b_air["builder_air (1 727)"]:::build
    b_rail["builder_rail (2 144)"]:::build
    b_road["builder_road (1 388)"]:::build
    b_water["builder_water (846)"]:::build
    lib_w["lib_water (610)"]:::build
  end

  subgraph M["Modèle de décision"]
    catalog["catalog (884)"]:::modele
    cand["candidates (3 282)"]:::modele
    econ["economy (704)"]:::modele
    proj["projects (1 914)"]:::modele
    tension["tension (689)"]:::modele
    spatial["spatial (183)"]:::modele
    capital["capital (136)"]:::modele
    budget["budget (92)"]:::modele
  end

  subgraph X["Transverse"]
    lines["lines (429)"]:::trans
    probes["probes (447)<br/>OpexSign · OpexDecide"]:::trans
    ledgers["ledgers (707)"]:::trans
    persist["persist (219)<br/>Save · Load"]:::trans
  end

  sweeps["Panneaux AISign → chunk SIGN des sauvegardes → sweeps/*.py"]:::sortie

  OT -->|Start / Save / Load| main
  info -.->|GetSetting| settings
  main --> settings
  main -->|_processEvents| events
  main -->|_runNextTaskWithSlackLedger| sched
  events --> handlers
  sched --> dispatch
  dispatch --> T
  T --> C
  b_water --> lib_w
  catalog --> cand --> econ
  cand --> proj
  spatial --> cand
  tension --> proj
  capital --> proj
  proj --> t_proj
  t_proj --> t_air
  t_proj --> t_rail
  t_proj --> t_road
  t_proj --> t_water
  handlers -->|arme c41_* · dueCycle=0| sched
  T --> lines
  T --> probes
  C --> probes
  M --> probes
  dispatch -->|tâche report| ledgers
  persist --> OT
  probes --> sweeps
```

## D2 — Ordre de chargement

Deux contraintes Squirrel fixent cet ordre : `main.nut` est compilé **entier** avant que le premier
`require()` ne s'exécute (les 17 `const` sont donc visibles de tous les modules, mais une `const`
déplacée serait invisible de `main.nut`), et un fichier de méthodes `function OpexAI::x()` ne peut
être requis qu'**après** la déclaration de la classe.

```mermaid
flowchart LR
  classDef step fill:#E4E9F2,stroke:#3B5A8A,color:#18231D
  classDef mod fill:#D8E8EE,stroke:#1F6F8B,color:#18231D
  classDef cls fill:#F3E3CF,stroke:#B5602A,color:#18231D
  classDef note fill:#F5F7F2,stroke:#B8321F,color:#18231D,stroke-dasharray:4 3

  c0["Compilation de main.nut entier<br/>17 const → table des constantes"]:::step
  c1["import pathfinder.rail v1"]:::step
  g1["require globals_pre.nut<br/>174 slots"]:::step
  subgraph R1["Bloc require 1 (l. 42-52)"]
    direction TB
    r1["budget → catalog → economy → spatial → candidates<br/>→ tension → projects → builder_rail → builder_air<br/>→ builder_water (→ lib_water) → builder_road"]:::mod
  end
  g2["require globals_post.nut<br/>51 slots, dont CASH_CANDIDATE_SCAN_LIMIT ← TOP_K"]:::step
  k["class OpexAI extends AIController (l. 101-400)<br/>champs · constructeur : _taskQueue des 15 tâches · prototypes"]:::cls
  subgraph R2["Bloc require 2 (l. 403-420) — méthodes OpexAI::"]
    direction TB
    r2["capital · events · event_handlers · ledgers · lines · persist<br/>probes · scheduler · scheduler_tasks · settings<br/>task_air · task_feeders · task_projects · task_rail<br/>task_report · task_road · task_town · task_water"]:::mod
  end
  s["OpexAI::Start() (l. 422)"]:::step
  ld["Moteur : Load() si sauvegarde, puis Start()"]:::step

  n1["Piège 1 : les const restent dans main.nut"]:::note
  n2["Piège 2 : méthodes requises APRÈS la classe"]:::note

  c0 --> c1 --> g1 --> R1 --> g2 --> k --> R2 --> s --> ld
  n1 -.- c0
  n2 -.- R2
```

## D3 — Cycle d'exécution

```mermaid
sequenceDiagram
  autonumber
  participant OT as Moteur OpenTTD
  participant S as main.nut · Start()
  participant SET as settings.nut
  participant P as persist.nut
  participant EV as events.nut
  participant EH as event_handlers.nut
  participant SC as scheduler.nut
  participant ST as scheduler_tasks.nut
  participant TK as task_*.nut

  OT->>S: Start()
  S->>SET: OpexLoadSettings() — 213 GetSetting → globales
  S->>S: FLEET_BEFORE_NEW ? échange air / air_fleet<br/>C41_WATER/ROAD_REFRESH ? arme c41_water / c41_road
  opt partie chargée
    S->>P: _reconcileAfterLoad() — filtre _lines et véhicules contre le monde
  end
  loop chaque passe (Sleep entre deux)
    S->>EV: _processEvents()
    EV->>EH: _onXxx(event), un handler par type d'événement
    EH-->>SC: dueCycle = 0 · enabled = true sur les tâches concernées
    S->>SC: _runNextTaskWithSlackLedger()
    SC->>TK: tête : _continueRailExpansion / _continueRailSearch (task_rail)
    SC->>SC: _checkC50MonthlyTreasury (ledgers) · tâche due par _taskCursor
    SC->>ST: _dispatchXxx(task, year)
    ST->>TK: _tryBuild… / _refleet… / _report… / _scrap…
    TK-->>ST: dueCycle reporté ou tâche rejouée
  end
  OT->>P: Save() — 13 clés (23 si save_full_state)
```

## D4 — Dispatch des 15 tâches

Ordre de la file tel que le constructeur la bâtit ; `Start()` échange `air` et `air_fleet` quand
`FLEET_BEFORE_NEW=1`. Les quatre tâches `c41_*` naissent désarmées (`dueCycle` infini) et sont
armées par des événements.

```mermaid
flowchart LR
  classDef q fill:#F3E3CF,stroke:#B5602A,color:#18231D
  classDef qoff fill:#F5F7F2,stroke:#B5602A,color:#5B6B60,stroke-dasharray:4 3
  classDef dst fill:#D8E8EE,stroke:#1F6F8B,color:#18231D

  subgraph Q["_taskQueue — un _dispatchXxx par entrée (scheduler_tasks.nut)"]
    direction TB
    q1["catalog"]:::q
    q2["c41_water"]:::qoff
    q3["c41_road"]:::qoff
    q4["c41_rail_signals"]:::qoff
    q5["c41_rail_junction"]:::qoff
    q6["report"]:::q
    q7["scrap"]:::q
    q8["air"]:::q
    q9["air_fleet"]:::q
    q10["feeders"]:::q
    q11["projects"]:::q
    q12["expand"]:::q
    q13["refleet"]:::q
    q14["town_growth"]:::q
    q15["repay"]:::q
  end

  d1["catalog.nut · OpexCatalog.refresh<br/>task_projects · _rebuildProjects · _c39StampFinanceable<br/>lines · _pruneAbandonedPairs"]:::dst
  d2["catalog.nut · refreshWater<br/>builder_water · OpexWaterPlans"]:::dst
  d3["catalog.nut · refreshRoad"]:::dst
  d4["task_rail · OpexC41BuildPbsAtApproach"]:::dst
  d5["task_rail · OpexC41RailApproachLead · OpexC41RepairJunction"]:::dst
  d6["ledgers · 14 _log* annuels<br/>task_report · _reportYear · _reportLines<br/>probes · OpexCashReserveProbeLog"]:::dst
  d7["task_report · _scrapDeadLines · _scrapRetiredVehicles · _purgeUnprofitableStreaks"]:::dst
  d8["task_air · _tryBuildAir"]:::dst
  d9["task_air · _resizeAirFleets<br/>projects · OpexIncrementalUpdateProjects"]:::dst
  d10["task_feeders · _tryBuildFeeders"]:::dst
  d11["capital · OpexAvailableCapital<br/>task_projects · _tryBuildProjects"]:::dst
  d12["task_rail · _expandRailLines"]:::dst
  d13["task_road · _refleetRoadLines<br/>task_water · _refleetCrashedWaterLines"]:::dst
  d14["task_town · _tryTownGrowth"]:::dst
  d15["capital · _tryRepayLoan"]:::dst

  q1 --> d1
  q2 --> d2
  q3 --> d3
  q4 --> d4
  q5 --> d5
  q6 --> d6
  q7 --> d7
  q8 --> d8
  q9 --> d9
  q10 --> d10
  q11 --> d11
  q12 --> d12
  q13 --> d13
  q14 --> d14
  q15 --> d15
```

## D5 — Pipeline de décision

Du monde observé à la ligne construite : chaque étage ne connaît que le précédent, et
`task_projects.nut` est le seul point où un projet devient un chantier.

```mermaid
flowchart LR
  classDef modele fill:#D8E8EE,stroke:#1F6F8B,color:#18231D
  classDef tache fill:#F8ECD9,stroke:#B5602A,color:#18231D
  classDef build fill:#DCEBE1,stroke:#2F7A56,color:#18231D
  classDef trans fill:#ECE6F1,stroke:#6B4E8E,color:#18231D

  catalog["catalog.nut<br/>OpexCatalog.refresh<br/>villes · industries · cargos · matériel"]:::modele
  cand["candidates.nut<br/>OpexBuildCandidates (rail · air · eau)<br/>OpexBuildRoadCandidates<br/>OpexGenerateSubsidyCandidates"]:::modele
  econ["economy.nut<br/>OpexLineEconomics<br/>OpexRoadLineEconomics"]:::modele
  spatial["spatial.nut<br/>OpexDirectedSpatialGrid"]:::modele
  lines["lines.nut<br/>OpexJoinCompatible · OpexAbandonedPairKey"]:::trans
  proj["projects.nut<br/>OpexBuildProjects · OpexProjectScore<br/>OpexProjectFinanceCapital (×1,70 rail · ×1,21 route)<br/>OpexPrequoteRailCandidates"]:::modele
  tension["tension.nut<br/>OpexTensionScore · prix fictifs"]:::modele
  capital["capital.nut<br/>OpexAvailableCapital · OpexCashReserve"]:::modele
  budget["budget.nut<br/>OpexOpsMeasureBegin / End"]:::modele
  brail["builder_rail.nut<br/>OpexQuoteRailCapital · OpexPlanRailRoute"]:::build
  bair["builder_air.nut<br/>OpexAirPlans"]:::build
  bwater["builder_water.nut<br/>OpexWaterPlans"]:::build
  tproj["task_projects.nut<br/>_tryBuildProjects · lot dynamique<br/>_rebuildProjects"]:::tache
  trail["task_rail · _tryBuildRailProject"]:::tache
  tair["task_air · _tryBuildAirProject"]:::tache
  troad["task_road · _tryBuildRoadProject"]:::tache
  twater["task_water · _tryBuildWaterProject"]:::tache
  tfleet["task_projects · _tryBuildFleetProject"]:::tache

  catalog -->|OpexRailEffectiveSpeed| cand
  econ --> cand
  spatial --> cand
  lines --> cand
  cand -->|19 symboles| proj
  tension -->|7 symboles| proj
  capital --> proj
  brail -->|devis rail avant élection| proj
  bair --> proj
  bwater --> proj
  budget -.->|mesure d'opcodes| catalog
  budget -.-> cand
  budget -.-> proj
  proj -->|OpexBuildProjects · OpexReselectProjects| tproj
  tproj --> trail
  tproj --> tair
  tproj --> troad
  tproj --> twater
  tproj --> tfleet
```

## D6 — Constructeurs par mode

```mermaid
flowchart LR
  classDef tache fill:#F8ECD9,stroke:#B5602A,color:#18231D
  classDef build fill:#DCEBE1,stroke:#2F7A56,color:#18231D
  classDef trans fill:#ECE6F1,stroke:#6B4E8E,color:#18231D
  classDef state fill:#F5F7F2,stroke:#B8321F,color:#18231D,stroke-dasharray:4 3

  subgraph AIR["Air"]
    tair["task_air.nut<br/>_tryBuildAir · _tryBuildAirProject · _resizeAirFleets"]:::tache
    bair["builder_air.nut<br/>OpexAirPlans · OpexBuildAirRoute · OpexAirAddPlane<br/>OpexAirTripModel · OpexAirCadenceCap"]:::build
    tair -->|9 symboles| bair
  end

  subgraph RAIL["Rail"]
    trail["task_rail.nut<br/>_tryBuildRailProject · _expandRailLines<br/>_startRailSearch → _continueRailSearch → _consumeRailSearch"]:::tache
    brail["builder_rail.nut<br/>OpexPrepareRailRoute · OpexCreateSegmentedSearch<br/>OpexAdvanceSegmentedSearch (RAIL_SEARCH_SLICE)<br/>OpexBuildLine · OpexUpgradeRailLineToDoubleTrack"]:::build
    st["États reprenables sur l'instance<br/>_railSearch · _railExpansion<br/>consommés en tête de _runNextTask"]:::state
    trail -->|14 symboles| brail
    st -.- trail
  end

  subgraph ROUTE["Route"]
    troad["task_road.nut<br/>_tryBuildRoadProject · _refleetRoadLines"]:::tache
    tfeed["task_feeders.nut<br/>_tryBuildFeeders · _tryBuildMailFeeder"]:::tache
    ttown["task_town.nut<br/>_tryTownGrowth"]:::tache
    broad["builder_road.nut<br/>OpexRoadPlanFor · OpexBuildRoadRoute · OpexRoadRefleet<br/>OpexRoadFindOrBuildTruckStop"]:::build
    troad --> broad
    tfeed --> broad
    ttown -->|OpexRoadInMap · OpexRoadPlanFor| broad
  end

  subgraph EAU["Eau"]
    twater["task_water.nut<br/>_tryBuildWaterProject · _refleetCrashedWaterLines"]:::tache
    bwater["builder_water.nut<br/>OpexWaterPlans · OpexBuildWaterRoute"]:::build
    libw["lib_water.nut<br/>OpexWaterLakesConnected (Lakes)"]:::build
    twater --> bwater -->|connectivité| libw
  end

  capital["capital.nut<br/>OpexCashReserve · OpexTryReborrow"]:::trans
  lines["lines.nut<br/>_markPairAbandoned · OpexBuildFailureIsAbandonable"]:::trans
  probes["probes.nut<br/>OpexSign · OpexDecide"]:::trans

  AIR --> capital
  RAIL --> capital
  ROUTE --> capital
  EAU --> capital
  AIR --> lines
  RAIL --> lines
  ROUTE --> lines
  AIR --> probes
  RAIL --> probes
  ROUTE --> probes
  EAU --> probes
```

## D7 — Événements, puis mesure et persistance

### D7a — De l'événement à l'effet

```mermaid
flowchart LR
  classDef ev fill:#F3E3CF,stroke:#B5602A,color:#18231D
  classDef eff fill:#D8E8EE,stroke:#1F6F8B,color:#18231D
  classDef q fill:#ECE6F1,stroke:#6B4E8E,color:#18231D

  pe["events.nut · _processEvents<br/>+ OpexC52EventExposureObserve (compte tout)"]:::ev

  subgraph V["Véhicules — event_handlers.nut"]
    vc["_onVehicleCrashed"]:::ev
    vd["_onVehicleWaitingInDepot"]:::ev
    va["_onVehicleAutoreplaced"]:::ev
    vu["_onVehicleUnprofitable"]:::ev
    vl["_onVehicleLost"]:::ev
    vs["_onStationFirstVehicle"]:::ev
  end
  subgraph W["Monde — event_handlers.nut"]
    io["_onIndustryOpen"]:::ev
    ic["_onIndustryClose"]:::ev
    tf["_onTownFounded"]:::ev
    ea["_onEngineAvailable"]:::ev
  end
  subgraph SB["Subventions — event_handlers.nut"]
    so["_onSubsidyOffer"]:::ev
    se["_onSubsidyOfferExpired"]:::ev
    sa["_onSubsidyAwarded"]:::ev
    sx["_onSubsidyExpired"]:::ev
  end

  e1["line.needsRefleet · retrait des files de casse"]:::eff
  e2["vente si _vehiclesToScrap (event_depot_sell)"]:::eff
  e3["re-clé _vehiclesToScrap / _vehiclesToRetire"]:::eff
  e4["_vehiclesToRetire ou _triggerScrapLine (task_report)"]:::eff
  e5["faits rail (task_rail : OpexC41Rail*Facts)<br/>arme c41_rail_signals · c41_rail_junction"]:::q
  e6["OpexDecide STATION_FIRST_VEHICLE (log seul)"]:::eff
  e7["_markDirty (events.nut) : couches catalogue / candidats<br/>dueCycle = 0 sur catalog et projects"]:::q
  e8["_triggerScrapLine (task_report)"]:::eff
  e9["OpexRefreshEpochBounds (candidates)<br/>_markDirty → arme c41_water / c41_road"]:::q
  e10["_activeSubsidies · OpexSubsidyMatchingLineId (candidates)<br/>dueCycle = 0 catalog / projects"]:::q
  e11["_purgeSubsidyFromProjects (task_projects)"]:::eff

  pe --> V
  pe --> W
  pe --> SB
  vc --> e1
  vd --> e2
  va --> e3
  vu --> e4
  vl --> e5
  vs --> e6
  io --> e7
  tf --> e7
  ic --> e7
  ic --> e8
  ea --> e9
  so --> e10
  se --> e11
  sa --> e11
  sx --> e11
```

### D7b — Mesure et persistance

```mermaid
flowchart LR
  classDef trans fill:#ECE6F1,stroke:#6B4E8E,color:#18231D
  classDef moteur fill:#D9DED4,stroke:#4A5A50,color:#18231D
  classDef sortie fill:#F5F7F2,stroke:#5B6B60,color:#18231D,stroke-dasharray:4 3
  classDef src fill:#F8ECD9,stroke:#B5602A,color:#18231D

  all["Tous les modules<br/>(tâches, constructeurs, modèle, boucle)"]:::src
  rep["scheduler_tasks · _dispatchReport (tâche annuelle report)"]:::src
  rec["task_projects · task_rail · task_road · task_air<br/>_recordC48* · _recordC49* · _logC50CashRefusal"]:::src

  probes["probes.nut<br/>OpexSign → AISign.BuildSign (≤ 31 caractères)<br/>OpexDecide → AILog (decision_log)"]:::trans
  ledgers["ledgers.nut<br/>accumulateurs annuels C39 · C41 · C48 · C49 · C50 · C52 · C54 · C55 · C60<br/>14 _log* vidés par report"]:::trans
  persist["persist.nut<br/>Save : 13 clés (23 avec save_full_state)<br/>Load → _pendingLines · _reconcileAfterLoad"]:::trans

  ot["Moteur OpenTTD<br/>sauvegardes mensuelles (OpenTTDLab)"]:::moteur
  sw["sweeps/bench_v2.py · diag_*.py<br/>lecture des chunks SIGN et VEHS"]:::sortie

  all -->|OpexSign · OpexDecide| probes
  rec --> ledgers
  rep --> ledgers
  ledgers -->|OpexC*Log| probes
  probes -->|panneaux sur la carte| ot
  ot -->|Save / Load| persist
  ot --> sw
```

## Annexe — matrice des dépendances (A utilise un symbole défini dans B)

Extraite le 2026-09-13 ; arêtes « `events.nut` → … » et « `scheduler.nut` → … » relevées avant la
passe 3, elles partent aujourd'hui pour l'essentiel de `event_handlers.nut` et
`scheduler_tasks.nut`.

| A (appelant) | B (appelé) | symboles | exemples |
|---|---|---:|---|
| builder_air | candidates | 4 | OpexBoostTownRating, OpexC60ObserveTownRating, OpexTownRatingHopeless, OpexAirPairInBand |
| builder_air | capital | 2 | OpexCashReserve, OpexTryReborrow |
| builder_air | economy | 2 | OpexCeilDiv, OpexStationRatingForHeadway |
| builder_air | probes | 2 | OpexDecide, OpexSign |
| builder_rail | economy | 3 | OpexLineEconomics, OpexApplyRailEconomics, OpexApplyRailActualCapital |
| builder_rail | catalog | 2 | OpexRailMinimumPlatformLength, OpexRailNominalMaxWagons |
| builder_rail | capital | 1 | OpexTryReborrow |
| builder_rail | probes | 1 | OpexDecide |
| builder_road | capital | 1 | OpexCashReserve |
| builder_road | lines | 1 | OpexLineVehicleIds |
| builder_road | probes | 1 | OpexDecide |
| builder_water | budget | 2 | OpexOpsMeasureBegin, OpexOpsMeasureEnd |
| builder_water | capital | 1 | OpexCashReserve |
| builder_water | economy | 1 | OpexStationRatingForHeadway |
| builder_water | lib_water | 1 | OpexWaterLakesConnected |
| builder_water | probes | 1 | OpexC56TaskLog |
| candidates | economy | 5 | OpexLineEconomics, OpexRoadLineEconomics, OpexRoadPaxUniqueMonthly, OpexCeilDiv |
| candidates | lines | 3 | OpexLineStationId, OpexJoinCompatible, OpexAbandonedPairKey |
| candidates | budget | 2 | OpexOpsMeasureBegin, OpexOpsMeasureEnd |
| candidates | probes | 2 | OpexDecide, OpexC55OriginRelaxObserve |
| candidates | catalog | 1 | OpexRailEffectiveSpeed |
| candidates | spatial | 3 | OpexIsqrt, OpexSpatialGrid, OpexDirectedSpatialGrid |
| capital | probes | 2 | OpexDecide, OpexSign |
| catalog | budget | 2 | OpexOpsMeasureBegin, OpexOpsMeasureEnd |
| catalog | candidates | 1 | OpexRefreshEpochBounds |
| catalog | probes | 1 | OpexDecide |
| economy | catalog | 3 | OpexRailNominalMaxWagons, OpexRailEffectiveSpeed, OpexRailWantedPlatformLength |
| economy | budget | 2 | OpexOpsMeasureBegin, OpexOpsMeasureEnd |
| events (+ handlers) | probes | 15 | OpexC39ProjectSignature, OpexC39Log, OpexC41RevisionSnapshot, OpexC41VehicleLostLog |
| events (+ handlers) | task_rail | 4 | OpexC41RailApproachFacts, OpexC41RailDepotFrontFacts, OpexC41RailApproachLead, OpexC41RailLocalLinks |
| events (+ handlers) | lines | 3 | OpexFindLineForVehicle, OpexC41PersistedLineForVehicle, OpexLineStationId |
| events (+ handlers) | candidates | 2 | OpexSubsidyMatchingLineId, OpexRefreshEpochBounds |
| events (+ handlers) | catalog | 1 | OpexCatalog.isWaterEngineRelevant |
| events (+ handlers) | task_projects | 1 | _purgeSubsidyFromProjects |
| events (+ handlers) | task_report | 1 | _triggerScrapLine |
| ledgers | probes | 18 | OpexC41SchedulerLog, OpexC49ScarcityLog, OpexC50ChronologyLog, OpexC52AutoreplaceLog |
| ledgers | builder_air | 2 | OpexAirCadenceCap, OpexAirDemandCap |
| ledgers | capital | 1 | OpexAvailableCapital |
| ledgers | lines | 1 | OpexC41PersistedLineForVehicle |
| lib_water | budget | 2 | OpexOpsMeasureBegin, OpexOpsMeasureEnd |
| lib_water | probes | 1 | OpexC56TaskLog |
| lines | probes | 1 | OpexDecide |
| main | probes | 2 | OpexDecide, OpexC56TaskLog |
| main | budget · catalog | 2 | OpexBudget(), OpexCatalog() (constructeur) |
| main | builder_air | 1 | OpexAirResetSiteCache |
| main | capital | 1 | OpexCashReserve |
| main | events · persist · scheduler · settings · tension | 5 | _processEvents, _reconcileAfterLoad, _runNextTaskWithSlackLedger, OpexLoadSettings, OpexTensionEnable |
| persist | probes | 1 | OpexDecide |
| persist | task_report | 1 | _purgeUnprofitableStreaks |
| probes | candidates | 1 | OpexRoadPairServed |
| probes | capital | 1 | OpexAvailableCapital |
| projects | candidates | 19 | OpexBuildCandidates, OpexBuildRoadCandidates, OpexTopK, OpexGenerateSubsidyCandidates |
| projects | tension | 7 | OpexTensionContext, OpexTensionVector, OpexTensionScore, OpexTensionComputeShadowPrices |
| projects | probes | 6 | OpexDecide, OpexC39Log, OpexC56TaskLog, OpexC55PaxTraceObserveRevalidated |
| projects | builder_rail | 3 | OpexRailTerrainScanProbe, OpexPlanRailRoute, OpexQuoteRailCapital |
| projects | task_air | 3 | OpexAirBatchPlanStillLive, OpexAirBatchSiteStillBuildable, OpexAirBatchPlanStillLiveIndexed |
| projects | budget | 2 | OpexOpsMeasureBegin, OpexOpsMeasureEnd |
| projects | builder_air | 2 | OpexAirSiteAbandonKey, OpexAirPlans |
| projects | economy | 2 | OpexApplyRailActualCapital, OpexCeilDiv |
| projects | builder_water · capital · ledgers · lines · task_water | 5 | OpexWaterPlans, OpexAvailableCapital, OpexC48IncrementalRecord, OpexAbandonedPairKey, OpexWaterBatchSiteStillBuildable |
| scheduler (+ tasks) | ledgers | 20 | _logC41SlackLedger, _checkC50MonthlyTreasury, _logC50AnnualReport, _logC39PassClockLedger |
| scheduler (+ tasks) | probes | 10 | OpexC56TaskLog, OpexDecide, OpexSign, OpexC39Log |
| scheduler (+ tasks) | task_rail | 6 | _continueRailExpansion, _continueRailSearch, _expandRailLines, OpexC41RepairJunction |
| scheduler (+ tasks) | task_report | 5 | _reportYear, _reportLines, _scrapDeadLines, _scrapRetiredVehicles |
| scheduler (+ tasks) | task_projects | 3 | _rebuildProjects, _c39StampFinanceable, _tryBuildProjects |
| scheduler (+ tasks) | catalog | 3 | OpexCatalog.refresh, refreshWater, refreshRoad |
| scheduler (+ tasks) | budget · capital · lines · projects · task_air | 10 | OpexOpsMeasureBegin, OpexAvailableCapital, _tryRepayLoan, _pruneAbandonedPairs, _findLineById, OpexLogPortfolioRank, OpexIncrementalUpdateProjects, _resizeAirFleets, _tryBuildAir |
| scheduler (+ tasks) | builder_water · candidates · events · task_feeders · task_road · task_town · task_water | 7 | OpexWaterPlans, OpexRefreshEpochBounds, _logStalenessRefresh, _tryBuildFeeders, _refleetRoadLines, _tryTownGrowth, _refleetCrashedWaterLines |
| settings | probes | 1 | OpexC50ResetNonExpansionLedger |
| task_air | builder_air | 9 | OpexBuildAirRoute, OpexAirPlans, OpexAirAddPlane, OpexAirRefleetCrashedPlane |
| task_air | probes | 3 | OpexDecide, OpexSign, OpexC50LogCashRefusal |
| task_air | candidates · capital · lines · ledgers | 7 | OpexC60ObserveTownRating, OpexTownRatingHopeless, OpexCashReserve, OpexTryReborrow, _markPairAbandoned, OpexBuildFailureIsAbandonable, _logC50CashRefusal |
| task_feeders | builder_road | 4 | OpexRoadPlanFor, OpexBuildRoadRoute, OpexRoadFindOrBuildTruckStop, OpexRoadRefitCapacity |
| task_feeders | candidates | 4 | OpexRoadFeederCandidates, OpexTownFeederCount, OpexRoadPairServed, OpexTownRoadLineCount |
| task_feeders | lines | 4 | OpexAbandonedPairKey, OpexLineStationId, _markPairAbandoned, OpexBuildFailureIsAbandonable |
| task_feeders | economy · capital · probes | 7 | OpexCeilDiv, OpexRoadLineEconomics, OpexApplyRoadEconomics, OpexCashReserve, OpexTryReborrow, OpexSign, OpexDecide |
| task_projects | projects | 6 | OpexBuildProjects, OpexReselectProjects, OpexIncrementalUpdateProjects, OpexDynamicBatchReselect |
| task_projects | probes | 5 | OpexDecide, OpexSign, OpexC50ChronologyLog, OpexC41ProjectsFallthroughLog |
| task_projects | ledgers | 4 | _logC50CashRefusal, _recordC48PassLedger, _recordC49ScarcityPass, _recordC48AttemptLedger |
| task_projects | capital | 3 | OpexCashReserve, OpexTryReborrow, OpexAvailableCapital |
| task_projects | task_air · task_rail · task_road · task_water | 6 | _resizeAirFleets, _tryBuildAirProject, _consumeRailSearch, _tryBuildRailProject, _tryBuildRoadProject, _tryBuildWaterProject |
| task_projects | budget · builder_air · candidates | 4 | OpexOpsMeasureBegin, OpexOpsMeasureEnd, OpexAirAddPlane, OpexFreightCargoOrder |
| task_rail | builder_rail | 14 | OpexPrepareRailRoute, OpexCreateSegmentedSearch, OpexAdvanceSegmentedSearch, OpexBuildLine |
| task_rail | lines | 6 | OpexAbandonedPairKey, _tooClose, OpexFindStationJoin, _findLineById |
| task_rail | probes | 5 | OpexSign, OpexDecide, OpexC50ChronologyLog, OpexC41RailDominationLog |
| task_rail | candidates · capital | 6 | OpexGetCandidateTownEndpoints, OpexC60ObserveTownRating, OpexTownRatingAllowStation, OpexCashReserve, OpexTryReborrow, OpexAvailableCapital |
| task_rail | catalog · economy · ledgers | 3 | OpexRailNominalMaxWagons, OpexRailFixedConsist, _logC50CashRefusal |
| task_report | lines | 4 | OpexLineVehicleType, OpexLineVehicleIds, OpexMedianInt, _findLineById |
| task_report | probes | 3 | OpexSign, OpexC50ChronologyLog, OpexDecide |
| task_road | candidates | 9 | OpexGetCandidateTownEndpoints, OpexTownRatingAllowStation, OpexRoadPairServed, OpexSubsidyChantierDays |
| task_road | probes | 9 | OpexDecide, OpexSign, OpexC55PaxTraceObserveAttempted, OpexC50ChronologyLog |
| task_road | economy | 4 | OpexCeilDiv, OpexRoadLineEconomics, OpexApplyRoadEconomics, OpexRoadPhysicalVehicleCap |
| task_road | lines | 4 | OpexAbandonedPairKey, _markPairAbandoned, OpexBuildFailureIsAbandonable, OpexLineVehicleIds |
| task_road | builder_road | 3 | OpexRoadPlanFor, OpexBuildRoadRoute, OpexRoadRefleet |
| task_road | capital · ledgers · task_projects | 4 | OpexCashReserve, OpexTryReborrow, _logC50CashRefusal, _purgeSubsidyFromProjects |
| task_town | builder_road | 3 | OpexRoadInMap, OpexRoadPlanFor, OpexBuildRoadRoute |
| task_town | probes · capital | 3 | OpexDecide, OpexSign, OpexCashReserve |
| task_water | builder_water | 2 | OpexBuildWaterRoute, OpexWaterRefleetCrashedShip |
| task_water | capital · probes · ledgers | 5 | OpexCashReserve, OpexTryReborrow, OpexSign, OpexDecide, _logC50CashRefusal |

Sans arête sortante : `tension.nut`, `spatial.nut`, `budget.nut`, `info.nut` (ses seules mentions
de symboles sont dans des commentaires et descriptions de réglages). Sans arête entrante :
`main.nut`, `info.nut`.
