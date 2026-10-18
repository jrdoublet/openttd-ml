# V242 — Diagnostic du rabattement routier (18/10/2026)

Étape diagnostic seule. Aucun changement dans `ai/`, aucun banc, aucun
changement de défaut. Branche `v242diag`. Les chiffres de flotte et de
lignes ci-dessous sont relus par `sweeps/v242_feeder_diag.py` sur des
extraits déjà produits.

Le réglage `v139_feeder_bus` n'est plus dans `ai/OpexAI/` (lot V234).
La fiche et le tableau des réfutés sont dans `docs/taches.md` (V242, et
V139 à V139d).

## 1. Quand AAAHogEx pose un rabattement

Sources lues : `ai/AAAHogEx-115/route.nut`, `road.nut`, `estimator.nut`,
`place.nut`, `station.nut`, `main.nut`. Les deux lignes citées par la fiche
existent : `route.nut:4048` est l'appel `CheckTownTransfer` dans
`CommonRouteBuilder.DoPostBuild` (`route.nut:4039`), et `road.nut:1359` est
`FindFirstStations` dans `TownBus._BuildBusStops` (`road.nut:1356`). Ce
second point pose les arrêts de ville. L'ordre de transfert est créé plus
loin, dans `CreateTransferRoadRoute` (`road.nut:1514`).

Il y a deux mécanismes.

**Navette locale (`TownBus`).** Deux arrêts drive-through `STATION_NEW`
près du centre. Ordres `OF_NON_STOP_INTERMEDIATE` seulement, sans
transfert (`road.nut:1295-1304`). Un arrêt déjà utilisé par un autre
véhicule est écarté (`IsUsedStationTransfer`, `road.nut:1326`). S'il reste
moins de deux arrêts libres, la navette est retirée (`road.nut:1605-1630`).
C'est un bus temporaire, jusqu'à ce que les lignes de transfert prennent
les arrêts.

**Ligne de transfert (`RoadRoute`).** `CreateTransferRoutes`
(`road.nut:1672`) puis `CreateTransferRoadRoute` (`road.nut:1514`) :

- source : arrêt de ville dont le nom contient `#` (`IsTownStop`,
  `station.nut:2578`) ;
- destination : une gare route ou un quai déjà dans le **même groupe**
  que la gare parente (aéroport, rail ou eau), sinon une gare route neuve
  jointe à ce groupe, sinon la gare parente elle-même si c'est une gare
  route (`road.nut:1711-1745`) ;
- drapeaux : `isTransfer = true`, `isBiDirectional = false`,
  `destRoute` = la ligne parente, `useDepotOrder = false`,
  `useServiceOrder = true` avant `Initialize()` (`road.nut:1531-1541`).
  `Initialize` ne remet pas ces drapeaux à zéro (`route.nut:1884`).

Ordres de la ligne de transfert, `MakeOrder` (`route.nut:2129`) :

- à la source, tuile de gare et `isSrcFullLoadOrder` (vrai dans le
  constructeur, `route.nut:1871`) : `OF_NON_STOP_INTERMEDIATE | OF_FULL_LOAD_ANY` ;
- à la destination, parce que `isTransfer` : `OF_NON_STOP_INTERMEDIATE | OF_TRANSFER | OF_NO_LOAD`
  (`route.nut:2159-2161`) ;
- pas d'ordre de dépôt au départ (`useDepotOrder` est faux) ; un dépôt
  d'arrivée est ajouté si `BuildDestDepot` a réussi, et dans ce cas
  l'ordre de service est retiré (`road.nut:1543-1545`).

Une ligne non transfert à sens unique décharge avec `OF_UNLOAD | OF_NO_LOAD`
(`route.nut:2165`). Ce n'est pas le rabattement.

### Déclencheur, priorité, coût

