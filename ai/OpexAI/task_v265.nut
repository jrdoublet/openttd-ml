/* task_v265.nut — Prolongement d'une ligne fret rail vers une destination plus lointaine
 * (modele AAAHogEx SearchAndBuildAdditionalDest, main.nut:3149, et TrainRouteExtendBuilder,
 * trainroute.nut:3161). Reglage : v265_branch_extension (defaut 0).
 *
 * Comme AAA : la ligne garde son origine A ; une nouvelle gare C est posee pres d'une industrie
 * acceptante plus lointaine, une voie part d'un aiguillage pose sur la voie A->B existante, et la
 * rame livre desormais C au lieu de B. Le troncon aiguillage->B devient un cul-de-sac (AAA le
 * garde aussi, AddBranchLine).
 *
 * Perimetre : lignes fret a voie unique et a une seule rame (pas de croisement possible, donc ni
 * signal ni anti-blocage a poser), sans second cargo. Le voyageur demande un modele de demande
 * de la nouvelle ville : non traite ici.
 *
 * Aucun seuil propre : la decision reutilise le modele de ligne (OpexLineEconomics), le score du
 * portefeuille (OpexProjectScore), le budget d'iterations des candidats (OpexIterationBudget) et
 * la reserve du meilleur projet AIR financable (meme calcul que V266). Au defaut 0, la tache est
 * desactivee dans la file et aucune fonction de ce fichier n'est appelee. */

/* Profit annuel par rame du modele de ligne, a distance de revenu et longueur de voie donnees.
 * La ligne garde une seule rame : on compare donc le profit par rame, pas le total du modele. */
function OpexV265PerTrainProfit(catalog, line, incomeDistance, routeDistance)
{
  local econ = OpexLineEconomics(catalog, line.cargo, incomeDistance, line.monthly, line.kind,
                                 line.platformLength, routeDistance);
  if (econ == null) return null;
  local trains = econ.trains > 0 ? econ.trains : 1;
  return econ.profitAnnual / trains;
}

/* Lignes prolongeables : fret, voie unique, une rame, quais connus, pas de second cargo. */
function OpexV265LineEligible(line)
{
  if (line == null || !("mode" in line) || line.mode != "rail") return false;
  if (!("kind" in line) || line.kind != "freight") return false;
  if (("scrapping" in line) && line.scrapping) return false;
  if (("doubleTrack" in line) && line.doubleTrack != 0) return false;
  if (("loop" in line) && line.loop != 0) return false;
  if (("v181Loop" in line) && line.v181Loop) return false;
  if (("cargo2" in line) && line.cargo2 != null) return false;
  if (!("platformA" in line) || !("platformB" in line) || line.platformA == null || line.platformB == null) return false;
  if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() != 1) return false;
  if (!AIVehicle.IsValidVehicle(line.vehicles[0])) return false;
  if (!("monthly" in line) || line.monthly <= 0 || !("platformLength" in line)) return false;
  return true;
}

/* Tete de pont ou de tunnel ferroviaire dont l'ouvrage part dans la direction dir.
 * AIRail.IsRailTile les exclut (script_rail.cpp:34-40, OpenTTD 15). */
function OpexV265WorkHead(tile, dir)
{
  if (!AIMap.IsValidTile(tile) || !AITile.HasTransportType(tile, AITile.TRANSPORT_RAIL)) return false;
  local far = null;
  if (AIBridge.IsBridgeTile(tile)) far = AIBridge.GetOtherBridgeEnd(tile);
  else if (AITunnel.IsTunnelTile(tile)) far = AITunnel.GetOtherTunnelEnd(tile);
  if (far == null || far == tile) return false;
  return (far - tile) / AIMap.DistanceManhattan(tile, far) == dir;
}

/* Voie A->B lue sur la carte, comme OpexTraceTrackTiles (builder_rail.nut) mais en traversant
 * ponts et tunnels. OpexTraceTrackTiles ne les franchit pas : AIRail.IsRailTile est faux sur
 * une tete d'ouvrage (script_rail.cpp:34-40), et AreTilesConnected exige un predecesseur
 * adjacent (script_rail.cpp:268-271). Smoke du 18/10 : 6 echecs sur 6, motif gap.
 * Rend { tiles, reason }. */
