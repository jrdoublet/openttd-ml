import("pathfinder.rail", "RailPathFinder", 1);

/*
 * NOTE SUR Save() :
 * L'etat structure ci-dessous documente ce que l'IA a fait, et reste disponible si vous
 * inspectez le savegame par un autre moyen plus tard. A la date d'ecriture (verifie
 * empiriquement), OpenTTDLab NE LIT PAS cette donnee : son parseur n'expose que l'echo des
 * reglages declares (chunk AIPL.settings), pas le contenu de Save().
 *
 * CANAL REEL : deux panneaux (AISign.BuildSign) sont poses a chaque tentative -- un statut, un
 * detail (voir _code()/_codeDetail() plus bas). Verifie empiriquement : le chunk SIGN du
 * savegame expose bien name/x/y/owner via OpenTTDLab (contrairement a Save(), AILog et — a tord
 * souponne au debut — AISign : le premier essai avait juste tourne trop peu de jours pour que
 * l'IA demarre). Complete par les chunks VEHS/STNN/DEPT/ORDR filtres par owner pour le detail
 * construit.
 *
 * LIMITE DE TAILLE DES PANNEAUX -- verifiee empiriquement, pas supposee : AISign.BuildSign
 * accepte au plus 31 caracteres ; au-dela il echoue *silencieusement* (ID invalide,
 * ERR_PRECONDITION_STRING_TOO_LONG), sans lever d'erreur Squirrel et sans rien afficher en jeu
 * ni dans le chunk SIGN. Avec le format d'origine ("TRLN|<stage>|<raison>|<construits>/<demandes>"),
 * presque toutes les raisons d'echec depassaient deja cette limite a elles seules (ex.
 * "no_buildable_tile_near_town" = 43 caracteres tout compris) : ces panneaux ne se posaient
 * probablement jamais, silencieusement. D'ou REASON_CODES ci-dessous : chaque raison est
 * reduite a un code court avant d'entrer dans un panneau. Legende complete dans docs/methode.md.
 */
/* Assignation racine (<-), pas "local" : les fonctions TrainLineAI::_code() etc. sont compilees
 * comme des affectations de haut niveau independantes, chacune dans son propre scope -- un
 * "local" de fichier n'est pas visible depuis leur corps (verifie empiriquement : "local"
 * provoquait "the index 'REASON_CODES' does not exist" a l'execution). */
::REASON_CODES <- {
  no_rail_type_available = "NORAIL",
  not_enough_towns = "NOTOWN",
  no_suitable_town_pair = "NOPAIR",
  no_pair_meets_population_floor = "MINPOP",
  no_viable_town_pair = "NOVIABLE",
  town_rank_out_of_range = "TWNOOR",
  town_rank_same_town = "TWNDUP",
  pair_rank_out_of_range = "PAIROOR",
  no_disjoint_town_pair = "NODISJ",
  no_buildable_tile_near_town = "NOTILE",
  no_path_found = "NOPATH",
  path_search_limit = "PATHLIM",
  track_build_failed = "TRKFAIL",
  station_build_failed = "STNFAIL",
  depot_build_failed = "DEPFAIL",
  no_engine_available = "NOENG",
  engine_rank_out_of_range = "ENGOOR",
  train_order_failed = "ORDFAIL",
};

class TrainLineAI extends AIController
{
  state = null;
  lastKnownTile = null;
  costs = null; // AIAccounting demarre des que les villes sont choisies -- mesure le cout de
                // construction reel (voie/ponts/tunnels/gares/depot/vehicules), a distinguer du
                // profit d'exploitation des vehicules (VEHS.profit_this_year), qui ne l'inclut
                // pas. Voir docs/methode.md.
}

function TrainLineAI::_report(text)
{
  local tile = this.lastKnownTile;
  if (tile == null) tile = AIMap.GetTileIndex(AIMap.GetMapSizeX() / 2, AIMap.GetMapSizeY() / 2);
  AISign.BuildSign(tile, text);
  AILog.Info(text);
}

/* Panneau de statut : index de ligne (pour rattacher un panneau a une tentative des qu'il y en a
 * plusieurs dans la meme partie -- une seule ligne par instance de compagnie aujourd'hui, mais le
 * champ est deja la pour quand plusieurs instances de TrainLineAI tourneront dans la meme
 * experience), stage, raison courte, trains construits/demandes. */
function TrainLineAI::_code()
{
  local reasonCode = this.state.failure_reason == null ? "OK" : ::REASON_CODES[this.state.failure_reason];
  return "TRLN|" + this.state.line_index + "|" + this.state.stage + "|" + reasonCode + "|" +
      this.state.built_trains + "/" + this.state.requested_trains;
}

/* Panneau de detail : paire de villes (IDs AITown, joignables au chunk CITY) et cout de
 * construction total (AIAccounting, voir plus haut). Uniquement pose si les villes ont ete
 * choisies -- absent pour les echecs qui precedent le choix des villes (no_rail_type_available,
 * not_enough_towns, town_rank_*). */
function TrainLineAI::_codeDetail()
{
  return "TRLN|" + this.state.line_index + "|T" + this.state.town_a + "-" + this.state.town_b +
      "|D" + this.state.distance_straight + "|C" + this.state.construction_cost;
}

/* Panneau de cout vehicules : part du cout total (ci-dessus) depensee en achat de materiel
 * roulant, isolee par difference sur this.costs avant/apres l'etape 7 (voir le commentaire a
 * cet endroit -- PAS un second AIAcconting, qui ne s'isole pas). La part infrastructure (voie,
 * ponts/tunnels, gares, depot) se deduit cote Python par soustraction (construction_cost -
 * vehicle_cost) -- pas la peine d'un panneau de plus pour une soustraction. Separer les deux
 * est necessaire pour amortir chacune sur son propre horizon : le materiel roulant a un max_age
 * connu du jeu, l'infrastructure n'a pas d'equivalent (voir docs/methode.md). Vaut 0 et se pose
 * quand meme (a 0) si l'echec survient avant l'achat de vehicules -- simplifie le parsing cote
 * Python (les trois panneaux coexistent toujours, ou aucun des trois). */
function TrainLineAI::_codeVehicleCost()
{
  return "TRLN|" + this.state.line_index + "|V" + this.state.vehicle_cost;
}

/* Features connues avant le pathfinder : populations courantes des deux villes et distance
 * euclidienne. CITY ne serialise pas la population dans OpenTTD 13.4. Avec deux populations a
 * six chiffres, "TRLN|99|P999999-999999|D999" fait 27 caracteres, sous la limite de 31.
 * Poste depuis _reportAll() (donc apres la premiere mutation de carte pour une ligne construite,
 * ou immediatement a l'echec sinon) -- PAS immediatement apres le choix de paire comme en v1, pour
 * ne pas ajouter de DoCommand avant la barriere. Voir le commentaire dans Start() a l'endroit ou
 * town_a_population/town_b_population sont ecrits dans this.state. */
function TrainLineAI::_codePairFeatures(populationA, populationB, distance)
{
  return "TRLN|" + this.state.line_index + "|P" + populationA + "-" + populationB + "|D" + distance;
}

/* Panneau de barriere : tick de la premiere commande de construction (le premier
 * DemolishTile) et M=barriere atteinte / O=preflight deja au-dela. Il est pose seulement apres
 * cette commande pour ne pas ajouter lui-meme un DoCommand avant le tick mesure. Meme avec un
 * line_index a deux chiffres et un tick a sept chiffres, "TRLN|99|B1234567|O" ne fait que 20
 * caracteres, bien sous la limite dure de 31 de AISign.BuildSign. */
function TrainLineAI::_codeBarrier()
{
  return "TRLN|" + this.state.line_index + "|B" + this.state.first_mutation_tick + "|" +
      (this.state.barrier_met ? "M" : "O");
}

/* Panneau distance Manhattan + cout estime : les deux connus des la paire choisie (avant le
 * pathfinder). Manhattan complete distance_straight (l'ecart entre les deux est un indice de
 * detour impose par le terrain) ; estimatedCost est deja calcule par l'IA pour filtrer les paires
 * inabordables (voir la boucle de construction de `pairs`), donc gratuit a exposer. Pire cas
 * mesure empiriquement (sweeps/debug_ai.py) : Manhattan <= ~212 (distance_straight <= 150 aux
 * bornes actuelles), cout estime <= disponibilites de depart (300000 mesure, banque+emprunt max).
 * "TRLN|99|M999|X999999" fait 21 caracteres, sous la limite de 31. */
function TrainLineAI::_codeDistCost()
{
  return "TRLN|" + this.state.line_index + "|M" + this.state.distance_manhattan +
      "|X" + this.state.estimated_cost;
}

/* Panneau specs moteur (vitesse, capacite WAGON, puissance) -- voir le commentaire sur
 * this.state.wagon_capacity dans Start() pour pourquoi c'est la capacite du wagon et non celle
 * (toujours -1) de la locomotive. Pire cas mesure empiriquement sur le jeu de moteurs 1970
 * (sweeps/debug_ai.py, stable sur 5 graines) : vitesse <= 160, capacite wagon <= 40, puissance
 * <= 3600 -- "TRLN|99|E999-999-9999" fait 22 caracteres, sous la limite de 31. */
function TrainLineAI::_codeEngineSpecs()
{
  return "TRLN|" + this.state.line_index + "|E" + this.state.engine_max_speed +
      "-" + this.state.wagon_capacity + "-" + this.state.engine_power;
}

/* Panneau cout moteur (prix d'achat, cout de roulement). Pire cas mesure empiriquement : prix
 * <= 30468, cout de roulement <= 2531 sur le jeu de moteurs 1970. "TRLN|99|F99999-9999" fait 20
 * caracteres, sous la limite de 31. */
function TrainLineAI::_codeEngineCost()
{
  return "TRLN|" + this.state.line_index + "|F" + this.state.engine_price +
      "-" + this.state.engine_running_cost;
}

