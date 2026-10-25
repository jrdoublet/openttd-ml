/* V216 (docs/plan_v216_scores_avant_premier_rail_20261016.md, etape 1) : sonde passive des
 * estimateurs. Rien ici ne modifie un tri, une admission, un financement ou un dimensionnement :
 * on journalise des champs deja calcules, sans recalcul d'economie. Inerte sans probes bit 29.
 * Etat transitoire, non persiste (un rechargement remet les compteurs a zero). */

V216_SELECT_SEQ <- 0;
V216_FIRST_PAX_BUILD <- -1;
V216_LAST_SELECT_DATE <- -1000;
V216_LAST_FLOW_MONTH <- -1;
V216_LAST_KDEC <- 0;
V216_FREIGHT_BUILDS <- 0;
V216_REJECTS <- [];
V216_REJECT_COUNTS <- { profit = 0, ratio = 0 };

/* Fenetre (3.1, resserree au smoke du 16/10 : chaque selection coutait 22 M opcodes en 3 ans) :
 * jusqu'a fin de 3e annee, une selection par semaine, plus toute selection ou un rail voyageurs
 * est dans les 3 premiers rangs (sur le point d'etre construit). */
function OpexV216SelectionWanted(funded)
{
  local now = AIDate.GetCurrentDate();
  if (AIDate.GetYear(now) > OPEX_START_YEAR + 2) return false;
  for (local i = 0; i < funded.len() && i < 3; i++) {
    local p = funded[i];
    if (p != null && ("mode" in p) && p.mode == "rail" && ("kind" in p) && p.kind == "pax") return true;
  }
  return now - V216_LAST_SELECT_DATE >= 7;
}

/* Sejour en gare mecanique (EST-16) : 40 ticks par tranche de 5 unites, wagons en parallele,
 * 74 ticks par jour. Le modele courant n'en compte aucun. */
function OpexV216DwellDays(perTrain, wagons)
{
  if (perTrain <= 0 || wagons <= 0) return 0.0;
  local perWagon = (perTrain + wagons - 1) / wagons;
  return 40.0 * ((perWagon + 4) / 5) / 74.0;
}

V216_KEYS_P <- ["mode", "kind", "cargo", "src", "dst", "distance", "capital", "budgetCapital", "profitAnnual", "revenueAnnual", "roi", "fundScore", "decisionFinanceCapital", "portfolioProfitAnnual", "portfolioDecisionFinanceCapital", "earlySlotBonusPct", "defensiveCompetitorClaims", "defensiveOwnClaims", "profitIsObserved", "v161ModelPerPlane"];
V216_KEYS_C <- ["monthly", "monthly2", "cargo2", "srcTown", "dstTown", "originServed", "trains", "wagons", "wagons2", "perTrain", "perTrain2", "oneWayDays", "effectiveSpeed", "tripsPerMonth", "headwayDays", "stationRating", "offered", "monthlyCapacity", "carried", "carried2", "revenue2", "runningAnnual", "amortAnnual", "vehicleCost", "immobilise", "platformLength", "iterations", "isLowRatio", "arm", "planes", "targetPlanes", "monthlyPax", "reuseA", "reuseB", "want", "baseVehicles", "planePrice"];
V216_KEYS_E <- ["planes", "capital", "airportCapital", "revenueAnnual", "revenuePaxAnnual", "revenueMailAnnual", "rawRevenueAnnual", "realizationFactor", "runningAnnual", "amortAnnual", "profitAnnual", "roundTripDays", "oneWayDays", "flightDays", "headwayDays", "stationRating", "offeredPaxA", "offeredPaxB", "offeredMailA", "offeredMailB", "carriedPax", "carriedMail", "paxCapacity", "mailCapacity", "routeSharePaxA", "routeSharePaxB", "existingPaxRateA", "existingPaxRateB", "cannibalLossAnnual", "decisionProfitAnnual", "decisionRevenueAnnual", "decisionCapital", "decisionPlanes", "decisionKDec"];
V216_KEYS_D <- ["paxA", "paxB", "mailA", "mailB", "paxProducedA", "paxProducedB", "currentPaxRatingA", "currentPaxRatingB"];

