# RAIL-SIBLING lot 1 — bancs du 2 novembre 2026

## Protocole

Worktree `/.wt_sibling_20261102`, branche `exp/rail-sibling-20261102`, base `99f29d9c` et arbre local modifié. Comparaison appariée C66.4 : OpexAI rail seul (`mode_air=0,mode_road=0,mode_water=0`) face à AAAHogEx-115 rail seul (`disable_veh_roadveh=1`, `disable_veh_tram=1`, `disable_veh_ship=1`, `disable_veh_aircraft=1`) ; référence `rail_sibling=0`, variante `rail_sibling=1`. Cible : `profit_year` en décembre 1974 ; garde de valeur explicitement assouplie à 100 % pour cette nuit.

Le premier smoke `results/rail_sibling_railseul_smoke_4x5_20261102*` est **invalide** : les deux bras OpexAI ont échoué à la compilation avec `candidates.nut:1433: expected IDENTIFIER`, à cause de l'identifiant Squirrel réservé `parent`. La correction a renommé l'argument en `mother`, sans changer la logique. Ce smoke ne prouve aucune performance.

## Smoke corrigé 4 × 5

Campagne `results/rail_sibling_railseul_smoke_4x5_r2_20261102.json`, bundle `9526d128d28e17b103123cb8ff8530347428d7942f6cace12bb86b2a26ca7ed5`, 4/4 paires comparables. `--probes 6`, `--script-debug`, CPU 8, mémoire 8 Go, 8 workers.

| Graine | Profit référence (£/an) | Profit variante (£/an) | Δ (£/an) | Profit AAA variante (£/an) |
|---|---:|---:|---:|---:|
| 42 | 1 174 166 | 1 123 713 | −50 453 | 2 190 231 |
| 100 | 1 245 672 | 1 227 570 | −18 102 | 867 165 |
| 7 | 2 060 375 | 2 095 564 | +35 189 | 1 616 096 |
| 999 | 1 850 688 | 1 808 651 | −42 037 | 2 611 899 |

Δ moyen **−18 850,75 £/an**, médiane **−30 069,5 £/an**, V/D/E **1/3/0**, Wilcoxon exact **p=0,375**, IC95 bootstrap **[−46 245 ; +15 882,5] £/an**, verdict brut `fail_primary`. Valeur de compagnie variante/référence : **+1,3366 %** (ratio des moyennes). La présence de `stagnation_suspect` pour les graines 100 et 999 impose de ne pas considérer cette exploration comme une qualification du mécanisme.

Les journaux variante `results/rail_sibling_railseul_smoke_4x5_r2_20261102_engine/rail_sibling_l1_seed*_r0.log` exposent 22/8/11/25 événements `RAIL_SIBLING_KEEP` pour les graines 42/100/7/999 et respectivement 2/1/2/2 `RAIL_BUILD` avec `reuse=1 join_end=A`. Ce dernier compteur est un **proxy** de construction jointe : il nécessite la vérification du partage effectif de la gare de départ et du lien `siblingOf` ; tous les événements `KEEP` ne correspondent pas à des constructions.

## Porte rail seule 40 × 5

Campagne `results/rail_sibling_railseul_40x5_20261102*`, bundle gelé `9526d128d28e17b103123cb8ff8530347428d7942f6cace12bb86b2a26ca7ed5`, 40 graines canoniques, `--line-telemetry`, 9 workers, 10 CPU, 8 Go. **40/40 paires complètes** dans le comparateur C66.4, `comparison_complete=true`, verdict brut `fail_primary`.

| Indicateur 1974 | Référence | Variante RAIL-SIBLING |
|---|---:|---:|
| Profit OpexAI moyen | 1 607 766 £/an | 1 629 723 £/an |
| Profit AAA moyen, duels séparés | 2 046 935 £/an | 2 048 443 £/an |
| Rapport des moyennes Opex/AAA | 78,55 % | 79,56 % |

**Δ Opex moyen +21 957,575 £/an**, médiane +17 672 £/an, **22 victoires / 18 défaites**, Wilcoxon exact **p=0,4679719**, IC95 bootstrap **[−14 620,30 ; +61 065,55] £/an**, seuil de gain utile **64 310,631 £/an**. Ratio des moyennes de `company_value` : **+1,483318 %** ; garde élargie à 100 % non bloquante. Ce gain descriptif ne satisfait ni la significativité ni le seuil de gain utile : le lot 1 ne franchit pas la porte A.

Les cinq plus fortes pertes Opex variante−référence sont : **8191 −233 812**, **2026 −155 818**, **232037 −137 319**, **1337 −134 698**, **17 −111 482 £/an**. Les ratios Opex/AAA sont descriptifs : chaque politique joue contre AAA dans son propre duel partagé, avec la même carte et configuration appariées.

