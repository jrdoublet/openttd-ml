/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
function OpexCashReserve()
{
  if (!DYNAMIC_CASH_RESERVE) {
    /* Branche statique : la boucle vehicules n'existe ici que si le plafond est demande, jamais
     * inconditionnellement (elle serait sans objet a reglage 0). */
    if (!RESERVE_MAINT_CAP) return CASH_RESERVE_STATIC;
    local totalRunning = 0;
    local vehicles = AIVehicleList();
    vehicles.Valuate(AIVehicle.GetRunningCost);
    for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
      totalRunning += vehicles.GetValue(v);
    }
    local maintCap = totalRunning / 12;
    if (maintCap < CASH_RESERVE_STATIC) return maintCap;
    return CASH_RESERVE_STATIC;
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
  /* Le plafond d'un mois d'entretien (decision utilisateur) prime sur le plancher CASH_RESERVE_MIN :
   * totalRunning / 12 est toujours < totalRunning / 4, donc ce plafond mord des que l'entretien
   * annuel passe sous 60 000 £, y compris jusqu'a 0 flotte vide. Assume, pas une marge de securite. */
  if (RESERVE_MAINT_CAP) {
    local maintCap = totalRunning / 12;
    if (maintCap < reserve) reserve = maintCap;
  }
  return reserve;
}
/* Capital effectivement mobilisable par le portefeuille. Cette valeur doit toujours etre relue
 * apres une depense : la caisse, le reliquat d'emprunt et la reserve peuvent tous avoir change.
 * Centraliser la formule evite que la future passe dynamique (C38) ne diverge de la generation,
 * du rafraichissement ou du cache incremental. */
function OpexAvailableCapital()
{
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local borrowable = REBORROW
      ? AICompany.GetMaxLoanAmount() - AICompany.GetLoanAmount() : 0;
  if (borrowable < 0) borrowable = 0;
  local available = cash + borrowable - OpexCashReserve();
  return available > 0 ? available : 0;
}
/* Tire le palier d'emprunt manquant pour atteindre `need`, jamais le maximum. Appeler seulement
 * quand REBORROW est vrai ET que money < need : le chemin historique (reborrow=0) ne paie alors
 * ni GetLoanAmount ni cette fonction.
 *
 * Arrondi VERS LE HAUT au palier GetLoanInterval(), puis bride a GetMaxLoanAmount() -- le
 * symetrique de _tryRepayLoan, qui arrondit aussi vers le haut pour ne pas passer sous son
 * plancher. Pose GL seulement sur un tirage reel : GL|year|drew|newLoan|ok (ok=1 si le solde
 * couvre need). Pire nom GL|1999|9999999|9999999|0 = 26 caracteres. */
function OpexTryReborrow(need, money)
{
  local loan = AICompany.GetLoanAmount();
  local maxLoan = AICompany.GetMaxLoanAmount();
  if (loan >= maxLoan) return money;
  local interval = AICompany.GetLoanInterval();
  if (interval <= 0) return money;

  local gap = need - money;
  if (gap <= 0) return money;
  local target = loan + gap;
  if (target > maxLoan) target = maxLoan;
  local newLoan = ((target + interval - 1) / interval) * interval;
  if (newLoan > maxLoan) newLoan = (maxLoan / interval) * interval;
  if (newLoan <= loan) return money;

  AICompany.SetLoanAmount(newLoan);
  local after = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local drew = after - money;
  if (drew <= 0) return after;
  local covered = after >= need ? 1 : 0;
  if (DECISION_LOG) {
    OpexDecide("LOAN", "action=reborrow drew=" + drew + " new_loan=" + newLoan + " covered=" + covered + " need=" + need + " cash_after=" + after);
  }
  OpexSign(AIMap.GetTileIndex(1, 1),
           "GL|" + AIDate.GetYear(AIDate.GetCurrentDate()) + "|" + drew + "|" + newLoan
                 + "|" + covered);
  return after;
}
/* Remboursement annuel : une fois la tresorerie confortablement au-dessus du plancher, on
 * rembourse le maximum d'emprunt qui laisse encore ce plancher disponible pour l'annee
 * suivante. SetLoanAmount exige un multiple de GetLoanInterval() ; on arrondit donc le nouvel
 * emprunt VERS LE HAUT (jamais vers le bas, ce qui rembourserait plus que permis et pourrait
 * passer sous le plancher). Le reemprunt a la demande (OpexTryReborrow, derriere reborrow)
 * est le pendant : sans lui ce remboursement est a sens unique. */
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
