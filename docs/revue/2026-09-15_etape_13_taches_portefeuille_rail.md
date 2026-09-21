# Étape 13 — Tâches portefeuille et rail

> **Statut au 2026-09-20 : REVUE HISTORIQUE.** Les constats de cette étape ont été réconciliés
> dans `docs/revue_code_2026-09-15_correctifs.md` et `docs/taches.md`. Ne pas interpréter les
> formulations « à faire » de cette fiche comme des tâches encore ouvertes sans vérifier la
> matrice et l'état courant de `docs/taches.md`.

- **SHA revu** : `3642623` (HEAD au moment de la revue ; `7304613` au début de la lecture, seuls les fichiers de revue 14/15 ont bougé entre-temps, ancres inchangées)
- **Modèle / effort prévus** : Opus 5 / high
- **Périmètre** : `ai/OpexAI/task_projects.nut`, `task_rail.nut` — 2 103 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Cœur d'exécution `_tryBuildProjects`, lot dynamique, entonnoir C63. Code directement sous la
priorité P1 (C63/C58). Bloc de ≈20 l. dupliqué avec `scheduler_tasks.nut:286-308`.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 13.1 — Un échec de construction rail n'est JAMAIS enregistré comme tel sur le chemin livré        [gravité : P1]
`task_rail.nut:287-292` · `task_projects.nut:519-521` — Le seul `passDiscards.append` d'échec de
chantier rail est gardé par `C63_INVEST_PROBE` **seul** (défaut 0), là où route
(`task_road.nut:281`), air (`task_air.nut:443`) et eau (`task_water.nut:44`) l'appendent sous
`C49_SCARCITY_LEDGER || C63_INVEST_PROBE || MONTHLY_FUNNEL`. Pire : ce site n'est atteint que par
le chemin **bloquant**. Avec `rail_search_resumable = 1` (défaut), l'échec passe par
`_consumeRailSearch` → `_recordRailAttempt`, et `task_projects.nut:519-521` ne fait qu'appeler
`_dynamicBatchRejected()` (inerte par défaut) : **aucun** enregistrement, sous aucun drapeau.
Conséquence observable : `funnelAttempted` a été incrémenté (`task_projects.nut:435`),
`passDiscards` reste vide, donc `_recordMonthlyFunnelPass` publie `attempted=1 funded=1 built=0`
sans le moindre champ `r_*`, et `OpexC63NotePass` trouve `reason = ""` →
`OpexC63ClassifyOpportunity` (`probes.nut:289`) rend **`invalid`**. Un échec de chantier rail est
donc compté comme « le meilleur projet était structurellement impossible ». Au passage suivant
dans la même passe (le scan reprend puisque `builtCount == 0`, `task_projects.nut:525`), le même
candidat relance un A* complet et rend `pending` → la passe est reclassée `waiting_compute`
(`task_projects.nut:741-746`). Aucune des deux étiquettes ne dit « la construction a échoué », et
un A* entier est rebrûlé sur une paire qui vient d'échouer.

### 13.2 — L'entonnoir mensuel additionne des stocks et des flux        [gravité : P2]
`task_projects.nut:29-40` et `109-111` — `considered` (`stats.budgetConsidered`) et `accepted`
(`this._projects.best.len()`) sont des **tailles de portefeuille à l'instant t**, invariantes tant
qu'aucune régénération n'a lieu ; `attempted` et `built` sont des **compteurs de la passe**. Les
cinq champs sont émis à chaque dispatch de `projects` (plusieurs par jour de jeu) sur la même
ligne, comme si c'étaient cinq étages d'un même entonnoir. Le consommateur les somme tous par mois
calendaire (`sweeps/diag_1v1_shared_monthly.py:363-368`, hors périmètre) : le « considéré » et
l'« accepté » mensuels valent donc la taille du vivier × le nombre de passes, tandis que
« tenté »/« bâti » sont justes. Les deux premiers étages de l'entonnoir C63/C58 sont inexploitables
en valeur absolue. Accessoirement `funded = attempted - cashRejects` (`107-108`) est **inférieur**
à `attempted` alors qu'il est imprimé avant lui : l'entonnoir n'est pas monotone dans l'ordre où il
se lit.

