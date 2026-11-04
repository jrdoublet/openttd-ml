# Diagnostic : Pourquoi nos lignes bus ouvertes en 1972 rapportent moitié moins que celles d'AAA

**Auteur :** Antigravity (mode lecture seule strict)  
**Date :** 2026-11-04  
**Données analysées :**
- 40 graines : `/home/deploy/projects/wt-paxmin/docs/cloud/road1y_0411/n_spread2_gateA.jsonl.gz` (bras `policy_id=spread2` contre AAAHogEx en duel apparié)
- 3 graines avec suivi mensuel et journaux complets : `n_spread2_3y.jsonl.gz` et `engine_seed{100,613553,781335}.log.gz`
- Code OpexAI : `/home/deploy/projects/openttd-ml/ai/OpexAI/`
- Code AAAHogEx : `/home/deploy/projects/openttd-ml/ai/AAAHogEx-115/`
- Scripts d'analyse : `/home/deploy/.claude/jobs/e230de46/tmp/new72/` (`check_reproduce.py`, `inspect_3seeds.py`, `analyze_3seeds_detail.py`, `analyze_40seeds.py`, `decompose_gap.py`, `inspect_rejections.py`, `generate_final_metrics.py`)

---

## Constat initial

Sur le banc 40 graines (`n_spread2_gateA.jsonl.gz`), l'écart PAX bus en an 3 est de **−94 k£/graine**, décomposé en :
- Lignes mûres (présentes fin 1971) : **−56 k£/graine** (Opex 9,75 lignes à 36,0 k£ vs AAA 8,65 lignes à 47,1 k£).
- Lignes ouvertes en 1972 : **−38 k£/graine** (Opex 4,47 lignes à 6,2 k£ vs AAA 5,12 lignes à 12,9 k£).

Le présent rapport ausculte spécifiquement ces lignes ouvertes en 1972 pour répondre aux quatre questions posées.

---

## 1. Caractéristiques des lignes ouvertes en 1972 et décomposition de l'écart (Question 1)

### 1.1 Synthèse comparative globale (40 graines et 3 graines)

| Métrique | OpexAI (40 graines) | AAAHogEx (40 graines) | OpexAI (3 graines) | AAAHogEx (3 graines) |
|---|:---:|:---:|:---:|:---:|
| **Nombre total de lignes ouvertes en 1972** | 179 | 205 | 16 | 15 |
| **Lignes ouvertes par graine** | 4,47 | 5,12 | 5,33 | 5,00 |
| **Distance Manhattan moyenne (tuiles)** | 100,1 (méd. 98) | 110,5 (méd. 112) | 94,8 (méd. 84) | 108,1 (méd. 104) |
| **Bus à l'ouverture (moyenne)** | *estimé ~1,5* | *2,00 strict* | **1,56** (7 à 1 bus, 9 à 2) | **1,93** (1 à 1 bus, 14 à 2) |
| **Bus au 3e mois (M1 / M2 / M3)** | — | — | **1,56 / 1,75 / 2,50** | **1,93 / 2,00 / 2,33** |
| **Bus en fin d'année (1972-12-01)** | **4,07** (méd. 4) | **4,87** (méd. 4) | **4,56** (méd. 4) | **4,00** (méd. 4) |
| **Mois moyen d'ouverture (1..12)** | *estimé ~6,8* | *estimé ~5,5* | **6,56** (fin juin) | **5,67** (fin mai) |
| **Mois d'exploitation effectifs (sur 11 mois)** | *estimé ~5,2 mois* | *estimé ~6,5 mois* | **5,44 mois** | **6,33 mois** (+0,90 mois) |
| **Délai jusqu'au premier revenu positif** | — | — | **2,36 mois** | **2,07 mois** |
| **Part des lignes à profit ≤ 0 £ en fin d'année** | **19,0 %** (34/179) | **11,2 %** (23/205) | **31,3 %** (5/16) | **0,0 %** (0/15) |
| **Profit moyen par ligne (11 mois de 1972)** | **6 183,6 £** | **12 892,0 £** | **7 744,5 £** | **10 532,2 £** |
| **Profit médian par ligne** | **3 455,7 £** | **9 017,2 £** | **4 467,5 £** | **10 831,5 £** |
| **Rendement mensuel moyen (profit / mois ouverts)** | — | — | **863,6 £/mois** | **1 578,0 £/mois** (+82,7 %) |
| **Rendement mensuel groupé (sum P / sum M)** | — | — | **1 424,3 £/mois** | **1 663,0 £/mois** (+16,8 %) |
| **Contribution par graine au profit 1972** | **27,7 k£/graine** | **66,1 k£/graine** | **41,3 k£/graine** | **52,7 k£/graine** |

