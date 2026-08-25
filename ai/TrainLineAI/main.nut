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
  town_rank_out_of_range = "TWNOOR",
  town_rank_same_town = "TWNDUP",
  no_buildable_tile_near_town = "NOTILE",
  no_path_found = "NOPATH",
  track_build_failed = "TRKFAIL",
  station_build_failed = "STNFAIL",
  depot_build_failed = "DEPFAIL",
  no_engine_available = "NOENG",
  engine_rank_out_of_range = "ENGOOR",
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
 * construction (AIAccounting, voir plus haut). Uniquement pose si les villes ont ete choisies --
 * absent pour les echecs qui precedent le choix des villes (no_rail_type_available,
 * not_enough_towns, town_rank_*). */
function TrainLineAI::_codeDetail()
{
  return "TRLN|" + this.state.line_index + "|T" + this.state.town_a + "-" + this.state.town_b +
      "|D" + this.state.distance_straight + "|C" + this.state.construction_cost;
}

function TrainLineAI::_reportAll()
{
  if (this.costs != null) this.state.construction_cost = this.costs.GetCosts();
  this._report(this._code());
  if (this.state.town_a != null && this.state.town_b != null) {
    this._report(this._codeDetail());
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

function TrainLineAI::Start()
{
  this.state = {
    stage = "starting",
    line_index = null,
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

  /* 1. Choisir un type de rail (le premier disponible) */
  local railTypes = AIRailTypeList();
  if (railTypes.IsEmpty()) this._fail("no_rail_type_available");
  local railType = railTypes.Begin();
  AIRail.SetCurrentRailType(railType);
  this.state.rail_type = railType;

  /* 2. Choisir deux villes par rang de population (0 = la plus peuplee). `number_towns` dans
   * openttd.cfg est une densite (2 = normale), pas un nombre de villes : logge une fois pour
   * borner les rangs valides sur cette carte (voir docs/methode.md). */
  local nth = function(list, rank) {
    local item = list.Begin();
    for (local i = 0; i < rank; i++) item = list.Next();
    return item;
  };

  local townList = AITownList();
  townList.Valuate(AITown.GetPopulation);
  townList.Sort(AIList.SORT_BY_VALUE, false);
  local townCount = townList.Count();
  AILog.Info("Town count on this map: " + townCount);
  if (townCount < 2) this._fail("not_enough_towns");

  local townARank = AIController.GetSetting("town_a_rank");
  local townBRank = AIController.GetSetting("town_b_rank");
  if (townARank >= townCount || townBRank >= townCount) this._fail("town_rank_out_of_range");
  if (townARank == townBRank) this._fail("town_rank_same_town");

  local townA = nth(townList, townARank);
  local townB = nth(townList, townBRank);
  this.state.town_a = townA;
  this.state.town_a_name = AITown.GetName(townA);
  this.state.town_b = townB;
  this.state.town_b_name = AITown.GetName(townB);
  this.lastKnownTile = AITown.GetLocation(townA);
  AILog.Info("Connecting " + AITown.GetName(townA) + " to " + AITown.GetName(townB));

  /* Distance a vol d'oiseau (euclidienne) entre les deux centre-villes -- connue avant tout
   * pathfinding, contrairement a path_length. C'est la feature de distance legitime (verifie
   * empiriquement que sqrt() et AIMap.DistanceSquare() sont bien disponibles cote Squirrel). */
  local locA = AITown.GetLocation(townA);
  local locB = AITown.GetLocation(townB);
  this.state.distance_straight = sqrt(AIMap.DistanceSquare(locA, locB).tofloat()).tointeger();

  /* Demarre la mesure du cout de construction ici : tout ce qui suit (voie, ponts/tunnels,
   * gares, depot, vehicules) est une depense en capital, a distinguer du profit d'exploitation
   * des vehicules (VEHS.profit_this_year, hors voie/gares/entretien -- voir docs/methode.md). */
  this.costs = AIAccounting();

  /* AITown.GetLocation() renvoie le centre-ville, occupe par des batiments : impossible d'y
   * construire du rail (contrairement a la route, qui peut se raccorder a la voirie
   * existante). On cherche la tuile constructible et plate la plus proche du centre-ville. */
  local findBuildableNear = function(center, maxRadius) {
    for (local r = 0; r <= maxRadius; r++) {
      for (local dx = -r; dx <= r; dx++) {
        for (local dy = -r; dy <= r; dy++) {
          if (abs(dx) != r && abs(dy) != r) continue; // contour du carre uniquement
          local t = center + AIMap.GetTileIndex(dx, dy);
          if (AIMap.IsValidTile(t) && AITile.IsBuildable(t) && AITile.GetSlope(t) == AITile.SLOPE_FLAT) {
            return t;
          }
        }
      }
    }
    return null;
  };

  local tileA = findBuildableNear(AITown.GetLocation(townA), 20);
  local tileB = findBuildableNear(AITown.GetLocation(townB), 20);
  if (tileA == null || tileB == null) this._fail("no_buildable_tile_near_town");
  this.lastKnownTile = tileA;

  /* 3. Chercher un chemin.
   * IMPORTANT : InitializePath attend des paires [tuile, tuile_precedente] pour etablir
   * une direction d'entree. Utiliser deux fois la meme tuile est degenere : le tout premier
   * pas du pathfinder tenterait de construire un rail dont l'origine ET le milieu sont la
   * meme tuile, ce qui echoue systematiquement (verifie en lisant le code source du
   * pathfinder). On propose donc les 4 directions d'entree possibles a chaque bout, et on
   * laisse le pathfinder choisir celle qui marche. */
  local offsets = [AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1),
                    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0)];
  local sources = [];
  local goals = [];
  foreach (offset in offsets) {
    if (AIMap.IsValidTile(tileA - offset)) sources.push([tileA, tileA - offset]);
    if (AIMap.IsValidTile(tileB - offset)) goals.push([tileB, tileB - offset]);
  }

  local pathfinder = RailPathFinder();
  pathfinder.cost.max_cost = 200000;
  pathfinder.InitializePath(sources, goals);

  local path = false;
  local iterations_left = 100000; // borne dure : n'attend pas indefiniment si aucun chemin n'existe
  while (path == false && iterations_left > 0) {
    path = pathfinder.FindPath(200);
    iterations_left -= 200;
    this.Sleep(1);
  }

  if (path == null || path == false) this._fail("no_path_found");
  this.state.path_found = true;

  /* Reconstitue la liste de tuiles, de tileA vers tileB */
  local tiles = [];
  local node = path;
  while (node != null) {
    tiles.push(node.GetTile());
    node = node.GetParent();
  }
  tiles.reverse();
  this.state.path_length = tiles.len();

  /* 4. Construire la voie. Triplets (prev, cur, next) comme l'exige AIRail.BuildRail ;
   * pont/tunnel quand deux tuiles consecutives ne sont pas adjacentes. */
  local built = 0;
  local failed = 0;
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

  if (failed > 0) this._fail("track_build_failed");

  /* 5. Construire une gare a chaque bout, un depot pres du depart */
  /* platform_length=1 : pas de garantie qu'un couloir de plusieurs tuiles soit degage
   * autour de la tuile choisie. Un train plus long que 1 case chargera moins bien
   * (limitation connue de ce squelette, pas un bug — a ameliorer si besoin). */
  local buildStation = function(tile) {
    /* BuildRailStation n'auto-nettoie pas la tuile (contrairement a BuildRail) : un arbre
     * ou autre debris suffit a la faire echouer avec ERR_AREA_NOT_CLEAR. */
    AITile.DemolishTile(tile);
    return AIRail.BuildRailStation(tile, AIRail.RAILTRACK_NE_SW, 1, 1, AIStation.STATION_NEW)
        || AIRail.BuildRailStation(tile, AIRail.RAILTRACK_NW_SE, 1, 1, AIStation.STATION_NEW);
  };

  local stationA_ok = buildStation(tiles[0]);
  local stationB_ok = buildStation(tiles[tiles.len() - 1]);
  this.state.station_a_tile = stationA_ok ? tiles[0] : null;
  this.state.station_b_tile = stationB_ok ? tiles[tiles.len() - 1] : null;

  if (!stationA_ok || !stationB_ok) this._fail("station_build_failed");

  local depotTile = null;
  foreach (offset in offsets) {
    local candidate = tiles[0] + offset;
    if (!AIMap.IsValidTile(candidate)) continue;
    AITile.DemolishTile(candidate);
    if (AIRail.BuildRailDepot(candidate, tiles[0])) {
      depotTile = candidate;
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
  local engineId = nth(engines, engineRank);
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
    AIOrder.AppendOrder(train, tiles[0], AIOrder.OF_NONE);
    AIOrder.AppendOrder(train, tiles[tiles.len() - 1], AIOrder.OF_NONE);
    AIVehicle.StartStopVehicle(train);
    builtTrains++;
  }
  this.state.built_trains = builtTrains;
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