/* Panneau distance gare<->centre-ville, pour les deux gares -- voir le commentaire sur
 * this.state.station_a_town_dist dans Start(). Pire cas : _makeStationPlans() cherche dans un
 * rayon 30 (Manhattan <= 60) avec une emprise de quai qui peut deporter l'ancre de jusqu'a
 * platformLength-1 tuiles de plus (<=6 avec wagons_per_train max=10), donc <= 66. "TRLN|99|SA99-SB99"
 * fait 17 caracteres au pire cas realiste ; largement sous 31 meme avec une marge a 3 chiffres. */
function TrainLineAI::_codeStationDist()
{
  return "TRLN|" + this.state.line_index + "|SA" + this.state.station_a_town_dist +
      "-SB" + this.state.station_b_town_dist;
}

/* Multiplicite des sorties locales de gare. `SP` est le nombre de plans retenus et `SR` le
 * dernier rayon effectivement visite par la boucle bornee de _makeStationPlans(). Ce dernier
 * distingue donc une ville qui atteint les 12 plans au rayon 3 d'une qui ne les atteint qu'au
 * rayon 28, sans elargir ni reparcourir la recherche. `SO` compte les sorties vers l'autre
 * centre-ville, `SN` est volontairement leur MIN (un seul bout bloque reste visible), et `RX`
 * est le MAX des rayons (le bout le plus difficile). Avec index=99, plans/outward<=12 et
 * rayon<=30 : "TRLN|99|SO12-12|SN12|RX30" fait 28 caracteres, sous la limite de 31. */
function TrainLineAI::_codeStationPlans()
{
  return "TRLN|" + this.state.line_index + "|SP" + this.state.station_plans_a +
      "-" + this.state.station_plans_b + "|SR" + this.state.station_radius_a +
      "-" + this.state.station_radius_b;
}

function TrainLineAI::_codeStationOutward()
{
  return "TRLN|" + this.state.line_index + "|SO" + this.state.station_outward_a +
      "-" + this.state.station_outward_b + "|SN" + this.state.station_outward_min +
      "|RX" + this.state.station_radius_max;
}

/* Panneaux production/acceptation de cargo dans la zone de chalandise de chaque gare -- un
 * panneau par gare (deux panneaux au lieu d'un pour rester sous la limite de 31 caracteres avec
 * de la marge). Pire cas mesure empiriquement pres d'un centre-ville a rayon 4 (sweeps/debug_ai.py,
 * 5 graines) : production <= 29, acceptation <= 251 -- "TRLN|99|GA9999-9999" fait 19 caracteres
 * meme avec une marge a 4 chiffres. */
function TrainLineAI::_codeCargoA()
{
  return "TRLN|" + this.state.line_index + "|GA" + this.state.station_a_cargo_prod +
      "-" + this.state.station_a_cargo_acc;
}

function TrainLineAI::_codeCargoB()
{
  return "TRLN|" + this.state.line_index + "|GB" + this.state.station_b_cargo_prod +
      "-" + this.state.station_b_cargo_acc;
}

/* Panneau terrain : denivele (max height - min height echantillonnes), tuiles d'eau, tuiles non
 * constructibles sur la ligne droite entre les deux centre-villes (PAS le vrai chemin du
 * pathfinder -- ca, c'est un resultat de construction, donc une fuite). Pire cas mesure
 * empiriquement (terrain plutot plat sur cette configuration de carte, denivele <= 7 observe) ;
 * eau/non-constructible bornes par distance_straight <= 150. "TRLN|99|H99|W999|U999" fait 22
 * caracteres, sous la limite de 31. */
function TrainLineAI::_codeTerrain()
{
  return "TRLN|" + this.state.line_index + "|H" + this.state.terrain_dh +
      "|W" + this.state.terrain_water + "|U" + this.state.terrain_unbuildable;
}

/* Panneau terrain du corridor direct centre-ville a centre-ville. Les H/W/U ci-dessus restent
 * la mesure du chemin retenu par le pathfinder ; ces trois valeurs-ci sont prises avant cet
 * appel et sont donc aussi presentes pour NOPATH/PATHLIM. */
function TrainLineAI::_codeCorridorTerrain()
{
  return "TRLN|" + this.state.line_index + "|CH" + this.state.corridor_dh +
      "|CW" + this.state.corridor_water + "|CU" + this.state.corridor_unbuildable;
}

/* Complements locaux du corridor direct. Panneau separe : ajouter ces deux valeurs a CH/CW/CU
 * depasserait les 31 caracteres acceptes par AISign.BuildSign dans le pire cas. */
function TrainLineAI::_codeCorridorTerrainRuns()
{
  return "TRLN|" + this.state.line_index + "|CR" + this.state.corridor_max_water_run +
      "|CS" + this.state.corridor_max_uphill_step;
}

/* Nombre de paires de villes candidates apres tous les filtres de carte. Il est emis meme si
 * pair_rank est hors plage, afin que PAIROOR expose le plafond propre a sa graine. */
function TrainLineAI::_codePairCount()
{
  return "TRLN|" + this.state.line_index + "|Q" + this.state.pair_count;
}

/* Reglages de preflight, en milliers. Avec line_index a deux chiffres, les bornes declarees
 * I<=300 et R<=60 donnent "TRLN|99|I300|R60" (17 caracteres), sous les 31 acceptes par
 * AISign.BuildSign. Les publier dans les panneaux rend chaque ligne de campagne tracable sans
 * ajouter de DoCommand avant la barriere. */
function TrainLineAI::_codePreflightBudget()
{
  return "TRLN|" + this.state.line_index + "|I" + this.state.pathfinder_iterations_k +
      "|R" + this.state.barrier_base_k;
}

/* Sondes A* tronquees : elles lisent l'etat de LA recherche en cours, sans jamais retirer un
 * noeud de la file. `N`=fermes, `F`=frontiere, `C`=cout g du meilleur noeud, `R`=distance de ce
 * noeud au centre de la ville destination, `G`=progres Manhattan depuis les centres des deux
 * villes, `Q`=C/G en milli-unites. Trois panneaux par instant restent sous les 31 caracteres,
 * meme pour line_index a quatre chiffres. -1 est le sentinel explicite pour une sonde non
 * atteinte (ou une frontiere vide), jamais une mesure a zero. */
function TrainLineAI::_codePathfinderProbeVolume(probe)
{
  return "TRLN|" + this.state.line_index + "|A" + probe.at + "|N" + probe.closed +
      "|F" + probe.frontier;
}

function TrainLineAI::_codePathfinderProbeDistance(probe)
{
  return "TRLN|" + this.state.line_index + "|A" + probe.at + "|C" + probe.cost +
      "|R" + probe.remaining;
}

function TrainLineAI::_codePathfinderProbeRatio(probe)
{
  return "TRLN|" + this.state.line_index + "|A" + probe.at + "|G" + probe.gained +
      "|Q" + probe.progress_ratio_ppm;
}

function TrainLineAI::_codePathfinderIterationsConsumed()
{
  return "TRLN|" + this.state.line_index + "|AP" + this.state.pathfinder_iterations_consumed;
}

/* Marques scratch compactes : meme granularite de 50 iterations que la mesure PATHLIM 300k,
 * plus le nombre de segments et de retours arriere pour expliquer le resultat sans toucher aux
 * fichiers de donnees de la campagne. */
function TrainLineAI::_codeSegmentedMeasure()
{
  /* Les noms complets depassent 31 caracteres dans un AISign. Un code d'un caractere conserve
   * le meme fait de mesure sans risquer qu'OpenTTD refuse silencieusement le panneau. */
  local stop = "X";
  if (this.state.pathfinder_stop == "found") stop = "F";
  else if (this.state.pathfinder_stop == "iteration_limit") stop = "L";
  else if (this.state.pathfinder_stop == "preflight_deadline") stop = "D";
  else if (this.state.pathfinder_stop == "open_empty") stop = "E";
  else if (this.state.pathfinder_stop == "no_progress") stop = "N";
  return "TPM|" + this.state.line_index + "|I" + this.state.pathfinder_iterations_consumed +
      "|K" + this.state.pathfinder_ticks + "|S" + stop;
}

function TrainLineAI::_codeSegmentedDetail()
{
  return "TSG|" + this.state.line_index + "|N" + this.state.segmented_segments +
      "|L" + this.state.segmented_local_choices + "|R" + this.state.segmented_backtracks;
}

/* Capture apres un FindPath(50) qui a retourne false : AyStar garde alors _open/_closed intacts.
 * Count() et Peek() de Queue.BinaryHeap v1 sont O(1); AIList.Count() est aussi O(1) dans l'API
 * OpenTTD. Surtout, Peek() ne devient jamais Pop(), donc la recherche suivante voit exactement
 * la meme frontiere. */
function TrainLineAI::_capturePathfinderProbe(pathfinder, destinationCenter, probe)
{
  local aystar = pathfinder._pathfinder;
  probe.iterations = this.state.pathfinder_iterations_consumed;
  probe.closed = aystar._closed == null ? -1 : aystar._closed.Count();
  probe.frontier = -1;
  probe.cost = -1;
  probe.remaining = -1;
  probe.gained = -1;
  probe.progress_ratio_ppm = -1;
  if (aystar._open == null) return;
  probe.frontier = aystar._open.Count();
  if (probe.frontier == 0) return;
  local best = aystar._open.Peek(); // Peek seulement : Pop() modifierait l'A*.
  if (best == null) return;
  probe.cost = best.GetCost();
  probe.remaining = AIMap.DistanceManhattan(best.GetTile(), destinationCenter);
  /* Meme reference de destination pour les trois instantanes. distance_manhattan est la distance
   * centre-ville A -> centre-ville B connue avant le pathfinder; G mesure donc le rapprochement
   * effectif du meilleur noeud vers le centre B. */
  probe.gained = this.state.distance_manhattan - probe.remaining;
  if (probe.gained > 0) {
    probe.progress_ratio_ppm = (probe.cost * 1000 / probe.gained).tointeger();
  }
}

