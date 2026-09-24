/* Etage 3b : une liaison aerienne passagers, sans pathfinding.
 *
 * L'avion est le contrepoint du rail : il n'y a pas de recherche A*, mais les aires de
 * construction et la compatibilite aeroport/appareil sont des preconditions reelles.
 * Regle : 2 types principaux d'avions et d'aeroports (les gros et les petits).
 * Les gros avions ne vont QUE dans les grands aeroports.
 * La construction elle-meme est transactionnelle : avion vendu, puis aeroports
 * retires, au moindre echec apres le premier aeroport.
 */

AIR_HUB_NEW_SITE_POOL <- 12;
AIR_SITE_RADIUS <- 25;
AIR_TOWN_MIN_DISTANCE <- 32;
AIR_MAX_SITE_PROBES <- 1500;
/* C78.4 : une tranche AIR grande carte peut traverser plusieurs suspensions
 * automatiques NoAI, mais reste bornee a environ un jour de jeu. Les mesures
 * C39/C76 utilisent ~186k opcodes/jour ; 180k garde une petite marge. */
AIR_PLAN_SLICE_OPS <- 180000;
AIR_MAX_PLANES_PER_ROUTE <- 16;
AIR_PLAN_DIAG_SEQ <- 0;
/* Plafond de distance aerienne (0 = illimite, docs/taches.md C6 supprime) */
AIR_MAX_DISTANCE <- 0;
/* Ordre de chargement passagers aerien (0 = aucun, 1 = deux extremites, 2 = premiere extremite seulement, comme AAAHogEx) */
AIR_FULL_LOAD <- 0;
/* Cache de sites d'aeroport par ville et type d'aeroport (C33.1) */
AIR_SITE_CACHE_ENABLED <- true;
AIR_SITE_CACHE <- {};
/* C36.3 : Filtre d'emprise sans AITestMode avant la sonde (defaut 1, banc 20x10). */
AIR_CHEAP_SITE <- true;
/* C33.2 : Arrets de bus joints au chantier aeroport */
AIR_JOINED_STOPS <- false;

function OpexAirResetSiteCache()
{
  AIR_SITE_CACHE.clear();
}

/* Un test de site n'est qu'une prediction : si le chantier reel le contredit, ne jamais
 * re-servir exactement cette ancre au prochain rafraichissement. On efface seulement l'entree
 * qui pointe encore vers l'ancre refusee (un autre calcul peut deja l'avoir remplacee), afin de
 * forcer la recherche d'une alternative dans cette meme ville et pour ce meme type d'aeroport. */
function OpexAirInvalidateCachedSite(site, airport)
{
  if (!AIR_SITE_CACHE_ENABLED || site == null) return;
  local key = site.town.id + "_" + airport.type;
  if (key in AIR_SITE_CACHE && AIR_SITE_CACHE[key] == site.anchor) delete AIR_SITE_CACHE[key];
}

/* Distance euclidienne exacte à vol d'oiseau pour la cinématique et le paiement aérien :
 * sqrt(dx^2 + dy^2) approximé par 0.414 * min(dx, dy) + max(dx, dy) */
function OpexFlightDistance(tileA, tileB)
{
  local dx = abs(AIMap.GetTileX(tileA) - AIMap.GetTileX(tileB));
  local dy = abs(AIMap.GetTileY(tileA) - AIMap.GetTileY(tileB));
  local minD = dx < dy ? dx : dy;
  local maxD = dx > dy ? dx : dy;
  local dist = (minD * 414) / 1000 + maxD;
  return dist > 0 ? dist : 1;
}

/* Distance Manhattan d'une tuile au rectangle [anchor, anchor + width/height - 1]. */
function OpexAirDistanceToRect(tile, anchor, width, height)
{
  local x = AIMap.GetTileX(tile);
  local y = AIMap.GetTileY(tile);
  local left = AIMap.GetTileX(anchor);
  local top = AIMap.GetTileY(anchor);
  local right = left + width - 1;
  local bottom = top + height - 1;
  local dx = x < left ? left - x : (x > right ? x - right : 0);
  local dy = y < top ? top - y : (y > bottom ? y - bottom : 0);
  return dx + dy;
}

/* B9/G4 : toutes les demandes AIR sont exprimees en production mensuelle de
 * cargo couverte. Pour un site neuf, l'emprise et le type d'aeroport sont deja
 * connus avant construction, donc cette grandeur est mesurable sans proxy de
 * population. */
function OpexAirAirportCatchmentProduction(airportTile, airportType, cargo)
{
  if (!AIMap.IsValidTile(airportTile) || cargo < 0
      || !AIAirport.IsValidAirportType(airportType)) return 0;
  local w = AIAirport.GetAirportWidth(airportType);
  local h = AIAirport.GetAirportHeight(airportType);
  local radius = AIAirport.GetAirportCoverageRadius(airportType);
  return AITile.GetCargoProduction(airportTile, cargo, w, h, radius);
}

/* Production de l'union reelle d'une station, pieces jointes comprises.
 * Chaque tuile est comptee une fois par AITileList_StationCoverage. */
function OpexAirStationCatchmentProduction(stationId, cargo)
{
  if (!AIStation.IsValidStation(stationId) || cargo < 0) return 0;
  local total = 0;
  local coverageTiles = AITileList_StationCoverage(stationId);
  foreach (coverageTile, value in coverageTiles) {
    total += AITile.GetCargoProduction(coverageTile, cargo, 1, 1, 0);
  }
  return total;
}

function OpexAirJoinedMarginalProduction(stationId, airportTile, airportType, cargo)
{
  local unionProduction = OpexAirStationCatchmentProduction(stationId, cargo);
  local airportProduction = OpexAirAirportCatchmentProduction(airportTile, airportType, cargo);
  local marginal = unionProduction - airportProduction;
  return marginal > 0 ? marginal : 0;
}

function OpexAirCatchmentProbeEndpoint(catalog, stationId, airportTile, townId,
                                      rawJoinedPax, modelJoinedPax, reused, endpoint)
{
  if (!AIR_CATCHMENT_PROBE) return 0;
  if (!AIStation.IsValidStation(stationId) || !AIAirport.IsAirportTile(airportTile)
      || !AITown.IsValidTown(townId)) return 0;
  local t0 = AIController.GetTick();
  local l0 = AIController.GetOpsTillSuspend();
  local airportType = AIAirport.GetAirportType(airportTile);
  local w = AIAirport.GetAirportWidth(airportType);
  local h = AIAirport.GetAirportHeight(airportType);
  local airportRadius = AIAirport.GetAirportCoverageRadius(airportType);
  local townTile = AITown.GetLocation(townId);
  local airportPax = AITile.GetCargoProduction(airportTile, catalog.paxCargo, w, h, airportRadius);
  local airportMail = 0;
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    airportMail = AITile.GetCargoProduction(airportTile, catalog.mailCargo, w, h, airportRadius);
  }
  local unionPax = 0;
  local unionMail = 0;
  local unionTiles = 0;
  local townCenterInUnion = false;
  local coverageTiles = AITileList_StationCoverage(stationId);
  foreach (coverageTile, value in coverageTiles) {
    unionTiles++;
    if (coverageTile == townTile) townCenterInUnion = true;
    unionPax += AITile.GetCargoProduction(coverageTile, catalog.paxCargo, 1, 1, 0);
    if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
      unionMail += AITile.GetCargoProduction(coverageTile, catalog.mailCargo, 1, 1, 0);
    }
  }
  local marginalPax = unionPax - airportPax;
  if (marginalPax < 0) marginalPax = 0;
  local marginalMail = unionMail - airportMail;
  if (marginalMail < 0) marginalMail = 0;
  local rawMinusTrue = reused ? 0 : rawJoinedPax - marginalPax;
  local modelMinusTrue = reused ? 0 : modelJoinedPax - marginalPax;
  local rectDistance = OpexAirDistanceToRect(townTile, airportTile, w, h);
  local airportCenter = airportTile + AIMap.GetTileIndex(w / 2, h / 2);
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - t0;
  local probeOps = elapsed <= 0
      ? l0 - left
      : l0 + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
  OpexAirCatchmentLog("AIR_CATCHMENT_ENDPOINT",
      "endpoint=" + endpoint + " station=" + stationId + " town=" + townId
      + " town_tile=" + townTile + " town_pop=" + AITown.GetPopulation(townId)
      + " airport_tile=" + airportTile + " airport_type=" + airportType
      + " airport_w=" + w + " airport_h=" + h + " airport_radius=" + airportRadius
      + " airport_generic_radius=" + AIStation.GetCoverageRadius(AIStation.STATION_AIRPORT)
      + " bus_radius=" + AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP)
      + " rect_distance=" + rectDistance
      + " center_distance=" + AIMap.DistanceManhattan(townTile, airportCenter)
      + " town_center_airport=" + (rectDistance <= airportRadius ? 1 : 0)
      + " town_center_union=" + (townCenterInUnion ? 1 : 0)
      + " coverage_tiles=" + unionTiles
      + " airport_pax_prod=" + airportPax + " union_pax_prod=" + unionPax
      + " joined_marginal_pax=" + marginalPax
      + " model_joined_pax=" + modelJoinedPax + " raw_joined_pax=" + rawJoinedPax
      + " overlap_overcount_pax=" + (rawMinusTrue > 0 ? rawMinusTrue : 0)
      + " raw_undercount_pax=" + (rawMinusTrue < 0 ? -rawMinusTrue : 0)
      + " model_error_pax=" + modelMinusTrue
      + " airport_mail_prod=" + airportMail + " union_mail_prod=" + unionMail
      + " joined_marginal_mail=" + marginalMail
      + " reused=" + (reused ? 1 : 0) + " probe_ops=" + probeOps);
  return probeOps;
}

/* Les plus grosses villes, sans trier le catalogue lui-meme. L'insertion est deterministe et
 * garde l'ordre d'enumeration d'OpenTTD en cas d'egalite de population. */
function OpexAirSortedTowns(towns)
{
  local out = [];
  foreach (town in towns) {
    local pos = out.len();
    while (pos > 0 && out[pos - 1].pop < town.pop) pos--;
    out.insert(pos, town);
  }
  return out;
}

/* C78.3 : le vivier aerien n'a plus de plafond arbitraire en nombre de villes.
 * La capacite spatiale garde le plafond en cellules utile aux petites cartes,
 * puis ajoute une borne lineaire en perimetre pour eviter O(n^2) sur 1024+. */
function OpexAirTownPoolLimit(towns)
{
  if (towns == null || towns.len() == 0) return 0;
  local minDistance = AIR_TOWN_MIN_DISTANCE > 0 ? AIR_TOWN_MIN_DISTANCE : 1;
  local cellsX = (AIMap.GetMapSizeX() + minDistance - 1) / minDistance;
  local cellsY = (AIMap.GetMapSizeY() + minDistance - 1) / minDistance;
  local gridCapacity = cellsX * cellsY;
  local perimeterCapacity = 4 * (cellsX + cellsY);
  local spatialCapacity = gridCapacity < perimeterCapacity ? gridCapacity : perimeterCapacity;
  if (spatialCapacity < 2 && towns.len() >= 2) spatialCapacity = 2;
  return towns.len() < spatialCapacity ? towns.len() : spatialCapacity;
}

function OpexAirTownServed(town, lines, diag = null)
{
  /* Keep the non-diagnostic path byte-for-byte equivalent in its tests and short-circuiting. */
  if (!DECISION_LOG || diag == null) {
    if (lines == null) return false;
    foreach (line in lines) {
      if (!("mode" in line) || line.mode != "air") continue;
      if (AIMap.DistanceManhattan(town.tile, line.originA) < 15) return true;
      if (AIMap.DistanceManhattan(town.tile, line.originB) < 15) return true;
    }
    return false;
  }

  if (lines == null) {
    diag.nullCalls++;
    diag.falseCalls++;
    if (DECISION_LOG && !diag.noAirLogged) {
      diag.noAirLogged = true;
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=null line_count=0"
                 + " air_line_count=0 verdict=0 comparisons=none");
    }
    return false;
  }
  if (lines.len() == 0) diag.emptyCalls++;
  else diag.nonemptyCalls++;

  local comparisons = "";
  local airLineCount = 0;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    local distanceA = AIMap.DistanceManhattan(town.tile, line.originA);
    if (distanceA < 15) {
      diag.trueCalls++;
      return true;
    }
    local distanceB = AIMap.DistanceManhattan(town.tile, line.originB);
    if (distanceB < 15) {
      diag.trueCalls++;
      return true;
    }
    comparisons += " line" + airLineCount
        + "_id=" + (("lineId" in line) ? line.lineId : "none")
        + " line" + airLineCount + "_originA=" + line.originA
        + " line" + airLineCount + "_originB=" + line.originB
        + " line" + airLineCount + "_distA=" + distanceA
        + " line" + airLineCount + "_distB=" + distanceB;
    airLineCount++;
  }
  diag.falseCalls++;
  if (airLineCount == 0 && !diag.noAirLogged) {
    diag.noAirLogged = true;
    if (DECISION_LOG) {
      local linesState = lines.len() == 0 ? "empty" : "nonempty";
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=" + linesState
                 + " line_count=" + lines.len()
                 + " air_line_count=0 verdict=0 comparisons=none");
    }
  }
  /* One record per failed town per OpexAirPlans invocation: repeated combo/site scans compare
   * the same immutable town and lines, so suppressing duplicates loses no comparison. */
  if (airLineCount > 0 && !(town.id in diag.loggedFalseTowns)) {
    diag.loggedFalseTowns[town.id] <- true;
    diag.loggedFalseCount++;
    if (DECISION_LOG) {
      OpexDecide("AIR_TOWN_SERVED", "scan=" + diag.scan + " town_id=" + town.id
                 + " town_tile=" + town.tile + " lines_state=nonempty line_count=" + lines.len()
                 + " air_line_count=" + airLineCount + " verdict=0" + comparisons);
    }
  }
  return false;
}

/* C83.1 : avec la limite historique de deux aeroports par ville, ce signal
 * donne directement le nombre de slots restants. Il n'est valable que lorsque
 * la regle de bruit est desactivee et que le conseil municipal n'est pas en
 * mode permissif (qui leve la limite). */
function OpexAirC83SlotSignalEnabled()
{
  return AIGameSettings.IsValid("economy.station_noise_level")
      && AIGameSettings.GetValue("economy.station_noise_level") == 0
      && AIGameSettings.IsValid("difficulty.town_council_tolerance")
      && AIGameSettings.GetValue("difficulty.town_council_tolerance") != 3;
}

function OpexAirC83SecondSlotOpen(town)
{
  if (!OpexAirC83SlotSignalEnabled() || town == null
      || !("id" in town) || !AITown.IsValidTown(town.id)) return false;
  if (AITown.GetPopulation(town.id) < AIR_EARLY_SLOT_MIN_POP) return false;
  return AITown.GetAllowedNoise(town.id) == 1;
}

/* Plancher des grands aeroports (combo large), 600 aujourd'hui. Point unique :
 * un futur reglage du type V93_AIRPORT_MIN_POP se brancherait ici. */
function OpexAirLargeAirportMinPop()
{
  return 600;
}

/* Plancher de la preemption C83. Le plancher historique reste 600. Si V93 est
 * arme, le plancher minimal de ce reglage remplace les 600, et seulement ici. */
function OpexAirPreemptMinPop()
{
  if (V93_AIRPORT_NO_POP_FLOOR) return V93_AIRPORT_MIN_POP;
  return OpexAirLargeAirportMinPop();
}

/* Plus grande ville encore vide : deux slots libres, population au plancher,
 * aucun aeroport Opex impute a cette ville. Une seule cible. */
function OpexAirPreemptPickTown(towns, ownCounts)
{
  if (!C83_PREEMPT_OPEN || !OpexAirC83SlotSignalEnabled() || towns == null) return null;
  local floor = OpexAirPreemptMinPop();
  local best = null;
  local bestPop = -1;
  foreach (town in towns) {
    if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) continue;
    local pop = AITown.GetPopulation(town.id);
    if (pop < floor) continue;
    if (AITown.GetAllowedNoise(town.id) != 2) continue;
    if (ownCounts != null && (town.id in ownCounts)) continue;
    if (best == null || pop > bestPop || (pop == bestPop && town.id < best.id)) {
      best = town;
      bestPop = pop;
    }
  }
  return best;
}

/* Ville debitée par le moteur pour un aeroport : ClosestTown de l'ancre
 * (CmdBuildAirport), pas GetNearestTown ni la ville commerciale du site. */
function OpexAirSlotTownId(anchor)
{
  if (anchor == null || !AIMap.IsValidTile(anchor)) return -1;
  local townId = AITile.GetClosestTown(anchor);
  if (townId >= 0 && AITown.IsValidTown(townId)) return townId;
  return -1;
}

function OpexAirOwnSlotTownCounts()
{
  local counts = {};
  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local townId = OpexAirSlotTownId(AIStation.GetLocation(st));
    if (townId < 0) continue;
    local n = (townId in counts) ? counts[townId] : 0;
    counts.rawset(townId, n + 1);
  }
  return counts;
}

/* Ville encore disputable : population du plancher grand aeroport, au moins un
 * slot, et aucun aeroport Opex dont l'ancre est imputee a cette ville. */
function OpexAirC83TownContestable(town, ownCounts)
{
  if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) return false;
  if (AITown.GetPopulation(town.id) < OpexAirLargeAirportMinPop()) return false;
  if (AITown.GetAllowedNoise(town.id) < 1) return false;
  if (ownCounts != null && (town.id in ownCounts)) return false;
  return true;
}

/* Meme predicat que la derniere boucle de OpexAirBatchPlanStillLive : une ligne
 * aerienne relie deja les centres-villes (originA/originB), pas les tuiles d'aeroport. */
function OpexAirTownCentersLinked(tileA, tileB, lines)
{
  if (lines == null || tileA == null || tileB == null) return false;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    if ((line.originA == tileA && line.originB == tileB) ||
        (line.originA == tileB && line.originB == tileA)) return true;
  }
  return false;
}

function OpexAirC78NoteNoSite(probes, reason)
{
  if (!C69_BOTTLENECK_PROBE || probes == null) return;
  if ("c78NoSite" in probes) probes.c78NoSite = reason;
  else probes.c78NoSite <- reason;
}

/* C83.1 : petit ensemble surveille par la course reactive. Contrairement a
 * OpexAirSortedTowns, ce helper ne trie jamais tout le catalogue : il maintient
 * seulement les K plus grandes villes, donc O(n*K) avec K=6 au defaut. */
function OpexAirC83WatchTowns(towns)
{
  local best = [];
  if (!OpexAirC83SlotSignalEnabled() || towns == null || AIR_C83_TARGET_TOWNS <= 0) {
    return best;
  }
  local ownCounts = null;
  if (C83_FIXES) ownCounts = OpexAirOwnSlotTownCounts();
  foreach (town in towns) {
    if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) continue;
    local pop = AITown.GetPopulation(town.id);
    if (C83_FIXES) {
      if (!OpexAirC83TownContestable(town, ownCounts)) continue;
    } else if (pop < AIR_EARLY_SLOT_MIN_POP) continue;
    local item = { town = town, pop = pop };
    local pos = best.len();
    while (pos > 0 && best[pos - 1].pop < pop) pos--;
    if (pos >= AIR_C83_TARGET_TOWNS) continue;
    best.insert(pos, item);
    if (best.len() > AIR_C83_TARGET_TOWNS) best.pop();
  }
  local out = [];
  foreach (item in best) out.append(item.town);
  return out;
}

/* 🔴 Une ligne aerienne stocke des TUILES d'aeroport dans stationA/stationB, malgre leur nom :
 * OpexBuildAirRoute calcule bien les StationID (`:831-832`) puis rend `result.stationA = airportA`,
 * la tuile. main.nut lit ces champs comme des tuiles partout (`GetStationID(line.stationA)` en
 * :1046, :1319, :2034) -- la convention "tuile" est donc la bonne. Seul le code de hub ci-dessous
 * les prenait pour des StationID deja resolus, avec trois consequences mesurees le 2026-09-03 :
 *   1. la garde `alreadyConnected` comparait un StationID a une tuile : TOUJOURS fausse, d'ou
 *      NEUF liaisons sur la meme paire de villes (graine 42, 1970-1972) ;
 *   2. la decouverte de hub testait `IsAirportTile()` sur un CENTRE-VILLE : toujours fausse, donc
 *      tous les aeroports tombaient dans le repli "orphelins" avec `routes = 0` code en dur ;
 *   3. `routes = 0` rendait le plafond `maxRoutes` inoperant ET annulait la decote de saturation
 *      `hubMonthly / (routes + 1)`, qui divisait donc toujours par 1.
 * Resoudre la tuile en StationID repare les trois d'un coup. */
function OpexAirLineStationId(line, which)
{
  local tile = (which == 0) ? line.stationA : line.stationB;
  if (tile == null || !AIMap.IsValidTile(tile)) return -1;
  return AIStation.GetStationID(tile);
}

/* Modele unique de temps de vol pour l'economie et le plafond de demande. */
function OpexAirTripModel(speed, capacity, distance)
{
  local effectiveSpeed = speed / 4.0;
  if (effectiveSpeed < 1.0) effectiveSpeed = 1.0;
  local flightDays = distance.tofloat() / (0.036 * effectiveSpeed);
  local airportDelayDays = 3.0;
  local oneWayDays = flightDays + airportDelayDays;
  if (oneWayDays < 1.0) oneWayDays = 1.0;
  local roundTripDays = 2.0 * oneWayDays;
  local tripsPerMonth = 30.4 / oneWayDays;
  return {
    effectiveSpeed = effectiveSpeed, flightDays = flightDays,
    airportDelayDays = airportDelayDays, oneWayDays = oneWayDays,
    roundTripDays = roundTripDays, tripsPerMonth = tripsPerMonth,
    capacityPerPlane = capacity * tripsPerMonth,
  };
}

/* Compte les lignes aeriennes vivantes qui touchent CET aeroport. Les champs stationA/B sont
 * des TUILES : chaque comparaison passe donc par GetStationID, comme le controle des hubs de
 * batch dans main.nut. */
function OpexAirLiveRoutesAtAirport(airportTile, lines)
{
  if (airportTile == null || !AIMap.IsValidTile(airportTile) || lines == null) return 0;
  local station = AIStation.GetStationID(airportTile);
  if (!AIStation.IsValidStation(station)) return 0;
  local routes = 0;
  foreach (other in lines) {
    if (!("mode" in other) || other.mode != "air") continue;
    local live = false;
    if (("vehicles" in other) && other.vehicles != null) {
      foreach (v in other.vehicles) {
        if (AIVehicle.IsValidVehicle(v)) { live = true; break; }
      }
    } else if (("vehicle" in other) && AIVehicle.IsValidVehicle(other.vehicle)) {
      live = true;
    }
    if (!live) continue;
    local otherA = ("stationA" in other) ? OpexAirLineStationId(other, 0) : -1;
    local otherB = ("stationB" in other) ? OpexAirLineStationId(other, 1) : -1;
    if (otherA == station || otherB == station) routes++;
  }
  return routes;
}

/* C16 : Creneau physique d'absorption de la piste (en jours par atterrissage).
 * Tire du modele de cadence d'AAAHogEx (air.nut:10-75). */
function OpexAirportStationDateSpan(airportType)
{
  switch (airportType) {
    case AIAirport.AT_SMALL: return 20;
    case AIAirport.AT_COMMUTER: return 16;
    case AIAirport.AT_LARGE: return 10;
    case AIAirport.AT_METROPOLITAN: return 8;
    case AIAirport.AT_INTERNATIONAL: return 5;
    case AIAirport.AT_INTERCON: return 4;
    default: return 12;
  }
}

