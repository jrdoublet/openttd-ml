/*
 * This file is part of SuperLib.Helper, which is an AI Library for OpenTTD
 * Copyright (C) 2008-2010  Zuu
 *
 * SuperLib.Helper is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License
 *
 * SuperLib.Helper is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with SuperLib.Helper; If not, see <http://www.gnu.org/licenses/> or
 * write to the Free Software Foundation, Inc., 51 Franklin Street,
 * Fifth Floor, Boston, MA 02110-1301 USA.
 *
 */

class _SuperLib_Helper
{
	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  OpenTTD version                                                 //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/**
	 * Get current OpenTTD version.
	 * @return A table with separate fields for each version part:
	 * @note that on RCs, IsRelease is false.
	 * - Major: the major version
	 * - Minor: the minor version
	 * - Build: the build
	 * - IsRelease: is this an stable release
	 * - Revision: the svn revision of this build
	 */
	static function GetOpenTTDVersion(); // This method originates from AILibCommon

	/**
	 * Checks if the OpenTTD version that execute your script has the bug that
	 * APIs that perform a DoCommand (world modifying actions) will carry out
	 * the action, but return the same value as in test mode. Eg. it will just
	 * return id 0 for all things that you create.
	 *
	 * If this method returns true, you should call AIController.Sleep(1) to
	 * terminate world generation and start the game, before calling any API
	 * method that perform a DoCommand, and where you use the return value in
	 * any way.
	 *
	 * This bug is further described here in the bug tracker:
	 * http://bugs.openttd.org/task/5561
	 */
	static function HasWorldGenBug();

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  SuperLib version                                                //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	// Note the SuperLib version methods are only available since
	// version 37.

	/*
	 * Returns the library version (integer value)
	 */
	static function GetSuperLibVersion();

	/*
	 * Prints library name + version to debug log using given log level,
	 * or at log level Log.LVL_INFO if no log level is given.
	 */
	static function PrintLibInfo(log_level = _SuperLib_Log.LVL_INFO);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  String                                                          //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Return the string with leading/trailing spaces removed.
	 */
	static function Trim(string);

	/*
	 * Works the same way as eg. Explode in php
	 */
	static function SplitString(delimiter, string, limit = null);

	/*
	 * Returns null if the substring can't be found in the string.
	 * This function differs from the built in squirrel function
	 * string.find(substr, startidx) in that it searches from the
	 * back.
	 */
	static function FindFromEnd(substr, string, startidx = null);

	/*
	 * Looks for just a single char. More effective than FindFromEnd.
	 * Note that findchar must be of the char type.
	 * Example: FindCharFromEnd(' ', 'Aa bb cc'); => 5
	 */
	static function FindCharFromEnd(findchar, string, startidx = null);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Date                                                            //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Returns a date string on the format <year>-<month>-<day>.
	 * Eg. 2010-01-10
	 */
	static function GetCurrentDateString();
	static function GetDateString(date);


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Sign                                                            //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Note: An AI can only access its own signs. So you must use the
	 *   cheat dialog and switch to the AI company if you want to place
	 *   control signs such as "break_on" etc.
	 */

	/* Use this function instead of AISign.BuildSign to never build more
	 * than one sign per tile
	 *
	 * Signs are only placed if the AI setting debug_signs is equal to 1
	 *
	 * Returns: The sign id of the sign that is placed/updated or -1
	 *   if no sign is created/updated.
	 */
	static function SetSign(tile, message, force_build_sign = false);

	/* Puts a "break" sign on the given tile and waits until that sign
	 * gets removed by the player. Usefull for debuging.
	 *
	 * Break points are only placed if AI setting debug_signs == 1 or
	 * if the sign "break_on" is present. In either case if the sign
	 * "no_break" is present then no break points will be placed.
	 * See the implementation if this text is not clear enough.
	 */
	static function BreakPoint(sign_tile, force_break_point = false);

	/* Checks if the AI has a sign with the given text */
	static function HasSign(text);

	/* Returns the id of the first found sign with given name. If no sign
	 * is found, -1 is returned.
	 */
	static function GetSign(text);

	/* Checks if the AI has a sign at the given location */
	static function HasSignAt(tile);

	/* Returns the id of the first found sign at the given tile. If no sign
	 * is found, -1 is returned.
	 */
	static function GetSignAt(tile);

