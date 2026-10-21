# RAIL-PROFIT-1 — composantes du profit des lignes ferroviaires

21 octobre 2026. Diagnostic **hors ligne** des 40 parties SOLO et des 40 DUEL de dix ans, à partir des journaux du PC. Exécuter `python -X utf8 sweeps/diag_rail_profit_components_20261021.py` pour régénérer ce rapport et `python -X utf8 -m unittest sweeps/test_rail_profit_components_20261021.py` pour les tests synthétiques.

## Verdict pour RAIL-CAL-1 prompt 4

La table multiplicative cargo × distance précédente, ajustée sur des **lignes-années**, détériorait déjà le profit DUEL : MAE 13 245 → 14 094 £/an ; biais +1 884 → +7 912 £/an (`docs/calibration_rail_jointe_20261021.md`, §Contre-vérification). Les modèles ci-dessous évaluent **chaque ligne mature une seule fois**, avec la médiane des années pleines et le test sur graines exclues de SOLO.

| Modèle | N lignes DUEL | MAE profit £/an | Biais prédit−réel £/an | Δ MAE vs brut £/an |
|---|---|---|---|---|
| raw | 1032 | 11 495 | 679 | 0 |
| global | 1032 | 13 474 | 7 870 | 1 979 |
| cargo | 1032 | 13 388 | 7 638 | 1 893 |
| cargo_distance | 1032 | 12 881 | 7 795 | 1 385 |
| cargo_roi | 1032 | 13 423 | 7 936 | 1 928 |


**Meilleur MAE sur DUEL : raw**, gain = 0 £/an par ligne (descriptif hors graines, conditionné aux lignes historiquement construites). Aucun correcteur de profit évalué ne réduit la MAE : **pas qualifié** pour le prompt 4.

| Correction | Graines avec gain / 40 | Gain MAE moyen par graine £ | IC95 bootstrap du gain £ |
|---|---|---|---|
| global | 4/40 | -1 974 | [-2 424 ; -1 500] |
| cargo | 3/40 | -1 882 | [-2 288 ; -1 455] |
| cargo_distance | 6/40 | -1 395 | [-1 904 ; -875] |
| cargo_roi | 4/40 | -1 924 | [-2 364 ; -1 470] |


## Comparaison comptablement homogène (les mêmes plis)

Deux cibles supplémentaires évitent de comparer directement le profit prévu net d'amortissement au profit de véhicules mesuré sans amortissement explicite : **exploitation** : `pred_rev − pred_run` versus `real_prof = real_rev − real_run` ; **net proxy** : `pred_prof` versus `real_prof − amort_pred`. Le second est une **hypothèse de dépréciation identique au budget théorique**, pas une mesure du net réalisé.

**operating**

| Modèle | N lignes | MAE homogène £/an | Biais £/an | Δ MAE vs brut £ |
|---|---|---|---|---|
| raw | 1032 | 11 487 | 2 202 | 0 |
| global | 1032 | 13 106 | 7 470 | 1 620 |
| cargo | 1032 | 13 098 | 7 364 | 1 611 |
| cargo_distance | 1032 | 12 574 | 7 560 | 1 087 |
| cargo_roi | 1032 | 13 216 | 7 768 | 1 729 |


**net_proxy**

| Modèle | N lignes | MAE homogène £/an | Biais £/an | Δ MAE vs brut £ |
|---|---|---|---|---|
| raw | 1032 | 11 487 | 2 202 | 0 |
| global | 1032 | 13 146 | 7 504 | 1 659 |
| cargo | 1032 | 13 142 | 7 410 | 1 655 |
| cargo_distance | 1032 | 12 617 | 7 604 | 1 131 |
| cargo_roi | 1032 | 13 244 | 7 792 | 1 758 |


## Couverture, appariements et sélection

| Observation | SOLO | DUEL |
|---|---|---|
| games | 40 | 40 |
| choices | 1440 | 1895 |
| builds | 1070 | 1088 |
| build_no_choice | 85 | 74 |
| build_choice_cargo_mismatch | 0 | 0 |
| build_no_mature | 31 | 56 |
| mature_lines | 1039 | 1032 |
| mature_without_choice | 85 | 74 |
| mature_usable_line_years | 5869 | 5510 |
| revenue_no_build | 0 | 0 |
| revenue_bad_vehicle_or_year | 0 | 0 |
| revenue_missing_component | 0 | 0 |
| mature_with_costs | 954 | 958 |
| real_accounting_checked_years | 5869 | 5510 |
| real_accounting_mismatch_years | 0 | 0 |
| predicted_gap_nonzero_years | 5869 | 5510 |


Appariement chronologique : dernier `PROJECT_CHOSEN` de même paire (src,dst) et cargo antérieur à `RAIL_BUILD`, puis `line` vers `LINE_REVENUE` (compagnie 0 seulement). Si le cargo diffère, le cas est identifié ; les projets abandonnés ne fournissent aucun profit contrefactuel. Un rapport décalé après la construction ou une ligne détruite avant deux ans créent un biais de survie. Les lignes choisies ne constituent pas un échantillon aléatoire du portefeuille.

