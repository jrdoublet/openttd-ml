# V94 — pré-filtre natif des sites aériens

État au 2026-09-25 : **défaut 1 (décision utilisateur), 20×10 neutre**.
`30_v91_astar_pondere.md` reste la fiche V91. Ce fichier est la fiche V94.

## Contexte

`OpexAirFindSite` à froid est le poste dominant d'`OpexAirPlans` : environ 2,5 M opcodes, 93 % du planning AIR (journal du 5 septembre 2026, ordre de grandeur à remesurer sur le code courant). Le chantier V90 a montré qu'un appel API coûte presque rien en opcodes : le coût est la logique Squirrel autour. Le balayage historique parcourt, pour `r` de 4 à `AIR_SITE_RADIUS` (25), chaque tuile de la couronne `max(|dx|, |dy|) = r`, et enchaîne en Squirrel `IsValidTile`, `GetTileX` / `GetTileY`, les bornes d'emprise, `OpexAirDistanceToRect`, `IsWaterTile` / `IsCoastTile` sur l'ancre et sur le coin opposé, `GetClosestTown` si un slot est exigé, puis `AIAirport.GetNearestTown`.

## Réglages

| Réglage | Défaut | Rôle |
|---|---|---|
| `v94_air_site_list` | 0 | 1 : la recherche froide passe par `AITileList`. 0 : le balayage historique, inchangé tuile par tuile. |
| `v94_air_site_check` | 0 | 1 : les deux recherches tournent sur la même entrée. L'ancien scan décide (ancre, sondes, écriture de `AIR_SITE_CACHE`). Une ligne `V94_CHECK OK` ou `V94_CHECK DIFF` est émise par `AILog.Info`. |

Les deux sont des booléens `AICONFIG_BOOLEAN`, déclarés dans `info.nut` et chargés dans `OpexLoadSettings`. Tant que le check vaut 1, `v94_air_site_list` ne change pas la décision : la référence reste l'ancien scan. Le chemin de cache (lecture, invalidation, réécriture de l'ancre ou de `null`) est le code historique, partagé, et n'est pas rejoué.

## Conception

Le balayage historique s'arrête au premier site valable, souvent à petit `r`. Construire d'abord tout le carré 51×51, une table Squirrel par survivant et un tri Squirrel du reliquat entier coûterait plus cher que cette sortie précoce. `OpexAirFindSiteListed` avance donc anneau par anneau. Dès qu'un `return` historique part (site trouvé, quota, limite de gares), les rayons suivants ne sont pas construits.

Pour chaque `r` de 4 à `AIR_SITE_RADIUS` :

1. `AddRectangle` du carré `[ville ± r]`, coupé à la carte et à l'emprise (`ax + largeur − 1 < mapX`, de même en Y). `RemoveRectangle` retire le carré `[ville ± (r − 1)]` avec le même clamp. C'est l'anneau `max(|dx|, |dy|) = r`, équivalent à `Valuate(AIMap.DistanceMax, town.tile)` puis `KeepValue(r)`, sans valuer l'intérieur du carré.
2. Filtres natifs sur cet anneau seul.
3. `Valuate(AIMap.GetTileX)` puis `Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING)`.
4. Passe Squirrel sur cette liste, et sortie au premier `return`.

Aucune table Squirrel par ancre, aucun comparateur Squirrel.

### Passés en natif (`Valuate` / `KeepValue` / `Sort`, pas une closure Squirrel)

Signatures relues sur l'API NoAI 15 (`AITile`, `AIAirport`, `AIMap`, `AIList`) :

| Appel | Signature | Rôle |
|---|---|---|
| `AITile.IsWaterTile` | `(tuile) -> bool` | `KeepValue(0)`. Un booléen vaut 0 ou 1 dans `Valuate`. |
| `AITile.IsCoastTile` | `(tuile) -> bool` | `KeepValue(0)`. La côte n'est pas une tuile d'eau. |
| `AITile.GetClosestTown` | `(tuile) -> TownID` | seulement si `requiredSlotTownId >= 0`, `KeepValue(requiredSlotTownId)`. |
| `AIAirport.GetNearestTown` | `(tuile, type) -> TownID` | `Valuate(..., airport.type)` puis `KeepValue(town.id)`. |
| `AIMap.GetTileX` | `(tuile) -> int` | valeur de tri, puis `Sort` ascendant. |

`AddRectangle` n'ajoute que des tuiles valides : les préconditions `IsValidTile` de ces valuateurs sont tenues. `GetNearestTown` renvoie un TownID invalide, sans erreur script, si le type ou l'emprise est inutilisable : `KeepValue` retire alors la tuile, comme la comparaison historique.

