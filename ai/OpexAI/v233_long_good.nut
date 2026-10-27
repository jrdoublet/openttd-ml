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
  /* Ne pas publier une paire hors de la fenetre tarifaire apres deplacement.
   * Le premier A compatible reste celui de la voie 1 : un couloir de voie 2
   * ferme ne deplace pas cette sortie. L'autre bout est un quai parallele. */
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
  /* Les geometries B alternatives peuvent se recouvrir (le quai primaire
   * de l'une est le secondaire de l'autre). Reserver une paire coherente,
   * avant A*, plutot que soustraire toutes les sorties de l'union reservee. */
  if (ok && phase == "build") {
    local selectedB = validB[0];
    foreach (q in validB) {
      if (OpexV233LParallelSide(validA[0], q, validA[0].parallel, q.parallel) != 0) {
        selectedB = q;
        break;
      }
    }
    validB = [selectedB];
  }
  return { plansA = ok ? validA : null, plansB = ok ? validB : null, length = length, slopeRelaxed = 0,
    reason = reason, pending = pending,
    statsA = scanA.stats, statsB = scanB.stats };
}

/* Bout marque pour la voie 2 seule. Le filtre historique ne reconnait qu'un
 * seul sens de quai traversant ; a contexte nul il reste inchange. */
function OpexV233LSameEnd(plan, original)
{
  if (("v233OtherEnd" in plan) && plan.v233OtherEnd == 1) return true;
  return OpexSameStationEnd(plan, original);
}

/* La voie 1 ne garde un couloir que s'il ne bouche pas son propre depart.
 * front dans le depart : rien de cet axe. after seul : on lache after. */
function OpexV233LKeepLaunch(front, after, departure)
{
  if (front == null || front in departure) return null;
  local kept = [front];
  if (after != null && !(after in departure)) kept.append(after);
  return kept;
}

/* Lead, sortie, deux pas en avant, et les deux lateraux du lead primaire. */
function OpexV233LMarkDeparture(plan, departure)
{
  if (!(plan.lead in departure)) departure[plan.lead] <- true;
  if (!(plan.station_exit in departure)) departure[plan.station_exit] <- true;
  local dx = AIMap.GetTileX(plan.lead) - AIMap.GetTileX(plan.station_exit);
  local dy = AIMap.GetTileY(plan.lead) - AIMap.GetTileY(plan.station_exit);
  if (dx == 0 && dy == 0) return;
  local forward = OpexV190MakeTile(plan.lead, dx, dy);
  local second = OpexV190MakeTile(plan.lead, 2 * dx, 2 * dy);
  local left = OpexV190MakeTile(plan.lead, -dy, dx);
  local right = OpexV190MakeTile(plan.lead, dy, -dx);
  foreach (t in [forward, second, left, right]) {
    if (t != null && !(t in departure)) departure[t] <- true;
  }
}

/* Un essai precedent a pu greffer l'autre bout dans parallels. Le retirer
 * avant la fusion : ses tuiles ne doivent pas entrer dans l'interdit voie 1. */
function OpexV233LDetachOtherEnd(plan)
{
  if (!("parallels" in plan) || plan.parallels == null) return;
  local kept = [];
  foreach (p in plan.parallels) {
    if (("v233OtherEnd" in p) && p.v233OtherEnd == 1) continue;
    kept.append(p);
  }
  plan.parallels = kept;
}

/* Meme ancre, pas, longueur et direction. Seuls la sortie et le lead changent.
 * Le pas reste positif : BuildRailStation exige l'ancre nord ou ouest. */
function OpexV233LOtherParallel(p)
{
  if (p == null) return null;
  local dx = AIMap.GetTileX(p.lead) - AIMap.GetTileX(p.station_exit);
  local dy = AIMap.GetTileY(p.lead) - AIMap.GetTileY(p.station_exit);
  if (dx * dx + dy * dy != 1) return null;
  local low = p.anchor;
  local high = p.anchor + (p.length - 1) * p.step;
  local otherExit = p.station_exit == low ? high : low;
  if (otherExit == p.station_exit) return null;
  local otherLead = OpexV190MakeTile(otherExit, -dx, -dy);
  if (otherLead == null || otherLead == p.lead || otherLead == p.station_exit || otherLead == otherExit) return null;
  return { anchor = p.anchor, step = p.step, length = p.length, direction = p.direction,
    station_exit = otherExit, lead = otherLead, v233OtherEnd = 1 };
}

/* Lenient = rail sur lead et front. Strict = rail aussi sur after, via beyond.
 * Les trois BuildRail restent dans le meme AITestMode. beyond n'est jamais
 * une tuile reservee : il ne sert qu'a prouver after. */
function OpexV233LCorridor(p, ux, uy, primary, platforms)
{
  if (ux == 0 && uy == 0) return null;
  local front = OpexV190MakeTile(p.lead, ux, uy);
  local after = OpexV190MakeTile(p.lead, 2 * ux, 2 * uy);
  if (front == null || after == null || front in primary || after in primary
      || front in platforms || after in platforms) return null;
  local beyond = OpexV190MakeTile(p.lead, 3 * ux, 3 * uy);
  if (beyond == null || beyond in primary || beyond in platforms)
    beyond = OpexV190MakeTile(after, -uy, ux);
  if (beyond == null || beyond in primary || beyond in platforms)
    beyond = OpexV190MakeTile(after, uy, -ux);
  if (beyond == front || beyond == after) beyond = null;
  local lenient = false;
  local strict = false;
  {
    local testMode = AITestMode();
    lenient = AIRail.BuildRail(p.station_exit, p.lead, front)
        && AIRail.BuildRail(p.lead, front, after);
    if (lenient && beyond != null && !(beyond in primary) && !(beyond in platforms))
      strict = AIRail.BuildRail(front, after, beyond);
  }
  if (!lenient) return null;
  return { front = front, after = after, beyond = beyond, strict = strict, ux = ux, uy = uy };
}

/* <- cree le slot ; = le remplace. Le second essai ne doit pas tuer l'IA. */
function OpexV233LSetPending(plan, extra)
{
  if ("v233PendingOther" in plan) plan.v233PendingOther = extra;
  else plan.v233PendingOther <- extra;
}

/* L'autre bout est un candidat de voie 2. Aucune de ses tuiles n'est ajoutee
 * a l'interdit de la voie 1. La greffe dans parallels attend la voie 2. */
function OpexV233LOfferOtherEnd(candidate, host, parallel, side, primary, platforms)
{
  local other = OpexV233LOtherParallel(parallel);
  if (other == null) return 0;
  OpexV233LSetPending(host, other);
  local dx = AIMap.GetTileX(other.lead) - AIMap.GetTileX(other.station_exit);
  local dy = AIMap.GetTileY(other.lead) - AIMap.GetTileY(other.station_exit);
  local corridor = OpexV233LCorridor(other, dx, dy, primary, platforms);
  if (corridor != null && corridor.strict) {
    if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=reserve reason=LAUNCH_OTHER side=" + side + " lead=" + other.lead
        + " front=" + corridor.front + " after=" + corridor.after
        + " ux=" + corridor.ux + " uy=" + corridor.uy);
    return 2;
  }
  return 1;
}

function OpexV233LInstallOtherEnd(plan)
{
  if (!("v233PendingOther" in plan) || plan.v233PendingOther == null) return;
  local extra = plan.v233PendingOther;
  if (!("parallels" in plan)) {
    plan.parallels <- [extra];
    return;
  }
  if (plan.parallels == null) {
    plan.parallels = [extra];
    return;
  }
  local present = false;
  foreach (p in plan.parallels) {
    if (p.lead == extra.lead && p.station_exit == extra.station_exit) present = true;
  }
  if (!present) plan.parallels.append(extra);
}

/* Une seule paire en construction : aucun quai/lead secondaire ne doit etre
 * consomme par la voie primaire. Meme reservation pour A* direct, reprenable
 * et preplanification, y compris la sonde inverse V294f.
 * Le supplement de voie 1 est le premier axe lenient (deux BuildRail), comme
 * avant TRACK4. Un axe strict ferme n'ajoute pas de lateral ni l'autre bout
 * a cet interdit. En conflit avec le depart primaire, on lache after puis
 * l'axe entier, et la voie 2 essaie une autre geometrie. */
function OpexV233LReserveDouble(candidate, plansA, plansB, clearance)
{
  OpexV233LDetachOtherEnd(plansA[0]);
  OpexV233LDetachOtherEnd(plansB[0]);
  local ignored = OpexV190MergeIgnoredTiles(clearance, plansA, plansB);
  /* Un lead libre ne suffit pas : la voie 1 peut fermer ses trois sorties.
   * Reserver deux pas droits seulement si leur pose native est possible.
   * Ne jamais interdire une interface primaire ni un quai de l'autre bout. */
  local primary = {}, platforms = {}, seen = {}, departure = {};
  foreach (t in ignored) seen[t] <- true;
  foreach (p in [plansA[0], plansB[0]]) {
    if (!(p.lead in primary)) primary[p.lead] <- true;
    if (!(p.station_exit in primary)) primary[p.station_exit] <- true;
    if (!(p.lead in departure)) departure[p.lead] <- true;
    OpexV233LMarkDeparture(p, departure);
    for (local i = 0; i < p.length; i++) {
      local tile = p.anchor + p.step * i;
      local sideTile = p.parallel.anchor + p.parallel.step * i;
      if (!(tile in primary)) primary[tile] <- true;
      if (!(sideTile in platforms)) platforms[sideTile] <- true;
    }
  }
  if (DECISION_LOG) {
    local pa = plansA[0];
    local pb = plansB[0];
    OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=reserve reason=ENDPOINTS"
        + " exit_a=" + pa.station_exit + " lead_a=" + pa.lead
        + " dx_a=" + (AIMap.GetTileX(pa.lead) - AIMap.GetTileX(pa.station_exit))
        + " dy_a=" + (AIMap.GetTileY(pa.lead) - AIMap.GetTileY(pa.station_exit))
        + " exit_b=" + pb.station_exit + " lead_b=" + pb.lead
        + " dx_b=" + (AIMap.GetTileX(pb.lead) - AIMap.GetTileX(pb.station_exit))
        + " dy_b=" + (AIMap.GetTileY(pb.lead) - AIMap.GetTileY(pb.station_exit)));
  }
  /* Droit d'abord, puis les deux lateraux. Le retour vers le quai n'est pas
   * une sortie. NOPA a 5 iterations = file vide des le lead : sans ce couloir
   * la voie 1 ferme les trois voisins et l'A* secondaire n'a rien a ouvrir. */
  local labels = ["A", "B"];
  local hosts = [plansA[0], plansB[0]];
  for (local s = 0; s < 2; s++) {
    local host = hosts[s];
    local p = host.parallel;
    local side = labels[s];
    local dx = AIMap.GetTileX(p.lead) - AIMap.GetTileX(p.station_exit);
    local dy = AIMap.GetTileY(p.lead) - AIMap.GetTileY(p.station_exit);
    local chosen = null;
    local strictOpen = false;
    foreach (axis in [[dx, dy], [-dy, dx], [dy, -dx]]) {
      local corridor = OpexV233LCorridor(p, axis[0], axis[1], primary, platforms);
      if (corridor == null) continue;
      if (chosen == null) chosen = corridor;
      else if (corridor.strict && !(corridor.front in departure) && DECISION_LOG) {
        OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=reserve reason=LAUNCH_OPEN side=" + side + " reserved=0 lead=" + p.lead
            + " front=" + corridor.front + " after=" + corridor.after
            + " ux=" + corridor.ux + " uy=" + corridor.uy);
      }
      if (corridor.strict && !(corridor.front in departure)) strictOpen = true;
    }
    OpexV233LSetPending(host, null);
    local reservedTiles = false;
    if (chosen != null) {
      local kept = OpexV233LKeepLaunch(chosen.front, chosen.after, departure);
      if (kept == null) {
        if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=reserve reason=RELEASE side=" + side + " tile=" + chosen.front + " kind=front");
        if (DECISION_LOG && chosen.after != null) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=reserve reason=RELEASE side=" + side + " tile=" + chosen.after + " kind=after");
      } else {
        foreach (t in kept) if (!(t in seen)) { ignored.append(t); seen[t] <- true; }
        if (chosen.after != null && kept.len() < 2) {
          if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
              + " phase=reserve reason=RELEASE side=" + side + " tile=" + chosen.after + " kind=after");
        }
        if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=reserve reason=LAUNCH side=" + side + " strict=" + (chosen.strict ? 1 : 0)
            + " lead=" + p.lead + " front=" + chosen.front + " after=" + chosen.after
            + " ux=" + chosen.ux + " uy=" + chosen.uy);
        reservedTiles = true;
      }
    }
    if (!strictOpen) {
      local tried = OpexV233LOfferOtherEnd(candidate, host, p, side, primary, platforms);
      if (!reservedTiles && DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
          + " phase=reserve reason=LAUNCH_NONE side=" + side + " lead=" + p.lead
          + " tried_other=" + (tried > 0 ? 1 : 0));
      else if (reservedTiles && tried < 2 && DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
          + " phase=reserve reason=OTHER_TRY side=" + side + " lead=" + p.lead
          + " tried_other=" + (tried > 0 ? 1 : 0));
    }
  }
  if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=reserve reason=RESERVED tiles=" + ignored.len()
      + " a=" + plansA[0].anchor + " a2=" + plansA[0].parallel.anchor
      + " lead_a2=" + plansA[0].parallel.lead
      + " b=" + plansB[0].anchor + " b2=" + plansB[0].parallel.anchor
      + " lead_b2=" + plansB[0].parallel.lead);
  return ignored;
}

