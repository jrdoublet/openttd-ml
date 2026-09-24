# V88 — Chaînes industrielles complètes de biens (goods)

Fiche de conception et protocole de qualification pour le chantier **V88**.

---

## 1. Contexte et objectif

Le constat établi dans [docs/26_c87_bus_et_lignes_aaa.md](26_c87_bus_et_lignes_aaa.md) §2-§3 montre un déséquilibre massif sur le fret ferroviaire :
- **AAAHogEx** dégage ≈ 570 k£/an en fret rail (sur 150 à 270 tuiles), notamment par des chaînes industrielles de biens (*goods*) et des trains de céréales/bétail/acier approvisionnant des usines, puis redistribuant les biens produits vers des villes acceptatrices.
- **OpexAI** ne transporte aucun bien (0 £ de revenus de biens), et son fret rail total plafonne à ≈ 15 k£/an (uniquement quelques lignes de charbon direct mine→centrale).

### Verrous levés par V88 :
1. **Valorisation conditionnelle aval** : `OpexFreightCandidates` évaluait un tronçon par `AIIndustry.GetLastMonthProduction`. Une usine non encore approvisionnée a une production nulle (`GetLastMonthProduction == 0`), de sorte qu'un tronçon usine→ville n'était jamais candidat. V88 introduit `OpexGoodsChainCandidates`, qui évalue conjointement le tronçon amont (matière première → usine) et le tronçon aval (biens → ville), en dérivant le volume aval du volume amont transporté.
2. **Origine déjà servie / Quai joint** : `OpexOriginService` écartait toute paire dont une extrémité était déjà desservie (`pairsOriginServed`). Pour une chaîne, l'usine doit pouvoir être terminus des intrants et origine des biens avec une gare jointe (partage du `StationID` et ajout d'un quai parallèle via `OpexJoinPlatformPlans`, avec exemption de collision `_tooClose` via `candidate.joinLineId`).
3. **Projet chaîne dans le portefeuille** : Évaluation conjointe (capital total, profit total, ROI de la chaîne) dans `portfolio_v2`, et construction ordonnée en deux étapes (intrant d'abord, biens ensuite).

---

## 2. Conception retenue

### 2.1. Réglage et constantes
- **Réglage** : `v88_goods_chain` (défaut `0`, booléen) déclaré dans `ai/OpexAI/info.nut`, initialisé à `false` dans `ai/OpexAI/globals_pre.nut`, lu dans `ai/OpexAI/settings.nut` (`V88_GOODS_CHAIN`), et intégré dans le contrat `sweeps/test_campaign_freeze.py` (71 réglages, défaut 0).
- **Hypothèse de conversion intrants → biens** : Définie dans `ai/OpexAI/main.nut` sous la constante nommée et documentée sans nombre magique :
  ```squirrel
  const OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT = 1.0;
  ```
  Dans le jeu de base OpenTTD (climat tempéré), 1 unité de céréales, bétail ou acier livrée à l'usine génère des biens proportionnellement au volume livré (ratio de base 1:1, modifié par le taux de livraison régulier). L'hypothèse 1.0 est conservatrice et prédictive pour estimer le dimensionnement de la desserte de biens.

### 2.2. Génération et valorisation conjointe (`candidates.nut`)
- Résolution dynamique des types d'industrie et cargos via l'API NoAI (`AICargo`, `AIIndustryType`, `AIIndustry`), sans aucun ID codé en dur :
  - Détection du cargo de biens via `AICargo.GetTownEffect(c) == AICargo.TE_GOODS`.
  - Identification des usines de transformation via `catalog.isTransformer[indType]`.
  - Récupération des intrants acceptés par `AIIndustryType.GetAcceptedCargo`.
- Pour chaque intrant disponible et chaque industrie productrice non encore servie :
  - Évaluation du tronçon d'intrant : `candInput = OpexMakeCandidate(...)`.
  - Estimation de la production mensuelle de biens :
    ```squirrel
    local goodsMonthly = (candInput.carried * OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT).tointeger();
    ```
  - Évaluation du tronçon aval vers chaque ville acceptatrice dans les bornes rail (`candGoods = OpexMakeCandidate(...)`).
  - Agrégation :
    - `totalProfit = candInput.profitAnnual + candGoods.profitAnnual;`
    - `totalCapital = candInput.capital + candGoods.capital;`
    - `chainRoi = (totalProfit * 1000) / totalCapital;`
  - Assemblage du `chainCandidate` (`isChain = true`, `inputCandidate`, `goodsCandidate`, `factoryId`, `dstTown`, etc.).

### 2.3. Clé de projet et clés d'abandon (`projects.nut`, `lines.nut`)
- Clé de projet dans le portefeuille :
  ```squirrel
  "chain|" + inputCargo + "|" + sourceIndustryId + "|" + factoryId + "|t" + dstTown
  ```
- Clés d'abandon (`OpexAbandonedPairKey`) :
  - Étape 1 : `"freight|" + inputCargo + "|" + srcInd + "|" + factoryId`
  - Étape 2 (vers ville) : `"freight|" + goodsCargo + "|" + factoryId + "|t" + dstTown` (conforme au standard G9§1 `t<townId>` pour éviter les collisions avec les IDs d'industries).

### 2.4. Gare jointe à l'usine (`builder_rail.nut`, `lines.nut`)
- Lors de la construction de l'étape 2, `goodsCandidate` reçoit :
  - `joinPlatform = factoryPlatform` (ancre, direction, longueur du quai posé à l'étape 1).
  - `joinStationId = factoryStationId` (StationID de la gare posée à l'étape 1).
  - `joinLineId = inputLineId`.
- Dans `builder_rail.nut` :
  - `OpexRailPlatformPlans` détecte `joinPlatform` et délègue à `OpexJoinPlatformPlans` pour générer des quais parallèles adjacents partageant `joinStationId`.
  - `OpexExecuteRailPlan` et `OpexSimulateRailInfraCost` passent `stIdA = planA.stationId` à `AIRail.BuildRailStation`.
- Dans `lines.nut` :
  - `_tooClose` ignore la ligne `candidate.joinLineId`, évitant le faux positif de rejet pour proximité excessive avec son propre quai d'intrant.

### 2.5. Construction en deux étapes et reprise (`task_rail.nut`, `task_projects.nut`)
- **Étape 1 (Intrant)** :
  - Déclenchée dans `_tryBuildRailProject` lorsque le projet chaîne est élu par le portefeuille.
  - Construit le tronçon `inputCandidate` (soit de manière immédiate, soit via la recherche A* reprenable `_startRailSearch`).
  - À la réussite : enregistre `this._activeGoodsChain` avec `step = 2`, `factoryId`, `townId`, `inputLineId`, `factoryStationId`, `factoryPlatform`, `goodsCandidate`.
  - Si le capital le permet immédiatement (`bankBalance >= goodsCandidate.capital + reserve`) et qu'aucune recherche rail n'est en vol, l'étape 2 est engagée dans la foulée.
- **Étape 2 (Biens)** :
  - Réalisée par `_tryBuildGoodsChainStep2(year, passDiscards, anchor, yy)`.
  - Reprise en tête de `_tryBuildProjects` dès qu'aucune recherche A* n'est en cours (`this._activeGoodsChain.step == 2 && this._railSearch == null`).
  - Si la trésorerie est temporairement insuffisante, l'étape 2 attend le tour suivant sans abandonner.
  - Si la recherche A* ou la construction échoue, `OpexRollback` nettoie les tuiles partielles, la paire est marquée abandonnée (`_markPairAbandoned`), et `this._activeGoodsChain` est remis à `null`.

### 2.6. Persistance NoAI (`persist.nut`)
- Sérialisation stricte sans float :
  - `OpexSaveGoodsChain(chain)` : convertit toutes les métriques en entiers (`.tointeger()`).
  - `OpexLoadGoodsChain(data, catalog)` : restaure la structure et ré-associe la locomotive via le catalogue.
- Intégré dans `OpexAI::Save()` (sauvegarde courte et complète) et `OpexAI::Load()`.
- Réconciliation dans `OpexAI::_reconcileAfterLoad()` :
  - Vérification de l'existence de l'usine (`AIIndustry.IsValidIndustry`) et de la ville (`AITown.IsValidTown`).
  - Vérification que la ligne d'intrant (`inputLineId`) est toujours vivante dans `this._lines` et que la gare (`factoryStationId`) est valide. En cas d'incohérence, `_activeGoodsChain` est invalidé proprement (`null`).
  - Journalisation de preuve dans `OpexDecide("LOAD_RECONCILE", ... + " goods_chain=...")`.

### 2.7. Instrumentation minimale
- Sous les conventions de sondes existantes (longueur des panneaux `OpexSign` ≤ 31 caractères) :
  - Choix portefeuille : `OpexDecide("CHAIN_CHOSEN", "fact=" + fId + " town=" + tId + ...)`
  - Étape 1 construite : `OpexDecide("CHAIN_STEP1", ...)` / `OpexSign(anchor, "C1|yy|lineId|factoryId")`
  - Étape 2 construite : `OpexDecide("CHAIN_STEP2", ...)` / `OpexSign(anchor, "C2|yy|lineId|townId")`
  - Échec de chaîne : `OpexDecide("CHAIN_FAIL", "step=" + step + " reason=" + reason)` / `OpexSign(anchor, "CF|yy|step|reasonCode")`

---

## 3. Étape 2 future : Trains mixtes (céréales + bétail)

Dans le climat tempéré, une ferme produit à la fois des céréales (*grain*) et du bétail (*livestock*). AAAHogEx compose fréquemment des convois mixtes embarquant les deux cargaisons vers la même usine.
Pour OpexAI, cette optimisation fera l'objet d'un chantier séparé (étape 2 future), derrière son propre réglage (ex. `v88_mixed_trains`, défaut 0) :
1. **Dimensionnement des rames mixtes** : Définir la composition du train (wagons couverts pour céréales + wagons bétail) proportionnellement à la production mensuelle relative des deux cargaisons à la ferme.
2. **Ordres de chargement** : Utiliser des ordres de chargement complet conditionnels ou partagés pour éviter l'attente indéfinie d'un wagon d'une catégorie alors que l'autre est plein.
3. **Modèle de rotation** : Adapter `OpexRailPlatformPlans` et `OpexLineEconomics` pour évaluer les revenus conjoints de deux cargaisons dans le même aller-retour.

---

## 4. Protocole de validation prévu

Conformément à la consigne, les smokes et diagnostics en partie réelle seront exécutés dans un environnement dédié après la livraison du code.

### 4.1. Smoke 1×1 puis 2×3
- **Configuration** : `OpexAI[v88_goods_chain=1]`
- **Critères de succès** :
  1. Aucune régression, crash, ou exception Squirrel.
  2. Présence des traces `CHAIN_CHOSEN`, `CHAIN_STEP1`, `CHAIN_STEP2` dans les journaux de décision / panneaux.
  3. Au moins une chaîne construite : ligne 1 (matière première → usine) et ligne 2 (usine → ville acceptatrice avec quai joint).
  4. **Biens réellement livrés** : confirmation dans `PLYR old_economy delivered_cargo` que le volume de biens livré est strictement supérieur à zéro (`delivered_cargo[goods] > 0`).

### 4.2. Diagnostic apparié 5 graines × 6 ans
- **Commande** :
  ```bash
  python3 sweeps/run_c66_reference.py --line-telemetry \
    --ref "OpexAI[v88_goods_chain=0]" \
    --var "OpexAI[v88_goods_chain=1]" \
    --seeds 5 --years 6
  ```
- **Métrique principale** : `profit_year` (gain annuel d'exploitation).
- **Seuils d'arbitrage** :
  - **Effet utile** : `+50 k£/an`
  - **Garde de valeur d'entreprise** : `−5 %` maximum admissible sur la valeur finale de l'entreprise.
