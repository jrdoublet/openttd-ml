/*
 * Modification note:
 * Part of OpexAI - V129 (2026-10-07): variante optimisee, a exploration strictement identique,
 * de OpexAyStarV90 / OpexBinaryHeapV90 / OpexRailPathFinderV90 (eux-memes derives de
 * Graph.AyStar v4, Queue.BinaryHeap v1 et Pathfinder.Rail v1, GPLv2).
 * Author: OpexAI
 * License: GNU General Public License version 2 (GPLv2).
 * What: tas a tableaux paralleles (memes comparaisons, meme depart) ; noeuds sans appel de
 *       cout dans le constructeur ; lecture directe des champs de parente ; ensemble des
 *       tuiles-buts ; voisins en une passe avec table de directions ; cache d'heuristique par
 *       tuile (l'estimation ne depend pas de la direction) ; table des ponts mise en cache ;
 *       FindPath(n) qui memorise le nombre d'iterations reellement consommees.
 *       Active seulement par v129_rail_astar_exact_opt ; a 0 ce fichier n'est jamais instancie.
 */

/* Iterations groupees par appel FindPath dans OpexAdvanceSegmentedSearch (V129 seulement). */
V129_RAIL_BATCH_ITERS <- 8;

class OpexBinaryHeapV129
{
	_items = null;
	_prios = null;
	_count = 0;

	constructor()
	{
		this._items = [];
		this._prios = [];
	}

	function Insert(item, priority);
	function Pop();
	function Peek();
	function PeekPriority();
	function Count();
	function Exists(item);
};

function OpexBinaryHeapV129::Insert(item, priority)
{
	local items = this._items;
	local prios = this._prios;
	items.append(0);
	prios.append(0);
	local count = this._count + 1;
	this._count = count;

	local hole;
	/* Meme point d'insertion que V90 : parent = hole / 2, comparaison <=. */
	for (hole = count - 1; hole > 0 && priority <= prios[hole / 2]; hole /= 2) {
		items[hole] = items[hole / 2];
		prios[hole] = prios[hole / 2];
	}
	items[hole] = item;
	prios[hole] = priority;
	return true;
}

function OpexBinaryHeapV129::Pop()
{
	local count = this._count;
	if (count == 0) return null;

	local items = this._items;
	local prios = this._prios;
	local node = items[0];
	local last = count - 1;
	local tmpItem = items[last];
	local tmpPrio = prios[last];
	items.pop();
	prios.pop();
	count--;
	this._count = count;
	if (count == 0) return node;

	/* Descente identique a V90 (_BubbleDown) : l'indice 0 n'est jamais relu avant d'etre ecrase. */
	local hole = 1;
	while (hole * 2 < count + 1) {
		local child = hole * 2;
		if (child != count && prios[child] <= prios[child - 1]) child++;
		local childPrio = prios[child - 1];
		if (childPrio > tmpPrio) break;
		items[hole - 1] = items[child - 1];
		prios[hole - 1] = childPrio;
		hole = child;
	}
	items[hole - 1] = tmpItem;
	prios[hole - 1] = tmpPrio;
	return node;
}

function OpexBinaryHeapV129::Peek()
{
	if (this._count == 0) return null;
	return this._items[0];
}

function OpexBinaryHeapV129::PeekPriority()
{
	if (this._count == 0) return null;
	return this._prios[0];
}

function OpexBinaryHeapV129::Count()
{
	return this._count;
}

function OpexBinaryHeapV129::Exists(item)
{
	foreach (it in this._items) {
		if (it == item) return true;
	}
	return false;
}

class OpexAyStarV129
{
	_queue_class = OpexBinaryHeapV129;
	_cost_callback = null;
	_estimate_callback = null;
	_neighbours_callback = null;
	_check_direction_callback = null;
	_cost_callback_param = null;
	_estimate_callback_param = null;
	_neighbours_callback_param = null;
	_check_direction_callback_param = null;
	_open = null;
	_closed = null;
	_goals = null;
	_goalSet = null;
	_consumed = 1;   ///< Iterations consommees par le dernier FindPath (pops, minimum 1 comme FindPath(1) de V90).

