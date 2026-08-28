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

/* Longueur de quai : ceil((1 + wagons) / 2) + 1, formule de TrainLineAI. */
const PLATFORM_LENGTH = 4;
const STATION_SEARCH_RADIUS = 30;
const MAX_STATION_PLANS = 12;
const PATH_CHUNK = 50;
const PATHFINDER_MAX_COST = 200000;

/* Plafond absolu, garde-fou : au-dela la ligne est de toute facon dans la zone ou le rendement
 * mesure s'effondre (74 par iteration a 150 tuiles contre 553 a 48). */
const HARD_ITERATION_CAP = 60000;

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
function OpexStationPlans(center, otherCenter, radius, length, maxPlans)
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
              plans.push({ anchor = anchor, station_exit = stationExit, lead = lead,
                           direction = axis[0], step = step });
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

/* Recherche de chemin sous budget d'iterations. Rend une table avec le chemin brut et le compte
 * d'iterations reellement consommees -- ce compte est le DENOMINATEUR du classement, il doit etre
 * mesure, pas estime. */
function OpexSearchPath(plansA, plansB, iterationBudget, deadlineTick, cycleYear)
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
  /* Une recherche ne peut pas consommer l'annee suivante : le cycle Start() doit alors rapporter,
   * entretenir et reclasser avant toute nouvelle tentative. La borne est calendaire, pas un
   * nouveau budget d'opcodes. */
  while (path == false && spent < iterationBudget && AIController.GetTick() < deadlineTick &&
         AIDate.GetYear(AIDate.GetCurrentDate()) == cycleYear) {
    path = pathfinder.FindPath(PATH_CHUNK);
    spent += PATH_CHUNK;
    AIController.Sleep(1);
  }

  /* Codes courts : un nom de panneau accepte au plus 31 caracteres et echoue SILENCIEUSEMENT
   * au-dela (verifie sur TrainLineAI). ABND = budget d'iterations epuise, c'est-a-dire l'arret
   * optimal qui a joue ; DEAD = fenetre de temps epuisee ; YEAR = frontiere annuelle atteinte ;
   * NOPA = file vide, aucun chemin. */
  local stop = "OK";
  if (path == false) {
    if (AIDate.GetYear(AIDate.GetCurrentDate()) != cycleYear) stop = "YEAR";
    else stop = (AIController.GetTick() >= deadlineTick) ? "DEAD" : "ABND";
  }
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
function OpexRollback(tiles, planA, planB, depot)
{
  if (depot != null) AITile.DemolishTile(depot);
  for (local i = 0; i < PLATFORM_LENGTH; i++) {
    if (planA != null) AITile.DemolishTile(planA.anchor + planA.step * i);
    if (planB != null) AITile.DemolishTile(planB.anchor + planB.step * i);
  }
  if (tiles == null) return;
  for (local i = 1; i < tiles.len() - 1; i++) {
    AITile.DemolishTile(tiles[i]);
  }
}

function OpexBuildTrains(catalog, cargo, kind, depotTile, exitA, exitB, wanted)
{
  local wagon = catalog.wagonByCargo[cargo];
  local built = 0;
  local lastError = 0;
  local diag = null;
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
    local train = AIVehicle.BuildVehicle(depotTile, catalog.loco.id);
    if (!AIVehicle.IsValidVehicle(train)) {
      lastError = AIError.GetLastError();
      /* Diagnostic minimal au moment exact de l'echec : c'est moins cher que de deviner. */
      local testOk = 0;
      {
        local probe = AITestMode();
        testOk = AIVehicle.BuildVehicle(depotTile, catalog.loco.id) != null ? 1 : 0;
      }
      diag = {
        railtype = AIRail.GetCurrentRailType(),
        isDepot = AIRail.IsRailDepotTile(depotTile) ? 1 : 0,
        buildable = AIEngine.IsBuildable(catalog.loco.id) ? 1 : 0,
        canRun = AIEngine.CanRunOnRail(catalog.loco.id, AIRail.GetCurrentRailType()) ? 1 : 0,
        price = catalog.loco.price,
        cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF),
        engineRail = AIEngine.GetRailType(catalog.loco.id),
        depotRail = AIRail.GetRailType(depotTile),
        vehType = AIEngine.GetVehicleType(catalog.loco.id),
        testOk = testOk,
      };
      break;
    }
    for (local w = 0; w < WAGONS_PER_TRAIN; w++) {
      local car = AIVehicle.BuildVehicle(depotTile, wagon.id);
      if (AIVehicle.IsValidVehicle(car)) AIVehicle.MoveWagon(car, 0, train, 0);
    }
    local okA = AIOrder.AppendOrder(train, exitA, AIOrder.OF_FULL_LOAD_ANY);
    local okB = AIOrder.AppendOrder(train, exitB, flagsB);
    if (!okA || !okB || AIOrder.GetOrderCount(train) != 2) {
      return { built = built, failed = true, error = lastError, diag = diag };
    }
    AIVehicle.StartStopVehicle(train);
    built++;
  }
  return { built = built, failed = false, error = lastError, diag = diag };
}