Le rabattement n'est pas un candidat du tas trié par valeur. C'est un
effet de bord **après** la construction de la ligne parente passagers ou
courrier (`DoPostBuild`, commentaire : les lignes aériennes doivent être
posées vite, le travail lent est reporté). Pour chaque cargo passagers ou
courrier, `CheckTownTransferCargo` (`route.nut:4054`) sort si le lieu
n'est pas une ville, si la ligne est déjà un transfert de ville, ou si
elle n'a pas le cargo. Si `CanExtendCoverageAreaInTowns()`
(`main.nut:4371`, vrai quand la jonction distante est permise et que
`IsAvoidExtendCoverageAreaInTowns` est faux), AAA étend les quais ; une
ligne **route** parente s'arrête là, et une ville qui ne peut pas croître
aussi. Sinon `TownBus.CheckTown` puis `CreateTransferRoutes`.

Le même contrôle est rejoué avec une probabilité de 10 % dans
`_CheckBuildVehicle` (`route.nut:2813`) si la gare n'est pas en débordement.

Sur les deux bancs du 18/10, le manifeste met
`IsAvoidExtendCoverageAreaInTowns=0`, et la cfg ne touche pas
`station.distant_join_stations`. Le défaut OpenTTD 15.3 de ce réglage est
vrai (`game_settings.ini`, `station.distant_join_stations`, `def = true`).
La branche « jonction distante » s'applique donc : pas de rabattement pour
une ligne route parente. Le seuil de population de `CheckTown`
(`road.nut:1156`) est 3 000 habitants dans cette branche, 1 300 sinon.
Il est sauté si la ville peut croître : `CanGrowthTown` (`place.nut:3120`)
est vrai quand la ville n'a ni objectif eau ni objectif nourriture.
L'inflation coupe tout `TownBus` (`road.nut:1106`). Les bancs forcent
`inflation = false`, qui est aussi le défaut 15.3.

Porte économique (`IsReadyEconomy`, `road.nut:1140`) : compagnie riche,
ou argent utilisable ≥ `GetInflatedMoney(200000)` et revenu trimestriel
≥ `GetInflatedMoney(50000)`. Riche (`main.nut:4324`) : utilisable
> 10 M£ inflatés, ou ((utilisable > 500 k£ et revenu, ou utilisable
> 2 M£) et emprunt nul ou en baisse). L'argent utilisable est le solde
plafonné à 1 G£ plus la capacité d'emprunt restante (`main.nut:4295`).
Le nombre de véhicules route doit rester sous `maxRoadVehicle`
(`road.nut:285`) ; le défaut 15.3 de `vehicle.max_roadveh` est 500, non
surchargé par la cfg. La marge « support » (`route.nut:233`) bloque si la
place restante est ≤ 10 % du plafond, sauf s'il reste plus de 30 places.
Avant les premiers arrêts, `WaitForMoney(10000)` (`road.nut:1369`), puis
le prix du bus.

Arrêts supplémentaires (`CanBuildNewBusStop`, `road.nut:1804`) : aucun
sous 6 000 habitants, puis plafonds 3, 4, 5, 6 et 7 arrêts selon la
population. `FindNewBusStop` demande une acceptation 60 (passagers) ou 30
(courrier). Le chemin est borné (`pathFindLimit = 30`,
`costDrivethroughstation = 0`, `road.nut:1796`).

Les lignes parentes, elles, sont triées par l'estimation (`GetValue`,
`main.nut:828`) : ROI tant que la compagnie n'est pas riche ou qu'il y a
de l'inflation (`CalculateProfitModel`, `main.nut:781`), sinon temps de
construction s'il reste beaucoup de place, sinon profit par véhicule.
Le rabattement ne passe pas par ce tri.

### Revenu que AAA attribue au bus

La construction ne teste pas la rentabilité du bus. `BuildVehicleFirst`
achète le premier véhicule si la caisse suit.

L'estimateur d'instance (`SetTransferParams`, `estimator.nut:518`) :
si la ligne est un transfert et que la parente existe, `totalDistance`
est la distance de Manhattan entre la **destination finale** (aéroport ou
gare lointaine, `GetFinalDestStation`) et l'arrêt de bus, et
`additionalCruiseDays` reprend le temps de croisière de la ligne parente.
`destRouteCargoIncome` vient de `GetDestRouteCargoIncome / 2`
(`estimator.nut:540`). Cette fonction rend 0 hors industrie de
transformation non brute (`place.nut:2149`) : **0 pour une ville de
passagers**. `Estimate` (`estimator.nut:285`) fait ensuite
`AICargo.GetCargoIncome(cargo, totalDistance, cruiseDays + additionalCruiseDays)`
et multiplie par la capacité du bus. L'estimation d'instance crédite donc
le bus du **tarif du trajet combiné** (distance aérienne, temps bus +
avion), pas du seul tronçon routier.