	constructor(cost_callback, estimate_callback, neighbours_callback, check_direction_callback, cost_callback_param = null,
	            estimate_callback_param = null, neighbours_callback_param = null, check_direction_callback_param = null)
	{
		if (typeof(cost_callback) != "function") throw("'cost_callback' has to be a function-pointer.");
		if (typeof(estimate_callback) != "function") throw("'estimate_callback' has to be a function-pointer.");
		if (typeof(neighbours_callback) != "function") throw("'neighbours_callback' has to be a function-pointer.");
		if (typeof(check_direction_callback) != "function") throw("'check_direction_callback' has to be a function-pointer.");

		this._cost_callback = cost_callback;
		this._estimate_callback = estimate_callback;
		this._neighbours_callback = neighbours_callback;
		this._check_direction_callback = check_direction_callback;
		this._cost_callback_param = cost_callback_param;
		this._estimate_callback_param = estimate_callback_param;
		this._neighbours_callback_param = neighbours_callback_param;
		this._check_direction_callback_param = check_direction_callback_param;
	}

	function InitializePath(sources, goals, ignored_tiles = []);
	function FindPath(iterations);
	function _CleanPath();
};

function OpexAyStarV129::InitializePath(sources, goals, ignored_tiles = [])
{
	if (typeof(sources) != "array" || sources.len() == 0) throw("sources has be a non-empty array.");
	if (typeof(goals) != "array" || goals.len() == 0) throw("goals has be a non-empty array.");

	this._open = this._queue_class();
	this._closed = {};

	foreach (node in sources) {
		if (typeof(node) == "array") {
			if (node[1] <= 0) throw("directional value should never be zero or negative.");
			local c = this._cost_callback(null, node[0], node[1], this._cost_callback_param);
			local new_path = this.Path(null, node[0], node[1], c);
			this._open.Insert(new_path, c + this._estimate_callback(node[0], node[1], goals, this._estimate_callback_param));
		} else {
			this._open.Insert(node, node.GetCost());
		}
	}

	this._goals = goals;
	this._goalSet = {};
	foreach (g in goals) {
		this._goalSet[(typeof(g) == "array") ? g[0] : g] <- true;
	}

	foreach (tile in ignored_tiles) {
		this._closed[tile] <- ~0;
	}
}

