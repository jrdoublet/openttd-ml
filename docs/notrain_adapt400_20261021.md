# Autopsie NOTRAIN sous adapt400 : pourquoi OpexAI pose des voies sans train

> **Date :** 21 octobre 2026  
> **Branche de travail :** `notrain` (dépôt `/home/deploy/projects/wt-notrain`)  
> **Données de banc analysées :** `/home/deploy/projects/wt-v299/results/v299_diag_3x10_20261021_engine/` (10 ans, 3 graines : 42, 7, 100 ; 2 bras : `reference_*` = master, `v299_*` = `v294_rail_weight_adapt=400`)  
> **Script de diagnostic :** [`sweeps/diag_notrain_adapt400.py`](file:///home/deploy/projects/wt-notrain/sweeps/diag_notrain_adapt400.py)  
> **Précédentes autopsies liées :** [`docs/railech_abnd_20261021.md`](file:///home/deploy/projects/wt-notrain/docs/railech_abnd_20261021.md), entrée `RAIL-ECH` dans [`docs/taches.md`](file:///home/deploy/projects/wt-notrain/docs/taches.md#L49-L52)

---

## Résumé exécutif

L'autopsie des abandons A* ([`docs/railech_abnd_20261021.md`](file:///home/deploy/projects/wt-notrain/docs/railech_abnd_20261021.md)) avait révélé que l'activation de `v294_rail_weight_adapt=400` divise par 5 les abandons A* (`ABND` : 45 $\to$ 9), mais fait exploser le motif **`NOTRAIN` de 1 à 10 tentatives**.

L'investigation approfondie des journaux moteur et du code Squirrel démontre que :
1. **Une voie posée sans train n'est pas abandonnée dans le monde : elle est intégralement démolie par rollback.**  
   À chaque échec au dépôt, [`OpexRollback()`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3008-L3044) rase la voie ferrée, les deux gares et le dépôt. Mais cette démolition est à fonds perdus : les frais de terrassement et de pose initiale ne sont pas remboursés par OpenTTD.
2. **Le capital détruit est massif :** les 10 tentatives `NOTRAIN` sous adapt400 ont brûlé **374 623 £** de trésorerie nette (contre 31 851 £ pour l'unique cas de master), soit une moyenne de **37 462 £ par tentative**.
3. **Les 10 `NOTRAIN` sous adapt400 ne sont pas 10 lignes différentes, mais seulement 2 paires répétées en boucle :**
   - Paire 1 (`40990 -> 44972`, acier, dist 157) : répétée **6 fois de suite** entre septembre 1972 et mars 1973 (**215 785 £** brûlés).
   - Paire 2 (`20255 -> 42610`, marchandises, dist 170) : répétée **4 fois de suite** entre septembre 1978 et avril 1979 (**158 838 £** brûlés).
4. **La cause de la répétition est une omission de sécurité dans [`task_rail.nut`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/task_rail.nut#L1355-L1361) :** le motif `NOTRAIN` n'est pas dans la liste des motifs qui appellent `_markPairAbandoned()`. La paire rejetée reste en tête du portefeuille avec un ROI prédit élevé (> 1 000). Comme l'A* adaptatif la résout désormais en ~300 itérations au lieu d'échouer en `ABND`, OpexAI la retente immédiatement le mois suivant !
5. **Les deux causes physiques de l'échec d'achat au dépôt sont :**
   - **Erreur 525 (`ERR_VEHICLE_TOO_LONG`, 7 cas sur 11) :** pour les gros volumes de fret, la rame calculée dépasse 13 wagons (7 tuiles), ce qui viole le plafond global OpenTTD `vehicle.max_train_length = 7`. `MoveWagon` échoue au 14e wagon.
   - **Erreur 0 (`failure="LENGTH"`, 4 cas sur 11) :** en 1978, la motrice `SH '125'` (HST Diesel 200 km/h) est introduite. C'est une motrice multi-head (`RAILVEH_MULTIHEAD`) qui mesure **16/16e de tuile** (deux motrices de 8/16e). Le modèle supposait une motrice de 8/16e (`2p - 1` wagons). Avec 13 wagons de 8/16e et une motrice de 16/16e, la rame mesure $16 + 13 \times 8 = 120 > 112$ (quai de 7 tuiles). Le garde interne [`builder_rail.nut:3145`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3145) bloque l'attelage avec `error = 0`.

---

## 1. Cartographie des sorties `NOTRAIN` et `ORDFAIL` dans le code

Dans le code source d'OpexAI, le statut `NOTRAIN` est produit à **5 endroits précis** :

```
                                  [Tentative Ferroviaire]
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
             [Fail-Before-Spend]                          [Post-Construction]
          Vérification des slots train                 Pose de la voie + gares + dépôt
        (OpexRailVehicleSlotAvailable)                               │
                       │                                             ▼
       ┌───────────────┼───────────────┐                    [OpexBuildTrains()]
       ▼               ▼               ▼                             │
builder_rail    builder_rail    rail_templates        ┌──────────────┴──────────────┐
  :L3891          :L4450          :L661               ▼                             ▼
(Voie simple)   (Voie double)   (Templates)    [failure == "ORDER"]         [Autre failure]
       │               │               │              │                             │
       └───────────────┼───────────────┘              ▼                             ▼
                       │                           ORDFAIL                       NOTRAIN
                       ▼                     (builder_rail:4105, 4587)     (builder_rail:4105, 4587)
                    NOTRAIN                                                         │
             (0 £ dépensé, 0 tuile)                                                 ▼
                                                                             [OpexRollback()]
                                                                         (Démolition intégrale,
                                                                         capital de pose perdu)
```

### 1.1 Les 3 sorties préventives « Fail-Before-Spend »
- [`ai/OpexAI/builder_rail.nut:3890-3893`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3890-L3893) (dans `OpexExecuteRailPlan`) :
  ```squirrel
  if (!OpexRailVehicleSlotAvailable()) {
    result.reason = "NOTRAIN";
    return result;
  }
  ```
- [`ai/OpexAI/builder_rail.nut:4449-4452`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L4449-L4452) (dans `OpexV190ExecuteRailPlan`) : code identique.
- [`ai/OpexAI/rail_templates.nut:660-663`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/rail_templates.nut#L660-L663) (dans `OpexBuildRailWithTemplates`) : code identique.

**Étape vérifiée :** ces gardes vérifient [`OpexRailVehicleSlotAvailable()`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3761-L3768), qui consulte `AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, AIVehicle.VT_RAIL) < AIGameSettings.GetValue("vehicle.max_trains")` (plafond standard de 500 trains).  
**Impact financier :** **Strictement 0 £**. Aucune tuile, aucune gare, aucun dépôt n'a encore été posé.  
**Journaux émis :** aucun journal direct juste avant, si ce n'est la vérification de trésorerie précédente (`result.money < need`). Dans les 11 cas analysés sur le banc, **aucune tentative n'est sortie par cette branche**.

### 1.2 Les 2 sorties après pose de voie : échec de construction du convoi
- [`ai/OpexAI/builder_rail.nut:4101-4107`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L4101-L4107) (dans `OpexExecuteRailPlan`) :
  ```squirrel
  result.diag = trains.diag;
  if (trains.failed || trains.built == 0) {
    if (tiles2 != null) OpexRollback(tiles2, planA2, planB2, depot2, trains.rollbackVehicles);
    OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
    result.actualCost = primaryCost + (postPathCosts != null ? postPathCosts.GetCosts() : 0);
    result.reason = (trains.failed && trains.failure == "ORDER") ? "ORDFAIL" : "NOTRAIN";
    return result;
  }
  ```
- [`ai/OpexAI/builder_rail.nut:4581-4589`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L4581-L4589) (dans `OpexV190ExecuteRailPlan`) : code identique pour la voie double.

**Étape en échec :**  
La voie ferrée, les deux gares et le dépôt ont déjà été construits physiquement sur la carte. `primaryCost` enregistre la facture totale réelle émise par le moteur OpenTTD. Puis `OpexBuildTrains(...)` est appelé :
1. **Contrôle initial de cohérence de longueur** ([`builder_rail.nut:3085`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3085)) :
   `if (wagons < 1 || wagons + wagons2 > nominalMaxWagons || trainLengthLimit < 1)`  
   $\to$ Renvoie `failure = "LENGTH", error = 0`.
2. **Achat de la locomotive au dépôt** ([`builder_rail.nut:3096`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3096)) :
   `AIVehicle.BuildVehicle(depotTile, loco.id)`. Si invalide : `failure = "VEHICLE", error = AIError.GetLastError()`. Remplit `diag` avec le prix, le cash, le type de rail, etc.
3. **Mesure de longueur et achat des wagons** ([`builder_rail.nut:3133-3162`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3133-L3162)) :
   - `car = AIVehicle.BuildVehicle(depotTile, wagon.id)`
   - Si `trainLength + carLength > trainLengthLimit` ([`builder_rail.nut:3145`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3145)) :  
     $\to$ Renvoie **`failure = "LENGTH", error = 0`**.
   - `if (!AIVehicle.MoveWagon(car, 0, train, 0))` ([`builder_rail.nut:3150`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3150)) :  
     $\to$ Renvoie **`failure = "WAGON", error = AIError.GetLastError()`**. Quand la rame dépasse `vehicle.max_train_length = 7` tuiles (112 unités), le moteur OpenTTD retourne l'erreur **525** (`ERR_VEHICLE_TOO_LONG`).
4. **Affectation des ordres** ([`builder_rail.nut:3165-3174`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3165-L3174)) :  
   `AppendOrder` pour la gare A puis la gare B. Si échec : `failure = "ORDER"`.  
   $\to$ **C'est le seul cas qui déclenche la raison `ORDFAIL`**. Dans tous les autres cas d'échec du train (`LENGTH`, `WAGON`, `VEHICLE`, `START`), la raison émise est **`NOTRAIN`**.

---

## 2. Relevé exhaustif des 11 occurrences `NOTRAIN`

Sur les 6 parties de 10 ans du banc v299 (3 graines $\times$ 2 bras), **11 occurrences** de `RAIL_ATTEMPT reason=NOTRAIN` ont été détectées, toutes concentrées sur la graine 42 :

| N° | Bras | Date | Paire Src $\to$ Dst | Coord Src | Coord Dst | Cargo | Manh | Len | Devis £ | Dépensé £ | Erreur | Itér. A* | Opcodes | Trésorerie précédant l'achat |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | Master | 1972-12-17 | 50791 $\to$ 22586 | (103, 198) | (58, 88) | GOOD | 155 | 166 | 88 486 £ | **31 851 £** | **525** | 3 167 | 10,59 M | 414 243 £ |
| **2** | V299 | 1972-09-26 | 40990 $\to$ 44972 | (30, 160) | (172, 175) | STEL | 157 | 149 | 100 095 £ | **37 462 £** | **525** | 306 | 2,56 M | 178 751 £ |
| **3** | V299 | 1972-10-20 | 40990 $\to$ 44972 | (30, 160) | (172, 175) | STEL | 157 | 149 | 97 005 £ | **34 717 £** | **525** | 307 | 2,56 M | 178 751 £ |
| **4** | V299 | 1972-11-12 | 40990 $\to$ 44972 | (30, 160) | (172, 175) | STEL | 157 | 149 | 97 599 £ | **35 369 £** | **525** | 308 | 2,54 M | 178 751 £ |
| **5** | V299 | 1972-12-06 | 40990 $\to$ 44972 | (30, 160) | (172, 175) | STEL | 157 | 149 | 97 569 £ | **35 339 £** | **525** | 308 | 2,54 M | 178 751 £ |
| **6** | V299 | 1972-12-30 | 40990 $\to$ 44972 | (30, 160) | (172, 175) | STEL | 157 | 149 | 97 569 £ | **35 339 £** | **525** | 308 | 2,54 M | 178 751 £ |
| **7** | V299 | 1973-03-03 | 40990 $\to$ 44972 | (30, 160) | (172, 175) | STEL | 157 | 149 | 100 134 £ | **37 559 £** | **525** | 308 | 2,55 M | 178 751 £ |
| **8** | V299 | 1978-09-09 | 20255 $\to$ 42610 | (31, 79) | (114, 166) | GOOD | 170 | 138 | 72 328 £ | **33 225 £** | **0** | 184 | 20,25 M | 9 186 899 £ |
| **9** | V299 | 1978-10-26 | 20255 $\to$ 42610 | (31, 79) | (114, 166) | GOOD | 170 | 138 | 68 761 £ | **29 583 £** | **0** | 984 | 5,30 M | 9 186 899 £ |
| **10** | V299 | 1978-12-10 | 20255 $\to$ 42610 | (31, 79) | (114, 166) | GOOD | 170 | 138 | 67 966 £ | **28 788 £** | **0** | 984 | 5,30 M | 9 186 899 £ |
| **11** | V299 | 1979-04-08 | 20255 $\to$ 42610 | (31, 79) | (114, 166) | GOOD | 170 | 158 | 92 998 £ | **67 242 £** | **0** | 3 948 | 9,02 M | 11 358 806 £ |

### 2.1 Examen des 200 lignes précédentes : la trésorerie était-elle en cause ?
L'extraction systématique des 200 lignes précédant chaque tentative écarte formellement l'hypothèse d'une insuffisance de liquidités :
- **En 1972 (tentatives 1 à 7) :** la trésorerie disponible (`live_budget`) s'élevait à **178 751 £** (pour un devis de ~97 k£ et un coût de pose de ~35 k£).
- **En 1978-1979 (tentatives 8 à 11) :** la compagnie disposait de **9,18 M£ à 11,36 M£ en caisse**, soit plus de 100 fois le coût complet de la ligne.
- Aucun message de refus de cash (`CASH`, `insufficient_cash`) n'est émis. L'échec se produit exclusivement au moment où le train est assemblé dans le dépôt.

### 2.2 Que devient l'infrastructure posée ? Y a-t-il réutilisation ultérieure ?
L'analyse du code de [`OpexRollback`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3008-L3044) et l'historique complet des parties révèlent :
1. **La démolition est totale et effective :**
   - La boucle `for (local i = 1; i < tiles.len() - 1; i++) AITile.DemolishTile(tiles[i])` rase chaque case de voie.
   - Les quais sont retirés par `AIRail.RemoveRailStationTileRectangle`.
   - Le dépôt est détruit par `AITile.DemolishTile(depot)`.
   - La preuve formelle que rien ne subsiste est que **la tentative du mois suivant repaye l'intégralité du coût de construction** (~35 000 £) sur le même tracé et les mêmes gares. Si des voies étaient restées en place, l'A* aurait échoué en `TRKFAIL` (`_HasRail` interdisant de poser sur du rail existant).
2. **Aucune reprise ultérieure par destination partagée (V178/V179) :**
   - Sur la paire `40990 -> 44972` : après l'abandon en mars 1973, une gare est posée à `44972` en avril 1974 pour du grain (`line=67`), mais avec `reuse=0` (gare 100 % neuve). Une gare est posée à `40990` en juin 1976 pour du minerai de fer (`line=76`), également avec `reuse=0`.
   - Sur la paire `20255 -> 42610` : **aucune ligne ferroviaire** n'a jamais été construite sur ces tuiles jusqu'à la fin de la partie en 1980.

---

## 3. Coût économique : le capital brûlé par les voies sans train

Lorsqu'un chantier échoue au dépôt, OpenTTD ne rembourse pas les travaux d'infrastructure (les frais de pose de voie, de signalisation et de terrassement sont perdus, et la démolition au bulldozer coûte elle-même de l'argent).

| Sous-ensemble | Nombre de tentatives | Distance Manh | Longueur tracé | Coût moyen / tentative | Capital total gaspillé |
|---|:---:|:---:|:---:|:---:|:---:|
| **Master : Paire 50791 $\to$ 22586 (GOOD)** | 1 | 155 | 166 | 31 851 £ | **31 851 £** |
| **V299 : Paire 40990 $\to$ 44972 (STEL)** | 6 | 157 | 149 | 35 964 £ | **215 785 £** |
| **V299 : Paire 20255 $\to$ 42610 (GOOD)** | 4 | 170 | 138 – 158 | 39 710 £ | **158 838 £** |
| **TOTAL V299 (adapt=400)** | **10** | **157 – 170** | **138 – 158** | **37 462 £** | **374 623 £** |

> [!CAUTION]
> **Surcoût direct de NOTRAIN sous adapt400 : 342 772 £ de capital détruit.**  
> Au lieu de transformer le succès de l'A* en rentabilité économique, la combinaison du déblocage de l'A* et de l'absence de mise en quarantaine de la paire transforme le chantier en une pompe aspirante qui pose et détruit la même voie 6 fois d'affilée en quelques mois.

---

## 4. Hypothèses classées, preuves formelles et correctifs

### Hypothèse 1 (Rang 1 — Effet multiplicateur) : Omission de `NOTRAIN` dans la mémoire d'abandon `_markPairAbandoned`

- **Description :** Dans [`ai/OpexAI/task_rail.nut:1355-1361`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/task_rail.nut#L1355-L1361), la fonction qui enregistre l'abandon d'une paire (`_markPairAbandoned`) liste explicitement les motifs d'échec :
  ```squirrel
  if ((result.reason == "ABND" || result.reason == "SITEA" || result.reason == "SITEB" ||
       result.reason == "SITEAB" || result.reason == "NOPA" || result.reason == "STNFAIL"
       || (RAIL_GEOMETRY_GUARD && RAIL_GEOMETRY_PAIR_MEMORY
           && result.reason == "TRKFAIL"
           && ("persistentGeometry" in result) && result.persistentGeometry))) {
    this._markPairAbandoned(OpexAbandonedPairKey(candidate));
  }
  ```
  `NOTRAIN` et `ORDFAIL` sont **totalement absents** de ce prédicat.
- **Preuve :** Après un échec `NOTRAIN`, la paire candidate conserve son score ROI intact dans le portefeuille (ex: ROI 1 078 pour l'acier, ROI 1 640 pour les marchandises). Au tick suivant, OpexAI la sélectionne immédiatement (`PROJECT_CHOSEN rank=0`). Sous master, l'A* lent finissait par diverger ou être différé ; sous adapt400, l'A* trouve le tracé en 300 itérations et reconstruit la même voie 6 fois en 6 mois. La boucle ne s'arrête que si la production baisse ou si un `ABND` accidentel survient (cas du 1979-07-03 après 4 tentatives).
- **Correctif proposé (Vérifié `task_rail.nut:1355`) :**  
  Ajouter `result.reason == "NOTRAIN" || result.reason == "ORDFAIL"` dans la condition d'abandon de la paire. Si un train ne peut pas être acheté sur un site donné, la paire doit être mise en liste noire / cooldown de 365 jours immédiatement au lieu d'être reconstruite le mois suivant.

---

### Hypothèse 2 (Rang 2 — Erreur 525) : Convoi de fret dépassant le plafond dur OpenTTD `vehicle.max_train_length = 7`

- **Description :** OpenTTD fixe par défaut `vehicle.max_train_length = 7` tuiles. Une tuile équivaut à 16 sous-unités de longueur (soit $7 \times 16 = 112$ unités).  
  Dans OpexAI, le quai nominal est dimensionné d'après `station.station_spread` (qui vaut **12 tuiles** dans la configuration de banc, [`catalog.nut:394`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/catalog.nut#L394)). Pour une usine sidérurgique ou une usine à fort débit, le modèle économique ([`economy.nut:235-260`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/economy.nut#L235-L260)) calcule une rame de 14 à 16 wagons.  
  Une motrice de 8 unités + 14 wagons de 8 unités = **120 unités > 112 unités**.  
  La voie et les quais de 8 ou 9 tuiles sont construits avec succès. La locomotive et les 13 premiers wagons sont achetés dans le dépôt. Mais au moment d'atteler le 14e wagon, `AIVehicle.MoveWagon` appelle la commande moteur OpenTTD `CmdMoveRailVehicle`, qui vérifie `train_length <= _settings_game.vehicle.max_train_length`. Le moteur refuse l'attelage avec l'erreur `STR_ERROR_TRAIN_TOO_LONG` $\to$ NoAI traduit en **`AIError.ERR_VEHICLE_TOO_LONG = 525`**.
- **Preuve :**  
  - 7 échecs sur 11 (1 sous master, 6 sous adapt400) émettent `RAIL_BUILD_FAIL reason=NOTRAIN error=525`.
  - Ce bogue a été documenté le 15/10 sous la tâche **V206** ([`docs/taches.md:1848`](file:///home/deploy/projects/wt-notrain/docs/taches.md#L1848)) mais laissé au défaut 0 car testé à l'époque en rail seul où la rentabilité marchandises était faible.
  - V207 avait corrigé ce point pour les seuls voyageurs ([`economy.nut:208-211`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/economy.nut#L208-L211) : *« Borne limitée aux rames pax V207 : le quai, le fret et les défauts restent inchangés »*). Le fret était resté vulnérable !
- **Correctif proposé (Vérifié `economy.nut:212` et `catalog.nut:395`) :**  
  Activer le bornage universel `maxWagons = OpexRailNominalMaxWagons(catalog.maxTrainLength)` pour **tous les cargos** (fret comme passagers) dans [`economy.nut:208`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/economy.nut#L208), ou borner `catalog.platformLength = min(station_spread, max_train_length)` dans [`catalog.nut:395`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/catalog.nut#L395).

---

### Hypothèse 3 (Rang 3 — Erreur 0) : Motrice multi-head `SH '125'` de longueur 16 heurtant le contrôle de longueur `builder_rail.nut:3145`

- **Description :** En 1978, la motrice `SH '125'` (InterCity 125, Diesel, 200 km/h) devient disponible. Dans la table OpenTTD (`table/engines.h:442`), elle est déclarée comme `RAILVEH_MULTIHEAD` (`M`) : elle possède obligatoirement une motrice de tête et une motrice de queue.  
  Quand `OpexBuildTrains` achète la motrice, `AIVehicle.GetLength(train)` renvoie **16 unités** (1 case complète).  
  Or, la formule historique de capacité nominale de quai ([`catalog.nut:20`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/catalog.nut#L20)) stipule :
  $$\text{nominalMaxWagons}(p) = 2p - 1$$
  Cette formule suppose que la motrice mesure **8 unités** (une demi-case) et chaque wagon **8 unités** ($8 + (2p-1) \times 8 = 16p$).  
  Pour un quai de $p = 7$ tuiles (plafond 112 unités), le modèle autorise 13 wagons.  
  Mais avec la motrice `SH '125'`, la longueur physique réelle devient :
  $$16 + (13 \times 8) = 120 \text{ unités} > 112 \text{ unités (quai de 7 tuiles)}$$
  Lors de la boucle d'achat des wagons dans `OpexBuildTrains` ([`builder_rail.nut:3145`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/builder_rail.nut#L3145)) :
  ```squirrel
  if (trainLength + carLength > trainLengthLimit) {
    return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
             failed = true, failure = "LENGTH", error = 0, diag = diag, ... };
  }
  ```
  La condition est violée dès le 13e wagon. La fonction retourne `failure = "LENGTH"` avec **`error = 0`**.
- **Preuve :**  
  - Les 4 échecs `NOTRAIN` avec `error = 0` ont tous eu lieu en fin de partie (1978-1979) sur la même ligne de marchandises `20255 -> 42610`.
  - C'est exactement l'époque où `SH '125'` (200 km/h) est élue meilleure locomotive par [`OpexCatalog::_refreshRail`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/catalog.nut#L559-L568) devant `SH '40'` (176 km/h) en raison de sa vitesse de pointe supérieure.
  - La valeur `error = 0` ne peut provenir d'aucune API NoAI (les erreurs NoAI sont strictement positives) ; elle est codée en dur uniquement aux lignes 3087 et 3147 de `builder_rail.nut` lors d'un échec `LENGTH`.
- **Correctif proposé (Vérifié `catalog.nut:20` et `economy.nut:200`) :**  
  Dans le catalogue, identifier si la locomotive choisie est `RAILVEH_MULTIHEAD` (ou si sa longueur mesurée au dépôt est de 16). Pour une motrice double, la capacité nominale du quai doit être réduite d'un wagon :
  $$\text{nominalMaxWagons}(p) = 2p - 2$$
  Ainsi, pour un quai de 7 tuiles, le convoi sera borné à 12 wagons ($16 + 12 \times 8 = 112 \le 112$), garantissant l'attelage sans rejet.

---

### Hypothèse 4 (Rang 4 — Rôle causal d'adapt400) : Déblocage des tracés longs et exposition de bogues dormants

- **Description :** Pourquoi ce phénomène n'apparaissait-il presque pas sous Master (1 seul cas) ?
- **Preuve :**  
  Sous Master (`reference_*`), le poids A* fixe de 120 % provoquait **45 abandons (`ABND`)** à 5 000 itérations (soit 33 % de toutes les tentatives ferroviaires !). Les lignes longues de plus de 150 tuiles n'aboutissaient presque jamais à la phase de construction physique : elles mouraient avant d'avoir dépensé un seul centime dans l'A*.  
  Sous `v294_rail_weight_adapt=400`, la recherche de chemin A* est résolue en **184 à 308 itérations**. Les lignes longues à fort volume (acier, marchandises) franchissent l'A* immédiatement et accèdent au chantier. C'est l'efficacité spectaculaire de l'A* qui a révélé au grand jour les bogues d'attelage et l'absence de mise en quarantaine des `NOTRAIN`.

---

## 5. Synthèse comparative des correctifs proposés

| Problème identifié | Fichier et Ligne vérifiés | Impact actuel | Correctif proposé (sous réglage à défaut 0) |
|---|---|---|---|
| **Répétition infinie des NOTRAIN** | [`ai/OpexAI/task_rail.nut:1355`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/task_rail.nut#L1355) | 375 k£ brûlés par reconstruction mensuelle en boucle | Inclure `NOTRAIN` et `ORDFAIL` dans `_markPairAbandoned()` avec cooldown de 365 j |
| **Erreur 525 (Rame > 7 tuiles)** | [`ai/OpexAI/economy.nut:208`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/economy.nut#L208) et [`catalog.nut:395`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/catalog.nut#L395) | 7 NOTRAIN sur 11 (247 k£ perdus) | Étendre la borne `vehicle.max_train_length` de V207 à tous les cargos fret |
| **Erreur 0 (Motrice SH 125 double-head)** | [`ai/OpexAI/catalog.nut:20`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/catalog.nut#L20) et [`economy.nut:201`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/economy.nut#L201) | 4 NOTRAIN sur 11 (159 k£ perdus) | Réduire de 1 wagon (`2p - 2`) la capacité nominale pour les motrices multi-head |

---

## 6. Conclusion et recommandations

L'apparition de 10 `NOTRAIN` sous `v294_rail_weight_adapt=400` n'est pas un défaut de l'algorithme A* lui-même, mais **le symptôme d'un pipeline ferroviaire dont l'entonnoir aval n'était pas préparé à recevoir des tracés résolus aussi vite**.

Deux actions complémentaires s'imposent avant de qualifier définitivement adapt400 :
1. **Verrou de sécurité immédiat :** Brancher `NOTRAIN` dans la mémoire d'abandon de [`task_rail.nut:1355`](file:///home/deploy/projects/wt-notrain/ai/OpexAI/task_rail.nut#L1355). Même en cas de rejet au dépôt, la compagnie ne doit plus jamais reconstruire et raser la même ligne 6 fois de suite.
2. **Couplage avec V206 / V282 (mode 2) :** Borner les rames et quais de fret à `vehicle.max_train_length = 7` pour éliminer à la source l'erreur 525 et l'incompatibilité de longueur.
