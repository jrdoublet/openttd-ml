/* Chemins opcode EXACT (exp_opcode_exact / exp_opcode_exact_check).
 * A 0, les fonctions historiques restent inline dans leur module : ce fichier
 * n'est execute que lorsque EXP_OPCODE_EXACT_ON est vrai.
 * Le mode check execute l'ancien et le nouveau calcul, compare les sorties,
 * publie les opcodes, et RENVOIE l'ancien resultat.
 * OpexOpsMeasureBegin/End n'est pas reentrant : jamais deux mesures imbriquees.
 */

OPCODE_EXACT_SITE_NAME <- null;

function OpexOpcodeExactSite(fallback) {
  if (OPCODE_EXACT_SITE_NAME != null) return OPCODE_EXACT_SITE_NAME;
  return fallback;
}

/* Borne de Manhattan. Les anneaux 0..R visitent le disque de Chebyshev de
 * rayon R : pour toute tuile balayee t, manhattan(centre, t) <= 2R.
 * Donc manhattan(t, arret) >= manhattan(centre, arret) - 2R.
 * Si manhattan(centre, arret) >= 2R + D, aucune tuile balayee (meme hors
 * carte : le bord ne fait que retirer des tuiles) n'est a distance < D.
 * L'ordre des arrets conserves est celui de la liste d'origine. */
function OpexRoadExcludeWithin(excludeTiles, center, radius, minDist) {
  if (excludeTiles == null) return null;
  /* minDist = seuil strict du test d'exclusion de l'appelant (voirie : ROAD_PAX_VOIRIE_MIN_PAIR). */
  local bound = 2 * radius + minDist;
  local near = [];
  foreach (exTile in excludeTiles) {
    if (AIMap.DistanceManhattan(center, exTile) < bound) near.append(exTile);
  }
  return near;
}

function OpexRoadStopsTooClose(tile, excludeTiles) {
  if (excludeTiles == null || excludeTiles.len() == 0) return false;
  foreach (exTile in excludeTiles) {
    if (AIMap.DistanceManhattan(tile, exTile) < ROAD_BUS_STOP_MIN_DISTANCE) return true;
  }
  return false;
}

function OpexRoadSiteListSame(a, b) {
  if (a == null || b == null || a.len() != b.len()) return false;
  for (local i = 0; i < a.len(); i++) {
    local x = a[i];
    local y = b[i];
    if (x.tile != y.tile || x.front != y.front || x.value != y.value || x.score != y.score) return false;
  }
  return true;
}

function OpexRoadSiteListDiff(a, b) {
  if (a == null || b == null) return "sites=null";
  if (a.len() != b.len()) return "sites=" + a.len() + "/" + b.len();
  for (local i = 0; i < a.len(); i++) {
    local x = a[i];
    local y = b[i];
    if (x.tile != y.tile) return "i=" + i + " tile=" + x.tile + "/" + y.tile;
    if (x.front != y.front) return "i=" + i + " front=" + x.front + "/" + y.front;
    if (x.value != y.value) return "i=" + i + " value=" + x.value + "/" + y.value;
    if (x.score != y.score) return "i=" + i + " score=" + x.score + "/" + y.score;
  }
  return "sites=ok";
}

function OpexRoadHuntSame(a, b) {
  if (a == null || b == null) return false;
  if (a.nCargo != b.nCargo || a.nBuildable != b.nBuildable || a.nCmd != b.nCmd || a.probes != b.probes) return false;
  return OpexRoadSiteListSame(a.sites, b.sites);
}

function OpexRoadHuntDiff(a, b) {
  if (a == null || b == null) return "hunt=null";
  if (a.nCargo != b.nCargo) return "nCargo=" + a.nCargo + "/" + b.nCargo;
  if (a.nBuildable != b.nBuildable) return "nBuildable=" + a.nBuildable + "/" + b.nBuildable;
  if (a.nCmd != b.nCmd) return "nCmd=" + a.nCmd + "/" + b.nCmd;
  if (a.probes != b.probes) return "probes=" + a.probes + "/" + b.probes;
  return OpexRoadSiteListDiff(a.sites, b.sites);
}

function OpexRoadHuntCore(hunt) {
  return { sites = hunt.sites, nCargo = hunt.nCargo, nBuildable = hunt.nBuildable,
           nCmd = hunt.nCmd, probes = hunt.probes };
}