function OpexAyStarV129::FindPath(iterations)
{
	local open = this._open;
	if (open == null) throw("can't execute over an uninitialized path");

	local closed = this._closed;
	local goals = this._goals;
	local goalSet = this._goalSet;
	local costCb = this._cost_callback;
	local costParam = this._cost_callback_param;
	local estCb = this._estimate_callback;
	local estParam = this._estimate_callback_param;
	local nbCb = this._neighbours_callback;
	local nbParam = this._neighbours_callback_param;
	local pops = 0;

	while (open.Count() > 0 && (iterations == -1 || iterations-- > 0)) {
		/* Get the path with the best score so far */
		local path = open.Pop();
		pops++;
		local cur_tile = path._tile;
		local cur_dir = path._direction;
		/* Make sure we didn't already pass it */
		if (cur_tile in closed) {
			local closed_dir = closed[cur_tile];
			if ((closed_dir & cur_dir) != 0) continue;

			/* Scan the path for a possible collision */
			local scan_path = path._prev;
			local mismatch = false;
			while (scan_path != null) {
				if (scan_path._tile == cur_tile) {
					if (!this._check_direction_callback(cur_tile, scan_path._direction, cur_dir, this._check_direction_callback_param)) {
						mismatch = true;
						break;
					}
				}
				scan_path = scan_path._prev;
			}
			if (mismatch) continue;

			closed[cur_tile] = closed_dir | cur_dir;
		} else {
			closed[cur_tile] <- cur_dir;
		}
		/* Check if we found the end (seulement si la tuile est celle d'un but : meme resultat que V90). */
		if (cur_tile in goalSet) {
			foreach (goal in goals) {
				if (typeof(goal) == "array") {
					if (cur_tile == goal[0]) {
						local goalNeighbours = nbCb(path, cur_tile, nbParam);
						foreach (gnode in goalNeighbours) {
							if (gnode[0] == goal[1]) {
								this._consumed = pops;
								this._CleanPath();
								return path;
							}
						}
						continue;
					}
				} else {
					if (cur_tile == goal) {
						this._consumed = pops;
						this._CleanPath();
						return path;
					}
				}
			}
		}
		/* Scan all neighbours */
		local neighbours = nbCb(path, cur_tile, nbParam);
		foreach (node in neighbours) {
			local ntile = node[0];
			local ndir = node[1];
			if (ndir <= 0) throw("directional value should never be zero or negative.");

			if ((ntile in closed) && ((closed[ntile] & ndir) != 0)) continue;
			local c = costCb(path, ntile, ndir, costParam);
			open.Insert(this.Path(path, ntile, ndir, c), c + estCb(ntile, ndir, goals, estParam));
		}
	}

	this._consumed = (pops == 0) ? 1 : pops;
	if (open.Count() > 0) return false;
	this._CleanPath();
	return null;
}

function OpexAyStarV129::_CleanPath()
{
	this._closed = null;
	this._open = null;
	this._goals = null;
	this._goalSet = null;
}

/* Noeud : memes champs et accesseurs que OpexAyStarV90.Path, mais le cout est fourni deja calcule. */
class OpexAyStarV129.Path
{
	_prev = null;
	_tile = null;
	_direction = null;
	_cost = null;

	constructor(old_path, new_tile, new_direction, new_cost)
	{
		this._prev = old_path;
		this._tile = new_tile;
		this._direction = new_direction;
		this._cost = new_cost;
	};

	function GetTile() { return this._tile; }
	function GetDirection() { return this._direction; }
	function GetParent() { return this._prev; }
	function GetCost() { return this._cost; }
};

class OpexRailPathFinderV129 extends OpexRailPathFinderV90
{
	_aystar_class = OpexAyStarV129;
	_estCache = null;
	_dirIdx = null;
	_consumed = 1;

	function InitializePath(sources, goals, ignored_tiles = [])
	{
		local nsources = [];

		local target_fn = (this._weight > 100) ? this._EstimateWeighted : this._Estimate;
		if (this._pathfinder._estimate_callback != target_fn) {
			this._pathfinder._estimate_callback = target_fn;
		}

		this._cache_slope = {};
		this._cache_coast = {};
		this._cache_bridge = {};
		this._cache_tunnel = {};
		this._cache_rail = {};
		this._cache_buildable = {};
		this._estCache = {};

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

		/* Index de direction de chaque offset (= _dir(cur, cur + offset)), calcule depuis les offsets. */
		this._dirIdx = [];
		foreach (offset in this._offsets) {
			this._dirIdx.append(this._dir(0, offset));
		}

		/* Table des ponts : reconstruite a chaque recherche, exactement comme V90 (un cache global
		 * a ete retire apres une divergence mesuree 1 recherche sur 13 : la table des ponts peut
		 * differer d'une date a l'autre sans que le nombre de types ne change). */
		local bridgeTable = {};
		for (local i = 2; i < this._max_bridge_length; i++) {
			local bridge_list = AIBridgeList_Length(i + 1);
			if (!bridge_list.IsEmpty()) {
				bridgeTable[i] <- bridge_list.Begin();
			}
		}
		this._bestBridgeForLength = bridgeTable;

		foreach (node in sources) {
			local p0 = this._pathfinder.Path(null, node[1], 0xFF, 0);
			local c1 = this._Cost(p0, node[0], 0xFF, this);
			nsources.push(this._pathfinder.Path(p0, node[0], 0xFF, c1));
		}
		this._goals = goals;
		this._pathfinder.InitializePath(nsources, goals, ignored_tiles);
	}

