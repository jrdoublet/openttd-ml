# Rapport AFM — Mesure télémétrique de la marge de financement et du risque réel des aéroports (5×3, 1970–1972)

**Dépôt :** `/home/deploy/projects/openttd-ml` (lecture seule, commit `29dac01`, 12/10/2026).  
**Corpus analysé :** Banc 1v1 5 graines × 3 ans duel AAAHogEx `results/afm_probe_5x3_20261012_engine/` :
- **Bras référence (5 parties) :** `reference_seed{42,100,999,1234,5678}_r0.log` (`probe_air_finance_margin=1`, `air_site_cost_quote=0`, marge historique 30/12/2 k£).
- **Bras variante V126 (5 parties) :** `V126_seed{42,100,999,1234,5678}_r0.log` (`probe_air_finance_margin=1`, `air_site_cost_quote=1`, `air_site_cost_margin_pct=0`, marge résiduelle 2 000 £).
- **Options de campagne :** `decision_log=1`, `--script-debug`. 10 parties complètes et saines.
- **Résultat macro C66.4 (launcher) :** delta profit moyen OpexAI −8 686 £/an, médiane +116 151 £/an, V/D/E 3/2/0, Wilcoxon p=1.0, IC95 bootstrap [−258 042 ; +189 556] £/an, ratio valeur 1.0329 (garde tenue), verdict moteur `diagnostic_only`.

---

## 1. Aéroports construits par an

La télémétrie `AIR_FINANCE_TRY` avec `outcome=built` permet de distinguer le nombre de lignes construites (`built`) et le nombre effectif d'aéroports neufs posés (`new_airports` : 2 pour `newpair`, 1 pour `hubsite`, 0 pour `hubhub`).

### 1.1 Répartition par graine et par année

| Bras | Graine | 1970 (L / A neufs) | 1971 (L / A neufs) | 1972 (L / A neufs) | Total Lignes | Total Aéroports Neufs | Détail lignes (np / hs / hh) |
|---|---|---:|---:|---:|---:|---:|---|
| **Référence** | 42 | 10 (19 neufs) | 28 (15 neufs) | 13 (4 neufs) | **51** | **38** | 10 np / 18 hs / 23 hh |
| | 100 | 10 (15 neufs) | 18 (5 neufs) | 12 (9 neufs) | **40** | **29** | 7 np / 15 hs / 18 hh |
| | 999 | 5 (7 neufs) | 14 (16 neufs) | 11 (8 neufs) | **30** | **31** | 8 np / 15 hs / 7 hh |
| | 1234 | 6 (10 neufs) | 8 (13 neufs) | 30 (10 neufs) | **44** | **33** | 9 np / 15 hs / 20 hh |
| | 5678 | 9 (17 neufs) | 24 (17 neufs) | 10 (6 neufs) | **43** | **40** | 13 np / 14 hs / 16 hh |
| *Sous-total Réf* | *5 graines* | **40 (68 neufs)** | **92 (66 neufs)** | **76 (37 neufs)** | **208** | **171** | **47 np / 77 hs / 84 hh** |
|---|---|---:|---:|---:|---:|---:|---|
| **V126** | 42 | 10 (19 neufs) | 30 (13 neufs) | 10 (7 neufs) | **50** | **39** | 14 np / 11 hs / 25 hh |
| | 100 | 10 (15 neufs) | 19 (7 neufs) | 12 (6 neufs) | **41** | **28** | 6 np / 16 hs / 19 hh |
| | 999 | 6 (11 neufs) | 17 (13 neufs) | 12 (9 neufs) | **35** | **33** | 9 np / 15 hs / 11 hh |
| | 1234 | 6 (11 neufs) | 8 (12 neufs) | 10 (9 neufs) | **24** | **32** | 12 np / 8 hs / 4 hh |
| | 5678 | 9 (17 neufs) | 28 (17 neufs) | 7 (1 neuf) | **44** | **35** | 11 np / 13 hs / 20 hh |
| *Sous-total V126* | *5 graines* | **41 (73 neufs)** | **102 (62 neufs)** | **51 (32 neufs)** | **194** | **167** | **52 np / 63 hs / 79 hh** |

