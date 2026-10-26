/* V233L : sorties GOOD longues, independantes des anciennes greffes V233.
 * Toutes les entrees sont court-circuitees par V233_LONG_GOOD. Fenetres de
 * six mois CLOS observes sur sept mois au plus ; aucun mois absent impute.
 * Ni stock transforme en debit, ni croissance promise.
 * Budget cooperatif : une unite native/economique peut depasser le plafond. */
const V233L_WINDOW = 6;
const V233L_MAX_AGE = 3;
const V233L_MAX_FACTORIES = 64;
const V233L_SLICE_OPS = 20000;
const V233L_TOWNS = 8;
/* Curseurs sauvegardes par paire/geometrie. Seuls les indices des plans sont
 * gardes : toute preuve physique est recalculee avant admission/construction. */
V233L_SITE_CACHE <- {};
V233L_JOIN_CURSOR <- {};
const V233L_SITE_CACHE_MAX = 128;
const V233L_SITE_TOTAL_OPS = 240000;
const V233L_JOIN_TOTAL_OPS = 80000;
const V233L_FUNNEL_BATCH = 5;
const V233L_FUNNEL_ANCHORS = 256;

function OpexV233LIs(candidate)
{
  return V233_LONG_GOOD > 0 && candidate != null
      && ("v233LongGood" in candidate) && candidate.v233LongGood;
}

function OpexV233LLog(event, fields)
{
  if (DECISION_LOG) OpexDecide("V233L_" + event, fields);
}

function OpexV233LNewState()
{
  return { month = -1, cursor = 0, rows = {}, growth = {}, pending = null, sites = V233L_SITE_CACHE };
}

function OpexV233LGoodCargo()
{
  local cargos = AICargoList();
  for (local cargo = cargos.Begin(); !cargos.IsEnd(); cargo = cargos.Next())
    if (AICargo.GetCargoLabel(cargo) == "GOOD") return cargo;
  return -1;
}

function OpexV233LMonth()
{
  local today = AIDate.GetCurrentDate();
  return AIDate.GetYear(today) * 12 + AIDate.GetMonth(today);
}

/* Le bassin doit toucher CETTE usine, pas seulement produire le meme cargo. */
function OpexV233LTouches(plan, industry, producing, coverage)
{
  local tiles = producing ? AITileList_IndustryProducing(industry, coverage)
                         : AITileList_IndustryAccepting(industry, coverage);
  for (local i = 0; i < plan.length; i++)
    if (tiles.HasItem(plan.anchor + i * plan.step)) return true;
  return false;
}

function OpexV233LCargoValue(anchor, step, length, cargo, coverage, producing)
{
  local horizontal = abs(step) == 1;
  return producing ? AITile.GetCargoProduction(anchor, cargo,
      horizontal ? length : 1, horizontal ? 1 : length, coverage)
      : AITile.GetCargoAcceptance(anchor, cargo,
      horizontal ? length : 1, horizontal ? 1 : length, coverage);
}

function OpexV233LInput(line, cargo)
{
  if (line == null || !("mode" in line) || line.mode != "rail"
      || !("kind" in line) || line.kind != "freight" || line.cargo == cargo
      || !("platformB" in line) || line.platformB == null
      || !("vehicles" in line) || line.vehicles.len() == 0
      || (("scrapping" in line) && line.scrapping)) return -1;
  local industry = AIIndustry.GetIndustryID(line.originB);
  if (!AIIndustry.IsValidIndustry(industry)
      || !AIIndustryType.IsProcessingIndustry(AIIndustry.GetIndustryType(industry))) return -1;
  local producing = AICargoList_IndustryProducing(industry);
  local accepting = AICargoList_IndustryAccepting(industry);
  if (!producing.HasItem(cargo) || !accepting.HasItem(line.cargo)) return -1;
  local station = OpexLineStationId(line, "B");
  if (station < 0 || AITile.GetOwner(line.stationB) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) return -1;
  if (!OpexV233LTouches(line.platformB, industry, false,
      AIStation.GetCoverageRadius(AIStation.STATION_TRAIN))) return -1;
  local vehicle = line.vehicles[0];
  if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetCapacity(vehicle, line.cargo) <= 0
      || !OpexVehicleServesStation(vehicle, station)) return -1;
  return industry;
}

function OpexV233LObserve(owner)
{
  local state = V233L_STATE;
  local month = OpexV233LMonth();
  if (state.month != month) { state.month = month; state.cursor = 0; }
  if (owner._lines == null || state.cursor >= owner._lines.len()) return;
  local mark = OpexOpsMeasureBegin();
  local cargo = OpexV233LGoodCargo();
  if (cargo < 0) { state.cursor = owner._lines.len(); return; }
  local count = 0;
  while (state.cursor < owner._lines.len() && count < 8
      && OpexOpsMeasureEnd(mark) < V233L_SLICE_OPS) {
    local line = owner._lines[state.cursor++];
    count++;
    OpexV233LObserveBacklog(line, month);
    local industry = OpexV233LInput(line, cargo);
    if (industry < 0) continue;
    if (!(industry in state.rows)) {
      if (state.rows.len() >= V233L_MAX_FACTORIES) continue;
      state.rows.rawset(industry, { month = -1, tile = line.originB,
        months = [], production = [], residual = [], inputLine = line.lineId, station = -1, townCursor = 0,
        exportLine = -1, exportMonth = -1 });
    }
    local row = state.rows[industry];
    if (row.tile != line.originB) { row.months = []; row.production = []; row.residual = []; row.month = -1; }
    row.tile = line.originB;
    row.inputLine = line.lineId;
    row.station = OpexLineStationId(line, "B");
    if (row.month >= month - 1) continue; // plusieurs intrants : un seul mois observe, jamais de recul.
    local production = AIIndustry.GetLastMonthProduction(industry, cargo);
    local transported = AIIndustry.GetLastMonthTransported(industry, cargo);
    if (OpexV233LMonth() != month) break; // ne pas etiqueter un mois nouveau avec l'ancien.
    local residual = production - transported;
    if (residual < 0) residual = 0;
    OpexV233LRecord(row, month - 1, production, residual);
    if (DECISION_LOG) OpexV233LLog("PRODUCTION", "industry=" + industry + " month=" + row.month
        + " produced=" + production + " transported=" + transported + " residual=" + residual
        + " samples=" + row.production.len() + " station=" + row.station
        + " input_cargo=" + AICargo.GetCargoLabel(line.cargo)
        + " good_rating=" + AIStation.GetCargoRating(row.station, cargo));
  }
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=observe units=" + count
      + " ops=" + OpexOpsMeasureEnd(mark) + " budget=" + V233L_SLICE_OPS);
}

/* Six valeurs reelles, au plus un mois absent dans les sept mois calendaires.
 * Une interruption longue evince les points anciens, sans fabriquer de zeros. */
function OpexV233LRecord(row, month, production, residual)
{
  if (month <= row.month) return;
  row.months.append(month);
  row.production.append(production);
  row.residual.append(residual);
  while (row.months.len() > V233L_WINDOW || row.months[0] < month - V233L_WINDOW) {
    row.months.remove(0); row.production.remove(0); row.residual.remove(0);
  }
  row.month = month;
}

/* Age calendaire du dernier mois CLOS : 1..3 inclus, jamais le mois en cours/futur. */
function OpexV233LFresh(month, now)
{
  return month >= 0 && month < now && now - month <= V233L_MAX_AGE;
}

function OpexV233LMin(values)
{
  local result = null;
  foreach (value in values) if (result == null || value < result) result = value;
  return result == null ? 0 : result;
}

function OpexV233LMean(values)
{
  local total = 0;
  foreach (value in values) total += value;
  return values.len() > 0 ? total / values.len() : 0;
}

/* Une secondaire produit a la livraison : des mois nuls entre deux trains
 * sont normaux. Six mois observes, au moins deux livraisons productives et
 * une production dans les trois derniers mois calendaires de la fenetre. */
function OpexV233LDurable(row)
{
  if (row.production.len() != V233L_WINDOW || row.residual.len() != V233L_WINDOW
      || row.months.len() != V233L_WINDOW || row.month - row.months[0] > V233L_WINDOW) return false;
  local positive = 0;
  local recent = 0;
  for (local i = 0; i < row.production.len(); i++) {
    if (row.production[i] > 0) positive++;
    if (row.months[i] >= row.month - 2) recent += row.production[i];
  }
  return positive >= 2 && recent > 0;
}

/* Appel une fois par source, jamais une fois par ville. Le service existant
 * NON-GOOD est distinct du depart GOOD ; une sortie deja exploitee est exclue. */
function OpexV233LSource(source, cargo, lines)
{
  if (!SAVE_FULL_STATE || V233L_STATE == null || AICargo.GetCargoLabel(cargo) != "GOOD"
      || !(source.id in V233L_STATE.rows)) return null;
  local row = V233L_STATE.rows[source.id];
  local mark = OpexOpsMeasureBegin();
  local reasons = [];
  if (row.tile != source.tile) reasons.append("source_changed");
  if (!OpexV233LDurable(row)) reasons.append("window");
  local inputLive = false;
  local exportExists = false;
  local complete = true;
  foreach (line in lines) {
    if (OpexOpsMeasureEnd(mark) >= V233L_SLICE_OPS) { complete = false; break; }
    if (("lineId" in line) && line.lineId == row.inputLine
        && OpexV233LInput(line, cargo) == source.id) inputLive = true;
    if (("cargo" in line) && line.cargo == cargo && ("originA" in line)
        && line.originA == source.tile && (!("scrapping" in line) || !line.scrapping)) exportExists = true;
  }
  local now = OpexV233LMonth();
  if (!OpexV233LFresh(row.month, now)) reasons.append("stale");
  if (!complete) reasons.append("budget");
  if (complete && !inputLive) reasons.append("input_not_live");
  if (exportExists) reasons.append("export_exists");
  local monthly = OpexV233LMean(row.residual);
  if (monthly <= 0) reasons.append("no_residual");
  /* Une ligne par condition/source, meme si la fenetre bloque deja. Ne pas
   * confondre un inventaire interrompu avec la preuve d'un intrant absent. */
  if (DECISION_LOG) foreach (reason in reasons) OpexV233LLog("REJECT",
      "industry=" + source.id + " reason=" + reason + " sample_month=" + row.month
      + " age=" + (now - row.month) + " samples=" + row.production.len()
      + " input_live=" + (inputLive ? 1 : 0) + " export_exists=" + (exportExists ? 1 : 0)
      + " residual=" + monthly);
  return { ready = reasons.len() == 0, row = row, monthly = monthly, sampleMonth = row.month,
    ops = OpexOpsMeasureEnd(mark), townStart = row.townCursor, visits = 0 };
}

