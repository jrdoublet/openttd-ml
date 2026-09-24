/*
 * Modification note:
 * Part of OpexAI - modified vendor copy of Pathfinder.Rail v1 for OpenTTD NoAI.
 * Author: OpexAI
 * Date: 2026-09-24
 * License: GNU General Public License version 2 (GPLv2).
 * What: Renamed class to OpexRailPathFinderV90; use OpexAyStarV90 instead of BaNaNaS import;
 *       precalculated map size, direction offsets, and goal X/Y coordinates;
 *       memoized per-search invariant tile queries (slope, is_buildable, is_coast, is_bridge, is_tunnel, has_rail);
 *       precomputed bridge types per length per search;
 *       added OpexRailPathfinderCheckerV90 for step-by-step parallel validation with BaNaNaS original;
 *       strictly identical route and cost decisions.
 *       V91 (2026-09-24): Added weighted A* heuristic support (_EstimateWeighted, v91_astar_weight_pct);
 *       zero overhead at default weight 100 via callback selection;
 *       comparative finish_weighted trace in OpexRailPathfinderCheckerV90 when weight > 100.
 */

/* $Id: main.nut 15101 2009-01-16 00:05:26Z truebrain $ */

/**
 * A Rail Pathfinder.
 */
class OpexRailPathFinderV90
{
	_aystar_class = OpexAyStarV90;
	_max_cost = null;              ///< The maximum cost for a route.
	_cost_tile = null;             ///< The cost for a single tile.
	_cost_diagonal_tile = null;    ///< The cost for a diagonal tile.
	_cost_turn = null;             ///< The cost that is added to _cost_tile if the direction changes.
	_cost_slope = null;            ///< The extra cost if a rail tile is sloped.
	_cost_bridge_per_tile = null;  ///< The cost per tile of a new bridge, this is added to _cost_tile.
	_cost_tunnel_per_tile = null;  ///< The cost per tile of a new tunnel, this is added to _cost_tile.
	_cost_coast = null;            ///< The extra cost for a coast tile.
	_pathfinder = null;            ///< A reference to the used AyStar object.
	_max_bridge_length = null;     ///< The maximum length of a bridge that will be build.
	_max_tunnel_length = null;     ///< The maximum length of a tunnel that will be build.

	cost = null;                   ///< Used to change the costs.
	_running = null;
	_goals = null;

	/* V91 : Poids heuristique (pourcentage, 100 = non pondéré V90) */
	_weight = 100;

	/* V90 : Constantes et précalculs par instance */
	_mapSizeX = null;
	_offsets = null;
	_goalCoords = null;
	_bestBridgeForLength = null;

	/* V90 : Caches mémoïsés par recherche (vidés dans InitializePath) */
	_cache_slope = null;
	_cache_coast = null;
	_cache_bridge = null;
	_cache_tunnel = null;
	_cache_rail = null;
	_cache_buildable = null;

	constructor(weight = null)
	{
		this._max_cost = 10000000;
		this._cost_tile = 100;
		this._cost_diagonal_tile = 70;
		this._cost_turn = 50;
		this._cost_slope = 100;
		this._cost_bridge_per_tile = 150;
		this._cost_tunnel_per_tile = 120;
		this._cost_coast = 20;
		this._max_bridge_length = 6;
		this._max_tunnel_length = 6;
		this._weight = (weight != null) ? weight : V91_ASTAR_WEIGHT_PCT;
		local estimate_fn = (this._weight > 100) ? this._EstimateWeighted : this._Estimate;
		this._pathfinder = this._aystar_class(this._Cost, estimate_fn, this._Neighbours, this._CheckDirection, this, this, this, this);

		this.cost = this.Cost(this);
		this._running = false;

		/* V90 : constantes de carte et offsets calculés une fois */
		this._mapSizeX = AIMap.GetMapSizeX();
		this._offsets = [
			AIMap.GetTileIndex(0, 1),
			AIMap.GetTileIndex(0, -1),
			AIMap.GetTileIndex(1, 0),
			AIMap.GetTileIndex(-1, 0)
		];
		this._goalCoords = [];
		this._bestBridgeForLength = {};

		/* V90 : initialisation des tables de mémoïsation */
		this._cache_slope = {};
		this._cache_coast = {};
		this._cache_bridge = {};
		this._cache_tunnel = {};
		this._cache_rail = {};
		this._cache_buildable = {};
	}

