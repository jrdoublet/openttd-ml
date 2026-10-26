/* Mechanical copies: python3 sweeps/po01c_generate.py.
 * Checkpoints retain VM locals; no captured closures. Never saved. */

function OpexPO01CPaxCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, candidateProfile = null, cruiseCache = null, paxBand = PAX_BAND_ALL, targetKind = null, targetId = -1, po01gDiagnostics = null)
{
  local po01fSitableCache = clone ::OpexSitableCache;
  local po01fOriginal = V216_COVER;
  // Private for the entire producer: intervening consumers cannot seed later pairs.
  // One cache epoch per producer, not per pair: suspension must not invalidate it.
  local po01fContext = { used = false, now = AIDate.GetCurrentDate(),
    diagnostics = po01gDiagnostics, cover = {
    ownMonth = po01fOriginal.ownMonth, advQuarter = po01fOriginal.advQuarter,
    own = po01fOriginal.own, adv = clone po01fOriginal.adv,
    cache = clone po01fOriginal.cache } };
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "before_first_yield", -1);
  local cargo = catalog.paxCargo;
  if (cargo < 0) { if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "after_last_yield", PO01C_WHERE.idx); return; }
  if (catalog.locoByCargoWagons != null && !(cargo in catalog.locoByCargoWagons)) { if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "after_last_yield", PO01C_WHERE.idx); return; }
  /* V275 bit 4 retire le 24/10 (decision utilisateur) : plus d'attente du rail voyageurs ; les priorites passent par la calibration. */
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local served = [];
  /* V275 bit 1 : villes ou nous avons deja un aeroport. Le rail y partagerait les memes
   * maisons que nos avions (V216 : 84 % du deficit rail voyageurs vient de nos modes). */
  local airTowns = null;
  if (V275_RAIL_PAX_MM & 1) {
    airTowns = {};
    foreach (po01eLineIndex, line in lines) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:air_lines", po01eLineIndex);
    }
      if (!("mode" in line) || line.mode != "air") continue;
      if (("scrapping" in line) && line.scrapping) continue;
      airTowns.rawset(line.originA, true);
      airTowns.rawset(line.originB, true);
    }
  }
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  for (local i = 0; i < n; i++) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:production", i);
    }
    local p = AITown.GetLastMonthProduction(towns[i].id, cargo);
    if (p <= 0 && towns[i].pop > 0) p = (towns[i].pop * 22) / 100;
    produced.append(p);
    local service = OpexOriginService(lines, towns[i].tile);
    served.append(service);
    if (service != null) stats.townsServed++; else stats.townsUnserved++;
  }
  local hasMail = V207_RAIL_MAIL && catalog.mailCargo >= 0 && (catalog.mailCargo in catalog.wagonByCargo);
  local mailProduced = null;
  if (hasMail) {
    mailProduced = [];
    for (local i = 0; i < n; i++) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:mail", i);
    }
      local mp = AITown.GetLastMonthProduction(towns[i].id, catalog.mailCargo);
      if (mp < 0) mp = 0;
      mailProduced.append(mp);
    }
  }
  if (profile != null) profile.paxPreparationOps += OpexOpsMeasureEnd(preparationMark);
  local pairTotalMark = profile != null ? OpexOpsMeasureBegin() : null;
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:OpexCatalogBounds", PO01C_WHERE.idx);
  local bounds = OpexCatalogBounds(catalog);
  local cellSize = bounds.railMax;
  if (cellSize < 1) cellSize = 1;
  local grid = OpexSpatialGrid();
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:grid.Build", PO01C_WHERE.idx);
  grid.Build(towns, cellSize);
  for (local a = 0; a < n; a++) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:neighbors", a);
    }
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:grid.GetCandidatesFor", PO01C_WHERE.idx);
    local neighbors = grid.GetCandidatesFor(a);
    foreach (b in neighbors) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:pair", b);
    }
      if (targetKind == "town" && targetId >= 0
          && towns[a].id != targetId && towns[b].id != targetId) continue;
      local pairDistance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (!OpexRailPaxPairInBand(bounds, pairDistance, paxBand)) continue;
      if (C60_TOWN_RATING_PROBE) {
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[a].id);
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[b].id);
      }
      if (abandonedPairs != null) {
        local tA = towns[a].id;
        local tB = towns[b].id;
        if (tA > tB) { local swap = tA; tA = tB; tB = swap; }
        local pairKey = "pax|" + cargo + "|" + tA + "|" + tB;
        if (pairKey in abandonedPairs) continue;
      }
      stats.pairsTotal++;
      if (profile != null) profile.paxPairsScanned++;
      local sa = served[a];
      local sb = served[b];
      if (sa != null || sb != null) {
        stats.pairsOriginServed++;
        continue;
      }
      if (airTowns != null && ((towns[a].tile in airTowns) || (towns[b].tile in airTowns))) {
        stats.pairsOriginServed++;
        continue;
      }
      /* Une ligne dessert les deux sens, et chaque sens transporte la production de SON
       * origine : le debit utile est la somme, pas le minimum. On ignore encore la croissance de
       * la ville que la desserte provoque (sous-estimation non calibree, plus petite que le
       * facteur ci-dessus d'apres la mesure). */
      local prodA = produced[a];
      local prodB = produced[b];
      local part = V207_RAIL_PAX_SHARE_PCT > 0 ? V207_RAIL_PAX_SHARE_PCT : TOWN_CATCHMENT_SHARE_PCT;
      local monthly = ((prodA + prodB) * part) / 100;
      local secondary = null;
      if (hasMail) {
        local mailA = mailProduced[a];
        local mailB = mailProduced[b];
        local mailMonthly = ((mailA + mailB) * part) / 100;
        secondary = { cargo = catalog.mailCargo, monthly = mailMonthly };
      }
      local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
      if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "rail_pax:pair_candidate", PO01C_WHERE.idx);
      local po01dBox = { value = null };
    local po01dChild = OpexPO01CMakePaxCandidate(po01dBox, po01fSitableCache, po01fContext, catalog, "pax", cargo, towns[a].tile, towns[b].tile, monthly, false, stats, false, candidateProfile, cruiseCache, secondary);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    local candidate = po01dBox.value;
      if (profile != null) {
        profile.paxCandidateOps += OpexOpsMeasureEnd(candidateMark);
        profile.paxCandidateCalls++;
      }
      if (candidate != null) {
        candidate.srcTown <- towns[a].id;
        candidate.dstTown <- towns[b].id;
        out.append(candidate);
      }
    }
  }
  if (profile != null) profile.paxPairTotalOps += OpexOpsMeasureEnd(pairTotalMark);
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CPaxCandidates", "after_last_yield", PO01C_WHERE.idx);
  ::OpexSitableCache = po01fSitableCache;
  if (po01fContext.used) V216_COVER = po01fContext.cover;
}

function OpexPO01CFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1, p1LongState = null)
{
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "before_first_yield", -1);
  /* C41.44 : les lignes sont immuables pendant une generation ; une ville peut donc reutiliser
   * exactement son resultat OpexOriginService, y compris null et l'etat blocked. */
  local townServiceCache = {};
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local served = [];
  for (local i = 0; i < industries.len(); i++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:service", i);
    local service = OpexOriginService(lines, industries[i].tile);
    served.append(service);
    if (service != null) stats.industriesServed++; else stats.industriesUnserved++;
  }
  if (profile != null) profile.freightPreparationOps += OpexOpsMeasureEnd(preparationMark);
  foreach (cargo, sources in catalog.producers) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:cargo", cargo);
    if (freightCargo != null && cargo != freightCargo) continue;
    if (catalog.locoByCargoWagons != null && !(cargo in catalog.locoByCargoWagons)) continue;
    local hasIndustrySinks = (cargo in catalog.acceptors);
    local hasTownSinks = (cargo in catalog.townAcceptors);
    if (!hasIndustrySinks && !hasTownSinks) continue;
    local sinks = hasIndustrySinks ? catalog.acceptors[cargo] : [];

    foreach (si in sources) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:source", si);
      local source = industries[si];
      if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local ss = served[si];
      local others2 = null;
      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:industry_pair", k);
        local di = sinks[k];
        if (di == si) continue;
        if (targetKind == "town") continue;
        if (targetKind == "industry" && targetId >= 0
            && source.id != targetId && industries[di].id != targetId) continue;
        if (abandonedPairs != null) {
          local pairKey = "freight|" + cargo + "|" + source.id + "|" + industries[di].id;
          if (pairKey in abandonedPairs) continue;
        }
        stats.pairsTotal++;
        local sd = served[di];
        /* V179 : source neuve, destination deja desservie : on garde la paire, V178 la rattache.
         * Ce chemin n'est pas marque convergent : V264 ne s'execute que dans l'exclusion. */
        local v179Keep = ss == null && sd != null;
        if (!v179Keep && (ss != null || sd != null)) {
          /* Paires deja rejetees. A 0 le drapeau est faux : aucun appel, pairsOriginServed. */
          local attached = null;
          if (ss == null && sd != null) {
            attached = OpexV264ConvergentService(lines, sd, cargo, source.tile);
          }
          if (attached == null) {
            stats.pairsOriginServed++;
            continue;
          }
          if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:OpexV264EmitConvergent", PO01C_WHERE.idx);
          local kept = OpexV264EmitConvergent(catalog, stats, profile, cruiseCache, cargo,
                                              source, industries[di], monthly, others2, attached);
          if (kept != null) out.append(kept);
          continue;
        }
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        /* P1 : les paires hors railMax ne doivent pas evincer les courtes du TopK
         * papier. En shadow les stats historiques restent identiques. */
        if (p1LongState != null && monthly > 0
            && OpexP1LongOffer(p1LongState, catalog, cargo, source, industries[di],
                               monthly, isTransformer)) {
          stats.distanceLong++;
          continue;
        }
        local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
        local secondary = null;
        if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:pair_candidate", PO01C_WHERE.idx);
        local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                            industries[di].tile, monthly, false, stats, isTransformer, profile, cruiseCache,
                                            secondary);
        if (profile != null) {
          profile.freightIndustryCandidateOps += OpexOpsMeasureEnd(candidateMark);
          profile.freightIndustryCandidateCalls++;
        }
        if (candidate != null) {
          if (v179Keep) candidate.v179DestServed <- 1;
          out.append(candidate);
        }
      }
      if (profile != null) profile.freightIndustryOps += OpexOpsMeasureEnd(industryMark);

      /* Livraison des marchandises complexes aux villes acceptatrices (Goods, Food, Mail, etc.) */
      if (hasTownSinks) {
        local townMark = profile != null ? OpexOpsMeasureBegin() : null;
        local townSinks = catalog.townAcceptors[cargo];
        for (local k = 0; k < townSinks.len(); k++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:town_pair", k);
          local town = townSinks[k];
          if (targetKind == "industry" && targetId >= 0 && source.id != targetId) continue;
          if (targetKind == "town" && targetId >= 0 && town.id != targetId) continue;
          local townGuardMark = (profile != null && C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE) ? OpexOpsMeasureBegin() : null;
          if (abandonedPairs != null) {
            /* G9Â§1 : utiliser "t" + town.id au lieu de GetIndustryID (qui retourne -1
             * pour une ville), en coherence avec OpexAbandonedPairKey. */
            local pairKey = "freight|" + cargo + "|" + source.id + "|t" + town.id;
            if (pairKey in abandonedPairs) {
              if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
              continue;
            }
          }
          stats.pairsTotal++;
          local townServiceMark = (profile != null && C41_RAIL_FREIGHT_TOWN_GUARDS_PROFILE) ? OpexOpsMeasureBegin() : null;
          local st = null;
          if (townServiceCache != null && town.id in townServiceCache) st = townServiceCache[town.id];
          else {
            st = OpexOriginService(lines, town.tile);
            if (townServiceCache != null) townServiceCache[town.id] <- st;
          }
          if (townServiceMark != null) { profile.freightTownServiceOps += OpexOpsMeasureEnd(townServiceMark); profile.freightTownServiceCalls++; }
          if (ss != null || st != null) {
            stats.pairsOriginServed++;
            if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
            continue;
          }
          local townMonthly = monthly;
          if (townMonthly <= 0) {
            if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
            continue;
          }
          if (townGuardMark != null) { profile.freightTownGuardsOps += OpexOpsMeasureEnd(townGuardMark); profile.freightTownGuardsCalls++; }
          if (C60_TOWN_RATING_PROBE) {
            OpexC60ObserveTownRating("rail", "candidate_gen", town.id);
          }
          local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
          if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "rail_freight:pair_candidate", PO01C_WHERE.idx);
          local candidate = OpexMakeCandidate(catalog, "freight", cargo, source.tile,
                                              town.tile, townMonthly, false, stats, false, profile, cruiseCache);
          if (profile != null) {
            profile.freightTownCandidateOps += OpexOpsMeasureEnd(candidateMark);
            profile.freightTownCandidateCalls++;
          }
          if (candidate != null) {
            candidate.dstTown <- town.id;
            out.append(candidate);
          }
        }
        if (profile != null) profile.freightTownOps += OpexOpsMeasureEnd(townMark);

      }
    }
  }
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CFreightCandidates", "after_last_yield", PO01C_WHERE.idx);
}

