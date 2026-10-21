# RAIL-CAL-1, etape 1 — calibration jointe du ROI RAIL, hors partie

21 octobre 2026. **Mesure passive uniquement, RAIL corrige dans les calculs hors ligne ; AIR,
flotte AIR et ROAD strictement inchanges.** Aucun banc OpenTTD supplementaire,
aucune modification de `ai/OpexAI`. Script reproductible :
`python -X utf8 sweeps/demo_calibration_rail_jointe_20261021.py --selftest`, puis
`python -X utf8 sweeps/demo_calibration_rail_jointe_20261021.py` ; sortie complete
`evidence/review/roi_calibration_predictors_20261021/calibration_rail_jointe_20261021.json`.

## Constantes finales apprises sur SOLO entier (40 graines)

**Cout** : sur 985 constructions RAIL dont devis et cout final sont connus,
re-ajustement OLS du ratio `cout reel / devis pre-A*` en fonction de la
distance `d` (tuiles) :

```
K_RAIL_cout(d) = 1,062686150395 + 0,003008780074 * d
devis_calibre = devis_initial * K_RAIL_cout(d)
```

La droite precedente RAIL-CAPEX-1 `1,051980877 + 0,003065880*d`
avait ete ajustee aux seules lignes matures. La petite difference est
attendue : **ici les 985 constructions** SOLO appariees sont exploitees
pour le cout, sans conditionner sur leur survie jusqu'a deux ans.

**Profit net** : sur 5 857 lignes-annees matures RAIL SOLO (`LINE_REVENUE`,
age >= 2, `real_prof` ramene a la flotte initiale, valeurs negatives
conservees), medians du ratio realise/predit par cargo × quartile de
distance. Chaque cellule est retrecie vers la mediane tous cargos
du meme quartile selon la formule explicitement demandee :

```
K_profit(cargo,Q) = (n * mediane_cargo_Q + 50 * mediane_tous_Q) / (n + 50)
ROI_RAIL_calibre = ROI_RAIL_brut * K_profit(cargo,Q) / K_RAIL_cout(d)
```

