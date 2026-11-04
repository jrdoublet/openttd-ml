# T9 — Inventaire du code rail expérimental (4 novembre 2026)

## Résumé

1. **Aucune suppression** dans cette tâche. Le processus reste : inventaire, puis liste validée
   par l'utilisateur, puis suppression.
2. **RAIL-LOOP (défaut 1) dépend de deux familles « mortes ».**
   - Géométrie DOUBLE-GROW : `OpexDoubleGrowPrimaryRoute`, `TurnsSafe` et `VerifyRoute`, dans
     `double_grow_geometry.nut`.
   - Signaux V190-FIX2 : `OpexV190Fix2PlaceSignal*` et `Rollback`, dans
     `v190_fix_directional.nut`.

   Il faut retirer les **sélecteurs** de ces familles, pas leurs fichiers, puis déplacer ces
   fonctions vers un module partagé avant toute suppression.
3. **V233L (défaut 1) garde vivants** `OpexV190ExecuteRailPlan`, `OpexConvertDoubleTrackToLoop`
   (V181), `OpexV190MergeIgnoredTiles` et `OpexV190CollectParallelTiles`. Ce ne sont pas du
   code mort.
4. **Le code mort coûte peu au défaut** : presque toutes les gardes sont des booléens globaux.
   Exception notable : `OpexV190Active()`, **un appel de fonction**, est évalué par candidat
   dans `OpexLineEconomics` (`economy.nut:411`, `:430`) et par essai de site
   (`builder_rail.nut:1477`), alors que `V190_RAIL_DOUBLE_BUILD=0`. Un court-circuit
   `V190_RAIL_DOUBLE_BUILD && OpexV190Active()` relève de la règle opcodes.
5. **Les verdicts du pack sont tous négatifs ou non qualifiés** pour V190/FIX/FIX2, RDS,
   SEARCH-PRIO, PAIR, DOUBLE-GROW, V131 et V259. Ceux de RAIL-OPEN, RAIL-SIBLING, INVEST-STALL et
   RAIL-LONG v2/v3 donnent « A échoue, B passe ». Recommandation : retirer 8 familles et en
   garder 6 (tableau).

## Tableau d'inventaire

Sources des verdicts : `docs/cloud_pack_20261104/campaigns.csv` (Δ profit/an, V/D, p), puis
`docs/taches.md` et les rapports cités. Les lignes sont comptées au commit `8268b653`.

