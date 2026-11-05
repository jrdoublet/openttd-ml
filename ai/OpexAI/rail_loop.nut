/* RAIL-LOOP (rail_loop=1, defaut 0) : doublement differe d'une ligne fret
 * SIMPLE en boucle a sens unique qui TRAVERSE ses deux gares.
 *
 * Voie 1 (existante) : sortie avant de la gare amont -> sortie avant de la
 * gare aval. Voie 2 (neuve) : sortie ARRIERE du quai aval -> sortie ARRIERE
 * du quai amont. Un quai ferroviaire OpenTTD est traversant : la rame entre
 * par un bout, s'arrete, ressort par l'autre bout, sans rebroussement. Toutes
 * les rames tournent dans le meme sens ; des PBS_ONEWAY espaces d'au moins
 * sept cases sur les deux voies autorisent 4 a 8 rames sur les ordres
 * partages existants (chargement complet amont, dechargement aval).
 *
 * Ce que ce module evite volontairement (causes des echecs du 3 novembre) :
 *  - aucun aiguillage de gorge ni quai parallele (V190-FIX2 : virages 90 deg,
 *    DIRECTIONAL_NO_SAFE_SWITCH_PAIR, NOPLATFORM ; DOUBLE-GROW :
 *    NO_PARALLEL_BAND, NO_NATIVE_STATION_SITES) ;
 *  - aucun embranchement de depot neuf (RDS : 26 rames perdues) : le depot
 *    primaire est garde, on lui ajoute au plus la courbe de sortie aval ;
 *  - aucune occupation du slot _railSearch (V190 : search_in_progress) : la
 *    recherche A* a son etat propre, avance d'une tranche bornee par passe
 *    de l'ordonnanceur et ne preempte ni ne bloque aucun projet ;
 *  - aucun refus de caisse bloquant (DOUBLE-GROW v2 : 356 skip_cash sur la
 *    meme ligne) : une ligne trop chere est reportee, le balayage continue.
 *
 * Etat transitoire owner._railLoopState (non sauvegarde). Les champs de
 * ligne railLoop* sont persistants : 1 = en cours (voie 2 posee si
 * railLoopTrack2 existe), 2 = boucle certifiee, -1 = echec avec delai. */

RAIL_LOOP_CURSOR <- 0;
RAIL_LOOP_SLICE <- 200;          // iterations A* par passe de l'ordonnanceur
RAIL_LOOP_BUDGET <- 8000;        // iterations A* au total pour la voie 2
RAIL_LOOP_MAX_TRAINS <- 8;
RAIL_LOOP_MIN_SPACING <- 7;      // espacement minimal des PBS (cases)
RAIL_LOOP_ARM_DAYS <- 180;       // delai maximal pour armer la voie 1
RAIL_LOOP_GROW_DAYS <- 45;       // au plus une rame neuve par ligne et periode
RAIL_LOOP_RETRY_DAYS <- 365;

function OpexRailLoopLog(line, phase, detail)
{
  if (!DECISION_LOG) return;
  OpexDecide("RLOOP", "phase=" + phase
      + " line=" + ((line != null && ("lineId" in line)) ? line.lineId : -1)
      + " trains=" + ((line != null && ("trains" in line)) ? line.trains : -1)
      + (detail != "" ? " " + detail : ""));
}

/* Plan d'extremite ARRIERE d'un quai, au format du pathfinder
 * (anchor/step/length/station_exit/lead). Conventions de builder_rail.nut :
 * station_exit == anchor => lead = anchor - step ; sinon station_exit est la
 * derniere case du quai et lead = station_exit + step. */
function OpexRailLoopBackPlan(platform)
{
  if (platform == null || !("anchor" in platform) || !("step" in platform)
      || !("length" in platform) || !("station_exit" in platform)
      || !("lead" in platform) || platform.length < 2) return null;
  local endFar = platform.station_exit != platform.anchor;
  local backExit = endFar ? platform.anchor
      : platform.anchor + platform.step * (platform.length - 1);
  local backLead = endFar ? backExit - platform.step : backExit + platform.step;
  if (!AIMap.IsValidTile(backExit) || !AIMap.IsValidTile(backLead)
      || AIMap.DistanceManhattan(backExit, backLead) != 1
      || !AIRail.IsRailStationTile(backExit)
      || AIStation.GetStationID(backExit) != AIStation.GetStationID(platform.station_exit)
      || !AITile.IsBuildable(backLead)
      || AITile.GetSlope(backLead) != AITile.SLOPE_FLAT) return null;
  /* L'ancre du plan arriere est celle du quai : le sens est donne par
   * station_exit, comme pour un plan prepare par OpexPrepareRailRoute. */
  return { anchor = platform.anchor, step = platform.step, length = platform.length,
           direction = ("direction" in platform) ? platform.direction : -1,
           station_exit = backExit, lead = backLead };
}