	/* Removes all signs that the AI has. */
	static function ClearAllSigns(except_tile = -1);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Cargo                                                           //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* Get the cargo ID of the passenger cargo */
	static function GetPAXCargo();

	/* Get the cargo ID of the mail cargo */
	static function GetMailCargo();

	/* Gets the cargo in an AIList containing cargoes that has the highest
	 * availability in the largest town
	 */
	static function GetCargoWithLargestAvailabilityInLargestTown(cargo_list);

	/* The GetTownProducedCargoList and GetTownAcceptedCargoList functions
	 * are climate aware, but are somewhat hardcoded as they make use of
	 * the cargo labels "MAIL", "GOOD" etc.
	 *
	 * If a NewGRF defines houses that produce eg. Coal without being an
	 * industry, then that will not be included by these functions.
	 */

	/* Get an AIList with cargo IDs as items.
	 * The list contains cargos that towns may produce
	 */
	static function GetTownProducedCargoList();

	/* Get an AIList with cargo IDs as items.
	 * The list contains cargos that towns may accept
	 */
	static function GetTownAcceptedCargoList();


	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  List                                                            //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/* A valuator function that returns the item itself */
	static function ItemValuator(a) { return a; }

	// This function comes from AdmiralAI, version 22, written by Yexo
	/**
	 * Apply a valuator function to every item of an AIList.
	 * @param list The AIList to apply the valuator to.
	 * @param valuator The function to apply.
	 * @param others Extra parameters for the valuator function).
	 */
	static function Valuate(list, valuator, ...);

	// This function comes from AdmiralAI, version 22, written by Yexo
	/**
	 * Call a function with the arguments given.
	 * @param func The function to call.
	 * @param args An array with all arguments for func.
	 * @pre args.len() <= 8.
	 * @return The return value from the called function.
	 */
	static function CallFunction(func, args);

	/* Returns the sum of all values in an AIList */
	static function ListValueSum(ai_list);

	/* Returns a list where the values and items has been swapped */
	static function CopyListSwapValuesAndItems(old_list);

	static function GetListMinValue(ai_list);
	static function GetListMaxValue(ai_list);

	static function SquirrelListToAIList(squirrel_list);

	// Todo: Rename this function to eg. FindSquirrelArrayKey or similar
	static function ArrayFind(array, toFind);

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Max, Min, Clamp etc.                                            //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	static function Min(x1, x2);
	static function Max(x1, x2);
	static function Clamp(x, min, max);
	static function Abs(a);
}

// Note to self: Internal static vars are defined at the very bottom of this file


// This method originates from AILibCommon
function _SuperLib_Helper::GetOpenTTDVersion()
{
	local v = AIController.GetVersion();
	local tmp =
	{
		Major = (v & 0xF0000000) >> 28,
		Minor = (v & 0x0F000000) >> 24,
		Build = (v & 0x00F00000) >> 20,
		IsRelease = (v & 0x00080000) != 0,
		Revision = v & 0x0007FFFF,
	}
	return tmp;
}

function _SuperLib_Helper::HasWorldGenBug()
{
	local version = _SuperLib_Helper.GetOpenTTDVersion();

	if (version.Major == 0 || (version.Major == 1 && version.Minor <= 3)) {
		return version.Revision < 25339;
	} else {
		return version.Revision < 25305;
	}
}

function _SuperLib_Helper::GetSuperLibVersion()
{
	return _SuperLib_VERSION;
}

function _SuperLib_Helper::PrintLibInfo(log_level = _SuperLib_Log.LVL_INFO)
{
	_SuperLib_Log.Info("SuperLib version " + _SuperLib_VERSION, log_level);
}

function _SuperLib_Helper::Trim(string)
{
	// Trim start
	local pos = string.find(" ");
	while (pos == 0) {
		string = string.slice(1);
		pos = string.find(" ");
	}

	// Trim end
	pos = _SuperLib_Helper.FindFromEnd(" ", string);
	while (pos == string.len() - 1) {
		string = string.slice(0, string.len() - 1);
		pos = _SuperLib_Helper.FindFromEnd(" ", string);
	}

	return str;
}

function _SuperLib_Helper::SplitString(delimiter, string, limit = null)
{
	local result = [];

	if(limit != null && limit <= 0) return result;

	local start = 0;
	local pos = string.find(delimiter, start);
	while(pos != null)
	{
		result.append(string.slice(start, pos));
		if(limit != null && result.len() >= limit) return result;

		start = pos + delimiter.len();
		pos = string.find(delimiter, start);
	}

	if(start != string.len())
		result.append(string.slice(start));

	return result;
}

