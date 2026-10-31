# ESTIM-31 — résultats documentés des trois finalistes 20 graines × 10 ans

**Date de qualification : 30 octobre 2026 — 1970–1979, OpenTTD 15.3,
AAAHogEx-115, carte 256², huit workers, un seul Docker.** Ce rapport
est reconstruit de manière déterministe depuis les archives JSON déjà
publiées ; **aucune nouvelle partie n'a été lancée**.

## 1. Protocole et paramètres figés

- Chaque candidat est qualifié séparément, avec son propre témoin
  `OpexAI[probes=2]` (ancien comportement OFF), contre AAAHogEx.
  **20 graines identiques**, 40/40 parties saines par candidat,
  **dix points annuels** au 1er décembre de 1970 à 1979 pour les
  deux compagnies de chaque bras (`off` et `variant`). Les comptes PLYR
  de 1979 proviennent des sauvegardes finales contrôlées.
- Chaque variante a `estim_unifie=31`, `eb14_progressive=3`,
  `probes=2`, V161 rendement marginal, poids d'a priori **15**,
  profil RAIL **incliné**, `v249_statue=2`, `eb2_fallback=0`,
  `air_load_min_pct=0`, coefficient RAIL **0,75**.
  Seuls le coefficient AIR et/ou le sélecteur moteur C121 changent
  dans ce trio. L'option C121 N1/N2 du troisième n'est **pas** le
  choix moteur exhaustif N1 du gagnant publié.
- **Critère de sélection exclusif** :
  `100 × moyenne20(profit_year OpexAI au 1979-12-01) /
  moyenne20(profit_year AAAHogEx au 1979-12-01)` **dans le même duel**.
  Ne pas prendre la moyenne des 20 ratios individuels ; les ratios
  par graine ci-dessous sont purement descriptifs. Aucun veto
  Wilcoxon/IC95/valeur de société n'entre dans cette élection.
- Le top3 a été **figé après les 40×5**, puis testé sur une
  cohorte **20×10**. Une différence entre variantes
  observée dans deux duels autonomes n'est pas une mesure
  causale directe à adversaire identique : les profits AAA peuvent
  varier d'une campagne à l'autre.

### Configurations individuelles (sources gelées)

| Rang 10 ans | Suite | Coefficient AIR | Coefficient RAIL | Poids | Profil RAIL | Moteur C121 | Rang 40×5 |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | `v161/mix_a200_r075_w15_slope` | 2,00 | 0,75 | 15,00 | incliné | **N1 complet** | 3 |
| 2 | `v161coeff/v161_a250_r075_w15` | 2,50 | 0,75 | 15,00 | incliné | **N1 complet** | 2 |
| 3 | `v161cap/mix_a200_r075_w15_slope` | 2,00 | 0,75 | 15,00 | incliné | **N1/N2** | 1 |

## 2. Classement économique — 1979 et changement de rang

| Rang à 10 ans | Variante | 40×5 / 1974 | 20×10 / 1979 | Profit Opex 1979 (£/an) | Profit AAA 1979 (£/an) | Écart Opex−AAA (£/an) | Victoires / 20 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | V161 AIR 2,00 / RAIL 0,75 — **variante élue** | 103,798667198 % | **66,557726256 %** | 4 255 528,00 | 6 393 740,05 | -2 138 212,05 | 1 |
| 2 | V161 AIR 2,50 / RAIL 0,75 — coefficient AIR augmenté | 105,171758309 % | 65,921947052 % | 4 225 862,90 | 6 410 403,65 | -2 184 540,75 | 1 |
| 3 | V161 AIR 2,00 / RAIL 0,75 × C121 N1/N2 — choix moteur étendu | 106,062928693 % | 65,188575006 % | 4 290 978,40 | 6 582 408,65 | -2 291 430,25 | 0 |

**Changement de classement :** N1/N2 passe de **1er**
sur 40×5 à **3e** sur 20×10 ; le V161 N1 AIR2,00 passe de
**3e** à **1er**. Les résultats décennaux montrent un
décrochage partagé à partir de 1975. Le classement est
celui **effectivement observé**, pas une preuve que
le remplacement N1 par N1/N2 cause à lui seul ce décrochage.

