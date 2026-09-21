/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Publie a l'entree du mois suivant : ainsi toutes les tranches du mois clos sont attribuees
 * a leur tache effective, y compris une continuation rail qui precede la file. */
function OpexAI::_logC41MonthlyBusyLedger()
{
  if (!C41_MONTHLY_BUSY_LEDGER || this._c41MonthlyBusyLedger == null) return;
  local year = this._c41MonthlyBusyMonth / 12;
  local month = this._c41MonthlyBusyMonth % 12 + 1;
  foreach (task, entry in this._c41MonthlyBusyLedger) {
    OpexC41SchedulerLog("C41_MONTH_BUSY", "year=" + year + " month=" + month + " task=" + task
                        + " calls=" + entry.calls + " ran=" + entry.ran + " ops=" + entry.ops);
  }
}
/* Publication annuelle, hors des passages mesures : au plus une ligne par categorie et par an.
 * Reset apres publication afin que chaque ligne decrive une fenetre comparable. */
function OpexAI::_logC41SlackLedger(year)
{
  if (!C41_SLACK_LEDGER || this._c41SlackLedger == null) return;
  foreach (task, entry in this._c41SlackLedger) {
    OpexC41SchedulerLog("C41_SLACK_LEDGER", "year=" + year + " task=" + task
                        + " calls=" + entry.calls + " ran=" + entry.ran + " ops=" + entry.ops
                        + " slack_ops_available=" + entry.slackAvailable
                        + " slack_ops_used=" + entry.slackUsed
                        + " slack_ops_left=" + entry.slackLeft);
  }
  this._c41SlackLedger = {};
}
/* C41.13 : photographie sans cout de carte ni de catalogue. Les dates sont posees seulement par
 * C41.0 au premier evenement d'une rafale ; une couche sans date ne produit donc pas de faux
 * point de fraicheur. */
function OpexAI::_recordC41StaleOpportunity(slackLeft)
{
  if ((!C41_OPPORTUNITY_LEDGER && !C41_ADMISSION_LEDGER) || this._staleness == null) return;
  local now = AIDate.GetCurrentDate();
  foreach (layer in ["cargos", "towns", "industries", "rail", "road", "air", "water"]) {
    local since = this._staleness.dirtySince.catalog[layer];
    if (since < 0) continue;
    local key = "catalog." + layer;
    if (C41_OPPORTUNITY_LEDGER && this._c41OpportunityLedger != null) {
      local entry = (key in this._c41OpportunityLedger) ? this._c41OpportunityLedger[key]
          : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
      local age = now - since;
      entry.observations++;
      entry.staleDays += age;
      if (age > entry.maxStaleDays) entry.maxStaleDays = age;
      entry.slackLeft += slackLeft;
      this._c41OpportunityLedger.rawset(key, entry);
    }
    local hint = OpexC41MicrotaskOpsHint(key);
    if (C41_ADMISSION_LEDGER && hint > 0 && this._c41AdmissionLedger != null) {
      local admission = (key in this._c41AdmissionLedger) ? this._c41AdmissionLedger[key]
          : { checks = 0, fits = 0, maxSlackLeft = 0, targetOps = hint };
      admission.checks++;
      if (slackLeft >= hint) admission.fits++;
      if (slackLeft > admission.maxSlackLeft) admission.maxSlackLeft = slackLeft;
      this._c41AdmissionLedger.rawset(key, admission);
    }
  }
  foreach (layer in ["rail", "road", "air", "water"]) {
    local since = this._staleness.dirtySince.candidates[layer];
    if (since < 0) continue;
    local key = "candidates." + layer;
    local entry = (key in this._c41OpportunityLedger) ? this._c41OpportunityLedger[key]
        : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
    local age = now - since;
    entry.observations++;
    entry.staleDays += age;
    if (age > entry.maxStaleDays) entry.maxStaleDays = age;
    entry.slackLeft += slackLeft;
    this._c41OpportunityLedger.rawset(key, entry);
  }
  foreach (layer in ["portfolio", "selection"]) {
    local since = this._staleness.dirtySince[layer];
    if (since < 0) continue;
    local entry = (layer in this._c41OpportunityLedger) ? this._c41OpportunityLedger[layer]
        : { observations = 0, staleDays = 0, maxStaleDays = 0, slackLeft = 0 };
    local age = now - since;
    entry.observations++;
    entry.staleDays += age;
    if (age > entry.maxStaleDays) entry.maxStaleDays = age;
    entry.slackLeft += slackLeft;
    this._c41OpportunityLedger.rawset(layer, entry);
  }
}
function OpexAI::_logC41AdmissionLedger(year)
{
  if (!C41_ADMISSION_LEDGER || this._c41AdmissionLedger == null) return;
  foreach (layer, entry in this._c41AdmissionLedger) {
    OpexC41SchedulerLog("C41_ADMISSION_LEDGER", "year=" + year + " layer=" + layer
                        + " target_ops=" + entry.targetOps + " checks=" + entry.checks
                        + " fits=" + entry.fits + " max_slack_ops_left=" + entry.maxSlackLeft);
  }
  this._c41AdmissionLedger = {};
}
function OpexAI::_logC41OpportunityLedger(year)
{
  if (!C41_OPPORTUNITY_LEDGER || this._c41OpportunityLedger == null) return;
  foreach (layer, entry in this._c41OpportunityLedger) {
    OpexC41SchedulerLog("C41_OPPORTUNITY_LEDGER", "year=" + year + " layer=" + layer
                        + " observations=" + entry.observations + " stale_days_sum=" + entry.staleDays
                        + " max_stale_days=" + entry.maxStaleDays + " slack_ops_left=" + entry.slackLeft);
  }
  this._c41OpportunityLedger = {};
}
/* C41.46 : accumulateur UNIQUE (pas par categorie, contrairement aux autres ledgers C41) -- il
 * n'existe qu'un seul canal de recherche rail a la fois (this._railSearch), donc rien a ventiler. */
