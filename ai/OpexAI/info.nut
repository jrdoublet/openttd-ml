class OpexAIInfo extends AIInfo {
  function GetAuthor()      { return "openttd-ml"; }
  function GetName()        { return "OpexAI"; }
  function GetDescription() { return "IA multimodale : meilleur ROI par origine/destination, puis revenu maximise sous contraintes de capital et d'opcodes."; }
  function GetVersion()     { return 8; }
  function GetDate()        { return "2026-10-24"; }
  function CreateInstance() { return "OpexAI"; }
  function GetShortName()   { return "OPEX"; }
  function GetAPIVersion()  { return "15"; }

  /* Le bit 2 de probes commande les panneaux : le joueur peut le couper
   * dans une partie partagee avec des humains.
   * Entre IA, la regle est de jouer a armes egales, sans auto-handicap. */
  function GetSettings()
  {
    AddSetting({ name = "multi1_road_priority",
      description = "MULTI-1 early multimodal road priority: 0=historical (default), 1=shadow, 2=one bounded top-K road promotion in 1971-73",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "multi1_air_over_rail",
      description = "MULTI-1 1971-73 multimodal: 0=off (default), 1=shadow, 2=promote one funded AIR ahead of unprepared RAIL head",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "multi1_road_detour",
      description = "MULTI-1 road TRACEX rescue in 1971-73: 0=off (default), 1=shadow, 2=bounded extra doglegs",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "eb2_new_station_fallback",
      description = "EB-2: fallback to normal stations when shared destination join fails (default 0)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "n75_multi_cargo",
      description = "1972+ cash-idle rail refill: 0=off, 1=shadow, 2=one extra freight cargo on empty funded rail pool (default 2)",
      min_value = 0, max_value = 2,
      easy_value = 2, medium_value = 2, hard_value = 2, custom_value = 2,
      flags = 0 });
    AddSetting({ name = "c77_intent_defer",
      description = "C77: defer intents (1=portfolio/worker, 2=also AIR year/subsidy expiry; default 2 since 23/10, porte B pass)",
      min_value = 0, max_value = 2,
      easy_value = 2, medium_value = 2, hard_value = 2, custom_value = 2,
      flags = 0 });
    AddSetting({ name = "po01c_regen_split",
      description = "PO01C: resumable reactive regeneration (default 1 since 23/10, user decision after neutral porte A)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
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
    AddSetting({ name = "p6_air_firstline_window",
      description = "P6 experimental first AIR line: 0=immediate historical build (default), 1=wait for at most one additional catalog publication (32 ticks / 160000 scan opcodes) when two affordable distinct AIR pairs are already selected",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "air_fleet_yield_rightsize",
      description = "P3 mature AIR 2->3+ reinforcement: 0=off (default), 1=C117 shadow, 2=conservative low-yield veto",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "front_pax2_bounded_overlap",
      description = "FRONT-PAX-2 AIR PASS only: 0=historical (default), 1=passive bounded shortlist, 2=up to one additional C121 candidate per arm per completed ALL-band scan",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "rail_cargo_opportunity_rank",
      description = "P2 prepared RAIL freight opportunity: 0=historical (default), 1=passive top-K shadow, 2=one adjacent same-C77-tier promotion (8% score, 93% fund, 80% profit)",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "rail_long_value_rank",
      description = "P1: C121/C80 one-train freight 160-300 beyond railMax; 0=off (default), 1=passive proxy shadow, 2=one physically prepared long option",
      min_value = 0, max_value = 2,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({ name = "multi1_road_cargo_shadow",
      description = "MULTI-1: passive secondary ROAD freight cargo probe on 256 maps, 1971-1973; <=16 pairs and <=3 physical plans per monthly observation. 0=off (default), 1=shadow only",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    AddSetting({ name = "front_pax1_bounds_probe",
      description = "FRONT-PAX-1: passive one-log-per-bounds-refresh road/rail and rail/air clamp reasons, 0=off (default), 1=log; no candidate or policy changes",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });
    /* --- 1. Systeme et instrumentation --- */

    /* V167 : un seul entier pilote panneaux, journal et sondes (somme de bits, voir settings.nut).
     * Defaut publication 0 = carte vierge ; les harnais injectent probes=2. */
    AddSetting({
      name = "probes",
      description = "Diagnostics bitmask (signed 31 bits): 0 none (default), 1 all, 2 signs, 4 legacy log, 8/16/32/64/128 legacy groups, 256 decision log only, 512..1073741824 individual channels (see docs/audit_sondes_20261022.md); groups also enable decision log; 67108864 V309 idle needs +256 for logs (67109120)",
      min_value = 0, max_value = 2147483647,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = 0
    });

    AddSetting({ name = "v286_rail_flow_probe",
      description = "V286 passive RAIL cargo/vehicle/industry snapshots: 0=off (default), 1=sample 16 lines every 30 game days; no policy change",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });

    AddSetting({ name = "c75_year_ledger_skip",
      description = "C75 opcode experiment: 0=keep annual counters (default), 1=skip only when C49/C69 diagnostics are off; K_pass unchanged",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });

    AddSetting({ name = "c75_bypass_ledger_skip",
      description = "C75 bypass diagnostic experiment: 0=keep log/signs (default), 1=skip ledger when signs and decision log are off; K_pass bypass unchanged",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = AICONFIG_BOOLEAN });

    /* Les panneaux requis par les sweeps restent actifs avec probes=2. */
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

    /* Les canaux de mesure sont commandes par probes (bits dedies ou groupes). */
    AddSetting({
      name = "c121_air_project_realization_adaptive",
      description = "C121 adaptive AIR strategy: use the learned reused-hub realization correction in observe, race and efficiency; 1 = on (default), 0 = off",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });

    AddSetting({
      name = "road1y_load_orders",
      description = "ROAD1Y: Align road vehicle orders on AAAHogEx (freight sink UNLOAD|NO_LOAD, pax source FULL_LOAD_ANY); 0 = off (default), 1 = on",
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
      name = "road100_solo_pax",
      description = "ROAD100: Generate profitable town-to-town buses only in ROAD-only games; 0 = off (default), 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_town_bus",
      description = "ROAD100-2: Generate intratown bus routes only in ROAD-only games; 0 = off (default), 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_road_batch",
      description = "ROAD100-3: Build up to four profitable ROAD lines per pass in ROAD-only games while preserving cash; 0 = off (default), 1 = on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_freight_diversity",
      description = "ROAD100-21: ROAD-only, score up to three freight cargos per rebuild with bounded work; 0=off, 1=on (default on this branch)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_freight_cargo_origin",
      description = "ROAD100-22: ROAD-only freight source and sink separation by cargo; physical checks unchanged, 0=off (default), 1=on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_batch_roi_15",
      description = "ROAD100-23: ROAD-only batch second build minimum predicted ROI 15% instead of 25%; retain cash reserve and physical checks, 0=off (default), 1=on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_freight_berths",
      description = "ROAD100-24: ROAD-only, add real joined truck berths to mature profitable freight lines before fleet expansion; 0=off (default), 1=on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_live_filter",
      description = "ROAD100-25: ROAD-only, drop stale already-served bus-town candidates before ranking, including PO01C publications; 0=off (default), 1=on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_berth_balance",
      description = "ROAD100-26: ROAD-only, add one real joined bus berth to the bottleneck end of a mature profitable PAX line before fleet growth; 0=off (default), 1=on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_double_berths",
      description = "ROAD100-28: ROAD-only, add physical joined bus berths on both ends of a mature profitable PAX route in separate years, then refleet on real waiting; off by default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_mail_intertown",
      description = "ROAD100-27: ROAD-only MAIL town-to-town with real truck stops; 0=off (default), 1=short diagnostic, 2=existing-road long with profitability guard",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      min_value = 0, max_value = 2, step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "road100_pax_intercity_roots",
      description = "ROAD100-29: ROAD-only passive PAX site/coverage probe for intercity distances 43..80; no projects, no builds, default off",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_producer_units",
      description = "ROAD100-30a: ROAD-only site-first PAX, convert actual producer counts to estimated monthly PAX using town production share; 0=off (default), 1=on",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_initial_berth_fleet",
      description = "ROAD100-31: ROAD-only, extra initial PAX buses after two actual joined terminus berths and incremental ROI guard, requires producer units; 0=off default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_segmented_corridor",
      description = "ROAD100-32: bounded local gaps to build real PAX corridors 80..170 in ROAD-only mode; requires long_build, 0=off default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_sparse_corridor",
      description = "ROAD100-33: sparse bounded roadway segments for physical PAX corridors 80..170; ROAD-only long_build required, 0=off default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_long_market_probe",
      description = "ROAD100-34: passive PASS/month root-site telemetry BEFORE long road preflight; ROAD-only long_build required, 0=off default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_portal_stitch",
      description = "ROAD100-35: short urban scanner and road portal corridor trial in ROAD-only, requires sparse+long_build; 0=off default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_graph_bridge",
      description = "ROAD100-36: ROAD-only high-capture PAX sites with bounded real-road graph bridge at distances 43..170; requires long_build, 0=off default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_town_voirie",
      description = "ROAD100-2b: Use existing road BFS for intratown bus routes; requires road100_town_bus=1 in ROAD-only games, off by default",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_fleet_cap",
      description = "ROAD100-4: Experimental intratown bus fleet cap, 0=physical historical 2 (default), 8=up to eight; risk of station queues",
      min_value = 0, max_value = 8,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "road100_town_roi_post",
      description = "ROAD100-5: Require at least 25% annual expected profit/capital after actual route planning for ROAD-only intratown bus routes; 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_intercity_site_fleet",
      description = "ROAD100-6: Intercity ROAD-only pax demand verified on actual sites; scale fleet to up to 30 buses only after physical capture, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_site_first",
      description = "ROAD100-7: ROAD-only bus candidates ranked after bounded buildable-stop capture and route planning; requires road100_solo_pax=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_joined_stops",
      description = "ROAD100-8: ROAD-only site-first bus stations try one joined catchment satellite per town; requires road100_site_first=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_multicatchment",
      description = "ROAD100-9: ROAD site-first may add passenger connections to already served towns only with physically disjoint stop coverage; requires road100_site_first=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road1y_dist_bands",
      description = "ROAD1Y: Freight road candidate generation by decreasing distance bands (64-128, 32-63, 7-31) and 128-tile traces; 0 = off, 1 = on (default)",
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road1y_fleet",
      description = "ROAD1Y: road vehicles allowed per stop pair from the first year, bought monthly on measured waiting cargo (0=off, historical cap of 2; default 4)",
      min_value = 0, max_value = 16,
      easy_value = 4, medium_value = 4, hard_value = 4,
      custom_value = 4,
      flags = 0
    });
    AddSetting({
      name = "road100_wait_fleet",
      description = "ROAD100-10: ROAD-only profitable mature bus routes expand fleet cautiously using actual station waiting; requires road100_site_first=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_site_window",
      description = "ROAD100-11: ROAD-only site-first physical preflights diversify lower-ranked towns within the existing opcode budget; requires road100_site_first=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_site_near",
      description = "ROAD100-12: ROAD-only site-first preflights nearby positive-proxy town pairs before distant pairs at fixed budget; requires road100_site_first=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_detour",
      description = "ROAD100-13: ROAD-only site-first try bounded two-corner physical road detours after existing roads and L fail; requires road100_site_first=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_tour",
      description = "ROAD100-14: ROAD-only extend a profitable existing passenger line to a third independent station with four orders; requires road100_solo_pax=1, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
    });
    AddSetting({
      name = "road100_pax_portfolio",
      description = "ROAD100-20: ROAD-only site-first multi-district passenger coverage, pre-build union and station-joined satellites with demand-based fleet; exclusive of old ROAD100-8, 0=off (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
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
      name = "dist_bornes_v276_freight",
      description = "DIST-BORNES-1: 1 = preserve V269 late freight relaxation in deferred V276 scans, including the spatial grid and freight band; 0 = historical V276 (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      default_value = 0, step_size = 1, flags = 0
    });
    AddSetting({
      name = "estim_unifie",
      description = "ESTIM-1: 1 revenue, 2 cash, 4 marginal operations, 8 physical primitives, 16 distance-dependent RAIL revenue and score cost; 0 = historical (default)",
      min_value = 0, max_value = 31,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      default_value = 0, step_size = 1, flags = 0
    });
    AddSetting({
      name = "dist_bornes_unified",
      description = "DIST-BORNES-1: 1 = one route, passenger rail, freight rail and air candidate distance window shared by all generators, PO01C, V276 and C42; 0 = historical filters (default)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      default_value = 0, step_size = 1, flags = 0
    });

    AddSetting({
      name = "v233_long_good",
      description = "V233L: observed fed-factory GOOD exports, 150-300 tiles, two trains and backlog growth; 0=off, 1=on (default 1 since 27/10, user decision)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v233_site_funnel",
      description = "V233L urban site B: 0 = spiral, 1 = native funnel (buildable rectangle, GOOD acceptance, then squirrel checks; default 1 since 27/10, user decision)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v233_funnel_center_test",
      description = "V233L funnel center pre-test: 0 = off, 1 = skip town if center acceptance < 8 (default 1, active if v233_site_funnel=1)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
      step_size = 1, flags = 0
    });

    AddSetting({
      name = "v284_rail_growth",
      description = "V284: 0 = off; N = grow saturated existing freight trains after N years with 1M cash, preserve speed, then passing loop and second train at platform limit (default 3 since 20/10, user decision after 40x10 +136 k)",
      min_value = 0, max_value = 10,
      easy_value = 3, medium_value = 3, hard_value = 3, custom_value = 3,
      step_size = 1, flags = 0
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
      name = "v307_probe_year",
      description = "V307: years after game start at which the v307_long_probe measurement runs (1 January); 0 = at start",
      min_value = 0, max_value = 9,
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
      name = "station_plan_precheck",
      description = "PO-02: skip non-buildable or non-flat base tiles before rail station orientations; 0 = historical, 1 = precheck (default since 23/10, porte B pass)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
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
      name = "c67_terrain_map",
      description = "C67.4: block terrain map filled in tick slack before Sleep, no consumer: 1 = enabled, 0 = disabled (default)",
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0,
      flags = AICONFIG_BOOLEAN
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
      description = "V200: double-track machinery only when cash net of loan >= this (k GBP) and cash >= 2x single quote; 0 = always (inert)",
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
      description = "V275: passenger rail compatible with air (bitmask): 1 = no passenger rail pair touching a town served by one of our airports, 2 = V212 recalibration (revenue 150 %, capital 85 %), 4 = retired 24/10 (no effect), 8 = by mode: without air, bits 1/2/4 plus the V207 package (share 40, mail, 2 joined stops) when V207 settings are at their defaults; with air, whole mask cleared; 15 = default, 0 = off",
      min_value = 0, max_value = 15,
      easy_value = 15, medium_value = 15, hard_value = 15,
      custom_value = 15,
      step_size = 1,
      flags = 0
    });
    AddSetting({
      name = "v249_statue",
      description = "V249 town statues when rich. 0 = off. 1 = mode 1: build at most one statue per month in served town with highest line profit, requiring cash to cover the most expensive listed project. 2 = mode 2 (V249a+b+c, default since 21/10): buy statue whenever predicted annual marginal gain over horizon covers measured cost, preserving admissible financeable projects and pending fleet renewal (V252).",
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
      description = "V250 exclusive transport rights, only when difficulty is custom (3): any other level forces 0. 0 = off at easy, medium, hard and custom (default). 1 = normal policy, and only when difficulty is hard (2) or custom (3): buy in the town where we and a rival share the most station catchment, and only when rich in the V249 sense (no loan, no project pass stopped for cash, cash after the purchase still covers the most expensive listed project). Easy and medium keep mode 1 off even if this setting is 1. A later fair_play switch will also cut mode 1. 2 = test, not filtered by difficulty or wealth: in the no-noise two-airport regime, rebuy rights in the largest towns where GetAllowedNoise is 0 and we own no airport, while cash covers the cost, for at most as many towns as one year of rights (one purchase lasts 12 economy months) that cash can pay. A freed slot is only logged; the normal AIR pipeline takes it. 3 = wider test: rival airport links are invisible to an AI, so buy rights in every town holding a rival airport (two-airport towns first, then by population), same cash cap; only towns saturated at purchase are watched for a freed slot. 4 = targeted: towns where a rival holds a town rating and we hold none (rival monopoly), then towns where both hold one and the population is in the top quarter of the map; each list by population, same cash cap and yearly rebuy as mode 2.",
      min_value = 0, max_value = 4,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, default_value = 0,
      step_size = 1,
      flags = 0
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
      name = "v292_hq_hub",
      description = "V292b: build company HQ once near passenger station with highest waiting cargo; 0 = off, 1 = on (default since 21/10)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "air_site_ranked",
      description = "Airport sites: native ranked bands with spiral fallback (0 off, 1 on)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({
      name = "air_site_probe",
      description = "Solo site probe, no construction: 0 off, 1 spiral, 2 hybrid, 3 initial, 4 bands, 5 border, 6 funnel, 7 strict, 8 strict_full, 9 oracle, 10 ranked",
      min_value = 0, max_value = 10,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = 0, step_size = 1
    });
    AddSetting({
      name = "air_site_funnel",
      description = "Airport site search: 0 = ring spiral, 1 = same spiral with a native footprint predicate (default 1 since 27/10, user decision)",
      min_value = 0, max_value = 1,
      easy_value = 1, medium_value = 1, hard_value = 1,
      custom_value = 1, flags = 0, step_size = 1
    });
    AddSetting({ name = "air_load_min_pct",
      description = "AIR-LOAD-1: minimum AIR load for fleet growth (0=off; 6 completed legs required, last 12 legs)",
      min_value = 0, max_value = 100, step_size = 5,
      easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
      flags = 0 });
    AddSetting({
      name = "road100_long_intercity",
      description = "ROAD100-16: 0 off; 1 read-only physical and financial shadow of long intercity bus corridors 80..170 tiles, ROAD solo/site-first only",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = 0, step_size = 1
    });
    AddSetting({
      name = "road100_long_build",
      description = "ROAD100-16 v6: 0 off; 1 opt-in financially guarded long intercity physical bus corridor build (requires long_intercity and ROAD solo site-first)",
      min_value = 0, max_value = 1,
      easy_value = 0, medium_value = 0, hard_value = 0,
      custom_value = 0, flags = 0, step_size = 1
    });
  }
}

RegisterAI(OpexAIInfo());