/* Un quai partage (autre ligne qui y rebrousse) casserait le sens unique. */
function OpexRailLoopPlatformsExclusive(owner, line)
{
  foreach (other in owner._lines) {
    if (other == null || other == line || !("mode" in other) || other.mode != "rail") continue;
    foreach (key in ["platformA", "platformB", "platformA2", "platformB2"]) {
      if (!(key in other) || other[key] == null || !("anchor" in other[key])) continue;
      local a = other[key].anchor;
      if (a == line.platformA.anchor || a == line.platformB.anchor) return false;
    }
  }
  return true;
}

/* Sens de circulation de la voie 1 impose par le depot primaire : la courbe
 * existante doit etre AMONT (entree d'entretien) ; la courbe de sortie aval
 * sera ajoutee a l'armement. flow=+1 : index croissant (A->B). */
function OpexRailLoopDepotFlow(route, depot, preferred = 0)
{
  if (depot == null || !AIRail.IsRailDepotTile(depot)) return null;
  local front = AIRail.GetRailDepotFrontTile(depot);
  local n = route.len();
  /* Le depot primaire (OpexBuildDepot) touche la gare : chercher sur toute la voie. */
  for (local k = 1; k < n - 1; k++) {
    if (route[k] != front) continue;
    /* Reprise apres Load : la courbe de sortie aval a pu deja etre posee,
     * les deux courbes existent ; garder le sens enregistre. */
    if (preferred != 0 && AIRail.AreTilesConnected(route[k - preferred], front, depot))
      return { index = k, flow = preferred };
    if (AIRail.AreTilesConnected(route[k - 1], front, depot)) return { index = k, flow = 1 };
    if (AIRail.AreTilesConnected(route[k + 1], front, depot)) return { index = k, flow = -1 };
    return null;
  }
  return null;
}

/* Un PBS_ONEWAY deja pose a contre-sens bloquerait la boucle. Les signaux
 * de bloc et les PBS ordinaires se franchissent par l'arriere : acceptes. */
function OpexRailLoopRouteAccepts(route, flow)
{
  local n = route.len();
  for (local i = 1; i < n - 1; i++) {
    local t = route[i];
    if (!AIRail.IsRailTile(t) || AIRail.IsRailStationTile(t)) continue;
    local against = flow > 0 ? route[i + 1] : route[i - 1];
    if (AIMap.DistanceManhattan(against, t) == 1
        && AIRail.GetSignalType(t, against) == AIRail.SIGNALTYPE_PBS_ONEWAY) return false;
  }
  return true;
}

/* Memes conditions qu'OpexV190Fix2PlaceSignal, sans rien poser. */
function OpexRailLoopSignalable(tiles, i)
{
  if (i <= 1 || i >= tiles.len() - 2) return false;
  local prev = tiles[i - 1];
  local t = tiles[i];
  local next = tiles[i + 1];
  return AIMap.DistanceManhattan(prev, t) == 1 && AIMap.DistanceManhattan(t, next) == 1
      && !AIBridge.IsBridgeTile(t) && !AITunnel.IsTunnelTile(t)
      && AIRail.IsRailTile(t) && !AIRail.IsRailStationTile(t)
      && OpexTileTrackCount(t) == 1 && AIRail.AreTilesConnected(prev, t, next)
      && AIRail.GetSignalType(t, prev) == AIRail.SIGNALTYPE_NONE
      && AIRail.GetSignalType(t, next) == AIRail.SIGNALTYPE_NONE;
}

/* Avant toute depense : la sortie aval du depot et le PBS de garde entre
 * la gare amont et le depot doivent etre posables. Le front du depot doit
 * etre droit (aucun virage a 90 deg cree par la courbe de sortie). */
