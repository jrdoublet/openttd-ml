# Revue 12/10 — rapport de l'étape 02 : catalogue AIR et V147

[Prompt](2026-10-12_etape_02_catalogue_air_v147.md) · [Plan](../revue_code_2026-10-12_plan.md)

- **SHA revu :** master `dfbdbed` (code identique à `d7055bc`).
- **Revue :** Claude (session interactive), lecture seule, aucun correctif.

## Verdict

Aucun P0 ni P1. Le découpage V147 en trois entrées de file est cohérent : pas de double
insertion, pas de phase orpheline, pas d'état incohérent après chargement. AC04 et AC06 sont
corrects sur les points demandés. Un risque préexistant, hors du code du jour, est relevé en P2
(02.1). Deux remarques P3.

## Couverture

- `scheduler_tasks.nut` : `OpexC121CatalogCanContinue`, `OpexC78StartCatalogAirRebuild`,
  `OpexC78RequeueInitialCatalogSlice`, `OpexV147ExtendQueue`, `OpexV147CurrentPhase`,
  `OpexV147ArmPhases`, `OpexV147PhaseTask`, `OpexAI::_dispatchAirCatalogPhase`,
  `OpexC78PublishPartialAir`, `OpexC78ApplyAir`, `OpexC78ContinueCatalogAirRebuild`,
  `OpexAI::_dispatchCatalog` (en entier).
- `scheduler.nut` : `_runNextTask` (sélection et dispatch), `OpexExpSchedulerSelectTask` (début).
- `main.nut` : constructeur de `_taskQueue` (~432), `Start` (~653), boucle de reprise C121 (~776-797).
- `persist.nut` : sauvegarde et restauration de `taskDue`/`taskCursor` (~773, ~880, ~902),
  `_reconcileAfterLoad` (~1018).
- `air_planning.nut` : `OpexAir0310CountStationRoutes`, `OpexAC04ValidateHubsAtUsage`,
  `OpexAir0310RefreshHubRoutes`, `OpexAir0310RestoredHubUsable`,
  `OpexAir0310HubSnapshotPrepare`/`Store`, `OpexAirPlansStepFindSites`, `OpexAirPlansStepNewPairs`,
  `OpexAirPlansCompleteCombo`, `OpexAirPlansHubDiscoveryPhase`, `OpexAirPlansHubToSitePhase`,
  début d'`OpexAirPlans`.
- `orchestrator.nut` : `OpexAC06CaptureRevisionNumbers`, `OpexAC06SnapshotLayer`,
  `OpexAC06AcknowledgeSnapshot`, `_c76BumpLayer`, `_dispatchReactiveIntention` (régénération),
  fin de `_c76DoFullRegen`.

## Réponses aux questions du prompt

1. **File de tâches.**
   - Double insertion impossible : `OpexV147ExtendQueue` (`scheduler_tasks.nut:90`) est gardé
     par `V147_TASK_BASE >= 0` et n'est appelé que dans `Start` (`main.nut:653`).
   - Aucune phase ne peut rester sans armement. `OpexV147ArmPhases` est appelé à trois endroits :
     au démarrage du scan (`scheduler_tasks.nut:72`), après chaque dispatch de phase (`:158`), et
     par l'entrée `catalog` tant qu'un scan est en cours (`:358-363`).
   - Si l'entrée dispatchée n'est pas la phase courante, la file est réarmée et le dispatch
     sort sans travail (`:150-154`).
   - Un rafraîchissement du catalogue par l'entrée `catalog` est impossible pendant un scan : la
     branche de garde n'est pas atteinte tant que `c78AirRebuild` existe. Le cas de la
     régénération **réactive** est traité en 02.1.
