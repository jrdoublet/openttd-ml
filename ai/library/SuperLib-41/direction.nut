/*
 * This file is part of SuperLib.Direction, which is an AI Library for OpenTTD
 * Copyright (C) 2010  Zuu
 *
 * SuperLib.Direction is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License
 *
 * SuperLib.Direction is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with SuperLib.Direction; If not, see <http://www.gnu.org/licenses/> or
 * write to the Free Software Foundation, Inc., 51 Franklin Street,
 * Fifth Floor, Boston, MA 02110-1301 USA.
 *
 */

class _SuperLib_Direction
{
	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Constants                                                       //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* _SuperLib_Direction constants */
	static DIR_N = 0;
	static DIR_NE = 1;
	static DIR_E  = 2;
	static DIR_SE = 3;
	static DIR_S  = 4;
	static DIR_SW = 5;
	static DIR_W  = 6;
	static DIR_NW = 7;

	/* Special values */
	static DIR_FIRST = 0;
	static DIR_LAST = 7;

	static DIR_INVALID = 8;

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  To string                                                       //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Translates a direction value into a human readable string that
	 * can be used for logging.
	 */
	static function GetDirString(dir);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Classification of direction                                     //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Returns true if the direction is a main direction (NW, SW, SE or NE) */
	static function IsMainDir(dir);

	/* Returns true if the direction is a diagonal direction (N, W, S or E) */
	static function IsDiagonalDir(dir);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  List of directions                                              //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Returns an AIList with all directions in random order */
	static function GetAllDirsInRandomOrder();

	/* Returns an AIList with all main directions in random order */
	static function GetMainDirsInRandomOrder();

	/* Returns an AIList with all diagonal directions in random order */
	static function GetDiagonalDirsInRandomOrder();

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Move In Direction                                               //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Returns the tile you get to if you move one tile in the
	 * 'in_direction' direction from 'from_tile'.
	 */
	static function GetAdjacentTileInDirection(from_tile, in_direction);

	/*
	 * Same as GetAdjacentTileInDirection, but not limited to adjacent tiles.
	 * When going in diagonal directions, the number of tiles are counted
	 * as if GetAdjacentTileInDirection was called in a loop.
	 */
	static function GetTileInDirection(from_tile, in_direction, n);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Get Direction between tiles                                     //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* If these function fails they return Direction.DIR_INVALID */

	/* Returns the direction you have to go from tile in order to reach
	 * adjacent_tile. A precondition is that these two tiles are
	 * adjacent.
	 */
	static function GetDirectionToAdjacentTile(tile, adjacent_tile);

	/* Returns the direction you have to move from tile1 to reach tile2.
	 * This function do not require tile1 and tile2 to be adjacent, but
	 * they must be exactly in one of the eight directions.
	 */
	static function GetDirectionToTile(tile1, tile2);

	/* Returns the direction from tile1 to tile2.
	 * Tiles do not have to be adjacent or exactly on compass axis.
	 * If directly on the axis it will be NE/SE/SW/NW, else it will
	 * be N/E/S/W.
	 * This method will fail if tile1 == tile2.
	 * This method was contributed by R2dical.
	 */
	static function GetDirectionToTileApprox(tile1, tile2);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Turn Direction                                                  //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Turns 'dir' 45 degrees clockwise a given number of times.
	 * num_45_deg must be an integer value. Negative values of num_45_deg
	 * are accepted.
	 */
	static function TurnDirClockwise45Deg(dir, num_45_deg);

	/* Same as TurnDirClockwise45Deg but turns anti clocwise instead */
	static function TurnDirAntiClockwise45Deg(dir, num_45_deg);

	static function TurnDirClockwise90Deg(dir, num_90_deg);
	static function TurnDirAntiClockwise90Deg(dir, num_90_deg);

	static function OppositeDir(dir);
}

function _SuperLib_Direction::GetDirString(dir)
{
	switch(dir)
	{
		case _SuperLib_Direction.DIR_N:
			return "N";
		case _SuperLib_Direction.DIR_NE:
			return "NE";
		case _SuperLib_Direction.DIR_E:
			return "E";
		case _SuperLib_Direction.DIR_SE:
			return "SE";
		case _SuperLib_Direction.DIR_S:
			return "S";
		case _SuperLib_Direction.DIR_SW:
			return "SW";
		case _SuperLib_Direction.DIR_W:
			return "W";
		case _SuperLib_Direction.DIR_NW:
			return "NW";
		default:
			_SuperLib_Log.Error("Direction::GetDirString: invalid direction: " + dir, _SuperLib_Log.LVL_INFO);
			return -1;
	}

}

