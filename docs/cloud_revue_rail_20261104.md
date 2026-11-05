# Revue de code rail : prompts pour sessions cloud (4 novembre 2026)

## Mode d'emploi

- **Une session cloud par tâche**, toutes sur la branche
  **`ccr-6d627d08-tlnphk`** (`rail_loop=1` par défaut depuis a8cfb1e8).
- **Coller le préambule commun, puis le bloc de la tâche.**
- **Ordre** :
  - T1 à T9 sont indépendantes et peuvent tourner en parallèle ;
  - T10 (synthèse) vient en dernier, une fois les autres poussées.
- **Livrable de chaque tâche** :
  - un fichier `docs/revue_rail_20261104/<Tn>_<sujet>.md` ;
  - une branche `cloud/revue-rail-<Tn>-20261104` poussée.

| Tâche | Sujet | Lignes | Modèle | Effort |
|---|---|---:|---|---|
| T1 | RAIL-LOOP, désormais actif par défaut | ~700 + câblage | **Fable 5.1** | high |
| T2 | Ordonnanceur rail I : slot de recherche, extension | `task_rail.nut` 1-1414 | **Fable 5.1** | xhigh |
| T3 | Ordonnanceur rail II : stock, upgrade, réparations | `task_rail.nut` 1414-3342 | **Opus 5.5** | high |
| T4 | Pathfinder et recherche segmentée | `builder_rail.nut` 2027-3095 | **Opus 5.5** | high |
| T5 | Plans de gare et de quai | `builder_rail.nut` 1-2027 | **Opus 5.5** | high |
| T6 | Construction, dépôt, rollback, signaux | `builder_rail.nut` 3095-4748 | **Fable 5.1** | high |
| T7 | Exécution du plan et mise en service | `builder_rail.nut` 4748-5972 | **Opus 5.5** | high |
| T8 | Rames : choix moteur, wagons, longueur, clonage | `rail_templates`, `rail_long*`, `catalog` (rail) | **Opus 5.5** | high |
| T9 | Inventaire du code rail expérimental | V190, DOUBLE-GROW, PAIR, RDS, V271… | **Sonnet 5.5** | medium |
| T10 | Synthèse et priorisation | les 9 rapports | **Opus 5.5** | medium |

**Pourquoi ces choix :**
- **Fable** va aux machines d'état et aux transactions, où un bug coûte des lignes entières :
  le slot de recherche, la pose et le rollback, RAIL-LOOP.
- **Opus** va aux revues de logique locale.
- **Sonnet** va à l'inventaire mécanique.
- **Avec un budget serré** :
  - garder T1, T2, T6 et T8 ;
  - T1 d'abord, car le code est désormais actif.

---

## Préambule commun (à coller en tête de chaque tâche)

