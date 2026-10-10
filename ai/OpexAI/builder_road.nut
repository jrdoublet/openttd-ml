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

ROAD_MAX_TRACE_TILES <- 48;
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
ROAD_PAX_VOIRIE <- true;
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
                       otherCenter, requireCargo = true, excludeTiles = null)
{
  if (EXP_OPCODE_EXACT_ON) return OpexRoadSitesGated(center, townId, cargo, vehType, coverage, wantProduction, radius, otherCenter, requireCargo, excludeTiles);
  local out = [];
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local probes = 0;
  local nCargo = 0;
  local nBuildable = 0;
  local nCmd = 0;
  for (local r = 0; r <= radius && probes < ROAD_MAX_SITE_PROBES; r++) {
    for (local dx = -r; dx <= r && probes < ROAD_MAX_SITE_PROBES; dx++) {
      for (local dy = -r; dy <= r && probes < ROAD_MAX_SITE_PROBES; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local x = cx + dx;
        local y = cy + dy;
        if (!OpexRoadInMap(x, y)) continue;
        local tile = AIMap.GetTileIndex(x, y);
        if (townId >= 0 && AITile.GetClosestTown(tile) != townId) continue;
        /* Espacement global minimal entre deux arrets passagers. */
        if (excludeTiles != null && excludeTiles.len() > 0) {
          local tooClose = false;
          foreach (exTile in excludeTiles) {
            if (AIMap.DistanceManhattan(tile, exTile) < ROAD_BUS_STOP_MIN_DISTANCE) {
              tooClose = true;
              break;
            }
          }
          if (tooClose) continue;
        }
        local value = wantProduction
            ? AITile.GetCargoProduction(tile, cargo, 1, 1, coverage)
            : AITile.GetCargoAcceptance(tile, cargo, 1, 1, coverage);
        if (requireCargo && (wantProduction ? (value <= 0) : (value < ROAD_ACCEPTANCE_FULL_UNIT))) continue;
        nCargo++;
        /* CheckFlatLandRoadStop ne regarde QUE la tuile de l'arret. Un batiment d'industrie ou
         * une maison a du cargo et brule le plafond de 48 sondes : 12 tuiles x 4 facades, et
         * on n'atteint jamais l'herbe a r = 2. Meme filtre que OpexStationPlans. */
        if (!AITile.IsBuildable(tile) || !OpexRoadIsFlat(tile)) continue;
        nBuildable++;
        foreach (offset in offsets) {
          if (probes >= ROAD_MAX_SITE_PROBES) break;
          local fx = x + offset[0];
          local fy = y + offset[1];
          if (!OpexRoadInMap(fx, fy)) continue;
          local front = AIMap.GetTileIndex(fx, fy);
          /* La facade portera DEUX axes de route : celui du trace et le raccord vers l'arret. Elle
           * doit donc etre plate -- cf. OpexRoadIsFlat. Une facade deja routiere n'est pas
           * "buildable" : ne pas l'exiger. */
          if (!OpexRoadIsFlat(front)) continue;
          if (!AIRoad.IsRoadTile(front) && !AITile.IsBuildable(front)) continue;
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
          nCmd++;
          local onRoad = AIRoad.IsRoadTile(front);
          /* Facade tournee vers l'autre extremite : le L part du front, pas de l'arret, et
           * n'a pas a retraverser le corps (mesure TRACEX 2026-08-30 : ~moitie des L etaient
           * nHit). Le cargo reste le critere dominant (x2). */
          local toward = 0;
          if (otherCenter != null &&
              AIMap.DistanceManhattan(front, otherCenter) < AIMap.DistanceManhattan(tile, otherCenter)) {
            toward = 2;
          }
          /* Le bonus de facade routiere n'est qu'un departage : il ne doit jamais faire passer un
           * site deux fois moins productif devant un autre, d'ou le facteur 2 sur la valeur. */
          local site = { tile = tile, front = front, value = value,
                         score = value * 2 + toward + (onRoad ? 1 : 0) };
          local pos = out.len();
          while (pos > 0 && out[pos - 1].score < site.score) pos--;
          out.insert(pos, site);
          if (out.len() > ROAD_MAX_SITES_PER_END) out.pop();
        }
      }
    }
  }
  return { sites = out, nCargo = nCargo, nBuildable = nBuildable, nCmd = nCmd, probes = probes };
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
  if (EXP_OPCODE_EXACT_ON) return OpexRoadPaxVoirieGated(center, townId, cargo, vehType, coverage, otherCenter, requireCargo, excludeTiles);
  local out = [];
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1)];
  local probes = 0;
  local radius = ROAD_TOWN_SEARCH_RADIUS;
  local sameTown = otherCenter != null &&
                   AIMap.DistanceManhattan(center, otherCenter) < ROAD_PAX_VOIRIE_SAME_TOWN_MAX_DIST;
  local minPair = ROAD_PAX_VOIRIE_MIN_PAIR;
  for (local r = 0; r <= radius; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        local adx = dx < 0 ? -dx : dx;
        local ady = dy < 0 ? -dy : dy;
        if (r > 0 && adx != r && ady != r) continue;
        if (!OpexRoadInMap(cx + dx, cy + dy)) continue;
        local tile = AIMap.GetTileIndex(cx + dx, cy + dy);
        if (townId >= 0 && AITile.GetClosestTown(tile) != townId) continue;
        if (!AIRoad.IsRoadTile(tile)) continue;
        if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile)) continue;
        if (OpexRoadTileTooClose(tile, excludeTiles, minPair)) continue;
        local value = AITile.GetCargoProduction(tile, cargo, 1, 1, coverage);
        if (requireCargo && value <= 0) continue;
        foreach (dir in dirs) {
          if (probes >= ROAD_MAX_SITE_PROBES) return out;
          local front = tile + dir;
          if (!AIMap.IsValidTile(front) || !AIRoad.IsRoadTile(front)) continue;
          local ok = false;
          { local test = AITestMode();
            ok = AIRoad.BuildDriveThroughRoadStation(tile, front, vehType, AIStation.STATION_NEW); }
          probes++;
          if (!ok) continue;
          local score;
          if (sameTown) {
            local ring = AIMap.DistanceManhattan(tile, center);
            local ringPen = ring > 3 ? ring - 3 : 3 - ring;
            score = value * 2 - ringPen * 4;
          } else {
            local dOther = (otherCenter != null) ? AIMap.DistanceManhattan(tile, otherCenter) : 0;
            score = value * 2 - dOther;
          }
          local site = { tile = tile, front = front, value = value, score = score };
          local pos = out.len();
          while (pos > 0 && out[pos - 1].score < site.score) pos--;
          out.insert(pos, site);
          if (out.len() > ROAD_MAX_SITES_PER_END) out.pop();
          break;
        }
      }
    }
  }
  return out;
}

