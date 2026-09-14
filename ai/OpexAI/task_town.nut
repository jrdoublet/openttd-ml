/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Une seule route v1 ; le scan apres rechargement empeche tout doublon maritime. */
/* La phase routiere : autant de petites lignes courtes que le classement en propose, dans la
 * limite des deux plafonds annuels ci-dessus.
 *
 * Elle tourne APRES _tryBuild, et c'est une decision, pas un detail d'ordonnancement. Les deux
 * modes ne se disputent jamais la meme PAIRE (leurs bandes de distance sont disjointes : le rail
 * commence ou la route s'arrete, a 25 tuiles) mais ils se disputent les memes ORIGINES et la meme
 * tresorerie. Le rail vaut un ordre de grandeur de plus par ligne : il choisit donc en premier, et
 * la route prend ce qui reste -- des villes et des industries qu'aucune ligne rail n'a retenues,
 * avec l'argent qui dort une fois la reserve rail respectee. C'est aussi ce qui garde la baseline
 * rail lisible au banc : a road_mode = 0 il ne se passe litteralement rien de plus.
 *
 * Le classement est recalcule ICI et non dans le cycle annuel : les lignes rail de l'annee
 * viennent d'entrer dans _lines, et leurs origines doivent etre exclues avant que la route ne
 * choisisse. */
/* Compte le nombre de stations actives de notre compagnie dans une ville donnee. */
function OpexCountTownStations(townId)
{
  local stations = AIStationList(AIStation.STATION_ANY);
  stations.Valuate(AIStation.GetNearestTown);
  stations.KeepValue(townId);
  return stations.Count();
}
/* Liste des villes desservies par au moins une liaison rail, air ou route de notre compagnie. */
function OpexGetServedTowns(lines)
{
  local townMap = {};
  local result = [];
  foreach (line in lines) {
    local stA = AIStation.GetStationID(line.stationA);
    local stB = AIStation.GetStationID(line.stationB);
    if (AIStation.IsValidStation(stA)) {
      local tA = AIStation.GetNearestTown(stA);
      if (tA >= 0 && !(tA in townMap)) {
        townMap.rawset(tA, true);
        result.append(tA);
      }
    }
    if (AIStation.IsValidStation(stB)) {
      local tB = AIStation.GetNearestTown(stB);
      if (tB >= 0 && !(tB in townMap)) {
        townMap.rawset(tB, true);
        result.append(tB);
      }
    }
  }
  return result;
}
/* Tache basse priorite de croissance urbaine : construit au plus une ligne bus de base dans une
 * ville deja desservie. Les quartiers suivants sont proposes au portefeuille comme extensions
 * espacees de cette meme ligne, jusqu'au plafond de croissance maximale OpenTTD. */