function OpexPO01CRoadFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, freightCargo = null, targetKind = null, targetId = -1)
{
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "before_first_yield", -1);
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local towns = catalog.towns;
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:OpexRoadFreightServedIndex", PO01C_WHERE.idx);
  local servedIndex = OpexRoadFreightServedIndex(lines);
  local servedIndustry = [];
  for (local i = 0; i < industries.len(); i++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:industry_service", i);
    servedIndustry.append(servedIndex != null
        ? (industries[i].tile in servedIndex) : OpexOriginServed(lines, industries[i].tile, true));
  }
  local servedTown = [];
  for (local i = 0; i < towns.len(); i++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:town_service", i);
    servedTown.append(servedIndex != null
        ? (towns[i].tile in servedIndex) : OpexOriginServed(lines, towns[i].tile, true));
  }

  /* L'acceptation d'une ville ne depend que du couple (ville, cargo) : la calculer une fois par
   * couple, et non par paire industrie-ville, evite de repayer AITile.GetCargoAcceptance pour
   * chaque producteur du meme cargo. Cle chaine plutot que table imbriquee : une seule table. */
  local acceptanceCache = {};
  /* Rayon d'une aire de chargement : c'est bien l'empreinte de la gare qu'on projette de poser,
   * pas un rayon arbitraire autour du centre administratif. Lu une fois, il ne change jamais. */
  local truckCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRUCK_STOP);
  if (profile != null) profile.freightPreparationOps += OpexOpsMeasureEnd(preparationMark);

  foreach (cargo, sources in catalog.producers) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:cargo", cargo);
    if (freightCargo != null && cargo != freightCargo) continue;
    if (!(cargo in catalog.roadEngineByCargo)) { stats.noEngine++; continue; }
    /* Les passagers sont traites par la famille 1 : les inclure ici apparierait une industrie a
     * une ville pour un cargo qu'aucune industrie ne produit utilement en volume. */
    if (cargo == catalog.paxCargo) continue;
    local sinks = (cargo in catalog.acceptors) ? catalog.acceptors[cargo] : [];
    /* C41.20 : la liste est locale au cargo et a cette generation. Les appels API anticipes sont
     * purs ; ils ne changent ni l'industrie, ni le filtre de distance, ni l'ordre des candidats. */
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:OpexRoadFreightAcceptedTowns", PO01C_WHERE.idx);
    local townTargets = OpexRoadFreightAcceptedTowns(towns, servedTown, cargo, truckCoverage);
    if (townTargets != null) stats.townAcceptancePrefiltered += towns.len() - townTargets.len();

    foreach (si in sources) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:source", si);
      if (servedIndustry[si]) {
        /* Le code livre saute toute la source. Sous sonde, enumerer seulement les paires
         * qu'il aurait sautees permet de compter ce filtre sans changer son continue. */
        if (C55_ORIGIN_RELAX_PROBE) {
          local source = industries[si];
          foreach (di in sinks) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:rejected_industry", di);
            if (di != si) OpexC55OriginRelaxObserve("freight", lines, source.tile,
                industries[di].tile, true, servedIndustry[di]);
          }
          for (local ti = 0; ti < towns.len(); ti++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:rejected_town", ti);
            OpexC55OriginRelaxObserve("freight", lines, source.tile, towns[ti].tile,
                true, servedTown[ti]);
          }
        }
        continue;
      }
      local source = industries[si];
      if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      if (monthly <= 0) { stats.noMonthly++; continue; }

      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:industry_pair", k);
        local di = sinks[k];
        if (di == si) continue;
        if (targetKind == "town") continue;
        if (targetKind == "industry" && targetId >= 0
            && source.id != targetId && industries[di].id != targetId) continue;
        if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("road", 1);
        if (C55_ORIGIN_RELAX_PROBE) OpexC55OriginRelaxObserve("freight", lines,
            source.tile, industries[di].tile, false, servedIndustry[di]);
        if (servedIndustry[di]) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("road", "origin_served", 1);
          continue;
        }
        local distance = AIMap.DistanceManhattan(source.tile, industries[di].tile);
        if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
        if (abandonedPairs != null) {
          local pairKey = "freight|" + cargo + "|" + source.id + "|" + industries[di].id;
          if (pairKey in abandonedPairs) continue;
        }
        stats.pairsInBand++;
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:pair_candidate", PO01C_WHERE.idx);
        local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo, source.tile,
                                                industries[di].tile, -1, -1, distance, monthly,
                                                stats, isTransformer);
        if (candidate != null) out.append(candidate);
      }
      if (profile != null) profile.freightIndustryOps += OpexOpsMeasureEnd(industryMark);

      /* C41.19 pose des marques internes autour des deux appels chers : ne jamais les imbriquer
       * dans la mesure globale town, qui peut traverser un suspend. */
      local townMark = (profile != null && !C41_ROAD_FREIGHT_TOWN_PROFILE)
          ? OpexOpsMeasureBegin() : null;
      /* L'index C41.20 saute les villes deja servies avant la boucle. Les enumerer ici sous
       * sonde conserve exactement cet index et rend ce second site de rejet visible. */
      if (C55_ORIGIN_RELAX_PROBE && townTargets != null) {
        for (local ti = 0; ti < towns.len(); ti++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:town_probe", ti);
          OpexC55OriginRelaxObserve("freight", lines, source.tile, towns[ti].tile,
              false, servedTown[ti]);
        }
      }
      local townPool = (townTargets != null) ? townTargets : towns;
      for (local k = 0; k < townPool.len(); k++) {
    yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:town_pair", k);
        local ti = k;
        local t = (townTargets != null) ? townTargets[ti] : ti;
        if (targetKind == "industry" && targetId >= 0 && source.id != targetId) continue;
        if (targetKind == "town" && targetId >= 0 && towns[t].id != targetId) continue;
        if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("road", 1);
        if (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE) profile.freightTownScanned++;
        if (C55_ORIGIN_RELAX_PROBE && townTargets == null) OpexC55OriginRelaxObserve("freight",
            lines, source.tile, towns[t].tile, false, servedTown[t]);
        if (townTargets == null && servedTown[t]) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("road", "origin_served", 1);
          continue;
        }
        local distance = AIMap.DistanceManhattan(source.tile, towns[t].tile);
        if (!OpexRoadDistanceAllowed(catalog, distance, stats)) continue;
        if (abandonedPairs != null) {
          /* G9Â§1 : "t" + towns[t].id, en coherence avec OpexAbandonedPairKey. */
          local pairKey = "freight|" + cargo + "|" + source.id + "|t" + towns[t].id;
          if (pairKey in abandonedPairs) continue;
        }
        local acceptance;
        if (townTargets != null) {
          /* L'index a deja verifie acceptance >= 8. Ne pas reecrire townRejected : son compteur
           * historique de paires filtrees n'est pertinent que sur le chemin exhaustif OFF. */
          acceptance = ROAD_ACCEPTANCE_FULL_UNIT;
        } else {
          local key = t + "|" + cargo;
          if (key in acceptanceCache) {
            acceptance = acceptanceCache[key];
            if (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE) profile.freightTownAcceptanceHits++;
          } else {
            local acceptanceMark = (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE)
                ? OpexOpsMeasureBegin() : null;
            acceptance = AITile.GetCargoAcceptance(towns[t].tile, cargo, 1, 1, truckCoverage);
            acceptanceCache.rawset(key, acceptance);
            if (acceptanceMark != null) {
              profile.freightTownAcceptanceOps += OpexOpsMeasureEnd(acceptanceMark);
              profile.freightTownAcceptanceMisses++;
            }
          }
        }
        if (acceptance < ROAD_ACCEPTANCE_FULL_UNIT) { stats.townRejected++; continue; }
        stats.pairsInBand++;
        if (C60_TOWN_RATING_PROBE) {
          OpexC60ObserveTownRating("road", "candidate_gen", towns[t].id);
        }
        local candidateMark = (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE)
            ? OpexOpsMeasureBegin() : null;
        if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "road_freight:pair_candidate", PO01C_WHERE.idx);
        local candidate = OpexMakeRoadCandidate(catalog, "freight", cargo, source.tile,
                                                towns[t].tile, -1, towns[t].id, distance, monthly,
                                                stats);
        if (candidateMark != null) {
          profile.freightTownCandidateOps += OpexOpsMeasureEnd(candidateMark);
          profile.freightTownAcceptedPairs++;
        }
        if (candidate != null) out.append(candidate);
      }
      if (townMark != null) profile.freightTownOps += OpexOpsMeasureEnd(townMark);

    }
  }
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRoadFreightCandidates", "after_last_yield", PO01C_WHERE.idx);
}

function OpexPO01CWaterPlans(catalog, lines = null, projects = null, profile = null, siteCatalog = null)
{
  if (catalog.ships.len() == 0 || catalog.paxCargo < 0) {
    if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("water", "no_engine", 1);
    return;
  }
  local mark = profile != null ? OpexOpsMeasureBegin() : null;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "water_town_sort", "-");
  local towns = OpexWaterSortedTowns(catalog.towns);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "water_town_sort", "-");
  if (profile != null) profile.town_sort_ops = OpexOpsMeasureEnd(mark);
  local historical = siteCatalog == null;
  local limit = towns.len() < (historical ? WATER_TOWN_POOL : WATER_TOWN_POOL)
      ? towns.len() : (historical ? WATER_TOWN_POOL : WATER_TOWN_POOL);
  local sites = historical ? [] : [];
  local probes = { left = WATER_MAX_SITE_PROBES, townsLeft = limit };
  mark = profile != null ? OpexOpsMeasureBegin() : null;
  local start = 0;
  if (!historical && towns.len() > 0 && siteCatalog != null) start = 0;
  local c56TownsScanned = 0;
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "water_site_scan", "-");
  for (local step = 0; step < limit; step++) {
    yield null; // PO01C_CHECKPOINT
    if (C56_TASK_TRACE) c56TownsScanned++;
    local i = historical ? step : step;
    if (profile != null) profile.towns_considered++;
    if (OpexWaterTownServed(towns[i], lines)) {
      if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("water", "origin_served", 1);
      continue;
    }
    local wasKnownComplete = !historical && siteCatalog != null;
    local townSites = OpexWaterHistoricalSites(towns[i], siteCatalog, probes,
                                                  null);
    if (townSites.len() == 0 && C69_BOTTLENECK_PROBE) OpexC73RecordRejection("water", "no_site", 1);
    if (historical || !wasKnownComplete) foreach (site in townSites) sites.append(site);
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "water_site_scan",
                                      "- towns=" + c56TownsScanned);
  if (!historical && towns.len() > 0 && siteCatalog != null) start = 0;
  if (profile != null) {
    profile.site_ops = OpexOpsMeasureEnd(mark);
    profile.site_scan_filter_ops = profile.site_ops - profile.dock_test_ops;
    profile.sites_found = sites.len();
    mark = OpexOpsMeasureBegin();
  }
  /* G11 : le BFS sert aussi a l'economie. Le limiter apres un classement Manhattan pouvait
   * elire un detour cotier comme s'il etait direct et ecarter une paire reellement meilleure.
   * Le bassin est deja borne par WATER_TOWN_POOL ; chaque paire admissible est donc chiffree
   * avec sa longueur navigable avant son classement. */
  local ranked = [];
  local c73WaterProduced = 0;
  local c56PairsExamined = 0;
  local c56LegacyInZero = 0;
  local c56LegacyOutZero = 0;
  local c56BfsIn = 0;
  local c56BfsOut = 0;
  /* Deux compteurs zero conservent le format et le cout du trace C56 historique. */
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "water_pair_loop", "-");
  for (local a = 0; a < sites.len(); a++) {
    yield null; // PO01C_CHECKPOINT
    for (local b = a + 1; b < sites.len(); b++) {
    yield null; // PO01C_CHECKPOINT
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("water", 1);
      /* Intervalle ramene de 500 a 10 le 2026-09-11 : a 500, la ligne n'etait JAMAIS atteinte
       * avant le gel, et la sonde restait muette sur le cas meme qu'elle devait diagnostiquer.
       * Un appel sain examine 0 paire (moins de deux sites), donc ce pas fin ne coute rien. */
      if (C56_TASK_TRACE) {
        c56PairsExamined++;
        if (c56PairsExamined % 10 == 0) {
          OpexC56TaskLog("WATER_PROBE_COUNTERS", "water_probe_counters",
                         "- pairs=" + c56PairsExamined + " lakes_in=" + c56LegacyInZero
                         + " lakes_out=" + c56LegacyOutZero + " bfs_in=" + c56BfsIn
                         + " bfs_out=" + c56BfsOut);
        }
      }
      if (profile != null) profile.pairs_considered++;
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
      if (distance < WATER_TOWN_MIN_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("water", "distance_short", 1);
        continue;
      }
      local orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_WATER,
                                                      sites[a].dock, sites[b].dock);
      if (orderDistance < 0 || !OpexWaterHasRange(catalog, orderDistance)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("water", "no_range", 1);
        continue;
      }
      if (profile != null) profile.pairs_after_range++;
      local monthlyPax = ((sites[a].town.pop + sites[b].town.pop) * 22) / 100;

      /* Distance TARIFAIRE (Manhattan entre quais, pas entre centres-villes) : corrige
       * inconditionnellement (bug independant du choix Lakes/BFS ci-dessous), voir
       * OpexWaterEconomics. */
      local tariffDistance = AIMap.DistanceManhattan(sites[a].dock, sites[b].dock);
      local navigableDistance = -1;

      {
        /* Comportement historique : un seul BFS fait connectivite ET distance, les deux
         * bornees par WATER_BFS_MARGIN. */
        local bfsMark = profile != null ? OpexOpsMeasureBegin() : null;
        if (C56_TASK_TRACE) { c56BfsIn++; OpexC56TaskLog("PAIR", "bfs_enter", "- pair=" + c56PairsExamined); }
        local po01dBox = { value = null };
    local po01dChild = OpexPO01CWaterFindConnection(po01dBox, sites[a], sites[b]);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    navigableDistance = po01dBox.value;
        if (C67_WATER_EXPOSURE) OpexC67WaterExposureNote(sites[a], sites[b], navigableDistance,
                                                         tariffDistance, orderDistance, monthlyPax);
        if (C56_TASK_TRACE) { c56BfsOut++; OpexC56TaskLog("PAIR", "bfs_exit", "- pair=" + c56PairsExamined); }
        if (profile != null) {
          profile.bfs_ops += OpexOpsMeasureEnd(bfsMark);
          profile.bfs_attempts++;
        }
        if (navigableDistance < 0) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("water", "no_connection", 1);
          continue;
        }
        if (profile != null) profile.bfs_connected++;
      }

      local economicsMark = profile != null ? OpexOpsMeasureBegin() : null;
      local economics = OpexWaterEconomics(catalog, navigableDistance, tariffDistance,
                                            orderDistance, monthlyPax);
      if (profile != null) {
        profile.economics_ops += OpexOpsMeasureEnd(economicsMark);
        profile.economics_attempts++;
      }
      if (economics == null || economics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("water", "profit_nonpositive", 1);
        continue;
      }
      if (profile != null) profile.positive_economics++;
      if (C69_BOTTLENECK_PROBE) c73WaterProduced++;
      local plan = { siteA = sites[a], siteB = sites[b], distance = navigableDistance,
                     tariffDistance = tariffDistance,
                     orderDistance = orderDistance, economics = economics };
      local pos = ranked.len();
      while (pos > 0 && (ranked[pos - 1].economics.roi < economics.roi ||
             (ranked[pos - 1].economics.roi == economics.roi &&
              ranked[pos - 1].economics.profitAnnual < economics.profitAnnual))) pos--;
      ranked.insert(pos, plan);
      if (ranked.len() > WATER_PROJECT_POOL) ranked.pop();
    }
  }
  if (C69_BOTTLENECK_PROBE) OpexC73RecordProduced("water", c73WaterProduced, ranked.len());
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "water_pair_loop",
                                      "- pairs=" + c56PairsExamined);
  if (profile != null) {
    profile.pair_total_ops = OpexOpsMeasureEnd(mark);
    profile.pair_filter_rank_ops = profile.pair_total_ops - profile.bfs_ops - profile.economics_ops;
  }
  local best = null;
  foreach (plan in ranked) {
    yield null; // PO01C_CHECKPOINT
    if (projects != null) projects.append(plan);
    if (best == null) best = plan;
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("WATER_PROBE_COUNTERS", "water_probe_counters",
                                      "- pairs=" + c56PairsExamined + " lakes_in=" + c56LegacyInZero
                                      + " lakes_out=" + c56LegacyOutZero + " bfs_in=" + c56BfsIn
                                      + " bfs_out=" + c56BfsOut);
  return;
}