| Drapeau (réglage) | Défaut | Fichiers et lignes | Dernier verdict de banc | Code partagé avec RAIL-LOOP | Dépendances croisées | Recommandation |
|---|---|---|---|---|---|---|
| **V190** (`v190_rail_double_build`, `_delay`, `_max_trains=4`) | 0 | `builder_rail.nut` : trace/plan `3202-3745` (~545), exécution `5972-6518` (~545) ; `task_rail.nut:525-567`, `:745-800` ; 10 appels `OpexV190Active()` dans `builder_rail.nut`, 10 dans `task_rail.nut`, 2 dans `economy.nut`, 1 dans `candidates.nut` | `v190_eco_20261103.md`. Pack : `v190_fix_independent_4x6` **−318 k**, 0/4 | `OpexV190VerifyIndependentDouble` (utilisé par DOUBLE-GROW v2 et FIX2) | **V233L** appelle `OpexV190ExecuteRailPlan`, `OpexV190MergeIgnoredTiles` et `CollectParallelTiles` | **Retirer** le chemin V190 (sélection, Cas 4, économie à deux voies) ; **garder** ce que V233L appelle ; court-circuiter `OpexV190Active()` |
| **V197** (`v197_guided_double`) | 0 | `builder_rail.nut:3368-3449` (~80), gardes `:4812`, `:5069` | Sous V190 ; aucun banc isolé positif | — | Requis par FIX2 (`V190_FIX_DIRECTIONAL && V197`) | **Retirer** avec V190 |
| **V190-FIX / FIX2** (`v190_fix_directional`) | 0 | `v190_fix_directional.nut` 475 ; `builder_rail.nut:6337-6350` | `v190_fix2_smoke_4x6` **−448 k** 0/4 ; `directional_orchestrated` **−631 k** 0/4 ; `safe90_wp` **−666 k** | **Oui** : `OpexV190Fix2PlaceSignal`, `PlaceSignalWindow` (×4), `Rollback` | V190, V197 | **Retirer le chemin directionnel**, **déplacer** les 3 aides de signal vers `rail_loop.nut` ou un module partagé |
| **V198 / V199 / V200** (`v198_template_double`, `v199_robust_build`, `_level_budget_k`, `v200_double_cash_k`) | 0 | V199 `builder_rail.nut:3784-4007` (~225) et branches de `OpexBuildTrack` ; V198 `rail_templates.nut` (851, en partie) ; V200 `:5275-5284` | Sous V190 ; aucun gain isolé consigné | — | V190 | **Retirer** avec V190. Vérifier d'abord la part de `rail_templates.nut` encore utilisée par INVEST-STALL et RAIL-LONG (`OpexRailVehicleSlotAvailable` y est seulement appelé) |
| **DOUBLE-GROW 1/2** (`double_grow`) | 0 | `double_grow.nut` 62, `double_grow_fleet.nut` 388, `double_grow_geometry.nut` 1 199, `double_grow_v2.nut` 143, `double_grow_v2_build.nut` 687 | 13 campagnes « diagnostic_only » 2×6, de −82 k à +68 k ; aucune qualification (`double_grow_20261103.md`) | **Oui** : `OpexDoubleGrowPrimaryRoute` (×2), `TurnsSafe`, `VerifyRoute` (×3) | `OpexV190VerifyIndependentDouble` | **Retirer** les sélecteurs (`task_rail.nut:629-630`), le build v2 et la flotte ; **garder ou déplacer** la géométrie utilisée par RAIL-LOOP |
| **RAIL-PAIR / V271 tandem** (`rail_pair`) | 0 | `task_rail_pair.nut` 650 ; `task_rail.nut:624`, `:649` | `rail_pair_smoke_4x6` r1 à r4 : **−56 k, −19 k, −40 k, −120 k**, toujours sous 50 % de victoires | — | Marqueur `v271Tandem` lu par `_expandRailLines` et RAIL-LOOP (`OpexRailLoopEligible`) | **Retirer**, en gardant la lecture du marqueur `v271Tandem` pour les anciennes sauvegardes, ou la retirer avec une migration |
| **RAIL-DEPOT-SIGNAL** (`rail_depot_signal`) | 0 | `rail_depot_signal.nut` 453 ; branches dans `builder_rail.nut` (`:5552`, `:5594`, `:6646`, `:6675`, rollback `:4418`) et `task_rail.nut:1770-1780` | `rds_smoke_4x6` **−1,31 M** 0/4 ; `orientation` **−935 k** ; `failclosed_A40x5` −12 k, 8/10 | — | Rollback (`OpexRailDepotSignalRollbackTracked`) | **Retirer** (le pire verdict du lot) |
| **RAIL-SEARCH-PRIO** (`rail_search_prio`) | 0 | `task_rail.nut:1-130` (~130) et ~15 appels de journal ; `scheduler.nut:435` | `rail_search_prio_4x6` **−325 k** 0/4 ; `_v190` **−409 k** 0/4 | — | Stock C121 (T3-04) | **Retirer**. Si T3-04 est traité, le faire par un délai de 180 jours sur la préparation, pas par la préemption |
| **RAIL-LONG 1/2/3** (`rail_long` 0..3, `rail_long_value_rank`) | 0 | `task_rail_long_v2.nut` 597, `_fleet.nut` 148, `rail_long_v3.nut` 104, `_multi.nut` 289, `_upgrade.nut` 860 ; `builder_rail.nut:1510-1562` et `OpexRailPlatformPlans` ; `economy.nut` (`railLongFill`) | v1 : smoke 4×6 **−50 k / −37 k**. v2 : A 40×5 +24,6 k (p=0,49) fail, B pass. v3 : A 40×5 **−17 £** fail, B rail +46 k et multi +48 k pass ; post-r6 : A 40×3 fail, B pass. **NO-GO** (`rail_long_20261103.md`) | — | V257 (raccourcissement, T8-04), INVEST-STALL (transactions v2) | **Retirer v1**. **Geler v2/v3** sans les supprimer, jusqu'à T5-01 (quai minimal) et T8-02 (traction au profit). Envisager de fusionner la transaction v2 avec RAIL-FILL |
| **INVEST-STALL** (`invest_stall`) | 0 | `invest_stall.nut` 164, `invest_stall_fleet.nut` 514 ; `task_v284.nut` (revalidation), `orchestrator.nut:1016-1019`, `scheduler.nut:110` ; projecteurs `invest_stall_*_off.py` | v2 : A 40×5 +5,5 k (p=0,67) fail, B 20×10 +35,9 k pass. 0 complément sur 37 à cause du bug T8-03 | — | V284, RAIL-LONG v2 | **Garder** : refaire le smoke après T8-F1, puis les portes A et B |
| **EB-2** (`eb2_new_station_fallback`) | 0 | `builder_rail.nut:1888` (une garde), `EB2_FALLBACK` | Porte A **échouée** (`taches.md`, lot EB) | — | Partage la branche de repli avec RAIL-OPEN (`strictOriginReuseJoin`) | **Fusionner** dans RAIL-OPEN : RAIL-OPEN finance déjà le repli, et T5-03 retouche cette branche |
| **V181 boucle** (`OpexConvertDoubleTrackToLoop`, `OpexTraceTrackTiles`, `OpexV181*`) | sans réglage propre | `builder_rail.nut:6719-7199` (~480) ; `task_rail.nut:786-800` (Cas 4, sous V190) | V181 « inerte » (+0,2 k, `taches.md`) | — | **V233L** (défaut 1) : `builder_rail.nut:6344` | **Garder** (vivant par V233L) ; seul l'appel du Cas 4 meurt avec V190 |
| **V131** (`v131_rail_repair`, `v131_town_clearance`) | 0 | `task_rail.nut:2199-3198` (~1 000) | Porte A 40×5 **réfutée** (`taches.md`, table V131) | — | Stock C121, `_revalidateRailStockPlan` | **Retirer** (le plus gros bloc mort de `task_rail.nut`) |
| **V259** (`v259_bridge_renew`) | 0 | `task_v259.nut` 333 ; `task_rail.nut:1604-1630`, `:1898-1915`, ponts V259 dans `_consumeRailUpgrade` | Exposition 6×10 : **0 événement** ; cause structurelle (`taches.md`, 18/10) | — | — | **Retirer**, ou garder seulement la liste des ponts si un autre usage la lit (aucun trouvé) |
| **V307** (`v307_long_probe`, `_probe_year`, `_sites`, `_sink_room`, `v307_abnd_autopsy`) | 0 | `probe_v307.nut` 503 ; `builder_rail.nut:202-470` (sink room, ~270) et `:566-1079` (sites, ~510) | Sonde (mesure). Mode inverse neutre, non retenu ; sites et sink room sans verdict positif | — | V307 sink room dans `OpexBuildLine` et `OpexRollback` | **Retirer** sites et sink room. **Garder** la sonde, outil de mesure documenté |
| **V294 continu** (`v294_rail_continuous`) | 0 | `builder_rail.nut:2199-2217` ; `task_rail.nut:1069`, `:1814`, `:1978` | Aucun verdict isolé trouvé | — | T4-05 (`structures = []`) | **À vérifier** : garder tant que T4-01 n'est pas tranché (alternative à la jonction de segments) |
| **RAIL-SIBLING / RAIL-OPEN** (`rail_sibling`, `rail_open`) | 0 | `builder_rail.nut:1570-1627`, branches de `OpexRailPlatformPlans`, `candidates.nut` | SIBLING : A 40×5 +22 k fail, B +27 k pass. OPEN : A +21 k fail, B rail +61 k pass, multi +158 k pass (p=0,075) | — | **Bras de référence de tous les bancs rail** ; T5-03 | **Garder** ; candidats à une requalification après T5-03 |
| **RAIL-FILL / RAIL-KEEP** (`rail_fill`, `rail_expand_keep`) | 0 | `rail_fill.nut` 100, `rail_keep.nut` 24 | Pas encore de banc (prompts du 04/11) | RAIL-FILL ignore les lignes RAIL-LOOP | V284 | **Garder** (récents, pas encore mesurés) |