```
Dépôt jrdoublet/openttd-ml, branche ccr-6d627d08-tlnphk. OpexAI est une IA NoAI (Squirrel) pour
OpenTTD 15.3. Elle affronte AAAHogEx-115. Lis d'abord AGENTS.md, ai/OpexAI/CLAUDE.md (pièges
Squirrel et NoAI, « ce qui ressemble à un bug mais n'en est pas un ») et docs/architecture_courante.md.

Contexte :
- En rail seul, Opex fait ~83 % du profit d'AAA à 5 ans et ~45 % à 10 ans.
- Opex plafonne vers 55 véhicules et 1,2 train par ligne ; AAA va de 4 à 12 trains par ligne.
- Le profit par véhicule est d'environ 30 k£ chez Opex, contre 60 k£ chez AAA.
- RAIL-LOOP (rail_loop=1, défaut depuis le 04/11) donne +173 k£/an en rail seul sur 20×10
  (p = 0,0014). Il est neutre à 5 ans et en multimodal.
- Rapports utiles :
  - docs/rail_loop_bancs_20261104.md ;
  - docs/cloud_double-voie_20261104.md ;
  - docs/point_9h_20261103.md ;
  - docs/cloud_pack_20261104/ (campagnes, graines et journaux agrégés).

Ta mission : REVUE DE CODE du périmètre ci-dessous. Cherche les défauts réels :
- logique fausse ;
- état incohérent ou fuite de slot ;
- argent dépensé sans retour ;
- chemins d'échec qui laissent des objets sur la carte ;
- bornes et index décalés ;
- persistance après chargement ;
- coût en opcodes non borné ;
- conditions qui rendent une fonctionnalité inerte (exposition nulle).

L'exemple du jour : OpexRailLoopDepotFlow cherchait le dépôt aux indices 4..n-4 alors que
OpexBuildDepot le pose à l'indice 1-2. Résultat : 0 boucle construite, sans aucune erreur.

Pour CHAQUE constat, donne :
- fichier:ligne ;
- gravité (bloquant / perte de profit / robustesse / style) ;
- le scénario concret qui déclenche le défaut ;
- la preuve (code cité, compteur dans docs/cloud_pack_20261104/logs_*.csv si pertinent) ;
- la correction proposée ;
- le gain attendu.

Classe chaque constat :
- (a) certain ;
- (b) probable ;
- (c) à vérifier en moteur.

Ne signale pas les drapeaux expérimentaux à défaut 0 comme du « code mort » : cela relève de T9.

Règles :
- Aucun changement de défaut ; aucun commit sur ccr-6d627d08-tlnphk ni sur master.
- Corrections permises uniquement si elles sont petites et certaines (a) :
  - sur une branche cloud/revue-rail-<Tn>-20261104 ;
  - le comportement au défaut ne change que pour un bug avéré, et le rapport le dit ;
  - chaque correction a son test dans sweeps/test_revue_rail_<Tn>_20261104.py ;
  - pour les modules qui en ont une, la projection OFF existante doit être mise à jour.
- Pas de Docker ni d'OpenTTD ici :
  - lance la suite `python3 -X utf8 -m unittest discover -s sweeps -p 'test_*.py'` avant et après ;
  - les échecs préexistants connus sont test_b6_portfolio_causality, deux test_rail_long_v3_multi
    et test_v166_aaahogex_settings (source AAAHogEx absente du clone, GPL : ne pas la chercher) ;
  - les tests sensibles aux octets peuvent échouer à cause de CRLF→LF : vérifie avant/après, ne
    « corrige » pas les fins de ligne.
- Le Squirrel ne se compile pas ici : relis chaque modification deux fois (closures sans capture,
  const littéraux, mots réservés clone/base).
- Rapport docs/revue_rail_20261104/<Tn>_<sujet>.md, en français, avec :
  - un résumé de 5 lignes ;
  - le tableau des constats triés par gain attendu ;
  - un plan de banc pour le PC : smoke 4×6 rail seul, graines 17 512 314 8191, référence
    OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1], AAA rail seul.
- Pousse la branche.
- Dernière ligne de ta réponse : « <Tn> TERMINÉ ».
```

---

## T1 — RAIL-LOOP, actif par défaut (Fable 5.1, high)

```
Périmètre : ai/OpexAI/rail_loop.nut (tout), son câblage gardé par RAIL_LOOP (main.nut,
task_rail.nut, scheduler.nut, settings.nut, globals_pre.nut, info.nut, persist.nut si concerné),
et les fonctions empruntées qu'il appelle :
- OpexDoubleGrowPrimaryRoute et OpexDoubleGrowVerifyRoute (double_grow_geometry.nut) ;
- OpexV190Fix2PlaceSignal* (v190_fix_directional.nut) ;
- OpexCreateRailPathfinder ;
- OpexTestRailTrack.

Questions prioritaires :
1. Exposition. Au smoke 4×6, les rejets restants sont depot_front_curve 46, back_lead_A/B 30 et
   cash 20 ; au 20×10, 56 « phase=fail ». Pour chaque motif, la condition est-elle nécessaire ou
   trop stricte ? Quelle variante sûre l'éviterait (dépôt dont l'avant tombe dans un virage,
   arrière de quai occupé par le lead d'une autre ligne, budget A* de 8 000) ?
2. Sûreté :
   - le PBS de garde est désormais facultatif (commit a8cfb1e8) : une rame peut-elle sortir du
     dépôt à contre-sens, ou rester bloquée ?
   - la condition ArmSafe (toutes les rames vont vers l'aval) peut-elle ne jamais devenir vraie ?
3. Persistance : sauvegarde puis chargement à chaque phase (search, track2, arm, certified).
   Les champs railLoop* sont-ils tous relus ? Une recherche perdue redevient-elle admissible ?
4. Croissance :
   - le critère « attente ≥ capacité d'une rame » et le plafond cap = cantons − 2 ;
   - le rythme d'un ajout tous les 45 jours ;
   - au 20×10, il y a eu 119 ajouts pour 33 boucles. Peut-on croître plus vite sans
     interblocage ?
5. Interaction avec C41 (réparation sur VehicleLost), INVEST-STALL et RAIL-LONG, ainsi qu'avec la
   mise à la casse et le remplacement de rames sur une ligne en boucle.
```