	/**
	 * Initialize a path search between sources and goals.
	 * @param sources The source tiles.
	 * @param goals The target tiles.
	 * @param ignored_tiles An array of tiles that cannot occur in the final path.
	 * @see AyStar::InitializePath()
	 */
	function InitializePath(sources, goals, ignored_tiles = []);

	/**
	 * Try to find the path as indicated with InitializePath with the lowest cost.
	 * @param iterations After how many iterations it should abort for a moment.
	 *  This value should either be -1 for infinite, or > 0. Any other value
	 *  aborts immediatly and will never find a path.
	 * @return A route if one was found, or false if the amount of iterations was
	 *  reached, or null if no path was found.
	 *  You can call this function over and over as long as it returns false,
	 *  which is an indication it is not yet done looking for a route.
	 * @see AyStar::FindPath()
	 */
	function FindPath(iterations);

	/* V90 : requêtes de tuiles mémoïsées */
	function _GetSlope(tile);
	function _IsBuildable(tile);
	function _IsCoast(tile);
	function _IsBridge(tile);
	function _IsTunnel(tile);
	function _HasRail(tile);

	function _Cost(path, new_tile, new_direction, self);
	function _Estimate(cur_tile, cur_direction, goal_tiles, self);
	function _EstimateWeighted(cur_tile, cur_direction, goal_tiles, self);
	function SetWeight(weight);
	function _Neighbours(path, cur_node, self);
	function _CheckDirection(tile, existing_direction, new_direction, self);
	function _GetBridgeNumSlopes(end_a, end_b);
	function _GetTunnelsBridges(last_node, cur_node, bridge_dir);
	function _IsSlopedRail(start, middle, end);
	function _dir(from, to);
	function _GetDirection(pre_from, from, to, is_bridge);
};

class OpexRailPathFinderV90.Cost
{
	_main = null;

	function _set(idx, val)
	{
		if (this._main._running) throw("You are not allowed to change parameters of a running pathfinder.");

		switch (idx) {
			case "max_cost":          this._main._max_cost = val; break;
			case "tile":              this._main._cost_tile = val; break;
			case "diagonal_tile":     this._main._cost_diagonal_tile = val; break;
			case "turn":              this._main._cost_turn = val; break;
			case "slope":             this._main._cost_slope = val; break;
			case "bridge_per_tile":   this._main._cost_bridge_per_tile = val; break;
			case "tunnel_per_tile":   this._main._cost_tunnel_per_tile = val; break;
			case "coast":             this._main._cost_coast = val; break;
			case "max_bridge_length": this._main._max_bridge_length = val; break;
			case "max_tunnel_length": this._main._max_tunnel_length = val; break;
			case "astar_weight_pct":  this._main.SetWeight(val); break;
			default: throw("the index '" + idx + "' does not exist");
		}

		return val;
	}

	function _get(idx)
	{
		switch (idx) {
			case "max_cost":          return this._main._max_cost;
			case "tile":              return this._main._cost_tile;
			case "diagonal_tile":     return this._main._cost_diagonal_tile;
			case "turn":              return this._main._cost_turn;
			case "slope":             return this._main._cost_slope;
			case "bridge_per_tile":   return this._main._cost_bridge_per_tile;
			case "tunnel_per_tile":   return this._main._cost_tunnel_per_tile;
			case "coast":             return this._main._cost_coast;
			case "max_bridge_length": return this._main._max_bridge_length;
			case "max_tunnel_length": return this._main._max_tunnel_length;
			case "astar_weight_pct":  return this._main._weight;
			default: throw("the index '" + idx + "' does not exist");
		}
	}

	constructor(main)
	{
		this._main = main;
	}
};

function OpexRailPathFinderV90::SetWeight(weight)
{
	this._weight = (weight >= 100) ? weight : 100;
	local target_fn = (this._weight > 100) ? this._EstimateWeighted : this._Estimate;
	this._pathfinder._estimate_callback = target_fn;
}

