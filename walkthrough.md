# Walkthrough — Résultats Comparatifs 1v1 (AAAHogEx vs OpexAI)

Ce document présente les résultats du banc 1v1 (20 graines × 3 ans, 1970) après intégration des 3 améliorations structurelles :
1. Tracé routier multi-variantes avec déviations en escalier ($Z$ et $+1$) pour contourner les obstacles sans dépendance externe.
2. Redimensionnement dynamique de flotte routière (`_refleetRoadLines`) et plafond relevé à 20 véhicules.
3. Remboursement d'emprunt progressif à partir de l'Année 2 au-delà de 50 000 £ de trésorerie.

---

## Tableau comparatif Année par Année (20 graines × 3 ans)

| Graine | AAAHogEx An 1<br>(Valeur / Véh) | OpexAI An 1<br>(Valeur / Véh) | AAAHogEx An 2<br>(Valeur / Véh) | OpexAI An 2<br>(Valeur / Véh) | AAAHogEx An 3<br>(Valeur / Véh) | OpexAI An 3<br>(Valeur / Véh) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 541 603 £ (48 v) | 9 834 £ (22 v) | 2 836 303 £ (201 v) | 130 890 £ (45 v) | 5 178 746 £ (358 v) | 209 425 £ (66 v) |
| **100** | 260 997 £ (30 v) | 72 770 £ (29 v) | 1 647 824 £ (161 v) | 209 035 £ (49 v) | 3 396 262 £ (348 v) | 191 496 £ (49 v) |
| **7** | 625 413 £ (54 v) | 203 294 £ (41 v) | 3 366 439 £ (232 v) | 475 771 £ (41 v) | 7 278 491 £ (456 v) | **857 981 £** (65 v) |
| **999** | 555 329 £ (52 v) | 143 882 £ (33 v) | 3 158 009 £ (211 v) | 325 876 £ (50 v) | 6 706 060 £ (427 v) | **573 776 £** (63 v) |
| **2026** | 383 415 £ (43 v) | 39 044 £ (19 v) | 2 857 070 £ (185 v) | 17 750 £ (21 v) | 4 958 013 £ (444 v) | 13 986 £ (28 v) |
| **1** | 429 855 £ (43 v) | 37 689 £ (34 v) | 2 703 342 £ (195 v) | 6 635 £ (41 v) | 5 432 273 £ (444 v) | 1 £ (51 v) |
| **17** | 487 996 £ (37 v) | 160 076 £ (25 v) | 2 369 056 £ (148 v) | 331 242 £ (27 v) | 4 589 682 £ (413 v) | **453 394 £** (27 v) |
| **73** | 472 492 £ (38 v) | 69 018 £ (41 v) | 2 769 190 £ (179 v) | 320 517 £ (53 v) | 5 715 888 £ (402 v) | **503 061 £** (63 v) |
| **314** | 400 181 £ (48 v) | 160 237 £ (45 v) | 2 639 564 £ (200 v) | 214 278 £ (59 v) | 6 157 617 £ (437 v) | 205 369 £ (58 v) |
| **512** | 361 134 £ (37 v) | 131 352 £ (19 v) | 1 376 296 £ (138 v) | 213 190 £ (28 v) | 3 361 187 £ (338 v) | **369 934 £** (57 v) |
| **1024** | 300 768 £ (35 v) | 80 307 £ (17 v) | 1 705 123 £ (144 v) | 237 074 £ (29 v) | 3 752 115 £ (299 v) | **550 605 £** (46 v) |
| **1337** | 484 531 £ (42 v) | 23 593 £ (13 v) | 2 531 449 £ (237 v) | 174 704 £ (31 v) | 4 619 519 £ (475 v) | 236 641 £ (26 v) |
| **4096** | 526 193 £ (53 v) | 170 376 £ (20 v) | 2 685 884 £ (216 v) | 586 720 £ (59 v) | 5 500 394 £ (306 v) | **1 056 422 £** (80 v) |
| **8191** | 386 308 £ (40 v) | 151 137 £ (34 v) | 2 418 744 £ (190 v) | 364 429 £ (39 v) | 4 944 668 £ (389 v) | **547 014 £** (49 v) |
| **12345** | 287 677 £ (38 v) | 23 882 £ (38 v) | 1 704 114 £ (132 v) | 90 365 £ (48 v) | 3 635 838 £ (304 v) | 201 893 £ (63 v) |
| **54321** | 310 525 £ (29 v) | 86 377 £ (29 v) | 1 769 991 £ (126 v) | 270 172 £ (46 v) | 3 933 518 £ (320 v) | **422 020 £** (69 v) |
| **65537** | 247 024 £ (32 v) | 141 394 £ (37 v) | 1 425 383 £ (113 v) | 218 063 £ (50 v) | 3 551 398 £ (292 v) | 252 619 £ (61 v) |
| **123456** | 410 326 £ (42 v) | 131 714 £ (31 v) | 2 563 966 £ (192 v) | 306 811 £ (31 v) | 5 269 697 £ (367 v) | **401 439 £** (31 v) |
| **424242** | 537 347 £ (47 v) | 134 918 £ (44 v) | 2 879 407 £ (217 v) | 300 003 £ (68 v) | 5 729 103 £ (400 v) | **394 662 £** (89 v) |
| **8675309** | 462 788 £ (54 v) | 39 080 £ (20 v) | 2 358 772 £ (171 v) | 97 118 £ (20 v) | 5 293 314 £ (349 v) | 147 917 £ (28 v) |
| **Moyenne** | **423 595 £ (42.1 v)** | **100 499 £ (29.6 v)** | **2 388 296 £ (179.4 v)** | **244 532 £ (41.8 v)** | **4 950 189 £ (378.4 v)** | **379 483 £ (53.5 v)** |

---

## Fichiers de données associés
* JSON complet : [`docs/bench_1v1_3y_full_improvements_20seeds.json`](file:///home/deploy/projects/openttd-ml/docs/bench_1v1_3y_full_improvements_20seeds.json)
* Checkpoint : [`docs/bench_1v1_3y_full_improvements_20seeds.jsonl`](file:///home/deploy/projects/openttd-ml/docs/bench_1v1_3y_full_improvements_20seeds.jsonl)
