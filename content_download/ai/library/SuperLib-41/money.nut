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

class _SuperLib_Money
{
	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Money, money                                                    //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function GetMaxSpendingAmount();

	// loan_limit = upper level of allowed loan size.
	// A value <= 0 means no limit.
	static function MakeSureToHaveAmount(amount, loan_limit = -1);

	static function MakeMaximumPayback();

	// If exec_function returns false and the last error is ERR_NOT_ENOUGH_CASH,
	// the exec_function is executed again in test + accounting mode to get the
	// cost of the action, to increase the loan and execute it again.
	//
	// Typically exec_function is a anonymous function that execute a rather simple
	// command.
	//
	// loan_limit = maximum loan to take. If it is <= 0, then there is no limit.
	//
	// Example
	//   ExecuteWithLoan(-1, function(a, b) { return AIRoad.BuildRoad(a, b); }, from, to);
	static function ExecuteWithLoan(loan_limit, exec_function, ...);

	// WARNING: this function doesn't work and will crash your AI.
	// The reason is that the cost of station maintenance is not known
	// to the AI.
	static function GetCompanyProfitLastYear();

	/*
	 * Wastes money (may be used to ensure bankruptcy)
	 * Note that this function will never return back to your AI.
	 *
	 * Author: This function has been contributed by Kogut
	 */
	static function BurnMoney();


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Temporary max loans                                             //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Example:
	 *   local old_balance = MaxLoan();
	 *
	 *   // .. do something that costs money ..
	 *
	 *   RestoreLoan(old_balance);
	 *
	 */

	static function MaxLoan(); // Returns previous balance
	static function RestoreLoan(old_balance); // restores the old balance


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Inflation                                                       //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Calculates the percentage of inflation since the start of the game.
	 * @return The percentage by which prices have risen since the start of the game.
	 * It is 100 if there is no inflation, 200 if prices have doubled, etc.
	 *
	 * Author: This function comes from SimpleAI, version 6, written by Brumi
	 */
	static function GetInflationRate();

	/*
	 * Adjusts any given amount of money for inflation
	 *
	 * Author: This function comes from AIAI, version 51, written by Kogut
	 */
	static function Inflate(money);


};

function _SuperLib_Money::GetMaxSpendingAmount()
{
	local balance = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
	local max_loan = AICompany.GetMaxLoanAmount();
	local loan_amount = AICompany.GetLoanAmount();

	return balance + (max_loan - loan_amount);
}

function _SuperLib_Money::MakeSureToHaveAmount(amount, loan_limit = -1, call_number = 1)
{
	local balance = AICompany.GetBankBalance(AICompany.COMPANY_SELF);

	if(balance >= amount)
	{
		return true; // Already enough money on the bank balance
	}

	local needed_loan_amount = amount - balance;

	local max_loan = AICompany.GetMaxLoanAmount();
	if(loan_limit > 0) max_loan = min(max_loan, loan_limit); // apply loan limit
	local current_loan_amount = AICompany.GetLoanAmount();

	if(max_loan - current_loan_amount < needed_loan_amount)
	{
		return false; // Not possible to loan the needed extra money from the bank
	}

	local num_loan_steps = needed_loan_amount / AICompany.GetLoanInterval();
	local extra_loan_amount = AICompany.GetLoanInterval() * num_loan_steps;
	if(extra_loan_amount < needed_loan_amount)
	{
		// In most cases the integer division will lead to a to small loan,
		// so compensate for that. Though in rare cases this is not needed.
		num_loan_steps++;
		extra_loan_amount += AICompany.GetLoanInterval();
	}

	AICompany.SetLoanAmount(current_loan_amount + extra_loan_amount);

	if(AICompany.GetBankBalance(AICompany.COMPANY_SELF) < amount)
	{
		if(call_number <= 1)
		{
			if (_SuperLib_Log.IsLevelAccepted(_SuperLib_Log.LVL_DEBUG)) {
				_SuperLib_Log.Error("Money::MakeSureToHaveAmount failed to acquire enough money even though the needed loan size is allowed.", _SuperLib_Log.LVL_DEBUG);
				_SuperLib_Log.Info("amount = " + amount + " balance = " + balance + " needed loan " + needed_loan_amount + " num loan steps = " + num_loan_steps + " extra loan = " + extra_loan_amount + " current loan = " + current_loan_amount, _SuperLib_Log.LVL_DEBUG);
				_SuperLib_Log.Info("Retrying .. ", _SuperLib_Log.LVL_DEBUG);
			}
			return _SuperLib_Money.MakeSureToHaveAmount(amount, loan_limit, call_number + 1)
		}
		else
		{
			_SuperLib_Log.Error("Money::MakeSureToHaveAmount retried but failed again!", _SuperLib_Log.LVL_INFO);
			_SuperLib_Log.Info("amount = " + amount + " balance = " + balance + " needed loan " + needed_loan_amount + " num loan steps = " + num_loan_steps + " extra loan = " + extra_loan_amount + " current loan = " + current_loan_amount, _SuperLib_Log.LVL_INFO);
		}

		return false;
	}

	return true;
}

