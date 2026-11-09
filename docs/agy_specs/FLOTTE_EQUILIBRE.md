# Spécification technique : FLOTTE-EQUILIBRE (Air et Route)

## 1. Objectif et critère de succès chiffré

### Objectif
Équilibrer le dimensionnement des flottes aériennes et routières afin d'éliminer la surcapacité oisive et non rentable sans dégrader le niveau de service ni provoquer de casse de ligne.
Sur les deux modes hors-rail, OpexAI souffre d'un surdimensionnement physique massif de sa flotte par rapport à AAAHogEx :
1. **Sur le mode ROUTE (bus/courrier)** :
   - Sur les 48 paires de villes communes (mesure 40 graines `n_spread2_gateA` du 04/11), OpexAI déploie **8,75 bus par ligne contre 6,81 chez AAAHogEx** (+28,5 % de bus) pour un profit par ligne strictement identique (**39,4 k£/an chez Opex vs 39,7 k£/an chez AAA**).
   - Au total à 3 ans, Opex possède **100,2 bus/graine contre 85,9 chez AAA**, avec un rendement unitaire inférieur (**3 778 £/bus vs 5 509 £/bus**), et **9,2 % des bus d'Opex affichent un profit annuel nul ou négatif** (voir `docs/taches.md` ligne 89).
2. **Sur le mode AIR** :
   - En 1979 (à 10 ans), la flotte gagnante ESTIM-31 compte **84,3 avions contre seulement 48,0 chez AAAHogEx** (+75,6 % d'appareils !), mais génère des recettes annuelles inférieures (**3,578 M£ vs 4,436 M£**, soit un retard de −857 k£/an, cf. `docs/taches.md` ligne 1151).
   - Les renforts V161 continuent d'acheter des avions dès que le modèle marginal prédit un gain infime, sans tenir compte de la saturation des terminaux, des temps d'approche et de la cannibalisation intra-hub.

### Critères de succès chiffrés
- **Économie de CAPEX et OPEX** :
  - Route : réduction de 1,5 à 2 bus par ligne saturée sur les liaisons mûres sans baisse de la demande transportée (gain net attendu : **+25 à +40 k£/an** de caisse préservée et de maintenance évitée).
  - Air : plafonnement des renforts marginaux à faible rendement pour éviter l'explosion de la flotte au-delà de 55-60 appareils à 10 ans (économie de 20+ appareils à ~30-50 k£ d'amortissement et maintenance annuelle par unité).
- **Garde de non-régression** :
  - Zéro baisse de `profit_year` sur les lignes mûres.
  - Zéro dégradation du ratio de desserte de captage.
  - Porte A (40×3) : gain relatif ≥ 4 % (`gain_short`), Wilcoxon p < 0,05, IC95 bootstrap bas > 0, garde de valeur −5 %.
  - Porte B (20×10) : non-érosion confirmée (`non_erosion`, IC95 bootstrap haut ≥ 0, garde de valeur −5 %).

---

## 2. État du code existant (fichier:ligne vérifiés dans le worktree)

