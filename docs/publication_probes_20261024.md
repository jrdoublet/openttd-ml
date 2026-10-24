# Publication v8 — sondes et couverture des harnais (24 octobre 2026)

Demande utilisateur sur `publication-1`, depuis `origin/master` : défaut de publication
`probes=0` aux quatre difficultés, version 8, date 2026-10-24. Seul
`ai/OpexAI/info.nut` change dans le code IA. Mémo consulté :
`/home/deploy/.claude/projects/-home-deploy-projects-openttd-ml/memory/rappel_defaut_panneaux.md`
(décision du 18/10), rappel versionné dans `docs/reprise_20261019.md`.

## Provenance et identité

`benchmark_opex_settings` ajoute uniquement `probes=2` si absent ; tout masque
explicite reste inchangé, y compris 0 dans les diagnostics directs dédiés.
`run_c66_reference.inject_probes` conserve aussi les masques explicites, mais
refuse toujours un masque sans panneaux, comme `bench_v2`.
Le défaut CLI du lanceur est 2 ; un masque explicite plus large active également
`--script-debug` si nécessaire.

`effective_ai_settings` conserve les vrais `defaults` (0) et les affectations
`explicit` ; la valeur ajoutée figure dans `benchmark_injected` et dans
`effective`. Le lanceur hôte peut matérialiser cette valeur dans `explicit`.
Les différences d’intervention sont calculées après normalisation des deux bras.
Le socle exact `probes=2` est exclu des écarts explicites communs au défaut dans
`bench_v2` ; les autres masques restent audités. Ainsi `OpexAI` et
`OpexAI[probes=2]` restent identiques, sans masquer une différence réelle de masque.
Le validateur `qualification.py` accepte seulement cette normalisation à 2
en supplément du plan et exige toujours tous les autres défauts et interventions.
Les empreintes des sources et du bundle changent normalement ; aucun manifeste
historique ni résultat figé n’a été réécrit.

## Inventaire avant édition

Recherche `rg` sur `OpexAI\[`, `run_experiments`, `openttdlab` et `docker` dans
`sweeps/*.py`, `bench*.py`, `campaign_freeze*.py`, `.github/workflows/*.yml`
et `qualifications/`, puis inspection AST des appels `local_folder` et des imports.
Les simples mentions ont été distinguées des lancements réels.

### Couverture directe

`run_c66_reference.py` : fallback commun 2 avant Docker. `campaign_freeze.py` :
résolution commune et provenance. Les 44 constructeurs directs suivants passent
leurs paramètres OpexAI par `benchmark_opex_settings` (contrat AST ajouté) :

- `sweeps/bench_1v1_3y_10seeds.py`
- `sweeps/bench_1v1_5y_20seeds.py`
- `sweeps/bench_v2.py`
- `sweeps/diag_1v1_decisions.py`
- `sweeps/diag_1v1_monthly.py`
- `sweeps/diag_1v1_shared_monthly.py`
- `sweeps/diag_1v1_shared_timeline.py`
- `sweeps/diag_air_afail_6y_5seeds.py`
- `sweeps/diag_air_engine_delay.py`
- `sweeps/diag_air_vehicles.py`
- `sweeps/diag_airport_delay_engine.py`
- `sweeps/diag_b6_portfolio_causality.py`
- `sweeps/diag_b8_scrap_lifecycle.py`
- `sweeps/diag_c121_investment.py`
- `sweeps/diag_c121_postbuild.py`
- `sweeps/diag_c39_events.py`
- `sweeps/diag_c53_orders.py`
- `sweeps/diag_c60_town_rating_exposure.py`
- `sweeps/diag_c63_c58.py`
- `sweeps/diag_c69_duel_erosion.py`
- `sweeps/diag_c72_plane_choice_solo_5x6.py`
- `sweeps/diag_c78_lines_vs_aaa.py`
- `sweeps/diag_c96_air_site.py`
- `sweeps/diag_c98_vs_aaa_engines.py`
- `sweeps/diag_cash_early.py`
- `sweeps/diag_discards.py`
- `sweeps/diag_nuit_air_solo.py`
- `sweeps/diag_r19_air_recovery_engine.py`
- `sweeps/diag_r1_r3_mechanisms.py`
- `sweeps/diag_r21_freight_destination.py`
- `sweeps/diag_r22_retirement_engine.py`
- `sweeps/diag_r23_rail_quote_failure.py`
- `sweeps/diag_r9_basin_opcode.py`
- `sweeps/diag_unused_cash_1970_1972.py`
- `sweeps/generate_c66_control_fixture.py`
- `sweeps/head_to_head.py`
- `sweeps/opex_full_campaign.py`
- `sweeps/opex_two_trains_diag.py`
- `sweeps/run_c121_autopsy_frozen_trace.py`
- `sweeps/run_c121_cache_fixtures.py`
- `sweeps/run_c121_fleet_fixtures.py`
- `sweeps/run_c121_kdec_cold_contracts.py`
- `sweeps/run_c83_repair_fixtures.py`
- `sweeps/run_mechanism_fixtures.py`

