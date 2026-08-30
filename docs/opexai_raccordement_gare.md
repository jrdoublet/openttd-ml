# OpexAI — raccordement à une gare existante (tranche v1)

**État au 2026-08-29 (nuit).** Le code est dans `master`, commandé par `station_join`, **défaut 0**.
Le banc vivier (`docs/bench_v2_vivier.json`) : +37,2 % de véhicules (t = 5,94), valeur nulle. Rejeu
après traction (`docs/bench_join_after_traction.json`, paire
`docs/bench_join_after_traction_paired.json`) : véhicules **+23,6 %, t = 3,50, 17/20** ; gares
**−11,9 %, t = −3,61** (réemploi) ; `company_value` +5,9 %, t = 0,96, sous le plancher. **La
construction survit, la valeur non.** `origin_sitable=0` sur les deux bras.

Le partage de bassin (`basin_share`) est mesuré et **ne paie pas**
(`docs/bench_basin_share_paired.json`) : valeur sous le plancher, véhicules nuls, gares
+12,9 % (t = 3,67) — les jointures sont déclassées, pas allégées. Défaut 0. AAAHogEx joint
autrement (groupe + spread). Idées : `docs/aaahogex_rail_join.md`. Le spread n'est pas la
suite tant que la v1 ne paie pas.

## Décision

Quand le seul obstacle est le filet physique `MIN_SEPARATION`, OpexAI peut raccorder **une** extrémité d'une nouvelle ligne rail à une gare rail OpexAI existante. Le seuil reste inchangé et l'identité d'origine (`ORIGIN_SEPARATION`) reste un rejet : une même ville ou industrie ne gagne rien à être servie deux fois.

