/* Rail rescue starvation gate, 30/10/2026.
 * Six calendar months without a successfully built NEW transport line,
 * irrespective of AIR / RAIL / ROAD / WATER. Replacements or fleet growth
 * are not new links. All repair policy controls remain default OFF.
 * Store one scalar date even with compact Save/Load; legacy saves lacking
 * the date restart a conservative six-month cooldown. */
RAIL_REPAIR_LAST_CONSTRUCTION_DATE <- -1;
RAIL_REPAIR_IDLE_LOGGED_LAST_BUILD <- -1;

function OpexRailRepairAnyOptIn()
{
  return RAIL_REPAIR_JOIN_SITE || RAIL_REPAIR_V131_FOCUS
      || RAIL_REPAIR_ASTAR_PAIR || RAIL_REPAIR_POSE_ORDER
      || V233L_CONSTRUCT == 2;
}

function OpexRailRepairNoteConstruction()
{
  if (!OpexRailRepairAnyOptIn()) return;
  RAIL_REPAIR_LAST_CONSTRUCTION_DATE = AIDate.GetCurrentDate();
  RAIL_REPAIR_IDLE_LOGGED_LAST_BUILD = -1;
  if (DECISION_LOG) OpexDecide("RAIL_REPAIR_IDLE", "phase=reset last="
      + RAIL_REPAIR_LAST_CONSTRUCTION_DATE + " reason=new_line");
}

function OpexRailRepairSixMonthThreshold(fromDate)
{
  if (fromDate < 0) return -1;
  local year = AIDate.GetYear(fromDate);
  local month = AIDate.GetMonth(fromDate) + 6;
  if (month > 12) { year++; month -= 12; }
  /* 31 aout -> 28/29 fevrier : six mois calendaires, pas 183 jours fixes. */
  local nextYear = month == 12 ? year + 1 : year;
  local nextMonth = month == 12 ? 1 : month + 1;
  local firstDay = AIDate.GetDate(year, month, 1);
  local daysInMonth = AIDate.GetDate(nextYear, nextMonth, 1) - firstDay;
  local day = AIDate.GetDayOfMonth(fromDate);
  if (day > daysInMonth) day = daysInMonth;
  return AIDate.GetDate(year, month, day);
}

function OpexRailRepairIdleActive()
{
  if (!OpexRailRepairAnyOptIn()) return false;
  if (RAIL_REPAIR_LAST_CONSTRUCTION_DATE < 0) return false;
  local now = AIDate.GetCurrentDate();
  if (now < RAIL_REPAIR_LAST_CONSTRUCTION_DATE) return false;
  if (now < OpexRailRepairSixMonthThreshold(RAIL_REPAIR_LAST_CONSTRUCTION_DATE))
    return false;
  if (DECISION_LOG && RAIL_REPAIR_IDLE_LOGGED_LAST_BUILD != RAIL_REPAIR_LAST_CONSTRUCTION_DATE) {
    RAIL_REPAIR_IDLE_LOGGED_LAST_BUILD = RAIL_REPAIR_LAST_CONSTRUCTION_DATE;
    OpexDecide("RAIL_REPAIR_IDLE", "phase=enabled last=" + RAIL_REPAIR_LAST_CONSTRUCTION_DATE
        + " now=" + now + " reason=six_calendar_months");
  }
  return true;
}