/* Liste blanche : le vidage generique de toutes les cles coutait 43,7 M opcodes en 3 ans (smoke). */
function OpexV216Pick(prefix, t, keyList)
{
  if (t == null || typeof t != "table") return "";
  local out = "";
  foreach (k in keyList) {
    if (!(k in t)) continue;
    local v = t[k];
    local tv = typeof v;
    if (tv == "integer" || tv == "string") out += " " + prefix + k + "=" + v;
    else if (tv == "float") out += " " + prefix + k + "=" + ((v * 100).tointeger() / 100.0);
    else if (tv == "bool") out += " " + prefix + k + "=" + (v ? 1 : 0);
  }
  return out;
}

function OpexV216ProjectLine(seq, role, rank, project, capitalBudget)
{
  local finance = OpexProjectFinanceCapital(project);
  local fundProfit = OpexProjectFundProfit(project);
  local fields = "seq=" + seq + " role=" + role + " rank=" + rank
      + " key=" + OpexProjectAttemptKey(project)
      + " finance=" + finance + " affordable=" + (finance <= capitalBudget ? 1 : 0)
      + " fund_profit=" + fundProfit
      + " k_mode_pct=" + (project.profitAnnual != 0 ? (fundProfit * 100) / project.profitAnnual : 0)
      + " tier=" + OpexProjectDefensiveAirPriority(project)
      + " select_score=" + (("fundScore" in project) ? OpexProjectSelectionScore(project, "fundScore") : 0)
      + OpexV216Pick("p.", project, V216_KEYS_P);
  if (("payload" in project) && project.payload != null && typeof project.payload == "table") {
    local c = project.payload;
    fields += OpexV216Pick("c.", c, V216_KEYS_C);
    if (project.mode == "rail" && ("perTrain" in c) && ("wagons" in c)) {
      local dwell = OpexV216DwellDays(c.perTrain, c.wagons);
      fields += " dwell_station_days=" + dwell + " dwell_model_days=0";
      if (("cargo" in c) && ("srcTown" in c) && ("dstTown" in c)) {
        fields += " prod_a=" + AITown.GetLastMonthProduction(c.srcTown, c.cargo)
            + " prod_b=" + AITown.GetLastMonthProduction(c.dstTown, c.cargo)
            + " supplied_a=" + AITown.GetLastMonthSupplied(c.srcTown, c.cargo)
            + " supplied_b=" + AITown.GetLastMonthSupplied(c.dstTown, c.cargo);
      }
    }
    if ("economics" in c) fields += OpexV216Pick("e.", c.economics, V216_KEYS_E);
    if ("c121Demand" in c) fields += OpexV216Pick("dm.", c.c121Demand, V216_KEYS_D);
  }
  local ghostMark = OpexOpsMeasureBegin();
  local ghost = (project.mode != "air" || (rank >= 0 && rank < 3)) ? OpexV216Ghost(project) : "";
  if (ghost != "") fields += ghost + " g.ops=" + OpexOpsMeasureEnd(ghostMark);
  OpexDecide("V216_DECOMP", fields);
}

/* 3.1 : appele apres chaque selection reelle (build / reselect / incremental). `funded` est le
 * classement complet (jusqu'a PROJECT_TOP_K), pas le seul projet construit. Lignes : rangs 0-19,
 * tout rail voyageurs classe ou finançable, et les 5 meilleurs non finançables par mode (tries
 * sur profitAnnual brut, champ deja present). */
