/* DOUBLE-GROW : seconde voie adjacente d'une ligne fret rentable EXISTANTE.
 * Geometrie par decalage de V190, sans A*, sans acces a _railSearch.
 * Toutes les emprises nouvelles restent disjointes de la voie, des quais et
 * du depot historiques. La ligne n'est promue qu'apres certification de la
 * flotte et de la circulation directionnelle par OpexDoubleGrowFleetFinalize.
 * Requiert builder_rail, rail_pair_geometry et v190_fix_directional.
 */
DOUBLE_GROW_GEOMETRY_REASON <- "";

function OpexDoubleGrowReject(reason, line = null)
{
  DOUBLE_GROW_GEOMETRY_REASON = reason;
  if (DECISION_LOG) OpexDecide("DOUBLE_GROW", "phase=geometry ok=0 reason=" + reason
      + " line=" + (line != null && ("lineId" in line) ? line.lineId : -1));
  return false;
}

/* Compteurs diagnostiques uniquement lorsque DECISION_LOG est arme.
 * Toutes les valeurs comptent des refus de candidats, jamais des lignes
 * construites ni des tuiles finalement presentes dans le monde. */
function OpexDoubleGrowDiagCount(diag, reason)
{
  if (diag != null) diag.rawset(reason, ((reason in diag) ? diag[reason] : 0) + 1);
  return false;
}

/* Les anciens motifs regroupaient plusieurs invariants sous clear_short
 * ou trace_window_fail. Garder ces compteurs historiques et memoriser le
 * PREMIER cas exact de chaque motif : aucun garde n'est assoupli. */
function OpexDoubleGrowDiagnosticReject(diag, reason, detail, index, tile)
{
  OpexDoubleGrowDiagCount(diag, reason);
  if (diag != null && !(reason + "_detail" in diag)) {
    diag.rawset(reason + "_detail", detail);
    diag.rawset(reason + "_idx", index);
    diag.rawset(reason + "_tile", tile == null ? -1 : tile);
  }
  return false;
}

function OpexDoubleGrowPlanLog(line, route, diag, ok)
{
  if (diag == null) return;
  local detail = "phase=plan ok=" + (ok ? 1 : 0)
      + " line=" + line.lineId + " route=" + route.len();
  foreach (key in ["a_raw", "b_raw", "a_end", "a_busy", "a_side",
                   "b_end", "b_busy", "b_side", "trace_attempt", "trace_null",
                   "structure_invalid", "clear_short", "clear_turn",
                   "clear_forbidden", "clear_repeat", "clear_pad",
                   "clear_occupied", "clear_terrain", "clear_structure",
                   "native_fail", "valid", "a_site_try", "b_site_try",
                   "a_site_bounds", "b_site_bounds", "a_site_occupied",
                   "b_site_occupied", "a_site_nonflat", "b_site_nonflat",
                   "a_site_lead", "b_site_lead", "a_site_rail",
                   "b_site_rail", "a_site_other", "b_site_other",
                   "a_site_join", "b_site_join", "a_site_err", "b_site_err",
                   "a_meta_bad", "b_meta_bad",
                   "a_site_accept", "b_site_accept",
                   "a_shifted", "b_shifted",
                   "trace_window_fail", "trace_start_mismatch",
                   "trace_end_mismatch", "trace_first_gap",
                   "trace_turn_gap", "trace_corner_gap",
                   "trace_structure_gap", "trace_bounds",
                   "trace_b_lead_gap", "trace_b_exit_gap",
                   "trace_dry_pass", "trace_dry_pass_structures",
                   "local_try", "local_nodes", "local_repaired",
                   "local_no_path", "local_native_fail",
                   "obstacle_eau", "obstacle_batiment", "obstacle_pente",
                   "obstacle_rail", "obstacle_gare", "obstacle_depot",
                   "obstacle_ouvrage", "obstacle_bounds", "obstacle_libre",
                   "site_outer_try", "site_outer_accept",
                   "outer_access_try", "outer_access_success",
                   "outer_access_fail", "outer_access_native_fail",
                   "trace_start_relocate", "trace_end_relocate",
                   "outer_access_projection_far"]) {
    detail += " " + key + "=" + (key in diag ? diag[key] : 0);
  }
  if ("trace_first_reason" in diag) detail += " trace_first_reason=" + diag.trace_first_reason
      + " trace_first_idx=" + diag.trace_first_idx
      + " trace_first_tile=" + diag.trace_first_tile;
  if ("trace_window_a" in diag) detail += " trace_window_a=" + diag.trace_window_a
      + " trace_window_b=" + diag.trace_window_b;
  if ("obstacle_first_kind" in diag)
    detail += " obstacle_first_kind=" + diag.obstacle_first_kind
        + " obstacle_first_tile=" + diag.obstacle_first_tile;
  foreach (prefix in ["access_a", "access_b"]) {
    if ((prefix + "_actual_exit") in diag) {
      detail += " " + prefix + "_actual_exit=" + diag[prefix + "_actual_exit"]
          + " " + prefix + "_actual_lead=" + diag[prefix + "_actual_lead"]
          + " " + prefix + "_virtual_exit=" + diag[prefix + "_virtual_exit"]
          + " " + prefix + "_virtual_lead=" + diag[prefix + "_virtual_lead"]
          + " " + prefix + "_projected_exit=" + diag[prefix + "_projected_exit"]
          + " " + prefix + "_projected_lead=" + diag[prefix + "_projected_lead"];
    }
  }
  foreach (reason in ["trace_window_fail", "trace_start_mismatch",
                       "trace_end_mismatch", "clear_short", "clear_forbidden"]) {
    if ((reason + "_detail") in diag) {
      detail += " " + reason + "_detail=" + diag[reason + "_detail"]
          + " " + reason + "_idx=" + diag[reason + "_idx"]
          + " " + reason + "_tile=" + diag[reason + "_tile"];
    }
  }
  OpexDecide("DOUBLE_GROW", detail);
}

function OpexDoubleGrowSiteBlocked(diag, prefix, tile, lead)
{
  OpexDoubleGrowDiagCount(diag, prefix + "_site_occupied");
  if (lead) OpexDoubleGrowDiagCount(diag, prefix + "_site_lead");
  OpexDoubleGrowObstacleDiag(diag, tile);
  if (AIMap.IsValidTile(tile) &&
      AITile.HasTransportType(tile, AITile.TRANSPORT_RAIL))
    OpexDoubleGrowDiagCount(diag, prefix + "_site_rail");
  else OpexDoubleGrowDiagCount(diag, prefix + "_site_other");
}

/* Classer l'obstacle reel avant tout chantier. Ne jamais demolir une
 * infrastructure preexistante pour faire passer le second corridor. */
function OpexDoubleGrowObstacleKind(tile)
{
  if (!AIMap.IsValidTile(tile)) return "bounds";
  if (AIRail.IsRailStationTile(tile)) return "gare";
  if (AIRail.IsRailDepotTile(tile)) return "depot";
  if (AIRail.IsRailTile(tile) ||
      AITile.HasTransportType(tile, AITile.TRANSPORT_RAIL)) return "rail";
  if (AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile))
    return "ouvrage";
  if (AITile.IsWaterTile(tile)) return "eau";
  if (!AITile.IsBuildable(tile)) return "batiment";
  if (AITile.GetSlope(tile) != AITile.SLOPE_FLAT) return "pente";
  return "libre";
}

function OpexDoubleGrowObstacleDiag(diag, tile)
{
  if (diag == null) return;
  local kind = OpexDoubleGrowObstacleKind(tile);
  OpexDoubleGrowDiagCount(diag, "obstacle_" + kind);
  if (!("obstacle_first_kind" in diag)) {
    diag.rawset("obstacle_first_kind", kind);
    diag.rawset("obstacle_first_tile", tile);
  }
}

