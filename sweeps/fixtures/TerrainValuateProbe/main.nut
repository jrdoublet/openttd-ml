/* C67: Valuate terrain reader measurement fixture.
 * Verifies:
 * (a) Exactitude of Valuate reader against reference tile-by-tile reader (5x5 and 10x10)
 * (b) Opcode cost comparison (reference vs Valuate)
 * (c) Non-suspendable bound: maximum opcode cost of any atomic call
 *
 * Contract: docs/c67_cartographie_contrat.md
 */

require("budget.nut");
require("terrain_map.nut");
require("terrain_valuate.nut");

class TerrainValuateProbe extends AIController {
  _signIndex = 0;

  function Emit(name) {
    if (name.len() > 31) throw "C67V: sign length exceeds 31 characters";
    local w = AIMap.GetMapSizeX();
    local h = AIMap.GetMapSizeY();
    local x = w / 2 - 20 + this._signIndex % 40;
    local y = h / 2 - 2 + this._signIndex / 40;
    this._signIndex++;
    local tile = AIMap.GetTileIndex(x, y);
    local signId = AISign.BuildSign(tile, name);
    if (!AISign.IsValidSign(signId)) {
      throw "C67V: failed to build sign " + name;
    }
  }

  /* Sample diverse blocks across the map: borders, corners, and interior terrain. */
  function SampleBlocks(reader, side, targetCount) {
    local w = reader.Width();
    local h = reader.Height();
    local nx = (w + side - 1) / side;
    local ny = (h + side - 1) / side;
    local totalBlocks = nx * ny;
    local seen = {};
    local blockList = [];

    // 1. Critical corner blocks (including map borders with invalid tiles)
    local corners = [
      0,
      nx - 1,
      (ny - 1) * nx,
      totalBlocks - 1
    ];
    foreach (cid in corners) {
      if (cid >= 0 && cid < totalBlocks && !(cid in seen)) {
        seen.rawset(cid, true);
        blockList.append(cid);
      }
    }

    // 2. Map border edges
    for (local bx = 1; bx < nx - 1 && blockList.len() < 12; bx += (nx / 4 > 0 ? nx / 4 : 1)) {
      local topEdge = bx;
      local bottomEdge = (ny - 1) * nx + bx;
      if (!(topEdge in seen)) { seen.rawset(topEdge, true); blockList.append(topEdge); }
      if (!(bottomEdge in seen)) { seen.rawset(bottomEdge, true); blockList.append(bottomEdge); }
    }
    for (local by = 1; by < ny - 1 && blockList.len() < 16; by += (ny / 4 > 0 ? ny / 4 : 1)) {
      local leftEdge = by * nx;
      local rightEdge = by * nx + nx - 1;
      if (!(leftEdge in seen)) { seen.rawset(leftEdge, true); blockList.append(leftEdge); }
      if (!(rightEdge in seen)) { seen.rawset(rightEdge, true); blockList.append(rightEdge); }
    }

    // 3. Deterministic pseudo-random interior sampling (canonical C67 trace points)
    for (local i = 0; i < 256 && blockList.len() < targetCount; i++) {
      local px = (i * 97 + 13) % w;
      local py = (i * 193 + 29) % h;
      local bid = (py / side) * nx + (px / side);
      if (bid >= 0 && bid < totalBlocks && !(bid in seen)) {
        seen.rawset(bid, true);
        blockList.append(bid);
      }
    }

    return blockList;
  }

  function RunSide(reader, side, targetCount) {
    local blockIds = this.SampleBlocks(reader, side, targetCount);
    local errorCount = 0;
    local refOpsTotal = 0;
    local valOpsTotal = 0;
    local maxSingleCall = 0;
    local maxBlockOps = 0;
    local tested = 0;

    AILog.Info("C67V_START side=" + side + " target_blocks=" + blockIds.len());

    foreach (bid in blockIds) {
      local refResult = reader.ReadBlockReference(bid, side);
      local valResult = reader.ReadBlockInstrumented(bid, side);

      local diffs = reader.CompareSummaries(refResult.summary, valResult.summary);
      if (diffs.len() > 0) {
        errorCount++;
        AILog.Error("C67V_MISMATCH side=" + side + " block=" + bid + " count=" + diffs.len() + " detail=" + diffs[0]);
      }

      refOpsTotal += refResult.telemetry.ops_total;
      valOpsTotal += valResult.telemetry.ops_total;

      if (valResult.telemetry.max_single_call > maxSingleCall) {
        maxSingleCall = valResult.telemetry.max_single_call;
      }
      if (valResult.telemetry.ops_total > maxBlockOps) {
        maxBlockOps = valResult.telemetry.ops_total;
      }

      tested++;
    }

    local refMean = tested > 0 ? refOpsTotal / tested : 0;
    local valMean = tested > 0 ? valOpsTotal / tested : 0;
    local savingPct = refOpsTotal > 0 ? ((refOpsTotal - valOpsTotal) * 100) / refOpsTotal : 0;

    AILog.Info("C67V_SUMMARY side=" + side + " blocks=" + tested + " errors=" + errorCount
               + " ref_total=" + refOpsTotal + " val_total=" + valOpsTotal
               + " ref_mean=" + refMean + " val_mean=" + valMean
               + " max_single=" + maxSingleCall + " max_block=" + maxBlockOps
               + " saving_pct=" + savingPct);

    // Telemetry signs (< 31 characters each)
    this.Emit("C67V|S" + side + "|BLOCKS|" + tested);
    this.Emit("C67V|S" + side + "|ERR|" + errorCount);
    this.Emit("C67V|S" + side + "|REF|" + refMean);
    this.Emit("C67V|S" + side + "|VAL|" + valMean);
    this.Emit("C67V|S" + side + "|MAX|" + maxSingleCall);
    this.Emit("C67V|S" + side + "|BMAX|" + maxBlockOps);
    this.Emit("C67V|S" + side + "|PCT|" + savingPct);

    return {
      side = side,
      tested = tested,
      errors = errorCount,
      ref_total = refOpsTotal,
      val_total = valOpsTotal,
      ref_mean = refMean,
      val_mean = valMean,
      max_single_call = maxSingleCall,
      max_block_ops = maxBlockOps,
      saving_pct = savingPct
    };
  }

  function Start() {
    local targetBlocks = AIController.GetSetting("blocks");
    if (targetBlocks <= 0) targetBlocks = 64;

    this.Emit("C67V|META|W|" + AIMap.GetMapSizeX());
    this.Emit("C67V|META|H|" + AIMap.GetMapSizeY());

    local reader = OpexTerrainValuateReader();

    local res5 = this.RunSide(reader, 5, targetBlocks);
    local res10 = this.RunSide(reader, 10, targetBlocks);

    if (res5.errors == 0 && res10.errors == 0) {
      this.Emit("C67V|PASS");
      AILog.Info("C67V_ALL_PASS");
    } else {
      AILog.Error("C67V_FAIL errors_s5=" + res5.errors + " errors_s10=" + res10.errors);
      throw "C67V: verification failed due to summary mismatches";
    }

    // Keep the company alive for harness observation
    while (true) AIController.Sleep(1);
  }
}
