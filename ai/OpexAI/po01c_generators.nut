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
        navigableDistance = OpexWaterFindConnection(sites[a], sites[b]);
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
