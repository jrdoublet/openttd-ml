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

/* AIR-ROI-RENFORT-1 / etape 2a : aucune nouvelle lecture d'etat physique
 * (API stations, vehicules, concurrent). Chaque valeur a son origine propre.
 * Les 2 messages PRE/CONTEXT sont construits avant l'achat, mais publies
 * APRES pour eviter la suspension due aux logs dans le tick transactionnel. */
function OpexAirR1Cell(key, value, origin)
{
  return " " + key + "=" + (value == null ? "na" : value)
      + " " + key + "_src=" + (value == null ? "missing" : origin);
}

function OpexAirR1Before(ai, project, rank)
{
  if (!AIR_ROI_RENFORT1_SHADOW || project == null || project.payload == null) return null;
  local entry = project.payload;
  local line = entry.line;
  if (line == null || !("lineId" in line)) return null;
  local now = AIDate.GetCurrentDate();
  local last = (line.lineId in AIR_ROI_RENFORT1_LAST)
      ? AIR_ROI_RENFORT1_LAST[line.lineId] : null;
  if (last != null && now - last >= 0 && now - last < 30) return null;
  AIR_ROI_RENFORT1_LAST.rawset(line.lineId, now);
  local tick = AIController.GetTick();
  local id = tick + "-" + ai._taskCycle + "-reinforce-" + line.lineId;
  local stamp = "id=" + id + " tick_pre=" + tick + " date_pre=" + now;
  local pre = stamp + " rank=" + rank;
  pre += OpexAirR1Cell("baseVehicles", ("baseVehicles" in entry) ? entry.baseVehicles : null, "plan_before");
  pre += OpexAirR1Cell("vehCount", ("vehCount" in line) ? line.vehCount : null, "line_before");
  pre += OpexAirR1Cell("want", ("want" in entry) ? entry.want : null, "plan_before");
  pre += OpexAirR1Cell("target", ("targetAirPlanes" in line) ? line.targetAirPlanes : null, "line_before");
  pre += OpexAirR1Cell("physicalMax", ("airR1PhysicalMax" in entry) ? entry.airR1PhysicalMax : null, "plan_before");
  pre += OpexAirR1Cell("planeCapacity", ("planeCapacity" in line) ? line.planeCapacity : null, "line_cached_before");
  pre += OpexAirR1Cell("waitPaxA", null, "missing");
  pre += OpexAirR1Cell("waitPaxB", null, "missing");
  pre += OpexAirR1Cell("waitMailA", null, "missing");
  pre += OpexAirR1Cell("waitMailB", null, "missing");
  pre += OpexAirR1Cell("airportOccupancy", null, "missing");
  pre += OpexAirR1Cell("pickupRate", null, "missing");
  pre += OpexAirR1Cell("lastHistoricalCycleDays", null, "missing");
  pre += OpexAirR1Cell("airportWaitDays", null, "missing");
  local context = stamp;
  context += OpexAirR1Cell("buildDate", ("buildDate" in line) ? line.buildDate : null, "line_historical");
  context += OpexAirR1Cell("lineAgeDays", ("buildDate" in line) ? now - line.buildDate : null, "derived_from_buildDate");
  context += OpexAirR1Cell("baseYear", ("year" in line) ? line.year : null, "line_historical");
  context += OpexAirR1Cell("lastFleetDate", ("lastAirFleetDate" in line) ? line.lastAirFleetDate : null, "line_historical");
  context += OpexAirR1Cell("marginalSamples", ("c121MarginalSamples" in line) ? line.c121MarginalSamples : null, "line_before");
  context += OpexAirR1Cell("coldStart", ("c121MarginalSamples" in line)
      ? (line.c121MarginalSamples <= 0 ? 1 : 0) : null, "derived_from_samples");
  context += OpexAirR1Cell("economicWindowYears", null, "missing");
  context += OpexAirR1Cell("v161Neighbours", ("v161Neighbours" in entry) ? entry.v161Neighbours : null, "plan_before");
  context += OpexAirR1Cell("v161Amort", ("c121VehicleAmortPerPlane" in line)
      ? line.c121VehicleAmortPerPlane : null, "line_cached_before");
  context += OpexAirR1Cell("ownedRoutesA", null, "missing");
  context += OpexAirR1Cell("ownedRoutesB", null, "missing");
  context += OpexAirR1Cell("rivalCapacity", null, "missing");
  context += OpexAirR1Cell("c121Arm", ("c121Arm" in line) ? line.c121Arm : null, "line_historical");
  context += OpexAirR1Cell("cargo", ("cargo" in line) ? line.cargo : null, "line_before");
  context += OpexAirR1Cell("stationA", ("stationA" in line) ? line.stationA : null, "line_before");
  context += OpexAirR1Cell("stationB", ("stationB" in line) ? line.stationB : null, "line_before");
  context += OpexAirR1Cell("refleetEngine", ("refleetEngine" in line) ? line.refleetEngine : null, "line_cached_before");
  context += OpexAirR1Cell("c77Tier", ("_bsTier" in project) ? project._bsTier : null, "selection_cached");
  context += OpexAirR1Cell("c77Stamp", ("_bsStamp" in project) ? project._bsStamp : null, "selection_cached");
  context += OpexAirR1Cell("kDec", AIR_FLOTTE1_KDEC >= 0 ? AIR_FLOTTE1_KDEC : null, "selection_snapshot");
  context += OpexAirR1Cell("kDecTick", AIR_FLOTTE1_KDEC_TICK >= 0 ? AIR_FLOTTE1_KDEC_TICK : null, "selection_snapshot");
  context += OpexAirR1Cell("fundScore", ("fundScore" in project) ? project.fundScore : null, "selection_cached");
  context += OpexAirR1Cell("unitPrice", ("planePrice" in entry) ? entry.planePrice : null, "plan_before");
  return { id = id, tick = tick, pre = pre, context = context };
}