function OpexRailLoopArmPrecheck(route, depot, k, flow)
{
  local n = route.len();
  local front = route[k];
  if (AIMap.DistanceManhattan(route[k - 1], front) != 1
      || AIMap.DistanceManhattan(front, route[k + 1]) != 1
      || front - route[k - 1] != route[k + 1] - front) return "depot_front_curve";
  local downstream = route[k + flow];
  if (!AIRail.AreTilesConnected(depot, front, downstream)) {
    local shield = AIAccounting();
    local test = AITestMode();
    if (!AIRail.BuildRail(depot, front, downstream)) return "depot_exit";
  }
  /* PBS de garde facultatif : un depot colle a la gare n'a pas de case libre ;
   * la sortie a contre-sens exigerait de franchir un PBS_ONEWAY par l'arriere. */
  return "";
}

function OpexRailLoopTrainPrice(vehicle)
{
  if (!AIVehicle.IsValidVehicle(vehicle)) return -1;
  local price = 0;
  for (local i = 0; i < AIVehicle.GetNumWagons(vehicle); i++) {
    local engine = AIVehicle.GetWagonEngineType(vehicle, i);
    if (!AIEngine.IsBuildable(engine)) return -1;
    price += AIEngine.GetPrice(engine);
  }
  return price;
}

function OpexRailLoopLiveVehicles(line)
{
  local live = [];
  if (!("vehicles" in line) || line.vehicles == null) return live;
  foreach (v in line.vehicles) if (AIVehicle.IsValidVehicle(v)) live.append(v);
  return live;
}

function OpexRailLoopProtected(line, route)
{
  local blocked = {};
  foreach (tile in route) blocked[tile] <- true;
  foreach (platform in [line.platformA, line.platformB]) {
    for (local i = 0; i < platform.length; i++) blocked[platform.anchor + i * platform.step] <- true;
    blocked[platform.lead] <- true;
  }
  if (AIRail.IsRailDepotTile(line.depot)) {
    blocked[line.depot] <- true;
    blocked[AIRail.GetRailDepotFrontTile(line.depot)] <- true;
  }
  return blocked;
}

/* --- Admission ------------------------------------------------------------ */

function OpexRailLoopEligible(line, now)
{
  return line != null && ("lineId" in line) && ("mode" in line) && line.mode == "rail"
      && ("kind" in line) && line.kind == "freight"
      && ("vehicles" in line) && line.vehicles != null && line.vehicles.len() == 1
      && ("trains" in line) && line.trains == 1
      && (!("doubleTrack" in line) || line.doubleTrack == 0)
      && !(("v271Tandem" in line) && line.v271Tandem)
      && !(("scrapping" in line) && line.scrapping)
      && ("platformA" in line) && line.platformA != null
      && ("platformB" in line) && line.platformB != null
      && ("stationA" in line) && ("stationB" in line) && ("cargo" in line)
      && ("depot" in line) && line.depot != null
      && ("buildDate" in line) && now - line.buildDate >= 180
      && ("lastProfit" in line) && line.lastProfit > 0
      && (!("railLoop" in line) || line.railLoop == 0
          || (line.railLoop < 0 && ("railLoopRetry" in line) && now >= line.railLoopRetry));
}

