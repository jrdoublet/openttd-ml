/* V190-FIX2 : essai directionnel, opt-in 0. Ne touche pas au trace V233L.
 * La correction independante V190-FIX (deux rames bidirectionnelles) reste
 * disponible si le drapeau n'est pas active. Le reseau directionnel conserve
 * deux quais par gare avec le meme StationID, une voie A->B et une B->A.
 * DEUX raccordements seulement : apres A2 vers voie1, apres B1 vers voie2.
 * L'ancienne boucle a quatre raccordements creait une petite boucle locale.
 * Les signaux PBS_ONEWAY regardent le sens du train et sont hors gorges.
 * Tout echec est fail-closed et annule les seuls changements de cette fonction.
 * Ne pas qualifier la constructibilite hors smoke OpenTTD. */

function OpexV190Fix2SwitchSafe(fromPrev, fromTile, fromNext, toPrev, toTile, toNext)
{
  if (!AIMap.IsValidTile(fromPrev) || !AIMap.IsValidTile(fromTile) ||
      !AIMap.IsValidTile(fromNext) || !AIMap.IsValidTile(toPrev) ||
      !AIMap.IsValidTile(toTile) || !AIMap.IsValidTile(toNext)) return false;
  if (AIMap.DistanceManhattan(fromPrev, fromTile) != 1 ||
      AIMap.DistanceManhattan(fromTile, fromNext) != 1 ||
      AIMap.DistanceManhattan(toPrev, toTile) != 1 ||
      AIMap.DistanceManhattan(toTile, toNext) != 1) return false;
  foreach (tile in [fromTile, toTile]) {
    if (!AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) ||
        AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile) ||
        OpexTileTrackCount(tile) != 1 ||
        AITile.GetOwner(tile) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) return false;
  }
  if (AIRail.GetSignalType(fromTile, fromPrev) != AIRail.SIGNALTYPE_NONE ||
      AIRail.GetSignalType(fromTile, fromNext) != AIRail.SIGNALTYPE_NONE ||
      AIRail.GetSignalType(toTile, toPrev) != AIRail.SIGNALTYPE_NONE ||
      AIRail.GetSignalType(toTile, toNext) != AIRail.SIGNALTYPE_NONE) return false;
  local distance = AIMap.DistanceManhattan(fromTile, toTile);
  if (distance == 1) return true;
  if (distance != 2) return false;
  local x1 = AIMap.GetTileX(fromTile);
  local y1 = AIMap.GetTileY(fromTile);
  local x2 = AIMap.GetTileX(toTile);
  local y2 = AIMap.GetTileY(toTile);
  if (abs(x1 - x2) != 1 || abs(y1 - y2) != 1) return false;
  /* Un raccordement avec case centrale deja occupee pourrait couper une
   * ligne preexistante de OpexAI ou d'AAAHogEx. Ne jamais la reutiliser. */
  foreach (mid in [AIMap.GetTileIndex(x1, y2), AIMap.GetTileIndex(x2, y1)]) {
    if (AIMap.IsValidTile(mid) && AITile.IsBuildable(mid) &&
        AITile.GetSlope(mid) == AITile.SLOPE_FLAT &&
        !AITile.HasTransportType(mid, AITile.TRANSPORT_RAIL)) return true;
  }
  return false;
}

function OpexV190Fix2SwitchConnected(fromPrev, fromTile, toTile, toNext)
{
  if (AIMap.DistanceManhattan(fromTile, toTile) == 1) {
    return AIRail.AreTilesConnected(fromPrev, fromTile, toTile) &&
           AIRail.AreTilesConnected(fromTile, toTile, toNext);
  }
  if (AIMap.DistanceManhattan(fromTile, toTile) != 2) return false;
  local x1 = AIMap.GetTileX(fromTile);
  local y1 = AIMap.GetTileY(fromTile);
  local x2 = AIMap.GetTileX(toTile);
  local y2 = AIMap.GetTileY(toTile);
  foreach (mid in [AIMap.GetTileIndex(x1, y2), AIMap.GetTileIndex(x2, y1)]) {
    if (AIRail.AreTilesConnected(fromPrev, fromTile, mid) &&
        AIRail.AreTilesConnected(fromTile, mid, toTile) &&
        AIRail.AreTilesConnected(mid, toTile, toNext)) return true;
  }
  return false;
}