	function FindPath(iterations)
	{
		local test_mode = AITestMode();
		local ret = this._pathfinder.FindPath(iterations);
		this._consumed = this._pathfinder._consumed;
		this._running = (ret == false) ? true : false;
		if (!this._running && ret != null) {
			foreach (goal in this._goals) {
				if (goal[0] == ret.GetTile()) {
					return this._pathfinder.Path(ret, goal[1], 0, this._Cost(ret, goal[1], 0, this));
				}
			}
		}
		return ret;
	}

	function LastConsumed() { return this._consumed; }

	function SetWeight(weight)
	{
		this._weight = (weight >= 100) ? weight : 100;
		local target_fn = (this._weight > 100) ? this._EstimateWeighted : this._Estimate;
		this._pathfinder._estimate_callback = target_fn;
		this._estCache = {};
	}

	function _Estimate(cur_tile, cur_direction, goal_tiles, self)
	{
		local cache = self._estCache;
		if (cur_tile in cache) return cache[cur_tile];
		local min_cost = self._max_cost;
		local cur_x = AIMap.GetTileX(cur_tile);
		local cur_y = AIMap.GetTileY(cur_tile);
		local diag_cost2 = self._cost_diagonal_tile * 2;
		local straight_cost = self._cost_tile;
		foreach (g in self._goalCoords) {
			local dx = abs(cur_x - g.x);
			local dy = abs(cur_y - g.y);
			local min_d = (dx < dy) ? dx : dy;
			local max_d = (dx > dy) ? dx : dy;
			local cost = min_d * diag_cost2 + (max_d - min_d) * straight_cost;
			if (cost < min_cost) min_cost = cost;
		}
		cache[cur_tile] <- min_cost;
		return min_cost;
	}

	function _EstimateWeighted(cur_tile, cur_direction, goal_tiles, self)
	{
		local cache = self._estCache;
		if (cur_tile in cache) return cache[cur_tile];
		local min_cost = self._max_cost;
		local cur_x = AIMap.GetTileX(cur_tile);
		local cur_y = AIMap.GetTileY(cur_tile);
		local diag_cost2 = self._cost_diagonal_tile * 2;
		local straight_cost = self._cost_tile;
		foreach (g in self._goalCoords) {
			local dx = abs(cur_x - g.x);
			local dy = abs(cur_y - g.y);
			local min_d = (dx < dy) ? dx : dy;
			local max_d = (dx > dy) ? dx : dy;
			local cost = min_d * diag_cost2 + (max_d - min_d) * straight_cost;
			if (cost < min_cost) min_cost = cost;
		}
		local est = (min_cost >= self._max_cost) ? self._max_cost : (min_cost * self._weight) / 100;
		cache[cur_tile] <- est;
		return est;
	}

