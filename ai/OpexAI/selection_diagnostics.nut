/* Diagnostics transitoires. Aucun resultat ne revient dans le portefeuille.
 * Requis par projects_selection, helpers appeles seulement apres settings. */
SELECTION_LIGHT_SEQ <- 0;
AMORT_PROBE_SEQ <- 0;

function OpexSelectionLightBegin()
{
  SELECTION_LIGHT_SEQ++;
  return { inv = SELECTION_LIGHT_SEQ, day = AIDate.GetCurrentDate(), tick = AIController.GetTick() };
}

function OpexSelectionLightEnd(mark, path, ops, considered, selected)
{
  local endDay = AIDate.GetCurrentDate();
  local endTick = AIController.GetTick();
  OpexDecide("SELECTION_LIGHT", "v=1 inv=" + mark.inv + " path=" + path
      + " start_day=" + mark.day + " end_day=" + endDay
      + " start_tick=" + mark.tick + " end_tick=" + endTick
      + " ops=" + ops + " considered=" + considered + " selected=" + selected);
}

function OpexAmortProbeBegin(budget)
{
  AMORT_PROBE_SEQ++;
  local supported = !C84_AIR_TARGET_FLEET && !C85_AIR_EQUIPMENT_FRONTIER
      && !C121_AIR_ECONOMICS && !C122_AIR_REGIME_PRIORITY && !C122_AIR_REGIME_SHADOW
      && !C118_AIR_TERRITORIAL_EXPANSION && !C120_AIR_TERRITORIAL_RANKING
      && !V92_AIR_SERVICE_CHOICE && C115_AIR_C100_CAPITAL_REPLAY
      && !EXP_C83_WATCH_DAILY && !EXP_SCHEDULER_SKIP_NOT_DUE && !EXP_AIR_HUB_PAIR_PREFILTER;
  return { id = AMORT_PROBE_SEQ, budget = budget, rows = [], originals = [],
      day = AIDate.GetCurrentDate(), tick = AIController.GetTick(), mark = OpexOpsMeasureBegin(),
      supported = supported, helperOps = 0, copyOps = 0, valid = supported };
}

function OpexAmortProbeCandidate(state, project, finance, denominator)
{
  if (!state.supported) return;
  local mark = OpexOpsMeasureBegin();
  local shadow = project.mode == "fleet" ? OpexFleetAmortShadow(project, true) : null;
  local calibrated = C70_PROFIT_CALIBRATED ? OpexCalibratedProfit(project) : project.profitAnnual;
  state.helperOps += OpexOpsMeasureEnd(mark);
  mark = OpexOpsMeasureBegin();
  local before = clone project;
  local after = clone project;
  local index = state.rows.len();
  before.amortProbeId <- "p" + index;
  after.amortProbeId <- before.amortProbeId;
  if (project.mode == "fleet" && shadow == null) state.valid = false;
  if (shadow != null) {
    /* Ne pas changer profitAnnual sur la copie de tri : priorite/admission figees.
     * Seul fundScore est alternatif ; le net est publie separement. */
    after.fundScore = OpexProjectScore(shadow.calibratedProfitAnnual, denominator);
  }
  local originalQuantity = 0;
  if (project.mode == "fleet") {
    originalQuantity = -1;
    foreach (entry in state.originals) if (entry.project == project) originalQuantity = entry.quantity;
  }
  local bonus = AIR_EARLY_SLOT && project.mode == "air" && ("earlySlotBonusPct" in project)
      ? project.earlySlotBonusPct : 0;
  state.rows.append({ before = before, after = after, live = project, shadow = shadow,
      calibrated = calibrated, finance = finance, denominator = denominator,
      factor = project.profitAnnual != 0 ? calibrated.tofloat() / project.profitAnnual : 1.0,
      bonus = bonus, original = originalQuantity,
      priority = OpexProjectDefensiveAirPriority(project)
          + ((V88_CHAIN_FORCE && OpexProjectIsForcedChain(project)) ? 1000 : 0) });
  state.copyOps += OpexOpsMeasureEnd(mark);
}

function OpexAmortProbeNumber(value)
{
  if (typeof value != "float" || value == 0.0) return value.tostring();
  /* NoAI n'expose pas la bibliotheque format(). Conserver neuf chiffres sans
   * tronquer les petits scores a six decimales ni deborder un entier 32 bits. */
  local magnitude = value < 0.0 ? -value : value;
  local exponent = 0;
  while (magnitude >= 10.0) { magnitude /= 10.0; exponent++; }
  while (magnitude < 1.0) { magnitude *= 10.0; exponent--; }
  return (value < 0.0 ? "-" : "") + (magnitude * 100000000.0).tointeger()
      + "e" + (exponent - 8);
}

