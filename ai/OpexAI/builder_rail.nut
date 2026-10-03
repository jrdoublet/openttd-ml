/* Etage 3 : construire une ligne rail, sous budget d'opcodes explicite.
 *
 * Reprend les correctifs durement gagnes de ai/TrainLineAI (chacun a coute une session) :
 *  - les plans de quai sont VALIDES avant tout (tuiles constructibles et plates, plus une tuile
 *    de sortie), et le pathfinder choisit lui-meme le couple de plans en cherchant depuis
 *    plusieurs sources vers plusieurs buts. C'est ce qui a supprime le facteur x24 d'une
 *    recherche par combinaison de quais, et c'est aussi ce qui evite qu'un quai avale un virage ;
 *  - la convention [lead, station_exit] des sources/buts : la bibliotheque traite node[0] comme
 *    la vraie case de depart et node[1] comme un predecesseur virtuel, et elle AJOUTE goal[1]
 *    apres avoir atteint goal[0]. Se tromper d'ordre fait chercher depuis le quai lui-meme ;
 *  - le depot : on pose l'aiguillage AVANT le batiment et on verifie AIRail.AreTilesConnected a
 *    chaque etape. Un appel de construction qui renvoie "reussi" ne prouve PAS que le resultat
 *    est fonctionnellement raccorde.
 *
 * Ce qui est NOUVEAU ici, et propre a OpexAI : la recherche a un budget d'iterations calcule, pas
 * une constante. Voir OpexIterationBudget().
 */

/* La longueur n'est PAS une constante : catalog.nut lit `station.station_spread` chaque annee,
 * puis OpexStationPlans appelle le vrai BuildRailStation sous AITestMode avant de proposer un
 * plan. Le jeu, et non une valeur supposee, reste donc l'autorite sur le maximum utilisable. */
const STATION_SEARCH_RADIUS = 30;
const MAX_STATION_PLANS = 12;
/* v1 reste un parallele dedie, pas l'enveloppe spread. Offset 1 est le colle d'origine ;
 * 2-4 sautent la sortie/voie qui occupe le voisin. 4 x 2 x 2 = 16 sondes, rien a cote d'A*.
 * Mesure 2026-08-30 : 658/692 SITE a nClear=0, 100 % du pax. */
const JOIN_PARALLEL_MAX_SIDE = 4;
const PATH_CHUNK = 50;
const PATHFINDER_MAX_COST = 200000;
/* Une tranche = un chunk de la bibliotheque. PATH_CHUNK=50 rend deja la main au moteur ;
 * c'est le rebouclage while dans OpexSearchPath qui confisquait la file (7 mois sans panneau,
 * docs/taches.md S0 undecies ter, 2026-09-03). Un seul chunk par tour, puis l'ordonnanceur
 * reprend les autres taches. */
/* ⚠️ LITTERAL OBLIGATOIRE : `const` n'accepte en Squirrel qu'un scalaire litteral. Ni
 * `= PATH_CHUNK` (reference a une autre constante) ni `= 74 * 365 * 2` (expression) ne
 * compilent -- « scalar expected : integer,float or string », et le fichier entier echoue a
 * la compilation, donc l'IA meurt au demarrage sur TOUS les bras, y compris le defaut.
 * Doit rester egal a PATH_CHUNK ci-dessus. */
const RAIL_SEARCH_SLICE = 50;
/* Borne horaire de SECURITE seulement. deadlineTick = iter/3 + 3000 gelait 7 mois parce que
 * la boucle ne rendait pas la main ; une fois etalee, le temps ECOULE inclut le travail des
 * autres taches, donc cette formule tuerait exactement les recherches qu'A4 doit sauver.
 * 54 020 = 74 ticks/jour * 365 * 2, soit deux ans de jeu, ~8x le plus long gel mesure
 * (litteral pour la meme raison que ci-dessus). Le vrai arret reste
 * spent >= iterationBudget (ABND). */
const RAIL_SEARCH_SAFETY_TICKS = 54020;

/* Pathfinding segmente (docs/taches.md A5), porte tel quel depuis
 * TrainLineAI::_segmentedPath (ai/TrainLineAI-segmented/main.nut:511).
 *
 * POURQUOI MAINTENANT. Sonde 2026-09-03 : 4 tentatives rail sur 10 meurent en ABND
 * (budget epuise sans chemin) -- une a 10 000 (plafond dur A3), trois a 5 000
 * (budget dynamique). Le prototype gagnait 1,7x a 3x d'iterations, mais 98 % de
 * ce gain venait des cas a 36k-95k, que A3 tronque desormais. L'objectif n'est
 * donc plus d'aller plus vite sur ce qui marche, c'est de trouver un chemin
 * sous 5 000-10 000 iterations la ou l'A* classique echoue.
 *
 * ⚠️ LITTERAUX OBLIGATOIRES : `const` n'accepte qu'un scalaire litteral
 * (tache A4, « scalar expected » tuait l'IA au demarrage sur TOUS les bras). */
const SEGMENTED_SEGMENT_ITERS = 2000;
const SEGMENTED_RECOVERY_ITERS = 10000;
const SEGMENTED_FRONTIER_WIDTH = 3;
const SEGMENTED_MAX_BACKTRACKS = 4;
/* Garde-fou historique du prototype (50 000). Sous A3 le budget vaut 5k-10k,
 * donc timeSafe = min(50 000, iterationBudget) se confond avec le budget. */
const SEGMENTED_TIME_SAFE_ITERS = 50000;
const SEGMENTED_BRIDGE_MIN_LEN = 3;
const SEGMENTED_BRIDGE_MAX_LEN = 20;

/* Plafond absolu, garde-fou reglable depuis main.nut::HARD_ITERATION_CAP. La mesure du 2026-08-29
 * (4 graines x 20 ans) a trouve 36 600 iterations comme maximum d'une reussite ; 40 000 garde 9 %
 * de marge, alors que les ABND a 60 000 absorbaient 56,5 % des opcodes de construction. */

/* Le budget derive du rapport est AMORTI (itérations par ligne REUSSIE) ; une tentative
 * INDIVIDUELLE en demande plus, queue asymetrique. 227 tentatives 15.3 : p95(iter OK) /
 * amort <= 2,7 sur toutes les bandes, donc 4x couvre la queue. Le plancher 2000 absorbe
 * le court une fois les noeuds v2 a 310 (4*310=1240 < 2000). Mesure du 2026-08-28 : sans
 * ce facteur, 60 tentatives sur 5 ans, budgets de 50 a 400, zero ligne. Ne PAS baisser
 * M en meme temps que les noeuds. */
const ATTEMPT_MULTIPLIER = 4;
const ATTEMPT_FLOOR = 2000;

/* LA regle d'arret optimal.
 *
 * Le budget d'opcodes est un debit non reportable : la seule question est de savoir a quel
 * candidat va le prochain tick. On continue donc a chercher cette ligne-ci tant qu'elle bat
 * encore l'alternative -- c'est-a-dire tant que son rapport, recalcule sur les iterations
 * REELLEMENT depensees, reste au-dessus du rapport du meilleur candidat non essaye.
 *
 * Le seuil a une forme fermee. Avec ratio = profit * 1000 / iterations, la ligne cesse de battre
 * l'alternative des que :
 *     profit * 1000 / (depense + reste_minimal) < ratio_alternative
 * d'ou le budget maximal ci-dessous. Aucune constante magique : le seuil est le rapport du
 * candidat suivant. Pour le dernier, l'appelant fournit MIN_RATIO, le plus petit rapport encore
 * acceptable au prochain classement annuel. Le cas <=0 reste seulement un garde-fou defensif.
 */
DYNAMIC_PATHFINDER_CAP <- true;

/* Plafond dur d'iterations A* dynamique :
 * 1. Faible au debut (15k) pour filtrer rapidement les lignes faciles sans bruler de temps.
 * 2. Augmente pendant le precalcul ou quand la tresorerie manque (60k) pour exploiter les opcodes dormants.
 * 3. Augmente avec la maturite du reseau (15k + 7.5k * nLines, jusqu'a 60k) quand les couloirs faciles sont epuises. */
function OpexDynamicHardCap(linesCount, isPreplanOrLowCash)
{
  if (!DYNAMIC_PATHFINDER_CAP) return HARD_ITERATION_CAP;
  if (isPreplanOrLowCash) return HARD_ITERATION_CAP;
  local cap = 5000 + linesCount * 1000;
  if (cap > HARD_ITERATION_CAP) cap = HARD_ITERATION_CAP;
  return cap;
}

function OpexIterationBudget(profitAnnual, alternativeRatio, hardCap = 10000)
{
  /* Le chemin est retourne avec le budget pour l'instrumentation : Z = pas d'alternative,
   * F = plancher de tentative, C = plafond dur, N = forme fermee non bornee. */
  if (alternativeRatio <= 0) return { budget = hardCap, path = "Z" };
  local budget = ATTEMPT_MULTIPLIER * (profitAnnual * 1000) / alternativeRatio;
  if (budget < ATTEMPT_FLOOR) return { budget = ATTEMPT_FLOOR, path = "F" };
  if (budget > hardCap) return { budget = hardCap, path = "C" };
  return { budget = budget, path = "N" };
}

/* Plans de quai autour d'un centre, orientes vers l'autre extremite.
 * Porte de TrainLineAI::_makeStationPlans. */
/* Une gare rail peut etre parfaitement plate, acceptee par BuildRailStation et pourtant ne servir
 * AUCUN cargo : le smoke traction 42 a construit ainsi 5 lignes fret a note -1 permanente. Les
 * trois trains etaient en VS_AT_STATION a l'ordre source, vitesse et chargement nuls, alors que
 * l'industrie produisait encore 135 unites/mois. La commande et la voie etaient donc innocente ;
 * l'empreinte du quai etait hors du bassin de l'industrie.
 *
 * GetCargoProduction/Acceptance est la sonde exacte deja utilisee par builder_road.nut. On la
 * consulte pour chacune des `length` tuiles : une seule partie de gare dans le rayon suffit au
 * moteur. 8 est le seuil documente de l'acceptation complete (en huitiemes), pas un rendement
 * suppose. Ce preflight epargne une voie, un depot et 1 a 8 locomotives a une ligne qui ne pourra
 * jamais charger. */
function OpexRailPlatformCargoValue(anchor, step, length, cargo, coverage, wantProduction)
{
  local best = 0;
  for (local i = 0; i < length; i++) {
    local tile = anchor + step * i;
    local value = wantProduction
        ? AITile.GetCargoProduction(tile, cargo, 1, 1, coverage)
        : AITile.GetCargoAcceptance(tile, cargo, 1, 1, coverage);
    if (value > best) best = value;
  }
  return best;
}

function OpexStationPlans(center, otherCenter, radius, length, maxPlans, cargo, coverage,
                          wantProduction, stats = null)
{
  local plans = [];
  local axes = [
    [AIRail.RAILTRACK_NE_SW, AIMap.GetTileIndex(1, 0)],
    [AIRail.RAILTRACK_NW_SE, AIMap.GetTileIndex(0, 1)],
  ];
  for (local r = 0; r <= radius && plans.len() < maxPlans; r++) {
    for (local dx = -r; dx <= r && plans.len() < maxPlans; dx++) {
      for (local dy = -r; dy <= r && plans.len() < maxPlans; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local base = center + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(base)) continue;
        foreach (axis in axes) {
          for (local sign = -1; sign <= 1; sign += 2) {
            local step = axis[1];
            local anchor = sign > 0 ? base : base - step * (length - 1);
            local stationExit = sign > 0 ? anchor + step * (length - 1) : anchor;
            local lead = sign > 0 ? stationExit + step : stationExit - step;
            local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead) &&
                AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
            for (local i = 0; i < length && usable; i++) {
              local platformTile = anchor + step * i;
              usable = AIMap.IsValidTile(platformTile) && AITile.IsBuildable(platformTile) &&
                  AITile.GetSlope(platformTile) == AITile.SLOPE_FLAT;
            }
            if (usable) {
              if (stats != null) stats.nClear++;
              local cargoValue = OpexRailPlatformCargoValue(anchor, step, length, cargo, coverage,
                                                             wantProduction);
              if (wantProduction ? (cargoValue <= 0) : (cargoValue < 8)) continue;
              if (stats != null) stats.nCargo++;
              /* Le rectangle plat ne prouve pas que la commande respecte le station_spread ou les
               * regles de gare. Ce test est au plus MAX_STATION_PLANS * 2 commandes par tentative
               * (24 avec le plafond deja mesure), tres petit devant les milliers d'iterations A* ;
               * il evite de lancer A* vers un quai que le moteur refuserait apres coup. */
              local stationOk = false;
              {
                local probe = AITestMode();
                stationOk = AIRail.BuildRailStation(anchor, axis[0], 1, length, AIStation.STATION_NEW);
              }
              if (stationOk) {
                if (stats != null) stats.nCmd++;
                plans.push({ anchor = anchor, station_exit = stationExit, lead = lead,
                             direction = axis[0], step = step, length = length, cargoValue = cargoValue });
              }
              if (plans.len() >= maxPlans) break;
            }
          }
          if (plans.len() >= maxPlans) break;
        }
      }
    }
  }
  return plans;
}

/* Un raccordement v1 ne melange jamais deux circulations sur le meme quai : on ajoute un quai
 * parallele, joint au meme StationID mais avec sa propre entree. AIRail.BuildRailStation accepte
 * bien un StationID existant (api/script_rail.hpp), mais ne sait pas "agrandir" abstraitement une
 * gare : ce quai explicite est donc l'unite atomique, et l'absence d'aiguillage protege la voie
 * voisine du bouchon a une voie mesure le 2026-08-28.
 *
 * platform est le plan que nous avions nous-memes pose pour la ligne voisine. On ne cherche pas a
 * inferer une gare generique (aeroport, dock, ou gare humaine) : cette tranche n'est autorisee a
 * toucher que la geometrie dont elle connait l'origine. Les deux choix d'extremite donnent au
 * pathfinder une entree dediee sans avoir a raccorder la voie ancienne.
 *
 * L'offset 1 d'origine laissait les deux cotes bloques par la sortie, un depot ou un quai deja
 * joint. On elargit PERPENDICULAIREMENT seulement, meme orientation, meme longueur : ce n'est
 * pas le scan d'enveloppe de AAAHogEx. stats recoit nClear / nCargo (= nClear, le cargo n'est
 * pas un filtre ici) / nCmd, pour que PS ne reste plus a 0,0,0 sur un echec de quai joint. */
