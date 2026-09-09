/*
 * This file is part of SuperLib, which is an AI Library for OpenTTD
 * Copyright (C) 2010-2011  Zuu
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

class _SuperLib_Airport
{
	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Airport types                                                   //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Returns an AIList with all airport types
	 */
	static function GetAirportTypeList();

	/*
	 * Returns the last available airport that the given engine can use
	 */
	static function GetLastAvailableAirportType(engine_id);

	/*
	 * Returns the amount of noise that a given airport type emits.
	 * (this is computed using the assumption that the center tile
	 *  of a town gets full noise level from an airport type)
	 */
	static function GetAirportTypeNoiseLevel(airport_type);

	/*
	 * Returns true if the plane type can (safely) use the airport type,
	 * else false.
	 * Large aircrafts on small airports yields false.
	 */
	static function IsPlaneTypeAcceptedByAirportType(plane_type, airport_type);

	/*
	 * Same as above, but with reversed argument order.
	 */
	static function IsAirportTypeAcceptingPlaneType(airport_type, plane_type);

	/* Checks if there is at least one airport that the given plan type can land (safely) on */
	static function AreThereAirportsForPlaneType(plane_type);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Airport information                                             //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Get the north tile of the airport of a given station.
	 * Returns an invalid tile if there is no airport for the given station
	 */
	static function GetAirportTile(station_id);

	/*
	 * Get the tile of one of the hangars of the airport of the given station.
	 * Returns an invalid tile on failure.
	 */
	static function GetHangarTile(station_id);

	/*
	 * Check if a given station has a small airport
	 */
	static function IsSmallAirport(station_id);
	static function IsSmallAirportType(airport_type);

	static function WillAirportAcceptCargo(top_left_tile, airport_type, cargo);
	static function WillAirportProduceCargo(top_left_tile, airport_type, cargo);

	static function GetAirportCargoAcceptance(top_left_tile, airport_type, cargo);
	static function GetAirportCargoProduction(top_left_tile, airport_type, cargo);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Airport construction                                            //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Note that if no cargo is passed to BuildAirportInTown, then the airport
	 * will be placed as far away as possible from the town, while still
	 * belonging to that town.
	 *
	 * accept_cargo and produce_cargo should be a cargo ID or -1 if you
	 * don't want to specify a cargo acceptance/production criteria.
	 */

	/* Return: tile or null */
	static function BuildAirportInTown(town_id, airport_type, accept_cargo = -1, produce_cargo = -1);

	/* Return: tile or null */
	/* Known limitations:
	 * - Doesn't try to alter the landscape to work with hilly terrain
	 * - Does only evaluate locations when the top left tile of the airport
	 *   is within range of the industry.
	 */
	static function BuildAirportForIndustry(airport_type, industry_id);

	/* Return: tile or null */
	static function FindInTownAirportPlacement(town_id, station_w, station_h, airport_type, maximum_noise, accept_cargo, produce_cargo);
	/* Return: an AIList with tiles */
	static function GetIndustryAirportCandidateTiles(airport_type, industry_id);
	/* note that IndustryAirportCandidateScore will run DoCommands in test mode need to be used in a for loop and not as a Valuator */
	static function IndustryAirportCandidateScore(tile, airport_type, old_airport_noise = 0, old_airport_town = -1);
	/*
	 * upgrade_type_list = squirrel array with airport types ordered with most desired first
	 *
	 * This function uses SuperLib::Result for return values:
	 * - SUCCESS
	 * - FAIL
	 * - REBUILD_FAILED  (= removed old airport, but couldn't build new one)
	 */
	static function UpgradeAirportInTown(town_id, old_station_id, upgrade_type_list, accept_cargo = -1, produce_cargo = -1);
	static function UpgradeAirportForIndustry(industry_id, old_station_id, upgrade_type_list, accept_cargo = -1, produce_cargo = -1);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Aircraft information                                            //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////
	/*
	 * Returns an AIList of all aircrafts in all the hangar(s) of the airport
	 * of a given station.
	 * Returns an empty AIList if there are no aircrafts.
	 */
	static function GetAircraftInHangar(station_id);
	static function GetAircraftsInHangar(station_id); // Old name up to version 19 of SuperLib

	/*
	 * Returns the number of non-stoped aircrafts in airport depot
	 */
	static function GetNumNonStopedAircraftInAirportDepot(station_id);
	static function GetNumNonStopedAircraftsInAirportDepot(station_id); // Old name up to version 19 of SuperLib


	/*
	 * Returns the number of aircrafts that are in the landing queue.
	 * That is aircrafts that are circulating and waiting to land.
	 *
	 * if filter_aircraft_destination = true, then only aircrafts that
	 * are going to the station given in station_id will included.
	 * if filter_aircraft_destination is set to false, then any aircraft
	 * in the holding queue will be included.
	 */
	static function GetNumAircraftInAirportQueue(station_id, filter_aircraft_destination = true);
	static function GetNumAircraftsInAirportQueue(station_id, filter_aircraft_destination = true); // Old name up to version 19 of SuperLib


	/*
	 * Get the distance from the center of an airport (existing or planed) to some other tile.
	 * What makes this function special is that it uses the airport center and not the north corner.
	 */
	static function AirportCenterDistanceManhatanTo(airport_tile, airport_type, other_tile);
}

/*static*/ function _SuperLib_Airport::GetAirportTypeList()
{
	local list = AIList();
	for(local i = 0; i <= AIAirport.AT_INTERCON; ++i)
	{
		if(AIAirport.IsAirportInformationAvailable(i))
			list.AddItem(i, i);
	}

	return list;
}

