class OpexAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA multimodale : meilleur ROI par origine/destination, puis revenu maximise sous contraintes de capital et d'opcodes."; }
  function GetVersion()     { return 7; }
  function GetDate()        { return "2026-09-09"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "15"; }

  /* Le reglage debug_signs existe pour NE PAS POLLUER une partie
   * partagee avec des joueurs humains.
   * Entre IA, la regle est de jouer a armes egales, sans auto-handicap. */
  function GetSettings()
  {
    AddSetting({ name = "v257_rail_refresh",
      description = "V257: review existing rail consists using observed traffic and replacement payback (default 1 since 19/10, user decision)",
      min_value = 0, max_value = 1, default_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
      flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "v233_goods_graft",
      description = "V233: measured goods to town graft (requires v233_pending_continue)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "v233_pending_continue",
      description = "V233: continue portfolio pass after pending rail/fleet search",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    /* --- 1. Systeme et instrumentation --- */

    /* V167 : un seul entier pilote panneaux, journal et sondes (somme de bits, voir settings.nut).
     * Defaut 2 = panneaux seuls, le comportement historique. */
    AddSetting({
      name = "probes",
      description = "Diagnostics bitmask: 0 none, 1 everything except 256 (signs, log, groups 8-128), 2 signs (default), 4 decision log, 8 opcodes/scheduler, 16 air, 32 rail, 64 road/water/costs, 128 events/portfolio (256 reserved, checks removed in V239); any probe group also enables the log; never changes decisions",
      min_value = 0, max_value = 511,
      easy_value = 2, medium_value = 2, hard_value = 2,
      custom_value = 2,
      flags = 0
    });

    /* Panneaux de diagnostic. Defaut ACTIF (requis par les sweeps pour collecter les metriques).
     * V167 : n'agit plus que comme veto (0) du bit 2 de probes. */
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

    /* Niveau de difficulte de l'IA choisi par le joueur (visible en jeu).
     * OpenTTD 15.3 n'applique plus easy/medium/hard/custom des reglages AI
     * et script.settings_profile n'existe plus. Les quatre valeurs restent a 3
     * (personnalise) pour le profil de reference des bancs. */
    AddSetting({
      name = "opex_difficulty",
      description = "AI difficulty level: 0 = Easy, 1 = Medium, 2 = Hard (default: full competitive play without unfair actions), 3 = Custom (anticompetitive actions such as exclusive rights allowed).",
      min_value = 0, max_value = 3,
      easy_value = 2, medium_value = 2, hard_value = 2,
      custom_value = 2, default_value = 2,
      step_size = 1,
      flags = 0
    });
    AddLabels("opex_difficulty", {
      _0 = "easy",
      _1 = "medium",
      _2 = "hard",
      _3 = "custom"
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
      name = "probe_event_backlog",
      description = "Monthly probe of _processEvents burst sizes and opcode consumption; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_select_reject",
      description = "Probe: log SELECT_REJECT for candidate air projects dropped by cash, floor, dedupe or top-k truncation; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "probe_candidates_road",
      description = "Enable road candidate generation opcode profiling (pax, freight, town); 1 = on, 0 = off (default)",
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
      name = "c83_preempt_open",
      description = "C83: keep one empty large town (both airport slots free) as a defensive new-airport target ahead of hub-to-hub, still subject to the profit test: 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v93_airport_no_pop_floor",
      description = "V93: a town under 600 people can take a large airport when route economics pass, down to 100 people; 1 = on (default), 0 = off",
      min_value = 0,
      max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v134_air_p2p_saturated_hub",
      description = "V134: allow a second airport in point-to-point (newpair) to a free town when existing airport reached air_hub_max_routes and town opens a 2nd slot; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v133_air_build_retry",
      description = "V133: quarantine an AIR town for 730 days after a local-authority refusal, a non-flat or invalid footprint, an unbuildable site or a town station cap, and keep lot pairs that do not use the failed site; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c121_air_project_realization_adaptive",
      description = "C121 adaptive AIR strategy: use the learned reused-hub realization correction in observe, race and efficiency; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
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
      name = "probe_events",
      description = "Enable AI event, crash, fleet depth and equipment selection probes; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    /* --- 3. Interrupteurs de mode et options rail --- */
    AddSetting({
      name = "mode_air",
      description = "V166: Air mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (default)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "mode_rail",
      description = "V166: Rail mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (default)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "mode_road",
      description = "V166: Road (buses, trucks) mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (default)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "mode_water",
      description = "V166: Water (ships, docks) mode on/off. 0 = no candidate, catalogue scan, construction or fleet of this mode (mono-mode benches); 1 = enabled (default)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v182_rail_freight_min_dist",
      description = "V182: minimum distance in tiles for rail freight candidates (generation filter); 0 = inert (default)",
      min_value = 0, max_value = 512,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });

    AddSetting({
      name = "v177_rail_pax_min_dist",
      description = "V177: minimum distance in tiles for rail passenger candidates (generation filter); 0 = inert (default)",
      min_value = 0, max_value = 512,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });

    AddSetting({
      name = "v180_rail_wagon_boost_delay",
      description = "V180: years after game start before the wagon boost applies; 0 = from start (default)",
      min_value = 0, max_value = 5,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v180_rail_wagon_boost_pct",
      description = "V180: rail consist sizing offers N% more cargo than the 50% rating calibration (bigger trains); 0 = inert (default)",
      min_value = 0, max_value = 400,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 25,
      flags = 0
    });
    AddSetting({
      name = "v179_rail_gen_dest_served",
      description = "V179: rail freight generator keeps pairs whose destination industry is already served (fresh source), for V178 to attach; 0 = inert, 1 = on (default, qualified 19/10 with V178: gate A 40x10 +235.6 k/yr, gate B 20x10 +192.2 k/yr)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "v178_rail_shared_dest",
      description = "V178: freight candidates share accepting rail station when destination is within MIN_SEPARATION of our existing station; 0 = inert, 1 = on (default, qualified 19/10 with V179: gate A 40x10 +235.6 k/yr, gate B 20x10 +192.2 k/yr)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v216_probe",
      description = "V216: passive estimator probe (SCORE_DECOMP, TOWN_FLOW, generation rejects) until end of year 3. 0 = inert",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = CONFIG_BOOLEAN
    });

    AddSetting({
      name = "v211_rivals_log",
      description = "V211: quarterly log of every company (value, performance, profit, bank, infrastructure) and our rank. Observation only, 0 = inert",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = CONFIG_BOOLEAN
    });

    AddSetting({
      name = "v216a_ghost_demand",
      description = "V216a: scale rail pax/mail demand by catchment already covered (ours or rivals). 0 = inert, 1 = company net gain (default since 16/10, V102 gates passed in full game), 2 = line share",
      min_value = 0, max_value = 2,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = 0
    });

    AddSetting({
      name = "v216f_dwell_pct",
      description = "V216f: add the mechanical station dwell (load + unload) to the rail cycle, in percent of the EST-16 estimate. 0 = inert; default 100 since 16/10 (V102 gates passed in full game)",
      min_value = 0, max_value = 200,
      easy_value = 100, medium_value = 100, hard_value = 100,
      custom_value = 100,
      flags = 0
    });

    AddSetting({
      name = "v217_rail_refill",
      description = "V217: from the third game year, at most once a month, regenerate the rail pool on the next freight cargo when idle cash exceeds 100000 and fewer than 2 rail candidates can start. 0 = inert, 1 = freight only (default since 17/10), 2 = freight and passengers (not validated at gate B)",
      min_value = 0, max_value = 2,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = 0
    });
    /* --- 4. Calibrations physiques et options reelles --- */

    AddSetting({
      name = "rail_geometry_guard",
      description = "preserve exact rail endpoint lead identity, reject proven doomed station/terminal geometry before spending, and remember only persistent geometric TRKFAIL; 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_geometry_prefilter",
      description = "diagnostic sub-switch for rail_geometry_guard pre-spend geometry rejection; 1 reproduces current candidate behavior",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_geometry_exact_identity",
      description = "diagnostic sub-switch for exact rail [lead,station_exit] endpoint identity; 1 reproduces current candidate behavior",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_geometry_pair_memory",
      description = "diagnostic sub-switch for pair-level abandonment after persistent geometric TRKFAIL; 1 reproduces current candidate behavior",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_failure_audit",
      description = "Diagnostic-only rail attempts and proximity refusals by kind; 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_geometry_live_replan",
      description = "on a live STNFAIL quote, retry an exact same-interface refresh once; if that interface disappeared, keep the pair eligible so the scheduler can replan it with a fresh A*; 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "rail_depot_cost",
      description = "Include rail depot construction cost in rail line infrastructure economics (F-RAIL-ECON-01): 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "c76_freight_rotation",
      description = "C76: a month without full pool regeneration still rotates the freight cargo by regenerating only the rail and road candidates: 1 = enabled, 0 = disabled (default)",
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
      name = "c80_air_choice_memo",
      description = "C80 tranche 5: the aircraft chosen per air route by a full pool regeneration is reused (only its economics recomputed) by the post-build updates: 1 = enabled, 0 = disabled (default)",
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
      name = "v195_v182_years",
      description = "V195: apply v182 rail freight min distance only during the first N years (0 = always, default)",
      min_value = 0, max_value = 10,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "v197_guided_double",
      description = "V197: guided double track pathfinding like AAAHogEx (outwardSide for track 1, guideTiles for track 2); 0 = inert default, 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v198_template_double",
      description = "V198: double track using station templates (loop source + through destination); 0 = inert default, 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v200_double_cash_k",
      description = "V200: double-track machinery only when cash net of loan >= this (k GBP) and cash >= 2x single quote + reserve; 0 = always (inert)",
      min_value = 0, max_value = 2000, step_size = 25,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });

    AddSetting({
      name = "v199_robust_build",
      description = "V199: robust rail track laying inspired by AAAHogEx (retry, homeward level, online signals, clear area); 0 = inert default, 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v199_level_budget_k",
      description = "V199: spending cap for homeward lateral strip leveling in kGBP (default 20 = 20 kGBP)",
      min_value = 0, max_value = 200,
      easy_value = 20, medium_value = 20, hard_value = 20,
      custom_value = 20,
      step_size = 5,
      flags = 0
    });

    AddSetting({
      name = "v190_rail_double_build",
      description = "V190: build freight rail lines directly as double-track loop from start (0 = inert default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v190_rail_double_delay",
      description = "V190: years after game start before freight lines are built double (0..5, default 0)",
      min_value = 0, max_value = 5,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "v190_rail_max_trains",
      description = "V190: maximum trains per double-track freight rail line (2..8, default 4)",
      min_value = 2, max_value = 8,
      easy_value = 4, medium_value = 4, hard_value = 4,
      custom_value = 4,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "v131_rail_repair",
      description = "V131: local repair of a stocked rail plan blocked on obstacle/station (extended anchors, bypass A* with adaptive budget, platform shift, duplicate-own-rail drop). 0 = off (default), no decision change. Not qualified",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v131_town_clearance",
      description = "V131: rail A* town clearance avoiding tiles near town centers to protect routes from urban and airport expansion. 0 = off (default), no decision change. Not qualified",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });


    /* AC04-B et AC05 : qualifies separement et en cumul, rollback 0. */
    AddSetting({
      name = "v163_multi_cargo",
      description = "V163: a rail freight train also carries a second cargo produced by its source industry and accepted by its destination industry (e.g. GRAI + LVST farm to factory), wagons sized per cargo; 0 = off (default), 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "v207_rail_pax_share_pct",
      description = "V207: predicted share of town passenger production captured by a rail line (0 = legacy 22%, 1..100 = custom percentage); 0 = off (default)",
      min_value = 0, max_value = 100,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v207_rail_mail",
      description = "V207: passenger rail lines also carry mail as a secondary cargo, with wagons sized to mail production; 0 = off (default), 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "v207_rail_pax_joined_stops",
      description = "V207: maximum number of drive-through bus stops joined to each passenger rail station to extend catchment (0..4); 0 = off (default)",
      min_value = 0, max_value = 4,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v207_rail_pax_site_rank_pct",
      description = "V207: passenger rail station sites are sampled more widely and only those whose platform catchment produces at least this percentage of the best sampled site are kept (1..100); 0 = off (default, first sites found)",
      min_value = 0, max_value = 100,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v249_statue",
      description = "V249: when rich (no loan, no project pass stopped for cash during the last month, cash still covering the reserve and the most expensive listed project after the statue), build at most one town statue per month in the served town with the highest line profit; 1 = on, 0 = off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "v252_air_engine_refresh",
      description = "V252: modernize air fleet; 0 = clone the existing plane (former behaviour), 1 = buy best available engine on reinforce/crash, 2 = mode 1 + active monthly replacement when rich (default, qualified 18/10: gate A +179 k/yr, gate B +180 k/yr)",
      min_value = 0, max_value = 2,
      easy_value = 2, medium_value = 2, hard_value = 2,
      custom_value = 2,
      step_size = 1,
      flags = 0
    });
    /* Quatre niveaux a 0 : le banc qui ne passe pas le reglage reste identique.
     * Mode 1 coupe en facile/moyen meme si la valeur est 1. Mode 2 ignore le niveau. */
    AddSetting({
      name = "v250_rights",
      description = "V250 exclusive transport rights, only when difficulty is custom (3): any other level forces 0. 0 = off at easy, medium, hard and custom (default). 1 = normal policy, and only when difficulty is hard (2) or custom (3): buy in the town where we and a rival share the most station catchment, and only when rich in the V249 sense (no loan, no project pass stopped for cash, cash after the purchase still covers the reserve and the most expensive listed project). Easy and medium keep mode 1 off even if this setting is 1. A later fair_play switch will also cut mode 1. 2 = test, not filtered by difficulty or wealth: in the no-noise two-airport regime, rebuy rights in the largest towns where GetAllowedNoise is 0 and we own no airport, while cash covers the cost plus the reserve, for at most as many towns as one year of rights (one purchase lasts 12 economy months) that cash can pay. A freed slot is only logged; the normal AIR pipeline takes it. 3 = wider test: rival airport links are invisible to an AI, so buy rights in every town holding a rival airport (two-airport towns first, then by population), same cash cap; only towns saturated at purchase are watched for a freed slot. 4 = targeted: towns where a rival holds a town rating and we hold none (rival monopoly), then towns where both hold one and the population is in the top quarter of the map; each list by population, same cash cap and yearly rebuy as mode 2.",
      min_value = 0, max_value = 4,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, default_value = 0,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v264_convergent_freight",
      description = "V264: a fresh rail-freight source may deliver to an industry we already serve, by joining one platform on that station (parallel, or any anchor whose union fits station.station_spread). 0 = inert, 1 = on (default since 19/10: 40x10 PC +111.8 k/yr on 39 pairs, accepted by user waiver). Does not exempt the freight distance floor and does not change the score.",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      step_size = 1,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "v268_c70_early",
      description = "V268: early realised line profitability. 0 = off (default), 1 = shadow log at 3/6/12/24 months (decision_log), 2 = also feed C70 with the 6-month estimate of lines younger than 2 years.",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v259_bridge_renew",
      description = "V259: renew rail (and road) bridges when faster bridge types become available and vehicles are speed-limited; 0 = off (default), 1 = economic renewal triggered on new bridge types",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, default_value = 0,
      step_size = 1,
      flags = 0
    });
  }
}

RegisterAI(OpexAIInfo());