/* Construit une ligne complete. Rend une table de resultat, jamais d'exception. */
function OpexBuildLine(catalog, budget, candidate, iterationBudget, deadlineTick, cycleYear)
{
  local result = { ok = false, reason = "", iterations = 0, opcodes = 0, error = 0, diag = null,
                   trains = 0, stationA = null, stationB = null, depot = null };

  budget.begin();
  local plansA = OpexStationPlans(candidate.src, candidate.dst,
                                  STATION_SEARCH_RADIUS, PLATFORM_LENGTH, MAX_STATION_PLANS);
  local plansB = OpexStationPlans(candidate.dst, candidate.src,
                                  STATION_SEARCH_RADIUS, PLATFORM_LENGTH, MAX_STATION_PLANS);
  result.opcodes += budget.end("build_plans");
  if (plansA.len() == 0 || plansB.len() == 0) { result.reason = "NOPLAN"; return result; }

  budget.begin();
  local search = OpexSearchPath(plansA, plansB, iterationBudget, deadlineTick, cycleYear);
  result.opcodes += budget.end("build_search");
  result.iterations = search.iterations;
  if (search.path == false || search.path == null) { result.reason = search.stop; return result; }

  local tiles = OpexPathTiles(search.path);
  if (tiles.len() < 3) { result.reason = "SHORT"; return result; }
  local planA = OpexMatchPlan(plansA, tiles[0]);
  local planB = OpexMatchPlan(plansB, tiles[tiles.len() - 1]);
  if (planA == null || planB == null) { result.reason = "NOMATCH"; return result; }

  budget.begin();
  for (local i = 0; i < PLATFORM_LENGTH; i++) {
    AITile.DemolishTile(planA.anchor + planA.step * i);
    AITile.DemolishTile(planB.anchor + planB.step * i);
  }
  local okA = AIRail.BuildRailStation(planA.anchor, planA.direction, 1, PLATFORM_LENGTH,
                                      AIStation.STATION_NEW);
  local okB = AIRail.BuildRailStation(planB.anchor, planB.direction, 1, PLATFORM_LENGTH,
                                      AIStation.STATION_NEW);
  if (!okA || !okB) {
    OpexRollback(null, planA, planB, null);
    result.opcodes += budget.end("build_stations"); result.reason = "STNFAIL"; return result;
  }

  local trackFailed = OpexBuildTrack(tiles);
  local last = tiles.len() - 1;
  local connected = trackFailed == 0 &&
      AIRail.AreTilesConnected(planA.station_exit, tiles[1], tiles[2]) &&
      AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planB.station_exit);
  if (!connected) {
    OpexRollback(tiles, planA, planB, null);
    result.opcodes += budget.end("build_track"); result.reason = "TRKFAIL"; return result;
  }

  local depot = OpexBuildDepot(tiles);
  result.opcodes += budget.end("build_track");
  if (depot == null) {
    OpexRollback(tiles, planA, planB, null);
    result.reason = "DEPFAIL"; return result;
  }

  budget.begin();
  local trains = OpexBuildTrains(catalog, candidate.cargo, candidate.kind, depot,
                                 planA.station_exit, planB.station_exit, candidate.trains);
  result.opcodes += budget.end("build_trains");
  result.error = trains.error;
  result.diag = trains.diag;
  if (trains.failed) {
    OpexRollback(tiles, planA, planB, depot);
    result.reason = "ORDFAIL"; return result;
  }
  if (trains.built == 0) {
    OpexRollback(tiles, planA, planB, depot);
    result.reason = "NOTRAIN"; return result;
  }

  result.ok = true;
  result.reason = "OK";
  result.trains = trains.built;
  result.stationA = planA.station_exit;
  result.stationB = planB.station_exit;
  result.depot = depot;
  return result;
}