/* V190FindParallelPlatformPlans sert aux gares AVANT construction : il
 * exige tout le quai et le lead strictement plats, sans explorer la moindre
 * translation le long de la gare. Une gare deja en service peut avoir une
 * maison, une pente ou une route sur l'une des deux bandes voisines.
 *
 * Repli differe : construire une plateforme à 1, puis éventuellement 2-3
 * cases de côté lorsque les bandes adjacentes sont occupées. La longueur
 * reste constante et seule une jointure native au StationID réel est admise.
 * Le raccord distant devra être certifié séparément, sans traverser voie1.
 * Chaque empreinte est vierge et testee sous AITestMode ; aucun terrassement,
 * demolition ou construction persistante n'intervient a ce stade. */
function OpexDoubleGrowDeferredPlatforms(platform, diag, prefix)
{
  local raw = OpexV190FindParallelPlatformPlans(platform, false, 1);
  if (diag != null) diag.rawset(prefix + "_raw", raw.len());
  local plans = [];
  foreach (p in raw) {
    p.rawset("axialShift", 0);
    p.rawset("lateralDist", 1);
    plans.append(p);
  }
  local existingId = AIStation.GetStationID(platform.anchor);
  /* Le finder V190 privilegie platform.stationId MEME si ce champ date
   * de la planification (STATION_NEW) et n'a jamais ete actualise apres
   * construction. Dans ce cas ses deux simulations echouent en tentant
   * de recreer la gare originale deja occupee. Ici l'ID est relu sur
   * la carte, jamais emprunte aux metadonnees en cache. */
  if (diag != null && ("stationId" in platform) &&
      platform.stationId != existingId)
    OpexDoubleGrowDiagCount(diag, prefix + "_meta_bad");
  if (!AIStation.IsValidStation(existingId)) return plans;
  local outwardX = AIMap.GetTileX(platform.lead) - AIMap.GetTileX(platform.station_exit);
  local outwardY = AIMap.GetTileY(platform.lead) - AIMap.GetTileY(platform.station_exit);
  if (abs(outwardX) + abs(outwardY) != 1) return plans;
  local lateralX = platform.direction == AIRail.RAILTRACK_NE_SW ? 0 : 1;
  local lateralY = platform.direction == AIRail.RAILTRACK_NE_SW ? 1 : 0;
  local maxShift = min(3, platform.length - 1);
  for (local dist = 1; dist <= 3; dist++) {
    for (local shift = 0; shift <= maxShift; shift++) {
      foreach (flip in [-1, 1]) {
      local dx = dist * flip * lateralX + shift * outwardX;
      local dy = dist * flip * lateralY + shift * outwardY;
      if (dist > 1) OpexDoubleGrowDiagCount(diag, "site_outer_try");
      local anchor = OpexV190MakeTile(platform.anchor, dx, dy);
      local stationExit = OpexV190MakeTile(platform.station_exit, dx, dy);
      local lead = OpexV190MakeTile(platform.lead, dx, dy);
      OpexDoubleGrowDiagCount(diag, prefix + "_site_try");
      if (anchor == null || stationExit == null || lead == null) {
        OpexDoubleGrowDiagCount(diag, prefix + "_site_bounds"); continue;
      }
      local duplicate = false;
      foreach (p in plans) if (p.anchor == anchor) duplicate = true;
      if (duplicate) continue;
      local usable = AIMap.DistanceManhattan(stationExit, lead) == 1;
      local nonflat = false;
      if (usable) {
        if (!AITile.IsBuildable(lead)) {
          OpexDoubleGrowSiteBlocked(diag, prefix, lead, true);
          usable = false;
        }
        else if (AITile.GetSlope(lead) != AITile.SLOPE_FLAT) nonflat = true;
      }
      for (local j = 0; j < platform.length && usable; j++) {
        local t = OpexV190MakeTile(anchor, j * outwardX *
            (platform.station_exit != platform.anchor ? 1 : -1),
            j * outwardY * (platform.station_exit != platform.anchor ? 1 : -1));
        if (t == null || t != anchor + j * platform.step) {
          OpexDoubleGrowDiagCount(diag, prefix + "_site_bounds");
          usable = false;
        } else if (!AITile.IsBuildable(t)) {
          OpexDoubleGrowSiteBlocked(diag, prefix, t, false);
          usable = false;
        }
        else if (AITile.GetSlope(t) != AITile.SLOPE_FLAT) nonflat = true;
      }
      if (!usable) continue;
      if (nonflat) OpexDoubleGrowDiagCount(diag, prefix + "_site_nonflat");
      local joins = false;
      {
        local shield = AIAccounting();
        local test = AITestMode();
        joins = AIRail.BuildRailStation(anchor, platform.direction, 1,
                                       platform.length, existingId);
      }
      if (!joins) {
        OpexDoubleGrowDiagCount(diag, prefix + "_site_join");
        if (diag != null) diag.rawset(prefix + "_site_err", AIError.GetLastError());
        continue;
      }
      plans.append({ anchor = anchor, station_exit = stationExit, lead = lead,
                     direction = platform.direction, step = platform.step,
                     length = platform.length, axialShift = shift,
                     lateralDist = dist });
      OpexDoubleGrowDiagCount(diag, prefix + "_site_accept");
      if (dist > 1) OpexDoubleGrowDiagCount(diag, "site_outer_accept");
      if (shift > 0) OpexDoubleGrowDiagCount(diag, prefix + "_shifted");
      }
    }
  }
  return plans;
}

/* Interface V190 limitée à la voie parallèle de distance UN. Les quais
 * physiques à deux/trois cases restent réellement distants et leurs deux
 * derniers tronçons seront raccordés par OpexDoubleGrowRepairSlice ; ces
 * sorties virtuelles ne sont JAMAIS construites comme des gares. */
function OpexDoubleGrowVirtualAccess(plan, original)
{
  local dist = ("lateralDist" in plan) ? plan.lateralDist : 1;
  if (dist == 1) return plan;
  if (dist < 2 || dist > 3) return null;
  local lateralX = original.direction == AIRail.RAILTRACK_NE_SW ? 0 : 1;
  local lateralY = original.direction == AIRail.RAILTRACK_NE_SW ? 1 : 0;
  local magnitude = lateralX != 0 ?
      AIMap.GetTileX(plan.anchor) - AIMap.GetTileX(original.anchor) :
      AIMap.GetTileY(plan.anchor) - AIMap.GetTileY(original.anchor);
  if (abs(magnitude) != dist) return null;
  local offset = magnitude > 0 ? -(dist - 1) : (dist - 1);
  local result = clone plan;
  result.station_exit = OpexV190MakeTile(plan.station_exit,
                                        offset * lateralX, offset * lateralY);
  result.lead = OpexV190MakeTile(plan.lead,
                                offset * lateralX, offset * lateralY);
  return result.station_exit != null && result.lead != null ? result : null;
}

/* Reprendre V190 au niveau des VRAIES sorties de quai, pas des sorties
 * virtuelles. V190 suit toutes les cases de sa route d'entree : avec un
 * quai avance, un virage ou un ouvrage dans la portion a couper en aval
 * faisait echouer le trace avant le TrimTrace. Une sous-route primaire
 * n'est autorisee que si les deux quais neufs sont exactement a une tuile
 * laterale de ses deux premiers et deux derniers points. Ni saut oblique
 * ni dogleg en entree de quai n'est ajoute ; aucun rail primaire ne bouge. */
