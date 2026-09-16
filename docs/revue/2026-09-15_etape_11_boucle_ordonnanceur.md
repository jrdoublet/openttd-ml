# Étape 11 — Boucle, persistance et ordonnanceur

- **SHA revu** : `2c317cc`
- **Modèle / effort prévus** : Sonnet 5 / high
- **Périmètre** : `ai/OpexAI/main.nut`, `persist.nut`, `scheduler.nut`, `scheduler_tasks.nut` — 1 713 l.
- **Plan** : `docs/revue_code_2026-09-15_plan.md`

**Enjeu annoncé**

Contrat « nom de tâche » en trois endroits sans table ; double appel dans `_dispatchTownGrowth`
avec récursion ; budget d'opcodes non reportable ; 3 familles de deadline ; 28 méthodes sans prototype.

**Rappel de méthode** — diagnostic seulement, rien n'est corrigé au passage. Vérifier à la main,
pas par grep seul. Vérifier le défaut d'un réglage avant de le qualifier de code mort. Ancrer
chaque constat sur `fichier:ligne`. Ne lire que `ai/OpexAI/CLAUDE.md` et les fichiers du
périmètre : pas `docs/taches.md` en entier, pas les journaux, pas `results/`.

---

## Constats

### 11.1 — Contrat « nom de tâche » sans table nom→fonction : aucun garde-fou contre une désynchronisation future        [gravité : P2]
`main.nut:290-325` (littéral `_taskQueue`), `scheduler.nut:214-240` (cascade de `if (task.name == "...")`),
`scheduler_tasks.nut` (15 `_dispatch*`) — vérifié à la main (extraction et diff des trois listes de noms,
15/15/15 identiques aujourd'hui : `air, air_fleet, c41_rail_junction, c41_rail_signals, c41_road, c41_water,
catalog, expand, feeders, projects, refleet, repay, report, scrap, town_growth`). Le code fait ce qu'il
prétend faire *aujourd'hui*, mais rien ne relie ces trois listes structurellement : si un futur commit
renomme une entrée à un seul des trois endroits (ou fait une faute de frappe), `scheduler.nut:241-243`
tombe dans la branche par défaut :
```
task.enabled = false;
...
return false;
```
— aucune `AILog.Error`, aucune exception, aucun panneau : la tâche est désactivée pour le reste de la
partie, silencieusement. `OpexC56TaskLog("TASK_EXIT", ...)` ne se déclenche que sous `c56_task_trace`
(hors défaut) et ne dit de toute façon pas « nom inconnu », juste « sortie ». Conséquence observable :
une régression de renommage ne casse pas la compilation Squirrel (donc échappe au smoke-test qui
détecte les erreurs de compilation, cf. `CLAUDE.md`), elle se voit seulement à l'absence durable d'un
type de panneau au banc — un mode de défaillance lent à diagnostiquer.

### 11.2 — `_tryTownGrowth` ne retourne jamais `true` : `town_growth_skip_noop` ne distingue jamais un tour utile d'un tour vide        [gravité : P2]
`scheduler_tasks.nut:682` teste `TOWN_GROWTH_SKIP_NOOP && !this._tryTownGrowth(year)`. Lu à la main dans
`task_town.nut:53-219` : `OpexAI::_tryTownGrowth` ne contient **aucun** `return true` — tous les chemins
sont soit un `return;` nu (garde précoce), soit une chute de fin de fonction après le `foreach`/`break`
de construction (ligne 217). En Squirrel, l'un et l'autre valent `null`, donc `!this._tryTownGrowth(year)`
vaut toujours `true`. Résultat : dès que `TOWN_GROWTH_SKIP_NOOP` est actif, la condition se réduit à
`TOWN_GROWTH_SKIP_NOOP` seul — la branche récursive (`_runNextTask()` imbriqué) est prise à **chaque**
passage, qu'une ligne bus ait réellement été construite ou non, et la branche `else` (second appel à
`_tryTownGrowth`) n'est **jamais** atteinte. Ce que le réglage prétend faire
(`info.nut:1908` : "After an empty town-growth attempt, run the next task immediately") n'est donc pas
ce qu'il fait : il n'y a pas de distinction "tour vide" vs "tour utile", et pas de double exécution
possible (la lecture initiale du plan laissait craindre les deux `this._tryTownGrowth` actifs
simultanément — vérifié faux, cf. 11.3). Réglage vérifié à défaut 0 (`globals_post.nut:272`,
`info.nut:1909`) : inerte au banc par défaut, mais le bug touche la seule branche que ce réglage est
censé activer.

### 11.3 — Récursion `_runNextTask()` dans `_dispatchTownGrowth` : pas de risque de pile, mais corrompt l'attribution des ledgers C41/C39        [gravité : P3]
`scheduler_tasks.nut:678-693`, seul site de récursion de l'ordonnanceur (confirmé par lecture des 15
`_dispatch*` : aucun autre n'appelle `_runNextTask`/`_runNextTaskWithSlackLedger`). Tracé à la main :
la profondeur est bornée par la taille de la file (15 tâches), pas de risque de dépassement de pile — la
tâche suivante immédiate (`repay`, dernière de la file) est presque toujours due au même `_taskCycle` et
termine la récursion en un seul niveau. En revanche `_runNextTask()` (`scheduler.nut:103`) réinitialise
`this._c41LastTaskName = "idle"` puis le réaffecte au nom de la tâche *suivante* choisie par l'appel
imbriqué (`scheduler.nut:203`) — en écrasant la valeur `"town_growth"` posée par l'appel englobant avant
que celui-ci n'entre dans `_dispatchTownGrowth`. `_runNextTaskWithSlackLedger` (`scheduler.nut:36-38`)
mesure les opcodes de l'appel *entier* (tentative de croissance urbaine + tâche suivante exécutée en
cascade) mais les attribue entièrement à `this._c41LastTaskName`, donc à la tâche suivante, jamais à
`town_growth`. Sous `C41_SLACK_LEDGER`/`C39_PASS_CLOCK_LEDGER` (activables indépendamment de
`town_growth_skip_noop`), ceci fausse silencieusement la mesure d'allocation d'opcodes par tâche — la
télémétrie même que l'enjeu du plan invoque pour revérifier le sous-effectif de gares. N'affecte que
le cas où `TOWN_GROWTH_SKIP_NOOP=1` (défaut 0, cf. 11.2).

### 11.4 — Le budget d'opcodes non reportable reste, par défaut, la source du gaspillage décrit à l'étape du 09-06 ; C20 et C36.1 sont sans rapport        [gravité : P2]
`main.nut:511-546` : le réglage `LOOP_BUDGET` (`globals_post.nut:103`, défaut `false`, confirmé
`settings.nut:58`) bascule entre deux boucles. Défaut (`LOOP_BUDGET=0`) : `main.nut:542-543` exécute
**une seule** tâche puis `AIController.Sleep(1)` — le commentaire `main.nut:521-525` documente
explicitement que ce chemin « dépens[e] quelques centaines d'opcodes et jett[e] les ~9 700 restants »
si la tâche piochée est hors période. Ce mécanisme historique, à défaut, est donc toujours celui qui
tourne au banc sauf réglage explicite. Le correctif en place (`LOOP_BUDGET=1`, `main.nut:526-534`) ne
« reporte » toujours rien d'un tick à l'autre — il ne fait que drainer plusieurs tâches *dans le même
tick* tant que `AIController.GetOpsTillSuspend() > LOOP_BUDGET_FLOOR` (2000) et `drained < LOOP_BUDGET_MAX_TASKS`
(8), sans jamais appeler `Sleep`, laissant le moteur suspendre lui-même l'IA en fin de budget — ce qui
évite le gaspillage d'un `Sleep` prématuré mais ne crée aucune réserve inter-tick. `C20`
(`info.nut:1607-1614`, échéance de sécurité par tranche pour l'A* reprenable) et `C36.1`
(`projects.nut:886-1327`, cache incrémental du vivier de portefeuille) sont vérifiés indépendants de
`LOOP_BUDGET` — aucune des deux fiches ne touche à `main.nut`/`scheduler.nut` ni au réglage `loop_budget` ;
elles changent le *contenu* d'une tâche, pas l'admission au budget de tick. Le diagnostic du 09-06 doit
donc être revérifié avec `loop_budget` explicitement à 1, pas supposé résolu par C20/C36.1.

### 11.5 — Trois familles de deadline non unifiées, documentées précisément        [gravité : P3]
Vérifié par lecture croisée des quatre fichiers :
1. **`dueCycle` (admission au round-robin)** — `scheduler.nut:181-206` : un entier comparé à `_taskCycle`,
   avancé à `_taskCycle + 1` par défaut à chaque exécution (`scheduler.nut:206`), ou gelé à `2147483647`
   pour des tâches armées par événement (`c41_water`, `c41_road`, `c41_rail_signals`, `c41_rail_junction`,
   `main.nut:293-299`). Gouverne uniquement si la tâche est *choisie* dans ce tour de file.
2. **Cadences calendaires internes au dispatch** — indépendantes de `dueCycle` : `_lastCatalogMonth == ym`
   (`scheduler_tasks.nut:35`), `_lastReportYear == year` (`scheduler_tasks.nut:501`), `_lastRepayMonth == ym`
   (`scheduler_tasks.nut:699`). Une tâche peut être *due* selon (1) mais ressortir en no-op selon (2) —
   c'est explicitement le problème que `town_growth_skip_noop` tente de traiter côté `town_growth`, qui
   lui n'a pas de garde calendaire du tout et se fie uniquement à un retour d'exécution (cf. 11.2).
3. **Budgets d'opcodes** — `LOOP_BUDGET_FLOOR`/`LOOP_BUDGET_MAX_TASKS` (`main.nut:81-82`) bornent
   *combien de tâches* un tick peut drainer ; `BUILD_TICK_MARGIN` (`main.nut:76`) et les tranches de
   `_railSearch`/`_continueRailSearch` (mesurées dans `scheduler.nut:150-176` via
   `OpexOpsMeasureBegin/End`) bornent *combien d'opcodes* une seule tâche continue peut consommer avant
   de rendre la main. Aucune des trois familles ne connaît les deux autres : une tâche peut être due
   (1), non-calendairement bloquée (2) et malgré tout couper une tranche A* au milieu (3) sans qu'aucun
   mécanisme central n'arbitre — chacune est un garde-fou local ajouté à une fiche différente (C20, C38,
   C41.x, C39.6).

### 11.6 — Trois états transactionnels multi-tick (`_railExpansion`, `_railSearch`, `_dynamicBatch`) absents de `Save`/`Load`/`_reconcileAfterLoad`        [gravité : P1]
`main.nut:132-140` déclare les trois champs avec leurs commentaires d'intention : `_railExpansion`
(« le train roule vers son dépôt pendant que la boucle principale continue par pas de dix jours »),
`_railSearch` (repris « en TÊTE de `_runNextTask` », terminé en le remettant à `null`), `_dynamicBatch`
(« nécessaire si un A* rail rend la main »). Vérifié par lecture intégrale de `persist.nut` : ni
`Save()` (lignes 2-102), ni `Load()` (103-140), ni `_reconcileAfterLoad()` (143-219) ne mentionnent l'un
des trois noms. Une sauvegarde prise pendant une expansion rail en vol ou une recherche A* reprise
perd donc silencieusement cet état au rechargement (`_railExpansion`/`_railSearch` redeviennent `null`
via les valeurs par défaut du constructeur, `main.nut:239` n'initialise même pas `_railExpansion`
explicitement — il hérite de la déclaration de classe `null`). Conséquence observable : pour
`_railExpansion` en particulier, le second train de doublement de voie a déjà pu être acheté et lancé
en jeu avant la sauvegarde ; si la finalisation (ajout à `line.vehicles`, passage de `doubleTrack` à 1)
n'a lieu que dans `_continueRailExpansion` — jamais rappelée puisque l'état est perdu — ce train
physique devient orphelin de la comptabilité de `_lines` : non suivi par `_scrapDeadLines`/
`_refleetRoadLines`/etc., et la ligne reste éligible à une nouvelle tentative d'expansion par
`_expandRailLines` alors qu'elle vient d'en recevoir une. À comparer, `_lines`/`_pendingLines` bénéficie
d'une reconciliation complète et prudente (validation de tuile, de station, de propriétaire,
purge des véhicules invalides) : le contraste souligne que l'absence de traitement pour ces trois
champs est un oubli plutôt qu'un choix documenté.

### 11.7 — Files de réparation `_c41RailSignalLines`/`_c41RailJunctionLines` non persistées        [gravité : P2]
`main.nut:219-221` déclare les deux tables (files de lignes à réparer après un `VehicleLost`),
peuplées par `event_handlers.nut:644/660` et consommées par `_dispatchC41RailSignals`/
`_dispatchC41RailJunction` (`scheduler_tasks.nut:420-497`). Absentes de `persist.nut` (mêmes trois
fonctions vérifiées qu'au 11.6). Une sauvegarde prise entre l'événement `VehicleLost` et l'exécution
de la micro-tâche de réparation perd l'intention de réparation : après rechargement, la ligne concernée
ne sera réparée que si un nouvel événement `VehicleLost` la re-signale. Gravité limitée en pratique :
`C41_RAIL_LOST_SIGNAL_REPAIR`/`C41_RAIL_LOST_JUNCTION_REPAIR` sont vérifiés à défaut `false`
(`globals_pre.nut:194,200`), donc inertes au banc par défaut — mais contrairement aux ledgers de mesure
(11.6 les distingue explicitement), il s'agit ici d'une file de travail fonctionnelle, pas d'un
compteur de diagnostic : sa perte a un effet de jeu (train resté bloqué plus longtemps), pas seulement
un effet de mesure.

### 11.8 — `_lastAirFleetMonth` : champ déclaré et non persisté, jamais lu dans le périmètre revu        [gravité : P3]
`main.nut:166` déclare `_lastAirFleetMonth = -1`. Recherche exhaustive dans les quatre fichiers du
périmètre (`main.nut`, `persist.nut`, `scheduler.nut`, `scheduler_tasks.nut`) : aucune autre occurrence.
`_dispatchAirFleet` (`scheduler_tasks.nut:579-605`) ne le lit ni ne l'écrit — contrairement à
`_lastCatalogMonth`/`_lastReportYear`/`_lastRepayMonth`, qui suivent tous le même patron de garde
calendaire et sont, eux, sauvegardés. Impossible de confirmer depuis ce périmètre si le champ est
utilisé dans `task_air.nut` (hors périmètre) ou s'il est mort — voir section « Hors périmètre » ci-dessous.

## Vérifié, n'est PAS un bug

- **Contrat nom de tâche, état actuel** : les trois listes de 15 noms (`_taskQueue` dans `main.nut`,
  cascade `if` dans `scheduler.nut`, `_dispatch*` dans `scheduler_tasks.nut`) sont vérifiées identiques
  caractère pour caractère aujourd'hui (extraction + diff, aucune divergence). Le risque documenté en
  11.1 est structurel (absence de garde-fou), pas un bug actif.
- **Pas de double exécution de `_tryTownGrowth`** : la lecture initiale de l'enjeu du plan pouvait laisser
  penser à un double appel actif (deux branches qui l'invoquent). Vérifié faux après lecture complète de
  `task_town.nut` : l'absence de tout `return true` rend la branche `else` de `_dispatchTownGrowth`
  (deuxième appel potentiel) inatteignable dès que `TOWN_GROWTH_SKIP_NOOP` est actif — voir 11.2 pour le
  bug réel (contraire : jamais de distinction, pas double exécution).
- **Pas de risque de dépassement de pile côté récursion** : profondeur bornée par la taille de la file
  (15 tâches), un seul site récursif dans tout l'ordonnanceur (11.3).
- **`enabled` du `_taskQueue` non sauvegardé** : vérifié sans impact — chaque tâche dont l'état
  `enabled` dépend d'un réglage (`air`/`AIR_PORTFOLIO`, `feeders`/`FEEDER_ENABLED` et
  `FEEDER_PORTFOLIO`, `expand`/`RAIL_EXPAND`+`RAIL_REFLEET`, `town_growth`/`TOWN_GROWTH_ENABLED`,
  `c41_water`/`C41_WATER_REFRESH`, `c41_road`/`C41_ROAD_REFRESH`) est redérivée de façon déterministe à
  chaque premier passage post-`Start()`, donc post-reload également ; seul `dueCycle` doit survivre
  (et c'est ce que `taskDue` sauvegarde, `persist.nut:26-28,93-99,135-139`).
- **Comptage prototypes/corps `OpexAI::`** (contexte de l'enjeu, hors des 5 tâches précises) : vérifié
  par grep structurel sur tout le dépôt — 75 prototypes déclarés dans la classe (`main.nut:328-406`),
  105 corps `function OpexAI::...` au total, dont 3 callbacks du framework NoAI qui n'ont normalement
  pas besoin d'un prototype de classe (`Start`, `Save`, `Load`) et ~26 méthodes internes réellement
  sans prototype. Proche du « 28 » de l'enjeu (écart probablement dû au choix d'inclure ou non les
  3 callbacks) — non recompté finement, hors des 5 tâches demandées.

## Hors périmètre, à relire ailleurs

- Le rôle réel (et l'éventuelle nécessité de persistance) de `_lastAirFleetMonth` (11.8) dépend de son
  usage dans `task_air.nut`, hors périmètre de cette étape — à vérifier par l'étape couvrant ce fichier.
- Le contenu détaillé de `_continueRailExpansion`/`_continueRailSearch`/`_consumeRailSearch` (logique de
  reprise elle-même, `task_rail.nut`/`builder_rail.nut`) n'a pas été relu ligne à ligne ici : seule
  l'absence de persistance de leur état porteur (`_railExpansion`, `_railSearch`, `_dynamicBatch`, 11.6)
  a été vérifiée depuis `persist.nut`. Confirmer dans l'étape couvrant `task_rail.nut`/`builder_rail.nut`
  que rien n'y compense cette absence (ex. un recalcul idempotent au lieu d'une reprise), et confirmer
  la conséquence exacte sur `line.doubleTrack`/`line.vehicles` en cas de perte de `_railExpansion`.
- Le comptage précis 28 vs ~26/29 méthodes sans prototype (enjeu du plan) n'a pas été recompté au-delà
  du grep structurel fait ici ; à confirmer si une étape dédiée au style/aux conventions du code le
  demande.