### Témoins OFF propres aux trois duels à 10 ans

| Variante | Ratio OFF (20×10) | Ratio ON (20×10) | Écart descriptif (points) | Profit Opex OFF | Profit AAA OFF |
| --- | ---: | ---: | ---: | ---: | ---: |
| `v161` | 58,856104 % | 66,557726 % | +7,701622 | 4 019 123,30 | 6 828 728,05 |
| `v161coeff` | 58,778124 % | 65,921947 % | +7,143823 | 4 059 112,60 | 6 905 821,95 |
| `v161cap` | 58,589440 % | 65,188575 % | +6,599135 | 4 038 345,35 | 6 892 616,35 |

Le bras OFF permet de situer chaque politique par rapport
à la référence historique du **propre essai**. Ses données
ne doivent pas être combinées avec un bras d'une autre
campagne comme un essai causal strictement synchronisé.

## 3. Résultats complets, variante par variante

### 1. V161 AIR 2,00 / RAIL 0,75 — **variante élue**

**Identité :** `v161/mix_a200_r075_w15_slope` ; campagne
`estim31ten_estim31v161_mix_a200_r075_w15_slope_20x10_20261030` ; **source SHA-256** :
`15078ee31b595f31c9deb054de58cd88edeb72ed9e1eafc9b03463535a28f879`. Les états Opex/AAA sont tous
issus de cette campagne, pas d'un adversaire emprunté à
l'une des deux autres.

**Bilan final :** 66,557726256 % AAAHogEx ;
Opex **4 255 528,00 £/an**, AAA
**6 393 740,05 £/an** ; différence
**-2 138 212,05 £/an** ;
**1/20** graines où Opex gagne.

#### Trajectoire annuelle (1er décembre, moyennes sur 20 graines)

| Année | Opex (£/an) | AAA (£/an) | Opex/AAA | OFF/AAA | Avions Opex/AAA | Trains Opex/AAA | Aéroports Opex/AAA | Caisse Opex (£) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1970 | 368 201,85 | 312 079,60 | 117,98 % | 121,08 % | 10,30/11,80 | 0,00/0,40 | 14,45/12,55 | 49 309,85 |
| 1971 | 1 735 330,80 | 1 337 757,35 | 129,72 % | 128,60 % | 35,90/24,20 | 8,60/5,50 | 27,05/24,10 | 109 895,90 |
| 1972 | 2 536 714,15 | 1 928 151,40 | 131,56 % | 123,21 % | 52,90/29,00 | 19,80/10,90 | 30,95/26,40 | 262 801,05 |
| 1973 | 2 757 099,30 | 2 420 683,45 | 113,90 % | 105,89 % | 67,65/36,90 | 23,05/18,30 | 32,45/31,40 | 530 245,15 |
| 1974 | 2 912 643,40 | 2 821 333,70 | 103,24 % | 93,38 % | 78,45/40,05 | 24,50/26,25 | 33,25/33,95 | 1 039 187,70 |
| 1975 | 3 135 781,70 | 3 528 206,60 | 88,88 % | 84,49 % | 81,70/40,55 | 25,90/31,50 | 33,70/34,55 | 2 127 775,15 |
| 1976 | 3 414 754,75 | 4 226 155,70 | 80,80 % | 76,30 % | 84,60/42,30 | 27,20/39,75 | 33,80/35,35 | 4 140 625,15 |
| 1977 | 3 695 687,60 | 5 020 180,95 | 73,62 % | 67,28 % | 84,65/44,90 | 28,35/44,35 | 34,15/35,70 | 7 255 716,80 |
| 1978 | 3 962 027,30 | 5 622 584,60 | 70,47 % | 63,23 % | 84,80/45,70 | 29,10/51,60 | 34,20/35,95 | 10 780 632,85 |
| 1979 | 4 255 528,00 | 6 393 740,05 | 66,56 % | 58,86 % | 84,25/48,00 | 29,55/56,25 | 34,30/36,20 | 14 742 506,80 |

#### Parc, couverture et trésorerie au 01/12/1979