function OpexV233LAdmit(context, source, town)
{
  local mark = OpexOpsMeasureBegin();
  context.visits++;
  if (!context.ready) { context.ops += OpexOpsMeasureEnd(mark); return false; }
  local distance = AIMap.DistanceManhattan(source.tile, town.tile);
  /* PO01C peut suspendre entre Source et Admit : dater l'offre figee, pas
   * une observation plus neuve arrivee entre-temps dans context.row. */
  local reason = !OpexV233LFresh(context.sampleMonth, OpexV233LMonth()) ? "stale" :
      (distance < 150 || distance > 300 ? "distance" : "OK");
  if (reason != "OK" && DECISION_LOG) OpexV233LLog("REJECT",
      "industry=" + source.id + " town=" + town.id + " reason=" + reason + " distance=" + distance);
  context.ops += OpexOpsMeasureEnd(mark);
  return reason == "OK";
}

function OpexV233LSourceEnd(context, source)
{
  context.row.townCursor = (context.row.townCursor + context.visits) % 65536;
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=candidates industry=" + source.id
      + " towns=" + context.visits + " ops=" + context.ops
      + " budget=" + V233L_SLICE_OPS);
}

/* Source propre d'abord si elle capte effectivement l'usine. Une jointure
 * native au quai d'intrants est aussi possible : pas de voie d'intrants reutilisee.
 * Le cargo de ce quai n'est jamais assimile a GOOD. */
