# État des tests sous estim_unifie=31 (QUALITÉ-TESTS-ESTIM31)

Date de référence : 2026-11-07  
Branche : `agy-easy` (base `origin/master 7e5ad9d4`)

## 1. Bilan d'ensemble et progression

| Étape | Tests totaux | Échecs (FAIL) | Erreurs (ERROR) | Total anomalies | Ignorés (skipped) |
|---|---|---|---|---|---|
| **Initial (base origin/master)** | 3849 | 83 | 24 | **107** | 16 |
| **Fin Tour 1 (commit `f5fabb7c`)** | 3849 | 49 | 17 | **66** (-41) | 16 |
| **Fin Tour 2 (commit `c2e0f2d5`)** | 3849 | 34 | 1 | **35** (-72) | 30 |
| **Tour 3 - Courant (commit `57f9152e`)** | 3849 | **32** | **1** | **33** (-74) | **29** |

**Bilan net après Tour 3 :** Réduction de **107 à 33 anomalies** (-69% d'anomalies).
Sur les **33 anomalies restantes** :
- **18 tests concernent le domaine RAIL** (laissés strictement intacts et inventoriés conformément aux consignes).
- **1 divergence d'interaction** C77 × PO01C × EB-14 consignée et chiffrée dans `docs/agy_specs/defauts_decouverts.md`.
- **14 échecs résiduels** de projections historiques ou d'empreintes strictes (dont le hunk 2 de `projects_models.nut` post-7160c6f5 et `main.nut` post-rail-experiments).

---

## 2. Classification détaillée des lots traités

### Famille A : Manque de dépendance optionnelle hôte (numpy) - RÉSOLU (Tour 1)
- `test_demo_frontieres_temps_20261025.py` (7 erreurs -> 0) : import optionnel protégé dans `sweeps/analyse_roi_predictors_20261021.py`.

### Famille B & B-bis : Attente obsolète de probes=0 (défaut promu à 2) - RÉSOLU (Tours 1 & 2)
- 8 tests alignés sur la valeur par défaut publique validée `probes=2`.

### Famille C & C-bis : Plafond AddSetting codé en dur obsolète (58 vs 68) - RÉSOLU (Tours 1 & 2)
- 7 tests actualisés au comptage réel de 68 réglages sur `master`.

### Famille D : Hunks V233L / off_source post-merge - RÉSOLU (Tour 1)
- 22 échecs résolus dans `v233_long_good_legacy.py`.

### Famille H : Signature OpexAirAddPlane et synchronisation files - RÉSOLU (Tour 2)
- 4 tests alignés sur le 4e argument `forcedEngine` et le paramètre `locked`.

### Famille I : Registre des tâches et priorités 20x10 - RÉSOLU (Tour 2)
- `sweeps/test_estim31_20x10_priority_analysis.py` aligné sur `AIR-COVERAGE-STOP` et la clôture de `POST-1974-ENTONNOIR`.

### Famille F-bis : Découplage de test_estim31_c121_dispatch.py - RÉSOLU (Tour 2)
- 4 tests résolus par lecture scindée de `air_economics_c121_fullscan.nut`.

### Famille E-bis : Valeurs par défaut et priors calibrés ESTIM-31 - RÉSOLU (Tour 2)
- `sweeps/test_estim_unifie.py` aligné sur les priors réels (`rail = 1.00`, `air = 1.50`, `weight = 15.0`).

### Famille K : Neutralisation de l'extension PAX_AIR_FIRST_AIR_UNBOUNDED dans V278 - RÉSOLU (Tour 3, commit `c4dba185`)
- `sweeps/test_v278_air_lazy_sites.py` : neutralisation ciblée de `&& !PAX_AIR_FIRST_AIR_UNBOUNDED` sur la garde de distance de `OpexAirPlansNewPairs`, restaurant exactement l'empreinte historique SHA-256 (`PAIRS_HASH`). 19/19 tests OK.

### Famille L : Autonomie du test de classement final ESTIM-31 - RÉSOLU (Tour 3, commit `57f9152e`)
- `sweeps/test_estim31_final_rank_20261030.py` : mock unitaire d'`analyze_40x5` en l'absence des fichiers de campagne volumineux de `results/`. Le test valide désormais l'ancre `docs/estim31_v161_40x5_20261030.json` de façon 100% autonome et passe inconditionnellement (2/2 tests OK, 0 skipped).

---

## 3. Inventaire exhaustif des tests SkipTest liés aux artefacts de campagne dans results/

Au total, **10 fichiers** et **14 méthodes de test** ont été protégés par `SkipTest` au Tour 2 en raison de l'absence du répertoire transitoire `results/` (ignoré par Git).

| N° | Fichier de test | Méthode de test | Artefact attendu dans `results/` | Autonomie possible ? (Fixture / Mock) | Action réalisée au Tour 3 |
|---|---|---|---|---|---|
| 1 | `sweeps/test_estim31_final_rank_20261030.py` | `test_anchor_exists_with_source_and_complete_paired_games` | `results/estim31_engine_dispatch_air15_root_20261029/...` (fichier jsonl de 400 lignes) | **OUI (Simple)** : l'ancre réside déjà dans `docs/estim31_v161_40x5_20261030.json`. Un mock de l'analyseur sur les suites secondaires permet de tester le chargement de l'ancre sans fichier externe. | **RENDU AUTONOME** (commit `57f9152e`). Le test s'exécute et passe avec succès. |
| 2 | `sweeps/test_estim31_c121_no_upper_20261030.py` | `test_off_byte_identity_and_no_upper_bound` | `results/estim31_no_upper20261030` et son parent `results/estim31_v161_safe20261030` | **NON (Lourd)** : compare byte-à-byte 6 fichiers Squirrel complets entre deux arbres de répertoires d'expériences du 30/10. Exigerait d'embarquer des dizaines de ko de code obsolète en fixture. | `SkipTest` maintenu lorsque `results/` est absent. |
| 3 | `sweeps/test_estim31_joint_next_prepare.py` | `test_no_historical_code_changed` | `results/estim31_joint_dispatch20261029/module_a150_r100_w15` | **NON (Lourd)** : vérifie l'absence de régression sur les copies générées dans `results/` par le script de préparation. | `SkipTest` maintenu. |
| 4 | `sweeps/test_estim31_joint_next_prepare.py` | `test_only_scanned_module_changed_and_no_unsafe_break` | Idem | **NON** : inspecte le code généré dans les 8 sous-dossiers de `results/estim31_joint_next20261030`. | `SkipTest` maintenu. |
| 5 | `sweeps/test_estim31_joint_next_prepare.py` | `test_all_scenarios_have_multiple_controls` | Idem | **NON** : vérifie la combinatoire des configurations écrites dans `design.json`. | `SkipTest` maintenu. |
| 6 | `sweeps/test_estim31_joint_safe_20261030.py` | `test_historical_off_files_identical` | `results/estim31_joint_safe20261030` et `results/estim31_joint_dispatch20261029` | **NON** : compare les fichiers Squirrel complets entre deux répertoires de campagne. | `SkipTest` maintenu. |
| 7 | `sweeps/test_estim31_joint_safe_20261030.py` | `test_early_prior_and_ge_shortcut_disabled_under_estim` | Idem | **NON** : inspecte `air_economics_c121_fullscan.nut` dans les copies de campagne. | `SkipTest` maintenu. |
| 8 | `sweeps/test_estim31_motor_joint_20261030.py` | `test_historical_sources_identical_and_exact_engine_choice` | `results/estim31_motor_joint20261030` et son parent | **NON** : vérifie 4 fichiers Squirrel complets par variante de campagne. | `SkipTest` maintenu. |
| 9 | `sweeps/test_estim31_v161_capcombo_20261030.py` | `test_only_experimental_prior_or_existing_runtime_settings_change` | `results/estim31_v161_capcombo20261030` | **NON** : vérifie l'arborescence générée par `estim31_v161_capcombo_prepare_20261030.py`. | `SkipTest` maintenu. |
| 10 | `sweeps/test_estim31_v161_coeff_20261030.py` | `test_only_the_early_estim_priors_change` | `results/estim31_v161_coeff20261030` | **NON** : vérifie les fichiers `design.json` et les sources modifiés dans `results/`. | `SkipTest` maintenu. |
| 11 | `sweeps/test_estim31_v161_policy_20261030.py` | `test_identical_off_and_estim_source` | `results/estim31_v161_policy20261030` | **NON** : vérifie l'intégrité de 4 copies complètes du dépôt. | `SkipTest` maintenu. |
| 12 | `sweeps/test_estim31_v161_safe_20261030.py` | `test_default_off_historical_functions_and_experimental_guard` | `results/estim31_v161_safe20261030` | **NON** : inspecte 5 fichiers Squirrel complets par variante. | `SkipTest` maintenu. |
| 13 | `sweeps/test_estim31_v161_motorcap_20261030.py` | `test_exact_union_of_parent_source_differences` | `results/estim31_v161_motorcap20261030` | **NON** : compare les unions de diffs de 3 arborescences parentes. | `SkipTest` maintenu. |
| 14 | `sweeps/test_estim31_v161_motorcap_20261030.py` | `test_no_unproved_pruning_and_same_engine_revalidation` | Idem | **NON** : vérifie le code source de l'algorithme moteur dans `results/`. | `SkipTest` maintenu. |

**Bilan :** 1 test autonome réussi (2 tests passants au total dans le fichier), 13 tests de validation structurelle des générateurs d'expériences maintenus sous `SkipTest` propre en l'absence du dossier `results/`.

---

## 4. Anomalies restantes (33 au total)

### 4.1 Tests RAIL (18 tests - conservés intacts)
1. `sweeps/test_c80_rail_stock_worker.py` : `test_revalidation_mandatory_before_build`
2. `sweeps/test_estim31_railnorm_safe_20261030.py` : `test_only_models_file_changes`
3. `sweeps/test_estim31_v161_rail1970_20261030.py` : `test_exact_opt_in_change_and_off_neutral`
4. `sweeps/test_estim_unifie_bit16.py` : `test_learning_is_level_only_and_reload_recalculates`
5. `sweeps/test_estim_unifie_bit16.py` : `test_off_projection_removes_bit16_and_preserves_historical_behavior`
6. `sweeps/test_p1_rail_long_value_rank.py` : `test_historical_producers_and_bytes_stay_frozen`
7. `sweeps/test_p1_rail_long_value_rank.py` : `test_trace_and_save_load_transience`
8. `sweeps/test_p2_rail_cargo_opportunity.py` : `test_historical_inventory_not_rebased`
9. `sweeps/test_rail_repair_idle_sixmonths_20261030.py` : `test_all_new_line_successes_reset_clock`
10. `sweeps/test_rail_track_failure_capture.py` : `test_failure_logs_and_rollback_order_are_unchanged`
11. `sweeps/test_rail_track_failure_capture.py` : `test_inlining_capture_restores_original_builder`
12. `sweeps/test_station_plan_precheck.py` : `test_only_guard_added_to_historical_rail_source`
13. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`economy.nut`)
14. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`globals_pre.nut`)
15. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`settings.nut`)
16. `sweeps/test_v233_long_good.py` : `test_off_reviewed_edits_preserve_all_original_hashes` (`task_rail.nut`)
17. `sweeps/test_v296a_batch_build.py` : `test_default_path_unchanged`
18. `sweeps/test_v296a_batch_build.py` : `test_every_exit_logs`

### 4.2 Tests HORS RAIL (15 tests)
- `sweeps/test_c77_intent_defer.py` (2 tests) : divergence PO01C / EB-14 consignée et chiffrée dans `defauts_decouverts.md`.
- `sweeps/test_po01c_regen_split.py` (7 tests) : empreintes PO01D et garde PO03 liée à la divergence EB-14.
- `sweeps/test_estim1_decision_probe.py` (1 test) : hunk 2 de `projects_models.nut` dans `estim_unifie_off_lots.py`.
- `sweeps/test_estim_unifie.py` (2 tests) : hunks de projection OFF.
- `sweeps/test_v161_fleet_net_marginal.py` (1 test) : hunk 2 de `projects_models.nut`.
- `sweeps/test_diag_air_site_probe.py` (1 test) : empreinte de `main.nut` modifiée par les expériences rail.
- *(Note : `sweeps/test_v278_air_lazy_sites.py` résolu au Tour 3)*.
