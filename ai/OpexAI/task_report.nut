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
  local c70Sums = C70_MODE_CALIBRATION ? { rail = [0.0, 0], road = [0.0, 0], air = [0.0, 0], water = [0.0, 0] } : null;
  local c69ProfRatios = C69_BOTTLENECK_PROBE ? { rail = [], road = [], air = [], water = [] } : null;
  local c69RevRatios = C69_BOTTLENECK_PROBE ? { rail = [], road = [], air = [], water = [] } : null;
  local c69LineCounts = C69_BOTTLENECK_PROBE ? { rail = 0, road = 0, air = 0, water = 0 } : null;
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
    /* C70 : ratio realise/predit par ligne, cumule sur ses annees pleines (age >= 2 : l'annee de
     * construction est partielle). Par convoi initial, amortissement predit retire du realise
     * (GetProfitLastYear n'amortit rien). Ratio de sommes : une annee aberrante pese son poids. */
    if (C70_MODE_CALIBRATION) {
      local cMode = ("mode" in line) ? line.mode : "unknown";
      local cAge = ("year" in line) ? (year - line.year) : -1;
      local cPred = ("predicted" in line) ? line.predicted : 0;
      local cN0 = ("trains0" in line) ? line.trains0 : 0;
      if (cAge >= 2 && cPred > 0 && cN0 > 0 && vehCount > 0 && (cMode in c70Sums)) {
        local cAmort = ("predAmort" in line) ? line.predAmort : 0;
        local real = profit.tofloat() * cN0 / vehCount - cAmort;
        if (!("c70Real" in line)) { line.c70Real <- 0.0; line.c70Pred <- 0.0; }
        line.c70Real += real;
        line.c70Pred += cPred.tofloat();
      }
      if (("c70Pred" in line) && line.c70Pred > 0 && (cMode in c70Sums)) {
        /* tofloat : apres chargement, les cumuls sont des entiers (la sauvegarde arrondit les
         * flottants) et une division entiere fausserait le ratio. */
        c70Sums[cMode][0] += line.c70Real.tofloat() / line.c70Pred.tofloat();
        c70Sums[cMode][1]++;
      }
    }
    if (C69_BOTTLENECK_PROBE) {
      local lMode = ("mode" in line) ? line.mode : "unknown";
      local lAge = ("year" in line) ? (year - line.year) : -1;
      if (lAge >= 1 && (lMode in c69ProfRatios)) {
        c69LineCounts[lMode]++;
        local predProfit = ("predicted" in line) ? line.predicted : 0;
        local predRev = ("predRevenue" in line) ? line.predRevenue : 0;
        local realRev = profit + runCost;
        /* Par convoi : la prediction porte sur la flotte initiale, le realise sur la flotte
         * courante (avions et bus ajoutes ensuite). Sans cette normalisation, le ratio mesure la
         * croissance de flotte, pas l'erreur du modele. */
        local n0 = ("trains0" in line) ? line.trains0 : 0;
        /* C70 : une ligne brute par ligne mure, pour les medianes hors partie (M1-M4). */
        OpexC69Log("phase=line_calib year=" + (year - 1) + " mode=" + lMode
            + " line=" + (("lineId" in line) ? line.lineId : -1) + " age=" + lAge
            + " pred_p=" + predProfit + " real_p=" + profit
            + " pred_r=" + predRev + " real_r=" + realRev
            + " pred_run=" + (("predRunning" in line) ? line.predRunning : 0)
            + " pred_amort=" + (("predAmort" in line) ? line.predAmort : 0)
            + " run=" + runCost
            + " trains0=" + n0 + " vehs=" + vehCount
            + " plane=" + (("planeId" in line) ? line.planeId : -1));
        if (n0 > 0 && vehCount > 0) {
          local scale = n0.tofloat() / vehCount.tofloat();
          if (predProfit > 0) {
            c69ProfRatios[lMode].append(profit.tofloat() * scale / predProfit.tofloat());
          }
          if (predRev > 0) {
            c69RevRatios[lMode].append(realRev.tofloat() * scale / predRev.tofloat());
          }
        }
      }
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
  if (C70_MODE_CALIBRATION) {
    /* Pseudo-ligne a 1 : k = (somme des ratios + 1) / (n + 1). Sans ligne mure, k = 1 ; la premiere
     * ligne ne pese que la moitie ; l'effet s'efface a mesure que les lignes s'accumulent. */
    foreach (m, acc in c70Sums) {
      C70_MODE_FACTOR[m] = (acc[0] + 1.0) / (acc[1] + 1).tofloat();
      if (C69_BOTTLENECK_PROBE) {
        OpexC69Log("phase=c70_factor year=" + year + " mode=" + m + " lines=" + acc[1]
            + " k=" + C70_MODE_FACTOR[m]);
      }
    }
  }
  if (C69_BOTTLENECK_PROBE && C69_PENDING_FOLLOWUPS != null) {
    foreach (item in C69_PENDING_FOLLOWUPS) {
      OpexC69Log("phase=c3_pending pass=" + item.passId + " passes_waited=" + item.passesWaited
          + " target=" + item.c69Key);
    }
  }
  if (C69_BOTTLENECK_PROBE) {
    foreach (m in ["rail", "road", "air", "water"]) {
      local nLines = c69LineCounts[m];
      if (nLines > 0) {
        local pList = c69ProfRatios[m];
        local rList = c69RevRatios[m];
        local medP = OpexMedianFloat(pList);
        local medR = OpexMedianFloat(rList);
        OpexC69Log("phase=annual_calibration year=" + year + " profit_year=" + (year - 1)
            + " mode=" + m + " n=" + nLines + " n_prof=" + pList.len() + " n_rev=" + rList.len()
            + " med_real_pred_prof=" + medP + " med_real_pred_rev=" + medR);
      }
    }
    OpexC69Log("phase=plane_choice_count year=" + year
        + " calls=" + C69_PLANE_CHOICE_CALLS
        + " differ_roi=" + C69_PLANE_CHOICE_DIFFER_ROI
        + " differ_c69=" + C69_PLANE_CHOICE_DIFFER_C69);
    C69_PLANE_CHOICE_CALLS = 0;
    C69_PLANE_CHOICE_DIFFER_ROI = 0;
    C69_PLANE_CHOICE_DIFFER_C69 = 0;
    local c73Year = year - 1;
    if (c73Year >= 1970) {
      OpexC73FlushLedger(c73Year);
      OpexC75FlushYear(c73Year);
      if (C39_INVALIDATION_PROBE) OpexC76FlushYear(c73Year);
    }
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
  if (C76_REGEN_TARGETED && toRemove.len() > 0) {
    this._c76BumpLayer("lines", false);
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

  if (C69_BOTTLENECK_PROBE) {
    this._reportC78Candidates(year);
  }
}

/* C78 : publication annuelle passive du vivier de candidats OpexAI */
function OpexAI::_reportC78Candidates(year)
{
  if (!C69_BOTTLENECK_PROBE) return;
  if (this._projects == null) return;

  local bestRank = {};
  if (("best" in this._projects) && this._projects.best != null) {
    for (local i = 0; i < this._projects.best.len(); i++) {
      local bp = this._projects.best[i];
      if (bp != null) {
        local k = OpexProjectAttemptKey(bp);
        if (!(k in bestRank)) bestRank[k] <- i;
      }
    }
  }

  local allCandidates = [];
  if (("candidateGroups" in this._projects) && this._projects.candidateGroups != null) {
    foreach (groupKey, list in this._projects.candidateGroups) {
      local arr = (typeof list == "array") ? list : [list];
      foreach (p in arr) {
        if (p != null) allCandidates.append(p);
      }
    }
  } else if (("best" in this._projects) && this._projects.best != null) {
    foreach (p in this._projects.best) {
      if (p != null) allCandidates.append(p);
    }
  }

  if (allCandidates.len() > 400) {
    allCandidates.sort(function(a, b) {
      local pa = ("profitAnnual" in a) ? a.profitAnnual : 0;
      local pb = ("profitAnnual" in b) ? b.profitAnnual : 0;
      if (pa != pb) return (pa > pb) ? -1 : 1;
      return 0;
    });
    allCandidates.resize(400);
  }

  local availableCapital = OpexAvailableCapital();

  foreach (p in allCandidates) {
    local mode = ("mode" in p) ? p.mode : "unknown";
    local townA = -1;
    local townB = -1;
    local indA = -1;
    local indB = -1;

    local cand = ("payload" in p && p.payload != null) ? p.payload : p;

    if (mode == "air") {
      local plan = cand;
      if (typeof plan == "table") {
        if (("siteA" in plan) && plan.siteA != null && typeof plan.siteA == "table") {
          if (("town" in plan.siteA) && plan.siteA.town != null) {
            if (typeof plan.siteA.town == "table" && ("id" in plan.siteA.town)) {
              townA = plan.siteA.town.id;
            } else if (typeof plan.siteA.town == "integer") {
              townA = plan.siteA.town;
            }
          }
          if (townA < 0 && ("anchor" in plan.siteA) && AIMap.IsValidTile(plan.siteA.anchor)) {
            townA = AITile.GetClosestTown(plan.siteA.anchor);
          }
        }
        if (("siteB" in plan) && plan.siteB != null && typeof plan.siteB == "table") {
          if (("town" in plan.siteB) && plan.siteB.town != null) {
            if (typeof plan.siteB.town == "table" && ("id" in plan.siteB.town)) {
              townB = plan.siteB.town.id;
            } else if (typeof plan.siteB.town == "integer") {
              townB = plan.siteB.town;
            }
          }
          if (townB < 0 && ("anchor" in plan.siteB) && AIMap.IsValidTile(plan.siteB.anchor)) {
            townB = AITile.GetClosestTown(plan.siteB.anchor);
          }
        }
      }
      if (townA < 0 && ("src" in p) && AIMap.IsValidTile(p.src)) townA = AITile.GetClosestTown(p.src);
      if (townB < 0 && ("dst" in p) && AIMap.IsValidTile(p.dst)) townB = AITile.GetClosestTown(p.dst);
    } else if (mode == "fleet") {
      if (typeof cand == "table" && ("line" in cand) && cand.line != null && typeof cand.line == "table") {
        local l = cand.line;
        if (("stationA" in l) && AIMap.IsValidTile(l.stationA)) townA = AITile.GetClosestTown(l.stationA);
        if (("stationB" in l) && AIMap.IsValidTile(l.stationB)) townB = AITile.GetClosestTown(l.stationB);
      }
    } else {
      if (typeof cand == "table") {
        if (("srcTown" in cand) && cand.srcTown >= 0) townA = cand.srcTown;
        if (("dstTown" in cand) && cand.dstTown >= 0) townB = cand.dstTown;
        if (("srcIndustry" in cand) && cand.srcIndustry >= 0) indA = cand.srcIndustry;
        if (("dstIndustry" in cand) && cand.dstIndustry >= 0) indB = cand.dstIndustry;
      }
      if (townA < 0 && ("srcTown" in p) && p.srcTown >= 0) townA = p.srcTown;
      if (townB < 0 && ("dstTown" in p) && p.dstTown >= 0) townB = p.dstTown;
      if (indA < 0 && ("srcIndustry" in p) && p.srcIndustry >= 0) indA = p.srcIndustry;
      if (indB < 0 && ("dstIndustry" in p) && p.dstIndustry >= 0) indB = p.dstIndustry;

      local isFreight = (("kind" in p) && p.kind == "freight") || (typeof cand == "table" && ("kind" in cand) && cand.kind == "freight");
      if (isFreight) {
        if (indA < 0) {
          local sTile = (typeof cand == "table" && ("src" in cand)) ? cand.src : (("src" in p) ? p.src : -1);
          if (AIMap.IsValidTile(sTile)) {
            local id = AIIndustry.GetIndustryID(sTile);
            if (AIIndustry.IsValidIndustry(id)) indA = id;
          }
        }
        if (indB < 0) {
          local dTile = (typeof cand == "table" && ("dst" in cand)) ? cand.dst : (("dst" in p) ? p.dst : -1);
          if (AIMap.IsValidTile(dTile)) {
            local id = AIIndustry.GetIndustryID(dTile);
            if (AIIndustry.IsValidIndustry(id)) indB = id;
          }
        }
      }

      /* Ville la plus proche meme pour le fret : les lignes relevees dans la sauvegarde sont
       * identifiees par la ville de leurs gares, l'appariement se fait donc par paire de villes. */
      if (townA < 0) {
        local sTile = (typeof cand == "table" && ("src" in cand)) ? cand.src : (("src" in p) ? p.src : -1);
        if (AIMap.IsValidTile(sTile)) townA = AITile.GetClosestTown(sTile);
      }
      if (townB < 0) {
        local dTile = (typeof cand == "table" && ("dst" in cand)) ? cand.dst : (("dst" in p) ? p.dst : -1);
        if (AIMap.IsValidTile(dTile)) townB = AITile.GetClosestTown(dTile);
      }
    }

    if (townA >= 0 && !AITown.IsValidTown(townA)) townA = -1;
    if (townB >= 0 && !AITown.IsValidTown(townB)) townB = -1;
    if (indA >= 0 && !AIIndustry.IsValidIndustry(indA)) indA = -1;
    if (indB >= 0 && !AIIndustry.IsValidIndustry(indB)) indB = -1;

    local pP = ("profitAnnual" in p) ? p.profitAnnual : 0;
    local pC = OpexProjectFinanceCapital(p);
    local key = OpexProjectAttemptKey(p);
    local rank = (key in bestRank) ? bestRank[key] : -1;
    local affordable = (pC <= availableCapital) ? 1 : 0;

    local fields = "year=" + year + " mode=" + mode + " townA=" + townA + " townB=" + townB
                 + " indA=" + indA + " indB=" + indB + " P=" + pP + " C=" + pC
                 + " rank=" + rank + " affordable=" + affordable;
    OpexC78CandidateLog(fields);
  }
}


function OpexAI::_c76RecordRegen(kind, ops, days, year, reason = "unknown")
{
  if (!C39_INVALIDATION_PROBE) return;

  local dateNow = AIDate.GetCurrentDate();
  local prev = C76_PREV_STATE;
  local daysSincePrev = (prev != null && ("date" in prev)) ? (dateNow - prev.date) : 0;

  local townPopSum = 0;
  local townsN = 0;
  local townsCurr = {};
  if (this._catalog != null && ("towns" in this._catalog) && this._catalog.towns != null) {
    townsN = this._catalog.towns.len();
    foreach (t in this._catalog.towns) {
      if (t != null) {
        if ("pop" in t) townPopSum += t.pop;
        if ("id" in t) townsCurr.rawset(t.id, true);
      }
    }
  }
  local townsDelta = 0;
  if (prev != null && ("towns" in prev) && prev.towns != null) {
    foreach (id, _ in townsCurr) {
      if (!(id in prev.towns)) townsDelta++;
    }
    foreach (id, _ in prev.towns) {
      if (!(id in townsCurr)) townsDelta++;
    }
  }
  local townPopDeltaPct = OpexC76FormatPct(townPopSum, (prev != null && ("towns_pop" in prev)) ? prev.towns_pop : null);

  local indCurr = {};
  local indProdSum = 0;
  if (this._catalog != null && ("industries" in this._catalog) && this._catalog.industries != null) {
    foreach (ind in this._catalog.industries) {
      if (ind != null && ("id" in ind) && AIIndustry.IsValidIndustry(ind.id)) {
        indCurr.rawset(ind.id, true);
      }
    }
  }
  if (this._catalog != null && ("producers" in this._catalog) && this._catalog.producers != null
      && ("industries" in this._catalog) && this._catalog.industries != null) {
    foreach (cargo, indIdxs in this._catalog.producers) {
      foreach (idx in indIdxs) {
        if (idx >= 0 && idx < this._catalog.industries.len()) {
          local ind = this._catalog.industries[idx];
          if (ind != null && ("id" in ind) && AIIndustry.IsValidIndustry(ind.id)) {
            indProdSum += AIIndustry.GetLastMonthProduction(ind.id, cargo);
          }
        }
      }
    }
  }
  local indChanged = 0;
  if (prev != null && ("industries" in prev) && prev.industries != null) {
    foreach (id, _ in indCurr) {
      if (!(id in prev.industries)) indChanged++;
    }
    foreach (id, _ in prev.industries) {
      if (!(id in indCurr)) indChanged++;
    }
  }
  local indProdDeltaPct = OpexC76FormatPct(indProdSum, (prev != null && ("ind_prod" in prev)) ? prev.ind_prod : null);

  local enginesRail = OpexC76GetBuildableEngines(AIVehicle.VT_RAIL);
  local enginesRoad = OpexC76GetBuildableEngines(AIVehicle.VT_ROAD);
  local enginesAir = OpexC76GetBuildableEngines(AIVehicle.VT_AIR);
  local enginesWater = OpexC76GetBuildableEngines(AIVehicle.VT_WATER);

  local chgRail = OpexC76CountEngineChanges(enginesRail, (prev != null && ("engines" in prev) && ("rail" in prev.engines)) ? prev.engines.rail : null);
  local chgRoad = OpexC76CountEngineChanges(enginesRoad, (prev != null && ("engines" in prev) && ("road" in prev.engines)) ? prev.engines.road : null);
  local chgAir = OpexC76CountEngineChanges(enginesAir, (prev != null && ("engines" in prev) && ("air" in prev.engines)) ? prev.engines.air : null);
  local chgWater = OpexC76CountEngineChanges(enginesWater, (prev != null && ("engines" in prev) && ("water" in prev.engines)) ? prev.engines.water : null);

  local linesN = (this._lines != null) ? this._lines.len() : 0;
  local linesDelta = (prev != null && ("lines_n" in prev)) ? (linesN - prev.lines_n) : 0;

  local budgetNow = OpexAvailableCapital();
  local cashBudgetDeltaPct = OpexC76FormatPct(budgetNow, (prev != null && ("budget" in prev)) ? prev.budget : null);

  local evStr = "0";
  if (C76_EVENTS_SINCE_PREV != null) {
    evStr = "" + C76_EVENTS_SINCE_PREV.total;
    if (C76_EVENTS_SINCE_PREV.total > 0 && C76_EVENTS_SINCE_PREV.by_type.len() > 0) {
      local parts = [];
      foreach (k, v in C76_EVENTS_SINCE_PREV.by_type) {
        parts.append(k + ":" + v);
      }
      evStr += "(" + parts[0];
      for (local i = 1; i < parts.len(); i++) {
        evStr += "," + parts[i];
      }
      evStr += ")";
    }
  }

  local candByMode = {
    rail = {},
    road = {},
    air = {},
    water = {},
    fleet = {}
  };
  if (this._projects != null && ("candidateGroups" in this._projects) && this._projects.candidateGroups != null) {
    foreach (groupKey, list in this._projects.candidateGroups) {
      local arr = (typeof list == "array") ? list : [list];
      foreach (p in arr) {
        if (p == null) continue;
        local m = ("mode" in p) ? p.mode : "unknown";
        if (!(m in candByMode)) candByMode.rawset(m, {});
        local key = OpexProjectAttemptKey(p);
        local profit = ("profitAnnual" in p) ? p.profitAnnual : 0;
        candByMode[m].rawset(key, profit);
      }
    }
  }

  local candN = {};
  local candSameKeys = {};
  local candSameEcon = {};
  local modeOrder = ["rail", "road", "air", "water", "fleet"];
  foreach (m in modeOrder) {
    local currKeys = candByMode[m];
    local prevKeys = (prev != null && ("cand_keys" in prev) && (m in prev.cand_keys)) ? prev.cand_keys[m] : null;
    candN.rawset(m, currKeys.len());
    if (prevKeys == null) {
      candSameKeys.rawset(m, "100.00");
      candSameEcon.rawset(m, "100.00");
    } else {
      local maxN = (currKeys.len() > prevKeys.len()) ? currKeys.len() : prevKeys.len();
      if (maxN == 0) {
        candSameKeys.rawset(m, "100.00");
        candSameEcon.rawset(m, "100.00");
      } else {
        local commonCount = 0;
        local sameEconCount = 0;
        foreach (k, currProfit in currKeys) {
          if (k in prevKeys) {
            commonCount++;
            local prevProfit = prevKeys[k];
            local diff = currProfit - prevProfit;
            if (diff < 0) diff = -diff;
            local baseP = prevProfit >= 0 ? prevProfit : -prevProfit;
            local tol = baseP / 100;
            if (diff <= tol) sameEconCount++;
          }
        }
        candSameKeys.rawset(m, OpexC76FormatRatioPct(commonCount, maxN));
        candSameEcon.rawset(m, (commonCount > 0) ? OpexC76FormatRatioPct(sameEconCount, commonCount) : "0.00");
      }
    }
  }

  local bestKeys = [];
  local bestTop1 = null;
  if (this._projects != null && ("best" in this._projects) && this._projects.best != null) {
    foreach (p in this._projects.best) {
      if (p != null) {
        local k = OpexProjectAttemptKey(p);
        bestKeys.append(k);
      }
    }
    if (bestKeys.len() > 0) bestTop1 = bestKeys[0];
  }

  local bestSameTop1 = 1;
  local bestSameKeysPct = "100.00";
  if (prev != null && ("best_keys" in prev)) {
    if (bestTop1 == null && prev.best_top1 == null) {
      bestSameTop1 = 1;
    } else if (bestTop1 != null && prev.best_top1 != null && bestTop1 == prev.best_top1) {
      bestSameTop1 = 1;
    } else {
      bestSameTop1 = 0;
    }

    local prevBestTable = {};
    if (prev.best_keys != null) {
      foreach (k in prev.best_keys) prevBestTable.rawset(k, true);
    }
    local maxBest = (bestKeys.len() > prev.best_keys.len()) ? bestKeys.len() : prev.best_keys.len();
    if (maxBest == 0) {
      bestSameKeysPct = "100.00";
    } else {
      local commonBest = 0;
      foreach (k in bestKeys) {
        if (k in prevBestTable) commonBest++;
      }
      bestSameKeysPct = OpexC76FormatRatioPct(commonBest, maxBest);
    }
  }

  local unchangedDeps = (prev != null
    && indChanged == 0
    && chgRail == 0 && chgRoad == 0 && chgAir == 0 && chgWater == 0
    && linesDelta == 0
    && townsDelta == 0) ? 1 : 0;

  local line = "phase=regen kind=" + kind + " reason=" + reason + " year=" + year
    + " days=" + days
    + " days_since_prev=" + daysSincePrev
    + " ops=" + ops
    + " towns_n=" + townsN
    + " towns_pop_delta_pct=" + townPopDeltaPct
    + " industries_n=" + indCurr.len()
    + " industries_changed=" + indChanged
    + " ind_prod_delta_pct=" + indProdDeltaPct
    + " engines_changed_rail=" + chgRail
    + " engines_changed_road=" + chgRoad
    + " engines_changed_air=" + chgAir
    + " engines_changed_water=" + chgWater
    + " lines_n=" + linesN
    + " lines_delta=" + linesDelta
    + " cash_budget_delta_pct=" + cashBudgetDeltaPct
    + " events_since_prev=" + evStr;

  foreach (m in modeOrder) {
    line += " cand_" + m + "_n=" + candN[m]
         + " cand_" + m + "_same_keys_pct=" + candSameKeys[m]
         + " cand_" + m + "_same_econ_pct=" + candSameEcon[m];
  }

  line += " best_same_top1=" + bestSameTop1
        + " best_same_keys_pct=" + bestSameKeysPct;

  OpexC76Log(line);

  if (C76_YEAR_LEDGER != null) {
    if (!(year in C76_YEAR_LEDGER)) {
      C76_YEAR_LEDGER.rawset(year, {
        full = 0,
        incremental = 0,
        avoided = 0,
        ops_total = 0,
        days_total = 0,
        unchanged_deps = 0,
        top1_unchanged = 0,
        reasons = {}
      });
    }
    local rec = C76_YEAR_LEDGER[year];
    if (kind == "full") rec.full++;
    else if (kind == "incremental") rec.incremental++;
    rec.ops_total += ops;
    rec.days_total += days;
    if (unchangedDeps == 1) rec.unchanged_deps++;
    if (bestSameTop1 == 1) rec.top1_unchanged++;
    if (!("reasons" in rec)) rec.reasons <- {};
    if (reason in rec.reasons) rec.reasons[reason]++;
    else rec.reasons.rawset(reason, 1);
  }

  C76_PREV_STATE = {
    date = dateNow,
    towns = townsCurr,
    towns_n = townsN,
    towns_pop = townPopSum,
    industries = indCurr,
    industries_n = indCurr.len(),
    ind_prod = indProdSum,
    engines = {
      rail = enginesRail,
      road = enginesRoad,
      air = enginesAir,
      water = enginesWater
    },
    lines_n = linesN,
    budget = budgetNow,
    cand_keys = candByMode,
    best_keys = bestKeys,
    best_top1 = bestTop1
  };

  C76_EVENTS_SINCE_PREV = { total = 0, by_type = {} };
}

function OpexAI::_c76RecordAvoided(year)
{
  if (!C39_INVALIDATION_PROBE) return;
  if (C76_YEAR_LEDGER != null) {
    if (!(year in C76_YEAR_LEDGER)) {
      C76_YEAR_LEDGER.rawset(year, {
        full = 0,
        incremental = 0,
        avoided = 0,
        ops_total = 0,
        days_total = 0,
        unchanged_deps = 0,
        top1_unchanged = 0,
        reasons = {}
      });
    }
    local rec = C76_YEAR_LEDGER[year];
    if (!("avoided" in rec)) rec.avoided <- 0;
    rec.avoided++;
  }
  local avoidedCount = (C76_YEAR_LEDGER != null && (year in C76_YEAR_LEDGER) && ("avoided" in C76_YEAR_LEDGER[year]))
      ? C76_YEAR_LEDGER[year].avoided : 1;
  OpexC76Log("phase=regen_avoided year=" + year + " avoided_count=" + avoidedCount);
}
