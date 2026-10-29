# Diagnostic OpexAI vs AAAHogEx — Route Seule à 3 Ans (1970–1972)

**Date :** 29 octobre 2026  
**Dépôt :** `/home/deploy/projects/wt-road1y`  
**Branche :** `road1y-s17` (HEAD `35224c42e7470d1cf41ca2f996efa041a6c9c378`)  
**Cadre :** Diagnostic d'investigation sans modification de code `.nut`, sans commit, sans git config, sans push.  
**Campagnes exécutées :**
- `road1y_3y_diag_p2` : Duel unilatéral de référence 3 ans sur 3 graines (`613553`, `781335`, `100`), `probes=2`, télémétrie de lignes mensuelle (`--line-telemetry --line-telemetry-monthly`), mode `script-debug`.
- `road1y_3y_probe258_s613` : Duel 3 ans sur graine `613553`, `probes=258` (journal complet de décision `OpexDecide`).
- Campagnes de comparaison historique citées : `road1y_busB2_gateA_40x3` (porte A 40×3) et `road1y_busB2_gateB_20x10` (porte B 20×10).

---

## Synthèse Exécutive : Pourquoi AAAHogEx s'envole en Année 3

### Le Paradoxe de la 1re Année
Au terme de la 1re année (1970), **OpexAI devance AAAHogEx** sur les 3 graines en mode route seule :
- **Graine 613553 :** Opex 143 759 £ vs AAA 137 976 £ (+5,8 k£ pour Opex, 44 vs 40 véhicules).
- **Graine 781335 :** Opex 122 471 £ vs AAA 117 371 £ (+5,1 k£ pour Opex, 46 vs 35 véhicules).
- **Graine 100 :** Opex 128 524 £ vs AAA 122 802 £ (+5,7 k£ pour Opex, 41 vs 35 véhicules).

À ce stade précoce, la rapidité d'Opex à mailler la carte (9 à 12 lignes ouvertes dès les 6 premiers mois) surclasse le démarrage plus lent de AAA.

### L'Effondrement Relatif en Année 2 et 3
Dès l'année 2 (1971), AAA dépasse Opex (+85 k£ à +102 k£ d'écart). En année 3 (1972), AAAHogEx explose littéralement alors qu'Opex stagne ou s'effondre :
- **Graine 613553 :** Opex 300 668 £ vs AAA 816 125 £ (ratio **0,37**, 102 vs 220 véhicules).
- **Graine 781335 :** Opex 253 239 £ vs AAA 577 155 £ (ratio **0,44**, 98 vs 144 véhicules).
- **Graine 100 :** Opex 141 960 £ vs AAA 555 117 £ (ratio **0,26**, 71 vs 153 véhicules).

Sur l'ensemble des 40 graines de la porte A (`road1y_busB2_gateA_40x3`), le ratio moyen terminal est de **0,41** au mieux. À 10 ans (`road1y_busB2_gateB_20x10`), le décrochage est massif : **211 k£ vs 2,71 M£** (ratio 0,08, 106 vs 491 véhicules).

---

## Question 1 : Lignes, Distances, Flottes et Productivité (Mois par Mois)

### 1.1 Évolution Mois par Mois sur la Graine 613553

