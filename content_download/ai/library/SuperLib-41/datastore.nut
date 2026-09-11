/*
 * This file is part of SuperLib.DataStore, which is an AI Library for OpenTTD
 * Copyright (C) 2008-2012  Zuu
 *
 * SuperLib.DataStore is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License
 *
 * SuperLib.DataStore is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with SuperLib.DataStore; If not, see <http://www.gnu.org/licenses/> or
 * write to the Free Software Foundation, Inc., 51 Franklin Street,
 * Fifth Floor, Boston, MA 02110-1301 USA.
 *
 */

class _SuperLib_DataStore
{
	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Data encoding/decoding                                          //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	/*
	 * Creates a string such as 0001 from a integer typed value
	 */
	static function IntToStrFill(int_val, num_digits);


	/*
	 * These two functions can be used to encode a integer value in a string.
	 * if encode_chars is null, it defaults to a 84-base characterset which
	 * has been designed to produce smilies for low values.
	 *
	 * @param int_val integer value to encode
	 * @param str_len minimum string length. The first character in the set
	 * of characters to use will be used as 'zero' to fill out the string.
	 * @param encode_chars a string with the characters to use as symbols. To
	 * get a standard 10-base result use "0123456789". If you omit this parameter
	 * or pass null, a 84-base character set will be used. The characters has
	 * been ordered such that it will produce smilies for low numbers.
	 *
	 * @ return a string
	 */
	static function EncodeIntegerInStr(int_val, str_len, encode_chars = null);
	/*
	 * @param str string to decode
	 * @param encode_chars same usage and rules as for the encode_chars
	 * parameter to EncodeIntegerInStr. You must pass the same value as
	 * encode_chars to EncodeIntegerInStr and DecodeIntegerFromStr to
	 * be able to decode your string correctly.
	 *
	 * @return a integer value
	 */
	static function DecodeIntegerFromStr(str, encode_chars = null);


	/*
	 * This is the default set of characters that is used if you don't specify something else
	 * with the encode_chars parameter to EncodeIntegerInStr and DecodeIntegerFromStr.
	 *
	 * For low 2-digit values it produces smilies. (yes I missed some variants that could produce
	 * some more smilies, but I won't change the default value to fix this as that will break for
	 * anyone who uses EncodeIntegerInStr/DecodeIntegerFromStr with the default set)
	 */
	static SMILEY_ENCODE_CHARS = ":)D|(/spOo3SP><{}[]$012456789abcdefghijklmnqrtuvwxyzABCEFGHIJKLMNQRTUVWXYZ?&;#=@!\\%";

	/*
	 * The same 84 characters as in SMILEY_ENCODE_CHARS, but in a more traditional order.
	 */
	static PLAIN_ENCODE_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ{}[]$?&<>;/()|#:=@!\\%";

	static HEX_ENCODE_CHARS = "0123456789abcdef";
	static BIN_ENCODE_CHARS = "01";

	//////////////////////////////////////////////////////////////////////
	//                                                                  //
	//  Store/read data                                                 //
	//                                                                  //
	//////////////////////////////////////////////////////////////////////

	// The string str, has to be short enough that there is room to add some extra random characters at the end so that an unique name is created
	// The extra characters at the end will be created by using EncodeIntegerInStr with raising
	// integer values. If you don't want the SMILEY_ENCODE_CHARS character set, you can pass
	// a different one through the optional encode_chars parameter

	// WARNING: In order for ReadStrFrom*Name to work, the encode_chars parameter must not contain
	// a space! (if you use DataStore.*_ENCOED_CHARS, you are safe. Only if you make your own
	// string you must make sure it doesn't contain a space)
	static function StoreInStationName(station_id, str, encode_chars = null);
	// If station_id is not a valid station, an empty string is returned.
	static function ReadStrFromStationName(station_id);

	// Similar but for vehicle names
	static function StoreInVehicleName(vehicle_id, str, encode_chars = null);
	// If vehicle_id is not a valid station, an empty string is returned.
	static function ReadStrFromVehicleName(vehicle_id);

