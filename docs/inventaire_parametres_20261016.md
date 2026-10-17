# Inventaire des paramètres déclarés par OpexAI — 16 octobre 2026

Source : `ai/OpexAI/info.nut` (277 `AddSetting`) et `ai/OpexAI/settings.nut` ; contrôle
statique des consommateurs `.nut` dans `ai/OpexAI/`. État lu sur HEAD `d80fa01b`.
Les quatre difficultés ont les mêmes valeurs par défaut. Le rôle reprend la description
déclarée dans `info.nut`, abrégée si très longue (en anglais, pour fidélité aux sources).

**Lecture de la colonne « encore actif ? » :**
- **Oui, défaut actif** : la fonctionnalité/branche est activée par défaut (une garde de runtime peut toujours empêcher son exposition dans une partie donnée).
- **Option, OFF** : paramètre bien chargé avec une branche de code disponible, mais valeur alternative désactivée au défaut ; cela ne signifie pas qu’il est inutile ou qualifié.
- **Conditionnel** : paramètre dépend d’un autre interrupteur. « Oui, conditionnel » signifie que ce parent est activé par défaut, « Non au défaut » qu’il est éteint.
- **Sonde** : diagnostic seulement, activable directement ou par le masque `probes`, qui vaut 2 (panneaux seuls) par défaut.
- **Reliquat** : variable chargée mais sans consommateur métier trouvé ; **effet absent/contourné** : les branches peuvent encore exister sans produire l’effet annoncé au défaut.