/* Classification historique d'une tuile : ville, puis liste d'exclusion entiere,
 * puis cargo, puis constructibilite. Les compteurs ne bougent qu'apres l'exclusion. */
function OpexRoadHistoricClassify(tile, townId, excludeTiles, cargo, wantProduction, coverage, requireCargo) {
  if (townId >= 0 && AITile.GetClosestTown(tile) != townId) {
    return { skip = true, why = "town", value = 0, build = false, steps = 0 };
  }
  local steps = 0;
  if (excludeTiles != null && excludeTiles.len() > 0) {
    foreach (exTile in excludeTiles) {
      steps++;
      if (AIMap.DistanceManhattan(tile, exTile) < ROAD_BUS_STOP_MIN_DISTANCE) {
        return { skip = true, why = "excl", value = 0, build = false, steps = steps };
      }
    }
  }
  local value = wantProduction
      ? AITile.GetCargoProduction(tile, cargo, 1, 1, coverage)
      : AITile.GetCargoAcceptance(tile, cargo, 1, 1, coverage);
  if (requireCargo && (wantProduction ? (value <= 0) : (value < ROAD_ACCEPTANCE_FULL_UNIT))) {
    return { skip = true, why = "cargo", value = value, build = false, steps = steps };
  }
  local build = AITile.IsBuildable(tile) && OpexRoadIsFlat(tile);
  return { skip = false, why = "ok", value = value, build = build, steps = steps };
}

/* Meme resultat, cargo avant l'exclusion reduite. La ville reste l'appel
 * direct : un ensemble Valuate(GetClosestTown) a diverge (why=ok/town). */
function OpexRoadExactClassify(tile, townId, near, cargo, wantProduction, coverage, requireCargo) {
  if (townId >= 0 && AITile.GetClosestTown(tile) != townId) {
    return { skip = true, why = "town", value = 0, build = false };
  }
  local value = wantProduction
      ? AITile.GetCargoProduction(tile, cargo, 1, 1, coverage)
      : AITile.GetCargoAcceptance(tile, cargo, 1, 1, coverage);
  if (requireCargo && (wantProduction ? (value <= 0) : (value < ROAD_ACCEPTANCE_FULL_UNIT))) {
    return { skip = true, why = "cargo", value = value, build = false };
  }
  if (OpexRoadStopsTooClose(tile, near)) {
    return { skip = true, why = "excl", value = value, build = false };
  }
  local build = AITile.IsBuildable(tile) && OpexRoadIsFlat(tile);
  return { skip = false, why = "ok", value = value, build = build };
}

function OpexRoadAccumulateFronts(out, x, y, tile, value, otherCenter, vehType, offsets, probes, nCmd) {
  foreach (offset in offsets) {
    if (probes >= ROAD_MAX_SITE_PROBES) break;
    local fx = x + offset[0];
    local fy = y + offset[1];
    if (!OpexRoadInMap(fx, fy)) continue;
    local front = AIMap.GetTileIndex(fx, fy);
    if (!OpexRoadIsFlat(front)) continue;
    if (!AIRoad.IsRoadTile(front) && !AITile.IsBuildable(front)) continue;
    local ok = false;
    { local test = AITestMode();
      ok = AIRoad.BuildRoad(front, tile) &&
           AIRoad.BuildRoadStation(tile, front, vehType, AIStation.STATION_NEW); }
    probes++;
    if (!ok) continue;
    nCmd++;
    local onRoad = AIRoad.IsRoadTile(front);
    local toward = 0;
    if (otherCenter != null &&
        AIMap.DistanceManhattan(front, otherCenter) < AIMap.DistanceManhattan(tile, otherCenter)) {
      toward = 2;
    }
    local site = { tile = tile, front = front, value = value,
                   score = value * 2 + toward + (onRoad ? 1 : 0) };
    local pos = out.len();
    while (pos > 0 && out[pos - 1].score < site.score) pos--;
    out.insert(pos, site);
    if (out.len() > ROAD_MAX_SITES_PER_END) out.pop();
  }
  return { probes = probes, nCmd = nCmd };
}

