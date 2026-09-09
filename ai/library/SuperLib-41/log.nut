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

//////////////////////////////////////////////////////////////////////
//                                                                  //
//  How to use Log                                                  //
//                                                                  //
//////////////////////////////////////////////////////////////////////

/*
 * 1. I will assume that you import the log part of the SuperLib library
 *    Like this: (see main.nut for more info about importing)
 *
 *      Import("util.superlib", "SuperLib", 3);
 *      Log <- SuperLib.Log;
 *
 *
 * 2. To write to the log
 *
 *      Log.Info("Hello world!", Log.LVL_DEBUG);
 *      Log.Info("A new industry appeared, let's connect it", Log.LVL_INFO);
 *      Log.Info("There is a some farm tiles in the way, build around it to save some money", Log.LVL_SUB_DECISIONS);
 *
 *      Log.Error("Out of money", Log.LVL_INFO);
 *      // ..
 *
 *    You can use one of the tree functions Info, Warning and Error that
 *    corresponds to the AILog.Info, AILog.Warning and AILog.Error functions
 *    and thus decides which color will be used at the AIDebug window.
 *
 *    The second choice you have (apart from what to write to the log) is
 *    which log level to use. Lower level values will be more 'likely' to
 *    be accepted. Eg. if the accepted level limit is at
 *    2 = LVL_SUB_DECISIONS, then only log messages with a level of 2 or
 *    lower will be printed to the log; all ather messages will be
 *    discarded.
 *
 *
 * 3. How is the log level limit decided?
 *
 *    By default SuperLib.Log reads the AI setting "log_level" and uses
 *    that as the upper limit of allowed log level.
 *
 *    You can override that by writing your own function that decides
 *    which messages that should be accepted based on their log level.
 *    Your custom function must only return true or false and take an
 *    integer as the only argument. To register this function you call
 *    the function:
 *
 *      Log.SetIsLevelAcceptedFunction(new_function)
 *
 *    If you for example want to add a custom level that should be accepted
 *    as well as all messages of level 2 and below you can do it like this:
 *
 *      Log.SetIsLevelAcceptedFunction( function(log_level) { return log_level == SOME_CUSTOM_VALUE || log_level < 2; } );
 *
 *    Or if you want to turn off all log messages from SuperLib and use your
 *    own log system in your AI: (not recommended, as the INFO level messages
 *    are mostly error messages that you want to get.)
 *
 *      Log.SetIsLevelAcceptedFunction( function(log_level) { return false; } );
 */


//////////////////////////////////////////////////////////////////////
//                                                                  //
//  Log class                                                       //
//                                                                  //
//////////////////////////////////////////////////////////////////////

class _SuperLib_Log
{
	/* Log levels: */
	static LVL_INFO = 1;           // main info. eg what it is doing
	static LVL_SUB_DECISIONS = 2;  // sub decisions - eg. reasons for not doing certain things etc.
	static LVL_DEBUG = 3;          // debug prints - debug prints during carrying out actions

	/*
	 * The Info/Warning/Error names corresponds to which
	 * AILog.* function that will be used if the log level
	 * is accepted by Log.IsLevelAccepted.
	 *
	 * It is recommended to always send a log level as the defaults
	 * may change in future versions of this library.
	 */
	static function Info(text, log_level = 3);    // LVL_DEBUG
	static function Warning(text, log_level = 1); // LVL_INFO
	static function Error(text, log_level = 1);   // LVL_INFO

	/* This function will return true if the log level is accepted,
	 * else false.
	 *
	 * Actually this is just a wrapper function that will call
	 * either the default implementation or your own implementation
	 * that you set using SetIsLevelAcceptedFunction, see below.
	 */
	static function IsLevelAccepted(log_level);

	/* Call this function to set a custom function for determining
	 * which log messages that should be accepted. See the usage
	 * help above for some examples.
	 *
	 * After having called this function, Log.IsLevelAccepted will
	 * call your custom function to get the result and then return it.
	 */
	static function SetIsLevelAcceptedFunction(new_function);
};

function _SuperLib_Log::Info(text, log_level = _SuperLib_Log.LVL_DEBUG)
{
	if (_SuperLib_Log.IsLevelAccepted(log_level)) AILog.Info("[" + _SuperLib_Helper.GetCurrentDateString() + "]  " + text);
}

function _SuperLib_Log::Warning(text, log_level = _SuperLib_Log.LVL_INFO)
{
	if (_SuperLib_Log.IsLevelAccepted(log_level)) AILog.Warning("[" + _SuperLib_Helper.GetCurrentDateString() + "]  " + text);
}

function _SuperLib_Log::Error(text, log_level = _SuperLib_Log.LVL_INFO)
{
	if (_SuperLib_Log.IsLevelAccepted(log_level)) AILog.Error("[" + _SuperLib_Helper.GetCurrentDateString() + "]  " + text);
}

function _SuperLib_Log::IsLevelAccepted(log_level)
{
	// Make sure the log_level is an integer as promised
	local ret = _SuperLib_Log_Private_IsLevelAccepted_Function(log_level.tointeger());

	if(typeof(ret) != "bool")
	{
		AILog.Error("SuperLib::Log::IsLevelAccepted: The underlying (probably custom) implementation of this function didn't return a boolean!");
		AILog.Error("SuperLib::Log::IsLevelAccepted: The type of the returned value was: " + typeof(ret));
		return true; // Print the log message as default, if the return type isn't a boolean
	}

	return ret;
}

function _SuperLib_Log::SetIsLevelAcceptedFunction(new_function)
{
	_SuperLib_Log_Private_IsLevelAccepted_Function = new_function;
}

//////////////////////////////////////////////////////////////////////
//                                                                  //
//  IsLevelAccepted default implementation                          //
//                                                                  //
//////////////////////////////////////////////////////////////////////

/* This is the default implementation of the function that decides if
 * a log message should be accepted or not.
 */
function _SuperLib_Log_Private_IsLevelAccepted_DefaultFunction(log_level)
{
	local ai_setting_log_level = AIController.GetSetting("log_level");

	if(ai_setting_log_level == -1)
	{
		// Only print messages of level LVL_INFO if the setting does not exist.
		return log_level <= 1;
	}

	return log_level <= ai_setting_log_level;
}

/* Here the default function is assigned to to an "internal" global scope
 * variable. This happens when you call the Import-function.
 */

_SuperLib_Log_Private_IsLevelAccepted_Function <- null; // First define the global var

/* Then call SetIsLevelAcceptedFunction so it gets tested (rather than just assigning to the global scope var) */
_SuperLib_Log.SetIsLevelAcceptedFunction(_SuperLib_Log_Private_IsLevelAccepted_DefaultFunction);