Dès que la compagnie n'est plus en `roiBase` et que la ligne est un
transfert de ville, `ChooseEngineSet` (`route.nut:2305`) appelle
`Route.Estimate` sur la **classe**, avec la distance du seul tronçon bus.
Le choix de moteur ne crédite alors plus le billet d'avion. Dans les deux
cas, ce calcul choisit un moteur. Il n'autorise pas la pose.

Le coût de rabattement imputé à l'estimation de la **ligne parente**
(`GetPaxMailTransferBuildingCost`, `route.nut:349`, appelé depuis
`estimator.nut` pour le rail, la route, l'eau et l'air) est, dans la
branche des bancs (jonction distante et extension autorisée),
`GetInflatedMoney(5000)`. L'autre branche met `prix du bus × 8 + 2 000`
inflatés. `GetInflatedMoney` scale par le plafond d'emprunt
(`main.nut:4195`).

Les lignes support (`IsSupport` = transfert, transfert source, ou
industrie brute, `route.nut:191`) sont **exemptées** du retrait pour
non-rentabilité (`route.nut:2480`). Le commentaire dit qu'un transfert
peut être déficitaire si le total gagne, et note qu'il faudrait vérifier
ce total. Le total n'est pas vérifié. AAA ne vend donc pas un bus parce
que `GetProfitLastYear` du bus est négatif.

Les bus suivants (`_CheckBuildVehicle`, `route.nut:2629`) : un transfert
de ville est sauté 80 % des passages ; un véhicule de plus exige une
attente supérieure à `max(100, needsProduction)` ; le premier part si le
compte est nul et que la parente `NeedsAdditionalProducing`. Pour un
transfert, ce besoin remonte à la ligne parente (`route.nut:602`).
`GetLeftCapacity` divise la capacité max par 3 hors ligne retour
(`route.nut:664`, commentaire : sinon le transfert de ville n'arrive
presque jamais).

### Ce que le jeu paie vraiment

Lu sur la source OpenTTD 15.3, `src/economy.cpp` :

- `PayTransfer` : le commentaire dit que le paiement réel n'est pas fait.
  Le montant est le revenu du trajet parcouru jusqu'ici, moins la part
  feeder déjà créditée, fois `economy.feeder_payment_share / 100`. Il va
  dans `visual_transfer` seulement.
- `PayFinalDelivery` : `route_profit` reçoit le `DeliverGoods` **entier**.
  Le profit affiché du livreur est ce montant moins la part feeder déjà
  créditée.
- Le destructeur déplace la caisse de la compagnie de `route_profit`
  seul. `profit_this_year` reçoit `visual_profit + visual_transfer`.

Le défaut 15.3 de `economy.feeder_payment_share` est **75**
(`economy_settings.ini`). La cfg des bancs ne le change pas.
`infrastructure_maintenance` est faux par défaut et absent de la cfg.

Conséquence : le bus affiche dans `GetProfitLastYear` environ 75 % du
revenu de **son** tronçon. La caisse de la compagnie n'encaisse le billet
entier qu'à la livraison finale, une seule fois. Le profit affiché de
l'avion est le billet entier moins la part déjà affichée sur le bus.
La somme des profits véhicules suit la caisse. Compter le billet d'avion
sur le bus compte deux fois un argent qui n'entre qu'une fois, et au
mauvais véhicule.

C'est l'erreur de V139, consignée dans `docs/taches.md` : 93 k£/an
estimés pour environ 0 réel sur les livres du bus. Le journal du
4 septembre (`docs/journaux/journal_2026-09-04.md`, section C24) décrit
le même partage 75 % et un bonus de ROI de 60 % alors présent dans
`candidates.nut`. Ce bonus n'est plus dans `ai/OpexAI/candidates.nut`.

## 2. Ce que ça rapporte à AAA dans les bancs existants