function OpexRoadSitesScan(center, townId, cargo, vehType, coverage, wantProduction, radius,
                           otherCenter, requireCargo, excludeTiles, paired) {
  local out = [];
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  local probes = 0;
  local nCargo = 0;
  local nBuildable = 0;
  local nCmd = 0;
  local near = null;
  local opsO = 0;
  local opsN = 0;
  local mismatch = 0;
  local detail = "";
  if (paired) {
    local markS = OpexOpsMeasureBegin();
    near = OpexRoadExcludeWithin(excludeTiles, center, radius, ROAD_BUS_STOP_MIN_DISTANCE);
    opsN += OpexOpsMeasureEnd(markS);
  } else {
    near = OpexRoadExcludeWithin(excludeTiles, center, radius, ROAD_BUS_STOP_MIN_DISTANCE);
  }
  local nTiles = 0;
  local nTown = 0;
  local nExclWalk = 0;
  local nExclHit = 0;
  local nExclSteps = 0;
  local nCargoFail = 0;
  local nBuildFail = 0;
  for (local r = 0; r <= radius && probes < ROAD_MAX_SITE_PROBES; r++) {
    for (local dx = -r; dx <= r && probes < ROAD_MAX_SITE_PROBES; dx++) {
      for (local dy = -r; dy <= r && probes < ROAD_MAX_SITE_PROBES; dy++) {
        if (abs(dx) != r && abs(dy) != r) continue;
        local x = cx + dx;
        local y = cy + dy;
        if (!OpexRoadInMap(x, y)) continue;
        local tile = AIMap.GetTileIndex(x, y);
        if (paired) nTiles++;
        local use = null;
        if (paired) {
          local markO = OpexOpsMeasureBegin();
          local hist = OpexRoadHistoricClassify(tile, townId, excludeTiles, cargo, wantProduction,
                                                coverage, requireCargo);
          local spentO = OpexOpsMeasureEnd(markO);
          local markN = OpexOpsMeasureBegin();
          local exact = OpexRoadExactClassify(tile, townId, near, cargo, wantProduction,
                                              coverage, requireCargo);
          local spentN = OpexOpsMeasureEnd(markN);
          opsO += spentO;
          opsN += spentN;
          local agree = hist.skip == exact.skip
              && (hist.skip || (hist.value == exact.value && hist.build == exact.build));
          if (!agree) {
            mismatch++;
            if (detail == "") {
              detail = "tile=" + tile + " skip=" + hist.skip + "/" + exact.skip
                  + " why=" + hist.why + "/" + exact.why
                  + " val=" + hist.value + "/" + exact.value
                  + " build=" + hist.build + "/" + exact.build;
            }
          }
          use = hist;
          nExclSteps += hist.steps;
          if (hist.why == "town") nTown++;
          else {
            nExclWalk++;
            if (hist.why == "excl") nExclHit++;
            else if (hist.why == "cargo") nCargoFail++;
          }
        } else {
          use = OpexRoadExactClassify(tile, townId, near, cargo, wantProduction,
                                      coverage, requireCargo);
        }
        if (use.skip) continue;
        nCargo++;
        if (!use.build) {
          if (paired) nBuildFail++;
          continue;
        }
        nBuildable++;
        local acc = null;
        if (paired) {
          local markP = OpexOpsMeasureBegin();
          acc = OpexRoadAccumulateFronts(out, x, y, tile, use.value, otherCenter, vehType,
                                         offsets, probes, nCmd);
          local spentP = OpexOpsMeasureEnd(markP);
          opsO += spentP;
          opsN += spentP;
        } else {
          acc = OpexRoadAccumulateFronts(out, x, y, tile, use.value, otherCenter, vehType,
                                         offsets, probes, nCmd);
        }
        probes = acc.probes;
        nCmd = acc.nCmd;
      }
    }
  }
  local exclLen = excludeTiles == null ? 0 : excludeTiles.len();
  local nearLen = near == null ? 0 : near.len();
  return {
    sites = out, nCargo = nCargo, nBuildable = nBuildable, nCmd = nCmd, probes = probes,
    tiles = nTiles, townSkip = nTown, exclWalk = nExclWalk, exclHit = nExclHit,
    exclSteps = nExclSteps, cargoFail = nCargoFail, buildFail = nBuildFail,
    exclLen = exclLen, nearLen = nearLen,
    opsOld = opsO, opsNew = opsN, mismatch = mismatch, detail = detail
  };
}

