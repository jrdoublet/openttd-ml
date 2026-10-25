/* RLW-03 : shadow mensuel des DECLENCHEURS, jamais de generation ni de pose.
 * Drapeau source OFF. Ne pas confondre les projets proches/financables avec
 * des projets physiquement constructibles (A* et devis reels : RLW-07). */

function OpexRLW03TopTownCohort(catalog)
{
  if (catalog == null || catalog.towns == null || catalog.towns.len() == 0) return null;
  local ranked = clone catalog.towns;
  /* Snapshot de population du premier catalogue complet, ordre deterministe. */
  ranked.sort(function(a, b) {
    if (a.pop != b.pop) return a.pop > b.pop ? -1 : 1;
    if (a.id == b.id) return 0;
    return a.id < b.id ? -1 : 1;
  });
  local top = (ranked.len() * 30 + 99) / 100;
  local cohort = [];
  for (local i = 0; i < top; i++) cohort.append(ranked[i].id);
  return cohort;
}

/* Mesure par ville EFFECTIVEMENT reliee (extremites des lignes), comme les
 * town IDs de AIR_BUILD historiques, pas par bassin de gares. L'index des
 * origines evite le produit nombre de villes x nombre de lignes chaque mois. */
function OpexRLW03ReachedTowns(cohort, mode, lines)
{
  if (cohort == null || cohort.len() == 0 || lines == null) return -1;
  local served = {};
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != mode) continue;
    if (mode == "rail" && (!("kind" in line) || line.kind != "pax")) continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (!("originA" in line) || !("originB" in line)) continue;
    if (AIMap.IsValidTile(line.originA)) {
      local a = AITile.GetClosestTown(line.originA);
      if (AITown.IsValidTown(a)) served.rawset(a, true);
    }
    if (AIMap.IsValidTile(line.originB)) {
      local b = AITile.GetClosestTown(line.originB);
      if (AITown.IsValidTown(b)) served.rawset(b, true);
    }
  }
  local count = 0;
  foreach (id in cohort) {
    if (!AITown.IsValidTown(id)) return -1; // Denominateur fige : inconnu, pas zero.
    if (id in served) count++;
  }
  return count;
}

/* Les candidats sont les projets courts DEJA publies. Ce comptage suit la
 * garde V217 et ajoute la capacite de financement : pas d'appel de generateur.
 * 2 signifie >=2, et non un nombre exact de projets dans le vivier. */
function OpexRLW03ShortPool(owner, cash)
{
  if (owner._projects == null || !("candidateGroups" in owner._projects)
      || owner._projects.candidateGroups == null || owner._catalog == null)
    return { pax = -1, freight = -1 };
  local cap = OpexCatalogBounds(owner._catalog).railMax;
  local counts = { pax = 0, freight = 0 };
  local seen = {};
  foreach (key, list in owner._projects.candidateGroups) {
    foreach (project in list) {
      if (project == null || !("mode" in project) || project.mode != "rail"
          || !("payload" in project) || project.payload == null) continue;
      local kind = ("kind" in project) ? project.kind : project.payload.kind;
      if (kind != "pax" && kind != "freight") continue;
      if (counts[kind] >= 2) continue;
      local c = project.payload;
      if (!("distance" in c) || c.distance > cap) continue;
      local pair = OpexAbandonedPairKey(c);
      if (owner._abandonedPairs != null && (pair in owner._abandonedPairs)) continue;
      local unique = kind + "|" + pair;
      if (unique in seen) continue;
      if (OpexProjectFinanceCapital(project) > cash) continue;
      local close = owner._tooClose(c);
      if (close.hard >= 0 || close.blocking >= 0) continue;
      seen.rawset(unique, true);
      counts[kind]++;
    }
    if (counts.pax >= 2 && counts.freight >= 2) break;
  }
  return counts;
}

/* Historique mensuel borne a 13 points ; la pente exige un mois TEMOIN a
 * exactement M-12. Les donnees absentes ne sont jamais traitees comme 0. */