function OpexPO01CRail(catalog)
{
  catalog.loco = null;
  catalog.railLocos = [];
  catalog.wagonByCargo = {};
  catalog.locoByCargoWagons = {};
  catalog.wagonChoicesByCargo = {};

  /* `station_spread` est la borne que CmdBuildRailStation controle sur `length`. Dans OpenTTD
   * 15.3 elle est entiere, entre 4 et 64, et vaut 12 dans la configuration gelee ; on lit donc la
   * partie, jamais un "7" suppose. Une valeur invalide signifie API/reglage indisponible : mieux
   * vaut alors rendre le rail non constructible que fabriquer une longueur silencieuse. */
  catalog.platformLength = AIGameSettings.GetValue("station.station_spread");
  catalog.maxTrainLength = AIGameSettings.GetValue("vehicle.max_train_length");
  catalog.freightTrainMultiplier = AIGameSettings.GetValue("vehicle.freight_trains");
  catalog.railCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  if (catalog.platformLength < 1 || catalog.freightTrainMultiplier < 1 || catalog.railCoverage < 1) return;

  /* Dernier type disponible. 1970 = ELECTRIC (intro 1967). 2000 = MONO : ne pas
   * allonger une campagne jusque-la sans figer le type. Maglev pas encore en 2000
   * (results/catalogue_churn_1950_2000.json). */
  local types = AIRailTypeList();
  types.Valuate(AIRail.IsRailTypeAvailable);
  types.KeepValue(1);
  /* Le choix ne doit PAS dependre de l'ordre d'iteration : le tri par defaut d'une AIList est
   * SORT_BY_VALUE DECROISSANT (script_list.cpp:397-403), donc le Valuate ci-dessus change cet
   * ordre. L'ancien "le dernier gagne" rendait le type de rail dependant du tri -- invisible a
   * 3 ans de partie ou un seul type est disponible, et instable des qu'il y en a plusieurs.
   * Voir docs/mecanique_jeu.md S15.1. */
  local chosen = -1;
  for (local t = types.Begin(); !types.IsEnd(); t = types.Next()) {
    yield null; // PO01C_CHECKPOINT
    if (OpexRailTypePreferred(t, chosen)) chosen = t;
  }
  if (chosen < 0) return;
  catalog.railType = chosen;
  AIRail.SetCurrentRailType(chosen);
  catalog.costTrackPerTile = AIRail.GetBuildCost(chosen, AIRail.BT_TRACK);
  catalog.costStation = AIRail.GetBuildCost(chosen, AIRail.BT_STATION);
  /* Le depot rail etait le seul cout d'infrastructure absent du modele, alors que la route
   * et l'eau comptent le leur et que builder_rail.nut le paie reellement. */
  catalog.costRailDepot = AIRail.GetBuildCost(chosen, AIRail.BT_DEPOT);
  catalog.costRailSignal = AIRail.GetBuildCost(chosen, AIRail.BT_SIGNAL);

  local engines = AIEngineList(AIVehicle.VT_RAIL);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    yield null; // PO01C_CHECKPOINT
    if (AIEngine.IsWagon(e)) {
      local cargo = AIEngine.GetCargoType(e);
      local capacity = AIEngine.GetCapacity(e);
      if (capacity <= 0) continue;
      /* Un seul wagon retenu par cargo : le plus capacitaire. La sonde M3 conserve en parallele
       * les alternatives SANS changer ce departage, y compris son premier-gagne en cas d'egalite. */
      local replaces = !(cargo in catalog.wagonByCargo) || capacity > catalog.wagonByCargo[cargo].capacity;
      if (!replaces && !EQUIPMENT_ROI_PROBE) continue;
      local cargoWeight = AICargo.GetWeight(cargo, capacity);
      /* Le moteur applique `vehicle.freight_trains` aux seuls cargos fret dans Train::GetWeight.
       * AICargo.GetWeight livre le poids nu, donc le multiplicateur lu ci-dessus est indispensable
       * pour que la masse utilisee par le catalogue soit celle du convoi plein reel. */
      if (AICargo.IsFreight(cargo)) cargoWeight *= catalog.freightTrainMultiplier;
      local entry = {
        id = e, capacity = capacity, speed = AIEngine.GetMaxSpeed(e), price = AIEngine.GetPrice(e),
        weight = AIEngine.GetWeight(e), fullWeight = AIEngine.GetWeight(e) + cargoWeight,
        runningCost = AIEngine.GetRunningCost(e), ageYears = AIEngine.GetMaxAge(e) / 365,
      };
      if (EQUIPMENT_ROI_PROBE) {
        if (!(cargo in catalog.wagonChoicesByCargo)) catalog.wagonChoicesByCargo.rawset(cargo, []);
        catalog.wagonChoicesByCargo[cargo].append(entry);
      }
      if (replaces) {
        if (cargo in catalog.wagonByCargo) catalog.wagonByCargo[cargo] = entry;
        else catalog.wagonByCargo.rawset(cargo, entry);
      }
    } else {
      /* ⚠️ PIEGE D'API, verifie le 2026-08-28. CanRunOnRail() ne suffit PAS : une locomotive
       * ELECTRIQUE "peut rouler" sur une voie non electrifiee (elle peut y etre tractee), mais
       * elle n'y a AUCUNE PUISSANCE. Symptome observe : AIEngine.IsBuildable et CanRunOnRail
       * rendaient tous deux vrai, le depot etait valide, la tresorerie suffisante -- et
       * AIVehicle.BuildVehicle echouait avec ERR_UNKNOWN sur les 100 tentatives. Le diagnostic
       * qui a tranche : engine_rail = 1 (electrifie) contre depot_rail = 0.
       * HasPowerOnRail() est le bon predicat. */
      if (!AIEngine.CanRunOnRail(e, chosen)) continue;
      if (!AIEngine.HasPowerOnRail(e, chosen)) continue;
      local speed = AIEngine.GetMaxSpeed(e);
      local power = AIEngine.GetPower(e);
      local weight = AIEngine.GetWeight(e);
      local tractiveEffort = AIEngine.GetMaxTractiveEffort(e);
      if (speed <= 0 || power <= 0 || weight <= 0 || tractiveEffort <= 0) continue;
      local entry = {
        id = e, speed = speed, power = power, weight = weight, tractiveEffort = tractiveEffort,
        price = AIEngine.GetPrice(e), runningCost = AIEngine.GetRunningCost(e),
        ageYears = AIEngine.GetMaxAge(e) / 365,
      };
      catalog.railLocos.append(entry);
      /* Conserve seulement le comparateur historique pour OL annuel : il ne decide plus RIEN. */
      if (catalog.loco == null || speed > catalog.loco.speed) {
        catalog.loco = entry;
      }
    }
  }

  /* Precalcul de la seule boucle couteuse : cargos x compositions x locomotives, une fois par
   * annee. Le catalogue complet mesurait 21 492 opcodes (0,008 % du budget de partie) ; cette
   * table supprime ensuite toute boucle moteur du chemin OpexLineEconomics, appele pour chaque
   * paire ville/industrie. La cle est le nombre de wagons, donc la selection voit bien la charge
   * reelle, pas une rame fictive de cinq wagons.
   *
   * La dichotomie est ecrite ici, plutot que par les appels imbriques OpexRailCruiseSpeed(),
   * OpexRailForce() et OpexRailResistance(). A 12 tuiles, au plus 23 wagons et 16 iterations par
   * moteur, les appels Squirrel faisaient monter ce seul cache a 1,12 M opcodes/an au smoke 42,
   * soit 52 fois les 21 492 du catalogue mesure. Les memes equations, deroulees sans fermeture ni
   * appel, gardent le cout annualise et mesurable par `cat_rail`, sans payer ce facteur 52.
   *
   * Les profils sont tries par vitesse decroissante avant ce cache. Si le premier soutient son
   * plafond, un moteur dont le plafond est inferieur ne peut mathematiquement ni le depasser ni
   * l'egaler : il est saute. Les seuls ex aequo possibles (meme plafond de wagon ou de moteur)
   * restent evalues pour conserver le departage acceleration, cout annuel, capital. C'est une
   * equivalence, pas un echantillonnage : si le plus rapide ne soutient pas son plafond, tous les
   * moteurs sont de nouveau evalues. Le smoke 42 mesure apres ce garde 175 768 opcodes en 1970,
   * soit 0,066 % du meme budget ou 21 492 valaient 0,008 % : c'est un cout annuel borne et non
   * le million repete qui aurait rendu le catalogue disproportionne. */
  local maxWagons = OpexRailNominalMaxWagons(catalog.platformLength);
  if (maxWagons < 1 || catalog.railLocos.len() == 0) return;
  for (local i = 1; i < catalog.railLocos.len(); i++) {
    yield null; // PO01C_CHECKPOINT
    local current = catalog.railLocos[i];
    local j = i - 1;
    while (j >= 0 && catalog.railLocos[j].speed < current.speed) {
    yield null; // PO01C_CHECKPOINT
      catalog.railLocos[j + 1] = catalog.railLocos[j];
      j--;
    }
    catalog.railLocos[j + 1] = current;
  }
  foreach (cargo, wagon in catalog.wagonByCargo) {
    yield null; // PO01C_CHECKPOINT
    local choices = [];
    for (local wagons = 1; wagons <= maxWagons; wagons++) {
    yield null; // PO01C_CHECKPOINT
      local best = null;
      local bestSpeed = -1;
      local bestAcceleration = -1;
      local topCeiling = catalog.railLocos[0].speed;
      if (wagon.speed > 0 && wagon.speed < topCeiling) topCeiling = wagon.speed;
      local topSustained = false;
      foreach (loco in catalog.railLocos) {
    yield null; // PO01C_CHECKPOINT
        if (topSustained && loco.speed < topCeiling) continue;
        local ceiling = loco.speed;
        if (wagon.speed > 0 && wagon.speed < ceiling) ceiling = wagon.speed;
        local totalWeight = loco.weight + wagons * wagon.fullWeight;
        local parts = 1 + wagons;
        local airDrag = 2048 / loco.speed;
        if (airDrag < 1) airDrag = 1;
        if (airDrag > 192) airDrag = 192;
        local airFactor = 14 * airDrag * (1 + (3 * parts) / 20.0) / 1000.0;
        local low = 0;
        local high = ceiling;
        while (low < high) {
    yield null; // PO01C_CHECKPOINT
          local middle = (low + high + 1) / 2;
          local powerForce = (loco.power * 746 * 18) / (middle * 5);
          local tractiveForce = loco.tractiveEffort * 1000;
          local force = powerForce < tractiveForce ? powerForce : tractiveForce;
          local rolling = 15 * (512 + middle) / 512;
          local resistance = totalWeight * (10 + rolling) + airFactor * middle * middle;
          if (force > resistance) low = middle;
          else high = middle - 1;
        }
        local cruise = low;
        if (cruise < 1) continue;
        if (loco.id == catalog.railLocos[0].id && cruise == topCeiling) topSustained = true;
        local halfSpeed = cruise / 2;
        if (halfSpeed < 1) halfSpeed = 1;
        local powerForce = (loco.power * 746 * 18) / (halfSpeed * 5);
        local tractiveForce = loco.tractiveEffort * 1000;
        local force = powerForce < tractiveForce ? powerForce : tractiveForce;
        local rolling = 15 * (512 + halfSpeed) / 512;
        local resistance = totalWeight * (10 + rolling) + airFactor * halfSpeed * halfSpeed;
        local acceleration = force > resistance ? (force - resistance) / (totalWeight * 4) : 0;
        /* Regle de selection, dans cet ordre : vitesse soutenable de la rame pleine, acceleration
         * a mi-vitesse (donc effort de traction et puissance), cout annuel, puis capital. Les deux
         * derniers ne servent qu'a departager deux locomotives que la physique rend equivalentes. */
        if (best == null || cruise > bestSpeed ||
            (cruise == bestSpeed && acceleration > bestAcceleration) ||
            (cruise == bestSpeed && acceleration == bestAcceleration && loco.runningCost < best.runningCost) ||
            (cruise == bestSpeed && acceleration == bestAcceleration && loco.runningCost == best.runningCost &&
             loco.price < best.price)) {
          best = loco;
          bestSpeed = cruise;
          bestAcceleration = acceleration;
        }
      }
      choices.append(best);
    }
    catalog.locoByCargoWagons.rawset(cargo, choices);
  }
  if (EQUIPMENT_ROI_PROBE) {
    foreach (cargo, wagons in catalog.wagonChoicesByCargo) {
    yield null; // PO01C_CHECKPOINT
      if (!(cargo in catalog.wagonByCargo) || !(cargo in catalog.locoByCargoWagons)) continue;
      local selectedId = catalog.wagonByCargo[cargo].id;
      foreach (wagon in wagons) {
    yield null; // PO01C_CHECKPOINT
        wagon.m3LocoChoices <- (wagon.id == selectedId)
            ? catalog.locoByCargoWagons[cargo]
            : OpexM3RailLocoChoices(catalog.railLocos, wagon, maxWagons);
      }
    }
  }
}