### 13.3 — `knapsackExact` : le panneau `IG|` publie « optimum prouvé » en dur        [gravité : P2]
`task_projects.nut:890-893` et `scheduler_tasks.nut:294-297` — Le champ émis est
`(stats.knapsackExact ? 0 : 1)`. `knapsackExact` n'est **jamais** mis à `false` : les cinq sites
d'écriture (`projects.nut:822, 1354, 1527, 1933, 2088`) l'initialisent tous à `true` et aucun ne le
retouche. Le cinquième champ d'`IG|` est donc la constante `0` sur toute la partie. Le commentaire
de 7 lignes qui le précède — identique au caractère près dans les deux fichiers — affirme qu'il
sert à « distinguer *le solveur a prouvé l'optimum* de *il a épuisé son budget de nœuds* » : il
prétend mesurer exactement ce qu'il ne mesure pas. `knapsackNodes` (même famille, mêmes cinq sites,
toujours 0) n'est lu nulle part et n'est pas dans le panneau. Confirme le constat de l'étape 6 et
en localise les deux sites d'émission. Le sixième champ, `this._budget.nested`, est lui réellement
alimenté (`budget.nut:51`) : la correction ne doit pas emporter le panneau entier.

### 13.4 — `decision_log = 1` vide le journal que C63, C49 et l'entonnoir vont lire        [gravité : P2]
`task_rail.nut:257-264` et `279-286` — Les `passDiscards` sont **appendés** sous
`DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL` (p. ex. `task_rail.nut:150, 155, 166, 228`)
mais **remis à `[]`** sous `if (DECISION_LOG)` seul, au moment où le candidat rail est élu. La liste
est rendue à l'appelant (`return { … discards = passDiscards }`), qui la réassigne
(`task_projects.nut:730`). Conséquence : allumer `decision_log` en même temps que `c63_invest_probe`
ou `monthly_funnel` efface tous les refus accumulés avant le candidat rail élu — `cashRejects` chute,
`funded` est surévalué, les `r_*` disparaissent, et `OpexC63NotePass` ne retrouve plus le motif du
rang restant (`probes.nut:405-413`). Une sonde change la valeur d'une autre.

### 13.5 — `MONTHLY_FUNNEL_DETAIL` n'a aucun émetteur        [gravité : P2]
`task_projects.nut:109-111` — `_recordMonthlyFunnelPass` n'émet qu'une ligne globale. Aucun
fichier de `ai/OpexAI/` ne contient la chaîne `MONTHLY_FUNNEL_DETAIL`, alors que
`sweeps/diag_1v1_shared_monthly.py:385-399` a un parseur complet dédié à la ventilation **par
mode** de l'entonnoir. Conséquence observable : la ventilation par mode rend un résultat vide, qui
se lit comme « zéro partout » et non comme « non mesuré » — sur le chantier P1 qui a précisément
besoin de savoir quel mode se fait refuser.

### 13.6 — Le panneau `EU|` est posé à chaque dispatch, toujours à zéro avec le défaut livré        [gravité : P2]
`task_rail.nut:374-376` — `OpexSign(... "EU|" …)` est inconditionnel dans `_expandRailLines`. Or
`rail_expand` vaut 0 par défaut et la boucle de sélection sort immédiatement (`task_rail.nut:319`,
`break`) : les cinq compteurs valent 0 à chaque fois. La tâche `expand` reste dispatchée puisque
`rail_refleet = 1` (`scheduler_tasks.nut:664`), avec `dueCycle` réarmé à chaque cycle
(`scheduler.nut:204`) et jusqu'à 8 tâches drainées par tick (`main.nut:82, 527`) : c'est un
`AISign.BuildSign` par cycle de file pendant toute la partie. Deux conséquences : le pool de
panneaux — ressource finie partagée par **toute** la mesure, `debug_signs = 1` par défaut — est
consommé pour rien, et l'entonnoir d'expansion lu par `sweeps/opex_full_campaign.py:1162` est noyé
sous des milliers de lignes nulles. Les autres panneaux annuels (`IG|`, `IB|`, `BS|`) sont eux posés
au plus une fois par régénération.

