/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexCashReserve()
{
  local cashMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
  if (!DYNAMIC_CASH_RESERVE) {
    if (!OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {
      if (cashMark != null) OpexSpanAgg("pub.cash", cashMark);
      return CASH_RESERVE_STATIC;
    }
  }
  local totalRunning = 0;
  local vehicles = AIVehicleList();
  vehicles.Valuate(AIVehicle.GetRunningCost);
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    totalRunning += vehicles.GetValue(v);
  }
  local reserve;
  local quarterlyBuffer = totalRunning / 4;
  if (CASH_RESERVE_PROBE) CASH_RESERVE_PROBE_CALLS++;
  if (quarterlyBuffer < CASH_RESERVE_MIN) {
    reserve = CASH_RESERVE_MIN;
    if (CASH_RESERVE_PROBE) CASH_RESERVE_PROBE_MIN_BINDS++;
  } else if (quarterlyBuffer > CASH_RESERVE_MAX) {
    reserve = CASH_RESERVE_MAX;
    if (CASH_RESERVE_PROBE) CASH_RESERVE_PROBE_MAX_BINDS++;
  } else reserve = quarterlyBuffer;
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
  if (cashMark != null) OpexSpanAgg("pub.cash", cashMark);
  return reserve;
}
/* Capital effectivement mobilisable par le portefeuille. Cette valeur doit toujours etre relue
 * apres une depense : la caisse, le reliquat d'emprunt et la reserve peuvent tous avoir change.
 * Centraliser la formule evite que la future passe dynamique (C38) ne diverge de la generation,
 * du rafraichissement ou du cache incremental. */
function OpexAvailableCapital()
{
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local borrowable = OPEX_ECONOMY_OPCODE_COMPAT_FALSE
      ? AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount() : 0;
  if (borrowable < 0) borrowable = 0;
  local available = cash + borrowable - OpexCashReserve();
  if (V88_STEP2_CASH_RESERVE) available -= V88_STEP2_RESERVE_AMOUNT;
  return available > 0 ? available : 0;
}
/* Remboursement annuel : une fois la tresorerie confortablement au-dessus du plancher, on
 * rembourse le maximum d'emprunt qui laisse encore ce plancher disponible pour l'annee
 * suivante. SetLoanAmount exige un multiple de GetLoanInterval() ; on arrondit donc le nouvel
 * emprunt VERS LE HAUT (jamais vers le bas, ce qui rembourserait plus que permis et pourrait
 * passer sous le plancher). */
function OpexAI::_tryRepayLoan(year)
{
  local loan = AICompany.GetLoanAmount();
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  OpexSign(AIMap.GetTileIndex(1, 1), "LF|" + (year % 100) + "|" + cash + "|" + loan);
  if (loan <= 0) {
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=none reason=no_loan cash=" + cash + " floor=" + LOAN_REPAY_FLOOR);
    }
    return;
  }

  if (cash <= LOAN_REPAY_FLOOR) {
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=refuse_repay reason=cash_below_floor cash=" + cash + " floor=" + LOAN_REPAY_FLOOR + " loan=" + loan);
    }
    return;
  }

  local interval = AICompany.GetLoanInterval();
  local minNewLoan = loan - (cash - LOAN_REPAY_FLOOR);
  if (minNewLoan < 0) minNewLoan = 0;
  local newLoan = ((minNewLoan + interval - 1) / interval) * interval;
  if (newLoan >= loan) {
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=refuse_repay reason=less_than_interval cash=" + cash + " floor=" + LOAN_REPAY_FLOOR + " loan=" + loan + " interval=" + interval);
    }
    return;  // moins d'un palier remboursable : pas la peine
  }

  local repaid = loan - newLoan;
  AICompany.SetLoanAmount(newLoan);
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "LR|" + year + "|" + repaid + "|" + newLoan);
  if (DECISION_LOG) {
    OpexDecide("LOAN", "action=repay repaid=" + repaid + " new_loan=" + newLoan + " cash=" + cash + " floor=" + LOAN_REPAY_FLOOR);
  }
}