function OpexV190Fix2Rollback(placedRails, placedSignals)
{
  for (local s = placedSignals.len() - 1; s >= 0; s--) {
    AIRail.RemoveSignal(placedSignals[s].tile, placedSignals[s].front);
  }
  for (local k = placedRails.len() - 1; k >= 0; k--) {
    local rec = placedRails[k];
    AIRail.RemoveRail(rec.prev, rec.cur, rec.next);
  }
}

/* Le moteur filtre les virages a 90 deg entre DEUX cases adjacentes avec
 * pf.forbid_90_deg=1 (defaut de nos duels). AreTilesConnected ne le fait PAS.
 * Masques OpenTTD 15.3 track_type.h / track_data.h :
 * X=1, Y=2, UPPER=4, LOWER=8, LEFT=16, RIGHT=32 ;
 * X croise Y ; UPPER/LOWER croisent LEFT/RIGHT.
 * Deduction d'un unique track pour un trajet prev-cur-next, y compris sur
 * un aiguillage qui porte plusieurs rails. 0 = trajet illisible. */
function OpexV190Fix2TrackBit(prev, cur, next)
{
  if (!AIMap.IsValidTile(prev) || !AIMap.IsValidTile(cur) ||
      !AIMap.IsValidTile(next) ||
      AIMap.DistanceManhattan(prev, cur) != 1 ||
      AIMap.DistanceManhattan(cur, next) != 1 || prev == next) return 0;
  local ax = AIMap.GetTileX(prev) - AIMap.GetTileX(cur);
  local ay = AIMap.GetTileY(prev) - AIMap.GetTileY(cur);
  local bx = AIMap.GetTileX(next) - AIMap.GetTileX(cur);
  local by = AIMap.GetTileY(next) - AIMap.GetTileY(cur);
  if (ay == 0 && by == 0 && ax == -bx) return 1; // X : E-W
  if (ax == 0 && bx == 0 && ay == -by) return 2; // Y : N-S
  if ((ax == -1 && by == -1) || (bx == -1 && ay == -1)) return 4;  // UPPER : W-N
  if ((ax == 1 && by == 1) || (bx == 1 && ay == 1)) return 8;     // LOWER : E-S
  if ((ay == -1 && bx == 1) || (by == -1 && ax == 1)) return 16;  // LEFT : N-E
  if ((ax == -1 && by == 1) || (bx == -1 && ay == 1)) return 32;  // RIGHT : W-S
  return 0;
}

function OpexV190Fix2TurnsSafe(path)
{
  if (path.len() < 5) return false;
  local prevBit = OpexV190Fix2TrackBit(path[0], path[1], path[2]);
  if (prevBit == 0) return false;
  for (local i = 2; i < path.len() - 1; i++) {
    local bit = OpexV190Fix2TrackBit(path[i - 1], path[i], path[i + 1]);
    if (bit == 0) return false;
    if ((prevBit == 1 && bit == 2) || (prevBit == 2 && bit == 1) ||
        ((prevBit == 4 || prevBit == 8) && (bit == 16 || bit == 32)) ||
        ((prevBit == 16 || prevBit == 32) && (bit == 4 || bit == 8))) return false;
    prevBit = bit;
  }
  return true;
}

/* Ne pas reutiliser le constructeur diagonal V181 tel quel : il accepte une
 * case intermediaire deja occupee par une autre voie OpexAI. Le prefiltre
 * FIX2 n'autorise qu'une case VIERGE, mais V181 pourrait choisir l'autre.
 * Chaque tentative garde sa propre transaction pour annuler les segments
 * partiels avant de tester l'autre milieu. */
