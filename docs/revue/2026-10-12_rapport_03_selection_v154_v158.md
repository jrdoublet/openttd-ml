# Revue 12/10 — rapport de l'étape 03 : sélection, V154 et V158

[Prompt](2026-10-12_etape_03_selection_v154_v158.md) · [Plan](../revue_code_2026-10-12_plan.md)

- **SHA revus :**
  - master `069c1ce` (code identique à `d7055bc`) ;
  - branche `origin/v158-lazy-select` `3d19c55`, lue dans le worktree `wt-v158-lazy-select`.
- **Revue :** Claude (session interactive), lecture seule, aucun correctif.

## Verdict

- **V154 :** aucun P0 ni P1. L'équivalence stricte annoncée tient au défaut.
- **V158 :** aucun P0 ni P1. Aucun lecteur de décision ne lit une sélection périmée :
  - soit il est précédé de `_ensureSelection()` ;
  - soit il resélectionne lui-même, ce qui matérialise la sélection implicitement ;
  - soit il ne lit que `projects.rail`, que la resélection n'écrit pas.
- L'équivalence de V158 n'est **pas stricte**, et son rapport le dit : la caisse est lue à la
  matérialisation et non plus à la publication. C'est le seul écart de décision trouvé.
- Quatre remarques P3.

## Couverture

**master, `projects_selection.nut` :**
- `OpexProjectInsertDefensive` (1540-1690) en entier ;
- `OpexProjectSelectionScore` (1521) ;
- `OpexProjectDefensiveAirPriority` (547) ;
- `OpexProjectRefreshEarlySlot` (379) et `OpexProjectRefreshDefensiveSlot` (444) ;
- construction de l'état des créneaux précoces (168-209) ;
- `OpexProjectScore` ;
- dans `OpexProjectSelectAffordable`, les sites d'insertion (1264-1375) et les incréments de
  `SELECT_BISECT_STAMP` (951, 1079, 1306) ;
- `selection_diagnostics.nut:92-98`.

**branche V158 :**
- le diff complet `master...3d19c55 -- ai/OpexAI` ;
- `OpexAir0310PublishIncremental` (`projects_update.nut:468-712`) en entier ;
- `OpexReselectProjects`, pour les champs qu'il écrit ;
- `OpexEnsureSelection` ;
- `OpexC78PublishPartialAir` et `OpexC78ContinueCatalogAirRebuild` ;
- `_dispatchAirFleet`, la tête de `_dispatchCatalog`, `_dispatchReport` jusqu'à `_reportYear` ;
- `_dispatchReactiveIntention` jusqu'à `:795` ;
- `_schedIdlePreDispatch`, et les lectures de `_schedIdlePostDispatch` ;
- `OpexInjectFleetProjects` ;
- le graphe d'appel de chaque lecteur, par grep puis lecture.

## Réponses aux questions du prompt

### 1. V154, ordre total

La clé comparée est le triplet suivant :
- le rang (entier : rang défensif C77, plus 1000 pour une chaîne forcée V88) ;
- le score (flottant, `OpexProjectScore` rend `0.0` pour une valeur ou un coût ≤ 0, jamais NaN) ;
- le revenu (entier).

L'ordre lexicographique décroissant de ce triplet est total. Squirrel compare entiers et flottants
numériquement.

Avec `keepsPrior = clé(prior) ≥ clé(projet)`, ce prédicat est monotone sur une liste triée. La
dichotomie trouve alors la même position que la remontée historique, qui s'arrête au premier
`prior`, en partant de la fin, qui garde la priorité. En cas d'égalité complète, le nouveau projet
va après tous ses égaux, dans l'ordre d'arrivée, dans les deux chemins.

Les listes sont toujours triées :
- `affordable`, `c69Affordable` et `pairBest` ne reçoivent que cette insertion ;
- `remove` et `pop` préservent l'ordre.

Scores égaux à l'arrondi près : on compare les mêmes flottants, sans tolérance, dans les deux
chemins. Pour `null` ou un champ absent, voir 03.4.

### 2. V154, repli

- `useBisect` est faux dès que C118 est actif ou que le shadow C122 tourne avec le régime 0
  (`projects_selection.nut:1545-1546`). Le chemin historique est alors repris en entier.
- Les appels diagnostiques passent `forceHistoric=true` (`:987`, `selection_diagnostics.nut:97-98`).
- Une clé en cache ne peut pas devenir périmée pendant un appel :
  - `servedTowns` et `servedCount` sont construits avant la boucle (168-209), puis seulement lus ;
  - les fonctions de rafraîchissement des créneaux n'écrivent que les champs du projet courant,
    avant son insertion ;
  - le tampon est réincrémenté quand `fundScore` est recalculé dans le repli du plancher (`:1306`).

### 3. V158, lecteurs

La resélection écrit :
- `best` ;
- `stats.*` ;
- `capitalBudget` et `capitalRemaining` ;
- `railReadyStock` ;
- `c69Best` et `c69KDecData`.

