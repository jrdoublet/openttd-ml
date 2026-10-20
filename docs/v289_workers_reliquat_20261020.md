# Audit V289 : Inventaire des mécanismes de reliquat et workers après V263b

Date : 2026-10-20  
Auteur : agy  
Branche : `v289` (depuis `master`)  
Contexte : Exploitation des ~5 600 opcodes/tick (~6 M opcodes/an, ~9 % du budget) abandonnés par `Sleep(1)` en fin de boucle principale (`main.nut` et `probes.nut`).

---

## 1. Préparation rail C121 (`_c121RailPrepAfterProjectsPass`) et stock de tracés

- **Fichiers et lignes vérifiés :**
  - `ai/OpexAI/rail_prep_c121.nut:145-175` : méthode `_c121RailPrepAfterProjectsPass()` appelée en fin de passe de la tâche projets (`task_projects.nut:1971, 1983`).
  - `ai/OpexAI/rail_prep_c121.nut:177-199` : `_c121RailPrepMaybeCatalog()` génère les candidats de préparation via `OpexBuildCandidates(...)` une fois par mois.
  - `ai/OpexAI/rail_prep_c121.nut:202-223` : `OpexC121RailPrepCandidateBlocked(ai, candidate, curDate)` filtre les candidats déjà en stock, en cooldown, abandonnés ou à industrie invalide.
  - `ai/OpexAI/rail_prep_c121.nut:227-260` : `_tryStartC121RailPrepSearch()` initialise un A* sur le meilleur candidat libre via `_startRailStockSearch(candidate)`.
  - `ai/OpexAI/rail_prep_c121.nut:116-141` : `_c121RailPrepOnPassStart()` gère la complétion vers le stock et le hold si l'aérien redevient finançable (`_c121RailPrepHold`).
  - `ai/OpexAI/task_rail.nut:1402-1504` : `_startRailStockSearch(candidate)` configure la recherche segmentée A* et instancie `_activeWorker = { kind = "rail_stock", state = { ai = this } }`.
  - `ai/OpexAI/task_rail.nut:1544-1615` : `_handleRailStockSearchCompleted()` dépose le plan validé dans `this._railReadyStock[pairKey]` (plafonné à `C121_RAIL_PREP_MAX = 3`).
- **État persisté :** Aucun. `_railReadyStock` est initialisé à `{}` dans `main.nut:418` et réinitialisé à `{}` au chargement dans `persist.nut:1042`. Ni `_railSearch`, ni `_c121RailPrepCandidates`, ni `_railStockCooldown` ne sont sérialisés dans la sauvegarde.
- **Coût par pas :**
  - Évaluation / catalogue mensuel : ~50k à 250k opcodes (exécuté au plus 1×/mois).
  - Amorçage d'une recherche (`OpexPrepareRailRoute` + `OpexCreateSegmentedSearch`) : ~1 000 à 3 000 opcodes.
  - Tranches A* individuelles : ~1 500 à 3 500 opcodes par tranche (`_v89EstimatedSliceOps`).
- **Reprenable :** Oui. La recherche A* est segmentée (`OpexCreateSegmentedSearch`) et avancée tranche par tranche (`_advanceRailSearchSliceWithLedgers()`).
- **Consommateurs du résultat :**
  - `projects_generation.nut:715-738` (`OpexProjectsIncludeRailReadyStock`) et `projects_selection.nut:1378-1430` injectent les tracés prêts dans les alternatives du portefeuille.
  - `task_projects.nut:1474` : contourne le blocage `search_in_progress` pour les chantiers préparés (`c121PrepStock`).
  - `task_rail.nut:167-245` et `364-370` : réutilise directement le tracé préparé (`railPlan`) sans recalcul et supprime l'entrée du stock lors de la construction.

---

## 2. Worker rail / stock V149 (`rail_stock`)

- **Fichiers et lignes vérifiés :**
  - `ai/OpexAI/orchestrator.nut:252-328` : fonction `OpexWorkerRailStockStep(worker, opsBudget, deadlineTick)`.
  - `ai/OpexAI/orchestrator.nut:330-343` : fonction `OpexWorkerRailStockCancel(worker)`.
  - `ai/OpexAI/orchestrator.nut:346` : enregistrement `OpexRegisterWorker("rail_stock", ...)`.
  - `ai/OpexAI/orchestrator.nut:992-1015` : cadencement du travailleur actif `rail_stock` dans l'orchestrateur.
  - Note historique (`docs/suppressions_parametres_idees_20261017.md:432`) : le réglage autonome `c80_rail_stock_worker` a été retiré, mais le travailleur sous-jacent `rail_stock` est resté dans `orchestrator.nut` pour la préparation C121.
- **État persisté :** Aucun. `persist.nut:117-120` ignore explicitement `rail_search` et `rail_stock` à la sauvegarde ; `persist.nut:1034-1037` purge tout travailleur orphelin au rechargement.
- **Coût par pas :** Une tranche d'A* (~1 500 à 3 500 opcodes), bornée par `AIController.GetOpsTillSuspend() >= minThreshold`.
- **Reprenable :** Oui, pas par pas via `_advanceRailSearchSliceWithLedgers()`.
- **Consommateurs du résultat :** `_handleRailStockSearchCompleted()` qui alimente `_railReadyStock`.

---

## 3. Avancement opportuniste V89 (`_advanceRailSearchThroughput`)

- **Fichiers et lignes vérifiés :**
  - `ai/OpexAI/scheduler.nut:428-447` : `OpexAI::_advanceRailSearchThroughput(maxSlices = -1)`.
  - `ai/OpexAI/main.nut:850` : appel dans la boucle normale juste avant `_c67SlackHook` et `Sleep(1)`.
  - `ai/OpexAI/probes.nut:2565` : appel dans `_mainLoopProfiled`.