function OpexDoubleGrowTraceWindow(route, planA2, planB2, side, diag,
                                   projection = null)
{
  local shiftA = ("axialShift" in planA2) ? planA2.axialShift : 0;
  local shiftB = ("axialShift" in planB2) ? planB2.axialShift : 0;
  local start = shiftA;
  local end = route.len() - 1 - shiftB;
  if (start < 0 || end >= route.len() || end - start < 3) {
    OpexDoubleGrowDiagnosticReject(diag, "trace_window_fail",
        "window_indices_A" + shiftA + "_B" + shiftB
          + "_N" + route.len(), start, null);
    return null;
  }
  local jumpA = AIMap.DistanceManhattan(route[start], route[start + 1]);
  local jumpB = AIMap.DistanceManhattan(route[end - 1], route[end]);
  if (jumpA != 1 || jumpB != 1) {
    OpexDoubleGrowDiagnosticReject(diag, "trace_window_fail",
        "window_jump_A" + jumpA + "_B" + jumpB
          + "_shiftA" + shiftA + "_shiftB" + shiftB,
        jumpA != 1 ? start : end - 1,
        jumpA != 1 ? route[start] : route[end - 1]);
    return null;
  }
  local ax = AIMap.GetTileX(route[start + 1]) - AIMap.GetTileX(route[start]);
  local ay = AIMap.GetTileY(route[start + 1]) - AIMap.GetTileY(route[start]);
  local perpA = OpexV190GetPerp(ax, ay, side);
  local expectedAExit = OpexV190MakeTile(route[start], perpA.x, perpA.y);
  local expectedALead = OpexV190MakeTile(route[start + 1], perpA.x, perpA.y);
  if (expectedAExit != planA2.station_exit || expectedALead != planA2.lead) {
    /* La translation du quai suit son AXE initial, pas les premiers
     * virages de la voie primaire. Pour shift>0 la projection du corridor
     * a l'index shift differe souvent de la sortie virtuelle du quai.
     * Ne PAS imposer leur egalite : le petit acces sera cherche et teste
     * physiquement sur une voie independante, sans modifier route1. */
    if (shiftA == 0 || expectedAExit == null || expectedALead == null ||
        AIMap.DistanceManhattan(expectedALead, planA2.lead) > 9 ||
        AIMap.DistanceManhattan(expectedAExit, planA2.station_exit) > 9) {
      OpexDoubleGrowDiagnosticReject(diag, "trace_start_mismatch",
          "shiftA" + shiftA + "_shiftB" + shiftB + "_side" + side
            + "_expectedExit" + (expectedAExit == null ? -1 : expectedAExit)
            + "_actualExit" + planA2.station_exit
            + "_expectedLead" + (expectedALead == null ? -1 : expectedALead)
            + "_actualLead" + planA2.lead, start, route[start]);
      return null;
    }
    OpexDoubleGrowDiagCount(diag, "trace_start_relocate");
  }
  local bx = AIMap.GetTileX(route[end]) - AIMap.GetTileX(route[end - 1]);
  local by = AIMap.GetTileY(route[end]) - AIMap.GetTileY(route[end - 1]);
  local perpB = OpexV190GetPerp(bx, by, side);
  local expectedBLead = OpexV190MakeTile(route[end - 1], perpB.x, perpB.y);
  local expectedBExit = OpexV190MakeTile(route[end], perpB.x, perpB.y);
  if (expectedBLead != planB2.lead || expectedBExit != planB2.station_exit) {
    if (shiftB == 0 || expectedBExit == null || expectedBLead == null ||
        AIMap.DistanceManhattan(expectedBLead, planB2.lead) > 9 ||
        AIMap.DistanceManhattan(expectedBExit, planB2.station_exit) > 9) {
      OpexDoubleGrowDiagnosticReject(diag, "trace_end_mismatch",
          "shiftA" + shiftA + "_shiftB" + shiftB + "_side" + side
            + "_expectedExit" + (expectedBExit == null ? -1 : expectedBExit)
            + "_actualExit" + planB2.station_exit
            + "_expectedLead" + (expectedBLead == null ? -1 : expectedBLead)
            + "_actualLead" + planB2.lead, end, route[end]);
      return null;
    }
    OpexDoubleGrowDiagCount(diag, "trace_end_relocate");
  }
  if (projection != null) {
    projection.rawset("aExit", expectedAExit);
    projection.rawset("aLead", expectedALead);
    projection.rawset("bExit", expectedBExit);
    projection.rawset("bLead", expectedBLead);
  }
  if (diag != null) {
    diag.rawset("trace_window_a", start);
    diag.rawset("trace_window_b", shiftB);
  }
  if (start == 0 && end == route.len() - 1) return route;
  local subroute = [];
  for (local i = start; i <= end; i++) subroute.append(route[i]);
  return subroute;
}

/* Autopsie SANS effet de bord des retours null de V190. Rejoue ses seuls
 * controles de continuité geometrique (pas de BuildBridge/BuildTunnel),
 * avec le MEME index i et la meme derniere tuile. Les ouvrages non testés
 * sont distingues de tout echec de coude ou de gorge. Ne jamais utiliser ce
 * resultat pour autoriser un build : seul le vrai traceur + test natif le
 * peuvent. */
function OpexDoubleGrowTraceDryIssue(tiles1, planA2, planB2, side)
{
  if (tiles1 == null || tiles1.len() < 3)
    return { reason = "trace_window_fail", idx = -1, tile = -1 };
  local top = planA2.lead;
  local structures = 0;
  for (local i = 1; i < tiles1.len() - 1; i++) {
    local prev1 = tiles1[i - 1];
    local cur1 = tiles1[i];
    local next1 = tiles1[i + 1];
    if (AIMap.DistanceManhattan(cur1, next1) > 1) {
      local dx = AIMap.GetTileX(next1) - AIMap.GetTileX(cur1);
      local dy = AIMap.GetTileY(next1) - AIMap.GetTileY(cur1);
      local ux = dx == 0 ? 0 : (dx > 0 ? 1 : -1);
      local uy = dy == 0 ? 0 : (dy > 0 ? 1 : -1);
      local perp = OpexV190GetPerp(ux, uy, side);
      local start2 = OpexV190MakeTile(cur1, perp.x, perp.y);
      local end2 = OpexV190MakeTile(next1, perp.x, perp.y);
      if (start2 == null || end2 == null)
        return { reason = "trace_bounds", idx = i, tile = cur1 };
      if (top != start2 && AIMap.DistanceManhattan(top, start2) != 1)
        return { reason = "trace_structure_gap", idx = i, tile = cur1 };
      top = end2;
      structures++;
      continue;
    }
    local manhPrev = AIMap.DistanceManhattan(prev1, cur1);
    local uxIn = AIMap.GetTileX(cur1) - AIMap.GetTileX(prev1);
    local uyIn = AIMap.GetTileY(cur1) - AIMap.GetTileY(prev1);
    if (manhPrev > 1) {
      uxIn = uxIn == 0 ? 0 : (uxIn > 0 ? 1 : -1);
      uyIn = uyIn == 0 ? 0 : (uyIn > 0 ? 1 : -1);
    }
    local uxOut = AIMap.GetTileX(next1) - AIMap.GetTileX(cur1);
    local uyOut = AIMap.GetTileY(next1) - AIMap.GetTileY(cur1);
    local inPerp = OpexV190GetPerp(uxIn, uyIn, side);
    local outPerp = OpexV190GetPerp(uxOut, uyOut, side);
    local pts = [];
    if (uxIn == uxOut && uyIn == uyOut) {
      pts.append(OpexV190MakeTile(cur1, inPerp.x, inPerp.y));
    } else {
      local cross = uxIn * uyOut - uyIn * uxOut;
      if (cross == side) {
        pts.append(OpexV190MakeTile(cur1, inPerp.x + outPerp.x,
                                          inPerp.y + outPerp.y));
      } else {
        pts.append(OpexV190MakeTile(cur1, inPerp.x, inPerp.y));
        pts.append(OpexV190MakeTile(cur1, inPerp.x + outPerp.x,
                                          inPerp.y + outPerp.y));
        pts.append(OpexV190MakeTile(cur1, outPerp.x, outPerp.y));
      }
    }
    foreach (p in pts) {
      if (p == null) return { reason = "trace_bounds", idx = i, tile = cur1 };
      if (top == p) continue;
      if (AIMap.DistanceManhattan(top, p) != 1)
        return { reason = i == 1 ? "trace_first_gap" :
                   (pts.len() > 1 ? "trace_corner_gap" : "trace_turn_gap"),
                 idx = i, tile = cur1 };
      top = p;
    }
  }
  if (top != planB2.lead) {
    if (AIMap.DistanceManhattan(top, planB2.lead) != 1)
      return { reason = "trace_b_lead_gap", idx = tiles1.len() - 2,
               tile = tiles1[tiles1.len() - 2] };
    top = planB2.lead;
  }
  if (top != planB2.station_exit &&
      AIMap.DistanceManhattan(top, planB2.station_exit) != 1)
    return { reason = "trace_b_exit_gap", idx = tiles1.len() - 1,
             tile = tiles1[tiles1.len() - 1] };
  /* Le vrai V190 ne sonde aucun ouvrage quand v233Context est fourni.
   * S'il renvoie null malgre ce prevol, il ne s'agit PAS d'un refus natif. */
  return { reason = structures > 0 ? "trace_dry_pass_structures" :
           "trace_dry_pass", idx = -1, tile = -1 };
}

