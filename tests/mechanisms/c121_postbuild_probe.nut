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