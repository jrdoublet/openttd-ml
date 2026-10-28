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
 * -- les alternatives naissent dans candidates.nut et la decision vit dans projects.nut ; ce
 * fichier ne fait plus que planifier et batir la paire qu'on lui donne.
 */

ROAD_MAX_TRACE_TILES <- ROAD1Y_DIST_BANDS ? 128 : 48;
ROAD_TOWN_SEARCH_RADIUS <- 16;
ROAD_INDUSTRY_SEARCH_RADIUS <- 5;
ROAD_MAX_SITE_PROBES <- 64;
ROAD_MAX_SITES_PER_END <- 4;
ROAD_MAX_TRACE_TRIALS <- 48;
ROAD_CAPITAL_MARGIN <- 1000;
ROAD_DEPOT_MIN_STOP_DISTANCE <- 3;
ROAD_PAX_VOIRIE_SAME_TOWN_MAX_DIST <- 12;
/* Pax : arrets traversants SUR la voirie existante (AAAHogEx). Le depot reste hors route.
 * Defaut 0. Ce n'est PAS le jet DT de 2026-08-28 (912 k ops en remplacement du L) : ici on
 * n'echantillonne que des IsRoadTile et on relie par BFS sur la voirie, sans scier les maisons.
 * MIN_PAIR = C29.4 / HogEx : sous 6 tuiles le depot (filet de 3) est impossible et
 * CmdBuildRoadStop rend TOO_CLOSE / BSTOP. */
ROAD_PAX_VOIRIE_MIN_PAIR <- ROAD_BUS_STOP_MIN_DISTANCE;

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
/* `requireCargo = false` : accepter un emplacement qui ne produit NI n'accepte de cargo par
 * lui-meme. C'est le cas du bout HUB d'une ligne de rabattage : la gare ou l'aeroport vise n'est
 * ni une source ni un puits au sens de la carte d'acceptation -- le cargo est celui que le bus
 * apporte. Exiger une production (le defaut pax) ou une acceptation (le defaut fret) y rend
 * SITEB a coup sur, et main.nut bannit alors la paire pour toujours (docs/taches.md S0 sexvicies,
 * verrou 2). */
function OpexRoadSites(center, townId, cargo, vehType, coverage, wantProduction, radius,
                       otherCenter, requireCargo = true, excludeTiles = null,
                       existingOnly = false)
{
  /* Levier B, Niveau 1 : pas de chargement sur industrie primaire rival-servie */
  if (OPEX_LEVEL_LIMITS && wantProduction && townId < 0) {
    local indId = AIIndustry.GetIndustryID(center);
    if (indId >= 0 && OpexIndustryPrimaryRivalServed(indId, center, coverage)) {
      return { sites = [], stats = null };
    }
  }

  /* Levier B, Niveau 0 : rejet si le rayon de captage chevauche celui d'une gare rivale */
  if (OPEX_LEVEL_LIMITS && !OpexLevelAllows("encroach_rival_catchment")) {
    local res = OpexRoadSitesGated(center, townId, cargo, vehType, coverage, wantProduction, radius, otherCenter, requireCargo, excludeTiles, existingOnly);
    if (res != null && ("sites" in res) && res.sites != null) {
      local filtered = [];
      foreach (s in res.sites) {
        local tx = AIMap.GetTileX(s.tile);
        local ty = AIMap.GetTileY(s.tile);
        if (!OpexStationEncroachesRival(tx, ty, tx, ty, coverage)) {
          filtered.append(s);
        }
      }
      res.sites = filtered;
    }
    return res;
  }

  return OpexRoadSitesGated(center, townId, cargo, vehType, coverage, wantProduction, radius, otherCenter, requireCargo, excludeTiles, existingOnly);
}

function OpexRoadIsForbidden(tile, stopA, stopB)
{
  return tile == stopA.tile || tile == stopB.tile;
}

/* Bug mesure le 2026-08-28 (results/opex_bus_diag_*.json, signs RT/RL/RQ) : sur la paire 27<->33,
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
function OpexRoadFindDepot(trace, stopA, stopB, driveThrough = false)
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
  /* Experience du 2026-08-28 (cf. results/opex_bus_diag_*.json) : chercher a partir de la fin du trace
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
       * constant, ordre bloque sur stopA, campagne graine 42 -- results/opex_bus_diag_*.json). Le
       * trace a 24 tuiles de facades candidates ; ROAD_DEPOT_MIN_STOP_DISTANCE ecarte tout le
       * voisinage immediat des deux arrets, pas seulement leur facade exacte. */
      /* DT : l'arret EST sur le trace, stop.front aussi. Mesurer au corps (tile) sinon
       * le filet de 3 avale tout un bus intra-ville. Cul-de-sac : garder la facade. */
      local keepA = driveThrough ? stopA.tile : stopA.front;
      local keepB = driveThrough ? stopB.tile : stopB.front;
      if (AIMap.DistanceManhattan(front, keepA) < ROAD_DEPOT_MIN_STOP_DISTANCE) continue;
      if (AIMap.DistanceManhattan(front, keepB) < ROAD_DEPOT_MIN_STOP_DISTANCE) continue;
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

function OpexRoadTraceMulti(from, to, variant)
{
  local x1 = AIMap.GetTileX(from);
  local y1 = AIMap.GetTileY(from);
  local x2 = AIMap.GetTileX(to);
  local y2 = AIMap.GetTileY(to);

  if (variant == 0) return OpexRoadTrace(from, to, true);
  if (variant == 1) return OpexRoadTrace(from, to, false);
  if (variant == 2) {
    local xmid = (x1 + x2) / 2;
    local c1 = AIMap.GetTileIndex(xmid, y1);
    local c2 = AIMap.GetTileIndex(xmid, y2);
    if (!OpexRoadIsFlat(c1) || !OpexRoadIsFlat(c2)) return [];
    local out = [];
    OpexRoadAppendSegment(out, from, c1);
    OpexRoadAppendSegment(out, c1, c2);
    OpexRoadAppendSegment(out, c2, to);
    return out;
  }
  if (variant == 3) {
    local ymid = (y1 + y2) / 2;
    local c1 = AIMap.GetTileIndex(x1, ymid);
    local c2 = AIMap.GetTileIndex(x2, ymid);
    if (!OpexRoadIsFlat(c1) || !OpexRoadIsFlat(c2)) return [];
    local out = [];
    OpexRoadAppendSegment(out, from, c1);
    OpexRoadAppendSegment(out, c1, c2);
    OpexRoadAppendSegment(out, c2, to);
    return out;
  }
  if (variant == 4) {
    local xmid = (x1 + x2) / 2 + 1;
    if (!OpexRoadInMap(xmid, y1) || !OpexRoadInMap(xmid, y2)) return [];
    local c1 = AIMap.GetTileIndex(xmid, y1);
    local c2 = AIMap.GetTileIndex(xmid, y2);
    if (!OpexRoadIsFlat(c1) || !OpexRoadIsFlat(c2)) return [];
    local out = [];
    OpexRoadAppendSegment(out, from, c1);
    OpexRoadAppendSegment(out, c1, c2);
    OpexRoadAppendSegment(out, c2, to);
    return out;
  }
  if (variant == 5) {
    local ymid = (y1 + y2) / 2 + 1;
    if (!OpexRoadInMap(x1, ymid) || !OpexRoadInMap(x2, ymid)) return [];
    local c1 = AIMap.GetTileIndex(x1, ymid);
    local c2 = AIMap.GetTileIndex(x2, ymid);
    if (!OpexRoadIsFlat(c1) || !OpexRoadIsFlat(c2)) return [];
    local out = [];
    OpexRoadAppendSegment(out, from, c1);
    OpexRoadAppendSegment(out, c1, c2);
    OpexRoadAppendSegment(out, c2, to);
    return out;
  }
  /* MULTI-1: four signed midpoint offsets, constrained to the rectangle.
   * Variants 0..5 remain untouched and take precedence in the planner. */
  if (variant >= 6 && variant <= 9) {
    local c1 = null;
    local c2 = null;
    if (variant == 6 || variant == 7) {
      local xmid = (x1 + x2) / 2 - (variant == 6 ? 1 : 2);
      if (xmid < (x1 < x2 ? x1 : x2) || xmid > (x1 > x2 ? x1 : x2)
        || !OpexRoadInMap(xmid, y1) || !OpexRoadInMap(xmid, y2)) return [];
      c1 = AIMap.GetTileIndex(xmid, y1);
      c2 = AIMap.GetTileIndex(xmid, y2);
    } else {
      local ymid = (y1 + y2) / 2 - (variant == 8 ? 1 : 2);
      if (ymid < (y1 < y2 ? y1 : y2) || ymid > (y1 > y2 ? y1 : y2)
        || !OpexRoadInMap(x1, ymid) || !OpexRoadInMap(x2, ymid)) return [];
      c1 = AIMap.GetTileIndex(x1, ymid);
      c2 = AIMap.GetTileIndex(x2, ymid);
    }
    if (!OpexRoadIsFlat(c1) || !OpexRoadIsFlat(c2)) return [];
    local out = [];
    OpexRoadAppendSegment(out, from, c1);
    OpexRoadAppendSegment(out, c1, c2);
    OpexRoadAppendSegment(out, c2, to);
    return out;
  }
  return [];
}

/* Un arret traversant n'a qu'un axe : le bus ne peut entrer/sortir que par front ou son oppose. */
function OpexRoadOnDtAxis(tile, front, other)
{
  if (front == null) return true;
  local back = tile - (front - tile);
  return other == front || other == back;
}

function OpexRoadOurBusTiles()
{
  local out = [];
  local stations = AIStationList(AIStation.STATION_BUS_STOP);
  for (local id = stations.Begin(); !stations.IsEnd(); id = stations.Next()) {
    /* GetLocation ne renvoie qu'une tuile arbitraire de la gare multimodale. Une gare peut avoir
     * plusieurs quais bus, notamment un arret joint a un aeroport : enumerer les vraies tuiles. */
    local tiles = AITileList_StationType(id, AIStation.STATION_BUS_STOP);
    for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next()) out.append(tile);
  }
  return out;
}

function OpexRoadTileTooClose(tile, others, minDist)
{
  if (others == null) return false;
  foreach (other in others) {
    if (AIMap.DistanceManhattan(tile, other) < minDist) return true;
  }
  return false;
}

/* BFS sur les tuiles de route deja connectees. Pas Pathfinder.Road.
 * srcFront/dstFront : contraindre le premier et dernier pas a l'axe DT, sinon le bus
 * sort en perpendiculaire et reste fige dans l'arret. */
function OpexRoadBfsPath(src, dst, maxNodes, srcFront = null, dstFront = null)
{
  if (src == dst) return [];
  if (!AIRoad.IsRoadTile(src) || !AIRoad.IsRoadTile(dst)) return null;
  local came = {};
  came.rawset(src, src);
  local q = [src];
  local qi = 0;
  local n = 0;
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  while (qi < q.len()) {
    local cur = q[qi];
    qi++;
    n++;
    if (n > maxNodes) return null;
    foreach (d in dirs) {
      local nxt = cur + d;
      if (!AIMap.IsValidTile(nxt)) continue;
      if (nxt in came) continue;
      if (!AIRoad.IsRoadTile(nxt)) continue;
      if (!AIRoad.AreRoadTilesConnected(cur, nxt)) continue;
      if (cur == src && !OpexRoadOnDtAxis(src, srcFront, nxt)) continue;
      if (nxt == dst && !OpexRoadOnDtAxis(dst, dstFront, cur)) continue;
      came.rawset(nxt, cur);
      if (nxt == dst) {
        local edges = [];
        local t = dst;
        while (t != src) {
          local p = came[t];
          edges.insert(0, { from = p, to = t });
          t = p;
        }
        return edges;
      }
      q.append(nxt);
    }
  }
  return null;
}

/* Sites pax : tuiles de ROUTE existantes, arret traversant. Jamais d'herbe entre les maisons.
 * Intra-ville : anneau a 3 tuiles du centre (HogEx), pas le cargo max des deux bouts
 * (sinon minD=1 et DEPOT impossible). Interurbain : encore le bord tourne vers l'autre ville. */
function OpexRoadPaxVoirieSites(center, townId, cargo, vehType, coverage, otherCenter,
                                requireCargo = true, excludeTiles = null)
{
  if (OPEX_LEVEL_LIMITS && !OpexLevelAllows("encroach_rival_catchment")) {
    local sites = OpexRoadPaxVoirieGated(center, townId, cargo, vehType, coverage, otherCenter, requireCargo, excludeTiles);
    if (sites != null) {
      local filtered = [];
      foreach (s in sites) {
        local tx = AIMap.GetTileX(s.tile);
        local ty = AIMap.GetTileY(s.tile);
        if (!OpexStationEncroachesRival(tx, ty, tx, ty, coverage)) {
          filtered.append(s);
        }
      }
      return filtered;
    }
    return sites;
  }
  return OpexRoadPaxVoirieGated(center, townId, cargo, vehType, coverage, otherCenter, requireCargo, excludeTiles);
}

/* ROAD100-7 : sur le seul chemin opt-in, tester d'abord les couples de sites
 * captant le plus de voyageurs (puis le trajet le plus court). Les plafonds
 * existants de sites, de BFS et de tracés sont conservés. */
function OpexRoad100SortSitePair(a, b)
{
  local valueA = a.a.value + a.b.value;
  local valueB = b.a.value + b.b.value;
  if (valueA != valueB) return valueA > valueB ? -1 : 1;
  if (a.d != b.d) return a.d < b.d ? -1 : 1;
  return 0;
}

function OpexRoad100SortJoinedSite(a, b)
{
  if (a.marginal != b.marginal) return a.marginal > b.marginal ? -1 : 1;
  if (a.distance != b.distance) return a.distance < b.distance ? -1 : 1;
  return a.tile < b.tile ? -1 : (a.tile > b.tile ? 1 : 0);
}

/* ROAD100-9 : plusieurs gares peuvent servir la meme ville uniquement si
 * leurs aires de couverture ne partagent AUCUNE tuile (distance Chebyshev).
 * Ce filtre a lieu a la generation ET a la construction, via le meme plan. */
function OpexRoad100CatchmentOverlaps(tile, existingStops, coverage)
{
  if (existingStops == null) return false;
  foreach (other in existingStops) {
    if (AIMap.DistanceMax(tile, other) <= 2 * coverage) return true;
  }
  return false;
}

/* ROAD100-16 v2 : echantillon physique leger, sans modifier le balayage
 * voirie historique rayon16. Le premier shadow v1 coutait 483k ops AVANT
 * SITE_B : verifier au plus 48 tuiles de route / 8 tests de quai / rayon8.
 * Score prioritairement sur la production de l'arret effectivement testable,
 * et non sur la seule demande totale de la ville. */