	// Generic store/read (works for any API class which have GetName/SetName with the same
	// parameter order as AIVehicle)
	static function StoreInObjectName(obj_id, obj_api_class, str, encode_chars = null);
	// If obj_id is not a valid object, an empty string is returned.
	static function ReadStrFromObjectName(obj_id, obj_api_class);
}

function _SuperLib_DataStore::EncodeIntegerInStr(int_val, str_len, encode_chars = null)
{
	// Default to DataStore.SMILEY_ENCODE_CHARS if no encode characters have been given.
	if(encode_chars == null)
	{
		encode_chars = _SuperLib_DataStore.SMILEY_ENCODE_CHARS;
	}

	// First convert the integer value into the new base
	local i = int_val;
	local base = encode_chars.len();

	local str = "";

	while(i >= base)
	{
		local div = (i / base).tointeger();
		local reminder = i - div * base;

		str = encode_chars[reminder].tochar() + str;

		i = div;
	}

	str = encode_chars[i].tochar() + str;

	// second append zeros at the beginning ot fill up the entire str_len

	while(str.len() < str_len)
	{
		str = encode_chars[0].tochar() + str;
	}

	return str;
}

function _SuperLib_DataStore::DecodeIntegerFromStr(str)
{
	// Default to DataStore.SMILEY_ENCODE_CHARS if no encode characters have been given.
	if(encode_chars == null)
	{
		encode_chars = _SuperLib_DataStore.SMILEY_ENCODE_CHARS;
	}

	local base10_val = 0;

	for(local i = 0; i < str.len(); ++i)
	{
		local c = str[i];
		local enc_base_val = encode_chars.find(c);

		base10_val += (str.len() - i) * enc_base_val;
	}

	return base10_val;
}

function _SuperLib_DataStore::StoreInStationName(station_id, str, encode_chars = null)
{
	if(!AIStation.IsValidStation(station_id))
		return false;

	return _SuperLib_DataStore.StoreInObjectName(station_id, AIBaseStation, str, encode_chars);
}

function _SuperLib_DataStore::ReadStrFromStationName(station_id)
{
	return _SuperLib_DataStore.ReadStrFromObjectName(station_id, AIBaseStation);
}

function _SuperLib_DataStore::StoreInVehicleName(vehicle_id, str, encode_chars = null)
{
	if(!AIVehicle.IsValidVehicle(vehicle_id))
		return false;

	return _SuperLib_DataStore.StoreInObjectName(vehicle_id, AIVehicle, str, encode_chars);
}

function _SuperLib_DataStore::ReadStrFromVehicleName(vehicle_id)
{
	return _SuperLib_DataStore.ReadStrFromObjectName(vehicle_id, AIVehicle);
}

function _SuperLib_DataStore::StoreInObjectName(obj_id, obj_api_class, str, encode_chars = null)
{
	if(encode_chars == null)
	{
		encode_chars = _SuperLib_DataStore.SMILEY_ENCODE_CHARS;
	}

	local i = 1;
	local obj_name = str + " " + _SuperLib_DataStore.EncodeIntegerInStr(i, 2, encode_chars);

	while(!obj_api_class.SetName(obj_id, obj_name))
	{
		i++;
		obj_name = str + " " + _SuperLib_DataStore.EncodeIntegerInStr(i, 2, encode_chars);

		if(i > 9000)
		{
			_SuperLib_Log.Error("Failed to give name to object 9000 times. Obj name: " + str, _SuperLib_Log.LVL_INFO);
			return false;
		}
	}

	return true;
}

function _SuperLib_DataStore::ReadStrFromObjectName(obj_id, obj_api_class)
{
	// get the part of the name after the last space
	local name = obj_api_class.GetName(obj_id);
	if (name == null) return "";

	local i = _SuperLib_Helper.FindCharFromEnd(' ', name);
	if(i == null) return name; // safe guard against object names without a space (in that case return entire string)

	local str = name.slice(0, i);
	return str;
}