| Paramètre | Défaut | Rôle (description déclarée) | Encore actif ? |
|---|---:|---|---|
| `probes` | 2 | Diagnostics bitmask: 0 none, 1 everything except 256 (signs, log, groups 8-128), 2 signs (défaut), 4 decision log, 8 opcodes/scheduler, 16 air, 32 rail, 64 road/water/costs, 128… | Oui : panneaux (masque 2) |
| `debug_signs` | 1 | Diagnostic signs on the map: 1 = current behaviour (required by sweeps/), 0 = none (use when playing with humans) | Oui : panneaux (veto de `probes`) |
| `decision_log` | 0 | Emit structured decision log lines via AILog: 1 = enabled, 0 = disabled (défaut) | Sonde, OFF (activable) |
| `air_p0_margin_probe` | 0 | Passive P0 AIR purchase and portfolio alternative logs, no decision changes; 0 = off (défaut) | **Non — reliquat** |
| `air_p0_second_step_marginal` | 0 | P0 test: use actual C121 model P(3)-P(2) for cold fleet 2->3 instead of reusing P(2)-P(1); 0 = off (défaut) | **Non — reliquat** |
| `save_full_state` | 1 | Persist the full decision state in savegames: 1 = save built lines and scheduler state (défaut), 0 = minimal payload | Oui, défaut actif |
| `pathfinder_sleep_ticks` | 0 | Ticks slept after each 50-iteration A* chunk: 0 = no self-handicap (défaut), 1+ = yield more often (with humans) | Oui : valeur de référence ou neutre (modifiable) |
| `probe_cost` | 0 | Enable construction cost probes (rail, air, road) comparing modelled vs real expense; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `capital_quote_learning` | 0 | P0: learn completed build quote/actual capital by construction family; keeps cash reserves separate; 0 = off (défaut) | Option, OFF au défaut |
| `road_finance_unbias_p0` | 0 | P0 isolated ROAD finance experiment: replace 121% by 100% of unchanged physical quote, preserving reserves; 0 = historical (défaut) | Option, OFF au défaut |
| `road_finance_gate_shadow_p0` | 0 | P0 passive ROAD finance gate comparison 121% vs 100% on identical generated projects; log only, 0 = off (défaut) | Sonde, OFF (activable) |
| `road_quote_components_shadow_p0` | 0 | P0 passive ROAD physical command-tariff quote and AIAccounting phase costs after siting; log only, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_scheduler` | 0 | Enable scheduler opcode, latency and idle-tour diagnostic ledgers (C41, C39, V95); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_loop_ops` | 0 | Log yearly opcode aggregates of the main loop (events, C117 sampler, orchestrator, Sleep leftover); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_span_trace` | 0 | Log dated nested spans of OpexAI micro-tasks (ticks and opcodes); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_c121_engine_table` | 0 | Log already-computed C121 engine scans and plan context for an offline engine table; 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_air_engine_depth` | 0 | Shadow only: on C121 full engine scans, score the N=1 runner-up at N=1 and N=2 with the fused kernel and log AIR_ENGINE_DEPTH; the V96 shortcut is unchanged; decisions unchanged; 1 = on,… | Sonde, OFF (activable) |
| `probe_air_finance_margin` | 0 | Exposure only: log AIR_FINANCE_TRY at air cash checks and AIR_FINANCE_FIRST_REVENUE/AIR_FINANCE_PENDING on built air lines; decisions unchanged; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_event_backlog` | 0 | Monthly probe of _processEvents burst sizes and opcode consumption; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_select_reject` | 0 | Probe: log SELECT_REJECT for candidate air projects dropped by cash, floor, dedupe or top-k truncation; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `exp_opcode_exact` | 1 | Exact opcode paths for road planning, air fleet sort, catchment and joined stops; 1 = on (défaut), 0 = historical | Oui, défaut actif |
| `exp_opcode_exact_check` | 0 | Run historical and exact opcode paths, log mismatches and opcode sums, keep the historical result; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `catalog_cost_probe` | 0 | Log catalog refresh and project generation costs; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `fleet_amort_shadow_probe` | 0 | Diagnostic only: 0 off, 1 added-aircraft amortisation shadow calculation, 2 full election snapshots; never changes decisions | Sonde, OFF (activable) |
| `r19_fault_inject` | 0 | TEST ONLY: force a rollback of the Nth new AIR route after its planes started (R19 recovery); 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_candidates_road` | 0 | Enable road candidate generation opcode profiling (pax, freight, town, feeder); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_candidates_rail` | 0 | Enable rail candidate generation profiling (pax, freight, speed, cruise, economics); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_catalogue` | 0 | Enable catalogue invalidation and engine availability probes (C39, C41); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_rail_search` | 0 | Enable rail A* search state probes (domination, fallthrough, cadence); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_vehicle_lost` | 0 | Enable vehicle lost and topology diagnostic probes (C41); 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_portfolio` | 0 | Enable portfolio, tension, scarcity and treasury chronological probes; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `rail_freight_select_shadow` | 0 | Diagnostic only: log freight rail cash, floor and final selection counts; 0 = off (défaut) | Sonde, OFF (activable) |
| `c69_fleet_demand_batch` | 0 | C69: allow air fleet expansion batch size to match measured waiting demand without the 4-plane cap; 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `c69_decision_bottleneck` | 1 | C69: rank projects by P/max(C, F*tau), F = operating cash flow, tau = days per build; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `c69_fleet_exempt` | 1 | C69 bis: fleet projects (planes added to an existing line) keep P/C under c69_decision_bottleneck, since they build nothing; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `c70_mode_calibration` | 1 | C70: scale predicted profit by a per-mode realised/predicted factor measured on own mature lines; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `c72_plane_choice` | 0 | C72: air plane choice per route; 0 = max profit (C68, défaut), 1 = max ROI, 2 = max P/max(C, K_dec) | Oui : valeur de référence ou neutre (modifiable) |
| `c84_air_target_fleet` | 0 | C84: keep current aircraft choice and 1-plane initial build, remember its profitable target fleet and use live marginal economics for demand-backed growth; 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `c85_air_equipment_frontier` | 0 | C85: prefilter route aircraft to the structurally non-dominated compatible frontier before C68 economics; 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `c83_local_repair` | 0 | Experimental C83: repair only the threatened town airport site, reuse known partner sites; fall back to targeted regeneration if no valid partner is known | Option, OFF au défaut |
| `c83_fixes` | 0 | C83 review fixes (contestable watch towns, slot-town identity, rearmable race, skip dead air pairs, targeted site scan): 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `exp_scheduler_skip_not_due` | 0 | Experimental P7: skip already completed report/repay tasks within one bounded scheduler scan; défaut off | Option, OFF au défaut |
| `exp_air_hub_pair_prefilter` | 0 | Experimental: skip hub pairs already linked by an AIR line before expensive route evaluation; défaut off | Option, OFF au défaut |
| `c83_preempt_open` | 0 | C83: keep one empty large town (both airport slots free) as a defensive new-airport target ahead of hub-to-hub, still subject to the profit test: 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `air_batch_town_reserve` | 0 | Air batch: fund at most one air project per new-airport town (reuse ends ignored); displaced plans stay in the pool: 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `v92_air_service_choice` | 0 | V92: choose an air service (engine x count) plus a cheap one-aircraft variant of the same route, and allow later re-equipment; 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `v93_airport_no_pop_floor` | 1 | V93: a town under 600 people can take a large airport when route economics pass, down to 100 people; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `v93_air_demand_production` | 0 | V93.1: air demand from last-month passenger production, competitor share and a per-line cap, at both ends; 1 = on, 0 = off (défaut). Independent of v93_airport_no_pop_floor | Option, OFF au défaut |
| `v95_air_post73_probe` | 0 | V95: passive annual diagnostic of post-1973 AIR opportunities rejected by population floor or served-town filters; 1 = probe, 0 = off (défaut) | Sonde, OFF (activable) |
| `v134_air_p2p_saturated_hub` | 0 | V134: allow a second airport in point-to-point (newpair) to a free town when existing airport reached air_hub_max_routes and town opens a 2nd slot; 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `v133_air_build_retry` | 0 | V133: quarantine an AIR town for 730 days after a local-authority refusal, a non-flat or invalid footprint, an unbuildable site or a town station cap, and keep lot pairs that do not use… | Option, OFF au défaut |
| `air_site_min_catchment` | 1 | V125: refuse an AIR site whose catchment produces no passengers or accepts none (acceptance < 8), instead of building a dead airport; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `air_site_cost_quote` | 0 | V126: add the levelling quote and modelled joined-stop cost of new airports to C121 AIR capital, and size the finance margin to the residual risk; requires c121_air_economics; 0 = off… | Option, OFF au défaut |
| `air_bfail_dispose_orphan` | 0 | BFAIL diagnostic: dispose of a newly built A via existing R19 rollback when B fails, even with infrastructure upkeep off; never removes reused hubs; 0 = retain (défaut) | Option, OFF au défaut |
| `air_bfail_precheck_shadow` | 0 | BFAIL passive probe: test B before spending on A for two-new-airport plans, log the verdict against the real build without rejecting; 0 = off (défaut) | Sonde, OFF (activable) |
| `air_site_cost_margin_pct` | 0 | V126 residual-risk margin, percent of the new-airport site cost (catalogue price + levelling quote) added to a 2,000 floor; used only when air_site_cost_quote=1 | Option OFF (requiert `air_site_cost_quote=1`) |
| `air_site_quote_keep_legacy_margin` | 0 | Diagnostic V126: with air_site_cost_quote=1, keep the historical 2000/12000/30000 AIR cash margin instead of residual-risk margin; 0 = off (défaut) | Option OFF (requiert `air_site_cost_quote=1`) |
| `air_site_stale_shadow` | 0 | Diagnostic only: re-quote selected new AIR sites before cash/build, log outdated quotes and financing exposure; no decision changes; 0 = off (défaut) | Sonde, OFF (activable) |
| `c96_air_site_catchment` | 1 | C96: choose among a bounded set of buildable AIR anchors by passenger-producing catchment tiles, without changing route demand/economics; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `c97_air_c69_engine_probe` | 0 | C97 passive probe: direct argmax over compatible AIR engine x fleet depth using calibrated P/max(portfolio capital, K_dec); no decision change | Sonde, OFF (activable) |
| `c98_air_realized_probe` | 0 | C98 passive probe: compare predicted versus realised AIR profit/revenue per aircraft, ratings and utilisation by engine/line; no decision change | Sonde, OFF (activable) |
| `c99_air_speed_api_fix` | 0 | C99: use AIEngine.GetMaxSpeed directly in AIR economics because NoAI already applies vehicle.plane_speed; 1 = corrected, 0 = legacy extra /4 (défaut) | Option, OFF au défaut |
| `c100_air_trip_physical` | 0 | C100: AIR trip time uses NoAI engine speed directly plus physical airport taxi/runway/vertical maneuver time; 1 = enabled, 0 = legacy (défaut) | Option, OFF au défaut |
| `c101_air_physical_engine_choice` | 0 | C101: among AIR engines using no more legacy capital than the C68 winner, rank by C100.1 physical profit, then return legacy route economics for admission/project scoring; 1 = enabled, 0… | Option, OFF au défaut |
| `c103_air_c100_rank_replay` | 0 | C103: replay the first positive C100 engine ranking only, while returning legacy route economics for admission/project scoring; 1 = enabled, 0 = legacy (défaut) | Option, OFF au défaut |
| `c104_air_c100_compare_probe` | 0 | C104 passive probe: compare legacy, first positive C100 replay and C100.1 AIR engine economics on identical route contexts; no decision change | Sonde, OFF (activable) |
| `c105_air_replay_choice_physical_economics` | 0 | C105: C100.1 physical AIR economics everywhere, but rank route engines with the first positive C100 replay objective; 1 = enabled, 0 = défaut | Option, OFF au défaut |
| `c106_air_marginal_physical_engine_choice` | 0 | C106: choose AIR engine by relative marginal return under C100.1 timing, while keeping legacy route economics for portfolio scoring; 1 = enabled, 0 = défaut | Option, OFF au défaut |
| `c108_air_onestep_physical_economics` | 0 | C108: C100.1 physical AIR economics everywhere, with one-step relative marginal-return engine choice; no cash or EngineID threshold; 1 = enabled, 0 = défaut | Option, OFF au défaut |
| `c109_air_speed_elasticity_physical` | 0 | C109: C100.1 physical AIR economics plus relative speed-profit elasticity engine choice (threshold 0.5); 1 = enabled, 0 = défaut | Option, OFF au défaut |
| `c110_air_engine_calibration_choice_only` | 0 | C110: learn C82 realised/predicted factors per AIR engine and use them only for route engine choice; keep C70 project scoring unchanged; 1 = enabled, 0 = défaut | Option, OFF au défaut |
| `c111_air_c100_decision_shadow` | 0 | C111 diagnostic: replay first positive C100 engine ranking, keep C68 decision economics/score, but finance/build the actually selected engine; 1 = enabled, 0 = défaut | Sonde, OFF (activable) |
| `c112_air_speed_elasticity_e75_physical` | 0 | C112: C100.1 physical AIR economics plus relative speed-profit elasticity engine choice (threshold 0.75); no cash or EngineID threshold; 1 = enabled, 0 = défaut | Option, OFF au défaut |
| `c113_air_c100_full_decision_shadow` | 0 | C113 diagnostic: C111 plus C68 shadow for AIR pre-admission; selected C100-replay engine still supplies real capital/fleet/build feasibility; 1 = enabled, 0 = défaut | Sonde, OFF (activable) |
| `c114_air_c100_full_replay` | 0 | C114 diagnostic: replay the first positive C100 globally (NoAI direct speed plus historical maneuver helper) in AIR route economics and engine choice; 1 = enabled, 0 = défaut | Option, OFF au défaut |
| `c115_air_c100_capital_replay` | 1 | C115: use first-C100 replay AIR economics only while the normal C68 route capital exceeds endogenous C69 K_dec; otherwise keep C68; 1 = enabled (temporary défaut), 0 = disabled | **Résiduel** (sélection principale sous C121) |
| `c116_air_project_probe` | 0 | C116 passive lightweight probe: reuse C115/C68 engine scan to measure AIR/global/self project unlock opportunity; no decision change; 1 = enabled, 0 = défaut | Sonde, OFF (activable) |
| `c117_air_throughput_probe` | 0 | C117 passive AIR throughput probe: completed-leg passengers, offered seats, cadence, waiting/rating and realised vehicle economics in 30-day line-age windows; no decision change | Sonde, OFF (activable) |
| `c117_lean_sampling` | 1 | V159 opcode optimization: 0 = legacy C117 sampler; 1 = lean sampling when probe is off (skips unused fields, AIAirport calls and string flush; défaut since 2026-10-13, V159 porte B… | Oui, défaut actif |
| `c121_station_flux_probe` | 0 | Passive PASS station balance: loading increases, queue changes, unknown losses and transfer risks; no fleet decisions; 0 = off (défaut) | Sonde, OFF (activable) |
| `c121_air_visible_competition` | 0 | Experimental PASS capture from visible rival airport tiles, equal-rating prior; common new/hub/live fleet demand; 0 = défaut | Option, OFF (requiert C121) |
| `c121_air_visible_fused` | 0 | Experimental live visible fleet quote: capture N/N+1 during target scan; requires visible competition; 0 = défaut | Option OFF (requiert `c121_air_visible_competition=1`) |
| `air_c121_physical_payment_days` | 1 | AIR C121: compute cargo payment age from physical one-way flight and airport manoeuvre time; 1 = on (défaut), 0 = C119 distance+30 proxy | Oui, défaut actif |
| `c118_air_coverage_probe` | 0 | C118 passive probe: log actual AIR catchment town coverage without changing decisions; 0 = off (défaut) | Sonde, OFF (activable) |
| `c121_air_economics_shadow` | 0 | C121 passive AIR economics shadow: B9 cargo-specific PASS/MAIL demand, directional carried volume, physical cycle and C119 payment; no decision change; 0 = off (défaut) | Sonde, OFF (activable) |
| `c121_air_economics` | 1 | C121 unified AIR economics for engine/project decisions; supersedes the C115 economic replay; 1 = on (défaut since 2026-10-07) | Oui, défaut actif |
| `c121_air_winner_fusion` | 1 | C121 opcode optimization: retain opening N=1 during the winner fleet scan; monthly tariff changes and AAA_LINE fall back; requires C121 economics; 1 = on (défaut) | **Oui, conditionnel** (`c121_air_economics=1` satisfait) |
| `c121_air_game_engine` | 1 | C121 opcode optimization: reuse the established aircraft of the current game per airport type and skip the engine scan; 1 = on (défaut since 2026-10-03, opcode neutrality rule), 0 = full… | **Oui, conditionnel** (`c121_air_economics=1` satisfait) |
| `c121_catalog_incremental` | 1 | Incremental C121 AIR plan economics and bounded catalog slices; requires c121_air_economics; 1 = on (défaut since 2026-10-07) | **Oui, conditionnel** (`c121_air_economics=1` satisfait) |
| `c121_catalog_air_first_year` | 1 | With incremental C121, generate only AIR candidates through the first game year; 1 by défaut, 0 = off | **Oui, conditionnel** (`c121_catalog_incremental=1 + mode_air=1` satisfait) |
| `c121_flat_bootstrap` | 1 | With incremental C121, skip the staged bootstrap: start in the complete stage so every post-build regeneration is the incremental C121 update instead of a synchronous full rebuild; 1 by… | **Oui, conditionnel** (`c121_catalog_incremental=1` satisfait) |
| `c121_air_first_year_rail_prep` | 1 | With air-only first year, when no living AIR project is fundable and no rail search is running, prepare up to 3 rail routes (catalog through segmented A*) without building them; 1 by… | **Oui, conditionnel** (`c121_catalog_air_first_year=1 + mode_rail=1` satisfait) |
| `c121_air_one_or_two_planes` | 1 | With C121 economics, score only fleet depths N=1 and N=2 and build the better one; N=2 starts the second aircraft from airport B toward A, without changing full-load orders; 1 by défaut,… | **Oui, conditionnel** (`c121_air_economics=1` satisfait) |
| `c121_air_first_live_shadow` | 0 | C121 cadence shadow: log passive 60/90-day live evidence for AIR lines still at one plane; never changes reinforcement decisions; 0 = off (défaut) | Sonde, OFF (activable) |
| `c121_air_first_live_growth` | 1 | C121 cadence: advance only AIR 1->2 when balanced 90-day live evidence is positive; target, portfolio arbitration and later reinforcements stay unchanged; 1 = on (défaut), 0 = off | **Oui, conditionnel** (`c121_air_economics=1` satisfait) |
| `c121_air_first_live_growth_phase_years` | 4 | With first-live growth, use the live 1->2 early override only during this many opening game years; 4 = défaut, 0 = all years | **Oui, conditionnel** (`c121_air_first_live_growth=1` satisfait) |
| `c121_kpass_shadow` | 0 | C121 cadence shadow: log each portfolio pass stop with blocking project and a bounded look-ahead of following project modes/finance; never changes decisions; 0 = off (défaut) | Sonde, OFF (activable) |
| `c121_kdec_cold_shadow` | 0 | C121 cadence shadow: for fleet projects with zero real marginal samples, log current K_dec rank versus the counterfactual C69 fleet exemption; never changes decisions; 0 = off (défaut) | Sonde, OFF (activable) |
| `c121_air_project_realization_adaptive` | 1 | C121 adaptive AIR strategy: use the learned reused-hub realization correction in observe, race and efficiency; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `air_p0_direct_realization` | 1 | Validated AIR P0: use mature observed C121 hub revenue ratios directly; 1 = on (défaut), 0 = legacy smoothing | Oui, défaut actif |
| `c121_air_pressure_probe` | 0 | C121 passive AIR competition-pressure probe over already-inspected slot towns; no map scan and no decision change; 0 = off (défaut) | Sonde, OFF (activable) |
| `c121_air_defensive_floor` | 0 | C121 protected experimental setting: defensive AIR floor uses 50% competitor-slot / 75% own-slot, currently neutralized by the global zero floor; branch still runs with C121 enabled and… | **Effet absent ou contourné au défaut** |
| `c121_air_engine_replay_shadow` | 0 | C121 passive engine/fleet economics replay using only observed exact PASS/MAIL capacities; no decision change; 0 = off (défaut) | Sonde, OFF (activable) |
| `c122_air_regime_shadow` | 0 | C122 passive shadow: run the same pressure lock, unserved-town annotation and AIR-vs-AIR comparison as C122, but never reorder projects; logs only would-be economic inversions; 0 = off… | Sonde, OFF (activable) |
| `c122_air_threat_probe` | 0 | C122.4 passive territorial-threat probe: when C83 sees one slot remaining in an unserved watched town, record the exact live/fundable AIR project, rank and blocker, then follow the same… | Sonde, OFF (activable) |
| `c122_air_threat_retry` | 0 | C122.4 experimental local retry: if an exact C83 threatened AIR project reaches build but its threatened endpoint site became unbuildable, enqueue one targeted C77 regeneration for that… | Option, OFF au défaut |
| `v88_goods_chain` | 0 | V88: complete goods industrial chains (input feeder line to transformer + goods delivery line to town); 1 = on, 0 = off (défaut) | Option, OFF au défaut |
| `v88_chain_force` | 0 | V88 test only: under v88_goods_chain, goods chain projects bypass top-K, profit floor and ranking to validate their construction path: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `v88_goods_chain=1`) |
| `v88_step2_plan_immediate` | 0 | V88: allow goods chain step 2 to build when railPlan is already computed, without waiting for railSearch to be idle: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `v88_goods_chain=1`) |
| `v88_all_inputs` | 0 | V88: evaluate all transformer input cargos regardless of freight rotation: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `v88_goods_chain=1`) |
| `v88_chain_step1_finance` | 0 | V88: finance capital of goods chain candidate based on step 1 only: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `v88_goods_chain=1`) |
| `v88_step2_rail_prio` | 0 | V88: priority for chain rail searches: block new rail searches while step 2 is pending, and throughput slice cap: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `v88_goods_chain=1`) |
| `v88_step2_cash_reserve` | 0 | V88: reserve capital for goods chain step 2 when step 1 is built: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `v88_goods_chain=1`) |
| `air_full_load` | 0 | C81: air full-load orders; 0 = none (défaut), 1 = full load at both airports, 2 = full load at the first airport only (AAAHogEx défaut) | Oui : valeur de référence ou neutre (modifiable) |
| `c82_engine_calibration` | 0 | C82: scale predicted air profit by a per-aircraft-engine realised/predicted factor from own mature air lines, instead of the C70 air factor (project ranking and aircraft choice per… | Option, OFF au défaut |
| `c75_multi_build` | 1 | C75: multi-build per pass in rich phase as long as capital < K_pass and capital <= available; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `c75_kpass_bypass` | 1 | C75 bis: allow at most one financeable new-line project per projects pass to bypass K_pass; fleet projects never qualify; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `probe_events` | 0 | Enable AI event, crash, fleet depth and equipment selection probes; 1 = on, 0 = off (défaut) | Sonde, OFF (activable) |
| `b9_air_catchment_probe` | 0 | B9/G4 passive AIR catchment/placement probe only; no decision change; 1 = enabled, 0 = off (défaut) | Sonde, OFF (activable) |
| `b9_air_demand_shadow` | 0 | B9/G4 passive pre-build AIR demand shadow; logs only, no decision change; 1 = enabled, 0 = off (défaut) | Sonde, OFF (activable) |
| `policy_caches` | 1 | C41 and portfolio performance caches and spatial indexing: 1 = enabled (défaut), 0 = off | Oui, défaut actif |
| `air_route_plane_selection` | 1 | C68 AIR policy: for an otherwise identical route, choose the compatible aircraft with the highest predicted annual profit; 1 = adopted route-specific choice/défaut, 0 = historical… | Oui, défaut actif |
| `policy_rail` | 1 | Rail construction and operations: resumable A*, quotes, refleet, orders: 1 = enabled (défaut), 0 = off | Oui, défaut actif |
| `policy_road` | 1 | Road transport policy: drive-through stops on existing streets, overlap filtering: 1 = enabled (défaut), 0 = off | Oui, défaut actif |
| `mode_air` | 1 | V166: Air mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (défaut) | Oui, défaut actif |
| `mode_rail` | 1 | V166: Rail mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (défaut) | Oui, défaut actif |
| `mode_road` | 1 | V166: Road (buses, trucks, airport feeder buses) mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (défaut) | Oui, défaut actif |
| `mode_water` | 1 | V166: Water (ships, docks) mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (défaut) | Oui, défaut actif |
| `v185_rail_short_freight_pct` | 0 | V185: predicted revenue of rail freight lines shorter than 100 tiles scaled to N% (realised/predicted calibration); 0 = inert (défaut) | Option, OFF au défaut |
| `v183_rail_all_freight` | 0 | V183: rail freight generation covers every freight cargo at once instead of one cargo per pass; 0 = inert (défaut) | Option, OFF au défaut |
| `v182_rail_freight_min_dist` | 0 | V182: minimum distance in tiles for rail freight candidates (generation filter); 0 = inert (défaut) | Option, OFF au défaut |
| `v177_rail_pax_min_dist` | 0 | V177: minimum distance in tiles for rail passenger candidates (generation filter); 0 = inert (défaut) | Option, OFF au défaut |
| `v180_rail_wagon_boost_delay` | 0 | V180: years after game start before the wagon boost applies; 0 = from start (défaut) | Option OFF (requiert `v180_rail_wagon_boost_pct>0`) |
| `v180_rail_wagon_boost_pct` | 0 | V180: rail consist sizing offers N% more cargo than the 50% rating calibration (bigger trains); 0 = inert (défaut) | Option, OFF au défaut |
| `v179_rail_gen_dest_served` | 0 | V179: rail freight generator keeps pairs whose destination industry is already served (fresh source), for V178 to attach; 0 = inert (défaut) | Option, OFF au défaut |
| `v178_rail_shared_dest` | 0 | V178: freight candidates share accepting rail station when destination is within MIN_SEPARATION of our existing station; 0 = inert (défaut) | Option, OFF au défaut |
| `v168_rail_max_dist` | 160 | V168: rail candidate maximum distance in tiles. 160 = défaut (qualified 13/10: gate A 40x3 +152.7 k/yr, gate B 20x10 pass); 0 = historical bound derived from the A* iteration cap through… | Oui, défaut actif |
| `v171_rail_knots` | 0 | V171: recalibrated rail A* iteration knot table (V2). 0 = historical V1 table (défaut); 1 = V2 table fitted on rail-vs-rail p90 iterations | Option, OFF au défaut |
| `v172_rail_long_weight_pct` | 200 | V172: rail A* heuristic weight percentage for long searches (>= v172_rail_long_weight_dist tiles). 0 = inert (uses v91_astar_weight_pct); 100..300 = override weight percentage; défaut… | Oui, défaut actif |
| `v172_rail_long_weight_dist` | 100 | V172: Manhattan distance threshold in tiles to trigger v172_rail_long_weight_pct. Default 100 | **Oui, conditionnel** (`v172_rail_long_weight_pct>0` satisfait) |
| `policy_air` | 1 | Aviation policy: portfolio arbitration, runway cadence cap, joined bus stops, hub reuse: 1 = enabled (défaut), 0 = off | Oui, défaut actif |
| `policy_abandon` | 1 | Construction failure memory and candidate filtering (C22/C33): 1 = enabled (défaut), 0 = off | Oui, défaut actif |
| `policy_portfolio` | 1 | Portfolio and financial invariants: clean density score, staged bootstrap, dynamic cash reserve: 1 = enabled (défaut), 0 = off | Oui, défaut actif |
| `policy_vehicle_events` | 0 | Vehicle lifecycle and crash handling (C52): 1 = active handling, 0 = off (défaut) | Option, OFF au défaut |
| `loan_repay_floor_k` | 300 | Cash floor below which the loan is not repaid, in thousands: 300 = défaut, 1000 = historical | Oui, défaut actif |
| `pathfinder_hard_cap_k` | 5 | Hard pathfinder iteration cap, in thousands (docs/taches.md A3): 10 = défaut, 40 = pre-A3 | Oui, défaut actif |
| `rail_upgrade_failure_memory` | 1 | remember a failed double-track A* search per line and do not retry it until the abandon cooldown expires; 1 = on (défaut), 0 = off | Oui, défaut actif |
| `rail_geometry_guard` | 0 | preserve exact rail endpoint lead identity, reject proven doomed station/terminal geometry before spending, and remember only persistent geometric TRKFAIL; 0 = off (défaut) | Option, OFF au défaut |
| `rail_geometry_prefilter` | 1 | diagnostic sub-switch for rail_geometry_guard pre-spend geometry rejection; 1 reproduces current candidate behavior | **Non au défaut** (parent `rail_geometry_guard=1` inactif) |
| `rail_geometry_exact_identity` | 1 | diagnostic sub-switch for exact rail [lead,station_exit] endpoint identity; 1 reproduces current candidate behavior | **Non au défaut** (parent `rail_geometry_guard=1` inactif) |
| `rail_geometry_pair_memory` | 1 | diagnostic sub-switch for pair-level abandonment after persistent geometric TRKFAIL; 1 reproduces current candidate behavior | **Non au défaut** (parent `rail_geometry_guard=1` inactif) |
| `rail_freight_trkfail_memory` | 0 | Isolated freight-only memory for persistent own-station lead TRKFAIL; 0 = off (défaut) | Option, OFF au défaut |
| `rail_end_jump_connect` | 1 | recognize collinear bridge/tunnel jump track continuity on terminal station connection; 1 = on (défaut since 2026-10-12, porte B 20x10), 0 = off | Oui, défaut actif |
| `rail_cached_proximity_gate` | 0 | Cached rail candidate proximity against live rail lines: 0 historical (défaut), 1 shadow only, 2 drop before selection | Option, OFF au défaut |
| `incr_revalidate_index` | 1 | Indexed revalidation of candidate pool: 0 historical, 1 indexed (défaut since 2026-10-12, V157 porte B 20x10), 2 control (both, historical used, mismatch logged) | Oui, défaut actif |
| `rail_failure_audit` | 0 | Diagnostic-only rail attempts and proximity refusals by kind; 0 = off (défaut) | Sonde, OFF (activable) |
| `probe_rail_preastar` | 0 | Passive rail station-access probe before A* with matched search/build outcomes; 0 = off (défaut) | Sonde, OFF (activable) |
| `rail_geometry_live_replan` | 0 | on a live STNFAIL quote, retry an exact same-interface refresh once; if that interface disappeared, keep the pair eligible so the scheduler can replan it with a fresh A*; 0 = off (défaut) | Option OFF (requiert `rail_geometry_guard=1`) |
| `rail_origin_reuse` | 0 | allow rail candidate generation when exactly one endpoint is already served; reject only pairs with both endpoints served; 0 = historical exclusivity (défaut) | Option, OFF au défaut |
| `rail_origin_exposure_shadow` | 0 | shadow-only: count rail pairs rejected by historical served-endpoint exclusivity; never admits candidates; 0 = off (défaut) | Sonde, OFF (activable) |
| `rail_origin_exposure_detail_shadow` | 0 | with rail_origin_exposure_shadow, classify exactly-one-served rejects using the existing rail-origin join contract; diagnostic only; 0 = off (défaut) | Sonde, OFF (activable) |
| `rail_target_cargo_prefilter` | 1 | opcode optimization: during targeted industry rail regeneration, skip fallback cargos that cannot structurally touch the target industry; 1 = on (défaut) | Oui, défaut actif |
| `rail_origin_reuse_fallback` | 0 | with rail_origin_reuse, publish one-served rail extensions only to fill a free-origin candidate pool below TOP_K; 0 = equal-priority reuse (diagnostic défaut) | Option, OFF au défaut |
| `rail_origin_reuse_pax` | 1 | diagnostic sub-switch for passenger one-served rail extensions; 1 reproduces rail_origin_reuse candidate behavior | **Non au défaut** (parent `rail_origin_reuse=1` inactif) |
| `rail_origin_reuse_freight` | 1 | diagnostic sub-switch for freight one-served rail extensions; 1 reproduces rail_origin_reuse candidate behavior | **Non au défaut** (parent `rail_origin_reuse=1` inactif) |
| `rail_origin_reuse_multiline_match` | 0 | with rail_origin_reuse, resolve a compatible line among all rail lines sharing the same StationID instead of testing only the first; 0 = historical first-line behavior (défaut) | Option OFF (requiert `rail_origin_reuse=1`) |
| `rail_origin_reuse_cross_cargo` | 0 | with rail_origin_reuse, allow a freight StationID to be reused by a different cargo; cross-cargo ignores the old line A/B role while same-cargo keeps the historical same-role guard; 0 =… | Option OFF (requiert `rail_origin_reuse=1`) |
| `rail_origin_reuse_air_priority_shadow` | 0 | measure whether a one-served rail extension would directly displace the immediately following fundable AIR project; no decision change; 0 = off (défaut) | Option OFF (requiert `rail_origin_reuse=1`) |
| `rail_origin_reuse_air_priority` | 0 | defer a one-served rail extension only when it would directly make the immediately following live AIR project unfundable; 0 = off (défaut) | Option OFF (requiert `rail_origin_reuse=1`) |
| `rail_origin_reuse_search_cap_k` | 0 | experimental hard A* cap override in thousands for origin-served rail extensions only; 0 = keep normal rail cap (défaut), 40 = pre-A3 diagnostic cap | Option OFF (requiert `rail_origin_reuse=1`) |
| `rail_origin_reuse_search_supersede` | 0 | experimental: when an origin-served rail extension is current rank 0, let it replace an in-progress primary non-reuse rail search; 0 = off (défaut) | Option OFF (requiert `rail_origin_reuse=1`) |
| `probe_rail_terrain` | 0 | log a cheap terrain-roughness summary of the straight line between both stations when a rail A* search starts, to test whether terrain predicts iteration-cap abandons; 0 = off (défaut) | Sonde, OFF (activable) |
| `abandon_cooldown_days` | 365 | Delai de reprise en jours sur la memoire d'abandon (365 = defaut adopte, docs/taches.md C33.3) | Oui, défaut actif |
| `rail_terrain_factor` | 100 | Pourcentage applique au cout du rail par tuile (100 = brut, 170 = calibre reel, docs/taches.md C2) | Oui : valeur de référence ou neutre (modifiable) |
| `rail_finance_bias_pct` | 100 | Rail project finance capital bias percentage (candidate capital * bias / 100); défaut 100 | Oui : valeur de référence ou neutre (modifiable) |
| `rail_depot_cost` | 0 | Include rail depot construction cost in rail line infrastructure economics (F-RAIL-ECON-01): 1 = enabled, 0 = disabled (défaut) | Option, OFF au défaut |
| `project_top_k` | 64 | Taille de la fenetre de selection du portefeuille (64 = defaut mesure) | Oui, défaut actif |
| `project_top_k_dynamic` | 0 | Cale PROJECT_TOP_K sur (villes + industries) de la carte: 1 = dynamique, 0 = fixe (defaut) | Option, OFF au défaut |
| `road_pax_build` | 0 | Build new town-to-town passenger bus lines: 0 = disabled by défaut to preserve airport demand, 1 = enabled | Option, OFF au défaut |
| `road_loading_fix` | 0 | Ignore vehicles loading at berths during road jam detection (docs/taches.md C26b): 1 = active, 0 = off (défaut) | Option, OFF au défaut |
| `road_pax_catchment_pct` | 86 | Town production share captured by each bus stop, percent: 86 = measured défaut, 0 = historical 22% | **Non au défaut** (parent `road_pax_build=1` inactif) |
| `road_stop_catchment_houses` | 10 | Maximum houses covered by a radius-3 bus stop (physical catchment bound, défaut 10) | **Non au défaut** (parent `road_pax_build=1` inactif) |
| `road_pax_dwell_days` | 6 | Average station dwell and loading time for passenger road vehicles in days (défaut 6) | **Non au défaut** (parent `road_pax_build=1` inactif) |
| `air_early_slot` | 1 | Early-slot policy: prioritize profitable air projects claiming first airport slots (adopted 2026-09-15): 1 = on (défaut), 0 = off | Oui, défaut actif |
| `air_early_slot_target_towns` | 6 | Early-slot target: number of distinct large towns to secure with an Opex airport before priority stops | Oui, défaut actif |
| `air_early_slot_min_pop` | 1000 | Early-slot minimum town population for a new airport endpoint to receive the priority bonus | Oui, défaut actif |
| `air_early_slot_bonus_pct` | 50 | Early-slot selection-score bonus per newly claimed qualifying town (percent) | Oui, défaut actif |
| `air_fleet_cadence_days` | 7 | Delai minimal en jours entre deux extensions de flotte aerienne sur une meme ligne (7 = hebdomadaire) | Oui, défaut actif |
| `air_fleet_cooldown_prefilter` | 1 | Filter AIR lines still under fleet-growth cooldown before ROI sorting | Oui, défaut actif |
| `air_fleet_routes_index` | 1 | Count live air routes per airport with an index once per pass: 0 = off, 1 = index (défaut since 2026-10-12, V160 porte B 20x10), 2 = compare | Oui, défaut actif |
| `v161_fleet_net_marginal` | 1 | V161 cap AIR fleet growth value by a prior net of neighbour lines sharing an airport: 0 = off, 1 = on (défaut since 2026-10-13, user decision after porte A 40x3 +2.7%) | Oui, défaut actif |
| `v161_prior_own` | 13000 | V161 prior: annual profit of one more plane on its own line (pounds) | Oui, défaut actif |
| `v161_prior_neighbour` | 2600 | V161 prior: annual profit lost per neighbour line sharing an airport (pounds) | Oui, défaut actif |
| `air_fleet_c121_preguard` | 0 | Filter AIR lines refused by C121 observation/cadence before visible fleet refresh | Option OFF (requiert `c121_air_visible_competition=1`) |
| `air_joined_stop_limit` | 2 | Maximum bus-stop pieces directly joined to each airport station (défaut 2) | Oui, défaut actif |
| `air_pax_revenue_calibration_pct` | 104 | Air passenger revenue calibration percent: 104 = measured défaut, 100 = uncalibrated | Oui, défaut actif |
| `town_growth` | 0 | Boost served town growth with one base bus line per town: 1 = enabled, 0 = off (défaut) | Option, OFF au défaut |
| `town_growth_plan_memo` | 1 | Town growth: remember a town whose bus-line planning failed (TRACEX/DEPOTX/SITE) and retry only when its house count changed; 1 = on (défaut), 0 = off | **Non au défaut** (parent `town_growth=1` inactif) |
| `town_growth_skip_noop` | 0 | After an empty town-growth attempt, run the next task immediately: 1 = skip slot, 0 = historical (défaut) | Option, OFF au défaut |
| `town_growth_roi_gate` | 1 | C87: build a town-growth bus line only if its predicted annual profit is positive, and close one losing money two full years in a row; 1 = on (défaut), 0 = off | **Non au défaut** (parent `town_growth=1` inactif) |
| `rail_expand` | 0 | Add one wagon to profitable saturated one-train rail lines: 1 = enabled, 0 = control (défaut) | Option, OFF au défaut |
| `road_time_scaled_cap` | 0 | B3 experiment: scale pax road fleet cap from simultaneous berth capacity: 1 = test arm, 0 = historical cap (défaut) | Option, OFF au défaut |
| `c80_worker_rail` | 0 | C80 tranche 1: migrate A* rail search to execution register worker: 1 = enabled, 0 = disabled (défaut) | Option, OFF au défaut |
| `c80_rail_stock_gate` | 0 | C80 A* stock step 1: rail candidate is eligible only with ready route in _railReadyStock: 1 = enabled, 0 = disabled (défaut) | Option, OFF au défaut |
| `c80_rail_stock_worker` | 0 | C80 A* stock step 2: autonomous RailSearchStock worker (N=1) on slack: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `c80_rail_stock_gate=1`) |
| `c80_worker_town` | 0 | C80 tranche 2: migrate town growth to execution register worker: 1 = enabled, 0 = disabled (défaut) | Option, OFF au défaut |
| `c76_regen_targeted` | 1 | C76 step 2 / C80 tranche 3: invalidation-driven project pool regeneration: 1 = enabled (défaut), 0 = monthly full regeneration | Oui, défaut actif |
| `c76_lean_invalidation` | 0 | C76: lean invalidation avoids full pool regenerations for budget changes and local line/subsidy updates: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `c76_regen_targeted=1`) |
| `c76_freight_rotation` | 0 | C76: under c76_regen_targeted, a month without full pool regeneration still rotates the freight cargo by regenerating only the rail and road candidates: 1 = enabled, 0 = disabled (défaut) | Option OFF (requiert `c76_regen_targeted=1`) |
| `c67_water_exposure_probe` | 0 | C67.6: passive probe, re-checks water pairs rejected by the bounded BFS with the block oracle in tick slack: 1 = enabled, 0 = disabled (défaut) | Sonde, OFF (activable) |
| `c67_terrain_map` | 0 | C67.4: block terrain map filled in tick slack before Sleep, no consumer: 1 = enabled, 0 = disabled (défaut) | **Effet absent ou contourné au défaut** |
| `c80_mode_regen` | 1 | C80 tranche 4: under c76_regen_targeted, an industry or non-air engine change regenerates only the dependent modes (rail, road, water) instead of the whole pool: 1 = enabled (défaut), 0… | **Oui, conditionnel** (`c76_regen_targeted=1` satisfait) |
| `c80_air_choice_memo` | 0 | C80 tranche 5: the aircraft chosen per air route by a full pool regeneration is reused (only its economics recomputed) by the post-build updates: 1 = enabled, 0 = disabled (défaut) | Option, OFF au défaut |
| `c80_air_hub_index` | 1 | C80 tranche 5 bis: exact per-call indexes of air routes per station and connected station pairs in air planning (same decisions, fewer opcodes): 1 = enabled (défaut), 0 = disabled | Oui, défaut actif |
| `c80_marginal_floor` | 1 | C80 task 5: filter marginal multi-build projects whose calibrated profit per vehicle is below the mode realized average: 1 = enabled (défaut), 0 = disabled | Oui, défaut actif |
| `c80_air_eval_fast` | 0 | C80 air eval fast: exact memoization and deferred checks in air planning (same decisions, fewer opcodes): 1 = enabled, 0 = disabled (défaut) | Option, OFF au défaut |
| `air_hubhub_marginal` | 1 | V86: Deduct cannibalised revenue from existing hub lines for legacy hub-to-hub economics; deduction bypassed under C121: 1 = enabled (défaut), 0 = disabled | **Effet absent ou contourné au défaut** |
| `air_hub_max_routes` | 3 | V86: Maximum number of routes per airport hub: 0 = défaut caps (4 for small/commuter, 12 for others), 1..12 = cap at min(défaut, N) | Oui, défaut actif |
| `v89_rail_search_throughput` | 1 | V89: opportunistic rail A* search throughput (multiple slices per tick / inter-stage): 1 = enabled (défaut), 0 = disabled | Oui, défaut actif |
| `unprofitable_streak_threshold` | 3 | C52 #4: Number of consecutive unprofitable years before retiring vehicle or scrapping line (défaut 3) | Oui, défaut actif |
| `v195_v182_years` | 0 | V195: apply v182 rail freight min distance only during the first N years (0 = always, défaut) | Oui : valeur de référence ou neutre (modifiable) |
| `v194_short_to_served_dst` | 0 | V194: exempt short rail freight (under v182 min distance) whose destination is near one of our rail stations (0 = off, défaut) | Option, OFF au défaut |
| `v193_chain_towns` | 0 | V193: V88 goods chain generation evaluates at most N most populated towns per source->factory and keeps the best chain (0 = unbounded, défaut) | Option OFF (requiert `v88_goods_chain=1`) |
| `v184_rail_search_slots` | 1 | V184: number of concurrent primary rail A* search slots (1..4, défaut 1) | Oui, défaut actif |
| `v197_guided_double` | 0 | V197: guided double track pathfinding like AAAHogEx (outwardSide for track 1, guideTiles for track 2); 0 = inert défaut, 1 = on | Option OFF (requiert `v190_rail_double_build=1`) |
| `v198_template_double` | 0 | V198: double track using station templates (loop source + through destination); 0 = inert défaut, 1 = on | Option OFF (requiert `v190_rail_double_build=1`) |
| `v200_double_cash_k` | 0 | V200: double-track machinery only when cash net of loan >= this (k GBP) and cash >= 2x single quote + reserve; 0 = always (inert) | Option OFF (requiert `v190_rail_double_build=1`) |
| `v199_robust_build` | 0 | V199: robust rail track laying inspired by AAAHogEx (retry, homeward level, online signals, clear area); 0 = inert défaut, 1 = on | Option OFF (requiert `v190_rail_double_build=1`) |
| `v199_level_budget_k` | 20 | V199: spending cap for homeward lateral strip leveling in kGBP (défaut 20 = 20 kGBP) | **Non au défaut** (parent `v199_robust_build=1` inactif) |
| `v190_rail_double_build` | 0 | V190: build freight rail lines directly as double-track loop from start (0 = inert défaut) | Option, OFF au défaut |
| `v190_rail_double_delay` | 0 | V190: years after game start before freight lines are built double (0..5, défaut 0) | Option OFF (requiert `v190_rail_double_build=1`) |
| `v190_rail_max_trains` | 4 | V190: maximum trains per double-track freight rail line (2..8, défaut 4) | **Non au défaut** (parent `v190_rail_double_build=1` inactif) |
| `v188_rail_join_slopes` | 0 | V188: allow sloped tiles for joined parallel rail platforms (double track) (0 = flat only) | Option OFF (requiert `v190_rail_double_build=1`) |
| `v187_rail_refleet_during_search` | 0 | V187: allow rail second train / double track while a new-line A* search is running (0 = historical) | Option, OFF au défaut |
| `v186_rail_search_slices` | 1 | V186: rail A* slices advanced per scheduler pass (1..16, défaut 1 = historical) | Oui, défaut actif |
| `v90_fast_pathfinder` | 1 | V90: optimized vendorized rail pathfinder (identical routes): 1 = enabled (défaut), 0 = BaNaNaS RailPathFinder | Oui, défaut actif |
| `v90_pathfinder_check` | 0 | V90: test-mode parallel step-by-step verification between BaNaNaS and V90 pathfinder: 1 = enabled (only if v90_fast_pathfinder=1), 0 = disabled (défaut) | Sonde, OFF (activable) |
| `v91_astar_weight_pct` | 120 | V91: weighted A* heuristic percentage for rail pathfinder (100 = unweighted V90, >100 faster search with slightly longer routes; défaut 120) | Oui, défaut actif |
| `v129_rail_astar_exact_opt` | 1 | V129: optimized rail A* with strictly identical exploration (parallel-array heap, cached heuristic/bridge table, batched FindPath, single-pass neighbours); needs v90_fast_pathfinder=1: 1… | Oui, défaut actif |
| `v129_rail_astar_check` | 0 | V129: test-mode lockstep check of V129 against V90 (heap top, cost, priority per step; logs V129_CHECK), only if v129_rail_astar_exact_opt=1: 1 = enabled, 0 = disabled (défaut) | Sonde, OFF (activable) |
| `v131_rail_repair` | 0 | V131: local repair of a stocked rail plan blocked on obstacle/station (extended anchors, bypass A* with adaptive budget, platform shift, duplicate-own-rail drop). 0 = off (défaut), no… | Option, OFF au défaut |
| `v131_town_clearance` | 0 | V131: rail A* town clearance avoiding tiles near town centers to protect routes from urban and airport expansion. 0 = off (défaut), no decision change. Not qualified | Option, OFF au défaut |
| `v94_air_site_list` | 1 | V94: native AITileList prefilter for OpexAirFindSite (same anchor and probes): 1 = enabled (défaut), 0 = legacy scan | Oui, défaut actif |
| `v94_air_site_check` | 0 | V94: run legacy and AITileList airport site scans on the same input; legacy decides; log V94_CHECK: 1 = enabled, 0 = disabled (défaut) | Sonde, OFF (activable) |
| `homogeneous_preselect` | 0 | Rank rail and road candidate pools by the portfolio funding score: 1 = enabled, 0 = historical ranking (défaut) | Option, OFF au défaut |
| `air_efficiency_batch` | 0 | AIR 2026-10-02 A/B: preflight both sites, one top64 plan per OD pair, event/cash portfolio reselection; 1 = candidate, 0 = previous behavior (défaut) | Option, OFF au défaut |
| `air_efficiency_preflight` | 0 | AIR efficiency A/B: preflight both airport endpoints before spending | Option, OFF au défaut |
| `air_efficiency_dedupe` | 0 | AIR efficiency A/B: keep one ranked AIR plan per OD pair in top K | Option, OFF au défaut |
| `air_efficiency_reselect` | 0 | AIR efficiency A/B: event-driven catalog plus cash-threshold local reselection | Option, OFF au défaut |
| `air0310_v96_shortcut_lean` | 1 | AIR 03/10 3a A/B: V96 shortcut keeps null guards and drops the unused upper score; 1 = on (défaut), 0 = previous bound | Oui, défaut actif |
| `air0310_one_two_fused` | 1 | AIR 03/10 3b A/B: prepare one aircraft's fares, trip, amortisation, capacities and airport costs, then score N=1 and N=2; 1 = on (défaut), 0 = two full economics calls | Oui, défaut actif |
| `air0310_incremental_publish` | 1 | AIR 03/10 1 A/B: a partial air publish inserts only the new plans and reselects; 1 = on (défaut), 0 = full portfolio rebuild | **Oui, conditionnel** (`c121_catalog_incremental=1` satisfait) |
| `air0310_hub_snapshot` | 1 | AIR 03/10 2 A/B: reuse the ordered hub and site snapshot across slices of the same combo while the air topology signature matches; 1 = on (défaut), 0 = rediscover every slice | **Oui, conditionnel** (`c121_catalog_incremental=1` satisfait) |
| `air0310_site_validity_cache` | 1 | AIR 03/10 V122 A/B: remember whether each air site is still buildable across reselections until the month changes or OpexAI builds or removes a station, airport or line; 1 = on (défaut),… | **Oui, conditionnel** (`c121_catalog_incremental=1` satisfait) |
| `v127_idle_cash_road_regen` | 0 | V127: under C121_CATALOG_INCREMENTAL, at most once a month, enqueue a road pool regeneration when idle cash exceeds 100000 and the road pool is small or 90 days old; 1 = on, 0 = off (défaut) | Option OFF (requiert `c121_catalog_incremental=1`) |
| `v139_feeder_bus` | 0 | V139: feeder bus shuttle from uncovered town center to airport; 0 = disabled (défaut), 1 = enabled | Option, OFF au défaut |
| `v141_catalog_incremental` | 1 | V141: during AIR0310 partial publish, refresh already-published air projects in place instead of OpexProjectFromAir; 1 = on (défaut, adopted 11/10), 0 = full reconvert | **Oui, conditionnel** (`c121_catalog_incremental=1` satisfait) |
| `v141_catalog_incremental_check` | 0 | V141 control: under probe_events, also run OpexProjectFromAir on published air and log V141_CHECK identical/diff; 1 = on, 0 = off (défaut) | Option OFF (requiert `c121_catalog_incremental=1`) |
| `subsidy_reselect_if_purged` | 1 | F-EVENT-BACKLOG-01: only reselect projects on subsidy expiration/award if _purgeSubsidyFromProjects actually removed candidates; 1 = conditional reselect, 0 = unconditional reselect… | Oui, défaut actif |
| `v147_air_catalog_tasks` | 1 | V147 (CD07/B): run AIR catalogue rebuild phases (scan, publish, apply) as their own scheduler entries; défaut 1, 0 = single catalog entry (rollback) | Oui, défaut actif |
| `ac04_extra_site_dedup` | 1 | AC04-B adopted: avoid physically duplicate hub-to-site anchors while keeping distinct second slots; défaut 1 | Oui, défaut actif |
| `ac05_skip_unused_hub_income` | 1 | AC05 adopted: skip unused V86 hub income precomputation when C121 ignores it; défaut 1 | Oui, défaut actif |
| `ac06_c76_snapshot_ack` | 1 | AC06 v2 adopted: C78 full scan acknowledges only C76 revisions covered by its initial refresh; défaut 1 | **Oui, conditionnel** (`c76_regen_targeted=1` satisfait) |
| `ac04_hub_usage_gate` | 1 | AC04-A v3 adopted: revalidate orphan hub capacity before evaluating AIR pairs; défaut 1, rollback 0 | Oui, défaut actif |
| `air_publish_lazy_select` | 1 | V158: defer AIR project reselection until selection state is read; 0 = eager, 1 = lazy select (défaut since 2026-10-12, V158 porte B 20x10) | Oui, défaut actif |
| `select_bisect_insert` | 1 | V154: binary search insertion in OpexProjectInsertDefensive; 1 = on (défaut since 2026-10-12, V157 porte B 20x10), 0 = historical | Oui, défaut actif |
| `v163_multi_cargo` | 0 | V163: a rail freight train also carries a second cargo produced by its source industry and accepted by its destination industry (e.g. GRAI + LVST farm to factory), wagons sized per… | Option, OFF au défaut |
| `v207_rail_pax_share_pct` | 0 | V207: predicted share of town passenger production captured by a rail line (0 = legacy 22%, 1..100 = custom percentage); 0 = off (défaut) | Oui : valeur de référence ou neutre (modifiable) |
| `v207_rail_mail` | 0 | V207: passenger rail lines also carry mail as a secondary cargo, with wagons sized to mail production; 0 = off (défaut), 1 = on | Option, OFF au défaut |
| `v207_rail_pax_joined_stops` | 0 | V207: maximum number of drive-through bus stops joined to each passenger rail station to extend catchment (0..4); 0 = off (défaut) | Option, OFF au défaut |
| `v207_rail_pax_site_rank_pct` | 0 | V207: passenger rail station sites are sampled more widely and only those whose platform catchment produces at least this percentage of the best sampled site are kept (1..100); 0 = off… | Option, OFF au défaut |
| `v212_rail_pax_revenue_pct` | 100 | V212: calibration of the predicted annual revenue of passenger rail lines, in percent (100 = off, défaut; 150 qualified in rail-only 15/10, losing in full games) | Oui : valeur de référence ou neutre (modifiable) |
| `v212_rail_pax_capital_pct` | 100 | V212: calibration of the predicted capital of passenger rail lines before the quote, in percent (100 = off, défaut; 85 qualified in rail-only 15/10, losing in full games) | Oui : valeur de référence ou neutre (modifiable) |
| `v214_rail_turn_cost` | 0 | V214: rail A* cost of leaving a diagonal (entering one is free), as AAAHogEx (300, qualified in rail-only only); 0 = historical 50 on every direction change (défaut) | Oui : valeur de référence ou neutre (modifiable) |
| `v214_rail_tight_turn_cost` | 0 | V214: rail A* extra cost of a 90 degree turn taken on a single tile, as AAAHogEx (1500, 100 below 40 tiles; qualified in rail-only only); 0 = off (défaut) | Oui : valeur de référence ou neutre (modifiable) |

## Cas importants pour un futur nettoyage

- `air_p0_margin_probe` : La variable chargée n’a pas de consommateur métier.
- `air_p0_second_step_marginal` : La variable chargée n’a pas de consommateur métier.
- `c121_air_defensive_floor` : Calcul possible, mais PORTFOLIO_FLOOR_PCT est fixé à 0 (settings.nut).
- `c67_terrain_map` : Calcul de carte implémenté, sans consommateur métier des résultats.
- `c115_air_c100_capital_replay` : Chemin historique encore présent (air_engine_choice.nut:1540), ignoré par la sélection principale lorsque C121 est actif.
- `air_hubhub_marginal` : Déduction du chemin legacy court-circuitée sous C121 avec ac05_skip_unused_hub_income=1.

La seule absence de `AIController.GetSetting()` dans `settings.nut` est
`pathfinder_sleep_ticks` : les constructeurs `builder_rail.nut` le lisent directement
(au moins deux sites). Les nombreuses sondes historiquement individuelles restent
compatibles avec `OpexProbeSetting()` et le masque `probes` ; elles ne sont pas
des paramètres morts simplement parce que leur valeur par défaut est zéro.

Cet inventaire est statique : il ne vaut ni preuve de couverture en partie ni
validation statistique d’une variante désactivée par défaut.

## Constantes verrouillées dans `settings.nut` (hors des 277 réglages utilisateur)

Ces noms ne sont **pas** déclarés par `AddSetting` et aucune valeur de l’interface
OpenTTD ne peut les changer directement. Ils sont distingués des paramètres ci-dessus.

| Constante | Valeur forcée | Fonction résiduelle | Active au défaut ? |
|---|---|---|---|
| `C55_FREIGHT_ORIGIN_RELAX` | `false` | Relâchement historique des filtres origine fret | Non |
| `C41_RAIL_LOST_SIGNAL_REPAIR` | `false` | Réparation des signaux lors de pertes rail | Non |
| `C41_RAIL_LOST_JUNCTION_REPAIR` | `false` | Réparation des jonctions rail lors de pertes | Non |
| `PAX_NEAR` | `false` | Branche historique de voyageurs proches | Non |
| `WATER_OPCODE_COMPAT_FALSE` | `false` | Branche de compatibilité des opcodes eau ; assignation répétée cinq fois | Non |
| `C53_ORDER_NOLOAD` | `false` | Variante historique d’ordres sans chargement | Non |
| `OPEX_AIR_CAP_PAD`, `OPEX_AIR_PLAN_PAD`, `OPEX_AIR_SITE_PAD`, `OPEX_AIR_TOWN_PAD` | `false` | Padding/opcodes AIR | Non |
| `TRANSIT_COST_PERMILLE` | `0` | Coût de transit additionnel | Non (terme nul) |
| `INFRA_AMORT_PCT` | `0` | Amortissement de l’infrastructure | Non (terme nul) |
| `AIR_MAX_DISTANCE` | `0` | Ancien plafond global de distance aérienne | Non (valeur neutre) |
| `PORTFOLIO_MAX_BATCH` | `1` | Taille maximale historique du lot de portefeuille | Fixé à 1 |
| `AIR_FLEET_BUFFER` | `0` | Marge supplémentaire de flotte AIR | Non (terme nul) |
| `PORTFOLIO_FLOOR_PCT` | `0` | Plancher de sélection, important pour le verrou R7 | Neutralisé à zéro |

Ne pas confondre ces constantes historiques avec une autorisation de supprimer leur code :
le chemin forcé peut encore consommer des opcodes ou intervenir en Save/Load.