function _SuperLib_Money::MakeMaximumPayback()
{
	local balance = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
	local current_loan_amount = AICompany.GetLoanAmount();

	if(balance < 0 || current_loan_amount == 0)
		return;

	local loan_interval = AICompany.GetLoanInterval();
	local num_payback_steps = balance / loan_interval

	local new_loan_amount = current_loan_amount - num_payback_steps * loan_interval;

	// Make sure to not payback more than possible
	new_loan_amount = _SuperLib_Helper.Max(new_loan_amount, 0);

	AICompany.SetLoanAmount(new_loan_amount);
}

function _SuperLib_Money::ExecuteWithLoan(loan_limit, exec_function, ...)
{
	// get args array
	local args = [];
	for(local c = 0; c < vargc; c++) {
		args.append(vargv[c]);
	}

	// First try without increasing the loan amount
	local result = _SuperLib_Helper.CallFunction(exec_function, args);

	// Was there not enough cash to execute the action?
	if (!result && AIError.GetLastError() == AIError.ERR_NOT_ENOUGH_CASH)
	{
		// get cost
		local cost = 0;
		{
			local am = AIAccounting();
			local tm = AITestMode();
			_SuperLib_Helper.CallFunction(exec_function, args);
			cost = am.GetCosts();
		}

		// get more money, in exec mode :-)
		if(_SuperLib_Money.MakeSureToHaveAmount(cost, loan_limit))
		{
			// try again
			result = _SuperLib_Helper.CallFunction(exec_function, args);
		}
	}

	return result;
}

function _SuperLib_Money::GetCompanyProfitLastYear()
{
	local all_vehicles = AIVehicleList();
	local company_profit = 0;

	foreach(vehicle_id in all_vehicles)
	{
		local veh_profit = AIVehicle.GetProfitLastYear(vehicle_id);

		// If the vehicle didn't make any money last year, but this year then use the numbers for this yea instead
		if(veh_profit <= 0)
		{
			local this_year = AIVehicle.GetProfitThisYear(vehicle_id);
			if(this_year > 0) veh_profit = this_year;
		}

		company_profit += veh_profit;
	}

	local all_stations = AIStationList(AIStation.STATION_ANY);
	foreach(station_id in all_stations)
	{
		local num = 0;
		num += AIStation.HasStationType(station_id, AIStation.STATION_BUS_STOP)? 1 : 0;
		num += AIStation.HasStationType(station_id, AIStation.STATION_TRUCK_STOP)? 1 : 0; // does truck + bus cost 500 each or just one of them?
		num += AIStation.HasStationType(station_id, AIStation.STATION_AIRPORT)? 1 : 0;
		num += AIStation.HasStationType(station_id, AIStation.STATION_TRAIN)? 1 : 0;
		num += AIStation.HasStationType(station_id, AIStation.STATION_DOCK)? 1 : 0;

		company_profit -= STATION_MAINTENANCE_COST * num;
	}

	return company_profit;
}

function _SuperLib_Money::MaxLoan()
{
	local old_balance = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
	AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());

	return old_balance;
}
function _SuperLib_Money::RestoreLoan(old_balance)
{
	_SuperLib_Money.MakeMaximumPayback();
	_SuperLib_Money.MakeSureToHaveAmount(old_balance);
}

function _SuperLib_Money::GetInflationRate()
{
	return AICompany.GetMaxLoanAmount() / (AIGameSettings.GetValue("difficulty.max_loan") / 100);
}

function _SuperLib_Money::Inflate(money)
{
	return (money / 100) * _SuperLib_Money.GetInflationRate() + (money % 100) * _SuperLib_Money.GetInflationRate() / 100;
}

function _SuperLib_Money::BurnMoney()
{
	AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
	local empty_tile = null;
	while(true)
	{
		for(local i = 0; i < 1000; i++)
		{
			empty_tile = _SuperLib_Tile.GetRandomTile();
			if(AITile.IsBuildable(empty_tile))
			{
				while(true)
				{
					if(!AITile.DemolishTile(empty_tile))
					{
						if(AIError.GetLastError() == AIError.ERR_NOT_ENOUGH_CASH) {
							return;
						}
						break;
					}
					if(!AITile.PlantTree(empty_tile))
					{
						if(AIError.GetLastError() == AIError.ERR_NOT_ENOUGH_CASH) {
							return;
						}
						break;
					}
				}
			}
		}
		AIController.Sleep(500);
	}
}

