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

/* SuperLib is a library that consists of many sub libraries with
 * code mainly from CluelessPlus and PAXLink.
 *
 * A general help and FAQ section exists after the main class
 * declaration below in this file. You may also see the
 * TT-forums thread about this library at:
 *   http://www.tt-forums.net/viewtopic.php?f=65&t=47525
 *
 * Open each sub-library file to find the interface documentation.
 */

require("version.nut");

require("result.nut");
require("log.nut");
require("helper.nut");
require("datastore.nut");
require("scorelist.nut");
require("money.nut");

require("tile.nut");
require("direction.nut");

require("engine.nut");
require("vehicle.nut");

require("town.nut");
require("industry.nut");

require("station.nut");
require("airport.nut");
require("order.nut");

require("road.nut");
require("roadpathfinder.nut");
require("roadbuilder.nut");

require("rail.nut");

/* <gs-only>
require("story.nut");
</gs-only> */

class SuperLib
{
	/* For accessing the sub libraries
	 * See the help further down.
	 */
	static Result = _SuperLib_Result;
	static Log = _SuperLib_Log;
	static Helper = _SuperLib_Helper;
	static DataStore = _SuperLib_DataStore;
	static ScoreList = _SuperLib_ScoreList;
	static Money = _SuperLib_Money;

	static Tile = _SuperLib_Tile;
	static Direction = _SuperLib_Direction;

	static Engine = _SuperLib_Engine;
	static Vehicle = _SuperLib_Vehicle;

	static Town = _SuperLib_Town;
	static Industry = _SuperLib_Industry;

	static Station = _SuperLib_Station;
	static Airport = _SuperLib_Airport;
	static Order = _SuperLib_Order;
	static OrderList = _SuperLib_OrderList;

	static Road = _SuperLib_Road;
	static RoadPathFinder = _SuperLib_RoadPathFinder;
	static RoadBuilder = _SuperLib_RoadBuilder;

	static Rail = _SuperLib_Rail;

	/* <gs-only>
	static Story = _SuperLib_Story;
	</gs-only> */
}

/* Q: How to use the sub libraries without the SuperLib prefix?
 *
 * A: Import the library under a name, eg SuperLib and then make global
 *    pointers to those sub-libraries that you want to use:
 *
 *      Import("util.superlib", "SuperLib", 1);
 *
 *      Helper <- SuperLib.Helper;
 *      Direction <- SuperLib.Direction;
 *      Tile <- SuperLib.Tile;
 *
 *    Then you can call eg. Helper.SetSign(some_tile, "sign text");
 */

/* Info: SuperLib contains a Log system which you either can use in your own
 *    AI or just live with the fact that SuperLib internally uses it.
 *
 *    More info about the log system can be found in log.nut including
 *    help for using it in your AI and how to change the amount of information
 *    that is printed to the logs.
 */

/* Q: What is all this _SuperLib_... that I see all over?
 *
 * A: Unfortunately due to constraints in OpenTTD and Squirrel, only the main
 *    class of a library will be renamed at import. For SuperLib that is the
 *    SuperLib class in this file. Every other class in this file or other
 *    .nut files that the library is built up by will end up at the global
 *    scope at the AI that imports the library. The global scope of the
 *    library will get merged with the global scope of your AI.
 *
 *    To reduce the risk of causing you conflict problems this library
 *    prefixes everything that ends up at the global scope of AIs with
 *    _SuperLib_. That is also why the library is not named Utils or something
 *    with higher risk of you already having at your global scope.
 *
 *    And to answer your ideas of splitting the library apart into many
 *    libraries, one for each class, that has the limitation that you
 *    can't have circular dependencies between your libraries which is needed.
 *
 *    You should however never need to use any of the _SuperLib_.. names as a
 *    user of this library. It is not even recommended to do so as it is
 *    part of the implementation and could change without notice.
 */