function OpexAI::_recordC41RailSliceLedger(netOps, taskOps, iterDelta, done)
{
  if (this._c41RailSliceLedger == null) {
    this._c41RailSliceLedger = { calls = 0, notDoneCalls = 0, netOps = 0, taskOps = 0, iterDelta = 0 };
  }
  local entry = this._c41RailSliceLedger;
  entry.calls++;
  if (!done) entry.notDoneCalls++;
  entry.netOps += netOps;
  entry.taskOps += taskOps;
  entry.iterDelta += iterDelta;
}
/* Publication annuelle, comme C41.11. `not_done_calls` = tranches qui n'ont PAS atteint
 * slice.done (recherche toujours en "search" apres l'appel) ; calls - not_done_calls = tranches
 * qui ont termine leur recherche (transition vers phase "build") cette annee. */
function OpexAI::_logC41RailSliceLedger(year)
{
  if (!C41_RAIL_SLICE_LEDGER || this._c41RailSliceLedger == null
      || this._c41RailSliceLedger.calls == 0) {
    this._c41RailSliceLedger = null;
    return;
  }
  local entry = this._c41RailSliceLedger;
  OpexC41RailSliceLog("year=" + year + " calls=" + entry.calls
                      + " not_done_calls=" + entry.notDoneCalls
                      + " net_ops=" + entry.netOps + " task_ops=" + entry.taskOps
                      + " iter_delta=" + entry.iterDelta);
  this._c41RailSliceLedger = null;
}
/* C39.6 : accumulateur PAR CLE (contrairement a C41.46, canal rail unique) -- la cle croise le
 * nom de tache de file et la presence d'une tranche A* dans la meme passe. */
function OpexAI::_recordC39PassClockLedger(key, days, ticks, ops, sliceDays, sliceTicks, sliceOps)
{
  if (this._c39PassClockLedger == null) this._c39PassClockLedger = {};
  local entry = (key in this._c39PassClockLedger) ? this._c39PassClockLedger[key]
      : { passes = 0, days = 0, ticks = 0, ops = 0, sliceDays = 0, sliceTicks = 0, sliceOps = 0 };
  entry.passes++;
  entry.days += days;
  entry.ticks += ticks;
  entry.ops += ops;
  entry.sliceDays += sliceDays;
  entry.sliceTicks += sliceTicks;
  entry.sliceOps += sliceOps;
  this._c39PassClockLedger.rawset(key, entry);
}
/* Publication annuelle, comme les autres ledgers C39/C41 : une ligne par cle, reset apres
 * publication pour que chaque ligne decrive une fenetre comparable (meme motif que
 * _logC41SlackLedger / _logC41RailSliceLedger). */
function OpexAI::_logC39PassClockLedger(year)
{
  if (!C39_PASS_CLOCK_LEDGER || this._c39PassClockLedger == null) return;
  foreach (key, entry in this._c39PassClockLedger) {
    OpexC39PassClockLog("phase=annual year=" + year + " key=" + key
                        + " passes=" + entry.passes + " days=" + entry.days
                        + " ticks=" + entry.ticks + " ops=" + entry.ops
                        + " slice_days=" + entry.sliceDays + " slice_ticks=" + entry.sliceTicks
                        + " slice_ops=" + entry.sliceOps);
  }
  this._c39PassClockLedger = {};
}
/* C48 : les ops par tentative sont volontairement imbriques dans ops_total de la passe. La
 * soustraction faite au depouillement mesure le cout hors tentative (balayage, A*, logs) ; ce
 * n'est pas un double comptage a "corriger". */
function OpexAI::_recordC48AttemptLedger(mode, outcome, rank, ops, days)
{
  if (this._c48AttemptLedger == null) this._c48AttemptLedger = {};
  local key = mode + "|" + outcome;
  local entry = (key in this._c48AttemptLedger) ? this._c48AttemptLedger[key]
      : { attempts = 0, ops = 0, days = 0, rankSum = 0 };
  entry.attempts++;
  entry.ops += ops;
  entry.days += days;
  entry.rankSum += rank;
  this._c48AttemptLedger.rawset(key, entry);
}
function OpexAI::_recordC48PassLedger(attemptsTotal, opsTotal, built, bestLen, maxRank)
{
  if (this._c48PassLedger == null) this._c48PassLedger = {};
  local entry = ("pass" in this._c48PassLedger) ? this._c48PassLedger.pass
      : { passes = 0, attemptsTotal = 0, opsTotal = 0, built = 0, bestLenSum = 0, maxRankSum = 0 };
  entry.passes++;
  entry.attemptsTotal += attemptsTotal;
  entry.opsTotal += opsTotal;
  if (built) entry.built++;
  entry.bestLenSum += bestLen;
  entry.maxRankSum += maxRank;
  this._c48PassLedger.rawset("pass", entry);
}
/* La tache report passe au premier tour de l'annee suivante : year=1971 decrit donc 1970, et
 * la derniere annee de partie n'est jamais publiee (~82 % de couverture sur six ans). */