function _SuperLib_Helper::FindFromEnd(substr, string, startidx = null)
{
	local substr_len = substr.len();
	local i = startidx == null? string.len() - substr_len: startidx;
	i = min(i, string.len() - substr_len);
	for(; i >= 0; i--)
	{
		if(string.slice(i, i + substr_len) == substr)
			break;
	}

	return i >= 0? i : null;
}

function _SuperLib_Helper::FindCharFromEnd(findchar, string, startidx = null)
{
	local i = startidx == null? string.len() - 1 : startidx;
	for(; i >= 0; i--)
	{
		if(string[i] == findchar)
			break;
	}

	return i >= 0? i : null;
}

function _SuperLib_Helper::GetCurrentDateString()
{
	local date = AIDate.GetCurrentDate();
	return _SuperLib_Helper.GetDateString(date);
}

function _SuperLib_Helper::GetDateString(date)
{
	local year = AIDate.GetYear(date);
	local month = AIDate.GetMonth(date);
   	local day = AIDate.GetDayOfMonth(date);

	return year + "-" + (month < 10? "0" + month : month) + "-" + (day < 10? "0" + day : day);
}

function _SuperLib_Helper::SetSign(tile, message, force_build_sign = false)
{
	if(!force_build_sign && AIController.GetSetting("debug_signs") != 1)
		return -1;

	local found = false;
	local sign_list = AISignList();
	local result = -1;
	foreach(i, _ in sign_list)
	{
		if(AISign.GetLocation(i) == tile)
		{
			if(found)
				AISign.RemoveSign(i);
			else
			{
				if(message == "")
					AISign.RemoveSign(i);
				else
					result = AISign.SetName(i, message);
				found = true;
			}
		}
	}

	if(!found)
		result = AISign.BuildSign(tile, message);

	return result;
}

// Places a sign on tile sign_tile and waits until the sign gets removed
function _SuperLib_Helper::BreakPoint(sign_tile, force_break_point = false)
{
	if(force_break_point != false)
	{
		if(_SuperLib_Helper.HasSign("no_break"))
			return;

		if(!_SuperLib_Helper.HasSign("break_on"))
		{
			if(AIController.GetSetting("debug_signs") != 1)
				return;

		}
	}

	/* This message is so important, so it do not use the log system to not get
	 * suppressed by it.
	 */
	AILog.Warning("Break point reached. -> Remove the \"break\" sign to continue.");
	_SuperLib_Helper.SetSign(sign_tile, ""); // remove any signs on the tile first
	local sign = AISign.BuildSign(sign_tile, "break");
	while(AISign.IsValidSign(sign)) { AIController.Sleep(1); }
}

function _SuperLib_Helper::HasSign(text)
{
	return _SuperLib_Helper.GetSign(text) != -1;
}
function _SuperLib_Helper::GetSign(text)
{
	local sign_list = AISignList();
	foreach(i, _ in sign_list)
	{
		if(AISign.GetName(i) == text)
		{
			return i;
		}
	}
	return -1;
}
function _SuperLib_Helper::HasSignAt(tile)
{
	return _SuperLib_Helper.GetSignAt(tile) != -1;
}
function _SuperLib_Helper::GetSignAt(tile)
{
	local sign_list = AISignList();
	foreach(i, _ in sign_list)
	{
		if(AISign.GetLocation(i) == tile)
		{
			return i;
		}
	}
	return -1;
}
function _SuperLib_Helper::ClearAllSigns(except_tile = -1)
{
	local sign_list = AISignList();
	foreach(i, _ in sign_list)
	{
		if (except_tile != -1 && AISign.GetLocation(i) == except_tile) continue;
		AISign.RemoveSign(i);
	}
}

/*function _SuperLib_Helper::MyClassValuate(list, valuator, valuator_class, ...)
{
   assert(typeof(list) == "instance");
   assert(typeof(valuator) == "function");

   local args = [valuator_class, null];

   for(local c = 0; c < vargc; c++) {
      args.append(vargv[c]);
   }

   foreach(item, _ in list) {
      args[1] = item;
      local value = valuator.acall(args);
      if (typeof(value) == "bool") {
         value = value ? 1 : 0;
      } else if (typeof(value) != "integer") {
         throw("Invalid return type from valuator");
      }
      list.SetValue(item, value);
   }
}*/

