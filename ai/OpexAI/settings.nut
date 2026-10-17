/* V167 : un seul reglage entier `probes` pilote panneaux, journal et sondes (somme de bits).
 *   1 = tout : panneaux, journal et groupes 8 a 128 (pas les verifications 256)
 *   2 = panneaux (avec veto de debug_signs=0)   4 = journal de decision
 *   8 = opcodes et ordonnanceur   16 = AIR   32 = rail   64 = route, eau et couts
 *   128 = evenements et portefeuille   256 = verifications par double calcul
 * Tout groupe de sondes active aussi le journal. Les anciens reglages individuels restent lus :
 * une sonde est active si son groupe l'est OU si son reglage propre est non nul. Seules les
 * sondes sans effet sur les decisions sont groupees. */
OPEX_PROBE_GROUPS <- {
  probe_scheduler = 8,
  probe_loop_ops = 8,
  probe_span_trace = 8,
  probe_event_backlog = 8,
  probe_candidates_road = 8,
  probe_candidates_rail = 8,
  probe_catalogue = 8,
  probe_select_reject = 16,
  c122_air_regime_shadow = 16,
  c122_air_threat_probe = 16,
  probe_rail_search = 32,
  rail_failure_audit = 32,
  probe_rail_preastar = 32,
  probe_rail_terrain = 32,
  probe_cost = 64,
  road_finance_gate_shadow_p0 = 64,
  road_quote_components_shadow_p0 = 64,
  c67_water_exposure_probe = 64,
  probe_events = 128,
  probe_vehicle_lost = 128,
  probe_portfolio = 128,
};

function OpexProbeSetting(name)
{
  local value = AIController.GetSetting(name);
  if (value <= 0 && (OPEX_PROBE_MASK & OPEX_PROBE_GROUPS[name]) != 0) return 1;
  return value;
}

/* C65 passe 2 & regroupement macro-politiques : lecture unique des reglages.
 * Fonction libre : n'affecte que des globales. Les mutations d'instance
 * restent dans Start(), juste apres l'appel. */