function OpexAI::_logC48ProjectAttemptLedger(year)
{
  if (!C48_PROJECT_ATTEMPT_LEDGER) return;
  if (this._c48AttemptLedger != null) {
    foreach (key, entry in this._c48AttemptLedger) {
      OpexC48ProjectAttemptLog("phase=annual year=" + year + " key=" + key
          + " attempts=" + entry.attempts + " ops=" + entry.ops + " days=" + entry.days
          + " rank_sum=" + entry.rankSum);
    }
  }
  if (this._c48PassLedger != null && ("pass" in this._c48PassLedger)) {
    local entry = this._c48PassLedger.pass;
    OpexC48ProjectAttemptLog("phase=annual_pass year=" + year + " passes=" + entry.passes
        + " attempts_total=" + entry.attemptsTotal + " ops_total=" + entry.opsTotal
        + " built=" + entry.built + " best_len_sum=" + entry.bestLenSum
        + " max_rank_sum=" + entry.maxRankSum);
  }
  this._c48AttemptLedger = {};
  this._c48PassLedger = {};
}
/* C49 : une seule cause, pour le premier rang non bati de LA passe. La tresorerie est lue ici,
 * a la fin : la question est MARGINALE — « given what we just did, what blocked the next one? ».
 * Une construction qui a consomme du cash rend donc correctement le rang suivant bloque par
 * TRESORERIE. Un projet non tente ne peut pas etre teste sur la carte sans changer la decision
 * et consommer des opcodes : `site` n'est attribue qu'a un echec carte deja observe ; `decision`
 * absorbe ces echecs carte non observes. C'est une limite acceptee, pas une omission. */
function OpexAI::_recordC49ScarcityPass(best, builtRanks, attemptedRanks, passDiscards)
{
  if (!C49_SCARCITY_LEDGER || this._c49ScarcityLedger == null) return;
  this._c49ScarcityLedger.passes++;
  if (best == null || best.len() == 0) {
    this._c49ScarcityLedger.none++;
    return;
  }

  local targetRank = -1;
  for (local i = 0; i < best.len(); i++) {
    if (!(i in builtRanks)) {
      targetRank = i;
      break;
    }
  }
  if (targetRank < 0) {
    this._c49ScarcityLedger.none++;
    return;
  }

  local project = best[targetRank];
  if (project == null) {
    this._c49ScarcityLedger.none++;
    return;
  }
  local available = OpexAvailableCapital();
  if (project.capital > available) {
    this._c49ScarcityLedger.cash++;
    return;
  }

  local vehicleType = OpexC49VehicleType(project.mode);
  local vehicleMode = project.mode == "fleet" ? "air" : project.mode;
  local setting = OpexTensionVehicleSetting(vehicleMode);
  if (vehicleType >= 0 && setting != null && AIGameSettings.IsValid(setting)) {
    local planned = OpexTensionProjectVehicleCount(project);
    local cap = AIGameSettings.GetValue(setting);
    if (AIGroup.GetNumVehicles(AIGroup.GROUP_ALL, vehicleType) + planned > cap) {
      this._c49ScarcityLedger.vehicles++;
      return;
    }
  }

  if (OpexC49IsMapFailure(passDiscards, targetRank)) {
    this._c49ScarcityLedger.site++;
    return;
  }
  if (targetRank in attemptedRanks) this._c49ScarcityLedger.decision_attempted++;
  else this._c49ScarcityLedger.decision_unattempted++;
}
/* La tache report publie au premier passage de l'annee suivante : year=1971 decrit donc 1970,
 * et la derniere annee de partie n'est jamais publiee (~82 % de couverture sur six ans). */