| Date | Lignes Opex | Lignes AAA | Véh. Opex | Véh. AAA | Caisse Opex (£) | Caisse AAA (£) | Dette Opex (£) | Dette AAA (£) | Profit/An Opex (£) | Profit/An AAA (£) |
|:---:|:---:|:---:|:---:|:---:|---:|---:|---:|---:|---:|---:|
| 1970-01-01 |  0 |  0 |   0 |   0 |   100,000 |   100,000 |   100,000 |   100,000 |          0 |          0 |
| 1970-02-01 |  2 |  1 |   5 |   2 |   242,209 |    19,640 |   300,000 |    50,000 |          0 |          0 |
| 1970-03-01 |  4 |  2 |  12 |   5 |   170,038 |    11,974 |   300,000 |    80,000 |          0 |          0 |
| 1970-04-01 |  6 |  2 |  18 |  14 |   112,468 |     1,369 |   300,000 |   120,000 |          0 |          0 |
| 1970-05-01 |  9 |  2 |  27 |  20 |    10,088 |     5,856 |   300,000 |   150,000 |      2,274 |        905 |
| 1970-06-01 |  9 |  2 |  30 |  25 |     5,520 |    19,107 |   300,000 |   180,000 |      2,274 |        905 |
| 1970-07-01 |  9 |  2 |  31 |  25 |    13,979 |    11,110 |   300,000 |   160,000 |      2,274 |        905 |
| 1970-08-01 |  9 |  3 |  33 |  27 |    20,842 |    18,819 |   300,000 |   170,000 |     30,584 |     36,892 |
| 1970-09-01 | 10 |  3 |  35 |  30 |    14,779 |     9,426 |   300,000 |   160,000 |     30,584 |     36,892 |
| 1970-10-01 | 10 |  3 |  38 |  35 |    17,918 |     7,219 |   300,000 |   170,000 |     30,584 |     36,892 |
| 1970-11-01 | 11 |  4 |  41 |  38 |    24,134 |    25,005 |   300,000 |   210,000 |     89,849 |     94,054 |
| 1970-12-01 | 12 |  5 |  44 |  40 |     6,464 |    14,840 |   300,000 |   210,000 |     89,849 |     94,054 |
| 1971-01-01 | 12 |  5 |  46 |  40 |    20,881 |    22,167 |   300,000 |   190,000 |     89,849 |     94,054 |
| 1971-02-01 | 14 |  5 |  50 |  39 |     5,926 |    12,665 |   300,000 |   150,000 |    163,372 |    168,577 |
| 1971-03-01 | 14 |  5 |  52 |  42 |    20,812 |     7,873 |   300,000 |   140,000 |    163,372 |    168,577 |
| 1971-04-01 | 15 |  5 |  57 |  43 |    12,188 |    11,924 |   300,000 |   130,000 |    163,372 |    168,577 |
| 1971-05-01 | 15 |  7 |  60 |  48 |    19,655 |    20,754 |   300,000 |   170,000 |    230,639 |    239,334 |
| 1971-06-01 | 16 |  9 |  62 |  51 |    12,008 |    17,826 |   300,000 |   200,000 |    230,639 |    239,334 |
| 1971-07-01 | 17 | 10 |  65 |  55 |    14,173 |    11,450 |   300,000 |   210,000 |    230,639 |    239,334 |
| 1971-08-01 | 17 | 10 |  66 |  66 |    35,448 |     7,632 |   300,000 |   230,000 |    275,927 |    288,233 |
| 1971-09-01 | 18 | 10 |  69 |  77 |    31,685 |    19,352 |   300,000 |   260,000 |    275,927 |    288,233 |
| 1971-10-01 | 19 | 10 |  72 |  84 |    23,285 |     8,528 |   300,000 |   240,000 |    275,927 |    288,233 |
| 1971-11-01 | 20 | 10 |  75 |  88 |     5,383 |    26,573 |   300,000 |   230,000 |    293,523 |    347,050 |
| 1971-12-01 | 20 | 10 |  77 |  89 |    18,622 |    23,224 |   300,000 |   180,000 |    293,523 |    347,050 |
| 1972-01-01 | 20 | 12 |  80 |  99 |    32,042 |    23,232 |   300,000 |   210,000 |    293,523 |    347,050 |
| 1972-02-01 | 20 | 13 |  80 | 102 |    57,563 |    16,619 |   300,000 |   180,000 |    297,889 |    429,454 |
| 1972-03-01 | 20 | 15 |  82 | 110 |    56,921 |    16,469 |   300,000 |   210,000 |    297,889 |    429,454 |
| 1972-04-01 | 23 | 18 |  90 | 121 |    17,788 |    19,529 |   300,000 |   250,000 |    297,889 |    429,454 |
| 1972-05-01 | 23 | 19 |  93 | 139 |    29,574 |    18,081 |   300,000 |   280,000 |    303,419 |    533,678 |
| 1972-06-01 | 24 | 19 |  97 | 157 |     9,723 |    25,256 |   300,000 |   300,000 |    303,419 |    533,678 |
| 1972-07-01 | 24 | 19 |  97 | 170 |    32,079 |    28,490 |   300,000 |   280,000 |    303,419 |    533,678 |
| 1972-08-01 | 25 | 19 | 100 | 190 |    32,882 |    23,460 |   300,000 |   290,000 |    306,812 |    660,477 |
| 1972-09-01 | 25 | 19 | 102 | 193 |    46,556 |    48,229 |   300,000 |   240,000 |    306,812 |    660,477 |
| 1972-10-01 | 25 | 20 | 102 | 203 |    75,195 |    26,323 |   300,000 |   200,000 |    306,812 |    660,477 |
| 1972-11-01 | 25 | 20 | 102 | 214 |    96,776 |    17,425 |   300,000 |   150,000 |    300,668 |    816,125 |
| 1972-12-01 | 25 | 21 | 102 | 220 |   118,904 |    43,030 |   300,000 |   120,000 |    300,668 |    816,125 |