/*static*/ function _SuperLib_Airport::GetLastAvailableAirportType(engine_id)
{
	local airport_types = _SuperLib_Airport.GetAirportTypeList();

	// Only keep airports that accept the given engine type
	airport_types.Valuate(_SuperLib_Airport.IsAirportTypeAcceptingPlaneType, AIEngine.GetPlaneType(engine_id));
	airport_types.KeepValue(1);

	// Only keep buildable airports
	airport_types.Valuate(AIAirport.IsValidAirportType);
	airport_types.KeepValue(1);

	if (airport_types.IsEmpty())
		return -1;

	// Return the airport with highest index
	airport_types.Sort(AIList.SORT_BY_ITEM, AIList.SORT_DESCENDING);
	return airport_types.Begin();
}

/*static*/ function _SuperLib_Airport::GetAirportTypeNoiseLevel(airport_type)
{
	local town_center_tile = AITown.GetLocation(AITownList().Begin());
	return AIAirport.GetNoiseLevelIncrease(town_center_tile, airport_type);
}
/*static*/ function _SuperLib_Airport::IsAirportTypeAcceptingPlaneType(airport_type, plane_type)
{
	return _SuperLib_Airport.IsPlaneTypeAcceptedByAirportType(plane_type, airport_type);
}

/*static*/ function _SuperLib_Airport::AreThereAirportsForPlaneType(plane_type)
{
	local list = _SuperLib_Airport.GetAirportTypeList();

	// Only keep buildable airports
	list.Valuate(AIAirport.IsValidAirportType);
	list.KeepValue(1);

	list.Valuate(_SuperLib_Airport.IsAirportTypeAcceptingPlaneType, plane_type);
	list.KeepValue(1);

	return !list.IsEmpty();
}

/*static*/ function _SuperLib_Airport::IsPlaneTypeAcceptedByAirportType(plane_type, airport_type)
{
	// Use full listing of hard coded airport types so that we don't assume anything about
	// possible future added airports.
	local large_ap = airport_type == AIAirport.AT_LARGE ||
				airport_type == AIAirport.AT_METROPOLITAN ||
				airport_type == AIAirport.AT_INTERNATIONAL ||
				airport_type == AIAirport.AT_INTERCON;

	local small_ap = airport_type == AIAirport.AT_SMALL ||
				airport_type == AIAirport.AT_COMMUTER;

	local heli_ap = airport_type == AIAirport.AT_HELIPORT ||
				airport_type == AIAirport.AT_HELISTATION ||
				airport_type == AIAirport.AT_HELIDEPOT;

	switch(plane_type)
	{
		case AIAirport.PT_BIG_PLANE:
			return large_ap;

		case AIAirport.PT_SMALL_PLANE:
			return large_ap || small_ap;

		case AIAirport.PT_HELICOPTER:
			return heli_ap || large_ap || small_ap; // All currently (2010-06-26) hardcoded airport types can take helicopters

	}

	_SuperLib_Log.Error("SuperLib::Airport::IsPlaneTypeAcceptedByAirportType: Unknown plane type (" + plane_type + ").", _SuperLib_Log.LVL_INFO);
	return false; // Should not happen
}

/*static*/ function _SuperLib_Airport::GetAirportTile(station_id)
{
	local airport_tiles = AITileList_StationType(station_id, AIStation.STATION_AIRPORT);
	if(airport_tiles.IsEmpty())
		return -1;

	airport_tiles.Sort(AIList.SORT_BY_ITEM, AIList.SORT_ASCENDING);

	return airport_tiles.Begin();
}

/*static*/ function _SuperLib_Airport::GetHangarTile(station_id)
{
	local hangar_tile = AIAirport.GetHangarOfAirport(_SuperLib_Airport.GetAirportTile(station_id));
	return hangar_tile;
}

/*static*/ function _SuperLib_Airport::WillAirportAcceptCargo(top_left_tile, airport_type, cargo)
{
	return _SuperLib_Airport.GetAirportCargoAcceptance(top_left_tile, airport_type, cargo) >= 8;
}

/*static*/ function _SuperLib_Airport::WillAirportProduceCargo(top_left_tile, airport_type, cargo)
{
	return _SuperLib_Airport.GetAirportCargoProduction(top_left_tile, airport_type, cargo) >= 8;
}

/*static*/ function _SuperLib_Airport::GetAirportCargoAcceptance(top_left_tile, airport_type, cargo)
{
	local coverage_radius = AIAirport.GetAirportCoverageRadius(airport_type);

	local ap_w = AIAirport.GetAirportWidth(airport_type);
	local ap_h = AIAirport.GetAirportHeight(airport_type);

	local acc = AITile.GetCargoAcceptance(top_left_tile, cargo, ap_w, ap_h, coverage_radius);

	return acc;
}

/*static*/ function _SuperLib_Airport::GetAirportCargoProduction(top_left_tile, airport_type, cargo)
{
	local coverage_radius = AIAirport.GetAirportCoverageRadius(airport_type);

	local ap_w = AIAirport.GetAirportWidth(airport_type);
	local ap_h = AIAirport.GetAirportHeight(airport_type);

	local prod = AITile.GetCargoProduction(top_left_tile, cargo, ap_w, ap_h, coverage_radius);

	return prod;
}