	function _Cost(path, new_tile, new_direction, self)
	{
		/* path == null means this is the first node of a path, so the cost is 0. */
		if (path == null) return 0;

		local prev_tile = path._tile;
		local par = path._prev;

		if (self._IsBridge(new_tile)) {
			if (AIBridge.GetOtherBridgeEnd(new_tile) != prev_tile) {
				local cost = path._cost + self._cost_tile;
				if (par != null && par._tile - prev_tile != prev_tile - new_tile) cost += self._cost_turn;
				return cost;
			}
			return path._cost + AIMap.DistanceManhattan(new_tile, prev_tile) * self._cost_tile + self._GetBridgeNumSlopes(new_tile, prev_tile) * self._cost_slope;
		}
		if (self._IsTunnel(new_tile)) {
			if (AITunnel.GetOtherTunnelEnd(new_tile) != prev_tile) {
				local cost = path._cost + self._cost_tile;
				if (par != null && par._tile - prev_tile != prev_tile - new_tile) cost += self._cost_turn;
				return cost;
			}
			return path._cost + AIMap.DistanceManhattan(new_tile, prev_tile) * self._cost_tile;
		}

		local distManhattan = AIMap.DistanceManhattan(new_tile, prev_tile);
		if (distManhattan > 1) {
			local cost = path._cost;
			if (AITunnel.GetOtherTunnelEnd(new_tile) == prev_tile) {
				cost += distManhattan * (self._cost_tile + self._cost_tunnel_per_tile);
			} else {
				cost += distManhattan * (self._cost_tile + self._cost_bridge_per_tile) + self._GetBridgeNumSlopes(new_tile, prev_tile) * self._cost_slope;
			}
			if (par != null) {
				local gp = par._prev;
				if (gp != null &&
						gp._tile - par._tile != max(AIMap.GetTileX(prev_tile) - AIMap.GetTileX(new_tile), AIMap.GetTileY(prev_tile) - AIMap.GetTileY(new_tile)) / distManhattan) {
					cost += self._cost_turn;
				}
			}
			return cost;
		}

		local cost = self._cost_tile;
		if (par != null) {
			local par_tile = par._tile;
			if (AIMap.DistanceManhattan(par_tile, prev_tile) == 1 && par_tile - prev_tile != prev_tile - new_tile) cost = self._cost_diagonal_tile;
			local gp = par._prev;
			if (gp != null && AIMap.DistanceManhattan(new_tile, gp._tile) == 3 &&
					gp._tile - par_tile != prev_tile - new_tile) {
				cost += self._cost_turn;
			}
		}

		if (self._IsCoast(new_tile)) {
			cost += self._cost_coast;
		}

		if (par != null && !self._IsBridge(prev_tile) && !self._IsTunnel(prev_tile) &&
				self._IsSlopedRail(par._tile, prev_tile, new_tile)) {
			cost += self._cost_slope;
		}

		return path._cost + cost;
	}

	function _Neighbours(path, cur_node, self)
	{
		if (self._HasRail(cur_node)) return [];
		if (path._cost >= self._max_cost) return [];
		local tiles = [];
		local par = path._prev;

		if (self._IsBridge(cur_node) || self._IsTunnel(cur_node)) {
			/* We don't use existing rails, so neither existing bridges / tunnels. */
		} else if (par != null && AIMap.DistanceManhattan(cur_node, par._tile) > 1) {
			local other_end = par._tile;
			local next_tile = cur_node + (cur_node - other_end) / AIMap.DistanceManhattan(cur_node, other_end);
			foreach (offset in self._offsets) {
				if (AIRail.BuildRail(cur_node, next_tile, next_tile + offset)) {
					tiles.push([next_tile, self._GetDirection(other_end, cur_node, next_tile, true)]);
				}
			}
		} else {
			local offsets = self._offsets;
			local dirIdx = self._dirIdx;
			if (par == null) {
				for (local i = 0; i < 4; i++) {
					tiles.push([cur_node + offsets[i], 1 << (4 + dirIdx[i])]);
				}
			} else {
				local par_tile = par._tile;
				local gp = par._prev;
				local blocked = (gp != null) ? (gp._tile - par_tile) : 0;
				local shift0 = 4 + 4 * self._dir(par_tile, cur_node);
				for (local i = 0; i < 4; i++) {
					local offset = offsets[i];
					local next_tile = cur_node + offset;
					/* Don't turn back */
					if (next_tile == par_tile) continue;
					/* Disallow 90 degree turns */
					if (gp != null && offset == blocked) continue;
					if (AIRail.BuildRail(par_tile, cur_node, next_tile)) {
						tiles.push([next_tile, 1 << (shift0 + dirIdx[i])]);
					}
				}
				if (gp != null) self._TunnelsBridgesInto(par_tile, cur_node, gp._tile, tiles);
			}
		}
		return tiles;
	}