/* Diagnostic exact du filtre V190, avant toute recherche de voie 2. */
function OpexV233LDoublePlatformLog(candidate, platform, side, forbidden)
{
  foreach (p in platform.parallels) {
    local reason = "OK", tile = -1;
    if (!OpexV233LSameEnd(p, platform)) reason = "WRONG_END";
    else if (p.lead in forbidden) { reason = "PRIMARY_HITS_LEAD"; tile = p.lead; }
    else {
      for (local i = 0; i < p.length; i++) {
        local t = p.anchor + p.step * i;
        if (t in forbidden) { reason = "PRIMARY_HITS_PLATFORM"; tile = t; break; }
      }
    }
    if (reason == "OK" && ("v233OtherEnd" in p) && p.v233OtherEnd == 1) reason = "OTHER_END";
    OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=platform side=" + side + " reason=" + reason + " tile=" + tile
        + " anchor=" + platform.anchor + " parallel=" + p.anchor + " lead=" + p.lead);
  }
}

function OpexV233LPlanDoubleTrack(catalog, candidate, planA, planB, tiles, iterations, deadline, structures)
{
  if ("v233Enclosed" in candidate) candidate.v233Enclosed = null;
  local routeLength = 0;
  for (local i = 1; i < tiles.len(); i++) routeLength += AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
  local supplied = iterations;
  iterations = OpexV233LDoubleBudget(routeLength);
  if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=budget reason=ROUTE_LENGTH length=" + routeLength + " remaining_primary=" + supplied
      + " budget=" + iterations + " local_cap=" + (iterations / 2));
  /* Apres toutes les fusions d'interdit voie 1. L'autre bout n'y est pas. */
  OpexV233LInstallOtherEnd(planA);
  OpexV233LInstallOtherEnd(planB);
  if (DECISION_LOG) {
    local forbidden = {};
    foreach (t in tiles) if (!(t in forbidden)) forbidden[t] <- true;
    foreach (p in [planA, planB]) {
      for (local i = 0; i < p.length; i++) {
        local tile = p.anchor + p.step * i;
        if (!(tile in forbidden)) forbidden[tile] <- true;
      }
    }
    OpexV233LDoublePlatformLog(candidate, planA, "A", forbidden);
    OpexV233LDoublePlatformLog(candidate, planB, "B", forbidden);
  }
  local dual = OpexV190PlanDoubleTrack(catalog, planA, planB, tiles, iterations, deadline, structures, candidate);
  if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=plan reason=" + dual.reason + " step=" + dual.step + " ok=" + (dual.ok ? 1 : 0)
      + " iters=" + dual.iterations + " budget=" + iterations + " skip=" + dual.skip);
  return dual;
}

/* Budget de recherche de voie 2 independant du reliquat de voie 1. Bornes
 * experimentales, pas une qualification economique ; deadline commune inchangee. */
function OpexV233LDoubleBudget(routeLength)
{
  return min(24000, max(8000, routeLength * 64));
}

/* Diagnostic des sorties directionnelles, sans poser ni ouvrir forbidden.
 * NOPA = file vide, contrairement a ABND ; le nombre de voisins libres
 * distingue un lead enferme d'un echec plus loin, sans promettre un chemin. */
function OpexV233LSearchHeadLog(candidate, p, side, forbidden)
{
  if (!DECISION_LOG) return;
  foreach (delta in [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    local next = OpexV190MakeTile(p.lead, delta[0], delta[1]);
    if (next == null || next == p.station_exit) continue;
    local ok = false, error = -1;
    {
      local testMode = AITestMode();
      ok = AIRail.BuildRail(p.station_exit, p.lead, next);
      if (!ok) error = AIError.GetLastError();
    }
    OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=head reason=EXIT side=" + side + " exit=" + p.station_exit + " lead=" + p.lead
        + " next=" + next + " forbidden=" + ((next in forbidden) ? 1 : 0)
        + " lead_forbidden=" + ((p.lead in forbidden) ? 1 : 0)
        + " lead_rail=" + (AITile.HasTransportType(p.lead, AITile.TRANSPORT_RAIL) ? 1 : 0)
        + " next_rail=" + (AITile.HasTransportType(next, AITile.TRANSPORT_RAIL) ? 1 : 0)
        + " native=" + (ok ? 1 : 0) + " error=" + error);
  }
}

/* Meme longueur et selection que OpexBuildTrack : le type le plus rapide de
 * AIBridgeList_Length(manhattan + 1), celui que la pose utilisera. L'erreur
 * 260 du smoke est AIError.ERR_AREA_NOT_CLEAR (pas 261, pas une longueur, une
 * pente ou un type absent : la liste n'etait pas vide). Un autre type de la
 * meme portee est journalise mais pas retenu : le constructeur partage ne
 * consomme pas un type par ouvrage et rejoue Begin(). Capturer l'erreur AVANT
 * tout diagnostic. Aucune demolition. Retour 0 si le type retenu passe. */
function OpexV233LBridgeProbe(candidate, fromTile, toTile, forbidden)
{
  local length = AIMap.DistanceManhattan(fromTile, toTile) + 1;
  local bridges = AIBridgeList_Length(length);
  OpexBridgeSortBySpeed(bridges);
  local bridgeType = bridges.IsEmpty() ? -1 : bridges.Begin();
  local ok = false, error = -1;
  if (bridgeType >= 0) {
    local testMode = AITestMode();
    ok = AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridgeType, fromTile, toTile);
    if (!ok) error = AIError.GetLastError();
  }
  if (DECISION_LOG) {
    OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=parallel reason=" + (ok ? "BRIDGE_OK" : (bridgeType < 0 ? "NO_BRIDGE_TYPE" : "BRIDGE_NATIVE"))
        + " tile=" + fromTile + " to=" + toTile + " length=" + length + " bridge_type=" + bridgeType
        + " rail_type=" + AIRail.GetCurrentRailType() + " error=" + error
        + " area_not_clear=" + (error == AIError.ERR_AREA_NOT_CLEAR ? 1 : 0)
        + " dx=" + (AIMap.GetTileX(toTile) - AIMap.GetTileX(fromTile))
        + " dy=" + (AIMap.GetTileY(toTile) - AIMap.GetTileY(fromTile)));
    foreach (t in [fromTile, toTile]) {
      OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
          + " phase=bridge_head reason=STATE tile=" + t + " forbidden=" + ((t in forbidden) ? 1 : 0)
          + " slope=" + AITile.GetSlope(t) + " lo=" + AITile.GetMinHeight(t) + " hi=" + AITile.GetMaxHeight(t)
          + " owner=" + AITile.GetOwner(t) + " buildable=" + (AITile.IsBuildable(t) ? 1 : 0)
          + " rail=" + (AITile.HasTransportType(t, AITile.TRANSPORT_RAIL) ? 1 : 0)
          + " road=" + (AITile.HasTransportType(t, AITile.TRANSPORT_ROAD) ? 1 : 0)
          + " station=" + (AIRail.IsRailStationTile(t) ? 1 : 0)
          + " bridge=" + (AIBridge.IsBridgeTile(t) ? 1 : 0)
          + " tunnel=" + (AITunnel.IsTunnelTile(t) ? 1 : 0));
    }
    /* Une obstruction peut etre sous le tablier plutot que sur une tete.
     * Etat descriptif borne, jamais assimile a la cause native certaine.
     * Pas d'arithmetique de TileIndex : un pas Y n'est pas +1. */
    local sameAxis = AIMap.GetTileX(fromTile) == AIMap.GetTileX(toTile)
        || AIMap.GetTileY(fromTile) == AIMap.GetTileY(toTile);
    if (!ok && length > 2 && sameAxis) {
      local udx = AIMap.GetTileX(toTile) - AIMap.GetTileX(fromTile);
      local udy = AIMap.GetTileY(toTile) - AIMap.GetTileY(fromTile);
      udx = udx > 0 ? 1 : (udx < 0 ? -1 : 0);
      udy = udy > 0 ? 1 : (udy < 0 ? -1 : 0);
      local reported = 0;
      for (local i = 1; i < length - 1 && reported < 8; i++) {
        local t = OpexV190MakeTile(fromTile, udx * i, udy * i);
        if (t == null || (AITile.IsBuildable(t) && !(t in forbidden))) continue;
        reported++;
        OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=bridge_span reason=STATE tile=" + t + " forbidden=" + ((t in forbidden) ? 1 : 0)
            + " owner=" + AITile.GetOwner(t) + " hi=" + AITile.GetMaxHeight(t)
            + " slope=" + AITile.GetSlope(t)
            + " buildable=" + (AITile.IsBuildable(t) ? 1 : 0)
            + " rail=" + (AITile.HasTransportType(t, AITile.TRANSPORT_RAIL) ? 1 : 0)
            + " bridge=" + (AIBridge.IsBridgeTile(t) ? 1 : 0)
            + " tunnel=" + (AITunnel.IsTunnelTile(t) ? 1 : 0)
            + " road=" + (AIRoad.IsRoadTile(t) ? 1 : 0)
            + " water=" + (AITile.IsWaterTile(t) ? 1 : 0)
            + " station=" + (AIRail.IsRailStationTile(t) ? 1 : 0)
            + " kind=" + OpexV233LOccupantKind(t));
      }
    }
    if (!ok && bridgeType >= 0) {
      for (local alt = bridges.Next(); !bridges.IsEnd(); alt = bridges.Next()) {
        local altOk = false, altError = -1;
        {
          local testMode = AITestMode();
          altOk = AIBridge.BuildBridge(AIVehicle.VT_RAIL, alt, fromTile, toTile);
          if (!altOk) altError = AIError.GetLastError();
        }
        OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=parallel reason=BRIDGE_ALT tile=" + fromTile + " bridge_type=" + alt
            + " ok=" + (altOk ? 1 : 0) + " error=" + altError
            + " area_not_clear=" + (altError == AIError.ERR_AREA_NOT_CLEAR ? 1 : 0));
        if (altOk) break;
      }
    }
  }
  return ok ? 0 : error;
}

/* Premiere portion invalide du parallele. Tous les appels sont des tests.
 * Verifier aussi l'axe des rampes : un saut natif constructible ne prouve
 * pas son raccordement au prefixe et au suffixe. */
