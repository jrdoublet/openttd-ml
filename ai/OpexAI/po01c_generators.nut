/* Mechanical copies: python3 sweeps/po01c_generate.py.
 * Checkpoints retain VM locals; no captured closures. Never saved. */

function OpexPO01CPaxCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, candidateProfile = null, cruiseCache = null, paxBand = PAX_BAND_ALL, targetKind = null, targetId = -1)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0) return;
  if (catalog.locoByCargoWagons != null && !(cargo in catalog.locoByCargoWagons)) return;
  /* V275 bit 4 : l'aerien d'abord. Les premieres annees, la caisse borne et un avion rend
   * plus par livre ; le rail voyageurs attend la 3e annee. Inerte en rail seul. */
  if ((V275_RAIL_PAX_MM & 4) && MODE_AIR
      && OPEX_START_YEAR >= 0 && AIDate.GetYear(AIDate.GetCurrentDate()) < OPEX_START_YEAR + 2) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local served = [];
  /* V275 bit 1 : villes ou nous avons deja un aeroport. Le rail y partagerait les memes
   * maisons que nos avions (V216 : 84 % du deficit rail voyageurs vient de nos modes). */
  local airTowns = null;
  if (V275_RAIL_PAX_MM & 1) {
    airTowns = {};
    foreach (line in lines) {
    yield null; // PO01C_CHECKPOINT
      if (!("mode" in line) || line.mode != "air") continue;
      if (("scrapping" in line) && line.scrapping) continue;
      airTowns.rawset(line.originA, true);
      airTowns.rawset(line.originB, true);
    }
  }
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  for (local i = 0; i < n; i++) {
    yield null; // PO01C_CHECKPOINT
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
    yield null; // PO01C_CHECKPOINT
      local mp = AITown.GetLastMonthProduction(towns[i].id, catalog.mailCargo);
      if (mp < 0) mp = 0;
      mailProduced.append(mp);
    }
  }
  if (profile != null) profile.paxPreparationOps += OpexOpsMeasureEnd(preparationMark);
  local pairTotalMark = profile != null ? OpexOpsMeasureBegin() : null;
  local bounds = OpexCatalogBounds(catalog);
  local cellSize = bounds.railMax;
  if (cellSize < 1) cellSize = 1;
  local grid = OpexSpatialGrid();
  grid.Build(towns, cellSize);
  for (local a = 0; a < n; a++) {
    yield null; // PO01C_CHECKPOINT
    local neighbors = grid.GetCandidatesFor(a);
    foreach (b in neighbors) {
    yield null; // PO01C_CHECKPOINT
      if (targetKind == "town" && targetId >= 0
          && towns[a].id != targetId && towns[b].id != targetId) continue;
      local pairDistance = AIMap.DistanceManhattan(towns[a].tile, towns[b].tile);
      if (!OpexRailPaxPairInBand(bounds, pairDistance, paxBand)) continue;
      if (C60_TOWN_RATING_PROBE) {
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[a].id);
        OpexC60ObserveTownRating("rail", "candidate_gen", towns[b].id);
      }
      if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
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
      local candidate = OpexMakeCandidate(catalog, "pax", cargo, towns[a].tile, towns[b].tile,
                                          monthly, false, stats, false, candidateProfile, cruiseCache,
                                          secondary);
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
}