/* Demarre la recherche de la voie 2 pour une ligne admissible. Ne pose rien. */
function OpexRailLoopBegin(owner, line, route, waiting, capacity)
{
  local now = AIDate.GetCurrentDate();
  local reject = "";
  if (route == null || !OpexDoubleGrowVerifyRoute(route, line.platformA, line.platformB))
    reject = "primary_route";
  else if (!OpexRailLoopPlatformsExclusive(owner, line)) reject = "shared_platform";
  local flowInfo = reject == "" ? OpexRailLoopDepotFlow(route, line.depot) : null;
  if (reject == "" && flowInfo == null) reject = "depot_flow";
  if (reject == "" && !OpexRailLoopRouteAccepts(route, flowInfo.flow)) reject = "oneway_against_flow";
  local railType = AIRail.GetRailType(line.depot);
  local oldType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(railType);
  if (reject == "" && AIRail.GetCurrentRailType() != railType) reject = "rail_type";
  if (reject == "") {
    local pre = OpexRailLoopArmPrecheck(route, line.depot, flowInfo.index, flowInfo.flow);
    if (pre != "") reject = pre;
  }
  local backA = reject == "" ? OpexRailLoopBackPlan(line.platformA) : null;
  local backB = reject == "" ? OpexRailLoopBackPlan(line.platformB) : null;
  if (reject == "" && backA == null) reject = "back_lead_A";
  if (reject == "" && backB == null) reject = "back_lead_B";
  local finder = null;
  local srcBack = null;
  local goalBack = null;
  local blocked = null;
  if (reject == "") {
    /* flow=+1 : voie 1 A->B, la voie 2 part de l'arriere de B vers l'arriere de A. */
    srcBack = flowInfo.flow > 0 ? backB : backA;
    goalBack = flowInfo.flow > 0 ? backA : backB;
    blocked = OpexRailLoopProtected(line, route);
    local ignored = [];
    foreach (tile, mark in blocked) {
      /* Les deux sorties arriere sont source et but : ne pas les fermer. */
      if (tile != srcBack.station_exit && tile != goalBack.station_exit) ignored.append(tile);
    }
    finder = OpexCreateRailPathfinder([srcBack], [goalBack], ignored,
                                      OpexRailAstarWeight(line.distance));
    if (finder == null) reject = "pathfinder";
  }
  AIRail.SetCurrentRailType(oldType);
  if (reject != "") {
    line.rawset("railLoop", -1);
    line.rawset("railLoopRetry", now + RAIL_LOOP_RETRY_DAYS);
    owner._saveProjection = null;
    OpexRailLoopLog(line, "reject", "reason=" + reject + " waiting=" + waiting);
    return false;
  }
  owner._railLoopState = { phase = "search", line = line, route = route,
      flow = flowInfo.flow, depotIndex = flowInfo.index,
      srcBack = srcBack, goalBack = goalBack, blocked = blocked,
      railType = railType, pathfinder = finder, spent = 0,
      startDate = now, tiles2 = null, signals2 = 0 };
  line.rawset("railLoop", 1);
  owner._saveProjection = null;
  OpexRailLoopLog(line, "search", "flow=" + flowInfo.flow + " route=" + route.len()
      + " depot_index=" + flowInfo.index + " waiting=" + waiting + " capacity=" + capacity);
  return true;
}

/* Echec : jamais de demolition ici. Avant son raccordement, la voie 2 a deja
 * ete retiree par OpexRailLoopBuildTrack2 ; apres, une rame peut y rouler
 * (sens unique correct) et la demolir l'isolerait. Une voie 2 conservee sans
 * armement reste une voie de retour a sens unique, sure pour une rame. */
function OpexRailLoopFail(owner, line, reason, keptTrack2)
{
  owner._railLoopState = null;
  if (line != null) {
    line.rawset("railLoop", -1);
    /* Avec une voie 2 posee, l'arriere des quais n'est plus libre : ne pas
     * relancer une admission vouee a back_lead. */
    line.rawset("railLoopRetry", AIDate.GetCurrentDate()
        + (keptTrack2 ? 100 * RAIL_LOOP_RETRY_DAYS : RAIL_LOOP_RETRY_DAYS));
  }
  owner._saveProjection = null;
  OpexRailLoopLog(line, "fail", "reason=" + reason + " kept_track2=" + (keptTrack2 ? 1 : 0));
}

/* --- Voie 2 ---------------------------------------------------------------- */

function OpexRailLoopBuildIndex(tiles, structures, i)
{
  local prev = tiles[i - 1];
  local cur = tiles[i];
  local next = tiles[i + 1];
  if (AIMap.DistanceManhattan(prev, cur) > 1) return true;  // autre tete d'ouvrage
  if (AIMap.DistanceManhattan(cur, next) > 1) {
    local kind = OpexPlannedStructureKind(structures, cur, next);
    if (kind == "tunnel" || (kind == null && AITunnel.GetOtherTunnelEnd(cur) == next))
      return AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
    local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
    OpexBridgeSortBySpeed(bridges);
    return !bridges.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
  }
  return AIRail.BuildRail(prev, cur, next) && AIRail.AreTilesConnected(prev, cur, next);
}

function OpexRailLoopRollbackTrack2(tiles, blocked)
{
  local own = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  for (local i = tiles.len() - 2; i >= 1; i--) {
    local t = tiles[i];
    if ((t in blocked) || !AIMap.IsValidTile(t) || AITile.GetOwner(t) != own) continue;
    if (AIRail.IsRailStationTile(t) || AIRail.IsRailDepotTile(t)) continue;
    if (AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t))
      AITile.DemolishTile(t);
  }
  OpexAir0310InvalidateSiteValidity();
}

/* Pose des PBS_ONEWAY le long de `tiles` dans le sens `toward`, entre les
 * index lo et hi inclus, au plus un par fenetre de `spacing` cases. Une
 * fenetre sans case signalable (pont, aiguillage) allonge seulement le
 * canton : le sens unique reste garanti par les autres signaux. */
