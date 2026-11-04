/* RAIL-NET (rail_net=1, defaut 0) : premier pas vers un reseau, strict opt-in.
 *
 * Une ligne fret NOUVELLE (source S, meme cargo, meme gare aval B) se greffe
 * sur une boucle RAIL-LOOP CERTIFIEE (railLoop == 2) au lieu de poser sa
 * propre ligne S->B :
 *   - embranchement 1 (fusion) : sortie AVANT du quai S -> case T1 de la voie
 *     chargee de l'hote (sens de marche vers B) ;
 *   - embranchement 2 (divergence) : case T2 de la voie vide de l'hote (sens
 *     B -> source de l'hote) -> sortie ARRIERE du quai S.
 * Les rames de S font donc S -> T1 -> B (dechargement) -> T2 -> S : un anneau
 * a sens unique qui partage avec l'hote le troncon T1->B->T2 et le quai B.
 *
 * Signalisation : PBS_ONEWAY sur les deux embranchements (OpexRailLoopSignalRun,
 * OpexV190Fix2PlaceSignal), jamais sur la case d'aiguillage (TracksOverlap).
 * Le premier signal apres la divergence est a >= longueur de rame + 2 cases.
 *
 * Fail closed : tout ce qui touche l'hote (les deux pieces d'aiguillage sur
 * T1/T2) est pose EN DERNIER, puis certifie ; un echec retire ces pieces, puis
 * les embranchements, le depot et le quai S. Un Load au milieu laisse au pire
 * des rails isoles, jamais un aiguillage vers un embranchement inacheve.
 * Sans certification, la paire reste au portefeuille ordinaire (ligne simple).
 *
 * Planificateur (etape 3) : greffe seulement si devis greffe <= RAIL_NET_COST_PCT %
 * du devis ligne simple S->B, capacite par canton suffisante (etape 2) et
 * plafonds anti-interblocage respectes. Une seule greffe par hote dans cette
 * etape. Etat transitoire owner._railNetState (non sauvegarde). */

RAIL_NET_CURSOR <- 0;
RAIL_NET_SLICE <- 200;        // iterations A* par passe
RAIL_NET_BUDGET <- 6000;      // iterations A* par embranchement
RAIL_NET_MAX_SPUR <- 40;      // distance Manhattan max source -> aiguillage
RAIL_NET_MIN_DIST <- 24;      // en dessous, une ligne simple est aussi courte
RAIL_NET_COST_PCT <- 80;      // greffe si devis <= 80 % du devis ligne simple
RAIL_NET_UTIL_PCT <- 70;      // occupation maximale du troncon partage
RAIL_NET_RETRY_DAYS <- 365;
RAIL_NET_SCAN_HOSTS <- 4;     // hotes examines par passe (borne d'opcodes)

function OpexRailNetLog(event, fields)
{
  if (!DECISION_LOG) return;
  OpexDecide("RNET", "phase=" + event + (fields != "" ? " " + fields : ""));
}

/* Une ligne greffee, ou un hote deja greffe, n'entre dans aucune autre
 * transformation (RAIL-LOOP, V284, Cas 1/2). Vrai seulement si le champ existe :
 * sans greffe, aucune ligne ne le porte. */
function OpexRailNetOwned(line)
{
  return line != null && ("railNetHost" in line);
}

/* --- Etape 2 : capacite par canton (fonctions pures) ------------------------ */

/* Passages par mois qu'un troncon a sens unique laisse passer : l'intervalle
 * minimal entre deux rames est le temps de liberer le canton le plus long plus
 * la longueur d'une rame. 0.036 x vitesse = cases/jour, meme convention que
 * OpexLineEconomics. */
function OpexRailNetPassesPerMonth(maxBlock, trainTiles, speed)
{
  if (maxBlock < 1 || trainTiles < 1 || speed <= 0) return 0.0;
  local tilesPerDay = 0.036 * speed;
  return 30.0 * tilesPerDay / (maxBlock + trainTiles);
}

/* Une rame repasse sur le troncon partage une fois par rotation. */
function OpexRailNetTrainPasses(roundTripDays)
{
  if (roundTripDays <= 0) return 0.0;
  return 30.0 / roundTripDays;
}

/* Anneau de N cantons : au plus N - 2 rames, comme OpexRailLoopCommit. Deux
 * cantons libres garantissent qu'une rame peut toujours avancer. */
function OpexRailNetCycleCap(cycleBlocks)
{
  local cap = cycleBlocks - 2;
  return cap > 0 ? cap : 0;
}

/* Une file d'attente de chargement complet ne doit jamais remonter jusqu'a
 * un aiguillage : rames d'une ligne <= cantons entre l'aiguillage et son quai
 * de chargement (+1 rame a quai). */
function OpexRailNetQueueFits(trains, blocksBeforePlatform)
{
  return trains <= blocksBeforePlatform + 1;
}

/* Longueurs de canton le long d'une voie parcourue dans l'ordre des index.
 * Un PBS_ONEWAY pose par OpexV190Fix2PlaceSignal(toward=1) regarde tiles[i-1]. */
