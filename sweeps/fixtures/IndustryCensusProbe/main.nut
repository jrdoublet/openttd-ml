/* V290: Industry and water connectivity census probe.
 * Does not build anything. Records oil rigs, coastal industries,
 * connected water components, and pairs with same_comp=1.
 */

class IndustryCensusProbe extends AIController {
  _mapW = 0;
  _mapH = 0;
  _waterComp = null; // array(mapW * mapH, -1)
  _compSizes = null; // array of sizes of each component
  _compCount = 0;
  _knownIndustries = null; // table id -> true
  _firstPassDone = false;

  function Start() {
    this._mapW = AIMap.GetMapSizeX();
    this._mapH = AIMap.GetMapSizeY();
    this._knownIndustries = {};

    AILog.Info("V290_START map_w=" + this._mapW + " map_h=" + this._mapH);

    // 1. Compute navigable water components by BFS
    this.BuildWaterComponents();

    // 2. Main monthly loop
    local lastMonth = -1;
    while (true) {
      local date = AIDate.GetCurrentDate();
      local month = AIDate.GetMonth(date);
      if (month != lastMonth) {
        lastMonth = month;
        this.MonthlyCensus(date);
      }
      AIController.Sleep(1);
    }
  }

  /* Compute connected components of navigable water across the entire map.
   * Uses a 4-connected BFS bounded with Sleep(1) to respect the opcode budget.
   */
  function BuildWaterComponents() {
    local total = this._mapW * this._mapH;
    this._waterComp = array(total, -1);
    this._compSizes = [];
    this._compCount = 0;
    local w = this._mapW;
    local h = this._mapH;

    for (local i = 0; i < total; i++) {
      if (AIController.GetOpsTillSuspend() < 1500) AIController.Sleep(1);

      if (this._waterComp[i] >= 0) continue;

      local x = i % w;
      local y = i / w;
      local tile = AIMap.GetTileIndex(x, y);
      if (!AITile.IsWaterTile(tile)) continue;

      // Start new component BFS
      local compId = this._compCount;
      this._compCount++;
      local queue = [i];
      this._waterComp[i] = compId;
      local count = 0;

      for (local head = 0; head < queue.len(); head++) {
        if (AIController.GetOpsTillSuspend() < 1500) AIController.Sleep(1);

        local cur = queue[head];
        local cx = cur % w;
        local cy = cur / w;
        local ctile = AIMap.GetTileIndex(cx, cy);
        count++;

        local neighbors = [
          [cx + 1, cy],
          [cx - 1, cy],
          [cx, cy + 1],
          [cx, cy - 1]
        ];

        foreach (n in neighbors) {
          local nx = n[0];
          local ny = n[1];
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;

          local nidx = ny * w + nx;
          if (this._waterComp[nidx] >= 0) continue;

          local ntile = AIMap.GetTileIndex(nx, ny);
          if (!AITile.IsWaterTile(ntile)) continue;
          if (!AIMarine.AreWaterTilesConnected(ctile, ntile)) continue;

          this._waterComp[nidx] = compId;
          queue.append(nidx);
        }
      }
      this._compSizes.append(count);
    }

    AILog.Info("V290_WATER_INIT comps=" + this._compCount);
  }

  /* Scan a bounding box around location to find all tiles belonging to industry id. */
  function GetIndustryTiles(id) {
    local loc = AIIndustry.GetLocation(id);
    local lx = AIMap.GetTileX(loc);
    local ly = AIMap.GetTileY(loc);
    local w = this._mapW;
    local h = this._mapH;
    local tiles = [];

    for (local dy = -3; dy <= 6; dy++) {
      local y = ly + dy;
      if (y < 0 || y >= h) continue;
      for (local dx = -3; dx <= 6; dx++) {
        local x = lx + dx;
        if (x < 0 || x >= w) continue;
        local t = AIMap.GetTileIndex(x, y);
        if (AIMap.IsValidTile(t) && AIIndustry.GetIndustryID(t) == id) {
          tiles.append(t);
        }
      }
    }
    if (tiles.len() == 0 && AIMap.IsValidTile(loc)) {
      tiles.append(loc);
    }
    return tiles;
  }

