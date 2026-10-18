# V257 — Diagnostic locomotives et wagons rail (18 octobre 2026)

Volets 1 et 2 de la tâche V257 (`docs/taches.md`, lignes 154-159). Revue du
choix de locomotive, de wagon et de longueur de rame, fret et voyageurs, chez
OpexAI et chez AAAHogEx, plus une mesure sur la campagne déjà jouée
`railseul_40x3_20261018`. Le volet 3 (révision périodique) est une esquisse.
Aucun fichier sous `ai/` n'a été modifié. Aucun banc, Docker ni OpenTTD n'a
été lancé.

Branche lue : `v257`, commit `9efd679` (`docs(taches): codex sur la suite RVA`).
Sources OpexAI : ce worktree, `ai/OpexAI/`. AAAHogEx est absent du worktree ;
le source lu est `/home/deploy/projects/openttd-ml/ai/AAAHogEx-115/` (les
citations ci-dessous sont relatives à ce répertoire). Chaque affirmation de
code a été relue sur le fichier cité.

Les chiffres de la campagne sont une mesure de composition du matériel, pas
une porte V102 et pas une qualification. Les résultats antérieurs au
2026-09-09 ne sont pas utilisés comme preuve. Le commentaire de
`catalog.nut:134-135` cite une médiane de vitesse du 2026-08-30 : c'est une
note de code, pas une mesure courante.

## 1. OpexAI

### 1.1 V96 ne gouverne pas le rail

V96 « moteur / avion de la partie » vit dans `air_economics_c121.nut`.
`OpexC121GameEngineTryShortcut` (`air_economics_c121.nut:1694-1696`) prend un
`airportType` et un avion. Aucun appel `OpexC121GameEngine*` n'existe ailleurs
dans `ai/OpexAI/`. Le catalogue rail est reconstruit à part :

- une fois par an, `OpexCatalog::refresh` appelle `_refreshRail`
  (`catalog.nut:1001`, déclenché par `scheduler_tasks.nut:408`) ;
- à la sortie d'un moteur, `ET_ENGINE_AVAILABLE` marque la couche
  `engines.<mode>` (`event_handlers.nut:440-458`, `events.nut:49-50`) et la
  régénération réactive rappelle `_refreshRail` pour le mode rail
  (`orchestrator.nut:838-846`).

La table des futurs candidats change donc. La ligne déjà construite garde
l'objet locomotive copié à la construction (`task_rail.nut:1211-1213`).

### 1.2 À quel moment la rame est choisie

Trois passages du même calcul, tous avant la pose de la voie :

1. Génération du candidat : `OpexMakeCandidate` (`candidates.nut:618`) appelle
   `OpexLineEconomics` (`candidates.nut:714`). Un profit annuel prévu ≤ 0 est
   rejeté (`candidates.nut:734`).
2. Après le quai trouvé : `OpexPrepareRailRoute` rappelle l'économie avec la
   longueur de quai réelle (`builder_rail.nut:2898-2903`).
3. Après l'A* : `OpexCompleteRailRouteAfterSearch` recalcule avec la longueur
   de tracé, somme des pas Manhattan tuile à tuile
   (`builder_rail.nut:2958-2976`). La distance tarifaire reste le Manhattan
   des extrémités (`economy.nut:162-165`, paramètre `distance`) ; le temps de
   trajet et le coût de voie prennent `routeDistance` (`economy.nut:178`).

Le journal de construction `RAIL_BUILD` (`task_rail.nut:1132-1141`) enregistre
le cargo, la distance, le profit prévu, le coût, le nombre de rames et le
nombre de wagons. Il n'enregistre ni l'identifiant, ni le nom, ni la vitesse,
ni la puissance de la locomotive. Ces champs sont posés sur un panneau `OL|`
(`task_rail.nut:1183-1185` : id, vitesse catalogue, vitesse effective,
puissance, effort de traction) et `PL|` (`task_rail.nut:1186-1188` : quai,
wagons, longueurs). Le harnais ne conserve que les panneaux `OR`/`OB`
(`sweeps/bench_1v1_5y_20seeds.py:570`, couverture `retained_signs_only`).

Ensuite la ligne ne rechoisit plus :

- le second train et le doublement reprennent `line.loco` et le prix du wagon
  du catalogue pour le cargo, sans relecture de `locoByCargoWagons`
  (`task_rail.nut:417`, `task_rail.nut:454`) ;