function OpexV233LParallelIssue(candidate, trace, forbidden)
{
  local tiles = trace.tiles;
  local seen = {};
  for (local i = 0; i < tiles.len(); i++) {
    if (tiles[i] in seen) return max(1, i - 1);
    seen[tiles[i]] <- true;
    if (i == 0 || i == tiles.len() - 1) continue;
    local prev = tiles[i - 1], cur = tiles[i], next = tiles[i + 1];
    if (cur in forbidden) {
      OpexV233LDoubleTraceLog(candidate, "PRIMARY_COLLISION", cur);
      return i;
    }
    if (i >= 3 && AIMap.DistanceManhattan(prev, cur) == 1
        && AIMap.DistanceManhattan(tiles[i - 2], prev) == 1
        && AIMap.DistanceManhattan(tiles[i - 3], tiles[i - 2]) == 1
        && cur - prev == tiles[i - 3] - tiles[i - 2]) return i - 1;
    if (AIMap.DistanceManhattan(prev, cur) > 1) continue;
    local ok = false, error = -1;
    if (AIMap.DistanceManhattan(cur, next) > 1) {
      local dist = AIMap.DistanceManhattan(cur, next);
      local step = (next - cur) / dist;
      if ((AIMap.GetTileX(cur) != AIMap.GetTileX(next) && AIMap.GetTileY(cur) != AIMap.GetTileY(next))
          || cur - prev != step || i + 2 >= tiles.len() || tiles[i + 2] - next != step) {
        OpexV233LDoubleTraceLog(candidate, "RAMP_AXIS", cur);
        return i;
      }
      local kind = OpexPlannedStructureKind(trace.structures, cur, next);
      if (kind == "tunnel" || (kind == null && AITunnel.GetOtherTunnelEnd(cur) == next)) {
        local testMode = AITestMode();
        ok = AITunnel.GetOtherTunnelEnd(cur) == next && AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur);
        if (!ok) error = AIError.GetLastError();
      } else {
        /* 0 = type le plus rapide accepte. Une erreur native est positive. */
        error = OpexV233LBridgeProbe(candidate, cur, next, forbidden);
        ok = error == 0;
      }
    } else {
      local testMode = AITestMode();
      ok = AIRail.BuildRail(prev, cur, next);
      if (!ok) error = AIError.GetLastError();
    }
    if (!ok) {
      OpexV233LDoubleTraceLog(candidate, "LOCAL_OBSTACLE", cur, error);
      /* Apres GetLastError : 260 = aire occupee, 264 = pente incompatible
       * avec deux axes. rail=0 distingue un objet d'une voie deja posee. */
      if (candidate != null && DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src
          + " dst=" + candidate.dst + " phase=obstacle tile=" + cur + " error=" + error
          + " slope=" + AITile.GetSlope(cur) + " owner=" + AITile.GetOwner(cur)
          + " buildable=" + (AITile.IsBuildable(cur) ? 1 : 0)
          + " rail=" + (AIRail.IsRailTile(cur) ? 1 : 0)
          + " station=" + (AIRail.IsRailStationTile(cur) ? 1 : 0)
          + " road=" + (AIRoad.IsRoadTile(cur) ? 1 : 0)
          + " water=" + (AITile.IsWaterTile(cur) ? 1 : 0));
      return i;
    }
  }
  return -1;
}

/* Une greffe de chemin conserve les deux interfaces directionnelles et
 * rejette tout retour sur la voie 1 ou le reste du parallele. */
function OpexV233LSpliceParallel(tiles, tail, left, right, forbidden)
{
  if (tail.len() < 4 || tail[0] != tiles[left] || tail[1] != tiles[left + 1]
      || tail[tail.len() - 2] != tiles[right - 1] || tail.top() != tiles[right]) return null;
  local joined = [], seen = {};
  for (local i = 0; i < left; i++) joined.append(tiles[i]);
  foreach (t in tail) joined.append(t);
  for (local i = right + 1; i < tiles.len(); i++) joined.append(tiles[i]);
  foreach (t in joined) {
    if (t in seen || t in forbidden) return null;
    seen[t] <- true;
  }
  return joined;
}

/* Tuiles d'un segment d'axe, offsets inclus. MakeTile evite le retour a la
 * ligne d'une addition de TileIndex. null si le segment sort de la carte. */
function OpexV233LCollectAxis(origin, udx, udy, fromOff, toOff)
{
  local seq = [];
  local dir = toOff >= fromOff ? 1 : -1;
  local guard = 0;
  for (local off = fromOff; guard < 16; off += dir) {
    guard++;
    local t = OpexV190MakeTile(origin, udx * off, udy * off);
    if (t == null) return null;
    seq.append(t);
    if (off == toOff) return seq;
  }
  return null;
}

/* Index du saut a reparer. L'obstacle peut etre la tete (BuildBridge) ou la
 * tuile de rampe juste avant (BuildRail vers une tete non libre). */
function OpexV233LBridgeAt(tiles, issue)
{
  if (issue < 1 || tiles == null) return -1;
  if (issue + 2 < tiles.len() && AIMap.DistanceManhattan(tiles[issue], tiles[issue + 1]) > 1) return issue;
  if (issue + 3 < tiles.len() && AIMap.DistanceManhattan(tiles[issue], tiles[issue + 1]) == 1
      && AIMap.DistanceManhattan(tiles[issue + 1], tiles[issue + 2]) > 1) return issue + 1;
  return -1;
}

/* Glisse le pont parallele le long de son axe, meme longueur d'abord, puis
 * une portee voisine. Le type reste celui de OpexBuildTrack (le plus rapide
 * de la nouvelle longueur). Les tetes qui tombent sur la voie 1 ou hors carte
 * sont refusees. Le raccord est teste en bloc ; rien n'est pose. */
function OpexV233LSlideBridge(candidate, trace, index, forbidden)
{
  local tiles = trace.tiles;
  if (index < 1 || index + 2 >= tiles.len()) return null;
  local prev = tiles[index - 1];
  local cur = tiles[index];
  local next = tiles[index + 1];
  local after = tiles[index + 2];
  local dist = AIMap.DistanceManhattan(cur, next);
  if (dist < 2) return null;
  if (AIMap.GetTileX(cur) != AIMap.GetTileX(next) && AIMap.GetTileY(cur) != AIMap.GetTileY(next)) return null;
  local udx = AIMap.GetTileX(next) - AIMap.GetTileX(cur);
  local udy = AIMap.GetTileY(next) - AIMap.GetTileY(cur);
  udx = udx > 0 ? 1 : (udx < 0 ? -1 : 0);
  udy = udy > 0 ? 1 : (udy < 0 ? -1 : 0);
  if (cur - prev != (next - cur) / dist || after - next != (next - cur) / dist) return null;
  local nudges = [
    [1, 1], [-1, -1], [2, 2], [-2, -2], [3, 3], [-3, -3], [4, 4], [-4, -4],
    [1, 0], [2, 0], [3, 0], [-1, 0], [-2, 0],
    [0, 1], [0, 2], [0, 3], [0, -1], [0, -2],
    [1, 2], [2, 1], [-1, -2], [-2, -1]
  ];
  local tries = 0, lastError = -1;
  foreach (nudge in nudges) {
    local startOff = nudge[0];
    local endOff = dist + nudge[1];
    if (endOff - startOff < 2) continue;
    local approach = OpexV233LCollectAxis(cur, udx, udy, -1, startOff);
    local landing = OpexV233LCollectAxis(cur, udx, udy, endOff, dist + 1);
    if (approach == null || landing == null || approach.len() < 1 || landing.len() < 1) continue;
    local seq = [];
    foreach (t in approach) seq.append(t);
    foreach (t in landing) seq.append(t);
    local seen = {}, clash = false;
    foreach (t in seq) {
      if (t in seen || t in forbidden) { clash = true; break; }
      seen[t] <- true;
    }
    if (clash) continue;
    for (local k = 0; k < index - 1; k++) if (tiles[k] in seen) { clash = true; break; }
    if (clash) continue;
    for (local k = index + 3; k < tiles.len(); k++) if (tiles[k] in seen) { clash = true; break; }
    if (clash) continue;
    /* k part de 0 : un decalage negatif place le saut entre seq[0] et seq[1].
     * Le saut et les rails de raccord sont testes ensemble ; rien n'est pose. */
    local bridgeType = -1, error = -1, built = true, bridged = false;
    {
      local testMode = AITestMode();
      for (local k = 0; k < seq.len() - 1; k++) {
        local far = AIMap.DistanceManhattan(seq[k], seq[k + 1]) > 1;
        if (far) {
          local length = AIMap.DistanceManhattan(seq[k], seq[k + 1]) + 1;
          local bridges = AIBridgeList_Length(length);
          OpexBridgeSortBySpeed(bridges);
          bridgeType = bridges.IsEmpty() ? -1 : bridges.Begin();
          if (bridgeType < 0 || !AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridgeType, seq[k], seq[k + 1])) {
            built = false;
            error = AIError.GetLastError();
            break;
          }
          bridged = true;
        } else if (k > 0 && AIMap.DistanceManhattan(seq[k - 1], seq[k]) == 1) {
          if (!AIRail.BuildRail(seq[k - 1], seq[k], seq[k + 1])) {
            built = false;
            error = AIError.GetLastError();
            break;
          }
        }
      }
    }
    tries++;
    if (!built || !bridged) { lastError = error; continue; }
    local joined = [];
    for (local k = 0; k < index - 1; k++) joined.append(tiles[k]);
    foreach (t in seq) joined.append(t);
    for (local k = index + 3; k < tiles.len(); k++) joined.append(tiles[k]);
    local structures = [];
    local start = approach[approach.len() - 1];
    local endTile = landing[0];
    foreach (s in trace.structures) {
      if (!("from" in s) || !("to" in s)) continue;
      if (s.from == cur && s.to == next) continue;
      local kept = false;
      for (local k = 0; k + 1 < joined.len(); k++) {
        if (s.from == joined[k] && s.to == joined[k + 1]) { kept = true; break; }
      }
      if (kept) structures.append(s);
    }
    structures.append({ from = start, to = endTile, kind = "bridge",
      length = AIMap.DistanceManhattan(start, endTile) });
    if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=bridge reason=SLIDE_CANDIDATE from=" + start + " to=" + endTile
        + " shift=" + startOff + " length=" + (endOff - startOff)
        + " bridge_type=" + bridgeType + " tries=" + tries);
    return { tiles = joined, structures = structures };
  }
  if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=bridge reason=SLIDE_NONE tile=" + cur + " tries=" + tries + " error=" + lastError
      + " area_not_clear=" + (lastError == AIError.ERR_AREA_NOT_CLEAR ? 1 : 0));
  return null;
}

/* Milieu de pont : la tuile reste MP_CLEAR et IsBuildable, IsBridgeTile ne
 * voit que les rampes. BuildRail repond alors MUST_DEMOLISH_BRIDGE_FIRST,
 * classe 260, alors que l'occupant semble libre. Pas d'API IsBridgeAbove :
 * une rampe a moins de 32 pas sur le meme axe, et l'autre tete de l'autre
 * cote de la tuile, prouve le tablier. */
function OpexV233LBridgeAbove(tile)
{
  if (!AIMap.IsValidTile(tile) || AIBridge.IsBridgeTile(tile)) return false;
  local tx = AIMap.GetTileX(tile);
  local ty = AIMap.GetTileY(tile);
  local axes = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  foreach (axis in axes) {
    local head = null;
    local ux = axis[0];
    local uy = axis[1];
    for (local step = 1; step <= 32; step++) {
      local t = OpexV190MakeTile(tile, ux * step, uy * step);
      if (t == null) break;
      if (AIBridge.IsBridgeTile(t)) { head = t; break; }
    }
    if (head == null) continue;
    local other = AIBridge.GetOtherBridgeEnd(head);
    if (!AIMap.IsValidTile(other) || other == head) continue;
    local hx = AIMap.GetTileX(head);
    local hy = AIMap.GetTileY(head);
    local ox = AIMap.GetTileX(other);
    local oy = AIMap.GetTileY(other);
    if (hy == ty && oy == ty && (hx - tx) * (ox - tx) < 0) return true;
    if (hx == tx && ox == tx && (hy - ty) * (oy - ty) < 0) return true;
  }
  return false;
}

/* Voie au sol, tablier, rampe, route, eau, maison ou pente. Une rampe est
 * un pont : elle est comptee avant le rail au sol. `house` couvre aussi une
 * industrie ou un objet non constructible qui n'est ni eau ni transport.
 * Arbre, rocher, champ et friche sont un sol libre que la pose peut nettoyer.
 * `above` est le sol sous un tablier : il a l'air libre et refuse 260. */
function OpexV233LOccupantKind(tile)
{
  if (tile == null || !AIMap.IsValidTile(tile)) return "off";
  if (AIRail.IsRailStationTile(tile)) return "station";
  if (AIBridge.IsBridgeTile(tile)) return "bridge";
  if (AITunnel.IsTunnelTile(tile)) return "tunnel";
  if (AIRail.IsRailTile(tile) || AITile.HasTransportType(tile, AITile.TRANSPORT_RAIL)) return "rail";
  if (AIRoad.IsRoadTile(tile)) return "road";
  if (AITile.IsWaterTile(tile) || AITile.IsCoastTile(tile)) return "water";
  if (!AITile.IsBuildable(tile)) return "house";
  if (AITile.GetSlope(tile) != AITile.SLOPE_FLAT) return "slope";
  if (AITile.HasTreeOnTile(tile)) return "tree";
  if (AITile.IsRockTile(tile)) return "rock";
  if (AITile.IsFarmTile(tile)) return "field";
  if (AITile.IsRoughTile(tile)) return "rough";
  if (OpexV233LBridgeAbove(tile)) return "above";
  return "clear";
}

/* Le glissement axial a echoue : le tablier ou la tete lointaine est occupe,
 * souvent par la voie 1 dont le milieu de pont n'est pas dans l'interdit.
 * Decale le pont sur l'autre perpendiculaire, meme portee d'abord, puis une
 * portee plus longue qui depasse l'occupation. Rien n'est pose. */
