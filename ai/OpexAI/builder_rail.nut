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
const PATH_CHUNK = 50;
const PATHFINDER_MAX_COST = 200000;

/* Plafond absolu, garde-fou reglable depuis main.nut::HARD_ITERATION_CAP. La mesure du 2026-08-29
 * (4 graines x 20 ans) a trouve 36 600 iterations comme maximum d'une reussite ; 40 000 garde 9 %
 * de marge, alors que les ABND a 60 000 absorbaient 56,5 % des opcodes de construction. */

/* Le budget derive du rapport est AMORTI (il vient de "iterations par ligne REUSSIE", qui inclut
 * deja les tentatives ratees) ; une tentative INDIVIDUELLE en demande plusieurs fois plus, car la
 * distribution est tres asymetrique -- a 30 tuiles la mediane est ~200 iterations pour une moyenne
 * de 352. Couper a la moyenne fait echouer une tentative sur deux ET jette la recherche deja
 * payee. Mesure du 2026-08-28 : sans ce facteur, 60 tentatives sur 5 ans, budgets de 50 a 400
 * iterations, zero ligne construite. */
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
function OpexIterationBudget(profitAnnual, alternativeRatio)
{
  /* Le chemin est retourne avec le budget pour l'instrumentation : Z = pas d'alternative,
   * F = plancher de tentative, C = plafond dur, N = forme fermee non bornee. */
  if (alternativeRatio <= 0) return { budget = HARD_ITERATION_CAP, path = "Z" };
  local budget = ATTEMPT_MULTIPLIER * (profitAnnual * 1000) / alternativeRatio;
  if (budget < ATTEMPT_FLOOR) return { budget = ATTEMPT_FLOOR, path = "F" };
  if (budget > HARD_ITERATION_CAP) return { budget = HARD_ITERATION_CAP, path = "C" };
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
 * pathfinder une entree dediee sans avoir a raccorder la voie ancienne. */
function OpexJoinPlatformPlans(platform, stationId)
{
  local length = platform.length;
  local plans = [];
  local sideways = platform.direction == AIRail.RAILTRACK_NE_SW
      ? AIMap.GetTileIndex(0, 1) : AIMap.GetTileIndex(1, 0);
  for (local side = -1; side <= 1; side += 2) {
    local anchor = platform.anchor + sideways * side;
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

      /* Le test inclut les regles de jointure et de taille de gare du moteur. Une reussite de
       * BuildRailStation ne suffit toujours pas pour la VOIE : elle sera controlee plus bas par
       * AreTilesConnected apres chaque pose. */
      local joins = false;
      {
        local probe = AITestMode();
        joins = AIRail.BuildRailStation(anchor, platform.direction, 1, length, stationId);
      }
      if (joins) {
        plans.push({ anchor = anchor, station_exit = stationExit, lead = lead,
                     direction = platform.direction, step = platform.step, length = length });
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
 *
 * Le quai joint est l'exception necessaire : il doit reprendre la longueur du quai existant pour
 * rester parallele et servir la meme gare. Il ne peut pas se raccourcir sans casser cet alignement;
 * l'autre extremite est alors cherchee a cette longueur precise. */
function OpexRailPlatformPlans(catalog, candidate, join)
{
  local joinA = join != null && join.candidateEnd == "A";
  local statsA = { nClear = 0, nCargo = 0, nCmd = 0 };
  local statsB = { nClear = 0, nCargo = 0, nCmd = 0 };
  if (join != null) {
    local length = join.platform.length;
    local plansA = joinA
        ? OpexJoinPlatformPlans(join.platform, join.stationId)
        : OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, length,
                           MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage, true,
                           statsA);
    local plansB = !joinA
        ? OpexJoinPlatformPlans(join.platform, join.stationId)
        : OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, length,
                           MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                           candidate.kind == "pax", statsB);
    if (plansA.len() > 0 && plansB.len() > 0) {
      return { plansA = plansA, plansB = plansB, length = length, joinA = joinA,
               slopeRelaxed = 0, reason = "OK", statsA = statsA, statsB = statsB };
    }
    return { plansA = null, plansB = null, length = length, joinA = joinA, slopeRelaxed = 0,
             reason = OpexRailSiteReason(plansA.len() > 0, plansB.len() > 0),
             statsA = statsA, statsB = statsB };
  }

  local floor = OpexRailMinimumPlatformLength();
  local wanted = candidate.platformLength;
  if (wanted > catalog.platformLength) wanted = catalog.platformLength;
  local sawA = false;
  local sawB = false;
  for (local length = wanted; length >= floor; length--) {
    local found = OpexRailTryPlatformLength(catalog, candidate, length, statsA, statsB);
    if (found.nA > 0) sawA = true;
    if (found.nB > 0) sawB = true;
    if (found.ok) {
      return { plansA = found.plansA, plansB = found.plansB, length = length, joinA = false,
               slopeRelaxed = 0, reason = "OK", statsA = statsA, statsB = statsB };
    }
  }
  if (!sawA) {
    local plansB = OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, floor,
                                    MAX_STATION_PLANS, candidate.cargo, catalog.railCoverage,
                                    candidate.kind == "pax", statsB);
    if (plansB.len() > 0) sawB = true;
  }
  return { plansA = null, plansB = null, length = 0, joinA = false, slopeRelaxed = 0,
           reason = OpexRailSiteReason(sawA, sawB), statsA = statsA, statsB = statsB };
}

/* Recherche de chemin sous budget d'iterations. Rend une table avec le chemin brut et le compte
 * d'iterations reellement consommees -- ce compte est le DENOMINATEUR du classement, il doit etre
 * mesure, pas estime. */
function OpexSearchPath(plansA, plansB, iterationBudget, deadlineTick)
{
  local sources = [];
  local goals = [];
  /* Convention [lead, station_exit] aux deux bouts : node[0] est le vrai depart, node[1] le
   * predecesseur virtuel ; a l'arrivee la bibliotheque ajoute goal[1] apres goal[0]. */
  foreach (plan in plansA) sources.push([plan.lead, plan.station_exit]);
  foreach (plan in plansB) goals.push([plan.lead, plan.station_exit]);

  local pathfinder = RailPathFinder();
  pathfinder.cost.max_cost = PATHFINDER_MAX_COST;
  pathfinder.InitializePath(sources, goals);

  local path = false;
  local spent = 0;
  /* 0 par defaut = aucun bridage : AAAHogEx ne dort PAS entre ses chunks (verifie dans son
   * source, cf. info.nut::pathfinder_sleep_ticks), donc le Sleep(1) inconditionnel qui etait ici
   * etait un handicap que nous seuls payions face a lui. Reglable pour rendre la main plus
   * souvent dans une partie avec des humains. */
  local sleepTicks = AIController.GetSetting("pathfinder_sleep_ticks");
  while (path == false && spent < iterationBudget && AIController.GetTick() < deadlineTick) {
    path = pathfinder.FindPath(PATH_CHUNK);
    spent += PATH_CHUNK;
    if (sleepTicks > 0) AIController.Sleep(sleepTicks);
  }

  /* Codes courts : un nom de panneau accepte au plus 31 caracteres et echoue SILENCIEUSEMENT
   * au-dela (verifie sur TrainLineAI). ABND = budget d'iterations epuise, c'est-a-dire l'arret
   * optimal qui a joue ; DEAD = fenetre de temps epuisee ; NOPA = file vide, aucun chemin. */
  local stop = "OK";
  if (path == false) stop = (AIController.GetTick() >= deadlineTick) ? "DEAD" : "ABND";
  else if (path == null) stop = "NOPA";
  return { path = path, iterations = spent, stop = stop };
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

function OpexMatchPlan(plans, tile)
{
  foreach (plan in plans) {
    if (plan.station_exit == tile) return plan;
  }
  return null;
}

/* La voie du quai joint doit rester une branche independante. Le pathfinder peut donner un cout
 * faible a un rail deja pose ; l'accepter ici fabriquerait precisement l'aiguillage implicite que
 * v1 refuse, et le rollback ne pourrait pas restaurer sa geometrie initiale. Les deux sorties de
 * quai (indices 0 et last) sont exclues : elles sont les nouvelles gares qui seront posees apres
 * ce controle. */
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

/* Pose la voie sur les cases intermediaires. Les extremites sont les sorties de quai. */
function OpexBuildTrack(tiles)
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
      if (AITunnel.GetOtherTunnelEnd(cur) == next) {
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
          !AIRail.AreTilesConnected(prev, cur, next)) ok = false;
    }
    if (!ok) failed++;
  }
  return failed;
}