### 1.2 Analyse temporelle de la pose
- **1970 :** La variante V126 pose légèrement plus tôt (+5 aéroports neufs au démarrage : 73 vs 68, et 32 newpairs vs 28), profitant de l'abaissement de la marge pour engager des paires dès que les fonds atteignent le devis + 2 k£.
- **1971 :** V126 réalise davantage de lignes au total (102 vs 92), mais avec une proportion accrue de maillages `hubhub` (52 vs 41).
- **1972 :** La référence rattrape son retard en ouvrant massivement des lignes à coût modéré (76 vs 51), notamment sur la graine 1234 (30 lignes dont 20 hubhub en référence contre 10 lignes en V126 où des échecs de pose ont ralenti le déploiement).
- **Total 3 ans :** Le nombre d'aéroports neufs posés est très proche (171 en référence vs 167 en V126), mais V126 construit un peu plus de `newpair` (52 vs 47) et moins de `hubsite` (63 vs 77).

---

## 2. Écart coût réel / coût prévu des aéroports

### 2.1 Écart macroéconomique `actual − planned` et dépassement de la marge appliquée

La métrique compare le coût réel décaissé (`actual`, issu de `AIAccounting`) au capital prévu (`planned`). La part de dépassement mesure la fréquence où `actual − planned > margin`.

| Bras | Graine | Écart médian (£) | Écart p90 (£) | Écart max (£) | Ratio médian | Ratio p90 | Ratio max | Dépassements marge (/total built) | Dépassements marge (/sites neufs) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Référence** | 42 | +1 965 | +12 863 | +23 396 | 1.022 | 1.216 | 1.424 | 4 / 51 (7.8 %) | 4 / 28 (14.3 %) |
| | 100 | +960 | +7 610 | +45 599 | 1.011 | 1.139 | 1.827 | 3 / 40 (7.5 %) | 3 / 22 (13.6 %) |
| | 999 | +1 746 | +9 560 | +15 618 | 1.021 | 1.155 | 1.258 | 2 / 30 (6.7 %) | 2 / 23 (8.7 %) |
| | 1234 | +712 | +12 921 | +31 447 | 1.009 | 1.238 | 1.543 | 4 / 44 (9.1 %) | 4 / 24 (16.7 %) |
| | 5678 | +2 276 | +15 925 | +39 970 | 1.032 | 1.251 | 1.691 | 2 / 43 (4.7 %) | 2 / 27 (7.4 %) |
| **Réf Agrégé** | **5 graines** | **+1 072** | **+12 551** | **+45 599** | **1.018** | **1.197** | **1.827** | **15 / 208 (7.2 %)** | **15 / 124 (12.1 %)** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **V126** | 42 | 0 | +299 | +8 865 | 1.000 | 1.004 | 1.115 | 2 / 50 (4.0 %) | 2 / 25 (8.0 %) |
| | 100 | 0 | +1 275 | +7 380 | 1.000 | 1.020 | 1.127 | 2 / 41 (4.9 %) | 2 / 22 (9.1 %) |
| | 999 | 0 | +1 068 | +7 189 | 1.000 | 1.017 | 1.121 | 3 / 35 (8.6 %) | 3 / 24 (12.5 %) |
| | 1234 | +188 | +6 460 | +11 790 | 1.002 | 1.092 | 1.219 | 4 / 24 (16.7 %) | 4 / 20 (20.0 %) |
| | 5678 | 0 | +935 | +11 235 | 1.000 | 1.014 | 1.211 | 3 / 44 (6.8 %) | 3 / 24 (12.5 %) |
| **V126 Agrégé**| **5 graines** | **0** | **+1 230** | **+11 790** | **1.000** | **1.017** | **1.219** | **14 / 194 (7.2 %)** | **14 / 115 (12.2 %)** |