function OpexV233LAsideBridge(candidate, trace, index, forbidden)
{
  local tiles = trace.tiles;
  if (candidate == null || index < 1 || index + 2 >= tiles.len()) return null;
  local prev = tiles[index - 1];
  local cur = tiles[index];
  local next = tiles[index + 1];
  local dist = AIMap.DistanceManhattan(cur, next);
  if (dist < 2) return null;
  if (AIMap.GetTileX(cur) != AIMap.GetTileX(next) && AIMap.GetTileY(cur) != AIMap.GetTileY(next)) return null;
  local udx = AIMap.GetTileX(next) - AIMap.GetTileX(cur);
  local udy = AIMap.GetTileY(next) - AIMap.GetTileY(cur);
  udx = udx > 0 ? 1 : (udx < 0 ? -1 : 0);
  udy = udy > 0 ? 1 : (udy < 0 ? -1 : 0);
  local step = (next - cur) / dist;
  if (cur - prev != step || tiles[index + 2] - next != step) return null;
  local kind = OpexV233LOccupantKind(next);
  if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=bridge reason=OCCUPANT tile=" + next + " kind=" + kind
      + " rail=" + (AIRail.IsRailTile(next) ? 1 : 0)
      + " bridge=" + (AIBridge.IsBridgeTile(next) ? 1 : 0)
      + " road=" + (AIRoad.IsRoadTile(next) ? 1 : 0)
      + " water=" + (AITile.IsWaterTile(next) ? 1 : 0)
      + " station=" + (AIRail.IsRailStationTile(next) ? 1 : 0)
      + " buildable=" + (AITile.IsBuildable(next) ? 1 : 0)
      + " slope=" + AITile.GetSlope(next) + " owner=" + AITile.GetOwner(next));
  local perps = [[-udy, udx], [udy, -udx]];
  /* Indice de perpendiculaire, amplitude laterale, glissement de la tete
   * lointaine. La tete proche reste en face de cur : un seul coude suffit. */
  local specs = [
    [0, 1, 0], [1, 1, 0],
    [0, 2, 0], [1, 2, 0],
    [0, 1, 2], [1, 1, 2],
    [0, 1, 4], [1, 1, 4],
    [0, 1, 6], [1, 1, 6],
    [0, 1, 8], [1, 1, 8],
    [0, 2, 2], [1, 2, 2],
    [0, 2, 4], [1, 2, 4],
    [0, 1, -2], [1, 1, -2],
    [0, 1, -4], [1, 1, -4]
  ];
  local tries = 0;
  local lastError = -1;
  foreach (spec in specs) {
    local px = perps[spec[0]][0];
    local py = perps[spec[0]][1];
    local lateral = spec[1];
    local endSlide = spec[2];
    local gap = dist + endSlide;
    if (gap < 2 || gap + 1 > 20) continue;
    local newStart = OpexV190MakeTile(cur, px * lateral, py * lateral);
    local newEnd = OpexV190MakeTile(next, px * lateral + udx * endSlide, py * lateral + udy * endSlide);
    if (newStart == null || newEnd == null) continue;
    if (AIMap.DistanceManhattan(newStart, newEnd) != gap) continue;
    if ((newEnd - newStart) / gap != step) continue;
    local axisBefore = OpexV190MakeTile(newStart, -udx, -udy);
    if (axisBefore == null) continue;
    local rejoin = -1;
    local seg = [];
    seg.append(prev);
    if (lateral == 2) {
      local midIn = OpexV190MakeTile(prev, px, py);
      if (midIn == null) continue;
      seg.append(midIn);
    }
    seg.append(axisBefore);
    seg.append(newStart);
    seg.append(newEnd);
    if (endSlide >= 0) {
      local axisAfter = OpexV190MakeTile(newEnd, udx, udy);
      if (axisAfter == null) continue;
      seg.append(axisAfter);
      local off = 0;
      local scanLimit = index + 1 + gap + 4;
      if (scanLimit > tiles.len()) scanLimit = tiles.len();
      for (local j = index + 1; j < scanLimit; j++) {
        local want = OpexV190MakeTile(next, udx * off, udy * off);
        if (want == null || tiles[j] != want) break;
        if (off > endSlide) { rejoin = j; break; }
        off++;
      }
      if (rejoin < 0) continue;
      if (lateral == 2) {
        local midOut = OpexV190MakeTile(tiles[rejoin], px, py);
        if (midOut == null) continue;
        seg.append(midOut);
      }
      seg.append(tiles[rejoin]);
    } else {
      if (index + 2 >= tiles.len() || tiles[index + 2] - next != step) continue;
      rejoin = index + 2;
      local walk = newEnd;
      local walkOk = true;
      for (local s = endSlide; s < 1; s++) {
        walk = OpexV190MakeTile(walk, udx, udy);
        if (walk == null) { walkOk = false; break; }
        seg.append(walk);
      }
      if (!walkOk) continue;
      if (lateral == 2) {
        local midOut = OpexV190MakeTile(tiles[rejoin], px, py);
        if (midOut == null) continue;
        seg.append(midOut);
      }
      seg.append(tiles[rejoin]);
    }
    local joined = [];
    for (local n = 0; n < index - 1; n++) joined.append(tiles[n]);
    foreach (t in seg) joined.append(t);
    for (local n = rejoin + 1; n < tiles.len(); n++) joined.append(tiles[n]);
    local seen = {};
    local clash = false;
    foreach (t in joined) {
      if (t in seen) { clash = true; break; }
      seen[t] <- true;
    }
    if (!clash) {
      foreach (t in seg) {
        if (t == prev || t == tiles[rejoin]) continue;
        if (t in forbidden) { clash = true; break; }
      }
    }
    if (clash || newStart in forbidden || newEnd in forbidden || axisBefore in forbidden) continue;
    local bridgeType = -1;
    local error = -1;
    local built = true;
    local testSeq = [];
    if (index >= 2) testSeq.append(tiles[index - 2]);
    foreach (t in seg) testSeq.append(t);
    if (rejoin + 1 < tiles.len()) testSeq.append(tiles[rejoin + 1]);
    {
      local testMode = AITestMode();
      for (local n = 0; n < testSeq.len() - 1; n++) {
        local far = AIMap.DistanceManhattan(testSeq[n], testSeq[n + 1]) > 1;
        if (far) {
          local length = AIMap.DistanceManhattan(testSeq[n], testSeq[n + 1]) + 1;
          local bridges = AIBridgeList_Length(length);
          OpexBridgeSortBySpeed(bridges);
          bridgeType = bridges.IsEmpty() ? -1 : bridges.Begin();
          if (bridgeType < 0 || !AIBridge.BuildBridge(AIVehicle.VT_RAIL, bridgeType, testSeq[n], testSeq[n + 1])) {
            built = false;
            error = AIError.GetLastError();
            break;
          }
        } else if (n > 0 && AIMap.DistanceManhattan(testSeq[n - 1], testSeq[n]) == 1) {
          if (!AIRail.BuildRail(testSeq[n - 1], testSeq[n], testSeq[n + 1])) {
            built = false;
            error = AIError.GetLastError();
            break;
          }
        }
      }
    }
    tries++;
    if (!built) { lastError = error; continue; }
    if (!OpexV233LParallelGeometry(candidate, joined)) continue;
    local structures = [];
    foreach (s in trace.structures) {
      if (!("from" in s) || !("to" in s)) continue;
      if (s.from == cur && s.to == next) continue;
      local kept = false;
      for (local n = 0; n + 1 < joined.len(); n++) {
        if (s.from == joined[n] && s.to == joined[n + 1]) { kept = true; break; }
      }
      if (kept) structures.append(s);
    }
    structures.append({ from = newStart, to = newEnd, kind = "bridge",
      length = AIMap.DistanceManhattan(newStart, newEnd) });
    if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=bridge reason=ASIDE_OK from=" + newStart + " to=" + newEnd
        + " perp=" + spec[0] + " k=" + lateral + " end_slide=" + endSlide
        + " length=" + (gap + 1) + " bridge_type=" + bridgeType
        + " tries=" + tries + " occupant=" + kind);
    return { tiles = joined, structures = structures };
  }
  if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=bridge reason=ASIDE_NONE tile=" + cur + " tries=" + tries
      + " error=" + lastError + " occupant=" + kind
      + " area_not_clear=" + (lastError == AIError.ERR_AREA_NOT_CLEAR ? 1 : 0));
  return null;
}

/* Bande fermee autour de la fenetre. L'interieur elargi de `margin` reste libre
 * pour le detour. L'epaisseur vaut la portee max du pathfinder : il n'ajoute
 * que la tuile d'atterrissage, donc une ligne d'une tuile se saute. Les tuiles
 * de la fenetre restent hors de la bande. */
function OpexV233LFence(tiles, left, right, margin, ignored)
{
  local minX = 100000, maxX = -1, minY = 100000, maxY = -1, keep = {};
  for (local i = left; i <= right; i++) {
    local x = AIMap.GetTileX(tiles[i]);
    local y = AIMap.GetTileY(tiles[i]);
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
    if (!(tiles[i] in keep)) keep[tiles[i]] <- true;
  }
  local mapX = AIMap.GetMapSizeX() - 1;
  local mapY = AIMap.GetMapSizeY() - 1;
  local inMinX = minX - margin > 0 ? minX - margin : 0;
  local inMinY = minY - margin > 0 ? minY - margin : 0;
  local inMaxX = maxX + margin < mapX ? maxX + margin : mapX;
  local inMaxY = maxY + margin < mapY ? maxY + margin : mapY;
  /* i < max_bridge_length, donc un saut de cette epaisseur tombe encore dedans. */
  local thick = V294_RAIL_BRIDGE_LEN > 1 ? V294_RAIL_BRIDGE_LEN : 6;
  local outMinX = inMinX - thick > 0 ? inMinX - thick : 0;
  local outMinY = inMinY - thick > 0 ? inMinY - thick : 0;
  local outMaxX = inMaxX + thick < mapX ? inMaxX + thick : mapX;
  local outMaxY = inMaxY + thick < mapY ? inMaxY + thick : mapY;
  for (local y = outMinY; y <= outMaxY; y++) {
    local insideY = y >= inMinY && y <= inMaxY;
    for (local x = outMinX; x <= outMaxX; x++) {
      if (insideY && x >= inMinX && x <= inMaxX) continue;
      local t = AIMap.GetTileIndex(x, y);
      if (!(t in keep)) ignored.append(t);
    }
  }
}

/* Reparer avant toute pose : conserver le parallele dans le PLAN evite
 * des rails orphelins et laisse devis/rollback integral au constructeur.
 * D'abord un pont parallele decale, puis trois fenetres (4/8/16 noeuds).
 * Le premier chemin local OK est greffe tout de suite : les rayons suivants
 * ne repartent pas, et l'A* complet ne demarre que si aucune greffe ne tient.
 * Six reparations, moitie du budget total au maximum ; l'autre moitie reste
 * disponible pour le repli complet. */
/* L'autre bout partage l'ancre : ce n'est pas une paire laterale.
 * Distance laterale exactement 1, meme pas, longueur et direction.
 * La tuile retournee est le coin nord-ouest, celui du recheck. */
function OpexV233LStationPair(primary, parallel)
{
  if (primary == null || parallel == null) return -1;
  if (("v233OtherEnd" in parallel) && parallel.v233OtherEnd == 1) return -1;
  if (primary.step != parallel.step || primary.length != parallel.length
      || primary.direction != parallel.direction) return -1;
  local sideways = primary.step == 1 ? AIMap.GetMapSizeX() : 1;
  if (abs(primary.anchor - parallel.anchor) != sideways) return -1;
  return primary.anchor < parallel.anchor ? primary.anchor : parallel.anchor;
}

function OpexV233LPlatformReady(platform, stationId)
{
  if (platform == null || !AIStation.IsValidStation(stationId)) return false;
  for (local i = 0; i < platform.length; i++) {
    local t = platform.anchor + i * platform.step;
    if (!AIRail.IsRailStationTile(t) || AIStation.GetStationID(t) != stationId) return false;
  }
  return true;
}

/* err est capture par l'appelant avant tout autre appel API. */
function OpexV233LPoseFailLog(candidate, step, anchor, err)
{
  if (!DECISION_LOG || candidate == null) return;
  local rail = AIRail.IsRailTile(anchor) ? 1 : 0;
  local station = AIRail.IsRailStationTile(anchor) ? 1 : 0;
  local slope = AITile.GetSlope(anchor);
  local owner = AITile.GetOwner(anchor);
  local buildable = AITile.IsBuildable(anchor) ? 1 : 0;
  OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=build step=" + step + " reason=FAIL error=" + err
      + " anchor=" + anchor + " rail=" + rail + " station=" + station
      + " slope=" + slope + " owner=" + owner + " buildable=" + buildable);
}

