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
    AddSetting({ name = "po01c_regen_split",
      description = "PO01C: resumable reactive regeneration (experimental)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "v278_air_lazy_sites",
      description = "V278: population ordered lazy AIR sites and scan preparation cache; 0 = off, 1 = on, 2 = auto: on when the map has at least 1024x1024 tiles (default since 20/10, qualified at 1024x1024 only)",
      min_value = 0, max_value = 2,
      easy_value = 2, medium_value = 2, hard_value = 2, custom_value = 2,
      flags = 0 });
    AddSetting({ name = "v279_reselect_memo",
      description = "V279: incremental memoization for OpexReselectProjects (0=historic, 1=memoized, 2=control check, 3=auto: 1 when the map has at least 1024x1024 tiles, else 0; default since 20/10, qualified at 1024x1024 only)",
      min_value = 0, max_value = 3,
      easy_value = 3, medium_value = 3, hard_value = 3, custom_value = 3,
      flags = 0 });
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
      name = "air_flotte1_shadow",
      description = "AIR-FLOTTE-1: log read-only AIR purchase and RAIL shortlist snapshots; diagnostic only, 0 = off (default), 1 = on",
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
      name = "v269_rail_late_relax",
      description = "V269: N years after game start, when the rail pool is empty and cash idle, regenerate rail freight up to 250 tiles; 0 = inert, 5 = default (20/10, 40x10 +83.1 k/yr, 24/16)",
      min_value = 0, max_value = 9,
      easy_value = 5, medium_value = 5, hard_value = 5,
      custom_value = 5,
      step_size = 1,
      flags = 0
    });

    AddSetting({
      name = "v284_rail_growth",
      description = "V284: 0 = off; N = grow saturated existing freight trains after N years with 1M cash, preserve speed, then passing loop and second train at platform limit (default 3 since 20/10, user decision after 40x10 +136 k)",
      min_value = 0, max_value = 10,
      easy_value = 3, medium_value = 3, hard_value = 3, custom_value = 3,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v294_rail_defer",
      description = "V294h: 0 = off; N = rail A* first tries N iterations in the search slot, then an aborted search continues in the background on leftover tick opcodes (20000 iterations, 365 days) and its path is reused when the pair is selected again",
      min_value = 0, max_value = 5000,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 100, flags = 0
    });

    AddSetting({
      name = "v301_notrain_fix",
      description = "V301: NOTRAIN fixes, bit mask. 1 = NOTRAIN/ORDFAIL abandons the pair; 2 = freight trains capped by vehicle.max_train_length; 4 = trim wagons that would not fit instead of failing; 8 = any TRKFAIL abandons the pair. 0 = historic; 15 = all (default since 21/10)",
      min_value = 0, max_value = 15,
      easy_value = 15, medium_value = 15, hard_value = 15, custom_value = 15,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v307_long_probe",
      description = "V307: measurement only. At game start, N town pairs per distance bin (120-179, 180-249, 250-349) are path-searched by the production A* (20k iterations), a coarse block A* and a corridor-guided A*; blocking, for solo measurement games. 0 = inert (default)",
      min_value = 0, max_value = 9,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v309_idle_probe",
      description = "V309: passive monthly idle-loop, opcode and financial wait instrumentation; requires decision_log=1. 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 1, flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "v307_probe_year",
      description = "V307: years after game start at which the v307_long_probe measurement runs (1 January); 0 = at start",
      min_value = 0, max_value = 9,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v308_carto_probe",
      description = "V308: passive one-shot survey of 400 random 8x8 blocks; 64-tile ground truth vs V307 and four six-point patterns; uses v307_probe_year. Blocking measurement only, 0 = off (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v307_abnd_autopsy",
      description = "V307: measurement only, needs decision_log. After each production rail search abandoned at its budget, rerun it blocking as fresh unsegmented forward and reverse A* (20k iterations) to tell an enclosed goal from a budget shortfall. 0 = inert (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v307_sites",
      description = "V307 1.8 experimental rail station sites: 0 = historical spiral (default), 1 = native dispersed, 2 = spiral first with native octant supplementation, 3 = spiral continued past its stop ring in missing octants only, budgeted",
      min_value = 0, max_value = 3,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v307_sink_room",
      description = "V307 1.9b experimental first freight industry sink: 1 = reserve opposite parallel platform strip, 2 = construct 2-platform destination station (includes reserve), 3 = both. 0 = historical (default)",
      min_value = 0, max_value = 15,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v294_rail_weight_adapt",
      description = "V294c: 0 = historic A* weights; N = initial weight 100..400%, lower to historic then 100% only after a stalled rail segment",
      min_value = 0, max_value = 400,
      easy_value = 400, medium_value = 400, hard_value = 400, custom_value = 400,
      step_size = 1, flags = 0
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
      name = "v275_rail_pax_mm",
      description = "V275: passenger rail compatible with air (bitmask): 1 = no passenger rail pair touching a town served by one of our airports, 2 = V212 recalibration (revenue 150 %, capital 85 %), 4 = with air enabled, no passenger rail candidate before the third year, 8 = by mode: without air, bits 1/2/4 plus the V207 package (share 40, mail, 2 joined stops) when V207 settings are at their defaults; with air, whole mask cleared; 15 = default, 0 = off",
      min_value = 0, max_value = 15,
      easy_value = 15, medium_value = 15, hard_value = 15,
      custom_value = 15,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v249_statue",
      description = "V249 town statues when rich. 0 = off. 1 = mode 1: build at most one statue per month in served town with highest line profit, requiring cash to cover reserve and most expensive listed project. 2 = mode 2 (V249a+b+c, default since 21/10): buy statue whenever predicted annual marginal gain over horizon covers measured cost, without cash reserve, preserving admissible financeable projects and pending fleet renewal (V252).",
      min_value = 0, max_value = 2,
      easy_value = 2, medium_value = 2, hard_value = 2,
      custom_value = 2, default_value = 2,
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
      name = "v276_cand_slices",
      description = "V276: resumable rail and road candidate units, 0 = legacy, 1 = freight ordered by unit income at 80 tiles, 2 = same income times total monthly cargo production (annual cache), 3 = auto: 2 when the map has at least 1024x1024 tiles, else 0 (default since 20/10)",
      min_value = 0, max_value = 3,
      easy_value = 3, medium_value = 3, hard_value = 3, custom_value = 3,
      step_size = 1, flags = 0
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
    AddSetting({
      name = "v277_air_pub_fast",
      description = "V277: fast air project publication and indexed re-selection filter; 0 = historical path, 1 = fast paths, 2 = control mode (runs both, logs differences, keeps historical), 3 = auto: 1 when the map has at least 1024x1024 tiles, else 0 (default since 20/10, qualified at 1024x1024 only)",
      min_value = 0, max_value = 3,
      easy_value = 3, medium_value = 3, hard_value = 3,
      custom_value = 3, default_value = 3,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v294_rail_bridge_len",
      description = "V294: maximum rail bridge and tunnel length in A* pathfinder (0 = legacy 6/tiles limit 5; N in 1..30 = max length in tiles)",
      min_value = 0, max_value = 30,
      easy_value = 20, medium_value = 20, hard_value = 20,
      custom_value = 20, default_value = 20,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v294_rail_continuous",
      description = "V294: 0 = legacy segmented search; 1 = continuous single A* search for rail lines, preserving closed set across chunks",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, default_value = 0,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v294_rail_weight_pct",
      description = "V294c: unified rail A* heuristic weight percentage across all distances (AAA uses 200 everywhere); 0 = off (uses V91/V172 distance-based weight, default), 100..400 = weight pct",
      min_value = 0, max_value = 400,
      easy_value = 200, medium_value = 200, hard_value = 200,
      custom_value = 200, flags = 0, step_size = 1
    });
    AddSetting({
      name = "v294_rail_aaa_costs",
      description = "V294d: align rail A* cost table with AAAHogEx (tunnel 0/tile + overcost >7 and >11, bridge 100/tile + overcost, level crossing +900, diagonal 67); 0 = off (default), 1 = on",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "v294_rail_reverse_probe",
      description = "V294f: reverse A* probe before rail search (sources = B, goals = A) bounded by N iterations (e.g. 300, like AAA); 0 = off (default), >0 = iteration cap",
      min_value = 0, max_value = 5000,
      easy_value = 300, medium_value = 300, hard_value = 300,
      custom_value = 300, flags = 0, step_size = 50
    });
    AddSetting({
      name = "v294_rail_dist_decouple",
      description = "V294i: decouple candidate railMax from iteration cap (HARD_ITERATION_CAP*12/10); 0 = off (uses derived/V168 bound, default), >0 = max tile distance",
      min_value = 0, max_value = 500,
      easy_value = 200, medium_value = 200, hard_value = 200,
      custom_value = 200, flags = 0, step_size = 10
    });
    AddSetting({
      name = "v294_rail_slope_engine",
      description = "V294j: consider engine strength in rail A* costs (slope 1500, turn 100 if weak); 0 = disabled (default), 1 = enabled",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "v295_astar_fast",
      description = "V295: exact opcode optimizations for rail A* V129 (parent chain bloom filter and deduplicated goal coords); 0 = off (default), 1 = on",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "v292_hq_hub",
      description = "V292b: build company HQ once near passenger station with highest waiting cargo; 0 = off, 1 = on (default since 21/10)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "v296_rail_batch_build",
      description = "V296a: lay each straight or diagonal run of rail track with one BuildRail command instead of one per tile (fewer suspended ticks); 0 = off, 1 = on (default since 21/10)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "v296_astar_native",
      description = "V296b: native AIList rail A*; 0 = V129, 1 = native (default since 21/10), 2 = compare with V129",
      min_value = 0, max_value = 2,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "rail_cal",
      description = "RAIL-CAL-1 experimental: correct only the ranking score of unbuilt RAIL candidates for predicted cost and profit; 0 = legacy (default), 1 = test",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, default_value = 0,
      flags = 0, step_size = 1
    });
  }
}

RegisterAI(OpexAIInfo());