*Note sur le filtre :* Tous les 15 dépassements de la référence et les 14 dépassements de V126 portent **exclusivement sur des chantiers avec au moins 1 nouvel aéroport** (0 dépassement sur les 84/79 hubhub).

### 2.2 Décomposition fine V126 sur les chantiers à sites neufs

Sur les 115 chantiers réussis de V126 comportant des aéroports neufs (167 extrémités neuves) :
1. **Précision du devis de nivellement (`c_level − quote`) :**
   - Médiane = **−45 £**, p90 = **0 £**, max = **+15 £**.
   - Le devis de nivellement est quasi-parfait : sur les 167 sites neufs, 100 % des devis sont exacts ou très légèrement sous-estimés de moins de 15 £.
2. **Défrichage non devisé (`c_airport − prix_catalogue_16200`) :**
   - Médiane = **+666 £**, p90 = **+3 617 £**, max = **+12 375 £**.
   - **C'est la cause numéro 1 des surcoûts :** `AIAirport.BuildAirport` facture les arbres, routes et rochers présents sur l'emprise. Ce défrichage n'est ni inclus dans le prix catalogue fixe (16 200 £), ni testé par `AITile.LevelTiles`.
3. **Arrêts joints (`c_stops / new_airports`) :**
   - Médiane = **225 £**, p90 = **300 £**, max = **487 £**.
   - Le modèle V126 réservant un montant prudent (forfait 2 250 £ ou modélisé 600 £) crée un coussin amortisseur favorable d'environ 300 à 900 £ par site.
4. **Résidu net V126 (`réel − [catalogue + devis connu + arrêts modélisés]`) :**
   - Médiane = **+165 £** (+0.6 % du coût de site).
   - p90 = **+2 848 £** (+11.7 % du coût de site).
   - Maximum = **+11 790 £** (+72.8 % du coût de site).
   - **Part dépassant la marge résiduelle de 2 000 £ : 14 sur 115 (12.2 %)**.

### 2.3 Courbe de couverture des résidus par pourcentage de marge

Quelle part des 115 chantiers à nouveaux aéroports dépasse une marge de la forme `2 000 £ + pct × coût_du_site` ?

| Pourcentage ajouté (`pct`) | Marge médiane résultante (£) | Nombre de chantiers dépassant | Part des chantiers non couverts (%) |
|---:|---:|---:|---:|
| **0 % (plancher 2 000 £ seul)** | **2 000 £** | **14 / 115** | **12.2 %** |
| 5 % | 3 620 £ | 12 / 115 | 10.4 % |
| 10 % | 5 240 £ | 9 / 115 | 7.8 % |
| 15 % | 6 860 £ | 7 / 115 | 6.1 % |
| **20 %** | **8 480 £** | **6 / 115** | **5.2 %** |
| 25 % | 10 100 £ | 6 / 115 | 5.2 % |
| 30 % | 11 720 £ | 4 / 115 | 3.5 % |
| 40 % | 14 960 £ | 2 / 115 | 1.7 % |
| 50 % | 18 200 £ | 2 / 115 | 1.7 % |
| *Régime historique (12/30 k£)* | *30 000 £* | *14 / 115* | *12.2 %* |

*Constat :* Même avec 20 % de marge ajoutée (marge médiane ~8 500 £), **5.2 % des chantiers subissent un dépassement**, en raison de défrichages exceptionnels dépassant 10 000 £.

---

## 3. Refus pour marge de trésorerie

Le filtre de marge intervient lors du dernier contrôle de liquidité d'exécution (`task_air.nut:396` et `753`) lorsque `cash < need` mais `cash >= capital + reserve`.

### 3.1 Nombre d'événements, déficit et devenir des projets

