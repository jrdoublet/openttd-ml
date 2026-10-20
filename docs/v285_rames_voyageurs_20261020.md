# Diagnostic V285 : Rames voyageurs en rail seul (20 octobre 2026)

Diagnostic établi conformément aux consignes de `AGENTS.md` à partir des données existantes (sans exécution de nouveau banc Docker).

## 1. Sources des données et protocoles

Les analyses reposent sur les campagnes suivantes, issues du worktree `/home/deploy/projects/wt-v275` :
1. **Campagne 10×3 (exposition rail seul avec `decision_log=1`) :**
   - Fichier de synthèse et télémétrie : `/home/deploy/projects/wt-v275/results/v275_expo_railseul_10x3_20261019.json`
   - Manifeste : `/home/deploy/projects/wt-v275/results/v275_expo_railseul_10x3_20261019.manifest.json`
   - Journaux moteur (20 fichiers, 10 graines canoniques 1..2026, duel OpexAI contre AAAHogEx) :
     `/home/deploy/projects/wt-v275/results/v275_expo_railseul_10x3_20261019_engine/v275m7_seed*.log` (bras variante V275 mm=7) et `reference_seed*.log` (bras référence).
   - Réglages du bras variante : `OpexAI[decision_log=1,mode_air=0,mode_road=0,mode_water=0,v207_rail_pax_share_pct=40,v207_rail_mail=1,v207_rail_pax_joined_stops=2,v275_rail_pax_mm=7]`.
2. **Campagne 20×10 (Porte B rail seul validée, horizon 10 ans) :**
   - Fichier de synthèse : `/home/deploy/projects/wt-v275/results/v275_railseul_porteB_20x10_vps_20261019.json`
   - Manifeste : `/home/deploy/projects/wt-v275/results/v275_railseul_porteB_20x10_vps_20261019.manifest.json`
   - Journaux moteur (40 fichiers, 20 graines canoniques, 10 ans) :
     `/home/deploy/projects/wt-v275/results/v275_railseul_porteB_20x10_vps_20261019_engine/v275_seed*.log` et `reference_seed*.log`.

---

## 2. Caractéristiques de nos lignes voyageurs rail (OpexAI)

Sur les 10 graines de l'exposition rail seul `v275m7` (10×3), **118 lignes voyageurs** ont été construites (`RAIL_BUILD line=... cargo=PASS`).
À l'échéance de 3 ans (fin 1972), la télémétrie relève **116 lignes voyageurs actives** (11,6 lignes par graine en moyenne).

### A. Composition des rames à la construction (118 lignes analysées)
- **Wagons passagers (`wagons`) :**
  - 1 wagon (40 places) : 22 lignes (18,6 %)
  - 2 wagons (80 places) : 58 lignes (49,2 %)
  - 3 wagons (120 places) : 30 lignes (25,4 %)
  - 4 wagons (160 places) : 7 lignes (5,9 %)
  - 5 wagons (200 places) : 1 ligne (0,8 %)
  - **Moyenne : 2,21 wagons passagers par rame, soit 88,5 places assises.** (Médiane : 2 wagons / 80 places).
- **Wagons courrier (`wagons2`, plomberie V163/V207) :**
  - 1 wagon (30 sacs) : 62 lignes (52,5 %)
  - 2 wagons (60 sacs) : 48 lignes (40,7 %)
  - 3 wagons (90 sacs) : 8 lignes (6,8 %)
  - **Moyenne : 1,54 wagon courrier par rame (46,3 sacs).** (Médiane : 1 wagon / 30 sacs).
- **Nombre total de wagons par rame :**
  - 2 wagons (1 pax + 1 mail) : 22 lignes (18,6 %)
  - 3 wagons (2 pax + 1 mail) : 40 lignes (33,9 %)
  - 4 wagons (2 pax + 2 mail ou 3 pax + 1 mail) : 18 lignes (15,3 %)
  - 5 wagons (3 pax + 2 mail) : 30 lignes (25,4 %)
  - 7 wagons (4 pax + 3 mail ou 5 pax + 2 mail) : 7 lignes (5,9 %)
  - 8 wagons (5 pax + 3 mail) : 1 ligne (0,8 %)
  - **Moyenne : 3,75 wagons totaux par rame.**
- **Longueur physique de la rame (locomotive 8/16 + wagons 8/16) :**
  - 1,5 tuile (1 loco + 2 wagons) : 22 lignes (18,6 %)
  - 2,0 tuiles (1 loco + 3 wagons) : 40 lignes (33,9 %)
  - 2,5 tuiles (1 loco + 4 wagons) : 18 lignes (15,3 %)
  - 3,0 tuiles (1 loco + 5 wagons) : 30 lignes (25,4 %)
  - 4,0 tuiles (1 loco + 7 wagons) : 7 lignes (5,9 %)
  - 4,5 tuiles (1 loco + 8 wagons) : 1 ligne (0,8 %)
  - **Moyenne : 2,38 tuiles.** (Médiane : 2,0 tuiles).