function OpexAirR1After(event, actualCost, added, replaced, reason)
{
  if (event == null) return;
  OpexDecide("AIRR1_PRE", event.pre);
  OpexDecide("AIRR1_CONTEXT", event.context);
  OpexDecide("AIRR1_OUTCOME", "id=" + event.id
      + " tick_pre=" + event.tick + " tick_after=" + AIController.GetTick()
      + OpexAirR1Cell("actualCost", actualCost, "accounting_transaction")
      + OpexAirR1Cell("added", added, "constructor_return")
      + OpexAirR1Cell("replaced", replaced, "constructor_return")
      + OpexAirR1Cell("reason", reason, "constructor_return"));
}

/* Amendement ITT du 22/10/2026. Une graine par monde, puis un hash borne
 * graine x lineId x numero d'episode. Chaque produit intermediaire reste
 * inferieur a 2^31 pour les VM Squirrel a entiers 32 bits. Aucun RNG au mode 0.
 * L'attribution est publiee AVANT toute commande OpexAirAddPlane. */
function OpexAirR1ITTSeed()
{
  if (AIR_ROI_RENFORT1_ITT_SEED >= 0) return AIR_ROI_RENFORT1_ITT_SEED;
  local gameSetting = "game_creation.generation_seed";
  if (AIGameSettings.IsValid(gameSetting)) {
    AIR_ROI_RENFORT1_ITT_SEED = AIGameSettings.GetValue(gameSetting) % 1000003;
    if (AIR_ROI_RENFORT1_ITT_SEED < 0) AIR_ROI_RENFORT1_ITT_SEED += 1000003;
    AIR_ROI_RENFORT1_ITT_SEED_SOURCE = "world_setting";
  } else {
    AIR_ROI_RENFORT1_ITT_SEED = AIBase.RandRange(1000003);
    AIR_ROI_RENFORT1_ITT_SEED_SOURCE = "ai_rng_first_eligible";
  }
  return AIR_ROI_RENFORT1_ITT_SEED;
}

function OpexAirR1ITTBlocked(line)
{
  if (AIR_ROI_RENFORT1_ITT == 0 || line == null || !("lineId" in line)) return false;
  if (!(line.lineId in AIR_ROI_RENFORT1_ITT_LINES)) return false;
  local state = AIR_ROI_RENFORT1_ITT_LINES[line.lineId];
  return state != null && ("blockedUntil" in state)
      && state.blockedUntil > AIDate.GetCurrentDate();
}

/* Releve passif par VehicleID : le profit NoAI est NET des frais de roulage des
 * avions, mais n'inclut pas les depenses d'infrastructure. Ni recette brute ni
 * maintenance distincte ne sont exposees par cette API : la recette ci-dessous
 * sera une reconstruction approximative (profit + cout de roulage prorate). */
function OpexAirR1ITTCheckpoint(line)
{
  local values = {};
  /* Sans inventaire de VehicleID propre a la ligne, une gare partagee
   * rendrait l'attribution non identifiable. */
  if (!("vehicles" in line) || line.vehicles == null) return null;
  local station = AIStation.GetStationID(line.stationA);
  if (!AIStation.IsValidStation(station)) return null;
  foreach (v in OpexLineVehicleIds(line, station)) {
    if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetVehicleType(v) != AIVehicle.VT_AIR) continue;
    values.rawset("" + v, { year = AIDate.GetYear(AIDate.GetCurrentDate()),
        profit = AIVehicle.GetProfitThisYear(v), last = AIVehicle.GetProfitLastYear(v),
        running = AIVehicle.GetRunningCost(v), age = AIVehicle.GetAge(v) });
  }
  return values;
}