## T2 — Ordonnanceur rail I : slot de recherche et extension (Fable 5.1, xhigh)

```
Périmètre : ai/OpexAI/task_rail.nut lignes 1-1414 :
- _tryBuildRailProject, _expandRailLines, _continueRailExpansion ;
- _startRailSearch, _continueRailSearch, _consumeRailSearch ;
- l'interaction avec scheduler.nut, projects_selection.nut et _railSearch.

Constats connus à confirmer et à corriger proprement :
- task_rail.nut:643 : sous V190, _expandRailLines ne rend plus la main quand _railSearch != null.
- task_rail.nut:706-728 → :1830 : _startRailUpgradeSearch écrase _railSearch sans test.
- docs/v190_eco_20261103.md §5 : graine 841478 en 1972, 89 RAIL_SEARCH OK, 0 PROJECT_CHOSEN.

Questions :
1. Cycle de vie complet du slot _railSearch : qui le prend, qui le libère et sur quel chemin
   d'échec il peut rester occupé. Compteur à rapprocher : PROJECT_DISCARD reason=search_in_progress
   (~236 par 4×6 en référence, contre ~350 RAIL_BUILD).
2. Après 1973, la plupart des candidats sont rejetés origin_served et la caisse dort. Le
   pipeline rail laisse-t-il passer des projets finançables (seconde source, nouvelle
   destination, prolongement) ?
3. Budget d'opcodes par passe : y a-t-il des boucles non bornées sur _lines ou sur la carte ?
4. Une recherche longue peut-elle être reprise (RAIL_SEARCH_RESUMABLE) après un chargement ?
```

## T3 — Ordonnanceur rail II : stock, upgrade, réparations (Opus 5.5, high)

```
Périmètre : ai/OpexAI/task_rail.nut lignes 1414-3342 :
- _recordRailAttempt ;
- _startRailUpgradeSearch et _consumeRailUpgrade ;
- _startRailStockSearch et ses gestionnaires de délai et de fin ;
- réparations _v131* ;
- _revalidateRailStockPlan ;
- _v184InitRailSlots.

Questions :
1. La recherche « stock » (spéculative) concurrence-t-elle les projets financés ? Dans quels cas
   garde-t-elle le slot alors qu'un projet attend ?
2. Réparations V131 : une réparation peut-elle boucler, dépenser sans fin, ou démolir un ouvrage
   utilisé par une autre ligne (ou une boucle RAIL-LOOP) ?
3. _recordRailAttempt et la mémoire d'échecs : un échec transitoire (caisse, slot occupé)
   bannit-il durablement une bonne paire ?
4. Upgrade (doublement V190) : depuis l'adoption de RAIL-LOOP, ce chemin est-il encore utile au
   défaut ? Peut-il entrer en conflit avec une ligne en boucle ?
```

## T4 — Pathfinder et recherche segmentée (Opus 5.5, high)

```
Périmètre : ai/OpexAI/builder_rail.nut lignes 2027-3095 :
- OpexTrainSlopeSteepness ;
- OpexCreateRailPathfinder et ses poids ;
- recherche segmentée (OpexAdvanceSegmentedSearch, OpexSegmentIgnoredTiles,
  OpexLocalStructureChoices, OpexV294cSwitchWeight) ;
- OpexV214PathGeometry, OpexMatchPlanExact, OpexRailPathGeometryIssue ;
- la bibliothèque de pathfinding sous ai/OpexAI/ ou ai/library/.

Questions :
1. Avec V294_RAIL_CONTINUOUS, OpexAdvanceRailPathfinder rend structures = []
   (builder_rail.nut:2204). Quels consommateurs supposent encore des structures planifiées ?
   (DOUBLE-GROW v2 rejetait tous les ponts et tunnels à cause de cela.)
2. Les poids (pente, virage, pont, tunnel, aiguillage) produisent-ils des tracés que les rames
   longues ou lourdes montent mal ? Comparer avec OpexTrainSlopeSteepness.
3. Où est la limite d'itérations ? Un échec A* coûte combien de jours de slot ? Taux NOPATH dans
   les journaux du pack.
4. forbid_90_deg et les tuiles ignorées : y a-t-il des cas où le pathfinder ne peut pas
   atteindre un quai pourtant constructible ?
```