function OpexAI::_logC49ScarcityLedger(year)
{
  if (!C49_SCARCITY_LEDGER || this._c49ScarcityLedger == null) return;
  local entry = this._c49ScarcityLedger;
  local regime = this._c49ScarcityRegime;
  local best = entry.cash;
  local decision = entry.decision_attempted + entry.decision_unattempted;
  foreach (resource in ["vehicles", "site"]) {
    if (entry[resource] > best) best = entry[resource];
  }
  if (decision > best) best = decision;
  local leaders = 0;
  foreach (resource in ["cash", "vehicles", "site"]) {
    if (entry[resource] == best) leaders++;
  }
  if (decision == best) leaders++;
  if (leaders == 1) {
    foreach (resource in ["cash", "vehicles", "site"]) {
      if (entry[resource] == best) {
        regime = resource;
        break;
      }
    }
    if (decision == best) regime = "decision";
  }
  /* Egalite : ne pas remplacer le regime precedent, hysteresis sans constante. */
  this._c49ScarcityRegime = regime;
  ::C49_CURRENT_REGIME = regime;
  OpexC49ScarcityLog("phase=annual year=" + year + " passes=" + entry.passes
      + " cash=" + entry.cash + " vehicles=" + entry.vehicles + " site=" + entry.site
      + " decision_attempted=" + entry.decision_attempted
      + " decision_unattempted=" + entry.decision_unattempted
      + " none=" + entry.none + " regime=" + regime);
  this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
      decision_attempted = 0, decision_unattempted = 0, none = 0 };
}
/* C50 : suivi mensuel de la tresorerie. 12 lignes par an, leger et sans allocation inutile. */
function OpexAI::_checkC50MonthlyTreasury(year)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local c50Date = AIDate.GetCurrentDate();
  local c50Ym = AIDate.GetYear(c50Date) * 12 + AIDate.GetMonth(c50Date);
  if (this._c50LastTreasuryMonth == c50Ym) return;
  this._c50LastTreasuryMonth = c50Ym;

  local bank = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local loan = AICompany.GetLoanAmount();
  local available = OpexAvailableCapital();
  OpexC50ChronologyLog("phase=treasury_monthly year=" + AIDate.GetYear(c50Date) + " month=" + AIDate.GetMonth(c50Date)
      + " cash=" + bank + " loan=" + loan + " available=" + available);
}
/* C50 : synthese annuelle de tresorerie au tour de report. */
function OpexAI::_logC50AnnualReport(year)
{
  if (!C50_CHRONOLOGY_PROBE) return;
  local bank = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local loan = AICompany.GetLoanAmount();
  local maxLoan = AICompany.GetMaxLoanAmount();
  local available = OpexAvailableCapital();
  /* M1 : GetCompanyValue a disparu de l'API NoAI. Le canal annuel doit publier
   * la valeur observee du trimestre courant, pas un zero sentinelle. */
  local val = AICompany.GetQuarterlyCompanyValue(
      AICompany.COMPANY_SELF, AICompany.CURRENT_QUARTER);
  OpexC50ChronologyLog("phase=treasury_annual year=" + year + " cash=" + bank
      + " loan=" + loan + " max_loan=" + maxLoan + " available=" + available
      + " company_value=" + val + " lines=" + this._lines.len());
  this._c50RefuseCache = {};
  C50_REFUSE_CACHE.clear();

  if (C50_NON_EXPANSION_LEDGER != null) {
    // --- AIR DIAGNOSTIC ---
    local airLines = 0;
    local airPlanes = 0;
    local airCapPhys = 0;
    local airCapDemand = 0;
    local airLinesAtCap = 0;
    foreach (line in this._lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      airLines++;
      local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
      airPlanes += have;
      local isSmall = (AIAirport.IsAirportTile(line.stationA) && AIAirport.GetAirportType(line.stationA) == AIAirport.AT_SMALL) ||
                      (AIAirport.IsAirportTile(line.stationB) && AIAirport.GetAirportType(line.stationB) == AIAirport.AT_SMALL);
      local physCap = isSmall ? 4 : AIR_MAX_PLANES_PER_ROUTE;
      if (AIR_CADENCE_CAP) physCap = OpexAirCadenceCap(line, this._catalog, this._lines);
      local demCap = physCap;
      if (AIR_DEMAND_CAP) {
        local d = OpexAirDemandCap(line, this._catalog, this._lines);
        if (d.cap < demCap) demCap = d.cap;
      }
      airCapPhys += physCap;
      airCapDemand += demCap;
      if (have >= demCap) airLinesAtCap++;
    }

    local la = C50_NON_EXPANSION_LEDGER.air;
    OpexC50ChronologyLog("phase=c50b_non_expansion mode=air year=" + year
        + " lines=" + airLines + " planes_total=" + airPlanes
        + " cap_physical=" + airCapPhys + " cap_demand=" + airCapDemand
        + " lines_at_cap=" + airLinesAtCap + " want_sum=" + la.want_sum
        + " ref_Y=" + la.ref_Y + " ref_C=" + la.ref_C + " ref_Q=" + la.ref_Q
        + " ref_L=" + la.ref_L + " ref_M=" + la.ref_M + " ref_W=" + la.ref_W
        + " ref_D=" + la.ref_D + " ref_V=" + la.ref_V + " ref_S=" + la.ref_S
        + " ref_X=" + la.ref_X + " ref_R=" + la.ref_R);

    // --- RAIL DIAGNOSTIC ---
    local railLines = 0;
    local railTrains = 0;
    local rail1Train = 0;
    local rail2Trains = 0;
    local railSingle = 0;
    local railDouble = 0;
    local railProfitable = 0;
    local railBacklogMet = 0;
    foreach (line in this._lines) {
      if (!("mode" in line) || line.mode != "rail") continue;
      railLines++;
      local trains = ("trains" in line) ? line.trains : (("vehicles" in line) ? line.vehicles.len() : 0);
      railTrains += trains;
      if (trains >= 2) rail2Trains++;
      else rail1Train++;
      if (("doubleTrack" in line) && line.doubleTrack == 1) railDouble++;
      else railSingle++;
      if (("lastProfit" in line) && line.lastProfit > 0) railProfitable++;

      if (line.cargo in this._catalog.wagonByCargo) {
        local wagon = this._catalog.wagonByCargo[line.cargo];
        local wA = ("lastWaitingA" in line) ? line.lastWaitingA : 0;
        local wB = ("lastWaitingB" in line) ? line.lastWaitingB : 0;
        local waiting = (("kind" in line) && line.kind == "freight") ? wA : (wA + wB);
        local thresh = (("kind" in line) && line.kind == "freight") ? (2 * wagon.capacity) : (4 * wagon.capacity);
        if (waiting >= thresh) railBacklogMet++;
      }
    }

    local lr = C50_NON_EXPANSION_LEDGER.rail;
    OpexC50ChronologyLog("phase=c50b_non_expansion mode=rail year=" + year
        + " lines=" + railLines + " trains_total=" + railTrains
        + " lines_1train=" + rail1Train + " lines_2trains=" + rail2Trains
        + " single_track=" + railSingle + " double_track=" + railDouble
        + " profitable=" + railProfitable + " backlog_met=" + railBacklogMet
        + " cash_refused=" + lr.cash_refused + " prep_failed=" + lr.prep_failed
        + " upgrade_failed=" + lr.upgrade_failed + " second_built=" + lr.second_built
        + " double_built=" + lr.double_built);

    // --- ROAD DIAGNOSTIC ---
    local roadLines = 0;
    local roadVehs = 0;
    foreach (line in this._lines) {
      if (!("mode" in line) || line.mode != "road") continue;
      roadLines++;
      local vehs = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
      roadVehs += vehs;
    }

    local lrd = C50_NON_EXPANSION_LEDGER.road;
    OpexC50ChronologyLog("phase=c50b_non_expansion mode=road year=" + year
        + " lines=" + roadLines + " vehs_total=" + roadVehs
        + " physical_cap_hit=" + lrd.physical_cap_hit + " congestion_hit=" + lrd.congestion_hit
        + " no_demand=" + lrd.no_demand + " loss_hit=" + lrd.loss_hit
        + " cash_refused=" + lrd.cash_refused + " other_refused=" + lrd.other_refused
        + " refill_built=" + lrd.refill_built);

    OpexC50ResetNonExpansionLedger();
  }
}
/* C50 : enregistrement deduplique des refus de tresorerie (au plus un log par mois calendaire et par candidat). */
function OpexAI::_logC50CashRefusal(mode, rank, cost, profit, roi, src, dst, need, money)
{
  OpexC50LogCashRefusal(mode, rank, cost, profit, roi, src, dst, need, money);
}
/* C55 : le report de debut d'annee publie l'annee ecoulee. La ligne summary est cumulative ;
 * la derniere ligne du log est donc aussi la synthese de fin de partie lisible sans jointure. */