function OpexRoad100LongCheapSites(center, townId, cargo, coverage, otherCenter,
                                   excluded, mark, limitOps)
{
  local rawSites = [];
  local seenRoad = 0;
  local tests = 0;
  local scanMark = OpexOpsMeasureBegin();
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1)];
  /* v4 : echantillonnage par anneaux pairs 0..16, deux tests maximum
   * par anneau pour ne pas epuiser les 16 essais en centre-ville. */
  for (local radius = 0; radius <= 16 && seenRoad < 160 && tests < 16; radius += 2) {
    if (OpexOpsMeasureEnd(scanMark) >= 65000 ||
        OpexOpsMeasureEnd(mark) >= limitOps - 40000) break;
    local ringTests = 0;
    for (local dx = -radius; dx <= radius && seenRoad < 160 && tests < 16
         && ringTests < 2; dx++) {
      for (local dy = -radius; dy <= radius && seenRoad < 160 && tests < 16
           && ringTests < 2; dy++) {
        if (OpexOpsMeasureEnd(scanMark) >= 65000 ||
            OpexOpsMeasureEnd(mark) >= limitOps - 40000) break;
        local adx = dx < 0 ? -dx : dx;
        local ady = dy < 0 ? -dy : dy;
        if (radius > 0 && adx != radius && ady != radius) continue;
        local xx = cx + dx;
        local yy = cy + dy;
        if (!OpexRoadInMap(xx, yy)) continue;
        local tile = AIMap.GetTileIndex(xx, yy);
        if (!AIRoad.IsRoadTile(tile) || AIRoad.IsRoadStationTile(tile)
            || AIRoad.IsRoadDepotTile(tile)) continue;
        seenRoad++;
        if (AITile.GetClosestTown(tile) != townId
            || OpexRoadTileTooClose(tile, excluded, ROAD_PAX_VOIRIE_MIN_PAIR))
          continue;
        local amount = AITile.GetCargoProduction(tile, cargo, 1, 1, coverage);
        if (amount <= 0) continue;
        foreach (dir in dirs) {
          if (tests >= 8) break;
          local front = tile + dir;
          if (!AIMap.IsValidTile(front) ||
              AIMap.DistanceManhattan(tile, front) != 1 ||
              !AIRoad.IsRoadTile(front)) continue;
          local ok = false;
          { local test = AITestMode();
            ok = AIRoad.BuildDriveThroughRoadStation(tile, front,
                AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
        tests++;
        ringTests++;
          if (!ok) continue;
          local toOther = AIMap.DistanceManhattan(tile, otherCenter);
          local item = { tile = tile, front = front, value = amount,
                         score = amount * 1000 - toOther };
        rawSites.append(item);
          break;
        }
      }
    }
  }
  /* La selection precedente gardait quatre arrets voisins dans le
   * meme quartier : l'union ajoutait 0..2 PASS sur cinq graines.
   * Conserver le meilleur arret, puis favoriser un satellite separant
   * ses maisons sans sortir du station_spread autour de la racine. */
  local out = [];
  local chosen = {};
  local spread = AIGameSettings.GetValue("station.station_spread");
  while (out.len() < 4 && out.len() < rawSites.len()) {
    local best = -1;
    local bestScore = -99999999;
    for (local j = 0; j < rawSites.len(); j++) {
      if (j in chosen) continue;
      local score = rawSites[j].score;
      if (out.len() > 0) {
        local fromRoot = AIMap.DistanceMax(rawSites[j].tile, out[0].tile);
        if (fromRoot >= spread) continue;
        local closest = 9999;
        foreach (picked in out) {
          local d = AIMap.DistanceMax(rawSites[j].tile, picked.tile);
          if (d < closest) closest = d;
        }
        /* 0 bonus en recouvrement, 2000 apres 2*coverage ; ne jamais
         * croire que deux carrés adjacents creent double demande. */
        local spreadBonus = closest * 200;
        if (spreadBonus > 2000) spreadBonus = 2000;
        score += spreadBonus;
      }
      if (best < 0 || score > bestScore
          || (score == bestScore && rawSites[j].tile < rawSites[best].tile)) {
        best = j;
        bestScore = score;
      }
    }
    if (best < 0) break;
    chosen.rawset(best, true);
    out.append(rawSites[best]);
  }
  return out;
}

/* ROAD100-16 v8 BUILD UNIQUEMENT : echantillonner des quartiers distincts
 * avant les AITest. Ni le shadow ni le CheapSites historique ne passent ici.
 * 4 couronnes x 4 quadrants x 6 points par secteur, avec 5 voisins au plus.
 * Le scan de maisons reste sparse (96 ancres, 480 tuiles uniques au plus),
 * aucune Valuate et aucune generation de candidats supplementaires.
 * Production = AITile.GetCargoProduction au rayon exact de l'arret, JAMAIS
 * une demande de ville ou un multiplicateur artificiel.
 * budget : 35k scan, 65k total par bout, garde du mark partage pour le plan. */
function OpexRoad100LongBuildSites(center, townId, cargo, coverage, otherCenter,
                                   excluded, mark, limitOps, nearOnly = false)
{
  local res = { sites = [], reason = "NO_SITE", samples = 0, road = 0,
      eligible = 0, buckets = 0, tests = 0, passed = 0,
      max_local = 0, max_tested = 0, ops = 0,
      scan_limited = 0, quadrant_mask = 0 };
  local scanMark = OpexOpsMeasureBegin();
  local radii = nearOnly ? [3] : [3, 8, 14, 22];
  local azimuth = [[1, 3], [2, 3], [3, 3], [3, 2], [3, 1], [3, 0]];
  local offsets = [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]];
  local dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local bins = [];
  for (local k = 0; k < 16; k++) bins.append(null);
  local seen = {};
  local stopScan = false;
  for (local ring = 0; ring < radii.len() && !stopScan; ring++) {
    local radius = radii[ring];
    for (local quadrant = 0; quadrant < 4 && !stopScan; quadrant++) {
      local cellMark = OpexOpsMeasureBegin();
      local sx = quadrant == 0 || quadrant == 3 ? 1 : -1;
      local sy = quadrant == 0 || quadrant == 1 ? 1 : -1;
      for (local direction = 0; direction < azimuth.len() && !stopScan; direction++) {
        /* Quota par secteur : les quartiers plus lointains ne sont pas
         * evinces par des milliers d'essais dans le cadran initial. */
        if (OpexOpsMeasureEnd(cellMark) >= 2100) break;
        for (local perturb = 0; perturb < offsets.len(); perturb++) {
          if (OpexOpsMeasureEnd(scanMark) >= 35000) {
            res.scan_limited = 1;
            stopScan = true;
            break;
          }
          if (OpexOpsMeasureEnd(cellMark) >= 2100) break;
          if (OpexOpsMeasureEnd(mark) >= limitOps - 90000 ||
              OpexOpsMeasureEnd(scanMark) >= 60000) {
            res.reason = "OPCAP";
            res.ops = OpexOpsMeasureEnd(scanMark);
            return res;
          }
          local x = cx + sx * ((radius * azimuth[direction][0]) / 3)
              + offsets[perturb][0];
          local y = cy + sy * ((radius * azimuth[direction][1]) / 3)
              + offsets[perturb][1];
          if (!OpexRoadInMap(x, y)) continue;
          local tile = AIMap.GetTileIndex(x, y);
          if (tile in seen) continue;
          seen.rawset(tile, true);
          res.samples++;
          if (!AIRoad.IsRoadTile(tile) || AIRoad.IsRoadStationTile(tile)
              || AIRoad.IsRoadDepotTile(tile) || AITile.IsStationTile(tile))
            continue;
          res.road++;
          if (AITile.GetClosestTown(tile) != townId ||
              OpexRoadTileTooClose(tile, excluded, ROAD_PAX_VOIRIE_MIN_PAIR))
            continue;
          res.eligible++;
          local production = AITile.GetCargoProduction(tile, cargo, 1, 1, coverage);
          if (production <= 0) continue;
          if (production > res.max_local) res.max_local = production;
          local slot = ring * 4 + quadrant;
          local prev = bins[slot];
          if (prev == null || production > prev.value ||
              (production == prev.value && tile < prev.tile))
            bins[slot] = { tile = tile, value = production,
                ring = ring, quadrant = quadrant };
        }
      }
    }
  }
  for (local idx = 0; idx < bins.len(); idx++) {
    if (bins[idx] != null) res.buckets++;
  }
  /* Au plus douze AITest, prioritaires par production dans chaque quadrant.
   * Trois passes par quadrant : le tri est LOCAL entre quatre couronnes,
   * jamais sur la totalité des 24² cases ni un tri de 1000 couples. */
  local attempted = {};
  local retained = [];
  for (local pass = 0; pass < 3 && res.tests < 12 && retained.len() < 4; pass++) {
    for (local q = 0; q < 4 && res.tests < 12 && retained.len() < 4; q++) {
      if (OpexOpsMeasureEnd(scanMark) >= 62000 ||
          OpexOpsMeasureEnd(mark) >= limitOps - 90000) {
        res.reason = "OPCAP";
        res.ops = OpexOpsMeasureEnd(scanMark);
        return res;
      }
      local pick = -1;
      for (local r = 0; r < 4; r++) {
        local key = r * 4 + q;
        local entry = bins[key];
        if (entry == null || key in attempted) continue;
        if (pick < 0 || entry.value > bins[pick].value ||
            (entry.value == bins[pick].value && entry.tile < bins[pick].tile))
          pick = key;
      }
      if (pick < 0) continue;
      attempted.rawset(pick, true);
      local site = bins[pick];
      /* Pas de double quartier : autoriser une seconde racine du meme
       * quadrant uniquement si elle est physiquement eloignee. */
      if (OpexRoadTileTooClose(site.tile, retained, 6)) continue;
      local probesHere = 0;
      /* ROAD100-16 v17 : dans un corridor express, le FRONT du quai
       * doit de preference sortir du quartier EN DIRECTION de l'autre
       * ville. Les quatre axes connectes restent admissibles, mais le
       * premier AITest ne se perd plus systematiquement en facade +X.
       * Aucun classement par profit post-construction ni route inventee. */
      local towardX = AIMap.GetTileX(otherCenter) >= AIMap.GetTileX(site.tile)
          ? 0 : 1;
      local towardY = AIMap.GetTileY(otherCenter) >= AIMap.GetTileY(site.tile)
          ? 2 : 3;
      local absX = AIMap.GetTileX(otherCenter) - AIMap.GetTileX(site.tile);
      local absY = AIMap.GetTileY(otherCenter) - AIMap.GetTileY(site.tile);
      if (absX < 0) absX = -absX;
      if (absY < 0) absY = -absY;
      local orderedDirs = absX >= absY
          ? [towardX, towardY, 1 - towardX, 5 - towardY]
          : [towardY, towardX, 5 - towardY, 1 - towardX];
      for (local d = 0; d < dirs.len() && res.tests < 12 && probesHere < 4; d++) {
        if (OpexOpsMeasureEnd(scanMark) >= 62000 ||
            OpexOpsMeasureEnd(mark) >= limitOps - 90000) {
          res.reason = "OPCAP";
          res.ops = OpexOpsMeasureEnd(scanMark);
          return res;
        }
        local axis = orderedDirs[d];
        local fx = AIMap.GetTileX(site.tile) + dirs[axis][0];
        local fy = AIMap.GetTileY(site.tile) + dirs[axis][1];
        if (!OpexRoadInMap(fx, fy)) continue;
        local front = AIMap.GetTileIndex(fx, fy);
        if (!AIRoad.IsRoadTile(front) ||
            !AIRoad.AreRoadTilesConnected(site.tile, front)) continue;
        res.tests++;
        probesHere++;
        if (site.value > res.max_tested) res.max_tested = site.value;
        local allowed = false;
        { local test = AITestMode();
          allowed = AIRoad.BuildDriveThroughRoadStation(site.tile, front,
              AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
        local chosenTile = site.tile;
        local chosenFront = front;
        local chosenValue = site.value;
        /* ROAD100-16 v15 : un centre de quartier peut etre inconstructible
         * meme si sa facade routiere voisine est admissible. Essayer le
         * quai a l'autre bout DE LA MEME arête connectee, sans route
         * fictive, ni production inventee, ni depasser 12 AITest/scanner.
         * AITest STATION_NEW physique obligatoire pour les deux sens. */
        if (!allowed && res.tests < 12 && probesHere < 4 &&
            AITile.GetClosestTown(front) == townId &&
            !OpexRoadTileTooClose(front, excluded, ROAD_PAX_VOIRIE_MIN_PAIR) &&
            !AIRoad.IsRoadStationTile(front) &&
            !AIRoad.IsRoadDepotTile(front) && !AITile.IsStationTile(front)) {
          local frontValue = AITile.GetCargoProduction(front, cargo, 1, 1, coverage);
          if (frontValue > 0) {
            res.tests++;
            probesHere++;
            if (frontValue > res.max_tested) res.max_tested = frontValue;
            { local test = AITestMode();
              allowed = AIRoad.BuildDriveThroughRoadStation(front, site.tile,
                  AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
            if (allowed) {
              chosenTile = front;
              chosenFront = site.tile;
              chosenValue = frontValue;
            }
          }
        }
        if (!allowed) continue;
        res.passed++;
        local toOther = AIMap.DistanceManhattan(chosenTile, otherCenter);
        res.sites.append({ tile = chosenTile, front = chosenFront, value = chosenValue,
            score = chosenValue * 1000 - toOther,
            quadrant = site.quadrant, ring = site.ring });
        retained.append(chosenTile);
        res.quadrant_mask = res.quadrant_mask | (1 << site.quadrant);
        break;
      }
    }
  }
  res.reason = res.sites.len() > 0 ? "OK" : "NO_TESTABLE";
  res.ops = OpexOpsMeasureEnd(scanMark);
  return res;
}

/* ROAD100-16 v3 : mesure PHYSIQUE du bassin theorique d'une seule StationID
 * avec une racine et au plus deux arrets DT joints (parmi quatre sites deja
 * passes individuellement sous AITest). Le vrai cumul de BuildStation(...,
 * stationId) n'est PAS teste ici : aucune union ne certifie la construction.
 *
 * Une unique Valuate native calcule la production 1x1 de toutes les maisons
 * des quatre carres ; chaque producteur est affecte a un masque de sites.
 * La somme des masques intersectant une configuration compte chaque maison
 * UNE FOIS, meme si deux/trois rayons de couverture se chevauchent. */
function OpexRoad100LongUnionEnd(sites, cargo, coverage, stationSpread,
                                 ownCoverage, mark, limitOps)
{
  local out = { measured = false, reason = "NO_SITE", roots = [], max_union = 0,
      max_single = 0, delta_single = 0, satellites = 0,
      root_tile = -1, producer_tiles = 0, combos = 0 };
  if (sites == null || sites.len() == 0 || coverage < 0 || stationSpread < 2)
    return out;
  local count = sites.len() < 4 ? sites.len() : 4;
  local x0 = AIMap.GetMapSizeX() - 1;
  local y0 = AIMap.GetMapSizeY() - 1;
  local x1 = 0;
  local y1 = 0;
  for (local i = 0; i < count; i++) {
    local x = AIMap.GetTileX(sites[i].tile);
    local y = AIMap.GetTileY(sites[i].tile);
    if (x - coverage < x0) x0 = x - coverage;
    if (y - coverage < y0) y0 = y - coverage;
    if (x + coverage > x1) x1 = x + coverage;
    if (y + coverage > y1) y1 = y + coverage;
  }
  if (x0 < 0) x0 = 0;
  if (y0 < 0) y0 = 0;
  if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
  if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
  /* Ne pas lancer un balayage natif potentiellement cher apres le budget. */
  if (OpexOpsMeasureEnd(mark) >= limitOps - 40000) { out.reason = "OPCAP"; return out; }
  local producing = AITileList();
  producing.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
  producing.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
  producing.KeepAboveValue(0);
  if (OpexOpsMeasureEnd(mark) >= limitOps) { out.reason = "OPCAP"; return out; }
  /* Une station Opex existante (bus, rail, air, port...) a deja capte ces
   * maisons ; le shadow long ne peut pas les vendre une seconde fois. */
  local byMask = [0, 0, 0, 0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0];
  foreach (producer, amount in producing) {
    if (OpexOpsMeasureEnd(mark) >= limitOps) { out.reason = "OPCAP"; return out; }
    if (ownCoverage != null && ownCoverage.HasItem(producer)) continue;
    local mask = 0;
    for (local i = 0; i < count; i++) {
      if (AIMap.DistanceMax(producer, sites[i].tile) <= coverage)
        mask = mask | (1 << i);
    }
    if (mask == 0) continue;
    byMask[mask] += amount;
    out.producer_tiles++;
  }
  local rootLimit = count;
  for (local root = 0; root < rootLimit; root++) {
    local rootBest = { value = 0, satellites = 0, mask = (1 << root) };
    for (local subset = 1; subset < (1 << count); subset++) {
      if ((subset & (1 << root)) == 0) continue;
      local minX = AIMap.GetMapSizeX();
      local minY = AIMap.GetMapSizeY();
      local maxX = -1;
      local maxY = -1;
      local selected = 0;
      local coherent = true;
      for (local idx = 0; idx < count; idx++) {
        if ((subset & (1 << idx)) == 0) continue;
        selected++;
        if (selected > 3) { coherent = false; break; }
        local xt = AIMap.GetTileX(sites[idx].tile);
        local yt = AIMap.GetTileY(sites[idx].tile);
        if (xt < minX) minX = xt;
        if (yt < minY) minY = yt;
        if (xt > maxX) maxX = xt;
        if (yt > maxY) maxY = yt;
        /* Limite conservatrice ROAD100-8 pour le satellite : stations
         * distinctes physiquement, mais dans le spread de la racine. */
        if (idx != root && (AIMap.DistanceManhattan(sites[root].tile,
                sites[idx].tile) < ROAD_BUS_STOP_MIN_DISTANCE ||
            AIMap.DistanceMax(sites[root].tile, sites[idx].tile) >= stationSpread))
          coherent = false;
      }
      if (!coherent || maxX - minX >= stationSpread ||
          maxY - minY >= stationSpread) continue;
      local volume = 0;
      for (local m = 1; m < (1 << count); m++) {
        if ((m & subset) != 0) volume += byMask[m];
      }
      out.combos++;
      if (selected == 1 && volume > out.max_single) out.max_single = volume;
      if (volume > rootBest.value ||
          (volume == rootBest.value && selected - 1 < rootBest.satellites)) {
        rootBest.value = volume;
        rootBest.satellites = selected - 1;
        rootBest.mask = subset;
      }
    }
    out.roots.append(rootBest);
    if (rootBest.value > out.max_union ||
        (rootBest.value == out.max_union && rootBest.satellites < out.satellites)) {
      out.max_union = rootBest.value;
      out.satellites = rootBest.satellites;
      out.root_tile = sites[root].tile;
    }
  }
  /* Les quatre sites ont chacun ete envisages en racine : max_single est
   * donc bien le meilleur arret individuel, apres retrait du bassin Opex. */
  out.delta_single = out.max_union - out.max_single;
  out.measured = true;
  out.reason = "COVERAGE_ONLY";
  return out;
}

/* ROAD100-16 v5 PATH_ONLY : BFS diagnostique sur voirie DEJA connectee.
 * Ne pas utiliser le BFS historique ici : son appel indivisible a 1024
 * noeuds ne sait pas interrompre une sonde proche du budget cumule.
 * Meme contraintes d'axe DT qu'OpexRoadBfsPath, sans AITest de jonction,
 * depot, construction, ou estimation de rentabilite. */
function OpexRoad100LongPathBudgetBfs(src, dst, srcFront, dstFront,
                                      mark, limitOps)
{
  local out = { reason = "NO_PATH", route = -1, nodes = 0, cost = -1 };
  if (!AIMap.IsValidTile(src) || !AIMap.IsValidTile(dst) ||
      !AIRoad.IsRoadTile(src) || !AIRoad.IsRoadTile(dst)) {
    out.reason = "NO_ROAD";
    return out;
  }
  if (src == dst) { out.reason = "SAME_TILE"; return out; }
  local came = {};
  came.rawset(src, src);
  local queue = [src];
  local head = 0;
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  /* Le cout par noeud varie selon l'environnement. Tester AVANT chaque
   * expansion et garder 10k d'opcodes pour retour et telemetrie. */
  while (head < queue.len() && out.nodes < 512) {
    if (OpexOpsMeasureEnd(mark) >= limitOps - 10000) {
      out.reason = "PATH_SKIPPED_OPCAP";
      return out;
    }
    local cur = queue[head];
    head++;
    out.nodes++;
    foreach (d in dirs) {
      local nextTile = cur + d;
      if (!AIMap.IsValidTile(nextTile) || nextTile in came ||
          !AIRoad.IsRoadTile(nextTile) ||
          !AIRoad.AreRoadTilesConnected(cur, nextTile)) continue;
      if (cur == src && !OpexRoadOnDtAxis(src, srcFront, nextTile)) continue;
      if (nextTile == dst && !OpexRoadOnDtAxis(dst, dstFront, cur)) continue;
      came.rawset(nextTile, cur);
      if (nextTile == dst) {
        local count = 0;
        local tile = dst;
        while (tile != src) {
          count++;
          tile = came[tile];
        }
        out.reason = "PATH_FOUND";
        out.route = count;
        /* Seulement les aretes routieres EXISTANTES ; 0 cout de pose de
         * couloir, aucun devis de gare/depot ni preuve de station jointe. */
        out.cost = 0;
        return out;
      }
      queue.append(nextTile);
    }
  }
  if (head < queue.len()) out.reason = "NODE_LIMIT";
  return out;
}

/* Une seule paire de sites choisie sans filtre de demande. Son resultat
 * reste DISTINCT de result.reason (LOW_DEMAND, ROI, JOIN_UNVERIFIED...).
 * Le budget est celui du shadow entier, jamais un compteur remis a zero. */
function OpexRoad100LongPathOnly(sitesA, sitesB, preliminary, mark, limitOps)
{
  local out = { reason = "PATH_NO_PAIR", forward_reason = "NOT_RUN",
      reverse_reason = "NOT_RUN", forward = -1, reverse = -1,
      forward_nodes = 0, reverse_nodes = 0, nodes = 0,
      cost = -1, ops = 0, siteA = -1, siteB = -1,
      center_distance = -1, site_distance = -1, node_limit = 512 };
  local probeMark = OpexOpsMeasureBegin();
  out.center_distance = AIMap.DistanceManhattan(preliminary.src, preliminary.dst);
  if (out.center_distance < 80 || out.center_distance > 170) return out;
  local firstA = null;
  local firstB = null;
  for (local a = 0; a < sitesA.len() && firstA == null; a++) {
    for (local b = 0; b < sitesB.len(); b++) {
      local dist = AIMap.DistanceManhattan(sitesA[a].tile, sitesB[b].tile);
      if (dist < 80 || dist > 170) continue;
      firstA = sitesA[a];
      firstB = sitesB[b];
      out.site_distance = dist;
      break;
    }
  }
  if (firstA == null) { out.ops = OpexOpsMeasureEnd(probeMark); return out; }
  out.siteA = firstA.tile;
  out.siteB = firstB.tile;
  if (OpexOpsMeasureEnd(mark) >= limitOps - 60000) {
    out.reason = "PATH_SKIPPED_OPCAP";
    out.ops = OpexOpsMeasureEnd(probeMark);
    return out;
  }
  local forward = OpexRoad100LongPathBudgetBfs(firstA.tile, firstB.tile,
      firstA.front, firstB.front, mark, limitOps);
  out.forward_reason = forward.reason;
  out.forward = forward.route;
  out.forward_nodes = forward.nodes;
  out.nodes += forward.nodes;
  if (forward.reason == "PATH_SKIPPED_OPCAP" ||
      OpexOpsMeasureEnd(mark) >= limitOps - 40000) {
    out.reason = "PATH_SKIPPED_OPCAP";
    out.ops = OpexOpsMeasureEnd(probeMark);
    return out;
  }
  local reverse = OpexRoad100LongPathBudgetBfs(firstB.tile, firstA.tile,
      firstB.front, firstA.front, mark, limitOps);
  out.reverse_reason = reverse.reason;
  out.reverse = reverse.route;
  out.reverse_nodes = reverse.nodes;
  out.nodes += reverse.nodes;
  if (reverse.reason == "PATH_SKIPPED_OPCAP")
    out.reason = "PATH_SKIPPED_OPCAP";
  else if (forward.reason == "PATH_FOUND" && reverse.reason == "PATH_FOUND") {
    out.reason = "PATH_BIDIRECTIONAL";
    out.cost = 0;
  } else out.reason = "PATH_NO_BIDIRECTIONAL";
  out.ops = OpexOpsMeasureEnd(probeMark);
  return out;
}

/* ROAD100-16 tranche A : sonde PURE avant toute nouvelle longue ligne.
 * Au plus quatre couples de sites forts, uniquement sur voirie connectee.
 * Un bon shadow n'est jamais un ordre de construire : il ne produit pas de
 * candidat portefeuille et ne suppose aucune route publique a notre charge.
 * Les futurs plans de chantier devront refaire les controles physiques. */
function OpexRoad100LongCorridorShadow(catalog, preliminary, limitOps = 250000)
{
  local result = { ok = false, reason = "OFF", siteA = -1, siteB = -1,
      monthly = 0, route = -1, ops = 0, tested = 0, fleet = 0,
      pred_profit = -1, pred_capital = -1, cash = -1,
      max_site_a = -1, max_site_b = -1, max_pair_monthly = -1,
      sites_a = 0, sites_b = 0, min_required_a = 80, min_required_b = 80,
      max_union_a = -1, max_union_b = -1,
      union_single_a = -1, union_single_b = -1,
      delta_single_a = -1, delta_single_b = -1,
      union_satellites_a = 0, union_satellites_b = 0,
      union_root_a = -1, union_root_b = -1,
      union_producers_a = 0, union_producers_b = 0,
      union_combos_a = 0, union_combos_b = 0,
      satellites_a = 0, satellites_b = 0,
      join_validated = false,
      path_reason = "PATH_NOT_RUN", path_forward_reason = "NOT_RUN",
      path_reverse_reason = "NOT_RUN", path_forward = -1, path_reverse = -1,
      path_nodes = 0, path_forward_nodes = 0, path_reverse_nodes = 0,
      path_node_limit = 512, path_ops = 0, path_cost = -1,
      path_site_a = -1, path_site_b = -1,
      path_center_distance = -1, path_site_distance = -1 };
  if (!ROAD100_LONG_INTERCITY || catalog == null || preliminary == null)
    return result;
  if (limitOps < 45000 || limitOps > 250000) {
    result.reason = "OPCAP";
    return result;
  }
  local mark = OpexOpsMeasureBegin();
  result.reason = "PRECHECK";
  do {
    if (!("kind" in preliminary) || preliminary.kind != "pax"
        || !("srcTown" in preliminary) || !("dstTown" in preliminary)
        || preliminary.srcTown == preliminary.dstTown) break;
    local cargo = catalog.paxCargo;
    if (cargo < 0 || !(cargo in catalog.roadEngineByCargo)) break;
    local engine = catalog.roadEngineByCargo[cargo];
    if (engine == null || engine.capacity <= 0 || engine.speed <= 0) break;
    local stop = OpexRoadStopKind(cargo);
    if (stop.vehType != AIRoad.ROADVEHTYPE_BUS) break;
    local coverage = AIStation.GetCoverageRadius(stop.stationType);
    local excluded = OpexRoadOurBusTiles();
    local sitesA = OpexRoad100LongCheapSites(preliminary.src, preliminary.srcTown,
        cargo, coverage, preliminary.dst, excluded, mark, limitOps);
    if (sitesA == null || sitesA.len() == 0) {
      result.reason = OpexOpsMeasureEnd(mark) >= limitOps - 40000
          ? "OPCAP" : "SITE_A";
      break;
    }
    if (OpexOpsMeasureEnd(mark) >= limitOps) { result.reason = "OPCAP"; break; }
    local sitesB = OpexRoad100LongCheapSites(preliminary.dst, preliminary.dstTown,
        cargo, coverage, preliminary.src, excluded, mark, limitOps);
    if (sitesB == null || sitesB.len() == 0) {
      result.reason = OpexOpsMeasureEnd(mark) >= limitOps - 40000
          ? "OPCAP" : "SITE_B";
      break;
    }
    if (OpexOpsMeasureEnd(mark) >= limitOps) { result.reason = "OPCAP"; break; }
    result.sites_a = sitesA.len();
    result.sites_b = sitesB.len();
    /* Valeurs natives d'UN SEUL arret, sans les confondre avec la
     * station supply AAA multi-stop du linkgraph. On telemetre le maximum
     * avant le seuil, pour montrer les vrais refus LOW_DEMAND. */
    foreach (probeSiteA in sitesA) {
      if (probeSiteA.value > result.max_site_a)
        result.max_site_a = probeSiteA.value;
    }
    foreach (probeSiteB in sitesB) {
      if (probeSiteB.value > result.max_site_b)
        result.max_site_b = probeSiteB.value;
    }
    result.max_pair_monthly = result.max_site_a + result.max_site_b;
    /* v5b : mesurer la connectivite AVANT les deux unions de maisons.
     * La v5 mesurait ~140k ops d'union+scan avant le PATH_ONLY, puis
     * sautait toujours le BFS faute de marge. La sonde utilise le meme
     * budget cumule et n'autorise aucun projet ; si elle est couteuse,
     * les unions suivantes doivent refuser OPCAP normalement. */
    local path = OpexRoad100LongPathOnly(sitesA, sitesB, preliminary,
        mark, limitOps);
    result.path_reason = path.reason;
    result.path_forward_reason = path.forward_reason;
    result.path_reverse_reason = path.reverse_reason;
    result.path_forward = path.forward;
    result.path_reverse = path.reverse;
    result.path_nodes = path.nodes;
    result.path_forward_nodes = path.forward_nodes;
    result.path_reverse_nodes = path.reverse_nodes;
    result.path_node_limit = path.node_limit;
    result.path_ops = path.ops;
    result.path_cost = path.cost;
    result.path_site_a = path.siteA;
    result.path_site_b = path.siteB;
    result.path_center_distance = path.center_distance;
    result.path_site_distance = path.site_distance;
    /* Une meme StationID peut comporter 1 racine + 2 satellites par ville.
     * Les quatre sites testables par ville sont communs a l'union et aux
     * comparaisons single, avec un seul Valuate 1x1 par extremite.
     * Preparer les gares Opex existantes de TOUS les modes : leur bassin
     * interdit d'inventer une demande supplementaire dans le shadow. */
    if (OpexOpsMeasureEnd(mark) >= limitOps - 40000) { result.reason = "OPCAP"; break; }
    local stationSpread = AIGameSettings.GetValue("station.station_spread");
    if (stationSpread < 2) { result.reason = "SPREAD"; break; }
    local ownCoverage = AITileList();
    local ownStations = AIStationList(AIStation.STATION_ANY);
    for (local stationId = ownStations.Begin(); !ownStations.IsEnd();
        stationId = ownStations.Next()) {
      if (OpexOpsMeasureEnd(mark) >= limitOps - 40000) { result.reason = "OPCAP"; break; }
      ownCoverage.AddList(AITileList_StationCoverage(stationId));
    }
    if (result.reason == "OPCAP") break;
    local unionA = OpexRoad100LongUnionEnd(sitesA, cargo, coverage,
        stationSpread, ownCoverage, mark, limitOps);
    if (!unionA.measured) { result.reason = unionA.reason; break; }
    local unionB = OpexRoad100LongUnionEnd(sitesB, cargo, coverage,
        stationSpread, ownCoverage, mark, limitOps);
    if (!unionB.measured) { result.reason = unionB.reason; break; }
    result.max_union_a = unionA.max_union;
    result.max_union_b = unionB.max_union;
    result.union_single_a = unionA.max_single;
    result.union_single_b = unionB.max_single;
    result.delta_single_a = unionA.delta_single;
    result.delta_single_b = unionB.delta_single;
    result.union_satellites_a = unionA.satellites;
    result.union_satellites_b = unionB.satellites;
    result.union_root_a = unionA.root_tile;
    result.union_root_b = unionB.root_tile;
    result.union_producers_a = unionA.producer_tiles;
    result.union_producers_b = unionB.producer_tiles;
    result.union_combos_a = unionA.combos;
    result.union_combos_b = unionB.combos;
    if (OpexOpsMeasureEnd(mark) >= limitOps) { result.reason = "OPCAP"; break; }
    local maxA = sitesA.len() < 2 ? sitesA.len() : 2;
    local maxB = sitesB.len() < 2 ? sitesB.len() : 2;
    result.reason = "LOW_DEMAND";
    local bestProfit = -1;
    local startCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    result.cash = startCash;
    local effectiveSpeed = engine.speed * ROAD_SPEED_EFFICIENCY_PCT / 100;
    if (effectiveSpeed <= 0) { result.reason = "SPEED"; break; }
    local fleetGrid = [2, 4, 8, 12, 16, 24, 30];
    for (local a = 0; a < maxA; a++) {
      if (OpexOpsMeasureEnd(mark) >= limitOps) { result.reason = "OPCAP"; break; }
      for (local b = 0; b < maxB; b++) {
        if (OpexOpsMeasureEnd(mark) >= limitOps) { result.reason = "OPCAP"; break; }
        local siteA = sitesA[a];
        local siteB = sitesB[b];
        local measuredA = unionA.roots[a];
        local measuredB = unionB.roots[b];
        local supply = measuredA.value + measuredB.value;
        /* Les seuils n'ont de sens qu'APRES l'union dedoublonnee et le
         * retrait des bassins Opex. L'AITest de chaque satellite isolement
         * ne valide jamais la jonction cumulative au StationID racine. */
        if (measuredA.value < 80 || measuredB.value < 80 || supply < 200)
          continue;
        result.reason = "NO_PATH";
        result.tested++;
        local distance = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
        if (distance < 80 || distance > 190) continue;
        local trace = OpexRoadBfsPath(siteA.tile, siteB.tile, 1024,
                                    siteA.front, siteB.front);
        if (trace == null || trace.len() > 190 || trace.len() < 80) continue;
        result.reason = "DEPOT";
        local depot = OpexRoadFindDepot(trace, siteA, siteB, true);
        if (depot == null) continue;
        local transitDays = trace.len() * 1000 / (36 * effectiveSpeed);
        if (transitDays < 1) transitDays = 1;
        local roundTripDays = 2 * (transitDays + ROAD_PAX_STOP_DWELL_DAYS);
        if (roundTripDays <= 0) continue;
        local fare = AICargo.GetCargoIncome(cargo, distance, transitDays);
        if (fare <= 0) { result.reason = "FARE"; continue; }
        result.reason = "ROI";
        /* Vrai service bidirectionnel, frequence par flotte N (et pas
         * rating(N=2) impose avant le cap30). Production et places bornent
         * chacune des deux sources ; revenus par passager livre UNE fois. */
        foreach (n in fleetGrid) {
          local headway = roundTripDays.tofloat() / n;
          local rating = OpexStationRatingForHeadway(headway);
          local visits = (30.0 * n) / roundTripDays;
          local maxPax = (visits * engine.capacity).tointeger();
          local fromA = (measuredA.value * rating / 100).tointeger();
          local fromB = (measuredB.value * rating / 100).tointeger();
          if (fromA > maxPax) fromA = maxPax;
          if (fromB > maxPax) fromB = maxPax;
          local carried = fromA + fromB;
          local annualRevenue = 12 * carried * fare;
          /* Seul le reseau de routes EXISTANT a ete certifie ici.
           * Provisionner le raccord depot (non paye encore), deux stops
           * et tous les bus avant le profit, sans financer par un proxy. */
          local stationCount = 2 + measuredA.satellites + measuredB.satellites;
          local infra = stationCount * catalog.costRoadBusStop + catalog.costRoadDepot
              + 2 * catalog.costRoadPerTile;
          local capital = infra + n * engine.price;
          if (startCash < capital + 50000) continue;
          local life = engine.ageYears > 0 ? engine.ageYears : 12;
          local amort = n * engine.price / life
              + (infra * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS;
          local annualProfit = annualRevenue - n * engine.runningCost - amort;
          if (annualProfit > bestProfit) {
            bestProfit = annualProfit;
            result.siteA = siteA.tile;
            result.siteB = siteB.tile;
            result.monthly = supply;
            result.route = trace.len();
            result.fleet = n;
            result.pred_profit = annualProfit;
            result.pred_capital = capital;
            result.satellites_a = measuredA.satellites;
            result.satellites_b = measuredB.satellites;
          }
        }
      }
    }
    if (result.reason == "OPCAP") break;
    if (bestProfit > 0) {
      if (result.satellites_a > 0 || result.satellites_b > 0) {
        /* Impossible de certifier la station jointe en AITestMode : chaque
         * test individuel repart de la carte initiale. Ne pas exposer une
         * route hypothetique comme physiquement valide ou construisible. */
        result.ok = false;
        result.reason = "JOIN_UNVERIFIED";
      } else {
        result.ok = true;
        result.reason = "SHADOW_OK";
      }
    } else if (result.pred_profit >= 0) {
      result.reason = "ROI";
    }
  } while (false);
  if (DECISION_LOG) OpexDecide("ROAD100_LONG_PATH",
      "reason=" + result.path_reason + " main_reason=" + result.reason
      + " src=" + preliminary.src + " dst=" + preliminary.dst
      + " siteA=" + result.path_site_a + " siteB=" + result.path_site_b
      + " centre_dist=" + result.path_center_distance
      + " site_dist=" + result.path_site_distance
      + " forward_reason=" + result.path_forward_reason
      + " reverse_reason=" + result.path_reverse_reason
      + " route_forward=" + result.path_forward
      + " route_reverse=" + result.path_reverse
      + " nodes_forward=" + result.path_forward_nodes
      + " nodes_reverse=" + result.path_reverse_nodes
      + " nodes_total=" + result.path_nodes
      + " nodes_limit=" + result.path_node_limit
      + " existing_road_cost=" + result.path_cost
      + " path_ops=" + result.path_ops);
  result.ops = OpexOpsMeasureEnd(mark);
  return result;
}

function OpexRoadPlanPaxVoirie(candidate, catalog = null)
{
  local stop = OpexRoadStopKind(candidate.cargo);
  if (stop.vehType != AIRoad.ROADVEHTYPE_BUS) return null;
  local coverage = AIStation.GetCoverageRadius(stop.stationType);
  local exclude = OpexRoadOurBusTiles();
  if (("existingStops" in candidate) && candidate.existingStops != null) {
    foreach (t in candidate.existingStops) exclude.append(t);
  }
  local sitesA = OpexRoadPaxVoirieSites(candidate.src, candidate.srcTown, candidate.cargo,
                                        stop.vehType, coverage, candidate.dst, true, exclude);
  if (sitesA.len() == 0) {
    if (DECISION_LOG) OpexDecide("VOIRIE_PLAN", "fail=SITEA srcTown=" + candidate.srcTown
                                 + " dstTown=" + candidate.dstTown);
    return null;
  }
  local sitesB = OpexRoadPaxVoirieSites(candidate.dst, candidate.dstTown, candidate.cargo,
                                        stop.vehType, coverage, candidate.src, true, exclude);
  if (sitesB.len() == 0) {
    if (DECISION_LOG) OpexDecide("VOIRIE_PLAN", "fail=SITEB srcTown=" + candidate.srcTown + " dstTown=" + candidate.dstTown
                                 + " nA=" + sitesA.len());
    return null;
  }
  local minPair = ROAD_PAX_VOIRIE_MIN_PAIR;
  local pairs = [];
  local nClose = 0;
  foreach (siteA in sitesA) {
    foreach (siteB in sitesB) {
      if (siteA.tile == siteB.tile) continue;
      if (("road100MultiCatchment" in candidate) && candidate.road100MultiCatchment &&
          (OpexRoad100CatchmentOverlaps(siteA.tile, exclude, coverage) ||
           OpexRoad100CatchmentOverlaps(siteB.tile, exclude, coverage))) continue;
      local d = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
      if (d < minPair) { nClose++; continue; }
      pairs.append({ a = siteA, b = siteB, d = d });
    }
  }
  local siteFirst = ("road100SiteFirst" in candidate) && candidate.road100SiteFirst;
  if (siteFirst) {
    pairs.sort(OpexRoad100SortSitePair);
  } else {
    pairs.sort(function(x, y) {
      if (x.d < y.d) return -1;
      if (x.d > y.d) return 1;
      return 0;
    });
  }
  local nBfs = 0;
  local nBfsNoDepot = 0;
  local nL = 0;
  local nLNoDepot = 0;
  local viableSitePlans = 0;
  local financeRejected = 0;
  local unprofitable = 0;
  local bestSitePlan = null;
  local bestProfit = -1;
  local bestRoi = -1;
  foreach (pair in pairs) {
    /* ROAD100-7 : la ligne limite les plans chers aux liaisons voisines.
     * Au smoke v1 toutes les premières paires dépassaient 86 cases ;
     * 16 BFS échouaient avant le moindre essai de route en L. */
    if (siteFirst && pair.d > ROAD_MAX_TRACE_TILES) continue;
    local siteA = pair.a;
    local siteB = pair.b;
    local trace = OpexRoadBfsPath(siteA.tile, siteB.tile, ROAD_MAX_TRACE_TILES, siteA.front, siteB.front);
    local via = "L";
    local depot = null;
    if (trace != null) {
      nBfs++;
      depot = OpexRoadFindDepot(trace, siteA, siteB, true);
      if (depot == null) nBfsNoDepot++;
    }
    if (depot == null) {
      trace = null;
      local axisH = AIMap.GetTileX(siteA.front) != AIMap.GetTileX(siteA.tile);
      for (local k = 0; k < 2; k++) {
        local firstH = (k == 0) ? axisH : !axisH;
        local dx = AIMap.GetTileX(siteB.tile) - AIMap.GetTileX(siteA.tile);
        local dy = AIMap.GetTileY(siteB.tile) - AIMap.GetTileY(siteA.tile);
        /* Premier pas reel du L : s'il est perpendiculaire a l'axe DT, le bus ne sort pas. */
        local firstIsH = firstH ? (dx != 0) : (dy == 0);
        if (firstIsH != axisH) continue;
        local l = OpexRoadTrace(siteA.tile, siteB.tile, firstH);
        if (l.len() == 0 || l.len() > ROAD_MAX_TRACE_TILES) continue;
        if (!OpexRoadTraceBuildable(l)) continue;
        nL++;
        local dpt = OpexRoadFindDepot(l, siteA, siteB, true);
        if (dpt == null) { nLNoDepot++; continue; }
        trace = l;
        depot = dpt;
        break;
      }
    } else {
      via = "BFS";
    }
    if (trace == null || depot == null) continue;
    /* Au lieu du premier couple réalisable, comparer au maximum trois
     * variantes physiques, avec leur volume, leur coût et leur caisse réels.
     * Le chemin historique OFF retourne toujours immédiatement ci-dessous. */
    if (siteFirst) {
      viableSitePlans++;
      local monthly = siteA.value + siteB.value;
      local producerEstimateA = null;
      local producerEstimateB = null;
      if (ROAD100_PAX_PRODUCER_UNITS && candidate.kind == "pax") {
        /* GetCargoProduction retourne des PRODUCTEURS, pas des
         * PASS/mois : meme conversion C121/B9 AIR par part de
         * producteurs de cette ville, sans waiting d'adversaire. */
        producerEstimateA = OpexRoad100PaxSiteMonthly(
            candidate.srcTown, candidate.cargo, siteA.tile, coverage);
        producerEstimateB = OpexRoad100PaxSiteMonthly(
            candidate.dstTown, candidate.cargo, siteB.tile, coverage);
        monthly = producerEstimateA.monthly + producerEstimateB.monthly;
      }
      local routeDist = trace.len() > 0 ? trace.len() : 1;
      local finances = catalog != null
          ? OpexRoadLineEconomics(catalog, candidate.cargo, pair.d, monthly,
                                  candidate.engine, "pax", routeDist) : null;
      if (finances == null || finances.profitAnnual <= 0) {
        unprofitable++;
      } else {
        local need = OpexEstimFinanceCapital("road", finances.capital, pair.d,
                                             false, finances.immobilise);
        local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
        if (cash < need + 25000) {
          financeRejected++;
        } else if (bestSitePlan == null || finances.profitAnnual > bestProfit
                   || (finances.profitAnnual == bestProfit && finances.roi > bestRoi)) {
          bestProfit = finances.profitAnnual;
          bestRoi = finances.roi;
          bestSitePlan = { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
                           stationType = stop.stationType, vehType = stop.vehType,
                           routeDistance = routeDist, shape = 0, trials = viableSitePlans,
                           driveThrough = true };
          if (ROAD100_PAX_PRODUCER_UNITS && candidate.kind == "pax") {
            bestSitePlan.road100PaxUnitsMonthly <- monthly;
            bestSitePlan.road100PaxUnitA <- producerEstimateA;
            bestSitePlan.road100PaxUnitB <- producerEstimateB;
          }
        }
      }
      if (viableSitePlans >= 3) break;
      continue;
    }
    if (DECISION_LOG) {
      OpexDecide("VOIRIE_PLAN", "ok=1 via=" + via + " d=" + pair.d
                 + " route=" + (trace.len() > 0 ? trace.len() : 1)
                 + " nA=" + sitesA.len() + " nB=" + sitesB.len()
                 + " nClose=" + nClose);
    }
    return { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
             stationType = stop.stationType, vehType = stop.vehType,
             routeDistance = trace.len() > 0 ? trace.len() : 1,
             shape = 0, trials = 1, driveThrough = true };
  }
  /* ROAD100-13 : filet opt-in UNIQUEMENT apres l'echec de tous les plans BFS/L.
   * Ne jamais supplanter un trace historique viable, meme non rentable.
   * Les variantes 2..9 ont deux virages plats verifies par OpexRoadTraceMulti.
   * Deux couples et 250k opcodes supplementaires au maximum (borne souple :
   * une tentative indivisible peut terminer au-dela du seuil). */
  if (siteFirst && ROAD100_DETOUR && viableSitePlans == 0) {
    local detourAttempts = 0;
    local detourPairs = 0;
    local detourOk = 0;
    local detourOps = 0;
    local detourReason = "NO_PATH";
    foreach (pair in pairs) {
      if (detourPairs >= 2 || detourOps >= 250000) break;
      if (pair.d > ROAD_MAX_TRACE_TILES) continue;
      detourPairs++;
      local siteA = pair.a;
      local siteB = pair.b;
      for (local variant = 2; variant <= 9; variant++) {
        if (detourOps >= 250000) { detourReason = "OPCAP"; break; }
        local detourMark = OpexOpsMeasureBegin();
        detourAttempts++;
        local trace = OpexRoadTraceMulti(siteA.tile, siteB.tile, variant);
        local depot = null;
        local trialReason = "EMPTY";
        if (trace.len() > ROAD_MAX_TRACE_TILES) {
          trialReason = "LONG";
        } else if (trace.len() > 0) {
          local last = trace.len() - 1;
          /* Les arrets traversants sont sur le trace : imposer la sortie A
           * ET l'entree B dans leur axe routier, pas seulement la premiere. */
          if (trace[0].from != siteA.tile || trace[last].to != siteB.tile
              || !OpexRoadOnDtAxis(siteA.tile, siteA.front, trace[0].to)
              || !OpexRoadOnDtAxis(siteB.tile, siteB.front, trace[last].from)) {
            trialReason = "DT_AXIS";
          } else if (!OpexRoadTraceBuildable(trace)) {
            trialReason = "UNBUILDABLE";
          } else {
            depot = OpexRoadFindDepot(trace, siteA, siteB, true);
            trialReason = depot == null ? "DEPOT" : "OK";
          }
        }
        if (depot != null) {
          detourOk++;
          viableSitePlans++;
          local monthly = siteA.value + siteB.value;
          local routeDist = trace.len();
          local finances = catalog != null
              ? OpexRoadLineEconomics(catalog, candidate.cargo, pair.d, monthly,
                                      candidate.engine, "pax", routeDist) : null;
          if (finances == null || finances.profitAnnual <= 0) {
            unprofitable++;
            trialReason = "UNPROFITABLE";
          } else {
            local need = OpexEstimFinanceCapital("road", finances.capital, pair.d,
                                                 false, finances.immobilise);
            local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
            if (cash < need + 25000) {
              financeRejected++;
              trialReason = "CASH";
            } else if (bestSitePlan == null || finances.profitAnnual > bestProfit
                       || (finances.profitAnnual == bestProfit && finances.roi > bestRoi)) {
              bestProfit = finances.profitAnnual;
              bestRoi = finances.roi;
              bestSitePlan = { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
                               stationType = stop.stationType, vehType = stop.vehType,
                               routeDistance = routeDist, shape = variant,
                               trials = detourAttempts, driveThrough = true };
            }
          }
        }
        detourOps += OpexOpsMeasureEnd(detourMark);
        detourReason = trialReason;
      }
    }
    if (detourOps >= 250000 && bestSitePlan == null) detourReason = "OPCAP";
    if (bestSitePlan != null) detourReason = "OK";
    if (DECISION_LOG) OpexDecide("ROAD100_DETOUR",
        "src=" + candidate.src + " dst=" + candidate.dst
        + " attempts=" + detourAttempts + " pairs=" + detourPairs
        + " ok=" + detourOk + " ops=" + detourOps
        + " reason=" + detourReason);
  }
  if (siteFirst && bestSitePlan != null) {
    if (DECISION_LOG) OpexDecide("ROAD100_SITE_PICK",
        "src=" + candidate.src + " dst=" + candidate.dst
        + " viable=" + viableSitePlans + " finance_reject=" + financeRejected
        + " unprofitable=" + unprofitable + " monthly="
        + (bestSitePlan.stopA.value + bestSitePlan.stopB.value)
        + " profit=" + bestProfit + " roi=" + bestRoi
        + " siteA=" + bestSitePlan.stopA.tile + " siteB=" + bestSitePlan.stopB.tile
        + " route=" + bestSitePlan.routeDistance + " depot=" + bestSitePlan.depot.tile);
    return bestSitePlan;
  }
  if (DECISION_LOG) {
    local minD = (pairs.len() > 0) ? pairs[0].d : -1;
    OpexDecide("VOIRIE_PLAN", "fail=" +
               ((nBfs == 0 && nL == 0) ? "NO_PATH" : "DEPOT")
               + " nA=" + sitesA.len() + " nB=" + sitesB.len()
               + " nPairs=" + pairs.len() + " minD=" + minD + " nClose=" + nClose
               + " nBfs=" + nBfs + " nBfsNoDepot=" + nBfsNoDepot
               + " nL=" + nL + " nLNoDepot=" + nLNoDepot);
  }
  return null;
}

/* Plan concret d'UN candidat routier. Le candidat porte deja la paire, le cargo et le sens ; il
 * reste a trouver deux sites d'arret reels et un trace multi-variantes qui les relie. */
/* ROAD100-16 v6 : dessiner uniquement des corridors LONG independants de
 * l'existence d'une voirie continue. Dans les coordonnees (u,v), u suit
 * l'axe du quai A et v lui est perpendiculaire. Les deux quais DT imposent
 * respectivement le premier et le dernier segment. Les schemas alternent
 * les axes en 5 ou 6 segments (4 ou 5 coudes), sans le plafond historique
 * ROAD_MAX_TRACE_TILES. Aucun Pathfinder ni commande de construction ici. */
function OpexRoad100LongShapeTrace(siteA, siteB, variant)
{
  local aHorizontal = AIMap.GetTileY(siteA.tile) == AIMap.GetTileY(siteA.front);
  local bHorizontal = AIMap.GetTileY(siteB.tile) == AIMap.GetTileY(siteB.front);
  local au = aHorizontal ? AIMap.GetTileX(siteA.tile) : AIMap.GetTileY(siteA.tile);
  local av = aHorizontal ? AIMap.GetTileY(siteA.tile) : AIMap.GetTileX(siteA.tile);
  local bu = aHorizontal ? AIMap.GetTileX(siteB.tile) : AIMap.GetTileY(siteB.tile);
  local bv = aHorizontal ? AIMap.GetTileY(siteB.tile) : AIMap.GetTileX(siteB.tile);
  local sameAxis = aHorizontal == bHorizontal;
  local step = 2 + 2 * (variant % 3);
  local shift = (variant % 2 == 0 ? step : -step);
  local signU = bu >= au ? 1 : -1;
  local signV = bv >= av ? 1 : -1;
  local points = [];
  points.append([au, av]);
  if (sameAxis) {
    local middleV = (av + bv) / 2 + shift;
    if (middleV == av || middleV == bv) middleV += shift;
    points.append([au + signU * step, av]);
    points.append([au + signU * step, middleV]);
    points.append([bu - signU * step, middleV]);
    points.append([bu - signU * step, bv]);
  } else {
    /* En v6, les quais perpendiculaires exigent cinq vrais changements
     * de direction : U,V,U,V,U,V. */
    local middleU = (au + bu) / 2 + shift;
    if (middleU == au + signU * step || middleU == bu)
      middleU += signU * step;
    points.append([au + signU * step, av]);
    points.append([au + signU * step, av + signV * step]);
    points.append([middleU, av + signV * step]);
    points.append([middleU, bv - signV * step]);
    points.append([bu, bv - signV * step]);
  }
  points.append([bu, bv]);
  local tiles = [];
  local total = 0;
  for (local i = 0; i < points.len(); i++) {
    local u = points[i][0];
    local v = points[i][1];
    local x = aHorizontal ? u : v;
    local y = aHorizontal ? v : u;
    if (!OpexRoadInMap(x, y)) return null;
    tiles.append(AIMap.GetTileIndex(x, y));
    if (i > 0) {
      local segment = AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
      if (segment < 1 || segment > 190 - total) return null;
      total += segment;
    }
  }
  if (total < 80 || total > 190) return null;
  for (local i = 1; i + 1 < tiles.len(); i++) {
    /* Un coude porte deux axes de route : sur pente, les AITest isoles
     * peuvent passer mais la pose cumulative echoue. */
    if (!OpexRoadIsFlat(tiles[i])) return null;
  }
  local trace = [];
  for (local i = 1; i < tiles.len(); i++)
    OpexRoadAppendSegment(trace, tiles[i - 1], tiles[i]);
  if (trace.len() != total || trace.len() < 80 || trace.len() > 190) return null;
  if (trace[0].from != siteA.tile || trace[trace.len() - 1].to != siteB.tile
      || !OpexRoadOnDtAxis(siteA.tile, siteA.front, trace[0].to)
      || !OpexRoadOnDtAxis(siteB.tile, siteB.front,
          trace[trace.len() - 1].from)) return null;
  /* Proscrire les boucles et les croisements sur une meme tuile, y compris
   * lorsque des variantes font demi-tour sur un segment. */
  local visited = {};
  visited.rawset(siteA.tile, true);
  foreach (edge in trace) {
    if (edge.to in visited) return null;
    visited.rawset(edge.to, true);
  }
  return trace;
}

/* ROAD100-16 v7 : contourner une arête explicitement refusee sans lancer
 * Pathfinder ni augmenter 190/400k. Retirer une courte fenetre RECTILIGNE
 * autour du blocage, passer sur une voie parallele (1 a 3 tuiles), puis
 * revenir sur la voie initiale. Les deux quais et leurs axes ne bougent pas.
 * Un detour est un candidat a re-tester, jamais une preuve de constructibilite. */
function OpexRoad100LongDoglegTrace(original, blockedIndex, side, width, siteA, siteB)
{
  if (original == null || blockedIndex <= 1 ||
      blockedIndex >= original.len() - 2 || width < 1 || width > 3 ||
      (side != -1 && side != 1)) return null;
  local direction = original[blockedIndex].to - original[blockedIndex].from;
  if (direction == 0) return null;
  local begin = blockedIndex;
  local finish = blockedIndex;
  /* La fenetre est volontairement plus large que l'arete fautive : une
   * maison ou pente a plusieurs tuiles peut sinon boucher la sortie. */
  while (begin > 1 && blockedIndex - begin < 4 &&
      original[begin - 1].to - original[begin - 1].from == direction) begin--;
  while (finish + 2 < original.len() && finish - blockedIndex < 4 &&
      original[finish + 1].to - original[finish + 1].from == direction) finish++;
  if (finish - begin < 2) return null;
  local firstTile = original[begin].from;
  local lastTile = original[finish].to;
  local x0 = AIMap.GetTileX(firstTile);
  local y0 = AIMap.GetTileY(firstTile);
  local x1 = AIMap.GetTileX(lastTile);
  local y1 = AIMap.GetTileY(lastTile);
  if (x0 != x1 && y0 != y1) return null;
  local dx = x0 == x1 ? side * width : 0;
  local dy = y0 == y1 ? side * width : 0;
  if (!OpexRoadInMap(x0 + dx, y0 + dy) ||
      !OpexRoadInMap(x1 + dx, y1 + dy)) return null;
  local bypassA = AIMap.GetTileIndex(x0 + dx, y0 + dy);
  local bypassB = AIMap.GetTileIndex(x1 + dx, y1 + dy);
  /* Chaque coude cree par le dogleg doit etre plat, y compris les
   * raccords a une ancienne route. */
  if (!OpexRoadIsFlat(firstTile) || !OpexRoadIsFlat(bypassA) ||
      !OpexRoadIsFlat(bypassB) || !OpexRoadIsFlat(lastTile)) return null;
  local route = [];
  for (local i = 0; i < begin; i++) route.append(original[i]);
  OpexRoadAppendSegment(route, firstTile, bypassA);
  OpexRoadAppendSegment(route, bypassA, bypassB);
  OpexRoadAppendSegment(route, bypassB, lastTile);
  for (local i = finish + 1; i < original.len(); i++) route.append(original[i]);
  if (route.len() < 80 || route.len() > 190) return null;
  if (route[0].from != siteA.tile || route[route.len() - 1].to != siteB.tile ||
      !OpexRoadOnDtAxis(siteA.tile, siteA.front, route[0].to) ||
      !OpexRoadOnDtAxis(siteB.tile, siteB.front, route[route.len() - 1].from))
    return null;
  local visited = {};
  visited.rawset(route[0].from, true);
  local previousDir = 0;
  foreach (edge in route) {
    if (!AIMap.IsValidTile(edge.from) || !AIMap.IsValidTile(edge.to) ||
        AIMap.DistanceManhattan(edge.from, edge.to) != 1 ||
        edge.to in visited) return null;
    local currentDir = edge.to - edge.from;
    if (previousDir != 0 && currentDir != previousDir &&
        !OpexRoadIsFlat(edge.from)) return null;
    previousDir = currentDir;
    visited.rawset(edge.to, true);
  }
  return route;
}

/* ROAD100-16 v12 : A* optimiste, sans consultation NoAI des 4 voisins.
 * On ne suppose PAS qu'une case est constructible pour publier le plan :
 * VerifyTrace controle chaque arete avant tout chantier. Si un test echoue,
 * l'arete ou la case identifiee est bannie, puis la recherche recommence.
 * Une tuile de changement d'axe exige toujours OpexRoadIsFlat, mise en
 * cache entre les relances ; les deux quais imposent leurs axes DT.
 *
 * Le budget local reste 85k soft, 320 etats, 190 aretes ; le budget
 * global 400k est partage avec les scans et les tests de chantier. */
function OpexRoad100LongObstacleTrace(siteA, siteB, bannedEdges, bannedTiles,
                                     staticCache, mark, limitOps)
{
  local out = { trace = null, reason = "NO_PATH", nodes = 0,
      houses = 0, bans_hit = 0, ops = 0, progress = 0,
      ops32 = -1, ops64 = -1, ops128 = -1, cache_hits = 0,
      cache_misses = 0, edge_queries = 0, frontier_max = 0,
      optimistic = 0, flat_probes = 0 };
  local searchMark = OpexOpsMeasureBegin();
  local from = siteA.tile;
  local goal = siteB.tile;
  if (!AIMap.IsValidTile(from) || !AIMap.IsValidTile(goal) ||
      !AIRoad.IsRoadTile(from) || !AIRoad.IsRoadTile(goal)) {
    out.reason = "NO_ROAD";
    return out;
  }
  local mapW = AIMap.GetMapSizeX();
  local mapH = AIMap.GetMapSizeY();
  local ax = AIMap.GetTileX(from);
  local ay = AIMap.GetTileY(from);
  local gx = AIMap.GetTileX(goal);
  local gy = AIMap.GetTileY(goal);
  local startHorizontal = ay == AIMap.GetTileY(siteA.front);
  local goalHorizontal = gy == AIMap.GetTileY(siteB.front);
  local offsets = [1, -1, mapW, -mapW];
  local dx = [1, -1, 0, 0];
  local dy = [0, 0, 1, -1];
  local h0 = (ax >= gx ? ax - gx : gx - ax) +
             (ay >= gy ? ay - gy : gy - ay);
  local open = [{ tile = from, x = ax, y = ay, dir = 4, distance = 0,
      g = 0, f = h0 * 100, prevState = null }];
  local best = {};
  local closed = {};
  best.rawset(from * 5 + 4, 0);
  while (open.len() > 0 && out.nodes < 320) {
    /* Une seule mesure par paquet de quatre etats : l'ancienne version
     * mesurait jusqu'a cinq fois par noeud, outre les appels de carte. */
    if ((out.nodes % 4) == 0) {
      if (OpexOpsMeasureEnd(mark) >= limitOps - 45000) {
        out.reason = "OPCAP";
        break;
      }
      local spent = OpexOpsMeasureEnd(searchMark);
      if (spent >= 85000) {
        out.reason = "SEARCH_CAP";
        break;
      }
    }
    local pick = 0;
    for (local i = 1; i < open.len(); i++) {
      if (open[i].f < open[pick].f ||
          (open[i].f == open[pick].f &&
           open[i].tile < open[pick].tile)) pick = i;
    }
    local current = open[pick];
    open.remove(pick);
    local currentKey = current.tile * 5 + current.dir;
    if (currentKey in closed ||
        current.g != best[currentKey]) continue;
    closed.rawset(currentKey, true);
    out.nodes++;
    local hCurrent = (current.x >= gx ? current.x - gx : gx - current.x) +
                     (current.y >= gy ? current.y - gy : gy - current.y);
    local progressed = h0 - hCurrent;
    if (progressed > out.progress) out.progress = progressed;
    if (out.nodes == 32) out.ops32 = OpexOpsMeasureEnd(searchMark);
    if (out.nodes == 64) out.ops64 = OpexOpsMeasureEnd(searchMark);
    if (out.nodes == 128) out.ops128 = OpexOpsMeasureEnd(searchMark);
    if (current.tile == goal) {
      local reverse = [];
      local visited = {};
      local cursor = current;
      while (cursor.prevState != null && reverse.len() < 191) {
        if (cursor.tile in visited) break;
        visited.rawset(cursor.tile, true);
        reverse.append({ from = cursor.prevState.tile, to = cursor.tile });
        cursor = cursor.prevState;
      }
      if (cursor.tile == from && reverse.len() >= 80 &&
          reverse.len() <= 190) {
        local trace = [];
        for (local r = reverse.len() - 1; r >= 0; r--)
          trace.append(reverse[r]);
        out.trace = trace;
        out.reason = "OK";
      } else {
        out.reason = "CYCLE";
      }
      break;
    }
    /* Ordre deterministe : d'abord l'axe principal vers le but,
     * puis l'autre axe gagnant, enfin les deux reculs necessaires
     * au contournement d'un obstacle. */
    local xp = current.x <= gx ? 0 : 1;
    local yp = current.y <= gy ? 2 : 3;
    local dirs = [xp, yp, 1 - xp, 5 - yp];
    /* Comparer les ecarts absolus, y compris vers l'ouest et le nord. */
    local deltaX = current.x >= gx ? current.x - gx : gx - current.x;
    local deltaY = current.y >= gy ? current.y - gy : gy - current.y;
    if (deltaX < deltaY) dirs = [yp, xp, 5 - yp, 1 - xp];
    else dirs = [xp, yp, 1 - xp, 5 - yp];
    for (local di = 0; di < 4; di++) {
      local dir = dirs[di];
      local horizontal = dir < 2;
      if (current.dir == 4 && horizontal != startHorizontal) continue;
      if (current.dir != 4 && current.dir != dir) {
        local flat = false;
        if (current.tile in staticCache) {
          flat = staticCache[current.tile];
          out.cache_hits++;
        } else {
          flat = OpexRoadIsFlat(current.tile);
          staticCache.rawset(current.tile, flat);
          out.cache_misses++;
          out.flat_probes++;
        }
        if (!flat) continue;
      }
      local nx = current.x + dx[dir];
      local ny = current.y + dy[dir];
      if (nx < 0 || ny < 0 || nx >= mapW || ny >= mapH) continue;
      local nextTile = current.tile + offsets[dir];
      if (nextTile == from) continue;
      if (nextTile == goal && horizontal != goalHorizontal) continue;
      if (nextTile in bannedTiles ||
          ((current.tile * 4 + dir) in bannedEdges)) {
        out.bans_hit++;
        continue;
      }
      local nextDistance = current.distance + 1;
      local hx = nx >= gx ? nx - gx : gx - nx;
      local hy = ny >= gy ? ny - gy : gy - ny;
      local h = hx + hy;
      if (nextDistance + h > 190) continue;
      local key = nextTile * 5 + dir;
      if (key in closed) continue;
      /* Aucune interrogation IsRoadTile/IsBuildable/IsStationTile ni
       * AreRoadTilesConnected sur le front. Ce chemin est SPECULATIF. */
      local turn = current.dir != 4 && current.dir != dir;
      local g = current.g + 10 + (turn ? 3 : 0);
      if (key in best && g >= best[key]) continue;
      best.rawset(key, g);
      out.optimistic++;
      open.append({ tile = nextTile, x = nx, y = ny, dir = dir,
          distance = nextDistance, g = g, f = h * 100 + g,
          prevState = current });
    }
    if (open.len() > out.frontier_max) out.frontier_max = open.len();
  }
  if (out.trace == null && out.reason == "NO_PATH" && out.nodes >= 320)
    out.reason = "NODE_CAP";
  out.ops = OpexOpsMeasureEnd(searchMark);
  /* Les appels NoAI sont indivisibles : eviter de rendre un trajet si
   * sa recherche a depasse le budget partage au dernier paquet. */
  if (OpexOpsMeasureEnd(mark) >= limitOps - 45000) {
    out.trace = null;
    out.reason = "OPCAP";
  } else if (out.ops > 85000) {
    out.trace = null;
    out.reason = "SEARCH_CAP";
  }
  return out;
}

/* V13 : polyligne deterministe a 3-5 segments (2-4 coudes), sans
 * file de priorite, aucun voisin explore et aucun scan du terrain.
 * Variante 0 = corridor direct, variantes suivantes = coudes decales.
 * Le seul controle terrain avant VerifyTrace porte sur les coudes :
 * chaque point qui change d'axe doit etre plat. Une ligne sans
 * boucle ni arrete bannie est un CANDIDAT, jamais un plan publie. */
function OpexRoad100LongPolylineTrace(siteA, siteB, variant,
                                      bannedEdges, bannedTiles,
                                      mark, limitOps)
{
  local out = { trace = null, reason = "GEOMETRY", nodes = 0,
      houses = 0, bans_hit = 0, ops = 0, progress = 0,
      ops32 = -1, ops64 = -1, ops128 = -1, cache_hits = 0,
      cache_misses = 0, edge_queries = 0, frontier_max = 0,
      optimistic = 0, flat_probes = 0, segments = 0, bends = 0 };
  local searchMark = OpexOpsMeasureBegin();
  local aHorizontal = AIMap.GetTileY(siteA.tile) == AIMap.GetTileY(siteA.front);
  local bHorizontal = AIMap.GetTileY(siteB.tile) == AIMap.GetTileY(siteB.front);
  /* V16 : creer les deux premieres/dernieres aretes directement sur
   * les fronts routiers deja connectes, pas seulement sur leur axe.
   * Elles sont ajoutees aux deux extremites du trace et partagees
   * entre preflight, admission, hash et chantier transactionnel. */
  local au = aHorizontal ? AIMap.GetTileX(siteA.front) : AIMap.GetTileY(siteA.front);
  local av = aHorizontal ? AIMap.GetTileY(siteA.front) : AIMap.GetTileX(siteA.front);
  local bu = aHorizontal ? AIMap.GetTileX(siteB.front) : AIMap.GetTileY(siteB.front);
  local bv = aHorizontal ? AIMap.GetTileY(siteB.front) : AIMap.GetTileX(siteB.front);
  local su = bu >= au ? 1 : -1;
  local sv = bv >= av ? 1 : -1;
  local step = 2 + 2 * (variant % 3);
  local pts = [[au, av]];
  if (aHorizontal == bHorizontal) {
    if (av != bv) {
      local middleU = (au + bu) / 2;
      if (variant == 1) middleU = au + su * step;
      if (variant == 2) middleU = bu - su * step;
      if (middleU == au || middleU == bu) {
        middleU = au + (variant == 2 ? -step : step);
      }
      pts.append([middleU, av]);
      pts.append([middleU, bv]);
    } else {
      local firstU = au + su * step;
      local lastU = bu - su * step;
      if (firstU == lastU) lastU += su * 2;
      local middleV = av + (variant % 2 == 0 ? step : -step);
      pts.append([firstU, av]);
      pts.append([firstU, middleV]);
      pts.append([lastU, middleV]);
      pts.append([lastU, bv]);
    }
  } else {
    local firstU = au + su * step;
    local middleV = av + sv * step;
    if (variant == 2) {
      firstU = bu - su * step;
      middleV = bv - sv * step;
    }
    if (firstU == au || firstU == bu || middleV == av || middleV == bv) {
      out.reason = "DEGENERATE";
      out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
    pts.append([firstU, av]);
    pts.append([firstU, middleV]);
    pts.append([bu, middleV]);
  }
  pts.append([bu, bv]);
  out.segments = pts.len() + 1;
  out.bends = pts.len() - 2;
  local mapW = AIMap.GetMapSizeX();
  local mapH = AIMap.GetMapSizeY();
  local tiles = [];
  local total = 2; /* station A -> front A, puis front B -> station B */
  for (local i = 0; i < pts.len(); i++) {
    local x = aHorizontal ? pts[i][0] : pts[i][1];
    local y = aHorizontal ? pts[i][1] : pts[i][0];
    if (x < 0 || y < 0 || x >= mapW || y >= mapH) {
      out.reason = "BOUNDS";
      out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
    local tile = AIMap.GetTileIndex(x, y);
    if (i > 0) {
      local previous = pts[i - 1];
      local du = pts[i][0] - previous[0];
      local dv = pts[i][1] - previous[1];
      if ((du == 0 && dv == 0) || (du != 0 && dv != 0)) {
        out.reason = "SEGMENT";
        out.ops = OpexOpsMeasureEnd(searchMark);
        return out;
      }
      total += (du >= 0 ? du : -du) + (dv >= 0 ? dv : -dv);
    }
    if (i > 0 && i + 1 < pts.len()) {
      out.flat_probes++;
      if (!OpexRoadIsFlat(tile)) {
        out.reason = "CORNER_SLOPE";
        out.ops = OpexOpsMeasureEnd(searchMark);
        return out;
      }
    }
    tiles.append(tile);
  }
  if (total < 80 || total > 190) {
    out.reason = "LENGTH";
    out.ops = OpexOpsMeasureEnd(searchMark);
    return out;
  }
  local trace = [{ from = siteA.tile, to = siteA.front }];
  for (local j = 1; j < tiles.len(); j++) {
    local startTile = tiles[j - 1];
    local endTile = tiles[j];
    local delta = endTile - startTile;
    local alongU = pts[j][0] != pts[j - 1][0];
    local horizontal = aHorizontal ? alongU : !alongU;
    local stride = (delta > 0 ? 1 : -1) * (horizontal ? 1 : mapW);
    local count = delta / stride;
    local walk = startTile;
    for (local n = 0; n < count; n++) {
      local nextTile = walk + stride;
      local dir = stride == 1 ? 0 : stride == -1 ? 1 :
          stride == mapW ? 2 : 3;
      if (nextTile in bannedTiles || (walk * 4 + dir) in bannedEdges) {
        out.bans_hit++;
        out.reason = "BANNED";
        out.ops = OpexOpsMeasureEnd(searchMark);
        return out;
      }
      trace.append({ from = walk, to = nextTile });
      walk = nextTile;
    }
  }
  trace.append({ from = siteB.front, to = siteB.tile });
  if (trace.len() != total || trace.len() == 0 ||
      trace[0].to != siteA.front ||
      trace[trace.len() - 1].from != siteB.front ||
      !OpexRoadOnDtAxis(siteA.tile, siteA.front, trace[0].to) ||
      !OpexRoadOnDtAxis(siteB.tile, siteB.front,
          trace[trace.len() - 1].from)) {
    out.reason = "DT_AXIS";
    out.ops = OpexOpsMeasureEnd(searchMark);
    return out;
  }
  local seen = {};
  seen.rawset(siteA.tile, true);
  foreach (edge in trace) {
    if (edge.to in seen) {
      out.reason = "CYCLE";
      out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
    seen.rawset(edge.to, true);
  }
  out.trace = trace;
  out.nodes = out.segments;
  out.progress = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
  out.optimistic = trace.len();
  out.reason = "OK";
  out.ops = OpexOpsMeasureEnd(searchMark);
  if (out.ops > 85000 ||
      OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
    out.trace = null;
    out.reason = out.ops > 85000 ? "SEARCH_CAP" : "OPCAP";
  }
  return out;
}

/* ROAD100-19 : exploration LOCALE de la voirie, pas de la carte.
 * Une rue urbaine peut s'eloigner de 2-4 cases avant de retrouver la
 * direction de l'autre ville. Rechercher des branches de routes DEJA
 * connectees physiquement (dans les deux sens) avant de sortir sur un
 * chantier nouveau ; ne jamais explorer des cases constructibles via
 * A*. Au plus 18 etats de route developpes et huit pas depuis le front.
 * Selectionner parmi quatre bouts de route la sortie dont le PREMIER
 * pas a l'exterieur est utilisable selon une lecture statique. Ce
 * dernier predicat n'est PAS une preuve : VerifyTrace fait l'AITest.
 * Aucun nouveau build/ouvrage dans cette fonction. */
function OpexRoad100LongRoadSleeve(frontTile, targetTile, stopTile,
                                   roadCache, roadLinks, bannedEdges, bannedTiles,
                                   variant, mark, limitOps, searchMark)
{
  local out = { tiles = [frontTile], steps = 0, probes = 0,
      linked = 0, reason = "NO_MORE_ROAD", expanded = 0,
      branches = 0, away_steps = 0, exits_tested = 0,
      exits_viable = 0, exit_blocked = 0, exit_axis = -1,
      exit_score = -1, max_depth = 0 };
  local mapWidth = AIMap.GetMapSizeX();
  local mapHeight = AIMap.GetMapSizeY();
  local gx = AIMap.GetTileX(targetTile);
  local gy = AIMap.GetTileY(targetTile);
  local x0 = AIMap.GetTileX(frontTile);
  local y0 = AIMap.GetTileY(frontTile);
  local offsets = [1, -1, mapWidth, -mapWidth];
  local dx = [1, -1, 0, 0];
  local dy = [0, 0, 1, -1];
  local seen = {};
  seen.rawset(stopTile, true);
  seen.rawset(frontTile, true);
  local baseDistance = (x0 >= gx ? x0 - gx : gx - x0) +
      (y0 >= gy ? y0 - gy : gy - y0);
  local nodes = [{ tile = frontTile, x = x0, y = y0,
      depth = 0, prev_index = -1, last_step = frontTile - stopTile,
      branch = -1 }];
  local head = 0;
  while (head < nodes.len() && head < 18) {
    if (OpexOpsMeasureEnd(mark) >= limitOps - 60000 ||
        OpexOpsMeasureEnd(searchMark) >= 11000) {
      out.reason = "SLEEVE_BUDGET";
      break;
    }
    local current = nodes[head];
    head++;
    out.expanded++;
    if (current.depth >= 8) continue;
    local currentDist = (current.x >= gx ? current.x - gx : gx - current.x) +
        (current.y >= gy ? current.y - gy : gy - current.y);
    local childCount = 0;
    for (local dir = 0; dir < 4; dir++) {
      local nx = current.x + dx[dir];
      local ny = current.y + dy[dir];
      if (nx < 0 || ny < 0 || nx >= mapWidth || ny >= mapHeight) continue;
      local nextTile = current.tile + offsets[dir];
      if (nextTile in seen) continue;
      if (nextTile in bannedTiles ||
          (current.tile * 4 + dir) in bannedEdges) continue;
      local distance = (nx >= gx ? nx - gx : gx - nx) +
          (ny >= gy ? ny - gy : gy - ny);
      /* Autoriser jusqu'a +4 cases de recul dans la ville, mais pas
       * l'errance sur une route plus longue que la marge 190. */
      if (distance > baseDistance + 4) continue;
      local isRoad = false;
      if (nextTile in roadCache) {
        isRoad = roadCache[nextTile];
      } else {
        isRoad = AIRoad.IsRoadTile(nextTile);
        roadCache.rawset(nextTile, isRoad);
        out.probes++;
      }
      if (!isRoad || AIRoad.IsRoadStationTile(nextTile) ||
          AIRoad.IsRoadDepotTile(nextTile) ||
          AITile.IsStationTile(nextTile)) continue;
      local linkKey = current.tile * 4 + dir;
      local linked = false;
      if (linkKey in roadLinks) {
        linked = roadLinks[linkKey];
      } else {
        linked = AIRoad.AreRoadTilesConnected(current.tile, nextTile) &&
            AIRoad.AreRoadTilesConnected(nextTile, current.tile);
        roadLinks.rawset(linkKey, linked);
        out.probes++;
      }
      if (!linked) continue;
      out.linked++;
      seen.rawset(nextTile, true);
      childCount++;
      local nd = current.depth + 1;
      if (nd > out.max_depth) out.max_depth = nd;
      if (distance > currentDist) out.away_steps++;
      nodes.append({ tile = nextTile, x = nx, y = ny,
          depth = nd, prev_index = head - 1, last_step = offsets[dir],
          branch = current.depth == 0 ? dir : current.branch });
    }
    if (childCount > 1) out.branches += childCount - 1;
  }
  /* Quatre bouts de branche au maximum ; le test concerne seulement
   * leur raccord exterieur (IsBuildable ou connexion existante). Un
   * cul-de-sac urbain avec maison devant ne doit plus gagner parce
   * qu'il a la plus petite distance de Manhattan. */
  local candidates = [];
  for (local i = 0; i < nodes.len(); i++) {
    local node = nodes[i];
    local dist = (node.x >= gx ? node.x - gx : gx - node.x) +
        (node.y >= gy ? node.y - gy : gy - node.y);
    local score = dist * 8 - node.depth * (variant == 1 ? 5 : 3);
    if (variant == 2) score += (node.depth % 2) * 3;
    local sameBranch = 0;
    local worstAt = -1;
    for (local ci = 0; ci < candidates.len(); ci++) {
      if (nodes[candidates[ci].index].branch != node.branch) continue;
      sameBranch++;
      if (worstAt < 0 || candidates[ci].score > candidates[worstAt].score)
        worstAt = ci;
    }
    /* Conserver deux MEILLEURES sorties par branche, pas les deux
     * premieres rencontrees en BFS (qui ignoreraient les avenues
     * desservies apres plusieurs tuiles). */
    if (sameBranch >= 2) {
      if (score >= candidates[worstAt].score) continue;
      candidates.remove(worstAt);
    }
    local pos = 0;
    while (pos < candidates.len() &&
        (candidates[pos].score < score ||
         (candidates[pos].score == score &&
          candidates[pos].index < i))) pos++;
    if (pos >= 6) continue;
    candidates.insert(pos, { index = i, score = score });
    if (candidates.len() > 6) candidates.pop();
  }
  local bestIndex = 0;
  local bestScore = 999999;
  local chosenAxis = -1;
  for (local c = 0; c < candidates.len(); c++) {
    if (OpexOpsMeasureEnd(mark) >= limitOps - 55000 ||
        OpexOpsMeasureEnd(searchMark) >= 14500) {
      out.reason = "EXIT_BUDGET";
      break;
    }
    local node = nodes[candidates[c].index];
    local dirs = [];
    if (node.x != gx) dirs.append(node.x < gx ? 0 : 1);
    if (node.y != gy) dirs.append(node.y < gy ? 2 : 3);
    local viableAxis = -1;
    for (local d = 0; d < dirs.len(); d++) {
      local dir = dirs[d];
      local nx = node.x + dx[dir];
      local ny = node.y + dy[dir];
      if (nx < 0 || ny < 0 || nx >= mapWidth || ny >= mapHeight) continue;
      local tile = node.tile + offsets[dir];
      if (tile in bannedTiles ||
          (node.tile * 4 + dir) in bannedEdges) continue;
      out.exits_tested++;
      local existing = AIRoad.IsRoadTile(tile);
      local usable = false;
      if (existing) {
        usable = AIRoad.AreRoadTilesConnected(node.tile, tile) &&
            AIRoad.AreRoadTilesConnected(tile, node.tile);
      } else {
        usable = AITile.IsBuildable(tile);
      }
      /* Un virage deja physiquement connecte sur pente est utilisable
       * tel quel. La platitude n'est obligatoire que pour la pose d'un
       * NOUVEAU bit routier sur deux axes. */
      if (usable && !existing && node.last_step != offsets[dir] &&
          !OpexRoadIsFlat(node.tile)) usable = false;
      if (usable) {
        out.exits_viable++;
        viableAxis = dir < 2 ? 0 : 1;
        break;
      }
      out.exit_blocked++;
    }
    if (viableAxis < 0) continue;
    local score = candidates[c].score;
    if (score < bestScore) {
      bestScore = score;
      bestIndex = candidates[c].index;
      chosenAxis = viableAxis;
    }
  }
  if (chosenAxis < 0) {
    /* Pas de preuve statique de sortie : ne pas inventer de route.
     * Le constructeur peut tester un autre site A/B deja classe. */
    out.reason = "NO_VIABLE_EXIT";
    return out;
  }
  local backwards = [];
  local cursor = bestIndex;
  while (cursor >= 0) {
    backwards.append(nodes[cursor].tile);
    cursor = nodes[cursor].prev_index;
  }
  out.tiles = [];
  for (local i = backwards.len() - 1; i >= 0; i--)
    out.tiles.append(backwards[i]);
  out.steps = out.tiles.len() - 1;
  out.exit_axis = chosenAxis;
  out.exit_score = bestScore;
  out.reason = "EXIT_FOUND";
  return out;
}

/* ROAD100-18 : joindre deux MANCHONS de voirie reellement connectes
 * par une liaison courte choisie sur la topologie effective. Les coudes
 * de jonction se deplacent autour du milieu jusqu'a trouver un terrain
 * plat ; aucun chemin A* a 150+ noeuds, aucune grille de formes fixes.
 * Toute arête nouvelle reste conjecturale jusqu'a VerifyTrace AITest.
 * Le retour de ce helper est compatible avec le dispatcher LONG v17. */
function OpexRoad100LongAdaptiveTrace(siteA, siteB, variant,
                                      bannedEdges, bannedTiles,
                                      roadCache, roadLinks,
                                      mark, limitOps)
{
  local out = { trace = null, reason = "GEOMETRY", nodes = 0,
      houses = 0, bans_hit = 0, ops = 0, progress = 0,
      ops32 = -1, ops64 = -1, ops128 = -1, cache_hits = 0,
      cache_misses = 0, edge_queries = 0, frontier_max = 0,
      optimistic = 0, flat_probes = 0, segments = 0, bends = 0,
      road_steps = 0, road_probes = 0, road_links = 0,
      corner_trials = 0, road_saved = 0,
      road_expanded = 0, road_branches = 0, road_away = 0,
      exit_tests = 0, exit_viable = 0, exit_blocked = 0,
      exit_a_reason = "NOT_RUN", exit_b_reason = "NOT_RUN",
      exit_a_axis = -1, exit_b_axis = -1, road_max_depth = 0 };
  local searchMark = OpexOpsMeasureBegin();
  if (!AIRoad.IsRoadTile(siteA.front) || !AIRoad.IsRoadTile(siteB.front) ||
      !AIRoad.AreRoadTilesConnected(siteA.tile, siteA.front) ||
      !AIRoad.AreRoadTilesConnected(siteB.front, siteB.tile)) {
    out.reason = "FRONT_ROAD";
    return out;
  }
  local sleeveA = OpexRoad100LongRoadSleeve(siteA.front, siteB.tile,
      siteA.tile, roadCache, roadLinks, bannedEdges, bannedTiles,
      variant, mark, limitOps, OpexOpsMeasureBegin());
  local sleeveB = OpexRoad100LongRoadSleeve(siteB.front, siteA.tile,
      siteB.tile, roadCache, roadLinks, bannedEdges, bannedTiles,
      variant, mark, limitOps, OpexOpsMeasureBegin());
  out.road_steps = sleeveA.steps + sleeveB.steps;
  out.road_saved = out.road_steps + 2;
  out.road_probes = sleeveA.probes + sleeveB.probes;
  out.road_links = sleeveA.linked + sleeveB.linked;
  out.road_expanded = sleeveA.expanded + sleeveB.expanded;
  out.road_branches = sleeveA.branches + sleeveB.branches;
  out.road_away = sleeveA.away_steps + sleeveB.away_steps;
  out.exit_tests = sleeveA.exits_tested + sleeveB.exits_tested;
  out.exit_viable = sleeveA.exits_viable + sleeveB.exits_viable;
  out.exit_blocked = sleeveA.exit_blocked + sleeveB.exit_blocked;
  out.exit_a_reason = sleeveA.reason;
  out.exit_b_reason = sleeveB.reason;
  out.exit_a_axis = sleeveA.exit_axis;
  out.exit_b_axis = sleeveB.exit_axis;
  out.road_max_depth = sleeveA.max_depth > sleeveB.max_depth
      ? sleeveA.max_depth : sleeveB.max_depth;
  if (sleeveA.reason != "EXIT_FOUND" || sleeveB.reason != "EXIT_FOUND") {
    out.reason = sleeveA.reason != "EXIT_FOUND"
        ? "CITY_EXIT_A_" + sleeveA.reason : "CITY_EXIT_B_" + sleeveB.reason;
    out.ops = OpexOpsMeasureEnd(searchMark);
    if (out.ops > 85000) out.reason = "SEARCH_CAP";
    else if (OpexOpsMeasureEnd(mark) >= limitOps - 50000)
      out.reason = "OPCAP";
    return out;
  }
  local aTip = sleeveA.tiles[sleeveA.tiles.len() - 1];
  local bTip = sleeveB.tiles[sleeveB.tiles.len() - 1];
  local ax = AIMap.GetTileX(aTip);
  local ay = AIMap.GetTileY(aTip);
  local bx = AIMap.GetTileX(bTip);
  local by = AIMap.GetTileY(bTip);
  local mx = ax + (bx - ax) / 2;
  local my = ay + (by - ay) / 2;
  local mapWidth = AIMap.GetMapSizeX();
  local mapHeight = AIMap.GetMapSizeY();
  local offsets = [0, 2, -2, 4, -4, 6, -6, 8, -8, 1, -1];
  local points = null;
  local lastA = sleeveA.tiles.len() >= 2
      ? aTip - sleeveA.tiles[sleeveA.tiles.len() - 2]
      : siteA.front - siteA.tile;
  local lastB = sleeveB.tiles.len() >= 2
      ? sleeveB.tiles[sleeveB.tiles.len() - 2] - bTip
      : siteB.tile - siteB.front;
  /* Variante0 suit d'abord l'axe du manchon A ; variante1 l'autre,
   * variante2 choisit le premier axe mais les coudes les plus eloignes.
   * Les offsets sont des sondes de PLATITUDE, pas un template rigide. */
  /* Le premier segment nouveau suit l'axe d'EVASION inspecte sur la
   * tuile de sortie. Ne pas revenir sur la maison ERR260 voisine quand
   * une avenue reelle permet une sortie sur l'autre axe. Les variantes
   * modifient les routes parcourues, pas ce predicat de constructibilite. */
  local firstHorizontal = sleeveA.exit_axis == 0;
  if (ax == bx) firstHorizontal = false;
  if (ay == by) firstHorizontal = true;
  if (ax == bx || ay == by) {
    points = [[ax, ay], [bx, by]];
  } else {
    local startOffset = variant == 2 ? 5 : 0;
    for (local oi = startOffset; oi < offsets.len(); oi++) {
      if (OpexOpsMeasureEnd(searchMark) >= 75000 ||
          OpexOpsMeasureEnd(mark) >= limitOps - 50000) break;
      local mid = (firstHorizontal ? mx : my) + offsets[oi];
      local x1 = firstHorizontal ? mid : ax;
      local y1 = firstHorizontal ? ay : mid;
      local x2 = firstHorizontal ? mid : bx;
      local y2 = firstHorizontal ? by : mid;
      if (x1 < 0 || x2 < 0 || y1 < 0 || y2 < 0 ||
          x1 >= mapWidth || x2 >= mapWidth ||
          y1 >= mapHeight || y2 >= mapHeight ||
          (x1 == ax && y1 == ay) || (x2 == bx && y2 == by)) continue;
      local c1 = AIMap.GetTileIndex(x1, y1);
      local c2 = AIMap.GetTileIndex(x2, y2);
      out.corner_trials++;
      out.flat_probes += 2;
      if (!OpexRoadIsFlat(c1) || !OpexRoadIsFlat(c2)) continue;
      points = [[ax, ay], [x1, y1], [x2, y2], [bx, by]];
      break;
    }
  }
  if (points == null) {
    out.reason = "NO_FLAT_CORNERS";
    out.ops = OpexOpsMeasureEnd(searchMark);
    return out;
  }
  local trace = [{ from = siteA.tile, to = siteA.front }];
  for (local i = 1; i < sleeveA.tiles.len(); i++) {
    local fromTile = sleeveA.tiles[i - 1];
    local toTile = sleeveA.tiles[i];
    local diff = toTile - fromTile;
    local dir = diff == 1 ? 0 : diff == -1 ? 1 :
        diff == mapWidth ? 2 : 3;
    if (toTile in bannedTiles || (fromTile * 4 + dir) in bannedEdges) {
      out.reason = "BANNED_ROAD_A";
      out.bans_hit++;
      out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
    trace.append({ from = fromTile, to = toTile });
  }
  local bridge = [];
  for (local i = 1; i < points.len(); i++) {
    local x0 = points[i - 1][0];
    local y0 = points[i - 1][1];
    local x1 = points[i][0];
    local y1 = points[i][1];
    if ((x0 != x1 && y0 != y1) || (x0 == x1 && y0 == y1)) {
      out.reason = "BRIDGE_SEGMENT"; return out;
    }
    local direction = x0 != x1 ? (x1 > x0 ? 1 : -1) :
        (y1 > y0 ? mapWidth : -mapWidth);
    local distance = x0 != x1 ? (x1 > x0 ? x1 - x0 : x0 - x1)
        : (y1 > y0 ? y1 - y0 : y0 - y1);
    local tile = AIMap.GetTileIndex(x0, y0);
    for (local j = 0; j < distance; j++) {
      local nextTile = tile + direction;
      local idir = direction == 1 ? 0 : direction == -1 ? 1 :
          direction == mapWidth ? 2 : 3;
      if (nextTile in bannedTiles || (tile * 4 + idir) in bannedEdges) {
        out.bans_hit++;
        out.reason = "BANNED";
        out.ops = OpexOpsMeasureEnd(searchMark);
        return out;
      }
      bridge.append({ from = tile, to = nextTile });
      tile = nextTile;
    }
  }
  /* Changer d'axe sur une route existante non plate est valable seulement
   * si la nouvelle arête est deja reliee ; sinon il faut un virage plat. */
  if (bridge.len() > 0 && lastA != 0 &&
      lastA != bridge[0].to - bridge[0].from) {
    out.flat_probes++;
    if (!OpexRoadIsFlat(aTip)) {
      out.reason = "SLEEVE_A_TURN";
      out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
  }
  if (bridge.len() > 0 && lastB != 0 &&
      lastB != bridge[bridge.len() - 1].to -
          bridge[bridge.len() - 1].from) {
    out.flat_probes++;
    if (!OpexRoadIsFlat(bTip)) {
      out.reason = "SLEEVE_B_TURN";
      out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
  }
  foreach (edge in bridge) trace.append(edge);
  for (local k = sleeveB.tiles.len() - 1; k > 0; k--) {
    local fromTile = sleeveB.tiles[k];
    local toTile = sleeveB.tiles[k - 1];
    local diff = toTile - fromTile;
    local dir = diff == 1 ? 0 : diff == -1 ? 1 :
        diff == mapWidth ? 2 : 3;
    if (toTile in bannedTiles || (fromTile * 4 + dir) in bannedEdges) {
      out.reason = "BANNED_ROAD_B";
      out.bans_hit++;
      out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
    trace.append({ from = fromTile, to = toTile });
  }
  trace.append({ from = siteB.front, to = siteB.tile });
  if (trace.len() < 80 || trace.len() > 190) {
    out.reason = "LENGTH"; out.ops = OpexOpsMeasureEnd(searchMark);
    return out;
  }
  local visited = {};
  visited.rawset(siteA.tile, true);
  local previous = siteA.tile;
  foreach (edge in trace) {
    if (edge.from != previous || edge.to in visited) {
      out.reason = "CYCLE"; out.ops = OpexOpsMeasureEnd(searchMark);
      return out;
    }
    visited.rawset(edge.to, true);
    previous = edge.to;
  }
  if (previous != siteB.tile ||
      !OpexRoadOnDtAxis(siteA.tile, siteA.front, trace[0].to) ||
      !OpexRoadOnDtAxis(siteB.tile, siteB.front,
          trace[trace.len() - 1].from)) {
    out.reason = "DT_AXIS"; out.ops = OpexOpsMeasureEnd(searchMark);
    return out;
  }
  out.trace = trace;
  out.nodes = points.len();
  out.segments = points.len() - 1;
  out.bends = points.len() - 2;
  out.progress = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
  out.optimistic = trace.len();
  out.reason = "OK";
  out.ops = OpexOpsMeasureEnd(searchMark);
  if (out.ops > 85000 ||
      OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
    out.trace = null;
    out.reason = out.ops > 85000 ? "SEARCH_CAP" : "OPCAP";
  }
  return out;
}

/* ROAD100-32 : recherche locale d'un gap entre deux ancres physiques,
 * jamais un A* de bout en bout. Les tests AITest complets restent au
 * VerifyTrace, avant toute publication ou pose. */
function OpexRoad100SegmentedGap(source, target, occupied, mark, limitOps)
{
  local out = { tiles = null, nodes = 0, reason = "NO_PATH" };
  local lx = AIMap.GetTileX(source);
  local ly = AIMap.GetTileY(source);
  local rx = AIMap.GetTileX(target);
  local ry = AIMap.GetTileY(target);
  local minX = (lx < rx ? lx : rx) - 5;
  local minY = (ly < ry ? ly : ry) - 5;
  local maxX = (lx > rx ? lx : rx) + 5;
  local maxY = (ly > ry ? ly : ry) + 5;
  if (minX < 0) minX = 0;
  if (minY < 0) minY = 0;
  if (maxX >= AIMap.GetMapSizeX()) maxX = AIMap.GetMapSizeX() - 1;
  if (maxY >= AIMap.GetMapSizeY()) maxY = AIMap.GetMapSizeY() - 1;
  local w = AIMap.GetMapSizeX();
  local delta = [1, -1, w, -w];
  local frontier = [{ tile = source, cost = 0,
      score = 5 * AIMap.DistanceManhattan(source, target), prev = -1, closed = false }];
  local best = {};
  best.rawset(source, 0);
  for (local expansion = 0; expansion < 80; expansion++) {
    if (OpexOpsMeasureEnd(mark) >= limitOps - 55000) {
      out.reason = "OPCAP"; return out;
    }
    local idx = -1;
    for (local k = 0; k < frontier.len(); k++) {
      if (frontier[k].closed) continue;
      if (idx < 0 || frontier[k].score < frontier[idx].score)
        idx = k;
    }
    if (idx < 0) return out;
    local cur = frontier[idx];
    frontier[idx].closed = true;
    out.nodes++;
    if (cur.tile == target) {
      local reverse = [];
      local walk = idx;
      while (walk >= 0) {
        reverse.append(frontier[walk].tile);
        walk = frontier[walk].prev;
      }
      out.tiles = [];
      for (local back = reverse.len() - 1; back >= 0; back--)
        out.tiles.append(reverse[back]);
      out.reason = "OK";
      return out;
    }
    for (local d = 0; d < 4; d++) {
      local next = cur.tile + delta[d];
      if (!AIMap.IsValidTile(next) ||
          AIMap.DistanceManhattan(next, cur.tile) != 1) continue;
      local x = AIMap.GetTileX(next);
      local y = AIMap.GetTileY(next);
      if (x < minX || x > maxX || y < minY || y > maxY ||
          (next != target && next in occupied) ||
          AIRoad.IsRoadStationTile(next) ||
          AIRoad.IsRoadDepotTile(next) ||
          AITile.IsStationTile(next)) continue;
      local connected = AIRoad.AreRoadTilesConnected(cur.tile, next);
      if (!connected &&
          !(AIRoad.IsRoadTile(next) || AITile.IsBuildable(next)))
        continue;
      if (!connected && cur.prev >= 0 &&
          cur.tile - frontier[cur.prev].tile != next - cur.tile &&
          !OpexRoadIsFlat(cur.tile)) continue;
      local edgeCost = connected ? 1 : 5;
      local newCost = cur.cost + edgeCost;
      if (next in best && best[next] <= newCost) continue;
      best.rawset(next, newCost);
      frontier.append({ tile = next, cost = newCost,
          score = newCost + 5 * AIMap.DistanceManhattan(next, target),
          prev = idx, closed = false });
    }
  }
  out.reason = "NODE_CAP";
  return out;
}

/* ROAD100-32 : des micro-gaps 12..20 cases autour de quelques ancres
 * explicites. Une trace ne peut etre offerte a la construction que si
 * VerifyTrace, DepotPreflight et le devis integral existants passent.
 * Aucun bonus de capture ou de revenus n'est produit par ce traceur. */
function OpexRoad100LongSegmentedTrace(siteA, siteB, mark, limitOps)
{
  local out = { trace = null, reason = "PRECHECK", anchors = 0,
      nodes = 0, existing = 0, new_edges = 0, ops = 0 };
  local startMark = OpexOpsMeasureBegin();
  if (!AIRoad.AreRoadTilesConnected(siteA.tile, siteA.front) ||
      !AIRoad.AreRoadTilesConnected(siteB.front, siteB.tile)) {
    out.reason = "FRONT_LINK"; return out;
  }
  local sx = AIMap.GetTileX(siteA.front);
  local sy = AIMap.GetTileY(siteA.front);
  local ex = AIMap.GetTileX(siteB.front);
  local ey = AIMap.GetTileY(siteB.front);
  local span = AIMap.DistanceManhattan(siteA.front, siteB.front);
  local gaps = (span + 15) / 16;
  if (gaps < 2) gaps = 2;
  if (gaps > 12) { out.reason = "ANCHOR_CAP"; return out; }
  local visited = {};
  visited.rawset(siteA.tile, true);
  local path = [siteA.tile, siteA.front];
  visited.rawset(siteA.front, true);
  local current = siteA.front;
  for (local i = 1; i <= gaps; i++) {
    if (OpexOpsMeasureEnd(mark) >= limitOps - 55000) {
      out.reason = "OPCAP"; break;
    }
    local target = siteB.front;
    if (i < gaps) {
      local x0 = sx + ((ex - sx) * i) / gaps;
      local y0 = sy + ((ey - sy) * i) / gaps;
      local chosen = -1;
      local chosenScore = 999999;
      for (local ox = -2; ox <= 2; ox++) {
        for (local oy = -2; oy <= 2; oy++) {
          local x = x0 + ox;
          local y = y0 + oy;
          if (!OpexRoadInMap(x, y)) continue;
          local trial = AIMap.GetTileIndex(x, y);
          if (trial in visited ||
              AIRoad.IsRoadStationTile(trial) ||
              AIRoad.IsRoadDepotTile(trial) ||
              AITile.IsStationTile(trial) ||
              !(AIRoad.IsRoadTile(trial) || AITile.IsBuildable(trial)))
            continue;
          local score = (ox < 0 ? -ox : ox) + (oy < 0 ? -oy : oy);
          if (AIRoad.IsRoadTile(trial)) score -= 2;
          if (!OpexRoadIsFlat(trial)) score += 4;
          if (score < chosenScore) {
            chosen = trial;
            chosenScore = score;
          }
        }
      }
      if (chosen < 0) { out.reason = "NO_ANCHOR"; break; }
      target = chosen;
    }
    local gap = OpexRoad100SegmentedGap(current, target, visited,
        mark, limitOps);
    out.nodes += gap.nodes;
    if (gap.tiles == null) {
      out.reason = gap.reason == "OPCAP" ? "OPCAP" : "LOCAL_" + gap.reason;
      break;
    }
    out.anchors++;
    for (local j = 1; j < gap.tiles.len(); j++) {
      local tile = gap.tiles[j];
      if (tile in visited || path.len() >= 190) {
        out.reason = "CYCLE_OR_LENGTH"; break;
      }
      path.append(tile);
      visited.rawset(tile, true);
    }
    if (out.reason == "CYCLE_OR_LENGTH") break;
    current = target;
    if (i == gaps) out.reason = "OK";
  }
  if (out.reason == "OK") {
    if (siteB.tile in visited || path.len() >= 190) out.reason = "END_CYCLE";
    else {
      path.append(siteB.tile);
      if (path.len() - 1 < 80 || path.len() - 1 > 190 ||
          !OpexRoadOnDtAxis(siteA.tile, siteA.front, path[1]) ||
          !OpexRoadOnDtAxis(siteB.tile, siteB.front,
              path[path.len() - 2])) out.reason = "LENGTH_OR_AXIS";
      else {
        local trace = [];
        for (local t = 1; t < path.len(); t++) {
          local fromTile = path[t - 1];
          local toTile = path[t];
          trace.append({ from = fromTile, to = toTile });
          if (AIRoad.AreRoadTilesConnected(fromTile, toTile)) out.existing++;
          else out.new_edges++;
        }
        out.trace = trace;
      }
    }
  }
  out.ops = OpexOpsMeasureEnd(startMark);
  if (out.ops > 125000 || OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
    out.reason = "OPCAP";
    out.trace = null;
  }
  return out;
}

/* V13 : trois polylignes geometriques au plus pour une paire de sites.
 * Apres AITest refusant une arete, essayer un contournement local via
 * DoglegTrace, puis exclure l'arete pour la variante suivante. Aucune
 * exploration A* : le travail est proportionnel aux segments produits.
 * Jamais de publication sans VerifyTrace integralement reussi. */
function OpexRoad100LongObstacleVerified(siteA, siteB, mark, limitOps)
{
  local out = { trace = null, checked = null, reason = "NO_PATH",
      attempts = 0, nodes = 0, tests = 0, blocked = 0, houses = 0,
      bans = 0, bans_hit = 0, last_error = -1,
      last_from = -1, last_to = -1, first_blocked = null, ops = 0,
      progress = 0, ops32 = -1, ops64 = -1, ops128 = -1,
      cache_hits = 0, cache_misses = 0, edge_queries = 0,
      frontier_max = 0, optimistic = 0, flat_probes = 0,
      area_probes = 0, tile_bans = 0, last_ban_tile = -1,
      segments = 0, bends = 0, bypass_tries = 0, bypass_passes = 0,
      bypass_buildable = 0, last_bypass_reason = "NOT_RUN",
      geometry_rejects = 0, road_steps = 0, road_probes = 0,
      road_links = 0, corner_trials = 0, road_saved = 0,
      road_expanded = 0, road_branches = 0, road_away = 0,
      exit_tests = 0, exit_viable = 0, exit_blocked = 0,
      exit_a_reason = "NOT_RUN", exit_b_reason = "NOT_RUN",
      exit_a_axis = -1, exit_b_axis = -1, road_max_depth = 0 };
  local verifyMark = OpexOpsMeasureBegin();
  local bannedEdges = {};
  local bannedTiles = {};
  local roadCache = {};
  local roadLinks = {};
  for (local attempt = 0; attempt < 3; attempt++) {
    if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
      out.reason = "OPCAP";
      break;
    }
    out.attempts++;
    local search = OpexRoad100LongAdaptiveTrace(siteA, siteB, attempt,
        bannedEdges, bannedTiles, roadCache, roadLinks, mark, limitOps);
    out.nodes += search.nodes;
    out.houses += search.houses;
    out.bans_hit += search.bans_hit;
    if (search.progress > out.progress) out.progress = search.progress;
    if (out.ops32 < 0 && search.ops32 >= 0) out.ops32 = search.ops32;
    if (out.ops64 < 0 && search.ops64 >= 0) out.ops64 = search.ops64;
    if (out.ops128 < 0 && search.ops128 >= 0) out.ops128 = search.ops128;
    out.cache_hits += search.cache_hits;
    out.cache_misses += search.cache_misses;
    out.edge_queries += search.edge_queries;
    out.optimistic += search.optimistic;
    out.flat_probes += search.flat_probes;
    if (search.trace == null) out.geometry_rejects++;
    out.segments += search.segments;
    out.bends += search.bends;
    out.road_steps += search.road_steps;
    out.road_probes += search.road_probes;
    out.road_links += search.road_links;
    out.corner_trials += search.corner_trials;
    out.road_saved += search.road_saved;
    out.road_expanded += search.road_expanded;
    out.road_branches += search.road_branches;
    out.road_away += search.road_away;
    out.exit_tests += search.exit_tests;
    out.exit_viable += search.exit_viable;
    out.exit_blocked += search.exit_blocked;
    out.exit_a_reason = search.exit_a_reason;
    out.exit_b_reason = search.exit_b_reason;
    out.exit_a_axis = search.exit_a_axis;
    out.exit_b_axis = search.exit_b_axis;
    if (search.road_max_depth > out.road_max_depth)
      out.road_max_depth = search.road_max_depth;
    if (search.frontier_max > out.frontier_max)
      out.frontier_max = search.frontier_max;
    out.reason = search.reason;
    if (search.trace == null) {
      /* Pente, polyligne hors carte ou arête deja bannie ne condamnent
       * pas les deux autres schemas ; seul le budget termine l'essai. */
      if (search.reason == "OPCAP" || search.reason == "SEARCH_CAP") break;
      continue;
    }
    local checked = OpexRoad100LongVerifyTrace(search.trace, siteA, siteB,
        mark, limitOps);
    out.tests += checked.tested;
    if (checked.ok) {
      out.trace = search.trace;
      out.checked = checked;
      out.reason = "OK";
      break;
    }
    out.reason = checked.reason;
    if (out.first_blocked == null && checked.blocked_index >= 0)
      out.first_blocked = checked;
    /* Contournement uniquement autour du refus constate. Pas de test
     * BuildRoad sur les voisins, pas de BFS de la carte. Chaque dogleg
     * conserve les deux arrets et ne passe que si VerifyTrace confirme. */
    if (checked.blocked_index >= 0 && checked.reason != "OPCAP" &&
        (checked.blocked_stage == "AITEST_BUILD_ROAD" ||
         checked.blocked_stage == "OCCUPIED_STATION")) {
      local localPassed = false;
      for (local doglegWidth = 1; doglegWidth <= 3 && !localPassed;
           doglegWidth++) {
        for (local side = -1; side <= 1; side += 2) {
          if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
            out.reason = "OPCAP";
            break;
          }
          local bypass = OpexRoad100LongDoglegTrace(search.trace,
              checked.blocked_index, side, doglegWidth, siteA, siteB);
          if (bypass == null) continue;
          out.bypass_tries++;
          local retest = OpexRoad100LongVerifyTrace(bypass, siteA, siteB,
              mark, limitOps);
          out.tests += retest.tested;
          out.last_bypass_reason = retest.reason;
          if (retest.ok) {
            out.trace = bypass;
            out.checked = retest;
            out.reason = "OK";
            out.bypass_passes++;
            out.bypass_buildable++;
            localPassed = true;
            break;
          }
          if (retest.reason == "OPCAP") {
            out.reason = "OPCAP";
            break;
          }
        }
        if (out.reason == "OPCAP") break;
      }
      if (localPassed || out.reason == "OPCAP") break;
    }
    if (checked.blocked_index < 0 || checked.blocked_from < 0 ||
        checked.blocked_to < 0 || checked.reason == "OPCAP") break;
    if (out.first_blocked == null) out.first_blocked = checked;
    out.blocked++;
    out.last_error = checked.blocked_error;
    out.last_from = checked.blocked_from;
    out.last_to = checked.blocked_to;
    /* Encodage numerique (tile * 4 + dir) plutot que concatenation de
     * chaines pour chacune des ~4 expansions d'un noeud. Le trace est
     * cardinal et peut etre banni dans les deux sens sans appel NoAI. */
    local delta = checked.blocked_to - checked.blocked_from;
    local mapWidth = AIMap.GetMapSizeX();
    local blockedDir = delta == 1 ? 0 :
        delta == -1 ? 1 : delta == mapWidth ? 2 :
        delta == -mapWidth ? 3 : -1;
    if (blockedDir >= 0) {
      bannedEdges.rawset(checked.blocked_from * 4 + blockedDir, true);
      bannedEdges.rawset(checked.blocked_to * 4 +
          (blockedDir % 2 == 0 ? blockedDir + 1 : blockedDir - 1), true);
      out.bans++;
    } else {
      /* Invariant brise : ne pas reexplorer indefiniment le meme trace. */
      out.reason = "BAD_EDGE";
      break;
    }
    local blockedTile = -1;
    if (checked.blocked_stage == "OCCUPIED_STATION") {
      /* VerifyTrace identifie l'arete, pas lequel de ses deux bouts porte
       * la station. On ne bannit que la case localement verifiee. */
      if (checked.blocked_from != siteA.tile &&
          checked.blocked_from != siteB.tile &&
          (AIRoad.IsRoadStationTile(checked.blocked_from) ||
           AIRoad.IsRoadDepotTile(checked.blocked_from) ||
           AITile.IsStationTile(checked.blocked_from)))
        blockedTile = checked.blocked_from;
      else if (checked.blocked_to != siteA.tile &&
          checked.blocked_to != siteB.tile &&
          (AIRoad.IsRoadStationTile(checked.blocked_to) ||
           AIRoad.IsRoadDepotTile(checked.blocked_to) ||
           AITile.IsStationTile(checked.blocked_to)))
        blockedTile = checked.blocked_to;
    } else if (checked.blocked_stage == "AITEST_BUILD_ROAD" &&
               checked.blocked_error == 260) {
      /* ERR_AREA_NOT_CLEAR : inspecter SEULEMENT l'arete qui a echoue.
       * Une route existante peut etre non buildable sans etre un obstacle :
       * dans ce cas bannir l'arete, et non la tuile. */
      out.area_probes++;
      if (checked.blocked_to != siteB.tile &&
          !AIRoad.IsRoadTile(checked.blocked_to) &&
          !AITile.IsBuildable(checked.blocked_to))
        blockedTile = checked.blocked_to;
      else if (checked.blocked_from != siteA.tile &&
          !AIRoad.IsRoadTile(checked.blocked_from) &&
          !AITile.IsBuildable(checked.blocked_from))
        blockedTile = checked.blocked_from;
    } else if (checked.blocked_stage == "AITEST_BUILD_ROAD" &&
               checked.blocked_error == AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD) {
      /* Erreur 0x501 : ne jamais demolir ou forcer une voie municipale.
       * Cette liaison ne peut prendre les bits du virage demands ; pour
       * un autre trace, l'arete est interdite dans les deux sens plus
       * haut. Une tuile urbaine etrangere n'est bannie que si elle est
       * l'obstacle local observe, sans condamner nos deux arrêts. */
      out.area_probes++;
      if (checked.blocked_to != siteB.tile &&
          AIRoad.IsRoadTile(checked.blocked_to) &&
          !AICompany.IsMine(AITile.GetOwner(checked.blocked_to)))
        blockedTile = checked.blocked_to;
      else if (checked.blocked_from != siteA.tile &&
          AIRoad.IsRoadTile(checked.blocked_from) &&
          !AICompany.IsMine(AITile.GetOwner(checked.blocked_from)))
        blockedTile = checked.blocked_from;
    }
    if (blockedTile >= 0 && !(blockedTile in bannedTiles)) {
      bannedTiles.rawset(blockedTile, true);
      out.tile_bans++;
      out.last_ban_tile = blockedTile;
      if (checked.blocked_error == 260) out.houses++;
    }
  }
  out.ops = OpexOpsMeasureEnd(verifyMark);
  return out;
}

/* Le constructeur historique pose chaque arete absente a son tour. Evaluer
 * TOUTES ces commandes sous AITest sans depenser un seul livre; le controle
 * des coudes plats et de la trace simple anticipe les conflits de fondations
 * que les tests d'aretes independants ne simulent pas cumulativement. */
function OpexRoad100LongVerifyTrace(trace, siteA, siteB, mark, limitOps)
{
  local out = { ok = false, reason = "UNBUILDABLE", missing = 0,
      tested = 0, existing = 0, blocked_index = -1,
      blocked_from = -1, blocked_to = -1, blocked_error = -1,
      blocked_stage = "NONE" };
  if (!ROAD100_PAX_GRAPH_BRIDGE) {
    if (trace == null || trace.len() < 80 || trace.len() > 190) {
      out.reason = "LENGTH";
      return out;
    }
  } else if (trace == null || trace.len() < 43 || trace.len() > 190) {
    out.reason = "LENGTH";
    return out;
  }
  if (!AIRoad.IsRoadTile(siteA.tile) || !AIRoad.IsRoadTile(siteB.tile)) {
    out.reason = "SITE_ROAD";
    return out;
  }
  for (local edgeIndex = 0; edgeIndex < trace.len(); edgeIndex++) {
    local edge = trace[edgeIndex];
    if (OpexOpsMeasureEnd(mark) >= limitOps - 20000) {
      out.reason = "OPCAP";
      out.blocked_stage = "OPCODE_GUARD";
      return out;
    }
    /* Deux arrets traversants ne peuvent etre traverses par le corridor
     * qu'a leurs extremites, aucun arret tiers/depot sur la trace. */
    if ((edge.to != siteA.tile && edge.to != siteB.tile &&
         (AIRoad.IsRoadStationTile(edge.to) || AIRoad.IsRoadDepotTile(edge.to)
          || AITile.IsStationTile(edge.to))) ||
        (edge.from != siteA.tile && edge.from != siteB.tile &&
         (AIRoad.IsRoadStationTile(edge.from) || AIRoad.IsRoadDepotTile(edge.from)
          || AITile.IsStationTile(edge.from)))) {
      out.reason = "BLOCKED";
      out.blocked_stage = "OCCUPIED_STATION";
      out.blocked_index = edgeIndex;
      out.blocked_from = edge.from;
      out.blocked_to = edge.to;
      return out;
    }
    if (AIRoad.AreRoadTilesConnected(edge.from, edge.to)) {
      out.existing++;
      continue;
    }
    local allowed = false;
    local failure = -1;
    { local test = AITestMode();
      allowed = AIRoad.BuildRoad(edge.from, edge.to);
      if (!allowed) failure = AIError.GetLastError(); }
    out.tested++;
    out.missing++;
    if (!allowed) {
      out.blocked_stage = "AITEST_BUILD_ROAD";
      out.blocked_index = edgeIndex;
      out.blocked_from = edge.from;
      out.blocked_to = edge.to;
      out.blocked_error = failure;
      return out;
    }
  }
  out.ok = true;
  out.reason = "EDGES_TESTED";
  return out;
}

/* Depot sans appel non borne a OpexRoadFindDepot sur 190 aretes : maximum
 * 48 facades de route, non confondues avec le trace et hors des deux quais.
 * Le constructeur vrai refera BuildRoad + BuildRoadDepot dans cet ordre. */
function OpexRoad100LongDepotPreflight(trace, siteA, siteB, mark, limitOps)
{
  local occupied = {};
  foreach (edge in trace) {
    occupied.rawset(edge.from, true);
    occupied.rawset(edge.to, true);
  }
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local checked = {};
  local probes = 0;
  for (local i = 0; i < trace.len() && probes < 48; i += 2) {
    if (OpexOpsMeasureEnd(mark) >= limitOps - 20000) return null;
    local front = trace[i].from;
    if (front in checked) continue;
    checked.rawset(front, true);
    if (!AIRoad.IsRoadTile(front) || !OpexRoadIsFlat(front)
        || AIMap.DistanceManhattan(front, siteA.tile) < ROAD_DEPOT_MIN_STOP_DISTANCE
        || AIMap.DistanceManhattan(front, siteB.tile) < ROAD_DEPOT_MIN_STOP_DISTANCE)
      continue;
    local fx = AIMap.GetTileX(front);
    local fy = AIMap.GetTileY(front);
    foreach (offset in offsets) {
      if (OpexOpsMeasureEnd(mark) >= limitOps - 20000) return null;
      local x = fx + offset[0];
      local y = fy + offset[1];
      if (!OpexRoadInMap(x, y)) continue;
      local tile = AIMap.GetTileIndex(x, y);
      if (tile in occupied || !OpexRoadIsFlat(tile) ||
          AITile.IsStationTile(tile) || AIRoad.IsRoadDepotTile(tile)
          || AIRoad.IsRoadStationTile(tile)) continue;
      probes++;
      local allowed = false;
      { local test = AITestMode();
        allowed = AIRoad.BuildRoad(front, tile)
            && AIRoad.BuildRoadDepot(tile, front); }
      if (allowed) return { tile = tile, front = front };
      if (probes >= 48) break;
    }
  }
  return null;
}

/* ROAD100-33 : traceur creux d'origine distincte, uniquement appele sous
 * son propre opt-in. La verification et le chantier restent communs. */
require("road100_sparse_corridor.nut");
/* ROAD100-36 : charge uniquement les definitions, toutes les actions restent opt-in. */
require("road100_graph_bridge.nut");

/* ROAD100-36 opt-in: one real-front egress hint per root, never a route
 * feasibility claim. The caller uses it only to ORDER its same 3 site
 * pairs; all final road edges still go through LongVerifyTrace. A failed
 * or censored probe may not eliminate a candidate. Cache keys are bounded
 * tile*4+direction, with no path search or permanent state. */
function OpexRoad100GBFrontAccessScore(site, toward, mark, ceiling, cache)
{
  if (site == null || toward == null ||
      OpexOpsMeasureEnd(mark) >= ceiling) return -1;
  local sx = AIMap.GetTileX(site.front);
  local sy = AIMap.GetTileY(site.front);
  local dx = AIMap.GetTileX(toward.front) - sx;
  local dy = AIMap.GetTileY(toward.front) - sy;
  local ax = dx < 0 ? -dx : dx;
  local ay = dy < 0 ? -dy : dy;
  if (ax == 0 && ay == 0) return 0;
  local direction = ax >= ay ? (dx >= 0 ? 0 : 1)
      : (dy >= 0 ? 2 : 3);
  local key = site.front * 4 + direction;
  if (key in cache) return cache[key];
  local x = sx + (direction == 0 ? 1 : direction == 1 ? -1 : 0);
  local y = sy + (direction == 2 ? 1 : direction == 3 ? -1 : 0);
  local score = 0;
  if (OpexRoadInMap(x, y)) {
    local next = AIMap.GetTileIndex(x, y);
    if (next != site.tile && !AIRoad.IsRoadStationTile(next)
        && !AIRoad.IsRoadDepotTile(next) && !AITile.IsStationTile(next)) {
      if (AIRoad.AreRoadTilesConnected(site.front, next) &&
          AIRoad.AreRoadTilesConnected(next, site.front)) score = 2;
      else if (OpexOpsMeasureEnd(mark) < ceiling - 1200) {
        local allowed = false;
        { local test = AITestMode();
          allowed = AIRoad.BuildRoad(site.front, next); }
        if (allowed) score = 1;
      }
    }
  }
  cache.rawset(key, score);
  return score;
}

/* ROAD100-16 v6, inerte sans le futur dispatch road100LongBuild : DEUX
 * StationID et aucun satellite. Seul un plan entierement prequalifie peut
 * rejoindre OpexBuildRoadRoute. Son chantier revalide tous les raccords. */
function OpexRoad100LongConstructPlan(catalog, candidate, limitOps = 400000)
{
  if (!ROAD100_LONG_BUILD || !ROAD100_LONG_INTERCITY ||
      catalog == null || candidate == null ||
      !("road100LongBuild" in candidate) || !candidate.road100LongBuild)
    return null;
  /* Limite partagée avec la présélection et la paire précédente.
   * Un appel de revalidation au chantier dispose de 400k indépendants,
   * mais la génération transmet explicitement son reliquat. */
  if (limitOps < 65000 || limitOps > 400000) return null;
  /* ROAD100-35 : les deux couples utilisent exactement la meme borne
   * 180k d'opcodes, y compris lors d'une revalidation au chantier. */
  if (ROAD100_PORTAL_STITCH && limitOps > 180000) limitOps = 180000;
  if (ROAD100_PAX_GRAPH_BRIDGE && limitOps > 180000) limitOps = 180000;
  local mark = OpexOpsMeasureBegin();
  local reason = "PRECHECK";
  local pairsTested = 0;
  local trials = 0;
  local missing = -1;
  local routeLength = -1;
  local quoteRoad = -1;
  local quoteTotal = -1;
  local selectedPlan = null;
  local doglegAttempts = 0;
  local doglegBuildable = 0;
  local obstacleAttempts = 0;
  local obstacleNodes = 0;
  local obstacleTests = 0;
  local obstacleBlocked = 0;
  local obstacleHouses = 0;
  local obstacleBans = 0;
  local obstacleBansHit = 0;
  local obstacleLastError = -1;
  local obstacleLastFrom = -1;
  local obstacleLastTo = -1;
  local obstacleReason = "NOT_RUN";
  local obstacleOps = 0;
  local obstacleProgress = 0;
  local obstacleOps32 = -1;
  local obstacleOps64 = -1;
  local obstacleOps128 = -1;
  local obstacleCacheHits = 0;
  local obstacleCacheMisses = 0;
  local obstacleEdgeQueries = 0;
  local obstacleFrontier = 0;
  local obstacleOptimistic = 0;
  local obstacleFlatProbes = 0;
  local obstacleAreaProbes = 0;
  local obstacleTileBans = 0;
  local obstacleLastBanTile = -1;
  local obstacleSegments = 0;
  local obstacleBends = 0;
  local obstacleBypassTries = 0;
  local obstacleBypassPasses = 0;
  local obstacleBypassReason = "NOT_RUN";
  local obstacleGeometryRejects = 0;
  local obstacleRoadSteps = 0;
  local obstacleRoadProbes = 0;
  local obstacleRoadLinks = 0;
  local obstacleCornerTrials = 0;
  local obstacleRoadSaved = 0;
  local obstacleRoadExpanded = 0;
  local obstacleRoadBranches = 0;
  local obstacleRoadAway = 0;
  local obstacleExitTests = 0;
  local obstacleExitViable = 0;
  local obstacleExitBlocked = 0;
  local obstacleExitAReason = "NOT_RUN";
  local obstacleExitBReason = "NOT_RUN";
  local obstacleExitAAxis = -1;
  local obstacleExitBAxis = -1;
  local obstacleRoadDepth = 0;
  local segmentAttempts = 0;
  local segmentAnchors = 0;
  local segmentNodes = 0;
  local segmentExisting = 0;
  local segmentNewEdges = 0;
  local segmentOps = 0;
  local segmentReason = "OFF";
  local sparseAttempts = 0;
  local sparseOps = 0;
  local sparseReason = "OFF";
  local firstBlockedIndex = -1;
  local firstBlockedFrom = -1;
  local firstBlockedTo = -1;
  local firstBlockedError = -1;
  local firstBlockedReason = "NONE";
  local firstBlockedStage = "NONE";
  local firstBlockedShape = -1;
  local lastStage = "PRECHECK";
  local buildScanA = null;
  local buildScanB = null;
  local pairReasons = ["NOT_RUN", "NOT_RUN", "NOT_RUN"];
  do {
    if (!("kind" in candidate) || candidate.kind != "pax" ||
        !("cargo" in candidate) || candidate.cargo != catalog.paxCargo ||
        !("src" in candidate) || !("dst" in candidate) ||
        !("srcTown" in candidate) || !("dstTown" in candidate) ||
        !AIMap.IsValidTile(candidate.src) || !AIMap.IsValidTile(candidate.dst) ||
        !AITown.IsValidTown(candidate.srcTown) ||
        !AITown.IsValidTown(candidate.dstTown) ||
        candidate.srcTown < 0 || candidate.dstTown < 0 ||
        candidate.srcTown == candidate.dstTown ||
        !("engine" in candidate) || candidate.engine == null ||
        !("price" in candidate.engine) || candidate.engine.price <= 0 ||
        catalog.roadType < 0 || catalog.costRoadPerTile <= 0 ||
        catalog.costRoadBusStop <= 0 || catalog.costRoadDepot <= 0) break;
    /* Aucun SetCurrentRoadType hors AITest : le dispatcher doit choisir le
     * type routier avant d'appeler ce planificateur sans effet de bord. */
    if (AIRoad.GetCurrentRoadType() != catalog.roadType) {
      reason = "ROADTYPE"; break;
    }
    local centres = AIMap.DistanceManhattan(candidate.src, candidate.dst);
    if (centres < (ROAD100_PAX_GRAPH_BRIDGE ? 43 : 80) || centres > 170) {
      reason = "CENTRES"; break;
    }
    local stop = OpexRoadStopKind(candidate.cargo);
    if (stop.vehType != AIRoad.ROADVEHTYPE_BUS) { reason = "CARGO"; break; }
    local coverage = AIStation.GetCoverageRadius(stop.stationType);
    local excluded = OpexRoadOurBusTiles();
    /* v8 : build-only spatial scanner ; CheapSites reste exclusif au
     * shadow ancien. Chaque bout consomme au plus ~65k sur le meme mark. */
    buildScanA = OpexRoad100LongBuildSites(candidate.src, candidate.srcTown,
        candidate.cargo, coverage, candidate.dst, excluded, mark, limitOps,
        ROAD100_PORTAL_STITCH);
    if (ROAD100_PORTAL_STITCH && buildScanA.sites.len() == 0
        && buildScanA.reason != "OPCAP"
        && OpexOpsMeasureEnd(mark) < limitOps - 100000) {
      buildScanA = OpexRoad100LongBuildSites(candidate.src, candidate.srcTown,
          candidate.cargo, coverage, candidate.dst, excluded, mark, limitOps);
    }
    if (buildScanA.reason == "OPCAP" ||
        OpexOpsMeasureEnd(mark) >= limitOps - 90000) {
      reason = "OPCAP"; lastStage = "BUILD_SITE_A_OPCAP"; break;
    }
    local sitesA = buildScanA.sites;
    if (sitesA.len() == 0) { reason = "SITE_A"; lastStage = "BUILD_SITE_A"; break; }
    buildScanB = OpexRoad100LongBuildSites(candidate.dst, candidate.dstTown,
        candidate.cargo, coverage, candidate.src, excluded, mark, limitOps,
        ROAD100_PORTAL_STITCH);
    if (ROAD100_PORTAL_STITCH && buildScanB.sites.len() == 0
        && buildScanB.reason != "OPCAP"
        && OpexOpsMeasureEnd(mark) < limitOps - 100000) {
      buildScanB = OpexRoad100LongBuildSites(candidate.dst, candidate.dstTown,
          candidate.cargo, coverage, candidate.src, excluded, mark, limitOps);
    }
    if (buildScanB.reason == "OPCAP" ||
        OpexOpsMeasureEnd(mark) >= limitOps - 90000) {
      reason = "OPCAP"; lastStage = "BUILD_SITE_B_OPCAP"; break;
    }
    local sitesB = buildScanB.sites;
    if (sitesB.len() == 0) { reason = "SITE_B"; lastStage = "BUILD_SITE_B"; break; }
    /* Les sites sont deja evalues et tries. Un premier front urbain
     * condamne par ERR260 ne doit pas priver le candidat d'un troisieme
     * site admissible, si le meme budget commun le permet. */
    local shortlist = [];
    /* RAIL multi-source + AIR ranked-site principles, V36 only: rank
     * every physical station pair BEFORE dropping to three. The two-hop
     * connected-road score is not a forecast nor a route feasibility
     * check. Unknown/censored pairs remain eligible on proxy ties. */
    local graphSiteRankMark = ROAD100_PAX_GRAPH_BRIDGE ? OpexOpsMeasureBegin() : null;
    local graphSiteRankCache = ROAD100_PAX_GRAPH_BRIDGE ? OpexRoad100GBCache() : null;
    local graphSiteRankLimit = limitOps - 90000;
    if (ROAD100_PAX_GRAPH_BRIDGE) {
      local rankHardCap = OpexOpsMeasureEnd(mark) + 4000;
      if (rankHardCap < graphSiteRankLimit) graphSiteRankLimit = rankHardCap;
    }
    local graphPairsRanked = 0;
    for (local a = 0; a < sitesA.len() && a < 4; a++) {
      for (local b = 0; b < sitesB.len() && b < 4; b++) {
        local dist = AIMap.DistanceManhattan(sitesA[a].tile, sitesB[b].tile);
        if (dist < (ROAD100_PAX_GRAPH_BRIDGE ? 43 : 80)
            || dist > 190) continue;
        local pair = { a = sitesA[a], b = sitesB[b],
            dist = dist, score = sitesA[a].value + sitesB[b].value };
        if (ROAD100_PAX_GRAPH_BRIDGE) {
          local outgoingA = OpexRoad100GBExistingExit(pair.a, pair.b,
              graphSiteRankCache, mark, graphSiteRankLimit);
          local outgoingB = OpexRoad100GBExistingExit(pair.b, pair.a,
              graphSiteRankCache, mark, graphSiteRankLimit);
          pair.graphRoadScore <- outgoingA < 0 || outgoingB < 0
              ? -1 : outgoingA + outgoingB;
          graphPairsRanked++;
        }
        local at = 0;
        while (at < shortlist.len()) {
          if (ROAD100_PAX_GRAPH_BRIDGE &&
              shortlist[at].graphRoadScore != pair.graphRoadScore) {
            if (shortlist[at].graphRoadScore > pair.graphRoadScore) {
              at++; continue;
            }
            break;
          }
          if (shortlist[at].score > pair.score ||
              (shortlist[at].score == pair.score &&
               shortlist[at].dist <= pair.dist)) {
            at++; continue;
          }
          break;
        }
        if (at >= 3) continue;
        shortlist.insert(at, pair);
        if (shortlist.len() > 3) shortlist.pop();
      }
    }
    if (ROAD100_PAX_GRAPH_BRIDGE && shortlist.len() > 1) {
      /* The already tested stops are not necessarily able to EXIT toward
       * the other town. Probe one adjacent physical edge per end and
       * reorder, never remove, the same shortlist. 6k shared opcode cap. */
      local exitMark = OpexOpsMeasureBegin();
      local exitCeiling = OpexOpsMeasureEnd(mark) + 6000;
      if (exitCeiling > limitOps - 80000) exitCeiling = limitOps - 80000;
      local exitCache = {};
      foreach (frontPair in shortlist) {
        local aExit = OpexRoad100GBFrontAccessScore(frontPair.a,
            frontPair.b, mark, exitCeiling, exitCache);
        local bExit = OpexRoad100GBFrontAccessScore(frontPair.b,
            frontPair.a, mark, exitCeiling, exitCache);
        frontPair.graphExitScore <- aExit < 0 || bExit < 0 ? -1 : aExit + bExit;
      }
      for (local i = 1; i < shortlist.len(); i++) {
        local j = i;
        while (j > 0 && shortlist[j].graphRoadScore ==
            shortlist[j - 1].graphRoadScore &&
            shortlist[j].graphExitScore > shortlist[j - 1].graphExitScore) {
          local swap = shortlist[j - 1];
          shortlist[j - 1] = shortlist[j];
          shortlist[j] = swap;
          j--;
        }
      }
      if (DECISION_LOG) {
        for (local i = 0; i < shortlist.len(); i++) {
          OpexDecide("ROAD100_GRAPH_SITE",
              "rank=" + i + " site_a=" + shortlist[i].a.tile
              + " site_b=" + shortlist[i].b.tile
              + " native_proxy=" + shortlist[i].score
              + " pre_top3_road=" + shortlist[i].graphRoadScore
              + " site_pairs=" + graphPairsRanked
              + " site_rank_ops=" + OpexOpsMeasureEnd(graphSiteRankMark)
              + " exit_score=" + shortlist[i].graphExitScore
              + " ops=" + OpexOpsMeasureEnd(exitMark));
        }
      }
    }
    /* ROAD100-34 SHADOW : les nombres natifs `site.value` sont des
     * PRODUCTEURS, pas des PASS/mois. Mesurer les seules racines AITest
     * de la shortlist AVANT de depenser les opcodes de trace. La mesure
     * utilise le helper mensuel V30a existant; aucun classement, devis,
     * chantier ou revenu ne peut dependre de ce SHADOW. Les recherches
     * gardent leur vrai budget partage (un probe peut etre censure). */
    if (ROAD100_LONG_MARKET_PROBE && shortlist.len() > 0) {
      local marketMark = OpexOpsMeasureBegin();
      local marketCacheA = {};
      local marketCacheB = {};
      local measurements = 0;
      local cacheHits = 0;
      for (local marketRank = 0; marketRank < shortlist.len(); marketRank++) {
        local marketPair = shortlist[marketRank];
        if (OpexOpsMeasureEnd(mark) >= limitOps - 100000) {
          if (DECISION_LOG) OpexDecide("ROAD100_LONG_MARKET",
              "phase=pretrace rank=" + marketRank
              + " reason=OPCAP pair_a=" + marketPair.a.tile
              + " pair_b=" + marketPair.b.tile
              + " measured=" + measurements
              + " ops=" + OpexOpsMeasureEnd(marketMark));
          break;
        }
        local rootA = null;
        if (marketPair.a.tile in marketCacheA) {
          rootA = marketCacheA[marketPair.a.tile];
          cacheHits++;
        } else {
          rootA = OpexRoad100PaxSiteMonthly(candidate.srcTown,
              candidate.cargo, marketPair.a.tile, coverage);
          marketCacheA.rawset(marketPair.a.tile, rootA);
          measurements++;
        }
        local rootB = null;
        if (marketPair.b.tile in marketCacheB) {
          rootB = marketCacheB[marketPair.b.tile];
          cacheHits++;
        } else {
          rootB = OpexRoad100PaxSiteMonthly(candidate.dstTown,
              candidate.cargo, marketPair.b.tile, coverage);
          marketCacheB.rawset(marketPair.b.tile, rootB);
          measurements++;
        }
        if (DECISION_LOG) OpexDecide("ROAD100_LONG_MARKET",
            "phase=pretrace rank=" + marketRank
            + " town_a=" + candidate.srcTown
            + " town_b=" + candidate.dstTown
            + " tile_a=" + marketPair.a.tile
            + " front_a=" + marketPair.a.front
            + " tile_b=" + marketPair.b.tile
            + " front_b=" + marketPair.b.front
            + " native_producers_a=" + marketPair.a.value
            + " native_producers_b=" + marketPair.b.value
            + " site_producers_a=" + rootA.siteProducers
            + " site_producers_b=" + rootB.siteProducers
            + " town_producers_a=" + rootA.townProducers
            + " town_producers_b=" + rootB.townProducers
            + " town_monthly_a=" + rootA.townMonthly
            + " town_monthly_b=" + rootB.townMonthly
            + " root_monthly_a=" + rootA.monthly
            + " root_monthly_b=" + rootB.monthly
            + " root_monthly_total=" + (rootA.monthly + rootB.monthly)
            + " measured=" + measurements
            + " cache_hits=" + cacheHits
            + " ops=" + OpexOpsMeasureEnd(marketMark));
      }
    }
    reason = "NO_PAIR";
    lastStage = "SITE_PAIR_RANK";
    foreach (pair in shortlist) {
      if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
        reason = "OPCAP"; break;
      }
      pairsTested++;
      /* Essayer le corridor a obstacles d'abord : les six templates
       * historiques restent une issue deterministe si cette recherche
       * bornee ne trouve pas de trajet complet. */
      /* -2 : ROAD100-33 sparse; -1 : ROAD100-32 dense; sept formes
       * historiques 0..6 strictement identiques si OFF. */
      for (local shape = (ROAD100_PAX_GRAPH_BRIDGE ? -3 :
               ROAD100_SPARSE_CORRIDOR ? -2 :
               ROAD100_SEGMENTED_CORRIDOR ? -1 : 0);
           shape < 7; shape++) {
        /* Aucune voie de secours sur les templates si GRAPH ne connecte pas. */
        if (ROAD100_PAX_GRAPH_BRIDGE && shape != -3) break;
        if (shape == -1 && !ROAD100_SEGMENTED_CORRIDOR) continue;
        if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
          reason = "OPCAP"; break;
        }
        trials++;
        local trace = null;
        local checked = null;
        if (shape == -3) {
          local fastCursor = 0;
          while (true) {
            local graph = OpexRoad100GraphBridgeTrace(pair.a, pair.b, mark, limitOps, fastCursor);
            trace = graph.trace;
            checked = null;
            if (DECISION_LOG) OpexDecide("ROAD100_GRAPH",
                "phase=trace reason=" + graph.reason
                + " ops=" + graph.ops
                + " route=" + (trace == null ? -1 : trace.len())
                + " total_ops=" + OpexOpsMeasureEnd(mark)
                + " site_a=" + pair.a.tile + " site_b=" + pair.b.tile);
            if (graph.reason == "OPCAP") {
              reason = "OPCAP"; lastStage = "GRAPH_OPCAP"; break;
            }
          /* Verify this speculative trace inside the V36-only dispatch,
           * before any portfolio admission. Preserve frozen V33 OFF hunks. */
          if (trace != null) {
            checked = OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,
                mark, limitOps);
            local graphFirstError = checked.blocked_error;
            local graphFirstIndex = checked.blocked_index;
            /* The rail pathfinder's heuristic/parent search is useful only
             * as a tiny repair of one physically rejected edge here. Do
             * not run a monolithic road A*, and never trust its geometry
             * until the common full-trace OpenTTD verifier succeeds. */
            if (!checked.ok && checked.blocked_stage == "AITEST_BUILD_ROAD"
                && checked.blocked_error == 260
                && checked.blocked_index >= 2
                && checked.blocked_index < 40
                && OpexOpsMeasureEnd(mark) < limitOps - 50000) {
              local graphRepair = OpexRoad100GBRepairLocal(trace,
                  checked.blocked_index, pair.a, pair.b, mark, limitOps);
              local repairRetest = null;
              if (graphRepair.trace != null &&
                  OpexOpsMeasureEnd(mark) < limitOps - 50000) {
                repairRetest = OpexRoad100LongVerifyTrace(graphRepair.trace,
                    pair.a, pair.b, mark, limitOps);
                if (repairRetest.ok) {
                  trace = graphRepair.trace;
                  checked = repairRetest;
                }
              }
              if (DECISION_LOG) OpexDecide("ROAD100_GRAPH",
                  "phase=local_repair reason=" + graphRepair.reason
                  + " candidate=" + (graphRepair.trace != null ? 1 : 0)
                  + " expanded=" + graphRepair.expanded
                  + " states=" + graphRepair.states
                  + " ops=" + graphRepair.ops
                  + " retest_ok=" + (repairRetest != null && repairRetest.ok ? 1 : 0)
                  + " retest_index=" + (repairRetest != null
                      ? repairRetest.blocked_index : -1)
                  + " retest_error=" + (repairRetest != null
                      ? repairRetest.blocked_error : -1)
                  + " first_index=" + graphFirstIndex
                  + " total_ops=" + OpexOpsMeasureEnd(mark));
            }
            local graphDetours = 0;
            local graphDetourLastError = -1;
            local graphDetourLastIndex = -1;
            /* V36 only: an early obstacle (area not clear or municipal
             * road) may need a short bounded detour after the real sleeve.
             * Never remove the town's road, never credit speculative
             * bits, and retest the FULL corridor under the same verifier. */
            if (!checked.ok && checked.blocked_stage == "AITEST_BUILD_ROAD"
                && (checked.blocked_error == 260 ||
                    checked.blocked_error ==
                        AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD)
                && checked.blocked_index >= 1
                && checked.blocked_index <= 20) {
              local originalGraphTrace = trace;
              /* The first two narrow widths both failed at index 3 in
               * seed 42. Prefer the widest local bypass before spending
               * the same shared reserve on narrower urban strips. */
              for (local graphWidth = 3; graphWidth >= 1 && !checked.ok;
                   graphWidth--) {
                for (local graphSide = 1; graphSide >= -1 && !checked.ok;
                     graphSide -= 2) {
                  if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) break;
                  local graphGeometry = { reason = "INIT" };
                  local graphAlternate = OpexRoad100GBFrontDoglegTrace(
                      originalGraphTrace, graphFirstIndex, graphSide,
                      graphWidth, pair.a, pair.b, graphGeometry);
                  if (graphAlternate == null) {
                    if (DECISION_LOG) OpexDecide("ROAD100_GRAPH",
                        "phase=detour_geometry width=" + graphWidth
                        + " side=" + graphSide
                        + " first_index=" + graphFirstIndex
                        + " reason=" + graphGeometry.reason
                        + " total_ops=" + OpexOpsMeasureEnd(mark));
                    continue;
                  }
                  graphDetours++;
                  local graphRetest = OpexRoad100LongVerifyTrace(
                      graphAlternate, pair.a, pair.b, mark, limitOps);
                  graphDetourLastIndex = graphRetest.blocked_index;
                  graphDetourLastError = graphRetest.blocked_error;
                  if (DECISION_LOG) OpexDecide("ROAD100_GRAPH",
                      "phase=detour width=" + graphWidth
                      + " side=" + graphSide
                      + " ok=" + (graphRetest.ok ? 1 : 0)
                      + " stage=" + graphRetest.blocked_stage
                      + " reason=" + graphRetest.reason
                      + " index=" + graphRetest.blocked_index
                      + " from=" + graphRetest.blocked_from
                      + " to=" + graphRetest.blocked_to
                      + " error=" + graphRetest.blocked_error
                      + " route=" + graphAlternate.len()
                      + " total_ops=" + OpexOpsMeasureEnd(mark));
                  if (graphRetest.ok) {
                    trace = graphAlternate;
                    checked = graphRetest;
                  }
                  if (graphRetest.reason == "OPCAP") break;
                }
              }
            }
            if (DECISION_LOG) OpexDecide("ROAD100_GRAPH",
                "phase=verify ok=" + (checked.ok ? 1 : 0)
                + " reason=" + checked.reason
                + " stage=" + checked.blocked_stage
                + " index=" + checked.blocked_index
                + " from=" + checked.blocked_from
                + " to=" + checked.blocked_to
                + " error=" + checked.blocked_error
                + " tested=" + checked.tested
                + " missing=" + checked.missing
                + " existing=" + checked.existing
                + " route=" + trace.len()
                + " first_error=" + graphFirstError
                + " first_index=" + graphFirstIndex
                + " town_road_error=" + AIRoad.ERR_ROAD_CANNOT_BUILD_ON_TOWN_ROAD
                + " limit_ops=" + limitOps
                + " detours=" + graphDetours
                + " detour_error=" + graphDetourLastError
                + " detour_index=" + graphDetourLastIndex
                + " site_a=" + pair.a.tile + " site_b=" + pair.b.tile
                + " total_ops=" + OpexOpsMeasureEnd(mark));
          }
            if (checked != null && checked.ok) {
              break;
            }
            if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
              reason = "OPCAP"; lastStage = "GRAPH_OPCAP"; break;
            }
            if (("nextFastCursor" in graph) && graph.nextFastCursor >= 0) {
              fastCursor = graph.nextFastCursor;
              trials++;
            } else if (("nextFastCursor" in graph) && graph.nextFastCursor == -1) {
              fastCursor = -1;
              trials++;
            } else {
              break;
            }
          }
          if (reason == "OPCAP") break;
        } else if (shape == -2) {
          local sparse = ROAD100_PORTAL_STITCH
              ? OpexRoad100PortalStitchTrace(pair.a, pair.b, mark, limitOps)
              : OpexRoad100SparseCorridorTrace(pair.a, pair.b, mark, limitOps);
          sparseAttempts++;
          sparseReason = sparse.reason;
          sparseOps += sparse.ops;
          trace = sparse.trace;
          if (DECISION_LOG) OpexDecide("ROAD100_SPARSE",
              "phase=preflight reason=" + sparse.reason
              + " route=" + (sparse.trace != null ? sparse.trace.len() : -1)
              + " ops=" + sparse.ops
              + " total_ops=" + OpexOpsMeasureEnd(mark));
          if (ROAD100_PORTAL_STITCH && DECISION_LOG) OpexDecide("ROAD100_PORTAL",
              "phase=preflight reason=" + sparse.reason
              + " detail=" + sparse.reason_detail
              + " first_reject=" + sparse.stats.first_reject
              + " portals_a=" + sparse.stats.portals_a
              + " portals_b=" + sparse.stats.portals_b
              + " expanded_a=" + sparse.stats.expanded_a
              + " expanded_b=" + sparse.stats.expanded_b
              + " road_links=" + sparse.stats.road_links
              + " portal_pairs=" + sparse.stats.portal_pairs
              + " bands=" + sparse.stats.bands
              + " alternatives=" + sparse.stats.alternatives
              + " cycles=" + sparse.stats.cycles
              + " route=" + (sparse.trace != null ? sparse.trace.len() : -1)
              + " ops=" + sparse.ops + " total_ops=" + OpexOpsMeasureEnd(mark)
              + " site_a=" + pair.a.tile + " front_a=" + pair.a.front
              + " site_b=" + pair.b.tile + " front_b=" + pair.b.front);
          if (sparse.reason == "OPCAP") {
            reason = "OPCAP"; lastStage = "SPARSE_OPCAP"; break;
          }
        } else if (shape == -1) {
          local segment = OpexRoad100LongSegmentedTrace(pair.a, pair.b,
              mark, limitOps);
          segmentAttempts++;
          segmentAnchors += segment.anchors;
          segmentNodes += segment.nodes;
          segmentExisting += segment.existing;
          segmentNewEdges += segment.new_edges;
          segmentOps += segment.ops;
          segmentReason = segment.reason;
          if (DECISION_LOG) OpexDecide("ROAD100_SEGMENTED",
              "phase=preflight anchors=" + segment.anchors
              + " nodes=" + segment.nodes
              + " existing=" + segment.existing
              + " new=" + segment.new_edges
              + " route=" + (segment.trace != null ? segment.trace.len() : -1)
              + " reason=" + segment.reason
              + " ops=" + segment.ops);
          trace = segment.trace;
          if (segment.reason == "OPCAP") {
            reason = "OPCAP"; lastStage = "SEGMENT_OPCAP"; break;
          }
        } else if (shape == 0) {
          local search = OpexRoad100LongObstacleVerified(pair.a, pair.b,
              mark, limitOps);
          obstacleAttempts += search.attempts;
          obstacleNodes += search.nodes;
          obstacleTests += search.tests;
          obstacleBlocked += search.blocked;
          obstacleHouses += search.houses;
          obstacleBans += search.bans;
          obstacleBansHit += search.bans_hit;
          obstacleLastError = search.last_error;
          obstacleLastFrom = search.last_from;
          obstacleLastTo = search.last_to;
          obstacleOps += search.ops;
          if (search.progress > obstacleProgress)
            obstacleProgress = search.progress;
          if (obstacleOps32 < 0 && search.ops32 >= 0)
            obstacleOps32 = search.ops32;
          if (obstacleOps64 < 0 && search.ops64 >= 0)
            obstacleOps64 = search.ops64;
          if (obstacleOps128 < 0 && search.ops128 >= 0)
            obstacleOps128 = search.ops128;
          obstacleCacheHits += search.cache_hits;
          obstacleCacheMisses += search.cache_misses;
          obstacleEdgeQueries += search.edge_queries;
          obstacleOptimistic += search.optimistic;
          obstacleFlatProbes += search.flat_probes;
          obstacleAreaProbes += search.area_probes;
          obstacleTileBans += search.tile_bans;
          obstacleSegments += search.segments;
          obstacleBends += search.bends;
          obstacleBypassTries += search.bypass_tries;
          obstacleBypassPasses += search.bypass_passes;
          obstacleGeometryRejects += search.geometry_rejects;
          obstacleRoadSteps += search.road_steps;
          obstacleRoadProbes += search.road_probes;
          obstacleRoadLinks += search.road_links;
          obstacleCornerTrials += search.corner_trials;
          obstacleRoadSaved += search.road_saved;
          obstacleRoadExpanded += search.road_expanded;
          obstacleRoadBranches += search.road_branches;
          obstacleRoadAway += search.road_away;
          obstacleExitTests += search.exit_tests;
          obstacleExitViable += search.exit_viable;
          obstacleExitBlocked += search.exit_blocked;
          obstacleExitAReason = search.exit_a_reason;
          obstacleExitBReason = search.exit_b_reason;
          obstacleExitAAxis = search.exit_a_axis;
          obstacleExitBAxis = search.exit_b_axis;
          if (search.road_max_depth > obstacleRoadDepth)
            obstacleRoadDepth = search.road_max_depth;
          if (search.last_bypass_reason != "NOT_RUN")
            obstacleBypassReason = search.last_bypass_reason;
          if (search.last_ban_tile >= 0)
            obstacleLastBanTile = search.last_ban_tile;
          if (search.frontier_max > obstacleFrontier)
            obstacleFrontier = search.frontier_max;
          obstacleReason = search.reason;
          trace = search.trace;
          checked = search.checked;
          if (search.first_blocked != null && firstBlockedIndex < 0) {
            firstBlockedIndex = search.first_blocked.blocked_index;
            firstBlockedFrom = search.first_blocked.blocked_from;
            firstBlockedTo = search.first_blocked.blocked_to;
            firstBlockedError = search.first_blocked.blocked_error;
            firstBlockedReason = search.first_blocked.reason;
            firstBlockedStage = search.first_blocked.blocked_stage;
            firstBlockedShape = 0;
          }
          if (search.reason == "OPCAP") {
            reason = "OPCAP";
            lastStage = "OBSTACLE_OPCAP";
            break;
          }
        } else {
          trace = OpexRoad100LongShapeTrace(pair.a, pair.b, shape - 1);
        }
        if (trace == null) {
          reason = shape == -3 ? "GRAPH_NO_TRACE" :
              shape == -2 ? sparseReason :
              shape == -1 ? segmentReason :
              shape == 0 ? obstacleReason : "GEOMETRY";
          lastStage = shape == -3 ? "GRAPH_SEARCH" :
              shape == -2 ? "SPARSE_SEARCH" :
              shape == -1 ? "SEGMENT_SEARCH" :
              shape == 0 ? "OBSTACLE_SEARCH" : "TEMPLATE_GEOMETRY";
          continue;
        }
        routeLength = trace.len();
        if (checked == null)
          checked = OpexRoad100LongVerifyTrace(trace, pair.a, pair.b,
              mark, limitOps);
        if (shape == -1 && DECISION_LOG) OpexDecide("ROAD100_SEGMENTED",
            "phase=verify ok=" + (checked.ok ? 1 : 0)
            + " reason=" + checked.reason
            + " missing=" + checked.missing
            + " existing=" + checked.existing
            + " first_fail=" + checked.blocked_index
            + " error=" + checked.blocked_error
            + " total_ops=" + OpexOpsMeasureEnd(mark));
        if (shape == -2 && DECISION_LOG) OpexDecide("ROAD100_SPARSE",
            "phase=verify ok=" + (checked.ok ? 1 : 0)
            + " reason=" + checked.reason
            + " missing=" + checked.missing
            + " existing=" + checked.existing
            + " first_fail=" + checked.blocked_index
            + " error=" + checked.blocked_error
            + " total_ops=" + OpexOpsMeasureEnd(mark));
        missing = checked.missing;
        if (!checked.ok) {
          reason = checked.reason;
          lastStage = checked.blocked_stage;
          if (checked.blocked_index >= 0 && firstBlockedIndex < 0) {
            firstBlockedIndex = checked.blocked_index;
            firstBlockedFrom = checked.blocked_from;
            firstBlockedTo = checked.blocked_to;
            firstBlockedError = checked.blocked_error;
            firstBlockedReason = checked.reason;
            firstBlockedStage = checked.blocked_stage;
            firstBlockedShape = shape;
          }
          if (reason == "OPCAP") break;
          /* v7 : le premier obstacle sur un segment rectiligne peut etre
           * contourne par des coudes plats. Au plus 12 doglegs pour les 2
           * paires, sans refaire les sites et sans modifier le plafond 190. */
          if (shape > 0 && (reason == "UNBUILDABLE" || reason == "BLOCKED") &&
              checked.blocked_index >= 0 && doglegAttempts < 12) {
            local widths = [1, 2, 3];
            for (local widthIndex = 0; widthIndex < widths.len(); widthIndex++) {
              if (doglegAttempts >= 12 || OpexOpsMeasureEnd(mark) >= limitOps - 50000)
                break;
              for (local sign = -1; sign <= 1; sign += 2) {
                if (doglegAttempts >= 12 || OpexOpsMeasureEnd(mark) >= limitOps - 50000)
                  break;
                local alternate = OpexRoad100LongDoglegTrace(trace,
                    checked.blocked_index, sign, widths[widthIndex], pair.a, pair.b);
                if (alternate == null) continue;
                doglegAttempts++;
                trials++;
                local retest = OpexRoad100LongVerifyTrace(alternate,
                    pair.a, pair.b, mark, limitOps);
                if (retest.ok) {
                  trace = alternate;
                  checked = retest;
                  routeLength = trace.len();
                  missing = retest.missing;
                  doglegBuildable++;
                  break;
                }
                reason = retest.reason;
                lastStage = retest.blocked_stage;
                if (reason == "OPCAP") break;
              }
              if (checked.ok || reason == "OPCAP") break;
            }
          }
          if (!checked.ok) {
            if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) reason = "OPCAP";
            if (reason == "OPCAP") break;
            continue;
          }
        }
        lastStage = "TRACE_VERIFIED";
        if (OpexOpsMeasureEnd(mark) >= limitOps - 50000) {
          reason = "OPCAP"; lastStage = "TRACE_BUDGET"; break;
        }
        /* Le quai DT ne fabrique pas les bits routiers de sa facade :
         * verifier qu'elle est DEJA liee au corps sur la bonne orientation,
         * independamment du trace futur, avant les deux AITest des quais. */
        if (!AIRoad.AreRoadTilesConnected(pair.a.tile, pair.a.front) ||
            !AIRoad.AreRoadTilesConnected(pair.b.tile, pair.b.front)) {
          reason = "STOP_LINK"; lastStage = "STATION_FRONT"; continue;
        }
        local allowedA = false;
        local allowedB = false;
        { local test = AITestMode();
          allowedA = AIRoad.BuildDriveThroughRoadStation(pair.a.tile,
              pair.a.front, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
          allowedB = AIRoad.BuildDriveThroughRoadStation(pair.b.tile,
              pair.b.front, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
        if (!allowedA || !allowedB) {
          reason = "STOP";
          lastStage = allowedA ? "STATION_B_TEST" : "STATION_A_TEST";
          continue;
        }
        local depot = OpexRoad100LongDepotPreflight(trace, pair.a, pair.b,
            mark, limitOps);
        if (OpexOpsMeasureEnd(mark) >= limitOps - 20000) {
          reason = "OPCAP"; lastStage = "DEPOT_BUDGET"; break;
        }
        if (depot == null) { reason = "DEPOT"; lastStage = "DEPOT_TEST"; continue; }
        /* Prix catalogue pour CHAQUE nouvelle arete, plus facteur 3 pour
         * les bits additionnels/terrain, deux quais, depot et son raccord.
         * Ajouter le prix de la flotte et une marge de 25 % + 50k liquide.
         * Ne jamais transformer cette prequalification en profit prevu. */
        quoteRoad = missing * catalog.costRoadPerTile * 3;
        local infrastructure = quoteRoad + 2 * catalog.costRoadBusStop
            + catalog.costRoadDepot + 3 * catalog.costRoadPerTile;
        local fleet = ("trains" in candidate) && candidate.trains > 0
            ? candidate.trains : 2;
        if (!OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, fleet)) {
          reason = "NOSLOT"; lastStage = "FINANCE_SLOT"; continue;
        }
        local capital = infrastructure + fleet * candidate.engine.price;
        if (("capital" in candidate) && candidate.capital > capital)
          capital = candidate.capital;
        if (("immobilise" in candidate) && candidate.immobilise > 0)
          capital += candidate.immobilise;
        quoteTotal = capital + capital / 4 + 50000;
        if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < quoteTotal) {
          reason = "CASH"; lastStage = "FINANCE_CASH"; continue;
        }
        selectedPlan = { stopA = pair.a, stopB = pair.b, trace = trace,
            depot = depot, stationType = stop.stationType,
            vehType = stop.vehType, routeDistance = trace.len(),
            driveThrough = true, shape = (shape == 0 ? 200 : 99 + shape),
            trials = trials,
            road100Segmented = shape == -1,
            road100Sparse = shape == -2,
            road100Graph = shape == -3 && ROAD100_PAX_GRAPH_BRIDGE,
            road100Portal = shape == -2 && ROAD100_PORTAL_STITCH,
            roadMissingCount = missing, roadQuoteCost = quoteRoad,
            road100LongCashNeed = quoteTotal, road100LongDepotChecked = true };
        reason = "OK";
        lastStage = "PLAN_READY";
        break;
      }
      if (selectedPlan != null || reason == "OPCAP") break;
      if (pairsTested > 0 && pairsTested <= 3) pairReasons[pairsTested - 1] = reason;
    }
    if (selectedPlan != null && pairsTested > 0 && pairsTested <= 3)
      pairReasons[pairsTested - 1] = "OK";
    if (reason == "OPCAP" && pairsTested > 0 && pairsTested <= 3)
      pairReasons[pairsTested - 1] = "OPCAP";
  } while (false);
  if (DECISION_LOG) OpexDecide("ROAD100_LONG_PLAN",
      "src=" + candidate.src + " dst=" + candidate.dst
      + " ok=" + (selectedPlan != null ? 1 : 0)
      + " reason=" + reason + " pairs=" + pairsTested
      + " trials=" + trials + " route=" + routeLength
      + " missing=" + missing + " road_quote=" + quoteRoad
      + " cash_need=" + quoteTotal + " ops=" + OpexOpsMeasureEnd(mark)
      + " stage=" + lastStage
      + " first_block_stage=" + firstBlockedStage
      + " first_block_reason=" + firstBlockedReason
      + " first_block_shape=" + firstBlockedShape
      + " first_block_index=" + firstBlockedIndex
      + " first_block_from=" + firstBlockedFrom
      + " first_block_to=" + firstBlockedTo
      + " first_block_error=" + firstBlockedError
      + " first_block_xy="
      + (firstBlockedFrom >= 0 ? AIMap.GetTileX(firstBlockedFrom) : -1)
      + "," + (firstBlockedFrom >= 0 ? AIMap.GetTileY(firstBlockedFrom) : -1)
      + ":" + (firstBlockedTo >= 0 ? AIMap.GetTileX(firstBlockedTo) : -1)
      + "," + (firstBlockedTo >= 0 ? AIMap.GetTileY(firstBlockedTo) : -1)
      + " dogleg_trials=" + doglegAttempts
      + " dogleg_edge_ok=" + doglegBuildable
      + " obstacle_attempts=" + obstacleAttempts
      + " obstacle_nodes=" + obstacleNodes
      + " obstacle_tests=" + obstacleTests
      + " obstacle_blocked=" + obstacleBlocked
      + " obstacle_houses=" + obstacleHouses
      + " obstacle_bans=" + obstacleBans
      + " obstacle_bans_hit=" + obstacleBansHit
      + " obstacle_last_error=" + obstacleLastError
      + " obstacle_last_from=" + obstacleLastFrom
      + " obstacle_last_to=" + obstacleLastTo
      + " obstacle_reason=" + obstacleReason
      + " obstacle_ops=" + obstacleOps
      + " obstacle_progress=" + obstacleProgress
      + " obstacle_ops32=" + obstacleOps32
      + " obstacle_ops64=" + obstacleOps64
      + " obstacle_ops128=" + obstacleOps128
      + " obstacle_cache_hit=" + obstacleCacheHits
      + " obstacle_cache_miss=" + obstacleCacheMisses
      + " obstacle_edge_queries=" + obstacleEdgeQueries
      + " obstacle_frontier=" + obstacleFrontier
      + " obstacle_optimistic=" + obstacleOptimistic
      + " obstacle_flat_probes=" + obstacleFlatProbes
      + " obstacle_area_probes=" + obstacleAreaProbes
      + " obstacle_tile_bans=" + obstacleTileBans
      + " obstacle_last_ban_tile=" + obstacleLastBanTile
      + " obstacle_segments=" + obstacleSegments
      + " obstacle_bends=" + obstacleBends
      + " obstacle_bypass_tries=" + obstacleBypassTries
      + " obstacle_bypass_passes=" + obstacleBypassPasses
      + " obstacle_bypass_reason=" + obstacleBypassReason
      + " obstacle_geometry_rejects=" + obstacleGeometryRejects
      + " obstacle_road_steps=" + obstacleRoadSteps
      + " obstacle_road_probes=" + obstacleRoadProbes
      + " obstacle_road_links=" + obstacleRoadLinks
      + " obstacle_corner_trials=" + obstacleCornerTrials
      + " obstacle_road_saved=" + obstacleRoadSaved
      + " obstacle_road_expanded=" + obstacleRoadExpanded
      + " obstacle_road_branches=" + obstacleRoadBranches
      + " obstacle_road_away=" + obstacleRoadAway
      + " obstacle_road_depth=" + obstacleRoadDepth
      + " segmented_attempts=" + segmentAttempts
      + " segmented_anchors=" + segmentAnchors
      + " segmented_nodes=" + segmentNodes
      + " segmented_existing=" + segmentExisting
      + " segmented_new=" + segmentNewEdges
      + " segmented_ops=" + segmentOps
      + " segmented_reason=" + segmentReason
      + " sparse_attempts=" + sparseAttempts
      + " sparse_ops=" + sparseOps
      + " sparse_reason=" + sparseReason
      + " obstacle_exit_tests=" + obstacleExitTests
      + " obstacle_exit_viable=" + obstacleExitViable
      + " obstacle_exit_blocked=" + obstacleExitBlocked
      + " obstacle_exit_a_reason=" + obstacleExitAReason
      + " obstacle_exit_b_reason=" + obstacleExitBReason
      + " obstacle_exit_a_axis=" + obstacleExitAAxis
      + " obstacle_exit_b_axis=" + obstacleExitBAxis
      + " pair0_reason=" + pairReasons[0]
      + " pair1_reason=" + pairReasons[1]
      + " pair2_reason=" + pairReasons[2]
      + " scan_a_reason=" + (buildScanA != null ? buildScanA.reason : "NA")
      + " scan_b_reason=" + (buildScanB != null ? buildScanB.reason : "NA")
      + " samples_a=" + (buildScanA != null ? buildScanA.samples : -1)
      + " samples_b=" + (buildScanB != null ? buildScanB.samples : -1)
      + " road_a=" + (buildScanA != null ? buildScanA.road : -1)
      + " road_b=" + (buildScanB != null ? buildScanB.road : -1)
      + " eligible_a=" + (buildScanA != null ? buildScanA.eligible : -1)
      + " eligible_b=" + (buildScanB != null ? buildScanB.eligible : -1)
      + " buckets_a=" + (buildScanA != null ? buildScanA.buckets : -1)
      + " buckets_b=" + (buildScanB != null ? buildScanB.buckets : -1)
      + " max_local_a=" + (buildScanA != null ? buildScanA.max_local : -1)
      + " max_local_b=" + (buildScanB != null ? buildScanB.max_local : -1)
      + " max_tested_a=" + (buildScanA != null ? buildScanA.max_tested : -1)
      + " max_tested_b=" + (buildScanB != null ? buildScanB.max_tested : -1)
      + " tests_a=" + (buildScanA != null ? buildScanA.tests : -1)
      + " tests_b=" + (buildScanB != null ? buildScanB.tests : -1)
      + " passed_a=" + (buildScanA != null ? buildScanA.passed : -1)
      + " passed_b=" + (buildScanB != null ? buildScanB.passed : -1)
      + " sites_a=" + (buildScanA != null ? buildScanA.sites.len() : -1)
      + " sites_b=" + (buildScanB != null ? buildScanB.sites.len() : -1)
      + " quadrants_a=" + (buildScanA != null ? buildScanA.quadrant_mask : -1)
      + " quadrants_b=" + (buildScanB != null ? buildScanB.quadrant_mask : -1)
      + " site_ops_a=" + (buildScanA != null ? buildScanA.ops : -1)
      + " site_ops_b=" + (buildScanB != null ? buildScanB.ops : -1));
  return selectedPlan;
}

/* ROAD100: revalidation directe du plan stocke (aretes, gares, depot, devis)
 * avant de relancer les scanners et la selection. Distingue invalidite physique,
 * derive de classement et manque de ressource. */
function OpexRoad100LongVerifyStoredPlan(catalog, candidate, storedPlan, limitOps = 400000)
{
  if (!ROAD100_LONG_BUILD || candidate == null || storedPlan == null ||
      !("kind" in candidate) || candidate.kind != "pax" ||
      !("stopA" in storedPlan) || storedPlan.stopA == null ||
      !("stopB" in storedPlan) || storedPlan.stopB == null ||
      !("trace" in storedPlan) || storedPlan.trace == null) {
    return { ok = false, reason = "LONG_SETTING", category = "resource" };
  }
  if (limitOps < 65000 || limitOps > 400000) limitOps = 400000;
  if (ROAD100_PORTAL_STITCH && limitOps > 180000) limitOps = 180000;
  if (ROAD100_PAX_GRAPH_BRIDGE && limitOps > 180000) limitOps = 180000;

  if (("road100GraphRequested" in candidate) && candidate.road100GraphRequested &&
      (!ROAD100_PAX_GRAPH_BRIDGE || !("road100Graph" in storedPlan) || !storedPlan.road100Graph)) {
    return { ok = false, reason = "GRAPH_DRIFT", category = "drift" };
  }
  if (("road100SegmentedUnits" in candidate) && candidate.road100SegmentedUnits &&
      (!ROAD100_SEGMENTED_CORRIDOR || !("road100Segmented" in storedPlan) || !storedPlan.road100Segmented)) {
    return { ok = false, reason = "SEGMENT_DRIFT", category = "drift" };
  }
  if (("road100SparseUnits" in candidate) && candidate.road100SparseUnits &&
      (!ROAD100_SPARSE_CORRIDOR || !("road100Sparse" in storedPlan) || !storedPlan.road100Sparse)) {
    return { ok = false, reason = "SPARSE_DRIFT", category = "drift" };
  }
  if (("road100PortalRequested" in candidate) && candidate.road100PortalRequested && !ROAD100_PORTAL_STITCH) {
    return { ok = false, reason = "PORTAL_SETTING", category = "resource" };
  }
  if (("road100PortalRequested" in candidate) && candidate.road100PortalRequested &&
      (("road100PortalUnits" in candidate) && candidate.road100PortalUnits) !=
      (("road100Portal" in storedPlan) && storedPlan.road100Portal)) {
    return { ok = false, reason = "PORTAL_DRIFT", category = "drift" };
  }

  local mark = OpexOpsMeasureBegin();

  /* 1. Gares : verification physique des extremites et facades */
  local stopA = storedPlan.stopA;
  local stopB = storedPlan.stopB;
  if (!AIRoad.IsRoadTile(stopA.tile) || !AIRoad.IsRoadTile(stopB.tile)) {
    return { ok = false, reason = "STATION_NOT_ROAD", category = "physical" };
  }
  if (!AIRoad.AreRoadTilesConnected(stopA.tile, stopA.front) ||
      !AIRoad.AreRoadTilesConnected(stopB.tile, stopB.front)) {
    return { ok = false, reason = "STATION_FRONT", category = "physical" };
  }
  local allowedA = false;
  local allowedB = false;
  {
    local test = AITestMode();
    allowedA = AIRoad.BuildDriveThroughRoadStation(stopA.tile, stopA.front,
        AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
    allowedB = AIRoad.BuildDriveThroughRoadStation(stopB.tile, stopB.front,
        AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
  }
  if (!allowedA || !allowedB) {
    return { ok = false, reason = "STATION_TEST", category = "physical" };
  }

  /* 2. Aretes : revalidation complete du trace */
  local checked = OpexRoad100LongVerifyTrace(storedPlan.trace, stopA, stopB, mark, limitOps);
  if (!checked.ok) {
    if (checked.reason == "OPCAP") {
      return { ok = false, reason = "OPCAP", category = "resource" };
    }
    return { ok = false, reason = "TRACE_" + checked.reason, category = "physical" };
  }
  local missing = checked.missing;

  /* 3. Depot : verification du depot stocke ou preflight de repli */
  local depot = null;
  if (("depot" in storedPlan) && storedPlan.depot != null &&
      ("tile" in storedPlan.depot) && ("front" in storedPlan.depot)) {
    local dt = storedPlan.depot.tile;
    local df = storedPlan.depot.front;
    if (AIRoad.IsRoadTile(df) && OpexRoadIsFlat(dt) &&
        !AITile.IsStationTile(dt) && !AIRoad.IsRoadDepotTile(dt) && !AIRoad.IsRoadStationTile(dt) &&
        AIMap.DistanceManhattan(df, stopA.tile) >= ROAD_DEPOT_MIN_STOP_DISTANCE &&
        AIMap.DistanceManhattan(df, stopB.tile) >= ROAD_DEPOT_MIN_STOP_DISTANCE) {
      local allowed = false;
      {
        local test = AITestMode();
        allowed = AIRoad.BuildRoad(df, dt) && AIRoad.BuildRoadDepot(dt, df);
      }
      if (allowed) depot = storedPlan.depot;
    }
  }
  if (depot == null) {
    depot = OpexRoad100LongDepotPreflight(storedPlan.trace, stopA, stopB, mark, limitOps);
  }
  if (OpexOpsMeasureEnd(mark) >= limitOps - 20000) {
    return { ok = false, reason = "OPCAP", category = "resource" };
  }
  if (depot == null) {
    return { ok = false, reason = "DEPOT_TEST", category = "physical" };
  }

  /* 4. Devis et ressources : devis infrastructure, slots et tresorerie */
  local quoteRoad = missing * catalog.costRoadPerTile * 3;
  if (("road100GenRoadQuote" in candidate) && quoteRoad > candidate.road100GenRoadQuote) {
    return { ok = false, reason = "QUOTE_EXCEEDED", category = "drift" };
  }
  local infrastructure = quoteRoad + 2 * catalog.costRoadBusStop
      + catalog.costRoadDepot + 3 * catalog.costRoadPerTile;
  local fleet = ("trains" in candidate) && candidate.trains > 0
      ? candidate.trains : 2;
  if (!OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, fleet)) {
    return { ok = false, reason = "NOSLOT", category = "resource" };
  }
  local capital = infrastructure + fleet * candidate.engine.price;
  if (("capital" in candidate) && candidate.capital > capital)
    capital = candidate.capital;
  if (("immobilise" in candidate) && candidate.immobilise > 0)
    capital += candidate.immobilise;
  local quoteTotal = capital + capital / 4 + 50000;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < quoteTotal) {
    return { ok = false, reason = "CASH", category = "resource" };
  }

  /* Plan valide et pret pour la pose */
  storedPlan.depot = depot;
  storedPlan.roadMissingCount = missing;
  storedPlan.roadQuoteCost = quoteRoad;
  storedPlan.road100LongCashNeed = quoteTotal;
  return { ok = true, plan = storedPlan, reason = "OK", category = "ok" };
}

function OpexRoadPlanFor(catalog, candidate)
{
  return OpexRoadPlanForActive(catalog, candidate);
}

/* La liste added ne contient que les aretes dont la connexion n'existait pas avant notre appel.
 * Le rollback ne supprime donc jamais une route de ville preexistante. */
function OpexRoadRollback(stopA, stopB, depot, vehicles, added, satellites = null)
{
  local allSold = true;
  if (vehicles != null) {
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (!AIVehicle.IsStoppedInDepot(v)) {
        AIVehicle.StartStopVehicle(v);
      }
      if (AIVehicle.IsStoppedInDepot(v)) {
        if (!AIVehicle.SellVehicle(v)) allSold = false;
      } else {
        allSold = false;
        AIVehicle.SendVehicleToDepot(v);
      }
    }
  }
  if (!allSold) return;
  /* Satellites joints aux StationID racines : les enlever AVANT les
   * racines. Le rollback ne touche que nos nouvelles stations dont
   * l'identifiant n'a pas change, jamais des routes etrangeres ni
   * des arrets appartenant a une autre compagnie. */
  if (satellites != null) {
    for (local i = satellites.len() - 1; i >= 0; i--) {
      local entry = satellites[i];
      if (!AIRoad.IsRoadStationTile(entry.tile)) continue;
      if (!AICompany.IsMine(AITile.GetOwner(entry.tile)) ||
          AIStation.GetStationID(entry.tile) != entry.id) return;
      if (!AIRoad.RemoveRoadStation(entry.tile)) return;
    }
  }
  if (depot != null && AIRoad.IsRoadDepotTile(depot)) AIRoad.RemoveRoadDepot(depot);
  if (stopB != null && AIRoad.IsRoadStationTile(stopB)) AIRoad.RemoveRoadStation(stopB);
  if (stopA != null && AIRoad.IsRoadStationTile(stopA)) AIRoad.RemoveRoadStation(stopA);
  if (added != null) {
    for (local i = added.len() - 1; i >= 0; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
  }
  OpexAir0310InvalidateSiteValidity();
}

/* ROAD100-8 (opt-in) : un arret traversant SATELLITE par terminus, joint au
 * StationID existant. Aucun ordre, vehicule ou plafond de quai supplementaire.
 * Le revenu marginal est estime a flotte et duree de parcours inchangees ;
 * les tuiles productrices deja couvertes ne sont jamais recomptees.
 * Recherche limitee a 8 cases Manhattan, 4 essais physiques et 25k opcodes
 * par bout. Une extension echouee ne compromet jamais la ligne de base. */
function OpexRoad100ExpandJoinedStops(catalog, candidate, stopA, stopB, stationA, stationB, accounting = null)
{
  local summary = { stopsA = [], stopsB = [], marginalA = 0, marginalB = 0,
                    cost = 0, ops = 0 };
  if (!ROAD100_JOINED_STOPS || candidate == null ||
      !("road100JoinedStops" in candidate) || !candidate.road100JoinedStops ||
      candidate.kind != "pax" || catalog == null || candidate.engine == null ||
      !AICargo.HasCargoClass(candidate.cargo, AICargo.CC_PASSENGERS)) return summary;
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) ||
      stationA == stationB) return summary;

  local spread = AIGameSettings.GetValue("station.station_spread");
  if (spread < 2) return summary;
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  if (coverage < 1) return summary;
  local price = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP);
  if (price < 1) return summary;
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  local stops = [stopA, stopB];
  local ids = [stationA, stationB];
  local monthly = candidate.monthly;
  if (monthly <= 0 || candidate.trains <= 0) return summary;
  /* Inverser la formule route pour conserver la duree calculee sur le trace
   * reel, meme lorsque les deux centres de ville sont plus proches. */
  local routeDist = candidate.distance;
  if (candidate.effectiveSpeed > 0 && candidate.oneWayDays > ROAD_PAX_STOP_DWELL_DAYS) {
    local inferred = ((candidate.oneWayDays - ROAD_PAX_STOP_DWELL_DAYS) *
                      36 * candidate.effectiveSpeed) / 1000;
    if (inferred > routeDist) routeDist = inferred;
  }
  local baseEconomics = OpexRoadLineEconomics(catalog, candidate.cargo, candidate.distance,
                                              monthly, candidate.engine, "pax", routeDist);
  if (baseEconomics == null || baseEconomics.trains != candidate.trains) return summary;

  for (local end = 0; end < 2; end++) {
    local mark = OpexOpsMeasureBegin();
    local primaryTile = stops[end];
    local id = ids[end];
    local town = AITile.GetClosestTown(primaryTile);
    local reason = "NO_SITE";
    local builtTile = -1;
    local builtMarginal = 0;
    local paid = 0;
    local roi = 0;
    local probed = 0;
    if (!AIRoad.IsRoadStationTile(primaryTile) || AIStation.GetStationID(primaryTile) != id ||
        !AITown.IsValidTown(town)) continue;
    if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 25000 + price) {
      reason = "CASH";
    } else {
      /* Un marche de tuiles productrices unique, calcule en natif. Valuate
       * avant KeepAboveValue evite un GetCargoProduction dans chaque boucle
       * (145 sites maximum × carre de couverture). */
      local bx = AIMap.GetTileX(primaryTile);
      local by = AIMap.GetTileY(primaryTile);
      local extent = 8 + coverage;
      local x0 = bx - extent; if (x0 < 0) x0 = 0;
      local y0 = by - extent; if (y0 < 0) y0 = 0;
      local x1 = bx + extent; if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
      local y1 = by + extent; if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
      local producing = AITileList();
      producing.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
      producing.Valuate(AITile.GetCargoProduction, candidate.cargo, 1, 1, 0);
      producing.KeepAboveValue(0);
      local sources = [];
      foreach (srcTile, volume in producing) {
        if (AITile.GetClosestTown(srcTile) == town)
          sources.append({ tile = srcTile, volume = volume });
      }
      local covered = AITileList_StationCoverage(id);
      /* Deux extremites dans la meme ville ne doivent pas capter deux fois
       * les memes maisons, meme si elles ont des StationID distincts. */
      if (AITile.GetClosestTown(stops[1 - end]) == town)
        covered.AddList(AITileList_StationCoverage(ids[1 - end]));
      local fronts = [];
      foreach (d in dirs) {
        local adj = primaryTile + d;
        if (AIMap.IsValidTile(adj) && AIRoad.IsRoadTile(adj) &&
            AIRoad.AreRoadTilesConnected(primaryTile, adj)) fronts.append(adj);
      }
      local choices = [];
      for (local dx = -8; dx <= 8; dx++) {
        /* GetOpsTillSuspend est la marge d'UN tick, pas le budget total.
         * Le smoke v2 avait interrompu les deux scans a ~9k ops simplement
         * parce que le tick se terminait ; laisser NoAI suspendre et reprendre
         * automatiquement, tout en bornant le travail cumule a 25k. */
        if (OpexOpsMeasureEnd(mark) >= 25000) { reason = "OPCAP"; break; }
        for (local dy = -8; dy <= 8; dy++) {
          if (abs(dx) + abs(dy) > 8) continue;
          local x = bx + dx;
          local y = by + dy;
          if (!OpexRoadInMap(x, y)) continue;
          local tile = AIMap.GetTileIndex(x, y);
          if (AIMap.DistanceMax(tile, primaryTile) >= spread ||
              AIMap.DistanceManhattan(tile, primaryTile) < ROAD_BUS_STOP_MIN_DISTANCE ||
              !AIRoad.IsRoadTile(tile) || AIRoad.IsRoadStationTile(tile) ||
              AIRoad.IsRoadDepotTile(tile) || AITile.IsStationTile(tile) ||
              AITile.GetClosestTown(tile) != town) continue;
          local marginal = 0;
          foreach (src in sources) {
            if (!covered.HasItem(src.tile) &&
                AIMap.DistanceMax(src.tile, tile) <= coverage) marginal += src.volume;
          }
          if (marginal <= 0) continue;
          choices.append({ tile = tile, marginal = marginal,
                           distance = AIMap.DistanceManhattan(tile, primaryTile) });
        }
      }
      choices.sort(OpexRoad100SortJoinedSite);
      local limit = choices.len() < 4 ? choices.len() : 4;
      for (local i = 0; i < limit && fronts.len() > 0; i++) {
        if (OpexOpsMeasureEnd(mark) >= 25000) { reason = "OPCAP"; break; }
        local choice = choices[i];
        probed++;
        local projected = OpexRoadLineEconomics(catalog, candidate.cargo, candidate.distance,
                                               monthly + choice.marginal, candidate.engine,
                                               "pax", routeDist);
        if (projected == null || projected.trains != candidate.trains ||
            projected.runningAnnual != baseEconomics.runningAnnual) {
          reason = "FLEET"; continue;
        }
        local amort = ((price * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS);
        local deltaAnnual = projected.revenueAnnual - baseEconomics.revenueAnnual - amort;
        if (deltaAnnual * 100 < price * 20) { reason = "ROI"; continue; }
        roi = (deltaAnnual * 100) / price;
        if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 25000 + price) {
          reason = "CASH"; break;
        }
        local front = null;
        foreach (d in dirs) {
          local adj = choice.tile + d;
          if (!AIMap.IsValidTile(adj) || !AIRoad.IsRoadTile(adj) ||
              !AIRoad.AreRoadTilesConnected(choice.tile, adj)) continue;
          local connected = false;
          foreach (baseFront in fronts) {
            if (OpexRoadBfsPath(adj, baseFront, 96) != null) {
              connected = true; break;
            }
          }
          if (!connected) continue;
          local testOk = false;
          {
            /* Bouclier : AIAccounting imbriqué jette le coût simulé sous AITestMode
             * pour ne pas gonfler actualCost du chantier parent. */
            local shield = AIAccounting();
            local test = AITestMode();
            testOk = AIRoad.BuildDriveThroughRoadStation(choice.tile, adj,
                          AIRoad.ROADVEHTYPE_BUS, id);
            test = null;
            shield = null;
          }
          if (testOk) { front = adj; break; }
        }
        if (front == null) { reason = "CONNECT"; continue; }
        if (OpexOpsMeasureEnd(mark) >= 25000) { reason = "OPCAP"; break; }
        /* Mesurer la commande réelle par AIAccounting isolé (sans polluer par le delta
         * de caisse), en respectant la non-imbrication : si accounting englobant est
         * fourni, lire par différence sur celui-ci, sinon ouvrir un compteur local. */
        local costBefore = accounting != null ? accounting.GetCosts() : 0;
        local stationAccounting = accounting != null ? null : AIAccounting();
        local ok = AIRoad.BuildDriveThroughRoadStation(choice.tile, front,
                                                        AIRoad.ROADVEHTYPE_BUS, id);
        local actualCost = accounting != null ? (accounting.GetCosts() - costBefore) : stationAccounting.GetCosts();
        stationAccounting = null;
        if (actualCost < 0) actualCost = 0;
        /* Un Build false ou une jonction vers un autre StationID ne doivent
         * JAMAIS demolir la ligne. Retirer seulement le nouveau tile. */
        local newTile = AIRoad.IsRoadStationTile(choice.tile) &&
                        AICompany.IsMine(AITile.GetOwner(choice.tile));
        local stillConnected = false;
        if (ok && newTile && AIRoad.AreRoadTilesConnected(choice.tile, front)) {
          foreach (baseFront in fronts) {
            if (OpexRoadBfsPath(front, baseFront, 96) != null) {
              stillConnected = true; break;
            }
          }
        }
        if (!ok || !newTile || AIStation.GetStationID(choice.tile) != id ||
            !stillConnected) {
          if (newTile) AIRoad.RemoveRoadStation(choice.tile);
          reason = "JOIN"; continue;
        }
        if (actualCost < 1 || deltaAnnual * 100 < actualCost * 20 ||
            AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 25000) {
          AIRoad.RemoveRoadStation(choice.tile);
          reason = "COST"; continue;
        }
        OpexAir0310InvalidateSiteValidity();
        builtTile = choice.tile;
        builtMarginal = choice.marginal;
        paid = actualCost;
        roi = (deltaAnnual * 100) / actualCost;
        monthly += builtMarginal;
        baseEconomics = projected;
        reason = "OK";
        if (end == 0) summary.stopsA.append(builtTile);
        else summary.stopsB.append(builtTile);
        summary.cost += paid;
        if (end == 0) summary.marginalA += builtMarginal;
        else summary.marginalB += builtMarginal;
        break;
      }
    }
    local spent = OpexOpsMeasureEnd(mark);
    summary.ops += spent;
    if (DECISION_LOG) OpexDecide("ROAD100_JOINED_STOP",
        "end=" + (end == 0 ? "A" : "B") + " station=" + id +
        " tile=" + builtTile + " cover_marginal=" + builtMarginal +
        " cost=" + paid + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF) +
        " roi_pct=" + roi + " ops=" + spent + " tick_left=" +
        AIController.GetOpsTillSuspend() + " probes=" + probed +
        " reason=" + reason);
  }
  return summary;
}