function OpexRailLoopSignalRun(tiles, lo, hi, toward, spacing, placed)
{
  local count = 0;
  if (toward > 0) {
    for (local k = lo; k <= hi; ) {
      local end = (k + spacing - 1 < hi) ? k + spacing - 1 : hi;
      local at = OpexV190Fix2PlaceSignalWindow(tiles, k, end, 1, 1, placed);
      if (at < 0) { k = end + 1; continue; }
      count++;
      k = at + spacing;
    }
  } else {
    for (local k = hi; k >= lo; ) {
      local end = (k - spacing + 1 > lo) ? k - spacing + 1 : lo;
      local at = OpexV190Fix2PlaceSignalWindow(tiles, k, end, -1, -1, placed);
      if (at < 0) { k = end - 1; continue; }
      count++;
      k = at - spacing;
    }
  }
  return count;
}

function OpexRailLoopSpacing(line)
{
  local trainTiles = ("platformLength" in line) ? line.platformLength : 3;
  return (trainTiles + 2 > RAIL_LOOP_MIN_SPACING) ? trainTiles + 2 : RAIL_LOOP_MIN_SPACING;
}

/* Fin de recherche : certification de la trace puis pose de la voie 2.
 * Ordre : cases interieures, PBS_ONEWAY, PUIS les deux raccords d'extremite.
 * La voie 2 n'est donc jamais accessible sans sa signalisation de sens. */
function OpexRailLoopBuildTrack2(owner, state, search)
{
  local line = state.line;
  local tiles = OpexResolveSearchTiles(search);
  local structures = OpexResolveSearchStructures(search);
  local n = tiles != null ? tiles.len() : 0;
  if (n < 12 || tiles[0] != state.srcBack.station_exit || tiles[1] != state.srcBack.lead
      || tiles[n - 2] != state.goalBack.lead || tiles[n - 1] != state.goalBack.station_exit)
    return "endpoints";
  /* Les deux raccords d'extremite sont des cases simples : un ouvrage qui
   * toucherait une gare la raccorderait avant la pose des PBS. */
  if (AIMap.DistanceManhattan(tiles[1], tiles[2]) != 1
      || AIMap.DistanceManhattan(tiles[n - 3], tiles[n - 2]) != 1) return "end_structure";
  if (!OpexJoinPathIsDedicated(tiles)) return "not_dedicated";
  for (local i = 1; i < n - 1; i++) if ((tiles[i] in state.blocked)) return "hits_primary";
  if (!OpexDoubleGrowTurnsSafe(tiles)) return "turn_90";
  local native = null;
  local trackCost = -1;
  {
    local account = AIAccounting();
    native = OpexTestRailTrack(tiles, structures);
    trackCost = account.GetCosts();
  }
  if (native == null || native.failed != 0) return "native_track";
  local live = OpexRailLoopLiveVehicles(line);
  local trainPrice = live.len() > 0 ? OpexRailLoopTrainPrice(live[0]) : -1;
  if (trainPrice < 0) return "train_price";
  if (OpexAvailableCapital() < trackCost + trainPrice) {
    OpexRailLoopLog(line, "cash", "track=" + trackCost + " train=" + trainPrice
        + " available=" + OpexAvailableCapital());
    return "cash";
  }
  OpexAir0310InvalidateSiteValidity();
  /* 1. Cases interieures 2..n-3 : deconnectees des deux gares. */
  for (local i = 2; i <= n - 3; i++) {
    if (!OpexRailLoopBuildIndex(tiles, structures, i)) {
      OpexRailLoopRollbackTrack2(tiles, state.blocked);
      return "build_interior";
    }
  }
  /* 2. Sens unique de la voie 2 : index croissant. */
  local placed = [];
  local spacing = OpexRailLoopSpacing(line);
  local count2 = OpexRailLoopSignalRun(tiles, 3, n - 4, 1, spacing, placed);
  if (count2 < 1) {
    OpexRailLoopRollbackTrack2(tiles, state.blocked);
    return "signals_track2";
  }
  /* 3. Raccords d'extremite, en dernier. */
  if (!OpexRailLoopBuildIndex(tiles, structures, 1)
      || !OpexRailLoopBuildIndex(tiles, structures, n - 2)
      || !OpexDoubleGrowVerifyRoute(tiles, state.srcBack, state.goalBack)) {
    OpexRailLoopRollbackTrack2(tiles, state.blocked);
    return "build_ends";
  }
  state.tiles2 = tiles;
  state.signals2 = count2;
  state.trackCost <- trackCost;
  /* Persistant : un Load au milieu de l'armement retrouve la voie 2. */
  line.rawset("railLoopTrack2", tiles);
  line.rawset("railLoopFlow", state.flow);
  line.rawset("railLoopPbs2", count2);
  owner._saveProjection = null;
  OpexRailLoopLog(line, "track2", "tiles=" + n + " pbs=" + count2 + " cost=" + trackCost);
  return "";
}