function OpexV233LPlatformPlans(catalog, candidate, phase = "build")
{
  local industry = AIIndustry.GetIndustryID(candidate.src);
  /* Quai pour la rame initiale, sans la marge de croissance facultative.
   * Ne jamais raccourcir en dessous des wagons promis au portefeuille. */
  local length = OpexRailPlatformLengthForWagons(candidate.wagons);
  local scanA = OpexV233LSiteSearch(candidate.src, length, candidate.cargo, catalog.railCoverage, true, null, candidate);
  local plansA = scanA.plans;
  foreach (p in plansA) {
      if (!OpexV233LTouches(p, industry, true, catalog.railCoverage)) continue;
      local station = candidate.v233InputStation;
      /* Meme captage, StationID partage si le moteur l'autorise. Une note GOOD
       * deja active est relevee au recalcul, pas la note du cargo entrant. */
      local shared = false;
      local goodRating = AIStation.IsValidStation(station) ? AIStation.GetCargoRating(station, candidate.cargo) : -1;
      if (AIStation.IsValidStation(station) && (goodRating <= 0 || goodRating >= candidate.stationRating)) {
        local accounting = AIAccounting();
        local test = AITestMode();
        /* Tester l'emprise des DEUX quais : AITestMode ne pose pas le premier. */
        local adjacent = p.parallel.anchor < p.anchor ? p.parallel.anchor : p.anchor;
        shared = AIRail.BuildRailStation(adjacent, p.direction, 2, p.length, station);
      }
      if (shared) p.stationId <- station;
  }
  /* Chemin court en premier, meme si le scan urbain est encore censure.
   * Chaque recherche garde son curseur ; un aeroport difficile ne bloque pas
   * le scan urbain, et reciproquement. */
  local joined = OpexV233LJoinSearch(candidate, length, catalog.railCoverage, phase + "_first");
  local compatible = plansA.len() == 0;
  foreach (p in plansA) foreach (q in joined.plans) {
    local distance = AIMap.DistanceManhattan(OpexV233LTariffTile(p), OpexV233LTariffTile(q));
    if (distance >= 150 && distance <= 300) compatible = true;
  }
  local scanB = joined;
  if (joined.plans.len() == 0 || !compatible) {
    if (V233_SITE_FUNNEL > 0) scanB = OpexV233LFunnelSearch(candidate, length, catalog.railCoverage);
    else scanB = OpexV233LSiteSearch(candidate.dst, length, candidate.cargo, catalog.railCoverage, false, null, candidate);
  }
  if (!compatible && joined.plans.len() > 0 && DECISION_LOG)
    OpexV233LLog("SITE_B_JOIN", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=" + phase + " ok=0 reason=distance");
  local plansB = scanB.plans;
  /* Ne pas publier une paire hors de la fenetre tarifaire apres deplacement. */
  local validA = [], validB = [];
  foreach (p in plansA) {
    foreach (q in plansB) {
      local origin = ("stationId" in p) ? AIStation.GetLocation(p.stationId) : p.anchor;
      local distance = AIMap.DistanceManhattan(origin, OpexV233LTariffTile(q));
      if (distance < 150 || distance > 300) continue;
      validB.append(q);
    }
    /* Un seul A, tous ses B compatibles : le produit cartesien offert a A*
     * ne doit pas reintroduire de paire hors bornes. */
    if (validB.len() > 0) { validA.append(p); break; }
  }
  local ok = validA.len() > 0 && validB.len() > 0;
  local pending = !ok && (scanA.reason == "budget" || scanB.reason == "budget"
      || (plansB.len() == 0 && joined.reason == "budget"));
  local limited = scanA.reason == "total_budget" || scanB.reason == "total_budget"
      || scanA.reason == "capacity" || scanB.reason == "capacity"
      || (plansB.len() == 0 && (joined.reason == "total_budget" || joined.reason == "capacity"));
  local reason = ok ? "OK" : (pending ? "SITE_PENDING" : (limited ? "SITE_LIMIT"
      : (plansA.len() > 0 && plansB.len() > 0 ? "DISTANCE" : OpexRailSiteReason(plansA.len() > 0, plansB.len() > 0))));
  if (DECISION_LOG) {
    OpexV233LSiteLog(candidate, scanA, "A", phase);
    OpexV233LSiteLog(candidate, scanB, "B", phase);
    if (!ok) OpexV233LLog(pending ? "SITE_WAIT" : "REJECT", "src=" + candidate.src + " dst=" + candidate.dst
        + " reason=" + reason + " phase=" + phase + " site_a=" + scanA.reason + " site_b=" + scanB.reason);
  }
  return { plansA = ok ? validA : null, plansB = ok ? validB : null, length = length, slopeRelaxed = 0,
    reason = reason, pending = pending,
    statsA = scanA.stats, statsB = scanB.stats };
}

function OpexV233LPreflight(catalog, candidate)
{
  local sites = OpexV233LPlatformPlans(catalog, candidate, "admission");
  return { ready = sites.reason == "OK", pending = sites.pending, reason = sites.reason };
}

function OpexV233LSiteStats()
{
  return { nClear = 0, nCargo = 0, nCmd = 0, terrain = 0, acceptance = 0,
    parallel = 0, authority = 0, native = 0, catchment = 0, spread = 0, error = 0, earlyAcceptance = 0 };
}

/* Coordonnees explicites : pas de retour a la ligne aux bords de carte. */
function OpexV233LOffset(tile, dx, dy)
{
  local x = AIMap.GetTileX(tile) + dx, y = AIMap.GetTileY(tile) + dy;
  if (x < 0 || y < 0 || x >= AIMap.GetMapSizeX() || y >= AIMap.GetMapSizeY()) return -1;
  return AIMap.GetTileIndex(x, y);
}

function OpexV233LFlat(tile)
{
  return AIMap.IsValidTile(tile) && AITile.IsBuildable(tile) && AITile.GetSlope(tile) == AITile.SLOPE_FLAT;
}

/* Une geometrie atomique. Aucun terrassement/demolition dans cette sonde.
 * Deux quais adjacents, sortie en tete au choix : un quai traversant libre
 * aux deux bouts fournit deux plans, sans exiger une sortie urbaine inutilisee. */
function OpexV233LSiteProbe(anchor, length, axis, sign, side, cargo, coverage, producing, industry, stats, host = null)
{
  local ux = axis == 0 ? 1 : 0, uy = axis == 0 ? 0 : 1;
  local step = axis == 0 ? 1 : AIMap.GetMapSizeX();
  local direction = axis == 0 ? AIRail.RAILTRACK_NE_SW : AIRail.RAILTRACK_NW_SE;
  local anchor2 = OpexV233LOffset(anchor, uy * side, ux * side);
  if (anchor2 < 0) { stats.parallel++; return null; }
  local first = anchor < anchor2 ? anchor : anchor2;
  local last = OpexV233LOffset(anchor > anchor2 ? anchor : anchor2, ux * (length - 1), uy * (length - 1));
  if (last < 0) { stats.terrain++; return null; }
  if (host != null && !OpexV233LJoinFits(host, first, last)) { stats.spread++; return null; }
  local exitIndex = sign > 0 ? length - 1 : 0;
  local leadIndex = sign > 0 ? length : -1;
  local lead = OpexV233LOffset(anchor, ux * leadIndex, uy * leadIndex);
  local lead2 = OpexV233LOffset(anchor2, ux * leadIndex, uy * leadIndex);
  if (!OpexV233LFlat(lead)) { stats.terrain++; return null; }
  if (!OpexV233LFlat(lead2)) { stats.parallel++; return null; }
  for (local i = 0; i < length; i++) {
    if (!OpexV233LFlat(OpexV233LOffset(anchor, ux * i, uy * i))) { stats.terrain++; return null; }
    if (!OpexV233LFlat(OpexV233LOffset(anchor2, ux * i, uy * i))) { stats.parallel++; return null; }
  }
  stats.nClear++;
  local value = OpexV233LCargoValue(anchor, step, length, cargo, coverage, producing);
  if (host != null) value = host.acceptance;
  local p = { anchor = anchor, step = step, length = length, direction = direction,
    station_exit = anchor + exitIndex * step, lead = lead, cargoValue = value };
  if ((producing && (value <= 0 || !OpexV233LTouches(p, industry, true, coverage)))
      || (!producing && value < 8)) { stats.acceptance++; return null; }
  stats.nCargo++;
  if (OPEX_LEVEL_LIMITS && !OpexLevelAllows("encroach_rival_catchment")
      && OpexStationEncroachesRival(AIMap.GetTileX(first), AIMap.GetTileY(first),
          AIMap.GetTileX(last), AIMap.GetTileY(last), coverage)) {
    stats.catchment++; return null;
  }
  local stationOk = false;
  {
    local accounting = AIAccounting();
    local test = AITestMode();
    local station = host == null ? AIStation.STATION_NEW : host.station;
    stationOk = AIRail.BuildRailStation(first, direction, 2, length, station);
    if (!stationOk) stats.error = AIError.GetLastError();
  }
  if (!stationOk) {
    if (stats.error == AIError.ERR_LOCAL_AUTHORITY_REFUSES) stats.authority++;
    else stats.native++;
    return null;
  }
  stats.nCmd++;
  p.parallel <- { anchor = anchor2, step = step, length = length, direction = direction,
    station_exit = anchor2 + exitIndex * step, lead = lead2 };
  p.parallels <- [p.parallel];
  if (host != null) { p.stationId <- host.station; p.v233Airport <- host.station; }
  return p;
}

/* Anneaux sans reparcourir leur interieur. Chaque cote a son propre budget,
 * son curseur (anneau, position, geometrie) et sa preuve de fin de recherche.
 * Un budget epuise n'est jamais une preuve d'absence de gare. */
function OpexV233LSiteSearch(center, length, cargo, coverage, producing, host = null, pair = null)
{
  local mark = OpexOpsMeasureBegin();
  if (producing) {
    local industry = AIIndustry.GetIndustryID(center);
    if (OPEX_LEVEL_LIMITS && industry >= 0 && OpexIndustryPrimaryRivalServed(industry, center, coverage))
      return { plans = [], stats = OpexV233LSiteStats(), reason = "rival_source", ring = 0, ops = 0, length = length };
  }
  local now = AIDate.GetCurrentDate();
  local key = center + ":" + length + ":" + cargo + ":" + coverage + ":" + (producing ? 1 : 0)
      + ":" + AIRail.GetCurrentRailType();
  if (pair != null) key += ":pair:" + pair.src + ":" + pair.dst;
  local radius = host == null ? STATION_SEARCH_RADIUS : host.spread / 2;
  if (host != null) key += ":join:" + host.station + ":" + host.left + ":" + host.top
      + ":" + host.right + ":" + host.bottom + ":" + host.spread;
  local action = "start";
  if (key in V233L_SITE_CACHE) {
    local old = V233L_SITE_CACHE[key];
    /* Jamais de TTL sur une recherche en attente ni sur un indice positif.
     * Un plafond total reste censure, avec delai de 180 jours avant nouvel essai. */
    if (now < old.used || (old.done && old.hints.len() == 0
        && now - old.date > (old.limited ? 180 : 30))) delete V233L_SITE_CACHE[key];
    else action = old.done ? "cached" : "continue";
  }
  if (!(key in V233L_SITE_CACHE)) {
    if (V233L_SITE_CACHE.len() >= V233L_SITE_CACHE_MAX) {
      local oldest = null, date = now + 1;
      foreach (k, entry in V233L_SITE_CACHE) if (entry.done && entry.used < date) { oldest = k; date = entry.used; }
      if (oldest != null) delete V233L_SITE_CACHE[oldest];
      else return { plans = [], stats = OpexV233LSiteStats(), reason = "capacity",
        ring = 0, ops = OpexOpsMeasureEnd(mark), length = length };
    }
    V233L_SITE_CACHE[key] <- { ring = 0, pos = 0, geometry = 0, done = false,
      date = now, used = now, stats = OpexV233LSiteStats(), hints = [],
      total = 0, slices = 0, limited = false, worked = -1,
      center = center, length = length, cargo = cargo, coverage = coverage, producing = producing,
      station = host == null ? -1 : host.station, railType = AIRail.GetCurrentRailType(),
      src = pair == null ? center : pair.src, dst = pair == null ? center : pair.dst,
      dstTown = pair == null ? -1 : pair.dstTown };
  }
  local scan = V233L_SITE_CACHE[key];
  scan.used = now;
  local plans = [];
  local industry = producing ? AIIndustry.GetIndustryID(center) : -1;
  /* Relire le monde meme pour un cache positif ; jamais reutiliser une preuve
   * native stale apres pose voisine, changement de note ou chargement. */
  foreach (hint in scan.hints) {
    local p = OpexV233LSiteProbe(hint.anchor, length, hint.axis, hint.sign, hint.side,
        cargo, coverage, producing, industry, scan.stats, host);
    if (p != null) plans.append(p);
  }
  if (scan.hints.len() > 0 && plans.len() == 0) {
    scan.hints.clear(); scan.done = false; scan.ring = 0; scan.pos = 0; scan.geometry = 0;
    scan.stats = OpexV233LSiteStats();
    scan.total = 0; scan.slices = 0; scan.limited = false; action = "invalidate";
  }
  local totalLimit = host == null ? V233L_SITE_TOTAL_OPS : V233L_JOIN_TOTAL_OPS;
  local startRing = scan.ring, startPos = scan.pos, startGeometry = scan.geometry;
  while (plans.len() < 4 && !scan.done && OpexOpsMeasureEnd(mark) < V233L_SLICE_OPS
      && scan.total + OpexOpsMeasureEnd(mark) < totalLimit) {
    local r = scan.ring, pos = scan.pos;
    local dx = 0, dy = 0;
    if (r > 0) {
      local edge = pos / (2 * r), order = pos % (2 * r);
      /* Milieu de chaque bord avant ses coins : distance au centre croissante. */
      local along = r + (order % 2 == 0 ? order / 2 : -(order + 1) / 2);
      if (edge == 0) { dx = -r + along; dy = -r; }
      else if (edge == 1) { dx = r; dy = -r + along; }
      else if (edge == 2) { dx = r - along; dy = r; }
      else { dx = -r; dy = r - along; }
    }
    local anchor = OpexV233LOffset(center, dx, dy);
    local clear = anchor >= 0 && OpexV233LFlat(anchor);
    /* Fenetre rapide spread x spread centree sur l'aeroport (12x12 au banc).
     * Le coin negatif de l'anneau pair est exclu pour ne pas scanner 13x13. */
    if (host != null && (dx < -((host.spread - 1) / 2) || dy < -((host.spread - 1) / 2))) clear = false;
    /* Un centre occupe refuse les huit geometries d'un coup. */
    if (!clear) { scan.geometry = 7; scan.stats.terrain++; }
    /* Une lecture d'acceptation par axe elimine ses quatre sorties/cotes avant
     * les boucles de terrain et les commandes natives. Pas de tri global cher. */
    if (clear && !producing && host == null && scan.geometry % 4 == 0) {
      local step = scan.geometry == 0 ? 1 : AIMap.GetMapSizeX();
      local last = OpexV233LOffset(anchor, scan.geometry == 0 ? length - 1 : 0,
          scan.geometry == 0 ? 0 : length - 1);
      if (last < 0 || OpexV233LCargoValue(anchor, step, length, cargo, coverage, false) < 8) {
        scan.geometry += 3; scan.stats.earlyAcceptance++; clear = false;
      }
    }
    local geometry = scan.geometry;
    scan.geometry++;
    if (scan.geometry == 8) {
      scan.geometry = 0; scan.pos++;
      if (scan.pos >= (r == 0 ? 1 : 8 * r)) { scan.pos = 0; scan.ring++; }
      if (scan.ring > radius) { scan.done = true; scan.date = now; }
    }
    if (!clear) continue;
    local axis = geometry / 4, sign = (geometry % 4) < 2 ? -1 : 1, side = geometry % 2 == 0 ? -1 : 1;
    local p = OpexV233LSiteProbe(anchor, length, axis, sign, side, cargo, coverage, producing, industry, scan.stats, host);
    if (p == null) continue;
    plans.append(p);
    scan.hints.append({ anchor = anchor, axis = axis, sign = sign, side = side });
  }
  /* Des que des plans existent, ils suffisent a l'admission ; pas de scan
   * jusqu'a douze resultats qui affame la destination. */
  if (plans.len() > 0) { scan.done = true; scan.date = now; }
  local ops = OpexOpsMeasureEnd(mark);
  /* Un indice positif revalide ne consomme pas une nouvelle recherche. */
  if (action != "cached") { scan.total += ops; scan.slices++; }
  scan.worked = AIController.GetTick();
  if (!scan.done && scan.total >= totalLimit) { scan.done = true; scan.limited = true; scan.date = now; }
  local reason = plans.len() > 0 ? "OK" : (scan.limited ? "total_budget" : (!scan.done ? "budget" : "exhausted"));
  if (DECISION_LOG) OpexV233LLog("SITE_STEP", "src=" + scan.src + " dst=" + scan.dst
      + " side=" + (producing ? "A" : "B") + " station=" + scan.station + " action=" + action
      + " from=" + startRing + ":" + startPos + ":" + startGeometry
      + " next=" + scan.ring + ":" + scan.pos + ":" + scan.geometry + " reason=" + reason
      + " slices=" + scan.slices + " ops=" + ops + " total_ops=" + scan.total + " limit=" + totalLimit
      + " early_acceptance=" + scan.stats.earlyAcceptance);
  return { plans = plans, stats = scan.stats, reason = reason, ring = scan.ring,
    ops = ops, length = length, cacheKey = key };
}

/* Rayon du carre urbain : 12 jusqu'a 3000 hab., puis +2 par millier au-dela,
 * plafond 18. */
function OpexV233LFunnelRadius(population)
{
  if (population <= 3000) return 12;
  local band = (population - 1) / 1000;
  local radius = 8 + 2 * band;
  if (radius > 18) radius = 18;
  return radius;
}

/* Deux quais seuls. Axe 0 : longueur en X et 2 en Y. L'ancre Valuate est
 * le coin Nord-Ouest (coordonnees minimales) de ce rectangle. */
function OpexV233LFunnelSpan(axis, length)
{
  return { w = axis == 0 ? length : 2, h = axis == 0 ? 2 : length };
}

function OpexV233LFunnelBox(center, radius, w, h)
{
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local minX = cx - radius;
  if (minX < 0) minX = 0;
  local minY = cy - radius;
  if (minY < 0) minY = 0;
  local maxX = cx + radius;
  local fitX = mapX - w;
  if (maxX > fitX) maxX = fitX;
  if (maxX >= mapX) maxX = mapX - 1;
  local maxY = cy + radius;
  local fitY = mapY - h;
  if (maxY > fitY) maxY = fitY;
  if (maxY >= mapY) maxY = mapY - 1;
  if (minX > maxX || minY > maxY) return null;
  return { minX = minX, minY = minY, maxX = maxX, maxY = maxY };
}

/* Liste native, une par axe. Pas de KeepTop : l'index squirrel reprend
 * apres reconstruction. L'acceptation retenue est strictement superieure a 7. */
function OpexV233LFunnelTiles(center, radius, w, h, cargo, coverage, entry)
{
  local box = OpexV233LFunnelBox(center, radius, w, h);
  if (box == null) return null;
  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(box.minX, box.minY), AIMap.GetTileIndex(box.maxX, box.maxY));
  entry.tiles = tiles.Count();
  tiles.Valuate(AITile.IsBuildableRectangle, w, h);
  tiles.KeepValue(1);
  entry.buildable = tiles.Count();
  tiles.Valuate(AITile.GetCargoAcceptance, cargo, w, h, coverage);
  tiles.KeepAboveValue(7);
  entry.accepting = tiles.Count();
  tiles.Sort(AIList.SORT_BY_VALUE, AIList.SORT_DESCENDING);
  return tiles;
}