	/* Meme logique que _GetTunnelsBridges, mais ajoute directement a `tiles` ; la direction de pont
	 * (fonction pure) n'est calculee qu'au premier ajout. */
	function _TunnelsBridgesInto(last_node, cur_node, gp_tile, tiles)
	{
		local slope = this._GetSlope(cur_node);
		if (slope == AITile.SLOPE_FLAT && this._IsBuildable(cur_node + (cur_node - last_node))) return;
		local bridge_dir = null;
		local bridgeTable = this._bestBridgeForLength;

		for (local i = 2; i < this._max_bridge_length; i++) {
			if (i in bridgeTable) {
				local target = cur_node + i * (cur_node - last_node);
				if (AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridgeTable[i], cur_node, target)) {
					if (bridge_dir == null) bridge_dir = this._GetDirection(gp_tile, last_node, cur_node, true);
					tiles.push([target, bridge_dir]);
				}
			}
		}

		if (slope != AITile.SLOPE_SW && slope != AITile.SLOPE_NW && slope != AITile.SLOPE_SE && slope != AITile.SLOPE_NE) return;
		local other_tunnel_end = AITunnel.GetOtherTunnelEnd(cur_node);
		if (!AIMap.IsValidTile(other_tunnel_end)) return;

		local tunnel_length = AIMap.DistanceManhattan(cur_node, other_tunnel_end);
		local prev_tile = cur_node + (cur_node - other_tunnel_end) / tunnel_length;
		if (AITunnel.GetOtherTunnelEnd(other_tunnel_end) == cur_node && tunnel_length >= 2 &&
				prev_tile == last_node && tunnel_length < this._max_tunnel_length && AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur_node)) {
			if (bridge_dir == null) bridge_dir = this._GetDirection(gp_tile, last_node, cur_node, true);
			tiles.push([other_tunnel_end, bridge_dir]);
		}
	}
};

/**
 * V129 test-mode checker : rejoue OpexRailPathFinderV90 et OpexRailPathFinderV129 pas a pas
 * (un FindPath(1) chacun), compare le sommet du tas (tuile, direction, cout, priorite) et le
 * nombre de noeuds ouverts avant chaque pas, puis le chemin final. Journal V129_CHECK.
 * Le resultat renvoye est celui de V129 ; V90 sert de reference.
 */
class OpexRailPathfinderCheckerV129
{
	_v90 = null;
	_v129 = null;
	_stepCount = 0;
	_firstDiffIter = -1;
	_firstDiffDesc = null;
	_doneLogged = false;
	_consumed = 1;
	_lastTop = "-";
	_lastTopPrev = "-";
	cost = null;
	_pathfinder = null;

	constructor(weight = null)
	{
		this._v90 = OpexRailPathFinderV90(weight);
		this._v129 = OpexRailPathFinderV129(weight);
		this.cost = this.Cost(this);
		this._pathfinder = this._v129._pathfinder;
	}

	function InitializePath(sources, goals, ignored_tiles = [])
	{
		this._stepCount = 0;
		this._firstDiffIter = -1;
		this._firstDiffDesc = null;
		this._doneLogged = false;
		this._v90.InitializePath(sources, goals, ignored_tiles);
		this._v129.InitializePath(sources, goals, ignored_tiles);
		this._pathfinder = this._v129._pathfinder;
		local t90 = this._v90._bestBridgeForLength;
		local t129 = this._v129._bestBridgeForLength;
		local same = (t90.len() == t129.len());
		if (same) {
			foreach (k, v in t90) {
				if (!(k in t129) || t129[k] != v) { same = false; break; }
			}
		}
		if (!same) OpexC56TaskLog("V129_CHECK", "bridge_table_diff", "-", "len_v90=" + t90.len() + " len_v129=" + t129.len());
	}

