# V211 — notre note de performance par composante sur 10 ans (diagnostic 20×10, 16/10)

Campagne `v211s_diag_10x10_20261016` (VPS, branche `v211-score` `3f3ba01`, partie complète,
20 graines × 10 ans, `--script-debug`). Bras `v211` : `v211_rivals_log=1`, seul à journaliser.
Lignes `V211_SCORE` : neuf composantes recalculées comme `UpdateCompanyRatingAndValue` (cibles de
`docs/mecanique_jeu.md` §6). Analyse : `python sweeps/analyze_v211.py <engine> v211`.

Effet du relevé (v211 contre ref) : −132,0 k£/an, médiane −115,8 k, 7/13/0, p = 0,18, IC95
[−312,1 k ; +35,4 k], valeur −2,3 % ; le premier diagnostic donnait +66,4 k (9/11) : bruit de
perturbation d'opcodes, le relevé ne décide rien. Notes finales du banc : OpexAI 887, AAAHogEx 897.

## Lecture

- Le recalcul suit la note officielle à 4-18 points près ; l'écart croît avec la variété de cargo,
  que nous approchons par le cargo principal des véhicules rentables (le courrier des avions et les
  cargos secondaires manquent) : la composante cargo officielle est vraisemblablement 35-45/50.
- En fin de partie, tout est saturé **sauf deux composantes** :
  - **profit minimal des véhicules de plus de 2 ans : 0/100 dès 1975.** Un seul véhicule de plus
    de 730 jours à profit annuel ≤ 0 annule la composante (pleine à 10 000 £). La retraite des
    véhicules déficitaires n'intervient qu'après 3 années consécutives
    (`unprofitable_streak_threshold=3`), donc il en reste toujours un.
  - variété de cargo (proxy 25/50).
- Cargaison livrée, véhicules rentables, gares, trésorerie et emprunt saturent entre 1975 et 1978.
- **Levier « finir premier »** : la note est à égalité avec AAA (ratio 1,00, premiers ~50 % des
  trimestres en 1977-1979) ; 100 points de profit minimal suffiraient à passer devant à coup sûr.

## Données — politique `v211` : 20 parties

### Ratios médians nous / meilleur adversaire et part des parties où nous menons

| année | trimestres | valeur | profit | note | trésorerie | livré | 1er valeur | 1er note | 1er profit |
|---|---|---|---|---|---|---|---|---|---|
| 1970 | 80 | 1.14 | 1.09 | 1.01 | 1.92 | 0.91 | 79% | 57% | 51% |
| 1971 | 80 | 1.30 | 1.22 | 1.00 | 2.01 | 1.07 | 79% | 48% | 69% |
| 1972 | 80 | 1.44 | 1.12 | 1.05 | 2.39 | 1.12 | 84% | 64% | 68% |
| 1973 | 78 | 1.51 | 0.90 | 1.07 | 2.62 | 0.94 | 88% | 69% | 27% |
| 1974 | 79 | 1.39 | 0.75 | 1.04 | 3.59 | 0.87 | 92% | 75% | 14% |
| 1975 | 80 | 1.23 | 0.59 | 1.03 | 2.56 | 0.72 | 82% | 66% | 4% |
| 1976 | 78 | 1.06 | 0.51 | 1.02 | 1.63 | 0.63 | 62% | 67% | 1% |
| 1977 | 80 | 0.88 | 0.45 | 1.00 | 1.06 | 0.56 | 18% | 52% | 0% |
| 1978 | 80 | 0.76 | 0.46 | 1.00 | 0.82 | 0.56 | 5% | 46% | 0% |
| 1979 | 60 | 0.68 | 0.42 | 1.00 | 0.74 | 0.52 | 5% | 52% | 0% |

### Infrastructure médiane (nous / adversaire le plus équipé)