/* C16 : Plafond physique de flotte aerienne derive de la CADENCE et non de la demande (docs/taches.md C16).
 * Calcule le nombre maximal d'avions qui peuvent tourner sur la ligne sans creer d'embouteillage
 * dans le ciel (holding pattern), compte tenu de la rotation aller-retour et du partage de piste. */
function OpexAirCadenceCap(line, catalog, lines)
{
  local speed = (("plane" in catalog) && catalog.plane != null) ? catalog.plane.speed : 1;
  local capacity = ("planeCapacity" in line) ? line.planeCapacity : 0;
  if (("vehicles" in line) && line.vehicles != null) {
    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      speed = AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v));
      if (capacity <= 0) capacity = AIVehicle.GetCapacity(v, line.cargo);
      break;
    }
  } else if (("vehicle" in line) && AIVehicle.IsValidVehicle(line.vehicle)) {
    speed = AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(line.vehicle));
    if (capacity <= 0) capacity = AIVehicle.GetCapacity(line.vehicle, line.cargo);
  }
  if (capacity <= 0 && ("plane" in catalog) && catalog.plane != null) {
    capacity = catalog.plane.capacity;
  }
  local distance = OpexFlightDistance(line.stationA, line.stationB);
  local trip = OpexAirTripModel(speed, capacity, distance);
  local roundTripDays = trip.roundTripDays;

  local routesA = OpexAirLiveRoutesAtAirport(line.stationA, lines);
  local routesB = OpexAirLiveRoutesAtAirport(line.stationB, lines);
  if (routesA < 1) routesA = 1;
  if (routesB < 1) routesB = 1;

  local typeA = (line.stationA != null && AIAirport.IsAirportTile(line.stationA))
      ? AIAirport.GetAirportType(line.stationA) : AIAirport.AT_SMALL;
  local typeB = (line.stationB != null && AIAirport.IsAirportTile(line.stationB))
      ? AIAirport.GetAirportType(line.stationB) : AIAirport.AT_SMALL;
  local spanA = OpexAirportStationDateSpan(typeA) * routesA;
  local spanB = OpexAirportStationDateSpan(typeB) * routesB;
  local effectiveSpan = (spanA > spanB) ? spanA : spanB;
  if (effectiveSpan < 1) effectiveSpan = 1;

  local cap = (roundTripDays / effectiveSpan.tofloat()).tointeger() + 1;
  if (cap < 1) cap = 1;
  if (cap > AIR_MAX_PLANES_PER_ROUTE) cap = AIR_MAX_PLANES_PER_ROUTE;
  return cap;
}

function OpexAirAirportAcceptsPlane(airportType, planeType)
{
  if (planeType == AIAirport.PT_SMALL_PLANE) return true;
  return airportType != AIAirport.AT_SMALL && airportType != AIAirport.AT_COMMUTER;
}

/* V86 Variante B : plafond de routes autorisees par type d'aeroport.
 * Si air_hub_max_routes vaut N > 0, le plafond devient min(plafond actuel, N). */
function OpexAirAirportMaxRoutes(airportType)
{
  local defaultCap = (airportType == AIAirport.AT_SMALL || airportType == AIAirport.AT_COMMUTER) ? 4 : 12;
  if (AIR_HUB_MAX_ROUTES > 0) {
    return AIR_HUB_MAX_ROUTES < defaultCap ? AIR_HUB_MAX_ROUTES : defaultCap;
  }
  return defaultCap;
}

/* C36.3 : l'emprise est-elle constructible SANS AITestMode ni LevelTiles ?
 * IsBuildableRectangle accepte Clear + Trees (BuildAirport les rase) et le cote, et refuse
 * maisons, industries, rail, mer, riviere. Le cote passe IsBuildable : on l'exclut a part,
 * avec mer/canal/riviere, sur CHAQUE tuile -- pas seulement les deux coins. C4 (span >= 2)
 * reste. Un hit ici n'est pas encore un site : OpexAirFindSite confirme en une sonde. */
function OpexAirFootprintCheapOk(anchor, airport)
{
  local w = airport.width;
  local h = airport.height;
  if (!AITile.IsBuildableRectangle(anchor, w, h)) return false;
  local minH = AITile.GetMinHeight(anchor);
  local maxH = AITile.GetMaxHeight(anchor);
  local offX = w - 1;
  local offY = h - 1;
  for (local tx = 0; tx <= offX; tx++) {
    for (local ty = 0; ty <= offY; ty++) {
      local t = anchor + AIMap.GetTileIndex(tx, ty);
      if (!AIMap.IsValidTile(t)) return false;
      if (AITile.IsWaterTile(t) || AITile.IsCoastTile(t) || AITile.IsRiverTile(t)) return false;
      local tMin = AITile.GetMinHeight(t);
      local tMax = AITile.GetMaxHeight(t);
      if (tMin < minH) minH = tMin;
      if (tMax > maxH) maxH = tMax;
      if (maxH - minH >= 2) return false;
    }
  }
  return true;
}

function OpexAirFootprintEnd(anchor, airport)
{
  /* AITile.LevelTiles prend le coin terminal de TERRASSEMENT, pas la derniere
   * tuile de l'aeroport. Pour une emprise w x h il est donc a +(w,h) :
   * SuperLib.Tile.CostToFlattern et AAAHogEx::AirStation.Build emploient tous
   * deux cette convention. L'ancienne borne +(w-1,h-1) laissait la rangee et
   * la colonne finales en pente, puis BuildAirport echouait ERR_FLAT_LAND_REQUIRED
   * bien que notre sonde ait annonce le site nivelable. */
  return anchor + AIMap.GetTileIndex(airport.width, airport.height);
}

function OpexAirFootprintIsFlat(anchor, airport)
{
  /* CheckFlatLandAirport compare le z du coin haut de chaque tuile (allowed_z), pas l'absence
   * de pente : min==max par tuile est plus dur que le moteur. */
  local z = AITile.GetMaxHeight(anchor);
  local offX = airport.width - 1;
  local offY = airport.height - 1;
  for (local tx = 0; tx <= offX; tx++) {
    for (local ty = 0; ty <= offY; ty++) {
      local t = anchor + AIMap.GetTileIndex(tx, ty);
      if (!AIMap.IsValidTile(t)) return false;
      if (AITile.GetMaxHeight(t) != z) return false;
    }
  }
  return true;
}

/* G7§2 : Sonde AITestMode de nivelabilite, sans modifier la carte ni depenser de tresorerie.
 * Retourne true si LevelTiles REUSSIRAIT (terrain deja plat, ou nivelable, ou autorisation
 * achetable). Utilise par OpexAirFindSite pendant la generation, avant election. */
function OpexAirCanLevelFootprint(anchor, airport, townId = -1)
{
  local end = OpexAirFootprintEnd(anchor, airport);
  if (!AIMap.IsValidTile(end)) return false;
  if (OpexAirFootprintIsFlat(anchor, airport)) return true;
  local probe = AITestMode();
  if (AITile.LevelTiles(anchor, end)) return true;
  local err = AIError.GetLastError();
  if (err == AITile.ERR_AREA_ALREADY_FLAT) return true;
  /* L'autorite locale refuse mais un boost arbre le resoudrait au moment de construire. */
  if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES && townId >= 0) return true;
  return false;
}

/* Nivellement REEL (pas AITestMode) de l'emprise exacte, puis verification min=max.
 * LevelTiles en test ne change pas la carte ; BuildAirport ne terrasse pas. */
function OpexAirLevelFootprint(anchor, airport, townId = -1)
{
  local end = OpexAirFootprintEnd(anchor, airport);
  if (!AIMap.IsValidTile(end)) return false;
  if (OpexAirFootprintIsFlat(anchor, airport)) return true;
  if (!AITile.LevelTiles(anchor, end)) {
    local err = AIError.GetLastError();
    if (err == AITile.ERR_AREA_ALREADY_FLAT) return OpexAirFootprintIsFlat(anchor, airport);
    if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES && townId >= 0) {
      OpexBoostTownRating(townId, 800, 40);
      if (!AITile.LevelTiles(anchor, end)) return false;
    } else {
      return false;
    }
  }
  return OpexAirFootprintIsFlat(anchor, airport);
}

/* C78.2 : ERR_STATION_TOO_MANY_STATIONS_IN_TOWN est une propriete de la ville,
 * pas de l'ancre testee. Une seule reponse du moteur suffit donc a exclure cette
 * ville pour tout le scan courant, y compris pour les autres types d'aeroport. */
function OpexAirRememberTownStationLimit(probes, town, error)
{
  if (error != AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) return false;
  if (probes != null && ("stationLimitedTowns" in probes)) {
    probes.stationLimitedTowns.rawset(town.id, true);
  }
  OpexAirC78NoteNoSite(probes, "no_site_slot");
  return true;
}

/* Trouve la premiere ancre constructible, par couronnes autour de la ville. L'ancre est bien le
 * coin haut-gauche attendu par BuildAirport. La couverture est testee contre le rectangle entier,
 * pas seulement contre son coin. */
function OpexAirFindSite(town, airport, probes, requiredSlotTownId = -1)
{
  if (C60_TOWN_RATING_PROBE) {
    OpexC60ObserveTownRating("air", "find_site", town.id);
  }
  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
  if (probes != null && ("stationLimitedTowns" in probes)
      && (town.id in probes.stationLimitedTowns)) return null;
  local key = town.id + "_" + airport.type;
  /* C83 cible : le cache historique est indexe par ville commerciale/type.
   * Une course au slot exige en plus ClosestTown(anchor)==ville cible ; ne pas
   * reutiliser ni ecrire ce cache dans ce chemin rare. */
  local useSiteCache = AIR_SITE_CACHE_ENABLED && requiredSlotTownId < 0;
  if (useSiteCache && (key in AIR_SITE_CACHE)) {
    local cachedAnchor = AIR_SITE_CACHE[key];
    if (cachedAnchor == null) {
      return null;
    }
    local offX = airport.width - 1;
    local offY = airport.height - 1;
    local mapX = AIMap.GetMapSizeX();
    local mapY = AIMap.GetMapSizeY();
    local ax = AIMap.GetTileX(cachedAnchor);
    local ay = AIMap.GetTileY(cachedAnchor);
    if (ax + offX < mapX && ay + offY < mapY) {
      local c4 = cachedAnchor + AIMap.GetTileIndex(offX, offY);
      if (!AITile.IsWaterTile(cachedAnchor) && !AITile.IsCoastTile(cachedAnchor) &&
          !AITile.IsWaterTile(c4) && !AITile.IsCoastTile(c4) &&
          AIAirport.GetNearestTown(cachedAnchor, airport.type) == town.id &&
          (!AIR_CHEAP_SITE || OpexAirFootprintCheapOk(cachedAnchor, airport))) {
        local ok = false;
        if (AIR_CHEAP_SITE) {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(cachedAnchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       OpexAirCanLevelFootprint(cachedAnchor, airport, town.id)) {
              /* G7§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              ok = true;
            }
          }
        } else {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(cachedAnchor, OpexAirFootprintEnd(cachedAnchor, airport));
              ok = AIAirport.BuildAirport(cachedAnchor, airport.type, AIStation.STATION_NEW);
              if (!ok) {
                local retryErr = AIError.GetLastError();
                if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                  AIR_SITE_CACHE[key] <- null;
                  return null;
                }
                if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
              }
            }
          }
        }
        if ("tested" in probes) probes.tested++;
        if (ok && C83_FIXES && OpexAirSlotTownId(cachedAnchor) != town.id) ok = false;
        if (ok) return { town = town, anchor = cachedAnchor };
      }
    }
    delete AIR_SITE_CACHE[key];
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
    for (local dx = -r; dx <= r; dx++) {
      for (local dy = -r; dy <= r; dy++) {
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
        if (C83_FIXES && requiredSlotTownId < 0 && OpexAirSlotTownId(anchor) != town.id) continue;
        if (AIAirport.GetNearestTown(anchor, airport.type) != town.id) continue;

        if (AIR_CHEAP_SITE) {
          /* Eau/riviere/cote sur toute l'emprise, C4, et IsBuildableRectangle : sans AITestMode.
           * La sonde ci-dessous ne tourne plus que sur un hit cheap. */
          if (!OpexAirFootprintCheapOk(anchor, airport)) {
            if ("cheapSkip" in probes) probes.cheapSkip++;
            continue;
          }
        } else {
          /* Filtre de platitude préalable (docs/taches.md §0 tervicies point 5 & C4, façon AAAHogEx) :
           * Si l'écart d'altitude au sein de l'emprise dépasse 1 niveau, le terrassement échoue
           * massivement ou coûte trop cher. Rejet éliminatoire avant d'entrer en AITestMode. */
          local minH = AITile.GetMinHeight(anchor);
          local maxH = AITile.GetMaxHeight(anchor);
          local tooSteep = false;
          for (local tx = 0; tx <= offX; tx++) {
            for (local ty = 0; ty <= offY; ty++) {
              local t = anchor + AIMap.GetTileIndex(tx, ty);
              local tMin = AITile.GetMinHeight(t);
              local tMax = AITile.GetMaxHeight(t);
              if (tMin < minH) minH = tMin;
              if (tMax > maxH) maxH = tMax;
              if (maxH - minH >= 2) { tooSteep = true; break; }
            }
            if (tooSteep) break;
          }
          if (tooSteep) continue;
        }

        if (used >= allowance) {
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          if (useSiteCache) AIR_SITE_CACHE[key] <- null;
          return null;
        }
        if (probes.left <= 0) {
          OpexAirC78NoteNoSite(probes, "no_site_budget");
          return null;
        }

        local ok = false;
        if (AIR_CHEAP_SITE) {
          {
            local probe = AITestMode();
            ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          }
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              if (useSiteCache) AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES &&
                OpexAirFootprintIsFlat(anchor, airport)) {
              ok = true;
            } else if ((err == AIError.ERR_LOCAL_AUTHORITY_REFUSES ||
                        err == AIError.ERR_FLAT_LAND_REQUIRED) &&
                       execLevels < 3) {
              execLevels++;
              /* G7§2 : test-mode seulement ; le terrassement reel est fait par le constructeur. */
              if (OpexAirCanLevelFootprint(anchor, airport, town.id)) {
                ok = true;
              }
            }
          }
        } else {
          local probe = AITestMode();
          ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
          if (!ok) {
            local err = AIError.GetLastError();
            if (OpexAirRememberTownStationLimit(probes, town, err)) {
              if (useSiteCache) AIR_SITE_CACHE[key] <- null;
              return null;
            } else if (err == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
              ok = true;
            } else {
              AITile.LevelTiles(anchor, OpexAirFootprintEnd(anchor, airport));
              ok = AIAirport.BuildAirport(anchor, airport.type, AIStation.STATION_NEW);
              if (!ok) {
                local retryErr = AIError.GetLastError();
                if (OpexAirRememberTownStationLimit(probes, town, retryErr)) {
                  if (useSiteCache) AIR_SITE_CACHE[key] <- null;
                  return null;
                }
                if (retryErr == AIError.ERR_LOCAL_AUTHORITY_REFUSES) ok = true;
              }
            }
          }
        }
        used++;
        probes.left--;
        if ("tested" in probes) probes.tested++;
        if (ok && C83_FIXES && requiredSlotTownId < 0 && OpexAirSlotTownId(anchor) != town.id) {
          ok = false;
        }
        if (ok) {
          if (useSiteCache) AIR_SITE_CACHE[key] <- anchor;
          return { town = town, anchor = anchor };
        }
      }
    }
  }
  if (useSiteCache && (used >= allowance || probes.left > 0)) {
    AIR_SITE_CACHE[key] <- null;
  }
  return null;
}

/* C78.2 : revalidation legere d'un site deja trouve. Le scan complet peut
 * suspendre pendant que la carte evolue ; ce predicat est donc rejoue juste
 * avant le classement, puis par le portefeuille avant sa propre selection. */
function OpexAirSiteStillBuildable(site, airport, plane, reuse, stationLimitedTowns = null)
{
  if (site == null || airport == null || plane == null || !AIMap.IsValidTile(site.anchor)) return false;
  if (reuse) {
    return AIAirport.IsAirportTile(site.anchor)
        && OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(site.anchor), plane.planeType);
  }
  if (!("town" in site) || site.town == null || !("id" in site.town)) return false;
  if (stationLimitedTowns != null && (site.town.id in stationLimitedTowns)) return false;
  if (AIAirport.GetNearestTown(site.anchor, airport.type) != site.town.id) return false;
  if (C83_FIXES) {
    local requiredSlot = site.town.id;
    if (("c83SlotTown" in site) && site.c83SlotTown >= 0) requiredSlot = site.c83SlotTown;
    if (OpexAirSlotTownId(site.anchor) != requiredSlot) return false;
  }
  if (AIR_CHEAP_SITE && !OpexAirFootprintCheapOk(site.anchor, airport)) return false;

  local ok = false;
  local error = 0;
  {
    local probe = AITestMode();
    ok = AIAirport.BuildAirport(site.anchor, airport.type, AIStation.STATION_NEW);
    if (!ok) error = AIError.GetLastError();
  }
  if (ok) return true;

  if (error == AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN) {
    if (stationLimitedTowns != null) stationLimitedTowns.rawset(site.town.id, true);
    return false;
  }
  if (error == AIError.ERR_LOCAL_AUTHORITY_REFUSES
      && OpexAirFootprintIsFlat(site.anchor, airport)) return true;
  if ((error == AIError.ERR_LOCAL_AUTHORITY_REFUSES || error == AIError.ERR_FLAT_LAND_REQUIRED)
      && OpexAirCanLevelFootprint(site.anchor, airport, site.town.id)) return true;
  return false;
}

/* Revenu par passager transporte. Sous V92, la soute connue remplace le forfait de 15 % :
 * elle est remplie dans la meme proportion que la cabine. Sans mesure, le forfait reste. */
function OpexAirFarePerPax(catalog, plane, distance, incomeDays)
{
  local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, distance, incomeDays);
  local totalIncomePerUnit = paxIncome;
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, distance, incomeDays);
    local mailPct = 15;
    if (V92_AIR_SERVICE_CHOICE && plane != null && ("mailCapacity" in plane)
        && plane.mailCapacity >= 0 && plane.capacity > 0) {
      mailPct = (plane.mailCapacity * 100) / plane.capacity;
    }
    totalIncomePerUnit = paxIncome + (mailIncome * mailPct) / 100;
  }
  return (totalIncomePerUnit * AIR_PAX_REVENUE_CALIBRATION_PCT) / 100.0;
}

/* Economie et dimensionnement optimal de flotte selon les caracteristiques du vehicule.
 * serviceScan (V92) leve le plafond a un avion et retient le meilleur nombre d'appareils. */
function OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
                          infrastructureMaintenance, maxCapital, newAirportCount = 2,
                          opcodePadding = 0, fixedPlanes = 0, targetSizing = false,
                          serviceScan = false)
{
  local econKey = null;
  local canMemo = C80_AIR_EVAL_FAST && fixedPlanes == 0 && opcodePadding == 0 && !targetSizing && !serviceScan;
  if (canMemo) {
    /* Memo valable seulement dans le mois ou il a ete rempli (prix indexes chaque mois). */
    local nowDate = AIDate.GetCurrentDate();
    if (AIR_MEMO_MONTH != AIDate.GetYear(nowDate) * 12 + AIDate.GetMonth(nowDate)) canMemo = false;
  }
  if (canMemo) {
    econKey = plane.id + "|" + airport.type + "|" + distance + "|" + monthlyPax + "|" + newAirportCount + "|" + maxCapital + "|" + (infrastructureMaintenance ? 1 : 0);
    if (econKey in AIR_ECONOMICS_MEMO) {
      return AIR_ECONOMICS_MEMO[econKey];
    }
  }

  local oneWayDays = 0;
  local roundTripDays = 0;
  local tripsPerMonth = 0;
  local capacityPerPlane = 0;
  local incomePerUnit = 0.0;

  if (canMemo) {
    local tripKey = (plane.id * 10000) + distance;
    if (tripKey in AIR_TRIP_MEMO) {
      local tripData = AIR_TRIP_MEMO[tripKey];
      oneWayDays = tripData.oneWayDays;
      roundTripDays = tripData.roundTripDays;
      tripsPerMonth = tripData.tripsPerMonth;
      capacityPerPlane = tripData.capacityPerPlane;
      incomePerUnit = tripData.incomePerUnit;
    } else {
      local trip = OpexAirTripModel(plane.speed, plane.capacity, distance);
      oneWayDays = trip.oneWayDays;
      roundTripDays = trip.roundTripDays;
      tripsPerMonth = trip.tripsPerMonth;
      capacityPerPlane = trip.capacityPerPlane;
      if (capacityPerPlane > 0) {
        local incomeDays = OpexCeilDiv(oneWayDays, 1);
        incomePerUnit = OpexAirFarePerPax(catalog, plane, distance, incomeDays);
      }
      AIR_TRIP_MEMO.rawset(tripKey, {
        oneWayDays = oneWayDays,
        roundTripDays = roundTripDays,
        tripsPerMonth = tripsPerMonth,
        capacityPerPlane = capacityPerPlane,
        incomePerUnit = incomePerUnit
      });
    }
  } else {
    local trip = OpexAirTripModel(plane.speed, plane.capacity, distance);
    oneWayDays = trip.oneWayDays;
    roundTripDays = trip.roundTripDays;
    tripsPerMonth = trip.tripsPerMonth;
    capacityPerPlane = trip.capacityPerPlane;
    if (capacityPerPlane <= 0) return null;
    local incomeDays = OpexCeilDiv(oneWayDays, 1);
    /* En soute, sans mesure, ~15 % du tarif postal par passager. V92 utilise la soute reelle. */
    incomePerUnit = OpexAirFarePerPax(catalog, plane, distance, incomeDays);
  }
  if (capacityPerPlane <= 0) {
    if (canMemo) AIR_ECONOMICS_MEMO.rawset(econKey, null);
    return null;
  }
  local airportMaintenanceAnnual =
      infrastructureMaintenance ? 12 * newAirportCount * airport.maintenance : 0;
  local airportAmortAnnual = (newAirportCount * airport.price * INFRA_AMORT_PCT / 100) / 30;
  local best = null;
  /* Plafond d'appareils initial : le portefeuille flotte demarre a un seul avion. */
  local isSmall = (airport.type == AIAirport.AT_SMALL || airport.type == AIAirport.AT_COMMUTER);
  local multiPlaneMax = (newAirportCount == 2) ? 3 : (isSmall ? 4 : 6);
  local maxAllowed = (targetSizing || serviceScan) ? multiPlaneMax
      : ((OPEX_ECONOMY_OPCODE_COMPAT_FALSE || FLEET_PORTFOLIO) ? 1 : multiPlaneMax);
  if (!targetSizing && !serviceScan && !OPEX_ECONOMY_OPCODE_COMPAT_FALSE && !FLEET_PORTFOLIO && OPEX_AIR_PLAN_PAD && opcodePadding > 0) maxAllowed = opcodePadding;
  /* Dimensionnement cible selon le volume passagers */
  local targetPlanes = OpexCeilDiv(monthlyPax, capacityPerPlane.tointeger());
  if (targetPlanes < 1) targetPlanes = 1;
  if (targetPlanes > maxAllowed) targetPlanes = maxAllowed;
  /* Apres chantier, la flotte existe deja : mesurer son economie ne doit pas proposer un
   * nombre theorique d'avions different de celui effectivement livre. */
  if (fixedPlanes > 0) targetPlanes = fixedPlanes;

  /* air_margin : la marge exigee a l'acceptation (30 000 / 12 000 / 2 000 selon le nombre
   * d'aeroports NEUFS -- autorite locale, terrassement, aleas) doit etre connue ici, sinon
   * _tryBuildAir trouve un plan puis le rejette et gache son cycle. L'appliquer globalement du
   * cote appelant a ete mesure a −11,5 % (t = −2,66) le 2026-09-01 : ca rabote aussi le hub-a-hub,
   * dont la marge reelle n'est que 2 000. Ici la marge est appliquee PAR PLAN, au bon grain.
   * L'appelant soustrait deja le plancher de 2 000, on ne compte donc que le supplement.
   * Sous 0 ou maxCapital == 0 (chemin portefeuille), ce bloc ne change rien. Adopte le
   * 2026-09-02 (defaut 1) : mesure NEUTRE, adopte pour la justesse -- voir main.nut. */
  local extraMargin = 0;
  if (AIR_MARGIN && maxCapital > 0) {
    extraMargin = ((newAirportCount == 2) ? 30000 : (newAirportCount == 1 ? 12000 : 2000)) - 2000;
  }

  local firstPlanes = fixedPlanes > 0 ? fixedPlanes : 1;
  for (local planes = firstPlanes; planes <= targetPlanes; planes++) {
    local capital = newAirportCount * airport.price + planes * plane.price;
    if (maxCapital > 0 && capital + extraMargin > maxCapital) break;
    local headwayDays = roundTripDays / planes;
    local stationRating = OpexStationRatingForHeadway(headwayDays);
    local offered = (monthlyPax * stationRating) / 100.0;
    local monthlyCapacity = planes * capacityPerPlane;
    local carried = (offered < monthlyCapacity ? offered : monthlyCapacity).tointeger();
    local revenueAnnual = (12 * carried * incomePerUnit).tointeger();
    local runningAnnual = planes * plane.runningCost + airportMaintenanceAnnual;
    local lifeYears = 20;
    if (V92_AIR_SERVICE_CHOICE && ("ageYears" in plane) && plane.ageYears > 1) lifeYears = plane.ageYears;
    local amortAnnual = planes * plane.price / lifeYears + airportAmortAnnual;
    local profitAnnual = revenueAnnual - runningAnnual - amortAnnual;
    local immobilise = (TRANSIT_COST_PERMILLE > 0)
        ? (revenueAnnual * roundTripDays * TRANSIT_COST_PERMILLE) / 365000 : 0;
    local totalCapital = capital + immobilise;
    local roi = totalCapital > 0 ? (profitAnnual * 1000) / totalCapital : 0;
    if (best == null || profitAnnual > best.profitAnnual ||
        (profitAnnual == best.profitAnnual && roi > best.roi)) {
      best = {
        planes = planes, profitAnnual = profitAnnual, revenueAnnual = revenueAnnual,
        runningAnnual = runningAnnual, amortAnnual = amortAnnual, capital = capital,
        immobilise = immobilise, roi = roi,
        oneWayDays = oneWayDays, roundTripDays = roundTripDays, headwayDays = headwayDays,
        stationRating = stationRating, tripsPerMonth = tripsPerMonth,
        monthlyCapacity = monthlyCapacity, carried = carried,
      };
    }
  }
  if (canMemo) AIR_ECONOMICS_MEMO.rawset(econKey, best);
  return best;
}

