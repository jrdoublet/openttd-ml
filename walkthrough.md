# Walkthrough — Banc 1v1 & Déplafonnement de la Croissance OpexAI

Nous avons procédé au retrait des plafonds stricts et exécuté les campagnes comparatives 1v1 (20 graines × 3 ans, 1970) face à AAAHogEx.

## 1. Modifications apportées pour faire sauter les plafonds

1. **Déplafonnement de la flotte routière ([`economy.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/economy.nut) & [`main.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/main.nut))** :
   - Passage de `MAX_ROAD_VEHICLES` initial de 2 à 8.
   - En repeuplement/expansion (`_refleetRoadLines`), dimensionnement dynamique jusqu'à 16 véhicules par ligne selon le stock de cargaison/passagers en attente aux arrêts.
2. **Dimensionnement aérien dynamique ([`main.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/main.nut#L2155))** :
   - Remplacement de la limite d'un avion/an par une boucle d'ajout par palier de charge (jusqu'à 4 avions par passage si le stock et la trésorerie le permettent).
3. **Génération aérienne exhaustive ([`projects.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/projects.nut#L281))** :
   - Évaluation de toutes les lignes aériennes sans filtrage de capital préalable (`maxCapital = 0`), confiant l'arbitrage global au sac à dos 0/1.
4. **Lots de construction multimodale ([`main.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/main.nut#L1475))** :
   - Capacité de construire jusqu'à 4 projets finançables par passage d'ordonnanceur (`maxBatch = 4`).
5. **Maillage multipoints par ville ([`candidates.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/candidates.nut#L990))** :
   - Remplacement du verrouillage global d'origine (`OpexOriginServed`) par un contrôle d'unicité de couple O/D (`OpexRoadPairServed`) et un quota jusqu'à 4 liaisons par ville (`OpexTownRoadLineCount`).

---

## 2. Résultats comparatifs 1v1 (20 graines × 3 ans)

| Graine | OpexAI (*Commit `ebbab62`*) | OpexAI (*Post-Fix*) | OpexAI (*Déplafonné & Maillé*) | AAAHogEx |
| :---: | :---: | :---: | :---: | :---: |
| **42** | 464 140 £ (70 veh) | 348 398 £ (26 veh) | 370 432 £ (16 veh) | 5 178 746 £ (358 veh) |
| **100** | 106 758 £ (19 veh) | 166 418 £ (20 veh) | 212 447 £ (18 veh) | 3 396 262 £ (348 veh) |
| **7** | 1 434 827 £ (63 veh) | 839 747 £ (52 veh) | 834 203 £ (26 veh) | 7 278 491 £ (456 veh) |
| **999** | 539 092 £ (76 veh) | 391 728 £ (53 veh) | 375 783 £ (85 veh) | 6 706 060 £ (427 veh) |
| **2026** | 1 £ (24 veh) | 25 022 £ (46 veh) | 38 192 £ (24 veh) | 4 958 013 £ (444 veh) |
| **1** | 121 241 £ (38 veh) | 1 £ (23 veh) | 86 685 £ (16 veh) | 5 432 273 £ (444 veh) |
| **17** | 868 797 £ (44 veh) | 540 579 £ (47 veh) | 576 650 £ (16 veh) | 4 524 098 £ (350 veh) |
| **73** | 260 469 £ (46 veh) | 110 995 £ (15 veh) | 26 986 £ (10 veh) | 5 736 159 £ (406 veh) |
| **314** | 471 280 £ (51 veh) | 366 371 £ (31 veh) | 247 317 £ (17 veh) | 6 157 617 £ (437 veh) |
| **512** | 466 845 £ (33 veh) | 490 613 £ (25 veh) | 632 467 £ (13 veh) | 3 361 187 £ (338 veh) |
| **1024** | 927 710 £ (44 veh) | 53 227 £ (29 veh) | 1 £ (11 veh) | 3 752 115 £ (299 veh) |
| **1337** | 471 397 £ (56 veh) | 191 232 £ (28 veh) | 199 366 £ (17 veh) | 4 621 564 £ (449 veh) |
| **4096** | 1 005 555 £ (64 veh) | 674 702 £ (32 veh) | 332 289 £ (25 veh) | 5 500 394 £ (306 veh) |
| **8191** | 716 971 £ (46 veh) | 380 944 £ (53 veh) | 318 137 £ (19 veh) | 4 899 290 £ (404 veh) |
| **12345** | 195 884 £ (39 veh) | 88 321 £ (30 veh) | 161 842 £ (24 veh) | 3 635 838 £ (304 veh) |
| **54321** | 492 061 £ (56 veh) | 697 465 £ (27 veh) | 374 672 £ (15 veh) | 3 933 518 £ (320 veh) |
| **65537** | 305 476 £ (56 veh) | 356 120 £ (43 veh) | 354 658 £ (38 veh) | 3 551 398 £ (292 veh) |
| **123456** | 668 205 £ (68 veh) | 477 937 £ (38 veh) | 519 055 £ (20 veh) | 5 269 697 £ (367 veh) |
| **424242** | 260 896 £ (39 veh) | 462 573 £ (40 veh) | 373 534 £ (64 veh) | 5 729 103 £ (400 veh) |
| **8675309** | 651 928 £ (31 veh) | 273 124 £ (22 veh) | 293 150 £ (14 veh) | 5 293 314 £ (349 veh) |
| **Moyenne** | **521 477 £** (48.1 veh) | **346 776 £** (34.0 veh) | **316 393 £** (24.4 veh) | **4 945 757 £** (374.9 veh) |