function OpexAI::_logC55OriginRelaxLedger(year)
{
  if (!C55_ORIGIN_RELAX_PROBE || C55_ORIGIN_RELAX_LEDGER == null) return;
  local entry = C55_ORIGIN_RELAX_LEDGER;
  OpexC55OriginRelaxLog("phase=annual year=" + year + " candidates_seen=" + entry.candidates_seen
      + " rejected_total=" + entry.rejected_total + " both_served=" + entry.both_served
      + " one_served=" + entry.one_served + " one_served_pax=" + entry.one_served_pax
      + " one_served_freight=" + entry.one_served_freight
      + " duplicate_exact=" + entry.duplicate_exact);
  entry.total_candidates_seen += entry.candidates_seen;
  entry.total_rejected_total += entry.rejected_total;
  entry.total_both_served += entry.both_served;
  entry.total_one_served += entry.one_served;
  entry.total_one_served_pax += entry.one_served_pax;
  entry.total_one_served_freight += entry.one_served_freight;
  entry.total_duplicate_exact += entry.duplicate_exact;
  OpexC55OriginRelaxLog("phase=summary year=" + year + " candidates_seen=" + entry.total_candidates_seen
      + " rejected_total=" + entry.total_rejected_total + " both_served=" + entry.total_both_served
      + " one_served=" + entry.total_one_served + " one_served_pax=" + entry.total_one_served_pax
      + " one_served_freight=" + entry.total_one_served_freight
      + " duplicate_exact=" + entry.total_duplicate_exact);
  C55_ORIGIN_RELAX_LEDGER = {
    candidates_seen = 0, rejected_total = 0, both_served = 0, one_served = 0,
    one_served_pax = 0, one_served_freight = 0, duplicate_exact = 0,
    total_candidates_seen = entry.total_candidates_seen, total_rejected_total = entry.total_rejected_total,
    total_both_served = entry.total_both_served, total_one_served = entry.total_one_served,
    total_one_served_pax = entry.total_one_served_pax,
    total_one_served_freight = entry.total_one_served_freight,
    total_duplicate_exact = entry.total_duplicate_exact,
  };
}
/* C55 : sonde de tracabilite causale PAX routier. */
function OpexAI::_logC55PaxTraceLedger(year)
{
  if (!C55_PAX_TRACE_PROBE || C55_PAX_TRACE_LEDGER == null) return;
  local entry = C55_PAX_TRACE_LEDGER;
  entry.total_revalidated += entry.revalidated;
  entry.total_origin_blocked += entry.origin_blocked;
  entry.total_spared += entry.spared;
  entry.total_attempted += entry.attempted;
  entry.total_precheck_ok += entry.precheck_ok;
  entry.total_financeable += entry.financeable;
  entry.total_planned += entry.planned;
  entry.total_viable += entry.viable;
  entry.total_built += entry.built;
  entry.total_built_profit += entry.built_profit;

  OpexC55PaxTraceLog("C55_PAX_TRACE", "phase=annual year=" + year
      + " revalidated=" + entry.revalidated
      + " origin_blocked=" + entry.origin_blocked
      + " spared=" + entry.spared
      + " attempted=" + entry.attempted
      + " precheck_ok=" + entry.precheck_ok
      + " financeable=" + entry.financeable
      + " planned=" + entry.planned
      + " viable=" + entry.viable
      + " built=" + entry.built
      + " built_profit=" + entry.built_profit);

  OpexC55PaxTraceLog("C55_PAX_TRACE", "phase=summary year=" + year
      + " revalidated=" + entry.total_revalidated
      + " origin_blocked=" + entry.total_origin_blocked
      + " spared=" + entry.total_spared
      + " attempted=" + entry.total_attempted
      + " precheck_ok=" + entry.total_precheck_ok
      + " financeable=" + entry.total_financeable
      + " planned=" + entry.total_planned
      + " viable=" + entry.total_viable
      + " built=" + entry.total_built
      + " built_profit=" + entry.total_built_profit);

  C55_PAX_TRACE_LEDGER = {
    revalidated = 0, origin_blocked = 0, spared = 0,
    attempted = 0, precheck_ok = 0, financeable = 0,
    planned = 0, viable = 0, built = 0, built_profit = 0,
    total_revalidated = entry.total_revalidated,
    total_origin_blocked = entry.total_origin_blocked,
    total_spared = entry.total_spared,
    total_attempted = entry.total_attempted,
    total_precheck_ok = entry.total_precheck_ok,
    total_financeable = entry.total_financeable,
    total_planned = entry.total_planned,
    total_viable = entry.total_viable,
    total_built = entry.total_built,
    total_built_profit = entry.total_built_profit,
  };
}
/* C60 : Le rapport annuel publie le bilan d'exposition aux notes municipales. */
function OpexAI::_logC60TownRatingLedger(year)
{
  if (!C60_TOWN_RATING_PROBE || C60_TOWN_RATING_LEDGER == null) return;
  local entry = C60_TOWN_RATING_LEDGER;
  OpexDecide("C60_TOWN_RATING_SUMMARY", "year=" + year
      + " checks=" + entry.checks
      + " none=" + entry.none
      + " ok=" + entry.ok
      + " very_poor=" + entry.very_poor
      + " appalling=" + entry.appalling
      + " road_checks=" + entry.by_mode.road.checks
      + " road_refused=" + entry.by_mode.road.refused
      + " rail_checks=" + entry.by_mode.rail.checks
      + " rail_refused=" + entry.by_mode.rail.refused
      + " air_checks=" + entry.by_mode.air.checks
      + " air_refused=" + entry.by_mode.air.refused);
}
/* C52 : le report de debut d'annee publie l'annee ecoulee et conserve un resume cumulatif. */
function OpexAI::_logC52AutoreplaceLedger(year)
{
  if (!C52_AUTOREPLACE_LOG || C52_AUTOREPLACE_LEDGER == null) return;
  local entry = C52_AUTOREPLACE_LEDGER;
  OpexC52AutoreplaceLog("phase=annual year=" + year + " events=" + entry.events
      + " remap_line_vehicles=" + entry.remap_line_vehicles
      + " remap_line_vehicle=" + entry.remap_line_vehicle
      + " remap_scrap_vehicles=" + entry.remap_scrap_vehicles
      + " remap_scrap_index=" + entry.remap_scrap_index + " untracked=" + entry.untracked
      + " rail=" + entry.rail + " road=" + entry.road + " air=" + entry.air
      + " water=" + entry.water + " unknown=" + entry.unknown
      + " line_rail=" + entry.line_rail + " line_road=" + entry.line_road
      + " line_air=" + entry.line_air + " line_water=" + entry.line_water);
  entry.total_events += entry.events;
  entry.total_remap_line_vehicles += entry.remap_line_vehicles;
  entry.total_remap_line_vehicle += entry.remap_line_vehicle;
  entry.total_remap_scrap_vehicles += entry.remap_scrap_vehicles;
  entry.total_remap_scrap_index += entry.remap_scrap_index;
  entry.total_untracked += entry.untracked;
  entry.total_rail += entry.rail;
  entry.total_road += entry.road;
  entry.total_air += entry.air;
  entry.total_water += entry.water;
  entry.total_unknown += entry.unknown;
  OpexC52AutoreplaceLog("phase=summary year=" + year + " events=" + entry.total_events
      + " remap_line_vehicles=" + entry.total_remap_line_vehicles
      + " remap_line_vehicle=" + entry.total_remap_line_vehicle
      + " remap_scrap_vehicles=" + entry.total_remap_scrap_vehicles
      + " remap_scrap_index=" + entry.total_remap_scrap_index
      + " untracked=" + entry.total_untracked + " rail=" + entry.total_rail
      + " road=" + entry.total_road + " air=" + entry.total_air
      + " water=" + entry.total_water + " unknown=" + entry.total_unknown);
  C52_AUTOREPLACE_LEDGER = {
    events = 0, remap_line_vehicles = 0, remap_line_vehicle = 0, remap_scrap_vehicles = 0,
    remap_scrap_index = 0, untracked = 0, rail = 0, road = 0, air = 0, water = 0, unknown = 0,
    line_rail = 0, line_road = 0, line_air = 0, line_water = 0,
    total_events = entry.total_events, total_remap_line_vehicles = entry.total_remap_line_vehicles,
    total_remap_line_vehicle = entry.total_remap_line_vehicle,
    total_remap_scrap_vehicles = entry.total_remap_scrap_vehicles,
    total_remap_scrap_index = entry.total_remap_scrap_index, total_untracked = entry.total_untracked,
    total_rail = entry.total_rail, total_road = entry.total_road, total_air = entry.total_air,
    total_water = entry.total_water, total_unknown = entry.total_unknown,
  };
}
function OpexC52EventExposureFields(fields, values)
{
  local text = "";
  foreach (field in fields) text += " " + field + "=" + values[field];
  return text;
}
/* C52 : le report de debut d'annee publie la fenetre ecoulee, puis conserve son cumul. */
function OpexAI::_logC52EventExposureLedger(year)
{
  if (!C52_EVENT_EXPOSURE_PROBE || C52_EVENT_EXPOSURE_LEDGER == null) return;
  local entry = C52_EVENT_EXPOSURE_LEDGER;
  entry.vehicle_unprofitable_distinct = entry.unprofitable_vehicles.len();
  OpexC52EventExposureLog("phase=annual year=" + year
                          + OpexC52EventExposureFields(entry.fields, entry));
  foreach (field in entry.fields) entry.totals[field] += entry[field];
  OpexC52EventExposureLog("phase=summary year=" + year
                          + OpexC52EventExposureFields(entry.fields, entry.totals));
  C52_EVENT_EXPOSURE_LEDGER = {
    fields = entry.fields, totals = entry.totals, unprofitable_vehicles = {},
    vehicle_crashed = 0, crashed_train = 0, crashed_other = 0, vehicle_waiting_in_depot = 0,
    industry_open = 0, industry_close = 0, town_founded = 0, engine_available = 0,
    vehicle_lost = 0, subsidy_offer = 0, subsidy_offer_expired = 0, subsidy_awarded = 0,
    subsidy_expired = 0, vehicle_autoreplaced = 0, vehicle_unprofitable = 0,
    vehicle_unprofitable_distinct = 0, aircraft_dest_too_far = 0, station_first_vehicle = 0,
    road_reconstruction = 0, engine_preview = 0, exclusive_transport_rights = 0, other = 0,
  };
}
/* La tache "report" publie au premier passage de l'annee suivante : year=1971 decrit donc
 * l'annee de jeu 1970, et la derniere annee de la partie n'est jamais publiee. Tous les appels
 * API couteux sont apres ce garde C54, afin que le defaut false n'atteigne aucune API ajoutee. */