function OpexRailNetBlocks(tiles)
{
  local blocks = [];
  local run = 0;
  for (local i = 1; i < tiles.len() - 1; i++) {
    run += AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
    if (AIRail.IsRailTile(tiles[i]) && AIMap.DistanceManhattan(tiles[i - 1], tiles[i]) == 1
        && AIRail.GetSignalType(tiles[i], tiles[i - 1]) != AIRail.SIGNALTYPE_NONE) {
      blocks.append(run);
      run = 0;
    }
  }
  blocks.append(run + 1);
  return blocks;
}

function OpexRailNetSignalsAfter(tiles, index)
{
  local n = 0;
  for (local i = index + 1; i < tiles.len() - 1; i++) {
    if (AIRail.IsRailTile(tiles[i]) && AIMap.DistanceManhattan(tiles[i - 1], tiles[i]) == 1
        && AIRail.GetSignalType(tiles[i], tiles[i - 1]) != AIRail.SIGNALTYPE_NONE) n++;
  }
  return n;
}

function OpexRailNetMax(values)
{
  local best = 0;
  foreach (v in values) if (v > best) best = v;
  return best;
}

/* --- Geometrie de l'hote ----------------------------------------------------- */

function OpexRailNetReverse(tiles)
{
  local out = [];
  for (local i = tiles.len() - 1; i >= 0; i--) out.append(tiles[i]);
  return out;
}

/* Voie chargee (vers la gare aval B) et voie vide (B -> source), dans l'ordre
 * de marche. flow > 0 : voie 1 de A vers B ; sinon la voie 2 porte le charge. */
function OpexRailNetTracks(host)
{
  if (!("railLoopTrack2" in host) || host.railLoopTrack2 == null
      || !("railLoopFlow" in host)) return null;
  local route = OpexDoubleGrowPrimaryRoute(host);
  if (route == null) return null;
  local track2 = host.railLoopTrack2;
  if (host.railLoopFlow > 0) return { loaded = route, empty = track2 };
  return { loaded = track2, empty = OpexRailNetReverse(route) };
}

/* Case d'aiguillage admissible : voie droite simple, sans signal, ni gare, ni
 * depot, ni ouvrage ; voisin lateral libre et plat. side = +1/-1 cote. */
function OpexRailNetJunctionTile(tiles, i, side)
{
  if (i < 1 || i + 1 >= tiles.len()) return null;
  local prev = tiles[i - 1];
  local cur = tiles[i];
  local next = tiles[i + 1];
  if (AIMap.DistanceManhattan(prev, cur) != 1 || AIMap.DistanceManhattan(cur, next) != 1) return null;
  if (cur - prev != next - cur) return null;
  if (!AIRail.IsRailTile(cur) || AIRail.IsRailStationTile(cur) || AIRail.IsRailDepotTile(cur)
      || AIBridge.IsBridgeTile(cur) || AITunnel.IsTunnelTile(cur)
      || OpexTileTrackCount(cur) != 1 || !AIRail.AreTilesConnected(prev, cur, next)) return null;
  if (AIRail.GetSignalType(cur, prev) != AIRail.SIGNALTYPE_NONE
      || AIRail.GetSignalType(cur, next) != AIRail.SIGNALTYPE_NONE) return null;
  local dir = next - cur;
  local perp = (dir == AIMap.GetTileIndex(1, 0) || dir == AIMap.GetTileIndex(-1, 0))
      ? AIMap.GetTileIndex(0, side) : AIMap.GetTileIndex(side, 0);
  local lead = cur + perp;
  if (!AIMap.IsValidTile(lead) || !AITile.IsBuildable(lead)
      || AITile.GetSlope(lead) != AITile.SLOPE_FLAT) return null;
  return { index = i, tile = cur, prev = prev, next = next, lead = lead, dir = dir };
}

/* Fusion : la plus proche de la source, a distance de securite des deux
 * extremites (une rame entiere de chaque cote). */
function OpexRailNetMergeSite(loaded, target, margin)
{
  local best = null;
  local bestDist = -1;
  for (local i = margin; i < loaded.len() - margin; i++) {
    foreach (side in [1, -1]) {
      local site = OpexRailNetJunctionTile(loaded, i, side);
      if (site == null) continue;
      local d = AIMap.DistanceManhattan(site.lead, target);
      if (best == null || d < bestDist) { best = site; bestDist = d; }
    }
  }
  return best;
}

/* Divergence : apres la gare B d'au moins `margin`, et avec assez de cantons
 * en aval pour que la file de chargement de l'hote ne l'atteigne jamais. */
function OpexRailNetDivergeSite(empty, target, margin, hostTrains)
{
  local best = null;
  local bestDist = -1;
  for (local i = margin; i < empty.len() - margin; i++) {
    if (!OpexRailNetQueueFits(hostTrains, OpexRailNetSignalsAfter(empty, i))) break;  // decroit avec i
    foreach (side in [1, -1]) {
      local site = OpexRailNetJunctionTile(empty, i, side);
      if (site == null) continue;
      local d = AIMap.DistanceManhattan(site.lead, target);
      if (best == null || d < bestDist) { best = site; bestDist = d; }
    }
  }
  return best;
}

/* Plan arriere d'un quai pas encore construit (meme convention que
 * OpexRailLoopBackPlan, sans exiger de gare posee). */