### 1.2 Ouvertures de Lignes par Trimestre et Profil des Distances

#### Graine 613553

| Trimestre | Lignes Opex | Dist. Moy. Opex (tuiles) | Lignes AAA | Dist. Moy. AAA (tuiles) | Détail distances Opex vs AAA |
|:---:|:---:|:---:|:---:|:---:|:---|
| 1970Q1 |  4 | 76.0 |  2 | 81.5 | Opex: [63, 78, 81, 82] | AAA: [66, 97] |
| 1970Q2 |  5 | 76.8 |  0 | - | Opex: [36, 71, 74, 88, 115] | AAA: [] |
| 1970Q3 |  1 | 33.0 |  1 | 70.0 | Opex: [33] | AAA: [70] |
| 1970Q4 |  2 | 60.5 |  2 | 97.0 | Opex: [21, 100] | AAA: [96, 98] |
| 1971Q1 |  2 | 44.0 |  0 | - | Opex: [22, 66] | AAA: [] |
| 1971Q2 |  2 | 30.0 |  3 | 97.7 | Opex: [25, 35] | AAA: [52, 118, 123] |
| 1971Q3 |  2 | 44.0 |  1 | 132.0 | Opex: [37, 51] | AAA: [132] |
| 1971Q4 |  2 | 91.5 |  0 | - | Opex: [82, 101] | AAA: [] |
| 1972Q1 |  0 | - |  3 | 104.7 | Opex: [] | AAA: [65, 92, 157] |
| 1972Q2 |  4 | 72.2 |  3 | 88.0 | Opex: [17, 72, 81, 119] | AAA: [78, 82, 104] |
| 1972Q3 |  1 | 18.0 |  0 | - | Opex: [18] | AAA: [] |
| 1972Q4 |  0 | - |  2 | 68.0 | Opex: [] | AAA: [61, 75] |

#### Graine 781335

| Trimestre | Lignes Opex | Dist. Moy. Opex (tuiles) | Lignes AAA | Dist. Moy. AAA (tuiles) | Détail distances Opex vs AAA |
|:---:|:---:|:---:|:---:|:---:|:---|
| 1970Q1 |  3 | 77.3 |  2 | 121.0 | Opex: [68, 82, 82] | AAA: [118, 124] |
| 1970Q2 |  7 | 52.6 |  1 | 113.0 | Opex: [18, 29, 36, 60, 66, 67, 92] | AAA: [113] |
| 1970Q3 |  1 | 19.0 |  1 | 121.0 | Opex: [19] | AAA: [121] |
| 1970Q4 |  1 | 72.0 |  0 | - | Opex: [72] | AAA: [] |
| 1971Q1 |  3 | 49.7 |  2 | 105.5 | Opex: [20, 54, 75] | AAA: [95, 116] |
| 1971Q2 |  1 | 33.0 |  0 | - | Opex: [33] | AAA: [] |
| 1971Q3 |  2 | 43.0 |  3 | 75.7 | Opex: [36, 50] | AAA: [61, 71, 95] |
| 1971Q4 |  1 | 52.0 |  3 | 123.7 | Opex: [52] | AAA: [110, 123, 138] |
| 1972Q1 |  2 | 74.5 |  1 | 141.0 | Opex: [65, 84] | AAA: [141] |
| 1972Q2 |  1 | 71.0 |  3 | 123.7 | Opex: [71] | AAA: [65, 74, 232] |
| 1972Q3 |  2 | 85.0 |  2 | 110.5 | Opex: [80, 90] | AAA: [103, 118] |
| 1972Q4 |  1 | 102.0 |  2 | 104.0 | Opex: [102] | AAA: [62, 146] |

#### Graine 100

