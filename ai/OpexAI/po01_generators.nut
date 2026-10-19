/* PO-01 : variantes a generateurs des quatre boucles de candidats.
 * Copies mecaniques : test_po01_reactive_split compare leur corps au producteur
 * synchrone apres retrait des seuls checkpoints. Ne pas modifier une copie seule.
 * Une reprise conserve les locales de la VM (aucune closure capturant une locale).
 * Etat transitoire uniquement ; jamais Save/Load.
 */

function OpexPO01PaxCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, candidateProfile = null, cruiseCache = null, paxBand = PAX_BAND_ALL, targetKind = null, targetId = -1)
{
  local cargo = catalog.paxCargo;
  if (cargo < 0) return;
  local towns = catalog.towns;
  local n = towns.len();
  local produced = [];
  local served = [];
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  for (local i = 0; i < n; i++) {
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
    local neighbors = grid.GetCandidatesFor(a);
    foreach (b in neighbors) {
    yield null; // PO01_CHECKPOINT
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

function OpexPO01FreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, cruiseCache = null, freightCargo = null, targetKind = null, targetId = -1)
{
  /* C41.44 : les lignes sont immuables pendant une generation ; une ville peut donc reutiliser
   * exactement son resultat OpexOriginService, y compris null et l'etat blocked. */
  local townServiceCache = {};
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local served = [];
  for (local i = 0; i < industries.len(); i++) {
    yield null; // PO01_CHECKPOINT
    local service = OpexOriginService(lines, industries[i].tile);
    served.append(service);
    if (service != null) stats.industriesServed++; else stats.industriesUnserved++;
  }
  if (profile != null) profile.freightPreparationOps += OpexOpsMeasureEnd(preparationMark);
  foreach (cargo, sources in catalog.producers) {
    yield null; // PO01_CHECKPOINT
    if (freightCargo != null && cargo != freightCargo) continue;
    local hasIndustrySinks = (cargo in catalog.acceptors);
    local hasTownSinks = (cargo in catalog.townAcceptors);
    if (!hasIndustrySinks && !hasTownSinks) continue;
    local sinks = hasIndustrySinks ? catalog.acceptors[cargo] : [];

    foreach (si in sources) {
    yield null; // PO01_CHECKPOINT
      local source = industries[si];
      if (OPEX_LEVEL_LIMITS && OpexIndustryPrimaryRivalServed(source.id, source.tile)) continue;
      local monthly = AIIndustry.GetLastMonthProduction(source.id, cargo);
      local ss = served[si];
      local others2 = V163_MULTI_CARGO ? OpexV163SourceOtherCargos(catalog, source.id, cargo) : null;
      local industryMark = profile != null ? OpexOpsMeasureBegin() : null;
      for (local k = 0; k < sinks.len(); k++) {
    yield null; // PO01_CHECKPOINT
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
        local v179Keep = V179_RAIL_GEN_DEST_SERVED && ss == null && sd != null;
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
        local secondary = (others2 != null && others2.len() > 0)
            ? OpexV163SecondaryCargo(others2, industries[di].id) : null;
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
    yield null; // PO01_CHECKPOINT
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

function OpexPO01RoadFreightCandidates(catalog, lines, out, stats, abandonedPairs = null, profile = null, freightCargo = null, targetKind = null, targetId = -1)
{
  local preparationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local industries = catalog.industries;
  local towns = catalog.towns;
  local servedIndex = OpexRoadFreightServedIndex(lines);
  local servedIndustry = [];
  for (local i = 0; i < industries.len(); i++) {
    yield null; // PO01_CHECKPOINT
    servedIndustry.append(servedIndex != null
        ? (industries[i].tile in servedIndex) : OpexOriginServed(lines, industries[i].tile, true));
  }
  local servedTown = [];
  for (local i = 0; i < towns.len(); i++) {
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
      if (servedIndustry[si]) {
        /* Le code livre saute toute la source. Sous sonde, enumerer seulement les paires
         * qu'il aurait sautees permet de compter ce filtre sans changer son continue. */
        if (C55_ORIGIN_RELAX_PROBE) {
          local source = industries[si];
          foreach (di in sinks) {
    yield null; // PO01_CHECKPOINT
            if (di != si) OpexC55OriginRelaxObserve("freight", lines, source.tile,
                industries[di].tile, true, servedIndustry[di]);
          }
          for (local ti = 0; ti < towns.len(); ti++) {
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
          OpexC55OriginRelaxObserve("freight", lines, source.tile, towns[ti].tile,
              false, servedTown[ti]);
        }
      }
      local townPool = (townTargets != null) ? townTargets : towns;
      for (local k = 0; k < townPool.len(); k++) {
    yield null; // PO01_CHECKPOINT
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

function OpexPO01WaterPlans(catalog, lines = null, projects = null, profile = null, siteCatalog = null)
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
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
    for (local b = a + 1; b < sites.len(); b++) {
    yield null; // PO01_CHECKPOINT
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
    yield null; // PO01_CHECKPOINT
    if (projects != null) projects.append(plan);
    if (best == null) best = plan;
  }
  if (C56_TASK_TRACE) OpexC56TaskLog("WATER_PROBE_COUNTERS", "water_probe_counters",
                                      "- pairs=" + c56PairsExamined + " lakes_in=" + c56LegacyInZero
                                      + " lakes_out=" + c56LegacyOutZero + " bfs_in=" + c56BfsIn
                                      + " bfs_out=" + c56BfsOut);
  return;
}
