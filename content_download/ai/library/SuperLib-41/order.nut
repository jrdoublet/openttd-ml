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

/*
 * This file contains two classes:
 * - Order     - utility functions for orders
 * - OrderList - for applying a set of orders to a vehicle
 */

//////////////////////////////////////////////////////////////////////
//                                                                  //
//  Order class  - utility functions for orders                     //
//                                                                  //
//////////////////////////////////////////////////////////////////////

class _SuperLib_Order {
	/* Gets the current destination that a vehicle heads to
	 * Returns -1 if the current order is a conditional order
	 */
	static function GetCurrentOrderDestination(vehicle_id);

	/* A function to clear all orders of a vehicle, that works so that if shared orders
	 * is used, each of the shared order is removed, but the sharing of the orders is
	 * not affected - only clearing of them.
	 */
	static function ClearOrdersOfSharedGroup(vehicle_id);

	/* Get an AIList of the stations that the vehicle has
	 * orders to visit (or go via)
	 */
	static function GetStationListFromOrders(vehicle_id);

	/* Checks if a given station exists in the orders of a vehicle */
	static function HasStationInOrders(vehicle_id, station_id);
}

function _SuperLib_Order::GetCurrentOrderDestination(vehicle_id)
{
	if(AIOrder.IsConditionalOrder(vehicle_id, AIOrder.ORDER_CURRENT))
		return -1;

	return AIOrder.GetOrderDestination(vehicle_id, AIOrder.ORDER_CURRENT);
}

function _SuperLib_Order::ClearOrdersOfSharedGroup(vehicle_id)
{
	local num_orders = AIOrder.GetOrderCount(vehicle_id);
	for(local i = 0; i < num_orders; i++)
	{
		AIOrder.RemoveOrder(vehicle_id, 0);
	}
	if(AIOrder.GetOrderCount(vehicle_id) != 0)
		_SuperLib_Log.Error("ClearOrdersOfSharedGroup: Not all orders cleared", _SuperLib_Log.LVL_INFO);
}

function _SuperLib_Order::GetStationListFromOrders(vehicle_id)
{
	local station_list = AIList();

	local num_orders = AIOrder.GetOrderCount(vehicle_id);
	for(local i = 0; i < num_orders; i++)
	{
		local tile_id = AIOrder.GetOrderDestination(vehicle_id, i);
		local station_id = AIStation.GetStationID(tile_id);
		if(AIStation.IsValidStation(station_id))
		{
			station_list.AddItem(station_id, 0);
		}
	}

	return station_list;
}

function _SuperLib_Order::HasStationInOrders(vehicle_id, station_id)
{
	local station_list = _SuperLib_Order.GetStationListFromOrders(vehicle_id);
	return station_list.HasItem(station_id);
}


//////////////////////////////////////////////////////////////////////
//                                                                  //
//  OrderList class  - applying a list of orders to a vehicle       //
//                                                                  //
//////////////////////////////////////////////////////////////////////

class _SuperLib_OrderList {
	list = null;

	skip_to_last_when_full = false;

	constructor()
	{
		this.list = [];
		skip_to_last_when_full = false;
	}

	/* Purpose: To have a way of applying orders to vehicles that will not do any
	 * harm if the orders are already present. If a single order is missing, then
	 * the other station orders will remain intact so that when you add a new
	 * station to the order list, not all vehicles will lose track of where they
	 * are heading.
	 */

	/* Usage:
	 *
	 * 1a) Call AddStop for all station you want the vehicle(s) to stop at/go via.
	 *     You must call AddStop in the order you want the stations to be visited.
	 *
	 * 1b) Call SkipToLastWhenFull(true) if you want to enable it. (when this is
	 *     done related to 1a) is not important, as long as you do it before 2). )
	 *
	 * 2) Call ApplyToVehicle(vehicle_id) for any number of vehicles that you
	 *    want to apply the order list to.
	 */


	/*
	 * Add a stop at a station.
	 *
	 * station_id_value = station id
	 * flags_value = AIOrder flags to use for the station
	 */
	function AddStop(station_id_value, flags_value);

	/*
	 * Call this function to enable/disable if vehicles
	 * should skip to the last station order if they are full
	 *
	 * If you enable this, conditional orders for this will be
	 * inserted to the vehicle orders to acomplish that.
	 */
	function SkipToLastWhenFull(enable);