function OpexV233LFunnelHas(entry, anchor)
{
  foreach (tile in entry.anchors) if (tile == anchor) return true;
  return false;
}

function OpexV233LFunnelQuayFlat(anchor, length, axis)
{
  local ux = axis == 0 ? 1 : 0;
  local uy = axis == 0 ? 0 : 1;
  local px = axis == 0 ? 0 : 1;
  local py = axis == 0 ? 1 : 0;
  for (local i = 0; i < length; i++) {
    if (!OpexV233LFlat(OpexV233LOffset(anchor, ux * i, uy * i))) return false;
    if (!OpexV233LFlat(OpexV233LOffset(anchor, ux * i + px, uy * i + py))) return false;
  }
  return true;
}

/* Le signe positif sort apres le quai. Le signe negatif place la tete
 * avant l'ancre, donc en coordonnees negatives. */
function OpexV233LFunnelSign(anchor, length, axis, source)
{
  local anchorCoord = axis == 0 ? AIMap.GetTileX(anchor) : AIMap.GetTileY(anchor);
  local sourceCoord = axis == 0 ? AIMap.GetTileX(source) : AIMap.GetTileY(source);
  local mid = anchorCoord + (length - 1) / 2;
  return sourceCoord >= mid ? 1 : -1;
}

function OpexV233LFunnelThroat(anchor, length, axis, sign)
{
  local ux = axis == 0 ? 1 : 0;
  local uy = axis == 0 ? 0 : 1;
  local px = axis == 0 ? 0 : 1;
  local py = axis == 0 ? 1 : 0;
  local leadIndex = sign > 0 ? length : -1;
  local lead = OpexV233LOffset(anchor, ux * leadIndex, uy * leadIndex);
  local lead2 = OpexV233LOffset(lead, px, py);
  if (!OpexV233LFlat(lead) || !OpexV233LFlat(lead2)) return false;
  return OpexV233LFlat(OpexV233LOffset(lead, -px, -py));
}

/* AITestMode reste dans OpexV233LSiteProbe. Un quai qui n'est plus plat
 * invalide l'ancre ; une tete refusee depend de la source et reste en cache. */
function OpexV233LFunnelTry(anchor, length, axis, source, cargo, coverage, stats, verdict)
{
  verdict.plan = null;
  verdict.drop = false;
  if (!OpexV233LFunnelQuayFlat(anchor, length, axis)) { verdict.drop = true; return; }
  local sign = OpexV233LFunnelSign(anchor, length, axis, source);
  if (!OpexV233LFunnelThroat(anchor, length, axis, sign)) return;
  verdict.plan = OpexV233LSiteProbe(anchor, length, axis, sign, 1, cargo, coverage, false, -1, stats, null);
}

function OpexV233LFunnelStop(entry, mark, charged)
{
  local spent = OpexOpsMeasureEnd(mark);
  local ops = spent - charged;
  if (entry.total + ops >= V233L_SITE_TOTAL_OPS) return "total_budget";
  if (spent >= V233L_SLICE_OPS) return "budget";
  return null;
}

/* Cle ville + axe, partagee entre les sources. Longueur, cargo et captage
 * restent dans la cle pour ne pas melanger des rectangles differents. */
function OpexV233LFunnelEnsure(town, axis, length, cargo, coverage)
{
  local now = AIDate.GetCurrentDate();
  local key = "funnel:" + town + ":" + axis + ":" + length + ":" + cargo + ":" + coverage;
  if (key in V233L_SITE_CACHE) {
    local old = V233L_SITE_CACHE[key];
    if (old.done && now - old.date > (old.limited ? 180 : 30)) delete V233L_SITE_CACHE[key];
    else { old.used = now; return old; }
  }
  if (V233L_SITE_CACHE.len() >= V233L_SITE_CACHE_MAX) {
    local oldest = null;
    local date = now + 1;
    foreach (k, item in V233L_SITE_CACHE)
      if (item.done && item.used < date) { oldest = k; date = item.used; }
    if (oldest != null) delete V233L_SITE_CACHE[oldest];
    else return null;
  }
  local entry = {
    funnel = true, town = town, axis = axis, length = length, cargo = cargo, coverage = coverage,
    radius = 0, anchors = [], cursor = 0, done = false, limited = false,
    date = now, used = now, total = 0, slices = 0, worked = -1,
    tiles = 0, buildable = 0, accepting = 0, probes = {}
  };
  V233L_SITE_CACHE[key] <- entry;
  return entry;
}

function OpexV233LFunnelRemove(entry, anchor)
{
  local kept = [];
  local removedAt = -1;
  for (local i = 0; i < entry.anchors.len(); i++) {
    if (removedAt < 0 && entry.anchors[i] == anchor) { removedAt = i; continue; }
    kept.append(entry.anchors[i]);
  }
  entry.anchors = kept;
  if (removedAt < 0 || typeof entry.probes != "table") return;
  foreach (src, probe in entry.probes) {
    if (typeof probe != "table") continue;
    if (probe.hint == anchor) probe.hint = -1;
    if (probe.index > removedAt) probe.index--;
  }
}

/* Remplit les ancres plates. Ne sonde pas : la tete depend de la source.
 * Le budget se lit entre les lots, pas au milieu d'un lot de cinq. */
function OpexV233LFunnelAdvance(entry, center, radius, mark, charged)
{
  local stop = OpexV233LFunnelStop(entry, mark, charged);
  if (stop != null) return { checked = 0, reason = stop };
  if (entry.radius != radius) {
    entry.radius = radius;
    entry.anchors = [];
    entry.cursor = 0;
    entry.done = false;
    entry.limited = false;
    entry.probes = {};
  }
  local span = OpexV233LFunnelSpan(entry.axis, entry.length);
  local tiles = OpexV233LFunnelTiles(center, radius, span.w, span.h, entry.cargo, entry.coverage, entry);
  if (tiles == null) {
    entry.tiles = 0;
    entry.buildable = 0;
    entry.accepting = 0;
    entry.done = true;
    entry.limited = false;
    entry.date = AIDate.GetCurrentDate();
    return { checked = 0, reason = "exhausted" };
  }
  local checked = 0;
  local batch = 0;
  local index = 0;
  for (local tile = tiles.Begin(); !tiles.IsEnd(); tile = tiles.Next()) {
    if (index < entry.cursor) { index++; continue; }
    if (batch == V233L_FUNNEL_BATCH) {
      local halt = OpexV233LFunnelStop(entry, mark, charged);
      if (halt != null) return { checked = checked, reason = halt };
      batch = 0;
    }
    entry.cursor = index + 1;
    checked++;
    batch++;
    index++;
    if (OpexV233LFunnelQuayFlat(tile, entry.length, entry.axis)
        && entry.anchors.len() < V233L_FUNNEL_ANCHORS
        && !OpexV233LFunnelHas(entry, tile)) entry.anchors.append(tile);
    if (entry.anchors.len() >= V233L_FUNNEL_ANCHORS) break;
  }
  entry.done = true;
  entry.limited = false;
  entry.date = AIDate.GetCurrentDate();
  return { checked = checked, reason = "exhausted" };
}

function OpexV233LFunnelProbeRow(entry, source)
{
  if (!("probes" in entry) || typeof entry.probes != "table") entry.probes = {};
  if (!(source in entry.probes))
    entry.probes.rawset(source, { index = 0, hint = -1, done = false });
  return entry.probes[source];
}

/* hint est l'index de tuile deja accepte, jamais le resultat AITestMode.
 * Chaque source ne refait que la tete orientee et la sonde. */
function OpexV233LFunnelProbe(entry, source, coverage, stats, plans, mark, charged)
{
  local stop = OpexV233LFunnelStop(entry, mark, charged);
  if (stop != null) return { checked = 0, ok = 0, reason = stop };
  local probe = OpexV233LFunnelProbeRow(entry, source);
  local checked = 0;
  local ok = 0;
  local batch = 0;
  local verdict = { plan = null, drop = false };
  if (probe.hint >= 0) {
    if (!OpexV233LFunnelHas(entry, probe.hint)) probe.hint = -1;
    else {
      OpexV233LFunnelTry(probe.hint, entry.length, entry.axis, source, entry.cargo, coverage, stats, verdict);
      checked++;
      batch++;
      if (verdict.drop) {
        OpexV233LFunnelRemove(entry, probe.hint);
        probe.hint = -1;
      } else if (verdict.plan != null) {
        if (plans.len() < 4) plans.append(verdict.plan);
        ok++;
      } else probe.hint = -1;
    }
  }
  while (plans.len() < 4 && probe.index < entry.anchors.len()) {
    if (batch == V233L_FUNNEL_BATCH) {
      local halt = OpexV233LFunnelStop(entry, mark, charged);
      if (halt != null) return { checked = checked, ok = ok, reason = halt };
      batch = 0;
    }
    local anchor = entry.anchors[probe.index];
    if (anchor == probe.hint) { probe.index++; continue; }
    verdict.plan = null;
    verdict.drop = false;
    OpexV233LFunnelTry(anchor, entry.length, entry.axis, source, entry.cargo, coverage, stats, verdict);
    checked++;
    batch++;
    if (verdict.drop) {
      OpexV233LFunnelRemove(entry, anchor);
      continue;
    }
    probe.index++;
    if (verdict.plan != null) {
      plans.append(verdict.plan);
      probe.hint = anchor;
      ok++;
    }
  }
  local reason = "exhausted";
  if (ok > 0) reason = "OK";
  else if (probe.index < entry.anchors.len() || !entry.done) reason = "budget";
  else probe.done = true;
  return { checked = checked, ok = ok, reason = reason };
}