| Bras | Graine | Refus marge (événements) | Paires de villes distinctes | Déficit médian (£) | Déficit p90 (£) | Min (£) | Max (£) | Paires construites plus tard | Délai médian (jours) | Paires jamais construites |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Référence** | 42 | 14 | 14 | 5 381 | 5 460 | 5 285 | 5 484 | 2 / 14 | 90 j | 12 / 14 (85.7 %) |
| | 100 | 0 | 0 | — | — | — | — | 0 | — | 0 |
| | 999 | 0 | 0 | — | — | — | — | 0 | — | 0 |
| | 1234 | 0 | 0 | — | — | — | — | 0 | — | 0 |
| | 5678 | 54 | 54 | 9 146 | 28 692 | 8 969 | 28 692 | 5 / 54 | 144 j | 49 / 54 (90.7 %) |
| **Réf Agrégé** | **5 graines** | **68** | **68** | **9 110** | **28 692** | **5 285** | **28 692** | **7 / 68 (10.3 %)** | **143 j** | **61 / 68 (89.7 %)** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **V126** | 42 | 0 | 0 | — | — | — | — | 0 | — | 0 |
| | 100 | 0 | 0 | — | — | — | — | 0 | — | 0 |
| | 999 | 0 | 0 | — | — | — | — | 0 | — | 0 |
| | 1234 | 1 | 1 | 120 | 120 | 120 | 120 | 0 / 1 | — | 1 / 1 (100 %) |
| | 5678 | 7 | 7 | 118 | 207 | 59 | 229 | 0 / 7 | — | 7 / 7 (100 %) |
| **V126 Agrégé**| **5 graines** | **8** | **8** | **119** | **203** | **59** | **229** | **0 / 8 (0 %)** | **—** | **8 / 8 (100 %)** |

### 3.2 Enseignements sur les refus
1. **Éradication quasi-totale des refus d'exécution sous V126 :** Les refus tombent de 68 à 8.
2. **Nature des déficits :**
   - En référence, les déficits sont massifs (médiane 9 110 £, p90 28 692 £) : ils représentent l'épaisseur même de la marge de 12 k£ ou 30 k£.
   - En V126, les 8 refus résiduels sont infimes (59 à 229 £), causés par des micro-variations de caisse (intérêts de prêt ou maintenance de véhicules) survenant le jour même de la tentative.
3. **Conséquence économique majeure :**
   - En référence, **89.7 % des projets refusés (61/68) n'ont jamais été construits** sur l'horizon de 3 ans.
   - Pour les 7 projets ayant fini par aboutir, le délai moyen d'attente est de **143 jours** (près de 5 mois de perte d'exploitation).

---

## 4. Échecs de pose AFAIL/BFAIL et coût perdu

Lorsqu'un chantier physique échoue (`AIR_FINANCE_TRY outcome=failed`), les fonds déjà dépensés sont mesurés par `AIAccounting` au moment de la sortie.

### 4.1 Bilan des échecs et coûts perdus par graine

| Bras | Graine | Échecs totaux | AFAIL (nb / coût) | BFAIL (nb / coût) | Autre (PLANE) | Coût perdu total (£) | Coût perdu médian (£) | Coût perdu max (£) | Orphelins A retenus |
|---|---|---:|---|---|---|---:|---:|---:|---:|
| **Référence** | 42 | 3 | 1 / 898 £ | 2 / 9 443 £ | 0 | 10 341 | 1 564 | 7 879 | 0 |
| | 100 | 5 | 3 / 21 437 £ | 2 / 2 629 £ | 0 | 24 066 | 7 610 | 12 627 | 0 |
| | 999 | 6 | 1 / 8 754 £ | 5 / 64 468 £ | 0 | 73 222 | 8 754 | 25 435 | 2 |
| | 1234 | 3 | 2 / 8 344 £ | 0 / 0 £ | 1 / 51 603 £ | 59 947 | 5 799 | 51 603 | 0 |
| | 5678 | 38 | 7 / 33 268 £ | 31 / 52 401 £ | 0 | 85 669 | 0 | 30 543 | 2 |
| **Réf Agrégé** | **5 graines** | **55** | **14 / 72 701 £** | **40 / 128 941 £** | **1 / 51 603 £** | **253 245 £** | **0 £** | **51 603 £** | **4** |
|---|---|---:|---|---|---|---:|---:|---:|---:|
| **V126** | 42 | 3 | 2 / 2 619 £ | 1 / 7 939 £ | 0 | 10 558 | 1 721 | 7 939 | 0 |
| | 100 | 4 | 2 / 13 102 £ | 2 / 4 168 £ | 0 | 17 270 | 5 160 | 7 610 | 0 |
| | 999 | 7 | 2 / 9 706 £ | 5 / 85 298 £ | 0 | 95 004 | 8 739 | 25 495 | 3 |
| | 1234 | 5 | 1 / 5 859 £ | 4 / 60 807 £ | 0 | 66 666 | 14 777 | 29 621 | 2 |
| | 5678 | 40 | 8 / 0 £ | 32 / 134 341 £ | 0 | 134 341 | 0 | 30 573 | 4 |
| **V126 Agrégé**| **5 graines** | **59** | **15 / 31 286 £** | **44 / 292 553 £** | **0** | **323 839 £** | **0 £** | **30 573 £** | **9** |