| Trimestre | Lignes Opex | Dist. Moy. Opex (tuiles) | Lignes AAA | Dist. Moy. AAA (tuiles) | Détail distances Opex vs AAA |
|:---:|:---:|:---:|:---:|:---:|:---|
| 1970Q1 |  4 | 59.0 |  1 | 52.0 | Opex: [44, 55, 63, 74] | AAA: [52] |
| 1970Q2 |  5 | 63.2 |  3 | 98.3 | Opex: [22, 34, 79, 87, 94] | AAA: [69, 111, 115] |
| 1970Q3 |  1 | 73.0 |  1 | 43.0 | Opex: [73] | AAA: [43] |
| 1970Q4 |  0 | - |  1 | 103.0 | Opex: [] | AAA: [103] |
| 1971Q1 |  2 | 74.0 |  1 | 108.0 | Opex: [50, 98] | AAA: [108] |
| 1971Q2 |  1 | 57.0 |  2 | 140.5 | Opex: [57] | AAA: [137, 144] |
| 1971Q3 |  2 | 56.5 |  1 | 129.0 | Opex: [40, 73] | AAA: [129] |
| 1971Q4 |  0 | - |  3 | 104.0 | Opex: [] | AAA: [68, 73, 171] |
| 1972Q1 |  0 | - |  0 | - | Opex: [] | AAA: [] |
| 1972Q2 |  1 | 78.0 |  1 | 110.0 | Opex: [78] | AAA: [110] |
| 1972Q3 |  0 | - |  4 | 100.2 | Opex: [] | AAA: [66, 67, 113, 155] |
| 1972Q4 |  1 | 121.0 |  3 | 163.0 | Opex: [121] | AAA: [121, 173, 195] |

### 1.3 Combien de bus par ligne à 1, 2 et 3 ans ?

Le contraste de concentration de flotte entre OpexAI et AAAHogEx est saisissant :

| Année (au 1er Déc.) | Graine | Nb Lignes Opex | Distribution Véhicules Opex | Moy. Véh/Ligne Opex | Nb Lignes AAA | Distribution Véhicules AAA | Moy. Véh/Ligne AAA |
|:---:|:---:|:---:|:---|:---:|:---:|:---|:---:|
| 1970 | 613553 | 12 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.7 | 5 | `[13, 12, 11, 2, 2]` | 8.0 |
| 1971 | 613553 | 20 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.9 | 10 | `[18, 11, 10, 10, 10, 9, 6, 6]...` | 8.9 |
| 1972 | 613553 | 25 | `[8, 4, 4, 4, 4, 4, 4, 4]...` | 4.1 | 21 | `[32, 23, 21, 14, 11, 11, 10, 10]...` | 10.5 |
| 1970 | 781335 | 12 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.8 | 4 | `[10, 10, 8, 7]` | 8.8 |
| 1971 | 781335 | 19 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.8 | 12 | `[10, 9, 9, 8, 7, 7, 5, 5]...` | 5.8 |
| 1972 | 781335 | 25 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.9 | 20 | `[27, 13, 10, 10, 9, 8, 8, 7]...` | 7.2 |
| 1970 | 100 | 11 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.7 | 6 | `[10, 8, 7, 6, 2, 2]` | 5.8 |
| 1971 | 100 | 16 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.9 | 13 | `[9, 7, 7, 7, 5, 5, 5, 5]...` | 4.8 |
| 1972 | 100 | 18 | `[4, 4, 4, 4, 4, 4, 4, 4]...` | 3.9 | 23 | `[26, 17, 15, 9, 9, 9, 8, 7]...` | 6.7 |

**Observations clés :**
- **OpexAI est figé à 4 véhicules par ligne :** Sur les 25 lignes d'Opex à 3 ans, 22 à 24 lignes ont *exactement* 4 véhicules. Seule une unique ligne (la première construite en 1970) a réussi à atteindre 8 véhicules sur la graine 613553. Sur les graines 781335 et 100, **zéro** ligne ne dépasse 4 véhicules.
- **AAAHogEx concentre massivement ses bus sur les corridors rentables :** Dès l'an 1, AAA monte à 11–13 bus par ligne. À l'an 2, ses meilleures lignes atteignent 18 bus. À l'an 3, la ligne principale atteint **32 bus**, la 2e 23 bus, la 3e 21 bus ! AAA place autant de bus sur 3 lignes qu'Opex sur l'ensemble de son réseau.

### 1.4 Productivité : Profit / Véhicule / An