- les rames au-delà de deux, chemin V190, sont un `AIVehicle.CloneVehicle` du
  train déjà en service (`task_rail.nut:540`) ;
- l'ajout de wagons après coup (`rail_expand`) a été figé à 0 puis retiré
  (`task_rail.nut:383`). Le quai est pourtant posé avec une marge de deux
  wagons (`catalog.nut:31`, `catalog.nut:49-52`) que rien ne remplit plus tard ;
- « upgrade » dans `task_rail.nut` est le doublement de voie
  (`task_rail.nut:1269`, journal `action=double_track` à
  `task_rail.nut:1330`), pas un changement de moteur.

Renouvellement compagnie : `SetAutoRenewStatus(true)`,
`SetAutoRenewMonths(-6)`, `SetAutoRenewMoney(OpexCashReserve())`
(`main.nut:736-738`). Aucun `SetAutoReplace` dans `ai/OpexAI/`. L'événement
autoreplace ne fait que remapper les identifiants de véhicules
(`event_handlers.nut:30-39`). Le modèle remplacé est donc le même modèle.

### 1.3 Critère de locomotive

Le choix n'est pas un maximum de profit ni de ROI du moteur. Il est précalculé
une fois par an (et à chaque moteur nouveau, cf. §1.1) dans
`OpexCatalog::_refreshRail` (`catalog.nut:382`).

Un seul type de wagon par cargo : la plus grande capacité, le premier gagne
en cas d'égalité (`catalog.nut:433-454`). Le poids plein du wagon fret inclut
`AICargo.GetWeight` multiplié par `vehicle.freight_trains`
(`catalog.nut:437-441`).

Les locomotives retenues ont de la puissance sur le type de rail choisi
(`HasPowerOnRail`, `catalog.nut:463-464`). Elles sont triées par vitesse
catalogue décroissante (`catalog.nut:505-513`). Pour chaque cargo et chaque
nombre de wagons de 1 à `OpexRailNominalMaxWagons` (`catalog.nut:18`,
`w ≤ 2p−1`), le départage est, dans cet ordre (`catalog.nut:556-567`) :

1. vitesse de croisière soutenable de la rame **pleine sur rail plat** ;
2. accélération à mi-vitesse (donc effort de traction et puissance) ;
3. coût d'entretien annuel ;
4. prix d'achat.

Le prix et l'entretien ne départagent que deux physiques équivalentes. Si la
locomotive la plus rapide tient son plafond, les locomotives au plafond
inférieur sont sautées (`catalog.nut:523-524`). `catalog.loco`, la plus rapide
en vitesse catalogue, ne sert qu'au panneau annuel (`catalog.nut:476-478`).

La même table sert le fret et les voyageurs. Ce qui les sépare est le wagon
du cargo, le sens payé, et les défauts ci-dessous.

### 1.4 Longueur de rame

`OpexLineEconomics` (`economy.nut:166`) dimensionne **une** rame pour emporter
`monthlyUnits × STATION_RATING_PCT / 100` avec `STATION_RATING_PCT = 50`
(`economy.nut:24`, `economy.nut:233-242`). La locomotive lue est
`locoByCargoWagons[cargo][wagons-1]` (`economy.nut:244`), puis une correction
si le cycle change (`economy.nut:261-268`).

Le nombre de trajets chargés par mois (`economy.nut:91-98`) utilise la durée
d'un aller si `bidirectional` est vrai, l'aller-retour sinon.
`OpexLoadedTripsPerMonth` est appelé avec `kind == "pax"`
(`economy.nut:226-227`). Les voyageurs sont donc payés dans les deux sens ;
le fret compte un retour à vide pour la fréquence, tout en ayant calculé la
vitesse avec le poids **plein** sur tout le trajet (`catalog.nut:83-85`,
`catalog.nut:527`).

Le fret ajoute le temps de chargement à quai (départ quand le wagon est plein,
`economy.nut:368-381`). Le nombre de rames va de 1 à `MAX_RAIL_TRAINS = 2`
(`economy.nut:42`, boucle `economy.nut:365`). V190 inactif
(`info.nut:569-574` défaut 0, `globals_pre.nut:67-69`) : on part de 1 rame.
Le départage des 1 contre 2 rames est le ROI, puis le profit absolu
(`economy.nut:407-418`).

