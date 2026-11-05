/* RAIL-DEPOT-SIGNAL. Strictement opt-in, aucun changement du constructeur OFF.
 * Regle 2026-11-03 : embranchement rectiligne degageant au moins une rame de
 * part et d'autre du PBS du depot, et PBS AVANT chaque entree d'aiguillage.
 * Les lignes bidirectionnelles conservent exclusivement SIGNALTYPE_PBS normal.
 * Un echec de la construction incrementale annule tous les rails et signaux
 * crees ici ; jamais de demolition d'une voie existante ou d'un batiment. */
RAIL_DEPOT_SIGNAL_SPURS <- {};

/* Garde fail-closed apres les smokes du 2026-11-03. Les trois PBS sont
 * constructibles mais 26 trains sur 27 branches sont perdus; les ablations
 * d'un ou deux PBS ne restaurent pas la circulation. Tant qu'aucune geometrie
 * YAPF/PBS sure n'est prouvee par les saves, NE PAS exposer de nouvelles
 * branches (ni meme les depots additionnels). Le constructeur historique est
 * essaye en repli, sans changement du flag utilisateur, qui reste a 0. */
function OpexRailDepotSignalSpurRoutingCertified()
{
  return false;
}

function OpexRailDepotSignalTiles(trainTiles)
{
  if (trainTiles == null || trainTiles < 1) return 1;
  return trainTiles;
}

function OpexRailDepotSignalRollbackSpur(mainBefore, mainAfter, junction, branch, depot, placedSignals, junctionBuilt, reverseBuilt, builtTrack)
{
  /* Seuls les signaux que NOUS avons poses sont retires. */
  for (local s = placedSignals.len() - 1; s >= 0; s--) {
    AIRail.RemoveSignal(placedSignals[s].tile, placedSignals[s].front);
  }
  if (depot != null && AIRail.IsRailDepotTile(depot)) AITile.DemolishTile(depot);
  for (local j = builtTrack - 1; j >= 0; j--) {
    local before = j == 0 ? junction : branch[j - 1];
    local after = j == branch.len() - 1 ? depot : branch[j + 1];
    AIRail.RemoveRail(before, branch[j], after);
  }
  if (reverseBuilt) AIRail.RemoveRail(mainAfter, junction, branch[0]);
  if (junctionBuilt) AIRail.RemoveRail(mainBefore, junction, branch[0]);
}

/* Construit une branche seulement sur des tuiles prealablement libres. Le PBS
 * de depot est a L+1 cases de la jonction ET a L+1 cases du depot (L=tuiles
 * de la rame), pour eviter qu'un train en attente occupe l'aiguillage. Les PBS
 * de voie principale sont eux aussi a >= L+1 cases AVANT la jonction. */