/*static*/ function _SuperLib_Airport::BuildAirportInTown(town_id, airport_type, accept_cargo = -1, produce_cargo = -1)
{
	// Don't waste time if station rating is too low
	if(!_SuperLib_Town.TownRatingAllowStationBuilding(town_id))
		return null;

	local ap_w = AIAirport.GetAirportWidth(airport_type);
	local ap_h = AIAirport.GetAirportHeight(airport_type);

	local max_noise_add = AITown.GetAllowedNoise(town_id);

	// Find somewhere to build the airport.
	// since level rect function do not guarantee to work in exec mode even if it work in test-mode
	// it need to be an iterative process to level land for the airport.
	local i = 0;
	local ap_tile = null;
	do
	{
		local find_ap_tile_result = _SuperLib_Airport.FindInTownAirportPlacement(town_id, ap_w, ap_h, airport_type, max_noise_add, accept_cargo, produce_cargo);
		ap_tile = find_ap_tile_result.tile;
		if(ap_tile != null)
		{
			_SuperLib_Helper.SetSign(ap_tile, "ap");
			_SuperLib_Tile.FlatternRect(ap_tile, ap_w, ap_h);
		}

		// Abort after 5 tries
		if(++i > 5)
			break;
	}
	while(ap_tile != null && AIMap.IsValidTile(ap_tile) && !_SuperLib_Tile.IsTileRectBuildableAndFlat(ap_tile, ap_w, ap_h))

	if(ap_tile != null && AIMap.IsValidTile(ap_tile))
	{
		// Build airport
		local airport_status = AIAirport.BuildAirport(ap_tile, airport_type, AIStation.STATION_NEW);

		if(!AIAirport.IsAirportTile(ap_tile))
		{
			_SuperLib_Log.Info("Build airport error msg: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_INFO);
			return null;
		}
		else
		{
			return ap_tile;
		}
	}

	return null;
}

/*static*/ function _SuperLib_Airport::GetIndustryAirportCandidateTiles(airport_type, industry_id)
{
	local radius = AIAirport.GetAirportCoverageRadius(airport_type);
	local tile_list = AIList();
	local accept_list = AITileList_IndustryAccepting(industry_id, radius);
	local produce_list = AITileList_IndustryProducing(industry_id, radius);
	if(accept_list.Count() > 0 && produce_list.Count() > 0)
	{
		tile_list = accept_list;
		tile_list.KeepList(produce_list);
	}
	else if(accept_list.Count() > 0)
	{
		tile_list = accept_list;
	}
	else
	{
		tile_list = produce_list
	}

	// Account for the size of the airport
	local additional_tiles = AITileList();
	local ap_w = AIAirport.GetAirportWidth(airport_type);
	local ap_h = AIAirport.GetAirportHeight(airport_type);
	local offset = AIMap.GetTileIndex(ap_w - 1, ap_h - 1);
	foreach(tile, _ in tile_list)
	{
		local ap_north = tile - offset;
		additional_tiles.AddRectangle(ap_north, tile);
	}
	tile_list.AddList(additional_tiles);


	// tile_list now is a list of tiles that can be used both for delivery of cargo and
	// getting cargo from the industry.

	return tile_list;
}

/*static*/ function _SuperLib_Airport::IndustryAirportCandidateScore(tile, airport_type, old_airport_noise = 0, old_airport_town = -1)
{
	// a negative number, used as score when construction is impossible
	local IMPOSSIBLE = -1;


	local noise_town = AIAirport.GetNearestTown(tile, airport_type);
	local noise_reduction = noise_town == old_airport_town? old_airport_noise : 0;
	local noise_buffert = AITown.GetAllowedNoise(noise_town) - (AIAirport.GetNoiseLevelIncrease(tile, airport_type) - noise_reduction);
	if(noise_buffert < 0)
	{
		// Too noisy
		return IMPOSSIBLE;
	}

	// Favor locations with lower noise contribution
	local result = AITown.GetAllowedNoise(noise_town) - noise_buffert;

	local tm = AITestMode();
	local can_build = false;
	{
		local am = AIAccounting();
		can_build = AIAirport.BuildAirport(tile, airport_type, AIStation.STATION_NEW);
		if(can_build) result += am.GetCosts();
		else result += 30000;
	}

	if(!can_build)
	{
		local last_error = AIError.GetLastError();
		switch(last_error)
		{
			case AIError.ERR_NOT_ENOUGH_CASH:
				return result + 100000;

			case AIError.ERR_AREA_NOT_CLEAR:
			case AIError.ERR_SITE_UNSUITABLE:
			case AIError.ERR_STATION_TOO_SPREAD_OUT:
			case AIError.ERR_LOCAL_AUTHORITY_REFUSES:
				return IMPOSSIBLE;

			case AIError.ERR_FLAT_LAND_REQUIRED:
			case AIError.ERR_LAND_SLOPED_WRONG: {
				local ap_w = AIAirport.GetAirportWidth(airport_type);
				local ap_h = AIAirport.GetAirportHeight(airport_type);
				local south_tile = _SuperLib_Tile.GetTileRelative(tile, ap_w, ap_h);
				local am = AIAccounting();
				AITile.LevelTiles(tile, south_tile);

				return result + am.GetCosts();
			}
		}

		// Unknown error
		result += 15000;

		// Objects in the way?
		local ap_tiles = AITileList();
		local ap_w = AIAirport.GetAirportWidth(airport_type);
		local ap_h = AIAirport.GetAirportHeight(airport_type);
		local south_tile = _SuperLib_Tile.GetTileRelative(tile, ap_w, ap_h);
		ap_tiles.AddRectangle(tile, south_tile);
		ap_tiles.Valuate(AITile.IsBuildable);
		local obstacle = false;
		foreach(_, buildable in ap_tiles)
		{
			if(!buildable)
			{
				obstacle = true;
				break;
			}
		}

		if(obstacle)
			return IMPOSSIBLE;


		// Can landscape?
		local am = AIAccounting();
		AITile.LevelTiles(tile, south_tile);

		result += am.GetCosts();
	}

	return result;
}

/*static*/ function _SuperLib_Airport::BuildAirportForIndustry(airport_type, industry_id)
{
	local tile_list = _SuperLib_Airport.GetIndustryAirportCandidateTiles(airport_type, industry_id);

	// tile_list now is a list of tiles that can be used both for delivery of cargo and
	// getting cargo from the industry.

	_SuperLib_Log.Info("tile count: " + tile_list.Count(), _SuperLib_Log.LVL_INFO);

	foreach(tile, _ in tile_list)
	{
		tile_list.SetValue(tile, _SuperLib_Airport.IndustryAirportCandidateScore(tile, airport_type, 0, -1));
	}
	tile_list.RemoveBelowValue(0); // remove impossible locations
	tile_list.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING); // best first

	local ap_w = AIAirport.GetAirportWidth(airport_type);
	local ap_h = AIAirport.GetAirportHeight(airport_type);

	foreach(tile, _ in tile_list)
	{
		// Try without landscaping
		if(AIAirport.BuildAirport(tile, airport_type, AIStation.STATION_NEW))
		{
			// return tile of successful airport
			return tile;
		}

		// Failed - try to landscape and try building again
		AITile.LevelTiles(tile, _SuperLib_Tile.GetTileRelative(tile, ap_w, ap_h));
		if(AIAirport.BuildAirport(tile, airport_type, AIStation.STATION_NEW))
		{
			// return tile of successful airport
			return tile;
		}
	}

	return null;
}