/* 1 = paire posee, 0 = pas adjacente, -1 = la commande a echoue.
 * v233Pair n'est ecrit qu'apres succes, pour le rollback. */
function OpexV233LPoseAdjacent(candidate, primary, parallel, stepName)
{
  local first = OpexV233LStationPair(primary, parallel);
  if (first < 0) return 0;
  local station = ("stationId" in primary) ? primary.stationId : AIStation.STATION_NEW;
  local ok = AIRail.BuildRailStation(first, primary.direction, 2, primary.length, station);
  if (!ok) {
    local err = AIError.GetLastError();
    OpexV233LPoseFailLog(candidate, stepName, first, err);
    return -1;
  }
  if ("v233Pair" in primary) primary.v233Pair = parallel;
  else primary.v233Pair <- parallel;
  if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=build step=" + stepName + " reason=PAIRED anchor=" + first
      + " length=" + primary.length + " station=" + station);
  return 1;
}

/* Quai deja joint : ne pas le demolir pour rejouer un num=1.
 * Sinon la commande separee, avec l'erreur native immediate. */
function OpexV233LPoseOne(candidate, platform, stationId, stepName)
{
  if (OpexV233LPlatformReady(platform, stationId)) {
    if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=build step=" + stepName + " reason=ALREADY anchor=" + platform.anchor);
    return true;
  }
  for (local i = 0; i < platform.length; i++)
    AITile.DemolishTile(platform.anchor + platform.step * i);
  local ok = AIRail.BuildRailStation(platform.anchor, platform.direction, 1, platform.length, stationId);
  if (!ok) {
    local err = AIError.GetLastError();
    OpexV233LPoseFailLog(candidate, stepName, platform.anchor, err);
  }
  return ok;
}

function OpexV233LRollbackPair(plan)
{
  if (plan == null || !("v233Pair" in plan) || plan.v233Pair == null) return;
  local extra = plan.v233Pair;
  for (local i = 0; i < extra.length; i++) {
    local t = extra.anchor + extra.step * i;
    if (AIRail.IsRailStationTile(t)) AIRail.RemoveRailStationTileRectangle(t, t, false);
    else AITile.DemolishTile(t);
  }
}

function OpexV233LNoteEnclosed(candidate, lead)
{
  if (candidate == null || lead == null) return;
  if (!("v233Enclosed" in candidate) || candidate.v233Enclosed == null) {
    if ("v233Enclosed" in candidate) candidate.v233Enclosed = {};
    else candidate.v233Enclosed <- {};
  }
  if (!(lead in candidate.v233Enclosed)) candidate.v233Enclosed[lead] <- true;
}

/* Marche droite dans l'axe de sortie. Le premier obstacle est nomme
 * (rail, pont, route, eau, maison) avant toute recherche large. */
function OpexV233LWalkCorridor(candidate, p, side, forbidden)
{
  if (!DECISION_LOG || candidate == null || p == null) return;
  local ux = AIMap.GetTileX(p.lead) - AIMap.GetTileX(p.station_exit);
  local uy = AIMap.GetTileY(p.lead) - AIMap.GetTileY(p.station_exit);
  ux = ux > 0 ? 1 : (ux < 0 ? -1 : 0);
  uy = uy > 0 ? 1 : (uy < 0 ? -1 : 0);
  local came = p.station_exit;
  local cur = p.lead;
  local steps = 0;
  local blocked = -1;
  local kind = "open";
  local error = -1;
  for (local n = 0; n < 10; n++) {
    local nxt = OpexV190MakeTile(cur, ux, uy);
    if (nxt == null) { kind = "edge"; break; }
    if (nxt in forbidden) { blocked = nxt; kind = "forbidden"; break; }
    local ok = false;
    {
      local testMode = AITestMode();
      ok = AIRail.BuildRail(came, cur, nxt);
      if (!ok) error = AIError.GetLastError();
    }
    if (!ok) {
      blocked = nxt;
      kind = OpexV233LOccupantKind(nxt);
      break;
    }
    steps++;
    came = cur;
    cur = nxt;
  }
  OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=head reason=CORRIDOR side=" + side + " lead=" + p.lead
      + " ux=" + ux + " uy=" + uy + " steps=" + steps + " blocked=" + blocked
      + " kind=" + kind + " error=" + error);
}

/* Sonde indicative : ni ouvrages, ni etats directionnels complets, et une
 * fenetre bornee. Meme une file vide ne prouve donc pas une poche. Le seuil
 * de progression sert au diagnostic, jamais a interdire l'A* complet. */
function OpexV233LProbeHead(candidate, p, side, goal, forbidden, deadline)
{
  if (!DECISION_LOG || candidate == null || p == null || goal == null) return;
  OpexV233LWalkCorridor(candidate, p, side, forbidden);
  local startDist = AIMap.DistanceManhattan(p.lead, goal);
  local need = startDist < 12 ? startDist : 12;
  if (need < 1) need = 1;
  local best = startDist;
  local seen = {};
  seen[p.lead] <- true;
  local qx = [p.lead];
  local qcame = [p.station_exit];
  local qh = 0;
  local expanded = 0;
  local cap = 64;
  while (qh < qx.len() && expanded < cap) {
    if (AIController.GetTick() >= deadline) return;
    /* Le plus proche du but d'abord : une poche ne doit pas remplir la
     * file avec des tuiles qui s'en eloignent avant d'avoir teste l'axe. */
    local bestI = qh;
    local bestD = AIMap.DistanceManhattan(qx[qh], goal);
    for (local i = qh + 1; i < qx.len(); i++) {
      local queued = AIMap.DistanceManhattan(qx[i], goal);
      if (queued < bestD) { bestD = queued; bestI = i; }
    }
    if (bestI != qh) {
      local swapTile = qx[qh];
      qx[qh] = qx[bestI];
      qx[bestI] = swapTile;
      local swapCame = qcame[qh];
      qcame[qh] = qcame[bestI];
      qcame[bestI] = swapCame;
    }
    local cur = qx[qh];
    local came = qcame[qh];
    qh++;
    expanded++;
    foreach (delta in [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      local nxt = OpexV190MakeTile(cur, delta[0], delta[1]);
      if (nxt == null || nxt == came || nxt in seen || nxt in forbidden) continue;
      if (AIMap.DistanceManhattan(p.lead, nxt) > 16) continue;
      if (AIMap.DistanceManhattan(nxt, goal) > startDist + 3) continue;
      local ok = false;
      {
        local testMode = AITestMode();
        ok = AIRail.BuildRail(came, cur, nxt);
      }
      if (!ok) continue;
      seen[nxt] <- true;
      local dist = AIMap.DistanceManhattan(nxt, goal);
      if (dist < best) best = dist;
      qx.append(nxt);
      qcame.append(cur);
    }
  }
  local progress = startDist - best;
  local closed = qh >= qx.len() ? 1 : 0;
  if (progress >= need) {
    if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=head reason=POCKET_OPEN side=" + side + " lead=" + p.lead
        + " start=" + startDist + " best=" + best + " progress=" + progress
        + " expanded=" + expanded + " closed=" + closed);
    return;
  }
  if (progress < need && (closed == 1 || expanded >= cap)) {
    if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=head reason=POCKET_UNKNOWN side=" + side + " lead=" + p.lead
        + " start=" + startDist + " best=" + best + " progress=" + progress
        + " need=" + need + " expanded=" + expanded + " closed=" + closed);
  }
}

function OpexV233LProbeHeads(candidate, plansA, plansB, forbidden, deadline)
{
  if (!DECISION_LOG || candidate == null) return;
  local goalA = (plansB != null && plansB.len() > 0) ? plansB[0].lead : null;
  local goalB = (plansA != null && plansA.len() > 0) ? plansA[0].lead : null;
  if (plansA != null) {
    foreach (p in plansA) OpexV233LProbeHead(candidate, p, "A", goalA, forbidden, deadline);
  }
  if (plansB != null) {
    foreach (p in plansB) OpexV233LProbeHead(candidate, p, "B", goalB, forbidden, deadline);
  }
}

/* Un NOPA local peut declasser une tete, jamais supprimer le dernier choix.
 * Si toutes sont suspectes, l'A* doit les essayer toutes. */
function OpexV233LWithoutEnclosed(plans, candidate)
{
  if (plans == null || candidate == null || !("v233Enclosed" in candidate)
      || candidate.v233Enclosed == null) return plans;
  local alternatives = 0;
  foreach (p in plans)
    if (!("lead" in p) || !(p.lead in candidate.v233Enclosed)) alternatives++;
  if (alternatives == 0 || plans.len() <= 1) {
    if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
        + " phase=search reason=KEEP_UNCERTAIN heads=" + plans.len());
    return plans;
  }
  local kept = [];
  foreach (p in plans) {
    if (("lead" in p) && (p.lead in candidate.v233Enclosed)) {
      if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
          + " phase=search reason=DROP_ENCLOSED lead=" + p.lead);
      continue;
    }
    kept.append(p);
  }
  return kept;
}

