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

---

## 5. Avec la recherche rapide (V90/V91)

Depuis le **2026-09-24**, les optimisations V90 (−8 % opcodes/itération) et V91 (A* pondéré au poids 120, itérations par recherche ÷ 5,4) sont actives par défaut dans OpexAI.

### 5.1 Impact physique sur le cycle d'une chaîne
- **Durée de recherche** : Une recherche qui exigeait ~3 000 itérations (soit 2,5 à 3 années de jeu à 900 iters/an) ne demande plus qu'environ **450 à 650 itérations**, parcourues en **10 à 12 tranches** de `RAIL_SEARCH_SLICE = 50`.
- **Délai temporel** : À raison d'un passage de tâche toutes les ~8-10 semaines calendaires, chaque étape de recherche s'accomplit désormais en **~60 à 100 jours de jeu (2 à 3 mois)**.
- **Cycle complet** :
  1. Décision portefeuille (`CHAIN_CHOSEN`)
  2. Recherche étape 1 (intrant) : ~2–3 mois (`CHAIN_STEP1_SEARCH` → `CHAIN_SEARCH_END step=1`)
  3. Mise en service étape 1 (`CHAIN_STEP1`)
  4. Recherche étape 2 (biens) : ~2–3 mois (`CHAIN_STEP2_SEARCH` → `CHAIN_SEARCH_END step=2`)
  5. Mise en service étape 2 (`CHAIN_STEP2`)
  6. Première livraison de biens : ~3–4 mois après mise en service (`CHAIN_DELIVERY`)
  - **Délai total décision → étape 2** : **~6 à 9 mois**, contre 5 à 6 ans avant V91.

### 5.2 Analyse des attentes et goulots restants (hors A*)
1. **Absence d'attente de production de biens** :
   - Le code (`ai/OpexAI/task_rail.nut:350-440`) ne contient **aucun test d'attente de production effective** (`GetLastMonthProduction > 0`) entre l'étape 1 et l'étape 2.
   - L'étape 2 s'engage immédiatement dès la pose du quai d'intrant. Le délai de recherche de l'étape 2 (~2-3 mois) chevauche naturellement le premier aller-retour du train d'intrants (trajet dépôt → ferme, chargement, trajet ferme → usine, déchargement, soit ~80-120 jours).
2. **Une seule chaîne active à la fois** :
   - `this._activeGoodsChain` (`task_rail.nut:161`) impose un verrou exclusif : toute nouvelle chaîne candidate est écartée avec `chain_in_progress` tant que l'étape 2 n'est pas construite.
3. **Monopolisation du créneau `_railSearch`** :
   - L'emplacement unique `this._railSearch` est occupé consécutivement par l'étape 1 puis l'étape 2. Pendant chacune de ces phases de 2-3 mois, les autres projets ferroviaires reçoivent `search_in_progress`.
4. **Trésorerie et calibrage du portefeuille** :
   - `OpexProjectFinanceCapital` (`projects.nut:288`) applique `budgetCapital = candInput.capital + candGoods.capital` multiplié par 1,7 (biais rail). Une chaîne exige donc 120k à 180k£ de trésorerie disponible pour franchir le filtre `financeCapital <= capitalBudget` (`projects.nut:909`).
   - Même sous `v88_chain_force=1`, ce filtre de capital n'était pas contourné, empêchant l'élection d'une chaîne dans les 2 premières années de jeu.
5. **Cadence de sélection / rotation du fret** :
   - `candidates.nut:1280` filtre sur `cargoIn == freightCargo`. Le cargo d'intrant (céréales, bétail, acier) n'est donc évalué que lors des passes où la rotation `freightCargoOrder` le sélectionne.
6. **Condition de reprise de l'étape 2 (`v88_step2_plan_immediate`)** :
   - `task_projects.nut:616` imposait `this._railSearch == null` pour reprendre l'étape 2. Si l'étape 2 avait déjà calculé son `railPlan` mais avait été différée pour trésorerie insuffisante (`C41_RAIL_CASH_RELEASE`), elle restait bloquée si un autre projet rail lançait une recherche.
   - Le nouveau réglage `v88_step2_plan_immediate` (défaut 0, booléen) autorise la construction de l'étape 2 dès que son `railPlan` est prêt, sans attendre que `_railSearch` redevienne inactif.

