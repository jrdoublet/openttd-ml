/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexC50ResetNonExpansionLedger()
{
  C50_NON_EXPANSION_LEDGER = {
    air = {
      want_sum = 0,
      ref_Y = 0,
      ref_V = 0,
      ref_D = 0,
      ref_L = 0,
      ref_C = 0,
      ref_Q = 0,
      ref_S = 0,
      ref_W = 0,
      ref_M = 0,
      ref_X = 0,
      ref_R = 0
    },
    rail = {
      cash_refused = 0,
      prep_failed = 0,
      upgrade_failed = 0,
      second_built = 0,
      double_built = 0
    },
    road = {
      physical_cap_hit = 0,
      congestion_hit = 0,
      no_demand = 0,
      loss_hit = 0,
      cash_refused = 0,
      other_refused = 0,
      refill_built = 0
    }
  };
}
function OpexSign(anchor, name)
{
  if (!DEBUG_SIGNS) return;
  AISign.BuildSign(anchor, name);
}
function OpexDecide(kind, fields)
{
  local date = AIDate.GetCurrentDate();
  if (_currentTaskName != null && !_currentTaskLogged && kind != "TASK") {
    _currentTaskLogged = true;
    local cur = _currentTaskName;
    _currentTaskName = null;
    OpexDecide("TASK", "name=" + cur);
    _currentTaskName = cur;
  }
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C39.0 : le journal de la sonde est indépendant de DECISION_LOG. Ce dernier instrumente toute
 * l'IA et change son budget d'opcodes ; C39 doit pouvoir observer le seul routeur passif. */
function OpexC39Log(kind, fields)
{
  if (!C39_INVALIDATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C41.11 reste lisible sans activer le bus C39 : il mesure le scheduler historique lui-meme. */
function OpexC41SchedulerLog(kind, fields)
{
  if (!C41_SLACK_LEDGER && !C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C41.46 : sonde independante de la famille C41.11/13/14 -- son propre gate, comme les sondes
 * rail-lost ci-dessous. OpexC41SchedulerLog aurait silencieusement avale ces lignes tant qu'aucun
 * des trois autres flags n'est actif (piege trouve au premier smoke test). */
function OpexC41RailSliceLog(fields)
{
  if (!C41_RAIL_SLICE_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_SLICE_LEDGER " + fields);
}
/* C48 : gate dedie, independant de C39/C41. Une sonde armee seule ne doit jamais etre absorbee
 * par le flag d'une autre fiche. */
function OpexC48ProjectAttemptLog(fields)
{
  if (!C48_PROJECT_ATTEMPT_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C48_PROJECT_ATTEMPT " + fields);
}
/* C49 : gate dedie. Ne jamais reutiliser celui de C48/C39/C41 : armer seulement cette sonde
 * doit suffire a publier ses lignes. */
function OpexC49ScarcityLog(fields)
{
  if (!C49_SCARCITY_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C49_SCARCITY " + fields);
}
/* C50 : gate dedie pour la sonde chronologique legere (tresorerie, profit par ligne,
 * projets batis avec cout/ROI, projets refuses pour tresorerie avec ROI).
 * Autonome : fonctionne avec decision_log=0. */
function OpexC50ChronologyLog(fields)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C50_CHRONO " + fields);
}
/* C50 : enregistrement deduplique des refus de tresorerie (au plus un log par mois calendaire et par candidat). */
function OpexC50LogCashRefusal(mode, rank, cost, profit, roi, src, dst, need, money)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  local ym = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  local key = mode + "|" + src + "|" + dst;
  if ((key in C50_REFUSE_CACHE) && C50_REFUSE_CACHE[key] == ym) return;
  C50_REFUSE_CACHE[key] <- ym;

  local available = OpexAvailableCapital();
  local loan = AICompany.GetLoanAmount();
  OpexC50ChronologyLog("phase=refused_cash mode=" + mode + " rank=" + rank
      + " cost=" + cost + " profit=" + profit + " roi=" + roi
      + " need=" + need + " cash=" + money + " loan=" + loan + " available=" + available);
}
/* C55 : gate dedie et autonome. Ne jamais reutiliser le gate C49 : la sonde doit publier seule. */
function OpexC55OriginRelaxLog(fields)
{
  if (!C55_ORIGIN_RELAX_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C55_ORIGIN_RELAX " + fields);
}
/* C55 : gate autonome pour la tracabilite causale PAX. */
function OpexC55PaxTraceLog(kind, fields)
{
  if (!C55_PAX_TRACE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* C56 : gate dedie et autonome. Lecture des traces :
 * - dernier TASK_ENTER name=X sans TASK_EXIT name=X : X ne rend pas la main, blocage dedans ;
 * - dernier STAGE_ENTER name=c56_stage_X sans STAGE_EXIT : blocage dans cette phase du portefeuille ;
 * - les phases sautees emettent aussi STAGE_EXIT : un jalon manquant signifie toujours un blocage ;
 * - TASK_ENTER/TASK_EXIT apparies jusqu'au bout puis plus rien : blocage hors tache ;
 * - LOOP_TICK continu sans TASK_ENTER : boucle active, ordonnanceur sans selection ;
 * - plus aucune trace : script lui-meme plus execute par le moteur. */
function OpexC56TaskLog(kind, name, cycle)
{
  if (!C56_TASK_TRACE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C56_TASK " + kind + " name=" + name
             + " cycle=" + cycle);
}
/* C52 : gate dedie et autonome. La sonde observe aussi quand la reparation est desarmee. */
function OpexC52AutoreplaceLog(fields)
{
  if (!C52_AUTOREPLACE_LOG) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C52_AUTOREPLACE " + fields);
}
/* C52 : gate dedie et autonome. La sonde ne publie que son propre ledger annuel. */
function OpexC52EventExposureLog(fields)
{
  if (!C52_EVENT_EXPOSURE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C52_EVENT_EXPOSURE " + fields);
}
/* Observe une paire au point meme ou le filtre d'origine route la voit. Cette fonction ne
 * retourne rien et n'ecrit que le ledger de sonde ; elle ne participe a aucun predicat. */
function OpexC55OriginRelaxObserve(kind, lines, src, dst, srcServed, dstServed)
{
  if (!C55_ORIGIN_RELAX_PROBE || C55_ORIGIN_RELAX_LEDGER == null) return;
  C55_ORIGIN_RELAX_LEDGER.candidates_seen++;
  if (!srcServed && !dstServed) return;
  C55_ORIGIN_RELAX_LEDGER.rejected_total++;
  if (srcServed && dstServed) {
    C55_ORIGIN_RELAX_LEDGER.both_served++;
    return;
  }
  C55_ORIGIN_RELAX_LEDGER.one_served++;
  if (kind == "pax") C55_ORIGIN_RELAX_LEDGER.one_served_pax++;
  else C55_ORIGIN_RELAX_LEDGER.one_served_freight++;
  /* Cle disponible ici : meme paire geometrique, dans un sens ou dans l'autre, a moins de
   * ORIGIN_SEPARATION des deux originA/originB d'une ligne route existante. */
  if (OpexRoadPairServed(lines, src, dst)) C55_ORIGIN_RELAX_LEDGER.duplicate_exact++;
}
/* C55 : observateurs pour la tracabilite causale PAX */
function OpexC55PaxTraceObserveRevalidated(isOriginBlocked)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.revalidated++;
  if (isOriginBlocked) C55_PAX_TRACE_LEDGER.origin_blocked++;
}
function OpexC55PaxTraceObserveSpared()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.spared++;
}
function OpexC55PaxTraceObserveAttempted()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.attempted++;
}
function OpexC55PaxTraceObservePrecheckOk()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.precheck_ok++;
}
function OpexC55PaxTraceObserveFinanceable()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.financeable++;
}
function OpexC55PaxTraceObservePlanned()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.planned++;
}
function OpexC55PaxTraceObserveViable()
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.viable++;
}
function OpexC55PaxTraceObserveBuilt(profit)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  C55_PAX_TRACE_LEDGER.built++;
  C55_PAX_TRACE_LEDGER.built_profit += profit;
}
function OpexC49VehicleType(mode)
{
  if (mode == "rail") return AIVehicle.VT_RAIL;
  if (mode == "road") return AIVehicle.VT_ROAD;
  if (mode == "air" || mode == "fleet") return AIVehicle.VT_AIR;
  if (mode == "water") return AIVehicle.VT_WATER;
  return -1;
}
function OpexC49IsMapFailure(passDiscards, rank)
{
  foreach (discard in passDiscards) {
    if (discard.rank != rank) continue;
    if (discard.reason == "build_failed" || discard.reason == "plan_failed"
        || discard.reason == "too_close" || discard.reason == "too_close_hard"
        || discard.reason == "too_close_no_join") return true;
  }
  return false;
}
/* C48.1 : gate dedie. Ne jamais reutiliser celui des tentatives C48 : une sonde armee seule
 * doit publier ses propres lignes. */
function OpexC48IncrementalLog(fields)
{
  if (!C48_INCREMENTAL_PROFILE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C48_INCREMENTAL " + fields);
}
/* C41.47 : un evenement par liberation, pas un accumulateur annuel -- les liberations sont
 * rares (motif observe : quelques par partie), la mesure interessante est LEQUEL candidat et
 * QUAND, pas un total. */
function OpexC41RailCashReleaseLog(fields)
{
  if (!C41_RAIL_CASH_RELEASE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_CASH_RELEASE " + fields);
}
/* C41.48 : un evenement par frontiere de tranche -- la frequence de declenchement EST la
 * mesure (repond a "sur combien de frontieres le test C41.49 aurait-il seulement l'occasion
 * de s'appliquer ?"), donc pas d'agregat qui la masquerait. */
function OpexC41RailDominationLog(fields)
{
  if (!C41_RAIL_DOMINATION_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_DOMINATION_PROBE " + fields);
}
/* C41.49 : son propre gate, comme C41.46/C41.47/C41.48 -- OpexC41SchedulerLog et
 * OpexC41RailDominationLog l'auraient sinon silencieusement avale (piege deja trouve trois fois). */
function OpexC41ProjectsFallthroughLog(fields)
{
  if (!C41_PROJECTS_FALLTHROUGH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_PROJECTS_FALLTHROUGH_PROBE " + fields);
}
/* C39.5 : gate propre -- ne jamais reutiliser celui d'une autre sonde, sinon armer seulement
 * c39_projects_cadence_probe rendrait le canal silencieux. */
function OpexC39ProjectsCadenceLog(fields)
{
  if (!C39_PROJECTS_CADENCE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PROJECTS_CADENCE " + fields);
}
/* C39.6 : gate propre, INDEPENDANT de C39_PROJECTS_CADENCE_PROBE et de C41_RAIL_SLICE_LEDGER --
 * ne jamais reutiliser le gate d'une autre sonde (piege deja trouve trois fois dans ce depot :
 * un canal reutilise reste silencieux tant que SA propre variante n'est pas armee). */
function OpexC39PassClockLog(fields)
{
  if (!C39_PASS_CLOCK_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C39_PASS_CLOCK " + fields);
}
function OpexC41StalenessLog(kind, fields)
{
  if (!C41_STALENESS_LEDGER) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
/* Contrat C41.14 : le hint est une borne prudente d'admission, pas une moyenne ni un budget
 * reservé. Le scheduler ne le lit pas encore pour executer : cette phase mesure seulement si le
 * point d'entree cible pourrait tenir dans le reliquat du tick courant. */
function OpexC41MicrotaskOpsHint(layer)
{
  if (layer == "catalog.water") return 350;
  return -1;
}
/* C41.4 reste observable sans armer C39 : c'est un inventaire de l'evenement, pas une
 * invalidation de catalogue. */
function OpexC41VehicleLostLog(fields)
{
  if (!C41_VEHICLE_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_VEHICLE_LOST " + fields);
}
function OpexC41RailLostLog(fields)
{
  if (!C41_RAIL_LOST_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST " + fields);
}
/* Gate C54 autonome : AIDate et AILog ne sont atteignables que si le reglage C54 est actif. */
function OpexC54VehicleOrdersLog(fields)
{
  if (!C54_VEHICLE_ORDERS_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C54_VEHICLE_ORDERS " + fields);
}
function OpexC41RailLostTopologyLog(fields)
{
  if (!C41_RAIL_LOST_TOPOLOGY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_TOPOLOGY " + fields);
}
function OpexC41RailLostPhysicalLog(fields)
{
  if (!C41_RAIL_LOST_PHYSICAL_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_PHYSICAL " + fields);
}
function OpexC41RailSignalRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_SIGNAL_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexC41RailLostConnectivityLog(fields)
{
  if (!C41_RAIL_LOST_CONNECTIVITY_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " C41_RAIL_LOST_CONNECTIVITY " + fields);
}
function OpexC41RailJunctionRepairLog(kind, fields)
{
  if (!C41_RAIL_LOST_JUNCTION_REPAIR) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " " + kind + " " + fields);
}
function OpexC39ProjectSignature(projects)
{
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) {
    return "none";
  }
  local project = projects.best[0];
  return project.mode + ":" + project.src + ":" + project.dst;
}
function OpexC41RevisionSnapshot(revisions)
{
  return "c=" + revisions.catalog.cargos + "," + revisions.catalog.towns + ","
         + revisions.catalog.industries + "," + revisions.catalog.rail + ","
         + revisions.catalog.road + "," + revisions.catalog.air + ","
         + revisions.catalog.water + " d=" + revisions.candidates.rail + ","
         + revisions.candidates.road + "," + revisions.candidates.air + ","
         + revisions.candidates.water + " p=" + revisions.portfolio + " s="
         + revisions.selection;
}
/* Le moteur a-t-il survécu au filtre propre à son mode ? Ce n'est pas une décision de
 * construction : C39.3 mesure précisément si le catalogue aurait une raison de propager l'event. */
function OpexC39CatalogUsesEngine(catalog, engine, mode)
{
  if (catalog == null) return false;
  if (mode == "rail") {
    if (catalog.railLocos != null) foreach (loco in catalog.railLocos) if (loco.id == engine) return true;
    if (catalog.wagonByCargo != null) foreach (cargo, wagon in catalog.wagonByCargo) if (wagon.id == engine) return true;
  } else if (mode == "road") {
    if (catalog.roadEngineByCargo != null) foreach (cargo, vehicle in catalog.roadEngineByCargo) if (vehicle.id == engine) return true;
  } else if (mode == "air") {
    if (catalog.plane != null && catalog.plane.id == engine) return true;
    if (catalog.airCombos != null) foreach (combo in catalog.airCombos) if (combo.plane.id == engine) return true;
  } else if (mode == "water") {
    if (catalog.ships != null) foreach (ship in catalog.ships) if (ship.id == engine) return true;
  }
  return false;
}
/* `retained=0` air signifie seulement que le moteur n'est pas le gagnant de `airCombos`.
 * Cette sonde separe les filtres eliminatoires de la domination capacite/vitesse, sans modifier
 * l'algorithme de selection. */
function OpexC39AirEngineReason(catalog, engine)
{
  if (catalog == null || !AIEngine.IsValidEngine(engine)) return "invalid";
  if (!AIEngine.IsBuildable(engine)) return "not_buildable";
  if (catalog.paxCargo < 0 || !AIEngine.CanRefitCargo(engine, catalog.paxCargo)) return "no_pax_refit";
  local planeType = AIEngine.GetPlaneType(engine);
  if (planeType != AIAirport.PT_SMALL_PLANE && planeType != AIAirport.PT_BIG_PLANE) return "unsupported_type";
  if (AIEngine.GetCapacity(engine) <= 0) return "zero_capacity";
  if (OpexC39CatalogUsesEngine(catalog, engine, "air")) return "selected";
  return "dominated";
}
function OpexCashReserveProbeLog(fields)
{
  if (!CASH_RESERVE_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " CASH_RESERVE_PROBE " + fields);
}
function OpexPortfolioRefreshProbeLog(fields)
{
  if (!PORTFOLIO_REFRESH_PROBE) return;
  local date = AIDate.GetCurrentDate();
  AILog.Info("OPEX " + AIDate.GetYear(date) + "-" + AIDate.GetMonth(date) + "-"
             + AIDate.GetDayOfMonth(date) + " PORTFOLIO_REFRESH_PROBE " + fields);
}