Défauts qui coupent les compositions mixtes :

| Réglage | Défaut | Effet au défaut |
|---|---|---|
| `v163_multi_cargo` | 0 (`info.nut:615-618`) | pas de second cargo fret. `OpexV163CandidateSecondary` rend null (`economy.nut:547-549`) |
| `v207_rail_mail` | 0 (`info.nut:630-634`) | pas de fourgon postal sur une ligne voyageurs (`candidates.nut:981`) |
| `v180_rail_wagon_boost_pct` | 0 (`info.nut:335-341`, `globals_pre.nut:21`) | pas d'allongement au-delà de l'offre à 50 % |
| `v190_rail_double_build` | 0 | une rame au départ, plafond 2 seulement si la ligne est doublée plus tard |

La part de ville captée par une gare voyageurs est `TOWN_CATCHMENT_SHARE_PCT = 22`
(`candidates.nut:961`). Ce 22 % date d'une calibration du 2026-08-28 citée
dans le commentaire : il n'est pas remesuré ici. Les industries n'ont pas
cette décote (`candidates.nut:959-960`).

Le quai demandé est la longueur des wagons utiles plus deux wagons de marge,
bornée par `station_spread` (`economy.nut:333-335`, `catalog.nut:49-52`).
Cette marge n'est pas convertie en wagons supplémentaires après la construction.

### 1.5 Ce que le profit suppose

Physique, hypothèse explicite pour le jeu de base, pas pour un NewGRF
(`catalog.nut:62-64`) :

- force `min(TE × 1000, puissance × 746 × 18 / (5 × v))` (`catalog.nut:65-70`,
  recopié dans la boucle `catalog.nut:537-539`) ;
- résistance `masse × (10 + 15 × (512+v) / 512)` plus traînée
  `14 × clamp(2048/vmax, 1, 192) × (1 + 3 × éléments / 20) × v² / 1000`
  (`catalog.nut:73-80`) ;
- masse = poids de la locomotive + wagons × poids plein (`catalog.nut:83-85`) ;
- croisière par dichotomie sous le plafond `min(vitesse loco, vitesse wagon)`
  (`catalog.nut:92-110`) ;
- vitesse effective entre arrêts : profil trapézoïdal sur **plat**,
  0,036 tuile/jour par km/h (`catalog.nut:127-135`). Virages, pentes et ponts
  restent inconnus avant l'A* et ne sont pas réinjectés dans la vitesse après
  le tracé : seul le kilométrage change (`builder_rail.nut:2966-2970`).

Compte d'exploitation (`economy.nut:387-401`) :

- recette = unités transportées × `AICargo.GetCargoIncome(cargo, distance Manhattan, jours d'aller arrondis au-dessus)` (`economy.nut:327`, `economy.nut:387`) ;
- entretien annuel = `trains × loco.runningCost` (`economy.nut:400`). Le champ
  `wagon.runningCost` est stocké (`catalog.nut:445`) et n'est pas soustrait ;
- amortissement = (prix loco + prix des wagons) / durée de vie **de la
  locomotive** (`economy.nut:349`, `economy.nut:399`). L'infrastructure est
  amortie à `INFRA_AMORT_PCT = 0` (`economy.nut:48`).

Il n'y a pas de fiabilité, pas de pente, pas de coût d'entretien des wagons,
et la vitesse fret est celle de la rame chargée aussi sur le retour à vide.

### 1.6 Quand un nouveau modèle sort

L'événement rafraîchit le catalogue (§1.1). Les **prochains** candidats
lisent la nouvelle table. Les lignes existantes gardent `line.loco`.
L'autorenew rachète le même modèle. Le second train clone la rame en service.
Rien, côté rail, ne ressemble à `OpexAirBestEngineForLine`
(`air_fleet.nut:8`) ni à la tâche mensuelle V252 (`task_v252.nut:7`).

## 2. AAAHogEx

Le choix est **par ligne**, au moment du dessin de la route, puis revu selon
le cache décrit au §2.3. Il n'y a pas de locomotive unique de la partie.

### 2.1 Critère

`HogeAI::CalculateProfitModel` (`main.nut:781-806`) pose `roiBase` tant que
la compagnie n'est pas riche ou qu'il y a de l'inflation. Sinon, s'il reste
beaucoup de slots véhicules, `buildingTimeBase` ; sinon `vehicleProfitBase`.
`GetValue` (`main.nut:828-835`) renvoie le ROI, le revenu par temps de
construction, ou le revenu par véhicule. En début de partie le chemin est
`roiBase`. `GetEngineSetsOrder` (`estimator.nut:1034-1045`) trie alors les
rames par ROI décroissant, sinon par `routeIncome`.

