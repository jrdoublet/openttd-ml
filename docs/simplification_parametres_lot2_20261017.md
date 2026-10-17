# Simplification des paramètres — lot 2 (préparation, 17/10/2026)

Suite de l'[inventaire du 16/10](inventaire_parametres_20261016.md). Le **lot 1** (en cours, branches
`v222-purge-air` agy et `v222-purge-terrain` grok) retire les 6 réglages « reliquat / effet absent »
et les constantes figées à `false` ; `air_p0_second_step_marginal` et `air_p0_margin_probe` sont
retirés par l'utilisateur.

Le lot 2 vise les **options OFF au défaut dont le verdict est déjà négatif ou nul** dans
`docs/taches.md`. Les retirer ne change pas le défaut : validation = contrats + smoke 1×1
(+ règle opcodes si le diff touche un chemin chaud). **Aucun retrait sans accord utilisateur
sur la liste** : un OFF n'est pas un réfuté (cf. légende de l'inventaire).

## Prérequis à trancher par l'utilisateur

1. **Fin de compatibilité `c121_air_economics=0`.** C121 est « définitivement adopté » (taches.md,
   12/10, retrait C119). Tant que le toggle existe, toute la famille C99–C115 reste atteignable
   ([plan C115](air_c115_cleanup_plan_20261010.md)). Décider : retirer le toggle C121 lui-même,
   puis toute la chaîne legacy AIR.
2. **Fil rail seul du 14/10** : les variantes V177–V194 ont été mesurées en rail seul 10×3 (bruit
   élevé). Les déclarer closes ou les garder comme briques d'expérience ?
3. **Sondes** (55 réglages `Sonde, OFF`) : hors lot 2. Ce ne sont pas des réglages morts ; une
   éventuelle fusion dans le masque `probes` est un chantier distinct.

## Lot 2A — AIR legacy pré-C121 (si prérequis 1 accepté)

| Réglages | Verdict | Source |
|---|---|---|
| `c99_air_speed_api_fix`, `c100_air_trip_physical`, `c101_…`, `c103_…`, `c105_…`, `c106_…`, `c108_…`, `c109_…`, `c110_…`, `c112_…`, `c114_air_c100_full_replay` (+ sondes C104, C111, C113) | Remplacés par C121 ; aucun consommateur sous C121=1 | plan C115 du 10/10 |
| `c121_air_economics` (toggle lui-même) | Adopté définitivement le 12/10 | taches.md l.85 |
| `c84_air_target_fleet` | Réfuté (−69,6 k£/an) | taches.md l.884 |
| `c85_air_equipment_frontier` | Caduc sous V96 | taches.md l.884 |
| `c122_air_threat_retry` | 40×5 `fail_primary` (−9,9 k£/an) | taches.md l.91 |
| `v133_air_build_retry` | Réfuté (porte A) | taches.md l.920 |
| `v134_air_p2p_saturated_hub` | Réfuté (porte A) | taches.md l.919 |
| `c83_local_repair` (+ `c83_fixes`, `c83_preempt_open` à vérifier) | 20×10 et 40×3 `fail_primary`, « prototype OFF conservé » | taches.md l.181, l.874 |

⚠️ Pièges connus : `C69_TRACK_BUILDS` et `c69BuildDates` (Save/Load) sont partagés ; ne garder
`OpexC104BestAirEngine`, `OpexC69ComputeKDec/CachedKDec` qu'après grep des appelants.

## Lot 2B — rail (si prérequis 2 accepté)

| Réglages | Verdict | Source |
|---|---|---|
| `v181_rail_max_trains` | 0 clonage, identique au bit près | taches.md l.1190 |
| `v185_rail_short_freight_pct` | Négatif (−44,7 k) | l.1186 |
| `v187_rail_refleet_during_search`, `v188_rail_join_slopes` | −126,7 k, 3/7 | l.1189 |
| `v190_rail_double_build`, `v190_rail_double_delay`, `v190_rail_max_trains` | Plantage puis nul ; défauts 0 maintenus | l.1191, 1202, 1339 |
| `v192_rail_time_denom_pct` | Nul confirmé | l.1203 |
| `v193_chain_towns` | Nul | l.1199 |
| `v194_short_to_served_dst` | Nul (−17 k) | l.1201 |
| `v131_rail_repair`, `v131_town_clearance` | Réfuté (porte A 40×5) | l.935 |
| `rail_cached_proximity_gate` | Porte A 40×5 `fail_primary` | l.877 |
| `rail_depot_cost` | 40×3 `fail_primary`, chantier différé | l.811 |
| `rail_origin_reuse` + 10 sous-réglages | Rail seul 10×3 neutre/négatif | l.1250 |