/* Convertit une chaine AyStar en ordre de construction. Cette copie est necessaire parce qu'un
 * segment suivant repart d'un nouveau RailPathFinder : il ne doit jamais reutiliser la file du
 * segment precedent, dont les noeuds sont detruits a la fin de FindPath(). */
function TrainLineAI::_segmentTiles(node)
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

/* Squirrel 3.0 ne capture pas les locales englobantes dans les closures ici. Eviter clone() et
 * copier explicitement les tableaux rend aussi les checkpoints de retour arriere independants. */
function TrainLineAI::_copySegmentTiles(tiles)
{
  local copied = [];
  foreach (tile in tiles) copied.push(tile);
  return copied;
}

/* Teste, sans rien construire, les franchissements collineaires qui prolongent le meilleur noeud
 * de frontiere. RailPathFinder ne propose normalement que des longueurs <= 6; la resolution
 * locale essaie donc explicitement les longueurs 3..20, dans cet ordre, et garde seulement les
 * extremites qui rapprochent vraiment du but. AITestMode est volontairement dans chaque essai :
 * aucun plan retenu ne modifie la carte avant la barriere de construction. */
function TrainLineAI::_localStructureChoices(front, previous, destinationCenter)
{
  local choices = [];
  local distance = AIMap.DistanceManhattan(front, previous);
  if (distance <= 0) return choices;
  local step = (front - previous) / distance;
  local before = AIMap.DistanceManhattan(front, destinationCenter);
  local next = front + step;
  if (!AIMap.IsValidTile(next)) return choices;

  /* Un budget court n'implique pas a lui seul un obstacle. Avant de sonder 18 ponts couteux,
   * verifier que la voie peut continuer dans l'axe du meilleur noeud. La premiere version
   * faisait ces essais a CHAQUE front, ce qui consommait le temps de jeu avant _reportAll() sur
   * 1003/50 sans aucune exception Squirrel. */
  local canContinue = false;
  {
    local testMode = AITestMode();
    canContinue = AIRail.BuildRail(previous, front, next);
  }
  if (canContinue) return choices;

  for (local length = 3; length <= 20; length++) {
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
      this.state.segmented_bridge_tests++;
    }
  }

  /* Un tunnel ne choisit pas son autre bouche : OpenTTD la deduit du relief. On le teste donc
   * apres les ponts, tout en imposant le meme axe et la meme borne de longueur que les ponts. */
  local tunnelEnd = AITunnel.GetOtherTunnelEnd(front);
  if (AIMap.IsValidTile(tunnelEnd)) {
    local tunnelDistance = AIMap.DistanceManhattan(front, tunnelEnd);
    if (tunnelDistance >= 2 && tunnelDistance + 1 <= 20 &&
        (tunnelEnd - front) / tunnelDistance == step &&
        AIMap.DistanceManhattan(tunnelEnd, destinationCenter) < before) {
      local usable = false;
      {
        local testMode = AITestMode();
        usable = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, front);
      }
      if (usable) {
        choices.push({ to = tunnelEnd, kind = "tunnel", length = tunnelDistance + 1 });
        this.state.segmented_tunnel_tests++;
      }
    }
  }
  return choices;
}

/* Recherche segmentee scratch-only. Chaque A* vise toujours les quais finals, mais est arrete
 * apres 2 000 iterations. Son meilleur noeud devient le nouveau front. Lorsqu'un franchissement
 * local est possible, un checkpoint conserve les autres longueurs; un cul-de-sac (file vide)
 * reprend ainsi l'alternative precedente au lieu de figer un choix glouton. Le seul compteur
 * global est pathfinder_iterations_consumed, incremente exactement par les appels FindPath(50)
 * comme la production. */
function TrainLineAI::_segmentedPath(sources, goals, destinationCenter, deadlineTick)
{
  local activeSources = sources;
  local prefix = null;
  local checkpoints = [];
  local iterationLimit = this.state.pathfinder_iterations_k * 1000;
  local segmentLimit = 2000;

  while (this.state.pathfinder_iterations_consumed < iterationLimit &&
      AIController.GetTick() < deadlineTick) {
    this.state.segmented_segments++;
    local pathfinder = RailPathFinder();
    pathfinder.cost.max_cost = 200000;
    pathfinder.InitializePath(activeSources, goals);
    local path = false;
    local segmentUsed = 0;
    while (path == false && segmentUsed < segmentLimit &&
        this.state.pathfinder_iterations_consumed < iterationLimit &&
        AIController.GetTick() < deadlineTick) {
      path = pathfinder.FindPath(50);
      segmentUsed += 50;
      this.state.pathfinder_iterations_consumed += 50;
      this.Sleep(1);
    }

    if (path != false && path != null) {
      local tail = this._segmentTiles(path);
      if (prefix == null) prefix = tail;
      else for (local i = 2; i < tail.len(); i++) prefix.push(tail[i]);
      this.state.pathfinder_stop = "found";
      return prefix;
    }

    if (path == null) {
      /* Aucune suite depuis ce front : essayer la longueur suivante du dernier obstacle resolu. */
      local resumed = false;
      while (checkpoints.len() > 0 && !resumed) {
        local checkpoint = checkpoints[checkpoints.len() - 1];
        if (checkpoint.next < checkpoint.choices.len()) {
          local choice = checkpoint.choices[checkpoint.next];
          checkpoint.next++;
          prefix = this._copySegmentTiles(checkpoint.prefix);
          prefix.push(choice.to);
          activeSources = [[choice.to, checkpoint.front]];
          this.state.segmented_backtracks++;
          resumed = true;
        } else {
          checkpoints.pop();
        }
      }
      if (resumed) continue;
      this.state.pathfinder_stop = "open_empty";
      return "no_path_found";
    }

    /* Le budget court est atteint : Peek() lit le meilleur noeud sans retirer la frontiere. */
    local best = pathfinder._pathfinder._open == null ? null : pathfinder._pathfinder._open.Peek();
    if (best == null) {
      this.state.pathfinder_stop = "open_empty";
      return "no_path_found";
    }
    local tail = this._segmentTiles(best);
    if (tail.len() < 3) {
      this.state.pathfinder_stop = "no_progress";
      return "no_path_found";
    }
    if (prefix == null) prefix = tail;
    else for (local i = 2; i < tail.len(); i++) prefix.push(tail[i]);

    local front = prefix[prefix.len() - 1];
    local previous = prefix[prefix.len() - 2];
    local choices = this._localStructureChoices(front, previous, destinationCenter);
    if (choices.len() > 0) {
      local checkpoint = { prefix = this._copySegmentTiles(prefix), front = front,
          choices = choices, next = 1 };
      checkpoints.push(checkpoint);
      prefix.push(choices[0].to);
      activeSources = [[choices[0].to, front]];
      this.state.segmented_local_choices++;
    } else {
      activeSources = [[front, previous]];
    }
  }

  this.state.pathfinder_stop = AIController.GetTick() >= deadlineTick ?
      "preflight_deadline" : "iteration_limit";
  return "path_search_limit";
}

/* Echantillonne la ligne DROITE entre les deux centres-villes (pas le vrai chemin du pathfinder,
 * qui est un resultat -- voir docs/phase3_ml.md 3.2). Un point par tuile de distance_straight
 * (borne a [minDistance, maxDistance] = [20,150] par construction des paires) : cout pur en
 * opcodes Squirrel, aucun DoCommand, donc aucun cout de tick tant que ca reste sous le budget
 * d'opcodes du VM avant suspension forcee (~10000) -- d'ou un scan 1D le long de la droite plutot
 * qu'un balayage de zone 2D, qui couterait bien plus cher. Verifie empiriquement (smoke-test) que
 * le preflight ne s'allonge pas au point de repousser la barriere. */
function TrainLineAI::_scanTerrain(locA, locB, samples)
{
  local xA = AIMap.GetTileX(locA);
  local yA = AIMap.GetTileY(locA);
  local xB = AIMap.GetTileX(locB);
  local yB = AIMap.GetTileY(locB);
  local steps = samples < 1 ? 1 : samples;
  local maxH = null;
  local minH = null;
  local water = 0;
  local unbuildable = 0;
  local waterRun = 0;
  local maxWaterRun = 0;
  local lastSlopeSampleH = null;
  local maxUphillStep = 0;
  local lastTile = null;
  for (local i = 0; i <= steps; i++) {
    local t = i.tofloat() / steps.tofloat();
    local x = (xA + (xB - xA).tofloat() * t + 0.5).tointeger();
    local y = (yA + (yB - yA).tofloat() * t + 0.5).tointeger();
    local tile = AIMap.GetTileIndex(x, y);
    if (!AIMap.IsValidTile(tile) || tile == lastTile) continue;
    lastTile = tile;
    local tMax = AITile.GetMaxHeight(tile);
    local tMin = AITile.GetMinHeight(tile);
    if (maxH == null || tMax > maxH) maxH = tMax;
    if (minH == null || tMin < minH) minH = tMin;
    if (AITile.IsWaterTile(tile)) {
      water++;
      waterRun++;
      if (waterRun > maxWaterRun) maxWaterRun = waterRun;
    } else {
      waterRun = 0;
    }
    if (!AITile.IsBuildable(tile)) unbuildable++;

    /* Cette boucle est deja echantillonnee a une position par tuile. On reutilise ces memes
     * lectures de hauteur aux positions 0, 8, 16... et a l'arrivee : aucun second parcours.
     * Si `samples` est inferieur a 8, les deux extremites deviennent les deux points de mesure,
     * ce qui donne la montee reelle sur le court corridor au lieu d'un faux zero. */
    if (i % 8 == 0 || i == steps) {
      if (lastSlopeSampleH != null && tMax > lastSlopeSampleH) {
        local uphill = tMax - lastSlopeSampleH;
        if (uphill > maxUphillStep) maxUphillStep = uphill;
      }
      lastSlopeSampleH = tMax;
    }
  }
  return { dh = (maxH == null ? 0 : maxH - minH), water = water, unbuildable = unbuildable,
      max_water_run = maxWaterRun, max_uphill_step = maxUphillStep };
}

