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

class _SuperLib_Vehicle
{
	/*
	 * Get the vehicle limit of a given vehicle type. If the vehicle
	 * type has been disabled for AI players, this function will report
	 * zero even if the limit is > 0.
	 *
	 * If the AI Settings of this AI have disabled the vehicle type, this
	 * function will also report zero. See the IsVehicleTypeDisabledByAISettings
	 * function for further details.
	 */
	static function GetVehicleLimit(vehicle_type);

	/*
	 * Gives the number of vehicles of given
	 * vehicle type that can be built before
	 * reaching the limit.
	 *
	 * If the AI has a higher number of vehicls
	 * than the limit, a negative value is
	 * returned.
	 *
	 * If the AI Settings of this AI have
	 * disabled the vehicle type, this function
	 * will also report zero. See the
	 * IsVehicleTypeDisabledByAISettings
	 * function for further details.
	 */
	static function GetVehiclesLeft(vehicle_type);

	/*
	 * This function reads the AI settings:
	 * - use_rvs
	 * - use_planes
	 * - use_trains
	 * - use_ships
	 *
	 * and return true if the setting is not defined in info.nut or
	 *
	 * Sample code for your info.nut:
	 *
	 *     AddSetting({name = "use_rvs", description = "Enable road vehicles", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = AICONFIG_BOOLEAN | AICONFIG_INGAME});
	 *     AddSetting({name = "use_planes", description = "Enable aircrafts", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = AICONFIG_BOOLEAN | AICONFIG_INGAME});
	 *     AddSetting({name = "use_trains", description = "Enable trains", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = AICONFIG_BOOLEAN | AICONFIG_INGAME});
	 *     AddSetting({name = "use_ships", description = "Enable ships", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = AICONFIG_BOOLEAN | AICONFIG_INGAME});
	 *
	 *
	 * If you want to use other setting names, a way of overriding
	 * those will need to be added to SuperLib. To increase the likelihood
	 * of that, you should inform about your need in the SuperLib thread.
	 */
	static function IsVehicleTypeDisabledByAISettings(vehicle_type);

	/*
	 * Returns a string that explains by which setting a vehicle type has
	 * been disabled (to display for users / debug).
	 *
	 * Only one setting is returned if several settings disable a particular
	 * vehicle type. If given vehicle type is not disabled, null is returned.
	 */
	static function GetVehicleTypeDisabledBySettingString(vehicle_type);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Vehicle Info                                                    //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function GetProfitThisAndLastYear(vehicle_id);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Where are the vehicles?                                         //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function IsVehicleAtStation(vehicle_id, station_id);

	static function HasTileListVehiclesOnIt(tile_rect, vehicle_type);
	static function VehicleIsWithinTileList(vehicle_id, tile_list);
	static function GetVehiclesAtTile(tile);
	static function GetVehicleLocations();

	static function GetVehicleCargoType(vehicle_id);

	// vehicle_type == null => include all vehicle types
	static function GetCrashedVehicleLocations(vehicle_type = null);
	// vehicle_type == null => include all vehicle types
	static function GetNonCrashedVehicleLocations(vehicle_type = null);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Sell vehicles                                                   //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * This function trys hard to ensure that a vehicle that should be sold
	 * really get sent to depot.
	 *
	 * Note that for GameScript, this function requires OpenTTD r24??? or
	 * newer or stable 1.3. If you call this function in a GameScript that
	 * is targeted at 1.2, it will crash your GameScript.
	 *
	 * For AIs, you need at least 1.2 to use this function or put this code
	 * at global scope:
	 *   AIOrder.AIOF_STOP_IN_DEPOT <- AIOrder.OF_STOP_IN_DEPOT;
	 *
	 *
	 * What it does:
	 * - IF sell_status != null THEN
	 *   - store the sell_status in the vehicle name using DataStore.StoreInVehicleName
	 * - unshares and clears the orders
	 * - IF stopped in depot THEN
	 *   - stop here
	 * - IF depot_tile is a valid depot tile THEN
	 *   - adds two orders to the depot at depot_tile
	 *   - uses skip to order between these depot orders
	 *   - removes one of the depot orders
	 * - ELSE
	 *   - send to depot using the API function for sending to depot (may fail)
	 * - IF road vehicle AND speed == 0
	 *   - try to turn around vehicle (as it might be stuck in a queue)
	 *
	 * As you might have noticed, this function doesn't actually wait for the vehicle to enter
	 * the depot and sells it. Instead you should regularly scan your depot for vehicles
	 * with the sell_status stored in their name and sell them when they appear in the depot.
	 * One way to do this is to call SellVehiclesInDepot for the depot_tile from time to time.
	 */
	static function SendVehicleToDepotForSelling(vehicle_id, depot_tile, sell_status = "sell");

	/*
	 * Sells vehicles in the depot on depot_tile that have sell_status stored
	 * in the vehicle name. See also SendVehicleToDepotForSelling.
	 *
	 * if sell_status is null, the function will sell all vehicles that are
	 * stopped in the depot.
	 */
	static function SellVehiclesInDepot(depot_tile, sell_status = "sell");
}