function OpexPO01CTowns(catalog)
{
  catalog.towns = [];
  catalog.townAcceptors = {};
  local list = AITownList();
  for (local t = list.Begin(); !list.IsEnd(); t = list.Next()) {
    yield null; // PO01C_CHECKPOINT
    local townMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    local tile = AITown.GetLocation(t);
    local pop = AITown.GetPopulation(t);
    local houses = AITown.GetHouseCount(t);
    local townObj = {
      id = t,
      tile = tile,
      pop = pop,
      houses = houses,
    };
    catalog.towns.append(townObj);

    /* Indexation des marchandises complexes et cargos urbains acceptes par la ville (Goods, Food, Mail, etc.) */
    foreach (cargo in catalog.cargos) {
    yield null; // PO01C_CHECKPOINT
      if (cargo == catalog.paxCargo) continue;
      local acceptance = AITile.GetCargoAcceptance(tile, cargo, 2, 2, catalog.railCoverage > 0 ? catalog.railCoverage : 4);
      if (acceptance >= 8 || (pop >= 300 && AICargo.HasCargoClass(cargo, AICargo.CC_EXPRESS))) {
        if (!(cargo in catalog.townAcceptors)) catalog.townAcceptors.rawset(cargo, []);
        catalog.townAcceptors[cargo].append(townObj);
      }
    }
    if (townMark != null) OpexSpanAgg("catalog.town", townMark);
  }
  /* Hors de la boucle : au defaut, un seul test par rafraichissement (identite des opcodes). */

}

function OpexPO01CIndustries(catalog)
{
  catalog.industries = [];
  catalog.producers = {};
  catalog.acceptors = {};

  local list = AIIndustryList();
  for (local i = list.Begin(); !list.IsEnd(); i = list.Next()) {
    yield null; // PO01C_CHECKPOINT
    if (!AIIndustry.IsValidIndustry(i)) continue;
    local type = AIIndustry.GetIndustryType(i);
    if (!AIIndustryType.IsValidIndustryType(type)) continue;
    catalog.industries.append({ id = i, tile = AIIndustry.GetLocation(i), type = type });
  }

  /* Les cargos produits/acceptes se lisent sur le TYPE d'industrie, pas sur l'instance
   * (AIIndustry.IsCargoProduced n'existe pas). On memorise par type : il y a une poignee de
   * types pour des dizaines d'industries, donc les listes ne sont lues qu'une fois chacune. */
  local producedByType = {};
  local acceptedByType = {};
  for (local k = 0; k < catalog.industries.len(); k++) {
    yield null; // PO01C_CHECKPOINT
    local industryMark = PROBE_SPAN_TRACE ? OpexOpsMeasureBegin() : null;
    local type = catalog.industries[k].type;
    if (!(type in producedByType)) {
      local prodList = AIIndustryType.IsValidIndustryType(type) ? AIIndustryType.GetProducedCargo(type) : null;
      local accList = AIIndustryType.IsValidIndustryType(type) ? AIIndustryType.GetAcceptedCargo(type) : null;
      producedByType.rawset(type, catalog._cargoArray(prodList));
      acceptedByType.rawset(type, catalog._cargoArray(accList));
    }
    local isTransformer = (producedByType[type].len() > 0 && acceptedByType[type].len() > 0);
    catalog.industries[k].isTransformer <- isTransformer;
    foreach (cargo in producedByType[type]) {
    yield null; // PO01C_CHECKPOINT
      if (!(cargo in catalog.producers)) catalog.producers.rawset(cargo, []);
      catalog.producers[cargo].append(k);
    }
    foreach (cargo in acceptedByType[type]) {
    yield null; // PO01C_CHECKPOINT
      if (!(cargo in catalog.acceptors)) catalog.acceptors.rawset(cargo, []);
      catalog.acceptors[cargo].append(k);
    }
    if (industryMark != null) OpexSpanAgg("catalog.industry", industryMark);
  }
}

function OpexPO01CAir(catalog)
{
  catalog.airport = null;
  catalog.plane = null;
  catalog.airCombos = [];
  catalog.airPlaneChoicesByAirport = {};
  if (catalog.paxCargo < 0) return;
  /* V166 : mode AIR coupe = catalogue vide, le meme chemin que sans appareil disponible. */
  if (!MODE_AIR) return;

  local airportLargeTypes = [
    { type = AIAirport.AT_INTERNATIONAL, allowBig = true, name = "INTERNATIONAL" },
    { type = AIAirport.AT_METROPOLITAN, allowBig = true, name = "METROPOLITAN" },
    { type = AIAirport.AT_LARGE, allowBig = true, name = "LARGE" },
  ];
  local airportSmallTypes = [
    { type = AIAirport.AT_COMMUTER, allowBig = false, name = "COMMUTER" },
    { type = AIAirport.AT_SMALL, allowBig = false, name = "SMALL" },
  ];

  local engines = AIEngineList(AIVehicle.VT_AIR);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  local keepPlaneChoices = true;

  // 1. Combo Grand Aeroport + Avion compatible
  foreach (choice in airportLargeTypes) {
    yield null; // PO01C_CHECKPOINT
    if (!AIAirport.IsValidAirportType(choice.type)) continue;
    local best = null;
    local probeChoices = [];
    for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    yield null; // PO01C_CHECKPOINT
      if (!AIEngine.CanRefitCargo(e, catalog.paxCargo)) continue;
      local planeType = AIEngine.GetPlaneType(e);
      if (planeType != AIAirport.PT_SMALL_PLANE && planeType != AIAirport.PT_BIG_PLANE) continue;
      local capacity = AIEngine.GetCapacity(e);
      local speed = AIEngine.GetMaxSpeed(e);
      if (capacity <= 0) continue;
      local isBig = (planeType == AIAirport.PT_BIG_PLANE);
      local bestIsBig = (best != null && best.isBig);
      local replaces = best == null || (isBig && !bestIsBig) ||
          (isBig == bestIsBig && (capacity > best.capacity || (capacity == best.capacity && speed > best.speed)));
      if (!replaces && !keepPlaneChoices) continue;
      local entry = {
        id = e, defaultCargo = AIEngine.GetCargoType(e), capacity = capacity, speed = speed,
        price = AIEngine.GetPrice(e), runningCost = AIEngine.GetRunningCost(e),
        maxOrderDistance = AIEngine.GetMaximumOrderDistance(e), planeType = planeType, isBig = isBig,
        ageYears = AIEngine.GetMaxAge(e) / 365, mailCapacity = -1,
      };
      if (keepPlaneChoices) probeChoices.append(entry);
      if (replaces) best = entry;
    }
    if (keepPlaneChoices && probeChoices.len() > 0) {
      catalog.airPlaneChoicesByAirport.rawset(choice.type, probeChoices);
    }
    if (best != null) {
      local ap = {
        type = choice.type,
        kind = "large",
        name = choice.name,
        allowBig = true,
        width = AIAirport.GetAirportWidth(choice.type),
        height = AIAirport.GetAirportHeight(choice.type),
        coverage = AIAirport.GetAirportCoverageRadius(choice.type),
        price = AIAirport.GetPrice(choice.type),
        maintenance = AIAirport.GetMonthlyMaintenanceCost(choice.type),
      };
      catalog.airCombos.append({ kind = "large", airport = ap, plane = best });
      if (catalog.airport == null) {
        catalog.airport = ap;
        catalog.plane = best;
      }
    }
  }

  // 2. Combo Petit Aeroport + Petit Avion (strictement PT_SMALL_PLANE)
  foreach (choice in airportSmallTypes) {
    yield null; // PO01C_CHECKPOINT
    if (!AIAirport.IsValidAirportType(choice.type)) continue;
    local best = null;
    local probeChoices = [];
    for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    yield null; // PO01C_CHECKPOINT
      if (!AIEngine.CanRefitCargo(e, catalog.paxCargo)) continue;
      local planeType = AIEngine.GetPlaneType(e);
      // Règle d'or : les gros avions ne vont JAMAIS dans les petits aeroports
      if (planeType != AIAirport.PT_SMALL_PLANE) continue;
      local capacity = AIEngine.GetCapacity(e);
      local speed = AIEngine.GetMaxSpeed(e);
      if (capacity <= 0) continue;
      local replaces = best == null || capacity > best.capacity ||
          (capacity == best.capacity && speed > best.speed);
      if (!replaces && !keepPlaneChoices) continue;
      local entry = {
        id = e, defaultCargo = AIEngine.GetCargoType(e), capacity = capacity, speed = speed,
        price = AIEngine.GetPrice(e), runningCost = AIEngine.GetRunningCost(e),
        maxOrderDistance = AIEngine.GetMaximumOrderDistance(e), planeType = planeType, isBig = false,
        ageYears = AIEngine.GetMaxAge(e) / 365, mailCapacity = -1,
      };
      if (keepPlaneChoices) probeChoices.append(entry);
      if (replaces) best = entry;
    }
    if (keepPlaneChoices && probeChoices.len() > 0) {
      catalog.airPlaneChoicesByAirport.rawset(choice.type, probeChoices);
    }
    if (best != null) {
      local ap = {
        type = choice.type,
        kind = "small",
        name = choice.name,
        allowBig = false,
        width = AIAirport.GetAirportWidth(choice.type),
        height = AIAirport.GetAirportHeight(choice.type),
        coverage = AIAirport.GetAirportCoverageRadius(choice.type),
        price = AIAirport.GetPrice(choice.type),
        maintenance = AIAirport.GetMonthlyMaintenanceCost(choice.type),
      };
      catalog.airCombos.append({ kind = "small", airport = ap, plane = best });
      if (catalog.airport == null) {
        catalog.airport = ap;
        catalog.plane = best;
      }
    }
  }
  AILog.Info("_refreshAir: combos=" + catalog.airCombos.len()
    + " airport=" + (catalog.airport != null ? "YES" : "NULL")
    + " plane=" + (catalog.plane != null ? "YES" : "NULL"));
}

function OpexPO01CWater(catalog)
{
  catalog.ships = [];
  catalog.maxShipPrice = 0;
  catalog.costDock = AIMarine.GetBuildCost(AIMarine.BT_DOCK);
  catalog.costWaterDepot = AIMarine.GetBuildCost(AIMarine.BT_DEPOT);
  if (catalog.paxCargo < 0) return;
  /* V166 : mode EAU coupe = aucune coque au catalogue. */
  if (!MODE_WATER) return;
  local engines = AIEngineList(AIVehicle.VT_WATER);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    yield null; // PO01C_CHECKPOINT
    if (!AIEngine.CanRefitCargo(e, catalog.paxCargo)) continue;
    local capacity = AIEngine.GetCapacity(e);
    local speed = AIEngine.GetMaxSpeed(e);
    local ship = { id = e, capacity = capacity, speed = speed, price = AIEngine.GetPrice(e),
                   runningCost = AIEngine.GetRunningCost(e),
                   maxOrderDistance = AIEngine.GetMaximumOrderDistance(e) };
    catalog.ships.append(ship);
    if (ship.price > catalog.maxShipPrice) catalog.maxShipPrice = ship.price;
  }
}

function OpexPO01CRoad(catalog)
{
  catalog.roadType = -1;
  catalog.roadEngineByCargo = {};
  catalog.roadEngineChoicesByCargo = {};
  catalog.maxRoadVehiclePrice = 0;
  catalog.costRoadPerTile = 0;
  catalog.costRoadBusStop = 0;
  catalog.costRoadTruckStop = 0;
  catalog.costRoadDepot = 0;
  if (!AIRoad.IsRoadTypeAvailable(AIRoad.ROADTYPE_ROAD)) return;
  catalog.roadType = AIRoad.ROADTYPE_ROAD;
  AIRoad.SetCurrentRoadType(catalog.roadType);
  catalog.costRoadPerTile = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_ROAD);
  catalog.costRoadBusStop = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_BUS_STOP);
  catalog.costRoadTruckStop = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_TRUCK_STOP);
  catalog.costRoadDepot = AIRoad.GetBuildCost(catalog.roadType, AIRoad.BT_DEPOT);

  /* Deux passes plutot qu'une boucle imbriquee sur AIEngineList : les predicats chers
   * (IsBuildable, CanRunOnRoad, HasPowerOnRoad, IsArticulated) sont evalues UNE fois par moteur,
   * et seul CanRefitCargo -- le seul qui depende du cargo -- est repaye pour chaque paire. Sur le
   * parc mesure (12 a 22 moteurs routiers en 20 ans, results/catalogue_churn.json) et une douzaine de
   * cargos, cela reste tres en dessous du budget annuel du catalogue. */
  local usable = [];
  local engines = AIEngineList(AIVehicle.VT_ROAD);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  engines.Valuate(AIEngine.IsArticulated);
  engines.KeepValue(0);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    yield null; // PO01C_CHECKPOINT
    if (!AIEngine.CanRunOnRoad(e, catalog.roadType)) continue;
    if (!AIEngine.HasPowerOnRoad(e, catalog.roadType)) continue;
    local capacity = AIEngine.GetCapacity(e);
    if (capacity <= 0) continue;
    usable.append({
      id = e, defaultCargo = AIEngine.GetCargoType(e), capacity = capacity,
      speed = AIEngine.GetMaxSpeed(e), price = AIEngine.GetPrice(e),
      runningCost = AIEngine.GetRunningCost(e),
      /* GetMaxAge rend des jours, comme pour la locomotive. */
      ageYears = AIEngine.GetMaxAge(e) / 365,
    });
  }

  foreach (cargo in catalog.cargos) {
    yield null; // PO01C_CHECKPOINT
    local best = null;
    local probeChoices = [];
    foreach (engine in usable) {
    yield null; // PO01C_CHECKPOINT
      if (engine.defaultCargo != cargo && !AIEngine.CanRefitCargo(engine.id, cargo)) continue;
      if (EQUIPMENT_ROI_PROBE) probeChoices.append(engine);
      /* capacity est celle du cargo D'ORIGINE : apres refit elle peut changer (le GRF decide).
       * C'est une approximation assumee pour le CLASSEMENT ; la valeur qui sert au dimensionnement
       * reel est relue depuis le depot par GetBuildWithRefitCapacity dans builder_road.nut. */
      if (best == null || engine.capacity > best.capacity ||
          (engine.capacity == best.capacity && engine.speed > best.speed)) {
        best = engine;
      }
    }
    if (best == null) continue;
    catalog.roadEngineByCargo.rawset(cargo, best);
    if (EQUIPMENT_ROI_PROBE) catalog.roadEngineChoicesByCargo.rawset(cargo, probeChoices);
    if (best.price > catalog.maxRoadVehiclePrice) catalog.maxRoadVehiclePrice = best.price;
  }
}