function OpexRailNetBackPlan(plan)
{
  local endFar = plan.station_exit != plan.anchor;
  local backExit = endFar ? plan.anchor : plan.anchor + plan.step * (plan.length - 1);
  local backLead = endFar ? backExit - plan.step : backExit + plan.step;
  if (!AIMap.IsValidTile(backLead) || !AITile.IsBuildable(backLead)
      || AITile.GetSlope(backLead) != AITile.SLOPE_FLAT) return null;
  return { anchor = plan.anchor, step = plan.step, length = plan.length,
           direction = plan.direction, station_exit = backExit, lead = backLead };
}

/* --- Etape 3 : planificateur ------------------------------------------------- */

function OpexRailNetHostTrains(owner, host)
{
  local n = host.trains;
  foreach (line in owner._lines)
    if (line != null && ("railNetHost" in line) && line.railNetHost == host.lineId) n += line.trains;
  return n;
}

function OpexRailNetHostEligible(owner, host)
{
  return host != null && ("railLoop" in host) && host.railLoop == 2
      && ("kind" in host) && host.kind == "freight" && ("mode" in host) && host.mode == "rail"
      && !(("scrapping" in host) && host.scrapping)
      && !("railNetFeeder" in host) && !("railNetHost" in host)
      && ("railLoopBlocks" in host) && ("loco" in host) && host.loco != null
      && ("wagons" in host) && ("platformLength" in host) && ("depot" in host)
      && AIRail.IsRailDepotTile(host.depot);
}

/* Source candidate : produit le cargo de l'hote, non desservie par nous,
 * assez loin de B pour qu'une ligne simple coute, assez pres du tronc. */
function OpexRailNetSources(owner, host, tracks)
{
  local out = [];
  local sink = host.stationB;
  local mid = tracks.loaded[tracks.loaded.len() / 2];
  local list = AIIndustryList_CargoProducing(host.cargo);
  for (local ind = list.Begin(); !list.IsEnd(); ind = list.Next()) {
    local tile = AIIndustry.GetLocation(ind);
    if (AIMap.DistanceManhattan(tile, sink) < RAIL_NET_MIN_DIST) continue;
    if (AIMap.DistanceManhattan(tile, mid) > RAIL_NET_MAX_SPUR * 2) continue;
    if (AIIndustry.GetLastMonthProduction(ind, host.cargo) <= 0) continue;
    /* Desservie par quiconque (nous ou un tiers) : pas de greffe. */
    if (AIIndustry.GetAmountOfStationsAround(ind) > 0) continue;
    local key = "i" + ind;
    if (("railNetTried" in host) && (key in host.railNetTried)
        && AIDate.GetCurrentDate() < host.railNetTried[key]) continue;
    local served = false;
    foreach (line in owner._lines) {
      if (line != null && ("originA" in line) && line.originA == tile) { served = true; break; }
    }
    if (served) continue;
    out.append({ industry = ind, tile = tile });
  }
  return out;
}

/* Devis : greffe (quai S, deux embranchements estimes a vol d'oiseau x 1,4,
 * depot, une rame) contre ligne simple S->B du modele economique commun. */
function OpexRailNetQuote(owner, host, source, merge, diverge, plan)
{
  local catalog = owner._catalog;
  local track = (catalog.costTrackPerTile * RAIL_TERRAIN_FACTOR) / 100;
  local spurTiles = (AIMap.DistanceManhattan(plan.lead, merge.lead)
      + AIMap.DistanceManhattan(diverge.lead, plan.lead)) * 14 / 10;
  local wagon = catalog.wagonByCargo[host.cargo];
  local train = host.loco.price + host.wagons * wagon.price;
  local connect = spurTiles * track + host.platformLength * catalog.costStation
      + catalog.costRailDepot + train;
  local monthly = AIIndustry.GetLastMonthProduction(source.industry, host.cargo);
  local plain = OpexLineEconomics(catalog, host.cargo,
      AIMap.DistanceManhattan(source.tile, host.stationB), monthly, "freight");
  local plainCost = (plain != null) ? plain.capital : -1;
  return { connect = connect, plain = plainCost, spurTiles = spurTiles, monthly = monthly,
           train = train };
}

/* Capacite du troncon partage (etape 2) et plafonds d'interblocage. */
function OpexRailNetCapacity(owner, host, tracks, extraTrains)
{
  local blocks = OpexRailNetBlocks(tracks.loaded);
  foreach (b in OpexRailNetBlocks(tracks.empty)) blocks.append(b);
  local maxBlock = OpexRailNetMax(blocks);
  local trainTiles = host.platformLength;
  local speed = ("effectiveSpeed" in host) ? host.effectiveSpeed : 0;
  local supply = OpexRailNetPassesPerMonth(maxBlock, trainTiles, speed);
  local hostTrains = OpexRailNetHostTrains(owner, host);
  local roundTrip = ("predOneWayDays" in host) ? 2.0 * host.predOneWayDays : 0.0;
  local demand = (hostTrains + extraTrains) * OpexRailNetTrainPasses(roundTrip);
  local cycleCap = OpexRailNetCycleCap(host.railLoopBlocks);
  return { maxBlock = maxBlock, supply = supply, demand = demand,
           trains = hostTrains + extraTrains, cycleCap = cycleCap,
           ok = supply > 0 && demand * 100 <= supply * RAIL_NET_UTIL_PCT
                && hostTrains + extraTrains <= cycleCap };
}