function OpexPO01CFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1)
{
  /* C41.44 : les lignes sont immuables pendant une generation ; une ville peut donc reutiliser
   * exactement son resultat OpexOriginService, y compris null et l'etat blocked. */
  local townServiceCache = {};
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local served = [];
  for (local i = 0; i < industries.len(); i++) {
    yield null; // PO01C_CHECKPOINT
    local service = OpexOriginService(lines, industries[i].tile);
    served.append(service);
    if (service != null) stats.industriesServed++; else stats.industriesUnserved++;
  }
  if (profile != null) profile.freightPreparationOps += OpexOpsMeasureEnd(preparationMark);
  foreach (cargo, sources in catalog.producers) {
    yield null; // PO01C_CHECKPOINT
    if (freightCargo != null && cargo != freightCargo) continue;
    if (catalog.locoByCargoWagons != null && !(cargo in catalog.locoByCargoWagons)) continue;
    local hasIndustrySinks = (cargo in catalog.acceptors);
    local hasTownSinks = (cargo in catalog.townAcceptors);
    if (!hasIndustrySinks && !hasTownSinks) continue;
    local sinks = hasIndustrySinks ? catalog.acceptors[cargo] : [];

    foreach (si in sources) {
    yield null; // PO01C_CHECKPOINT
      local source = industries[si];
      if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local ss = served[si];
      local others2 = null;
      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
    yield null; // PO01C_CHECKPOINT
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
          if (V264_CONVERGENT_FREIGHT && ss == null && sd != null) {
            attached = OpexV264ConvergentService(lines, sd, cargo, source.tile);
          }
          if (attached == null) {
            stats.pairsOriginServed++;
            continue;
          }
          local kept = OpexV264EmitConvergent(catalog, stats, profile, cruiseCache, cargo,
                                              source, industries[di], monthly, others2, attached);
          if (kept != null) out.append(kept);
          continue;
        }
        local isTransformer = ("isTransformer" in industries[di]) && industries[di].isTransformer;
        local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
        local secondary = null;
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
          if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
          local candidateMark = profile != null ? OpexOpsMeasureBegin() : null;
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
}

function OpexPO01CRoadFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, freightCargo = null, targetKind = null, targetId = -1)
{
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local towns = catalog.towns;
  local servedIndex = OpexRoadFreightServedIndex(lines);
  local servedIndustry = [];
  for (local i = 0; i < industries.len(); i++) {
    yield null; // PO01C_CHECKPOINT
    servedIndustry.append(servedIndex != null
        ? (industries[i].tile in servedIndex) : OpexOriginServed(lines, industries[i].tile, true));
  }
  local servedTown = [];
  for (local i = 0; i < towns.len(); i++) {
    yield null; // PO01C_CHECKPOINT
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
    if (freightCargo != null && cargo != freightCargo) continue;
    if (!(cargo in catalog.roadEngineByCargo)) { stats.noEngine++; continue; }
    /* Les passagers sont traites par la famille 1 : les inclure ici apparierait une industrie a
     * une ville pour un cargo qu'aucune industrie ne produit utilement en volume. */
    if (cargo == catalog.paxCargo) continue;
    local sinks = (cargo in catalog.acceptors) ? catalog.acceptors[cargo] : [];
    /* C41.20 : la liste est locale au cargo et a cette generation. Les appels API anticipes sont
     * purs ; ils ne changent ni l'industrie, ni le filtre de distance, ni l'ordre des candidats. */
    local townTargets = OpexRoadFreightAcceptedTowns(towns, servedTown, cargo, truckCoverage);
    if (townTargets != null) stats.townAcceptancePrefiltered += towns.len() - townTargets.len();

    foreach (si in sources) {
    yield null; // PO01C_CHECKPOINT
      if (servedIndustry[si]) {
        /* Le code livre saute toute la source. Sous sonde, enumerer seulement les paires
         * qu'il aurait sautees permet de compter ce filtre sans changer son continue. */
        if (C55_ORIGIN_RELAX_PROBE) {
          local source = industries[si];
          foreach (di in sinks) {
    yield null; // PO01C_CHECKPOINT
            if (di != si) OpexC55OriginRelaxObserve("freight", lines, source.tile,
                industries[di].tile, true, servedIndustry[di]);
          }
          for (local ti = 0; ti < towns.len(); ti++) {
    yield null; // PO01C_CHECKPOINT
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
          OpexC55OriginRelaxObserve("freight", lines, source.tile, towns[ti].tile,
              false, servedTown[ti]);
        }
      }
      local townPool = (townTargets != null) ? townTargets : towns;
      for (local k = 0; k < townPool.len(); k++) {
    yield null; // PO01C_CHECKPOINT
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
        if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
        local candidateMark = (profile != null && C41_ROAD_FREIGHT_TOWN_PROFILE)
            ? OpexOpsMeasureBegin() : null;
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
                                                  WATER_OPCODE_COMPAT_FALSE ? profile : null);
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

      /* Slot neutre : l'ancienne bascule etait forcee false. La branche vide conserve
       * sa structure d'execution sans restaurer le flag ni le code Lakes. */
      if (WATER_OPCODE_COMPAT_FALSE) {
      } else {
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

function OpexPO01CCargos(catalog)
{
  catalog.cargos = [];
  catalog.paxCargo = -1;
  catalog.mailCargo = -1;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    yield null; // PO01C_CHECKPOINT
    catalog.cargos.append(c);
    if (catalog.paxCargo < 0 && AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) catalog.paxCargo = c;
    if (catalog.mailCargo < 0 && AICargo.HasCargoClass(c, AICargo.CC_MAIL)) catalog.mailCargo = c;
  }
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
    if (t > chosen) chosen = t;
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
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
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
    c83RepairCombo = false,
    air0310HubRestored = false,
    air0310HubSkip = null,
  };

  local spPlans = PROBE_SPAN_TRACE ? OpexSpanBegin("air.plans") : null;
  local prepared = OpexAirPlansStepPrepare(ctx);
  if (!prepared) {
    if (spPlans != null) OpexSpanEnd(spPlans);
    { po01dResult.value = ctx.bestPlan; return; }
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
  if (ctx.sliced && ("c83Repair" in ctx.resumeState)) {
    local repaired = OpexC83RepairFindSites(ctx, comboIndex, combo, airport, plane);
    if (repaired.handled) { po01dResult.value = repaired.done; return; }
  }
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
    if (C83_FIXES && targetTownId >= 0) {
      scanEnd = scanStart;
      for (local c83Scan = scanStart; c83Scan < limit; c83Scan++) {
    yield null; // PO01C_CHECKPOINT

        if (towns[c83Scan].id == targetTownId) {
          scanEnd = c83Scan + 1;
          break;
        }
      }
    }
    local testedBefore = probes.tested;
    local cheapBefore = ("cheapSkip" in probes) ? probes.cheapSkip : 0;
    local foundBefore = scanSites.len();
    local tSites0 = AIController.GetTick();
    local lSites0 = AIController.GetOpsTillSuspend();
    for (local i = scanStart; i < scanEnd; i++) {
    yield null; // PO01C_CHECKPOINT

      probes.townsLeft = limit - i;
      if (C83_FIXES && targetTownId >= 0) probes.townsLeft = scanEnd - i;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      if (V133_AIR_BUILD_RETRY && OpexV133AirTownSkip(ctx, towns[i].id)) {
        /* V133 : ville en quarantaine, aucun site newpair/hubsite. Le curseur de tranche suit. */
      } else if (OPEX_LEVEL_LIMITS && !OpexTownAirportAllowedByLevel(towns[i], null, -1, ctx.catalog)) {
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
        local v134State = (V134_AIR_P2P_SATURATED_HUB && isServed)
            ? OpexAirV134SaturatedHubState(towns[i], lines, ctx.hubIndex)
            : { eligible = false, hubRoutes = 0 };
        local v134Eligible = v134State.eligible;
        local skipServed = false;
        if (isServed && !c83OwnSecondSlot) skipServed = !v134Eligible;
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
          if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
            c83RequiredSlotTown = towns[i].id;
          }
          if (c83RequiredSlotTown < 0 && v134Eligible) {
            c83RequiredSlotTown = towns[i].id;
          }
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
            if (v134Eligible) {
              site.v134SecondSlot <- true;
              site.v134HubRoutes <- v134State.hubRoutes;
            }
            if (C83_FIXES && c83RequiredSlotTown >= 0) site.c83SlotTown <- c83RequiredSlotTown;
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
    if (!ctx.c83RepairCombo && sites.len() < AIR_HUB_NEW_SITE_POOL) {
      local hubProbes = {
        left = AIR_MAX_SITE_PROBES, townsLeft = limit, tested = 0, cheapSkip = 0,
        stationLimitedTowns = stationLimitedTowns
      };
      local tHubSites0 = AIController.GetTick();
      local lHubSites0 = AIController.GetOpsTillSuspend();
      local hubScanEnd = limit;
      if (C83_FIXES && targetTownId >= 0) {
        hubScanEnd = 0;
        for (local c83Scan = 0; c83Scan < limit; c83Scan++) {
    yield null; // PO01C_CHECKPOINT

          if (towns[c83Scan].id == targetTownId) {
            hubScanEnd = c83Scan + 1;
            break;
          }
        }
      }
      for (local i = 0; i < hubScanEnd && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
    yield null; // PO01C_CHECKPOINT

        hubProbes.townsLeft = limit - i;
        if (C83_FIXES && targetTownId >= 0) hubProbes.townsLeft = hubScanEnd - i;
        if (V133_AIR_BUILD_RETRY && OpexV133AirTownSkip(ctx, towns[i].id)) continue;
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
        if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
          c83RequiredSlotTown = towns[i].id;
        }
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
          if (C83_FIXES && c83RequiredSlotTown >= 0) extraSite.c83SlotTown <- c83RequiredSlotTown;
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