/* C84 : economie de croisiere utilisee uniquement pour memoriser une cible de flotte pour
 * l'appareil deja choisi par la politique courante. Elle ignore le capital disponible de la passe
 * courante : la construction initiale
 * reste financee comme aujourd'hui avec un seul avion et les renforts restent marginaux. */
function OpexAirTargetEconomics(catalog, airport, plane, distance, monthlyPax,
                                infrastructureMaintenance, newAirportCount, opcodePadding = 0)
{
  return OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
      infrastructureMaintenance, 0, newAirportCount, opcodePadding, 0, true);
}

/* C84 : score marginal d'un renfort d'une ligne EXISTANTE. Le moteur est celui du premier
 * appareil vivant, exactement comme OpexAirAddPlane ; aucun choix d'equipement n'est refait.
 * fixedPlanes force OpexAirEconomics a evaluer un seul point, et newAirportCount=0 annule les
 * couts d'infrastructure constants : la difference mesure donc uniquement have -> have+want. */
function OpexAirExistingLineMarginalEconomics(catalog, line, have, want)
{
  if (line == null || have < 1 || want < 1 || !("airMonthlyPax" in line)
      || line.airMonthlyPax <= 0 || !("distance" in line) || line.distance <= 0
      || !("vehicles" in line) || line.vehicles.len() == 0) return null;

  local template = null;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) {
      template = v;
      break;
    }
  }
  if (template == null) return null;

  local engine = AIVehicle.GetEngineType(template);
  local capacity = AIEngine.GetCapacity(engine);
  local speed = AIEngine.GetMaxSpeed(engine);
  local price = AIEngine.GetPrice(engine);
  local runningCost = AIEngine.GetRunningCost(engine);
  if (capacity <= 0 || speed <= 0 || price <= 0 || runningCost < 0) return null;

  local airportTile = AIAirport.IsAirportTile(line.stationA) ? line.stationA
      : ((("stationB" in line) && AIAirport.IsAirportTile(line.stationB)) ? line.stationB : null);
  if (airportTile == null) return null;
  local airportType = AIAirport.GetAirportType(airportTile);
  if (!AIAirport.IsValidAirportType(airportType)) return null;

  local airport = {
    type = airportType,
    price = AIAirport.GetPrice(airportType),
    maintenance = AIAirport.GetMonthlyMaintenanceCost(airportType),
  };
  local plane = {
    id = engine,
    capacity = capacity,
    speed = speed,
    price = price,
    runningCost = runningCost,
  };
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local before = OpexAirEconomics(catalog, airport, plane, line.distance, line.airMonthlyPax,
      infrastructureMaintenance, 0, 0, 0, have);
  local after = OpexAirEconomics(catalog, airport, plane, line.distance, line.airMonthlyPax,
      infrastructureMaintenance, 0, 0, 0, have + want);
  if (before == null || after == null) return null;
  return {
    profitAnnual = after.profitAnnual - before.profitAnnual,
    revenueAnnual = after.revenueAnnual - before.revenueAnnual,
  };
}

/* G4 : Reconcile le contrat economique d'une ligne air avec ce qui a ete effectivement pose.
 * Les arrets joints n'ajoutent que leur bassin marginal hors couverture de l'aeroport et la flotte
 * est figee au nombre reellement construit. Le cout comptable final remplace le capital estime,
 * puis amortissement, profit et ROI sont derives ensemble. */
function OpexAirReconcileActualBuild(catalog, plan, result, lines = null)
{
  if (plan == null || result == null || !("economics" in plan)) return;
  local actualPlanes = ("vehicles" in result && result.vehicles != null) ? result.vehicles.len() : 0;
  if (actualPlanes <= 0) return;
  local baseMonthly = ("monthlyPax" in plan) ? plan.monthlyPax : 0;
  local joinedMonthly = OPEX_AIR_PLAN_PAD && ("joinedMonthlyPax" in result)
      ? result.joinedMonthlyPax : 0;
  local monthlyPax = baseMonthly + joinedMonthly;
  if (monthlyPax < 10) monthlyPax = 10;
  if (V93_AIR_DEMAND_PRODUCTION) {
    /* Meme unite qu'avant : passagers mensuels de la paire, somme des deux bouts,
     * plus le bassin marginal des arrets joints. Le plancher de 10 ne s'applique pas. */
    if (catalog != null) AIR_DEMAND_PAX_CARGO = catalog.paxCargo;
    local airport = ("airport" in plan) ? plan.airport : null;
    local demandA = 0;
    local demandB = 0;
    if (("siteA" in plan) && plan.siteA != null && ("town" in plan.siteA)) {
      local anchorA = ("anchor" in plan.siteA) ? plan.siteA.anchor : null;
      demandA = OpexAirTownMonthlyPax(plan.siteA.town, anchorA, airport, lines);
    }
    if (("siteB" in plan) && plan.siteB != null && ("town" in plan.siteB)) {
      local anchorB = ("anchor" in plan.siteB) ? plan.siteB.anchor : null;
      demandB = OpexAirTownMonthlyPax(plan.siteB.town, anchorB, airport, lines);
    }
    monthlyPax = demandA + demandB + joinedMonthly;
  }
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local economics = OpexAirEconomics(catalog, plan.airport, plan.plane, plan.distance, monthlyPax,
                                      AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0,
                                      0, newAirports, 0, actualPlanes);
  if (economics == null) return;

  if (("actualCost" in result) && result.actualCost > 0) {
    local vehicleFloor = actualPlanes * plan.plane.price;
    local actualCapital = result.actualCost;
    if (actualCapital < vehicleFloor) actualCapital = vehicleFloor;
    local capitalDelta = actualCapital - economics.capital;
    economics.capital = actualCapital;
    economics.amortAnnual += ((capitalDelta * INFRA_AMORT_PCT / 100) / 30);
    economics.profitAnnual = economics.revenueAnnual - economics.runningAnnual - economics.amortAnnual;
    local totalCapital = economics.capital + economics.immobilise;
    economics.roi = totalCapital > 0 ? (economics.profitAnnual * 1000) / totalCapital : 0;
  }
  plan.monthlyPax = monthlyPax;
  plan.planes = actualPlanes;
  plan.capital = economics.capital;
  plan.economics = economics;
}

/* G4/B9 : contrat pre-chantier des arrets joints.
 * Les arrets sont optionnels et leur cout exact depend du site et d'eventuelles depenses
 * d'autorite locale. Le 5x6 B9 a invalide BT_BUS_STOP comme estimateur du cout traversant.
 * On ne melange donc plus un faux cout connu avec une demande inconnue : les deux restent
 * nuls a l'election et sont remplaces par leurs valeurs mesurees apres chantier. */
function OpexAirReserveJoinedStops(catalog, plan)
{
  if (!AIR_JOINED_STOPS || plan == null || !("economics" in plan)) return;
  /* B9/08.6 : extension optionnelle apres le coeur aeroport+avion. Le 5x6
   * mesure 450..2250 GBP par arret selon le site/autorite : BT_BUS_STOP n'est
   * pas une reserve exacte. Avant chantier, cout ET demande joints restent a
   * zero ; apres chantier, actualCost et catchment union reel sont reconcilies. */
  plan.joinedStopReserve <- 0;
}

function OpexAirCatalogPlane(catalog, airportType, engineId)
{
  if (catalog != null && catalog.airPlaneChoicesByAirport != null
      && (airportType in catalog.airPlaneChoicesByAirport)) {
    foreach (plane in catalog.airPlaneChoicesByAirport[airportType]) {
      if (plane.id == engineId) return plane;
    }
  }
  if (!AIEngine.IsValidEngine(engineId)) return null;
  return {
    id = engineId,
    capacity = AIEngine.GetCapacity(engineId),
    speed = AIEngine.GetMaxSpeed(engineId),
    price = AIEngine.GetPrice(engineId),
    runningCost = AIEngine.GetRunningCost(engineId),
    maxOrderDistance = AIEngine.GetMaximumOrderDistance(engineId),
    ageYears = AIEngine.GetMaxAge(engineId) / 365,
    mailCapacity = -1,
    isBig = false,
  };
}

function OpexAirLineSellValue(line)
{
  local total = 0;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v)) total += AIVehicle.GetCurrentValue(v);
  }
  return total;
}

function OpexAirLineReequipPending(line)
{
  return line != null && ("v92PendingEngine" in line) && line.v92PendingEngine >= 0;
}

function OpexAirClearReequip(line)
{
  if (line == null) return;
  if ("v92PendingEngine" in line) delete line.v92PendingEngine;
  if ("v92PendingCount" in line) delete line.v92PendingCount;
  if ("v92SentToHangar" in line) line.v92SentToHangar = [];
}

function OpexAirAlreadySentToHangar(line, vehicle)
{
  if (!("v92SentToHangar" in line) || line.v92SentToHangar == null) return false;
  foreach (id in line.v92SentToHangar) {
    if (id == vehicle) return true;
  }
  return false;
}

/* SendVehicleToDepot est une bascule, et l'ordre manuel n'est pas dans la liste
 * d'ordres. On memorise les vehicules deja envoyes et on ne les renvoie jamais.
 * Le hangar d'arrivee est le plus proche, pas forcement celui de l'aeroport A. */
function OpexAirSendLineToHangar(line, hangar)
{
  local waiting = false;
  foreach (v in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(v) || AIVehicle.IsStoppedInDepot(v)) continue;
    waiting = true;
    if (OpexAirAlreadySentToHangar(line, v)) continue;
    if (!AIVehicle.SendVehicleToDepot(v)) continue;
    if (!("v92SentToHangar" in line) || line.v92SentToHangar == null) line.v92SentToHangar <- [];
    line.v92SentToHangar.append(v);
  }
  return waiting;
}

function OpexAirReleaseHangarHold(line)
{
  if (line == null || !("vehicles" in line) || line.vehicles == null) {
    OpexAirClearReequip(line);
    return;
  }
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsStoppedInDepot(v)) AIVehicle.StartStopVehicle(v);
  }
  OpexAirClearReequip(line);
}

/* Repose `count` appareils d'un moteur deja vendu. Retourne le nombre réellement relancé. */
function OpexAirRebuildFleet(line, hangar, engineId, count, cargo)
{
  if (engineId < 0 || count < 1) return 0;
  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local restored = [];
  for (local i = 0; i < count; i++) {
    local aircraft = AIVehicle.BuildVehicleWithRefit(hangar, engineId, cargo);
    if (!AIVehicle.IsValidVehicle(aircraft)) break;
    local ordersOk = true;
    if (restored.len() == 0) {
      ordersOk = AIOrder.AppendOrder(aircraft, line.stationA, airFlagsA)
          && AIOrder.AppendOrder(aircraft, line.stationB, airFlagsB)
          && AIOrder.GetOrderCount(aircraft) == 2;
    } else {
      ordersOk = AIOrder.ShareOrders(aircraft, restored[0]);
    }
    if (!ordersOk || !AIVehicle.StartStopVehicle(aircraft)) {
      if (AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
      break;
    }
    restored.append(aircraft);
  }
  if (restored.len() == 0) return 0;
  line.vehicles = restored;
  line.vehicle = restored[0];
  line.refleetEngine = engineId;
  line.vehCount <- restored.len();
  line.trains = restored.len();
  return restored.len();
}

function OpexAirLineAllInHangar(line)
{
  local any = false;
  foreach (v in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    any = true;
    if (!AIVehicle.IsStoppedInDepot(v)) return false;
  }
  return any;
}

/* Vend la flotte et pose `count` appareils du nouveau moteur. En echec, rachete l'ancien. */
function OpexAirReplaceFleet(line, hangar, catalog, plane, count)
{
  if (plane == null || count < 1 || !OpexAirLineAllInHangar(line)) return null;
  local cargo = ("cargo" in line) ? line.cargo : catalog.paxCargo;
  local oldEngine = ("refleetEngine" in line) ? line.refleetEngine : -1;
  if (!AIEngine.IsBuildable(plane.id) || (oldEngine >= 0 && !AIEngine.IsBuildable(oldEngine))) {
    return { added = 0, reason = "ABORT" };
  }
  local sell = OpexAirLineSellValue(line);
  local cost = count * plane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money + sell < cost + OpexCashReserve()) return { added = 0, reason = "ABORT" };
  local old = [];
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v)) old.append(v);
  }
  local oldCount = old.len();
  local kept = [];
  foreach (v in old) {
    if (!AIVehicle.SellVehicle(v)) kept.append(v);
  }
  if (kept.len() > 0) {
    line.vehicles = kept;
    line.vehicle = kept[0];
    line.vehCount <- kept.len();
    line.trains = kept.len();
    return null;
  }
  local built = [];
  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local failed = false;
  for (local i = 0; i < count; i++) {
    local aircraft = AIVehicle.BuildVehicleWithRefit(hangar, plane.id, cargo);
    if (!AIVehicle.IsValidVehicle(aircraft)) { failed = true; break; }
    local ordersOk = true;
    if (built.len() == 0) {
      ordersOk = AIOrder.AppendOrder(aircraft, line.stationA, airFlagsA)
          && AIOrder.AppendOrder(aircraft, line.stationB, airFlagsB)
          && AIOrder.GetOrderCount(aircraft) == 2;
    } else {
      ordersOk = AIOrder.ShareOrders(aircraft, built[0]);
    }
    if (!ordersOk) {
      if (AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
      failed = true;
      break;
    }
    built.append(aircraft);
  }
  if (failed || built.len() != count) {
    foreach (aircraft in built) {
      if (AIVehicle.IsValidVehicle(aircraft) && AIVehicle.IsStoppedInDepot(aircraft)) AIVehicle.SellVehicle(aircraft);
    }
    if (OpexAirRebuildFleet(line, hangar, oldEngine, oldCount, cargo) <= 0) {
      line.vehicles = [];
      line.vehicle = -1;
      line.vehCount <- 0;
      line.trains = 0;
    }
    return null;
  }
  local started = true;
  foreach (aircraft in built) {
    if (!AIVehicle.StartStopVehicle(aircraft)) {
      foreach (sold in built) {
        if (AIVehicle.IsValidVehicle(sold) && AIVehicle.IsStoppedInDepot(sold)) AIVehicle.SellVehicle(sold);
      }
      started = false;
      break;
    }
  }
  if (!started) {
    if (OpexAirRebuildFleet(line, hangar, oldEngine, oldCount, cargo) <= 0) {
      line.vehicles = [];
      line.vehicle = -1;
      line.vehCount <- 0;
      line.trains = 0;
    }
    return null;
  }
  line.vehicles = built;
  line.vehicle = built[0];
  line.refleetEngine = plane.id;
  line.planeId = plane.id;
  line.planeCapacity = plane.capacity;
  line.vehCount <- built.len();
  line.trains = built.len();
  line.v92LastReplaceYear <- AIDate.GetYear(AIDate.GetCurrentDate());
  OpexAirClearReequip(line);
  if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local mail = AIVehicle.GetCapacity(built[0], catalog.mailCargo);
    if (mail >= 0) AIR_MAIL_CAP.rawset(plane.id, mail);
  }
  return { added = 0, reason = "REPLACE", vehCount = built.len() };
}

/* Un autre moteur au meilleur nombre bat un appareil de plus du moteur actuel. */
function OpexAirConsiderReplace(line, catalog, airportTile)
{
  if (("scrapping" in line) && line.scrapping) return null;
  if (!("distance" in line) || line.distance <= 0) return null;
  if (!("airMonthlyPax" in line) || line.airMonthlyPax <= 0) return null;
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  if (("v92LastReplaceYear" in line) && year - line.v92LastReplaceYear < 2) return null;
  local airportType = AIAirport.GetAirportType(airportTile);
  if (!AIAirport.IsValidAirportType(airportType)) return null;
  local currentId = ("refleetEngine" in line) ? line.refleetEngine : -1;
  if (currentId < 0) return null;
  local have = 0;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) have++;
  }
  if (have < 1) return null;
  OpexAirLearnMailCaps(catalog);
  local airport = {
    type = airportType,
    price = AIAirport.GetPrice(airportType),
    maintenance = AIAirport.GetMonthlyMaintenanceCost(airportType),
  };
  local infrastructure = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local current = OpexAirCatalogPlane(catalog, airportType, currentId);
  if (current == null) return null;
  OpexAirApplyKnownMail(current);
  local keep = OpexAirEconomics(catalog, airport, current, line.distance, line.airMonthlyPax,
      infrastructure, 0, 0, 0, have + 1, false, false);
  if (catalog.airPlaneChoicesByAirport == null
      || !(airportType in catalog.airPlaneChoicesByAirport)) return null;
  local bestPlane = null;
  local bestEcon = null;
  foreach (plane in catalog.airPlaneChoicesByAirport[airportType]) {
    if (plane.id == currentId || !OpexAirPlaneInRange(plane, line.distance)) continue;
    OpexAirApplyKnownMail(plane);
    local econ = OpexAirEconomics(catalog, airport, plane, line.distance, line.airMonthlyPax,
        infrastructure, 0, 0, 0, 0, false, true);
    if (OpexAirServiceBetter(econ, bestEcon)) {
      bestPlane = plane;
      bestEcon = econ;
    }
  }
  if (bestPlane == null) return null;
  local cap = OpexAirCadenceCap(line, catalog, null);
  if (cap < 1) cap = 1;
  if (bestEcon.planes > cap) {
    bestEcon = OpexAirEconomics(catalog, airport, bestPlane, line.distance, line.airMonthlyPax,
        infrastructure, 0, 0, 0, cap, false, false);
  }
  if (!OpexAirServiceBetter(bestEcon, keep)) return null;
  local sell = OpexAirLineSellValue(line);
  local cost = bestEcon.planes * bestPlane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money + sell < cost + OpexCashReserve()) return null;
  return { plane = bestPlane, count = bestEcon.planes };
}

function OpexAirMaybeReequip(line, catalog, hangar, airportTile)
{
  if (("v92PendingEngine" in line) && line.v92PendingEngine >= 0) {
    if (!OpexAirLineAllInHangar(line)) {
      OpexAirSendLineToHangar(line, hangar);
      return { added = 0, reason = "REEEQUIP_WAIT" };
    }
    local airportType = AIAirport.GetAirportType(airportTile);
    local plane = OpexAirCatalogPlane(catalog, airportType, line.v92PendingEngine);
    local count = ("v92PendingCount" in line) ? line.v92PendingCount : 1;
    local swapped = OpexAirReplaceFleet(line, hangar, catalog, plane, count);
    if (swapped != null && swapped.reason == "ABORT") {
      OpexAirReleaseHangarHold(line);
      return { added = 0, reason = "REEEQUIP_ABORT" };
    }
    if (swapped != null) return swapped;
    OpexAirClearReequip(line);
    return { added = 0, reason = "REEEQUIP_FAIL" };
  }
  local decision = OpexAirConsiderReplace(line, catalog, airportTile);
  if (decision == null) return null;
  line.v92PendingEngine <- decision.plane.id;
  line.v92PendingCount <- decision.count;
  OpexAirSendLineToHangar(line, hangar);
  if (OpexAirLineAllInHangar(line)) {
    local swapped = OpexAirReplaceFleet(line, hangar, catalog, decision.plane, decision.count);
    if (swapped != null && swapped.reason == "ABORT") {
      OpexAirReleaseHangarHold(line);
      return { added = 0, reason = "REEEQUIP_ABORT" };
    }
    if (swapped != null) return swapped;
    OpexAirClearReequip(line);
    return { added = 0, reason = "REEEQUIP_FAIL" };
  }
  return { added = 0, reason = "REEEQUIP_WAIT" };
}

/* Ajoute un seul avion a une liaison deja mesuree. Le clonage partage les ordres et ne refait ni
 * recherche de sites ni construction d'infrastructure : c'est le chemin marginal au meilleur
 * profit/opcode. Toute decision de l'appeler reste dans main.nut, apres une annee de donnees.
 * Sous V92, un autre service peut remplacer la flotte avant ce clonage. */