/* Depot pres du depart. On pose l'aiguillage AVANT le batiment et on verifie la connectivite a
 * chaque etape : un appel qui renvoie "reussi" ne prouve pas que le resultat est raccorde. */
function OpexBuildDepot(tiles)
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
      if (AIRail.IsRailStationTile(candidate) || AIRail.IsRailDepotTile(candidate)) continue;
      local onRoute = false;
      foreach (routeTile in tiles) {
        if (routeTile == candidate) { onRoute = true; break; }
      }
      if (onRoute) continue;

      AITile.DemolishTile(candidate);
      {
        local testMode = AITestMode();
        if (!AIRail.BuildRailDepot(candidate, anchor)) continue;
      }
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

function OpexBuildTrains(catalog, cargo, kind, depotTile, exitA, exitB, wanted, loco, wagons, platformLength)
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
  /* OF_FULL_LOAD_ANY aux deux arrets : verifie empiriquement sur TrainLineAI que OF_NONE fait
   * repartir a vide sur une ligne neuve a faible frequentation -- vrai pour les PAIRES DE VILLES
   * (pax), ou chaque bout produit ET accepte le cargo, donc chaque leg peut se remplir.
   *
   * FAUX pour le fret (diagnostic du 2026-08-28, ai/OpexAI/main.nut::_reportLines, docs/
   * opex_freight_diag.json) : OpexFreightCandidates n'apparie qu'un producteur a un accepteur du
   * MEME cargo -- la ligne est structurellement A SENS UNIQUE, le puits ne produit jamais rien a
   * charger pour le retour. Avec OF_FULL_LOAD_ANY aux deux bouts, le convoi qui arrive au puits
   * reste bloque en VS_AT_STATION (etat 3) a l'ordre 1 pour toujours -- confirme sur un convoi
   * reel (order=1, load=0, coince) -- et sur une gare a UNE seule voie, ce convoi bouche la ligne
   * : les autres convois restent VS_RUNNING vitesse 0 juste derriere. Resultat mesure : note de
   * gare a -1 et revenu nul des la 2e annee sur 3 lignes fret / 3. Les industries elles-memes
   * restaient valides et productives tout du long (IA|...|1|1|prod>0) -- ce n'est donc PAS une
   * fermeture d'industrie. Correctif : le puits fret n'attend PAS de plein chargement (OF_NONE),
   * seule la source continue de le faire. */
  local flagsB = (kind == "freight") ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY;
  for (local i = 0; i < wanted; i++) {
    local train = AIVehicle.BuildVehicle(depotTile, loco.id);
    if (!AIVehicle.IsValidVehicle(train)) {
      lastError = AIError.GetLastError();
      /* Diagnostic minimal au moment exact de l'echec : c'est moins cher que de deviner. */
      local testOk = 0;
      {
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
    local okA = AIOrder.AppendOrder(train, exitA, AIOrder.OF_FULL_LOAD_ANY);
    local okB = AIOrder.AppendOrder(train, exitB, flagsB);
    if (!okA || !okB || AIOrder.GetOrderCount(train) != 2) {
      return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
               failed = true, failure = "ORDER", error = lastError, diag = diag };
    }
    built++;
  }
  /* Pas de train lance avant que la transaction entiere soit certaine : voir OpexRollback. */
  foreach (train in vehicles) AIVehicle.StartStopVehicle(train);
  return { built = built, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
           failed = false, failure = "", error = lastError, diag = diag, trainLength = measuredLength,
           locoLength = measuredLocoLength, wagonLength = measuredWagonLength };
}