function OpexV233LRepairParallel(candidate, trace, forbidden, planA, planB, budget, deadline)
{
  local result = { trace = null, iterations = 0, enclosedLead = null };
  local blocked = {};
  foreach (t, unused in forbidden) blocked[t] <- true;
  foreach (p in [planA, planB]) {
    for (local i = 0; i < p.length; i++) {
      local t = p.anchor + p.step * i;
      if (t != p.station_exit && !(t in blocked)) blocked[t] <- true;
    }
  }
  for (local repairs = 0; repairs <= 6; repairs++) {
    if (AIController.GetTick() >= deadline) return result;
    local issue = OpexV233LParallelIssue(candidate, trace, blocked);
    if (issue < 0) { result.trace = trace; return result; }
    local bridgeAt = OpexV233LBridgeAt(trace.tiles, issue);
    if (bridgeAt >= 0) {
      local slid = OpexV233LSlideBridge(candidate, trace, bridgeAt, blocked);
      /* L'axe est occupe (voie 1, rampe, eau). L'autre cote et une portee
       * plus longue sont testes avant tout A*, meme local. */
      if (slid == null) slid = OpexV233LAsideBridge(candidate, trace, bridgeAt, blocked);
      if (slid != null) {
        local nextIssue = OpexV233LParallelIssue(candidate, slid, blocked);
        /* L'index change avec la longueur du detour : comparer la tuile.
         * Un pont enfin libre doit sortir tout de suite : la boucle se termine
         * apres le dernier essai et result.trace resterait nul. */
        local oldHead = trace.tiles[bridgeAt];
        if (nextIssue < 0 || slid.tiles[nextIssue] != oldHead) {
          trace = slid;
          if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
              + " phase=bridge reason=SLIDE_KEEP tiles=" + trace.tiles.len() + " repairs=" + (repairs + 1));
          if (nextIssue < 0) {
            result.trace = trace;
            return result;
          }
          continue;
        }
      }
    }
    if (repairs == 6 || result.iterations >= budget) return result;
    local fixed = false;
    /* Un pont de longueur L est un seul saut du trace. Le rayon 4 ne voit
     * pas le contour : la fenetre et le budget suivent L, pas le nombre de
     * noeuds. 1000 iterations ne contournent pas un ouvrage de 8. */
    local span = 1;
    if (bridgeAt >= 0) span = AIMap.DistanceManhattan(trace.tiles[bridgeAt], trace.tiles[bridgeAt + 1]) + 1;
    local seenReach = -1;
    foreach (radius in [4, 8, 16]) {
      local reach = radius;
      if (span > reach) reach = span;
      if (reach == seenReach) continue;
      seenReach = reach;
      local tiles = trace.tiles;
      local left = max(0, issue - reach), right = min(tiles.len() - 1, issue + reach + 1);
      /* Deux interfaces disjointes, jamais un acces hors du trace. */
      if (left + 1 >= right) continue;
      /* Interfaces ordinaires : ne jamais couper au milieu d'un ouvrage. */
      if (AIMap.DistanceManhattan(tiles[left], tiles[left + 1]) != 1
          || AIMap.DistanceManhattan(tiles[right - 1], tiles[right]) != 1) continue;
      local ignored = [];
      foreach (t, unused in blocked) ignored.append(t);
      for (local i = 0; i < tiles.len(); i++)
        if (i < left || i > right) ignored.append(tiles[i]);
      /* Marge libre 20. L'epaisseur du cadre est V294_RAIL_BRIDGE_LEN. */
      OpexV233LFence(tiles, left, right, 20, ignored);
      local cap = min(budget - result.iterations, min(8000, max(1000, span * span * 48)));
      if (cap <= 0 || AIController.GetTick() >= deadline) return result;
      /* Grand-parent reel : sans lui le premier pas du pathfinder n'a pas
       * d'interdit de coude, et la greffe est refusee en silence. */
      local approach = null;
      if (left > 0 && AIMap.DistanceManhattan(tiles[left - 1], tiles[left]) == 1)
        approach = tiles[left - 1];
      else if (left == 0 && AIMap.DistanceManhattan(tiles[left], tiles[left + 1]) == 1) {
        local behind = OpexV190MakeTile(tiles[left],
            AIMap.GetTileX(tiles[left]) - AIMap.GetTileX(tiles[left + 1]),
            AIMap.GetTileY(tiles[left]) - AIMap.GetTileY(tiles[left + 1]));
        if (behind != null && AIMap.DistanceManhattan(behind, tiles[left]) == 1) approach = behind;
      }
      local a = { station_exit = tiles[left], lead = tiles[left + 1], approach = approach };
      local b = { station_exit = tiles[right], lead = tiles[right - 1] };
      local search = OpexSearchPath([a], [b], cap, deadline, ignored);
      result.iterations += search.iterations;
      if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
          + " phase=local reason=" + search.stop + " issue=" + tiles[issue] + " left=" + left + " right=" + right
          + " radius=" + radius + " reach=" + reach + " span=" + span
          + " iters=" + search.iterations + " budget=" + cap + " spent=" + result.iterations);
      /* Fenetre collee a la tete et file vide en 5 iterations : la sortie
       * est fermee. Ne pas elargir le rayon ni la redonner a l'A* complet. */
      if (radius == 4 && left == 0 && (search.path == null || search.path == false)
          && search.stop == "NOPA" && search.iterations <= 5) {
        result.enclosedLead = planA.lead;
        OpexV233LNoteEnclosed(candidate, planA.lead);
        return result;
      }
      if (search.path == null || search.path == false) continue;
      local tail = OpexResolveSearchTiles(search);
      if (approach != null && tail.len() > 0 && tail[0] == approach) {
        local trimmed = [];
        for (local k = 1; k < tail.len(); k++) trimmed.append(tail[k]);
        tail = trimmed;
      }
      /* Une tuile du trace deja planifie n'est pas une collision nouvelle.
       * L'obstacle suivant reste au tour d'apres : sinon un recouvrement dans
       * le suffixe jette le detour et relance les rayons 8 et 16. */
      local ban = {};
      foreach (t, banFlag in blocked) ban[t] <- true;
      foreach (t in tiles) if (t in ban) delete ban[t];
      local joined = OpexV233LSpliceParallel(tiles, tail, left, right, ban);
      if (joined == null) {
        if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=local reason=REJECT_SPLICE issue=" + tiles[issue] + " left=" + left
            + " right=" + right + " radius=" + radius + " tail=" + tail.len());
        break;
      }
      if (!OpexV233LParallelGeometry(candidate, joined)) break;
      local dedicated = OpexJoinPathIsDedicated(joined);
      if (!OpexJoinPathIsDedicated(tail)) {
        if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=local reason=REJECT_DEDICATED radius=" + radius);
        break;
      }
      /* Garder seulement les ouvrages encore presents apres remplacement.
       * Les sauts A* sans metadata restent reconnus par le constructeur. */
      local structures = [];
      foreach (s in trace.structures) {
        for (local i = 0; i + 1 < joined.len(); i++)
          if (s.from == joined[i] && s.to == joined[i + 1]) { structures.append(s); break; }
      }
      foreach (s in OpexResolveSearchStructures(search)) structures.append(s);
      local patched = { tiles = joined, structures = structures };
      /* Le detour doit au moins eliminer l'obstacle courant. Le prochain
       * tour validera tous les autres obstacles et les raccords complets. */
      local nextIssue = OpexV233LParallelIssue(candidate, patched, blocked);
      if (nextIssue >= 0 && nextIssue <= left + tail.len() - 2) {
        if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
            + " phase=local reason=REJECT_ISSUE tile=" + patched.tiles[nextIssue]
            + " index=" + nextIssue + " radius=" + radius);
        break;
      }
      trace = patched;
      fixed = true;
      if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
          + " phase=adopt reason=LOCAL tiles=" + joined.len() + " radius=" + radius
          + " left=" + left + " right=" + right + " repairs=" + (repairs + 1)
          + " full_dedicated=" + (dedicated ? 1 : 0));
      if (DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
          + " phase=local reason=SPLICED tiles=" + joined.len() + " repairs=" + (repairs + 1));
      break;
    }
    if (!fixed) return result;
  }
  local leftover = OpexV233LParallelIssue(candidate, trace, blocked);
  if (leftover < 0) result.trace = trace;
  return result;
}

/* Erreur de pose locale : 260 (aire occupee), 264 (pente), ou un occupant
 * qui n'est ni vide ni hors carte. L'argent ne se contourne pas. */
function OpexV233LPoseLocal(error, tile)
{
  if (error == AIError.ERR_NOT_ENOUGH_CASH) return false;
  if (error == AIError.ERR_AREA_NOT_CLEAR || error == AIError.ERR_LAND_SLOPED_WRONG) return true;
  local kind = OpexV233LOccupantKind(tile);
  if (kind != "clear" && kind != "off") return true;
  return error > 0;
}

/* Sol que la pose peut encore nettoyer. Le tablier (`above`) n'en fait pas
 * partie : il reste dans la zone ignoree. */
function OpexV233LPoseOpen(kind)
{
  return kind == "clear" || kind == "slope" || kind == "tree"
      || kind == "field" || kind == "rock" || kind == "rough";
}

/* La tuile a l'air libre, mais le triplet BuildRail est refuse. Deja pose
 * et manque d'argent ne sont pas un obstacle a contourner. */
function OpexV233LRailRefused(prev, cur, next)
{
  if (!AIMap.IsValidTile(prev) || !AIMap.IsValidTile(cur) || !AIMap.IsValidTile(next)) return false;
  if (AIMap.DistanceManhattan(prev, cur) != 1 || AIMap.DistanceManhattan(cur, next) != 1) return false;
  local refused = false;
  {
    local testMode = AITestMode();
    if (!AIRail.BuildRail(prev, cur, next)) {
      local err = AIError.GetLastError();
      refused = err != AIError.ERR_ALREADY_BUILT && err != AIError.ERR_NOT_ENOUGH_CASH;
    }
  }
  return refused;
}

/* Dernier index de la zone bloquee. Un saut natif compte ses deux tetes.
 * Un sol libre dont le triplet suivant est quand meme refuse (260 sur le
 * voisin, ou tablier classe a tort) reste dans la zone. Plafond 24 : une
 * portee de pont tient dans la fenetre, le but atterrit apres. */
function OpexV233LPoseSpan(tiles, index)
{
  local last = index;
  local n = tiles.len();
  if (index + 1 < n && AIMap.DistanceManhattan(tiles[index], tiles[index + 1]) > 1)
    last = index + 1;
  local guard = 0;
  while (last + 1 < n - 1 && guard < 24) {
    local nxt = last + 1;
    if (AIMap.DistanceManhattan(tiles[last], tiles[nxt]) > 1) {
      last = nxt;
      guard++;
      continue;
    }
    local kind = OpexV233LOccupantKind(tiles[nxt]);
    if (OpexV233LPoseOpen(kind)) {
      local after = nxt + 1;
      if (after >= n || !OpexV233LRailRefused(tiles[last], tiles[nxt], tiles[after])) break;
    }
    last = nxt;
    guard++;
  }
  return last;
}

/* Interface adjacente avant l'echec, au moins 4 tuiles en arriere quand
 * c'est possible, jamais au milieu d'un ouvrage. -1 si aucune. */
function OpexV233LPoseAnchor(tiles, index)
{
  local left = -1;
  local limit = index - 16;
  if (limit < 0) limit = 0;
  for (local anchor = index - 2; anchor >= limit; anchor--) {
    if (anchor + 2 >= tiles.len()) continue;
    if (AIMap.DistanceManhattan(tiles[anchor], tiles[anchor + 1]) != 1) continue;
    if (anchor > 0 && AIMap.DistanceManhattan(tiles[anchor - 1], tiles[anchor]) > 1) continue;
    if (AIMap.DistanceManhattan(tiles[anchor + 1], tiles[anchor + 2]) > 1) continue;
    left = anchor;
    if (index - left >= 4) break;
  }
  return left;
}

/* Premiere interface adjacente apres la zone, sur le plan restant. */
function OpexV233LPoseFar(tiles, zone)
{
  local n = tiles.len();
  for (local far = zone + 2; far < n; far++) {
    if (AIMap.DistanceManhattan(tiles[far - 1], tiles[far]) != 1) continue;
    if (far >= 2 && AIMap.DistanceManhattan(tiles[far - 2], tiles[far - 1]) > 1) continue;
    return far;
  }
  return -1;
}

/* Retire seulement NOTRE rail deja pose dans la fenetre qu'on va remplacer.
 * Le pathfinder refuse une tuile qui a deja du rail : le lead doit etre libre.
 * La maison ou l'objet qui a fait echouer la pose n'est pas demoli. */
function OpexV233LDropBuilt(tiles, fromIdx, toIdx)
{
  if (fromIdx < 1) fromIdx = 1;
  for (local k = toIdx; k >= fromIdx; k--) {
    local t = tiles[k];
    if (!AIMap.IsValidTile(t)) continue;
    if (!AICompany.IsMine(AITile.GetOwner(t))) continue;
    if (AIRail.IsRailStationTile(t) || AIRail.IsRailDepotTile(t)) continue;
    if (AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t))
      AITile.DemolishTile(t);
  }
}

/* Tuile en echec, voisine precedente et suivante, leur occupant, ancre,
 * but, iterations et budget. Les index hors fenetre restent a -1. */
function OpexV233LPoseSuffix(tiles, index, left, right, zone, iters, budget)
{
  local cur = -1;
  local prev = -1;
  local nxt = -1;
  local prevKind = "off";
  local nextKind = "off";
  local anchorTile = -1;
  local goal = -1;
  local goalIdx = -1;
  if (tiles != null && index >= 0 && index < tiles.len()) cur = tiles[index];
  if (tiles != null && index - 1 >= 0 && index - 1 < tiles.len()) {
    prev = tiles[index - 1];
    prevKind = OpexV233LOccupantKind(prev);
  }
  if (tiles != null && index + 1 >= 0 && index + 1 < tiles.len()) {
    nxt = tiles[index + 1];
    nextKind = OpexV233LOccupantKind(nxt);
  }
  if (tiles != null && left >= 0 && left < tiles.len()) anchorTile = tiles[left];
  if (tiles != null && right - 1 >= 0 && right - 1 < tiles.len()) {
    goalIdx = right - 1;
    goal = tiles[goalIdx];
  }
  return " cur=" + cur
      + " prev=" + prev + " prev_kind=" + prevKind
      + " next=" + nxt + " next_kind=" + nextKind
      + " anchor=" + left + " anchor_tile=" + anchorTile
      + " goal=" + goal + " goal_idx=" + goalIdx
      + " zone=" + zone + " iters=" + iters + " budget=" + budget;
}

function OpexV233LPoseLog(candidate, reason, index, kind, error, tiles, left, right, zone, iters, budget)
{
  if (!DECISION_LOG || candidate == null) return;
  OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=repair reason=" + reason
      + " idx=" + index + " kind=" + kind + " error=" + error
      + OpexV233LPoseSuffix(tiles, index, left, right, zone, iters, budget));
}

/* Voie 1, quais primaires et depot : meme interdit que la greffe du plan. */
function OpexV233LPoseBlocked(ctx)
{
  local blocked = {};
  if (("primary" in ctx) && ctx.primary != null) {
    foreach (t in ctx.primary) blocked[t] <- true;
  }
  if (("planA" in ctx) && ctx.planA != null) {
    local p = ctx.planA;
    for (local i = 0; i < p.length; i++) {
      local t = p.anchor + p.step * i;
      if (t != p.station_exit && !(t in blocked)) blocked[t] <- true;
    }
  }
  if (("planB" in ctx) && ctx.planB != null) {
    local p = ctx.planB;
    for (local i = 0; i < p.length; i++) {
      local t = p.anchor + p.step * i;
      if (t != p.station_exit && !(t in blocked)) blocked[t] <- true;
    }
  }
  if (("depot" in ctx) && ctx.depot != null) {
    blocked[ctx.depot] <- true;
    local front = AIRail.GetRailDepotFrontTile(ctx.depot);
    if (AIMap.IsValidTile(front)) blocked[front] <- true;
  }
  return blocked;
}

/* Une fenetre, le budget local span^2*48, la meme greffe que SPLICED.
 * Rien n'est pose. null si le detour ne se raccorde pas. */
