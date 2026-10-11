/* C67: terrain summary reader using native NoAI AITileList / Valuate.
 * Reconstructible, isolated, no economic consumer. budget.nut must be loaded first.
 * Contract: docs/c67_cartographie_contrat.md.
 */

const OPEX_TERRAIN_VALUATE_VERSION = 1;

class OpexTerrainValuateReader {
  _source = null;
  _width = 0;
  _height = 0;

  constructor(source = null) {
    this._source = source == null ? OpexTerrainSource() : source;
    this._width = this._source.Width();
    this._height = this._source.Height();
  }

  function Width() { return this._width; }
  function Height() { return this._height; }

  /* Geometric bounds of block id for side S (5 or 10). */
  function BlockBounds(id, side) {
    local nx = (this._width + side - 1) / side;
    local bx = id % nx;
    local by = id / nx;
    local x0 = bx * side;
    local y0 = by * side;
    local x1 = x0 + side < this._width ? x0 + side : this._width;
    local y1 = y0 + side < this._height ? y0 + side : this._height;
    return {
      x0 = x0,
      y0 = y0,
      x1 = x1,
      y1 = y1,
      w = x1 - x0,
      h = y1 - y0,
      total_tiles = (x1 - x0) * (y1 - y0)
    };
  }

  /* Valid interior range clamped to map borders (1 <= x < mapW - 1, 1 <= y < mapH - 1). */
  function ValidBounds(bounds) {
    local vx0 = bounds.x0 < 1 ? 1 : bounds.x0;
    local vy0 = bounds.y0 < 1 ? 1 : bounds.y0;
    local vx1 = bounds.x1 > this._width - 1 ? this._width - 1 : bounds.x1;
    local vy1 = bounds.y1 > this._height - 1 ? this._height - 1 : bounds.y1;
    return {
      x0 = vx0,
      y0 = vy0,
      x1 = vx1,
      y1 = vy1,
      valid = (vx0 < vx1 && vy0 < vy1)
    };
  }

  /* High-performance read without per-call telemetry overhead. */
  function ReadBlock(id, side) {
    local b = this.BlockBounds(id, side);
    local vb = this.ValidBounds(b);

    if (!vb.valid) {
      return {
        schema_version = 1,
        block_id = id,
        generation = 1,
        sample_count = 0,
        invalid_count = b.total_tiles,
        water_count = 0,
        coast_count = 0,
        flat_count = 0,
        buildable_count = 0,
        height_min = null,
        height_max = null,
        height_min_sum = 0,
        first_sample_tick = this._source.Tick(),
        last_sample_tick = this._source.Tick(),
        dynamic_sample_tick = this._source.Tick(),
        water_ratio = null,
        flat_ratio = null,
        buildable_ratio = null,
        mean_tile_min_height = null,
        relief = null
      };
    }

    local tickNow = this._source.Tick();
    local tiles = AITileList();
    tiles.AddRectangle(AIMap.GetTileIndex(vb.x0, vb.y0), AIMap.GetTileIndex(vb.x1 - 1, vb.y1 - 1));
    local sample_count = tiles.Count();
    local invalid_count = b.total_tiles - sample_count;

    if (sample_count == 0) {
      return {
        schema_version = 1,
        block_id = id,
        generation = 1,
        sample_count = 0,
        invalid_count = b.total_tiles,
        water_count = 0,
        coast_count = 0,
        flat_count = 0,
        buildable_count = 0,
        height_min = null,
        height_max = null,
        height_min_sum = 0,
        first_sample_tick = tickNow,
        last_sample_tick = tickNow,
        dynamic_sample_tick = tickNow,
        water_ratio = null,
        flat_ratio = null,
        buildable_ratio = null,
        mean_tile_min_height = null,
        relief = null
      };
    }

    local work = AIList();

    work.AddList(tiles);
    work.Valuate(AITile.IsWaterTile);
    work.KeepValue(1);
    local water_count = work.Count();

    work.Clear();
    work.AddList(tiles);
    work.Valuate(AITile.IsCoastTile);
    work.KeepValue(1);
    local coast_count = work.Count();

    work.Clear();
    work.AddList(tiles);
    work.Valuate(AITile.IsBuildable);
    work.KeepValue(1);
    local buildable_count = work.Count();

    work.Clear();
    work.AddList(tiles);
    work.Valuate(AITile.GetSlope);
    work.KeepValue(AITile.SLOPE_FLAT);
    local flat_count = work.Count();

    work.Clear();
    work.AddList(tiles);
    work.Valuate(AITile.GetMinHeight);
    work.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
    local height_min = work.GetValue(work.Begin());
    local height_min_sum = 0;
    foreach (tileIndex, h in work) {
      height_min_sum += h;
    }

    work.Clear();
    work.AddList(tiles);
    work.Valuate(AITile.GetMaxHeight);
    work.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
    local height_max = work.GetValue(work.Begin());

    return {
      schema_version = 1,
      block_id = id,
      generation = 1,
      sample_count = sample_count,
      invalid_count = invalid_count,
      water_count = water_count,
      coast_count = coast_count,
      flat_count = flat_count,
      buildable_count = buildable_count,
      height_min = height_min,
      height_max = height_max,
      height_min_sum = height_min_sum,
      first_sample_tick = tickNow,
      last_sample_tick = tickNow,
      dynamic_sample_tick = tickNow,
      water_ratio = water_count.tofloat() / sample_count,
      flat_ratio = flat_count.tofloat() / sample_count,
      buildable_ratio = buildable_count.tofloat() / sample_count,
      mean_tile_min_height = height_min_sum.tofloat() / sample_count,
      relief = height_max - height_min
    };
  }