La validité de la tuile et les bornes d'emprise sont le rectangle clampé. `OpexAirDistanceToRect` n'a pas d'équivalent API. `AIMap.DistanceManhattan` mesure deux tuiles ; un seuil de 25 retirerait des ancres dont l'emprise reste à 25 ou moins de la ville.

### Restés dans la passe Squirrel, sur l'anneau déjà ordonné

Dans cet ordre, avant le test `used >= allowance` / `probes.left` :

1. `OpexAirDistanceToRect(town.tile, anchor, w, h) > 25`
2. eau ou côte du coin opposé `anchor + GetTileIndex(largeur − 1, hauteur − 1)`
3. `OpexAirFootprintCheapOk` si `AIR_CHEAP_SITE` (le compteur `probes.cheapSkip` est incrémenté ici), sinon le rejet de pente `maxH − minH >= 2`

Puis le même bloc de sondes `AITestMode` / `BuildAirport` / `execLevels` / cache que le balayage historique. `AIR_CHEAP_SITE` faux garde le terrassement de test dans ce bloc.

## Équivalence d'ordre

La boucle historique, à `r` fixé, visite `dx` de `−r` à `r` puis, pour chaque `dx`, `dy` de `−r` à `r` en ne gardant que la couronne. C'est l'ordre `(dx, dy)`.

`Sort(SORT_BY_VALUE, SORT_ASCENDING)` après `GetTileX` parcourt le set de `ScriptList`, ordonné par la paire `(valeur, index de tuile)`. La valeur est X. À X égal, l'index croissant est Y croissant, parce que l'index OpenTTD vaut `y * mapX + x`. Dans l'anneau géométrique, `(X, Y)` est `(dx, dy)`. Le tri par défaut d'une `AIList` est descendant (`catalog.nut`) : l'appel `Sort` ascendant est nécessaire, sinon la colonne serait lue de Y décroissant.

`sweeps/test_v94_air_site_list.py` compare, anneau par anneau, cet ordre `(X, index)` à la boucle `(dx, dy)`, puis la concaténation des anneaux après le filtre de distance.

Les filtres déplacés sont purs : lecture de tuile, pas de `AITestMode`, pas d'écriture de `probes`, pas d'erreur script posée par le source 15.3. `used >= allowance` et `probes.left` ne sont testés qu'après eux. Les retirer d'avance ne change ni l'ancre, ni `used`, ni `probes.left`, ni `allowance`, ni `execLevels`, ni `cheapSkip`, ni `tested`, ni `stationLimitedTowns`, tant que la carte ne change pas pendant le scan.

`town.tile + GetTileIndex(dx, dy)` peut, au bord, tomber sur une tuile valide de la rangée voisine (débordement de X). Cette tuile n'est pas dans le rectangle clampé. Le test statique, jusqu'à 12×8 et 9×11 sur des cartes 64 et 256 (l'intercontinental vanilla d'OpenTTD 15.3 fait 9×11, `airport_defaults.h`), ne trouve aucun débordement qui passe `OpexAirDistanceToRect`. La distance minimale de ce débordement vaut `mapX − 24 − largeur` : elle reste supérieure à 25 tant que la largeur est inférieure à `mapX − 49`. À partir de cette largeur (15 sur une carte 64), un débordement peut atteindre la sonde. `test_wide_footprint_can_keep_a_wrapped_anchor` le montre pour 20×1. `V94_CHECK` le signalerait par un `DIFF` d'ancre.

## Mode check

`v94_air_site_check = 1` copie `probes` (y compris `stationLimitedTowns`) avant l'ancien scan. L'ancien scan tourne sur les vrais compteurs et écrit `AIR_SITE_CACHE` comme aujourd'hui. La liste tourne ensuite sur la copie, avec écriture de cache désactivée. La trace compare l'ancre, `used`, `probes.left`, `tested`, `cheapSkip`, `execLevels`, `allowance`, `townsLeft` et le drapeau de limite de gares de la ville :

```
V94_CHECK OK town=12 anchor=100/100 used=2/2 left=1490/1490 tested=2/2 cheap=30/30 exec=0/0 allow=75/75 lim=0/0
```

`anchor=-1` signifie aucune ancre. Le mode check ne remplace pas la décision. Il ajoute un second scan en mode test : le coût `ops_sites` n'est pas comparable tant que le check est armé, et `AIError.GetLastError()` en sortie de fonction peut être celui du second scan. Un `DIFF` isolé après une suspension NoAI peut venir d'un changement de carte entre les deux passages ; un `DIFF` répété sur la même ville, carte stable, est un écart d'algorithme.

