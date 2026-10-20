/*
 * OpexAI V296b (2026-10-21), derived from v129.nut and Pathfinder.Rail v1 /
 * Graph.AyStar v4 (GPLv2). License: GNU General Public License version 2.
 * Native priority queue, indexed ancestry, fused expansion. Equal f uses FIFO node IDs.
 * Tile helpers remain inherited; cost expressions deliberately mirror V129.
 * No native object is persisted. Path objects exist only at the public output boundary.
 */
class OpexRailPathFinderV296 extends OpexRailPathFinderV129
{
    _tiles = null;
    _dirs = null;
    _costs = null;
    _parents = null;
    _blooms = null;
    _closed = null;
    _goalSet = null;

    constructor(weight = null)
    {
        base.constructor(weight);
        this._pathfinder = { _open = null };
    }

    function SetWeight(weight)
    {
        this._weight = (weight >= 100) ? weight : 100;
        this._estCache = {};
    }

    function _Append(tile, direction, cost, parent)
    {
        local id = this._tiles.len();
        this._tiles.append(tile); this._dirs.append(direction); this._costs.append(cost);
        this._parents.append(parent);
        this._blooms.append((parent < 0 ? 0 : this._blooms[parent]) | (1 << (tile % 61)));
        return id;
    }

    function Materialize(id)
    {
        local chain = [];
        for (local n = id; n >= 0; n = this._parents[n]) chain.append(n);
        local path = null;
        for (local i = chain.len() - 1; i >= 0; i--) {
            local n = chain[i];
            path = OpexAyStarV129.Path(path, this._tiles[n], this._dirs[n], this._costs[n], this._blooms[n]);
        }
        return path;
    }

    function FrontierAlternatives(limit)
    {
        local open = this._pathfinder._open;
        local result = [];
        if (open == null) return result;
        local seen = {};
        for (local id = open.Begin(); !open.IsEnd() && result.len() < limit; id = open.Next()) {
            local key = this._tiles[id] + ":" + this._dirs[id];
            if (key in seen) continue;
            seen[key] <- true;
            result.append(this.Materialize(id));
        }
        return result;
    }

    function _Finish(id)
    {
        local result = null;
        if (id >= 0) {
            result = this.Materialize(id);
            // V129 appends the FIRST goal with this tile after accepting ANY valid goal exit.
            foreach (goal in this._goals) {
                if (typeof(goal) == "array" && goal[0] == result.GetTile()) {
                    result = OpexAyStarV129.Path(result, goal[1], 0, this._Cost(result, goal[1], 0, this));
                    break;
                }
            }
        }
        this._pathfinder._open = null;
        this._closed = null; this._goalSet = null;
        this._tiles = null; this._dirs = null; this._costs = null;
        this._parents = null; this._blooms = null;
        this._running = false;
        return result;
    }

    function InitializePath(sources, goals, ignored_tiles = [])
    {
        if (sources.len() == 0 || goals.len() == 0) throw("empty sources/goals");
        this._tiles = []; this._dirs = []; this._costs = []; this._parents = []; this._blooms = [];
        this._closed = {}; this._goalSet = {};
        this._pathfinder._open = AIList();
        this._pathfinder._open.Sort(AIList.SORT_BY_VALUE, true);
        foreach (tile in ignored_tiles) this._closed[tile] <- ~0;
        foreach (g in goals) this._goalSet[(typeof(g) == "array") ? g[0] : g] <- true;

        this._cache_slope = {};
        this._cache_coast = {};
        this._cache_bridge = {};
        this._cache_tunnel = {};
        this._cache_rail = {};
        this._cache_buildable = {};
        this._estCache = {};

        this._goalCoords = [];
        local seen = {};
        foreach (g in goals) {
            local tile = (typeof(g) == "array") ? g[0] : g;
            if (tile in seen) continue;
            seen[tile] <- true;
            this._goalCoords.append({ tile = tile, x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile) });
        }

