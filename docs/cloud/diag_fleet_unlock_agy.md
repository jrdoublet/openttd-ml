# Rapport d'Autopsie Économique et Diagnostic : Flotte Bus Road1y (`road1y_fleet_unlock`)

**Date :** 29 octobre 2026  
**Dépôt :** `/home/deploy/projects/wt-road1y` (branche `road1y-s17`, commit `e32fac22`)  
**Auteur du diagnostic :** Antigravity  
**Fichiers analysés :** `results/road1y_unlock_{off,3,4,5,12,15}.json(l)` et journaux moteurs associés  
**Campagnes exécutées :** `road1y_unlock_4`, `road1y_unlock_5`, `road1y_unlock_12` (mesures 3 ans, graines 100, 613553, 781335)

---

## 1. Synthèse Exécutive et Verdict

Le rapport précédent (`agy_flotte3_rapport.md`) présentait le déverrouillage de la flotte sous le masque 15 (`road1y_fleet_unlock=15`) comme un succès en mettant en avant la hausse de la valeur de compagnie (+20 %, atteignant 454 k£ contre 379 k£) et le nombre de bus déployés (107 vs 88).

**Ce constat était trompeur car la valeur de compagnie n'est pas l'objectif économique du projet : seul le profit compte.**
Une autopsie financière et physique rigoureuse révèle :
1. **Effondrement du profit d'exploitation :** Le profit annuel chute de **-22,3 %** (passant de **232 233 £/an** à **180 350 £/an**, en recul unanime sur 3/3 graines).
2. **Atrophie du réseau (-7 à -8 lignes) :** OpexAI n'exploite plus que **16 lignes** en moyenne au lieu de **22,3 lignes** (17 vs 25 sur la graine 613553, 17 vs 24 sur 781335, 14 vs 18 sur 100).
3. **Le piège de trésorerie :** En achetant des bus supplémentaires dès que la caisse atteint 10 000 £, l'algorithme siphonne en continu la trésorerie mensuelle (~3 500 £ par bus). Il empêche la compagnie d'accumuler le capital forfaitaire (~20 000 £ à 22 000 £) nécessaire à l'ouverture de nouvelles lignes dans le portefeuille.
4. **Rendement marginal médiocre voire négatif :** Sur les lignes passées de 4 à 8 bus, les bus ajoutés génèrent souvent un profit marginal dérisoire (+361 £/an par bus sur 613553, très inférieur aux coûts d'achat et d'entretien) voire détruisent du profit net sur 10 lignes sur 28 par cannibalisation et congestion.
5. **Erreur conceptuelle du bit 4 (`road1yStops = road1yStopsA + road1yStopsB`) :** Sommer les arrêts des deux villes au lieu de prendre le goulot d'étranglement `min(A, B)` autorise 8 bus sur une ligne à simple quai, et 12 à 18 bus sur une ligne 2+1 quais. Les bus s'entassent à la station à quai unique, créant des bouchons urbains massifs.

**Verdict sans appel :** La variante qui maximise le profit à 3 ans est **`road1y_unlock_off`** (masque 0, défaut) ou **`road1y_unlock_3`** (masque 3), avec **232 233 £/an**.

---

## 2. Tableau Exhaustif des 6 Variantes à 3 Ans (Opex vs AAA)

Toutes les campagnes ont été simulées rigoureusement selon le protocole C66.3 (3 ans, graines 100, 613553, 781335, 3 workers VPS, `docker ps` vide avant chaque lancement).

