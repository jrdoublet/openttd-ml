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

function TrainLineAI::_reportAll()
{
  if (this.costs != null) this.state.construction_cost = this.costs.GetCosts();
  this._report(this._code());
  if (this.state.town_a != null && this.state.town_b != null) {
    this._report(this._codeDetail());
    this._report(this._codeVehicleCost());
    if (this.state.first_mutation_tick != null) this._report(this._codeBarrier());
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

function TrainLineAI::_makeStationPlans(center, radius, length, maxPlans)
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
  local plansA = this._makeStationPlans(AITown.GetLocation(townA), 30, platformLength, 12);
  local plansB = this._makeStationPlans(AITown.GetLocation(townB), 30, platformLength, 12);
  if (plansA.len() == 0 || plansB.len() == 0) return "no_buildable_tile_near_town";

  local sources = [];
  local goals = [];
  /* La bibliotheque construit la chaine source comme node[1] -> node[0], puis ajoute goal[1]
   * apres goal[0]. Le chemin reconstruit doit donc etre : sortieA -> leadA -> ... -> leadB ->
   * sortieB. `leadA` est le vrai depart de l'A*, avec `station_exit` comme case precedente. */
  foreach (plan in plansA) sources.push([plan.lead, plan.station_exit]);
  foreach (plan in plansB) goals.push([plan.lead, plan.station_exit]);

  local pathfinder = RailPathFinder();
  pathfinder.cost.max_cost = 200000;
  pathfinder.InitializePath(sources, goals);
  local path = false;
  local iterationsLeft = 30000;
  while (path == false && iterationsLeft > 0 && AIController.GetTick() < deadlineTick) {
    path = pathfinder.FindPath(50);
    iterationsLeft -= 50;
    this.Sleep(1);
  }
  if (path == false) return "path_search_limit";
  if (path == null) return "no_path_found";

  local tiles = [];
  local node = path;
  while (node != null) {
    tiles.push(node.GetTile());
    node = node.GetParent();
  }
  tiles.reverse();
  local simplifiedTiles = [];
  foreach (tile in tiles) {
    if (simplifiedTiles.len() >= 2 && simplifiedTiles[simplifiedTiles.len() - 2] == tile) {
      simplifiedTiles.pop();
      continue;
    }
    if (simplifiedTiles.len() == 0 || simplifiedTiles[simplifiedTiles.len() - 1] != tile) {
      simplifiedTiles.push(tile);
    }
  }
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
      local pair = { town_a = candidateA, town_b = candidateB, score = score };
      pairs.push(pair);
    }
  }
  if (pairs.len() == 0) {
    if (populationSkipped > 0) this._fail("no_pair_meets_population_floor");
    if (disjointSkipped > 0) this._fail("no_disjoint_town_pair");
    this._fail("no_suitable_town_pair");
  }

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
  this.lastKnownTile = AITown.GetLocation(townA);
  this._report("TRLN|TRY|" + pairRank + "|T" + townA + "-" + townB);
  /* Budget de recherche (voir commentaire dans _preflightPair() pour le bug de fond) : 1500
   * jours (~74 ticks/jour), soit environ 40% d'une partie de 10 ans, laisse le reste de la
   * partie pour construire et faire rouler la ligne assez longtemps pour un signal de profit
   * exploitable, meme si le preflight epuise tout son budget. */
  local preflightDeadline = AIController.GetTick() + 1500 * 74;
  local selectedPreflight = this._preflightPair(townA, townB, platformLengthForEstimate,
      preflightDeadline);
  if (typeof(selectedPreflight) == "string") this._fail(selectedPreflight);

  this.state.town_a = townA;
  this.state.town_a_name = AITown.GetName(townA);
  this.state.town_b = townB;
  this.state.town_b_name = AITown.GetName(townB);
  this.lastKnownTile = AITown.GetLocation(townA);
  AILog.Info("Connecting " + AITown.GetName(townA) + " to " + AITown.GetName(townB) +
      " score=" + bestScore);

  /* Distance a vol d'oiseau (euclidienne) entre les deux centre-villes -- connue avant tout
   * pathfinding, contrairement a path_length. C'est la feature de distance legitime (verifie
   * empiriquement que sqrt() et AIMap.DistanceSquare() sont bien disponibles cote Squirrel). */
  local locA = AITown.GetLocation(townA);
  local locB = AITown.GetLocation(townB);
  this.state.distance_straight = sqrt(AIMap.DistanceSquare(locA, locB).tofloat()).tointeger();

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
   * BARRIER_BASE=5000 est choisi sur la distribution 1970/256x256 de
   * sweeps/phase2_preflight_distribution.py (max observe 4397 au tick absolu, marge 603). Le
   * script de mesure cree une copie /tmp avec zero afin d'observer le preflight non masque. */
  local BARRIER_BASE = 5000;
  local barrierTarget = BARRIER_BASE + this.state.stagger_slot * STAGGER_TICKS;
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