### 4.2 Anatomie du risque BFAIL
1. **L'asymétrie AFAIL vs BFAIL :**
   - En cas d'AFAIL (échec sur la première extrémité), seul le terrassement partiel est perdu : coût médian modéré (0 à 1 872 £, max 8 739 £ hors cas extrêmes).
   - En cas de BFAIL (échec sur la seconde extrémité), **l'aéroport A a déjà été construit** (prix catalogue 16 200 £ + défrichage/terrassement de 5 000 à 14 000 £). La perte instantanée de caisse est de **20 000 à 30 000 £ par BFAIL** !
2. **L'aggravation sous V126 :**
   - Le coût total perdu en BFAIL passe de 128 941 £ en référence à **292 553 £ en V126** (+127 %).
   - En abaissant la marge à 2 000 £, OpexAI s'engage dans des chantiers avec un coussin financier insuffisant pour encaisser le choc d'un BFAIL.
   - Sur les graines 999, 1234 et 5678, BFAIL consomme respectivement 85 k£, 61 k£ et 134 k£ de trésorerie sèche.

---

## 5. Jours bloqués à cause de la marge en 1970–1971

Le blocage amont est mesuré directement par l'événement `AIR_FINANCE_SELECT` (`projects_selection.nut:2135`), qui identifie à chaque passe les projets où `capital <= budget < capital + marge`.

### 5.1 Bilan des blocages par graine

| Bras | Graine | Passes bloquées 1970 | Jours uniques 1970 (stricts*) | Passes bloquées 1971 | Jours uniques 1971 (stricts*) | Total Jours 1970-1971 | Total Stricts 1970-1971 | Déficit médian au Vivier (£) | Déficit p90 au Vivier (£) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Référence** | 42 | 156 | 123 j (122 j) | 86 | 70 j (37 j) | 193 j | 159 j | 10 748 | 21 907 |
| | 100 | 51 | 48 j (38 j) | 35 | 28 j (19 j) | 76 j | 57 j | 8 309 | 25 232 |
| | 999 | 90 | 62 j (55 j) | 112 | 83 j (27 j) | 145 j | 82 j | 11 234 | 19 576 |
| | 1234 | 36 | 36 j (29 j) | 69 | 60 j (49 j) | 96 j | 78 j | 9 366 | 25 615 |
| | 5678 | 111 | 87 j (81 j) | 82 | 58 j (8 j) | 145 j | 89 j | 12 552 | 24 464 |
| **Réf Moyenne**| **par graine**| **88.8** | **71.2 j (65.0 j)** | **76.8** | **59.8 j (28.0 j)** | **131.0 j** | **93.0 j** | **10 442** | **23 359** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **V126** | 42 | 22 | 21 j (10 j) | 27 | 24 j (7 j) | 45 j | 17 j | 1 161 | 1 812 |
| | 100 | 17 | 16 j (8 j) | 21 | 18 j (6 j) | 34 j | 14 j | 1 200 | 1 892 |
| | 999 | 8 | 8 j (4 j) | 20 | 18 j (0 j) | 26 j | 4 j | 1 352 | 1 838 |
| | 1234 | 7 | 7 j (2 j) | 21 | 20 j (5 j) | 27 j | 7 j | 1 283 | 1 689 |
| | 5678 | 14 | 14 j (0 j) | 26 | 22 j (0 j) | 36 j | 0 j | 1 380 | 1 890 |
| **V126 Moyenne**| **par graine**| **13.6** | **13.2 j (4.8 j)** | **23.0** | **20.4 j (3.6 j)** | **33.6 j** | **8.4 j** | **1 275** | **1 824** |

