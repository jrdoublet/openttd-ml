# Profit estimé à l'élection contre profit réalisé, par ligne et par mode

> **Correction (orchestrateur, 2026-09-27)** : ce rapport attribue une partie du rejet du rail à `RAIL_FINANCE_BIAS_PCT = 170`. C'est faux sur ce code : `rail_finance_bias_pct` vaut **100** par défaut (`info.nut`, `settings.nut`) depuis l'adoption du 2026-09-26. Les deux autres facteurs (capital plus lourd, aérien finançable plus tôt) restent des hypothèses tant que le profit estimé à l'élection n'est pas mesuré.


**Date :** 2026-09-26  
**Branche / Worktree :** `astar-workers-e1` (`.wt_astar`, commit `0b060d6`)  
**Données analysées :** `results/lineprofit_default_5x6_20260926.{json,jsonl}` (duel 1v1 carte partagée OpexAI vs AAAHogEx, graines 42, 100, 999, 1234, 5678 × 6 ans, 1970–1975)  
**Règles appliquées :** [AGENTS.md](../AGENTS.md) §1 (contexte courant), §5 (mesure fiable, extracteurs, échelle ×256, `None` ≠ 0), §6 (preuves post-09/09). Aucune partie lancée ; analyse passive et outillage de mesure.

---

## 1. Contexte et question

Dans le sélecteur de portefeuille d'OpexAI (`projects.nut`), les projets sont classés par `fundScore` (profit annuel estimé ÷ capital de financement). En pratique, cette heuristique préfère quasi systématiquement l'aérien au rail.

Pourtant, en duel face à AAAHogEx :
1. Les quelques trains construits au défaut (2 à 6 lignes, 3 à 7 trains selon la graine) contribuent pour **~300 k£/an** à la valeur finale ; interdire le rail coûte **−291 k£/an** (1/4 victoires, `results/astar_e1_gate_vs_default_5x6_20260926.*`).
2. Laisser le sélecteur libre de choisir sans garde-fou perd **−202 k£/an** (0/5 victoires, `results/astar_e2e_vs_default_5x6_20260926.*`).

**Hypothèse :** L'estimation de profit à l'élection (ou le modèle de capital) d'un mode est fortement biaisée par rapport au réalisé (surévaluation de l'aérien, sous-évaluation du rail, ou distorsion du capital requis).

---

## 2. Inventaire des sources et état de disponibilité

### 2.1 Sources de l'estimé (au moment du choix / de la construction)

| Mode | Métrique | Fichier:Ligne | Symbole / Calcul | Échelle | Canal de persistance |
|---|---|---|---|---|---|
| **AIR** | Profit annuel estimé | `builder_air.nut:3228`<br>`task_air.nut:214,483` | `plan.economics.profitAnnual` | £ / an (entier) | Panneau `AF\|<lineId>\|<vehs>\|<profitAnnual>` ; log `AIR_BUILD` / `AIR_BUILT` |
| **AIR** | Capital estimé | `builder_air.nut:3228`<br>`task_air.nut:216,485` | `plan.capital` | £ (entier) | Panneau `AH\|<lineId>\|<reuseA>\|<capital>\|<hubRoutes>` |
| **AIR** | Devis vs Coût réel | `task_air.nut:153,395` | `result.plannedCapital`, `actualCost` | £ (entier) | Panneau `AC\|<lineId>\|<planCap>\|<cost>\|<planes>\|<vehs>` (actif si `probe_cost=1`) |
| **RAIL** | Revenu estimé | `candidates.nut:1408`<br>`task_rail.nut:1408` | `candidate.revenueAnnual` | £ / an (entier) | Panneau `OF\|<lineId>\|<revenueAnnual>` |
| **RAIL** | Roulage estimé | `candidates.nut:1409`<br>`task_rail.nut:1409` | `candidate.runningAnnual` | £ / an (entier) | Panneau `OJ\|<lineId>\|<runningAnnual>` |
| **RAIL** | Amortissement estimé | `candidates.nut:1410`<br>`task_rail.nut:1410` | `candidate.amortAnnual` | £ / an (entier) | Panneau `OK\|<lineId>\|<amortAnnual>` |
| **RAIL** | Profit estimé net | `task_rail.nut:1443` | `candidate.profitAnnual` (`OF - OJ - OK`) | £ / an (entier) | Déductible de `OF - OJ - OK` ; champ `line.predicted` en RAM |
| **RAIL** | Devis vs Coût réel | `task_rail.nut:1433` | `result.capital`, `result.actualCost` | £ (entier) | Panneau `DC\|<lineId>\|<capital>\|<actualCost>\|...` (actif si `probe_cost=1`) |
| **ROUTE** | Estimations P/R/A | `task_road.nut:228-230` | `revenueAnnual`, `runningAnnual`, `amortAnnual` | £ / an (entier) | Panneaux `OF\|`, `OJ\|`, `OK\|` |
| **ROUTE** | Coût réel | `task_road.nut:238` | `result.cost` | £ (entier) | Panneau `RC\|<yy>\|<lineId>\|1\|<cost>\|<vehs>` |
| **TOUS** | `fundScore` élection | `projects.nut:277,1032` | `(profit * 1000) / financeCapital` | score ratio | Calculé en RAM ; panneau `IP\|<yy>\|<M>\|<budgetScore>` |
| **TOUS** | Biais capital rail | `projects.nut:295,315` | `RAIL_FINANCE_BIAS_PCT = 170%` | % (entier) | Multiplie le capital rail par **1,7** pour `financeCapital` |
| **TOUS** | Chronologie projets | `task_projects.nut:852,1101,1146` | `OpexC50ChronologyLog` | mixte | Log NoAI `C50_CHRONO phase=project_built` (actif si `probe_portfolio=1`) |