function OpexRailPathFinderV90::InitializePath(sources, goals, ignored_tiles = [])
{
	local nsources = [];

	/* V91 : synchroniser le callback d'estimation selon le poids effectif */
	local target_fn = (this._weight > 100) ? this._EstimateWeighted : this._Estimate;
	if (this._pathfinder._estimate_callback != target_fn) {
		this._pathfinder._estimate_callback = target_fn;
	}

	/* V90 : vider les caches par recherche */
	this._cache_slope = {};
	this._cache_coast = {};
	this._cache_bridge = {};
	this._cache_tunnel = {};
	this._cache_rail = {};
	this._cache_buildable = {};

	/* V90 : précalcul des coordonnées des buts */
	this._goalCoords = [];
	foreach (g in goals) {
		local tile = (typeof(g) == "array") ? g[0] : g;
		this._goalCoords.append({
			goal = g,
			tile = tile,
			x = AIMap.GetTileX(tile),
			y = AIMap.GetTileY(tile)
		});
	}

	/* V90 : précalcul des types de ponts disponibles par longueur */
	this._bestBridgeForLength = {};
	for (local i = 2; i < this._max_bridge_length; i++) {
		local bridge_list = AIBridgeList_Length(i + 1);
		if (!bridge_list.IsEmpty()) {
			this._bestBridgeForLength[i] <- bridge_list.Begin();
		}
	}

	foreach (node in sources) {
		local path = this._pathfinder.Path(null, node[1], 0xFF, this._Cost, this);
		path = this._pathfinder.Path(path, node[0], 0xFF, this._Cost, this);
		nsources.push(path);
	}
	this._goals = goals;
	this._pathfinder.InitializePath(nsources, goals, ignored_tiles);
}

function OpexRailPathFinderV90::FindPath(iterations)
{
	local test_mode = AITestMode();
	local ret = this._pathfinder.FindPath(iterations);
	this._running = (ret == false) ? true : false;
	if (!this._running && ret != null) {
		foreach (goal in this._goals) {
			if (goal[0] == ret.GetTile()) {
				return this._pathfinder.Path(ret, goal[1], 0, this._Cost, this);
			}
		}
	}
	return ret;
}

function OpexRailPathFinderV90::_GetSlope(tile)
{
	if (tile in this._cache_slope) return this._cache_slope[tile];
	local s = AITile.GetSlope(tile);
	this._cache_slope[tile] <- s;
	return s;
}

function OpexRailPathFinderV90::_IsBuildable(tile)
{
	if (tile in this._cache_buildable) return this._cache_buildable[tile];
	local b = AITile.IsBuildable(tile);
	this._cache_buildable[tile] <- b;
	return b;
}

function OpexRailPathFinderV90::_IsCoast(tile)
{
	if (tile in this._cache_coast) return this._cache_coast[tile];
	local c = AITile.IsCoastTile(tile);
	this._cache_coast[tile] <- c;
	return c;
}

function OpexRailPathFinderV90::_IsBridge(tile)
{
	if (tile in this._cache_bridge) return this._cache_bridge[tile];
	local b = AIBridge.IsBridgeTile(tile);
	this._cache_bridge[tile] <- b;
	return b;
}

function OpexRailPathFinderV90::_IsTunnel(tile)
{
	if (tile in this._cache_tunnel) return this._cache_tunnel[tile];
	local t = AITunnel.IsTunnelTile(tile);
	this._cache_tunnel[tile] <- t;
	return t;
}

function OpexRailPathFinderV90::_HasRail(tile)
{
	if (tile in this._cache_rail) return this._cache_rail[tile];
	local r = AITile.HasTransportType(tile, AITile.TRANSPORT_RAIL);
	this._cache_rail[tile] <- r;
	return r;
}

function OpexRailPathFinderV90::_GetBridgeNumSlopes(end_a, end_b)
{
	local slopes = 0;
	local direction = (end_b - end_a) / AIMap.DistanceManhattan(end_a, end_b);
	local mapX = this._mapSizeX;
	local slope = this._GetSlope(end_a);
	if (!((slope == AITile.SLOPE_NE && direction == 1) || (slope == AITile.SLOPE_SE && direction == -mapX) ||
		(slope == AITile.SLOPE_SW && direction == -1) || (slope == AITile.SLOPE_NW && direction == mapX) ||
		 slope == AITile.SLOPE_N || slope == AITile.SLOPE_E || slope == AITile.SLOPE_S || slope == AITile.SLOPE_W)) {
		slopes++;
	}

	slope = this._GetSlope(end_b);
	direction = -direction;
	if (!((slope == AITile.SLOPE_NE && direction == 1) || (slope == AITile.SLOPE_SE && direction == -mapX) ||
		(slope == AITile.SLOPE_SW && direction == -1) || (slope == AITile.SLOPE_NW && direction == mapX) ||
		 slope == AITile.SLOPE_N || slope == AITile.SLOPE_E || slope == AITile.SLOPE_S || slope == AITile.SLOPE_W)) {
		slopes++;
	}
	return slopes;
}