function OpexAI::_logC54VehicleOrders(year)
{
  if (!C54_VEHICLE_ORDERS_PROBE) return;
  local vehicles = AIVehicleList();
  foreach (vehicle, _ in vehicles) {
    local vehicleType = AIVehicle.GetVehicleType(vehicle);
    local mode = vehicleType == AIVehicle.VT_RAIL ? "rail"
        : vehicleType == AIVehicle.VT_ROAD ? "road"
        : vehicleType == AIVehicle.VT_AIR ? "air"
        : vehicleType == AIVehicle.VT_WATER ? "water" : "invalid";
    local orders = AIOrder.GetOrderCount(vehicle);
    local destinations = {};
    for (local position = 0; position < orders; position++) {
      /* IsGotoStationOrder exclut depot, waypoint et conditionnel avant GetOrderDestination. */
      if (!AIOrder.IsGotoStationOrder(vehicle, position)) continue;
      local destination = AIOrder.GetOrderDestination(vehicle, position);
      destinations.rawset(destination, true);
    }
    local line = OpexC41PersistedLineForVehicle(this._lines, vehicle);
    local lineId = line != null && ("lineId" in line) ? line.lineId : -1;
    /* GetProfit* est en livres reelles via API, contrairement a VEHS (~256 x livres). */
    OpexC54VehicleOrdersLog("phase=vehicle year=" + year + " vid=" + vehicle
        + " mode=" + mode + " engine=" + AIVehicle.GetEngineType(vehicle)
        + " age=" + AIVehicle.GetAge(vehicle) + " max_age=" + AIVehicle.GetMaxAge(vehicle)
        + " orders=" + orders + " distinct_dest=" + destinations.len()
        + " profit_last=" + AIVehicle.GetProfitLastYear(vehicle)
        + " profit_this=" + AIVehicle.GetProfitThisYear(vehicle)
        + " in_depot=" + (AIVehicle.IsStoppedInDepot(vehicle) ? 1 : 0)
        + " line=" + lineId);
  }
}
/* C48.1 : tous les compteurs de volume sont explicites dans chaque ligne :
 * lines = lines.len() a l'entree (total), groups/projects_scanned/retained = rejeu des groupes,
 * fleet_plan = elements lus, air_plans = plans produits,
 * alternatives/selected = entree/sortie de la selection. Les champs non pertinents a une phase
 * valent zero. La tache report publie au premier passage de l'annee suivante : year=1971 decrit
 * 1970 et la derniere annee n'est jamais publiee (~82 % de couverture sur six ans). */