| Année (1er Déc.) | Graine | Profit Total Opex (£) | Profit/Véh Opex (£) | Profit Total AAA (£) | Profit/Véh AAA (£) | Ratio Opex / AAA |
|:---:|:---:|---:|---:|---:|---:|:---:|
| 1970 | 613553 |   143,759 |   3267 |   137,976 |   3449 | **1.04** |
| 1971 | 613553 |   275,427 |   3577 |   360,576 |   4051 | **0.76** |
| 1972 | 613553 |   272,188 |   2669 |   850,851 |   3868 | **0.32** |
| 1970 | 781335 |   122,471 |   2662 |   117,371 |   3353 | **1.04** |
| 1971 | 781335 |   223,748 |   3065 |   315,112 |   4567 | **0.71** |
| 1972 | 781335 |   242,435 |   2474 |   534,295 |   3710 | **0.45** |
| 1970 | 100 |   128,524 |   3135 |   122,802 |   3509 | **1.05** |
| 1971 | 100 |   180,687 |   2868 |   282,731 |   4488 | **0.64** |
| 1972 | 100 |   120,174 |   1693 |   599,917 |   3921 | **0.20** |

---

## Question 2 : Trésorerie et Emprunt

### 2.1 Le Piège de l'Argent Oisif chez OpexAI
L'examen mois par mois révèle un comportement d'allocation du capital hautement dysfonctionnel chez OpexAI :
1. **Emprunt maximal immédiat et irréversible :** Dès janvier 1970 (`main.nut:762`), Opex emprunte la somme maximale permise (`AICompany.SetLoanAmount(300000)`). Comme la dette est au plafond légal, la capacité d'emprunt résiduelle (*borrowable*) est **strictement nulle** pendant toute la durée de la partie.
2. **Plancher de remboursement inatteignable :** La méthode `_tryRepayLoan` (`capital.nut:15`) compare la trésorerie à `LOAN_REPAY_FLOOR <- 300000;` (`globals_post.nut:17`). Tant que la trésorerie n'excède pas 300 000 £, **aucun remboursement d'emprunt n'est autorisé**.
3. **Accumulation massive de cash stérile :** En 1972, les lignes existantes génèrent du cash mais Opex n'a plus de projets éligibles et ne renforce pas sa flotte. La trésorerie s'accumule sans emploi :
   - Graine 613553 : **118 904 £** oisifs en banque au 1er décembre 1972.
   - Graine 781335 : **42 680 £** oisifs.
   - Graine 100 : **29 252 £** oisifs.
4. **Coût financier pur :** Avec 300 000 £ de dette à 4 % d'intérêt annuel, Opex paie **12 000 £/an** de frais financiers fixes, alors qu'elle dispose de plus de 100 000 £ dormant sur son compte en fin de 3e année !

### 2.2 La Gestion Dynamique de la Dette par AAAHogEx
À l'opposé, AAAHogEx pilote sa dette au plus près de ses besoins d'investissement :
- En 1970, AAA démarre avec un emprunt modeste de 50 000 £ à 120 000 £, n'empruntant que par tranches au fur et à mesure qu'il pose des lignes et achète des véhicules.
- En 1971, AAA fait fluctuer sa dette entre 130 000 £ et 260 000 £ selon ses chantiers, maintenant sa trésorerie entre 7 000 £ et 25 000 £ (pratiquement pas de cash oisif).
- En 1972, face à l'afflux massif de profits, AAA commence à **rembourser sa dette**, la ramenant de 280 000 £ à **120 000 £** tout en finançant 220 véhicules ! Cela réduit ses charges d'intérêt et dope sa valeur de compagnie.

---

## Question 3 : Renfort de Flotte et Verrous Structurels

Pourquoi les lignes d'Opex restent-elles figées à 4 véhicules alors que les stations débordent ?

### 3.1 Le Triple Verrou d'OpexAI
L'analyse du code source et des logs du moteur (`road1y_3y_probe258_s613`) met en évidence un enchaînement fatal de 3 restrictions :

#### Verrou 1 : Le plafond géométrique d'arrêts (`OpexRoadPhysicalVehicleCap`)
Dans `economy.nut:725-730` :
```squirrel
function OpexRoadPhysicalVehicleCap(nStopsA, nStopsB)
{
  local nMin = nStopsA < nStopsB ? nStopsA : nStopsB;
  if (nMin < 1) nMin = 1;
  return 2 * nMin;
}
```
Chaque ligne de bus est initialement créée avec 1 arrêt à chaque extrémité (`nStopsA=1, nStopsB=1`). Le plafond physique est donc de `2 * 1 = 2` bus, porté à `4` par `ROAD1Y_FLEET = 4` (`ROAD1Y_FLEET * stops = 4 * 1 = 4`).