function OpexDoubleGrowTraceDiag(diag, issue)
{
  OpexDoubleGrowDiagCount(diag, issue.reason);
  if (diag != null && !("trace_first_reason" in diag)) {
    diag.rawset("trace_first_reason", issue.reason);
    diag.rawset("trace_first_idx", issue.idx);
    diag.rawset("trace_first_tile", issue.tile);
  }
}

/* Refuser les traces approximatives : OpexTraceTrackTiles peut s'arreter sur
 * un autre quai du meme StationID et choisit la premiere branche trouvee.
 * V271 impose la sortie exacte et refuse les embranchements ambigus. */
function OpexDoubleGrowPrimaryRoute(line)
{
  local planA = line.platformA;
  local planB = line.platformB;
  if (planA == null || planB == null || !("lead" in planA) ||
      !("station_exit" in planA) || !("station_exit" in planB) ||
      !("lead" in planB) || !("anchor" in planA) ||
      !("anchor" in planB) || !("step" in planA) ||
      !("step" in planB) || !("length" in planA) ||
      !("length" in planB) || !("direction" in planA) ||
      !("direction" in planB)) return null;
  if (planA.length < 2 || planB.length < 2 ||
      AIMap.DistanceManhattan(planA.station_exit, planA.lead) != 1 ||
      AIMap.DistanceManhattan(planB.station_exit, planB.lead) != 1 ||
      AIStation.GetStationID(planA.station_exit) != AIStation.GetStationID(line.stationA) ||
      AIStation.GetStationID(planB.station_exit) != AIStation.GetStationID(line.stationB)) return null;
  local route = OpexV271TraceTrackTiles(planA.station_exit, planA.lead,
                                      planB.station_exit, true);
  if (route == null || route.len() < 36 ||
      route[0] != planA.station_exit || route[1] != planA.lead ||
      route[route.len() - 2] != planB.lead ||
      route[route.len() - 1] != planB.station_exit) return null;
  return route;
}

/* Verifie AUSSI les structures : AreTilesConnected ne s'applique pas aux
 * deux extremites non adjacentes d'un pont ou d'un tunnel. Aucun usage de
 * la presence des signaux comme preuve de connectivite. */
function OpexDoubleGrowVerifyRoute(tiles, planA, planB)
{
  if (tiles == null || tiles.len() < 3 || planA == null || planB == null ||
      tiles[0] != planA.station_exit || tiles[tiles.len() - 1] != planB.station_exit)
    return false;
  local own = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  foreach (plan in [planA, planB]) {
    for (local j = 0; j < plan.length; j++) {
      local t = plan.anchor + j * plan.step;
      if (!AIRail.IsRailStationTile(t) || AITile.GetOwner(t) != own) return false;
    }
  }
  local last = tiles.len() - 1;
  if (!OpexRailEndConnected(tiles[0], tiles[1], tiles[2], "A") ||
      !OpexRailEndConnected(tiles[last], tiles[last - 1], tiles[last - 2], "B"))
    return false;
  for (local i = 1; i < last; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    if (!AIMap.IsValidTile(cur) || AITile.GetOwner(cur) != own) return false;
    local dPrev = AIMap.DistanceManhattan(prev, cur);
    local dNext = AIMap.DistanceManhattan(cur, next);
    if (dPrev > 1) {
      if (!(AIBridge.IsBridgeTile(cur) && AIBridge.GetOtherBridgeEnd(cur) == prev) &&
          !(AITunnel.IsTunnelTile(cur) && AITunnel.GetOtherTunnelEnd(cur) == prev))
        return false;
    } else if (dNext > 1) {
      if (!(AIBridge.IsBridgeTile(cur) && AIBridge.GetOtherBridgeEnd(cur) == next) &&
          !(AITunnel.IsTunnelTile(cur) && AITunnel.GetOtherTunnelEnd(cur) == next))
        return false;
    } else if (!AIRail.AreTilesConnected(prev, cur, next)) return false;
  }
  return true;
}

/* La geometrie V190 suit chaque coude. Verifier en plus les couples de
 * trackbits (OpenTTD forbid_90_deg) qui peuvent etre physiquement joints
 * mais inaccessibles par le pathfinder des trains. Les sauts d'ouvrage
 * interrompent la comparaison des couples de tuiles adjacentes. */
function OpexDoubleGrowTurnsSafe(tiles)
{
  local previousBit = 0;
  for (local i = 1; i < tiles.len() - 1; i++) {
    local bit = OpexV190Fix2TrackBit(tiles[i - 1], tiles[i], tiles[i + 1]);
    if (bit == 0) {
      if (AIMap.DistanceManhattan(tiles[i - 1], tiles[i]) == 1 &&
          AIMap.DistanceManhattan(tiles[i], tiles[i + 1]) == 1) return false;
      previousBit = 0;
      continue;
    }
    if ((previousBit == 1 && bit == 2) || (previousBit == 2 && bit == 1) ||
        ((previousBit == 4 || previousBit == 8) && (bit == 16 || bit == 32)) ||
        ((previousBit == 16 || previousBit == 32) && (bit == 4 || bit == 8)))
      return false;
    previousBit = bit;
  }
  return true;
}

function OpexDoubleGrowClear(tiles, structures, forbidden, planA2, planB2,
                             diag = null, primaryRoute = null, depot1 = null)
{
  if (tiles == null)
    return OpexDoubleGrowDiagnosticReject(diag, "clear_short",
        "null_trace", -1, null);
  if (tiles.len() < 36)
    return OpexDoubleGrowDiagnosticReject(diag, "clear_short",
        "length_" + tiles.len(), -1, null);
  if (tiles[0] != planA2.station_exit)
    return OpexDoubleGrowDiagnosticReject(diag, "clear_short",
        "station_A_exit", 0, tiles[0]);
  if (tiles[1] != planA2.lead)
    return OpexDoubleGrowDiagnosticReject(diag, "clear_short",
        "station_A_lead", 1, tiles[1]);
  if (tiles[tiles.len() - 2] != planB2.lead)
    return OpexDoubleGrowDiagnosticReject(diag, "clear_short",
        "station_B_lead", tiles.len() - 2, tiles[tiles.len() - 2]);
  if (tiles[tiles.len() - 1] != planB2.station_exit)
    return OpexDoubleGrowDiagnosticReject(diag, "clear_short",
        "station_B_exit", tiles.len() - 1, tiles[tiles.len() - 1]);
  local issue = OpexRailPathGeometryIssue(tiles, planA2, planB2);
  if (issue != null)
    return OpexDoubleGrowDiagnosticReject(diag, "clear_short",
        "geometry_" + issue.kind, -1, issue.tile);
  if (!OpexDoubleGrowTurnsSafe(tiles))
    return OpexDoubleGrowDiagCount(diag, "clear_turn");
  local seen = {};
  for (local index = 0; index < tiles.len(); index++) {
    local tile = tiles[index];
    if (!AIMap.IsValidTile(tile))
      return OpexDoubleGrowDiagnosticReject(diag, "clear_forbidden",
          "invalid_tile", index, tile);
    if (tile in forbidden) {
      local kind = "protected_other";
      if (depot1 != null && tile == depot1) {
        kind = "primary_depot";
      } else if (depot1 != null &&
                 tile == AIRail.GetRailDepotFrontTile(depot1)) {
        kind = "primary_depot_front";
      } else if (AIRail.IsRailStationTile(tile)) {
        kind = "primary_station";
      } else if (primaryRoute != null) {
        foreach (firstTile in primaryRoute)
          if (firstTile == tile) { kind = "primary_track"; break; }
      }
      return OpexDoubleGrowDiagnosticReject(diag, "clear_forbidden",
          kind, index, tile);
    }
    if (tile in seen) return OpexDoubleGrowDiagCount(diag, "clear_repeat");
    seen[tile] <- true;
  }
  /* Aucun morceau du corridor ne doit traverser les autres cases des deux
   * quais neufs : elles seront transformees en gare apres le devis. */
  foreach (plan in [planA2, planB2]) {
    for (local j = 0; j < plan.length; j++) {
      local t = plan.anchor + j * plan.step;
      if (t != plan.station_exit && (t in seen))
        return OpexDoubleGrowDiagCount(diag, "clear_pad");
    }
  }
  for (local i = 1; i < tiles.len() - 1; i++) {
    local cur = tiles[i];
    if (AIRail.IsRailTile(cur) || AIRail.IsRailStationTile(cur) ||
        AIRail.IsRailDepotTile(cur) || AIBridge.IsBridgeTile(cur) ||
        AITunnel.IsTunnelTile(cur) ||
        AITile.HasTransportType(cur, AITile.TRANSPORT_RAIL))
      return OpexDoubleGrowDiagCount(diag, "clear_occupied");
    if (!AITile.IsBuildable(cur))
      return OpexDoubleGrowDiagCount(diag, "clear_terrain");
    if (i + 1 < tiles.len()) {
      local next = tiles[i + 1];
      if (AIMap.DistanceManhattan(cur, next) > 1 &&
          OpexPlannedStructureKind(structures, cur, next) == null)
        return OpexDoubleGrowDiagCount(diag, "clear_structure");
    }
  }
  return true;
}

