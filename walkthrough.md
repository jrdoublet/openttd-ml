# Walkthrough — Analyse et Résultats Comparatifs 1v1 (AAAHogEx vs OpexAI)

## 1. Diagnostic de la baisse précédente et correctifs appliqués

Lors du banc intermédiaire précédent, la performance moyenne avait chuté à **379 483 £** en raison de deux goulets d'étranglement :
1. **Épuisement prématuré du budget d'essais routiers** : Dans `OpexRoadPlanFor`, tester 6 formes géométriques avec un plafond à `ROAD_MAX_TRACE_TRIALS = 12` arrêtait la recherche après seulement 2 paires de sites testées ($2 \times 6 = 12$), rejetant abusivement 66 % des sites viables.
2. **Désendettement prématuré en Année 2** : Abaisser le plancher d'emprunt à 50 000 £ ponctionnait la trésorerie disponible pour rembourser une dette à 4 % d'intérêt au détriment de l'investissement dans des lignes rapportant > 150 % de retour sur investissement.

### Correctifs apportés :
- **Architecture de tracé en 2 passes** : Test prioritaire des $L$ directs sur l'ensemble des paires de sites, puis bascule sur les déviations en $Z$ et contournements si nécessaire.
- **Déblocage du maillage inter-villes** : Remplacement du plafond arbitraire de 4 lignes par ville par un quota dynamique proportionnel à la population (`4 + pop / 300`) et calcul réaliste du flux passagers restant.
- **Préservation intégrale du capital de croissance** : Maintien du plancher d'emprunt à 300 000 £ pour maximiser la capitalisation et le réinvestissement dans les 3 premières années.

---

## 2. Tableau comparatif Année par Année (20 graines × 3 ans)

| Graine | AAAHogEx An 1<br>(Val / Véh) | OpexAI An 1<br>(Val / Véh) | AAAHogEx An 2<br>(Val / Véh) | OpexAI An 2<br>(Val / Véh) | AAAHogEx An 3<br>(Val / Véh) | OpexAI An 3<br>(Val / Véh) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 541 603 £ (48 v) | 44 563 £ (25 v) | 2 836 303 £ (201 v) | 149 456 £ (36 v) | 5 178 746 £ (358 v) | **406 626 £** (50 v) |
| **100** | 260 997 £ (30 v) | 57 451 £ (34 v) | 1 647 824 £ (161 v) | 199 711 £ (48 v) | 3 396 262 £ (348 v) | **237 199 £** (59 v) |
| **7** | 625 413 £ (54 v) | 249 609 £ (66 v) | 3 366 439 £ (232 v) | 618 753 £ (90 v) | 7 278 491 £ (456 v) | **901 817 £** (90 v) |
| **999** | 555 329 £ (52 v) | 155 437 £ (41 v) | 3 158 009 £ (211 v) | 309 242 £ (59 v) | 6 697 320 £ (421 v) | **452 494 £** (76 v) |
| **2026** | 383 415 £ (43 v) | 42 090 £ (20 v) | 2 857 070 £ (185 v) | 42 554 £ (20 v) | 4 958 013 £ (444 v) | **94 741 £** (34 v) |
| **1** | 429 855 £ (43 v) | 70 862 £ (46 v) | 2 703 342 £ (195 v) | 50 260 £ (51 v) | 5 432 273 £ (444 v) | **30 878 £** (60 v) |
| **17** | 487 996 £ (37 v) | 150 751 £ (22 v) | 2 369 056 £ (148 v) | 440 898 £ (53 v) | 4 589 682 £ (413 v) | **645 531 £** (52 v) |
| **73** | 472 492 £ (38 v) | 150 965 £ (40 v) | 2 769 190 £ (179 v) | 378 860 £ (62 v) | 5 736 159 £ (396 v) | **631 633 £** (79 v) |
| **314** | 400 181 £ (48 v) | 175 493 £ (51 v) | 2 639 564 £ (200 v) | 270 829 £ (57 v) | 6 157 617 £ (437 v) | **298 404 £** (74 v) |
| **512** | 361 134 £ (37 v) | 163 565 £ (34 v) | 1 376 296 £ (138 v) | 227 437 £ (40 v) | 3 361 187 £ (338 v) | **311 901 £** (54 v) |
| **1024** | 300 768 £ (35 v) | 93 809 £ (19 v) | 1 705 123 £ (144 v) | 249 892 £ (19 v) | 3 752 115 £ (299 v) | **388 555 £** (21 v) |
| **1337** | 484 531 £ (42 v) | 26 541 £ (14 v) | 2 531 449 £ (237 v) | 198 950 £ (37 v) | 4 619 519 £ (475 v) | **514 651 £** (56 v) |
| **4096** | 526 193 £ (53 v) | 162 875 £ (20 v) | 2 685 884 £ (216 v) | 584 660 £ (60 v) | 5 500 394 £ (306 v) | **1 109 476 £** (117 v) |
| **8191** | 386 308 £ (40 v) | 167 136 £ (43 v) | 2 418 744 £ (190 v) | 512 947 £ (65 v) | 4 899 290 £ (404 v) | **1 022 731 £** (81 v) |
| **12345** | 287 677 £ (38 v) | 34 741 £ (50 v) | 1 704 114 £ (132 v) | 141 100 £ (69 v) | 3 635 838 £ (304 v) | **147 876 £** (83 v) |
| **54321** | 310 525 £ (29 v) | 90 330 £ (29 v) | 1 769 991 £ (126 v) | 427 939 £ (78 v) | 3 933 518 £ (320 v) | **638 129 £** (83 v) |
| **65537** | 247 024 £ (32 v) | 183 421 £ (41 v) | 1 425 383 £ (113 v) | 324 860 £ (64 v) | 3 551 398 £ (292 v) | **439 102 £** (81 v) |
| **123456** | 410 326 £ (42 v) | 137 748 £ (34 v) | 2 563 966 £ (192 v) | 270 202 £ (34 v) | 5 269 697 £ (367 v) | **544 845 £** (64 v) |
| **424242** | 537 347 £ (47 v) | 157 822 £ (46 v) | 2 879 407 £ (217 v) | 356 132 £ (79 v) | 5 729 103 £ (400 v) | **344 765 £** (80 v) |
| **8675309** | 462 788 £ (54 v) | 45 941 £ (18 v) | 2 358 772 £ (171 v) | 119 444 £ (18 v) | 5 293 314 £ (349 v) | **316 050 £** (41 v) |
| **Moyenne** | **423 595 £ (42.1 v)** | **118 058 £ (34.6 v)** | **2 388 296 £ (179.4 v)** | **293 706 £ (52.0 v)** | **4 948 497 £ (378.6 v)** | **473 870 £ (66.8 v)** |

---

## 3. Synthèse de progression

- **Flotte totale moyenne** : Record absolu à **66,8 véhicules** (+25 % de véhicules actifs par rapport au banc précédent).
- **Graines millionnaires** :
  - Graine **4096** : **1 109 476 £** (117 véhicules, 22 stations)
  - Graine **8191** : **1 022 731 £** (81 véhicules, 26 stations)
  - Graine **7** : **901 817 £** (90 véhicules, 18 stations)
  - Graine **17** : **645 531 £** (52 véhicules)
  - Graine **54321** : **638 129 £** (83 véhicules, 26 stations)
  - Graine **73** : **631 633 £** (79 véhicules, 22 stations)