function OpexRailNetPlan(owner, host, tracks, source)
{
  local margin = host.platformLength + 2;
  local plans = OpexStationPlans(source.tile, host.stationB, 8, host.platformLength, 6,
      host.cargo, owner._catalog.railCoverage, true);
  foreach (plan in plans) {
    local back = OpexRailNetBackPlan(plan);
    if (back == null) continue;
    local merge = OpexRailNetMergeSite(tracks.loaded, plan.lead, margin);
    local diverge = OpexRailNetDivergeSite(tracks.empty, back.lead, margin, host.trains);
    if (merge == null || diverge == null) return { ok = false, reason = "no_junction" };
    if (AIMap.DistanceManhattan(merge.lead, plan.lead) > RAIL_NET_MAX_SPUR
        || AIMap.DistanceManhattan(diverge.lead, back.lead) > RAIL_NET_MAX_SPUR)
      return { ok = false, reason = "spur_far" };
    local quote = OpexRailNetQuote(owner, host, source, merge, diverge, plan);
    if (quote.plain <= 0 || quote.connect * 100 > quote.plain * RAIL_NET_COST_PCT)
      return { ok = false, reason = "plain_cheaper", quote = quote };
    local cap = OpexRailNetCapacity(owner, host, tracks, 1);
    if (!cap.ok) return { ok = false, reason = "capacity", quote = quote, cap = cap };
    return { ok = true, reason = "connect", plan = plan, back = back, merge = merge,
             diverge = diverge, quote = quote, cap = cap };
  }
  return { ok = false, reason = "no_site" };
}

function OpexRailNetRemember(host, industry, days)
{
  if (!("railNetTried" in host)) host.rawset("railNetTried", {});
  host.railNetTried.rawset("i" + industry, AIDate.GetCurrentDate() + days);
}

/* --- Recherche des embranchements ------------------------------------------ */

function OpexRailNetIgnored(tracks, plan, back, extra)
{
  local ignored = [];
  foreach (t in tracks.loaded) ignored.append(t);
  foreach (t in tracks.empty) ignored.append(t);
  for (local i = 0; i < plan.length; i++) ignored.append(plan.anchor + plan.step * i);
  foreach (t in extra) ignored.append(t);
  return ignored;
}

function OpexRailNetBegin(owner, host, tracks, source, decision)
{
  local railType = AIRail.GetRailType(host.depot);
  local merge = decision.merge;
  local diverge = decision.diverge;
  /* Interdits anti-coude-90 : arrivee sur le lead de fusion depuis l'avant,
   * sortie du lead de divergence vers l'arriere. */
  local mergeGoal = { lead = merge.lead, station_exit = merge.tile };
  local ignored = OpexRailNetIgnored(tracks, decision.plan, decision.back,
      [merge.lead + merge.dir, diverge.lead - diverge.dir]);
  local oldType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(railType);
  local finder = OpexCreateRailPathfinder([decision.plan], [mergeGoal], ignored,
      OpexRailAstarWeight(AIMap.DistanceManhattan(decision.plan.lead, merge.lead)));
  AIRail.SetCurrentRailType(oldType);
  if (finder == null) return false;
  owner._railNetState = { phase = "spur1", host = host, tracks = tracks, source = source,
      plan = decision.plan, back = decision.back, merge = merge, diverge = diverge,
      quote = decision.quote, railType = railType, pathfinder = finder, spent = 0,
      ignored = ignored, spur1 = null, structures1 = null, spur2 = null, structures2 = null,
      startDate = AIDate.GetCurrentDate() };
  OpexRailNetLog("begin", "host=" + host.lineId + " src=" + source.tile
      + " connect=" + decision.quote.connect + " plain=" + decision.quote.plain
      + " supply=" + decision.cap.supply + " demand=" + decision.cap.demand
      + " trains=" + decision.cap.trains + " cycle_cap=" + decision.cap.cycleCap);
  return true;
}

function OpexRailNetFail(owner, reason)
{
  local state = owner._railNetState;
  owner._railNetState = null;
  if (state == null) return;
  OpexRailNetRemember(state.host, state.source.industry, RAIL_NET_RETRY_DAYS);
  owner._saveProjection = null;
  OpexRailNetLog("fail", "host=" + state.host.lineId + " src=" + state.source.tile
      + " reason=" + reason);
}

/* --- Pose, certification, retour arriere ----------------------------------- */

/* Continuite d'un embranchement, ouvrages compris (meme regle que
 * OpexDoubleGrowVerifyRoute, sans exigence de quai aux deux bouts). */
function OpexRailNetVerifyPath(tiles)
{
  local own = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  for (local i = 1; i < tiles.len() - 1; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    if (!AIMap.IsValidTile(cur) || AITile.GetOwner(cur) != own) return false;
    local dPrev = AIMap.DistanceManhattan(prev, cur);
    local dNext = AIMap.DistanceManhattan(cur, next);
    if (dPrev > 1) {
      if (!(AIBridge.IsBridgeTile(cur) && AIBridge.GetOtherBridgeEnd(cur) == prev)
          && !(AITunnel.IsTunnelTile(cur) && AITunnel.GetOtherTunnelEnd(cur) == prev)) return false;
    } else if (dNext > 1) {
      if (!(AIBridge.IsBridgeTile(cur) && AIBridge.GetOtherBridgeEnd(cur) == next)
          && !(AITunnel.IsTunnelTile(cur) && AITunnel.GetOtherTunnelEnd(cur) == next)) return false;
    } else if (!AIRail.AreTilesConnected(prev, cur, next)) return false;
  }
  return true;
}