function OpexRoadPlanPaxVoirie(candidate)
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
      local d = AIMap.DistanceManhattan(siteA.tile, siteB.tile);
      if (d < minPair) { nClose++; continue; }
      pairs.append({ a = siteA, b = siteB, d = d });
    }
  }
  pairs.sort(function(x, y) {
    if (x.d < y.d) return -1;
    if (x.d > y.d) return 1;
    return 0;
  });
  local nBfs = 0;
  local nBfsNoDepot = 0;
  local nL = 0;
  local nLNoDepot = 0;
  foreach (pair in pairs) {
    local siteA = pair.a;
    local siteB = pair.b;
    local trace = OpexRoadBfsPath(siteA.tile, siteB.tile, 96, siteA.front, siteB.front);
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
  if (DECISION_LOG) {
    local minD = (pairs.len() > 0) ? pairs[0].d : -1;
    OpexDecide("VOIRIE_PLAN", "fail=DEPOT nA=" + sitesA.len() + " nB=" + sitesB.len()
               + " nPairs=" + pairs.len() + " minD=" + minD + " nClose=" + nClose
               + " nBfs=" + nBfs + " nBfsNoDepot=" + nBfsNoDepot
               + " nL=" + nL + " nLNoDepot=" + nLNoDepot);
  }
  return null;
}

/* Plan concret d'UN candidat routier. Le candidat porte deja la paire, le cargo et le sens ; il
 * reste a trouver deux sites d'arret reels et un trace multi-variantes qui les relie. */
