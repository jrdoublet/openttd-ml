/* RLW-04b : enumeration passive du fret non perissable a 224..288 tuiles.
 * Adapte de RLW-04 du worktree historique .worktrees/rlw04 : curseur de
 * sources, stock trace borne et comptage des opcodes, sans grille Squirrel.
 * Aucune interaction avec candidats, portefeuille, A* ou constructeur. */

const RLW04B_MIN = 224;
const RLW04B_MAX = 288;
const RLW04B_PROBE_BIT = 16777216;
const RLW04B_POOL_CAP = 32;
const RLW04B_SOURCE_CAP = 512;
/* La calibration d'un cargo peut depasser 3 000 opcodes : une reserve
 * distincte evite de suspendre ce calcul atomique au demarrage. */
const RLW04B_RESERVE = 8500;
/* Chaque Valuate est atomique, mais chaque source a sa propre tranche.
 * Garder plus de 1 500 opcodes de marge pour le pire scan observe et son log. */
const RLW04B_SOURCE_RESERVE = 2700;
const RLW04B_MAX_SLICES_CALL = 16;
const RLW04B_SLICE_BUDGET = 7000;

function OpexRLW04BInit()
{
  return { cargos = [], cargoCursor = 0, units = [], cursor = 0,
      initialized = false, completed = false, firstDate = AIDate.GetCurrentDate(),
      doneDate = -1, slices = 0, totalOps = 0, maxOps = 0,
      overruns = 0, tickCrossings = 0, initOps = 0, initMaxOps = 0,
      sources = 0, pairs = 0, stocked = [], stockCursor = 0,
      rejectedLargeLists = 0, invalidSources = 0, rejectedCargos = 0,
      lastOps = 0, opLow = 0, opMid = 0, opHigh = 0 };
}

/* Duree reelle du materiel de la partie (profil loco + deux wagons a 256).
 * Rapide = trajet physique + 2 jours de chargement, lent = meme trajet
 * degrade de 40 % + 6 jours d'attente. Ni ID ni paiement de cargo codes. */
function OpexRLW04BCargo(catalog, cargo)
{
  local info = { cargo = cargo, fast = -1, slow = -1, incomeFast = 0,
      incomeSlow = 0, ratioPm = -1, speed = 0, keep = false, reason = "unsupported" };
  if (!AICargo.IsValidCargo(cargo)) { info.reason = "invalid"; return info; }
  if (AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS)
      || AICargo.HasCargoClass(cargo, AICargo.CC_MAIL)
      || AICargo.GetTownEffect(cargo) == AICargo.TE_GOODS) {
    info.reason = "pax_mail_goods";
    return info;
  }
  if (catalog.locoByCargoWagons == null || !(cargo in catalog.locoByCargoWagons)
      || catalog.producers == null || !(cargo in catalog.producers)
      || catalog.producers[cargo].len() == 0) {
    info.reason = "no_rail_or_source";
    return info;
  }
  local profile = OpexGetEpochRailProfile(catalog, cargo, 256);
  if (profile == null || profile.speed <= 0) { info.reason = "no_train"; return info; }
  info.speed = profile.speed;
  local realDays = 256.0 * OpexDaysPerTile(profile.speed.tofloat(), 74.0);
  info.fast = (realDays + 2.0).tointeger();
  info.slow = (realDays * 1.4 + 6.0).tointeger();
  if (info.slow <= info.fast) info.slow = info.fast + 1;
  info.incomeFast = AICargo.GetCargoIncome(cargo, 256, info.fast);
  info.incomeSlow = AICargo.GetCargoIncome(cargo, 256, info.slow);
  if (info.incomeFast <= 0) { info.reason = "zero_income"; return info; }
  info.ratioPm = (1000 * info.incomeSlow) / info.incomeFast;
  info.keep = info.ratioPm >= 800;
  info.reason = info.keep ? "retained" : "perishable";
  return info;
}

function OpexRLW04BLogCargo(info, sources)
{
  OpexDecide("RLW04B_CARGO", "cargo=" + AICargo.GetCargoLabel(info.cargo)
      + " speed=" + info.speed + " fast_days=" + info.fast
      + " slow_days=" + info.slow + " fast_income=" + info.incomeFast
      + " slow_income=" + info.incomeSlow + " ratio_pm=" + info.ratioPm
      + " retained=" + (info.keep ? 1 : 0) + " sources=" + sources
      + " reason=" + info.reason);
}

function OpexRLW04BLog(s, phase)
{
  local elapsed = AIDate.GetCurrentDate() - s.firstDate;
  OpexDecide("RLW04B_ENUM", "phase=" + phase + " sources=" + s.sources
      + " slices=" + s.slices + " units=" + s.units.len()
      + " cursor=" + s.cursor + " pairs=" + s.pairs
      + " stock=" + s.stocked.len() + " days=" + elapsed
      + " ops=" + s.lastOps + " max_ops=" + s.maxOps
      + " total_ops=" + s.totalOps + " low=" + s.opLow
      + " mid=" + s.opMid + " high=" + s.opHigh
      + " init_ops=" + s.initOps + " init_max=" + s.initMaxOps
      + " overruns=" + s.overruns + " ticks=" + s.tickCrossings
      + " too_many_sinks=" + s.rejectedLargeLists
      + " invalid_sources=" + s.invalidSources + " rejected_cargos=" + s.rejectedCargos
      + " budget=" + RLW04B_SLICE_BUDGET);
}

