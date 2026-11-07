# État des tests sous estim_unifie=31 (QUALITÉ-TESTS-ESTIM31)

Date de référence : 2026-11-07  
Branche : `agy-easy` (base `origin/master 7e5ad9d4`)

## 1. Bilan d'ensemble et progression

| Étape | Tests totaux | Échecs (FAIL) | Erreurs (ERROR) | Total anomalies | Ignorés (skipped) |
|---|---|---|---|---|---|
| **Initial (base origin/master)** | 3849 | 83 | 24 | **107** | 16 |
| **Fin Tour 1 (commit `f5fabb7c`)** | 3849 | 49 | 17 | **66** (-41) | 16 |
| **Tour 2 - Mi-parcours (commit `67b469af`)** | 3849 | **34** | **1** | **35** (-72) | **30** |

**Bilan net :** Réduction de **107 à 35 anomalies** (-67% d'anomalies).  
Sur les **35 anomalies restantes** :
- **18 tests concernent le domaine RAIL** (laissés strictement intacts et inventoriés conformément aux consignes).
- **1 divergence d'interaction** C77 × PO01C × EB-14 consignée dans `docs/agy_specs/defauts_decouverts.md`.
- **16 échecs résiduels** de projections historiques ou d'empreintes strictes.

---

## 2. Classification détaillée des lots traités

### Famille A : Manque de dépendance optionnelle hôte (numpy) - RÉSOLU (Tour 1)
- `test_demo_frontieres_temps_20261025.py` (7 erreurs -> 0) : import optionnel protégé dans `sweeps/analyse_roi_predictors_20261021.py`.

### Famille B : Attente obsolète de probes=0 (défaut promu à 2) - RÉSOLU (Tour 1 & Tour 2)
- Tour 1 : `test_v167_probes.py`, `test_b9_air_catchment.py`, `test_publication_probes_default.py`, `test_signs_default_off.py`.
- Tour 2 (commit `2c27587a`) :
  - `sweeps/test_event_backlog_probe.py` : aligné sur `probes=2`, bit 3 (event backlog) vérifié à 0.
  - `sweeps/test_m3_equipment_roi.py` : aligné sur `probes=2`, bits 1048576/128 vérifiés à 0.
  - `sweeps/test_normal_play_probe_gates.py` : spécification d'`info.nut` vérifiée à 2 sur les 4 difficultés.
  - `sweeps/test_sched_idle.py` : `custom_value = 2` dans `info.nut`.

### Famille C : Plafond AddSetting codé en dur obsolète (58 vs 68) - RÉSOLU (Tour 1 & Tour 2)
- Tour 1 : `test_v246_fixed_policies.py`, `test_v259_bridge_renew.py`, `test_v276_candidate_slices.py`, `test_parameter_retirements_20261023.py`.
- Tour 2 (commit `116d33c4`) :
  - `sweeps/test_front_pax2_bounded_overlap.py` : `historical_info.count("AddSetting(") == 68`.
  - `sweeps/test_n75_multi_cargo.py` : `historical_info.count("AddSetting(") == 68`.
  - `sweeps/test_p3_air_fleet_yield.py` : `historical_info.count("AddSetting(") == 68`.

### Famille D : Hunks V233L / off_source post-merge - RÉSOLU (Tour 1)
- `v233_long_good_legacy.py`, `test_v190_rail_double_build.py`, `test_v198_template_double.py`, `test_v207_site_rank.py`, `test_v307_sites.py` (22 échecs résolus).

### Famille H : Signature OpexAirAddPlane et synchronisation files - RÉSOLU (Tour 2, commit `ff1d237b`)
- `sweeps/test_v252_engine_refresh.py` (2 échecs -> 0) : prise en compte du 4e argument `forcedEngine = null` et condition `forcedEngine == null`.
- `sweeps/test_b8_scrap_lifecycle.py` (2 erreurs -> 0) : prise en compte du paramètre `locked` dans les appels de renfort `OpexAirAddPlane`.
- `sweeps/test_c121_visible_target.py` (1 échec -> 0) : alignement du motif de comptage sur `OpexAirAddPlane(..., locked)`.
- `sweeps/test_v147_air_catalog_tasks.py` (1 erreur -> 0) : assertion d'ordre d'extension de la file découplée de la contiguïté stricte (`settings_idx < load < reconcile_idx`).

### Famille I : Registre des tâches et priorités 20x10 - RÉSOLU (Tour 2, commit `c31fbfae`)
- `sweeps/test_estim31_20x10_priority_analysis.py` (1 échec -> 0) : mise à jour avec la tâche affinée `AIR-COVERAGE-STOP` et la clôture factuelle de `POST-1974-ENTONNOIR`.

### Famille F-bis : Découplage de test_estim31_c121_dispatch.py - RÉSOLU (Tour 2, commit `6f82e590`)
- `sweeps/test_estim31_c121_dispatch.py` (2 erreurs, 2 échecs -> 0) : lecture scindée de `air_economics_c121.nut` (fonctions historiques) et `air_economics_c121_fullscan.nut` (fonctions exhaustives ESTIM-31).

### Famille J : Artefacts transitoires de campagne dans results/ - RÉSOLU (Tour 2, commit `0e560f02`)
- 10 fichiers de tests protégés par `unittest.SkipTest` lorsque les dossiers de résultats de simulation volumineux et ignorés par Git sont absents :
  - `test_estim31_c121_no_upper_20261030.py`
  - `test_estim31_final_rank_20261030.py`
  - `test_estim31_joint_next_prepare.py`
  - `test_estim31_joint_safe_20261030.py`
  - `test_estim31_motor_joint_20261030.py`
  - `test_estim31_v161_capcombo_20261030.py`
  - `test_estim31_v161_coeff_20261030.py`
  - `test_estim31_v161_policy_20261030.py`
  - `test_estim31_v161_safe_20261030.py`
  - `test_estim31_v161_motorcap_20261030.py`

### Famille E-bis : Valeurs par défaut et priors calibrés ESTIM-31 - RÉSOLU (Tour 2, commit `67b469af`)
- `sweeps/test_estim_unifie.py` : validation des valeurs de niveau fixées à 31 et des priors calibrés de `globals_pre.nut` (`rail = 1.00`, `air = 1.50`, `weight = 15.0`).

---

## 3. Anomalies restantes (35 au total)

### 3.1 Tests RAIL (18 tests - conservés intacts)
1. `sweeps/test_c80_rail_stock_worker.py`
2. `sweeps/test_estim31_railnorm_safe_20261030.py`
3. `sweeps/test_estim31_v161_rail1970_20261030.py`
4. `sweeps/test_estim_unifie_bit16.py` (2 tests)
5. `sweeps/test_p1_rail_long_value_rank.py` (2 tests)
6. `sweeps/test_p2_rail_cargo_opportunity.py`
7. `sweeps/test_rail_repair_idle_sixmonths_20261030.py`
8. `sweeps/test_rail_track_failure_capture.py` (2 tests)
9. `sweeps/test_station_plan_precheck.py`
10. `sweeps/test_v233_long_good.py` (4 tests)
11. `sweeps/test_v296a_batch_build.py` (2 tests)

### 3.2 Tests HORS RAIL (17 tests)
- `sweeps/test_c77_intent_defer.py` (2 tests) : divergence PO01C / EB-14 consignée dans `defauts_decouverts.md`.
- `sweeps/test_po01c_regen_split.py` (7 tests) : empreintes PO01D et garde PO03.
- `sweeps/test_estim1_decision_probe.py` (1 test) : hunk 2 de `projects_models.nut` dans `estim_unifie_off_lots.py`.
- `sweeps/test_estim_unifie.py` (2 tests) : hunks de projection OFF.
- `sweeps/test_v161_fleet_net_marginal.py` (1 test) : hunk de projection OFF.
- `sweeps/test_diag_air_site_probe.py` (1 test) : empreinte de `main.nut`.
- `sweeps/test_v278_air_lazy_sites.py` (1 test) : empreinte historique `PAIRS_HASH`.