**À ne pas retirer sans avis** : `v180_*` (porte A échouée mais encore citée), `v182_*` (« reste
meilleure »), `v177_*`, `v207_*` (défauts sur branche V207), `v197/v198/v199/v200` (worktree
`wt-v197-dbl` vivant), `v163_multi_cargo` (« gros banc à faire »), `v171_rail_knots`,
`rail_geometry_*` (« non qualifié », pas réfuté).

## Lot 2C — autres réfutés

| Réglages | Verdict | Source |
|---|---|---|
| `capital_quote_learning` | Rejeté (P0 09/10) | l.214 |
| `v139_feeder_bus` | Réfuté (porte A 40×5) | l.931 |

À vérifier avant de proposer : `town_growth*`, `road_pax_build*`, `v88_*` (V218 a réutilisé V88),
`c80_*`, `air_efficiency_*`, `exp_*`, `v92/v93_*` (V93 plancher qualifié : ne pas confondre avec
`v93_air_demand_production`).

## Exécution proposée

- Un agent par lot, un worktree chacun, après fusion du lot 1 (mêmes fichiers `info.nut` /
  `settings.nut` : éviter les conflits). 2A et 2B touchent des fichiers disjoints hors
  `info.nut`/`settings.nut`, donc parallélisables ; 2C à l'un des deux.
- Même consigne qu'au lot 1 : garder exactement le défaut, refuser et justifier tout retrait qui
  toucherait Save/Load ou un appelant partagé, mettre à jour `sweeps/` (plans, tests de contrat),
  aucun banc lancé par l'agent.
- Validation par Claude : relecture du diff, contrats, smoke 1×1 ; pour 2A (gros retrait sur un
  chemin AIR), 20×10 neutre selon la règle opcodes avant fusion.

## Lot V232 (préparé le 17/10, en attente d'accord)

Trié à partir de l'inventaire des 226 réglages restants après V231. Ne sont retenus que les réglages à défaut 0 (ou neutres) dont un verdict négatif ou nul est écrit. Ensuite, comme pour V231 : défaut figé, branche inactive retirée et documentée au maximum dans `suppressions_parametres_idees_20261017.md`, smoke, puis 20×10 si le smoke diffère. **35 réglages, 226 → 191.**

### Rail (moi), 11 réglages
| Réglages | Verdict |
|---|---|
| `v88_goods_chain` + `v88_chain_force`, `v88_step2_plan_immediate`, `v88_all_inputs`, `v88_chain_step1_finance`, `v88_step2_rail_prio`, `v88_step2_cash_reserve` | Rail seul 10×3 (14/10) : −298,5 k£/an, 0/9, p = 0,004, valeur −60,8 %. **Garder** la jointure de quai V88 (`OpexJoinPlatformPlans`), qui sert à V178. |
| `c80_rail_stock_gate`, `c80_rail_stock_worker`, `c80_worker_rail` | Stock + worker en rail seul : −374,0 k£/an, 0/10, p = 0,002. V149 (stock + worker au reliquat) : porte A −73,6 k. Thème inerte au défaut (relecture du 12/10). L'idée « A* dans les workers » reste dans la fiche cible. |
| `rail_expand` | Rail seul 10×3 : −14,4 k, 4/4/2, nul. Rallonger les rames est réfuté ailleurs (V180, V204). |

### Villes et route (agy), 13 réglages
| Réglages | Verdict |
|---|---|
| `town_growth`, `town_growth_plan_memo`, `town_growth_skip_noop`, `town_growth_roi_gate`, `c80_worker_town` | Retest C121 : −8,08 %, IC95 négatif. Désactivé le 02/10 sur décision utilisateur. |
| `road_finance_unbias_p0`, `road_finance_gate_shadow_p0`, `road_quote_components_shadow_p0` | Biais route 121 % : retrait échoué en V102 A40×3 (`road_finance_unbias_p0_20261009.md`). Les deux ombres en dépendent. |
| `road_time_scaled_cap` | −0,41 %, IC95 [−31 ; +18] k : nul. |
| `policy_vehicle_events` | −1,06 % ; retrait aveugle des véhicules déficitaires jugé destructeur. |
| `project_top_k_dynamic` | 5×6 : −8,0 % en moyenne, 2/5. |
| `v139_feeder_bus` | Porte A 40×5 réfutée. Le calcul seul coûte −48,8 k£/an et −17,75 avions. Idée de rabattement reprise pour la réécriture (§9.3). |
| `road_pax_dwell_days` | Réglage numérique au défaut 6 : devient une constante (`ROAD_PAX_STOP_DWELL_DAYS`, toujours lue par `economy.nut`). |