### 5.3 Protocole de mesure opérationnel
1. **Diagnostic solo 5 graines × 8 ans** :
   ```bash
   python3 sweeps/diag_c69_bottleneck_probe.py \
     --arm "OpexAI[probe_portfolio=1,probe_events=1,v88_goods_chain=1]" \
     --seeds 100 12345 42 7 999 --years 8 --max-workers 3 \
     --grep "CHAIN_" --raw results/diag_v88_chain_solo_raw.jsonl \
     --out results/diag_v88_chain_solo.json
   ```
   Variante avec forçage de chaîne :
   ```bash
   python3 sweeps/diag_c69_bottleneck_probe.py \
     --arm "OpexAI[probe_portfolio=1,probe_events=1,v88_goods_chain=1,v88_chain_force=1]" \
     --seeds 100 12345 42 7 999 --years 8 --max-workers 3 \
     --grep "CHAIN_" --raw results/diag_v88_chain_force_raw.jsonl \
     --out results/diag_v88_chain_force.json
   ```
2. **Analyse des délais et livraisons** :
   ```bash
   python3 sweeps/analyse_v88_chains.py results/diag_v88_chain_solo_raw.jsonl
   python3 sweeps/analyse_v88_chains.py results/diag_v88_chain_force_raw.jsonl
   ```
   - Indicateurs : chaînes choisies, terminées, livrant des biens (`CHAIN_DELIVERY` et `delivered_cargo_last_quarter[goods] > 0`), délais médians par étape.
3. **Critères d'accès au duel** :
   - Passage au **duel apparié 5×6** (`run_c66_reference.py`) si au moins 3/5 graines construisent une chaîne complète avec des biens livrés.
   - Seuil de qualification économique : effet utile `+50 k£/an` sur `profit_year`, garde de valeur d'entreprise `−5 %`.
   - Duel officiel **20 graines × 10 ans** avant tout changement de défaut.

### 5.4 Résultat du diagnostic solo 5×8 — 2026-09-25

Campagne `results/v88_goods_chain_solo_5x8_20260925.json` avec traces
`results/v88_goods_chain_solo_5x8_20260925.jsonl`, graines 100/12345/42/7/999 :
**5/5 parties saines, 0 échec moteur**.

Après correction d'un bug de l'analyseur (une chaîne terminée était perdue lorsqu'une nouvelle
`CHAIN_CHOSEN` survenait avant sa première `CHAIN_DELIVERY`), le bilan réel est :
- **4 chaînes choisies** ;
- **2 chaînes terminées** ;
- **2 chaînes avec livraison de biens**, sur les graines **42 et 7** ;
- **0 chaîne en échec explicite** ;
- **8 attentes** `step=2 reason=rail_search`.

Délais médians observés : recherche étape 1 **153 jours**, mise en service étape 1 **72 jours**,
recherche étape 2 **300,5 jours**, mise en service étape 2 **136,5 jours**, décision→étape 2
**863,5 jours (2,37 ans)**, étape 2→première livraison **295 jours**. Pathfinder médian :
étape 1 **694 itérations / 57 tuiles**, étape 2 **853 itérations / 70 tuiles**.

Le critère préalable au duel (**≥3/5 graines avec chaîne complète livrée**) n'est donc **pas atteint**.
Ne pas lancer le 5×6 causal V88 tel quel ; il faut d'abord augmenter l'exposition ou supprimer le
blocage résiduel de l'étape 2, notamment autour du slot rail unique.

### 5.5 Requalification sur le défaut courant (`master` `ed8fc13`) — 2026-09-26

Campagne `results/v88x_diag_chain_solo.json` avec traces `results/v88x_diag_chain_solo_raw.jsonl`,
mesurée sur `master` à jour (incluant `rail_finance_bias_pct=100` et `v89_rail_search_throughput=1`) :
- **Graines analysées** : 5 (100, 12345, 42, 7, 999) sur 8 ans, arm `OpexAI[probe_portfolio=1,probe_events=1,v88_goods_chain=1]`
- **Chaînes choisies** : 6
- **Chaînes terminées** : 1 (graine 100)
- **Chaînes avec livraison de biens** : **0** (0/5 graines)
- **Chaînes échouées** : 3 (2 `TRKFAIL` graine 100, 1 `factory_gone` graine 7)
- **Attentes mesurées** : **17 attentes** `step=2 reason=rail_search`
- **Délais médians** : recherche ét. 1 **142,5 j**, commission ét. 1 **155 j**, recherche ét. 2 **889 j**, décision→ét. 2 **322 j**.

