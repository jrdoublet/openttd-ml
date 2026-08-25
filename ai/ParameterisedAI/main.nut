import("pathfinder.road", "RoadPathFinder", 4);

class ParameterisedAI extends AIController 
{
}

function ParameterisedAI::Start()
{
  local setName = function() {
      local i = 1
      local name = "ParameterisedAI"
      while (!AICompany.SetName(name)) {
        name = "ParameterisedAI #" + ++i
      }

      return name;
  }

  local findTownsToConnect = function()
  {
    // Connect the two towns with the highest population
    local townlist = AITownList();
    townlist.Valuate(AITown.GetPopulation);
    townlist.Sort(AIList.SORT_BY_VALUE, false);
    local townid_a = townlist.Begin();
    local townid_b = townlist.Next();

    return [townid_a, townid_b];
  }

  local findPathToConnect = function(start, end)
  {
    /* Tell OpenTTD we want to build normal road (no tram tracks). */
    AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);

    /* Create an instance of the pathfinder. */
    local pathfinder = RoadPathFinder();

    /* Set the cost for making a turn extreme high. */
    pathfinder.cost.turn = 5000;
    pathfinder.InitializePath([start], [end]);

    local path = false;
    while (path == false) {
      AILog.Info("Finding path... ")
      path = pathfinder.FindPath(100);
      this.Sleep(1);
    }

    return path
  }

  local getTiles = function(path)
  {
    while (path != null) {
      yield path.GetTile();
      path = path.GetParent();
    }
  }

  local getTilePairs = function(path)
  {
    while (path != null) {
      local par = path.GetParent();
      if (par != null) {
        yield [path.GetTile(), par.GetTile()];
      }
      path = par;
    }
  }

  local buildRoad = function(tilePairs) {
    local tileList = AITileList();
    foreach (tilePair in tilePairs) {
      local current = tilePair[0];
      local next = tilePair[1];
      tileList.AddTile(current);
      if (AIMap.DistanceManhattan(current, next) == 1 ) {
        if (!AIRoad.BuildRoad(current, next)) {
          /* An error occured while building a piece of road. TODO: handle it.
           * Note that is can also be the case that the road was already build. */
        }
      } else {
        /* Build a bridge or tunnel. */
        if (!AIBridge.IsBridgeTile(current) && !AITunnel.IsTunnelTile(current)) {
          /* If it was a road tile, demolish it first. Do this to work around expended roadbits. */
          if (AIRoad.IsRoadTile(current)) AITile.DemolishTile(current);
          if (AITunnel.GetOtherTunnelEnd(current) == next) {
            if (!AITunnel.BuildTunnel(AIVehicle.VT_ROAD, current)) {
              /* An error occured while building a tunnel. TODO: handle it. */
            }
          } else {
            local bridge_list = AIBridgeList_Length(AIMap.DistanceManhattan(current, next) + 1);
            bridge_list.Valuate(AIBridge.GetMaxSpeed);
            bridge_list.Sort(AIList.SORT_BY_VALUE, false);
            if (!AIBridge.BuildBridge(AIVehicle.VT_ROAD, bridge_list.Begin(), current, next)) {
              /* An error occured while building a bridge. TODO: handle it. */
            }
          }
        }
      }
    }
  }

  local buildAlong = function(tiles, buildFunc) {
    foreach (pathTileIndex in tiles) {
      local adjacentTiles = AITileList();
      adjacentTiles.AddTile(pathTileIndex - AIMap.GetTileIndex(1,0));
      adjacentTiles.AddTile(pathTileIndex - AIMap.GetTileIndex(0,1));
      adjacentTiles.AddTile(pathTileIndex - AIMap.GetTileIndex(-1,0));
      adjacentTiles.AddTile(pathTileIndex - AIMap.GetTileIndex(0,-1));

      foreach (index, value in adjacentTiles) {
        local built = buildFunc(index, pathTileIndex);
        if (built) {
          if (!AIRoad.BuildRoad(index, pathTileIndex)) {
          }
          return index;
        }
      }
    }
  }

  local reverse = function(gen) {
    local reversed = [];
    foreach (item in gen) {
      reversed.append(item);
    }
    reversed.reverse();
    return reversed;
  }

  local getPassengerCargo = function() {
    foreach (cargo, dummy in AICargoList()) {
      if (AICargo.GetTownEffect(cargo) == AICargo.TE_PASSENGERS) {
        return cargo;
      }
    }
  }

  local chooseBusEngine = function(passengerCargo) {
    local roadEngines = AIEngineList(AIVehicle.VT_ROAD);
    roadEngines.Valuate(AIEngine.CanRefitCargo, passengerCargo);
    roadEngines.KeepValue(1);
    roadEngines.Valuate(AIEngine.IsBuildable);
    roadEngines.KeepValue(1);
    roadEngines.Valuate(AIEngine.GetMaxSpeed);
    roadEngines.Sort(AIList.SORT_BY_VALUE, false);
    return roadEngines.Begin();
  }

  local name = setName();
  AILog.Info("Chosen company name: " + name);

  local townsToConnect = findTownsToConnect();
  AILog.Info("Going to connect " + AITown.GetName(townsToConnect[0]) + " to " + AITown.GetName(townsToConnect[1]));

  local path = findPathToConnect(AITown.GetLocation(townsToConnect[0]), AITown.GetLocation(townsToConnect[1])) 

  if (path == null) {
    AILog.Error("No path found");
  }

  /* If a path was found, build a road over it. */
  buildRoad(getTilePairs(path));
  AILog.Info("Done");

  // Build station as close as possible to the start of the path
  local buildRoadStation = function(tile, front) {
    return AIRoad.BuildRoadStation(tile, front, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW)
  }
  local startStationTile = buildAlong(getTiles(path), buildRoadStation);

  // Build station as close as possible to the end of the path
  local reversedTiles = reverse(getTiles(path));
  local endStationTile = buildAlong(reversedTiles, buildRoadStation);

  // Build depot as close as possible to the start of the path
  local buildRoadDepot = function(tile, front) {
    return AIRoad.BuildRoadDepot(tile, front);
  }
  local depotTile = buildAlong(getTiles(path), buildRoadDepot)

  // Find bus type to build
  local busEngine = chooseBusEngine(getPassengerCargo());
  AILog.Info("Have chosen bus " + AIEngine.GetName(busEngine));

  // Set the bus going between the stations
  local maximum_buses = AIController.GetSetting("maximum_buses");
  for (local i = 0 ; i < maximum_buses; i++) {
    local busVehicle = AIVehicle.BuildVehicle(depotTile, busEngine);
    AIOrder.AppendOrder(busVehicle, startStationTile, AIOrder.OF_NONE);
    AIOrder.AppendOrder(busVehicle, endStationTile, AIOrder.OF_NONE);
    AIVehicle.StartStopVehicle(busVehicle);
    AILog.Info("Have started bus");
  }

  // Inifinite loop so the AI doesn't register as exited
  while (true) {
    AILog.Info("Sleeping");
    this.Sleep(50)
  }
}

function ParameterisedAI::Save()
{
 return {};
}

function ParameterisedAI::Load(version, data)
{
}