/* ROAD100_PAX_PORTFOLIO v20 : prevoir UNIQUEMENT des opportunites
 * physiques, pas des recettes acquises. Deux racines A0/B0 restent les
 * deux seules destinations des vehicules. Producteurs evalues UNE FOIS
 * par une liste native (deux rectangles de quartier) ; un meme producteur
 * appartient au plus a une racine/satellite/Opex existant.
 * Le vrai StationID n'existe pas avant BuildRoadRoute. Le test STATION_NEW
 * prouve seulement la faisabilite de la tuile, jamais la jonction.
 * Limites : 12 sites evalues/fin, 4 AITest DT au TOTAL, 85k opcodes. */
function OpexRoad100PaxPortfolioPreview(catalog, candidate, plan)
{
  local out = { ok = false, monthly = 0, marginalA = 0,
      marginalB = 0, stopsA = [], stopsB = [], ops = 0,
      reason = "OFF", quote = 0, baseMonthly = 0,
      siteA = -1, siteB = -1, frontA = -1, frontB = -1,
      roadType = -1, stationTests = 0, sitesA = 0,
      sitesB = 0, producers = 0, roadsA = 0, roadsB = 0,
      townsA = 0, townsB = 0, spread = -1, coverage = -1 };
  if (!ROAD100_PAX_PORTFOLIO) return out;
  local mark = OpexOpsMeasureBegin();
  out.reason = "PRECHECK";
  do {
    if (catalog == null || candidate == null || plan == null ||
        !("stopA" in plan) || !("stopB" in plan) ||
        !("kind" in candidate) || candidate.kind != "pax" ||
        !("cargo" in candidate) ||
        !AICargo.HasCargoClass(candidate.cargo, AICargo.CC_PASSENGERS) ||
        !("roadType" in catalog) || catalog.roadType < 0 ||
        !("vehType" in plan) || plan.vehType != AIRoad.ROADVEHTYPE_BUS ||
        !AIMap.IsValidTile(plan.stopA.tile) ||
        !AIMap.IsValidTile(plan.stopB.tile) ||
        !AIRoad.IsRoadTile(plan.stopA.tile) ||
        !AIRoad.IsRoadTile(plan.stopB.tile) ||
        !AIMap.IsValidTile(plan.stopA.front) ||
        !AIMap.IsValidTile(plan.stopB.front)) break;
    out.siteA = plan.stopA.tile;
    out.siteB = plan.stopB.tile;
    out.frontA = plan.stopA.front;
    out.frontB = plan.stopB.front;
    out.roadType = catalog.roadType;
    local spread = AIGameSettings.GetValue("station.station_spread");
    local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    out.spread = spread;
    out.coverage = coverage;
    local price = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP);
    if (spread < 7 || coverage < 1 || price <= 0) {
      out.reason = "SPREAD_OR_PRICE"; break;
    }
    /* Opt-in seulement : les AITest doivent utiliser le type de route
     * effectivement choisi par le constructeur, pas le defaut du tick. */
    AIRoad.SetCurrentRoadType(catalog.roadType);
    if (AIRoad.GetCurrentRoadType() != catalog.roadType) {
      out.reason = "ROADTYPE"; break;
    }
    local roots = [plan.stopA.tile, plan.stopB.tile];
    local fronts = [plan.stopA.front, plan.stopB.front];
    local towns = [AITile.GetClosestTown(roots[0]),
                   AITile.GetClosestTown(roots[1])];
    if (!AITown.IsValidTown(towns[0]) || !AITown.IsValidTown(towns[1])) {
      out.reason = "TOWN"; break;
    }
    local ownCovered = AITileList();
    local ownStations = AIStationList(AIStation.STATION_ANY);
    for (local id = ownStations.Begin(); !ownStations.IsEnd();
         id = ownStations.Next()) {
      if (OpexOpsMeasureEnd(mark) >= 85000 - 18000) {
        out.reason = "OPCAP"; break;
      }
      ownCovered.AddList(AITileList_StationCoverage(id));
    }
    if (out.reason == "OPCAP") break;
    local radius = spread - 1;
    if (radius > 9) radius = 9;
    local producers = AITileList();
    for (local end = 0; end < 2; end++) {
      local x = AIMap.GetTileX(roots[end]);
      local y = AIMap.GetTileY(roots[end]);
      local ext = radius + coverage;
      local lx = x - ext; if (lx < 0) lx = 0;
      local ly = y - ext; if (ly < 0) ly = 0;
      local hx = x + ext;
      local hy = y + ext;
      if (hx >= AIMap.GetMapSizeX()) hx = AIMap.GetMapSizeX() - 1;
      if (hy >= AIMap.GetMapSizeY()) hy = AIMap.GetMapSizeY() - 1;
      producers.AddRectangle(AIMap.GetTileIndex(lx, ly),
          AIMap.GetTileIndex(hx, hy));
    }
    if (OpexOpsMeasureEnd(mark) >= 85000 - 18000) {
      out.reason = "OPCAP"; break;
    }
    producers.Valuate(AITile.GetCargoProduction, candidate.cargo, 1, 1, 0);
    producers.KeepAboveValue(0);
    if (OpexOpsMeasureEnd(mark) >= 85000 - 14000) {
      out.reason = "OPCAP"; break;
    }
    local sources = [];
    foreach (srcTile, vol in producers) {
      if (OpexOpsMeasureEnd(mark) >= 85000 - 11000) {
        out.reason = "OPCAP"; break;
      }
      if (ownCovered.HasItem(srcTile)) continue;
      sources.append({ tile = srcTile, amount = vol });
      out.producers++;
    }
    if (out.reason == "OPCAP") break;
    local captured = {};
    foreach (src in sources) {
      if (AIMap.DistanceMax(src.tile, roots[0]) <= coverage ||
          AIMap.DistanceMax(src.tile, roots[1]) <= coverage) {
        captured.rawset(src.tile, true);
        out.baseMonthly += src.amount;
      }
    }
    out.monthly = out.baseMonthly;
    /* V20d : la boucle script des 4 anneaux coutait ~77k opcodes,
     * meme sans route (seed42). Extraire les routes par une valuation
     * NATIVE unique, puis qualifier au plus 12 sites par bout. Le
     * rayon inclut tout station_spread, jusqu'a 11 tuiles. */
    local balance = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    /* Ne jamais faire classer un satellite qui viderait le budget du depot
     * et du premier bus. Les controles physiques referont cette garde. */
    local reserveAfterSat = candidate.engine.price + catalog.costRoadDepot
        + 3 * catalog.costRoadPerTile + 25000;
    for (local end = 0; end < 2; end++) {
      if (OpexOpsMeasureEnd(mark) >= 85000 - 12000) {
        out.reason = "OPCAP"; break;
      }
      local cx = AIMap.GetTileX(roots[end]);
      local cy = AIMap.GetTileY(roots[end]);
      local options = [];
      local acceptedSites = 0;
      local roadSites = 0;
      local townSites = 0;
      local radius = spread - 1;
      if (radius > 11) radius = 11;
      local x0 = cx - radius; if (x0 < 0) x0 = 0;
      local y0 = cy - radius; if (y0 < 0) y0 = 0;
      local x1 = cx + radius;
      local y1 = cy + radius;
      if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
      if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
      local roads = AITileList();
      roads.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
      roads.Valuate(AIRoad.IsRoadTile);
      roads.KeepAboveValue(0);
      for (local tile = roads.Begin(); !roads.IsEnd() && acceptedSites < 12;
           tile = roads.Next()) {
        if (OpexOpsMeasureEnd(mark) >= 85000 - 11000) break;
        if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile) ||
            AITile.IsStationTile(tile)) continue;
        roadSites++;
        if (AIMap.DistanceMax(tile, roots[end]) >= spread ||
            AIMap.DistanceManhattan(tile, roots[end]) < 6 ||
            AIMap.DistanceManhattan(tile, roots[1 - end]) < 6 ||
            AITile.GetClosestTown(tile) != towns[end]) continue;
        townSites++;
        local marginal = 0;
        foreach (src in sources) {
          if (!(src.tile in captured) &&
              AIMap.DistanceMax(src.tile, tile) <= coverage)
            marginal += src.amount;
        }
        if (marginal <= 0) continue;
        acceptedSites++;
        options.append({ tile = tile, marginal = marginal,
            distance = AIMap.DistanceManhattan(tile, roots[end]) });
      }
      if (end == 0) out.sitesA = acceptedSites;
      else out.sitesB = acceptedSites;
      if (end == 0) { out.roadsA = roadSites; out.townsA = townSites; }
      else { out.roadsB = roadSites; out.townsB = townSites; }
      options.sort(OpexRoad100SortJoinedSite);
      for (local ci = 0; ci < options.len(); ci++) {
        if (OpexOpsMeasureEnd(mark) >= 85000 - 10000) {
          out.reason = "OPCAP"; break;
        }
        if (out.stationTests >= 4 ||
            out.quote + price + reserveAfterSat > balance)
          break;
        local choice = options[ci];
        local selected = end == 0 ? out.stopsA : out.stopsB;
        if (selected.len() >= 2) break;
        local spacingOK = true;
        local minX = cx;
        local maxX = cx;
        local minY = cy;
        local maxY = cy;
        foreach (sat in selected) {
          if (AIMap.DistanceManhattan(choice.tile, sat.tile) < 6)
            spacingOK = false;
          local sx = AIMap.GetTileX(sat.tile);
          local sy = AIMap.GetTileY(sat.tile);
          if (sx < minX) minX = sx;
          if (sx > maxX) maxX = sx;
          if (sy < minY) minY = sy;
          if (sy > maxY) maxY = sy;
        }
        local qx = AIMap.GetTileX(choice.tile);
        local qy = AIMap.GetTileY(choice.tile);
        if (qx < minX) minX = qx;
        if (qx > maxX) maxX = qx;
        if (qy < minY) minY = qy;
        if (qy > maxY) maxY = qy;
        if (!spacingOK || maxX - minX >= spread ||
            maxY - minY >= spread) continue;
        local dirs = [1, -1, AIMap.GetMapSizeX(), -AIMap.GetMapSizeX()];
        local front = -1;
        for (local fi = 0; fi < dirs.len(); fi++) {
          if (OpexOpsMeasureEnd(mark) >= 85000 - 10000) break;
          local adj = choice.tile + dirs[fi];
          if (!AIMap.IsValidTile(adj) ||
              AIMap.DistanceManhattan(adj, choice.tile) != 1 ||
              !AIRoad.IsRoadTile(adj) ||
              !AIRoad.AreRoadTilesConnected(choice.tile, adj) ||
              !AIRoad.AreRoadTilesConnected(adj, choice.tile)) continue;
          if (OpexRoadBfsPath(adj, fronts[end], 64) == null ||
              OpexRoadBfsPath(fronts[end], adj, 64) == null) continue;
          out.stationTests++;
          local allowed = false;
          { local test = AITestMode();
            allowed = AIRoad.BuildDriveThroughRoadStation(choice.tile, adj,
                AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }
          if (allowed) { front = adj; break; }
          if (out.stationTests >= 4) break;
        }
        if (front < 0) continue;
        local exactMarginal = 0;
        foreach (src in sources) {
          if (!(src.tile in captured) &&
              AIMap.DistanceMax(src.tile, choice.tile) <= coverage)
            exactMarginal += src.amount;
        }
        if (exactMarginal <= 0) continue;
        selected.append({ tile = choice.tile, front = front,
            marginal = exactMarginal, quote = price });
        out.quote += price;
        out.monthly += exactMarginal;
        if (end == 0) out.marginalA += exactMarginal;
        else out.marginalB += exactMarginal;
        foreach (src in sources) {
          if (AIMap.DistanceMax(src.tile, choice.tile) <= coverage)
            captured.rawset(src.tile, true);
        }
      }
      if (out.reason == "OPCAP") break;
    }
    if (out.reason == "OPCAP") {
      out.stopsA = []; out.stopsB = [];
      out.quote = 0; out.marginalA = 0; out.marginalB = 0;
      out.monthly = out.baseMonthly;
      break;
    }
    out.ok = out.stopsA.len() + out.stopsB.len() > 0;
    out.reason = out.ok ? "PREVIEW_ONLY" : "NO_SATELLITE";
  } while (false);
  out.ops = OpexOpsMeasureEnd(mark);
  if (out.ops > 85000) {
    out.ok = false; out.reason = "OPCAP";
    out.stopsA = []; out.stopsB = [];
    out.marginalA = 0; out.marginalB = 0;
    out.quote = 0; out.monthly = out.baseMonthly;
  }
  if (DECISION_LOG) OpexDecide("ROAD100_PAX_PORTFOLIO_PREVIEW",
      "ok=" + (out.ok ? 1 : 0) + " reason=" + out.reason
      + " monthly=" + out.monthly + " base=" + out.baseMonthly
      + " marginal_a=" + out.marginalA + " marginal_b=" + out.marginalB
      + " sat_a=" + out.stopsA.len() + " sat_b=" + out.stopsB.len()
      + " site_a=" + out.siteA + " site_b=" + out.siteB
      + " candidates_a=" + out.sitesA + " candidates_b=" + out.sitesB
      + " station_tests=" + out.stationTests + " producers=" + out.producers
      + " roads_a=" + out.roadsA + " roads_b=" + out.roadsB
      + " towns_a=" + out.townsA + " towns_b=" + out.townsB
      + " spread=" + out.spread + " coverage=" + out.coverage
      + " quote=" + out.quote + " ops=" + out.ops);
  return out;
}

