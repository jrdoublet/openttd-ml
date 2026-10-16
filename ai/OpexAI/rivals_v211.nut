/* V211 : releve trimestriel des compagnies (nous compris), strictement observatoire.
 * Une ligne V211_RIVAL par compagnie au premier passage de chaque trimestre, puis une ligne
 * V211_RANK avec notre rang. Aucune decision ne lit ces valeurs. Les grandeurs trimestrielles
 * portent sur le trimestre clos (quarter 1) ; la tresorerie est l'instantane rendu par
 * GetBankBalance, dont la valeur pour une autre compagnie est precisement ce qu'on verifie. */

function OpexV211QuarterlyTick()
{
  local now = AIDate.GetCurrentDate();
  local quarter = AIDate.GetYear(now) * 4 + (AIDate.GetMonth(now) - 1) / 3;
  if (quarter == V211_LAST_QUARTER) return;
  /* Premier passage : on arme sans journaliser, le trimestre en cours n'est pas clos. */
  local first = V211_LAST_QUARTER < 0;
  V211_LAST_QUARTER = quarter;
  if (first) return;
  local mark = OpexOpsMeasureBegin();
  local self = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local rows = [];
  for (local c = AICompany.COMPANY_FIRST; c <= AICompany.COMPANY_LAST; c++) {
    if (AICompany.ResolveCompanyID(c) == AICompany.COMPANY_INVALID) continue;
    local row = {
      id = c,
      value = AICompany.GetQuarterlyCompanyValue(c, 1),
      perf = AICompany.GetQuarterlyPerformanceRating(c, 1),
      income = AICompany.GetQuarterlyIncome(c, 1),
      expenses = AICompany.GetQuarterlyExpenses(c, 1),
      delivered = AICompany.GetQuarterlyCargoDelivered(c, 1)
    };
    rows.append(row);
    OpexDecide("V211_RIVAL", "company=" + c + " self=" + (c == self ? 1 : 0)
        + " name=" + OpexV211Word(AICompany.GetName(c))
        + " value=" + row.value + " perf=" + row.perf
        + " income=" + row.income + " expenses=" + row.expenses
        + " profit=" + (row.income + row.expenses) + " delivered=" + row.delivered
        + " bank=" + AICompany.GetBankBalance(c)
        + " rail=" + AIInfrastructure.GetInfrastructurePieceCount(c, AIInfrastructure.INFRASTRUCTURE_RAIL)
        + " road=" + AIInfrastructure.GetInfrastructurePieceCount(c, AIInfrastructure.INFRASTRUCTURE_ROAD)
        + " stations=" + AIInfrastructure.GetInfrastructurePieceCount(c, AIInfrastructure.INFRASTRUCTURE_STATION)
        + " airports=" + AIInfrastructure.GetInfrastructurePieceCount(c, AIInfrastructure.INFRASTRUCTURE_AIRPORT)
        + " canals=" + AIInfrastructure.GetInfrastructurePieceCount(c, AIInfrastructure.INFRASTRUCTURE_CANAL));
  }
  local rankValue = 1, rankPerf = 1, rankProfit = 1, mine = null;
  foreach (row in rows) if (row.id == self) mine = row;
  if (mine == null) return;
  foreach (row in rows) {
    if (row.id == self) continue;
    if (row.value > mine.value) rankValue++;
    if (row.perf > mine.perf) rankPerf++;
    if (row.income + row.expenses > mine.income + mine.expenses) rankProfit++;
  }
  OpexDecide("V211_RANK", "companies=" + rows.len() + " rank_value=" + rankValue
      + " rank_perf=" + rankPerf + " rank_profit=" + rankProfit
      + " ops=" + OpexOpsMeasureEnd(mark));
}

/* Les noms de compagnie contiennent des espaces : on les remplace pour garder k=v. */
function OpexV211Word(text)
{
  if (text == null) return "-";
  local out = "";
  foreach (ch in text) out += (ch == ' ' || ch == '=') ? "_" : ch.tochar();
  return out;
}