/*static*/ function _SuperLib_Airport::UpgradeAirportInTown(town_id, old_station_id, upgrade_type_list, accept_cargo = -1, produce_cargo = -1)
{
	// Don't waste time if station rating is too low
	if(!_SuperLib_Town.TownRatingAllowStationBuilding(town_id))
		return _SuperLib_Result.TOWN_RATING_TOO_LOW;

	local old_ap_tile = _SuperLib_Airport.GetAirportTile(old_station_id);
	local old_ap_type = AIAirport.GetAirportType(old_ap_tile);

	if(upgrade_type_list.len() == 1 && upgrade_type_list[0] == old_ap_type) // protect function against forever calling itself
	{
		_SuperLib_Log.Info("UpgradeAirportInTown - upgrade list only contain the current airport type => fail", _SuperLib_Log.LVL_DEBUG);
		return _SuperLib_Result.FAIL;
	}

	local curr_noise_contrib = AIMap.IsValidTile(old_ap_tile) ? AIAirport.GetNoiseLevelIncrease(old_ap_tile, old_ap_type) : 0;
	local removed_old_airport = false;
	local economy_problem = false;
	local town_rating_problem = false;
	local town_noise_problem = false;
	foreach(airport_type in upgrade_type_list)
	{
		if(AIAirport.GetPrice(airport_type) * 13 / 10 > AICompany.GetBankBalance(AICompany.COMPANY_SELF))
		{
			_SuperLib_Log.Info("Airport cost: " + (AIAirport.GetPrice(airport_type) * 13 / 10) + ". Money: " + AICompany.GetBankBalance(AICompany.COMPANY_SELF), _SuperLib_Log.LVL_DEBUG);
			economy_problem = true;
			continue;
		}

		economy_problem = false;

		local ap_w = AIAirport.GetAirportWidth(airport_type);
		local ap_h = AIAirport.GetAirportHeight(airport_type);
		local max_noise_add = AITown.GetAllowedNoise(town_id) + curr_noise_contrib;
		if (_SuperLib_Log.IsLevelAccepted(_SuperLib_Log.LVL_DEBUG)) {
			local town_name = AITown.GetName(town_id);
			if (town_name == null) town_name = "null";
			_SuperLib_Log.Info("Town allowed noise: " + AITown.GetAllowedNoise(town_id) + " curr ap noise: " + curr_noise_contrib + " (town: " + town_name + ")", _SuperLib_Log.LVL_DEBUG);
			_SuperLib_Log.Info("old tile: " + _SuperLib_Tile.GetTileString(old_ap_tile) + " old ap_type: " + old_ap_type, _SuperLib_Log.LVL_DEBUG);
		}

		local i = 0;
		local ap_tile = null;
		do
		{
			local find_ap_tile_result = _SuperLib_Airport.FindInTownAirportPlacement(town_id, ap_w, ap_h, airport_type, max_noise_add, accept_cargo, produce_cargo);
			if(find_ap_tile_result.money_error)
			{
				_SuperLib_Log.Info("UpgradeAirportInTown - economy problem", _SuperLib_Log.LVL_DEBUG);
				economy_problem = true;
				break;
			}
			else if(find_ap_tile_result.noise_error)
			{
				_SuperLib_Log.Info("UpgradeAirportInTown - noise problem", _SuperLib_Log.LVL_DEBUG);
				town_noise_problem = true;
				break;
			}
			else if(find_ap_tile_result.permanent_fail)
			{
				_SuperLib_Log.Info("UpgradeAirportInTown - permanent location problem for airport type", _SuperLib_Log.LVL_DEBUG);
				break;
			}

			ap_tile = find_ap_tile_result.tile;
			if(ap_tile != null)
			{
				_SuperLib_Helper.SetSign(ap_tile, "ap");
				_SuperLib_Tile.FlatternRect(ap_tile, ap_w, ap_h);
			}

			// Abort after 5 tries
			if(++i > 5)
				break;
		}
		while(ap_tile != null && AIMap.IsValidTile(ap_tile) && !_SuperLib_Tile.IsTileRectBuildableAndFlat(ap_tile, ap_w, ap_h))

		if(ap_tile != null && AIMap.IsValidTile(ap_tile))
		{
			// Abort if town rating is too low
			if(!_SuperLib_Town.TownRatingAllowStationBuilding(town_id))
			{
				town_rating_problem = true;
				break;
			}

			// Abort if money is too low
			if(AIAirport.GetPrice(airport_type) * 12 / 10 > AICompany.GetBankBalance(AICompany.COMPANY_SELF))
			{
				_SuperLib_Log.Info("Airport cost: " + (AIAirport.GetPrice(airport_type) * 12 / 10) + ". Money: " + AICompany.GetBankBalance(AICompany.COMPANY_SELF), _SuperLib_Log.LVL_DEBUG);
				economy_problem = true;
				continue; // try next airport type
			}

			// Remove old
			if(AIAirport.IsAirportTile(old_ap_tile))
			{
				{
					local i = 0;
					local tm = AITestMode();
					while(!AITile.DemolishTile(ap_tile) && i < 10000)
					{
						AIController.Sleep(10);
						++i;
					}
				}
				if(AITile.DemolishTile(old_ap_tile))
					removed_old_airport = true;
				else
					return _SuperLib_Result.FAIL;
			}

			// Build airport
			local airport_status = AIAirport.BuildAirport(ap_tile, airport_type, old_station_id);

			if(!AIAirport.IsAirportTile(ap_tile))
			{
				_SuperLib_Log.Info("Build airport error msg: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_INFO);
				continue; // try next airport type
			}
			else
			{
				return _SuperLib_Result.SUCCESS;
			}
		}
		else
		{
			_SuperLib_Log.Info("UpgradeAirportInTown - could not find a location", _SuperLib_Log.LVL_DEBUG);
		}
	}

	// failed to upgrade airport
	if(removed_old_airport)
	{
		local try_rebuild = _SuperLib_Airport.UpgradeAirportInTown(town_id, old_station_id, [old_ap_type], accept_cargo, produce_cargo);
		if(_SuperLib_Result.IsFail(try_rebuild))
		{
			// failed to rebuild old airport
			return _SuperLib_Result.REBUILD_FAILED;
		}
		else
		{
			return _SuperLib_Result.SUCCESS;
		}
	}

	// failed to upgrade airport, but airport has not been removed

	if(town_noise_problem)
		return _SuperLib_Result.TOWN_NOISE_ACCEPTANCE_TOO_LOW;

	if(town_rating_problem)
		return _SuperLib_Result.TOWN_RATING_TOO_LOW;

	if(economy_problem)
		return _SuperLib_Result.MONEY_TOO_LOW;

	return _SuperLib_Result.FAIL;
}

/*static*/ function _SuperLib_Airport::UpgradeAirportForIndustry(industry_id, old_station_id, upgrade_type_list, accept_cargo = -1, produce_cargo = -1)
{
	_SuperLib_Log.Info("Airport.UpgradeAirportForIndustry", _SuperLib_Log.LVL_DEBUG);

	local old_ap_tile = _SuperLib_Airport.GetAirportTile(old_station_id);
	local old_ap_type = AIAirport.GetAirportType(old_ap_tile);
	local old_ap_price = AIAirport.GetPrice(old_ap_type);

	if(upgrade_type_list.len() == 1 && upgrade_type_list[0] == old_ap_type) // protect function against forever calling itself
	{
		_SuperLib_Log.Info("UpgradeAirportForIndustry - upgrade list only contain the current airport type => fail", _SuperLib_Log.LVL_DEBUG);
		return _SuperLib_Result.FAIL;
	}

	local curr_noise_contrib = AIAirport.GetNoiseLevelIncrease(old_ap_tile, old_ap_type);
	local curr_noise_contrib_town = AIAirport.GetNearestTown(old_ap_tile, old_ap_type);
	local removed_old_airport = false;
	local economy_problem = false;
	local town_rating_problem = false;
	local town_noise_problem = false;
	foreach(airport_type in upgrade_type_list)
	{
		local new_ap_price = AIAirport.GetPrice(airport_type);
		local cost = removed_old_airport? new_ap_price : new_ap_price * 15 / 10; // if we have removed the old AP, be more desperate
		if(cost > AICompany.GetBankBalance(AICompany.COMPANY_SELF))
		{
			_SuperLib_Log.Info("Airport (evaluated) cost: " + cost + ". Money: " + AICompany.GetBankBalance(AICompany.COMPANY_SELF), _SuperLib_Log.LVL_DEBUG);
			economy_problem = true;
			continue;
		}

		economy_problem = false;

		local ap_w = AIAirport.GetAirportWidth(airport_type);
		local ap_h = AIAirport.GetAirportHeight(airport_type);

		//local max_noise_add = AITown.GetAllowedNoise(town_id) + curr_noise_contrib;

		local tile_list = _SuperLib_Airport.GetIndustryAirportCandidateTiles(airport_type, industry_id);

		_SuperLib_Log.Info("UpgradeAirportForIndustry - " + tile_list.Count() + " locations to try", _SuperLib_Log.LVL_DEBUG);

		foreach(tile, _ in tile_list)
		{
			tile_list.SetValue(tile, _SuperLib_Airport.IndustryAirportCandidateScore(tile, airport_type, 0, -1));
		}
		tile_list.RemoveBelowValue(0); // remove impossible locations
		tile_list.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING); // best first

		_SuperLib_Log.Info("UpgradeAirportForIndustry - " + tile_list.Count() + " locations after removal of impossible locations", _SuperLib_Log.LVL_DEBUG);

		local ap_w = AIAirport.GetAirportWidth(airport_type);
		local ap_h = AIAirport.GetAirportHeight(airport_type);

		// Is there a landscaping free location?
		local landscape_free_location = -1;
		{
			local tm = AITestMode();
			foreach(tile, _ in tile_list)
			{
				if(AIAirport.BuildAirport(tile, airport_type, AIStation.STATION_NEW))
				{
					landscape_free_location = tile;
				}
			}
		}

		if(landscape_free_location)
		{
			if(!AIAirport.IsAirportTile(old_ap_tile)) // don't destroy a non-ap tile
				return _SuperLib_Result.FAIL;

			AITile.DemolishTile(old_ap_tile);
			removed_old_airport = true;

			if(AIAirport.BuildAirport(landscape_free_location, airport_type, old_station_id))
				return _SuperLib_Result.SUCCESS;

			// upgrade failed - try to rebuild old AP
			_SuperLib_Log.Info("UpgradeAirportForIndustry: upgrade at landscaping free location failed - try to rebuild old AP", _SuperLib_Log.LVL_SUB_DECISIONS);
			if(AIAirport.BuildAirport(old_ap_tile, old_ap_type, old_station_id))
				return _SuperLib_Result.FAIL;

			return _SuperLib_Result.REBUILD_FAILED;
		}
		else
		{
			// need to remove old airport first
			if(!AIAirport.IsAirportTile(old_ap_tile)) // don't destroy a non-ap tile
				return _SuperLib_Result.FAIL;

			AITile.DemolishTile(old_ap_tile);
			removed_old_airport = true;

			// try to landscape
			foreach(tile in tile_list)
			{
				AITile.LevelTiles(tile, _SuperLib_Tile.GetTileRelative(tile, ap_w, ap_h));

				// Try to build airport
				if(AIAirport.BuildAirport(landscape_free_location, airport_type, old_station_id))
					return _SuperLib_Result.SUCCESS;

				local error = AIError.GetLastError();
				economy_problem = error == AIError.ERR_NOT_ENOUGH_CASH;
				town_rating_problem = error = AIError.ERR_LOCAL_AUTHORITY_REFUSES;

				if(AICompany.GetBankBalance(AICompany.COMPANY_SELF) * 12 / 10 < old_ap_price)
				{
					// Getting low in money => rebuild old AP and stop before
					// we risk losing the airport

					if(AIAirport.BuildAirport(old_ap_tile, old_ap_type, old_station_id))
						return _SuperLib_Result.FAIL;

					// failed to re-build old AP
					break; // go to next AP type and hope we can build it
				}
			}
		}
	}

	// failed to upgrade airport
	if(removed_old_airport)
	{
		local try_rebuild = _SuperLib_Airport.UpgradeAirportForIndustry(industry_id, old_station_id, [old_ap_type], accept_cargo, produce_cargo);
		if(_SuperLib_Result.IsFail(try_rebuild))
		{
			// failed to rebuild old airport
			return _SuperLib_Result.REBUILD_FAILED;
		}
		else
		{
			return _SuperLib_Result.SUCCESS;
		}
	}

	// failed to upgrade airport, but airport has not been removed

	if(town_noise_problem)
		return _SuperLib_Result.TOWN_NOISE_ACCEPTANCE_TOO_LOW;

	if(town_rating_problem)
		return _SuperLib_Result.TOWN_RATING_TOO_LOW;

	if(economy_problem)
		return _SuperLib_Result.MONEY_TOO_LOW;

	return _SuperLib_Result.FAIL;
}

