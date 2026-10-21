# Autopsie des abandons A* rail (ABND) : OpexAI face à AAAHogEx

> **Date :** 21 octobre 2026  
> **Branche :** `railech` (dépôt `/home/deploy/projects/wt-railech`, dérivé de `master`)  
> **Données de banc analysées :** `/home/deploy/projects/wt-v299/results/v299_diag_3x10_20261021_engine/` (10 ans, graines 42, 7, 100, 2 bras : `reference_*` = master, `v299_*` = `v294_rail_weight_adapt=400`)  
> **Script de diagnostic :** [`sweeps/diag_railech_abnd.py`](file:///home/deploy/projects/wt-railech/sweeps/diag_railech_abnd.py)  
> **Adversaire analysé :** AAAHogEx-115 ([`ai/AAAHogEx-115/`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/))

---

## 1. Analyse comparative sur les journaux v299 (10 ans, 3 graines, 2 bras)

### 1.1 OpexAI : Tentatives `RAIL_ATTEMPT` par motif × tranche de distance Manhattan × bras

Dans le journal OpexAI (`[script:4] [0]`), chaque tentative de construction d'une ligne ferroviaire émet une ligne structurée `RAIL_ATTEMPT` ([`ai/OpexAI/task_rail.nut:1123-1140`](file:///home/deploy/projects/wt-railech/ai/OpexAI/task_rail.nut#L1123-L1140)).
Les motifs d'échec sont définis dans [`ai/OpexAI/builder_rail.nut`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut) :
- `OK` : tracé trouvé et ligne posée avec succès ([`builder_rail.nut:3238, 3878`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L3238)).
- `ABND` : abandon de l'A* car le plafond dur d'itérations est atteint (`spent >= iterationBudget`, soit `HARD_ITERATION_CAP = 5000`, [`builder_rail.nut:894`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L894), [`globals_pre.nut:602`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L602)).
- `NOPA` : file ouverte de l'A* vidée sans avoir pu atteindre la destination ([`builder_rail.nut:897`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L897)).
- `SITE*` (`SITEAB`, `SITEB`, `SITEA`) : impossibilité de placer un quai ou de raccorder la gorge à l'une ou aux deux extrémités ([`builder_rail.nut:711, 794, 815`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L711)).
- `TRKFAIL` : échec physique de pose des rails après validation du tracé ([`builder_rail.nut:3167, 3772`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L3167)).
- `STNFAIL` : échec de pose de la station dans le monde ([`builder_rail.nut:3702, 4260`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L3702)).
- `NOTRAIN` : budget ou disponibilité de matériel insuffisant au dépôt ([`builder_rail.nut:3659, 3873`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L3659)).

#### Bras Master (`reference_*` : poids $w=120\%$ sous 100 tuiles, $w=200\%$ au-delà)

| Motif | < 60 tuiles | 60 – 100 tuiles | 100 – 160 tuiles | $\ge 160$ tuiles | Total | % du Total |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **OK** | 9 | 14 | 32 | 6 | **61** | 44,5 % |
| **ABND** | 1 | **21** | 8 | 15 | **45** | **32,8 %** |
| **SITEAB** | 0 | 6 | 4 | 11 | **21** | 15,3 % |
| **SITEB** | 0 | 1 | 1 | 1 | **3** | 2,2 % |
| **TRKFAIL** | 1 | 2 | 1 | 0 | **4** | 2,9 % |
| **NOTRAIN** | 0 | 0 | 1 | 0 | **1** | 0,7 % |
| **STNFAIL** | 0 | 1 | 0 | 0 | **1** | 0,7 % |
| **NOPA** | 0 | 0 | 0 | 1 | **1** | 0,7 % |
| **TOTAL** | **11** | **45** | **47** | **34** | **137** | 100,0 % |

#### Bras V299 (`v299_*` : `v294_rail_weight_adapt=400`)

| Motif | < 60 tuiles | 60 – 100 tuiles | 100 – 160 tuiles | $\ge 160$ tuiles | Total | % du Total |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **OK** | 9 | **26** | 33 | 6 | **74** | 61,2 % |
| **ABND** | 2 | **0** | 3 | 4 | **9** | **7,4 %** |
| **SITEAB** | 0 | 11 | 3 | 3 | **17** | 14,0 % |
| **NOTRAIN** | 0 | 0 | 6 | 4 | **10** | 8,3 % |
| **TRKFAIL** | 0 | 0 | 6 | 0 | **6** | 5,0 % |
| **STNFAIL** | 0 | 0 | 2 | 2 | **4** | 3,3 % |
| **NOPA** | 0 | 0 | 0 | 1 | **1** | 0,8 % |
| **TOTAL** | **11** | **37** | **53** | **20** | **121** | 100,0 % |

> [!IMPORTANT]
> **Basculement spectaculaire sur la tranche 60–100 tuiles :**
> - Dans **master**, les abandons A* (`ABND`) représentent **46,7 % des tentatives de 60 à 100 tuiles** (21 ABND sur 45 tentatives, pour seulement 14 réussites).
> - Dans **v299** (`adapt=400`), les abandons tombent à **0 sur 37 tentatives**, et les réussites bondissent de 14 à 26 (+85,7 %).
> - Au global, les abandons A* sont divisés par **5** (45 $\to$ 9).

---

### 1.2 OpexAI : Itérations et opcodes médians par motif

| Bras | Motif | Nombre ($n$) | Itérations Médiane | Itérations Moyenne | Opcodes Médiane | Opcodes Moyenne |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Master** | **OK** | 61 | **1 287** | 1 542 | **3,25 M** | 4,11 M |
| | **ABND** | 45 | **5 000** | 5 000 | **6,88 M** | 7,26 M |
| | **SITEAB** | 21 | 0 | 0 | 0,00 M | 0,00 M |
| | **TRKFAIL** | 4 | 3 034 | 2 881 | 5,36 M | 5,47 M |
| | **SITEB** | 3 | 0 | 0 | 21,89 M | 19,61 M |
| | **NOTRAIN** | 1 | 3 167 | 3 167 | 10,59 M | 10,59 M |
| | **STNFAIL** | 1 | 4 308 | 4 308 | 6,19 M | 6,19 M |
| | **NOPA** | 1 | 201 | 201 | 0,17 M | 0,17 M |
| **V299** | **OK** | 74 | **156** | 325 | **1,43 M** | 1,87 M |
| | **ABND** | 9 | **5 000** | 4 696 | **6,80 M** | 6,43 M |
| | **SITEAB** | 17 | 0 | 0 | 0,00 M | 0,00 M |
| | **NOTRAIN** | 10 | 308 | 794 | 2,56 M | 5,52 M |
| | **TRKFAIL** | 6 | 373 | 389 | 4,28 M | 4,21 M |
| | **STNFAIL** | 4 | 1 504 | 1 666 | 4,20 M | 3,60 M |
| | **NOPA** | 1 | 2 716 | 2 716 | 3,87 M | 3,87 M |

> [!TIP]
> **Coût d'un échec ABND :** Chaque `ABND` consomme invariablement **5 000 itérations** et **6,88 M d'opcodes** (environ 700 ticks de calcul Squirrel pur). Dans master, les 45 ABND ont gaspillé **309,6 M d'opcodes** pour un gain économique strictement nul.
> Dans V299, les réussites `OK` aboutissent en une médiane de **156 itérations** (contre 1 287, division par 8,2) et **1,43 M opcodes** (contre 3,25 M).

---

### 1.3 AAAHogEx : Taux de succès et nature réelle des échecs

Dans les journaux d'AAAHogEx (`[script:4] [1]`), les tentatives de voies ferrées sont tracées par le module `RouteBuilder` (`TrainRouteBuilder`, [`route.nut:3534-3543`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/route.nut#L3534-L3543), [`trainroute.nut:2850-3159`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L2850-L3159)).
L'analyse systématique des 67 échecs ferroviaires d'AAAHogEx sur les 6 parties révèle les étiquettes réelles suivantes :
1. **Échecs précoces de gare (`Station NG / AddNgPlace`)** : 39 cas (58,2 % des échecs). AAA n'arrive pas à placer une gare respectant ses critères d'acceptation ou de longueur (`candidates:0/...`, `TrainRoute: No destStation` / `No srcStation`, [`trainroute.nut:3000-3021`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3000-L3021)). Il enregistre immédiatement le lieu en liste noire (`Place.AddNgPlace`) et **abandonne en 1 à 10 jours sans faire tourner l'A\***.
2. **Échecs A* (`A* No path found`)** : 20 cas (29,9 % des échecs, soit seulement **4,3 % de ses 470 tentatives**). L'A* d'AAA tente jusqu'à 240 tranches de 50 itérations (`counter:240`, soit 12 000 itérations) avant de conclure `RailPathBuilder: No path found` ([`railbuilder.nut:2376`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2376)). Ces échecs durent 125 à 329 jours de jeu.
3. **Échecs d'exécution de quai (`srcStation/destStation.BuildExec failed`)** : 5 cas (7,5 % des échecs). Échec de terraformation ou d'éviction locale lors de la pose effective de la gare ([`trainroute.nut:3028, 3039`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3028)). Durée : 3 à 5 jours.
4. **Dépôt manquant (`srcDepot == null`)** : 2 cas (3,0 % des échecs). Impossibilité de trouver un embranchement pour le dépôt ([`trainroute.nut:3095`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3095)).
5. **Autre** : 1 cas (1,5 %).

#### Répartition d'AAAHogEx par tranche de distance

| Statut / Motif AAA | < 60 tuiles | 60 – 100 tuiles | 100 – 160 tuiles | $\ge 160$ tuiles | Total | Jours Méd. [Min - Max] |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Succeeded (Succès)** | **52** | **38** | **34** | **41** | **165** (71,1 %) | 41 j [7 – 248] |
| **Station NG (`AddNgPlace`)** | 18 | 12 | 4 | 5 | **39** (16,8 %) | **4 j** [1 – 12] |
| **A* `No path found`** | 4 | 5 | 4 | 6 | **19** (8,2 %) | **188 j** [36 – 329] |
| **`srcStation.BuildExec`** | 2 | 2 | 0 | 0 | **4** (1,7 %) | **4 j** [3 – 5] |
| **`srcDepot == null`** | 2 | 0 | 0 | 0 | **2** (0,9 %) | 68 j [7 – 129] |
| **`destStation.BuildExec`**| 0 | 0 | 0 | 1 | **1** (0,4 %) | 20 j [20 – 20] |
| **Autre échec** | 0 | 1 | 1 | 0 | **2** (0,9 %) | 126 j [68 – 185] |
| **TOTAL AAA** | **78** | **58** | **43** | **53** | **232** (100 %) | — |

#### Efficacité de l'A* d'AAA (`TrainRoute: Path found`)

Dans ses réussites, le nombre d'appels de 50 itérations (`_FindPath(50)`, [`pathfinder.nut:209`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L209)) et le nombre de jours nécessaires sont remarquablement stables :
- **< 60 tuiles** : médiane **1 appel (~50 itérations)**, résolu en **1 jour** de jeu ($n=99$).
- **60 – 100 tuiles** : médiane **4 appels (~200 itérations)**, résolu en **2 à 3 jours** de jeu ($n=67$).
- **100 – 160 tuiles** : médiane **6 appels (~300 itérations)**, résolu en **4 jours** de jeu ($n=68$).
- **$\ge 160$ tuiles** : médiane **9 appels (~450 itérations)**, résolu en **6,5 à 7 jours** de jeu ($n=78$).

---

## 2. Autopsie détaillée des 24 abandons à < 100 tuiles

### 2.1 Relevé exhaustif des 22 abandons de Master (`reference_*`)

Les 22 abandons courts de master ont tous eu lieu à `weight=120`, à `iters=5000` et ont consommé entre 5,8 M et 9,8 M d'opcodes chacun.  
Sur une carte de $256 \times 256$, la coordonnée tuile est $(x = \text{tile} \pmod{256}, y = \lfloor \text{tile} / 256 \rfloor)$.

| N° | Graine | Date | Manh | Src | Coord Src | Dst | Coord Dst | Type | Cargo | Profit Prédit | ROI | Opcodes | Particularité réseau |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | 100 | 1972-12-18 | 75 | 15063 | (215, 58) | 31179 | (203, 121) | fret | COAL | 30 578 £ | 698 | 6,4 M | Relief collinaire |
| 2 | 100 | 1974-07-01 | 90 | 26718 | (94, 104) | 22803 | (19, 89) | fret | IORE | 30 952 £ | 681 | 7,4 M | Traversée est-ouest |
| 3 | 100 | 1974-08-23 | 85 | 26718 | (94, 104) | 23828 | (20, 93) | fret | IORE | 28 456 £ | 634 | 7,3 M | Cible proche de la précédente |
| 4 | 100 | 1976-08-21 | 76 | 18741 | (53, 73) | 9822 | (94, 38) | pax | PASS | 4 599 £ | 99 | 6,6 M | Ville enclavée (essai 1) |
| 5 | 100 | 1978-08-12 | 76 | 18741 | (53, 73) | 9822 | (94, 38) | pax | PASS | 8 568 £ | 177 | 6,2 M | Re-tentative identique (essai 2) |
| 6 | 100 | 1978-10-24 | 40 | 24247 | (183, 94) | 21717 | (213, 84) | pax | PASS | 927 £ | 21 | 5,9 M | Gorge urbaine dense |
| 7 | 100 | 1979-09-15 | 73 | 36777 | (169, 143) | 29140 | (212, 113) | fret | WOOD | 45 076 £ | 1237 | 8,4 M | Faisceau de voies existant |
| 8 | 42 | 1972-03-17 | 96 | 9815 | (87, 38) | 26996 | (116, 105) | fret | COAL | 69 361 £ | 1442 | 7,1 M | Dest partagée (`shared_dest=1`) |
| 9 | 42 | 1972-09-17 | 98 | 4968 | (104, 19) | 26996 | (116, 105) | fret | COAL | 33 810 £ | 731 | 7,3 M | Même centrale électrique |
| 10 | 42 | 1974-07-22 | 91 | 40752 | (48, 159) | 56143 | (79, 219) | fret | GRAI | 22 453 £ | 504 | 9,8 M | Corridor sud |
| 11 | 42 | 1977-07-19 | 96 | 9815 | (87, 38) | 26996 | (116, 105) | fret | COAL | 80 650 £ | 1528 | 6,4 M | Re-tentative sur 26996 |
| 12 | 42 | 1977-09-25 | 91 | 40752 | (48, 159) | 56143 | (79, 219) | fret | GRAI | 37 032 £ | 737 | 7,5 M | Re-tentative sur 56143 |
| 13 | 42 | 1979-06-26 | 83 | 9815 | (87, 38) | 13978 | (154, 54) | fret | COAL | 68 601 £ | 1683 | 7,7 M | Mine 9815 vers centrale 13978 |
| 14 | 42 | 1979-08-30 | 98 | 4968 | (104, 19) | 26996 | (116, 105) | fret | COAL | 26 072 £ | 682 | 6,7 M | Re-tentative sur 26996 |
| 15 | 42 | 1979-11-02 | 60 | 33442 | (162, 130) | 34012 | (220, 132) | pax | PASS | 2 462 £ | 75 | 6,9 M | Ligne pax transversale |
| 16 | 7 | 1972-08-16 | 91 | 18076 | (156, 70) | 30662 | (198, 119) | fret | COAL | 40 470 £ | 890 | 7,0 M | Colline intermédiaire |
| 17 | 7 | 1972-12-10 | 91 | 42993 | (241, 167) | 30662 | (198, 119) | fret | COAL | 27 255 £ | 613 | 6,4 M | Même centrale 30662 |
| 18 | 7 | 1974-02-13 | 91 | 59671 | (23, 233) | 37146 | (26, 145) | fret | WOOD | 32 296 £ | 709 | 8,0 M | Ligne nord-sud en bordure |
| 19 | 7 | 1976-07-30 | 74 | 19603 | (147, 76) | 7289 | (121, 28) | fret | COAL | 16 548 £ | 344 | 6,2 M | Traversée réseau AAA |
| 20 | 7 | 1979-08-03 | 78 | 11500 | (236, 44) | 26585 | (217, 103) | pax | PASS | 9 014 £ | 245 | 6,9 M | Liaison interurbaine |
| 21 | 7 | 1979-10-15 | 65 | 56752 | (176, 221) | 53372 | (124, 208) | pax | PASS | 5 654 £ | 169 | 6,8 M | Corridor urbain sud |
| 22 | 7 | 1979-12-20 | 73 | 46669 | (77, 182) | 53372 | (124, 208) | pax | PASS | 4 934 £ | 144 | 5,8 M | Même ville terminus 53372 |

### 2.2 Relevé des 2 seuls abandons de V299 (`adapt=400`)

Dans V299, les 2 seuls abandons sous 100 tuiles sont survenus à des distances très courtes (< 40 tuiles) sur des liaisons de passagers secondaires :
1. **Graine 7 (1974-05-13)** : `src=53372 (124, 208) -> dst=48525 (141, 189)`, `manh=36`, pax, profit prédit 606 £, ROI 16, `adapt=100/100/2`, ops 6,0 M.
2. **Graine 7 (1979-06-17)** : `src=23268 (228, 90) -> dst=19926 (214, 77)`, `manh=27`, pax, profit prédit 302 £, ROI 10, `adapt=100/100/2`, ops 3,0 M.

Ces deux cas révèlent le mécanisme de repli adaptatif : sur ces deux lignes très courtes et enclavées dans le tissu urbain, le poids 400 a échoué rapidement, le repli est descendu à 100 (`adapt=100/100/2`), et à poids 100 dans un tissu urbain dense sans possibilité de démolir, l'A* a saturé son plafond de 5 000 itérations.

### 2.3 Le verdict causal : le devenir dans V299 des paires ayant échoué dans Master

Parmi les 17 paires uniques de master ayant échoué par `ABND` à < 100 tuiles, 7 ont été soumises à la construction dans V299.  
**Résultat : 7 sur 7 ont réussi (`ok=1 reason=OK`), avec une médiane de 131 itérations seulement !**

- **Graine 100 `(26718, 23828)` manh=85** : était `ABND` (5 000 iters, 7,3 M ops) $\to$ **OK en 272 itérations** (1,40 M ops, `adapt=400/400/0`).
- **Graine 100 `(36777, 29140)` manh=73** : était `ABND` (5 000 iters, 8,4 M ops) $\to$ **OK en 75 itérations** (0,98 M ops, `adapt=400/400/0`).
- **Graine 42 `(9815, 26996)` manh=96** : était `ABND` (5 000 iters, 7,1 M ops) $\to$ **OK en 116 itérations** (1,12 M ops, `adapt=400/400/0`).
- **Graine 7 `(42993, 30662)` manh=91** : était `ABND` (5 000 iters, 6,4 M ops) $\to$ **OK en 438 itérations** (1,53 M ops, `adapt=400/400/0`).
- **Graine 7 `(59671, 37146)` manh=91** : était `ABND` (5 000 iters, 8,0 M ops) $\to$ **OK en 76 itérations** (1,01 M ops, `adapt=400/400/0`).
- **Graine 7 `(19603, 7289)` manh=74** : était `ABND` (5 000 iters, 6,2 M ops) $\to$ **OK en 131 itérations** (1,02 M ops, `adapt=400/400/0`).
- **Graine 7 `(11500, 26585)` manh=78** : était `ABND` (5 000 iters, 6,9 M ops) $\to$ **OK en 794 itérations** (2,06 M ops, `adapt=400/400/0`).

> [!CAUTION]
> **Preuve définitive :** Ce test causal prouve mathématiquement que les 22 paires qui abandonnaient dans master n'étaient **pas** topologiquement insolubles ni bloquées par un obstacle infranchissable. Elles étaient de parfaits tracés réalisables en 75 à 438 pas, mais l'A* de master s'égarait dans une exploration 2D diffuse à cause d'un poids d'heuristique trop faible ($w=120\%$).

---

### 2.4 Tableau comparatif des contraintes d'A* : OpexAI vs AAAHogEx

Chaque fichier et numéro de ligne a été formellement vérifié dans le code source courant :

| Contrainte / Paramètre | OpexAI ([`ai/OpexAI/`](file:///home/deploy/projects/wt-railech/ai/OpexAI/)) | AAAHogEx ([`ai/AAAHogEx-115/`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/)) | Effet sur l'abandon de l'A* |
|---|---|---|---|
| **Poids de l'heuristique ($w$)** | **$w = 120\%$** si distance $< 100$ tuiles ([`globals_pre.nut:664`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L664), [`builder_rail.nut:833`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L833)).<br>**$w = 200\%$** si distance $\ge 100$ ([`globals_pre.nut:92`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L92), [`builder_rail.nut:830`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L830)). | **$w = 200\%$ universel**, pour TOUTES les distances y compris $< 100$ ([`pathfinder.nut:86, 133, 820`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L86) `_estimate_rate = 2;`). | **Cause n°1 des ABND courts** : à $w=1,2$, le coût réel $g$ dépasse $h$ dès le moindre détour, transformant l'A* en Dijkstra circulaire. |
| **Plafond d'itérations** | Plafond dur **5 000 itérations** ([`globals_pre.nut:602`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L602), [`builder_rail.nut:894`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L894)). | **12 000 itérations** (`pathFindLimit * 3 * 50 = 240 * 50`, [`main.nut:242`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/main.nut#L242), [`trainroute.nut:3063`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3063)). | Opex coupe à 5 000 alors qu'AAA accorde jusqu'à 12 000 itérations en tâche de fond. |
| **Continuité de l'exploration** | **Segmenté** ([`builder_rail.nut:1162`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L1162)) : à chaque tranche de **2 000 itérations** ([`builder_rail.nut:62`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L62)), destruction du pathfinder et **perte totale du closed set** ([`builder_rail.nut:1160`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L1160)). | **Recherche continue unique** dans `AyStar` ([`aystar.nut:115-125`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L115-L125)). Queue C++ native, **closed set préservé** jusqu'au bout. | **Majeur** : à 2 000 itérations, Opex jette sa mémoire et ré-explore les mêmes tuiles en boucle lors du segment 2. |
| **Coût unitaire tuile** | Droite: **100**, Diagonale: **70** ([`pathfinder_v90/rail.nut:64-65`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L64-L65), [`v129.nut:495-498`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L495-L498)). | Droite: **100**, Diagonale: **67** ([`pathfinder.nut:126, 134, 657-659`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L126)). | Quasi-identique. |
| **Coût virage standard** | Sortie diagonale: **+300** sous V214 ([`globals_pre.nut:69`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L69), [`v129.nut:505-507`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L505-L507)). | Sortie diagonale: **+300** ([`pathfinder.nut:135, 665`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L135)). | Identique. |
| **Coude serré (90° consécutif)** | **+1 500** (+100 si dist $< 40$) sous V214 ([`globals_pre.nut:70`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L70), [`v129.nut:510-519`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L510-L519)). | **+1 500** (+100 si dist $< 40$) ([`pathfinder.nut:136, 525-532`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L136)). | Identique. |
| **Virage 180° (U-turn)** | Interdit ([`v129.nut:622`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L622)). | Interdit ([`pathfinder.nut:1098-1102`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1098-L1102)). | Identique. |
| **Coût des pentes** | **100** sur chaque tuile de pente ([`pathfinder_v90/rail.nut:67`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L67), [`v129.nut:528`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L528)). | **100** ([`pathfinder.nut:147`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L147)) ou **1 500** si machine trop faible ([`:177`]). Évalué sur le dénivelé net `abs(h2 - h1) >= _max_slope` ([`:675-693`]). | Opex taxe toute pente individuelle ; AAA taxe le dénivelé soutenu ou adapte à la motrice. |
| **Coût pont par tuile** | **100 + 150 = 250 / tuile** ([`pathfinder_v90/rail.nut:68`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L68), [`v129.nut:485`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L485)). | **100 + 100 = 200 / tuile** ([`pathfinder.nut:138, 597`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L138)) ; surcoût progressif si $>7$ et $>11$ ([`:598-603`]). | Pont plus lourdement taxé chez Opex (+25 %). |
| **Longueur max pont** | **5 tuiles** (`_max_bridge_length = 6`, boucle `i < 6`, [`rail.nut:71, 572`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L71), [`v129.nut:642`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L642)). | **30 tuiles** ([`pathfinder.nut:140`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L140) `_max_bridge_length = 30;`). | **Majeur** : tout lac ou obstacle $> 5$ tuiles force un contournement massif chez Opex. |
| **Pont sur terrain plat** | **Interdit** : `if (slope == SLOPE_FLAT && IsBuildable(next)) return [];` ([`rail.nut:569`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L569), [`v129.nut:638`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L638)). | Autorisé dès qu'un obstacle sous-jacent l'exige ([`pathfinder.nut:1381-1393`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1381-L1393)). | Opex ne peut pas sauter par-dessus un terrain plat constructible pour anticiper un obstacle. |
| **Coût tunnel par tuile** | **100 + 120 = 220 / tuile** ([`pathfinder_v90/rail.nut:69`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L69), [`v129.nut:483`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L483)). | **0 / tuile** ([`pathfinder.nut:139, 589`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L139)) ; surcoût progressif si $>7$ et $>11$ ([`:590-595`]). | **Majeur** : AAA rend le creusement de colline gratuit pour éviter de monter en surface. |
| **Longueur max tunnel** | **5 tuiles** (`_max_tunnel_length = 6`, rejet si $\ge 6$, [`rail.nut:72, 585`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L72), [`v129.nut:659`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L659)). | **11 tuiles** (14 si riche, [`pathfinder.nut:141, 184`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L141)). | Les collines de largeur $> 5$ tuiles sont infranchissables en tunnel chez Opex. |
| **Démolition dans l'A\*** | **Strictement aucune** ([`pathfinder_v90/rail.nut:271`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L271) `IsBuildable(tile)` obligatoire). | Démolition de ses propres voies mortes (`CanDemolishRail`, [`pathfinder.nut:1164`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1164)) et remblai d'eau peu profonde (`_RaiseAtWater`, [`:1181`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1181)). | Opex est totalement bloqué par tout aménagement existant. |
| **Traversée de rails existants** | **Interdite** : `if (_HasRail(cur_node)) return [];` ([`pathfinder_v90/v129.nut:589`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L589)). Franchissement aérien limité à un pont de 5 tuiles max. | **Autorisée en pont** (`_CanChangeBridge`, `_cost_under_bridge = 50`, [`pathfinder.nut:129, 823-855`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L129)). Peut convertir sa propre voie en pont pour passer dessous. | Un faisceau de voies ou une gare existante devient une barrière impénétrable pour Opex. |
| **Plafond `max_cost`** | **`PATHFINDER_MAX_COST = 200 000`** ([`builder_rail.nut:31, 856`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L31), [`v129.nut:649`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L649)). | **`_max_cost = 10 000 000`** ([`pathfinder.nut:68`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L68), [`aystar.nut:122`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L122)). | Marge 50× supérieure chez AAA (évite les abandons prématurés en relief accidenté). |
| **Plans de gare au départ** | Jusqu'à **12 plans A $\times$ 12 plans B = 144 paires** ([`builder_rail.nut:23, 840-845, 1166`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L23)). | Gare **posée et fixée avant l'A\*** ([`trainroute.nut:3027`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3027)) ; 1 à 2 voies de sortie ([`railbuilder.nut:2299-2300`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2299)). | **Majeur** : Opex dilue son front d'onde dès la tuile 0 en explorant 12 sorties à la fois. |

---

## 3. Hypothèses classées sur la cause des abandons courts (`ABND`)

### Hypothèse 1 (Rang 1 — Certaine, prouvée) : Le poids insuffisant ($w = 120\%$) sous 100 tuiles provoque une diffusion circulaire en 2D dès le premier obstacle

- **Mécanisme :** Dans l'algorithme A*, le score évalué est $f = g + w \cdot h$.  
  À $w = 1,2$ (défaut de master pour distance $< 100$), chaque pas direct vers le but diminue $h$ de 100 (gain de $-120$ sur $f$), mais coûte 100 de déplacement direct ($+100$ sur $g$), soit un gain net minuscule de seuil $-20$ par tuile.  
  Dès que le tracé doit négocier un contournement (deux virages à $+300 = +600$ sous V214, ou un coude serré à $+1 500$, ou une pente à $+100$), $g$ prend une avance massive sur $h$.  
  L'algorithme conclut alors que rebrousser chemin et explorer l'espace libre dans toutes les directions orthogonales et opposées coûte moins cher que de continuer à contourner l'obstacle. Le front d'onde s'élargit en nappe 2D circulaire (Dijkstra) et sature le plafond de 5 000 itérations avant d'avoir contourné la colline ou la ville.  
  À $w = 200\%$ (AAA) ou $w = 400\%$ (V294c), le poids de guidage vers la cible écrase les pénalités locales de virage et force l'A* à avancer droit au but comme un rayon laser.
- **Preuve irréfutable :** Le diagnostic v299 avec `adapt=400` fait chuter les abandons courts de **21 à 0** sur la tranche 60–100 tuiles. De plus, les **7 paires ré-échantillonnées qui avaient échoué par ABND dans master ont toutes réussi du premier coup** sous V299 en une médiane de **131 itérations seulement**.

---

### Hypothèse 2 (Rang 2 — Majeure) : La destruction du closed set tous les 2 000 itérations dans la recherche segmentée interdit la reprise efficace

- **Mécanisme :** Dans [`ai/OpexAI/builder_rail.nut:1160`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L1160), la recherche segmentée est conçue pour libérer la mémoire : tous les 2 000 pas (`SEGMENTED_SEGMENT_ITERS = 2000`), le pathfinder est entièrement détruit, son closed set est jeté à la poubelle, et une nouvelle recherche est instanciée depuis les 3 meilleures tuiles de la frontière.  
  Le nouveau pathfinder n'ayant aucune mémoire des tuiles déjà fermées, il recommence immédiatement à ré-explorer les impasses et les zones déjà visitées au segment précédent. Dès que le tracé rencontre une difficulté topologique demandant plus de 2 000 itérations pour être contournée, le segment 2 tourne en rond dans l'espace du segment 1 et atteint le plafond dur de 5 000 itérations (`HARD_ITERATION_CAP = 5000`) au segment 3.
- **Test / Preuve pour trancher :** Comparer sous le même poids $w=120\%$ une recherche continue unique (`v294_rail_continuous=1`) contre la recherche segmentée : mesurer le taux d'ABND et le taux de revisite des tuiles fermées.

---

### Hypothèse 3 (Rang 3 — Structurelle) : Rigidité topologique extrême (ponts/tunnels max 5 tuiles, ponts plats interdits)

- **Mécanisme :** Dans master, un pont ou un tunnel ne peut dépasser **5 tuiles** ([`pathfinder_v90/rail.nut:71-72`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L71-L72)). De surcroît, [`v129.nut:638`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L638) interdit formellement de jeter un pont depuis une tuile plate si la tuile suivante est constructible.  
  Si un lac, une dépression ou un faisceau ferroviaire traverse la ligne directe et fait plus de 5 tuiles de large, OpexAI est **incapable de le ponter**. Il est obligé d'engager un contournement de dizaines de tuiles. À $w=120\%$, ce contournement dégénère immédiatement en ABND (Hypothèse 1). AAAHogEx, lui, jette un pont de 15 à 30 tuiles en ligne droite ([`pathfinder.nut:140`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L140)) et franchit l'obstacle en 1 appel de 50 itérations.
- **Test / Preuve pour trancher :** Vérifier sur les 2 seuls ABND résiduels de V299 (graines 7, manh=36 et manh=27) si le relief ou des rails existants bloquaient la trajectoire directe sans possibilité de pont long.

---

### Hypothèse 4 (Rang 4 — Aggravante) : Dilution du front d'onde par le multi-station planning (144 combinaisons simultanées)

- **Mécanisme :** Dans [`builder_rail.nut:840-845`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L840-L845), OpexAI injecte jusqu'à 12 positions de quai A et 12 positions de quai B dans la même recherche (`MAX_STATION_PLANS = 12`).  
  Au lieu de partir d'un vecteur unique, la file de priorité $Open$ démarre avec 12 sources et cherche 12 cibles. Les premiers centaines de pas d'A* ne progressent pas vers l'arrivée, ils explorent en éventail les 12 variantes de sortie de gare dans le tissu urbain de la ville de départ. Dans les villes denses (ex: ligne 6, manh=40, profit 927 £), cet éventail consomme l'essentiel du budget avant même d'avoir quitté l'agglomération.
- **Test / Preuve pour trancher :** Comme AAA ([`trainroute.nut:3027`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3027)), pré-sélectionner le meilleur quai avant la recherche, et lancer l'A* avec 1 seul départ et 1 seule arrivée. Mesurer la réduction des itérations à l'origine.

---

### Hypothèse 5 (Rang 5 — Manque à gagner) : Absence de filtrage rapide préalable par rapport à AAA

- **Mécanisme :** Quand un terminus est trop encombré pour accueillir une ligne, AAAHogEx s'en aperçoit lors de la phase préliminaire de géométrie de gare (`GetBestHgStationCosts`, `TrainRoute: No destStation`) et **coupe court en 1 à 4 jours** avec `AddNgPlace` sans jamais invoquer l'A*.  
  OpexAI, faute de garde géométrique stricte préalable, confie le problème à l'A*, qui tente désespérément pendant 5 000 itérations et 50 jours de se frayer un chemin impossible, bloquant le créneau de construction ferroviaire de l'IA.
- **Test / Preuve pour trancher :** Implémenter le ticket V294g (mémoire d'échec par lieu et expiration par motif) pour court-circuiter l'A* sur les gares saturées.

---

## 4. Synthèse et plan d'action recommandé

1. **Adopter un poids d'heuristique unifié élevé ($w \ge 200\%$) pour toutes les distances :**  
   Le seuil historique $w=120\%$ pour distance $< 100$ était une erreur de conception majeure qui créait artificiellement 21 abandons sur 45 tentatives. AAA utilise $w=200\%$ partout depuis toujours.
2. **Supprimer la destruction du closed set tous les 2 000 pas :**  
   L'A* doit conserver sa queue et son ensemble fermé tout au long de la recherche (`v294_rail_continuous=1`), exactement comme `AyStar` d'AAA.
3. **Augmenter la portée des ponts et tunnels à 20-30 tuiles :**  
   Déverrouiller les ponts longs pour franchir les plans d'eau et les voies ferrées transversales en ligne droite sans forcer un contournement terrestre ruineux.
4. **Pré-sélectionner 1 à 2 orientations de quai au lieu de 12 :**  
   Concentrer le front d'onde dès le premier tick de recherche.
