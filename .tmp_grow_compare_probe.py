from pathlib import Path

# globals
p = Path("ai/OpexAI/globals_pre.nut")
s = p.read_text(encoding="utf-8")
anchor = "  lifecycleGrowAttempted = 0,\n"
block = """  lifecycleGrowAttempted = 0,
  /* TEMP_GROW_COMPARE_BEGIN */
  growCompareSamples = 0, growCompareTopAir = 0,
  growCompareGrowProfit = 0, growCompareGrowCapital = 0, growCompareGrowScore = 0,
  growCompareTopProfit = 0, growCompareTopCapital = 0, growCompareTopScore = 0,
  /* TEMP_GROW_COMPARE_END */
"""
assert "TEMP_GROW_COMPARE_BEGIN" not in s
assert anchor in s
p.write_text(s.replace(anchor, block, 1), encoding="utf-8")

# projects
p = Path("ai/OpexAI/projects.nut")
s = p.read_text(encoding="utf-8")
anchor = """  order.Sort(AIList.SORT_BY_VALUE, false);

  local best = [];
"""
block = """  order.Sort(AIList.SORT_BY_VALUE, false);

  /* TEMP_GROW_COMPARE_BEGIN: passive diagnostic only. */
  if (AIR_CAPITAL_FRONTIER_PROBE && candidates.len() > 0) {
    local compareGrow = null;
    foreach (candidate in candidates) {
      if (candidate == null || !("mode" in candidate) || candidate.mode != "fleet"
          || !("payload" in candidate) || candidate.payload == null
          || !("frontierStepKind" in candidate.payload)
          || candidate.payload.frontierStepKind != "grow") continue;
      if (compareGrow == null || candidate.frontierScoreInt > compareGrow.frontierScoreInt)
        compareGrow = candidate;
    }
    if (compareGrow != null) {
      local compareTopId = order.Begin();
      if (!order.IsEnd()) {
        local compareTop = candidates[compareTopId];
        if (compareTop != null && compareTop != compareGrow) {
          AIR_CAPITAL_FRONTIER_LEDGER.growCompareSamples++;
          if (("mode" in compareTop) && compareTop.mode == "air")
            AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopAir++;
          AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowProfit += OpexCapitalFrontierProjectProfit(compareGrow);
          AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowCapital += OpexProjectShadowCapital(compareGrow);
          AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowScore += compareGrow.frontierScoreInt;
          AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopProfit += OpexCapitalFrontierProjectProfit(compareTop);
          AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopCapital += OpexProjectShadowCapital(compareTop);
          AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopScore += compareTop.frontierScoreInt;
        }
      }
    }
  }
  /* TEMP_GROW_COMPARE_END */

  local best = [];
"""
assert "TEMP_GROW_COMPARE_BEGIN" not in s
assert anchor in s
p.write_text(s.replace(anchor, block, 1), encoding="utf-8")

# task_air
p = Path("ai/OpexAI/task_air.nut")
s = p.read_text(encoding="utf-8")
start = s.index('      OpexSign(AIMap.GetTileIndex(37, 8), "CF25|"')
end = s.index('    }', start)
old = s[start:end]
Path("results/_tmp_grow_compare_task_air_block.txt").write_text(old, encoding="utf-8")
new = """      /* TEMP_GROW_COMPARE_BEGIN: repurpose CF25..27 for one diagnostic run. */
      OpexSign(AIMap.GetTileIndex(37, 8), "CF25|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growCompareSamples + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopAir + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowProfit / 1000) + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowCapital / 1000));
      OpexSign(AIMap.GetTileIndex(38, 8), "CF26|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareGrowScore / 1000) + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopProfit / 1000) + "|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopCapital / 1000));
      OpexSign(AIMap.GetTileIndex(39, 8), "CF27|"
               + (AIR_CAPITAL_FRONTIER_LEDGER.growCompareTopScore / 1000) + "|0|"
               + AIR_SELECTION_LEDGER.coverMissing + "|" + AIR_SELECTION_LEDGER.coverBudgetBelow + "|"
               + AIR_SELECTION_LEDGER.coverBudgetAbove + "|"
               + AIR_SELECTION_LEDGER.coverRawStateMismatch + "|"
               + AIR_SELECTION_LEDGER.coverSemanticHits + "|"
               + AIR_SELECTION_LEDGER.coverStateMismatch);
      /* TEMP_GROW_COMPARE_END */
"""
p.write_text(s[:start] + new + s[end:], encoding="utf-8")
print("patched")