function OpexV265TraceTrack(startStationTile, leadTile, endStationTile)
{
  if (!AIMap.IsValidTile(leadTile)) return { tiles = null, reason = "lead" };
  local endStId = AIStation.GetStationID(endStationTile);
  local tiles = [startStationTile, leadTile];
  local visited = {};
  visited[startStationTile] <- true;
  visited[leadTile] <- true;
  local offsets = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0), AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  local prev = startStationTile;
  local cur = leadTile;
  while (!(AIRail.IsRailStationTile(cur) && AIStation.GetStationID(cur) == endStId)) {
    local found = null;
    local dir = cur - prev;
    if (AIMap.DistanceManhattan(prev, cur) == 1 && OpexV265WorkHead(cur, dir)) {
      /* Entree d'ouvrage : sauter a l'autre tete, puis continuer dans l'axe. */
      local far = AIBridge.IsBridgeTile(cur) ? AIBridge.GetOtherBridgeEnd(cur) : AITunnel.GetOtherTunnelEnd(cur);
      tiles.append(far);
      visited[far] <- true;
      prev = far;
      found = far + dir;
      if (!AIRail.IsRailTile(found) && !OpexV265WorkHead(found, dir)) return { tiles = null, reason = "exit" };
    } else {
      if (!AIRail.IsRailTile(cur)) return { tiles = null, reason = "notrail" };
      foreach (off in offsets) {
        local n = cur + off;
        if (n == prev || !AIMap.IsValidTile(n)) continue;
        if (!AIRail.AreTilesConnected(prev, cur, n)) continue;
        if (!AIRail.IsRailTile(n) && !OpexV265WorkHead(n, off)) continue;
        if (AIRail.IsRailStationTile(n) && AIStation.GetStationID(n) != endStId) continue;
        found = n;
        break;
      }
      if (found == null) return { tiles = null, reason = "gap" };
      prev = cur;
    }
    if (found in visited) return { tiles = null, reason = "cycle" };
    visited[found] <- true;
    tiles.append(found);
    cur = found;
  }
  return { tiles = tiles, reason = "ok" };
}

/* Reserve = meilleur projet AIR (ou renfort AIR) encore financable, plus la reserve de caisse.
 * Copie du calcul V266 (branche v266, non fusionnee) : candidateGroups contient tous les modes
 * avant la troncature au financable (projects.nut). null tant que le portefeuille n'existe pas. */
function OpexAI::_v265AirReserve()
{
  if (this._projects == null || !("candidateGroups" in this._projects)) return null;
  local available = AICompany.GetBankBalance(AICompany.COMPANY_SELF) - OpexCashReserve();
  local best = null;
  local bestScore = 0.0;
  local kDec = OpexC69ComputeKDec().K_dec;
  foreach (key, group in this._projects.candidateGroups) {
    foreach (p in group) {
      if (!OpexC121AutopsyIsAirRelated(p)) continue;
      if (p.mode == "air") {
        if (!OpexIncrementalCandidateStillValid(p, this._lines, this._abandonedPairs)) continue;
      } else {
        /* Le filtre O/D exact rejette les renforts de flotte par construction. */
        local live = false;
        foreach (line in this._lines)
          if (line == p.payload.line && !line.scrapping) live = true;
        if (!live) continue;
      }
      local cost = OpexProjectFinanceCapital(p);
      if (cost <= 0 || cost > available) continue;
      /* Meme denominateur que projects_selection.nut ; ne pas relire un fundScore perime. */
      local decisionCost = (p.mode == "air" && ("decisionFinanceCapital" in p)
        && p.decisionFinanceCapital > 0) ? p.decisionFinanceCapital : cost;
      local exempt = p.mode == "fleet" && !OpexC121ProjectHasRealization(p);
      local scored = clone p;
      scored.fundScore <- OpexProjectScore(OpexProjectFundProfit(p),
        kDec > decisionCost && !exempt ? kDec : decisionCost);
      local score = OpexProjectSelectionScore(scored, "fundScore");
      if (best == null || score > bestScore) { best = p; bestScore = score; }
    }
  }
  return OpexCashReserve() + (best == null ? 0 : OpexProjectFinanceCapital(best));
}

/* Sources de l'A* : pour chaque tuile droite et nue de la voie A->B, ses deux voisines
 * perpendiculaires constructibles ou l'aiguillage (A->tuile->voisine) passe en mode test.
 * Le pathfinder ne developpe pas un noeud pose sur un rail existant (_Neighbours, _HasRail) :
 * la source est donc la premiere tuile neuve, la tuile de la voie servant de predecesseur.
 * Rend { sources = [pseudo-plans], forks = { "fork|n" -> {fork, prev, index} } }. */