function OpexV190Fix2TrySwitch(fromPrev, fromTile, toTile, toNext,
                              placedRails, isSimulation = false,
                              farPrev = null, farNext = null)
{
  /* Sans case exterieure, un coude fatal juste AVANT ou APRES la
   * jonction echappe au controle. Le retour B1 -> B2 du seed512 est
   * invalide (LOWER -> LEFT et RIGHT -> UPPER), malgre ses rails joints. */
  if (farPrev == null || farNext == null) return false;
  local dist = AIMap.DistanceManhattan(fromTile, toTile);
  if (dist == 1) {
    if (!OpexV190Fix2TurnsSafe([farPrev, fromPrev, fromTile,
                                toTile, toNext, farNext])) return false;
    return OpexV181TryBuildSwitch(fromPrev, fromTile, toTile, toNext,
                                 placedRails, isSimulation);
  }
  if (dist != 2) return false;
  local x1 = AIMap.GetTileX(fromTile);
  local y1 = AIMap.GetTileY(fromTile);
  local x2 = AIMap.GetTileX(toTile);
  local y2 = AIMap.GetTileY(toTile);
  if (abs(x1 - x2) != 1 || abs(y1 - y2) != 1) return false;

  foreach (mid in [AIMap.GetTileIndex(x1, y2), AIMap.GetTileIndex(x2, y1)]) {
    if (!AIMap.IsValidTile(mid) || !AITile.IsBuildable(mid) ||
        AITile.GetSlope(mid) != AITile.SLOPE_FLAT ||
        AITile.HasTransportType(mid, AITile.TRANSPORT_RAIL)) continue;
    if (!OpexV190Fix2TurnsSafe([farPrev, fromPrev, fromTile, mid,
                                toTile, toNext, farNext])) continue;
    local subRecords = [];
    local ok = OpexV181TryBuildSwitchSegment(fromPrev, fromTile, mid,
                                            subRecords, isSimulation);
    if (ok) ok = OpexV181TryBuildSwitchSegment(fromTile, mid, toTile,
                                              subRecords, isSimulation);
    if (ok) ok = OpexV181TryBuildSwitchSegment(mid, toTile, toNext,
                                              subRecords, isSimulation);
    if (ok) {
      if (!isSimulation && placedRails != null) {
        foreach (rec in subRecords) placedRails.append(rec);
      }
      return true;
    }
    if (!isSimulation) OpexV190Fix2Rollback(subRecords, []);
  }
  return false;
}

/* Renvoie null pour une entree PBS sur structure ou courbe incertaine.
 * Aucun repli en PBS bidirectionnel, qui autoriserait le contre-sens. */
function OpexV190Fix2PlaceSignal(tiles, index, toward, placedSignals)
{
  if (index <= 1 || index >= tiles.len() - 2) return false;
  local tile = tiles[index];
  local prev = tiles[index - 1];
  local next = tiles[index + 1];
  /* AIRail.front est le cote vers lequel REGARDE le signal, donc celui
   * d'ou approche la locomotive. Voie1 croissante : arrivee depuis prev ;
   * voie2 decroissante : arrivee depuis next. */
  local front = toward > 0 ? prev : next;
  if (!AIMap.IsValidTile(tile) || AIMap.DistanceManhattan(prev, tile) != 1 ||
      AIMap.DistanceManhattan(tile, next) != 1 ||
      AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile) ||
      !AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) ||
      OpexTileTrackCount(tile) != 1 ||
      !AIRail.AreTilesConnected(prev, tile, next) ||
      AIRail.GetSignalType(tile, prev) != AIRail.SIGNALTYPE_NONE ||
      AIRail.GetSignalType(tile, next) != AIRail.SIGNALTYPE_NONE) return false;
  if (!("SIGNALTYPE_PBS_ONEWAY" in AIRail) ||
      !AIRail.BuildSignal(tile, front, AIRail.SIGNALTYPE_PBS_ONEWAY)) return false;
  if (AIRail.GetSignalType(tile, front) != AIRail.SIGNALTYPE_PBS_ONEWAY) {
    AIRail.RemoveSignal(tile, front);
    return false;
  }
  placedSignals.append({ tile = tile, front = front });
  return true;
}

