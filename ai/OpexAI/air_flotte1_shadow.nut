/* AIR-FLOTTE-1 : photographie read-only AVANT debit de capital, sonde dediee.
 * Aucun changement de score, de fit, de classement, de selection ou de budget.
 * Un RAIL du vivier hors best n'a PAS ete revalide (site, A*, admissibilite).
 * Ne jamais presenter son ROI comme un contrefactuel realise. */

/* Buffer local plutot qu'AILog dans le chemin pre-transactionnel : les logs
 * sont emis APRES le retour du constructeur. Evite qu'AILog suspende l'IA
 * entre la photographie et l'achat qu'elle doit decrire. */
function OpexAirF1Queue(logs, kind, fields)
{
  logs.append({ kind = kind, fields = fields });
}

/* Trace des rails de la passe sans changer passDiscards ni le selecteur. */
function OpexAirF1RailPath(project, rank, stage, reason)
{
  if (!AIR_FLOTTE1_SHADOW || AIR_FLOTTE1_RAIL_PATH == null || project == null) return;
  AIR_FLOTTE1_RAIL_PATH.rawset(OpexProjectAttemptKey(project),
      { rank = rank, stage = stage, reason = reason });
}

function OpexAirF1RailLog(eventId, scope, project, rank, available, spend, logs)
{
  local finance = OpexProjectFinanceCapital(project);
  local capital = ("capital" in project) ? project.capital : -1;
  local profit = ("profitAnnual" in project) ? project.profitAnnual : -1;
  local calibrated = OpexCalibratedProfit(project);
  local calRoi = finance > 0 ? (calibrated * 1000.0 / finance) : -1;
  local storedScore = scope == "listed_best_remaining" && ("fundScore" in project)
      ? project.fundScore : -1;
  OpexAirF1Queue(logs, "AIRF1_RAIL", "id=" + eventId + " scope=" + scope
      + " rank=" + rank + " key=" + OpexProjectAttemptKey(project)
      + " src=" + project.src + " dst=" + project.dst
      + " cargo=" + project.cargo + " kind=" + project.kind
      + " distance=" + project.distance + " finance=" + finance
      + " capital=" + capital + " profit_raw=" + profit
      + " profit_c70=" + calibrated + " roi_raw=" + project.roi
      + " roi_c70_finance=" + calRoi + " fund_score_stored=" + storedScore
      + " afford_now=" + ((finance <= available) ? 1 : 0)
      + " afford_after=" + ((finance <= available - spend) ? 1 : 0)
      + " eligibility=unverified");
}

/* Compte et selectionne les RAIL du vivier sans mettre a jour leurs caches.
 * Un RAIL hors best peut avoir perdu au filtre de budget, top-K, site ou autre;
 * son fundScore ne doit PAS etre reutilise : il peut dater d'une autre passe.
 * Le meilleur brut est un diagnostic, pas le meilleur candidat executable. */
function OpexAirF1PoolRail(ai, eventId, available, spend, listedKeys, logs)
{
  if (ai._projects == null || !("candidateGroups" in ai._projects)
      || ai._projects.candidateGroups == null) {
    OpexAirF1Queue(logs, "AIRF1_POOL", "id=" + eventId + " present=0");
    return;
  }
  local total = 0;
  local outside = 0;
  local outsideAffordable = 0;
  local outsideNotAffordable = 0;
  local bestRaw = null;
  local bestRawRoi = -1;
  local truncated = 0;
  local examined = 0;
  /* Pas de recherche A*, de revalidation ou de reelection du portefeuille. */
  foreach (key, list in ai._projects.candidateGroups) {
    foreach (project in list) {
      /* Borne aussi les non-RAIL : un vivier tres fourni ne doit pas
       * deplacer tous les investissements de plusieurs ticks. */
      if (examined >= 512) { truncated = 1; break; }
      examined++;
      if (project == null || !("mode" in project) || project.mode != "rail") continue;
      /* Limite de securite opcodes; si tronque, AUCUNE affirmation d'optimum. */
      if (total >= 256) { truncated = 1; break; }
      total++;
      if (OpexProjectAttemptKey(project) in listedKeys) continue;
      outside++;
      local finance = OpexProjectFinanceCapital(project);
      if (finance <= available) outsideAffordable++;
      else outsideNotAffordable++;
      if (bestRaw == null || project.roi > bestRawRoi) {
        bestRaw = project;
        bestRawRoi = project.roi;
      }
    }
    if (truncated != 0) break;
  }
  OpexAirF1Queue(logs, "AIRF1_POOL", "id=" + eventId + " present=1 total_rail=" + total
      + " examined=" + examined
      + " outside_best=" + outside + " affordable_raw=" + outsideAffordable
      + " not_affordable_raw=" + outsideNotAffordable
      + " truncated=" + truncated
      + " eligibility=unverified");
  if (bestRaw != null)
    OpexAirF1RailLog(eventId, "pool_best_raw_roi_unverified", bestRaw, -1,
                     available, spend, logs);
}

