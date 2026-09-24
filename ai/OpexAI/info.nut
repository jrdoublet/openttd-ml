class OpexAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA multimodale : meilleur ROI par origine/destination, puis revenu maximise sous contraintes de capital et d'opcodes."; }
  function GetVersion()     { return 7; }
  function GetDate()        { return "2026-09-09"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "15"; }

  /* Les reglages debug_signs et pathfinder_sleep_ticks existent pour NE PAS POLLUER une partie
   * partagee avec des joueurs humains.
   * Entre IA, la regle est de jouer a armes egales, sans auto-handicap. */
  function GetSettings()
  {
    /* --- 1. Systeme et instrumentation --- */

    /* Panneaux de diagnostic. Defaut ACTIF (requis par les sweeps pour collecter les metriques). */
    AddSetting({
      name = "debug_signs",
      description = "Diagnostic signs on the map: 1 = current behaviour (required by sweeps/), 0 = none (use when playing with humans)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "decision_log",
      description = "Emit structured decision log lines via AILog: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "save_full_state",
      description = "Persist the full decision state in savegames: 1 = save built lines and scheduler state (default), 0 = minimal payload",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "pathfinder_sleep_ticks",
      description = "Ticks slept after each 50-iteration A* chunk: 0 = no self-handicap (default), 1+ = yield more often (with humans)",
      min_value = 0, max_value = 10,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });

    /* --- 2. Sondes de diagnostic unifiees (9 groupes) --- */

    AddSetting({
      name = "probe_cost",
      description = "Enable construction cost probes (rail, air, road) comparing modelled vs real expense; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_scheduler",
      description = "Enable scheduler opcode and latency diagnostic ledgers (C41, C39); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_candidates_road",
      description = "Enable road candidate generation opcode profiling (pax, freight, town, feeder); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_candidates_rail",
      description = "Enable rail candidate generation profiling (pax, freight, speed, cruise, economics); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_catalogue",
      description = "Enable catalogue invalidation and engine availability probes (C39, C41); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_rail_search",
      description = "Enable rail A* search state probes (domination, fallthrough, cadence); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_vehicle_lost",
      description = "Enable vehicle lost and topology diagnostic probes (C41); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_portfolio",
      description = "Enable portfolio, tension, scarcity and treasury chronological probes; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c69_fleet_demand_batch",
      description = "C69: allow air fleet expansion batch size to match measured waiting demand without the 4-plane cap; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c69_decision_bottleneck",
      description = "C69: rank projects by P/max(C, F*tau), F = operating cash flow, tau = days per build; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c69_fleet_exempt",
      description = "C69 bis: fleet projects (planes added to an existing line) keep P/C under c69_decision_bottleneck, since they build nothing; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c70_mode_calibration",
      description = "C70: scale predicted profit by a per-mode realised/predicted factor measured on own mature lines; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c72_plane_choice",
      description = "C72: air plane choice per route; 0 = max profit (C68, default), 1 = max ROI, 2 = max P/max(C, K_dec)",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "c84_air_target_fleet",
      description = "C84: keep current aircraft choice and 1-plane initial build, remember its profitable target fleet and use live marginal economics for demand-backed growth; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c85_air_equipment_frontier",
      description = "C85: prefilter route aircraft to the structurally non-dominated compatible frontier before C68 economics; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v88_goods_chain",
      description = "V88: complete goods industrial chains (input feeder line to transformer + goods delivery line to town); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v88_chain_force",
      description = "V88 test only: under v88_goods_chain, goods chain projects bypass top-K, profit floor and ranking to validate their construction path: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_full_load",
      description = "C81: air full-load orders; 0 = none (default), 1 = full load at both airports, 2 = full load at the first airport only (AAAHogEx default)",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "c82_engine_calibration",
      description = "C82: scale predicted air profit by a per-aircraft-engine realised/predicted factor from own mature air lines, instead of the C70 air factor (project ranking and aircraft choice per route); 0 = off (default), 1 = on",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "c75_multi_build",
      description = "C75: multi-build per pass in rich phase as long as capital < K_pass and capital <= available; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });


    AddSetting({
      name = "probe_events",
      description = "Enable AI event, crash, fleet depth and equipment selection probes; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* --- 3. Macro-politiques adoptees unifiees (8 groupes) --- */

    AddSetting({
      name = "policy_caches",
      description = "C41 and portfolio performance caches and spatial indexing: 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_route_plane_selection",
      description = "C68 AIR policy: for an otherwise identical route, choose the compatible aircraft with the highest predicted annual profit; 1 = adopted route-specific choice/default, 0 = historical catalog aircraft",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "policy_rail",
      description = "Rail construction and operations: resumable A*, quotes, refleet, orders: 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "policy_road",
      description = "Road transport policy: drive-through stops on existing streets, overlap filtering: 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "policy_air",
      description = "Aviation policy: portfolio arbitration, runway cadence cap, joined bus stops, hub reuse: 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "policy_abandon",
      description = "Construction failure memory and candidate filtering (C22/C33): 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "policy_portfolio",
      description = "Portfolio and financial invariants: clean density score, staged bootstrap, dynamic cash reserve: 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "policy_vehicle_events",
      description = "Vehicle lifecycle and crash handling (C52): 1 = active handling, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* --- 4. Calibrations physiques et options reelles --- */

    AddSetting({
      name = "loan_repay_floor_k",
      description = "Cash floor below which the loan is not repaid, in thousands: 300 = default, 1000 = historical",
      min_value = 0, max_value = 2000,
      easy_value = 300, medium_value = 300, hard_value = 300,
      custom_value = 300,
      step_size = 50,
      flags = 0
    });

    AddSetting({
      name = "pathfinder_hard_cap_k",
      description = "Hard pathfinder iteration cap, in thousands (docs/taches.md A3): 10 = default, 40 = pre-A3",
      min_value = 5, max_value = 100,
      easy_value = 10, medium_value = 10, hard_value = 10,
      custom_value = 10,
      step_size = 5,
      flags = 0
    });

    AddSetting({
      name = "abandon_cooldown_days",
      description = "Delai de reprise en jours sur la memoire d'abandon (365 = defaut adopte, docs/taches.md C33.3)",
      min_value = 0, max_value = 5000,
      easy_value = 365, medium_value = 365, hard_value = 365,
      custom_value = 365,
      step_size = 30,
      flags = 0
    });

    AddSetting({
      name = "rail_terrain_factor",
      description = "Pourcentage applique au cout du rail par tuile (100 = brut, 170 = calibre reel, docs/taches.md C2)",
      min_value = 100, max_value = 300,
      easy_value = 170, medium_value = 170, hard_value = 170,
      custom_value = 170,
      step_size = 10,
      flags = 0
    });

    AddSetting({
      name = "rail_depot_cost",
      description = "Include rail depot construction cost in rail line infrastructure economics (F-RAIL-ECON-01): 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "project_top_k",
      description = "Taille de la fenetre de selection du portefeuille (64 = defaut mesure)",
      min_value = 8, max_value = 128,
      easy_value = 64, medium_value = 64, hard_value = 64,
      custom_value = 64,
      step_size = 8,
      flags = 0
    });

    AddSetting({
      name = "project_top_k_dynamic",
      description = "Cale PROJECT_TOP_K sur (villes + industries) de la carte: 1 = dynamique, 0 = fixe (defaut)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road_pax_build",
      description = "Build new town-to-town passenger bus lines: 0 = disabled by default to preserve airport demand, 1 = enabled",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road_loading_fix",
      description = "Ignore vehicles loading at berths during road jam detection (docs/taches.md C26b): 1 = active, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road_pax_catchment_pct",
      description = "Town production share captured by each bus stop, percent: 86 = measured default, 0 = historical 22%",
      min_value = 0, max_value = 100,
      easy_value = 86, medium_value = 86, hard_value = 86,
      custom_value = 86,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "road_stop_catchment_houses",
      description = "Maximum houses covered by a radius-3 bus stop (physical catchment bound, default 10)",
      min_value = 1, max_value = 50,
      easy_value = 10, medium_value = 10, hard_value = 10,
      custom_value = 10,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "road_pax_dwell_days",
      description = "Average station dwell and loading time for passenger road vehicles in days (default 6)",
      min_value = 1, max_value = 30,
      easy_value = 6, medium_value = 6, hard_value = 6,
      custom_value = 6,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "air_early_slot",
      description = "Early-slot policy: prioritize profitable air projects claiming first airport slots (adopted 2026-09-15): 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_early_slot_target_towns",
      description = "Early-slot target: number of distinct large towns to secure with an Opex airport before priority stops",
      min_value = 1, max_value = 16,
      easy_value = 6, medium_value = 6, hard_value = 6,
      custom_value = 6,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "air_early_slot_min_pop",
      description = "Early-slot minimum town population for a new airport endpoint to receive the priority bonus",
      min_value = 0, max_value = 10000,
      easy_value = 1000, medium_value = 1000, hard_value = 1000,
      custom_value = 1000,
      step_size = 100,
      flags = 0
    });

    AddSetting({
      name = "air_early_slot_bonus_pct",
      description = "Early-slot selection-score bonus per newly claimed qualifying town (percent)",
      min_value = 0, max_value = 200,
      easy_value = 50, medium_value = 50, hard_value = 50,
      custom_value = 50,
      step_size = 10,
      flags = 0
    });

    AddSetting({
      name = "air_fleet_cadence_days",
      description = "Delai minimal en jours entre deux extensions de flotte aerienne sur une meme ligne (7 = hebdomadaire)",
      min_value = 0, max_value = 365,
      easy_value = 7, medium_value = 7, hard_value = 7,
      custom_value = 7,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "air_joined_stop_limit",
      description = "Maximum bus-stop pieces directly joined to each airport station (default 2)",
      min_value = 0, max_value = 2,
      easy_value = 2, medium_value = 2, hard_value = 2,
      custom_value = 2,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "air_pax_revenue_calibration_pct",
      description = "Air passenger revenue calibration percent: 104 = measured default, 100 = uncalibrated",
      min_value = 50, max_value = 200,
      easy_value = 104, medium_value = 104, hard_value = 104,
      custom_value = 104,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "town_growth",
      description = "Boost served town growth with one base bus line per town: 1 = enabled (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "town_growth_plan_memo",
      description = "Town growth: remember a town whose bus-line planning failed (TRACEX/DEPOTX/SITE) and retry only when its house count changed; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "town_growth_skip_noop",
      description = "After an empty town-growth attempt, run the next task immediately: 1 = skip slot, 0 = historical (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "town_growth_roi_gate",
      description = "C87: build a town-growth bus line only if its predicted annual profit is positive, and close one losing money two full years in a row; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

        AddSetting({
      name = "rail_expand",
      description = "Add one wagon to profitable saturated one-train rail lines: 1 = enabled, 0 = control (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road_time_scaled_cap",
      description = "B3 experiment: scale pax road fleet cap from simultaneous berth capacity: 1 = test arm, 0 = historical cap (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_double_register",
      description = "C80 tranche 0: double-register orchestrator (reactive queue + execution register): 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_worker_rail",
      description = "C80 tranche 1: migrate A* rail search to execution register worker: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_worker_town",
      description = "C80 tranche 2: migrate town growth to execution register worker: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c76_regen_targeted",
      description = "C76 step 2 / C80 tranche 3: invalidation-driven project pool regeneration: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c76_lean_invalidation",
      description = "C76: lean invalidation avoids full pool regenerations for budget changes and local line/subsidy updates: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c76_freight_rotation",
      description = "C76: under c76_regen_targeted, a month without full pool regeneration still rotates the freight cargo by regenerating only the rail and road candidates: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_mode_regen",
      description = "C80 tranche 4: under c76_regen_targeted, an industry or non-air engine change regenerates only the dependent modes (rail, road, water) instead of the whole pool: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_air_choice_memo",
      description = "C80 tranche 5: the aircraft chosen per air route by a full pool regeneration is reused (only its economics recomputed) by the post-build updates: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_air_hub_index",
      description = "C80 tranche 5 bis: exact per-call indexes of air routes per station and connected station pairs in air planning (same decisions, fewer opcodes): 1 = enabled (default), 0 = disabled",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_marginal_floor",
      description = "C80 task 5: filter marginal multi-build projects whose calibrated profit per vehicle is below the mode realized average: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_air_eval_fast",
      description = "C80 air eval fast: exact memoization and deferred checks in air planning (same decisions, fewer opcodes): 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_hubhub_marginal",
      description = "V86: Deduct cannibalised revenue from existing hub lines when evaluating hub-to-hub air routes: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_hub_max_routes",
      description = "V86: Maximum number of routes per airport hub: 0 = default caps (4 for small/commuter, 12 for others), 1..12 = cap at min(default, N)",
      min_value = 0, max_value = 12,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "v89_rail_search_throughput",
      description = "V89: opportunistic rail A* search throughput (multiple slices per tick / inter-stage): 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "unprofitable_streak_threshold",
      description = "C52 #4: Number of consecutive unprofitable years before retiring vehicle or scrapping line (default 3)",
      min_value = 1, max_value = 10,
      easy_value = 3, medium_value = 3, hard_value = 3,
      custom_value = 3,
      step_size = 1,
      flags = 0
    });
  }
}

RegisterAI(OpexAIInfo());