function OpexRoadPlanFor(catalog, candidate)
{
  if (EXP_OPCODE_EXACT_ON) return OpexRoadPlanForActive(catalog, candidate);
  if (catalog.roadType < 0) return { plan = null, reason = "NOROAD" };
  AIRoad.SetCurrentRoadType(catalog.roadType);
  if (ROAD_PAX_VOIRIE && candidate.kind == "pax") {
    /* Intra-ville (town_growth) : le DT rate le depot (maisons le long de la rue) et
     * brulait 50+ chasses/an avant le L cul-de-sac. Aller directement au plan historique. */
    local sameTown = candidate.srcTown >= 0 && candidate.srcTown == candidate.dstTown;
    if (!sameTown) {
      local voirie = OpexRoadPlanPaxVoirie(candidate);
      if (voirie != null) return { plan = voirie, reason = "OK" };
      if (DECISION_LOG) {
        OpexDecide("VOIRIE_PLAN", "fail=FALLBACK srcTown=" + candidate.srcTown
                   + " dstTown=" + candidate.dstTown);
      }
    }
  }
  local stop = OpexRoadStopKind(candidate.cargo);
  local coverage = AIStation.GetCoverageRadius(stop.stationType);
  local radiusA = candidate.srcTown >= 0 ? ROAD_TOWN_SEARCH_RADIUS : ROAD_INDUSTRY_SEARCH_RADIUS;
  local radiusB = candidate.dstTown >= 0 ? ROAD_TOWN_SEARCH_RADIUS : ROAD_INDUSTRY_SEARCH_RADIUS;
  local dstWantsProduction = candidate.kind == "pax";

  /* Le filtre est global a toutes nos gares bus. Le repli
   * historique de la planification contournait sinon la protection de la voie `voirie`. */
  local excludeA = null;
  if (stop.vehType == AIRoad.ROADVEHTYPE_BUS) {
    excludeA = OpexRoadOurBusTiles();
    if (("existingStops" in candidate) && candidate.existingStops != null) {
      foreach (existingTile in candidate.existingStops) excludeA.append(existingTile);
    }
  } else if ("existingStops" in candidate) {
    excludeA = candidate.existingStops;
  }
  local huntA = OpexRoadSites(candidate.src, candidate.srcTown, candidate.cargo, stop.vehType,
                              coverage, true, radiusA, candidate.dst, true, excludeA);
  local sitesA = huntA.sites;
  if (sitesA.len() == 0) return { plan = null, reason = "SITEA", site = huntA };
  local huntB = OpexRoadSites(candidate.dst, candidate.dstTown, candidate.cargo, stop.vehType,
                              coverage, dstWantsProduction, radiusB, candidate.src, true,
                              excludeA);
  local sitesB = huntB.sites;
  if (sitesB.len() == 0) return { plan = null, reason = "SITEB", site = huntB };

  local trials = 0;
  local nEmpty = 0;
  local nLong = 0;
  local nHit = 0;
  local nUnb = 0;
  local noDepot = 0;

  // Passe 1 : L direct rapide (0 = horizontal, 1 = vertical)
  foreach (siteA in sitesA) {
    foreach (siteB in sitesB) {
      if (stop.vehType == AIRoad.ROADVEHTYPE_BUS &&
          AIMap.DistanceManhattan(siteA.tile, siteB.tile) < ROAD_BUS_STOP_MIN_DISTANCE) continue;
      for (local shape = 0; shape < 2; shape++) {
        if (trials >= ROAD_MAX_TRACE_TRIALS) break;
        trials++;
        local trace = OpexRoadTrace(siteA.front, siteB.front, shape == 0);
        if (trace.len() == 0) { nEmpty++; continue; }
        if (trace.len() > ROAD_MAX_TRACE_TILES) { nLong++; continue; }
        if (OpexRoadTraceHitsStop(trace, siteA.tile) || OpexRoadTraceHitsStop(trace, siteB.tile)) {
          nHit++;
          continue;
        }
        if (!OpexRoadTraceBuildable(trace)) { nUnb++; continue; }
        local depot = OpexRoadFindDepot(trace, siteA, siteB);
        if (depot == null) { noDepot++; continue; }
        return { plan = { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
                          stationType = stop.stationType, vehType = stop.vehType,
                          routeDistance = trace.len(), shape = shape, trials = trials },
                 reason = "OK" };
      }
    }
  }

  // Passe 2 : Déviations en escalier (Z et contournements) si tous les L directs échouent
  foreach (siteA in sitesA) {
    foreach (siteB in sitesB) {
      if (stop.vehType == AIRoad.ROADVEHTYPE_BUS &&
          AIMap.DistanceManhattan(siteA.tile, siteB.tile) < ROAD_BUS_STOP_MIN_DISTANCE) continue;
      for (local shape = 2; shape < 6; shape++) {
        if (trials >= ROAD_MAX_TRACE_TRIALS * 3) break;
        trials++;
        local trace = OpexRoadTraceMulti(siteA.front, siteB.front, shape);
        if (trace.len() == 0) { nEmpty++; continue; }
        if (trace.len() > ROAD_MAX_TRACE_TILES) { nLong++; continue; }
        if (OpexRoadTraceHitsStop(trace, siteA.tile) || OpexRoadTraceHitsStop(trace, siteB.tile)) {
          nHit++;
          continue;
        }
        if (!OpexRoadTraceBuildable(trace)) { nUnb++; continue; }
        local depot = OpexRoadFindDepot(trace, siteA, siteB);
        if (depot == null) { noDepot++; continue; }
        return { plan = { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
                          stationType = stop.stationType, vehType = stop.vehType,
                          routeDistance = trace.len(), shape = shape, trials = trials },
                 reason = "OK" };
      }
    }
  }

  return { plan = null, reason = noDepot > 0 ? "DEPOTX" : "TRACEX",
           trace = { trials = trials, nEmpty = nEmpty, nLong = nLong, nHit = nHit,
                     nUnb = nUnb, nNoDepot = noDepot } };
}

