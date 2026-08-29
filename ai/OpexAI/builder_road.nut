/* Lignes routieres : bus ville<->ville, et camions industrie->industrie / industrie->ville.
 *
 * Le trace n'utilise PAS Pathfinder.Road. Sur la graine gelee, l'A* de la bibliotheque a coute
 * 696 794 opcodes pour 500 iterations sur la paire la plus proche (20 tuiles), alors qu'un essai
 * de trace Manhattan coute 121 opcodes. Ici, on echantillonne des sites d'arret dans le rayon de
 * l'extremite, puis on accepte seulement l'un des deux L que BuildRoad valide sous AITestMode.
 * C'est borne, assez court pour le creneau que le rail refuse, et chaque arete reelle est
 * revalidee.
 *
 * ⚠️ PISTES DEJA ECARTEES PAR LA MESURE, ne pas les reproposer (docs/opexai_mode_route) :
 *   - Pathfinder.Road : 696 794 opcodes contre 171 356 pour le trace Manhattan borne ;
 *   - arrets traversants (BuildDriveThroughRoadStation) : 912 232 opcodes, aucun gain, et un arret
 *     en echec deux annees de suite. C'est cette disposition en cul-de-sac qui impose d'ecarter les
 *     vehicules articules au catalogue ;
 *   - distance du depot aux arrets, testee de 1 a 4 tuiles : la variable pertinente etait la
 *     CONNEXITE, pas la distance.
 *
 * Historique (2026-08-29) : la v1 ne savait construire qu'UNE liaison passagers, choisie en
 * balayant toutes les paires de villes de la carte. Elle est devenue un constructeur par candidat
 * -- le classement vit dans candidates.nut (OpexBuildRoadCandidates), ce fichier ne fait plus que
 * planifier et batir la paire qu'on lui donne.
 */

const ROAD_MAX_TRACE_TILES = 32;
/* Rayon de recherche d'un site d'arret. Une ville s'etale, donc on cherche loin de son centre
 * administratif ; une industrie occupe quelques tuiles et l'arret doit de toute facon tomber dans
 * son rayon de couverture, donc chercher au-dela serait payer des sondes pour rien. */
const ROAD_TOWN_SEARCH_RADIUS = 16;
const ROAD_INDUSTRY_SEARCH_RADIUS = 5;
const ROAD_MAX_SITE_PROBES = 48;
const ROAD_MAX_SITES_PER_END = 4;
/* Chaque essai revalide jusqu'a ROAD_MAX_TRACE_TILES aretes sous AITestMode : sans ce plafond, un
 * plan pourrait consommer 4 x 4 x 2 = 32 essais, soit un millier de commandes de test pour une
 * seule paire -- exactement le genre de depense que l'etage 2 est cense empecher. */
const ROAD_MAX_TRACE_TRIALS = 12;
const ROAD_CAPITAL_MARGIN = 25000;
const ROAD_DEPOT_MIN_STOP_DISTANCE = 3;

function OpexRoadInMap(x, y)
{
  return x >= 0 && y >= 0 && x < AIMap.GetMapSizeX() && y < AIMap.GetMapSizeY();
}

/* 🔴 MESURE DU 2026-08-29, campagne 6 ans graine 42 : 21 tentatives routieres, 21 echecs, dont une
 * moitie en ERR_LAND_SLOPED_WRONG (264) sur la pose du trace lui-meme.
 *
 * Cause : AITestMode valide chaque arete ISOLEMENT, sur la carte telle qu'elle est AVANT que nous
 * n'ayons rien pose. Or une tuile qui recoit des bits de route sur DEUX axes -- le coin du L, la
 * facade d'un arret (bit du trace + bit vers l'arret), la facade du depot (idem) -- n'est
 * constructible en deux axes que si elle est PLATE. Sur une pente, le jeu pose une fondation pour
 * un axe et refuse l'autre. Chaque arete passait donc son test isole, et la pose reelle echouait
 * des que la deuxieme direction arrivait sur la meme tuile.
 *
 * Exiger la platitude sur ces seules tuiles est volontairement conservateur : une longue portion
 * droite en pente reste acceptee (elle ne porte qu'un axe), seuls les points de jonction sont
 * contraints. Le cout d'un faux negatif est un candidat perdu ; celui d'un faux positif est une
 * transaction batie a moitie puis annulee, argent et opcodes compris. */
function OpexRoadIsFlat(tile)
{
  return AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
}

