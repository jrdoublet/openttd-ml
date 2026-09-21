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
    "ai/OpexAI/builder_air.nut",
    '''  /* Tri capital croissant puis profit decroissant : un simple prefix-max suffit
   * ensuite pour retirer exactement les configurations dominees en (capital, profit). */
  choices.sort(function(a, b) {
    if (a.frontierCapital < b.frontierCapital) return -1;
    if (a.frontierCapital > b.frontierCapital) return 1;
    if (a.economics.profitAnnual > b.economics.profitAnnual) return -1;
    if (a.economics.profitAnnual < b.economics.profitAnnual) return 1;
    if (a.plane.id < b.plane.id) return -1;
    if (a.plane.id > b.plane.id) return 1;
    return 0;
  });

  local kept = [];
  local bestProfit = null;
  foreach (choice in choices) {
    if (bestProfit != null && choice.economics.profitAnnual <= bestProfit) continue;
    kept.append(choice);
    bestProfit = choice.economics.profitAnnual;
  }
''',
    '''  /* AIList fait le seul tri necessaire : capital croissant. Les variantes de
   * capital identique sont traitees comme un bucket et reduites au profit maximal
   * avant le prefix-max. Cela reproduit exactement la dominance (capital, profit)
   * sans callback Squirrel O(n log n), ni cle composite susceptible d'overflow. */
  local capitalOrder = AIList();
  for (local i = 0; i < choices.len(); i++)
    capitalOrder.AddItem(i, choices[i].frontierCapital);
  capitalOrder.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING);

  local kept = [];
  local bestProfit = null;
  local bucketChoice = null;
  local bucketCapital = null;
  for (local id = capitalOrder.Begin(); !capitalOrder.IsEnd(); id = capitalOrder.Next()) {
    local choice = choices[id];
    local capital = capitalOrder.GetValue(id);
    if (bucketChoice != null && capital != bucketCapital) {
      local bucketProfit = bucketChoice.economics.profitAnnual;
      if (bestProfit == null || bucketProfit > bestProfit) {
        kept.append(bucketChoice);
        bestProfit = bucketProfit;
      }
      bucketChoice = null;
    }
    if (bucketChoice == null
        || choice.economics.profitAnnual > bucketChoice.economics.profitAnnual
        || (choice.economics.profitAnnual == bucketChoice.economics.profitAnnual
            && choice.plane.id < bucketChoice.plane.id)) {
      bucketChoice = choice;
    }
    bucketCapital = capital;
  }
  if (bucketChoice != null) {
    local bucketProfit = bucketChoice.economics.profitAnnual;
    if (bestProfit == null || bucketProfit > bestProfit) kept.append(bucketChoice);
  }
''')

p = Path("sweeps/test_air_capital_frontier.py")
s = p.read_text(encoding="utf-8")
old = '''        self.assertIn("function OpexAirEquipmentFrontier", src)
        self.assertIn("frontierCapital = economics.capital + economics.immobilise", src)
        self.assertIn("choice.economics.profitAnnual <= bestProfit", src)
        self.assertNotIn("sqrt(", src[src.index("function OpexAirEquipmentFrontier"):src.index("function OpexAirRouteChoices")])
'''
new = '''        self.assertIn("function OpexAirEquipmentFrontier", src)
        self.assertIn("frontierCapital = economics.capital + economics.immobilise", src)
        frontier = src[src.index("function OpexAirEquipmentFrontier"):src.index("function OpexAirRouteChoices")]
        self.assertIn("local capitalOrder = AIList()", frontier)
        self.assertIn("capitalOrder.AddItem(i, choices[i].frontierCapital)", frontier)
        self.assertIn("capitalOrder.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING)", frontier)
        self.assertIn("bucketProfit > bestProfit", frontier)
        self.assertNotIn("choices.sort(function", frontier)
        self.assertNotIn("sqrt(", frontier)
'''
if old not in s:
    raise SystemExit("target test block not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