        /* V214 : couts de virage a la AAAHogEx, lus une fois par recherche (pas dans _Cost). */
        this._v214Turn = V214_RAIL_TURN_COST;
        /* V294j : si v294_rail_slope_engine actif et locomotive trop faible, cout de virage aligne a 100 comme AAA. */
        if (V294_RAIL_SLOPE_ENGINE > 0 && this._cost_turn == 100) this._v214Turn = 100;
        this._v214Tight = V214_RAIL_TIGHT_TURN_COST;
        if (this._v214Tight > 0) {
            /* AAA ramene le coude serre a 100 sous 40 tuiles de trajet. La recherche segmentee fixe
             * _v214RouteDist avant l'appel : ses sources intermediaires sont plus pres du but. */
            if (this._v214RouteDist < 0) {
                foreach (node in sources) {
                    foreach (g in this._goalCoords) {
                        local d = AIMap.DistanceManhattan((typeof(node) == "array") ? node[0] : node.GetTile(), g.tile);
                        if (this._v214RouteDist < 0 || d < this._v214RouteDist) this._v214RouteDist = d;
                    }
                }
            }
            if (this._v214RouteDist >= 0 && this._v214RouteDist < 40 && this._v214Tight > 100) this._v214Tight = 100;
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
            local id;
            if (typeof(node) == "array") {
                local first = this._Append(node[1], 0xFF, 0, -1);
                // Only a temporary input record for the cold source cost, never a Path instance.
                local seed = { _tile = node[1], _prev = null, _cost = 0 };
                id = this._Append(node[0], 0xFF, this._Cost(seed, node[0], 0xFF, this), first);
            } else {
                // Import the complete ancestry, including foreign Path nodes without _bloom.
                local chain = [];
                for (local n = node; n != null; n = n.GetParent()) chain.append(n);
                id = -1;
                for (local i = chain.len() - 1; i >= 0; i--) {
                    local n = chain[i];
                    id = this._Append(n.GetTile(), n.GetDirection(), n.GetCost(), id);
                }
            }
            // V129 seeds Path sources at g, without heuristic.
            this._pathfinder._open.AddItem(id, this._costs[id]);
        }
        this._goals = goals;
        this._running = false;
        this._consumed = 1;
    }

    function FindPath(iterations);
};