function OpexRailPathFinderV90::_Cost(path, new_tile, new_direction, self)
{
	/* path == null means this is the first node of a path, so the cost is 0. */
	if (path == null) return 0;

	local prev_tile = path.GetTile();

	/* If the new tile is a bridge / tunnel tile, check whether we came from the other
	 *  end of the bridge / tunnel or if we just entered the bridge / tunnel. */
	if (self._IsBridge(new_tile)) {
		if (AIBridge.GetOtherBridgeEnd(new_tile) != prev_tile) {
			local cost = path.GetCost() + self._cost_tile;
			if (path.GetParent() != null && path.GetParent().GetTile() - prev_tile != prev_tile - new_tile) cost += self._cost_turn;
			return cost;
		}
		return path.GetCost() + AIMap.DistanceManhattan(new_tile, prev_tile) * self._cost_tile + self._GetBridgeNumSlopes(new_tile, prev_tile) * self._cost_slope;
	}
	if (self._IsTunnel(new_tile)) {
		if (AITunnel.GetOtherTunnelEnd(new_tile) != prev_tile) {
			local cost = path.GetCost() + self._cost_tile;
			if (path.GetParent() != null && path.GetParent().GetTile() - prev_tile != prev_tile - new_tile) cost += self._cost_turn;
			return cost;
		}
		return path.GetCost() + AIMap.DistanceManhattan(new_tile, prev_tile) * self._cost_tile;
	}

	/* If the two tiles are more then 1 tile apart, the pathfinder wants a bridge or tunnel
	 *  to be build. It isn't an existing bridge / tunnel, as that case is already handled. */
	local distManhattan = AIMap.DistanceManhattan(new_tile, prev_tile);
	if (distManhattan > 1) {
		/* Check if we should build a bridge or a tunnel. */
		local cost = path.GetCost();
		if (AITunnel.GetOtherTunnelEnd(new_tile) == prev_tile) {
			cost += distManhattan * (self._cost_tile + self._cost_tunnel_per_tile);
		} else {
			cost += distManhattan * (self._cost_tile + self._cost_bridge_per_tile) + self._GetBridgeNumSlopes(new_tile, prev_tile) * self._cost_slope;
		}
		if (path.GetParent() != null && path.GetParent().GetParent() != null &&
				path.GetParent().GetParent().GetTile() - path.GetParent().GetTile() != max(AIMap.GetTileX(prev_tile) - AIMap.GetTileX(new_tile), AIMap.GetTileY(prev_tile) - AIMap.GetTileY(new_tile)) / distManhattan) {
			cost += self._cost_turn;
		}
		return cost;
	}

	/* Check for a turn. We do this by substracting the TileID of the current
	 *  node from the TileID of the previous node and comparing that to the
	 *  difference between the tile before the previous node and the node before
	 *  that. */
	local cost = self._cost_tile;
	if (path.GetParent() != null && AIMap.DistanceManhattan(path.GetParent().GetTile(), prev_tile) == 1 && path.GetParent().GetTile() - prev_tile != prev_tile - new_tile) cost = self._cost_diagonal_tile;
	if (path.GetParent() != null && path.GetParent().GetParent() != null &&
			AIMap.DistanceManhattan(new_tile, path.GetParent().GetParent().GetTile()) == 3 &&
			path.GetParent().GetParent().GetTile() - path.GetParent().GetTile() != prev_tile - new_tile) {
		cost += self._cost_turn;
	}

	/* Check if the new tile is a coast tile. */
	if (self._IsCoast(new_tile)) {
		cost += self._cost_coast;
	}

	/* Check if the last tile was sloped. */
	if (path.GetParent() != null && !self._IsBridge(prev_tile) && !self._IsTunnel(prev_tile) &&
			self._IsSlopedRail(path.GetParent().GetTile(), prev_tile, new_tile)) {
		cost += self._cost_slope;
	}

	return path.GetCost() + cost;
}