function OpexAirAddPlane(line, catalog = null)
{
  local result = { added = 0, reason = "" };
  if (!("vehicles" in line) || line.vehicles.len() == 0) {
    result.reason = "NOVEH"; return result;
  }
  local airportTile = ("originA" in line) && AIAirport.IsAirportTile(line.originA)
      ? line.originA
      : (AIAirport.IsAirportTile(line.stationA) ? line.stationA : null);
  if (airportTile == null) {
    result.reason = "NOAIR"; return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(airportTile);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    result.reason = "HANG"; return result;
  }
  local template = null;
  foreach (v in line.vehicles) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) {
      template = v; break;
    }
  }
  if (template == null) { result.reason = "NOLIVE"; return result; }
  if (V92_AIR_SERVICE_CHOICE && catalog != null) {
    local swapped = OpexAirMaybeReequip(line, catalog, hangar, airportTile);
    if (swapped != null) return swapped;
  }
  local price = AIEngine.GetPrice(AIVehicle.GetEngineType(template));
  if (price <= 0) { result.reason = "PRICE"; return result; }
  local need = price + OpexCashReserve() + 1000;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    if (money < need) {
      result.reason = "CASH"; return result;
    }
  }
  local extra = AIVehicle.CloneVehicle(hangar, template, true);
  if (!AIVehicle.IsValidVehicle(extra)) {
    local engine = AIVehicle.GetEngineType(template);
    local cargo = ("cargo" in line) ? line.cargo : 0;
    extra = AIVehicle.BuildVehicleWithRefit(hangar, engine, cargo);
    if (AIVehicle.IsValidVehicle(extra)) {
      if (!AIOrder.ShareOrders(extra, template)) {
        if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
        result.reason = "ORDER"; return result;
      }
    }
  }
  if (!AIVehicle.IsValidVehicle(extra)) {
    result.reason = "CLONE|" + AIError.GetLastError();
    return result;
  }
  if (!AIVehicle.StartStopVehicle(extra)) {
    if (AIVehicle.IsStoppedInDepot(extra)) AIVehicle.SellVehicle(extra);
    result.reason = "START"; return result;
  }
  line.vehicles.append(extra);
  result.added = 1;
  result.reason = "OK";
  return result;
}

/* Reconstitue un avion perdu sans dependre d'un appareil encore vivant. Le moteur
 * est memorise dans la ligne a sa construction; les deux aeroports sont des
 * destinations durables, donc les ordres peuvent etre recrees sans clonage. */
function OpexAirRefleetCrashedPlane(line)
{
  local result = { added = 0, reason = "" };
  if (!(("refleetEngine" in line) && line.refleetEngine >= 0)) {
    result.reason = "NOENGINE"; return result;
  }
  if (!AIAirport.IsAirportTile(line.stationA) || !AIAirport.IsAirportTile(line.stationB)) {
    result.reason = "NOAIRPORT"; return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(line.stationA);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    result.reason = "HANGAR"; return result;
  }
  if (AIVehicle.GetBuildWithRefitCapacity(hangar, line.refleetEngine, line.cargo) <= 0) {
    result.reason = "REFIT"; return result;
  }
  local price = AIEngine.GetPrice(line.refleetEngine);
  if (price <= 0 || AICompany.GetBankBalance(AICompany.COMPANY_SELF) < price + OpexCashReserve()) {
    result.reason = "CASH"; return result;
  }
  local plane = AIVehicle.BuildVehicleWithRefit(hangar, line.refleetEngine, line.cargo);
  if (!AIVehicle.IsValidVehicle(plane)) { result.reason = "BUILD"; return result; }
  local flagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local flagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  if (!AIOrder.AppendOrder(plane, line.stationA, flagsA) ||
      !AIOrder.AppendOrder(plane, line.stationB, flagsB) || AIOrder.GetOrderCount(plane) != 2) {
    AIVehicle.SellVehicle(plane); result.reason = "ORDER"; return result;
  }
  if (!AIVehicle.StartStopVehicle(plane)) {
    if (AIVehicle.IsStoppedInDepot(plane)) AIVehicle.SellVehicle(plane);
    result.reason = "START"; return result;
  }
  if (!("vehicles" in line)) line.vehicles <- [];
  else if (line.vehicles == null) line.vehicles = [];
  line.vehicles.append(plane);
  if ("vehicle" in line) line.vehicle = plane;
  else line.vehicle <- plane;
  result.added = 1; result.reason = "OK";
  return result;
}

/* Evalue et planifie la meilleure liaison aerienne en testant les combinaisons
 * grand aeroport (+gros/petit avion) et petit aeroport (+petit avion strictement). */
function OpexAirPlanBetter(plan, bestPlan)
{
  if (bestPlan == null) return true;
  /* Arbitrage ROI vs Volume : si un plan offre un ROI significativement superieur (>25% d'ecart),
   * il deploie le capital plus vite et permet de batir plus de lignes. */
  if (plan.economics.roi > (bestPlan.economics.roi * 1.25).tointeger()) return true;
  if (bestPlan.economics.roi > (plan.economics.roi * 1.25).tointeger()) return false;
  return plan.economics.profitAnnual > bestPlan.economics.profitAnnual;
}

/* V92 : pose le service retenu et, s'il differe, la variante a un appareil bon marche.
 * Les deux portent la meme cle de paire pour qu'un seul soit construit. */
function OpexAirV92PairBlocked(lines, plan)
{
  if (!V92_AIR_SERVICE_CHOICE || plan == null || !("v92PairKey" in plan)) return false;
  if (plan.v92PairKey in V92_CLOSED_PAIRS) return true;
  if (lines == null || !("siteA" in plan) || !("siteB" in plan)) return false;
  local tileA = plan.siteA.town.tile;
  local tileB = plan.siteB.town.tile;
  foreach (line in lines) {
    if (!("mode" in line) || line.mode != "air") continue;
    local originA = ("originA" in line) ? line.originA : -1;
    local originB = ("originB" in line) ? line.originB : -1;
    if ((originA == tileA && originB == tileB) || (originA == tileB && originB == tileA)) return true;
  }
  return false;
}

function OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan)
{
  if (V92_AIR_SERVICE_CHOICE && routeChoice != null && ("alternate" in routeChoice)
      && routeChoice.alternate != null && routeChoice.alternate.economics != null
      && routeChoice.alternate.economics.profitAnnual > 0) {
    local alt = routeChoice.alternate;
    local townA = plan.siteA.town.id;
    local townB = plan.siteB.town.id;
    if (townA > townB) {
      local swap = townA;
      townA = townB;
      townB = swap;
    }
    local key = townA + "|" + townB + "|" + plan.airport.type;
    plan.v92PairKey <- key;
    plan.v92Role <- "service";
    local cheap = {};
    foreach (k, v in plan) cheap[k] <- v;
    cheap.plane = alt.plane;
    cheap.economics = alt.economics;
    cheap.planes = alt.economics.planes;
    cheap.capital = alt.economics.capital;
    cheap.v92Role = "cheap";
    if ("targetPlanes" in cheap) cheap.targetPlanes = alt.economics.planes;
    if (projects != null) projects.append(cheap);
    if (OpexAirPlanBetter(cheap, bestPlan)) bestPlan = cheap;
  }
  if (projects != null) projects.append(plan);
  if (OpexAirPlanBetter(plan, bestPlan)) bestPlan = plan;
  return bestPlan;
}

/* C82 : arbitrage d'appareil par route evalue sur les profits et ROI calibres par moteur.
 * L'objet economics renvoye reste brut (non modifie). */
function OpexC82ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding)
{
  local bestPlane = selectedPlane;
  local bestEconomics = selectedEconomics;
  local bestK = (selectedPlane != null) ? OpexC82EngineFactor(selectedPlane.id) : 1.0;
  local bestCalProfit = (selectedEconomics != null) ? (selectedEconomics.profitAnnual * bestK) : 0.0;
  local bestCalRoi = (selectedEconomics != null) ? (selectedEconomics.roi * bestK) : 0.0;
  local bestScore = 0.0;

  local kDec = 0;
  if (C69_BOTTLENECK_PROBE || C72_PLANE_CHOICE == 2) {
    kDec = OpexC69CachedKDec();
  }

  if (C72_PLANE_CHOICE == 2 && selectedEconomics != null) {
    local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
    bestScore = denom > 0 ? (bestCalProfit.tofloat() * 1000.0) / denom : 0.0;
  }

  local rawPlane = null;
  local rawEconomics = null;
  local rawScore = 0.0;
  local evalCount = 0;

  if (C69_BOTTLENECK_PROBE) {
    if (selectedEconomics != null) {
      evalCount = 1;
      rawPlane = selectedPlane;
      rawEconomics = selectedEconomics;
      local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
      rawScore = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
    }
  }

  foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
    if (plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null) continue;

    local k = OpexC82EngineFactor(plane.id);
    local calProfit = economics.profitAnnual * k;
    local calRoi = economics.roi * k;

    if (C72_PLANE_CHOICE == 1) {
      if (bestEconomics == null || calRoi > bestCalRoi ||
          (calRoi == bestCalRoi && calProfit > bestCalProfit)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    } else if (C72_PLANE_CHOICE == 2) {
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (calProfit.tofloat() * 1000.0) / curDenom : 0.0;
      if (bestEconomics == null || curScore > bestScore ||
          (curScore == bestScore && calProfit > bestCalProfit)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestScore = curScore;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    } else {
      if (bestEconomics == null || calProfit > bestCalProfit ||
          (calProfit == bestCalProfit && calRoi > bestCalRoi)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestCalProfit = calProfit;
        bestCalRoi = calRoi;
      }
    }

    if (C69_BOTTLENECK_PROBE) {
      evalCount++;
      if (C72_PLANE_CHOICE == 1) {
        if (rawEconomics == null || economics.roi > rawEconomics.roi ||
            (economics.roi == rawEconomics.roi && economics.profitAnnual > rawEconomics.profitAnnual)) {
          rawPlane = plane;
          rawEconomics = economics;
        }
      } else if (C72_PLANE_CHOICE == 2) {
        local curDenom = economics.capital > kDec ? economics.capital : kDec;
        local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
        if (rawEconomics == null || curScore > rawScore ||
            (curScore == rawScore && economics.profitAnnual > rawEconomics.profitAnnual)) {
          rawPlane = plane;
          rawEconomics = economics;
          rawScore = curScore;
        }
      } else {
        if (rawEconomics == null || economics.profitAnnual > rawEconomics.profitAnnual ||
            (economics.profitAnnual == rawEconomics.profitAnnual && economics.roi > rawEconomics.roi)) {
          rawPlane = plane;
          rawEconomics = economics;
        }
      }
    }
  }

  if (C69_BOTTLENECK_PROBE && evalCount >= 2) {
    C82_CHOICE_CALLS++;
    local idBrut = (rawPlane != null) ? rawPlane.id : -1;
    local idCalibre = (bestPlane != null) ? bestPlane.id : -1;
    if (idCalibre != idBrut) {
      C82_CHOICE_DIFFER++;
      local kBrut = (idBrut >= 0) ? OpexC82EngineFactor(idBrut) : 1.0;
      local kCalibre = (idCalibre >= 0) ? OpexC82EngineFactor(idCalibre) : 1.0;
      OpexC69Log("phase=c82_choice raw=" + idBrut + " cal=" + idCalibre
          + " k_raw=" + kBrut + " k_cal=" + kCalibre + " c72=" + C72_PLANE_CHOICE);
    }
  }

  return { plane = bestPlane, economics = bestEconomics };
}

/* C68 : transforme le contre-factuel passif M3 en intervention minimale. Le caller a deja choisi
 * le type d'aeroport, les sites, la paire et la demande avec le chemin historique. Sous le switch,
 * on ne change donc que l'appareil et l'economie de cette route, avec exactement le meme modele
 * OpexAirEconomics que M3. Sous 0, le resultat est strictement le couple historique. */
/* C80 tranche 5 : `memoKey` identifie la route (villes ou gares, type d'aeroport, avion du combo).
 * Etat 1 (generation complete) : choix complet, memorise. Etat 2 (mise a jour apres chantier) :
 * seule l'economie de l'avion memorise est recalculee ; sans memo valide, choix complet memorise.
 * Un appel plafonne en capital (construction, `maxCapital` > 0) ne lit ni n'ecrit le memo. */
function OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
                                  newAirportCount, opcodePadding, choice)
{
  if (choice == null || choice.plane == null || choice.economics == null) return choice;
  local targetEconomics = OpexAirTargetEconomics(catalog, airport, choice.plane, distance, monthlyPax,
      infrastructureMaintenance, newAirportCount, opcodePadding);
  if (targetEconomics != null) {
    choice.targetEconomics <- targetEconomics;
    choice.targetPlanes <- targetEconomics.planes;
  }
  return choice;
}

/* Lit la soute des avions deja en vol de cette compagnie, une fois par mois.
 * AIVehicleList ne voit pas les avions des autres compagnies. */
function OpexAirLearnMailCaps(catalog)
{
  if (catalog == null || !("mailCargo" in catalog) || catalog.mailCargo < 0
      || !("paxCargo" in catalog) || catalog.paxCargo < 0) return;
  local now = AIDate.GetCurrentDate();
  local month = AIDate.GetYear(now) * 12 + AIDate.GetMonth(now);
  if (AIR_MAIL_LEARN_MONTH == month) return;
  AIR_MAIL_LEARN_MONTH = month;
  local list = AIVehicleList();
  list.Valuate(AIVehicle.GetVehicleType);
  list.KeepValue(AIVehicle.VT_AIR);
  for (local v = list.Begin(); !list.IsEnd(); v = list.Next()) {
    local engine = AIVehicle.GetEngineType(v);
    if (engine < 0 || (engine in AIR_MAIL_CAP)) continue;
    local pax = AIVehicle.GetCapacity(v, catalog.paxCargo);
    local mail = AIVehicle.GetCapacity(v, catalog.mailCargo);
    if (pax > 0 && mail >= 0) AIR_MAIL_CAP.rawset(engine, mail);
  }
}

function OpexAirApplyKnownMail(plane)
{
  if (plane == null || !("id" in plane)) return;
  if (plane.id in AIR_MAIL_CAP) plane.mailCapacity = AIR_MAIL_CAP[plane.id];
}

function OpexAirPlaneInRange(plane, distance)
{
  return plane != null && !(plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance);
}

function OpexAirServiceBetter(candidate, incumbent)
{
  if (candidate == null || candidate.profitAnnual <= 0) return false;
  if (incumbent == null) return true;
  if (candidate.profitAnnual > incumbent.profitAnnual) return true;
  if (candidate.profitAnnual == incumbent.profitAnnual && candidate.roi > incumbent.roi) return true;
  return false;
}

/* V92 : pour chaque moteur compatible, le nombre d'appareils au meilleur profit,
 * puis la meilleure variante a un seul appareil dont le prix ne depasse pas
 * le gros jet le moins cher (ou le moins cher tout court sur un petit aeroport). */
function OpexAirChooseRouteService(catalog, airport, selectedPlane, distance, monthlyPax,
                                   infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding)
{
  OpexAirLearnMailCaps(catalog);
  local bestPlane = null;
  local bestEcon = null;
  local cheapPlane = null;
  local cheapEcon = null;
  if (airport == null || catalog == null || catalog.airPlaneChoicesByAirport == null
      || !(airport.type in catalog.airPlaneChoicesByAirport)) {
    local econ = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1, false, false);
    return { plane = selectedPlane, economics = econ };
  }
  local choices = catalog.airPlaneChoicesByAirport[airport.type];
  local cheapLimit = -1;
  local anyPrice = -1;
  foreach (plane in choices) {
    if (!OpexAirPlaneInRange(plane, distance)) continue;
    OpexAirApplyKnownMail(plane);
    if (anyPrice < 0 || plane.price < anyPrice) anyPrice = plane.price;
    if (("isBig" in plane) && plane.isBig && (cheapLimit < 0 || plane.price < cheapLimit)) {
      cheapLimit = plane.price;
    }
  }
  if (cheapLimit < 0) cheapLimit = anyPrice;
  if (selectedPlane != null) OpexAirApplyKnownMail(selectedPlane);

  foreach (plane in choices) {
    if (!OpexAirPlaneInRange(plane, distance)) continue;
    local scanned = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 0, false, true);
    if (OpexAirServiceBetter(scanned, bestEcon)) {
      bestPlane = plane;
      bestEcon = scanned;
    }
    if (cheapLimit >= 0 && plane.price <= cheapLimit) {
      local one = (scanned != null && scanned.planes == 1) ? scanned
          : OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
              infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1, false, false);
      if (OpexAirServiceBetter(one, cheapEcon)) {
        cheapPlane = plane;
        cheapEcon = one;
      }
    }
  }
  if (bestPlane == null && selectedPlane != null) {
    bestEcon = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding, 1, false, false);
    bestPlane = selectedPlane;
  }
  local choice = { plane = bestPlane, economics = bestEcon };
  if (cheapPlane != null && bestPlane != null && cheapEcon != null
      && (cheapPlane.id != bestPlane.id || cheapEcon.planes != bestEcon.planes)) {
    choice.alternate <- { plane = cheapPlane, economics = cheapEcon };
  }
  return choice;
}

function OpexAirChooseRoutePlane(catalog, airport, selectedPlane, distance, monthlyPax,
                                 infrastructureMaintenance, maxCapital, newAirportCount,
                                 opcodePadding, memoKey = null)
{
  if (V92_AIR_SERVICE_CHOICE) {
    return OpexAirChooseRouteService(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  }
  if (!C80_AIR_CHOICE_MEMO || memoKey == null || maxCapital != 0 || AIR_CHOICE_MEMO_STATE == 0) {
    local choice = OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (C84_AIR_TARGET_FLEET) {
      return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
          newAirportCount, opcodePadding, choice);
    }
    return choice;
  }
  if (AIR_CHOICE_MEMO_STATE == 2 && (memoKey in AIR_CHOICE_MEMO)) {
    local planeId = AIR_CHOICE_MEMO[memoKey];
    local memoPlane = null;
    if (planeId == selectedPlane.id) {
      memoPlane = selectedPlane;
    } else if (airport.type in catalog.airPlaneChoicesByAirport) {
      foreach (plane in catalog.airPlaneChoicesByAirport[airport.type]) {
        if (plane.id == planeId) { memoPlane = plane; break; }
      }
    }
    if (memoPlane != null && (memoPlane.maxOrderDistance <= 0 || distance <= memoPlane.maxOrderDistance)) {
      local economics = OpexAirEconomics(catalog, airport, memoPlane, distance, monthlyPax,
          infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
      if (economics != null) {
        local choice = { plane = memoPlane, economics = economics };
        if (C84_AIR_TARGET_FLEET) {
          return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
              newAirportCount, opcodePadding, choice);
        }
        return choice;
      }
    }
  }
  local choice = OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  if (choice.plane != null) AIR_CHOICE_MEMO.rawset(memoKey, choice.plane.id);
  if (C84_AIR_TARGET_FLEET) {
    return OpexAirAttachTargetFleet(catalog, airport, distance, monthlyPax, infrastructureMaintenance,
        newAirportCount, opcodePadding, choice);
  }
  return choice;
}

function OpexAirChooseRoutePlaneFull(catalog, airport, selectedPlane, distance, monthlyPax,
                                     infrastructureMaintenance, maxCapital, newAirportCount,
                                     opcodePadding)
{
  local selectedEconomics = OpexAirEconomics(catalog, airport, selectedPlane, distance, monthlyPax,
      infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
  if (!AIR_ROUTE_PLANE_SELECTION || !(airport.type in catalog.airPlaneChoicesByAirport)) {
    return { plane = selectedPlane, economics = selectedEconomics };
  }
  if (C82_ENGINE_CALIBRATION) return OpexC82ChooseRoutePlane(catalog, airport, selectedPlane, selectedEconomics, distance, monthlyPax, infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);

  local bestPlane = selectedPlane;
  local bestEconomics = selectedEconomics;
  local bestScore = 0.0;

  local kDec = 0;
  if (C69_BOTTLENECK_PROBE || C72_PLANE_CHOICE == 2) {
    kDec = OpexC69CachedKDec();
  }

  if (C72_PLANE_CHOICE == 2 && selectedEconomics != null) {
    local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
    bestScore = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
  }

  local r_plane = null;
  local r_econ = null;
  local c_plane = null;
  local c_econ = null;
  local c_score = 0.0;
  local evalCount = 0;

  if (C69_BOTTLENECK_PROBE) {
    if (selectedEconomics != null) {
      evalCount = 1;
      r_plane = selectedPlane;
      r_econ = selectedEconomics;
      c_plane = selectedPlane;
      c_econ = selectedEconomics;
      local denom = selectedEconomics.capital > kDec ? selectedEconomics.capital : kDec;
      c_score = denom > 0 ? (selectedEconomics.profitAnnual.tofloat() * 1000.0) / denom : 0.0;
    }
  }

  local routePlaneChoices = catalog.airPlaneChoicesByAirport[airport.type];
  /* C85 ne change que l'objectif C68 historique (profit max). Les modes C72/C82 ont des
   * objectifs differents ; ils conservent volontairement la liste complete. Le selectedPlane
   * reste evalue separement ci-dessus, meme s'il est domine et absent de la frontier. */
  if (C85_AIR_EQUIPMENT_FRONTIER && C72_PLANE_CHOICE == 0 && !C82_ENGINE_CALIBRATION
      && ("airPlaneFrontierByAirport" in catalog)
      && airport.type in catalog.airPlaneFrontierByAirport
      && catalog.airPlaneFrontierByAirport[airport.type].len() > 0) {
    routePlaneChoices = catalog.airPlaneFrontierByAirport[airport.type];
  }

  foreach (plane in routePlaneChoices) {
    if (plane.id == selectedPlane.id) continue;
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null) continue;
    if (C72_PLANE_CHOICE == 1) {
      if (bestEconomics == null || economics.roi > bestEconomics.roi ||
          (economics.roi == bestEconomics.roi && economics.profitAnnual > bestEconomics.profitAnnual)) {
        bestPlane = plane;
        bestEconomics = economics;
      }
    } else if (C72_PLANE_CHOICE == 2) {
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
      if (bestEconomics == null || curScore > bestScore ||
          (curScore == bestScore && economics.profitAnnual > bestEconomics.profitAnnual)) {
        bestPlane = plane;
        bestEconomics = economics;
        bestScore = curScore;
      }
    } else {
      if (bestEconomics == null || economics.profitAnnual > bestEconomics.profitAnnual ||
          (economics.profitAnnual == bestEconomics.profitAnnual && economics.roi > bestEconomics.roi)) {
        bestPlane = plane;
        bestEconomics = economics;
      }
    }
    if (C69_BOTTLENECK_PROBE) {
      evalCount++;
      if (r_econ == null || economics.roi > r_econ.roi ||
          (economics.roi == r_econ.roi && economics.profitAnnual > r_econ.profitAnnual)) {
        r_plane = plane;
        r_econ = economics;
      }
      local curDenom = economics.capital > kDec ? economics.capital : kDec;
      local curScore = curDenom > 0 ? (economics.profitAnnual.tofloat() * 1000.0) / curDenom : 0.0;
      if (c_econ == null || curScore > c_score ||
          (curScore == c_score && economics.profitAnnual > c_econ.profitAnnual)) {
        c_plane = plane;
        c_econ = economics;
        c_score = curScore;
      }
    }
  }

  if (C69_BOTTLENECK_PROBE && evalCount >= 2) {
    C69_PLANE_CHOICE_CALLS++;
    if (r_plane.id != bestPlane.id) C69_PLANE_CHOICE_DIFFER_ROI++;
    if (c_plane.id != bestPlane.id) C69_PLANE_CHOICE_DIFFER_C69++;

    if (r_plane.id != bestPlane.id || c_plane.id != bestPlane.id) {
      local avail = OpexAvailableCapital();
      local p_name = OpexPlaneName(bestPlane.id);
      local r_name = OpexPlaneName(r_plane.id);
      local c_name = OpexPlaneName(c_plane.id);
      OpexC69Log("phase=plane_choice dist=" + distance + " kdec=" + kDec + " avail=" + avail
          + " nplanes=" + evalCount
          + " p_id=" + bestPlane.id + " p_name=" + p_name + " p_P=" + bestEconomics.profitAnnual
          + " p_C=" + bestEconomics.capital + " p_roi=" + bestEconomics.roi
          + " r_id=" + r_plane.id + " r_name=" + r_name + " r_P=" + r_econ.profitAnnual
          + " r_C=" + r_econ.capital + " r_roi=" + r_econ.roi
          + " c_id=" + c_plane.id + " c_name=" + c_name + " c_P=" + c_econ.profitAnnual
          + " c_C=" + c_econ.capital + " c_roi=" + c_econ.roi);
    }
  }

  return { plane = bestPlane, economics = bestEconomics };
}