function OpexLoadSettings()
{
  /* --- 1. Systeme et persistance --- */
  local probes = AIController.GetSetting("probes");
  if (probes < 0) probes = 2;
  if ((probes & 1) != 0) probes = probes | 254;
  OPEX_PROBE_MASK = probes;
  DEBUG_SIGNS = (probes & 2) != 0
      && AIController.GetSetting("debug_signs") != 0;
  DECISION_LOG = (probes & 508) != 0
      || AIController.GetSetting("decision_log") != 0;
  PORTFOLIO_LOG = DECISION_LOG;
  SAVE_FULL_STATE = AIController.GetSetting("save_full_state") != 0;
  /* Résolution au chargement : aucun test ajouté aux boucles de génération au défaut. */
  ::OpexTopK <- AIController.GetSetting("homogeneous_preselect") != 0
      ? OpexTopKFund : OpexTopKLegacy;

  /* --- 2. Macro-politiques unifiees (8 groupes) --- */

  // 1. policy_caches : C41 caches cruise, acceleration, town service, served index, cash release, portfolio & air site caches
  local polCaches = AIController.GetSetting("policy_caches") != 0;
  C41_ROAD_FREIGHT_SERVED_INDEX = polCaches;
  C41_ROAD_FREIGHT_ACCEPTANCE_INDEX = polCaches;
  C41_RAIL_PAX_CRUISE_CACHE = polCaches;
  C41_RAIL_FREIGHT_CRUISE_CACHE = polCaches;
  C41_RAIL_FREIGHT_ACCELERATION_CACHE = polCaches;
  C41_RAIL_FREIGHT_TOWN_SERVICE_CACHE = polCaches;
  C41_RAIL_CASH_RELEASE = polCaches;
  PORTFOLIO_CACHE = polCaches;
  AIR_SITE_CACHE_ENABLED = polCaches;

  // V166 : interrupteurs de mode, lus avant les faisceaux policy_* qui en dependent.
  MODE_AIR = AIController.GetSetting("mode_air") != 0;
  MODE_RAIL = AIController.GetSetting("mode_rail") != 0;
  MODE_ROAD = AIController.GetSetting("mode_road") != 0;
  MODE_WATER = AIController.GetSetting("mode_water") != 0;
  V177_RAIL_PAX_MIN_DIST = AIController.GetSetting("v177_rail_pax_min_dist");
  if (V177_RAIL_PAX_MIN_DIST < 0) V177_RAIL_PAX_MIN_DIST = 0;
  V183_RAIL_ALL_FREIGHT = AIController.GetSetting("v183_rail_all_freight") != 0;
  local freightMin = AIController.GetSetting("v182_rail_freight_min_dist");
  V182_RAIL_FREIGHT_MIN_DIST = (freightMin != null && freightMin > 0) ? freightMin : 0;
  V171_RAIL_KNOTS = AIController.GetSetting("v171_rail_knots") != 0 ? 1 : 0;
  V216_PROBE = AIController.GetSetting("v216_probe") != 0;
  V211_RIVALS = AIController.GetSetting("v211_rivals_log") != 0;
  V216A_GHOST_DEMAND = AIController.GetSetting("v216a_ghost_demand");
  V216F_DWELL_PCT = AIController.GetSetting("v216f_dwell_pct");
  V178_RAIL_SHARED_DEST = AIController.GetSetting("v178_rail_shared_dest") != 0;
  V179_RAIL_GEN_DEST_SERVED = AIController.GetSetting("v179_rail_gen_dest_served") != 0;
  local wagonBoost = AIController.GetSetting("v180_rail_wagon_boost_pct");
  local boostDelay = AIController.GetSetting("v180_rail_wagon_boost_delay");
  V180_RAIL_WAGON_BOOST_DELAY = (boostDelay != null && boostDelay > 0 && boostDelay <= 5) ? boostDelay : 0;
  if (V180_START_YEAR < 0) V180_START_YEAR = AIDate.GetYear(AIDate.GetCurrentDate());
  V180_RAIL_WAGON_BOOST_PCT = (wagonBoost != null && wagonBoost > 0 && wagonBoost <= 400) ? wagonBoost : 0;
  local railSlots = AIController.GetSetting("v184_rail_search_slots");
  V184_RAIL_SEARCH_SLOTS = (railSlots != null && railSlots >= 1 && railSlots <= 4) ? railSlots : 1;
  local v182Years = AIController.GetSetting("v195_v182_years");
  V195_V182_YEARS = (v182Years != null && v182Years > 0 && v182Years <= 10) ? v182Years : 0;
  local railSlices = AIController.GetSetting("v186_rail_search_slices");
  V186_RAIL_SEARCH_SLICES = (railSlices != null && railSlices >= 1 && railSlices <= 16) ? railSlices : 1;
  V190_RAIL_DOUBLE_BUILD = AIController.GetSetting("v190_rail_double_build") != 0;
  V197_GUIDED_DOUBLE = AIController.GetSetting("v197_guided_double") != 0;
  V198_TEMPLATE_DOUBLE = AIController.GetSetting("v198_template_double") != 0;
  V200_DOUBLE_CASH_K = AIController.GetSetting("v200_double_cash_k");
  if (V200_DOUBLE_CASH_K < 0) V200_DOUBLE_CASH_K = 0;
  V199_ROBUST_BUILD = AIController.GetSetting("v199_robust_build") != 0;
  local v199LevelBudget = AIController.GetSetting("v199_level_budget_k");
  V199_LEVEL_BUDGET_K = (v199LevelBudget != null && v199LevelBudget >= 0) ? v199LevelBudget : 20;
  local v207Share = AIController.GetSetting("v207_rail_pax_share_pct");
  V207_RAIL_PAX_SHARE_PCT = (v207Share != null && v207Share >= 0 && v207Share <= 100) ? v207Share : 0;
  V207_RAIL_MAIL = AIController.GetSetting("v207_rail_mail") != 0;
  local v207Stops = AIController.GetSetting("v207_rail_pax_joined_stops");
  V207_RAIL_PAX_JOINED_STOPS = (v207Stops != null && v207Stops >= 0 && v207Stops <= 4) ? v207Stops : 0;
  local v207Rank = AIController.GetSetting("v207_rail_pax_site_rank_pct");
  V207_RAIL_PAX_SITE_RANK_PCT = (v207Rank != null && v207Rank >= 0 && v207Rank <= 100) ? v207Rank : 0;
  local v190Delay = AIController.GetSetting("v190_rail_double_delay");
  if (v190Delay == null || v190Delay < 0) v190Delay = 0;
  V190_FROM_YEAR = AIDate.GetYear(AIDate.GetCurrentDate()) + v190Delay;
  local v190Max = AIController.GetSetting("v190_rail_max_trains");
  V190_RAIL_MAX_TRAINS = (v190Max != null && v190Max >= 2 && v190Max <= 8) ? v190Max : 4;

  // 3. policy_rail : resumable A*, quotes, micro-deadline, segmented search, refleet, orders, origin sitability
  local polRail = AIController.GetSetting("policy_rail") != 0;
  RAIL_DEVIS = polRail;
  RAIL_SEARCH_RESUMABLE = polRail;
  RAIL_MICRO_DEADLINE = polRail;
  RAIL_SEGMENTED_SEARCH = polRail;
  RAIL_REFLEET = polRail;
  DYNAMIC_PATHFINDER_CAP = polRail;
  PAX_FULL_LOAD = polRail;
  ORIGIN_SITABLE = polRail;

  // 4. policy_road : road mode, street drive-through stops, refleet, fleet fix, overlap filtering
  local polRoad = AIController.GetSetting("policy_road") != 0;
  ROAD_BUILD_ENABLED = polRoad && MODE_ROAD;
  ROAD_REFLEET = polRoad;
  ROAD_FLEET_FIX = polRoad;
  PRICING_ROAD_OPS = polRoad;
  ROAD_PAX_OVERLAP = polRoad;
  ROAD_PAX_VOIRIE = polRoad;

  // 5. policy_air : air portfolio, fleet portfolio, cadence cap, line price, yield order, cheap site C36.3, joined stops, hubs
  local polAir = AIController.GetSetting("policy_air") != 0;
  AIR_PORTFOLIO = polAir;
  FLEET_PORTFOLIO = polAir;
  AIR_CADENCE_CAP = polAir;
  AIR_FLEET_LINE_PRICE = polAir;
  AIR_ROI_ORDER = polAir;
  AIR_ABANDON = polAir;
  AIR_MARGIN = polAir;
  AIR_CHEAP_SITE = polAir;
  AIR_JOINED_STOPS = polAir;
  AIR_HUB = polAir;
  AIR_HUB_FIX = polAir;

  // 6. policy_abandon : abandon memory, generation filter, transient cash guard (C22, C33)
  local polAbandon = AIController.GetSetting("policy_abandon") != 0;
  ABANDON_MEMORY = polAbandon;
  ABANDON_GEN_FILTER = polAbandon;
  ABANDON_MEMORY_TRANSIENT_GUARD = polAbandon;

  // 7. policy_portfolio : economy fix, clean density score, staged bootstrap, vivier filter, complex cargo, dynamic reserve
  local polPort = AIController.GetSetting("policy_portfolio") != 0;
  ECONOMY_FIX = polPort;
  CLEAN_DENSITY_SCORE = polPort;
  STAGED_BOOTSTRAP = polPort;
  VIVIER_RATIO_FILTER = polPort;
  COMPLEX_CARGO = polPort;
  CAPITAL_CALIBRATION = polPort;
  ROAD_FINANCE_UNBIAS_P0 = AIController.GetSetting("road_finance_unbias_p0") != 0;
  ROAD_FINANCE_GATE_SHADOW_P0 = OpexProbeSetting("road_finance_gate_shadow_p0") != 0;
  ROAD_QUOTE_COMPONENTS_SHADOW_P0 = OpexProbeSetting("road_quote_components_shadow_p0") != 0;
  DYNAMIC_CASH_RESERVE = polPort;
  C53_ORDER_NONSTOP = polPort;
  EVENT_CATALOG_INVALIDATE = polPort;

  // 8. policy_vehicle_events : crash recovery, unprofitable retirement (C52)
  local polVehEvents = AIController.GetSetting("policy_vehicle_events") != 0;
  EVENT_VEHICLE_CRASHED = polVehEvents;
  EVENT_VEHICLE_UNPROFITABLE = polVehEvents;

  /* --- 3. Calibrations physiques et options reelles --- */

  RAIL_UPGRADE_FAILURE_MEMORY = AIController.GetSetting("rail_upgrade_failure_memory") != 0;
  RAIL_GEOMETRY_GUARD = AIController.GetSetting("rail_geometry_guard") != 0;
  RAIL_GEOMETRY_EXACT_IDENTITY = AIController.GetSetting("rail_geometry_exact_identity") != 0;
  RAIL_GEOMETRY_PREFILTER = AIController.GetSetting("rail_geometry_prefilter") != 0;
  RAIL_GEOMETRY_PAIR_MEMORY = AIController.GetSetting("rail_geometry_pair_memory") != 0;
  RAIL_END_JUMP_CONNECT = AIController.GetSetting("rail_end_jump_connect") != 0;
  INCR_REVALIDATE_INDEX = AIController.GetSetting("incr_revalidate_index");
  RAIL_FAILURE_AUDIT = OpexProbeSetting("rail_failure_audit") != 0;
  RAIL_PREASTAR_PROBE = OpexProbeSetting("probe_rail_preastar") != 0;
  RAIL_GEOMETRY_LIVE_REPLAN = AIController.GetSetting("rail_geometry_live_replan") != 0;
  RAIL_TARGET_CARGO_PREFILTER = AIController.GetSetting("rail_target_cargo_prefilter") != 0;
  RAIL_TERRAIN_PROBE = OpexProbeSetting("probe_rail_terrain") != 0;

  PROJECT_TOP_K_DYNAMIC = AIController.GetSetting("project_top_k_dynamic") != 0;

  ROAD_LOADING_FIX = AIController.GetSetting("road_loading_fix") != 0;

  local roadPaxDwell = AIController.GetSetting("road_pax_dwell_days");
  if (roadPaxDwell >= 0) ROAD_PAX_STOP_DWELL_DAYS = roadPaxDwell;

  V163_MULTI_CARGO = AIController.GetSetting("v163_multi_cargo") == 1;

  TOWN_GROWTH_ENABLED = AIController.GetSetting("town_growth") != 0;
  TOWN_GROWTH_SKIP_NOOP = AIController.GetSetting("town_growth_skip_noop") != 0;
  TOWN_GROWTH_PLAN_MEMO = AIController.GetSetting("town_growth_plan_memo") != 0;
  TOWN_GROWTH_ROI_GATE = AIController.GetSetting("town_growth_roi_gate") != 0;

  /* --- 4. Sondes de diagnostic unifiees (9 groupes) --- */

  // 1. probe_cost : rail_cost_probe, air_cost_probe, road_cost_probe
  local probeCost = OpexProbeSetting("probe_cost") != 0;
  RAIL_COST_PROBE = probeCost;
  AIR_COST_PROBE = probeCost;
  ROAD_COST_PROBE = probeCost;

  // 2. probe_scheduler : C41_SLACK, BUSY, STALENESS, OPPORTUNITY, ADMISSION, C39_CLOCK, C41_SLICE
  local probeScheduler = OpexProbeSetting("probe_scheduler") != 0;
  PROBE_LOOP_OPS = OpexProbeSetting("probe_loop_ops") != 0;
  PROBE_SPAN_TRACE = OpexProbeSetting("probe_span_trace") != 0;
  PROBE_EVENT_BACKLOG = OpexProbeSetting("probe_event_backlog") != 0;
  PROBE_SELECT_REJECT = OpexProbeSetting("probe_select_reject") != 0;
  if (PROBE_EVENT_BACKLOG) {
    EVENT_BACKLOG_CALLS = 0;
    EVENT_BACKLOG_EVENTS = 0;
    EVENT_BACKLOG_MAX_BURST = 0;
    EVENT_BACKLOG_OPS_TOTAL = 0;
    EVENT_BACKLOG_OPS_MAX = 0;
    EVENT_BACKLOG_MONTH = -1;
  }
  EXP_OPCODE_EXACT = AIController.GetSetting("exp_opcode_exact") != 0;
  EXP_OPCODE_EXACT_ON = EXP_OPCODE_EXACT;
  if (EXP_OPCODE_EXACT_ON) {
    OPCODE_EXACT_STATS = null;
    OPCODE_EXACT_BREAK = null;
    OPCODE_EXACT_MISMATCHES = null;
    OPCODE_EXACT_CAL_YEAR = -1;
    OPCODE_EXACT_LATE_DATE = -1;
    OPCODE_EXACT_SITE_NAME = null;
    OPCODE_EXACT_PLAN_ONCE = null;
  }
  C41_SLACK_LEDGER = probeScheduler;
  C41_MONTHLY_BUSY_LEDGER = probeScheduler;
  C41_STALENESS_LEDGER = probeScheduler;
  C41_OPPORTUNITY_LEDGER = probeScheduler;
  C41_ADMISSION_LEDGER = probeScheduler;
  C39_PASS_CLOCK_LEDGER = probeScheduler;
  C41_RAIL_SLICE_LEDGER = probeScheduler;
  V95_SCHED_IDLE_LEDGER = probeScheduler;

  // 3. probe_candidates_road : profiles pax, freight, town sinks, feeder
  local probeCandRoad = OpexProbeSetting("probe_candidates_road") != 0;
  C41_ROAD_CANDIDATE_PROFILE = probeCandRoad;
  C41_ROAD_FREIGHT_PROFILE = probeCandRoad;
  C41_ROAD_FREIGHT_TOWN_PROFILE = probeCandRoad;

  // 4. probe_candidates_rail : profiles pax, freight, speeds, cruise, economics
  local probeCandRail = OpexProbeSetting("probe_candidates_rail") != 0;
  C41_RAIL_PORTFOLIO_PROFILE = probeCandRail;
  C41_RAIL_CANDIDATE_PROFILE = probeCandRail;
  C41_RAIL_PAX_PROFILE = probeCandRail;
  C41_RAIL_PAX_CANDIDATE_PROFILE = probeCandRail;
  C41_RAIL_PAX_ECONOMICS_PROFILE = probeCandRail;
  C41_RAIL_PAX_SPEED_PROFILE = probeCandRail;
  C41_RAIL_PAX_SPEED_DETAIL_PROFILE = probeCandRail;
  C41_RAIL_PAX_CRUISE_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_CANDIDATE_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_ECONOMICS_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_CRUISE_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_SPEED_DETAIL_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_EFFECTIVE_SPEED_PROFILE = probeCandRail;
  C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE = probeCandRail;

  // 5. probe_catalogue : invalidations C39, delta, air reason, C41 revision, water candidate/plans/site
  local probeCat = OpexProbeSetting("probe_catalogue") != 0;
  C39_INVALIDATION_PROBE = probeCat;
  C39_DECISION_DELTA_PROBE = probeCat;
  C39_AIR_REASON_PROBE = probeCat;
  C41_REVISION_PROBE = probeCat;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  if (C39_INVALIDATION_PROBE) OpexC76Reset();

  // 6. probe_rail_search : domination, fallthrough, projects cadence
  local probeRailSearch = OpexProbeSetting("probe_rail_search") != 0;
  C41_RAIL_DOMINATION_PROBE = probeRailSearch;
  C41_PROJECTS_FALLTHROUGH_PROBE = probeRailSearch;
  C39_PROJECTS_CADENCE_PROBE = probeRailSearch;

  // 7. probe_vehicle_lost : diagnostic vehicules perdus rail/global
  local probeLost = OpexProbeSetting("probe_vehicle_lost") != 0;
  C41_RAIL_LOST_TOPOLOGY_PROBE = probeLost;
  C41_RAIL_LOST_PHYSICAL_PROBE = probeLost;
  C41_RAIL_LOST_CONNECTIVITY_PROBE = probeLost;
  C41_RAIL_LOST_PROBE = probeLost;
  C41_VEHICLE_LOST_PROBE = probeLost;

  // 8. probe_portfolio : scarcity, chronology, invest C63, funnel, tension, reserves, origin relax, town rating
  local probePort = OpexProbeSetting("probe_portfolio") != 0;
  C49_SCARCITY_LEDGER = probePort;
  C50_CHRONOLOGY_PROBE = probePort;
  if (C50_CHRONOLOGY_PROBE) {
    OpexC50ResetNonExpansionLedger();
  }
  C63_INVEST_PROBE = probePort;
  if (C63_INVEST_PROBE) OpexC63ResetLedger();
  C70_MODE_CALIBRATION = AIController.GetSetting("c70_mode_calibration") != 0;
  C70_PROFIT_CALIBRATED = C70_MODE_CALIBRATION;
  ::OpexCalibratedProfit <- OpexC70Profit;
  C69_BOTTLENECK_PROBE = probePort;
  C69_DECISION_BOTTLENECK = AIController.GetSetting("c69_decision_bottleneck") != 0;
  C69_FLEET_EXEMPT = AIController.GetSetting("c69_fleet_exempt") != 0;
  C69_FLEET_DEMAND_BATCH = AIController.GetSetting("c69_fleet_demand_batch") != 0;
  C72_PLANE_CHOICE = AIController.GetSetting("c72_plane_choice");
  C83_FIXES = AIController.GetSetting("c83_fixes") != 0;
  C83_LOCAL_REPAIR = AIController.GetSetting("c83_local_repair") != 0;
  EXP_AIR_HUB_PAIR_PREFILTER = AIController.GetSetting("exp_air_hub_pair_prefilter") != 0;
  C83_PREEMPT_OPEN = AIController.GetSetting("c83_preempt_open") != 0;
  V93_AIRPORT_NO_POP_FLOOR = AIController.GetSetting("v93_airport_no_pop_floor") != 0;
  V95_AIR_POST73_YEAR = -1;
  V134_AIR_P2P_SATURATED_HUB = AIController.GetSetting("v134_air_p2p_saturated_hub") != 0;
  V133_AIR_BUILD_RETRY = AIController.GetSetting("v133_air_build_retry") != 0;
  AIR_BFAIL_DISPOSE_ORPHAN = AIController.GetSetting("air_bfail_dispose_orphan") != 0;
  C121_STATION_FLUX_LAST_DATE = -1;
  C121_STATION_FLUX_STATE = {};
  /* Amorcage plat : sans etapes, chaque regeneration apres chantier prend le
   * chemin incremental C121 au lieu d'un OpexBuildProjects complet synchrone. */
  STAGED_BOOTSTRAP = false;
  C121_CATALOG_FIRST_YEAR_ACTIVE = false;
  C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS = 4;
  C121_AIR_FIRST_LIVE_STATE = {};
  C121_AIR_FIRST_LIVE_OPS = 0;
  C121_AIR_FIRST_LIVE_SAMPLES = 0;
  C121_AIR_FIRST_LIVE_PRIORITY_STATE = {};
  {
    C121_CATALOG_CACHE.clear();
    C121_AIR_ENDPOINT_CACHE = null;
    OpexC121InvalidateEndpointGeometry();
    C121_CATALOG_TOWN_REV.clear();
    C121_CATALOG_TOWN_POP.clear();
    C121_CATALOG_TOWN_PROD.clear();
    C121_CATALOG_TOWN_CURSOR = 0;
    C121_CATALOG_TOWN_BATCH_DATE = -1;
    C121_CATALOG_AIRPORT_PRICES.clear();
    C121_CATALOG_AIRPORT_REV.clear();
    C121_CATALOG_STATION_REV.clear();
    C121_CATALOG_STATION_LINES.clear();
    C121_CATALOG_HUB_LEARN_REV.clear();
    C121_CATALOG_AIRPORT_LEARN_REV.clear();
    C121_CATALOG_ARM_LEARN_REV.clear();
    C121_CATALOG_TOWN_PRIORITY.clear();
  }
  C121_AIR_PROJECT_REALIZATION_ADAPTIVE = AIController.GetSetting("c121_air_project_realization_adaptive") != 0;
  AIR_P0_DIRECT_REALIZATION_ACTIVE = false;
  C121_AIR_P0_DIRECT_FACTOR.hubsite = 1.0;
  C121_AIR_P0_DIRECT_FACTOR.hubhub = 1.0;
  C121_AIR_PRESSURE_SNAPSHOT = null;
  C121_AIR_PRESSURE_ACCUM = null;
  C121_AIR_PRESSURE_PREV = null;
  C122_AIR_REGIME_SHADOW = OpexProbeSetting("c122_air_regime_shadow") != 0;
  C122_AIR_THREAT_RETRY = AIController.GetSetting("c122_air_threat_retry") != 0;
  C122_AIR_THREAT_PROBE = OpexProbeSetting("c122_air_threat_probe") != 0 || C122_AIR_THREAT_RETRY;
  C122_AIR_THREAT_WATCH.clear();
  C122_AIR_THREAT_SEQ = 0;
  C122_AIR_THREAT_RETRY_COUNT = 0;
  C121_AIR_ENGINE_CAPACITY_OBS.clear();
  C121_AIR_REALIZATION_FACTOR.newpair = 1.0;
  C121_AIR_REALIZATION_FACTOR.hubsite = 1.0;
  C121_AIR_REALIZATION_FACTOR.hubhub = 1.0;
  C117_AIR_LAST_DATE = -1;
  C117_AIR_LINE_STATE = {};
  C117_AIR_VEHICLE_STATE = {};
  AIR_FULL_LOAD = AIController.GetSetting("air_full_load");
  C69_TRACK_BUILDS = C69_BOTTLENECK_PROBE || C69_DECISION_BOTTLENECK || (C72_PLANE_CHOICE == 2);
  if (C69_TRACK_BUILDS) {
    C69_BUILD_DATES = [];
    C69_PENDING_FOLLOWUPS = [];
    C69_BUILD_PASS_COUNT = 0;
    C69_LAST_AFFORDABLE = null;
    C69_LAST_KDEC_DATA = null;
    C69_CACHED_KDEC_DATE = -1;
    C69_CACHED_KDEC_VALUE = 0;
    C69_PLANE_CHOICE_CALLS = 0;
    C69_PLANE_CHOICE_DIFFER_ROI = 0;
    C69_PLANE_CHOICE_DIFFER_C69 = 0;
    if (C69_BOTTLENECK_PROBE) {
      OpexC73ResetLedger();
      C80_MARGINAL_FLOOR_LEDGER = { discards = 0, discard_profit = 0 };
      C80_AIR_INC_COUNTS.full = 0;
      C80_AIR_INC_COUNTS.targeted = 0;
      C80_AIR_INC_COUNTS.none = 0;
    }
  }
  C75_MULTI_BUILD = AIController.GetSetting("c75_multi_build") != 0;
  C75_KPASS_BYPASS = AIController.GetSetting("c75_kpass_bypass") != 0;
  if (C75_KPASS_BYPASS) {
    OpexC75BypassResetYearLedger();
  }
  C75_TRACK_PASSES = C75_MULTI_BUILD || C69_BOTTLENECK_PROBE;
  if (C75_TRACK_PASSES) {
    C75_PASS_DATES = [];
    OpexC75ResetYearLedger();
  }
  MONTHLY_FUNNEL = probePort;
  TENSION_PROBE = probePort;
  if (TENSION_PROBE) {
    PORTFOLIO_LOG = true;
  }
  CASH_RESERVE_PROBE = probePort;
  PORTFOLIO_REFRESH_PROBE = probePort;
  C55_ORIGIN_RELAX_PROBE = probePort;
  if (C55_ORIGIN_RELAX_PROBE) {
    C55_ORIGIN_RELAX_LEDGER = {
      candidates_seen = 0, rejected_total = 0, both_served = 0, one_served = 0,
      one_served_pax = 0, one_served_freight = 0, duplicate_exact = 0,
      total_candidates_seen = 0, total_rejected_total = 0, total_both_served = 0,
      total_one_served = 0, total_one_served_pax = 0, total_one_served_freight = 0,
      total_duplicate_exact = 0,
    };
  }
  C55_PAX_TRACE_PROBE = probePort;
  if (C55_PAX_TRACE_PROBE) {
    C55_PAX_TRACE_LEDGER = {
      revalidated = 0, origin_blocked = 0,
      total_revalidated = 0, total_origin_blocked = 0,
    };
  }
  C60_TOWN_RATING_PROBE = probePort;
  if (C60_TOWN_RATING_PROBE) {
    C60_TOWN_RATING_LEDGER = {
      checks = 0, none = 0, ok = 0, very_poor = 0, appalling = 0,
      by_mode = {
        road = { checks = 0, refused = 0 },
        rail = { checks = 0, refused = 0 },
        air = { checks = 0, refused = 0 }
      }
    };
  }

  // 9. probe_events : C52 autoreplace, exposure, crash, unprofitable, first vehicle, C56 task trace, air fleet/catchment, equipment roi, vehicle orders
  local probeEvents = OpexProbeSetting("probe_events") != 0;
  C52_AUTOREPLACE_LOG = probeEvents;
  if (C52_AUTOREPLACE_LOG) {
    C52_AUTOREPLACE_LEDGER = {
      events = 0, remap_line_vehicles = 0, remap_line_vehicle = 0, remap_scrap_vehicles = 0,
      untracked = 0, rail = 0, road = 0, air = 0, water = 0, unknown = 0,
      line_rail = 0, line_road = 0, line_air = 0, line_water = 0,
      total_events = 0, total_remap_line_vehicles = 0, total_remap_line_vehicle = 0,
      total_remap_scrap_vehicles = 0, total_untracked = 0,
      total_rail = 0, total_road = 0, total_air = 0, total_water = 0, total_unknown = 0,
    };
  }
  C52_EVENT_EXPOSURE_PROBE = probeEvents;
  if (C52_EVENT_EXPOSURE_PROBE) {
    local c52EventFields = [
      "vehicle_crashed", "crashed_train", "crashed_other", "vehicle_waiting_in_depot",
      "industry_open", "industry_close", "town_founded", "engine_available", "vehicle_lost",
      "subsidy_offer", "subsidy_offer_expired", "subsidy_awarded", "subsidy_expired",
      "vehicle_autoreplaced", "vehicle_unprofitable", "vehicle_unprofitable_distinct",
      "aircraft_dest_too_far", "station_first_vehicle", "road_reconstruction", "engine_preview",
      "exclusive_transport_rights", "other",
    ];
    local c52EventTotals = {};
    foreach (field in c52EventFields) c52EventTotals.rawset(field, 0);
    C52_EVENT_EXPOSURE_LEDGER = {
      fields = c52EventFields, totals = c52EventTotals, unprofitable_vehicles = {},
      vehicle_crashed = 0, crashed_train = 0, crashed_other = 0, vehicle_waiting_in_depot = 0,
      industry_open = 0, industry_close = 0, town_founded = 0, engine_available = 0,
      vehicle_lost = 0, subsidy_offer = 0, subsidy_offer_expired = 0, subsidy_awarded = 0,
      subsidy_expired = 0, vehicle_autoreplaced = 0, vehicle_unprofitable = 0,
      vehicle_unprofitable_distinct = 0, aircraft_dest_too_far = 0, station_first_vehicle = 0,
      road_reconstruction = 0, engine_preview = 0, exclusive_transport_rights = 0, other = 0,
    };
  }
  C52_CRASH_LOG = probeEvents;
  C52_UNPROFITABLE_LOG = probeEvents;
  C52_STATION_FIRST_VEHICLE_LOG = probeEvents;
  C56_TASK_TRACE = probeEvents;
  if (C56_TASK_TRACE) C56_LOOP_TICK_COUNT = 0;
  AIR_FLEET_PROBE = probeEvents;
  AIR_CATCHMENT_PROBE = probeEvents;
  EQUIPMENT_ROI_PROBE = probeEvents;
  C54_VEHICLE_ORDERS_PROBE = probeEvents;
  C78_SLOT_INTERCEPT_PROBE = probePort;

  /* --- 5. Pistes formellement abandonnees / constantes neutres verrouillees --- */
  /* R7 : zero global conserve ; le reglage defensif C121 ne retablit pas de plancher positif. */
  PORTFOLIO_FLOOR_PCT = 0;
  ROAD_TIME_SCALED_CAP = AIController.GetSetting("road_time_scaled_cap") != 0;
  C76_REGEN_TARGETED = AIController.GetSetting("c76_regen_targeted") != 0;
  C67_TERRAIN_MAP = AIController.GetSetting("c67_terrain_map") != 0;
  C67_WATER_EXPOSURE = OpexProbeSetting("c67_water_exposure_probe") != 0;
  C67_SLACK_HOOK = C67_TERRAIN_MAP || C67_WATER_EXPOSURE;
  /* C77 corrige est permanent et repose sur le socle du double registre. */
  C80_WORKER_RAIL = AIController.GetSetting("c80_worker_rail") != 0;
  C80_RAIL_STOCK_GATE = AIController.GetSetting("c80_rail_stock_gate") != 0;
  C80_RAIL_STOCK_WORKER = C80_RAIL_STOCK_GATE && (AIController.GetSetting("c80_rail_stock_worker") != 0);
  C80_WORKER_TOWN = AIController.GetSetting("c80_worker_town") != 0;
  C76_FREIGHT_ROTATION = C76_REGEN_TARGETED && (AIController.GetSetting("c76_freight_rotation") != 0);
  C80_MODE_REGEN = C76_REGEN_TARGETED && (AIController.GetSetting("c80_mode_regen") != 0);
  C80_AIR_CHOICE_MEMO = AIController.GetSetting("c80_air_choice_memo") != 0;
  C80_AIR_EVAL_FAST = AIController.GetSetting("c80_air_eval_fast") != 0;
  C41_RAIL_LOST_SIGNAL_REPAIR = false;
  C41_RAIL_LOST_JUNCTION_REPAIR = false;
  RAIL_EXPAND = AIController.GetSetting("rail_expand") != 0;
  V127_IDLE_CASH_ROAD_REGEN = AIController.GetSetting("v127_idle_cash_road_regen") != 0;
  V127_LAST_MONTH = -1;
  V127_LAST_ROAD_REGEN_DATE = -1;
  local railRefill = AIController.GetSetting("v217_rail_refill");
  V217_RAIL_REFILL = (railRefill != null && railRefill >= 0 && railRefill <= 2) ? railRefill : 0;
  V217_LAST_MONTH = -1;
  AIR0310_SITE_VALIDITY_STATE = null;
  RAIL_DEPOT_COST = AIController.GetSetting("rail_depot_cost") != 0;
  V89_RAIL_SEARCH_THROUGHPUT = AIController.GetSetting("v89_rail_search_throughput") != 0;
  if (C80_RAIL_STOCK_WORKER) V89_RAIL_SEARCH_THROUGHPUT = false;
  V90_FAST_PATHFINDER = AIController.GetSetting("v90_fast_pathfinder") != 0;
  V129_RAIL_ASTAR_EXACT_OPT = AIController.GetSetting("v129_rail_astar_exact_opt") != 0;
  V131_RAIL_REPAIR = AIController.GetSetting("v131_rail_repair") != 0;
  V131_TOWN_CLEARANCE = AIController.GetSetting("v131_town_clearance") != 0;
  V139_FEEDER_BUS = AIController.GetSetting("v139_feeder_bus") != 0;
  SUBSIDY_RESELECT_IF_PURGED = AIController.GetSetting("subsidy_reselect_if_purged") != 0;
  SELECT_BISECT_INSERT = AIController.GetSetting("select_bisect_insert") != 0;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  AIR_MAX_DISTANCE = 0;
  TRANSIT_COST_PERMILLE = 0;
  INFRA_AMORT_PCT = 0;
  PORTFOLIO_MAX_BATCH = 1;
  AIR_FLEET_BUFFER = 0;
}