| Variante / Masque | Description des Bits | Graine 100 (£) | Graine 613553 (£) | Graine 781335 (£) | Profit Moyen Opex | Profit Moyen AAA | Ratio Pft | Valeur Moy. Opex | Véhicules Opex | Lignes Opex |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **`road1y_unlock_off`** (0) | Verrou 4 bus / réserves 50k | 141 960 | 300 668 | 254 071 | **232 233 £** | 647 816 £ | 0.36 | 379 309 £ | 88.0 | 22.3 |
| **`road1y_unlock_3`** (3) | Bits 1+2 (5k arrêt, 10k renfort) | 141 960 | 300 668 | 254 071 | **232 233 £** | 647 816 £ | 0.36 | 379 309 £ | 88.0 | 22.3 |
| **`road1y_unlock_4`** (4) | Bit 4 (refleet attente + somme arrêts) | 135 250 | 239 382 | 183 317 | **185 983 £** | 687 081 £ | 0.27 | 463 154 £ | 107.0 | 15.3 |
| **`road1y_unlock_5`** (5) | Bits 1+4 (5k arrêt + refleet somme) | 135 250 | 239 382 | 183 317 | **185 983 £** | 687 081 £ | 0.27 | 463 154 £ | 107.0 | 15.3 |
| **`road1y_unlock_12`** (12) | Bits 4+8 (refleet somme + cap 6/quai) | 125 765 | 219 594 | 195 692 | **180 350 £** | 662 377 £ | 0.27 | 454 886 £ | 106.7 | 16.0 |
| **`road1y_unlock_15`** (15) | Bits 1+2+4+8 (tous déverrouillés) | 125 765 | 219 594 | 195 692 | **180 350 £** | 662 377 £ | 0.27 | 454 886 £ | 106.7 | 16.0 |