  /* Instrumented read measuring every non-suspendable atomic step. */
  function ReadBlockInstrumented(id, side) {
    local b = this.BlockBounds(id, side);
    local vb = this.ValidBounds(b);
    local maxCallOps = 0;
    local callDetails = {};
    local callCount = 0;

    if (!vb.valid) {
      return {
        summary = {
          schema_version = 1,
          block_id = id,
          generation = 1,
          sample_count = 0,
          invalid_count = b.total_tiles,
          water_count = 0,
          coast_count = 0,
          flat_count = 0,
          buildable_count = 0,
          height_min = null,
          height_max = null,
          height_min_sum = 0,
          first_sample_tick = this._source.Tick(),
          last_sample_tick = this._source.Tick(),
          dynamic_sample_tick = this._source.Tick(),
          water_ratio = null,
          flat_ratio = null,
          buildable_ratio = null,
          mean_tile_min_height = null,
          relief = null
        },
        telemetry = {
          ops_total = 0,
          max_single_call = 0,
          call_count = 0,
          calls = {}
        }
      };
    }

    local tickStart = this._source.Tick();
    local overallMark = this._source.Mark();

    // 1. AddRectangle
    local mark0 = this._source.Mark();
    local tiles = AITileList();
    tiles.AddRectangle(AIMap.GetTileIndex(vb.x0, vb.y0), AIMap.GetTileIndex(vb.x1 - 1, vb.y1 - 1));
    local opsAdd = this._source.Spent(mark0);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == mark0.tick && opsAdd > maxCallOps) maxCallOps = opsAdd;
    callCount++;
    callDetails.rawset("add_rectangle", opsAdd);

    local sample_count = tiles.Count();
    local invalid_count = b.total_tiles - sample_count;

    if (sample_count == 0) {
      local totalEmptyOps = this._source.Spent(overallMark);
      return {
        summary = {
          schema_version = 1,
          block_id = id,
          generation = 1,
          sample_count = 0,
          invalid_count = b.total_tiles,
          water_count = 0,
          coast_count = 0,
          flat_count = 0,
          buildable_count = 0,
          height_min = null,
          height_max = null,
          height_min_sum = 0,
          first_sample_tick = tickStart,
          last_sample_tick = tickStart,
          dynamic_sample_tick = tickStart,
          water_ratio = null,
          flat_ratio = null,
          buildable_ratio = null,
          mean_tile_min_height = null,
          relief = null
        },
        telemetry = {
          ops_total = totalEmptyOps,
          max_single_call = maxCallOps,
          call_count = callCount,
          calls = callDetails
        }
      };
    }

    local work = AIList();

