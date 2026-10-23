/* Module AIR extrait de builder_air.nut (R11) : selection des villes, creneaux C83/V95 et hygiene des candidats. */
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

/* Ville debitÃƒÆ’Ã‚Â©e par le moteur pour un aeroport : ClosestTown de l'ancre
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

/* V95 causal : le second slot doit etre encore libre et le premier doit etre
 * detenu par un tiers. Avec station_noise_level=0, slots=1 et zero aeroport
 * Opex sur la ville physique impliquent exactement un aeroport concurrent. */
function OpexAirV95CompetitorSecondSlotOpen(town, anchor = null)
{
  if (!OpexAirC83SlotSignalEnabled() || town == null || !("id" in town)
      || !AITown.IsValidTown(town.id)) return false;
  if (anchor != null && OpexAirSlotTownId(anchor) != town.id) return false;
  if (AITown.GetAllowedNoise(town.id) != 1) return false;
  local ownCounts = OpexAirOwnSlotTownCounts();
  return !(town.id in ownCounts) || ownCounts[town.id] == 0;
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
  foreach (town in towns) {
    if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) continue;
    local pop = AITown.GetPopulation(town.id);
    if (pop < AIR_EARLY_SLOT_MIN_POP) continue;
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

/* ÃƒÂ°Ã…Â¸Ã¢â‚¬ÂÃ‚Â´ Une ligne aerienne stocke des TUILES d'aeroport dans stationA/stationB, malgre leur nom :
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

/* Levier A : calcul du seuil de population pour le quart superieur de la carte (top 25%). */
function OpexTownPopulationTopQuartileThreshold(catalog = null)
{
  local pops = [];
  if (catalog != null && ("towns" in catalog) && catalog.towns != null && catalog.towns.len() > 0) {
    foreach (t in catalog.towns) pops.append(t.pop);
  } else {
    local towns = AITownList();
    for (local t = towns.Begin(); !towns.IsEnd(); t = towns.Next()) {
      pops.append(AITown.GetPopulation(t));
    }
  }
  if (pops.len() == 0) return 0;
  pops.sort();
  return pops[pops.len() * 3 / 4];
}

/* Levier A : nombre d'aeroports rivaux dans une ville. */
function OpexTownRivalAirports(townId, ownCounts = null)
{
  if (!AITown.IsValidTown(townId)) return 0;
  local own = 0;
  if (ownCounts != null && (townId in ownCounts)) own = ownCounts[townId];
  else {
    local counts = OpexAirOwnSlotTownCounts();
    if (townId in counts) own = counts[townId];
  }
  if (OpexAirC83SlotSignalEnabled()) {
    local noise = AITown.GetAllowedNoise(townId);
    local rivals = 2 - noise - own;
    return rivals > 0 ? rivals : 0;
  }
  local me = AICompany.ResolveCompanyID(AICompany.COMPANY_SELF);
  local center = AITown.GetLocation(townId);
  if (!AIMap.IsValidTile(center)) return 0;
  local cx = AIMap.GetTileX(center);
  local cy = AIMap.GetTileY(center);
  local radius = STATION_SEARCH_RADIUS;
  local minX = cx - radius < 1 ? 1 : cx - radius;
  local minY = cy - radius < 1 ? 1 : cy - radius;
  local maxX = cx + radius > AIMap.GetMapSizeX() - 2 ? AIMap.GetMapSizeX() - 2 : cx + radius;
  local maxY = cy + radius > AIMap.GetMapSizeY() - 2 ? AIMap.GetMapSizeY() - 2 : cy + radius;
  local tiles = AITileList();
  tiles.AddRectangle(AIMap.GetTileIndex(minX, minY), AIMap.GetTileIndex(maxX, maxY));
  tiles.Valuate(AITile.IsStationTile);
  tiles.KeepValue(1);
  local rivals = 0;
  local seenStations = {};
  foreach (tile, _ in tiles) {
    local owner = AITile.GetOwner(tile);
    if (owner != me && AICompany.ResolveCompanyID(owner) != AICompany.COMPANY_INVALID && AIAirport.IsAirportTile(tile)) {
      if (AITile.GetClosestTown(tile) == townId) {
        local stId = AIStation.GetStationID(tile);
        if (!(stId in seenStations)) {
          seenStations.rawset(stId, true);
          rivals++;
        }
      }
    }
  }
  return rivals;
}

/* Levier A : verification d'autorisation d'un aeroport dans une ville selon le niveau actif.
 * Niveau 0 : jamais d'aeroport dans une ville ou un concurrent a deja un aeroport.
 * Niveau 1 : ne jamais prendre le dernier creneau d'une ville ou un concurrent est seul
 *            (1 rival, 0 a nous), sauf si la population est dans le quart superieur.
 * Niveaux 2 et 3 : zero opcode de plus (court-circuit en premiere ligne). */
function OpexTownAirportAllowedByLevel(town, ownCounts = null, topPopThreshold = -1, catalog = null)
{
  local allowRivalTown = OpexLevelAllows("airport_rival_town");
  local allowPreemptLast = OpexLevelAllows("preempt_last_airport_slot");
  if (allowRivalTown && allowPreemptLast) return true;

  if (town == null || !("id" in town) || !AITown.IsValidTown(town.id)) return true;

  local rivals = OpexTownRivalAirports(town.id, ownCounts);

  /* Niveau 0 : refus si un rival est present */
  if (!allowRivalTown && rivals > 0) {
    if (DECISION_LOG) {
      OpexDecide("LEVEL_SKIP", "feature=airport_rival_town town=" + town.id + " rivals=" + rivals);
    }
    return false;
  }

  /* Niveau 1 : refus si dernier creneau pris a un rival seul hors quart superieur */
  if (!allowPreemptLast) {
    local own = 0;
    if (ownCounts != null && (town.id in ownCounts)) own = ownCounts[town.id];
    else {
      local counts = OpexAirOwnSlotTownCounts();
      if (town.id in counts) own = counts[town.id];
    }
    if (own == 0 && rivals == 1) {
      local isLastSlot = (AITown.GetAllowedNoise(town.id) == 1);
      if (isLastSlot) {
        local pop = ("pop" in town) ? town.pop : AITown.GetPopulation(town.id);
        if (topPopThreshold < 0) {
          topPopThreshold = OpexTownPopulationTopQuartileThreshold(catalog);
        }
        if (pop < topPopThreshold) {
          if (DECISION_LOG) {
            OpexDecide("LEVEL_SKIP", "feature=preempt_last_airport_slot town=" + town.id + " pop=" + pop + " top_pop=" + topPopThreshold);
          }
          return false;
        }
      }
    }
  }

  return true;
}