function OpexRailPathFinderV90::_Estimate(cur_tile, cur_direction, goal_tiles, self)
{
	local min_cost = self._max_cost;
	local cur_x = AIMap.GetTileX(cur_tile);
	local cur_y = AIMap.GetTileY(cur_tile);
	local diag_cost2 = self._cost_diagonal_tile * 2;
	local straight_cost = self._cost_tile;

	/* As estimate we multiply the lowest possible cost for a single tile with
	 * the minimum number of tiles we need to traverse. */
	foreach (g in self._goalCoords) {
		local dx = abs(cur_x - g.x);
		local dy = abs(cur_y - g.y);
		local min_d = (dx < dy) ? dx : dy;
		local max_d = (dx > dy) ? dx : dy;
		local cost = min_d * diag_cost2 + (max_d - min_d) * straight_cost;
		if (cost < min_cost) min_cost = cost;
	}
	return min_cost;
}

function OpexRailPathFinderV90::_EstimateWeighted(cur_tile, cur_direction, goal_tiles, self)
{
	local min_cost = self._max_cost;
	local cur_x = AIMap.GetTileX(cur_tile);
	local cur_y = AIMap.GetTileY(cur_tile);
	local diag_cost2 = self._cost_diagonal_tile * 2;
	local straight_cost = self._cost_tile;

	/* As estimate we multiply the lowest possible cost for a single tile with
	 * the minimum number of tiles we need to traverse. */
	foreach (g in self._goalCoords) {
		local dx = abs(cur_x - g.x);
		local dy = abs(cur_y - g.y);
		local min_d = (dx < dy) ? dx : dy;
		local max_d = (dx > dy) ? dx : dy;
		local cost = min_d * diag_cost2 + (max_d - min_d) * straight_cost;
		if (cost < min_cost) min_cost = cost;
	}
	if (min_cost >= self._max_cost) return self._max_cost;
	return (min_cost * self._weight) / 100;
}

function OpexRailPathFinderV90::_Neighbours(path, cur_node, self)
{
	if (self._HasRail(cur_node)) return [];
	/* self._max_cost is the maximum path cost, if we go over it, the path isn't valid. */
	if (path.GetCost() >= self._max_cost) return [];
	local tiles = [];
	local offsets = self._offsets;

	/* Check if the current tile is part of a bridge or tunnel. */
	if (self._IsBridge(cur_node) || self._IsTunnel(cur_node)) {
		/* We don't use existing rails, so neither existing bridges / tunnels. */
	} else if (path.GetParent() != null && AIMap.DistanceManhattan(cur_node, path.GetParent().GetTile()) > 1) {
		local other_end = path.GetParent().GetTile();
		local next_tile = cur_node + (cur_node - other_end) / AIMap.DistanceManhattan(cur_node, other_end);
		foreach (offset in offsets) {
			if (AIRail.BuildRail(cur_node, next_tile, next_tile + offset)) {
				tiles.push([next_tile, self._GetDirection(other_end, cur_node, next_tile, true)]);
			}
		}
	} else {
		/* Check all tiles adjacent to the current tile. */
		foreach (offset in offsets) {
			local next_tile = cur_node + offset;
			/* Don't turn back */
			if (path.GetParent() != null && next_tile == path.GetParent().GetTile()) continue;
			/* Disallow 90 degree turns */
			if (path.GetParent() != null && path.GetParent().GetParent() != null &&
				next_tile - cur_node == path.GetParent().GetParent().GetTile() - path.GetParent().GetTile()) continue;
			/* We add them to the to the neighbours-list if we can build a rail to
			 *  them and no rail exists there. */
			if ((path.GetParent() == null || AIRail.BuildRail(path.GetParent().GetTile(), cur_node, next_tile))) {
				if (path.GetParent() != null) {
					tiles.push([next_tile, self._GetDirection(path.GetParent().GetTile(), cur_node, next_tile, false)]);
				} else {
					tiles.push([next_tile, self._GetDirection(null, cur_node, next_tile, false)]);
				}
			}
		}
		if (path.GetParent() != null && path.GetParent().GetParent() != null) {
			local bridges = self._GetTunnelsBridges(path.GetParent().GetTile(), cur_node, self._GetDirection(path.GetParent().GetParent().GetTile(), path.GetParent().GetTile(), cur_node, true));
			foreach (tile in bridges) {
				tiles.push(tile);
			}
		}
	}
	return tiles;
}

