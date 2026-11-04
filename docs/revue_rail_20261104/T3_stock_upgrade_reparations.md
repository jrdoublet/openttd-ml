# T3 — Revue de l'ordonnanceur rail II : stock, upgrade, réparations (4 novembre 2026)

## Résumé

1. **Le stock spéculatif ne concurrence pas les projets en rail seul** : il n'existe que par la
   préparation C121, c'est-à-dire en multimodal, pendant la première année, quand aucun projet
   rail n'est généré. Il garde le slot seulement au passage à l'année 2, sans délai de 180 jours
   (T3-04).
2. **Course certaine entre upgrade et RAIL-LOOP** sur une même ligne. Un A\* d'upgrade lancé
   avant que RAIL-LOOP prenne la ligne s'exécutait quand même et doublait une ligne en cours de
   conversion en boucle. **Corrigé (F2, sans condition)** : le slot est rendu à la transaction
   (T3-01).
3. **Les bannissements « durables » viennent d'échecs physiques, pas de la caisse ni du slot.**
   `STNFAIL`, `NOTRAIN` (plafond de trains) et `TRKFAIL` bannissent pourtant 365 × n jours, avec
   un compteur jamais remis à zéro. Une partie est transitoire (T3-02, à mesurer).
4. **Le doublement Cas 2 posait voie, gares et dépôt sans slot train**, puis démolissait tout sur
   `TRAINFAIL`. **Corrigé (F1)**, inerte sous le plafond (T3-03).
5. **Les réparations V131 ne bouclent pas, ne démolissent rien et sont bornées** (défaut 0). Le
   worker `rail_stock` ne vérifie pas qu'il traite un stock : invariant latent, non atteint dans
   la boucle normale (T3-05).

## Périmètre et provenance

- **Référence** : `ccr-6d627d08-tlnphk` au commit **`8268b653`** (`rail_loop=1` par défaut,
  RAIL-FILL et RAIL-KEEP en opt-in). Les numéros de ligne désignent ce commit, sauf mention
  « branche T3 ».
- **Livraison** : branche `cloud/revue-rail-T3-20261104`. Elle part de `8268b653` et ne
  contient pas les correctifs de T2 (branche distincte).
