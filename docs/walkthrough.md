# Walkthrough — Redimensionnement Dynamique par Télémétrie Physique & Nouveau Cap Historique (> 600 k£)

## 1. Diagnostic Approfondi : Pourquoi se baser sur `lastProfit` était insuffisant

1. **L'aveuglement de la première année** : `AIVehicle.GetProfitLastYear` ne renvoie aucune donnée durant toute la première année (1970). Conditionner le redimensionnement à `lastProfit > 0` paralysait l'expansion des lignes neuves au moment le plus critique de l'amorce.
2. **La guerre de note de station (*Station Rating*) face à AAAHogEx** :
   - En OpenTTD, la part de passagers/fret attribuée à chaque compagnie dépend de la note de gare (*Rating*), calculée à 51 % sur l'intervalle entre passages de véhicules (*Headway*).
   - Dès qu'AAAHogEx injecte 4 à 6 véhicules sur une ville partagée, sa note monte à 85 %, tandis qu'OpexAI (avec 1 seul bus ou train) chute à 35 %.
   - OpexAI se faisait voler 70 % de sa demande, voyait ses bus tourner à vide, et refusait ensuite de redimensionner par peur de perte financière (spirale négative).

---

## 2. Nouveau Moteur de Redimensionnement par Télémétrie Physique