/* Un obstacle ponctuel (pont, courbe, rail non signalable) ne doit pas
 * condamner tous les PBS : chercher un candidat dans le bloc de longueur
 * spacing, sans rapprocher les signaux consecutifs sous ce minimum. */
function OpexV190Fix2PlaceSignalWindow(tiles, start, end, step, toward,
                                      placedSignals)
{
  for (local k = start; step > 0 ? k <= end : k >= end; k += step) {
    if (OpexV190Fix2PlaceSignal(tiles, k, toward, placedSignals)) return k;
  }
  return -1;
}

/* Un StationID partage entre deux quais ne contraint pas YAPF au sens de
 * circulation. Poser un waypoint sur CHAQUE branche directionnelle oblige
 * l'ordre A -> WP_AB -> B -> WP_BA -> A, sans arret intermediaire.
 * Un waypoint exige une voie droite sans signal et conserve le rail en place.
 * Les deux waypoints sont poses avant de modifier les ordres des trains. */
function OpexV190Fix2BuildWaypoint(tiles, start, end, step, placedWaypoints)
{
  for (local i = start; step > 0 ? i <= end : i >= end; i += step) {
    if (i <= 1 || i >= tiles.len() - 2) continue;
    local tile = tiles[i];
    local prev = tiles[i - 1];
    local next = tiles[i + 1];
    if (!AIRail.IsRailTile(tile) || AIRail.IsRailStationTile(tile) ||
        AIRail.IsRailDepotTile(tile) || AIRail.IsRailWaypointTile(tile) ||
        AIBridge.IsBridgeTile(tile) || AITunnel.IsTunnelTile(tile) ||
        OpexTileTrackCount(tile) != 1 ||
        AITile.GetOwner(tile) != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF) ||
        !AIRail.AreTilesConnected(prev, tile, next)) continue;
    local tracks = AIRail.GetRailTracks(tile);
    if (tracks != AIRail.RAILTRACK_NW_SE && tracks != AIRail.RAILTRACK_NE_SW) continue;
    if (AIRail.GetSignalType(tile, prev) != AIRail.SIGNALTYPE_NONE ||
        AIRail.GetSignalType(tile, next) != AIRail.SIGNALTYPE_NONE) continue;
    if (!AIRail.BuildRailWaypoint(tile)) continue;
    if (!AIRail.IsRailWaypointTile(tile) ||
        !AIWaypoint.IsValidWaypoint(AIWaypoint.GetWaypointID(tile))) {
      AIRail.RemoveRailWaypointTileRectangle(tile, tile, true);
      continue;
    }
    placedWaypoints.append(tile);
    return tile;
  }
  return null;
}

function OpexV190Fix2RestoreOrders(vehicles)
{
  local ok = true;
  foreach (train in vehicles) {
    if (!AIVehicle.IsValidVehicle(train)) { ok = false; continue; }
    if (AIOrder.GetOrderCount(train) == 4 && AIOrder.IsGotoWaypointOrder(train, 3)) {
      if (!AIOrder.RemoveOrder(train, 3)) ok = false;
    }
    if (AIOrder.GetOrderCount(train) == 3 && AIOrder.IsGotoWaypointOrder(train, 1)) {
      if (!AIOrder.RemoveOrder(train, 1)) ok = false;
    }
    if (AIOrder.GetOrderCount(train) != 2 ||
        !AIOrder.IsGotoStationOrder(train, 0) ||
        !AIOrder.IsGotoStationOrder(train, 1)) ok = false;
  }
  return ok;
}

