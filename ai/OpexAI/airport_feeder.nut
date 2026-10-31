/* PAX-AIR-FIRST phase 2, prototype BUS reel, opt-in par l'appelant.
 *
 * Ce module n'est pas importe par defaut. Le caller doit fournir un
 * classificateur de constructibilite independant, PAS OpexAirFindSite :
 * null / budget epuise / absence de catchment ne sont pas des preuves.
 *
 * Version volontairement conservative : REUTILISER un arret BUS source,
 * un arret BUS joint a un aeroport et un depot ROUTE deja existants.
 * Aucune station/route/depot n'est construite ou detruite ici. Le seul
 * chantier physique est l'achat d'un bus et la pose de ses deux ordres.
 * Il faut etendre le siting/depot avec des transactions avant d'ouvrir
 * le mecanisme aux villes sans arret ni depot utilisable.
 *
 * Contrat du classificateur classifyTown(townId) : table avec
 * version=1, townId, status="airport_unbuildable", complete=true,
 * unknown=false, checkedTick=GetTick(). Le classificateur autonome
 * OpexAirportFeederTownSlotProof certifie SEULEMENT le plafond municipal
 * de deux aeroports (kind="town_slot_cap"), independamment de la geometrie.
 * Dans tous les autres regimes, il retourne UNKNOWN. Cette version refuse
 * aussi les certificats geometriques externes, meme "complete=true" :
 * l'exhaustivite doit etre implementee et validee separement.
 */
OPEX_AIRPORT_FEEDER_MAX_SPEND <- 120000;
OPEX_AIRPORT_FEEDER_MIN_RESERVE <- 150000;
/* 4 recherches aller/retour (source-hub, depot-source) de 128
 * expansions maximum chacune, 4 voisins au plus par expansion. */
OPEX_AIRPORT_FEEDER_MAX_BFS <- 128;

/* Limite exactement celle du moteur OpenTTD : le plafond 2 est SUPPRIME
 * en mode bruit ou quand le conseil est "permissive" (valeur 3 en 15.3).
 * Valeur absente ou hors plage : pas de preuve. Ce controle du regime ne
 * prouve PAS qu'un aeroport serait constructible en l'absence de plafond. */
function OpexAirportFeederTownSlotRule()
{
  if (!AIGameSettings.IsValid("economy.station_noise_level")
      || !AIGameSettings.IsValid("difficulty.town_council_tolerance"))
    return false;
  local noise = AIGameSettings.GetValue("economy.station_noise_level");
  local council = AIGameSettings.GetValue("difficulty.town_council_tolerance");
  return noise == 0 && council >= 0 && council <= 2;
}

/* O(1), sans sonde, sans mise en cache et sans mutation de carte.
 * Dans le regime "2 slots", AITown.GetAllowedNoise est le nombre
 * de slots restants TOUS exploitants confondus (OpexAirC83SlotSignalEnabled).
 * IMPORTANT : la ville liee au plafond est AITile.GetClosestTown(anchor),
 * pas AIAirport.GetNearestTown(anchor,airportType). Ici townId designe
 * precisement cette ville de quota. Ne pas extrapoler aux villes voisines.
 * checkedTypes=availableTypes=0 exprime "non applicable" pour cette preuve
 * globale, et NE signifie PAS qu'un scan geometrique a ete effectue. */
function OpexAirportFeederTownSlotProof(townId)
{
  local proof = { version = 1, townId = townId, status = "UNKNOWN",
                  complete = false, unknown = true, checkedTick = AIController.GetTick(),
                  kind = "town_slot_cap", reason = "UNKNOWN_RULE",
                  checkedTypes = 0, availableTypes = 0 };
  if (!AITown.IsValidTown(townId)) {
    proof.reason = "INVALID_TOWN";
    return proof;
  }
  if (!OpexAirportFeederTownSlotRule()) return proof;
  local remaining = AITown.GetAllowedNoise(townId);
  if (remaining != 0) {
    proof.reason = "SLOTS_OPEN_OR_INVALID";
    return proof;
  }
  proof.status = "airport_unbuildable";
  proof.complete = true;
  proof.unknown = false;
  proof.reason = "TOWN_TWO_AIRPORT_CAP";
  return proof;
}

