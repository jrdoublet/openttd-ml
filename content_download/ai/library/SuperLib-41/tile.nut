/*
 * This file is part of SuperLib, which is an AI Library for OpenTTD
 * Copyright (C) 2010  Zuu
 *
 * SuperLib is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License
 *
 * SuperLib is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with SuperLib; If not, see <http://www.gnu.org/licenses/> or
 * write to the Free Software Foundation, Inc., 51 Franklin Street,
 * Fifth Floor, Boston, MA 02110-1301 USA.
 *
 */

class _SuperLib_Tile
{
	// some functions that don't fit in the categories below:

	static function GetTileString(tile);
	static function GetTownTiles(town_id);

	/* Get a random tile on the map */
	static function GetRandomTile();

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Relation                                                        //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function IsStraight(tile1, tile2);
	static function GetTileRelative(relative_to_tile, delta_x, delta_y); // clamps the new coordinate to the map


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Neighbours                                                      //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Get the four neighbours in the main directions NW, SW, SE and NE */
	static function GetNeighbours4MainDir(tile_id);

	/* Get all eight neighbours */
	static function GetNeighbours8(tile_id);

	/* Returns true if any of the eight neighbours are buildable */
	static function IsAdjacent8ToBuildableTile(tile_id);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Tile rectangles                                                 //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	// finds max/min x/y and creates a new tile list with this rect size + grow_amount
	static function MakeTileRectAroundTile(center_tile, radius);

	static function GrowTileRect(tile_list, grow_amount);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Slope info                                                      //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Checks if the build on slope setting is on. If the setting name
	 * has changed it will crash your AI! This is would only happen if
	 * OpenTTD renames the setting.
	 */
	static function IsBuildOnSlopeEnabled();

	/* Returns true only if it is a pure NE / SE / SW / NW slope */
	static function IsDownSlope(tile_id, direction);
	static function IsUpSlope(tile_id, direction);

	/* Returns true either if it is a pure up/down slope, but also if
	 * building a road/rail in the given direction would give a down/up
	 * slope in the given direction. If game setting build_on_slopes is
	 * disabled then these functions functions exactly the same as
	 * IsDownSlope/IsUpSlope.
	 */
	static function IsBuildOnSlope_DownSlope(tile_id, direction);
	static function IsBuildOnSlope_UpSlope(tile_id, direction);

	/* Checks if the tile acts as a flat tile with respect to build on slopes */
	static function IsBuildOnSlope_Flat(tile_id);

	/* Checks if the tile acts as a flat tile with respect to build on slopes for building
	 * road/rail in given direction. It only supports main directions. */
	static function IsBuildOnSlope_FlatInDirection(tile_id, direction);

	/* Checks if the tile acts as a flat tile with respect to build on slopes for building
	 * a bridge in given direction. It only supports main directions. */
	static function IsBuildOnSlope_FlatForBridgeInDirection(tile_id, direction);

	/* Checks if the tile acts as a flat tile with respect to build on slopes for building
	 * terminus constructions in given direction. (eg. road stops, road depots, train depots)
	 * It only supports main directions. */
	static function IsBuildOnSlope_FlatForTerminusInDirection(tile_id, direction);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Tile info                                                       //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Check if there is a bridge that starts in bridge_search_direction
	 * from tile and goes from there back over the tile 'tile'. If so the
	 * function will return the start tile of the bridge. Otherwise -1.
	 */
	static function GetBridgeAboveStart(tile, bridge_search_direction);

	/*
	 * Returns an AIRoad.RoadVehicleType of the type that the road stop
	 * has or -1 if there is no road stop at the tile
	 */
	static function GetRoadStopType(tile);

	/*
	 * Returns the tile that is closest to tile and is a road tile.
	 * It takes a maximum radius. If it can't find any road tile within
	 * the radius, it will return null.
	 */
	static function FindClosestRoadTile(tile, max_radius);

	/*
	 * Is the tile a depot for vehicle_type
	 */
	static function IsDepotTile(tile, vehicle_type);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Tile walking                                                    //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Checks if it is possible to walk from one tile to another using only
	 * tiles for which the is_allowed_tile_function function returns true.
	 *
	 * is_allowed_tile_function is a function that takes one argument,
	 * a tile index.
	 *
	 * The algorithm used is not meant to walk long distances or complex
	 * areas.
	 *
	 * Example:
	 *   CanWalk4ToTile(a, b, AIMarine.IsCanalTile); // will check if there is a canal from a to b
	 */