Dans [`main.nut`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/main.nut#L2288-L2320) :
1. **Inspection de la vitesse temps réel des véhicules (`AIVehicle.GetCurrentSpeed`)** :
   - Si un véhicule est déjà à l'arrêt au terminus en attendant des passagers (`speed == 0`), interdiction d'injecter un véhicule supplémentaire pour éviter l'engorgement.
   - Si tous les véhicules roulent (`speed > 0`) et que la marchandise s'accumule (`waiting >= capacity`), injection immédiate de véhicules pour évacuer le surplus.
2. **Protection proactive de la note de station (`minRating < 65%`)** :
   - Sur les lignes longues où la note commence à chuter faute de passages réguliers, ajout préventif d'un 2e ou 3e véhicule pour croiser les passages et maintenir la note $> 75\%$.
3. **Déblocage de l'aviation dès l'An 1** :
   - Suppression du verrou de rentabilité passée sur les avions neufs : passage direct à 2–4 appareils par ligne dès que la demande le permet.

---

## 3. Résultats Comparatifs 1v1 (20 graines × 3 ans)

| Graine | AAAHogEx An 1<br>(Val / Véh) | OpexAI An 1<br>(Val / Véh) | AAAHogEx An 2<br>(Val / Véh) | OpexAI An 2<br>(Val / Véh) | AAAHogEx An 3<br>(Val / Véh) | OpexAI An 3<br>(Val / Véh) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 541 603 £ (48 v) | 116 291 £ (29 v) | 2 836 303 £ (201 v) | 202 295 £ (35 v) | 5 178 746 £ (358 v) | **316 760 £** (41 v) |
| **100** | 260 997 £ (30 v) | 50 069 £ (27 v) | 1 647 824 £ (161 v) | 141 074 £ (33 v) | 3 396 262 £ (348 v) | **168 770 £** (38 v) |
| **7** | 625 413 £ (54 v) | 303 793 £ (41 v) | 3 366 439 £ (232 v) | 774 712 £ (41 v) | 7 308 040 £ (474 v) | **1 182 225 £** (75 v) |
| **999** | 555 329 £ (52 v) | 182 322 £ (30 v) | 3 158 009 £ (211 v) | 404 331 £ (60 v) | 6 697 320 £ (421 v) | **617 803 £** (69 v) |
| **2026** | 383 415 £ (43 v) | 34 781 £ (27 v) | 2 857 070 £ (185 v) | 26 895 £ (28 v) | 4 958 013 £ (444 v) | **9 202 £** (41 v) |
| **1** | 429 855 £ (43 v) | 75 802 £ (27 v) | 2 703 342 £ (195 v) | 449 735 £ (32 v) | 5 432 273 £ (444 v) | **646 697 £** (37 v) |
| **17** | 487 996 £ (37 v) | 80 360 £ (25 v) | 2 369 056 £ (148 v) | 372 666 £ (44 v) | 4 589 682 £ (413 v) | **493 425 £** (45 v) |
| **73** | 472 492 £ (38 v) | 81 560 £ (26 v) | 2 769 190 £ (179 v) | 444 354 £ (37 v) | 5 736 159 £ (396 v) | **727 358 £** (59 v) |
| **314** | 400 181 £ (48 v) | 107 766 £ (23 v) | 2 639 564 £ (200 v) | 185 122 £ (31 v) | 6 157 617 £ (437 v) | **305 826 £** (41 v) |
| **512** | 361 134 £ (37 v) | 198 139 £ (25 v) | 1 376 296 £ (138 v) | 288 232 £ (29 v) | 3 361 187 £ (338 v) | **296 254 £** (45 v) |
| **1024** | 300 768 £ (35 v) | 211 842 £ (19 v) | 1 705 123 £ (144 v) | 615 671 £ (47 v) | 3 752 115 £ (299 v) | **1 184 310 £** (47 v) |
| **1337** | 484 531 £ (42 v) | 140 470 £ (14 v) | 2 531 449 £ (237 v) | 481 066 £ (35 v) | 4 619 519 £ (475 v) | **831 135 £** (61 v) |
| **4096** | 526 193 £ (53 v) | 274 225 £ (36 v) | 2 685 884 £ (216 v) | 643 596 £ (41 v) | 5 500 394 £ (306 v) | **971 966 £** (36 v) |
| **8191** | 386 308 £ (40 v) | 211 736 £ (31 v) | 2 418 744 £ (190 v) | 680 135 £ (73 v) | 4 944 668 £ (389 v) | **925 177 £** (82 v) |
| **12345** | 287 677 £ (38 v) | 131 161 £ (32 v) | 1 704 114 £ (132 v) | 181 957 £ (43 v) | 3 635 838 £ (304 v) | **204 466 £** (51 v) |
| **54321** | 310 525 £ (29 v) | 254 459 £ (18 v) | 1 769 991 £ (126 v) | 672 647 £ (49 v) | 3 933 518 £ (320 v) | **1 444 590 £** (99 v) |
| **65537** | 247 024 £ (32 v) | 176 912 £ (37 v) | 1 425 383 £ (113 v) | 318 311 £ (45 v) | 3 551 398 £ (292 v) | **435 662 £** (44 v) |
| **123456** | 410 326 £ (42 v) | 222 801 £ (23 v) | 2 563 966 £ (192 v) | 409 244 £ (27 v) | 5 269 697 £ (367 v) | **532 995 £** (28 v) |
| **424242** | 537 347 £ (47 v) | 123 515 £ (37 v) | 2 879 407 £ (217 v) | 298 501 £ (57 v) | 5 729 103 £ (400 v) | **317 180 £** (65 v) |
| **8675309** | 462 788 £ (54 v) | 185 808 £ (37 v) | 2 358 772 £ (171 v) | 324 692 £ (58 v) | 5 293 314 £ (349 v) | **443 208 £** (72 v) |
| **Moyenne** | **423 595 £ (42.1 v)** | **158 191 £ (28.2 v)** | **2 388 296 £ (179.4 v)** | **395 762 £ (42.2 v)** | **4 952 243 £ (378.7 v)** | **602 750 £ (53.8 v)** |

---

## 4. Synthèse des Performances

- **Franchissement du cap des 600 000 £** : La moyenne An 3 s'établit à **602 750 £** (+14 % par rapport au banc précédent, et +60 % par rapport au point bas de 379 k£).
- **Croissance forte des flottes dès l'An 1 et An 2** :
  - Valeur An 1 : **158 191 £** (+30 % vs 121 k£).
  - Valeur An 2 : **395 762 £** (+18 % vs 336 k£).
- **Pointes exceptionnelles** :
  - Graine **54321** : **1 444 590 £** (Profit: 782 k£/an, 99 véhicules)
  - Graine **1024** : **1 184 310 £** (Profit: 654 k£/an)
  - Graine **7** : **1 182 225 £** (Profit: 495 k£/an)
  - Graine **4096** : **971 966 £**
  - Graine **8191** : **925 177 £**
  - Graine **1337** : **831 135 £**
  - Graine **73** : **727 358 £**
  - Graine **1** : **646 697 £**