/* Lors d'un repli local, une structure V190 n'est conservee QUE si ses deux
 * extremites sont encore consecutives dans le nouveau trace. Le BFS ne
 * pretend jamais construire un franchissement sans ouvrage explicite. */
function OpexDoubleGrowKeepStructures(tiles, structures)
{
  local kept = [];
  foreach (s in structures) {
    for (local i = 0; i + 1 < tiles.len(); i++) {
      if (tiles[i] == s.from && tiles[i + 1] == s.to) {
        kept.append(s);
        break;
      }
    }
  }
  return kept;
}

/* Un A* LOCAL borne a un troncon d'environ 8..24 cases ; jamais de
 * recherche A* globale ni de second etat _railSearch. Il contourne les
 * gares/depots/rails existants sans construire sur ces cases. Les 2
 * extremites de la sous-route sont conservees, le reste du trace V190
 * n'est pas modifie. La validation de TOUT le parcours est obligatoire. */
function OpexDoubleGrowRepairSlice(tiles, structures, forbidden, planA2, planB2,
                                   primaryRoute, depot1, obstacleIndex, diag)
{
  if (tiles == null || obstacleIndex <= 0 || obstacleIndex >= tiles.len() - 1)
    return null;
  local last = tiles.len() - 1;
  foreach (radius in [5, 8, 12]) {
    local left = max(1, obstacleIndex - radius);
    local right = min(last - 1, obstacleIndex + radius);
    if (right - left < 2 || left >= right ||
        tiles[left] in forbidden || tiles[right] in forbidden ||
        AIMap.DistanceManhattan(tiles[left - 1], tiles[left]) != 1 ||
        AIMap.DistanceManhattan(tiles[right], tiles[right + 1]) != 1)
      continue;
    OpexDoubleGrowDiagCount(diag, "local_try");
    local blocked = clone forbidden;
    for (local k = 0; k < left; k++) blocked[tiles[k]] <- true;
    for (local k = right + 1; k < tiles.len(); k++) blocked[tiles[k]] <- true;
    /* Le nouveau raccord ne traverse aucun quai, y compris les parties
     * de gare qui ne figurent pas dans tiles1/tiles2. */
    foreach (platform in [planA2, planB2])
      for (local k = 0; k < platform.length; k++)
        blocked[platform.anchor + k * platform.step] <- true;
    local goal = tiles[right];
    local before = tiles[left - 1];
    local start = tiles[left];
    local frontier = [{ path = [before, start], g = 0,
                         f = 2 * AIMap.DistanceManhattan(start, goal) }];
    local best = {};
    local expanded = 0;
    local completed = 0;
    while (frontier.len() > 0 && expanded < 420 && completed < 12) {
      local bestIndex = 0;
      for (local j = 1; j < frontier.len(); j++)
        if (frontier[j].f < frontier[bestIndex].f) bestIndex = j;
      local state = frontier[bestIndex];
      frontier.remove(bestIndex);
      expanded++;
      OpexDoubleGrowDiagCount(diag, "local_nodes");
      local path = state.path;
      local cur = path[path.len() - 1];
      local prev = path[path.len() - 2];
      if (cur == goal) {
        completed++;
        local joined = [];
        for (local k = 0; k < left; k++) joined.append(tiles[k]);
        for (local k = 1; k < path.len(); k++) joined.append(path[k]);
        for (local k = right + 1; k < tiles.len(); k++) joined.append(tiles[k]);
        local kept = OpexDoubleGrowKeepStructures(joined, structures);
        /* Deux reparations peuvent etre necessaires sur la MEME bande :
         * B end_jump puis A depot. Un controle global premature refuserait
         * le premier detour parce que l'autre obstacle subsiste. Ne
         * valider qu'apres le dernier raccord, en OpexDoubleGrowPlan. */
        if (!OpexDoubleGrowTurnsSafe(joined)) continue;
        local endJump = OpexRailPathGeometryIssue(joined, planA2, planB2);
        if (obstacleIndex == last - 1 && endJump != null &&
            endJump.kind == "end_jump") continue;
        local pathClear = true;
        for (local k = 2; k < path.len(); k++) {
          local tile = path[k];
          if (tile in forbidden || (tile != goal && !AITile.IsBuildable(tile))) {
            pathClear = false;
            break;
          }
        }
        if (!pathClear) continue;
        OpexDoubleGrowDiagCount(diag, "local_repaired");
        return { tiles = joined, structures = kept };
      }
      if (state.g >= (right - left + 14)) continue;
      foreach (offset in [{ x = 1, y = 0 }, { x = -1, y = 0 },
                          { x = 0, y = 1 }, { x = 0, y = -1 }]) {
        local next = OpexV190MakeTile(cur, offset.x, offset.y);
        if (next == null || next == prev ||
            (next in blocked && next != goal)) continue;
        if (next != goal && !AITile.IsBuildable(next)) {
          OpexDoubleGrowObstacleDiag(diag, next);
          continue;
        }
        if (next != goal && (AIRail.IsRailTile(next) ||
            AIRail.IsRailStationTile(next) || AIRail.IsRailDepotTile(next) ||
            AIBridge.IsBridgeTile(next) || AITunnel.IsTunnelTile(next) ||
            AITile.HasTransportType(next, AITile.TRANSPORT_RAIL))) {
          OpexDoubleGrowObstacleDiag(diag, next);
          continue;
        }
        local repeated = false;
        foreach (old in path) if (old == next) { repeated = true; break; }
        if (repeated) continue;
        local guide = 999999;
        for (local k = left; k <= right; k++)
          guide = min(guide, AIMap.DistanceManhattan(next, tiles[k]));
        if (guide > 5) continue;
        if (path.len() >= 3 &&
            !OpexDoubleGrowTurnsSafe([path[path.len() - 3],
                                      prev, cur, next])) continue;
        local g = state.g + 1 + (guide > 1 ? guide - 1 : 0);
        local key = cur + ":" + next;
        if (key in best && best[key] <= g) continue;
        best.rawset(key, g);
        local extended = clone path;
        extended.append(next);
        frontier.append({ path = extended, g = g,
                          f = g + 2 * AIMap.DistanceManhattan(next, goal) });
      }
    }
  }
  OpexDoubleGrowDiagCount(diag, "local_no_path");
  return null;
}