### Couverture par délégation

Ces entrées passent par `bench_v2.build_arms`, `bench_1v1_5y_20seeds`,
`diag_cadence_duel` ou les lanceurs hôtes ci-dessus ; aucune injection YAML
dupliquée ne peut écraser un masque fourni par l’utilisateur :

- `sweeps/_tmp_host_c121_autopsy_frozen_trace.py`
- `sweeps/bench_c50b_physical.py`
- `sweeps/diag_c69_bottleneck_probe.py`
- `sweeps/diag_c80_projects_gap.py`
- `sweeps/diag_cadence_duel.py`
- `sweeps/diag_constants_binding.py`
- `sweeps/diag_family2_floors.py`
- `sweeps/diag_first_year_chrono.py`
- `sweeps/diag_first_year_chrono_c121.py`
- `sweeps/diag_homog_preselect.py`
- `sweeps/diag_opcode_exact.py`
- `sweeps/diag_opcode_profile.py`
- `sweeps/diag_p2_lifecycle.py`
- `sweeps/diag_p2bis.py`
- `sweeps/diag_p5_preplan.py`
- `sweeps/diag_parallel_integration.py`
- `sweeps/diag_sched_idle.py`
- `sweeps/diag_v89_projects_gap.py`
- `sweeps/duel_yearly_ratio.py`
- `sweeps/github_bench.py`
- `sweeps/github_qualification.py`
- `sweeps/pcal03_inventaire.py`
- `sweeps/run_c121_night_queue.py`
- `sweeps/run_m3_equipment_roi_5x6.py`
- `sweeps/run_m3_equipment_roi_host.py`
- `sweeps/run_m4_conformity.py`
- `sweeps/run_m4_conformity_host.py`
- `sweeps/save_load_roundtrip.py`
- `sweeps/smoke_test.py`

Workflows : `bench.yml` (github_bench), `ci.yml` (smoke_test),
`qualify.yml` (github_qualification). Commentaires de routage ajoutés.
`benchmark-regressions.yml` et `ai-review-contracts.yml` ne lancent que des
tests/contrats, sans parties. `qualifications/` ne contient actuellement aucun
plan JSON : le modèle README délègue à ces mêmes lanceurs et documente le socle.

### Hors injection OpexAI

Ces harnais lancent uniquement des adversaires ou des IA de diagnostic distinctes
(TerrainBenchProbe, TerrainValuateProbe, TerrainMapProbe, WaterGraphProbe,
WaterMemoryProbe, C119ApiSmoke, C119IncomeProbe, C121CapProbe) :

- `sweeps/bench.py`
- `sweeps/bench_c67_terrain.py`
- `sweeps/bench_c67_valuate.py`
- `sweeps/diag_c67_terrain.py`
- `sweeps/diag_c67_water.py`
- `sweeps/diag_water_memory.py`
- `sweeps/run_c119_income_api_smoke.py`
- `sweeps/run_c119_income_lookup.py`
- `sweeps/run_c121_air_capacity_catalog.py`

Lecteurs/protocoles hors ligne repérés par leurs mentions, sans nouveau lancement :

- `sweeps/compare_cd_cross_tree_c66.py`
- `sweeps/diag_b9_air_catchment.py`
- `sweeps/report_air_roi_renfort1_itt_campagne2_20261022.py`
- `sweeps/diag_air_selection_light.py`

**Non couverts volontairement** : `sweeps/archive/` (harnais historiques à
requalifier avant réutilisation), bundles/preuves et anciennes campagnes figées.
Aucun lanceur OpexAI direct actif de `sweeps/*.py` ne reste sans fallback.
La couverture est statique : aucune compatibilité moteur nouvelle n’est affirmée
pour les anciens diagnostics utilisant des réglages retirés.

## Tests et rebasages explicites

Nouveau `test_publication_probes_default.py` : cinq contrats (quatre difficultés,
métadonnées, injection/masques explicites/refus sans panneaux, provenance et
identité, inventaire AST des constructeurs directs).
`test_qualification.py` : acceptation du socle automatique ou matérialisé, refus
d’un autre masque commun non prévu par le plan.

Attentes du défaut 2 rebasées à 0 dans :

- `sweeps/test_v167_probes.py`
- `sweeps/test_signs_default_off.py`
- `sweeps/test_b9_air_catchment.py`
- `sweeps/test_c122_air_regime_priority.py`
- `sweeps/test_campaign_freeze.py`
- `sweeps/test_event_backlog_probe.py`
- `sweeps/test_m3_equipment_roi.py`
- `sweeps/test_sched_idle.py`

Le selftest de `bench_1v1_5y_20seeds.py` attend désormais le défaut publié 0.
`test_campaign_freeze.py` attend le fallback 2 dans le descripteur moteur et
teste explicitement le refus du défaut publié sans panneaux au banc.
`test_v167_probes.py` attend la conservation d’un masque explicite.