function OpexRailPathFinderV296::FindPath(iterations)
{
    local test_mode = AITestMode();
    local open = this._pathfinder._open;
    if (open == null) throw("can't execute over an uninitialized path");
    local tiles = this._tiles, dirs = this._dirs, costs = this._costs;
    local parents = this._parents, blooms = this._blooms;
    local closed = this._closed, goalSet = this._goalSet, goals = this._goals;
    local coords = this._goalCoords, cache = this._estCache;
    local single = coords.len() == 1;
    local goalX = coords[0].x, goalY = coords[0].y;
    local offsets = this._offsets, dirIdx = this._dirIdx;
    local bridgeTable = this._bestBridgeForLength;
    local maxBridge = this._max_bridge_length, maxTunnel = this._max_tunnel_length;
    local bridgeStop = max(4, maxBridge + 2);
    local maxCost = this._max_cost, weight = this._weight;
    local pops = 0, found = -1;
    local c_cost_bridge_per_tile = this._cost_bridge_per_tile;
    local c_cost_bridge_per_tile_ex = this._cost_bridge_per_tile_ex;
    local c_cost_bridge_per_tile_ex2 = this._cost_bridge_per_tile_ex2;
    local c_cost_coast = this._cost_coast;
    local c_cost_diagonal_tile = this._cost_diagonal_tile;
    local c_cost_level_crossing = this._cost_level_crossing;
    local c_cost_slope = this._cost_slope;
    local c_cost_tile = this._cost_tile;
    local c_cost_tunnel_per_tile = this._cost_tunnel_per_tile;
    local c_cost_tunnel_per_tile_ex = this._cost_tunnel_per_tile_ex;
    local c_cost_tunnel_per_tile_ex2 = this._cost_tunnel_per_tile_ex2;
    local c_cost_turn = this._cost_turn;
    local c_guideTiles = this._guideTiles;
    local c_outwardSide = this._outwardSide;
    local c_v214Tight = this._v214Tight;
    local c_v214Turn = this._v214Turn;
    local diag2 = c_cost_diagonal_tile * 2;
    while (!open.IsEmpty() && (iterations == -1 || iterations-- > 0)) {
        local id = open.Begin();
        open.RemoveItem(id);
        pops++;
        local cur = tiles[id], direction = dirs[id], par = parents[id];
        if (cur in closed) {
            local cd = closed[cur];
            if ((cd & direction) != 0) continue;
            if (par >= 0 && (blooms[par] & (1 << (cur % 61))) != 0) {
                local scan = par;
                while (scan >= 0 && tiles[scan] != cur) scan = parents[scan];
                // _CheckDirection always returns false in the rail finder.
                if (scan >= 0) continue;
            }
            closed[cur] = cd | direction;
        } else {
            closed[cur] <- direction;
        }
        local atGoal = cur in goalSet;
        if (atGoal) {
            foreach (goal in goals) {
                if (typeof(goal) != "array" && goal == cur) { found = id; break; }
            }
            if (found >= 0) break;
        }
        // Prune on g, exactly like V129 _Neighbours, including at a paired goal.
        if (this._HasRail(cur) || costs[id] >= maxCost) continue;
        if (this._IsBridge(cur) || this._IsTunnel(cur)) continue;
        local parTile = par >= 0 ? tiles[par] : 0;
        local grand = par >= 0 ? parents[par] : -1;
        local longArrival = par >= 0 && AIMap.DistanceManhattan(cur, parTile) > 1;
        local nextAfter = longArrival ? cur + (cur - parTile) / AIMap.DistanceManhattan(cur, parTile) : 0;
        local blocked = grand >= 0 ? tiles[grand] - parTile : 0;
        local shift0 = par >= 0 && !longArrival ? 4 + 4 * this._dir(parTile, cur) : 0;
        local slope = 0, bridgeDir = null;
        // Four unit candidates, bridge lengths 2..maxBridge-1, then tunnel.
        // Generation and consumption share scalars: no intermediate neighbour arrays.
        for (local slot = 0; slot <= bridgeStop; slot++) {
            local new_tile, new_direction;
            if (slot < 4) {
                if (longArrival) {
                    if (!AIRail.BuildRail(cur, nextAfter, nextAfter + offsets[slot])) continue;
                    new_tile = nextAfter;
                    new_direction = this._GetDirection(parTile, cur, nextAfter, true);
                } else {
                    new_tile = cur + offsets[slot];
                    if (par < 0) {
                        new_direction = 1 << (4 + dirIdx[slot]);
                    } else {
                        if (new_tile == parTile || (grand >= 0 && offsets[slot] == blocked)) continue;
                        if (!AIRail.BuildRail(parTile, cur, new_tile)) continue;
                        new_direction = 1 << (shift0 + dirIdx[slot]);
                    }
                }
            } else {
                if (longArrival || grand < 0) break;
                if (slot == 4) {
                    slope = this._GetSlope(cur);
                    if (slope == AITile.SLOPE_FLAT && this._IsBuildable(cur + (cur - parTile))) break;
                }
                if (slot < bridgeStop) {
                    local length = slot - 2;
                    if (!(length in bridgeTable)) continue;
                    new_tile = cur + length * (cur - parTile);
                    if (!AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridgeTable[length], cur, new_tile)) continue;
                } else {
                    if (slope != AITile.SLOPE_SW && slope != AITile.SLOPE_NW && slope != AITile.SLOPE_SE && slope != AITile.SLOPE_NE) break;
                    new_tile = AITunnel.GetOtherTunnelEnd(cur);
                    if (!AIMap.IsValidTile(new_tile)) break;
                    local length = AIMap.DistanceManhattan(cur, new_tile);
                    local before = cur + (cur - new_tile) / length;
                    if (AITunnel.GetOtherTunnelEnd(new_tile) != cur || length < 2 || before != parTile ||
                            length >= maxTunnel || !AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur)) break;
                }
                if (bridgeDir == null) bridgeDir = this._GetDirection(tiles[grand], parTile, cur, true);
                new_direction = bridgeDir;
            }
            if (atGoal) {
                foreach (goal in goals) {
                    if (typeof(goal) == "array" && goal[0] == cur && goal[1] == new_tile) { found = id; break; }
                }
                if (found >= 0) break;
            }
            if (new_direction <= 0) throw("directional value should never be zero or negative.");
            if ((new_tile in closed) && ((closed[new_tile] & new_direction) != 0)) continue;
            local prev_tile = cur;
            // BEGIN V129 COST: only self fields and ancestor accesses are substituted.
            local step_cost = 0;
            if (this._IsBridge(new_tile)) {
                if (AIBridge.GetOtherBridgeEnd(new_tile) != prev_tile) {
                    step_cost = c_cost_tile;
                    if (par >= 0 && tiles[par] - prev_tile != prev_tile - new_tile) step_cost += c_cost_turn;
                } else {
                    step_cost = AIMap.DistanceManhattan(new_tile, prev_tile) * c_cost_tile + this._GetBridgeNumSlopes(new_tile, prev_tile) * c_cost_slope;
                }
            } else if (this._IsTunnel(new_tile)) {
                if (AITunnel.GetOtherTunnelEnd(new_tile) != prev_tile) {
                    step_cost = c_cost_tile;
                    if (par >= 0 && tiles[par] - prev_tile != prev_tile - new_tile) step_cost += c_cost_turn;
                } else {
                    step_cost = AIMap.DistanceManhattan(new_tile, prev_tile) * c_cost_tile;
                }
            } else {
                local distManhattan = AIMap.DistanceManhattan(new_tile, prev_tile);
                if (distManhattan > 1) {
                    if (AITunnel.GetOtherTunnelEnd(new_tile) == prev_tile) {
                        step_cost = distManhattan * (c_cost_tile + c_cost_tunnel_per_tile);
                        if (c_cost_tunnel_per_tile_ex > 0 && distManhattan > 7) {
                            step_cost += (distManhattan - 7) * c_cost_tunnel_per_tile_ex;
                        }
                        if (c_cost_tunnel_per_tile_ex2 > 0 && distManhattan > 11) {
                            step_cost += (distManhattan - 11) * c_cost_tunnel_per_tile_ex2;
                        }
                    } else {
                        step_cost = distManhattan * (c_cost_tile + c_cost_bridge_per_tile) + this._GetBridgeNumSlopes(new_tile, prev_tile) * c_cost_slope;
                        if (c_cost_bridge_per_tile_ex > 0 && distManhattan > 7) {
                            step_cost += (distManhattan - 7) * c_cost_bridge_per_tile_ex;
                        }
                        if (c_cost_bridge_per_tile_ex2 > 0 && distManhattan > 11) {
                            step_cost += (distManhattan - 11) * c_cost_bridge_per_tile_ex2;
                        }
                    }
                    if (par >= 0) {
                        local gp = parents[par];
                        if (gp >= 0 &&
                                tiles[gp] - tiles[par] != max(AIMap.GetTileX(prev_tile) - AIMap.GetTileX(new_tile), AIMap.GetTileY(prev_tile) - AIMap.GetTileY(new_tile)) / distManhattan) {
                            step_cost += c_cost_turn;
                        }
                    }
                } else {
                    step_cost = c_cost_tile;
                    if (par >= 0) {
                        local par_tile = tiles[par];
                        if (AIMap.DistanceManhattan(par_tile, prev_tile) == 1 && par_tile - prev_tile != prev_tile - new_tile) step_cost = c_cost_diagonal_tile;
                        local gp = parents[par];
                        if (gp >= 0 && AIMap.DistanceManhattan(new_tile, tiles[gp]) == 3 &&
                                tiles[gp] - par_tile != prev_tile - new_tile) {
                            if (c_v214Turn <= 0) {
                                step_cost += c_cost_turn;
                            } else if (prev_tile - par_tile != par_tile - tiles[gp]) {
                                /* V214 : comme AAAHogEx, l'entree dans une diagonale est gratuite ; seule la
                                 * sortie (diagonale -> droite) paie. */
                                step_cost += c_v214Turn;
                            }
                        }
                        if (c_v214Tight > 0 && gp >= 0) {
                            local ggp = parents[gp];
                            /* V214 : droite, coin, droite perpendiculaire sur 4 pas unitaires (AAA _IsTightTurn). */
                            if (ggp >= 0 && AIMap.DistanceManhattan(new_tile, tiles[ggp]) == 4 &&
                                    new_tile - prev_tile == prev_tile - par_tile &&
                                    par_tile - tiles[gp] == tiles[gp] - tiles[ggp] &&
                                    prev_tile - par_tile != par_tile - tiles[gp]) {
                                step_cost += c_v214Tight;
                            }
                        }
                    }

                    if (this._IsCoast(new_tile)) {
                        step_cost += c_cost_coast;
                    }
                    /* V294d : passage a niveau, apres l'affectation du cout diagonal qui l'ecraserait. */
                    if (c_cost_level_crossing > 0 && AITile.HasTransportType(new_tile, AITile.TRANSPORT_ROAD)) {
                        step_cost += c_cost_level_crossing;
                    }

                    if (par >= 0 && !this._IsBridge(prev_tile) && !this._IsTunnel(prev_tile) &&
                            this._IsSlopedRail(tiles[par], prev_tile, new_tile)) {
                        step_cost += c_cost_slope;
                    }
                }
            }

            if (c_guideTiles != null) {
                if (c_guideTiles.rawin(new_tile)) {
                    local level = c_guideTiles[new_tile];
                    if (level == 0) {
                        step_cost = (step_cost * 5) / 10;
                    } else {
                        step_cost = (step_cost * (5 + level)) / 10;
                    }
                } else {
                    step_cost = step_cost * 2;
                }
            }

            if (c_outwardSide != null) {
                local dist = AIMap.DistanceManhattan(new_tile, prev_tile);
                if (dist >= 1) {
                    local dx = (AIMap.GetTileX(new_tile) - AIMap.GetTileX(prev_tile)) / dist;
                    local dy = (AIMap.GetTileY(new_tile) - AIMap.GetTileY(prev_tile)) / dist;
                    local px = -c_outwardSide * dy;
                    local py = c_outwardSide * dx;
                    local x_new = AIMap.GetTileX(new_tile) + px;
                    local y_new = AIMap.GetTileY(new_tile) + py;
                    local mapX = AIMap.GetMapSizeX();
                    local mapY = AIMap.GetMapSizeY();
                    if (x_new < 0 || y_new < 0 || x_new >= mapX || y_new >= mapY) {
                        step_cost += 400;
                    } else {
                        local lat_new = AIMap.GetTileIndex(x_new, y_new);
                        if (!AIMap.IsValidTile(lat_new) || !AITile.IsBuildable(lat_new)) {
                            step_cost += 400;
                        } else if (dist > 1) {
                            local x_prev = AIMap.GetTileX(prev_tile) + px;
                            local y_prev = AIMap.GetTileY(prev_tile) + py;
                            if (x_prev < 0 || y_prev < 0 || x_prev >= mapX || y_prev >= mapY) {
                                step_cost += 400;
                            } else {
                                local lat_prev = AIMap.GetTileIndex(x_prev, y_prev);
                                if (!AIMap.IsValidTile(lat_prev) || !AITile.IsBuildable(lat_prev)) {
                                    step_cost += 400;
                                }
                            }
                        } else {
                            local slope = AITile.GetSlope(lat_new);
                            if (slope != AITile.SLOPE_FLAT && slope != AITile.GetSlope(new_tile)) {
                                step_cost += 400;
                            }
                        }
                    }
                }
            }

            // END V129 COST
            local c = costs[id] + step_cost;
            local estimate;
            if (new_tile in cache) {
                estimate = cache[new_tile];
            } else {
                local x = AIMap.GetTileX(new_tile), y = AIMap.GetTileY(new_tile);
                local minCost = maxCost;
                if (single) {
                    local dx = abs(x - goalX), dy = abs(y - goalY);
                    local lo = dx < dy ? dx : dy, hi = dx > dy ? dx : dy;
                    local h = lo * diag2 + (hi - lo) * c_cost_tile;
                    if (h < minCost) minCost = h;
                } else {
                    foreach (g in coords) {
                        local dx = abs(x - g.x), dy = abs(y - g.y);
                        local lo = dx < dy ? dx : dy, hi = dx > dy ? dx : dy;
                        local h = lo * diag2 + (hi - lo) * c_cost_tile;
                        if (h < minCost) minCost = h;
                    }
                }
                estimate = weight > 100 && minCost < maxCost ? (minCost * weight) / 100 : minCost;
                cache[new_tile] <- estimate;
            }
            local nid = tiles.len();
            tiles.append(new_tile); dirs.append(new_direction); costs.append(c); parents.append(id);
            blooms.append(blooms[id] | (1 << (new_tile % 61)));
            open.AddItem(nid, c + estimate);
        }
        if (found >= 0) break;
    }
    this._consumed = pops == 0 ? 1 : pops;
    if (found >= 0) return this._Finish(found);
    if (open.IsEmpty()) return this._Finish(-1);
    this._running = true;
    return false;
}