*\* Jours stricts :* Jours où `top_mode == "none"`, c'est-à-dire où l'IA n'a sélectionné **aucun autre mode alternatif** (ni rail, ni route, ni eau) et s'est retrouvée totalement inactive faute de pouvoir franchir la marge.

### 5.2 Comparaison des blocages
- **Réduction massive sous V126 :** Les jours bloqués par la marge tombent de **131 jours à 33.6 jours** par graine en 1970–1971 (−74.3 %).
- **Jours d'inactivité totale (stricts) :** Ils s'effondrent de **93.0 jours à 8.4 jours** par graine (−91.0 %).
- **Déficit budgétaire :** Le déficit médian passe de 10 442 £ en référence (inférieur aux 30 k£ de marge) à seulement 1 275 £ sous V126 (inférieur aux 2 000 £ de marge résiduelle).

---

## 6. Marqueurs de log utilisés et localisation dans le code

Tous les fichiers et numéros de ligne ci-dessous ont été vérifiés sur l'arbre courant :

| Donnée mesurée | Marqueur de log exact | Fichier Squirrel source | Lignes réelles | Fonction d'émission et condition |
|---|---|---|---|---|
| **Exécution & Coût réel AIAccounting** | `AIR_FINANCE_TRY` | `ai/OpexAI/task_air.nut` | L. 42–58, 398, 424, 756, 800 | `OpexAirFinanceMarginLogTry` émis sous `PROBE_AIR_FINANCE_MARGIN=1` lors de chaque contrôle cash et fin de chantier `OpexBuildAirRoute` |
| **Champs V126 (devis, arrêts, ventilation)** | `v126= quote_a= c_level_a= c_airport_a= c_stops=` | `ai/OpexAI/task_air.nut` | L. 61–93 | `OpexAirV126FinanceFields` et `OpexAirV126CostFields`, concaténés à `AIR_FINANCE_TRY` |
| **Blocage marge au portefeuille (Vivier)** | `AIR_FINANCE_SELECT` | `ai/OpexAI/projects_selection.nut` | L. 1486, 2118–2145 | `OpexAirFinanceMarginLogSelect` émis dans `OpexSelectBestProjects` sous `PROBE_AIR_FINANCE_MARGIN=1` |
| **Premier revenu & fenêtre de liquidité** | `AIR_FINANCE_FIRST_REVENUE` et `AIR_FINANCE_PENDING` | `ai/OpexAI/task_air.nut` | L. 255–288, 1071 | `OpexAirFinanceMarginTick` émis sur les lignes actives sous `PROBE_AIR_FINANCE_MARGIN=1` |
| **Motifs d'échec de pose** | `PROJECT_DISCARD reason=build_failed detail=...` | `ai/OpexAI/task_air.nut` | L. 762, 839 | Émis sous `DECISION_LOG=1` avec code d'erreur NoAI |
| **Orphelins conservés après BFAIL** | `orphan_kept=1` et `AIR_ORPHAN_RETAIN` | `ai/OpexAI/air_construction.nut` | L. 478, 502 | Émis dans `OpexBuildAirRoute` lorsque l'aéroport A orphelin est conservé sans démolition |