  /* Check whether an industry is coastal (water tile strictly less than 3 tiles away)
   * and determine its primary and all touching water component IDs.
   */
  function GetIndustryWaterInfo(id, indTiles, onWater) {
    local w = this._mapW;
    local h = this._mapH;
    local coastal = onWater ? 1 : 0;
    local bestComp = -1;
    local bestDist = 999;
    local bestCompSize = -1;
    local compsFound = {};

    // Built-in dock (e.g. Oil Rig)
    if (AIIndustry.HasDock(id)) {
      local dock = AIIndustry.GetDockLocation(id);
      if (AIMap.IsValidTile(dock)) {
        local dx = AIMap.GetTileX(dock);
        local dy = AIMap.GetTileY(dock);
        local dockAdj = [[dx+1, dy], [dx-1, dy], [dx, dy+1], [dx, dy-1], [dx, dy]];
        foreach (adj in dockAdj) {
          local ax = adj[0], ay = adj[1];
          if (ax >= 0 && ay >= 0 && ax < w && ay < h) {
            local at = AIMap.GetTileIndex(ax, ay);
            if (AITile.IsWaterTile(at)) {
              local c = this._waterComp[ay * w + ax];
              if (c >= 0) {
                bestComp = c;
                bestDist = 0;
                coastal = 1;
                compsFound[c] <- true;
                break;
              }
            }
          }
        }
      }
    }

    // Tiles strictly less than 3 tiles away (dx in [-2, 2], dy in [-2, 2])
    foreach (t in indTiles) {
      local tx = AIMap.GetTileX(t);
      local ty = AIMap.GetTileY(t);

      for (local dy = -2; dy <= 2; dy++) {
        local y = ty + dy;
        if (y < 0 || y >= h) continue;
        for (local dx = -2; dx <= 2; dx++) {
          local x = tx + dx;
          if (x < 0 || x >= w) continue;
          local wt = AIMap.GetTileIndex(x, y);
          if (AITile.IsWaterTile(wt)) {
            coastal = 1;
            local dist = abs(dx) > abs(dy) ? abs(dx) : abs(dy);
            local c = this._waterComp[y * w + x];
            if (c >= 0) {
              compsFound[c] <- true;
              local cSize = (c < this._compSizes.len()) ? this._compSizes[c] : 0;
              if (dist < bestDist || (dist == bestDist && cSize > bestCompSize)) {
                bestDist = dist;
                bestComp = c;
                bestCompSize = cSize;
              }
            }
          }
        }
      }
    }

    return { coastal = coastal, water_comp = bestComp, all_comps = compsFound };
  }

  function SanitizeName(name) {
    if (name == null || name == "") return "-";
    local res = "";
    for (local i = 0; i < name.len(); i++) {
      local ch = name.slice(i, i + 1);
      res += (ch == " ") ? "_" : ch;
    }
    return res;
  }

  function IsOilRig(id, indType, rawName) {
    if (rawName != null && (rawName.find("Oil Rig") != null || rawName.find("Oil_Rig") != null || rawName.find("plate-forme") != null)) {
      return true;
    }
    if ((AIIndustry.IsBuiltOnWater(id) || AIIndustryType.IsBuiltOnWater(indType)) &&
        (AIIndustry.HasDock(id) || AIIndustryType.HasDock(indType))) {
      return true;
    }
    return false;
  }

  function FormatIndustryCargos(id, indType) {
    local prodStr = "";
    local prodList = AIIndustryType.GetProducedCargo(indType);
    if (prodList != null) {
      for (local c = prodList.Begin(); !prodList.IsEnd(); c = prodList.Next()) {
        if (!AICargo.IsValidCargo(c)) continue;
        local label = AICargo.GetCargoLabel(c);
        local qte = AIIndustry.GetLastMonthProduction(id, c);
        if (prodStr != "") prodStr += ",";
        prodStr += label + ":" + qte;
      }
    }
    if (prodStr == "") prodStr = "-";

    local acceptStr = "";
    local accList = AIIndustryType.GetAcceptedCargo(indType);
    if (accList != null) {
      for (local c = accList.Begin(); !accList.IsEnd(); c = accList.Next()) {
        if (!AICargo.IsValidCargo(c)) continue;
        local label = AICargo.GetCargoLabel(c);
        if (acceptStr != "") acceptStr += ",";
        acceptStr += label;
      }
    }
    if (acceptStr == "") acceptStr = "-";

    return { prod = prodStr, accept = acceptStr };
  }