### B. Longueur de quai et marge d'allongement
- **Longueur de quai construite (`platformLength`) :**
  - 3 tuiles : 62 lignes (52,5 %)
  - 4 tuiles : 48 lignes (40,7 %)
  - 5 tuiles : 7 lignes (5,9 %)
  - 6 tuiles : 1 ligne (0,8 %)
  - **Moyenne : 3,55 tuiles.** (Médiane : 3,0 tuiles).
- **Marge d'infrastructure :**
  En application de `RAIL_PLATFORM_GROWTH_WAGONS = 2` (`catalog.nut:31`), chaque quai est dimensionné pour accueillir la rame initiale plus 2 wagons de marge :
  - Sur un quai de 3 tuiles (capacité maximale 5 wagons + 1 loco), la rame en compte 2 ou 3 (marge disponible : 2 à 3 wagons, soit 80 à 120 places).
  - Sur un quai de 4 tuiles (capacité maximale 7 wagons + 1 loco), la rame en compte 4 ou 5 (marge disponible : 2 à 3 wagons).
  - **Pourtant, aucun wagon n'est jamais ajouté en cours de partie.**

### C. Nombre de trains par ligne (télémétrie fin 1972)
- 1 train : 86 lignes (74,1 %)
- 2 trains : 30 lignes (25,9 %)
- 3 trains ou plus : **0 ligne (0,0 %)**
- **Moyenne : 1,26 train par ligne.** (Médiane : 1).

---

## 3. Attente aux gares (télémétrie de ligne fin 1972)

La télémétrie de `v275_expo_railseul_10x3_20261019.json` consigne pour chaque gare d'extrémité (`endpoint_cargo_stats`) la note de gare et l'attente maximale enregistrée (`max_waiting_cargo`) :
- **Attente moyenne de voyageurs par extrémité de gare :** 234,5 passagers (médiane : 177, min : 0, max : 1 461 passagers).
- **Attente maximale sur la ligne (pire des deux gares) :** moyenne = 342,6 passagers, médiane = 293 passagers.
- **Ratio attente maximale / capacité d'une rame :**
  - Moyenne : **5,0×** la capacité d'une rame (médiane : 2,93×).
  - **105 lignes sur 116 (90,5 %)** ont une attente maximale strictement supérieure à la capacité totale d'une rame pleine.
  - Sur plus de la moitié des lignes, l'attente dépasse le double de la rame (ratio médian 2,93×) ; elle atteint jusqu'à 36,5× la capacité de la rame sur les plus fortes saturations (ex. 1 461 passagers en attente pour une rame de 40 places).

---

## 4. Comparaison avec AAAHogEx