/* ROAD100_PAX_PORTFOLIO : jonction des sites EXACTS de l'aperçu aux
 * StationID racines apres leur pose. Un preview ne constitue jamais une
 * preuve de join : AITest et GetStationID sont refaits. La couverture
 * realisee se mesure par difference des listes natives, non par la
 * valeur estimee de l'aperçu. Les satellites ne changent pas les ordres,
 * les bus ou les quais A0/B0. Seules les stations NOUVELLES a nous
 * pourront etre retirees par OpexRoadRollback si le chantier echoue. */
function OpexRoad100PaxPortfolioBuild(catalog, candidate, plan, preview,
                                      stopA, stopB, stationA, stationB, accounting = null)
{
  local out = { ok = false, stopsA = [], stopsB = [],
      marginalA = 0, marginalB = 0, monthly = 0, cost = 0,
      ops = 0, reason = "OFF", builtTiles = [], attempted = 0,
      tested = 0, joined = 0, failed = 0 };
  if (!ROAD100_PAX_PORTFOLIO) return out;
  local mark = OpexOpsMeasureBegin();
  out.reason = "PRECHECK";
  do {
    if (catalog == null || candidate == null || plan == null ||
        preview == null || !("ok" in preview) || !preview.ok ||
        !("road100PaxPortfolio" in candidate) ||
        !candidate.road100PaxPortfolio ||
        !("stopsA" in preview) || !("stopsB" in preview) ||
        !("siteA" in preview) || !("siteB" in preview) ||
        !("frontA" in preview) || !("frontB" in preview) ||
        !("roadType" in preview) ||
        preview.siteA != stopA || preview.siteB != stopB ||
        preview.frontA != plan.stopA.front ||
        preview.frontB != plan.stopB.front ||
        preview.roadType != catalog.roadType ||
        !AIRoad.IsRoadStationTile(stopA) ||
        !AIRoad.IsRoadStationTile(stopB) ||
        AIStation.GetStationID(stopA) != stationA ||
        AIStation.GetStationID(stopB) != stationB ||
        !AIStation.IsValidStation(stationA) ||
        !AIStation.IsValidStation(stationB) || stationA == stationB) break;
    local spread = AIGameSettings.GetValue("station.station_spread");
    local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    local price = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP);
    local reserveAfterSat = candidate.engine.price + catalog.costRoadDepot
        + 3 * catalog.costRoadPerTile + 25000;
    if (spread < 7 || coverage < 1 || price <= 0) {
      out.reason = "SPREAD"; break;
    }
    local roots = [stopA, stopB];
    local fronts = [plan.stopA.front, plan.stopB.front];
    local ids = [stationA, stationB];
    local selected = [preview.stopsA, preview.stopsB];
    local producing = AITileList();
    local extent = spread - 1 + coverage;
    if (extent > 9 + coverage) extent = 9 + coverage;
    for (local end = 0; end < 2; end++) {
      local x = AIMap.GetTileX(roots[end]);
      local y = AIMap.GetTileY(roots[end]);
      local x0 = x - extent; if (x0 < 0) x0 = 0;
      local y0 = y - extent; if (y0 < 0) y0 = 0;
      local x1 = x + extent;
      local y1 = y + extent;
      if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
      if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
      producing.AddRectangle(AIMap.GetTileIndex(x0, y0),
          AIMap.GetTileIndex(x1, y1));
    }
    if (OpexOpsMeasureEnd(mark) >= 48000) {
      out.reason = "OPCAP"; break;
    }
    producing.Valuate(AITile.GetCargoProduction, candidate.cargo, 1, 1, 0);
    producing.KeepAboveValue(0);
    if (OpexOpsMeasureEnd(mark) >= 50000) {
      out.reason = "OPCAP"; break;
    }
    local covered = AITileList();
    local otherCovered = AITileList();
    local own = AIStationList(AIStation.STATION_ANY);
    for (local id = own.Begin(); !own.IsEnd(); id = own.Next()) {
      if (OpexOpsMeasureEnd(mark) >= 53000) {
        out.reason = "OPCAP"; break;
      }
      local stationTiles = AITileList_StationCoverage(id);
      covered.AddList(stationTiles);
      if (id != stationA && id != stationB)
        otherCovered.AddList(stationTiles);
    }
    if (out.reason == "OPCAP") break;
    local rootCoverA = AITileList_StationCoverage(stationA);
    local rootCoverB = AITileList_StationCoverage(stationB);
    foreach (srcTile, value in producing) {
      if (!otherCovered.HasItem(srcTile) &&
          (rootCoverA.HasItem(srcTile) || rootCoverB.HasItem(srcTile)))
        out.monthly += value;
    }
    if (OpexOpsMeasureEnd(mark) >= 55000) {
      out.reason = "OPCAP"; break;
    }
    local selectedTiles = [[], []];
    for (local end = 0; end < 2; end++) {
      for (local i = 0; i < selected[end].len() && i < 2; i++) {
        if (OpexOpsMeasureEnd(mark) >= 55000) {
          out.reason = "OPCAP"; break;
        }
        out.attempted++;
        local sat = selected[end][i];
        if (!("tile" in sat) || !("front" in sat) ||
            !AIMap.IsValidTile(sat.tile) || !AIMap.IsValidTile(sat.front) ||
            AIMap.DistanceManhattan(sat.tile, roots[end]) < 6 ||
            AIMap.DistanceManhattan(sat.tile, roots[1 - end]) < 6 ||
            !AIRoad.IsRoadTile(sat.tile) ||
            AIRoad.IsRoadStationTile(sat.tile) ||
            AIRoad.IsRoadDepotTile(sat.tile) ||
            AITile.IsStationTile(sat.tile) ||
            !AIRoad.AreRoadTilesConnected(sat.tile, sat.front) ||
            !AIRoad.AreRoadTilesConnected(sat.front, sat.tile)) {
          out.failed++; continue;
        }
        local minX = AIMap.GetTileX(roots[end]);
        local maxX = minX;
        local minY = AIMap.GetTileY(roots[end]);
        local maxY = minY;
        local spaced = true;
        foreach (priorTile in selectedTiles[end]) {
          if (AIMap.DistanceManhattan(priorTile, sat.tile) < 6)
            spaced = false;
          local px = AIMap.GetTileX(priorTile);
          local py = AIMap.GetTileY(priorTile);
          if (px < minX) minX = px;
          if (px > maxX) maxX = px;
          if (py < minY) minY = py;
          if (py > maxY) maxY = py;
        }
        local sx = AIMap.GetTileX(sat.tile);
        local sy = AIMap.GetTileY(sat.tile);
        if (sx < minX) minX = sx;
        if (sx > maxX) maxX = sx;
        if (sy < minY) minY = sy;
        if (sy > maxY) maxY = sy;
        if (!spaced || maxX - minX >= spread || maxY - minY >= spread ||
            OpexRoadBfsPath(sat.front, fronts[end], 64) == null ||
            OpexRoadBfsPath(fronts[end], sat.front, 64) == null) {
          out.failed++; continue;
        }
        local predicted = 0;
        foreach (srcTile, value in producing) {
          if (!covered.HasItem(srcTile) &&
              AIMap.DistanceMax(srcTile, sat.tile) <= coverage)
            predicted += value;
        }
        if (predicted <= 0 ||
            AICompany.GetBankBalance(AICompany.COMPANY_SELF) <
                price + reserveAfterSat) {
          out.failed++; continue;
        }
        if (out.tested >= 4) { out.reason = "TEST_CAP"; break; }
        out.tested++;
        local testOk = false;
        {
          /* Bouclier : AIAccounting imbriqué jette le coût simulé sous AITestMode
           * pour ne pas gonfler actualCost du chantier parent. */
          local shield = AIAccounting();
          local test = AITestMode();
          testOk = AIRoad.BuildDriveThroughRoadStation(sat.tile,
              sat.front, AIRoad.ROADVEHTYPE_BUS, ids[end]);
          test = null;
          shield = null;
        }
        if (!testOk) { out.failed++; continue; }
        /* Mesurer la commande réelle par AIAccounting isolé (sans polluer par le delta
         * de caisse), en respectant la non-imbrication : si accounting englobant est
         * fourni, lire par différence sur celui-ci, sinon ouvrir un compteur local. */
        local costBefore = accounting != null ? accounting.GetCosts() : 0;
        local stationAccounting = accounting != null ? null : AIAccounting();
        local done = AIRoad.BuildDriveThroughRoadStation(sat.tile,
            sat.front, AIRoad.ROADVEHTYPE_BUS, ids[end]);
        local paid = accounting != null ? (accounting.GetCosts() - costBefore) : stationAccounting.GetCosts();
        stationAccounting = null;
        if (paid < 0) paid = 0;
        local ours = AIRoad.IsRoadStationTile(sat.tile) &&
            AICompany.IsMine(AITile.GetOwner(sat.tile)) &&
            AIStation.GetStationID(sat.tile) == ids[end];
        /* Enregistrer toute station reellement posee AVANT un controle
         * susceptible d'echouer ; la transaction peut alors la nettoyer. */
        if (ours) out.builtTiles.append({ tile = sat.tile, id = ids[end] });
        local connected = done && ours &&
            AIRoad.AreRoadTilesConnected(sat.tile, sat.front) &&
            AIRoad.AreRoadTilesConnected(sat.front, sat.tile);
        if (!connected || paid <= 0 ||
            AICompany.GetBankBalance(AICompany.COMPANY_SELF) < reserveAfterSat) {
          if (ours) {
            if (!AIRoad.RemoveRoadStation(sat.tile)) {
              out.reason = "ROLLBACK"; break;
            }
            out.builtTiles.pop();
          }
          out.failed++; continue;
        }
        local newCover = AITileList_StationCoverage(ids[end]);
        local realized = 0;
        foreach (srcTile, value in producing) {
          if (!covered.HasItem(srcTile) && newCover.HasItem(srcTile))
            realized += value;
        }
        if (realized <= 0) {
          if (ours) {
            if (!AIRoad.RemoveRoadStation(sat.tile)) {
              out.reason = "ROLLBACK"; break;
            }
            out.builtTiles.pop();
          }
          out.failed++; continue;
        }
        covered.AddList(newCover);
        selectedTiles[end].append(sat.tile);
        out.joined++;
        out.cost += paid;
        out.monthly += realized;
        if (end == 0) {
          out.stopsA.append(sat.tile);
          out.marginalA += realized;
        } else {
          out.stopsB.append(sat.tile);
          out.marginalB += realized;
        }
        OpexAir0310InvalidateSiteValidity();
      }
      if (out.reason == "OPCAP" || out.reason == "TEST_CAP" ||
          out.reason == "ROLLBACK") break;
    }
    out.ok = out.joined > 0;
    if (out.reason != "OPCAP" && out.reason != "TEST_CAP" &&
        out.reason != "ROLLBACK")
      out.reason = out.joined == 0 ? "NO_JOIN" :
          out.failed > 0 ? "PARTIAL" : "OK";
    if (("road100PaxProducerUnits" in candidate) &&
        candidate.road100PaxProducerUnits && candidate.monthly > 0) {
      out.monthly = candidate.monthly;
    }
  } while (false);
  out.ops = OpexOpsMeasureEnd(mark);
  if (out.ops > 65000) out.reason = "OPCAP";
  if (DECISION_LOG) OpexDecide("ROAD100_PAX_PORTFOLIO",
      "phase=build reason=" + out.reason + " joined=" + out.joined
      + " fail=" + out.failed + " tested=" + out.tested
      + " marginal_a=" + out.marginalA
      + " marginal_b=" + out.marginalB
      + " stops_a=" + out.stopsA.len()
      + " stops_b=" + out.stopsB.len()
      + " cash_cost=" + out.cost + " monthly=" + out.monthly
      + " ops=" + out.ops);
  return out;
}