Elle n'écrit pas `projects.rail`. La seule source de péremption est
`OpexAir0310PublishIncremental` (`projects_update.nut:696`), appelée uniquement par
`OpexC78PublishPartialAir`, qui sort du dispatch aussitôt après la publication. Les lecteurs se
rangent en quatre groupes.

**Lecteurs gardés par `_ensureSelection()` :**

| Site de garde | Lecteurs couverts |
|---|---|
| `_dispatchProjects` (`scheduler_tasks.nut:1058`) | — |
| `_tryBuildProjects` (`task_projects.nut:1400`) | tout ce qui n'est appelé que depuis la passe : `_tryBuildAirProject`, `_tryBuildRailProject`, `_c83WatchAirSlotTransitions` et C122, `_consumeResumableRailAtPassStart` et `_projectsRankOfAttemptKey`, `_recordPortfolioProjectBuilt`, `OpexPromoteLiveDefensiveAir` |
| `_dispatchReport` (`scheduler_tasks.nut:885`) | `_reportYear` et `_reportC78Candidates` |
| `_dispatchReactiveIntention` (`orchestrator.nut:763`) | lecture de `best[0]` et `OpexPromoteLiveDefensiveAir`, en `:768-772` |
| `_purgeSubsidyFromProjects` (`task_projects.nut:165`) | — |
| `_updateRailStockSelectionThreshold` (`task_rail.nut:1831`) | — |
| sonde C41 (`task_rail.nut:1327`) | — |
| sonde C39 (`events.nut:63`) | — |
| sonde V95 (`ledgers.nut:272`) | — |

**Lecteurs qui resélectionnent eux-mêmes :** la resélection remet le marqueur à faux.

| Fonction | Site |
|---|---|
| `_dispatchAirFleet` | via `OpexInjectFleetProjects` (`scheduler_tasks.nut:1040`), quand le plan de flotte n'est pas vide |
| `_c77InjectSubsidy` | `orchestrator.nut:927` |
| `_c77RemoveSubsidy` | `event_handlers.nut:361` |
| `_c76PurgeInvalidCandidates` | `orchestrator.nut:1365` |
| `_c76RotateFreight` | — |
| `_c80DoModeRegen` | — |
| `OpexWorkerRegenCandidatesStep` | — |
| `OpexPromoteLiveDefensiveAirStock` | — |
| `_dispatchCatalog`, branche de garde | `:434`, `:534` |
| application finale d'un scan | `_rebuildProjects`, avec une table neuve sans marqueur |

**Lecteurs de `projects.rail` seul, non périmé :**
- l'affectation de `_ranked` dans `OpexC78PublishPartialAir` (`scheduler_tasks.nut:213`) ;
- `_tryStartRailStockWorker`, qui lit `projects.rail.best`, le plan rail et non le portefeuille.

**Branche de garde de `_dispatchCatalog` :** elle lit `capitalBudget` et
`stats.nextProjectCapital` (`:385-387`). Elle n'est atteinte que hors scan. Or seul
`OpexC78ApplyAir` efface `c78AirRebuild` (`:251`), après un `_rebuildProjects` qui remplace la
table. Ces champs sont donc frais.

Seul lecteur non couvert : la sonde V95 hors tâche `projects` (03.1).

**Écart de décision.** La caisse est lue à la matérialisation (`projects_selection.nut:1952`) et
non plus à la publication (`projects_update.nut:703` au défaut 0). Il n'y a pas d'autre écart :
- `OpexProjectSelectAffordable` n'a pas d'hystérésis : ni état global de décision, ni lecture de
  l'ancien `best` ;
- les champs `fundScore` sont recalculés à chaque appel.

C'est l'écart que décrit le §5 du rapport V158. Le 20×10 `non_erosion` en cours sur le PC est
donc la bonne porte. Le classement du rapport V158 comme optimisation d'opcodes est défendable,
mais ce n'est pas une équivalence stricte.

### 4. V158, persistance et événements

`selectionStale` vit dans `_projects`, qui n'est pas sauvé : `Load` et `_reconcileAfterLoad`
remettent `_projects` à null (`persist.nut:890`, `:1023`). La table est reconstruite en entier
au premier catalogue, sans marqueur.

Pour les événements :
- **subventions :** `_c77RemoveSubsidy` resélectionne et `_purgeSubsidyFromProjects` est gardé ;
- **intentions réactives :** gardées en `:763`. Les branches qui précèdent régénèrent, donc
  resélectionnent ;
- **`_markDirty` :** ne lit la sélection que sous la sonde C39, qui est gardée.

Aucun événement ne lit `best` sans matérialiser.

### 5. V158 × V154

Oui. `OpexEnsureSelection` appelle `OpexReselectProjects`, puis `OpexProjectSelectAffordable`,
qui incrémente le tampon (`:1079`). Les conditions de `useBisect` sont identiques.