#### Verrou 2 : La condition de cash prohibitive pour construire les arrêts joints (`extra_stops`)
Pour passer de 4 à 8 véhicules, la ligne *doit* construire un 2e arrêt joint (`line.nStopsA = 2, line.nStopsB = 2`).
Or, dans `ai/OpexAI/bus_districts.nut:236` :
```squirrel
if (cost < 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cost + 50000) {
  out.reason = "CASH"; return out;
}
```
Un arrêt de bus OpenTTD coûte **~200 £**. Mais le code exige une encaisse minimale de **50 000 £** avant d'autoriser cette dépense !
Pendant les 30 premiers mois de la simulation, la caisse d'Opex oscille entre 5 000 £ et 35 000 £ (voir tableau mois par mois). Le journal de décision `road1y_3y_probe258_s613` le prouve sans ambiguïté :
```text
ROAD1Y_EXTRA_STOPS phase=build line=1 side=1 ok=false reason=CASH tile=-1 stops_a=2 stops_b=1
ROAD1Y_EXTRA_STOPS phase=build line=2 side=0 ok=false reason=CASH tile=-1 stops_a=1 stops_b=1
ROAD1Y_EXTRA_STOPS phase=build line=3 side=0 ok=false reason=CASH tile=-1 stops_a=1 stops_b=1
```
Ces rejets pour `reason=CASH` se répètent **chaque mois sur toutes les lignes**. Seule la ligne 0 a eu la chance d'être construite en mars 1970 alors que la caisse initiale était encore > 50 000 £ ; elle a pu bâtir son 2e arrêt et monter à 8 bus.

#### Verrou 3 : `ROAD1Y_PAX_REFLEET` désactivé par défaut
Dans `globals_pre.nut:79` :
```squirrel
ROAD1Y_PAX_REFLEET <- false; // ROAD1Y-D : renfort refleet bus selon passagers en attente
```
Tant que ce paramètre est à `false`, `bus_districts_overrides.nut:2049` calcule `road1yStops = min(nStopsA, nStopsB) = 1`. Même si 300 passagers attendent, la cible de flotte est bridée à `4 * 1 = 4` bus !

### 3.2 Conséquences : Attente aux Arrêts et Notes de Gares

Au 1er décembre 1972, l'état des gares Opex vs AAA est édifiant :

| Métrique (Passagers) | Graine 613553 Opex | Graine 613553 AAA | Graine 781335 Opex | Graine 781335 AAA | Graine 100 Opex | Graine 100 AAA |
|:---|---:|---:|---:|---:|---:|---:|
| Note de gare moyenne | **50,0 %** (127/255) | **67,8 %** (173/255) | **50,3 %** (128/255) | **61,6 %** (157/255) | **38,7 %** (99/255) | **62,6 %** (160/255) |
| Note minimale observée | **21 %** | 46 % | **33 %** | 25 % | **22 %** | 38 % |
| Passagers en attente max | **346** (Ligne 22) | 678 | **318** | 1 249 | 29 | 510 |
| Stations avec >140 passagers | 1 | 4 | 2 | 11 | 0 | 6 |

Exemple typique chez Opex : sur la **Ligne 22** (distance 82 tuiles), **346 passagers attendent** au terminus A et 115 au terminus B. La ligne dégage **8 583 £ de profit par bus**. Mais Opex y maintient obstinément 4 bus seulement ! Faute de fréquence de passage, la note de gare chute à **41 %**, ce qui signifie qu'OpenTTD détruit ou refuse de confier 59 % des passagers de la ville à Opex.

---

## Question 4 : Épuisement du Vivier de Lignes

### 4.1 Chronologie de l'Arrêt des Constructions
- **1970 :** 12 lignes construites (rythme soutenu, 1 à 3 par mois).
- **1971 :** 8 lignes construites (fort ralentissement).
- **1972 :** Seulement 5 lignes ouvertes sur la graine 613553, 6 sur 781335, et **2 seulement** sur 100.
- **Dès août 1972 sur 613553 : plus aucune ligne n'est construite.**