---

## 7. Ce qui n'est pas mesurable

1. **L'identité unique des opportunités écartées au Vivier :**  
   `AIR_FINANCE_SELECT` journalise le nombre de projets bloqués par passe (`blocked_margin=N`) et les caractéristiques du *meilleur* projet (`blk_profit`, `blk_finance`), mais pas la liste nominative de tous les projets candidats. Comme la passe s'exécute tous les ~10 ticks, les mêmes projets génèrent des dizaines de comptages répétés.
2. **La valeur économique nette des opportunités manquées :**  
   Pour les 61 paires de villes définitivement abandonnées en référence, on ignore le profit réel qu'elles auraient produit (déduction faite de la saturation de l'espace aérien et du cannibalisme inter-hubs), ainsi que la rentabilité des investissements alternatifs réalisés à leur place.
3. **La liquidation / valorisation à long terme des aéroports orphelins :**  
   Lors d'un BFAIL, la station A est conservée (`orphan_kept=1`, 4 cas en référence, 9 en V126). Avec la maintenance d'infrastructure à 0, elle ne produit pas de coût récurrent, et peut être réutilisée plus tard comme hub. Le coût décaissé à l'échec (~20–30 k£) n'est donc pas une pure perte destructrice, mais un actif gelé sans recette immédiate. Le banc 3 ans ne mesure pas le taux de réemploi ultérieur à 5 ou 10 ans.
