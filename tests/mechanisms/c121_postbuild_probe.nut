/* Diagnostic in a copied AI only. No policy flag, snapshot or Save() mutation. */
PB_SEQ <- 0;
PB_PASS <- 0;
PB_STATE <- null;

function PBLog(edge, tail = "")
{
  PB_SEQ++;
  local day = AIDate.GetCurrentDate();
  local tick = AIController.GetTick();
  AILog.Info("POSTBUILD v=1 seq=" + PB_SEQ + " pass=" + PB_PASS
      + " edge=" + edge + " day=" + day + " tick=" + tick + tail);
}

function PBDispatch(owner)
{
  PBLog("dispatch", " invalidated=" + (owner._portfolioInvalidated ? 1 : 0)
      + " best=" + (owner._projects != null ? owner._projects.best.len() : -1)
      + " rail=" + (owner._railSearch != null ? owner._railSearch.phase : "none"));
}

function PBBegin(owner)
{
  PB_PASS++;
  PB_STATE = { dead = 0, outcomes = 0, built = 0 };
  PBLog("pass_begin", " stage=" + owner._generationStage);
}

function PBEnd(reason)
{
  PBLog("pass_end", " reason=" + (reason != null ? reason : "none")
      + " dead=" + PB_STATE.dead + " outcomes=" + PB_STATE.outcomes
      + " built=" + PB_STATE.built);
  PB_STATE = null;
}

function PBOutcome(project, rank, outcome)
{
  PB_STATE.outcomes++;
  if (outcome == "built") PB_STATE.built++;
  PBLog("outcome", " mode=" + project.mode + " rank=" + rank
      + " outcome=" + outcome);
}

function PBKPassStop(owner, project, rank, finance, kPass, availCap)
{
  if (project == null) return;
  local available = availCap >= 0 ? availCap : OpexAvailableCapital();
  local lineId = -1;
  if (("mode" in project) && project.mode == "fleet"
      && ("payload" in project) && project.payload != null
      && ("line" in project.payload) && project.payload.line != null
      && ("lineId" in project.payload.line)) {
    lineId = project.payload.line.lineId;
  }
  PBLog("kpass_stop", " next_mode=" + project.mode + " rank=" + rank
      + " line_id=" + lineId + " finance=" + finance + " k_pass=" + kPass
      + " available=" + available);
  if (project.mode != "fleet" || owner._projects == null || owner._projects.best == null) return;
  for (local j = rank + 1; j < owner._projects.best.len(); j++) {
    local tail = owner._projects.best[j];
    if (tail == null) continue;
    local tailFinance = OpexProjectFinanceCapital(tail);
    PBLog("kpass_tail", " stop_rank=" + rank + " rank=" + j + " mode=" + tail.mode
        + " finance=" + tailFinance + " affordable=" + (tailFinance <= available ? 1 : 0)
        + " below_kpass=" + (tailFinance < kPass ? 1 : 0));
  }
}

function PBPhaseBegin(kind)
{
  PBLog("phase_begin", " kind=" + kind);
  return { day = AIDate.GetCurrentDate(), mark = OpexOpsMeasureBegin(), kind = kind };
}

function PBPhaseEnd(state)
{
  local ops = OpexOpsMeasureEnd(state.mark);
  local tick = AIController.GetTick();
  local day = AIDate.GetCurrentDate();
  PBLog("phase_end", " kind=" + state.kind + " start_day=" + state.day
      + " end_day=" + day + " start_tick=" + state.mark.tick + " end_tick=" + tick
      + " ops=" + ops);
}