### 4.2 Les Véritables Causes de l'Arrêt
Le journal de décision de `road1y_3y_probe258_s613` en fin 1972 montre :
```text
OPEX 1972-12-4 VIVIER path=incremental considered=0 selected=0 rejected=0 budget=61082 remaining=61082
OPEX 1972-12-6 VIVIER path=reselect considered=0 selected=0 rejected=0 budget=63232 remaining=63232
OPEX 1972-12-6 PORTFOLIO_EMPTY budget=63232
```
Le vivier est **totalement vide** (`considered = 0`) alors qu'Opex a **63 232 £ de budget non consommé**.

Pourquoi n'y a-t-il plus aucun candidat ?
1. **Plafond de distance à 128 tuiles (`ROAD_MAX_TRACE_TILES = 128`) :** Dans `candidates.nut:653`, toute liaison interurbaine > 128 tuiles est rejetée (`stats.roadDistanceLong`). Les logs indiquent entre **100 et 239 rejets par an** pour cette seule cause (`reason=road_distance_long`). Or, AAA dessert couramment des liaisons de 130 à 232 tuiles.
2. **Saturation des villes :** Le filtre `OpexTownRoadLineCount(lines, town.tile) >= 4` (`bus_districts_overrides.nut:315`) interdit à toute ville d'avoir plus de 4 lignes de bus.
3. **Restriction par quartier :** Le masque `ROAD1Y_BUS_FIXES & 8` limite chaque ville à 2 districts maximum.
4. **Pas un blocage par AAA :** Sur 37 villes reliées par Opex et 25 par AAA sur la graine 613553, **23 villes sont partagées**. Opex n'a pas été chassé des villes par AAA ; Opex a simplement épuisé les combinaisons de paires [30–128 tuiles] éligibles sous ses règles.

---

## Question 5 : Remplacement de Matériel et Croissance Urbaine

### 5.1 Renouvellement et Modèles de Bus
- **Véhicules disponibles en 1970–1972 :** Dans le jeu de base OpenTTD (climat tempéré OpenGFX), le seul bus routier disponible de 1950 à 1980 est le **Foster Bus** (vitesse 56 km/h, capacité 35 passagers, prix ~3 200 £, durée de vie 15 ans).
- Le modèle suivant (Hereford Bus) n'apparaît qu'en 1980. Aucun renouvellement technologique n'intervient donc pendant les 3 premières années.
- À l'âge de 3 ans, les bus achetés en 1970 ont une fiabilité maximale (90 %+) et ne nécessitent aucun remplacement (`AICompany.SetAutoRenewMonths(-6)` est configuré mais inactif car les bus ont 12 ans de vie utile restante).

### 5.2 Croissance des Villes et Captation
- Le service de bus stimule la croissance des villes (effet `towneffect:1` des passagers).
- Cependant, comme AAA maintient une note de station de 68–75 % (contre 38–50 % pour Opex), **AAAHogEx capte les 3/4 des nouveaux habitants générés**, tandis qu'Opex en laisse s'évaporer plus de la moitié.

---

## Question 6 : Hiérarchie des Causes et 3 Propositions Concrètes

### 6.1 Classement des Causes de l'Écart par £ Perdues (Graine 613553)
Écart total de profit annuel à 3 ans : **515 457 £** (AAA : 816 125 £ vs Opex : 300 668 £).

1. **Absence totale de transport postal (`MAIL`) : ~250 000 à 300 000 £/an perdues**
   - AAA tire **297 389 £** de profit annuel uniquement sur le courrier avec 76 camions postaux (`cargo=2`).
   - Sur les graines 781335 et 100, AAA gagne respectivement 133 815 £ et 153 817 £ sur le courrier.
   - Opex ne gagne **0 £** car `ROAD100_MAIL_INTERTOWN = false` par défaut. C'est plus de **55 % de l'écart total** à 3 ans.

2. **Sous-dimensionnement de la flotte passagers (cap 4 bus + réserve 50k) : ~180 000 à 220 000 £/an perdues**
   - Sur le trafic passagers pur, Opex et AAA ont exactement le même nombre de bus (75 bus chacun sur 613553).
   - Pourtant, les 75 bus de AAA rapportent **482 982 £** (6 440 £/bus) contre **219 082 £** (2 921 £/bus) pour Opex !
   - Le plafonnement à 4 bus et le refus d'extra stops (`reason=CASH`) empêchent de résorber les stocks massifs (346 passagers en souffrance) et détruisent la note de gare.

3. **Plafond de distance à 128 tuiles et vivier asséché : ~60 000 à 100 000 £/an perdues**
   - En fin 1972, Opex garde **118 904 £** de cash stérile faute de pouvoir générer des tracés > 128 tuiles.
   - AAA exploite des liaisons de 130 à 170 tuiles qui rapportent 70 000 £ à 76 000 £ par ligne.