	/* walks with 4 main directions as neighbours */
	static function CanWalk4ToTile(from_tile, to_tile, is_allowed_tile_function);

	/* walks with 8 neighbours */
	static function CanWalk8ToTile(from_tile, to_tile, is_allowed_tile_function);

	/*
	 * This function takes an additional parameter neighbours_function which
	 * should be a function that takes a tile id and returns an AIList with
	 * tiles that are neighbours to the tile.
	 */
	static function CanWalkToTile(from_tile, to_tile, is_allowed_tile_function, neighbours_function);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Landscaping                                                     //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function CostToClearTiles(tile_list);
	static function CostToFlattern(top_left_tile, width, height);
	static function FlatternRect(top_left_tile, width, height);
	static function IsTileRectBuildableAndFlat(top_left_tile, width, height);
}

function _SuperLib_Tile::GetTileString(tile)
{
	return "" + AIMap.GetTileX(tile) + ", " + AIMap.GetTileY(tile);
}

function _SuperLib_Tile::GetTownTiles(town_id)
{
	local town_tiles = AITileList();
	local town_tile = AITown.GetLocation(town_id);
	local radius = 20 + _SuperLib_Helper.Max(0, AITown.GetPopulation(town_id) / 1000);

	local top_left = _SuperLib_Tile.GetTileRelative(town_tile, -radius, -radius);
	local bottom_right = _SuperLib_Tile.GetTileRelative(town_tile, radius, radius);

	town_tiles.AddRectangle(_SuperLib_Tile.GetTileRelative(town_tile, -radius, -radius), _SuperLib_Tile.GetTileRelative(town_tile, radius, radius));

	return town_tiles;
}

function _SuperLib_Tile::GetRandomTile()
{
	return AIMap.GetTileIndex(
			AIBase.RandRange(AIMap.GetMapSizeX()),
			AIBase.RandRange(AIMap.GetMapSizeY())
	);
}

function _SuperLib_Tile::IsStraight(tile1, tile2)
{
	return AIMap.GetTileX(tile1) == AIMap.GetTileX(tile2) ||
			AIMap.GetTileY(tile1) == AIMap.GetTileY(tile2);
}

function _SuperLib_Tile::GetTileRelative(relative_to_tile, delta_x, delta_y)
{
	local tile_x = AIMap.GetTileX(relative_to_tile);
	local tile_y = AIMap.GetTileY(relative_to_tile);

	local new_x = _SuperLib_Helper.Clamp(tile_x + delta_x, 1, AIMap.GetMapSizeX() - 2);
	local new_y = _SuperLib_Helper.Clamp(tile_y + delta_y, 1, AIMap.GetMapSizeY() - 2);

	return AIMap.GetTileIndex(new_x, new_y);
}

function _SuperLib_Tile::GetNeighbours4MainDir(tile_id)
{
	local list = AIList();

	if(!AIMap.IsValidTile(tile_id))
		return list;

	local tile_x = AIMap.GetTileX(tile_id);
	local tile_y = AIMap.GetTileY(tile_id);

	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_NE), _SuperLib_Direction.DIR_NE);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_SE), _SuperLib_Direction.DIR_SE);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_SW), _SuperLib_Direction.DIR_SW);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_NW), _SuperLib_Direction.DIR_NW);

	return list;
}

function _SuperLib_Tile::GetNeighbours8(tile_id)
{
	local list = AIList();

	if(!AIMap.IsValidTile(tile_id))
		return list;

	local tile_x = AIMap.GetTileX(tile_id);
	local tile_y = AIMap.GetTileY(tile_id);

	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_N), _SuperLib_Direction.DIR_N);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_E), _SuperLib_Direction.DIR_E);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_S), _SuperLib_Direction.DIR_S);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_W), _SuperLib_Direction.DIR_W);

	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_NE), _SuperLib_Direction.DIR_NE);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_SE), _SuperLib_Direction.DIR_SE);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_SW), _SuperLib_Direction.DIR_SW);
	list.AddItem(_SuperLib_Direction.GetAdjacentTileInDirection(tile_id, _SuperLib_Direction.DIR_NW), _SuperLib_Direction.DIR_NW);

	return list;
}

function _SuperLib_Tile::IsAdjacent8ToBuildableTile(tile_id)
{
	local neighbours = GetNeighbours8(tile_id);

	neighbours.Valuate(AITile.IsBuildable);
	neighbours.KeepValue(1);

	return !neighbours.IsEmpty();
}

