/* C65 passe 2 & regroupement macro-politiques : lecture unique des reglages.
 * Fonction libre : n'affecte que des globales. Les mutations d'instance
 * restent dans Start(), juste apres l'appel. */
function OpexLoadSettings()
{
  /* --- 1. Systeme et persistance --- */
  DEBUG_SIGNS = AIController.GetSetting("debug_signs") != 0;
  DECISION_LOG = AIController.GetSetting("decision_log") != 0;
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

  // C68: air route plane selection
  AIR_ROUTE_PLANE_SELECTION = AIController.GetSetting("air_route_plane_selection") != 0;

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
  ROAD_BUILD_ENABLED = polRoad;
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
  DYNAMIC_CASH_RESERVE = polPort;
  C53_ORDER_NONSTOP = polPort;
  EVENT_CATALOG_INVALIDATE = polPort;

  // 8. policy_vehicle_events : crash recovery, unprofitable retirement (C52)
  local polVehEvents = AIController.GetSetting("policy_vehicle_events") != 0;
  EVENT_VEHICLE_CRASHED = polVehEvents;
  EVENT_VEHICLE_UNPROFITABLE = polVehEvents;

  /* --- 3. Calibrations physiques et options reelles --- */

  LOAN_REPAY_FLOOR = AIController.GetSetting("loan_repay_floor_k") * 1000;
  HARD_ITERATION_CAP = AIController.GetSetting("pathfinder_hard_cap_k") * 1000;
  RAIL_UPGRADE_FAILURE_MEMORY = AIController.GetSetting("rail_upgrade_failure_memory") != 0;
  RAIL_GEOMETRY_GUARD = AIController.GetSetting("rail_geometry_guard") != 0;
  RAIL_GEOMETRY_EXACT_IDENTITY = AIController.GetSetting("rail_geometry_exact_identity") != 0;
  RAIL_GEOMETRY_PREFILTER = AIController.GetSetting("rail_geometry_prefilter") != 0;
  RAIL_GEOMETRY_PAIR_MEMORY = AIController.GetSetting("rail_geometry_pair_memory") != 0;
  RAIL_GEOMETRY_LIVE_REPLAN = AIController.GetSetting("rail_geometry_live_replan") != 0;
  RAIL_ORIGIN_REUSE = AIController.GetSetting("rail_origin_reuse") != 0;
  RAIL_ORIGIN_EXPOSURE_SHADOW = AIController.GetSetting("rail_origin_exposure_shadow") != 0;
  RAIL_ORIGIN_EXPOSURE_DETAIL_SHADOW = RAIL_ORIGIN_EXPOSURE_SHADOW
      && AIController.GetSetting("rail_origin_exposure_detail_shadow") != 0;
  RAIL_TARGET_CARGO_PREFILTER = AIController.GetSetting("rail_target_cargo_prefilter") != 0;
  RAIL_ORIGIN_REUSE_FALLBACK = AIController.GetSetting("rail_origin_reuse_fallback") != 0;
  RAIL_ORIGIN_REUSE_PAX = AIController.GetSetting("rail_origin_reuse_pax") != 0;
  RAIL_ORIGIN_REUSE_FREIGHT = AIController.GetSetting("rail_origin_reuse_freight") != 0;
  RAIL_ORIGIN_REUSE_MULTILINE_MATCH = RAIL_ORIGIN_REUSE
      && AIController.GetSetting("rail_origin_reuse_multiline_match") != 0;
  RAIL_ORIGIN_REUSE_CROSS_CARGO = RAIL_ORIGIN_REUSE
      && AIController.GetSetting("rail_origin_reuse_cross_cargo") != 0;
  RAIL_ORIGIN_REUSE_AIR_PRIORITY_SHADOW = RAIL_ORIGIN_REUSE
      && AIController.GetSetting("rail_origin_reuse_air_priority_shadow") != 0;
  RAIL_ORIGIN_REUSE_AIR_PRIORITY = RAIL_ORIGIN_REUSE
      && AIController.GetSetting("rail_origin_reuse_air_priority") != 0;
  RAIL_ORIGIN_REUSE_SEARCH_CAP = RAIL_ORIGIN_REUSE
      ? AIController.GetSetting("rail_origin_reuse_search_cap_k") * 1000 : 0;
  RAIL_ORIGIN_REUSE_SEARCH_SUPERSEDE = RAIL_ORIGIN_REUSE
      && AIController.GetSetting("rail_origin_reuse_search_supersede") != 0;
  RAIL_TERRAIN_PROBE = AIController.GetSetting("probe_rail_terrain") != 0;

  local acd = AIController.GetSetting("abandon_cooldown_days");
  if (acd >= 0) ABANDON_COOLDOWN_DAYS = acd;

  local rtf = AIController.GetSetting("rail_terrain_factor");
  if (rtf > 0) RAIL_TERRAIN_FACTOR = rtf;

  local ptk = AIController.GetSetting("project_top_k");
  if (ptk > 0) PROJECT_TOP_K = ptk;
  PROJECT_TOP_K_DYNAMIC = AIController.GetSetting("project_top_k_dynamic") != 0;

  ROAD_PAX_BUILD_ENABLED = AIController.GetSetting("road_pax_build") != 0;
  ROAD_LOADING_FIX = AIController.GetSetting("road_loading_fix") != 0;

  local roadPaxCatchment = AIController.GetSetting("road_pax_catchment_pct");
  ROAD_PAX_CATCHMENT_SHARE_PCT = (roadPaxCatchment == 0) ? 22 : roadPaxCatchment;

  local roadStopHouses = AIController.GetSetting("road_stop_catchment_houses");
  if (roadStopHouses > 0) ROAD_STOP_CATCHMENT_HOUSES = roadStopHouses;

  local roadPaxDwell = AIController.GetSetting("road_pax_dwell_days");
  if (roadPaxDwell >= 0) ROAD_PAX_STOP_DWELL_DAYS = roadPaxDwell;

  AIR_EARLY_SLOT = AIController.GetSetting("air_early_slot") != 0;
  local aest = AIController.GetSetting("air_early_slot_target_towns");
  if (aest >= 1) AIR_EARLY_SLOT_TARGET_TOWNS = aest;

  local aesmp = AIController.GetSetting("air_early_slot_min_pop");
  if (aesmp >= 0) AIR_EARLY_SLOT_MIN_POP = aesmp;

  local aesb = AIController.GetSetting("air_early_slot_bonus_pct");
  if (aesb >= 0) AIR_EARLY_SLOT_BONUS_PCT = aesb;

  local afcd = AIController.GetSetting("air_fleet_cadence_days");
  if (afcd >= 0) AIR_FLEET_CADENCE_DAYS = afcd;
  AIR_FLEET_COOLDOWN_PREFILTER = AIController.GetSetting("air_fleet_cooldown_prefilter") != 0;
  AIR_EFFICIENCY_BATCH = AIController.GetSetting("air_efficiency_batch") != 0;
  AIR_EFFICIENCY_PREFLIGHT = AIR_EFFICIENCY_BATCH || AIController.GetSetting("air_efficiency_preflight") != 0;
  AIR_EFFICIENCY_DEDUPE = AIR_EFFICIENCY_BATCH || AIController.GetSetting("air_efficiency_dedupe") != 0;
  AIR_EFFICIENCY_RESELECT = AIR_EFFICIENCY_BATCH || AIController.GetSetting("air_efficiency_reselect") != 0;

  local ajsl = AIController.GetSetting("air_joined_stop_limit");
  if (ajsl >= 0) AIR_JOINED_STOP_LIMIT = ajsl;

  local airPaxCalibration = AIController.GetSetting("air_pax_revenue_calibration_pct");
  if (airPaxCalibration > 0) AIR_PAX_REVENUE_CALIBRATION_PCT = airPaxCalibration;

  TOWN_GROWTH_ENABLED = AIController.GetSetting("town_growth") != 0;
  TOWN_GROWTH_SKIP_NOOP = AIController.GetSetting("town_growth_skip_noop") != 0;
  TOWN_GROWTH_PLAN_MEMO = AIController.GetSetting("town_growth_plan_memo") != 0;
  TOWN_GROWTH_ROI_GATE = AIController.GetSetting("town_growth_roi_gate") != 0;

  UNPROFITABLE_STREAK_THRESHOLD = AIController.GetSetting("unprofitable_streak_threshold");

  /* --- 4. Sondes de diagnostic unifiees (9 groupes) --- */

  // 1. probe_cost : rail_cost_probe, air_cost_probe, road_cost_probe
  local probeCost = AIController.GetSetting("probe_cost") != 0;
  RAIL_COST_PROBE = probeCost;
  AIR_COST_PROBE = probeCost;
  ROAD_COST_PROBE = probeCost;

  // 2. probe_scheduler : C41_SLACK, BUSY, STALENESS, OPPORTUNITY, ADMISSION, C39_CLOCK, C41_SLICE
  local probeScheduler = AIController.GetSetting("probe_scheduler") != 0;
  CATALOG_COST_PROBE = AIController.GetSetting("catalog_cost_probe") != 0;
  PROBE_LOOP_OPS = AIController.GetSetting("probe_loop_ops") != 0;
  PROBE_SPAN_TRACE = AIController.GetSetting("probe_span_trace") != 0;
  PROBE_C121_ENGINE_TABLE = AIController.GetSetting("probe_c121_engine_table") != 0;
  PROBE_AIR_ENGINE_DEPTH = AIController.GetSetting("probe_air_engine_depth") != 0;
  PROBE_AIR_FINANCE_MARGIN = AIController.GetSetting("probe_air_finance_margin") != 0;
  PROBE_EVENT_BACKLOG = AIController.GetSetting("probe_event_backlog") != 0;
  if (PROBE_EVENT_BACKLOG) {
    EVENT_BACKLOG_CALLS = 0;
    EVENT_BACKLOG_EVENTS = 0;
    EVENT_BACKLOG_MAX_BURST = 0;
    EVENT_BACKLOG_OPS_TOTAL = 0;
    EVENT_BACKLOG_OPS_MAX = 0;
    EVENT_BACKLOG_MONTH = -1;
  }
  EXP_OPCODE_EXACT = AIController.GetSetting("exp_opcode_exact") != 0;
  EXP_OPCODE_EXACT_CHECK = AIController.GetSetting("exp_opcode_exact_check") != 0;
  EXP_OPCODE_EXACT_ON = EXP_OPCODE_EXACT || EXP_OPCODE_EXACT_CHECK;
  if (EXP_OPCODE_EXACT_ON) {
    OPCODE_EXACT_STATS = null;
    OPCODE_EXACT_BREAK = null;
    OPCODE_EXACT_MISMATCHES = null;
    OPCODE_EXACT_CAL_YEAR = -1;
    OPCODE_EXACT_LATE_DATE = -1;
    OPCODE_EXACT_SITE_NAME = null;
    OPCODE_EXACT_PLAN_ONCE = null;
  }
  FLEET_AMORT_SHADOW_PROBE = AIController.GetSetting("fleet_amort_shadow_probe");
  R19_FAULT_INJECT = AIController.GetSetting("r19_fault_inject");
  C41_SLACK_LEDGER = probeScheduler;
  C41_MONTHLY_BUSY_LEDGER = probeScheduler;
  C41_STALENESS_LEDGER = probeScheduler;
  C41_OPPORTUNITY_LEDGER = probeScheduler;
  C41_ADMISSION_LEDGER = probeScheduler;
  C39_PASS_CLOCK_LEDGER = probeScheduler;
  C41_RAIL_SLICE_LEDGER = probeScheduler;
  V95_SCHED_IDLE_LEDGER = probeScheduler;

  // 3. probe_candidates_road : profiles pax, freight, town sinks, feeder
  local probeCandRoad = AIController.GetSetting("probe_candidates_road") != 0;
  C41_ROAD_CANDIDATE_PROFILE = probeCandRoad;
  C41_ROAD_FREIGHT_PROFILE = probeCandRoad;
  C41_ROAD_FREIGHT_TOWN_PROFILE = probeCandRoad;

  // 4. probe_candidates_rail : profiles pax, freight, speeds, cruise, economics
  local probeCandRail = AIController.GetSetting("probe_candidates_rail") != 0;
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
  local probeCat = AIController.GetSetting("probe_catalogue") != 0;
  C39_INVALIDATION_PROBE = probeCat;
  C39_DECISION_DELTA_PROBE = probeCat;
  C39_AIR_REASON_PROBE = probeCat;
  C41_REVISION_PROBE = probeCat;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  if (C39_INVALIDATION_PROBE) OpexC76Reset();

  // 6. probe_rail_search : domination, fallthrough, projects cadence
  local probeRailSearch = AIController.GetSetting("probe_rail_search") != 0;
  C41_RAIL_DOMINATION_PROBE = probeRailSearch;
  C41_PROJECTS_FALLTHROUGH_PROBE = probeRailSearch;
  C39_PROJECTS_CADENCE_PROBE = probeRailSearch;

  // 7. probe_vehicle_lost : diagnostic vehicules perdus rail/global
  local probeLost = AIController.GetSetting("probe_vehicle_lost") != 0;
  C41_RAIL_LOST_TOPOLOGY_PROBE = probeLost;
  C41_RAIL_LOST_PHYSICAL_PROBE = probeLost;
  C41_RAIL_LOST_CONNECTIVITY_PROBE = probeLost;
  C41_RAIL_LOST_PROBE = probeLost;
  C41_VEHICLE_LOST_PROBE = probeLost;

  // 8. probe_portfolio : scarcity, chronology, invest C63, funnel, tension, reserves, origin relax, town rating
  local probePort = AIController.GetSetting("probe_portfolio") != 0;
  C49_SCARCITY_LEDGER = probePort;
  C50_CHRONOLOGY_PROBE = probePort;
  if (C50_CHRONOLOGY_PROBE) {
    OpexC50ResetNonExpansionLedger();
  }
  C63_INVEST_PROBE = probePort;
  if (C63_INVEST_PROBE) OpexC63ResetLedger();
  C70_MODE_CALIBRATION = AIController.GetSetting("c70_mode_calibration") != 0;
  C82_ENGINE_CALIBRATION = AIController.GetSetting("c82_engine_calibration") != 0;
  C70_PROFIT_CALIBRATED = C70_MODE_CALIBRATION || C82_ENGINE_CALIBRATION;
  ::OpexCalibratedProfit <- C82_ENGINE_CALIBRATION ? OpexC82Profit : OpexC70Profit;
  C69_BOTTLENECK_PROBE = probePort;
  C69_DECISION_BOTTLENECK = AIController.GetSetting("c69_decision_bottleneck") != 0;
  C69_FLEET_EXEMPT = AIController.GetSetting("c69_fleet_exempt") != 0;
  C69_FLEET_DEMAND_BATCH = AIController.GetSetting("c69_fleet_demand_batch") != 0;
  C72_PLANE_CHOICE = AIController.GetSetting("c72_plane_choice");
  C84_AIR_TARGET_FLEET = AIController.GetSetting("c84_air_target_fleet") != 0;
  C85_AIR_EQUIPMENT_FRONTIER = AIController.GetSetting("c85_air_equipment_frontier") != 0;
  C83_FIXES = AIController.GetSetting("c83_fixes") != 0;
  C83_LOCAL_REPAIR = AIController.GetSetting("c83_local_repair") != 0;
  EXP_SCHEDULER_SKIP_NOT_DUE = AIController.GetSetting("exp_scheduler_skip_not_due") != 0;
  EXP_AIR_HUB_PAIR_PREFILTER = AIController.GetSetting("exp_air_hub_pair_prefilter") != 0;
  C83_PREEMPT_OPEN = AIController.GetSetting("c83_preempt_open") != 0;
  AIR_BATCH_TOWN_RESERVE = AIController.GetSetting("air_batch_town_reserve") != 0;
  V92_AIR_SERVICE_CHOICE = AIController.GetSetting("v92_air_service_choice") != 0;
  V93_AIRPORT_NO_POP_FLOOR = AIController.GetSetting("v93_airport_no_pop_floor") != 0;
  V93_AIR_DEMAND_PRODUCTION = AIController.GetSetting("v93_air_demand_production") != 0;
  V95_AIR_POST73_PROBE = AIController.GetSetting("v95_air_post73_probe") != 0;
  V95_AIR_POST73_YEAR = -1;
  C96_AIR_SITE_CATCHMENT = AIController.GetSetting("c96_air_site_catchment") != 0;
  AIR_SITE_MIN_CATCHMENT = AIController.GetSetting("air_site_min_catchment") != 0;
  AIR_SITE_COST_QUOTE = AIController.GetSetting("air_site_cost_quote") != 0;
  local ascmp = AIController.GetSetting("air_site_cost_margin_pct");
  if (ascmp >= 0) AIR_SITE_COST_MARGIN_PCT = ascmp;
  C97_AIR_C69_ENGINE_PROBE = AIController.GetSetting("c97_air_c69_engine_probe") != 0;
  C98_AIR_REALIZED_PROBE = AIController.GetSetting("c98_air_realized_probe") != 0;
  C99_AIR_SPEED_API_FIX = AIController.GetSetting("c99_air_speed_api_fix") != 0;
  C100_AIR_TRIP_PHYSICAL = AIController.GetSetting("c100_air_trip_physical") != 0;
  C101_AIR_PHYSICAL_ENGINE_CHOICE = AIController.GetSetting("c101_air_physical_engine_choice") != 0;
  C103_AIR_C100_RANK_REPLAY = AIController.GetSetting("c103_air_c100_rank_replay") != 0;
  C104_AIR_C100_COMPARE_PROBE = AIController.GetSetting("c104_air_c100_compare_probe") != 0;
  C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS = AIController.GetSetting("c105_air_replay_choice_physical_economics") != 0;
  C106_AIR_MARGINAL_PHYSICAL_ENGINE_CHOICE = AIController.GetSetting("c106_air_marginal_physical_engine_choice") != 0;
  C108_AIR_ONESTEP_PHYSICAL_ECONOMICS = AIController.GetSetting("c108_air_onestep_physical_economics") != 0;
  C109_AIR_SPEED_ELASTICITY_PHYSICAL = AIController.GetSetting("c109_air_speed_elasticity_physical") != 0;
  C110_AIR_ENGINE_CALIBRATION_CHOICE_ONLY = AIController.GetSetting("c110_air_engine_calibration_choice_only") != 0;
  C111_AIR_C100_DECISION_SHADOW = AIController.GetSetting("c111_air_c100_decision_shadow") != 0;
  C112_AIR_SPEED_ELASTICITY_E75_PHYSICAL = AIController.GetSetting("c112_air_speed_elasticity_e75_physical") != 0;
  C113_AIR_C100_FULL_DECISION_SHADOW = AIController.GetSetting("c113_air_c100_full_decision_shadow") != 0;
  C114_AIR_C100_FULL_REPLAY = AIController.GetSetting("c114_air_c100_full_replay") != 0;
  C115_AIR_C100_CAPITAL_REPLAY = AIController.GetSetting("c115_air_c100_capital_replay") != 0;
  C116_AIR_MARGINAL_CAPITAL = AIController.GetSetting("c116_air_marginal_capital") != 0;
  C116_AIR_PROJECT_PROBE = AIController.GetSetting("c116_air_project_probe") != 0;
  C117_AIR_THROUGHPUT_PROBE = AIController.GetSetting("c117_air_throughput_probe") != 0;
  C118_AIR_TERRITORIAL_EXPANSION = AIController.GetSetting("c118_air_territorial_expansion") != 0;
  C118_AIR_COVERAGE_PROBE = AIController.GetSetting("c118_air_coverage_probe") != 0;
  C119_AIR_INCOME_MODEL = AIController.GetSetting("c119_air_income_model") != 0;
  C118_AIR_PROJECT_SNAPSHOT = null;
  C118_AIR_DECISION_SEQ = 0;
  C120_AIR_TERRITORIAL_RANKING = AIController.GetSetting("c120_air_territorial_ranking") != 0;
  C121_AIR_ECONOMICS_SHADOW = AIController.GetSetting("c121_air_economics_shadow") != 0;
  C121_AIR_ECONOMICS = AIController.GetSetting("c121_air_economics") != 0;
  C121_AIR_WINNER_FUSION = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_air_winner_fusion") != 0;
  C121_AIR_GAME_ENGINE = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_air_game_engine") != 0;
  C121_CATALOG_INCREMENTAL = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_catalog_incremental") != 0;
  C121_CATALOG_AIR_FIRST_YEAR = C121_CATALOG_INCREMENTAL
      && AIController.GetSetting("c121_catalog_air_first_year") != 0;
  /* Amorcage plat : sans etapes, chaque regeneration apres chantier prend le
   * chemin incremental C121 au lieu d'un OpexBuildProjects complet synchrone. */
  C121_FLAT_BOOTSTRAP = C121_CATALOG_INCREMENTAL
      && AIController.GetSetting("c121_flat_bootstrap") != 0;
  if (C121_FLAT_BOOTSTRAP) STAGED_BOOTSTRAP = false;
  C121_AIR_FIRST_YEAR_RAIL_PREP = C121_CATALOG_AIR_FIRST_YEAR
      && AIController.GetSetting("c121_air_first_year_rail_prep") != 0;
  C121_AIR_ONE_OR_TWO_PLANES = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_air_one_or_two_planes") != 0;
  C121_CATALOG_FIRST_YEAR_ACTIVE = false;
  C121_FLEET_STOCK_GROWTH = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_fleet_stock_growth") != 0;
  C121_AIR_OBSERVATION_GROWTH = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_air_observation_growth") != 0;
  C121_AIR_FIRST_OBSERVATION_GROWTH = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_air_first_observation_growth") != 0;
  C121_AIR_FIRST_GROWTH_MIN_DAYS = C121_AIR_FIRST_OBSERVATION_GROWTH
      ? AIController.GetSetting("c121_air_first_growth_min_days") : 0;
  C121_AIR_FIRST_GROWTH_PHASE_YEARS = C121_AIR_FIRST_OBSERVATION_GROWTH
      ? AIController.GetSetting("c121_air_first_growth_phase_years") : 0;
  C121_AIR_FIRST_GROWTH_LATE_DAYS = C121_AIR_FIRST_OBSERVATION_GROWTH
      ? AIController.GetSetting("c121_air_first_growth_late_days") : 0;
  C121_AIR_FIRST_GROWTH_MIN_WAIT_PCT = C121_AIR_FIRST_OBSERVATION_GROWTH
      ? AIController.GetSetting("c121_air_first_growth_min_wait_pct") : 0;
  C121_AIR_FIRST_LIVE_SHADOW = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_air_first_live_shadow") != 0;
  C121_AIR_FIRST_LIVE_GROWTH = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_air_first_live_growth") != 0;
  C121_AIR_FIRST_LIVE_GROWTH_PHASE_YEARS = C121_AIR_FIRST_LIVE_GROWTH
      ? AIController.GetSetting("c121_air_first_live_growth_phase_years") : 0;
  C121_AIR_FIRST_LIVE_AIR_PRIORITY = C121_AIR_FIRST_LIVE_GROWTH
      && AIController.GetSetting("c121_air_first_live_air_priority") != 0;
  C121_KPASS_SHADOW = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_kpass_shadow") != 0;
  C121_KPASS_AIR_CONTINUE = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_kpass_air_continue") != 0;
  C121_KDEC_COLD_SHADOW = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_kdec_cold_shadow") != 0;
  C121_KDEC_COLD_EXEMPT = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_kdec_cold_exempt") != 0;
  C121_AIR_FIRST_LIVE_STATE = {};
  C121_AIR_FIRST_LIVE_OPS = 0;
  C121_AIR_FIRST_LIVE_SAMPLES = 0;
  C121_AIR_FIRST_LIVE_PRIORITY_STATE = {};
  C121_TERRITORY_FIRST = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_territory_first") != 0;
  C121_AAA_LINE = C121_AIR_ECONOMICS
      && AIController.GetSetting("c121_aaa_line") != 0;
  if (C121_CATALOG_INCREMENTAL) {
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
  C121_AIR_ENGINE_REALIZATION = AIController.GetSetting("c121_air_engine_realization") != 0;
  C121_AIR_PROJECT_REALIZATION = AIController.GetSetting("c121_air_project_realization") != 0;
  C121_AIR_PROJECT_REALIZATION_ADAPTIVE = AIController.GetSetting("c121_air_project_realization_adaptive") != 0;
  C121_AIR_PRESSURE_PROBE = AIController.GetSetting("c121_air_pressure_probe") != 0;
  C121_AIR_PRESSURE_SNAPSHOT = null;
  C121_AIR_PRESSURE_ACCUM = null;
  C121_AIR_PRESSURE_PREV = null;
  /* R7 : parametre protege, branche conservee. PORTFOLIO_FLOOR_PCT reste force a 0
   * plus bas : 50% / 75% de ce plancher valent toujours 0, sans neutraliser le
   * filtre des profits negatifs hors exemptions existantes. Les calculs executes
   * peuvent changer la cadence d'opcodes ; ne pas supprimer la branche. */
  C121_AIR_DEFENSIVE_FLOOR = AIController.GetSetting("c121_air_defensive_floor") != 0;
  C121_AIR_INITIAL_PROJECT_ECONOMICS = AIController.GetSetting("c121_air_initial_project_economics") != 0;
  C121_AIR_ENGINE_REPLAY_SHADOW = AIController.GetSetting("c121_air_engine_replay_shadow") != 0;
  C122_AIR_REGIME_PRIORITY = AIController.GetSetting("c122_air_regime_priority") != 0;
  C122_AIR_REGIME_SHADOW = AIController.GetSetting("c122_air_regime_shadow") != 0;
  C122_AIR_THREAT_RETRY = AIController.GetSetting("c122_air_threat_retry") != 0;
  C122_AIR_THREAT_PROBE = AIController.GetSetting("c122_air_threat_probe") != 0 || C122_AIR_THREAT_RETRY;
  C122_AIR_THREAT_WATCH.clear();
  C122_AIR_THREAT_SEQ = 0;
  C122_AIR_THREAT_RETRY_COUNT = 0;
  C121_AIR_ENGINE_CAPACITY_OBS.clear();
  C121_AIR_REALIZATION_FACTOR.newpair = 1.0;
  C121_AIR_REALIZATION_FACTOR.hubsite = 1.0;
  C121_AIR_REALIZATION_FACTOR.hubhub = 1.0;
  C120_AIR_SELECTION_SNAPSHOT = null;
  C120_AIR_FILTER_SNAPSHOT = null;
  C120_AIR_SELECT_SEQ = 0;
  C120_AIR_LAST_TRACE_KEY = "";
  if (C116_AIR_PROJECT_PROBE) {
    C116_AIR_PROJECT_PROBE_COUNT = 0;
    C116_AIR_PROJECT_PROBE_YEAR = -1;
    C116_AIR_PROJECT_PROBE_YEAR_COUNT = 0;
    C116_AIR_PROJECT_PROBE_SEEN = {};
  }
  if (C117_AIR_THROUGHPUT_PROBE) {
    C117_AIR_LAST_DATE = -1;
    C117_AIR_LINE_STATE = {};
    C117_AIR_VEHICLE_STATE = {};
  }
  /* C113 etend C111 : reutiliser ses branches shadow/memo sans dupliquer le hot path. */
  if (C113_AIR_C100_FULL_DECISION_SHADOW) C111_AIR_C100_DECISION_SHADOW = true;
  V88_GOODS_CHAIN = AIController.GetSetting("v88_goods_chain") != 0;
  V88_CHAIN_FORCE = V88_GOODS_CHAIN && (AIController.GetSetting("v88_chain_force") != 0);
  V88_STEP2_PLAN_IMMEDIATE = V88_GOODS_CHAIN && (AIController.GetSetting("v88_step2_plan_immediate") != 0);
  V88_ALL_INPUTS = V88_GOODS_CHAIN && (AIController.GetSetting("v88_all_inputs") != 0);
  V88_CHAIN_STEP1_FINANCE = V88_GOODS_CHAIN && (AIController.GetSetting("v88_chain_step1_finance") != 0);
  V88_STEP2_RAIL_PRIO = V88_GOODS_CHAIN && (AIController.GetSetting("v88_step2_rail_prio") != 0);
  V88_STEP2_CASH_RESERVE = V88_GOODS_CHAIN && (AIController.GetSetting("v88_step2_cash_reserve") != 0);
  AIR_FULL_LOAD = AIController.GetSetting("air_full_load");
  /* c121_aaa_line : chargement complet aux deux bouts pour toutes les lignes du bras C121. */
  if (C121_AAA_LINE) AIR_FULL_LOAD = 1;
  C69_TRACK_BUILDS = C69_BOTTLENECK_PROBE || C69_DECISION_BOTTLENECK || (C72_PLANE_CHOICE == 2)
      || C97_AIR_C69_ENGINE_PROBE || C115_AIR_C100_CAPITAL_REPLAY || C116_AIR_MARGINAL_CAPITAL;
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
  local probeEvents = AIController.GetSetting("probe_events") != 0;
  local b9CatchmentProbe = AIController.GetSetting("b9_air_catchment_probe") != 0;
  B9_AIR_DEMAND_SHADOW = AIController.GetSetting("b9_air_demand_shadow") != 0;
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
  AIR_CATCHMENT_PROBE = probeEvents || b9CatchmentProbe;
  EQUIPMENT_ROI_PROBE = probeEvents;
  C54_VEHICLE_ORDERS_PROBE = probeEvents;
  C78_SLOT_INTERCEPT_PROBE = probePort;

  /* --- 5. Pistes formellement abandonnees / constantes neutres verrouillees --- */
  /* R7 : zero global conserve ; le reglage defensif C121 ne retablit pas de plancher positif. */
  PORTFOLIO_FLOOR_PCT = 0;
  ROAD_TIME_SCALED_CAP = AIController.GetSetting("road_time_scaled_cap") != 0;
  C76_REGEN_TARGETED = AIController.GetSetting("c76_regen_targeted") != 0;
  C67_TERRAIN_MAP = AIController.GetSetting("c67_terrain_map") != 0;
  C67_WATER_EXPOSURE = AIController.GetSetting("c67_water_exposure_probe") != 0;
  C67_SLACK_HOOK = C67_TERRAIN_MAP || C67_WATER_EXPOSURE;
  /* C77 corrige est permanent et repose sur le socle du double registre. */
  C80_WORKER_RAIL = AIController.GetSetting("c80_worker_rail") != 0;
  C80_RAIL_STOCK_GATE = AIController.GetSetting("c80_rail_stock_gate") != 0;
  C80_RAIL_STOCK_WORKER = C80_RAIL_STOCK_GATE && (AIController.GetSetting("c80_rail_stock_worker") != 0);
  C80_WORKER_TOWN = AIController.GetSetting("c80_worker_town") != 0;
  C76_LEAN_INVALIDATION = C76_REGEN_TARGETED && (AIController.GetSetting("c76_lean_invalidation") != 0);
  C76_FREIGHT_ROTATION = C76_REGEN_TARGETED && (AIController.GetSetting("c76_freight_rotation") != 0);
  C80_MODE_REGEN = C76_REGEN_TARGETED && (AIController.GetSetting("c80_mode_regen") != 0);
  C80_AIR_CHOICE_MEMO = AIController.GetSetting("c80_air_choice_memo") != 0;
  C80_AIR_HUB_INDEX = AIController.GetSetting("c80_air_hub_index") != 0;
  C80_MARGINAL_FLOOR = AIController.GetSetting("c80_marginal_floor") != 0;
  C80_AIR_EVAL_FAST = AIController.GetSetting("c80_air_eval_fast") != 0;
  C55_FREIGHT_ORIGIN_RELAX = false;
  C41_RAIL_LOST_SIGNAL_REPAIR = false;
  C41_RAIL_LOST_JUNCTION_REPAIR = false;
  RAIL_EXPAND = AIController.GetSetting("rail_expand") != 0;
  AIR0310_V96_SHORTCUT_LEAN = AIController.GetSetting("air0310_v96_shortcut_lean") != 0;
  AIR0310_ONE_TWO_FUSED = AIController.GetSetting("air0310_one_two_fused") != 0;
  AIR0310_INCREMENTAL_PUBLISH = C121_CATALOG_INCREMENTAL
      && AIController.GetSetting("air0310_incremental_publish") != 0;
  V127_IDLE_CASH_ROAD_REGEN = C121_CATALOG_INCREMENTAL
      && AIController.GetSetting("v127_idle_cash_road_regen") != 0;
  V127_LAST_MONTH = -1;
  V127_LAST_ROAD_REGEN_DATE = -1;
  AIR0310_HUB_SNAPSHOT = C121_CATALOG_INCREMENTAL
      && AIController.GetSetting("air0310_hub_snapshot") != 0;
  AIR0310_SITE_VALIDITY_CACHE = C121_CATALOG_INCREMENTAL
      && AIController.GetSetting("air0310_site_validity_cache") != 0;
  AIR0310_SITE_VALIDITY_STATE = null;
  RAIL_DEPOT_COST = AIController.GetSetting("rail_depot_cost") != 0;
  AIR_HUBHUB_MARGINAL = AIController.GetSetting("air_hubhub_marginal") != 0;
  local hubMaxRoutes = AIController.GetSetting("air_hub_max_routes");
  AIR_HUB_MAX_ROUTES = hubMaxRoutes >= 0 ? hubMaxRoutes : 0;
  V89_RAIL_SEARCH_THROUGHPUT = AIController.GetSetting("v89_rail_search_throughput") != 0;
  if (C80_RAIL_STOCK_WORKER) V89_RAIL_SEARCH_THROUGHPUT = false;
  V90_FAST_PATHFINDER = AIController.GetSetting("v90_fast_pathfinder") != 0;
  V90_PATHFINDER_CHECK = AIController.GetSetting("v90_pathfinder_check") != 0;
  local astarWeight = AIController.GetSetting("v91_astar_weight_pct");
  V91_ASTAR_WEIGHT_PCT = (astarWeight != null && astarWeight >= 100 && astarWeight <= 300) ? astarWeight : 100;
  local railBias = AIController.GetSetting("rail_finance_bias_pct");
  RAIL_FINANCE_BIAS_PCT = (railBias != null && railBias >= 90 && railBias <= 200) ? railBias : 100;
  V94_AIR_SITE_LIST = AIController.GetSetting("v94_air_site_list") != 0;
  V94_AIR_SITE_CHECK = AIController.GetSetting("v94_air_site_check") != 0;
  PAX_NEAR = false;
  OPEX_AIR_CAP_PAD = false;
  OPEX_AIR_PLAN_PAD = false;
  OPEX_AIR_SITE_PAD = false;
  OPEX_AIR_TOWN_PAD = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  AIR_MAX_DISTANCE = 0;
  C53_ORDER_NOLOAD = false;
  TRANSIT_COST_PERMILLE = 0;
  INFRA_AMORT_PCT = 0;
  PORTFOLIO_MAX_BATCH = 1;
  AIR_FLEET_BUFFER = 0;
}