function OpexV216LogSelection(path, alternatives, funded, capitalBudget)
{
  if (!OpexV216SelectionWanted(funded)) return;
  local mark = OpexOpsMeasureBegin();
  V216_LAST_SELECT_DATE = AIDate.GetCurrentDate();
  V216_SELECT_SEQ++;
  local seq = V216_SELECT_SEQ;
  local ranked = {};
  foreach (i, p in funded) {
    if (p == null) continue;
    ranked.rawset(OpexProjectAttemptKey(p), i);
    if (i < 20 || (p.mode == "rail" && ("kind" in p) && p.kind == "pax"))
      OpexV216ProjectLine(seq, "ranked", i, p, capitalBudget);
  }
  local affordable = 0;
  local unaffordable = {};
  foreach (p in alternatives) {
    if (p == null || !("mode" in p)) continue;
    if (OpexProjectFinanceCapital(p) <= capitalBudget) {
      affordable++;
      if (p.mode == "rail" && ("kind" in p) && p.kind == "pax"
          && !(OpexProjectAttemptKey(p) in ranked))
        OpexV216ProjectLine(seq, "affordable", -1, p, capitalBudget);
      continue;
    }
    if (!(p.mode in unaffordable)) unaffordable.rawset(p.mode, []);
    local list = unaffordable[p.mode];
    local pos = list.len();
    while (pos > 0 && list[pos - 1].profitAnnual < p.profitAnnual) pos--;
    if (pos < 5) {
      list.insert(pos, p);
      if (list.len() > 5) list.pop();
    }
  }
  local bestUnaff = null;
  foreach (mode, list in unaffordable) {
    foreach (i, p in list) OpexV216ProjectLine(seq, "unaffordable", i, p, capitalBudget);
    if (list.len() > 0 && (bestUnaff == null || list[0].profitAnnual > bestUnaff.profitAnnual))
      bestUnaff = list[0];
  }
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  OpexDecide("V216_SELECT", "seq=" + seq + " path=" + path
      + " budget=" + capitalBudget + " cash=" + cash
      + " loan=" + AICompany.GetLoanAmount() + " max_loan=" + AICompany.GetMaxLoanAmount()
      + " k_dec=" + V216_LAST_KDEC
      + " alternatives=" + alternatives.len() + " affordable=" + affordable
      + " ranked=" + funded.len()
      + " top_key=" + (funded.len() > 0 && funded[0] != null ? OpexProjectAttemptKey(funded[0]) : "none")
      + " best_unaff_mode=" + (bestUnaff != null ? bestUnaff.mode : "none")
      + " best_unaff_profit=" + (bestUnaff != null ? bestUnaff.profitAnnual : 0)
      + " best_unaff_finance=" + (bestUnaff != null ? OpexProjectFinanceCapital(bestUnaff) : 0)
      + " probe_ops=" + OpexOpsMeasureEnd(mark));
}

/* Date du premier RAIL_BUILD voyageurs (fenetre 3.1) et decomposition au premier fret. */
function OpexV216OnRailBuild(candidate)
{
  local kind = ("kind" in candidate) ? candidate.kind : "";
  if (kind == "pax" && V216_FIRST_PAX_BUILD < 0) V216_FIRST_PAX_BUILD = AIDate.GetCurrentDate();
  local project = { mode = "rail", kind = kind, cargo = candidate.cargo,
      src = candidate.src, dst = candidate.dst, payload = candidate,
      distance = candidate.distance, capital = candidate.capital,
      budgetCapital = candidate.capital, profitAnnual = candidate.profitAnnual,
      revenueAnnual = candidate.revenueAnnual, roi = candidate.roi };
  V216_SELECT_SEQ++;
  OpexV216ProjectLine(V216_SELECT_SEQ, "built_" + kind, 0, project, 0x7fffffff);
}

/* 3.3 : une fois par mois, flux par ville, par industrie et par gare. AICargoMonitor est reserve
 * aux scripts de jeu (absent de l'API IA 15.3, constate au smoke du 16/10) : la prise en charge
 * par compagnie n'est pas lisible. On journalise le total transporte (toutes compagnies), le
 * nombre de gares autour de chaque industrie (toutes compagnies) et, pour nos gares, note et
 * attente par cargo ; la part adverse se deduit hors ligne (ou des sauvegardes). */