### 13.7 — L'échec de croissance de flotte n'est visible que sous C63        [gravité : P3]
`task_projects.nut:187-191` — Le refus `insufficient_cash` du même helper est gardé par
`DECISION_LOG || C63_INVEST_PROBE || MONTHLY_FUNNEL` (`169`), mais `fleet_grow_failed` est appendé
à l'intérieur du `if (C63_INVEST_PROBE)` qui entoure `OpexC63RecordSpend`. Avec
`monthly_funnel = 1` seul, l'entonnoir voit une tentative de plus sans jamais le motif : `built`
baisse sans qu'aucun `r_*` n'augmente.

### 13.8 — Le duplicata `IG|`/`FN|`/`IB|` a divergé : `IB` porte un champ de plus ici        [gravité : P3]
`task_projects.nut:883-906` vs `scheduler_tasks.nut:287-307` — Comparaison ligne à ligne : les
panneaux `IG|` et `FN|` et leurs deux commentaires sont **identiques au caractère près** (seule
l'indentation diffère, +2 espaces). `IB|` a divergé : ici il porte un quatrième champ
`"|B" + batchBuilt` et son commentaire de justification (`902-904`), absents du côté scheduler. Le
lecteur tolère les deux formes (`sweeps/opex_full_campaign.py:56`, groupe optionnel `(?:\|B(\d+))?`)
et rattache l'`IB` à l'`IG` du même bloc, donc la mesure reste juste ; mais la divergence est réelle
et non signalée des deux côtés. À noter pour la correction : le budget de 30 caractères annoncé au
commentaire suppose `batchBuilt` à un chiffre — sous `portfolio_dynamic_batch` rien ne borne le
nombre de succès d'une passe (le seul frein est le plancher d'opcodes et
`DYNAMIC_BATCH_REJECT_LIMIT`), donc deux chiffres atteignent la limite annoncée de 31.

### 13.9 — `_refreshDynamicBatch` : paramètre inutilisé et « budget avant » trompeur        [gravité : P3]
`task_projects.nut:216-231` — `year` n'est utilisé nulle part dans le corps (contrairement à
`_stopDynamicBatch`, qui s'en sert l. 279). Et `before` lit
`this._projects.capitalBudget`, c'est-à-dire le budget de la **dernière réélection**, pas le budget
d'avant le chantier qui vient d'aboutir : la ligne `DYNAMIC_BATCH action=continue` publie un
`budget_before` qui, au deuxième succès d'un lot, est déjà le `budget_after` du premier. Journal
seul, chemin non livré.

### 13.10 — `OpexC41RepairJunction` : le code de retour `0` couvre deux échecs différents        [gravité : P3]
`task_rail.nut:98-103` vs `128-129` — Le bloc de documentation déclare « 0 = AITestMode refuse la
pose ». Le second `return 0` (l. 129) est renvoyé quand le `AITestMode` a **réussi** et que la
commande réelle a échoué — un cas nettement plus intéressant, que la table de codes ne permet pas
de distinguer du refus en mode test.

### 13.11 — Le garde admet que `doubleTrack` puisse manquer, l'affectation exige qu'il existe        [gravité : P3]
`task_rail.nut:426` puis `455-461` ; même motif en `1092-1099` — Le test d'entrée est
`(!("doubleTrack" in line) || line.doubleTrack == 0)`, qui accepte explicitement une ligne sans la
clé ; le succès écrit ensuite `line.doubleTrack = 1`, `line.depot2 = …`, `line.stationA2 = …` avec
`=`. En Squirrel, `=` sur une clé absente lève, alors que le fichier utilise correctement `<-`
ailleurs pour ce motif (`task_rail.nut:268-270, 849-850, 1102`). Non atteignable aujourd'hui — toute
ligne rail est créée avec les six clés (`task_rail.nut:1008-1013`) et les autres modes sont filtrés
par `mode != "rail"` — mais la tolérance affichée par le garde est illusoire, et `save_full_state`
vaut 1 par défaut : une sauvegarde antérieure à l'ajout de ces clés réactive le cas.