/* Le type d'arret est impose par le CARGO, jamais choisi : docs/mecanique_jeu.md S11, "les bus ont
 * besoin d'arrets de bus, pas d'aires de chargement", et l'inverse pour les camions. Un bus ne
 * chargera JAMAIS sur une aire de chargement -- l'erreur serait silencieuse (arret bati, note a
 * -1, aucun ramassage), soit exactement le mode d'echec qui a coute trois passes de diagnostic a
 * la v1. */
function OpexRoadStopKind(cargo)
{
  if (AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS)) {
    return { vehType = AIRoad.ROADVEHTYPE_BUS, stationType = AIStation.STATION_BUS_STOP };
  }
  return { vehType = AIRoad.ROADVEHTYPE_TRUCK, stationType = AIStation.STATION_TRUCK_STOP };
}

function OpexRoadAppendSegment(trace, from, to)
{
  local x = AIMap.GetTileX(from);
  local y = AIMap.GetTileY(from);
  local tx = AIMap.GetTileX(to);
  local ty = AIMap.GetTileY(to);
  while (x != tx) {
    local nx = x + (x < tx ? 1 : -1);
    local next = AIMap.GetTileIndex(nx, y);
    trace.append({ from = AIMap.GetTileIndex(x, y), to = next });
    x = nx;
  }
  while (y != ty) {
    local ny = y + (y < ty ? 1 : -1);
    local next = AIMap.GetTileIndex(x, ny);
    trace.append({ from = AIMap.GetTileIndex(x, y), to = next });
    y = ny;
  }
}

function OpexRoadTrace(from, to, firstHorizontal)
{
  local corner = firstHorizontal
    ? AIMap.GetTileIndex(AIMap.GetTileX(to), AIMap.GetTileY(from))
    : AIMap.GetTileIndex(AIMap.GetTileX(from), AIMap.GetTileY(to));
  /* Le coin est la seule tuile du L a porter les deux axes ; sur une pente le second est refuse
   * (cf. OpexRoadIsFlat). Un trace parfaitement droit n'a pas de coin -- corner y vaut alors l'une
   * des deux extremites, dont la platitude est deja exigee comme facade d'arret. */
  if (corner != from && corner != to && !OpexRoadIsFlat(corner)) return [];
  local out = [];
  OpexRoadAppendSegment(out, from, corner);
  OpexRoadAppendSegment(out, corner, to);
  return out;
}

/* Un retour positif de BuildRoad n'est jamais une preuve : le predicat est la connectivite.
 * AITestMode ne modifie pas la carte, donc chaque arete est evaluee independamment. C'est
 * suffisant pour un L : une arete n'a pas besoin qu'une autre ait ete posee auparavant. */
function OpexRoadTraceBuildable(trace)
{
  foreach (edge in trace) {
    if (AIRoad.AreRoadTilesConnected(edge.from, edge.to)) continue;
    local buildable = false;
    { local test = AITestMode(); buildable = AIRoad.BuildRoad(edge.from, edge.to); }
    if (!buildable) return false;
  }
  return true;
}

/* Sites d'arret candidats autour d'une extremite, testes AVANT toute mutation.
 *
 * Etre proche du centre administratif ne prouve pas qu'une maison se trouve dans le bassin : la
 * premiere sonde de la v1 construisait deux arrets a note -1. GetCargoProduction (ou
 * GetCargoAcceptance a l'arrivee d'une ligne de fret) sur l'empreinte exacte de l'arret elimine
 * ces faux sites avant un seul cout.
 *
 * `townId >= 0` contraint la recherche a rester dans la ville visee ; une extremite industrielle
 * passe -1, la contrainte n'ayant alors aucun sens (une industrie appartient a la ville la plus
 * proche, qui peut etre celle de l'autre extremite).
 *
 * ⚠️ La v1 exigeait que la facade soit DEJA une tuile de route, pour ancrer l'arret sur la voirie
 * municipale. Cette exigence est levee (2026-08-29) : elle rendait toute industrie non desservie
 * par une route inatteignable, c'est-a-dire la majorite d'entre elles, et le fret est precisement
 * l'objet de cette generalisation. Le trace que nous batissons relie les deux facades, donc la
 * facade n'a pas besoin de preexister -- BuildRoad(front, tile) sous AITestMode prouve deja
 * qu'elle est constructible. La preference pour une facade deja routiere reste, mais comme un
 * BONUS de classement (moins de tuiles a payer, aucune demolition), plus comme un filtre. */