function OpexV216MonthlyTick()
{
  local now = AIDate.GetCurrentDate();
  local year = AIDate.GetYear(now);
  if (year > OPEX_START_YEAR + 2) return;
  local ym = year * 12 + AIDate.GetMonth(now);
  if (ym == V216_LAST_FLOW_MONTH) return;
  V216_LAST_FLOW_MONTH = ym;
  local mark = OpexOpsMeasureBegin();
  local pax = OpexV216Cargo(AICargo.CC_PASSENGERS);
  local mail = OpexV216Cargo(AICargo.CC_MAIL);
  local logged = 0;
  foreach (town, tv in AITownList()) {
    local fields = "town=" + town + " pop=" + AITown.GetPopulation(town);
    local any = false;
    foreach (cargo in [pax, mail]) {
      if (cargo == null) continue;
      local label = AICargo.GetCargoLabel(cargo);
      local supplied = AITown.GetLastMonthSupplied(town, cargo);
      fields += " prod_" + label + "=" + AITown.GetLastMonthProduction(town, cargo)
          + " supplied_" + label + "=" + supplied
          + " pct_" + label + "=" + AITown.GetLastMonthTransportedPercentage(town, cargo);
      if (supplied > 0) any = true;
    }
    if (any) {
      OpexDecide("V216_TOWN_FLOW", fields);
      logged++;
    }
  }
  foreach (ind, iv in AIIndustryList()) {
    foreach (cargo, cv in AICargoList_IndustryProducing(ind)) {
      if (AIIndustry.GetLastMonthTransportedPercentage(ind, cargo) <= 0) continue;
      OpexDecide("V216_IND_FLOW", "industry=" + ind + " cargo=" + AICargo.GetCargoLabel(cargo)
          + " prod=" + AIIndustry.GetLastMonthProduction(ind, cargo)
          + " transported=" + AIIndustry.GetLastMonthTransported(ind, cargo)
          + " stations_around=" + AIIndustry.GetAmountOfStationsAround(ind));
      logged++;
    }
  }
  foreach (st, sv in AIStationList(AIStation.STATION_ANY)) {
    local fields = "station=" + st + " town=" + AIStation.GetNearestTown(st)
        + " rail=" + (AIStation.HasStationType(st, AIStation.STATION_TRAIN) ? 1 : 0)
        + " air=" + (AIStation.HasStationType(st, AIStation.STATION_AIRPORT) ? 1 : 0)
        + " road=" + ((AIStation.HasStationType(st, AIStation.STATION_BUS_STOP)
            || AIStation.HasStationType(st, AIStation.STATION_TRUCK_STOP)) ? 1 : 0);
    local any = false;
    foreach (cargo, cv in AICargoList()) {
      if (!AIStation.HasCargoRating(st, cargo)) continue;
      local label = AICargo.GetCargoLabel(cargo);
      fields += " rating_" + label + "=" + AIStation.GetCargoRating(st, cargo)
          + " waiting_" + label + "=" + AIStation.GetCargoWaiting(st, cargo);
      any = true;
    }
    if (any) {
      OpexDecide("V216_STATION_FLOW", fields);
      logged++;
    }
  }
  OpexDecide("V216_FLOW_DONE", "rows=" + logged + " probe_ops=" + OpexOpsMeasureEnd(mark));
}

function OpexV216Cargo(cls)
{
  foreach (cargo, lv in AICargoList()) {
    if (AICargo.HasCargoClass(cargo, cls)) return cargo;
  }
  return null;
}

/* 3.4 : rejets rail voyageurs a la generation ; garde les 5 moins mauvais par profit. */
function OpexV216NoteReject(reason, kind, srcTile, dstTile, monthly, economics)
{
  if (kind != "pax" || economics == null) return;
  V216_REJECT_COUNTS[reason] = V216_REJECT_COUNTS[reason] + 1;
  local row = { reason = reason, src = srcTile, dst = dstTile, monthly = monthly,
      distance = AIMap.DistanceManhattan(srcTile, dstTile), economics = economics };
  local pos = V216_REJECTS.len();
  while (pos > 0 && V216_REJECTS[pos - 1].economics.profitAnnual < economics.profitAnnual) pos--;
  if (pos < 5) {
    V216_REJECTS.insert(pos, row);
    if (V216_REJECTS.len() > 5) V216_REJECTS.pop();
  }
}

function OpexV216FlushRejects()
{
  if (V216_REJECT_COUNTS.profit == 0 && V216_REJECT_COUNTS.ratio == 0) return;
  OpexDecide("V216_GEN_REJECT", "n_profit=" + V216_REJECT_COUNTS.profit
      + " n_ratio=" + V216_REJECT_COUNTS.ratio + " top=" + V216_REJECTS.len());
  foreach (i, row in V216_REJECTS) {
    local e = row.economics;
    OpexDecide("V216_GEN_REJECT_TOP", "rank=" + i + " reason=" + row.reason
        + " src=" + row.src + " dst=" + row.dst + " distance=" + row.distance
        + " monthly=" + row.monthly
        + " dwell_station_days=" + (("perTrain" in e) && ("wagons" in e) ? OpexV216DwellDays(e.perTrain, e.wagons) : 0)
        + OpexV216Pick("e.", e, V216_KEYS_C) + OpexV216Pick("e.", e, V216_KEYS_P));
  }
  V216_REJECTS = [];
  V216_REJECT_COUNTS = { profit = 0, ratio = 0 };
}

