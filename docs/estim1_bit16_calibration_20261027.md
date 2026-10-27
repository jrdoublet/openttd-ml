# ESTIM-1 bit 16 — calibration RAIL selon la distance (27 octobre 2026)

**Périmètre.** Calibration hors partie, à partir des journaux `decision_log=1` de 40 parties DUEL et 40 parties SOLO × 10 ans du 21/10/2026. Cette note propose uniquement des paramètres pour le bit 16 expérimental ; les facteurs modaux existants, dont `k_R.rail = 0,92` du bit 1, restent la référence. Aucun gain en `profit_year` ou classement réellement constructible n'a été mesuré par cette analyse.

## Recette RAIL : quatre quartiles et droite normalisée

Même population que l'a priori ESTIM bit 1 (`sweeps/estim_unifie_priors.py`) : `LINE_REVENUE`, année complète (`age >= 2`), flotte inchangée depuis `RAIL_BUILD` (`vehs == n0`), recette réalisée `real_rev = profit + exploitation`, recette prédite brute `pred_rev > 0`. On retrouve les **4 495 années-lignes DUEL** et le rapport des sommes **0,91785547** publiés pour le bit 1. Les 40 parties servent de grappes pour les IC95 (bootstrap percentile de 3 000 tirages, générateur Python `Random(20261027)`), afin de ne pas considérer les années d'une même ligne comme indépendantes.

Les coupures **fixées avant la présente estimation** par RAIL-CAL-1 sur les constructions SOLO+DUEL du 21/10 sont Q1 `d <= 90`, Q2 `91..127`, Q3 `128..172`, Q4 `d >= 173`, `d` en tuiles. Un facteur brut est le rapport `Σ real_rev / Σ pred_rev` dans le quartile. Pour le comparer à l'a priori 0,92, la table et la droite sont ramenées à **la même moyenne pondérée par la recette prédite**, `0,92` ; seule leur dépendance à la distance change.

| Quartile | DUEL années-lignes | DUEL ratio brut | `k_R` normalisé | IC95 `k_R` par partie | SOLO `k_R` normalisé (n) |
|---|---:|---:|---:|---:|---:|
| Q1 `<=90` | 1 227 | 0,73238 | **0,73409** | [0,67787 ; 0,79773] | 0,74190 (978) |
| Q2 `91–127` | 1 156 | 0,85072 | **0,85271** | [0,79772 ; 0,91571] | 0,83397 (1 345) |
| Q3 `128–172` | 1 109 | 0,97053 | **0,97280** | [0,90332 ; 1,04269] | 0,94761 (1 520) |
| Q4 `>=173` | 1 003 | 1,06275 | **1,06523** | [1,00707 ; 1,12376] | 1,04447 (1 298) |

La régression linéaire aux moindres carrés pondérés, avec **poids `pred_rev`** pour chaque ligne-année, ajuste `real_rev/pred_rev` à la distance. Après renormalisation, le modèle DUEL à intégrer dans le bit 16 serait :

```text
k_R(d) = 0.92 + 0.0025851937835571948 * (d - 134.49704854924377)
       = 0.5722990661837049 + 0.0025851937835571948 * d
```

Sa pente a pour **IC95 [0,001874 ; 0,003255] par tuile** ; distances des observations DUEL : **15–250 tuiles**. Le centrage exact sur `d=134,4970` garantit `Σpred_rev × k_R(d) / Σpred_rev = 0,92` sur le corpus DUEL. La pente SOLO renormalisée à 0,92 est **0,0025119241082623**, IC95 **[0,002146 ; 0,002857]**, sur 5 141 années-lignes ; le ratio brut SOLO vaut **1,14263**. L'accord des pentes étaye l'effet de distance, sans prétendre que le niveau du prior DUEL s'applique tel quel à SOLO. Les lignes hors de la plage 15–250 n'étant pas représentées par DUEL, borner l'argument `d` à cet intervalle est prudent lors d'une éventuelle intégration.

Pour préserver la **mise à jour en partie** du facteur global du bit 1, intégrer la droite comme profil relatif : `k_R_effectif(d) = ESTIM_K_R.rail × k_R(d) / 0,92`. La formule numérique ci-dessus décrit le démarrage à prior modal 0,92 ; elle ne doit pas remplacer la valeur du facteur modal qui évolue avec les observations.

### Pourquoi préférer la droite aux quatre paliers ?

Validation descriptive **leave-one-game-out**, 40 plis DUEL : on réestime les coefficients sur 39 parties, puis calcule `|real_rev − pred_rev × k(d)|` sur la partie exclue. Le modèle plat est le prior 0,92 ; le modèle à paliers utilise les ratios de sommes par Q renormalisés sur les 39 parties. Les IC95 portent sur les différences de MAE après rééchantillonnage des 40 parties tenues à l'écart.

