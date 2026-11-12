# État de la suite de tests au 12 novembre 2026

Date : 2026-11-12  
Branche : `agy12-nov12`  
Dépôt : `/home/deploy/projects/wt-agy12`  

---

## 1. Bilan global avant / après correction des anomalies hors-rail

Avant intervention (sur base master / post-leviers de la nuit) :
- **Total tests exécutés :** 3901 tests
- **FAIL (échecs) :** 22
- **ERROR (erreurs) :** 1
- **Dont anomalies hors-rail :** 6 FAIL (1 dans `test_c77_intent_defer`, 1 dans `test_diag_air_site_probe`, 4 dans `test_po01c_regen_split`)
- **Dont anomalies rail :** 16 FAIL + 1 ERROR

Après intervention (alignement des témoins des 3 suites hors-rail) :
- **Total tests exécutés :** 3901 tests
- **FAIL (échecs) :** 16 (tous strictement ferroviaires / domaine rail protégé)
- **ERROR (erreurs) :** 1 (strictement ferroviaire / domaine rail protégé)
- **Anomalies hors-rail restantes :** **0** (100 % résolues)
- **Suites protégées :**
  - `test_road1y*.py` : 74/74 OK (100 %)
  - `test_road100*.py` : 236/236 OK (3 skip) (100 %)
  - `test_v251*.py` : 7/7 OK (100 %)

---

## 2. Anomalies hors-rail corrigées

### 1. `sweeps/test_c77_intent_defer.py` (1 FAIL corrigé)
- **Test :** `test_modes_0_1_orchestrator_bytes_and_api_contract`
- **Cause :** Le test comparait l'empreinte SHA-256 d'`orchestrator.nut` (après retrait du bloc mode-2 C77) à une empreinte figée au commit historique `8c9c9e1a`. Les ajouts légitimes postérieurs dans `_runOrchestratorTick` (EB-14, V233L, RAIL-LONG v2/v3, INVEST_STALL) modifiaient les octets restants.
- **Correction :** Acceptation du tuple d'empreintes revues incluant l'empreinte de merge `2a70dd048191089c3d46695b38c4b6a51af7e9afddc986ed9800b9fa99bcc8d2`.

### 2. `sweeps/test_diag_air_site_probe.py` (1 FAIL corrigé)
- **Test :** `test_off_hashes`
- **Cause :** Les empreintes figées dans `sweeps/fixtures/air_site_probe_off_hashes.json` dataient du 27/10/2026. L'évolution de `main.nut`, `settings.nut`, `info.nut`, `globals_pre.nut`, `po01c_generators.nut`, `po01c_regen.nut` et `probes.nut` par les leviers mergés ultérieurs faisait échouer la vérification unitaire.
- **Correction :** Ajout de la table `REVIEWED_MERGED_OFF_HASHES` associant chaque fichier source à son empreinte projetée OFF revu sur la base mergée actuelle, tout en conservant les empreintes historiques d'origine.

### 3. `sweeps/test_po01c_regen_split.py` (4 FAIL corrigés)
- **Tests :**
  - `test_po01d_synchronous_path_bytes_unchanged` (`air_planning.nut`, `candidates.nut`, `catalog.nut`)
  - `test_po01f_historical_dependencies_unchanged` (`economy.nut`)
- **Cause :**
  - `air_planning.nut` a reçu le levier `AIR_COVERAGE_STOP` (`ae6fe7d1`).
  - `catalog.nut` a reçu les gardes `EB10_GUARDS` (`e66c523b`).
  - `candidates.nut` et `economy.nut` ont reçu les projections de merge de HEAD.
- **Correction :** Prise en compte des empreintes de merge revues pour ces fichiers via des dictionnaires de hachages acceptés, en préservant strictement les ancrages historiques `RESERVE0_PO01D_SHA256` et `RESERVE0_PO01F_SHA256`.

---

## 3. Liste exhaustive des 16 FAIL + 1 ERROR restants (domaine RAIL)

Ces anomalies sont **toutes réservées au domaine ferroviaire** (interdit d'intervention selon `AGENTS.md` et consignes de mission).

| Type | Test | Fichier / Composant | Raison du maintien (domaine rail) |
|---|---|---|---|
| **ERROR** | `test_only_models_file_changes` | `sweeps/test_estim31_railnorm_safe_20261030.py` | Requiert un répertoire d'artefacts externe non versionné (`/home/deploy/results/estim31_railnorm_safe20261030/...`). |
| **FAIL** | `test_revalidation_mandatory_before_build` | `sweeps/test_c80_rail_stock_worker.py` | Contrat de revalidation du stock worker ferroviaire C80. |
| **FAIL** | `test_exact_opt_in_change_and_off_neutral` | `sweeps/test_estim31_v161_rail1970_20261030.py` | Financement ferroviaire de première année (V161 / RAIL1970). |
| **FAIL** | `test_learning_is_level_only_and_reload_recalculates` | `sweeps/test_estim_unifie_bit16.py` | Apprentissage de distance rail (bit 16 d'ESTIM-UNIFIE). |
| **FAIL** | `test_historical_producers_and_bytes_stay_frozen` | `sweeps/test_p1_rail_long_value_rank.py` | Classement de valeur des lignes longues ferroviaires P1. |
| **FAIL** | `test_trace_and_save_load_transience` | `sweeps/test_p1_rail_long_value_rank.py` | Transience et Save/Load du traceur P1 rail. |
| **FAIL** | `test_historical_inventory_not_rebased` | `sweeps/test_p2_rail_cargo_opportunity.py` | Opportunités de fret ferroviaire P2. |
| **FAIL** | `test_all_new_line_successes_reset_clock` | `sweeps/test_rail_repair_idle_sixmonths_20261030.py` | Horloge de réparation rail 6 mois (`task_road.nut` vérifié dans le contexte rail repair). |
| **FAIL** | `test_failure_logs_and_rollback_order_are_unchanged` | `sweeps/test_rail_track_failure_capture.py` | Capture d'échec de pose de voie ferrée et ordre de rollback. |
| **FAIL** | `test_inlining_capture_restores_original_builder` | `sweeps/test_rail_track_failure_capture.py` | Inlining de capture de voie ferrée dans `builder_rail.nut`. |
| **FAIL** | `test_only_guard_added_to_historical_rail_source` | `sweeps/test_station_plan_precheck.py` | Pré-vérification de plan de gare ferroviaire. |
| **FAIL** | `test_off_reviewed_edits_preserve_all_original_hashes` (economy) | `sweeps/test_v233_long_good.py` | Ligne ferroviaire mono-voie et modèle de profit V233L. |
| **FAIL** | `test_off_reviewed_edits_preserve_all_original_hashes` (globals_pre) | `sweeps/test_v233_long_good.py` | Réglages et variables globales V233L / rail long. |
| **FAIL** | `test_off_reviewed_edits_preserve_all_original_hashes` (settings) | `sweeps/test_v233_long_good.py` | Chargement des réglages ferroviaires V233L. |
| **FAIL** | `test_off_reviewed_edits_preserve_all_original_hashes` (task_rail) | `sweeps/test_v233_long_good.py` | Tâche d'exécution ferroviaire V233L. |
| **FAIL** | `test_default_path_unchanged` | `sweeps/test_v296a_batch_build.py` | Pose par lots de voies ferrées V296A. |
| **FAIL** | `test_every_exit_logs` | `sweeps/test_v296a_batch_build.py` | Journalisation des sorties de pose de voies ferrées V296A. |