function OpexPO01CWaterFindConnection(po01dResult, siteA, siteB)
{
  local ax = AIMap.GetTileX(siteA.dock);
  local ay = AIMap.GetTileY(siteA.dock);
  local bx = AIMap.GetTileX(siteB.dock);
  local by = AIMap.GetTileY(siteB.dock);
  local minX = max(0, min(ax, bx) - WATER_BFS_MARGIN);
  local minY = max(0, min(ay, by) - WATER_BFS_MARGIN);
  local maxX = min(AIMap.GetMapSizeX() - 1, max(ax, bx) + WATER_BFS_MARGIN);
  local maxY = min(AIMap.GetMapSizeY() - 1, max(ay, by) + WATER_BFS_MARGIN);
  local queue = [];
  local seen = {};
  foreach (water in siteA.waterTiles) {
    yield null; // PO01C_CHECKPOINT
 queue.append(water); seen.rawset(water, 0); }
  local head = 0;
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < queue.len() && head < WATER_BFS_MAX_NODES) {
    yield null; // PO01C_CHECKPOINT

    local current = queue[head++];
    local distance = seen[current];
    if (OpexWaterContains(siteB.waterTiles, current)) { po01dResult.value = distance; return; }
    local x = AIMap.GetTileX(current);
    local y = AIMap.GetTileY(current);
    foreach (offset in offsets) {
    yield null; // PO01C_CHECKPOINT

      local nx = x + offset[0];
      local ny = y + offset[1];
      if (nx < minX || nx > maxX || ny < minY || ny > maxY) continue;
      local next = AIMap.GetTileIndex(nx, ny);
      if (!AITile.IsWaterTile(next)) continue;
      if (!AIMarine.AreWaterTilesConnected(current, next)) continue;
      if (!(next in seen)) { seen.rawset(next, distance + 1); queue.append(next); }
    }
  }
  { po01dResult.value = -1; return; }
}