function OpexAI::_tryTownGrowth(year)
{
  if (!TOWN_GROWTH_ENABLED || this._catalog.roadType < 0 || this._catalog.paxCargo < 0) return;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < OpexCashReserve() + 25000) return;

  local engine = (this._catalog.paxCargo in this._catalog.roadEngineByCargo)
      ? this._catalog.roadEngineByCargo[this._catalog.paxCargo] : null;
  if (engine == null) return;

  local servedTowns = OpexGetServedTowns(this._lines);
  if (servedTowns.len() == 0) return;

  local anchor = AIMap.GetTileIndex(1, 1);

  foreach (townId in servedTowns) {
    if (!AITown.IsValidTown(townId)) continue;
    /* Une seule ligne bus de base par commune. Le plafond de croissance n'autorise pas cinq
     * lignes superposees : les quartiers suivants deviennent des bus_pax_extension de la ligne. */
    if (OpexTownBusPaxServed(this._lines, townId)) continue;
    local currentCount = OpexCountTownStations(townId);
    if (currentCount >= 5) continue;

    local townTile = AITown.GetLocation(townId);
    local townPop = AITown.GetPopulation(townId);
    if (townPop < 100) continue;

    local cx = AIMap.GetTileX(townTile);
    local cy = AIMap.GetTileY(townTile);
    local srcCenter = townTile;
    local offsets = [[6, 0], [-6, 0], [0, 6], [0, -6], [6, 6], [-6, -6], [8, 0], [0, 8]];
    local dstCenter = null;
    foreach (off in offsets) {
      local tx = cx + off[0];
      local ty = cy + off[1];
      if (OpexRoadInMap(tx, ty)) {
        local t = AIMap.GetTileIndex(tx, ty);
        if (AITile.GetClosestTown(t) == townId && AITile.GetCargoProduction(t, this._catalog.paxCargo, 1, 1, 3) > 0) {
          dstCenter = t;
          break;
        }
      }
    }
    if (dstCenter == null) {
      dstCenter = townTile + AIMap.GetTileIndex(5, 5);
      if (!AIMap.IsValidTile(dstCenter) || AITile.GetClosestTown(dstCenter) != townId) dstCenter = townTile;
    }

    local dist = AIMap.DistanceManhattan(srcCenter, dstCenter);
    if (dist < 4) dist = 5;

    local candidate = {
      src = srcCenter,
      dst = dstCenter,
      srcTown = townId,
      dstTown = townId,
      cargo = this._catalog.paxCargo,
      kind = "pax",
      distance = dist,
      trains = 1,
      engine = engine,
      capital = 2 * this._catalog.costRoadBusStop + 20 * this._catalog.costRoadPerTile + this._catalog.costRoadDepot + engine.price,
      revenueAnnual = 0,
      runningAnnual = 0,
      amortAnnual = 0,
      carried = 0,
      oneWayDays = 1,
      iterations = 0,
      profitAnnual = 0,
      effectiveSpeed = engine.speed,
    };

    this._budget.begin();
    local planning = OpexRoadPlanFor(this._catalog, candidate);
    local planOps = this._budget.end("build_road_plans");
    local plan = planning.plan;
    if (plan == null) {
      if (DECISION_LOG) {
        OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                   + " reason=plan detail=" + planning.reason);
      }
      continue;
    }

    local actualDist = AIMap.DistanceManhattan(plan.stopA.tile, plan.stopB.tile);
    if (actualDist < 1) actualDist = 1;
    candidate.distance = actualDist;
    local routeDist = (plan.routeDistance != null && plan.routeDistance > 0) ? plan.routeDistance : actualDist;
    candidate.capital = 2 * this._catalog.costRoadBusStop + routeDist * this._catalog.costRoadPerTile + this._catalog.costRoadDepot + candidate.engine.price;

    local need = candidate.capital + OpexCashReserve();
    money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need) {
      if (DECISION_LOG) {
        OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                   + " reason=cash need=" + need + " cash=" + money);
      }
      continue;
    }
    /* growth_yields : la croissance urbaine batit des lignes a profitAnnual = 0 et
     * revenueAnnual = 0 EXPLICITES (voir le candidat construit ci-dessus). Son rendement est
     * indirect -- faire grossir la ville pour nourrir les autres lignes -- mais son capital, lui,
     * est bien reel et immediat. Or le goulot mesure de cette IA est la VITESSE DU CAPITAL :
     * 44,5 % de la valeur d'entreprise dort en caisse, et un seul projet est bati par mois
     * (docs/taches.md S0 decies). Cette depense a rendement nul entre donc en concurrence directe
     * avec les projets rentables du portefeuille.
     *
     * Sous 1, la croissance urbaine ne prend que le capital dont le portefeuille NE VEUT PAS :
     * elle exige un surplus au-dela de ce que celui-ci s'est deja engage a depenser
     * (`selectedCapital`). Elle cede donc le pas sans jamais etre supprimee. */
    if (GROWTH_YIELDS && this._projects != null) {
      local committed = ("stats" in this._projects) ? this._projects.stats.selectedCapital : 0;
      if (money < need + committed) {
        if (DECISION_LOG) {
          OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                     + " reason=committed need=" + need + " committed=" + committed
                     + " cash=" + money);
        }
        continue;
      }
    }

    local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
    if (C63_INVEST_PROBE) OpexC63RecordSpendResult("road", result, candidate.capital);
    if (ROAD_COST_PROBE) {
      OpexSign(anchor, "RP|" + townId + "|" + result.plannedCapital + "|" + result.actualCost
                             + "|" + (result.ok ? result.vehicles.len() : 0));
    }
    if (!result.ok) {
      if (DECISION_LOG) {
        OpexDecide("TOWN_GROWTH", "action=fail town=" + townId + " stations=" + currentCount
                   + " reason=build detail=" + result.reason + " error=" + result.error
                   + " dist=" + actualDist);
      }
      continue;
    }

    local newCount = OpexCountTownStations(townId);
    OpexSign(anchor, "TG|" + (year % 100) + "|" + townId + "|" + currentCount + "|" + newCount);
    if (DECISION_LOG) {
      OpexDecide("TOWN_GROWTH", "action=build town=" + townId + " stations_before=" + currentCount + " stations_after=" + newCount + " cost=" + candidate.capital);
    }

    this._lines.append({
      stationA = result.stopA, stationB = result.stopB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = 0, iterations = 0, trains = result.vehicles.len(), distance = dist, year = year,
      predRevenue = 0, predRunning = 0, predAmort = 0, predCarried = 0, predTrains = 1, predOneWayDays = 1,
      /* Batie pour la CROISSANCE de la ville, pas pour son profit : son candidat porte
       * revenueAnnual = 0 EXPLICITE. A exclure nommement d'une comparaison predit/reel, et non
       * devinee par pred_rev == 0 -- 21 a 23 % des enregistrements du diagnostic. */
      purpose = "town_growth",
      effectiveSpeed = engine.speed, catalogSpeed = engine.speed,
      mode = "road", kind = "pax", depot = result.depot,
      srcTown = townId, dstTown = townId, extraStops = [],
      nStopsA = result.nStopsA, nStopsB = result.nStopsB,
      srcIndustry = -1, dstIndustry = -1,
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      isLowRatio = ("isLowRatio" in candidate) ? candidate.isLowRatio : false,
      opcodeRatio = ("opcodeRatio" in candidate) ? candidate.opcodeRatio : -1,
      lineId = this._nextLineId,
    });
    this._nextLineId++;
    break;
  }
}
