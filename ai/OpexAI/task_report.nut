/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Item 7 : au plus UNE tentative rail par an sur une paire que le modele a rejetee
 * (profit predit <= 0). Le classement n'en a jamais vu : stash des moins negatives,
 * hors TOP_K. On ne joint pas, on n'emprunte pas.
 *
 * Budget : alternativeRatio 0, chemin Z, HARD_ITERATION_CAP (40 000). Le premier
 * sondage (results/opex_probe_negative_20y_5seeds.json) passait MIN_RATIO et tombait
 * au plancher 2000 : 48/52 ABND, mediane 123 tuiles. Le volume des rejets est le
 * long ; 2000 ne le mesure pas. 0 n'ajoute aucun parametre a OpexBuildLine, donc
 * le chemin d'opcodes du classement reste intact.
 *
 * Panneaux, tous gates par probe_negative donc absents du defaut :
 *  PQ|aa|stash|close|cash|tried  -- entonnoir annuel
 *  PN|aa|id|profit|dist|R|iter   -- la tentative, profit AU CLASSEMENT (celui du rejet)
 *  PX|id                         -- la ligne batie est un probe, pas un candidat classe
 * Pire PN|99|999|-999999|200|A|40000 : 29 caracteres. */
/* Le releve qui permet de calibrer l'etage 1 : pour chaque ligne, la note de gare REELLE (on
 * suppose STATION_RATING_PCT = 75) et le profit REEL des vehicules (on a predit profitAnnual).
 * C'est exactement la mesure qui manquait a la campagne v3. */