## Code mort qui coûte des opcodes au défaut

| Site | Fréquence | Coût | Correction (règle opcodes) |
|---|---|---|---|
| `OpexV190Active()`, `economy.nut:411`, `:430` | Deux fois par appel `OpexLineEconomics`, soit des milliers par régénération | Appel de fonction, lecture de deux globales, `AIDate` (`globals_pre.nut:137`) | `V190_RAIL_DOUBLE_BUILD && OpexV190Active()` |
| `OpexV190Active()`, `builder_rail.nut:1477` | Une fois par longueur de quai essayée | Idem, plus `AIDate.GetCurrentDate()` | Idem |
| `candidates.nut:1075` | Une fois par candidat V233L | Idem | Idem |
| `_expandRailLines`, gardes `RAIL_PAIR`, `RAIL_LOOP`, `RAIL_EXPAND_KEEP`, `V284` | Par ligne et par passe | Booléens | Rien à faire |
| `orchestrator.nut:1016-1019` | Par tick | Court-circuitées par `V233_LONG_GOOD > 0` | Rien à faire tant que V233L vaut 1 ; à revoir si V233L passe à 0, car `OpexInvestStallPending` et `OpexRailLongV2FleetPending` seraient appelées à chaque tick |
| `RAIL_SEARCH_PRIO`, journaux V131 et V307 | Gardés | Booléens | Rien à faire |

Le gain se mesure en opcodes, pas en profit : appliquer la règle de neutralité opcodes
(`AGENTS.md` §4) et non les portes économiques.

## Ordre de suppression proposé (après validation utilisateur)

1. **Déplacer d'abord** les fonctions partagées utilisées par RAIL-LOOP (géométrie DOUBLE-GROW,
   signaux FIX2) vers un module neutre. Projections et tests suivent ; aucun comportement ne
   change.
2. Retirer, un lot par commit, avec sa projection OFF et la compatibilité des sauvegardes
   (marqueurs `v271Tandem`, `v190Independent`, `v181Loop`, `depotEndB*`) :
   - RDS ;
   - SEARCH-PRIO ;
   - PAIR ;
   - DOUBLE-GROW (sélecteurs, build v2 et flotte) ;
   - V131 ;
   - V259 ;
   - V307 sites et sink room ;
   - V190 + V197 + FIX + FIX2 + V198 + V199 + V200, en préservant les appels V233L.
3. Fusionner EB-2 dans RAIL-OPEN. Retirer RAIL-LONG v1.
4. Après chaque lot : suite complète, puis un smoke 1×1 de compilation. Le comportement au défaut
   doit rester identique au bit près, entre deux bras du même code.

## Livraison

- Branche `cloud/revue-rail-T9-20261104` : ce rapport seul, aucun changement de code.
