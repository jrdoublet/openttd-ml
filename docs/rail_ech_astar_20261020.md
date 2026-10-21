# Autopsie des abandons A* ferroviaires : OpexAI face à AAAHogEx

> **Date :** 20 octobre 2026  
> **Auteur :** Antigravity (agy)  
> **Branche de travail :** `railech` (dépôt `/home/deploy/projects/wt-railech`, dérivé de `master` `350f92e`)  
> **Objet :** Comprendre pourquoi 1 recherche ferroviaire sur 4 chez OpexAI s'achève par un abandon (`ABND` à `HARD_ITERATION_CAP = 5000`), y compris à moins de 100 tuiles de distance Manhattan, et pourquoi OpexAI ne tente presque jamais de liaisons $\ge 160$ tuiles, alors qu'AAAHogEx réussit 80 % de ses liaisons $\ge 160$ tuiles avec une médiane de seulement 13 appels `_FindPath(50)` (~650 itérations).

---

## 1. Table comparée exhaustive des deux A* ferroviaires

Chaque ligne et fichier ci-dessous a été vérifié par `grep -n` dans les arborescences [`ai/OpexAI/`](file:///home/deploy/projects/wt-railech/ai/OpexAI/) et [`ai/AAAHogEx-115/`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/).

| Caractéristique / Paramètre | OpexAI (`ai/OpexAI/`) | AAAHogEx (`ai/AAAHogEx-115/`) | Impact sur l'exploration |
|---|---|---|---|
| **Unité d'une « itération »** | 1 nœud extrait du tas binaire Squirrel (`open.Pop()`, [`pathfinder_v90/v129.nut:205`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L205)) et ses voisins explorés. | 1 nœud extrait de `AIPriorityQueue` natif C++ (`this._open.Pop()`, [`aystar.nut:115-117`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/aystar.nut#L115-L117)) et ses voisins explorés. | Même unité algorithmique stricte (1 nœud = 1 itération). AAA utilise une queue C++ native sans bytecode Squirrel. |
| **Sauts / segments droits sur terre** | Pas élémentaire cardinal tuile par tuile ([`pathfinder_v90/v129.nut:616-625`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L616-L625)). Aucun saut macro ni rayon de visée sur terre. | Pas élémentaire cardinal tuile par tuile ([`pathfinder.nut:1022, 1094-1122`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1022)). Aucun saut de ligne droite sur terre ferme. | Les deux explorent tuile par tuile en plaine. |
| **Poids de l'heuristique ($w$)** | **$w = 1,2$ (120 %)** si distance $< 100$ tuiles ([`globals_pre.nut:664`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L664) `V91_ASTAR_WEIGHT_PCT <- 120;`, [`builder_rail.nut:833`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L833)).<br>**$w = 2,0$ (200 %)** si distance $\ge 100$ tuiles ([`globals_pre.nut:92, 123`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L92), [`builder_rail.nut:830`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L830)). | **$w = 2,0$ (200 %)** universel, pour TOUTES les distances y compris $< 100$ ([`pathfinder.nut:86, 133, 820`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L86) `_estimate_rate = 2;`). | **Majeur** : à $w=1,2$, $g$ surpasse vite $h$ dès qu'il y a des virages, forçant l'A* d'Opex à dégénérer en nappe 2D pour les liaisons courtes. |
| **Formule de l'heuristique $h$** | $\min(dx, dy) \cdot 140 + (\max(dx, dy) - \min(dx, dy)) \cdot 100$ ([`pathfinder_v90/v129.nut:427, 448`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L427)). | $\min(dx, dy) \cdot 140 + (\max(dx, dy) - \min(dx, dy)) \cdot 100$ ([`pathfinder.nut:46, 802`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L46)). | Formule géométrique strictement identique (Manhattan octogonal pondéré). |
| **Coût unitaire tuile droite** | **100** ([`pathfinder_v90/rail.nut:64`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L64), [`v129.nut:495`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L495)). | **100** ([`pathfinder.nut:134, 659`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L134)). | Identique. |
| **Coût unitaire tuile diagonale** | **70** ([`pathfinder_v90/rail.nut:65`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L65), [`v129.nut:498`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L498)). | **67** ([`pathfinder.nut:126, 657`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L126)). | Quasi-identique (favorise la diagonale). |
| **Coût virage standard** | Entrée diagonale gratuite, sortie diagonale **+300** via V214 ([`globals_pre.nut:69`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L69), [`v129.nut:505-507`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L505-L507)). (50 historique si V214 inerte). | Entrée diagonale gratuite, sortie diagonale **+300** ([`pathfinder.nut:135, 665`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L135)). | Identique sous V214. |
| **Coût coude serré (90° sur 1 case)** | **+1500** (+100 si distance $< 40$) via V214 ([`globals_pre.nut:70`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L70), [`v129.nut:357, 510-519`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L357)). | **+1500** (+100 si distance $< 40$) ([`pathfinder.nut:136, 525-532`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L136)). | Identique sous V214. |
| **Coût pente de relief** | **100** ([`pathfinder_v90/rail.nut:67`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L67), [`v129.nut:528`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L528)). | **100** par défaut ([`pathfinder.nut:147, 675-693`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L147)), ou **1500** si motrice faible ([`pathfinder.nut:165-180`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L165-L180)). | AAA pénalise massivement les collines quand les trains manquent de puissance. |
| **Coût unitaire pont** | **100 + 150 = 250 / tuile** ([`pathfinder_v90/rail.nut:68`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L68), [`v129.nut:485`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L485)). | **100 / tuile** ([`pathfinder.nut:138, 597`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L138)) ; surcoût progressif +200 si $>7$ et +400 si $>11$ tuiles ([`pathfinder.nut:121-124, 598-603`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L121-L124)). | Pont plus lourdement taxé chez Opex dès la première tuile. |
| **Coût unitaire tunnel** | **100 + 120 = 220 / tuile** ([`pathfinder_v90/rail.nut:69`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L69), [`v129.nut:483`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L483)). | **0 / tuile** ([`pathfinder.nut:139, 581`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L139)) ; surcoût progressif +200 si $>7$ et +300 si $>11$ tuiles ([`pathfinder.nut:123-124, 582-587`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L123-L124)). | **Majeur** : AAA rend le percement de colline gratuit pour éviter de serpenter en surface. |
| **Longueur max pont / tunnel** | **Pont 6 tuiles, tunnel 6 tuiles** ([`pathfinder_v90/rail.nut:71-72`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L71-L72), [`v129.nut:642, 659`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L642)). | **Pont 30 tuiles, tunnel 11 à 14 tuiles** ([`pathfinder.nut:140-141, 184`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L140-L141)). | **Majeur** : obstacle d'eau ou relief $>6$ infranchissable en ligne droite chez Opex. |
| **Pont sur terrain plat (`SLOPE_FLAT`)** | **Interdit** : `if (slope == SLOPE_FLAT && IsBuildable(next)) return [];` ([`pathfinder_v90/rail.nut:569`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L569), [`v129.nut:638`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L638)). | Autorisé si obstacle sous-jacent non constructible ([`pathfinder.nut:1381-1393`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1381-L1393)). | Opex ne tente jamais de ponter depuis du plat sauf si la case suivante est non-constructible. |
| **Tunnels artificiels (`Underground`)** | **Non implémenté**. | **Oui** : `_GetUndergroundTunnel` ([`pathfinder.nut:1276-1349`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1276-L1349)), tunnel en tranchée sans falaise naturelle. | AAA traverse les plateaux et dénivelés en tunnel à niveau constant. |
| **Démolition dans l'A*** | **Strictement aucune**. `AITile.IsBuildable(tile)` obligatoire ([`pathfinder_v90/rail.nut:271-277`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L271-L277)). | **Oui** : démolition de ses propres rails inactifs (`CanDemolishRail`, [`pathfinder.nut:1164-1178`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1164-L1178)) et surélévation d'eau peu profonde (`_RaiseAtWater`, [`pathfinder.nut:1181-1196`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1181-L1196)). | AAA nettoie ses rails morts et remblaie les côtes. |
| **Traversée de routes (PN)** | Pas de surcoût spécifique (coût 100). | Pénalité **+900** (`_cost_level_crossing = 900`, [`pathfinder.nut:109, 567`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L109)). | AAA évite les passages à niveau sauf si nécessaire. |
| **Traversée de rails existants** | **STRICTEMENT INTERDITE** : `if (self._HasRail(cur_node)) return [];` ([`pathfinder_v90/v129.nut:589`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L589), [`rail.nut:487`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/rail.nut#L487)). | **AUTORISÉE sous pont** (`_CanChangeBridge`, `underBridge = true`, `_cost_under_bridge = 50`, [`pathfinder.nut:129, 823-855, 1044-1048`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L129)). | **CRITIQUE** : toute voie posée chez Opex ou par AAA devient un mur infranchissable pour Opex. |
| **Virages à 90 degrés** | U-turn sur 2 pas interdit (`offset == blocked`, [`v129.nut:622`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L622)). Coude serré pénalisé à +1500 via V214. | U-turn et virages 90° interdits ([`pathfinder.nut:1098-1102`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1098-L1102)). Coude serré pénalisé à +1500 ([`pathfinder.nut:136, 525-532`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L136)). | Équivalent. |
| **Départ et arrivée** | Jusqu'à 12 plans A et 12 plans B simultanés (`MAX_STATION_PLANS = 12`, [`builder_rail.nut:23, 840-845, 1164-1167`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L23)). | Gare pré-sélectionnée et construite / validée AVANT l'A* (`StationToStation`, [`railbuilder.nut:2154-2159`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/railbuilder.nut#L2154-L2159)) ; 1 à 2 vecteurs de sortie de gorge (`GetArrivalsTiles()`, [`station.nut:3525-3532`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/station.nut#L3525-L3532)). | Opex fait porter à l'A* le choix du quai parmi 12 combinaisons, diluant le front d'onde. |
| **Ré-utilisation de voies existantes** | Nulle dans l'A* (`_HasRail -> return []`, [`v129.nut:589`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L589)). | Aiguillages et fourches en gorge de gare autorisés (`fork = true`, [`pathfinder.nut:1034-1041`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1034-L1041)). | AAA réutilise les entrées de gare. |
| **Borne max_cost** | **`PATHFINDER_MAX_COST = 200000`** ([`builder_rail.nut:31, 856, 1233`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L31)). | **`_max_cost = 10000000`** (10 M, [`pathfinder.nut:68`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L68)). | Aucun blocage direct par max_cost chez Opex, mais marge 50× plus faible. |
| **Architecture globale** | **Recherche segmentée** ([`builder_rail.nut:1162`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L1162)) coupée à **2 000 itérations** (`SEGMENTED_SEGMENT_ITERS = 2000`, [`builder_rail.nut:62, 1330`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L62)) : destruction du pathfinder, perte du closed set, reprise sur frontière. Plafond dur = **5 000 iters** ([`globals_pre.nut:602`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L602)). | **Recherche continue unique** dans `AyStar`, sans segmentation ni destruction du graphe. Avancement par tranches de 50 itérations (`_FindPath(50)`, [`pathfinder.nut:209`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L209)), limite à **12 000 iters** (`pathFindLimit * 3 * 50`, [`trainroute.nut:3063`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/trainroute.nut#L3063), [`pathfinder.nut:199`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L199)). | **CRITIQUE** : la segmentation d'Opex jette son exploration après 2 000 pas ; dès le premier retour arrière, le plafond de 5 000 est atteint. |
| **Sonde inverse bidirectionnelle** | **Aucune** (recherche purement unidirectionnelle A → B). | **Oui** : mini-sonde de 100 iters depuis la cible toutes les tranches (`pathFinder2`, [`railbuilder.nut:2260-2266`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/railbuilder.nut#L2260-L2266)). | AAA court-circuite le calcul dès que le terrain inverse est plat. |
| **Corridor guidé seconde voie** | Guidage partiel `_outwardSide` / `_guideTiles` ([`builder_rail.nut:546-581`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L546-L581)). | Réservation latérale à l'aller (+3000), puis couloir BFS 1D strict de largeur 1 tuile (`_reverseNears`, `_cost_guide = 900`, [`pathfinder.nut:346-410, 805-813`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L346-L410)). | La seconde voie d'AAA aboutit en quelques dizaines d'itérations garanties. |
| **Plafond distance admissible** | **160 tuiles Manhattan** ([`globals_pre.nut:16`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L16) `V168_RAIL_MAX_DIST <- 160;`, [`candidates.nut:372, 417`](file:///home/deploy/projects/wt-railech/ai/OpexAI/candidates.nut#L372)). | Aucune borne fixe ; déterminée par le profit et la carte (jusqu'à 300+ tuiles). | **Explique à 100 %** pourquoi Opex ne tente presque jamais $\ge 160$ tuiles. |

---

## 2. Autopsie des abandons (`ABND`)

### 2.1 Synthèse globale (6 parties × 10 ans, graines 42, 7, 1234)

Données extraites des 6 parties de référence des campagnes `v270_expo_3x10_20261019_engine` et `v265fix_expo_complete_3x10_20261019_engine` via [`sweeps/rail_ech_autopsy.py`](file:///home/deploy/projects/wt-railech/sweeps/rail_ech_autopsy.py) (déduplication stricte identique à `sweeps/rail_ech_fail_cmp.py`) :

- **Tentatives OpexAI :** **154 tentatives**, **99 réussies (64,3 %)**, **55 échecs**.
- **Nature des échecs OpexAI :** **39 ABND (70,9 % de tous les échecs)**, 7 `TRKFAIL` (12,7 %), 4 `NOTRAIN` (7,3 %), 2 `STNFAIL` (3,6 %), 2 `NOPA` (3,6 %), 1 `SITEB` (1,8 %).
- **Tentatives AAAHogEx (`RouteBuilder`) :** **242 tentatives**, **175 réussies (72,3 %)**, **67 échecs**.
  - Ses échecs sont très majoritairement administratifs/topographiques immédiats (ex: pas de site de gare `No destStation` ou industrie fermée), sans gaspillage d'itérations A*.

### 2.2 Taux de succès et itérations par tranche de distance Manhattan

| Tranche Manhattan | OpexAI Réussite | OpexAI % | AAAHogEx Réussite | AAAHogEx % | Opex Itér. Méd. (OK) | Opex Itér. Méd. (ABND) | AAA Appels Méd. [Itér.] | AAA Jours Méd. |
|---|---|---|---|---|---|---|---|---|
| **0 – 60 tuiles** | 20 / 29 | 69,0 % | 71 / 107 | 66,4 % | 418 (29 à 4 748) | **5 000** (4 336 à 5 000) [n=6] | 1 appel [50 it] | 1 jour |
| **60 – 100 tuiles** | 31 / 49 | 63,3 % | 39 / 54 | 72,2 % | 2 297 (123 à 4 322) | **5 000** (5 000 à 5 000) [n=16] | 4 appels [200 it] | 3 jours |
| **100 – 160 tuiles** | 47 / 72 | 65,3 % | 28 / 35 | **80,0 %** | 524 (150 à 4 456) | **5 000** (5 000 à 5 000) [n=17] | 6 appels [300 it] | 3 jours |
| **160 – 250 tuiles** | 1 / 4 | **25,0 %** | 26 / 32 | **81,2 %** | 883 (883) [n=1] | — (0 tenté en ABND) | 7 appels [350 it] | 4 jours |
| **250+ tuiles** | **0 / 0** | — | 11 / 14 | **78,6 %** | — | — | 15 appels [750 it] | 11 jours |

> [!IMPORTANT]
> **Constat n°1 :** 22 des 39 abandons (56,4 %) ont lieu à **moins de 100 tuiles de distance**, dont 6 abandons à moins de 60 tuiles (distances 28, 28, 29, 36, 36, 36) !
> **Constat n°2 :** À distance égale (100–160 tuiles), quand Opex réussit, il consomme une médiane de 524 itérations (avec le poids V172 $w=200$). Mais chez AAA, une liaison de 160 tuiles prend 4 appels de 50 itérations (~200 itérations) en **2 à 3 jours de jeu**.
> **Constat n°3 :** Opex ne fait aucune tentative à $\ge 250$ tuiles et 4 seulement entre 160 et 250 tuiles, alors qu'AAAHogEx y maintient un taux de réussite de **80 %** avec une médiane de 350 à 750 itérations.

### 2.3 Tableau exhaustif des 39 abandons (`reason=ABND`)

| N° | Campagne | Graine | Date | Type | Tuile Src | Tuile Dst | Manh | Profit Prédit (£/an) | ROI Prédit | Poids A* ($w$) | Itérations | Opcodes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `v270` | 42 | 1973-10-10 | Fret | 12890 | 4884 | 101 | 29 488 £ | 632 | 200 | 5 000 | 7,5 M |
| 2 | `v270` | 42 | 1974-02-03 | Fret | 8935 | 28395 | 80 | 22 514 £ | 520 | 120 | 5 000 | 7,7 M |
| 3 | `v270` | 42 | 1974-04-06 | Fret | 47847 | 28395 | 80 | 22 514 £ | 520 | 120 | 5 000 | 6,8 M |
| 4 | `v270` | 42 | 1975-03-17 | Fret | 5537 | 22642 | 114 | 9 200 £ | 204 | 200 | 5 000 | 11,2 M |
| 5 | `v270` | 42 | 1976-03-16 | Fret | 59522 | 33405 | 107 | **107 523 £** | 1808 | 200 | 5 000 | 8,5 M |
| 6 | `v270` | 42 | 1976-06-04 | Fret | 12890 | 4884 | 101 | 38 605 £ | 752 | 200 | 5 000 | 6,8 M |
| 7 | `v270` | 42 | 1977-03-12 | Fret | 50791 | 14422 | 159 | **128 821 £** | 1775 | 200 | 5 000 | 11,0 M |
| 8 | `v270` | 42 | 1978-05-22 | Fret | 63361 | 56143 | 78 | 7 952 £ | 172 | 120 | 5 000 | 6,8 M |
| 9 | `v270` | 42 | 1978-09-16 | Fret | 5537 | 33405 | 145 | 11 143 £ | 265 | 200 | 5 000 | 8,7 M |
| 10 | `v270` | 42 | 1978-12-26 | Fret | 12890 | 4884 | 101 | 55 989 £ | 1358 | 200 | 5 000 | 10,0 M |
| 11 | `v270` | 42 | 1979-07-17 | Fret | 14418 | 12349 | **29** | 6 468 £ | 220 | 120 | 5 000 | 9,8 M |
| 12 | `v270` | 42 | 1979-09-17 | Pax | 59980 | 51219 | 91 | 5 654 £ | 156 | 120 | 5 000 | 6,6 M |
| 13 | `v270` | 42 | 1979-12-22 | Pax | 33442 | 21394 | 63 | 3 350 £ | 101 | 120 | 5 000 | 6,3 M |
| 14 | `v270` | 7 | 1972-07-22 | Fret | 44048 | 56172 | 139 | 28 955 £ | 535 | 200 | 5 000 | 7,0 M |
| 15 | `v270` | 7 | 1973-05-18 | Fret | 14158 | 16270 | 72 | 12 780 £ | 301 | 120 | 5 000 | 7,3 M |
| 16 | `v270` | 7 | 1973-10-22 | Fret | 10277 | 11843 | **36** | 6 923 £ | 185 | 120 | 5 000 | 9,0 M |
| 17 | `v270` | 7 | 1975-02-15 | Fret | 10277 | 11843 | **36** | 12 131 £ | 282 | 120 | 5 000 | 8,6 M |
| 18 | `v270` | 1234 | 1974-03-17 | Fret | 35648 | 54073 | 79 | 26 295 £ | 610 | 120 | 5 000 | 7,1 M |
| 19 | `v270` | 1234 | 1974-10-24 | Fret | 41311 | 59751 | 80 | 19 263 £ | 443 | 120 | 5 000 | 6,9 M |
| 20 | `v270` | 1234 | 1974-12-13 | Fret | 22161 | 10306 | 125 | 21 057 £ | 397 | 200 | 5 000 | 6,0 M |
| 21 | `v270` | 1234 | 1975-03-28 | Fret | 22161 | 10306 | 125 | 33 026 £ | 590 | 200 | 5 000 | 5,7 M |
| 22 | `v270` | 1234 | 1976-03-27 | Fret | 10306 | 32905 | 159 | **142 524 £** | 1905 | 200 | 5 000 | 7,8 M |
| 23 | `v270` | 1234 | 1976-06-10 | Fret | 22161 | 10306 | 125 | 15 093 £ | 284 | 200 | 5 000 | 6,1 M |
| 24 | `v270` | 1234 | 1978-06-14 | Fret | 10306 | 32905 | 159 | **110 929 £** | 1565 | 200 | 5 000 | 7,6 M |
| 25 | `v270` | 1234 | 1978-09-29 | Fret | 22161 | 10306 | 125 | 15 093 £ | 284 | 200 | 5 000 | 5,8 M |
| 26 | `v270` | 1234 | 1979-12-05 | Fret | 22161 | 10306 | 125 | 23 414 £ | 550 | 200 | 5 000 | 5,8 M |
| 27 | `v265fix` | 42 | 1978-07-03 | Fret | 63576 | 42610 | 108 | **80 921 £** | 1795 | 200 | 5 000 | 8,7 M |
| 28 | `v265fix` | 7 | 1973-10-10 | Fret | 33495 | 46570 | 70 | 16 023 £ | 378 | 120 | 5 000 | 7,1 M |
| 29 | `v265fix` | 7 | 1975-07-23 | Fret | 33495 | 46570 | 70 | 13 248 £ | 281 | 120 | 5 000 | 7,0 M |
| 30 | `v265fix` | 7 | 1976-03-14 | Pax | 11500 | 26585 | 78 | 5 967 £ | 128 | 120 | 5 000 | 6,5 M |
| 31 | `v265fix` | 7 | 1977-03-14 | Pax | 53372 | 48244 | **28** | 927 £ | 22 | 120 | 5 000 | 5,8 M |
| 32 | `v265fix` | 7 | 1978-07-30 | Pax | 11500 | 26585 | 78 | 9 384 £ | 193 | 120 | 5 000 | 6,7 M |
| 33 | `v265fix` | 7 | 1978-10-04 | Pax | 53372 | 48244 | **28** | 1 767 £ | 43 | 120 | 5 000 | 5,9 M |
| 34 | `v265fix` | 7 | 1979-08-12 | Fret | 2263 | 26585 | 97 | 63 705 £ | 1399 | 120 | 5 000 | 6,8 M |
| 35 | `v265fix` | 7 | 1979-12-14 | Pax | 53372 | 48525 | **36** | 542 £ | 18 | 120 | 4 336 | 5,4 M |
| 36 | `v265fix` | 1234 | 1975-06-16 | Fret | 35648 | 58628 | 150 | 56 467 £ | 967 | 200 | 5 000 | 6,8 M |
| 37 | `v265fix` | 1234 | 1975-10-11 | Fret | 10419 | 14563 | 64 | 3 699 £ | 82 | 120 | 5 000 | 6,1 M |
| 38 | `v265fix` | 1234 | 1976-12-05 | Pax | 34710 | 39767 | 83 | 4 455 £ | 94 | 120 | 5 000 | 6,8 M |
| 39 | `v265fix` | 1234 | 1978-01-07 | Fret | 10419 | 14563 | 64 | 3 291 £ | 73 | 120 | 5 000 | 5,9 M |

### 2.4 Analyse topographique et environnementale des paires abandonnées

L'extraction des coordonnées spatiales sur la grille OpenTTD 256×256 ($x = \text{tile} \pmod{256}$, $y = \lfloor \text{tile} / 256 \rfloor$) et le croisement avec les événements du journal moteur révèlent deux grands types d'échecs :

1. **L'effet « Mur de rails » (années 1973–1979) :**
   - **Exemple 1 : Paire n°5 `(59522, 33405)` (graine 42, 1976)**. Usine de biens (x=130, y=232) vers Ville 19 (x=125, y=130). Corridor quasi vertical nord-sud ($dx=5, dy=102$). Entre 1971 et 1975, les lignes 60 (`(37005, 61346)`), 63 (`(18773, 28869)`) et 66 ont été posées d'est en ouest en travers de ce couloir. Comme Opex interdit strictement de croiser un rail existant (`_HasRail -> return []`, [`pathfinder_v90/v129.nut:589`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L589)) et interdit de ponter sur terrain plat (`SLOPE_FLAT`, [`v129.nut:638`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L638)), cette voie transversale forme une **barrière physique étanche**. L'A* s'épuise à longer la voie ferrée sur des kilomètres à la recherche d'une ouverture qui n'existe pas.
   - **Exemple 2 : Paire n°20/21/23/25/26 `(22161, 10306)` (graine 1234, répétée 5 fois !)**. Src (x=145, y=86) vers Dst (x=66, y=40). La liaison est barrée par les premières lignes construites en 1971-1972 autour du carrefour central. Opex retente inlassablement cette paire car son profit prévu est attractif (15 à 33 k£/an), consommant à chaque passage 5 000 itérations et ~6 M opcodes pour rien.

2. **L'échec à courte distance ($< 60$ tuiles) par relief ou encerclement :**
   - **Exemple : Paires n°31, 33, 35 `(53372, 48244)` (graine 7, distance 28 tuiles)**. Src (x=124, y=208) vers Dst (x=116, y=188). À 28 tuiles seulement, le poids est $w=1,2$ ([`globals_pre.nut:664`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L664)). Le relief ou les habitations de la ville forcent des virages en S (pénalisés de 300 à 1 500 dans $g$). Le coût accumulé $g$ dépasse très vite $1,2 \cdot h$, l'A* s'étale en nappe sur 360°, atteint la coupure segmentée de 2 000 itérations, tente un point relais, échoue, et finit en `ABND` à 5 000 itérations sans jamais sortir de l'agglomération.

---

## 3. Hypothèses classées de la cause de divergence

### Hypothèse 1 (Priorité 1) : Heuristique trop faible ($w=1,2$ sous 100 tuiles) et amplification de $g$ par les coûts de virage V214

- **Éléments de code :**
  - [`ai/OpexAI/globals_pre.nut:664`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L664) : `V91_ASTAR_WEIGHT_PCT <- 120;` (conservé pour $D < 100$).
  - [`ai/OpexAI/globals_pre.nut:69-70`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L69-L70) : `V214_RAIL_TURN_COST <- 300; V214_RAIL_TIGHT_TURN_COST <- 1500;`.
  - [`ai/OpexAI/pathfinder_v90/v129.nut:507, 517`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L507) : injection de +300 par sortie de diagonale et +1500 par coude serré dans le coût accumulé $g$.
- **Mécanisme mathématique et mesure empirique :**
  Sur les tracés réussis de la graine 42 (via `V214_PATH`), nous avons comparé l'heuristique initiale $h(\text{départ})$ au coût réel $g$ reconstruit :
  - Sur une ligne droite dégagée, $g / h \approx 1,05$ à $1,15$.
  - Dès qu'il y a du relief ou des habitations imposant des virages (ex: $D=33$ tuiles, 10 sorties de diagonale et 4 coudes serrés), le coût réel explose à $g \approx 16\,000$ pour un $h = 2\,880$, soit un **ratio $g / h = 5,56$** !
  - À $w = 1,2$, un détour imposant un coude serré (+1 500 dans $g$) augmente la fonction d'évaluation $f(n) = g(n) + 1,2 \cdot h(n)$ de plus de 1 300 points. L'A* gèle immédiatement cette branche prometteuse et se met à dépiler tous les nœuds de la file ouverte dans toutes les directions (expansion d'une bulle 2D), gaspillant des milliers d'itérations.
  - Chez AAAHogEx, $w = 2,0$ universel ([`pathfinder.nut:133`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L133)) : avancer d'une case vers la cible diminue $2 \cdot h$ de 200. Le coût de 100 de la tuile est surcompensé ($f$ diminue de 100 à chaque pas), ce qui guide la recherche comme un rayon laser et absorbe sans broncher les pénalités de virage.
- **Sonde exacte à ajouter pour confirmation complète :**
  Dans [`ai/OpexAI/task_rail.nut:967`](file:///home/deploy/projects/wt-railech/ai/OpexAI/task_rail.nut#L967), compléter l'émission de `V214_PATH` avec :
  ```squirrel
  local astarG = ("path" in slice && slice.path != null && slice.path != false) ? slice.path._cost : -1;
  local astarH = ("pathfinder" in slice && slice.pathfinder != null) ? slice.pathfinder._Estimate(v214Tiles[0], 0, slice.pathfinder._goals, slice.pathfinder) : -1;
  OpexDecide("V214_PATH", ... + " g_cost=" + astarG + " h_start=" + astarH + " weight=" + state.weight);
  ```

### Hypothèse 2 (Priorité 2) : L'infranchissabilité des rails existants (`_HasRail`) combinée au verrou des ponts sur terrain plat

- **Éléments de code :**
  - [`ai/OpexAI/pathfinder_v90/v129.nut:589`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L589) : `if (self._HasRail(cur_node)) return [];`.
  - [`ai/OpexAI/pathfinder_v90/v129.nut:638`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L638) : `if (slope == AITile.SLOPE_FLAT && this._IsBuildable(cur_node + (cur_node - last_node))) return;`.
- **Mécanisme :**
  En OpenTTD, une voie ferrée posée sur terrain plat ne peut être franchie ni au sol (interdit par `_HasRail`), ni en tunnel (SLOPE_FLAT interdit le percement), ni par un pont (un pont sur terrain plat exige une rampe ou un dénivelé que `_TunnelsBridgesInto` ne construit pas). Dès 1974-1976, le réseau d'Opex et d'AAAHogEx découpe la carte en cellules étanches. Une ligne cherchant à relier une mine à une usine de l'autre côté d'une voie existante est **physiquement impossible à tracer**. L'A* explore toute la longueur de la voie adverse, atteint 5 000 itérations et abandonne.
- **Comparaison avec AAAHogEx :**
  AAAHogEx autorise le passage sous les ponts adverses ou la conversion d'une voie existante en pont pour passer en dessous (`_CanChangeBridge`, `underBridge = true`, [`pathfinder.nut:823-855`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L823-L855)), et autorise le creusement de tunnels artificiels `Underground` ([`pathfinder.nut:1276`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L1276)).

### Hypothèse 3 (Priorité 3) : L'amputation destructrice de la recherche segmentée (`SEGMENTED_SEGMENT_ITERS = 2000`)

- **Éléments de code :**
  - [`ai/OpexAI/builder_rail.nut:62`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L62) : `const SEGMENTED_SEGMENT_ITERS = 2000;`.
  - [`ai/OpexAI/builder_rail.nut:1330-1331`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L1330-L1331) :
    ```squirrel
    local frontier = OpexFrontierAlternatives(state.pathfinder, SEGMENTED_FRONTIER_WIDTH * 4);
    state.pathfinder = null; // <- DESTRUCTION TOTALE DU PATHFINDER
    ```
- **Mécanisme :**
  Lorsque l'A* n'a pas atteint la gare cible en 2 000 itérations (très fréquent à $w=1,2$ ou face à un obstacle), il jette l'instance `pathfinder`, perd l'intégralité de sa liste fermée, choisit un point frontière arbitraire, et réinstancie un nouvel A*. Si ce point frontière était une mauvaise direction, il déclenche un retour arrière (`backtrack`) qui consomme à nouveau des milliers d'itérations. Comme le plafond dur absolu est `HARD_ITERATION_CAP = 5000` ([`globals_pre.nut:602`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L602)), un seul segment coupé plus un demi-segment de reprise épuisent le budget de 5 000 et provoquent l'abandon `ABND`.
- **Comparaison avec AAAHogEx :**
  AAAHogEx ne segmente JAMAIS sa recherche : il conserve la même file ouverte `AIPriorityQueue` et la même liste fermée du début à la fin ([`aystar.nut:115`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/aystar.nut#L115)), avançant par tranches propres de 50 itérations ([`pathfinder.nut:209`](file:///home/deploy/projects/wt-railech/ai/AAAHogEx-115/pathfinder.nut#L209)).

### Hypothèse 4 : Le verrouillage du vivier candidat à 160 tuiles (`V168_RAIL_MAX_DIST = 160`)

- **Éléments de code :**
  - [`ai/OpexAI/globals_pre.nut:16`](file:///home/deploy/projects/wt-railech/ai/OpexAI/globals_pre.nut#L16) : `V168_RAIL_MAX_DIST <- 160;`.
  - [`ai/OpexAI/candidates.nut:372, 417`](file:///home/deploy/projects/wt-railech/ai/OpexAI/candidates.nut#L372) : `if (V168_RAIL_MAX_DIST > 0) railMax = V168_RAIL_MAX_DIST; catalog.bounds.railMax = railMax;`.
- **Mécanisme :**
  La question posée (« pourquoi nous ne tentons presque jamais $\ge 160$ tuiles ») trouve ici sa réponse immédiate et totale : le générateur de candidats ferroviaires élimine d'emblée toute paire dont la distance Manhattan dépasse `V168_RAIL_MAX_DIST` (160 tuiles). OpexAI ne peut pas tenter ce que son catalogue s'interdit de produire.

---

## 4. Recommandations concrètes (derrière réglages à défaut 0)

### Recommandation 1 : Extension du poids heuristique $w=2,0$ à toutes les distances ferroviaires

- **Principe :** Abaisser le seuil d'activation de V172 (`V172_RAIL_LONG_WEIGHT_DIST`) de 100 à 0, ou introduire un réglage unifiant le poids $w=2,0$ sur l'ensemble des recherches ferroviaires (comme AAAHogEx).
- **Emplacement :** [`ai/OpexAI/builder_rail.nut:828-834`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L828-L834) et [`ai/OpexAI/settings.nut`](file:///home/deploy/projects/wt-railech/ai/OpexAI/settings.nut).
- **Pseudo-code :**
  ```squirrel
  // builder_rail.nut:828
  function OpexRailAstarWeight(dist = null)
  {
    if (V294_RAIL_UNIFIED_WEIGHT_PCT > 0) {
      return V294_RAIL_UNIFIED_WEIGHT_PCT; // ex: 200
    }
    if (dist != null && V172_RAIL_LONG_WEIGHT_PCT > 0 && dist >= V172_RAIL_LONG_WEIGHT_DIST) {
      return V172_RAIL_LONG_WEIGHT_PCT;
    }
    return V91_ASTAR_WEIGHT_PCT;
  }
  ```
- **Validation courte :** Smoke mono-mode rail 42 × 3 ans avec `decision_log=1` (`v294_rail_unified_weight_pct=200` contre 0). Mesurer le taux d'abandon sur les distances $<100$ tuiles (actuellement 56 % des ABND) et la baisse des itérations médianes à $<60$ tuiles (de 418 à ~50).

### Recommandation 2 : Mode de recherche A* continu (désactivation de la coupure de segment à 2 000 iters)

- **Principe :** Supprimer la destruction du pathfinder à 2 000 itérations en permettant à l'A* de poursuivre dans le même graphe exploré jusqu'à trouver la solution ou atteindre son budget, évitant les faux départs et les backtracks destructeurs.
- **Emplacement :** [`ai/OpexAI/builder_rail.nut:1222-1250, 1327-1335`](file:///home/deploy/projects/wt-railech/ai/OpexAI/builder_rail.nut#L1222).
- **Pseudo-code :**
  ```squirrel
  // builder_rail.nut:1229
  local segmentCap = (V294_RAIL_CONTINUOUS_ASTAR > 0) ? state.iterationBudget : SEGMENTED_SEGMENT_ITERS;
  ```
- **Validation courte :** Même smoke rail 42 × 3 ans (`v294_rail_continuous_astar=1`). Vérifier si les recherches de 80–140 tuiles aboutissent de manière continue sans générer de `segmentedBacktracks`.

### Recommandation 3 : Franchissement des voies ferrées adverses et pontage sur plat

- **Principe :** Autoriser le pathfinder à tester un pont par-dessus une tuile contenant du rail (`_HasRail`) même si le terrain de départ est `SLOPE_FLAT`, dès lors que la tuile cible au-delà de la voie est constructible.
- **Emplacement :** [`ai/OpexAI/pathfinder_v90/v129.nut:637-640`](file:///home/deploy/projects/wt-railech/ai/OpexAI/pathfinder_v90/v129.nut#L637-L640).
- **Pseudo-code :**
  ```squirrel
  // v129.nut:638
  local nextTile = cur_node + (cur_node - last_node);
  if (slope == AITile.SLOPE_FLAT && this._IsBuildable(nextTile)) {
    if (V294_RAIL_CROSS_RAIL == 0 || !this._HasRail(nextTile)) return;
  }
  ```
- **Validation courte :** Smoke 42 × 6 ans pour observer si le blocage total de 1974–1979 est levé.

---

## 5. Annexe : Commandes exécutées pour l'extraction et l'autopsie

Toutes les données présentées ci-dessus ont été produites par l'exécution stricte des commandes suivantes :

```bash
# 1. Vérification des invariants Git et de non-pollution du dépôt
git -C /home/deploy/projects/wt-railech status --short

# 2. Exécution du comparateur initial sur les archives
python3 sweeps/rail_ech_fail_cmp.py \
  /home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v270/results/v270_expo_3x10_20261019_engine \
  /home/deploy/projects/openttd-ml/results/worktrees_archives_20261020/wt-v265fix/results/v265fix_expo_complete_3x10_20261019_engine

# 3. Autopsie détaillée et extraction des 39 abandons et des métriques de distance
python3 sweeps/rail_ech_autopsy.py

# 4. Vérification de la suite de tests unitaires (2 183 tests OK)
python3 -m unittest discover -s sweeps -p 'test_*.py'
```