function OpexRoadSitesExact(center, townId, cargo, vehType, coverage, wantProduction, radius,
                            otherCenter, requireCargo, excludeTiles) {
  return OpexRoadSitesScan(center, townId, cargo, vehType, coverage, wantProduction, radius,
                           otherCenter, requireCargo, excludeTiles, false);
}

function OpexRoadSitesGated(center, townId, cargo, vehType, coverage, wantProduction, radius,
                            otherCenter, requireCargo, excludeTiles) {
  return OpexRoadHuntCore(OpexRoadSitesExact(center, townId, cargo, vehType, coverage,
                                               wantProduction, radius, otherCenter, requireCargo,
                                               excludeTiles));
}

function OpexRoadVoirieHistoricClassify(tile, townId, excludeTiles, cargo, coverage, requireCargo, minPair) {
  if (townId >= 0 && AITile.GetClosestTown(tile) != townId) {
    return { skip = true, why = "town", value = 0 };
  }
  if (!AIRoad.IsRoadTile(tile)) return { skip = true, why = "road", value = 0 };
  if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile)) {
    return { skip = true, why = "stop", value = 0 };
  }
  if (OpexRoadTileTooClose(tile, excludeTiles, minPair)) {
    return { skip = true, why = "excl", value = 0 };
  }
  local value = AITile.GetCargoProduction(tile, cargo, 1, 1, coverage);
  if (requireCargo && value <= 0) return { skip = true, why = "cargo", value = value };
  return { skip = false, why = "ok", value = value };
}

function OpexRoadVoirieExactClassify(tile, townId, near, cargo, coverage, requireCargo, minPair) {
  if (townId >= 0 && AITile.GetClosestTown(tile) != townId) return { skip = true, why = "town", value = 0 };
  if (!AIRoad.IsRoadTile(tile)) return { skip = true, why = "road", value = 0 };
  if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile)) {
    return { skip = true, why = "stop", value = 0 };
  }
  local value = AITile.GetCargoProduction(tile, cargo, 1, 1, coverage);
  if (requireCargo && value <= 0) return { skip = true, why = "cargo", value = value };
  if (OpexRoadTileTooClose(tile, near, minPair)) return { skip = true, why = "excl", value = value };
  return { skip = false, why = "ok", value = value };
}

function OpexRoadVoirieTryFronts(out, tile, value, dirs, vehType, probes, sameTown, center, otherCenter) {
  foreach (dir in dirs) {
    if (probes >= ROAD_MAX_SITE_PROBES) return { probes = probes, stop = true };
    local front = tile + dir;
    if (!AIMap.IsValidTile(front) || !AIRoad.IsRoadTile(front)) continue;
    local ok = false;
    { local test = AITestMode();
      ok = AIRoad.BuildDriveThroughRoadStation(tile, front, vehType, AIStation.STATION_NEW); }
    probes++;
    if (!ok) continue;
    local score;
    if (sameTown) {
      local ring = AIMap.DistanceManhattan(tile, center);
      local ringPen = ring > 3 ? ring - 3 : 3 - ring;
      score = value * 2 - ringPen * 4;
    } else {
      local dOther = (otherCenter != null) ? AIMap.DistanceManhattan(tile, otherCenter) : 0;
      score = value * 2 - dOther;
    }
    local site = { tile = tile, front = front, value = value, score = score };
    local pos = out.len();
    while (pos > 0 && out[pos - 1].score < site.score) pos--;
    out.insert(pos, site);
    if (out.len() > ROAD_MAX_SITES_PER_END) out.pop();
    break;
  }
  return { probes = probes, stop = false };
}