/* Aucun resultat UNKNOWN, partiel ni perime. Pour une preuve de slots,
 * re-evaluer le regime et le quota DIRECTEMENT (le callback peut etre
 * mensonger ou avoir calcule avant un changement de regles).
 * Tout autre kind reste bloque, meme avec des comptes de types complets. */
function OpexAirportFeederCertified(townId, classifyTown)
{
  if (!AITown.IsValidTown(townId)) return false;
  if (classifyTown == null) classifyTown = OpexAirportFeederTownSlotProof;
  if (typeof classifyTown != "function") return false;
  local proof = classifyTown(townId);
  if (proof == null || typeof proof != "table") return false;
  if (!("version" in proof) || proof.version != 1
      || !("townId" in proof) || proof.townId != townId
      || !("status" in proof) || proof.status != "airport_unbuildable"
      || !("complete" in proof) || proof.complete != true
      || !("unknown" in proof) || proof.unknown != false
      || !("checkedTick" in proof) || proof.checkedTick != AIController.GetTick())
    return false;
  return ("kind" in proof) && proof.kind == "town_slot_cap"
      && ("checkedTypes" in proof) && proof.checkedTypes == 0
      && ("availableTypes" in proof) && proof.availableTypes == 0
      && OpexAirportFeederTownSlotRule()
      && AITown.GetAllowedNoise(townId) == 0;
}

function OpexAirportFeederEnabled(optIn)
{
  return optIn == true && MODE_AIR && MODE_ROAD && ROAD_BUILD_ENABLED;
}

/* Une route AIR effectivement exploitee doit desservir le StationID exact
 * du hub. Les lignes AIR stockent des tiles (pas des StationID) en A/B. */
function OpexAirportFeederParent(lines, hubId, paxCargo)
{
  if (lines == null || !AIStation.IsValidStation(hubId)) return -1;
  foreach (line in lines) {
    if (line == null || !("mode" in line) || line.mode != "air"
        || !("cargo" in line) || line.cargo != paxCargo) continue;
    local touches = false, hasDifferentAirport = false;
    foreach (field in ["stationA", "stationB"]) {
      if (!(field in line) || line[field] == null
          || !AIMap.IsValidTile(line[field])) continue;
      if (AIStation.GetStationID(line[field]) == hubId) touches = true;
      else if (AIStation.IsValidStation(AIStation.GetStationID(line[field])))
        hasDifferentAirport = true;
    }
    if (!touches || !hasDifferentAirport
        || (("scrapping" in line) && line.scrapping)) continue;
    if (!("vehicles" in line) || line.vehicles == null) continue;
    foreach (plane in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(plane)
          || AIVehicle.GetVehicleType(plane) != AIVehicle.VT_AIR
          || AIVehicle.GetCapacity(plane, paxCargo) <= 0) continue;
      if (!OpexVehicleServesStation(plane, hubId)) continue;
      /* A passenger transfer is useful only with a real outbound leg.
       * A parked/single-stop airplane would accumulate passengers forever. */
      local hasOutbound = false;
      local orderCount = AIOrder.GetOrderCount(plane);
      for (local i = 0; i < orderCount; i++) {
        if (!AIOrder.IsValidVehicleOrder(plane, i)) continue;
        local dest = AIOrder.GetOrderDestination(plane, i);
        if (AIMap.IsValidTile(dest)) {
          local station = AIStation.GetStationID(dest);
          if (AIStation.IsValidStation(station) && station != hubId)
            hasOutbound = true;
        }
      }
      if (!hasOutbound) continue;
      /* BUG/limitation connue : les lignes AIR n'ont pas toujours de
       * lineId persistant. Ne pas inventer un ID (index _lines instable
       * apres Save/Load) : retourner -1 et bloquer le feeder. Le prime
       * devra fournir un identifiant stable avant integration. */
      return ("lineId" in line) && typeof line.lineId == "integer"
          && line.lineId >= 0 ? line.lineId : -1;
    }
  }
  return -1;
}