### Flottes au 1er décembre 1979

Les deux campagnes nommées sont des fichiers, pas des dossiers :

- `results/diff_n0_vs_n2_20x10_pc_20261018.jsonl.gz` (et `.json`,
  `.manifest.json`) ;
- `results/v256_v252opt_20x10_pc_20261018.jsonl.gz` (idem).

20 graines, 10 ans, départ 1970, carte 256×256, OpenTTD 15.3 / OpenGFX 7.1 /
OpenTTDLab 0.0.75. `line_telemetry`, `station_supply_telemetry` et
`retained_savegames` sont nuls dans les deux JSON. Le manifeste
`diff_n0` est sale (`0d3b2b60`, difficulté Opex 2 contre 0). Le manifeste
`v256` est propre (`4e9380bd`, `v252_air_engine_refresh` 2 contre 0).
AAA a les défauts (`usable_cargos=3`, route autorisée,
`IsAvoidExtendCoverageAreaInTowns=0`).

`profit_year` est la somme des quatre derniers trimestres clos
(`sweeps/bench_v2.py`, `year_profit_metrics`). Au 1979-12-01 la couverture
est `complete` (4/4) pour les 20+20 lignes de référence du premier
banc. Ce n'est pas le profit routier, et ce n'est pas le seul calendrier
1979 : le trimestre octobre-décembre 1979 n'est pas clos, le quatrième
trimestre clos est celui de la fin 1978.

Véhicules primaires, moyenne (médiane) sur 20 parties. Lecteur :
`python3 sweeps/v242_feeder_diag.py company-jsonl`.

| Campagne | Politique | Compagnie | Route | Air | Rail | Arrêts bus | Aéroports | Capacité pax air |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| diff_n0 | reference | AAA | 174,5 (174,5) | 51,0 (51) | 70,4 (71) | 105,1 (106,5) | 35,7 (36) | 7 610 |
| diff_n0 | reference | Opex | 4,55 (5) | 137,3 (144) | 20,9 (20,5) | 34,6 (35,5) | 37,9 (39) | 18 038 |
| diff_n0 | diff_n0 | AAA | 171,9 (172,5) | 55,6 (54,5) | 72,9 (73,5) | 106,3 (105,5) | 39,0 (39) | 8 263 |
| diff_n0 | diff_n0 | Opex | 2,50 (2) | 121,8 (126) | 19,3 (19,5) | 29,7 (30,5) | 33,5 (35) | 15 027 |
| v256 | reference | AAA | 172,1 (173,5) | 50,6 (49) | 72,2 (68,5) | 105,9 (105,5) | 35,8 (36) | 7 758 |
| v256 | reference | Opex | 4,00 (4) | 136,0 (141,5) | 20,4 (20) | 34,5 (34,5) | 38,3 (39,5) | 17 679 |
| v256 | v256_v252off | AAA | 178,0 (176) | 53,1 (51,5) | 68,2 (68) | 106,5 (105) | 37,3 (38) | 8 126 |
| v256 | v256_v252off | Opex | 4,25 (4) | 139,6 (144) | 20,7 (20) | 34,6 (35) | 38,0 (38,5) | 31 764 |

Fourchettes route AAA, référence : 118–239 (`diff_n0`) et 116–223
(`v256`). Opex référence : 0–13 et 0–12. Le « 166 contre 3 » de la fiche
V139 est du même ordre ; ces deux bancs mesurent plutôt **172–178 bus
AAA contre 4 bus Opex** au défaut, à dix ans. Le profit de compagnie
AAA est d'environ 7,8 M£ sur quatre trimestres clos, celui d'Opex
référence d'environ 3,8 M£. Rien dans ce JSONL ne sépare le profit
routier, les ordres de transfert, ni le remplissage.

### Part en transfert et profit propre du bus

La télémétrie de ligne existe dans d'autres campagnes multimodes, pas
dans les deux 20×10 ci-dessus. Le lecteur groupe le dernier décembre par
politique et par compagnie. Une ligne route est un **proxy** de
rabattement si un de ses StationID est aussi celui d'une ligne air ou
rail de la même compagnie au même instant. C'est l'arrêt joint, pas le
drapeau `OF_TRANSFER`, que l'extracteur ne conserve pas
(`sweeps/bench_1v1_5y_20seeds.py`, `extract_line_telemetry`). Les champs
`revenue` et `running_cost` y sont marqués indisponibles. Les profits de
ligne sont déjà en livres (`profit_last_year` / 256).