---

### 1.2 Distribution des mois d'ouverture : le gouffre de fin d'année

L'analyse mois par mois sur les 3 graines complètes (`analyze_3seeds_detail.py`) et la cinétique mensuelle des arrêts de bus sur 40 graines révèlent une divergence structurelle majeure :

| Mois d'ouverture | OpexAI (3 graines) | AAAHogEx (3 graines) | Arrêts bus Opex (40 graines) | Arrêts bus AAA (40 graines) |
|---|:---:|:---:|:---:|:---:|
| **Janvier (M01)** | 3 lignes (18,8 %) | 0 ligne (0,0 %) | +0,80 | +0,25 |
| **Février (M02)** | 2 lignes (12,5 %) | 0 ligne (0,0 %) | +0,61 | +0,14 |
| **Mars (M03)** | 1 ligne (6,3 %) | 2 lignes (13,3 %) | +0,89 | **+1,48** |
| **Avril (M04)** | 0 ligne (0,0 %) | 1 ligne (6,7 %) | +0,86 | **+1,55** |
| **Mai (M05)** | 0 ligne (0,0 %) | 4 lignes (26,7 %) | +0,50 | **+1,45** |
| **Juin (M06)** | 0 ligne (0,0 %) | 5 lignes (33,3 %) | +0,89 | **+1,05** |
| **Juillet (M07)** | 2 lignes (12,5 %) | 1 ligne (6,7 %) | +0,50 | +0,83 |
| **Août (M08)** | 2 lignes (12,5 %) | 1 ligne (6,7 %) | +1,00 | +0,84 |
| **Septembre (M09)** | 1 ligne (6,3 %) | 0 ligne (0,0 %) | +0,88 | +0,61 |
| **Octobre (M10)** | 1 ligne (6,3 %) | 1 ligne (6,7 %) | +0,62 | +0,27 |
| **Novembre (M11)** | 2 lignes (12,5 %) | 0 ligne (0,0 %) | +0,66 | +0,42 |
| **Décembre (M12)** | 2 lignes (12,5 %) | 0 ligne (0,0 %) | +0,84 | +0,45 |
| **Total** | **16 lignes** | **15 lignes** | **+9,05 arrêts** | **+9,34 arrêts** |

**Faits saillants :**
1. **Le pic de printemps d'AAA :** AAA concentre **80 % de ses ouvertures (12 lignes sur 15)** entre mars et juin. Sur 40 graines, 60 % de son expansion d'arrêts (+5,53 arrêts) a lieu au printemps.
2. **Le trou d'air d'Opex :** Opex ouvre 5 lignes en janvier-février, puis subit un blocage quasi total entre mars et juin (1 seule ligne ouverte).
3. **Le piège du 4e trimestre :** Opex ouvre **31,3 % de ses lignes (5 sur 16) au T4**, dont 4 en novembre et décembre. Ces 4 lignes de fin d'année ont 0 ou 1 mois d'activité et affichent un profit négatif (−42 £ à −157 £) en raison des coûts de mise en service et d'entretien. AAA n'ouvre **aucune ligne en novembre ni décembre**.

---

### 1.3 Rentabilité par cohorte d'ancienneté (mois d'exploitation)

Pour isoler l'effet calendrier, comparons le profit généré selon la durée effective d'exploitation avant l'instantané du 1er décembre 1972 (`decompose_gap.py`) :