/* Diagnostic only: both searches receive the same per-call iteration allowance.
 * If native finishes first, finish the reference before returning the native result.
 * This extra work is intentional in mode 2; LastConsumed counts only native pops.
 * A log at every call also records bounded probes / abandoned segmented searches.
 * V129 uses the configured V295 switch; log it so opcode comparisons are interpretable.
 */
class OpexRailPathfinderCheckerV296 extends OpexRailPathFinderV296
{
    _reference = null;
    _referenceResult = false;
    _iters129 = 0;
    _iters296 = 0;
    _ops129 = 0;
    _ops296 = 0;

    function InitializePath(sources, goals, ignored_tiles = [])
    {
        this._reference = OpexRailPathFinderV129();
        foreach (key in ["max_cost", "tile", "diagonal_tile", "turn", "slope", "bridge_per_tile",
                "tunnel_per_tile", "coast", "max_bridge_length", "max_tunnel_length", "astar_weight_pct",
                "level_crossing", "bridge_per_tile_ex", "bridge_per_tile_ex2", "tunnel_per_tile_ex",
                "tunnel_per_tile_ex2"]) this._reference.cost[key] = this.cost[key];
        this._reference._outwardSide = this._outwardSide;
        this._reference._guideTiles = this._guideTiles;
        this._reference._v214RouteDist = this._v214RouteDist;
        this._referenceResult = false;
        this._iters129 = 0; this._iters296 = 0;
        this._ops129 = 0; this._ops296 = 0;
        local test_mode = AITestMode();
        local pairs = [], imported = false;
        foreach (node in sources) {
            if (typeof(node) == "array") pairs.append(node);
            else {
                imported = true;
                local parent = node.GetParent();
                if (parent == null) throw("rail source requires a predecessor");
                pairs.append([node.GetTile(), parent.GetTile()]);
            }
        }
        this._reference.InitializePath(pairs, goals, ignored_tiles);
        if (imported) {
            local seeds = [];
            foreach (node in sources) {
                if (typeof(node) == "array") {
                    local p = OpexAyStarV129.Path(null, node[1], 0xFF, 0, 1 << (node[1] % 61));
                    seeds.append(OpexAyStarV129.Path(p, node[0], 0xFF,
                        this._reference._Cost(p, node[0], 0xFF, this._reference), p._bloom | (1 << (node[0] % 61))));
                } else {
                    local chain = [];
                    for (local n = node; n != null; n = n.GetParent()) chain.append(n);
                    local p = null, bloom = 0;
                    for (local i = chain.len() - 1; i >= 0; i--) {
                        local n = chain[i];
                        bloom = bloom | (1 << (n.GetTile() % 61));
                        p = OpexAyStarV129.Path(p, n.GetTile(), n.GetDirection(), n.GetCost(), bloom);
                    }
                    seeds.append(p);
                }
            }
            this._reference._pathfinder.InitializePath(seeds, goals, ignored_tiles);
        }
        base.InitializePath(sources, goals, ignored_tiles);
    }