Dans la fenêtre paresseuse, `best` peut contenir des objets que `OpexV141RefreshPublishedAir` a
modifiés sur place, avec des clés `_bs*` anciennes. Le nouveau tampon les invalide dès la
matérialisation. Il n'y a pas d'interaction.

### 6. Libellé d'année

Confirmé : 03.3.

## Constats

### 03.1 — La sonde V95 lit une sélection périmée après les tâches catalogue et `air_fleet` [P3, démontré, sonde seule]

**Mécanisme.**
- `_schedIdlePostDispatch` lit `best.len()` et `stats.emptyCause` après **toute** tâche, pour
  `P2_RESOLVE` (`ledgers.nut:1031-1050`).
- Il est gardé par `V95_SCHED_IDLE_LEDGER`, c'est-à-dire `probe_scheduler`.
- La garde V158 de `_schedIdlePreDispatch` (`:271-273`) ne vaut que pour `projects` et `report`.

**Scénario.** Sous V158=1 :
1. une phase de catalogue publie avec la sélection différée ;
2. `P2_RESOLVE` voit l'ancien `best`, éventuellement vide ;
3. la résolution d'un chantier en attente est attribuée à une tâche ultérieure (`air_fleet` ou
   `targeted_air`) au lieu de `catalog_other`.

**Effet.** Mesure seule. Les deux bras d'un A/B V158 ne sont pas comparables sur cette
ventilation. Le tableau §3 du rapport V158 classe ce lecteur « Couvert », ce qui n'est vrai que
pour la tâche `projects`.

### 03.2 — `air_publish_lazy_select` lu sans garde `>= 0` [P3, démontré, inoffensif]

`settings.nut:173` : `AIR_PUBLISH_LAZY_SELECT = AIController.GetSetting("air_publish_lazy_select");`,
puis le test `!= 0` (`projects_update.nut:696`).

Un nom inconnu rendrait -1, ce qui activerait la paresse. Ce cas n'arrive pas tant que le réglage
est déclaré dans `info.nut`, mais il s'écarte de la convention des réglages voisins
(`if (x >= 0) ...`).

### 03.3 — `AIR_LAZY_SELECT year=Y` compte l'année Y−1 [P3, démontré]

**Mécanisme.**
- `_dispatchReport` reçoit l'année courante (`scheduler.nut:263`).
- Il ne tourne qu'au premier cycle d'une nouvelle année (`scheduler_tasks.nut:883-884`).
- `_logAirLazySelect` journalise alors les compteurs accumulés depuis le rapport précédent, puis
  les remet à zéro.

**Effet.**
- La ligne `year=1971` décrit 1970.
- La ligne `year=1970`, émise au démarrage, est vide.
- C'est la même convention que la ligne `REPORT`. À l'analyse, décaler d'un an.

### 03.4 — V154 : champs `_bs*` laissés sur les projets ; revenu absent lu comme 0 [P3, démontré]

**Champs `_bs*`.** La dichotomie pose six champs par `rawset` sur chaque projet comparé
(`projects_selection.nut:1556-1561`, `:1582-1587`). Ils restent sur les tables de
`candidateGroups` et de `best`, sans jamais être retirés.

Aucun lecteur de décision n'énumère les champs d'un projet : `OpexV141DecisionFieldDiff` compare
une liste fixe. C'est donc seulement de la mémoire, et du bruit si un projet est un jour vidé dans
un journal.

**Revenu absent.** Le chemin dichotomique prend `revenueAnnual` absent pour 0 (`:1554`, `:1581`).
Le chemin historique lit `prior.revenueAnnual` directement (`:1682`), et lèverait une erreur.

Les deux chemins ne divergent que dans ce cas d'erreur, qui n'est pas observé : tous les
constructeurs de projet posent `revenueAnnual`.

## Tests

- **Branche `3d19c55`** : `PYTHONPATH=…:sweeps python3 -m unittest sweeps/test_v158_lazy_select.py
  sweeps/test_v154_bisect_equivalence.py` donne **23 tests, OK**.
- **master `069c1ce`** : `sweeps/test_v154_bisect_equivalence.py` donne **12 tests, OK**.

Ces tests sont contractuels et en simulation Python. Ils ne prouvent pas que le Squirrel compile.

## Limites et non-lus

- Le corps complet de `_tryBuildProjects` (~900 lignes) n'a pas été relu. La couverture de ses
  lecteurs repose sur la garde en `:1400` et sur le graphe d'appel : tous ses lecteurs ne sont
  appelés que depuis la passe.
- `OpexIncrementalUpdateProjects` : seule la remise à zéro du marqueur (`:283`) a été lue.
- Les écritures de `OpexRegenerateModeProjects` et `OpexApplyGeneratedModeProjects` ont été lues
  par grep seulement. Leur resélection est en `projects_generation.nut:174`.
- 03.1 n'a pas été vérifié en partie : aucune partie n'a été lancée.
- Le rythme réel des matérialisations n'a pas été mesuré : il faudrait compter les publications
  différées que résorbe `air_fleet` avant `projects`.