/* 3.2 : estimateur fantome V216a, calcule et journalise, jamais utilise. Pour une extremite
 * (centre = tuile de ville du candidat rail, ou site AIR), dans le rayon de captage : tuiles
 * productrices, couvertes par nos gares, couvertes par des gares adverses seules, et la meilleure
 * note de nos gares qui les couvrent. Partage a la maniere de MoveGoodsToStation : le volume
 * deplace suit la meilleure note, reparti au prorata des notes ; la note adverse est illisible,
 * supposee egale a la notre. Approximation : la gare rail n'est pas encore placee, la zone est
 * centree sur la tuile de ville. AIR limite aux 3 premiers rangs. */
V216_COVER <- { ownMonth = -1, advQuarter = -1, own = {}, adv = {}, cache = {} };

function OpexV216StationRadius(tile)
{
  if (AIRail.IsRailStationTile(tile)) return AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  /* GetCoverageRadius(STATION_AIRPORT) vaut -1 : le rayon depend du type (smoke du 16/10). */
  if (AIAirport.IsAirportTile(tile)) {
    local r = AIAirport.GetAirportCoverageRadius(AIAirport.GetAirportType(tile));
    return r > 0 ? r : 4;
  }
  if (AIRoad.IsRoadStationTile(tile)) return AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  return AIStation.GetCoverageRadius(AIStation.STATION_DOCK);
}

/* Tables de couverture (refonte du 16/10 : le balayage tuile par tuile coutait 15 a 40 k opcodes
 * par extremite). `own[tuile] = [note voyageurs, note courrier]` maximales de nos gares qui la
 * couvrent, reconstruite chaque mois gare par gare sur la boite englobante de ses tuiles elargie
 * du rayon. Les gares adverses sont lues paresseusement autour de chaque centre et gardees un
 * trimestre (`adv[centre]`). Une gare posee dans le mois n'y figure qu'au mois suivant. */
V216_ADV_MAX_RADIUS <- 5;

function OpexV216MarkRect(table, x0, y0, x1, y1, ratings)
{
  if (x0 < 1) x0 = 1;
  if (y0 < 1) y0 = 1;
  if (x1 > AIMap.GetMapSizeX() - 2) x1 = AIMap.GetMapSizeX() - 2;
  if (y1 > AIMap.GetMapSizeY() - 2) y1 = AIMap.GetMapSizeY() - 2;
  for (local x = x0; x <= x1; x++) {
    for (local y = y0; y <= y1; y++) {
      local key = AIMap.GetTileIndex(x, y);
      if (ratings == null) {
        table.rawset(key, true);
      } else if (key in table) {
        local cur = table[key];
        if (ratings[0] > cur[0]) cur[0] = ratings[0];
        if (ratings[1] > cur[1]) cur[1] = ratings[1];
      } else {
        table.rawset(key, [ratings[0], ratings[1]]);
      }
    }
  }
}

function OpexV216RefreshCover()
{
  local now = AIDate.GetCurrentDate();
  local ym = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now) - 1;
  local cover = V216_COVER;
  if (cover.ownMonth == ym) return cover;
  cover.ownMonth = ym;
  cover.cache = {};
  cover.own = {};
  if (cover.advQuarter != ym / 3) {
    cover.advQuarter = ym / 3;
    cover.adv = {};
  }
  local pax = OpexV216Cargo(AICargo.CC_PASSENGERS);
  local mail = OpexV216Cargo(AICargo.CC_MAIL);
  foreach (st, sv in AIStationList(AIStation.STATION_ANY)) {
    local ratings = [0, 0];
    if (pax != null && AIStation.HasCargoRating(st, pax)) ratings[0] = AIStation.GetCargoRating(st, pax);
    if (mail != null && AIStation.HasCargoRating(st, mail)) ratings[1] = AIStation.GetCargoRating(st, mail);
    foreach (type in [AIStation.STATION_TRAIN, AIStation.STATION_AIRPORT, AIStation.STATION_BUS_STOP,
                      AIStation.STATION_TRUCK_STOP, AIStation.STATION_DOCK]) {
      if (!AIStation.HasStationType(st, type)) continue;
      local x0 = 99999, y0 = 99999, x1 = -1, y1 = -1, r = 0;
      foreach (tile, tv in AITileList_StationType(st, type)) {
        local x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
        if (x < x0) x0 = x;
        if (y < y0) y0 = y;
        if (x > x1) x1 = x;
        if (y > y1) y1 = y;
        if (r == 0) r = OpexV216StationRadius(tile);
      }
      if (x1 >= 0) OpexV216MarkRect(cover.own, x0 - r, y0 - r, x1 + r, y1 + r, ratings);
    }
  }
  return cover;
}