function OpexV233LFunnelTrace(town, axis, radius, tiles, buildable, accepting, checked, ok, ops, reason)
{
  if (!DECISION_LOG) return;
  OpexV233LLog("SITE_FUNNEL", "town=" + town + " axis=" + axis + " radius=" + radius
      + " tiles=" + tiles + " buildable=" + buildable + " accepting=" + accepting
      + " checked=" + checked + " ok=" + ok + " ops=" + ops + " reason=" + reason);
}

function OpexV233LFunnelSearch(candidate, length, coverage)
{
  local mark = OpexOpsMeasureBegin();
  local plans = [];
  local stats = OpexV233LSiteStats();
  local town = ("dstTown" in candidate) ? candidate.dstTown : -1;
  local ops = 0;
  if (town < 0 || !AITown.IsValidTown(town)) {
    ops = OpexOpsMeasureEnd(mark);
    OpexV233LFunnelTrace(town, -1, 0, 0, 0, 0, 0, 0, ops, "exhausted");
    return { plans = plans, stats = stats, reason = "exhausted", ring = 0, ops = ops, length = length };
  }
  local center = AITown.GetLocation(town);
  local radius = OpexV233LFunnelRadius(AITown.GetPopulation(town));
  local charged = 0;
  local sawBudget = false;
  local sawTotal = false;
  local sawCapacity = false;
  local lastRing = 0;
  local cargo = candidate.cargo;
  local source = candidate.src;
  for (local axis = 0; axis < 2 && plans.len() < 4; axis++) {
    local entry = OpexV233LFunnelEnsure(town, axis, length, cargo, coverage);
    if (entry == null) {
      sawCapacity = true;
      OpexV233LFunnelTrace(town, axis, radius, 0, 0, 0, 0, 0, 0, "capacity");
      break;
    }
    local checked = 0;
    local ok = 0;
    local axisReason = entry.done ? "exhausted" : "budget";
    if (!entry.done) {
      local step = OpexV233LFunnelAdvance(entry, center, radius, mark, charged);
      checked = step.checked;
      axisReason = step.reason;
    }
    if (plans.len() < 4 && axisReason != "budget" && axisReason != "total_budget") {
      local probed = OpexV233LFunnelProbe(entry, source, coverage, stats, plans, mark, charged);
      checked += probed.checked;
      ok = probed.ok;
      axisReason = probed.reason;
    }
    local nowOps = OpexOpsMeasureEnd(mark);
    ops = nowOps - charged;
    entry.total += ops;
    charged = nowOps;
    entry.slices++;
    entry.used = AIDate.GetCurrentDate();
    entry.worked = AIController.GetTick();
    if (!entry.done && entry.total >= V233L_SITE_TOTAL_OPS) {
      entry.done = true;
      entry.limited = true;
      entry.date = entry.used;
      axisReason = "total_budget";
    }
    if (axisReason == "budget") sawBudget = true;
    if (axisReason == "total_budget") sawTotal = true;
    lastRing = entry.cursor;
    OpexV233LFunnelTrace(town, axis, radius, entry.tiles, entry.buildable, entry.accepting,
        checked, ok, ops, axisReason);
  }
  local verdict = plans.len() > 0 ? "OK" : (sawBudget ? "budget" : (sawTotal ? "total_budget"
      : (sawCapacity ? "capacity" : "exhausted")));
  return { plans = plans, stats = stats, reason = verdict, ring = lastRing,
    ops = OpexOpsMeasureEnd(mark), length = length };
}

function OpexV233LFunnelBackground(entry)
{
  local mark = OpexOpsMeasureBegin();
  local town = entry.town;
  local reason = "exhausted";
  local checked = 0;
  if (!AITown.IsValidTown(town)) {
    entry.done = true;
    entry.date = AIDate.GetCurrentDate();
  } else if (!entry.done) {
    local center = AITown.GetLocation(town);
    local radius = OpexV233LFunnelRadius(AITown.GetPopulation(town));
    local step = OpexV233LFunnelAdvance(entry, center, radius, mark, 0);
    checked = step.checked;
    reason = step.reason;
  }
  local ops = OpexOpsMeasureEnd(mark);
  entry.total += ops;
  entry.slices++;
  entry.used = AIDate.GetCurrentDate();
  entry.worked = AIController.GetTick();
  if (!entry.done && entry.total >= V233L_SITE_TOTAL_OPS) {
    entry.done = true;
    entry.limited = true;
    entry.date = entry.used;
    reason = "total_budget";
  }
  OpexV233LFunnelTrace(town, entry.axis, entry.radius, entry.tiles, entry.buildable,
      entry.accepting, checked, 0, ops, reason);
}

function OpexV233LFunnelDrop(town, anchor)
{
  if (V233_SITE_FUNNEL <= 0 || town < 0 || anchor < 0) return;
  foreach (key, entry in V233L_SITE_CACHE) {
    if (!("funnel" in entry) || !entry.funnel || entry.town != town) continue;
    OpexV233LFunnelRemove(entry, anchor);
  }
}

function OpexV233LLoadFunnel(scan)
{
  foreach (field in ["town", "axis", "radius", "length", "cargo", "coverage", "cursor",
      "date", "used", "total", "slices", "worked", "tiles", "buildable", "accepting"])
    if (!(field in scan) || typeof scan[field] != "integer") return false;
  foreach (field in ["done", "limited", "funnel"])
    if (!(field in scan) || typeof scan[field] != "bool") return false;
  if (scan.town < 0 || (scan.axis != 0 && scan.axis != 1) || scan.radius < 0 || scan.radius > 18
      || scan.length < 1 || scan.length > 64 || scan.cargo < 0 || scan.coverage < 0
      || scan.coverage > 64 || scan.cursor < 0 || scan.cursor > 4096 || scan.total < 0
      || scan.slices < 0 || scan.tiles < 0 || scan.buildable < 0 || scan.accepting < 0
      || (scan.limited && !scan.done)) return false;
  if (!("anchors" in scan) || typeof scan.anchors != "array"
      || scan.anchors.len() > V233L_FUNNEL_ANCHORS) return false;
  foreach (anchor in scan.anchors)
    if (typeof anchor != "integer" || anchor < 0) return false;
  if (!("probes" in scan) || scan.probes == null) scan.probes = {};
  else if (typeof scan.probes != "table") return false;
  else {
    foreach (src, probe in scan.probes) {
      if (typeof src != "integer" || typeof probe != "table") return false;
      if (!("index" in probe) || typeof probe.index != "integer" || probe.index < 0) return false;
      if (!("hint" in probe) || typeof probe.hint != "integer" || probe.hint < -1) return false;
      if (!("done" in probe) || typeof probe.done != "bool") return false;
    }
  }
  return true;
}

/* Une seule tranche par tour, la recherche la moins recemment travaillee.
 * Ne depend plus du prochain rafraichissement (parfois annuel) du portefeuille.
 * Aucun candidat financier n'est conserve/publie par ce worker. */
function OpexV233LContinueSites()
{
  local selected = null, selectedKey = null;
  foreach (key, scan in V233L_SITE_CACHE) {
    if (scan.done) continue;
    if (selected == null || scan.worked < selected.worked) { selected = scan; selectedKey = key; }
  }
  if (selected == null) return;
  /* Entree d'entonnoir : ne jamais la relancer comme une spirale.
   * Reglage a 0 : la clore, sinon elle resterait la plus ancienne. */
  if (("funnel" in selected) && selected.funnel) {
    if (V233_SITE_FUNNEL <= 0) {
      selected.done = true;
      selected.date = AIDate.GetCurrentDate();
      return;
    }
    OpexV233LFunnelBackground(selected);
    return;
  }
  local host = null;
  if (selected.station >= 0) {
    host = OpexV233LJoinHost(selected.station, selected.dstTown, selected.cargo);
    if (host.reason != "OK") {
      selected.done = true; selected.date = AIDate.GetCurrentDate();
      if (DECISION_LOG) OpexV233LLog("SITE_B_JOIN", "src=" + selected.src + " dst=" + selected.dst
          + " phase=background station=" + selected.station + " reason=" + host.reason + " ok=0");
      return;
    }
  }
  local railType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(selected.railType);
  local center = host == null ? selected.center
      : AIMap.GetTileIndex((host.left + host.right) / 2, (host.top + host.bottom) / 2);
  local result = OpexV233LSiteSearch(center, selected.length, selected.cargo,
      selected.coverage, selected.producing, host, selected);
  AIRail.SetCurrentRailType(railType);
  /* Une extension de l'hote change la cle ; ne pas laisser son ancien scan
   * inacheve reprendre indefiniment. La nouvelle entree garde sa propre borne. */
  if (!("cacheKey" in result) || result.cacheKey != selectedKey) delete V233L_SITE_CACHE[selectedKey];
  if (DECISION_LOG) OpexV233LSiteLog(selected, result, selected.producing ? "A" : "B", "background");
}

/* NoAI 15.3 n'expose pas GetCargoAcceptance sur AIStation. La liste de
 * couverture est le masque moteur (union dedupliquee, arrets C33.2 inclus).
 * radius=0 n'est respecte par AITile qu'avec modified_catchment actif. */