/* Un arret de plus, meme facade, tuile cardinale voisine, joint au StationID deja pose.
 * STATION_JOIN_ADJACENT est le piege AAAHogEx (deux gares voisines -> gare neuve) : on passe
 * l'identifiant du primaire et on verifie GetStationID apres pose. Une extra qui n'a pas joint
 * est retiree sur place, la ligne ne meurt pas. */
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

/* V31b : comparaison marginale apres VRAIS quais, sans modifier le
 * contrat historique de OpexRoadLineEconomics (ESTIM/V262). Calculer
 * exactement N bus et la note a leur headway ; le revenu reste celui
 * des seules racines V30a, et ne suppose pas qu'un satellite soit servi.
 * Ce devis est volontairement isole a l'opt-in V31 deja NO-GO au smoke. */
function OpexRoad100PaxFixedFleetEconomics(catalog, candidate, plan,
                                           physicalCap, fixedVehicles)
{
  if (!ROAD100_PAX_INITIAL_BERTH_FLEET || candidate.kind != "pax" ||
      physicalCap < 3 || fixedVehicles < 1 || fixedVehicles > physicalCap ||
      candidate.monthly <= 0 || candidate.engine == null) return null;
  local baseline = OpexRoadLineEconomics(catalog, candidate.cargo,
      candidate.distance, candidate.monthly, candidate.engine, "pax",
      plan.routeDistance, physicalCap);
  if (baseline == null || baseline.oneWayDays <= 0 ||
      candidate.engine.capacity <= 0) return null;
  local tripDays = baseline.oneWayDays;
  local roundTripDays = 2 * tripDays;
  local rating = (ESTIM_UNIFIE & 8) != 0
      ? OpexStationRatingForHeadway(roundTripDays / fixedVehicles)
      : STATION_RATING_PCT;
  local offered = (candidate.monthly * rating) / 100;
  if (offered <= 0) return null;
  local tripsMonth = OpexLoadedTripsPerMonth(tripDays, roundTripDays, true);
  local monthlyCapacity = fixedVehicles * candidate.engine.capacity * tripsMonth;
  local carried = offered < monthlyCapacity ? offered : monthlyCapacity;
  local headway = roundTripDays.tofloat() / fixedVehicles;
  local daysMonth = (ESTIM_UNIFIE & 8) != 0 ? OpexEstimDaysPerMonth() : 30.0;
  local waitingPerEnd = (candidate.monthly.tofloat() / 2.0) * headway /
      daysMonth;
  local pickup = waitingPerEnd < candidate.engine.capacity ? waitingPerEnd
      : candidate.engine.capacity.tofloat();
  local actualMonthly = (2.0 * fixedVehicles * daysMonth * pickup /
      roundTripDays).tointeger();
  if (actualMonthly < carried) carried = actualMonthly;
  carried = carried.tointeger();
  local revenueAnnual = (12 * carried * AICargo.GetCargoIncome(candidate.cargo,
      candidate.distance, OpexCeilDiv(baseline.transitDays, 1))).tointeger();
  local vehicleCost = fixedVehicles * candidate.engine.price;
  local infrastructureCost = baseline.capital -
      baseline.trains * candidate.engine.price;
  if (infrastructureCost < 0) return null;
  local life = candidate.engine.ageYears > 0 ? candidate.engine.ageYears : 12;
  local amortAnnual = vehicleCost / life +
      ((infrastructureCost * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS);
  local runningAnnual = fixedVehicles * candidate.engine.runningCost;
  local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
  local capital = vehicleCost + infrastructureCost;
  local immobilise = TRANSIT_COST_PERMILLE > 0
      ? (revenueAnnual * roundTripDays * TRANSIT_COST_PERMILLE) / 365000 : 0;
  local totalCapital = capital + immobilise;
  local roi = profitAnnual > 0 && totalCapital > 0
      ? (profitAnnual * 1000) / totalCapital : 0;
  local result = clone baseline;
  result.trains = fixedVehicles;
  result.roadVehicleCap = physicalCap;
  result.carried = carried;
  result.revenueAnnual = revenueAnnual;
  result.runningAnnual = runningAnnual;
  result.amortAnnual = amortAnnual;
  result.capital = capital;
  result.immobilise = immobilise;
  result.profitAnnual = profitAnnual;
  result.roi = roi;
  return result;
}

/* Transaction complete. Les vehicules ne demarrent qu'apres les ordres et toutes les connexions
 * valides, donc ils peuvent toujours etre vendus dans le depot pendant le rollback. */
function OpexBuildRoadRoute(catalog, budget, plan, candidate)
{
  local result = { ok = false, reason = "", error = 0, stopA = null, stopB = null,
                   stationA = null, stationB = null, depot = null, vehicles = [], cost = 0,
                   capacity = 0, opcodes = 0, nStopsA = 1, nStopsB = 1, actualCost = 0,
                   plannedCapital = (("capital" in candidate) ? candidate.capital : 0) };
  /* road_cost_probe : symetrique de air_cost_probe (builder_air.nut) et du devis rail P1.1.
   * Tout AITestMode dans les sous-modules (satellites PORTFOLIO, JOINED_STOPS) est isole
   * sous bouclier AIAccounting imbrique afin de ne mesurer que les commandes reelles executees. */
  local costs = AIAccounting();
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local balanceBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local cargo = candidate.cargo;
  local added = [];
  local stopA = null;
  local stopB = null;
  local depot = null;
  local built = [];
  local portfolioSatellites = [];
  local portfolioSummary = null;

  /* Revalidation transactionnelle : entre la generation (eventuellement mise en cache) et le
   * chantier, une autre ligne peut avoir pose un arret. Ne jamais engager la route dans ce cas. */
  if (AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS)) {
    local liveBusStops = OpexRoadOurBusTiles();
    if (OpexRoadTileTooClose(plan.stopA.tile, liveBusStops, ROAD_BUS_STOP_MIN_DISTANCE) ||
        OpexRoadTileTooClose(plan.stopB.tile, liveBusStops, ROAD_BUS_STOP_MIN_DISTANCE) ||
        AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile) < ROAD_BUS_STOP_MIN_DISTANCE) {
      result.reason = "SPACING";
      return result;
    }
  }

  /* V262 T12 : revérifier le plafond route juste avant la premiere depense. */
  local plannedRoad = (("trains" in candidate) && candidate.trains > 0) ? candidate.trains : 1;
  /* Un StationID de passagers, meme muni de satellites, garde deux
   * ordres A0/B0 et au plus deux bus de quai fiables simultanement.
   * Ne jamais acheter 28 bus sur un bonus de couverture preview. */
  if (ROAD100_PAX_PORTFOLIO &&
      ("road100PaxPortfolio" in candidate) && candidate.road100PaxPortfolio &&
      plannedRoad > 2) plannedRoad = 2;
  if (!OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, plannedRoad)) {
    result.reason = "NOSLOT";
    OpexDecide("VEHICLE_SLOT", "mode=road planned=" + plannedRoad + " reason=NOSLOT");
    return result;
  }

  budget.begin();
  OpexAir0310InvalidateSiteValidity();
  if (!OpexRoadBuildTrace(plan.trace, added)) {
    result.error = AIError.GetLastError();
    result.opcodes = budget.end("build_roads");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(null, null, null, built, added); result.reason = "ROAD"; return result;
  }
  result.opcodes = budget.end("build_roads");

  budget.begin();
  /* Meme bug que le depot (cf. commentaire sur OpexRoadFindDepot et sur OpexRoadSites) :
   * CmdBuildRoadStop ne pose ni ne verifie rien sur "front". Le raccord doit donc etre construit
   * explicitement AVANT l'arret, pendant que la tuile de l'arret est encore une route ordinaire
   * clairable -- CMD_LANDSCAPE_CLEAR interne de CmdBuildRoadStop la remplace ensuite, "front"
   * garde le bit. Chaque arete n'est ajoutee a `added` que si elle est reellement connectee. */
  local driveThrough = ("driveThrough" in plan) && plan.driveThrough;
  local okA = false;
  if (driveThrough) {
    okA = AIRoad.BuildDriveThroughRoadStation(plan.stopA.tile, plan.stopA.front,
                                             plan.vehType, AIStation.STATION_NEW);
  } else {
    AIRoad.BuildRoad(plan.stopA.front, plan.stopA.tile);
    local stubConnectedA = AIRoad.AreRoadTilesConnected(plan.stopA.front, plan.stopA.tile);
    if (stubConnectedA) added.append({ from = plan.stopA.front, to = plan.stopA.tile });
    okA = stubConnectedA && AIRoad.BuildRoadStation(plan.stopA.tile, plan.stopA.front,
                                                    plan.vehType, AIStation.STATION_NEW);
  }
  /* Bout en bout : GetRoadStationFrontTile, comme GetRoadDepotFrontTile, n'est que la geometrie
   * DECLAREE (station + offset), jamais une preuve de connexion reelle. Contrairement a ce que
   * supposait un commentaire precedent, AreRoadTilesConnected gere correctement les tuiles
   * MP_STATION (GetAnyRoadBits en fait un cas explicite, verifie dans road_map.cpp) : c'est donc le
   * seul predicat qui prouve que l'arret est reellement raccorde a "front", pas seulement pose. */
  if (okA && AIRoad.IsRoadStationTile(plan.stopA.tile) &&
      (driveThrough || AIRoad.GetRoadStationFrontTile(plan.stopA.tile) == plan.stopA.front) &&
      AIRoad.AreRoadTilesConnected(plan.stopA.tile, plan.stopA.front)) stopA = plan.stopA.tile;
  if (stopA == null) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_road_stops");
    result.actualCost = costs.GetCosts();
    /* ROAD100-8 uniquement : ASTOP peut signifier une station deja posee
     * mais non reliee. Ne jamais laisser ce site orphelin apres un okA. */
    local partialA = ((("road100SiteFirst" in candidate) && candidate.road100SiteFirst)
                      || (ROAD100_JOINED_STOPS && ("road100JoinedStops" in candidate) &&
                          candidate.road100JoinedStops)) && okA &&
                      AIRoad.IsRoadStationTile(plan.stopA.tile) &&
                      AICompany.IsMine(AITile.GetOwner(plan.stopA.tile))
                      ? plan.stopA.tile : null;
    OpexRoadRollback(partialA, null, null, built, added); result.reason = "ASTOP"; return result;
  }
  local okB = false;
  if (driveThrough) {
    okB = AIRoad.BuildDriveThroughRoadStation(plan.stopB.tile, plan.stopB.front,
                                             plan.vehType, AIStation.STATION_NEW);
  } else {
    AIRoad.BuildRoad(plan.stopB.front, plan.stopB.tile);
    local stubConnectedB = AIRoad.AreRoadTilesConnected(plan.stopB.front, plan.stopB.tile);
    if (stubConnectedB) added.append({ from = plan.stopB.front, to = plan.stopB.tile });
    okB = stubConnectedB && AIRoad.BuildRoadStation(plan.stopB.tile, plan.stopB.front,
                                                    plan.vehType, AIStation.STATION_NEW);
  }
  if (okB && AIRoad.IsRoadStationTile(plan.stopB.tile) &&
      (driveThrough || AIRoad.GetRoadStationFrontTile(plan.stopB.tile) == plan.stopB.front) &&
      AIRoad.AreRoadTilesConnected(plan.stopB.tile, plan.stopB.front)) stopB = plan.stopB.tile;
  if (stopB == null) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_road_stops");
    local partialB = ((("road100SiteFirst" in candidate) && candidate.road100SiteFirst)
                      || (ROAD100_JOINED_STOPS && ("road100JoinedStops" in candidate) &&
                          candidate.road100JoinedStops)) && okB &&
                      AIRoad.IsRoadStationTile(plan.stopB.tile) &&
                      AICompany.IsMine(AITile.GetOwner(plan.stopB.tile))
                      ? plan.stopB.tile : null;
    OpexRoadRollback(stopA, partialB, null, built, added);
    result.actualCost = costs.GetCosts();
    result.reason = "BSTOP"; return result;
  }
  local stationA = AIStation.GetStationID(stopA);
  local stationB = AIStation.GetStationID(stopB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) || stationA == stationB) {
    result.opcodes += budget.end("build_road_stops");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, null, built, added); result.reason = "STATION"; return result;
  }

  result.opcodes += budget.end("build_road_stops");

  /* PORTFOLIO : uniquement APRES les deux racines physiques, AVANT
   * depot/flotte. Une preview non reproduite ne change rien aux achats.
   * Chaque satellite effectivement joint est memorise pour rollback
   * si les etapes de depot, vehicules ou ordres echouent ensuite. */
  if (ROAD100_PAX_PORTFOLIO &&
      ("road100PaxPortfolio" in candidate) &&
      candidate.road100PaxPortfolio &&
      ("road100PortfolioPreview" in plan) &&
      plan.road100PortfolioPreview != null &&
      plan.road100PortfolioPreview.ok) {
    budget.begin();
    portfolioSummary = OpexRoad100PaxPortfolioBuild(
        catalog, candidate, plan, plan.road100PortfolioPreview,
        stopA, stopB, stationA, stationB, costs);
    portfolioSatellites = portfolioSummary.builtTiles;
    result.opcodes += budget.end("build_road_portfolio");
    result.road100PaxPortfolio <- portfolioSummary;
    result.nStopsA = 1 + portfolioSummary.stopsA.len();
    result.nStopsB = 1 + portfolioSummary.stopsB.len();
    if (portfolioSummary.reason == "ROLLBACK") {
      OpexRoadRollback(stopA, stopB, null, built, added, portfolioSatellites);
      result.actualCost = costs.GetCosts();
      result.reason = "PORTFOLIO_ROLLBACK";
      return result;
    }
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
    result.error = AIError.GetLastError(); OpexRoadRollback(stopA, stopB, null, built, added, portfolioSatellites);
    result.actualCost = costs.GetCosts();
    result.reason = "DEPOT"; return result;
  }

  budget.begin();
  local capacity = OpexRoadRefitCapacity(depot, candidate.engine, cargo);
  if (capacity <= 0) {
    result.opcodes += budget.end("build_road_vehicles");
    OpexRoadRollback(stopA, stopB, depot, built, added, portfolioSatellites);
    result.actualCost = costs.GetCosts();
    result.reason = "REFIT"; return result;
  }
  local first = AIVehicle.BuildVehicleWithRefit(depot, candidate.engine.id, cargo);
  if (!AIVehicle.IsValidVehicle(first)) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_road_vehicles");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, depot, built, added, portfolioSatellites); result.reason = "VEH"; return result;
  }
  built.append(first);
  if (AIVehicle.GetCapacity(first, cargo) <= 0 ||
      !AIRoad.RoadVehHasPowerOnRoad(AIVehicle.GetRoadType(first), catalog.roadType)) {
    result.opcodes += budget.end("build_road_vehicles");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, depot, built, added, portfolioSatellites); result.reason = "POWER"; return result;
  }

  /* ROAD100-31 : aucune preview ne permet d'acheter un bus en plus.
   * Le PORTFOLIO a deja construit des quais physiques a CHAQUE bout,
   * verifie leur StationID, connexite et caisse. Seulement maintenant
   * examiner la rentabilite MARGINALE de bus supplementaires sur le
   * volume ROOT dimensionnellement corrige (pas sur des satellites
   * non livres). Le stock de 2 bus reste intact si un seul bout est joint,
   * si la capacite refit change ou si la marge/les slots sont absents. */
  local road100PaxExtraInit = null;
  if (ROAD100_PAX_INITIAL_BERTH_FLEET && candidate.kind == "pax"
      && ("road100PaxProducerUnits" in candidate)
      && candidate.road100PaxProducerUnits
      && portfolioSummary != null && portfolioSummary.ok
      && portfolioSummary.stopsA.len() > 0
      && portfolioSummary.stopsB.len() > 0
      && result.nStopsA >= 2 && result.nStopsB >= 2
      && candidate.monthly > 0
      && AIVehicle.GetCapacity(first, cargo) == candidate.engine.capacity) {
    local bayA = portfolioSummary.stopsA[0];
    local bayB = portfolioSummary.stopsB[0];
    local baysValid = AIRoad.IsRoadStationTile(bayA)
        && AIRoad.IsRoadStationTile(bayB)
        && AICompany.IsMine(AITile.GetOwner(bayA))
        && AICompany.IsMine(AITile.GetOwner(bayB))
        && AIStation.GetStationID(bayA) == stationA
        && AIStation.GetStationID(bayB) == stationB;
    /* Des quais distants joints au meme StationID ne sont pas
     * forcement ADJACENTS aux tuiles root ; leur raccord sat/front
     * a deja ete prouve dans OpexRoad100PaxPortfolioBuild. */
    if (baysValid) {
      local cap = OpexRoadPhysicalVehicleCap(result.nStopsA, result.nStopsB);
      if (cap > 8) cap = 8;
      local base = OpexRoad100PaxFixedFleetEconomics(catalog, candidate,
          plan, cap, candidate.trains);
      local bestDelta = 0;
      local bestVehicles = candidate.trains;
      local price = AIEngine.GetPrice(candidate.engine.id);
      if (base != null && base.trains == candidate.trains && price > 0) {
        for (local vehicles = candidate.trains + 1;
             vehicles <= cap; vehicles++) {
          local option = OpexRoad100PaxFixedFleetEconomics(catalog,
              candidate, plan, cap, vehicles);
          if (option == null || option.trains != vehicles ||
              option.profitAnnual <= base.profitAnnual ||
              option.profitAnnual <= 0) continue;
          local extraVehicles = vehicles - candidate.trains;
          local extraCapital = extraVehicles * price;
          local extraProfit = option.profitAnnual - base.profitAnnual;
          local extraRoi = extraCapital > 0 ?
              (extraProfit * 1000) / extraCapital : 0;
          if (extraRoi < 250 ||
              AICompany.GetBankBalance(AICompany.COMPANY_SELF) <
                  extraCapital + 50000 ||
              !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, vehicles))
            continue;
          if (extraProfit > bestDelta) {
            bestDelta = extraProfit;
            bestVehicles = vehicles;
            road100PaxExtraInit = { economics = option,
                bayA = bayA, bayB = bayB, roi = extraRoi,
                baseTrains = base.trains };
          }
        }
        if (DECISION_LOG) OpexDecide("ROAD100_PAX_INITIAL_FLEET",
            "phase=quote requested=" + bestVehicles
            + " base=" + base.trains + " delta_profit=" + bestDelta
            + " extra_capital=" + ((bestVehicles - base.trains) * price)
            + " adopted=" + (road100PaxExtraInit != null ? 1 : 0)
            + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      }
    }
  }

  /* Ordres. La regle du fret vient directement de l'effondrement rail du 2026-08-28 : une ligne de
   * fret est a SENS UNIQUE, donc un OF_FULL_LOAD_ANY au puits fait attendre pour toujours un
   * chargement de retour qui n'existe pas. La source, elle, garde le plein chargement : le cargo y
   * s'accumule de toute facon, et un camion qui part avec une unite paie son trajet pour rien.
   * qui attend d'etre plein detruit precisement ce que la ligne a de bon. */
  local nonstopFlag = AIOrder.OF_NON_STOP_INTERMEDIATE;
  local isFreight = (candidate.kind == "freight");
  local sourceFullLoad = isFreight || ROAD1Y_LOAD_ORDERS;
  local sourceFlags = (sourceFullLoad ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE) | nonstopFlag;
  local orderA = AIOrder.AppendOrder(first, stopA, sourceFlags);
  local errorA = orderA ? 0 : AIError.GetLastError();
  /* Terminus : OF_NONE (ou OF_UNLOAD | OF_NO_LOAD sous ROAD1Y_LOAD_ORDERS sur fret). */
  local destFlags = (ROAD1Y_LOAD_ORDERS && isFreight) ? (AIOrder.OF_UNLOAD | AIOrder.OF_NO_LOAD) : AIOrder.OF_NONE;
  destFlags = destFlags | nonstopFlag;
  local orderB = AIOrder.AppendOrder(first, stopB, destFlags);
  local errorB = orderB ? 0 : AIError.GetLastError();
  if (!orderA || !orderB || AIOrder.GetOrderCount(first) != 2) {
    result.error = !orderA ? errorA : errorB; result.opcodes += budget.end("build_road_vehicles");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, depot, built, added, portfolioSatellites); result.reason = "ORDERS"; return result;
  }

  /* Les vehicules suivants sont CLONES du premier avec partage d'ordres : le clone reprend le
   * refit, et le partage evite de reposer deux ordres par vehicule (docs/mecanique_jeu.md S9,
   * AIOrder.ShareOrders). Un clone qui echoue n'est pas fatal -- la ligne roule avec ce qu'elle a,
   * ce qui vaut mieux qu'un rollback complet pour un vehicule d'appoint.
   * ⚠️ Le plafond vient du jeu, pas de nous : un arret n'accueille que DEUX vehicules a la fois,
   * au-dela ils font la queue sur la route et se bloquent (docs/mecanique_jeu.md S11). C'est
   * OpexRoadPhysicalVehicleCap dans economy.nut qui borne candidate.trains. */
  local want = candidate.trains;
  if (ROAD100_PAX_PORTFOLIO &&
      ("road100PaxPortfolio" in candidate) && candidate.road100PaxPortfolio) {
    if (want > 2) want = 2;
    /* La capacite par bus est celle obtenue APRES refit. Si le bassin
     * physique root+sat ne justifie qu'un vehicule au temps de cycle
     * effectivement prevu, le second n'est pas achete. Sans duree
     * fiable, rester a un seul bus plutot que supposer une cadence. */
    if (portfolioSummary != null && portfolioSummary.joined > 0) {
       local measuredMonthly = ROAD100_PAX_INITIAL_BERTH_FLEET
           || ROAD100_PAX_PRODUCER_UNITS;
       measuredMonthly = measuredMonthly
           && ("road100PaxProducerUnits" in candidate)
           && candidate.road100PaxProducerUnits
           ? candidate.monthly : portfolioSummary.monthly;
      local oneWayDays = ("oneWayDays" in candidate) ?
          candidate.oneWayDays : 0;
      if (measuredMonthly > 0 && oneWayDays > 0) {
        local roundDays = 2 * oneWayDays + 2 * ROAD_PAX_STOP_DWELL_DAYS;
        local perBusMonthly = roundDays > 0 ?
            capacity * 30 / roundDays : 0;
        if (perBusMonthly > 0 && measuredMonthly <= perBusMonthly)
          want = 1;
      }
    }
  }
  if (road100PaxExtraInit != null
      && road100PaxExtraInit.economics.trains > want)
    want = road100PaxExtraInit.economics.trains;
  for (local i = 1; i < want; i++) {
    /* `clone` est un MOT RESERVE de Squirrel (l'operateur de copie) : le nommer ainsi fait echouer
     * la compilation du fichier entier, et l'echec est presque muet -- une seule ligne dans la
     * sortie OpenTTD, aucun panneau, une compagnie qui existe sans rien construire. */
    if (road100PaxExtraInit != null && i >= candidate.trains) {
      local initPrice = AIEngine.GetPrice(candidate.engine.id);
      if (initPrice <= 0 ||
          AICompany.GetBankBalance(AICompany.COMPANY_SELF) <
              initPrice + 50000 ||
          !OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 1)) break;
    }
    if (("road100IntercitySiteFleet" in candidate) && candidate.road100IntercitySiteFleet) {
      local price = AIEngine.GetPrice(candidate.engine.id);
      if (price <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + 25000) break;
    } else if (i >= candidate.trains) {
      local price = AIEngine.GetPrice(candidate.engine.id);
      if (price <= 0) break;
      if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price) break;
    }
    local extra = AIVehicle.CloneVehicle(depot, first, true);
    if (!AIVehicle.IsValidVehicle(extra)) break;
    built.append(extra);
  }

  local started = [];
  local startFailed = false;
  foreach (v in built) {
    if (!AIVehicle.StartStopVehicle(v)) {
      startFailed = true;
      break;
    }
    started.append(v);
  }
  if (startFailed) {
    foreach (v in started) {
      AIVehicle.StartStopVehicle(v);
    }
    result.error = AIError.GetLastError();
    result.opcodes += budget.end("build_road_vehicles");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, depot, built, added, portfolioSatellites);
    result.reason = "START";
    return result;
  }
  /* L'economie de 3/4 bus n'est publiee dans la ligne qu'APRES
   * construction et demarrage effectifs ; aucun bus predit non achete
   * ne peut devenir profit ou capacite. Le supplement de cout des
   * stations jointes est une depense reellement payee deja refletee
   * dans result.cost, pas une recette satellite. */
  if (road100PaxExtraInit != null && built.len() > candidate.trains) {
    local actual = OpexRoad100PaxFixedFleetEconomics(catalog, candidate,
        plan, built.len(), built.len());
    if (actual != null && actual.trains == built.len()) {
      OpexApplyRoadEconomics(candidate, actual, candidate.distance);
      candidate.immobilise = actual.immobilise;
      candidate.iterations = OpexRoadIterations(candidate.distance);
      candidate.ratio = (actual.profitAnnual * 1000) / candidate.iterations;
      result.road100PaxInitialBays <- [
          road100PaxExtraInit.bayA, road100PaxExtraInit.bayB];
    }
    if (DECISION_LOG) OpexDecide("ROAD100_PAX_INITIAL_FLEET",
        "phase=built requested=" + want + " vehicles=" + built.len()
        + " base=" + road100PaxExtraInit.baseTrains
        + " stops_a=" + result.nStopsA + " stops_b=" + result.nStopsB
        + " profit=" + candidate.profitAnnual
        + " cash=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
  }
  result.opcodes += budget.end("build_road_vehicles");

  result.ok = true; result.reason = "OK"; result.stopA = stopA; result.stopB = stopB;
  result.stationA = stationA; result.stationB = stationB; result.depot = depot;
  result.vehicles = built;
  result.capacity = AIVehicle.GetCapacity(first, cargo);
  if (EQUIPMENT_ROI_PROBE) {
    local selectedRefit = ("defaultCargo" in candidate.engine) && candidate.engine.defaultCargo != cargo;
    OpexM3EquipmentLog("mode=road phase=post_refit selected=" + candidate.engine.id
        + " cargo=" + cargo + " selected_refit=" + (selectedRefit ? 1 : 0)
        + " catalog_capacity=" + candidate.engine.capacity + " actual_capacity=" + result.capacity
        + " capacity_delta=" + (result.capacity - candidate.engine.capacity));
  }
  if (ROAD100_JOINED_STOPS && ("road100JoinedStops" in candidate) &&
      candidate.road100JoinedStops) {
    result.road100JoinedStops <- OpexRoad100ExpandJoinedStops(
        catalog, candidate, stopA, stopB, stationA, stationB, costs);
  }
  result.cost = balanceBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  result.actualCost = costs.GetCosts();

  return result;
}