/* Coude en U (pf.forbid_90_deg) sur trois pas unitaires : t3 voisin de t0. */
function OpexRailNetHasNinety(tiles)
{
  for (local k = 0; k + 3 < tiles.len(); k++) {
    if (AIMap.DistanceManhattan(tiles[k], tiles[k + 3]) == 1
        && AIMap.DistanceManhattan(tiles[k], tiles[k + 1]) == 1
        && AIMap.DistanceManhattan(tiles[k + 1], tiles[k + 2]) == 1
        && AIMap.DistanceManhattan(tiles[k + 2], tiles[k + 3]) == 1) return true;
  }
  return false;
}

/* Retire tout ce que la greffe a pose ; ne touche jamais une case de l'hote
 * autrement qu'en retirant la seule piece d'aiguillage ajoutee. */
function OpexRailNetRollback(state, built)
{
  if (built.mergePiece) AIRail.RemoveRail(state.merge.lead, state.merge.tile, state.merge.next);
  if (built.divergePiece) AIRail.RemoveRail(state.diverge.prev, state.diverge.tile, state.diverge.lead);
  if (built.signals.len() > 0) OpexV190Fix2Rollback([], built.signals);
  local own = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  foreach (tiles in [state.spur1, state.spur2]) {
    if (tiles == null) continue;
    for (local i = 1; i < tiles.len() - 1; i++) {
      local t = tiles[i];
      if (t == state.merge.tile || t == state.diverge.tile) continue;
      if (!AIMap.IsValidTile(t) || AITile.GetOwner(t) != own) continue;
      if (AIRail.IsRailStationTile(t) || AIRail.IsRailDepotTile(t)) continue;
      if (AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t))
        AITile.DemolishTile(t);
    }
  }
  if (built.depot != null) AITile.DemolishTile(built.depot);
  if (built.station) {
    for (local i = 0; i < state.plan.length; i++) {
      local t = state.plan.anchor + state.plan.step * i;
      if (AIRail.IsRailStationTile(t)) AIRail.RemoveRailStationTileRectangle(t, t, false);
    }
  }
  OpexAir0310InvalidateSiteValidity();
}

/* Pose en un seul appel. Ordre : quai S, interieurs, depot, signaux, raccords
 * a S, puis SEULEMENT les deux pieces d'aiguillage sur l'hote, certifiees. */