function OpexV265ForkSources(path)
{
  local out = { sources = [], forks = {} };
  local xStep = AIMap.GetTileIndex(1, 0);
  local yStep = AIMap.GetTileIndex(0, 1);
  local test = AITestMode();
  /* path[0] est le quai A, path[len-1] le quai B : on exige deux voisines de voie nue. */
  for (local i = 2; i < path.len() - 2; i++) {
    local prev = path[i - 1];
    local t = path[i];
    local next = path[i + 1];
    if (AIMap.DistanceManhattan(prev, t) != 1 || AIMap.DistanceManhattan(t, next) != 1) continue;
    if (t - prev != next - t) continue;
    if (!AIRail.IsRailTile(t) || AIRail.IsRailStationTile(t) || AIRail.IsRailDepotTile(t)) continue;
    if (AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t) || AIRail.IsLevelCrossingTile(t)) continue;
    local tracks = AIRail.GetRailTracks(t);
    if (tracks != AIRail.RAILTRACK_NE_SW && tracks != AIRail.RAILTRACK_NW_SE) continue;
    if (AIRail.GetSignalType(t, prev) != AIRail.SIGNALTYPE_NONE
        || AIRail.GetSignalType(t, next) != AIRail.SIGNALTYPE_NONE) continue;
    local perp = (abs(t - prev) == xStep) ? yStep : xStep;
    foreach (p in [perp, -perp]) {
      local n = t + p;
      if (!AIMap.IsValidTile(n) || !AITile.IsBuildable(n)) continue;
      if (!AIRail.BuildRail(prev, t, n)) continue;
      out.sources.append({ lead = n, station_exit = t });
      out.forks[t + "|" + n] <- { fork = t, prev = prev, index = i };
    }
  }
  return out;
}

/* Point d'entree de la file. Une ligne par appel (curseur), une passe complete par mois au plus :
 * le cout par appel reste borne par un balayage d'industries et quelques OpexLineEconomics. */
function OpexAI::_dispatchV265BranchExtension(task, year)
{
  if (!V265_BRANCH_EXTENSION) return false;
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v265SweepMonth != ym) {
    this._v265SweepMonth = ym;
    this._v265SweepDone = false;
  }
  if (this._v265SweepDone) return false;
  if (this._v265Failed == null) this._v265Failed = {};
  if (this._lines == null || this._lines.len() == 0 || this._catalog == null) {
    this._v265SweepDone = true;
    return false;
  }
  /* Le creneau A* est unique : ne jamais passer devant le portefeuille ou un doublement. */
  if (this._railSearch != null || this._railExpansion != null) return false;

  if (this._v265Cursor >= this._lines.len()) this._v265Cursor = 0;
  local line = this._lines[this._v265Cursor];
  this._v265Cursor++;
  if (this._v265Cursor >= this._lines.len()) this._v265SweepDone = true;
  if (!OpexV265LineEligible(line)) return false;
  this._v265TryLine(line, date);
  return true;
}