## Comptabilité et attribution (DUEL, une ligne mature)

Le code `task_report.nut:247-262,431-435,523` calcule `real_prof` avec `AIVehicle.GetProfitLastYear`, mais `real_run` est la **somme des coûts de fonctionnement courants** `GetRunningCost`, et `real_rev` est **construit** comme `real_prof + real_run`. Ce revenu n'est donc **pas un poste de recettes observé indépendamment pour l'année passée**. Le code `economy.nut:395-397,455-463` prédit `pred_prof = pred_rev − pred_run − amortAnnual`. L'amortissement réel n'est pas enregistré et ne peut pas être déduit par différence. L'égalité réalisée est une identité de construction, pas une vérification indépendante du moteur.

Contrôle : résidu réalisé **exactement nul pour chacune des 5510 lignes-années DUEL** (`real_accounting_mismatch_years=0`). La prise de médianes séparées par ligne peut casser cette identité (résidu maximal 1 084.00 £/an sur les seules médianes). Résidu prédit `pred_rev−pred_run−pred_prof` médian **1 471 £/an** (négatifs : 0, nuls : 0). Ce dernier est un **amortissement prévu**, sans observation correspondante au réel.

| Grandeur | N lignes | MAE £/an | Biais prédit−réel £/an |
|---|---|---|---|
| rev | 1032 | 11 591 | 2 266 |
| run | 1032 | 199 | 54 |
| prof | 1032 | 11 495 | 679 |


Décomposition algébrique des **moyennes** (en £/an, médianes annuelles par ligne) : biais profit = 678.89 ; biais revenu − biais fonctionnement − amortissement prévu = 690.05. Les médianes prises séparément peuvent briser légèrement l'identité quand les différentes composantes varient d'une année à l'autre. Les biais de revenu/charges ne constituent donc **pas une attribution causale** du profit.

| Type | MAE revenu | Biais revenu | MAE courant | Biais courant | MAE profit | Biais profit |
|---|---|---|---|---|---|---|
| PASS | 4 060 | 1 096 | 462 | 462 | 3 920 | -732 |
| FREIGHT | 12 007 | 2 331 | 185 | 31 | 11 914 | 757 |


## Erreur de profit par cargo et par distance (DUEL)

| Cargo | N | Brut MAE | Global MAE | Cargo MAE | Cargo×distance MAE | Cargo×ROI MAE |
|---|---|---|---|---|---|---|
| COAL | 225 | 14 710 | 18 880 | 17 704 | 16 079 | 18 306 |
| GOOD | 37 | 61 717 | 80 176 | 80 176 | 80 176 | 80 176 |
| GRAI | 180 | 7 000 | 8 988 | 9 217 | 9 094 | 9 001 |
| IORE | 176 | 8 292 | 7 703 | 7 968 | 7 748 | 7 941 |
| LVST | 59 | 7 091 | 8 354 | 9 058 | 9 247 | 9 171 |
| OIL_ | 130 | 7 872 | 8 122 | 7 729 | 7 266 | 7 758 |
| PASS | 54 | 3 920 | 4 054 | 3 896 | 3 856 | 3 885 |
| STEL | 4 | 8 708 | 11 278 | 11 278 | 11 278 | 11 278 |
| VALU | 2 | 23 364 | 23 906 | 23 906 | 23 906 | 23 906 |
| WOOD | 165 | 11 002 | 11 253 | 11 896 | 11 616 | 11 496 |


| Bande tuiles | N | Brut MAE | Cargo MAE | Cargo×distance MAE |
|---|---|---|---|---|
| Q1 | 280 | 8 489 | 11 952 | 9 954 |
| Q2 | 254 | 9 149 | 12 030 | 11 368 |
| Q3 | 249 | 12 283 | 13 087 | 13 456 |
| Q4 | 249 | 16 482 | 16 690 | 17 139 |


Les bornes de distance sont fixées avant mesure : ≤90, 91–127, 128–172, ≥173. Les facteurs sont médians sur **une ligne** et rétrécis vers le cargo (poids 50, minimum 10 lignes), puis limités à [0,05 ; 4]. Le signal supplémentaire testé est le quartile de ROI prédit (≤35, ≤50, ≤70, >70 %) ; aucun champ de revenu réalisé n'entre dans les prédicteurs. Un `pred_prof` nul ou négatif reste inchangé ; profit réalisé négatif conservé dans entraînement, MAE et biais.

## Quartiles selon ROI **prédit**

| Quartile | N | ROI prévu médian % | ROI réalisé médian % | MAE profit brut £ | MAE meilleur £ | Biais meilleur £ |
|---|---|---|---|---|---|---|
| Q1 | 239 | 22.7 | 15.4 | 5 880 | 5 880 | -2 939 |
| Q2 | 240 | 43.3 | 31.1 | 7 859 | 7 859 | -3 206 |
| Q3 | 239 | 58.7 | 43.0 | 10 968 | 10 968 | -4 081 |
| Q4 | 240 | 87.6 | 59.2 | 21 500 | 21 500 | 10 310 |