/* Choisit une facade vraiment connectee, jamais la seule facade declaree
 * par GetRoadStationFrontTile (qui ne prouve pas la connexion). */
function OpexAirportFeederRoadFront(stop)
{
  if (stop == null || !AIMap.IsValidTile(stop)
      || !AIRoad.IsRoadStationTile(stop)) return null;
  local fronts = [AIRoad.GetRoadStationFrontTile(stop)];
  if (AIRoad.IsDriveThroughRoadStationTile(stop))
    fronts.append(AIRoad.GetDriveThroughBackTile(stop));
  foreach (front in fronts) {
    if (front != null && AIMap.IsValidTile(front)
        && AIRoad.AreRoadTilesConnected(stop, front)) return front;
  }
  return null;
}

/* Recherche physique bornee, avec coordonnees de voisinage : contrairement
 * a des offsets GetTileIndex(-1,0), aucune interpolation invalide de tuiles.
 * Le debut/fin peuvent etre arret en baie/depot (non IsRoadTile) ; entre
 * les deux, seules les tuiles de route du roadType voulu sont admissibles.
 * Un appel en sens inverse est necessaire pour verifier le retour reel. */
function OpexAirportFeederRoadReachable(from, to, roadType, maxNodes)
{
  if (from == to) return false;
  local queue = [from];
  local seen = {};
  seen.rawset(from, true);
  local head = 0;
  local expanded = 0;
  local dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < queue.len() && expanded < maxNodes) {
    local tile = queue[head++];
    expanded++;
    local x = AIMap.GetTileX(tile);
    local y = AIMap.GetTileY(tile);
    foreach (d in dirs) {
      local nx = x + d[0];
      local ny = y + d[1];
      if (nx <= 0 || ny <= 0 || nx >= AIMap.GetMapSizeX() - 1
          || ny >= AIMap.GetMapSizeY() - 1) continue;
      local next = AIMap.GetTileIndex(nx, ny);
      if (next in seen) continue;
      if (next != to && (!AIRoad.IsRoadTile(next)
          || !AIRoad.HasRoadType(next, roadType))) continue;
      if (!AIRoad.AreRoadTilesConnected(tile, next)) continue;
      if (next == to) return true;
      seen.rawset(next, true);
      queue.append(next);
    }
  }
  return false;
}

/* Revalidation du plan EXISTANT, sans chantier ni demolition. Quatre BFS
 * exigent source->hub->source et depot->source->depot (128 expans. chacun).
 * plan = {townId, airportTile, sourceStop, hubStop, depot}.
 * On exige un appel explicite optIn=true : defaut OFF strict. */