| année | rail | road | stations | airports |
|---|---|---|---|---|
| 1970 | 0 / 1 | 0 / 0 | 14 / 12 | 8 / 8 |
| 1971 | 139 / 304 | 0 / 178 | 52 / 78 | 24 / 22 |
| 1972 | 323 / 1630 | 67 / 828 | 81 / 258 | 35 / 26 |
| 1973 | 709 / 2854 | 137 / 1132 | 111 / 418 | 38 / 30 |
| 1974 | 1035 / 4802 | 214 / 1222 | 126 / 587 | 39 / 34 |
| 1975 | 1393 / 6262 | 228 / 1292 | 147 / 694 | 39 / 34 |
| 1976 | 1576 / 7922 | 228 / 1416 | 154 / 794 | 39 / 36 |
| 1977 | 1801 / 9037 | 228 / 1447 | 160 / 858 | 39 / 36 |
| 1978 | 1932 / 9794 | 229 / 1571 | 163 / 935 | 39 / 36 |
| 1979 | 1972 / 10633 | 230 / 1640 | 163 / 1039 | 39 / 36 |

### Dépassement durable en valeur et en note

| partie | dernier trimestre | valeur dépassée dès | note dépassée dès |
|---|---|---|---|
| v211_seed100_r0.log | 1979-T3 | 1976-T4 | 1975-T1 |
| v211_seed1024_r0.log | 1979-T3 | 1977-T2 | — |
| v211_seed123456_r0.log | 1979-T3 | 1976-T2 | — |
| v211_seed12345_r0.log | 1979-T3 | — | — |
| v211_seed1337_r0.log | 1979-T3 | 1977-T2 | 1979-T3 |
| v211_seed17_r0.log | 1979-T3 | 1976-T3 | 1977-T1 |
| v211_seed1_r0.log | 1979-T3 | 1977-T2 | 1979-T3 |
| v211_seed2026_r0.log | 1979-T3 | 1975-T2 | 1979-T1 |
| v211_seed314_r0.log | 1979-T3 | 1977-T2 | 1978-T3 |
| v211_seed4096_r0.log | 1979-T3 | 1977-T2 | — |
| v211_seed424242_r0.log | 1979-T3 | 1976-T4 | — |
| v211_seed42_r0.log | 1979-T3 | 1977-T4 | 1975-T1 |
| v211_seed512_r0.log | 1979-T3 | 1970-T2 | 1970-T1 |
| v211_seed54321_r0.log | 1979-T3 | 1974-T4 | 1970-T4 |
| v211_seed65537_r0.log | 1979-T3 | 1976-T3 | — |
| v211_seed73_r0.log | 1979-T3 | 1976-T2 | — |
| v211_seed7_r0.log | 1979-T3 | 1976-T4 | 1976-T1 |
| v211_seed8191_r0.log | 1979-T3 | 1977-T3 | 1978-T1 |
| v211_seed8675309_r0.log | 1979-T3 | 1976-T3 | — |
| v211_seed999_r0.log | 1979-T3 | 1975-T2 | — |

### Notre note par composante (points médians, hors relevés de janvier)

| année | vehicles /100 | stations /100 | min_profit /100 | min_income /50 | max_income /100 | delivered /400 | cargo /50 | money /50 | loan_margin /50 | total recalculé | note officielle |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1970 | 0 | 16 | 0 | 0 | 100 | 19 | 0 | 0 | 0 | 138 | 146 |
| 1971 | 7 | 60 | 0 | 0 | 100 | 132 | 6 | 0 | 0 | 312 | 316 |
| 1972 | 34 | 91 | 100 | 0 | 100 | 262 | 12 | 1 | 12 | 643 | 646 |
| 1973 | 61 | 100 | 70 | 50 | 100 | 321 | 18 | 6 | 50 | 756 | 764 |
| 1974 | 90 | 100 | 12 | 50 | 100 | 344 | 22 | 11 | 50 | 788 | 804 |
| 1975 | 100 | 100 | 0 | 50 | 100 | 377 | 25 | 20 | 50 | 820 | 840 |
| 1976 | 100 | 100 | 0 | 50 | 100 | 398 | 25 | 31 | 50 | 852 | 865 |
| 1977 | 100 | 100 | 0 | 50 | 100 | 400 | 25 | 43 | 50 | 865 | 881 |
| 1978 | 100 | 100 | 0 | 50 | 100 | 400 | 25 | 50 | 50 | 875 | 888 |
| 1979 | 100 | 100 | 0 | 50 | 100 | 400 | 25 | 50 | 50 | 875 | 893 |