Quartiles fixes sur les constructions SOLO+DUEL : **Q1 ≤90 ; Q2 91–127 ;
Q3 128–172 ; Q4 ≥173**. Medians de repli du profit SOLO, respectivement
**0,905527 / 1,114477 / 1,291211 / 1,422478**. Cellule absente :
mediane du quartile. Les facteurs suivants sont la **table exacte arrondie
a quatre decimales pour lecture**, les valeurs non arrondies et les effectifs
figurant dans le JSON (le prompt 4 devrait utiliser les constantes precises
seulement s'il etait autorise).

| Cargo | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| COAL | 0,8442 (480) | 1,1066 (334) | 1,3735 (318) | 1,4834 (273) |
| GOOD | 0,8546 (6) | 1,2900 (17) | repli 1,2912 | 1,4259 (8) |
| GRAI | 1,0015 (150) | 1,1159 (343) | 1,3087 (432) | 1,3803 (315) |
| IORE | 0,9875 (136) | 1,1785 (305) | 1,2944 (314) | 1,4475 (278) |
| LVST | 1,0597 (46) | 1,0690 (52) | 1,3980 (54) | 1,5792 (61) |
| OIL_ | 0,8823 (115) | 1,0358 (170) | 1,0943 (257) | 1,3488 (177) |
| PASS | 0,6692 (205) | 0,8194 (17) | 1,1796 (5) | repli 1,4225 |
| STEL | 1,1237 (6) | repli 1,1145 | repli 1,2912 | repli 1,4225 |
| VALU | 0,7410 (1) | 1,1077 (1) | 1,3316 (2) | 1,4746 (2) |
| WOOD | 0,9116 (181) | 1,1280 (249) | 1,3689 (232) | 1,3862 (315) |

Ces constantes sont **entrainees sur SOLO entier pour lecture uniquement**.
Les chiffres d'evaluation DUEL qui suivent proviennent de **cinq plis** :
les 40 graines sont separees en cinq ensembles disjoints de 8, chaque
ensemble DUEL etant evalue par des constantes SOLO reapprises sans ses
8 graines. L'effectif d'entrainement varie entre 764 et 808 couts,
et 4 628 a 4 754 lignes-annees de profit selon le pli. Aucun DUEL ne sert
a ajuster les constantes appliquees a ce DUEL.

## Chiffre demande : baisse du score RAIL au top 5 DUEL

Sur **13 695 entrees RAIL** des top 5 journaux, somme des scores positifs
bruts `4 031 381`, scores calibres `3 337 543` :

**Facteur moyen pondere par le score : 0,827891 ; baisse −17,211 %.**
IC95 **bootstrap en grappes de graines** (20 000 tirages, graine 20261021) :
**[−18,099 % ; −16,276 %]**. Ce sont des scores **historiques**,
pas des profits additionnels ni des constructions contrefactuelles.

| Quartile de distance | Entrees RAIL | Score avant / apres (total) | Baisse |
|---|---:|---:|---:|
| Q1 ≤90 | 3 487 | 776 139 / 554 565 | **−28,548 %** |
| Q2 91–127 | 2 790 | 838 991 / 678 560 | **−19,122 %** |
| Q3 128–172 | 4 772 | 1 516 161 / 1 315 365 | **−13,244 %** |
| Q4 ≥173 | 2 646 | 900 090 / 789 053 | **−12,336 %** |

| Cargo | Entrees top 5 | Baisse score ponderee |
|---|---:|---:|
| COAL | 2 173 | −17,281 % |
| GOOD | 786 | −15,671 % |
| GRAI | 3 039 | −17,336 % |
| IORE | 1 782 | −16,151 % |
| LVST | 2 209 | −11,664 % |
| OIL_ | 1 639 | −25,199 % |
| PASS | 367 | −38,330 % |
| STEL | 136 | −19,197 % |
| VALU | 92 | −19,844 % |
| WOOD | 1 472 | −17,894 % |

| Annee | Entrees RAIL | Baisse score ponderee |
|---|---:|---:|
| 1971 | 392 | −21,174 % |
| 1972 | 2 393 | −17,252 % |
| 1973 | 3 066 | −18,043 % |
| 1974 | 2 129 | −16,197 % |
| 1975 | 1 520 | −15,929 % |
| 1976 | 1 416 | −15,475 % |
| 1977 | 1 002 | −15,558 % |
| 1978 | 920 | −16,259 % |
| 1979 | 857 | −15,447 % |

La valeur 1970 est absente car il n'y a aucune entree RAIL positive dans
ce top 5 pour l'annee ; il ne faut pas la traiter comme un zero economique.

Les facteurs AIR (1 323 entrees), flotte AIR (5 508) et ROAD (377)
restent **exactement 1** sur toutes les observations. Les facteurs RAIL
sur les cinq plis vont de **0,4054** a **1,0072**.

### Frontieres de classement numerique visibles

Sur les top 5 exposes, on observe **417 changements de leader numerique** :
330 RAIL→RAIL, 63 RAIL→AIR, 14 RAIL→flotte AIR, 10 RAIL→ROAD.
**Aucun AIR→RAIL** observe. Ce calcul maximise les seuls `rank_score`
publies et ne respecte pas necessairement toutes les priorites de classe
C77, les bonus AIR, les contraintes de financement, ni les candidats hors
top 5. Cela **ne demontre aucune construction contrefactuelle**.

## Contre-verification de calibration physique, profit et ROI

Suivant la precision de `docs/taches.md:98`, on compare aussi quatre
ablations sur les DUEL hors graine : brut, cout seul, profit seul, conjoint.
MAE de cout sur 1 014 constructions physiquement appariees ; MAE du profit
**en £/an**, sur 5 502 lignes-annees matures (profit negatif inclus) ;
ROI seulement sur 4 984 lignes-annees appariees a un cout reel positif.

| Correction | MAE cout £ | MAE profit £/an | Biais profit prédit−réel £/an | MAE ROI (points) | Biais ROI (points) |
|---|---:|---:|---:|---:|---:|
| Brut | 26 710 | 13 245 | +1 884 | 24,054 | +18,834 |
| Cout seul | **10 326** | **13 245** | +1 884 | **17,504** | +1,115 |
| Profit seul | 26 710 | 14 094 | +7 912 | 33,351 | +30,464 |
| Cout + profit | **10 326** | 14 094 | +7 912 | 18,584 | +8,454 |

Le **profit par cargo × distance appris en SOLO aggrave l'erreur absolue
de profit en DUEL** (+850 £/an). La correction conjointe ameliore nettement
le ROI brut, mais **moins que le cout seul** (18,584 contre 17,504 points).
Ne pas confondre reduction moyenne du score et qualite predictive.
La correction du profit accroit aussi le **biais positif de profit** de
1 884 a 7 912 £/an ; le detail des erreurs par cargo × quartile (33 cellules
DUEL) figure dans `ablations_duel.profit_error_by_cargo_quartile` du JSON.
La mediane du Spearman de classement de ROI reel entre lignes **d'une meme
graine**, sur 40 graines, est de **0,7156 brut, 0,6918 cout seul, 0,6871
profit seul et 0,7151 conjoint**. Le modele conjoint ne progresse donc
pas non plus sur l'ordre des lignes construites.

Controle de platitude : mediane `(ROI reel)/(ROI predit)` par quartile :

| Quartile | Brut | Cout seul | Conjoint |
|---|---:|---:|---:|
| Q1 | 0,6695 | 0,8423 | 0,9585 |
| Q2 | 0,6688 | 0,9335 | 0,8309 |
| Q3 | 0,7168 | 1,0909 | 0,8327 |
| Q4 | 0,7081 | 1,1602 | 0,8090 |

En conjoint, le ratio **Q1/Q4 est 1,1848**, alors qu'il etait ~0,946
avant correction : on obtient une pente residuelle d'environ 18 % entre
les extremes, et non une neutralite meilleure en distance. La calibration
ne satisfait donc pas de maniere convaincante le controle de platitude.

## Verdict et prochaine decision

- **Mesure demandee : −17,21 %**, voisine en ordre de grandeur des −20 %
  anticipes, mais la table de profit est non qualifiante hors SOLO.
- **Ne pas activer cette table RAIL dans la selection** et ne pas coder le
  prompt 4 pour le moment. La correction du seul cout ameliore les devis
  mais n'est pas une recalibration economique conjointe, comme le rappelle
  `docs/taches.md:98-106`. L'experimentation de profit RAIL independante
  (RAIL-PROFIT-1) est le prerequis rationnel.
- **Ne pas diminuer AIR de 20 % sur ces seuls chiffres** : la condition de
  proximite est remplie approximativement, mais elle ne remplace pas une
  evaluation economique du RAIL actif. AIR et sa flotte n'ont subi aucune
  modification ici.

Limites : scores du seul top 5, selection des lignes construites non
aleatoire, historiques distincts SOLO/DUEL, aucun cout contrefactuel,
aucune integration budget/K_dec, et dependance des lignes-annees d'une meme
partie. Seul le bootstrap des scores est agrege par **graine**, pas par
les 13 695 lignes top 5 prises pour independantes.