function OpexC48IncrementalRecord(step, ops, days, lines, groups, projectsScanned, retained,
                                  fleetPlan, airPlans, alternatives, selected)
{
  if (!C48_INCREMENTAL_PROFILE) return;
  if (C48_INCREMENTAL_LEDGER == null) C48_INCREMENTAL_LEDGER = {};
  local entry = (step in C48_INCREMENTAL_LEDGER) ? C48_INCREMENTAL_LEDGER[step]
      : { calls = 0, ops = 0, days = 0, lines = 0, groups = 0, projectsScanned = 0,
          retained = 0, fleetPlan = 0, airPlans = 0, alternatives = 0,
          selected = 0 };
  entry.calls++;
  entry.ops += ops;
  entry.days += days;
  entry.lines += lines;
  entry.groups += groups;
  entry.projectsScanned += projectsScanned;
  entry.retained += retained;
  entry.fleetPlan += fleetPlan;
  entry.airPlans += airPlans;
  entry.alternatives += alternatives;
  entry.selected += selected;
  C48_INCREMENTAL_LEDGER.rawset(step, entry);
}
function OpexAI::_logC48IncrementalLedger(year)
{
  if (!C48_INCREMENTAL_PROFILE) return;
  /* Une ligne pour CHACUNE des six phases, meme si une garde fonctionnelle n'a produit aucun
   * appel cette annee : le depouillement distingue ainsi zero de "phase absente du journal". */
  local steps = ["tension_ctx", "groups_replay", "fleet", "air", "selection", "total"];
  foreach (step in steps) {
    local entry = (C48_INCREMENTAL_LEDGER != null && (step in C48_INCREMENTAL_LEDGER))
        ? C48_INCREMENTAL_LEDGER[step]
        : { calls = 0, ops = 0, days = 0, lines = 0, groups = 0, projectsScanned = 0,
            retained = 0, fleetPlan = 0, airPlans = 0, alternatives = 0,
            selected = 0 };
    OpexC48IncrementalLog("phase=annual year=" + year + " step=" + step
        + " calls=" + entry.calls + " ops=" + entry.ops + " days=" + entry.days
        + " lines=" + entry.lines + " groups=" + entry.groups
        + " projects_scanned=" + entry.projectsScanned + " retained=" + entry.retained
        + " fleet_plan=" + entry.fleetPlan
        + " air_plans=" + entry.airPlans + " alternatives=" + entry.alternatives
        + " selected=" + entry.selected);
  }
  C48_INCREMENTAL_LEDGER = null;
}

