/*
 * this file is part of superlib, which is an ai library for openttd
 * copyright (c) 2010-2011  Zuu
 *
 * superlib is free software; you can redistribute it and/or modify it
 * under the terms of the gnu general public license as published by
 * the free software foundation; version 2 of the license
 *
 * superlib is distributed in the hope that it will be useful,
 * but without any warranty; without even the implied warranty of
 * merchantability or fitness for a particular purpose.  see the
 * gnu general public license for more details.
 *
 * you should have received a copy of the gnu general public license
 * along with superlib; if not, see <http://www.gnu.org/licenses/> or
 * write to the free software foundation, inc., 51 franklin street,
 * fifth floor, boston, ma 02110-1301 usa.
 *
 */

/*
 * So far only a few functions use these return values.
 * Functions that only return success or fail, return a boolean.
 * Only when several fail-states exist, these values might be used.
 *
 * See function comments + implementation of the library function
 * you want to use.
 */

class _SuperLib_Result {

	static SUCCESS = 0;
	static FAIL = 1;
	static NOT_ENOUGH_MONEY = 2;
	static TIME_OUT = 3;
	static REBUILD_FAILED = 4; // when a destructive action failed and the original state couldn't be restored
	static MONEY_TOO_LOW = 5; // couldn't afford the action
	static TOWN_RATING_TOO_LOW = 6; // couldn't do the action because town rating was too low
	static TOWN_NOISE_ACCEPTANCE_TOO_LOW = 7;

	static function IsSuccess(return_val);
	static function IsFail(return_val);
}

/*static*/ function _SuperLib_Result::IsSuccess(return_val)
{
	return return_val == _SuperLib_Result.SUCCESS;
}

/*static*/ function _SuperLib_Result::IsFail(return_val)
{
	return return_val != _SuperLib_Result.SUCCESS;
}