function OpexV233LJoinHost(station, town, cargo)
{
  local host = { station = station, reason = "host", acceptance = 0,
    left = AIMap.GetMapSizeX(), top = AIMap.GetMapSizeY(), right = -1, bottom = -1,
    spread = AIGameSettings.GetValue("station.station_spread") };
  if (!AIStation.IsValidStation(station) || !AIStation.HasStationType(station, AIStation.STATION_AIRPORT)
      || AIStation.GetNearestTown(station) != town) return host;
  local airport = AITileList_StationType(station, AIStation.STATION_AIRPORT);
  if (airport.IsEmpty() || AITile.GetOwner(airport.Begin()) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) return host;
  if (!AIGameSettings.GetValue("station.distant_join_stations")) { host.reason = "join_disabled"; return host; }
  if (!AIGameSettings.GetValue("station.modified_catchment")) { host.reason = "catchment_mode"; return host; }
  local parts = AITileList_StationType(station, AIStation.STATION_ANY);
  for (local t = parts.Begin(); !parts.IsEnd(); t = parts.Next()) {
    local x = AIMap.GetTileX(t), y = AIMap.GetTileY(t);
    host.left = min(host.left, x); host.right = max(host.right, x);
    host.top = min(host.top, y); host.bottom = max(host.bottom, y);
  }
  if (host.right < 0 || host.right - host.left + 1 > host.spread
      || host.bottom - host.top + 1 > host.spread) { host.reason = "spread"; return host; }
  local catchment = AITileList_StationCoverage(station);
  for (local t = catchment.Begin(); !catchment.IsEnd(); t = catchment.Next()) {
    local value = AITile.GetCargoAcceptance(t, cargo, 1, 1, 0);
    if (value < 0) { host.reason = "acceptance_unknown"; return host; }
    host.acceptance += value;
    if (host.acceptance >= 8) break;
  }
  host.reason = host.acceptance >= 8 ? "OK" : "acceptance";
  return host;
}

function OpexV233LJoinFits(host, first, last)
{
  return max(host.right, AIMap.GetTileX(last)) - min(host.left, AIMap.GetTileX(first)) + 1 <= host.spread
      && max(host.bottom, AIMap.GetTileY(last)) - min(host.top, AIMap.GetTileY(first)) + 1 <= host.spread;
}

function OpexV233LJoinSearch(candidate, length, coverage, phase)
{
  local mark = OpexOpsMeasureBegin();
  local result = { plans = [], stats = OpexV233LSiteStats(), reason = "no_airport",
    ring = 0, ops = 0, length = length };
  local stations = AIStationList(AIStation.STATION_AIRPORT);
  local ids = [];
  for (local id = stations.Begin(); !stations.IsEnd(); id = stations.Next())
    if (AIStation.GetNearestTown(id) == candidate.dstTown) ids.append(id);
  local key = candidate.src + ":" + candidate.dst + ":" + length + ":" + candidate.cargo;
  if (!(key in V233L_JOIN_CURSOR)) {
    if (V233L_JOIN_CURSOR.len() >= V233L_SITE_CACHE_MAX) V233L_JOIN_CURSOR.clear();
    V233L_JOIN_CURSOR[key] <- 0;
  }
  local start = V233L_JOIN_CURSOR[key];
  for (local i = 0; i < ids.len(); i++) {
    local index = (start + i) % ids.len();
    local host = OpexV233LJoinHost(ids[index], candidate.dstTown, candidate.cargo);
    local reason = host.reason;
    /* Ne pas attribuer les compteurs du precedent aeroport a cet hote. */
    result = { plans = [], stats = OpexV233LSiteStats(), reason = reason,
      ring = 0, ops = 0, length = length };
    if (reason == "OK") {
      result = OpexV233LSiteSearch(AIMap.GetTileIndex((host.left + host.right) / 2, (host.top + host.bottom) / 2), length,
          candidate.cargo, coverage, false, host, candidate);
      reason = result.reason;
    }
    if (DECISION_LOG) OpexV233LLog("SITE_B_JOIN", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=" + phase + " station=" + host.station + " ok=" + (result.plans.len() > 0 ? 1 : 0)
        + " reason=" + reason + " acceptance=" + host.acceptance + " spread=" + host.spread
        + " terrain=" + result.stats.terrain + " parallel=" + result.stats.parallel
        + " authority=" + result.stats.authority + " native=" + result.stats.native
        + " spread_refused=" + result.stats.spread + " error=" + result.stats.error
        + " scan_ops=" + result.ops + " ops=" + OpexOpsMeasureEnd(mark));
    if (result.plans.len() > 0 || reason == "budget") {
      V233L_JOIN_CURSOR[key] = index;
      result.ops = OpexOpsMeasureEnd(mark);
      return result;
    }
    result.reason = reason;
    V233L_JOIN_CURSOR[key] = (index + 1) % ids.len();
    if (i + 1 < ids.len() && OpexOpsMeasureEnd(mark) >= V233L_SLICE_OPS) {
      result.reason = "budget"; break;
    }
  }
  result.ops = OpexOpsMeasureEnd(mark);
  if (ids.len() == 0 && DECISION_LOG) OpexV233LLog("SITE_B_JOIN", "src=" + candidate.src
      + " dst=" + candidate.dst + " phase=" + phase + " station=-1 ok=0 reason=no_airport");
  return result;
}

function OpexV233LTariffTile(platform)
{
  return ("stationId" in platform) ? AIStation.GetLocation(platform.stationId) : platform.anchor;
}

/* Avant devis/depense : la station a pu s'etendre pendant A*. Proteger ses
 * tuiles et les routes de desserte dans sa boite (+1), y compris C33.2.
 * Le rollback commun retire des tuiles rail, jamais la station composite. */