function OpexRoadSites(center, townId, cargo, vehType, coverage, wantProduction, radius)
{
  local out = [];
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local probes = 0;
  for (local r = 0; r <= radius && probes < ROAD_MAX_SITE_PROBES; r++) {
    for (local dx = -r; dx <= r && probes < ROAD_MAX_SITE_PROBES; dx++) {
      for (local dy = -r; dy <= r && probes < ROAD_MAX_SITE_PROBES; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local x = cx + dx;
        local y = cy + dy;
        if (!OpexRoadInMap(x, y)) continue;
        local tile = AIMap.GetTileIndex(x, y);
        if (townId >= 0 && AITile.GetClosestTown(tile) != townId) continue;
        local value = wantProduction
            ? AITile.GetCargoProduction(tile, cargo, 1, 1, coverage)
            : AITile.GetCargoAcceptance(tile, cargo, 1, 1, coverage);
        if (wantProduction ? (value <= 0) : (value < ROAD_ACCEPTANCE_MIN)) continue;
        foreach (offset in offsets) {
          if (probes >= ROAD_MAX_SITE_PROBES) break;
          local fx = x + offset[0];
          local fy = y + offset[1];
          if (!OpexRoadInMap(fx, fy)) continue;
          local front = AIMap.GetTileIndex(fx, fy);
          /* La facade portera DEUX axes de route : celui du trace et le raccord vers l'arret. Elle
           * doit donc etre plate -- cf. OpexRoadIsFlat. */
          if (!OpexRoadIsFlat(front)) continue;
          /* Bug jumeau de celui du depot (2026-08-28, cf. commentaire sur OpexRoadFindDepot) :
           * CmdBuildRoadStop ne construit/verifie rien sur "front" non plus (station_cmd.cpp,
           * CheckFlatLandRoadStop ne regarde QUE la tuile de l'arret). Rien ne garantit que la
           * facade porte deja le bit tourne vers l'arret. On teste donc aussi BuildRoad(front,
           * tile) : c'est le raccord que OpexBuildRoadRoute devra poser pour de vrai avant de
           * batir l'arret. */
          local ok = false;
          { local test = AITestMode();
            ok = AIRoad.BuildRoad(front, tile) &&
                 AIRoad.BuildRoadStation(tile, front, vehType, AIStation.STATION_NEW); }
          probes++;
          if (!ok) continue;
          local onRoad = AIRoad.IsRoadTile(front);
          /* Le bonus de facade routiere n'est qu'un departage : il ne doit jamais faire passer un
           * site deux fois moins productif devant un autre, d'ou le facteur 2 sur la valeur. */
          local site = { tile = tile, front = front, value = value,
                         score = value * 2 + (onRoad ? 1 : 0) };
          local pos = out.len();
          while (pos > 0 && out[pos - 1].score < site.score) pos--;
          out.insert(pos, site);
          if (out.len() > ROAD_MAX_SITES_PER_END) out.pop();
        }
      }
    }
  }
  return out;
}

function OpexRoadIsForbidden(tile, stopA, stopB)
{
  return tile == stopA.tile || tile == stopB.tile;
}

/* Bug mesure le 2026-08-28 (docs/opex_bus_diag_*.json, signs RT/RL/RQ) : sur la paire 27<->33,
 * siteA.front == (54,27), siteA.tile == (55,27), et le trace horizontal siteA.front -> corner
 * (56,27) marche PRECISEMENT sur siteA.tile au passage. AITestMode/BuildRoad valident cette case
 * comme route plate ordinaire (rien n'y est encore construit), mais BuildRoadStation la remplace
 * ensuite par un arret NON traversant (cul-de-sac, entree/sortie par la seule facade) -- la
 * continuite du trace vers l'autre arret est donc coupee exactement au point le plus critique.
 * Mesure : le bus ne depasse jamais l'ordre 0 (rating -1 4 ans durant, RW=0, jamais AT_STATION).
 * Le filet : aucune tuile du trace (hors les deux facades, qui sont TOUJOURS des tuiles OK) ne
 * doit coincider avec le corps d'un des deux arrets. */
function OpexRoadTraceHitsStop(trace, stopTile)
{
  foreach (edge in trace) {
    if (edge.from == stopTile || edge.to == stopTile) return true;
  }
  return false;
}

