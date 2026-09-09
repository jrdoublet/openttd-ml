/*
 * This file is part of SuperLib, which is an AI Library for OpenTTD
 * Copyright (C) 2010-2012  Zuu
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

/* Hello!
 *
 * Thanks for the interest in this library. Please see the main.nut
 * file for general information about this library.
 *
 * The library is adopted to OpenTTD API version 15
 */

/*
 * Hall of fame - bug reports, fixes and code contributions:
 *   11Runner
 *   Core Xii
 *   fanioz
 *   Kogut
 *   krinn
 *   MinchinWeb
 *   teshiron
 *   R2dical
 *   yorg
 *   Xaric
 *
 * Have I forgot you? tell me!
 */

require("version.nut");

class SuperLib extends AILibrary {
	function GetAuthor()      { return "Zuu"; }
	function GetName()        { return "SuperLib"; }
	function GetShortName()   { return "SPRL"; }
	function GetDescription() { return "SuperLib contains common functions used by Zuu's CluelessPlus, PAXLink, TownCars, IdleMore, TutorialAI and Game Scripts. Other AI and GameScript authors are also welcome to use this library."; }
	function GetAPIVersion()  { return "15"; }
	function GetVersion()     { return _SuperLib_VERSION; }
	function GetDate()        { return "2026-02-07"; }
	function GetURL()         { return "http://junctioneer.net/o-ai/SuperLib"; }
	function CreateInstance() { return "SuperLib"; }
	function GetCategory()    { return "Util"; }
}

RegisterLibrary(SuperLib());