`TrainRoute::ChooseEngineSet` (`trainroute.nut:781-787`) prend l'élément `[0]`
de cette liste. Le choix retenu est donc le meilleur ROI (début de partie) ou
le meilleur revenu de route, parmi les compositions effectivement évaluées.

Le préfiltre physique n'est pas ce classement. Il ne s'applique que si
`checkRailType` ou `limitTrainEngines == 1` (`estimator.nut:1473-1480`) :
`min(vitesse, vitesse wagon) × (100+fiabilité)/200 × min(min(5000, TE×10), puissance) × facteur de trésorerie`.
`TrainRoute::GetEstimator` pose bien `limitTrainEngines = 1` et
`checkRailType` (`trainroute.nut:220-226`), mais le dessin courant de la
route passe par `GetEngineSets` avec une autre limite : 6 locomotives et
6 types de wagons au premier dessin (`trainroute.nut:866-868`), sinon le
défaut du constructeur, 10 locomotives et 3 types de wagons en `roiBase`,
5 et 2 sinon (`estimator.nut:1012-1017`). Dans ce cas les moteurs sont
mélangés par `AIBase.RandItem` (`estimator.nut:1482-1483`) puis les N premiers
sont évalués en économie complète. La conversion de type de rail
(`ChooseEngineSetAllRailTypes`, `trainroute.nut:908-910`) repasse au score
physique, avec 5 locomotives et 2 wagons.

### 2.2 Wagons, longueur, locomotives multiples

Cinq sélecteurs de wagons (`estimator.nut:1240-1283`) : équilibre
vitesse / (prix + 3 × entretien) par capacité, capacité par longueur, vitesse,
inverse de l'entretien, inverse du prix. `_GetWagonEngines` garde le meilleur
de chaque sélecteur (`estimator.nut:1346-1352`). `GetEngineSets` n'en évalue
ensuite que `limitWagonEngines` (`estimator.nut:1420-1429`).

Les cargos secondaires (courrier sur voyageurs, céréales + bétail, parfois un
retour) passent par `GetSuitableSubWagonEngine` (`estimator.nut:1048`) et sont
ajoutés à la rame (`estimator.nut:1556-1576`). Le commentaire
`estimator.nut:190` dit que le train peut porter un autre cargo en même temps.

La longueur grossit wagon par wagon tant que la rame tient dans le quai, lui-même
borné par `maxStationSpread` (`estimator.nut:1661-1674`). Chaque longueur est
scorée. Une locomotive de plus est ajoutée si l'accélération en pente est ≤ 0
(`estimator.nut:1703-1708`) ou si la croisière en pente est sous 90 % de la
vitesse max (`estimator.nut:1830-1833`).

Physique utilisée pour ce score : croisière mélangeant plat et pente,
`(plat × 3 + pente) / 4` (`estimator.nut:2198-2204`), traînée, et malus de
fiabilité sur les jours si les pannes sont actives (`estimator.nut:1711-1713`,
`estimator.nut:1737-1739`). L'entretien compte **chaque** locomotive et
**chaque** wagon (`estimator.nut:2142-2147`). L'amortissement n'est ajouté que
si les pannes sont activées (`estimator.nut:42-51`, ajouté à l'entretien dans
`estimator.nut:59`).

Le journal `BuildTrain` (`trainroute.nut:1198`) imprime `GetExplain`
(`estimator.nut:247-255`) puis la composition (`estimator.nut:458-478`) :
nom du moteur, vitesse de croisière **modélisée** (`speed:`), nombre de
locomotives seulement s'il est ≥ 2 (suffixe `xN` après le nom), wagons
`NomxCompte`, et `(single)` si la route est conçue à une rame. Le `xN` **avant**
le nom est `vehiclesPerRoute`, la flotte prévue, pas le nombre de locomotives.
La puissance et l'EngineID ne sont pas écrits.

`BuildTrain` construit une rame (`trainroute.nut:1201-1213`). Les rames
suivantes passent par `CheckCloneTrain` (`trainroute.nut:2364-2414`), qui
clone sans ligne `BuildTrain`.

