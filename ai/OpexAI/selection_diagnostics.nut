/* Diagnostics transitoires. Aucun resultat ne revient dans le portefeuille.
 * Requis par projects_selection, helpers appeles seulement apres settings. */
SELECTION_LIGHT_SEQ <- 0;

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