| Indicateur | OpexAI | AAAHogEx |
| --- | ---: | ---: |
| Avions (stock) | 84,25 | 48,00 |
| Trains (stock) | 29,55 | 56,25 |
| Aéroports | 34,30 | 36,20 |
| Villes avec aéroport | 33,75 | 33,75 |
| Caisse (£) | 14 742 506,80 | 17 868 005,00 |
| Prêt en cours (£) | 0,00 | 0,00 |
| Moteur AIR 223 (stock survivant) | 15,75 | 5,45 |
| Moteur AIR 228 (stock survivant) | 6,80 | 13,05 |
| Moteur AIR 220 (stock survivant) | 0,55 | 2,25 |

#### Écritures PLYR réellement enregistrées — 1979 YTD au 1er décembre

Source : [`estim31_ten_v161_accounts_1979_20261030.json`](estim31_ten_v161_accounts_1979_20261030.json).
Les recettes sont présentées en valeur positive (le
fichier PLYR stocke les recettes avec un signe négatif) ;
les dépenses sont des écritures **nettes**.

| Poste moyen (£/monde) | OpexAI | AAAHogEx |
| --- | ---: | ---: |
| Recettes AIR | 3 578 481,75 | 4 435 714,35 |
| Recettes RAIL | 799 231,15 | 1 967 012,70 |
| Recettes ROUTE | 537,65 | 9 243,55 |
| Recettes NAVAL | 3 802,35 | 2 361,90 |
| Exploitation AIR | 370 912,00 | 277 835,00 |
| Exploitation RAIL | 70 229,90 | 106 229,10 |
| Exploitation ROUTE | 93,35 | 73 540,80 |
| Exploitation NAVAL | 284,90 | 1 709,00 |
| Construction tous modes | 60 677,45 | 212 986,40 |
| Véhicules neufs moins ventes, tous modes | 167 348,70 | 719 492,75 |
| Autres (y compris actions municipales) | 77 715,25 | 139 546,00 |
| Intérêts d'emprunt | 0,00 | 0,00 |

#### Les vingt paires de graines — profit annuel 1979

La colonne « ratio individuel » est **descriptive** et
n'est **pas** la métrique de classement, laquelle
repose sur le ratio **des deux moyennes**.

| Graine | OpexAI (£/an) | AAAHogEx (£/an) | Écart Opex−AAA (£/an) | Ratio individuel |
| ---: | ---: | ---: | ---: | ---: |
| 42 | 3 943 550,00 | 7 392 457,00 | -3 448 907,00 | 53,35 % |
| 100 | 2 987 282,00 | 4 411 821,00 | -1 424 539,00 | 67,71 % |
| 7 | 4 980 089,00 | 7 493 379,00 | -2 513 290,00 | 66,46 % |
| 999 | 5 285 011,00 | 7 073 870,00 | -1 788 859,00 | 74,71 % |
| 2026 | 4 533 804,00 | 8 365 440,00 | -3 831 636,00 | 54,20 % |
| 1 | 4 956 293,00 | 6 897 904,00 | -1 941 611,00 | 71,85 % |
| 17 | 3 712 029,00 | 4 460 248,00 | -748 219,00 | 83,22 % |
| 73 | 5 646 709,00 | 6 711 909,00 | -1 065 200,00 | 84,13 % |
| 314 | 4 874 844,00 | 8 256 733,00 | -3 381 889,00 | 59,04 % |
| 512 | 2 915 384,00 | 6 816 988,00 | -3 901 604,00 | 42,77 % |
| 1024 | 3 566 887,00 | 5 610 594,00 | -2 043 707,00 | 63,57 % |
| 1337 | 3 601 643,00 | 7 729 720,00 | -4 128 077,00 | 46,59 % |
| 4096 | 4 752 101,00 | 6 903 885,00 | -2 151 784,00 | 68,83 % |
| 8191 | 4 260 240,00 | 6 722 193,00 | -2 461 953,00 | 63,38 % |
| 12345 | 4 028 185,00 | 4 800 044,00 | -771 859,00 | 83,92 % |
| 54321 | 3 735 962,00 | 4 064 924,00 | -328 962,00 | 91,91 % |
| 65537 | 3 933 258,00 | 6 504 711,00 | -2 571 453,00 | 60,47 % |
| 123456 | 4 884 904,00 | 3 437 391,00 | 1 447 513,00 | 142,11 % |
| 424242 | 4 165 708,00 | 6 804 236,00 | -2 638 528,00 | 61,22 % |
| 8675309 | 4 346 677,00 | 7 416 354,00 | -3 069 677,00 | 58,61 % |