Le hit de cache n'est pas doublé : les deux modes partagent ce chemin.

## Instrumentation

Aucun compteur nouveau. `OpexAirPlansFindSites` et `OpexAirPlansDiscoverHubs` entourent déjà `OpexAirFindSite` avec `AIController.GetTick` / `GetOpsTillSuspend`. `OpexAirCalcDeltaOps` est la même formule que `OpexOpsMeasureEnd`. Le cumul est `perfOpsSites`, publié par `AILog.Info` dans `AIR_PLAN_PERF` (`ops_sites=`) et, si `decision_log=1`, par `OpexDecide("AIR_PLAN_PERF", ...)`. Le gain de V94 se lit en comparant ce champ, check désactivé, `v94_air_site_list=0` contre `1`.

Le coût en opcodes d'un élément de `Valuate` n'est pas connu sur cette machine : les sources OpenTTD n'y sont pas. Il sera lu par `ops_sites`, pas estimé. Un anneau qui ne trouve pas de site paie ses `Valuate` en entier ; les anneaux suivants ne sont construits qu'après cet échec.

## Protocole de mesure (non exécuté)

Règle d'adoption des optimisations d'opcodes (AGENTS.md §4) : gain mesuré sur `ops_sites`, puis duel 20×10 apparié complet et sain sans perte. L'IC95 du delta `profit_year` ne doit pas être entièrement négatif, le test des signes ne doit pas être une défaite significative (p ≥ 0,05 ou majorité de victoires), et la garde de valeur −5 % doit tenir. Le seuil d'effet utile +50 k£/an et 15/20 ne s'applique pas.

Limites Docker du VPS : `--cpus=3 --memory=2g --memory-swap=2g`, `-v openttd-lab-home:/home/lab`, `--max-workers 3`.

1. Smoke 1 graine × 1 an, `v94_air_site_list=1`, `v94_air_site_check=0`, compilation et partie saine.

```bash
docker run --rm --cpus=3 --memory=2g --memory-swap=2g \
  -v openttd-lab-home:/home/lab -v "$PWD":/work -w /work openttd-lab \
  python3 sweeps/bench_v2.py --arms "OpexAI[v94_air_site_list=1]" \
  --seeds 42 --years 1 --max-workers 3 \
  --out results/smoke_v94_air_site_list.json
```

2. Solo avec `v94_air_site_check=1` (la liste est comparée même si `v94_air_site_list` reste 0). Zéro ligne `V94_CHECK DIFF`. La trace est un `AILog.Info` : elle n'apparaît qu'avec `-d script=4` (les lignes `[I]` ; `sweeps/save_load_roundtrip.py` le rappelle). `bench_v2.py` ne passe pas ce flag. Les diagnostics qui l'injectent (`sweeps/diag_c60_town_rating_exposure.py`, `sweeps/save_load_roundtrip.py`) montrent le motif.

3. Même graine, même horizon : deux solos `v94_air_site_list=0` et `=1`, check à 0, et comparer `ops_sites` dans `AIR_PLAN_PERF`. C'est la mesure du coût réel de `Valuate`. Le gain suppose que le premier site arrive avant d'avoir valué beaucoup d'anneaux, et que les filtres natifs réduisent ce qui reste à l'emprise Squirrel.

4. Duel apparié 20×10, métrique `profit_year`, garde de valeur 5 %, règle de neutralité ci-dessus :

```bash
python3 sweeps/run_c66_reference.py \
  --campaign v94_air_site_list_20x10 \
  --years 10 \
  --reference "OpexAI" \
  --variant "OpexAI[v94_air_site_list=1]" \
  --variant-policy-id "v94_air_site_list" \
  --primary-metric "profit_year" \
  --min-useful-primary-delta 50000 \
  --value-guard-max-loss-pct 5.0 \
  --max-workers 3
```

`--min-useful-primary-delta` reste requis par le harnais. Pour cette adoption, un verdict `fail_primary` au seuil +50 k£ n'est pas un rejet : lire l'IC95, le test des signes et la garde de valeur. Ne pas lancer ce duel avant le zéro `DIFF` et un `ops_sites` en baisse.

## Hors périmètre

`OpexRailOriginSitable`, `OpexStationPlans`, `OpexRoadSites`, `OpexAirBuildJoinedStops`, `OpexWaterFindSite`, les BFS eau et route, l'A* rail, `spatial.nut`, `terrain_map.nut`.

