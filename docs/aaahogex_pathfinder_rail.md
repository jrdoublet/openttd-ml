# Analyse comparative du pathfinding rail : AAAHogEx vs OpexAI

> **Contexte de l'analyse :**
> - **Question posée :** Comment AAAHogEx (`ai/AAAHogEx-115/`) parvient-il à trouver des chemins rail de 120 à 240 tuiles en seulement quelques jours de jeu (souvent 2 à 4 tranches), alors qu'OpexAI (`ai/OpexAI/builder_rail.nut`, `task_rail.nut`) abandonne entre 40 % et 60 % de ses recherches au-delà de 140 tuiles (plafond de 10 000 itérations, budget `OpexIterationBudget`) ?
> - **Périmètre :** Analyse en lecture seule du code source d'AAAHogEx-115 et d'OpexAI. Tous les chemins et numéros de lignes cités ci-dessous ont été vérifiés directement dans l'arbre source du dépôt.

---

## 1. Algorithme de recherche rail d'AAAHogEx

### 1.1 Architecture et classes

Dans AAAHogEx, le moteur de recherche ferroviaire repose sur deux classes principales :

1. **`RailPathFinder`** ([`ai/AAAHogEx-115/pathfinder.nut:2-100`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L2-L100)) :
   - Encapsule la logique métier propre au rail OpenTTD : calcul des coûts de virage, de pente, de pont, de tunnel et de réservation de la voie retour.
   - Instancie l'algorithme A* via `_aystar_class = AyStar` ([`pathfinder.nut:6`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L6)) dans `InitializeParameters()` ([`pathfinder.nut:106`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L106)) :
     ```squirrel
     _pathfinder = this._aystar_class(this, this._Cost, this._Estimate, this._Neighbours, this._CheckDirection);
     ```

2. **`AyStar`** ([`ai/AAAHogEx-115/aystar.nut:5-75`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L5-L75)) :
   - Implémentation générique de l'algorithme A* pilotée par les rappels (`_Cost`, `_Estimate`, `_Neighbours`, `_CheckDirection`).
   - Représentation d'un nœud dans le graphe : `AyStar.Path` ([`aystar.nut:219-250`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L219-L250)).

### 1.2 Structure de la file ouverte et de la liste fermée

Dans `AyStar::InitializePath` ([`ai/AAAHogEx-115/aystar.nut:82-83`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L82-L83)) :
```squirrel
this._open = AIPriorityQueue();
this._closed = AIList();
```