/* Meme mesure, mais sur les tuiles du chemin effectivement retenu. `tiles` est explicitement
 * passe en parametre : les closures Squirrel de cet environnement ne capturent pas les locales
 * englobantes. Les extremites de pont/tunnel font partie de la representation du pathfinder ;
 * le compteur mesure donc le trace que l'IA a effectivement retenu, pas le corridor direct. */
function TrainLineAI::_scanTerrainTiles(tiles)
{
  local maxH = null;
  local minH = null;
  local water = 0;
  local unbuildable = 0;
  local seen = {};
  foreach (tile in tiles) {
    if (!AIMap.IsValidTile(tile) || tile in seen) continue;
    seen[tile] <- true;
    local tMax = AITile.GetMaxHeight(tile);
    local tMin = AITile.GetMinHeight(tile);
    if (maxH == null || tMax > maxH) maxH = tMax;
    if (minH == null || tMin < minH) minH = tMin;
    if (AITile.IsWaterTile(tile)) water++;
    if (!AITile.IsBuildable(tile)) unbuildable++;
  }
  return { dh = (maxH == null ? 0 : maxH - minH), water = water, unbuildable = unbuildable };
}

function TrainLineAI::_reportAll()
{
  if (this.costs != null) this.state.construction_cost = this.costs.GetCosts();
  this._report(this._code());
  this._report(this._codePreflightBudget());
  this._report(this._codePathfinderIterationsConsumed());
  if (this.state.pathfinder_ticks != null && this.state.pathfinder_stop != null) {
    this._report(this._codeSegmentedMeasure());
    this._report(this._codeSegmentedDetail());
  }
  foreach (probe in this.state.pathfinder_probes) {
    this._report(this._codePathfinderProbeVolume(probe));
    this._report(this._codePathfinderProbeDistance(probe));
    this._report(this._codePathfinderProbeRatio(probe));
  }
  if (this.state.pair_count != null) this._report(this._codePairCount());
  if (this.state.town_a != null && this.state.town_b != null) {
    this._report(this._codeDetail());
    this._report(this._codeVehicleCost());
    /* Panneau population/distance -- deplace ici depuis un envoi immediat avant preflight (voir
     * le commentaire dans Start() a l'endroit ou town_a/town_b sont maintenant assignes) : meme
     * raison de cout de tick que les nouveaux panneaux ci-dessous. */
    this._report(this._codePairFeatures(this.state.town_a_population, this.state.town_b_population,
        this.state.distance_straight));
    this._report(this._codeDistCost());
    this._report(this._codeEngineSpecs());
    this._report(this._codeEngineCost());
    /* Mesure pure prise avant _preflightPair(), mais publication differee dans ce flux existant
     * pour ne pas ajouter de DoCommand avant la barriere. Contrairement aux H/W/U du trace
     * retenu, elle est disponible aussi pour NOPATH/PATHLIM. */
    this._report(this._codeCorridorTerrain());
    this._report(this._codeCorridorTerrainRuns());
    /* Ces deux panneaux sont poses seulement ici, dans le flux differe existant. Le booleen
     * distingue explicitement une recherche de plans jamais atteinte (panneaux absents) d'une
     * recherche executee qui a trouve 0 plan (SP0, rayon 30, sorties 0). Ils sont disponibles
     * avant le pathfinder et restent donc presents pour PATHLIM. */
    if (this.state.station_plan_metrics_ready) {
      this._report(this._codeStationPlans());
      this._report(this._codeStationOutward());
    }
    if (this.state.first_mutation_tick != null) this._report(this._codeBarrier());
    /* Ces quatre panneaux exigent un preflight reussi (plans de quai + chemin) : absents pour un
     * echec avant ce stade (NOPATH/PATHLIM/NOTILE), presents pour tout le reste (TRKFAIL/STNFAIL/
     * DEPFAIL/ORDFAIL/success/partial), exactement comme this.state.path_found. */
    if (this.state.path_found) {
      this._report(this._codeStationDist());
      this._report(this._codeCargoA());
      this._report(this._codeCargoB());
      this._report(this._codeTerrain());
    }
  }
}

function TrainLineAI::_fail(reason)
{
  this.state.stage = "failed";
  this.state.failure_reason = reason;
  this._reportAll();
  while (true) {
    this.Sleep(50);
  }
}

/* Detecte si une ville a deja une gare rail, quel que soit le proprietaire -- AIRail.IsRailStationTile
 * est une requete d'etat de tuile globale (non filtree par compagnie), deja utilisee deux fois plus
 * bas dans ce fichier pour le placement du depot (recherche "IsRailStationTile"). AIStationList()/
 * AISignList(), elles, sont filtrees sur la compagnie appelante -- inutilisables pour voir ce qu'une
 * AUTRE compagnie a construit dans la meme partie. Un scan de tuiles est donc la seule facon de
 * detecter une ville deja desservie par une AUTRE instance de TrainLineAI (voir contrainte villes
 * disjointes dans Start()). Limite connue et acceptee : centre sur AITown.GetLocation, pas sur les
 * tuiles reelles de la gare -- si deux villes candidates sont proches, la gare d'une ville C peut
 * apparaitre dans le rayon d'une ville B et la faire percevoir a tort comme deja desservie. */
function TrainLineAI::_isTownServed(townID, radius)
{
  local center = AITown.GetLocation(townID);
  for (local dx = -radius; dx <= radius; dx++) {
    for (local dy = -radius; dy <= radius; dy++) {
      local tile = center + AIMap.GetTileIndex(dx, dy);
      if (!AIMap.IsValidTile(tile)) continue;
      if (AIRail.IsRailStationTile(tile)) return true;
    }
  }
  return false;
}

function TrainLineAI::_makeStationPlans(center, otherCenter, radius, length, maxPlans)
{
  local plans = [];
  local reachedRadius = 0;
  local outward = 0;
  local towardOtherX = AIMap.GetTileX(otherCenter) - AIMap.GetTileX(center);
  local towardOtherY = AIMap.GetTileY(otherCenter) - AIMap.GetTileY(center);
  local axes = [
    [AIRail.RAILTRACK_NE_SW, AIMap.GetTileIndex(1, 0)],
    [AIRail.RAILTRACK_NW_SE, AIMap.GetTileIndex(0, 1)],
  ];
  for (local r = 0; r <= radius && plans.len() < maxPlans; r++) {
    reachedRadius = r;
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
              local plan = { anchor = anchor, station_exit = stationExit, lead = lead,
                  direction = axis[0], step = step };
              plans.push(plan);
              /* Orientation de sortie = lead - station_exit; direction vers l'autre ville =
               * otherCenter - center. Avec les differences de coordonnees de tuiles, compter
               * exactement si (lead.x-exit.x)*(other.x-center.x) +
               * (lead.y-exit.y)*(other.y-center.y) > 0. C'est execute au moment ou ce plan est
               * deja retenu : aucun second parcours de tuiles ou des plans. */
              local exitDX = AIMap.GetTileX(plan.lead) - AIMap.GetTileX(plan.station_exit);
              local exitDY = AIMap.GetTileY(plan.lead) - AIMap.GetTileY(plan.station_exit);
              if (exitDX * towardOtherX + exitDY * towardOtherY > 0) outward++;
              if (plans.len() >= maxPlans) break;
            }
          }
          if (plans.len() >= maxPlans) break;
        }
      }
    }
  }
  return { plans = plans, radius = reachedRadius, outward = outward };
}

/* Retourne soit une raison d'echec, soit le chemin et les plans de gare retenus. Les epreuves
 * sont volontairement sans effet sur la carte : elles permettent de passer a la paire suivante
 * avant d'avoir pose une gare ou un rail qu'il faudrait ensuite demolir.
 *
 * Une version precedente relancait un A* complet pour chacune des 24 combinaisons de quais. Sur
 * une paire non joignable, la meme grande region inaccessible etait alors exploree jusqu'a 24
 * fois, ce qui bloquait des parties entieres. RailPathFinder sait gerer nativement plusieurs
 * sources et buts : une seule recherche multi-source/multi-but couvre toutes les geometries.
 * `deadlineTick` reste une ceinture de securite entre deux appels FindPath ; il ne peut pas
 * interrompre un appel individuel pathologique, mais la multiplication par 24 est supprimee. */
function TrainLineAI::_preflightPair(townA, townB, platformLength, deadlineTick)
{
  local planDataA = this._makeStationPlans(AITown.GetLocation(townA), AITown.GetLocation(townB),
      30, platformLength, 12);
  local planDataB = this._makeStationPlans(AITown.GetLocation(townB), AITown.GetLocation(townA),
      30, platformLength, 12);
  local plansA = planDataA.plans;
  local plansB = planDataB.plans;
  /* Enregistrer immediatement apres les deux boucles, AVANT les sorties NOPATH/PATHLIM : zero
   * est une mesure reelle (aucun plan), tandis que null/absent signifie que ce stade n'a jamais
   * ete execute. */
  this.state.station_plan_metrics_ready = true;
  this.state.station_plans_a = plansA.len();
  this.state.station_plans_b = plansB.len();
  this.state.station_radius_a = planDataA.radius;
  this.state.station_radius_b = planDataB.radius;
  this.state.station_outward_a = planDataA.outward;
  this.state.station_outward_b = planDataB.outward;
  this.state.station_outward_min = planDataA.outward < planDataB.outward ?
      planDataA.outward : planDataB.outward;
  this.state.station_radius_max = planDataA.radius > planDataB.radius ?
      planDataA.radius : planDataB.radius;
  if (plansA.len() == 0 || plansB.len() == 0) return "no_buildable_tile_near_town";

  local sources = [];
  local goals = [];
  /* La bibliotheque construit la chaine source comme node[1] -> node[0], puis ajoute goal[1]
   * apres goal[0]. Le chemin reconstruit doit donc etre : sortieA -> leadA -> ... -> leadB ->
   * sortieB. `leadA` est le vrai depart de l'A*, avec `station_exit` comme case precedente. */
  foreach (plan in plansA) sources.push([plan.lead, plan.station_exit]);
  foreach (plan in plansB) goals.push([plan.lead, plan.station_exit]);

  /* Chaque segment repart d'une file A* neuve pour mesurer le cout de cette strategie. */
  local pathfinderStartTick = AIController.GetTick();
  local segmented = this._segmentedPath(sources, goals, AITown.GetLocation(townB), deadlineTick);
  this.state.pathfinder_ticks = AIController.GetTick() - pathfinderStartTick;
  if (typeof(segmented) == "string") return segmented;
  local simplifiedTiles = segmented;
  if (simplifiedTiles.len() < 3) return "no_path_found";

  local selectedPlanA = null;
  local selectedPlanB = null;
  foreach (plan in plansA) {
    if (plan.station_exit == simplifiedTiles[0]) { selectedPlanA = plan; break; }
  }
  foreach (plan in plansB) {
    if (plan.station_exit == simplifiedTiles[simplifiedTiles.len() - 1]) { selectedPlanB = plan; break; }
  }
  if (selectedPlanA == null || selectedPlanB == null) return "no_path_found";
  return { tiles = simplifiedTiles, plans_a = [selectedPlanA], plans_b = [selectedPlanB] };
}

