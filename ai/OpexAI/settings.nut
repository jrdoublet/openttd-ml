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

  local ajsl = AIController.GetSetting("air_joined_stop_limit");
  if (ajsl >= 0) AIR_JOINED_STOP_LIMIT = ajsl;

  local airPaxCalibration = AIController.GetSetting("air_pax_revenue_calibration_pct");
  if (airPaxCalibration > 0) AIR_PAX_REVENUE_CALIBRATION_PCT = airPaxCalibration;

  TOWN_GROWTH_ENABLED = AIController.GetSetting("town_growth") != 0;
  TOWN_GROWTH_SKIP_NOOP = AIController.GetSetting("town_growth_skip_noop") != 0;
  TOWN_GROWTH_PLAN_MEMO = AIController.GetSetting("town_growth_plan_memo") != 0;

  UNPROFITABLE_STREAK_THRESHOLD = AIController.GetSetting("unprofitable_streak_threshold");

  /* --- 4. Sondes de diagnostic unifiees (9 groupes) --- */

  // 1. probe_cost : rail_cost_probe, air_cost_probe, road_cost_probe
  local probeCost = AIController.GetSetting("probe_cost") != 0;
  RAIL_COST_PROBE = probeCost;
  AIR_COST_PROBE = probeCost;
  ROAD_COST_PROBE = probeCost;

  // 2. probe_scheduler : C41_SLACK, BUSY, STALENESS, OPPORTUNITY, ADMISSION, C39_CLOCK, C41_SLICE
  local probeScheduler = AIController.GetSetting("probe_scheduler") != 0;
  C41_SLACK_LEDGER = probeScheduler;
  C41_MONTHLY_BUSY_LEDGER = probeScheduler;
  C41_STALENESS_LEDGER = probeScheduler;
  C41_OPPORTUNITY_LEDGER = probeScheduler;
  C41_ADMISSION_LEDGER = probeScheduler;
  C39_PASS_CLOCK_LEDGER = probeScheduler;
  C41_RAIL_SLICE_LEDGER = probeScheduler;

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
  PORTFOLIO_FLOOR_PCT = 0;
  ROAD_TIME_SCALED_CAP = AIController.GetSetting("road_time_scaled_cap") != 0;
  C76_REGEN_TARGETED = AIController.GetSetting("c76_regen_targeted") != 0;
  C77_OPPORTUNISTIC_CANDIDATES = AIController.GetSetting("c77_opportunistic_candidates") != 0;
  C77_TARGETED_BUILD = C77_OPPORTUNISTIC_CANDIDATES && (AIController.GetSetting("c77_targeted_build") != 0);
  C77_FIXES = C77_OPPORTUNISTIC_CANDIDATES && (AIController.GetSetting("c77_fixes") != 0);
  /* C77 alimente la file reactive : l'armer implique le socle C80. C76 fonctionne sans. */
  C80_DOUBLE_REGISTER = AIController.GetSetting("c80_double_register") != 0 || C77_OPPORTUNISTIC_CANDIDATES;
  C80_WORKER_RAIL = C80_DOUBLE_REGISTER && (AIController.GetSetting("c80_worker_rail") != 0);
  C80_WORKER_TOWN = C80_DOUBLE_REGISTER && (AIController.GetSetting("c80_worker_town") != 0);
  C76_LEAN_INVALIDATION = C76_REGEN_TARGETED && (AIController.GetSetting("c76_lean_invalidation") != 0);
  C80_MODE_REGEN = C76_REGEN_TARGETED && (AIController.GetSetting("c80_mode_regen") != 0);
  C80_AIR_CHOICE_MEMO = AIController.GetSetting("c80_air_choice_memo") != 0;
  C80_AIR_HUB_INDEX = AIController.GetSetting("c80_air_hub_index") != 0;
  C80_MARGINAL_FLOOR = AIController.GetSetting("c80_marginal_floor") != 0;
  C80_AIR_EVAL_FAST = AIController.GetSetting("c80_air_eval_fast") != 0;
  C80_FLEET_INJECT = AIController.GetSetting("c80_fleet_inject") != 0;
  C80_AIR_TARGETED_UPDATE = AIController.GetSetting("c80_air_targeted_update") != 0;
  C55_FREIGHT_ORIGIN_RELAX = false;
  C41_RAIL_LOST_SIGNAL_REPAIR = false;
  C41_RAIL_LOST_JUNCTION_REPAIR = false;
  JOIN_MAX_DISTANCE = 0;
  BASIN_SHARE = false;
  RAIL_EXPAND = AIController.GetSetting("rail_expand") != 0;
  PAX_NEAR = false;
  OPEX_AIR_CAP_PAD = false;
  OPEX_AIR_PLAN_PAD = false;
  OPEX_AIR_SITE_PAD = false;
  OPEX_AIR_TOWN_PAD = false;
  C39_ENGINE_REFRESH = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  AIR_MAX_DISTANCE = 0;
  C53_ORDER_NOLOAD = false;
  TRANSIT_COST_PERMILLE = 0;
  INFRA_AMORT_PCT = 0;
  PORTFOLIO_MAX_BATCH = 1;
  AIR_FLEET_BUFFER = 0;
}