/* ROAD100-14 : un nouvel arret de tour A1 est une STATION DISTINCTE, pas un
 * quai joint a A0. Cette fonction ne change jamais la ligne, ses deux arrets,
 * son depot ou sa flotte. Le caller peut memoriser tile/marginal apres succes.
 * Sans opt-in, aucune commande ni sonde n'est executee. */
function OpexRoad100TryTourAddStop(catalog, line, vehicle)
{
  local result = { ok = false, tile = -1, marginal = 0, cost = 0,
                   ops = 0, reason = "OFF" };
  if (!ROAD100_TOUR) return result;
  local mark = OpexOpsMeasureBegin();
  local startCash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local stationTests = 0;
  local candidatesChecked = 0;
  local roadSitesSeen = 0;
  local finalOrders = -1;
  local stationCount = 2;
  local predDelta = -1;
  local routeB1 = -1;
  local route1B = -1;
  result.reason = "PRECHECK";

  /* Une unique sortie de fonction pour journaliser aussi les refus. Tous les
   * break ci-dessous sortent seulement de cette boucle, sans effet de bord. */
  do {
    if (catalog == null || line == null || !("mode" in line) || line.mode != "road"
        || !("kind" in line) || line.kind != "pax" || !("cargo" in line)
        || !AICargo.HasCargoClass(line.cargo, AICargo.CC_PASSENGERS)
        || !("stationA" in line) || !("stationB" in line)
        || !("nStopsA" in line) || !("nStopsB" in line)
        || line.nStopsA != 1 || line.nStopsB != 1
        || !("distance" in line) || line.distance <= 0
        || !("roadType" in catalog) || catalog.roadType < 0) break;
    if ((("road100TourActive" in line) && line.road100TourActive)
        || (("scrapping" in line) && line.scrapping)) {
      result.reason = "ALREADY_ACTIVE"; break;
    }
    local stopA0 = line.stationA;
    local stopB0 = line.stationB;
    if (!AIRoad.IsRoadStationTile(stopA0) || !AIRoad.IsRoadStationTile(stopB0)
        || stopA0 == stopB0) { result.reason = "STOPS"; break; }
    local idA0 = AIStation.GetStationID(stopA0);
    local idB0 = AIStation.GetStationID(stopB0);
    if (!AIStation.IsValidStation(idA0) || !AIStation.IsValidStation(idB0)
        || idA0 == idB0) { result.reason = "STATION_ID"; break; }
    if (!AIVehicle.IsValidVehicle(vehicle)
        || AIVehicle.GetVehicleType(vehicle) != AIVehicle.VT_ROAD
        || AIVehicle.GetCapacity(vehicle, line.cargo) <= 0
        || AIOrder.GetOrderCount(vehicle) != 2
        || !AIOrder.IsValidVehicleOrder(vehicle, 0)
        || !AIOrder.IsValidVehicleOrder(vehicle, 1)
        || AIOrder.GetOrderDestination(vehicle, 0) != stopA0
        || AIOrder.GetOrderDestination(vehicle, 1) != stopB0) {
      result.reason = "MODEL_ORDERS"; break;
    }
    finalOrders = 2;
    local fleet = OpexLineVehicleIds(line, idA0);
    local hasModel = false;
    foreach (bus in fleet) {
      if (bus == vehicle) hasModel = true;
      if (!AIVehicle.IsValidVehicle(bus)
          || AIOrder.GetOrderCount(bus) != 2
          || AIOrder.GetOrderDestination(bus, 0) != stopA0
          || AIOrder.GetOrderDestination(bus, 1) != stopB0) {
        result.reason = "FLEET_ORDERS"; break;
      }
    }
    if (result.reason == "FLEET_ORDERS") break;
    if (!hasModel || fleet.len() < 1 || fleet.len() > 2) {
      result.reason = "MODEL_FLEET"; break;
    }
    if (!("roadEngineByCargo" in catalog)
        || !(line.cargo in catalog.roadEngineByCargo)) {
      result.reason = "ENGINE"; break;
    }
    local engine = catalog.roadEngineByCargo[line.cargo];
    if (engine == null || engine.id != AIVehicle.GetEngineType(vehicle)) {
      /* La projection d'un autre moteur serait une fausse garantie de ROI. */
      result.reason = "ENGINE"; break;
    }
    AIRoad.SetCurrentRoadType(catalog.roadType);
    local frontA0 = AIRoad.GetRoadStationFrontTile(stopA0);
    local frontB0 = AIRoad.GetRoadStationFrontTile(stopB0);
    if (!AIMap.IsValidTile(frontA0) || !AIMap.IsValidTile(frontB0)
        || !AIRoad.AreRoadTilesConnected(stopA0, frontA0)
        || !AIRoad.AreRoadTilesConnected(stopB0, frontB0)) {
      result.reason = "ORIGIN_CONNECT"; break;
    }
    local townA0 = AITile.GetClosestTown(stopA0);
    if (!AITown.IsValidTown(townA0)) { result.reason = "TOWN"; break; }
    local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
    local price = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP);
    if (price <= 0) { result.reason = "PRICE"; break; }
    if (startCash < 25000 + price + 1000) { result.reason = "CASH"; break; }

    /* Tous les volumes sont evalues UNE FOIS dans une liste native : evaluer
     * GetCargoProduction 12 x (2*coverage+1)^2 fois en Squirrel saturait les
     * 100k opcodes avant le premier AITestMode. La liste couvre chaque A1
     * possible (rayon Manhattan 12 autour de A0), plus le bassin B0. */
    local radiusProduction = 12 + coverage;
    local ax = AIMap.GetTileX(stopA0);
    local ay = AIMap.GetTileY(stopA0);
    local bx = AIMap.GetTileX(stopB0);
    local by = AIMap.GetTileY(stopB0);
    local x0 = ax - radiusProduction; if (x0 < 0) x0 = 0;
    local y0 = ay - radiusProduction; if (y0 < 0) y0 = 0;
    local x1 = ax + radiusProduction;
    if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
    local y1 = ay + radiusProduction;
    if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
    local xB0 = bx - coverage; if (xB0 < 0) xB0 = 0;
    local yB0 = by - coverage; if (yB0 < 0) yB0 = 0;
    local xB1 = bx + coverage;
    if (xB1 >= AIMap.GetMapSizeX()) xB1 = AIMap.GetMapSizeX() - 1;
    local yB1 = by + coverage;
    if (yB1 >= AIMap.GetMapSizeY()) yB1 = AIMap.GetMapSizeY() - 1;
    local production = AITileList();
    production.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
    production.AddRectangle(AIMap.GetTileIndex(xB0, yB0), AIMap.GetTileIndex(xB1, yB1));
    production.Valuate(AITile.GetCargoProduction, line.cargo, 1, 1, 0);
    production.KeepAboveValue(0);
    if (OpexOpsMeasureEnd(mark) >= 100000) { result.reason = "OPCAP"; break; }
    /* Les tuiles productrices sont comptees une seule fois sur les deux gares
     * historiques. A1 ne peut pas reutiliser ces maisons pour se justifier. */
    local coveredA = AITileList_StationCoverage(idA0);
    local coveredB = AITileList_StationCoverage(idB0);
    local covered = AITileList_StationCoverage(idA0);
    covered.AddList(coveredB);
    local monthlyA = 0;
    local monthlyB = 0;
    for (local srcTile = coveredA.Begin(); !coveredA.IsEnd(); srcTile = coveredA.Next()) {
      if (OpexOpsMeasureEnd(mark) >= 100000) break;
      if (production.HasItem(srcTile)) monthlyA += production.GetValue(srcTile);
    }
    for (local srcTile = coveredB.Begin(); !coveredB.IsEnd(); srcTile = coveredB.Next()) {
      if (OpexOpsMeasureEnd(mark) >= 100000) break;
      if (coveredA.HasItem(srcTile)) continue;
      if (production.HasItem(srcTile)) monthlyB += production.GetValue(srcTile);
    }
    if (OpexOpsMeasureEnd(mark) >= 100000) { result.reason = "OPCAP"; break; }
    local monthly = monthlyA + monthlyB;
    if (monthly <= 0) { result.reason = "NO_BASE_DEMAND"; break; }
    local allBusStops = OpexRoadOurBusTiles();
    local baseRoute = line.distance;
    if (!("effectiveSpeed" in line) || line.effectiveSpeed <= 0
        || !("predOneWayDays" in line)
        || line.predOneWayDays <= ROAD_PAX_STOP_DWELL_DAYS) {
      result.reason = "ROI_UNVERIFIED"; break;
    }
    local inferred = ((line.predOneWayDays - ROAD_PAX_STOP_DWELL_DAYS)
                      * 36 * line.effectiveSpeed) / 1000;
    if (inferred > baseRoute) baseRoute = inferred;
    local baseEconomics = OpexRoadLineEconomics(
        catalog, line.cargo, line.distance, monthly, engine, "pax", baseRoute);
    if (baseEconomics == null) { result.reason = "ROI_UNVERIFIED"; break; }
    local busCapacity = AIVehicle.GetCapacity(vehicle, line.cargo);
    local distAB = AIMap.DistanceManhattan(stopA0, stopB0);
    if (busCapacity <= 0 || distAB <= 0) {
      result.reason = "ROI_UNVERIFIED"; break;
    }
    local transitAB = OpexCeilDiv(baseRoute * 1000, 36 * line.effectiveSpeed);
    if (transitAB < 1) transitAB = 1;
    local periodOff = 2 * transitAB + 2 * ROAD_PAX_STOP_DWELL_DAYS;
    local tripsOff = 30.0 * fleet.len() / periodOff;
    local ratingOff = OpexStationRatingForHeadway(periodOff.tofloat() / fleet.len());
    local capOff = tripsOff * busCapacity;
    local offA = monthlyA * ratingOff / 100.0;
    local offB = monthlyB * ratingOff / 100.0;
    if (offA > capOff) offA = capOff;
    if (offB > capOff) offB = capOff;
    local fareAB = AICargo.GetCargoIncome(line.cargo, distAB, transitAB);
    if (fareAB <= 0) { result.reason = "ROI_UNVERIFIED"; break; }
    local offRevenue = 12.0 * (offA + offB) * fareAB;
    local stopAmort = (price * INFRA_AMORT_PCT / 100) / INFRA_LIFE_YEARS;
    /* ROAD100-14 v5 : index CLAIRSEME par colonne des seules maisons
     * productrices NON couvertes. Le prefix dense v4 a consomme davantage
     * d'opcodes que v3 : n'allouer et traverser que les points positifs. */
    local gridW = x1 - x0 + 1;
    local gridH = y1 - y0 + 1;
    local sourcesByX = array(gridW);
    for (local idx = 0; idx < gridW; idx++) sourcesByX[idx] = [];
    for (local producingTile = production.Begin(); !production.IsEnd();
         producingTile = production.Next()) {
      if (OpexOpsMeasureEnd(mark) >= 100000) break;
      if (covered.HasItem(producingTile)) continue;
      local gx = AIMap.GetTileX(producingTile) - x0;
      local gy = AIMap.GetTileY(producingTile) - y0;
      /* La liste comporte egalement le bassin B0, parfois hors grille A0. */
      if (gx < 0 || gy < 0 || gx >= gridW || gy >= gridH) continue;
      sourcesByX[gx].append({ y = gy, amount = production.GetValue(producingTile) });
    }
    if (OpexOpsMeasureEnd(mark) >= 100000) { result.reason = "OPCAP"; break; }
    local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                  AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
    local choices = [];
    /* v5 conserve les bornes v3 : 64 sites routiers, 12 sites positifs,
     * quatre tests STATION_NEW et 100k opcodes cumules (soft). */
    for (local radius = 6; radius <= 12 && candidatesChecked < 12 && roadSitesSeen < 64; radius++) {
      if (OpexOpsMeasureEnd(mark) >= 100000) break;
      for (local dx = -radius; dx <= radius && candidatesChecked < 12 && roadSitesSeen < 64; dx++) {
        if (OpexOpsMeasureEnd(mark) >= 100000) break;
        for (local dy = -radius; dy <= radius && candidatesChecked < 12 && roadSitesSeen < 64; dy++) {
          if (abs(dx) + abs(dy) != radius) continue;
          local x = AIMap.GetTileX(stopA0) + dx;
          local y = AIMap.GetTileY(stopA0) + dy;
          if (!OpexRoadInMap(x, y)) continue;
          local tile = AIMap.GetTileIndex(x, y);
          if (AITile.GetClosestTown(tile) != townA0
              || !AIRoad.IsRoadTile(tile) || AIRoad.IsRoadStationTile(tile)
              || AIRoad.IsRoadDepotTile(tile) || AITile.IsStationTile(tile)) continue;
          local overlaps = false;
          foreach (oldStop in allBusStops) {
            if (AIMap.DistanceManhattan(tile, oldStop) < 6
                || AIMap.DistanceMax(tile, oldStop) <= 2 * coverage) {
              overlaps = true; break;
            }
          }
          if (overlaps) continue;
          roadSitesSeen++;
          /* Somme du rectangle [x+-coverage,y+-coverage] non deja couvert,
           * exacte comme v3 mais sans consultations de listes par cellule. */
          local left = x - coverage - x0;
          local right = x + coverage - x0;
          local top = y - coverage - y0;
          local bottom = y + coverage - y0;
          if (left < 0) left = 0;
          if (top < 0) top = 0;
          if (right >= gridW) right = gridW - 1;
          if (bottom >= gridH) bottom = gridH - 1;
          local marginal = 0;
          for (local scanX = left; scanX <= right; scanX++) {
            foreach (source in sourcesByX[scanX]) {
              if (source.y >= top && source.y <= bottom)
                marginal += source.amount;
            }
          }
          if (marginal > 0) {
            candidatesChecked++;
            choices.append({ tile = tile, marginal = marginal, distance = radius });
          }
        }
      }
    }
    if (OpexOpsMeasureEnd(mark) >= 100000) { result.reason = "OPCAP"; break; }
    choices.sort(OpexRoad100SortJoinedSite);
    if (choices.len() == 0) { result.reason = "NO_MARGINAL"; break; }

    result.reason = "CONNECT";
    local limit = choices.len() < 4 ? choices.len() : 4;
    for (local i = 0; i < limit; i++) {
      if (OpexOpsMeasureEnd(mark) >= 100000) { result.reason = "OPCAP"; break; }
      local choice = choices[i];
      local frontA1 = null;
      local legB = 0;
      local legReturn = 0;
      /* La station DT et les deux chemins utilisent exactement le MEME axe.
       * Aucun bit de route nouveau n'est construit par ce tour. */
      foreach (offset in dirs) {
        local neighbour = choice.tile + offset;
        local opposite = choice.tile - offset;
        if (!AIMap.IsValidTile(neighbour) || !AIMap.IsValidTile(opposite)
            || !AIRoad.AreRoadTilesConnected(choice.tile, neighbour)
            || !AIRoad.AreRoadTilesConnected(choice.tile, opposite)) continue;
        local toA0 = OpexRoadBfsPath(choice.tile, frontA0, 96, neighbour, null);
        if (toA0 == null || toA0.len() == 0) continue;
        local toB0 = OpexRoadBfsPath(choice.tile, frontB0, 96, neighbour, null);
        if (toB0 == null || toB0.len() == 0) continue;
        local fromB0 = OpexRoadBfsPath(frontB0, choice.tile, 96, null, neighbour);
        if (fromB0 == null || fromB0.len() == 0) continue;
        frontA1 = neighbour;
        legB = toB0.len() + 1;
        legReturn = fromB0.len() + 1;
        break;
      }
      if (frontA1 == null) continue;
      routeB1 = legB;
      route1B = legReturn;
      /* Compte d'exploitation par JAMBE. La production A1 n'est pas un
       * revenu : on ne paye que les voyageurs theor. transportables, capes
       * par les visites de la flotte et le rating. Scenario prudent :
       * 50% de la demande propre a A1, une visite A0/A1 au lieu de deux,
       * B0 visite deux fois mais son stock ne peut etre charge deux fois. */
      local travelB1 = OpexCeilDiv(legB * 1000, 36 * line.effectiveSpeed);
      local travel1B = OpexCeilDiv(legReturn * 1000, 36 * line.effectiveSpeed);
      if (travelB1 < 1) travelB1 = 1;
      if (travel1B < 1) travel1B = 1;
      local periodOn = 2 * transitAB + travelB1 + travel1B
                       + 4 * ROAD_PAX_STOP_DWELL_DAYS;
      if (periodOn <= periodOff) { result.reason = "ROI_UNVERIFIED"; continue; }
      local tripsOn = 30.0 * fleet.len() / periodOn;
      local ratingOn = OpexStationRatingForHeadway(periodOn.tofloat() / fleet.len());
      local ratingB = OpexStationRatingForHeadway(periodOn.tofloat() / (2 * fleet.len()));
      local capOn = tripsOn * busCapacity;
      local onA = monthlyA * ratingOn / 100.0;
      local onA1 = (choice.marginal * 0.5) * ratingOn / 100.0;
      local onB = monthlyB * ratingB / 100.0;
      if (onA > capOn) onA = capOn;
      if (onA1 > capOn) onA1 = capOn;
      if (onB > 2 * capOn) onB = 2 * capOn;
      local dist1B = AIMap.DistanceManhattan(choice.tile, stopB0);
      local fare1B = AICargo.GetCargoIncome(line.cargo, dist1B, travel1B);
      local fareB1 = AICargo.GetCargoIncome(line.cargo, dist1B, travelB1);
      if (fare1B <= 0 || fareB1 <= 0) {
        result.reason = "ROI_UNVERIFIED"; continue;
      }
      /* B0 fournit le MEME flux a deux destinations : le tarif minimum
       * pour toutes ses unites evite un credit artificiel. */
      local conservativeB = fareB1 < fareAB ? fareB1 : fareAB;
      local onRevenue = 12.0 * (onA * fareAB + onA1 * fare1B
                              + onB * conservativeB);
      local deltaAnnual = onRevenue - offRevenue - stopAmort;
      predDelta = deltaAnnual.tointeger();
      if (deltaAnnual < 200 || deltaAnnual * 100 < price * 20) {
        result.reason = "ROI"; continue;
      }
      if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 25000 + price + 1000) {
        result.reason = "CASH"; break;
      }
      local canBuild = false;
      { local test = AITestMode();
        canBuild = AIRoad.BuildDriveThroughRoadStation(
            choice.tile, frontA1, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
      }
      stationTests++;
      if (!canBuild) { result.reason = "TEST_STATION"; continue; }
      if (OpexOpsMeasureEnd(mark) >= 100000) { result.reason = "OPCAP"; break; }
      if (AIRoad.IsRoadStationTile(choice.tile) || AITile.IsStationTile(choice.tile)
          || !AIVehicle.IsValidVehicle(vehicle)
          || AIOrder.GetOrderCount(vehicle) != 2
          || AIOrder.GetOrderDestination(vehicle, 0) != stopA0
          || AIOrder.GetOrderDestination(vehicle, 1) != stopB0
          || AIStation.GetStationID(stopA0) != idA0
          || AIStation.GetStationID(stopB0) != idB0) {
        result.reason = "STALE"; break;
      }
      /* La tresorerie evolue meme sans chantier. AIAccounting local isole
       * uniquement la commande A1, jamais les revenus/depenses du jeu
       * pendant les scans et la recherche BFS. */
      local stationAccounting = AIAccounting();
      local built = AIRoad.BuildDriveThroughRoadStation(
          choice.tile, frontA1, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW);
      local paid = stationAccounting.GetCosts();
      stationAccounting = null;
      if (paid < 0) paid = 0;
      local ownedA1 = AIRoad.IsRoadStationTile(choice.tile)
          && AICompany.IsMine(AITile.GetOwner(choice.tile));
      if (ownedA1) result.cost += paid;
      local idA1 = ownedA1 ? AIStation.GetStationID(choice.tile) : AIStation.STATION_INVALID;
      local connectedA1 = false;
      if (built && ownedA1 && AIStation.IsValidStation(idA1)
          && idA1 != idA0 && idA1 != idB0
          && AIRoad.AreRoadTilesConnected(choice.tile, frontA1)) {
        /* IMPORTANT : l'axe peut etre choisi dans un sens ou l'autre.
         * Reprendre l'autre voisin avec la tuile du choix, pas un ancien
         * 'opposite' d'une iteration differente. */
        local backA1 = choice.tile - (frontA1 - choice.tile);
        connectedA1 = AIRoad.AreRoadTilesConnected(choice.tile, backA1)
            && OpexRoadBfsPath(frontA1, frontA0, 96) != null
            && OpexRoadBfsPath(frontA1, frontB0, 96) != null
            && OpexRoadBfsPath(frontB0, frontA1, 96) != null;
      }
      if (!built || !connectedA1 || paid <= 0 || paid * 100 > price * 125
          || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 25000
          || deltaAnnual < 200 || deltaAnnual * 100 < paid * 20) {
        local removedA1 = true;
        /* choice.tile n'etait PAS une station avant le build. Meme un
         * STATION_NEW anormalement joint a A0/B0 doit etre retire, mais
         * uniquement sur cette NOUVELLE tuile, jamais sur l'ancien quai. */
        if (ownedA1)
          removedA1 = AIRoad.RemoveRoadStation(choice.tile);
        result.reason = !removedA1 ? "ROLLBACK" :
                        (!connectedA1 ? "POST_CONNECT" : "COST_ROI");
        if (!removedA1) break;
        continue;
      }
      /* Les deux ajouts agissent sur les ORDRES PARTAGES. Ni A0/B0 ni leurs
       * positions 0/1 ne sont modifies, y compris en cas de rollback. */
      local tourFlags = AIOrder.OF_NONE | AIOrder.OF_NON_STOP_INTERMEDIATE;
      local orderA1 = AIOrder.AppendOrder(vehicle, choice.tile, tourFlags);
      local orderB0 = false;
      if (orderA1 && AIOrder.GetOrderCount(vehicle) == 3)
        orderB0 = AIOrder.AppendOrder(vehicle, stopB0,
                                    AIOrder.GetOrderFlags(vehicle, 1));
      local verified = orderA1 && orderB0 && AIOrder.GetOrderCount(vehicle) == 4;
      if (verified) {
        foreach (bus in fleet) {
          if (!AIVehicle.IsValidVehicle(bus) || AIOrder.GetOrderCount(bus) != 4
              || AIOrder.GetOrderDestination(bus, 0) != stopA0
              || AIOrder.GetOrderDestination(bus, 1) != stopB0
              || AIOrder.GetOrderDestination(bus, 2) != choice.tile
              || AIOrder.GetOrderDestination(bus, 3) != stopB0) {
            verified = false; break;
          }
        }
      }
      if (!verified) {
        /* Retirer exclusivement les deux positions ajoutees, jamais les
         * ordres 0/1, le depot, les routes ou les gares historiques. */
        if (AIOrder.GetOrderCount(vehicle) == 4) AIOrder.RemoveOrder(vehicle, 3);
        if (AIOrder.GetOrderCount(vehicle) == 3) AIOrder.RemoveOrder(vehicle, 2);
        local restoredOrders = AIOrder.GetOrderCount(vehicle) == 2
            && AIOrder.GetOrderDestination(vehicle, 0) == stopA0
            && AIOrder.GetOrderDestination(vehicle, 1) == stopB0;
        if (restoredOrders) {
          foreach (bus in fleet) {
            if (!AIVehicle.IsValidVehicle(bus) || AIOrder.GetOrderCount(bus) != 2
                || AIOrder.GetOrderDestination(bus, 0) != stopA0
                || AIOrder.GetOrderDestination(bus, 1) != stopB0) {
              restoredOrders = false; break;
            }
          }
        }
        local removedA1 = true;
        /* Si les ordres partages restent corrompus, ne JAMAIS effacer leur
         * destination A1. Exposer l'incident critique au caller. */
        if (restoredOrders && ownedA1)
          removedA1 = AIRoad.RemoveRoadStation(choice.tile);
        result.reason = (restoredOrders && removedA1)
            ? "ORDERS" : "ROLLBACK";
        break;
      }
      result.ok = true;
      result.tile = choice.tile;
      result.marginal = choice.marginal;
      stationCount = 3;
      finalOrders = 4;
      result.reason = "OK";
      OpexAir0310InvalidateSiteValidity();
      break;
    }
    if (result.reason == "PRECHECK") result.reason = "NO_CANDIDATE";
  } while (false);

  result.ops = OpexOpsMeasureEnd(mark);
  if (DECISION_LOG) OpexDecide("ROAD100_TOUR",
      "line=" + (line != null && ("lineId" in line) ? line.lineId : -1)
      + " reason=" + result.reason + " tile=" + result.tile
      + " marginal=" + result.marginal + " paid=" + result.cost
      + " ops=" + result.ops + " candidates=" + candidatesChecked
      + " road_sites_seen=" + roadSitesSeen
      + " tests=" + stationTests + " stations=" + stationCount
      + " orders=" + finalOrders
      + " route_b1=" + routeB1 + " route_1b=" + route1B
      + " pred_delta=" + predDelta
      + " cash_before=" + startCash
      + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
      + " tick_left=" + AIController.GetOpsTillSuspend());
  return result;
}