function OpexRailPathFinderV90::_CheckDirection(tile, existing_direction, new_direction, self)
{
	return false;
}

function OpexRailPathFinderV90::_dir(from, to)
{
	local diff = from - to;
	if (diff == 1) return 0;
	if (diff == -1) return 1;
	if (diff == this._mapSizeX) return 2;
	if (diff == -this._mapSizeX) return 3;
	throw("Shouldn't come here in _dir");
}

function OpexRailPathFinderV90::_GetDirection(pre_from, from, to, is_bridge)
{
	if (is_bridge) {
		local diff = from - to;
		if (diff == 1) return 1;
		if (diff == -1) return 2;
		if (diff == this._mapSizeX) return 4;
		if (diff == -this._mapSizeX) return 8;
	}
	return 1 << (4 + (pre_from == null ? 0 : 4 * this._dir(pre_from, from)) + this._dir(from, to));
}

/**
 * Get a list of all bridges and tunnels that can be build from the
 *  current tile. Bridges will only be build starting on non-flat tiles
 *  for performance reasons. Tunnels will only be build if no terraforming
 *  is needed on both ends.
 */
function OpexRailPathFinderV90::_GetTunnelsBridges(last_node, cur_node, bridge_dir)
{
	local slope = this._GetSlope(cur_node);
	if (slope == AITile.SLOPE_FLAT && this._IsBuildable(cur_node + (cur_node - last_node))) return [];
	local tiles = [];

	for (local i = 2; i < this._max_bridge_length; i++) {
		if (i in this._bestBridgeForLength) {
			local target = cur_node + i * (cur_node - last_node);
			if (AIBridge.BuildBridge(AIVehicle.VT_RAIL, this._bestBridgeForLength[i], cur_node, target)) {
				tiles.push([target, bridge_dir]);
			}
		}
	}

	if (slope != AITile.SLOPE_SW && slope != AITile.SLOPE_NW && slope != AITile.SLOPE_SE && slope != AITile.SLOPE_NE) return tiles;
	local other_tunnel_end = AITunnel.GetOtherTunnelEnd(cur_node);
	if (!AIMap.IsValidTile(other_tunnel_end)) return tiles;

	local tunnel_length = AIMap.DistanceManhattan(cur_node, other_tunnel_end);
	local prev_tile = cur_node + (cur_node - other_tunnel_end) / tunnel_length;
	if (AITunnel.GetOtherTunnelEnd(other_tunnel_end) == cur_node && tunnel_length >= 2 &&
			prev_tile == last_node && tunnel_length < this._max_tunnel_length && AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur_node)) {
		tiles.push([other_tunnel_end, bridge_dir]);
	}
	return tiles;
}

function OpexRailPathFinderV90::_IsSlopedRail(start, middle, end)
{
	local NW = 0; // Set to true if we want to build a rail to / from the north-west
	local NE = 0; // Set to true if we want to build a rail to / from the north-east
	local SW = 0; // Set to true if we want to build a rail to / from the south-west
	local SE = 0; // Set to true if we want to build a rail to / from the south-east
	local mapX = this._mapSizeX;

	if (middle - mapX == start || middle - mapX == end) NW = 1;
	if (middle - 1 == start || middle - 1 == end) NE = 1;
	if (middle + mapX == start || middle + mapX == end) SE = 1;
	if (middle + 1 == start || middle + 1 == end) SW = 1;

	/* If there is a turn in the current tile, it can't be sloped. */
	if ((NW || SE) && (NE || SW)) return false;

	local slope = this._GetSlope(middle);
	/* A rail on a steep slope is always sloped. */
	if (AITile.IsSteepSlope(slope)) return true;

	/* If only one corner is raised, the rail is sloped. */
	if (slope == AITile.SLOPE_N || slope == AITile.SLOPE_W) return true;
	if (slope == AITile.SLOPE_S || slope == AITile.SLOPE_E) return true;

	if (NW && (slope == AITile.SLOPE_NW || slope == AITile.SLOPE_SE)) return true;
	if (NE && (slope == AITile.SLOPE_NE || slope == AITile.SLOPE_SW)) return true;

	return false;
}