/* Le depot est decide sur le L planifie mais pose apres lui. Il n'est pas construit dans une
 * boucle de gare : deux arrets simples suffisent a l'increment, la boucle est une amelioration de
 * capacite a mesurer plus tard, pas un pretexte a ajouter des stations.
 *
 * Bug racine du bus fige (2026-08-28, prouve dans le source du jeu, road_cmd.cpp:1151 /
 * script_road.cpp:524) : CmdBuildRoadDepot ne construit QUE sur sa propre tuile ; il ne touche
 * jamais "front". AIRoad.BuildRoadDepot(tile, front) se contente de calculer une DiagDirection a
 * partir de la geometrie tile/front et de la passer a cette commande -- "front" ne recoit donc
 * JAMAIS le bit de route perpendiculaire dont le depot a besoin, sauf si quelque chose d'autre l'a
 * deja construit. Comme "front" est ici toujours l'interieur d'un segment DROIT du trace, seuls
 * les deux bits dans l'axe du trace y existent (poses par OpexRoadBuildTrace) -- jamais le bit
 * perpendiculaire vers le depot. D'ou la mesure : bus fige EXACTEMENT sur la tuile du depot (RL),
 * vitesse qui oscille sans jamais avancer (RV/RQ) -- il ne peut litteralement pas monter sur
 * "front", quel que soit le nombre d'annees. Chaque site candidat doit donc AUSSI poser ce bit
 * manquant avec BuildRoad(front, tile) avant BuildRoadDepot -- cf. OpexBuildRoadRoute. */
function OpexRoadFindDepot(trace, stopA, stopB)
{
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local seen = {};
  /* 🔴 MESURE DU 2026-08-29 (meme campagne) : l'autre moitie des 21 echecs etait un DEPOT en
   * ERR_AREA_NOT_CLEAR (260), c'est-a-dire "il faut d'abord enlever la route". La cause est la
   * meme dissymetrie plan/pose que ci-dessus, sous un autre angle : les quatre voisins d'une
   * facade sont testes sur la carte AVANT la pose du trace, et deux d'entre eux -- ceux dans
   * l'axe -- SONT le trace. Vides et constructibles au test, ils portent une route au moment de
   * batir le depot. La v1 ne s'en apercevait pas : elle ne faisait qu'UNE tentative par partie, et
   * un echec s'y lisait comme "pas de site", pas comme un bug.
   *
   * Le trace est indexe une fois ici plutot que parcouru pour chaque candidat : la recherche
   * examine jusqu'a quatre voisins de chacune de ses ~25 tuiles. */
  local onTrace = {};
  foreach (edge in trace) {
    if (!(edge.from in onTrace)) onTrace.rawset(edge.from, true);
    if (!(edge.to in onTrace)) onTrace.rawset(edge.to, true);
  }
  /* Experience du 2026-08-28 (cf. docs/opex_bus_diag_*.json) : chercher a partir de la fin du trace
   * (cote siteB) plutot que du debut echoue purement et simplement (DEPOT, aucun site
   * constructible sur toute cette moitie) -- le terrain degage n'existe qu'aux abords immediats
   * des arrets, pas au milieu du trace. Le depot doit donc rester cherche depuis le debut. */
  foreach (edge in trace) {
    local fronts = [edge.from, edge.to];
    foreach (front in fronts) {
      if (front in seen) continue;
      seen.rawset(front, true);
      /* Mesure du 2026-08-28 : meme apres avoir evite que le trace ne traverse le CORPS d'un
       * arret (OpexRoadTraceHitsStop), la premiere facade du trace est TOUJOURS siteA.front (le
       * trace commence toujours la), donc sans ce filet le depot s'y accroche systematiquement --
       * meme facade que l'arret, puis a 1 seule tuile d'elle une fois ce cas exclu. Le bus ne
       * chargeait toujours rien apres 4 ans dans les deux configurations (rating -1, RW=0
       * constant, ordre bloque sur stopA, campagne graine 42 -- docs/opex_bus_diag_*.json). Le
       * trace a 24 tuiles de facades candidates ; ROAD_DEPOT_MIN_STOP_DISTANCE ecarte tout le
       * voisinage immediat des deux arrets, pas seulement leur facade exacte. */
      if (AIMap.DistanceManhattan(front, stopA.front) < ROAD_DEPOT_MIN_STOP_DISTANCE) continue;
      if (AIMap.DistanceManhattan(front, stopB.front) < ROAD_DEPOT_MIN_STOP_DISTANCE) continue;
      /* La facade du depot porte elle aussi deux axes : le trace et le raccord vers le depot. */
      if (!OpexRoadIsFlat(front)) continue;
      local x = AIMap.GetTileX(front);
      local y = AIMap.GetTileY(front);
      foreach (offset in offsets) {
        local x2 = x + offset[0];
        local y2 = y + offset[1];
        if (!OpexRoadInMap(x2, y2)) continue;
        local tile = AIMap.GetTileIndex(x2, y2);
        if (OpexRoadIsForbidden(tile, stopA, stopB)) continue;
        if (tile in onTrace) continue;      // cf. le commentaire ERR_AREA_NOT_CLEAR ci-dessus
        if (!OpexRoadIsFlat(tile)) continue;
        /* Les deux commandes doivent passer sous AITestMode : BuildRoad(front, tile) prouve que le
         * raccord manquant (cf. commentaire ci-dessus) est constructible, BuildRoadDepot(tile,
         * front) que le depot lui-meme l'est. Ni l'une ni l'autre seule ne suffit. */
        local ok = false;
        { local test = AITestMode();
          ok = AIRoad.BuildRoad(front, tile) && AIRoad.BuildRoadDepot(tile, front); }
        if (ok) return { tile = tile, front = front };
      }
    }
  }
  return null;
}

