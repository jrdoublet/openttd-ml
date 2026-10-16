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
  OpexV211SelfScore(mine.perf);
}

/* Note de performance d'OpenTTD recalculee pour nous seuls, composante par composante
 * (economy.cpp, UpdateCompanyRatingAndValue ; cibles de docs/mecanique_jeu.md section 6). L'API
 * ne rend que le total : on journalise les parties brutes, les points et le total recalcule,
 * a comparer a `perf` (note officielle du trimestre clos). Le jeu calcule la note en fin de
 * trimestre ; on la refait au premier passage du trimestre suivant, d'ou de petits ecarts.
 * La variete de cargo est approchee par les cargos des vehicules ayant rapporte l'an dernier :
 * le jeu compte les types livres au trimestre, que l'API IA n'expose pas. Les gares comptent une
 * fois par type d'installation ; le jeu n'y compte que celles chargees ou dechargees depuis moins
 * de 20 jours (non expose), d'ou une borne haute. */
function OpexV211SelfScore(perf)
{
  local mark = OpexOpsMeasureBegin();
  local self = AICompany.COMPANY_SELF;
  local vehicles = 0, minProfit = null, cargos = {};
  foreach (v, _ in AIVehicleList()) {
    local profit = AIVehicle.GetProfitLastYear(v);
    if (profit > 0) {
      vehicles++;
      cargos[AIEngine.GetCargoType(AIVehicle.GetEngineType(v))] <- true;
    }
    if (AIVehicle.GetAge(v) > 730 && (minProfit == null || profit < minProfit)) minProfit = profit;
  }
  if (minProfit == null) minProfit = 0;
  local stations = 0;
  foreach (st, _ in AIStationList(AIStation.STATION_ANY)) {
    foreach (type in [AIStation.STATION_TRAIN, AIStation.STATION_TRUCK_STOP, AIStation.STATION_BUS_STOP,
                      AIStation.STATION_AIRPORT, AIStation.STATION_DOCK]) {
      if (AIStation.HasStationType(st, type)) stations++;
    }
  }
  /* Trimestres clos disponibles depuis le debut de la partie (12 au plus, 4 pour le livre). */
  local now = AIDate.GetCurrentDate();
  local closed = (AIDate.GetYear(now) - OPEX_START_YEAR) * 4 + (AIDate.GetMonth(now) - 1) / 3;
  local n = closed < 12 ? closed : 12;
  local minIncome = null, maxIncome = null, delivered = 0;
  for (local q = 1; q <= n; q++) {
    local net = AICompany.GetQuarterlyIncome(self, q) + AICompany.GetQuarterlyExpenses(self, q);
    if (minIncome == null || net < minIncome) minIncome = net;
    if (maxIncome == null || net > maxIncome) maxIncome = net;
    if (q <= 4) delivered += AICompany.GetQuarterlyCargoDelivered(self, q);
  }
  if (minIncome == null) minIncome = 0;
  if (maxIncome == null) maxIncome = 0;
  local money = AICompany.GetBankBalance(self);
  local loan = AICompany.GetLoanAmount();
  local nCargo = cargos.len();
  local parts = [
    ["vehicles", vehicles, 120, 100], ["stations", stations, 80, 100],
    ["min_profit", minProfit, 10000, 100], ["min_income", minIncome, 50000, 50],
    ["max_income", maxIncome, 100000, 100], ["delivered", delivered, 40000, 400],
    ["cargo", nCargo, 8, 50], ["money", money, 10000000, 50], ["loan_margin", 250000 - loan, 250000, 50]
  ];
  local fields = "perf=" + perf, total = 0;
  foreach (part in parts) {
    local raw = part[1] < 0 ? 0 : (part[1] > part[2] ? part[2] : part[1]);
    local pts = (raw.tofloat() * part[3] / part[2]).tointeger();
    total += pts;
    fields += " " + part[0] + "=" + part[1] + " pts_" + part[0] + "=" + pts + "/" + part[3];
  }
  OpexDecide("V211_SCORE", fields + " total=" + total + " ops=" + OpexOpsMeasureEnd(mark));
}

/* Les noms de compagnie contiennent des espaces : on les remplace pour garder k=v. */
function OpexV211Word(text)
{
  if (text == null) return "-";
  local out = "";
  foreach (ch in text) out += (ch == ' ' || ch == '=') ? "_" : ch.tochar();
  return out;
}
