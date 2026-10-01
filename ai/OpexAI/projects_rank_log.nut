/* Extrait de projects.nut (R14) : Journal de classement du portefeuille (DECISION_LOG). Requis depuis projects.nut. */

/* Le schema historique reste lisible : score/cost conservent leur sens legacy. M1 ajoute
 * rank_score/finance_capital pour publier aussi les quantites qui classent reellement. */
function OpexLogPortfolioRank(projects)
{
  if (!DECISION_LOG) return;
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) return;
  local n = projects.best.len();
  if (n > 5) n = 5;
  for (local i = 0; i < n; i++) {
    local p = projects.best[i];
    if (p == null) continue;
    local cargoStr = ("cargo" in p && p.cargo >= 0) ? AICargo.GetCargoLabel(p.cargo) : "none";
    local legacyScore = p.budgetScore;
    local rankKey = "fundScore";
    local rawRankScore = (rankKey in p) ? p[rankKey] : p.budgetScore;
    local rankScore = (AIR_EARLY_SLOT && (rankKey in p))
        ? OpexProjectSelectionScore(p, rankKey) : rawRankScore;
    local financeCapital = OpexProjectFinanceCapital(p);
    local turnoverBonus = ("turnoverBonus" in p) ? p.turnoverBonus : 100;
    local generationRatio = ("generationRatio" in p) ? p.generationRatio : 0;
    local roadFleet = (p.mode == "road" && ("vehiclesForVolume" in p))
        ? (" raw_vehs=" + p.vehiclesForVolume + " berth_cap=" + p.payload.roadBerthCapacity
           + " fleet_cap=" + p.roadVehicleCap + " capped_vehs=" + p.selectedRoadVehicles)
        : "";
    if (DECISION_LOG) OpexDecide("PORTFOLIO_RANK", "rank=" + i + " mode=" + p.mode + " kind=" + p.kind + " cargo=" + cargoStr + " src=" + p.src + " dst=" + p.dst + " dist=" + p.distance + " roi=" + p.roi + " turnover_bonus=" + turnoverBonus + " generation_ratio=" + generationRatio + " score=" + legacyScore + " rank_score=" + rankScore + " rank_score_raw=" + rawRankScore + " budget_score=" + p.budgetScore + " cost=" + p.capital + " finance_capital=" + financeCapital + " profit=" + p.profitAnnual + roadFleet);
  }
}

/* Remplace le logger ci-dessus uniquement a l'activation de la sonde. Le meme parcours publie
 * PORTFOLIO_RANK si demande, puis TENSION ; aucun second parcours du portefeuille n'est cree.
 * Le contexte -- flotte, plafonds, engagements, foncier -- ne depend PAS du projet : il est
 * calcule une seule fois, hors de la boucle. Un seul bloc de budget encadre l'ensemble, pour que
 * probe_ops mesure le cout REEL de la sonde par cycle et non par projet. */
function OpexLogPortfolioRankWithTension(projects)
{
  if (!DECISION_LOG && !TENSION_PROBE) return;
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) return;
  local n = projects.best.len();
  if (n > 5) n = 5;

  TENSION_BUDGET.begin();
  local ctx = OpexTensionContext(projects);
  local lines = [];
  for (local i = 0; i < n; i++) {
    local p = projects.best[i];
    if (p == null) continue;
    local result = OpexTensionVector(p, ctx);
    local fields = "rank=" + i + " mode=" + p.mode + " dominant=" + result.dominant
                 + " gap=" + result.gapRelative;
    foreach (entry in result.vector) {
      fields += " " + entry.resource + "_tension=" + entry.tension
              + " " + entry.resource + "_cost=" + entry.cost
              + " " + entry.resource + "_available=" + entry.available
              + " " + entry.resource + "_commitments=" + entry.commitments
              + " " + entry.resource + "_flow=" + entry.flow
              + " " + entry.resource + "_tau=" + entry.tau;
    }
    lines.append(fields);
  }
  local spent = TENSION_BUDGET.end("tension");

  /* Journalisation hors du bloc mesure : le cout du journal n'est pas celui du calcul. */
  for (local i = 0; i < n; i++) {
    local p = projects.best[i];
    if (p == null) continue;
    local cargoStr = ("cargo" in p && p.cargo >= 0) ? AICargo.GetCargoLabel(p.cargo) : "none";
    local legacyScore = p.budgetScore;
    local rankKey = "fundScore";
    local rawRankScore = (rankKey in p) ? p[rankKey] : p.budgetScore;
    local rankScore = (AIR_EARLY_SLOT && (rankKey in p))
        ? OpexProjectSelectionScore(p, rankKey) : rawRankScore;
    local financeCapital = OpexProjectFinanceCapital(p);
    local turnoverBonus = ("turnoverBonus" in p) ? p.turnoverBonus : 100;
    local generationRatio = ("generationRatio" in p) ? p.generationRatio : 0;
    local roadFleet = (p.mode == "road" && ("vehiclesForVolume" in p))
        ? (" raw_vehs=" + p.vehiclesForVolume + " berth_cap=" + p.payload.roadBerthCapacity
           + " fleet_cap=" + p.roadVehicleCap + " capped_vehs=" + p.selectedRoadVehicles)
        : "";
    if (DECISION_LOG) OpexDecide("PORTFOLIO_RANK", "rank=" + i + " mode=" + p.mode + " kind=" + p.kind + " cargo=" + cargoStr + " src=" + p.src + " dst=" + p.dst + " dist=" + p.distance + " roi=" + p.roi + " turnover_bonus=" + turnoverBonus + " generation_ratio=" + generationRatio + " score=" + legacyScore + " rank_score=" + rankScore + " rank_score_raw=" + rawRankScore + " budget_score=" + p.budgetScore + " cost=" + p.capital + " finance_capital=" + financeCapital + " profit=" + p.profitAnnual + roadFleet);
  }
  foreach (fields in lines) OpexDecide("TENSION", fields);
  /* Les quatre mesures foncieres cote a cote : le stock d'origines libres (celui qui est
   * desormais au denominateur), la pression de separation, les paires produites, et l'ancien
   * proxy de taille de vivier. C'est ce qui permet de comparer les mesures entre elles au lieu
   * d'en figer une a l'aveugle. */
  OpexDecide("TENSION_COST", "probe_ops=" + spent + " projects=" + lines.len()
             + " fleet_rail=" + ctx.fleet.rail + " fleet_road=" + ctx.fleet.road
             + " fleet_air=" + ctx.fleet.air + " fleet_water=" + ctx.fleet.water
             + " origins_free=" + ctx.originsFree + " origins_served=" + ctx.originsServed
             + " pairs_total=" + ctx.pairsTotal + " separation_rejected=" + ctx.separationRejected
             + " pool_rail=" + ctx.pool.rail + " pool_road=" + ctx.pool.road
             + " pool_air=" + ctx.pool.air + " pool_water=" + ctx.pool.water);
}