/*static*/ function _SuperLib_Vehicle::GetVehicleLimit(vehicle_type)
{
	// Report zero if the vehicle type is disabled, as no vehicles will
	// be possible to build even if the limit is > 0.
	if(AIGameSettings.IsDisabledVehicleType(vehicle_type))
		return 0;

	// Check if the vehicle type is disabled by the AI settings
	if(_SuperLib_Vehicle.IsVehicleTypeDisabledByAISettings(vehicle_type))
		return 0;

	local setting = "";
	switch(vehicle_type)
	{
		case AIVehicle.VT_ROAD:
			setting = "max_roadveh";
			break;

		case AIVehicle.VT_AIR:
			setting = "max_aircraft";
			break;
		case AIVehicle.VT_RAIL:
			setting = "max_trains";
			break;

		case AIVehicle.VT_WATER:
			setting = "max_ships";
			break;
	}

	return AIGameSettings.GetValue(setting);
}

function _SuperLib_Vehicle::GetVehiclesLeft(vehicle_type)
{
	local limit = _SuperLib_Vehicle.GetVehicleLimit(vehicle_type);

	// Quickly bail out if vehicle type is disabled
	if(limit == 0)
		return 0;

	// Check if the vehicle type is disabled by the AI settings
	if(_SuperLib_Vehicle.IsVehicleTypeDisabledByAISettings(vehicle_type))
		return 0;

	local veh_list = AIVehicleList();
	veh_list.Valuate(AIVehicle.GetVehicleType);
	veh_list.KeepValue(vehicle_type);

	return limit - veh_list.Count();
}

/*static*/ function _SuperLib_Vehicle::IsVehicleTypeDisabledByAISettings(vehicle_type)
{
	local ai_setting = "use_";
	switch(vehicle_type)
	{
		case AIVehicle.VT_ROAD:
			ai_setting += "rvs";
			break;

		case AIVehicle.VT_AIR:
			ai_setting += "planes";
			break;

		case AIVehicle.VT_RAIL:
			ai_setting += "trains";
			break;

		case AIVehicle.VT_WATER:
			ai_setting += "ships";
			break;

		default:
			// Unknown vehicle_type
			return false;
	}

	return AIController.GetSetting(ai_setting) == 0; // GetSetting returns -1 if the setting is undefined
}

/*static*/ function _SuperLib_Vehicle::GetVehicleTypeDisabledBySettingString(vehicle_type)
{
	// Are AIs disabled for all AIs in the advanced settings?
	if(AIGameSettings.IsDisabledVehicleType(vehicle_type))
		return "Advanced Settings -> Competitors -> Computer players";

	// Check if the vehicle type is disabled by the AI settings
	if(_SuperLib_Vehicle.IsVehicleTypeDisabledByAISettings(vehicle_type))
		return "AI Settings -> [click on AI] -> Configure";

	if(_SuperLib_Vehicle.GetVehicleLimit(vehicle_type) == 0)
		return "Advanced Settings -> Vehicles -> Max trains/road/aircraft/ships per company"

	return null;
}

/*static*/ function _SuperLib_Vehicle::GetProfitThisAndLastYear(vehicle_id)
{
	return AIVehicle.GetProfitLastYear(vehicle_id) + AIVehicle.GetProfitThisYear(vehicle_id);
}

/*static*/ function _SuperLib_Vehicle::IsVehicleAtStation(vehicle_id, station_id)
{
	if(AIVehicle.GetState(vehicle_id) != AIVehicle.VS_AT_STATION)
		return false;

	local veh_tile = AIVehicle.GetLocation(vehicle_id);

	// Check if the tile that the vehicle is at is a station
	// with the right station id
	return AIStation.GetStationID(veh_tile) == station_id;
}

/*static*/ function _SuperLib_Vehicle::HasTileListVehiclesOnIt(tile_rect, vehicle_type)
{
	local all_veh = AIVehicleList();
	all_veh.Valuate(AIVehicle.GetVehicleType);
	all_veh.KeepValue(vehicle_type);

	all_veh.Valuate(_SuperLib_Vehicle.VehicleIsWithinTileList, tile_rect);
	all_veh.KeepValue(1);

	return !all_veh.IsEmpty();
}

/*static*/ function _SuperLib_Vehicle::VehicleIsWithinTileList(vehicle_id, tile_list)
{
	return tile_list.HasItem(AIVehicle.GetLocation(vehicle_id));
}

/*static*/ function _SuperLib_Vehicle::GetVehiclesAtTile(tile)
{
	local vehicles = AIVehicleList();
	vehicles.Valuate(AIVehicle.GetLocation);
	vehicles.KeepValue(tile);

	return vehicles;
}

/*static*/ function _SuperLib_Vehicle::GetVehicleLocations()
{
	local veh_list = AIVehicleList();

	// Get a list of tile locations of our vehicles
	veh_list.Valuate(AIVehicle.GetLocation);
	local veh_locations = _SuperLib_Helper.CopyListSwapValuesAndItems(veh_list);

	return veh_locations;
}