function _SuperLib_Tile::MakeTileRectAroundTile(center_tile, radius)
{
	local tile_x = AIMap.GetTileX(center_tile);
	local tile_y = AIMap.GetTileY(center_tile);

	local x_min = _SuperLib_Helper.Clamp(tile_x - radius, 1, AIMap.GetMapSizeX() - 2);
	local x_max = _SuperLib_Helper.Clamp(tile_x + radius, 1, AIMap.GetMapSizeX() - 2);
	local y_min = _SuperLib_Helper.Clamp(tile_y - radius, 1, AIMap.GetMapSizeY() - 2);
	local y_max = _SuperLib_Helper.Clamp(tile_y + radius, 1, AIMap.GetMapSizeY() - 2);

	local list = AITileList();
	list.AddRectangle( AIMap.GetTileIndex(x_min, y_min), AIMap.GetTileIndex(x_max, y_max) );

	return list;
}

function _SuperLib_Tile::GrowTileRect(tile_list, grow_amount)
{
	local min_x = AIMap.GetMapSizeX(), min_y = AIMap.GetMapSizeY(), max_x = 0, max_y = 0;

	foreach(tile, _ in tile_list)
	{
		local x = AIMap.GetTileX(tile);
		local y = AIMap.GetTileY(tile);

		if(x < min_x) min_x = x;
		if(y < min_y) min_y = y;
		if(x > max_x) max_x = x;
		if(y > max_y) max_y = y;
	}

	local new_tile_list = AITileList();

	// Create the x0,y0 and x1,y1 coordinates for the grown rectangle clamped to the map size (minus a 1 tile border to fully support non-water map borders)
	local x0 = _SuperLib_Helper.Max(1, min_x - grow_amount);
	local y0 = _SuperLib_Helper.Max(1, min_y - grow_amount);
	local x1 = _SuperLib_Helper.Min(AIMap.GetMapSizeX() - 2, max_x + grow_amount);
	local y1 = _SuperLib_Helper.Min(AIMap.GetMapSizeY() - 2, max_y + grow_amount);

	new_tile_list.AddRectangle(AIMap.GetTileIndex(x0, y0), AIMap.GetTileIndex(x1, y1));
	return new_tile_list;
}

function _SuperLib_Tile::IsBuildOnSlopeEnabled()
{
	if (!AIGameSettings.IsValid("build_on_slopes"))
	{
		// This error is too important to risk getting suppressed by the log system, therefore
		// AILog is used directly.
		AILog.Error("Game setting \"build_on_slopes\" is not valid anymore!");
		KABOOOOOOOM_game_setting_is_not_valid_anymore // Make sure this error is found!
	}

	return AIGameSettings.GetValue("build_on_slopes") != false;
}

function _SuperLib_Tile::IsDownSlope(tile_id, direction)
{
	local opposite_dir =  _SuperLib_Direction.TurnDirClockwise45Deg(direction, 4);
	return _SuperLib_Tile.IsUpSlope(tile_id, opposite_dir);
}

function _SuperLib_Tile::IsUpSlope(tile_id, direction)
{
	local slope = AITile.GetSlope(tile_id);

	switch(direction)
	{
		case _SuperLib_Direction.DIR_NE:
			return slope == AITile.SLOPE_NE; // Has N & E corners raised

		case _SuperLib_Direction.DIR_SE:
			return slope == AITile.SLOPE_SE;

		case _SuperLib_Direction.DIR_SW:
			return slope == AITile.SLOPE_SW;

		case _SuperLib_Direction.DIR_NW:
			return slope == AITile.SLOPE_NW;

		default:
			return false;
	}

	return false;
}

function _SuperLib_Tile::IsBuildOnSlope_DownSlope(tile_id, direction)
{
	local opposite_dir = _SuperLib_Direction.TurnDirClockwise45Deg(direction, 4);
	return _SuperLib_Tile.IsBuildOnSlope_UpSlope(tile_id, opposite_dir);
}