function OpexRoadPaxVoirieScan(center, townId, cargo, vehType, coverage, otherCenter,
                               requireCargo, excludeTiles, paired) {
  local out = [];
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local dirs = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1)];
  local probes = 0;
  local radius = ROAD_TOWN_SEARCH_RADIUS;
  local sameTown = otherCenter != null &&
                   AIMap.DistanceManhattan(center, otherCenter) < ROAD_PAX_VOIRIE_SAME_TOWN_MAX_DIST;
  local minPair = ROAD_PAX_VOIRIE_MIN_PAIR;
  local near = null;
  local opsO = 0;
  local opsN = 0;
  local mismatch = 0;
  local detail = "";
  if (paired) {
    local markS = OpexOpsMeasureBegin();
    near = OpexRoadExcludeWithin(excludeTiles, center, radius, minPair);
    opsN += OpexOpsMeasureEnd(markS);
  } else {
    near = OpexRoadExcludeWithin(excludeTiles, center, radius, minPair);
  }
  local nTiles = 0;
  for (local r = 0; r <= radius; r++) {
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
        local adx = dx < 0 ? -dx : dx;
        local ady = dy < 0 ? -dy : dy;
        if (r > 0 && adx != r && ady != r) continue;
        if (!OpexRoadInMap(cx + dx, cy + dy)) continue;
        local tile = AIMap.GetTileIndex(cx + dx, cy + dy);
        if (paired) nTiles++;
        local use = null;
        if (paired) {
          local markO = OpexOpsMeasureBegin();
          local hist = OpexRoadVoirieHistoricClassify(tile, townId, excludeTiles, cargo, coverage,
                                                      requireCargo, minPair);
          local spentO = OpexOpsMeasureEnd(markO);
          local markN = OpexOpsMeasureBegin();
          local exact = OpexRoadVoirieExactClassify(tile, townId, near, cargo, coverage,
                                                    requireCargo, minPair);
          local spentN = OpexOpsMeasureEnd(markN);
          opsO += spentO;
          opsN += spentN;
          local agree = hist.skip == exact.skip && (hist.skip || hist.value == exact.value);
          if (!agree) {
            mismatch++;
            if (detail == "") {
              detail = "tile=" + tile + " skip=" + hist.skip + "/" + exact.skip
                  + " why=" + hist.why + "/" + exact.why
                  + " val=" + hist.value + "/" + exact.value;
            }
          }
          use = hist;
        } else {
          use = OpexRoadVoirieExactClassify(tile, townId, near, cargo, coverage,
                                            requireCargo, minPair);
        }
        if (use.skip) continue;
        local fronts;
        if (paired) {
          local markP = OpexOpsMeasureBegin();
          fronts = OpexRoadVoirieTryFronts(out, tile, use.value, dirs, vehType, probes,
                                           sameTown, center, otherCenter);
          local spentP = OpexOpsMeasureEnd(markP);
          opsO += spentP;
          opsN += spentP;
        } else {
          fronts = OpexRoadVoirieTryFronts(out, tile, use.value, dirs, vehType, probes,
                                           sameTown, center, otherCenter);
        }
        probes = fronts.probes;
        if (fronts.stop) {
          if (paired) {
            local site = OpexOpcodeExactSite("road_voirie");
            local same = mismatch == 0;
          }
          return out;
        }
      }
    }
  }
  if (paired) {
    local site = OpexOpcodeExactSite("road_voirie");
    local same = mismatch == 0;
  }
  return out;
}

function OpexRoadPaxVoirieExact(center, townId, cargo, vehType, coverage, otherCenter,
                                requireCargo, excludeTiles) {
  return OpexRoadPaxVoirieScan(center, townId, cargo, vehType, coverage, otherCenter,
                               requireCargo, excludeTiles, false);
}

function OpexRoadPaxVoirieGated(center, townId, cargo, vehType, coverage, otherCenter,
                                requireCargo, excludeTiles) {
  return OpexRoadPaxVoirieExact(center, townId, cargo, vehType, coverage, otherCenter,
                                  requireCargo, excludeTiles);
}