/*static*/ function _SuperLib_Vehicle::GetVehicleCargoType(vehicle_id)
{
	// Go through all cargos and check the capacity for each
	// cargo.
	local max_cargo = -1;
	local max_cap = -1;

	local cargos = AICargoList();
	foreach(cargo, _ in cargos)
	{
		local cap = AIVehicle.GetCapacity(vehicle_id, cargo);
		if(cap > max_cap)
		{
			max_cap = cap;
			max_cargo = cargo;
		}
	}

	// Return the cargo which the vehicle has highest capacity
	// for.
	return max_cargo;
}

/*static*/ function _SuperLib_Vehicle::GetCrashedVehicleLocations(vehicle_type = null)
{
	local veh_list = AIVehicleList();
	veh_list.Valuate(AIVehicle.GetState);
	veh_list.KeepValue(AIVehicle.VS_CRASHED);

	if(vehicle_type != null)
	{
		veh_list.Valuate(AIVehicle.GetVehicleType);
		veh_list.KeepValue(vehicle_type);
	}

	// Get a list of tile locations of our vehicles
	veh_list.Valuate(AIVehicle.GetLocation);
	local veh_locations = _SuperLib_Helper.CopyListSwapValuesAndItems(veh_list);

	return veh_locations;
}

/*static*/ function _SuperLib_Vehicle::GetNonCrashedVehicleLocations(vehicle_type = null)
{
	local veh_list = AIVehicleList();
	veh_list.Valuate(AIVehicle.GetState);
	veh_list.RemoveValue(AIVehicle.VS_CRASHED);
	veh_list.RemoveValue(AIVehicle.VS_INVALID);

	if(vehicle_type != null)
	{
		veh_list.Valuate(AIVehicle.GetVehicleType);
		veh_list.KeepValue(vehicle_type);
	}

	// Get a list of tile locations of our vehicles
	veh_list.Valuate(AIVehicle.GetLocation);
	local veh_locations = _SuperLib_Helper.CopyListSwapValuesAndItems(veh_list);

	return veh_locations;
}

/*static*/ function _SuperLib_Vehicle::SendVehicleToDepotForSelling(vehicle_id, depot_tile, sell_status = "sell")
{
	if(!AIVehicle.IsValidVehicle(vehicle_id))
		return;

	if(sell_status != null)
		_SuperLib_DataStore.StoreInVehicleName(vehicle_id, sell_status);

	// Unshare & clear orders
	AIOrder.UnshareOrders(vehicle_id);
	while(AIOrder.GetOrderCount(vehicle_id) > 0)
	{
		AIOrder.RemoveOrder(vehicle_id, 0);
	}

	// Check if it is already in a depot
	if(AIVehicle.IsStoppedInDepot(vehicle_id))
		return; // Don't sell it as this function doesn't sell vehicles.

	if(_SuperLib_Tile.IsDepotTile(depot_tile, AIVehicle.GetVehicleType(vehicle_id)))
	{
		// Send vehicle to specific depot so it don't get lost
		if(AIOrder.AppendOrder(vehicle_id, depot_tile, AIOrder.OF_STOP_IN_DEPOT))
		{
			// Add an extra order so we can skip between the orders to fully make sure vehicles leave
			// stations they previously were full loading at.
			AIOrder.AppendOrder(vehicle_id, depot_tile, AIOrder.OF_STOP_IN_DEPOT);

			// so that vehicles that load stuff departures
			AIOrder.SkipToOrder(vehicle_id, 1);
			AIOrder.SkipToOrder(vehicle_id, 0);

			// Remove the second now unnecessary order
			AIOrder.RemoveOrder(vehicle_id, 1);
		}
	}
	else
	{
		// no depot at depot_tile => fallback to the API function
		AIVehicle.SendVehicleToDepot(vehicle_id);
	}

	// Turn around road vehicles that stand still, possible in queues.
	if(AIVehicle.GetVehicleType(vehicle_id) == AIVehicle.VT_ROAD)
	{
		if(AIVehicle.GetCurrentSpeed(vehicle_id) == 0)
		{
			_SuperLib_Log.Info("Turn around road vehicle that was sent for selling since speed is zero and it might be stuck in a queue.", _SuperLib_Log.LVL_DEBUG);
			AIVehicle.ReverseVehicle(vehicle_id);
		}
	}
}

/*static*/ function _SuperLib_Vehicle::SellVehiclesInDepot(depot_tile, sell_status = "sell")
{
	local vehicle_list = AIVehicleList_Depot(depot_tile);

	foreach(vehicle_id, _ in vehicle_list)
	{
		if(!AIVehicle.IsStoppedInDepot(vehicle_id))
			continue;

		if(sell_status == null || _SuperLib_DataStore.ReadStrFromVehicleName(vehicle_id) == sell_status)
		{
			// The vehicle is stopped in depot and has the correct sell_status
			// stored in the vehicle name.
			AIVehicle.SellVehicle(vehicle_id);
		}
	}

}