function OpexRailDepotSignalTrySpur(tiles, index, trainTiles, forbidden)
{
  local last = tiles.len() - 1;
  local l = OpexRailDepotSignalTiles(trainTiles);
  local clear = l + 2;
  if (index <= clear + 3 || index >= last - clear - 3) return null;
  local junction = tiles[index];
  local before = tiles[index - 1];
  local after = tiles[index + 1];
  if (!AIMap.IsValidTile(junction) || !AIMap.IsValidTile(before) ||
      !AIMap.IsValidTile(after) ||
      AIMap.DistanceManhattan(before, junction) != 1 ||
      AIMap.DistanceManhattan(after, junction) != 1 ||
      AIRail.IsRailStationTile(junction) ||
      !AIRail.IsRailTile(junction) || OpexTileTrackCount(junction) != 1 ||
      !AIRail.AreTilesConnected(before, junction, after)) return null;
  if (AIRail.GetSignalType(junction, before) != AIRail.SIGNALTYPE_NONE ||
      AIRail.GetSignalType(junction, after) != AIRail.SIGNALTYPE_NONE) return null;
  if (forbidden != null && (junction in forbidden)) return null;

  /* Aucun aiguillage, courbe speciale ou signal non-PBS dans les deux zones
   * d'approche : on ne laisse jamais un PBS immediatement APRES l'aiguillage. */
  local approach = [index - clear, index + clear];
  foreach (at in approach) {
    if (at <= 1 || at >= last - 1) return null;
    local step = at < index ? 1 : -1;
    if (!AIMap.IsValidTile(tiles[at - step]) ||
        AIMap.DistanceManhattan(tiles[at], tiles[at - step]) != 1) return null;
    for (local k = at; k != index; k += step) {
      if (!AIMap.IsValidTile(tiles[k]) || !AIMap.IsValidTile(tiles[k + step]) ||
          !AIMap.IsValidTile(tiles[k - step]) ||
          AIMap.DistanceManhattan(tiles[k], tiles[k + step]) != 1 ||
          AIMap.DistanceManhattan(tiles[k], tiles[k - step]) != 1 ||
          !AIRail.IsRailTile(tiles[k]) || AIRail.IsRailStationTile(tiles[k]) ||
          OpexTileTrackCount(tiles[k]) != 1) return null;
      /* Ne pas ajouter un aiguillage si un autre signal existe dans la zone
       * de dégagement d'une rame, même s'il n'est pas à notre site PBS. */
      if (AIRail.GetSignalType(tiles[k], tiles[k + step]) != AIRail.SIGNALTYPE_NONE ||
          AIRail.GetSignalType(tiles[k], tiles[k - step]) != AIRail.SIGNALTYPE_NONE) return null;
    }
    if (AIRail.GetSignalType(tiles[at], tiles[at + step]) != AIRail.SIGNALTYPE_NONE ||
        AIRail.GetSignalType(tiles[at], tiles[at - step]) != AIRail.SIGNALTYPE_NONE) return null;
  }
  local offsets = [AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(-1, 0),
                   AIMap.GetTileIndex(0, 1), AIMap.GetTileIndex(0, -1)];
  foreach (offset in offsets) {
    local first = junction + offset;
    if (first == before || first == after) continue;
    local branch = [];
    local suitable = true;
    local depot = null;
    /* 2L+2 tuiles d'embranchement + un batiment de depot. */
    for (local d = 1; d <= 2 * l + 3; d++) {
      local tile = junction + d * offset;
      local previous = junction + (d - 1) * offset;
      if (!AIMap.IsValidTile(tile) || AIMap.DistanceManhattan(previous, tile) != 1 ||
          (forbidden != null && (tile in forbidden)) || !AITile.IsBuildable(tile) ||
          AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) ||
          AIRail.IsRailDepotTile(tile) || AITile.HasTransportType(tile, AITile.TRANSPORT_ROAD)) {
        suitable = false; break;
      }
      if (d == 2 * l + 3) depot = tile;
      else branch.append(tile);
    }
    if (!suitable) continue;

    local newSignals = [];
    local builtTrack = 0;
    local junctionBuilt = AIRail.BuildRail(before, junction, branch[0]);
    if (!junctionBuilt || !AIRail.AreTilesConnected(before, junction, after) ||
        !AIRail.AreTilesConnected(before, junction, branch[0])) {
      if (junctionBuilt) AIRail.RemoveRail(before, junction, branch[0]);
      continue;
    }
    /* Le dépôt doit être joignable depuis les DEUX sens de la voie principale.
     * Le premier raccordement peut n'ouvrir qu'une seule direction : poser
     * explicitement la seconde courbe puis vérifier toutes les connexions. */
    local reverseBuilt = AIRail.BuildRail(after, junction, branch[0]);
    if (!AIRail.AreTilesConnected(after, junction, branch[0]) ||
        !AIRail.AreTilesConnected(before, junction, branch[0]) ||
        !AIRail.AreTilesConnected(before, junction, after)) {
      OpexRailDepotSignalRollbackSpur(before, after, junction, branch, null,
                                     newSignals, true, reverseBuilt, builtTrack);
      continue;
    }
    for (local j = 0; j < branch.len(); j++) {
      local prev = j == 0 ? junction : branch[j - 1];
      local next = j == branch.len() - 1 ? depot : branch[j + 1];
      if (!AIRail.BuildRail(prev, branch[j], next)) break;
      builtTrack++;
    }
    local depotBuilt = false;
    if (builtTrack == branch.len()) {
      depotBuilt = AIRail.BuildRailDepot(depot, branch[branch.len() - 1]);
    }
    if (!depotBuilt || AIRail.GetRailDepotFrontTile(depot) != branch[branch.len() - 1]) {
      OpexRailDepotSignalRollbackSpur(before, after, junction, branch,
                                     depot, newSignals, true, reverseBuilt, builtTrack);
      continue;
    }

    /* AIRail.BuildSignal(tile, front) prend le cote d'ou vient le train.
     * En quittant le depot vers l'aiguillage, le train arrive de branch[l+1].
     * L'ancienne valeur branch[l-1] orientait le PBS vers la gorge et
     * laissait des trains perdre leur chemin dans la branche. */
    local spurSignal = branch[l];
    local spurFront = branch[l + 1];
    local signalOk = AIRail.BuildSignal(spurSignal, spurFront, AIRail.SIGNALTYPE_PBS);
    if (signalOk) newSignals.append({ tile = spurSignal, front = spurFront });
    foreach (at in approach) {
      if (!signalOk) break;
      local step = at < index ? 1 : -1;
      /* Approche exterieure -> jonction : le train arrive de at-step. */
      signalOk = AIRail.BuildSignal(tiles[at], tiles[at - step], AIRail.SIGNALTYPE_PBS);
      if (signalOk) newSignals.append({ tile = tiles[at], front = tiles[at - step] });
    }
    if (!signalOk) {
      OpexRailDepotSignalRollbackSpur(before, after, junction, branch, depot,
                                     newSignals, true, reverseBuilt, builtTrack);
      continue;
    }
    local data = { depot = depot, junction = junction, routeIndex = index,
                   trainTiles = l, spurTiles = branch.len(), signals = newSignals.len(),
                   signalDepot = spurSignal, mainBefore = tiles[approach[0]],
                   mainAfter = tiles[approach[1]], before = before, after = after,
                   reverseBuilt = reverseBuilt,
                   branch = branch, placedSignals = newSignals };
    RAIL_DEPOT_SIGNAL_SPURS[depot] <- data;
    if (DECISION_LOG) OpexDecide("RAIL_DEPOT_SIGNAL", "phase=spur depot=" + depot
        + " junction=" + junction + " route_index=" + index + " train_tiles=" + l
        + " spur_tiles=" + branch.len() + " bidir=1 pbs_depot=" + spurSignal
        + " pbs_main_a=" + tiles[approach[0]] + " pbs_main_b=" + tiles[approach[1]]);
    return depot;
  }
  return null;
}

