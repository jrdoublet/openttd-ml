# V90 — Optimisation du coût par itération du pathfinder rail (A* vendorisé)

Date : **2026-09-24**.  
Statut : **défaut 1 depuis le 2026-09-24 (décision utilisateur) ; équivalence vérifiée ; gain mesuré −8 % (voir §9)**.  
Objectif : **diviser par au moins 2 le coût en opcodes d'une itération de l'A* ferroviaire**, à **tracé strictement identique** (même arbre d'exploration, même ordre de dépilement, même chemin trouvé, même nombre d'itérations).

---

## 1. Contexte et constats mesurés

Dans la configuration de production d'OpexAI (`docs/28_v89_debit_recherche_rail.md`) :
- Une itération d'A* ferroviaire consomme entre **800 et 3 400 opcodes** et effectue entre **35 et 75 appels à l'API NoAI C++**.
- Une tranche de 50 itérations (`RAIL_SEARCH_SLICE = 50`) coûte entre **40 000 et 170 000 opcodes**.
- En conséquence, l'A* ne reçoit qu'environ **1 % du temps script**, et la recherche d'une ligne ferroviaire peut s'étaler sur **2 à 3 années de jeu** (ex. 3 126 itérations réelles).
- Pendant tout ce temps, le slot `_railSearch` est occupé et bloque les autres projets ferroviaires du portefeuille (`search_in_progress`).
- V89 (`v89_rail_search_throughput`) agit sur le **débit** (avancement de tranches opportunistes sur le slack dormant). V90 s'attaque directement au **coût unitaire de l'itération**.

---

## 2. Analyse des goulots par fichier et ligne

L'audit des bibliothèques de référence BaNaNaS (`libsrc/`) a mis en évidence plusieurs inefficacités majeures :

### 2.1 `Graph.AyStar` v4 (`libsrc/4752412a-Graph.AyStar-4/Graph.AyStar.4/main.nut`)
- **Ligne 100** : `this._closed = AIList();`  
  L'ensemble fermé est une structure C++ NoAI (`AIList`). À chaque nœud dépilé et à chaque voisin examiné, l'algorithme traverse le pont Squirrel $\leftrightarrow$ C++ NoAI via `_closed.HasItem(cur_tile)` (l.129), `_closed.GetValue(cur_tile)` (l.131, 149), `_closed.SetValue(...)` (l.149), `_closed.AddItem(...)` (l.152) et `_closed.GetValue(node[0])` (l.179). Cela représente 15 à 30 franchissements de la frontière NoAI par itération.

