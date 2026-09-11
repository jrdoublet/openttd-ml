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

class _SuperLib_Engine
{
	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Engine info                                                     //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function GetRequiredStationType(engine);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Travel time                                                     //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function GetFullSpeedTraveltime(engine, distance);

	static function GetStationToStationAircraftTravelTime(engine, station1_id, station2_id);
	static function GetAircraftTravelTime(engine, distance, station1_type, station2_type);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Engine selection                                                //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* vehicle_type = AIVehicle::VehicleType constant
	 */
	static function DoesEngineExistForCargo(cargo_id, vehicle_type = -1, no_trams = true, no_articulated = true, only_small_aircrafts = false);

	/* The function used by PAXLink for engine selection.
	 * It always use the PAX cargo and is mainly intended for buses and aircrafts.
	 */
	static function GetEngine_PAXLink(needed_capacity, vehicle_type, only_small_aircrafts = false);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Route distance selection                                        //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function GetIdealTransportDistance(engine_id, cargo_id, airport_type = -1);
}

function _SuperLib_Engine::GetRequiredStationType(engine)
{
	// On error (unknown station type), the code breaks out of the switch blocks and
	// the code at the bottom of the function is ran to display a warning and return null
	switch(AIEngine.GetVehicleType(engine))
	{
		case AIVehicle.VT_ROAD:
			switch(AIRoad.GetRoadVehicleTypeForCargo(AIEngine.GetCargoType(engine)))
			{
				case AIRoad.ROADVEHTYPE_BUS:
					return AIStation.STATION_BUS_STOP;
				case AIRoad.ROADVEHTYPE_TRUCK:
					return AIStation.STATION_TRUCK_STOP;
				default:
					break;
			}
			break;

		case AIVehicle.VT_AIR:
			return AIStation.STATION_AIRPORT;

		case AIVehicle.VT_RAIL:
			return AIStation.STATION_TRAIN;

		case AIVehicle.VT_WATER:
			return AIStation.STATION_DOCK;

		default:
			break;
	}

	local engine_name = AIEngine.GetName(engine);
	if (engine_name == null) engine_name = "null";
	_SuperLib_Log.Warning("Can't figure out which station type that corresponds to engine " + engine_name, _SuperLib_Log.LVL_INFO);
	return null;
}

function _SuperLib_Engine::DoesEngineExistForCargo(cargo_id, vehicle_type = -1, no_trams = true, no_articulated = true, only_small_aircrafts = false)
{
	local engine_list = AIEngineList(vehicle_type);

	// Only keep engines that can cary the given cargo
	engine_list.Valuate(AIEngine.CanRefitCargo, cargo_id);
	engine_list.KeepValue(1);

	if(vehicle_type == AIVehicle.VT_ROAD)
	{
		if(no_trams)
		{
			// filter out trams
			engine_list.Valuate(AIEngine.GetRoadType);
			engine_list.KeepValue(AIRoad.ROADTYPE_ROAD);
		}
		if(no_articulated)
		{
			// filter out articulated vehicles
			engine_list.Valuate(AIEngine.IsArticulated)
			engine_list.KeepValue(0);
		}
	}

	if(vehicle_type == AIVehicle.VT_AIR && only_small_aircrafts)
	{
		engine_list.Valuate(AIEngine.GetPlaneType);
		engine_list.RemoveValue(AIAirport.PT_BIG_PLANE);
	}

	return !engine_list.IsEmpty();
}


function _SuperLib_Engine::GetFullSpeedTraveltime(engine, distance)
{
	// X km/h => X/27 tiles/day

	/* Multiply by this from start and then remove it at the end in order to
	 * not lose to much significance in the calculation process.
	 *
	 * On 100 km/h the tile/day speed becomes 3.7, which would become just
	 * 3 in the integer conversion which would be loosing to much detail.
	 */
	local MULTI = 50;

	local km_h_speed = AIEngine.GetMaxSpeed(engine) * MULTI;
	local tile_speed = km_h_speed / 27;

	local travel_time_days = distance * MULTI / tile_speed;

	return travel_time_days;
}

function _SuperLib_Engine::GetStationToStationAircraftTravelTime(engine, station1_id, station2_id)
{
	local ap_tiles = [_SuperLib_Airport.GetAirportTile(station1_id), _SuperLib_Airport.GetAirportTile(station2_id)];
	local distance = AIMap.DistanceManhattan(ap_tiles[0], ap_tiles[1]);

	return _SuperLib_Engine.GetAircraftTravelTime(engine, distance, AIAirport.GetAirportType(ap_tiles[0]), AIAirport.GetAirportType(ap_tiles[1]));
}