/* Plan concret d'UN candidat routier. Le candidat porte deja la paire, le cargo et le sens ; il
 * reste a trouver deux sites d'arret reels et un L qui les relie. Le sens compte : l'extremite
 * d'arrivee d'une ligne de fret doit ACCEPTER le cargo, pas le produire. */
function OpexRoadPlanFor(catalog, candidate)
{
  if (catalog.roadType < 0) return { plan = null, reason = "NOROAD" };
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local stop = OpexRoadStopKind(candidate.cargo);
  local coverage = AIStation.GetCoverageRadius(stop.stationType);
  local radiusA = candidate.srcTown >= 0 ? ROAD_TOWN_SEARCH_RADIUS : ROAD_INDUSTRY_SEARCH_RADIUS;
  local radiusB = candidate.dstTown >= 0 ? ROAD_TOWN_SEARCH_RADIUS : ROAD_INDUSTRY_SEARCH_RADIUS;
  /* Une ligne pax est bidirectionnelle : les deux extremites sont des sources. Une ligne de fret
   * est a sens unique -- c'est la meme asymetrie que le rail, et elle decide ici du predicat de
   * site comme elle decidera plus bas des ordres. */
  local dstWantsProduction = candidate.kind == "pax";

  /* Le plan rend une RAISON, jamais un simple null : la mesure du 2026-08-29 donnait 20 NOPLAN sur
   * 24 tentatives sans dire lesquelles butaient sur les sites d'arret et lesquelles sur le trace --
   * deux causes qui n'appellent pas du tout le meme correctif (rayon et sondes d'un cote, plafond
   * d'essais et platitude de l'autre). */
  local sitesA = OpexRoadSites(candidate.src, candidate.srcTown, candidate.cargo, stop.vehType,
                               coverage, true, radiusA);
  if (sitesA.len() == 0) return { plan = null, reason = "SITEA" };
  local sitesB = OpexRoadSites(candidate.dst, candidate.dstTown, candidate.cargo, stop.vehType,
                               coverage, dstWantsProduction, radiusB);
  if (sitesB.len() == 0) return { plan = null, reason = "SITEB" };

  local trials = 0;
  local noDepot = 0;
  foreach (siteA in sitesA) {
    foreach (siteB in sitesB) {
      for (local shape = 0; shape < 2; shape++) {
        if (trials >= ROAD_MAX_TRACE_TRIALS) {
          return { plan = null, reason = noDepot > 0 ? "DEPOTX" : "TRACEX" };
        }
        trials++;
        local trace = OpexRoadTrace(siteA.front, siteB.front, shape == 0);
        if (trace.len() == 0 || trace.len() > ROAD_MAX_TRACE_TILES) continue;
        /* cf. commentaire sur OpexRoadTraceHitsStop : le trace ne doit jamais retraverser le
         * corps d'un des deux arrets qu'il relie, sous peine d'etre coupe une fois l'arret
         * construit par-dessus. */
        if (OpexRoadTraceHitsStop(trace, siteA.tile) || OpexRoadTraceHitsStop(trace, siteB.tile)) continue;
        if (!OpexRoadTraceBuildable(trace)) continue;
        local depot = OpexRoadFindDepot(trace, siteA, siteB);
        /* Un trace valide sans depot n'est pas le meme echec qu'aucun trace valide : le premier dit
         * que le terrain autour du trace est bati ou en pente, le second que les deux facades ne se
         * relient pas. noDepot les separe dans la raison rendue. */
        if (depot == null) { noDepot++; continue; }
        return { plan = { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
                          stationType = stop.stationType, vehType = stop.vehType,
                          routeDistance = trace.len(), shape = shape, trials = trials },
                 reason = "OK" };
      }
    }
  }
  return { plan = null, reason = noDepot > 0 ? "DEPOTX" : "TRACEX" };
}