/* M3/G12 : comparaison PASSIVE du plan air deja elu contre les autres appareils compatibles avec
 * le meme type d'aeroport, sur la meme distance/demande et avec le meme nombre initial d'avions. */
function OpexM3ProbeAirEquipment(catalog, plan, phase)
{
  if (!EQUIPMENT_ROI_PROBE || plan == null || !("airport" in plan) || !("plane" in plan) ||
      !(plan.airport.type in catalog.airPlaneChoicesByAirport)) return;
  local alternatives = catalog.airPlaneChoicesByAirport[plan.airport.type];
  if (alternatives.len() == 0) return;
  local infrastructureMaintenance = AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local newAirports = (("reuseA" in plan) && plan.reuseA ? 0 : 1)
      + (("reuseB" in plan) && plan.reuseB ? 0 : 1);
  local fixedPlanes = ("planes" in plan) && plan.planes > 0 ? plan.planes : 1;
  local bestProfit = null, bestProfitId = -1;
  local bestRoi = null, bestRoiId = -1;
  local bestNativeProfit = null, bestNativeProfitId = -1;
  local bestNativeRoi = null, bestNativeRoiId = -1;
  local viable = 0, nativeChoices = 0, refitProxyChoices = 0;
  foreach (plane in alternatives) {
    if (plane.maxOrderDistance > 0 && plan.distance > plane.maxOrderDistance) continue;
    local native = plane.defaultCargo == catalog.paxCargo;
    if (native) nativeChoices++; else refitProxyChoices++;
    local economics = OpexAirEconomics(catalog, plan.airport, plane, plan.distance, plan.monthlyPax,
        infrastructureMaintenance, 0, newAirports, 0, fixedPlanes);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = plane.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = plane.id;
    }
    if (native && (bestNativeProfit == null || economics.profitAnnual > bestNativeProfit.profitAnnual ||
        (economics.profitAnnual == bestNativeProfit.profitAnnual && economics.roi > bestNativeProfit.roi))) {
      bestNativeProfit = economics; bestNativeProfitId = plane.id;
    }
    if (native && (bestNativeRoi == null || economics.roi > bestNativeRoi.roi ||
        (economics.roi == bestNativeRoi.roi && economics.profitAnnual > bestNativeRoi.profitAnnual))) {
      bestNativeRoi = economics; bestNativeRoiId = plane.id;
    }
  }
  OpexM3EquipmentLog("mode=air phase=" + phase + " airport_type=" + plan.airport.type
      + " choices=" + alternatives.len() + " viable=" + viable + " native_choices=" + nativeChoices
      + " refit_proxy_choices=" + refitProxyChoices + " selected=" + plan.plane.id
      + " selected_refit=" + (plan.plane.defaultCargo != catalog.paxCargo ? 1 : 0)
      + " selected_profit=" + plan.economics.profitAnnual + " selected_roi=" + plan.economics.roi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_roi_id=" + bestRoiId + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_native_profit_id=" + bestNativeProfitId
      + " best_native_profit=" + (bestNativeProfit != null ? bestNativeProfit.profitAnnual : -999999999)
      + " best_native_roi_id=" + bestNativeRoiId
      + " best_native_roi=" + (bestNativeRoi != null ? bestNativeRoi.roi : -1));
}

function OpexM3ProbeAirPreAdmission(catalog, airport, selectedPlane, distance, monthlyPax,
                                    infrastructureMaintenance, maxCapital, newAirportCount,
                                    opcodePadding, selectedEconomics, phase)
{
  if (!EQUIPMENT_ROI_PROBE || airport == null || selectedPlane == null ||
      !(airport.type in catalog.airPlaneChoicesByAirport)) return;
  local alternatives = catalog.airPlaneChoicesByAirport[airport.type];
  if (alternatives.len() == 0) return;
  local bestProfit = null, bestProfitId = -1;
  local bestRoi = null, bestRoiId = -1;
  local bestNativeProfit = null, bestNativeProfitId = -1;
  local bestNativeRoi = null, bestNativeRoiId = -1;
  local viable = 0, nativeChoices = 0, refitProxyChoices = 0;
  foreach (plane in alternatives) {
    if (plane.maxOrderDistance > 0 && distance > plane.maxOrderDistance) continue;
    local native = plane.defaultCargo == catalog.paxCargo;
    if (native) nativeChoices++; else refitProxyChoices++;
    local economics = OpexAirEconomics(catalog, airport, plane, distance, monthlyPax,
        infrastructureMaintenance, maxCapital, newAirportCount, opcodePadding);
    if (economics == null) continue;
    viable++;
    if (bestProfit == null || economics.profitAnnual > bestProfit.profitAnnual ||
        (economics.profitAnnual == bestProfit.profitAnnual && economics.roi > bestProfit.roi)) {
      bestProfit = economics; bestProfitId = plane.id;
    }
    if (bestRoi == null || economics.roi > bestRoi.roi ||
        (economics.roi == bestRoi.roi && economics.profitAnnual > bestRoi.profitAnnual)) {
      bestRoi = economics; bestRoiId = plane.id;
    }
    if (native && (bestNativeProfit == null || economics.profitAnnual > bestNativeProfit.profitAnnual ||
        (economics.profitAnnual == bestNativeProfit.profitAnnual && economics.roi > bestNativeProfit.roi))) {
      bestNativeProfit = economics; bestNativeProfitId = plane.id;
    }
    if (native && (bestNativeRoi == null || economics.roi > bestNativeRoi.roi ||
        (economics.roi == bestNativeRoi.roi && economics.profitAnnual > bestNativeRoi.profitAnnual))) {
      bestNativeRoi = economics; bestNativeRoiId = plane.id;
    }
  }
  local selectedProfit = selectedEconomics != null ? selectedEconomics.profitAnnual : -999999999;
  local selectedRoi = selectedEconomics != null ? selectedEconomics.roi : -1;
  local selectedPositive = selectedEconomics != null && selectedEconomics.profitAnnual > 0;
  OpexM3EquipmentLog("mode=air phase=" + phase + " airport_type=" + airport.type
      + " choices=" + alternatives.len() + " viable=" + viable + " native_choices=" + nativeChoices
      + " refit_proxy_choices=" + refitProxyChoices + " selected=" + selectedPlane.id
      + " selected_refit=" + (selectedPlane.defaultCargo != catalog.paxCargo ? 1 : 0)
      + " selected_ok=" + (selectedEconomics != null ? 1 : 0)
      + " selected_profit=" + selectedProfit + " selected_roi=" + selectedRoi
      + " best_profit_id=" + bestProfitId
      + " best_profit=" + (bestProfit != null ? bestProfit.profitAnnual : -999999999)
      + " best_roi_id=" + bestRoiId + " best_roi=" + (bestRoi != null ? bestRoi.roi : -1)
      + " best_native_profit_id=" + bestNativeProfitId
      + " best_native_profit=" + (bestNativeProfit != null ? bestNativeProfit.profitAnnual : -999999999)
      + " best_native_roi_id=" + bestNativeRoiId
      + " best_native_roi=" + (bestNativeRoi != null ? bestNativeRoi.roi : -1)
      + " admission_flip=" + ((!selectedPositive && bestProfit != null && bestProfit.profitAnnual > 0) ? 1 : 0)
      + " native_admission_flip="
      + ((!selectedPositive && bestNativeProfit != null && bestNativeProfit.profitAnnual > 0) ? 1 : 0));
}

/* An anchor only describes the north-west corner. Its buildability depends on
 * the airport footprint, so the airport type is part of the durable-site key. */
function OpexAirSitePaddingKey(site, airportType)
{
  return "air_site|" + airportType + "|" + site.anchor;
}

function OpexAirTownPaddingKey(site)
{
  return "air_town_limit|" + site.town.tile;
}

/* C78.2 : une paire AIR est non orientee. Generation et chantier ecrivent
 * exactement la meme cle, meme si un hub inverse l'ordre des extremites. */
function OpexAirPairKey(siteA, siteB)
{
  local a = siteA.town.tile;
  local b = siteB.town.tile;
  if (a > b) {
    local swap = a;
    a = b;
    b = swap;
  }
  return "air|" + a + "|" + b;
}

/* Compatibilite des sauvegardes anterieures a C78.2 : les anciennes cles
 * pouvaient avoir ete ecrites dans l'autre sens. */
function OpexAirPairIsAbandoned(abandoned, siteA, siteB)
{
  if (abandoned == null || siteA == null || siteB == null) return false;
  local canonical = OpexAirPairKey(siteA, siteB);
  if (canonical in abandoned) return true;
  local legacyForward = "air|" + siteA.town.tile + "|" + siteB.town.tile;
  if (legacyForward != canonical && (legacyForward in abandoned)) return true;
  local legacyReverse = "air|" + siteB.town.tile + "|" + siteA.town.tile;
  return legacyReverse != canonical && (legacyReverse in abandoned);
}

/* C78 etape 2 : identification de la ville d'un hub aerien. */
function OpexC78HubTownId(h)
{
  if (h != null) {
    if (("town" in h) && h.town != null && ("id" in h.town)) return h.town.id;
    if (("anchor" in h) && AIMap.IsValidTile(h.anchor)) return AITile.GetClosestTown(h.anchor);
  }
  return -1;
}

/* Calcul du delta d'opcodes consommes depuis (t0, l0). */
function OpexAirCalcDeltaOps(t0, l0)
{
  local left = AIController.GetOpsTillSuspend();
  local elapsed = AIController.GetTick() - t0;
  return elapsed <= 0
    ? l0 - left
    : l0 + (elapsed - 1) * OPS_PER_TICK + (OPS_PER_TICK - left);
}

/* 1. Preparation : combos, villes, OpexAirTownPoolLimit, indices et reprise. */
function OpexAirPlansPrepare(ctx)
{
  local catalog = ctx.catalog;
  local lines = ctx.lines;
  local targetTownId = ctx.targetTownId;
  if (V93_AIR_DEMAND_PRODUCTION) AIR_DEMAND_PAX_CARGO = catalog.paxCargo;
  local resumeState = ctx.resumeState;
  local t0_all = ctx.t0_all;
  local sliced = ctx.sliced;

  if (C80_AIR_EVAL_FAST) {
    /* Les prix changent au debut de chaque mois (inflation) : une planification decoupee qui
     * enjambe un changement de mois repart avec des memos vides pour rester exacte. */
    local memoDate = AIDate.GetCurrentDate();
    local memoMonth = AIDate.GetYear(memoDate) * 12 + AIDate.GetMonth(memoDate);
    if (!sliced || !("airFastInit" in resumeState) || AIR_MEMO_MONTH != memoMonth) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
      if (sliced) resumeState.airFastInit <- true;
    }
    AIR_MEMO_MONTH = memoMonth;
  }
  if (sliced) {
    if (!("done" in resumeState)) resumeState.done <- false;
    if (resumeState.done) {
      ctx.bestPlan = ("bestPlan" in resumeState) ? resumeState.bestPlan : null;
      return false;
    }
    if (!("combo" in resumeState)) resumeState.combo <- 0;
    if (!("a" in resumeState)) resumeState.a <- 0;
    if (!("b" in resumeState)) resumeState.b <- 1;
    if (!("sites" in resumeState)) resumeState.sites <- null;
    if (!("bestPlan" in resumeState)) resumeState.bestPlan <- null;
    if (!("stationLimitedTowns" in resumeState)) resumeState.stationLimitedTowns <- {};
    if (!("perfOpsSites" in resumeState)) resumeState.perfOpsSites <- 0;
    if (!("perfOpsEval" in resumeState)) resumeState.perfOpsEval <- 0;
    if (!("perfProbesCount" in resumeState)) resumeState.perfProbesCount <- 0;
    if (!("perfCheapSkip" in resumeState)) resumeState.perfCheapSkip <- 0;
    if (!("perfSitesFound" in resumeState)) resumeState.perfSitesFound <- 0;
    if (!("totalOps" in resumeState)) resumeState.totalOps <- 0;
    if (!("startTick" in resumeState)) resumeState.startTick <- t0_all;
    if (!("towns" in resumeState)) resumeState.towns <- null;
    if (!("combos" in resumeState)) resumeState.combos <- null;
    if (!("townLimit" in resumeState)) resumeState.townLimit <- -1;
    if (!("scanIndex" in resumeState)) resumeState.scanIndex <- 0;
    if (!("scanSites" in resumeState)) resumeState.scanSites <- [];
    if (!("scanProbes" in resumeState)) resumeState.scanProbes <- null;
    if (!("rankIndex" in resumeState)) resumeState.rankIndex <- 0;
    if (!("rankSites" in resumeState)) resumeState.rankSites <- [];
    if (!("c83TopTownIds" in resumeState)) resumeState.c83TopTownIds <- null;
  }
  local perfOpsSites = sliced ? resumeState.perfOpsSites : 0;
  local perfOpsEval = sliced ? resumeState.perfOpsEval : 0;
  local perfProbesCount = sliced ? resumeState.perfProbesCount : 0;
  local perfCheapSkip = sliced ? resumeState.perfCheapSkip : 0;
  local perfSitesFound = sliced ? resumeState.perfSitesFound : 0;

  local combos = sliced && resumeState.combos != null
      ? resumeState.combos
      : ((("airCombos" in catalog) && catalog.airCombos != null && catalog.airCombos.len() > 0)
          ? catalog.airCombos
          : (catalog.airport != null && catalog.plane != null ? [{ airport = catalog.airport, plane = catalog.plane }] : []));
  if (sliced && resumeState.combos == null) resumeState.combos = combos;
  local servedDiag = sliced && ("servedDiag" in resumeState) ? resumeState.servedDiag : null;
  if (DECISION_LOG && servedDiag == null) {
    AIR_PLAN_DIAG_SEQ++;
    servedDiag = {
      scan = AIR_PLAN_DIAG_SEQ,
      nullCalls = 0, emptyCalls = 0, nonemptyCalls = 0,
      trueCalls = 0, falseCalls = 0,
      loggedFalseTowns = {}, loggedFalseCount = 0, noAirLogged = false,
    };
    local linesState = lines == null ? "null" : (lines.len() == 0 ? "empty" : "nonempty");
    local lineCount = lines == null ? 0 : lines.len();
    local airLineCount = 0;
    if (lines != null) {
      foreach (line in lines) {
        if (("mode" in line) && line.mode == "air") airLineCount++;
      }
    }
    OpexDecide("AIR_PLAN_INPUT", "scan=" + servedDiag.scan + " lines_state=" + linesState
               + " line_count=" + lineCount + " air_line_count=" + airLineCount
               + " combos=" + combos.len());
    if (sliced) resumeState.servedDiag <- servedDiag;
  }
  if (combos.len() == 0) {
    if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "no_engine", 1);
    if (DECISION_LOG) {
      OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
                 + " null_calls=0 empty_calls=0 nonempty_calls=0 true_calls=0 false_calls=0"
                 + " false_towns_logged=0");
    }
    if (sliced) {
      resumeState.bestPlan = null;
      resumeState.sites = null;
      resumeState.done = true;
    }
    if (C80_AIR_EVAL_FAST) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
    }
    ctx.bestPlan = null;
    return false;
  }

  /* C80 tranche 5 bis : index exacts des lignes aeriennes, construits une fois par appel (les
   * lignes ne changent pas pendant la planification). Memes resolutions de gare que les boucles
   * qu'ils remplacent : nombre de routes par gare (decouverte des hubs) et paires deja reliees
   * (hub a hub), au lieu d'un parcours de toutes les lignes par hub et par paire de hubs. */
  local hubIndex = null;
  if (C80_AIR_HUB_INDEX && AIR_HUB && lines != null) {
    hubIndex = { routes = {}, pairs = {} };
    foreach (other in lines) {
      if (!("mode" in other) || other.mode != "air") continue;
      local oA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
          : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
      local oB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
          : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
      hubIndex.routes.rawset(oA, ((oA in hubIndex.routes) ? hubIndex.routes[oA] : 0) + 1);
      if (oB != oA) hubIndex.routes.rawset(oB, ((oB in hubIndex.routes) ? hubIndex.routes[oB] : 0) + 1);
      if (AIStation.IsValidStation(oA) && AIStation.IsValidStation(oB)) {
        hubIndex.pairs.rawset(oA + "|" + oB, true);
        hubIndex.pairs.rawset(oB + "|" + oA, true);
      }
    }
  }

  local c83TopTownIds = sliced && resumeState.c83TopTownIds != null
      ? resumeState.c83TopTownIds
      : {};
  local towns = sliced && resumeState.towns != null
      ? resumeState.towns
      : OpexAirSortedTowns(catalog.towns);
  if (!sliced || resumeState.towns == null) {
    /* C83.1 : la double prise proactive ne concerne que les plus grandes
     * villes deja couvertes par la politique early-slot. Calculer ce rang
     * avant une eventuelle remise en tete targetTownId preserve le vrai
     * classement par population. */
    if (OpexAirC83SlotSignalEnabled() && AIR_C83_TARGET_TOWNS > 0) {
      /* c83_fixes ne retouche pas cette liste : elle autorise le second slot
       * proactif d'une ville DEJA servie par Opex (C83.1 adopte). Le filtre
       * « ville encore disputable, Opex absent » ne concerne que le watcher. */
      local c83TopLimit = towns.len() < AIR_C83_TARGET_TOWNS
          ? towns.len() : AIR_C83_TARGET_TOWNS;
      for (local c83i = 0; c83i < c83TopLimit; c83i++) {
        if (towns[c83i].pop >= AIR_EARLY_SLOT_MIN_POP) {
          c83TopTownIds.rawset(towns[c83i].id, true);
        }
      }
    }
    if (sliced) resumeState.c83TopTownIds = c83TopTownIds;
    if (targetTownId >= 0) {
      local targetedTowns = [];
      foreach (town in towns) if (town.id == targetTownId) targetedTowns.append(town);
      foreach (town in towns) if (town.id != targetTownId) targetedTowns.append(town);
      towns = targetedTowns;
    }
    if (sliced) resumeState.towns = towns;
  }
  local limit = sliced && resumeState.townLimit >= 0
      ? resumeState.townLimit
      : OpexAirTownPoolLimit(towns);
  if (sliced) resumeState.townLimit = limit;
  /* C78 etape 2 : une generation complete journalisee par an, sous sonde seulement (aucun appel
   * d'API au defaut). Les bornes et les tuiles permettent de situer toute paire d'AAAHogEx par
   * rapport aux bandes de distance (airMin = bascule rail/avion). En mode reprenable (C78.4),
   * la decision est prise a la premiere tranche et conservee dans resumeState. */
  local c78Year = -1;
  local c78Gen = false;
  if (sliced && ("c78Gen" in resumeState)) {
    c78Year = resumeState.c78Year;
    c78Gen = resumeState.c78Gen;
  } else {
    if (C69_BOTTLENECK_PROBE && targetTownId < 0) {
      c78Year = AIDate.GetYear(AIDate.GetCurrentDate());
      c78Gen = C78_GEN_LOG_YEAR != c78Year;
    }
    if (c78Gen) {
      C78_GEN_LOG_YEAR = c78Year;
      local poolLimit = towns.len() < 120 ? towns.len() : 120;
      local townsStr = "";
      for (local idx = 0; idx < poolLimit; idx++) {
        if (idx > 0) townsStr += ",";
        townsStr += towns[idx].id + ":" + towns[idx].pop + ":" + towns[idx].tile;
      }
      local c78B = OpexCatalogBounds(catalog);
      OpexC78Log("C78_AIRPOOL", "year=" + c78Year + " pool=" + limit
          + " mapx=" + AIMap.GetMapSizeX() + " airMin=" + c78B.airMin + " airMax=" + c78B.airMax
          + " railMin=" + c78B.railMin + " railMax=" + c78B.railMax
          + " overlap=" + c78B.railAirOverlapMin
          + " e_cash=" + AIError.ERR_NOT_ENOUGH_CASH + " e_authority=" + AIError.ERR_LOCAL_AUTHORITY_REFUSES
          + " e_clear=" + AIError.ERR_AREA_NOT_CLEAR + " e_flat=" + AIError.ERR_FLAT_LAND_REQUIRED
          + " e_site=" + AIError.ERR_SITE_UNSUITABLE
          + " e_town_stations=" + AIStation.ERR_STATION_TOO_MANY_STATIONS_IN_TOWN
          + " e_too_close=" + AIStation.ERR_STATION_TOO_CLOSE_TO_ANOTHER_STATION
          + " towns=" + townsStr);
    }
    if (sliced) {
      resumeState.c78Year <- c78Year;
      resumeState.c78Gen <- c78Gen;
    }
  }
  local stationLimitedTowns = sliced ? resumeState.stationLimitedTowns : {};
  local bestPlan = sliced ? resumeState.bestPlan : null;
  /* GetMonthlyMaintenanceCost expose le tarif potentiel, pas une depense toujours active.
   * CompaniesGenStatistics ne le debite que si le reglage de partie est arme. La configuration
   * gelee le laisse a false : compter ce tarif rendait toutes les paires de la graine 42
   * artificiellement deficitaires (270 000/an pour deux AT_LARGE). */
  local infrastructureMaintenance =
      AIGameSettings.GetValue("economy.infrastructure_maintenance") != 0;
  local comboStart = sliced ? resumeState.combo : 0;

  ctx.combos = combos;
  ctx.servedDiag = servedDiag;
  ctx.hubIndex = hubIndex;
  ctx.c83TopTownIds = c83TopTownIds;
  ctx.towns = towns;
  ctx.limit = limit;
  ctx.c78Year = c78Year;
  ctx.c78Gen = c78Gen;
  ctx.stationLimitedTowns = stationLimitedTowns;
  ctx.bestPlan = bestPlan;
  ctx.infrastructureMaintenance = infrastructureMaintenance;
  ctx.comboStart = comboStart;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;

  return true;
}

