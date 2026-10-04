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
      description = "Enable scheduler opcode, latency and idle-tour diagnostic ledgers (C41, C39, V95); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_loop_ops",
      description = "Log yearly opcode aggregates of the main loop (events, C117 sampler, orchestrator, Sleep leftover); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_span_trace",
      description = "Log dated nested spans of OpexAI micro-tasks (ticks and opcodes); 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_c121_engine_table",
      description = "Log already-computed C121 engine scans and plan context for an offline engine table; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "exp_opcode_exact",
      description = "Exact opcode paths for road planning, air fleet sort, catchment and joined stops; 1 = on (default), 0 = historical",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "exp_opcode_exact_check",
      description = "Run historical and exact opcode paths, log mismatches and opcode sums, keep the historical result; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "catalog_cost_probe",
      description = "Log catalog refresh and project generation costs; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "fleet_amort_shadow_probe",
      description = "Diagnostic only: 0 off, 1 added-aircraft amortisation shadow calculation, 2 full election snapshots; never changes decisions",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });

    AddSetting({
      name = "r19_fault_inject",
      description = "TEST ONLY: force a rollback of the Nth new AIR route after its planes started (R19 recovery); 0 = off (default)",
      min_value = 0, max_value = 20,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
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
      name = "c83_slot_reaction",
      description = "C83: regenerate AIR candidates when a watched town has one airport slot left; 1 = current behavior (default), 0 = continue the projects pass without this reactive regeneration",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c83_local_repair",
      description = "Experimental C83: repair only the threatened town airport site, reuse known partner sites; fall back to targeted regeneration if no valid partner is known",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c83_fixes",
      description = "C83 review fixes (contestable watch towns, slot-town identity, rearmable race, skip dead air pairs, targeted site scan): 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "exp_c83_watch_daily",
      description = "Experimental P4: poll existing C83 airport-slot watcher once per available game day before arbitration; default off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "exp_scheduler_skip_not_due",
      description = "Experimental P7: skip already completed report/repay tasks within one bounded scheduler scan; default off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "exp_air_hub_pair_prefilter",
      description = "Experimental: skip hub pairs already linked by an AIR line before expensive route evaluation; default off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c83_preempt_open",
      description = "C83: keep one empty large town (both airport slots free) as a defensive new-airport target ahead of hub-to-hub, still subject to the profit test: 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air_batch_town_reserve",
      description = "Air batch: fund at most one air project per new-airport town (reuse ends ignored); displaced plans stay in the pool: 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v92_air_service_choice",
      description = "V92: choose an air service (engine x count) plus a cheap one-aircraft variant of the same route, and allow later re-equipment; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v93_airport_no_pop_floor",
      description = "V93: a town under 600 people can take a large airport when route economics pass, down to 100 people; 1 = on, 0 = off (default)",
      min_value = 0,
      max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v93_air_demand_production",
      description = "V93.1: air demand from last-month passenger production, competitor share and a per-line cap, at both ends; 1 = on, 0 = off (default). Independent of v93_airport_no_pop_floor",
      min_value = 0,
      max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v95_air_post73_probe",
      description = "V95: passive annual diagnostic of post-1973 AIR opportunities rejected by population floor or served-town filters; 1 = probe, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v95_air_targeted_second",
      description = "V95.1 inactive compatibility setting: value is loaded but has no consumer; neither 0 (default) nor 1 enables targeted second airports",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v95_air_post73_targeted",
      description = "V95 inactive compatibility setting: value is loaded but has no consumer; neither 0 (default) nor 1 enables post-1973 targeted sites; v95_air_post73_probe remains a separate active probe",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c96_air_site_catchment",
      description = "C96: choose among a bounded set of buildable AIR anchors by passenger-producing catchment tiles, without changing route demand/economics; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c97_air_c69_engine_probe",
      description = "C97 passive probe: direct argmax over compatible AIR engine x fleet depth using calibrated P/max(portfolio capital, K_dec); no decision change",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c98_air_realized_probe",
      description = "C98 passive probe: compare predicted versus realised AIR profit/revenue per aircraft, ratings and utilisation by engine/line; no decision change",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c99_air_speed_api_fix",
      description = "C99: use AIEngine.GetMaxSpeed directly in AIR economics because NoAI already applies vehicle.plane_speed; 1 = corrected, 0 = legacy extra /4 (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c100_air_trip_physical",
      description = "C100: AIR trip time uses NoAI engine speed directly plus physical airport taxi/runway/vertical maneuver time; 1 = enabled, 0 = legacy (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c101_air_physical_engine_choice",
      description = "C101: among AIR engines using no more legacy capital than the C68 winner, rank by C100.1 physical profit, then return legacy route economics for admission/project scoring; 1 = enabled, 0 = legacy (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c103_air_c100_rank_replay",
      description = "C103: replay the first positive C100 engine ranking only, while returning legacy route economics for admission/project scoring; 1 = enabled, 0 = legacy (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c104_air_c100_compare_probe",
      description = "C104 passive probe: compare legacy, first positive C100 replay and C100.1 AIR engine economics on identical route contexts; no decision change",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c105_air_replay_choice_physical_economics",
      description = "C105: C100.1 physical AIR economics everywhere, but rank route engines with the first positive C100 replay objective; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c106_air_marginal_physical_engine_choice",
      description = "C106: choose AIR engine by relative marginal return under C100.1 timing, while keeping legacy route economics for portfolio scoring; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c108_air_onestep_physical_economics",
      description = "C108: C100.1 physical AIR economics everywhere, with one-step relative marginal-return engine choice; no cash or EngineID threshold; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c109_air_speed_elasticity_physical",
      description = "C109: C100.1 physical AIR economics plus relative speed-profit elasticity engine choice (threshold 0.5); 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c110_air_engine_calibration_choice_only",
      description = "C110: learn C82 realised/predicted factors per AIR engine and use them only for route engine choice; keep C70 project scoring unchanged; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c111_air_c100_decision_shadow",
      description = "C111 diagnostic: replay first positive C100 engine ranking, keep C68 decision economics/score, but finance/build the actually selected engine; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c112_air_speed_elasticity_e75_physical",
      description = "C112: C100.1 physical AIR economics plus relative speed-profit elasticity engine choice (threshold 0.75); no cash or EngineID threshold; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c113_air_c100_full_decision_shadow",
      description = "C113 diagnostic: C111 plus C68 shadow for AIR pre-admission; selected C100-replay engine still supplies real capital/fleet/build feasibility; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c114_air_c100_full_replay",
      description = "C114 diagnostic: replay the first positive C100 globally (NoAI direct speed plus historical maneuver helper) in AIR route economics and engine choice; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c115_air_c100_capital_replay",
      description = "C115: use first-C100 replay AIR economics only while the normal C68 route capital exceeds endogenous C69 K_dec; otherwise keep C68; 1 = enabled (temporary default), 0 = disabled",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c116_air_marginal_capital",
      description = "C116.4: keep strict C68 economics for AIR portfolio ranking/admission, then after selection buy the highest-profit cheaper engine that saves enough capital to cover the cached gap of the best pending AIR project; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c116_air_project_probe",
      description = "C116 passive lightweight probe: reuse C115/C68 engine scan to measure AIR/global/self project unlock opportunity; no decision change; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c117_air_throughput_probe",
      description = "C117 passive AIR throughput probe: completed-leg passengers, offered seats, cadence, waiting/rating and realised vehicle economics in 30-day line-age windows; no decision change",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c119_air_income_model",
      description = "C119: AIR pre-build income uses Manhattan payment distance and delivery-only time while keeping legacy cycle, demand and fleet sizing unchanged; 1 = enabled, 0 = default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c118_air_territorial_expansion",
      description = "C118: rank viable AIR expansion by real new-town catchment coverage and choose the engine minimizing time to the next territorial AIR project; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c118_air_coverage_probe",
      description = "C118 passive probe: log actual AIR catchment town coverage and territorial decision diagnostics without enabling the C118 policy; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c120_air_territorial_ranking",
      description = "C120: rank already-generated viable AIR projects by new administrative airport towns (physical slot town), then keep the existing C115 economic order; engine/economics unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_economics_shadow",
      description = "C121 passive AIR economics shadow: B9 cargo-specific PASS/MAIL demand, directional carried volume, physical cycle and C119 payment; no decision change; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_economics",
      description = "C121 experimental unified AIR economics for engine/project decisions; supersedes the C115 economic replay when enabled; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_winner_fusion",
      description = "C121 opcode optimization: retain opening N=1 during the winner fleet scan; monthly tariff changes and AAA_LINE fall back; requires C121 economics; 1 = on (default)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_engine_context",
      description = "C121 opcode experiment: reuse pair/engine trip, fares and amortisation during one chooser call; refresh on input/date changes; 0 = off pending qualification",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_game_engine",
      description = "C121 opcode optimization: reuse the established aircraft of the current game per airport type and skip the engine scan; 1 = on (default since 2026-10-03, opcode neutrality rule), 0 = full engine scan",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_decision_depth_economics",
      description = "C121 experimental: rank a new AIR project on the full-fleet depth selected by C121 decision score; initial build and post-build target stay unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_portfolio_depth_economics",
      description = "C121 experimental: choose AIR decision depth with the same P/max(C,K_dec) economics used by the portfolio; engine, initial N=1 build and post-build target stay unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_portfolio_split_economics",
      description = "C121 experimental: keep max-profit long-run economics for project qualification, but rank AIR with a separate P/max(C,K_dec) depth; engine, initial N=1 build and post-build target stay unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_catalog_incremental",
      description = "Experimental incremental C121 AIR plan economics and bounded catalog slices; requires c121_air_economics; 0 = off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_catalog_air_first_year",
      description = "With incremental C121, generate only AIR candidates through the first game year; 1 by default, 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_flat_bootstrap",
      description = "With incremental C121, skip the staged bootstrap: start in the complete stage so every post-build regeneration is the incremental C121 update instead of a synchronous full rebuild; 1 by default, 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_first_year_rail_prep",
      description = "With air-only first year, when no living AIR project is fundable and no rail search is running, prepare up to 3 rail routes (catalog through segmented A*) without building them; 1 by default, 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_one_or_two_planes",
      description = "With C121 economics, score only fleet depths N=1 and N=2 and build the better one; N=2 starts the second aircraft from airport B toward A, without changing full-load orders; 1 by default, 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_aaa_line",
      description = "With C121, open each AIR line with two aircraft (one per airport, AAAHogEx-style) and full-load orders at both airports; 0 = off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_territory_first",
      description = "With C121, reserve cash for the next AIR project opening a town without an Opex airport: other builds (fleet, hub, rail, road) must leave enough for it; 0 = off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_fleet_stock_growth",
      description = "With C121, grow under-target AIR fleets on waiting-cargo evidence (AAAHogEx-like) with a 60-day cooldown instead of the two-year observation rules; 0 = off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_observation_growth",
      description = "C121 experimental: allow at most one +1 AIR reinforcement per new positive annual report while under target; portfolio arbitration and target bound stay unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_first_observation_growth",
      description = "C121 cadence experiment: advance only the first AIR reinforcement 1->2 to the first positive annual observation; later reinforcements keep the standard two-year C121 cadence; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_first_growth_min_days",
      description = "With c121_air_first_observation_growth, minimum line age in days before the first 1->2 AIR reinforcement; 0 = no extra age floor",
      min_value = 0, max_value = 365,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 15,
      flags = 0
    });

    AddSetting({
      name = "c121_air_first_growth_phase_years",
      description = "Cadence experiment: for this many game years use c121_air_first_growth_min_days, then switch first 1->2 reinforcements to c121_air_first_growth_late_days; 0 = disabled",
      min_value = 0, max_value = 20,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "c121_air_first_growth_late_days",
      description = "With phased first-growth cadence, minimum line age after the early phase; 0 = no extra late age floor",
      min_value = 0, max_value = 365,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 15,
      flags = 0
    });

    AddSetting({
      name = "c121_air_first_growth_min_wait_pct",
      description = "With first-observation growth, require current max waiting cargo to reach this percentage of one plane capacity before 1->2; 0 = disabled",
      min_value = 0, max_value = 100,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 5,
      flags = 0
    });

    AddSetting({
      name = "c121_air_first_live_shadow",
      description = "C121 cadence shadow: log passive 60/90-day live evidence for AIR lines still at one plane; never changes reinforcement decisions; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_first_live_growth",
      description = "C121 cadence: advance only AIR 1->2 when balanced 90-day live evidence is positive; target, portfolio arbitration and later reinforcements stay unchanged; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_first_live_growth_phase_years",
      description = "With first-live growth, use the live 1->2 early override only during this many opening game years; 4 = default, 0 = all years",
      min_value = 0, max_value = 20,
      easy_value = 4, medium_value = 4, hard_value = 4,
      custom_value = 4, step_size = 1, flags = 0
    });

    AddSetting({
      name = "c121_air_first_live_air_priority",
      description = "With C121 first-live growth, defer a live 1->2 only when the immediately following project is a fundable new AIR line, the pass has built nothing yet, and buying the plane would make that AIR line unaffordable; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_kpass_shadow",
      description = "C121 cadence shadow: log each portfolio pass stop with blocking project and a bounded look-ahead of following project modes/finance; never changes decisions; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_kpass_air_continue",
      description = "C121 cadence experiment: when a fleet reinforcement would stop the pass on K_pass but a live AIR new-line project is fundable in the next five ranks, skip only that fleet blocker and keep scanning under the normal C75 bypass rules; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_kdec_cold_shadow",
      description = "C121 cadence shadow: for fleet projects with zero real marginal samples, log current K_dec rank versus the counterfactual C69 fleet exemption; never changes decisions; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_kdec_cold_exempt",
      description = "C121 experiment: preserve the C69 fleet K_dec exemption until a real marginal sample exists; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_engine_realization",
      description = "C121 experimental engine-only realization correction by AIR arm; project economics unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_project_realization",
      description = "C121 experimental conservative project realization correction for reused-hub AIR arms only; newpair unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_project_realization_adaptive",
      description = "C121 adaptive AIR strategy: use reused-hub realization correction only when the locked pressure regime is efficiency; otherwise keep raw C121 race economics; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_pressure_probe",
      description = "C121 passive AIR competition-pressure probe over already-inspected slot towns; no map scan and no decision change; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_defensive_floor",
      description = "C121 protected experimental setting: defensive AIR floor uses 50% competitor-slot / 75% own-slot, currently neutralized by the global zero floor; branch still runs with C121 enabled and may affect opcode cadence; 0 = off (default), 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_initial_project_economics",
      description = "C121 experimental: rank a new AIR project on the one-plane economy actually built; future fleet remains a separate marginal project; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_engine_replay_shadow",
      description = "C121 passive engine/fleet economics replay using only observed exact PASS/MAIL capacities; no decision change; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c122_air_regime_priority",
      description = "C122 experimental AIR regime strategy: after the locked C121 pressure classification, race prioritizes viable AIR projects whose already-computed defensive annotation opens an unserved Opex slot town within the same C77 tier; efficiency keeps raw economic order; economics/engine/finance unchanged; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c122_air_regime_shadow",
      description = "C122 passive shadow: run the same pressure lock, unserved-town annotation and AIR-vs-AIR comparison as C122, but never reorder projects; logs only would-be economic inversions; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c122_air_threat_probe",
      description = "C122.4 passive territorial-threat probe: when C83 sees one slot remaining in an unserved watched town, record the exact live/fundable AIR project, rank and blocker, then follow the same TownID until Opex claims it or the competitor closes it; no decision change; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c122_air_threat_retry",
      description = "C122.4 experimental local retry: if an exact C83 threatened AIR project reaches build but its threatened endpoint site became unbuildable, enqueue one targeted C77 regeneration for that TownID; implies the passive threat probe; no scoring/economics/engine/finance change; 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c102_air_station_rating_probe",
      description = "C102 inactive compatibility setting: value is loaded but has no consumer; neither 0 (default) nor 1 enables station-rating probe output",
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
      name = "v88_step2_plan_immediate",
      description = "V88: allow goods chain step 2 to build when railPlan is already computed, without waiting for railSearch to be idle: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v88_all_inputs",
      description = "V88: evaluate all transformer input cargos regardless of freight rotation: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v88_chain_step1_finance",
      description = "V88: finance capital of goods chain candidate based on step 1 only: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v88_step2_rail_prio",
      description = "V88: priority for chain rail searches: block new rail searches while step 2 is pending, and throughput slice cap: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v88_step2_cash_reserve",
      description = "V88: reserve capital for goods chain step 2 when step 1 is built: 1 = enabled, 0 = disabled (default)",
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
      name = "c75_kpass_bypass",
      description = "C75 bis: allow at most one financeable new-line project per projects pass to bypass K_pass; fleet projects never qualify; 1 = on (default), 0 = off",
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

    AddSetting({
      name = "b9_air_catchment_probe",
      description = "B9/G4 passive AIR catchment/placement probe only; no decision change; 1 = enabled, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "b9_air_demand_shadow",
      description = "B9/G4 passive pre-build AIR demand shadow; logs only, no decision change; 1 = enabled, 0 = off (default)",
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
      name = "rail_search_day_cap",
      description = "max days a single rail A* search may hold the one search slot before being abandoned and the slot released; 0 = off (default)",
      min_value = 0, max_value = 400,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 10,
      flags = 0
    });

    AddSetting({
      name = "rail_upgrade_failure_memory",
      description = "remember a failed double-track A* search per line and do not retry it until the abandon cooldown expires; 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_rail_terrain",
      description = "log a cheap terrain-roughness summary of the straight line between both stations when a rail A* search starts, to test whether terrain predicts iteration-cap abandons; 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
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
      easy_value = 100, medium_value = 100, hard_value = 100,
      custom_value = 100,
      step_size = 10,
      flags = 0
    });

    AddSetting({
      name = "rail_finance_bias_pct",
      description = "Rail project finance capital bias percentage (candidate capital * bias / 100); default 100",
      min_value = 90, max_value = 200,
      easy_value = 100, medium_value = 100, hard_value = 100,
      custom_value = 100,
      step_size = 5,
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
      name = "air_fleet_cooldown_prefilter",
      description = "Filter AIR lines still under fleet-growth cooldown before ROI sorting",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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
      description = "Boost served town growth with one base bus line per town: 1 = enabled, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "town_growth_plan_memo",
      description = "Town growth: remember a town whose bus-line planning failed (TRACEX/DEPOTX/SITE) and retry only when its house count changed; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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
      description = "C80 compatibility setting, ignored: the double-register orchestrator is permanently on for C77; both 0 (declared default) and 1 keep it enabled",
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
      name = "c80_rail_stock_gate",
      description = "C80 A* stock step 1: rail candidate is eligible only with ready route in _railReadyStock: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_rail_stock_worker",
      description = "C80 A* stock step 2: autonomous RailSearchStock worker (N=1) on slack: 1 = enabled, 0 = disabled (default)",
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
      description = "C76 step 2 / C80 tranche 3: invalidation-driven project pool regeneration: 1 = enabled (default), 0 = monthly full regeneration",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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
      name = "c67_water_exposure_probe",
      description = "C67.6: passive probe, re-checks water pairs rejected by the bounded BFS with the block oracle in tick slack: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c67_terrain_map",
      description = "C67.4: block terrain map filled in tick slack before Sleep, no consumer: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c80_mode_regen",
      description = "C80 tranche 4: under c76_regen_targeted, an industry or non-air engine change regenerates only the dependent modes (rail, road, water) instead of the whole pool: 1 = enabled (default), 0 = disabled",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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
      description = "V86: Deduct cannibalised revenue from existing hub lines for legacy hub-to-hub economics; deduction bypassed under C121: 1 = enabled (default), 0 = disabled",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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
      description = "V89: opportunistic rail A* search throughput (multiple slices per tick / inter-stage): 1 = enabled (default), 0 = disabled",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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

    AddSetting({
      name = "v90_fast_pathfinder",
      description = "V90: optimized vendorized rail pathfinder (identical routes): 1 = enabled (default), 0 = BaNaNaS RailPathFinder",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v90_pathfinder_check",
      description = "V90: test-mode parallel step-by-step verification between BaNaNaS and V90 pathfinder: 1 = enabled (only if v90_fast_pathfinder=1), 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v91_astar_weight_pct",
      description = "V91: weighted A* heuristic percentage for rail pathfinder (100 = unweighted V90, >100 faster search with slightly longer routes; default 120)",
      min_value = 100, max_value = 300,
      easy_value = 120, medium_value = 120, hard_value = 120,
      custom_value = 120,
      step_size = 10,
      flags = 0
    });

    AddSetting({
      name = "v94_air_site_list",
      description = "V94: native AITileList prefilter for OpexAirFindSite (same anchor and probes): 1 = enabled (default), 0 = legacy scan",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v94_air_site_check",
      description = "V94: run legacy and AITileList airport site scans on the same input; legacy decides; log V94_CHECK: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "homogeneous_preselect",
      description = "Rank rail and road candidate pools by the portfolio funding score: 1 = enabled, 0 = historical ranking (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "air_efficiency_batch",
      description = "AIR 2026-10-02 A/B: preflight both sites, one top64 plan per OD pair, event/cash portfolio reselection; 1 = candidate, 0 = previous behavior (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({ name = "air_efficiency_preflight", description = "AIR efficiency A/B: preflight both airport endpoints before spending", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "air_efficiency_dedupe", description = "AIR efficiency A/B: keep one ranked AIR plan per OD pair in top K", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "air_efficiency_reselect", description = "AIR efficiency A/B: event-driven catalog plus cash-threshold local reselection", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = AICONFIG_BOOLEAN });

    AddSetting({
      name = "v107_densify_portfolio",
      description = "V107: price a second rail train or a double-track upgrade as a fleet project and let the portfolio rank it; 1 = on, 0 = spend from residual cash (default). Road refleet is unchanged.",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air0310_v96_shortcut_lean",
      description = "AIR 03/10 3a A/B: V96 shortcut keeps null guards and drops the unused upper score; 1 = on (default), 0 = previous bound",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air0310_one_two_fused",
      description = "AIR 03/10 3b A/B: prepare one aircraft's fares, trip, amortisation, capacities and airport costs, then score N=1 and N=2; 1 = on (default), 0 = two full economics calls",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_air0310_n1_fallback",
      description = "AIR 03/10 4 probe: log C121 air plans lost or deferred when C1 <= budget < C2 after N=2 wins; 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air0310_n1_fallback",
      description = "AIR 03/10 4 A/B: if the chosen N=2 opening is not fundable and the already computed N=1 opening is, publish that N=1 economy; 1 = on, 0 = drop the plan (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "air0310_incremental_publish",
      description = "AIR 03/10 1 A/B: a partial air publish inserts only the new plans and reselects; 1 = on (default), 0 = full portfolio rebuild",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });
  }
}

RegisterAI(OpexAIInfo());