### 2.3 Renouvellement

`TrainRoute::ChooseEngineSet` **remplace** `CommonRoute::ChooseEngineSet`.
L'expiration de 1 500 jours (`route.nut:2295-2300`) est le chemin commun
(route, route routière, avion). Elle ne s'applique pas au train, dont le cache
est dans `GetEngineSets` (`trainroute.nut:790-837`) :

- durée minimale de maintien : 365 jours si la ligne a moins de 5 ans, 3 ans
  entre 5 et 10 ans, 10 ans après (`trainroute.nut:796-804`) ;
- ce plancher redescend à 365 jours si le quai a de la place libre
  (`trainroute.nut:806-816`) ;
- dans les 10 ans, revérification annuelle de la production : on redessine si
  un cargo attendu dépasse 1 000 et que sa production a monté
  (`trainroute.nut:821-837`).

`CheckTrains` (`trainroute.nut:2256`) ne renouvelle que si une autre route
principale existe et si `HasIncome(20000)` (`trainroute.nut:2316-2318`). Si
l'ensemble moteur a changé, ou s'il reste ≤ 600 jours de vie
(`trainroute.nut:2354`), le train va au dépôt et `BuildNewTrain` reconstruit
la composition. `CheckOldVehicles` (`route.nut:1622-1639`) ignore explicitement
`VT_RAIL`. `CheckRailUpdate` (`trainroute.nut:2429-2440`) convertit le type de
rail si un meilleur moteur l'exige, pas avant 5 ans, puis pas à nouveau avant
15 ans.

## 3. Mesure sur `railseul_40x3_20261018`

Campagne déjà jouée, citée comme mesure (pas comme porte) dans
`docs/taches.md:140-142` : rail seul, 40 graines × 3 ans, `decision_log` et
`--script-debug`. Fichiers lus, sans relancer de partie :

- 40 journaux `results/railseul_40x3_20261018_engine/railseul_seed*_r0.log` ;
- `results/railseul_40x3_20261018.jsonl` (schéma compagnie et
  `line_telemetry`).

Le bundle ne contient pas les sauvegardes. `decode_vehicles` connaît
`engine_type` de la tête (`sweeps/physical_counters.py:371-375`) mais
`extract_company_record` ne le publie que pour l'air
(`sweeps/bench_1v1_5y_20seeds.py:1117-1123`). Le jsonl rail a
`air_engine_counts` vide et aucune colonne moteur rail.

### 3.1 OpexAI — ce que `RAIL_BUILD` contient

569 lignes `RAIL_BUILD`, toutes `trains=1`, aucune `wagons2`. Profit **prévu
à la décision**, pas le profit réalisé, et pas par moteur : le moteur n'est
pas dans la ligne.