**Limites de l'interprétation de cette variante :**
les stocks de moteurs sont **survivants à une date** et
non des achats ; les achats de véhicules PLYR sont
**nets des ventes** et **tous modes confondus** ;
« Autres » comprend les actions municipales sans
les attribuer uniquement aux statues. Les opcodes
observés dans ces qualifications sont **partiels**
(`opcodes_complete_all=false`), non une mesure du CPU
global. Aucune ventilation des revenus par ligne
ou du profit marginal d'un avion/train n'est prouvée
par ces tableaux.

### 2. V161 AIR 2,50 / RAIL 0,75 — coefficient AIR augmenté

**Identité :** `v161coeff/v161_a250_r075_w15` ; campagne
`estim31ten_estim31vcoef_v161_a250_r075_w15_20x10_20261030` ; **source SHA-256** :
`10d21056814b32f8672db28c7d6016538904ae335e1fa7c22bef0dfbd00527ec`. Les états Opex/AAA sont tous
issus de cette campagne, pas d'un adversaire emprunté à
l'une des deux autres.

**Bilan final :** 65,921947052 % AAAHogEx ;
Opex **4 225 862,90 £/an**, AAA
**6 410 403,65 £/an** ; différence
**-2 184 540,75 £/an** ;
**1/20** graines où Opex gagne.

#### Trajectoire annuelle (1er décembre, moyennes sur 20 graines)

| Année | Opex (£/an) | AAA (£/an) | Opex/AAA | OFF/AAA | Avions Opex/AAA | Trains Opex/AAA | Aéroports Opex/AAA | Caisse Opex (£) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1970 | 368 178,20 | 312 075,95 | 117,98 % | 121,08 % | 10,25/11,75 | 0,00/0,40 | 14,40/12,55 | 52 338,45 |
| 1971 | 1 729 317,20 | 1 328 152,45 | 130,20 % | 128,60 % | 35,10/23,80 | 8,90/5,55 | 26,80/24,10 | 128 495,65 |
| 1972 | 2 514 856,10 | 1 937 054,80 | 129,83 % | 123,22 % | 52,80/29,20 | 20,00/10,75 | 30,70/26,80 | 251 410,55 |
| 1973 | 2 690 813,05 | 2 379 154,90 | 113,10 % | 106,13 % | 67,05/36,85 | 23,15/19,40 | 32,10/32,00 | 489 441,55 |
| 1974 | 2 868 143,20 | 2 786 735,80 | 102,92 % | 94,68 % | 77,50/38,35 | 24,70/28,75 | 32,65/33,20 | 965 531,80 |
| 1975 | 3 104 372,00 | 3 542 238,85 | 87,64 % | 83,60 % | 81,35/39,35 | 25,85/37,25 | 33,35/33,65 | 2 171 516,25 |
| 1976 | 3 400 814,25 | 4 375 705,70 | 77,72 % | 77,48 % | 82,85/42,80 | 26,60/43,00 | 33,70/34,35 | 4 274 941,70 |
| 1977 | 3 662 580,55 | 5 098 464,45 | 71,84 % | 67,66 % | 83,35/44,95 | 27,20/50,60 | 33,75/35,00 | 7 237 731,05 |
| 1978 | 3 965 239,95 | 5 751 254,20 | 68,95 % | 65,73 % | 83,00/46,60 | 28,45/56,10 | 33,75/35,30 | 10 716 052,60 |
| 1979 | 4 225 862,90 | 6 410 403,65 | 65,92 % | 58,78 % | 82,70/50,05 | 29,20/63,25 | 34,05/36,00 | 14 601 760,80 |

#### Parc, couverture et trésorerie au 01/12/1979