/* Reconstitue la flotte d'une ligne routiere dont les vehicules ont disparu (age, destruction
 * a un passage a niveau, renouvellement qui n'a pas suivi). L'infrastructure est deja payee :
 * on ne replanifie rien. Si un vehicule reste, on le clone (ordres partages). S'il n'en reste
 * aucun, on reconstitue moteur + ordres comme a la construction. N'ajoute jamais au-dela du
 * plafond de quais de la ligne (2 x min(nStopsA, nStopsB), au moins deux vehicules).
 * Rend { added, after, reason }. */
/* ROAD100-24 : élargir PHYSIQUEMENT les deux quais fret d'une ligne
 * EXISTANTE. Ni production ni recettes ne sont credités : ce sont les
 * livraisons et le profit de l'exercice clos qui justifient ensuite
 * un refleet. Une seule pose par extrémité; STATION_NEW est interdit.
 * Pas de route neuve, donc aucun A* ni dépense routière implicite. */
/* ROAD100-27b : long MAIL uniquement sur voirie PREEXISTANTE et connectee.
 * Contrairement au planner LONG, aucune nouvelle arete n'est proposee.
 * Les fronts doivent etre des routes reliees dans les DEUX directions,
 * les arrets camion restent sur les deux tuiles distinctes hors du trace.
 * Les tests AITestMode de sites viennent de OpexRoadSites, et le depot
 * de OpexRoadFindDepot ; le constructeur les revalide en commandes reelles. */