/* Le rollback d'une ligne non encore mise en service doit aussi retirer les
 * bretelles propres a ce module. Sans cela OpexRollback n'effacerait que le
 * depot et la ligne principale, laissant le raccordement en friche. */
function OpexRailDepotSignalRollbackTracked(depot)
{
  if (depot == null || !(depot in RAIL_DEPOT_SIGNAL_SPURS)) return false;
  local data = RAIL_DEPOT_SIGNAL_SPURS[depot];
  OpexRailDepotSignalRollbackSpur(data.before, data.after, data.junction, data.branch, depot,
                                 data.placedSignals, true, data.reverseBuilt, data.branch.len());
  delete RAIL_DEPOT_SIGNAL_SPURS[depot];
  return true;
}

/* Emplacements proches des terminus, mais hors de leur gorge. Les longues
 * lignes utilisent aussi ce constructeur par cible d'indice ~100 tuiles. */
function OpexRailDepotSignalBuildNear(tiles, fromB, otherDepot = null, extraForbidden = null, trainTiles = 6)
{
  if (!OpexRailDepotSignalSpurRoutingCertified()) return null;
  if (tiles == null || tiles.len() < 14) return null;
  local last = tiles.len() - 1;
  local clear = OpexRailDepotSignalTiles(trainTiles) + 7;
  /* La fenetre historique de 13 sites causait de nombreux NO_SAFE_SPUR,
   * puis des DEPFAIL sans ligne. Chercher plus loin sur la route deja
   * construite, toujours avec les gardes de gorge et de voies existantes. */
  for (local offset = 0; offset <= 100; offset++) {
    local i = fromB ? last - clear - offset : clear + offset;
    if (i <= 2 || i >= last - 2) break;
    if (otherDepot != null && AIMap.IsValidTile(otherDepot) &&
        AIMap.DistanceManhattan(otherDepot, tiles[i]) < 8) continue;
    local depot = OpexRailDepotSignalTrySpur(tiles, i, trainTiles, extraForbidden);
    if (depot != null) return depot;
  }
  return null;
}

/* La voie 1 doit pouvoir accueillir une rame complete dans son embranchement.
 * Pas de repli au depot colle a une sortie de gare sous opt-in : il pourrait
 * rendre impossible le trafic ou creer le demi-tour observe par l'utilisateur. */