function OpexAI::_v265TryLine(line, date)
{
  local reserve = this._v265AirReserve();
  if (reserve == null) return;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local catalog = this._catalog;
  local bounds = OpexCatalogBounds(catalog);
  local dAB = AIMap.DistanceManhattan(line.stationA, line.stationB);
  /* Avant l'A*, longueurs de voie approchees par la distance Manhattan des deux cotes. */
  local current = OpexV265PerTrainProfit(catalog, line, dAB, dAB);
  if (current == null) return;
  local traceKey = line.lineId + "|-1";
  if ((traceKey in this._v265Failed) && date - this._v265Failed[traceKey] < ABANDON_COOLDOWN_DAYS) return;

  local best = null;
  local inds = AIIndustryList_CargoAccepting(line.cargo);
  for (local ind = inds.Begin(); !inds.IsEnd(); ind = inds.Next()) {
    if (("dstIndustry" in line) && ind == line.dstIndustry) continue;
    local key = line.lineId + "|" + ind;
    if ((key in this._v265Failed) && date - this._v265Failed[key] < ABANDON_COOLDOWN_DAYS) continue;
    local indTile = AIIndustry.GetLocation(ind);
    local dAC = AIMap.DistanceManhattan(line.stationA, indTile);
    /* Prolonger, pas detourner : C plus loin de A que B, dans la borne des candidats rail. */
    if (dAC <= dAB || dAC > bounds.railMax) continue;
    local dBC = AIMap.DistanceManhattan(line.stationB, indTile);
    local after = OpexV265PerTrainProfit(catalog, line, dAC, dAB + dBC);
    if (after == null || after <= current) continue;
    /* Meme cout de voie que le modele de ligne (economy.nut, effectiveTrackCost). */
    local capital = dBC * catalog.costTrackPerTile * RAIL_TERRAIN_FACTOR / 100 + line.platformLength * catalog.costStation;
    if (money < capital + reserve) continue;
    local score = OpexProjectScore(after - current, capital);
    if (best == null || score > best.score)
      best = { ind = ind, tile = indTile, gain = after - current, capital = capital, score = score };
  }
  if (best == null) return;

  local leadA = OpexC41RailApproachLead(line.platformA, line.stationA);
  local trace = (leadA == null) ? { tiles = null, reason = "lead" }
      : OpexV265TraceTrack(line.stationA, leadA, line.stationB);
  local path = trace.tiles;
  if (path == null) {
    /* La voie ne depend pas de C : memoriser l'echec pour la ligne entiere (ind -1). */
    this._v265Fail(line, -1, "trace_" + trace.reason);
    return;
  }
  local forks = OpexV265ForkSources(path);
  if (forks.sources.len() == 0) {
    this._v265Fail(line, best.ind, "nofork");
    return;
  }
  local plansC = OpexStationPlans(best.tile, line.stationB, STATION_SEARCH_RADIUS, line.platformLength,
                                  MAX_STATION_PLANS, line.cargo, catalog.railCoverage, false);
  if (plansC.len() == 0) {
    this._v265Fail(line, best.ind, "site");
    return;
  }
  local budgetInfo = OpexIterationBudget(best.gain, MIN_RATIO, HARD_ITERATION_CAP);
  local weight = OpexRailAstarWeight(AIMap.DistanceManhattan(line.stationB, best.tile));
  local segmented = OpexCreateSegmentedSearch(forks.sources, plansC, budgetInfo.budget, null, weight);
  if (segmented == null) {
    this._v265Fail(line, best.ind, "nopa");
    return;
  }
  if (DECISION_LOG) {
    OpexDecide("V265_SEARCH", "line=" + line.lineId + " cargo=" + line.cargo + " ind=" + best.ind
               + " dAB=" + dAB + " dAC=" + AIMap.DistanceManhattan(line.stationA, best.tile)
               + " gain=" + best.gain + " capital=" + best.capital + " reserve=" + reserve
               + " forks=" + forks.sources.len() + " plans=" + plansC.len() + " budget=" + budgetInfo.budget);
  }
  this._railSearch = {
    kind = "v265",
    phase = "search",
    pathfinder = null,
    segmented = segmented,
    weight = weight,
    spent = 0,
    iterationBudget = budgetInfo.budget,
    safetyDeadline = AIController.GetTick() + RAIL_SEARCH_SAFETY_TICKS,
    line = line,
    v265 = { ind = best.ind, tile = best.tile, forks = forks.forks, plansC = plansC,
             pathLen = path.len(), current = current },
  };
  this._continueRailSearch();
}

function OpexAI::_v265Fail(line, ind, reason)
{
  this._v265Failed[line.lineId + "|" + ind] <- AIDate.GetCurrentDate();
  if (DECISION_LOG) OpexDecide("V265_FAIL", "line=" + line.lineId + " ind=" + ind + " reason=" + reason);
}