function OpexRLW03Growth(history, ym, coverage)
{
  local old = -1;
  foreach (row in history) if (row.month == ym - 12) old = row.coverage;
  for (local i = history.len() - 1; i >= 0; i--)
    if (history[i].month < ym - 12) history.remove(i);
  if (coverage >= 0) history.append({ month = ym, coverage = coverage });
  return old >= 0 && coverage >= 0 ? coverage - old : -1001;
}

function OpexAI::_rlw03MonthlyObserve()
{
  if (!RLW03_SHADOW || !DECISION_LOG || !MODE_RAIL || this._catalog == null) return;
  if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) return;
  local date = AIDate.GetCurrentDate();
  local year = AIDate.GetYear(date);
  local month = AIDate.GetMonth(date);
  local ym = year * 12 + month;
  /* Inclure le cout du tri initial dans la premiere mesure, pas seulement
   * celui du comptage de lignes et du vivier. */
  local mark = OpexOpsMeasureBegin();
  if (this._rlw03State == null) {
    local top = OpexRLW03TopTownCohort(this._catalog);
    if (top == null) return;
    this._rlw03State = { cohort = top, cohortMonth = ym, lastMonth = -1,
      paxHistory = [], railHistory = [], paxShortage = 0, freightShortage = 0 };
  }
  local s = this._rlw03State;
  if (s.lastMonth == ym || s.cohort == null || s.cohort.len() == 0) return;
  /* Ne pas traiter deux mois eloignes comme deux observations consecutives. */
  if (s.lastMonth >= 0 && ym != s.lastMonth + 1) {
    s.paxShortage = 0;
    s.freightShortage = 0;
  }
  s.lastMonth = ym;
  local airReached = MODE_AIR ? OpexRLW03ReachedTowns(s.cohort, "air", this._lines) : -1;
  local railReached = !MODE_AIR ? OpexRLW03ReachedTowns(s.cohort, "rail", this._lines) : -1;
  local n = s.cohort.len();
  local airCoverage = airReached >= 0 ? (1000 * airReached) / n : -1;
  local railCoverage = railReached >= 0 ? (1000 * railReached) / n : -1;
  local coverage = MODE_AIR ? airCoverage : railCoverage;
  local growth = MODE_AIR
      ? OpexRLW03Growth(s.paxHistory, ym, airCoverage)
      : OpexRLW03Growth(s.railHistory, ym, railCoverage);
  local cash = OpexAvailableCapital();
  local pools = OpexRLW03ShortPool(this, cash);
  local liquid = cash >= 100000;
  s.paxShortage = liquid && pools.pax >= 0 && pools.pax < 2 ? s.paxShortage + 1 : 0;
  s.freightShortage = liquid && pools.freight >= 0 && pools.freight < 2 ? s.freightShortage + 1 : 0;
  local age = (year - OPEX_START_YEAR) * 12 + month - 1;
  local plateau = coverage >= 800 && growth != -1001 && growth <= 50;
  local paxFallback = !MODE_AIR && s.paxShortage >= 2;
  local paxReady = age >= 24 && (plateau || paxFallback);
  local freightReady = age >= 24 && s.freightShortage >= 2;
  local ops = OpexOpsMeasureEnd(mark);
  if (DECISION_LOG) {
    OpexDecide("RLW03_TRIGGER", "family=pax month=" + ym + " cohort=" + n
        + " mode=" + (MODE_AIR ? "multimodal" : "rail_only")
        + " served=" + (MODE_AIR ? airReached : railReached)
        + " coverage_pm=" + coverage + " growth12_pm=" + growth
        + " short_startable=" + pools.pax + " streak=" + s.paxShortage
        + " capital=" + cash + " age_months=" + age
        + " eligible=" + (paxReady ? 1 : 0)
        + " reason=" + (plateau ? "coverage_plateau" : (paxFallback ? "short_pax_pool" : "none"))
        + " ops=" + ops);
    OpexDecide("RLW03_TRIGGER", "family=freight month=" + ym + " cohort=" + n
        + " short_startable=" + pools.freight + " streak=" + s.freightShortage
        + " capital=" + cash + " age_months=" + age
        + " eligible=" + (freightReady ? 1 : 0)
        + " reason=" + (freightReady ? "short_freight_pool" : "none") + " ops=shared");
  }
}