/* C69 etape 1 : enregistrement et publication a chaque passe qui construit */
function OpexAI::_recordC69BuildingPass(year, projects, builtProjects)
{
  if (!C69_BOTTLENECK_PROBE) return;
  if (C69_BUILD_DATES == null) C69_BUILD_DATES = [];
  if (C69_PENDING_FOLLOWUPS == null) C69_PENDING_FOLLOWUPS = [];

  local now = AIDate.GetCurrentDate();
  if (builtProjects != null) {
    foreach (p in builtProjects) {
      C69_BUILD_DATES.append(now);
    }
  }

  local builtKeys = {};
  if (builtProjects != null) {
    foreach (p in builtProjects) {
      builtKeys[OpexC69AttemptKey(p)] <- true;
    }
  }

  /* Evaluer les suivis C3 en attente des passes precedentes */
  local activeFollowups = [];
  foreach (item in C69_PENDING_FOLLOWUPS) {
    item.passesWaited++;
    if (item.c69Key in builtKeys) {
      item.builtNext = 1;
      item.resolved = true;
      OpexC69Log("phase=c3_check pass=" + item.passId + " built_next=1 passes_waited=" + item.passesWaited + " target=" + item.c69Key);
    } else if (item.passesWaited >= item.maxPasses) {
      item.builtNext = 0;
      item.resolved = true;
      OpexC69Log("phase=c3_check pass=" + item.passId + " built_next=0 passes_waited=" + item.passesWaited + " target=" + item.c69Key);
    } else {
      activeFollowups.append(item);
    }
  }
  C69_PENDING_FOLLOWUPS = activeFollowups;

  /* Evaluer et journaliser la passe courante */
  if (projects == null || !("best" in projects) || projects.best == null || projects.best.len() == 0) {
    return;
  }

  local actualTop = projects.best[0];
  local c69Top = (("c69Best" in projects) && projects.c69Best != null && projects.c69Best.len() > 0)
      ? projects.c69Best[0] : actualTop;

  local c69RankInActual = -1;
  local c69Key = OpexC69AttemptKey(c69Top);
  for (local r = 0; r < projects.best.len(); r++) {
    if (OpexC69AttemptKey(projects.best[r]) == c69Key) {
      c69RankInActual = r;
      break;
    }
  }

  local kData = (("c69KDecData" in projects) && projects.c69KDecData != null)
      ? projects.c69KDecData : OpexC69ComputeKDec();
  local fVeh = OpexC69VehicleProfitLastYear();

  C69_BUILD_PASS_COUNT++;
  local passId = C69_BUILD_PASS_COUNT;
  local actualCap = OpexProjectFinanceCapital(actualTop);
  local c69Cap = OpexProjectFinanceCapital(c69Top);
  local diff = (c69RankInActual != 0) ? 1 : 0;

  OpexC69Log("phase=build pass=" + passId + " year=" + year
      + " F=" + kData.F + " F_veh=" + fVeh + " tau=" + kData.tau + " K_dec=" + kData.K_dec
      + " actual_mode=" + actualTop.mode + " actual_P=" + actualTop.profitAnnual
      + " actual_C=" + actualCap
      + " c69_mode=" + c69Top.mode + " c69_P=" + c69Top.profitAnnual
      + " c69_C=" + c69Cap
      + " c69_rank_in_actual=" + c69RankInActual
      + " diff=" + diff);

  if (diff == 1) {
    if (c69Key in builtKeys) {
      OpexC69Log("phase=c3_check pass=" + passId + " built_next=1 passes_waited=0 target=" + c69Key);
    } else {
      C69_PENDING_FOLLOWUPS.append({
        passId = passId,
        c69Key = c69Key,
        passesWaited = 0,
        maxPasses = 2,
        resolved = false,
        builtNext = 0
      });
    }
  }
}