function _SuperLib_Direction::IsMainDir(dir)
{
	return dir == _SuperLib_Direction.DIR_NE ||
			dir == _SuperLib_Direction.DIR_SE ||
			dir == _SuperLib_Direction.DIR_SW ||
			dir == _SuperLib_Direction.DIR_NW;
}

function _SuperLib_Direction::IsDiagonalDir(dir)
{
	return dir == _SuperLib_Direction.DIR_N ||
			dir == _SuperLib_Direction.DIR_E ||
			dir == _SuperLib_Direction.DIR_S ||
			dir == _SuperLib_Direction.DIR_W;
}

function _SuperLib_Direction::GetAllDirsInRandomOrder()
{
	local dir_list = AIList();
	for(local dir = _SuperLib_Direction.DIR_FIRST; dir != _SuperLib_Direction.DIR_LAST + 1; dir++)
	{
		dir_list.AddItem(dir, AIBase.Rand());
	}
	dir_list.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);

	return dir_list;
}

function _SuperLib_Direction::GetMainDirsInRandomOrder()
{
	local dir_list = AIList();
	for(local dir = _SuperLib_Direction.DIR_FIRST; dir != _SuperLib_Direction.DIR_LAST + 1; dir++)
	{
		if(!_SuperLib_Direction.IsMainDir(dir))
			continue;

		dir_list.AddItem(dir, AIBase.Rand());
	}
	dir_list.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);

	return dir_list;
}

function _SuperLib_Direction::GetDiagonalDirsInRandomOrder()
{
	local dir_list = AIList();
	for(local dir = _SuperLib_Direction.DIR_FIRST; dir != _SuperLib_Direction.DIR_LAST + 1; dir++)
	{
		if(!_SuperLib_Direction.IsDiagonalDir(dir))
			continue;

		dir_list.AddItem(dir, AIBase.Rand());
	}
	dir_list.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);

	return dir_list;
}

function _SuperLib_Direction::GetAdjacentTileInDirection(from_tile, in_direction)
{
	return _SuperLib_Direction.GetTileInDirection(from_tile, in_direction, 1);
}

function _SuperLib_Direction::GetTileInDirection(from_tile, in_direction, n)
{
	if(n == 0) return from_tile;

	switch(in_direction)
	{
		case _SuperLib_Direction.DIR_N:
			return _SuperLib_Tile.GetTileRelative(from_tile, -n, -n);
		case _SuperLib_Direction.DIR_NE:
			return _SuperLib_Tile.GetTileRelative(from_tile, -n,  0);
		case _SuperLib_Direction.DIR_E:
			return _SuperLib_Tile.GetTileRelative(from_tile, -n,  n);
		case _SuperLib_Direction.DIR_SE:
			return _SuperLib_Tile.GetTileRelative(from_tile,  0,  n);
		case _SuperLib_Direction.DIR_S:
			return _SuperLib_Tile.GetTileRelative(from_tile,  n,  n);
		case _SuperLib_Direction.DIR_SW:
			return _SuperLib_Tile.GetTileRelative(from_tile,  n,  0);
		case _SuperLib_Direction.DIR_W:
			return _SuperLib_Tile.GetTileRelative(from_tile,  n, -n);
		case _SuperLib_Direction.DIR_NW:
			return _SuperLib_Tile.GetTileRelative(from_tile,  0, -n);
		default:
			_SuperLib_Log.Error("Direction::GetTileInDirection: invalid direction: " + in_direction, _SuperLib_Log.LVL_INFO);
			return -1;
	}
}

function _SuperLib_Direction::GetDirectionToAdjacentTile(tile, adjacent_tile)
{
	local rel_x = AIMap.GetTileX(adjacent_tile) - AIMap.GetTileX(tile);
	local rel_y = AIMap.GetTileY(adjacent_tile) - AIMap.GetTileY(tile);

	local rel_dir = [ [_SuperLib_Direction.DIR_N, [-1, -1]],
			[_SuperLib_Direction.DIR_NE, [-1,  0]],
			[_SuperLib_Direction.DIR_E,  [-1,  1]],
			[_SuperLib_Direction.DIR_SE, [ 0,  1]],
			[_SuperLib_Direction.DIR_S,  [ 1,  1]],
			[_SuperLib_Direction.DIR_SW, [ 1,  0]],
			[_SuperLib_Direction.DIR_W,  [ 1, -1]],
			[_SuperLib_Direction.DIR_NW, [ 0, -1]] ];

	foreach(dir in rel_dir)
	{
		local rel = dir[1];
		local X = 0;
		local Y = 1;

		if(rel[X] == rel_x && rel[Y] == rel_y)
		{
			return dir[0];
		}
	}

	return _SuperLib_Direction.DIR_INVALID;
}

