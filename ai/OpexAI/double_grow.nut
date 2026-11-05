/* DOUBLE-GROW : selec­tion mensuelle des lignes fret deja productives.
 * La construction principale reste identique. Le doublement est opportuniste,
 * sans affecter le slot _railSearch ni les projets candidats. */
DOUBLE_GROW_CURSOR <- 0;

function OpexDoubleGrowSelect(owner, year)
{
  if (!DOUBLE_GROW || !MODE_RAIL || !SAVE_FULL_STATE || owner == null || owner._lines == null
      || owner._catalog == null || owner._lines.len() == 0
      || owner._railExpansion != null || owner._railSearch != null
      || owner._activeWorker != null || owner._v257Pending != null
      || owner._v271Pending != null || owner._railLongV2Pending != null
      || OpexV284Busy(owner)) return false;

  local count = owner._lines.len();
  local now = AIDate.GetCurrentDate();
  local maxScan = min(count, 12);
  for (local i = 0; i < maxScan; i++) {
    local line = owner._lines[(DOUBLE_GROW_CURSOR + i) % count];
    if (line == null || !("mode" in line) || line.mode != "rail"
        || !("kind" in line) || line.kind != "freight"
        || !("lineId" in line) || !("vehicles" in line)
        || line.vehicles == null || !("trains" in line)
        || (("scrapping" in line) && line.scrapping)
        || !("lastProfit" in line) || line.lastProfit <= 0
        || !("buildDate" in line) || now - line.buildDate < 365
        || !("cargo" in line) || !("stationA" in line)) continue;

    /* La marge doit etre deja positive. Un stock temporaire n'autorise pas
     * une depense si le cash de l'entreprise reste sollicite. */
    if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < 750000) return false;
    local station = AIStation.GetStationID(line.stationA);
    if (!AIStation.IsValidStation(station)) continue;
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    if (waiting < 120) continue;

    if (("doubleGrowDirectional" in line) && line.doubleGrowDirectional) {
      if (line.trains < 8 && OpexDoubleGrowFleet(owner, line)) {
        DOUBLE_GROW_CURSOR = (DOUBLE_GROW_CURSOR + i + 1) % count;
        return true;
      }
      continue;
    }
    if (line.trains != 1 || line.vehicles.len() != 1
        || (("doubleTrack" in line) && line.doubleTrack != 0)) continue;
    if (("doubleGrowRetry" in line) && now < line.doubleGrowRetry) continue;
    if (FLEET_ARB && !OpexFleetRequest(line, "rail", "add_vehicle", null,
        null, "DOUBLE_CONVERSION")) continue;
    /* Un seul essai au maximum par ligne et par an si le terrain refuse. */
    line.rawset("doubleGrowRetry", now + 365);
    owner._saveProjection = null;
    DOUBLE_GROW_CURSOR = (DOUBLE_GROW_CURSOR + i + 1) % count;
    if (OpexDoubleGrowGeometry(owner, line)) {
      if (DECISION_LOG) OpexDecide("DOUBLE_GROW", "event=double line=" + line.lineId
          + " trains=" + line.trains + " waiting=" + waiting);
      return true;
    }
    if (DECISION_LOG) OpexDecide("DOUBLE_GROW", "event=skip line=" + line.lineId
        + " reason=geometry waiting=" + waiting);
    return false;
  }
  DOUBLE_GROW_CURSOR = (DOUBLE_GROW_CURSOR + maxScan) % count;
  return false;
}