    // 2. Water
    local mark1 = this._source.Mark();
    work.AddList(tiles);
    local markVal1 = this._source.Mark();
    work.Valuate(AITile.IsWaterTile);
    local opsVal1 = this._source.Spent(markVal1);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markVal1.tick && opsVal1 > maxCallOps) maxCallOps = opsVal1;
    callDetails.rawset("val_water", opsVal1);
    callCount++;

    work.KeepValue(1);
    local water_count = work.Count();
    local opsWater = this._source.Spent(mark1);
    callDetails.rawset("step_water", opsWater);

    // 3. Coast
    local mark2 = this._source.Mark();
    work.Clear();
    work.AddList(tiles);
    local markVal2 = this._source.Mark();
    work.Valuate(AITile.IsCoastTile);
    local opsVal2 = this._source.Spent(markVal2);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markVal2.tick && opsVal2 > maxCallOps) maxCallOps = opsVal2;
    callDetails.rawset("val_coast", opsVal2);
    callCount++;

    work.KeepValue(1);
    local coast_count = work.Count();
    local opsCoast = this._source.Spent(mark2);
    callDetails.rawset("step_coast", opsCoast);

    // 4. Buildable
    local mark3 = this._source.Mark();
    work.Clear();
    work.AddList(tiles);
    local markVal3 = this._source.Mark();
    work.Valuate(AITile.IsBuildable);
    local opsVal3 = this._source.Spent(markVal3);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markVal3.tick && opsVal3 > maxCallOps) maxCallOps = opsVal3;
    callDetails.rawset("val_buildable", opsVal3);
    callCount++;

    work.KeepValue(1);
    local buildable_count = work.Count();
    local opsBuildable = this._source.Spent(mark3);
    callDetails.rawset("step_buildable", opsBuildable);

    // 5. Flat
    local mark4 = this._source.Mark();
    work.Clear();
    work.AddList(tiles);
    local markVal4 = this._source.Mark();
    work.Valuate(AITile.GetSlope);
    local opsVal4 = this._source.Spent(markVal4);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markVal4.tick && opsVal4 > maxCallOps) maxCallOps = opsVal4;
    callDetails.rawset("val_slope", opsVal4);
    callCount++;

    work.KeepValue(AITile.SLOPE_FLAT);
    local flat_count = work.Count();
    local opsFlat = this._source.Spent(mark4);
    callDetails.rawset("step_flat", opsFlat);

    // 6. Min height & sum
    local mark5 = this._source.Mark();
    work.Clear();
    work.AddList(tiles);
    local markVal5 = this._source.Mark();
    work.Valuate(AITile.GetMinHeight);
    local opsVal5 = this._source.Spent(markVal5);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markVal5.tick && opsVal5 > maxCallOps) maxCallOps = opsVal5;
    callDetails.rawset("val_min_h", opsVal5);
    callCount++;

    local markSort5 = this._source.Mark();
    work.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
    local opsSort5 = this._source.Spent(markSort5);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markSort5.tick && opsSort5 > maxCallOps) maxCallOps = opsSort5;
    callDetails.rawset("sort_min_h", opsSort5);
    callCount++;

    local height_min = work.GetValue(work.Begin());
    local height_min_sum = 0;
    foreach (tileIndex, h in work) {
      height_min_sum += h;
    }
    local opsMinH = this._source.Spent(mark5);
    callDetails.rawset("step_min_height", opsMinH);

    // 7. Max height
    local mark6 = this._source.Mark();
    work.Clear();
    work.AddList(tiles);
    local markVal6 = this._source.Mark();
    work.Valuate(AITile.GetMaxHeight);
    local opsVal6 = this._source.Spent(markVal6);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markVal6.tick && opsVal6 > maxCallOps) maxCallOps = opsVal6;
    callDetails.rawset("val_max_h", opsVal6);
    callCount++;

    local markSort6 = this._source.Mark();
    work.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
    local opsSort6 = this._source.Spent(markSort6);
    /* Hors frontiere de tick seulement : OpexOpsMeasureEnd ajoute un tick entier sinon. */
    if (AIController.GetTick() == markSort6.tick && opsSort6 > maxCallOps) maxCallOps = opsSort6;
    callDetails.rawset("sort_max_h", opsSort6);
    callCount++;

    local height_max = work.GetValue(work.Begin());
    local opsMaxH = this._source.Spent(mark6);
    callDetails.rawset("step_max_height", opsMaxH);

    local totalOps = this._source.Spent(overallMark);
    local tickEnd = this._source.Tick();

    local summary = {
      schema_version = 1,
      block_id = id,
      generation = 1,
      sample_count = sample_count,
      invalid_count = invalid_count,
      water_count = water_count,
      coast_count = coast_count,
      flat_count = flat_count,
      buildable_count = buildable_count,
      height_min = height_min,
      height_max = height_max,
      height_min_sum = height_min_sum,
      first_sample_tick = tickStart,
      last_sample_tick = tickEnd,
      dynamic_sample_tick = tickEnd,
      water_ratio = water_count.tofloat() / sample_count,
      flat_ratio = flat_count.tofloat() / sample_count,
      buildable_ratio = buildable_count.tofloat() / sample_count,
      mean_tile_min_height = height_min_sum.tofloat() / sample_count,
      relief = height_max - height_min
    };

    return {
      summary = summary,
      telemetry = {
        ops_total = totalOps,
        max_single_call = maxCallOps,
        call_count = callCount,
        calls = callDetails
      }
    };
  }

  /* Reference tile-by-tile reader (matching OpexTerrainMap logic). */
  function ReadBlockReference(id, side) {
    local b = this.BlockBounds(id, side);
    local tickStart = this._source.Tick();
    local mark = this._source.Mark();
    local sample_count = 0;
    local invalid_count = 0;
    local water_count = 0;
    local coast_count = 0;
    local flat_count = 0;
    local buildable_count = 0;
    local height_min = null;
    local height_max = null;
    local height_min_sum = 0;
    local maxTileOps = 0;

    for (local y = b.y0; y < b.y1; y++) {
      for (local x = b.x0; x < b.x1; x++) {
        local tMark = this._source.Mark();
        local t = this._source.Read(x, y);
        local tCost = this._source.Spent(tMark);
        if (tCost > maxTileOps) maxTileOps = tCost;
        if (t == null) {
          invalid_count++;
          continue;
        }
        sample_count++;
        if (t.water) water_count++;
        if (t.coast) coast_count++;
        if (t.flat) flat_count++;
        if (t.buildable) buildable_count++;
        height_min = height_min == null ? t.lo : (t.lo < height_min ? t.lo : height_min);
        height_max = height_max == null ? t.hi : (t.hi > height_max ? t.hi : height_max);
        height_min_sum += t.lo;
      }
    }

    local totalOps = this._source.Spent(mark);
    local tickEnd = this._source.Tick();

    local summary = {
      schema_version = 1,
      block_id = id,
      generation = 1,
      sample_count = sample_count,
      invalid_count = invalid_count,
      water_count = water_count,
      coast_count = coast_count,
      flat_count = flat_count,
      buildable_count = buildable_count,
      height_min = height_min,
      height_max = height_max,
      height_min_sum = height_min_sum,
      first_sample_tick = tickStart,
      last_sample_tick = tickEnd,
      dynamic_sample_tick = tickEnd,
      water_ratio = sample_count == 0 ? null : water_count.tofloat() / sample_count,
      flat_ratio = sample_count == 0 ? null : flat_count.tofloat() / sample_count,
      buildable_ratio = sample_count == 0 ? null : buildable_count.tofloat() / sample_count,
      mean_tile_min_height = sample_count == 0 ? null : height_min_sum.tofloat() / sample_count,
      relief = sample_count == 0 ? null : height_max - height_min
    };

    return {
      summary = summary,
      telemetry = {
        ops_total = totalOps,
        max_tile_ops = maxTileOps
      }
    };
  }

  /* Compares reference summary with Valuate summary. Returns array of mismatch descriptions. */
  function CompareSummaries(refSummary, valSummary) {
    local diffs = [];
    local intFields = [
      "schema_version", "block_id", "sample_count", "invalid_count",
      "water_count", "coast_count", "flat_count", "buildable_count",
      "height_min", "height_max", "height_min_sum", "relief"
    ];
    foreach (field in intFields) {
      if (refSummary[field] != valSummary[field]) {
        diffs.append(field + ": ref=" + refSummary[field] + " val=" + valSummary[field]);
      }
    }

    local floatFields = ["water_ratio", "flat_ratio", "buildable_ratio", "mean_tile_min_height"];
    foreach (field in floatFields) {
      local rVal = refSummary[field];
      local vVal = valSummary[field];
      if (rVal == null && vVal == null) continue;
      if (rVal == null || vVal == null) {
        diffs.append(field + ": nullness mismatch ref=" + rVal + " val=" + vVal);
      } else {
        local delta = rVal - vVal;
        if (delta < 0) delta = -delta;
        if (delta > 0.00001) {
          diffs.append(field + ": diff=" + delta + " ref=" + rVal + " val=" + vVal);
        }
      }
    }
    return diffs;
  }
}