function _SuperLib_Helper::ListValueSum(ai_list)
{
	local sum = 0;
	foreach(item, value in ai_list)
	{
		sum += value
	}

	return sum;
}

function _SuperLib_Helper::CopyListSwapValuesAndItems(old_list)
{
	local new_list = AIList();
	foreach(i, _ in old_list)
	{
		local value = old_list.GetValue(i);
		new_list.AddItem(value, i);
	}

	return new_list;
}

function _SuperLib_Helper::GetListMinValue(ai_list)
{
	ai_list.Sort(AIList.SORT_BY_VALUE, true); // highest last
	return ai_list.GetValue(ai_list.Begin());
}

function _SuperLib_Helper::GetListMaxValue(ai_list)
{
	ai_list.Sort(AIList.SORT_BY_VALUE, false); // highest first
	return ai_list.GetValue(ai_list.Begin());
}

function _SuperLib_Helper::SquirrelListToAIList(squirrel_list)
{
	local ai_list = AIList();
	foreach(item in squirrel_list)
	{
		ai_list.AddItem(item, 0);
	}

	return ai_list;
}

// RETURN null if not found, else the key to the found value.
function _SuperLib_Helper::ArrayFind(array, toFind)
{

	foreach(key, val in array)
	{
		if(val == toFind)
		{
			return key;
		}
	}
	return null;
}

function _SuperLib_Helper::GetPAXCargo()
{
	if(!AICargo.IsValidCargo(_SuperLib_Helper_private_pax_cargo))
	{
		local cargo_list = AICargoList();
		cargo_list.Valuate(AICargo.HasCargoClass, AICargo.CC_PASSENGERS);
		cargo_list.KeepValue(1);
		cargo_list.Valuate(AICargo.GetTownEffect);
		cargo_list.KeepValue(AICargo.TE_PASSENGERS);

		local pax_cargo = _SuperLib_Helper.GetCargoWithLargestAvailabilityInLargestTown(cargo_list);

		if(!AICargo.IsValidCargo(pax_cargo))
		{
			_SuperLib_Log.Error("PAX cargo do not exist", _SuperLib_Log.LVL_INFO);
			return -1;
		}

		// Remember the cargo id of pax
		_SuperLib_Helper_private_pax_cargo = pax_cargo;
		return cargo_list.Begin();
	}

	return _SuperLib_Helper_private_pax_cargo;
}

function _SuperLib_Helper::GetMailCargo()
{
	if(!AICargo.IsValidCargo(_SuperLib_Helper_private_mail_cargo))
	{
		local cargo_list = AICargoList();
		cargo_list.Valuate(AICargo.HasCargoClass, AICargo.CC_MAIL);
		cargo_list.KeepValue(1);
		cargo_list.Valuate(AICargo.GetTownEffect);
		cargo_list.KeepValue(AICargo.TE_MAIL);

		local mail_cargo = _SuperLib_Helper.GetCargoWithLargestAvailabilityInLargestTown(cargo_list);

		if(!AICargo.IsValidCargo(mail_cargo))
		{
			_SuperLib_Log.Error("Mail cargo do not exist", _SuperLib_Log.LVL_INFO);
			return -1;
		}

		// Remember the cargo id of mail
		_SuperLib_Helper_private_mail_cargo = mail_cargo;
		return cargo_list.Begin();
	}

	return _SuperLib_Helper_private_mail_cargo;
}

function _SuperLib_Helper::GetCargoWithLargestAvailabilityInLargestTown(cargo_list)
{
	if(cargo_list.Count() < 1) // zero cargoes?
		return -1;
	else if(cargo_list.Count() < 2) // only one cargo?
		return cargo_list.Begin();

	// Check which cargo that has biggest availability in the biggest town
	local town_list = AITownList();
	town_list.Valuate(AITown.GetPopulation);
	town_list.KeepTop(1);

	local top_town = town_list.Begin();
	local town_tile = AITown.GetLocation(top_town);
	if(AITown.IsValidTown(top_town))
	{
		foreach(cargo_id, _ in cargo_list)
		{
			local radius = 5;
			local acceptance = AITile.GetCargoAcceptance(town_tile, cargo_id, 1, 1, radius);

			cargo_list.SetValue(cargo_id, acceptance);
		}

		// Keep the most accepted cargo
		cargo_list.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
		cargo_list.KeepTop(1);
	}

	return cargo_list.Begin();
}

