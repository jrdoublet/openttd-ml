/*
 * This file is part of SuperLib, which is an AI Library for OpenTTD
 * Copyright (C) 2011  Zuu
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

class _SuperLib_Town
{
	static function TownRatingAllowStationBuilding(town_id);

	/*
	 * These methods will use GetTerrainType available in OpenTTD 1.3.1
	 * and later. If your AI/GS is used in an older version of OpenTTD
	 * these methods will fall back to a slower method which iterate over
	 * the land around the town to see what is the dominating land type
	 * using an older API that only work on clear land.
	 *
	 * Note: If you write an AI and want to detect if a town need water
	 * in desert or food in artic to grow, use AITown.GetCargoGoal instead
	 * which will have the benefit of adapting to when the growth goals are
	 * adopted by a Game Script. These methods are mainly intended for such
	 * Game Scripts which will set the cargo goals of towns.
	 *
	 * Note 2: When IsDesertTown and IsSnowTown operate in fallback mode,
	 * they will not always report the correct result. For towns in the
	 * border between snow/desert and non-snow/desert, they will give some
	 * false positives and false negatives.
	 *
	 * Note 3: IsDesertTown fallback will cache its results while IsSnowTown
	 * will always iterate over tiles in fallback mode due to the chance of
	 * there being a NewGRF with variable snow height.
	 */
	static function IsDesertTown(town_id);
	static function IsSnowTown(town_id);

	/*
	 * Returns true if IsDesertTown and IsSnowTown will use the fallback
	 * method.
	 */
	static function WillUseTerrainFallbackMethod();
}

function _SuperLib_Town::TownRatingAllowStationBuilding(town_id)
{
	local rating = AITown.GetRating(town_id, AICompany.COMPANY_SELF);
   	return rating == AITown.TOWN_RATING_NONE || rating > AITown.TOWN_RATING_VERY_POOR;
}

function _SuperLib_Town::IsDesertTown(town_id)
{
	local town_tile = AITown.GetLocation(town_id);
	if ("GetTerrainType" in AITile) {
		return !AITile.IsWaterTile(town_tile) && AITile.GetTerrainType(town_tile) == AITile.TERRAIN_DESERT;
	}

	// Fallback cache
	if (_SuperLib_Town_private_desert_towns.rawin(town_id)) {
		return _SuperLib_Town_private_desert_towns.rawget(town_id);
	}

	// Fallback method for older OpenTTD versions
	// - Search in all 8 directions out from the town
	//   until a buildable tile is found.
	// - Desert tiles score a positive value and non-desert
	//   tiles score a negative value. The score is weighted
	//   by the distance to town so that tiles near the town
	//   weight more.
	// - If the total score is > X, the town is estimated to
	//   be a desert town.

	local result = _SuperLib_Town_Private_TownLandType(town_id, AITile.IsDesertTile);

	// Cache result
	_SuperLib_Town_private_desert_towns.rawset(town_id, result);

	return result;
}

function _SuperLib_Town::IsSnowTown(town_id)
{
	local town_tile = AITown.GetLocation(town_id);
	if ("GetTerrainType" in AITile) {
		return AITile.GetTerrainType(town_tile) == AITile.TERRAIN_SNOW;
	}

	// Fallback method for older OpenTTD versions

	// Due to variable snow height, we cannot cache the result of this method
	return _SuperLib_Town_Private_TownLandType(town_id, AITile.IsSnowTile);
}

function _SuperLib_Town::WillUseTerrainFallbackMethod()
{
	return !("GetTerrainType" in AITile);
}

function _SuperLib_Town_Private_TownLandType(town_id, land_type_func)
{
	// Start by searching in the main dirs
	local main_dirs = AIList();
	main_dirs.AddItem(_SuperLib_Direction.DIR_N, 0);
	main_dirs.AddItem(_SuperLib_Direction.DIR_W, 0);
	main_dirs.AddItem(_SuperLib_Direction.DIR_S, 0);
	main_dirs.AddItem(_SuperLib_Direction.DIR_E, 0);

	local main_dir_search = _SuperLib_Town_Private_TownLandTypeScore(town_id, land_type_func, main_dirs);

	// If all 4 main dirs are positive/negative, then return true/false
	if (main_dir_search.n_true_dirs == 4) return true;
	if (main_dir_search.n_true_dirs == 0) return false;

	// Town is at a border. Get counts also for diagonal dirs before drawing a conclusion
	local diag_dirs = AIList();
	diag_dirs.AddItem(_SuperLib_Direction.DIR_NE, 0);
	diag_dirs.AddItem(_SuperLib_Direction.DIR_NW, 0);
	diag_dirs.AddItem(_SuperLib_Direction.DIR_SE, 0);
	diag_dirs.AddItem(_SuperLib_Direction.DIR_SW, 0);
	local diag_dir_search = _SuperLib_Town_Private_TownLandTypeScore(town_id, land_type_func, diag_dirs);

	local tot_score = main_dir_search.score + diag_dir_search.score;

	return tot_score > 0;
}
function _SuperLib_Town_Private_TownLandTypeScore(town_id, land_type_func, dir_list)
{
	local town_tile = AITown.GetLocation(town_id);
	local max_search = 30;

	// null = no clear tile found yet
	// false = not desert
	// true = is desert
	local dir_status = [null, null, null, null, null, null, null, null];
	local score = 0;       // total score
	local n_true_dirs = 0; // n dirs where land_type_func returns true
	local n_unknown_dirs = dir_list.Count();
	for (local i = 1; i < max_search; i++) {
		foreach (dir, _ in dir_list) {
			if (dir_status[dir] != null) continue;

			local t = _SuperLib_Direction.GetTileInDirection(town_tile, dir, i);

			if (AITile.IsWaterTile(t)) {
				dir_status[dir] = false;
				n_unknown_dirs--;
			} else if (AITile.IsBuildable(t) && !AITile.HasTreeOnTile(t)) {
				dir_status[dir] = land_type_func(t);
				if (dir_status[dir]) n_true_dirs++;
				n_unknown_dirs--;
				score += (dir_status[dir]? 1 : -1) * (max_search - i) / 5;
			}
		}

		if (n_unknown_dirs == 0) break;
	}

	return {score = score, n_true_dirs = n_true_dirs};
}


// Private static variables
_SuperLib_Town_private_desert_towns <- {};