function OpexRoad100MailExistingConnectedPlan(catalog, candidate)
{
  if (!ROAD100_MAIL_LONG_EXISTING || catalog == null || candidate == null
      || candidate.kind != "freight" || candidate.cargo != catalog.mailCargo
      || candidate.srcTown < 0 || candidate.dstTown < 0
      || candidate.srcTown == candidate.dstTown) return null;
  local stop = OpexRoadStopKind(candidate.cargo);
  if (stop.vehType != AIRoad.ROADVEHTYPE_TRUCK
      || stop.stationType != AIStation.STATION_TRUCK_STOP) return null;
  local centerDistance = AIMap.DistanceManhattan(candidate.src, candidate.dst);
  if (centerDistance < 43 || centerDistance > 80) return null;
  local coverage = AIStation.GetCoverageRadius(stop.stationType);
  local foundA = OpexRoadSites(candidate.src, candidate.srcTown, candidate.cargo,
      stop.vehType, coverage, true, ROAD_TOWN_SEARCH_RADIUS, candidate.dst,
      true, null, true);
  local foundB = OpexRoadSites(candidate.dst, candidate.dstTown, candidate.cargo,
      stop.vehType, coverage, false, ROAD_TOWN_SEARCH_RADIUS, candidate.src,
      true, null, true);
  if (foundA == null || foundB == null
      || foundA.sites == null || foundB.sites == null) return null;
  if (foundA.sites.len() == 0 || foundB.sites.len() == 0) {
    if (DECISION_LOG) OpexDecide("ROAD100_MAIL_LONG",
        "phase=reject reason=" + (foundA.sites.len() == 0 ? "SITE_A" : "SITE_B")
        + " srcTown=" + candidate.srcTown + " dstTown=" + candidate.dstTown
        + " sitesA=" + foundA.sites.len() + " sitesB=" + foundB.sites.len());
    return null;
  }
  local tested = 0;
  local noRoad = 0;
  local noConnected = 0;
  local noLength = 0;
  local noStop = 0;
  local noDepot = 0;
  foreach (siteA in foundA.sites) {
    if (tested >= 4) break;
    if (siteA.value <= 0 || !AIRoad.IsRoadTile(siteA.front)) {
      noRoad++;
      continue;
    }
    foreach (siteB in foundB.sites) {
      if (tested >= 4) break;
      if (siteB.value < ROAD_ACCEPTANCE_FULL_UNIT
          || !AIRoad.IsRoadTile(siteB.front)
          || siteA.tile == siteB.tile || siteA.front == siteB.front) {
        noRoad++;
        continue;
      }
      tested++;
      local direct = OpexRoadBfsPath(siteA.front, siteB.front, 256);
      if (direct == null) { noConnected++; continue; }
      if (direct.len() < 40 || direct.len() > 128) { noLength++; continue; }
      if (OpexRoadTraceHitsStop(direct, siteA.tile)
          || OpexRoadTraceHitsStop(direct, siteB.tile)) { noStop++; continue; }
      local reverse = OpexRoadBfsPath(siteB.front, siteA.front, 256);
      if (reverse == null) { noConnected++; continue; }
      if (reverse.len() < 40 || reverse.len() > 128) { noLength++; continue; }
      if (OpexRoadTraceHitsStop(reverse, siteA.tile)
          || OpexRoadTraceHitsStop(reverse, siteB.tile)) { noStop++; continue; }
      /* Le depot peut s'ancrer a la voirie existante ; aucun segment
       * d'interville n'est construit ou comptabilise fictivement. */
      local depot = OpexRoadFindDepot(direct, siteA, siteB);
      if (depot == null || !AIMap.IsValidTile(depot.tile)) {
        noDepot++;
        continue;
      }
      if (DECISION_LOG) OpexDecide("ROAD100_MAIL_LONG",
          "phase=plan srcTown=" + candidate.srcTown + " dstTown=" + candidate.dstTown
          + " tested=" + tested + " route=" + direct.len());
      return {
        stopA = siteA, stopB = siteB, trace = direct, depot = depot,
        stationType = stop.stationType, vehType = stop.vehType,
        routeDistance = direct.len(), shape = 270, trials = tested,
        road100MailExisting = true
      };
    }
  }
  if (DECISION_LOG) OpexDecide("ROAD100_MAIL_LONG",
      "phase=reject reason=NO_PLAN srcTown=" + candidate.srcTown
      + " dstTown=" + candidate.dstTown + " sitesA=" + foundA.sites.len()
      + " sitesB=" + foundB.sites.len() + " tested=" + tested
      + " no_road=" + noRoad + " no_conn=" + noConnected
      + " no_length=" + noLength + " no_stop=" + noStop
      + " no_depot=" + noDepot);
  return null;
}

/* Conservateur par construction : le modele standard impute encore
 * routeDistance * costRoadPerTile bien que le corridor existe deja.
 * Ne jamais accroître revenu/profit/ROI sans devis du coût effectivement
 * evite, et ne jamais ajouter de courrier B->A non livre. */
function OpexRoad100MailExistingEconomics(catalog, economics, plan)
{
  if (!ROAD100_MAIL_LONG_EXISTING || catalog == null || economics == null
      || plan == null || !("road100MailExisting" in plan)
      || !plan.road100MailExisting || plan.trace == null
      || plan.trace.len() != plan.routeDistance
      || plan.stationType != AIStation.STATION_TRUCK_STOP
      || plan.vehType != AIRoad.ROADVEHTYPE_TRUCK) return null;
  return economics;
}

function OpexRoad100FreightBerthGrow(catalog, line, have, waitingSource)
{
  local out = { ok = false, reason = "OFF", a = -1, b = -1,
      cost = 0, ops = 0, tested = 0, sites = 0 };
  if (!ROAD100_FREIGHT_BERTHS || catalog == null || line == null ||
      !("kind" in line) || line.kind != "freight" ||
      have < 2 || !("capacity" in line) || line.capacity <= 0 ||
      waitingSource < 3 * line.capacity ||
      !("lastProfit" in line) || line.lastProfit < 3000 ||
      !("nStopsA" in line) || !("nStopsB" in line) ||
      line.nStopsA != 1 || line.nStopsB != 1) return out;
  local mark = OpexOpsMeasureBegin();
  local roots = [line.stationA, line.stationB];
  local ids = [];
  local fronts = [];
  local spread = AIGameSettings.GetValue("station.station_spread");
  local price = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_TRUCK_STOP);
  out.reason = "PRECHECK";
  if (spread < 3 || price <= 0 ||
      AICompany.GetBankBalance(AICompany.COMPANY_SELF) <
          50000 + 2 * price + 2 * 20000) return out;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  foreach (root in roots) {
    if (!AIMap.IsValidTile(root) || !AIRoad.IsRoadStationTile(root) ||
        !AICompany.IsMine(AITile.GetOwner(root))) return out;
    local id = AIStation.GetStationID(root);
    local front = AIRoad.GetRoadStationFrontTile(root);
    if (!AIStation.IsValidStation(id) || !AIMap.IsValidTile(front) ||
        !AIRoad.AreRoadTilesConnected(root, front)) return out;
    ids.append(id);
    fronts.append(front);
  }
  if (ids[0] == ids[1]) return out;

  local planned = [];
  local delta = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                 AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  for (local end = 0; end < 2; end++) {
    local root = roots[end];
    local cx = AIMap.GetTileX(root);
    local cy = AIMap.GetTileY(root);
    local r = spread - 1;
    if (r > 4) r = 4;
    local x0 = cx - r; if (x0 < 0) x0 = 0;
    local y0 = cy - r; if (y0 < 0) y0 = 0;
    local x1 = cx + r; if (x1 >= AIMap.GetMapSizeX()) x1 = AIMap.GetMapSizeX() - 1;
    local y1 = cy + r; if (y1 >= AIMap.GetMapSizeY()) y1 = AIMap.GetMapSizeY() - 1;
    local roads = AITileList();
    roads.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
    roads.Valuate(AIRoad.IsRoadTile);
    roads.KeepAboveValue(0);
    local selected = null;
    local visited = 0;
    foreach (tile, value in roads) {
      if (visited >= 12 || out.tested >= 4 || OpexOpsMeasureEnd(mark) >= 60000) break;
      if (tile == root || tile == roots[1 - end] ||
          AIMap.DistanceManhattan(tile, root) < 2 ||
          AIMap.DistanceManhattan(tile, root) > 4 ||
          AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile) ||
          AITile.IsStationTile(tile)) continue;
      visited++;
      local wx = AIMap.GetTileX(tile);
      local wy = AIMap.GetTileY(tile);
      for (local dir = 0; dir < 4; dir++) {
        if (out.tested >= 4 || OpexOpsMeasureEnd(mark) >= 60000) break;
        local f = tile + delta[dir];
        local back = tile - delta[dir];
        if (!AIMap.IsValidTile(f) || !AIMap.IsValidTile(back) ||
            AIMap.DistanceManhattan(tile, f) != 1 ||
            AIMap.DistanceManhattan(tile, back) != 1 ||
            !AIRoad.IsRoadTile(f) || !AIRoad.IsRoadTile(back) ||
            !AIRoad.AreRoadTilesConnected(tile, f) ||
            !AIRoad.AreRoadTilesConnected(tile, back)) continue;
        local px = wx < cx ? wx : cx;
        local qx = wx > cx ? wx : cx;
        local py = wy < cy ? wy : cy;
        local qy = wy > cy ? wy : cy;
        if (qx - px >= spread || qy - py >= spread ||
            OpexRoadBfsPath(f, fronts[end], 96) == null ||
            OpexRoadBfsPath(fronts[end], f, 96) == null) continue;
        out.tested++;
        local canBuild = false;
        { local test = AITestMode();
          canBuild = AIRoad.BuildDriveThroughRoadStation(tile, f,
              AIRoad.ROADVEHTYPE_TRUCK, ids[end]); }
        if (canBuild) { selected = { tile = tile, front = f, back = back }; break; }
      }
      if (selected != null) break;
    }
    out.sites += visited;
    if (selected == null) {
      out.reason = OpexOpsMeasureEnd(mark) >= 60000 ? "OPCAP" : "NO_SITE";
      break;
    }
    planned.append(selected);
  }
  if (planned.len() == 2 && OpexOpsMeasureEnd(mark) < 60000) {
    local placed = [];
    local allConnected = true;
    local cashBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    out.reason = "BUILD";
    for (local end = 0; end < 2; end++) {
      local p = planned[end];
      if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + 50000 + 20000)
        break;
      local built = AIRoad.BuildDriveThroughRoadStation(p.tile, p.front,
          AIRoad.ROADVEHTYPE_TRUCK, ids[end]);
      local ours = AIRoad.IsRoadStationTile(p.tile) &&
          AICompany.IsMine(AITile.GetOwner(p.tile)) &&
          AIStation.GetStationID(p.tile) == ids[end];
      if (ours) placed.append(p.tile);
      if (!built || !ours || !AIRoad.AreRoadTilesConnected(p.tile, p.front) ||
          !AIRoad.AreRoadTilesConnected(p.tile, p.back) ||
          !AIRoad.AreRoadTilesConnected(p.front, p.tile) ||
          !AIRoad.AreRoadTilesConnected(p.back, p.tile)) {
        allConnected = false;
        break;
      }
    }
    if (allConnected && placed.len() == 2 &&
        AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= 50000 + 20000) {
      out.a = placed[0]; out.b = placed[1];
      out.cost = cashBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
      out.ok = out.cost > 0;
      out.reason = out.ok ? "OK" : "COST";
    }
    if (!out.ok) {
      local removed = true;
      for (local i = placed.len() - 1; i >= 0; i--) {
        if (!AIRoad.RemoveRoadStation(placed[i])) removed = false;
      }
      if (!removed) out.reason = "ROLLBACK";
    }
  } else if (planned.len() == 2) {
    out.reason = "OPCAP";
  }
  out.ops = OpexOpsMeasureEnd(mark);
  if (DECISION_LOG) OpexDecide("ROAD100_FREIGHT_BERTHS",
      "phase=build line=" + line.lineId + " reason=" + out.reason
      + " ok=" + out.ok + " a=" + out.a + " b=" + out.b
      + " paid=" + out.cost + " ops=" + out.ops
      + " tested=" + out.tested + " visited=" + out.sites);
  return out;
}

/* ROAD100-26 : un SEUL quai de bus rejoint physiquement le StationID du
 * terminus limitant d'une ligne PAX mature. Pas de revenu, nouvel ordre,
 * nouvelle route ni ligne nouvelle : le seul gain éventuel sera le profit
 * annuel des bus effectivement clonés et faisant des livraisons. */
function OpexRoad100PaxBalanceBerth(catalog, line, side)
{
  local out = { ok = false, reason = "OFF", tile = -1, side = side,
      paid = 0, ops = 0, tested = 0, visited = 0 };
  if (!(ROAD100_PAX_BERTH_BALANCE || ROAD100_PAX_DOUBLE_BERTHS) || catalog == null || line == null
      || !("kind" in line) || line.kind != "pax"
      || (side != 0 && side != 1)) return out;
  local mark = OpexOpsMeasureBegin();
  local root = side == 0 ? line.stationA : line.stationB;
  local other = side == 0 ? line.stationB : line.stationA;
  local spread = AIGameSettings.GetValue("station.station_spread");
  local price = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP);
  out.reason = "PRECHECK";
  if (spread < 3 || price <= 0
      || !AIMap.IsValidTile(root) || !AIMap.IsValidTile(other)
      || !AIRoad.IsRoadStationTile(root) || !AIRoad.IsRoadStationTile(other)
      || !AICompany.IsMine(AITile.GetOwner(root))
      || !AICompany.IsMine(AITile.GetOwner(other))
      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 50000 + 2 * price + 20000) {
    out.ops = OpexOpsMeasureEnd(mark);
    return out;
  }
  local id = AIStation.GetStationID(root);
  local otherId = AIStation.GetStationID(other);
  local rootFront = AIRoad.GetRoadStationFrontTile(root);
  if (!AIStation.IsValidStation(id) || !AIStation.IsValidStation(otherId)
      || id == otherId || !AIMap.IsValidTile(rootFront)
      || !AIRoad.AreRoadTilesConnected(root, rootFront)) {
    out.ops = OpexOpsMeasureEnd(mark);
    return out;
  }
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local cx = AIMap.GetTileX(root);
  local cy = AIMap.GetTileY(root);
  local maxRadius = spread - 1;
  if (maxRadius > 4) maxRadius = 4;
  local delta = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                 AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  out.reason = "NO_SITE";
  local finished = false;
  /* Rayons croissants, 12 sites de route au maximum, quatre tests de station.
   * L'inventaire simple évite Valuate et la surcharge de mémoire de listes. */
  for (local radius = 2; radius <= maxRadius && !finished; radius++) {
    for (local dx = -radius; dx <= radius && !finished; dx++) {
      for (local dy = -radius; dy <= radius && !finished; dy++) {
        if (out.visited >= 12 || out.tested >= 4
            || OpexOpsMeasureEnd(mark) >= 40000) break;
        local adx = dx < 0 ? -dx : dx;
        local ady = dy < 0 ? -dy : dy;
        if (adx + ady != radius) continue;
        local x = cx + dx; local y = cy + dy;
        if (x < 0 || y < 0 || x >= AIMap.GetMapSizeX() || y >= AIMap.GetMapSizeY()) continue;
        local tile = AIMap.GetTileIndex(x, y);
        if (tile == other || !AIRoad.IsRoadTile(tile)
            || AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile)
            || AITile.IsStationTile(tile)) continue;
        out.visited++;
        for (local d = 0; d < 4; d++) {
          if (out.tested >= 4 || OpexOpsMeasureEnd(mark) >= 40000) break;
          local f = tile + delta[d];
          local back = tile - delta[d];
          if (!AIMap.IsValidTile(f) || !AIMap.IsValidTile(back)
              || AIMap.DistanceManhattan(tile, f) != 1
              || AIMap.DistanceManhattan(tile, back) != 1
              || !AIRoad.IsRoadTile(f) || !AIRoad.IsRoadTile(back)
              || !AIRoad.AreRoadTilesConnected(tile, f)
              || !AIRoad.AreRoadTilesConnected(tile, back)
              || OpexRoadBfsPath(f, rootFront, 96) == null
              || OpexRoadBfsPath(rootFront, f, 96) == null) continue;
          out.tested++;
          local canBuild = false;
          { local test = AITestMode();
            canBuild = AIRoad.BuildDriveThroughRoadStation(tile, f,
                AIRoad.ROADVEHTYPE_BUS, id); }
          if (!canBuild) continue;
          if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + 70000) {
            out.reason = "CASH";
            break;
          }
          local cashBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
          out.reason = "BUILD";
          local built = AIRoad.BuildDriveThroughRoadStation(tile, f,
              AIRoad.ROADVEHTYPE_BUS, id);
          local ours = AIRoad.IsRoadStationTile(tile)
              && AICompany.IsMine(AITile.GetOwner(tile))
              && AIStation.GetStationID(tile) == id;
          local connected = built && ours
              && AIRoad.AreRoadTilesConnected(tile, f)
              && AIRoad.AreRoadTilesConnected(tile, back)
              && AIRoad.AreRoadTilesConnected(f, tile)
              && AIRoad.AreRoadTilesConnected(back, tile);
          if (connected && cashBefore > AICompany.GetBankBalance(AICompany.COMPANY_SELF)
              && AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= 70000) {
            out.ok = true;
            out.tile = tile;
            out.paid = cashBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
            out.reason = "OK";
          } else {
            if (ours && !AIRoad.RemoveRoadStation(tile)) out.reason = "ROLLBACK";
            else out.reason = "VERIFY";
          }
          /* Une commande effective au maximum, même si l'API échoue :
           * jamais de seconde pose après rollback incertain. */
          finished = true;
          break;
        }
      }
    }
  }
  if (OpexOpsMeasureEnd(mark) >= 40000 && out.reason == "NO_SITE") out.reason = "OPCAP";
  out.ops = OpexOpsMeasureEnd(mark);
  if (DECISION_LOG) OpexDecide("ROAD100_PAX_BERTH",
      "phase=build line=" + line.lineId + " side=" + side
      + " reason=" + out.reason + " ok=" + out.ok
      + " tile=" + out.tile + " paid=" + out.paid + " ops=" + out.ops
      + " tested=" + out.tested + " visited=" + out.visited);
  return out;
}

function OpexRoadRefleet(catalog, line, have, target)
{
  local result = { added = 0, after = have, reason = "OK" };
  local missing = target - have;
  if (missing <= 0) { result.reason = "FULL"; return result; }
  if (!("depot" in line) || line.depot == null || !AIRoad.IsRoadDepotTile(line.depot)) {
    result.reason = "NODEPT"; return result;
  }
  if (!AIRoad.IsRoadStationTile(line.stationA) || !AIRoad.IsRoadStationTile(line.stationB)) {
    result.reason = "STN"; return result;
  }
  AIRoad.SetCurrentRoadType(catalog.roadType);

  local template = null;
  if (have > 0) {
    local existing = OpexLineVehicleIds(line, AIStation.GetStationID(line.stationA));
    foreach (v in existing) {
      if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_ROAD) {
        template = v;
        break;
      }
    }
  }

  local engine = (line.cargo in catalog.roadEngineByCargo) ? catalog.roadEngineByCargo[line.cargo] : null;
  local unitPrice = 0;
  if (template != null) {
    unitPrice = AIEngine.GetPrice(AIVehicle.GetEngineType(template));
  } else if (engine != null) {
    unitPrice = engine.price;
  } else {
    result.reason = "NOENG"; return result;
  }
  if (unitPrice <= 0) { result.reason = "PRICE"; return result; }
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local affordable = money / unitPrice;
  if (affordable < 1) { result.reason = "CASH"; return result; }
  if (missing > affordable) missing = affordable;

  local built = [];
  if (template != null) {
    for (local i = 0; i < missing; i++) {
      local extra = AIVehicle.CloneVehicle(line.depot, template, true);
      if (!AIVehicle.IsValidVehicle(extra)) {
        if (built.len() == 0) { result.reason = "CLONE"; return result; }
        break;
      }
      built.append(extra);
    }
  } else {
    if (OpexRoadRefitCapacity(line.depot, engine, line.cargo) <= 0) {
      result.reason = "REFIT"; return result;
    }
    local first = AIVehicle.BuildVehicleWithRefit(line.depot, engine.id, line.cargo);
    if (!AIVehicle.IsValidVehicle(first)) { result.reason = "VEH"; return result; }
    built.append(first);
    local nonstopFlag = AIOrder.OF_NON_STOP_INTERMEDIATE;
    local isFreight = (("kind" in line) && line.kind == "freight");
    local sourceFlags = (isFreight ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE) | nonstopFlag;
    local destFlags = AIOrder.OF_NONE;
    destFlags = destFlags | nonstopFlag;
    /* ROAD100-14 : les ordres persistants d'une ligne convertie survivent
     * a la disparition de sa flotte. Ne pas conditionner cette reconstitution
     * au switch de CREATION : ON -> OFF ne doit pas casser une ligne payee. */
    local tourActive = ("road100TourActive" in line) && line.road100TourActive;
    local tourValid = false;
    local tourTile = -1;
    if (tourActive && ("road100TourStops" in line)
        && typeof line.road100TourStops == "array"
        && line.road100TourStops.len() == 4) {
      tourTile = line.road100TourStops[2];
      if (AIMap.IsValidTile(tourTile) && AIRoad.IsRoadStationTile(tourTile)
          && AICompany.IsMine(AITile.GetOwner(tourTile))) {
        local midId = AIStation.GetStationID(tourTile);
        local aId = AIStation.GetStationID(line.stationA);
        local bId = AIStation.GetStationID(line.stationB);
        tourValid = AIStation.IsValidStation(midId) && midId != aId && midId != bId;
      }
    }
    if (tourActive && !tourValid) {
      line.road100TourActive = false;
      if (DECISION_LOG) OpexDecide("ROAD100_TOUR", "phase=refleet_recover line="
          + line.lineId + " reason=LOST_A1");
    }
    if (!AIOrder.AppendOrder(first, line.stationA, sourceFlags) ||
        !AIOrder.AppendOrder(first, line.stationB, destFlags) ||
        (tourValid && (!AIOrder.AppendOrder(first, tourTile, destFlags)
            || !AIOrder.AppendOrder(first, line.stationB, destFlags))) ||
        AIOrder.GetOrderCount(first) != (tourValid ? 4 : 2)) {
      AIVehicle.SellVehicle(first);
      result.reason = "ORDER"; return result;
    }
    for (local i = 1; i < missing; i++) {
      local extra = AIVehicle.CloneVehicle(line.depot, first, true);
      if (!AIVehicle.IsValidVehicle(extra)) break;
      built.append(extra);
    }
  }

  foreach (v in built) {
    if (!AIVehicle.StartStopVehicle(v)) {
      if (AIVehicle.IsStoppedInDepot(v)) AIVehicle.SellVehicle(v);
      else AIVehicle.SendVehicleToDepot(v);
    } else {
      result.added++;
    }
  }
  if (result.added == 0) { result.reason = "START"; return result; }
  result.after = have + result.added;
  return result;
}