function OpexJoinPlatformPlans(platform, stationId, stats = null)
{
  local length = platform.length;
  local plans = [];
  local sideways = platform.direction == AIRail.RAILTRACK_NE_SW
      ? AIMap.GetTileIndex(0, 1) : AIMap.GetTileIndex(1, 0);
  for (local dist = 1; dist <= JOIN_PARALLEL_MAX_SIDE; dist++) {
    for (local flip = -1; flip <= 1; flip += 2) {
      local anchor = platform.anchor + sideways * (dist * flip);
      for (local farExit = 0; farExit <= 1; farExit++) {
        local stationExit = farExit != 0 ? anchor + platform.step * (length - 1) : anchor;
        local lead = farExit != 0 ? stationExit + platform.step : stationExit - platform.step;
        local usable = AIMap.IsValidTile(lead) && AITile.IsBuildable(lead) &&
            AITile.GetSlope(lead) == AITile.SLOPE_FLAT;
        for (local i = 0; i < length && usable; i++) {
          local tile = anchor + platform.step * i;
          usable = AIMap.IsValidTile(tile) && AITile.IsBuildable(tile) &&
              AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
        }
        if (!usable) continue;
        if (stats != null) {
          stats.nClear++;
          stats.nCargo++;
        }

        /* Le test inclut les regles de jointure et de taille de gare du moteur. Une reussite de
         * BuildRailStation ne suffit toujours pas pour la VOIE : elle sera controlee plus bas par
         * AreTilesConnected apres chaque pose. */
        local joins = false;
        {
          local probe = AITestMode();
          joins = AIRail.BuildRailStation(anchor, platform.direction, 1, length, stationId);
        }
        if (joins) {
          if (stats != null) stats.nCmd++;
          plans.push({ anchor = anchor, station_exit = stationExit, lead = lead,
                       direction = platform.direction, step = platform.step, length = length });
        }
      }
    }
  }
  return plans;
}

/* Un couple de plans a une longueur donnee. Rend nA/nB meme en echec : c'est ce qui permet de
 * distinguer SITEA, SITEB et SITEAB, au lieu du seau unique NOPLAN. Les closures Squirrel de
 * cet environnement ne capturent pas les locaux englobants -- d'ou une fonction libre. */
function OpexRailTryPlatformLength(catalog, candidate, length, statsA, statsB)
{
  local plansA = OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, length,
                                  MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, true,
                                  statsA);
  if (plansA.len() == 0) {
    return { ok = false, nA = 0, nB = -1, plansA = plansA, plansB = [] };
  }
  local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, length,
                                  MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                  candidate.kind == "pax", statsB);
  if (plansB.len() == 0) {
    return { ok = false, nA = plansA.len(), nB = 0, plansA = plansA, plansB = plansB };
  }
  return { ok = true, nA = plansA.len(), nB = plansB.len(), plansA = plansA, plansB = plansB };
}

function OpexRailSiteReason(sawA, sawB)
{
  if (!sawA && !sawB) return "SITEAB";
  if (!sawA) return "SITEA";
  return "SITEB";
}

/* Cherche les deux extremites a la meme longueur, du quai economiquement voulu vers le plancher
 * d'une locomotive et un wagon. Le test de chaque longueur reste celui de OpexStationPlans :
 * plat, constructible, cargo dans le rayon et BuildRailStation en AITest. Une longueur plus
 * courte est donc un vrai plan constructible, pas une approximation geometrique.
 *
 * Le seau NOPLAN est eclate : SITEA / SITEB / SITEAB. La cause mesuree du 50 % restant n'etait
 * pas le site search -- c'etaient des origines fret sans tuile de terre dans le bassin
 * (OpexRailOriginSitable, candidates.nut).
 */
function OpexRailPlatformPlans(catalog, candidate)
{
  local statsA = { nClear = 0, nCargo = 0, nCmd = 0 };
  local statsB = { nClear = 0, nCargo = 0, nCmd = 0 };

  local floor = OpexRailMinimumPlatformLength();
  local wanted = candidate.platformLength;
  if (wanted > catalog.platformLength) wanted = catalog.platformLength;
  local sawA = false;
  local sawB = false;

  /* V88 : si le candidat dispose d'un quai joint a une gare existante (ex. usine pour ligne de biens) */
  if (("joinPlatform" in candidate) && candidate.joinPlatform != null &&
      ("joinStationId" in candidate) && candidate.joinStationId >= 0) {
    local jointPlansA = OpexJoinPlatformPlans(candidate.joinPlatform, candidate.joinStationId, statsA);
    if (jointPlansA.len() > 0) {
      local jointLength = candidate.joinPlatform.length;
      foreach (p in jointPlansA) {
        p.stationId <- candidate.joinStationId;
      }
      local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, jointLength,
                                      MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                      candidate.kind == "pax", statsB);
      if (plansB.len() > 0) {
        return { plansA = jointPlansA, plansB = plansB, length = jointLength,
                 slopeRelaxed = 0, reason = "OK", statsA = statsA, statsB = statsB };
      }
      sawA = true;
    }
  }

  for (local length = wanted; length >= floor; length--) {
    local found = OpexRailTryPlatformLength(catalog, candidate, length, statsA, statsB);
    if (found.nA > 0) sawA = true;
    if (found.nB > 0) sawB = true;
    if (found.ok) {
      return { plansA = found.plansA, plansB = found.plansB, length = length,
               slopeRelaxed = 0, reason = "OK", statsA = statsA, statsB = statsB };
    }
  }
  if (!sawA) {
    local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, floor,
                                    MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                    candidate.kind == "pax", statsB);
    if (plansB.len() > 0) sawB = true;
  }
  return { plansA = null, plansB = null, length = 0, slopeRelaxed = 0,
           reason = OpexRailSiteReason(sawA, sawB), statsA = statsA, statsB = statsB };
}

/* Cree le pathfinder. L'objet doit survivre entre les tours (stocke sur this._railSearch) :
 * FindPath(PATH_CHUNK) reprend exactement ou il s'etait arrete. Ne pas recreer a chaque tranche. */
function OpexCreateRailPathfinder(plansA, plansB, ignoredTiles = null)
{
  local sources = [];
  local goals = [];
  /* Convention [lead, station_exit] aux deux bouts : node[0] est le vrai depart, node[1] le
   * predecesseur virtuel ; a l'arrivee la bibliotheque ajoute goal[1] apres goal[0]. */
  foreach (plan in plansA) sources.push([plan.lead, plan.station_exit]);
  foreach (plan in plansB) goals.push([plan.lead, plan.station_exit]);
  if (sources.len() == 0 || goals.len() == 0) return null;
  local pathfinder;
  if (V90_FAST_PATHFINDER) {
    if (V90_PATHFINDER_CHECK) {
      pathfinder = OpexRailPathfinderCheckerV90();
    } else {
      pathfinder = OpexRailPathFinderV90();
    }
  } else {
    pathfinder = RailPathFinder();
  }
  pathfinder.cost.max_cost = PATHFINDER_MAX_COST;
  pathfinder.InitializePath(sources, goals, ignoredTiles == null ? [] : ignoredTiles);
  return pathfinder;
}

/* Une tranche d'A*. `spent` est le cumul DEJA consomme (denominateur du classement : mesurer,
 * pas estimer, et surtout pas remettre a zero d'une tranche a l'autre). `sliceIters` borne
 * CETTE tranche ; passer iterationBudget reconstitue la boucle bloquante historique.
 * deadlineTick : en mode bloquant, la formule historique (iter/3 + marge) ; en mode
 * reprenable, RAIL_SEARCH_SAFETY_TICKS -- le budget d'iterations est la vraie borne. */
function OpexAdvanceRailPathfinder(pathfinder, spent, iterationBudget, deadlineTick, sliceIters)
{
  local path = false;
  local sliceSpent = 0;
  /* 0 par defaut = aucun bridage : AAAHogEx ne dort PAS entre ses chunks (verifie dans son
   * source, cf. info.nut::pathfinder_sleep_ticks), donc le Sleep(1) inconditionnel qui etait ici
   * etait un handicap que nous seuls payions face a lui. Reglable pour rendre la main plus
   * souvent dans une partie avec des humains. */
  local sleepTicks = AIController.GetSetting("pathfinder_sleep_ticks");
  while (path == false && spent < iterationBudget && sliceSpent < sliceIters
         && AIController.GetTick() < deadlineTick) {
    path = pathfinder.FindPath(PATH_CHUNK);
    spent += PATH_CHUNK;
    sliceSpent += PATH_CHUNK;
    if (sleepTicks > 0) AIController.Sleep(sleepTicks);
  }

  /* Codes courts : un nom de panneau accepte au plus 31 caracteres et echoue SILENCIEUSEMENT
   * au-dela (verifie sur TrainLineAI). ABND = budget d'iterations epuise, c'est-a-dire l'arret
   * optimal qui a joue ; DEAD = fenetre de temps epuisee ; NOPA = file vide, aucun chemin.
   * CONT = tranche epuisee, la recherche n'est pas finie -- ne jamais rapporter ce code au
   * classement, seulement reprendre au tour suivant. */
  local stop = "OK";
  local done = true;
  if (path == false) {
    /* Meme priorite que l'historique : DEAD gagne si les deux bornes sont franchies. */
    if (AIController.GetTick() >= deadlineTick) stop = "DEAD";
    else if (spent >= iterationBudget) stop = "ABND";
    else { stop = "CONT"; done = false; }
  } else if (path == null) {
    stop = "NOPA";
  }
  return { path = path, iterations = spent, stop = stop, done = done };
}

/* Convertit une chaine AyStar en ordre de construction. Copie obligatoire : le segment suivant
 * repart d'un RailPathFinder neuf, et les noeuds du segment precedent meurent avec FindPath. */
function OpexSegmentTiles(node)
{
  local tiles = [];
  while (node != null) {
    tiles.push(node.GetTile());
    node = node.GetParent();
  }
  tiles.reverse();
  local simplified = [];
  foreach (tile in tiles) {
    if (simplified.len() >= 2 && simplified[simplified.len() - 2] == tile) {
      simplified.pop();
    } else if (simplified.len() == 0 || simplified[simplified.len() - 1] != tile) {
      simplified.push(tile);
    }
  }
  return simplified;
}

/* Squirrel 3.0 ne capture pas les locales englobantes. clone() est refuse ; une copie
 * explicite rend les checkpoints de retour arriere independants. */
function OpexCopySegmentTiles(tiles)
{
  local copied = [];
  foreach (tile in tiles) copied.push(tile);
  return copied;
}

/* Une paire de tuiles eloignees peut etre un pont OU l'entree d'un tunnel naturel.
 * GetOtherTunnelEnd au moment de poser a produit TRKFAIL (prototype 4/9 -> 7/9,
 * 2026-09-03). Le kind retenu sous AITestMode doit voyager jusqu'a la construction. */
function OpexCopySegmentStructures(structures)
{
  local copied = [];
  foreach (structure in structures) {
    copied.push({ from = structure.from, to = structure.to, kind = structure.kind,
        length = structure.length });
  }
  return copied;
}

function OpexPlannedStructureKind(structures, fromTile, toTile)
{
  if (structures == null) return null;
  foreach (structure in structures) {
    if (structure.from == fromTile && structure.to == toTile) return structure.kind;
  }
  return null;
}

/* Un nouveau segment a un closed set vide. Sans ce garde, il reentre le prefixe deja
 * planifie et la pose boucle (TRKFAIL). Les deux dernieres cases restent autorisees :
 * elles sont la source directionnelle du segment. */
function OpexCanAppendSegment(prefix, tail)
{
  if (prefix == null) return true;
  local seen = {};
  for (local i = 0; i < prefix.len() - 2; i++) seen[prefix[i]] <- true;
  for (local i = 2; i < tail.len(); i++) {
    if (tail[i] in seen) return false;
  }
  return true;
}

/* Extraire K minima par un petit front d'indices, sans retirer de noeud et sans
 * closure. Trier toute la file etait O(n log n) a chaque coupure et mangeait la
 * fenetre avant le prochain FindPath. */
function OpexFrontierAlternatives(pathfinder, maxAlternatives)
{
  local open = pathfinder._pathfinder._open;
  if (open == null || open.Count() == 0) return [];
  local nodes = [];
  local seen = {};
  local candidates = [0];
  while (candidates.len() > 0 && nodes.len() < maxAlternatives) {
    local bestPosition = 0;
    local bestPriority = open._queue[candidates[0]][1];
    for (local i = 1; i < candidates.len(); i++) {
      local priority = open._queue[candidates[i]][1];
      if (priority < bestPriority) {
        bestPosition = i;
        bestPriority = priority;
      }
    }
    local heapIndex = candidates[bestPosition];
    candidates[bestPosition] = candidates[candidates.len() - 1];
    candidates.pop();
    local left = heapIndex * 2 + 1;
    local right = left + 1;
    if (left < open.Count()) candidates.push(left);
    if (right < open.Count()) candidates.push(right);
    local node = open._queue[heapIndex][0];
    local key = node.GetTile() + ":" + node.GetDirection();
    if (key in seen) continue;
    seen[key] <- true;
    nodes.push(node);
  }
  return nodes;
}