/* --- Armement de la voie 1 -------------------------------------------------- */

/* Toutes les rames doivent rouler vers la gare AVAL de la voie 1 : elles
 * parcourent alors la voie 1 dans le sens des futurs PBS_ONEWAY. */
function OpexRailLoopArmSafe(line, flow)
{
  local downstream = AIStation.GetStationID(flow > 0 ? line.stationB : line.stationA);
  local live = OpexRailLoopLiveVehicles(line);
  if (live.len() == 0) return false;
  foreach (v in live) {
    if (AIVehicle.IsStoppedInDepot(v)) return false;
    local dest = AIOrder.GetOrderDestination(v, AIOrder.ORDER_CURRENT);
    if (!AIMap.IsValidTile(dest) || AIStation.GetStationID(dest) != downstream) return false;
  }
  return true;
}

function OpexRailLoopArm(owner, state)
{
  local line = state.line;
  local route = state.route;
  local n = route.len();
  local k = state.depotIndex;
  local flow = state.flow;
  local depot = line.depot;
  local front = route[k];
  local downstreamTile = route[k + flow];
  /* Courbe de sortie aval du depot (l'entree amont existe deja). */
  local addedExit = false;
  if (!AIRail.AreTilesConnected(depot, front, downstreamTile)) {
    if (!AIRail.BuildRail(depot, front, downstreamTile)
        || !AIRail.AreTilesConnected(depot, front, downstreamTile)) return "depot_exit";
    addedExit = true;
  }
  local placed = [];
  local spacing = OpexRailLoopSpacing(line);
  /* Un PBS entre la gare amont et le depot interdit la sortie a contre-sens. */
  local guard = flow > 0
      ? OpexV190Fix2PlaceSignalWindow(route, k - 1, 2, -1, 1, placed)
      : OpexV190Fix2PlaceSignalWindow(route, k + 1, n - 3, 1, -1, placed);
  local count1 = -1;
  if (guard < 0) OpexDecide("RLOOP", "phase=guard_skip line=" + line.lineId + " k=" + k);
  {
    count1 = flow > 0
        ? OpexRailLoopSignalRun(route, k + 2, n - 3, 1, spacing, placed)
        : OpexRailLoopSignalRun(route, 2, k - 2, -1, spacing, placed);
  }
  if (count1 < 1) {
    OpexV190Fix2Rollback([], placed);
    if (addedExit) AIRail.RemoveRail(depot, front, downstreamTile);
    return "signals_track1";
  }
  state.signals1 <- count1 + (guard >= 0 ? 1 : 0);
  return "";
}

/* --- Flotte ----------------------------------------------------------------- */

function OpexRailLoopClone(owner, line)
{
  local live = OpexRailLoopLiveVehicles(line);
  if (live.len() == 0 || !AIRail.IsRailDepotTile(line.depot)
      || !OpexRailVehicleSlotAvailable()) return null;
  local model = live[0];
  local price = OpexRailLoopTrainPrice(model);
  if (price < 0 || OpexAvailableCapital() < price) return null;
  local train = AIVehicle.CloneVehicle(line.depot, model, true);
  if (!AIVehicle.IsValidVehicle(train)) return null;
  if (!AIVehicle.StartStopVehicle(train)) {
    AIVehicle.SellVehicle(train);
    return null;
  }
  line.vehicles.append(train);
  line.trains = line.vehicles.len();
  line.rawset("vehCount", line.vehicles.len());
  line.rawset("railLoopNextGrow", AIDate.GetCurrentDate() + RAIL_LOOP_GROW_DAYS);
  owner._saveProjection = null;
  return train;
}