| Année | Cargo | n | Profit prévu moyen | Médiane (index n//2) | Wagons les plus fréquents |
|---|---|---:|---:|---:|---|
| 1970 | COAL | 130 | 44 757 | 44 137 | 4, 3, 5, 2 |
| 1970 | PASS | 94 | 6 864 | 5 826 | 1 (59), 2 (32), 3 (3) |
| 1970 | WOOD | 47 | 30 594 | 30 951 | 3, 4, 2 |
| 1970 | IORE | 14 | 30 074 | 28 168 | 4, 2, 3 |
| 1970 | GRAI | 2 | 29 690 | — | 4, 3 |
| 1970 | OIL_ | 1 | 7 683 | — | 2 |
| 1971 | PASS | 43 | 4 585 | 4 290 | 1 (35) |
| 1971 | IORE | 32 | 25 773 | 26 980 | 3, 4, 2 |
| 1971 | GRAI | 17 | 28 932 | 30 278 | 3 (12) |
| 1971 | OIL_ | 15 | 23 602 | 22 200 | 3, 2 |
| 1971 | WOOD | 14 | 32 704 | 35 367 | 3 |
| 1971 | LVST | 8 | 22 362 | 26 620 | dispersé |
| 1971 | GOOD | 6 | 100 604 | 101 887 | 5 à 11 |
| 1972 | PASS | 40 | 3 324 | 2 946 | 1 (37), 2 (3) |
| 1972 | OIL_ | 25 | 22 171 | 19 803 | 2, 3 |
| 1972 | GRAI | 23 | 27 048 | 25 743 | 3, 2, 4 |
| 1972 | LVST | 20 | 26 696 | 30 051 | 6, 5, 4 |
| 1972 | IORE | 19 | 25 979 | 24 712 | 3, 2 |

Céréales et bétail sont des lignes séparées. Aucune ligne voyageurs n'a de
second cargo. Le fret utile tient en général dans 2 à 6 wagons ; les
marchandises dépassent parfois (un 12 wagons en 1972).

`RAIL_EXPAND action=second_train` : 0. `action=clone` : 0.
`action=double_track` : 1971, 59 réussites et 23 échecs ; 1972, 42 réussites
et 18 échecs ; rien en 1970. Le doublement de voie a donc lieu. Le second
train, qui exigerait ensuite un stock en attente (`task_rail.nut:411-413`),
n'est jamais journalisé comme construit dans ces 40 parties.

### 3.2 AAAHogEx — `BuildTrain`

1 098 lignes `BuildTrain` parsées (une ligne `BuildTrain failed` écartée, ce
n'est pas un achat). Lecture selon `estimator.nut:467-476` : nom, `xN` après
le nom = locomotives de la rame, wagons, `speed:` = croisière modélisée.

| Année | Achats | 1 loco | ≥ 2 locos | Rames `(single)` | Cargo mixte | Voyageurs, tous avec courrier |
|---|---:|---:|---:|---:|---:|---:|
| 1970 | 315 | 315 | 0 | 287 | 190 | 50 |
| 1971 | 356 | 356 | 0 | 232 | 160 | 66 |
| 1972 | 427 | 426 | 1 | 225 | 284 | 173 |

La seule rame à deux locomotives est un `SH '8P' (Steam)x2` avec 10 coal
trucks, en 1972, flotte prévue de 6. Le mécanisme multi-locomotives existe
(§2.2) ; sur ce jeu de base et ces trois années il ne se déclenche presque
pas. `vehiclesPerRoute` (le `xN` avant le nom) a pour médiane 1 chaque année,
et pour moyenne 1,27 / 2,10 / 3,10. C'est la flotte **prévue** au dessin, pas
le nombre de rames posées par cette ligne de log. Les clones ne sont pas
dans `BuildTrain`.

Moteurs achetés (croisière médiane du modèle de rame, pas la vitesse catalogue ;
wagons médians) :

| Année | Moteur | n | Croisière méd. | Wagons méd. |
|---|---|---:|---:|---:|
| 1970 | Floss '47' (Diesel) | 221 | 122 | 8 |
| 1970 | UU '37' (Diesel) | 52 | 114 | 8 |
| 1970 | SH/Hendry '25' (Diesel) | 15 | 106 | 6 |
| 1970 | Chaney 'Jubilee' (Steam) | 10 | 98 | 4,5 |
| 1970 | Ginzu 'A4' (Steam) | 8 | 106 | 4,5 |
| 1970 | SH '8P' (Steam) | 8 | 114 | 4,5 |
| 1970 | SH '30' (Electric) | 1 | 122 | 13 |
| 1971 | Floss '47' (Diesel) | 275 | 122 | 10 |
| 1971 | UU '37' (Diesel) | 61 | 114 | 8 |
| 1971 | SH/Hendry '25' (Diesel) | 18 | 106 | 3,5 |
| 1971 | SH '8P' (Steam) | 1 | 108 | 13 |
| 1971 | Chaney 'Jubilee' (Steam) | 1 | 98 | 2 |
| 1972 | Floss '47' (Diesel) | 304 | 122 | 10 |
| 1972 | UU '37' (Diesel) | 58 | 114 | 8 |
| 1972 | SH/Hendry '25' (Diesel) | 50 | 106 | 3 |
| 1972 | SH '30' (Electric) | 8 | 122 | 13 |
| 1972 | SH '8P' (Steam) | 6 | 114 | 8 |
| 1972 | Chaney 'Jubilee' (Steam) | 1 | 98 | 3 |

Wagons des achats voyageurs : Passenger Carriage et Mail Van sur **chaque**
rame voyageurs (50, 66, 173), plus quelques Goods Van (5 en 1971, 19 en 1972).
Fret : Grain Hopper et Livestock Van presque à parité (140/140, 94/95,
111/112), puis Coal Truck, Wood Truck, et le reste. Longueur : médiane 8
wagons en 1970, 10 en 1971 et en 1972 (min 1, max 13).

Puissance et EngineID : absents du journal.

### 3.3 Profit réalisé par moteur

Impossible sur ces artefacts.

`line_telemetry.lines` porte `mode`, `cargo_types` (identifiants numériques),
`profit_this_year_gbp`, `profit_last_year_gbp`, `vehicle_ids`,
`capacity_by_cargo`. Il ne porte ni EngineID, ni nom, ni `lineId` Opex. On ne
peut pas le joindre à `RAIL_BUILD line=N` ni à un moteur. Les panneaux `OL`
qui auraient l'EngineID ne sont pas extraits. Les sauvegardes ne sont pas
dans le bundle, donc `engine_type` de `physical_counters.py:375` n'est plus
relisible.

Le profit prévu Opex du §3.1 reste le seul profit rattaché à une ligne rail
dans les journaux, et il n'est pas réalisé. Le compte économique déjà publié
pour cette même campagne (`docs/taches.md:142`) est le réalisé agrégé, sans
moteur : en 1972, 16,5 trains Opex contre 29, 319 k£ contre 1 221 k£ ;
voyageurs Opex 8,8 k£/train contre 48 k£ pour les trains voyageurs+courrier
d'AAA ; bétail+céréales AAA 51 k£ contre céréales et bétail séparés 16 et
11 k£. Ce diagnostic ne recalcule pas ces totaux. Il constate que la
composition journalisée (une rame, voyageurs souvent à un wagon et sans
courrier, céréales et bétail sur deux lignes, contre ~8-10 wagons, courrier
systématique, céréales et bétail dans la même rame) est le mécanisme cohérent
avec cet écart. La part causale de chaque levier n'est pas mesurée.

### 3.4 Banc minimal, à lancer à part

Un nouveau `railseul` avec le harnais actuel **ne donnera pas** le moteur
Opex : `RAIL_BUILD` ne le contient pas, et le collecteur jette `engine_type`
hors de l'air. Le rejouer n'est utile qu'après un des deux branchements
suivants, sans changement de comportement :

1. Publier, pour le rail comme pour l'air, `engine_type`, la longueur de rame
   et le profit du véhicule depuis `primary_vehicles_detail`
   (`physical_counters.py:371-377`, filtre air à
   `bench_1v1_5y_20seeds.py:1122`). Le cliché de décembre donne alors, par
   compagnie et par année, le modèle réellement en service et son profit
   réalisé. Il ne donne toujours pas le profit **prévu**.
2. Conserver les panneaux `OL`, `PL`, `PC` et `OF`
   (`task_rail.nut:1171-1194`) au lieu de `retained_signs_only`. On obtient
   l'EngineID, la puissance, l'effort, les wagons et le profit prévu, joints
   par `lineId` au journal `RAIL_BUILD`. Le profit réalisé demande encore le
   point 1, ou un `lineId` dans `line_telemetry`.

Protocole suffisant pour cette photo, une fois le collecteur branché : rail
seul, 3 graines (42, 100, 7), 3 ans, `decision_log` et `--script-debug`, même
réglage que `railseul_40x3_20261018`. Ce n'est pas une porte. Côté AAA, le
journal `BuildTrain` actuel suffit déjà pour le nom, la croisière modélisée,
les wagons et le nombre de locomotives ; il manque la puissance et l'EngineID,
que le point 1 couvrirait aussi.

## 4. Écarts, par impact probable

Ce classement est une hypothèse ordonnée par ce que les journaux et le compte
déjà publié rendent visible. Il ne remplace pas une porte A/B.

1. **Longueur et composition de la rame.** Opex pose une rame, souvent un
   wagon voyageurs (59/94 en 1970, 37/40 en 1972) et 2 à 6 wagons fret.
   AAA pose une médiane de 8 puis 10 wagons, le courrier sur chaque rame
   voyageurs, les céréales et le bétail ensemble. Les défauts `v163_multi_cargo`
   et `v207_rail_mail` à 0 coupent exactement ces deux compositions. Les
   changer est un changement de comportement : hors de ce diagnostic, et
   soumis à qualification s'il est tenté. La marge de quai de deux wagons
   n'est jamais remplie (`task_rail.nut:383`).
2. **Pas de révision par ligne.** Le moteur est copié à la construction et
   recloné. Un modèle nouveau ne touche que les candidats futurs. AAA
   redessine la rame (cache d'un an à dix ans, ou chaque année si le quai est
   trop long) et reconstruit si l'ensemble a changé ou s'il reste ≤ 600 jours
   de vie. Sur 1970-1972 cet effet est encore faible : les deux IA achètent
   surtout le diesel disponible, et AAA ne passe presque pas à deux
   locomotives. Il grandit dès qu'un modèle plus rapide sort après l'ouverture
   des lignes.
3. **Le critère Opex maximise la vitesse sur plat à pleine charge**, puis
   l'accélération, et ne regarde le prix qu'en dernier. Une locomotive un peu
   plus lente et beaucoup moins chère n'est pas choisie si une plus rapide
   tient son plafond (`catalog.nut:523-524`). AAA classe les compositions
   évaluées par ROI en début de partie. Son échantillon de moteurs est en
   partie aléatoire (§2.1), donc son critère économique ne voit pas tout le
   catalogue.
4. **Le compte Opex oublie l'entretien des wagons, la pente et la fiabilité.**
   AAA les met dans le score (`estimator.nut:2142-2147`,
   `estimator.nut:2198-2204`). L'écart de critère est réel ; son effet en
   livres sur 1970-1972 n'est pas isolé, parce qu'on ne connaît pas le moteur
   qu'Opex a acheté.
5. **Une rame, et le second train n'est pas sorti** dans les 40 parties, y
   compris après 101 doublements réussis. AAA prévoit souvent plusieurs rames
   (`vehiclesPerRoute` moyen 3,1 en 1972) et les ajoute par clone. Le volume
   de flotte du compte publié (16,5 contre 29 trains en 1972) va dans le même
   sens. V190, qui construirait plus d'une rame fret, est au défaut 0.

## 5. Esquisse du volet 3

Réglage nouveau, défaut 0, comme demandé dans `docs/taches.md:159`. Pas
d'implémentation ici.

Objet : pour une ligne rail déjà ouverte, comparer la rame stockée
(`line.loco`, `wagonId`, `wagons`, `task_rail.nut:1211-1213`) à la table
courante `locoByCargoWagons` et au réalisé (`profit` dernière année, cargo en
attente, déjà lus par `_expandRailLines` en `lastProfit` / `lastWaitingA`).
Deux déclencheurs : le passage périodique, et le rafraîchissement catalogue
qui suit `ET_ENGINE_AVAILABLE` (déjà en place pour les **futurs** candidats,
`orchestrator.nut:846`). Remplacer au plus une rame par passage, sur le modèle
de `task_v252.nut:102-146` (construire le successeur, partager les ordres,
envoyer l'ancien au dépôt). Le rail n'a pas d'équivalent de
`OpexAirBestEngineForLine` (`air_fleet.nut:8`) : le critère de remplacement
reste à écrire, et il ne doit pas être le seul maximum de vitesse catalogue,
puisque c'est déjà ce qui fige la rame longue et chère.

Contrainte d'opcodes. `task_v252.nut:41-77` balaie **toutes** les lignes air
à chaque mois pour n'en remplacer qu'une. V256, décrit dans `docs/taches.md:152`
et absent du code de cette branche, coupe ce balayage : au plus un appel par
ligne, arrêt au premier remplaçable. Pour le rail, ne pas importer le balayage
complet. Étaler :

- un curseur d'index de ligne, sauvegardé avec l'état (au même titre que les
  autres curseurs de file), avancé d'une ligne par passage ;
- soit une intention réactive qui ne traite que cet index
  (`orchestrator.nut:563`, `_enqueueReactive`), soit un pas de worker sur le
  reliquat de tick déjà enveloppé par `_runBackgroundQueue`
  (`orchestrator.nut:559`) et `_runNextTaskWithSlackLedger` (`scheduler.nut:7`).

Un passage complet des lignes prend alors autant de cycles que de lignes.
`OpexLineEconomics` n'est appelé que pour la ligne du curseur. Le cache par
ligne de l'idée V256 sert à ne pas recalculer une ligne dont le catalogue, le
profit réalisé et l'attente n'ont pas bougé depuis le passage précédent.

Hors de cette esquisse, et à qualifier séparément s'ils sont ouverts : le
courrier voyageurs (`v207_rail_mail`), le second cargo fret (`v163_multi_cargo`),
et l'allongement de rame (`v180_rail_wagon_boost_pct`). Les activer n'est pas
décidé par ce diagnostic.