/* Priorite a une sortie d'ouvrage directement vers le lead B, puis a une
 * collision avec une infrastructure protegee. Il ne s'agit jamais d'une
 * autorisation de poser une voie2 sur le depot1. */
function OpexDoubleGrowRepairIndex(tiles, forbidden, planA2, planB2)
{
  if (tiles == null || tiles.len() < 5) return -1;
  local issue = OpexRailPathGeometryIssue(tiles, planA2, planB2);
  if (issue != null && issue.kind == "end_jump") return tiles.len() - 2;
  for (local i = 1; i < tiles.len() - 1; i++)
    if (tiles[i] in forbidden) return i;
  return -1;
}

/* Acces de quai a 2/3 cases : le coeur V190 reste a une seule case de
 * la primaire. Replacer les sorties virtuelles par les VRAIES sorties de
 * gare puis reconstruire exclusivement la courte gorge secondaire. Faire
 * B avant A permet de certifier chaque raccord a partir du trace intact
 * a l'autre extremite. En cas de doute, aucune geometrie n'est retournee. */
function OpexDoubleGrowOuterAccess(tiles, structures, planA2, planB2,
                                   forbidden, route, depot1, diag,
                                   needsA = false, needsB = false)
{
  local distA = ("lateralDist" in planA2) ? planA2.lateralDist : 1;
  local distB = ("lateralDist" in planB2) ? planB2.lateralDist : 1;
  if (distA == 1 && distB == 1 && !needsA && !needsB)
    return { tiles = tiles, structures = structures };
  local working = clone tiles;
  local kept = structures;
  OpexDoubleGrowDiagCount(diag, "outer_access_try");
  if (working.len() < 16) return null;
  if (distB > 1 || needsB) {
    local last = working.len() - 1;
    working[last - 1] = planB2.lead;
    working[last] = planB2.station_exit;
    local access = OpexDoubleGrowRepairSlice(working, kept, forbidden, planA2,
                                            planB2, route, depot1, last - 2, diag);
    if (access == null) {
      OpexDoubleGrowDiagCount(diag, "outer_access_fail");
      return null;
    }
    working = access.tiles;
    kept = access.structures;
  }
  if (distA > 1 || needsA) {
    working[0] = planA2.station_exit;
    working[1] = planA2.lead;
    local access = OpexDoubleGrowRepairSlice(working, kept, forbidden, planA2,
                                            planB2, route, depot1, 2, diag);
    if (access == null) {
      OpexDoubleGrowDiagCount(diag, "outer_access_fail");
      return null;
    }
    working = access.tiles;
    kept = access.structures;
  }
  if (!OpexDoubleGrowClear(working, kept, forbidden, planA2, planB2,
                           null, route, depot1)) {
    OpexDoubleGrowDiagCount(diag, "outer_access_fail");
    return null;
  }
  OpexDoubleGrowDiagCount(diag, "outer_access_success");
  return { tiles = working, structures = kept };
}

/* La bande conserve un decalage d'UNE case depuis la voie1. Les quais
 * peuvent etre avances de 1..3 cases sur la bande, sans dogleg ni A*.
 * Le depot1 et sa sortie ne sont jamais des candidats pour la voie2. */