function OpexRailLoopCommit(owner, state)
{
  local line = state.line;
  local blocks = state.signals1 + state.signals2 + 2;
  local cap = blocks - 2;
  if (cap > RAIL_LOOP_MAX_TRAINS) cap = RAIL_LOOP_MAX_TRAINS;
  if (cap < 2) cap = 2;
  line.rawset("railLoop", 2);
  line.rawset("railLoopBlocks", blocks);
  line.rawset("railLoopCap", cap);
  line.rawset("railLoopDate", AIDate.GetCurrentDate());
  owner._railLoopState = null;
  local train = OpexRailLoopClone(owner, line);
  owner._saveProjection = null;
  OpexRailLoopLog(line, "commit", "flow=" + state.flow + " pbs1=" + state.signals1
      + " pbs2=" + state.signals2 + " cap=" + cap
      + " second=" + (train != null ? train : -1));
}

/* Croissance d'une boucle certifiee : une rame si la cargaison attend une
 * rame pleine a la source, que la ligne gagne de l'argent et que le nombre
 * de cantons laisse au moins deux cantons libres. */
function OpexRailLoopGrow(owner, line, now)
{
  local cap = ("railLoopCap" in line) ? line.railLoopCap : 2;
  if (line.trains >= cap) return false;
  if (("railLoopNextGrow" in line) && now < line.railLoopNextGrow) return false;
  if (!("lastProfit" in line) || line.lastProfit <= 0) return false;
  local live = OpexRailLoopLiveVehicles(line);
  if (live.len() == 0) return false;
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)) return false;
  local capacity = AIVehicle.GetCapacity(live[0], line.cargo);
  local waiting = AIStation.GetCargoWaiting(station, line.cargo);
  if (capacity <= 0 || waiting < capacity) return false;
  local train = OpexRailLoopClone(owner, line);
  if (train == null) return false;
  OpexRailLoopLog(line, "grow", "waiting=" + waiting + " capacity=" + capacity
      + " cap=" + cap + " train=" + train);
  return true;
}

/* --- Points d'entree ---------------------------------------------------------- */

/* Appele en tete de _expandRailLines. true seulement si de l'argent a ete
 * depense (rame clonee) ; le demarrage d'une recherche ne consomme pas le
 * tour d'expansion. */
function OpexRailLoopSelect(owner, year)
{
  if (!RAIL_LOOP || !MODE_RAIL || owner == null || owner._lines == null
      || owner._catalog == null || owner._lines.len() == 0) return false;
  local now = AIDate.GetCurrentDate();
  local count = owner._lines.len();
  /* Reprise apres Load : une voie 2 posee mais non armee reprend en armement ;
   * une recherche perdue redevient admissible plus tard. */
  if (owner._railLoopState == null) {
    foreach (line in owner._lines) {
      if (line == null || !("railLoop" in line) || line.railLoop != 1) continue;
      local route = ("railLoopTrack2" in line) ? OpexDoubleGrowPrimaryRoute(line) : null;
      local flowInfo = (route != null && ("railLoopFlow" in line))
          ? OpexRailLoopDepotFlow(route, line.depot, line.railLoopFlow) : null;
      if (flowInfo != null && ("railLoopFlow" in line) && flowInfo.flow == line.railLoopFlow) {
        owner._railLoopState = { phase = "arm", line = line, route = route,
            flow = flowInfo.flow, depotIndex = flowInfo.index,
            blocked = OpexRailLoopProtected(line, route), railType = AIRail.GetRailType(line.depot),
            tiles2 = line.railLoopTrack2,
            signals2 = ("railLoopPbs2" in line) ? line.railLoopPbs2 : 1, startDate = now, pathfinder = null,
            spent = 0, srcBack = null, goalBack = null };
        OpexRailLoopLog(line, "resume", "phase=arm");
        break;
      }
      /* Recherche perdue : nouvel essai bientot. Voie 2 posee mais armement
       * impossible : elle reste une voie de retour sure, pas de nouvel essai. */
      line.rawset("railLoop", -1);
      line.rawset("railLoopRetry", now + (("railLoopTrack2" in line) ? 100 * RAIL_LOOP_RETRY_DAYS : 30));
      owner._saveProjection = null;
    }
  }
  /* Croissance des boucles certifiees d'abord. */
  foreach (line in owner._lines) {
    if (line == null || !("railLoop" in line) || line.railLoop != 2) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (OpexRailLoopGrow(owner, line, now)) return true;
  }
  if (owner._railLoopState != null) return false;
  local scan = count < 16 ? count : 16;
  for (local i = 0; i < scan; i++) {
    local line = owner._lines[(RAIL_LOOP_CURSOR + i) % count];
    if (!OpexRailLoopEligible(line, now)) continue;
    local station = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(station)) continue;
    local live = OpexRailLoopLiveVehicles(line);
    if (live.len() != 1) continue;
    local capacity = AIVehicle.GetCapacity(live[0], line.cargo);
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    if (capacity <= 0 || waiting < capacity) continue;
    /* Devis d'admission : voie 2 ~ 1,5 x la voie 1 + une rame. Un refus
     * reporte CETTE ligne et laisse le balayage continuer. */
    local route = OpexDoubleGrowPrimaryRoute(line);
    if (route == null) continue;
    local unit = AIRail.GetBuildCost(AIRail.GetRailType(line.depot), AIRail.BT_TRACK);
    local price = OpexRailLoopTrainPrice(live[0]);
    local quote = (unit > 0 && price >= 0) ? (route.len() * unit * 3) / 2 + price : -1;
    if (quote < 0 || OpexAvailableCapital() < quote) {
      line.rawset("railLoop", -1);
      line.rawset("railLoopRetry", now + 60);
      owner._saveProjection = null;
      OpexRailLoopLog(line, "defer", "reason=cash quote=" + quote
          + " available=" + OpexAvailableCapital());
      continue;
    }
    RAIL_LOOP_CURSOR = (RAIL_LOOP_CURSOR + i + 1) % count;
    OpexRailLoopBegin(owner, line, route, waiting, capacity);
    return false;
  }
  RAIL_LOOP_CURSOR = (RAIL_LOOP_CURSOR + scan) % count;
  return false;
}