function OpexAI::_reportLines(year)
{
  this._purgeUnprofitableStreaks();
  local anchor = AIMap.GetTileIndex(1, 1);
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    local vehicleType = OpexLineVehicleType(line);
    /* fleet_fix : ce `continue` sautait la ligne AVANT toute mise a jour de deadStreak, vehCount,
     * lastProfit, lastRevenue et lastLiveVehicles. Une gare A devenue invalide (demolie, tuile
     * passee a autrui) gelait donc l'etat de la ligne POUR TOUJOURS : _scrapDeadLines s'appuyant
     * sur deadStreak, la ligne n'etait jamais ferraillee, ses vehicules saignaient leur cout
     * d'exploitation toute la partie, et ses deux extremites continuaient de bloquer _tooClose
     * pour de nouveaux candidats (docs/taches.md S0 nonies). Meme mode d'echec que la ligne OIL_
     * deja documentee plus bas, sur un chemin que ce correctif ne couvrait pas.
     *
     * On compte desormais la gare perdue comme une annee morte : la ligne rejoint le chemin normal
     * de ferraillage au lieu de pourrir en silence. */
    if (!AIStation.IsValidStation(stationA)) {
      if (FLEET_FIX || vehicleType == AIVehicle.VT_AIR) {
        local streak = ("deadStreak" in line) ? line.deadStreak : 0;
        line.deadStreak <- streak + 1;
        if (!("scrapping" in line)) line.scrapping <- false;
        if (!("scrapVehicles" in line)) line.scrapVehicles <- [];
        OpexSign(anchor, "OZ|" + line.lineId + "|" + year + "|SA|" + line.deadStreak);
      }
      continue;
    }

    local ratingA = AIStation.GetCargoRating(stationA, line.cargo);
    local ratingB = AIStation.IsValidStation(stationB)
        ? AIStation.GetCargoRating(stationB, line.cargo) : -1;
    /* line.lineId, pas i : identite stable qui survit a un retrait de _lines par _scrapDeadLines
     * (cf. commentaire sur _nextLineId). Toutes les lignes rail/avion/bateau en ont une. */
    OpexSign(anchor, "OY|" + line.lineId + "|" + year + "|" + ratingA + "|" + ratingB);

    /* Profit reel (deja mesure), plus le detail qui manquait : combien de convois roulent
     * VRAIMENT (vs. le trains predit dans _tryBuild), leur cout de fonctionnement reel, et le
     * revenu reel implicite (profit + cout de fonctionnement, puisque GetProfitLastYear n'est
     * pas decompose par l'API). C'est ce qui permet de departager "note de gare fausse" de
     * "cout de fonctionnement fausse" de "convois manquants" comme cause du 10x. */
    local profit = 0;
    local runCost = 0;
    local vehCount = 0;
    local isFreight = ("kind" in line) && line.kind == "freight";
    local diagSlot = 0;
    /* Une gare jointe possede un seul StationID : AIVehicleList_Station melangerait les lignes.
     * La liste figee a la construction est l'attribution correcte ; le helper ne consulte la gare
     * que pour les etats sauvegardes anterieurs a ce correctif. */
    local vehicles = OpexLineVehicleIds(line, stationA);
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (AIVehicle.GetVehicleType(v) != vehicleType) continue;
      local prof = AIVehicle.GetProfitLastYear(v);
      profit += prof;
      runCost += AIVehicle.GetRunningCost(v);
      vehCount++;
      if (prof >= 0 && this._unprofitableStreaks != null && (v in this._unprofitableStreaks)) {
        delete this._unprofitableStreaks[v];
      }
      /* Diagnostic effondrement fret : etat REEL de CHAQUE convoi (pas juste le premier -- une
       * gare a UNE seule voie, donc un convoi bloque au puits peut faire la queue derriere les
       * autres, qui rendraient "en marche, vitesse 0" sans etre eux-memes la cause). L'ordre
       * courant (0 = source, 1 = puits), l'etat, la vitesse et le chargement du cargo de la
       * ligne. Limite a 3 convois (MAX_TRAINS le permet toujours ici en pratique). */
      if (isFreight && diagSlot < 3) {
        local state = AIVehicle.GetState(v);
        local order = AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT);
        local speed = AIVehicle.GetCurrentSpeed(v);
        local load = AIVehicle.GetCargoLoad(v, line.cargo);
        OpexSign(anchor, "VS|" + line.lineId + "|" + year + "|" + diagSlot + "|" + state + "|" + order);
        OpexSign(anchor, "VL|" + line.lineId + "|" + year + "|" + diagSlot + "|" + speed + "|" + load);
        diagSlot++;
      }
    }
    OpexSign(anchor, "OZ|" + line.lineId + "|" + year + "|" + profit);
    OpexSign(anchor, "OU|" + line.lineId + "|" + year + "|" + vehCount + "|" + runCost);
    /* Collision/crash detector: an owned train that disappears outside the explicit freight
     * scrapping path is never silently ignored. RX is an alarm (loss can also be engine-side),
     * not an unsafe recovery action; no replacement is launched from this path. */
    if (vehicleType == AIVehicle.VT_RAIL) {
      local priorLive = ("lastLiveVehicles" in line) ? line.lastLiveVehicles : vehCount;
      if (!line.scrapping && vehCount < priorLive) {
        local lost = priorLive - vehCount;
        local priorCrashes = ("suspectedCrashes" in line) ? line.suspectedCrashes : 0;
        line.suspectedCrashes <- priorCrashes + lost;
        OpexSign(anchor, "RX|" + (year % 100) + "|" + line.lineId + "|" + lost + "|" + line.suspectedCrashes);
      }
      line.lastLiveVehicles <- vehCount;
    }
    OpexSign(anchor, "OO|" + line.lineId + "|" + year + "|" + (profit + runCost));
    /* Rendement de vitesse (taches S4.3). Instantane annuel des convois EN MARCHE
     * (vitesse > 0, donc pas a quai). med / cat = rendement vs catalogue ; med / pred
     * vs la traction. "RV|99|999|8|999|999|999" = 22 caracteres. Rail seulement. */
    if (vehicleType == AIVehicle.VT_RAIL) {
      local moving = [];
      local catalogs = [];
      foreach (v in vehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;
        if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_RAIL) continue;
        local speed = AIVehicle.GetCurrentSpeed(v);
        if (speed <= 0) continue;
        moving.append(speed);
        catalogs.append(AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v)));
      }
      local pred = ("effectiveSpeed" in line) ? line.effectiveSpeed.tointeger() : 0;
      local cat = 0;
      if (catalogs.len() > 0) cat = OpexMedianInt(catalogs);
      else if (("loco" in line) && line.loco != null && ("speed" in line.loco)) cat = line.loco.speed;
      OpexSign(anchor, "RV|" + (year % 100) + "|" + line.lineId + "|" + moving.len() + "|"
                               + OpexMedianInt(moving) + "|" + pred + "|" + cat);
    }
    /* Rendement route (ROAD_SPEED_EFFICIENCY_PCT = 60, hypothese). Meme instantane que RV.
     * "RY|99|999|P|8|999|999|999" = 24 caracteres. */
    local roadRealSpeed = -1;
    if (vehicleType == AIVehicle.VT_ROAD) {
      local moving = [];
      local catalogs = [];
      foreach (v in vehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;
        if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_ROAD) continue;
        local speed = AIVehicle.GetCurrentSpeed(v);
        if (speed <= 0) continue;
        moving.append(speed);
        catalogs.append(AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v)));
      }
      local pred = ("effectiveSpeed" in line) ? line.effectiveSpeed.tointeger() : 0;
      local cat = 0;
      if (catalogs.len() > 0) cat = OpexMedianInt(catalogs);
      else if ("catalogSpeed" in line) cat = line.catalogSpeed;
      local kindCh = (("kind" in line) && line.kind == "pax") ? "P" : "F";
      if (moving.len() > 0) roadRealSpeed = OpexMedianInt(moving);
      OpexSign(anchor, "RY|" + (year % 100) + "|" + line.lineId + "|" + kindCh + "|"
                               + moving.len() + "|" + (roadRealSpeed >= 0 ? roadRealSpeed : 0) + "|"
                               + pred + "|" + cat);
    }
    /* `<-` : le slot n'existe pas a la construction. `=` leve "the index 'vehCount' does not
     * exist" et tue le script (mesure 2026-08-29, toutes les graines, des 1971). */
    line.vehCount <- vehCount;
    line.lastProfit <- profit;
    line.lastRevenue <- profit + runCost;
    if (C50_CHRONOLOGY_PROBE) {
      local cLabel = AICargo.IsValidCargo(line.cargo) ? AICargo.GetCargoLabel(line.cargo) : "unknown";
      local lMode = ("mode" in line) ? line.mode : "unknown";
      local lAge = ("year" in line) ? (year - line.year) : -1;
      local predProfit = ("predicted" in line) ? line.predicted : 0;
      local lineRoi = ("roi" in line) ? line.roi : 0;
      OpexC50ChronologyLog("phase=line_profit year=" + year + " profit_year=" + (year - 1)
          + " line=" + line.lineId + " mode=" + lMode + " cargo=" + cLabel + " vehs=" + vehCount
          + " profit=" + profit + " run_cost=" + runCost + " rev=" + (profit + runCost)
          + " pred_profit=" + predProfit + " roi=" + lineRoi + " age=" + lAge);
    }
    if (C63_INVEST_PROBE) {
      local lMode = ("mode" in line) ? line.mode : "unknown";
      local lAge = ("year" in line) ? (year - line.year) : -1;
      local predProfit = ("predicted" in line) ? line.predicted : 0;
      local predRev = ("predRevenue" in line) ? line.predRevenue : 0;
      OpexC63RecordLine(lMode, lAge, predProfit, profit, predRev, profit + runCost,
                        vehCount, line.lineId, year - 1);
    }
    if (DECISION_LOG) {
      local realRevenue = profit + runCost;
      local predRevenue = ("predRevenue" in line) ? line.predRevenue : 0;
      local predProfit = ("predicted" in line) ? line.predicted : 0;
      local predRunning = ("predRunning" in line) ? line.predRunning : 0;
      local isLow = ("isLowRatio" in line && line.isLowRatio) ? 1 : 0;
      local opRatio = ("opcodeRatio" in line) ? line.opcodeRatio : -1;
      local lMode = ("mode" in line) ? line.mode : "unknown";
      local lKind = ("kind" in line) ? line.kind : "unknown";
      local lAge = ("year" in line) ? (year - line.year) : -1;
      local lPurpose = ("purpose" in line) ? line.purpose : "profit";
      local cLabel = AICargo.GetCargoLabel(line.cargo);
      local extra = "";
      if (lMode == "road") {
        local rawVehs = ("predVehiclesForVolume" in line) ? line.predVehiclesForVolume
                      : (("predTrains" in line) ? line.predTrains : 0);
        local predBerthCap = ("predRoadBerthCapacity" in line) ? line.predRoadBerthCapacity
                          : OpexRoadPhysicalVehicleCap(1, 1);
        local predVehicleCap = ("predRoadVehicleCap" in line) ? line.predRoadVehicleCap
                            : (("predTrains" in line) ? line.predTrains : predBerthCap);
        local predVehs = ("predTrains" in line) ? line.predTrains : 0;
        local predCarried = ("predCarried" in line) ? line.predCarried : 0;
        local predDays = ("predOneWayDays" in line) ? line.predOneWayDays : 0;
        local predDist = ("distance" in line) ? line.distance : 0;
        local predSpeed = ("effectiveSpeed" in line) ? line.effectiveSpeed.tointeger() : 0;
        local catSpeed = ("catalogSpeed" in line) ? line.catalogSpeed : 0;
        local realDist = (AIStation.IsValidStation(stationA) && AIStation.IsValidStation(stationB))
            ? AIMap.DistanceManhattan(AIStation.GetLocation(stationA), AIStation.GetLocation(stationB)) : predDist;
        local townA = ("originA" in line) ? AITile.GetClosestTown(line.originA) : -1;
        local townB = ("originB" in line) ? AITile.GetClosestTown(line.originB) : -1;
        local popA = AITown.IsValidTown(townA) ? AITown.GetPopulation(townA) : -1;
        local popB = AITown.IsValidTown(townB) ? AITown.GetPopulation(townB) : -1;
        local prodA = AITown.IsValidTown(townA) ? AITown.GetLastMonthProduction(townA, line.cargo) : -1;
        local prodB = AITown.IsValidTown(townB) ? AITown.GetLastMonthProduction(townB, line.cargo) : -1;
        local waitA = AIStation.IsValidStation(stationA) ? AIStation.GetCargoWaiting(stationA, line.cargo) : -1;
        local waitB = AIStation.IsValidStation(stationB) ? AIStation.GetCargoWaiting(stationB, line.cargo) : -1;
        local cap = ("capacity" in line) ? line.capacity : -1;
        local nStopsA = ("nStopsA" in line) ? line.nStopsA : 1;
        local nStopsB = ("nStopsB" in line) ? line.nStopsB : 1;
        local berthCap = OpexRoadPhysicalVehicleCap(nStopsA, nStopsB);
        local vehicleCap = C50B_ROAD_CAP_RELAX ? MAX_ROAD_VEHICLES
            : OpexRoadFleetVehicleCap(nStopsA, nStopsB, predDays, lKind);
        local extraStops = ("extraStops" in line && line.extraStops != null) ? line.extraStops.len() : 0;
        extra = " raw_vehs=" + rawVehs + " pred_berth_cap=" + predBerthCap
              + " pred_vehicle_cap=" + predVehicleCap + " berth_cap=" + berthCap
              + " vehicle_cap=" + vehicleCap
              + " pred_vehs=" + predVehs + " n_stops_a=" + nStopsA + " n_stops_b=" + nStopsB
              + " extra_stops=" + extraStops + " dist=" + predDist + " real_dist=" + realDist
              + " pred_carried=" + predCarried + " pred_days=" + predDays + " pred_speed=" + predSpeed
              + " cat_speed=" + catSpeed + " real_speed=" + roadRealSpeed + " rating_a=" + ratingA
              + " rating_b=" + ratingB + " pop_a=" + popA + " pop_b=" + popB + " prod_a=" + prodA
              + " prod_b=" + prodB + " wait_a=" + waitA + " wait_b=" + waitB + " cap=" + cap;
      }
      OpexDecide("LINE_REVENUE", "line=" + line.lineId + " mode=" + lMode + " kind=" + lKind + " cargo=" + cLabel + " year=" + year + " age=" + lAge + " pred_rev=" + predRevenue + " real_rev=" + realRevenue + " pred_prof=" + predProfit + " real_prof=" + profit + " pred_run=" + predRunning + " real_run=" + runCost + " vehs=" + vehCount + " low_ratio=" + isLow + " op_ratio=" + opRatio + " purpose=" + lPurpose + extra);
    }
    if (vehicleType == AIVehicle.VT_RAIL || vehicleType == AIVehicle.VT_AIR) {
      /* Instantane de backlog, complete par l'utilisation annuelle derivee du revenu dans
       * _expandRailLines. Le second signal evite que la phase du train au jour du releve fasse
       * disparaitre une saturation reelle ; deux annees consecutives restent obligatoires. */
      line.lastWaitingA <- AIStation.GetCargoWaiting(stationA, line.cargo);
      line.lastWaitingB <- AIStation.IsValidStation(stationB)
          ? AIStation.GetCargoWaiting(stationB, line.cargo) : 0;
      if (vehicleType == AIVehicle.VT_AIR) {
        OpexSign(anchor, "FA|" + (year % 100) + "|" + line.lineId + "|"
                         + line.lastWaitingA + "|" + line.lastWaitingB);
      }
    }

    /* Les deux industries sont-elles encore valides ? Et l'industrie source produit-elle encore ?
     * Depart le blocage "train coince" (hypothese 2) de la fermeture d'industrie (hypothese 1). */
    if (isFreight) {
      local srcAlive = AIIndustry.IsValidIndustry(line.srcIndustry) ? 1 : 0;
      local dstAlive = AIIndustry.IsValidIndustry(line.dstIndustry) ? 1 : 0;
      local srcProd = srcAlive ? AIIndustry.GetLastMonthProduction(line.srcIndustry, line.cargo) : -1;
      OpexSign(anchor, "IA|" + line.lineId + "|" + year + "|" + srcAlive + "|" + dstAlive + "|" + srcProd);

      /* Detection ligne morte : srcAlive=0 seul ne suffit PAS (cf. commentaire DEAD_STREAK_THRESHOLD
       * -- une gare peut recuperer une industrie voisine). srcSuffering couvre aussi l'industrie
       * encore ouverte mais a production nulle, meme consequence pour la ligne qu'une fermeture.
       * collapsed exige EN PLUS la preuve REELLE, mesuree ici meme : note de gare a -1 (aucun
       * cargo jamais vu) ET revenu implicite (profit + cout de fonctionnement) nul ou negatif,
       * c'est-a-dire rien transporte du tout cette annee. deadStreak ne compte que les annees
       * CONSECUTIVES ou les trois tiennent ensemble ; un seul manque et le compteur retombe a 0. */
      /* 🔴 CORRIGE LE 2026-08-29. La condition exigeait AUSSI ratingA <= 0, et cette clause etait
       * fausse : une gare CONSERVE sa derniere note quand plus rien n'y passe. Mesure, campagne
       * 20 ans graine 42 : la ligne routiere OIL_ a perdu son industrie source en 1979 et a roule
       * ONZE ANS a -842 par an sans jamais etre mise au rebut, note de gare figee a 67 tout du
       * long. Le revenu implicite (profit + cout de fonctionnement) suffit et ne ment pas : a zero,
       * la ligne n'a rien transporte de l'annee, quelle que soit la note affichee. La prudence
       * reste assuree par les deux autres conditions -- l'industrie source en souffrance, et
       * DEAD_STREAK_THRESHOLD annees CONSECUTIVES.
       * ⚠️ Comme le renouvellement automatique, ce correctif touche AUSSI les lignes rail. */
      local srcSuffering = (!srcAlive) || (srcProd == 0);
      local collapsed = srcSuffering && (profit + runCost) <= 0;
      line.deadStreak = collapsed ? line.deadStreak + 1 : 0;
      if (line.deadStreak > 0) {
        OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + line.deadStreak);
      }
    } else if (vehicleType == AIVehicle.VT_AIR) {
      /* G10 : une ligne air n'a pas de signal industrie. Son bilan annuel est donc la mesure
       * directe de sa viabilite. Deux pertes consecutives, comme le seuil fret, evitent de
       * vendre un appareil sur une seule annee de mise en route ou de fluctuation du trafic. */
      local priorStreak = ("deadStreak" in line) ? line.deadStreak : 0;
      local nextStreak = profit < 0 ? priorStreak + 1 : 0;
      if ("deadStreak" in line) line.deadStreak = nextStreak;
      else line.deadStreak <- nextStreak;
      if (!("scrapping" in line)) line.scrapping <- false;
      if (!("scrapVehicles" in line)) line.scrapVehicles <- [];
      if (nextStreak > 0) OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + nextStreak);
    }
  }
  if (C50_CHRONOLOGY_PROBE) {
    local sumProf = 0;
    local sumRev = 0;
    local profCount = 0;
    local lossCount = 0;
    foreach (l in this._lines) {
      local p = ("lastProfit" in l) ? l.lastProfit : 0;
      local r = ("lastRevenue" in l) ? l.lastRevenue : 0;
      sumProf += p;
      sumRev += r;
      if (p >= 0) profCount++;
      else lossCount++;
    }
    OpexC50ChronologyLog("phase=line_profit_summary year=" + year + " profit_year=" + (year - 1)
        + " lines=" + this._lines.len()
        + " prof_sum=" + sumProf + " rev_sum=" + sumRev
        + " prof_lines=" + profCount + " loss_lines=" + lossCount);
  }
}
/* Remediation ligne morte (2026-08-28) : une fois deadStreak >= DEAD_STREAK_THRESHOLD confirme
 * par _reportLines, on arrete l'hemorragie de cout de fonctionnement en vendant les convois --
 * mais AIVehicle.SellVehicle exige un convoi a l'arret DANS un depot (verifie sur la doc API
 * ai-api/classAIVehicle.html le 2026-08-28 : precondition "the vehicle must be stopped in the
 * depot", exception ERR_VEHICLE_NOT_IN_DEPOT sinon). La vente est donc etalee sur plusieurs
 * annees, au meme rythme annuel que le reste du cycle : l'annee ou le seuil est franchi on
 * envoie chaque convoi au depot (SendVehicleToDepot) et on fige la liste de leurs IDs sur la
 * ligne (scrapVehicles), depuis la liste vehicles posee par cette ligne -- PAS une interrogation
 * par gare qui prendrait les convois du voisin sur un StationID partage. Les annees suivantes, on
 * verifie IsStoppedInDepot() sur cette liste figee
 * et on vend (SellVehicle) ce qui est arrive ; quand elle est vide, la ligne est retiree de
 * _lines -- ce qui l'arrete d'etre rapportee chaque annee ET libere stationA/stationB/originA/
 * originB du filet _tooClose, pour qu'une ligne neuve et proche ne soit plus bloquee par un
 * cadavre. Les gares et voies physiques ne sont PAS demolies : une fois hors de _lines elles ne
 * bloquent plus rien (le seul frein etait la presence dans _lines), et demolir ajoute un risque
 * (note d'autorite locale, infrastructure partagee) pour un gain nul ici. */

