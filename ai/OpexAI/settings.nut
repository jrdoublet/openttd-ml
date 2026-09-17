/* C65 passe 2 : lecture unique des reglages, deplacee depuis Start().
 * Fonction libre : n'affecte que des globales. Les mutations d'instance
 * restent dans Start(), juste apres l'appel. */
function OpexLoadSettings()
{
  /* Lu une seule fois : le reglage ne change pas en cours de partie, et OpexSign est appele des
   * dizaines de fois par an. Un GetSetting par appel serait du gaspillage pur. */
  DEBUG_SIGNS = AIController.GetSetting("debug_signs") != 0;
  SAVE_FULL_STATE = AIController.GetSetting("save_full_state") != 0;
  /* Exprime en milliers dans le reglage : AddSetting ne porte que des entiers, et un pas de
   * 50 000 sur une plage de 0 a 2 000 000 serait illisible en unites brutes. */
  LOAN_REPAY_FLOOR = AIController.GetSetting("loan_repay_floor_k") * 1000;
  /* Memes reglages lus UNE fois : OpexIterationBudget et _tryBuild tournent pour chaque candidat,
   * donc les GetSetting dans ces boucles seraient du debit d'opcodes perdu. */
  HARD_ITERATION_CAP = AIController.GetSetting("pathfinder_hard_cap_k") * 1000;
  RAIL_SEARCH_RESUMABLE = AIController.GetSetting("rail_search_resumable") != 0;
  RAIL_MICRO_DEADLINE = AIController.GetSetting("rail_micro_deadline") != 0;
  RAIL_SEGMENTED_SEARCH = AIController.GetSetting("rail_segmented_search") != 0;
  DECISION_LOG = AIController.GetSetting("decision_log") != 0;
  PORTFOLIO_LOG = DECISION_LOG;
  ABANDON_MEMORY = AIController.GetSetting("abandon_memory") != 0;
  local acd = AIController.GetSetting("abandon_cooldown_days");
  if (acd >= 0) ABANDON_COOLDOWN_DAYS = acd;
  ABANDON_GEN_FILTER = AIController.GetSetting("abandon_gen_filter") != 0;
  STATION_JOIN = AIController.GetSetting("station_join") != 0;
  JOIN_MAX_DISTANCE = AIController.GetSetting("join_max_distance");
  JOIN_PLACE = AIController.GetSetting("join_place") != 0;
  ORIGIN_SITABLE = AIController.GetSetting("origin_sitable") != 0;
  BASIN_SHARE = AIController.GetSetting("basin_share") != 0;
  REBORROW = AIController.GetSetting("reborrow") != 0;
  /* Lu ici comme les autres reglages de decision : catalog.refresh le consulte des le premier
   * cycle annuel, qui a lieu apres Start(). */
  ROAD_BUILD_ENABLED = AIController.GetSetting("road_mode") != 0;
  ROAD_PAX_BUILD_ENABLED = AIController.GetSetting("road_pax_build") != 0;
  ROAD_PAX_EXTENSIONS = AIController.GetSetting("road_pax_extensions") != 0;
  TOWN_GROWTH_ENABLED = AIController.GetSetting("town_growth") != 0;
  TOWN_GROWTH_SKIP_NOOP = AIController.GetSetting("town_growth_skip_noop") != 0;
  local roadPaxCatchment = AIController.GetSetting("road_pax_catchment_pct");
  ROAD_PAX_CATCHMENT_SHARE_PCT = (roadPaxCatchment == 0) ? 22 : roadPaxCatchment;
  local roadStopHouses = AIController.GetSetting("road_stop_catchment_houses");
  if (roadStopHouses > 0) ROAD_STOP_CATCHMENT_HOUSES = roadStopHouses;
  local roadPaxDwell = AIController.GetSetting("road_pax_dwell_days");
  if (roadPaxDwell >= 0) ROAD_PAX_STOP_DWELL_DAYS = roadPaxDwell;
  local airPaxCalibration = AIController.GetSetting("air_pax_revenue_calibration_pct");
  if (airPaxCalibration > 0) AIR_PAX_REVENUE_CALIBRATION_PCT = airPaxCalibration;
  ROAD_REFLEET = AIController.GetSetting("road_refleet") != 0;
  ROAD_MULTISTOP = AIController.GetSetting("road_multistop") != 0;
  MARGINAL_FLEET = AIController.GetSetting("marginal_fleet") != 0;
  AIR_PORTFOLIO = AIController.GetSetting("air_portfolio") != 0;
  FLEET_PORTFOLIO = AIController.GetSetting("fleet_portfolio") != 0;
  TENSION_SCORING = AIController.GetSetting("tension_scoring") != 0;
  local dfp = AIController.GetSetting("decision_friction_permille");
  if (dfp >= 0) TENSION_DECISION_FRICTION = dfp.tofloat() / 1000.0;
  SHADOW_PRICING = AIController.GetSetting("shadow_pricing") != 0;
  FLAT_BONUS = AIController.GetSetting("flat_bonus") != 0;
  AIR_ROI_ORDER = AIController.GetSetting("air_roi_order") != 0;
  LOOP_BUDGET = AIController.GetSetting("loop_budget") != 0;
  PORTFOLIO_MAX_BATCH = AIController.GetSetting("portfolio_max_batch");
  PORTFOLIO_DYNAMIC_BATCH = AIController.GetSetting("portfolio_dynamic_batch") != 0;
  local dynamicRejectLimit = AIController.GetSetting("dynamic_batch_reject_limit");
  if (dynamicRejectLimit >= 0) DYNAMIC_BATCH_REJECT_LIMIT = dynamicRejectLimit;
  local dynamicOpsBudget = AIController.GetSetting("dynamic_batch_ops_budget_pct");
  if (dynamicOpsBudget >= 0) DYNAMIC_BATCH_OPS_BUDGET_PCT = dynamicOpsBudget;
  PORTFOLIO_FLOOR_PCT = AIController.GetSetting("portfolio_floor_pct");
  FLEET_FIX = AIController.GetSetting("fleet_fix") != 0;
  ECONOMY_FIX = AIController.GetSetting("economy_fix") != 0;
  GROWTH_YIELDS = AIController.GetSetting("growth_yields") != 0;
  AIR_MARGIN = AIController.GetSetting("air_margin") != 0;
  AIR_ABANDON = AIController.GetSetting("air_abandon") != 0;
  AIR_ABANDON_SITE = AIController.GetSetting("air_abandon_site") != 0;
  AIR_TOWN_LIMIT_MEMORY = AIController.GetSetting("air_town_limit_memory") != 0;
  STAGED_BOOTSTRAP = AIController.GetSetting("staged_bootstrap") != 0;
  PRICING_ROAD_RATING = AIController.GetSetting("pricing_road_rating") != 0;
  PRICING_RAIL_DEPOT = AIController.GetSetting("pricing_rail_depot") != 0;
  PRICING_ROAD_OPS = AIController.GetSetting("pricing_road_ops") != 0;
  AIR_PRESITE = AIController.GetSetting("air_presite") != 0;
  PORTFOLIO_FRESH_BUDGET = AIController.GetSetting("portfolio_fresh_budget") != 0;
  PORTFOLIO_CACHE = AIController.GetSetting("portfolio_cache") != 0;
  FLEET_BEFORE_NEW = AIController.GetSetting("fleet_before_new") != 0;
  local tc = AIController.GetSetting("transit_cost");
  if (tc >= 0) TRANSIT_COST_PERMILLE = tc;
  RAIL_DEVIS = AIController.GetSetting("rail_devis") != 0;
  RAIL_EXPAND = AIController.GetSetting("rail_expand") != 0;
  ASTAR_COST_V2 = AIController.GetSetting("astar_cost") != 0;
  PROBE_NEGATIVE = AIController.GetSetting("probe_negative") != 0;
  PAX_NEAR = AIController.GetSetting("pax_near") != 0;
  DYNAMIC_CASH_RESERVE = AIController.GetSetting("dynamic_cash_reserve") != 0;
  RESERVE_MAINT_CAP = AIController.GetSetting("reserve_maint_cap") != 0;
  AIR_MARGIN_V2 = AIController.GetSetting("air_margin_v2") != 0;
  CAPITAL_CALIBRATION = AIController.GetSetting("capital_calibration") != 0;
  RAIL_PREQUOTE = AIController.GetSetting("rail_prequote") != 0;
  RAIL_PREQUOTE_KEEP_PLAN = AIController.GetSetting("rail_prequote_keep_plan") != 0;
  RAIL_TERRAIN_PROBE = AIController.GetSetting("rail_terrain_probe") != 0;
  ABANDON_MEMORY_TRANSIENT_GUARD = AIController.GetSetting("abandon_memory_transient_guard") != 0;
  AIR_HUB_FIX = AIController.GetSetting("air_hub_fix") != 0;
  AIR_DEMAND_CAP = AIController.GetSetting("air_demand_cap") != 0;
  AIR_DEMAND_PLAN = AIController.GetSetting("air_demand_plan") != 0;
  DYNAMIC_PATHFINDER_CAP = AIController.GetSetting("dynamic_pathfinder_cap") != 0;
  PAX_FULL_LOAD = AIController.GetSetting("pax_full_load") != 0;
  AIR_FULL_LOAD = AIController.GetSetting("air_full_load") != 0;
  C53_ORDER_NONSTOP = AIController.GetSetting("c53_order_nonstop") != 0;
  C53_ORDER_NOLOAD = AIController.GetSetting("c53_order_noload") != 0;
  COMPLEX_CARGO = AIController.GetSetting("complex_cargo") != 0;
  AIR_HUB = AIController.GetSetting("air_hub") != 0;
  local airMaxDist = AIController.GetSetting("air_max_distance");
  if (airMaxDist >= 0) AIR_MAX_DISTANCE = airMaxDist;
  local afcd = AIController.GetSetting("air_fleet_cadence_days");
  if (afcd >= 0) AIR_FLEET_CADENCE_DAYS = afcd;
  local afb = AIController.GetSetting("air_fleet_buffer");
  if (afb >= -1) AIR_FLEET_BUFFER = afb;
  local rtf = AIController.GetSetting("rail_terrain_factor");
  if (rtf > 0) RAIL_TERRAIN_FACTOR = rtf;
  local ptk = AIController.GetSetting("project_top_k");
  if (ptk > 0) PROJECT_TOP_K = ptk;
  PROJECT_TOP_K_DYNAMIC = AIController.GetSetting("project_top_k_dynamic") != 0;
  RAIL_REFLEET = AIController.GetSetting("rail_refleet") != 0;
  EVENT_DEPOT_SELL = AIController.GetSetting("event_depot_sell") != 0;
  EVENT_INDUSTRY_CLOSE = AIController.GetSetting("event_industry_close") != 0;
  EVENT_SUBSIDY_PROBE = AIController.GetSetting("event_subsidy_probe") != 0;
  C42_SUBSIDIES = AIController.GetSetting("c42_subsidies") != 0;
  EVENT_VEHICLE_LOST = AIController.GetSetting("event_vehicle_lost") != 0;
  EVENT_VEHICLE_CRASHED = AIController.GetSetting("event_vehicle_crashed") != 0;
  EVENT_VEHICLE_UNPROFITABLE = AIController.GetSetting("event_vehicle_unprofitable") != 0;
  UNPROFITABLE_STREAK_THRESHOLD = AIController.GetSetting("unprofitable_streak_threshold");
  EVENT_CATALOG_INVALIDATE = AIController.GetSetting("event_catalog_invalidate") != 0;
  C39_ENGINE_REFRESH = AIController.GetSetting("c39_engine_refresh") != 0;
  C41_WATER_REFRESH = AIController.GetSetting("c41_water_refresh") != 0;
  C41_WATER_PRECHECK = AIController.GetSetting("c41_water_precheck") != 0;
  WATER_LAKES_CONNECTIVITY = AIController.GetSetting("water_lakes_connectivity") != 0;
  WATER_LAKES_OPS_BUDGET = AIController.GetSetting("water_lakes_ops_budget") != 0;
  WATER_SITE_CATALOG = AIController.GetSetting("water_site_catalog") != 0;
  WATER_DISCOVERY_REAL_FRONTS = AIController.GetSetting("water_discovery_real_fronts") != 0;
  C41_ROAD_REFRESH = AIController.GetSetting("c41_road_refresh") != 0;
  C41_ROAD_FREIGHT_SERVED_INDEX = AIController.GetSetting("c41_road_freight_served_index") != 0;
  C41_ROAD_FREIGHT_ACCEPTANCE_INDEX = AIController.GetSetting("c41_road_freight_acceptance_index") != 0;

  C41_RAIL_PAX_CRUISE_CACHE = AIController.GetSetting("c41_rail_pax_cruise_cache") != 0;
  C41_RAIL_FREIGHT_CRUISE_CACHE = AIController.GetSetting("c41_rail_freight_cruise_cache") != 0;
  C41_RAIL_FREIGHT_ACCELERATION_CACHE = AIController.GetSetting("c41_rail_freight_acceleration_cache") != 0;
  C41_RAIL_FREIGHT_TOWN_SERVICE_CACHE = AIController.GetSetting("c41_rail_freight_town_service_cache") != 0;
  C41_RAIL_LOST_SIGNAL_REPAIR = AIController.GetSetting("c41_rail_lost_signal_repair") != 0;
  C41_RAIL_LOST_JUNCTION_REPAIR = AIController.GetSetting("c41_rail_lost_junction_repair") != 0;
  C41_RAIL_CASH_RELEASE = AIController.GetSetting("c41_rail_cash_release") != 0;
  C49_VARIABLE_DENOMINATOR = AIController.GetSetting("c49_variable_denominator") != 0;
  C55_FREIGHT_ORIGIN_RELAX = AIController.GetSetting("c55_freight_origin_relax") != 0;
  C55_ROAD_ORIGIN_RELAX = AIController.GetSetting("c55_road_origin_relax") != 0;
  C55_ROAD_PAX_ORIGIN_RELAX = AIController.GetSetting("c55_road_pax_origin_relax") != 0;
  C60_TOWN_RATING_FILTER = AIController.GetSetting("c60_town_rating_filter") != 0;
  C48_INDEXED_REGENERATION = AIController.GetSetting("c48_indexed_regeneration") != 0;
  C48_INDEX_SHADOW = AIController.GetSetting("c48_index_shadow") != 0;
  C46_FREIGHT_GRID = AIController.GetSetting("c46_freight_grid") != 0;
  C46_FREIGHT_GRID_SHADOW = AIController.GetSetting("c46_freight_grid_shadow") != 0;
  C50B_ROAD_CAP_RELAX = AIController.GetSetting("c50b_road_cap_relax") != 0;
  ROAD_TIME_SCALED_CAP = AIController.GetSetting("road_time_scaled_cap") != 0;
  C50B_RAIL_BACKLOG_RELAX = AIController.GetSetting("c50b_rail_backlog_relax") != 0;
  VIVIER_RATIO_FILTER = AIController.GetSetting("vivier_ratio_filter") != 0;
  ROAD_FLEET_FIX = AIController.GetSetting("road_fleet_fix") != 0;
  AIR_FLEET_LINE_PRICE = AIController.GetSetting("air_fleet_line_price") != 0;
  AIR_CADENCE_CAP = AIController.GetSetting("air_cadence_cap") != 0;
  AIR_CADENCE_CAP_ADAPTIVE = AIController.GetSetting("air_cadence_cap_adaptive") != 0;
  if (AIR_CADENCE_CAP_ADAPTIVE) {
    local nIndustries = AIIndustryList().Count();
    if (nIndustries < 50) {
      AIR_CADENCE_CAP = false;
      AILog.Info("AIR_CADENCE_CAP_ADAPTIVE: nIndustries=" + nIndustries + " (<50) -> AIR_CADENCE_CAP desactive");
    } else {
      AILog.Info("AIR_CADENCE_CAP_ADAPTIVE: nIndustries=" + nIndustries + " (>=50) -> AIR_CADENCE_CAP conserve");
    }
  }
  ROAD_LOADING_FIX = AIController.GetSetting("road_loading_fix") != 0;
  CLEAN_DENSITY_SCORE = AIController.GetSetting("clean_density_score") != 0;
  local iap = AIController.GetSetting("infra_amort_pct");
  if (iap >= 0) INFRA_AMORT_PCT = iap;
  AIR_SITE_CACHE_ENABLED = AIController.GetSetting("air_site_cache") != 0;
  AIR_CHEAP_SITE = AIController.GetSetting("air_cheap_site") != 0;
  AIR_JOINED_STOPS = AIController.GetSetting("air_joined_stops") != 0;
  AIR_ROUTE_PLANE_SELECTION = AIController.GetSetting("air_route_plane_selection") != 0;
  local ajsl = AIController.GetSetting("air_joined_stop_limit");
  if (ajsl >= 0) AIR_JOINED_STOP_LIMIT = ajsl;
  AIR_EARLY_SLOT = AIController.GetSetting("air_early_slot") != 0;
  local aest = AIController.GetSetting("air_early_slot_target_towns");
  if (aest >= 1) AIR_EARLY_SLOT_TARGET_TOWNS = aest;
  local aesmp = AIController.GetSetting("air_early_slot_min_pop");
  if (aesmp >= 0) AIR_EARLY_SLOT_MIN_POP = aesmp;
  local aesb = AIController.GetSetting("air_early_slot_bonus_pct");
  if (aesb >= 0) AIR_EARLY_SLOT_BONUS_PCT = aesb;
  ROAD_CHEAP_TRACE = AIController.GetSetting("road_cheap_trace") != 0;
  ROAD_PAX_VOIRIE = AIController.GetSetting("road_pax_voirie") != 0;
  ROAD_PAX_OVERLAP = AIController.GetSetting("road_pax_overlap") != 0;

  /* --- Sondes de diagnostic unifiees (9 groupes) --- */

  // 1. probe_cost : rail_cost_probe, air_cost_probe, road_cost_probe
  local probeCost = AIController.GetSetting("probe_cost") != 0;
  RAIL_COST_PROBE = probeCost;
  AIR_COST_PROBE = probeCost;
  ROAD_COST_PROBE = probeCost;

  // 2. probe_scheduler : C41_SLACK, BUSY, STALENESS, OPPORTUNITY, ADMISSION, C39_CLOCK, C48_ATTEMPT, C41_SLICE
  local probeScheduler = AIController.GetSetting("probe_scheduler") != 0;
  C41_SLACK_LEDGER = probeScheduler;
  C41_MONTHLY_BUSY_LEDGER = probeScheduler;
  C41_STALENESS_LEDGER = probeScheduler;
  C41_OPPORTUNITY_LEDGER = probeScheduler;
  C41_ADMISSION_LEDGER = probeScheduler;
  C39_PASS_CLOCK_LEDGER = probeScheduler;
  C48_PROJECT_ATTEMPT_LEDGER = probeScheduler;
  C41_RAIL_SLICE_LEDGER = probeScheduler;

  // 3. probe_candidates_road : profiles pax, freight, town sinks
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
  /* Emboitement volontaire (perdu puis restaure le 2026-09-17) : sans le precontrole, activer
   * probe_catalogue ferait executer OpexWaterPlans() pour de vrai (BFS littoral, tests de dock
   * sous AITestMode) au lieu de rester une sonde passive. */
  C41_WATER_CANDIDATE_PROBE = probeCat && C41_WATER_PRECHECK;
  C41_WATER_PLANS_PROFILE = probeCat && C41_WATER_CANDIDATE_PROBE;
  C41_WATER_SITE_PROFILE = probeCat && C41_WATER_PLANS_PROFILE;

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
  C41_RAIL_LOST_PROBE = probeLost || C41_RAIL_LOST_SIGNAL_REPAIR || C41_RAIL_LOST_JUNCTION_REPAIR;
  C41_VEHICLE_LOST_PROBE = probeLost || C41_RAIL_LOST_PROBE;

  // 8. probe_portfolio : scarcity, chronology, invest C63, funnel, tension, incremental, reserves, origin relax, town rating
  local probePort = AIController.GetSetting("probe_portfolio") != 0;
  C49_SCARCITY_LEDGER = probePort || C49_VARIABLE_DENOMINATOR;
  if (C49_SCARCITY_LEDGER) {
    ::C49_CURRENT_REGIME = "cash";
  }
  C50_CHRONOLOGY_PROBE = probePort;
  if (C50_CHRONOLOGY_PROBE) {
    OpexC50ResetNonExpansionLedger();
  }
  C63_INVEST_PROBE = probePort;
  if (C63_INVEST_PROBE) OpexC63ResetLedger();
  MONTHLY_FUNNEL = probePort;
  TENSION_PROBE = probePort;
  if (TENSION_PROBE) {
    PORTFOLIO_LOG = true;
  }
  C48_INCREMENTAL_PROFILE = probePort;
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
      revalidated = 0, origin_blocked = 0, spared = 0,
      attempted = 0, precheck_ok = 0, financeable = 0,
      planned = 0, viable = 0, built = 0, built_profit = 0,
      total_revalidated = 0, total_origin_blocked = 0, total_spared = 0,
      total_attempted = 0, total_precheck_ok = 0, total_financeable = 0,
      total_planned = 0, total_viable = 0, total_built = 0, total_built_profit = 0,
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

  // 9. probe_events : C52 autoreplace, exposure, crash, unprofitable, first vehicle, C56 task trace, C42 subsidy, air fleet/catchment, equipment roi, vehicle orders
  local probeEvents = AIController.GetSetting("probe_events") != 0;
  C52_AUTOREPLACE_LOG = probeEvents;
  if (C52_AUTOREPLACE_LOG) {
    C52_AUTOREPLACE_LEDGER = {
      events = 0, remap_line_vehicles = 0, remap_line_vehicle = 0, remap_scrap_vehicles = 0,
      remap_scrap_index = 0, untracked = 0, rail = 0, road = 0, air = 0, water = 0, unknown = 0,
      line_rail = 0, line_road = 0, line_air = 0, line_water = 0,
      total_events = 0, total_remap_line_vehicles = 0, total_remap_line_vehicle = 0,
      total_remap_scrap_vehicles = 0, total_remap_scrap_index = 0, total_untracked = 0,
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
  C42_SUBSIDY_LOG = probeEvents;
  AIR_FLEET_PROBE = probeEvents;
  AIR_CATCHMENT_PROBE = probeEvents;
  EQUIPMENT_ROI_PROBE = probeEvents;
  C54_VEHICLE_ORDERS_PROBE = probeEvents;
}