- **Comportement actuel :** Ne travaille QUE si `this._railSearch != null && this._railSearch.phase == "search"`. Si aucune recherche n'est en cours, ou si `_c121RailPrepHold` est actif, retourne immédiatement `0`.
- **État persisté :** Aucun. Le suivi `_v89EstimatedSliceOps` (initialisé à 2 000 dans `main.nut:145`) est recalibré dynamiquement en mémoire.
- **Coût par pas :** Dépend du nombre de tranches exécutées (chacune ~1 500 - 3 500 opcodes).
- **Reprenable :** Oui.
- **Consommateurs du résultat :** Accélère la terminaison de la recherche A* en cours vers sa phase `"build"`.

---

## 4. Cartographie C67 (`_c67TerrainSlackStep`)

- **Fichiers et lignes vérifiés :**
  - `ai/OpexAI/task_terrain.nut:95-115` : `_c67TerrainSlackStep()`.
  - `ai/OpexAI/task_terrain.nut:147-154` : `_c67SlackHook()`.
  - `ai/OpexAI/main.nut:852-856` et `probes.nut:2568-2574` : crochet gardé par `if (C67_SLACK_HOOK)`.
  - `ai/OpexAI/task_terrain.nut:10-11` : constantes `C67_SLACK_RESERVE = 3000` et `C67_SLACK_MIN = 4000`.
- **Comportement actuel :** Actif uniquement si `C67_SLACK_HOOK` est vrai (`c67_terrain_map` ou `c67_water_exposure_probe` à 1). Au défaut (0), le crochet n'est jamais appelé et le reliquat est abandonné.
- **État persisté :** Aucun. `_c67Terrain` (`OpexTerrainMap`) est instancié à la demande (`_c67TerrainInit()`) et non sérialisé.
- **Coût par pas :** Biaisé pour ne jamais déborder : alloue `left - C67_SLACK_RESERVE` (au moins 1 000 opcodes par pas).
- **Reprenable :** Oui, progression par blocs de tuiles (raster).
- **Consommateurs du résultat :** Oracles de terrain et sonde passive eau.

---

## 5. Croissance des villes desservies (`town_growth`)

- **Fichiers et lignes vérifiés :**
  - `ai/OpexAI/main.nut:488` : `{ name = "town_growth", dueCycle = 2147483647, enabled = false }` (slot inerte réservé pour la stabilité du curseur de tâche lors du chargement d'anciennes sauvegardes).
  - `ai/OpexAI/persist.nut:161` : `if (kind == "town_growth") return null;` (travailleur urbain obsolète ignoré au rechargement).
  - `ai/OpexAI/task_report.nut:167-204` et `538-540` : maintien des fonctions de santé pour d'éventuelles lignes historiques de croissance urbaine (`purpose == "town_growth"`).
  - Disparition de la logique active : `task_town.nut` et `feeder_bus.nut` ont été intégralement purgés lors de V234 (`commit a9660ab`). Aucun mécanisme de planification ou d'action urbaine n'existe dans le code actuel.
- **Référence de richesse et de garde (V249) :**
  - `ai/OpexAI/task_v249.nut:9-20` : `OpexV249MaxListedCapital(projects)` calcule le capital du projet le plus cher du portefeuille.
  - `ai/OpexAI/task_v249.nut:46-54` : `OpexV249MeasureStatueCost(townId)` mesure le coût réel via `AITestMode()` et `AIAccounting()`.
  - `ai/OpexAI/task_v249.nut:128-133` : seuil de richesse `threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects)`. L'action n'est financée que si `cash - cost >= threshold` et `loan == 0`.
- **Spécification pour V289 (bit 4) :**
  - Comme aucun mécanisme urbain n'a survécu à V234, implémentation du pas minimal demandé :
    1. Déterminer les villes desservies par les lignes en service et identifier la plus rentable via `OpexV249LineProfit` (comme dans `task_v249.nut`).
    2. Vérifier `AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_FUND_BUILDINGS)`.
    3. Mesurer le coût en `AITestMode()` avec `AIAccounting()`.
    4. Garde de richesse : `cash - cost >= OpexCashReserve() + OpexV249MaxListedCapital(this._projects)` et aucun emprunt.
    5. Cadence : au plus une fois par ville et par 6 mois (mémoire de date par ville `_v289TownFundDate`, non persistée car simple borne de cadence).

---

## 6. Synthèse des caractéristiques

| Composant | Fichier & Lignes | État persisté | Coût / pas (opcodes) | Reprenable | Consommateur |
|---|---|---|---|---|---|
| **Stock & Prep Rail** | `rail_prep_c121.nut:145-260`, `task_rail.nut:1402-1615` | Non (reconstruit) | ~1 500 - 3 500 (tranche) | Oui (A* segmenté) | `_railReadyStock` -> sélection & construction sans A* bloquant |
| **Worker `rail_stock`** | `orchestrator.nut:252-328` | Non | ~1 500 - 3 500 | Oui | Complétion A* vers `_railReadyStock` |
| **Opportuniste V89** | `scheduler.nut:428-447` | Non | ~1 500 - 3 500 | Oui | Recherche rail en cours (`_railSearch`) |
| **Cartographie C67** | `task_terrain.nut:95-115` | Non | Biaisé (`left - 3000`) | Oui (blocs raster) | `OpexTerrainMap` (oracles) |
| **Croissance urbaine** | Purgé en V234 ; garde `task_v249.nut:9-140` | Non | ~500 - 1 500 (`AITestMode` / action) | Ponctuel (1 ville/6 mois) | Développement urbain (`TOWN_ACTION_FUND_BUILDINGS`) |