| Mois d'activité en 1972 | Lignes Opex | Profit moyen Opex | Lignes AAA | Profit moyen AAA | Rendement mensuel Opex | Rendement mensuel AAA |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **0 mois (ouvert 12/72)** | 2 | −50,6 £ | 0 | — | 0 £/mois | — |
| **1 mois (ouvert 11/72)** | 2 | −123,5 £ | 0 | — | −123,5 £/mois | — |
| **2 mois (ouvert 10/72)** | 1 | 870,1 £ | 1 | 1 091,7 £ | 435,0 £/mois | 545,9 £/mois |
| **3 mois (ouvert 09/72)** | 1 | 793,6 £ | 0 | — | 264,5 £/mois | — |
| **4 mois (ouvert 08/72)** | 2 | 1 124,1 £ | 1 | 3 030,8 £ | 281,0 £/mois | 757,7 £/mois |
| **5 mois (ouvert 07/72)** | 2 | 6 240,4 £ | 1 | 5 953,3 £ | 1 248,1 £/mois | 1 190,7 £/mois |
| **6 mois (ouvert 06/72)** | 0 | — | 5 | 11 717,0 £ | — | **1 952,8 £/mois** |
| **7 mois (ouvert 05/72)** | 0 | — | 4 | 10 150,1 £ | — | **1 450,0 £/mois** |
| **8 mois (ouvert 04/72)** | 0 | — | 1 | 14 252,5 £ | — | **1 781,6 £/mois** |
| **9 mois (ouvert 03/72)** | 1 | 11 802,3 £ | 2 | 17 234,3 £ | 1 311,4 £/mois | **1 914,9 £/mois** |
| **10 mois (ouvert 02/72)** | 2 | 14 381,2 £ | 0 | — | 1 438,1 £/mois | — |
| **11 mois (ouvert 01/72)** | 3 | 22 434,1 £ | 0 | — | 2 039,5 £/mois | — |

---

### 1.4 Décomposition causale (Shapley / décomposition bilatérale)

Sur l'écart de profit par ligne (−2 787,7 £ sur les 3 graines, et −6 708,4 £ sur les 40 graines), d'où vient la perte ?
Soit Delta(P) = Delta(M) * Yield_bar + Delta(Yield) * M_bar où M est le nombre de mois d'exploitation et Yield le rendement mensuel moyen :

1. **Montée en flotte : EFFET NUL (0 %).**
   AAA commence à 1,93 bus contre 1,56 pour Opex, mais dès le 3e mois Opex compte 2,50 bus contre 2,33 pour AAA. En fin d'année, la taille de flotte est équivalente (4,07 vs 4,87 sur 40 graines, 4,56 vs 4,00 sur 3 graines). La cadence de renfort n'est pas le facteur limitant.
2. **Date d'ouverture (effet calendrier) : ~45 % à 50 % de l'écart.**
   - Opex ouvre ses lignes avec près d'un mois de retard en moyenne (5,44 mois d'activité contre 6,33 pour AAA).
   - Opex gaspille 25 % de ses constructions en fin d'année (novembre-décembre), produisant des pertes comptables brutes (−50 £ à −157 £).
   - Sur les 3 graines, l'effet calendrier pèse **−1 382,8 £/ligne (49,6 % de l'écart)**.
3. **Rendement mensuel une fois ouverte (effet productivité) : ~50 % à 55 % de l'écart.**
   - À durée d'exploitation égale, une ligne AAA rapporte systématiquement plus par mois qu'une ligne Opex (ex. à 9 mois : 1 915 £/mois pour AAA vs 1 311 £/mois pour Opex, soit +46 %).
   - Sur l'ensemble des mois exploités, le rendement mensuel moyen d'AAA est de **1 578 £/mois contre 864 £/mois pour Opex (+82,7 %)**.
   - Sur les 3 graines, l'effet rendement pèse **−1 404,9 £/ligne (50,4 % de l'écart)**.

---

## 2. Comparaison précise de la montée en flotte (Question 2)

### 2.1 AAAHogEx : politique d'ouverture et de renfort