function _SuperLib_Tile::IsBuildOnSlope_UpSlope(tile_id, direction)
{
	// If build on slopes is disabled, then call IsUpSlope instead
	if (!_SuperLib_Tile.IsBuildOnSlopeEnabled())
	{
		return _SuperLib_Tile.IsUpSlope(tile_id, direction);
	}

	local slope = AITile.GetSlope(tile_id);

	switch(direction)
	{
		case _SuperLib_Direction.DIR_NE:
			return ((slope & AITile.SLOPE_N) != 0x00 || (slope & AITile.SLOPE_E) != 0x00) && // must have either N or E tile raised
					((slope & AITile.SLOPE_S) == 0x00 && (slope & AITile.SLOPE_W) == 0x00); // and neither of S or W

		case _SuperLib_Direction.DIR_SE:
			return ((slope & AITile.SLOPE_S) != 0x00 || (slope & AITile.SLOPE_E) != 0x00) &&
					((slope & AITile.SLOPE_N) == 0x00 && (slope & AITile.SLOPE_W) == 0x00);

		case _SuperLib_Direction.DIR_SW:
			return ((slope & AITile.SLOPE_S) != 0x00 || (slope & AITile.SLOPE_W) != 0x00) &&
					((slope & AITile.SLOPE_N) == 0x00 && (slope & AITile.SLOPE_E) == 0x00);

		case _SuperLib_Direction.DIR_NW:
			return ((slope & AITile.SLOPE_N) != 0x00 || (slope & AITile.SLOPE_W) != 0x00) &&
					((slope & AITile.SLOPE_S) == 0x00 && (slope & AITile.SLOPE_E) == 0x00);

		default:
			return false;
	}

	return false;
}

function _SuperLib_Tile::IsBuildOnSlope_Flat(tile_id)
{
	local slope = AITile.GetSlope(tile_id);

	if (slope == AITile.SLOPE_FLAT) return true;

	// Only accept three raised corner tiles if build on slope is enabled
	if (!_SuperLib_Tile.IsBuildOnSlopeEnabled())
	{
		return false;
	}

	// check for steep slopes as they can otherwise give false positives in the check below
	if(AITile.IsSteepSlope(slope)) return false;

	// If two opposite corners are raised -> return true, else false
	return ((slope & AITile.SLOPE_N) != 0x00 && (slope & AITile.SLOPE_S) != 0x00) ||
			((slope & AITile.SLOPE_E) != 0x00 && (slope & AITile.SLOPE_W) != 0x00);

}

function _SuperLib_Tile::IsBuildOnSlope_FlatInDirection(tile_id, direction)
{
	// Backward compatibility
	return _SuperLib_Tile.IsBuildOnSlope_FlatForBridgeInDirection(tile_id, direction);
}

function _SuperLib_Tile::IsBuildOnSlope_FlatForTerminusInDirection(tile_id, direction)
{
	local slope = AITile.GetSlope(tile_id);

	if (slope == AITile.SLOPE_FLAT) return true;

	// Only accept three raised corner tiles if build on slope is enabled
	if (!_SuperLib_Tile.IsBuildOnSlopeEnabled())
	{
		return false;
	}

	// Check if at least two opposite corners are raised
	if (_SuperLib_Tile.IsBuildOnSlope_Flat(tile_id))
		return true;

	// If a single slope is raised, then check if the direction is so that the entry to the terminus
	// construction is facing one of the half-raised sides.
	if ((slope & AITile.SLOPE_N) != 0)
		return direction == _SuperLib_Direction.DIR_NE || direction == _SuperLib_Direction.DIR_NW;

	if ((slope & AITile.SLOPE_E) != 0)
		return direction == _SuperLib_Direction.DIR_NE || direction == _SuperLib_Direction.DIR_SE;

	if ((slope & AITile.SLOPE_S) != 0)
		return direction == _SuperLib_Direction.DIR_SE || direction == _SuperLib_Direction.DIR_SW;

	if ((slope & AITile.SLOPE_W) != 0)
		return direction == _SuperLib_Direction.DIR_SW || direction == _SuperLib_Direction.DIR_NW;

	return false;
}

function _SuperLib_Tile::IsBuildOnSlope_FlatForBridgeInDirection(tile_id, direction)
{
	local slope = AITile.GetSlope(tile_id);

	if (slope == AITile.SLOPE_FLAT) return true;

	// Only accept three raised corner tiles if build on slope is enabled
	if (!_SuperLib_Tile.IsBuildOnSlopeEnabled())
	{
		return false;
	}

	// Check if at least two oposite corners are raised
	if (_SuperLib_Tile.IsBuildOnSlope_Flat(tile_id))
		return true;

	if (direction == _SuperLib_Direction.DIR_NE || direction == _SuperLib_Direction.DIR_SW)
	{
		// If going in NE/SW direction ( / ): check for slopes in NW/SE direction
		return (slope == AITile.SLOPE_NW || slope == AITile.SLOPE_SE)
	}
	else if (direction == _SuperLib_Direction.DIR_NW || direction == _SuperLib_Direction.DIR_SE)
	{
		// If going in NW/SE direction ( / ): check for slopes in NE/SW direction
		return (slope == AITile.SLOPE_NE || slope == AITile.SLOPE_SW)
	}

	// Bad direction parameter value
	return false;
}