### 13.12 — Phase `resume` de l'expansion : seule phase sans issue de secours        [gravité : P3]
`task_rail.nut:541-549` — Toutes les autres phases de `_continueRailExpansion` ont une sortie bornée
(`waitDays` l. 555, `RAIL_EXPAND_TIMEOUT_DAYS` l. 601, `dispatchAttempts >= 3` l. 586) qui pose un
panneau `EX|` et libère `this._railExpansion`. La phase `resume` réessaie `StartStopVehicle`
indéfiniment : tant qu'elle échoue, ni panneau ni libération, et `_expandRailLines` sort d'entrée
(l. 306) — donc plus aucun second train ni doublement de voie de toute la partie, sans trace.

**État courant vérifié le 2026-09-16.** Ne pas rouvrir 13.11/13.12 :

- 13.11 est déjà corrigé sur les deux chemins de succès par `rawset` pour les champs
  `doubleTrack/depot2/stationA2/stationB2/platformA2/platformB2` ;
- 13.12 est déjà corrigé avec `resumeAttempts`, au plus trois échecs de
  `StartStopVehicle`, panneau `EX|...|R|`, puis libération de `_railExpansion`.

B5 ajoute une reprise save/reload idempotente qui ne rappelle pas `StartStopVehicle` lorsqu'une
rame `resume` a déjà quitté le dépôt.

## Vérifié, n'est PAS un bug

- **G2 / `_hadAbandonsThisPass` (renvoi de l'étape 12) — confirmé sain.** Initialisé à `false`
  (`main.nut:226`), posé par `_markPairAbandoned` (`lines.nut:316`) sur **tous** les chemins, y
  compris le rail reprenable (`task_rail.nut:1030-1033`, atteint depuis `_consumeRailSearch`
  → `_recordRailAttempt`), lu en `task_projects.nut:859` et remis à `false` en `908`. Pas de fuite :
  `hadAbandons` fait partie de la condition d'entrée du bloc (`863`), donc un drapeau posé est
  toujours consommé. Vérifié aussi qu'aucun appel exécuté **entre** la lecture (859) et la remise à
  zéro (908) ne repose le drapeau : `_resizeAirFleets` commence à `task_air.nut:612`, les quatre
  sites d'abandon d'air sont tous au-dessus (`11, 14, 24, 27, 165, 453`), et
  `OpexIncrementalUpdateProjects`/`OpexBuildProjects` sont des fonctions libres de `projects.nut`
  sans accès à `this`. Le drapeau posé par une autre tâche (feeders, air) entre deux passes est bien
  consommé par la passe suivante — c'est l'effet voulu par le commentaire G4§1.
- **`portfolio_max_batch = 1` ↔ lot dynamique.** Avec le défaut (`info.nut`, les quatre
  `*_value = 1`), `maxBatch` borne effectivement la passe à une construction : `builtCount` peut déjà
  valoir 1 en sortie de `_consumeRailSearch` (`task_projects.nut:482`) et la garde `525` supprime
  alors tout le balayage. Le nettoyage de `railPlan` de `task_rail.nut:141-146` est bien inerte dans
  cette configuration, comme son commentaire l'annonce. Sous `portfolio_dynamic_batch = 1`,
  `maxBatch` est totalement contourné (`525`, `603-606`, `658-661`, `708-711`, `772-775`, `824-827`) :
  c'est délibéré et documenté par le commentaire d'`info.nut` qui présente le lot dynamique comme
  l'alternative à l'augmentation de `portfolio_max_batch`.
- **Émission de l'entonnoir à chaque passe (et non une fois par mois) malgré son nom.**
  `OpexMonthlyFunnelLog` (`probes.nut:102-108`) écrit à chaque appel et
  `_recordMonthlyFunnelPass` est appelé une fois par dispatch de `projects`. C'est assumé côté
  lecteur, qui agrège explicitement « par mois calendaire (somme des passes) »
  (`sweeps/diag_1v1_shared_monthly.py:345`). Seul le mélange stock/flux pose problème (13.2).
- **`_c63RecordPassAndProbe` est compatible avec un correctif d'attribution dans `probes.nut`.**
  Le site d'appel (`task_projects.nut:2-21`) appelle `OpexC63NotePass` puis relit
  `C63_INVEST_LEDGER.lastKind` (l. 6) pour décider s'il faut déclencher la sonde de vivier vide. Il
  attend de `lastKind` le **type de la passe qui vient d'être classée**. Le défaut d'attribution
  relevé par l'étape 2 porte sur `days` (= intervalle écoulé **avant** la passe, imputé au `kind`
  **de** la passe, `probes.nut:366-369` puis `421`), pas sur `lastKind` : un correctif qui impute
  `days` à l'ancien `lastKind` avant de l'écraser ne demande **aucune** contrepartie ici. Un
  correctif qui décalerait `lastKind` d'une passe, en revanche, casserait `_c63RecordPassAndProbe`.