/* Centre des station_exit de plansB : OpexAI a plusieurs buts, pas un centre-ville. */
function OpexDestinationCenter(plansB)
{
  local sumX = 0;
  local sumY = 0;
  local n = 0;
  foreach (plan in plansB) {
    sumX += AIMap.GetTileX(plan.station_exit);
    sumY += AIMap.GetTileY(plan.station_exit);
    n++;
  }
  if (n <= 0) return 0;
  return AIMap.GetTileIndex(sumX / n, sumY / n);
}

/* Ponts 3-20 et tunnels, sous AITestMode, UNIQUEMENT si le rail ne peut pas
 * continuer dans l'axe. Sonder 18 ponts a chaque coupure sans obstacle epuisait
 * la fenetre et mourait sans exception (piege 1 du prototype). */
function OpexLocalStructureChoices(front, previous, destinationCenter, state)
{
  local choices = [];
  local distance = AIMap.DistanceManhattan(front, previous);
  if (distance <= 0) return choices;
  local step = (front - previous) / distance;
  local before = AIMap.DistanceManhattan(front, destinationCenter);
  local next = front + step;
  if (!AIMap.IsValidTile(next)) return choices;

  local canContinue = false;
  {
    local testMode = AITestMode();
    canContinue = AIRail.BuildRail(previous, front, next);
  }
  if (canContinue) return choices;

  for (local length = SEGMENTED_BRIDGE_MIN_LEN; length <= SEGMENTED_BRIDGE_MAX_LEN; length++) {
    local target = front + (length - 1) * step;
    if (!AIMap.IsValidTile(target) || AIMap.DistanceManhattan(target, destinationCenter) >= before) {
      continue;
    }
    local bridges = AIBridgeList_Length(length);
    if (bridges.IsEmpty()) continue;
    bridges.Valuate(AIBridge.GetMaxSpeed);
    bridges.Sort(AIList.SORT_BY_VALUE, false);
    local usable = false;
    {
      local testMode = AITestMode();
      usable = AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), front, target);
    }
    if (usable) {
      choices.push({ to = target, kind = "bridge", length = length });
      state.bridgeTests++;
    }
  }

  local tunnelEnd = AITunnel.GetOtherTunnelEnd(front);
  if (AIMap.IsValidTile(tunnelEnd)) {
    local tunnelDistance = AIMap.DistanceManhattan(front, tunnelEnd);
    if (tunnelDistance >= 2 && tunnelDistance + 1 <= SEGMENTED_BRIDGE_MAX_LEN &&
        (tunnelEnd - front) / tunnelDistance == step &&
        AIMap.DistanceManhattan(tunnelEnd, destinationCenter) < before) {
      local usable = false;
      {
        local testMode = AITestMode();
        usable = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, front);
      }
      if (usable) {
        choices.push({ to = tunnelEnd, kind = "tunnel", length = tunnelDistance + 1 });
        state.tunnelTests++;
      }
    }
  }
  return choices;
}

function OpexSegmentedResult(state, path, stop, done)
{
  local tiles = null;
  local structures = null;
  if (stop == "OK") {
    tiles = state.prefix;
    structures = state.structures;
  }
  return {
    path = path,
    tiles = tiles,
    structures = structures,
    iterations = state.iterations,
    stop = stop,
    done = done,
    segments = state.segments,
    backtracks = state.backtracks,
    localChoices = state.localChoices,
  };
}

function OpexTrySegmentedBacktrack(state)
{
  if (state.alternatives.len() > 0 && state.backtracks < SEGMENTED_MAX_BACKTRACKS) {
    local alternative = state.alternatives.pop();
    state.prefix = OpexCopySegmentTiles(alternative.prefix);
    state.structures = OpexCopySegmentStructures(alternative.structures);
    state.activeSources = alternative.sources;
    state.backtracks++;
    state.nextSegmentLimit = SEGMENTED_RECOVERY_ITERS;
    state.pathfinder = null;
    state.segmentPath = false;
    state.segmentUsed = 0;
    return true;
  }
  return false;
}

/* Cree l'etat d'une recherche segmentee. Table passee en parametre : Squirrel ici
 * ne capture pas les locales englobantes (piege 6). pathfinder reste null jusqu'au
 * premier segment : le closed set ne survit jamais d'un segment a l'autre. */
function OpexCreateSegmentedSearch(plansA, plansB, iterationBudget, ignoredTiles = null)
{
  local sources = [];
  local goals = [];
  foreach (plan in plansA) sources.push([plan.lead, plan.station_exit]);
  foreach (plan in plansB) goals.push([plan.lead, plan.station_exit]);
  if (sources.len() == 0 || goals.len() == 0) return null;

  /* timeSafe = min(50 000, budget). Sous A3 le budget vaut 5k-10k, donc se confond
   * avec iterationBudget ; le plafond historique reste pour un cap plus haut. */
  local timeSafe = SEGMENTED_TIME_SAFE_ITERS;
  if (iterationBudget < timeSafe) timeSafe = iterationBudget;

  return {
    activeSources = sources,
    goals = goals,
    ignoredTiles = ignoredTiles == null ? [] : ignoredTiles,
    destinationCenter = OpexDestinationCenter(plansB),
    prefix = null,
    structures = [],
    alternatives = [],
    nextSegmentLimit = SEGMENTED_SEGMENT_ITERS,
    currentSegmentLimit = SEGMENTED_SEGMENT_ITERS,
    pathfinder = null,
    segmentPath = false,
    segmentUsed = 0,
    iterations = 0,
    iterationBudget = iterationBudget,
    timeSafe = timeSafe,
    segments = 0,
    backtracks = 0,
    localChoices = 0,
    bridgeTests = 0,
    tunnelTests = 0,
  };
}

/* Une tranche de recherche segmentee. `state.iterations` est le denominateur du
 * classement : uniquement les vrais FindPath(1), cumules sur TOUS les segments et
 * TOUS les retours arriere, jamais remis a zero (piege 4).
 *
 * Slice : si FindPath s'arrete parce que sliceIters est epuise ALORS que le
 * segment court encore et que budget/deadline restent, CONT + garder le meme
 * pathfinder, SANS traiter la frontiere. Un segment fini (null ou 2000) est
 * traite comme le prototype, meme en mode reprenable. */
function OpexAdvanceSegmentedSearch(state, sliceIters, deadlineTick)
{
  local sliceSpent = 0;
  local sleepTicks = AIController.GetSetting("pathfinder_sleep_ticks");
  local ignored = state.ignoredTiles;

  while (state.iterations < state.iterationBudget &&
         state.iterations < state.timeSafe &&
         AIController.GetTick() < deadlineTick &&
         sliceSpent < sliceIters) {

    if (state.pathfinder == null) {
      state.segments++;
      state.currentSegmentLimit = state.nextSegmentLimit;
      state.nextSegmentLimit = SEGMENTED_SEGMENT_ITERS;
      local pathfinder;
      if (V90_FAST_PATHFINDER) {
        if (V90_PATHFINDER_CHECK) {
          pathfinder = OpexRailPathfinderCheckerV90();
        } else {
          pathfinder = OpexRailPathFinderV90();
        }
      } else {
        pathfinder = RailPathFinder();
      }
      /* Table de cout inchangee : seulement max_cost, comme l'A* classique. */
      pathfinder.cost.max_cost = PATHFINDER_MAX_COST;
      pathfinder.InitializePath(state.activeSources, state.goals, ignored);
      state.pathfinder = pathfinder;
      state.segmentPath = false;
      state.segmentUsed = 0;
    }

    while (state.segmentPath == false &&
           state.segmentUsed < state.currentSegmentLimit &&
           state.iterations < state.iterationBudget &&
           state.iterations < state.timeSafe &&
           AIController.GetTick() < deadlineTick &&
           sliceSpent < sliceIters) {
      state.segmentPath = state.pathfinder.FindPath(1);
      state.segmentUsed++;
      state.iterations++;
      sliceSpent++;
      /* Sleep seulement si le reglage le demande (defaut 0 : ne pas reintroduire
       * le Sleep(1) qui etait un handicap face a AAAHogEx). Groupe par PATH_CHUNK
       * comme le prototype groupait Sleep(1). */
      if (sleepTicks > 0 && (state.segmentPath != false || state.segmentUsed % PATH_CHUNK == 0)) {
        AIController.Sleep(sleepTicks);
      }
    }

    local path = state.segmentPath;
    if (path != false && path != null) {
      local tail = OpexSegmentTiles(path);
      if (state.prefix == null) state.prefix = tail;
      else for (local i = 2; i < tail.len(); i++) state.prefix.push(tail[i]);
      state.pathfinder = null;
      return OpexSegmentedResult(state, path, "OK", true);
    }

    if (path == null) {
      state.pathfinder = null;
      if (OpexTrySegmentedBacktrack(state)) continue;
      return OpexSegmentedResult(state, null, "NOPA", true);
    }

    /* path == false : le segment n'a pas abouti. */
    if (state.segmentUsed < state.currentSegmentLimit) {
      /* Segment encore en cours : slice, budget ou deadline. */
      if (state.iterations < state.iterationBudget &&
          state.iterations < state.timeSafe &&
          AIController.GetTick() < deadlineTick) {
        return OpexSegmentedResult(state, false, "CONT", false);
      }
      if (AIController.GetTick() >= deadlineTick) {
        return OpexSegmentedResult(state, false, "DEAD", true);
      }
      return OpexSegmentedResult(state, false, "ABND", true);
    }

    /* Coupure a 2000 (ou 10000 en reprise). Empiler 3 alternatives a CHAQUE
     * coupure, pas seulement aux obstacles : sinon la pile reste vide et
     * backtracks=0 / local_choices=0 (piege 3, echec initial du prototype). */
    local frontier = OpexFrontierAlternatives(state.pathfinder, SEGMENTED_FRONTIER_WIDTH * 4);
    state.pathfinder = null;
    local usable = [];
    foreach (node in frontier) {
      local candidateTail = OpexSegmentTiles(node);
      if (candidateTail.len() < 3 || !OpexCanAppendSegment(state.prefix, candidateTail)) continue;
      usable.push({ tail = candidateTail });
      if (usable.len() >= SEGMENTED_FRONTIER_WIDTH) break;
    }
    if (usable.len() == 0) {
      if (OpexTrySegmentedBacktrack(state)) continue;
      return OpexSegmentedResult(state, null, "NOPA", true);
    }

    local tail = usable[0].tail;
    /* Moins bon -> meilleur : Pop() essaie le deuxieme noeud tout de suite. */
    for (local i = usable.len() - 1; i >= 1; i--) {
      local alternativeTail = usable[i].tail;
      local alternativePrefix = state.prefix == null ? OpexCopySegmentTiles(alternativeTail) :
          OpexCopySegmentTiles(state.prefix);
      if (state.prefix != null) {
        for (local j = 2; j < alternativeTail.len(); j++) alternativePrefix.push(alternativeTail[j]);
      }
      if (alternativePrefix.len() < 2) continue;
      local alternativeFront = alternativePrefix[alternativePrefix.len() - 1];
      local alternativePrevious = alternativePrefix[alternativePrefix.len() - 2];
      state.alternatives.push({ prefix = alternativePrefix,
          structures = OpexCopySegmentStructures(state.structures),
          sources = [[alternativeFront, alternativePrevious]] });
    }

    if (state.prefix == null) state.prefix = tail;
    else for (local i = 2; i < tail.len(); i++) state.prefix.push(tail[i]);

    local front = state.prefix[state.prefix.len() - 1];
    local previous = state.prefix[state.prefix.len() - 2];
    local choices = OpexLocalStructureChoices(front, previous, state.destinationCenter, state);
    if (choices.len() > 0) {
      for (local i = choices.len() - 1; i >= 1; i--) {
        local alternativePrefix = OpexCopySegmentTiles(state.prefix);
        alternativePrefix.push(choices[i].to);
        local alternativeStructures = OpexCopySegmentStructures(state.structures);
        alternativeStructures.push({ from = front, to = choices[i].to, kind = choices[i].kind,
            length = choices[i].length });
        state.alternatives.push({ prefix = alternativePrefix, structures = alternativeStructures,
            sources = [[choices[i].to, front]] });
      }
      state.prefix.push(choices[0].to);
      state.structures.push({ from = front, to = choices[0].to, kind = choices[0].kind,
          length = choices[0].length });
      state.activeSources = [[choices[0].to, front]];
      state.localChoices++;
    } else {
      state.activeSources = [[front, previous]];
    }
  }

  if (AIController.GetTick() >= deadlineTick) {
    return OpexSegmentedResult(state, false, "DEAD", true);
  }
  if (state.iterations >= state.timeSafe || state.iterations >= state.iterationBudget) {
    return OpexSegmentedResult(state, false, "ABND", true);
  }
  return OpexSegmentedResult(state, false, "CONT", false);
}

/* Recherche de chemin sous budget d'iterations. Rend une table avec le chemin brut et le compte
 * d'iterations reellement consommees -- ce compte est le DENOMINATEUR du classement, il doit etre
 * mesure, pas estime.
 *
 * Mode BLOQUANT (rail_search_resumable=0, defaut) : reconstitue la boucle historique. C'est
 * cette boucle qui gelait l'IA des mois entiers (7 mois, graine 100, juin-dec 1971) : la
 * bibliotheque rendait la main toutes les 50 iterations et on la reprenait aussitot, donc
 * _runNextTask ne tournait plus. Le mode reprenable vit dans OpexAI::_continueRailSearch.
 *
 * rail_segmented_search=1 : meme enveloppe, mais chaque A* vise les quais finals et s'arrete
 * a 2000 iterations. Defaut 0 = A* classique inchange (table de cout, plafond A3). */