function OpexRailDepotSignalBuildPrimary(tiles, extraForbidden = null, trainTiles = 6)
{
  local depot = OpexRailDepotSignalBuildNear(tiles, false, null, extraForbidden, trainTiles);
  /* RDS ne doit jamais faire perdre une ligne viable lorsqu'aucune branche
   * longue/protegee ne passe les controles. Un echec revient au constructeur
   * de depot historique, deja utilise avec la meme liste forbidden en OFF.
   * Le cas sans depot constructible MEME dans le constructeur historique
   * demeure un vrai DEPFAIL, sans masquer cette impossibilite physique. */
  if (depot == null) {
    depot = OpexBuildDepot(tiles, extraForbidden);
    if (DECISION_LOG) OpexDecide("RAIL_DEPOT_SIGNAL", "phase=legacy_fallback"
        + " depot=" + (depot != null ? depot : -1)
        + " route_tiles=" + (tiles != null ? tiles.len() : -1)
        + " status=" + (depot != null ? "OK" : "LEGACY_DEPFAIL"));
  }
  if (DECISION_LOG) OpexDecide("RAIL_DEPOT_SIGNAL", "phase=primary"
      + " depot=" + (depot != null ? depot : -1)
      + " route_tiles=" + (tiles != null ? tiles.len() : -1)
      + " train_tiles=" + trainTiles + " status=" + (depot != null ? "OK" : "NO_SAFE_SPUR"));
  return depot;
}

function OpexRailDepotSignalPathDistance(tiles, depot, fromB)
{
  if (tiles == null || depot == null || !AIMap.IsValidTile(depot) ||
      !AIRail.IsRailDepotTile(depot)) return -1;
  local index = -1;
  if (depot in RAIL_DEPOT_SIGNAL_SPURS) {
    index = RAIL_DEPOT_SIGNAL_SPURS[depot].routeIndex;
  } else {
    local front = AIRail.GetRailDepotFrontTile(depot);
    if (!AIMap.IsValidTile(front)) return -1;
    for (local i = 0; i < tiles.len(); i++) {
      if (tiles[i] == front) { index = i; break; }
    }
  }
  if (index < 0 || index >= tiles.len()) return -1;
  local start = fromB ? index : 0;
  local end = fromB ? tiles.len() - 1 : index;
  local distance = 0;
  for (local i = start + 1; i <= end; i++) {
    distance += AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
  }
  return distance;
}

function OpexRailDepotSignalRouteLength(tiles)
{
  if (tiles == null || tiles.len() < 2) return 0;
  local distance = 0;
  for (local i = 1; i < tiles.len(); i++) {
    distance += AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
  }
  return distance;
}

function OpexRailDepotSignalIndexForDistance(tiles, target)
{
  local distance = 0;
  for (local i = 1; i < tiles.len(); i++) {
    distance += AIMap.DistanceManhattan(tiles[i - 1], tiles[i]);
    if (distance >= target) return i;
  }
  return tiles.len() - 1;
}

/* Un PBS bidirectionnel au plus, sur une section simple. La voie unique reste
 * bidirectionnelle; les signaux bloc a sens unique sont reserves aux boucles
 * V181/V199 existantes (aucun changement de leur politique sous ce reglage). */
function OpexRailDepotSignalJoinedPbs(tiles, platform, fromB)
{
  local c41 = OpexC41BuildPbsAtApproach(platform);
  if (c41 == 1 || c41 == 2 || c41 == -2) return c41;
  if (tiles == null || tiles.len() < 5) return -1;
  local last = tiles.len() - 1;
  local step = fromB ? -1 : 1;
  local start = fromB ? last : 0;
  local failed = false;
  for (local distance = 2; distance <= 9; distance++) {
    local i = start + step * distance;
    if (i <= 0 || i >= last) break;
    local tile = tiles[i];
    local toward = tiles[i - step];
    local away = tiles[i + step];
    if (!AIMap.IsValidTile(tile) || !AIMap.IsValidTile(toward) || !AIMap.IsValidTile(away)) continue;
    if (AIMap.DistanceManhattan(tile, toward) != 1 ||
        AIMap.DistanceManhattan(tile, away) != 1 ||
        OpexTileTrackCount(tile) != 1 ||
        !AIRail.AreTilesConnected(toward, tile, away)) continue;
    local one = AIRail.GetSignalType(tile, toward);
    local two = AIRail.GetSignalType(tile, away);
    if (one == AIRail.SIGNALTYPE_PBS || two == AIRail.SIGNALTYPE_PBS) return 2;
    if (one != AIRail.SIGNALTYPE_NONE || two != AIRail.SIGNALTYPE_NONE) return -2;
    if (AIRail.BuildSignal(tile, toward, AIRail.SIGNALTYPE_PBS)) return 1;
    failed = true;
  }
  return failed ? 0 : -1;
}