/* Tuiles couvertes par des gares adverses dans la fenetre d'un centre (rayon de captage + rayon
 * adverse maximal), lues une fois par trimestre et par centre. */
function OpexV216AdvAround(cover, center, radius)
{
  if (center in cover.adv) return cover.adv[center];
  local table = {};
  local me = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local cx = AIMap.GetTileX(center), cy = AIMap.GetTileY(center);
  local w = radius + V216_ADV_MAX_RADIUS;
  local tiles = AITileList();
  local mx = AIMap.GetMapSizeX() - 2, my = AIMap.GetMapSizeY() - 2;
  tiles.AddRectangle(AIMap.GetTileIndex(cx - w < 1 ? 1 : cx - w, cy - w < 1 ? 1 : cy - w),
      AIMap.GetTileIndex(cx + w > mx ? mx : cx + w, cy + w > my ? my : cy + w));
  tiles.Valuate(AITile.IsStationTile);
  tiles.KeepValue(1);
  foreach (tile, tv in tiles) {
    if (AITile.GetOwner(tile) == me) continue;
    if (!AIRail.IsRailStationTile(tile) && !AIAirport.IsAirportTile(tile)
        && !AIRoad.IsRoadStationTile(tile) && !AIMarine.IsDockTile(tile)) continue;
    local r = OpexV216StationRadius(tile);
    local x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
    OpexV216MarkRect(table, x - r > cx - radius ? x - r : cx - radius,
        y - r > cy - radius ? y - r : cy - radius,
        x + r < cx + radius ? x + r : cx + radius,
        y + r < cy + radius ? y + r : cy + radius, null);
  }
  cover.adv.rawset(center, table);
  return table;
}

function OpexV216Coverage(center, cargo, radius)
{
  local cover = OpexV216RefreshCover();
  local key = center + "|" + cargo + "|" + radius;
  if (key in cover.cache) return cover.cache[key];
  local adv = OpexV216AdvAround(cover, center, radius);
  local ci = AICargo.HasCargoClass(cargo, AICargo.CC_MAIL) ? 1 : 0;
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local res = { prod = 0, own = 0, adv = 0, ownRating = 0 };
  for (local x = cx - radius; x <= cx + radius; x++) {
    for (local y = cy - radius; y <= cy + radius; y++) {
      if (x < 1 || y < 1 || x >= AIMap.GetMapSizeX() - 1 || y >= AIMap.GetMapSizeY() - 1) continue;
      local tile = AIMap.GetTileIndex(x, y);
      if (AITile.GetCargoProduction(tile, cargo, 1, 1, 0) <= 0) continue;
      res.prod++;
      if (tile in cover.own) {
        res.own++;
        local r = cover.own[tile][ci];
        if (r > res.ownRating) res.ownRating = r;
      } else if (tile in adv) {
        res.adv++;
      }
    }
  }
  cover.cache.rawset(key, res);
  return res;
}

/* Gain net de la compagnie pour une extremite, en % de l'hypothese du modele (tuiles libres),
 * a la note prevue rn (%). 100 sans tuile productrice lisible. Partage par V216a. */
function OpexV216GainPct(center, cargo, radius, rn)
{
  if (center == null || center < 0 || rn <= 0) return 100;
  local c = OpexV216Coverage(center, cargo, radius);
  if (c.prod <= 0) return 100;
  local rnf = rn.tofloat();
  local ro = c.ownRating.tofloat();
  local best = rnf > ro ? rnf : ro;
  local free = (c.prod - c.own - c.adv).tofloat();
  return (100.0 * (free * rnf + c.own * (best - ro) + c.adv * rnf * 0.5) / (c.prod * rnf)).tointeger();
}