/*static*/ function _SuperLib_Airport::FindInTownAirportPlacement(town_id, station_w, station_h, airport_type, maximum_noise, accept_cargo, produce_cargo)
{
	_SuperLib_Log.Info("FindInTownAirportPlacement(" + town_id + ", " + station_w + ", " + station_h + ", " + airport_type + ", " + maximum_noise + ", " + accept_cargo + ", " + produce_cargo + ")", _SuperLib_Log.LVL_DEBUG);
	local town_tiles = _SuperLib_Tile.GetTownTiles(town_id);

	// with respect to station sign
	town_tiles.Valuate(AITile.GetClosestTown);
	town_tiles.KeepValue(town_id);

	if(maximum_noise != -1) {
		// keep only tiles where the town noise influence would match town_id.
		town_tiles.Valuate(AIAirport.GetNearestTown, airport_type);
		town_tiles.KeepValue(town_id);
	}

	if(town_tiles.IsEmpty())
	{
		_SuperLib_Log.Info("FindInTownAirportPlacement - no tile is closest to town", _SuperLib_Log.LVL_DEBUG);
		return { permanent_fail = true, money_error = false, noise_error = false, tile = null };
	}

	if(accept_cargo != -1)
	{
		town_tiles.Valuate(_SuperLib_Airport.WillAirportAcceptCargo, airport_type, accept_cargo);
		town_tiles.KeepValue(1);
	}

	if(produce_cargo != -1)
	{
		town_tiles.Valuate(_SuperLib_Airport.WillAirportProduceCargo, airport_type, produce_cargo);
		town_tiles.KeepValue(1);
	}

	if(town_tiles.IsEmpty())
	{
		_SuperLib_Log.Info("FindInTownAirportPlacement - no tile provide requested cargo", _SuperLib_Log.LVL_DEBUG);
		return { permanent_fail = true, money_error = false, noise_error = false, tile = null };
	}

	if(maximum_noise != -1)
	{
		town_tiles.Valuate(AIAirport.GetNoiseLevelIncrease, airport_type);
		town_tiles.KeepBelowValue(maximum_noise + 1);
	}

	if(town_tiles.IsEmpty())
	{
		_SuperLib_Log.Info("FindInTownAirportPlacement - no tile can take new noise level", _SuperLib_Log.LVL_DEBUG);
		return { permanent_fail = true, money_error = false, noise_error = true, tile = null };
	}

	_SuperLib_Helper.Valuate(town_tiles, _SuperLib_Tile.CostToFlattern, station_w, station_h);
	town_tiles.RemoveValue(-1);
	town_tiles.KeepBelowValue(AICompany.GetBankBalance(AICompany.COMPANY_SELF) / 10);

	//town_tiles.Valuate(_SuperLib_Tile.IsTileRectBuildableAndFlat, station_w, station_h);
	//town_tiles.KeepValue(1);

	if(town_tiles.IsEmpty())
		return { permanent_fail = false, money_error = true, noise_error = false, tile = null };

	local min_max_equal = false;
	local sort_order = null;
	if(accept_cargo != -1)
	{
		// find location with best coverage
		town_tiles.Valuate(_SuperLib_Airport.GetAirportCargoAcceptance, airport_type, accept_cargo);

		town_tiles.Sort(AIList.SORT_BY_VALUE, true);
		local min = town_tiles.GetValue(town_tiles.Begin());
		town_tiles.Sort(AIList.SORT_BY_VALUE, false); // sort highest first
		local max = town_tiles.GetValue(town_tiles.Begin());
		sort_order = false; // highest first

		min_max_equal = min == max;
	}
	else if(produce_cargo != -1)
	{
		// find location with best coverage
		town_tiles.Valuate(_SuperLib_Airport.GetAirportCargoProduction, airport_type, produce_cargo);

		town_tiles.Sort(AIList.SORT_BY_VALUE, true);
		local min = town_tiles.GetValue(town_tiles.Begin());
		town_tiles.Sort(AIList.SORT_BY_VALUE, false); // sort highest first
		local max = town_tiles.GetValue(town_tiles.Begin());
		sort_order = false; // highest first

		min_max_equal = min == max;
	}

	// if no cargo accept/produce or all tiles give equal acceptance/production, place near/far from town
	if((accept_cargo == -1 && produce_cargo == -1) || min_max_equal)
	{
		// place near town
		town_tiles.Valuate(_SuperLib_Airport.AirportCenterDistanceManhatanTo, airport_type, AITown.GetLocation(town_id));

		// if all tiles give equal cargo acceptance/production, place near town.
		if(min_max_equal)
			sort_order = true; // sort smallest first
		else // if no cargo acceptance/production is needed, place far away
			sort_order = false; // sort largest first
	}

	// apply some randomization

	town_tiles.Sort(AIList.SORT_BY_ITEM, true); // sort by item to not cause (almost) infinite loop due to randomization of sort order
	foreach(tile, val in town_tiles)
	{
		if(_SuperLib_Tile.IsTileRectBuildableAndFlat(tile, station_w, station_h))
			town_tiles.SetValue(tile, (AIBase.RandRange(3) - 1) + val - 2) // give two in bonus
		else
			town_tiles.SetValue(tile, (AIBase.RandRange(3) - 1) + val);
	}
	town_tiles.Sort(AIList.SORT_BY_VALUE, sort_order); // sort again by value

	return { permanent_fail = false, money_error = false, noise_error = false, tile = town_tiles.Begin() };
}