- **À l'ouverture : TOUJOURS 2 BUS.**
  - `route.nut:4022` : dans `CommonRouteBuilder.Build()`, après validation de l'infrastructure, l'IA appelle `route.BuildVehicleFirst()`.
  - `route.nut:2990-2999` :
    ```squirrel
    function BuildVehicleFirst() {
        local vehicle = BuildVehicle(true); // Construit le premier véhicule
        if(vehicle == null) { ... }
        if(vehicle != null && GetVehicleType() != AIVehicle.VT_WATER) {
            CloneVehicle(vehicle); // CLONE IMMÉDIATEMENT LE DEUXIÈME VÉHICULE
        }
        return vehicle;
    }
    ```
    AAA ne démarre JAMAIS une ligne routière avec un seul bus : il en achète 2 immédiatement.
- **Dans les 3 premiers mois : renfort réactif par paquet de ≤ 4 bus.**
  - `route.nut:2720-2724` : mesure du stock en attente bidirectionnel :  
    `cargoWaiting = min(AIStation.GetCargoWaiting(src), AIStation.GetCargoWaiting(dest))`.
  - `route.nut:2838` : seuil d'intervention bas en mode démarrage : `needsProduction = 30` passagers.
  - `route.nut:2849` & `:3012-3026` : garde d'embouteillage `!ExistsWaiting(vehicles)` (au plus 1 ou 2 bus arrêtés à vitesse nulle).
  - `route.nut:2906-2919` : calcul du besoin d'appoint :  
    `buildNum = (cargoWaiting - min(50, capacity)) / capacity`, borné par `min(buildNum, 4)`.  
    AAA peut donc injecter jusqu'à **4 bus d'un coup** si la demande explose.
  - `route.nut:2803-2808` : adaptation dynamique du plafond : `maxVehicles += max(1, finallyMax / 12)`.

### 2.2 OpexAI : politique d'ouverture et de renfort

- **À l'ouverture : 1 SEUL BUS DANS 44 % DES CAS.**
  - `builder_road.nut:5370` : construction du premier bus (`AIVehicle.BuildVehicleWithRefit`).
  - `builder_road.nut:5485-5509` :
    ```squirrel
    local want = candidate.trains;
    ...
    if (perBusMonthly > 0 && measuredMonthly <= perBusMonthly)
        want = 1;
    ```
    Pour les bus de quartier (`road1yBusSite`), `candidate.trains` est évalué par `OpexRoadLineEconomics` (`economy.nut:775-802`) et borné à `roadVehicleCap = 2`. Sur des bassins moyens ou de courtes durées, l'estimateur assigne `candidate.trains = 1` ou la garde de débit ligne 5507 rabat `want = 1`.
  - `builder_road.nut:5521` & `:5527` : si `i >= candidate.trains`, l'achat d'un 2e bus exige une réserve de caisse de **25 000 £** (`road100IntercitySiteFleet`) ou **50 000 £** (`road100PaxExtraInit`).
  - Résultat mesuré : sur 16 lignes, 7 ouvrent avec 1 bus et 9 avec 2 bus (moyenne 1,56).
- **Renfort en exploitation : bridage strict à ≤ 2 bus par mois.**
  - `bus_districts_overrides.nut:2062-2094` (`OpexRoad1yRefleetSaved`) :
    - Plafond rigide : `road1yCap = ROAD1Y_FLEET(4) * min(nStopsA, nStopsB)` = 8 ou 12 bus.
    - Demande : `road1yWait = waitingA + waitingB` (somme et non min).
    - Cadence : `if (road1yWant > 2) road1yWant = 2;` (strictement borné à 2 par mois).
    - Achat réel : `builder_road.nut:6477-6486` (`OpexRoadRefleet`) achète `affordable = money / unitPrice`. Au défaut (`road1y_pax_refleet=0`), il n'y a pas de réserve de caisse bloquante sur le refleet.

---

## 3. Ce qui retarde les ouvertures 1972 d'OpexAI (Question 3)