/* V216a : la demande du modele suppose toutes les tuiles de la ville libres. On la multiplie par
 * la moyenne des facteurs des deux extremites, a une note prevue constante de 35 % (mediane des
 * c.stationRating rail pax du smoke du 16/10) : mode 1 = gain net de la compagnie (une tuile deja
 * couverte par nous a une meilleure note ne rapporte rien), mode 2 = part de la ligne. */
V216A_RN <- 35;

function OpexV216aEndPct(center, cargo, radius)
{
  if (V216A_GHOST_DEMAND == 1) return OpexV216GainPct(center, cargo, radius, V216A_RN);
  if (center == null || center < 0) return 100;
  local c = OpexV216Coverage(center, cargo, radius);
  if (c.prod <= 0) return 100;
  local rnf = V216A_RN.tofloat();
  local ro = c.ownRating.tofloat();
  local best = rnf > ro ? rnf : ro;
  local free = (c.prod - c.own - c.adv).tofloat();
  local line = free * rnf + c.own * best * rnf / (rnf + ro) + c.adv * rnf * 0.5;
  return (100.0 * line / (c.prod * rnf)).tointeger();
}

function OpexV216aScaleDemand(srcTile, dstTile, cargo, monthly)
{
  local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  local pct = (OpexV216aEndPct(srcTile, cargo, radius) + OpexV216aEndPct(dstTile, cargo, radius)) / 2;
  if (pct >= 100) return monthly;
  return (monthly * pct) / 100;
}

/* Facteurs du fantome pour une extremite, rapportes a l'hypothese du modele (toutes les tuiles
 * libres, note prevue rn en %) : line = part de la ligne, gain = gain net de la compagnie. */
function OpexV216GhostEnd(tag, center, cargo, radius, rn)
{
  if (center == null || center < 0 || rn <= 0) return "";
  local c = OpexV216Coverage(center, cargo, radius);
  local out = " g." + tag + "_prod=" + c.prod + " g." + tag + "_own=" + c.own
      + " g." + tag + "_adv=" + c.adv + " g." + tag + "_rown=" + c.ownRating;
  if (c.prod <= 0) return out;
  local rnf = rn.tofloat();
  local ro = c.ownRating.tofloat();
  local free = (c.prod - c.own - c.adv).tofloat();
  local best = rnf > ro ? rnf : ro;
  local line = free * rnf + c.own * best * rnf / (rnf + ro) + c.adv * rnf * 0.5;
  local gain = free * rnf + c.own * (best - ro) + c.adv * rnf * 0.5;
  local base = c.prod * rnf;
  return out + " g." + tag + "_line_pct=" + (100.0 * line / base).tointeger()
      + " g." + tag + "_gain_pct=" + (100.0 * gain / base).tointeger();
}

function OpexV216Ghost(project)
{
  if (!("mode" in project) || !("payload" in project) || project.payload == null) return "";
  local c = project.payload;
  if (project.mode == "rail" && ("kind" in project) && project.kind == "pax") {
    local rn = ("stationRating" in c) ? c.stationRating : 0;
    local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
    return OpexV216GhostEnd("a", project.src, project.cargo, radius, rn)
        + OpexV216GhostEnd("b", project.dst, project.cargo, radius, rn);
  }
  if (project.mode == "air" && ("economics" in c) && c.economics != null) {
    local e = c.economics;
    local radius = (("airport" in c) && c.airport != null && ("type" in c.airport))
        ? AIAirport.GetAirportCoverageRadius(c.airport.type) : 4;
    if (radius <= 0) radius = 4;
    /* ratingPaxA/B sont en points /255 ; stationRating est en %, comme AIStation.GetCargoRating. */
    local ra = ("stationRating" in e) ? e.stationRating : 0;
    local rb = ra;
    local cargo = ("cargo" in project) ? project.cargo : 0;
    return OpexV216GhostEnd("a", project.src, cargo, radius, ra)
        + OpexV216GhostEnd("b", project.dst, cargo, radius, rb);
  }
  return "";
}
