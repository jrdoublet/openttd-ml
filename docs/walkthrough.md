# Walkthrough — Résultats Détaillés du Banc 1v1 (AAAHogEx vs OpexAI)

Ce document récapitule l'ensemble des résultats du banc 1v1 (20 graines × 3 ans, 1970) confrontant `OpexAI` et `AAAHogEx`, ainsi que l'emplacement de tous les fichiers de données brutes.

---

## 1. Emplacement des fichiers de résultats

Les données brutes et séries temporelles mensuelles de chaque simulation sont enregistrées dans les fichiers suivants :

* **Dernier banc 1v1 complet (20 graines × 3 ans)** :
  - JSON complet avec séries mensuelles : [`docs/bench_1v1_3y_latest_20seeds.json`](file:///home/deploy/projects/openttd-ml/docs/bench_1v1_3y_latest_20seeds.json)
  - Checkpoint mensuel ligne à ligne : [`docs/bench_1v1_3y_latest_20seeds.jsonl`](file:///home/deploy/projects/openttd-ml/docs/bench_1v1_3y_latest_20seeds.jsonl)
* **Banc 1v1 de référence avant correctifs (commit `ebbab62`)** :
  - [`docs/bench_1v1_3y_ebbab62_20seeds.json`](file:///home/deploy/projects/openttd-ml/docs/bench_1v1_3y_ebbab62_20seeds.json)
* **Campagnes multi-années** :
  - Campagne 10 ans (10 graines) : [`docs/opex_full_campaign_10y_42_43_44_45_46_47_48_49_50_51.json`](file:///home/deploy/projects/openttd-ml/docs/opex_full_campaign_10y_42_43_44_45_46_47_48_49_50_51.json)
  - Campagne 20 ans (5 graines) : [`docs/opex_full_campaign_20y_42_43_44_45_46.json`](file:///home/deploy/projects/openttd-ml/docs/opex_full_campaign_20y_42_43_44_45_46.json)
* **Rapports de synthèse** :
  - Racine du dépôt : [`walkthrough.md`](file:///home/deploy/projects/openttd-ml/walkthrough.md)
  - Répertoire documentation : [`docs/walkthrough.md`](file:///home/deploy/projects/openttd-ml/docs/walkthrough.md)

---

## 2. Tableau comparatif Année par Année (20 graines)

| Graine | AAAHogEx An 1<br>(Valeur / Véh) | OpexAI An 1<br>(Valeur / Véh) | AAAHogEx An 2<br>(Valeur / Véh) | OpexAI An 2<br>(Valeur / Véh) | AAAHogEx An 3<br>(Valeur / Véh) | OpexAI An 3<br>(Valeur / Véh) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 541 603 £ (48 v) | 47 508 £ (35 v) | 2 836 303 £ (201 v) | 173 522 £ (32 v) | 5 178 746 £ (358 v) | 277 495 £ (56 v) |
| **100** | 260 997 £ (30 v) | 1 £ (14 v) | 1 647 824 £ (161 v) | 88 948 £ (34 v) | 3 396 262 £ (348 v) | 355 413 £ (36 v) |
| **7** | 625 413 £ (54 v) | 226 047 £ (47 v) | 3 366 439 £ (232 v) | 572 071 £ (73 v) | 7 278 491 £ (456 v) | **1 079 841 £** (88 v) |
| **999** | 555 329 £ (52 v) | 161 392 £ (47 v) | 3 158 009 £ (211 v) | 374 907 £ (72 v) | 6 697 320 £ (419 v) | 537 829 £ (87 v) |
| **2026** | 383 415 £ (43 v) | 1 £ (16 v) | 2 857 070 £ (185 v) | 354 £ (19 v) | 4 958 013 £ (444 v) | 26 554 £ (28 v) |
| **1** | 429 855 £ (43 v) | 78 473 £ (25 v) | 2 703 342 £ (195 v) | 160 014 £ (24 v) | 5 432 273 £ (444 v) | 213 716 £ (27 v) |
| **17** | 487 996 £ (37 v) | 139 152 £ (17 v) | 2 369 056 £ (148 v) | 374 142 £ (30 v) | 4 589 682 £ (413 v) | 570 325 £ (47 v) |
| **73** | 472 492 £ (38 v) | 1 £ (4 v) | 2 769 190 £ (179 v) | 1 £ (4 v) | 5 736 159 £ (396 v) | 1 £ (6 v) |
| **314** | 400 181 £ (48 v) | 1 £ (23 v) | 2 639 564 £ (200 v) | 126 180 £ (25 v) | 6 157 617 £ (437 v) | 255 779 £ (27 v) |
| **512** | 361 134 £ (37 v) | 110 324 £ (15 v) | 1 376 296 £ (138 v) | 359 159 £ (15 v) | 3 361 187 £ (338 v) | 529 690 £ (27 v) |
| **1024** | 300 768 £ (35 v) | 42 882 £ (13 v) | 1 705 123 £ (144 v) | 170 032 £ (13 v) | 3 752 115 £ (299 v) | 253 005 £ (19 v) |
| **1337** | 484 531 £ (42 v) | 56 488 £ (17 v) | 2 531 449 £ (237 v) | 216 874 £ (23 v) | 4 619 519 £ (475 v) | 353 730 £ (45 v) |
| **4096** | 526 193 £ (53 v) | 84 935 £ (20 v) | 2 685 884 £ (216 v) | 365 126 £ (31 v) | 5 500 394 £ (306 v) | **863 415 £** (29 v) |
| **8191** | 386 308 £ (40 v) | 82 623 £ (36 v) | 2 418 744 £ (190 v) | 151 955 £ (39 v) | 4 899 290 £ (404 v) | 169 607 £ (49 v) |
| **12345** | 287 677 £ (38 v) | 17 188 £ (22 v) | 1 704 114 £ (132 v) | 69 052 £ (44 v) | 3 635 838 £ (304 v) | 219 298 £ (57 v) |
| **54321** | 310 525 £ (29 v) | 137 563 £ (35 v) | 1 769 991 £ (126 v) | 408 913 £ (50 v) | 3 933 518 £ (320 v) | 637 712 £ (51 v) |
| **65537** | 247 024 £ (32 v) | 179 678 £ (42 v) | 1 425 383 £ (113 v) | 309 399 £ (46 v) | 3 551 398 £ (292 v) | 397 683 £ (59 v) |
| **123456** | 410 326 £ (42 v) | 76 149 £ (12 v) | 2 563 966 £ (192 v) | 206 639 £ (12 v) | 5 269 697 £ (367 v) | 296 442 £ (12 v) |
| **424242** | 537 347 £ (47 v) | 71 493 £ (30 v) | 2 879 407 £ (217 v) | 328 789 £ (36 v) | 5 729 103 £ (400 v) | 477 208 £ (35 v) |
| **8675309** | 462 788 £ (54 v) | 24 908 £ (13 v) | 2 358 772 £ (171 v) | 204 032 £ (19 v) | 5 293 314 £ (349 v) | 390 053 £ (19 v) |
| **Moyenne** | **423 595 £ (42.1 v)** | **76 840 £ (24.1 v)** | **2 388 296 £ (179.4 v)** | **233 005 £ (32.0 v)** | **4 948 497 £ (378.4 v)** | **395 240 £ (40.2 v)** |