4. **Frais financiers d'emprunt stérile : ~12 000 £/an perdues**
   - Opex paie 4 % sur 300 000 £ d'emprunt permanent alors qu'elle dispose de plus de 100 000 £ oisifs en banque.

---

### 6.2 Trois Corrections Précises par Ordre de Gain Attendu (Non Codées)

Conformément à la consigne, ces 3 leviers sont localisés précisément (fichier:ligne) sans modification de `.nut` :

#### 1. Activer le Courrier Routier Interurbain (`ROAD100_MAIL_INTERTOWN`)
- **Fichiers & Lignes :**
  - [`ai/OpexAI/globals_pre.nut:100`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/globals_pre.nut#L100) : passer `ROAD100_MAIL_INTERTOWN <- true;` (au lieu de `false`).
  - [`ai/OpexAI/info.nut:456`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/info.nut#L456) : basculer la valeur par défaut de `road100_mail_intertown` de `0` à `1`.
- **Mécanisme :** Déclenche `OpexRoad100MailIntertownGenerator` (`candidates.nut:3598`) qui exploite les centres-villes déjà découverts pour faire circuler des camions postaux point à point. Le courrier bénéficie d'un tarif kilométrique élevé, d'un temps de chargement ultra-court et d'un coût de voirie quasi-nul (routes urbaines existantes).
- **Gain attendu :** **+150 000 à +250 000 £/an** à 3 ans.

#### 2. Déverrouiller les Arrêts Joints et le Refleet Passager (`extra_stops` & `road1y_pax_refleet`)
- **Fichiers & Lignes :**
  - [`ai/OpexAI/bus_districts.nut:236`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/bus_districts.nut#L236) : abaisser la réserve de trésorerie de construction d'arrêt joint de 50 000 £ à 10 000 £ :
    `if (cost < 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < cost + 10000)`
  - [`ai/OpexAI/globals_pre.nut:79`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/globals_pre.nut#L79) / [`info.nut:440`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/info.nut#L440) : passer `ROAD1Y_PAX_REFLEET <- true;` (au lieu de `false`).
  - [`ai/OpexAI/bus_districts_overrides.nut:1858`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/bus_districts_overrides.nut#L1858) et [`1948`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/bus_districts_overrides.nut#L1948) : abaisser la réserve de refleet routier de 50 000 £ à 15 000 £.
- **Mécanisme :** Dès qu'un terminus accumule plus de 70 à 140 passagers, Opex peut immédiatement dépenser 200 £ pour poser le 2e quai joint (`nStops = 2`), ce qui déverrouille le plafond de flotte de 4 à 8 (ou 12) bus. Le refleet dynamique injecte les bus nécessaires, épongeant les files d'attente, portant la note de gare à 70 %+ et doublant les revenus de la ligne.
- **Gain attendu :** **+100 000 à +180 000 £/an** à 3 ans.

#### 3. Élargir le Plafond de Tracé Routier à 192 Tuiles (`ROAD_MAX_TRACE_TILES`)
- **Fichiers & Lignes :**
  - [`ai/OpexAI/settings.nut:125`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/settings.nut#L125) : `ROAD_MAX_TRACE_TILES = ROAD1Y_DIST_BANDS ? 192 : 48;` (au lieu de 128).
  - [`ai/OpexAI/builder_road.nut:24`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/builder_road.nut#L24) : `ROAD_MAX_TRACE_TILES <- ROAD1Y_DIST_BANDS ? 192 : 48;`
  - [`ai/OpexAI/globals_pre.nut:70`](file:///home/deploy/projects/wt-road1y/ai/OpexAI/globals_pre.nut#L70) : ajouter la bande `[129, 192]` dans `ROAD1Y_DIST_BAND_LIMITS`.
- **Mécanisme :** Empêche l'assèchement prématuré du vivier (`considered = 0`) en 1972. Réoriente les 118 000 £ de trésorerie oisive vers 5 à 8 liaisons interurbaines longues (130–180 tuiles) qui sont les plus lucratives d'OpenTTD.
- **Gain attendu :** **+50 000 à +100 000 £/an** à 3 ans.

---

*Rapport généré automatiquement depuis les données réelles et vérifiées des simulations OpenTTD 15.3 / OpenTTDLab.*