	function LastConsumed() { return this._consumed; }

	function _Note(desc)
	{
		if (this._firstDiffIter >= 0) return;
		this._firstDiffIter = this._stepCount;
		this._firstDiffDesc = desc;
		OpexC56TaskLog("V129_CHECK", "step_diff", "-", "iter=" + this._stepCount + " diff=" + desc);
	}

	function FindPath(iterations)
	{
		local count = (iterations > 0) ? iterations : 1;
		local r90 = false;
		local r129 = false;
		local steps = 0;

		for (local i = 0; i < count; i++) {
			if (this._v90._pathfinder._open != null && this._v90._pathfinder._open.Count() > 0) {
				this._lastTopPrev = this._lastTop;
				local lp = this._v90._pathfinder._open.Peek();
				this._lastTop = lp.GetTile() + ":" + lp.GetDirection();
			}
			local o90 = this._v90._pathfinder._open;
			local o129 = this._v129._pathfinder._open;
			if (o90 != null && o129 != null) {
				if (o90.Count() != o129.Count()) {
					this._Note("open_count_v90=" + o90.Count() + "/v129=" + o129.Count() + " prev_popped=" + this._lastTopPrev);
				} else if (o90.Count() > 0) {
					local t90 = o90.Peek();
					local t129 = o129.Peek();
					local p90 = o90._queue[0][1];
					local p129 = o129.PeekPriority();
					if (t90.GetTile() != t129.GetTile() || t90.GetDirection() != t129.GetDirection()
							|| t90.GetCost() != t129.GetCost() || p90 != p129) {
						this._Note("v90=" + t90.GetTile() + ":" + t90.GetDirection() + ":" + t90.GetCost() + ":" + p90
						           + "/v129=" + t129.GetTile() + ":" + t129.GetDirection() + ":" + t129.GetCost() + ":" + p129);
					}
				}
			} else if ((o90 == null) != (o129 == null)) {
				this._Note("open_null_mismatch");
			}
			r90 = this._v90.FindPath(1);
			r129 = this._v129.FindPath(1);
			steps++;
			this._stepCount++;
			if (r90 != false || r129 != false) break;
		}
		this._consumed = steps;

		if ((r90 != false || r129 != false) && !this._doneLogged) {
			this._doneLogged = true;
			local samePath = false;
			if (r90 == null && r129 == null) {
				samePath = true;
			} else if (r90 != null && r90 != false && r129 != null && r129 != false) {
				local a = OpexSegmentTiles(r90);
				local b = OpexSegmentTiles(r129);
				if (a.len() == b.len() && r90.GetCost() == r129.GetCost()) {
					samePath = true;
					for (local j = 0; j < a.len(); j++) {
						if (a[j] != b[j]) { samePath = false; break; }
					}
				}
			}
			OpexC56TaskLog("V129_CHECK", "finish", "-",
			               "iters=" + this._stepCount + " same_path=" + (samePath ? "oui" : "non")
			               + " first_diff=" + (this._firstDiffIter >= 0 ? ("iter=" + this._firstDiffIter + " " + this._firstDiffDesc) : "none"));
		}
		return r129;
	}
};

class OpexRailPathfinderCheckerV129.Cost
{
	_checker = null;

	constructor(checker)
	{
		this._checker = checker;
	}

	function _set(idx, val)
	{
		this._checker._v90.cost[idx] = val;
		this._checker._v129.cost[idx] = val;
		return val;
	}

	function _get(idx)
	{
		return this._checker._v129.cost[idx];
	}
};

/* Choix de la variante a l'instanciation (jamais dans la boucle chaude). */
function OpexNewRailPathfinderV129()
{
	if (V129_RAIL_ASTAR_CHECK) return OpexRailPathfinderCheckerV129();
	return OpexRailPathFinderV129();
}
