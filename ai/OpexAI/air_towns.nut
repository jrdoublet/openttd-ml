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

/* V126 : trouve l'aeroport Opex impute a la ville et compte ses lignes AIR.
 * Une ville peut avoir plusieurs stations AIR dans des configurations speciales ;
 * le candidat est admissible si au moins un aeroport vivant de cette ville reste
 * sous le plafond de deux routes. */
function OpexAirV126ServedTownState(town, lines)
{
  local state = { eligible = false, stationId = -1, routes = 0, noise = -1 };
  if (!V126_AIR_SERVED_TOWN_REUSE || town == null || !("id" in town)
      || !AITown.IsValidTown(town.id)) return state;

  state.noise = AITown.GetAllowedNoise(town.id);
  if (state.noise < 1) return state;

  local ownAirports = AIStationList(AIStation.STATION_AIRPORT);
  for (local st = ownAirports.Begin(); !ownAirports.IsEnd(); st = ownAirports.Next()) {
    local loc = AIStation.GetLocation(st);
    if (OpexAirSlotTownId(loc) != town.id) continue;
    local routes = 0;
    if (lines != null) {
      foreach (line in lines) {
        if (!("mode" in line) || line.mode != "air") continue;
        local stationA = ("stationA" in line) ? line.stationA : -1;
        local stationB = ("stationB" in line) ? line.stationB : -1;
        if (stationA == st || stationB == st) routes++;
      }
    }
    if (routes < 2) {
      state.eligible = true;
      state.stationId = st;
      state.routes = routes;
      return state;
    }
  }
  return state;
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