function OpexSearchPath(plansA, plansB, iterationBudget, deadlineTick, ignoredTiles = null)
{
  local res;
  if (RAIL_SEGMENTED_SEARCH) {
    local state = OpexCreateSegmentedSearch(plansA, plansB, iterationBudget, ignoredTiles);
    if (state == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=blocking outcome=NOPA iters=0 budget=" + iterationBudget);
      return { path = null, iterations = 0, stop = "NOPA" };
    }
    /* sliceIters = iterationBudget : une seule avancee jusqu'au chemin / ABND / DEAD / NOPA. */
    res = OpexAdvanceSegmentedSearch(state, iterationBudget, deadlineTick);
  } else {
    local pathfinder = OpexCreateRailPathfinder(plansA, plansB, ignoredTiles);
    if (pathfinder == null) {
      if (DECISION_LOG) OpexDecide("RAIL_SEARCH", "type=blocking outcome=NOPA iters=0 budget=" + iterationBudget);
      return { path = null, iterations = 0, stop = "NOPA" };
    }
    /* sliceIters = iterationBudget : une seule "tranche" aussi longue que le budget, donc le
     * while interne ne s'arrete plus que sur chemin / ABND / DEAD, comme avant A4. */
    local result = OpexAdvanceRailPathfinder(pathfinder, 0, iterationBudget, deadlineTick,
                                             iterationBudget);
    res = { path = result.path, iterations = result.iterations, stop = result.stop };
  }
  if (DECISION_LOG) {
    OpexDecide("RAIL_SEARCH", "type=blocking outcome=" + res.stop + " iters=" + res.iterations + " budget=" + iterationBudget);
  }
  return res;
}

/* Deplie le chemin en liste de tuiles, en supprimant les allers-retours d'une tuile que le
 * pathfinder produit quand plusieurs directions d'entree sont proposees. */
function OpexPathTiles(path)
{
  local tiles = [];
  local node = path;
  while (node != null) {
    tiles.push(node.GetTile());
    node = node.GetParent();
  }
  tiles.reverse();
  local simplified = [];
  foreach (tile in tiles) {
    if (simplified.len() >= 2 && simplified[simplified.len() - 2] == tile) {
      simplified.pop();
      continue;
    }
    if (simplified.len() == 0 || simplified[simplified.len() - 1] != tile) simplified.push(tile);
  }
  return simplified;
}

/* Un succes segmente porte `tiles` (prefixe complet, y compris ponts/tunnels locaux)
 * et pas seulement le dernier noeud AyStar. L'A* classique n'a pas ce champ. */
function OpexResolveSearchTiles(search)
{
  if (("tiles" in search) && search.tiles != null) return search.tiles;
  if (search.path == false || search.path == null) return [];
  return OpexPathTiles(search.path);
}

function OpexResolveSearchStructures(search)
{
  if (("structures" in search) && search.structures != null) return search.structures;
  return [];
}

function OpexMatchPlan(plans, tile)
{
  foreach (plan in plans) {
    if (plan.station_exit == tile) return plan;
  }
  return null;
}

/* Une voie parallele d'upgrade doit rester une branche independante. Le pathfinder peut donner
 * un cout faible a un rail deja pose ; l'accepter fabriquerait un aiguillage implicite que le
 * rollback ne pourrait pas restaurer. Les deux sorties de quai (indices 0 et last) sont exclues. */
function OpexJoinPathIsDedicated(tiles)
{
  for (local i = 1; i < tiles.len() - 1; i++) {
    local tile = tiles[i];
    if (AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) {
      return false;
    }
  }
  return true;
}

function OpexPlanHitsSet(plan, forbidden)
{
  if (plan.lead in forbidden) return true;
  for (local i = 0; i < plan.length; i++) {
    if ((plan.anchor + plan.step * i) in forbidden) return true;
  }
  return false;
}

function OpexSameStationEnd(plan, original)
{
  return (plan.station_exit != plan.anchor) == (original.station_exit != original.anchor);
}

/* Deuxieme voie dediee, un train par voie. Jamais deux convois sur les memes tuiles :
 * le pathfinder ignore la premiere voie, le depot 2 n'y touche pas, et si la pose
 * echoue on garde la ligne a UN train. skip : 2=pas de quai, 3=pas de chemin, 4=voie,
 * 5=gare, 6=depot, 7=cash, 8=chevauchement, 9=court. */
function OpexTryDoubleTrack(catalog, planA, planB, tiles, depot, cashReserve, iterationBudget, deadlineTick, extraForbidden = null)
{
  local acc = { ok = false, skip = 2, tiles = null, planA = null, planB = null, depot = null,
                iterations = 0, actualCost = 0, structures = null };
  local stationIdA = AIStation.GetStationID(planA.anchor);
  local stationIdB = AIStation.GetStationID(planB.anchor);
  if (!AIStation.IsValidStation(stationIdA) || !AIStation.IsValidStation(stationIdB)) return acc;

  local forbidden = {};
  foreach (tile in tiles) forbidden[tile] <- true;
  for (local i = 0; i < planA.length; i++) forbidden[planA.anchor + planA.step * i] <- true;
  for (local i = 0; i < planB.length; i++) forbidden[planB.anchor + planB.step * i] <- true;
  forbidden[depot] <- true;
  local depotFront = AIRail.GetRailDepotFrontTile(depot);
  if (AIMap.IsValidTile(depotFront)) forbidden[depotFront] <- true;
  if (extraForbidden != null) {
    foreach (tile in extraForbidden) forbidden[tile] <- true;
  }

  local dualA = [];
  foreach (plan in OpexJoinPlatformPlans(planA, stationIdA)) {
    if (OpexSameStationEnd(plan, planA) && !OpexPlanHitsSet(plan, forbidden)) dualA.append(plan);
  }
  local dualB = [];
  foreach (plan in OpexJoinPlatformPlans(planB, stationIdB)) {
    if (OpexSameStationEnd(plan, planB) && !OpexPlanHitsSet(plan, forbidden)) dualB.append(plan);
  }
  if (dualA.len() == 0 || dualB.len() == 0) return acc;

  local ignored = [];
  foreach (tile, ignoredVal in forbidden) ignored.append(tile);
  local search = OpexSearchPath(dualA, dualB, iterationBudget, deadlineTick, ignored);
  acc.iterations = search.iterations;
  if (search.path == false || search.path == null) { acc.skip = 3; return acc; }

  local tiles2 = OpexResolveSearchTiles(search);
  local structures2 = OpexResolveSearchStructures(search);
  if (tiles2.len() < 3) { acc.skip = 9; return acc; }
  local planA2 = OpexMatchPlan(dualA, tiles2[0]);
  local planB2 = OpexMatchPlan(dualB, tiles2[tiles2.len() - 1]);
  if (planA2 == null || planB2 == null) { acc.skip = 9; return acc; }
  if (!OpexJoinPathIsDedicated(tiles2)) { acc.skip = 8; return acc; }
  for (local i = 1; i < tiles2.len() - 1; i++) {
    if (tiles2[i] in forbidden) { acc.skip = 8; return acc; }
  }

  local depotCost = AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_DEPOT);
  local extra = tiles2.len() * catalog.costTrackPerTile
      + (planA2.length + planB2.length) * catalog.costStation + depotCost;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < extra + cashReserve) {
    acc.skip = 7;
    return acc;
  }

  local costs = AIAccounting();
  for (local i = 0; i < planA2.length; i++) AITile.DemolishTile(planA2.anchor + planA2.step * i);
  for (local i = 0; i < planB2.length; i++) AITile.DemolishTile(planB2.anchor + planB2.step * i);
  local okA = AIRail.BuildRailStation(planA2.anchor, planA2.direction, 1, planA2.length, stationIdA);
  local okB = AIRail.BuildRailStation(planB2.anchor, planB2.direction, 1, planB2.length, stationIdB);
  local joinedA = AIStation.GetStationID(planA2.anchor) == stationIdA;
  local joinedB = AIStation.GetStationID(planB2.anchor) == stationIdB;
  if (!okA || !okB || !joinedA || !joinedB) {
    OpexRollback(null, planA2, planB2, null, null);
    acc.skip = 5;
    return acc;
  }

  local trackFailed = OpexBuildTrack(tiles2, structures2);
  local last = tiles2.len() - 1;
  local connected = trackFailed == 0 &&
      AIRail.AreTilesConnected(planA2.station_exit, tiles2[1], tiles2[2]) &&
      AIRail.AreTilesConnected(tiles2[last - 2], tiles2[last - 1], planB2.station_exit);
  if (!connected) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    acc.skip = 4;
    return acc;
  }

  local depot2 = OpexBuildDepot(tiles2, forbidden);
  if (depot2 == null) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    acc.skip = 6;
    return acc;
  }

  acc.ok = true;
  acc.skip = 0;
  acc.tiles = tiles2;
  acc.planA = planA2;
  acc.planB = planB2;
  acc.depot = depot2;
  acc.structures = structures2;
  acc.actualCost = costs.GetCosts();
  return acc;
}

/* Pose la voie sur les cases intermediaires. Les extremites sont les sorties de quai.
 * `structures` propage le kind retenu sous AITestMode : GetOtherTunnelEnd sur une paire
 * eloignee a pris un tunnel naturel a la place d'un pont (TRKFAIL, prototype 4/9 -> 7/9).
 * Tableau vide ou null = deduction classique, A* inchange.
 * `failure` optionnel : null (defaut) n'ecrit rien. Sinon, au premier segment refuse
 * seulement (cles neuves en <-) : index, tile, kind (rail|bridge|tunnel|connect),
 * error, manh_prev, manh_next, puis l'etat de `cur` apres l'echec
 * (is_buildable, is_rail, is_station, is_road, is_water, owner_self, slope,
 * dup_index). Ces lectures restent dans le `if` deja garde : sonde eteinte ou
 * echec deja enregistre, aucun appel. connect = BuildRail vrai mais
 * AreTilesConnected faux. */