/* 2. Recherche des sites : sondage des villes candidates et revalidation avant classement. */
function OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo)
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
    if (C83_FIXES && targetTownId >= 0) {
      scanEnd = scanStart;
      for (local c83Scan = scanStart; c83Scan < limit; c83Scan++) {
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
      probes.townsLeft = limit - i;
      if (C83_FIXES && targetTownId >= 0) probes.townsLeft = scanEnd - i;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      if (towns[i].id in stationLimitedTowns) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_station_limit", 1);
        if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_station_limit");
      } else {
        /* Ne filtrer que les lignes aeriennes existantes : un aeroport ne concurrence pas une
         * gare ferroviaire, et exclure les villes deja servies en rail empechait toute
         * construction aerienne sur une carte partiellement couverte. */
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        if (isServed && !c83OwnSecondSlot) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "origin_served", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=origin_served");
        } else if (!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600) {
          /* Grands aeroports : accessibles des 600 habitants. A 0, le booleen
           * est le seul test ajoute sur ce chemin. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_small", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_small");
        } else if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP) {
          /* V93 : plancher minimal, grand ou petit. A 0 ce test est faux. */
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "town_pop_v93", 1);
          if (c78Gen) OpexC78Log("C78_AIRTOWN", "year=" + c78Year + " combo=" + airport.type + ":" + plane.id + " town=" + towns[i].id + " rank=" + i + " outcome=town_pop_v93");
        } else {
          local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
              ? targetTownId : -1;
          if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
            c83RequiredSlotTown = towns[i].id;
          }
          if (c78Gen && ("c78NoSite" in probes)) probes.c78NoSite = null;
          local site = OpexAirFindSite(towns[i], airport, probes, c83RequiredSlotTown);
          if (site != null) {
            if (c83OwnSecondSlot) site.c83OwnSecondSlot <- true;
            if (C83_FIXES && c83RequiredSlotTown >= 0) site.c83SlotTown <- c83RequiredSlotTown;
            scanSites.append(site);
            if (c78Gen) {
              if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < 600) {
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
          return false;
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
      local site = scanSites[rankIndex];
      if (OpexAirSiteStillBuildable(site, airport, plane, false, stationLimitedTowns)) {
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
          return false;
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
  return true;
}

/* 3. Arm « nouvelles paires » : evaluation de toutes les paires (a, b) de sites neufs. */
function OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo)
{
  local sites = ctx.sites;
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local opsBudget = ctx.opsBudget;
  local deadlineTick = ctx.deadlineTick;
  local stationLimitedTowns = ctx.stationLimitedTowns;
  local targetTownId = ctx.targetTownId;
  local lines = ctx.lines;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local projects = ctx.projects;
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

  local tEval0 = AIController.GetTick();
  local lEval0 = AIController.GetOpsTillSuspend();
  local siteValidity = {};
  /* Une regeneration AIR ciblee sur une ville ne conservera plus tard que les
   * projets qui touchent cette ville. OpexAirPlansPrepare met deja la cible en
   * tete : dans le cas normal, evaluer seulement a=0 transforme C(n,2) en O(n)
   * sans changer l'ensemble de candidats finalement reinjecte. Si l'invariant
   * ne tient pas, repli exact sur le parcours complet + filtre historique. */
  local targetSiteIndex = -1;
  if (targetTownId >= 0) {
    for (local targetIndex = 0; targetIndex < sites.len(); targetIndex++) {
      if (sites[targetIndex].town.id == targetTownId) {
        targetSiteIndex = targetIndex;
        break;
      }
    }
  }
  local pairOuterLimit = sites.len();
  if (targetTownId >= 0 && targetSiteIndex < 0) pairOuterLimit = 0;
  else if (targetTownId >= 0 && targetSiteIndex == 0) pairOuterLimit = 1;
  local startA = sliced && resumeState.combo == comboIndex ? resumeState.a : 0;
  local pairProgress = false;
  for (local a = startA; a < pairOuterLimit; a++) {
    local startB = sliced && resumeState.combo == comboIndex && a == startA
        ? resumeState.b : a + 1;
    for (local b = startB; b < sites.len(); b++) {
      if (sliced) {
        resumeState.bestPlan = bestPlan;
        resumeState.perfOpsSites = perfOpsSites;
        resumeState.perfOpsEval = perfOpsEval + _calcDeltaOps(tEval0, lEval0);
        resumeState.perfProbesCount = perfProbesCount;
        resumeState.perfCheapSkip = perfCheapSkip;
        resumeState.perfSitesFound = perfSitesFound;
        local sliceOps = _calcDeltaOps(t0_all, l0_all);
        /* Toujours consommer au moins UNE paire par appel. Le cout fixe de
         * reprise peut depasser le reliquat du tick ; rendre la main avant la
         * premiere paire bloquait alors eternellement sur le meme curseur. */
        if (pairProgress && ((opsBudget > 0 && sliceOps >= opsBudget)
            || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick))) {
          resumeState.totalOps += sliceOps;
          ctx.bestPlan = bestPlan;
          ctx.perfOpsSites = perfOpsSites;
          ctx.perfOpsEval = perfOpsEval;
          ctx.perfProbesCount = perfProbesCount;
          ctx.perfCheapSkip = perfCheapSkip;
          ctx.perfSitesFound = perfSitesFound;
          return false;
        }
        resumeState.combo = comboIndex;
        resumeState.sites = sites;
        local nextA = a;
        local nextB = b + 1;
        if (nextB >= sites.len()) {
          nextA = a + 1;
          nextB = nextA + 1;
        }
        resumeState.a = nextA;
        resumeState.b = nextB;
        pairProgress = true;
        if (resumingCombo) {
          local keyA = sites[a].anchor;
          local keyB = sites[b].anchor;
          if (!(keyA in siteValidity)) {
            siteValidity.rawset(keyA, OpexAirSiteStillBuildable(
                sites[a], airport, plane, false, stationLimitedTowns));
          }
          if (!siteValidity[keyA]) continue;
          if (!(keyB in siteValidity)) {
            siteValidity.rawset(keyB, OpexAirSiteStillBuildable(
                sites[b], airport, plane, false, stationLimitedTowns));
          }
          if (!siteValidity[keyB]) continue;
        }
      }
      if (targetTownId >= 0
          && sites[a].town.id != targetTownId && sites[b].town.id != targetTownId) continue;
      if (C83_FIXES && OpexAirTownCentersLinked(sites[a].town.tile, sites[b].town.tile, lines)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "batch_plan_dead", 1);
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + linkedDist + " outcome=batch_plan_dead P=-1 C=-1");
        }
        continue;
      }
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(sites[a].town.tile, sites[b].town.tile);
      if (C80_AIR_EVAL_FAST) {
        if (distance < minDist) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
          continue;
        }
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      sites[a].anchor, sites[b].anchor);
      local flightDistance = OpexFlightDistance(sites[a].anchor, sites[b].anchor);
      if (!C80_AIR_EVAL_FAST && distance < minDist) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }

      if (abandoned != null) {
        if (OpexAirPairIsAbandoned(abandoned, sites[a], sites[b])
            || (OPEX_AIR_TOWN_PAD && ((OpexAirTownPaddingKey(sites[a]) in abandoned)
                || (OpexAirTownPaddingKey(sites[b]) in abandoned)))
            || (OPEX_AIR_SITE_PAD && ((OpexAirSitePaddingKey(sites[a], airport.type) in abandoned)
                || (OpexAirSitePaddingKey(sites[b], airport.type) in abandoned)))) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }

      local popA = sites[a].town.pop;
      local popB = sites[b].town.pop;
      local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthlyPax = OpexAirTownMonthlyPax(sites[a].town, sites[a].anchor, airport, ctx.lines)
            + OpexAirTownMonthlyPax(sites[b].town, sites[b].anchor, airport, ctx.lines);
      }
      if (a == 0 && b == 1) {
        OpexSign(AIMap.GetTileIndex(1, 5), "AX|PA=" + popA + "|PB=" + popB + "|MPX=" + monthlyPax);
      }

      local routeChoice = OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
                                                  infrastructureMaintenance, maxCapital, 2, opcodePadding,
                                                  C80_AIR_CHOICE_MEMO ? ("n|" + sites[a].town.id + "|" + sites[b].town.id
                                                      + "|" + airport.type + "|" + plane.id) : null);
      local routePlane = routeChoice.plane;
      local economics = routeChoice.economics;
      if (EQUIPMENT_ROI_PROBE) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 2, opcodePadding, economics, "pre_admission_newpair");
      }
      if (economics == null) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "economics_unavailable", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
        continue;
      }

      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, sites[a].anchor, sites[b].anchor);
      }
      local plan = {
        siteA = sites[a], siteB = sites[b], distance = flightDistance,
        orderDistance = orderDistance,
        airport = airport, plane = routePlane,
        monthlyPax = monthlyPax, planes = economics.planes, capital = economics.capital, economics = economics,
        reuseA = false, hubRoutes = 0, arm = "newpair",
        c83OwnSecondSlotA = ("c83OwnSecondSlot" in sites[a]) && sites[a].c83OwnSecondSlot,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in sites[b]) && sites[b].c83OwnSecondSlot,
      };
      if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);

      if (a == 0 && b == 1) {
        OpexSign(AIMap.GetTileIndex(1, 8), "AY|" + economics.capital + "|"
                                              + economics.profitAnnual);
        OpexSign(AIMap.GetTileIndex(1, 9), "AV|" + routePlane.speed + "|" + routePlane.capacity
                                              + "|" + economics.planes + "|"
                                              + economics.oneWayDays.tointeger());
      }
      if (economics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "profit_nonpositive", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
      } else {
        if (c78Gen) {
          if (V93_AIR_DEMAND_PRODUCTION) {
            local paxOld = ((sites[a].town.pop + sites[b].town.pop) * TOWN_CATCHMENT_SHARE_PCT) / 100;
            if (paxOld < 10) paxOld = 10;
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=newpair combo=" + airport.type + ":" + plane.id + " townA=" + sites[a].town.id + " townB=" + sites[b].town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
      }
    }
  }
  perfOpsEval += _calcDeltaOps(tEval0, lEval0);
  if (sliced) {
    resumeState.a = sites.len();
    resumeState.b = sites.len();
    resumeState.bestPlan = bestPlan;
    resumeState.perfOpsEval = perfOpsEval;
    local pairSliceOps = _calcDeltaOps(t0_all, l0_all);
    if ((opsBudget > 0 && pairSliceOps >= opsBudget)
        || (deadlineTick > 0 && AIController.GetTick() >= deadlineTick)) {
      resumeState.perfOpsSites = perfOpsSites;
      resumeState.perfProbesCount = perfProbesCount;
      resumeState.perfCheapSkip = perfCheapSkip;
      resumeState.perfSitesFound = perfSitesFound;
      resumeState.totalOps += pairSliceOps;
      ctx.bestPlan = bestPlan;
      ctx.perfOpsSites = perfOpsSites;
      ctx.perfOpsEval = perfOpsEval;
      ctx.perfProbesCount = perfProbesCount;
      ctx.perfCheapSkip = perfCheapSkip;
      ctx.perfSitesFound = perfSitesFound;
      return false;
    }
  }

  ctx.bestPlan = bestPlan;
  ctx.perfOpsSites = perfOpsSites;
  ctx.perfOpsEval = perfOpsEval;
  ctx.perfProbesCount = perfProbesCount;
  ctx.perfCheapSkip = perfCheapSkip;
  ctx.perfSitesFound = perfSitesFound;
  return true;
}

/* 4. Decouverte des hubs : lignes existantes et aeroports orphelins. */
function OpexAirPlansDiscoverHubs(ctx, combo, airport, plane)
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

  if (AIR_HUB && lines != null) {
    if (sites.len() < AIR_HUB_NEW_SITE_POOL) {
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
          if (towns[c83Scan].id == targetTownId) {
            hubScanEnd = c83Scan + 1;
            break;
          }
        }
      }
      for (local i = 0; i < hubScanEnd && sites.len() < AIR_HUB_NEW_SITE_POOL; i++) {
        hubProbes.townsLeft = limit - i;
        if (C83_FIXES && targetTownId >= 0) hubProbes.townsLeft = hubScanEnd - i;
        if (towns[i].id in stationLimitedTowns) {
          continue;
        }
        local isServed = OpexAirTownServed(towns[i], lines, servedDiag);
        local c83OwnSecondSlot = isServed && (towns[i].id in c83TopTownIds)
            && OpexAirC83SecondSlotOpen(towns[i]);
        if (isServed && !c83OwnSecondSlot) continue;
        /* Typage : grands aeroports des 600 hab. A 0, seul le booleen est ajoute. */
        if (!V93_AIRPORT_NO_POP_FLOOR && combo.kind == "large" && towns[i].pop < 600) continue;
        if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < V93_AIRPORT_MIN_POP) continue;
        if (combo.kind == "small" && towns[i].pop >= 2500) continue;
        local c83RequiredSlotTown = (targetTownId >= 0 && towns[i].id == targetTownId)
            ? targetTownId : -1;
        if (C83_FIXES && c83RequiredSlotTown < 0 && c83OwnSecondSlot) {
          c83RequiredSlotTown = towns[i].id;
        }
        local extraSite = OpexAirFindSite(towns[i], airport, hubProbes, c83RequiredSlotTown);
        if (extraSite != null) {
          if (c83OwnSecondSlot) extraSite.c83OwnSecondSlot <- true;
          if (C83_FIXES && c83RequiredSlotTown >= 0) extraSite.c83SlotTown <- c83RequiredSlotTown;
          /* v93=1 seulement si le scan principal n'a pas deja retenu cette ville. */
          if (V93_AIRPORT_NO_POP_FLOOR && towns[i].pop < 600 && ("c78Gen" in ctx) && ctx.c78Gen) {
            local v93Already = false;
            foreach (prev in sites) {
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
      if (!("mode" in line) || line.mode != "air") continue;
      if (("deadStreak" in line) && line.deadStreak >= 2) continue;
      /* air_hub_fix : l'ancre d'un hub est la TUILE D'AEROPORT (line.stationA/B), pas le
       * centre-ville (line.originA/B). Sous 0, on rejoue litteralement le comportement casse. */
      local ends = null;
      if (AIR_HUB_FIX) {
        ends = [
          { anchor = line.stationA, origin = line.originA, stationId = line.stationA },
          { anchor = line.stationB, origin = line.originB, stationId = line.stationB },
        ];
      } else {
        ends = [
          { anchor = line.originA, origin = line.originA, stationId = line.stationA },
          { anchor = line.originB, origin = line.originB, stationId = line.stationB },
        ];
      }
      foreach (end in ends) {
        if (!AIMap.IsValidTile(end.anchor) || !AIAirport.IsAirportTile(end.anchor)) continue;
        local existingType = AIAirport.GetAirportType(end.anchor);
        if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
        /* Resolution non ambigue : `end.stationId` est une tuile, et `IsValidStation(tuile)`
         * peut etre vrai par pure collision d'indices. On resout toujours depuis l'ancre. */
        local station = AIR_HUB_FIX
            ? AIStation.GetStationID(end.anchor)
            : (AIStation.IsValidStation(end.stationId) ? end.stationId : AIStation.GetStationID(end.anchor));
        if (!AIStation.IsValidStation(station) || (station in seenStations)) continue;

        local routeCount = 0;
        if (hubIndex != null) {
          if (station in hubIndex.routes) routeCount = hubIndex.routes[station];
        } else {
          foreach (other in lines) {
            if (!("mode" in other) || other.mode != "air") continue;
            local otherA = AIR_HUB_FIX ? OpexAirLineStationId(other, 0)
                : (AIStation.IsValidStation(other.stationA) ? other.stationA : AIStation.GetStationID(other.originA));
            local otherB = AIR_HUB_FIX ? OpexAirLineStationId(other, 1)
                : (AIStation.IsValidStation(other.stationB) ? other.stationB : AIStation.GetStationID(other.originB));
            if (otherA == station || otherB == station) routeCount++;
          }
        }
        local maxRoutes = OpexAirAirportMaxRoutes(existingType);
        if (routeCount >= maxRoutes) continue;
        local townId = AITile.GetClosestTown(end.origin);
        if (townId < 0) continue;
        local hubTown = null;
        foreach (town in towns) {
          if (town.id == townId) { hubTown = town; break; }
        }
        if (hubTown == null) {
          hubTown = { id = townId, tile = end.origin, pop = AITown.GetPopulation(townId) };
        }
        seenStations.rawset(station, true);
        hubs.append({ town = hubTown, anchor = end.anchor, stationId = station, routes = routeCount });
      }
    }
    /* Aéroports orphelins : aéroports bâtis sans ligne active (ex: issu d'un BFAIL conservé). */
    local orphanList = AIStationList(AIStation.STATION_AIRPORT);
    for (local st = orphanList.Begin(); !orphanList.IsEnd(); st = orphanList.Next()) {
      if (st in seenStations) continue;
      local loc = AIStation.GetLocation(st);
      if (!AIMap.IsValidTile(loc) || !AIAirport.IsAirportTile(loc)) continue;
      local existingType = AIAirport.GetAirportType(loc);
      if (!OpexAirAirportAcceptsPlane(existingType, plane.planeType)) continue;
      local townId = AITile.GetClosestTown(loc);
      if (townId < 0) continue;
      local hubTown = null;
      foreach (town in towns) {
        if (town.id == townId) { hubTown = town; break; }
      }
      if (hubTown == null) {
        hubTown = { id = townId, tile = loc, pop = AITown.GetPopulation(townId) };
      }
      seenStations.rawset(st, true);
      hubs.append({ town = hubTown, anchor = loc, stationId = st, routes = 0 });
    }
  }

  /* La decouverte des hubs et des sites supplementaires peut elle aussi
   * suspendre. Revalider les destinations neuves au dernier moment avant
   * le classement hub-site. */
  if (sites.len() > 0) {
    local liveHubSites = [];
    foreach (site in sites) {
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
      if (siteFields != "") siteFields += ",";
      siteFields += site.town.id + ":" + site.town.tile;
    }
    local hubFields = hubs.len() == 0 ? "none" : "";
    foreach (hub in hubs) {
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

/* 5. Arm « hub vers site » : evaluation des paires (hub existant, site neuf). */
function OpexAirPlansHubToSite(ctx, combo, airport, plane)
{
  local hubs = ctx.hubs;
  local sites = ctx.sites;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local c78Year = ctx.c78Year;
  local c78Gen = ctx.c78Gen;
  local projects = ctx.projects;
  local bestPlan = ctx.bestPlan;
  local targetTownId = ctx.targetTownId;
  local lines = ctx.lines;

  foreach (hub in hubs) {
    local hubMonthlyPre = C80_AIR_EVAL_FAST
        ? (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1))
        : 0;
    foreach (site in sites) {
      if (targetTownId >= 0
          && hub.town.id != targetTownId && site.town.id != targetTownId) continue;
      if (C83_FIXES && OpexAirTownCentersLinked(hub.town.tile, site.town.tile, lines)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "batch_plan_dead", 1);
        if (c78Gen) {
          local linkedDist = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + linkedDist + " outcome=batch_plan_dead P=-1 C=-1");
        }
        continue;
      }
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local distance = AIMap.DistanceManhattan(hub.town.tile, site.town.tile);
      if (distance < 20) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR,
                                                      hub.anchor, site.anchor);
      local flightDistance = OpexFlightDistance(hub.anchor, site.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }
      if (abandoned != null) {
        if (OpexAirPairIsAbandoned(abandoned, hub, site)
            || (OPEX_AIR_TOWN_PAD && (OpexAirTownPaddingKey(site) in abandoned))
            || (OPEX_AIR_SITE_PAD && (OpexAirSitePaddingKey(site, airport.type) in abandoned))) {
          if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
          if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
          continue;
        }
      }
      local hubMonthly = C80_AIR_EVAL_FAST
          ? hubMonthlyPre
          : (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1));
      local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
      local monthlyPax = hubMonthly + newMonthly;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthlyPax = OpexAirTownMonthlyPax(hub.town, hub.anchor, airport, ctx.lines)
            + OpexAirTownMonthlyPax(site.town, site.anchor, airport, ctx.lines);
      }
      local routeChoice = OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
                                                  infrastructureMaintenance, maxCapital, 1, opcodePadding,
                                                  C80_AIR_CHOICE_MEMO ? ("h|" + hub.stationId + "|" + site.town.id
                                                      + "|" + airport.type + "|" + plane.id) : null);
      local routePlane = routeChoice.plane;
      local economics = routeChoice.economics;
      if (EQUIPMENT_ROI_PROBE) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 1, opcodePadding, economics, "pre_admission_hubsite");
      }
      if (economics == null || economics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) {
          if (economics == null) OpexC73RecordRejection("air", "economics_unavailable", 1);
          else OpexC73RecordRejection("air", "profit_nonpositive", 1);
        }
        if (c78Gen) {
          if (economics == null) {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        continue;
      }
      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub.anchor, site.anchor);
      }
      local plan = {
        siteA = hub, siteB = site, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = routePlane, monthlyPax = monthlyPax, planes = economics.planes,
        capital = economics.capital, economics = economics,
        reuseA = true, hubRoutes = hub.routes, arm = "hubsite",
        c83OwnSecondSlotA = false,
        c83OwnSecondSlotB = ("c83OwnSecondSlot" in site) && site.c83OwnSecondSlot,
      };
      if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);
      if (plan.economics.profitAnnual <= 0) continue;
      if (c78Gen) {
        if (V93_AIR_DEMAND_PRODUCTION) {
          local paxOld = (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1))
              + ((site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100);
          if (paxOld < 10) paxOld = 10;
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
        } else {
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hubsite combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub) + " townB=" + site.town.id + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
        }
      }
      bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
    }
  }
  ctx.bestPlan = bestPlan;
}

