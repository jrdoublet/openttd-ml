FXVC <- { calls = 0, quotes = 0, quoteOps = 0, cachedOps = 0, quoteTicks = 0, cachedTicks = 0, month = -1 };
function FxTLStart(ai) { }
function FxTLWorld(ai)
{
  local now = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(now)*12 + AIDate.GetMonth(now);
  if (FXVC.month == month) return;
  if (FXVC.month >= 0) AILog.Info("C121_VISIBLE_COST_MONTH visible=" + (C121_AIR_VISIBLE_COMPETITION ? 1 : 0)
      + " month=" + FXVC.month + " calls=" + FXVC.calls + " quotes=" + FXVC.quotes
      + " quote_ops=" + FXVC.quoteOps + " cached_ops=" + FXVC.cachedOps
      + " quote_ticks=" + FXVC.quoteTicks + " cached_ticks=" + FXVC.cachedTicks);
  FXVC = { calls = 0, quotes = 0, quoteOps = 0, cachedOps = 0, quoteTicks = 0, cachedTicks = 0, month = month };
}
function OpexC121RefreshVisibleFleet(catalog, line, lines, force = false)
{
  local old = line != null && ("lineId" in line) && line.lineId in C121_VISIBLE_FLEET_CACHE
      ? C121_VISIBLE_FLEET_CACHE[line.lineId] : null;
  local tick = AIController.GetTick();
  local ops = AIController.GetOpsTillSuspend();
  FxVCOriginal(catalog, line, lines, force);
  local left = AIController.GetOpsTillSuspend();
  local ticks = AIController.GetTick()-tick;
  local spent = ticks <= 0 ? ops-left : ops+(ticks-1)*OPS_PER_TICK+(OPS_PER_TICK-left);
  local current = line != null && ("lineId" in line) && line.lineId in C121_VISIBLE_FLEET_CACHE
      ? C121_VISIBLE_FLEET_CACHE[line.lineId] : null;
  local quoted = current != null && (old == null || old != current);
  FXVC.calls++;
  if (quoted) {
    FXVC.quotes++;
    FXVC.quoteOps += spent;
    FXVC.quoteTicks += ticks;
    AILog.Info("C121_VISIBLE_COST_QUOTE line=" + line.lineId + " ops=" + spent
        + " ticks=" + ticks + " vehicles=" + current.vehicles);
  } else { FXVC.cachedOps += spent; FXVC.cachedTicks += ticks; }
  if (FXVC.calls == 1) AILog.Info("C121_VISIBLE_COST_WORLD pass=1 visible=" + (C121_AIR_VISIBLE_COMPETITION ? 1 : 0));
}