function OpexRailNetBuild(owner, state)
{
  local host = state.host;
  local spur1 = state.spur1;
  local spur2 = state.spur2;
  local n1 = spur1.len();
  local n2 = spur2.len();
  local built = { station = false, depot = null, signals = [], mergePiece = false, divergePiece = false };
  if (n1 < 8 || n2 < 8) return { why = "short", built = built };
  /* La source a pu etre desservie entre-temps par le portefeuille. */
  foreach (line in owner._lines)
    if (line != null && ("originA" in line) && line.originA == state.source.tile)
      return { why = "served", built = built };
  if (AIIndustry.GetAmountOfStationsAround(state.source.industry) > 0)
    return { why = "served", built = built };
  /* Extremites simples : un ouvrage colle a un aiguillage ou au quai S
   * raccorderait avant la pose des PBS (meme regle que RAIL-LOOP). */
  if (AIMap.DistanceManhattan(spur1[1], spur1[2]) != 1
      || AIMap.DistanceManhattan(spur1[n1 - 3], spur1[n1 - 2]) != 1
      || AIMap.DistanceManhattan(spur2[1], spur2[2]) != 1
      || AIMap.DistanceManhattan(spur2[n2 - 3], spur2[n2 - 2]) != 1)
    return { why = "end_structure", built = built };
  if (OpexRailNetHasNinety([spur1[n1 - 3], spur1[n1 - 2], state.merge.tile, state.merge.next])
      || OpexRailNetHasNinety([state.diverge.prev, state.diverge.tile, spur2[1], spur2[2]])
      || OpexRailNetHasNinety(spur1) || OpexRailNetHasNinety(spur2))
    return { why = "turn_90", built = built };
  local cost = -1;
  {
    local account = AIAccounting();
    local test1 = OpexTestRailTrack(spur1, state.structures1);
    local test2 = OpexTestRailTrack(spur2, state.structures2);
    if (test1.failed != 0 || test2.failed != 0) return { why = "native_track", built = built };
    cost = account.GetCosts();
  }
  local need = cost + state.quote.train + host.platformLength * owner._catalog.costStation
      + owner._catalog.costRailDepot;
  if (OpexAvailableCapital() < need || !OpexRailVehicleSlotAvailable())
    return { why = "cash", built = built };
  OpexAir0310InvalidateSiteValidity();
  /* 1. Quai S, gare neuve. */
  for (local i = 0; i < state.plan.length; i++) AITile.DemolishTile(state.plan.anchor + state.plan.step * i);
  if (!AIRail.BuildRailStation(state.plan.anchor, state.plan.direction, 1, state.plan.length,
                               AIStation.STATION_NEW)) return { why = "station", built = built };
  built.station = true;
  /* 2. Interieurs des deux embranchements, raccordes a S mais PAS a l'hote. */
  for (local i = 1; i <= n1 - 3; i++)
    if (!OpexRailLoopBuildIndex(spur1, state.structures1, i)) return { why = "spur1", built = built };
  for (local i = 2; i <= n2 - 2; i++)
    if (!OpexRailLoopBuildIndex(spur2, state.structures2, i)) return { why = "spur2", built = built };
  /* 3. Depot de service sur l'embranchement 1, ouvert dans les deux sens. */
  local forbidden = {};
  forbidden[state.merge.lead] <- true;
  forbidden[state.diverge.lead] <- true;
  local depot = OpexBuildDepot(spur1, forbidden);
  if (depot == null) return { why = "depot", built = built };
  built.depot = depot;
  local front = AIRail.GetRailDepotFrontTile(depot);
  local k = -1;
  for (local i = 1; i < n1 - 1; i++) if (spur1[i] == front) { k = i; break; }
  if (k < 1 || k + 1 >= n1 - 2) return { why = "depot_index", built = built };
  if (!AIRail.AreTilesConnected(depot, front, spur1[k + 1])) {
    AIRail.BuildRail(depot, front, spur1[k + 1]);
    if (!AIRail.AreTilesConnected(depot, front, spur1[k + 1])) return { why = "depot_exit", built = built };
  }
  /* 4. Sens unique : apres le depot sur l'embranchement 1 ; apres une rame
   * entiere sur l'embranchement 2 (le canton d'aiguillage reste libre). */
  local spacing = OpexRailLoopSpacing(host);
  local s1 = OpexRailLoopSignalRun(spur1, k + 2, n1 - 3, 1, spacing, built.signals);
  local s2 = OpexRailLoopSignalRun(spur2, host.platformLength + 2, n2 - 4, 1, spacing, built.signals);
  if (s1 < 1 || s2 < 1) return { why = "signals", built = built };
  if (!OpexRailNetQueueFits(1, s2)) return { why = "queue", built = built };
  if (!OpexRailNetVerifyPath(spur1.slice(0, n1 - 2)) || !OpexRailNetVerifyPath(spur2.slice(1)))
    return { why = "spur_path", built = built };
  /* 5. Aiguillages sur l'hote, en dernier. */
  if (!OpexRailLoopBuildIndex(spur1, state.structures1, n1 - 2))
    return { why = "merge_lead", built = built };
  if (!AIRail.BuildRail(state.merge.lead, state.merge.tile, state.merge.next))
    return { why = "merge_piece", built = built };
  built.mergePiece = true;
  if (!AIRail.BuildRail(state.diverge.prev, state.diverge.tile, state.diverge.lead))
    return { why = "diverge_piece", built = built };
  built.divergePiece = true;
  if (!OpexRailLoopBuildIndex(spur2, state.structures2, 1)) return { why = "diverge_lead", built = built };
  /* 6. Certification : hote intact, aiguillages raccordes, anneau complet. */
  local ok = AIRail.AreTilesConnected(state.merge.prev, state.merge.tile, state.merge.next)
      && AIRail.AreTilesConnected(state.merge.lead, state.merge.tile, state.merge.next)
      && AIRail.AreTilesConnected(state.diverge.prev, state.diverge.tile, state.diverge.next)
      && AIRail.AreTilesConnected(state.diverge.prev, state.diverge.tile, state.diverge.lead)
      && OpexRailNetVerifyPath(spur1) && OpexRailNetVerifyPath(spur2);
  if (!ok) return { why = "certify", built = built };
  return { why = "", built = built, cost = cost, signals1 = s1, signals2 = s2, depot = depot };
}

/* Rame construite au depot de l'HOTE : sa sortie aval (armement RAIL-LOOP)
 * part dans le sens de marche ; ordres S (plein) puis B (dechargement). */