function OpexV190Fix2RollbackGuidance(vehicles, placedWaypoints,
                                     placedRails, placedSignals)
{
  local ok = OpexV190Fix2RestoreOrders(vehicles);
  for (local i = placedWaypoints.len() - 1; i >= 0; i--) {
    local tile = placedWaypoints[i];
    if (AIRail.IsRailWaypointTile(tile) &&
        !AIRail.RemoveRailWaypointTileRectangle(tile, tile, true)) ok = false;
    if (AIRail.IsRailWaypointTile(tile)) ok = false;
  }
  OpexV190Fix2Rollback(placedRails, placedSignals);
  return ok;
}

function OpexV190Fix2GuideOrders(vehicles, waypointAB, waypointBA,
                                stationA, stationB)
{
  local waypointIdAB = AIWaypoint.GetWaypointID(waypointAB);
  local waypointIdBA = AIWaypoint.GetWaypointID(waypointBA);
  if (!AIWaypoint.IsValidWaypoint(waypointIdAB) ||
      !AIWaypoint.IsValidWaypoint(waypointIdBA) ||
      waypointIdAB == waypointIdBA) return false;
  foreach (train in vehicles) {
    if (!AIOrder.InsertOrder(train, 1, waypointAB, AIOrder.OF_NONE) ||
        !AIOrder.AppendOrder(train, waypointBA, AIOrder.OF_NONE)) return false;
    if (AIOrder.GetOrderCount(train) != 4 ||
        !AIOrder.IsGotoStationOrder(train, 0) ||
        !AIOrder.IsGotoWaypointOrder(train, 1) ||
        !AIOrder.IsGotoStationOrder(train, 2) ||
        !AIOrder.IsGotoWaypointOrder(train, 3) ||
        AIStation.GetStationID(AIOrder.GetOrderDestination(train, 0)) != stationA ||
        AIStation.GetStationID(AIOrder.GetOrderDestination(train, 2)) != stationB ||
        AIWaypoint.GetWaypointID(AIOrder.GetOrderDestination(train, 1)) != waypointIdAB ||
        AIWaypoint.GetWaypointID(AIOrder.GetOrderDestination(train, 3)) != waypointIdBA)
      return false;
  }
  return true;
}

/* Des indices distants ne garantissent pas la separation spatiale lorsque
 * le trace longe une boucle : eviter tout chevauchement des aiguillages. */
function OpexV190Fix2PairSafe(a, b, tiles1, tiles2, clear)
{
  if (b.i1 - a.i1 <= 2 * clear + 4 ||
      b.i2 - a.i2 <= 2 * clear + 4) return false;
  foreach (left in [tiles1[a.i1], tiles2[a.i2]]) {
    foreach (right in [tiles1[b.i1], tiles2[b.i2]]) {
      if (AIMap.DistanceManhattan(left, right) <= 2) return false;
    }
  }
  return true;
}

/* Selectionner les deux raccordements source A2->voie1 et destination
 * B1->voie2, sans retour A/B supplementaire (la rame inverse en gare).
 * La zone de gorge avant aiguillage reste bidirectionnelle. */
