/*
 * this file is part of superlib, which is an ai library for openttd
 * copyright (c) 2008-2012  Zuu
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
 * GAME SCRIPT only - this sub library does only work with Game Scripts.
 */

class _SuperLib_Story {

	/**
	 * This function creates a new story page with page elements.
	 * If any part fails, the page will be removed and the
	 * function returns -1.
	 *
	 * This function verify that the Story Book API exist before trying to
	 * call it. Thus you can use it to display pages that will show for
	 * users that play with a recent enough OpenTTD version without breaking
	 * compatibility with older OpenTTD versions.
	 *
	 * Args:
	 *  company, title, [ [type, reference, text], [type, reference, text], [type, reference, text], ... ]
	 *   or
	 *  company, title,   type, reference, text,   type, reference, text,   type, reference, text, ...
	 *
	 * 1) Each element is passed as an array with three unnamed elements. All elements are packed into an array.
	 * 2) Each element is passed as a sequence of three arguments.
	 *
	 * See the API docs for StoryPage.NewElement for details on the allowed page element arguments.
	 *
	 * Return:
	 *  The page id of created page or -1 if anything fails.
	 */
	function NewStoryPage(company, title, ...);

	/*
	 * As above, but with a different return value:
	 *
	 * Return:
	 *  An array where the first index contain page id or -1 if anything
	 *  fails. The following array items contain the id of each page element
	 *  in the same order as the page elements were created.
	 */
	function NewStoryPage2(company, title, ...);

	/*
	 * This method automatically display a given message in the story book
	 * if a new enough OpenTTD version is used. On older versions, it falls
	 * back to GSGoal.Question. When it falls back, the title will not be
	 * displayed.
	 *
	 * The intention is for scripts that want to allow nightly users to
	 * read messages nicely in the story book while still not cutting the
	 * support for 1.3 users. Later when 1.4 is out, you should probably
	 * look into using the Story Book API directly or through the
	 * NewStoryPage method above. That way you can provide hook better into
	 * all features of the Story Book.
	 *
	 * @param company The company ID of the receiver or
	 * GSCompany.COMPANY_INVALID if the message should be viewed by everyone.
	 * @param text A GSText object with the body text.
	 * @param title A GSText object with the title text or null to not set a title.
	 * @param question_id You can optionally set the unique id of the question window.
	 * @param question_type You can optionally set the question type
	 * @param question_type You can optionally set the question buttons
	 *
	 * @return if it fails, it returns -1. If IsStoryBookAvailable() returns
	 * true, the return value of this method will be the story page id,
	 * otherwise a value >= 0 is returned on success.
	 */
	function ShowMessage(company, text, title = null, question_id = 0, question_type = GSGoal.QT_INFORMATION, question_buttons = GSGoal.BUTTON_CLOSE);

	/*
	 * Returns true if the story book feature is available.
	 */
	function IsStoryBookAvailable();

	/* Private: Used internally by IsStoryBookAvailable */
	static APICheck = this;
}

function _SuperLib_Story::NewStoryPage(company, title, ...)
{
	// Read the arguments, and convert to a stacked array if
	// flat multiple arguments was used.
	local stacked_array = [];
	if (vargc == 1) {
		stacked_array = vargv[0];
	} else {
		for (local c = 0; c + 2 < vargc; c+= 3) {
			stacked_array.append([vargv[c], vargv[c+1], vargv[c+2]]);
		}
	}

	local ret = _SuperLib_Story.NewStoryPage2(company, title, stacked_array)
	return ret[0];
}

function _SuperLib_Story::NewStoryPage2(company, title, ...)
{
	local ERROR = [-1];
	if (!_SuperLib_Story.IsStoryBookAvailable()) return ERROR;

	local page_id = GSStoryPage.New(company, title);
	if (!GSStoryPage.IsValidStoryPage(page_id)) {
		_SuperLib_Log.Error("NewStoryPage: Failed to create page", _SuperLib_Log.LVL_INFO);
		return ERROR;
	}
	local result = [page_id];

	// Convert args to the stacked array format
	local stacked_array = [];
	if (vargc == 1) {
		stacked_array = vargv[0];
	} else {
		for (local c = 0; c + 2 < vargc; c+= 3) {
			stacked_array.append([vargv[c], vargv[c+1], vargv[c+2]]);
		}
	}

	// Process element array
	foreach(element in stacked_array) {
		local type = element[0];
		local ref = element[1];
		local text = element[2];

		local pe = GSStoryPage.NewElement(page_id, type, ref, text);
		if (!GSStoryPage.IsValidStoryPageElement(pe)) {
			_SuperLib_Log.Error("NewStoryPage: Failed to add element", _SuperLib_Log.LVL_INFO);
			GSStoryPage.Remove(page_id);
			return ERROR;
		}
		result.append(pe);
	}

	return result;
}


function _SuperLib_Story::ShowMessage(company, text, title = null, question_id = 0, question_type = GSGoal.QT_INFORMATION, question_buttons = GSGoal.BUTTON_CLOSE)
{
	if (_SuperLib_Story.IsStoryBookAvailable()) {
		local page = _SuperLib_Story.NewStoryPage(company, title, GSStoryPage.SPET_TEXT, 0, text);
		if (page != -1) GSStoryPage.Show(page);
		return page;
	} else {
		return GSGoal.Question(question_id, company, text, question_type, question_buttons) ? 0 : -1;
	}
}

function _SuperLib_Story::IsStoryBookAvailable()
{
	/*
	 * Thanks to Krinn for this API check solution.
	 */
	if (!("GSStoryPage" in _SuperLib_Story.APICheck)) return false;

	/*
	 * Require minimum r25621 to consider GSStoryPage as existing.
	 * r25620 and r25621 fixes to critical bugs of the Story Book.
	 * Before that it is better to fall back to GSGoal.Question
	 * than annoying users with known bugs.
	 */
	local version = _SuperLib_Helper.GetOpenTTDVersion();
	return version.Revision >= 25621;
}
