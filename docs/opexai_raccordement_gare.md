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

Deux contrôles de la même passe s'appliquent aussi quand `station_join=0`. Après chaque `BuildRail`, `AIRail.AreTilesConnected` vérifie le raccordement réel : une ligne auparavant déclarée construite peut donc désormais finir en `TRKFAIL`, ce qui est voulu car le succès de l'appel ne garantit pas une voie utilisable. De même, `StartStopVehicle` est reporté après toute la boucle de construction afin qu'un rollback puisse encore vendre une transaction incomplète. Ces deux protections changent le comportement de toutes les lignes, pas seulement des lignes jointes. Les mesures de `docs/opexai_plafonnement_mesure.json` et `docs/bench_v2.json` doivent donc être re-baselinées avant toute comparaison avec une exécution de cette version.

## Limites reportées

Cette tranche ne construit pas de jonction générale, de double voie, ni d'extension après remplissage des deux côtés du quai initial. Elle ne joint pas deux gares existantes, ni ne réutilise un aéroport ou un dock. Ces cas exigent une géométrie de station générique et une politique de capacité, distinctes du petit chemin transactionnel validé ici. Le réglage `station_join` (défaut **0** après le banc vivier) permet d'opposer ce comportement au bras historique.

AAAHogEx joint autrement : un nouveau quai **dans le spread d'un groupe de gare**, pas un parallèle collé après `_tooClose`. Idées et méthode, sans copie : `docs/aaahogex_rail_join.md`.
