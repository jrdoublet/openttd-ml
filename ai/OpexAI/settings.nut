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
  probe_cost = 64,
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

/* Niveau 0..3. Sur OpenTTD <= 13.4, script.settings_profile (0 facile, 1 moyen,
 * 2 difficile ; 3 personnalise existait hors menu) fait foi. Sur 14/15.3 le
 * reglage a disparu : opex_difficulty, dont les quatre valeurs valent 2, est
 * le niveau. Un banc qui ne le passe pas joue donc en difficile. */
function OpexResolveDifficulty()
{
  if (AIGameSettings.IsValid("script.settings_profile")) {
    local profile = AIGameSettings.GetValue("script.settings_profile");
    if (profile == null || profile < 0) return 0;
    if (profile > 3) return 3;
    return profile;
  }
  local value = AIController.GetSetting("opex_difficulty");
  if (value == null || value < 0) return 2;
  if (value > 3) return 3;
  return value;
}

/* C65 passe 2 & regroupement macro-politiques : lecture unique des reglages.
 * Fonction libre : n'affecte que des globales. Les mutations d'instance
 * restent dans Start(), juste apres l'appel. */
function OpexLoadSettings()
{
  /* V276/V278 (defaut auto depuis le 20/10, decision utilisateur) : qualifies ensemble a 1024x1024
   * seulement (portes A +631 k et B +1,11 M), sans gain mesure a 256x256 ; actifs des 1024x1024 tuiles. */
  local bigMap = AIMap.GetMapSizeX() * AIMap.GetMapSizeY() >= 1024 * 1024;
  local v278 = AIController.GetSetting("v278_air_lazy_sites");
  V278_AIR_LAZY_SITES = v278 == 1 || (v278 == 2 && bigMap);
  /* V277/V279 (defaut auto depuis le 20/10, decision utilisateur) : qualifies a 1024x1024 par V287
   * (porte B +680 k, porte A +237 k non significative) ; negatifs a 256x256 (banc PC -195 k, 6/14).
   * 3 = auto : 1 des 1024x1024 tuiles, 0 sinon. */
  local v279 = AIController.GetSetting("v279_reselect_memo");
  V279_RESELECT_MEMO = (v279 == 3) ? (bigMap ? 1 : 0) : v279;
  V233_PENDING_CONTINUE = AIController.GetSetting("v233_pending_continue") != 0;
  V233_GOODS_GRAFT = AIController.GetSetting("v233_goods_graft") != 0;
  if (V233_GOODS_GRAFT && !V233_PENDING_CONTINUE) {
    AILog.Warning("V233: v233_goods_graft refused: v233_pending_continue=0");
    V233_GOODS_GRAFT = false;
  }
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
  OPEX_DIFFICULTY = OpexResolveDifficulty();
  OPEX_LEVEL_LIMITS = !OpexLevelAllows("encroach_rival_catchment") || !OpexLevelAllows("compete_primary_industry")
      || !OpexLevelAllows("airport_rival_town") || !OpexLevelAllows("preempt_last_airport_slot");

  /* --- 2. Interrupteurs de mode et options rail --- */

  // V166 : interrupteurs de mode conserves pour les bancs monomodes.
  MODE_AIR = AIController.GetSetting("mode_air") != 0;
  MODE_RAIL = AIController.GetSetting("mode_rail") != 0;
  MODE_ROAD = AIController.GetSetting("mode_road") != 0;
  MODE_WATER = AIController.GetSetting("mode_water") != 0;
  // V261 point 6 : couper aussi les modes que la partie interdit aux IA ou dont le plafond vaut 0.
  if (MODE_AIR && !OpexModeAllowedByGame("air")) MODE_AIR = false;
  if (MODE_RAIL && !OpexModeAllowedByGame("rail")) MODE_RAIL = false;
  if (MODE_ROAD && !OpexModeAllowedByGame("road")) MODE_ROAD = false;
  if (MODE_WATER && !OpexModeAllowedByGame("water")) MODE_WATER = false;
  V177_RAIL_PAX_MIN_DIST = AIController.GetSetting("v177_rail_pax_min_dist");
  if (V177_RAIL_PAX_MIN_DIST < 0) V177_RAIL_PAX_MIN_DIST = 0;
  local freightMin = AIController.GetSetting("v182_rail_freight_min_dist");
  V182_RAIL_FREIGHT_MIN_DIST = (freightMin != null && freightMin > 0) ? freightMin : 0;
  V216_PROBE = AIController.GetSetting("v216_probe") != 0;
  V211_RIVALS = AIController.GetSetting("v211_rivals_log") != 0;
  V216A_GHOST_DEMAND = AIController.GetSetting("v216a_ghost_demand");
  V216F_DWELL_PCT = AIController.GetSetting("v216f_dwell_pct");
  V264_CONVERGENT_FREIGHT = AIController.GetSetting("v264_convergent_freight") != 0;
  local lateRelax = AIController.GetSetting("v269_rail_late_relax");
  local railGrowth = AIController.GetSetting("v284_rail_growth");
  if (railGrowth != null && railGrowth >= 0 && railGrowth <= 10) V284_RAIL_GROWTH = railGrowth;
  local v294BridgeLen = AIController.GetSetting("v294_rail_bridge_len");
  V294_RAIL_BRIDGE_LEN = (v294BridgeLen != null && v294BridgeLen >= 0 && v294BridgeLen <= 30) ? v294BridgeLen : 0;
  local v294Continuous = AIController.GetSetting("v294_rail_continuous");
  V294_RAIL_CONTINUOUS = (v294Continuous != null && v294Continuous > 0) ? 1 : 0;
  local railDefer = AIController.GetSetting("v294_rail_defer");
  if (railDefer != null && railDefer >= 0 && railDefer <= 5000) V294H_RAIL_DEFER = railDefer;
  local weightAdapt = AIController.GetSetting("v294_rail_weight_adapt");
  V294C_RAIL_WEIGHT_ADAPT = (weightAdapt != null && weightAdapt >= 100 && weightAdapt <= 400) ? weightAdapt : 0;
  V269_RAIL_LATE_RELAX = (lateRelax != null && lateRelax > 0 && lateRelax <= 9) ? lateRelax : 0;
  local v182Years = AIController.GetSetting("v195_v182_years");
  V195_V182_YEARS = (v182Years != null && v182Years > 0 && v182Years <= 10) ? v182Years : 0;
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
  local v275 = AIController.GetSetting("v275_rail_pax_mm");
  V275_RAIL_PAX_MM = (v275 != null && v275 >= 0 && v275 <= 15) ? v275 : 0;
  /* V275 bit 8 (defaut 15 depuis le 20/10, decision utilisateur) : reglage selon le mode.
   * Sans aerien, paquet qualifie en rail seul (portes A +635 k et B +791 k) : bits 1/2/4 et,
   * si les reglages V207 sont a leur defaut, part 40 + courrier + 2 arrets joints. Avec
   * l'aerien, masque ramene a 0 : le paquet y perd a 3 ans (-71 k) et le bras sobre y est
   * neutre (+0,2 k), donc le comportement multimodal reste celui d'avant V275. */
  if (V275_RAIL_PAX_MM & 8) {
    if (MODE_AIR) {
      V275_RAIL_PAX_MM = 0;
    } else if (V207_RAIL_PAX_SHARE_PCT == 0 && !V207_RAIL_MAIL && V207_RAIL_PAX_JOINED_STOPS == 0) {
      V207_RAIL_PAX_SHARE_PCT = 40;
      V207_RAIL_MAIL = true;
      V207_RAIL_PAX_JOINED_STOPS = 2;
    }
  }
  local v190Delay = AIController.GetSetting("v190_rail_double_delay");
  if (v190Delay == null || v190Delay < 0) v190Delay = 0;
  V190_FROM_YEAR = AIDate.GetYear(AIDate.GetCurrentDate()) + v190Delay;
  local v190Max = AIController.GetSetting("v190_rail_max_trains");
  V190_RAIL_MAX_TRAINS = (v190Max != null && v190Max >= 2 && v190Max <= 8) ? v190Max : 4;
  V249_STATUE = AIController.GetSetting("v249_statue") == 1;
  local rights = AIController.GetSetting("v250_rights");
  if (rights == null || rights < 0 || rights > 4) rights = 0;
  /* V250 entiere reservee au niveau 3 (personnalise) : geste anticoncurrentiel. */
  if (!OpexLevelAllows("v250_rights")) rights = 0;
  V250_RIGHTS = rights;
  local v259Renew = AIController.GetSetting("v259_bridge_renew");
  V259_BRIDGE_RENEW = (v259Renew != null && v259Renew == 1) ? 1 : 0;
  local v277Pub = AIController.GetSetting("v277_air_pub_fast");
  if (v277Pub == 3) v277Pub = AIMap.GetMapSizeX() * AIMap.GetMapSizeY() >= 1024 * 1024 ? 1 : 0;
  V277_AIR_PUB_FAST = (v277Pub != null && v277Pub >= 0 && v277Pub <= 2) ? v277Pub : 0;
  local railWeightPct = AIController.GetSetting("v294_rail_weight_pct");
  if (railWeightPct != null && (railWeightPct == 0 || (railWeightPct >= 100 && railWeightPct <= 400))) {
    V294_RAIL_WEIGHT_PCT = railWeightPct;
  }
  local aaaCosts = AIController.GetSetting("v294_rail_aaa_costs");
  if (aaaCosts != null && (aaaCosts == 0 || aaaCosts == 1)) {
    V294_RAIL_AAA_COSTS = aaaCosts;
  }
  local revProbe = AIController.GetSetting("v294_rail_reverse_probe");
  if (revProbe != null && revProbe >= 0) {
    V294_RAIL_REVERSE_PROBE = revProbe;
  }
  local distDecouple = AIController.GetSetting("v294_rail_dist_decouple");
  if (distDecouple != null && distDecouple >= 0) {
    V294_RAIL_DIST_DECOUPLE = distDecouple;
  }
  local slopeEngine = AIController.GetSetting("v294_rail_slope_engine");
  if (slopeEngine != null && slopeEngine >= 0) {
    V294_RAIL_SLOPE_ENGINE = slopeEngine;
  }
  local v295Fast = AIController.GetSetting("v295_astar_fast");
  V295_ASTAR_FAST = (v295Fast != null && v295Fast == 1) ? 1 : 0;
  local v297Floor = AIController.GetSetting("v297_rail_roi_floor");
  V297_RAIL_ROI_FLOOR = (v297Floor != null && v297Floor > 0) ? v297Floor : 0;
  local v297Relax = AIController.GetSetting("v297_relax_stations");
  V297_RELAX_STATIONS = (v297Relax != null && v297Relax > 0) ? v297Relax : 0;

  // V246 : paquets adoptes figes ; les interrupteurs de mode restent actifs.
  ROAD_BUILD_ENABLED = MODE_ROAD;
  // Repli interne avant l'amorcage plat, qui le desactive plus bas.
  STAGED_BOOTSTRAP = true;

  /* --- 3. Calibrations physiques et options reelles --- */

  RAIL_GEOMETRY_GUARD = AIController.GetSetting("rail_geometry_guard") != 0;
  RAIL_GEOMETRY_EXACT_IDENTITY = AIController.GetSetting("rail_geometry_exact_identity") != 0;
  RAIL_GEOMETRY_PREFILTER = AIController.GetSetting("rail_geometry_prefilter") != 0;
  RAIL_GEOMETRY_PAIR_MEMORY = AIController.GetSetting("rail_geometry_pair_memory") != 0;
  RAIL_FAILURE_AUDIT = OpexProbeSetting("rail_failure_audit") != 0;
  RAIL_GEOMETRY_LIVE_REPLAN = AIController.GetSetting("rail_geometry_live_replan") != 0;

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
  {
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

  // 3. probe_candidates_road : profiles pax, freight, town sinks
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
  ::OpexCalibratedProfit <- OpexC70Profit;
  C69_BOTTLENECK_PROBE = probePort;
  C83_FIXES = AIController.GetSetting("c83_fixes") != 0;
  C83_LOCAL_REPAIR = AIController.GetSetting("c83_local_repair") != 0;
  C83_PREEMPT_OPEN = AIController.GetSetting("c83_preempt_open") != 0;
  V95_AIR_POST73_YEAR = -1;
  V134_AIR_P2P_SATURATED_HUB = AIController.GetSetting("v134_air_p2p_saturated_hub") != 0;
  V133_AIR_BUILD_RETRY = AIController.GetSetting("v133_air_build_retry") != 0;
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
  {
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
  {
    OpexC75BypassResetYearLedger();
  }
  {
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
  C67_TERRAIN_MAP = AIController.GetSetting("c67_terrain_map") != 0;
  C67_WATER_EXPOSURE = OpexProbeSetting("c67_water_exposure_probe") != 0;
  C67_SLACK_HOOK = C67_TERRAIN_MAP || C67_WATER_EXPOSURE;
  /* C77 corrige est permanent et repose sur le socle du double registre. */
  C41_RAIL_LOST_SIGNAL_REPAIR = false;
  C41_RAIL_LOST_JUNCTION_REPAIR = false;
  local railRefill = AIController.GetSetting("v217_rail_refill");
  V217_RAIL_REFILL = (railRefill != null && railRefill >= 0 && railRefill <= 2) ? railRefill : 0;
  V217_LAST_MONTH = -1;
  local v276 = AIController.GetSetting("v276_cand_slices");
  V276_CAND_SLICES = (v276 == 3) ? (bigMap ? 2 : 0) : v276;
  V276_CATALOG_TASK = null;
  V276_CARGO_YEAR = -1;
  V276_CARGO_ORDER = null;
  AIR0310_SITE_VALIDITY_STATE = null;
  RAIL_DEPOT_COST = AIController.GetSetting("rail_depot_cost") != 0;
  V131_RAIL_REPAIR = AIController.GetSetting("v131_rail_repair") != 0;
  V131_TOWN_CLEARANCE = AIController.GetSetting("v131_town_clearance") != 0;
  WATER_OPCODE_COMPAT_FALSE = false;
  WATER_OPCODE_COMPAT_FALSE = false;
  AIR_MAX_DISTANCE = 0;
  TRANSIT_COST_PERMILLE = 0;
  INFRA_AMORT_PCT = 0;
  PORTFOLIO_MAX_BATCH = 1;
  AIR_FLEET_BUFFER = 0;
}