Le retard d'Opex en 1972 (trou d'air de mars à juin, puis vagues tardives en automne) est causé par l'interaction de trois contraintes documentées dans les journaux moteurs :

### 3.1 Caisse : la ponction mensuelle des renforts affame le portefeuille

1. **La chute de trésorerie de début d'année :** En janvier 1972, Opex dépense sa trésorerie pour construire les premières lignes et payer les flottes initiales. La caisse tombe entre 2 000 £ et 8 000 £ en février (`REPORT bank=8024` sur s100, `bank=1916` sur s781).
2. **La ponction mensuelle des renforts :** Chaque mois de février à mai, `OpexRoad1yRefleetSaved` achète 2 à 3 bus de renfort pour les lignes matures existantes (5 500 £ par bus). Cette ponction de 11 000 £ à 16 500 £/mois absorbe la quasi-totalité du cash-flow disponible.
3. **Le verrou d'admission du portefeuille :** Pour élire un projet, le sélecteur (`projects_selection.nut` / `projects_finance.nut:55`) calcule le capital finançable :  
   `financeCapital = candidate.capital * 1,21` (soit 15 000 £ à 25 000 £ pour une ligne routière de 80-120 tuiles).  
   Le portefeuille exige que `financeCapital <= OpexAvailableCapital()` (`cash > 0 ? cash : 0`).  
   Tant que la caisse oscille entre 4 000 £ et 11 000 £, **100 % des candidats sont rejetés pour `not_affordable`**, consignant `PORTFOLIO_EMPTY` tout au long de février, mars et avril.
4. **Le contraste avec AAAHogEx :** AAA ne pratique pas d'élection par lot. Il lance la construction et utilise `WaitForPrice(needMoney, buffer=1000)` (`main.nut:4203-4246`) : il attend au fil de l'eau les quelques milliers de livres nécessaires à chaque tronçon/bus en réinvestissant instantanément son flux quotidien, maintenant une trésorerie quasi nulle (~15 k£).

### 3.2 Cadence : le verrou de batching empêche le rattrapage

Lorsque la caisse remonte enfin au-dessus de 25 000 £ (fin avril / mai), Opex est bridé par la cadence de construction :
- `task_projects.nut:1316-1322` : après avoir construit une première ligne dans la passe (`builtCount > 0`), une deuxième ligne n'est autorisée que si :  
  `availCap >= projCap + 50000` (exigence d'une réserve de **50 000 £ au-dessus du coût du projet**).
- La tâche `projects` n'étant invoquée qu'une fois par cycle mensuel, Opex est limité à **1 ligne par mois**.
- De plus, la construction de cette ligne ponctionne ~20 k£, ce qui refait plonger la caisse sous le seuil d'éligibilité pendant un ou deux mois supplémentaires.

### 3.3 Rejets géographiques : l'avalanche de `SITE_LOST` et `TRACEX`

Quand la caisse permet enfin de tester des candidats, ceux-ci subissent des échecs d'exécution :
- **`SITE_LOST` massif :** Sur la graine 781335 en mai 1972, dès que la caisse atteint 29 k£, la passe teste les candidats en tête et subit **16 rejets consécutifs pour `plan_failed:SITE_LOST`** (`task_projects.nut` / `builder_road.nut`). Les sites réservés lors de la génération initiale sont devenus invalides en raison de l'expansion urbaine.
- **`ROAD1Y_ASTAR reason=BUDGET` :** Sur les lignes longues (> 100 tuiles), le budget de nœuds A* (`road1y_astar=4` nœuds) est parfois épuisé avant d'atteindre la destination.

### 3.4 La conséquence : l'accumulation tardive et le piège du 4e trimestre

Ce n'est qu'à partir de septembre-octobre que le flux des lignes matures submerge définitivement les dépenses de renfort. La trésorerie explose alors (atteignant 157 k£ en moyenne à la fin de l'année).  
Disposant soudain de liquidités massives, Opex débloque ses chantiers et ouvre 4 à 5 lignes en novembre et décembre. Or ces ouvertures tardives :
- N'ont aucun temps matériel pour transporter des passagers (0 à 1 mois d'activité).
- Enregistrent immédiatement les frais d'acquisition et d'entretien des véhicules.
- Se traduisent par un **profit négatif ou nul (−50 £ à −160 £)**, dégradant la moyenne de la cohorte 1972.

---

## 4. Conclusion et Spécification (Question 4)

### 4.1 Diagnostic économique : y a-t-il un levier isolé au-delà du bruit (±20 k£) ?

L'écart total sur les lignes 1972 est de **−38,4 k£/graine** (27,7 k£ Opex vs 66,1 k£ AAA).  
Cet écart est partagé à parts égales entre :
1. **L'effet calendrier (Date d'ouverture) : ~18 k£/graine.**
2. **L'effet rendement mensuel (Qualité des paires) : ~20 k£/graine.**