## Mesure (2026-09-24, solo, graines 42 et 100 × 3 ans, `decision_log=1`)

Harnais `sweeps/diag_c69_bottleneck_probe.py` (`-d script=4`), fichiers `results/v94_check*.json[l]`
et `results/v94_perf_{0,1}.json[l]` de ce worktree (non versionnés).

- **Équivalence** (`v94_air_site_check=1`) : 84 `V94_CHECK OK`, 0 `DIFF`. Limite : les 84 cas ont
  tous trouvé un site ; le chemin « aucun site / allowance épuisée » n'a pas été exercé.
- **Opcodes** (`v94_air_site_list=0` contre `1`, check à 0) :

| Graine | Bras | `ops_sites` | sondes | ops/sonde | `total_ops` planning AIR |
|---|---|---|---|---|---|
| 42 | 0 | 5 973 004 | 1 054 | 5 667 | 111 870 618 |
| 42 | 1 | 5 406 818 | 1 134 | 4 768 (−16 %) | 112 409 952 |
| 100 | 0 | 6 835 872 | 1 034 | 6 611 | 81 741 754 |
| 100 | 1 | 5 258 150 | 834 | 6 305 (−5 %) | 72 826 682 |

Les trajectoires divergent (nombre de sondes différent) : même à décisions identiques par appel,
le coût en opcodes déplace les suspensions. Le gain par sonde est de −5 à −16 %.

**Constat principal** : `ops_sites` ne pèse plus que 5 à 8 % d'`AIR_PLAN_PERF.total_ops` ; le poste
dominant est désormais `ops_eval` (ex. dernière passe graine 42 : 2,34 M sur 2,53 M). Le chiffre de
93 % du 5 septembre est périmé (cache de sites C33.1, `air_cheap_site`). V94 économise donc de
l'ordre de 1 % du planning AIR : le 20×10 de neutralité (~1 h de VPS) n'est pas lancé sans décision
utilisateur.

## 20×10 apparié (2026-09-25)

Campagne `v94_air_site_list_vs_default_10y_20seeds_20260924` (`run_c66_reference.py`, base `6c18ef0`,
3 workers). **Incomplète : 19/20 paires**, la partie de référence (V94 à 0) de la graine 1024 étant
classée `stagnation_suspect` (`declining_without_expansion`) ; verdict harnais `incomplete`.
Sur les 19 paires complètes : `profit_year` −60,7 k£/an (médiane −80,4 k), 9 V / 10 D, p = 1,0,
IC95 [−236,8 ; +115,4] k£/an ; valeur −4,07 % (garde −5 % tenue). Ces chiffres satisferaient la
règle de neutralité d'AGENTS.md §4, mais une campagne incomplète n'est pas un résultat d'adoption.

**Report sur C83** : V94 appliqué sur `c83-fixes` + restriction de la contrainte de créneau aux
courses C83 ; les appels de télémétrie `OpexAirC78NoteNoSite` ont été reproduits dans le chemin liste.
Solo 42/100 × 3 ans, `c83_fixes=1`, `v94_air_site_check=1` : 114 `V94_CHECK OK`, 0 `DIFF`
(cas « aucun site » toujours non exercé).

**Diagnostic de la graine 1024** : faux positif de `game_health.activity_from_series`. Aucune erreur
moteur ; valeur 8,06 M£, caisse 3,7 → 4,9 M£ de mai à décembre 1979, mais flotte (142) et gares (75)
inchangées depuis août (4 mois > `ACTIVITY_RECENT_STEPS` = 3) et une baisse de valeur en novembre.

## 20×10 sur la base C83 (2026-09-25)

Campagne `v94_on_c83_vs_default_10y_20seeds_20260925` : base `c83-fixes` (`3d4d5a4`) + restriction de
la contrainte de créneau aux courses C83 + V94, `c83_fixes` à 0 dans les deux bras. **20/20 paires
saines.** `profit_year` +1,3 k£/an (médiane +61,3 k), 13 V / 7 D, p = 0,263, IC95 [−121,8 ; +124,3]
k£/an ; valeur −3,13 % ; véhicules primaires −4,5. Verdict harnais `fail_primary` (seuil +50 k£,
non applicable ici). Règle d'AGENTS.md §4 : IC95 non entièrement négatif, majorité de victoires,
garde −5 % tenue → **neutre, adoptable**. Le gain d'opcodes a été mesuré sur la base `6c18ef0`
(−5 à −16 % d'`ops_sites` par sonde, ≈ 1 % du planning AIR).
