/*
 * this file is part of superlib, which is an ai library for openttd
 * copyright (c) 2008-2011  Zuu
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

//
// This class mainly exist for legacy reasons as some of the
// code in SuperLib that comes from the old parts of CluelessPlus
// uses this code.
//

//
// What differs this class from the AIList is that the items
// does not need to be integers. It can store arrays, objects
// etc. in the list. The supported methods for scoring/sorting
// is not as many as in AIList.
//

//
// The terms used in ScoreList are:
//
// * value   (in AIList this is the key)
// * score   (in AIList this is the value)
//
// A valuator sets the score.
//

class _SuperLib_ScoreList
{
	list = null;

	sort_max = true;
	sorted = false;

	constructor() {
		list = [];
		sort_max = true;
		sorted = false;
	}

	function Push(value, score);
	function PopMax();
	function PopMin();

	function CompareMin(a, b); // min first
	function CompareMax(a, b); // max first

	// Calls a valuator functions that returns
	// a score for each item
	function ScoreValuate(class_instance, valuator, ...);
}

function _SuperLib_ScoreList::Push(value, score)
{
	list.append([value, score]);
	sorted = false;
}
function _SuperLib_ScoreList::PopMax()
{
	if(list.len() <= 0)
	{
		return null;
	}
	if(!sorted || sort_max)
	{
		list.sort(this.CompareMin);
	}

	return list.pop()[0];
}
function _SuperLib_ScoreList::PopMin()
{
	if(list.len() <= 0)
	{
		return null;
	}
	if(!sorted || !sort_max)
	{
		list.sort(this.CompareMax);
	}

	return list.pop()[0];
}
function _SuperLib_ScoreList::CompareMin(a, b)
{
	if(a[1] > b[1])
		return 1
	else if(a[1] < b[1])
		return -1
	return 0;
}
function _SuperLib_ScoreList::CompareMax(a, b)
{
	if(a[1] > b[1])
		return -1
	else if(a[1] < b[1])
		return 1
	return 0;
}

function _SuperLib_ScoreList::ScoreValuate(class_instance, valuator, ...)
{
	assert(typeof(valuator) == "function");

	local args = [class_instance, null];

	for(local c = 0; c < vargc; c++) {
		args.append(vargv[c]);
	}

	foreach(value_score_pair in list)
	{
		args[1] = value_score_pair[0];
		local score = valuator.acall(args);

		if (typeof(score) == "bool")
		{
			score = score ? 1 : 0;
		}
	   	else if (typeof(score) != "integer")
		{
			throw("Invalid return type from valuator");
		}

		// Update the score
		value_score_pair[1] = score;
	}

	this.sorted = false;
}