function OpexV190Fix2BuildDirectional(line, depot1, depot2, trainTiles, diag = null)
{
  local placedRails = [];
  local placedSignals = [];
  if (!OpexV190VerifyIndependentDouble(line, depot1, depot2) ||
      !("vehicles" in line) || line.vehicles == null || line.vehicles.len() < 2) {
    if (diag != null) diag.step <- "DIRECTIONAL_PRECHECK";
    return false;
  }
  local stationA = AIStation.GetStationID(line.stationA);
  local stationB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB) ||
      stationA == stationB || line.vehicles[0] == line.vehicles[1]) {
    if (diag != null) diag.step <- "DIRECTIONAL_INVALID_STATIONS";
    return false;
  }
  foreach (train in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(train) || AIOrder.GetOrderCount(train) != 2 ||
        !AIOrder.IsGotoStationOrder(train, 0) ||
        !AIOrder.IsGotoStationOrder(train, 1) ||
        AIStation.GetStationID(AIOrder.GetOrderDestination(train, 0)) != stationA ||
        AIStation.GetStationID(AIOrder.GetOrderDestination(train, 1)) != stationB) {
      if (diag != null) diag.step <- "DIRECTIONAL_INVALID_ORDERS";
      return false;
    }
  }
  if (trainTiles < 1) trainTiles = 1;
  local tiles1 = line.tiles1;
  local tiles2 = line.tiles2;
  local last1 = tiles1.len() - 1;
  local last2 = tiles2.len() - 1;
  local clear = trainTiles + 2;
  local switchA = null;
  local switchB = null;
  local candidatesA = [];
  local candidatesB = [];
  local candidateLimit = 64;
  local minIndex = clear + 2;
  local maxIndex = minIndex + 24;
  {
    local test = AITestMode();
    for (local i2 = minIndex; i2 <= maxIndex && i2 < last2 - clear &&
                     candidatesA.len() < candidateLimit; i2++) {
      for (local i1 = minIndex; i1 <= maxIndex && i1 < last1 - clear &&
                       candidatesA.len() < candidateLimit; i1++) {
        if (OpexV190Fix2SwitchSafe(tiles2[i2 - 1], tiles2[i2], tiles2[i2 + 1],
                                    tiles1[i1 - 1], tiles1[i1], tiles1[i1 + 1]) &&
            OpexV190Fix2TrySwitch(tiles2[i2 - 1], tiles2[i2], tiles1[i1],
                tiles1[i1 + 1], null, true, tiles2[i2 - 2], tiles1[i1 + 2])) {
          candidatesA.append({ i1 = i1, i2 = i2 });
        }
      }
    }
    for (local d1 = minIndex; d1 <= maxIndex && d1 < last1 - clear &&
                     candidatesB.len() < candidateLimit; d1++) {
      for (local d2 = minIndex; d2 <= maxIndex && d2 < last2 - clear &&
                       candidatesB.len() < candidateLimit; d2++) {
        local i1 = last1 - d1;
        local i2 = last2 - d2;
        if (OpexV190Fix2SwitchSafe(tiles1[i1 + 1], tiles1[i1], tiles1[i1 - 1],
                                    tiles2[i2 + 1], tiles2[i2], tiles2[i2 - 1]) &&
            OpexV190Fix2TrySwitch(tiles1[i1 + 1], tiles1[i1], tiles2[i2],
                tiles2[i2 - 1], null, true, tiles1[i1 + 2], tiles2[i2 - 2])) {
          candidatesB.append({ i1 = i1, i2 = i2 });
        }
      }
    }
  }
  /* Ne pas retenir aveuglement les deux premiers raccordements : chercher
   * une PAIRE compatible, avec borne fixe pour garder un cout raisonnable. */
  foreach (a in candidatesA) {
    foreach (b in candidatesB) {
      if (!OpexV190Fix2PairSafe(a, b, tiles1, tiles2, clear)) continue;
      switchA = a;
      switchB = b;
      break;
    }
    if (switchA != null) break;
  }
  if (switchA == null || switchB == null) {
    if (diag != null) diag.step <- "DIRECTIONAL_NO_SAFE_SWITCH_PAIR";
    if (DECISION_LOG) OpexDecide("V190_FIX", "phase=pair_reject"
        + " candidates_a=" + candidatesA.len() + " candidates_b=" + candidatesB.len());
    return false;
  }

  local ok = OpexV190Fix2TrySwitch(tiles2[switchA.i2 - 1], tiles2[switchA.i2],
                                   tiles1[switchA.i1], tiles1[switchA.i1 + 1],
                                   placedRails, false, tiles2[switchA.i2 - 2],
                                   tiles1[switchA.i1 + 2]);
  if (ok) ok = OpexV190Fix2TrySwitch(tiles1[switchB.i1 + 1], tiles1[switchB.i1],
                                     tiles2[switchB.i2], tiles2[switchB.i2 - 1],
                                     placedRails, false, tiles1[switchB.i1 + 2],
                                     tiles2[switchB.i2 - 2]);
  if (ok) ok = OpexV190Fix2SwitchConnected(tiles2[switchA.i2 - 1], tiles2[switchA.i2],
                                           tiles1[switchA.i1], tiles1[switchA.i1 + 1]);
  if (ok) ok = OpexV190Fix2SwitchConnected(tiles1[switchB.i1 + 1], tiles1[switchB.i1],
                                           tiles2[switchB.i2], tiles2[switchB.i2 - 1]);
  if (!ok) {
    if (diag != null) diag.step <- "DIRECTIONAL_SWITCH_BUILD";
    OpexV190Fix2Rollback(placedRails, placedSignals);
    return false;
  }

  /* Sens reel de la voie1 : A -> B (PBS face a prev),
   * voie2 : B -> A (PBS face a next), comme V181 et AIRail. */
  local spacing = clear > 7 ? clear : 7;
  local count1 = 0;
  local count2 = 0;
  for (local k = switchA.i1 + clear; k <= switchB.i1 - clear; ) {
    local nextSignal = OpexV190Fix2PlaceSignalWindow(tiles1, k,
        (k + spacing - 1 < switchB.i1 - clear) ? k + spacing - 1 : switchB.i1 - clear,
        1, 1, placedSignals);
    if (nextSignal < 0) { ok = false; break; }
    count1++;
    k = nextSignal + spacing;
  }
  if (ok) {
    for (local k = switchB.i2 - clear; k >= switchA.i2 + clear; ) {
      local nextSignal = OpexV190Fix2PlaceSignalWindow(tiles2, k,
          (k - spacing + 1 > switchA.i2 + clear) ? k - spacing + 1 : switchA.i2 + clear,
          -1, -1, placedSignals);
      if (nextSignal < 0) { ok = false; break; }
      count2++;
      k = nextSignal - spacing;
    }
  }
  if (!ok || count1 < 1 || count2 < 1) {
    if (diag != null) diag.step <- "DIRECTIONAL_PBS_BUILD";
    OpexV190Fix2Rollback(placedRails, placedSignals);
    return false;
  }

  local placedWaypoints = [];
  local waypointAB = OpexV190Fix2BuildWaypoint(tiles1, switchA.i1 + clear,
      switchB.i1 - clear, 1, placedWaypoints);
  local waypointBA = OpexV190Fix2BuildWaypoint(tiles2, switchB.i2 - clear,
      switchA.i2 + clear, -1, placedWaypoints);
  if (waypointAB == null || waypointBA == null ||
      !OpexV190Fix2GuideOrders(line.vehicles, waypointAB, waypointBA,
                                stationA, stationB)) {
    if (diag != null) diag.step <- "DIRECTIONAL_WAYPOINT_ORDERS";
    if (!OpexV190Fix2RollbackGuidance(line.vehicles, placedWaypoints,
                                      placedRails, placedSignals) && diag != null)
      diag.step <- "DIRECTIONAL_GUIDANCE_ROLLBACK_FAILED";
    return false;
  }
  if (DECISION_LOG) OpexDecide("V190_FIX", "phase=directional ok=1"
      + " a1=" + switchA.i1 + " a2=" + switchA.i2
      + " b1=" + switchB.i1 + " b2=" + switchB.i2
      + " pbs_aboard=" + count1 + " pbs_return=" + count2
      + " trains=" + line.vehicles.len() + " track1=A_to_B track2=B_to_A"
      + " waypoint_ab=" + waypointAB + " waypoint_ba=" + waypointBA);
  return true;
}