/**
 * V90 test-mode checker:
 * Runs BaNaNaS RailPathFinder and OpexRailPathFinderV90 in lockstep,
 * compares current node at each step and end path/iterations,
 * logs V90_CHECK under probe_events.
 */
class OpexRailPathfinderCheckerV90
{
	_orig = null;
	_v90 = null;
	_stepCount = 0;
	_stepCountOrig = 0;
	_stepCountV90 = 0;
	_firstDiffIter = -1;
	_firstDiffDesc = null;
	_doneLogged = false;
	_doneOrig = false;
	_doneV90 = false;
	_resOrig = false;
	_resV90 = false;
	_isWeighted = false;
	cost = null;
	_pathfinder = null;

	constructor(weight = null)
	{
		this._orig = RailPathFinder();
		this._v90 = OpexRailPathFinderV90(weight);
		this.cost = this.Cost(this);
		this._pathfinder = this._v90._pathfinder;
		this._stepCount = 0;
		this._stepCountOrig = 0;
		this._stepCountV90 = 0;
		this._firstDiffIter = -1;
		this._firstDiffDesc = null;
		this._doneLogged = false;
		this._doneOrig = false;
		this._doneV90 = false;
		this._resOrig = false;
		this._resV90 = false;
		this._isWeighted = (this._v90._weight > 100);
	}

	function InitializePath(sources, goals, ignored_tiles = [])
	{
		this._stepCount = 0;
		this._stepCountOrig = 0;
		this._stepCountV90 = 0;
		this._firstDiffIter = -1;
		this._firstDiffDesc = null;
		this._doneLogged = false;
		this._doneOrig = false;
		this._doneV90 = false;
		this._resOrig = false;
		this._resV90 = false;
		this._orig.InitializePath(sources, goals, ignored_tiles);
		this._v90.InitializePath(sources, goals, ignored_tiles);
		this._pathfinder = this._v90._pathfinder;
		this._isWeighted = (this._v90._weight > 100);
	}