/* Apres demarrage du train seulement : un echec de depot B ne compromet pas
 * la gare, la voie ni le train deja rentables. Le cout entre dans postPathCosts. */
function OpexRailDepotSignalEnhance(candidate, tiles, planA, planB, depot, tiles2 = null, depot2 = null)
{
  /* En repli historique, ne pas poser ensuite de nouvelles branches non
   * certifiees sur la ligne deja rentable. */
  if (!OpexRailDepotSignalSpurRoutingCertified()) {
    return { depotB = null, depotB2 = null, midDepots = [], midDepots2 = [],
             midCount = 0, midCount2 = 0, joinSignal = -1, joinEnd = "-",
             startPath = OpexRailDepotSignalPathDistance(tiles, depot, false),
             endPath = -1,
             startPath2 = (tiles2 != null) ? OpexRailDepotSignalPathDistance(tiles2, depot2, false) : -1,
             endPath2 = -1 };
  }
  local trainTiles = (candidate != null && ("platformLength" in candidate))
      ? candidate.platformLength : 6;
  if (DECISION_LOG) {
    /* Les reglages du duel peuvent differer des 180 archives SOLO : mesurer
     * ceux de la partie en cours au lieu de deduire le service des seuls saves. */
    local breakdowns = AIGameSettings.IsValid("difficulty.vehicle_breakdowns")
        ? AIGameSettings.GetValue("difficulty.vehicle_breakdowns") : -1;
    local service = AIGameSettings.IsValid("vehicle.servint_trains")
        ? AIGameSettings.GetValue("vehicle.servint_trains") : -1;
    local percent = AIGameSettings.IsValid("vehicle.servint_ispercent")
        ? AIGameSettings.GetValue("vehicle.servint_ispercent") : -1;
    OpexDecide("RAIL_DEPOT_SIGNAL", "phase=config breakdowns=" + breakdowns
        + " service_trains=" + service + " service_percent=" + percent);
  }
  /* Eviter un depot B qui remplace une case de l'autre voie independante.
   * Symetrique et sans effet sur les plans a voie simple. */
  local forbiddenB = null;
  local forbiddenB2 = null;
  if (tiles2 != null) {
    forbiddenB = {};
    foreach (tile in tiles2) forbiddenB[tile] <- true;
    if (depot2 != null) forbiddenB[depot2] <- true;
    forbiddenB2 = {};
    foreach (tile in tiles) forbiddenB2[tile] <- true;
    if (depot != null) forbiddenB2[depot] <- true;
  }
  local endDepot = OpexRailDepotSignalBuildNear(tiles, true, depot, forbiddenB, trainTiles);
  if (forbiddenB2 != null && endDepot != null) {
    forbiddenB2[endDepot] <- true;
    local front = AIRail.GetRailDepotFrontTile(endDepot);
    if (AIMap.IsValidTile(front)) forbiddenB2[front] <- true;
  }
  local endDepot2 = (tiles2 != null && depot2 != null)
      ? OpexRailDepotSignalBuildNear(tiles2, true, depot2, forbiddenB2, trainTiles) : null;
  /* Un depot supplementaire tous les ~100 pas sur les longues lignes. Une
   * tentative non constructible n'annule jamais la ligne deja en service. */
  local midDepots = [];
  local midDepots2 = [];
  local gap = 100;
  local routeDist = OpexRailDepotSignalRouteLength(tiles);
  local routeDist2 = OpexRailDepotSignalRouteLength(tiles2);
  local targets = routeDist > gap ? (routeDist + gap - 1) / gap - 1 : 0;
  local targets2 = routeDist2 > gap ? (routeDist2 + gap - 1) / gap - 1 : 0;
  if (routeDist > gap) {
    local sections = (routeDist + gap - 1) / gap;
    for (local section = 1; section < sections; section++) {
      local target = OpexRailDepotSignalIndexForDistance(tiles, (routeDist * section) / sections);
      local found = false;
      for (local d = 0; d <= 9; d++) {
        local i = target + ((d % 2 == 0) ? d / 2 : -(d + 1) / 2);
        if (i <= trainTiles + 5 || i >= tiles.len() - trainTiles - 6) continue;
        local depotMid = OpexRailDepotSignalTrySpur(tiles, i, trainTiles, forbiddenB);
        if (depotMid != null) { midDepots.append(depotMid); found = true; break; }
      }
      if (!found && DECISION_LOG) OpexDecide("RAIL_DEPOT_SIGNAL", "phase=intermediate_skip"
          + " track=1 target=" + target + " section=" + section + " status=NO_SAFE_SPUR");
    }
  }
  if (tiles2 != null && depot2 != null && routeDist2 > gap) {
    local sections = (routeDist2 + gap - 1) / gap;
    for (local section = 1; section < sections; section++) {
      local target = OpexRailDepotSignalIndexForDistance(tiles2, (routeDist2 * section) / sections);
      local found = false;
      for (local d = 0; d <= 9; d++) {
        local i = target + ((d % 2 == 0) ? d / 2 : -(d + 1) / 2);
        if (i <= trainTiles + 5 || i >= tiles2.len() - trainTiles - 6) continue;
        local depotMid2 = OpexRailDepotSignalTrySpur(tiles2, i, trainTiles, forbiddenB2);
        if (depotMid2 != null) { midDepots2.append(depotMid2); found = true; break; }
      }
      if (!found && DECISION_LOG) OpexDecide("RAIL_DEPOT_SIGNAL", "phase=intermediate_skip"
          + " track=2 target=" + target + " section=" + section + " status=NO_SAFE_SPUR");
    }
  }
  local joined = candidate != null && ("joinPlatform" in candidate) && candidate.joinPlatform != null;
  local joinB = joined && ("joinEnd" in candidate) && candidate.joinEnd == "B";
  local signal = joined ? OpexRailDepotSignalJoinedPbs(tiles, joinB ? planB : planA, joinB) : -1;
  if (DECISION_LOG) OpexDecide("RAIL_DEPOT_SIGNAL", "phase=coverage"
      + " distance=" + routeDist + " distance2=" + routeDist2
      + " train_tiles=" + trainTiles + " mid_targets=" + targets
      + " mid2_targets=" + targets2 + " mid_built=" + midDepots.len()
      + " mid2_built=" + midDepots2.len()
      + " depot_b=" + (endDepot != null ? endDepot : -1)
      + " depot_b2=" + (endDepot2 != null ? endDepot2 : -1));
  return { depotB = endDepot, depotB2 = endDepot2, midDepots = midDepots,
           midDepots2 = midDepots2, midCount = midDepots.len(),
           midCount2 = midDepots2.len(), joinSignal = signal,
           joinEnd = joined ? (joinB ? "B" : "A") : "-",
           startPath = OpexRailDepotSignalPathDistance(tiles, depot, false),
           endPath = OpexRailDepotSignalPathDistance(tiles, endDepot, true),
           startPath2 = (tiles2 != null) ? OpexRailDepotSignalPathDistance(tiles2, depot2, false) : -1,
           endPath2 = (tiles2 != null) ? OpexRailDepotSignalPathDistance(tiles2, endDepot2, true) : -1 };
}