/* 6. Arm « hub vers hub » : liaisons directes entre deux aeroports existants. */
function OpexAirPlansHubToHub(ctx, combo, airport, plane)
{
  /* Liaisons Hub-a-Hub directes entre deux aeroports existants (capital = 1 avion seul) */
  local hubs = ctx.hubs;
  local catalog = ctx.catalog;
  local paxBand = ctx.paxBand;
  local abandoned = ctx.abandoned;
  local infrastructureMaintenance = ctx.infrastructureMaintenance;
  local maxCapital = ctx.maxCapital;
  local c78Year = ctx.c78Year;
  local c78Gen = ctx.c78Gen;
  local projects = ctx.projects;
  local lines = ctx.lines;
  local hubIndex = ctx.hubIndex;
  local bestPlan = ctx.bestPlan;
  local targetTownId = ctx.targetTownId;

  local hubAvgIncome = [];
  if (AIR_HUBHUB_MARGINAL) {
    for (local h = 0; h < hubs.len(); h++) hubAvgIncome.append(0.0);
    if (lines != null && hubs.len() > 0) {
      local hubIndexByStation = {};
      for (local h = 0; h < hubs.len(); h++) {
        hubIndexByStation.rawset(hubs[h].stationId, h);
      }
      local hubLinesCount = [];
      local hubLinesIncomeSum = [];
      for (local h = 0; h < hubs.len(); h++) {
        hubLinesCount.append(0);
        hubLinesIncomeSum.append(0.0);
      }
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        if (("deadStreak" in line) && line.deadStreak >= 2) continue;
        local stA = AIR_HUB_FIX ? OpexAirLineStationId(line, 0)
            : (AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA));
        local stB = AIR_HUB_FIX ? OpexAirLineStationId(line, 1)
            : (AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB));
        if (!AIStation.IsValidStation(stA) || !AIStation.IsValidStation(stB)) continue;

        local dist = ("distance" in line && line.distance > 0)
            ? line.distance
            : (AIMap.IsValidTile(line.stationA) && AIMap.IsValidTile(line.stationB)
                ? OpexFlightDistance(line.stationA, line.stationB) : 0);
        if (dist <= 0) continue;
        local days = ("predOneWayDays" in line && line.predOneWayDays > 0) ? line.predOneWayDays : 0;
        local incomeDays = OpexCeilDiv(days, 1);
        if (incomeDays < 1) incomeDays = 1;
        local paxIncome = AICargo.GetCargoIncome(catalog.paxCargo, dist, incomeDays);
        local totalIncomePerUnit = paxIncome;
        if (("mailCargo" in catalog) && catalog.mailCargo >= 0) {
          local mailIncome = AICargo.GetCargoIncome(catalog.mailCargo, dist, incomeDays);
          totalIncomePerUnit = paxIncome + (mailIncome * 15) / 100;
        }
        local incomePerUnit = (totalIncomePerUnit * AIR_PAX_REVENUE_CALIBRATION_PCT) / 100.0;

        if (stA in hubIndexByStation) {
          local h = hubIndexByStation[stA];
          hubLinesCount[h]++;
          hubLinesIncomeSum[h] += incomePerUnit;
        }
        if (stB in hubIndexByStation && stB != stA) {
          local h = hubIndexByStation[stB];
          hubLinesCount[h]++;
          hubLinesIncomeSum[h] += incomePerUnit;
        }
      }
      for (local h = 0; h < hubs.len(); h++) {
        if (hubLinesCount[h] > 0) {
          hubAvgIncome[h] = hubLinesIncomeSum[h] / hubLinesCount[h];
        }
      }
    }
  }

  for (local i = 0; i < hubs.len(); i++) {
    local hub1MonthlyPre = C80_AIR_EVAL_FAST
        ? (((hubs[i].town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hubs[i].routes + 1))
        : 0;
    for (local j = i + 1; j < hubs.len(); j++) {
      local hub1 = hubs[i];
      local hub2 = hubs[j];
      if (targetTownId >= 0
          && hub1.town.id != targetTownId && hub2.town.id != targetTownId) continue;
      if (C69_BOTTLENECK_PROBE) OpexC73RecordExamined("air", 1);
      local st1 = hub1.stationId;
      local st2 = hub2.stationId;
      local alreadyConnected = false;
      if (hubIndex != null) {
        alreadyConnected = (st1 + "|" + st2) in hubIndex.pairs;
      } else
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        /* air_hub_fix : c'est CETTE comparaison qui etait morte -- un StationID (st1/st2, issus
         * de la decouverte de hub) contre une tuile d'aeroport (line.stationA/B). */
        local oA = AIR_HUB_FIX ? OpexAirLineStationId(line, 0)
            : (AIStation.IsValidStation(line.stationA) ? line.stationA : AIStation.GetStationID(line.originA));
        local oB = AIR_HUB_FIX ? OpexAirLineStationId(line, 1)
            : (AIStation.IsValidStation(line.stationB) ? line.stationB : AIStation.GetStationID(line.originB));
        if (!AIStation.IsValidStation(oA) || !AIStation.IsValidStation(oB)) continue;
        if ((oA == st1 && oB == st2) || (oA == st2 && oB == st1)) {
          alreadyConnected = true; break;
        }
      }
      if (alreadyConnected) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "already_connected", 1);
        if (c78Gen) {
          local c78Dist = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + c78Dist + " outcome=already_connected P=-1 C=-1");
        }
        continue;
      }
      local distance = AIMap.DistanceManhattan(hub1.town.tile, hub2.town.tile);
      if (distance < 20) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_short", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=distance_short P=-1 C=-1");
        continue;
      }
      local orderDistance = C80_AIR_EVAL_FAST ? 0 : AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
      local flightDistance = OpexFlightDistance(hub1.anchor, hub2.anchor);
      if (!OpexAirPairInBand(catalog, distance, flightDistance, paxBand)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "pax_band", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=pax_band P=-1 C=-1");
        continue;
      }
      if (AIR_MAX_DISTANCE > 0 && flightDistance > AIR_MAX_DISTANCE) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "distance_long", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=distance_long P=-1 C=-1");
        continue;
      }
      if (plane.maxOrderDistance > 0 && flightDistance > plane.maxOrderDistance) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "max_order_distance", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=max_order_distance P=-1 C=-1");
        continue;
      }
      if (OpexAirPairIsAbandoned(abandoned, hub1, hub2)) {
        if (C69_BOTTLENECK_PROBE) OpexC73RecordRejection("air", "abandoned", 1);
        if (c78Gen) OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=abandoned P=-1 C=-1");
        continue;
      }
      local monthly1 = C80_AIR_EVAL_FAST
          ? hub1MonthlyPre
          : (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1));
      local monthly2 = ((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1);
      local monthlyPax = monthly1 + monthly2;
      local opcodePadding = 0;
      if (OPEX_AIR_PLAN_PAD) opcodePadding = opcodePadding;
      if (monthlyPax < 10) monthlyPax = 10;
      if (V93_AIR_DEMAND_PRODUCTION) {
        monthly1 = OpexAirTownMonthlyPax(hub1.town, hub1.anchor, airport, lines);
        monthly2 = OpexAirTownMonthlyPax(hub2.town, hub2.anchor, airport, lines);
        monthlyPax = monthly1 + monthly2;
      }
      local routeChoice = OpexAirChooseRoutePlane(catalog, airport, plane, flightDistance, monthlyPax,
                                                  infrastructureMaintenance, maxCapital, 0, opcodePadding,
                                                  C80_AIR_CHOICE_MEMO ? ("hh|" + hub1.stationId + "|" + hub2.stationId
                                                      + "|" + airport.type + "|" + plane.id) : null);
      local routePlane = routeChoice.plane;
      local economics = routeChoice.economics;
      if (EQUIPMENT_ROI_PROBE) {
        OpexM3ProbeAirPreAdmission(catalog, airport, routePlane, flightDistance, monthlyPax,
            infrastructureMaintenance, maxCapital, 0, opcodePadding, economics, "pre_admission_hubhub");
      }
      if (AIR_HUBHUB_MARGINAL && economics != null && economics.profitAnnual > 0) {
        /* V86 Variante A : retrancher la perte de revenu annuel des lignes aeriennes existantes.
         * Hypothese : CargoDist etant desactive (DT_MANUAL), les passagers montent dans le premier avion
         * quelle que soit sa destination. La nouvelle ligne hub->hub cannibalise les passagers des lignes
         * existantes des deux hubs. Aucun gain de note de gare (station rating) n'est modelise. */
        local pax1 = (monthlyPax > 0) ? (economics.carried.tofloat() * monthly1) / monthlyPax : 0.0;
        if (pax1 > monthly1) pax1 = monthly1.tofloat();
        local pax2 = (monthlyPax > 0) ? (economics.carried.tofloat() * monthly2) / monthlyPax : 0.0;
        if (pax2 > monthly2) pax2 = monthly2.tofloat();
        local lossAnnual = (12.0 * (pax1 * hubAvgIncome[i] + pax2 * hubAvgIncome[j])).tointeger();
        if (lossAnnual > 0) {
          economics = clone economics;
          economics.profitAnnual -= lossAnnual;
          local totalCapital = economics.capital + economics.immobilise;
          economics.roi = totalCapital > 0 ? (economics.profitAnnual * 1000) / totalCapital : 0;
        }
      }
      if (economics == null || economics.profitAnnual <= 0) {
        if (C69_BOTTLENECK_PROBE) {
          if (economics == null) OpexC73RecordRejection("air", "economics_unavailable", 1);
          else OpexC73RecordRejection("air", "profit_nonpositive", 1);
        }
        if (c78Gen) {
          if (economics == null) {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=economics_unavailable P=-1 C=-1");
          } else {
            OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=profit_nonpositive P=" + economics.profitAnnual + " C=" + economics.capital);
          }
        }
        continue;
      }
      if (C80_AIR_EVAL_FAST) {
        orderDistance = AIOrder.GetOrderDistance(AIVehicle.VT_AIR, hub1.anchor, hub2.anchor);
      }
      local plan = {
        siteA = hub1, siteB = hub2, distance = flightDistance, orderDistance = orderDistance,
        airport = airport, plane = routePlane, monthlyPax = monthlyPax, planes = economics.planes,
        capital = economics.capital, economics = economics,
        reuseA = true, reuseB = true, hubRoutes = hub1.routes + hub2.routes,
        arm = "hubhub",
      };
      if (C84_AIR_TARGET_FLEET && ("targetPlanes" in routeChoice)) {
        plan.targetPlanes <- routeChoice.targetPlanes;
      }
      OpexAirReserveJoinedStops(catalog, plan);
      if (plan.economics.profitAnnual <= 0) continue;
      if (c78Gen) {
        if (V93_AIR_DEMAND_PRODUCTION) {
          local paxOld = (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1))
              + (((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1));
          if (paxOld < 10) paxOld = 10;
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital + " paxNew=" + monthlyPax + " paxOld=" + paxOld);
        } else {
          OpexC78Log("C78_AIRPAIR", "year=" + c78Year + " arm=hub combo=" + airport.type + ":" + plane.id + " townA=" + OpexC78HubTownId(hub1) + " townB=" + OpexC78HubTownId(hub2) + " dist=" + distance + " outcome=admitted P=" + economics.profitAnnual + " C=" + economics.capital);
        }
      }
      bestPlan = OpexAirStoreRoutePlan(projects, plan, routeChoice, bestPlan);
    }
  }
  ctx.bestPlan = bestPlan;
}

/* 7. Finalisation : enregistrement des perf, sondes et nettoyage de la reprise. */
function OpexAirPlansFinalize(ctx)
{
  local servedDiag = ctx.servedDiag;
  local t0_all = ctx.t0_all;
  local l0_all = ctx.l0_all;
  local sliced = ctx.sliced;
  local resumeState = ctx.resumeState;
  local bestPlan = ctx.bestPlan;
  local perfOpsSites = ctx.perfOpsSites;
  local perfOpsEval = ctx.perfOpsEval;
  local perfProbesCount = ctx.perfProbesCount;
  local perfCheapSkip = ctx.perfCheapSkip;
  local perfSitesFound = ctx.perfSitesFound;
  local combos = ctx.combos;
  local projects = ctx.projects;
  local _calcDeltaOps = OpexAirCalcDeltaOps;

  if (DECISION_LOG) {
    OpexDecide("AIR_SERVED_SUMMARY", "scan=" + servedDiag.scan
               + " null_calls=" + servedDiag.nullCalls + " empty_calls=" + servedDiag.emptyCalls
               + " nonempty_calls=" + servedDiag.nonemptyCalls + " true_calls=" + servedDiag.trueCalls
               + " false_calls=" + servedDiag.falseCalls
               + " false_towns_logged=" + servedDiag.loggedFalseCount);
  }
  local totalOps = _calcDeltaOps(t0_all, l0_all);
  local elapsedTicks = AIController.GetTick() - t0_all;
  if (sliced) {
    totalOps += resumeState.totalOps;
    elapsedTicks = AIController.GetTick() - resumeState.startTick;
    resumeState.totalOps = totalOps;
    resumeState.bestPlan = bestPlan;
    resumeState.done = true;
    resumeState.sites = null;
    resumeState.towns = null;
    resumeState.combos = null;
    if (C80_AIR_EVAL_FAST) {
      AIR_ECONOMICS_MEMO = {};
      AIR_TRIP_MEMO = {};
    }
  }
  local elapsedDays = elapsedTicks / 74;
  if (DECISION_LOG) {
    local scanNum = (servedDiag != null && ("scan" in servedDiag)) ? servedDiag.scan : 0;
    OpexDecide("AIR_PLAN_PERF", "scan=" + scanNum + " total_ops=" + totalOps
               + " ops_sites=" + perfOpsSites + " ops_eval=" + perfOpsEval
               + " ticks=" + elapsedTicks + " days=" + elapsedDays
               + " probes=" + perfProbesCount + " cheap_skip=" + perfCheapSkip
               + " sites=" + perfSitesFound
               + " combos=" + combos.len()
               + " plans=" + (projects != null ? projects.len() : (bestPlan != null ? 1 : 0)));
  }
  AILog.Info("AIR_PLAN_PERF: total_ops=" + totalOps + " ops_sites=" + perfOpsSites
             + " ops_eval=" + perfOpsEval + " ticks=" + elapsedTicks + " days=" + elapsedDays
             + " probes=" + perfProbesCount + " cheap_skip=" + perfCheapSkip
             + " sites=" + perfSitesFound);
  OpexSign(AIMap.GetTileIndex(1, 2), "AP|T=" + totalOps + "|S=" + perfOpsSites + "|E=" + perfOpsEval + "|TK=" + elapsedTicks);
  if (C69_BOTTLENECK_PROBE) {
    local actualPlans = (projects != null) ? projects.len() : (bestPlan != null ? 1 : 0);
    OpexC73RecordProduced("air", actualPlans, actualPlans);
  }
  if (C80_AIR_EVAL_FAST && !sliced) {
    AIR_ECONOMICS_MEMO = {};
    AIR_TRIP_MEMO = {};
  }
  return bestPlan;
}

/* Index du prochain combo kind=small apres comboIndex, ou -1. Aucun appel d'API. */
function OpexAirV93NextSmallCombo(combos, comboIndex)
{
  local nextSmall = comboIndex + 1;
  while (nextSmall < combos.len()) {
    local candidate = combos[nextSmall];
    if (("kind" in candidate) && candidate.kind == "small") return nextSmall;
    nextSmall++;
  }
  return -1;
}

/* `abandoned` : table des paires dont une construction a deja echoue (cle
 * canonique OpexAirPairKey), et optionnellement des
 * sites exacts et types ("air_site|airportType|anchor"). null = filtre desactive.
 * Le filtre est place APRES les tests de distance et AVANT OpexAirEconomics : les paires
 * ecartees pour distance ne paient pas la concatenation, et celles qui restent evitent le
 * calcul cher. */
function OpexAirPlans(catalog, lines = null, maxCapital = 0, projects = null, abandoned = null,
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
    hubs = []
  };

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_prepare", "-");
  local prepared = OpexAirPlansPrepare(ctx);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_prepare", "-",
      "combos=" + (ctx.combos != null ? ctx.combos.len() : 0) + " towns=" + (ctx.towns != null ? ctx.towns.len() : 0)
      + " target=" + targetTownId);
  if (!prepared) {
    return ctx.bestPlan;
  }

  for (local comboIndex = ctx.comboStart; comboIndex < ctx.combos.len(); comboIndex++) {
    local combo = ctx.combos[comboIndex];
    local airport = combo.airport;
    local plane = combo.plane;
    local minDist = (plane.speed >= 400) ? 32 : 30;
    local resumingCombo = ctx.sliced && ctx.resumeState.combo == comboIndex && ctx.resumeState.sites != null;

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_find_sites", "-");
    local sitesOk = OpexAirPlansFindSites(ctx, comboIndex, combo, airport, plane, resumingCombo);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_find_sites", "-",
        "combo=" + comboIndex + " sites=" + ctx.sites.len() + " probes=" + ctx.perfProbesCount);
    if (!sitesOk) {
      return ctx.bestPlan;
    }

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_new_pairs", "-");
    local pairsOk = OpexAirPlansNewPairs(ctx, comboIndex, combo, airport, plane, minDist, resumingCombo);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_new_pairs", "-",
        "combo=" + comboIndex + " plans=" + (ctx.projects != null ? ctx.projects.len() : -1));
    if (!pairsOk) {
      return ctx.bestPlan;
    }

    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hubs", "-");
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_discover", "-");
    OpexAirPlansDiscoverHubs(ctx, combo, airport, plane);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_discover", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len());

    local c56PlansBefore = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_site", "-");
    local tHubEval0 = AIController.GetTick();
    local lHubEval0 = AIController.GetOpsTillSuspend();
    OpexAirPlansHubToSite(ctx, combo, airport, plane);
    local c56PlansMid = (ctx.projects != null) ? ctx.projects.len() : 0;
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_site", "-",
        "hubs=" + ctx.hubs.len() + " sites=" + ctx.sites.len() + " admitted=" + (c56PlansMid - c56PlansBefore));
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_hub_to_hub", "-");
    OpexAirPlansHubToHub(ctx, combo, airport, plane);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hub_to_hub", "-",
        "hubs=" + ctx.hubs.len() + " admitted=" + (((ctx.projects != null) ? ctx.projects.len() : 0) - c56PlansMid));
    ctx.perfOpsEval += _calcDeltaOps(tHubEval0, lHubEval0);
    if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_hubs", "-", "hubs=" + ctx.hubs.len());

    if (AIR_HUB && ctx.hubs.len() > 0) {
      OpexSign(AIMap.GetTileIndex(1, 6), "AU|" + ctx.hubs.len() + "|"
               + (ctx.bestPlan != null && ctx.bestPlan.reuseA ? 1 : 0));
    }
    OpexSign(AIMap.GetTileIndex(1, 4), "AE|S=" + ctx.sites.len() + "|B=" + (ctx.bestPlan != null ? ctx.bestPlan.economics.profitAnnual : "NO"));
    if (ctx.sliced) {
      ctx.resumeState.combo = comboIndex + 1;
      ctx.resumeState.a = 0;
      ctx.resumeState.b = 1;
      ctx.resumeState.sites = null;
      ctx.resumeState.scanIndex = 0;
      ctx.resumeState.scanSites = [];
      ctx.resumeState.scanProbes = null;
      ctx.resumeState.rankIndex = 0;
      ctx.resumeState.rankSites = [];
      ctx.resumeState.bestPlan = ctx.bestPlan;
      ctx.resumeState.stationLimitedTowns = ctx.stationLimitedTowns;
      ctx.resumeState.perfOpsSites = ctx.perfOpsSites;
      ctx.resumeState.perfOpsEval = ctx.perfOpsEval;
      ctx.resumeState.perfProbesCount = ctx.perfProbesCount;
      ctx.resumeState.perfCheapSkip = ctx.perfCheapSkip;
      ctx.resumeState.perfSitesFound = ctx.perfSitesFound;
    }
    /* Un plan grand arrete la boucle. Sous V93, les combos petits qui suivent
     * sont quand meme parcourus ; les grands suivants restent sautes. A 0, le
     * booleen provoque le meme break, sans helper ni appel d'API. */
    local bestPlan = ctx.bestPlan;
    if (bestPlan != null && bestPlan.airport.allowBig) {
      if (!V93_AIRPORT_NO_POP_FLOOR) break;
      if (!(("kind" in combo) && combo.kind == "small")) {
        local nextSmall = OpexAirV93NextSmallCombo(ctx.combos, comboIndex);
        if (nextSmall < 0) break;
        if (ctx.sliced) ctx.resumeState.combo = nextSmall;
        comboIndex = nextSmall - 1;
      }
    }
  }

  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_ENTER", "air_finalize", "-");
  local finalPlan = OpexAirPlansFinalize(ctx);
  if (C56_TASK_TRACE) OpexC56TaskLog("STAGE_EXIT", "air_finalize", "-");
  return finalPlan;
}

/* Sondage pur d'un site : rend 0 s'il accepte l'aeroport, sinon le code d'erreur. Ne depense
 * rien et NE LAISSE AUCUNE TRACE dans la comptabilite du caller.
 *
 * ⚠️ Les deux pieges de ce sondage, mesures dans le source de 15.3 :
 *
 * 1. AIAccounting compte AUSSI les commandes jouees en AITestMode --
 *    `if (estimate_only) IncreaseDoCommandCosts(res.GetCost())`, script_object.cpp:299-302.
 *    Un sondage d'aeroport ajoute donc son prix SIMULE au compteur sans qu'une livre sorte :
 *    +35 000 £ par ligne au premier essai du 2026-09-02 (ratio cout/modele 1,02 -> 1,38).
 *    Le bouclier est un AIAccounting IMBRIQUE : son destructeur RESTAURE le total du niveau
 *    superieur (script_accounting.cpp), donc tout ce qui entre dedans est jete.
 *
 * 2. AITestMode lit le terrain REEL. Les 8 echecs mesures sont 7 x ERR_FLAT_LAND_REQUIRED et
 *    1 x ERR_AREA_NOT_CLEAR : sonder avant de niveler rejetterait tous les bons sites.
 *    A n'appeler qu'APRES LevelTiles.
 *
 * CmdBuildAirport appelle CheckIfAuthorityAllowsNewStation en tout premier
 * (station_cmd.cpp:2637), et NoTestTownRating n'est pose que par la generation interne du jeu :
 * le refus municipal remonte donc bien jusqu'ici. */
function OpexAirProbeSite(site, airportType)
{
  local shield = AIAccounting();
  local test = AITestMode();
  local ok = AIAirport.BuildAirport(site.anchor, airportType, AIStation.STATION_NEW);
  local err = ok ? 0 : AIError.GetLastError();
  test = null;
  shield = null;
  return err;
}

/* Le refus municipal est le seul cas rattrapable : on plante alors des arbres -- HORS bouclier,
 * cette depense-la est reelle -- et on resonde. ERR_LOCAL_AUTHORITY_REFUSES couvre AUSSI le
 * plafond de bruit (script_error.hpp), que les arbres ne reparent pas : le second sondage tranche
 * entre les deux au lieu de le deviner. */
function OpexAirSiteRefusal(site, airportType)
{
  local err = OpexAirProbeSite(site, airportType);
  if (err != AIError.ERR_LOCAL_AUTHORITY_REFUSES) return err;
  OpexBoostTownRating(site.town.id, 800, 40);
  return OpexAirProbeSite(site, airportType);
}

function OpexAirRollback(airportA, airportB, planes)
{
  /* La flotte n'est demarree qu'apres tous les clones et ordres valides : elle est donc encore
   * dans le hangar et peut etre vendue avant que ce hangar ne disparaisse. */
  foreach (plane in planes) {
    if (AIVehicle.IsValidVehicle(plane)) AIVehicle.SellVehicle(plane);
  }
  /* G7§1 : l'ancien code ne retirait que airportB. airportA -- toujours passe en premier
   * argument par les appelants quand il est neuf -- n'etait jamais retire, laissant un
   * aeroport orphelin sur la carte apres chaque echec BFAIL/STNFAIL/HANGAR/PLANE/ORDFAIL/START. */
  if (airportB != null && AIAirport.IsAirportTile(airportB)) AIAirport.RemoveAirport(airportB);
  if (airportA != null && AIAirport.IsAirportTile(airportA)) AIAirport.RemoveAirport(airportA);
}

/* C33.2 : Pose d'arrets de bus traversants joints a la gare de l'aeroport (modele AAAHogEx piece stations).
 * Ces arrets etendent l'aire de captage de l'aeroport jusqu'au coeur de la ville hote,
 * captant les passagers directement a l'aeroport sans aucun vehicule routier ni frais de transfert. */
