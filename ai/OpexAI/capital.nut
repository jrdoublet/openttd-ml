/* Capital effectivement mobilisable par le portefeuille. Cette valeur doit toujours etre relue
 * apres une depense, car la caisse peut changer.
 * Centraliser la formule evite que la future passe dynamique (C38) ne diverge de la generation,
 * du rafraichissement ou du cache incremental. */
function OpexAvailableCapital()
{
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  return cash > 0 ? cash : 0;
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