| Indicateur | OpexAI | AAAHogEx |
| --- | ---: | ---: |
| Avions (stock) | 82,70 | 50,05 |
| Trains (stock) | 29,20 | 63,25 |
| Aéroports | 34,05 | 36,00 |
| Villes avec aéroport | 33,40 | 33,40 |
| Caisse (£) | 14 601 760,80 | 17 483 905,50 |
| Prêt en cours (£) | 0,00 | 0,00 |
| Moteur AIR 223 (stock survivant) | 15,60 | 4,70 |
| Moteur AIR 228 (stock survivant) | 8,05 | 17,20 |
| Moteur AIR 220 (stock survivant) | 0,70 | 1,95 |

#### Écritures PLYR réellement enregistrées — 1979 YTD au 1er décembre

Source : [`estim31_ten_v161a250_accounts_1979_20261030.json`](estim31_ten_v161a250_accounts_1979_20261030.json).
Les recettes sont présentées en valeur positive (le
fichier PLYR stocke les recettes avec un signe négatif) ;
les dépenses sont des écritures **nettes**.

| Poste moyen (£/monde) | OpexAI | AAAHogEx |
| --- | ---: | ---: |
| Recettes AIR | 3 557 309,40 | 4 424 964,25 |
| Recettes RAIL | 772 293,95 | 2 156 744,55 |
| Recettes ROUTE | 732,45 | 5 295,50 |
| Recettes NAVAL | 2 102,35 | 7 413,75 |
| Exploitation AIR | 372 329,10 | 287 746,40 |
| Exploitation RAIL | 68 108,35 | 115 226,50 |
| Exploitation ROUTE | 127,00 | 76 631,30 |
| Exploitation NAVAL | 142,50 | 2 487,45 |
| Construction tous modes | 34 087,50 | 260 926,15 |
| Véhicules neufs moins ventes, tous modes | 215 174,25 | 1 093 741,55 |
| Autres (y compris actions municipales) | 78 043,00 | 186 634,75 |
| Intérêts d'emprunt | 0,00 | 0,00 |

#### Les vingt paires de graines — profit annuel 1979

La colonne « ratio individuel » est **descriptive** et
n'est **pas** la métrique de classement, laquelle
repose sur le ratio **des deux moyennes**.

| Graine | OpexAI (£/an) | AAAHogEx (£/an) | Écart Opex−AAA (£/an) | Ratio individuel |
| ---: | ---: | ---: | ---: | ---: |
| 42 | 3 815 065,00 | 6 223 025,00 | -2 407 960,00 | 61,31 % |
| 100 | 2 985 782,00 | 5 549 820,00 | -2 564 038,00 | 53,80 % |
| 7 | 4 677 426,00 | 7 750 909,00 | -3 073 483,00 | 60,35 % |
| 999 | 5 453 033,00 | 6 203 477,00 | -750 444,00 | 87,90 % |
| 2026 | 4 656 753,00 | 7 371 693,00 | -2 714 940,00 | 63,17 % |
| 1 | 4 839 112,00 | 5 833 193,00 | -994 081,00 | 82,96 % |
| 17 | 3 363 099,00 | 4 262 531,00 | -899 432,00 | 78,90 % |
| 73 | 5 323 617,00 | 8 423 861,00 | -3 100 244,00 | 63,20 % |
| 314 | 5 101 153,00 | 9 185 742,00 | -4 084 589,00 | 55,53 % |
| 512 | 3 119 331,00 | 6 891 912,00 | -3 772 581,00 | 45,26 % |
| 1024 | 3 095 695,00 | 5 550 488,00 | -2 454 793,00 | 55,77 % |
| 1337 | 3 631 550,00 | 7 509 657,00 | -3 878 107,00 | 48,36 % |
| 4096 | 4 436 264,00 | 8 277 685,00 | -3 841 421,00 | 53,59 % |
| 8191 | 4 150 709,00 | 5 865 883,00 | -1 715 174,00 | 70,76 % |
| 12345 | 4 198 509,00 | 4 298 756,00 | -100 247,00 | 97,67 % |
| 54321 | 3 429 522,00 | 4 952 970,00 | -1 523 448,00 | 69,24 % |
| 65537 | 3 859 219,00 | 6 276 847,00 | -2 417 628,00 | 61,48 % |
| 123456 | 4 759 304,00 | 4 057 555,00 | 701 749,00 | 117,29 % |
| 424242 | 5 091 412,00 | 6 140 839,00 | -1 049 427,00 | 82,91 % |
| 8675309 | 4 530 703,00 | 7 581 230,00 | -3 050 527,00 | 59,76 % |

