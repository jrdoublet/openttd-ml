# Revue du diff de la branche `road1y-combo`

## 1. Objectif et contexte
L'objectif de cette mission est de regrouper l'ensemble des 8 leviers « neutres » route seule (proches de 0, ni franchement négatifs ni encore adoptés) dans une branche unique (`road1y-combo`, créée depuis `origin/master` sur le worktree `/home/deploy/projects/wt-combo`) afin de les qualifier ensemble en duel face à AAAHogEx en mode route seule.

Les leviers explicitement exclus (`aaa_fleet`, `town_reuse`, `pax_min`, `rich_fleet`, `abandon_days`, `site_relocate`, `retry`, `famille mail`, `next2`) ont été scrupuleusement ignorés.

Tous les nouveaux paramètres sont déclarés avec une valeur par défaut de **0** pour toutes les difficultés (`easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0`), bornés rigoureusement, et forcés à 0 en l'absence du mode route seule (`if (!road1yRoadOnly) ROAD1Y_* = 0;`) dans les **deux** chargeurs de paramètres (`OpexLoadSettings` et `OpexLoadBusDistrictSettings`). À 0, le code exécuté est strictement équivalent bit-à-bit et décision par décision à celui de `master`.

---

## 2. Historique des commits intégrés

La branche comporte exactement 8 commits de fonctionnalité au-dessus de `origin/master` (un commit par levier) :

1. `7769e4c4` - `feat(road1y): road1y_bridge max bridge length over water and rail for bus A* (default 0)`
   - Paramètre : `road1y_bridge` (0..6, défaut 0, valeur banquée 4).
   - Fichiers modifiés : `builder_road.nut`, `globals_pre.nut`, `info.nut`, `road1y_astar.nut`, `settings.nut`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road1y_bridge.py`, `sweeps/test_road1y_multimodal_gate.py`.

2. `bbe7acb1` - `feat(road1y): add road1y_far long-distance bus pair setting and trace budget scaling`
   - Paramètre : `road1y_far` (0..96, défaut 0, valeur banquée 64).
   - Fichiers modifiés : `bus_districts_overrides.nut`, `globals_pre.nut`, `info.nut`, `road1y_astar.nut`, `settings.nut`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road1y_far.py`, `sweeps/test_road1y_multimodal_gate.py`.

3. `65f31ff2` - `feat(road1y): road1y_freight, plafond camions fret + admission x2 (défaut 0)`
   - Paramètre : `road1y_freight` (0..30, défaut 0, valeur banquée 12).
   - Fichiers modifiés : `candidates.nut`, `economy.nut`, `globals_pre.nut`, `info.nut`, `settings.nut`, `sweeps/fixtures/invest_stall_merged_20261105.json`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road100_merge_projection_20261105.py`, `sweeps/test_road1y_freight.py`, `sweeps/test_road1y_multimodal_gate.py`.

4. `cfac5e68` - `feat(road1y): road1y_truck_fleet, flotte des camions fret geree comme AAAHogEx (defaut 0)`
   - Paramètre : `road1y_truck_fleet` (0..1, défaut 0, valeur banquée 1).
   - Fichiers modifiés : `ai/OpexAI/road1y_truck_fleet.nut` (nouveau), `bus_districts_overrides.nut`, `globals_pre.nut`, `info.nut`, `main.nut`, `settings.nut`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/fixtures/road100_bus_districts_overrides.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road1y_multimodal_gate.py`, `sweeps/test_road1y_truck_fleet.py`.

5. `3bbe9108` - `feat(road1y): road1y_berth_fleet mask, default 0`
   - Paramètre : `road1y_berth_fleet` (masque 0..3, défaut 0, valeur banquée 3).
   - Fichiers modifiés : `bus_districts.nut`, `bus_districts_overrides.nut`, `globals_pre.nut`, `info.nut`, `settings.nut`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/fixtures/road100_bus_districts_overrides.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road1y_berth_fleet.py`, `sweeps/test_road1y_multimodal_gate.py`.

6. `dfe534bd` - `feat(road1y): road1y_pax_bilat bus refleet on weakest terminus stock (default 0)`
   - Paramètre : `road1y_pax_bilat` (0..1, défaut 0, valeur banquée 1).
   - Fichiers modifiés : `bus_districts_overrides.nut`, `globals_pre.nut`, `info.nut`, `settings.nut`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road100_bus_districts.py`, `sweeps/test_road1y_multimodal_gate.py`, `sweeps/test_road1y_pax_bilat.py`.