function OpexDoubleGrowPlan(line, route)
{
  local a = line.platformA;
  local b = line.platformB;
  local forbidden = {};
  foreach (tile in route) forbidden[tile] <- true;
  foreach (plan in [a, b]) {
    for (local i = 0; i < plan.length; i++) forbidden[plan.anchor + i * plan.step] <- true;
  }
  forbidden[line.depot] <- true;
  local front = AIRail.GetRailDepotFrontTile(line.depot);
  if (AIMap.IsValidTile(front)) forbidden[front] <- true;

  local start = route[0];
  local lead = route[1];
  local end = route[route.len() - 1];
  local beforeEnd = route[route.len() - 2];
  local dxA = AIMap.GetTileX(lead) - AIMap.GetTileX(start);
  local dyA = AIMap.GetTileY(lead) - AIMap.GetTileY(start);
  local dxB = AIMap.GetTileX(end) - AIMap.GetTileX(beforeEnd);
  local dyB = AIMap.GetTileY(end) - AIMap.GetTileY(beforeEnd);
  local diag = DECISION_LOG ? {} : null;
  local plansA = OpexDoubleGrowDeferredPlatforms(a, diag, "a");
  local plansB = OpexDoubleGrowDeferredPlatforms(b, diag, "b");
  foreach (pA in plansA) {
    if (!OpexSameStationEnd(pA, a)) {
      OpexDoubleGrowDiagCount(diag, "a_end"); continue;
    }
    if (OpexPlanHitsSet(pA, forbidden)) {
      OpexDoubleGrowDiagCount(diag, "a_busy"); continue;
    }
    local pads = clone forbidden;
    pads[pA.lead] <- true;
    for (local j = 0; j < pA.length; j++) pads[pA.anchor + j * pA.step] <- true;
    local oxA = AIMap.GetTileX(pA.station_exit) - AIMap.GetTileX(start);
    local oyA = AIMap.GetTileY(pA.station_exit) - AIMap.GetTileY(start);
    local crossA = dxA * oyA - dyA * oxA;
    local distA = ("lateralDist" in pA) ? pA.lateralDist : 1;
    if (abs(crossA) != distA) {
      OpexDoubleGrowDiagCount(diag, "a_side"); continue;
    }
    local side = crossA > 0 ? 1 : -1;
    local virtualA = OpexDoubleGrowVirtualAccess(pA, a);
    if (virtualA == null) {
      OpexDoubleGrowDiagCount(diag, "a_side"); continue;
    }
    foreach (pB in plansB) {
      if (!OpexSameStationEnd(pB, b)) {
        OpexDoubleGrowDiagCount(diag, "b_end"); continue;
      }
      if (OpexPlanHitsSet(pB, pads)) {
        OpexDoubleGrowDiagCount(diag, "b_busy"); continue;
      }
      local oxB = AIMap.GetTileX(pB.station_exit) - AIMap.GetTileX(end);
      local oyB = AIMap.GetTileY(pB.station_exit) - AIMap.GetTileY(end);
      local crossB = dxB * oyB - dyB * oxB;
      local distB = ("lateralDist" in pB) ? pB.lateralDist : 1;
      /* Le decalage axial du quai B modifie oxB/oyB, mais pas le produit
       * vectoriel lateral : il doit rester du MEME cote de A vers B. */
      /* Le contrat historique garde le test exact pour une seule case.
       * Les accès plus loin exigent la MEME orientation et leur distance. */
      if ((distB == 1 && dxB * oyB - dyB * oxB != side) ||
          (distB > 1 && crossB != side * distB)) {
        OpexDoubleGrowDiagCount(diag, "b_side"); continue;
      }
      local virtualB = OpexDoubleGrowVirtualAccess(pB, b);
      if (virtualB == null) {
        OpexDoubleGrowDiagCount(diag, "b_side"); continue;
      }
      local projection = {};
      local window = OpexDoubleGrowTraceWindow(route, virtualA, virtualB,
                                               side, diag, projection);
      if (window == null) continue;
      /* V190 recoit les sorties PROJETEES sur la voie1 a l'index de la
       * fenetre. Les vraies sorties pA/pB restent intactes : seule
       * OpexDoubleGrowOuterAccess peut les raccorder et les certifier. */
      local traceA = clone virtualA;
      local traceB = clone virtualB;
      traceA.station_exit = projection.aExit;
      traceA.lead = projection.aLead;
      traceB.station_exit = projection.bExit;
      traceB.lead = projection.bLead;
      local needsA = traceA.station_exit != pA.station_exit ||
                     traceA.lead != pA.lead;
      local needsB = traceB.station_exit != pB.station_exit ||
                     traceB.lead != pB.lead;
      if (diag != null && needsA && !("access_a_actual_exit" in diag)) {
        diag.rawset("access_a_actual_exit", pA.station_exit);
        diag.rawset("access_a_actual_lead", pA.lead);
        diag.rawset("access_a_virtual_exit", virtualA.station_exit);
        diag.rawset("access_a_virtual_lead", virtualA.lead);
        diag.rawset("access_a_projected_exit", traceA.station_exit);
        diag.rawset("access_a_projected_lead", traceA.lead);
      }
      if (diag != null && needsB && !("access_b_actual_exit" in diag)) {
        diag.rawset("access_b_actual_exit", pB.station_exit);
        diag.rawset("access_b_actual_lead", pB.lead);
        diag.rawset("access_b_virtual_exit", virtualB.station_exit);
        diag.rawset("access_b_virtual_lead", virtualB.lead);
        diag.rawset("access_b_projected_exit", traceB.station_exit);
        diag.rawset("access_b_projected_lead", traceB.lead);
      }
      OpexDoubleGrowDiagCount(diag, "trace_attempt");
      /* v233Context non null = trace geometrique pur. Les ouvrages sont
       * verifies plus bas par OpexTestRailTrack sous AITestMode : eviter
       * qu'un pont refuse au milieu du trace masque un probleme de site. */
      local trace = OpexV190TraceParallelTrack(window, a, b, traceA, traceB,
                                                 side, null, {});
      if (trace == null) {
        OpexDoubleGrowDiagCount(diag, "trace_null");
        if (diag != null) OpexDoubleGrowTraceDiag(diag,
            OpexDoubleGrowTraceDryIssue(window, traceA, traceB, side));
        continue;
      }
      /* V190 historique renvoie {start,end,kind} quand v233Context=null ;
       * OpexPlannedStructureKind ne sait lire que {from,to,kind}.
       * Convertir avant tout devis pour eviter un crash sur pont/tunnel. */
      local structures = [];
      local validStructures = true;
      foreach (s in trace.structures) {
        if (("from" in s) && ("to" in s)) {
          structures.append({ from = s.from, to = s.to, kind = s.kind });
        } else if (("start" in s) && ("end" in s)) {
          structures.append({ from = s.start, to = s.end, kind = s.kind });
        } else validStructures = false;
      }
      if (!validStructures) {
        OpexDoubleGrowDiagCount(diag, "structure_invalid"); continue;
      }
      /* Un quai distant n'est jamais raccorde par la projection virtuelle
       * seule : exiger son acces PHYSIQUE court, vierge et totalement
       * certifie avant l'appel historique a Clear. */
      if (needsA || needsB) {
        local access = OpexDoubleGrowOuterAccess(trace.tiles, structures,
            pA, pB, forbidden, route, line.depot, diag, needsA, needsB);
        if (access == null) continue;
        trace.tiles = access.tiles;
        structures = access.structures;
      }
      /* Ne jamais relacher clear_forbidden : si l'offset V190 heurte le
       * depot1 (seed512) ou si un ouvrage arrive directement sur le lead B,
       * essayer deux detours strictement locaux, puis refuser si la carte
       * ne permet pas un rail independant. */
      /* Contrat historique : toujours verifier la bande V190 brute
       * AVANT de considerer un detour. Les controles ulterieurs sont
       * identiques sur les candidats reconstruits. */
      local clear = OpexDoubleGrowClear(trace.tiles, structures, forbidden,
                                       pA, pB, diag, route, line.depot);
      local candidateTiles = trace.tiles;
      local candidateStructures = structures;
      for (local repairs = 0; !clear && repairs < 2; repairs++) {
        local blockedIndex = OpexDoubleGrowRepairIndex(candidateTiles,
                                                       forbidden, pA, pB);
        if (blockedIndex < 0) break;
        OpexDoubleGrowObstacleDiag(diag, candidateTiles[blockedIndex]);
        local replacement = OpexDoubleGrowRepairSlice(candidateTiles,
            candidateStructures, forbidden, pA, pB, route, line.depot,
            blockedIndex, diag);
        if (replacement == null) break;
        candidateTiles = replacement.tiles;
        candidateStructures = replacement.structures;
        clear = OpexDoubleGrowClear(candidateTiles, candidateStructures,
                                    forbidden, pA, pB, diag, route, line.depot);
      }
      if (!clear) continue;
      local native = null;
      {
        /* AIAccounting imbrique absorbe le cout simule d'AITestMode. */
        local shield = AIAccounting();
        native = OpexTestRailTrack(candidateTiles, candidateStructures);
      }
      if (native.failed > 0) {
        OpexDoubleGrowDiagCount(diag, "native_fail"); continue;
      }
      OpexDoubleGrowDiagCount(diag, "valid");
      OpexDoubleGrowPlanLog(line, route, diag, true);
      return { tiles1 = route, tiles2 = candidateTiles,
               structures2 = candidateStructures,
               platformA2 = pA, platformB2 = pB, depot2 = null,
               stationIdA = AIStation.GetStationID(line.stationA),
               stationIdB = AIStation.GetStationID(line.stationB),
               forbidden = forbidden };
    }
  }
  OpexDoubleGrowPlanLog(line, route, diag, false);
  return null;
}

/* Seules les cases prealablement vierges de la bande2 sont supprimees.
 * Ne jamais appeler OpexV190RollbackDoubleTrack : il retirerait aussi des
 * PBS_ONEWAY potentiellement preexistants de la voie primaire. */
function OpexDoubleGrowRollbackGeometry(geometry)
{
  if (geometry == null) return true;
  local ok = true;
  local own = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  if (geometry.depot2 != null && AIMap.IsValidTile(geometry.depot2) &&
      AIRail.IsRailDepotTile(geometry.depot2) &&
      AITile.GetOwner(geometry.depot2) == own &&
      !AITile.DemolishTile(geometry.depot2)) ok = false;
  for (local i = geometry.tiles2.len() - 2; i >= 1; i--) {
    local t = geometry.tiles2[i];
    if ((t in geometry.forbidden) || !AIMap.IsValidTile(t) ||
        AITile.GetOwner(t) != own) continue;
    if ((AIRail.IsRailTile(t) || AIBridge.IsBridgeTile(t) || AITunnel.IsTunnelTile(t)) &&
        !AITile.DemolishTile(t)) ok = false;
  }
  foreach (plan in [geometry.platformA2, geometry.platformB2]) {
    local stationId = plan == geometry.platformA2 ? geometry.stationIdA : geometry.stationIdB;
    for (local j = 0; j < plan.length; j++) {
      local t = plan.anchor + j * plan.step;
      if ((t in geometry.forbidden) || !AIRail.IsRailStationTile(t) ||
          AITile.GetOwner(t) != own || AIStation.GetStationID(t) != stationId) continue;
      if (!AIRail.RemoveRailStationTileRectangle(t, t, false)) ok = false;
    }
  }
  OpexAir0310InvalidateSiteValidity();
  return ok;
}

/* Constructeur volontairement unitaire : OpexBuildTrack pourrait declencher
 * la reprise V199 par A* et modifier la route sous nos pieds. */
function OpexDoubleGrowBuildTrack(geometry)
{
  local tiles = geometry.tiles2;
  for (local i = 1; i < tiles.len() - 1; i++) {
    local prev = tiles[i - 1];
    local cur = tiles[i];
    local next = tiles[i + 1];
    if (AIMap.DistanceManhattan(prev, cur) > 1) continue;
    if (AIMap.DistanceManhattan(cur, next) > 1) {
      local kind = OpexPlannedStructureKind(geometry.structures2, cur, next);
      if (kind == "tunnel") {
        if (!AITunnel.BuildTunnel(AIVehicle.VT_RAIL, cur)) return false;
      } else if (kind == "bridge") {
        local bridges = AIBridgeList_Length(AIMap.DistanceManhattan(cur, next) + 1);
        OpexBridgeSortBySpeed(bridges);
        if (bridges.IsEmpty() || !AIBridge.BuildBridge(AIVehicle.VT_RAIL,
                                                      bridges.Begin(), cur, next)) return false;
      } else return false;
    } else if (!AIRail.BuildRail(prev, cur, next) ||
               !AIRail.AreTilesConnected(prev, cur, next)) return false;
  }
  return OpexDoubleGrowVerifyRoute(tiles, geometry.platformA2, geometry.platformB2);
}