	/*
	 * Applies the order list to a given vehicle.
	 */
	function ApplyToVehicle(vehicle_id);

	/*
	 * Returns the order index that has a given destination.
	 * start search from order index 'begin'
	 */
	static function FindOrderDestination(vehicle_id, begin, match_destination);
}

function _SuperLib_OrderList::AddStop(station_id_value, flags_value)
{
	list.append(
		{station_id=station_id_value,
		flags=flags_value}
	);
}

function _SuperLib_OrderList::SkipToLastWhenFull(enable)
{
	skip_to_last_when_full = enable;
}

function _SuperLib_OrderList::ApplyToVehicle(vehicle_id)
{
	if(!AIVehicle.IsValidVehicle(vehicle_id))
	{
		_SuperLib_Log.Warning("OrderList::ApplyToVehicle: invalid vehicle id (" + vehicle_id + ") supplied", _SuperLib_Log.LVL_INFO);
		return;
	}

	_SuperLib_Log.Info("order list len: " + this.list.len(), _SuperLib_Log.LVL_DEBUG);
	//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));

	local i = 0;
	for(; i < list.len(); i++)
	{
		local station_id = list[i].station_id;
		local flags = list[i].flags;

		//Helper.SetSign( AIStation.GetLocation(station_id), "flags: " + flags);
		_SuperLib_Log.Info("station " + station_id + " with flags " + flags, _SuperLib_Log.LVL_DEBUG);
	}

	i = 0;
	//local i = 0; // this.list position
	local k = 0; // order list position
	for(; i < list.len(); i++)
	{
		//// Add a normal order to the target in this.list ////

		// if current position is a conditional order, then remove it until a non-conditional order is found
		// or end of order list is reached
		while(k < AIOrder.GetOrderCount(vehicle_id) && AIOrder.IsConditionalOrder(vehicle_id, k))
		{
			// remove conditional order
			AIOrder.RemoveOrder(vehicle_id, k);
		}

		if(k < AIOrder.GetOrderCount(vehicle_id))
		{
			// k is a normal order -> change it or insert a new

			// check if the destination is correct
			local curr_order_dest_station = AIStation.GetStationID(AIOrder.GetOrderDestination(vehicle_id, k));
			if(curr_order_dest_station == this.list[i].station_id)
			{
				// current order has correct destination
				_SuperLib_Log.Info("current order has correct destination", _SuperLib_Log.LVL_DEBUG);
				AIOrder.SetOrderFlags(vehicle_id, k, this.list[i].flags); // Make sure the flags are correct
			}
			else
			{
				// current order has wrong destination
				_SuperLib_Log.Info("current order has Wrong destination", _SuperLib_Log.LVL_DEBUG);

				// First try to see if there is an order with this destination
				local later_order = _SuperLib_OrderList.FindOrderDestination(vehicle_id, k+1, AIStation.GetLocation(this.list[i].station_id));
				if(later_order != -1)
				{
					// Found the destination later in list, move it to i
					_SuperLib_Log.Info("Found correct destination later in list", _SuperLib_Log.LVL_DEBUG);
					AIOrder.MoveOrder(vehicle_id, later_order, k);
					AIOrder.SetOrderFlags(vehicle_id, k, this.list[i].flags); // Make sure the flags are correct
				}
				else
				{
					// There is no order with this destination, make a new order.
					_SuperLib_Log.Info("Did not found correct destination later in list -> insert a new one", _SuperLib_Log.LVL_DEBUG);

					//Helper.SetSign(AIStation.GetLocation(this.list[i].station_id), "insert " + this.list[i].flags);
					AIOrder.InsertOrder(vehicle_id, k, AIStation.GetLocation(this.list[i].station_id), this.list[i].flags);
					_SuperLib_Log.Info("Insert order error msg: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_DEBUG);
				}
			}
		}
		else
		{
			// no existing order -> append a new one

			// append a new normal order
			_SuperLib_Log.Info("Existing order list is shorter than current k -> Append new order", _SuperLib_Log.LVL_DEBUG);
			//Helper.SetSign(AIStation.GetLocation(this.list[i].station_id), "append");
			AIOrder.AppendOrder(vehicle_id, AIStation.GetLocation(this.list[i].station_id), this.list[i].flags);
			_SuperLib_Log.Info("Append order error msg: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_DEBUG);
			//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));
		}

		k++;

		//// Add a conditional order if wanted ////
		if(skip_to_last_when_full && i < list.len() - 2)
		{
			if(k < AIOrder.GetOrderCount(vehicle_id) && AIOrder.IsConditionalOrder(vehicle_id, k))
			{
				// there is a conditional order, so don't do anything
			}
			else
			{
				// next order don't exist or is not a conditional order
				AIOrder.InsertConditionalOrder(vehicle_id, k, 0); // Add a dummy conditional order pointing on first order
				_SuperLib_Log.Info("Insert conditional order error msg: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_DEBUG);
			}

			k++;

			_SuperLib_Log.Info("Breaking after conditional order have been added", _SuperLib_Log.LVL_DEBUG);
			//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));
		}


		//_SuperLib_Log.Info("Breaking before next loop", _SuperLib_Log.LVL_DEBUG);
		//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));
	}



	_SuperLib_Log.Info("Breaking before removal", _SuperLib_Log.LVL_DEBUG);
	//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));

	// if the vehicle order list contained orders that we don't want to have anymore, they will be located at the end.
	// so remove all orders that are after the last item number in this.list
	local num_to_remove = AIOrder.GetOrderCount(vehicle_id) - k;
	if(num_to_remove > 0)
	{
		for(local j = 0; j < num_to_remove; j++)
		{
			// Remove the one with id last wanted + 1, since the remaining ones move up after each removal.
			AIOrder.RemoveOrder(vehicle_id, k);
		}
	}

	_SuperLib_Log.Info("Breaking after removal", _SuperLib_Log.LVL_DEBUG);
	//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));

	// Update the conditional orders
	if(skip_to_last_when_full)
	{
		local num_orders = AIOrder.GetOrderCount(vehicle_id);
		local jump_to = num_orders - 1;
		for(local order = 0; order < num_orders; order++)
		{
			if(AIOrder.IsConditionalOrder(vehicle_id, order))
			{
				if(!AIOrder.SetOrderJumpTo(vehicle_id, order, jump_to))
				{
					_SuperLib_Log.Warning("You are using a OpenTTD version < r16063 where the SetOrderJumpTo function is broken. The old (less good) ApplyToVehicle function will be used instead.", _SuperLib_Log.LVL_INFO);
					return this.Old_070_Compatible_ApplyToVehicle(vehicle_id);
				}
				_SuperLib_Log.Info("Set order jump to - error message: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_DEBUG);
				AIOrder.SetOrderCondition(vehicle_id, order, AIOrder.OC_LOAD_PERCENTAGE);
				AIOrder.SetOrderCompareFunction(vehicle_id, order, AIOrder.CF_EQUALS);
				AIOrder.SetOrderCompareValue(vehicle_id, order, 100);
			}
		}
	}

	_SuperLib_Log.Info("Breaking at end of ApplyOrder", _SuperLib_Log.LVL_DEBUG);
	//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));
}

function _SuperLib_OrderList::Old_070_Compatible_ApplyToVehicle(vehicle_id)
{
	_SuperLib_Log.Info("order list len: " + this.list.len(), _SuperLib_Log.LVL_DEBUG);
	//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));

	local i = 0;
	for(; i < list.len(); i++)
	{
		if(i < AIOrder.GetOrderCount(vehicle_id))
		{
			_SuperLib_Log.Info(" i < num orders of vehicle", _SuperLib_Log.LVL_DEBUG);

			// If current order is a conditional order
			if(AIOrder.IsConditionalOrder(vehicle_id, i))
			{
				// remove conditional order
				AIOrder.RemoveOrder(vehicle_id, i);

				// skip to next order. Since one order was removed next order now has same id as the removed order (if it exists)
				i--;
				continue;

				// then at the end we add back conditional orders
			}

			local curr_order_dest_station = AIStation.GetStationID(AIOrder.GetOrderDestination(vehicle_id, i));
			if(curr_order_dest_station == this.list[i].station_id)
			{
				// current order has correct destination
				_SuperLib_Log.Info("current order has correct destination", _SuperLib_Log.LVL_DEBUG);
				AIOrder.SetOrderFlags(vehicle_id, i, this.list[i].flags); // Make sure the flags are correct
			}
			else
			{
				// current order has wrong destination
				_SuperLib_Log.Info("current order has Wrong destination", _SuperLib_Log.LVL_DEBUG);

				// First try to see if there is an order with this destination
				local later_order = _SuperLib_OrderList.FindOrderDestination(vehicle_id, i+1, AIStation.GetLocation(this.list[i].station_id));
				if(later_order != -1)
				{
					// Found the destination later in list, move it to i
					_SuperLib_Log.Info("Found correct destination later in list", _SuperLib_Log.LVL_DEBUG);
					AIOrder.MoveOrder(vehicle_id, later_order, i);
					AIOrder.SetOrderFlags(vehicle_id, i, this.list[i].flags); // Make sure the flags are correct
				}
				else
				{
					// There is no order with this destination, make a new order.
					_SuperLib_Log.Info("Did not found correct destination later in list -> insert a new one", _SuperLib_Log.LVL_DEBUG);
					//Helper.SetSign(AIStation.GetLocation(this.list[i].station_id), "insert");
					AIOrder.InsertOrder(vehicle_id, i, AIStation.GetLocation(this.list[i].station_id), this.list[i].flags);
					_SuperLib_Log.Info("Insert order error msg: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_DEBUG);
				}
			}
		}
		else
		{
			// the existing order list is shorter than current wanted order.
			_SuperLib_Log.Info("Existing order list is shorter than current i -> Append new order", _SuperLib_Log.LVL_DEBUG);

			// Append wanted order at the end
			//Helper.SetSign(AIStation.GetLocation(this.list[i].station_id), "append");
			AIOrder.AppendOrder(vehicle_id, AIStation.GetLocation(this.list[i].station_id), this.list[i].flags);
			_SuperLib_Log.Info("Append order error msg: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_DEBUG);
		}

		_SuperLib_Log.Info("Breaking before next loop", _SuperLib_Log.LVL_DEBUG);
		//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));
	}

	_SuperLib_Log.Info("Breaking before removal", _SuperLib_Log.LVL_DEBUG);
	//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));

	// if the vehicle order list contained orders that we don't want to have anymore, they will be located at the end.
	// so remove all orders that are after the last item number in this.list
	local num_to_remove = AIOrder.GetOrderCount(vehicle_id) - this.list.len();
	if(num_to_remove > 0)
	{
		for(local j = 0; j < num_to_remove; j++)
		{
			// Remove the one with id last wanted + 1, since the remaining ones move up after each removal.
			AIOrder.RemoveOrder(vehicle_id, this.list.len());
		}
	}

	_SuperLib_Log.Info("Breaking after removal", _SuperLib_Log.LVL_DEBUG);
	//Helper.BreakPoint(AIVehicle.GetLocation(vehicle_id));

	// Add conditional orders if wanted
	if(skip_to_last_when_full && AIOrder.GetOrderCount(vehicle_id) >= 2)
	{
		// for all but last
		local order = 0;
		local num_regular_orders = AIOrder.GetOrderCount(vehicle_id);
		_SuperLib_Log.Info("Num regular orders: " + num_regular_orders, _SuperLib_Log.LVL_DEBUG);
		for(local i = 0; i < num_regular_orders - 1; i++)
		{
			_SuperLib_Log.Info("Inserting a conditional order at location " + (order + 1), _SuperLib_Log.LVL_DEBUG);
			AIOrder.InsertConditionalOrder(vehicle_id, order + 1, AIOrder.GetOrderCount(vehicle_id) - 1);
			AIOrder.SetOrderCondition(vehicle_id, order + 1, AIOrder.OC_LOAD_PERCENTAGE);
			AIOrder.SetOrderCompareFunction(vehicle_id, order + 1, AIOrder.CF_EQUALS);
			AIOrder.SetOrderCompareValue(vehicle_id, order + 1, 100);

			_SuperLib_Log.Info("Order count: " + AIOrder.GetOrderCount(vehicle_id), _SuperLib_Log.LVL_DEBUG);

			order += 2; // next regular order
		}
	}
}

/* static */ function _SuperLib_OrderList::FindOrderDestination(vehicle_id, begin, match_destination)
{
	local num = AIOrder.GetOrderCount(vehicle_id);
	for(local i = begin; i < num; i++)
	{
		if(AIOrder.GetOrderDestination(vehicle_id, i) == match_destination)
			return i;
	}

	return -1;
}