**Limites de l'interprétation de cette variante :**
les stocks de moteurs sont **survivants à une date** et
non des achats ; les achats de véhicules PLYR sont
**nets des ventes** et **tous modes confondus** ;
« Autres » comprend les actions municipales sans
les attribuer uniquement aux statues. Les opcodes
observés dans ces qualifications sont **partiels**
(`opcodes_complete_all=false`), non une mesure du CPU
global. Aucune ventilation des revenus par ligne
ou du profit marginal d'un avion/train n'est prouvée
par ces tableaux.

### 3. V161 AIR 2,00 / RAIL 0,75 × C121 N1/N2 — choix moteur étendu

**Identité :** `v161cap/mix_a200_r075_w15_slope` ; campagne
`estim31ten_estim31vcap_mix_a200_r075_w15_slope_20x10_20261030` ; **source SHA-256** :
`183187e6b60f442edf3f0ea7eaa556cfccb4729aed185f1ddf12298e242711c9`. Les états Opex/AAA sont tous
issus de cette campagne, pas d'un adversaire emprunté à
l'une des deux autres.

**Bilan final :** 65,188575006 % AAAHogEx ;
Opex **4 290 978,40 £/an**, AAA
**6 582 408,65 £/an** ; différence
**-2 291 430,25 £/an** ;
**0/20** graines où Opex gagne.

#### Trajectoire annuelle (1er décembre, moyennes sur 20 graines)

| Année | Opex (£/an) | AAA (£/an) | Opex/AAA | OFF/AAA | Avions Opex/AAA | Trains Opex/AAA | Aéroports Opex/AAA | Caisse Opex (£) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1970 | 387 018,45 | 307 731,05 | 125,77 % | 121,08 % | 11,10/11,50 | 0,00/0,45 | 15,90/12,25 | 37 935,55 |
| 1971 | 1 796 746,95 | 1 298 356,30 | 138,39 % | 128,60 % | 39,65/22,90 | 9,45/5,80 | 29,70/24,00 | 117 926,80 |
| 1972 | 2 698 299,00 | 1 900 980,40 | 141,94 % | 123,22 % | 55,80/29,35 | 20,50/12,10 | 31,90/26,90 | 350 673,00 |
| 1973 | 2 834 773,80 | 2 455 038,45 | 115,47 % | 106,09 % | 69,75/38,00 | 23,00/18,10 | 32,75/32,35 | 473 538,25 |
| 1974 | 3 022 441,65 | 2 841 351,05 | 106,37 % | 92,97 % | 78,45/39,85 | 24,20/26,05 | 33,10/33,00 | 1 095 044,40 |
| 1975 | 3 258 723,50 | 3 457 162,45 | 94,26 % | 82,15 % | 82,10/38,70 | 25,00/32,85 | 33,75/33,40 | 2 486 503,90 |
| 1976 | 3 534 185,00 | 4 211 807,90 | 83,91 % | 76,12 % | 83,40/41,35 | 25,40/40,60 | 34,00/33,90 | 4 995 897,00 |
| 1977 | 3 830 083,05 | 5 070 545,20 | 75,54 % | 68,61 % | 84,50/44,25 | 26,35/48,75 | 34,35/34,50 | 8 365 902,80 |
| 1978 | 4 100 142,95 | 5 851 313,85 | 70,07 % | 63,20 % | 84,95/46,35 | 27,40/55,50 | 34,50/35,30 | 12 059 949,30 |
| 1979 | 4 290 978,40 | 6 582 408,65 | 65,19 % | 58,59 % | 84,95/49,25 | 27,95/59,45 | 34,90/35,60 | 16 072 476,05 |