function OpexBuildTrack(tiles, structures = null, failure = null)
{
  local failed = 0;
  for (local i = 1; i < tiles.len() - 1; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    local ok = false;
    if (prev == next) {
      ok = true;                                   // aller-retour, rien a poser
    } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
      ok = true;                                   // autre bout d'un franchissement deja pose
    } else if (AIMap.DistanceManhattan(cur, next) > 1) {
      local plannedKind = OpexPlannedStructureKind(structures, cur, next);
      if (plannedKind == "tunnel" ||
          (plannedKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
        ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
      } else {
        local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
        bridges.Valuate(AIBridge.GetMaxSpeed);
        bridges.Sort(AIList.SORT_BY_VALUE, false);
        ok = !bridges.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
      }
    } else {
      ok = AIRail.BuildRail(prev, cur, next);
      /* BuildRail peut repondre vrai sans dessiner la transition attendue. Pour les trois cases
       * adjacentes ou l'API autorise le predicat, la verification est immediate plutot que
       * reportee au seul test des sorties de gare. Ponts et tunnels n'acceptent pas ce predicat
       * (precondition de voisinage) et restent controles par les deux segments voisins. */
      if (ok && AIMap.DistanceManhattan(prev, cur) == 1 &&
          AIMap.DistanceManhattan(cur, next) == 1 &&
          !AIRail.AreTilesConnected(prev, cur, next)) {
        ok = false;
        /* failure null : un test, aucun appel en plus. L'erreur est lue avant Manhattan. */
        if (failure != null && !("index" in failure)) {
          local err = AIError.GetLastError();
          local manhPrev = AIMap.DistanceManhattan(prev, cur);
          local manhNext = AIMap.DistanceManhattan(cur, next);
          failure.index <- i;
          failure.tile <- cur;
          failure.kind <- "connect";
          failure.error <- err;
          failure.manh_prev <- manhPrev;
          failure.manh_next <- manhNext;
          /* Apres GetLastError : les lectures suivantes ne doivent pas ecraser err. */
          failure.is_buildable <- AITile.IsBuildable(cur) ? 1 : 0;
          failure.is_rail <- AIRail.IsRailTile(cur) ? 1 : 0;
          failure.is_station <- AIRail.IsRailStationTile(cur) ? 1 : 0;
          failure.is_road <- AIRoad.IsRoadTile(cur) ? 1 : 0;
          failure.is_water <- AITile.IsWaterTile(cur) ? 1 : 0;
          failure.owner_self <- (AITile.GetOwner(cur) == AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) ? 1 : 0;
          failure.slope <- AITile.GetSlope(cur);
          local dupIndex = -1;
          for (local j = 0; j < i; j++) {
            if (tiles[j] == cur) {
              dupIndex = j;
              break;
            }
          }
          failure.dup_index <- dupIndex;
        }
      }
    }
    if (!ok) {
      failed++;
      if (failure != null && !("index" in failure)) {
        local err = AIError.GetLastError();
        local manhPrev = AIMap.DistanceManhattan(prev, cur);
        local manhNext = AIMap.DistanceManhattan(cur, next);
        /* Meme predicat que la branche de pose, apres la capture de l'erreur. */
        local segmentKind = "rail";
        if (manhNext > 1) {
          local gapKind = OpexPlannedStructureKind(structures, cur, next);
          if (gapKind == "tunnel" ||
              (gapKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
            segmentKind = "tunnel";
          } else {
            segmentKind = "bridge";
          }
        }
        failure.index <- i;
        failure.tile <- cur;
        failure.kind <- segmentKind;
        failure.error <- err;
        failure.manh_prev <- manhPrev;
        failure.manh_next <- manhNext;
        /* Apres GetLastError : les lectures suivantes ne doivent pas ecraser err. */
        failure.is_buildable <- AITile.IsBuildable(cur) ? 1 : 0;
        failure.is_rail <- AIRail.IsRailTile(cur) ? 1 : 0;
        failure.is_station <- AIRail.IsRailStationTile(cur) ? 1 : 0;
        failure.is_road <- AIRoad.IsRoadTile(cur) ? 1 : 0;
        failure.is_water <- AITile.IsWaterTile(cur) ? 1 : 0;
        failure.owner_self <- (AITile.GetOwner(cur) == AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) ? 1 : 0;
        failure.slope <- AITile.GetSlope(cur);
        local dupIndex = -1;
        for (local j = 0; j < i; j++) {
          if (tiles[j] == cur) {
            dupIndex = j;
            break;
          }
        }
        failure.dup_index <- dupIndex;
      }
    }
  }
  return failed;
}

/* C80 : Re-verification d'un trace de voie sous AITestMode pour le stock de traces.
 * Meme parcours que OpexBuildTrack mais SANS le controle AreTilesConnected,
 * car sous mode test les voies ne sont pas reellement posees sur la carte. */
function OpexTestRailTrack(tiles, structures = null)
{
  local testMode = AITestMode();
  local failed = 0;
  local firstSegment = null;
  local firstTile = null;
  for (local i = 1; i < tiles.len() - 1; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    local ok = false;
    if (prev == next) {
      ok = true;                                   // aller-retour, rien a poser
    } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
      ok = true;                                   // autre bout d'un franchissement deja pose
    } else if (AIMap.DistanceManhattan(cur, next) > 1) {
      local plannedKind = OpexPlannedStructureKind(structures, cur, next);
      if (plannedKind == "tunnel" ||
          (plannedKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
        ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
      } else {
        local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
        bridges.Valuate(AIBridge.GetMaxSpeed);
        bridges.Sort(AIList.SORT_BY_VALUE, false);
        ok = !bridges.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
      }
    } else {
      ok = AIRail.BuildRail(prev, cur, next);
    }
    if (!ok) {
      failed++;
      if (firstSegment == null) {
        firstTile = cur;
        firstSegment = prev + "-" + cur + "-" + next;
      }
    }
  }
  return { failed = failed, firstSegment = firstSegment, firstTile = firstTile };
}

/* Depot pres du depart. On pose l'aiguillage AVANT le batiment et on verifie la connectivite a
 * chaque etape : un appel qui renvoie "reussi" ne prouve pas que le resultat est raccorde. */
function OpexBuildDepot(tiles, forbidden = null)
{
  local offsets = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
    AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1),
  ];
  for (local index = 1; index < tiles.len() - 1; index++) {
    local anchor = tiles[index];
    if (AIRail.IsRailStationTile(anchor) || !AIRail.IsRailTile(anchor)) continue;
    local stationSide = tiles[index - 1];
    local lineSide = tiles[index + 1];
    if (AIMap.DistanceManhattan(stationSide, anchor) != 1) continue;
    if (AIMap.DistanceManhattan(lineSide, anchor) != 1) continue;

    AIRail.BuildRail(stationSide, anchor, lineSide);
    if (!AIRail.AreTilesConnected(stationSide, anchor, lineSide)) continue;

    foreach (offset in offsets) {
      local candidate = anchor + offset;
      if (!AIMap.IsValidTile(candidate)) continue;
      if (forbidden != null && (candidate in forbidden)) continue;
      if (AIRail.IsRailStationTile(candidate) || AIRail.IsRailDepotTile(candidate)) continue;
      local onRoute = false;
      foreach (routeTile in tiles) {
        if (routeTile == candidate) { onRoute = true; break; }
      }
      if (onRoute) continue;

      {
        /* Bouclier : AIAccounting compte le cout SIMULE des commandes jouees en AITestMode
         * (script_object.cpp:299-302). Sans lui, le sondage qui REUSSIT ajoutait un prix de
         * depot fantome (~450 £) au `actualCost` de chaque ligne rail. Le destructeur d'un
         * AIAccounting imbrique restaure le total superieur, donc tout ce qui entre ici est jete. */
        local shield = AIAccounting();
        local testMode = AITestMode();
        if (!AIRail.BuildRailDepot(candidate, anchor)) continue;
      }
      AITile.DemolishTile(candidate);
      AIRail.BuildRail(stationSide, anchor, candidate);
      if (!AIRail.AreTilesConnected(stationSide, anchor, candidate) ||
          !AIRail.AreTilesConnected(stationSide, anchor, lineSide)) {
        AIRail.RemoveRail(stationSide, anchor, candidate);
        AIRail.BuildRail(stationSide, anchor, lineSide);
        continue;
      }
      if (!AIRail.BuildRailDepot(candidate, anchor) ||
          AIRail.GetRailDepotFrontTile(candidate) != anchor) {
        AIRail.RemoveRail(stationSide, anchor, candidate);
        AIRail.BuildRail(stationSide, anchor, lineSide);
        continue;
      }
      return candidate;
    }
  }
  return null;
}

/* Une tentative ratee apres la pose ne doit RIEN laisser sur la carte.
 *
 * Sans cela chaque echec abandonne deux gares et toute une voie : mesure du 2026-08-28, 28 gares
 * orphelines pour zero ligne. Le cout n'est pas que financier -- une gare sans transfert depuis
 * 50 jours coute -15 par mois de note d'autorite locale (docs/mecanique_jeu.md §7), donc les
 * ruines degradent activement la capacite a construire dans ces villes. */
function OpexRollback(tiles, planA, planB, depot, vehicles)
{
  /* OpexBuildTrains ne demarre les convois qu'apres que TOUS leurs ordres sont poses. Si un
   * ordre echoue, ils sont donc encore vendables dans le depot et le rollback reste vraiment
   * atomique, y compris pour un nouveau quai joint. */
  if (vehicles != null) {
    foreach (vehicle in vehicles) {
      if (AIVehicle.IsValidVehicle(vehicle) && AIVehicle.IsStoppedInDepot(vehicle)) {
        AIVehicle.SellVehicle(vehicle);
      }
    }
  }
  if (depot != null) AITile.DemolishTile(depot);
  if (planA != null) {
    for (local i = 0; i < planA.length; i++) AITile.DemolishTile(planA.anchor + planA.step * i);
  }
  if (planB != null) {
    for (local i = 0; i < planB.length; i++) AITile.DemolishTile(planB.anchor + planB.step * i);
  }
  if (tiles == null) return;
  for (local i = 1; i < tiles.len() - 1; i++) {
    AITile.DemolishTile(tiles[i]);
  }
}

function OpexBuildTrains(catalog, cargo, kind, depotTile, exitA, exitB, wanted, loco, wagons, platformLength, startVehicles = true)
{
  local wagon = catalog.wagonByCargo[cargo];
  local built = 0;
  local vehicles = [];          // locomotives tete : identite persistante de la ligne
  local rollbackVehicles = [];  // tete ET wagons isoles : cleanup atomique si MoveWagon echoue
  local lastError = 0;
  local diag = null;
  local measuredLength = 0;
  local measuredLocoLength = 0;
  local measuredWagonLength = 0;
  /* OpexRailNominalMaxWagons(p) = 2*p-1 donne, avec les mesures vanilla 8/16 + 8/16,
   * 8 + (2*p-1)*8 = p*16. Le constructeur applique exactement cette limite, puis mesure chaque
   * vehicule reel pour que ni une locomotive ni un wagon NewGRF plus long ne rende le modele plus
   * optimiste que le quai bati. */
  local nominalMaxWagons = OpexRailNominalMaxWagons(platformLength);
  local trainLengthLimit = platformLength * 16;
  if (wagons < 1 || wagons > nominalMaxWagons || trainLengthLimit < 1) {
    return { built = 0, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
             failed = true, failure = "LENGTH", error = 0, diag = diag };
  }
  /* Ordres de chargement : pour le fret (sens unique), seule la source attend le plein chargement.
   * Pour les passagers, PAX_FULL_LOAD=1 force le plein chargement aux deux bouts (patron trAIns).
   * C53 : C53_ORDER_NOLOAD interdit tout rechargement au puits pour les convois de fret (OF_NO_LOAD). */
  local nonstopFlag = C53_ORDER_NONSTOP ? AIOrder.OF_NON_STOP_INTERMEDIATE : 0;
  local flagsA = ((kind == "pax" && !PAX_FULL_LOAD) ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY) | nonstopFlag;
  local destFreightFlags = C53_ORDER_NOLOAD ? (AIOrder.OF_UNLOAD | AIOrder.OF_NO_LOAD) : AIOrder.OF_NONE;
  local flagsB = ((kind == "freight") ? destFreightFlags : ((kind == "pax" && !PAX_FULL_LOAD) ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY)) | nonstopFlag;
  for (local i = 0; i < wanted; i++) {
    local train = AIVehicle.BuildVehicle(depotTile, loco.id);
    if (!AIVehicle.IsValidVehicle(train)) {
      lastError = AIError.GetLastError();
      /* Diagnostic minimal au moment exact de l'echec : c'est moins cher que de deviner. */
      local testOk = 0;
      {
        /* Meme bouclier que dans OpexBuildDepot : ce sondage ne doit rien laisser dans la
         * comptabilite du caller, sans quoi un echec de convoi facturerait une loco fantome. */
        local shield = AIAccounting();
        local probe = AITestMode();
        testOk = AIVehicle.BuildVehicle(depotTile, loco.id) != null ? 1 : 0;
      }
      diag = {
        railtype = AIRail.GetCurrentRailType(),
        isDepot = AIRail.IsRailDepotTile(depotTile) ? 1 : 0,
        buildable = AIEngine.IsBuildable(loco.id) ? 1 : 0,
        canRun = AIEngine.CanRunOnRail(loco.id, AIRail.GetCurrentRailType()) ? 1 : 0,
        price = loco.price,
        cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF),
        engineRail = AIEngine.GetRailType(loco.id),
        depotRail = AIRail.GetRailType(depotTile),
        vehType = AIEngine.GetVehicleType(loco.id),
        testOk = testOk,
      };
      /* Le chemin et les convois deja poses ont une valeur : apres le premier train, garder une
       * frequence moindre est preferable a jeter l'A* et toute la ligne. Seul l'echec du tout
       * premier train laisse la ligne sans service et doit declencher le rollback. */
      if (built == 0) {
        return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                 failed = true, failure = "VEHICLE", error = lastError, diag = diag };
      }
      break;
    }
    /* Conserver le train avant les ordres : un echec d'ordre doit aussi pouvoir le vendre dans le
     * rollback, au lieu de laisser un depot impossible a demolir. */
    vehicles.append(train);
    rollbackVehicles.append(train);
    local trainLength = AIVehicle.GetLength(train);
    measuredLocoLength = trainLength;
    for (local w = 0; w < wagons; w++) {
      local car = AIVehicle.BuildVehicle(depotTile, wagon.id);
      if (AIVehicle.IsValidVehicle(car)) {
        rollbackVehicles.append(car);
        local carLength = AIVehicle.GetLength(car);
        measuredWagonLength = carLength;
        /* Aucune longueur par moteur n'existe dans NoAI 15.3 : cette mesure porte donc sur les
         * vehicules reels, dans l'unite du moteur (1/16 de tuile). Elle verifie la formule qui a
         * donne `wagons` AVANT de lancer le train ; un NewGRF plus long ne peut pas deborder
         * silencieusement du quai. */
        if (trainLength + carLength > trainLengthLimit) {
          return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                   failed = true, failure = "LENGTH", error = 0, diag = diag, trainLength = trainLength,
                   locoLength = measuredLocoLength, wagonLength = measuredWagonLength };
        }
        if (!AIVehicle.MoveWagon(car, 0, train, 0)) {
          return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                   failed = true, failure = "WAGON", error = AIError.GetLastError(), diag = diag,
                   trainLength = trainLength, locoLength = measuredLocoLength,
                   wagonLength = measuredWagonLength };
        }
        trainLength += carLength;
      } else {
        return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                 failed = true, failure = "WAGON", error = AIError.GetLastError(), diag = diag,
                 trainLength = trainLength, locoLength = measuredLocoLength,
                 wagonLength = measuredWagonLength };
      }
    }
    measuredLength = trainLength;
    local okA = AIOrder.AppendOrder(train, exitA, flagsA);
    if (!okA) {
      return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
               failed = true, failure = "ORDER", error = AIError.GetLastError(), diag = diag };
    }
    local okB = AIOrder.AppendOrder(train, exitB, flagsB);
    if (!okB || AIOrder.GetOrderCount(train) != 2) {
      return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
               failed = true, failure = "ORDER", error = !okB ? AIError.GetLastError() : 0, diag = diag };
    }
    built++;
  }
  /* Pas de train lance avant que la transaction entiere soit certaine : voir OpexRollback.
   * La double voie construit un convoi par depot puis les demarre ensemble. */
  if (startVehicles) {
    local started = [];
    local startFailed = false;
    foreach (train in vehicles) {
      if (!AIVehicle.StartStopVehicle(train)) {
        startFailed = true;
        break;
      }
      started.append(train);
    }
    if (startFailed) {
      foreach (train in started) {
        AIVehicle.StartStopVehicle(train);
      }
      return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
               failed = true, failure = "START", error = AIError.GetLastError(), diag = diag,
               trainLength = measuredLength, locoLength = measuredLocoLength,
               wagonLength = measuredWagonLength };
    }
  }
  return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
           failed = false, failure = "", error = lastError, diag = diag, trainLength = measuredLength,
           locoLength = measuredLocoLength, wagonLength = measuredWagonLength };
}

/* Premier signal : PBS bidirectionnel devant le quai, pas un sens unique
 * au milieu (mecanique_jeu §12.2). GetSignalType(tile, front) : front est
 * la case vers laquelle le signal REGARDE. -1 = rien a poser (pas de rail). */
function OpexTryBuildSignal(tile, front)
{
  if (!AIMap.IsValidTile(tile) || !AIMap.IsValidTile(front)) return -1;
  if (AIMap.DistanceManhattan(tile, front) != 1) return -1;
  if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile)) return -1;
  if (!AIRail.IsRailTile(tile)) return -1;
  if (AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) return -1;
  if (AIRail.GetSignalType(tile, front) != AIRail.SIGNALTYPE_NONE) return 1;
  if (AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_PBS)) return 1;
  if (AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_NORMAL_TWOWAY)) return 1;
  return 0;
}