## T5 — Plans de gare et de quai (Opus 5.5, high)

```
Périmètre : ai/OpexAI/builder_rail.nut lignes 1-2027 :
- OpexV307* (sink room, plans ciblés) ;
- OpexV207RankStationPlans ;
- OpexV264* (ancrage) ;
- OpexRailTryPlatformLength ;
- OpexRailOpenJoinKey et OpexRailOpenNewStationFunded ;
- OpexRailPlatformPlans.

Constats terrain :
- les quais d'Opex font 3-4 tuiles contre 7 chez AAA ;
- RAIL-LONG v1-v3 n'a pas réussi à les allonger durablement (docs/rail_long_20261103.md) ;
- RAIL-LOOP rejette back_lead_A/B quand l'arrière d'un quai n'est pas libre et plat.

Questions :
1. Pourquoi la longueur de quai choisie reste-t-elle courte ? Qui la plafonne (production, caisse,
   terrain, gabarit) ? Fichier:ligne.
2. Les plans de gare peuvent-ils réserver une case libre à l'arrière du quai, pour une future
   boucle ou un allongement, à coût quasi nul ?
3. Jointure aux gares existantes (rail_sibling, rail_open) : des cas où la jointure échoue en
   silence ou crée un quai inutilisable ?
4. Captation (catchment) : les gares sont-elles bien placées pour la production ? La note de
   source est de 151 chez Opex, contre 212 chez AAA.
```

## T6 — Construction, dépôt, rollback, signaux (Fable 5.1, high)

```
Périmètre : ai/OpexAI/builder_rail.nut lignes 3095-4748 :
- OpexSameStationEnd ;
- OpexV190TraceParallelTrack ;
- OpexV199CanDemolishTile ;
- journaux V296a ;
- OpexTestRailTrack ;
- OpexBuildDepot ;
- OpexRollback et OpexV301Trim ;
- OpexAccountSignal.

Questions :
1. Rollback : après chaque échec possible de la pose, que reste-t-il sur la carte, et que
   reste-t-il dépensé ? Rails, ponts, tunnels, gares, dépôts, signaux. Les compteurs d'orphelins
   sont-ils fiables ?
2. OpexBuildDepot place le dépôt à l'indice 1-2, collé à la gare, en aiguillage sur la voie
   principale. Est-ce un goulot pour plusieurs rames (entrées et sorties de dépôt qui bloquent la
   gorge) ? Ce placement empêche-t-il des usages futurs (boucle, allongement) ? Proposer un
   placement « après le premier canton » sans casser les contrats.
3. Signaux : où sont-ils posés au défaut, de quel type, à quel espacement ? Sur voie unique, sont-
   ils utiles ou nuisibles (blocage de rames en face à face) ?
4. Coûts : le coût réel posé correspond-il à l'estimation (RAIL_TERRAIN_FACTOR=170,
   OpexAccountSignal) ? L'AIAccounting fantôme est-il bien protégé partout ?
```

## T7 — Exécution du plan et mise en service (Opus 5.5, high)

```
Périmètre : ai/OpexAI/builder_rail.nut lignes 4748-5972 :
- OpexPrepareRailRoute et OpexPlanRailRoute ;
- OpexVehicleSlotAvailable et OpexRailVehicleSlotAvailable ;
- OpexV200WantDouble ;
- OpexExecuteRailPlan ;
- OpexBuildLine (achat des rames, ordres, chargement complet, refit).

Questions :
1. Ordres :
   - full load à la source ? non-stop ? déchargement à la destination ? retour à vide ?
   - quels drapeaux sont posés (builder_rail.nut:4517 OF_NON_STOP_INTERMEDIATE) ?
   - des cas où une rame attend indéfiniment au chargement sur une source faible ?
2. Nombre de rames initial et plafond par ligne (OpexRailVehicleSlotAvailable) : qui limite Opex à
   environ 1,2 rame par ligne en voie unique, en dehors de RAIL-LOOP ?
3. Chemins d'échec entre la pose des voies et l'achat des rames : une ligne peut-elle exister
   sans rame, ou avec une rame sans ordres ?
4. Cohérence de l'objet line (platformA/B, depot, vehicles, trains) avec ce que lisent ensuite
   RAIL-LOOP, INVEST-STALL et la persistance.
```