function OpexRoadPlanForActive(catalog, candidate) {
  if (catalog.roadType < 0) return { plan = null, reason = "NOROAD" };
  AIRoad.SetCurrentRoadType(catalog.roadType);
  if (candidate.kind == "pax") {
    local sameTown = candidate.srcTown >= 0 && candidate.srcTown == candidate.dstTown;
    if (!sameTown) {
      local voirie = OpexRoadPlanPaxVoirie(candidate);
      if (voirie != null) return { plan = voirie, reason = "OK" };
      if (DECISION_LOG) {
        OpexDecide("VOIRIE_PLAN", "fail=FALLBACK srcTown=" + candidate.srcTown
                   + " dstTown=" + candidate.dstTown);
      }
    }
  }
  local stop = OpexRoadStopKind(candidate.cargo);
  local coverage = AIStation.GetCoverageRadius(stop.stationType);
  local radiusA = candidate.srcTown >= 0 ? ROAD_TOWN_SEARCH_RADIUS : ROAD_INDUSTRY_SEARCH_RADIUS;
  local radiusB = candidate.dstTown >= 0 ? ROAD_TOWN_SEARCH_RADIUS : ROAD_INDUSTRY_SEARCH_RADIUS;
  local dstWantsProduction = candidate.kind == "pax";

  local excludeA = null;
  if (stop.vehType == AIRoad.ROADVEHTYPE_BUS) {
    excludeA = OpexRoadOurBusTiles();
    if (("existingStops" in candidate) && candidate.existingStops != null) {
      foreach (existingTile in candidate.existingStops) excludeA.append(existingTile);
    }
  } else if ("existingStops" in candidate) {
    excludeA = candidate.existingStops;
  }
  OPCODE_EXACT_SITE_NAME = "road_a";
  local huntA = OpexRoadSites(candidate.src, candidate.srcTown, candidate.cargo, stop.vehType,
                              coverage, true, radiusA, candidate.dst, true, excludeA);
  OPCODE_EXACT_SITE_NAME = "road_b";
  local sitesA = huntA.sites;
  if (sitesA.len() == 0) {
    OPCODE_EXACT_SITE_NAME = null;
    return { plan = null, reason = "SITEA", site = huntA };
  }
  local huntB = OpexRoadSites(candidate.dst, candidate.dstTown, candidate.cargo, stop.vehType,
                              coverage, dstWantsProduction, radiusB, candidate.src, true,
                              excludeA);
  OPCODE_EXACT_SITE_NAME = null;
  local sitesB = huntB.sites;
  if (sitesB.len() == 0) return { plan = null, reason = "SITEB", site = huntB };

  local trials = 0;
  local nEmpty = 0;
  local nLong = 0;
  local nHit = 0;
  local nUnb = 0;
  local noDepot = 0;

  foreach (siteA in sitesA) {
    foreach (siteB in sitesB) {
      if (stop.vehType == AIRoad.ROADVEHTYPE_BUS &&
          AIMap.DistanceManhattan(siteA.tile, siteB.tile) < ROAD_BUS_STOP_MIN_DISTANCE) continue;
      for (local shape = 0; shape < 2; shape++) {
        if (trials >= ROAD_MAX_TRACE_TRIALS) break;
        trials++;
        local trace = OpexRoadTrace(siteA.front, siteB.front, shape == 0);
        if (trace.len() == 0) { nEmpty++; continue; }
        if (trace.len() > ROAD_MAX_TRACE_TILES) { nLong++; continue; }
        if (OpexRoadTraceHitsStop(trace, siteA.tile) || OpexRoadTraceHitsStop(trace, siteB.tile)) {
          nHit++;
          continue;
        }
        if (!OpexRoadTraceBuildable(trace)) { nUnb++; continue; }
        local depot = OpexRoadFindDepot(trace, siteA, siteB);
        if (depot == null) { noDepot++; continue; }
        return { plan = { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
                          stationType = stop.stationType, vehType = stop.vehType,
                          routeDistance = trace.len(), shape = shape, trials = trials },
                 reason = "OK" };
      }
    }
  }

  foreach (siteA in sitesA) {
    foreach (siteB in sitesB) {
      if (stop.vehType == AIRoad.ROADVEHTYPE_BUS &&
          AIMap.DistanceManhattan(siteA.tile, siteB.tile) < ROAD_BUS_STOP_MIN_DISTANCE) continue;
      for (local shape = 2; shape < 6; shape++) {
        if (trials >= ROAD_MAX_TRACE_TRIALS * 3) break;
        trials++;
        local trace = OpexRoadTraceMulti(siteA.front, siteB.front, shape);
        if (trace.len() == 0) { nEmpty++; continue; }
        if (trace.len() > ROAD_MAX_TRACE_TILES) { nLong++; continue; }
        if (OpexRoadTraceHitsStop(trace, siteA.tile) || OpexRoadTraceHitsStop(trace, siteB.tile)) {
          nHit++;
          continue;
        }
        if (!OpexRoadTraceBuildable(trace)) { nUnb++; continue; }
        local depot = OpexRoadFindDepot(trace, siteA, siteB);
        if (depot == null) { noDepot++; continue; }
        return { plan = { stopA = siteA, stopB = siteB, trace = trace, depot = depot,
                          stationType = stop.stationType, vehType = stop.vehType,
                          routeDistance = trace.len(), shape = shape, trials = trials },
                 reason = "OK" };
      }
    }
  }

  return { plan = null, reason = noDepot > 0 ? "DEPOTX" : "TRACEX",
           trace = { trials = trials, nEmpty = nEmpty, nLong = nLong, nHit = nHit,
                     nUnb = nUnb, nNoDepot = noDepot } };
}