/* Construit une ligne complete. Rend une table de resultat, jamais d'exception. */
function OpexBuildLine(catalog, budget, candidate, alternativeRatio, join, cashReserve)
{
  local result = { ok = false, reason = "", iterations = 0, opcodes = 0, error = 0, diag = null,
                   trains = 0, vehicles = [], stationA = null, stationB = null, depot = null,
                   platformA = null, platformB = null, trainLength = 0, wagons = candidate.wagons,
                   platformLength = candidate.platformLength, locoLength = 0, wagonLength = 0,
                   wantedPlatformLength = candidate.platformLength, plansA = 0, plansB = 0,
                   slopeRelaxed = 0, siteClear = 0, siteCargo = 0, siteCmd = 0,
                   siteKind = candidate.kind == "pax" ? "P" : "F",
                   capital = candidate.capital, money = 0,
                   budgetInfo = OpexIterationBudget(candidate.profitAnnual, alternativeRatio),
                   iterationBudget = 0 };
  result.iterationBudget = result.budgetInfo.budget;

  budget.begin();
  local platformPlans = OpexRailPlatformPlans(catalog, candidate, join);
  result.opcodes += budget.end("build_plans");
  /* SITEA/SITEB/SITEAB remplacent le seau NOPLAN : sans eux, 23 echecs a iterations=0 ne disent
   * pas quelle extremite manque, ni si c'est l'economie du quai trouve qui a rendu null. */
  if (platformPlans.plansA == null || platformPlans.reason != "OK") {
    result.reason = platformPlans.reason;
    local stats = platformPlans.reason == "SITEB" ? platformPlans.statsB : platformPlans.statsA;
    result.siteClear = stats.nClear;
    result.siteCargo = stats.nCargo;
    result.siteCmd = stats.nCmd;
    return result;
  }
  local plansA = platformPlans.plansA;
  local plansB = platformPlans.plansB;
  local joinA = platformPlans.joinA;
  result.platformLength = platformPlans.length;
  result.plansA = plansA.len();
  result.plansB = plansB.len();
  result.slopeRelaxed = platformPlans.slopeRelaxed ? 1 : 0;

  /* La recherche a choisi le plus long site faisable. Refaire l'economie AVANT demolition est
   * obligatoire : un repli de 5 a 3 tuiles peut enlever des wagons, changer la locomotive et le
   * nombre de rames. Le second controle de cash couvre aussi une jointure existante plus longue
   * que le quai initialement souhaite. */
  local economics = OpexLineEconomics(catalog, candidate.cargo, candidate.distance,
                                      candidate.monthly, candidate.kind, result.platformLength);
  if (economics == null) { result.reason = "ECON"; return result; }
  result.capital = economics.capital;
  result.money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (result.money < result.capital + cashReserve) { result.reason = "CASH"; return result; }
  OpexApplyRailEconomics(candidate, economics);
  result.wagons = candidate.wagons;
  result.budgetInfo = OpexIterationBudget(candidate.profitAnnual, alternativeRatio);
  result.iterationBudget = result.budgetInfo.budget;

  budget.begin();
  local deadlineTick = AIController.GetTick() + result.iterationBudget / 3 + BUILD_TICK_MARGIN;
  local search = OpexSearchPath(plansA, plansB, result.iterationBudget, deadlineTick);
  result.opcodes += budget.end("build_search");
  result.iterations = search.iterations;
  if (search.path == false || search.path == null) { result.reason = search.stop; return result; }

  local tiles = OpexPathTiles(search.path);
  if (tiles.len() < 3) { result.reason = "SHORT"; return result; }
  local planA = OpexMatchPlan(plansA, tiles[0]);
  local planB = OpexMatchPlan(plansB, tiles[tiles.len() - 1]);
  if (planA == null || planB == null) { result.reason = "NOMATCH"; return result; }
  if (join != null && !OpexJoinPathIsDedicated(tiles)) { result.reason = "JOINPATH"; return result; }

  budget.begin();
  for (local i = 0; i < planA.length; i++) {
    AITile.DemolishTile(planA.anchor + planA.step * i);
  }
  for (local i = 0; i < planB.length; i++) {
    AITile.DemolishTile(planB.anchor + planB.step * i);
  }
  local okA = AIRail.BuildRailStation(planA.anchor, planA.direction, 1, planA.length,
                                      joinA ? join.stationId : AIStation.STATION_NEW);
  local okB = AIRail.BuildRailStation(planB.anchor, planB.direction, 1, planB.length,
                                      !joinA && join != null ? join.stationId : AIStation.STATION_NEW);
  local joinedA = !joinA || AIStation.GetStationID(planA.anchor) == join.stationId;
  local joinedB = joinA || join == null || AIStation.GetStationID(planB.anchor) == join.stationId;
  if (!okA || !okB || !joinedA || !joinedB) {
    OpexRollback(null, planA, planB, null, null);
    result.opcodes += budget.end("build_stations"); result.reason = "STNFAIL"; return result;
  }

  local trackFailed = OpexBuildTrack(tiles);
  local last = tiles.len() - 1;
  local connected = trackFailed == 0 &&
      AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) &&
      AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit);
  if (!connected) {
    OpexRollback(tiles, planA, planB, null, null);
    result.opcodes += budget.end("build_track"); result.reason = "TRKFAIL"; return result;
  }

  local depot = OpexBuildDepot(tiles);
  result.opcodes += budget.end("build_track");
  if (depot == null) {
    OpexRollback(tiles, planA, planB, null, null);
    result.reason = "DEPFAIL"; return result;
  }

  budget.begin();
  local trains = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, depot,
                                 planA.station_exit, planB.station_exit, candidate.trains, candidate.loco,
                                 candidate.wagons, candidate.platformLength);
  result.opcodes += budget.end("build_trains");
  result.error = trains.error;
  result.diag = trains.diag;
  if (trains.failed) {
    OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
    result.reason = trains.failure == "ORDER" ? "ORDFAIL" : "NOTRAIN"; return result;
  }
  if (trains.built == 0) {
    OpexRollback(tiles, planA, planB, depot, trains.rollbackVehicles);
    result.reason = "NOTRAIN"; return result;
  }

  result.ok = true;
  result.reason = "OK";
  result.trains = trains.built;
  result.trainLength = trains.trainLength;
  result.locoLength = trains.locoLength;
  result.wagonLength = trains.wagonLength;
  result.vehicles = trains.vehicles;
  result.stationA = planA.station_exit;
  result.stationB = planB.station_exit;
  result.depot = depot;
  /* La geometrie d'origine est gardee pour pouvoir ajouter le prochain quai sans deviner une
   * gare etrangere. Ce sont les seules tuiles preexistantes que la tranche v1 sait reutiliser. */
  result.platformA = { anchor = planA.anchor, direction = planA.direction, step = planA.step,
                       length = planA.length };
  result.platformB = { anchor = planB.anchor, direction = planB.direction, step = planB.step,
                       length = planB.length };
  return result;
}