## T8 — Rames : moteur, wagons, longueur, clonage (Opus 5.5, high)

```
Périmètre :
- choix des locomotives et des wagons (catalog.nut, partie rail ; economy.nut, estimations
  rail) ;
- rail_templates.nut ;
- rail_long_v3.nut, rail_long_v3_multi.nut, rail_long_v3_upgrade.nut ;
- task_rail_long_v2*.nut ;
- invest_stall* (fleet top-up) ;
- double_grow_fleet.nut, pour la logique de clonage.

Constats :
- AAA roule avec des rames de 10-13 wagons, souvent 2-3 locomotives, sur des quais de 7 tuiles ;
- Opex roule avec 2-4 wagons et 1 locomotive ;
- RAIL-LONG v3 est un no-go économique (docs/rail_long_20261103.md) ;
- INVEST-STALL a fait 37 compléments de flotte choisis, 0 achevé.

Questions :
1. Puissance et effort de traction contre poids chargé et pente : le choix de locomotive est-il
   juste ? Y a-t-il des rames sous-motorisées qui rampent sur les pentes ?
2. Pourquoi RAIL-LONG v3 a-t-il échoué : idée mauvaise, ou défaut (devis rejeté, quai non
   allongé, remplacement bridé) ? Fichier:ligne.
3. INVEST-STALL, 0 complément sur 37 : trouver le point exact où la transaction est abandonnée.
4. Renouvellement des rames (âge, fiabilité) et refit : y a-t-il des rames vieilles ou des
   wagons du mauvais type laissés en service ?
```

## T9 — Inventaire du code rail expérimental (Sonnet 5.5, medium)

```
Périmètre : tous les drapeaux rail de ai/OpexAI/info.nut et leur code :
- V190, V197, V190-FIX2 ;
- DOUBLE-GROW 1/2 ;
- RAIL-PAIR et V271 tandem ;
- RAIL-DEPOT-SIGNAL ;
- RAIL-SEARCH-PRIO ;
- RAIL-LONG 1/2/3 ;
- INVEST-STALL ;
- EB-2 ;
- V181 boucle (OpexConvertDoubleTrackToLoop) ;
- builder_rail.nut 5972-7349 (OpexV190ExecuteRailPlan, OpexTraceTrackTiles…).

Livrable : un tableau avec une ligne par drapeau. Colonnes :
- défaut ;
- fichiers et nombre de lignes ;
- dernier verdict de banc (chercher dans docs/ et docs/taches.md) ;
- code partagé avec RAIL-LOOP (OpexDoubleGrow*, OpexV190Fix2*) ;
- dépendances croisées ;
- recommandation : garder / retirer / fusionner.

Ne rien supprimer (phase de nettoyage : inventaire → liste validée par l'utilisateur →
suppression). Signaler surtout le code mort qui coûte des opcodes au défaut (gardes évaluées à
chaque passe).
```

## T10 — Synthèse (Opus 5.5, medium, après les autres)

```
Lis les branches cloud/revue-rail-T1..T9-20261104 et leurs rapports
docs/revue_rail_20261104/*.md.

Produis docs/revue_rail_20261104/T10_synthese.md :
- les 10 constats au plus fort gain attendu, toutes tâches confondues ;
- les doublons ou contradictions entre rapports ;
- les corrections déjà codées et leurs risques croisés (deux branches qui touchent la même
  fonction) ;
- l'ordre de fusion et de banc recommandé pour le PC, un banc à la fois : smoke 4×6 rail seul,
  puis porte A 40×5, puis porte B 20×10.

Pas de code. Pousse sur cloud/revue-rail-T10-20261104.
Dernière ligne : « T10 TERMINÉ ».
```