  function MonthlyCensus(date) {
    local y = AIDate.GetYear(date);
    local m = AIDate.GetMonth(date);
    local d = AIDate.GetDayOfMonth(date);
    local mStr = (m < 10) ? ("0" + m) : ("" + m);
    local dStr = (d < 10) ? ("0" + d) : ("" + d);
    local dateStr = y + "-" + mStr + "-" + dStr;

    // 1. Detect closed industries
    local toRemove = [];
    foreach (id, _ in this._knownIndustries) {
      if (!AIIndustry.IsValidIndustry(id)) {
        AILog.Info("V290_IND_CLOSE id=" + id);
        toRemove.append(id);
      }
    }
    foreach (id in toRemove) {
      delete this._knownIndustries[id];
    }

    // 2. Scan current industries
    local indList = AIIndustryList();
    local currentIndustries = [];
    local oilRigsCount = 0;
    local coastalCount = 0;

    for (local id = indList.Begin(); !indList.IsEnd(); id = indList.Next()) {
      if (!AIIndustry.IsValidIndustry(id)) continue;
      if (AIController.GetOpsTillSuspend() < 1500) AIController.Sleep(1);

      local indType = AIIndustry.GetIndustryType(id);
      local rawName = AIIndustryType.GetName(indType);
      local typeName = this.SanitizeName(rawName);
      local loc = AIIndustry.GetLocation(id);
      local lx = AIMap.GetTileX(loc);
      local ly = AIMap.GetTileY(loc);
      local onWater = (AIIndustry.IsBuiltOnWater(id) || AIIndustryType.IsBuiltOnWater(indType)) ? 1 : 0;
      local hasDock = (AIIndustry.HasDock(id) || AIIndustryType.HasDock(indType)) ? 1 : 0;

      local indTiles = this.GetIndustryTiles(id);
      local waterInfo = this.GetIndustryWaterInfo(id, indTiles, onWater);
      local coastal = waterInfo.coastal;
      local waterComp = waterInfo.water_comp;

      local isRig = this.IsOilRig(id, indType, rawName);
      if (isRig) oilRigsCount++;
      if (coastal == 1) coastalCount++;

      local isNew = !(id in this._knownIndustries);
      if (isNew) {
        this._knownIndustries[id] <- true;
        local cargos = this.FormatIndustryCargos(id, indType);
        AILog.Info("V290_IND id=" + id + " type=" + typeName + " tile=" + loc + " x=" + lx + " y=" + ly
                   + " on_water=" + onWater + " coastal=" + coastal + " water_comp=" + waterComp
                   + " dock=" + hasDock + " prod=" + cargos.prod + " accept=" + cargos.accept);
      }

      currentIndustries.append({
        id = id,
        type = indType,
        typeName = typeName,
        tile = loc,
        x = lx,
        y = ly,
        on_water = onWater,
        coastal = coastal,
        water_comp = waterComp,
        all_comps = waterInfo.all_comps
      });
    }

    AILog.Info("V290_MONTH date=" + dateStr + " industries=" + currentIndustries.len()
               + " oil_rigs=" + oilRigsCount + " coastal=" + coastalCount);

    // 3. First pass only: log V290_PAIR and V290_SUMMARY
    if (!this._firstPassDone) {
      this._firstPassDone = true;
      this.ComputeFirstPassPairs(currentIndustries);
    }
  }

  function ComputeFirstPassPairs(industries) {
    local bulkLabels = ["COAL", "IORE", "GRAI", "WOOD", "OIL_", "STEL", "GOOD"];
    local targetCargos = {}; // label -> cargo_id
    local cList = AICargoList();

    for (local c = cList.Begin(); !cList.IsEnd(); c = cList.Next()) {
      if (!AICargo.IsValidCargo(c)) continue;
      local l = AICargo.GetCargoLabel(c);
      foreach (wanted in bulkLabels) {
        if (l == wanted) {
          targetCargos[l] <- c;
          break;
        }
      }
    }

    local pairCount = {};
    local sameCompCount = {};
    foreach (label in bulkLabels) {
      pairCount[label] <- 0;
      sameCompCount[label] <- 0;
    }
    local totalPairs = 0;
    local totalSameComp = 0;

    // Filter coastal industries
    local coastalInds = [];
    foreach (ind in industries) {
      if (ind.coastal == 1 || ind.on_water == 1) {
        coastalInds.append(ind);
      }
    }

    foreach (label, cargoId in targetCargos) {
      foreach (src in coastalInds) {
        if (AIController.GetOpsTillSuspend() < 1500) AIController.Sleep(1);

        // Check if src produces this cargo
        local prodList = AIIndustryType.GetProducedCargo(src.type);
        local produces = false;
        if (prodList != null) {
          for (local c = prodList.Begin(); !prodList.IsEnd(); c = prodList.Next()) {
            if (c == cargoId) { produces = true; break; }
          }
        }
        if (!produces) continue;

        foreach (dst in coastalInds) {
          if (src.id == dst.id) continue;

          // Check if dst accepts this cargo
          local accList = AIIndustryType.GetAcceptedCargo(dst.type);
          local accepts = false;
          if (accList != null) {
            for (local c = accList.Begin(); !accList.IsEnd(); c = accList.Next()) {
              if (c == cargoId) { accepts = true; break; }
            }
          }
          if (!accepts) continue;

          local dist = AIMap.DistanceManhattan(src.tile, dst.tile);
          if (dist < 40 || dist > 400) continue;

          // Connection by same water component
          local sameComp = 0;
          if (src.water_comp >= 0 && dst.water_comp >= 0) {
            if (src.water_comp == dst.water_comp) {
              sameComp = 1;
            } else {
              foreach (sc, _ in src.all_comps) {
                if (sc in dst.all_comps) { sameComp = 1; break; }
              }
            }
          }

          pairCount[label]++;
          totalPairs++;
          if (sameComp == 1) {
            sameCompCount[label]++;
            totalSameComp++;
          }

          AILog.Info("V290_PAIR src=" + src.id + " dst=" + dst.id + " cargo=" + label
                     + " dist=" + dist + " same_comp=" + sameComp);
        }
      }
    }

    foreach (label in bulkLabels) {
      AILog.Info("V290_SUMMARY cargo=" + label + " pairs=" + pairCount[label]
                 + " same_comp=" + sameCompCount[label]);
    }
    AILog.Info("V290_SUMMARY_TOTAL total_pairs=" + totalPairs + " total_same_comp=" + totalSameComp);
  }
}