2. **Publication partielle.**
   - Une même tranche ne peut pas être publiée deux fois : `lastPublishedCount` avance à chaque
     publication (`:216`), et `partialPending` est servi avant toute nouvelle tranche (`:273`).
   - Le repli `fallback` ne se déclenche que si le scan primaire n'a produit aucun plan (`:320`) :
     aucune publication partielle n'est donc perdue au changement de bande.
   - Je n'ai pas lu le prédicat d'invalidation d'`OpexAir0310PublishIncremental`
     (`projects_update.nut` ~507-523). Il reste à vérifier qu'une paire publiée puis bloquée par
     AC04 est bien retirée ; voir les limites.
3. **AC06.**
   - Les révisions restent monotones : `OpexAC06AcknowledgeSnapshot`
     (`orchestrator.nut:1212-1240`) prend le maximum entre l'instantané et l'accusé, compteur
     par compteur et mode par mode.
   - Accuser un instantané déjà remplacé est donc sans effet.
   - Un événement arrivé pendant le scan reste non accusé, et redéclenche la régénération
     suivante, ce qui est voulu.
4. **Sauvegarde.**
   - `c78AirRebuild` n'est pas persisté : un scan en cours est perdu au chargement et repart de
     zéro.
   - Les trois entrées V147 n'existent pas encore au moment de `Load`, puisqu'elles sont
     ajoutées dans `Start`. Leurs `dueCycle` sauvés ne sont donc pas restaurés, ce qui est
     cohérent : elles repartent désactivées et sont réarmées au prochain scan.
   - Un `taskCursor` sauvé sur une entrée V147 reste valide. Rechargé avec V147=0, il dépasse la
     file ; la boucle de `_runNextTask` le tolère (`scheduler.nut:270-288`).
   - Aucun état incohérent.
5. **Équivalence V147=1 / V147=0.**
   - **Hors amorçage :** les phases sont en fin de file (`scheduler_tasks.nut:93-96`). La tranche
     de scan tourne donc après `air`, `air_fleet` et `projects` du même cycle, et non plus en
     tête.
   - **Pendant l'amorçage (`_projects == null`) :** `OpexV147ArmPhases` reproduit
     `OpexC78RequeueInitialCatalogSlice`, avec échéance immédiate et curseur placé sur la phase.
   - **Boucle de reprise C121** (`main.nut:786-789`) : même travail, dispatché par la phase.
   - Aucune autre différence de décision trouvée. L'ordre change, donc ce n'est pas une
     équivalence stricte. C'est déjà couvert par la qualification de V147.
   - `C121_CATALOG_AIR_FIRST_YEAR` et le lot de villes C121 peuvent passer deux fois par cycle
     (entrée `catalog`, puis phase). C'est sans effet : le premier calcul est idempotent, le
     second est gardé par la date (`scheduler_tasks.nut:341`).

## Constats

### 02.1 — Régénération réactive complète pendant un scan C78 tranché [P2, hypothèse, préexistant]

**Mécanisme**
- `_c76BumpLayer(..., isEvent=true)` enfile une intention `regen` (`orchestrator.nut:1089-1092`).
  `_dispatchReactiveIntention` lance alors `_c76DoFullRegen` de façon synchrone dès que les villes,
  les lignes ou les moteurs AIR ont changé, car `_c80ModeRegenModes` rend `null`
  (`orchestrator.nut:677-682`, `:1380`).
- Rien ne vérifie qu'un scan `c78AirRebuild` est en cours.

**Conséquences possibles, sous `C121_CATALOG_INCREMENTAL=1` (le défaut)**
1. Une régénération complète non tranchée (rafraîchissement du catalogue, puis
   `_rebuildProjects` avec génération AIR complète) tombe au milieu d'un scan conçu pour être
   tranché.
2. L'`apply` du scan republie ensuite des plans calculés sur l'**ancien** catalogue, par-dessus
   ceux, plus frais, de la régénération réactive.
3. Si le rafraîchissement change la liste des combos, les curseurs du scan (`s.cursor.combo`, `a`,
   `b`) peuvent désigner un autre combo.