    function SetWeight(weight)
    {
        base.SetWeight(weight);
        if (this._reference != null) this._reference.SetWeight(weight);
    }

    function _AdvanceReference(iterations)
    {
        if (this._referenceResult != false) return;
        local mark = OpexOpsMeasureBegin();
        this._referenceResult = this._reference.FindPath(iterations);
        this._ops129 += OpexOpsMeasureEnd(mark);
        this._iters129 += this._reference.LastConsumed();
    }

    function FindPath(iterations)
    {
        local test_mode = AITestMode();
        local mark = OpexOpsMeasureBegin();
        local result = base.FindPath(iterations);
        this._ops296 += OpexOpsMeasureEnd(mark);
        this._iters296 += this.LastConsumed();
        this._AdvanceReference(iterations);
        if (result != false && this._referenceResult == false) this._AdvanceReference(-1);
        if (DECISION_LOG) {
            local found129 = this._referenceResult != false && this._referenceResult != null;
            local found296 = result != false && result != null;
            local c129 = found129 ? this._referenceResult.GetCost() : -1;
            local c296 = found296 ? result.GetCost() : -1;
            OpexDecide("V296_CHECK", "iters_v129=" + this._iters129 + " iters_v296=" + this._iters296
                + " cost_v129=" + c129 + " cost_v296=" + c296
                + " ops_v129=" + this._ops129 + " ops_v296=" + this._ops296
                + " found_v129=" + (found129 ? 1 : 0) + " found_v296=" + (found296 ? 1 : 0)
                + " complete_v129=" + (this._referenceResult != false ? 1 : 0)
                + " complete_v296=" + (result != false ? 1 : 0)
                + " weight=" + this._weight + " v295=" + V295_ASTAR_FAST
                + " cost_equal=" + (found129 && found296 ? (c129 == c296 ? 1 : 0) : -1));
        }
        return result;
    }
};
