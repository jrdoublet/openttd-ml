from pathlib import Path
p=Path("ai/OpexAI/projects.nut")
s=p.read_text(encoding="utf-8")
if "function OpexSelectionLedgerRecordCause" not in s:
    anchor="function OpexCapitalFrontierAssignScores(alternatives, capitalBudget, catalog = null, lines = null)\n"
    helper=r'''function OpexSelectionLedgerRecordCause(cause, diagnostic, ops, days)
{
  if (!(AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT)) return;
  if (ops < 0) ops = 0;
  if (days < 0) days = 0;
  AIR_SELECTION_LEDGER.calls++;
  if (diagnostic) {
    AIR_SELECTION_LEDGER.diagnosticCalls++;
    AIR_SELECTION_LEDGER.diagnosticOps += ops;
    AIR_SELECTION_LEDGER.diagnosticDays += days;
    if (cause == "diagnostic_counterfactual") AIR_SELECTION_LEDGER.diagnosticCounterfactualCalls++;
    return;
  }
  AIR_SELECTION_LEDGER.productionCalls++;
  AIR_SELECTION_LEDGER.productionOps += ops;
  AIR_SELECTION_LEDGER.productionDays += days;
  if (cause == "generation") {
    AIR_SELECTION_LEDGER.generationCalls++; AIR_SELECTION_LEDGER.generationOps += ops; AIR_SELECTION_LEDGER.generationDays += days;
  } else if (cause == "lifecycle") {
    AIR_SELECTION_LEDGER.lifecycleCalls++; AIR_SELECTION_LEDGER.lifecycleOps += ops; AIR_SELECTION_LEDGER.lifecycleDays += days;
  } else if (cause == "budget_reselect") {
    AIR_SELECTION_LEDGER.budgetReselectCalls++; AIR_SELECTION_LEDGER.budgetReselectOps += ops; AIR_SELECTION_LEDGER.budgetReselectDays += days;
  } else if (cause == "dynamic_batch") {
    AIR_SELECTION_LEDGER.dynamicBatchCalls++; AIR_SELECTION_LEDGER.dynamicBatchOps += ops; AIR_SELECTION_LEDGER.dynamicBatchDays += days;
  } else if (cause == "execution") {
    AIR_SELECTION_LEDGER.executionCalls++; AIR_SELECTION_LEDGER.executionOps += ops; AIR_SELECTION_LEDGER.executionDays += days;
  }
}

function OpexSelectionLedgerRecordPhase(phase, diagnostic, ops, days)
{
  if (!(AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT)) return;
  if (ops < 0) ops = 0;
  if (days < 0) days = 0;
  if (diagnostic) {
    if (phase == "externality") { AIR_SELECTION_LEDGER.diagnosticExternalityOps += ops; AIR_SELECTION_LEDGER.diagnosticExternalityDays += days; }
    else if (phase == "relaxation") { AIR_SELECTION_LEDGER.diagnosticRelaxationOps += ops; AIR_SELECTION_LEDGER.diagnosticRelaxationDays += days; }
    else if (phase == "ranking") { AIR_SELECTION_LEDGER.diagnosticRankingOps += ops; AIR_SELECTION_LEDGER.diagnosticRankingDays += days; }
    return;
  }
  if (phase == "externality") { AIR_SELECTION_LEDGER.externalityOps += ops; AIR_SELECTION_LEDGER.externalityDays += days; }
  else if (phase == "relaxation") { AIR_SELECTION_LEDGER.relaxationOps += ops; AIR_SELECTION_LEDGER.relaxationDays += days; }
  else if (phase == "ranking") { AIR_SELECTION_LEDGER.rankingOps += ops; AIR_SELECTION_LEDGER.rankingDays += days; }
}

'''
    assert anchor in s
    s=s.replace(anchor,helper+anchor,1)
old='''function OpexCapitalFrontierAssignScores(alternatives, capitalBudget, catalog = null, lines = null)
{
  local phaseMark = AIR_CAPITAL_FRONTIER_PROBE ? OpexOpsMeasureBegin() : null;
  local selectionDate = AIDate.GetCurrentDate();'''
new='''function OpexCapitalFrontierAssignScores(alternatives, capitalBudget, catalog = null, lines = null,
                                         selectionDiagnostic = false)
{
  local measurePhases = AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT;
  local phaseMark = measurePhases ? OpexOpsMeasureBegin() : null;
  local phaseDate = measurePhases ? AIDate.GetCurrentDate() : 0;
  local selectionDate = AIDate.GetCurrentDate();'''
assert old in s
s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")
