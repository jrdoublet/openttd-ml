/* Extrait de projects.nut (R14) : Contraintes financieres : capital financable. Requis depuis projects.nut. */

/* P1 : cout a comparer a la tresorerie mobilisable. budgetCapital reste le
 * cout economique utilise par les scores historiques ; il ne faut pas y injecter
 * un multiplicateur global. Le repli de financabilite applique rail 1,7x et route
 * 1,21x. Si le trace a deja fourni un devis reel, capitalIsActual fait utiliser
 * ce montant. Les marges et le capital immobilise restent inchanges. */
/* ESTIM-1 M5 : cout de decaissement commun au choix et au chantier, aux facteurs
 * de financement qualifies du chemin historique. Un devis realise (AITestMode ou plan reel) n'est jamais multiplie de nouveau.
 * OpexAvailableCapital represente la caisse mobilisable sans reserve. */
function OpexEstimFinanceCapital(mode, capital, distance, capitalIsActual = false, immobilise = 0)
{
  if (capital < 0) capital = 0;
  if (immobilise < 0) immobilise = 0;
  local factor = 1.0;
  if (!capitalIsActual) {
    /* Facteurs de financement qualifies (decision du 26/09 : rail 100 %, route 121 %).
     * La majoration de devis rail mesuree n'est pas reintroduite au financement. */
    if (mode == "rail") factor = RAIL_FINANCE_BIAS_PCT / 100.0;
    else if (mode == "road") factor = 1.21;
  }
  return (capital.tofloat() * factor + 0.999).tointeger() + immobilise;
}

function OpexProjectFinanceCapital(project)
{
  if (project == null || !("budgetCapital" in project)) return 0;
  if ((ESTIM_UNIFIE & 2) != 0) {
    local mode = ("mode" in project) ? project.mode : "unknown";
    local capital = ("capital" in project) ? project.capital : project.budgetCapital;
    if (("deltaC" in project) && project.deltaC > 0) capital = project.deltaC;
    /* Une ligne AIR doit financer la flotte reellement commandee, pas le devis
     * a un avion de decisionEconomics. */
    local immobilise = 0;
    if (("payload" in project) && project.payload != null) {
      if (("immobilise" in project.payload)) immobilise = project.payload.immobilise;
      if (("economics" in project.payload) && project.payload.economics != null
          && ("immobilise" in project.payload.economics))
        immobilise = project.payload.economics.immobilise;
    }
    local actual = ("capitalIsActual" in project) && project.capitalIsActual;
    if (!actual && ("payload" in project) && project.payload != null
        && ("capitalIsActual" in project.payload)) actual = project.payload.capitalIsActual;
    if (actual && ("payload" in project) && project.payload != null
        && ("capital" in project.payload) && project.payload.capital > 0)
      capital = project.payload.capital;
    local distance = ("distance" in project) ? project.distance : 0;
    return OpexEstimFinanceCapital(mode, capital, distance, actual, immobilise);
  }
  local financeCapital = project.budgetCapital;
  if (!("mode" in project)) return financeCapital;

  local biasPct = 0;
  if (project.mode == "rail") biasPct = RAIL_FINANCE_BIAS_PCT;
  else if (project.mode == "road") biasPct = 121;
  else return financeCapital;

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