function _SuperLib_Engine::GetAircraftTravelTime(engine, distance, station1_type, station2_type)
{
	local ap_types = [station1_type, station2_type];

	local travel_time = 0;

	// Add some time for each airport depending on the airport type
	foreach(ap_type in ap_types)
	{
		switch(ap_type)
		{
			// These values have just been guessed. Some research is needed to find better values. Or at least confirm or reject the guessed values.
			case AIAirport.AT_SMALL:
				travel_time += 10;
				break;

			case AIAirport.AT_COMMUTER:
				travel_time += 5;
				break;

			case AIAirport.AT_LARGE:
				travel_time += 10;
				break;

			case AIAirport.AT_METROPOLITAN:
				travel_time += 8;
				break;

			case AIAirport.AT_INTERNATIONAL:
				travel_time += 7;
				break;

			case AIAirport.AT_INTERCON:
				travel_time += 7;
				break;

			default:
				// Unknown airport type -> crash the AI
				KABOOOOOM_unknown_airport_type();
		}
	}

	// Add the time it takes to fly between the airports
	travel_time += _SuperLib_Engine.GetFullSpeedTraveltime(engine, distance);

	return travel_time;
}

/* This function calculates a score for the PAXLink engine selection function
 */
function _SuperLib_Private_GetBusEngineScoreValuator(engine_id, needed_capacity, max_money)
{
	local score = 0;

	// if can afford engine
	if(AIEngine.GetPrice(engine_id) < max_money)
		score += 1000;

	// If we need 20 capacity, then only those 20 should share the costs.
	local tot_pax_cap = AIEngine.GetCapacity(engine_id);
	local count_pax = _SuperLib_Helper.Min(tot_pax_cap, needed_capacity)

	local price = AIEngine.GetPrice(engine_id);
	local running_cost = AIEngine.GetRunningCost(engine_id);

	// Handle the case when engine capacity is zero or
	// needed_capacity is zero, so that division by zero does not occur.
	local price_per_pax = 1000;
	local running_cost_per_pax = 1000;
	if(count_pax > 0)
	{
		price_per_pax = price / count_pax;
		running_cost_per_pax = running_cost / count_pax;
	}



	score -= running_cost_per_pax * 3;

	score -= price_per_pax

	// some hacks to valuate capacity and speed more if needed capacity is really high
	local pax_factor = 2;
	local speed_factor = 2;
	if(needed_capacity > 200)
		pax_factor = 4;
	if(needed_capacity > 800)
	{
		speed_factor = 4;
		pax_factor = 8;
	}

	//pax_factor *= 2;
	speed_factor *= 2;

	score += tot_pax_cap * pax_factor; // while only the needed pax cap shares the cost, a bigger bus get a score bonus even if the extra space isn't needed for now.

	score += AIEngine.GetMaxSpeed(engine_id) * speed_factor;

	score += AIBase.RandRange(100);

	if(AIEngine.GetReliability(engine_id) > 50)
		score += AIEngine.GetReliability(engine_id) * 2;

	return score;
}

function _SuperLib_Engine::GetEngine_PAXLink(needed_capacity, vehicle_type, only_small_aircrafts = false)
{
	local engine_list = AIEngineList(vehicle_type);

	// Only keep non-articulated
	if(vehicle_type == AIVehicle.VT_ROAD)
	{
		// filter out articulated vehicles
		engine_list.Valuate(AIEngine.IsArticulated)
		engine_list.KeepValue(0);

		// filter out trams
		engine_list.Valuate(AIEngine.GetRoadType);
		engine_list.KeepValue(AIRoad.ROADTYPE_ROAD);
	}
	else if(vehicle_type == AIVehicle.VT_AIR)
	{
		if(only_small_aircrafts)
		{
			engine_list.Valuate(AIEngine.GetPlaneType);
			engine_list.RemoveValue(AIAirport.PT_BIG_PLANE);
		}
	}

	// Don't buy zero-price vehicles. These are often there for eye candy etc.
	engine_list.Valuate(AIEngine.GetPrice);
	engine_list.RemoveValue(0);
	engine_list.Valuate(AIEngine.GetRunningCost);
	engine_list.RemoveValue(0);

	engine_list.Valuate(AIEngine.CanRefitCargo, _SuperLib_Helper.GetPAXCargo());
	engine_list.KeepValue(1);

	if(_SuperLib_Log.IsLevelAccepted(_SuperLib_Log.LVL_DEBUG))
	{
		foreach(i, _ in engine_list)
		{
			local engine_name = AIEngine.GetName(i);
			if (engine_name == null) engine_name = "null";
			_SuperLib_Log.Info("Engine name: " + engine_name, _SuperLib_Log.LVL_DEBUG);
		}
	}

	local max_money = _SuperLib_Money.GetMaxSpendingAmount()
	engine_list.Valuate(_SuperLib_Private_GetBusEngineScoreValuator, needed_capacity, max_money);
	engine_list.Sort(AIList.SORT_BY_VALUE, false); // highest first
	engine_list.KeepTop(1);
	return engine_list.Begin();
}