function OpexAirR1ITTMonthDate(start, offset)
{
  local year = AIDate.GetYear(start);
  local month = AIDate.GetMonth(start) + offset;
  year += (month - 1) / 12;
  month = ((month - 1) % 12) + 1;
  local lastDay = AIDate.GetDate(year, month, 1);
  if (month == 12) lastDay = AIDate.GetDate(year + 1, 1, 1) - 1;
  else lastDay = AIDate.GetDate(year, month + 1, 1) - 1;
  local day = AIDate.GetDayOfMonth(start);
  local maxDay = AIDate.GetDayOfMonth(lastDay);
  return AIDate.GetDate(year, month, day < maxDay ? day : maxDay);
}

function OpexAirR1ITTObserve(ai)
{
  if (AIR_ROI_RENFORT1_ITT == 0 || ai._lines == null) return;
  local now = AIDate.GetCurrentDate();
  if (AIR_ROI_RENFORT1_ITT_LAST_SAMPLE_DATE == now) return;
  AIR_ROI_RENFORT1_ITT_LAST_SAMPLE_DATE = now;
  local seen = {};
  foreach (line in ai._lines) {
    if (line != null && ("lineId" in line)) seen.rawset(line.lineId, true);
    if (line == null || !("lineId" in line) || !(line.lineId in AIR_ROI_RENFORT1_ITT_LINES)) continue;
    local state = AIR_ROI_RENFORT1_ITT_LINES[line.lineId];
    if (!("track" in state) || state.track == null) continue;
    local tr = state.track;
    if (tr.month >= 24) continue;
    local due = OpexAirR1ITTMonthDate(tr.start, tr.month + 1);
    if (now < due) continue;
    local current = OpexAirR1ITTCheckpoint(line);
    local days = now - tr.lastDate;
    local profit = 0;
    local running = 0.0;
    /* L'intervalle est juge independamment de l'historique. Une lacune
     * ancienne ne masque pas une fenetre ulterieure redevenue mesurable. */
    local valid = true;
    local fail = "none";
    if (current == null) { valid = false; fail = "missing_inventory_or_station"; }
    else if (days < 18 || days > 42) { valid = false; fail = "interval_days_out_of_range"; }
    else if (now - due > 14) { valid = false; fail = "checkpoint_lag_over_14_days"; }
    local count = current != null ? current.len() : 0;
    if (current != null) {
      foreach (id, item in current) {
        if (id in tr.previous) {
          local before = tr.previous[id];
          if (item.year == before.year) profit += item.profit - before.profit;
          else if (item.year == before.year + 1)
            profit += item.last - before.profit + item.profit;
          else { valid = false; fail = "profit_year_gap"; }
        } else {
          /* Un appareil ne de ce mois a un compteur YTD utilisable. Un
           * transfert ancien serait ambigu et invalide l'intervalle. */
          if (item.age > days + 2) { valid = false; fail = "untracked_vehicle_join"; }
          else profit += item.profit;
        }
        running += item.running.tofloat() * days.tofloat() / 365.25;
      }
      foreach (id, before in tr.previous) {
        if (!(id in current)) { valid = false; fail = "vehicle_sold_or_lost"; }
      }
    }
    tr.month++;
    tr.complete = valid;
    tr.previous = current != null ? current : {};
    tr.lastDate = now;
    OpexDecide("AIRR1_ITT_MONTH", "id=" + tr.id + " seed=" + AIR_ROI_RENFORT1_ITT_SEED
        + " line=" + line.lineId + " month_offset=" + tr.month
        + " complete=" + (valid ? 1 : 0) + " interval_valid=" + (valid ? 1 : 0)
        + " fail_reason=" + fail + " date_due=" + due
        + " date_actual=" + now + " days=" + days + " aircraft=" + count
        + " vehicle_net_profit_gbp=" + profit
        + " running_cost_est_gbp=" + running
        + " revenue_est_gbp=" + (profit + running)
        + " maintenance_gbp=na residual_value_gbp=na"
        + " scope=vehicle_operating_no_infrastructure");
  }
  foreach (lineId, state in AIR_ROI_RENFORT1_ITT_LINES) {
    if (lineId in seen || state == null || !("track" in state) || state.track == null) continue;
    local tr = state.track;
    if (tr.month >= 24 || now < OpexAirR1ITTMonthDate(tr.start, tr.month + 1)) continue;
    OpexDecide("AIRR1_ITT_CENSOR", "id=" + tr.id + " seed=" + AIR_ROI_RENFORT1_ITT_SEED
        + " line=" + lineId + " month_offset=" + (tr.month + 1)
        + " date_actual=" + now + " reason=line_missing");
    tr.month = 24;
    tr.complete = false;
  }
}