function OpexAirportFeederValidate(catalog, lines, plan, classifyTown = null, optIn = false)
{
  local out = { ok = false, reason = "DISABLED", parentLine = -1,
                sourceStation = -1, hubStation = -1, engine = null };
  if (!OpexAirportFeederEnabled(optIn)) return out;
  out.reason = "PLAN";
  if (catalog == null || plan == null || typeof plan != "table"
      || !("townId" in plan) || !("airportTile" in plan)
      || !("sourceStop" in plan) || !("hubStop" in plan)
      || !("depot" in plan) || !("roadType" in catalog)
      || !("paxCargo" in catalog) || !("roadEngineByCargo" in catalog)
      || catalog.roadType < 0 || catalog.paxCargo < 0
      || !AITown.IsValidTown(plan.townId)) return out;
  local pax = catalog.paxCargo;
  if (!AICargo.HasCargoClass(pax, AICargo.CC_PASSENGERS)
      || AIRoad.GetRoadVehicleTypeForCargo(pax) != AIRoad.ROADVEHTYPE_BUS
      || !AIRoad.IsRoadTypeAvailable(catalog.roadType)
      || AIRoad.GetRoadTramType(catalog.roadType) != AIRoad.ROADTRAMTYPES_ROAD
      || !(pax in catalog.roadEngineByCargo)) return out;
  local engine = catalog.roadEngineByCargo[pax];
  if (engine == null || !("id" in engine)
      || AIEngine.GetVehicleType(engine.id) != AIVehicle.VT_ROAD
      || !AIEngine.IsBuildable(engine.id)
      || !AIEngine.CanRunOnRoad(engine.id, catalog.roadType)
      || !AIEngine.HasPowerOnRoad(engine.id, catalog.roadType)) return out;
  out.engine = engine;
  AIRoad.SetCurrentRoadType(catalog.roadType);

  if (plan.airportTile == null || plan.sourceStop == null
      || plan.hubStop == null || plan.depot == null
      || !AIMap.IsValidTile(plan.airportTile)
      || !AIMap.IsValidTile(plan.sourceStop)
      || !AIMap.IsValidTile(plan.hubStop)
      || !AIMap.IsValidTile(plan.depot)) return out;
  if (!AIAirport.IsAirportTile(plan.airportTile)
      || !AICompany.IsMine(AITile.GetOwner(plan.airportTile))
      || !AIRoad.IsRoadStationTile(plan.sourceStop)
      || !AIRoad.IsRoadStationTile(plan.hubStop)
      || !AIRoad.IsDriveThroughRoadStationTile(plan.hubStop)
      || !AIRoad.IsRoadDepotTile(plan.depot)
      || !AICompany.IsMine(AITile.GetOwner(plan.sourceStop))
      || !AICompany.IsMine(AITile.GetOwner(plan.hubStop))
      || !AICompany.IsMine(AITile.GetOwner(plan.depot))
      || AITile.GetClosestTown(plan.sourceStop) != plan.townId) return out;
  local hubId = AIStation.GetStationID(plan.airportTile);
  local srcId = AIStation.GetStationID(plan.sourceStop);
  if (!AIStation.IsValidStation(hubId) || !AIStation.IsValidStation(srcId)
      || srcId == hubId || AIStation.GetStationID(plan.hubStop) != hubId) return out;
  /* En NoAI, IsValidBaseStation est restreint aux stations que NOUS
   * possedons ; AIBaseStation.GetOwner n'existe pas (API GameScript).
   * Doubler cette verification par GetOwner sur les tiles reelles. */
  if (!AIBaseStation.IsValidBaseStation(hubId)
      || !AIBaseStation.IsValidBaseStation(srcId)) return out;
  out.sourceStation = srcId;
  out.hubStation = hubId;
  local sourceBusStops = AITileList_StationType(srcId, AIStation.STATION_BUS_STOP);
  local busStops = AITileList_StationType(hubId, AIStation.STATION_BUS_STOP);
  if (!sourceBusStops.HasItem(plan.sourceStop)
      || !busStops.HasItem(plan.hubStop)) return out;
  local parentLine = OpexAirportFeederParent(lines, hubId, pax);
  if (parentLine < 0) { out.reason = "NO_AIR_SERVICE"; return out; }
  out.parentLine = parentLine;
  if (lines != null) {
    foreach (line in lines) {
      if (line == null || !("purpose" in line)
          || line.purpose != "airport_feeder") continue;
      if (("sourceTownId" in line) && line.sourceTownId == plan.townId) {
        out.reason = "DUPLICATE";
        return out;
      }
    }
  }
  if (AITile.GetCargoProduction(plan.sourceStop, pax, 1, 1,
          AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP)) <= 0) {
    out.reason = "NO_PAX";
    return out;
  }
  local srcFront = OpexAirportFeederRoadFront(plan.sourceStop);
  local hubFront = OpexAirportFeederRoadFront(plan.hubStop);
  local depotFront = AIRoad.GetRoadDepotFrontTile(plan.depot);
  if (srcFront == null || hubFront == null || depotFront == null
      || !AIMap.IsValidTile(depotFront)
      || !AIRoad.AreRoadTilesConnected(plan.depot, depotFront)) {
    out.reason = "DISCONNECTED";
    return out;
  }
  local missingLeg = null;
  if (!OpexAirportFeederRoadReachable(plan.sourceStop, plan.hubStop,
          catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS))
    missingLeg = "source_hub";
  else if (!OpexAirportFeederRoadReachable(plan.hubStop, plan.sourceStop,
          catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS))
    missingLeg = "hub_source";
  else if (!OpexAirportFeederRoadReachable(plan.depot, plan.sourceStop,
          catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS))
    missingLeg = "depot_source";
  else if (!OpexAirportFeederRoadReachable(plan.sourceStop, plan.depot,
          catalog.roadType, OPEX_AIRPORT_FEEDER_MAX_BFS))
    missingLeg = "source_depot";
  if (missingLeg != null) {
    if (DECISION_LOG) OpexDecide("AIRPORT_FEEDER_PATH",
        "leg=" + missingLeg + " town=" + plan.townId
        + " source=" + plan.sourceStop + " source_front=" + srcFront
        + " hub=" + plan.hubStop + " hub_front=" + hubFront
        + " depot=" + plan.depot + " depot_front=" + depotFront
        + " max_nodes=" + OPEX_AIRPORT_FEEDER_MAX_BFS);
    out.reason = "NO_ROAD_PATH";
    return out;
  }
  /* Le classificateur tourne EN DERNIER : si la recherche precedente a
   * suspendu le script, seule une preuve du tick courant peut passer. */
  if (!OpexAirportFeederCertified(plan.townId, classifyTown)) {
    out.reason = "UNKNOWN_AIRPORT";
    return out;
  }
  out.ok = true;
  out.reason = "OK";
  return out;
}