function OpexPO01CAirFindSite(po01dResult, town, airport, probes, requiredSlotTownId = -1)
{
  if (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(town)) { po01dResult.value = null; return; }
  if (C60_TOWN_RATING_PROBE) {
    OpexC60ObserveTownRating("air", "find_site", town.id);
  }
  if (probes != null && ("stationLimitedTowns" in probes)
      && (town.id in probes.stationLimitedTowns)) { po01dResult.value = null; return; }
  local key = town.id + "_" + airport.type;
  /* C83 cible : le cache historique est indexe par ville commerciale/type.
   * Une course au slot exige en plus ClosestTown(anchor)==ville cible ; ne pas
   * reutiliser ni ecrire ce cache dans ce chemin rare. */
  local useSiteCache = AIR_SITE_CACHE_ENABLED && requiredSlotTownId < 0;
  if (useSiteCache && (key in AIR_SITE_CACHE)) {
    local cachedAnchor = AIR_SITE_CACHE[key];
    if (cachedAnchor == null) {
      { po01dResult.value = null; return; }
    }
    local offX = airport.width - 1;
    local offY = airport.height - 1;
    local mapX = AIMap.GetMapSizeX();
    local mapY = AIMap.GetMapSizeY();
    local ax = AIMap.GetTileX(cachedAnchor);
    local ay = AIMap.GetTileY(cachedAnchor);
    if (ax + offX < mapX && ay + offY < mapY) {
      local c4 = cachedAnchor + AIMap.GetTileIndex(offX, offY);
      if (!AITile.IsWaterTile(cachedAnchor) && !AITile.IsCoastTile(cachedAnchor) && !AITile.IsWaterTile(c4)
          && !AITile.IsCoastTile(c4) && AIAirport.GetNearestTown(cachedAnchor, airport.type) == town.id && (OpexAirFootprintCheapOk(cachedAnchor, airport))
          && (OpexAirSiteHasCatchment(cachedAnchor, airport, OpexAirDemandPaxCargo()))) {
        local ok = false;
        {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              AIR_SITE_CACHE[key] <- null;
              { po01dResult.value = null; return; }
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(cachedAnchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       OpexAirCanLevelFootprint(cachedAnchor, airport, town.id)) {
              /* G7Ãƒâ€šÃ‚Â§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              ok = true;
            }
          }
        }
        if ("tested" in probes) probes.tested++;
        if (ok) { po01dResult.value = { town = town, anchor = cachedAnchor }; return; }
      }
    }
    delete AIR_SITE_CACHE[key];
  }

  /* C96 reste prioritaire. Le chemin historique V94 est conserve (V237) ; au
   * defaut il etait deja court-circuite par C96. Son comparateur est retire (V239). */
  {
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirFindSiteCatchmentListed(po01dBox, town, airport, probes, requiredSlotTownId, key, useSiteCache);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    po01dResult.value = po01dBox.value.site; return;
  }

  /* Le budget global reste borne, mais il est partage entre les villes encore
   * a sonder. Elargir le vivier ne peut donc pas multiplier sans borne les
   * AITestMode : davantage de villes donne moins de sondes par ville. */
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    yield null; // PO01C_CHECKPOINT

    for (local dx = -r; dx <= r; dx++) {
    yield null; // PO01C_CHECKPOINT

      for (local dy = -r; dy <= r; dy++) {
    yield null; // PO01C_CHECKPOINT

        if (abs(dx) != r && abs(dy) != r) continue;
        local anchor = town.tile + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(anchor)) continue;
        local ax = AIMap.GetTileX(anchor);
        local ay = AIMap.GetTileY(anchor);
        if (ax + offX >= mapX || ay + offY >= mapY) continue;
        if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
        if (AITile.IsWaterTile(anchor) || AITile.IsCoastTile(anchor)) continue;
        local c4 = anchor + AIMap.GetTileIndex(offX, offY);
        if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;
        if (requiredSlotTownId >= 0 && AITile.GetClosestTown(anchor) != requiredSlotTownId) continue;
        if (AIAirport.GetNearestTown(anchor, airport.type) != town.id) continue;

        {
          /* Eau/riviere/cote sur toute l'emprise, C4, et IsBuildableRectangle : sans AITestMode.
           * La sonde ci-dessous ne tourne plus que sur un hit cheap. */
          if (!OpexAirFootprintCheapOk(anchor, airport)) {
            if ("cheapSkip" in probes) probes.cheapSkip++;
            continue;
          }
        }

        if (used >= allowance) {
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          if (useSiteCache) AIR_SITE_CACHE[key] <- null;
          { po01dResult.value = null; return; }
        }
        if (probes.left <= 0) {
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          { po01dResult.value = null; return; }
        }

        local ok = false;
        {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              if (useSiteCache) AIR_SITE_CACHE[key] <- null;
              { po01dResult.value = null; return; }
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(anchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       execLevels < 3) {
              execLevels++;
              /* G7Ãƒâ€šÃ‚Â§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              if (OpexAirCanLevelFootprint(anchor, airport, town.id)) {
                ok = true;
              }
            }
          }
        }
        used++;
        probes.left--;
        if ("tested" in probes) probes.tested++;
        if (ok) {
          if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
          local found = { town = town, anchor = anchor };
          { po01dResult.value = found; return; }
        }
      }
    }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  { po01dResult.value = null; return; }
}

function OpexPO01CAirFindSiteListed(po01dResult, town, airport, probes, requiredSlotTownId, key, useSiteCache)
{
  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    yield null; // PO01C_CHECKPOINT

    local ring = OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY);
    if (ring == null) continue;
    foreach (anchor, anchorX in ring) {
    yield null; // PO01C_CHECKPOINT

      if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
      local c4 = anchor + AIMap.GetTileIndex(offX, offY);
      if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;

      {
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
          continue;
        }
      }

      if (used >= allowance) {
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        if (useSiteCache) AIR_SITE_CACHE[key] <- null;
        { po01dResult.value = { site = null, used = used, execLevels = execLevels, allowance = allowance }; return; }
      }
      if (probes.left <= 0) {
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        { po01dResult.value = { site = null, used = used, execLevels = execLevels, allowance = allowance }; return; }
      }

      local ok = false;
      {
        {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        }
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            { po01dResult.value = { site = null, used = used, execLevels = execLevels, allowance = allowance }; return; }
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
              OpexAirFootprintIsFlat(anchor, airport)) {
            ok = true;
          } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                      err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                     execLevels < 3) {
            execLevels++;
            if (OpexAirCanLevelFootprint(anchor, airport, town.id)) {
              ok = true;
            }
          }
        }
      }
      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (ok) {
        if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
        { po01dResult.value = {
          site = { town = town, anchor = anchor },
          used = used, execLevels = execLevels, allowance = allowance
        }; return; }
      }
    }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  { po01dResult.value = { site = null, used = used, execLevels = execLevels, allowance = allowance }; return; }
}

function OpexPO01CAirFindSiteCatchmentListed(po01dResult, town, airport, probes, requiredSlotTownId, key, useSiteCache)
{
  local paxCargo = OpexAirDemandPaxCargo();
  if (paxCargo < 0) {
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirFindSiteListed(po01dBox, town, airport, probes, requiredSlotTownId, key, useSiteCache);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    po01dResult.value = po01dBox.value; return;
  }

  local townsLeft = probes.townsLeft > 0 ? probes.townsLeft : 1;
  local allowance = (probes.left + townsLeft - 1) / townsLeft;
  probes.townsLeft--;
  local used = 0;
  local execLevels = 0;
  local w = airport.width;
  local h = airport.height;
  local offX = w - 1;
  local offY = h - 1;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local townX = AIMap.GetTileX(town.tile);
  local townY = AIMap.GetTileY(town.tile);
  local best = null;
  local bestScore = -1;
  local firstAnchor = -1;
  local firstScore = -1;
  local valid = 0;
  local firstValidRing = -1;
  local bestRing = -1;

  for (local r = 4; r <= AIR_SITE_RADIUS; r++) {
    yield null; // PO01C_CHECKPOINT

    if (firstValidRing >= 0 && r > firstValidRing + C96_AIR_SITE_EXTRA_RINGS) break;
    local ring = OpexAirFindSiteRing(town, airport, requiredSlotTownId, townX, townY, r, offX, offY, mapX, mapY);
    if (ring == null) continue;
    foreach (anchor, anchorX in ring) {
    yield null; // PO01C_CHECKPOINT

      if (OpexAirDistanceToRect(town.tile, anchor, w, h) > 25) continue;
      local c4 = anchor + AIMap.GetTileIndex(offX, offY);
      if (AITile.IsWaterTile(c4) || AITile.IsCoastTile(c4)) continue;

      {
        if (!OpexAirFootprintCheapOk(anchor, airport)) {
          if ("cheapSkip" in probes) probes.cheapSkip++;
          continue;
        }
      }

      if (used >= allowance || probes.left <= 0) {
        if (best != null) {
          OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
              valid, firstValidRing, bestRing, used);
          if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
          { po01dResult.value = { site = best, used = used, execLevels = execLevels, allowance = allowance }; return; }
        }
        OpexAirC78NoteNoSite(probes, "no_site_budget");
        if (useSiteCache && used >= allowance) AIR_SITE_CACHE[key] <- null;
        { po01dResult.value = { site = null, used = used, execLevels = execLevels, allowance = allowance }; return; }
      }

      local ok = false;
      {
        {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
        }
        if (!ok) {
          local err = AIError.GetLastError();
          if (OpexAirRememberTownStationLimit(probes, town, err)) {
            if (useSiteCache) AIR_SITE_CACHE[key] <- null;
            { po01dResult.value = { site = null, used = used, execLevels = execLevels, allowance = allowance }; return; }
          } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
              OpexAirFootprintIsFlat(anchor, airport)) {
            ok = true;
          } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                      err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                     execLevels < 3) {
            execLevels++;
            if (OpexAirCanLevelFootprint(anchor, airport, town.id)) ok = true;
          }
        }
      }

      used++;
      probes.left--;
      if ("tested" in probes) probes.tested++;
      if (!ok) continue;

      if (!OpexAirSiteHasCatchment(anchor, airport, paxCargo)) {
        if ("deadCatchment" in probes) probes.deadCatchment++;
        continue;
      }
      if (firstValidRing < 0) firstValidRing = r;
      local score = OpexAirC96SiteCatchmentScore(anchor, airport, paxCargo);
      valid++;
      if (firstAnchor < 0) {
        firstAnchor = anchor;
        firstScore = score;
      }
      if (best == null || score > bestScore) {
        best = { town = town, anchor = anchor };
        bestScore = score;
        bestRing = r;
      }
      if (valid >= C96_AIR_SITE_MAX_VALID) {
        OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
            valid, firstValidRing, bestRing, used);
        if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
        { po01dResult.value = { site = best, used = used, execLevels = execLevels, allowance = allowance }; return; }
      }
    }
  }

  if (best != null) {
    OpexAirC96LogChoice(town, airport, firstAnchor, firstScore, best, bestScore,
        valid, firstValidRing, bestRing, used);
    if (useSiteCache) AIR_SITE_CACHE[key] <- best.anchor;
    { po01dResult.value = { site = best, used = used, execLevels = execLevels, allowance = allowance }; return; }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) AIR_SITE_CACHE[key] <- null;
  { po01dResult.value = { site = null, used = used, execLevels = execLevels, allowance = allowance }; return; }
}

function OpexPO01CAirPlans(po01dResult, catalog, lines = null, maxCapital = 0, projects = null, abandoned = null,
                      paxBand = PAX_BAND_ALL, targetTownId = -1,
                      resumeState = null, opsBudget = 0, deadlineTick = 0)
{
  local t0_all = AIController.GetTick();
  local l0_all = AIController.GetOpsTillSuspend();
  local _calcDeltaOps = OpexAirCalcDeltaOps;
  local ctx = {
    catalog = catalog,
    lines = lines,
    maxCapital = maxCapital,
    projects = projects,
    abandoned = abandoned,
    paxBand = paxBand,
    targetTownId = targetTownId,
    resumeState = resumeState,
    opsBudget = opsBudget,
    deadlineTick = deadlineTick,
    t0_all = t0_all,
    l0_all = l0_all,
    sliced = resumeState != null,
    combos = null,
    servedDiag = null,
    hubIndex = null,
    c83TopTownIds = null,
    towns = null,
    limit = 0,
    c78Year = -1,
    c78Gen = false,
    stationLimitedTowns = null,
    bestPlan = null,
    infrastructureMaintenance = false,
    comboStart = 0,
    perfOpsSites = 0,
    perfOpsEval = 0,
    perfProbesCount = 0,
    perfCheapSkip = 0,
    perfSitesFound = 0,
    sites = [],
    hubs = [],
    air0310HubRestored = false,
    air0310HubSkip = null,
    fp2 = null,
  };

  local spPlans = PROBE_SPAN_TRACE ? OpexSpanBegin("air.plans") : null;
  local prepared = OpexAirPlansStepPrepare(ctx);
  if (!prepared) {
    if (spPlans != null) OpexSpanEnd(spPlans);
    { po01dResult.value = ctx.bestPlan; return; }
  }

  if (FRONT_PAX2_BOUNDED_OVERLAP > 0 && paxBand == PAX_BAND_ALL
      && catalog != null && catalog.bounds != null) {
    if (resumeState != null && ("frontPax2Bounded" in resumeState)) {
      ctx.fp2 = resumeState.frontPax2Bounded;
    } else {
      ctx.fp2 = OpexFP2NewShortlist(catalog.bounds);
      if (resumeState != null) resumeState.frontPax2Bounded <- ctx.fp2;
    }
  }

  for (local comboIndex = ctx.comboStart; comboIndex < ctx.combos.len(); comboIndex++) {
    yield null; // PO01C_CHECKPOINT

    local combo = ctx.combos[comboIndex];
    local airport = combo.airport;
    local plane = combo.plane;
    local minDist = (plane.speed >= 400) ? 32 : 30;
    local resumingCombo = ctx.sliced && ctx.resumeState.combo == comboIndex && ctx.resumeState.sites != null;

    local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirPlansStepFindSites(po01dBox, ctx, comboIndex, combo, airport, plane, resumingCombo);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    local sitesOk = po01dBox.value;
    if (!sitesOk) {
      if (spPlans != null) OpexSpanEnd(spPlans);
      { po01dResult.value = ctx.bestPlan; return; }
    }

    local pairsOk = OpexAirPlansStepNewPairs(ctx, comboIndex, combo, airport, plane,
        minDist, resumingCombo);
    if (!pairsOk) {
      if (spPlans != null) OpexSpanEnd(spPlans);
      { po01dResult.value = ctx.bestPlan; return; }
    }

    {
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirPlansHubDiscoveryPhase(po01dBox, ctx, comboIndex, combo, airport, plane);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    }

    local c56PlansBefore = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_site", "-");
    local tHubEval0 = AIController.GetTick();
    local lHubEval0 = AIController.GetOpsTillSuspend();
    local spHubSite = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_site") : null;
    if (!OpexAirPlansHubToSitePhase(ctx, combo, airport, plane)) {
      if (spHubSite != null) OpexSpanEnd(spHubSite);
      if (spPlans != null) OpexSpanEnd(spPlans);
      { po01dResult.value = ctx.bestPlan; return; }
    }
    if (spHubSite != null) OpexSpanEnd(spHubSite);
    local c56PlansMid = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_site", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len() + " admitted=" + (c56PlansMid - c56PlansBefore));
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_hub", "-");
    local spHubHub = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_hub") : null;
    local hubsOk = OpexAirPlansHubToHub(ctx, combo, airport, plane);
    if (spHubHub != null) OpexSpanEnd(spHubHub);
    if (!hubsOk) {
      if (spPlans != null) OpexSpanEnd(spPlans);
      { po01dResult.value = ctx.bestPlan; return; }
    }
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_hub", "-",
        "hubs=" + ctx.hubs.len() + " admitted=" + (((ctx.projects != null) ? ctx.projects.len() : 0) - c56PlansMid));
    ctx.perfOpsEval += _calcDeltaOps(tHubEval0, lHubEval0);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hubs", "-", "hubs=" + ctx.hubs.len());

    local nextCombo = OpexAirPlansCompleteCombo(ctx, comboIndex, combo);
    if (nextCombo < 0) break;
    comboIndex = nextCombo - 1;
  }

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_finalize", "-");
  local spFinal = PROBE_SPAN_TRACE ? OpexSpanBegin("air.finalize") : null;
  local finalPlan = OpexAirPlansFinalize(ctx);
  if (spFinal != null) OpexSpanEnd(spFinal);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_finalize", "-");
  if (spPlans != null) OpexSpanEnd(spPlans);
  { po01dResult.value = finalPlan; return; }
}

function OpexPO01CAirPlansStepFindSites(po01dResult, ctx, comboIndex, combo, airport, plane, resumingCombo)
{
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_find_sites", "-");
  local spSites = PROBE_SPAN_TRACE ? OpexSpanBegin("air.sites") : null;
  local sitesOk;
  if (V278_AIR_LAZY_SITES && OpexV278LazyEnabled(ctx)) {
    sitesOk = OpexV278LazySites(ctx, comboIndex, combo, airport, plane);
  } else {
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirPlansFindSites(po01dBox, ctx, comboIndex, combo, airport, plane, resumingCombo);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    sitesOk = po01dBox.value;
  }
  if (spSites != null) OpexSpanEnd(spSites);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_find_sites", "-",
      "combo=" + comboIndex + " sites=" + ctx.sites.len() + " probes=" + ctx.perfProbesCount);
  { po01dResult.value = sitesOk; return; }
}

function OpexPO01CAirPlansFindSites(po01dResult, ctx, comboIndex, combo, airport, plane, resumingCombo)
{
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local opsBudget = ctx.opsBudget;
  local deadlineTick = ctx.deadlineTick;
  local limit = ctx.limit;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local towns = ctx.towns;
  local lines = ctx.lines;
  local targetTownId = ctx.targetTownId;
  local servedDiag = ctx.servedDiag;
  local c83TopTownIds = ctx.c83TopTownIds;
  local c78Gen = ctx.c78Gen;
  local c78Year = ctx.c78Year;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local bestPlan = ctx.bestPlan;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  local sites = resumingCombo ? resumeState.sites : [];
  if (!resumingCombo) {
    local scanSites = sliced ? resumeState.scanSites : [];
    local probes = sliced && resumeState.scanProbes != null
        ? resumeState.scanProbes
        : {
            left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
            stationLimitedTowns = stationLimitedTowns
          };
    local scanStart = sliced ? resumeState.scanIndex : 0;
    local scanEnd = limit;
    if (V278_AIR_LAZY_SITES && ("v278ScanEnd" in ctx)) scanEnd = ctx.v278ScanEnd;
    local testedBefore = probes.tested;
    local cheapBefore = ("cheapSkip" in probes) ? probes.cheapSkip : 0;
    local foundBefore = scanSites.len();
    local tSites0 = AIController.GetTick();
    local lSites0 = AIController.GetOpsTillSuspend();
    for (local i = scanStart; i < scanEnd; i++) {
    yield null; // PO01C_CHECKPOINT

      probes.townsLeft = limit - i;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      if (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(towns[i], null, -1, ctx.catalog)) {
        /* Levier A : bridage de difficulte (niveaux 0 et 1). Niveaux 2 et 3 : zero opcode. */
      } else if (towns[i].id in stationLimitedTowns) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_station_limit", 1);
        if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_station_limit");
      } else {
        /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
         * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
         * construction aerienne sur une carte partiellement couverte. */
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        local skipServed = isServed && !c83OwnSecondSlot;
        if (skipServed) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "origin_served", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=origin_served");
        } else if (towns[i].pop < V93_AIRPORT_MIN_POP) {
          /* V93 fige : plancher minimal, grand ou petit. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_v93", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_v93");
        } else {
          local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
              ? targetTownId : -1;
          if (c78Gen && ("c78NoSite" in probes)) probes.c78NoSite = null;
          local v278Started = V278_AIR_LAZY_SITES ? AIController.GetTick() : -1;
          local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirFindSite(po01dBox, towns[i], airport, probes, c83RequiredSlotTown);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    local site = po01dBox.value;
          if (site != null) {
            if (c83OwnSecondSlot) site.c83OwnSecondSlot <- true;
            if (V278_AIR_LAZY_SITES) OpexV278RememberFoundSite(site, airport, v278Started);
            scanSites.append(site);
            if (c78Gen) {
              if (towns[i].pop < 600) {
                OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site v93=1 pop=" + towns[i].pop);
              } else {
                OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site");
              }
            }
          }
          else {
            if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "no_site", 1);
            if (c78Gen) {
              local c78Outcome = "no_site_terrain";
              if (("c78NoSite" in probes) && probes.c78NoSite != null) c78Outcome = probes.c78NoSite;
              if (c78Outcome != "no_site_slot" && OpexAirC83SlotSignalEnabled()
                  && AITown.GetAllowedNoise(towns[i].id) < 1) {
                c78Outcome = "no_site_slot";
              }
              OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=" + c78Outcome);
            }
          }
        }
      }
      if (sliced) {
        resumeState.combo = comboIndex;
        resumeState.scanIndex = i + 1;
        resumeState.scanSites = scanSites;
        resumeState.scanProbes = probes;
        local scanSliceOps = _calcDeltaOps(t0_all, l0_all);
        if ((opsBudget > 0 && scanSliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
          perfOpsSites += _calcDeltaOps(tSites0, lSites0);
          perfProbesCount += probes.tested - testedBefore;
          perfCheapSkip += (("cheapSkip" in probes) ? probes.cheapSkip : 0) - cheapBefore;
          perfSitesFound += scanSites.len() - foundBefore;
          resumeState.bestPlan = bestPlan;
          resumeState.stationLimitedTowns = stationLimitedTowns;
          resumeState.perfOpsSites = perfOpsSites;
          resumeState.perfOpsEval = perfOpsEval;
          resumeState.perfProbesCount = perfProbesCount;
          resumeState.perfCheapSkip = perfCheapSkip;
          resumeState.perfSitesFound = perfSitesFound;
          resumeState.totalOps += scanSliceOps;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          { po01dResult.value = false; return; }
        }
      }
    }
    perfOpsSites += _calcDeltaOps(tSites0, lSites0);
    if (sliced) {
      perfProbesCount += probes.tested - testedBefore;
      perfCheapSkip += (("cheapSkip" in probes) ? probes.cheapSkip : 0) - cheapBefore;
      perfSitesFound += scanSites.len() - foundBefore;
    } else {
      perfProbesCount += probes.tested;
      if ("cheapSkip" in probes) perfCheapSkip += probes.cheapSkip;
      perfSitesFound += scanSites.len();
    }

    /* C78.4 : la revalidation peut elle aussi consommer plusieurs ticks. Elle
     * reprend par index de site ; aucun site valide n'est sonde deux fois juste
     * parce qu'une tranche a rendu la main. */
    local rankableSites = sliced ? resumeState.rankSites : [];
    local rankStart = sliced ? resumeState.rankIndex : 0;
    for (local rankIndex = rankStart; rankIndex < scanSites.len(); rankIndex++) {
    yield null; // PO01C_CHECKPOINT

      local site = scanSites[rankIndex];
      if (V278_AIR_LAZY_SITES
          ? OpexV278SiteOk(site, airport, plane, stationLimitedTowns)
          : OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
        rankableSites.append(site);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("air", "site_stale_before_rank", 1);
      }
      if (sliced) {
        resumeState.combo = comboIndex;
        resumeState.rankIndex = rankIndex + 1;
        resumeState.rankSites = rankableSites;
        local rankSliceOps = _calcDeltaOps(t0_all, l0_all);
        if ((opsBudget > 0 && rankSliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
          resumeState.bestPlan = bestPlan;
          resumeState.stationLimitedTowns = stationLimitedTowns;
          resumeState.perfOpsSites = perfOpsSites;
          resumeState.perfOpsEval = perfOpsEval;
          resumeState.perfProbesCount = perfProbesCount;
          resumeState.perfCheapSkip = perfCheapSkip;
          resumeState.perfSitesFound = perfSitesFound;
          resumeState.totalOps += rankSliceOps;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          { po01dResult.value = false; return; }
        }
      }
    }
    sites = rankableSites;
    if (sliced) {
      resumeState.combo = comboIndex;
      resumeState.a = 0;
      resumeState.b = 1;
      resumeState.sites = sites;
      resumeState.scanIndex = 0;
      resumeState.scanSites = [];
      resumeState.scanProbes = null;
      resumeState.rankIndex = 0;
      resumeState.rankSites = [];
    }
  }
  /* En mode reprenable, ne pas reconstruire le meme panneau a chaque
   * tranche de paires. Outre la pollution de SIGN, AISign.BuildSign consomme
   * des opcodes et faisait de la reprise elle-meme une part majeure du cout. */
  if (!sliced || !resumingCombo) {
    OpexSign(AIMap.GetTileIndex(1, 3), "AS|S=" + sites.len() + "|A=" + airport.name);
  }

  ctx.sites = sites;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;
  { po01dResult.value = true; return; }
}

function OpexPO01CAirPlansHubDiscoveryPhase(po01dResult, ctx, comboIndex, combo, airport, plane)
{
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hubs", "-");
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_discover", "-");
    local reuseHubs = false;
    if (ctx.sliced) {
      local hubSnapAction = OpexAir0310HubSnapshotPrepare(ctx, comboIndex, airport, plane);
      OpexAir0310HubSnapshotCount(ctx, hubSnapAction);
      reuseHubs = hubSnapAction == "reuse";
    }
    if (!reuseHubs) {
      ctx.air0310HubOrphan <- [];
      local spDisc = PROBE_SPAN_TRACE ? OpexSpanBegin("air.hub_discover") : null;
      {
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirPlansDiscoverHubs(po01dBox, ctx, combo, airport, plane);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    }
      if (spDisc != null) OpexSpanEnd(spDisc);
      if (ctx.sliced) OpexAir0310HubSnapshotStore(ctx, comboIndex);
    }
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_discover", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len());
    OpexAC04ValidateHubsAtUsage(ctx);
}

function OpexPO01CAirPlansDiscoverHubs(po01dResult, ctx, combo, airport, plane)
{
  /* Bras hub : un aeroport existant, rentable et non sature (max 8 routes), plus UNE destination. */
  local hubs = [];
  local sites = ctx.sites;
  local lines = ctx.lines;
  local limit = ctx.limit;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local towns = ctx.towns;
  local targetTownId = ctx.targetTownId;
  local servedDiag = ctx.servedDiag;
  local c83TopTownIds = ctx.c83TopTownIds;
  local hubIndex = ctx.hubIndex;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  if (lines != null) {
    if (sites.len() < AIR_HUB_NEW_SITE_POOL) {
      local hubProbes = {
        left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
        stationLimitedTowns = stationLimitedTowns
      };
      local tHubSites0 = AIController.GetTick();
      local lHubSites0 = AIController.GetOpsTillSuspend();
      local hubScanEnd = limit;
      for (local i = 0; i < hubScanEnd && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
    yield null; // PO01C_CHECKPOINT

        hubProbes.townsLeft = limit - i;
        if (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(towns[i], null, -1, ctx.catalog)) continue;
        if (towns[i].id in stationLimitedTowns) {
          continue;
        }
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        if (isServed && !c83OwnSecondSlot) continue;
        /* V93 fige : plancher sanitaire commun aux types d'aeroport. */
        if (towns[i].pop < V93_AIRPORT_MIN_POP) continue;
        if (combo.kind == "small" && towns[i].pop >= 2500) continue;
        local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
            ? targetTownId : -1;
        local po01dBox = { value = null };
    local po01dChild = OpexPO01CAirFindSite(po01dBox, towns[i], airport, hubProbes, c83RequiredSlotTown);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      yield null; // PO01C_CHECKPOINT
    }
    local extraSite = po01dBox.value;
        if (extraSite != null) {
          if (OpexAC04ExtraSiteAlreadyKnown(sites, extraSite))
            continue;
          if (c83OwnSecondSlot) extraSite.c83OwnSecondSlot <- true;
          /* v93=1 seulement si le scan principal n'a pas deja retenu cette ville. */
          if (towns[i].pop < 600 && ("c78Gen" in ctx) && ctx.c78Gen) {
            local v93Already = false;
            foreach (prev in sites) {
    yield null; // PO01C_CHECKPOINT

              if (("town" in prev) && prev.town != null && ("id" in prev.town) && prev.town.id == towns[i].id) {
                v93Already = true;
                break;
              }
            }
            if (!v93Already) {
              OpexC78Log("C78_AIRTOWN", "year=" + ctx.c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=site v93=1 pop=" + towns[i].pop);
            }
          }
          sites.append(extraSite);
          ctx.perfSitesFound++;
        }
      }
      ctx.perfOpsSites += _calcDeltaOps(tHubSites0, lHubSites0);
      ctx.perfProbesCount += hubProbes.tested;
      if ("cheapSkip" in hubProbes) ctx.perfCheapSkip += hubProbes.cheapSkip;
    }
    local seenStations = {};
    foreach (line in lines) {
    yield null; // PO01C_CHECKPOINT

      if (!("mode" in line) || line.mode != "air") continue;
      if (("deadStreak" in line) && line.deadStreak >= 2) continue;
      /* L'ancre d'un hub est la tuile d'aeroport (line.stationA/B). */
      local ends = [
        { anchor = line.stationA, origin = line.originA, stationId = line.stationA },
        { anchor = line.stationB, origin = line.originB, stationId = line.stationB },
      ];
      foreach (end in ends) {
    yield null; // PO01C_CHECKPOINT

        if (!AIMap.IsValidTile(end.anchor) || !AIAirport.IsAirportTile(end.anchor)) continue;
        local existingType = AIAirport.GetAirportType(end.anchor);
        if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
        /* Resolution non ambigue : `end.stationId` est une tuile, et `IsValidStation(tuile)`
         * peut etre vrai par pure collision d'indices. On resout toujours depuis l'ancre. */
        local station = AIStation.GetStationID(end.anchor);
        if (!AIStation.IsValidStation(station) || (station in seenStations)) continue;

        local routeCount = 0;
        if (hubIndex != null) {
          if (station in hubIndex.routes) routeCount = hubIndex.routes[station];
        } else {
          foreach (other in lines) {
    yield null; // PO01C_CHECKPOINT

            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = OpexAirLineStationId(other, 0);
            local otherB = OpexAirLineStationId(other, 1);
            if (otherA == station || otherB == station) routeCount++;
          }
        }
        local maxRoutes = OpexAirAirportMaxRoutes(existingType);
        if (routeCount >= maxRoutes) continue;
        local townId = AITile.GetClosestTown(end.origin);
        if (townId < 0) continue;
        local hubTown = null;
        foreach (town in towns) {
    yield null; // PO01C_CHECKPOINT

          if (town.id == townId) { hubTown = town; break; }
        }
        if (hubTown == null) {
          hubTown = { id = townId, tile = end.origin, pop = AITown.GetPopulation(townId) };
        }
        seenStations.rawset(station, true);
        hubs.append({ town = hubTown, anchor = end.anchor, stationId = station, routes = routeCount });
        OpexAir0310NoteHubOrigin(ctx, 0);
      }
    }
    /* AÃƒÆ’Ã‚Â©roports orphelins : aÃƒÆ’Ã‚Â©roports bÃƒÆ’Ã‚Â¢tis sans ligne active (ex: issu d'un BFAIL conservÃƒÆ’Ã‚Â©). */
    local orphanList = AIStationList(AIStation.STATION_AIRPORT);
    for (local st = orphanList.Begin(); !orphanList.IsEnd(); st = orphanList.Next()) {
    yield null; // PO01C_CHECKPOINT

      if (st in seenStations) continue;
      local loc = AIStation.GetLocation(st);
      if (!AIMap.IsValidTile(loc) || !AIAirport.IsAirportTile(loc)) continue;
      local existingType = AIAirport.GetAirportType(loc);
      if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
      local townId = AITile.GetClosestTown(loc);
      if (townId < 0) continue;
      local hubTown = null;
      foreach (town in towns) {
    yield null; // PO01C_CHECKPOINT

        if (town.id == townId) { hubTown = town; break; }
      }
      if (hubTown == null) {
        hubTown = { id = townId, tile = loc, pop = AITown.GetPopulation(townId) };
      }
      seenStations.rawset(st, true);
      hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 });
      OpexAir0310NoteHubOrigin(ctx, 1);
    }
  }

  /* La decouverte des hubs et des sites supplementaires peut elle aussi
   * suspendre. Revalider les destinations neuves au dernier moment avant
   * le classement hub-site. */
  if (sites.len() > 0) {
    local liveHubSites = [];
    foreach (site in sites) {
    yield null; // PO01C_CHECKPOINT

      if (OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
        liveHubSites.append(site);
      } else if (C69_BOTTLENECK_PROBE) {
        OpexC73RecordRejection("air", "site_stale_before_rank", 1);
      }
    }
    sites = liveHubSites;
  }

  if (DECISION_LOG) {
    local siteFields = sites.len() == 0 ? "none" : "";
    foreach (site in sites) {
    yield null; // PO01C_CHECKPOINT

      if (siteFields != "") siteFields += ",";
      siteFields += site.town.id + ":" + site.town.tile;
    }
    local hubFields = hubs.len() == 0 ? "none" : "";
    foreach (hub in hubs) {
    yield null; // PO01C_CHECKPOINT

      if (hubFields != "") hubFields += ",";
      hubFields += hub.town.id + ":" + hub.town.tile;
    }
    OpexDecide("AIR_PLAN_SETS", "scan=" + servedDiag.scan + " combo=" + combo.kind
               + " airport_type=" + airport.type + " plane=" + plane.id
               + " sites_count=" + sites.len() + " sites=" + siteFields
               + " hubs_count=" + hubs.len() + " hubs=" + hubFields);
  }

  ctx.sites = sites;
  ctx.hubs = hubs;
}

function OpexPO01CMakePaxCandidate(po01dResult, po01fSitableCache, po01fContext, catalog, kind, cargo, srcTile, dstTile, monthly, originServed, stats, isTransformer = false, profile = null, cruiseCache = null, secondary = null)
{
  if (monthly <= 0) {
    stats.noMonthly++;
    { po01dResult.value = null; return; }
  }
  local distance = AIMap.DistanceManhattan(srcTile, dstTile);
  local bounds = OpexCatalogBounds(catalog);
  if (kind == "pax") {
    if (distance < bounds.railMin) {
      stats.distanceShort++;
      { po01dResult.value = null; return; }
    }
    if (distance > bounds.railMax) {
      stats.distanceLong++;
      { po01dResult.value = null; return; }
    }
  } else if (distance > ((V269_RAIL_LATE_RELAX > 0 && V269_RELAXED && V269_RAIL_MAX_DIST > bounds.railMax) ? V269_RAIL_MAX_DIST : bounds.railMax)) {
    stats.distanceLong++;
    { po01dResult.value = null; return; }
  }
  local iterations = OpexRailIterations(distance);
  /* Source seulement, et seulement si origin_sitable = 1. Les 7 a 15 SITEA mesures etaient
   * tous du fret a nCargo=0 cote A. Filtrer aussi le puits enlevait des paires urbaines encore
   * constructibles. A 0, le classement est celui d'avant le filtre (SITEA reste possible).
   *
   * MEMO (2026-09-09) : le predicat ne depend que de (srcTile, cargo), jamais de dstTile. Dans
   * la boucle de paires, srcTile est invariant sur toute la liste de voisins d'une meme ville
   * source : sans memo, le balayage en anneaux (jusqu'a ~225 tuiles, un appel natif chacune)
   * etait refait une fois PAR PAIRE au lieu d'une fois par source. Table videe a chaque
   * OpexBuildCandidates -- aucune donnee stale possible : une gare ou un rail bati pres de la
   * source change le resultat, et la generation suivante le recalcule.
   * Cle entiere plutot que chaine : NUM_CARGO <= 64 dans OpenTTD, donc srcTile * 64 + cargo est
   * injectif, et evite de construire une chaine a chaque paire (ce qui aurait coute presque
   * aussi cher que le cas ou le predicat repond des le premier anneau).
   * âš ï¸ profile.paxSitableCalls compte desormais les CALCULS reels, pas les invocations : c'est
   * ce qu'on veut mesurer, mais ce n'est plus comparable aux releves anterieurs au memo.
   *
   * MESURE (2026-09-09, 3 graines x 2 ans, 256x256, c41_rail_pax_candidate_profile=1) :
   * graine 42 865 calculs pour 4 298 appels (5,0x), graine 100 920 pour 4 398 (4,8x),
   * graine 7 1 148 pour 6 197 (5,4x) -- ~100 opcodes par calcul reel. Le facteur de
   * reutilisation est borne par le nombre de voisins a portee d'une ville source : il vaut
   * ~5 sur 256x256 et croit avec la taille de carte, donc le gain est le plus grand la ou il
   * sert le plus (C46, cartes 1024x1024). */
  local sitable = true;
  local sitableKey = srcTile * 64 + cargo;
  if (sitableKey in po01fSitableCache) {
    sitable = po01fSitableCache[sitableKey];
  } else {
    local sitableMark = profile != null ? OpexOpsMeasureBegin() : null;
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CRailOriginSitable(po01dBox, srcTile, cargo, catalog.railCoverage, true);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    sitable = po01dBox.value;
    if (profile != null) {
      profile.paxSitableOps += OpexOpsMeasureEnd(sitableMark);
      profile.paxSitableCalls++;
    }
    po01fSitableCache[sitableKey] <- sitable;
      if (DECISION_LOG && po01fContext.diagnostics != null)
        po01fContext.diagnostics.sitableFills++;
  }
  if (!sitable) {
    stats.unsitable++;
    { po01dResult.value = null; return; }
  }

  if (V216A_GHOST_DEMAND > 0 && kind == "pax") {
    po01fContext.used = true;
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216aScaleDemand(po01dBox, po01fContext, srcTile, dstTile, cargo, monthly);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    monthly = po01dBox.value;
    if (secondary != null) {
      local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216aScaleDemand(po01dBox, po01fContext, srcTile, dstTile, secondary.cargo, secondary.monthly);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    local po01fMail = po01dBox.value;
      secondary = { cargo = secondary.cargo, monthly = po01fMail };
    }
    if (monthly <= 0) {
      stats.noMonthly++;
      { po01dResult.value = null; return; }
    }
  }
  local economicsMark = profile != null ? OpexOpsMeasureBegin() : null;
  /* C41.33 donne le total ; C41.34 le republie avec ses sous-phases afin que les sorties
   * prÃ©coces de OpexLineEconomics restent visibles comme reliquat de prÃ©paration. */
  local freightEconomicsMark = (profile != null && kind == "freight" && (C41_RAIL_FREIGHT_ECONOMICS_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_DETAIL_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_SETUP_PROFILE || C41_RAIL_FREIGHT_ECONOMICS_CONSIST_PROFILE)) ? OpexOpsMeasureBegin() : null;
  if (DECISION_LOG) OpexPO01CWhere("OpexPO01CMakePaxCandidate", "pax:LineEconomics", -1);
  local economics = OpexLineEconomics(catalog, cargo, distance, monthly, kind, 0, null, profile, cruiseCache,
                                      null, null, secondary);
  if (profile != null) {
    profile.paxEconomicsOps += OpexOpsMeasureEnd(economicsMark);
    profile.paxEconomicsCalls++;
  }
  if (freightEconomicsMark != null) {
    profile.freightEconomicsOps += OpexOpsMeasureEnd(freightEconomicsMark);
    profile.freightEconomicsCalls++;
  }
  if (EQUIPMENT_ROI_PROBE) {
    local m3Candidate = { cargo = cargo, distance = distance, monthly = monthly, kind = kind };
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CMakePaxCandidate", "pax:M3ProbeRailEquipment", -1);
    OpexM3ProbeRailEquipment(catalog, m3Candidate, 0, null, economics, "pre_admission");
  }
  if (economics == null) {
    stats.economicsUnavailable++;
    { po01dResult.value = null; return; }
  }
  /* Un candidat dont le profit annuel attendu est negatif ne merite aucun opcode.
   * L'ancienne famille pax_near (PAX_NEAR fige a false) n'admet plus rien. */
  if (economics.profitAnnual <= 0) {
    stats.profitNonPositive++;
    if (V216_PROBE) OpexV216NoteReject("profit", kind, srcTile, dstTile, monthly, economics);
    { po01dResult.value = null; return; }
  }

  local opcodeRatio = (economics.profitAnnual * 1000) / iterations;
  /* MIN_RATIO reste une mesure et le cout d'opportunite terminal du pathfinder, mais il ne peut
   * plus eliminer un mode AVANT l'arbitrage par couple O/D. La contrainte d'opcodes est appliquee
   * apres la contrainte de capital dans projects.nut. */
  local minRatio = (kind == "freight") ? 200 : MIN_RATIO;
  local isLowRatio = (opcodeRatio < minRatio);
  if (isLowRatio) {
    stats.ratioTooLow++;
    if (V216_PROBE) OpexV216NoteReject("ratio", kind, srcTile, dstTile, monthly, economics);
    { po01dResult.value = null; return; }
  }

  /* Score composite : priorise le fort ROI et le retour sur investissement rapide (cash turnover).
   * Une rotation rapide (oneWayDays court) reinjecte du cash rapidement pour financer les lignes suivantes. */
  local turnoverBonus = 100;
  if (economics.oneWayDays <= 12) turnoverBonus = 130;
  else if (economics.oneWayDays <= 25) turnoverBonus = 115;
  else if (economics.oneWayDays <= 45) turnoverBonus = 100;
  else turnoverBonus = 60;
  /* C32 : un forfait n'est pas une estimation. Le monopole (+40 %) et la chaine (+35 %) deplacaient
   * le classement sans rien predire, et C27 avait deja du les sortir du numerateur de densite parce
   * qu'ils faussaient un diagnostic entier. Tous les modes concourent desormais
   * sur leur ROI estime. */
  local freightBonus = 100;
  local adjustedRoi = (((economics.roi * turnoverBonus) / 100) * freightBonus) / 100;
  local ratio = opcodeRatio + (adjustedRoi * 15);
  local effectiveRoi = (economics.roi * freightBonus) / 100;

  stats.accepted++;
  local candidate = {
    mode = "rail",
    kind = kind,            // "pax" ou "freight"
    cargo = cargo,
    /* Vrai quand UNE des deux extremites reutilise une origine deja desservie ; le champ
     * alimente le cout de tension fonciere (une seule origine libre consommee). */
    originServed = originServed,
    src = srcTile,
    dst = dstTile,
    distance = distance,
    monthly = monthly,
    trains = economics.trains,
    wagons = economics.wagons,
    perTrain = economics.perTrain,
    platformLength = economics.platformLength,
    loco = economics.loco,
    effectiveSpeed = economics.effectiveSpeed,
    tripsPerMonth = economics.tripsPerMonth,
    headwayDays = economics.headwayDays,
    stationRating = economics.stationRating,
    offered = economics.offered,
    monthlyCapacity = economics.monthlyCapacity,
    trainsForHeadway = economics.trainsForHeadway,
    trainsForVolume = economics.trainsForVolume,
    carried = economics.carried,
    capital = economics.capital,
    vehicleCost = economics.vehicleCost,
    immobilise = ("immobilise" in economics) ? economics.immobilise : 0,
    roi = effectiveRoi,
    /* B6 diagnostic : le bonus de rotation agit sur ratio/TopK en amont, pas sur ce roi. */
    turnoverBonus = turnoverBonus,
    freightBonus = freightBonus,
    isTransformer = isTransformer,
    profitAnnual = economics.profitAnnual,
    /* Detail du calcul, garde pour l'instrumentation predit-vs-reel (cf. main.nut). */
    revenueAnnual = economics.revenueAnnual,
    runningAnnual = economics.runningAnnual,
    amortAnnual = economics.amortAnnual,
    oneWayDays = economics.oneWayDays,
    iterations = iterations,
    ratio = ratio,
    opcodeRatio = opcodeRatio,
    isLowRatio = isLowRatio,
  };
  /* V163 : le second cargo n'est garde que s'il a trouve place dans la rame. */
  if (("wagons2" in economics) && economics.wagons2 > 0) {
    candidate.cargo2 <- economics.cargo2;
    candidate.monthly2 <- economics.monthly2;
    candidate.wagons2 <- economics.wagons2;
    candidate.perTrain2 <- economics.perTrain2;
    candidate.carried2 <- economics.carried2;
    candidate.revenue2 <- economics.revenue2;
  }
  { po01dResult.value = candidate; return; }
}

function OpexPO01CRailOriginSitable(po01dResult, tile, cargo, coverage, wantProduction)
{
  local po01gWork = 0;
  local radius = coverage + 3;
  for (local r = 0; r <= radius; r++) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRailOriginSitable", "pax:RailOriginSitable", -1);
    }

    for (local dx = -r; dx <= r; dx++) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRailOriginSitable", "pax:RailOriginSitable", -1);
    }

      for (local dy = -r; dy <= r; dy++) {
    if (++po01gWork % 32 == 0) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CRailOriginSitable", "pax:RailOriginSitable", -1);
    }
    }

        if (abs(dx) != r && abs(dy) != r) continue;
        local t = tile + AIMap.GetTileIndex(dx, dy);
        if (!AIMap.IsValidTile(t)) continue;
        if (AITile.IsWaterTile(t)) continue;
        if (AITile.IsStationTile(t) || AIRail.IsRailTile(t)) continue;
        local industry = AIIndustry.GetIndustryID(t);
        if (AIIndustry.IsValidIndustry(industry)) continue;
        local value = wantProduction
            ? AITile.GetCargoProduction(t, cargo, 1, 1, coverage)
            : AITile.GetCargoAcceptance(t, cargo, 1, 1, coverage);
        if (wantProduction ? (value > 0) : (value >= 8)) { po01dResult.value = true; return; }
      }
    }
  }
  { po01dResult.value = false; return; }
}