function OpexAirFleetYieldCompare(a, b) {
  if (a.lineYield > b.lineYield) return -1;
  if (a.lineYield < b.lineYield) return 1;
  return 0;
}

function OpexAirFleetSortPrecomputed(airLines) {
  local wrapped = [];
  foreach (line in airLines) {
    wrapped.append({ line = line, lineYield = OpexAirFleetYield(line) });
  }
  wrapped.sort(OpexAirFleetYieldCompare);
  local out = [];
  foreach (item in wrapped) out.append(item.line);
  return out;
}

/* Tri de la copie locale. Ne touche pas this._lines. */
function OpexAirFleetSortSelect(airLines) {
  return OpexAirFleetSortPrecomputed(airLines);
}

function OpexAirCatchmentSumExact(stationId, cargo) {
  local coverageTiles = AITileList_StationCoverage(stationId);
  coverageTiles.Valuate(AITile.GetCargoProduction, cargo, 1, 1, 0);
  local total = 0;
  foreach (tile, value in coverageTiles) total += value;
  return total;
}

function OpexAirStationCatchmentProductionActive(stationId, cargo) {
  return OpexAirCatchmentSumExact(stationId, cargo);
}

function OpexAirJoinedLoopOrder(a, b) {
  if (a.x < b.x) return -1;
  if (a.x > b.x) return 1;
  if (a.y < b.y) return -1;
  if (a.y > b.y) return 1;
  return 0;
}

function OpexAirJoinedCandidatesExact(minX, maxX, minY, maxY, town, paxCargo, coverage,
                                      airportCoverage, ax, ay, w, h, center) {
  if (minX > maxX || minY > maxY) return [];
  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(minX, minY), AIMap.GetTileIndex(maxX, maxY));
  tiles.Valuate(AIRoad.IsRoadTile);
  tiles.KeepValue(1);
  tiles.Valuate(AIRoad.IsRoadStationTile);
  tiles.KeepValue(0);
  tiles.Valuate(AIRoad.IsRoadDepotTile);
  tiles.KeepValue(0);
  tiles.Valuate(AITile.IsStationTile);
  tiles.KeepValue(0);
  tiles.Valuate(AITile.GetCargoProduction, paxCargo, 1, 1, coverage);
  tiles.KeepAboveValue(0);
  local raw = [];
  foreach (tile, val in tiles) {
    if (AITile.GetClosestTown(tile) != town.id) continue;
    if (AIMap.DistanceManhattan(tile, center) < 3) continue;
    local x = AIMap.GetTileX(tile);
    local y = AIMap.GetTileY(tile);
    local dx = 0;
    if (x < ax) dx = ax - x;
    else if (x >= ax + w) dx = x - (ax + w - 1);
    local dy = 0;
    if (y < ay) dy = ay - y;
    else if (y >= ay + h) dy = y - (ay + h - 1);
    if (dx + dy <= airportCoverage) continue;
    raw.append({
      tile = tile, value = val, dist = AIMap.DistanceManhattan(tile, town.tile), x = x, y = y
    });
  }
  raw.sort(OpexAirJoinedLoopOrder);
  local candidates = [];
  foreach (item in raw) {
    candidates.append({ tile = item.tile, value = item.value, dist = item.dist });
  }
  return candidates;
}

function OpexAirJoinedCandidatesSelect(minX, maxX, minY, maxY, town, paxCargo, coverage,
                                       airportCoverage, ax, ay, w, h, center) {
  return OpexAirJoinedCandidatesExact(minX, maxX, minY, maxY, town, paxCargo, coverage,
                                        airportCoverage, ax, ay, w, h, center);
}