### 2.1 Flotte routière (Bus et Courrier)
1. **Évaluation et renfort des lignes de bus standard** :
   - [`ai/OpexAI/task_road.nut:1370-1415`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/task_road.nut#L1370-L1415) : `OpexAI::_resizeRoadFleets` : boucle d'inspection des lignes routières, détection de `needsRefleet`, calcul de `target` et appel de renfort via `OpexRoadRefleet`.
   - [`ai/OpexAI/bus_districts_overrides.nut:2075-2115`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/bus_districts_overrides.nut#L2075-L2115) : variante active sous district bus ROAD1Y.
   - [`ai/OpexAI/builder_road.nut:6440-6475`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/builder_road.nut#L6440-L6475) : `function OpexRoadRefleet(catalog, line, have, target)` : instancie les véhicules manquants par `AIVehicle.CloneVehicle` jusqu'à atteindre `target`.
2. **Réallocation des bus sous ROAD1Y_WEAK** :
   - [`ai/OpexAI/bus_districts.nut:816-925`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/bus_districts.nut#L816-L925) : `OpexRoad1yWeakStep` : transfère les bus des lignes produisant `< ROAD1Y_WEAK * 100` £/bus vers les lignes rentables saturées.
3. **Flotte courrier ROAD1Y_MAIL** :
   - [`ai/OpexAI/bus_districts.nut:458-530`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/bus_districts.nut#L458-L530) : `OpexRoad1yRefleetMailLine` : calcule `want` selon le stock d'attente et `ROAD1Y_GAP` (plafonné à 12 fourgons).

### 2.2 Flotte aérienne (Avions)
1. **Dimensionnement cible initial (C121)** :
   - [`ai/OpexAI/air_catalog_c121.nut:325-327`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/air_catalog_c121.nut#L325-L327) : `line.c121TargetPlanes <- target.planes;` : stocke l'objectif d'appareils calculé lors de la planification de la ligne.
   - [`ai/OpexAI/air_economics_c121.nut:518-535`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/air_economics_c121.nut#L518-L535) : `function OpexC121AirFleetScanCap` : calcul de la capacité flotte par temps de rotation.
2. **Ordonnancement et boucle de renforts périodiques** :
   - [`ai/OpexAI/task_air.nut:515-555`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/task_air.nut#L515-L555) : `function OpexAI::_resizeAirFleets(year, plan = null)` : trie les lignes selon le rendement marginal (`OpexAirFleetSortSelect`) et filtre sur la cadence `AIR_FLEET_CADENCE_DAYS`.
   - [`ai/OpexAI/task_air.nut:615-660`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/task_air.nut#L615-L660) : vérifie `c121BelowTarget` (`line.targetAirPlanes > have`) et autorise l'injection d'un projet de renfort +1.
3. **Exécution du projet de renfort aérien (V161)** :
   - [`ai/OpexAI/task_projects.nut:203-325`](file:///home/deploy/projects/wt-agyeasy/ai/OpexAI/task_projects.nut#L203-L325) : `function OpexAI::_tryBuildFleetProject` : valide le gain marginal pré-achat, vérifie la non-liquidation de la ligne (`!line.scrapping`), puis appelle `OpexAirAddPlane(line, this._catalog, this._lines, locked)`.

---

## 3. Conception proposée

### 3.1 Nouveaux réglages de contrôle de flotte
Afin de calibrer et qualifier indépendamment les deux volets, la conception introduit deux réglages opt-in à **défaut 0** :
1. `flotte_equilibre_road` (plage 0..3, défaut 0) :
   - `0` = Comportement historique inchangé.
   - `1` = Plafonnement dynamique du ratio bus / temps de trajet : limite le nombre de bus par ligne selon `target = min(target, ceil(roundTripDays / headwayMin))`.
   - `2` = Seuil de profitabilité marginale à l'achat : interdit l'ajout d'un bus si le profit moyen par bus de la ligne sur les 12 derniers mois est `< 2 500 £/an`.
   - `3` = Combinaison modes 1 + 2 avec retrait progressif des bus à profit négatif après 2 ans de maturité.
2. `flotte_equilibre_air` (plage 0..2, défaut 0) :
   - `0` = Comportement historique inchangé.
   - `1` = Amortissement marginal complet et pénalité de congestion terminale : exige `ΔP_net > 0` en intégrant une réduction d'efficacité de 8 % par appareil déjà présent sur le même tarmac (aéroports petits ou saturés).
   - `2` = Mode 1 + gel des renforts au-delà de 3 appareils sur aéroport AT_SMALL ou 6 appareils sur aéroport AT_LARGE.

### 3.2 Implantation Squirrel
- **Déclarations dans `globals_pre.nut`** :
  ```squirrel
  FLOTTE_EQUILIBRE_ROAD <- 0;
  FLOTTE_EQUILIBRE_AIR <- 0;
  ```
- **Lecture dans les deux chargeurs de `settings.nut`** :
  ```squirrel
  FLOTTE_EQUILIBRE_ROAD = AIController.GetSetting("flotte_equilibre_road");
  if (FLOTTE_EQUILIBRE_ROAD == null || FLOTTE_EQUILIBRE_ROAD < 0 || FLOTTE_EQUILIBRE_ROAD > 3)
    FLOTTE_EQUILIBRE_ROAD = 0;
  FLOTTE_EQUILIBRE_AIR = AIController.GetSetting("flotte_equilibre_air");
  if (FLOTTE_EQUILIBRE_AIR == null || FLOTTE_EQUILIBRE_AIR < 0 || FLOTTE_EQUILIBRE_AIR > 2)
    FLOTTE_EQUILIBRE_AIR = 0;
  ```
- **Gardes dans `builder_road.nut` et `bus_districts_overrides.nut`** :
  ```squirrel
  if (FLOTTE_EQUILIBRE_ROAD > 0 && ("lineId" in line)) {
    target = OpexRoadEquilibreTarget(line, have, target, FLOTTE_EQUILIBRE_ROAD);
  }
  ```
- **Gardes dans `task_air.nut` et `task_projects.nut`** :
  ```squirrel
  if (FLOTTE_EQUILIBRE_AIR > 0) {
    if (!OpexAirEquilibreCheck(line, have, FLOTTE_EQUILIBRE_AIR)) {
      OpexAirFleetRefusal(line, year, "E"); // E = Equilibre cap
      continue;
    }
  }
  ```

### 3.3 Persistance et Save/Load
Aucun état volatile n'est introduit : les calculs reposent exclusivement sur les champs existants et déjà persistés de `line` (`vehCount`, `vehicles`, `lastProfit`, `year`, `targetAirPlanes`, etc.) répertoriés dans `ai/OpexAI/persist.nut`. Compatibilité bidirectionnelle Save/Load immédiate.

---

## 4. Pièges connus et essais négatifs antérieurs

1. **Échec de l'import monolithique de la flotte AAA (`road1y_aaa_fleet=1`, commit `10d3a6c1`)** :
   - Tentative : importer en bloc le code de flotte d'AAA (plafond strict par temps de parcours, ajout conditionné au minimum de deux arrêts, garde de 2 bus arrêtés au dépôt).
   - Résultat au banc : Porte A 40×3 catastrophique à **−22,7 k£/an**, 16V / 24D, valeur de société à **−9,4 %** (`fail_primary_and_value_guard`).
   - Leçon apprise : Les renforts d'OpexAI qualifiés de « sans demande » par AAA génèrent en réalité du cash net substantiel grâce au mécanisme de captage étendu (`spread_stops=2`). Un élagage brutal détruit la valeur. Le contrôle doit être paramétrique, progressif et cibler uniquement les unités démontrées non rentables.
2. **Échec des filtres de stock et rendement courrier (`road1y_mail_min=15`, commit `989a2fa6`)** :
   - Tentative : supprimer les fourgons lorsque l'attente est inférieure à 15 sacs.
   - Résultat : Perte nette de **−45 k£/an** (fourgons 94 → 46) car même un fourgon sous-utilisé à 1,4 k£/an de profit brut contribue positivement au solde global au-dessus de son coût d'amortissement.
3. **Piste `road1y_spread_cap` non validée (`docs/taches.md` ligne 99)** :
   - Vouloir borner prématurément la flotte sous `spread_stops` sans vérifier si la caisse oisive trouve un meilleur réinvestissement ne rapporte rien.

---

## 5. Plan de test

### 5.1 Tests statiques et unitaires hôte
1. `sweeps/test_flotte_equilibre_contracts.py` :
   - Vérifier la déclaration des deux réglages dans `info.nut` aux 4 difficultés (défaut 0).
   - Vérifier la déclaration des deux globales dans `globals_pre.nut`.
   - Vérifier la double lecture dans `settings.nut`.
   - Vérifier que pour les réglages à 0, le code exécuté est strictement identique à l'historique (chemin OFF pur).
2. `sweeps/test_flotte_equilibre_unit.py` :
   - Tester unitaire de `OpexRoadEquilibreTarget` : vérification que les lignes profitables ne sont jamais bridées sous leur seuil rentable.
   - Tester `OpexAirEquilibreCheck` : vérification du blocage spécifique sur aéroports saturés.

### 5.2 Validation comportementale proportionnée (AGENTS.md §4)
1. **Smoke causal (1 graine × 1 an)** :
   - Exécution sous Docker hôte local (10 CPU, 8G RAM) pour valider l'absence d'erreur moteur NoAI et la stabilité du Save/Load.
2. **Porte A — gain court (`gain_short`)** :
   - **40 graines × 3 ans**, 80 duels contre AAAHogEx.
   - Métrique primaire : `profit_year` (Opex candidat − Opex référence).
   - Seuils : Wilcoxon exact bilatéral p < 0,05, borne basse IC95 bootstrap > 0, delta moyen ≥ 4 % du profit terminal de référence, ratio valeur ≥ 95 % (garde −5 %).
3. **Porte B — non-érosion (`non_erosion`)** :
   - **20 graines × 10 ans**, 40 duels.
   - Critère : borne haute IC95 bootstrap ≥ 0, garde de valeur −5 % tenue.

---

## 6. Estimation de difficulté et effet attendu

| Dimension | Estimation | Justification et sources |
|---|---|---|
| **Difficulté d'implémentation** | **Moyenne (2 / 5)** | Code purement décisionnel localisé dans `task_road.nut`, `builder_road.nut` et `task_air.nut`. Aucune modification d'infrastructure, de tracé physique ou de structure de données persistée. |
| **Effet attendu en profit** | **+30 à +60 k£/an** à 3 ans<br>**+80 à +150 k£/an** à 10 ans | Élimination de 9,2 % des bus déficitaires (gain direct d'exploitation ~25 k£/an) et économie de capex sur 15–20 avions superflus à 10 ans sans perte de chiffre d'affaires. |
| **Effet attendu en opcodes** | **+1,5 à +3,0 M opcodes/an** | Moins de véhicules à inspecter mensuellement par `_resizeAirFleets` et `_resizeRoadFleets`, moins de cycles de pathfinding/dépôt. |
| **Sources des données** | `docs/taches.md` (L87–93, L1151), campagne `n_spread2_gateA` du 04/11, audit décennal ESTIM-31 du 30/10 (`estim31_top3_decade_trajectory_20261030.json`). |