### AIR (grok), 10 réglages
| Réglages | Verdict |
|---|---|
| `air_site_cost_quote`, `air_site_cost_margin_pct`, `air_site_quote_keep_legacy_margin` | V126, porte A 40×3 `fail_primary` : −92,7 k£/an, 20/20. |
| `c121_air_visible_competition`, `c121_air_visible_fused`, `air_fleet_c121_preguard` | Porte A 40×6 du 08/10 : −0,89 %. Défaut 0. V161 couvre le profit net de renfort. |
| `air_batch_town_reserve` | 5×6 du 24/09 : −179,9 k£/an. |
| `c82_engine_calibration` | Défaut 0 depuis C82. Moteur quasi fixe par partie (V96). |
| `c80_air_choice_memo`, `c80_air_eval_fast` | Opcodes divisés par deux mais profit en baisse sur 3 graines ; non retenus. |

### Écartés de ce lot
- Interdits ou mis de côté : `c67_*`, `v177`–`v182`, `v207_*`, `v190`/`v197`–`v200`, `rail_geometry_*`, `c122_*`, `c83_*`, `v133`/`v134`, `v131_*`, `rail_depot_cost`.
- Prometteurs ou en attente de décision : `c76_freight_rotation` (+61 k en rail seul), `v163_multi_cargo` (neutre, adoption à décider), `homogeneous_preselect` (+7 à +13 % de valeur sur des graines isolées).
- Verdict introuvable, à vérifier avant un lot ultérieur : `v171_rail_knots` (porte A du 13/10), `v183_rail_all_freight`, `v127_idle_cash_road_regen`, `c69_fleet_demand_batch`, `exp_air_hub_pair_prefilter`, `air_bfail_dispose_orphan`, `road_loading_fix` (+0,10 %, quasi inerte).
- Les sondes (`probe_*`, `*_shadow`) forment un lot à part : elles ne changent rien au comportement, mais leur retrait est à arbitrer (outils de diagnostic).

## Plan de nuit du 17→18/10 (préparé, en attente de validation)

Base : master après V232 (211 réglages). Six lots, **134 réglages, 211 → 77**. Pour chaque lot :
1. code (agent ou moi), en worktree depuis le master courant ;
2. contrats sans nouvel échec, puis smoke graine 42 ; fixture R1 si `tests/mechanisms/` est touché ;
3. smoke identique ⇒ master directement. Sinon 20×10 contre le lot précédent, **et** comparaison cumulée contre V230 (`v230_20x10_20261017`) ;
4. neutre ⇒ fusion, doc (§ par lot dans `suppressions_parametres_idees_20261017.md`), push ;
5. **non neutre** (p < 0,05 négatif, ou valeur < −5 %), ou **cumul contre V230 < −5 %** de profit ⇒ pas de fusion, lot documenté, on passe au suivant.

Un seul banc à la fois ; les agents codent en parallèle, sans Docker.

