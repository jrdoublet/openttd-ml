/* ROAD1Y pair_fleet : classement des paires bus-quartier en route seule sur
 * l'estimation a flotte mure. Appele par OpexRoad100SoloPaxCandidates
 * seulement si road1y_pair_fleet = N > 0.
 *
 * L'estimateur historique evalue une paire a deux bus : le profit estime est
 * alors plat en distance (6-11 k), alors que le profit mur reel croit avec
 * elle (Opex 31 k a 64-95 tuiles, 50 k a 96-127). Une ville deja prise par
 * une paire courte ne sert plus a la paire longue qu'AAAHogEx construit
 * ensuite (cause C1 de RAPPORT_CLOUD5 : 26 paires AAA sur 38).
 *
 * Pour les paires de 127 tuiles au plus, la meme economie est recalculee avec
 * un plafond de N bus (OpexRoadLineEconomics, fleetCapOverride = N) et ses
 * profit, recette, couts et ROI remplacent ceux du candidat. Flotte de
 * construction (trains), capital, sites et ordre de generation restent
 * inchanges ; le constructeur recalcule ensuite l'economie historique apres
 * trace (OpexApplyRoadEconomics), si bien que la prediction de la ligne et la
 * calibration k_R ne voient jamais l'estimation mure. */

function OpexRoad1yPairFleetRank(catalog, candidate, cargo, distance, monthly, fleet)
{
  if (fleet <= 0 || distance > 127) return;
  local engine = (cargo in catalog.roadEngineByCargo) ? catalog.roadEngineByCargo[cargo] : null;
  if (engine == null) return;
  local mature = OpexRoadLineEconomics(catalog, cargo, distance, monthly, engine, "pax",
      null, fleet);
  if (mature == null || mature.profitAnnual <= candidate.profitAnnual) {
    if (DECISION_LOG)
      OpexDecide("ROAD1Y_PAIR_FLEET", "action=keep town_a=" + candidate.srcTown
          + " town_b=" + candidate.dstTown + " site_a=" + candidate.src
          + " site_b=" + candidate.dst + " distance=" + distance + " monthly=" + monthly
          + " hist_profit=" + candidate.profitAnnual
          + " mature_profit=" + (mature == null ? 0 : mature.profitAnnual));
    return;
  }
  local histProfit = candidate.profitAnnual;
  candidate.road1yPairFleetHistProfit <- histProfit;
  candidate.road1yPairFleetVehicles <- mature.trains;
  candidate.profitAnnual = mature.profitAnnual;
  candidate.revenueAnnual = mature.revenueAnnual;
  candidate.runningAnnual = mature.runningAnnual;
  candidate.amortAnnual = mature.amortAnnual;
  candidate.roi = candidate.capital > 0 ? (mature.profitAnnual * 1000) / candidate.capital : 0;
  if (candidate.iterations > 0)
    candidate.ratio = (mature.profitAnnual * 1000) / candidate.iterations;
  if (DECISION_LOG)
    OpexDecide("ROAD1Y_PAIR_FLEET", "action=rank town_a=" + candidate.srcTown
        + " town_b=" + candidate.dstTown + " site_a=" + candidate.src
        + " site_b=" + candidate.dst + " distance=" + distance + " monthly=" + monthly
        + " hist_profit=" + histProfit + " mature_profit=" + mature.profitAnnual
        + " mature_vehs=" + mature.trains + " build_vehs=" + candidate.trains
        + " roi=" + candidate.roi);
}