// Loops through all hangars in an airport and retrive the aircrafts in them
/*static*/ function _SuperLib_Airport::GetAircraftInHangar(station_id)
{
	local hangar_aircraft_list = AIList();

	// Loop through all hangars of the airport
	local airport_tiles = AITileList_StationType(station_id, AIStation.STATION_AIRPORT);
	airport_tiles.Valuate(AIAirport.IsHangarTile);
	airport_tiles.KeepValue(1);

	foreach(hangar_tile in airport_tiles)
	{
		// Get a list of all vehicles in current hangar
		local vehicle_list = AIVehicleList_Depot(hangar_tile);

		// Add those vehicles to the list of all airplanes in hangars of this airport
		hangar_aircraft_list.AddList(vehicle_list);
	}

	return hangar_aircraft_list;
}
/*static*/ function _SuperLib_Airport::GetAircraftsInHangar(station_id)
{
	return _SuperLib_Airport.GetAircraftInHangar(station_id);
}

/*static*/ function _SuperLib_Airport::IsSmallAirport(station_id)
{
	local airport_type = AIAirport.GetAirportType(_SuperLib_Airport.GetAirportTile(station_id));
	return _SuperLib_Airport.IsSmallAirportType(airport_type);
}

/*static*/ function _SuperLib_Airport::IsSmallAirportType(airport_type)
{
	return airport_type == AIAirport.AT_SMALL || airport_type == AIAirport.AT_COMMUTER;
}