/* La liste added ne contient que les aretes dont la connexion n'existait pas avant notre appel.
 * Le rollback ne supprime donc jamais une route de ville preexistante. */
function OpexRoadRollback(stopA, stopB, depot, vehicles, added)
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
  if (depot != null && AIRoad.IsRoadDepotTile(depot)) AIRoad.RemoveRoadDepot(depot);
  if (stopB != null && AIRoad.IsRoadStationTile(stopB)) AIRoad.RemoveRoadStation(stopB);
  if (stopA != null && AIRoad.IsRoadStationTile(stopA)) AIRoad.RemoveRoadStation(stopA);
  if (added != null) {
    for (local i = added.len() - 1; i >= 0; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
  }
  if (AIR0310_SITE_VALIDITY_CACHE) OpexAir0310InvalidateSiteValidity();
}

/* Un arret de plus, meme facade, tuile cardinale voisine, joint au StationID deja pose.
 * STATION_JOIN_ADJACENT est le piege AAAHogEx (deux gares voisines -> gare neuve) : on passe
 * l'identifiant du primaire et on verifie GetStationID apres pose. Une extra qui n'a pas joint
 * est retiree sur place, la ligne ne meurt pas. */
function OpexRoadTryJoinStop(stop, stationId, vehType, noTile, added)
{
  local tx = AIMap.GetTileX(stop.tile);
  local ty = AIMap.GetTileY(stop.tile);
  local fx = AIMap.GetTileX(stop.front);
  local fy = AIMap.GetTileY(stop.front);
  local dx = fx - tx;
  local dy = fy - ty;
  local perps = [[-dy, dx], [dy, -dx]];
  foreach (p in perps) {
    local x2 = tx + p[0];
    local y2 = ty + p[1];
    local fx2 = fx + p[0];
    local fy2 = fy + p[1];
    if (!OpexRoadInMap(x2, y2) || !OpexRoadInMap(fx2, fy2)) continue;
    local tile = AIMap.GetTileIndex(x2, y2);
    local front = AIMap.GetTileIndex(fx2, fy2);
    if (tile in noTile) continue;
    if (front == stop.tile) continue;
    if (!OpexRoadIsFlat(tile) || !AITile.IsBuildable(tile)) continue;
    if (!OpexRoadIsFlat(front)) continue;
    if (!AIRoad.IsRoadTile(front) && !AITile.IsBuildable(front)) continue;
    local ok = false;
    {
      local test = AITestMode();
      ok = (AIRoad.AreRoadTilesConnected(stop.front, front) || AIRoad.BuildRoad(stop.front, front)) &&
           (AIRoad.AreRoadTilesConnected(front, tile) || AIRoad.BuildRoad(front, tile)) &&
           AIRoad.BuildRoadStation(tile, front, vehType, stationId);
    }
    if (!ok) continue;
    /* Cette tentative peut poser deux aretes avant d'echouer a poser/join l'arret. Ne pas
     * reporter ces aretes sur le candidat perpendiculaire suivant ni les laisser au caller si
     * aucun arret n'est finalement retourne. */
    local addedStart = added.len();
    if (!AIRoad.AreRoadTilesConnected(stop.front, front)) {
      local builtFront = AIRoad.BuildRoad(stop.front, front);
      if (AIRoad.AreRoadTilesConnected(stop.front, front) && builtFront) {
        added.append({ from = stop.front, to = front });
      }
    }
    if (!AIRoad.AreRoadTilesConnected(stop.front, front)) {
      for (local i = added.len() - 1; i >= addedStart; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
      added.resize(addedStart);
      continue;
    }
    if (!AIRoad.AreRoadTilesConnected(front, tile)) {
      local builtStub = AIRoad.BuildRoad(front, tile);
      if (AIRoad.AreRoadTilesConnected(front, tile) && builtStub) {
        added.append({ from = front, to = tile });
      }
    }
    if (!AIRoad.AreRoadTilesConnected(front, tile)) {
      for (local i = added.len() - 1; i >= addedStart; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
      added.resize(addedStart);
      continue;
    }
    if (!AIRoad.BuildRoadStation(tile, front, vehType, stationId)) {
      for (local i = added.len() - 1; i >= addedStart; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
      added.resize(addedStart);
      continue;
    }
    if (!AIRoad.IsRoadStationTile(tile) ||
        AIStation.GetStationID(tile) != stationId ||
        AIRoad.GetRoadStationFrontTile(tile) != front ||
        !AIRoad.AreRoadTilesConnected(tile, front)) {
      if (AIRoad.IsRoadStationTile(tile)) AIRoad.RemoveRoadStation(tile);
      for (local i = added.len() - 1; i >= addedStart; i--) AIRoad.RemoveRoad(added[i].from, added[i].to);
      added.resize(addedStart);
      continue;
    }
    return { tile = tile, front = front };
  }
  return null;
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

/* P0 B0, SHADOW only. Counts commands/road edges missing on the PRE-BUILD
 * map. BT_ROAD is a tariff proxy, not the exact execution charge (terrain,
 * clearing and multi-bit tiles may vary). Never set capitalIsActual or alter
 * economics/financing from this descriptive quote. */
function OpexRoadQuotePlanComponents(catalog, plan, candidate)
{
  local missingEdges = 0;
  foreach (edge in plan.trace) {
    if (!AIRoad.AreRoadTilesConnected(edge.from, edge.to)) missingEdges++;
  }
  local driveThrough = ("driveThrough" in plan) && plan.driveThrough;
  local stopStubs = 0;
  if (!driveThrough) {
    if (!AIRoad.AreRoadTilesConnected(plan.stopA.front, plan.stopA.tile)) stopStubs++;
    if (!AIRoad.AreRoadTilesConnected(plan.stopB.front, plan.stopB.tile)) stopStubs++;
  }
  local depotStub = AIRoad.AreRoadTilesConnected(plan.depot.front, plan.depot.tile) ? 0 : 1;
  local stopTariff = AICargo.HasCargoClass(candidate.cargo, AICargo.CC_PASSENGERS)
      ? catalog.costRoadBusStop : catalog.costRoadTruckStop;
  local traceQuote = missingEdges * catalog.costRoadPerTile;
  local stopsQuote = 2 * stopTariff + stopStubs * catalog.costRoadPerTile;
  local depotQuote = catalog.costRoadDepot + depotStub * catalog.costRoadPerTile;
  local vehicleQuote = candidate.trains * candidate.engine.price;
  return {
    missingEdges = missingEdges, stopStubs = stopStubs,
    depotStub = depotStub, driveThrough = driveThrough,
    traceQuote = traceQuote, stopsQuote = stopsQuote,
    depotQuote = depotQuote, vehicleQuote = vehicleQuote,
    quote = traceQuote + stopsQuote + depotQuote + vehicleQuote
  };
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
                   capacity = 0, opcodes = 0, nStopsA = 1, nStopsB = 1, actualCost = 0,
                   plannedCapital = (("capital" in candidate) ? candidate.capital : 0) };
  /* road_cost_probe : symetrique de air_cost_probe (builder_air.nut) et du devis rail P1.1.
   * Aucun AITestMode n'est appele depuis cette fonction (verifie : OpexRoadBuildTrace et le reste
   * du corps n'exécutent que de vraies commandes) -- pas de bouclier imbrique necessaire. */
  local costs = AIAccounting();
  local p0TraceSpend = 0;
  local p0StopsSpend = 0;
  local p0DepotSpend = 0;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  local balanceBefore = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local cargo = candidate.cargo;
  local added = [];
  local stopA = null;
  local stopB = null;
  local depot = null;
  local built = [];

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

  budget.begin();
  if (AIR0310_SITE_VALIDITY_CACHE) OpexAir0310InvalidateSiteValidity();
  if (!OpexRoadBuildTrace(plan.trace, added)) {
    result.error = AIError.GetLastError();
    result.opcodes = budget.end("build_roads");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(null, null, null, built, added); result.reason = "ROAD"; return result;
  }
  result.opcodes = budget.end("build_roads");
  if (ROAD_QUOTE_COMPONENTS_SHADOW_P0) p0TraceSpend = costs.GetCosts();

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
    OpexRoadRollback(null, null, null, built, added); result.reason = "ASTOP"; return result;
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
    OpexRoadRollback(stopA, null, null, built, added);
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
  if (ROAD_QUOTE_COMPONENTS_SHADOW_P0) p0StopsSpend = costs.GetCosts();

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
  if (ROAD_QUOTE_COMPONENTS_SHADOW_P0) p0DepotSpend = costs.GetCosts();
  if (depot == null) {
    result.error = AIError.GetLastError(); OpexRoadRollback(stopA, stopB, null, built, added);
    result.actualCost = costs.GetCosts();
    result.reason = "DEPOT"; return result;
  }

  budget.begin();
  local capacity = OpexRoadRefitCapacity(depot, candidate.engine, cargo);
  if (capacity <= 0) {
    result.opcodes += budget.end("build_road_vehicles");
    OpexRoadRollback(stopA, stopB, depot, built, added);
    result.actualCost = costs.GetCosts();
    result.reason = "REFIT"; return result;
  }
  local first = AIVehicle.BuildVehicleWithRefit(depot, candidate.engine.id, cargo);
  if (!AIVehicle.IsValidVehicle(first)) {
    result.error = AIError.GetLastError(); result.opcodes += budget.end("build_road_vehicles");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, depot, built, added); result.reason = "VEH"; return result;
  }
  built.append(first);
  if (AIVehicle.GetCapacity(first, cargo) <= 0 ||
      !AIRoad.RoadVehHasPowerOnRoad(AIVehicle.GetRoadType(first), catalog.roadType)) {
    result.opcodes += budget.end("build_road_vehicles");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, depot, built, added); result.reason = "POWER"; return result;
  }

  /* Ordres. La regle du fret vient directement de l'effondrement rail du 2026-08-28 : une ligne de
   * fret est a SENS UNIQUE, donc un OF_FULL_LOAD_ANY au puits fait attendre pour toujours un
   * chargement de retour qui n'existe pas. La source, elle, garde le plein chargement : le cargo y
   * s'accumule de toute facon, et un camion qui part avec une unite paie son trajet pour rien.
   * qui attend d'etre plein detruit precisement ce que la ligne a de bon. */
  local nonstopFlag = C53_ORDER_NONSTOP ? AIOrder.OF_NON_STOP_INTERMEDIATE : 0;
  local sourceFlags = (candidate.kind == "freight" ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE) | nonstopFlag;
  local orderA = AIOrder.AppendOrder(first, stopA, sourceFlags);
  local errorA = orderA ? 0 : AIError.GetLastError();
  /* C53 : C53_ORDER_NOLOAD interdit tout rechargement parasite au terminus de dechargement. */
  local isFreight = candidate.kind == "freight";
  local destFlags = isFreight
      ? (C53_ORDER_NOLOAD ? (AIOrder.OF_UNLOAD | AIOrder.OF_NO_LOAD) : AIOrder.OF_NONE)
      : AIOrder.OF_NONE;
  destFlags = destFlags | nonstopFlag;
  local orderB = AIOrder.AppendOrder(first, stopB, destFlags);
  local errorB = orderB ? 0 : AIError.GetLastError();
  if (!orderA || !orderB || AIOrder.GetOrderCount(first) != 2) {
    result.error = !orderA ? errorA : errorB; result.opcodes += budget.end("build_road_vehicles");
    result.actualCost = costs.GetCosts();
    OpexRoadRollback(stopA, stopB, depot, built, added); result.reason = "ORDERS"; return result;
  }

  /* Les vehicules suivants sont CLONES du premier avec partage d'ordres : le clone reprend le
   * refit, et le partage evite de reposer deux ordres par vehicule (docs/mecanique_jeu.md S9,
   * AIOrder.ShareOrders). Un clone qui echoue n'est pas fatal -- la ligne roule avec ce qu'elle a,
   * ce qui vaut mieux qu'un rollback complet pour un vehicule d'appoint.
   * ⚠️ Le plafond vient du jeu, pas de nous : un arret n'accueille que DEUX vehicules a la fois,
   * au-dela ils font la queue sur la route et se bloquent (docs/mecanique_jeu.md S11). C'est
   * MAX_ROAD_VEHICLES dans economy.nut qui borne candidate.trains. */
  local want = candidate.trains;
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
  for (local i = 1; i < want; i++) {
    /* `clone` est un MOT RESERVE de Squirrel (l'operateur de copie) : le nommer ainsi fait echouer
     * la compilation du fichier entier, et l'echec est presque muet -- une seule ligne dans la
     * sortie OpenTTD, aucun panneau, une compagnie qui existe sans rien construire. */
    if (i >= candidate.trains) {
      local price = AIEngine.GetPrice(candidate.engine.id);
      if (price <= 0) break;
      if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) - OpexCashReserve() < price) break;
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
    OpexRoadRollback(stopA, stopB, depot, built, added);
    result.reason = "START";
    return result;
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
  result.cost = balanceBefore - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  result.actualCost = costs.GetCosts();
  if (ROAD_QUOTE_COMPONENTS_SHADOW_P0) {
    result.phaseCosts <- {
      trace = p0TraceSpend,
      stops = p0StopsSpend - p0TraceSpend,
      depot = p0DepotSpend - p0StopsSpend,
      vehicles = result.actualCost - p0DepotSpend
    };
  }
  return result;
}

/* Reconstitue la flotte d'une ligne routiere dont les vehicules ont disparu (age, destruction
 * a un passage a niveau, renouvellement qui n'a pas suivi). L'infrastructure est deja payee :
 * on ne replanifie rien. Si un vehicule reste, on le clone (ordres partages). S'il n'en reste
 * aucun, on reconstitue moteur + ordres comme a la construction. N'ajoute jamais au-dela du
 * plafond de quais de la ligne (2 x min(nStopsA, nStopsB), sinon MAX_ROAD_VEHICLES).
 * Rend { added, after, reason }. */
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
  local affordable = (money - OpexCashReserve()) / unitPrice;
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
    local nonstopFlag = C53_ORDER_NONSTOP ? AIOrder.OF_NON_STOP_INTERMEDIATE : 0;
    local isFreight = (("kind" in line) && line.kind == "freight");
    local sourceFlags = (isFreight ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE) | nonstopFlag;
    local destFlags = isFreight
        ? (C53_ORDER_NOLOAD ? (AIOrder.OF_UNLOAD | AIOrder.OF_NO_LOAD) : AIOrder.OF_NONE)
        : AIOrder.OF_NONE;
    destFlags = destFlags | nonstopFlag;
    if (!AIOrder.AppendOrder(first, line.stationA, sourceFlags) ||
        !AIOrder.AppendOrder(first, line.stationB, destFlags) ||
        AIOrder.GetOrderCount(first) != 2) {
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