**Diagnostic des goulots mesurés dans l'entonnoir (Étape 2) :**
1. **Évaluation du capital au portefeuille** : `candInput.capital + candGoods.capital` imposait ~100k-120k£ de trésorerie disponible pour qu'une chaîne entre dans `projects.best`, retardant le premier choix à 1974.
2. **Rotation des cargos de fret** : `OpexGoodsChainCandidates` ne scannait que `cargoIn == freightCargo`. Si le charbon était actif, toutes les usines (céréales, bétail, acier) étaient ignorées.
3. **Monopolisation du slot `_railSearch`** : Des recherches ferroviaires ordinaires ont accaparé le slot unique jusqu'à 1 517 jours (4,15 ans sur graine 999), interdisant à la chaîne de lancer l'A*.
4. **Famine de trésorerie post-étape 1** : Sans réserve, les lignes aériennes vidaient la caisse dès l'étape 1 construite, retardant l'étape 2 (1,5 an sur graine 7, conduisant à la fermeture de l'usine `factory_gone`).

### 5.6 Levée des verrous d'exposition et qualification (Étape 2) — 2026-09-26

Quatre réglages neufs (défaut 0, sans aucun surcoût ni dérive au défaut) ont été introduits :
- `v88_all_inputs` : évalue tous les intrants acceptés sans attendre la rotation `freightCargo`.
- `v88_chain_step1_finance` : capitalise la chaîne sur l'étape 1 (~50 k£) pour la sélection initiale.
- `v88_step2_rail_prio` : bloque les recherches rail concurrentes quand l'étape 2 attend, et plafonne le seuil de tranche de débit à 2 500 opcodes.
- `v88_step2_cash_reserve` : réserve le capital estimé de l'étape 2 dans `OpexAvailableCapital` dès que l'étape 1 est construite.

**Validation préalable de non-régression et contrat :**
- 359/359 tests unitaires Python OK (`test_campaign_freeze.py`, `test_v88_goods_chain.py`, `test_v89_rail_throughput.py`).
- **Identité stricte au défaut** (`bench_v2.py --arms "OpexAI" --seeds 42 --years 1`) : 100 % identique au bit près à la référence sur `master` (`company_value=427019`, `score=194`, `profit_year=306642`, `median_station_rating=167`, `n_vehicles=23`, `n_stations=20`).
- **Persistance Save/Load** (`sweeps/save_load_roundtrip.py`) : `LOAD_RECONCILE` OK, synchronisation de `V88_STEP2_RESERVE_AMOUNT` validée à la réconciliation.

**Résultats de la requalification 5×8 solo** (`results/v88x_diag_chain_fixed.json`, `results/v88x_diag_chain_fixed_raw.jsonl`) :
Arm : `OpexAI[probe_portfolio=1,probe_events=1,v88_goods_chain=1,v88_all_inputs=1,v88_chain_step1_finance=1,v88_step2_rail_prio=1,v88_step2_cash_reserve=1,v88_step2_plan_immediate=1]`

| Graine | Chaînes choisies | Chaînes terminées | Chaînes livrant | Échecs | Délais décision→ét. 2 (j) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **7** | 1 | 1 | **1** | 0 | 881 |
| **42** | 3 | 2 | **2** | 0 | 379, 913 |
| **100** | 2 | 2 | **2** | 0 | 106, 318 |
| **999** | 1 | 1 | **1** | 0 | 976 |
| **12345** | 2 | 1 | **1** | 1 (`ABND`) | 675 |
| **Total** | **9** | **7** | **7 (5/5 graines)** | **1** | **médiane : 675 j (1,85 an)** |

- **Attentes mesurées** : **0 attente** (ni `rail_search`, ni `cash`).
- **Délais médians** :
  - Recherche étape 1 : **18,0 jours** (contre 153 j le 25 sept, −88 %)
  - Recherche étape 2 : **44,0 jours** (contre 300,5 j le 25 sept, −85 %)
  - Mise en service étape 1 : **95,0 jours**
  - Mise en service étape 2 : **496,0 jours**
  - Étape 2 → première livraison : **217,0 jours**
- **Premières livraisons de biens par graine** :
  - Graine 100 : 1972-05-20 (ligne 15, rev 6 689 £)
  - Graine 12345 : 1973-04-10 (ligne 24, rev 6 868 £)
  - Graine 42 : 1973-06-27 (ligne 16, rev 14 522 £)
  - Graine 999 : 1974-01-20 (ligne 27, rev 11 611 £)
  - Graine 7 : 1977-09-30 (ligne 76, rev 7 009 £)

**Verdict :** Le seuil d'accès au duel ($\ge 3/5$ graines livrant une chaîne complète) est **pleinement atteint avec 5/5 graines (100 %)**. Le duel causal apparié 5×6 peut être lancé par l'orchestrateur.

### 5.7 Duels 5×6 et enquête — 2026-09-26 : la qualification solo ne se traduit pas en gain

La qualification solo de §5.6 ne tient pas en duel contre AAAHogEx (5 graines 42/100/999/1234/5678 ×
6 ans, variante − référence `v88_goods_chain=0`, arbre non commité, bundles gelés) :

| Variante | `profit_year` | V/D | IC95 | Valeur |
|---|---:|---:|---|---:|
| 4 correctifs (`v88_unlocked_vs_default_5x6_20260926`) | −286,6 k£/an | 0/5 | [−372,5 ; −200,7] k£ | −15,1 % |
| sans réserve ni priorité rail (`v88_noreserve_noprio_vs_default_5x6_20260926`) | −234,2 k£/an | 1/4 | [−442,0 ; −26,4] k£ | −15,4 % |
| chaînes seules (`v88_chainonly_vs_default_5x6_20260926`) | −117,1 k£/an (médiane −235,3) | 2/3 | [−421,0 ; +186,7] k£ | −10,0 % |

Symptôme commun : effondrement de la flotte aérienne (graine 5678 : 109 → 31 avions ; 999 : 84–89 →
32–33), le rail ne gagnant que 0 à +7 trains.

**Enquête solo** (`sweeps/diag_v88_investigation.py`, `results/v88inv_*`, graines 100/999/5678 × 6 ans) :
les chaînes seules ne font pas s'effondrer l'aérien en solo (337 contre 342 avions, profit en hausse) ;
avec les correctifs, −34 % d'avions. La perte « chaînes seules » du duel n'est donc pas reproduite en solo.

**Défauts confirmés par lecture de code** :
1. `v88_chain_step1_finance` fixe `budgetCapital` au capital de l'étape 1 (`projects.nut:452`), mais
   `fundScore` = profit (des deux étapes) ÷ `OpexProjectFinanceCapital` (`projects.nut:1037`) : le score
   est environ doublé et la chaîne passe en tête du classement.
2. `_tryBuildGoodsChainStep2` renvoie `true` quand l'étape 2 ne fait que lancer son A*
   (`if (start.pending) return true;`, `task_rail.nut` ~424 sur `master`) : `_tryBuildProjects`
   incrémente `builtCount` sans construction et applique `k_pass` aux projets suivants.

Aggravant (comportement existant, pas propre à V88) : une passe `projects` qui lance un A* s'arrête
(`task_projects.nut` ~1164-1195) ; tous les projets derrière la chaîne, aériens compris, sont sautés.
En duel, AAAHogEx occupe pendant ces gels les places d'aéroport des villes (deux par ville), et
OpexAI échoue ensuite sur ces paires.

**Décision** : V88 est suspendu jusqu'à la cible « A\* dans les workers, projets rail éligibles
seulement à tracé prêt » ([note 36](36_astar_workers_conception.md), étape 4 : les étapes d'une chaîne
deviennent des demandes de tracé prioritaires). Les deux défauts sont à corriger à ce moment-là ;
ne pas relancer de duel V88 avant.