function TrainLineAI::Start()
{
  this.state = {
    stage = "starting",
    line_index = null,
    stagger_slot = null,
    town_a = null,
    town_a_name = null,
    town_b = null,
    town_b_name = null,
    distance_straight = 0,
    distance_manhattan = 0,
    estimated_cost = 0,
    town_a_population = 0,
    town_b_population = 0,
    // Backlog d'enrichissement (docs/phase3_ml.md 3.2) -- captures pendant le preflight,
    // postees en differe depuis _reportAll(). Restent a leur valeur par defaut si le preflight
    // echoue avant le stade ou elles deviennent connues (voir gates dans _reportAll()).
    station_a_town_dist = 0,
    station_b_town_dist = 0,
    station_a_cargo_prod = 0,
    station_a_cargo_acc = 0,
    station_b_cargo_prod = 0,
    station_b_cargo_acc = 0,
    // null + ready=false = plan search never reached; ready=true permits literal zero plans.
    station_plan_metrics_ready = false,
    station_plans_a = null,
    station_plans_b = null,
    station_radius_a = null,
    station_radius_b = null,
    station_outward_a = null,
    station_outward_b = null,
    station_outward_min = null,
    station_radius_max = null,
    terrain_dh = 0,
    terrain_water = 0,
    terrain_unbuildable = 0,
    corridor_dh = 0,
    corridor_water = 0,
    corridor_unbuildable = 0,
    corridor_max_water_run = 0,
    corridor_max_uphill_step = 0,
    pair_count = null,
    engine_max_speed = 0,
    engine_power = 0,
    engine_price = 0,
    engine_running_cost = 0,
    wagon_capacity = 0,
    rail_type = null,
    path_found = false,
    path_length = 0, // diagnostic seulement -- NE PAS utiliser comme feature : resultat du
                      // pathfinder, pas connu avant tentative (fuite). Le pre-connu legitime est
                      // distance_straight (distance a vol d'oiseau entre les deux villes). Voir
                      // docs/methode.md.
    track_tiles_built = 0,
    track_tiles_failed = 0,
    station_a_tile = null,
    station_b_tile = null,
    depot_tile = null,
    engine_id = null,
    engine_name = null,
    cargo_id = null,
    requested_trains = null,
    wagons_per_train = null,
    pathfinder_iterations_k = null,
    barrier_base_k = null,
    // Scratch-only : compteur global comparable a la production et diagnostic de segmentation.
    pathfinder_ticks = null,
    pathfinder_stop = null,
    segmented_segments = 0,
    segmented_local_choices = 0,
    segmented_backtracks = 0,
    segmented_bridge_tests = 0,
    segmented_tunnel_tests = 0,
    // Etat des trois lectures A*; -1 = instant non atteint / valeur indisponible, jamais zero.
    pathfinder_iterations_consumed = 0,
    pathfinder_probes = [
      { at = 500, iterations = -1, closed = -1, frontier = -1, cost = -1, remaining = -1,
        gained = -1, progress_ratio_ppm = -1 },
      { at = 2000, iterations = -1, closed = -1, frontier = -1, cost = -1, remaining = -1,
        gained = -1, progress_ratio_ppm = -1 },
      { at = 5000, iterations = -1, closed = -1, frontier = -1, cost = -1, remaining = -1,
        gained = -1, progress_ratio_ppm = -1 },
    ],
    built_trains = 0,
    construction_cost = 0,
    vehicle_cost = 0, // sous-ensemble de construction_cost -- voir _codeVehicleCost()
    first_mutation_tick = null,
    barrier_met = false,
    failure_reason = null,
  };

  local setName = function() {
    local i = 1;
    local name = "TrainLineAI";
    while (!AICompany.SetName(name)) {
      name = "TrainLineAI #" + ++i;
    }
    return name;
  };
  AILog.Info("Chosen company name: " + setName());

  /* Emprunte le maximum des le premier tick, avant toute construction. Objectif : supprimer
   * le manque d'argent comme cause d'echec possible, pour qu'un echec ne puisse plus venir
   * que du terrain ou du pathfinder -- les deux causes qui donnaient la meme signature a zero
   * (0 construit) sont ainsi reduites a une seule. Le remboursement ne pollue pas la cible :
   * on mesure company_value, qui est net de l'emprunt (voir docs/methode.md). */
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());

  this.state.requested_trains = AIController.GetSetting("num_trains");
  this.state.wagons_per_train = AIController.GetSetting("wagons_per_train");
  this.state.line_index = AIController.GetSetting("line_index");
  this.state.stagger_slot = AIController.GetSetting("stagger_slot");
  this.state.pathfinder_iterations_k = AIController.GetSetting("pathfinder_iterations_k");
  this.state.barrier_base_k = AIController.GetSetting("barrier_base_k");

  /* Echelonnement des demarrages -- necessaire pour que la compagnie N voie les gares deja
   * posees par les compagnies 0..N-1 avant de choisir sa propre paire (contrainte villes
   * disjointes plus bas). stagger_slot est deliberement distinct de line_index : ce dernier est
   * seulement l'identifiant echoise dans les panneaux, et peut donc rester 0..99 dans une
   * campagne de parties isolees sans retarder chacune d'elles. La compagnie stagger_slot=0 ne
   * subit aucun delai : elle construit dans les memes conditions temporelles qu'en partie
   * isolee, ce qui garde ce point de reference comparable entre parties a N compagnies
   * differentes.
   * STAGGER_TICKS=6000 (~81 jours/compagnie) est une estimation de depart, pas encore confirmee
   * empiriquement -- voir docs/methode.md pour la bissection prevue via sweeps/debug_ai.py. */
  local STAGGER_TICKS = 6000;
  local staggerDelay = this.state.stagger_slot * STAGGER_TICKS;
  if (staggerDelay > 0) this.Sleep(staggerDelay);

  /* 1. Choisir un type de rail (le premier disponible) */
  local railTypes = AIRailTypeList();
  if (railTypes.IsEmpty()) this._fail("no_rail_type_available");
  local railType = railTypes.Begin();
  AIRail.SetCurrentRailType(railType);
  this.state.rail_type = railType;

  /* 2. Choisir la meilleure paire de villes. Plutot qu'un rang arbitraire dans la liste des
   * populations, le score favorise naturellement deux grandes villes proches :
   * population_A * population_B / distance. */
  local townList = AITownList();
  townList.Valuate(AITown.GetPopulation);
  local townCount = townList.Count();
  AILog.Info("Town count on this map: " + townCount);
  if (townCount < 2) this._fail("not_enough_towns");

  /* Seuil dur : le diagnostic Phase 0 (2026-08-26) observe une mediane ~700 dans la config
   * revisee, mais encore une queue importante sous 500. Garder 500 filtre les petites villes sans
   * jeter la majorite du pool; aucune paire sous ce seuil n'est plus acceptee en repli. */
  local minPopulation = 500;
  local minDistance = 20;
  local maxDistance = 150;
  local platformLengthForEstimate = (this.state.wagons_per_train + 2) / 2 + 1;
  local trackCost = AIRail.GetBuildCost(railType, AIRail.BT_TRACK);
  local stationCost = AIRail.GetBuildCost(railType, AIRail.BT_STATION);
  local depotCost = AIRail.GetBuildCost(railType, AIRail.BT_DEPOT);
  local availableMoney = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local candidates = [];
  foreach (town, population in townList) candidates.push(town);

  /* Contrainte villes disjointes (dure, pas un reglage) : une ville deja desservie par une
   * AUTRE compagnie de la meme partie (voir _isTownServed() plus haut) ne peut plus etre
   * choisie par celle-ci. Precalcule une seule fois par ville (pas par paire) -- un scan
   * rayon x candidates^2 serait sinon refait a chaque paire. DISJOINT_CHECK_RADIUS=40 (rayon 30
   * de _makeStationPlans + marge) est une estimation de depart, pas encore confirmee
   * empiriquement -- voir docs/methode.md. */
  local DISJOINT_CHECK_RADIUS = 40;
  local townServed = {};
  foreach (town in candidates) {
    townServed[town] <- this._isTownServed(town, DISJOINT_CHECK_RADIUS);
  }

  local pairs = [];
  local disjointSkipped = 0;
  local populationSkipped = 0;
  for (local i = 0; i < candidates.len() - 1; i++) {
    local candidateA = candidates[i];
    if (townServed[candidateA]) { disjointSkipped++; continue; }
    local locCandidateA = AITown.GetLocation(candidateA);
    local populationA = AITown.GetPopulation(candidateA);
    for (local j = i + 1; j < candidates.len(); j++) {
      local candidateB = candidates[j];
      if (townServed[candidateB]) { disjointSkipped++; continue; }
      local distance = sqrt(AIMap.DistanceSquare(locCandidateA, AITown.GetLocation(candidateB)).tofloat()).tointeger();
      if (distance < minDistance || distance > maxDistance) continue;

      /* Estimation volontairement prudente : deux fois le cout de voie droite couvre les
       * virages, le terrassement et une partie des ponts, puis on ajoute gares et depot. */
      local estimatedCost = (distance + 2) * trackCost * 2 +
          2 * platformLengthForEstimate * stationCost + depotCost;
      if (estimatedCost > availableMoney) continue;

      local populationB = AITown.GetPopulation(candidateB);
      if (populationA < minPopulation || populationB < minPopulation) {
        populationSkipped++;
        continue;
      }
      local score = populationA.tofloat() * populationB.tofloat() / distance.tofloat();
      /* estimated_cost est deja calcule ci-dessus pour le filtre d'abordabilite -- conserve sur
       * la paire pour pouvoir etre republie plus tard comme feature (voir _codeDistCost()) sans
       * le recalculer. */
      local pair = { town_a = candidateA, town_b = candidateB, score = score, estimated_cost = estimatedCost };
      pairs.push(pair);
    }
  }
  if (pairs.len() == 0) {
    if (populationSkipped > 0) this._fail("no_pair_meets_population_floor");
    if (disjointSkipped > 0) this._fail("no_disjoint_town_pair");
    this._fail("no_suitable_town_pair");
  }

  this.state.pair_count = pairs.len();

  /* Une paire bien notee peut etre bloquee par la topographie. La version precedente essayait
   * les paires dans l'ordre du score jusqu'a en trouver une viable (jusqu'a 12 essais) : un
   * echec de preflight etait alors masque par un repli automatique sur la paire suivante, et le
   * signal de constructibilite ne portait que sur "au moins une paire parmi les 12 meilleures
   * marche" -- aucun controle sur la difficulte reellement testee.
   *
   * On trie maintenant TOUTES les paires candidates par score decroissant et on prend
   * directement celle au rang `pair_rank` (0 = meilleur score -- la meme paire que l'ancienne
   * boucle essayait en premier, donc toujours faisable en pratique). Un seul preflight, sans
   * repli sur une autre paire : un echec au rang N est desormais un vrai point de donnee sur la
   * difficulte de ce rang plutot qu'une raison de le cacher. `pair_rank` expose ainsi un
   * gradient de difficulte controle en parametre d'IA, echantillonnable cote Python. */
  pairs.sort(function(a, b) {
    if (a.score > b.score) return -1;
    if (a.score < b.score) return 1;
    return 0;
  });
  local pairRank = AIController.GetSetting("pair_rank");
  if (pairRank >= pairs.len()) this._fail("pair_rank_out_of_range");
  local selectedPair = pairs[pairRank];
  local townA = selectedPair.town_a;
  local townB = selectedPair.town_b;
  local bestScore = selectedPair.score;
  local locA = AITown.GetLocation(townA);
  local locB = AITown.GetLocation(townB);
  this.lastKnownTile = locA;

  /* Toutes les features qui ne dependent que de la paire retenue (pas du pathfinding) sont
   * capturees ICI, tout de suite dans this.state -- population, distance (vol d'oiseau et
   * Manhattan), identifiants/noms de ville, cout estime. Rien n'est poste ici (aucun DoCommand,
   * donc aucun cout de tick) : la publication est differee dans _reportAll() (voir plus bas et le
   * panneau de barriere existant, qui suit deja ce patron). Ecrire ces champs AVANT l'appel a
   * _preflightPair() -- et non apres, comme le faisait la version precedente -- est deliberement
   * different de v1 : ca fait survivre ces features a un echec de preflight (NOPATH/PATHLIM), qui
   * est la plus grosse part de la classe negative (82% des echecs, voir docs/phase2_hurdle_dataset.md).
   * En v1, seul le panneau population contournait deja ce probleme en etant poste immediatement,
   * avant meme d'entrer dans cette fonction ; le placer dans _reportAll() sans avancer aussi
   * town_a/town_b aurait fait regresser sa disponibilite sur NOPATH/PATHLIM. */
  this.state.town_a = townA;
  this.state.town_a_name = AITown.GetName(townA);
  this.state.town_b = townB;
  this.state.town_b_name = AITown.GetName(townB);
  this.state.town_a_population = AITown.GetPopulation(townA);
  this.state.town_b_population = AITown.GetPopulation(townB);
  /* Distance a vol d'oiseau (euclidienne) entre les deux centre-villes -- connue avant tout
   * pathfinding, contrairement a path_length. C'est la feature de distance legitime (verifie
   * empiriquement que sqrt() et AIMap.DistanceSquare() sont bien disponibles cote Squirrel). */
  this.state.distance_straight = sqrt(AIMap.DistanceSquare(locA, locB).tofloat()).tointeger();
  this.state.distance_manhattan = AIMap.DistanceManhattan(locA, locB);
  this.state.estimated_cost = selectedPair.estimated_cost;

  /* Le corridor est echantillonne avant le pathfinder et stocke dans l'etat. Cette requete de
   * carte est pure : aucun panneau n'est encore pose, donc la barriere de premiere mutation ne
   * bouge pas. _reportAll() l'emettra au meme moment que les autres panneaux, y compris quand
   * _preflightPair() s'arrete ensuite sur PATHLIM. */
  local corridorTerrain = this._scanTerrain(locA, locB, this.state.distance_straight);
  this.state.corridor_dh = corridorTerrain.dh;
  this.state.corridor_water = corridorTerrain.water;
  this.state.corridor_unbuildable = corridorTerrain.unbuildable;
  this.state.corridor_max_water_run = corridorTerrain.max_water_run;
  this.state.corridor_max_uphill_step = corridorTerrain.max_uphill_step;

  /* Specs du moteur/wagon choisis -- lecture pure (AIEngineList/AIEngine.Get*, verifiees
   * empiriquement disponibles avec cette signature via sweeps/debug_ai.py), aucun DoCommand,
   * donc sans cout de tick. Le choix ne depend que de la date de partie, du cargo passager et de
   * engine_rank -- pas du resultat du preflight -- donc deja connu ici. Duplique volontairement
   * le meme calcul que l'etape 6 plus bas (qui achete reellement le moteur) plutot que de
   * restructurer le code existant : ca laisse l'ordre d'echec NOENG/ENGOOR de l'etape 6 intact.
   * Si aucun moteur ne correspond (rang hors plage), les champs restent a leur valeur initiale
   * (0) -- l'etape 6 produira alors le vrai echec ENGOOR/NOENG en temps voulu. */
  local earlyPassengerCargo = null;
  foreach (cargo, dummy in AICargoList()) {
    if (AICargo.GetTownEffect(cargo) == AICargo.TE_PASSENGERS) { earlyPassengerCargo = cargo; break; }
  }
  local earlyEngines = AIEngineList(AIVehicle.VT_RAIL);
  earlyEngines.Valuate(AIEngine.IsWagon);
  earlyEngines.KeepValue(0);
  earlyEngines.Valuate(AIEngine.IsBuildable);
  earlyEngines.KeepValue(1);
  earlyEngines.Valuate(AIEngine.GetMaxSpeed);
  earlyEngines.Sort(AIList.SORT_BY_VALUE, false);
  local earlyEngineRank = AIController.GetSetting("engine_rank");
  if (earlyEngineRank < earlyEngines.Count()) {
    local earlyEngineId = earlyEngines.Begin();
    for (local i = 0; i < earlyEngineRank; i++) earlyEngineId = earlyEngines.Next();
    this.state.engine_max_speed = AIEngine.GetMaxSpeed(earlyEngineId);
    this.state.engine_power = AIEngine.GetPower(earlyEngineId);
    this.state.engine_price = AIEngine.GetPrice(earlyEngineId);
    this.state.engine_running_cost = AIEngine.GetRunningCost(earlyEngineId);

    /* Capacite du WAGON, pas de la locomotive : AIEngine.GetCapacity() sur une locomotive rend
     * -1 (verifie empiriquement), seuls les wagons transportent du cargo dans ce depot (voir le
     * commentaire "Une locomotive ne transporte pas elle-meme..." plus bas). C'est la valeur dont
     * le cote Python a besoin pour calculer num_trains * wagons_per_train * capacite_wagon. */
    local earlyWagons = AIEngineList(AIVehicle.VT_RAIL);
    earlyWagons.Valuate(AIEngine.CanRefitCargo, earlyPassengerCargo);
    earlyWagons.KeepValue(1);
    earlyWagons.Valuate(AIEngine.IsBuildable);
    earlyWagons.KeepValue(1);
    earlyWagons.Valuate(AIEngine.IsWagon);
    earlyWagons.KeepValue(1);
    this.state.wagon_capacity = earlyWagons.IsEmpty() ? 0 : AIEngine.GetCapacity(earlyWagons.Begin());
  }

  this._report("TRLN|TRY|" + pairRank + "|T" + townA + "-" + townB);
  /* Budget de recherche (voir commentaire dans _preflightPair() pour le bug de fond) : 1500
   * jours (~74 ticks/jour), soit environ 40% d'une partie de 10 ans, laisse le reste de la
   * partie pour construire et faire rouler la ligne assez longtemps pour un signal de profit
   * exploitable, meme si le preflight epuise tout son budget. */
  local preflightDeadline = AIController.GetTick() + 1500 * 74;
  local selectedPreflight = this._preflightPair(townA, townB, platformLengthForEstimate,
      preflightDeadline);
  if (typeof(selectedPreflight) == "string") this._fail(selectedPreflight);

  this.lastKnownTile = locA;
  AILog.Info("Connecting " + AITown.GetName(townA) + " to " + AITown.GetName(townB) +
      " score=" + bestScore);

  /* 3. Planifier plusieurs sorties de gare valides AVANT le pathfinding. La version precedente
   * ne proposait qu'une orientation deduite du centre des villes. Si la case juste devant ce
   * quai etait occupee (arbre, route, maison, bord de carte), RailPathFinder ne pouvait meme
   * pas commencer et signalait NOPATH, alors qu'une sortie a 90 degres etait libre.
   *
   * Chaque plan contient une emprise complete de quai, plate et constructible, ainsi que sa
  * case de raccordement. Le chemin trouve choisira donc une vraie paire de gares constructible,
  * sans sacrifier l'alignement des quais avec leurs rails. */
  local platformLength = (this.state.wagons_per_train + 2) / 2 + 1;
  this.lastKnownTile = locA;
  local stationPlansA = selectedPreflight.plans_a;
  local stationPlansB = selectedPreflight.plans_b;
  if (stationPlansA.len() == 0 || stationPlansB.len() == 0) {
    this._fail("no_buildable_tile_near_town");
  }

  /* Reutiliser les cases validees durant la pre-verification empeche une seconde recherche,
   * ou une reconstruction differente, de produire NOPATH apres un TRY reussi. */
  local tiles = selectedPreflight.tiles;
  this.state.path_found = true;

  /* Features de gare/terrain -- connues des que le preflight a reussi (plans de quai retenus +
   * chemin), donc AVANT toute mutation de carte. Capturees ici dans this.state, mais POSTEES plus
   * tard (voir _reportAll(), gate sur this.state.path_found) : chaque panneau supplementaire ici
   * serait un DoCommand de plus avant la barriere, ce qui reduirait la marge de 1084 ticks
   * mesuree (voir docs/phase3_ml.md 3.0bis) -- meme raison que le panneau de barriere existant.
   * plans_a/plans_b sont des listes a un seul element (voir _preflightPair()) : c'est exactement
   * le plan qui sera construit plus bas. */
  local planA = stationPlansA[0];
  local planB = stationPlansB[0];
  this.state.station_a_town_dist = AIMap.DistanceManhattan(planA.anchor, locA);
  this.state.station_b_town_dist = AIMap.DistanceManhattan(planB.anchor, locB);

  /* Zone de chalandise : AITile.GetCargoProduction/GetCargoAcceptance(tile, cargo, width, height,
   * radius) prennent le coin de coordonnees minimales du rectangle -- verifie empiriquement que
   * `anchor` (pas `station_exit`) est toujours ce coin, puisque _makeStationPlans() construit
   * toujours les tuiles du quai comme anchor + step*i avec step un vecteur unitaire positif (donc
   * anchor est toujours le coin nord/ouest, quel que soit le signe utilise pour le placement).
   * CATCHMENT_RADIUS=4 : rayon de chalandise vanilla par defaut d'une gare ferroviaire (sans
   * newGRF de gares ni "improved catchment"), confirme par sweeps/debug_ai.py (production/
   * acceptation non nulles et plausibles autour d'un centre-ville avec ce rayon). */
  local CATCHMENT_RADIUS = 4;
  local widthA = (planA.direction == AIRail.RAILTRACK_NE_SW) ? platformLength : 1;
  local heightA = (planA.direction == AIRail.RAILTRACK_NE_SW) ? 1 : platformLength;
  local widthB = (planB.direction == AIRail.RAILTRACK_NE_SW) ? platformLength : 1;
  local heightB = (planB.direction == AIRail.RAILTRACK_NE_SW) ? 1 : platformLength;
  this.state.station_a_cargo_prod = AITile.GetCargoProduction(planA.anchor, earlyPassengerCargo, widthA, heightA, CATCHMENT_RADIUS);
  this.state.station_a_cargo_acc = AITile.GetCargoAcceptance(planA.anchor, earlyPassengerCargo, widthA, heightA, CATCHMENT_RADIUS);
  this.state.station_b_cargo_prod = AITile.GetCargoProduction(planB.anchor, earlyPassengerCargo, widthB, heightB, CATCHMENT_RADIUS);
  this.state.station_b_cargo_acc = AITile.GetCargoAcceptance(planB.anchor, earlyPassengerCargo, widthB, heightB, CATCHMENT_RADIUS);

  local terrain = this._scanTerrainTiles(tiles);
  this.state.terrain_dh = terrain.dh;
  this.state.terrain_water = terrain.water;
  this.state.terrain_unbuildable = terrain.unbuildable;

  /* Demarre la mesure du cout de construction ICI, apres le pathfinding, pas avant -- bug trouve
   * empiriquement : un echec no_path_found rapportait parfois un cout de plusieurs dizaines de
   * millions alors qu'aucune construction n'a lieu avant cet echec (aucune commande de jeu emise
   * pendant la recherche de chemin). RailPathFinder explore des candidats de pont/tunnel en
   * evaluant leur cout (voir AIBridgeList_Length/GetMaxSpeed plus bas, meme technique) -- tout
   * porte a croire que ces evaluations, faites en AITestMode par la librairie, se retrouvaient
   * comptees dans this.costs simplement parce qu'il etait deja ouvert (meme mecanisme que le
   * piege AIAccounting documente dans docs/methode.md : un accounting ouvert pendant qu'une
   * activite de cout se produit ailleurs en capte le cumul, imbrique ou non). Ouvrir this.costs
   * seulement une fois le chemin trouve evite toute contamination par l'exploration du
   * pathfinder -- tout ce qui suit (voie, ponts/tunnels, gares, depot, vehicules) est la seule
   * depense en capital reelle, a distinguer du profit d'exploitation des vehicules
   * (VEHS.profit_this_year, hors voie/gares/entretien -- voir docs/methode.md). */
  this.costs = AIAccounting();

  this.state.path_length = tiles.len();

  /* Le premier et le dernier noeud identifient sans ambiguite les deux plans retenus par le
   * pathfinder. On construit ensuite exactement ces quais, pas une orientation supposee. */
  local stationPlanA = null;
  local stationPlanB = null;
  foreach (plan in stationPlansA) {
    if (plan.station_exit == tiles[0]) { stationPlanA = plan; break; }
  }
  foreach (plan in stationPlansB) {
    if (plan.station_exit == tiles[tiles.len() - 1]) { stationPlanB = plan; break; }
  }
  if (stationPlanA == null || stationPlanB == null) this._fail("no_path_found");

  local stationAAnchor = stationPlanA.anchor;
  local stationAExit = stationPlanA.station_exit;
  local stationAStep = stationPlanA.step;
  local stationADirection = stationPlanA.direction;
  local stationBAnchor = stationPlanB.anchor;
  local stationBExit = stationPlanB.station_exit;
  local stationBStep = stationPlanB.step;
  local stationBDirection = stationPlanB.direction;

  /* Barriere de preflight : toutes les preparations (paire, plans de quais et chemin) sont
   * terminees, mais aucune tuile n'a encore ete modifiee. La cible est ABSOLUE dans le compteur
   * AI, tout en conservant l'ecart de STAGGER_TICKS entre compagnies : le slot N construit a
   * BARRIER_BASE + N*STAGGER_TICKS. Ainsi N-1 a au moins 6000-38 ticks pour poser ses gares
   * avant la selection/construction de N, donc _isTownServed() garde son ordre de visibilite.
   * Le budget A* et cette barriere DOIVENT bouger ensemble : une iteration coute environ 2700
   * opcodes pour un budget VM d'environ 10000/tick, soit 3,7 iterations/tick. Les 30000
   * iterations historiques prennent donc 7337 a 10519 ticks et saturent environ 96 % de
   * BARRIER_BASE=11000. Augmenter seulement le budget ferait passer barrier_flag a O et casserait
   * silencieusement la comparabilite des lignes (2000/2000 M dans la campagne v2). Diagnostic des
   * 9 pires PATHLIM charges en eau : tous franchissables, mais 41200 a 89350 iterations et jusqu'a
   * 27858 ticks; une campagne qui les vise doit donc employer environ 90000 iterations et une
   * barriere vers 33000. Les reglages sont en milliers : defauts 30/11 reproduisent exactement
   * les constantes historiques 30000/11000. */
  local barrierBase = this.state.barrier_base_k * 1000;
  local barrierTarget = barrierBase + this.state.stagger_slot * STAGGER_TICKS;
  local beforeBarrier = AIController.GetTick();
  this.state.barrier_met = beforeBarrier <= barrierTarget;
  if (beforeBarrier < barrierTarget) this.Sleep(barrierTarget - beforeBarrier);

  /* 4. Construire la voie. Triplets (prev, cur, next) comme l'exige AIRail.BuildRail ;
   * pont/tunnel quand deux tuiles consecutives ne sont pas adjacentes. */
  /* Les quais sont poses avant la voie. L'itineraire part de la sortie du quai A et se termine
   * sur la tuile juste devant le quai B. */
  this.state.first_mutation_tick = AIController.GetTick();
  for (local i = 0; i < platformLength; i++) {
    AITile.DemolishTile(stationAAnchor + stationAStep * i);
    AITile.DemolishTile(stationBAnchor + stationBStep * i);
  }
  local stationA_ok = AIRail.BuildRailStation(stationAAnchor, stationADirection, 1, platformLength, AIStation.STATION_NEW);
  local stationB_ok = AIRail.BuildRailStation(stationBAnchor, stationBDirection, 1, platformLength, AIStation.STATION_NEW);
  this.state.station_a_tile = stationA_ok ? stationAExit : null;
  this.state.station_b_tile = stationB_ok ? stationBExit : null;
  if (!stationA_ok || !stationB_ok) this._fail("station_build_failed");

  local built = 0;
  local failed = 0;
  if (tiles.len() < 3) this._fail("no_path_found");
  /* Les premiere et derniere cases sont les sorties des deux quais. La voie nouvelle est posee
   * uniquement sur les cases intermediaires, avec les quais comme voisins aux deux extremites. */
  for (local i = 1; i < tiles.len() - 1; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    local ok = false;

    if (prev == next) {
      /* Artefact connu du pathfinder quand plusieurs directions d'entree candidates sont
       * proposees (voir InitializePath) : le chemin fait un aller-retour sur une tuile.
       * Rien a construire ici, ce n'est pas un vrai changement de direction. */
      ok = true;
    } else if (AIMap.DistanceManhattan(prev, cur) > 1) {
      /* cur est l'autre bout d'un pont/tunnel commençant en prev : rien a construire ici,
       * c'est gere au pas precedent. */
      ok = true;
    } else if (AIMap.DistanceManhattan(cur, next) > 1) {
      /* next est de l'autre cote d'un pont/tunnel : le construire maintenant. */
      if (AITunnel.GetOtherTunnelEnd(cur) == next) {
        ok = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
      } else {
        local bridge_list = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
        bridge_list.Valuate(AIBridge.GetMaxSpeed);
        bridge_list.Sort(AIList.SORT_BY_VALUE, false);
        ok = !bridge_list.IsEmpty() && AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridge_list.Begin(), cur, next);
      }
    } else {
      ok = AIRail.BuildRail(prev, cur, next);
    }

    if (ok) built++; else { failed++; AILog.Error("Track fail at i=" + i + " prev=" + prev + " cur=" + cur + " next=" + next); }
  }
  this.state.track_tiles_built = built;
  this.state.track_tiles_failed = failed;

  local startNext = tiles[2];
  if (failed > 0 ||
      !AIRail.AreTilesConnected(stationAExit, tiles[1], startNext) ||
      !AIRail.AreTilesConnected(tiles[tiles.len() - 3], tiles[tiles.len() - 2], stationBExit)) {
    this._fail("track_build_failed");
  }

  /* 5. Construire le depot pres du depart. Les deux gares sont deja posees et raccordees. */

  /* Nous posons d'abord l'aiguillage, puis le batiment : BuildRailDepot() ne cree pas
   * lui-meme les rails de raccordement. Le controle de connectivite ci-dessous conserve la
   * ligne principale, y compris lorsque le raccordement est place apres un virage. */
  local depotOffsets = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
    AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1),
  ];
  local depotTile = null;
  /* tiles[0] est la sortie du quai A. On commence sur la premiere voie ordinaire : le quai reste
   * intact et l'aiguillage du depot ne se trouve pas dans la gare. */
  for (local anchorIndex = 1; anchorIndex < tiles.len() - 1 && depotTile == null; anchorIndex++) {
    local depotAnchor = tiles[anchorIndex];
    if (AIRail.IsRailStationTile(depotAnchor) || !AIRail.IsRailTile(depotAnchor)) continue;

    local stationSide = tiles[anchorIndex - 1]; // cote de la gare A
    local lineSide = tiles[anchorIndex + 1];    // cote de la gare B
    if (AIMap.DistanceManhattan(stationSide, depotAnchor) != 1 ||
        AIMap.DistanceManhattan(lineSide, depotAnchor) != 1) continue;

    /* Cette voie existait avant la pose du depot. La reposer est sans effet si elle est deja
     * presente et rend l'intention explicite : l'aiguillage doit conserver la ligne A <-> B. */
    AIRail.BuildRail(stationSide, depotAnchor, lineSide);
    if (!AIRail.AreTilesConnected(stationSide, depotAnchor, lineSide)) continue;

    foreach (offset in depotOffsets) {
      local candidate = depotAnchor + offset;
      if (!AIMap.IsValidTile(candidate)) continue;
      if (AIRail.IsRailStationTile(candidate) || AIRail.IsRailDepotTile(candidate)) continue;

      local onRoute = false;
      foreach (routeTile in tiles) {
        if (routeTile == candidate) { onRoute = true; break; }
      }
      if (onRoute) continue;

      /* La case est liberee, puis l'aiguillage est construit AVANT le depot. Ce dernier ne
       * peut etre construit de facon fiable que lorsque sa sortie a deja une voie en face. */
      AITile.DemolishTile(candidate);
      {
        local testMode = AITestMode();
        if (!AIRail.BuildRailDepot(candidate, depotAnchor)) continue;
      }
      AIRail.BuildRail(stationSide, depotAnchor, candidate);
      local depotToA = AIRail.AreTilesConnected(stationSide, depotAnchor, candidate);
      local aToB = AIRail.AreTilesConnected(stationSide, depotAnchor, lineSide);
      if (!depotToA || !aToB) {
        AIRail.RemoveRail(stationSide, depotAnchor, candidate);
        AIRail.BuildRail(stationSide, depotAnchor, lineSide);
        continue;
      }

      local builtDepot = AIRail.BuildRailDepot(candidate, depotAnchor);
      if (!builtDepot || AIRail.GetRailDepotFrontTile(candidate) != depotAnchor) {
        AILog.Warning("Could not build depot at " + candidate + "; trying another junction");
        if (builtDepot) AITile.DemolishTile(candidate);
        AIRail.RemoveRail(stationSide, depotAnchor, candidate);
        AIRail.BuildRail(stationSide, depotAnchor, lineSide);
        continue;
      }

      depotTile = candidate;
      AILog.Info("Connected depot " + depotTile + " through rail tile " + depotAnchor);
      break;
    }
  }
  this.state.depot_tile = depotTile;
  if (depotTile != null) this.lastKnownTile = depotTile;

  if (depotTile == null) this._fail("depot_build_failed");

  /* 6. Choisir un cargo passager et le meilleur moteur disponible pour ce cargo */
  local passengerCargo = null;
  foreach (cargo, dummy in AICargoList()) {
    if (AICargo.GetTownEffect(cargo) == AICargo.TE_PASSENGERS) {
      passengerCargo = cargo;
      break;
    }
  }
  this.state.cargo_id = passengerCargo;

  /* Une locomotive ne transporte pas elle-meme de passagers (seuls les wagons le font) :
   * pas de filtre CanRefitCargo ici, seulement IsWagon=0 pour ecarter les wagons. */
  local engines = AIEngineList(AIVehicle.VT_RAIL);
  engines.Valuate(AIEngine.IsWagon);
  engines.KeepValue(0);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  engines.Valuate(AIEngine.GetMaxSpeed);
  engines.Sort(AIList.SORT_BY_VALUE, false);

  local engineCount = engines.Count();
  if (engineCount == 0) this._fail("no_engine_available");
  local engineRank = AIController.GetSetting("engine_rank");
  if (engineRank >= engineCount) this._fail("engine_rank_out_of_range");
  local engineId = engines.Begin();
  for (local i = 0; i < engineRank; i++) engineId = engines.Next();
  this.state.engine_id = engineId;
  this.state.engine_name = AIEngine.GetName(engineId);
  AILog.Info("Chosen engine: " + this.state.engine_name);

  /* 7. Acheter les trains, chacun avec son nombre de wagons, et les mettre en service */
  local wagons = AIEngineList(AIVehicle.VT_RAIL);
  wagons.Valuate(AIEngine.CanRefitCargo, passengerCargo);
  wagons.KeepValue(1);
  wagons.Valuate(AIEngine.IsBuildable);
  wagons.KeepValue(1);
  wagons.Valuate(AIEngine.IsWagon);
  wagons.KeepValue(1);
  local wagonId = wagons.IsEmpty() ? null : wagons.Begin();

  /* Isole le cout des achats de vehicules de celui de l'infrastructure (voie/ponts/tunnels/
   * gares/depot, etapes 4-5) par difference sur this.costs, PAS par un second AIAccounting
   * imbrique : verifie empiriquement qu'un AIAccounting ouvert pendant qu'un autre est encore
   * en vie ne demarre PAS a zero -- il reflete le meme cumul depuis l'ouverture du premier
   * (deux segments de voie construits l'un apres l'autre, cout 90 puis +360 ; le second
   * AIAccounting, ouvert juste avant le second segment, affichait 450 -- le cumul total depuis
   * le premier -- pas 360, son propre cout isole). Piege reel, evite ici. Voir docs/methode.md. */
  local costBeforeVehicles = this.costs.GetCosts();
  local builtTrains = 0;
  for (local i = 0; i < this.state.requested_trains; i++) {
    local train = AIVehicle.BuildVehicle(depotTile, engineId);
    if (!AIVehicle.IsValidVehicle(train)) {
      AILog.Warning("Could not afford train " + (i + 1) + "/" + this.state.requested_trains);
      break;
    }
    if (wagonId != null) {
      for (local w = 0; w < this.state.wagons_per_train; w++) {
        local wagon = AIVehicle.BuildVehicle(depotTile, wagonId);
        if (AIVehicle.IsValidVehicle(wagon)) {
          AIVehicle.MoveWagon(wagon, 0, train, 0);
        }
      }
    }
    /* OF_FULL_LOAD_ANY sur les deux arrets (patron trAIns) : verifie empiriquement que ca charge
     * bien les wagons a plein (contrairement a OF_NONE, qui ne force aucune attente et repart
     * systematiquement a vide sur une ligne neuve a faible frequentation). Le blocage restant
     * (income toujours nul) n'est PAS un probleme de flags d'ordre -- teste et ecarte, y compris
     * le patron asymetrique d'AdmiralAI (FULL_LOAD_ANY a l'aller, UNLOAD|NO_LOAD au retour) : le
     * vrai probleme est que le train ne quitte jamais le voisinage immediat du depot (voir
     * docs/methode.md, bug 4 -- probablement le depot lui-meme, place sur une jonction sans
     * signal apres la correction du bug 2). */
    local orderA_ok = AIOrder.AppendOrder(train, stationAExit, AIOrder.OF_FULL_LOAD_ANY);
    local orderB_ok = AIOrder.AppendOrder(train, stationBExit, AIOrder.OF_FULL_LOAD_ANY);
    if (!orderA_ok || !orderB_ok || AIOrder.GetOrderCount(train) != 2) {
      AILog.Error("Train orders failed: A=" + orderA_ok + " B=" + orderB_ok +
          " count=" + AIOrder.GetOrderCount(train));
      this._fail("train_order_failed");
    }
    AIVehicle.StartStopVehicle(train);
    builtTrains++;
  }
  this.state.built_trains = builtTrains;
  this.state.vehicle_cost = this.costs.GetCosts() - costBeforeVehicles;
  this.state.stage = (builtTrains == this.state.requested_trains) ? "success" : "partial";
  this._reportAll();

  while (true) {
    this.Sleep(50);
  }
}

function TrainLineAI::Save()
{
  return this.state == null ? {} : this.state;
}

function TrainLineAI::Load(version, data)
{
}
