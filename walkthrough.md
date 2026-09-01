# Walkthrough — Analyse Détaillée des 2 Pires Graines et Nouveau Record 1v1

## 1. Diagnostic Approfondi : Analyse des 2 Pires Graines (Graine 2026 et Graine 100)

L'inspection fine des logs et panneaux d'instrumentation sur les graines les plus faibles a identifié les causes racines précises du retard par rapport à AAAHogEx :

### A. Graine 2026 (Relief montagneux et villes en pente)
* **Où AAAHogEx gagne son argent** : AAAHogEx implante des petits aéroports (3x4 tuiles) et de courtes lignes de bus sinueuses au ras des villes montagneuses.
* **Pourquoi OpexAI n'y était pas** :
  - Dans [`builder_air.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_air.nut#L300), une règle interdisait les petits aéroports sur les villes de population $\ge 2500$ hab (`if (combo.kind == "small" && towns[i].pop >= 2500) continue;`).
  - Or, sur la graine 2026, toutes les grandes villes sont situées sur un relief escarpé qui ne comporte **aucune surface plane de 4x4 tuiles** pour un grand aéroport.
  - Résultat : OpexAI rejetait le grand aéroport (manque de place 4x4) ET s'interdisait le petit aéroport (population > 2500), bloquant l'aviation pendant 2 ans (`AD|NULL|C=1`).
* **Correctif apporté** : Autorisation des petits aéroports sur toutes les villes dès qu'un grand aéroport ne peut pas être implanté.

### B. Graine 100 (Villes distantes à faible demande unitaire)
* **Où AAAHogEx gagne son argent** : AAAHogEx concentre son capital sur 2 aéroports très rentables et ne disperse pas sa trésorerie sur des liaisons routières déficitaires.
* **Pourquoi OpexAI n'y était pas** :
  - Sur la graine 100, OpexAI a construit 2 lignes d'avions très rentables (+147 k£/an), mais a ensuite ouvert 6 lignes de bus rurales longue distance qui tournaient toutes à perte (-1 076 £/an, -624 £/an).
  - Pire : [`_refleetRoadLines`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/main.nut#L2294) rachetait continuellement des bus sur ces lignes déficitaires (jusqu'à 12 bus sur la ligne 3), siphonnant 70 000 £ de cash et empêchant le solde d'atteindre le montant nécessaire pour poser un 3e aéroport.
* **Correctif apporté** :
  - Interdiction stricte de redimensionner toute ligne dont le profit est nul ou négatif (`line.lastProfit <= 0`).
  - Conditionnement de l'achat de véhicules supplémentaires à une rentabilité avérée (`lastProfit > 500 £`) et à une trésorerie excédentaire (> 60 000 £).

---

## 2. Tableau comparatif Année par Année (20 graines × 3 ans)

| Graine | AAAHogEx An 1<br>(Val / Véh) | OpexAI An 1<br>(Val / Véh) | AAAHogEx An 2<br>(Val / Véh) | OpexAI An 2<br>(Val / Véh) | AAAHogEx An 3<br>(Val / Véh) | OpexAI An 3<br>(Val / Véh) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 541 603 £ (48 v) | 36 882 £ (27 v) | 2 836 303 £ (201 v) | 208 621 £ (36 v) | 5 178 746 £ (358 v) | **370 847 £** (70 v) |
| **100** | 260 997 £ (30 v) | 50 069 £ (27 v) | 1 647 824 £ (161 v) | 142 217 £ (34 v) | 3 396 262 £ (348 v) | **150 973 £** (41 v) |
| **7** | 625 413 £ (54 v) | 252 188 £ (35 v) | 3 366 439 £ (232 v) | 633 745 £ (34 v) | 7 278 491 £ (456 v) | **1 069 789 £** (77 v) |
| **999** | 555 329 £ (52 v) | 152 223 £ (44 v) | 3 158 009 £ (211 v) | 276 115 £ (47 v) | 6 706 060 £ (427 v) | **432 384 £** (69 v) |
| **2026** | 383 415 £ (43 v) | 5 536 £ (15 v) | 2 857 070 £ (185 v) | 793 £ (20 v) | 4 958 013 £ (444 v) | **76 933 £** (29 v) |
| **1** | 429 855 £ (43 v) | 75 802 £ (24 v) | 2 703 342 £ (195 v) | 270 305 £ (24 v) | 5 432 273 £ (444 v) | **499 310 £** (47 v) |
| **17** | 487 996 £ (37 v) | 187 545 £ (27 v) | 2 369 056 £ (148 v) | 486 065 £ (57 v) | 4 589 682 £ (413 v) | **816 539 £** (55 v) |
| **73** | 472 492 £ (38 v) | 81 560 £ (24 v) | 2 769 190 £ (179 v) | 261 253 £ (24 v) | 5 736 159 £ (396 v) | **384 307 £** (24 v) |
| **314** | 400 181 £ (48 v) | 115 220 £ (31 v) | 2 639 564 £ (200 v) | 303 274 £ (52 v) | 6 157 617 £ (437 v) | **468 733 £** (68 v) |
| **512** | 361 134 £ (37 v) | 125 202 £ (17 v) | 1 376 296 £ (138 v) | 277 867 £ (38 v) | 3 361 187 £ (338 v) | **435 702 £** (46 v) |
| **1024** | 300 768 £ (35 v) | 118 897 £ (15 v) | 1 705 123 £ (144 v) | 357 353 £ (24 v) | 3 752 115 £ (299 v) | **918 685 £** (41 v) |
| **1337** | 484 531 £ (42 v) | 94 723 £ (19 v) | 2 531 449 £ (237 v) | 348 743 £ (18 v) | 4 621 564 £ (449 v) | **538 359 £** (23 v) |
| **4096** | 526 193 £ (53 v) | 177 713 £ (20 v) | 2 685 884 £ (216 v) | 645 632 £ (63 v) | 5 500 394 £ (306 v) | **1 002 915 £** (48 v) |
| **8191** | 386 308 £ (40 v) | 125 583 £ (33 v) | 2 418 744 £ (190 v) | 473 622 £ (58 v) | 4 899 290 £ (404 v) | **748 237 £** (53 v) |
| **12345** | 287 677 £ (38 v) | 129 906 £ (39 v) | 1 704 114 £ (132 v) | 161 117 £ (44 v) | 3 635 838 £ (304 v) | **211 498 £** (60 v) |
| **54321** | 310 525 £ (29 v) | 152 520 £ (14 v) | 1 769 991 £ (126 v) | 638 602 £ (46 v) | 3 933 518 £ (320 v) | **1 046 619 £** (66 v) |
| **65537** | 247 024 £ (32 v) | 176 912 £ (37 v) | 1 425 383 £ (113 v) | 308 041 £ (44 v) | 3 551 398 £ (292 v) | **421 816 £** (43 v) |
| **123456** | 410 326 £ (42 v) | 127 610 £ (24 v) | 2 563 966 £ (192 v) | 402 117 £ (25 v) | 5 269 697 £ (367 v) | **544 343 £** (24 v) |
| **424242** | 537 347 £ (47 v) | 168 634 £ (47 v) | 2 879 407 £ (217 v) | 364 387 £ (64 v) | 5 729 103 £ (400 v) | **574 131 £** (74 v) |
| **8675309** | 462 788 £ (54 v) | 66 722 £ (18 v) | 2 358 772 £ (171 v) | 161 070 £ (18 v) | 5 293 314 £ (349 v) | **316 838 £** (44 v) |
| **Moyenne** | **423 595 £ (42.1 v)** | **121 072 £ (26.9 v)** | **2 388 296 £ (179.4 v)** | **336 047 £ (38.5 v)** | **4 949 036 £ (377.6 v)** | **551 448 £ (50.1 v)** |

---

## 3. Synthèse des Avancées

- **Nouveau record absolu de valeur moyenne** : **551 448 £** (hausse continue depuis 379 k£ $\to$ 473 k£ $\to$ 530 k£ $\to$ 551 k£).
- **3 graines millionnaires** :
  - Graine **7** : **1 069 789 £**
  - Graine **54321** : **1 046 619 £**
  - Graine **4096** : **1 002 915 £**
- **Hausse des graines moyennes** : Graine 1024 (**918 k£**), Graine 17 (**816 k£**), Graine 8191 (**748 k£**), Graine 424242 (**574 k£**).