### Analyse Causalité par Bit
- **Invariance totale des Bits 1 et 2 :** 
  - Masque 0 vs Masque 3 : **Strictement identique** au centime près (232 233 £).
  - Masque 4 vs Masque 5 : **Strictement identique** au centime près (185 983 £).
  - Masque 12 vs Masque 15 : **Strictement identique** au centime près (180 350 £).
  *Conclusion :* Les réserves de trésorerie (5 000 £ pour l'arrêt joint, 10 000 £ pour les bus) n'ont aucun impact si le moteur de refleet ou les conditions de seuil ne sont pas satisfaits.
- **Le Bit 4 est le destructeur de profit :** 
  - L'activation du bit 4 fait s'effondrer le profit de **232 233 £ à 185 983 £ (-46 250 £/an, soit -20,0 %)**.
  - C'est ce bit qui force `target = have`, gonfle le plafond via `road1yStopsA + road1yStopsB`, et déclenche les achats compulsifs de bus.
- **Le Bit 8 aggrave la perte :**
  - Passer de 4 à 12 (ou de 5 à 15) fait chuter le profit de **185 983 £ à 180 350 £ (-5 633 £/an supplémentaires)**. Relever le plafond à 6 bus par arrêt sature davantage les terminus.

---

## 3. Analyse Micro-Économique : Les Lignes Passées de 4 à 8+ Bus

Sur les 3 graines, comparons les lignes identiques entre `road1y_unlock_off` (4 bus) et `road1y_unlock_15` (8 à 12 bus).

### 3.1 Tableau Comparatif Ligne par Ligne (Paires Identiques)

| Graine | Paire de Villes | Bus OFF | Pft OFF (£) | Pft/Bus OFF | Bus U15 | Pft U15 (£) | Pft/Bus U15 | Delta Profit (£) | Pft Marginal/Bus | Attente OFF | Attente U15 | Note OFF (0-255) | Note U15 (0-255) |
|:---:|:---:|:---:|---:|---:|:---:|---:|---:|---:|---:|:---:|:---:|:---:|:---:|
| **613553** | (1, 17) | 4 | 10 652 | 2 663 | 8 | 27 129 | 3 391 | **+16 478** | +4 119 £ | [3, 19] | [54, 9] | [88, 82] | [103, 119] |
| 613553 | (4, 15) | 4 | 24 441 | 6 110 | 8 | 18 191 | 2 274 | **−6 249** | **−1 562 £** | [5, 35] | [9, 6] | [135, 119] | [101, 115] |
| 613553 | (5, 42) | 4 | 34 283 | 8 571 | 8 | 30 817 | 3 852 | **−3 465** | **−866 £** | [4, 17] | [10, 3] | [141, 133] | [135, 119] |
| 613553 | (8, 16) | 4 | 36 198 | 9 049 | 12 | 37 746 | 3 146 | **+1 548** | **+194 £** | [346, 115] | [60, 3] | [107, 131] | [133, 161] |
| 613553 | (9, 30) | 4 | 2 506 | 627 | 8 | 3 558 | 445 | **+1 051** | +263 £ | [22, 12] | [6, 31] | [103, 111] | [170, 156] |
| 613553 | (11, 45) | 4 | 4 150 | 1 038 | 8 | 6 461 | 808 | **+2 310** | +578 £ | [5, 8] | [21, 3] | [149, 137] | [174, 186] |
| 613553 | (12, 39) | 4 | 18 275 | 4 569 | 8 | 18 153 | 2 269 | **−122** | **−30 £** | [4, 17] | [7, 2] | [100, 86] | [170, 172] |
| 613553 | (20, 43) | 4 | 20 170 | 5 042 | 8 | 20 201 | 2 525 | **+32** | **+8 £** | [0, 68] | [34, 8] | [99, 100] | [130, 133] |
| 613553 | (22, 35) | 4 | 12 679 | 3 170 | 8 | 10 696 | 1 337 | **−1 982** | **−496 £** | [5, 4] | [4, 7] | [155, 153] | [125, 118] |
| 613553 | (24, 31) | 4 | 33 655 | 8 414 | 8 | 47 516 | 5 940 | **+13 862** | +3 465 £ | [103, 58] | [28, 7] | [75, 76] | [129, 133] |
| 613553 | (38, 40) | 4 | 6 427 | 1 607 | 7 | 0 | 0 | **−6 427** | **−2 142 £** | [8, 0] | [0, 1] | [182, 145] | [189, 196] |
| **781335** | (2, 23) | 4 | 30 619 | 7 655 | 8 | 38 575 | 4 822 | **+7 957** | +1 989 £ | [2, 85] | [5, 19] | [121, 89] | [137, 115] |
| 781335 | (6, 28) | 4 | 3 884 | 971 | 8 | 5 923 | 740 | **+2 039** | +510 £ | [0, 14] | [12, 0] | [151, 143] | [192, 192] |
| 781335 | (8, 21) | 4 | 6 818 | 1 704 | 8 | 15 745 | 1 968 | **+8 927** | +2 232 £ | [1, 7] | [8, 0] | [88, 90] | [111, 97] |
| 781335 | (9, 36) | 4 | 28 475 | 7 119 | 8 | 42 841 | 5 355 | **+14 367** | +3 592 £ | [271, 12] | [20, 27] | [133, 137] | [109, 89] |
| 781335 | (11, 34) | 4 | 8 888 | 2 222 | 8 | 9 342 | 1 168 | **+455** | **+114 £** | [3, 5] | [0, 0] | [100, 100] | [173, 167] |
| 781335 | (15, 35) | 4 | 22 638 | 5 659 | 8 | 21 009 | 2 626 | **−1 629** | **−407 £** | [0, 5] | [9, 8] | [92, 100] | [180, 176] |
| 781335 | (16, 17) | 4 | 22 186 | 5 546 | 8 | 25 896 | 3 237 | **+3 711** | +928 £ | [14, 6] | [16, 3] | [93, 101] | [90, 108] |
| 781335 | (18, 26) | 4 | 29 126 | 7 281 | 8 | 31 244 | 3 906 | **+2 119** | +530 £ | [10, 63] | [28, 4] | [101, 95] | [123, 137] |
| 781335 | (34, 45) | 4 | 4 372 | 1 093 | 8 | 8 359 | 1 045 | **+3 987** | +997 £ | [2, 8] | [0, 2] | [153, 151] | [151, 149] |
| **100** | (1, 29) | 4 | 22 095 | 5 524 | 8 | 30 163 | 3 770 | **+8 069** | +2 017 £ | [4, 29] | [1, 14] | [83, 61] | [117, 113] |
| 100 | (3, 11) | 4 | 6 085 | 1 521 | 8 | 10 429 | 1 304 | **+4 345** | +1 086 £ | [7, 1] | [9, 2] | [80, 96] | [155, 162] |
| 100 | (4, 14) | 4 | 12 759 | 3 190 | 8 | 14 010 | 1 751 | **+1 252** | **+313 £** | [12, 0] | [19, 2] | [98, 108] | [129, 129] |
| 100 | (6, 15) | 4 | 8 688 | 2 172 | 8 | 2 588 | 324 | **−6 100** | **−1 525 £** | [4, 22] | [0, 7] | [112, 96] | [190, 190] |
| 100 | (7, 31) | 4 | 9 160 | 2 290 | 8 | 10 371 | 1 296 | **+1 212** | **+303 £** | [20, 3] | [5, 16] | [90, 102] | [143, 129] |
| 100 | (8, 24) | 4 | 16 683 | 4 171 | 8 | 20 079 | 2 510 | **+3 396** | +849 £ | [10, 0] | [12, 33] | [81, 57] | [139, 117] |
| 100 | (16, 18) | 4 | 10 794 | 2 698 | 8 | 19 884 | 2 486 | **+9 090** | +2 273 £ | [17, 2] | [5, 26] | [84, 83] | [99, 94] |
| 100 | (30, 38) | 4 | 25 483 | 6 371 | 8 | 18 926 | 2 366 | **−6 556** | **−1 639 £** | [12, 1] | [2, 7] | [77, 73] | [118, 94] |

### 3.2 Les 4 Bus Ajoutés Rapportent-ils ?
**NON.** Dans l'immense majorité des cas, doubler la flotte est une opération financière désastreuse :
1. **Échecs complets (Delta négatif ou nul) :** Sur 28 lignes renforcées, **10 lignes (36 %)** voient leur profit total chuter ou stagner malgré 4 bus supplémentaires !
   - Exemple sur (6, 15) graine 100 : profit écroulé de 8 688 £ à 2 588 £ (**−70 %**).
   - Exemple sur (30, 38) graine 100 : perte nette de **−6 556 £/an**.
   - Exemple sur (4, 15) graine 613553 : perte nette de **−6 249 £/an**.
2. **Le cas emblématique de la ligne (8, 16) sur 613553 (12 bus) :**
   - 4 bus en OFF rapportaient **36 198 £** (9 049 £/bus).
   - 12 bus en U15 rapportent **37 746 £** (3 146 £/bus).
   - **+8 bus achetés** pour seulement **+1 548 £** de profit supplémentaire (+194 £ par bus, très loin de couvrir ne serait-ce que la maintenance annuelle de 700 £ par bus).
   - L'autopsie des véhicules individuels montre que les véhicules 64, 65, 67, 69 rapportent respectivement 922 £, 988 £, **−242 £ (déficit)** et 148 £.
3. **Bilan global sur les lignes communes (Graine 613553) :**
   - Pour les 14 lignes communes, Opex a injecté **+46 bus** (60 → 106).
   - Le profit de ces lignes est passé de 242 225 £ à 258 872 £ (+16 647 £ au total).
   - **Profit marginal moyen : +361 £ par an et par bus ajouté.** Un bus coûte 3 500 £ à l'achat : il faut 10 ans pour amortir le capital investi, sur un horizon de 3 ans !

### 3.3 Attente aux Arrêts et Notes de Gare
- **Note de gare :** Elle progresse modérément (passant de ~90-110 à ~130-170 sur l'échelle 0-255 d'OpenTTD, soit 35-45 % → 50-65 %). Mais dans OpenTTD, une gare à 65 % ne capte que 20 à 25 % de passagers en plus par rapport à une gare à 45 %.
- **Attente :** Elle est effectivement divisée par 2 ou 3 (ex. ligne (8, 16) où l'attente passe de 346 à 60). Mais vider l'arrêt ne signifie pas générer de la demande : les bus circulent ensuite aux trois quarts vides, multipliant les coûts de roulement sans recette billetterie.

---

## 4. Pourquoi 8 Lignes de Moins : L'Autopsie du Piège de Trésorerie

Sur la graine 613553, Opex passe de **25 lignes** à **17 lignes** (−8 lignes).  
Sur la graine 781335, Opex passe de **24 lignes** à **17 lignes** (−7 lignes).  
Sur la graine 100, Opex passe de **18 lignes** à **14 lignes** (−4 lignes).

### 4.1 Chronologie Trimestrielle : La Trésorerie Siphonnée par le Refleet

Regardons l'évolution comparée de la trésorerie et des lignes sur la graine 613553 :

| Date | Lignes OFF | Véhicules OFF | Trésorerie OFF (£) | Lignes U15 | Véhicules U15 | Trésorerie U15 (£) |
|:---:|:---:|:---:|---:|:---:|:---:|---:|
| **1970-01-01** | 0 | 0 | 100 000 | 0 | 0 | 100 000 |
| **1970-04-01** | 6 | 18 | 112 468 | 6 | 21 | 95 133 |
| **1970-07-01** | 9 | 31 | 13 979 | 9 | 37 | 9 753 |
| **1970-10-01** | 10 | 38 | 17 918 | 9 | 49 | 8 232 |
| **1971-01-01** | 12 | 46 | 20 881 | **9** | **61** | **12 833** |
| **1971-04-01** | 15 | 57 | 12 188 | 11 | 68 | 4 052 |
| **1971-07-01** | 17 | 65 | 14 173 | 11 | 79 | 11 154 |
| **1971-10-01** | 19 | 72 | 23 285 | 12 | 88 | 10 490 |
| **1972-01-01** | 20 | 80 | **32 042** | **12** | **97** | **16 553** |
| **1972-04-01** | 23 | 90 | 17 788 | 13 | 103 | 13 221 |
| **1972-07-01** | 24 | 97 | 32 079 | 14 | 109 | 17 559 |
| **1972-10-01** | 25 | 102 | 75 195 | 16 | 115 | 17 977 |
| **1972-12-01** | **25** | **102** | **118 904** | **17** | **120** | **20 510** |

### 4.2 Le Mécanisme Causal du Blocage du Vivier
1. **Le coût d'une nouvelle ligne :**
   Dans le planificateur Opex (`task_projects.nut`), un nouveau projet routier requiert un capital disponible de **20 000 £ à 25 000 £** (voierie, deux arrêts, dépôt et 2 à 4 bus initiaux).
2. **Ce qui se passe sous `road1y_unlock_off` :**
   Chaque ligne est plafonnée à 4 bus. Dès qu'une ligne atteint 4 bus, l'achat de véhicules est verrouillé. Les recettes d'exploitation s'accumulent donc en banque : la caisse dépasse régulièrement 20 000 £ (20k en janv. 71, 23k en oct. 71, 32k en janv. 72, 75k en oct. 72). À chaque franchissement de seuil, le portefeuille sélectionne et finance une **nouvelle ligne** qui ouvre un nouveau marché.
3. **Ce qui se passe sous `road1y_unlock_15` :**
   Le refleet mensuel tourne chaque mois. Dès que la caisse atteint 10 000 £ ou 15 000 £, l'algorithme achète immédiatement 1 ou 2 bus supplémentaires pour les lignes existantes (~3 500 £ par bus).
   - **La trésorerie ne peut jamais atteindre le seuil de 20 000 £.** Durant toute l'année 1971, le cash oscille entre 4 000 £ et 12 800 £.
   - **Année 1971 stérile :** Sur la graine 613553, Opex ne construit **strictement aucune nouvelle ligne** pendant les 9 premiers mois de 1971 (le nombre de lignes reste bloqué à 9). Pendant ce temps, 24 bus sont achetés sur les lignes existantes !
   - Le journal de décision avec sonde (`probes=258`) confirme que la tâche de portefeuille se termine chaque mois par `PORTFOLIO_EMPTY budget=4114`, `budget=8770`, `budget=6506`, etc. Le vivier contient des dizaines de villes prêtes à être reliées, mais le budget disponible est insuffisant car il est immédiatement aspiré par le refleet.

### 4.3 Le Coût d'Opportunité des Lignes Abandonnées
Dans la variante OFF, les lignes non construites par U15 ont généré les profits suivants :
- Sur 613553 : **11 lignes non construites** valant **61 664 £/an** de profit dans OFF (dont la ligne (33, 36) rapportant à elle seule 29 224 £/an, la ligne (7, 8) 14 276 £/an, et la ligne (10, 23) 11 134 £/an).
- Sur 781335 : **14 lignes non construites** valant **84 294 £/an** de profit dans OFF.
- Sur 100 : **6 lignes non construites** valant **42 525 £/an** de profit dans OFF.

**Équation économique finale :**  
Perte de profit sur les nouvelles lignes non ouvertes : **−61 664 £**  
Gain de profit sur les 46 bus ajoutés aux lignes existantes : **+16 647 £**  
**Résultat net : perte de −45 000 £ à −80 000 £ par graine !**

---

## 5. Analyse Algorithmique et Physique du Bit 4 : `road1yStopsA + road1yStopsB`

Le code introduit dans `bus_districts_overrides.nut:2052-2055` est :
```squirrel
local isPax = (("kind" in line) && line.kind == "pax");
local road1yStopsA = ("nStopsA" in line) ? line.nStopsA : 1;
local road1yStopsB = ("nStopsB" in line) ? line.nStopsB : 1;
local road1yStops = (isPax && paxRefleet)
    ? (road1yStopsA + road1yStopsB)
    : (road1yStopsB < road1yStopsA ? road1yStopsB : road1yStopsA);
```

### 5.1 Pourquoi la Somme est un Contresens Physique
- **Avant le bit 4 :**  
  `road1yStops = min(nStopsA, nStopsB)`.  
  Le commentaire historique de la ligne 2046 indique explicitement :  
  *« sous un plafond de ROAD1Y_FLEET véhicules par paire de quais »*.  
  Une ligne de transport est un circuit entre deux terminus. Sa capacité maximale de débit est dictée par son **goulot d'étranglement**, c'est-à-dire le terminus ayant le plus petit nombre de quais : `min(A, B)`.
- **Avec le bit 4 (`road1yStopsA + road1yStopsB`) :**  
  L'auteur a confondu le nombre de quais par terminus avec la somme totale des arrêts du réseau de la ligne.
  1. **Sur une ligne standard 1 quai à A et 1 quai à B :**  
     `stopsA + stopsB = 1 + 1 = 2`.  
     Le plafond devient immédiatement `ROAD1Y_FLEET * 2 = 4 * 2 = 8 bus` !  
     La ligne est autorisée à doubler sa flotte sans qu'aucun quai supplémentaire n'ait été posé !
  2. **Sur une ligne avec 2 arrêts à A et 1 arrêt à B (2+1) :**  
     `stopsA + stopsB = 2 + 1 = 3`.  
     Le plafond devient `4 * 3 = 12 bus` (et avec le bit 8, `6 * 3 = 18 bus`) !

### 5.2 Conséquences en Jeu sur une Extrémité à 1 Quai
Lorsqu'une extrémité n'a qu'un seul quai et que 12 bus y convergent :
- Un bus de 30 passagers met environ 10 à 15 jours de jeu pour charger/décharger à un drive-through stop.
- Avec 12 bus sur la ligne, un bus arrive tous les 3 à 5 jours.
- Le bus qui arrive trouve le quai occupé : il s'arrête sur la voie publique immédiatement en amont. Le bus suivant s'arrête derrière lui, bloquant le carrefour de la ville.
- Les bus se « paquétisent » (headway bunching). Ils repartent tous ensemble à la queue leu leu, vides, et arrivent ensemble à l'autre terminus.
- L'exploitation subit une explosion des coûts kilométriques et d'usure sans aucun gain de passagers transportés.

---

## 6. Conclusion et Recommandations Opérationnelles

### 6.1 Variante Maximisant le Profit 3 Ans
La variante qui maximise le profit d'exploitation à 3 ans est **`road1y_unlock_off`** (ou `road1y_unlock_3`), avec **232 233 £/an**.  
Toutes les autres variantes dégradent le profit de 20 % à 22 % en gaspillant le capital dans des renforts prématurés au détriment de l'expansion géographique.

### 6.2 Principes de Correction pour une Flotte Dynamique Saine
Si un renfort de flotte doit être réintroduit ultérieurement, il doit impérativement respecter trois règles économiques et physiques strictes :

1. **Règle de Primauté de l'Expansion Géographique (Priorité au Vivier) :**
   - Interdire tout refleet au-delà de 4 bus tant que le vivier de projets contient des lignes rentables non construites ET que la trésorerie n'atteint pas `25 000 £ + coût_du_bus`.
   - Ne renforcer les lignes existantes que lorsque le portefeuille est vide (`PORTFOLIO_EMPTY`) ou que l'excédent de trésorerie garantit que la prochaine ligne pourra être construite sans délai.
2. **Rétablissement du Goulot d'Étranglement Physique `min(A, B)` :**
   - Remplacer immédiatement `road1yStopsA + road1yStopsB` par `min(road1yStopsA, road1yStopsB)`.
   - Une ligne ne doit JAMAIS dépasser 4 bus si l'un de ses deux terminus ne dispose que d'un seul quai. Le passage à 8 bus doit être conditionné à la présence physique de **2 quais à chaque extrémité**.
3. **Filtre de Rentabilité Marginale du Bus :**
   - N'autoriser l'achat d'un 5e, 6e, 7e ou 8e bus que si :
     - Le profit historique de la ligne est supérieur à **5 000 £ par bus existant** (`lastProfit / have >= 5000`).
     - L'attente dépasse la capacité de la flotte aux DEUX terminus (`waitingA > 2 * capacity && waitingB > 2 * capacity`).
     - Si une ligne à 4 bus ne dégage que 2 000 £/bus, tout ajout de bus est formellement prohibé.