function OpexAirR1ITTAssign(ai, project, rank)
{
  if (AIR_ROI_RENFORT1_ITT == 0 || project == null || project.payload == null) return null;
  local entry = project.payload;
  local line = entry.line;
  if (line == null || !("lineId" in line)) return null;
  local now = AIDate.GetCurrentDate();
  local state = (line.lineId in AIR_ROI_RENFORT1_ITT_LINES)
      ? AIR_ROI_RENFORT1_ITT_LINES[line.lineId] : null;
  /* Deux episodes d'une meme ligne ne doivent pas partager leur fenetre de
   * suivi primaire. Si la premiere est traitee, les renforts naturels restent
   * autorises ; s'ils sont differes, ils sont bloques pendant 732 jours. */
  if (state != null && ("nextEligible" in state) && now < state.nextEligible) return null;
  if (state != null && ("track" in state) && state.track != null
      && state.track.month < 24) return null;
  local seq = state != null && ("seq" in state) ? state.seq + 1 : 1;
  local seed = OpexAirR1ITTSeed();
  local lineNum = line.lineId % 10000;
  local episodeNum = seq % 10000;
  local h = (seed * 1201 + lineNum * 7919 + 123457) % 1000003;
  h = (h * 1201 + episodeNum * 7793 + 54321) % 1000003;
  h = (h * 1201 + 98711) % 1000003;
  local p = AIR_ROI_RENFORT1_ITT == 2 ? 50 : 0;
  local deferred = p == 50 && h < 500001;
  local untilDate = now + 732;
  local tick = AIController.GetTick();
  local id = tick + "-" + ai._taskCycle + "-reinforce-" + line.lineId + "-" + seq;
  local checkpoint = OpexAirR1ITTCheckpoint(line);
  AIR_ROI_RENFORT1_ITT_LINES.rawset(line.lineId,
      { seq = seq, nextEligible = untilDate, blockedUntil = deferred ? untilDate : -1,
        track = { id = id, start = now, lastDate = now, month = 0,
          complete = checkpoint != null, previous = checkpoint != null ? checkpoint : {} } });
  local have = ("vehCount" in line) ? line.vehCount : (("vehicles" in line) ? line.vehicles.len() : 0);
  local target = ("targetAirPlanes" in line) ? line.targetAirPlanes : -1;
  local arm = deferred ? "deferred" : "treatment";
  OpexDecide("AIRR1_ITT_ASSIGN", "episode=" + id + " id=" + id
      + " line=" + line.lineId + " seq=" + seq + " seed=" + seed
      + " seed_src=" + AIR_ROI_RENFORT1_ITT_SEED_SOURCE
      + " hash=" + h + " p=" + p + " arm=" + arm
      + " tick=" + tick + " date_pre=" + now + " rank=" + rank
      + " baseline=" + have + " vehicles_before=" + have
      + " want=" + entry.want + " target=" + target
      + " saturation=" + ((target > 0 && have >= target) ? 1 : 0)
      + " kind=" + (("c121Arm" in line) ? line.c121Arm : "na")
      + " cargo=" + (("cargo" in line) ? line.cargo : -1)
      + " station_a=" + (("stationA" in line) ? line.stationA : -1)
      + " station_b=" + (("stationB" in line) ? line.stationB : -1)
      + " last_profit=" + (("lastProfit" in line) ? line.lastProfit : "na")
      + " last_profit_src=line_cached_last_report"
      + " v161_source=" + (("v161Source" in project) ? project.v161Source : "na")
      + " v161_model=" + (("v161ModelPerPlane" in project) ? project.v161ModelPerPlane : "na")
      + " predicted_profit=" + (("profitAnnual" in project) ? project.profitAnnual : "na")
      + " roi=" + (("roi" in project) ? project.roi : "na")
      + " cash_before=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF)
      + " quote=" + entry.planePrice + " until_date=" + untilDate);
  return { id = id, line = line.lineId, arm = arm, deferred = deferred,
           tick = tick, untilDate = untilDate };
}

function OpexAirR1ITTOutcome(event, added, replaced, reason, actualCost)
{
  if (event == null) return;
  OpexDecide("AIRR1_ITT_OUTCOME", "episode=" + event.id + " id=" + event.id
      + " line=" + event.line + " arm=" + event.arm
      + " tick=" + AIController.GetTick() + " tick_before=" + event.tick
      + " added=" + added + " replaced=" + replaced
      + " reason=" + reason + " actual_cost=" + actualCost
      + " cash_after=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
}