4. **La cause physique exacte des BFAIL :**  
   Le journal fournit le code d'erreur (`error=263 airport footprint remains non-flat` ou `error=2 invalid airport footprint`), mais n'enregistre pas l'événement exact ayant altéré l'emprise entre le scan et la pose (construction d'une maison municipale, route rivale posée par AAAHogEx, ou relief complexe en bord de carte).
5. **Le biais de sélection sur les quantiles de coût :**  
   Les quantiles de coût réel / devis (médiane +165 £, p90 +2 848 £) ne sont mesurés que sur les chantiers **réussis**. Les échecs BFAIL/AFAIL en sont exclus par construction, ce qui masque l'impact financier de l'échec dans l'évaluation du risque d'exécution.

---

## 8. Conclusion économique

### 8.1 La marge actuelle est-elle justifiée par le risque réel mesuré ?

**Non, ni la marge historique (30/12/2 k£), ni la marge minimale de 2 000 £ ne sont adaptées à la réalité économique mesurée :**

1. **La marge historique (30 k£ newpair, 12 k£ hubsite) est excessivement restrictive sur les coûts de chantier normaux :**
   - Le surcoût réel de nivellement est quasi-nul (médiane −45 £, p90 0 £).
   - Le surcoût médian tous postes confondus sur les chantiers réussis n'est que de **+165 £** (+0.6 % du coût de site).
   - En immobilisant 30 000 £ par couple de villes, cette marge bloque artificiellement la sélection amont pendant **131 jours par graine en 1970–1971** (dont **93 jours d'inactivité totale**), conduisant à l'abandon définitif de **89.7 % des opportunités d'ouverture**.

2. **Mais la baisse directe à 2 000 £ (V126 brut) est excessivement dangereuse et économiquement perdante :**
   - **Risque de chantier résiduel :** 12.2 % des chantiers réussis dépassent 2 000 £ (jusqu'à +11 790 £ de surcoût), principalement à cause du défrichage d'arbres/bâtiments facturé par `AIAirport.BuildAirport` (médiane +666 £, p90 +3 617 £, max +12 375 £).
   - **Risque d'échec BFAIL dévastateur :** Avec 8 à 9 BFAIL par partie et une perte sèche de **20 000 à 30 000 £ par échec** (l'aéroport A étant payé avant que B n'échoue), une marge de 2 000 £ laisse la trésorerie sans aucune protection. Les coûts perdus en BFAIL s'envolent à **292 553 £** en V126.
   - Ce mécanisme explique pourquoi la variante V126 perd de l'argent au banc économique global (−8 686 £/an sur ce 5×3, −70 729 £/an sur le 6×3 du 08/10).

### 8.2 Quel pourcentage de marge résiduelle le risque observé justifierait-il ?

Pour concilier la fluidité des ouvertures (suppression des 131 jours bloqués) et la solvabilité de l'entreprise :

1. **Pour couvrir le risque de chantier des réussites (défrichage & imprévus) :**
   - Un pourcentage de **15 % à 20 % du coût du site** ajouté au plancher de 2 000 £ (soit une marge de **~5 200 à 8 500 £** par chantier comportant un ou deux aéroports neufs) permet de couvrir **94 % à 95 % des chantiers réussis**.
   - Au-delà de 20 %, chaque point de pourcentage supplémentaire apporte peu de couverture (les surcoûts extrêmes étant isolés à > 11 k£) tout en recréant des retards de sélection inutiles.

2. **Pour couvrir le risque combiné (dépasser les 2 000 £ ET absorber le risque BFAIL) :**
   - Une simple marge proportionnelle au site (ex. 20 %) ne peut pas compenser à elle seule une perte sèche de 25 000 £ lors d'un BFAIL survenant 8 fois par partie.
   - **La recommandation économique optimale sans toucher au catalogue AIR s'établit en deux volets :**
     1. **Calibrage de la marge résiduelle :** Adopter une marge intermédiaire combinant un plancher plus protecteur sur les paires neuves et un pourcentage de site :
        - `hubhub` (0 aéroport neuf) : **2 000 £** (risque résiduel nul, 0 dépassement observé).
        - `hubsite` (1 aéroport neuf) : **6 000 £ + 10 % du coût de site** (~8 000 £ total).
        - `newpair` (2 aéroports neufs) : **12 000 £ + 10 % du coût de site** (~16 000 £ total, divisant par deux la barrière historique de 30 000 £ tout en garantissant un coussin de sécurité face au risque BFAIL).
     2. **Fiabilisation amont de l'infrastructure (hors catalogue) :** Pré-vérifier la constructibilité de l'aéroport B (`AITestMode` sur l'emprise B) **immédiatement avant de poser l'aéroport A**, afin de neutraliser à la source les 292 k£ de pertes BFAIL sans avoir besoin de gonfler indûment les marges de trésorerie.

---

## Note de relecture (Claude, 12/10)

- **Lien causal BFAIL ↔ marge à rejeter.** La marge ne décide pas si l'extrémité B échoue : elle décide seulement si l'on tente le chantier. La hausse des pertes BFAIL sous V126 (44 contre 40 échecs, 292 k£ contre 129 k£) vient surtout de la graine 5678 (32 BFAIL, emprises en bord de carte, cf. V145) et du nombre de tentatives, pas d'une « absence de coussin ».
- **Le pré-test de B avant A existe déjà** (`air_efficiency_preflight`, `air_bfail_precheck_shadow`, étudiés le 09/10 : [rapport](air_bfail_precheck_shadow_20261009.md)). La piste 2 de la conclusion n'est pas nouvelle.
- **« V126 perd de l'argent » n'est pas établi** : sur ce 5×3, Δ moyen −8,7 k£ mais médiane +116 k£, 3 V/2 D, IC95 [−258 k ; +190 k].
- **Acquis utilisables :** devis de nivellement exact ; surcoût résiduel dominé par le défrichage non devisé (médiane +666 £, p90 +3,6 k£) ; marge historique = 131 jours bloqués par graine en 1970-71 (93 d'inactivité totale), contre 34 (8) sous V126 ; une marge de 15 % du coût de site couvre 94 % des chantiers réussis.
- **Suite :** candidat V126 calibré `air_site_cost_quote=1, air_site_cost_margin_pct=15`, jamais passé au banc (seule la marge de 2 k£ seule avait échoué en porte A le 07/10). Pré-enregistré : porte A 40×3 `gain_short`, seuil +4 %, garde de valeur 5 %.