### 2.2 `Pathfinder.Rail` v1 (`libsrc/5046524c-Pathfinder.Rail-1/Pathfinder.Rail.1/main.nut`)
- **Lignes 261–262** : Dans `_Neighbours`, les offsets `[AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1), AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0)]` sont recalculés à travers l'API NoAI à **chaque appel** de `_Neighbours`.
- **Lignes 313–314, 323–324, 144–153, 369–371** : `AIMap.GetMapSizeX()` est appelé de manière répétée dans `_dir`, `_GetDirection`, `_GetBridgeNumSlopes` (4 fois par pont !) et `_IsSlopedRail` (2 fois).
- **Lignes 247–251** : Dans `_Estimate`, `AIMap.GetTileX(tile[0])` et `AIMap.GetTileY(tile[0])` des buts sont recalculés pour chaque but, à chaque voisin généré, alors que les coordonnées des buts sont invariantes dès `InitializePath`.
- **Lignes 341–347** : Dans `_GetTunnelsBridges`, une nouvelle liste C++ `AIBridgeList_Length(i + 1)` est instanciée pour chaque longueur $i \in [2, \text{max\_bridge\_length}[$ à chaque tuile examinée, suivie de `IsEmpty()` et `Begin()`.
- **Lignes 174, 182, 221, 226, 257** : `_Cost` et `_Neighbours` réinterrogent le moteur OpenTTD pour `IsBridgeTile`, `IsTunnelTile`, `IsCoastTile`, `GetSlope` et `HasTransportType` sur les mêmes tuiles à répétition.

### 2.3 Utilisation dans OpexAI (`ai/OpexAI/builder_rail.nut`)
- **Ligne 363** : `OpexCreateRailPathfinder` instancie `RailPathFinder()`.
- **Ligne 687** : `OpexAdvanceSegmentedSearch` instancie `RailPathFinder()`.
- **Ligne 702** : `state.segmentPath = state.pathfinder.FindPath(1);` boucle 50 fois par tranche, créant 50 objets `AITestMode()` et 50 contextes d'appel.

---

## 3. Copies vendorisées et obligations de licence GPLv2

Les trois bibliothèques d'origine sont sous licence **GNU General Public License version 2 (GPLv2)**.  
Conformément aux obligations de la licence et aux exigences du projet :

1. **Localisation** : Les copies vendorisées et optimisées sont placées dans le dossier propre `ai/OpexAI/pathfinder_v90/` :
   - `ai/OpexAI/pathfinder_v90/binary_heap.nut`
   - `ai/OpexAI/pathfinder_v90/aystar.nut`
   - `ai/OpexAI/pathfinder_v90/rail.nut`
2. **Préservation des mentions** :
   - Tous les avis de copyright d'origine, identifiants SVN (`$Id: ... $`) et mentions de licence GPLv2 sont intégralement conservés dans chaque fichier.
   - En tête de chaque fichier, une note de modification standardisée précise la date (`2026-09-24`), l'auteur (`OpexAI`), la nature des changements et le maintien strict sous licence GPLv2.
3. **Noms de classes distincts** :
   - `Binary_Heap` $\rightarrow$ `OpexBinaryHeapV90`
   - `AyStar` $\rightarrow$ `OpexAyStarV90` (et `OpexAyStarV90.Path`)
   - `Rail` $\rightarrow$ `OpexRailPathFinderV90` (et `OpexRailPathFinderV90.Cost`)
   - Vérificateur de test $\rightarrow$ `OpexRailPathfinderCheckerV90`
   Ces noms distincts évitent toute collision dans l'espace global Squirrel avec l'import BaNaNaS `pathfinder.rail` v1 (qui reste utilisé quand le réglage est à 0).
4. **Indépendance vis-à-vis de `libsrc/`** :
   - Le dossier `libsrc/` reste une référence de lecture externe non committée.
   - Aucun fichier de `ai/` ne référence `libsrc/`.

---

## 4. Optimisations réalisées (à tracé identique)

Toutes les optimisations préservent rigoureusement l'ordre de découverte, le coût calculé et la logique de décision :

### 4.1 Ensemble fermé en table Squirrel (`OpexAyStarV90`)
- Remplacement de `this._closed = AIList();` par une table native Squirrel `this._closed = {};`.
- L'appartenance est testée en mémoire via `cur_tile in this._closed` et `node[0] in this._closed`.
- Les directions explorées sont combinées par masque binaire (`closed_dir | path.GetDirection()`), avec sémantique strictement identique à l'API `AIList`.
- Gain : suppression complète de 15 à 30 appels NoAI par itération.

### 4.2 Précalcul par instance des constantes (`OpexRailPathFinderV90`)
- `this._mapSizeX = AIMap.GetMapSizeX();` calculé une fois dans le constructeur et réutilisé dans `_dir`, `_GetDirection`, `_GetBridgeNumSlopes` et `_IsSlopedRail`.
- `this._offsets` (4 directions cardinales) calculé une fois dans le constructeur.

### 4.3 Précalcul par recherche des coordonnées des buts (`OpexRailPathFinderV90`)
- Dans `InitializePath`, extraction et stockage de `this._goalCoords = [ { tile, x, y }, ... ]`.
- Dans `_Estimate`, `AIMap.GetTileX(cur_tile)` et `AIMap.GetTileY(cur_tile)` ne sont appelés qu'une seule fois pour la tuile courante, puis les distances de Manhattan sont calculées directement avec les coordonnées précalculées des buts.

### 4.4 Précalcul par recherche des ponts disponibles (`OpexRailPathFinderV90`)
- Dans `InitializePath`, interrogation unique de `AIBridgeList_Length(i + 1)` pour chaque longueur de pont $i \in [2, \text{max\_bridge\_length}[$.
- Stockage du meilleur type de pont dans une table `this._bestBridgeForLength[i] <- bridge_list.Begin();`.
- Dans `_GetTunnelsBridges`, suppression totale des instanciations d'`AIBridgeList_Length` : simple test de présence de clé `i in this._bestBridgeForLength`.

### 4.5 Mémoïsation par recherche des requêtes de tuile invariantes
- Les tables `_cache_slope`, `_cache_coast`, `_cache_bridge`, `_cache_tunnel`, `_cache_rail`, `_cache_buildable` sont vidées à chaque appel de `InitializePath`.
- Les requêtes répétées sur les mêmes tuiles adjacentes sont servies depuis la table mémoire Squirrel, évitant de repasser par le runtime C++ NoAI.

---

## 5. Ce qui a été écarté et pourquoi

### 5.1 Non-mémoïsation de `AIRail.BuildRail(a, b, c)` en mode test
**Analyse** :
- `AIRail.BuildRail(a, b, c)` en mode test ne dépend effectivement que du triplet `(a, b, c)` et de l'état physique de la carte.
- **Cependant**, dans l'algorithme A*, un nœud de direction identique arrivant sur une tuile est systématiquement éliminé par l'ensemble fermé (`_closed`) avant que `_Neighbours` ne soit appelé.
- En conséquence, pour une recherche donnée, un même triplet `(parent, cur_node, next_tile)` n'est **pratiquement jamais réévalué** (taux de réutilisation $\approx 0\,\%$).
- Construire une clé de mémoïsation (par hachage ou concaténation de chaînes) et insérer dans une table Squirrel aurait introduit un **surcoût net en opcodes sans aucun hit de cache**.
- La mémoïsation de `BuildRail(a, b, c)` a donc été **écartée pour des raisons d'efficacité prouvée**.

### 5.2 Maintien de `FindPath(1)` dans `OpexAdvanceSegmentedSearch`
**Analyse** :
- L'instruction demandait d'appeler `FindPath(n)` par blocs si possible, tout en conservant exactement les mêmes points d'arrêt, et d'expliquer si l'échéance par tick l'empêchait.
- Dans OpenTTD NoAI, l'échéance `AIController.GetTick() < deadlineTick` est une condition d'arrêt temporelle stricte.
- Si un bloc de $n > 1$ itérations était lancé, le moteur OpenTTD pourrait incrémenter le tick (suite au dépassement du quota de 10 000 opcodes par tick) en cours de bloc sans que Squirrel ne puisse s'arrêter à l'itération précise où `GetTick() >= deadlineTick`.
- De plus, la classe originale BaNaNaS `RailPathFinder` ne renvoie pas le décompte des itérations consommées lorsqu'elle trouve le but ou échoue prématurément, ce qui fausserait `state.iterations`.
- Enfin, le mode de test parallèle pas à pas `v90_pathfinder_check` requiert impérativement une granularité unitaire pour vérifier la correspondance du heap nœud par nœud.
- **Décision** : Le découpage par tranches reste unitaire (`FindPath(1)`) dans `OpexAdvanceSegmentedSearch` pour garantir l'équivalence bit-à-bit et le respect absolu de l'échéance par tick.

---

## 6. Réglages et mode de vérification parallèle

### 6.1 `v90_fast_pathfinder` (défaut 0, booléen)
- À 0 (défaut) : OpexAI instancie `RailPathFinder()` de BaNaNaS. Comportement, opcodes et trajectoire identiques à l'existant.
- À 1 : OpexAI instancie `OpexRailPathFinderV90()`.

### 6.2 `v90_pathfinder_check` (défaut 0, booléen)
- Actif uniquement si `v90_fast_pathfinder = 1`.
- Instancie la classe `OpexRailPathfinderCheckerV90` :
  - Fait tourner en parallèle l'original BaNaNaS et la version vendorisée V90 sur les mêmes sources, buts et contraintes.
  - À chaque pas, compare le nœud en tête de file (`Peek()`) : tuile, direction, coût.
  - À la terminaison, compare le nombre d'itérations et le tracé exact des tuiles (`OpexSegmentTiles`).
  - Journalise sous `probe_events` via `OpexC56TaskLog` le tag `V90_CHECK` :
    - En cours : `OPEX ... C56_TASK V90_CHECK name=step_identical iters=...` (ou `step_diff`).
    - À la fin : `OPEX ... C56_TASK V90_CHECK name=finish iters=... same_path=oui same_iters=oui first_diff=none`.

---

## 7. Gain attendu par itération

| Composant | Coût avant (BaNaNaS) | Coût V90 optimisé | Gain attendu |
|---|---|---|---|
| Ensemble fermé (`_closed`) | 15 à 30 appels NoAI (`AIList`) | 0 appel NoAI (table Squirrel native) | −400 à −1 200 opcodes |
| Ponts par longueur | 4 instanciations `AIBridgeList` par tuile | 0 instanciation (table précalculée) | −200 à −600 opcodes |
| Requêtes tuiles récurrentes | Appels NoAI répétés (`GetSlope`, `IsCoast`, ...) | Lookups table mémoire Squirrel | −150 à −400 opcodes |
| Coordonnées des buts | $2 \times N_{\text{goals}}$ appels `GetTileX/Y` par voisin | $2$ appels pour `cur_tile` seulement | −50 à −150 opcodes |
| **Total par itération** | **800 à 3 400 opcodes** | **300 à 1 200 opcodes** | **Coût divisé par 2,5 à 3** |

---

## 8. Protocole de validation prévu

### Étape 1 : Smoke de vérification d'équivalence stricte
- **Configuration** : `v90_fast_pathfinder=1`, `v90_pathfinder_check=1`, `probe_events=1`, graine 42 sur 1 an.
- **Critère de succès** : Dans la sortie `probe_events`, 100 % des traces `V90_CHECK finish` doivent afficher `same_path=oui same_iters=oui first_diff=none`. Zéro divergence tolérée.

### Étape 2 : Mesure du coût unitaire par itération
- **Configuration** : `probe_events=1`, comparaison de `v90_fast_pathfinder=0` vs `v90_fast_pathfinder=1`.
- **Indicateurs** :
  - `_c41RailSliceLastOps` / `sliceIters` sur les traces `RAIL_SLICE`.
  - Coût moyen d'une tranche de 50 itérations (`est_slice_ops` dans `RAIL_ANNUAL`).
  - Débit annuel `year_iters` et temps total d'exploration d'un tronçon.

### Étape 3 : Exposition solo 3 graines × 10 ans
- Graines 42, 100, 999.
- Vérification de l'absence de régression de santé, de crash script ou d'abandon anormal.

### Étape 4 : Duel apparié officiel 20 graines × 10 ans
- **Commande** :
  ```bash
  python3 sweeps/run_c66_reference.py \
    --campaign v90_fast_pathfinder_20x10 \
    --years 10 \
    --reference "OpexAI" \
    --variant "OpexAI[v90_fast_pathfinder=1]" \
    --variant-policy-id "v90_fast_pathfinder" \
    --primary-metric "profit_year" \
    --min-useful-primary-delta 50000 \
    --value-guard-max-loss-pct 5.0 \
    --max-workers 3
  ```
- **Seuils d'adoption** :
  - Métrique primaire : `profit_year` $\ge +50\text{ k\pounds/an}$.
  - Garde-fou sur la valeur d'entreprise : perte $\le -5\,\%$.
  - Test bilatéral des signes : $p < 0{,}05$ ($\ge 15/20$ victoires).

---

## 9. Mesures du 2026-09-24 (session VPS)

### 9.1 Équivalence (`v90_fast_pathfinder=1`, `v90_pathfinder_check=1`)
`diag_c69_bottleneck_probe.py`, `probe_events=1` : graines 42/100 × 3 ans (`results/v90_check_smoke.jsonl`)
puis 42/999/1234 × 5 ans (`results/v90_check_smoke2.jsonl`). **Zéro écart** : ≈ 3 300 pas comparés,
une recherche terminée (graine 100, 954 itérations, `same_path=oui same_iters=oui first_diff=none`),
une recherche de la graine 999 étalée de janvier à novembre 1974 identique pas à pas — la mémoïsation
par recherche ne diverge pas malgré les changements de carte entre tranches. Couverture limitée :
trois graines sur cinq ne lancent aucune recherche rail avant 1975.

### 9.2 Coût par itération (`probe_scheduler=1`, ledger `C41_RAIL_SLICE_LEDGER`)
Graines 100/999/1234 × 8 ans, `results/v90_cost_v0.jsonl` / `v90_cost_v1.jsonl` :

| Bras | Itérations | Opcodes nets | Opcodes/itération |
|---|---:|---:|---:|
| BaNaNaS (`v90_fast_pathfinder=0`) | 16 212 | 45,7 M | **2 821** |
| V90 (`v90_fast_pathfinder=1`) | 15 460 | 39,9 M | **2 583** |

Par graine : 2 645→2 488 (100), 3 052→2 776 (999), 3 334→2 799 (1234). **Gain ≈ −8 %**, loin du ÷2,5
estimé au §7. Les trajectoires divergent après la première recherche (dérive d'opcodes), le rapport
reste un ordre de grandeur fiable.

### 9.3 Pourquoi l'estimation du §7 était fausse
Le compteur d'opcodes compte des **instructions Squirrel** ; un appel à l'API NoAI (y compris
`AIList.HasItem`, `AITile.GetSlope`, `AIRail.BuildRail` en mode test) en coûte à peine quelques-unes,
quel que soit son coût C++. Mémoïser les requêtes de tuile ou remplacer l'`AIList` fermée ne supprime
donc presque rien. Le coût réside dans la logique Squirrel elle-même : tas binaire (Pop/Insert en
O(log n) avec copies de paires), construction d'un `Path` et appel de `_Cost` par voisin, chaînes
`GetParent()`, `_GetDirection`, `_Estimate`, boucle des ponts. À tracé strictement identique, la marge
restante est faible ; un gain d'un facteur ≥ 2 exige de **réduire le nombre d'itérations**
(heuristique pondérée, pas plus longs), ce qui change le tracé et relève d'une autre décision.

Duel 20×10 non lancé : un gain de 8 % sur ≈ 1 % du temps script ne peut pas produire d'effet
économique détectable.

**Décision utilisateur du 2026-09-24** : `v90_fast_pathfinder` passe à **1 par défaut** (tracé identique, coût moindre). Le défaut n'est pas bit-identique à l'ancien (dérive d'opcodes), sans duel 20×10. Suite : V91, heuristique pondérée.