	function FindPath(iterations)
	{
		local count = (iterations > 0) ? iterations : 1;

		if (this._isWeighted) {
			for (local i = 0; i < count; i++) {
				if (!this._doneV90) {
					local rV90 = this._v90.FindPath(1);
					this._stepCountV90++;
					if (rV90 != false) {
						this._doneV90 = true;
						this._resV90 = rV90;
					}
				}
				if (!this._doneOrig) {
					local rOrig = this._orig.FindPath(1);
					this._stepCountOrig++;
					if (rOrig != false) {
						this._doneOrig = true;
						this._resOrig = rOrig;
					}
				}
				if (this._doneV90) break;
			}

			if (this._doneV90) {
				while (!this._doneOrig) {
					local rOrig = this._orig.FindPath(1);
					this._stepCountOrig++;
					if (rOrig != false) {
						this._doneOrig = true;
						this._resOrig = rOrig;
						break;
					}
				}

				if (!this._doneLogged) {
					this._doneLogged = true;
					local lenOrig = 0;
					local costOrig = 0;
					if (this._resOrig != null && this._resOrig != false) {
						lenOrig = OpexSegmentTiles(this._resOrig).len();
						costOrig = this._resOrig.GetCost();
					}
					local lenV90 = 0;
					local costV90 = 0;
					if (this._resV90 != null && this._resV90 != false) {
						lenV90 = OpexSegmentTiles(this._resV90).len();
						costV90 = this._resV90.GetCost();
					}
					local ratioIters = (this._stepCountOrig > 0) ? (this._stepCountV90 * 1.0 / this._stepCountOrig) : 1.0;
					local ratioLen = (lenOrig > 0) ? (lenV90 * 1.0 / lenOrig) : 1.0;
					local ratioCost = (costOrig > 0) ? (costV90 * 1.0 / costOrig) : 1.0;

					OpexC56TaskLog("V90_CHECK", "finish_weighted", "-",
					               "iters_orig=" + this._stepCountOrig +
					               " iters_weighted=" + this._stepCountV90 +
					               " ratio_iters=" + ratioIters +
					               " len_orig=" + lenOrig +
					               " len_weighted=" + lenV90 +
					               " ratio_len=" + ratioLen +
					               " cost_orig=" + costOrig +
					               " cost_weighted=" + costV90 +
					               " ratio_cost=" + ratioCost);
				}
				return this._resV90;
			}
			return false;
		}

		/* Mode non pondéré (weight == 100) : comparaison pas à pas lockstep */
		local retOrig = false;
		local retV90 = false;

		for (local i = 0; i < count; i++) {
			local topOrig = (this._orig._pathfinder._open != null && this._orig._pathfinder._open.Count() > 0) ? this._orig._pathfinder._open.Peek() : null;
			local topV90 = (this._v90._pathfinder._open != null && this._v90._pathfinder._open.Count() > 0) ? this._v90._pathfinder._open.Peek() : null;

			if (topOrig != null && topV90 != null) {
				if (topOrig.GetTile() != topV90.GetTile() || topOrig.GetDirection() != topV90.GetDirection() || topOrig.GetCost() != topV90.GetCost()) {
					if (this._firstDiffIter < 0) {
						this._firstDiffIter = this._stepCount;
						this._firstDiffDesc = "orig=" + topOrig.GetTile() + ":" + topOrig.GetDirection() + ":" + topOrig.GetCost() + "/v90=" + topV90.GetTile() + ":" + topV90.GetDirection() + ":" + topV90.GetCost();
						OpexC56TaskLog("V90_CHECK", "step_diff", "-", "iter=" + this._stepCount + " diff=" + this._firstDiffDesc);
					}
				}
			} else if (topOrig != topV90) {
				if (this._firstDiffIter < 0) {
					this._firstDiffIter = this._stepCount;
					this._firstDiffDesc = "open_mismatch_orig=" + (topOrig != null ? 1 : 0) + "/v90=" + (topV90 != null ? 1 : 0);
					OpexC56TaskLog("V90_CHECK", "step_diff", "-", "iter=" + this._stepCount + " diff=" + this._firstDiffDesc);
				}
			}

			retOrig = this._orig.FindPath(1);
			retV90 = this._v90.FindPath(1);
			this._stepCount++;

			if (retOrig != false || retV90 != false) {
				break;
			}
		}

		if (retV90 != false || retOrig != false) {
			if (!this._doneLogged) {
				this._doneLogged = true;
				local sameIters = (retOrig != false && retV90 != false);
				local samePath = false;
				if (retOrig == null && retV90 == null) {
					samePath = true;
				} else if (retOrig != null && retOrig != false && retV90 != null && retV90 != false) {
					local tilesOrig = OpexSegmentTiles(retOrig);
					local tilesV90 = OpexSegmentTiles(retV90);
					if (tilesOrig.len() == tilesV90.len()) {
						samePath = true;
						for (local j = 0; j < tilesOrig.len(); j++) {
							if (tilesOrig[j] != tilesV90[j]) {
								samePath = false;
								break;
							}
						}
					}
				}
				OpexC56TaskLog("V90_CHECK", "finish", "-",
				               "iters=" + this._stepCount +
				               " same_path=" + (samePath ? "oui" : "non") +
				               " same_iters=" + (sameIters ? "oui" : "non") +
				               " first_diff=" + (this._firstDiffIter >= 0 ? ("iter=" + this._firstDiffIter + " " + this._firstDiffDesc) : "none"));
			}
		} else {
			if (this._firstDiffIter >= 0) {
				OpexC56TaskLog("V90_CHECK", "step_diverged", "-", "iter=" + this._stepCount + " first_diff_iter=" + this._firstDiffIter);
			} else {
				OpexC56TaskLog("V90_CHECK", "step_identical", "-", "iter=" + this._stepCount);
			}
		}

		return retV90;
	}
};

class OpexRailPathfinderCheckerV90.Cost
{
	_checker = null;

	constructor(checker)
	{
		this._checker = checker;
	}

	function _set(idx, val)
	{
		if (idx == "astar_weight_pct") {
			this._checker._v90.cost[idx] = val;
			this._checker._isWeighted = (this._checker._v90._weight > 100);
			return val;
		}
		this._checker._orig.cost[idx] = val;
		this._checker._v90.cost[idx] = val;
		return val;
	}

	function _get(idx)
	{
		return this._checker._v90.cost[idx];
	}
};