function OpexPO01CV216MarkRect(po01dResult, po01fContext, table, x0, y0, x1, y1, ratings)
{
  local po01gWork = 0;
  if (x0 < 1) x0 = 1;
  if (y0 < 1) y0 = 1;
  if (x1 > AIMap.GetMapSizeX() - 2) x1 = AIMap.GetMapSizeX() - 2;
  if (y1 > AIMap.GetMapSizeY() - 2) y1 = AIMap.GetMapSizeY() - 2;
  for (local x = x0; x <= x1; x++) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216MarkRect", "pax:V216MarkRect", -1);
    }

    for (local y = y0; y <= y1; y++) {
    if (++po01gWork % 32 == 0) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216MarkRect", "pax:V216MarkRect", -1);
    }
    }

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

function OpexPO01CV216RefreshCover(po01dResult, po01fContext)
{
  local now = po01fContext.now;
  local ym = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now) - 1;
  local cover = po01fContext.cover;
  if (cover.ownMonth == ym) { po01dResult.value = cover; return; }
  cover.ownMonth = ym;
  if (DECISION_LOG && po01fContext.diagnostics != null)
    po01fContext.diagnostics.coverRebuilds++;
  cover.cache = {};
  cover.own = {};
  if (cover.advQuarter != ym / 3) {
    cover.advQuarter = ym / 3;
    cover.adv = {};
  }
  local pax = OpexV216Cargo(AICargo.CC_PASSENGERS);
  local mail = OpexV216Cargo(AICargo.CC_MAIL);
  foreach (st, sv in AIStationList(AIStation.STATION_ANY)) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216RefreshCover", "pax:V216RefreshCover", -1);
    }

    local ratings = [0, 0];
    if (pax != null && AIStation.HasCargoRating(st, pax)) ratings[0] = AIStation.GetCargoRating(st, pax);
    if (mail != null && AIStation.HasCargoRating(st, mail)) ratings[1] = AIStation.GetCargoRating(st, mail);
    foreach (type in [AIStation.STATION_TRAIN, AIStation.STATION_AIRPORT, AIStation.STATION_BUS_STOP,
                      AIStation.STATION_TRUCK_STOP, AIStation.STATION_DOCK]) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216RefreshCover", "pax:V216RefreshCover", -1);
    }
      if (!AIStation.HasStationType(st, type)) continue;
      local x0 = 99999, y0 = 99999, x1 = -1, y1 = -1, r = 0;
      foreach (tile, tv in AITileList_StationType(st, type)) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216RefreshCover", "pax:V216RefreshCover", -1);
    }

        local x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
        if (x < x0) x0 = x;
        if (y < y0) y0 = y;
        if (x > x1) x1 = x;
        if (y > y1) y1 = y;
        if (r == 0) r = OpexV216StationRadius(tile);
      }
      if (x1 >= 0) {
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216MarkRect(po01dBox, po01fContext, cover.own, x0 - r, y0 - r, x1 + r, y1 + r, ratings);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    }
    }
  }
  { po01dResult.value = cover; return; }
}