| Modèle `k_R` | MAE DUEL £/ligne-année | MAE SOLO £/ligne-année |
|---|---:|---:|
| Constant 0,92 | 13 558,57 | 14 669,99 |
| **Linéaire** | **12 949,16** | **14 383,59** |
| Paliers Q1–Q4 | 13 008,25 | 14 398,91 |

En DUEL, droite moins constante : **−609,40 £/ligne-année**, IC95 **[−851,86 ; −360,93]** et amélioration dans **32/40 parties**. Paliers moins droite : **+59,08 £**, IC95 **[−35,38 ; +147,64]** ; les paliers améliorent l'erreur dans seulement **14/40 parties**. En SOLO, droite moins constante : **−286,41 £**, IC95 [−451,40 ; −122,40] ; paliers moins droite : +15,32 £, IC95 [−36,85 ; +70,66]. La droite conserve donc le bénéfice prédictif observé, avec deux coefficients et sans discontinuité artificielle à 90/127/172. Cette validation reste conditionnée aux lignes déjà construites, sans observation des candidats refusés.

## Coût RAIL avant A* : multiplicateur distinct

`RAIL_ATTEMPT` publie `pre` (capital avant recherche A*), `actual` (coût effectivement décaissé), `manh` (distance) et `ok`. On retient uniquement les `ok=1`, `pre>0`, `actual>0` **précédés d'un `PROJECT_CHOSEN` ordinaire sans `railPlan`** (l'événement historique est émis avant `_startRailSearch`, `task_rail.nut`). Les projets dont le tracé était préparé et les traces `p1_long=1` sont exclus, car le bon devis n'est plus nécessairement le devis naïf. Une sélection consommée ne peut être réutilisée par une seconde tentative. En DUEL, **1 088 succès** avec pré-devis exploitables, dont **74** à tracé déjà préparé exclus : **1 014 constructions** pour l'estimation. En SOLO : **1 070**, **85** exclus, donc **985** retenues.

| Quartile | DUEL n | `Σcoût réel / Σdevis pré-A*` DUEL | IC95 DUEL | SOLO n / ratio |
|---|---:|---:|---:|---:|
| Q1 | 248 | **1,25825** | [1,23171 ; 1,28745] | 164 / 1,24836 |
| Q2 | 254 | **1,45755** | [1,42822 ; 1,48568] | 255 / 1,39598 |
| Q3 | 254 | **1,59703** | [1,57217 ; 1,62539] | 292 / 1,53560 |
| Q4 | 258 | **1,66092** | [1,62973 ; 1,69239] | 274 / 1,61914 |

La régression **OLS du ratio par construction** (`actual/pre`) donne en DUEL :

```text
k_C_preAstar(d) = 1.077866789429587 + 0.0032418925908056723 * d
k_C_apresAstar = 1.0
```

IC95 en grappes : pente **[0,002986 ; 0,003488]**, ordonnée **[1,045721 ; 1,114447]**. SOLO : `1,0674369372245902 + 0,0029887667764848355 × d` ; IC95 pente **[0,002700 ; 0,003285]**, soit une vérification indépendante du signe et de l'ordre de grandeur. Ce modèle concerne exclusivement le **devis pré-A*** à risque terrain : dès qu'un `railPlan` a établi un devis actualisé, **factoriser par 1** pour éviter la double majoration de capital. Il n'autorise à lui seul aucune modification de la garde de financement ; l'ancien facteur de coût avait déjà été écarté au financement dans la revue ESTIM bit 2.

## Reproduction et limites

Depuis la racine `/openttd-ml` sous PowerShell 5.1 :

```powershell
python -X utf8 sweeps/estim_unifie_priors.py --selftest
python -X utf8 sweeps/estim_unifie_priors.py --rail-distance --bootstrap 3000 --campaign duel=results/calibration_pc_20261021/results/calib_duel_40x10_pc_20261021_engine --campaign solo=results/calibration_pc_20261021/results/calib_solo_40x10_pc_20261021_engine --out results/estim1_bit16_priors_20261027.json
```

Les coefficients complets, effectifs et IC sont dans [`results/estim1_bit16_priors_20261027.json`](../results/estim1_bit16_priors_20261027.json). Le script conserve son comportement historique pour la commande sans `--rail-distance` ; l'option nouvelle est un dépouillement séparé. Tests intégrés au `--selftest` : appariement des devis après événement pré-A*, exclusion des tracés préparés, fit exact d'une droite synthétique et normalisation de la recette.

**Portée du résultat.** Les quartiles reflètent la sélection effective des lignes, et le bootstrap mesure la variabilité entre les 40 parties, pas un effet causal d'activation du bit 16. Les années-lignes répétées d'une même ligne ne sont pas indépendantes ; les IC sont rééchantillonnés par partie. Il faudrait encore vérifier les candidats financés/évincés, les erreurs de profit total et les portes économiques A/B en monde partagé avant d'adopter le bit par défaut.