/* La seconde voie et son depot sont construits avant l'appel a la flotte.
 * Le finalizer travaille sur stagedLine (copie de la table et du tableau de
 * trains), pas sur line. Il doit vendre la rame2 et restituer les ordres,
 * aiguillages, PBS et waypoints si sa certification echoue. */
function OpexDoubleGrowGeometry(owner, line)
{
  DOUBLE_GROW_GEOMETRY_REASON = "";
  if (owner == null || line == null || !("mode" in line) || line.mode != "rail" ||
      !("kind" in line) || line.kind != "freight" ||
      !("lastProfit" in line) || line.lastProfit <= 0 ||
      !("depot" in line) || line.depot == null ||
      !AIRail.IsRailDepotTile(line.depot) ||
      !("platformA" in line) || !("platformB" in line) ||
      !("stationA" in line) || !("stationB" in line) ||
      !("vehicles" in line) || line.vehicles == null || line.vehicles.len() != 1 ||
      !("trains" in line) || line.trains != 1 ||
      (("doubleTrack" in line) && line.doubleTrack != 0) ||
      (("v271Tandem" in line) && line.v271Tandem) ||
      (("scrapping" in line) && line.scrapping) ||
      !AIVehicle.IsValidVehicle(line.vehicles[0]))
    return OpexDoubleGrowReject("INELIGIBLE", line);
  /* Le module flotte est charge explicitement par main.nut lorsque le
   * reglage est present : aucun acces reflexif au tableau racine. */
  local stationAId = AIStation.GetStationID(line.stationA);
  local stationBId = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationAId) || !AIStation.IsValidStation(stationBId) ||
      stationAId == stationBId) return OpexDoubleGrowReject("STATION_IDS", line);

  local previousType = AIRail.GetCurrentRailType();
  local expectedType = AIRail.GetRailType(line.depot);
  AIRail.SetCurrentRailType(expectedType);
  if (AIRail.GetCurrentRailType() != expectedType)
    return OpexDoubleGrowReject("RAIL_TYPE", line);
  local route = OpexDoubleGrowPrimaryRoute(line);
  if (route == null || !OpexDoubleGrowVerifyRoute(route, line.platformA, line.platformB)) {
    AIRail.SetCurrentRailType(previousType);
    return OpexDoubleGrowReject("PRIMARY_TRACE", line);
  }
  local geometry = OpexDoubleGrowPlan(line, route);
  if (geometry == null) {
    AIRail.SetCurrentRailType(previousType);
    return OpexDoubleGrowReject("NO_PARALLEL_BAND", line);
  }
  local estimate = geometry.tiles2.len()
      * AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_TRACK)
      + AIRail.GetBuildCost(AIRail.GetCurrentRailType(), AIRail.BT_DEPOT);
  if (owner._catalog != null) estimate +=
      (geometry.platformA2.length + geometry.platformB2.length) * owner._catalog.costStation;
  if (AICompany.GetBankBalance(AICompany.COMPANY_SELF) < estimate + 50000) {
    AIRail.SetCurrentRailType(previousType);
    return OpexDoubleGrowReject("CASH", line);
  }

  OpexAir0310InvalidateSiteValidity();
  local ok = AIRail.BuildRailStation(geometry.platformA2.anchor,
      geometry.platformA2.direction, 1, geometry.platformA2.length, stationAId);
  if (ok) ok = AIStation.GetStationID(geometry.platformA2.anchor) == stationAId;
  if (ok) ok = AIRail.BuildRailStation(geometry.platformB2.anchor,
      geometry.platformB2.direction, 1, geometry.platformB2.length, stationBId);
  if (ok) ok = AIStation.GetStationID(geometry.platformB2.anchor) == stationBId;
  if (ok) ok = OpexDoubleGrowBuildTrack(geometry);

  if (ok) {
    local depotForbidden = {};
    foreach (t, ignored in geometry.forbidden) depotForbidden[t] <- true;
    foreach (t in geometry.tiles2) depotForbidden[t] <- true;
    /* La recherche du depot est limitee au milieu du corridor. V190-FIX2
     * garde les gorges et les aiguillages des deux bouts sans depot. */
    local middle = geometry.tiles2.len() / 2;
    local window = [];
    for (local i = max(2, middle - 8); i <= min(geometry.tiles2.len() - 3, middle + 8); i++)
      window.append(geometry.tiles2[i]);
    if (window.len() >= 3) geometry.depot2 = OpexBuildDepot(window, depotForbidden);
    ok = geometry.depot2 != null && AIRail.IsRailDepotTile(geometry.depot2) &&
        AIRail.GetRailDepotFrontTile(geometry.depot2) != line.depot &&
        OpexDoubleGrowVerifyRoute(route, line.platformA, line.platformB) &&
        OpexDoubleGrowVerifyRoute(geometry.tiles2, geometry.platformA2,
                                  geometry.platformB2);
  }

  local stagedLine = null;
  if (ok) {
    stagedLine = clone line;
    /* rawset couvre aussi les sauvegardes qui portent deja les clefs vides
     * de l'ancien upgrader ; aucun champ n'est ecrit dans line a ce stade. */
    stagedLine.rawset("tiles1", route);
    stagedLine.rawset("tiles2", geometry.tiles2);
    stagedLine.rawset("platformA2", geometry.platformA2);
    stagedLine.rawset("platformB2", geometry.platformB2);
    stagedLine.rawset("stationA2", geometry.platformA2.station_exit);
    stagedLine.rawset("stationB2", geometry.platformB2.station_exit);
    stagedLine.rawset("depot2", geometry.depot2);
    stagedLine.rawset("doubleTrack", 1);
    stagedLine.rawset("vehicles", [line.vehicles[0]]);
    ok = OpexDoubleGrowFleetFinalize(owner, line, stagedLine);
    /* Le finalizer certifie lui-meme les deux rames et la conversion FIX2.
     * Une verification supplementaire susceptible d'echouer APRES FIX2
     * ferait detruire la voie2 alors que les aiguillages sont deja poses. */
  }
  if (!ok) {
    local rolledBack = OpexDoubleGrowRollbackGeometry(geometry);
    AIRail.SetCurrentRailType(previousType);
    return OpexDoubleGrowReject(rolledBack ? "BUILD_OR_DIRECTION" : "ROLLBACK_FAILED", line);
  }

  line.rawset("tiles1", route);
  line.rawset("tiles2", geometry.tiles2);
  line.rawset("stationA2", geometry.platformA2.station_exit);
  line.rawset("stationB2", geometry.platformB2.station_exit);
  line.rawset("platformA2", geometry.platformA2);
  line.rawset("platformB2", geometry.platformB2);
  line.rawset("depot2", geometry.depot2);
  line.rawset("vehicles", stagedLine.vehicles);
  line.rawset("doubleTrack", 1);
  line.rawset("trains", stagedLine.vehicles.len());
  line.rawset("vehCount", stagedLine.vehicles.len());
  line.rawset("v190Independent", false);
  line.rawset("v190Directional", true);
  line.rawset("v181Loop", true);
  line.rawset("doubleGrowDirectional", true);
  owner._saveProjection = null;
  OpexAir0310InvalidateSiteValidity();
  AIRail.SetCurrentRailType(previousType);
  if (DECISION_LOG) OpexDecide("DOUBLE_GROW", "phase=directional ok=1 line=" + line.lineId
      + " path=" + geometry.tiles2.len() + " depot2=" + geometry.depot2
      + " trains=" + stagedLine.vehicles.len());
  return true;
}