| Lot | Qui | Famille | Réglages |
|---|---|---|---|
| **V234** | agy | Villes et route : options OFF réfutées | `town_growth`, `town_growth_plan_memo`, `town_growth_skip_noop`, `town_growth_roi_gate`, `c80_worker_town`, `road_finance_unbias_p0`, `road_finance_gate_shadow_p0`, `road_quote_components_shadow_p0`, `road_time_scaled_cap`, `road_loading_fix`, `road_pax_dwell_days` (→ constante 6), `policy_vehicle_events`, `project_top_k_dynamic`, `v139_feeder_bus` (14) |
| **V235** | grok | Rail et AIR : options OFF réfutées ou jamais adoptées | `c80_rail_stock_gate`, `c80_rail_stock_worker`, `c80_worker_rail`, `rail_expand`, `v183_rail_all_freight`, `v171_rail_knots`, `v127_idle_cash_road_regen`, `c69_fleet_demand_batch`, `exp_air_hub_pair_prefilter`, `air_bfail_dispose_orphan`, `air_full_load`, `c72_plane_choice` (12). Les cinq sans verdict écrit sont signalés comme « jamais adoptés ». |
| **V236** | moi | Réglages numériques → constantes, même valeur | `pathfinder_sleep_ticks`, `rail_terrain_factor`, `rail_finance_bias_pct`, `v212_rail_pax_revenue_pct`, `v212_rail_pax_capital_pct`, `v214_rail_turn_cost`, `v214_rail_tight_turn_cost`, `loan_repay_floor_k`, `pathfinder_hard_cap_k`, `abandon_cooldown_days`, `project_top_k`, `air_early_slot_target_towns`, `air_early_slot_min_pop`, `air_early_slot_bonus_pct`, `air_fleet_cadence_days`, `v161_prior_own`, `v161_prior_neighbour`, `air_joined_stop_limit`, `air_pax_revenue_calibration_pct`, `air_hub_max_routes`, `unprofitable_streak_threshold`, `v91_astar_weight_pct`, `v172_rail_long_weight_pct`, `v172_rail_long_weight_dist`, `v168_rail_max_dist`, `c121_air_first_live_growth_phase_years` (26). Smoke identique attendu. ⚠️ Ces réglages ne seront plus modifiables au lanceur : un futur balayage devra rajouter le réglage. |
| **V237** | agy | Interrupteurs **adoptés** AIR/catalogue : branche OFF retirée | `air_site_min_catchment`, `c96_air_site_catchment`, `c117_lean_sampling`, `air_c121_physical_payment_days`, `c121_air_winner_fusion`, `c121_air_game_engine`, `c121_catalog_incremental`, `c121_catalog_air_first_year`, `c121_flat_bootstrap`, `c121_air_first_year_rail_prep`, `c121_air_one_or_two_planes`, `c121_air_first_live_growth`, `c121_air_project_realization_adaptive`, `air_p0_direct_realization`, `air_route_plane_selection`, `air_early_slot`, `air_fleet_cooldown_prefilter`, `air_fleet_routes_index`, `v161_fleet_net_marginal`, `c80_air_hub_index`, `c80_marginal_floor`, `v94_air_site_list`, `air0310_v96_shortcut_lean`, `air0310_one_two_fused`, `air0310_incremental_publish`, `air0310_hub_snapshot`, `air0310_site_validity_cache`, `v141_catalog_incremental`, `v147_air_catalog_tasks`, `ac04_extra_site_dedup`, `ac05_skip_unused_hub_income`, `ac06_c76_snapshot_ack`, `ac04_hub_usage_gate`, `air_publish_lazy_select` (34) |
| **V238** | grok | Interrupteurs **adoptés** cœur et rail : branche OFF retirée | `exp_opcode_exact`, `c69_decision_bottleneck`, `c69_fleet_exempt`, `c70_mode_calibration`, `c75_multi_build`, `c75_kpass_bypass`, `policy_caches`, `c76_regen_targeted`, `c80_mode_regen`, `v89_rail_search_throughput`, `v90_fast_pathfinder`, `v129_rail_astar_exact_opt`, `v184_rail_search_slots` (1 = un créneau), `v186_rail_search_slices`, `rail_upgrade_failure_memory`, `rail_end_jump_connect`, `incr_revalidate_index`, `rail_target_cargo_prefilter`, `subsidy_reselect_if_purged`, `select_bisect_insert` (20) |
| **V239** | moi | Sondes d'enquêtes closes et vérificateurs d'équivalence | `c97_air_c69_engine_probe`, `c98_air_realized_probe`, `c116_air_project_probe`, `c117_air_throughput_probe`, `c118_air_coverage_probe`, `c121_station_flux_probe`, `c121_air_economics_shadow`, `c121_air_first_live_shadow`, `c121_kpass_shadow`, `c121_kdec_cold_shadow`, `c121_air_pressure_probe`, `c121_air_engine_replay_shadow`, `b9_air_catchment_probe`, `b9_air_demand_shadow`, `v95_air_post73_probe`, `catalog_cost_probe`, `r19_fault_inject`, `rail_freight_select_shadow`, `air_bfail_precheck_shadow`, `air_site_stale_shadow`, `probe_air_finance_margin`, `probe_c121_engine_table`, `probe_air_engine_depth`, `exp_opcode_exact_check`, `v90_pathfinder_check`, `v129_rail_astar_check`, `v94_air_site_check`, `v141_catalog_incremental_check` (28) |

**Ordre** : V236 et V239 (moi), pendant que agy fait V234 puis V237 et grok V235 puis V238. Bancs dans l'ordre où les lots sont prêts. Durée estimée : 5 × 1 h 15 de bancs, plus le code, environ 8-9 h.

**Conservés volontairement** :
- options utilisateur : `probes`, `debug_signs`, `decision_log`, `save_full_state`, `mode_*`, `policy_air`/`rail`/`road`/`abandon`/`portfolio` (bancs rail seul) ;
- sondes génériques : `probe_events`, `probe_span_trace`, `probe_cost`, `probe_scheduler`, `probe_loop_ops`, `probe_event_backlog`, `probe_select_reject`, `probe_candidates_*`, `probe_catalogue`, `probe_rail_search`, `probe_vehicle_lost`, `probe_portfolio`, `rail_failure_audit`, `probe_rail_preastar`, `probe_rail_terrain` ;
- protégés ou mis de côté : `v93_airport_no_pop_floor`, V178/V179, V216/V217, `c122_*`, `c83_*`, `v133`/`v134`, `v131_*`, `rail_geometry_*`, `c67_*`, `v177`–`v182`/`v195`, `v207_*`, `v190`/`v197`–`v200`, `rail_depot_cost` ;
- en attente de décision : `v163_multi_cargo`, `c76_freight_rotation`, `homogeneous_preselect`, `c80_air_choice_memo`, `c80_air_eval_fast`.
