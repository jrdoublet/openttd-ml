/* Extrait de projects.nut (R14) : Contraintes financieres : capital financable. Requis depuis projects.nut. */

/* P1 : cout a comparer a la tresorerie mobilisable. budgetCapital reste le
 * cout economique utilise par les scores historiques ; il ne faut pas y injecter
 * un multiplicateur global. Le repli de financabilite applique rail 1,7x et route
 * 1,21x. Si le trace a deja fourni un devis reel, capitalIsActual fait utiliser
 * ce montant. Les marges et le capital immobilise restent inchanges. */
function OpexProjectFinanceCapital(project)
{
  if (project == null || !("budgetCapital" in project)) return 0;
  local financeCapital = project.budgetCapital;
  if (CAPITAL_QUOTE_LEARNING) return OpexCapitalQuoteFinance(project, financeCapital);
  if (!CAPITAL_CALIBRATION || !("mode" in project)) return financeCapital;

  local biasPct = 0;
  if (project.mode == "rail") biasPct = RAIL_FINANCE_BIAS_PCT;
  else if (project.mode == "road") biasPct = 121;
  else return financeCapital;

  /* P0 isolation: only ROAD's funding-side multiplier changes. Economic
   * project.capital, budgetCapital, reserves and physical build stay intact. */
  if (project.mode == "road" && ROAD_FINANCE_UNBIAS_P0) biasPct = 100;

  local capital = ("capital" in project) ? project.capital : 0;
  local modelCapital = capital;
  if (capital <= 0) return financeCapital;
  local capitalIsActual = ("capitalIsActual" in project) && project.capitalIsActual;
  if (!capitalIsActual && ("payload" in project) && project.payload != null
      && ("capitalIsActual" in project.payload)) {
    capitalIsActual = project.payload.capitalIsActual;
    if (capitalIsActual && ("capital" in project.payload)
        && project.payload.capital > 0) {
      capital = project.payload.capital;
    }
  }
  local nonConstructionCapital = financeCapital - modelCapital;
  if (nonConstructionCapital < 0) nonConstructionCapital = 0;
  if (capitalIsActual) return capital + nonConstructionCapital;

  return ((capital * biasPct) / 100) + nonConstructionCapital;
}