/* Transaction : aucune infrastructure n'est modifiee. Un echec revend
 * uniquement le bus neuf (ou demande son retour au depot), et NE FAIT
 * JAMAIS RemoveRoadStation/RemoveRoadDepot/RemoveRoad sur le hub.
 * Le caller doit conserver le ticket PENDING_SELL si le bus a deja quitte
 * le depot ; sinon il reste un vehicule orphelin.
 *
 * Retourne {ok, reason, vehicle, sourceStation, hubStation, parentLine,
 *          actualCost}. Si ok, le caller doit inscrire une ligne
 * purpose="airport_feeder" avec sourceTownId/parentAirLineId dans _lines,
 * puis fournir le refleet avec les MEMES ordres de transfert.
 */
function OpexAirportFeederBuild(catalog, lines, plan, classifyTown = null,
                               optIn = false, maxSpend = 0, cashReserve = -1)
{
  local result = { ok = false, reason = "DISABLED", vehicle = null,
                   sourceStation = -1, hubStation = -1,
                   parentLine = -1, actualCost = 0 };
  if (!OpexAirportFeederEnabled(optIn)) return result;
  if (maxSpend < 0 || maxSpend > OPEX_AIRPORT_FEEDER_MAX_SPEND
      || cashReserve < -1) {
    result.reason = "LIMITS"; return result;
  }
  local cap = maxSpend > 0 && maxSpend <= OPEX_AIRPORT_FEEDER_MAX_SPEND
      ? maxSpend : OPEX_AIRPORT_FEEDER_MAX_SPEND;
  local reserve = cashReserve >= 0 ? cashReserve : OPEX_AIRPORT_FEEDER_MIN_RESERVE;
  local checked = OpexAirportFeederValidate(catalog, lines, plan, classifyTown, optIn);
  if (!checked.ok) { result.reason = checked.reason; return result; }
  result.sourceStation = checked.sourceStation;
  result.hubStation = checked.hubStation;
  result.parentLine = checked.parentLine;
  if (!OpexVehicleSlotAvailable(AIVehicle.VT_ROAD, 1)) {
    result.reason = "NO_SLOT"; return result;
  }
  local price = AIEngine.GetPrice(checked.engine.id);
  local before = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (price <= 0 || price > cap || before - price < reserve) {
    result.reason = "CASH"; return result;
  }
  if (AIVehicle.GetBuildWithRefitCapacity(plan.depot, checked.engine.id, catalog.paxCargo) <= 0) {
    result.reason = "REFIT"; return result;
  }
  local bus = AIVehicle.BuildVehicleWithRefit(plan.depot, checked.engine.id, catalog.paxCargo);
  if (!AIVehicle.IsValidVehicle(bus)) {
    result.reason = "BUILD_BUS"; return result;
  }
  result.vehicle = bus;
  if (("recoveryTicket" in plan) && plan.recoveryTicket != null) {
    plan.recoveryTicket.vehicle = bus;
    plan.recoveryTicket.vehicles = [bus];
    plan.recoveryTicket.recoveryEngine = AIVehicle.GetEngineType(bus);
  }
  result.actualCost = before - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local validBus = AIVehicle.IsStoppedInDepot(bus)
      && AIVehicle.GetVehicleType(bus) == AIVehicle.VT_ROAD
      && AIVehicle.GetCapacity(bus, catalog.paxCargo) > 0
      && AIRoad.RoadVehHasPowerOnRoad(AIVehicle.GetRoadType(bus), catalog.roadType);
  if (validBus && result.actualCost <= cap
      && AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= reserve) {
    local srcFlags = AIOrder.OF_NONE | AIOrder.OF_NON_STOP_INTERMEDIATE;
    local hubFlags = AIOrder.OF_TRANSFER | AIOrder.OF_NO_LOAD
        | AIOrder.OF_NON_STOP_INTERMEDIATE;
    validBus = AIOrder.AreOrderFlagsValid(plan.sourceStop, srcFlags)
        && AIOrder.AreOrderFlagsValid(plan.hubStop, hubFlags)
        && AIOrder.AppendOrder(bus, plan.sourceStop, srcFlags)
        && AIOrder.AppendOrder(bus, plan.hubStop, hubFlags)
        && AIOrder.GetOrderCount(bus) == 2
        && AIStation.GetStationID(AIOrder.GetOrderDestination(bus, 0))
            == result.sourceStation
        && AIStation.GetStationID(AIOrder.GetOrderDestination(bus, 1))
            == result.hubStation
        && (AIOrder.GetOrderFlags(bus, 0) & AIOrder.OF_NO_LOAD) == 0
        && (AIOrder.GetOrderFlags(bus, 1) & AIOrder.OF_TRANSFER) != 0
        && (AIOrder.GetOrderFlags(bus, 1) & AIOrder.OF_NO_LOAD) != 0;
  } else {
    validBus = false;
  }
  if (!validBus || !AIVehicle.StartStopVehicle(bus)) {
    result.reason = "ORDERS_OR_START";
    if (AIVehicle.IsStoppedInDepot(bus) && AIVehicle.SellVehicle(bus))
      result.vehicle = null;
    else {
      AIVehicle.SendVehicleToDepot(bus);
      result.reason = "PENDING_SELL";
    }
    result.actualCost = before - AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (("recoveryTicket" in plan) && plan.recoveryTicket != null) {
      plan.recoveryTicket.vehicle = result.vehicle;
      plan.recoveryTicket.vehicles = result.vehicle != null
          ? [result.vehicle] : [];
      plan.recoveryTicket.recoveryEngine = result.vehicle != null
          ? AIVehicle.GetEngineType(result.vehicle) : -1;
    }
    return result;
  }
  result.ok = true;
  result.reason = "OK";
  return result;
}