/* Une station devenue partagee a aussi besoin de proteger les approches des
 * lignes qui y etaient deja. On ne touche qu'au quai de ce StationID, jamais
 * aux signaux existants d'un autre type ni aux aiguillages a plusieurs branches. */
function OpexRailDepotSignalProtectExisting(lines, candidate, newLineId)
{
  local acc = { seen = 0, built = 0, present = 0, refused = 0 };
  if (!OpexRailDepotSignalSpurRoutingCertified()) return acc;
  if (!("joinStationId" in candidate) || candidate.joinStationId < 0) return acc;
  local stationId = candidate.joinStationId;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "rail" ||
        !("lineId" in line) || line.lineId == newLineId) continue;
    local a = ("stationA" in line) && line.stationA != null &&
        AIStation.GetStationID(line.stationA) == stationId;
    local b = ("stationB" in line) && line.stationB != null &&
        AIStation.GetStationID(line.stationB) == stationId;
    if (!a && !b) continue;
    acc.seen++;
    local platform = a ? (("platformA" in line) ? line.platformA : null)
                       : (("platformB" in line) ? line.platformB : null);
    local status = OpexC41BuildPbsAtApproach(platform, a ? line.stationA : line.stationB);
    if (status == 1) acc.built++;
    else if (status == 2) acc.present++;
    else acc.refused++;
  }
  return acc;
}