- **G6§1 dans `_expandRailLines`.** La garde d'entrée (`task_rail.nut:306`) et le `break` de
  l'en-tête de boucle (`319`) font bien traverser jusqu'au bloc `RAIL_REFLEET` avec `best` nul quand
  `rail_expand = 0` / `rail_refleet = 1` (les deux défauts livrés). Le chemin vivant est
  `RAIL_SEARCH_RESUMABLE` (`436-447`), pas l'appel bloquant.
- **Pas de contamination par le champ `kind` manquant des lignes feeders (renvoi de l'étape 9).**
  Les deux boucles de classification de ligne de ce périmètre (`task_rail.nut:320` et `380`) testent
  `!("kind" in line)` avant tout usage, en plus du test de mode : une ligne feeder sans `kind` est
  écartée dans les deux cas. Les lignes rail créées ici portent toujours `mode` et `kind`
  (`task_rail.nut:1014`).

## Hors périmètre, à relire ailleurs

- **`probes.nut::OpexC63NotePass` (étape 2)** — l'attribution de `days` reste à corriger là-bas ;
  la contrepartie côté `task_projects.nut` est analysée ci-dessus et se résume à une contrainte sur
  le correctif, pas à une modification.
- **`sweeps/diag_1v1_shared_monthly.py:363-368`** — la somme mensuelle de `considered`/`accepted`
  (constat 13.2) se corrige soit à l'émission, soit à la lecture ; l'arbitrage dépasse ce périmètre.
- **`sweeps/diag_1v1_shared_monthly.py:385-399`** — parseur `MONTHLY_FUNNEL_DETAIL` sans émetteur
  (constat 13.5) : à supprimer ou à alimenter, décision conjointe avec le chantier C63/C58.
- **`task_rail.nut::_consumeRailUpgrade` (≈1070-1086)** — gel de `_railSearch` sur `CASH` : constat
  déjà tranché par l'étape 7, non rouvert ici. Le reste du fichier a été relu normalement.
- **`task_road.nut:281`, `task_air.nut:443`, `task_water.nut:44`** — servent de référence au constat
  13.1 (garde correcte, `reason = "build_failed"` normalisé, champs `detail`/`error` renseignés).
  C'est le rail qui s'écarte de la convention, pas l'inverse ; rien à corriger dans ces trois
fichiers.

## Réconciliation M1 — 2026-09-16

Le scheduler émet désormais `IB|yy|budget|selectionPoolCapital|B0` et
`task_projects` conserve `B<batchBuilt>`. Les trois positions historiques restent
identiques et le parseur accepte encore les anciens `IB` sans suffixe. Le JSON ajoute
`selection_pool_capital` et garde `selected_capital` comme alias. Le commentaire
`IG|` côté scheduler ne prétend plus qu'un solveur B&B inexistant a prouvé un optimum.

**Passe résiduelle 2026-09-17.** Deux écarts rail actifs ont été corrigés sans modifier le choix
de route : les deux flushes de `PROJECT_DISCARD` remettent désormais `passDiscards=[]`, comme les
autres modes, ce qui empêche la republication des mêmes rejets au retour de tentative ; et le
panneau `EU|` est émis sous `RAIL_EXPAND || RAIL_REFLEET`, donc visible sur le chemin default
refleet-only. Côté harnais, le bit IG historique est exposé comme `selection_not_exact`, avec
`knapsack_truncated=null`, et le banc 3 ans publie `n_vehicles` via le décodeur physique H3 plutôt
que le nombre brut d'entrées `VEHS`.