function OpexV233LJoinRouteClear(candidate, plan)
{
  if (!("v233Airport" in plan.planB)) return true;
  local host = OpexV233LJoinHost(plan.planB.v233Airport, candidate.dstTown, candidate.cargo);
  local reason = host.reason;
  local parts = AITileList_StationType(host.station, AIStation.STATION_ANY);
  if (reason == "OK") {
    foreach (path in [plan.tiles, plan.tiles2]) {
      if (path == null) { reason = "double_missing"; break; }
      foreach (t in path) {
        local x = AIMap.GetTileX(t), y = AIMap.GetTileY(t);
        if (parts.HasItem(t) || (AIRoad.IsRoadTile(t) && x >= host.left - 1 && x <= host.right + 1
            && y >= host.top - 1 && y <= host.bottom + 1)) { reason = "protected_route"; break; }
      }
      if (reason != "OK") break;
    }
  }
  if (reason == "OK") {
    local p = plan.planB, q = plan.planB2;
    if (q == null || p.step != q.step || p.length != q.length) reason = "double_geometry";
    else {
      local first = min(p.anchor, q.anchor), last = max(p.anchor, q.anchor) + (p.length - 1) * p.step;
      local sideways = p.step == 1 ? AIMap.GetMapSizeX() : 1;
      if (abs(p.anchor - q.anchor) != sideways || !OpexV233LJoinFits(host, first, last)) reason = "spread";
      foreach (platform in [p, q]) {
        if (!OpexV233LFlat(platform.lead)) reason = "occupied";
        for (local i = 0; i < platform.length; i++)
          if (!OpexV233LFlat(platform.anchor + i * platform.step)) reason = "occupied";
      }
      if (reason == "OK") {
        local accounting = AIAccounting();
        local test = AITestMode();
        if (!AIRail.BuildRailStation(first, p.direction, 2, p.length, host.station)) reason = "native";
      }
    }
  }
  if (DECISION_LOG) OpexV233LLog("SITE_B_JOIN", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=recheck station=" + host.station + " ok=" + (reason == "OK" ? 1 : 0) + " reason=" + reason);
  return reason == "OK";
}

function OpexV233LSiteLog(candidate, scan, side, phase)
{
  local s = scan.stats;
  OpexV233LLog("SITE", "src=" + candidate.src + " dst=" + candidate.dst + " side=" + side
      + " phase=" + phase + " reason=" + scan.reason + " plans=" + scan.plans.len()
      + " length=" + scan.length + " ring=" + scan.ring + " ops=" + scan.ops
      + " clear=" + s.nClear + " cargo=" + s.nCargo + " cmd=" + s.nCmd
      + " terrain=" + s.terrain + " acceptance=" + s.acceptance + " parallel=" + s.parallel
      + " authority=" + s.authority + " native=" + s.native + " catchment=" + s.catchment
      + " spread=" + s.spread + " error=" + s.error);
  foreach (p in scan.plans) OpexV233LLog("SITE_PLAN", "src=" + candidate.src + " dst=" + candidate.dst
      + " side=" + side + " phase=" + phase + " anchor=" + p.anchor + " parallel=" + p.parallel.anchor
      + " direction=" + p.direction + " length=" + p.length + " exit=" + p.station_exit + " lead=" + p.lead
      + " cargo_value=" + p.cargoValue + " threshold=" + (side == "B" ? 8 : 1));
}

/* Seule exception de proximite : cote A, quai NON-GOOD livrant exactement
 * cette usine. Cote B et tous les autres voisins restent controles. */
function OpexV233LSourceNeighbour(candidate, line, end)
{
  return OpexV233LIs(candidate) && end == "A" && line.originB == candidate.src
      && line.cargo != candidate.cargo;
}

function OpexV233LTick(owner)
{
  if (!SAVE_FULL_STATE) return; // transactions et identites exigent la sauvegarde complete.
  if (V233L_STATE == null) V233L_STATE = OpexV233LNewState();
  OpexV233LObserve(owner);
  OpexV233LContinueSites();
  OpexV233LContinueGrowth(owner);
}

function OpexV233LRecheck(candidate, plan)
{
  local industry = AIIndustry.GetIndustryID(candidate.src);
  if (V233L_STATE == null || !(industry in V233L_STATE.rows) || plan.doubleTrack != 1
      || plan.planA == null || plan.planB == null) return false;
  local row = V233L_STATE.rows[industry];
  if (!OpexV233LFresh(row.month, OpexV233LMonth())
      || !OpexV233LDurable(row) || OpexV233LMean(row.residual) < candidate.monthly) return false;
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  if (!OpexV233LTouches(plan.planA, industry, true, coverage)) return false;
  if ("v233Airport" in plan.planB) {
    if (!OpexV233LJoinRouteClear(candidate, plan)) return false;
  } else if (OpexV233LCargoValue(plan.planB.anchor, plan.planB.step, plan.planB.length,
      candidate.cargo, coverage, false) < 8) return false;
  local sourceTile = ("stationId" in plan.planA) ? AIStation.GetLocation(plan.planA.stationId) : plan.planA.anchor;
  local distance = AIMap.DistanceManhattan(sourceTile, OpexV233LTariffTile(plan.planB));
  return distance >= 150 && distance <= 300;
}

function OpexV233LInputTarget(line)
{
  if (V233L_STATE == null || line == null || !("originB" in line)) return false;
  local industry = AIIndustry.GetIndustryID(line.originB);
  if (!(industry in V233L_STATE.rows)) return false;
  local row = V233L_STATE.rows[industry];
  if (row.exportLine < 0 || row.exportMonth < OpexV233LMonth() - 1) return false;
  if (!OpexV233LFresh(row.month, OpexV233LMonth()) || !OpexV233LDurable(row)) return false;
  return OpexV233LInput(line, OpexV233LGoodCargo()) == industry;
}

function OpexV233LObserveBacklog(line, month)
{
  if (line == null || !("mode" in line) || line.mode != "rail"
      || !("vehicles" in line) || line.vehicles.len() == 0 || !("lineId" in line)) return;
  if (OpexV233LIs(line) && (!("scrapping" in line) || !line.scrapping)
      && AIVehicle.IsValidVehicle(line.vehicles[0])) {
    local industry = AIIndustry.GetIndustryID(line.originA);
    if (industry in V233L_STATE.rows) {
      V233L_STATE.rows[industry].exportLine = line.lineId;
      V233L_STATE.rows[industry].exportMonth = month;
    }
  }
  if (!OpexV233LIs(line) && !OpexV233LInputTarget(line)) return;
  local station = OpexLineStationId(line, "A");
  if (station < 0) return;
  local growth = V233L_STATE.growth;
  if (!(line.lineId in growth)) {
    if (growth.len() >= 128) return;
    growth.rawset(line.lineId, { month = -1, waiting = [], nextMonth = -1 });
  }
  local row = growth[line.lineId];
  if (row.month == month) return;
  if (row.month != month - 1) row.waiting = [];
  row.month = month;
  row.waiting.append(AIStation.GetCargoWaiting(station, line.cargo));
  if (row.waiting.len() > 3) row.waiting.remove(0);
}

function OpexV233LBacklog(line, waiting, required)
{
  if (V233L_STATE == null || !(line.lineId in V233L_STATE.growth)) return false;
  local row = V233L_STATE.growth[line.lineId];
  return row.month == OpexV233LMonth() && row.month >= row.nextMonth
      && row.waiting.len() == 3 && waiting >= required && OpexV233LMin(row.waiting) >= required;
}

/* Capacite mensuelle et tarif issus de la physique C41 et de l'API du jeu.
 * Le stock confirme l'exposition, il n'est jamais annualise. */
function OpexV233LFleetMargin(line, vehicle, added, newLoco, newWagons, extraCost = 0)
{
  local industry = AIIndustry.GetIndustryID(line.originA);
  if (!AIIndustry.IsValidIndustry(industry)) return null;
  local production = AIIndustry.GetLastMonthProduction(industry, line.cargo);
  local station = OpexLineStationId(line, "A");
  if (station < 0 || production <= 0) return null;
  local rating = AIStation.GetCargoRating(station, line.cargo);
  if (rating <= 0) return null;
  local wagon = OpexV257Engine(AIVehicle.GetWagonEngineType(vehicle, 1), line.cargo, true);
  local oldLoco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
  local oldWagons = AIVehicle.GetNumWagons(vehicle) - 1;
  local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
  local oldSpeed = OpexRailEffectiveSpeed(oldLoco, wagon, oldWagons, distance);
  local newSpeed = OpexRailEffectiveSpeed(newLoco, wagon, newWagons, distance);
  if (oldSpeed <= 0 || newSpeed < oldSpeed) return null;
  local oldDays = distance / (0.036 * oldSpeed);
  local newDays = distance / (0.036 * newSpeed);
  local dwell = OpexRailStationDwellDays(wagon);
  local oldCapacity = AIVehicle.GetCapacity(vehicle, line.cargo) * 30.0 / (2 * oldDays + dwell);
  local newCapacity = newWagons * wagon.capacity * 30.0 / (2 * newDays + dwell);
  local offered = production * rating / 100.0;
  /* Pour une sortie neuve, ne pas promettre les flux pris par les rivaux. */
  if (OpexV233LIs(line)) {
    local factory = AIIndustry.GetIndustryID(line.originA);
    if (!(factory in V233L_STATE.rows)) return null;
    local row = V233L_STATE.rows[factory];
    if (!OpexV233LFresh(row.month, OpexV233LMonth()) || !OpexV233LDurable(row)) return null;
    offered = OpexV233LMean(row.production) * rating / 100.0;
  }
  local before = line.vehicles.len() * oldCapacity;
  local after = added ? before + newCapacity : before - oldCapacity + newCapacity;
  if (before > offered) before = offered;
  if (after > offered) after = offered;
  local delta = after - before;
  if (delta <= 0) return null;
  local loadDays = newWagons * wagon.capacity * 30.0 / offered;
  local income = AICargo.GetCargoIncome(line.cargo, line.distance, OpexCeilDiv(newDays + loadDays / 2, 1));
  local cost = newLoco.price + newWagons * wagon.price + extraCost;
  local running = newLoco.runningCost - (added ? 0 : oldLoco.runningCost);
  local profit = 12 * delta * income - running - cost / (newLoco.ageYears > 0 ? newLoco.ageYears : 20);
  if (profit <= 0 || OpexAvailableCapital() < cost + OpexCashReserve()) return null;
  return { profit = profit, cost = cost, monthly = delta };
}

function OpexV233LInputMargin(line, selected, equipment, number, loopPlan)
{
  local loco = OpexV257Engine(equipment.engine, line.cargo, false);
  local infrastructure = loopPlan == null ? 0 : loopPlan.pieces.len() * AIRail.GetBuildCost(
      AIRail.GetRailType(line.depot), AIRail.BT_TRACK);
  local margin = OpexV233LFleetMargin(line, selected.vehicle, selected.add, loco, number, infrastructure);
  if (margin == null) {
    if (DECISION_LOG) OpexV233LLog("REJECT", "line=" + line.lineId + " reason=input_margin");
    return false;
  }
  V233L_STATE.growth[line.lineId].nextMonth = OpexV233LMonth() + 3;
  if (DECISION_LOG) OpexV233LLog("INPUT_PICK", "line=" + line.lineId + " monthly=" + margin.monthly + " profit=" + margin.profit);
  return true;
}

function OpexV233LSelectGrowth(owner, year)
{
  if (!SAVE_FULL_STATE || V233L_STATE == null || owner._lines == null || owner._v257Pending != null
      || owner._railExpansion != null || OpexV284Busy(owner) || V233L_STATE.pending != null) return false;
  local mark = OpexOpsMeasureBegin();
  local best = null;
  foreach (line in owner._lines) {
    if (OpexOpsMeasureEnd(mark) >= V233L_SLICE_OPS) break;
    local exportGood = OpexV233LIs(line);
    local input = !exportGood && OpexV233LInputTarget(line);
    if ((!exportGood && !input) || line.vehicles.len() < 2 || line.vehicles.len() >= 14
        || !("v181Loop" in line) || !line.v181Loop || line.doubleTrack != 1
        || (("scrapping" in line) && line.scrapping) || OpexV163Wagons2(line) > 0) continue;
    local vehicle = line.vehicles[0];
    if (!AIVehicle.IsValidVehicle(vehicle) || AIVehicle.GetNumWagons(vehicle) < 2) continue;
    local wagonId = AIVehicle.GetWagonEngineType(vehicle, 1);
    if (!AIEngine.IsWagon(wagonId) || !AIEngine.IsBuildable(wagonId)
        || AIEngine.GetCargoType(wagonId) != line.cargo
        || AIEngine.GetCapacity(AIVehicle.GetEngineType(vehicle)) > 0
        || AIVehicle.GetLength(vehicle) > OpexV284Limit(line) * 16) continue;
    local homogeneous = true;
    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v) || AIVehicle.GetEngineType(v) != AIVehicle.GetEngineType(vehicle)
          || AIVehicle.GetNumWagons(v) != AIVehicle.GetNumWagons(vehicle)
          || AIVehicle.GetCapacity(v, line.cargo) != AIVehicle.GetCapacity(vehicle, line.cargo)) homogeneous = false;
      if (!AIVehicle.IsValidVehicle(v)) continue;
      for (local w = 1; w < AIVehicle.GetNumWagons(v); w++)
        if (AIVehicle.GetWagonEngineType(v, w) != wagonId) homogeneous = false;
    }
    if (!homogeneous) continue;
    local station = OpexLineStationId(line, "A");
    if (station < 0) continue;
    local waiting = AIStation.GetCargoWaiting(station, line.cargo);
    if (!OpexV233LBacklog(line, waiting, AIVehicle.GetCapacity(vehicle, line.cargo))) continue;
    local loco = OpexV257Engine(AIVehicle.GetEngineType(vehicle), line.cargo, false);
    local number = AIVehicle.GetNumWagons(vehicle) - 1;
    local margin = OpexV233LFleetMargin(line, vehicle, true, loco, number);
    if (margin == null) {
      if (DECISION_LOG) OpexV233LLog("REJECT", "line=" + line.lineId + " reason=export_margin");
      continue;
    }
    if (best == null || margin.profit / margin.cost > best.score) best = {
      line = line, vehicle = vehicle, score = margin.profit / margin.cost, margin = margin };
  }
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=growth ops=" + OpexOpsMeasureEnd(mark) + " budget=" + V233L_SLICE_OPS);
  if (best == null) return OpexV284Select(owner, year, true);
  if (!OpexRailVehicleSlotAvailable() || !AIRail.IsRailDepotTile(best.line.depot)) return false;
  V233L_STATE.pending = { lineId = best.line.lineId, vehicle = best.vehicle,
    newVehicle = -1, depot = best.line.depot, phase = "prepare", before = null };
  V233L_STATE.growth[best.line.lineId].nextMonth = OpexV233LMonth() + 3;
  if (DECISION_LOG) OpexV233LLog("GROW_PICK", "line=" + best.line.lineId + " monthly=" + best.margin.monthly
      + " profit=" + best.margin.profit + " cost=" + best.margin.cost);
  return true;
}