Campagnes utilisées, bras de référence seulement :

- `results/ref_ventil_10s_y5.json` — 10 graines, année 5, instantané
  1974-12-01, faisceau `132016440730e919…`. Bras `afm_probe` laissé de
  côté.
- `results/v172_complet_porteA_40x3_20261016.json` — 40 graines, année 3,
  1972-12-01, faisceau `3c0789b8da836338…`. Bras `v172` laissé de côté
  pour Opex ; AAA y est cité seulement comme contrôle.
- `results/v163_9x6_20261013.json` — 9 graines, année 6, 1975-12-01,
  bras `v163_off`, en contrôle plus long.

| Instantané | Route AAA | Proxy joint | Part | Dont touchent l'air | Dont touchent le rail | Autres bus | Profit bus joint, année précédente | Profit air, année précédente |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ventil, référence, 1974 | 155,2 | 149,2 | 0,961 | 122,5 | 56,8 | 6,0 | −7 800 £ (méd. −9 661) | 1,654 M£ |
| v172, ref, 1972 | 101,5 | 98,7 | 0,973 | 86,6 | 29,9 | 2,8 | +3 320 £ (méd. +2 996) | 1,328 M£ |
| v163_off, 1975 | 144,0 | 136,8 | 0,949 | 111,3 | 56,8 | 7,2 | −11 197 £ (méd. −14 607) | 1,306 M£ |

La somme « touche l'air + touche le rail » dépasse le proxy joint : une
ligne peut toucher les deux. À cinq ans, environ 30 véhicules sont dans
les deux comptes (122,5 + 56,8 − 149,2).

Le profit propre des bus joints est de l'ordre de **quelques milliers de
livres, souvent négatif**, contre **1,3 à 1,7 M£** affichés par les
avions la même année précédente. Les bus non joints sont encore plus
proches de zéro (ventil référence : +118 £). Cela colle au paiement 15.3 :
le bus n'inscrit que sa part de tronçon, et cette part ne paie pas la
flotte.

### Effet sur le remplissage des avions et des trains

**Non mesurable dans ces extraits.** `decode_vehicles` et la télémétrie
de ligne ne copient ni le chargement courant, ni les drapeaux d'ordre.
`max_waiting_cargo` est le pic depuis le dernier recalcul de note, pas le
stock instantané (`bench_1v1_5y_20seeds.py`, commentaire vers la ligne 808).
Les sauvegardes des deux 20×10 ne sont pas conservées
(`retained_savegames` nul).

Le seul rapprochement possible est le pic d'attente des aéroports dont le
StationID est partagé avec une ligne route, contre les autres. Seuil
physique : pic passagers (cargo `"0"`, confirmé par la fixture
`sweeps/fixtures/c66_control_fixture_15_3.json` : avion capacité 300 type 0,
bus 35 type 0, courrier type 2) inférieur à la capacité passagers d'un
véhicule de la ligne. Ce n'est pas un taux de sièges vides.

| AAA, aéroports comparables | Pic < 1 avion | Attente / siège, moyenne des parties |
|---|---:|---:|
| ventil 1974, joints route | 231/267 = 0,865 | 0,511 |
| ventil 1974, sans route | 14/19 = 0,737 | 1,399 (médiane des parties 0,320) |
| v172 1972, joints route | 569/600 = 0,948 | 0,232 |
| v172 1972, sans route | 176/182 = 0,967 | 0,152 |

À trois ans les deux groupes sont sous un avion dans les mêmes
proportions, et l'attente relative est du même ordre. À cinq ans la
moyenne des aéroports sans bus est tirée par quelques gares (19
aéroports, médiane 0,32 contre moyenne 1,40). Rien ici ne montre que le
rabattement remplit les avions. Le profit affiché des avions est grand
dans les deux cas ; il mélange le billet entier et la part déjà inscrite
sur le bus.

