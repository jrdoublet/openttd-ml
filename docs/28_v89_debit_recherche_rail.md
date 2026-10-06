# V89 — Débit de recherche de chemin ferroviaire opportuniste

**Statut au 30 septembre : défaut 1 par décision utilisateur du 26, comme dépendance
de V88, malgré un 20×10 sans gain direct démontré.** Le protocole initial ci-dessous
est historique ; il n'ordonne pas un nouveau banc. [Décision et limites](journaux/synthese_decisions_2026-09-30.md).

Date : **2026-09-24**. Protocole requalifié le **2026-09-25** après adoption de V91=120.
Objectif : réduire le **délai de mise en service** des lignes ferroviaires sans toucher au budget d'itérations ni à la qualité des tracés.

---

## 1. Constat mesuré (2026-09-24)

Relevés en solo (graines 42 et 100, 8 ans, sondes passives `probe_events`) :
- Une recherche rail reprenable (`rail_search_resumable=1`, actif par défaut via `policy_rail`) n'avance qu'à un rythme d'environ **900 itérations par AN** de jeu (avec une tranche `RAIL_SEARCH_SLICE = 50`, `ai/OpexAI/builder_rail.nut:39`) : bilans annuels `spent = 800 → 1700 → 3050 → 4050 → 4950` pour un budget alloué de 10 000 itérations.
- Des recherches ordinaires de 1971–1972 avancent au même rythme lent : ~2 600 itérations en un an complet.
- Un tronçon a mis **3 ans de jeu** à trouver son tracé (3 126 itérations réelles).
- L'activation du travailleur orchestrateur `c80_worker_rail=1` n'a pas changé ce rythme.
- Pendant toute cette durée (jusqu'à 3 ans), l'unique emplacement `this._railSearch` est occupé (`phase == "search"`). En conséquence, **tout autre candidat rail du portefeuille est écarté** (`search_in_progress`, 98 à 150 rejets par partie en 5 ans dans `task_rail.nut:150, 262` et `task_projects.nut:416, 440, 455`).

---

## 2. Hypothèse vérifiée par la lecture du code

L'hypothèse est **entièrement confirmée** par l'analyse du code source :

1. **Une seule tranche par tour de file** (`scheduler.nut:162-164`, `orchestrator.nut:214`) :
   Dans le chemin normal, `_advanceRailSearchSliceWithLedgers()` n'est appelé qu'une seule fois au début de `_runNextTask()`. Sous `c80_worker_rail=1`, `OpexWorkerRailSearchStep` n'exécute également qu'un seul appel de tranche par tick de travailleur (`orchestrator.nut:214`).
2. **Rareté des appels due aux tâches de fond monolithiques** :
   Un tour complet de la file de tâches `_taskQueue` prend entre **45 et 135 jours de jeu** (médiane mesurée : 86 jours, cf. `docs/journaux/23_nuit_2026-09-23.md` §7 et `CLAUDE.md` §183). Sur une année de 365 jours, le scheduler n'accomplit donc que ~4 tours de file, soit seulement 50 à 60 appels de `_runNextTask()`. À raison de 50 itérations par tranche, le débit maximal théorique sans tâche sautée est de `60 × 50 = 3 000` itérations/an, et typiquement ~900 à 2 600 itérations/an observées.
3. **Absence d'avancement pendant les tâches longues** :
   Les tâches longues (`catalog`, `projects`, `town_growth`) consomment entre **1 et 13 millions d'opcodes chacune** (`docs/journaux/23_nuit_2026-09-23.md` §7 et §9). Pendant qu'une telle tâche tourne, NoAI suspend automatiquement le thread du script au bout du quota d'opcodes du tick (10 000 opcodes) et reprend au tick suivant à l'intérieur de la même fonction Squirrel, sans jamais repasser par la tête de `_runNextTask` ni par la boucle principale `while (true)`. Durant les 100 à 1 300 ticks consécutifs que peut durer une régénération de catalogue ou une sélection de portefeuille, l'A* rail n'avance pas d'une seule itération.
4. **Gaspillage du budget dans les ticks rapides** :
   À l'inverse, lorsqu'une tâche courte (`scrap`, `c41_rail_signals`, `repay`, `report`) s'exécute, elle ne consomme que 200 à 500 opcodes. Les ~9 500 opcodes restants du tick sont purement perdus car la boucle principale appelle immédiatement `AIController.Sleep(1)` (`main.nut:569, 573`).

---

## 3. Historique réfuté (ne pas reproduire)

Conformément à `docs/archives/taches_archive_2026-09-09.md` (lignes 615–640 et 970–982) :
- ⛔ **Relever le budget d'itérations** : réfuté. Augmenter le plafond n'augmente pas la vitesse à laquelle les itérations sont parcourues dans le temps de jeu.
- ⛔ **Échéance globale posée à l'entrée** : `rail_search_resumable` avait été rejeté historiquement (−23,1 % puis −13,3 % de valeur, −27,5 % de gares) parce qu'une échéance globale à l'entrée amputait la recherche au lieu de la redistribuer dans le temps. La perte économique venait directement de la non-mise en service de lignes abandonnées par timeout global. **Règle absolue : chaque tranche doit porter sa propre échéance locale** (`RAIL_MICRO_DEADLINE`), jamais une échéance globale.
- ⛔ **`rail_segmented_search` (A5, défaut 1)** : 4× moins cher en opcodes bruts sur les cas extrêmes, mais valeur économique nulle face à AAAHogEx.

**Principe clé de V89** : Le levier est le **DÉBIT d'itérations par jour de jeu**, pas le budget d'itérations ni le coût total du pathfinder.

---

## 4. Conception retenue

L'implémentation est placée derrière le réglage `v89_rail_search_throughput`. Le réglage est **défaut 1 depuis le 2026-09-26**, par décision utilisateur, car V88 dépend de ce débit de recherche rail.

### 4.1 Mécanisme d'avancement opportuniste (`_advanceRailSearchThroughput`)

Une méthode dédiée `OpexAI::_advanceRailSearchThroughput(maxSlices = -1)` (`ai/OpexAI/scheduler.nut`) avance des tranches supplémentaires tant que :
1. `V89_RAIL_SEARCH_THROUGHPUT` est actif ;
2. Une recherche rail est active en phase `"search"` (`this._railSearch != null && this._railSearch.phase == "search"`) ;
3. Le budget d'opcodes restant dans le tick courant dépasse le coût estimé d'une tranche : `AIController.GetOpsTillSuspend() >= this._v89EstimatedSliceOps` (seuil auto-calibré sur les mesures réelles de `sliceOps`, plancher de sécurité à 1 500 opcodes).

### 4.2 Préservation stricte de l'échéance par tranche

Chaque tranche additionnelle est exécutée via `_advanceRailSearchSliceWithLedgers()`, qui appelle `_continueRailSearch()` (`ai/OpexAI/task_rail.nut`).
À chaque tranche, `RAIL_MICRO_DEADLINE` (C20) pose une **échéance locale fraîche** :
```squirrel
deadlineTick = AIController.GetTick() + RAIL_SEARCH_SLICE / 3 + BUILD_TICK_MARGIN;
```
Aucune échéance globale n'est imposée sur l'enchaînement des tranches. Si le temps ou le budget d'une tranche est dépassé, l'A* s'arrête selon les règles normales (`stop = "CONT"` pour continuer au prochain appel, ou `"OK"`/`"ABND"`/`"DEAD"`).

### 4.3 Points d'injection du débit

Pour maximiser le débit sans changer l'ordonnancement des tâches :
1. **En tête de `_runNextTask`** (`scheduler.nut:162-164`) : après la 1ère tranche historique, tranches additionnelles tant que le tick a du budget.
2. **Dans le travailleur C80** (`orchestrator.nut:214`) : `OpexWorkerRailSearchStep` pompe les tranches supplémentaires si du budget est disponible.
3. **Dans la boucle principale de `Start()`** (`main.nut:578, 582`) : avant l'appel à `AIController.Sleep(1)`, le reliquat d'opcodes inutilisé par la tâche précédente (dormant) est consommé pour faire avancer l'A* au lieu d'être gaspillé.
4. **Entre les étapes des tâches longues** :
   - `_dispatchCatalog` (`scheduler_tasks.nut:230, 265, 292, 301`) : après `refresh` et après `rebuildProjects`.
   - `_tryBuildProjects` (`task_projects.nut:898, 900`) : après chaque projet examiné dans le portefeuille.
   - `_tryTownGrowth` (`task_town.nut:285`) : entre chaque ville examinée.

### 4.4 Invariants et contrats préservés

- **Garde à 0** : Si `v89_rail_search_throughput = 0`, aucun appel supplémentaire n'est effectué. Le comportement est bit-identique à l'actuel.
- **Budget d'itérations inchangé** : `plan.iterationBudget` et `state.spent` restent calculés exactement selon les règles existantes (`OpexIterationBudget`, `OpexDynamicHardCap`).
- **Modèle de vitesse C41** : `OpexRailEffectiveSpeed` n'est pas modifié.
- **Ordre des tâches et portefeuille** : La recherche rail ne bascule en phase `"build"` que lorsque le tracé est entièrement trouvé (`slice.done == true`). La construction physique n'a lieu que lors de la consommation par `_consumeRailSearch` lors de la passe `projects`, respectant l'ordre du portefeuille et les réserves de trésorerie.
- **Persistance et rechargement (Save/Load)** : `_railSearch` contient un objet C++ non sérialisable. Au rechargement, `persist.nut:649-675` effectue un abandon propre de la recherche en cours et force une replanification complète du catalogue (`this._portfolioInvalidated = true`). V89 ne modifie pas la structure de `_railSearch` et préserve intégralement ce contrat.

---

## 5. Allocation des opcodes

Les opcodes sont une ressource de flux allouée à chaque tick (10 000 opcodes/tick).
- **Origine du budget des tranches V89** :
  1. Le **slack dormant** des ticks rapides (tâches courtes, attente d'ordres) qui était jusqu'ici perdu par `Sleep(1)`. Ce prélèvement est à coût d'opportunité nul pour les autres tâches.
  2. Les **intervalles entre sous-étapes** des tâches de fond (catalog, projects, town growth).
- **Impact sur les autres tâches** : Une tâche longue prendra potentiellement quelques ticks calendaires supplémentaires pour s'achever (ex. 130 ticks au lieu de 100 pour une étape de régénération), mais en contrepartie le tracé ferroviaire avance en continu au lieu d'être paralysé pendant des mois.

---

## 6. Instrumentation passive (`probe_events`)

Toutes les traces réutilisent `OpexC56TaskLog` (actif sous `probe_events=1`, coût nul au défaut) et sont compatibles avec `sweeps/analyse_c76_exposure.py` et `sweeps/diag_c69_bottleneck_probe.py --extra-tags C56_TASK` :

1. `RAIL_SLICE` : émis à chaque tranche d'A*.
   `OPEX AAAA-M-J C56_TASK RAIL_SLICE name=primary cycle=... tick=... opsclk=... slice_iters=50 spent=... budget=... done=... stop=...`
2. `RAIL_SEARCH_START` : émis au lancement d'une recherche primaire.
   `OPEX AAAA-M-J C56_TASK RAIL_SEARCH_START name=primary cycle=... tick=... opsclk=... src=... dst=... budget=... hard_cap=...`
3. `RAIL_SEARCH_END` : émis à la fin (ou abandon) de la recherche primaire.
   `OPEX AAAA-M-J C56_TASK RAIL_SEARCH_END name=primary cycle=... tick=... opsclk=... src=... dst=... outcome=... iters=... budget=... days=... ticks=...`
4. `RAIL_COMMISSION` : émis à la mise en service réussie de la ligne construite.
   `OPEX AAAA-M-J C56_TASK RAIL_COMMISSION name=primary cycle=... tick=... opsclk=... line=... src=... dst=... iters=... delay_days=... search_to_service_days=...`
   où `delay_days` mesure le délai complet entre la sélection du candidat et la mise en service effective.
5. `RAIL_ANNUAL` : bilan annuel émis lors du rapport annuel (`_dispatchReport`).
   `OPEX AAAA-M-J C56_TASK RAIL_ANNUAL name=rail cycle=... tick=... opsclk=... year=... year_iters=... year_slices=... search_days=... active_search=...`

---

## 7. Protocole de validation courant

Les mesures historiques de §1 précèdent l'adoption de **V91=120**, qui réduit désormais le
nombre d'itérations de recherche d'environ ×5. Il faut donc d'abord vérifier que le goulot
calendaire existe encore sur le défaut courant avant de mesurer causalement V89.

### Étape 1 : diagnostic d'exposition solo 3 graines × 6 ans

- **Graines** : 42, 100, 999 ; **6 ans**.
- **Bras unique** : défaut courant (`OpexAI`, donc V90 actif, V91=120 et
  `v89_rail_search_throughput=0`) avec `probe_portfolio=1,probe_events=1`.
- Ce diagnostic ne mesure **pas** encore l'effet économique de V89 : il répond uniquement à la
  question « V91 a-t-il déjà absorbé le goulot de débit rail ? ».
- **Indicateurs mesurés** :
  - Débit A* : itérations par an (`year_iters`), nombre de tranches (`year_slices`), jours avec recherche active (`search_days`).
  - Délais : délai médian sélection → mise en service (`delay_days`) et fin recherche → mise en service (`search_to_service_days`).
  - Volume ferroviaire : nombre de lignes rail construites, trains pilotés.
  - Part d'opcodes : répartition du temps script par tâche (`self_ops` via `sweeps/analyse_c76_exposure.py`).

**Résultat du 2026-09-25 — exposition confirmée.** Campagne
`results/v89_exposure_v91_current_3x6_20260925.json` + traces `.jsonl`, graines
42/100/999, 3/3 parties saines. Les 6 recherches terminées durent 20, 48, 68,
311, 414 et 735 jours, soit une médiane de **189,5 jours**. Quatre lignes sont
mises en service dans l'horizon, avec des délais sélection→service de 102, 108,
342 et 822 jours (médiane **225 jours**) ; le délai fin recherche→service vaut
31, 40, 82 et 87 jours (médiane **61 jours**). Les bilans annuels avec recherche
active rapportent 294, 350, 739, 800 et 900 itérations/an (médiane **739**) et
132 à 340 jours/an de recherche active. V91=120 a donc réduit le nombre total
d'itérations par recherche, mais **n'a pas supprimé le goulot calendaire**.

Si les recherches restent étalées sur des mois/années ou continuent de bloquer sensiblement le
slot `_railSearch`, passer à l'étape 2. Sinon, considérer que V91 a absorbé l'exposition et ne pas
dépenser un 20×10 sur V89.

### Étape 2 : duel causal 5 graines × 6 ans, conditionnel

- **Seulement si l'étape 1 confirme l'exposition**.
- Référence : défaut courant ; variante : `OpexAI[v89_rail_search_throughput=1]`.
- Graines 42, 100, 999, 1234, 5678 ; métrique `profit_year`, effet utile +50 k£/an,
  garde de valeur −5 %.
- Mesurer en parallèle les mêmes délais et volumes ferroviaires pour vérifier que le mécanisme
  agit bien par accélération de mise en service plutôt que par une dérive économique indirecte.

**Résultat du 2026-09-25 — non favorable.** Campagne
`results/v89_rail_throughput_vs_default_5x6_20260925.json`, 5/5 paires complètes.
Variante − référence : `profit_year` moyen **−62,0 k£/an**, médiane **−117,7 k£**,
**2 victoires / 3 défaites**, test des signes p=1,0, IC95 **[−177,5 ; +53,5] k£/an**.
La valeur d'entreprise moyenne est **+1,48 %**. Le mécanisme ne franchit donc pas le seuil
de qualification économique prévu pour passer au 20×10. Le 20×10 V89 ne doit pas être lancé
tel quel ; toute reprise doit d'abord modifier causalement l'allocation du slack/opcodes.

### Étape 3 : qualification 20 graines × 10 ans, seulement après un 5×6 favorable

- **Harnais** : `sweeps/run_c66_reference.py`
  ```bash
  python3 sweeps/run_c66_reference.py \
    --campaign v89_rail_throughput_20x10 \
    --years 10 \
    --reference "OpexAI" \
    --variant "OpexAI[v89_rail_search_throughput=1]" \
    --variant-policy-id "v89_rail_search_throughput" \
    --primary-metric "profit_year" \
    --min-useful-primary-delta 50000 \
    --value-guard-max-loss-pct 5.0 \
    --max-workers 10 \
    --cpus 10
  ```
- **Critères d'adoption** :
  - Métrique primaire : `profit_year` (profit annuel moyen).
  - Effet minimal utile : **+50 k£/an**.
  - Garde-fou sur la valeur : perte maximale de valeur d'entreprise ≤ **−5 %**.
  - Verdict statistique : test bilatéral exact des signes p < 0,05 (au moins 15 victoires sur 20 graines), ou borne inférieure de l'IC95 de Student > 0.
