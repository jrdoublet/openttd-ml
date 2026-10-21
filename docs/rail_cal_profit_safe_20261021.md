# RAIL-CAL-1 — essai prudent de correction du profit (21 octobre 2026)

Exploration **hors ligne** : 40 jeux SOLO (1039 lignes matures) pour ajuster ; 40 jeux DUEL (1032 lignes matures) pour évaluer, un échantillon par ligne (médiane des années âge ≥2). Tous les coefficients s'apprennent exclusivement sur 32 graines SOLO par pli, les 8 graines DUEL correspondantes restent hors apprentissage. Une sélection de modèle entre variantes sur DUEL serait exploratoire, pas une qualification indépendante.

## Constat principal

Biais prévu−réel en SOLO **-7 136 £/an**, contre **679 £/an** en DUEL : transfert de domaine instable. Le constat ne justifie pas une correction multiplicative calibrée sur SOLO.

Chaque correction de profit garde le coût brut inchangé et utilise seulement `pred_prof`, `cargo`, `distance` ou `roi_pred` (candidats au choix). Les ratios sont bornés à [0,25 ; 2], les corrections additives à 2 000 £/an après pondération, la pente affine à [0,5 ; 1,5] avant un retrait à 10 %. `add_dist_factor10` borne aussi le **facteur de profit** final à [0,9 ; 1,1] : k = 1 + clip(0,1 × résidu SOLO rétréci, −0,1 × profit prévu, +0,1 × profit prévu) / profit prévu, pour profit prévu > 0. La correction `solo_inner_select` est choisie automatiquement par validation SOLO interne sur 4 sous-plis, puis appliquée au DUEL exclu.

| Modèle | MAE DUEL £/an | Biais £/an | Gain vs brut £/an par ligne | Graines améliorées /40 | Gain moyen /graine [IC95 bootstrap] £ | Spearman médian profit /graine |
|---|---:|---:|---:|---:|---:|---:|
| raw | 11 495 | 679 | 0 | 0/40 | 0 [0 ; 0] | 0.741 |
| global_10 | 11 545 | 1 396 | -49 | 15/40 | -49 [-105 ; 6] | 0.741 |
| global_25 | 11 678 | 2 471 | -183 | 14/40 | -183 [-319 ; -47] | 0.741 |
| weighted_10 | 11 540 | 1 373 | -45 | 15/40 | -45 [-98 ; 10] | 0.741 |
| weighted_25 | 11 662 | 2 413 | -167 | 14/40 | -167 [-298 ; -37] | 0.741 |
| dist_10 | 11 410 | 1 409 | 86 | 27/40 | 85 [5 ; 163] | 0.751 |
| dist_25 | 11 365 | 2 505 | 130 | 25/40 | 126 [-64 ; 312] | 0.757 |
| cargo_dist_10 | 11 383 | 1 402 | 112 | 27/40 | 110 [28 ; 192] | 0.754 |
| roi_10 | 11 480 | 1 351 | 15 | 20/40 | 15 [-38 ; 69] | 0.737 |
| add_10 | 11 467 | 1 235 | 28 | 22/40 | 27 [-9 ; 64] | 0.741 |
| add_dist_10 | 11 331 | 1 292 | 164 | 29/40 | 161 [102 ; 221] | 0.751 |
| add_dist_factor10 | 11 333 | 1 289 | 163 | 29/40 | 159 [100 ; 220] | 0.751 |
| affine_10 | 11 542 | 1 393 | -47 | 15/40 | -47 [-102 ; 8] | 0.741 |
| solo_inner_select | 11 365 | 2 505 | 130 | 25/40 | 126 [-64 ; 312] | 0.757 |

## Validation croisée

| Pli | Entraînement SOLO (lignes) | Test DUEL (lignes) | Choix sur SOLO interne | MAE SOLO interne brut | MAE SOLO interne choisi |
|---|---:|---:|---|---:|---:|
| 1 | 840 | 198 | dist_25 | 12 049 | 10 907 |
| 2 | 833 | 202 | dist_25 | 11 857 | 10 861 |
| 3 | 812 | 226 | dist_25 | 11 742 | 10 721 |
| 4 | 823 | 209 | dist_25 | 11 888 | 10 819 |
| 5 | 848 | 197 | dist_25 | 11 754 | 10 740 |

Gains de MAE par pli DUEL (valeurs positives = réduction du MAE) :

| Pli | dist_10 | cargo_dist_10 | add_dist_10 | add_dist_factor10 | Sélection SOLO interne |
|---|---:|---:|---:|---:|---:|
| 1 | 234 | 264 | 243 | 242 | 528 |
| 2 | 89 | 115 | 160 | 158 | 156 |
| 3 | -45 | -19 | 63 | 58 | -162 |
| 4 | 124 | 156 | 206 | 205 | 201 |
| 5 | 44 | 61 | 162 | 163 | -37 |

Paramètres SOLO du modèle simple par quartile, intervalles extrêmes entre plis (ces chiffres ne proviennent jamais de DUEL) :

| Quartile | Ratio SOLO `dist` (min–max) | Additif SOLO `add_dist` £/an (min–max) |
|---|---:|---:|
| Q1 | 0.981–0.990 | 95–305 |
| Q2 | 1.131–1.161 | 3 377–4 260 |
| Q3 | 1.292–1.317 | 7 575–8 247 |
| Q4 | 1.396–1.425 | 12 599–14 041 |

## Interprétation et limites

`real_prof` est le profit du véhicule pour l'année passée; `pred_prof` soustrait un amortissement théorique. L'écart ne prouve pas un biais structurel de revenu. Les lignes construites, survécues et âgées de 2 ans sont sélectionnées; le score ne démontre pas l'effet causal d'une modification de politique. `src_prod` est lu au bilan par la sonde conditionnelle `V284_RAIL_GROWTH` et n'est pas stocké dans les objets d'apprentissage ici ; l'employer à la sélection nécessiterait vérifier le champ candidat, son coût API et sa stabilité historique. Ne pas utiliser le `src_prod` post-construction comme prédicteur rétrospectif.

Le classement est le Spearman des profits annuels sur les mêmes lignes construites au sein de chaque graine (sans calibration du capital). Aucun changement de rang éventuel ne démontre une meilleure sélection contrefactuelle.

Recommandation : distinguer le candidat **choisi sans lire DUEL**, `solo_inner_select`, des nombreux essais exploratoires. Un gain moyen positif sur des modèles choisis après consultation DUEL n'est pas une qualification. Pour une politique qualifiée, garder le facteur de profit à 1 sans preuve sur un autre échantillon ; un facteur non neutre peut être placé sous drapeau expérimental clairement identifié pour tester le contrat du prompt 4, sans bascule du défaut.

Reproduire : `python -X utf8 sweeps/demo_rail_cal_profit_safe_20261021.py`. Pas de Docker ni de modification de `ai/OpexAI`.