/* Une seule source par tranche : ni index, ni tri, ni boucle Squirrel sur
 * tous les puits de la carte. Le Manhattan est valuate en C++ ; les bornes
 * exclusives (223, 289) choisissent exactement 224..288. */
function OpexRLW04BSource(s, catalog)
{
  if (s.cursor >= s.units.len()) return;
  local u = s.units[s.cursor];
  if (u.index >= u.sources.len()) { s.cursor++; return; }
  local srcId = u.sources[u.index++];
  s.sources++;
  if (!AIIndustry.IsValidIndustry(srcId) || !AICargo.IsValidCargo(u.cargo)) {
    s.invalidSources++;
    return;
  }
  local tile = AIIndustry.GetLocation(srcId);
  if (!AIMap.IsValidTile(tile)) { s.invalidSources++; return; }
  local sinks = AIIndustryList_CargoAccepting(u.cargo);
  /* Risque atomique de Valuate : le petit vivier par cargo est attendu,
   * mais un NewGRF massif est mesure et exclu avec motif explicite. */
  if (sinks.Count() > RLW04B_SOURCE_CAP) { s.rejectedLargeLists++; return; }
  sinks.Valuate(AIIndustry.GetDistanceManhattanToTile, tile);
  sinks.KeepBetweenValue(223, 289);
  for (local dst = sinks.Begin(); !sinks.IsEnd(); dst = sinks.Next()) {
    if (dst == srcId || !AIIndustry.IsValidIndustry(dst)) continue;
    local distance = sinks.GetValue(dst);
    s.pairs++;
    local pair = { cargo = u.cargo, srcId = srcId, dstId = dst, distance = distance };
    if (s.stocked.len() < RLW04B_POOL_CAP) s.stocked.append(pair);
    else {
      s.stocked[s.stockCursor] = pair;
      s.stockCursor = (s.stockCursor + 1) % RLW04B_POOL_CAP;
    }
  }
  if (u.index >= u.sources.len()) s.cursor++;
}

function OpexAI::_rlw04bStep()
{
  if (!RLW04B_SHADOW || !MODE_RAIL || this._catalog == null
      || this._catalog.cargos == null || this._catalog.producers == null
      || this._catalog.locoByCargoWagons == null) return;
  if (STAGED_BOOTSTRAP && this._generationStage < OPEX_STAGE_COMPLETE) return;
  if (this._rlw04bState == null) {
    if (AIController.GetOpsTillSuspend() < RLW04B_RESERVE) return;
    this._rlw04bState = OpexRLW04BInit();
    foreach (c in this._catalog.cargos) this._rlw04bState.cargos.append(c);
    return;
  }
  local s = this._rlw04bState;
  if (s.completed) return;
  if (!s.initialized) {
    if (AIController.GetOpsTillSuspend() < RLW04B_RESERVE) return;
    if (s.cargoCursor < s.cargos.len()) {
      local cargo = s.cargos[s.cargoCursor++];
      local markCargo = OpexOpsMeasureBegin();
      local info = OpexRLW04BCargo(this._catalog, cargo);
      local sources = (cargo in this._catalog.producers) ? this._catalog.producers[cargo].len() : 0;
      if (info.keep) {
        /* Snapshot IDs par cargo : les index ne reculent pas sur refresh. */
        local ids = [];
        foreach (srcIndex in this._catalog.producers[cargo]) {
          if (srcIndex >= 0 && srcIndex < this._catalog.industries.len())
            ids.append(this._catalog.industries[srcIndex].id);
        }
        s.units.append({ cargo = cargo, sources = ids, index = 0 });
      } else s.rejectedCargos++;
      local usedCargo = OpexOpsMeasureEnd(markCargo);
      s.initOps += usedCargo;
      if (usedCargo > s.initMaxOps) s.initMaxOps = usedCargo;
      OpexRLW04BLogCargo(info, sources);
      return;
    }
    s.initialized = true;
    OpexRLW04BLog(s, "start");
    return;
  }
  local steps = 0;
  local callTick = AIController.GetTick();
  while (s.cursor < s.units.len() && steps < RLW04B_MAX_SLICES_CALL
      && AIController.GetTick() == callTick) {
    local admission = s.maxOps + 1400;
    if (admission < RLW04B_SOURCE_RESERVE) admission = RLW04B_SOURCE_RESERVE;
    if (AIController.GetOpsTillSuspend() < admission) break;
    local mark = OpexOpsMeasureBegin();
    OpexRLW04BSource(s, this._catalog);
    local used = OpexOpsMeasureEnd(mark);
    steps++;
    s.slices++;
    s.lastOps = used;
    s.totalOps += used;
    if (used > s.maxOps) s.maxOps = used;
    if (used < 1000) s.opLow++;
    else if (used < 3000) s.opMid++;
    else s.opHigh++;
    if (AIController.GetTick() != mark.tick) s.tickCrossings++;
    if (used > RLW04B_SLICE_BUDGET || AIController.GetTick() != mark.tick) s.overruns++;
    /* Journaliser a chaque seizieme source, dans la reserve de la tranche. */
    if (s.slices % 16 == 0) OpexRLW04BLog(s, "progress");
  }
  if (s.cursor >= s.units.len() && !s.completed) {
    s.completed = true;
    s.doneDate = AIDate.GetCurrentDate();
    OpexRLW04BLog(s, "done");
  }
}
