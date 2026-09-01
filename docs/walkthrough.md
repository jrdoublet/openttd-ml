# Walkthrough — Analyse Détaillée des Écarts et Résultats Comparatifs 1v1 (AAAHogEx vs OpexAI)

## 1. Diagnostic Approfondi : Pourquoi AAAHogEx gagnait et où était l'écart ?

L'analyse comparative détaillée sur les pires graines (notamment la **Graine 1**) a mis en évidence le mécanisme exact qui créait l'écart :

### A. Où AAAHogEx gagne son argent en An 1-3 :
1. **L'Amorce Aérienne Immédiate (Jour 1)** : AAAHogEx construit dès les premières semaines une liaison aérienne entre les deux villes les plus distantes. Deux avions génèrent immédiatement **> 250 000 £ / an de cash-flow net**.
2. **Le Réseau Feeder Routier Massif** : Avec les profits de l'aviation, AAAHogEx déploie en continu 40 à 100 liaisons routières (bus et camions) à bas coût.
3. **Réinvestissement continu sans temps mort** : L'IA ne thésaurise pas et ne rembourse pas sa dette à 4 % ; chaque livre de profit est immédiatement réinjectée dans des lignes à fort ROI.

### B. Pourquoi OpexAI n'allait pas là avant :
1. **La tâche `air` était devenue orpheline** : Lors du passage au solveur sac à dos (`projects.nut`), le module dédié `_tryBuildAir` ([`main.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/main.nut#L497)) avait été retiré de la file de tâches `_taskQueue`. L'aviation n'était plus tentée que comme un candidat parmi d'autres dans le sac à dos.
2. **La famine de trésorerie par sur-achat de bus** : Dès que la trésorerie atteignait 7 000 £, l'IA rachetait des bus sur des lignes rurales (parfois jusqu'à 16 bus par ligne), empêchant la caisse d'atteindre le seuil de 50 000 £ requis pour construire un aéroport.

---

## 2. Correctifs Appliqués

1. **Restauration de la tâche `air` prioritaire dans `_taskQueue`** : Exécution systématique du bâtisseur aérien proactif dès que la ligne de crédit ou la trésorerie est disponible.
2. **Régulation du redimensionnement routier** : Priorité donnée à l'expansion de réseau plutôt qu'à la saturation de lignes rurales déficitaires.
3. **Conservation du capital d'investissement** : Maintien de l'emprunt pour financer le réseau à haut rendement.

---

## 3. Résultats Comparatifs 1v1 (20 graines × 3 ans)

| Graine | AAAHogEx An 1<br>(Val / Véh) | OpexAI An 1<br>(Val / Véh) | AAAHogEx An 2<br>(Val / Véh) | OpexAI An 2<br>(Val / Véh) | AAAHogEx An 3<br>(Val / Véh) | OpexAI An 3<br>(Val / Véh) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 541 603 £ (48 v) | 43 082 £ (26 v) | 2 836 303 £ (201 v) | 205 389 £ (26 v) | 5 178 746 £ (358 v) | **500 254 £** (51 v) |
| **100** | 260 997 £ (30 v) | 50 947 £ (25 v) | 1 647 824 £ (161 v) | 114 893 £ (37 v) | 3 396 262 £ (348 v) | **139 205 £** (49 v) |
| **7** | 625 413 £ (54 v) | 263 397 £ (40 v) | 3 366 439 £ (232 v) | 653 373 £ (38 v) | 7 308 040 £ (474 v) | **1 074 809 £** (83 v) |
| **999** | 555 329 £ (52 v) | 172 501 £ (44 v) | 3 158 009 £ (211 v) | 293 551 £ (61 v) | 6 706 060 £ (433 v) | **316 734 £** (71 v) |
| **2026** | 383 415 £ (43 v) | 5 536 £ (15 v) | 2 857 070 £ (185 v) | 793 £ (21 v) | 4 958 013 £ (444 v) | **44 863 £** (32 v) |
| **1** | 429 855 £ (43 v) | 83 188 £ (29 v) | 2 703 342 £ (195 v) | 284 376 £ (39 v) | 5 432 273 £ (444 v) | **583 596 £** (63 v) |
| **17** | 487 996 £ (37 v) | 186 941 £ (37 v) | 2 369 056 £ (148 v) | 382 203 £ (61 v) | 4 589 682 £ (413 v) | **512 341 £** (90 v) |
| **73** | 472 492 £ (38 v) | 90 661 £ (34 v) | 2 769 190 £ (179 v) | 395 142 £ (61 v) | 5 715 888 £ (402 v) | **631 045 £** (87 v) |
| **314** | 400 181 £ (48 v) | 130 919 £ (36 v) | 2 639 564 £ (200 v) | 301 788 £ (50 v) | 6 157 617 £ (437 v) | **467 196 £** (87 v) |
| **512** | 361 134 £ (37 v) | 162 952 £ (33 v) | 1 376 296 £ (138 v) | 287 957 £ (45 v) | 3 413 013 £ (287 v) | **359 442 £** (49 v) |
| **1024** | 300 768 £ (35 v) | 118 897 £ (15 v) | 1 705 123 £ (144 v) | 357 353 £ (24 v) | 3 752 115 £ (299 v) | **897 980 £** (46 v) |
| **1337** | 484 531 £ (42 v) | 94 723 £ (19 v) | 2 531 449 £ (237 v) | 348 743 £ (18 v) | 4 621 564 £ (449 v) | **538 359 £** (23 v) |
| **4096** | 526 193 £ (53 v) | 177 713 £ (20 v) | 2 685 884 £ (216 v) | 650 991 £ (61 v) | 5 500 394 £ (306 v) | **1 035 009 £** (50 v) |
| **8191** | 386 308 £ (40 v) | 136 310 £ (44 v) | 2 418 744 £ (190 v) | 454 054 £ (67 v) | 4 899 290 £ (404 v) | **717 397 £** (90 v) |
| **12345** | 287 677 £ (38 v) | 148 271 £ (42 v) | 1 704 114 £ (132 v) | 207 900 £ (57 v) | 3 635 838 £ (304 v) | **191 748 £** (65 v) |
| **54321** | 310 525 £ (29 v) | 195 288 £ (46 v) | 1 769 991 £ (126 v) | 508 511 £ (53 v) | 3 933 518 £ (320 v) | **970 096 £** (99 v) |
| **65537** | 247 024 £ (32 v) | 184 078 £ (40 v) | 1 425 383 £ (113 v) | 342 149 £ (66 v) | 3 551 398 £ (292 v) | **385 543 £** (70 v) |
| **123456** | 410 326 £ (42 v) | 117 147 £ (25 v) | 2 563 966 £ (192 v) | 426 479 £ (24 v) | 5 269 697 £ (367 v) | **574 626 £** (24 v) |
| **424242** | 537 347 £ (47 v) | 173 804 £ (48 v) | 2 879 407 £ (217 v) | 340 649 £ (72 v) | 5 729 103 £ (400 v) | **339 140 £** (80 v) |
| **8675309** | 462 788 £ (54 v) | 66 722 £ (18 v) | 2 358 772 £ (171 v) | 161 070 £ (18 v) | 5 293 314 £ (349 v) | **326 565 £** (59 v) |
| **Moyenne** | **423 595 £ (42.1 v)** | **130 154 £ (31.8 v)** | **2 388 296 £ (179.4 v)** | **335 868 £ (45.0 v)** | **4 952 091 £ (376.5 v)** | **530 297 £ (63.4 v)** |

---

## 4. Synthèse des Résultats

- **Record historique de performance moyenne** : **530 297 £** (contre 379 k£ précédemment).
- **Rétablissement spectaculaire de la graine 1** : Passe de **30 878 £** à **583 596 £** ($\times 19$).
- **Multiplication des graines à très haute valeur** :
  - Graine **7** : **1 074 809 £**
  - Graine **4096** : **1 035 009 £**
  - Graine **54321** : **970 096 £**
  - Graine **1024** : **897 980 £**
  - Graine **8191** : **717 397 £**
  - Graine **73** : **631 045 £**