/* La liste added ne contient que les aretes dont la connexion n'existait pas avant notre appel.
 * Le rollback ne supprime donc jamais une route de ville preexistante. */
function OpexRoadRollback(stopA, stopB, depot, vehicles, added)
{
  foreach (v in vehicles) {
    if (AIVehicle.IsValidVehicle(v)) AIVehicle.SellVehicle(v);
  }
  if (depot != null && AIRoad.IsRoadDepotTile(depot)) AIRoad.RemoveRoadDepot(depot);
  if (stopB != null && AIRoad.IsRoadStationTile(stopB)) AIRoad.RemoveRoadStation(stopB);
  if (stopA != null && AIRoad.IsRoadStationTile(stopA)) AIRoad.RemoveRoadStation(stopA);
  for (local i = added.len() - 1; i >= 0; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
}

function OpexRoadBuildTrace(trace, added)
{
  foreach (edge in trace) {
    if (AIRoad.AreRoadTilesConnected(edge.from, edge.to)) continue;
    local ok = AIRoad.BuildRoad(edge.from, edge.to);
    /* L'API peut repondre ERR_ALREADY_BUILT alors que l'arete etait deja presente : seul le test
     * de connectivite decide. Si nous avons vraiment construit, elle est marquee pour rollback. */
    local connected = AIRoad.AreRoadTilesConnected(edge.from, edge.to);
    if (!connected) return false;
    if (ok) added.append(edge);
  }
  return true;
}

/* La capacite du catalogue est celle du cargo D'ORIGINE du moteur ; celle qui compte est la
 * capacite APRES refit, et un NewGRF peut la faire dependre du depot. On la relit donc ici, une
 * fois le depot bati -- c'est la seule valeur qui ait une chance d'etre exacte. */
function OpexRoadRefitCapacity(depot, engine, cargo)
{
  return AIVehicle.GetBuildWithRefitCapacity(depot, engine.id, cargo);
}

/* Transaction complete. Les vehicules ne demarrent qu'apres les ordres et toutes les connexions
 * valides, donc ils peuvent toujours etre vendus dans le depot pendant le rollback. */
function OpexBuildRoadRoute(catalog, budget, plan, candidate)
{
  local result = { ok = false, reason = "", error = 0, stopA = null, stopB = null,
                   stationA = null, stationB = null, depot = null, vehicles = [], cost = 0,
                   capacity = 0, opcodes = 0 };
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local balanceBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local cargo = candidate.cargo;
  local added = [];
  local stopA = null;
  local stopB = null;
  local depot = null;
  local built = [];

  budget.begin();
  if (!OpexRoadBuildTrace(plan.trace, added)) {
    result.error = AIError.GetLastError();
    result.opcodes = budget.end("build_roads");
    OpexRoadRollback(null, null, null, built, added); result.reason = "ROAD"; return result;
  }
  result.opcodes = budget.end("build_roads");

  budget.begin();
  /* Meme bug que le depot (cf. commentaire sur OpexRoadFindDepot et sur OpexRoadSites) :
   * CmdBuildRoadStop ne pose ni ne verifie rien sur "front". Le raccord doit donc etre construit
   * explicitement AVANT l'arret, pendant que la tuile de l'arret est encore une route ordinaire
   * clairable -- CMD_LANDSCAPE_CLEAR interne de CmdBuildRoadStop la remplace ensuite, "front"
   * garde le bit. Chaque arete n'est ajoutee a `added` que si elle est reellement connectee. */
  AIRoad.BuildRoad(plan.stopA.front, plan.stopA.tile);
  local stubConnectedA = AIRoad.AreRoadTilesConnected(plan.stopA.front, plan.stopA.tile);
  if (stubConnectedA) added.append({ from = plan.stopA.front, to = plan.stopA.tile });
  local okA = stubConnectedA && AIRoad.BuildRoadStation(plan.stopA.tile, plan.stopA.front,
                                                        plan.vehType, AIStation.STATION_NEW);
  /* Bout en bout : GetRoadStationFrontTile, comme GetRoadDepotFrontTile, n'est que la geometrie
   * DECLAREE (station + offset), jamais une preuve de connexion reelle. Contrairement a ce que
   * supposait un commentaire precedent, AreRoadTilesConnected gere correctement les tuiles
   * MP_STATION (GetAnyRoadBits en fait un cas explicite, verifie dans road_map.cpp) : c'est donc le
   * seul predicat qui prouve que l'arret est reellement raccorde a "front", pas seulement pose. */
  if (okA && AIRoad.IsRoadStationTile(plan.stopA.tile) &&
      AIRoad.GetRoadStationFrontTile(plan.stopA.tile) == plan.stopA.front &&
      AIRoad.AreRoadTilesConnected(plan.stopA.tile, plan.stopA.front)) stopA = plan.stopA.tile;
  if (stopA == null) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_road_stops");
    OpexRoadRollback(null, null, null, built, added); result.reason = "ASTOP"; return result;
  }
  AIRoad.BuildRoad(plan.stopB.front, plan.stopB.tile);
  local stubConnectedB = AIRoad.AreRoadTilesConnected(plan.stopB.front, plan.stopB.tile);
  if (stubConnectedB) added.append({ from = plan.stopB.front, to = plan.stopB.tile });
  local okB = stubConnectedB && AIRoad.BuildRoadStation(plan.stopB.tile, plan.stopB.front,
                                                        plan.vehType, AIStation.STATION_NEW);
  if (okB && AIRoad.IsRoadStationTile(plan.stopB.tile) &&
      AIRoad.GetRoadStationFrontTile(plan.stopB.tile) == plan.stopB.front &&
      AIRoad.AreRoadTilesConnected(plan.stopB.tile, plan.stopB.front)) stopB = plan.stopB.tile;
  result.opcodes += budget.end("build_road_stops");
  if (stopB == null) {
    result.error = AIError.GetLastError(); OpexRoadRollback(stopA, null, null, built, added);
    result.reason = "BSTOP"; return result;
  }
  local stationA = AIStation.GetStationID(stopA);
  local stationB = AIStation.GetStationID(stopB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) || stationA == stationB) {
    OpexRoadRollback(stopA, stopB, null, built, added); result.reason = "STATION"; return result;
  }

  budget.begin();
  /* Le vrai bug (2026-08-28, prouve dans road_cmd.cpp:1151/script_road.cpp:524, cf. commentaire
   * sur OpexRoadFindDepot) : CmdBuildRoadDepot ne construit RIEN sur "front", seulement sur sa
   * propre tuile. Sans ce raccord explicite, "front" ne recoit jamais le bit de route
   * perpendiculaire vers le depot -- le vehicule reste physiquement incapable de monter dessus
   * (mesure : RL fige exactement sur la tuile du depot, RV/RQ oscillent sans avancer). Ce
   * BuildRoad pose ce bit manquant AVANT le depot, pendant que la tuile du depot est encore une
   * route ordinaire clairable ; BuildRoadDepot la remplace ensuite (CMD_LANDSCAPE_CLEAR interne),
   * "front" garde le bit. L'arete est ajoutee a `added` (donc demontee par le rollback) des
   * qu'elle est reellement connectee -- avant meme de savoir si le depot suivra. */
  AIRoad.BuildRoad(plan.depot.front, plan.depot.tile);
  local stubConnected = AIRoad.AreRoadTilesConnected(plan.depot.front, plan.depot.tile);
  if (stubConnected) added.append({ from = plan.depot.front, to = plan.depot.tile });
  local depotOk = stubConnected && AIRoad.BuildRoadDepot(plan.depot.tile, plan.depot.front);
  /* Comme pour le rail : un "reussi" de l'API n'est jamais une preuve de connexion. Contrairement a
   * ce que supposait un commentaire precedent, AreRoadTilesConnected gere correctement le cas
   * ROAD_TILE_DEPOT (GetAnyRoadBits renvoie DiagDirToRoadBits(GetRoadDepotDirection(tile)), verifie
   * dans road_map.cpp) : c'est donc le seul predicat qui prouve que le depot est reellement
   * raccorde au trace, pas seulement pose avec la bonne geometrie declaree
   * (IsRoadDepotTile/GetRoadDepotFrontTile). */
  if (depotOk && AIRoad.IsRoadDepotTile(plan.depot.tile) &&
      AIRoad.GetRoadDepotFrontTile(plan.depot.tile) == plan.depot.front &&
      AIRoad.AreRoadTilesConnected(plan.depot.tile, plan.depot.front)) depot = plan.depot.tile;
  result.opcodes += budget.end("build_road_depot");
  if (depot == null) {
    result.error = AIError.GetLastError(); OpexRoadRollback(stopA, stopB, null, built, added);
    result.reason = "DEPOT"; return result;
  }

  budget.begin();
  local capacity = OpexRoadRefitCapacity(depot, candidate.engine, cargo);
  if (capacity <= 0) {
    result.opcodes += budget.end("build_road_vehicles");
    OpexRoadRollback(stopA, stopB, depot, built, added);
    result.reason = "REFIT"; return result;
  }
  local first = AIVehicle.BuildVehicleWithRefit(depot, candidate.engine.id, cargo);
  if (!AIVehicle.IsValidVehicle(first)) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_road_vehicles");
    OpexRoadRollback(stopA, stopB, depot, built, added); result.reason = "VEH"; return result;
  }
  built.append(first);
  if (AIVehicle.GetCapacity(first, cargo) <= 0 ||
      !AIRoad.RoadVehHasPowerOnRoad(AIVehicle.GetRoadType(first), catalog.roadType)) {
    result.opcodes += budget.end("build_road_vehicles");
    OpexRoadRollback(stopA, stopB, depot, built, added); result.reason = "POWER"; return result;
  }

  /* Ordres. La regle du fret vient directement de l'effondrement rail du 2026-08-28 : une ligne de
   * fret est a SENS UNIQUE, donc un OF_FULL_LOAD_ANY au puits fait attendre pour toujours un
   * chargement de retour qui n'existe pas. La source, elle, garde le plein chargement : le cargo y
   * s'accumule de toute facon, et un camion qui part avec une unite paie son trajet pour rien.
   * Le pax fait l'inverse du rail et ne charge JAMAIS a plein : sur une ligne courte, la note de
   * gare depend a 51 % du delai depuis le dernier ramassage (docs/mecanique_jeu.md S3) -- un bus
   * qui attend d'etre plein detruit precisement ce que la ligne a de bon. */
  local sourceFlags = candidate.kind == "freight" ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local orderA = AIOrder.AppendOrder(first, stopA, sourceFlags);
  local errorA = orderA ? 0 : AIError.GetLastError();
  local orderB = AIOrder.AppendOrder(first, stopB, AIOrder.OF_NONE);
  local errorB = orderB ? 0 : AIError.GetLastError();
  if (!orderA || !orderB || AIOrder.GetOrderCount(first) != 2) {
    result.error = !orderA ? errorA : errorB; result.opcodes += budget.end("build_road_vehicles");
    OpexRoadRollback(stopA, stopB, depot, built, added); result.reason = "ORDERS"; return result;
  }

  /* Les vehicules suivants sont CLONES du premier avec partage d'ordres : le clone reprend le
   * refit, et le partage evite de reposer deux ordres par vehicule (docs/mecanique_jeu.md S9,
   * AIOrder.ShareOrders). Un clone qui echoue n'est pas fatal -- la ligne roule avec ce qu'elle a,
   * ce qui vaut mieux qu'un rollback complet pour un vehicule d'appoint.
   * ⚠️ Le plafond vient du jeu, pas de nous : un arret n'accueille que DEUX vehicules a la fois,
   * au-dela ils font la queue sur la route et se bloquent (docs/mecanique_jeu.md S11). C'est
   * MAX_ROAD_VEHICLES dans economy.nut qui borne candidate.trains, pas ce code. */
  for (local i = 1; i < candidate.trains; i++) {
    /* `clone` est un MOT RESERVE de Squirrel (l'operateur de copie) : le nommer ainsi fait echouer
     * la compilation du fichier entier, et l'echec est presque muet -- une seule ligne dans la
     * sortie OpenTTD, aucun panneau, une compagnie qui existe sans rien construire. */
    local extra = AIVehicle.CloneVehicle(depot, first, true);
    if (!AIVehicle.IsValidVehicle(extra)) break;
    built.append(extra);
  }

  foreach (v in built) {
    if (!AIVehicle.StartStopVehicle(v)) {
      result.error = AIError.GetLastError();
      result.opcodes += budget.end("build_road_vehicles");
      OpexRoadRollback(stopA, stopB, depot, built, added); result.reason = "START"; return result;
    }
  }
  result.opcodes += budget.end("build_road_vehicles");

  result.ok = true; result.reason = "OK"; result.stopA = stopA; result.stopB = stopB;
  result.stationA = stationA; result.stationB = stationB; result.depot = depot;
  result.vehicles = built;
  result.capacity = AIVehicle.GetCapacity(first, cargo);
  result.cost = balanceBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  return result;
}