/* Appele par _continueRailSearch quand la recherche kind=v265 est finie (phase build). */
function OpexAI::_v265ConsumeSearch()
{
  local state = this._railSearch;
  this._railSearch = null;
  local line = state.line;
  local v = state.v265;
  local search = state.search;
  if (!OpexV265LineEligible(line)) {
    this._v265Fail(line, v.ind, "line_changed");
    return;
  }
  if (search.path == false || search.path == null) {
    this._v265Fail(line, v.ind, "path_" + search.stop);
    return;
  }
  local tiles = OpexResolveSearchTiles(search);
  local structures = OpexResolveSearchStructures(search);
  local last = tiles.len() - 1;
  if (tiles.len() < 4) { this._v265Fail(line, v.ind, "short"); return; }
  local forkKey = tiles[0] + "|" + tiles[1];
  if (!(forkKey in v.forks)) { this._v265Fail(line, v.ind, "nomatch_fork"); return; }
  local fork = v.forks[forkKey];
  local planC = OpexMatchPlan(v.plansC, tiles[last]);
  if (planC == null || tiles[last - 1] != planC.lead) { this._v265Fail(line, v.ind, "nomatch_station"); return; }
  /* Le pathfinder ne voit pas le predecesseur de l'aiguillage : refuser le demi-tour a 90 degres. */
  if (tiles[2] - tiles[1] == fork.prev - fork.fork) { this._v265Fail(line, v.ind, "hairpin"); return; }

  /* Reevaluation sur la voie reelle : A->aiguillage sur l'ancienne voie, puis la branche. */
  local catalog = this._catalog;
  local dAB = AIMap.DistanceManhattan(line.stationA, line.stationB);
  local dAC = AIMap.DistanceManhattan(line.stationA, planC.station_exit);
  local current = OpexV265PerTrainProfit(catalog, line, dAB, v.pathLen);
  local after = OpexV265PerTrainProfit(catalog, line, dAC, fork.index + last);
  if (current == null || after == null || after <= current) {
    this._v265Fail(line, v.ind, "econ_after_path");
    return;
  }
  local capital = tiles.len() * catalog.costTrackPerTile * RAIL_TERRAIN_FACTOR / 100 + planC.length * catalog.costStation;
  local reserve = this._v265AirReserve();
  if (reserve == null || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < capital + reserve) {
    /* Refus de caisse : pas un echec du site, on reessaiera a une passe suivante. */
    if (DECISION_LOG) OpexDecide("V265_SKIP", "line=" + line.lineId + " reason=cash capital=" + capital
                                 + " reserve=" + reserve);
    return;
  }

  local costs = AIAccounting();
  OpexAir0310InvalidateSiteValidity();
  /* Gare et branche d'abord ; l'aiguillage sur la voie vivante en dernier. */
  if (!AIRail.BuildRailStation(planC.anchor, planC.direction, 1, planC.length, AIStation.STATION_NEW)) {
    OpexRollback(null, null, planC, null, null);
    this._v265Fail(line, v.ind, "station");
    return;
  }
  local trackFailed = OpexBuildTrack(tiles, structures);
  local connected = trackFailed == 0
      && AIRail.AreTilesConnected(tiles[last - 2], tiles[last - 1], planC.station_exit);
  if (!connected) {
    /* OpexRollback ne demolit ni tiles[0] (voie vivante) ni la derniere tuile (le quai). */
    OpexRollback(tiles, null, planC, null, null);
    this._v265Fail(line, v.ind, "track");
    return;
  }
  local junction = AIRail.BuildRail(fork.prev, fork.fork, tiles[1])
      && AIRail.AreTilesConnected(fork.prev, fork.fork, tiles[1])
      && AIRail.AreTilesConnected(fork.fork, tiles[1], tiles[2]);
  if (!junction) {
    AIRail.RemoveRail(fork.prev, fork.fork, tiles[1]);
    OpexRollback(tiles, null, planC, null, null);
    this._v265Fail(line, v.ind, "junction");
    return;
  }

  /* La rame livre C au lieu de B : memes drapeaux, ordre insere avant l'ancien puis l'ancien retire. */
  local train = line.vehicles[0];
  local oldStation = AIStation.GetStationID(line.stationB);
  local redirected = false;
  for (local i = 0; i < AIOrder.GetOrderCount(train); i++) {
    if (AIStation.GetStationID(AIOrder.GetOrderDestination(train, i)) != oldStation) continue;
    local flags = AIOrder.GetOrderFlags(train, i);
    if (!AIOrder.InsertOrder(train, i, planC.station_exit, flags)) break;
    if (!AIOrder.RemoveOrder(train, i + 1)) {
      AIOrder.RemoveOrder(train, i);
      break;
    }
    redirected = true;
    break;
  }
  if (!redirected) {
    AIRail.RemoveRail(fork.prev, fork.fork, tiles[1]);
    OpexRollback(tiles, null, planC, null, null);
    this._v265Fail(line, v.ind, "orders");
    return;
  }

  local oldStationB = line.stationB;
  line.stationB = planC.station_exit;
  line.platformB = { anchor = planC.anchor, direction = planC.direction, step = planC.step,
                     length = planC.length, station_exit = planC.station_exit, lead = planC.lead };
  line.originB = v.tile;
  line.dstIndustry = v.ind;
  line.distance = AIMap.DistanceManhattan(line.originA, v.tile);
  local count = ("v265Extensions" in line) ? line.v265Extensions : 0;
  line.v265Extensions <- count + 1;
  this._saveProjection = null;
  this._c76BumpLayer("lines", false);
  if (DECISION_LOG) {
    OpexDecide("V265_BUILD", "line=" + line.lineId + " ind=" + v.ind + " old_dst=" + oldStationB
               + " new_dst=" + planC.station_exit + " fork=" + fork.fork + " fork_index=" + fork.index
               + " branch_tiles=" + tiles.len() + " dAB=" + dAB + " dAC=" + dAC
               + " per_train_before=" + current + " per_train_after=" + after
               + " cost=" + costs.GetCosts());
  }
}
