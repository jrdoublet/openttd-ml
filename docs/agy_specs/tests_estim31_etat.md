# État des tests sous estim_unifie=31 (QUALITÉ-TESTS-ESTIM31)

Date de référence : 2026-11-07
Commit initial : `7e5ad9d4` (base `origin/master`)

## 1. Bilan initial

Exécution globale :
`python3 -m unittest discover -s sweeps -p 'test_*.py'`
Résultat initial :
- Total tests : **3849**
- Échecs (`FAIL`) : **83**
- Erreurs (`ERROR`) : **24**
- Ignorés (`skipped`) : **16**
- Échecs attendus (`expected failures`) : **2**
- Total anomalies : **107**

## 2. Classification par famille

### Famille A : Manque de dépendance optionnelle hôte (numpy) - RÉSOLU
- `test_demo_frontieres_temps_20261025.py` (7 erreurs initiales -> 0 erreur, 8 OK) : import optionnel de `numpy` protégé dans `sweeps/analyse_roi_predictors_20261021.py`.

### Famille B : Attente obsolète de défauts modifiés lors de ESTIM31 (`probes=2`, etc.) - RÉSOLU
- `test_v167_probes.py` (1 échec initial -> 0, 13 OK) : assertion alignée sur `probes=2` dans `info.nut`.
- `test_b9_air_catchment.py` (1 échec initial -> 0, OK) : assertion alignée sur `defaults["probes"] == 2` tout en vérifiant la désactivation du bit 20.
- `test_publication_probes_default.py` (2 échecs initiaux -> 0, 5 OK) : aligné sur `probes=2`.
- `test_signs_default_off.py` (1 échec initial -> 0, 4 OK) : aligné sur `probes=2` dans `info.nut`.

### Famille C : Plafonds AddSetting codés en dur obsolètes (historique 58 vs 68) - RÉSOLU
- `test_v246_fixed_policies.py` (1 échec initial -> 0, 6 OK) : assertion actualisée à `<= 68`.
- `test_v259_bridge_renew.py` (1 échec initial -> 0, 14 OK) : assertion actualisée à `== 68`.
- `test_v276_candidate_slices.py` (1 échec initial -> 0, 26 OK) : assertion actualisée à `<= 68`.
- `test_parameter_retirements_20261023.py` (1 échec initial -> 0, 4 OK) : assertion actualisée à `== 68`.

### Famille D : Hunks V233L / off_source dans `v233_long_good_legacy.py` et tests associés - RÉSOLU
- `v233_long_good_legacy.py` : enregistrement des SHAs d'entrée et projetés de `economy.nut`, `globals_pre.nut`, `settings.nut` post-merge.
- `test_v190_rail_double_build.py` (15 échecs initiaux -> 0, 18 OK).
- `test_v198_template_double.py` (4 échecs initiaux -> 0, 20 OK, vérification syntaxe directe).
- `test_v207_site_rank.py` (1 échec initial -> 0, 6 OK).
- `test_v307_sites.py` (2 échecs initiaux -> 0, 13 OK).

### Famille E : Hunks ESTIM-1 / projection OFF dans `estim_unifie_off_lots.py`, `estim_merged_off.py`, etc.
- `test_estim_unifie.py` (4 échecs)
- `test_estim_unifie_bit16.py` (2 échecs)
- `test_estim1_decision_probe.py` (1 échec)
- `test_v161_fleet_net_marginal.py` (1 échec)
- `invest_stall_platform_off.py` / `test_c77_intent_defer.py` (2 échecs)

### Famille F : Tests spécifiques ESTIM-31 / C121 / 20x10 rédigés pendant la transition
- `test_estim31_c121_dispatch.py` (4 échecs/erreurs)
- `test_estim31_c121_no_upper_20261030.py` (1 erreur)
- `test_estim31_final_rank_20261030.py` (1 erreur)
- `test_estim31_joint_next_prepare.py` (2 erreurs)
- `test_estim31_joint_safe_20261030.py` (2 erreurs)
- `test_estim31_motor_joint_20261030.py` (1 erreur)
- `test_estim31_railnorm_safe_20261030.py` (1 erreur)
- `test_estim31_v161_capcombo_20261030.py` (1 erreur)
- `test_estim31_v161_coeff_20261030.py` (1 erreur)
- `test_estim31_v161_motorcap_20261030.py` (2 échecs)
- `test_estim31_v161_policy_20261030.py` (1 erreur)
- `test_estim31_v161_rail1970_20261030.py` (1 échec)
- `test_estim31_v161_safe_20261030.py` (1 erreur)
- `test_estim31_20x10_priority_analysis.py` (1 échec)

### Famille G : Autres tests de contrats et assertions unitaires
- `test_b8_scrap_lifecycle.py` (2 erreurs)
- `test_c121_visible_target.py` (1 échec)
- `test_c80_rail_stock_worker.py` (1 échec)
- `test_diag_air_site_probe.py` (1 échec)
- `test_event_backlog_probe.py` (1 échec)
- `test_front_pax2_bounded_overlap.py` (1 échec)
- `test_m3_equipment_roi.py` (1 échec)
- `test_n75_multi_cargo.py` (1 échec)
- `test_normal_play_probe_gates.py` (1 échec)
- `test_p1_rail_long_value_rank.py` (2 échecs)
- `test_p2_rail_cargo_opportunity.py` (1 échec)
- `test_p3_air_fleet_yield.py` (1 échec)
- `test_po01c_regen_split.py` (autres échecs)
- `test_rail_repair_idle_sixmonths_20261030.py` (1 échec)
- `test_rail_track_failure_capture.py` (2 échecs)
- `test_sched_idle.py` (1 échec)
- `test_station_plan_precheck.py` (1 échec)
- `test_taches_reconciliation_20261030.py` (1 échec)
- `test_v147_air_catalog_tasks.py` (1 erreur)
- `test_v216_probe.py` (1 échec)
- `test_v252_engine_refresh.py` (2 échecs)
- `test_v278_air_lazy_sites.py` (1 échec)
- `test_v296a_batch_build.py` (2 échecs)