function OpexAI::_triggerScrapLine(line, criterion)
{
  if (("scrapping" in line) && line.scrapping) return;
  line.scrapping = true;
  line.deadStreak = DEAD_STREAK_THRESHOLD;
  local anchor = AIMap.GetTileIndex(1, 1);
  local year = AIDate.GetYear(AIDate.GetCurrentDate());
  /* B8 : chaque NOUVEAU cycle de rebut repart de son annee propre. Cela ecrase aussi un champ
   * stale provenant d'une ancienne sauvegarde/reprise avant le correctif. */
  if ("scrapStartYear" in line) line.scrapStartYear = year;
  else line.scrapStartYear <- year;
  local ids = [];
  local vehicleType = OpexLineVehicleType(line);
  /* Les lignes air gardent leurs IDs de flotte. Meme si l'aeroport A est invalide, les avions
   * doivent rejoindre un hangar et etre vendus ; une liste par gare serait alors vide et
   * retirerait seulement la ligne logique en laissant les couts d'exploitation actifs. */
  local stationA = AIStation.GetStationID(line.stationA);
  local vehicles = ("vehicles" in line) ? line.vehicles
      : (AIStation.IsValidStation(stationA) ? OpexLineVehicleIds(line, stationA) : []);
  foreach (v in vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    if (AIVehicle.GetVehicleType(v) != vehicleType) continue;
    AIVehicle.SendVehicleToDepot(v);
    ids.append(v);
    if (EVENT_DEPOT_SELL && this._vehiclesToScrap != null) {
      this._vehiclesToScrap.rawset(v, line.lineId);
    }
  }
  line.scrapVehicles = ids;
  if (DECISION_LOG) {
    local m = ("mode" in line) ? line.mode : "unknown";
    OpexDecide("SCRAP_LINE", "action=start line=" + line.lineId + " mode=" + m
               + " dead_streak=" + line.deadStreak + " threshold=" + DEAD_STREAK_THRESHOLD
               + " vehicles=" + ids.len() + " criterion=" + criterion
               + " start_year=" + line.scrapStartYear);
  }
  local signCode = (criterion == "industry_close") ? "C" : "2";
  OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + signCode);
}
function OpexAI::_scrapDeadLines(year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local toRemove = [];

  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("deadStreak" in line)) continue;

    /* Recuperation des feeders marques pour ferraillage par l'ancien traitement generique
     * VehicleUnprofitable. Les arrets et le depot existent encore : ne pas vendre le dernier
     * vehicule d'une ligne de rabattement valide. Cette branche sert aussi aux sauvegardes
     * deja touchees avant le correctif 2026-09-15. */
    local isFeederLine =
        ((("isFeeder" in line) && line.isFeeder) ||
         (("purpose" in line) && (line.purpose == "feeder" || line.purpose == "feeder_mail")));
    if (isFeederLine) {
      local stationA = ("stationA" in line) ? AIStation.GetStationID(line.stationA) : AIStation.STATION_INVALID;
      local stationB = ("stationB" in line) ? AIStation.GetStationID(line.stationB) : AIStation.STATION_INVALID;
      local infrastructureValid = AIStation.IsValidStation(stationA)
          && AIStation.IsValidStation(stationB)
          && ("depot" in line) && AIRoad.IsRoadDepotTile(line.depot);
      if (infrastructureValid) {
        if (("scrapVehicles" in line) && line.scrapVehicles != null) {
          foreach (v in line.scrapVehicles) {
            if (this._vehiclesToScrap != null && (v in this._vehiclesToScrap)) delete this._vehiclesToScrap[v];
            if (this._vehiclesToRetire != null && (v in this._vehiclesToRetire)) delete this._vehiclesToRetire[v];
            if (this._unprofitableStreaks != null && (v in this._unprofitableStreaks)) delete this._unprofitableStreaks[v];
            if (AIVehicle.IsValidVehicle(v) && AIVehicle.IsStoppedInDepot(v)) {
              AIVehicle.StartStopVehicle(v);
            }
          }
        }
        line.deadStreak = 0;
        if ("scrapping" in line) line.scrapping = false;
        else line.scrapping <- false;
        if ("scrapVehicles" in line) line.scrapVehicles = [];
        else line.scrapVehicles <- [];
        /* Un feeder sauve redevient une ligne normale. Garder l'ancien timer ferait qu'un futur
         * rebut, parfois plusieurs annees plus tard, serait immediatement considere timeout. */
        if ("scrapStartYear" in line) delete line.scrapStartYear;
        if (DECISION_LOG) {
          OpexDecide("FEEDER_RECOVER", "line=" + line.lineId
                     + " action=cancel_scrap scrap_timer_reset=1");
        }
        continue;
      }
    }

    if (!line.scrapping && line.deadStreak >= DEAD_STREAK_THRESHOLD) {
      this._triggerScrapLine(line, "dead_streak");
    }

    if (line.scrapping) {
      if (EVENT_DEPOT_SELL && this._vehiclesToScrap != null && ("scrapVehicles" in line)) {
        foreach (v in line.scrapVehicles) {
          if (AIVehicle.IsValidVehicle(v) && !(v in this._vehiclesToScrap)) {
            this._vehiclesToScrap.rawset(v, line.lineId);
          }
        }
      }
      local remaining = [];
      foreach (v in line.scrapVehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;  // deja vendu ou detruit
        if (AIVehicle.IsStoppedInDepot(v)) {
          AIVehicle.SellVehicle(v);
          if (this._vehiclesToScrap != null && (v in this._vehiclesToScrap)) {
            delete this._vehiclesToScrap[v];
          }
          if (this._unprofitableStreaks != null && (v in this._unprofitableStreaks)) {
            delete this._unprofitableStreaks[v];
          }
          if (DECISION_LOG) {
            OpexDecide("SCRAP_LINE", "action=sell_vehicle line=" + line.lineId + " vehicle=" + v);
          }
        } else {
          remaining.append(v);
        }
      }
      line.scrapVehicles = remaining;
      /* Sortie de secours du ferraillage. Sans elle, la SEULE sortie etait `remaining.len() == 0` :
       * un vehicule qui ne peut plus atteindre un depot -- depot detruit, route coupee, convoi
       * bloque -- figeait la ligne DEFINITIVEMENT. Elle restait alors dans _lines, re-scannee
       * chaque annee, payant son cout d'exploitation, et ses deux extremites continuaient de
       * bloquer _tooClose pour de nouveaux candidats : exactement l'interblocage que le retrait
       * est cense empecher (docs/taches.md S0 nonies).
       *
       * On borne donc la phase en ANNEES. Les vehicules encore vivants sont abandonnes en l'etat
       * plutot que de garder la ligne en vie : ils continueront a rouler, mais la ligne libere ses
       * origines et cesse d'etre re-scannee. Panneau DL|...|4 pour distinguer cette sortie de la
       * sortie propre DL|...|3. */
      if (!("scrapStartYear" in line)) line.scrapStartYear <- year;
      local stuck = (year - line.scrapStartYear) >= SCRAP_TIMEOUT_YEARS;
      if (remaining.len() == 0 || stuck) {
        if (this._vehiclesToScrap != null) {
          foreach (v in remaining) {
            if (v in this._vehiclesToScrap) delete this._vehiclesToScrap[v];
          }
        }
        if (this._unprofitableStreaks != null) {
          foreach (v in line.scrapVehicles) {
            if (v in this._unprofitableStreaks) delete this._unprofitableStreaks[v];
          }
        }
        toRemove.append(i);  // i = position physique dans _lines, pour le retrait -- pas le sign
        if (DECISION_LOG) {
          local crit = (remaining.len() == 0) ? "all_sold" : "timeout";
          local elapsed = ("scrapStartYear" in line) ? year - line.scrapStartYear : -1;
          OpexDecide("SCRAP_LINE", "action=removed line=" + line.lineId + " criterion=" + crit
                     + " remaining=" + remaining.len()
                     + " start_year=" + (("scrapStartYear" in line) ? line.scrapStartYear : -1)
                     + " elapsed=" + elapsed);
        }
        OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + (remaining.len() == 0 ? "3" : "4"));
      }
    }
  }

  /* Retrait du plus grand indice au plus petit pour ne jamais invalider un indice pas encore
   * traite dans toRemove. */
  for (local k = toRemove.len() - 1; k >= 0; k--) {
    this._lines.remove(toRemove[k]);
  }
}
/* Vente autonome des retraites unitaires C52. Contrairement a la mise au rebut
 * d'une ligne, la ligne reste exploitee : cette file ne touche ni scrapping ni
 * ses gares. Elle est deliberement independante de EVENT_DEPOT_SELL, qui ne
 * sert qu'a accelerer la vente au moment de l'evenement depot. */