Gares rail, même règle, cargo `"0"`, endpoints dont la ligne a une
capacité passagers (le fret sans ce cargo sort du dénominateur) :

| Rail, pic < 1 véhicule | Comparables | Part |
|---|---:|---:|
| Opex, ventil référence 1974 | 42/46 | 0,913 |
| AAA, ventil référence 1974 | 57/65 | 0,877 |
| Opex, v172 ref 1972 | 136/156 | 0,872 |
| AAA, v172 ref 1972 | 81/93 | 0,871 |

L'attente moyenne par partie est d'environ 13 passagers pour ~40 sièges
par véhicule chez Opex à cinq ans, et d'environ 22 pour ~46 sièges à
trois ans. Les gares passagers d'Opex ne sont pas, sur ce pic, saturées
à un convoi. Beaucoup d'endpoints rail n'entrent pas dans le compte
(118 gares listées contre 46 comparables à cinq ans) : pas de capacité
passagers sur la ligne.

## 3. Opex : captage ou capacité

Sur les mêmes instantanés de référence, **aucune** ligne route d'Opex ne
partage un StationID avec une ligne air ou rail (part proxy 0, y compris
les 40 parties de v172 et les 9 de v163_off). Les quelques bus (moyenne
2,6 à 4,6 selon l'horizon) sont des lignes autonomes. Leur profit de
l'année précédente est de quelques milliers de livres (ventil : moyenne
3 906 £ ; v172 : 4 935 £).

Aéroports Opex, pic d'attente passagers contre un avion :

| Bras référence | Aéroports comparables | Pic < 1 avion | Attente pic moyenne | Sièges / avion | Attente / siège | Note moyenne |
|---|---:|---:|---:|---:|---:|---:|
| ventil, 1974, 10 graines | 243/243 | 1,000 | 7,9 | 234 | 0,033 | 149,5 |
| v172 ref, 1972, 40 graines | 1 366/1 366 | 1,000 | 10,9 | 232,5 | 0,047 | 134,2 |
| v163_off, 1975, 9 graines | 346/346 | 1,000 | 6,5 | 238 | 0,028 | 149,4 |

La note de gare (0–255) est moyenne, pas effondrée : le cargo a été noté.
Le stock n'atteint jamais, sur ce pic, la capacité d'un avion. Deux
lectures restent ouvertes, et les extraits ne les séparent pas :

- le captage est mince : les avions partent avec des sièges vides ;
- la cadence vide un filet continu : le pic reste bas **et** les sièges
  se remplissent.

La part des aéroports où un rabattement **pourrait** trouver des sièges
vides est donc, sur ce proxy, **tous les aéroports comparables** (1 366/1 366
à trois ans, 243/243 à cinq ans). C'est un plafond de candidats, pas une
mesure de sièges vides. Aucune de ces campagnes n'a été lancée avec une
conservation de sauvegarde exploitable pour le chargement.

### Campagne à lancer, non lancée ici

