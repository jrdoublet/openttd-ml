import("pathfinder.rail", "RailPathFinder", 1);

/*
 * NOTE SUR Save() :
 * L'etat structure ci-dessous est ecrit pour documenter ce que l'IA a fait, et rester
 * disponible si vous inspectez le savegame par un autre moyen plus tard (ou une future
 * version d'OpenTTDLab qui exposerait les donnees AI). A la date d'ecriture (verifie
 * empiriquement), OpenTTDLab NE LIT PAS cette donnee : son parseur n'expose que l'echo
 * des reglages declares (chunk AIPL.settings), pas le contenu de Save(). Le vrai canal
 * exploitable aujourd'hui est le savegame lui-meme : chunks VEHS/STNN/DEPT/ORDR filtres
 * par owner, compares a AIPL.settings (demande vs construit).
 */

class TrainLineAI extends AIController
{
  state = null;
}

function TrainLineAI::_sleepForever()
{
  local reason = this.state.failure_reason == null ? "n/a" : this.state.failure_reason;
  AILog.Info("Stage=" + this.state.stage + " reason=" + reason);
  while (true) {
    this.Sleep(50);
  }
}

function TrainLineAI::Start()
{
  this.state = {
    stage = "starting",
    town_a = null,
    town_a_name = null,
    town_b = null,
    town_b_name = null,
    rail_type = null,
    path_found = false,
    path_length = 0,
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

  this.state.requested_trains = AIController.GetSetting("num_trains");
  this.state.wagons_per_train = AIController.GetSetting("wagons_per_train");

  /* 1. Choisir un type de rail (le premier disponible) */
  local railTypes = AIRailTypeList();
  if (railTypes.IsEmpty()) {
    this.state.stage = "failed";
    this.state.failure_reason = "no_rail_type_available";
    AILog.Error("No rail type available");
    this._sleepForever();
    return;
  }
  local railType = railTypes.Begin();
  AIRail.SetCurrentRailType(railType);
  this.state.rail_type = railType;

  /* 2. Choisir les deux villes les plus peuplees */
  local townList = AITownList();
  townList.Valuate(AITown.GetPopulation);
  townList.Sort(AIList.SORT_BY_VALUE, false);
  if (townList.Count() < 2) {
    this.state.stage = "failed";
    this.state.failure_reason = "not_enough_towns";
    AILog.Error("Not enough towns");
    this._sleepForever();
    return;
  }
  local townA = townList.Begin();
  local townB = townList.Next();
  this.state.town_a = townA;
  this.state.town_a_name = AITown.GetName(townA);
  this.state.town_b = townB;
  this.state.town_b_name = AITown.GetName(townB);
  AILog.Info("Connecting " + AITown.GetName(townA) + " to " + AITown.GetName(townB));

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
  if (tileA == null || tileB == null) {
    this.state.stage = "failed";
    this.state.failure_reason = "no_buildable_tile_near_town";
    AILog.Error("No buildable flat tile found near a town");
    this._sleepForever();
    return;
  }

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

  if (path == null || path == false) {
    this.state.stage = "failed";
    this.state.failure_reason = "no_path_found";
    AILog.Error("No rail path found between " + this.state.town_a_name + " and " + this.state.town_b_name);
    this._sleepForever();
    return;
  }
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

    if (ok) built++; else { failed++; AILog.Error("Track fail at i=" + i + " prev=" + prev + " cur=" + cur + " next=" + next + " d1=" + AIMap.DistanceManhattan(prev,cur) + " d2=" + AIMap.DistanceManhattan(cur,next)); }
  }
  this.state.track_tiles_built = built;
  this.state.track_tiles_failed = failed;

  if (failed > 0) {
    this.state.stage = "failed";
    this.state.failure_reason = "track_build_failed";
    AILog.Error("Track build failed on " + failed + " tile(s)");
    this._sleepForever();
    return;
  }

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
  if (!stationA_ok) AILog.Error("Station A failed at tile " + tiles[0] + ": " + AIError.GetLastErrorString());
  local stationB_ok = buildStation(tiles[tiles.len() - 1]);
  if (!stationB_ok) AILog.Error("Station B failed at tile " + tiles[tiles.len() - 1] + ": " + AIError.GetLastErrorString());
  this.state.station_a_tile = stationA_ok ? tiles[0] : null;
  this.state.station_b_tile = stationB_ok ? tiles[tiles.len() - 1] : null;

  if (!stationA_ok || !stationB_ok) {
    this.state.stage = "failed";
    this.state.failure_reason = "station_build_failed";
    AILog.Error("Station build failed");
    this._sleepForever();
    return;
  }

  local depotTile = null;
  foreach (offset in offsets) {
    local candidate = tiles[0] + offset;
    if (!AIMap.IsValidTile(candidate)) continue;
    AITile.DemolishTile(candidate);
    if (AIRail.BuildRailDepot(candidate, tiles[0])) {
      depotTile = candidate;
      break;
    } else {
      AILog.Error("Depot candidate " + candidate + " failed: " + AIError.GetLastErrorString());
    }
  }
  this.state.depot_tile = depotTile;

  if (depotTile == null) {
    this.state.stage = "failed";
    this.state.failure_reason = "depot_build_failed";
    AILog.Error("Depot build failed");
    this._sleepForever();
    return;
  }

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

  if (engines.IsEmpty()) {
    this.state.stage = "failed";
    this.state.failure_reason = "no_engine_available";
    AILog.Error("No suitable engine available");
    this._sleepForever();
    return;
  }
  local engineId = engines.Begin();
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
  AILog.Info("Built " + builtTrains + "/" + this.state.requested_trains + " trains");

  this._sleepForever();
}

function TrainLineAI::Save()
{
  return this.state == null ? {} : this.state;
}

function TrainLineAI::Load(version, data)
{
}