function _SuperLib_Helper::GetTownProducedCargoList()
{
	if (_SuperLib_Helper_private_town_produced_cargo_list  == null)
	{
		_SuperLib_Helper_private_town_produced_cargo_list = AIList();
		_SuperLib_Helper_private_town_produced_cargo_list.AddItem(_SuperLib_Helper.GetPAXCargo(), 0);
		_SuperLib_Helper_private_town_produced_cargo_list.AddItem(_SuperLib_Helper.GetMailCargo(), 0);
	}

	local result = AIList();
	result.AddList(_SuperLib_Helper_private_town_produced_cargo_list);
	return result;
}

function _SuperLib_Helper::GetTownAcceptedCargoList()
{
	if (_SuperLib_Helper_private_town_accepted_cargo_list  == null)
	{
		_SuperLib_Helper_private_town_accepted_cargo_list = AIList();
		_SuperLib_Helper_private_town_accepted_cargo_list.AddItem(_SuperLib_Helper.GetPAXCargo(), 0);
		_SuperLib_Helper_private_town_accepted_cargo_list.AddItem(_SuperLib_Helper.GetMailCargo(), 0);

		local cargos = AICargoList();
		foreach(cargo_id, _ in cargos)
		{
			local label = AICargo.GetCargoLabel(cargo_id);
			if (label == "GOOD")
				_SuperLib_Helper_private_town_accepted_cargo_list.AddItem(cargo_id, 0);
			if (label == "FOOD")
				_SuperLib_Helper_private_town_accepted_cargo_list.AddItem(cargo_id, 0);
			if (label == "FZDR") // Fizzy drinks
				_SuperLib_Helper_private_town_accepted_cargo_list.AddItem(cargo_id, 0);
			if (label == "SWET") // Sweets
				_SuperLib_Helper_private_town_accepted_cargo_list.AddItem(cargo_id, 0);
		}
	}

	local result = AIList();
	result.AddList(_SuperLib_Helper_private_town_accepted_cargo_list);
	return result;
}

// This function comes from AdmiralAI, version 22, written by Yexo
function _SuperLib_Helper::CallFunction(func, args)
{
	switch (args.len()) {
		case 0: return func();
		case 1: return func(args[0]);
		case 2: return func(args[0], args[1]);
		case 3: return func(args[0], args[1], args[2]);
		case 4: return func(args[0], args[1], args[2], args[3]);
		case 5: return func(args[0], args[1], args[2], args[3], args[4]);
		case 6: return func(args[0], args[1], args[2], args[3], args[4], args[5]);
		case 7: return func(args[0], args[1], args[2], args[3], args[4], args[5], args[6]);
		case 8: return func(args[0], args[1], args[2], args[3], args[4], args[5], args[6], args[7]);
		default: throw "Too many arguments to CallFunction";
	}
}

// This function comes from AdmiralAI, version 22, written by Yexo
function _SuperLib_Helper::Valuate(list, valuator, ...)
{
	assert(typeof(list) == "instance");
	assert(typeof(valuator) == "function");

	local args = [null];

	for(local c = 0; c < vargc; c++) {
		args.append(vargv[c]);
	}

	foreach(item, _ in list) {
		args[0] = item;
		local value = _SuperLib_Helper.CallFunction(valuator, args);
		if (typeof(value) == "bool") {
			value = value ? 1 : 0;
		} else if (typeof(value) != "integer") {
			throw("Invalid return type from valuator");
		}
		list.SetValue(item, value);
	}
}

function _SuperLib_Helper::Min(x1, x2)
{
	return x1 < x2? x1 : x2;
}

function _SuperLib_Helper::Max(x1, x2)
{
	return x1 > x2? x1 : x2;
}

function _SuperLib_Helper::Clamp(x, min, max)
{
	x = _SuperLib_Helper.Max(x, min);
	x = _SuperLib_Helper.Min(x, max);
	return x;
}

function _SuperLib_Helper::Abs(a)
{
	return a >= 0? a : -a;
}

// Private static variable - don't touch (read or write) from the outside.
_SuperLib_Helper_private_pax_cargo <- -1;
_SuperLib_Helper_private_mail_cargo <- -1;

_SuperLib_Helper_private_town_accepted_cargo_list <- null;
_SuperLib_Helper_private_town_produced_cargo_list <- null;