/* Instant directement avant la commande d'achat (aucun delai calendrier).
 * Le portefeuille best reste un snapshot de selection, et peut etre stale.
 * L'identifiant porte tick/cycle/ligne pour associer les logs et l'issue. */
function OpexAirF1Before(ai, channel, lineId, price, project, rank,
                         oldEngine = -1, newEngine = -1, builtKeys = null,
                         protectedCapital = -1, oldProfit = -1)
{
  if (!AIR_FLOTTE1_SHADOW) return null;
  local date = AIDate.GetCurrentDate();
  local tick = AIController.GetTick();
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local reserve = OpexCashReserve();
  /* Meme notion de capital mobilisable que le portefeuille, emprunt compris
   * lorsqu'il est autorise. Le seuil apres achat est un proxy a reserve fixe. */
  local avail = OpexAvailableCapital();
  local id = tick + "-" + ai._taskCycle + "-" + channel + "-" + lineId;
  local logs = [];
  local rawProfit = project != null ? project.profitAnnual : -1;
  local calProfit = project != null ? OpexCalibratedProfit(project) : -1;
  local finance = project != null ? OpexProjectFinanceCapital(project) : price;
  /* Pour le renfort la depense planifiee peut etre de plusieurs avions.
   * V252 est toujours une unite. La depense effective est dans OUTCOME. */
  local plannedSpend = project != null && ("capital" in project)
      ? project.capital : price;
  local score = project != null && ("fundScore" in project) ? project.fundScore : -1;
  local railSearchPhase = "none";
  local railSearchKind = "none";
  local railSearchKey = "none";
  if (ai._railSearch != null) {
    railSearchPhase = ("phase" in ai._railSearch) ? ai._railSearch.phase : "unknown";
    railSearchKind = ("kind" in ai._railSearch) ? ai._railSearch.kind : "unknown";
    if (("candidate" in ai._railSearch) && ai._railSearch.candidate != null)
      railSearchKey = OpexC69AttemptKey(ai._railSearch.candidate);
  }
  local kdec = AIR_FLOTTE1_KDEC;
  local kdecTick = AIR_FLOTTE1_KDEC_TICK;
  if (ai._projects != null && ("c69KDecData" in ai._projects)
      && ai._projects.c69KDecData != null
      && ("K_dec" in ai._projects.c69KDecData))
    kdec = ai._projects.c69KDecData.K_dec;
  local best = (ai._projects != null && ("best" in ai._projects))
      ? ai._projects.best : null;
  OpexAirF1Queue(logs, "AIRF1_BUY", "id=" + id + " channel=" + channel + " phase=before"
      + " date=" + date + " tick=" + tick + " cycle=" + ai._taskCycle
      + " line=" + lineId + " rank=" + rank + " cash=" + cash
      + " reserve=" + reserve + " avail=" + avail + " unit_price=" + price
      + " spend=" + plannedSpend
      + " finance=" + finance + " k_dec_snapshot=" + kdec
      + " k_dec_selection_tick=" + kdecTick
      + " v252_threshold=" + protectedCapital + " old_profit_history=" + oldProfit
      + " raw_profit=" + rawProfit + " calibrated_profit=" + calProfit
      + " raw_roi=" + (project != null ? project.roi : -1)
      + " fund_score=" + score + " v161_src="
      + (project != null && ("v161Source" in project) ? project.v161Source : "unknown")
      + " v161_model=" + (project != null && ("v161ModelPerPlane" in project)
                          ? project.v161ModelPerPlane : -1)
      + " old_engine=" + oldEngine + " new_engine=" + newEngine
      + " rail_search_phase=" + railSearchPhase
      + " rail_search_kind=" + railSearchKind
      + " rail_search_key=" + railSearchKey
      + " best_len=" + (best != null ? best.len() : -1)
      + " rail_realized_two_year=unknown");

  local listedKeys = {};
  local bestRail = null;
  local bestRailRank = -1;
  local nRail = 0;
  if (best != null) {
    for (local i = 0; i < best.len(); i++) {
      local p = best[i];
      if (p == null || p.mode != "rail") continue;
      local railKey = OpexProjectAttemptKey(p);
      listedKeys.rawset(railKey, true);
      /* On exclut les RAIL deja effectivement construits dans cette passe. */
      if (builtKeys != null && railKey in builtKeys) continue;
      nRail++;
      if (bestRail == null) {
        bestRail = p;
        bestRailRank = i;
      }
    }
  }
  OpexAirF1Queue(logs, "AIRF1_LIST", "id=" + id + " rail_remaining=" + nRail
      + " best_rank=" + bestRailRank
      + " search_same_best=" + ((bestRail != null
          && railSearchKey == OpexProjectAttemptKey(bestRail)) ? 1 : 0)
      + " rail_pass_stage=" + ((bestRail != null && AIR_FLOTTE1_RAIL_PATH != null
          && OpexProjectAttemptKey(bestRail) in AIR_FLOTTE1_RAIL_PATH)
              ? AIR_FLOTTE1_RAIL_PATH[OpexProjectAttemptKey(bestRail)].stage : "not_seen")
      + " rail_pass_reason=" + ((bestRail != null && AIR_FLOTTE1_RAIL_PATH != null
          && OpexProjectAttemptKey(bestRail) in AIR_FLOTTE1_RAIL_PATH)
              ? AIR_FLOTTE1_RAIL_PATH[OpexProjectAttemptKey(bestRail)].reason : "unknown")
      + " selection_is_live=unverified");
  if (bestRail != null)
    OpexAirF1RailLog(id, "listed_best_remaining", bestRail, bestRailRank,
                     avail, plannedSpend, logs);
  OpexAirF1PoolRail(ai, id, avail, plannedSpend, listedKeys, logs);
  /* Une suspension due au journal ou au scan annule l'atomicite temporelle.
   * Marquer explicitement le cas au lieu de fabriquer un meme instant. */
  local tickAfter = AIController.GetTick();
  OpexAirF1Queue(logs, "AIRF1_CLOCK", "id=" + id + " tick_before=" + tick
      + " tick_after=" + tickAfter + " same_tick=" + (tick == tickAfter ? 1 : 0));
  return { id = id, tick = tick, cash = cash, logs = logs };
}

/* Dernier relevé directement au point transactionnel. Un scan resté dans le
 * même tick n'est pas une preuve si le journal a suspendu après CLOCK. */
function OpexAirF1Ready(event)
{
  if (event == null) return;
  local tick = AIController.GetTick();
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  OpexAirF1Queue(event.logs, "AIRF1_READY", "id=" + event.id + " tick_ready=" + tick
      + " cash_ready=" + cash + " same_tick=" + (tick == event.tick ? 1 : 0)
      + " same_cash=" + (cash == event.cash ? 1 : 0));
}

function OpexAirF1After(event, outcome, added = 0, replaced = 0)
{
  if (event == null) return;
  /* Apres le debit physique seulement : les donnees sont prelevees avant,
   * mais AILog n'interfere plus avec le constructeur. */
  foreach (record in event.logs) OpexDecide(record.kind, record.fields);
  OpexDecide("AIRF1_OUTCOME", "id=" + event.id + " outcome=" + outcome
      + " added=" + added + " replaced=" + replaced
      + " tick=" + AIController.GetTick()
      + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
}