7. `e8913f33` - `feat(road1y): road1y_pair_fleet, classer les paires bus-quartier sur l'estimation a flotte mure (defaut 0)`
   - Paramètre : `road1y_pair_fleet` (0..24, défaut 0, valeur banquée 8).
   - Fichiers modifiés : `ai/OpexAI/road1y_pair_fleet.nut` (nouveau), `bus_districts_overrides.nut`, `economy.nut`, `globals_pre.nut`, `info.nut`, `main.nut`, `settings.nut`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/fixtures/road100_bus_districts_overrides.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road1y_multimodal_gate.py`, `sweeps/test_road1y_pair_fleet.py`.

8. `3c8c727b` - `feat(road1y): road1y_alt_load, une part des bus PAX charge a plein au bout B (defaut 0)`
   - Paramètre : `road1y_alt_load` (0..50, défaut 0, valeur banquée 33).
   - Fichiers modifiés : `builder_road.nut`, `bus_districts.nut`, `globals_pre.nut`, `info.nut`, `scheduler_tasks.nut`, `settings.nut`, `sweeps/fixtures/road100_bus_districts_hunks.json`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/road100_off_projection.py`, `sweeps/test_road1y_alt_load.py`, `sweeps/test_road1y_multimodal_gate.py`, `sweeps/test_v251_inventory.py`.

---

## 3. Revue détaillée des modifications de code

### 3.1 Déclarations globales et chargeurs de paramètres
- `globals_pre.nut` : tous les symboles globaux (`ROAD1Y_BRIDGE`, `ROAD1Y_FAR`, `ROAD1Y_FREIGHT`, `ROAD1Y_TRUCK_FLEET`, `ROAD1Y_BERTH_FLEET`, `ROAD1Y_PAX_BILAT`, `ROAD1Y_PAIR_FLEET`, `ROAD1Y_ALT_LOAD`, `ROAD1Y_ALT_LOAD_CENSUS_YM`) sont initialisés à 0 (ou -1 pour le recensement) après la ligne 124, à l'extérieur des contextes de hunks historiques ROAD100/ROAD1Y-B2.
- `info.nut` : déclaration des 8 réglages avec `min_value = 0`, bornes supérieures exactes, et `easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = 0`.
- `settings.nut` : dans `OpexLoadSettings` et `OpexLoadBusDistrictSettings`, lecture systématique via `AIController.GetSetting()`, validation stricte des bornes (repli à 0 si hors bornes), et forçage conditionnel `if (!road1yRoadOnly) ROAD1Y_* = 0;`.

### 3.2 Modules métier
- **Ponts et portée A\*** (`builder_road.nut`, `road1y_astar.nut`) :
  - Support des ponts au-dessus des plans d'eau et voies ferrées conditionné à `ROAD1Y_BRIDGE > 0`.
  - Extension du rayon de recherche et dimensionnement proportionnel du budget de nœuds conditionnés à `ROAD1Y_FAR > 0`.
- **Fret routier** (`candidates.nut`, `economy.nut`, `road1y_truck_fleet.nut`, `bus_districts_overrides.nut`) :
  - Admission renforcée et plafond camions relevé sous `ROAD1Y_FREIGHT > 0`.
  - Gestion dynamique de flotte camions calquée sur AAAHogEx sous `ROAD1Y_TRUCK_FLEET > 0`.
- **Quais et renforts bus** (`bus_districts.nut`, `bus_districts_overrides.nut`) :
  - Refleet bus sur l'attente bilatérale `2 * min(waitingA, waitingB)` sous `ROAD1Y_PAX_BILAT > 0`.
  - Extra-quais joints sans réserve 50k (bit 1) et renfort mensuel (bit 2) sous `ROAD1Y_BERTH_FLEET`.
  - Inversion ordonnée des ordres (plein chargement en B) sur N% des bus sous `ROAD1Y_ALT_LOAD > 0`.
  - Reclassement des paires bus ≤ 127 tuiles sur l'estimation à N bus sous `ROAD1Y_PAIR_FLEET > 0`.

### 3.3 Fixtures et projecteurs de régression
- `road100_bus_districts_hunks.json` : mise à jour des blocs `info.nut`, `settings.nut` et `builder_road.nut`.
- `road100_bus_districts_overrides.json` : synchronisation exacte des méthodes surchargées.
- `road100_off_projection.py` : calcul des SHA256 exacts pour `ROAD1Y_B2_RAIL_MERGE` et `ROAD1Y_B2_RAIL_MERGE_STAGES` pour chaque étape de projection.
- `rail_open_legacy.py` et `rail_sibling_legacy.py` : synchronisation de `_MERGE_SHA`.
- `invest_stall_merged_20261105.json` : ajout de la variante `road1y_freight` pour valider la transition d'état de `candidates.nut`.

---

## 4. Vérification de conformité et validation

- **`git diff --check`** : zéro avertissement de formatage, d'espaces superflus ou de conflit.
- **Tests unitaires dédiés** :
  - `test_road1y*.py` : 145 tests passants sur 145.
  - `test_road100*.py` : 236 tests passants sur 236 (3 passés intentionnellement).
  - `test_v251*.py` : 7 tests passants sur 7.
- **Suite globale** : aucun nouvel échec par rapport à `origin/master`.
- **Invariants préservés** : aucun mot-clé réservé Squirrel utilisé comme identifiant, aucun `.find(` sur tableau, aucune fonction anonyme dans le code neuf, aucune capture implicite.