/* Transaction de renfort GOOD : identite avant lancement, adoption idempotente
 * et nettoyage des vehicules crees au depot si Save interrompt la construction. */
function OpexV233LContinueGrowth(owner)
{
  if (V233L_STATE.pending == null) return;
  local mark = OpexOpsMeasureBegin();
  OpexV233LGrowthStep(owner);
  if (DECISION_LOG) OpexV233LLog("OPS", "phase=growth_execute ops=" + OpexOpsMeasureEnd(mark));
}

function OpexV233LGrowthStep(owner)
{
  local pending = V233L_STATE.pending;
  if (pending == null) return;
  local line = owner._findLineById(pending.lineId);
  if (pending.phase == "rollback") {
    if (AIVehicle.IsValidVehicle(pending.newVehicle)) OpexV257Discard(owner, pending.newVehicle);
    if (pending.before != null) {
      local vehicles = AIVehicleList();
      for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next())
        if (AIVehicle.IsStoppedInDepot(v) && AIVehicle.GetLocation(v) == pending.depot
            && !OpexWaterContains(pending.before, v)
            && OpexFindLineForVehicle(owner._lines, v) == null) OpexV257Discard(owner, v);
    }
    V233L_STATE.pending = null;
    return;
  }
  if (line == null || !AIVehicle.IsValidVehicle(pending.vehicle)
      || (("scrapping" in line) && line.scrapping)) { pending.phase = "rollback"; return; }
  if (pending.phase == "prepare") {
    if (!OpexRailVehicleSlotAvailable() || !AIRail.IsRailDepotTile(pending.depot)) { V233L_STATE.pending = null; return; }
    local loco = OpexV257Engine(AIVehicle.GetEngineType(pending.vehicle), line.cargo, false);
    local wagons = AIVehicle.GetNumWagons(pending.vehicle) - 1;
    local margin = OpexV233LFleetMargin(line, pending.vehicle, true, loco, wagons);
    if (margin == null || !AIEngine.IsBuildable(loco.id)) { V233L_STATE.pending = null; return; }
    local vehicles = AIVehicleList();
    if (vehicles.Count() > 2048) { V233L_STATE.pending = null; return; }
    pending.before = [];
    for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next())
      if (AIVehicle.GetLocation(v) == pending.depot) pending.before.append(v);
    pending.phase = "building";
    pending.newVehicle = AIVehicle.CloneVehicle(pending.depot, pending.vehicle, true);
    if (!AIVehicle.IsValidVehicle(pending.newVehicle)) { pending.phase = "rollback"; return; }
    pending.phase = "starting";
  }
  if (pending.phase == "starting") {
    if (!AIVehicle.IsValidVehicle(pending.newVehicle)) { pending.phase = "rollback"; return; }
    if (AIVehicle.IsStoppedInDepot(pending.newVehicle) && !AIVehicle.StartStopVehicle(pending.newVehicle)) {
      pending.phase = "rollback"; return;
    }
    if (!OpexWaterContains(line.vehicles, pending.newVehicle)) line.vehicles.append(pending.newVehicle);
    line.trains = line.vehicles.len();
    line.vehCount <- line.trains;
    owner._saveProjection = null;
    owner._saveProjectionMonth = -1;
    if (DECISION_LOG) OpexV233LLog(OpexV233LIs(line) ? "GOOD_GROW" : "INPUT_GROW",
        "line=" + line.lineId + " trains=" + line.trains + " vehicle=" + pending.newVehicle);
    V233L_STATE.pending = null;
  }
}

/* Un ancien save n'a pas de sites. Une entree invalide est abandonnee sans
 * perdre les observations/transactions ; aucun objet API ni plan natif sauve. */
function OpexV233LLoadSites(data)
{
  local restored = {};
  if (typeof data != "table" || data.len() > V233L_SITE_CACHE_MAX) return restored;
  foreach (key, scan in data) {
    if (typeof key != "string" || typeof scan != "table") continue;
    if (("funnel" in scan) && scan.funnel) {
      if (!OpexV233LLoadFunnel(scan)) continue;
      scan.worked = -1;
      restored[key] <- scan;
      continue;
    }
    local valid = true;
    foreach (field in ["ring", "pos", "geometry", "date", "used", "total", "slices", "worked",
        "center", "length", "cargo", "coverage", "station", "railType", "src", "dst", "dstTown"])
      if (!(field in scan) || typeof scan[field] != "integer") valid = false;
    foreach (field in ["done", "limited", "producing"])
      if (!(field in scan) || typeof scan[field] != "bool") valid = false;
    if (!valid) continue;
    if (scan.ring < 0 || scan.ring > 256 || scan.pos < 0
        || scan.pos >= (scan.ring == 0 ? 1 : 8 * scan.ring)
        || scan.geometry < 0 || scan.geometry > 7 || scan.length < 1 || scan.length > 64
        || scan.total < 0 || scan.slices < 0 || scan.coverage < 0 || scan.coverage > 64
        || scan.center < 0 || scan.src < 0 || scan.dst < 0 || scan.cargo < 0
        || scan.station < -1 || scan.railType < 0 || (scan.limited && !scan.done)) continue;
    if (!("stats" in scan) || typeof scan.stats != "table"
        || !("hints" in scan) || typeof scan.hints != "array" || scan.hints.len() > 4) continue;
    foreach (field, value in OpexV233LSiteStats())
      if (!(field in scan.stats) || typeof scan.stats[field] != "integer" || scan.stats[field] < 0) valid = false;
    foreach (hint in scan.hints) {
      if (typeof hint != "table") { valid = false; break; }
      foreach (field in ["anchor", "axis", "sign", "side"])
        if (!(field in hint) || typeof hint[field] != "integer") valid = false;
      if (!valid) break;
      if (hint.anchor < 0 || hint.axis < 0 || hint.axis > 1
          || abs(hint.sign) != 1 || abs(hint.side) != 1) valid = false;
    }
    if (!valid) continue;
    scan.worked = -1; // horloge VM nouvelle ; curseurs et cumul conserves.
    restored[key] <- scan;
  }
  return restored;
}

function OpexV233LLoad(data)
{
  V233L_SITE_CACHE.clear();
  V233L_JOIN_CURSOR.clear();
  local state = OpexV233LNewState();
  if (data == null || typeof data != "table") return state;
  if (!("month" in data) || typeof data.month != "integer"
      || !("cursor" in data) || typeof data.cursor != "integer" || data.cursor < 0
      || !("rows" in data) || typeof data.rows != "table" || data.rows.len() > V233L_MAX_FACTORIES
      || !("growth" in data) || typeof data.growth != "table" || data.growth.len() > 128
      || !("pending" in data)) return state;
  foreach (id, row in data.rows) {
    if (typeof id != "integer" || typeof row != "table") return state;
    foreach (key in ["month", "tile", "inputLine", "station", "townCursor", "exportLine", "exportMonth"])
      if (!(key in row) || typeof row[key] != "integer") return state;
    foreach (key in ["production", "residual"]) {
      if (!(key in row) || typeof row[key] != "array" || row[key].len() > V233L_WINDOW) return state;
      foreach (value in row[key]) if (typeof value != "integer" || value < 0) return state;
    }
    if (row.production.len() != row.residual.len() || row.townCursor < 0) return state;
    if ("months" in row) {
      if (typeof row.months != "array" || row.months.len() != row.production.len()) return state;
      local previous = -1;
      foreach (month in row.months) {
        if (typeof month != "integer" || month < 0 || month <= previous || month > row.month
            || month < row.month - V233L_WINDOW) return state;
        previous = month;
      }
      if (row.months.len() > 0 && previous != row.month) return state;
    } else if (row.production.len() > 0 && row.month < row.production.len() - 1) return state;
  }
  foreach (id, row in data.growth) {
    if (typeof id != "integer" || typeof row != "table") return state;
    foreach (key in ["month", "nextMonth"])
      if (!(key in row) || typeof row[key] != "integer") return state;
    if (!("waiting" in row) || typeof row.waiting != "array" || row.waiting.len() > 3) return state;
    foreach (value in row.waiting) if (typeof value != "integer" || value < 0) return state;
  }
  if (("pending" in data) && data.pending != null) {
    local pending = data.pending;
    if (typeof pending != "table") return state;
    foreach (key in ["lineId", "vehicle", "newVehicle", "depot"])
      if (!(key in pending) || typeof pending[key] != "integer") return state;
    if (!("phase" in pending) || typeof pending.phase != "string"
        || !("before" in pending) || (pending.before != null && typeof pending.before != "array")) return state;
    if (pending.before != null) foreach (v in pending.before) if (typeof v != "integer") return state;
    if (pending.phase != "prepare" && pending.phase != "building"
        && pending.phase != "starting" && pending.phase != "rollback") return state;
    if (pending.phase != "prepare" && pending.before == null) return state;
  }
  /* Ancien schema : ses tableaux etaient strictement consecutifs et dates
   * par row.month. Restituer ces dates connues, sans inventer de production.
   * Migrer seulement apres validation de TOUT l'etat, sans API monde. */
  foreach (id, row in data.rows) {
    if ("months" in row) continue;
    row.months <- [];
    for (local i = 0; i < row.production.len(); i++)
      row.months.append(row.month - row.production.len() + 1 + i);
  }
  V233L_SITE_CACHE = ("sites" in data) ? OpexV233LLoadSites(data.sites) : {};
  data.sites <- V233L_SITE_CACHE;
  return data;
}

function OpexV233LReconcile(owner)
{
  if (V233L_STATE == null || V233L_STATE.pending == null) return;
  local pending = V233L_STATE.pending;
  if (pending.phase == "building") pending.phase = "rollback";
  /* starting est repris par identite : un train deja parti n'est pas recrée. */
}