function OpexTileTrackCount(tile)
{
  if (!AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) || AIRail.IsRailDepotTile(tile)) {
    return 0;
  }
  local tracks = AIRail.GetRailTracks(tile);
  if (tracks == AIRail.RAILTRACK_INVALID) return 0;
  local n = 0;
  if ((tracks & AIRail.RAILTRACK_NE_SW) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NW_SE) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NW_NE) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_SW_SE) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NW_SW) != 0) n++;
  if ((tracks & AIRail.RAILTRACK_NE_SE) != 0) n++;
  return n;
}

function OpexAccountSignal(built, acc)
{
  if (built == 1) acc.ok++;
  else if (built == 0) acc.fail++;
}

/* Essaie les deux orientations d'un PBS. -1 = emplacement inutilisable (pont, gare, deja pose),
 * 0 = commande refusee, 1 = pose ou deja present. */
function OpexTryBuildSignalEither(tile, a, b)
{
  local first = OpexTryBuildSignal(tile, a);
  if (first == 1) return 1;
  if (b != null && AIMap.IsValidTile(b) && b != a) {
    local second = OpexTryBuildSignal(tile, b);
    if (second == 1) return 1;
    if (second == 0) return 0;
  }
  return first;
}

/* Cherche un PBS sur une voie simple en s’éloignant d’une gare ou d’un aiguillage.
 * OpenTTD 15.3 refuse structurellement les signaux sur TracksOverlap : le filtre trackCount == 1
 * est donc une precondition moteur, pas une heuristique. */
function OpexPlacePathApproachSignal(tiles, start, step, minDistance, maxDistance, acc, kind, used)
{
  local last = tiles.len() - 1;
  for (local distance = minDistance; distance <= maxDistance; distance++) {
    local i = start + step * distance;
    if (i <= 0 || i >= last) break;
    local tile = tiles[i];
    if (tile in used || OpexTileTrackCount(tile) != 1) continue;
    local built = OpexTryBuildSignalEither(tile, tiles[i - step], tiles[i + step]);
    if (built == -1) continue;
    OpexAccountSignal(built, acc);
    if (built == 1) {
      used[tile] <- true;
    } else {
      acc.failures.append({ kind = kind, slot = i, error = AIError.GetLastError(),
                            tracks = OpexTileTrackCount(tile),
                            x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile) });
    }
    return built;
  }
  acc.skip++;
  return -1;
}

function OpexPlaceJoinSignals(planA, planB, tiles, depot)
{
  local acc = { ok = 0, fail = 0, skip = 0, junc = 0, failures = [] };
  local last = tiles.len() - 1;
  local used = {};

  /* Slot 1 est la gorge de gare et porte souvent deux tracks. Deux tuiles plus loin suffit a
   * degager un train dont la longueur est bornee par le quai. */
  OpexPlacePathApproachSignal(tiles, 0, 1, 2, 8, acc, "A", used);
  OpexPlacePathApproachSignal(tiles, last, -1, 2, 8, acc, "B", used);

  /* Le depot ajoute un vrai aiguillage a la voie. Les PBS vont sur les deux approches simples,
   * jamais sur la tuile junc : CmdBuildSingleSignal refuse tout TracksOverlap. */
  if (depot != null) {
    local junc = AIRail.GetRailDepotFrontTile(depot);
    local juncIndex = -1;
    for (local i = 1; i < last; i++) {
      if (tiles[i] == junc) { juncIndex = i; break; }
    }
    if (juncIndex >= 0 && OpexTileTrackCount(junc) >= 2) {
      acc.junc++;
      OpexPlacePathApproachSignal(tiles, juncIndex, -1, 1, 8, acc, "L", used);
      OpexPlacePathApproachSignal(tiles, juncIndex, 1, 1, 8, acc, "R", used);
    }
  }
  return acc;
}

/* Quais + economie, AVANT l'A*. Separe pour que le mode reprenable puisse poser le pathfinder
 * et rendre la main sans rejouer ce travail a chaque tranche. plansA == null => echec, pas de
 * recherche a lancer. */
function OpexPrepareRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)
{
  /* C67.6 rail : capital du candidat tel que finance avant A* (distance Manhattan). */
  if (DECISION_LOG && !("preCapital" in candidate)
      && !(("capitalIsActual" in candidate) && candidate.capitalIsActual))
    candidate.preCapital <- candidate.capital;
  local plan = { ok = false, reason = "", iterations = 0, opcodes = 0,
                 plansA = null, plansB = null, planA = null, planB = null,
                 length = candidate.platformLength,
                 slopeRelaxed = 0, siteClear = 0, siteCargo = 0, siteCmd = 0,
                 tiles = null, depot = null, tiles2 = null, planA2 = null, planB2 = null, depot2 = null,
                 doubleTrack = 0, doubleTiles = 0, doubleDepot = null, doubleSkip = 0,
                 structures = null, structures2 = null,
                 segmentedSegments = 0, segmentedBacktracks = 0, segmentedLocalChoices = 0,
                 budgetInfo = null, iterationBudget = 0, capital = candidate.capital };

  plan.budgetInfo = OpexIterationBudget(candidate.profitAnnual, alternativeRatio, hardCap);
  plan.iterationBudget = plan.budgetInfo.budget;

  budget.begin();
  local platformPlans = OpexRailPlatformPlans(catalog, candidate);
  plan.opcodes += budget.end("build_plans");
  if (platformPlans.plansA == null || platformPlans.reason != "OK") {
    plan.reason = platformPlans.reason;
    local stats = platformPlans.reason == "SITEB" ? platformPlans.statsB : platformPlans.statsA;
    plan.siteClear = stats.nClear;
    plan.siteCargo = stats.nCargo;
    plan.siteCmd = stats.nCmd;
    return plan;
  }
  plan.plansA = platformPlans.plansA;
  plan.plansB = platformPlans.plansB;
  plan.length = platformPlans.length;
  plan.slopeRelaxed = platformPlans.slopeRelaxed ? 1 : 0;

  local economics = OpexLineEconomics(catalog, candidate.cargo, candidate.distance,
                                      candidate.monthly, candidate.kind, plan.length);
  if (economics == null) { plan.reason = "ECON"; return plan; }
  plan.capital = economics.capital;
  OpexApplyRailEconomics(candidate, economics);
  plan.budgetInfo = OpexIterationBudget(candidate.profitAnnual, alternativeRatio, hardCap);
  plan.iterationBudget = plan.budgetInfo.budget;
  return plan;
}

/* Assemble le plan une fois l'A* termine. `search.iterations` DOIT etre le cumul de toutes
 * les tranches : c'est le denominateur du classement. */
function OpexCompleteRailRouteAfterSearch(catalog, candidate, plan, search)
{
  plan.iterations = search.iterations;
  if (("segments" in search)) {
    plan.segmentedSegments = search.segments;
    plan.segmentedBacktracks = search.backtracks;
    plan.segmentedLocalChoices = search.localChoices;
  }
  if (search.path == false || search.path == null) { plan.reason = search.stop; return plan; }

  local tiles = OpexResolveSearchTiles(search);
  if (tiles.len() < 3) { plan.reason = "SHORT"; return plan; }
  local planA = OpexMatchPlan(plan.plansA, tiles[0]);
  local planB = OpexMatchPlan(plan.plansB, tiles[tiles.len() - 1]);
  if (planA == null || planB == null) { plan.reason = "NOMATCH"; return plan; }

  plan.tiles = tiles;
  plan.structures = OpexResolveSearchStructures(search);
  plan.planA = planA;
  plan.planB = planB;

  /* Recalibrer avec la longueur effectivement trouvee AVANT de decider si une
   * seconde voie est necessaire. Sinon un detour peut faire passer le besoin de
   * une a deux rames apres que la topologie a ete figee : le constructeur ne
   * dispose alors que du premier depot et ne livre qu'une rame. */
  local routeDistance = 0;
  for (local i = 1; i < tiles.len(); i++) {
    routeDistance += AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
  }
  if (routeDistance > 0) {
    local economics = OpexLineEconomics(catalog, candidate.cargo, candidate.distance,
                                        candidate.monthly, candidate.kind, plan.length,
                                        routeDistance);
    if (EQUIPMENT_ROI_PROBE) {
      OpexM3ProbeRailEquipment(catalog, candidate, plan.length, routeDistance, economics);
    }
    if (economics != null) {
      plan.capital = economics.capital;
      OpexApplyRailEconomics(candidate, economics);
    }
  }

  if (candidate.trains > 1) {
    local remain = plan.iterationBudget - plan.iterations;
    if (remain < ATTEMPT_FLOOR) remain = ATTEMPT_FLOOR;
    /* Sous rail_search_resumable, la borne tick historique tuerait cette seconde recherche
     * des qu'elle est entrelacee. OpexTryDoubleTrack sort de toute facon avant l'A* pour une
     * ligne neuve (gares pas encore posees, docs/taches.md S0) : le changement de deadline
     * n'a donc d'effet que si ce chemin redevient vivant. */
    local dualDeadline = (RAIL_SEARCH_RESUMABLE
        ? AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS
        : AIController.GetTick() + remain / 3 + BUILD_TICK_MARGIN);
    local dual = OpexTryDoubleTrack(catalog, planA, planB, tiles, null, 0,
                                    remain, dualDeadline, []);
    /* Cumul : les iterations de la seconde voie s'ajoutent au denominateur, pas le remplacent. */
    plan.iterations += dual.iterations;
    plan.doubleSkip = dual.skip;
    if (dual.ok) {
      plan.doubleTrack = 1;
      plan.doubleTiles = dual.tiles.len();
      plan.doubleDepot = dual.depot;
      plan.tiles2 = dual.tiles;
      plan.planA2 = dual.planA;
      plan.planB2 = dual.planB;
      plan.depot2 = dual.depot;
      plan.structures2 = dual.structures;
    }
  }

  plan.ok = true;
  plan.reason = "OK";
  return plan;
}

/* Precalcule le plan physique complet d'une ligne ferroviaire (quais, economie, trace A*,
 * depot, double voie eventuelle) SANS modifier la carte du jeu ni depenser de tresorerie.
 * Mode bloquant : conserve pour rail_search_resumable=0. Le mode reprenable orchestre
 * Prepare / tranches / Complete depuis OpexAI::_continueRailSearch. */
function OpexPlanRailRoute(catalog, budget, candidate, alternativeRatio, hardCap = 10000)
{
  local plan = OpexPrepareRailRoute(catalog, budget, candidate, alternativeRatio, hardCap);
  if (plan.plansA == null) return plan;

  budget.begin();
  local deadlineTick = AIController.GetTick() + plan.iterationBudget / 3 + BUILD_TICK_MARGIN;
  local search = OpexSearchPath(plan.plansA, plan.plansB, plan.iterationBudget, deadlineTick);
  plan.opcodes += budget.end("build_search");
  return OpexCompleteRailRouteAfterSearch(catalog, candidate, plan, search);
}

/* Devis réel par AITestMode + AIAccounting avant engagement (docs/taches.md §0 tervicies point 8 & C7).
 * Simule la construction des gares et de la voie sans modifier la carte pour mesurer le coût exact. */
/* R23 : null signifie devis invalide, jamais un cout partiel utilisable.
 * Capturer le premier motif avant toute autre commande. L'argument diagnostic
 * est optionnel pour conserver les appelants qui ne demandent que le cout. */
function OpexRailQuoteFailure(failure, reason, tile, error)
{
  if (failure != null) {
    failure.reason <- reason;
    failure.tile <- tile;
    failure.error <- error;
  }
  return null;
}

function OpexSimulateRailInfraCost(plan, failure = null)
{
  local simulatedInfra = 0;
  {
    local testMode = AITestMode();
    local accounting = AIAccounting();

    local planA = plan.planA;
    local planB = plan.planB;
    local tiles = plan.tiles;
    for (local i = 0; i < planA.length; i++) {
      local tile = planA.anchor + planA.step * i;
      if (!AITile.DemolishTile(tile)) return OpexRailQuoteFailure(failure, "STNFAIL", tile, AIError.GetLastError());
    }
    for (local i = 0; i < planB.length; i++) {
      local tile = planB.anchor + planB.step * i;
      if (!AITile.DemolishTile(tile)) return OpexRailQuoteFailure(failure, "STNFAIL", tile, AIError.GetLastError());
    }
    local stIdA = ("stationId" in planA) ? planA.stationId : AIStation.STATION_NEW;
    local stIdB = ("stationId" in planB) ? planB.stationId : AIStation.STATION_NEW;
    if (!AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length, stIdA)) {
      return OpexRailQuoteFailure(failure, "STNFAIL", planA.anchor, AIError.GetLastError());
    }
    if (!AIRail.BuildRailStation(planB.anchor, planB.direction, 1, planB.length, stIdB)) {
      return OpexRailQuoteFailure(failure, "STNFAIL", planB.anchor, AIError.GetLastError());
    }

    for (local i = 1; i < tiles.len() - 1; i++) {
      local prev = tiles[i - 1];
      local cur = tiles[i];
      local next = tiles[i + 1];
      local ok = false;
      if (prev == next) {
        continue;
      } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
        continue;
      } else if (AIMap.DistanceManhattan(cur, next) > 1) {
        local plannedKind = OpexPlannedStructureKind(
            (("structures" in plan) ? plan.structures : null), cur, next);
        if (plannedKind == "tunnel" ||
            (plannedKind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
          ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
        } else {
          local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
          bridges.Valuate(AIBridge.GetMaxSpeed);
          bridges.Sort(AIList.SORT_BY_VALUE, false);
          if (bridges.IsEmpty()) {
            return OpexRailQuoteFailure(failure, "TRKFAIL", cur, AIError.ERR_PRECONDITION_FAILED);
          }
          ok = AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridges.Begin(), cur, next);
        }
      } else {
        ok = AIRail.BuildRail(prev, cur, next);
      }
      if (!ok) {
        local error = AIError.GetLastError();
        /* Seulement une voie DEJA presente peut etre testee par connectivite.
         * Ne jamais exiger AreTilesConnected apres une pose seulement simulee. */
        if (error == AIError.ERR_ALREADY_BUILT &&
            AIMap.DistanceManhattan(prev, cur) == 1 && AIMap.DistanceManhattan(cur, next) == 1 &&
            AIRail.IsRailTile(cur) && AITile.GetOwner(cur) == AICompany.ResolveCompanyID(AICompany.COMPANY_SELF) &&
            AIRail.GetRailType(cur) == AIRail.GetCurrentRailType() &&
            AIRail.AreTilesConnected(prev, cur, next)) continue;
        return OpexRailQuoteFailure(failure, "TRKFAIL", cur, error);
      }
    }
    simulatedInfra = accounting.GetCosts();
  }
  return simulatedInfra;
}