function _SuperLib_Tile::GetBridgeAboveStart(tile, bridge_search_direction)
{
	if (!_SuperLib_Direction.IsMainDir(bridge_search_direction))
	{
		_SuperLib_Log.Error("Tile::GetBridgeAboveStart(tile, bridge_search_direction) was called with a non-main direction", _SuperLib_Log.LVL_INFO);
		return -1;
	}

	local max_height = AITile.GetMaxHeight(tile);

	for (local curr_tile = _SuperLib_Direction.GetAdjacentTileInDirection(tile, bridge_search_direction);
			true;
			curr_tile = _SuperLib_Direction.GetAdjacentTileInDirection(curr_tile, bridge_search_direction))
	{
		local curr_tile_height = AITile.GetMaxHeight(curr_tile);
		if (curr_tile_height < max_height)
		{
			// The down slope at the other side of a hill has been found -> There can't be a bridge to 'tile'.
			return -1;
		}

		max_height = max(max_height, curr_tile_height);

		if (AIBridge.IsBridgeTile(curr_tile))
		{
			// A bridge was found

			// Check that the bridge goes in the right direction
			local other_end = AIBridge.GetOtherBridgeEnd(curr_tile);
			local found_bridge_dir = _SuperLib_Direction.GetDirectionToTile(curr_tile, other_end);

			// Return -1 if the bridge direction is wrong eg. 90 deg of bridge_search_direction or away from the tile 'tile'
			return found_bridge_dir == bridge_search_direction? curr_tile : -1;
		}

		// Is the next tile the same as current tile?
		// That is, have we reached the end of the map?
		if(curr_tile == _SuperLib_Direction.GetAdjacentTileInDirection(curr_tile, bridge_search_direction))
		{
			break;
		}
	}

	return -1;
}

function _SuperLib_Tile::FindClosestRoadTile(tile, max_radius)
{
	if(!tile || !AIMap.IsValidTile(tile))
		return null;

	if(AIRoad.IsRoadTile(tile))
		return tile;

	local r; // current radius

	local start_x = AIMap.GetTileX(tile);
	local start_y = AIMap.GetTileY(tile);

	local x0, x1, y0, y1;
	local ix, iy;
	local test_tile;

	for(r = 1; r < max_radius; ++r)
	{
		y0 = start_y - r;
		y1 = start_y + r;
		for(ix = start_x - r; ix <= start_x + r; ++ix)
		{
			test_tile = AIMap.GetTileIndex(ix, y0)
			if(test_tile != null && AIRoad.IsRoadTile(test_tile))
				return test_tile;

			test_tile = AIMap.GetTileIndex(ix, y1)
			if(test_tile != null && AIRoad.IsRoadTile(test_tile))
				return test_tile;
		}

		x0 = start_x - r;
		x1 = start_x + r;
		for(iy = start_y - r + 1; iy <= start_y + r - 1; ++iy)
		{
			test_tile = AIMap.GetTileIndex(x0, iy)
			if(test_tile != null && AIRoad.IsRoadTile(test_tile))
				return test_tile;

			test_tile = AIMap.GetTileIndex(x1, iy)
			if(test_tile != null && AIRoad.IsRoadTile(test_tile))
				return test_tile;

		}
	}

	return null;
}

function _SuperLib_Tile::IsDepotTile(tile, vehicle_type)
{
	switch(vehicle_type)
	{
		case AIVehicle.VT_ROAD:
			local old_rt = AIRoad.GetCurrentRoadType();
			local rt_list = [AIRoad.ROADTYPE_ROAD, AIRoad.ROADTYPE_TRAM];
			foreach(rt in rt_list)
			{
				if(AIRoad.HasRoadType(tile, rt))
				{
					AIRoad.SetCurrentRoadType(rt);

					if(AIRoad.IsRoadDepotTile(tile))
					{
						AIRoad.SetCurrentRoadType(old_rt);
						return true;
					}
				}
			}
			AIRoad.SetCurrentRoadType(old_rt);
			return false;

		case AIVehicle.VT_RAIL:
			local old_rt = AIRail.GetCurrentRailType();
			local rt_list = AIRailTypeList();
			foreach(rt, _ in rt_list)
			{
				if(AIRail.GetRailType(tile) == rt)
				{
					AIRail.SetCurrentRailType(rt);

					if(AIRail.IsRailDepotTile(tile))
					{
						AIRail.SetCurrentRailType(old_rt);
						return true;
					}
				}
			}
			AIRail.SetCurrentRailType(old_rt);
			return false;

		case AIVehicle.VT_AIR:
			return AIAirport.IsHangarTile(tile);

		case AIVehicle.VT_WATER:
			return AIAirport.IsWaterDepotTile(tile);
	}

	return false;
}