`test_po01c_regen_split.py` : seule l’empreinte `info.nut` est rebasée, avec
commentaire daté (version/date/probes). Cette empreinte était déjà obsolète avant
intervention ; les autres empreintes en échec restent intactes.

Suite complète exécutée avant/après avec code de sortie conservé et affichage des
trois dernières lignes. Journaux locaux `/tmp/publication_tests_before.log` et
`/tmp/publication_tests_final.log`. Résultats finaux consignés ci-dessous.

| Suite complète | Tests | Échecs | Erreurs | Skips | Échecs attendus |
|---|---:|---:|---:|---:|---:|
| Avant | 2 403 | 14 | 5 | 7 | 2 |
| Après | 2 409 | 13 | 5 | 7 | 2 |

Aucune régression ajoutée. Le seul échec disparu est l’empreinte `info.nut`
explicitement rebasée. Contrats publication : **5/5 OK** ; qualification :
**38/38 OK** (dont le nouveau contrat du socle). `git diff --check` propre.
Les échecs préexistants restants sont conservés, sans masquage :

- `ERROR: test_invalidation_follows_real_construction_only (test_air0310_6_site_validity_cache.TestAir0310SiteValidityCache.test_invalidation_follows_real_construction_only)`
- `ERROR: test_airr1_offline_postprocess_20261023 (unittest.loader._FailedTest.test_airr1_offline_postprocess_20261023)`
- `ERROR: test_analyze_air_load_shadow (unittest.loader._FailedTest.test_analyze_air_load_shadow)`
- `ERROR: test_audit_air_roi_renfort1 (unittest.loader._FailedTest.test_audit_air_roi_renfort1)`
- `ERROR: test_audit_air_roi_renfort1_itt (unittest.loader._FailedTest.test_audit_air_roi_renfort1_itt)`
- `FAIL: test_generators_track_current_producers (test_po01c_regen_split.PO01CContracts.test_generators_track_current_producers)`
- `FAIL: test_po01d_synchronous_path_bytes_unchanged (test_po01c_regen_split.PO01CContracts.test_po01d_synchronous_path_bytes_unchanged) (name='builder_water.nut')`
- `FAIL: test_po01d_synchronous_path_bytes_unchanged (test_po01c_regen_split.PO01CContracts.test_po01d_synchronous_path_bytes_unchanged) (name='air_sites.nut')`
- `FAIL: test_po01d_synchronous_path_bytes_unchanged (test_po01c_regen_split.PO01CContracts.test_po01d_synchronous_path_bytes_unchanged) (name='candidates.nut')`
- `FAIL: test_po01d_synchronous_path_bytes_unchanged (test_po01c_regen_split.PO01CContracts.test_po01d_synchronous_path_bytes_unchanged) (name='catalog.nut')`
- `FAIL: test_po01d_synchronous_path_bytes_unchanged (test_po01c_regen_split.PO01CContracts.test_po01d_synchronous_path_bytes_unchanged) (name='main.nut')`
- `FAIL: test_po01d_synchronous_path_bytes_unchanged (test_po01c_regen_split.PO01CContracts.test_po01d_synchronous_path_bytes_unchanged) (name='probes.nut')`
- `FAIL: test_po01d_synchronous_path_bytes_unchanged (test_po01c_regen_split.PO01CContracts.test_po01d_synchronous_path_bytes_unchanged) (name='settings.nut')`
- `FAIL: test_po01f_historical_dependencies_unchanged (test_po01c_regen_split.PO01CContracts.test_po01f_historical_dependencies_unchanged)`
- `FAIL: test_inlining_capture_restores_original_builder (test_rail_track_failure_capture.TestRailTrackFailureCapture.test_inlining_capture_restores_original_builder)`
- `FAIL: test_testmode_twin_is_unchanged (test_rail_track_failure_capture.TestRailTrackFailureCapture.test_testmode_twin_is_unchanged)`
- `FAIL: test_r9_opcode_compat_slots_remain (test_review_r6_r10_contracts.ReviewR6R10ContractsTest.test_r9_opcode_compat_slots_remain)`
- `FAIL: test_only_guard_added_to_historical_rail_source (test_station_plan_precheck.StationPlanPrecheck.test_only_guard_added_to_historical_rail_source)`

Les erreurs sont : un symbole WATER_OPCODE_COMPAT_FALSE absent du code testé,
un import OpenTTDLab manquant et trois imports pytest manquants. Aucune dépendance
installée pour modifier ce constat. Les autres échecs concernent les contrats
historiques/générateurs PO01C et rail, hors périmètre de publication.

Aucun Docker, partie, push, merge, modification de configuration Git ni variable
GIT_DIR/GIT_WORK_TREE exportée. Validation Squirrel/moteur non exécutée conformément
à la demande ; ces tests hôte ne prouvent ni compilation ni performance économique.