- **Lecture complète** : `task_rail.nut:1414-3346`.
- **Lecture ciblée** :
  - `orchestrator.nut:216-352` (workers `rail_search` et `rail_stock`) et `:995-1110`
    (ordre (b)/(c)/(d) du tick) ;
  - `scheduler.nut:255-290`, `:428-545` (tranches A\* et débit V89) ;
  - `main.nut:830-875` (boucle principale) ;
  - `rail_prep_c121.nut` (en entier) ;
  - `task_projects.nut:895-910` ;
  - `projects.nut:128-140` ;
  - `lines.nut:236-310` (mémoire d'abandon) ;
  - `builder_rail.nut:1210-1260`, `:3075-3093`, `:5244-5275`, `:5420-5480`, `:6519-6720`
    (préparation et exécution de l'upgrade) ;
  - `rail_loop.nut:1-300`, `:556-640`.
- **Journaux** : `docs/cloud_pack_20261104/logs_*.csv`, en comptes agrégés par étiquette et
  motif. Le pack ne contient ni `RAIL_EXPAND`, ni `RAIL_STN_FAIL err=`, ni `RLOOP` par ligne :
  les fréquences sont à mesurer sur le PC (§ Plan de banc).

## Constats, triés par gain attendu

Classes : **(a)** certain dans le code ; **(b)** probable ; **(c)** à vérifier en moteur.

| ID | Classe / gravité | Emplacement (`8268b653`) | Défaut | Correction | Gain attendu |
|---|---|---|---|---|---|
| T3-01 | (a) logique, (c) fréquence ; perte de profit, robustesse | `task_rail.nut:1859-1864` ; `:651` ; `rail_loop.nut:269`, `:196-210` ; `builder_rail.nut:6624-6625` | RAIL-LOOP n'utilise pas `_railSearch`. Il peut donc prendre (`railLoop=1`) une ligne dont l'A\* d'upgrade est en vol. `_consumeRailUpgrade` doublait ensuite cette ligne sans revérifier. Résultat : `doubleTrack=1` sur une ligne en boucle, un état que `OpexRailLoopEligible` exclut par construction. L'exécution démolit aussi les tuiles des quais jumeaux **sans revérifier qu'elles sont encore libres** | **F2 codé, sans condition** : à la transaction, si `RAIL_LOOP && railLoop > 0`, rendre le slot sans pose ni mémoire. Journal `RAIL_EXPAND ... reason=RLOOP_OWNED ok=0` | La ligne reste à RAIL-LOOP : jusqu'à 8 rames, environ +29 k£/an par rame, au lieu d'une seule rame indépendante. Évite une démolition possible de la voie 2 de la boucle |
| T3-02 | (b) ; perte de profit | `task_rail.nut:1796-1803` ; `lines.nut:277-292`, `:295-302` ; `task_rail.nut:1923-1927` | `STNFAIL` (sans condition), `NOTRAIN`/`ORDFAIL` (`V301_NOTRAIN_FIX & 1`, actif à 15) et `TRKFAIL` (`& 8`, actif) bannissent la paire 365 × n jours, plafonné à 1 825. `_abandonCounts` est persisté, jamais décrémenté ni remis à zéro. Côté upgrade, tout échec hors `CASH` bannit la ligne de la même façon | Opt-in : pour `STNFAIL`, transmettre `AIError.GetLastError()` dans `result` (aujourd'hui seulement journalisé sous `DECISION_LOG`, `builder_rail.nut:5460-5468`). Délai court (30 à 60 jours) sans incrémenter `count` quand l'erreur est `ERR_VEHICLE_IN_THE_WAY` ou `ERR_LOCAL_AUTHORITY_REFUSES` ; idem pour `NOTRAIN` quand la cause est le plafond. Non codé | Inconnu, potentiellement le plus grand du lot. Le pack compte **545 `RAIL_BUILD_FAIL STNFAIL`** et **3 543 `PROJECT_DISCARD abandoned_pair`**, toutes campagnes confondues. La part transitoire reste à mesurer (étape 0 du plan) |
| T3-03 | (a) ; perte d'argent au plafond, nulle en banc | `task_rail.nut:1863` → `builder_rail.nut:6580-6669` ; invariant `builder_rail.nut:5258-5262` | `OpexExecuteUpgradeAfterSearch` vérifie la caisse (`:6617`) mais pas le slot train. Au plafond `vehicle.max_trains`, il pose gares, voie 2 et dépôt, échoue sur `OpexBuildTrains`, démolit tout (`TRAINFAIL`, `:6666`) et bannit la ligne 365 × n jours. Le commentaire M4/16.2 l'interdit pourtant explicitement | **F1 codé, sans condition** : `_consumeRailUpgrade` n'exécute que si `OpexRailVehicleSlotAvailable()`. Sinon résultat `NOVEHSLOT`, même mémoire d'échec qu'avant, sans dépense | Nul sous le plafond (500 trains par défaut, Opex en a environ 55). Au plafond : coût de la voie 2, des gares, du dépôt et de leur démolition, une fois par ligne et par 365 × n jours |
| T3-04 | (a) logique, (b) effet ; perte de profit, multimodal seulement | `orchestrator.nut:271-303` ; `task_rail.nut:312-318` | Un A\* de préparation C121 (`isC121RailPrep`) ne subit jamais le délai de 180 jours (`!prepSearch`), y compris après la première année. Au passage à l'année 2, les premiers projets rail sont refusés (`search_in_progress`) jusqu'à la fin de cet A\* spéculatif, que seul son budget d'itérations borne | Appliquer le délai de 180 jours dès que `C121_CATALOG_FIRST_YEAR_ACTIVE` est faux, ou laisser `RAIL_SEARCH_PRIO` (opt-in existant, propriétaire `stock`) préempter. Non codé | Faible : quelques semaines de retard sur le premier projet rail en multimodal |
| T3-05 | (c) ; robustesse | `orchestrator.nut:268`, `:327-330` ; `task_rail.nut:2058-2094`, `:2096` ; `rail_prep_c121.nut:123`, `:148` ; `task_projects.nut:906` | `OpexWorkerRailStockStep` avance **n'importe quel** `_railSearch` et le dépose au stock à la fin, sans tester `isStockSearch`. Les gestionnaires de fin appelés hors worker ne libèrent pas `_activeWorker`. Scénario théorique : un stock finit hors worker, une primaire part dans la même passe, puis est déposée au stock au lieu d'être construite. **Non atteint dans la boucle normale** : (c) précède toujours (d) dans le tick (`orchestrator.nut:1060`), et le débit V89 de `main.nut:873`, qui peut finir l'A\* après (d), est rattrapé par (c) au tick suivant, avant toute passe projects | Garde d'une ligne dans le worker : `return "done"` si `_railSearch` n'est ni `isStockSearch` ni `v131_repair`. Non codée : sans scénario atteignable, elle déplacerait les opcodes sans gain prouvé | Nul tant que l'ordre du tick reste celui-ci ; protège les évolutions futures |
| T3-06 | (a) ; aucun défaut | `task_rail.nut:2199-3198` | V131 (défaut 0) : sondes sous `AITestMode` uniquement, aucune démolition. Bornes `V131_REPAIR_MAX_TILES=35`, `_RUNS=3`, `_ITERS=2500`. Une seule réparation par plan (`v131RepairFailed`/`v131Repaired`, `_v131RepairExhausted`). Slot refusé (`slot_busy`) si `_railSearch` ou un worker rail est actif | — | — |
| T3-07 | (a) ; style | `task_rail.nut:3202-3338`, `:3340-3346` | `_revalidateRailStockPlan` ne bannit rien : un échec jette le plan (`_c121RailPrepDropStock`) ou refuse le rang (`cash`, `no_vehicle_slot`). `_v184InitRailSlots` n'est qu'une remise à zéro | — | — |

### T3-01 — Upgrade et RAIL-LOOP sur la même ligne

**Chronologie qui déclenche le défaut** (au défaut, `rail_loop=1`, V190 inactif) :

1. Cycle *t*. RAIL-LOOP n'admet pas L : soit l'attente est sous une rame pleine, soit
   `_railLoopState` est déjà pris par une autre ligne. Le Cas 2 de `_expandRailLines`
   (`:709-732`), avec son seuil plus bas de 2 wagons, lance l'A\* d'upgrade sur L
   (`_railSearch.kind = "upgrade"`).
2. Cycle *t + Δ*, A\* d'upgrade encore en vol. `OpexRailLoopSelect` (`:631`) passe **avant** la
   garde de slot (`:644`). L est encore admissible (`doubleTrack == 0`, `trains == 1`) et
   `OpexRailLoopBegin` pose `railLoop = 1` (`rail_loop.nut:269`).
3. L'A\* d'upgrade finit. `_consumeRailUpgrade` exécutait `OpexExecuteUpgradeAfterSearch`
   **sans revérifier** la garde `railLoop > 0` que `_expandRailLines:651` applique au
   lancement.

**Conséquences possibles** :

- la ligne devient `doubleTrack=1` avec 2 rames pendant que RAIL-LOOP continue
  (`OpexRailLoopStep` ne teste que `railLoop != 1`) ;
- si la voie 2 de la boucle a été posée pendant l'A\*, le tracé d'upgrade la croise et
  `OpexJoinPathIsDedicated` refuse (`OVERLAP`) : le slot est perdu et la ligne bannie
  365 jours ;
- les quais jumeaux sont choisis libres à la préparation (`OpexJoinPlatformPlans` exige
  `IsBuildable`). Pourtant `builder_rail.nut:6624-6625` les démolit à l'exécution sans
  revérification. Si la voie 2 de la boucle y passe, `DemolishTile` la coupe (classe (c),
  géométrie à confirmer).

**Correctif F2** : la garde de `:651` est rejouée à la transaction. Le slot est rendu, sans
mémoire d'échec (la ligne n'est pas en échec) et sans dépense. Le comportement au défaut ne
change **que dans cette course**, ce qui est un bug avéré dans le code : deux transformations
concurrentes d'une même ligne, dont l'une rend l'autre inadmissible.

### T3-02 — Ce qui bannit vraiment une paire

| Échec | Banni ? | Où |
|---|---|---|
| Caisse (`CASH`, `cash_at_build`, `insufficient_cash`) | **Non** | `_recordRailAttempt` ne marque pas `CASH` ; upgrade : sortie `CASH` sans mémoire (`:1867-1879`) |
| Slot occupé (`search_in_progress`) | **Non** | refus de rang (`:312-325`), aucune écriture |
| Revalidation d'un plan de stock | **Non** | `:327-366` : plan jeté ou rang refusé |
| `ABND`, `SITEA/B/AB`, `NOPA` | Oui | `:1796-1803` |
| `STNFAIL` | Oui, sans tenir compte du code d'erreur | `:1797` |
| `NOTRAIN`, `ORDFAIL` | Oui (`V301_NOTRAIN_FIX & 1`) | `:1798` |
| `TRKFAIL` | Oui (`& 8`, ou garde géométrique) | `:1799-1802` |
| Upgrade hors `CASH` (y compris `TRAINFAIL`, `STATIONFAIL`) | Oui (clé de ligne) | `:1923-1927` |

Le délai vaut `365 × count`, plafonné à 1 825 jours (`lines.nut:301-302`). `count` vient de
`_abandonCounts` : persisté (`persist.nut:702`, `:833`), jamais décrémenté ni effacé après un
succès. Un deuxième `STNFAIL` passager sur une bonne paire la retire donc deux ans ; un
troisième, trois ans.

Parmi les causes de `STNFAIL`, `ERR_VEHICLE_IN_THE_WAY` et `ERR_LOCAL_AUTHORITY_REFUSES`
(note de ville remontée en quelques mois) sont transitoires. `ERR_AREA_NOT_CLEAR` et
`ERR_FLAT_LAND_REQUIRED` ne le sont pas. La correction doit donc être pilotée par le code
d'erreur et mesurée avant d'être codée.

## Réponses aux questions du prompt

**1. Le stock concurrence-t-il les projets financés ?**

Seule la préparation C121 démarre un stock (`rail_prep_c121.nut:270`, unique appelant de
`_startRailStockSearch`). Elle exige `MODE_AIR && MODE_RAIL` et la première année.

- **Rail seul** (référence des bancs) : jamais de stock, aucune concurrence.
- **Multimodal, première année** : `projects.nut:132-138` coupe toute génération rail
  (`doFreight = doPaxRail = false`). Aucun projet rail n'attend donc. Le stock cède en plus le
  tick (« hold ») dès qu'un AIR vivant est finançable (`orchestrator.nut:275-295`).
- **Multimodal, passage à l'année 2** : seul cas où un projet attend. L'A\* de préparation en
  vol garde le slot sans délai de 180 jours (T3-04), et les projets rail sont refusés
  `search_in_progress` jusqu'à sa fin. `RAIL_SEARCH_PRIO` (opt-in) sait déjà préempter ce
  propriétaire.

**2. Réparations V131 : boucle, dépense sans fin, démolition ?**

Non, pour les trois (T3-06) :

- tout se fait sous `AITestMode` ; le plan réparé est ensuite posé par le constructeur normal ;
- aucune `DemolishTile` dans `:2199-3198` ;
- itérations, tuiles et passes sont bornées, avec une seule tentative par plan.

Une réparation occupe le slot (`kind = "v131_repair"`), avec le même délai de 180 jours que le
stock. Défaut 0 : risque nul au défaut. Elle ne touche pas une boucle RAIL-LOOP, puisqu'elle ne
sonde que les tuiles du plan neuf.

**3. Un échec transitoire bannit-il durablement une bonne paire ?**

- **Caisse et slot occupé : non** (tableau T3-02).
- **Oui pour d'autres transitoires** : `STNFAIL` dû à un véhicule ou à l'autorité locale,
  `NOTRAIN` au plafond, `TRKFAIL` passager. Le bannissement s'aggrave à chaque répétition,
  sans oubli du compteur.
- Côté upgrade, avant F1, le plafond de trains provoquait **dépense, démolition et**
  bannissement. Après F1, il ne reste que le bannissement, comme avant.

**4. L'upgrade (Cas 2, doublement indépendant) est-il encore utile au défaut ? Conflit avec une
boucle ?**

**Utilité.** Il reste actif au défaut (V190 inactif, Cas 2 historique) et garde une utilité
résiduelle : une ligne que RAIL-LOOP refuse géométriquement (`reject`, `primary_route`) peut
encore recevoir une seconde rame. Mais il passe **avant** RAIL-LOOP sur les lignes en croissance
(seuil plus bas, T2-03 de la revue T2) et les retire définitivement des boucles. Recommandation
inchangée depuis T2 : sous RAIL-LOOP, réserver le Cas 2 aux lignes refusées par la boucle
(opt-in, à mesurer).

**Conflit avec une boucle.** Il y en avait un, la course T3-01, corrigé par F2. Hors de cette
course, il n'y a pas de conflit :

- `_expandRailLines` saute `railLoop > 0` ;
- `OpexPrepareUpgradeSearch` refuse `doubleTrack == 1` ;
- `OpexRailLoopEligible` exclut les lignes doublées.

Reste une ligne en échec de boucle **avec voie 2 conservée** (`railLoop = -1`, nouvel essai à
6 000 jours) : le Cas 2 peut la doubler. Le chemin dédié refuse toute tuile rail, ce qui
empêche de croiser la voie 2. Les quais jumeaux ne sont choisis que sur des tuiles
constructibles. Pas de démolition de la boucle, au pire un `OVERLAP` et un bannissement d'un an.

## Corrections livrées (branche `cloud/revue-rail-T3-20261104`)

Les deux correctifs sont **sans condition**, dans un seul hunk de `_consumeRailUpgrade`
(`task_rail.nut`, branche T3 `:1863-1878`), avant l'appel historique.

| ID | Changement | Effet au défaut |
|---|---|---|
| F2 (T3-01) | `if (RAIL_LOOP && ("railLoop" in state.line) && state.line.railLoop > 0)` : journal `RLOOP_OWNED` sous `DECISION_LOG`, `_railSearch = null`, `return` | Change le comportement **uniquement** dans la course upgrade ↔ RAIL-LOOP (bug avéré). Sous `rail_loop=0`, inerte |
| F1 (T3-03) | `OpexRailVehicleSlotAvailable() ? OpexExecuteUpgradeAfterSearch(...) : { ok = false, reason = "NOVEHSLOT", cost = 0, train = null }` | Inerte sous le plafond de trains ; au plafond, plus de pose ni de démolition (bug avéré, invariant M4/16.2). Même mémoire d'échec qu'un `TRAINFAIL` |

Autres changements :

- **Projection OFF** : `sweeps/revue_rail_t3_off.py`, nouvelle tête de chaîne dans
  `invest_stall_diagnostic_off.off_source`, avant RAIL-KEEP. Elle restaure les octets de
  `8268b653`, est idempotente et refuse un hunk partiel ou dupliqué. Les tests de projection de
  RAIL-LOOP, RAIL-FILL et RAIL-KEEP retirent d'abord cette couche.
- **Harnais** : `sweeps/run_m4_conformity.py` accepte `max_trains_<n>` en plus de
  `max_trains_0`, pour exposer F1 (plan de banc, étape 3).
- **Tests** : `sweeps/test_revue_rail_T3_20261104.py`, 14 tests (ordre des gardes, sortie sans
  mémoire pour F2, champs lus couverts par le résultat de repli de F1, prédicat identique à
  `:651`, arité, projection, harnais).
- **Suite complète** `python3 -X utf8 -m unittest discover -s sweeps -p 'test_*.py'` :
  - avant : 3 407 tests, 4 échecs, 12 erreurs ;
  - après : 3 421 tests, **les mêmes 4 échecs et 12 erreurs**, tous préexistants et connus :
    `test_b6_portfolio_causality` (1), `test_rail_long_v3_multi` (2) et
    `test_v166_aaahogex_settings` (13, source AAAHogEx absente). Aucun nouvel échec.
- **Squirrel relu deux fois** : pas de closure, pas de `const`, pas d'identifiant réservé.
  `RAIL_LOOP`, `DECISION_LOG`, `OpexDecide` et `OpexRailVehicleSlotAvailable` sont des globales
  chargées avant `task_rail.nut`. La table de repli porte `ok` et `reason`, seuls champs lus
  hors de la branche de succès.

## Plan de banc pour le PC

```powershell
$ref = 'OpexAI[mode_air=0,mode_road=0,mode_water=0,rail_sibling=1,rail_open=1]'
$aaa = @('--aaahogex-setting','disable_veh_roadveh=1','--aaahogex-setting','disable_veh_tram=1',
         '--aaahogex-setting','disable_veh_ship=1','--aaahogex-setting','disable_veh_aircraft=1')

# 0. Fréquences sur des journaux EXISTANTS (aucune partie)
$logs = '.wt_rail_loop_20261104\results\rail_loop_non_erosion_rail_20x10_20261104_engine\*.log'
Get-ChildItem $logs | ForEach-Object {
  $stn  = (Select-String $_ 'RAIL_STN_FAIL').Count
  $veh  = (Select-String $_ 'RAIL_STN_FAIL .* err=(\d+)' -AllMatches |
           ForEach-Object { $_.Matches.Groups[1].Value } | Group-Object | ForEach-Object { "$($_.Name):$($_.Count)" }) -join ','
  $ban  = (Select-String $_ 'ABANDON_PAIR .* count=([2-9])').Count
  "$($_.Name) stnfail=$stn errs=[$veh] rebans=$ban" }
# T3-01 : lignes qui ont à la fois un RLOOP et un doublement Cas 2
Get-ChildItem $logs | ForEach-Object {
  $loops = Select-String $_ 'RLOOP .*line=(\d+)' | ForEach-Object { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
  $dbl   = Select-String $_ 'RAIL_EXPAND action=double_track line=(\d+) reason=OK ok=1' | ForEach-Object { $_.Matches[0].Groups[1].Value }
  "$($_.Name) both=$((@($dbl) | Where-Object { $loops -contains $_ }).Count)" }

# 1. Compilation 1x1 (F1 et F2 toujours actifs)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/bench_v2.py --arms "OpexAI" --seeds 42 --years 1 --max-workers 1 `
  --out results/revue_t3_smoke_1x1_20261104.json

# 2. Smoke 4x6 rail seul : branche T3 contre 8268b653 (worktree séparé, même harnais)
git worktree add ..\wt_t3_base 8268b653
python -X utf8 sweeps/run_c66_reference.py --campaign revue_t3_smoke_4x6_20261104 `
  --policy-id reference --variant-policy-id revue_t3 --reference $ref --variant $ref `
  --decision-rule gain_short --min-useful-primary-delta-pct 4 --required-seeds 4 --required-years 6 `
  --years 6 --seeds 17 512 314 8191 --probes 6 --script-debug --line-telemetry `
  --mount-root 'C:\Users\jr\vscode\openttd-ml\openttd-ml' --cpus 10 --memory 8g --max-workers 10 `
  --value-guard-max-loss-pct 100 --out results/revue_t3_smoke_4x6_20261104.json @aaa
# (la même commande depuis ..\wt_t3_base, --campaign revue_t3_base_smoke_4x6_20261104)

# 3. Exposition de F1 : plafond bas de trains (multimodal par défaut, diagnostic)
docker run --rm --cpus=10 --memory=8g --memory-swap=8g -v openttd-lab-home:/home/lab -v "${PWD}:/work" -w /work openttd-lab `
  python3 sweeps/run_m4_conformity.py --scenarios max_trains_8 --seeds 17 512 314 8191 --years 6 --workers 4 `
  --out results/revue_t3_max_trains_8_4x6_20261104.json
```

**Critères de lecture.**

| Critère | Attendu |
|---|---|
| Santé du smoke | 8/8, 0 erreur NoAI, année de fin = 1976 pour chaque graine |
| `RAIL_EXPAND ... reason=RLOOP_OWNED` (étape 2, `--script-debug`) | Rare. Chaque occurrence est une course T3-01 évitée ; la ligne doit ensuite avoir `RLOOP phase=commit` ou `fail` |
| Étape 0, `both` | > 0 sur l'ancien code : la course a coûté des boucles ; = 0 : F2 sans objet en pratique, à garder comme garde de transaction |
| Étape 3, `max_trains_8` | Branche T3 : `RU|..|NOVEHSLOT` et aucun `RU|..|TRAINFAIL` ; base : `TRAINFAIL` avec démolition |
| Étape 0, `errs` de `RAIL_STN_FAIL` | Part de `ERR_VEHICLE_IN_THE_WAY` / `ERR_LOCAL_AUTHORITY_REFUSES`. Au-delà d'environ 20 % des `STNFAIL`, coder l'opt-in T3-02, puis porte A 40×3 et porte B 20×10 |
| `company_value`, `profit_year` (étape 2) | Neutre à ±5 % : F1 et F2 n'agissent que dans des cas rares ; un écart plus grand se lit d'abord comme du chaos d'opcodes (même code, trajectoire décalée) |

F1 et F2 corrigent des transactions et ne changent pas de réglage : pas de qualification
économique obligatoire. **T3-02 et T3-04**, s'ils sont codés, sont des opt-in et passent par
les portes A et B du §4.