function _SuperLib_Tile::CanWalk4ToTile(from_tile, to_tile, is_allowed_tile_function)
{
	return _SuperLib_Tile.CanWalkToTile(from_tile, to_tile, is_allowed_tile_function, _SuperLib_Tile.GetNeighbours4MainDir);
}

function _SuperLib_Tile::CanWalk8ToTile(from_tile, to_tile, is_allowed_tile_function)
{
	return _SuperLib_Tile.CanWalkToTile(from_tile, to_tile, is_allowed_tile_function, _SuperLib_Tile.GetNeighbours8);
}

function _SuperLib_Tile::CanWalkToTile(from_tile, to_tile, is_allowed_tile_function, neighbours_function)
{
	if(from_tile == to_tile) return true;

	local open_list = AIList();
	local closed_list = AIList();

	// Init
	local curr_tile = from_tile;
	closed_list.AddItem(curr_tile, 0);

	while(true)
	{
		// Add the neighbours of current tile that have not been visited to open_list
		local neighbours = neighbours_function(curr_tile);
		neighbours.RemoveList(closed_list);
		neighbours.Valuate(is_allowed_tile_function);
		neighbours.KeepValue(1);
		open_list.AddList(neighbours);

		// If open_list is empty and we have not visited the to_tile, there is no path.
		if(open_list.IsEmpty())
			return false;

		// Pick a new curr_tile from open_list
		curr_tile = open_list.Begin();
		open_list.RemoveItem(curr_tile);
		closed_list.AddItem(curr_tile, 0); // add it to close_list so it is not visited again

		// Is the new curr_tile the to_tile?
		if(curr_tile == to_tile)
			return true;
	}
}

function _SuperLib_Tile::CostToClearTiles(tile_list)
{
	local test_mode = AITestMode();
	local account = AIAccounting();

	foreach(tile, _ in tile_list) {
		AITile.DemolishTile(tile);
	}

	return account.GetCosts();
}

function _SuperLib_Tile::CostToFlattern(top_left_tile, width, height)
{
	if(!AITile.IsBuildableRectangle(top_left_tile, width, height))
		return -1; // not buildable

	if(_SuperLib_Tile.IsTileRectBuildableAndFlat(top_left_tile, width, height))
		return 0; // zero cost

	local level_cost = 0;
	{{
		local test = AITestMode();
		local account = AIAccounting();

		if(!AITile.LevelTiles(top_left_tile, _SuperLib_Tile.GetTileRelative(top_left_tile, width, height)))
			return -1;

		level_cost = account.GetCosts();
	}}

	return level_cost;

	return 0;
}

function _SuperLib_Tile::FlatternRect(top_left_tile, width, height)
{
	if(AITile.GetCornerHeight(top_left_tile, AITile.CORNER_N) == 0)
	{
		// Don't allow flattern down to sea level
		return false;
	}

	return AITile.LevelTiles(top_left_tile, _SuperLib_Tile.GetTileRelative(top_left_tile, width, height));
}

function _SuperLib_Tile::IsTileRectBuildableAndFlat(top_left_tile, width, height)
{
	local tiles = AITileList();

	// First use API function to check rect as that is faster than doing it self in squirrel.
	if(!AITile.IsBuildableRectangle(top_left_tile, width, height))
		return false;

	// Then only if it is buildable, check that it is flat also.
	tiles.AddRectangle(top_left_tile, _SuperLib_Tile.GetTileRelative(top_left_tile, width - 1, height - 1));

	// remember how many tiles there are from the beginning
	local count_before = tiles.Count();

	// remove non-flat tiles
	tiles.Valuate(AITile.GetSlope);
	tiles.KeepValue(0);

	// if all tiles are remaining, then all tiles are flat
	return count_before == tiles.Count();
}