Ces quartiles sont recalculés sur les mêmes lignes DUEL à coût physique positif ; quartiler sur le réalisé sélectionne mécaniquement les extrêmes et amplifie la régression vers la moyenne.

## Quartiles selon ROI **réalisé**

| Quartile | N | ROI prévu médian % | ROI réalisé médian % | MAE profit brut £ | MAE meilleur £ | Biais meilleur £ |
|---|---|---|---|---|---|---|
| Q1 | 239 | 26.2 | 12.9 | 10 408 | 10 408 | 8 455 |
| Q2 | 240 | 45.0 | 28.6 | 8 256 | 8 256 | 1 679 |
| Q3 | 239 | 55.5 | 42.9 | 10 157 | 10 157 | -2 823 |
| Q4 | 240 | 79.1 | 64.8 | 17 401 | 17 401 | -7 175 |


Ces quartiles sont recalculés sur les mêmes lignes DUEL à coût physique positif ; quartiler sur le réalisé sélectionne mécaniquement les extrêmes et amplifie la régression vers la moyenne.

## ROI financier : devis et profit sont des modèles distincts

Coût : OLS `(coût final RAIL_BUILD / devis PROJECT_CHOSEN) ~ a+b·distance` appris **sur constructions SOLO des quatre autres plis**, utilisé sur les lignes DUEL appariées ; si aucun devis n'est apparié, la ligne reste dans les métriques de profit mais sort du ROI.

| Profit | N ROI | MAE ROI / devis brut (points) | MAE ROI / devis recalé | Biais ROI recalé | Spearman médian / graine |
|---|---|---|---|---|---|
| raw | 958 | 21.34 | 14.52 | -0.08 | 0.692 |
| global | 958 | 32.32 | 16.92 | 8.99 | 0.692 |
| cargo | 958 | 32.13 | 16.84 | 8.71 | 0.699 |
| cargo_distance | 958 | 32.36 | 16.35 | 8.72 | 0.704 |
| cargo_roi | 958 | 32.63 | 16.94 | 9.13 | 0.687 |


La correction de capital ne peut justifier, à elle seule, le correcteur de **profit** : comparer séparément ses MAE et biais à ceux du coût seul (ligne `raw` sur devis recalé). Spearman est calculé au sein de chaque graine avec rangs moyens en cas d'égalité, puis médiané sur les 40 graines. Les cinq plis DUEL de huit graines n'ont aucune graine d'entraînement SOLO commune.

## Signal à mesurer ensuite (hypothèses, pas des résultats)

D'abord instrumenter sous `decision_log` déjà existant, à une cadence limitée (un événement par construction puis un bilan annuel), la **demande captable au choix**, la production industrielle, `predCarried`, la capacité et les trains/wagons envisagés, les temps aller-retour et les notes de gare prévues. S'ils sont déjà présents dans l'objet candidat, leur lecture et concaténation coûtent O(1) par projet dans la branche de diagnostic ; ne pas faire d'appel API pour recalculer. Mesurer ensuite au bilan la charge/capacité, la production transportée, la note des gares et la présence concurrente : données dynamiques qui **ne sont pas connues au choix** ; O(1) appels par ligne et par an, jamais par candidat. Proscrire scans de carte, recherche de trajet ou listes de véhicules par candidat. Les opcodes exacts restent à profiler avant toute activation.

**Limites** : seules les lignes survivantes jusqu'à âge ≥2 ont un profit mesuré ; médianes de 2 à 8 années pleines ; variation du nombre de trains normalisée par `n0/vehs` (approximation linéaire, pas reconstruction contrefactuelle de la flotte de départ). Une première/deuxième campagne SOLO et DUEL sur la même graine ne constitue pas une répétition indépendante. `GetRunningCost` est une charge annualisée courante, pas une comptabilité annuelle, et `real_rev` est calculée par solde. La notation `roi` dans PROJECT_CHOSEN est en millièmes ; ici ROI annualisé est `100·profit/capital`, avec deux versions de capital. Pas de preuve directe d'amortissement historique réel ni de causalité de l'effet du concurrent.

## Reproductibilité : plis et tailles

| Pli | Graines DUEL tenues à l'écart | Lignes entraînement SOLO | Lignes test DUEL | Constructions coût entraînement |
|---|---|---|---|---|
| 1 | 17486, 101154, 173883, 416714, 551035, 659100, 785502, 874979 | 840 | 198 | 770 |
| 2 | 31249, 104234, 283371, 438248, 621101, 697929, 786605, 875622 | 833 | 202 | 768 |
| 3 | 66989, 133887, 306616, 467272, 625099, 707080, 795462, 933000 | 812 | 226 | 743 |
| 4 | 89252, 150301, 341090, 497933, 628258, 709384, 858483, 945977 | 823 | 209 | 755 |
| 5 | 100323, 150807, 404321, 550673, 657364, 754022, 861251, 952252 | 848 | 197 | 780 |