// returns the station location for current order. If current order is the hangar, return the airport location.
function _SuperLib_Airport_Private_GetCurrentOrderDestinationStationSignLocation(vehicle_id)
{
	local loc = _SuperLib_Order.GetCurrentOrderDestination(vehicle_id);

	// change loc tile to the station sign location
	loc = AIStation.GetLocation(AIStation.GetStationID(loc));

	return loc;
}

/*static*/ function _SuperLib_Airport::GetNumNonStopedAircraftInAirportDepot(station_id)
{
	local hangar_vehicles = _SuperLib_Airport.GetAircraftInHangar(station_id);

	hangar_vehicles.Valuate(AIVehicle.IsStoppedInDepot);
	hangar_vehicles.KeepValue(0);

	return hangar_vehicles.Count();
}

/*static*/ function _SuperLib_Airport::GetNumNonStopedAircraftsInAirportDepot(station_id)
{
	return _SuperLib_Airport.GetNumNonStopedAircraftInAirportDepot(station_id);
}

/*static*/ function _SuperLib_Airport::GetNumAircraftsInAirportQueue(station_id, filter_aircraft_destination = true)
{
	// aircrafts
	local station_vehicle_list = AIVehicleList_Station(station_id);
	station_vehicle_list.Valuate(AIVehicle.GetVehicleType);
	station_vehicle_list.KeepValue(AIVehicle.VT_AIR);

	// get airport tile
	local airport_tile = _SuperLib_Airport.GetAirportTile(station_id);

	// get airport holding rectangle
	local holding_rect = AITileList();

	switch(AIAirport.GetAirportType(airport_tile))
	{
		case AIAirport.AT_SMALL:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, -2, 0), _SuperLib_Tile.GetTileRelative(airport_tile, 17, 12));
			holding_rect.RemoveRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, 1, 1), _SuperLib_Tile.GetTileRelative(airport_tile, 3, 2)); // remove non-holding airport tiles
			break;

		case AIAirport.AT_COMMUTER:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, -2, 0), _SuperLib_Tile.GetTileRelative(airport_tile, 14, 9));
			holding_rect.RemoveRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, 1, 1), _SuperLib_Tile.GetTileRelative(airport_tile, 4, 3)); // remove non-holding airport tiles
			break;

		case AIAirport.AT_LARGE:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, 9, 0), _SuperLib_Tile.GetTileRelative(airport_tile, 17, 5));
			break;

		case AIAirport.AT_METROPOLITAN:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, -2, 0), _SuperLib_Tile.GetTileRelative(airport_tile, 17, 12));
			holding_rect.RemoveRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, 1, 1), _SuperLib_Tile.GetTileRelative(airport_tile, 5, 5)); // remove non-holding airport tiles
			break;

		case AIAirport.AT_INTERNATIONAL:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, -2, 0), _SuperLib_Tile.GetTileRelative(airport_tile, 19, 13));
			holding_rect.RemoveRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, 1, 1), _SuperLib_Tile.GetTileRelative(airport_tile, 6, 6)); // remove non-holding airport tiles
			break;

		case AIAirport.AT_INTERCON:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, -13, -11), _SuperLib_Tile.GetTileRelative(airport_tile, 19, 21));
			holding_rect.RemoveRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, 0, 0), _SuperLib_Tile.GetTileRelative(airport_tile, 8, 10)); // remove non-holding airport tiles
			break;

		case AIAirport.AT_HELIPORT:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, -2, -4), _SuperLib_Tile.GetTileRelative(airport_tile, 4, 3));
			holding_rect.RemoveTile(_SuperLib_Tile.GetTileRelative(airport_tile, 0, 0)); // remove non-holding airport tiles (landing tile)
			break;

		case AIAirport.AT_HELIDEPOT:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, -1, -4), _SuperLib_Tile.GetTileRelative(airport_tile, 3, 1));
			holding_rect.RemoveTile(_SuperLib_Tile.GetTileRelative(airport_tile, 0, 1)); // remove non-holding airport tiles (landing tile)
			break;

		case AIAirport.AT_HELISTATION:
			holding_rect.AddRectangle(_SuperLib_Tile.GetTileRelative(airport_tile, 4, -2), _SuperLib_Tile.GetTileRelative(airport_tile, 9, 1));
			break;

		default:
			// Unknown airport type -> crash the AI
			_SuperLib_Log.Warning("Unknown airport type: " + AIAirport.GetAirportType(airport_tile), _SuperLib_Log.LVL_INFO);
			KABOOOOOM_unknown_airport_type();
	}

	station_vehicle_list.Valuate(_SuperLib_Vehicle.VehicleIsWithinTileList, holding_rect);
	station_vehicle_list.KeepValue(1);

	// Only keep vehicles that are on the way to the airport
	if(filter_aircraft_destination)
	{
		station_vehicle_list.Valuate(_SuperLib_Airport_Private_GetCurrentOrderDestinationStationSignLocation);
		station_vehicle_list.KeepValue(AIStation.GetLocation(station_id));
	}

	// remove vehicles that are in a depot (the right depot of international would else give false positive
	station_vehicle_list.Valuate(AIVehicle.IsInDepot);
	station_vehicle_list.KeepValue(0);

	return station_vehicle_list.Count();
}
/*static*/ function _SuperLib_Airport::GetNumAircraftInAirportQueue(station_id, filter_aircraft_destination = true)
{
	return _SuperLib_Airport.GetNumAircraftsInAirportQueue(station_id, filter_aircraft_destination);
}

/*static*/ function _SuperLib_Airport::AirportCenterDistanceManhatanTo(airport_tile, airport_type, other_tile)
{
	local ap_w = AIAirport.GetAirportWidth(airport_type);
	local ap_h = AIAirport.GetAirportHeight(airport_type);

	local ap_center = _SuperLib_Tile.GetTileRelative(airport_tile, ap_w/2, ap_h/2);

	return AIMap.DistanceManhattan(ap_center, other_tile);
}