/* Appele a chaque passe de l'ordonnanceur tant qu'un etat existe. Jamais
 * bloquant : une tranche A* bornee, ou un test d'armement, ou la pose. */
function OpexRailLoopStep(owner)
{
  local state = owner._railLoopState;
  if (state == null) return;
  local line = state.line;
  if (!RAIL_LOOP || line == null || !("railLoop" in line) || line.railLoop != 1
      || (("scrapping" in line) && line.scrapping)) {
    OpexRailLoopFail(owner, line, "line_changed", state.tiles2 != null);
    return;
  }
  local oldType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(state.railType);
  if (AIRail.GetCurrentRailType() != state.railType) {
    AIRail.SetCurrentRailType(oldType);
    OpexRailLoopFail(owner, line, "rail_type", state.tiles2 != null);
    return;
  }
  if (state.phase == "search") {
    local result = OpexAdvanceRailPathfinder(state.pathfinder, state.spent, RAIL_LOOP_BUDGET,
                                             AIController.GetTick() + 250, RAIL_LOOP_SLICE);
    state.spent = result.iterations;
    if (!result.done) {
      AIRail.SetCurrentRailType(oldType);
      return;
    }
    state.pathfinder = null;
    if (result.path == null || result.path == false) {
      AIRail.SetCurrentRailType(oldType);
      OpexRailLoopFail(owner, line, "astar_" + result.stop + " iters=" + state.spent, false);
      return;
    }
    /* La carte a pu changer pendant la recherche : revalider la voie 1. */
    if (!OpexDoubleGrowVerifyRoute(state.route, line.platformA, line.platformB)
        || OpexRailLoopLiveVehicles(line).len() != 1) {
      AIRail.SetCurrentRailType(oldType);
      OpexRailLoopFail(owner, line, "primary_changed", false);
      return;
    }
    local why = OpexRailLoopBuildTrack2(owner, state, result);
    AIRail.SetCurrentRailType(oldType);
    if (why != "") {
      OpexRailLoopFail(owner, line, why, false);
      return;
    }
    state.phase = "arm";
    state.startDate = AIDate.GetCurrentDate();
    return;
  }
  if (state.phase == "arm") {
    if (AIDate.GetCurrentDate() - state.startDate > RAIL_LOOP_ARM_DAYS) {
      AIRail.SetCurrentRailType(oldType);
      OpexRailLoopFail(owner, line, "arm_timeout", true);
      return;
    }
    if (!OpexRailLoopArmSafe(line, state.flow)) {
      AIRail.SetCurrentRailType(oldType);
      return;
    }
    local why = OpexRailLoopArm(owner, state);
    AIRail.SetCurrentRailType(oldType);
    if (why != "") {
      OpexRailLoopFail(owner, line, why, true);
      return;
    }
    OpexRailLoopCommit(owner, state);
    return;
  }
  AIRail.SetCurrentRailType(oldType);
}