function OpexAirBuildJoinedStops(airportTile, stationId, airport, town, paxCargo)
{
  local summary = { count = 0, monthlyPax = 0 };
  if (!AIR_JOINED_STOPS || !AIStation.IsValidStation(stationId)) return summary;
  local mapX = AIMap.GetMapSizeX();
  local mapY = AIMap.GetMapSizeY();
  local spread = AIGameSettings.GetValue("station.station_spread");
  if (spread < 4) spread = 12;

  local w = airport.width;
  local h = airport.height;
  local ax = AIMap.GetTileX(airportTile);
  local ay = AIMap.GetTileY(airportTile);
  local center = airportTile + AIMap.GetTileIndex(w / 2, h / 2);

  /* Boite permise par station_spread autour de l'emprise de l'aeroport */
  local minX = ax + w - spread;
  if (minX < 1) minX = 1;
  local maxX = ax + spread - 1;
  if (maxX >= mapX - 1) maxX = mapX - 2;

  local minY = ay + h - spread;
  if (minY < 1) minY = 1;
  local maxY = ay + spread - 1;
  if (maxY >= mapY - 1) maxY = mapY - 2;

  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP);
  local airportCoverage = AIStation.GetCoverageRadius(AIStation.STATION_AIRPORT);
  local dirs = [
    AIMap.GetTileIndex(1, 0), AIMap.GetTileIndex(0, 1),
    AIMap.GetTileIndex(-1, 0), AIMap.GetTileIndex(0, -1)
  ];

  local candidates = [];
  for (local x = minX; x <= maxX; x++) {
    for (local y = minY; y <= maxY; y++) {
      local tile = AIMap.GetTileIndex(x, y);
      if (!AIMap.IsValidTile(tile)) continue;
      if (AITile.GetClosestTown(tile) != town.id) continue;
      if (!AIRoad.IsRoadTile(tile)) continue;
      if (AIRoad.IsRoadStationTile(tile) || AIRoad.IsRoadDepotTile(tile) || AITile.IsStationTile(tile)) continue;
      if (AIMap.DistanceManhattan(tile, center) < 3) continue;

      /* C33.2 / G4 : un arret dans la couverture deja assuree par l'emprise aeroport ne
       * rapporte aucune demande marginale. Distance minimale au rectangle de l'aeroport,
       * pas seulement a son coin d'ancrage. */
      local dx = 0;
      if (x < ax) dx = ax - x;
      else if (x >= ax + w) dx = x - (ax + w - 1);
      local dy = 0;
      if (y < ay) dy = ay - y;
      else if (y >= ay + h) dy = y - (ay + h - 1);
      if (dx + dy <= airportCoverage) continue;

      local val = AITile.GetCargoProduction(tile, paxCargo, 1, 1, coverage);
      if (val <= 0) continue;

      foreach (dir in dirs) {
        local front = tile + dir;
        if (!AIMap.IsValidTile(front) || !AIRoad.IsRoadTile(front)) continue;
        local ok = false;
        {
          local test = AITestMode();
          ok = AIRoad.BuildDriveThroughRoadStation(tile, front, AIRoad.ROADVEHTYPE_BUS, stationId);
        }
        if (ok) {
          candidates.append({ tile = tile, front = front, value = val, dist = AIMap.DistanceManhattan(tile, town.tile) });
          break;
        }
      }
    }
  }

  if (candidates.len() == 0) return summary;

  candidates.sort(function(a, b) {
    if (a.value > b.value) return -1;
    if (a.value < b.value) return 1;
    if (a.dist < b.dist) return -1;
    if (a.dist > b.dist) return 1;
    return 0;
  });

  local builtStops = [];
  local maxStops = AIR_JOINED_STOP_LIMIT;
  if (maxStops < 0) maxStops = 0;
  if (maxStops > 2) maxStops = 2;

  foreach (cand in candidates) {
    if (builtStops.len() >= maxStops) break;

    local tooClose = false;
    foreach (prev in builtStops) {
      /* Deux rayons de collecte qui se recouvrent ne sont pas additionnables. */
      if (AIMap.DistanceManhattan(cand.tile, prev) <= 2 * coverage) {
        tooClose = true;
        break;
      }
    }
    if (tooClose) continue;

    local ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, cand.front, AIRoad.ROADVEHTYPE_BUS, stationId);
    if (!ok && AIError.GetLastError() == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
      OpexBoostTownRating(town.id, 800, 40);
      ok = AIRoad.BuildDriveThroughRoadStation(cand.tile, cand.front, AIRoad.ROADVEHTYPE_BUS, stationId);
    }

    if (ok) {
      builtStops.append(cand.tile);
      summary.count++;
      summary.monthlyPax += cand.value;
      if (DECISION_LOG) {
        OpexDecide("AIR_JOINED_STOP", "station=" + stationId + " town=" + town.id + " tile=" + cand.tile + " val=" + cand.value);
      }
    }
  }

  return summary;
}

/* Construit une ligne aerienne complete. Le caller a deja mesure la recherche des sites et
 * verifie le budget monetaire. Rend toujours une table, jamais une exception. */
function OpexBuildAirRoute(catalog, budget, plan, lines = null)
{
  local result = { ok = false, reason = "", opcodes = 0, error = 0, errorText = "", stationA = null,
                   stationB = null, vehicle = null, vehicles = [], actualCost = 0,
                   plannedCapital = (("capital" in plan) ? plan.capital : 0),
                   joinedStopsA = 0, joinedStopsB = 0, joinedMonthlyPax = 0,
                   joinedMonthlyPaxA = 0, joinedMonthlyPaxB = 0,
                   joinedRawMonthlyPax = 0, joinedRawMonthlyPaxA = 0, joinedRawMonthlyPaxB = 0,
                   joinedStopCost = 0 };
  local airportA = null;
  local airportB = null;
  local plane = null;
  local airportErrorA = 0;
  local airportErrorTextA = "";
  local airportErrorB = 0;
  local airportErrorTextB = "";

  local airport = ("airport" in plan) ? plan.airport : catalog.airport;
  local planeChoice = ("plane" in plan) ? plan.plane : catalog.plane;
  local reuseA = ("reuseA" in plan) && plan.reuseA;
  local reuseB = ("reuseB" in plan) && plan.reuseB;

  /* air_cost_probe : le cout REEL de la ligne aerienne, nivellement, aeroports, avions et
   * demolitions de repli compris. Symetrique du `costs` de builder_rail.nut. Le seul
   * AIAccounting imbrique en dessous est le bouclier d'OpexAirProbeSite, et c'est voulu : il
   * jette le cout SIMULE des sondages au lieu de le laisser gonfler ce compteur. */
  local costs = AIAccounting();

  budget.begin();

  if (reuseA) {
    if (AIAirport.IsAirportTile(plan.siteA.anchor) &&
        OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteA.anchor),
                                   planeChoice.planeType)) {
      airportA = plan.siteA.anchor;
    }
  } else {
    OpexAirLevelFootprint(plan.siteA.anchor, airport, plan.siteA.town.id);
    local okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
    if (!okA) {
      local errorA = AIError.GetLastError();
      if (errorA == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
        OpexBoostTownRating(plan.siteA.town.id, 800, 40);
        okA = AIAirport.BuildAirport(plan.siteA.anchor, airport.type, AIStation.STATION_NEW);
        if (!okA) {
          airportErrorA = AIError.GetLastError();
          airportErrorTextA = AIError.GetLastErrorString();
        }
      } else {
        airportErrorA = errorA;
        airportErrorTextA = AIError.GetLastErrorString();
      }
    }
    if (okA && AIAirport.IsAirportTile(plan.siteA.anchor)) airportA = plan.siteA.anchor;
  }
  if (airportA == null) {
    if (!reuseA) {
      OpexAirInvalidateCachedSite(plan.siteA, airport);
      result.error = airportErrorA;
      result.errorText = airportErrorTextA;
    }
    result.opcodes += budget.end("build_airports");
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = reuseA ? "HUB" : "AFAIL";
    return result;
  }

  if (reuseB) {
    if (AIAirport.IsAirportTile(plan.siteB.anchor) &&
        OpexAirAirportAcceptsPlane(AIAirport.GetAirportType(plan.siteB.anchor),
                                   planeChoice.planeType)) {
      airportB = plan.siteB.anchor;
    }
  } else {
    OpexAirLevelFootprint(plan.siteB.anchor, airport, plan.siteB.town.id);
    local okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
    if (!okB) {
      local errorB = AIError.GetLastError();
      if (errorB == AIError.ERR_LOCAL_AUTHORITY_REFUSES) {
        OpexBoostTownRating(plan.siteB.town.id, 800, 40);
        okB = AIAirport.BuildAirport(plan.siteB.anchor, airport.type, AIStation.STATION_NEW);
        if (!okB) {
          airportErrorB = AIError.GetLastError();
          airportErrorTextB = AIError.GetLastErrorString();
        }
      } else {
        airportErrorB = errorB;
        airportErrorTextB = AIError.GetLastErrorString();
      }
    }
    if (okB && AIAirport.IsAirportTile(plan.siteB.anchor)) airportB = plan.siteB.anchor;
  }
  result.opcodes += budget.end("build_airports");
  if (airportB == null) {
    if (!reuseB) {
      OpexAirInvalidateCachedSite(plan.siteB, airport);
      result.error = airportErrorB;
      result.errorText = airportErrorTextB;
    }
    local keepOrphan = (AIGameSettings.GetValue("economy.infrastructure_maintenance") == 0);
    if (!keepOrphan) {
      OpexAirRollback(reuseA ? null : airportA, null, []);
    }
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = reuseB ? "HUBB" : "BFAIL";
    return result;
  }

  local stationA = AIStation.GetStationID(airportA);
  local stationB = AIStation.GetStationID(airportB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) {
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "STNFAIL";
    return result;
  }
  local hangar = AIAirport.GetHangarOfAirport(airportA);
  if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) {
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "HANGAR";
    return result;
  }

  budget.begin();
  plane = AIVehicle.BuildVehicleWithRefit(hangar, planeChoice.id, catalog.paxCargo);
  if (!AIVehicle.IsValidVehicle(plane)) {
    result.error = AIError.GetLastError();
    result.errorText = AIError.GetLastErrorString();
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, []);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "PLANE";
    return result;
  }

  local airFlagsA = (AIR_FULL_LOAD == 1 || AIR_FULL_LOAD == 2) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local airFlagsB = (AIR_FULL_LOAD == 1) ? AIOrder.OF_FULL_LOAD_ANY : AIOrder.OF_NONE;
  local okOrderA = AIOrder.AppendOrder(plane, airportA, airFlagsA);
  local errorA = okOrderA ? 0 : AIError.GetLastError();
  local okOrderB = AIOrder.AppendOrder(plane, airportB, airFlagsB);
  local errorB = okOrderB ? 0 : AIError.GetLastError();
  local ordersOk = okOrderA && okOrderB && AIOrder.GetOrderCount(plane) == 2;
  if (!ordersOk) {
    result.error = !okOrderA ? errorA : errorB;
    result.errorText = AIError.GetLastErrorString();
    result.opcodes += budget.end("build_aircraft");
    OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, [plane]);
    result.actualCost = costs != null ? costs.GetCosts() : 0;
    result.reason = "ORDFAIL";
    return result;
  }
  local built = [plane];
  local wanted = ("planes" in plan) ? plan.planes : 1;
  for (local i = 1; i < wanted; i++) {
    local extra = AIVehicle.CloneVehicle(hangar, plane, true);
    if (!AIVehicle.IsValidVehicle(extra)) {
      local engine = AIVehicle.GetEngineType(plane);
      extra = AIVehicle.BuildVehicleWithRefit(hangar, engine, catalog.paxCargo);
      if (AIVehicle.IsValidVehicle(extra) && !AIOrder.ShareOrders(extra, plane)) {
        result.error = AIError.GetLastError();
        result.errorText = AIError.GetLastErrorString();
        built.append(extra);
        result.opcodes += budget.end("build_aircraft");
        OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built);
        result.actualCost = costs != null ? costs.GetCosts() : 0;
        result.reason = "ORDFAIL";
        return result;
      }
    }
    if (!AIVehicle.IsValidVehicle(extra)) break;
    built.append(extra);
  }
  foreach (aircraft in built) {
    if (!AIVehicle.StartStopVehicle(aircraft)) {
      result.error = AIError.GetLastError();
      result.errorText = AIError.GetLastErrorString();
      result.opcodes += budget.end("build_aircraft");
      OpexAirRollback(reuseA ? null : airportA, reuseB ? null : airportB, built);
      result.actualCost = costs != null ? costs.GetCosts() : 0;
      result.reason = "START";
      return result;
    }
  }
  result.opcodes += budget.end("build_aircraft");

  if (AIR_JOINED_STOPS) {
    local beforeStops = costs != null ? costs.GetCosts() : 0;
    if (!reuseA) {
      local joinedA = OpexAirBuildJoinedStops(airportA, stationA, airport, plan.siteA.town, catalog.paxCargo);
      result.joinedStopsA = joinedA.count;
      result.joinedRawMonthlyPaxA = joinedA.monthlyPax;
      result.joinedRawMonthlyPax += joinedA.monthlyPax;
      result.joinedMonthlyPaxA = OpexAirJoinedMarginalProduction(
          stationA, airportA, airport.type, catalog.paxCargo);
      result.joinedMonthlyPax += result.joinedMonthlyPaxA;
    }
    if (!reuseB) {
      local joinedB = OpexAirBuildJoinedStops(airportB, stationB, airport, plan.siteB.town, catalog.paxCargo);
      result.joinedStopsB = joinedB.count;
      result.joinedRawMonthlyPaxB = joinedB.monthlyPax;
      result.joinedRawMonthlyPax += joinedB.monthlyPax;
      result.joinedMonthlyPaxB = OpexAirJoinedMarginalProduction(
          stationB, airportB, airport.type, catalog.paxCargo);
      result.joinedMonthlyPax += result.joinedMonthlyPaxB;
    }
    local afterStops = costs != null ? costs.GetCosts() : beforeStops;
    result.joinedStopCost = afterStops - beforeStops;
    if (result.joinedStopCost < 0) result.joinedStopCost = 0;
  }

  result.actualCost = costs != null ? costs.GetCosts() : 0;
  result.ok = true;
  result.reason = "OK";
  result.stationA = airportA;
  result.stationB = airportB;
  result.vehicle = plane;
  result.vehicles = built;
  result.capacity <- AIVehicle.GetCapacity(plane, catalog.paxCargo);
  if (V92_AIR_SERVICE_CHOICE && ("mailCargo" in catalog) && catalog.mailCargo >= 0) {
    local builtMail = AIVehicle.GetCapacity(plane, catalog.mailCargo);
    if (builtMail >= 0 && planeChoice != null) AIR_MAIL_CAP.rawset(planeChoice.id, builtMail);
  }
  if (EQUIPMENT_ROI_PROBE) {
    OpexM3EquipmentLog("mode=air phase=post_refit selected=" + planeChoice.id
        + " cargo=" + catalog.paxCargo
        + " selected_refit=" + (planeChoice.defaultCargo != catalog.paxCargo ? 1 : 0)
        + " catalog_capacity=" + planeChoice.capacity + " actual_capacity=" + result.capacity
        + " capacity_delta=" + (result.capacity - planeChoice.capacity));
  }
  result.reusedA <- reuseA;
  if (AIR_CATCHMENT_PROBE) {
    local probeOps = 0;
    probeOps += OpexAirCatchmentProbeEndpoint(catalog, stationA, airportA, plan.siteA.town.id,
                                             result.joinedRawMonthlyPaxA,
                                             result.joinedMonthlyPaxA, reuseA, "A");
    probeOps += OpexAirCatchmentProbeEndpoint(catalog, stationB, airportB, plan.siteB.town.id,
                                             result.joinedRawMonthlyPaxB,
                                             result.joinedMonthlyPaxB, reuseB, "B");
    OpexAirCatchmentLog("AIR_CATCHMENT_BUILD",
        "arm=" + (("arm" in plan) ? plan.arm : "unknown")
        + " base_source=" + (OPEX_AIR_PLAN_PAD ? "demand_plan" : "town_population_proxy")
        + " base_monthly=" + plan.monthlyPax
        + " reserve_stop_cost=" + (("joinedStopReserve" in plan) ? plan.joinedStopReserve : 0)
        + " actual_stop_cost=" + result.joinedStopCost + " stop_limit=" + AIR_JOINED_STOP_LIMIT
        + " stops_a=" + result.joinedStopsA + " stops_b=" + result.joinedStopsB
        + " model_joined_a=" + result.joinedMonthlyPaxA
        + " model_joined_b=" + result.joinedMonthlyPaxB
        + " model_joined_total=" + result.joinedMonthlyPax
        + " raw_joined_a=" + result.joinedRawMonthlyPaxA
        + " raw_joined_b=" + result.joinedRawMonthlyPaxB
        + " raw_joined_total=" + result.joinedRawMonthlyPax
        + " reuse_a=" + (reuseA ? 1 : 0) + " reuse_b=" + (reuseB ? 1 : 0)
        + " planned_capital=" + result.plannedCapital + " actual_cost=" + result.actualCost
        + " probe_ops=" + probeOps);
  }
  if (V93_AIR_DEMAND_PRODUCTION) OpexAirReconcileActualBuild(catalog, plan, result, lines);
  else OpexAirReconcileActualBuild(catalog, plan, result);
  return result;
}

/* V93.1 : memos du mois, meme horloge que C80 (AIR_MEMO_MONTH / AIR_ECONOMICS_MEMO).
 * Les cles v93t| et v93c| ne collisionnent pas avec les cles d'economie. */
function OpexAirDemandTouchMemo()
{
  local nowDate = AIDate.GetCurrentDate();
  if (nowDate == AIR_DEMAND_MEMO_DATE) return;
  AIR_DEMAND_MEMO_DATE = nowDate;
  local month = AIDate.GetYear(nowDate) * 12 + AIDate.GetMonth(nowDate);
  if (AIR_MEMO_MONTH != month) {
    AIR_ECONOMICS_MEMO = {};
    AIR_TRIP_MEMO = {};
    AIR_MEMO_MONTH = month;
  }
}

/* Cargo passagers du catalogue. Repli : premiere classe CC_PASSENGERS, sans identifiant fixe. */
function OpexAirDemandPaxCargo()
{
  if (AIR_DEMAND_PAX_CARGO >= 0) return AIR_DEMAND_PAX_CARGO;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    if (AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) {
      AIR_DEMAND_PAX_CARGO = c;
      return c;
    }
  }
  return -1;
}

function OpexAirDemandTownRecord(town, paxCargo)
{
  local townId = town.id;
  local key = "v93t|" + townId;
  if (key in AIR_ECONOMICS_MEMO) return AIR_ECONOMICS_MEMO[key];
  if (!AITown.IsValidTown(townId)) return null;
  local pop = ("pop" in town) ? town.pop : AITown.GetPopulation(townId);
  local produced = AITown.GetLastMonthProduction(townId, paxCargo);
  if (pop >= 0 && produced > pop) produced = pop / 8;
  if (produced < 0) produced = 0;
  local transported = AITown.GetLastMonthTransportedPercentage(townId, paxCargo);
  if (transported < 0) transported = 0;
  /* AITile.GetCargoProduction compte des tuiles productrices, pas des passagers :
   * on ne s'en sert que comme proportion (tuiles couvertes par l'aeroport / tuiles
   * productrices de la ville), rayon croissant avec la population. */
  local townRadius = 4 + (sqrt(pop > 0 ? pop : 0) / 8).tointeger();
  if (townRadius > 20) townRadius = 20;
  local producerTiles = AITile.GetCargoProduction(AITown.GetLocation(townId), paxCargo, 1, 1, townRadius);
  if (producerTiles < 0) producerTiles = 0;
  local record = { produced = produced, transported = transported, pop = pop, producerTiles = producerTiles };
  AIR_ECONOMICS_MEMO.rawset(key, record);
  return record;
}

/* Lignes aeriennes Opex qui partent de cette ville (origin = centre-ville) ou de cet
 * aeroport (station = tuile d'aeroport). Le compte est stable tant que la liste ne change
 * pas de longueur : la boucle de paires ne la reparcourt pas. */
function OpexAirDemandOwnLines(town, siteAnchor, lines)
{
  if (lines == null) return 0;
  local nLines = lines.len();
  if (AIR_DEMAND_LINE_MEMO_LEN != nLines) {
    AIR_DEMAND_LINE_MEMO = {};
    AIR_DEMAND_LINE_MEMO_LEN = nLines;
  }
  local townId = ("id" in town) ? town.id : -1;
  local anchorKey = siteAnchor == null ? -1 : siteAnchor;
  local cacheKey = townId + "|" + anchorKey;
  if (cacheKey in AIR_DEMAND_LINE_MEMO) return AIR_DEMAND_LINE_MEMO[cacheKey];
  local townTile = ("tile" in town) ? town.tile : -1;
  local n = 0;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "air") continue;
    local hit = false;
    if (townTile >= 0) {
      if (("originA" in line) && line.originA == townTile) hit = true;
      else if (("originB" in line) && line.originB == townTile) hit = true;
    }
    if (!hit && siteAnchor != null) {
      if (("stationA" in line) && line.stationA == siteAnchor) hit = true;
      else if (("stationB" in line) && line.stationB == siteAnchor) hit = true;
    }
    if (hit) n++;
  }
  AIR_DEMAND_LINE_MEMO.rawset(cacheKey, n);
  return n;
}

/* Type reel si l'ancre est deja un aeroport, sinon le type que l'on s'apprete a poser.
 * -1 dans le memo : ancre encore libre, le type vient de l'argument. */
function OpexAirDemandAirportType(siteAnchor, airport)
{
  if (airport == null || !("type" in airport)) return -1;
  if (siteAnchor == null) return airport.type;
  local key = "v93a|" + siteAnchor;
  if (key in AIR_ECONOMICS_MEMO) {
    local cached = AIR_ECONOMICS_MEMO[key];
    if (cached >= 0) return cached;
    return airport.type;
  }
  local resolved = -1;
  if (AIAirport.IsAirportTile(siteAnchor)) {
    local existing = AIAirport.GetAirportType(siteAnchor);
    if (AIAirport.IsValidAirportType(existing)) resolved = existing;
  }
  AIR_ECONOMICS_MEMO.rawset(key, resolved);
  if (resolved >= 0) return resolved;
  return airport.type;
}

/* -1 si l'ancre est inconnue : pas de borne. Sinon le nombre de tuiles productrices
 * du bassin (GetCargoProduction compte des producteurs), en cache par ancre et par
 * type pour le mois. */
function OpexAirDemandCatchment(siteAnchor, airportType, paxCargo)
{
  if (siteAnchor == null || airportType < 0) return -1;
  local key = "v93c|" + siteAnchor + "|" + airportType + "|" + paxCargo;
  if (key in AIR_ECONOMICS_MEMO) return AIR_ECONOMICS_MEMO[key];
  if (!AIMap.IsValidTile(siteAnchor) || !AIAirport.IsValidAirportType(airportType)) return -1;
  local sum = OpexAirAirportCatchmentProduction(siteAnchor, airportType, paxCargo);
  if (sum < 0) sum = 0;
  AIR_ECONOMICS_MEMO.rawset(key, sum);
  return sum;
}

/* Passagers mensuels d'une extremite. Appele pour les deux bouts quand
 * V93_AIR_DEMAND_PRODUCTION est arme. Sans ligne Opex au depart, la part deja
 * transporte est celle des autres : production * 70 / (pourcentage + 70).
 * Avec des lignes, ce pourcentage melange nos avions : on partage seulement
 * la production par (lignes + 1). Le / (lignes + 1) est toujours applique
 * (il vaut 1 tant qu'aucune ligne ne part). Puis part des tuiles productrices captees, puis
 * plafond de ligne (200, ou 100 sous 700 habitants). */
function OpexAirTownMonthlyPax(town, siteAnchor, airport, lines)
{
  if (town == null || !("id" in town)) return 0;
  local paxCargo = OpexAirDemandPaxCargo();
  if (paxCargo < 0) return 0;
  OpexAirDemandTouchMemo();
  local record = OpexAirDemandTownRecord(town, paxCargo);
  if (record == null) return 0;
  local ownLines = OpexAirDemandOwnLines(town, siteAnchor, lines);
  local pax = record.produced;
  if (ownLines == 0) {
    pax = (record.produced * V93_AIR_COMPETITOR_WEIGHT) / (record.transported + V93_AIR_COMPETITOR_WEIGHT);
  }
  pax = pax / (ownLines + 1);
  /* Part de la ville reellement captee par l'emprise : proportion de ses tuiles
   * productrices dans le rayon de l'aeroport (unite commune, tuiles). */
  local catchment = OpexAirDemandCatchment(siteAnchor, OpexAirDemandAirportType(siteAnchor, airport), paxCargo);
  if (catchment >= 0 && record.producerTiles > 0 && catchment < record.producerTiles) {
    pax = (pax * catchment) / record.producerTiles;
  }
  local cap = V93_AIR_LINE_PAX_CAP;
  if (record.pop >= 0 && record.pop < V93_AIR_LINE_PAX_SMALL_POP) cap = V93_AIR_LINE_PAX_CAP / 2;
  if (pax > cap) pax = cap;
  if (pax < 0) pax = 0;
  return pax;
}