function OpexAmortProbeOrder(projects)
{
  local result = "";
  foreach (project in projects) result += (result == "" ? "" : ",") + project.amortProbeId;
  return result == "" ? "none" : result;
}

function OpexAmortProbeEnd(state, affordable)
{
  local mark = OpexOpsMeasureBegin();
  local originalOrder = [];
  local shadowOrder = [];
  foreach (row in state.rows) {
    OpexProjectInsertDefensive(originalOrder, row.before, "fundScore", state.rows.len(), AIR_EARLY_SLOT);
    OpexProjectInsertDefensive(shadowOrder, row.after, "fundScore", state.rows.len(), AIR_EARLY_SLOT);
  }
  local orderMatches = originalOrder.len() >= affordable.len();
  for (local i = 0; i < affordable.len() && orderMatches; i++) {
    local rowIndex = originalOrder[i].amortProbeId.slice(1).tointeger();
    if (state.rows[rowIndex].live != affordable[i]) orderMatches = false;
  }
  state.copyOps += OpexOpsMeasureEnd(mark);
  local envelopeOps = OpexOpsMeasureEnd(state.mark);
  local endDay = AIDate.GetCurrentDate();
  local endTick = AIController.GetTick();
  local emitMark = OpexOpsMeasureBegin();
  if (FLEET_AMORT_SHADOW_PROBE == 2) {
    OpexDecide("FLEET_AMORT", "v=1 phase=begin id=" + state.id + " revision=1 day=" + state.day
        + " count=" + state.rows.len() + " budget=" + state.budget
        + " supported=" + (state.supported ? 1 : 0) + " calibrated=" + (C70_PROFIT_CALIBRATED ? 1 : 0));
    foreach (index, row in state.rows) {
      local p = row.before;
      local altProfit = row.shadow != null ? row.shadow.netProfitAnnual : p.profitAnnual;
      local altCalibrated = row.shadow != null ? row.shadow.calibratedProfitAnnual : row.calibrated;
      local category = p.mode == "fleet" ? "fleet_legacy"
          : ((p.mode == "air" || p.mode == "rail" || p.mode == "road" || p.mode == "water") ? "new_link" : "other_unchanged");
      local fields = "v=1 phase=candidate id=" + state.id + " candidate=" + p.amortProbeId
          + " index=" + index + " mode=" + p.mode + " category=" + category
          + " profit=" + p.profitAnnual + " net=" + altProfit
          + " calibrated=" + OpexAmortProbeNumber(row.calibrated)
          + " net_calibrated=" + OpexAmortProbeNumber(altCalibrated)
          + " score=" + OpexAmortProbeNumber(OpexProjectSelectionScore(p, "fundScore"))
          + " net_score=" + OpexAmortProbeNumber(OpexProjectSelectionScore(row.after, "fundScore"))
          + " finance=" + row.finance + " denominator=" + row.denominator
          + " factor=" + OpexAmortProbeNumber(row.factor) + " priority=" + row.priority
          + " bonus=" + row.bonus + " revenue=" + p.revenueAnnual
          + " original=" + row.original + " quantity=" + (p.mode == "fleet" ? p.payload.want : 0);
      if (p.mode == "fleet") {
        fields += " price=" + p.payload.planePrice
            + " observed=" + (("profitIsObserved" in p) && p.profitIsObserved ? 1 : 0)
            + " line=" + (("lineId" in p.payload.line) ? p.payload.line.lineId : -1)
            + " line_mode=" + p.payload.line.mode;
      }
      OpexDecide("FLEET_AMORT", fields);
    }
    OpexDecide("FLEET_AMORT", "v=1 phase=end id=" + state.id + " count=" + state.rows.len()
        + " complete=" + (state.valid && orderMatches ? 1 : 0)
        + " baseline=" + OpexAmortProbeOrder(originalOrder)
        + " alternative=" + OpexAmortProbeOrder(shadowOrder));
  }
  local emitOps = OpexOpsMeasureEnd(emitMark);
  /* Emission du bilan exclue du cout emit ; enveloppe = selection vivante + sonde,
   * pas le cout propre de la sonde. Sous-couts disjoints, ne pas les lui ajouter. */
  OpexDecide("FLEET_AMORT_COST", "v=1 id=" + state.id + " mode=" + FLEET_AMORT_SHADOW_PROBE
      + " count=" + state.rows.len() + " valid=" + (state.valid && orderMatches ? 1 : 0)
      + " order_matches=" + (orderMatches ? 1 : 0)
      + " helper_ops=" + state.helperOps + " copy_sort_ops=" + state.copyOps
      + " emit_ops=" + emitOps + " envelope_ops=" + envelopeOps
      + " days=" + (endDay - state.day) + " ticks=" + (endTick - state.tick));
}