function _SuperLib_Direction::GetDirectionToTile(tile1, tile2)
{
	local rel_x = AIMap.GetTileX(tile2) - AIMap.GetTileX(tile1);
	local rel_y = AIMap.GetTileY(tile2) - AIMap.GetTileY(tile1);

	if(rel_x == 0 && rel_y == 0)
	{
		return _SuperLib_Direction.DIR_INVALID;
	}
	else if (_SuperLib_Helper.Abs(rel_x) >= 1 && _SuperLib_Helper.Abs(rel_y) >= 1)
	{
		// Neither of NE, NW, SW, SE

		if (_SuperLib_Helper.Abs(rel_x) == _SuperLib_Helper.Abs(rel_y))
		{
			// Same amplitude of rel_x and rel_y => N, W, S or E.
			if(rel_x <= -1 && rel_y <= -1) return _SuperLib_Direction.DIR_N;
			if(rel_x <= -1 && rel_y >= 1) return _SuperLib_Direction.DIR_E;
			if(rel_x >= 1 && rel_y >= 1) return _SuperLib_Direction.DIR_S;
			if(rel_x >= 1 && rel_y <= -1) return _SuperLib_Direction.DIR_W;

			// Error
			return _SuperLib_Direction.DIR_INVALID;
		}
		else
		{
			// Not a valid direction
			return _SuperLib_Direction.DIR_INVALID;
		}
	}
	else
	{
		// either rel_x or rel_y is 0 and the other has a value > 0.

		if (rel_x < 0) return _SuperLib_Direction.DIR_NE;
		if (rel_y > 0) return _SuperLib_Direction.DIR_SE;
		if (rel_x > 0) return _SuperLib_Direction.DIR_SW;
		if (rel_y < 0) return _SuperLib_Direction.DIR_NW;

		// Error
		return _SuperLib_Direction.DIR_INVALID
	}

	// Error
	return _SuperLib_Direction.DIR_INVALID
}

/* This method was contributed by R2dical. */
function _SuperLib_Direction::GetDirectionToTileApprox(tile1, tile2)
{
	local rel_x = AIMap.GetTileX(tile2) - AIMap.GetTileX(tile1);
	local rel_y = AIMap.GetTileY(tile2) - AIMap.GetTileY(tile1);

	// Same tile
	if (rel_x == 0 && rel_y == 0) return _SuperLib_Direction.DIR_INVALID;
	// On the same axis.
	else if (rel_x == 0 && rel_y > 0) return _SuperLib_Direction.DIR_NW;
	else if (rel_x == 0 && rel_y < 0) return _SuperLib_Direction.DIR_SE;
	else if (rel_x > 0 && rel_y == 0) return _SuperLib_Direction.DIR_NE;
	else if (rel_x < 0 && rel_y == 0) return _SuperLib_Direction.DIR_SW;
	// Off axis.
	else if (rel_x > 0 && rel_y > 0) return _SuperLib_Direction.DIR_N;
	else if (rel_x < 0 && rel_y < 0) return _SuperLib_Direction.DIR_S;
	else if (rel_x > 0 && rel_y < 0) return _SuperLib_Direction.DIR_E;
	else if (rel_x < 0 && rel_y > 0) return _SuperLib_Direction.DIR_W;

	// Error
	return _SuperLib_Direction.DIR_INVALID
}

function _SuperLib_Direction::TurnDirClockwise45Deg(dir, num_45_deg)
{
	/* Make sure to only handle positive turns */
	if(num_45_deg < 0) return TurnDirAntiClockwise45Deg(dir, -num_45_deg);

	dir += num_45_deg

	while(dir > _SuperLib_Direction.DIR_LAST)
	{
		dir -= (_SuperLib_Direction.DIR_LAST - _SuperLib_Direction.DIR_FIRST) + 1;
	}

	return dir;
}

function _SuperLib_Direction::TurnDirAntiClockwise45Deg(dir, num_45_deg)
{
	/* Make sure to only handle positive turns */
	if(num_45_deg < 0) return TurnDirClockwise45Deg(dir, -num_45_deg);

	dir -= num_45_deg

	while(dir < _SuperLib_Direction.DIR_FIRST)
	{
		dir += (_SuperLib_Direction.DIR_LAST - _SuperLib_Direction.DIR_FIRST) + 1;
	}

	return dir;
}

function _SuperLib_Direction::TurnDirClockwise90Deg(dir, num_90_deg)
{
	return _SuperLib_Direction.TurnDirClockwise45Deg(dir, num_90_deg * 2);
}

function _SuperLib_Direction::TurnDirAntiClockwise90Deg(dir, num_90_deg)
{
	return _SuperLib_Direction.TurnDirAntiClockwise45Deg(dir, num_90_deg * 2);
}

function _SuperLib_Direction::OppositeDir(dir)
{
	return _SuperLib_Direction.TurnDirClockwise45Deg(dir, 4);
}