function OpexRailNetCommit(owner, state, res)
{
  local host = state.host;
  local trains = OpexBuildTrains(owner._catalog, host.cargo, "freight", host.depot,
      state.plan.station_exit, host.stationB, 1, host.loco, host.wagons,
      host.platformLength, false);
  if (trains.failed || trains.built == 0) {
    foreach (v in trains.rollbackVehicles) if (AIVehicle.IsValidVehicle(v)) AIVehicle.SellVehicle(v);
    return "train";
  }
  local train = trains.vehicles[0];
  local id = owner._nextLineId;
  owner._nextLineId++;
  local line = {
    lineId = id, mode = "rail", kind = "freight", cargo = host.cargo,
    originA = state.source.tile, originB = ("originB" in host) ? host.originB : -1,
    stationA = state.plan.station_exit, stationB = host.stationB,
    platformA = { anchor = state.plan.anchor, direction = state.plan.direction,
                  step = state.plan.step, length = state.plan.length,
                  station_exit = state.plan.station_exit, lead = state.plan.lead },
    platformB = host.platformB, depot = res.depot,
    vehicles = [train], trains = 1, trains0 = 1, vehCount = 1,
    wagons = host.wagons, loco = host.loco, platformLength = host.platformLength,
    distance = AIMap.DistanceManhattan(state.source.tile, host.stationB),
    year = AIDate.GetYear(AIDate.GetCurrentDate()), buildDate = AIDate.GetCurrentDate(),
    predicted = 0, predTrains = 1, doubleTrack = 0,
    effectiveSpeed = ("effectiveSpeed" in host) ? host.effectiveSpeed : 0,
    railNetHost = host.lineId, railNetMerge = state.merge.tile, railNetDiverge = state.diverge.tile,
    railNetSpur1 = state.spur1, railNetSpur2 = state.spur2,
    railNetPbs1 = res.signals1, railNetPbs2 = res.signals2, railNetCap = res.signals2
  };
  owner._lines.append(line);
  host.rawset("railNetFeeder", id);
  /* File de chargement de l'hote : cantons entre la divergence et son quai. */
  host.rawset("railNetQueueCap", OpexRailNetSignalsAfter(state.tracks.empty, state.diverge.index));
  if (!AIVehicle.StartStopVehicle(train)) {
    OpexRailNetLog("warn", "host=" + host.lineId + " feeder=" + id + " start=0");
  }
  owner._railNetState = null;
  owner._saveProjection = null;
  OpexRailNetLog("commit", "host=" + host.lineId + " feeder=" + id + " src=" + state.source.tile
      + " cost=" + res.cost + " pbs1=" + res.signals1 + " pbs2=" + res.signals2
      + " spur1=" + state.spur1.len() + " spur2=" + state.spur2.len() + " train=" + train);
  return "";
}

/* --- Croissance sous plafonds ------------------------------------------------ */

/* Hote : RAIL-LOOP ne clone plus si l'anneau partage est plein. */
function OpexRailNetHostMayGrow(owner, host)
{
  if (!("railNetFeeder" in host)) return true;
  local cap = ("railLoopCap" in host) ? host.railLoopCap : 2;
  local queue = ("railNetQueueCap" in host) ? host.railNetQueueCap : 0;
  return OpexRailNetHostTrains(owner, host) + 1 <= cap
      && OpexRailNetQueueFits(host.trains + 1, queue);
}

/* Greffe : une rame de plus si la source attend une rame pleine, la ligne
 * gagne, l'anneau partage a de la place et la file tient avant l'aiguillage. */
function OpexRailNetGrow(owner, line, now)
{
  local host = null;
  foreach (other in owner._lines)
    if (other != null && ("lineId" in other) && other.lineId == line.railNetHost) { host = other; break; }
  if (host == null || !OpexRailNetHostEligibleForGrowth(host)) return false;
  if (("railNetNextGrow" in line) && now < line.railNetNextGrow) return false;
  if (!("lastProfit" in line) || line.lastProfit <= 0) return false;
  if (!OpexRailNetQueueFits(line.trains + 1, ("railNetPbs2" in line) ? line.railNetPbs2 : 1)) return false;
  local cap = ("railLoopCap" in host) ? host.railLoopCap : 2;
  if (OpexRailNetHostTrains(owner, host) + 1 > cap) return false;
  local live = OpexRailLoopLiveVehicles(line);
  if (live.len() == 0) return false;
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)) return false;
  local capacity = AIVehicle.GetCapacity(live[0], line.cargo);
  if (capacity <= 0 || AIStation.GetCargoWaiting(station, line.cargo) < capacity) return false;
  local price = OpexRailLoopTrainPrice(live[0]);
  if (price < 0 || OpexAvailableCapital() < price || !OpexRailVehicleSlotAvailable()) return false;
  local train = AIVehicle.CloneVehicle(host.depot, live[0], true);
  if (!AIVehicle.IsValidVehicle(train)) return false;
  if (!AIVehicle.StartStopVehicle(train)) { AIVehicle.SellVehicle(train); return false; }
  line.vehicles.append(train);
  line.trains = line.vehicles.len();
  line.rawset("vehCount", line.vehicles.len());
  line.rawset("railNetNextGrow", now + RAIL_LOOP_GROW_DAYS);
  owner._saveProjection = null;
  OpexRailNetLog("grow", "feeder=" + line.lineId + " trains=" + line.trains + " cap=" + cap);
  return true;
}

function OpexRailNetHostEligibleForGrowth(host)
{
  return ("railLoop" in host) && host.railLoop == 2 && !(("scrapping" in host) && host.scrapping)
      && AIRail.IsRailDepotTile(host.depot);
}

/* Sonde de banc (decision_log seulement) : rames a l'arret hors gare et hors
 * depot (attente a un signal), rames accidentees, sur la greffe et son hote.
 * Une valeur non nulle sur deux releves consecutifs signale un blocage. */
