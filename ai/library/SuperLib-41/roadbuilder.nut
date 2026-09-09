/*
 * This file is part of SuperLib, which is an AI Library for OpenTTD
 * Copyright (C) 2011  Zuu
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
 * Warning: The RoadBuilder class is a bit talky on the log.
 * While most SuperLib classes are intended as low-level stuff
 * this class is a more complex higher level thing that assumes
 * that the world is interested in what it does.
 *
 * That is something that follows from CluelessPlus and might
 * change in the future, but not now.
 *
 * Also see the log class on how to disable all SuperLib log
 * messages all together if you don't use the SuperLib log system.
 */

class _SuperLib_RoadBuilder {

	pf_loops_used = null;
	build_loops_used = null;

	slow_pf = false;
	slow_build = false;
	estimate_multiplier = null;
	loan_limit = null;

	connect_tile1 = null;
	connect_tile2 = null;
	connect_repair = false;
	connect_max_loops = 4000;
	connect_forbidden_tiles = null;

	path = null;
	pf_error = null;

	constructor() {
		this.pf_loops_used = 0;
		this.build_loops_used = 0;
		this.slow_pf = false;
		this.slow_build = false;
		this.estimate_multiplier = 1;
		this.loan_limit = -1; // no limit

		this.connect_tile1 = null;
		this.connect_tile2 = null;
		this.connect_repair = false;
		this.connect_max_loops = 4000;
		this.connect_forbidden_tiles = [];

		this.path = null;
		this.pf_error = _SuperLib_RoadPathFinder.PATH_FIND_NO_ERROR;
	}


	// If repair_existing == true, then it should as much as possible avoid building road next to existing to get a tiny bit less penalty

	static CONNECT_SUCCEEDED = 0;            // Connection established from tile1 to tile2
	static CONNECT_FAILED_OTHER = 1;         // Failed for other reason
	static CONNECT_FAILED_TIME_OUT = 2;      // Pathfinder timeout
	static CONNECT_FAILED_NO_PATH_FOUND = 3; // Pathfinder failed to find path
	static CONNECT_FAILED_OUT_OF_TRIES = 4;  // Road building could not complete even after retrying X times

	//
	// 1) Call Init to tell RoadBuilder which tiles to connect, if it should attempt to repair
	// or build a new connection (repair => higher path-finding cost of building new road)
	//
	// 2) Optionally call DoPathfinding(). It will return true/false depending on if a path was
	// found.
	//
	// 3) Call ConnectTiles(). If DoPathfinding was called in step 2) it will use the path found
	// there, otherwise the pathfinder is used to find a path. ConnectTiles will try up to 4
	// times (if there is an obstacle built after path finding) to connect the tiles given by Init
	// with road.

	//
	// The idea is that in some conditions, you might want to do the initial path finding,
	// get the result of it before starting the work of connecting the tiles
    //

	function Init(tile1, tile2, repair_existing = false, max_loops = 4000, forbidden_tiles = []);

	function DoPathfinding();
	// Returns one of the CONNECT_* constants.
	function ConnectTiles(call_count = 1);


	// Call this function after ConnectTiles have returned to see how many loops that were used.
	// The values are accumulated since the instance was created in case ConnectTiles is called
	// multiple times or has to make recursive calls.
	function GetPFLoopsUsed();
	function GetBuildLoopsUsed();

	// Enable slow path finding + road building for ConnectTiles. This is known from the
	// "slow ai" setting in CluelessPlus.
	function EnableSlowAI(enable = true);

	// Enables slow path finding (but leaves road building speed untouched)
	function EnableSlowPathFinding(enable = true);

	// Enables slow building (but leaves path finding speed untouched)
	function EnableSlowBuilding(enable = true);

	// Pass a value that will be used to multiply the result of _Estimate in the path finder.
	// Passing a float value is supported, but the result after multiplying will be casted to
	// an integer. Recommended values: [1.0, 2.0]. Default: 1 (integer)
	// A higher value usually speeds up the pathfinding, at the cost that the pathfinder will
	// not spend as much time on finding solutions that reuse existing infrastructure.
	function SetEstimateMultiplier(estimate_multiplier);

	// loan_limit = maximum loan to take in order to afford construction. The loan is only
	// increased if a build action fails. A value <= 0 means that there is no limit (other
	// than the maximum loan imposed by OpenTTD).
	function SetLoanLimit(loan_limit);
}


function _SuperLib_RoadBuilder::Init(tile1, tile2, repair_existing = false, max_loops = 4000, forbidden_tiles = [])
{
	this.pf_loops_used = 0;

	this.connect_tile1 = tile1;
	this.connect_tile2 = tile2;
	this.connect_repair = repair_existing;
	this.connect_max_loops = max_loops;
	this.connect_forbidden_tiles = forbidden_tiles;

	this.path = null;
}