L'API le permet : `AIRail.BuildRailStation(tile, direction, num_platforms,
platform_length, station_id)` accepte un `station_id` valide, donc un quai construit à côté du quai existant rejoint la même gare. Cette conclusion est vérifiée dans les en-têtes NoAI 15 (`script_rail.hpp` : `@pre station_id == STATION_NEW || STATION_JOIN_ADJACENT || IsValidStation(station_id)` ; `STATION_NEW = 0xFFFD` dans `script_basestation.hpp`). Le `src/` de *ce* dépôt n'est que du Python — ces en-têtes vivent dans le source OpenTTD, pas ici. L'appel transmet l'identifiant à la commande de construction. Le coût est un quai neuf de 1 x 4 plus son nettoyage éventuel, mais ni la première gare complète ni son choix de site ; surtout, une seule extrémité doit encore être cherchée et bâtie.

## Quai et voie

La tranche ajoute un **quai parallèle dédié** à celui de la ligne voisine, avec sa propre entrée de voie. Il est joint au même `StationID`, mais sa voie ne rejoint pas celle de la ligne précédente. La recherche rejette tout chemin qui toucherait un rail, un dépôt ou un quai déjà posé : il n'y a donc ni aiguillage ajouté sur la ligne ancienne, ni quai unique partagé. Les deux circulations restent physiquement indépendantes et ne reproduisent pas le blocage mesuré sur une voie unique.

Chaque pose et chaque chemin sont contrôlés par `AIRail.AreTilesConnected`, comme le dépôt. La pose est précédée d'un test (`AITestMode`) et, après un échec, le rollback ne démolit que le nouveau quai, la nouvelle gare distante, la voie et le dépôt : jamais la gare préexistante. L'API ne fournit pas un agrandissement abstrait d'une gare ; construire ce quai supplémentaire avec le même identifiant est précisément l'agrandissement disponible, au coût de la construction de la plate-forme.

## Compatibilité et sens du fret

V1 accepte seulement une gare d'une ligne **rail** OpexAI, de même `kind` et même cargo. Pour le fret, les rôles doivent coïncider : source avec source, ou puits avec puits. Joindre une source à un puits est refusé, car la gare commune pourrait accepter localement le cargo qui devait partir. Les ordres restent inchangés : `OF_FULL_LOAD_ANY` à la source, `OF_NONE` au puits. Les gares avion, dock, une autre cargaison, une seconde extrémité trop proche, et deux gares physiques distinctes autour du même candidat restent des rejets v1.

## Lecture de `_lines`

Une ligne raccordée conserve ses deux tuiles de quai propres, mais l'une retourne le même `StationID` que la ligne voisine. `_tooClose` court-circuite le filet uniquement pour cette extrémité et cette gare logique ; l'autre extrémité demeure protégée. Chaque ligne mémorise désormais les identifiants exacts de ses convois. `_reportLines` et `_scrapDeadLines` les utilisent donc au lieu de demander tous les véhicules d'une gare partagée : une ligne morte ne peut plus ni compter ni vendre les trains de sa voisine.

## Changements inconditionnels et re-baselinage

Deux contrôles de la même passe s'appliquent aussi quand `station_join=0`. Après chaque `BuildRail`, `AIRail.AreTilesConnected` vérifie le raccordement réel : une ligne auparavant déclarée construite peut donc désormais finir en `TRKFAIL`, ce qui est voulu car le succès de l'appel ne garantit pas une voie utilisable. De même, `StartStopVehicle` est reporté après toute la boucle de construction afin qu'un rollback puisse encore vendre une transaction incomplète. Ces deux protections changent le comportement de toutes les lignes, pas seulement des lignes jointes.

**Re-baseline (2026-08-30).** Ils sont dans `docs/bench_road_current.json` (20×20, défauts, route ON) : moyenne 3,13 M, emprunt 0. `docs/bench_v2.json` et `docs/opexai_plafonnement_mesure.json` restent historiques. `docs/bench_after_pbs.json` n'est **pas** ce successeur : PBS `e027037` y tombe 20/20.

## Limites reportées

Cette tranche ne construit pas de jonction générale, de double voie, ni d'extension après remplissage des deux côtés du quai initial. Elle ne joint pas deux gares existantes, ni ne réutilise un aéroport ou un dock. Ces cas exigent une géométrie de station générique et une politique de capacité, distinctes du petit chemin transactionnel validé ici. Le réglage `station_join` (défaut **0** après le banc vivier) permet d'opposer ce comportement au bras historique.

AAAHogEx joint autrement : un nouveau quai **dans le spread d'un groupe de gare**, pas un parallèle collé après `_tooClose`. Idées et méthode, sans copie : `docs/aaahogex_rail_join.md`.

## Refus (2026-08-30)

`OpexFindStationJoin` dit maintenant *pourquoi* il refuse : panneau `OB|R` (M / K / R / other),
lu par `sweeps/opex_full_campaign.py`. Cinq graines × 20 ans, `station_join=1`
(`docs/opex_join_refuse_20y_5seeds.json`) : 196 M, 75 K, **0 R**, 41 other, 705 tentatives,
39 OK, **0 JOINPATH**. Les rôles fret inverses meurent à la génération. JOINPATH est vide.
Le rendement restant est SITEA/SITEB sur un quai parallèle, pas un A\* invalidé après coup.

## Parallèle offset 1–4 (2026-08-30)

`OpexJoinPlatformPlans` ne colle plus au seul voisin : offsets 1 à 4, même orientation, même
longueur. Ce n'est pas le scan d'enveloppe. 5 graines × 20 ans
(`docs/opex_join_parallel_20y_5seeds.json` contre `docs/opex_join_refuse_20y_5seeds.json`) :
39 → 71 jointures OK (5,5 % → 15,7 %), SITE 692 → 393, JOINPATH toujours 0. Il reste 361
échecs au quai joint avec `nClear=0` — autre orientation / enveloppe, c'est-à-dire le spread,
explicitement pas la suite. 5/5 plus de véhicules, 4/5 moins de valeur. Défaut `station_join` 0.

## Population jointe (étape 0) et porte H1 (2026-08-30)

`docs/opex_join_pop.json` (même campagne parallèle, pas un nouveau run) :

| | n | dist. médiane | trains | réel/prédit (an 2) |
|---|---:|---:|---:|---:|
| neuves | 66 | **43** | 2 | 1,19 |
| jointes | 71 | **63** | 3 | 0,80 |
| jointes < 50 | 20 | 37 | 2 | **1,12** |
| jointes ≥ 100 | 7 | 109 | 4 | **0,07** |

Encore du long. H1 : `join_max_distance`, défaut **0**. À 50, rejet tooClose **sans A\***
(panneau `OB|R` champ D). 5 graines (`docs/opex_join_cap50_20y_5seeds.json`) :
jointures OK 71 → **29**, dist. 63 → **37**, D = 1035. Contre le parallèle : moins
de véhicules, plus de valeur (on arrête le vivier). Contre `join=0` (campagne
villes) : médiane valeur **plate**, 2 graines à **−30 %**. ⚠️ **Pas de banc n=20.**
Le défaut join reste 0. H2 mesuré ci-dessous, ne paie pas. Pas de spread.

## H2 — joindre au lieu (`join_place`, 2026-08-30)

Réglage propre, défaut **0**, indépendant de `station_join`. Pour chaque gare
rail OpexAI, origines **libres** dans 25–75 tuiles (cappé par
`join_max_distance` si > 0). Même `kind` / cargo / rôle fret que la v1.
L'objet join est attaché à la génération : `_tryBuild` ne repasse pas par
`_tooClose`. Quai parallèle 1–4, identifiant du primaire. `JOINPATH` inchangé
(dédié). PBS de jointure : approches voie simple, jamais l'aiguillage
(mesure H2 ci-dessous encore sur l'ancien placement).

5 graines × 20 ans, `join_place=1` seul
(`docs/opex_join_place_20y_5seeds.json`) contre `join=0`
(`docs/opex_town_growth_20y_5seeds.json`) :

| | n | dist. médiane | trains | réel/prédit (an 2) |
|---|---:|---:|---:|---:|
| neuves | 73 | 43 | 2 | 1,21 |
| H2 | **50** | **50** | 2 | **−0,16** |

| graine | valeur join=0 | H2 | delta |
|---|---:|---:|---:|
| 42 | 3,24 M | 2,00 M | −38 % |
| 100 | 2,01 M | 0,16 M | **−92 %** |
| 999 | 3,53 M | 1,17 M | −67 % |
| 4096 | 2,46 M | 0,84 M | −66 % |
| 12345 | 4,65 M | 2,42 M | −48 % |
| **médiane** | **3,24 M** | **1,17 M** | **−64 %** |

Véhicules 204 → 169. 201 tentatives de jointure, 50 OK, **0 JOINPATH**.
Le TOP_K se remplit de H2 (jusqu'à 143 classés / an cumulés) qui meurent
en SITEA au quai joint — le spread, toujours pas la suite. Les jointures
qui passent **perdent** en an 2. ⚠️ **Défaut 0. Pas de banc n=20. Pas de
spread.** Signaux (mesure H2) : 77 OK / 128 fail / 50 junc (un PBS dépôt par
jointure ; le front de quai vers la gare refuse souvent). Placement corrigé
ci-dessous.

## PBS hors aiguillage (2026-08-30)

`CmdBuildSingleSignal` refuse tout `TracksOverlap` (erreur 2050).
`OpexPlaceJoinSignals` cherche un PBS sur une voie simple : approches de
gare à 2–8 tuiles et les deux côtés du dépôt, jamais la tuile de croisement.
Un pont ou un tunnel saute l'emplacement (`SJ`) ; une commande refusée sur
une voie simple rollback (`JF`, `SIGFAIL`) avant les trains. `JOINPATH`
inchangé.

Baseline `station_join=1`, `join_max_distance=50`
(`docs/opex_station_junction_baseline_20y_5seeds.json`) : 4 jointes, 5 PBS /
11 refus. Après (`docs/opex_junction_signal_fix_20y_5seeds.json`) : 3 jointes,
**9 / 0**, 3 skip, 0 `JF`, 0 `SIGFAIL`, 0 `RX`, 0 `XC`. Ce n'est pas une
jonction de voie. ⚠️ **Défaut `station_join` 0.** Pas de spread.