function OpexAI::_scrapRetiredVehicles(year)
{
  if (this._vehiclesToRetire == null) return;
  local now = AIDate.GetCurrentDate();
  local removeTickets = [];
  local clearStreaks = [];
  local upgradeTickets = [];
  foreach (vehicle, savedTicket in this._vehiclesToRetire) {
    /* Compatibilite : les premieres sauvegardes portent simplement lineId (int).
     * Les tickets recents ajoutent le calendrier de relance sans invalider ces etats. */
    local ticket = null;
    if (typeof savedTicket == "table") ticket = savedTicket;
    else {
      ticket = { lineId = savedTicket, startedDate = now, lastSendDate = now, attempts = 0 };
      upgradeTickets.append({ vehicle = vehicle, ticket = ticket });
    }
    local lineId = ("lineId" in ticket) ? ticket.lineId : -1;
    if (!AIVehicle.IsValidVehicle(vehicle)) {
      removeTickets.append(vehicle);
      clearStreaks.append(vehicle);
      continue;
    }
    local started = ("startedDate" in ticket) ? ticket.startedDate : now;
    if (AIVehicle.IsStoppedInDepot(vehicle)) {
      if (AIVehicle.SellVehicle(vehicle)) {
        removeTickets.append(vehicle);
        clearStreaks.append(vehicle);
        if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
          OpexDecide("UNPROFITABLE_RETIRE", "action=sell vehicle=" + vehicle + " line=" + lineId);
        }
        continue;
      }
      /* Si la vente echoue durablement meme au depot, laisser tomber dans le
       * chemin timeout ci-dessous plutot que garder un ticket a vie. */
      if (now - started < SCRAP_TIMEOUT_YEARS * 365) continue;
    }

    if (now - started >= SCRAP_TIMEOUT_YEARS * 365) {
      /* Ne jamais laisser une retraite impossible rendre l'inventaire permanent
       * mensonger. On annule le retrait, remet le vehicule dans l'inventaire de
       * la ligne et le redemarre s'il attend finalement au depot. */
      local line = this._findLineById(lineId);
      if (line != null) {
        if (("mode" in line) && line.mode != "road") {
          if (!("vehicles" in line)) line.vehicles <- [];
          else if (line.vehicles == null) line.vehicles = [];
          local known = false;
          foreach (existing in line.vehicles) {
            if (existing == vehicle) { known = true; break; }
          }
          if (!known) line.vehicles.append(vehicle);
          if (!("vehicle" in line) || !AIVehicle.IsValidVehicle(line.vehicle)) {
            if ("vehicle" in line) line.vehicle = vehicle;
            else line.vehicle <- vehicle;
          }
          local restored = line.vehicles.len();
          if ("vehCount" in line) line.vehCount = restored;
          else line.vehCount <- restored;
          if ("trains" in line) line.trains = restored;
          else line.trains <- restored;
        } else {
          /* Une ligne route est inventoriee par ses ordres : un rapport annuel a
           * pu deja recompter le camion pendant l'attente. Ne pas l'incrementer
           * aveuglement; relever seulement la cible retiree. */
          if ("predTrains" in line) {
            line.predTrains++;
            if ("vehCount" in line && line.vehCount < line.predTrains) line.vehCount++;
            if ("trains" in line && line.trains < line.predTrains) line.trains++;
          }
        }
      }
      if (AIVehicle.IsStoppedInDepot(vehicle)) AIVehicle.StartStopVehicle(vehicle);
      removeTickets.append(vehicle);
      clearStreaks.append(vehicle);
      if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
        OpexDecide("UNPROFITABLE_RETIRE", "action=cancel_timeout vehicle=" + vehicle + " line=" + lineId);
      }
      continue;
    }

    local lastSend = ("lastSendDate" in ticket) ? ticket.lastSendDate : -1;
    if (lastSend < 0 || now - lastSend >= 90) {
      if (AIVehicle.SendVehicleToDepot(vehicle)) {
        ticket.lastSendDate = now;
        ticket.attempts = ("attempts" in ticket) ? ticket.attempts + 1 : 1;
      }
    }
  }
  foreach (vehicle in removeTickets) {
    if (vehicle in this._vehiclesToRetire) delete this._vehiclesToRetire[vehicle];
    if (this._vehiclesToScrap != null && (vehicle in this._vehiclesToScrap)) {
      delete this._vehiclesToScrap[vehicle];
    }
  }
  foreach (upgrade in upgradeTickets) {
    if (upgrade.vehicle in this._vehiclesToRetire) {
      this._vehiclesToRetire.rawset(upgrade.vehicle, upgrade.ticket);
    }
  }
  if (this._unprofitableStreaks != null) {
    foreach (vehicle in clearStreaks) {
      if (vehicle in this._unprofitableStreaks) delete this._unprofitableStreaks[vehicle];
    }
  }
}
/* Les VehicleID sont reutilisables. Ne jamais laisser un streak attache a un ID
 * mort survivre jusqu'a ce qu'un vehicule sans rapport recupere son numero. */