/*static*/ function _SuperLib_Engine::GetIdealTransportDistance(engine_id, cargo_id, airport_type = -1)
{
	local vt_type = AIEngine.GetVehicleType(engine_id);

	// Check if -1 airport is given and in this case try to find a airport type to use
	if (vt_type == AIVehicle.VT_AIR && airport_type == -1)
	{
		airport_type = _SuperLib_Airport.GetLastAvailableAirportType(engine_id);

		if (!AIAirport.IsAirportInformationAvailable(airport_type))
		{
			_SuperLib_Log.Info("ap type: " + airport_type, _SuperLib_Log.LVL_INFO);
			_SuperLib_Log.Info("SuperLib::Engine::GetIdealTransportDistance: Invalid airport type - can't find available airport type for engine", _SuperLib_Log.LVL_INFO);
			return -1;
		}
	}

	local M = 100;

	local curr_distance = 100;
	local prev_distance = -1;
	local step_size = 50;
	local prev_value = -1;
	local curr_value = -1;
	// TODO: search function to move towards optimum

	local i = -1;

	while(prev_distance == -1 ||
			(++i < 10 &&                                // max 10 iterations
			abs(curr_distance - prev_distance) >= 5))   // stop if distance change was smaller than 5 tiles
	{
		_SuperLib_Log.Info("LOOP", _SuperLib_Log.LVL_DEBUG);
		_SuperLib_Log.Info("  prev_distance" + prev_distance + " | curr_distance: " + curr_distance, _SuperLib_Log.LVL_DEBUG);

		local travel_time = -1;
		local travel_time_delta = -1;
		local delta = max(5, curr_distance / 10);
		local distance_delta = curr_distance + delta;
		switch(vt_type)
		{
			case AIVehicle.VT_AIR:
				travel_time = _SuperLib_Engine.GetAircraftTravelTime(engine_id, curr_distance, airport_type, airport_type);
				travel_time_delta = _SuperLib_Engine.GetAircraftTravelTime(engine_id, distance_delta, airport_type, airport_type);

				break;

			case AIVehicle.VT_ROAD:
			case AIVehicle.VT_RAIL:
			case AIVehicle.VT_WATER:
				// Assume 2.5 days in station delay per station => 5 days in total
				// and a 10% delay due to curves etc.

				travel_time = (_SuperLib_Engine.GetFullSpeedTraveltime(engine_id, curr_distance) * 9) / 10 + 5;
				travel_time_delta = (_SuperLib_Engine.GetFullSpeedTraveltime(engine_id, distance_delta) * 9) / 10 + 5;
		}

		local value = AICargo.GetCargoIncome(cargo_id, curr_distance, travel_time) * M / travel_time;
		local value_delta = AICargo.GetCargoIncome(cargo_id, distance_delta, travel_time_delta) * M / travel_time;

		// Get movement direction
		local k = M * (value_delta - value) / delta;

		// Get new distance
		local change = curr_distance * k * 3 / M;
		if( abs(change) > 500) // don't change more than 500 in distance
		{
			change = k > 0? 500 : -500;
		}
		local new_distance = curr_distance + change;
		//local new_distance = curr_distance + (k > 0? step_size : -step_size);

		_SuperLib_Log.Info("  tt: " + travel_time + " | tt delta: " + travel_time_delta, _SuperLib_Log.LVL_DEBUG);
		_SuperLib_Log.Info("  value: " + value + " | value delta: " + value_delta, _SuperLib_Log.LVL_DEBUG);
		_SuperLib_Log.Info("  k: " + k + " | New distance: " + new_distance, _SuperLib_Log.LVL_DEBUG);

		prev_distance = curr_distance;
		curr_distance = new_distance;
	}

	return curr_distance;
}