#### Parc, couverture et trésorerie au 01/12/1979

| Indicateur | OpexAI | AAAHogEx |
| --- | ---: | ---: |
| Avions (stock) | 84,95 | 49,25 |
| Trains (stock) | 27,95 | 59,45 |
| Aéroports | 34,90 | 35,60 |
| Villes avec aéroport | 34,10 | 34,10 |
| Caisse (£) | 16 072 476,05 | 18 341 902,25 |
| Prêt en cours (£) | 0,00 | 0,00 |
| Moteur AIR 223 (stock survivant) | 15,35 | 6,10 |
| Moteur AIR 228 (stock survivant) | 0,60 | 12,70 |
| Moteur AIR 220 (stock survivant) | 7,05 | 2,75 |

#### Écritures PLYR réellement enregistrées — 1979 YTD au 1er décembre

Source : [`estim31_ten_motorcap_accounts_1979_20261030.json`](estim31_ten_motorcap_accounts_1979_20261030.json).
Les recettes sont présentées en valeur positive (le
fichier PLYR stocke les recettes avec un signe négatif) ;
les dépenses sont des écritures **nettes**.

| Poste moyen (£/monde) | OpexAI | AAAHogEx |
| --- | ---: | ---: |
| Recettes AIR | 3 631 907,45 | 4 463 360,65 |
| Recettes RAIL | 783 915,65 | 2 132 625,75 |
| Recettes ROUTE | 492,35 | 13 031,70 |
| Recettes NAVAL | 1 943,10 | 3 377,55 |
| Exploitation AIR | 376 008,50 | 286 256,40 |
| Exploitation RAIL | 65 795,40 | 114 660,80 |
| Exploitation ROUTE | 38,30 | 77 932,55 |
| Exploitation NAVAL | 143,20 | 1 337,65 |
| Construction tous modes | 12 114,50 | 207 117,25 |
| Véhicules neufs moins ventes, tous modes | 232 734,25 | 772 205,85 |
| Autres (y compris actions municipales) | 21 566,50 | 118 185,25 |
| Intérêts d'emprunt | 0,00 | 0,00 |

#### Les vingt paires de graines — profit annuel 1979

La colonne « ratio individuel » est **descriptive** et
n'est **pas** la métrique de classement, laquelle
repose sur le ratio **des deux moyennes**.

| Graine | OpexAI (£/an) | AAAHogEx (£/an) | Écart Opex−AAA (£/an) | Ratio individuel |
| ---: | ---: | ---: | ---: | ---: |
| 42 | 3 312 983,00 | 6 030 248,00 | -2 717 265,00 | 54,94 % |
| 100 | 3 124 470,00 | 3 495 608,00 | -371 138,00 | 89,38 % |
| 7 | 4 824 106,00 | 7 258 196,00 | -2 434 090,00 | 66,46 % |
| 999 | 4 912 570,00 | 7 414 778,00 | -2 502 208,00 | 66,25 % |
| 2026 | 4 284 887,00 | 8 109 182,00 | -3 824 295,00 | 52,84 % |
| 1 | 5 067 427,00 | 8 280 053,00 | -3 212 626,00 | 61,20 % |
| 17 | 3 474 314,00 | 6 657 601,00 | -3 183 287,00 | 52,19 % |
| 73 | 5 090 863,00 | 6 874 021,00 | -1 783 158,00 | 74,06 % |
| 314 | 4 662 665,00 | 8 362 385,00 | -3 699 720,00 | 55,76 % |
| 512 | 3 400 558,00 | 7 587 308,00 | -4 186 750,00 | 44,82 % |
| 1024 | 3 621 085,00 | 4 910 847,00 | -1 289 762,00 | 73,74 % |
| 1337 | 4 250 707,00 | 7 489 704,00 | -3 238 997,00 | 56,75 % |
| 4096 | 5 588 873,00 | 6 718 518,00 | -1 129 645,00 | 83,19 % |
| 8191 | 4 070 167,00 | 6 185 466,00 | -2 115 299,00 | 65,80 % |
| 12345 | 4 309 594,00 | 4 593 479,00 | -283 885,00 | 93,82 % |
| 54321 | 3 542 912,00 | 6 632 245,00 | -3 089 333,00 | 53,42 % |
| 65537 | 3 862 654,00 | 6 070 995,00 | -2 208 341,00 | 63,62 % |
| 123456 | 4 562 719,00 | 5 912 042,00 | -1 349 323,00 | 77,18 % |
| 424242 | 5 171 122,00 | 6 112 691,00 | -941 569,00 | 84,60 % |
| 8675309 | 4 684 892,00 | 6 952 806,00 | -2 267 914,00 | 67,38 % |