function _SuperLib_RoadBuilder::DoPathfinding()
{
	_SuperLib_Helper.SetSign(this.connect_tile1, "from");
	_SuperLib_Helper.SetSign(this.connect_tile2, "to");

	local try_tiles = [ {from = [this.connect_tile1], to = [this.connect_tile2] },
		  { from = [this.connect_tile2], to = [this.connect_tile1] } ];

	/*
	 * Run the pathfinder twice. First one time with very few iterations to see if the path is blocked from that
	 * direction. If it is blocked, don't do anything more and return failure. Otherwise, restart from the other
	 * direction and path-find from there, now with full max_iterations available.
	 */
	this.pf_loops_used = 0;
	this.pf_error = _SuperLib_RoadPathFinder.PATH_FIND_NO_ERROR;
	local i = 0;
	for(i = 0; i < 2; ++i)
	{
		local pathfinder = _SuperLib_RoadPathFinder();

		pathfinder.InitializePath(try_tiles[i].from, try_tiles[i].to, this.connect_repair, this.connect_forbidden_tiles, this.estimate_multiplier);

		pathfinder.SetStepSize(100);
		local max_iterations = this.connect_max_loops - this.pf_loops_used;
		local num_iterations = i == 0? 100 : max_iterations; // On first try, only do a few iterations to see if we run into a dead end.
		pathfinder.SetMaxIterations(num_iterations);
		this.path = null;
		this.pf_error = _SuperLib_RoadPathFinder.PATH_FIND_NO_ERROR;
		while (this.path == null && this.pf_error == _SuperLib_RoadPathFinder.PATH_FIND_NO_ERROR) {
			this.path = pathfinder.FindPath();
			this.pf_error = pathfinder.GetFindPathError();
			AIController.Sleep(1);

			if(this.slow_pf)
				AIController.Sleep(5);
		}
		this.pf_loops_used += pathfinder.GetIterationsUsed();

		if(path != null) break; // found path?
		if(i == 0 && this.pf_error != _SuperLib_RoadPathFinder.PATH_FIND_FAILED_TIME_OUT)
		{
			// Pathfinder stopped at first try for other reason than time out. => fail
			_SuperLib_Log.Info("PF stopped at first try for other reason than timeout => fail", _SuperLib_Log.LVL_DEBUG);
			this.pf_error = _SuperLib_RoadPathFinder.PATH_FIND_FAILED_NO_PATH;
			return false;
		}
	}

	// For ConnectTiles to work properly, we need to swap connect_tile1 and connect_tile2
	// when path was found backwards.
	if (i == 1) {
		local tmp = this.connect_tile1;
		this.connect_tile1 = this.connect_tile2;
		this.connect_tile2 = tmp;
	}

	_SuperLib_Log.Info("PF loops used:" + this.pf_loops_used, _SuperLib_Log.LVL_DEBUG);

	return this.path != null;
}