Duel de référence seul, sans variante, télémétrie de ligne annuelle, et
sauvegardes gardées pour un décodeur ultérieur de `cargo.packets`,
`cargo_cap` et `current_order.flags` (présents dans
`sweeps/fixtures/c66_control_fixture_15_3.json` ; la somme des paquets
n'a pas été vérifiée comme chargement courant) :

```text
python -X utf8 sweeps/run_c66_reference.py \
  --campaign v242_ref_telemetry_20x10 \
  --years 10 \
  --line-telemetry \
  --retain-savegames results/v242_ref_saves_20261018
```

Sans `--variant`, le lanceur ne demande pas de seuil. Sans `--seeds`,
`bench_1v1_5y_20seeds.py` prend les 20 graines de la règle `signs20`.
Le profil CPU/RAM reste celui du §3 d'`AGENTS.md` selon l'hôte. Même
avec `--line-telemetry`, le JSON ne contiendra ni sièges vides ni
`OF_TRANSFER` : seul le dossier de sauvegardes le permet. Cette commande
n'a pas été exécutée.

## 4. Critère de pose, sans priver les avions

V139 a échoué en porte A sur `v139_porteA_40x5_20261009_r1` :
`fail_primary`, profit ON−OFF **−154,3 k£/an** (médiane −181,0), V/D/E
6/34/0, Wilcoxon p = 7,88×10⁻⁷, IC95 bootstrap [−203,6 ; −104,2] k£,
valeur −3,90 %. Les bus Opex passent de 2,3 à 28,3 et les avions de
91,9 à 79,1 (`docs/taches.md`, ligne V139). V139b
(`fail_primary_and_value_guard`, −132,9 k£/an, valeur −5,148 %) fait
passer les avions de 91,40 à 71,33 alors que les véhicules route restent
à 1,95→2,15. V139c (`fail_primary`, −62,4 k£/an) : avions 91,08→76,90,
route 1,80→3,15. V139d, calcul seul sans poser de bus : **−48,8 k£/an**,
**−17,75 avions** et **+716 k£ de trésorerie**. Le scan et
l'ordonnancement suffisent à manger le créneau de construction, même
quand peu de bus sont achetés.

Le portefeuille courant explique le mécanisme de caisse.
`projects_selection.nut` n'admet un projet que si
`OpexProjectFinanceCapital` tient dans le budget, puis le classe par
ratio. Le commentaire des lignes 703-716 rappelle qu'un ratio seul
favorise les petits projets bon marché et laisse les gros avions hors
du cycle (`maxBatch = 1`). Un bus dont le ROI est gonflé par le billet
d'avion gagne ce cycle. C'est ce qu'il ne faut pas refaire.

Critère, sans effectif, sans année et sans seuil de population :

1. La ligne aérienne ou ferroviaire parente existe déjà. Le bus ne
   précède pas l'avion.
2. La valeur est le revenu **marginal de compagnie** : le nombre de
   places que l'avion peut encore vendre (sièges vides mesurés sur
   `cargo_cap` et le chargement réel, pas le pic d'attente) multiplié
   par le tarif origine → destination finale
   (`AICargo.GetCargoIncome` sur la distance et le temps du trajet
   complet), plafonné par ce que le bus peut réellement amener, moins
   le coût de marche du bus et l'immobilisation de son capital. La
   caisse n'encaisse ce tarif qu'une fois, à la livraison de l'avion.
   On n'inscrit pas ce tarif au ROI du bus, et on ne soustrait pas une
   seconde fois les 75 % de `feeder_payment_share` : ils ne sont qu'un
   partage d'affichage.
3. La caisse du bus est le résidu après avoir réservé le capital du
   meilleur projet aérien déjà finançable. Le feeder n'entre pas dans
   la liste `affordable` triée par ratio. S'il n'y a pas de résidu, on
   ne pose rien.
4. Le scan qui mesure les sièges vides doit rester assez court pour ne
   pas décaler le cycle de construction. V139d montre qu'un calcul seul
   réduit déjà la flotte aérienne.
5. On ne retire pas le bus parce que son propre `GetProfitLastYear` est
   négatif : ce profit est la part de tronçon. On juge le profit de
   l'avion parent, en argent de compagnie.

À copier d'AAA : poser la parente d'abord, ne pas juger le bus sur son
propre livre, n'ajouter un bus que si la parente a encore de la place.
À ne pas copier : les seuils 1 300 / 3 000 / 6 000 habitants, la division
par 3 de `GetLeftCapacity`, le premier bus inconditionnel, le tarif du
trajet entier dans l'estimation du bus, et les 8 prix de bus imputés à
la parente.

Tant que les sièges vides ne sont pas lus sur une sauvegarde, le critère
ne peut pas être chiffré. Le proxy « pic < un avion » désigne toute la
flotte aérienne d'Opex comme candidate, ce qui est exactement la porte
ouverte par laquelle V139 a acheté des bus à la place d'avions.

Contrôle : `PYTHONPATH=sweeps python3 -m unittest discover -s sweeps -p "test_*.py"`
— 1 937 tests, 3 ignorés, échec 0 (18/10). Les 13 tests de
`sweeps/test_v242_feeder_diag.py` couvrent le dernier instantané, la
séparation des duels AAA par `duel_policy_id`, le proxy d'arrêt joint et
le pic d'attente.
