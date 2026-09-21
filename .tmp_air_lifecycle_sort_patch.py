from pathlib import Path
p = Path("ai/OpexAI/builder_air.nut")
s = p.read_text(encoding="utf-8")
old = '''  /* Domination sur le prochain pas uniquement. En cas de pas identique, garder
   * d'abord la cible finale au profit le plus eleve : l'action immediate est la
   * meme et sera de toute facon re-evaluee juste apres son execution. */
  options.sort(function(a, b) {
    if (a.transactionCapital < b.transactionCapital) return -1;
    if (a.transactionCapital > b.transactionCapital) return 1;
    if (a.marginalGainAnnual > b.marginalGainAnnual) return -1;
    if (a.marginalGainAnnual < b.marginalGainAnnual) return 1;
    if (a.targetProfitAnnual > b.targetProfitAnnual) return -1;
    if (a.targetProfitAnnual < b.targetProfitAnnual) return 1;
    if (a.targetEngine < b.targetEngine) return -1;
    if (a.targetEngine > b.targetEngine) return 1;
    return a.targetFleetSize - b.targetFleetSize;
  });
  local kept = [];
  local bestGain = null;
  foreach (option in options) {
    if (bestGain != null && option.marginalGainAnnual <= bestGain) continue;
    kept.append(option);
    bestGain = option.marginalGainAnnual;
  }
'''
new = '''  /* Domination sur le prochain pas uniquement. AIList trie le capital natif ;
   * les egalites de capital sont reduites localement au meilleur gain marginal,
   * puis au meme tie-break historique sur la cible finale. */
  local optionOrder = AIList();
  for (local i = 0; i < options.len(); i++)
    optionOrder.AddItem(i, options[i].transactionCapital);
  optionOrder.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);
  local kept = [];
  local bestGain = null;
  local bucketOption = null;
  local bucketCapital = null;
  for (local id = optionOrder.Begin(); !optionOrder.IsEnd(); id = optionOrder.Next()) {
    local option = options[id];
    local capital = optionOrder.GetValue(id);
    if (bucketOption != null && capital != bucketCapital) {
      local bucketGain = bucketOption.marginalGainAnnual;
      if (bestGain == null || bucketGain > bestGain) {
        kept.append(bucketOption);
        bestGain = bucketGain;
      }
      bucketOption = null;
    }
    if (bucketOption == null
        || option.marginalGainAnnual > bucketOption.marginalGainAnnual
        || (option.marginalGainAnnual == bucketOption.marginalGainAnnual
            && (option.targetProfitAnnual > bucketOption.targetProfitAnnual
                || (option.targetProfitAnnual == bucketOption.targetProfitAnnual
                    && (option.targetEngine < bucketOption.targetEngine
                        || (option.targetEngine == bucketOption.targetEngine
                            && option.targetFleetSize < bucketOption.targetFleetSize)))))) {
      bucketOption = option;
    }
    bucketCapital = capital;
  }
  if (bucketOption != null) {
    local bucketGain = bucketOption.marginalGainAnnual;
    if (bestGain == null || bucketGain > bestGain) kept.append(bucketOption);
  }
'''
if old not in s: raise SystemExit("builder lifecycle block not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")

p = Path("sweeps/test_air_capital_frontier.py")
s = p.read_text(encoding="utf-8")
old = '''        self.assertIn("option.targetProfitAnnual > prior.targetProfitAnnual", frontier)
        self.assertLess(frontier.index("foreach (actionKey, option in byAction)"),
                        frontier.index("options.sort(function(a, b)"))
'''
new = '''        self.assertIn("option.targetProfitAnnual > prior.targetProfitAnnual", frontier)
        self.assertIn("local optionOrder = AIList()", frontier)
        self.assertIn("optionOrder.AddItem(i, options[i].transactionCapital)", frontier)
        self.assertIn("optionOrder.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING)", frontier)
        self.assertNotIn("options.sort(function", frontier)
        self.assertLess(frontier.index("foreach (actionKey, option in byAction)"),
                        frontier.index("local optionOrder = AIList()"))
'''
if old not in s: raise SystemExit("test lifecycle block not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