function OpexAI::_purgeUnprofitableStreaks()
{
  if (this._unprofitableStreaks == null) return;
  local stale = [];
  foreach (vehicle, ignored in this._unprofitableStreaks) {
    if (!AIVehicle.IsValidVehicle(vehicle)) stale.append(vehicle);
  }
  foreach (vehicle in stale) {
    if (vehicle in this._unprofitableStreaks) delete this._unprofitableStreaks[vehicle];
  }
}
function OpexAI::_reportYear(year, ranked)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local best = ranked.best.len() > 0 ? ranked.best[0] : null;
  local stats = ranked.stats;

  OpexSign(anchor, "OX|" + year + "|" + this._catalog.towns.len()
                           + "|" + this._catalog.industries.len() + "|" + ranked.all);
  /* Croissance de ville (taches S4.5). Ville desservie = GetClosestTown d'une de
   * nos gares (rail/route/air/eau). "TV|89|12|9999|30|999" = 22 caracteres. */
  local servedTowns = {};
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    local ends = [line.stationA];
    if (("stationB" in line) && line.stationB != null) ends.append(line.stationB);
    foreach (tile in ends) {
      if (tile == null || !AIMap.IsValidTile(tile)) continue;
      local town = AITile.GetClosestTown(tile);
      if (town >= 0) servedTowns.rawset(town, true);
    }
  }
  local servedPops = [];
  local freePops = [];
  foreach (town in this._catalog.towns) {
    if (town.id in servedTowns) servedPops.append(town.pop);
    else freePops.append(town.pop);
  }
  OpexSign(anchor, "TV|" + (year % 100) + "|" + servedPops.len() + "|"
                           + OpexMedianInt(servedPops) + "|" + freePops.len() + "|"
                           + OpexMedianInt(freePops));
  OpexSign(anchor, "OC|" + year + "|" + this._budget.get("cat_towns")
                           + "|" + this._budget.get("cat_industries")
                           + "|" + this._budget.get("cat_rail"));
  OpexSign(anchor, "OP|" + year + "|" + this._budget.get("cand_pax")
                           + "|" + this._budget.get("cand_freight"));
  OpexSign(anchor, "OS|" + year + "|" + this._budget.get("cand_rank")
                           + "|" + this._budget.utilisationPerMille(this._startTick));

  /* Le poste qui domine tout le reste : la recherche de chemin et la construction. */
  local buildOps = this._budget.get("build_plans") + this._budget.get("build_search")
                 + this._budget.get("build_stations") + this._budget.get("build_track")
                 + this._budget.get("build_trains") + this._budget.get("build_water_plans")
                 + this._budget.get("build_docks") + this._budget.get("build_water_depot")
                 + this._budget.get("build_ships");
  OpexSign(anchor, "OW|" + year + "|" + buildOps + "|" + this._lines.len());

  local elapsedTicks = AIController.GetTick() - this._startTick;
  local totalAvail = elapsedTicks * OPS_PER_TICK;
  local totalUsed = this._budget.total();
  local totalUnused = totalAvail - totalUsed;
  if (totalUnused < 0) totalUnused = 0;
  local pctUsed = (totalAvail > 0) ? ((totalUsed * 1000) / totalAvail) : 0;
  local pctUnused = 1000 - pctUsed;
  local btText = "BT|" + (totalUsed / 1000000) + "M|" + (totalUnused / 1000000) + "M|" + pctUsed + "|" + pctUnused;
  if ("tot" in _budgetSignIds && AISign.IsValidSign(_budgetSignIds["tot"])) {
    AISign.SetName(_budgetSignIds["tot"], btText);
  } else {
    _budgetSignIds["tot"] <- AISign.BuildSign(AIMap.GetTileIndex(20, 1), btText);
  }

  local catY = 2;
  foreach (cat, spent in this._budget.totals) {
    local catPct = (totalUsed > 0) ? ((spent * 1000) / totalUsed) : 0;
    local availPct = (totalAvail > 0) ? ((spent * 1000) / totalAvail) : 0;
    local bcText = "BC|" + cat + "|" + (spent / 1000) + "k|" + catPct + "|" + availPct;
    if (bcText.len() > 31) bcText = bcText.slice(0, 31);
    if (cat in _budgetSignIds && AISign.IsValidSign(_budgetSignIds[cat])) {
      AISign.SetName(_budgetSignIds[cat], bcText);
    } else {
      _budgetSignIds[cat] <- AISign.BuildSign(AIMap.GetTileIndex(20, catY), bcText);
    }
    catY++;
  }

  /* Ces quatre panneaux mesurent les rejets AVANT TOP_K : sans eux, ranked.all ne dit pas si le
   * vivier est epuise par les origines, les bornes de distance ou le plancher de rendement. */
  OpexSign(anchor, "CG|" + year + "|" + stats.townsServed + "|" + stats.townsUnserved + "|"
                           + stats.industriesServed + "|" + stats.industriesUnserved);
  OpexSign(anchor, "CR|" + year + "|" + stats.pairsTotal + "|" + stats.pairsOriginServed
                           + "|" + stats.noMonthly);
  /* Le devenir des paires a UNE seule extremite servie, que la generation ne jette plus depuis le
   * 2026-08-29 : combien sont irrecuperables (aucune jointure concevable) et combien poursuivent
   * vers l'etage economique. La somme des deux est ce que l'ancienne regle coupait a l'aveugle.
   * Gate sur STATION_JOIN comme GM l'est sur ABANDON_MEMORY : le bras de controle du banc ne doit
   * pas payer une commande de panneau que l'autre bras ne paie pas. Son absence vaut zero. */
  if (STATION_JOIN || JOIN_PLACE) {
    OpexSign(anchor, "CJ|" + year + "|" + stats.pairsJoinImpossible + "|" + stats.pairsOneServed);
  }
  OpexSign(anchor, "CD|" + year + "|" + stats.distanceShort + "|" + stats.distanceLong);
  OpexSign(anchor, "CE|" + year + "|" + stats.economicsUnavailable + "|"
                           + stats.profitNonPositive + "|" + stats.ratioTooLow);
  OpexSign(anchor, "CK|" + year + "|" + stats.accepted + "|" + stats.topKOmitted);
  /* Item 7 : population des rejets profit<=0, pas seulement le compte CE.
   * NH|aa|n50|n75|n100|n200  bandes de distance ; NM|aa|pax|frt|near|mean.
   * Pire NM|99|9999|9999|9999|-999999 : 28 caracteres. Gate : a 0, zero panneau. */
  if (PROBE_NEGATIVE) {
    local mean = 0;
    if (stats.profitNonPositive > 0) mean = stats.negSum / stats.profitNonPositive;
    OpexSign(anchor, "NH|" + (year % 100) + "|" + stats.negBand50 + "|" + stats.negBand75
                             + "|" + stats.negBand100 + "|" + stats.negBand200);
    OpexSign(anchor, "NM|" + (year % 100) + "|" + stats.negPax + "|" + stats.negFreight
                             + "|" + stats.negNear + "|" + mean);
  }

  if (best != null) {
    OpexSign(anchor, "OB|" + year + "|" + best.distance
                             + "|" + best.monthly + "|" + best.ratio);
    OpexSign(anchor, "OE|" + year + "|" + best.trains
                             + "|" + best.profitAnnual + "|" + best.capital);
  }
  OpexSign(anchor, "OD|" + year + "|" + ranked.bands[0] + "|" + ranked.bands[1]
                           + "|" + ranked.bands[2] + "|" + ranked.bands[3]);
  if (this._catalog.loco != null) {
    OpexSign(anchor, "OL|" + year + "|" + this._catalog.loco.speed
                             + "|" + this._catalog.costTrackPerTile
                             + "|" + this._catalog.costStation);
  }

  if (EVENT_SUBSIDY_PROBE && this._subsidyStats != null) {
    OpexSign(anchor, "SR|" + (year % 100) + "|" + this._subsidyStats.offers
                     + "|" + this._subsidyStats.matchedPool
                     + "|" + this._subsidyStats.awardedSelf
                     + "|" + this._subsidyStats.awardedOther
                     + "|" + this._subsidyStats.expiredWithoutAward);
    if (DECISION_LOG) {
      OpexDecide("SUBSIDY_REPORT", "year=" + year + " offers=" + this._subsidyStats.offers + " matched=" + this._subsidyStats.matchedPool + " awarded_self=" + this._subsidyStats.awardedSelf + " awarded_other=" + this._subsidyStats.awardedOther + " expired=" + this._subsidyStats.expiredWithoutAward);
    }
  }
}
