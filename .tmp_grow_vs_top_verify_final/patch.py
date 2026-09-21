from pathlib import Path
import re
g=Path("ai/OpexAI/globals_pre.nut")
s=g.read_text(encoding="utf-8")
needle='  lifecycleGrowAttempted = 0,\n'
insert='''  lifecycleGrowAttempted = 0,
  growVsTopCount = 0,
  growVsTopGrowProfit = 0, growVsTopGrowCap = 0,
  growVsTopGrowCharge = 0, growVsTopGrowScore = 0,
  growVsTopTopProfit = 0, growVsTopTopCap = 0,
  growVsTopTopCharge = 0, growVsTopTopScore = 0,
  growVsTopLambdaBps = 0, growVsTopTopAir = 0, growVsTopTopFleet = 0,
'''
assert needle in s
g.write_text(s.replace(needle,insert,1),encoding="utf-8",newline="\n")
p=Path("ai/OpexAI/projects.nut")
s=p.read_text(encoding="utf-8")
needle='''  if (AIR_CAPITAL_FRONTIER_PROBE && best.len() > 0 && best[0].mode == "fleet"
      && ("payload" in best[0]) && best[0].payload != null
      && ("frontierStepKind" in best[0].payload)
      && best[0].payload.frontierStepKind == "grow")
    AIR_CAPITAL_FRONTIER_LEDGER.lifecycleGrowTop++;
  return { best = best, financeable = candidates.len() };
'''
insert='''  if (AIR_CAPITAL_FRONTIER_PROBE && best.len() > 0) {
    local bestGrow = null;
    foreach (project in candidates) {
      if (project == null || project.mode != "fleet"
          || !("payload" in project) || project.payload == null
          || !("frontierStepKind" in project.payload)
          || project.payload.frontierStepKind != "grow") continue;
      if (bestGrow == null || project.frontierScoreInt > bestGrow.frontierScoreInt)
        bestGrow = project;
    }
    if (bestGrow != null && bestGrow != best[0]) {
      local top = best[0];
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopCount++;
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowProfit += OpexCapitalFrontierProjectProfit(bestGrow);
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowCap += OpexProjectShadowCapital(bestGrow);
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowCharge += bestGrow.frontierCapitalCharge.tointeger();
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowScore += bestGrow.frontierScore.tointeger();
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopProfit += OpexCapitalFrontierProjectProfit(top);
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopCap += OpexProjectShadowCapital(top);
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopCharge += top.frontierCapitalCharge.tointeger();
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopScore += top.frontierScore.tointeger();
      AIR_CAPITAL_FRONTIER_LEDGER.growVsTopLambdaBps += (bestGrow.frontierCapitalPrice * 10000.0).tointeger();
      if (top.mode == "air") AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopAir++;
      else if (top.mode == "fleet") AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopFleet++;
    }
  }
  if (AIR_CAPITAL_FRONTIER_PROBE && best.len() > 0 && best[0].mode == "fleet"
      && ("payload" in best[0]) && best[0].payload != null
      && ("frontierStepKind" in best[0].payload)
      && best[0].payload.frontierStepKind == "grow")
    AIR_CAPITAL_FRONTIER_LEDGER.lifecycleGrowTop++;
  return { best = best, financeable = candidates.len() };
'''
assert needle in s
p.write_text(s.replace(needle,insert,1),encoding="utf-8",newline="\n")
t=Path("ai/OpexAI/task_air.nut")
s=t.read_text(encoding="utf-8")
pat=re.compile(r'''      OpexSign\(AIMap\.GetTileIndex\(37, 8\), "CF25\|"[\s\S]*?               \+ AIR_SELECTION_LEDGER\.coverStateMismatch\);''')
repl='''      OpexSign(AIMap.GetTileIndex(37, 8), "CF25|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopCount + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowProfit + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowCap + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowCharge);
      OpexSign(AIMap.GetTileIndex(38, 8), "CF26|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopGrowScore + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopProfit + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopCap);
      OpexSign(AIMap.GetTileIndex(39, 8), "CF27|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopCharge + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopScore + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopLambdaBps + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopAir + "|"
               + AIR_CAPITAL_FRONTIER_LEDGER.growVsTopTopFleet + "|0|0|0");'''
s2,n=pat.subn(repl,s,count=1)
assert n==1,n
t.write_text(s2,encoding="utf-8",newline="\n")
print("PATCH_OK")