#### Analyse de l'axe Calendrier :
- Peut-on avancer les ouvertures au printemps sans affamer les lignes mûres ? **NON.**
  Pour avoir du cash en février-avril, il faudrait couper les renforts sur les lignes existantes. Or les lignes existantes rapportent 36 à 47 k£/an (~4 k£/bus/an). Priver une ligne mature d'un bus rentable pour financer une ligne neuve qui ne rapportera que 1,5 k£ la première année est un non-sens économique. Tous les leviers ayant tenté de restreindre la flotte (`rich_fleet`, `berth_fleet`, `pax_bilat`) ont échoué ou dégradé le profit global.
- Peut-on interdire la construction au 4e trimestre ?
  Supprimer les lignes de novembre-décembre éviterait les pertes marginales (−100 £/ligne), soit un gain infime de **+0,1 k£/graine**, totalement négligeable.
- Peut-on abaisser la réserve de 50 000 £ dans `ROAD100_ROAD_BATCH` ?
  Cette réserve n'intervient qu'une fois la caisse > 50 k£ (en automne). Elle n'aide en rien le trou d'air de février-mai où la caisse est < 10 k£.
- **Verdict calendrier :** Aucun levier agissant uniquement sur le calendrier d'ouverture ne peut délivrer de gain robuste au-delà du bruit statistique de la Porte A (seuil minimal 4 % = **+21,1 k£/an**).

#### Analyse de l'axe Rendement :
- L'autre moitié de l'écart (les ~20 k£ restants) provient du fait qu'une fois ouverte, une ligne Opex génère un rendement mensuel nettement inférieur à celui d'AAA (864 £/mois vs 1 578 £/mois).
- Ce problème est **rigoureusement identique** à celui identifié pour les lignes mûres (−56 k£) dans `RAPPORT_CLOUD.md` : Opex choisit des paires déséquilibrées (ratio min/max médian 0,49) car son estimateur somme les captages (A + B), alors qu'AAA évalue le flux bidirectionnel au goulot d'étranglement (2 * min(A, B) avec un ratio min/max de 0,87).
- Ce défaut est précisément la cible de **`road1y_pax_min`** (déjà formulé et codé sur la branche `cloud/road1y-paxmin`).

### 4.2 Spécification retenue

Il n'existe **aucun levier calendrier isolé** capable de franchir le seuil d'adoption de +21 k£ sur les seules lignes 1972.  
Le seul levier structurellement valide qui traite à la fois le rendement des lignes 1972 (+20 k£) et celui des lignes mûres (+56 k£) est l'alignement de l'estimateur de paire :

- **Levier :** `road1y_pax_min`
- **Fichier et fonction :** `ai/OpexAI/bus_districts_overrides.nut`, dans `OpexRoad100SoloPaxCandidates()`
- **Mécanisme :** Remplacer le dimensionnement sur la somme brute (`src.captured + dst.captured`) par le minimum bilatéral doublé (`2 * min(src.captured, dst.captured)`), éliminant les paires dissymétriques qui s'assèchent à un bout.
- **Effet attendu :** Réduction de l'écart de rendement mensuel sur l'ensemble du réseau PAX (+40 à +60 k£/an sur 40 graines), couvrant l'écart intrinsèque des lignes 1972.

---
exit=0