function OpexRailNetWatch(owner, line, now)
{
  if (!DECISION_LOG) return;
  if (("railNetWatchDate" in line) && now - line.railNetWatchDate < 30) return;
  line.rawset("railNetWatchDate", now);
  local host = null;
  foreach (other in owner._lines)
    if (other != null && ("lineId" in other) && other.lineId == line.railNetHost) { host = other; break; }
  local counts = [0, 0, 0, 0];   // greffe : arretees, accidentees ; hote : idem
  foreach (pair in [[line, 0], [host, 2]]) {
    local l = pair[0];
    if (l == null || !("vehicles" in l)) continue;
    foreach (v in l.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      local st = AIVehicle.GetState(v);
      if (st == AIVehicle.VS_CRASHED) counts[pair[1] + 1]++;
      else if (st == AIVehicle.VS_RUNNING && AIVehicle.GetCurrentSpeed(v) == 0) counts[pair[1]]++;
    }
  }
  OpexRailNetLog("watch", "feeder=" + line.lineId + " host=" + line.railNetHost
      + " feeder_trains=" + line.trains + " feeder_stopped=" + counts[0] + " feeder_crashed=" + counts[1]
      + " host_trains=" + (host != null ? host.trains : -1) + " host_stopped=" + counts[2]
      + " host_crashed=" + counts[3]);
}

/* --- Points d'entree --------------------------------------------------------- */

/* Appele en tete de _expandRailLines apres RAIL-LOOP. true seulement si de
 * l'argent a ete depense (rame clonee). */
function OpexRailNetSelect(owner, year)
{
  local now = AIDate.GetCurrentDate();
  foreach (line in owner._lines) {
    if (line == null || !("railNetHost" in line) || (("scrapping" in line) && line.scrapping)) continue;
    OpexRailNetWatch(owner, line, now);
    if (OpexRailNetGrow(owner, line, now)) return true;
  }
  if (owner._railNetState != null || owner._railLoopState != null) return false;
  local count = owner._lines.len();
  if (count == 0) return false;
  local scanned = 0;
  for (local i = 0; i < count && scanned < RAIL_NET_SCAN_HOSTS; i++) {
    local host = owner._lines[(RAIL_NET_CURSOR + i) % count];
    if (!OpexRailNetHostEligible(owner, host)) continue;
    scanned++;
    local tracks = OpexRailNetTracks(host);
    if (tracks == null) continue;
    foreach (source in OpexRailNetSources(owner, host, tracks)) {
      local decision = OpexRailNetPlan(owner, host, tracks, source);
      OpexRailNetLog("plan", "host=" + host.lineId + " src=" + source.tile
          + " choice=" + decision.reason
          + (("quote" in decision) ? " connect=" + decision.quote.connect
              + " plain=" + decision.quote.plain : ""));
      if (!decision.ok) {
        OpexRailNetRemember(host, source.industry, RAIL_NET_RETRY_DAYS);
        continue;
      }
      RAIL_NET_CURSOR = (RAIL_NET_CURSOR + i + 1) % count;
      if (!OpexRailNetBegin(owner, host, tracks, source, decision))
        OpexRailNetRemember(host, source.industry, RAIL_NET_RETRY_DAYS);
      return false;
    }
  }
  RAIL_NET_CURSOR = (RAIL_NET_CURSOR + RAIL_NET_SCAN_HOSTS) % count;
  return false;
}

/* Une tranche bornee par passe de l'ordonnanceur. */
function OpexRailNetStep(owner)
{
  local state = owner._railNetState;
  if (state == null) return;
  if (!RAIL_NET || !OpexRailNetHostEligibleForGrowth(state.host)) {
    OpexRailNetFail(owner, "host_changed");
    return;
  }
  local oldType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(state.railType);
  if (AIRail.GetCurrentRailType() != state.railType) {
    AIRail.SetCurrentRailType(oldType);
    OpexRailNetFail(owner, "rail_type");
    return;
  }
  local result = OpexAdvanceRailPathfinder(state.pathfinder, state.spent, RAIL_NET_BUDGET,
                                           AIController.GetTick() + 250, RAIL_NET_SLICE);
  state.spent = result.iterations;
  if (!result.done) { AIRail.SetCurrentRailType(oldType); return; }
  state.pathfinder = null;
  if (result.path == null || result.path == false) {
    AIRail.SetCurrentRailType(oldType);
    OpexRailNetFail(owner, state.phase + "_" + result.stop);
    return;
  }
  local tiles = OpexResolveSearchTiles(result);
  local structures = OpexResolveSearchStructures(result);
  if (state.phase == "spur1") {
    state.spur1 = tiles;
    state.structures1 = structures;
    local ignored = [];
    foreach (t in state.ignored) ignored.append(t);
    foreach (t in tiles) ignored.append(t);
    local divergeSource = { lead = state.diverge.lead, station_exit = state.diverge.tile };
    state.pathfinder = OpexCreateRailPathfinder([divergeSource], [state.back], ignored,
        OpexRailAstarWeight(AIMap.DistanceManhattan(state.diverge.lead, state.back.lead)));
    state.spent = 0;
    state.phase = "spur2";
    AIRail.SetCurrentRailType(oldType);
    if (state.pathfinder == null) OpexRailNetFail(owner, "spur2_finder");
    return;
  }
  state.spur2 = tiles;
  state.structures2 = structures;
  local res = OpexRailNetBuild(owner, state);
  if (res.why != "") {
    OpexRailNetRollback(state, res.built);
    AIRail.SetCurrentRailType(oldType);
    OpexRailNetFail(owner, res.why);
    return;
  }
  local why = OpexRailNetCommit(owner, state, res);
  AIRail.SetCurrentRailType(oldType);
  if (why != "") {
    OpexRailNetRollback(state, res.built);
    OpexRailNetFail(owner, why);
  }
}