function _SuperLib_RoadBuilder::ConnectTiles(call_count = 1)
{
	_SuperLib_Log.Info("Connecting tiles - try no: " + call_count, _SuperLib_Log.LVL_DEBUG);

	if(this.path == null)
	{
		if(!this.DoPathfinding()) {
			if(this.pf_error == _SuperLib_RoadPathFinder.PATH_FIND_FAILED_TIME_OUT) {
				_SuperLib_Log.Warning("SuperLib: Timed out to find path. Used " + this.pf_loops_used + " of " + this.connect_max_loops + " loops", _SuperLib_Log.LVL_INFO);
				return _SuperLib_RoadBuilder.CONNECT_FAILED_TIME_OUT;
			} else {
				_SuperLib_Log.Warning("SuperLib: Failed to find path", _SuperLib_Log.LVL_INFO);
				return _SuperLib_RoadBuilder.CONNECT_FAILED_NO_PATH_FOUND;
			}
		}
	}

	_SuperLib_Helper.SetSign(this.connect_tile1, "from" + call_count);
	_SuperLib_Helper.SetSign(this.connect_tile2, "to" + call_count);

	_SuperLib_Log.Info("Path found, now start building!", _SuperLib_Log.LVL_SUB_DECISIONS);

	//AISign.BuildSign(path.GetTile(), "Start building");

	local pppp = this.path;
	_SuperLib_Log.Info("Path : " + this.path, _SuperLib_Log.LVL_DEBUG);
	while (this.path != null) {
		local par = this.path.GetParent();
		//_SuperLib_Helper.SetSign(this.path.GetTile(), "tile");
		if (par != null) {
			local last_node = this.path.GetTile();
			//_SuperLib_Helper.SetSign(par.GetTile(), "par");
			if (AIMap.DistanceManhattan(this.path.GetTile(), par.GetTile()) == 1 ) {
				if (AIRoad.AreRoadTilesConnected(this.path.GetTile(), par.GetTile())) {
					// there is already a road here, don't do anything
					//_SuperLib_Helper.SetSign(par.GetTile(), "conn");

					if (AITile.HasTransportType(par.GetTile(), AITile.TRANSPORT_RAIL))
					{
						// Found a rail track crossing the road, try to bridge it
						_SuperLib_Helper.SetSign(par.GetTile(), "rail!");

						local bridge_result = _SuperLib_Road.ConvertRailCrossingToBridge(par.GetTile(), this.path.GetTile());
						if (bridge_result.succeeded == true)
						{
							// TODO update par/path
							local new_par = par;
							while (new_par != null && new_par.GetTile() != bridge_result.bridge_start && new_par.GetTile() != bridge_result.bridge_end)
							{
								new_par = new_par.GetParent();
							}

							if (new_par == null)
							{
								_SuperLib_Log.Warning("Tried to convert rail crossing to bridge but somehow got lost from the found path.", _SuperLib_Log.LVL_INFO);
							}
							par = new_par;
						}
						else
						{
							_SuperLib_Log.Info("Failed to bridge railway crossing", _SuperLib_Log.LVL_INFO);
						}
					}

				} else {

					/* Look for longest straight road and build it as one build command */
					local straight_begin = this.path;
					local straight_end = par;

					if(!this.slow_build) // build piece by piece in slow-mode
					{
						local prev = straight_end.GetParent();
						while(prev != null &&
								_SuperLib_Tile.IsStraight(straight_begin.GetTile(), prev.GetTile()) &&
								AIMap.DistanceManhattan(straight_end.GetTile(), prev.GetTile()) == 1)
						{
							straight_end = prev;
							prev = straight_end.GetParent();
						}

						/* update the looping vars. (path is set to par in the end of the main loop) */
						par = straight_end;
					}

					//AISign.BuildSign(this.path.GetTile(), "path");
					//AISign.BuildSign(par.GetTile(), "par");

					// Build road, and if needed increase the loan
					local result = _SuperLib_Money.ExecuteWithLoan(this.loan_limit, function(from, to) {
						return AIRoad.BuildRoad(from, to);
					}, straight_begin.GetTile(), straight_end.GetTile());

					if (!result) {
						/* An error occured while building a piece of road. TODO: handle it.
						 * Note that is can also be the case that the road was already build. */

						_SuperLib_Helper.SetSign(straight_begin.GetTile(), "fail from");
						_SuperLib_Helper.SetSign(straight_end.GetTile(), "fail to");
						_SuperLib_Log.Warning("Build straight failed", _SuperLib_Log.LVL_SUB_DECISIONS);


						// Try PF again

						// Update connect tiles to only connect the part that is missing
						this.connect_tile2 = this.path.GetTile();
						this.connect_repair = false; // set repair := false as the road might be broken
						this.connect_max_loops = _SuperLib_Helper.Max(this.connect_max_loops, 4000);
						this.path = null; // re-do the pathfinding using the updated connect_* values.
						this.pf_error = _SuperLib_RoadPathFinder.PATH_FIND_FAILED_NO_PATH;
						if (call_count > 4 ||
								this.ConnectTiles(call_count+1) != _SuperLib_RoadBuilder.CONNECT_SUCCEEDED)
						{
							_SuperLib_Log.Warning("After several tries the road construction could still not be completed", _SuperLib_Log.LVL_INFO);
							return _SuperLib_RoadBuilder.CONNECT_FAILED_OUT_OF_TRIES;
						}
						else
						{
							return _SuperLib_RoadBuilder.CONNECT_SUCCEEDED;
						}
					}

					if(this.slow_build)
						AIController.Sleep(10);
				}
			} else {
				if (AIBridge.IsBridgeTile(this.path.GetTile())) {
					/* A bridge exists */

					_SuperLib_Helper.SetSign(this.path.GetTile(), "bridge exists", false);

					// Check if it is a bridge with low speed
					local bridge_type_id = AIBridge.GetBridgeType(this.path.GetTile())
					local bridge_max_speed = AIBridge.GetMaxSpeed(bridge_type_id);

					if(bridge_max_speed < 100) // low speed bridge
					{
						_SuperLib_Helper.SetSign(this.path.GetTile(), "exists slow", false);

						local other_end_tile = AIBridge.GetOtherBridgeEnd(this.path.GetTile());
						local bridge_length = AIMap.DistanceManhattan( this.path.GetTile(), other_end_tile ) + 1;
						local bridge_list = AIBridgeList_Length(bridge_length);

						bridge_list.Valuate(AIBridge.GetMaxSpeed);
						bridge_list.KeepAboveValue(bridge_max_speed);

						if(!bridge_list.IsEmpty())
						{
							_SuperLib_Helper.SetSign(this.path.GetTile(), "exists upgrade", false);
							// There is a faster bridge

							// Pick a random faster bridge than the current one
							bridge_list.Valuate(AIBase.RandItem);
							bridge_list.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);

							_SuperLib_Log.Info("Try to upgrade slow existing bridge", _SuperLib_Log.LVL_SUB_DECISIONS);

							// Upgrade the bridge
							AIBridge.BuildBridge( AIVehicle.VT_ROAD, bridge_list.Begin(), this.path.GetTile(), other_end_tile );

							_SuperLib_Log.Info("Upgrade err: " + AIError.GetLastErrorString() );
						}
					}

				} else if(AITunnel.IsTunnelTile(this.path.GetTile())) {
					/* A tunnel exists */

					// All tunnels have equal speed so nothing to do
				} else {
					/* Build a bridge or tunnel. */

					/* If it was a road tile, demolish it first. Do this to work around expended roadbits. */
					if (AIRoad.IsRoadTile(this.path.GetTile()) &&
							!AIRoad.IsRoadStationTile(this.path.GetTile()) &&
							!AIRoad.IsRoadDepotTile(this.path.GetTile())) {
						AITile.DemolishTile(this.path.GetTile());
					}
					if (AITunnel.GetOtherTunnelEnd(this.path.GetTile()) == par.GetTile()) {

						local result = _SuperLib_Money.ExecuteWithLoan(this.loan_limit, function(p1, p2) {
							return AITunnel.BuildTunnel(p1, p2);
						}, AIVehicle.VT_ROAD, this.path.GetTile());

						if (!result) {
							/* An error occured while building a tunnel. TODO: handle it. */
							_SuperLib_Log.Info("Build tunnel error: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_INFO);
						}
					} else {
						local bridge_list = AIBridgeList_Length(AIMap.DistanceManhattan(this.path.GetTile(), par.GetTile()) +1);
						bridge_list.Valuate(AIBridge.GetMaxSpeed);

						local result = _SuperLib_Money.ExecuteWithLoan(this.loan_limit, function(p1, p2, p3, p4) {
							return AIBridge.BuildBridge(p1, p2, p3, p4);
						}, AIVehicle.VT_ROAD, bridge_list.Begin(), this.path.GetTile(), par.GetTile());

						if (!result) {
							/* An error occured while building a bridge. TODO: handle it. */
							_SuperLib_Log.Info("Build bridge error: " + AIError.GetLastErrorString(), _SuperLib_Log.LVL_INFO);
						}
					}

					if(this.slow_build)
						AIController.Sleep(50); // Sleep a bit after tunnels
				}
			}
		}
		this.path = par;
		this.build_loops_used += 1;
	}

	_SuperLib_Log.Info("Build loops used:" + this.build_loops_used, _SuperLib_Log.LVL_DEBUG);
	//AISign.BuildSign(tile1, "Done");

	// Remove the from/to signs now that the road was successfully built
	_SuperLib_Helper.SetSign(this.connect_tile1, "");
	_SuperLib_Helper.SetSign(this.connect_tile2, "");

	return _SuperLib_RoadBuilder.CONNECT_SUCCEEDED;
}

function _SuperLib_RoadBuilder::GetPFLoopsUsed()
{
	return this.pf_loops_used;
}

function _SuperLib_RoadBuilder::GetBuildLoopsUsed()
{
	return this.build_loops_used;
}

function _SuperLib_RoadBuilder::EnableSlowAI(enable = true)
{
	this.slow_pf = enable;
	this.slow_build = enable;
}

function _SuperLib_RoadBuilder::EnableSlowPathFinding(enable = true)
{
	this.slow_pf = enable;
}

function _SuperLib_RoadBuilder::EnableSlowBuilding(enable = true)
{
	this.slow_build = enable;
}

function _SuperLib_RoadBuilder::SetEstimateMultiplier(estimate_multiplier)
{
	this.estimate_multiplier = estimate_multiplier;
}

function _SuperLib_RoadBuilder::SetLoanLimit(loan_limit)
{
	this.loan_limit = loan_limit;
}