**Limites de l'interprétation de cette variante :**
les stocks de moteurs sont **survivants à une date** et
non des achats ; les achats de véhicules PLYR sont
**nets des ventes** et **tous modes confondus** ;
« Autres » comprend les actions municipales sans
les attribuer uniquement aux statues. Les opcodes
observés dans ces qualifications sont **partiels**
(`opcodes_complete_all=false`), non une mesure du CPU
global. Aucune ventilation des revenus par ligne
ou du profit marginal d'un avion/train n'est prouvée
par ces tableaux.

## 4. Conclusions documentaires et suites

1. Le **défaut élu est bien le rang 1 à dix ans** :
   `v161/mix_a200_r075_w15_slope`, AIR2,00, RAIL0,75,
   poids15, pente RAIL, V161 same-engine, C121 scan
   **N1 exhaustif**, `estim_unifie=31`, EB14=3 et `probes=2`.
   La variante AIR2,50 et la variante N1/N2 sont
   **mesurées mais non adoptées**, et leurs verdicts
   ne doivent pas être rouverts en tant que simple
   nouveau candidat sans nouvelle hypothèse.
2. Les trois trajectoires passent de plus de **100 %**
   à moins de **100 %** entre le 1er décembre 1974 et
   celui de 1975, et convergent vers **65–67 %** en
   1979. Le phénomène est **commun** aux trois variantes,
   pas un incident propre au sélecteur C121 N1/N2.
3. Les stocks ferroviaires croissent peu chez Opex
   relativement à AAA, alors qu'Opex conserve une
   trésorerie importante. En AIR, plus d'avions ne
   signifie pas plus de recettes. Ce sont des
   **symptômes**, non la preuve qu'une extension ou
   réduction de flotte supplémentaire serait rentable.
4. La priorité de diagnostic reste **POST-1974-ENTONNOIR**
   puis **RAIL-RENDEMENT-TARDIF** et **AIR-PRODUCTIVITÉ**.
   Un nouveau `1×10` loggé ne sera envisagé que si les
   artefacts déjà conservés ne permettent pas de
   distinguer les motifs exacts de rejet tardif.

Références de travail : [liste active](taches.md),
[analyse des priorités](estim31_priorites_20x10_20261030.md),
[protocole et promotion](estim31_phase_combinatoire_20261030.md),
[validation du défaut](estim31_default_validation_20261030.md).

## 5. Sources immuables et reproduction

Sources **déjà archivées**, aucune campagne redémarrée :

- [`estim31_top3_20x10_20261030.json`](estim31_top3_20x10_20261030.json)
- [`estim31_top3_decade_trajectory_20261030.json`](estim31_top3_decade_trajectory_20261030.json)
- [`estim31_top3_frozen_20261030.json`](estim31_top3_frozen_20261030.json)
- [`estim31_ten_v161_accounts_1979_20261030.json`](estim31_ten_v161_accounts_1979_20261030.json)
- [`estim31_ten_v161a250_accounts_1979_20261030.json`](estim31_ten_v161a250_accounts_1979_20261030.json)
- [`estim31_ten_motorcap_accounts_1979_20261030.json`](estim31_ten_motorcap_accounts_1979_20261030.json)

Le rapport est généré par
[`sweeps/estim31_document_three_finalists_20261030.py`](../sweeps/estim31_document_three_finalists_20261030.py).
Pour le reproduire :

```powershell
python -X utf8 sweeps/estim31_document_three_finalists_20261030.py
python -X utf8 sweeps/estim31_document_three_finalists_20261030.py --check
```
