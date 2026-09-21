from pathlib import Path

def replace_block(path, old, new):
    p = Path(path)
    data = p.read_bytes()
    nl = b"\r\n" if b"\r\n" in data else b"\n"
    old_b = old.replace("\n", nl.decode()).encode()
    new_b = new.replace("\n", nl.decode()).encode()
    if old_b not in data:
        raise SystemExit(f"target block not found: {path}")
    p.write_bytes(data.replace(old_b, new_b, 1))

replace_block(
    "ai/OpexAI/projects.nut",
    '''    local representative = null;
    local representativeProfit = 0;
    foreach (row in rows) {
      local project = row.project;
      if (project == null
          || (("frontierExactDominated" in project) && project.frontierExactDominated))
        continue;
      local profit = OpexCapitalFrontierProjectProfit(project);
      if (profit <= 0) continue;
      if (representative == null || profit > representativeProfit
          || (profit == representativeProfit && row.capital < representative.capital)) {
        representative = row;
        representativeProfit = profit;
      }
    }
    if (representative == null) continue;
    groupCount++;
    if (representative.financeCap > 0) fullDemand += representative.financeCap;
    if (representative.capital > 0 && sampleCount < sampleMax) {
      local ratioPct = ((representativeProfit.tofloat() * 100.0)
          / representative.capital).tointeger();
      if (ratioPct < 0) ratioPct = 0;
      ratios.AddItem(sampleCount, ratioPct);
      sampleCount++;
    }
''',
    '''    local representative = null;
    local representativeProfit = 0;
    local predecessor = null;
    local predecessorProfit = 0;
    local bucketRepresentative = null;
    local bucketProfit = 0;
    local bucketCapital = null;
    foreach (row in rows) {
      local project = row.project;
      if (project == null
          || (("frontierExactDominated" in project) && project.frontierExactDominated))
        continue;
      local profit = OpexCapitalFrontierProjectProfit(project);
      if (profit <= 0) continue;
      /* rows est deja ordonne par capital dans OpexCapitalFrontierPrepare. Un
       * seul passage suffit donc pour reduire les egalites de capital puis suivre
       * les records de profit. Le record precedent est exactement l'increment
       * marginal qui mene au point de profit maximal du groupe. */
      if (bucketRepresentative != null && row.capital != bucketCapital) {
        if (bucketProfit > representativeProfit) {
          predecessor = representative;
          predecessorProfit = representativeProfit;
          representative = bucketRepresentative;
          representativeProfit = bucketProfit;
        }
        bucketRepresentative = null;
      }
      if (bucketRepresentative == null || profit > bucketProfit) {
        bucketRepresentative = row;
        bucketProfit = profit;
      }
      bucketCapital = row.capital;
    }
    if (bucketRepresentative != null && bucketProfit > representativeProfit) {
      predecessor = representative;
      predecessorProfit = representativeProfit;
      representative = bucketRepresentative;
      representativeProfit = bucketProfit;
    }
    if (representative == null) continue;
    groupCount++;
    if (representative.financeCap > 0) fullDemand += representative.financeCap;
    if (representative.capital > 0 && sampleCount < sampleMax) {
      local priorCapital = predecessor != null ? predecessor.capital : 0;
      local priorProfit = predecessor != null ? predecessorProfit : 0;
      local deltaCapital = representative.capital - priorCapital;
      local deltaProfit = representativeProfit - priorProfit;
      if (deltaCapital > 0 && deltaProfit > 0) {
        local ratioPct = ((deltaProfit.tofloat() * 100.0) / deltaCapital).tointeger();
        if (ratioPct < 0) ratioPct = 0;
        ratios.AddItem(sampleCount, ratioPct);
        sampleCount++;
      }
    }
''')

replace_block(
    "sweeps/test_air_capital_frontier.py",
    '''        self.assertIn("local sampleMax = 32", relaxation)
        self.assertIn("local representative = null", relaxation)
        self.assertIn("representativeProfit", relaxation)
        self.assertIn("ratios.AddItem(sampleCount, ratioPct)", relaxation)
''',
    '''        self.assertIn("local sampleMax = 32", relaxation)
        self.assertIn("local representative = null", relaxation)
        self.assertIn("representativeProfit", relaxation)
        self.assertIn("local predecessor = null", relaxation)
        self.assertIn("local deltaCapital = representative.capital - priorCapital", relaxation)
        self.assertIn("local deltaProfit = representativeProfit - priorProfit", relaxation)
        self.assertIn("(deltaProfit.tofloat() * 100.0) / deltaCapital", relaxation)
        self.assertEqual(relaxation.count("foreach (row in rows)"), 1)
        self.assertNotIn("representativeProfit.tofloat() * 100.0)\\n          / representative.capital", relaxation)
        self.assertIn("ratios.AddItem(sampleCount, ratioPct)", relaxation)
''')