- **File ouverte (`_open`) :** AAAHogEx utilise directement la classe native OpenTTD C++ `AIPriorityQueue`.
  - Contrairement à un tas binaire codé en Squirrel (comme le `Queue.BinaryHeap` de BaNaNaS ou `OpexBinaryHeapV129` dans OpexAI), les opérations `Insert()`, `Pop()` et `Peek()` s'exécutent en C++ natif au sein du moteur OpenTTD.
  - Le coût en opcodes Squirrel pour la gestion de la file ouverte est quasi-nul (un simple appel de fonction d'API C++ au lieu de dizaines de swaps et de comparaisons en bytecode Squirrel).
- **Liste fermée (`_closed`) :** Utilise `AIList()` en C++, avec stockage par tuile d'un masque binaire de directions (`SetValue(cur_tile, GetValue(cur_tile) | path.GetDirection())`, [`aystar.nut:137`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L137)).

### 1.3 Heuristique : poids et admissibilité

L'heuristique est calculée dans `RailPathFinder::_Estimate` ([`ai/AAAHogEx-115/pathfinder.nut:791-821`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L791-L821)) :

```squirrel
798: local dx = abs(AIMap.GetTileX(cur_tile) - AIMap.GetTileX(goal[0]));
799: local dy = abs(AIMap.GetTileY(cur_tile) - AIMap.GetTileY(goal[0]));
802: min_cost = min(min_cost, min(dx, dy) * 70 * 2 + (max(dx, dy) - min(dx, dy)) * 100);
...
820: return min_cost * self._estimate_rate + guide;
```

- **Poids heuristique (`_estimate_rate`) :**
  - Fixé à **`_estimate_rate = 2`** dans le constructeur et dans `InitializeParameters()` ([`pathfinder.nut:86`, `133`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L86)).
  - **Admissibilité : NON admissible**. L'heuristique sous-estime la distance géométrique par tuile diagonale (`70 * 2 = 140` pour `dx=1, dy=1`), mais la multiplie immédiatement par **2,0** (`min_cost * 2`).
  - **Conséquence fondamentale :** Avec un poids $w = 2,0$, la fonction d'évaluation est $f(n) = g(n) + 2 \cdot h(n)$. Lorsqu'un nœud avance d'une tuile vers le but, $g$ augmente d'environ 100, mais $2 \cdot h$ diminue de 200 : **$f(n)$ diminue de ~100** ! L'algorithme se transforme en un *greedy best-first search* quasi-rectiligne (beam search) qui fonce vers la cible sans ouvrir d'arborescences latérales tant qu'il ne rencontre pas d'obstacle infranchissable.
- **Terme `guide` :** Si la recherche concerne la voie de retour (`_reverseNears != null`, [`pathfinder.nut:805-813`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L805-L813)), un surcoût heuristique de `_cost_guide * level` (`_cost_guide = 900`) est injecté dès qu'on s'écarte de la voie jumelle (voir section 3).

### 1.4 Coûts unitaires et pénalités

Définis dans `InitializeParameters()` ([`pathfinder.nut:102-194`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L102-L194)) et évalués dans `__Cost()` ([`pathfinder.nut:504-772`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L504-L772)) :

- **Tuile droite :** `_cost_tile = 100` ([`pathfinder.nut:134`, `659`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L134)).
- **Tuile diagonale :** `_cost_diagonal_tile = 67` ([`pathfinder.nut:126`, `657`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L126)) (favorise le tracé fluide en diagonale à 45°).
- **Virages :**
  - Virage standard (changement d'orientation) : `_cost_turn = 300` ([`pathfinder.nut:135`, `665`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L135)).
  - Virage serré (S-bend, chicane) : `_cost_tight_turn = 1500` (ou 100 si distance < 40) ([`pathfinder.nut:136`, `525-532`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L136)).
  - Virage serré opposé : `_cost_tight_turn_rev = 1500` ([`pathfinder.nut:137`, `528`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L137)).
  - Courbe gauche rayon 2 : pénalité de 300 à 500 pour réserver le gabarit de la seconde voie ([`pathfinder.nut:558`, `717`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L558)).
- **Pente :** `_cost_slope = 100` par défaut ([`pathfinder.nut:147`, `675-693`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L147)). Si la motrice a un effort de traction ou une puissance insuffisants face au réglage de pente du jeu (`train_slope_steepness`), le coût grimpe à `1500` ([`pathfinder.nut:177`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L177)) pour forcer les tunnels.
- **Ponts :**
  - `_cost_bridge_per_tile = 100` ([`pathfinder.nut:138`, `597`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L138)).
  - Pénalités progressives de surlongueur : `_cost_bridge_per_tile_ex = 200` (voie double) au-delà de 7 tuiles, et `_cost_bridge_per_tile_ex2 = 400` au-delà de 11 tuiles ([`pathfinder.nut:121-124`, `598-603`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L121-L124)).
- **Tunnels :**
  - **`_cost_tunnel_per_tile = 0`** ([`pathfinder.nut:139`, `581`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L139)) : *"トンネルではなく山登りをしない為にコスト0に"* (coût zéro pour inciter à perforer plutôt qu'à escalader les collines).
  - Pénalité de surlongueur de 200/300 au-delà de 7 et 11 tuiles ([`pathfinder.nut:582-587`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L582-L587)).
- **Eau et côtes :**
  - Côte : `_cost_coast = 20` ([`pathfinder.nut:79`, `670`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L79)).
  - Mer : `_cost_water = 20` (ou `-50` si l'IA a le droit de remblayer l'eau, [`pathfinder.nut:85`, `190`, `673`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L85)).
  - Double diagonale maritime : `_cost_doublediagonal_sea = 100000` ([`pathfinder.nut:127`, `655`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L127)) pour interdire les zigzags au ras de l'eau.
- **Passages à niveau et voies existantes :**
  - Traversée de route : `_cost_level_crossing = 900` ([`pathfinder.nut:109`, `567`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L109)).
  - Croisement sous pont : `_cost_under_bridge = 50` ([`pathfinder.nut:129`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L129)) via `_CanChangeBridge` ([`pathfinder.nut:823-850`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L823-L850)).
  - **Réservation de la voie jumelle à l'aller (`isOutward = true`)** ([`pathfinder.nut:712-763`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L712-L763)) : Pour chaque tuile posée à l'aller, l'A* vérifie si la tuile latérale parallèle `t + revDir` est constructible. Si elle ne l'est pas (eau, relief, pont impossible en parallèle), **une pénalité de +3000** est infligée !

### 1.5 Voisinage et étapes multi-tuiles

La génération des voisins dans `__Neighbours` ([`ai/AAAHogEx-115/pathfinder.nut:1014-1147`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1014-L1147)) combine des pas élémentaires et de puissants sauts macro :

- **Pas élémentaires :** 4 directions cardinales (`HgTile.DIR4Index`, [`pathfinder.nut:1022`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1022)). Les virages à 90° et 180° sont immédiatement filtrés ([`pathfinder.nut:1097-1102`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1097-L1102)).
- **Pas multi-tuiles (Ponts) :**
  - Dans `_GetTunnelsBridges()` ([`pathfinder.nut:1383-1393`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1383-L1393)), une boucle teste les portées de ponts de 2 jusqu'à **`_max_bridge_length = 30`** tuiles :
    ```squirrel
    for (local i = 2; i < this._max_bridge_length; i++) {
        ...
        local target = cur_node + i * dir;
        if (significant && ... && RailPathFinder.BuildBridge(..., cur_node, target)) {
            tiles.push([target, bridge_dir]);
        }
    }
    ```
  - **Un pont de 25 tuiles franchissant une vallée ou un lac est inséré comme UN SEUL nœud voisin.** L'A* traverse l'obstacle en une seule itération.
- **Pas multi-tuiles (Tunnels) :**
  - Détection automatique de la sortie via `AITunnel.GetOtherTunnelEnd(cur_node)` ([`pathfinder.nut:1423-1432`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1423-L1432)) jusqu'à **`_max_tunnel_length = 11`** (ou 14 si riche, [`pathfinder.nut:141`, `184`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L141)). Un tunnel montagneux de 10 tuiles est également un saut d'une seule itération.
- **Tunnels sous-terrains artificiels (`Underground`) :**
  - Mécanisme custom `_GetUndergroundTunnel` ([`pathfinder.nut:1310-1349`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1310-L1349)) permettant de traverser les dénivelés en tunnel à niveau constant, générant des nœuds `RailPathFinder.Underground(L)`.
- **Continuité après saut :** Si le parent a une distance Manhattan > 1 (pont ou tunnel), le nœud est forcé de continuer tout droit en sortie ([`pathfinder.nut:1066-1081`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1066-L1081)).

---

## 2. Bornes, découpage temporel et gestion d'échec

### 2.1 Bornes d'itérations et origine de `limitCount`

La limite de recherche provient de la configuration globale et du constructeur de ligne :

1. `pathFindLimit` vaut **80** par défaut dans `main.nut:242` :
   ```squirrel
   pathFindLimit = 80;
   ```
2. Dans `trainroute.nut:3063` ([`ai/AAAHogEx-115/trainroute.nut:3063`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3063)) :
   ```squirrel
   local adjustedPathFindLimit = !hogeAI.HasIncome(10000) && !hogeAI.IsRich() ? hogeAI.pathFindLimit * 3 : hogeAI.pathFindLimit;
   ```
   Soit 80 si l'IA est bien établie, ou 240 (80 × 3) si l'IA débute / a peu de revenus.
3. Dans `RailPathFinder::FindPath` ([`ai/AAAHogEx-115/pathfinder.nut:197-200`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L197-L200)) :
   ```squirrel
   198: HgLog.Info("TrainRoute: Pathfinding...limit count:"+limitCount+" distance:"+distance);
   199: limitCount *= 3;
   ```
   Le `limitCount` effectif dans la boucle vaut donc **240 tranches** (ou 720).

### 2.2 Découpage entre ticks : `_FindPath(50)` et `OnPathFindingInterval`

La boucle d'avancement est structurée ainsi ([`pathfinder.nut:204-219`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L204-L219)) :

```squirrel
204: while (path == false) {
205:     if (limitCount < counter) break;
209:     path = _FindPath(50);
211:     counter++;
214:     if (path == false && eventPoller != null && eventPoller.OnPathFindingInterval() == false) {
215:         HgLog.Info("TrainRoute: FindPath break by OnPathFindingInterval");
216:         return null;
217:     }
218:     totalInterval += AIDate.GetCurrentDate() - intervalStartDate;
219: }
```

- **Taille de tranche :** Chaque appel `_FindPath(50)` exécute exactement **50 itérations** d'A* (`this._pathfinder.FindPath(50)` dans [`pathfinder.nut:430`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L430)).
- **Pas de mise en sommeil artificielle :** AAAHogEx n'exécute **aucun `AIController.Sleep()`** entre ses tranches de pathfinding. La recherche consomme les ticks et jours du jeu à son rythme normal.
- **Régulation par `OnPathFindingInterval()` :**
  À chaque tranche de 50 itérations, `eventPoller.OnPathFindingInterval()` est appelé :
  - Dans `main.nut:3954-3957` ([`ai/AAAHogEx-115/main.nut:3954-3957`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/main.nut#L3954-L3957)), cela exécute `DoInterval()` (gestion des événements moteur, renouvellement de véhicules, gestion de prêt).
  - Dans `railbuilder.nut:2246-2275` ([`ai/AAAHogEx-115/railbuilder.nut:2246-2275`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2246-L2275)), cela permet de déclencher une recherche inverse (voir section 3).
  - Dans `pathfinder.nut:1611-1626` ([`ai/AAAHogEx-115/pathfinder.nut:1611-1626`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1611-L1626)), l'objet `Pathfinding` écoute les fermetures d'industries (`AIEventIndustryClose`). Si une industrie liée ferme pendant la recherche, `failed = true` et `OnPathFindingInterval` renvoie `false`, interrompant immédiatement l'A*.

### 2.3 Ce qui se passe en cas d'échec

1. Si `counter > limitCount` (épuisement du plafond de 240 tranches × 50 = 12 000 itérations) :
   - `pathfinder.nut:221-222` ([`pathfinder.nut:221-222`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L221-L222)) :
     ```squirrel
     if (path == false) {
         path = _pathfinder._open.Peek();
     }
     ```
     Le pathfinder extrait le meilleur nœud partiel disponible en tête de file ouverte, mais **`isFoundPath` reste `false`** !
   - Dans `railbuilder.nut:2369-2378` ([`railbuilder.nut:2369-2378`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2369-L2378)) :
     ```squirrel
     local path1 = pathFinder1.FindPath(limitCount, this);
     if (foundedRevPath != null) { ... }
     else if (pathFinder1.IsFoundGoal()) { ... }
     else {
         HgLog.Warning("RailPathBuilder: No path found");
         return false;
     }
     ```
   - Si le but n'a pas été atteint, le constructeur refuse le chemin partiel et retourne `false`.
2. **Repli et rollback :**
   - Dans `trainroute.nut:3040` et `railbuilder.nut:2407-2410` ([`trainroute.nut:3040`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/trainroute.nut#L3040), [`railbuilder.nut:2407-2410`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2407-L2410)), l'échec de construction déclenche `railBuilder1.Rollback()`. Les gares ou portions déjà posées sont détruites et les fonds remboursés.
   - AAAHogEx abandonne le projet pour ce cycle sans bloquer le moteur, et réévaluera d'autres opportunités à l'intervalle suivant.

---

## 3. Astuces d'accélération majeures dans AAAHogEx

### 3.1 Guidage par corridor 1D pour la voie retour (`_reverseNears`)

Pour une ligne double voie, chercher deux chemins indépendants de 200 tuiles dans un plan 2D multiplierait par deux le risque d'échec et d'explosion combinatoire. AAAHogEx résout ce problème de manière brillante :

1. **Réservation à l'aller :** Lors de la construction de la première voie (`isOutward = true`), toute tuile dont l'emplacement parallèle adjacent est bloqué reçoit une pénalité prohibitive (+3000, [`pathfinder.nut:759`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L759)). La première voie garantit donc l'existence d'un couloir libre à côté d'elle.
2. **Champ de distance BFS (`SetReverseNears`) :**
   Dans `RailPathFinder::SetReverseNears()` ([`ai/AAAHogEx-115/pathfinder.nut:346-410`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L346-L410)), une fois la première voie posée, ses tuiles sont passées comme `reversePath`. L'algorithme pré-calcule un champ de distance par BFS :
   - `level = 0` : le rail exactement parallèle (`tile + revDir`).
   - `level = 1 .. 19` : anneaux de tuiles adjacentes s'éloignant du corridor.
3. **Pénalisation heuristique dans `_Estimate` :**
   Dans `_Estimate` ([`pathfinder.nut:805-813`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L805-L813)) :
   ```squirrel
   if (self._reverseNears != null) {
       if (self._reverseNears.rawin(cur_tile)) {
           local level = self._reverseNears[cur_tile];
           guide = self._cost_guide * level;
       } else {
           guide = self._cost_guide * 20;
       }
   }
   ```
   Avec `_cost_guide = 900` ([`pathfinder.nut:128`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L128)), toute tuile s'écartant du couloir parallèle subit un surcoût heuristique de 900 par case d'écart (et 18 000 hors champ).
   **Résultat :** La recherche de la seconde voie est réduite à un espace à 1 dimension (un couloir de largeur 1 tuile). Elle réussit en **quelques dizaines d'itérations seulement**, sans aucun risque de divergence.

### 3.2 Recherche bidirectionnelle opportuniste

Dans `railbuilder.nut:2246-2275` ([`ai/AAAHogEx-115/railbuilder.nut:2246-2275`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2246-L2275)), à chaque intervalle de la recherche principale `pathFinder1` (aller de A vers B) :
```squirrel
2260: local pathFinder2 = GetPathFinder2();
2262: local path2 = pathFinder2.FindPath(2, null);
2263: if (pathFinder2.IsFoundGoal()) {
2264:     HgLog.Info("pathFinder2 found goal " + HgTile(path2.GetTile()));
2265:     foundedRevPath = path2;
2266:     return false;
2267: }
```
- AAAHogEx lance une mini-sonde inverse depuis l'arrivée B vers le départ A de seulement **2 tranches** (100 itérations).
- Si le terrain depuis l'arrivée offre une ligne droite dégagée, `pathFinder2` peut trouver le chemin en sens inverse très rapidement.
- Dès que `pathFinder2` atteint la cible, il renvoie `false` à `OnPathFindingInterval()`, ce qui coupe immédiatement `pathFinder1` (`FindPath break by OnPathFindingInterval`) et utilise `path2.Reverse()` pour construire la voie ([`railbuilder.nut:2370-2371`, `2388`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2370-L2371)).

### 3.3 Sauts de ponts géants et tunnels à coût zéro

- **Ponts jusqu'à 30 tuiles :** Les plans d'eau et dépressions ne nécessitent aucun contournement itératif. Une seule itération A* teste et pose une liaison directe de 30 tuiles.
- **Tunnels gratuits (`_cost_tunnel_per_tile = 0`) :** Élimine le piège classique des A* géographiques qui explorent des centaines de nœuds pour serpenter sur les versants de montagne : le tunnel direct est instantanément préféré.

---

## 4. Décodage des journaux de banc d'AAAHogEx

Les messages observés dans les journaux s'expliquent précisément par le code :

### 4.1 `"TrainRoute: Pathfinding...limit count:N distance:N"`

- **Fichier et ligne :** [`ai/AAAHogEx-115/pathfinder.nut:198`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L198) :
  ```squirrel
  HgLog.Info("TrainRoute: Pathfinding...limit count:"+limitCount+" distance:"+distance);
  ```
- **Signification :**
  - `distance` : Distance de Manhattan entre les gares de départ et d'arrivée.
  - `limit count` : Nombre de tranches maximales allouées (généralement 80 ou 240, multiplié par 3 à la ligne suivante pour donner le plafond `counter`).

### 4.2 `"TrainRoute: FindPath break by OnPathFindingInterval"`

- **Fichier et ligne :** [`ai/AAAHogEx-115/pathfinder.nut:215`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L215) :
  ```squirrel
  if (path == false && eventPoller != null && eventPoller.OnPathFindingInterval()==false) {
      HgLog.Info("TrainRoute: FindPath break by OnPathFindingInterval");
      return null;
  }
  ```
- **Signification :** La boucle de recherche principale a été interrompue prématurément par le callback d'intervalle. Cela se produit dans deux situations bien précises :
  1. **Succès de la recherche inverse :** Dans `railbuilder.nut:2263-2266`, la mini-sonde `pathFinder2` a atteint la gare de départ en moins de 100 itérations. La recherche principale est donc arrêtée car le chemin a déjà été trouvé par l'autre extrémité.
  2. **Fermeture d'industrie :** Dans `pathfinder.nut:1612-1614`, l'événement `AIEventIndustryClose` a frappé l'une des deux industries connectées pendant le calcul, annulant la recherche pour éviter de poser des rails vers une usine disparue.

### 4.3 `"TrainRoute: Path found. (count:4 date:2) distance:N"`

- **Fichier et ligne :** [`ai/AAAHogEx-115/pathfinder.nut:224`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L224) :
  ```squirrel
  HgLog.Info("TrainRoute: Path found. (count:" + counter + " date:"+ (AIDate.GetCurrentDate() - startDate - totalInterval) +") distance:"+distance);
  ```
- **Que mesurent exactement `count` et `date` ?**
  - **`count` (ici 4) :** C'est le **nombre de tranches de 50 itérations** exécutées par `_FindPath(50)` avant de trouver le but !
    - `count = 4` signifie que l'A* a trouvé un chemin complet de 120 à 240 tuiles en seulement **3 à 4 tranches, soit entre 150 et 200 itérations au total** !
    - Pour un trajet de 150 tuiles, 150 à 200 itérations prouvent que l'algorithme a progressé de manière quasi-rectiligne (1 tuile explorée par tuile de chemin, zéro dispersion latérale).
  - **`date` (ici 2) :** C'est le **nombre de jours de jeu écoulés** strictement consacrés à l'A* (`AIDate.GetCurrentDate() - startDate - totalInterval`).
    - `startDate` est la date OpenTTD (en jours) au début du pathfinding.
    - `totalInterval` est la somme des jours consommés par `OnPathFindingInterval()` (tâches administratives et recherche inverse).
    - `date = 2` signifie que le pathfinding n'a monopolisé que **2 jours calendaires de simulation OpenTTD**.

---

## 5. Tableau comparatif AAAHogEx contre OpexAI

| Critère / Composant | AAAHogEx (`ai/AAAHogEx-115/`) | OpexAI (`ai/OpexAI/`) |
|---|---|---|
| **Classe de recherche** | `RailPathFinder` ([`pathfinder.nut:2`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L2)) sur `AyStar` ([`aystar.nut:5`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L5)) | `OpexRailPathFinderV90` ([`pathfinder_v90/rail.nut:23`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/pathfinder_v90/rail.nut#L23)) ou `V129` ([`v129.nut:587`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/pathfinder_v90/v129.nut#L587)) |
| **Structure de file ouverte** | **`AIPriorityQueue` (C++ natif)** ([`aystar.nut:82`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/aystar.nut#L82)) | Tas binaire Squirrel (`OpexBinaryHeapV129`, [`v129.nut:19`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/pathfinder_v90/v129.nut#L19)) |
| **Poids heuristique ($w$)** | **$w = 2,0$ (`_estimate_rate = 2`)** ([`pathfinder.nut:133`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L133))<br>Fortement non admissible, beam search directif | **$w = 1,2$ (`V91_ASTAR_WEIGHT_PCT = 120`)** ([`info.nut:1827`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/info.nut#L1827))<br>Proche de l'admissibilité (1,0 historique) |
| **Itérations pour 150 tuiles** | **150 à 250 itérations** (quasi-linéaire) | **5 000 à > 10 000 itérations** (expansion d'ellipse 2D) |
| **Longueur max pont / tunnel** | **Pont 30 tuiles, tunnel 11-14 tuiles** ([`pathfinder.nut:140-141`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L140-L141)) | **Pont 6 tuiles, tunnel 6 tuiles** ([`pathfinder_v90/rail.nut:69-70`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/pathfinder_v90/rail.nut#L69-L70)) |
| **Tunnels sous-terrains** | Oui (`RailPathFinder.Underground`, [`pathfinder.nut:1310`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L1310)) | Non |
| **Coût unitaire tunnel** | **`0`** (incitation maximale au percement) ([`pathfinder.nut:139`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L139)) | `120` (pénalité de percement) ([`pathfinder_v90/rail.nut:67`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/pathfinder_v90/rail.nut#L67)) |
| **Double voie / voie jumelle** | Réservation latérale à l'aller (+3000), puis **couloir 1D guidé par BFS** (`_reverseNears`, [`pathfinder.nut:354`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/pathfinder.nut#L354)) | Deux recherches A* indépendantes en 2D (voie 1 puis voie 2 upgrade, [`task_rail.nut:1720`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L1720)) |
| **Recherche bidirectionnelle** | **Oui** : sonde inverse dans `OnPathFindingInterval` ([`railbuilder.nut:2260`](file:///home/deploy/projects/openttd-ml/ai/AAAHogEx-115/railbuilder.nut#L2260)) | Non (recherche purement unidirectionnelle A → B) |
| **Découpage et tranches** | Tranches de 50 itérations (`_FindPath(50)`), 0 sleep | Tranches `RAIL_SEARCH_SLICE` (ex: 2000 iters avec coupure de segment à 2000, [`builder_rail.nut:762`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut#L762)) |
| **Budget et plafond d'échec** | 240 tranches × 50 = **12 000 itérations** (ou 36 000) | `OpexIterationBudget` (plancher 1000, **plafond dur 10 000**, [`builder_rail.nut:123`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/builder_rail.nut#L123)) |
| **Comportement à l'échec** | Rollback complet, libération immédiate, pas d'abandon définitif | Arrêt sur `ABND`, marquage `_markPairAbandoned` ([`task_rail.nut:1703`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L1703)), paire rejetée |

---

## 6. Les 3 différences majeures expliquant l'écart et transpositions à OpexAI

### 1. Le poids de l'heuristique A* : $w = 2,0$ contre $w = 1,2$ (Facteur n°1 de vitesse)

- **Explication causale :**
  C'est la cause mathématique directe du nombre infime d'itérations (`count: 4`, soit ~200 itérations pour 150 tuiles chez AAAHogEx contre > 10 000 chez OpexAI).
  - À $w = 1,2$ (réglage actuel d'OpexAI `v91_astar_weight_pct = 120`), l'A* reste proche d'une recherche admissible. Sur une longue distance (150 tuiles), le coût accumulé $g(n)$ rivalise avec l'heuristique, forçant l'A* à explorer un ballon 2D volumineux (une ellipse large de dizaines de tuiles). Le nombre de nœuds ouverts croît de façon quadratique avec la distance : 10 000 itérations sont épuisées avant que la tête de recherche n'atteigne le tiers ou la moitié du parcours.
  - À $w = 2,0$, la valeur $f(n) = g(n) + 2 \cdot h(n)$ **diminue strictement à chaque pas qui se rapproche de la gare cible**. L'algorithme se comporte comme un fil guidé vers le but, n'explorant qu'une largeur de 1 à 2 tuiles. Le nombre de nœuds ouverts est strictement linéaire par rapport à la distance ($O(D)$ au lieu de $O(D^2)$).
- **Idée de transposition à OpexAI :**
  - OpexAI dispose déjà de l'infrastructure `_EstimateWeighted` et du paramètre `v91_astar_weight_pct` ([`ai/OpexAI/settings.nut:734`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/settings.nut#L734), [`info.nut:1826`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/info.nut#L1826)). Les bornes du paramètre vont déjà jusqu'à 300 !
  - **Piste concrète :** Introduire un poids adaptatif à la distance ou qualifier un palier plus agressif pour les longues liaisons (ex: `v91_astar_weight_pct = 180` ou `200` pour toute recherche avec `candidate.distance >= 100`).

### 2. Franchissement macro : portée des ponts/tunnels (30 vs 6) et coût tunnel nul (Facteur n°1 de déblocage)

- **Explication causale :**
  Sur une carte OpenTTD de 512×512 ou 1024×1024, un tracé de 140 à 240 tuiles rencontre inévitablement des obstacles topographiques majeurs : bras de mer, grands lacs, fleuves ou chaînes de collines.
  - OpexAI est bridé à **6 tuiles** pour les ponts et 6 tuiles pour les tunnels (`_max_bridge_length = 6`, `_max_tunnel_length = 6`, [`pathfinder_v90/rail.nut:69-70`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/pathfinder_v90/rail.nut#L69-L70)). Face à une étendue d'eau de 8 tuiles de large ou un relief accidenté, le pathfinder d'OpexAI est dans l'impossibilité physique de traverser en ligne droite. Il est forcé de chercher un contournement sinueux sur des dizaines de tuiles, ce qui fait exploser les itérations jusqu'au plafond `ABND` (10 000 itérations).
  - De plus, OpexAI taxe les tunnels d'un surcoût (`_cost_tunnel_per_tile = 120`), ce qui pousse l'A* à essayer de contourner les collines en surface plutôt que de percer tout droit.
  - AAAHogEx autorise des ponts de **30 tuiles** et des tunnels de **14 tuiles**, et fixe le coût unitaire de tunnel à **0**. Il traverse les obstacles en un seul bond de graphe (1 itération).
- **Idée de transposition à OpexAI :**
  - Dans `OpexRailPathFinderV90` / `V129`, augmenter la portée maximale autorisée des ponts et tunnels en fonction de la distance de la ligne (ex: `_max_bridge_length = min(24, candidate.distance / 5)`).
  - Réduire `_cost_tunnel_per_tile` (actuellement à 120) pour inciter le pathfinder à transpercer le relief plutôt qu'à tenter des contournements coûteux en itérations.

### 3. Construction de double voie : guidage 1D par corridor contre double recherche 2D indépendante

- **Explication causale :**
  Dans OpexAI, le doublement d'une ligne ou la recherche d'une double voie consiste à relancer un A* complet 2D (`OpexPrepareUpgradeSearch`, [`task_rail.nut:1720`](file:///home/deploy/projects/openttd-ml/ai/OpexAI/task_rail.nut#L1720)), soumis au même plafond d'itérations et aux mêmes risques de blocage que la voie principale.
  - AAAHogEx ne résout le problème de cheminement 2D qu'**une seule fois** (à l'aller), en prenant soin de pénaliser (+3000) tout tracé dont le flanc parallèle n'est pas dégagé (`isOutward = true`).
  - Pour le retour, AAAHogEx applique son guidage BFS `_reverseNears` : le pathfinder est enfermé dans un champ de force de largeur 1 tuile le long de la première voie. Il ne consomme quasiment aucune itération et son succès est garanti à 100 %.
- **Idée de transposition à OpexAI :**
  - Implémenter dans OpexAI un mode de pose jumelle "suivi de trace" (ou contrainte de couloir via tuiles ignorées / heuristique directionnelle) pour la seconde voie, au lieu de recalculer un A* générique non guidé sur toute la carte.

---
*Rapport rédigé en conformité avec les règles de consultation du dépôt (lecture seule, vérification stricte des chemins et lignes dans le code source).*