function OpexV233LPoseSearch(candidate, tiles, structures, blocked, left, right, index, zone, cap, deadline)
{
  if (left < 0 || right <= left + 1 || right >= tiles.len()) return null;
  if (AIMap.DistanceManhattan(tiles[left], tiles[left + 1]) != 1) return null;
  if (AIMap.DistanceManhattan(tiles[right - 1], tiles[right]) != 1) return null;
  local ignored = [];
  foreach (t, unused in blocked) ignored.append(t);
  for (local k = 0; k < tiles.len(); k++)
    if (k < left || k > right) ignored.append(tiles[k]);
  for (local z = index; z <= zone && z < tiles.len(); z++) ignored.append(tiles[z]);
  OpexV233LFence(tiles, left, right, 20, ignored);
  local approach = null;
  if (left > 0 && AIMap.DistanceManhattan(tiles[left - 1], tiles[left]) == 1)
    approach = tiles[left - 1];
  else if (left == 0 && AIMap.DistanceManhattan(tiles[left], tiles[left + 1]) == 1) {
    local behind = OpexV190MakeTile(tiles[left],
        AIMap.GetTileX(tiles[left]) - AIMap.GetTileX(tiles[left + 1]),
        AIMap.GetTileY(tiles[left]) - AIMap.GetTileY(tiles[left + 1]));
    if (behind != null && AIMap.DistanceManhattan(behind, tiles[left]) == 1) approach = behind;
  }
  local a = { station_exit = tiles[left], lead = tiles[left + 1], approach = approach };
  local b = { station_exit = tiles[right], lead = tiles[right - 1] };
  local search = OpexSearchPath([a], [b], cap, deadline, ignored);
  if (search.path == null || search.path == false) return { search = search, joined = null };
  local tail = OpexResolveSearchTiles(search);
  if (approach != null && tail.len() > 0 && tail[0] == approach) {
    local trimmed = [];
    for (local k = 1; k < tail.len(); k++) trimmed.append(tail[k]);
    tail = trimmed;
  }
  local ban = {};
  foreach (t, banFlag in blocked) ban[t] <- true;
  foreach (t in tiles) if (t in ban) delete ban[t];
  local joined = OpexV233LSpliceParallel(tiles, tail, left, right, ban);
  if (joined == null) return { search = search, joined = null };
  if (!OpexV233LParallelGeometry(candidate, joined)) return { search = search, joined = null };
  if (!OpexJoinPathIsDedicated(joined) || !OpexJoinPathIsDedicated(tail))
    return { search = search, joined = null };
  local kept = [];
  if (structures != null) {
    foreach (s in structures) {
      for (local i = 0; i + 1 < joined.len(); i++)
        if (s.from == joined[i] && s.to == joined[i + 1]) { kept.append(s); break; }
    }
  }
  foreach (s in OpexResolveSearchStructures(search)) kept.append(s);
  local patched = { tiles = joined, structures = kept };
  /* Le prefixe est deja notre rail : BuildRail y repond ALREADY_BUILT et
   * masquerait l'obstacle. La fenetre seule, ancre en extremite. */
  local window = { tiles = tail, structures = kept };
  local nextIssue = OpexV233LParallelIssue(candidate, window, blocked);
  if (nextIssue >= 0) return { search = search, joined = null };
  return { search = search, joined = patched, tail = tail.len() };
}

/* Echec de pose a l'index i. Jusqu'a 3 greffes par ligne. giveUp : revenir
 * au rollback actuel. tiles : reprendre la pose a restart. null : pas un
 * obstacle local, le constructeur continue comme avant. */
function OpexV233LRepairPose(ctx, tiles, structures, index, failedTile, error)
{
  if (ctx == null || tiles == null || !OpexV233LPoseLocal(error, failedTile)) return null;
  local candidate = ("candidate" in ctx) ? ctx.candidate : null;
  local kindTile = (index >= 0 && index < tiles.len()) ? tiles[index] : failedTile;
  local kind = OpexV233LOccupantKind(kindTile);
  if (!("repairs" in ctx) || ctx.repairs == null) ctx.repairs = 0;
  local zone = OpexV233LPoseSpan(tiles, index);
  local left = OpexV233LPoseAnchor(tiles, index);
  local right = OpexV233LPoseFar(tiles, zone);
  local span = zone - index + 1;
  if (span < 1) span = 1;
  local cap = min(8000, max(1000, span * span * 48));
  if (ctx.repairs >= 3) {
    OpexV233LPoseLog(candidate, "LIMIT", index, kind, error, tiles, left, right, zone, 0, cap);
    return { giveUp = true };
  }
  if (left < 0 || right < 0 || left + 1 >= right || zone >= right) {
    OpexV233LPoseLog(candidate, "NOPA", index, kind, error, tiles, left, right, zone, 0, -1);
    return { giveUp = true };
  }
  local deadline = AIController.GetTick() + cap / 3 + BUILD_TICK_MARGIN;
  /* Liberer le lead et le moignon deja pose, pas l'ancre ni l'obstacle. */
  OpexV233LDropBuilt(tiles, left + 1, index - 1);
  local blocked = OpexV233LPoseBlocked(ctx);
  local found = OpexV233LPoseSearch(candidate, tiles, structures, blocked, left, right, index, zone, cap, deadline);
  if (!("iterations" in ctx) || ctx.iterations == null) ctx.iterations = 0;
  if (found != null && ("search" in found) && found.search != null)
    ctx.iterations = ctx.iterations + found.search.iterations;
  if (found == null || !("joined" in found) || found.joined == null) {
    local iters = 0;
    if (found != null && ("search" in found) && found.search != null)
      iters = found.search.iterations;
    OpexV233LPoseLog(candidate, "NOPA", index, kind, error, tiles, left, right, zone, iters, cap);
    return { giveUp = true };
  }
  ctx.repairs = ctx.repairs + 1;
  if (DECISION_LOG && candidate != null) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=repair reason=OK idx=" + index + " kind=" + kind + " error=" + error
      + OpexV233LPoseSuffix(tiles, index, left, right, zone, found.search.iterations, cap)
      + " left=" + left + " right=" + right + " tiles=" + found.joined.tiles.len()
      + " iters=" + found.search.iterations + " repairs=" + ctx.repairs);
  return { tiles = found.joined.tiles, structures = found.joined.structures, restart = left + 1 };
}

/* Vecteurs signes : une difference de TileIndex n'est PAS un TileIndex.
 * En B le trace arrive, alors que lead - exit pointe vers l'exterieur. */
function OpexV233LParallelSide(planA, planB, pA, pB)
{
  local dxA = AIMap.GetTileX(planA.lead) - AIMap.GetTileX(planA.station_exit);
  local dyA = AIMap.GetTileY(planA.lead) - AIMap.GetTileY(planA.station_exit);
  local oxA = AIMap.GetTileX(pA.station_exit) - AIMap.GetTileX(planA.station_exit);
  local oyA = AIMap.GetTileY(pA.station_exit) - AIMap.GetTileY(planA.station_exit);
  local side = dxA * oyA - dyA * oxA;
  if (side != 1 && side != -1) return 0;
  local dxB = AIMap.GetTileX(planB.lead) - AIMap.GetTileX(planB.station_exit);
  local dyB = AIMap.GetTileY(planB.lead) - AIMap.GetTileY(planB.station_exit);
  local oxB = AIMap.GetTileX(pB.station_exit) - AIMap.GetTileX(planB.station_exit);
  local oyB = AIMap.GetTileY(pB.station_exit) - AIMap.GetTileY(planB.station_exit);
  return oxB == side * dyB && oyB == -side * dxB ? side : 0;
}

function OpexV233LDoubleTraceLog(candidate, reason, tile = -1, error = -1)
{
  if (candidate != null && DECISION_LOG) OpexV233LLog("DOUBLE", "src=" + candidate.src + " dst=" + candidate.dst
      + " phase=parallel reason=" + reason + " tile=" + tile + " error=" + error);
}

/* Meme contrainte de virage que _Neighbours du pathfinder, appliquee au
 * raccourci parallele qui ne passe pas dans A*. Les sauts restent natifs. */