Le JSON final fournit **800/800 captures de lignes valides** ; les 80 parties ont `game_ok=true` et `failed_runs=0`, mais 52/160 statuts compagnie sont `stagnation_suspect`. Voir `docs/rail_sibling_lot1_40x5_analysis_20261102.md` pour l'audit détaillé : **57 groupes de deux lignes fret avec une gare A commune et des destinations distinctes**, soit 57 lignes supplémentaires physiquement présentes au 1er décembre 1974, réparties sur 32/40 graines ON ; **zéro groupe correspondant dans OFF**. Chaque paire possède deux trains et leur profit véhicule cumulé 1974 est positif, mais n'est pas un profit incrémental. Les **80 journaux moteur du 40×5 sont vides** (`probes=2`) : impossible de certifier le nombre exact de constructions issues de `RAIL_SIBLING_KEEP→RAIL_BUILD`, ni les candidats refusés. Le smoke corrigé à `probes=6` documente un seul enchaînement KEEP→BUILD certain (graine 42).

## Décision conditionnelle

Le delta moyen 40×5 est positif, donc la suite prescrite est **20×10 rail seul**, puis **20×10 multimodal**, tous deux avec `--decision-rule non_erosion`, `--value-guard-max-loss-pct 100`, 20 graines canoniques et 10 ans. Ces bancs sont descriptifs en présence du verdict `fail_primary` de 40×5 : ils ne qualifient pas à eux seuls le lot 1.

## Rail seul — non-érosion 20 × 10

Campagne `results/rail_sibling_railseul_20x10_20261102.json`, bundle gelé **identique au 40×5** `9526d128d28e17b103123cb8ff8530347428d7942f6cace12bb86b2a26ca7ed5`, carte 256² et période 1970–1979. **20/20 paires complètes**, règle `non_erosion`, garde exceptionnelle 100 %, `--line-telemetry`.

**Δ profit_year Opex ON−OFF +27 363,15 £/an** (médiane +29 482,5 £), V/D/E **11/9/0**, Wilcoxon descriptif **p=0,4090977**, IC95 bootstrap **[−34 000,30 ; +88 925,95] £/an**, valeur moyenne ON−OFF **−1,499704 %**. Verdict brut **`pass`** pour non-érosion, car la borne supérieure de l'IC95 n'est pas strictement négative. Ce résultat ne convertit pas le `fail_primary` du 40×5 en qualification.

Dans le bras de référence du 20×10, profit moyen Opex **1 723 994 £/an** contre AAAHogEx **3 941 369 £/an** : ratio de moyennes **43,74 %**. Dans la variante : Opex **1 751 358 £/an** contre AAA **3 929 023 £/an**, soit **44,57 %**. **0/20** victoires Opex face à AAA dans la variante également. La graine 512 passe de 1 318 685 à 1 358 389 £/an chez Opex (AAA variante 5 541 746 £/an) ; 1337 de 1 520 073 à 1 350 592 £/an (AAA variante 4 543 874 £/an). L'objectif absolu de 100 % à dix ans n'est pas atteint, malgré le gain moyen modeste de la variante.

## Multimodal — non-érosion 20 × 10

Campagne terminée `results/rail_sibling_multimodal_20x10_20261102.json`, bundle `410e53b0e1668b9f70efcf43a25099e74498281cd0e62893d041090e09244bab85`. OpexAI sans mode désactivé dans les deux bras, AAAHogEx sans désactivation de véhicules ; 20 graines, dix années, `--line-telemetry`, 9 workers (autre activité Docker constatée), garde exceptionnelle à 100 %. **20/20 paires complètes, 40 parties, zéro échec moteur.**

**Delta Opex ON−OFF −36 380,60 £/an**, médiane **−27 813,50 £/an**, **10 victoires / 10 défaites**, Wilcoxon descriptif **p=0,4523754**, IC95 bootstrap **[−142 322,70 ; +74 699,85] £/an**, valeur de compagnie **−0,372233 %** (ratio des moyennes ON/OFF). Verdict brut **`pass`** selon la règle de non-érosion : la borne haute de l'intervalle n'est pas négative. Cela ne démontre pas une amélioration multimodale.

| Profit moyen 1979 | Référence OFF | Variante RAIL-SIBLING ON |
|---|---:|---:|
| OpexAI | 4 090 826,35 £/an | 4 054 445,75 £/an |
| AAAHogEx | 6 659 391,30 £/an | 6 586 533,10 £/an |
| Ratio Opex/AAA des moyennes | **61,429 %** | **61,557 %** |

**Objectif 80 % multimodal non atteint.** La hausse apparente du ratio malgré la baisse de profit propre OpexAI vient de la diminution plus importante du profit AAA dans les duels du bras ON. Le verdict global économique du lot 1 reste `fail_primary` au 40×5 rail seul, malgré la non-érosion au 20×10 rail seul et multimodal.