### A. À l'horizon 3 ans (campagne 10×3 `v275m7`)
| Grandeur | OpexAI (v275m7) | AAAHogEx | Écart |
|---|---|---|---|
| Lignes voyageurs actives (1972) | 116 (11,6 / graine) | 43 (4,3 / graine) | OpexAI +170 % en nombre de lignes |
| Trains par commande (`BuildTrain`) | 1,00 fixe à la pose | 3,03 en moyenne (jusqu'à 19) | AAA ×3,0 |
| Trains par ligne active (1972) | 1,26 (max 2) | 1,58 (max 7) | AAA +25 % (jusqu'à 7 trains/ligne) |
| Wagons par rame | 3,75 en moyenne | 8,39 en moyenne (jusqu'à 13) | AAA ×2,2 |
| Longueur physique de rame | 2,38 tuiles | 4,69 tuiles (jusqu'à 7,0) | AAA ×2,0 |
| Places assises par train | **88,5 places** (médiane 80) | **207,2 places** (médiane 200) | AAA ×2,3 |
| Sacs de courrier par train | 46,3 sacs | 96,3 sacs | AAA ×2,1 |
| Capacité voyageurs par ligne | 111,4 places | 331,2 places (jusqu'à 1 680) | AAA ×3,0 |
| Longueur de quai prédominante | 3 tuiles (52,5 %), 4 tuiles (40,7 %) | 7 tuiles (57,5 %), 4-6 tuiles (42,5 %) | AAA dimensionne à 7 dès la pose |
| Attente moyenne aux gares | **234,5 passagers** | **58,8 passagers** | OpexAI ×4,0 de saturation |
| Lignes avec attente > 1 rame | **90,5 %** (105 / 116) | **14,0 %** (6 / 43) | AAA évacue la demande |

### B. À l'horizon 10 ans (campagne 20×10 `v275_railseul_porteB_20x10_vps_20261019`)
- **480 commandes `BuildTrain` voyageurs analysées chez AAA :**
  - Multiplicateur de trains par commande : moyenne = 4,40 trains (jusqu'à 33 trains sur une seule ligne).
  - Capacité par train : moyenne = 184,5 places voyageurs (fréquemment 200, 240, 320 places) + 94,4 sacs de courrier.
  - Wagons par rame : moyenne = 7,74 wagons (jusqu'à 13 wagons).
  - Longueur de rame : moyenne = 4,37 tuiles (64 rames à la longueur maximale de 7,0 tuiles).
- **Bilan économique à 10 ans :**
  - Profit annuel OpexAI : **1 330 750 £/an** (29,95 trains en référence → 36,4 trains sous V275).
  - Profit annuel AAAHogEx : **5 282 000 £/an** (87,3 trains en moyenne).
  - Ratio OpexAI / AAAHogEx : **25,2 %** (l'écart reste de **×4**).

---

## 5. Ce qui empêche aujourd'hui une rame plus longue

Quatre verrous cumulatifs expliquent pourquoi les rames d'OpexAI restent bloquées à 40–80 places :

### 1. Sous-estimation du flux lors du dimensionnement initial (`economy.nut:233-237`)
```squirrel
local calibrationOffered = (monthlyUnits * STATION_RATING_PCT) / 100.0;
local wagons = OpexCeilDiv(calibrationOffered, wagon.capacity * referenceTrips);
```
- `monthlyUnits` est calculé dans `candidates.nut:1046` comme `(prodA + prodB) * 40 / 100` (`V207_RAIL_PAX_SHARE_PCT = 40`).
- `STATION_RATING_PCT = 50`.
- Dès lors, `calibrationOffered = (prodA + prodB) * 0,20` (seulement 20 % de la production des deux villes).
- Divisé par `wagon.capacity (40) * referenceTrips (~2,5 trajets/mois)` = 100 passagers/mois par wagon.
- Une paire de villes générant 500 passagers/mois se voit attribuer `calibrationOffered = 100`, soit **1 seul wagon** (40 places).
- Une paire de 1 000 passagers/mois reçoit **2 wagons** (80 places).
- Le modèle suppose que les voyageurs attendent docilement leur tour et ne s'accumulent pas entre deux passages de train.

### 2. Dimensionnement étroit du quai à la pose (`economy.nut:328-330`)
```squirrel
local platformLength = fixedPlatformLength > 0
    ? fixedPlatformLength
    : OpexRailWantedPlatformLength(wagons + wagons2, catalog.platformLength);
```
- `OpexRailWantedPlatformLength` calcule `(targetWagons + 2 + 2) / 2`.
- Pour 1 wagon pax + 1 wagon courrier (2 wagons) : quai = **3 tuiles**.
- Pour 2 wagons pax + 1 wagon courrier (3 wagons) : quai = **3 tuiles**.
- Pour 3 wagons pax + 1 wagon courrier (4 wagons) : quai = **4 tuiles**.
- Les gares sont donc physiquement construites à **3 ou 4 tuiles** (moyenne 3,55 tuiles), alors que le moteur de jeu autorise `vehicle.max_train_length = 7` tuiles (13 wagons).
- Un quai de 3 tuiles ne peut physiquement jamais accueillir plus de 5 wagons (1 motrice + 5 wagons).

### 3. Absence totale d'allongement dynamique en cours de partie
- **Suppression historique de `rail_expand` (`task_rail.nut:383`) :** le commentaire acte que « L'expansion de wagons (rail_expand) a été figée à 0 et retirée ». Aucune tâche périodique n'ajoute de wagon aux rames existantes.
- **Exclusion catégorique des rames voyageurs par V257 (`task_v257.nut:238`) :**
  ```squirrel
  /* Les compositions mixtes ont d'autres contrats de refit : ne pas les demolir. */
  if ((("wagons2" in line) && line.wagons2 > 0) || this._railExpansion != null) return;
  ```
  Toutes les lignes voyageurs posées avec V207/V275 comportent des wagons de courrier (`wagons2 > 0`). En conséquence, `_v257Review` **rejette immédiatement et sans exception toutes les lignes voyageurs**.
  Dans les journaux des 10 graines de 10×3, **exactement 0 ligne voyageur** n'a jamais été revue ou retouchée par V257.

### 4. Capacité de traction des locomotives
Ce n'est **pas** la locomotive qui empêche des rames plus longues :
- En 1970, OpexAI utilise les motrices diesel standard (UU '37', Floss '47').
- Chez AAAHogEx, la même UU '37' tracte en routine des rames de 8 à 13 wagons (240 à 320 passagers + 90 à 120 sacs de courrier) à 114–122 km/h.
- La puissance et l'effort de traction sont amplement suffisants pour tirer des rames de 6 à 8 wagons sur nos lignes.

---

## 6. Ce qui empêche un 2e train sur la ligne (renforts)

### A. Conditions exigées par le code (`task_rail.nut:411-435`)
Sur une ligne à voie unique (le cas de 100 % des lignes à la pose), ajouter un second train impose :
1. Un seuil de congestion : `waiting >= 4 * wagon.capacity` (160 passagers en attente).
2. La trésorerie intégrale pour dédoubler toute l'infrastructure :
   `need = trackCost + trainCost + OpexCashReserve()`, soit entre **60 000 et 100 000 £**.
   Pendant les premières années, la trésorerie disponible est prioritairement consommée par la pose de nouvelles lignes (portefeuille C75).
3. La réussite du dédoublement physique (`OpexPrepareUpgradeSearch` puis A*) :
   - Trouver une tuile de quai adjacent parallèle disponible dans les deux villes (`planA2`, `planB2`).
   - Trouver un tracé de seconde voie complet entre les deux sorties de gare.
4. Dans les villes où la population et les bâtiments se développent autour de la gare, l'espace pour une seconde plateforme adjacente est souvent occupé (`STATIONFAIL` ou `NOPATH`).

### B. Rejets observés dans les journaux (10×3 `v275m7`)
- Sur 118 lignes voyageurs posées, seules **42 tentatives** de dédoublement ont été engagées :
  - `double_track:OK` : 31
  - `double_track:NOPATH` : 5 (échec du pathfinder pour trouver la voie parallèle)
  - `double_track:TRACKFAIL` : 2 (échec lors de la pose des rails)
  - `double_track:STATIONFAIL` : 2 (impossible de poser le second quai adjacent)
  - `double_track:TRAINFAIL` : 1 (erreur lors de l'achat du train)
  - `double_track:OVERLAP` : 1 (conflit d'emprise)
- **73,7 % des lignes voyageurs (87 / 118) n'ont jamais tenté le moindre dédoublement.**

### C. Le plafond absolu de 2 trains (`task_rail.nut:400`)
```squirrel
if (!OpexV190Active() || line.kind != "freight") {
  if (line.trains >= 2 || line.vehicles.len() >= 2) continue;
}
```
- Pour les lignes voyageurs, **le code interdit formellement de dépasser 2 trains**.
- Même lorsqu'une ligne a été dédoublée avec succès (`line.trains == 2`), elle ne peut **jamais** recevoir un 3e train (seul le fret sous V190 dispose d'une clause de clonage supplémentaire).
- En conséquence, une ligne dédoublée reste plafonnée à 2 rames de 80 places = 160 places au total, face à une attente qui dépasse couramment 300 à 600 passagers.

---

## 7. Synthèse et leviers actionnables pour V285

| Problème identifié | Cause dans le code | Levier possible |
|---|---|---|
| Quais trop courts (3–4 tuiles) | `OpexRailWantedPlatformLength` calibré sur 2 wagons | **Levier 1 :** Quai dimensionné à `catalog.maxTrainLength` (7 tuiles) dès la pose pour `kind == "pax"`. |
| Rames courtes figées à vie (40–80 pl.) | `rail_expand` supprimé ; V257 exclut `wagons2 > 0` | **Levier 2 :** Allongement progressif des rames voyageurs (ajout d'un wagon jusqu'au quai via `_continueRailExpansion` quand `waiting >= train_capacity`). |
| Combinaison quai long + rames évolutives | Effet multiplicateur des deux leviers | **Levier 3 :** Quai 7 tuiles dès la pose (1) + allongement jusqu'au quai quand l'attente déborde (2). |
| Plafond de trains (1 train sur 74 % des lignes, max 2) | Dédoublement lourd et coûteux, interdiction > 2 trains | Révision des conditions de renfort ou déverrouillage du 2e/3e train sur voie double. |

Le levier le plus économique et direct consiste à **permettre l'allongement des rames voyageurs** (Levier 2) combiné ou non à un **quai dimensionné à 7 tuiles dès la pose** (Levier 1), ce qui exploite immédiatement la marge des quais existants (2 à 3 wagons disponibles) et ouvre la possibilité d'atteindre 8 à 10 wagons sur les quais neufs sans dépendre d'un dédoublement d'infrastructure complexe.