function OpexV233LParallelGeometry(candidate, tiles)
{
  local seen = {};
  for (local i = 0; i < tiles.len(); i++) {
    if (tiles[i] in seen) {
      OpexV233LDoubleTraceLog(candidate, "SELF_INTERSECTION", tiles[i]);
      return false;
    }
    seen[tiles[i]] <- true;
    if (i >= 3 && AIMap.DistanceManhattan(tiles[i], tiles[i - 1]) == 1
        && AIMap.DistanceManhattan(tiles[i - 1], tiles[i - 2]) == 1
        && AIMap.DistanceManhattan(tiles[i - 2], tiles[i - 3]) == 1
        && tiles[i] - tiles[i - 1] == tiles[i - 3] - tiles[i - 2]) {
      OpexV233LDoubleTraceLog(candidate, "FORBID_90", tiles[i - 1]);
      return false;
    }
  }
  return true;
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
    radius = 0, anchors = [], cursor = 0, done = false, limited = false, centerReject = false,
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
  if (V233_SITE_FUNNEL > 0 && V233_FUNNEL_CENTER_TEST > 0) {
    local cached0 = OpexV233LFunnelEnsure(town, 0, length, cargo, coverage);
    local cached1 = OpexV233LFunnelEnsure(town, 1, length, cargo, coverage);
    if ((cached0 != null && ("centerReject" in cached0) && cached0.centerReject)
        || (cached1 != null && ("centerReject" in cached1) && cached1.centerReject)) {
      return { plans = plans, stats = stats, reason = "exhausted", ring = 0,
        ops = OpexOpsMeasureEnd(mark), length = length };
    }
    if (cached0 != null && cached0.done && cached0.anchors.len() == 0
        && cached1 != null && cached1.done && cached1.anchors.len() == 0) {
      return { plans = plans, stats = stats, reason = "exhausted", ring = 0,
        ops = OpexOpsMeasureEnd(mark), length = length };
    }
    if (cached0 != null && cached0.cursor == 0 && cached0.anchors.len() == 0 && !cached0.done) {
      /* Pre-test d'emprise du quai (w x h = length x 2 puis 2 x length) centree sur la ville. */
      local centerAcc = -1;
      local bestW = length;
      local bestH = 2;
      local cx = AIMap.GetTileX(center);
      local cy = AIMap.GetTileY(center);
      local mapX = AIMap.GetMapSizeX();
      local mapY = AIMap.GetMapSizeY();
      for (local axis = 0; axis < 2; axis++) {
        local w = axis == 0 ? length : 2;
        local h = axis == 0 ? 2 : length;
        local x0 = cx - (w / 2);
        local y0 = cy - (h / 2);
        if (x0 < 0) x0 = 0;
        if (y0 < 0) y0 = 0;
        if (x0 > mapX - w) x0 = mapX - w;
        if (y0 > mapY - h) y0 = mapY - h;
        local tile0 = AIMap.GetTileIndex(x0, y0);
        if (AIMap.IsValidTile(tile0)) {
          local acc = AITile.GetCargoAcceptance(tile0, cargo, w, h, coverage);
          if (acc > centerAcc) {
            centerAcc = acc;
            bestW = w;
            bestH = h;
          }
        }
      }
      if (centerAcc < 8) {
        cached0.done = true;
        cached0.limited = false;
        cached0.centerReject = true;
        cached0.date = AIDate.GetCurrentDate();
        if (cached1 != null) {
          cached1.done = true;
          cached1.limited = false;
          cached1.centerReject = true;
          cached1.date = cached0.date;
        }
        if (DECISION_LOG) OpexV233LLog("SITE_FUNNEL", "town=" + town + " reason=CENTER_REJECT center_acc=" + centerAcc + " w=" + bestW + " h=" + bestH);
        return { plans = plans, stats = stats, reason = "exhausted", ring = 0,
          ops = OpexOpsMeasureEnd(mark), length = length };
      }
    }
  }
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
  if (!("centerReject" in scan)) scan.centerReject <- false;
  else if (typeof scan.centerReject != "bool") return false;
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

/* Fenetre plus large que les 6 tuiles historiques. Un couple (3, 10)
 * n'est pas couvert par deux boucles qui partent a 7 : les deux indices
 * vont de 1 a `limit`. Rien n'est pose : chaque essai a son AITestMode. */
function OpexV233LScanSwitch(tilesFrom, tilesTo, atEnd, outbound, limit, usedFrom, usedTo)
{
  if (tilesFrom == null || tilesTo == null) return null;
  local lastFrom = tilesFrom.len() - 1;
  local lastTo = tilesTo.len() - 1;
  for (local dFrom = 1; dFrom <= limit; dFrom++) {
    local iFrom = atEnd ? lastFrom - dFrom : dFrom;
    if (atEnd) {
      if (iFrom <= 1 || iFrom >= lastFrom) continue;
    } else if (iFrom <= 0 || iFrom >= lastFrom - 2) continue;
    if (iFrom == usedFrom) continue;
    for (local dTo = 1; dTo <= limit; dTo++) {
      local iTo = atEnd ? lastTo - dTo : dTo;
      if (atEnd) {
        if (iTo <= 1 || iTo >= lastTo) continue;
      } else if (iTo <= 0 || iTo >= lastTo - 2) continue;
      if (iTo == usedTo) continue;
      local aPrev = tilesFrom[iFrom];
      local a = tilesFrom[iFrom];
      local b = tilesTo[iTo];
      local bNext = tilesTo[iTo];
      if (!atEnd && outbound) {
        aPrev = tilesFrom[iFrom - 1];
        bNext = tilesTo[iTo + 1];
      } else if (!atEnd) {
        aPrev = tilesFrom[iFrom + 1];
        bNext = tilesTo[iTo - 1];
      } else if (outbound) {
        aPrev = tilesFrom[iFrom + 1];
        bNext = tilesTo[iTo - 1];
      } else {
        aPrev = tilesFrom[iFrom - 1];
        bNext = tilesTo[iTo + 1];
      }
      local ok = false;
      {
        local testMode = AITestMode();
        ok = OpexV181TryBuildSwitch(aPrev, a, b, bNext, null, true);
      }
      if (ok) return { fromIdx = iFrom, toIdx = iTo };
    }
  }
  return null;
}

/* Index de signal sur le trace reel. Le raccord brut peut etre hors trace :
 * le signal reste sur la voie, juste avant le bout concerne. */
function OpexV233LClampIndex(tiles, atEnd, tile)
{
  if (tiles == null || tiles.len() < 4) return -1;
  local n = tiles.len();
  local start = atEnd ? n - 12 : 1;
  if (start < 1) start = 1;
  local stop = atEnd ? n - 2 : 12;
  if (stop > n - 2) stop = n - 2;
  if (stop < start) stop = start;
  local best = start;
  local bestDist = 100000;
  if (tile != null && AIMap.IsValidTile(tile)) {
    for (local i = start; i <= stop; i++) {
      local dist = AIMap.DistanceManhattan(tiles[i], tile);
      if (dist < bestDist) { bestDist = dist; best = i; }
    }
  }
  if (best <= 1) best = 2;
  if (best >= n - 1) best = n - 2;
  return best;
}

/* Distance du lead au bout du trace. Le but atteint par la voie 2 est le
 * lead le plus proche, pas forcement la sortie choisie par la voie 1. */
function OpexV233LEndRank(tiles, atEnd, lead)
{
  if (tiles == null || lead == null || !AIMap.IsValidTile(lead)) return 100000;
  local n = tiles.len();
  local start = atEnd ? n - 12 : 0;
  if (start < 0) start = 0;
  local stop = atEnd ? n - 1 : 11;
  if (stop >= n) stop = n - 1;
  local best = 100000;
  for (local i = start; i <= stop; i++) {
    local dist = AIMap.DistanceManhattan(tiles[i], lead);
    if (dist < best) best = dist;
  }
  return best;
}

/* Raccord quai/voie : le cote voie doit etre sur le trace reel et garder
 * son voisin exterieur (qui peut tourner). L'autre cote rejoint directement
 * le quai, y compris son bout inutilise, sans inventer un rail de liaison. */
function OpexV233LRawSwitch(exitFrom, leadFrom, exitTo, leadTo, outbound, tilesFrom, tilesTo, atEnd)
{
  if (exitFrom == null || leadFrom == null || exitTo == null || leadTo == null) return null;
  local route = outbound ? tilesTo : tilesFrom;
  local lead = outbound ? leadTo : leadFrom;
  local routeIdx = atEnd ? route.len() - 2 : 1;
  if (routeIdx <= 0 || routeIdx >= route.len() - 1 || route[routeIdx] != lead) return null;
  local outside = route[routeIdx + (atEnd ? -1 : 1)];
  local aPrev = exitFrom;
  local a = leadFrom;
  local b = leadTo;
  local bNext = outside;
  if (!outbound) {
    aPrev = outside;
    bNext = exitTo;
  }
  if (aPrev == null || a == null || b == null || bNext == null) return null;
  local ok = false;
  {
    local testMode = AITestMode();
    ok = OpexV181TryBuildSwitch(aPrev, a, b, bNext, null, true);
  }
  if (!ok) return null;
  return { raw = 1, aPrev = aPrev, a = a, b = b, bNext = bNext, fromIdx = 2, toIdx = 2 };
}

/* Les deux bouts d'un quai traversant. Le plus proche du trace de la voie 2
 * est essaye d'abord : l'autre bout reserve depuis 27d4df81 peut etre le
 * seul ou les voies se rejoignent. */
function OpexV233LRecoverEnd(line, tiles1, tiles2, atEnd)
{
  local plan1 = atEnd ? (("platformB" in line) ? line.platformB : null)
      : (("platformA" in line) ? line.platformA : null);
  local plan2 = atEnd ? (("platformB2" in line) ? line.platformB2 : null)
      : (("platformA2" in line) ? line.platformA2 : null);
  if (plan1 == null || plan2 == null) return null;
  if (!("lead" in plan1) || !("lead" in plan2)) return null;
  /* Les plans retenus peuvent sortir par des bouts opposes. Aligner la
   * premiere tete sur la seconde AVANT de construire les deux couples. */
  if (plan1.lead - plan1.station_exit != plan2.lead - plan2.station_exit) {
    plan1 = OpexV233LOtherParallel(plan1);
    if (plan1 == null || plan1.lead - plan1.station_exit != plan2.lead - plan2.station_exit) return null;
  }
  local selected = { exit1 = plan1.station_exit, lead1 = plan1.lead,
    exit2 = plan2.station_exit, lead2 = plan2.lead };
  local specs = [];
  local other1 = OpexV233LOtherParallel(plan1);
  local other2 = OpexV233LOtherParallel(plan2);
  local other = null;
  if (other1 != null && other2 != null) {
    other = { exit1 = other1.station_exit, lead1 = other1.lead,
      exit2 = other2.station_exit, lead2 = other2.lead };
  }
  local rankSel = OpexV233LEndRank(tiles2, atEnd, selected.lead2);
  local rankOther = other != null ? OpexV233LEndRank(tiles2, atEnd, other.lead2) : 100000;
  if (other == null || rankSel <= rankOther) {
    specs.append(selected);
    if (other != null) specs.append(other);
  } else {
    specs.append(other);
    specs.append(selected);
  }
  local tilesFrom = atEnd ? tiles1 : tiles2;
  local tilesTo = atEnd ? tiles2 : tiles1;
  local bestOut = null;
  local bestIn = null;
  foreach (spec in specs) {
    local exitFrom = atEnd ? spec.exit1 : spec.exit2;
    local leadFrom = atEnd ? spec.lead1 : spec.lead2;
    local exitTo = atEnd ? spec.exit2 : spec.exit1;
    local leadTo = atEnd ? spec.lead2 : spec.lead1;
    if (bestOut == null) {
      local sw = OpexV233LRawSwitch(exitFrom, leadFrom, exitTo, leadTo, true, tilesFrom, tilesTo, atEnd);
      if (sw != null) {
        sw.fromIdx = OpexV233LClampIndex(tilesFrom, atEnd, leadFrom);
        sw.toIdx = OpexV233LClampIndex(tilesTo, atEnd, leadTo);
        if (sw.fromIdx < 2) sw.fromIdx = 2;
        if (sw.toIdx < 2) sw.toIdx = 2;
        bestOut = sw;
        if (DECISION_LOG) OpexV233LLog("SWITCH", "end=" + (atEnd ? "B" : "A")
            + " dir=out raw=1 lead1=" + leadFrom + " lead2=" + leadTo
            + " fromIdx=" + sw.fromIdx + " toIdx=" + sw.toIdx);
      }
    }
    if (bestIn == null) {
      local swIn = OpexV233LRawSwitch(exitFrom, leadFrom, exitTo, leadTo, false, tilesFrom, tilesTo, atEnd);
      if (swIn != null) {
        local fromIdx = OpexV233LClampIndex(tilesFrom, atEnd, leadFrom);
        local toIdx = OpexV233LClampIndex(tilesTo, atEnd, leadTo);
        if (fromIdx < 2) fromIdx = 2;
        if (toIdx < 2) toIdx = 2;
        if (bestOut != null && fromIdx == bestOut.fromIdx) fromIdx = fromIdx > 2 ? fromIdx - 1 : fromIdx + 1;
        if (bestOut != null && toIdx == bestOut.toIdx) toIdx = toIdx > 2 ? toIdx - 1 : toIdx + 1;
        swIn.fromIdx = fromIdx;
        swIn.toIdx = toIdx;
        bestIn = swIn;
        if (DECISION_LOG) OpexV233LLog("SWITCH", "end=" + (atEnd ? "B" : "A")
            + " dir=in raw=1 lead1=" + leadFrom + " lead2=" + leadTo
            + " fromIdx=" + swIn.fromIdx + " toIdx=" + swIn.toIdx);
      }
    }
  }
  if (bestOut == null && bestIn == null) return null;
  return { outbound = bestOut, inbound = bestIn };
}

/* Apres la fenetre de 6. D'abord 24 tuiles sur les traces, puis le lead
 * parallele du bout effectivement atteint, y compris l'autre extremite. */
function OpexV233LRecoverSwitches(line, tiles1, tiles2, outA, inA, outB, inB)
{
  if (outA == null) outA = OpexV233LScanSwitch(tiles2, tiles1, false, true, 24, -1, -1);
  if (outA != null && inA == null) {
    local skipFrom = ("fromIdx" in outA) ? outA.fromIdx : -1;
    local skipTo = ("toIdx" in outA) ? outA.toIdx : -1;
    inA = OpexV233LScanSwitch(tiles2, tiles1, false, false, 24, skipFrom, skipTo);
  }
  if (outB == null) outB = OpexV233LScanSwitch(tiles1, tiles2, true, true, 24, -1, -1);
  if (outB != null && inB == null) {
    local skipFrom = ("fromIdx" in outB) ? outB.fromIdx : -1;
    local skipTo = ("toIdx" in outB) ? outB.toIdx : -1;
    inB = OpexV233LScanSwitch(tiles1, tiles2, true, false, 24, skipFrom, skipTo);
  }
  if (outA == null || inA == null) {
    local endA = OpexV233LRecoverEnd(line, tiles1, tiles2, false);
    if (endA != null) {
      if (outA == null) outA = endA.outbound;
      if (inA == null) inA = endA.inbound;
    }
  }
  if (outB == null || inB == null) {
    local endB = OpexV233LRecoverEnd(line, tiles1, tiles2, true);
    if (endB != null) {
      if (outB == null) outB = endB.outbound;
      if (inB == null) inB = endB.inbound;
    }
  }
  return { outA = outA, inA = inA, outB = outB, inB = inB };
}

/* Pose reelle. Un raccord brut n'est pas indexe sur le trace : ses quatre
 * tuiles ont ete choisies sur les leads. Sinon, memes arguments que V181. */
function OpexV233LPlaceSwitch(sw, tilesFrom, tilesTo, atEnd, outbound, placed)
{
  if (sw == null || !("fromIdx" in sw) || !("toIdx" in sw)) return false;
  if (("raw" in sw) && sw.raw == 1)
    return OpexV181TryBuildSwitch(sw.aPrev, sw.a, sw.b, sw.bNext, placed, false);
  local iFrom = sw.fromIdx;
  local iTo = sw.toIdx;
  if (tilesFrom == null || tilesTo == null) return false;
  if (iFrom <= 0 || iTo <= 0 || iFrom >= tilesFrom.len() - 1 || iTo >= tilesTo.len() - 1) return false;
  if (!atEnd && outbound)
    return OpexV181TryBuildSwitch(tilesFrom[iFrom - 1], tilesFrom[iFrom], tilesTo[iTo], tilesTo[iTo + 1], placed, false);
  if (!atEnd)
    return OpexV181TryBuildSwitch(tilesFrom[iFrom + 1], tilesFrom[iFrom], tilesTo[iTo], tilesTo[iTo - 1], placed, false);
  if (outbound)
    return OpexV181TryBuildSwitch(tilesFrom[iFrom + 1], tilesFrom[iFrom], tilesTo[iTo], tilesTo[iTo - 1], placed, false);
  return OpexV181TryBuildSwitch(tilesFrom[iFrom - 1], tilesFrom[iFrom], tilesTo[iTo], tilesTo[iTo + 1], placed, false);
}