/* Capital total du devis rail utilise par le constructeur avant engagement. */
function OpexQuoteRailCapital(catalog, candidate, plan, failure = null)
{
  local realInfra = OpexSimulateRailInfraCost(plan, failure);
  if (realInfra == null) return null;
  if (realInfra <= 0) return 0;
  local depotCost = catalog.costRailDepot + 2 * catalog.costTrackPerTile;
  local vehicleCost = ("vehicleCost" in candidate) ? candidate.vehicleCost : 0;
  if (vehicleCost <= 0 && ("loco" in candidate) && candidate.loco != null &&
      (candidate.cargo in catalog.wagonByCargo)) {
    vehicleCost = candidate.trains * (candidate.loco.price
        + candidate.wagons * catalog.wagonByCargo[candidate.cargo].price);
  }
  return realInfra + depotCost + vehicleCost;
}

/* M4/16.2 : ne jamais engager d'infrastructure si OpenTTD n'a plus aucun slot train.
 * Ce test est volontairement duplique au plus pres de la transaction : task_rail l'utilise avant
 * de lancer l'A*, mais une recherche reprenable peut terminer plusieurs ticks plus tard, apres
 * qu'un autre chemin a consomme le dernier slot. */
function OpexRailVehicleSlotAvailable()
{
  local setting = "vehicle.max_trains";
  if (!AIGameSettings.IsValid(setting)) return true;
  local cap = AIGameSettings.GetValue(setting);
  local used = AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, AIVehicle.VT_RAIL);
  return used < cap;
}

/* Execute la construction reelle d'un plan precalcule ou valide. */
function OpexExecuteRailPlan(catalog, budget, candidate, plan, cashReserve)
{
  local result = { ok = false, reason = "", iterations = plan.iterations, opcodes = plan.opcodes,
                   error = 0, diag = null, trains = 0, vehicles = [],
                   stationA = null, stationB = null, depot = null,
                   platformA = null, platformB = null, trainLength = 0, wagons = candidate.wagons,
                   platformLength = plan.length, locoLength = 0, wagonLength = 0,
                   wantedPlatformLength = candidate.platformLength, plansA = plan.plansA.len(),
                   plansB = plan.plansB.len(), slopeRelaxed = plan.slopeRelaxed,
                   siteClear = plan.siteClear, siteCargo = plan.siteCargo, siteCmd = plan.siteCmd,
                   siteKind = candidate.kind == "pax" ? "P" : "F",
                   capacitySignalsOk = 0, capacitySignalsFail = 0, capacitySignalSegments = 0, capacitySignalFailures = [],
                   doubleTrack = plan.doubleTrack, doubleSkip = plan.doubleSkip,
                   doubleTiles = plan.doubleTiles, doubleDepot = plan.doubleDepot,
                   capital = plan.capital, money = 0, actualCost = 0,
                   budgetInfo = plan.budgetInfo, iterationBudget = plan.iterationBudget,
                   segmentedSegments = plan.segmentedSegments,
                   segmentedBacktracks = plan.segmentedBacktracks,
                   segmentedLocalChoices = plan.segmentedLocalChoices };

  local planA = plan.planA;
  local planB = plan.planB;
  local tiles = plan.tiles;
  /* Franchissement colle a une sortie de gare. Deux entiers sur result, lus par
   * RAIL_ATTEMPT. -1 si le trace est absent ou trop court pour l'index. Nul au defaut. */
  if (DECISION_LOG) {
    local crossStart = -1;
    local crossEnd = -1;
    if (tiles != null && tiles.len() >= 2) {
      crossStart = (AIMap.DistanceManhattan(tiles[0], tiles[1]) > 1) ? 1 : 0;
    }
    if (tiles != null && tiles.len() >= 3) {
      local tail = tiles.len() - 1;
      crossEnd = (AIMap.DistanceManhattan(tiles[tail - 2], tiles[tail - 1]) > 1) ? 1 : 0;
    }
    result.startx <- crossStart;
    result.endx <- crossEnd;
  }
  if (RAIL_DEVIS) {
    local quoteFailure = {};
    local realCapital = OpexQuoteRailCapital(catalog, candidate, plan, quoteFailure);
    if (realCapital == null) {
      result.error = quoteFailure.error;
      result.reason = result.error == AIError.ERR_NOT_ENOUGH_CASH ? "CASH" : quoteFailure.reason;
      result.quoteFailure <- quoteFailure;
      return result;
    }
    if (realCapital > 0) {
      result.capital = realCapital;
      /* G3 : le devis est une information economique, pas uniquement un garde de cash. */
      OpexApplyRailActualCapital(candidate, realCapital);
      plan.capital = candidate.capital;
    }
  }

  result.money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local need = result.capital + cashReserve;
  if (result.money < need) {
    if (result.money < need) { result.reason = "CASH"; return result; }
  }

  /* Fail-before-spend : stations, voie, depot et terrassement commencent juste apres. */
  if (!OpexRailVehicleSlotAvailable()) {
    result.reason = "NOTRAIN";
    return result;
  }

  local costs = AIAccounting();

  budget.begin();
  for (local i = 0; i < planA.length; i++) {
    AITile.DemolishTile(planA.anchor + planA.step * i);
  }
  for (local i = 0; i < planB.length; i++) {
    AITile.DemolishTile(planB.anchor + planB.step * i);
  }
  local stIdA = ("stationId" in planA) ? planA.stationId : AIStation.STATION_NEW;
  local stIdB = ("stationId" in planB) ? planB.stationId : AIStation.STATION_NEW;
  local okA = AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length, stIdA);
  local okB = AIRail.BuildRailStation(planB.anchor, planB.direction, 1, planB.length, stIdB);
  if (!okA || !okB) {
    /* Avant rollback : DemolishTile ecraserait GetLastError. decision_log=0 n'entre pas. */
    if (DECISION_LOG) {
      local err = AIError.GetLastError();
      OpexDecide("RAIL_STN_FAIL", "ok_a=" + (okA ? 1 : 0)
          + " ok_b=" + (okB ? 1 : 0)
          + " anchor_a=" + planA.anchor
          + " anchor_b=" + planB.anchor
          + " len_a=" + planA.length
          + " len_b=" + planB.length
          + " err=" + err);
    }
    OpexRollback(null, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.opcodes += budget.end("build_stations"); result.reason = "STNFAIL"; return result;
  }

  /* Table seulement sous decision_log : null au defaut, aucune allocation. */
  local trackFailure = null;
  if (DECISION_LOG) trackFailure = {};
  local trackFailed = OpexBuildTrack(tiles, plan.structures, trackFailure);
  local last = tiles.len() - 1;
  local connected = trackFailed == 0 &&
      AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) &&
      AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit);
  if (!connected) {
    /* Avant rollback, et seulement ici : `connected` court-circuite les deux
     * AreTilesConnected quand trackFailed > 0. Memes indices. len < 3 : -1. */
    if (DECISION_LOG) {
      local exitA = -1;
      local exitB = -1;
      if (tiles.len() >= 3) {
        exitA = AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) ? 1 : 0;
        exitB = AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit) ? 1 : 0;
      }
      local fields = "cause=" + (trackFailed > 0 ? "track" : "connect")
          + " failed=" + trackFailed
          + " tiles=" + tiles.len()
          + " exit_a=" + exitA
          + " exit_b=" + exitB;
      if (trackFailed > 0 && trackFailure != null && ("index" in trackFailure)) {
        fields += " idx=" + trackFailure.index
            + " tile=" + trackFailure.tile
            + " kind=" + trackFailure.kind
            + " err=" + trackFailure.error
            + " mprev=" + trackFailure.manh_prev
            + " mnext=" + trackFailure.manh_next;
        /* Cles optionnelles : une cle absente leve en Squirrel. */
        if ("is_buildable" in trackFailure) fields += " bld=" + trackFailure.is_buildable;
        if ("is_rail" in trackFailure) fields += " rail=" + trackFailure.is_rail;
        if ("is_station" in trackFailure) fields += " stn=" + trackFailure.is_station;
        if ("is_road" in trackFailure) fields += " road=" + trackFailure.is_road;
        if ("is_water" in trackFailure) fields += " watr=" + trackFailure.is_water;
        if ("owner_self" in trackFailure) fields += " own=" + trackFailure.owner_self;
        if ("slope" in trackFailure) fields += " slp=" + trackFailure.slope;
        if ("dup_index" in trackFailure) fields += " dup=" + trackFailure.dup_index;
      }
      /* Identite planifiee de la gare B, toujours sous DECISION_LOG. */
      if ("lead" in planB) fields += " leadb=" + planB.lead;
      if ("station_exit" in planB) fields += " exitb=" + planB.station_exit;
      /* Deux bouts du trace, y compris quand failed=0 (table failure vide).
       * len < 3 : aucun index, ces champs sont absents. */
      if (tiles.len() >= 3) {
        fields += " h0=" + tiles[0]
            + " h1=" + tiles[1]
            + " h2=" + tiles[2]
            + " d01=" + AIMap.DistanceManhattan(tiles[0], tiles[1])
            + " d12=" + AIMap.DistanceManhattan(tiles[1], tiles[2])
            + " t2=" + tiles[last - 2]
            + " t1=" + tiles[last - 1]
            + " t0=" + tiles[last]
            + " d21=" + AIMap.DistanceManhattan(tiles[last - 2], tiles[last - 1])
            + " d10=" + AIMap.DistanceManhattan(tiles[last - 1], tiles[last]);
      }
      OpexDecide("RAIL_TRACK_FAIL", fields);
    }
    OpexRollback(tiles, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.opcodes += budget.end("build_track"); result.reason = "TRKFAIL"; return result;
  }

  local depot = OpexBuildDepot(tiles);
  result.opcodes += budget.end("build_track");
  if (depot == null) {
    OpexRollback(tiles, planA, planB, null, null);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "DEPFAIL"; return result;
  }

  local primaryCost = costs.GetCosts();
  costs = null;

  local tiles2 = plan.tiles2;
  local planA2 = plan.planA2;
  local planB2 = plan.planB2;
  local depot2 = plan.depot2;
  local want = 1;
  local doubleCost = 0;
  local okD = false;

  if (plan.doubleTrack == 1 && tiles2 != null && planA2 != null && planB2 != null) {
    local dCosts = AIAccounting();
    for (local i = 0; i < planA2.length; i++) AITile.DemolishTile(planA2.anchor + planA2.step * i);
    for (local i = 0; i < planB2.length; i++) AITile.DemolishTile(planB2.anchor + planB2.step * i);
    local okA2 = AIRail.BuildRailStation(planA2.anchor, planA2.direction, 1, planA2.length,
                                        AIStation.GetStationID(planA.anchor));
    local okB2 = AIRail.BuildRailStation(planB2.anchor, planB2.direction, 1, planB2.length,
                                        AIStation.GetStationID(planB.anchor));
    if (okA2 && okB2) {
      local tFail = OpexBuildTrack(tiles2, plan.structures2);
      local l2 = tiles2.len() - 1;
      local conn2 = tFail == 0 &&
          AIRail.AreTilesConnected(planA2.station_exit, tiles2[1], tiles2[2]) &&
          AIRail.AreTilesConnected(tiles2[l2 - 2], tiles2[l2 - 1], planB2.station_exit);
      if (conn2) {
        depot2 = OpexBuildDepot(tiles2);
        if (depot2 != null) {
          okD = true;
          doubleCost = dCosts.GetCosts();
          want = candidate.trains > 2 ? 2 : candidate.trains;
        }
      }
    }
    if (!okD) {
      OpexRollback(tiles2, planA2, planB2, depot2, null);
      tiles2 = null; planA2 = null; planB2 = null; depot2 = null;
    }
  }

  local postPathCosts = AIAccounting();
  budget.begin();
  local trains = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, depot,
                                 planA.station_exit, planB.station_exit, 1, candidate.loco,
                                 candidate.wagons, candidate.platformLength, false);
  if (!trains.failed && trains.built > 0 && want == 2 && depot2 != null) {
    local second = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, depot2,
                                   planA2.station_exit, planB2.station_exit, 1, candidate.loco,
                                   candidate.wagons, candidate.platformLength, false);
    if (second.failed || second.built == 0) {
      foreach (vehicle in trains.rollbackVehicles) second.rollbackVehicles.append(vehicle);
      trains = second;
    } else {
      foreach (vehicle in second.vehicles) trains.vehicles.append(vehicle);
      foreach (vehicle in second.rollbackVehicles) trains.rollbackVehicles.append(vehicle);
      trains.built += second.built;
    }
  }
  if (!trains.failed && trains.built > 0) {
    local started = [];
    local startFailed = false;
    foreach (train in trains.vehicles) {
      if (!AIVehicle.StartStopVehicle(train)) {
        startFailed = true;
        trains.failed = true;
        trains.failure = "START";
        trains.error = AIError.GetLastError();
        break;
      }
      started.append(train);
    }
    if (startFailed) {
      foreach (train in started) {
        AIVehicle.StartStopVehicle(train);
      }
    }
  }
  result.opcodes += budget.end("build_trains");
  result.error = trains.error;
  result.diag = trains.diag;
  if (trains.failed || trains.built == 0) {
    if (tiles2 != null) OpexRollback(tiles2, planA2, planB2, depot2, trains.rollbackVehicles);
    OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
    result.actualCost = primaryCost + (postPathCosts != null ? postPathCosts.GetCosts() : 0);
    result.reason = (trains.failed && trains.failure == "ORDER") ? "ORDFAIL" : "NOTRAIN";
    return result;
  }

  result.ok = true;
  result.reason = "OK";
  result.trains = trains.built;
  result.trainLength = trains.trainLength;
  result.locoLength = trains.locoLength;
  result.wagonLength = trains.wagonLength;
  result.vehicles = trains.vehicles;
  result.actualCost = primaryCost + doubleCost + postPathCosts.GetCosts();
  /* Les tuiles reellement payees (ponts, tunnels, demolitions, seconde voie) remplacent enfin
   * le devis avant que main.nut n'inscrive les predictions de la ligne. */
  OpexApplyRailActualCapital(candidate, result.actualCost);
  result.capital = candidate.capital;
  result.stationA = planA.station_exit;
  result.stationB = planB.station_exit;
  result.depot = depot;
  /* Le refleet est accessible avec les defauts livres : l'upgrade de seconde
   * voie relit station_exit et lead via OpexSameStationEnd. Ces metadonnees sont
   * donc un contrat de la ligne rail. */
  result.platformA = { anchor = planA.anchor, direction = planA.direction, step = planA.step,
                       length = planA.length, station_exit = planA.station_exit, lead = planA.lead };
  result.platformB = { anchor = planB.anchor, direction = planB.direction, step = planB.step,
                       length = planB.length, station_exit = planB.station_exit, lead = planB.lead };
  result.doubleTrack <- (okD ? 1 : 0);
  if (okD && depot2 != null) {
    result.depot2 <- depot2;
    result.stationA2 <- planA2.station_exit;
    result.stationB2 <- planB2.station_exit;
    result.platformA2 <- { anchor = planA2.anchor, direction = planA2.direction, step = planA2.step, length = planA2.length };
    result.platformB2 <- { anchor = planB2.anchor, direction = planB2.direction, step = planB2.step, length = planB2.length };
  }
  return result;
}