**Statut :** c'est une hypothèse. Le code le permet ; je n'ai pas vérifié en partie si les deux
se chevauchent. V151 a déjà mesuré environ deux régénérations réactives complètes par partie,
en 01/1972 et 01/1973, à environ 7 M opcodes chacune.

**À vérifier :** sous `decision_log=1`, compter les `PORTFOLIO_REFRESH`/régénérations
`reactive` émises alors qu'un `c78AirRebuild` est actif.

**Piste :** différer l'intention en posant `_portfolioInvalidated` tant qu'un scan est en cours.
C'est un changement de comportement : il faudrait passer les portes A et B.

### 02.2 — Entrée `catalog` à vide pendant un scan sous V147 [P3, démontré]

Tant qu'un scan est en cours, l'entrée `catalog` (index 0) est dispatchée à chaque cycle
uniquement pour appeler `OpexV147ArmPhases` et sortir (`scheduler_tasks.nut:358-363`). Or ce
réarmement est déjà fait à la fin de chaque dispatch de phase (`:158`). On paie donc un dispatch
vide par cycle, ce qui retarde d'un créneau les autres entrées.

**Piste :** désactiver l'entrée `catalog` pendant le scan, puis la réactiver dans
`OpexC78ApplyAir`. C'est une optimisation d'ordonnancement, pas une optimisation stricte.

### 02.3 — AC04 n'est réévalué qu'au début de chaque reprise de tranche [P3, démontré, sans effet constaté]

`OpexAC04ValidateHubsAtUsage` tourne à chaque passage dans `OpexAirPlansHubDiscoveryPhase`
(`air_planning.nut:2486`). Selon le cas, c'est après une découverte, ou après une reprise
d'instantané accompagnée de `OpexAir0310RefreshHubRoutes`.

L'instantané est copié **avant** la validation (`OpexAir0310HubSnapshotStore` puis
`:2486`) : un hub orphelin y garde `routes = 0` et il est réévalué à chaque reprise. La
classification reste donc fraîche d'une tranche à l'autre, et seul l'intérieur d'une tranche
peut être en retard.

Le nom « at usage » est un peu trompeur ; ce n'est pas un défaut.

## Tests

`PYTHONPATH=sweeps python3 -m unittest` sur 19 fichiers (`test_v147_air_catalog_tasks`,
`test_ac02`–`test_ac08`, `test_ac_catalogue_accepted`, `test_cd00`, `test_cd01_cd02`,
`test_cd03_cd05`, `test_c121_catalog_incremental`, `test_v141_catalog_incremental`,
`test_catalog_cost_probe`, `test_r4_catalog_continuation`) : **114 tests, 112 OK, 2 erreurs**.

Les deux erreurs viennent de `test_ac04_causal_existing` et ne sont pas des défauts de code :
`results/ac_fixes_worktree_20261011/results/ac04a_opcode_loop_10x4_20261011_phase_summary.json`
est absent de cet hôte. Ce sont des tests de preuves archivées, qui dépendent d'un artefact non
versionné.

## Limites et non-lus

- `OpexAir0310PublishIncremental` (`projects_update.nut` ~480-560) : prédicat d'invalidation non
  lu. La question 2 reste donc ouverte pour une paire publiée puis bloquée par AC04.
- Corps de `OpexAirPlansDiscoverHubs`, `OpexAirPlansFindSites`, `OpexAirPlansNewPairs`,
  `OpexAirPlansHubToSite`, `OpexAirPlansHubHub` : seuls les enveloppes CD01–CD05 et leurs
  curseurs ont été lus.
- `OpexAC04ExtraSiteAlreadyKnown` : seulement le début.
- `_c80DoModeRegen` et `_rebuildProjects` : non lus. Ils commandent la portée réelle de 02.1.
- Pas de test de sauvegarde et rechargement exécuté (`sweeps/save_load_roundtrip.py` demande une
  partie).