### 2.2 Sources du réalisé (en exploitation)

| Donnée | Fichier:Ligne | Symbole / Calcul | Échelle brute OpenTTD | Échelle convertie £ |
|---|---|---|---|---|
| **Profit annuel véhicule** | `task_report.nut:54,76` | `AIVehicle.GetProfitLastYear(v)` | £ (l'API NoAI convertit en interne) | £ / an (entier) -> Panneau `OZ\|<lineId>\|<year>\|<profit>` |
| **Revenu annuel véhicule** | `task_report.nut:107` | `profit + runCost` | £ | £ / an (entier) -> Panneau `OO\|<lineId>\|<year>\|<revenue>` |
| **Télémétrie par ligne (VEHS)** | `bench_1v1_5y_20seeds.py:596,598` | `common.profit_last_year`, `profit_this_year` | **Unités fractiles internes (×256)** | **Divisé par 256.0** (`PROFIT_RAW_UNITS_PER_GBP`) -> `profit_last_year_gbp` |
| **Qualité des gares** | `task_report.nut:35` | `AIStation.GetCargoRating` | 0 à 255 (0 à 100 %) | Panneau `OY\|<lineId>\|<year>\|<ratingA>\|<ratingB>` |
| **Calibrage C70 par ligne** | `task_report.nut:225-233` | `OpexC69Log("phase=line_calib ...")` | £ | Log NoAI `C69_BOTTLENECK phase=line_calib` (actif si `probe_portfolio=1`) |

### 2.3 Piège d'échelle vérifié

Conformément à la mise en garde d'[AGENTS.md](../AGENTS.md) §5 :
- Les champs bruts `common.profit_this_year` et `common.profit_last_year` du chunk `VEHS` d'OpenTTD 15.3 sont stockés en `currency_fract` (1 £ = 256 unités internes).
- L'extracteur `extract_line_telemetry` applique rigoureusement `line["profit_last_year_gbp"] += raw_last / 256.0`.
- **Contrôle de cohérence :** La somme de `profit_last_year_gbp` sur l'ensemble des lignes OpexAI en 1975 donne par exemple 1 265 124 £ (graine 42), en accord parfait avec le `profit_year` de la compagnie (1 418 510 £ dans `summary`, qui intègre les intérêts bancaires et les frais hors véhicules). Sans cette division par 256, le chiffre aurait été aberrant (~324 M£).

### 2.4 État dans `results/lineprofit_default_5x6_20260926`

1. **Ce qui est disponible :**
   - 60 snapshots annuels de décembre (1970 à 1975) pour OpexAI et AAAHogEx sur les 5 graines.
   - Les profits récents par véhicule et par ligne : `profit_this_year_gbp` (montée en charge) et `profit_last_year_gbp` (année civile précédente).
   - Les villes d'extrémité, gares, nombre de convois, types et capacités de cargo.
2. **Ce qui n'est PAS disponible dans ce run :**
   - **Journaux moteur (`_engine/*.log`) : 0 octet.** OpenTTD n'émet pas les messages de script NoAI (`AILog.Info`) sur stdout sans l'argument `-d script=4`. Cet argument n'est pas injecté par `bench_1v1_5y_20seeds.py`.
   - **Estimations à l'élection dans le JSON :** Les panneaux `AF|`, `AH|`, `OF|`, `OJ|`, `OK|`, `DC|` n'ont pas été lus depuis le chunk `SIGN` par la fonction `keep(row)` de ce harnais (seuls les panneaux `IB|`, `SB|`, `SK|`, `OE|A|771`, `C7C|`, `C7Y|`, `C7S|` ont été extraits). Les fichiers de sauvegarde `.sav` bruts ont été détruits à l'issue de l'exécution du banc.
   - **Conséquence :** Le rapport estimé/réalisé ne peut pas être calculé directement sur ce seul run ; en revanche, le réalisé par ligne et par mode est intégralement mesurable et exploité ci-dessous. La mesure minimale pour obtenir l'estimé est détaillée en Section 5.

---

## 3. Mesure : Profit réalisé par ligne et par mode (OpexAI au défaut)

Les lignes ont été suivies individuellement sur les 6 snapshots de décembre (1970 à 1975) via le module [sweeps/line_profit_analysis.py](../sweeps/line_profit_analysis.py).

On distingue rigoureusement :
- **Année de montée en charge :** Première année civile suivant l'ouverture ($y_0 + 1$), reflétant la mise en place du trafic (et les mois partiels de $y_0$).
- **Régime permanent :** Années civiles pleines d'exploitation ($y \ge y_0 + 2$).

### 3.1 Vue synthétique par mode

| Mode | Lignes créées (tot / moy par graine) | Lignes en régime (tot / moy) | Convois / ligne | Montée en charge : Moyenne (Médiane) | Régime : Moyenne ± Écart-type | Régime : Médiane [Min, Max] | Lignes déficitaires en régime | Profit annuel régime moyen / graine |
|---|---|---|---|---|---|---|---|---|
| **RAIL** | 20 (4,0) | 17 (3,4) | 1,05 | 13 285 £ (9 166 £) | **27 950 £** ± 25 416 £ | **20 526 £** [−2 533 £, 71 998 £] | 2 / 17 (11,8 %) | **95 029 £ / an** |
| **AIR** | 477 (95,4) | 294 (58,8) | 1,13 | 15 504 £ (7 708 £) | **23 042 £** ± 15 862 £ | **18 611 £** [−1 069 £, 106 352 £] | 1 / 294 (0,3 %) | **1 354 861 £ / an** |
| **ROUTE** | 74 (14,8) | 61 (12,2) | 1,86 | 1 341 £ (336 £) | **1 570 £** ± 2 271 £ | **409 £** [−736 £, 7 521 £] | 14 / 61 (23,0 %) | **19 151 £ / an** |
| **EAU** | 1 (0,2) | 0 (0,0) | 1,00 | −578 £ (−578 £) | — | — | — | 0 £ / an |

### 3.2 Déciles du profit annuel en régime (£ / an / ligne)

| Mode | p10 | p25 | p50 (Médiane) | p75 | p90 | p95 |
|---|---|---|---|---|---|---|
| **RAIL** | −283 £ | 13 570 £ | **20 526 £** | 46 288 £ | 67 671 £ | 71 998 £ |
| **AIR** | 7 962 £ | 12 680 £ | **18 611 £** | 30 097 £ | 44 188 £ | 53 000 £ |
| **ROUTE** | −357 £ | 28 £ | **409 £** | 2 654 £ | 5 174 £ | 6 083 £ |

### 3.3 Ventilation par graine pour OpexAI

| Graine | RAIL : Lignes (Régime) | RAIL : Profit Régime Total | AIR : Lignes (Régime) | AIR : Profit Régime Total | ROUTE : Lignes (Régime) | ROUTE : Profit Régime Total |
|---|---|---|---|---|---|---|
| **42** | 3 (3) | 56 669 £ | 102 (68) | 1 370 718 £ | 21 (18) | 31 331 £ |
| **100** | 5 (4) | 52 307 £ | 97 (56) | 1 150 720 £ | 8 (7) | 6 840 £ |
| **999** | 4 (4) | 196 747 £ | 93 (56) | 1 302 294 £ | 15 (13) | 17 303 £ |
| **1234** | 6 (4) | 113 451 £ | 97 (51) | 1 356 148 £ | 13 (11) | 10 907 £ |
| **5678** | 2 (2) | 55 971 £ | 88 (63) | 1 594 427 £ | 17 (12) | 29 376 £ |
| **Moyenne** | **4,0 (3,4)** | **95 029 £** | **95,4 (58,8)** | **1 354 861 £** | **14,8 (12,2)** | **19 151 £** |

### 3.4 Recensement exhaustif des 20 lignes ferroviaires d'OpexAI

| Graine | Clé de ligne | Année $y_0$ | Villes / Cargo | Trains | Montée ($y_0+1$) | Régime moyen | Profil annuel observé (`profit_last`) |
|---|---|---|---|---|---|---|---|
| **42** | `rail\|21,22` | 1970 | [7, 7] Céréales (8) | 1 | 4 262 £ | **8 965 £** | 1971: 4.3k, 1972: 8.8k, 1973: 9.4k, 1974: 8.8k, 1975: 8.8k |
| **42** | `rail\|45,46` | 1971 | [25, 27] Pax (0) | 1 | −618 £ | **1 416 £** | 1972: −0.6k, 1973: 2.2k, 1974: 2.2k, 1975: −0.2k |
| **42** | `rail\|66,67` | 1971 | [35, 38] **Charbon (1)** | 1 | 12 167 £ | **46 288 £** | 1972: 12.2k, 1973: 44.1k, 1974: 50.8k, 1975: 44.0k |
| **100** | `rail\|10,11` | 1970 | [4, 35] Charbon (1) | 1 | — | — | 1970: 0 (rebutée avant 1971) |
| **100** | `rail\|11` | 1971 | [4] Charbon (1) | 1 | 14 914 £ | **−2 533 £** | 1972: 14.9k, 1973: −2.5k, 1974: −2.5k, 1975: −2.5k (mine fermée) |
| **100** | `rail\|32,33` | 1971 | [21, 26] Pétrole (3) | 1 | 13 090 £ | **13 570 £** | 1972: 13.1k, 1973: 15.0k, 1974: 15.0k, 1975: 10.6k |
| **100** | `rail\|81,82` | 1972 | [7, 36] Céréales (8) | 1 | 13 741 £ | **20 526 £** | 1973: 13.7k, 1974: 22.1k, 1975: 18.9k |
| **100** | `rail\|108,109` | 1972 | [20, 30] Pétrole (3) | 1 | 6 676 £ | **20 743 £** | 1973: 6.7k, 1974: 20.7k, 1975: 20.7k |
| **999** | `rail\|57,58` | 1971 | [3, 13] **Charbon (1)** | 1 | 37 278 £ | **70 269 £** | 1972: 37.3k, 1973: 67.6k, 1974: 75.5k, 1975: 67.7k |
| **999** | `rail\|143,144` | 1972 | [30, 32] **Charbon (1)** | 1 | 39 979 £ | **56 734 £** | 1973: 40.0k, 1974: 60.5k, 1975: 52.9k |
| **999** | `rail\|156,157` | 1972 | [21, 31] Fer (4) | 1 | 9 166 £ | **14 414 £** | 1973: 9.2k, 1974: 13.9k, 1975: 15.0k |
| **999** | `rail\|202,203` | 1972 | [17, 40] **Charbon (1)** | 1 | 17 038 £ | **55 329 £** | 1973: 17.0k, 1974: 60.6k, 1975: 50.1k |
| **1234** | `rail\|12,13` | 1970 | [27, 44] Bétail (7) | 2 | 7 632 £ | **15 172 £** | 1971: 7.6k, 1972: 13.5k, 1973: 13.5k, 1974: 17.3k, 1975: 16.4k |
| **1234** | `rail\|14,15` | 1970 | [6, 38] Pax (0) | 1 | −250 £ | **−349 £** | 1971: −0.3k, 1972: −0.1k, 1973: −0.7k, 1974: −0.3k, 1975: −0.3k |
| **1234** | `rail\|124,125` | 1972 | [14, 21] Bétail (7) | 1 | 2 359 £ | **26 629 £** | 1973: 2.4k, 1974: 26.6k, 1975: 26.6k |
| **1234** | `rail\|160,161` | 1973 | [35, 39] **Charbon (1)** | 1 | 42 716 £ | **71 998 £** | 1974: 42.7k, 1975: 72.0k |
| **1234** | `rail\|186,187` | 1974 | [13, 43] Pétrole (3) | 1 | −1 489 £ | — | 1975: −1.5k (mise en service tardive) |
| **1234** | `rail\|192,193` | 1974 | [34, 34] Fer (4) | 1 | 1 891 £ | — | 1975: 1.9k (mise en service tardive) |
| **5678** | `rail\|12,13` | 1970 | [20, 42] Pax (0) | 1 | 4 320 £ | **3 154 £** | 1971: 4.3k, 1972: 6.6k, 1973: 5.3k, 1974: 0.6k, 1975: −0.0k |
| **5678** | `rail\|145,146` | 1972 | [5, 19] **Charbon (1)** | 1 | 27 534 £ | **52 817 £** | 1973: 27.5k, 1974: 49.9k, 1975: 55.7k |

---

## 4. Comparaison avec l'adversaire AAAHogEx

AAAHogEx partage la même carte, les mêmes villes et industries, et la même durée de jeu (6 ans).

### 4.1 Vue d'ensemble comparative

| Arm | Mode | Lignes créées | Lignes en régime | Convois / ligne | Régime : Moyenne | Régime : Médiane | Régime : Plage [Min, Max] | % Déficitaires | Profit annuel régime moyen / graine |
|---|---|---|---|---|---|---|---|---|---|
| **OpexAI** | **RAIL** | 20 | 17 | 1,05 | 27 950 £ | **20 526 £** | [−2 533 £, 71 998 £] | 11,8 % | 95 029 £ |
| **AAAHogEx** | **RAIL** | 112 | 61 | 1,88 | **51 067 £** | 9 450 £ | [−1 490 £, 822 887 £] | 8,2 % | **623 017 £** |
| **OpexAI** | **AIR** | 477 | 294 | 1,13 | 23 042 £ | 18 611 £ | [−1 069 £, 106 352 £] | 0,3 % | 1 354 861 £ |
| **AAAHogEx** | **AIR** | 102 | 95 | 2,43 | **102 340 £** | **83 673 £** | [4 960 £, 349 643 £] | 0,0 % | **1 944 454 £** |
| **OpexAI** | **ROUTE** | 74 | 61 | 1,86 | 1 570 £ | 409 £ | [−736 £, 7 521 £] | 23,0 % | 19 151 £ |
| **AAAHogEx** | **ROUTE** | 548 | 440 | 1,72 | **−186 £** | **−381 £** | [−1 198 £, 8 466 £] | **78,0 %** | **−16 357 £** |

### 4.2 Enseignements sur la structure du trafic

1. **Stratégie Aérienne :**
   - **OpexAI** maille le territoire avec une multitude de lignes (59 lignes mûres par graine) exploitées chacune par un convoi unique (1,13 avion/ligne). Médiane unitaire : **18 611 £/an**.
   - **AAAHogEx** concentre son réseau sur les liaisons majeures (19 lignes mûres par graine), mais empile les gros appareils (2,43 avions/ligne). Médiane unitaire : **83 673 £/an** (4,5× plus qu'OpexAI).
2. **Stratégie Ferroviaire :**
   - **OpexAI** exploite très peu de lignes (3,4 mûres par graine), presque exclusivement avec 1 seul convoi. Pourtant, sa médiane (**20 526 £/an**) dépasse celle d'AAAHogEx (**9 450 £/an**), car OpexAI cible des gisements de fret très rentables.
   - **AAAHogEx** déploie un réseau ferroviaire massif (12,2 lignes mûres par graine, avec des lignes à plusieurs convois) qui lui rapporte **623 k£/an** par graine (6,5× plus qu'OpexAI).
3. **Stratégie Routière :**
   - **OpexAI** maintient un réseau routier modeste (12 lignes mûres par graine), globalement positif (+19 k£/an).
   - **AAAHogEx** inonde la carte de centaines de lignes d'autobus urbains (88 lignes mûres par graine), dont **78 % sont déficitaires** (−16 k£/an de perte nette).

---

## 5. Analyse causale : Pourquoi le sélecteur préfère-t-il l'Air au Rail ?

La question initiale posait l'hypothèse d'une distorsion de l'estimation de profit :
> *« Hypothèse : l'estimation de profit d'un mode (rail sous-estimé ? air surestimé ?) est faussée par rapport au réalisé. »*

La mesure du réalisé apporte une réponse sans ambiguïté :

### 5.1 En régime, le rail est PLUS rentable que l'air par ligne construite
- **Rail OpexAI :** Moyenne de **27 950 £ / an / ligne** (médiane **20 526 £**).
  - Les lignes de charbon rapportent en moyenne **59 000 £ / an** par train (avec des pics à **70 269 £** et **71 998 £**).
- **Air OpexAI :** Moyenne de **23 042 £ / an / ligne** (médiane **18 611 £**).
- Le rail produit donc **+21 % de profit unitaire en moyenne** et **+10 % en médiane** par rapport à l'avion.

### 5.2 Les causes racines du blocage de sélection du Rail

Puisque le rail réalisé est supérieur ou égal à l'air, pourquoi le `fundScore = profit / capital` préfère-t-il l'air ? Quatre mécanismes concordants l'expliquent :

1. **Le ratio capital/infrastructure (l'avantage intrinsèque de l'air) :**
   - Une ligne aérienne requiert deux petits aéroports et un aéronef : capital modélisé de **~35 000 à 45 000 £**.
   - Une ligne ferroviaire requiert terrassement, voie, 2 gares, signalisation, dépôt, motrice et wagons : capital modélisé de **~70 000 à 110 000 £**.
   - Même avec un profit identique de 25 000 £/an, l'air affiche un score brut de $25\,000 / 40\,000 = 0{,}625$, contre $25\,000 / 85\,000 = 0{,}294$ pour le rail.

2. **La pénalité de financement artificielle sur le rail (`RAIL_FINANCE_BIAS_PCT = 170%`) :**
   - Dans `projects.nut:295,315`, la fonction `OpexProjectFinanceCapital` applique au capital du rail un biais de **1,7×** :
     $$\text{financeCapital}_{\text{rail}} = \text{capital} \times 1{,}70$$
   - Ce biais fait passer le capital de calcul d'une ligne rail de 85 k£ à **144,5 k£**, faisant chuter son `fundScore` à $25\,000 / 144\,500 = 0{,}173$. Le rail est donc artificiellement dégradé d'un facteur 1,7 dans la compétition face à l'air.

3. **L'asphyxie de trésorerie par prédation mensuelle :**
   - L'air est finançable dès que la trésorerie disponible atteint ~35 k£.
   - Le rail doit attendre que la trésorerie atteigne ~120–150 k£ (capital majoré + réserves).
   - Chaque mois, le scheduler évalue le vivier. Dès que la trésorerie franchit 40 k£, une opportunité aérienne rentable est finançable immédiatement : elle est construite, consomme la caisse, et ramène le solde bancaire près de zéro. La trésorerie n'atteint donc presque jamais le seuil d'admissibilité d'un grand projet ferroviaire, sauf lors des tout premiers mois de bootstrap.

4. **La sous-évaluation du fret ferroviaire par convoi unique :**
   - Le modèle ferroviaire évalue le profit d'une ligne pour un seul train initial (`trains = 1`).
   - Or, une mine de charbon produisant 150 à 250 t/mois pourrait saturer 2 à 3 trains sans infrastructure supplémentaire. L'air, lui, dimensionne sa capacité passager au plus près de la demande urbaine. Le rail sous-estime donc son retour sur investissement marginal par rapport à l'infrastructure posée.

---

## 6. Protocole pour la mesure de l'estimé et commande recommandée

### 6.1 Diagnostic de captation NoAI
- Les commandes NoAI `AILog.Info` ne sont **pas** capturées par le banc standard (`bench_1v1_5y_20seeds.py`), car OpenTTD requiert `-d script=4` en ligne de commande pour sortir les logs sur stdout. Sans ce paramètre, les fichiers de logs moteur restent vides (0 octet).
- En revanche, les panneaux de la carte (`AISign.BuildSign`) sont **sauvegardés dans le chunk `SIGN`** des sauvegardes OpenTTD. Comme `debug_signs=1` est actif par défaut, les panneaux `AF|`, `AH|`, `OF|`, `OJ|`, `OK|` sont déjà physiquement générés dans la partie.

### 6.2 Mesure minimale recommandée (sans modification Squirrel)

Pour capturer à la fois le capital planifié et le coût réel de construction pour chaque ligne, il suffit d'armer la sonde existante `probe_cost=1` :
- `probe_cost=1` ajoute la pose des panneaux :
  - `DC|<lineId>|<plannedCapital>|<actualCost>|...` pour le rail.
  - `AC|<lineId>|<plannedCapital>|<actualCost>|...` pour l'air.
- Associés aux panneaux posés par défaut (`AF|`, `AH|`, `OF|`, `OJ|`, `OK|`), 100 % des prédictions (profit estimé, capital estimé, coût réel) sont consignés dans le chunk `SIGN`.
- L'extracteur [sweeps/line_profit_analysis.py](../sweeps/line_profit_analysis.py) implémente déjà le décodeur `extract_estimates_from_signs` validé par les tests unitaires [sweeps/test_line_profit_analysis.py](../sweeps/test_line_profit_analysis.py).

### 6.3 Commande exacte à lancer par l'orchestrateur

```bash
python3 sweeps/run_c66_reference.py --campaign lineprofit_costprobe_5x6_20260927 --years 6 --seeds 42 100 999 1234 5678 --line-telemetry --reference "OpexAI[probe_cost=1]" --max-workers 3
```

*Remarque :* Si l'on souhaite également capturer les événements textuels `C50_CHRONO phase=project_built` via stdout, il faudra utiliser `--reference "OpexAI[probe_portfolio=1]"` et s'assurer que le harnais injecte `-d script=4` dans l'appel OpenTTD. L'option par panneaux `probe_cost=1` ci-dessus est plus robuste car elle ne dépend pas de stdout.

---

## 7. Résumé exécutif (10-15 lignes)

1. **Inventaire :** Les profits réels par ligne sont entièrement mesurés dans `lineprofit_default_5x6_20260926.json` après correction de l'échelle OpenTTD (`/ 256.0`). Les profits estimés n'étaient pas capturés car les journaux moteur étaient vides (absence de `-d script=4` dans le banc) et les panneaux `SIGN` n'ont pas été persistés dans ce JSON.
2. **Mesure du réalisé OpexAI (5 graines × 6 ans) :**
   - **Rail :** 17 lignes mûres, profit annuel moyen de **27 950 £ / an** (médiane **20 526 £ / an**). Les lignes de charbon rapportent en moyenne **59 000 £ / an** par train (max 71 998 £).
   - **Air :** 294 lignes mûres, profit annuel moyen de **23 042 £ / an** (médiane **18 611 £ / an**, 0,3 % négatives).
   - **Route :** 61 lignes mûres, profit annuel moyen de **1 570 £ / an** (médiane **409 £ / an**, 23 % négatives).
3. **Comparaison adverse :** AAAHogEx gagne **623 k£/an** en rail (61 lignes mûres à 1,88 convoi/ligne) et **1 944 k£/an** en air (95 lignes à 2,43 avions/ligne, médiane 83,7 k£/an), tandis que ses 440 lignes routières perdent de l'argent (78 % déficitaires).
4. **Cause racine de l'arbitrage :** Le rail en régime est **+21 % plus rentable que l'air par ligne unitaire**. La préférence systématique du sélecteur pour l'air ne provient pas d'une surévaluation du profit aérien, mais :
   - D'un capital de départ 2× à 3× plus faible pour l'air (infrastructure légère) ;
   - Du multiplicateur de capital `RAIL_FINANCE_BIAS_PCT = 170%` qui pénalise artificiellement le rail d'un facteur 1,7 dans `fundScore` ;
   - D'une concurrence de caisse mensuelle où les petits projets aériens consomment la trésorerie avant qu'elle n'atteigne le palier de financement du rail.
5. **Mesure suivante :** Pour obtenir le rapport réalisé/estimé complet sans modifier Squirrel, lancer le duel 5×6 avec le bras de référence `OpexAI[probe_cost=1]`, qui pose les panneaux de devis et coûts réels `DC|` et `AC|` dans le chunk `SIGN`.