function OpexPO01CV216AdvAround(po01dResult, po01fContext, cover, center, radius)
{
  if (center in cover.adv) { po01dResult.value = cover.adv[center]; return; }
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
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216AdvAround", "pax:V216AdvAround", -1);
    }

    if (AITile.GetOwner(tile) == me) continue;
    if (!AIRail.IsRailStationTile(tile) && !AIAirport.IsAirportTile(tile)
        && !AIRoad.IsRoadStationTile(tile) && !AIMarine.IsDockTile(tile)) continue;
    local r = OpexV216StationRadius(tile);
    local x = AIMap.GetTileX(tile), y = AIMap.GetTileY(tile);
    {
    local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216MarkRect(po01dBox, po01fContext, table, x - r > cx - radius ? x - r : cx - radius,
        y - r > cy - radius ? y - r : cy - radius,
        x + r < cx + radius ? x + r : cx + radius,
        y + r < cy + radius ? y + r : cy + radius, null);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    }
  }
  cover.adv.rawset(center, table);
  { po01dResult.value = table; return; }
}

function OpexPO01CV216Coverage(po01dResult, po01fContext, center, cargo, radius)
{
  local po01gWork = 0;
  local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216RefreshCover(po01dBox, po01fContext);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    local cover = po01dBox.value;
  local key = center + "|" + cargo + "|" + radius;
  if (key in cover.cache) { po01dResult.value = cover.cache[key]; return; }
  local adv;
  { local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216AdvAround(po01dBox, po01fContext, cover, center, radius);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    adv = po01dBox.value; }
  local ci = AICargo.HasCargoClass(cargo, AICargo.CC_MAIL) ? 1 : 0;
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local res = { prod = 0, own = 0, adv = 0, ownRating = 0 };
  for (local x = cx - radius; x <= cx + radius; x++) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216Coverage", "pax:V216Coverage", -1);
    }

    for (local y = cy - radius; y <= cy + radius; y++) {
    if (++po01gWork % 32 == 0) {
    if (OpexOpsMeasureEnd(PO01C_WORK_MARK) >= PO01C_WORK_OPS) {
      yield null; // PO01C_CHECKPOINT
    if (DECISION_LOG) OpexPO01CWhere("OpexPO01CV216Coverage", "pax:V216Coverage", -1);
    }
    }

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
  { po01dResult.value = res; return; }
}

function OpexPO01CV216GainPct(po01dResult, po01fContext, center, cargo, radius, rn)
{
  if (center == null || center < 0 || rn <= 0) { po01dResult.value = 100; return; }
  local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216Coverage(po01dBox, po01fContext, center, cargo, radius);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    local c = po01dBox.value;
  if (c.prod <= 0) { po01dResult.value = 100; return; }
  local rnf = rn.tofloat();
  local ro = c.ownRating.tofloat();
  local best = rnf > ro ? rnf : ro;
  local free = (c.prod - c.own - c.adv).tofloat();
  { po01dResult.value = (100.0 * (free * rnf + c.own * (best - ro) + c.adv * rnf * 0.5) / (c.prod * rnf)).tointeger(); return; }
}

function OpexPO01CV216aEndPct(po01dResult, po01fContext, center, cargo, radius)
{
  if (V216A_GHOST_DEMAND == 1) { local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216GainPct(po01dBox, po01fContext, center, cargo, radius, V216A_RN);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    po01dResult.value = po01dBox.value; return; }
  if (center == null || center < 0) { po01dResult.value = 100; return; }
  local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216Coverage(po01dBox, po01fContext, center, cargo, radius);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    local c = po01dBox.value;
  if (c.prod <= 0) { po01dResult.value = 100; return; }
  local rnf = V216A_RN.tofloat();
  local ro = c.ownRating.tofloat();
  local best = rnf > ro ? rnf : ro;
  local free = (c.prod - c.own - c.adv).tofloat();
  local line = free * rnf + c.own * best * rnf / (rnf + ro) + c.adv * rnf * 0.5;
  { po01dResult.value = (100.0 * line / (c.prod * rnf)).tointeger(); return; }
}

function OpexPO01CV216aScaleDemand(po01dResult, po01fContext, srcTile, dstTile, cargo, monthly)
{
  local radius = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  local po01fSrc, po01fDst;
  { local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216aEndPct(po01dBox, po01fContext, srcTile, cargo, radius);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    po01fSrc = po01dBox.value; }
  { local po01dBox = { value = null };
    local po01dChild = OpexPO01CV216aEndPct(po01dBox, po01fContext, dstTile, cargo, radius);
    while (po01dChild.getstatus() != "dead") {
      resume po01dChild;
      if (po01dChild.getstatus() != "dead") yield null; // PO01C_CHECKPOINT
    }
    po01fDst = po01dBox.value; }
  local pct = (po01fSrc + po01fDst) / 2;
  if (pct >= 100) { po01dResult.value = monthly; return; }
  { po01dResult.value = (monthly * pct) / 100; return; }
}
