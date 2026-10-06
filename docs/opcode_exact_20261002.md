# Opcodes exacts sous C121 — 2 octobre 2026

Chantier du worktree `codex/opcode-exact-c121` (base `52ab555`), intégré sur
`c121-catalog` (`1c20c56`). **Mise à jour du 2 octobre : `exp_opcode_exact` passe
à 1 par défaut** après un 20×10 duel neutre au sens de la règle opcodes
(§ [Qualification 20×10](#qualification-20×10-et-défaut)) ; `exp_opcode_exact_check`
reste à 0. Les sections suivantes décrivent le chantier tel que livré, avant cette
qualification.

`exp_opcode_exact=1` exécute les chemins neufs. `exp_opcode_exact_check=1`
exécute l'ancien et le neuf sur les mêmes entrées, **rend le résultat ancien**,
et publie une fois par année close :

`OPCODE_EXACT y=<année> site=<nom> calls=<n> mismatch=<n> ops_old=<somme> ops_new=<somme>`

Les cinq premières divergences d'un site dans une partie sont des lignes
`OPCODE_EXACT_MISMATCH`. Les deux réglages sont déclarés dans `info.nut`
(lignes 79 et 87, booléens ; quatre difficultés à 0 à la livraison, à 1 pour
`exp_opcode_exact` depuis le 2 octobre), initialisés dans
`globals_pre.nut` et chargés dans `settings.nut`. À 0, chaque site lit le
booléen une fois puis exécute le corps historique.

## Mesure préalable d'un `OpexRoadPlanFor`

Source : premier appel de chaque côté, journal
`results/opcode_exact_check_3x6b_20261002.log`, lignes `OPCODE_EXACT_PLAN`.
`ops_old` est le classement historique (`OpexRoadHistoricClassify` /
`OpexRoadVoirieHistoricClassify`). Les tracés ne sont pas réécrits : une seule
passe, comptée à part (`site=road_trace`).

| Graine | Côté | Tuiles | Ville | Marche d'exclusion | Pas Manhattan | Hits | Cargo rejeté | Non plat / non constructible | Sondes | Liste | Liste proche | ops_old | ops_new |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | A | 137 | 0 | 137 | 504 | 92 | 4 | 20 | 64 | 4 | 2 | 34 895 | 23 590 |
| 100 | B | 192 | 47 | 145 | 519 | 74 | 27 | 24 | 64 | 4 | 2 | 27 827 | 25 005 |
| 100 | tracés | 2 essais, 0 arrêt touché, 2 constructibles, 2 dépôts | | | | | | | | | | 5 063 | — |
| 42 | A | 75 | 0 | 75 | 300 | 0 | 0 | 54 | 64 | 4 | 0 | 20 336 | 17 096 |
| 42 | B | 38 | 0 | 38 | 152 | 0 | 5 | 14 | 64 | 4 | 0 | 15 644 | 13 958 |
| 42 | tracés | 54 essais, 26 arrêts, 28 constructibles, 1 dépôt | | | | | | | | | | 33 772 | — |
| 999 | A | 120 | 0 | 120 | 360 | 60 | 0 | 38 | 64 | 3 | 1 | 23 034 | 21 710 |
| 999 | B | 145 | 15 | 130 | 390 | 36 | 24 | 47 | 64 | 3 | 1 | 25 665 | 22 978 |
| 999 | tracés | 72 essais, 29 arrêts, 29 constructibles, 0 dépôt | | | | | | | | | | 49 925 | — |

Ces premiers plans ont encore 3 ou 4 arrêts sur la carte : la marche
d'exclusion n'est pas encore le poste dominant, et le plafond
`ROAD_MAX_SITE_PROBES` (64) est déjà atteint. Le poste grossit avec la liste.
Agrégat historique de la graine 100 en **1974** (`OPCODE_EXACT_BREAK`, dernière
publication de l'année) : 9 plans, 17 appels de sites, 4 409 tuiles, 220 rejets
de ville, 4 189 marches d'exclusion, **129 728 pas de Manhattan**, 1 403 hits,
liste d'exclusion cumulée 629 (moyenne 37 par appel), liste proche cumulée 44
(moyenne 2,6). `ops_old` des côtés A et B : 1 393 116 + 543 883. Tracés de la
même année : 276 essais, 99 arrêts touchés, 77 constructibles, 0 dépôt,
237 044 opcodes. Le balayage des sites domine les tracés. C'est ce balayage
qui est réécrit.

Rayon `ROAD_TOWN_SEARCH_RADIUS` = 16 (`builder_road.nut:25`) : disque de
Chebyshev, chaque tuile une fois, au plus 1 089 tuiles. Manhattan maximal
depuis le centre jusqu'à un coin : `2 * 16 = 32`.

## Définition des opcodes du contrôle

Pour `road_a`, `road_b` et `road_voirie`, les deux classements d'une tuile sont
mesurés l'un après l'autre (`OpexOpsMeasureBegin` / `OpexOpsMeasureEnd`,
`budget.nut:19`). La liste rendue suit le classement historique. Les sondes
`AITestMode` ne sont exécutées qu'une fois ; leur coût est ajouté aux deux
sommes. La construction de la liste proche (`OpexRoadExcludeWithin`) n'est
comptée que dans `ops_new`. Le compteur `steps++` du classement historique est
dans `ops_old`. Le chemin `exp_opcode_exact=1` ne mesure pas tuile par tuile :
son coût réel est celui du classement neuf plus les sondes, sans le second
passage.

Les années publiées sont 1970–1974. Les trois parties s'arrêtent au
1975-12-01 (`last_date` du JSON), avant le seuil du 28 décembre et avant le
1er janvier 1976, donc **1975 n'a aucune ligne**. Une année sans appel d'un
site n'a pas de ligne pour ce site.

## A — planification routière

Mécanisme. Portes en une lecture : `OpexRoadSites` (`builder_road.nut:154`),
`OpexRoadPaxVoirieSites` (`builder_road.nut:484`, second anneau vers la ligne
490), `OpexRoadPlanFor` (`builder_road.nut:642`). Corps neufs :
`OpexRoadExactClassify` (`opcode_exact.nut:232`),
`OpexRoadExcludeWithin` (`opcode_exact.nut:120`),
`OpexRoadVoirieExactClassify` (`opcode_exact.nut:434`),
`OpexRoadPlanForActive` (`opcode_exact.nut:599`).

Exactitude.

- Ville : `AITile.GetClosestTown(tile) != townId`, le même appel que
  l'historique. Un ensemble `AITileList.Valuate(GetClosestTown)` a été retiré
  après le premier contrôle (voir plus bas).
- Cargo avant l'exclusion. Un échec de cargo et un arrêt trop proche sautent
  tous les deux **avant** `nCargo++`. Les tuiles acceptées ont la même valeur
  et le même drapeau `build`. L'ordre de l'anneau, le plafond de 64 sondes et
  l'insertion triée (`OpexRoadAccumulateFronts`) sont ceux du corps historique.
- Liste proche. `ROAD_BUS_STOP_MIN_DISTANCE` = 6 (`economy.nut:547`). Si
  `DistanceManhattan(centre, arrêt) >= 2 * rayon + 6`, alors toute tuile du
  disque est à une distance Manhattan d'au moins 6 : le test strict `< 6` est
  faux. On garde les arrêts à distance `< 2 * rayon + 6`, dans leur ordre
  d'origine. Le bord de carte ne fait que rétrécir le disque réellement
  balayé, donc la borne du carré complet reste sûre. Preuve :
  `sweeps/test_opcode_exact.py`, `test_manhattan_bound`. Le contrôle final n'a
  aucune divergence `why=excl`.
- Voirie : ville, `AIRoad.IsRoadTile`, gare ou dépôt, puis cargo, puis la liste
  proche. L'historique teste la distance avant le cargo. Une tuile rejetée
  pour les deux raisons est absente de la liste dans les deux cas ; la valeur
  n'est comparée que si la tuile est retenue. Les sondes de front ne tournent
  qu'une fois.

Contrôle final, trois graines, sommes des années publiées, `mismatch=0` :

| Site | Années-graines | Appels | ops_old | ops_new | Gain |
|---|---:|---:|---:|---:|---:|
| `road_a` | 15 | 331 | 21 913 141 | 8 239 823 | 62,4 % |
| `road_b` | 15 | 311 | 19 641 839 | 7 842 081 | 60,1 % |
| `road_voirie` | 8 | 18 | 1 130 223 | 1 002 265 | 11,3 % |

Deux années de voirie coûtent plus cher : graine 100, 1970, 96 246 → 122 164
(−26,9 %) et 1971, 119 025 → 120 860 (−1,5 %). La liste d'exclusion y est
encore courte, et le cargo est lu avant le rejet de distance. Le cumul des
huit observations reste un gain. Le chemin est conservé.

Le premier contrôle (`results/opcode_exact_check_3x6_20261002.json`) avait
`mismatch_sum=14`, toutes les lignes de détail `why=ok/town` : l'historique
acceptait la tuile, l'ensemble `Valuate` la rejetait. Ce préfiltre, et
l'ensemble voirie `Valuate(IsRoadTile)`, ont été retirés. Le second contrôle
est celui du tableau.

## B — tri des flottes aériennes

`task_air.nut:755`. Sous `AIR_ROI_ORDER`, le chemin neuf appelle
`OpexAirFleetSortPrecomputed` (`opcode_exact.nut:729`) : un couple
`{line, lineYield}` par ligne, `lineYield = OpexAirFleetYield(line)` calculé
une fois, puis `sort` avec un comparateur qui ne lit que ce champ (plus grand
rendement d'abord, 0 à égalité). Le tableau rendu est une nouvelle liste de
lignes ; aucun champ n'est écrit sur les enregistrements de `this._lines`.
Le comparateur historique a les mêmes résultats, donc le tri de Squirrel
(qsort) produit la même permutation. Le contrôle compare les `lineId` et
**renvoie le tableau ancien**.

| | Années-graines | Appels | ops_old | ops_new | Gain |
|---|---:|---:|---:|---:|---:|
| `air_fleet` | 15 | 572 | 3 298 584 | 867 098 | 73,7 % |

`mismatch=0` sur chaque année publiée. Le champ ne s'appelle pas `yield` :
c'est un mot réservé, le premier smoke a échoué à la compilation
(`expected 'IDENTIFIER'`, `results/opcode_exact_smoke_1y_20261002.json`).

## C — production de desserte

Seule `OpexAirStationCatchmentProduction` (`air_coverage.nut:243`) change dans
`air_coverage.nut`. `air_catalog_c121.nut` n'est pas touché. Le chemin neuf
(`OpexAirCatchmentSumExact`, `opcode_exact.nut:790`) construit sa propre
`AITileList_StationCoverage`, appelle
`Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0)` — les quatre arguments de
la boucle historique — et somme **toutes** les valeurs entières, y compris les
négatives. Pas de `KeepAboveValue`. La liste de l'appelant n'est pas mutée.

| | Années-graines | Appels | ops_old | ops_new | Gain |
|---|---:|---:|---:|---:|---:|
| `air_catchment` | 8 | 55 | 171 645 | 125 542 | 26,9 % |

`mismatch=0`. Le gain est stable d'une année à l'autre (26,8 à 26,9 %).

## D — arrêts joints

`OpexAirBuildJoinedStops` (`air_construction.nut:98`). Le chemin neuf
(`OpexAirJoinedCandidatesExact`, `opcode_exact.nut:845`) préfiltre le rectangle
avec `AITileList` (`IsRoadTile`, absence de gare, de dépôt et de
`IsStationTile`, production strictement positive), puis réordonne les tuiles
en x extérieur / y intérieur avant le `sort` existant. Le tri Squirrel n'est
pas stable : l'ordre d'entrée des ex æquo est celui de la double boucle. Un
rectangle vide rend `[]`. En contrôle, la liste comparée est celle de
l'historique, et `BuildDriveThroughRoadStation` ne s'exécute qu'une fois, sur
cette liste.

| | Années-graines | Appels | ops_old | ops_new | Gain |
|---|---:|---:|---:|---:|---:|
| `air_joined` | 8 | 55 | 596 419 | 330 407 | 44,6 % |

`mismatch=0`.

## E — échantillonneur C117, non livré

`OpexC117AirThroughputStep` (`probes.nut:339`) reste le corps historique, sans
porte. Un cache par avion (moteur, capacité passagers, capacité courrier) a
été mesuré dans le premier contrôle : `mismatch=0`, et `ops_new` supérieur à
`ops_old` sur chaque graine.

| Graine | Années | Appels | ops_old | ops_new | Écart |
|---|---:|---:|---:|---:|---:|
| 42 | 5 | 457 | 1 132 912 | 1 281 723 | −13,1 % |
| 100 | 6 | 559 | 1 274 003 | 1 555 242 | −22,1 % |
| 999 | 6 | 533 | 1 103 632 | 1 328 989 | −20,4 % |

Source : `results/opcode_exact_check_3x6_20261002.json`. `GetCapacity` coûte
moins cher que la recherche dans la table. Le coût d'exploitation, la charge,
l'ordre et le profit n'étaient pas mis en cache. Le cache, les fonctions
`OpexC117ReadCaps` / `OpexC117AirThroughputStepActive` et la globale
`C117_AIR_CAP_CACHE` ont été retirés. Le second contrôle ne republie pas ce
site.

## Contrôle final, détail par année

Dernière publication de chaque `(graine, année, site)`. Toutes les lignes ont
`mismatch=0`. Fichier :
`results/opcode_exact_check_3x6b_20261002.json`.

| Graine | Année | Site | Appels | ops_old | ops_new | Gain |
|---:|---:|---|---:|---:|---:|---:|
| 42 | 1970 | air_catchment | 6 | 18 621 | 13 620 | 26,9 % |
| 42 | 1971 | air_catchment | 12 | 38 034 | 27 816 | 26,9 % |
| 42 | 1973 | air_catchment | 2 | 6 131 | 4 484 | 26,9 % |
| 42 | 1970 | air_fleet | 35 | 6 356 | 4 159 | 34,6 % |
| 42 | 1971 | air_fleet | 41 | 52 106 | 17 672 | 66,1 % |
| 42 | 1972 | air_fleet | 21 | 80 910 | 23 229 | 71,3 % |
| 42 | 1973 | air_fleet | 16 | 90 574 | 24 983 | 72,4 % |
| 42 | 1974 | air_fleet | 46 | 459 188 | 117 403 | 74,4 % |
| 42 | 1970 | air_joined | 6 | 68 043 | 45 344 | 33,4 % |
| 42 | 1971 | air_joined | 12 | 126 421 | 61 541 | 51,3 % |
| 42 | 1973 | air_joined | 2 | 22 795 | 13 828 | 39,3 % |
| 42 | 1970 | road_a | 32 | 952 646 | 680 250 | 28,6 % |
| 42 | 1971 | road_a | 31 | 2 456 011 | 909 620 | 63,0 % |
| 42 | 1972 | road_a | 30 | 2 432 886 | 809 374 | 66,7 % |
| 42 | 1973 | road_a | 22 | 2 617 364 | 691 647 | 73,6 % |
| 42 | 1974 | road_a | 18 | 1 859 063 | 556 241 | 70,1 % |
| 42 | 1970 | road_b | 32 | 885 218 | 639 057 | 27,8 % |
| 42 | 1971 | road_b | 31 | 2 712 054 | 993 333 | 63,4 % |
| 42 | 1972 | road_b | 30 | 2 390 962 | 784 218 | 67,2 % |
| 42 | 1973 | road_b | 21 | 2 378 479 | 699 414 | 70,6 % |
| 42 | 1974 | road_b | 17 | 1 483 895 | 436 181 | 70,6 % |
| 42 | 1971 | road_voirie | 2 | 138 477 | 105 702 | 23,7 % |
| 42 | 1972 | road_voirie | 2 | 107 860 | 99 447 | 7,8 % |
| 100 | 1970 | air_catchment | 8 | 25 488 | 18 640 | 26,9 % |
| 100 | 1971 | air_catchment | 7 | 21 697 | 15 870 | 26,9 % |
| 100 | 1970 | air_fleet | 35 | 13 826 | 6 726 | 51,4 % |
| 100 | 1971 | air_fleet | 47 | 85 935 | 27 778 | 67,7 % |
| 100 | 1972 | air_fleet | 54 | 253 321 | 70 816 | 72,0 % |
| 100 | 1973 | air_fleet | 34 | 330 786 | 85 310 | 74,2 % |
| 100 | 1974 | air_fleet | 37 | 597 734 | 147 738 | 75,3 % |
| 100 | 1970 | air_joined | 8 | 86 107 | 46 104 | 46,5 % |
| 100 | 1971 | air_joined | 7 | 77 299 | 44 323 | 42,7 % |
| 100 | 1970 | road_a | 16 | 1 225 602 | 543 778 | 55,6 % |
| 100 | 1971 | road_a | 19 | 1 103 883 | 479 164 | 56,6 % |
| 100 | 1972 | road_a | 27 | 1 945 948 | 652 354 | 66,5 % |
| 100 | 1973 | road_a | 17 | 1 112 700 | 392 593 | 64,7 % |
| 100 | 1974 | road_a | 9 | 1 393 116 | 349 311 | 74,9 % |
| 100 | 1970 | road_b | 16 | 947 774 | 460 974 | 51,4 % |
| 100 | 1971 | road_b | 18 | 1 136 062 | 495 649 | 56,4 % |
| 100 | 1972 | road_b | 25 | 1 758 898 | 725 948 | 58,7 % |
| 100 | 1973 | road_b | 13 | 840 313 | 294 866 | 64,9 % |
| 100 | 1974 | road_b | 8 | 543 883 | 203 555 | 62,6 % |
| 100 | 1970 | road_voirie | 2 | 96 246 | 122 164 | −26,9 % |
| 100 | 1971 | road_voirie | 2 | 119 025 | 120 860 | −1,5 % |
| 100 | 1972 | road_voirie | 4 | 258 839 | 219 887 | 15,0 % |
| 100 | 1974 | road_voirie | 2 | 137 088 | 123 694 | 9,8 % |
| 999 | 1970 | air_catchment | 4 | 12 843 | 9 392 | 26,9 % |
| 999 | 1971 | air_catchment | 10 | 30 507 | 22 316 | 26,8 % |
| 999 | 1972 | air_catchment | 6 | 18 324 | 13 404 | 26,9 % |
| 999 | 1970 | air_fleet | 29 | 4 319 | 3 238 | 25,0 % |
| 999 | 1971 | air_fleet | 44 | 30 367 | 12 256 | 59,6 % |
| 999 | 1972 | air_fleet | 38 | 109 754 | 32 567 | 70,3 % |
| 999 | 1973 | air_fleet | 38 | 262 277 | 70 168 | 73,2 % |
| 999 | 1974 | air_fleet | 57 | 921 131 | 223 055 | 75,8 % |
| 999 | 1970 | air_joined | 4 | 43 932 | 28 346 | 35,5 % |
| 999 | 1971 | air_joined | 10 | 107 771 | 60 297 | 44,1 % |
| 999 | 1972 | air_joined | 6 | 64 051 | 30 624 | 52,2 % |
| 999 | 1970 | road_a | 29 | 672 687 | 499 763 | 25,7 % |
| 999 | 1971 | road_a | 15 | 540 290 | 302 347 | 44,0 % |
| 999 | 1972 | road_a | 33 | 1 603 546 | 691 198 | 56,9 % |
| 999 | 1973 | road_a | 17 | 799 816 | 337 262 | 57,8 % |
| 999 | 1974 | road_a | 16 | 1 197 583 | 344 921 | 71,2 % |
| 999 | 1970 | road_b | 29 | 680 658 | 557 380 | 18,1 % |
| 999 | 1971 | road_b | 13 | 575 117 | 314 587 | 45,3 % |
| 999 | 1972 | road_b | 30 | 1 630 147 | 651 914 | 60,0 % |
| 999 | 1973 | road_b | 16 | 859 346 | 316 721 | 63,1 % |
| 999 | 1974 | road_b | 12 | 819 033 | 268 284 | 67,2 % |
| 999 | 1970 | road_voirie | 2 | 110 829 | 102 986 | 7,1 % |
| 999 | 1972 | road_voirie | 2 | 161 859 | 107 525 | 33,6 % |

Somme de ces lignes : 46 751 851 → 18 407 216 opcodes, soit 60,6 % sur les
sites mesurés. Ce total n'inclut pas les tracés (inchangés) ni 1975.

Les trois parties du contrôle final sont saines : `run_ok=true`,
`failure_reason=null`, `script_error_hits=0`, `opcode_exact_mismatch_sum=0`.

## Commandes

Tests, depuis le worktree, après le retrait du préfiltre de ville et du cache
C117 :

`python3 -m unittest discover -s sweeps -p "test_*.py"`

1 143 tests, OK, 1 skip préexistant : `sweeps/test_b9_air_catchment.py`,
`harnais indisponible hors Docker : No module named 'openttdlab'`.

Smoke, bras
`OpexAI[c121_air_economics=1,c121_catalog_incremental=1,exp_opcode_exact=1]`,
graine 42, 1 an. Limites `--network host --cpus=3 --memory=2g --memory-swap=2g`,
montage du worktree sur `/work`.

- `results/opcode_exact_smoke_1y_20261002.json` : échec de compilation, champ
  `yield` (mot réservé). Corrigé en `lineYield` avant les parties suivantes.
- `results/opcode_exact_smoke_1y42_20261002.json` : OK, encore avec le
  préfiltre de ville ensuite retiré. Journal `/tmp/opcode_exact_logs/smoke_1y42.log`.
- `results/opcode_exact_smoke_1y42b_20261002.json` : OK sur le code livré.
  `run_ok=true`, `failure_reason=null`, `status=OK`, valeur 122 885, aucune
  chaîne « made an error ». Journal `/tmp/opcode_exact_logs/smoke_1y42b.log`.

Contrôle, bras `...exp_opcode_exact_check=1`, graines 42 100 999, 6 ans,
`sweeps/diag_opcode_exact.py` (`-d script=4`).

- `results/opcode_exact_check_3x6_20261002.json` et `.log` : `mismatch_sum=14`,
  `script_error_hits=0`, 14 détails `why=ok/town`. Code retiré ensuite.
  Journal `/tmp/opcode_exact_logs/check_3x6.log` (`EXIT:1`).
- `results/opcode_exact_check_3x6b_20261002.json` et `.log` : `rows=3`,
  `mismatch_sum=0`, `script_error_hits=0`. Journal
  `/tmp/opcode_exact_logs/check_3x6b.log` (`EXIT:0`).

`docker ps` ne montrait aucun conteneur `openttd-lab` avant chaque lancement.
Aucun `openttd` direct. Aucun commit.

## Limites

Le contrôle prouve l'égalité des sorties sur ces trois parties, pas sur toute
entrée théorique. La borne de Manhattan est prouvée pour le disque complet ;
elle n'a pas divergé dans le moteur. Le mode contrôle allonge les plans et
peut décaler la trajectoire solo par rapport à `exp_opcode_exact=1` : le
critère exigé est `mismatch=0` à l'intérieur du contrôle. La neutralité
économique du §4 (20 graines × 10 ans) n'est pas mesurée. Les défauts restent
à 0.

## Qualification 20×10 et défaut

Règle appliquée : optimisation d'opcodes (`AGENTS.md` §4, décision du 24/09),
fixée avant le banc : métrique `profit_year`, effet utile minimal 0, garde de
valeur −5 %. Gain d'opcodes : contrôle `mismatch=0` ci-dessus (route −62 % et
−60 %, voirie −11 %).

**Premier 20×10 (`opcode_exact_c121_20x10_20261002`, worktree) : incomplet.**
Graine 314, bras variante : arrêt du script par « This script took too long to
Save » (`Save()` plafonné à 100 k opcodes ; chaque ligne y était projetée champ
par champ). `Save()` ne dépend pas de `exp_opcode_exact` : le défaut est latent
dans les deux bras dès que le portefeuille est grand. Diagnostics :
`diag_opcode_exact_crash_s314_20261002*`.

**Correctif `910bb68`** (`persist.nut`, `main.nut`) : la projection d'une ligne
est factorisée dans `OpexSaveProjectLine` (même liste d'exclusion
`OPEX_SAVE_LINE_SKIP`, mêmes conversions) ; à partir de
`SAVE_PROJECTION_MIN_LINES` = 64 lignes, la boucle principale rafraîchit une
fois par mois un cache de projections, que `Save()` relit ; une ligne absente du
cache est projetée dans `Save()` comme avant. Sous 64 lignes, chemin inchangé.
Vérifié sur la graine 314 (`diag_opcode_exact_savefix_s314_20261002`, partie
complète) et par deux allers-retours `sweeps/save_load_roundtrip.py`, dont un
rechargement en 1979 avec 96 lignes, cache exercé
(`save_load_savefix_s314_late_20261002.json`). Les tests de contrat de `Save()`
(`test_b3_road_fleet_targets.py`, `test_c121_air_economics.py`) ont été
alignés sur cette structure.

**Banc d'adoption (`results/opcode_exact_savefix_c121_20x10_20261002.*`)** :
code `910bb68` (arbre sale seulement par des fichiers non suivis hors IA), image
`openttd-lab:venv-20261001` (`sha256:5af51ac5…`), 3 CPU, 2 Go sans swap,
3 workers. Duel C66.4 contre AAAHogEx-115, 20 graines × 10 ans, deux bras
C121 (`c121_air_economics=1,c121_catalog_incremental=1`), `exp_opcode_exact`
0 contre 1.

- Couverture : 20/20 paires complètes, `failed_runs=[]`, verdict du harnais
  `pass`.
- `profit_year` (variante − référence) : moyenne **+74 039 £/an**, médiane
  +82 974 ; **15 victoires / 5 défaites**, test des signes p = 0,041 ;
  IC95 (t) [−114 850 ; +262 928].
- `company_value` : ratio des moyennes **+6,76 %** (12/8) ; garde −5 % tenue.
- `performance_history` : +14,05 en moyenne (11/9).

Lecture : aucune perte (IC95 non entièrement négatif, majorité de victoires,
garde tenue) ; la règle opcodes est satisfaite. Le +74 k£/an n'est pas
présenté comme un gain établi : l'IC95 contient 0 et le duel n'est pas
déterministe.

**Défaut : `exp_opcode_exact=1`** (`info.nut`, quatre difficultés). Smoke 1×1
au défaut : `results/smoke_opcode_exact_default_1y42_20261002.json`, OK, le
harnais résout `exp_opcode_exact=1`. Suite Python : 1 143 tests, OK, 1 skip.

**Contrôle au défaut C115 (`results/opcode_exact_default_c115_20x10_20261002.*`)** :
les deux bras de ce premier banc portaient C121, qui n'est pas le défaut de la
branche. Même protocole et mêmes graines, bras `OpexAI[exp_opcode_exact=0]`
contre `OpexAI[exp_opcode_exact=1]` au défaut livré (C115=1, C121=0) ; code
`020c77a` (même IA que `e4312cb` après rebase), image `venv-20261001`.

- Couverture : 20/20 paires, `failed_runs=[]` ; verdict brut `fail_primary`
  (attendu : la règle signs20 cherche un gain, pas une neutralité).
- `profit_year` : moyenne **−50 299 £/an**, médiane −61 051 ; **6 victoires /
  14 défaites**, test des signes p = 0,115 ; IC95 (t) [−189 942 ; +89 343].
- `company_value` : ratio des moyennes −2,14 % (7/13) ; garde −5 % tenue.
- `performance_history` : +3,7 (12/8). Écart au duel (`profit_year`) : +10 k£
  en moyenne, médiane −81 k£ (9/11).

Lecture selon la règle opcodes : pas de perte établie (IC95 non entièrement
négatif, p ≥ 0,05, garde tenue), donc le défaut 1 reste conforme. Le sens est
toutefois défavorable sous C115 (14 défaites sur 20), à l'inverse du banc C121
(15 victoires) ; le duel n'étant pas déterministe, aucun des deux sens n'est
établi. Smoke 1×1 de l'arbre fusionné `652dac9` :
`results/smoke_merged_652dac9_1y42_20261002.json`, OK.