/* Construit une ligne complete, en reutilisant le plan precalcule s'il est present.
 * Un railPlan non-null, y compris en echec (ABND/DEAD/SITE), est consomme tel quel : la
 * recherche reprenable a deja paye les iterations, les rejouer casserait le denominateur
 * et referait le gel. Le bras historique (railPlan absent) planifie puis construit. */
function OpexBuildLine(catalog, budget, candidate, alternativeRatio, cashReserve, hardCap = 10000)
{
  /* C67.6 rail : cout modele avant devis, pour mesurer l'ecart au facteur fixe 1,70.
   * Journal de decision seulement (defaut 0) : aucun effet sur la partie par defaut. */
  if (DECISION_LOG && !("modelCapital" in candidate)
      && !(("capitalIsActual" in candidate) && candidate.capitalIsActual))
    candidate.modelCapital <- candidate.capital;
  local plan = null;
  if (("railPlan" in candidate) && candidate.railPlan != null) {
    plan = candidate.railPlan;
  } else {
    plan = OpexPlanRailRoute(catalog, budget, candidate, alternativeRatio, hardCap);
  }
  if (!plan.ok) {
    return { ok = false, reason = plan.reason, iterations = plan.iterations, opcodes = plan.opcodes,
             siteClear = plan.siteClear, siteCargo = plan.siteCargo, siteCmd = plan.siteCmd,
             siteKind = "N", error = 0, diag = null,
             trains = 0, doubleTrack = 0, doubleSkip = 0,
             capacitySignalSegments = 0, capacitySignalsOk = 0, capacitySignalsFail = 0,
             capacitySignalFailures = [],
             budgetInfo = plan.budgetInfo, iterationBudget = plan.iterationBudget,
             segmentedSegments = plan.segmentedSegments,
             segmentedBacktracks = plan.segmentedBacktracks,
             segmentedLocalChoices = plan.segmentedLocalChoices };
  }
  return OpexExecuteRailPlan(catalog, budget, candidate, plan, cashReserve);
}

/* Prepare la recherche de seconde voie d'une ligne existante, SANS lancer l'A*.
 * ok=false => pas de pathfinder a poser (raison dans .reason). */
function OpexPrepareUpgradeSearch(line, hardCap = 10000)
{
  local prep = { ok = false, reason = "", dualA = null, dualB = null, ignored = null,
                 forbidden = null, iterationBudget = hardCap, planA = null, planB = null,
                 stationIdA = -1, stationIdB = -1 };
  if (line == null || (("doubleTrack" in line) && line.doubleTrack == 1)) {
    prep.reason = "ALREADY_DOUBLE";
    return prep;
  }
  if (!("platformA" in line) || !("platformB" in line) || line.platformA == null || line.platformB == null) {
    prep.reason = "NOPLATFORM";
    return prep;
  }
  local stationIdA = AIStation.GetStationID(line.stationA);
  local stationIdB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationIdA) || !AIStation.IsValidStation(stationIdB)) {
    prep.reason = "NOSTATION";
    return prep;
  }

  local forbidden = {};
  if (("depot" in line) && line.depot != null) {
    forbidden[line.depot] <- true;
    local df = AIRail.GetRailDepotFrontTile(line.depot);
    if (AIMap.IsValidTile(df)) forbidden[df] <- true;
  }
  local planA = line.platformA;
  local planB = line.platformB;
  for (local i = 0; i < planA.length; i++) forbidden[planA.anchor + planA.step * i] <- true;
  for (local i = 0; i < planB.length; i++) forbidden[planB.anchor + planB.step * i] <- true;

  local dualA = [];
  foreach (plan in OpexJoinPlatformPlans(planA, stationIdA)) {
    if (OpexSameStationEnd(plan, planA) && !OpexPlanHitsSet(plan, forbidden)) dualA.append(plan);
  }
  local dualB = [];
  foreach (plan in OpexJoinPlatformPlans(planB, stationIdB)) {
    if (OpexSameStationEnd(plan, planB) && !OpexPlanHitsSet(plan, forbidden)) dualB.append(plan);
  }
  if (dualA.len() == 0 || dualB.len() == 0) {
    prep.reason = "NOSPOT";
    return prep;
  }

  local ignored = [];
  foreach (tile, ignoredVal in forbidden) ignored.append(tile);
  prep.ok = true;
  prep.reason = "OK";
  prep.dualA = dualA;
  prep.dualB = dualB;
  prep.ignored = ignored;
  prep.forbidden = forbidden;
  prep.planA = planA;
  prep.planB = planB;
  prep.stationIdA = stationIdA;
  prep.stationIdB = stationIdB;
  return prep;
}

/* Pose la seconde voie une fois l'A* termine. search.iterations est ignore ici
 * (l'upgrade n'entre pas dans le denominateur du classement des candidats). */
function OpexExecuteUpgradeAfterSearch(catalog, budget, line, cashReserve, search, prep)
{
  local result = { ok = false, reason = "", cost = 0, train = null, depot2 = null,
                   stationA2 = null, stationB2 = null, platformA2 = null, platformB2 = null };
  if (search.path == false || search.path == null) {
    result.reason = "NOPATH";
    return result;
  }
  local tiles2 = OpexResolveSearchTiles(search);
  local structures2 = OpexResolveSearchStructures(search);
  if (tiles2.len() < 3) {
    result.reason = "SHORT";
    return result;
  }
  local planA2 = OpexMatchPlan(prep.dualA, tiles2[0]);
  local planB2 = OpexMatchPlan(prep.dualB, tiles2[tiles2.len() - 1]);
  if (planA2 == null || planB2 == null) {
    result.reason = "NOMATCH";
    return result;
  }
  if (!OpexJoinPathIsDedicated(tiles2)) {
    result.reason = "OVERLAP";
    return result;
  }
  for (local i = 1; i < tiles2.len() - 1; i++) {
    if (tiles2[i] in prep.forbidden) {
      result.reason = "OVERLAP";
      return result;
    }
  }

  local wagon = (line.cargo in catalog.wagonByCargo) ? catalog.wagonByCargo[line.cargo] : null;
  if (wagon == null) { result.reason = "NOWAGON"; return result; }
  local depotCost = AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_DEPOT);
  local trackCost = tiles2.len() * catalog.costTrackPerTile + (planA2.length + planB2.length) * catalog.costStation + depotCost;
  local trainCost = line.loco.price + line.wagons * wagon.price;
  local totalNeeded = trackCost + trainCost + cashReserve;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < totalNeeded) {
    result.reason = "CASH";
    return result;
  }

  local costs = AIAccounting();
  for (local i = 0; i < planA2.length; i++) AITile.DemolishTile(planA2.anchor + planA2.step * i);
  for (local i = 0; i < planB2.length; i++) AITile.DemolishTile(planB2.anchor + planB2.step * i);
  local okA = AIRail.BuildRailStation(planA2.anchor, planA2.direction, 1, planA2.length, prep.stationIdA);
  local okB = AIRail.BuildRailStation(planB2.anchor, planB2.direction, 1, planB2.length, prep.stationIdB);
  local joinedA = AIStation.GetStationID(planA2.anchor) == prep.stationIdA;
  local joinedB = AIStation.GetStationID(planB2.anchor) == prep.stationIdB;
  if (!okA || !okB || !joinedA || !joinedB) {
    OpexRollback(null, planA2, planB2, null, null);
    result.reason = "STATIONFAIL";
    return result;
  }

  local trackFailed = OpexBuildTrack(tiles2, structures2);
  local last = tiles2.len() - 1;
  local connected = trackFailed == 0 &&
      AIRail.AreTilesConnected(planA2.station_exit, tiles2[1], tiles2[2]) &&
      AIRail.AreTilesConnected(tiles2[last - 2], tiles2[last - 1], planB2.station_exit);
  if (!connected) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    result.reason = "TRACKFAIL";
    return result;
  }

  local depot2 = OpexBuildDepot(tiles2, prep.forbidden);
  if (depot2 == null) {
    OpexRollback(tiles2, planA2, planB2, null, null);
    result.reason = "DEPOTFAIL";
    return result;
  }

  local signals = OpexPlaceJoinSignals(planA2, planB2, tiles2, depot2);

  local newTrains = OpexBuildTrains(catalog, line.cargo, line.kind, depot2,
                                    planA2.station_exit, planB2.station_exit, 1,
                                    line.loco, line.wagons, line.platformLength, true);
  if (newTrains.failed || newTrains.built == 0) {
    OpexRollback(tiles2, planA2, planB2, depot2, newTrains.rollbackVehicles);
    result.reason = "TRAINFAIL";
    return result;
  }

  result.ok = true;
  result.reason = "OK";
  result.depot2 = depot2;
  result.stationA2 = planA2.station_exit;
  result.stationB2 = planB2.station_exit;
  result.platformA2 = { anchor = planA2.anchor, direction = planA2.direction, step = planA2.step, length = planA2.length };
  result.platformB2 = { anchor = planB2.anchor, direction = planB2.direction, step = planB2.step, length = planB2.length };
  result.train = newTrains.vehicles[0];
  result.cost = costs.GetCosts();
  return result;
}

/* Doublement securise d'une ligne ferroviaire existante :
 * Pose un second quai a la gare A, un second quai a la gare B,
 * trace une seconde voie dediee avec son propre depot, pose les signaux PBS,
 * et lance le deuxieme convoi. Zero collision, voies independantes.
 * Mode bloquant (rail_search_resumable=0). Le mode reprenable orchestre
 * Prepare / tranches / Execute depuis OpexAI::_continueRailSearch. */
function OpexUpgradeRailLineToDoubleTrack(catalog, budget, line, cashReserve, hardCap = 10000)
{
  local result = { ok = false, reason = "", cost = 0, train = null, depot2 = null,
                   stationA2 = null, stationB2 = null, platformA2 = null, platformB2 = null };
  local prep = OpexPrepareUpgradeSearch(line, hardCap);
  if (!prep.ok) {
    result.reason = prep.reason;
    return result;
  }
  local deadlineTick = AIController.GetTick() + hardCap / 3 + BUILD_TICK_MARGIN;
  local search = OpexSearchPath(prep.dualA, prep.dualB, prep.iterationBudget, deadlineTick, prep.ignored);
  return OpexExecuteUpgradeAfterSearch(catalog, budget, line, cashReserve, search, prep);
}

/* Construit un 2e train sur une ligne deja doublee avec depot2 valide. */
function OpexBuildSecondTrain(catalog, line, cashReserve)
{
  local result = { ok = false, reason = "", train = null };
  if (!("depot2" in line) || line.depot2 == null || !AIRail.IsRailDepotTile(line.depot2)) {
    result.reason = "NODEPOT2"; return result;
  }
  local wagon = (line.cargo in catalog.wagonByCargo) ? catalog.wagonByCargo[line.cargo] : null;
  if (wagon == null) { result.reason = "NOWAGON"; return result; }
  local trainCost = line.loco.price + line.wagons * wagon.price;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < trainCost + cashReserve) {
    result.reason = "CASH"; return result;
  }
  local stA = (("stationA2" in line) && line.stationA2 != null) ? line.stationA2 : line.stationA;
  local stB = (("stationB2" in line) && line.stationB2 != null) ? line.stationB2 : line.stationB;
  local newTrains = OpexBuildTrains(catalog, line.cargo, line.kind, line.depot2,
                                    stA, stB, 1, line.loco, line.wagons, line.platformLength, true);
  if (newTrains.failed || newTrains.built == 0) {
    OpexRollback(null, null, null, null, newTrains.rollbackVehicles);
    result.reason = "TRAINFAIL"; return result;
  }
  result.ok = true;
  result.reason = "OK";
  result.train = newTrains.vehicles[0];
  return result;
}
