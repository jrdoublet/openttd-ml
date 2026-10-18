/* V249 : une statue par mois quand on est riche. Aucun montant fixe :
 * riche = aucun emprunt, aucune passe projets arretee faute de caisse depuis le
 * mois precedent (V249_CASH_STOP, pose dans task_projects.nut), et apres la
 * statue la caisse couvre encore la reserve et le projet le plus cher du
 * portefeuille. Aucun etat sauvegarde. La statue est un bit du monde
 * (AITown.HasStatue). _v249StatueMonth et _v249StatueTowns ne font que borner la
 * cadence et suivre les villes dans la session courante. NoAI 15 n'expose pas
 * AITown.GetActionCost.
 *
 * Mode 1 : ville au plus fort profit brut de lignes (historique).
 * Mode 2 : ville au plus fort gain annuel attendu (effet source +26 de note cible,
 * station_cmd.cpp, pondere par profit annuel de ligne), avec filtre d'amortissement
 * base sur la duree de vie restante des convois existants. */

/* Capital du projet le plus cher encore liste : la statue ne doit jamais
 * prendre l'argent d'un projet que le portefeuille veut financer. */
function OpexV249MaxListedCapital(projects)
{
  if (projects == null || !("best" in projects) || projects.best == null) return 0;
  local most = 0;
  foreach (project in projects.best) {
    local capital = OpexProjectFinanceCapital(project);
    if (capital > most) most = capital;
  }
  return most;
}

function OpexV249LineVehicles(line)
{
  local stationId = OpexLineStationId(line, "A");
  if (stationId < 0) stationId = OpexLineStationId(line, "B");
  if (stationId >= 0) return OpexLineVehicleIds(line, stationId);
  if (("vehicles" in line) && line.vehicles != null) return line.vehicles;
  return [];
}

function OpexV249LineProfit(line)
{
  local vehicles = OpexV249LineVehicles(line);
  if (vehicles == null) return 0;
  local vehicleType = OpexLineVehicleType(line);
  local profit = 0;
  foreach (v in vehicles) {
    if (!AIVehicle.IsValidVehicle(v)) continue;
    if (AIVehicle.GetVehicleType(v) != vehicleType) continue;
    profit += AIVehicle.GetProfitLastYear(v);
  }
  return profit;
}

/* Cout que PerformTownAction paierait. AITestMode n'execute pas : la statue
 * n'est pas posee. AIAccounting enregistre le cout de commande simule. */
function OpexV249MeasureStatueCost(townId)
{
  local account = AIAccounting();
  {
    local test = AITestMode();
    AITown.PerformTownAction(townId, AITown.TOWN_ACTION_BUILD_STATUE);
  }
  return account.GetCosts();
}

/* Suivi mensuel de la note moyenne des gares dans les villes ayant une statue
 * posee par nous dans la session courante (mode 2).
 * Ce suivi est strictement O(villes a statue). */
function OpexAI::_v249LogStatueRatings()
{
  if (this._v249StatueTowns == null || this._v249StatueTowns.len() == 0 || this._lines == null) return;
  local tracked = {};
  foreach (townId in this._v249StatueTowns) {
    tracked[townId] <- { stations = {}, seenRatings = {} };
  }
  foreach (line in this._lines) {
    if (line == null) continue;
    local cargo = ("cargo" in line) ? line.cargo : -1;
    local hasCargo = (cargo >= 0 && AICargo.IsValidCargo(cargo));
    foreach (endName in ["A", "B"]) {
      local st = OpexLineStationId(line, endName);
      if (st < 0 || !AIStation.IsValidStation(st)) continue;
      local townId = AIStation.GetNearestTown(st);
      if (!(townId in tracked)) continue;
      local info = tracked[townId];
      info.stations[st] <- 1;
      if (hasCargo && AIStation.HasCargoRating(st, cargo)) {
        local rKey = st + ":" + cargo;
        if (!(rKey in info.seenRatings)) {
          local pct = AIStation.GetCargoRating(st, cargo);
          info.seenRatings[rKey] <- OpexC121RatingPercentToByteMid(pct);
        }
      }
    }
  }
  foreach (townId in this._v249StatueTowns) {
    local info = tracked[townId];
    local sumR = 0;
    local countR = 0;
    foreach (r in info.seenRatings) {
      sumR += r;
      countR++;
    }
    local avgRating = (countR > 0) ? ((sumR.tofloat() / countR.tofloat()) + 0.5).tointeger() : 0;
    if (DECISION_LOG) OpexDecide("V249_RATING", "town=" + townId + " rating=" + avgRating + " stations=" + info.stations.len());
  }
}

function OpexAI::_dispatchV249Statue(task, year)
{
  if (!V249_STATUE) return false;
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v249StatueMonth == ym) return false;
  this._v249StatueMonth = ym;

  if (V249_STATUE == 2 && DECISION_LOG && this._v249StatueTowns != null && this._v249StatueTowns.len() > 0) {
    this._v249LogStatueRatings();
  }

  local cashStop = V249_CASH_STOP;
  ::V249_CASH_STOP = false;
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=loan loan=" + loan);
    return true;
  }
  if (cashStop) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cash_stop");
    return true;
  }

  local bestTown = -1;
  local bestLines = 0;
  local bestProfit = 0;
  local bestGain = 0.0;
  local bestStations = 0;
  local bestAvgRating = 0;
  local bestLinesTable = null;
  local paybackYears = 0.0;
  local found = false;
  local nStatue = 0;
  local nUnavail = 0;
  local nTowns = 0;
  local nLines = 0;

  if (V249_STATUE == 1) {
    local byTown = {};
    if (this._lines != null) {
      foreach (line in this._lines) {
        if (line == null) continue;
        nLines++;
        local profit = OpexV249LineProfit(line);
        local seenTown = {};
        foreach (endName in ["A", "B"]) {
          local stationId = OpexLineStationId(line, endName);
          if (stationId < 0) continue;
          local townId = AIStation.GetNearestTown(stationId);
          if (!AITown.IsValidTown(townId)) continue;
          if (townId in seenTown) continue;
          seenTown[townId] <- 1;
          if (!(townId in byTown)) byTown[townId] <- { profit = 0, lines = 0 };
          byTown[townId].profit += profit;
          byTown[townId].lines++;
        }
      }
    }

    foreach (townId, info in byTown) {
      nTowns++;
      if (AITown.HasStatue(townId)) {
        nStatue++;
        continue;
      }
      if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_BUILD_STATUE)) {
        nUnavail++;
        continue;
      }
      if (!found || info.profit > bestProfit || (info.profit == bestProfit && townId < bestTown)) {
        found = true;
        bestTown = townId;
        bestProfit = info.profit;
        bestLines = info.lines;
      }
    }
  } else {
    /* MODE 2 : Choix par gain annuel attendu de captage et test d'amortissement. */
    local candidates = {};
    if (this._lines != null) {
      foreach (line in this._lines) {
        if (line == null) continue;
        nLines++;
        local lineProfit = OpexV249LineProfit(line);
        local cargo = ("cargo" in line) ? line.cargo : -1;
        local hasCargo = (cargo >= 0 && AICargo.IsValidCargo(cargo));

        /* Approximation economique (mode 2) : OpenTTD ne ventile pas le profit
         * annuel d'un convoi par marchandise ni par station. On utilise donc le profit
         * global annuel de la ligne (AIVehicle.GetProfitLastYear) pondere par le gain
         * relatif de captage ((min(note + 26, 255) - note) / note) a chaque gare qui
         * charge ce cargo. Quand les DEUX extremites chargent le cargo (voyageurs,
         * courrier), chacune ne porte que la moitie du profit : une statue ne releve
         * que le flux de sa ville. Le fret ne charge qu'a la source, qui porte tout. */
        local stA = OpexLineStationId(line, "A");
        local stB = OpexLineStationId(line, "B");
        local loadsA = hasCargo && stA >= 0 && AIStation.IsValidStation(stA) && AIStation.HasCargoRating(stA, cargo);
        local loadsB = hasCargo && stB >= 0 && AIStation.IsValidStation(stB) && AIStation.HasCargoRating(stB, cargo);
        local endShare = (loadsA && loadsB) ? 0.5 : 1.0;

        foreach (endName in ["A", "B"]) {
          local stationId = (endName == "A") ? stA : stB;
          if (stationId < 0 || !AIStation.IsValidStation(stationId)) continue;
          local townId = AIStation.GetNearestTown(stationId);
          if (!AITown.IsValidTown(townId)) continue;

          if (!(townId in candidates)) {
            candidates[townId] <- { gain = 0.0, stations = {}, lines = {}, seenRatings = {} };
          }
          local cData = candidates[townId];
          cData.stations[stationId] <- 1;
          cData.lines[line] <- 1;

          if (hasCargo && AIStation.HasCargoRating(stationId, cargo)) {
            local rKey = stationId + ":" + cargo;
            local pct = AIStation.GetCargoRating(stationId, cargo);
            local note = OpexC121RatingPercentToByteMid(pct);
            if (!(rKey in cData.seenRatings)) {
              cData.seenRatings[rKey] <- note;
            }
            if (note > 0 && lineProfit > 0) {
              local targetNote = note + 26;
              if (targetNote > 255) targetNote = 255;
              local relGain = (targetNote - note).tofloat() / note.tofloat();
              local weight = lineProfit.tofloat() * endShare;
              cData.gain += relGain * weight;
            }
          }
        }
      }
    }

    foreach (townId, cData in candidates) {
      nTowns++;
      if (AITown.HasStatue(townId)) {
        nStatue++;
        continue;
      }
      if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_BUILD_STATUE)) {
        nUnavail++;
        continue;
      }
      if (cData.gain <= 0.0) continue;

      if (!found || cData.gain > bestGain || (cData.gain == bestGain && townId < bestTown)) {
        found = true;
        bestTown = townId;
        bestGain = cData.gain;
        bestStations = cData.stations.len();
        bestLinesTable = cData.lines;
        local sumR = 0;
        local countR = 0;
        foreach (r in cData.seenRatings) {
          sumR += r;
          countR++;
        }
        bestAvgRating = (countR > 0) ? ((sumR.tofloat() / countR.tofloat()) + 0.5).tointeger() : 0;
      }
    }
  }

  if (!found) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=no_town statue=" + nStatue + " unavailable=" + nUnavail + " towns=" + nTowns + " lines=" + nLines);
    return true;
  }

  local cost = OpexV249MeasureStatueCost(bestTown);

  if (V249_STATUE == 2) {
    /* Duree de vie et amortissement (mode 2) : pas de fin de partie connue de l'IA
     * (le jeu peut durer indefiniment) ; la statue est permanente (source OpenTTD).
     * On compare le delai de remboursement cout/gain a la duree de service moyenne restante
     * des vehicules de ces lignes ((AIVehicle.GetMaxAge - AIVehicle.GetAge) / 365). */
    local seenVehicles = {};
    local totalRemDays = 0.0;
    local totalVehicles = 0;
    if (bestLinesTable != null) {
      foreach (line, _ in bestLinesTable) {
        local vType = OpexLineVehicleType(line);
        local vehicles = OpexV249LineVehicles(line);
        if (vehicles == null) continue;
        foreach (v in vehicles) {
          if (!AIVehicle.IsValidVehicle(v)) continue;
          if (AIVehicle.GetVehicleType(v) != vType) continue;
          if (v in seenVehicles) continue;
          seenVehicles[v] <- 1;
          local rem = AIVehicle.GetMaxAge(v) - AIVehicle.GetAge(v);
          if (rem < 0) rem = 0;
          totalRemDays += rem;
          totalVehicles++;
        }
      }
    }

    local vehRemainingYears = (totalVehicles > 0) ? ((totalRemDays / totalVehicles.tofloat()) / 365.0) : 0.0;
    paybackYears = (bestGain > 0.0) ? (cost.tofloat() / bestGain) : -1.0;

    if (cost <= 0 || totalVehicles == 0 || paybackYears < 0.0 || bestGain * vehRemainingYears < cost.tofloat()) {
      local pbStr = "" + ((paybackYears * 10).tointeger() / 10.0);
      local vyStr = "" + ((vehRemainingYears * 10).tointeger() / 10.0);
      if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=payback town=" + bestTown + " gain=" + bestGain.tointeger() + " cost=" + cost + " payback=" + pbStr + " veh_years=" + vyStr);
      return true;
    }
  }

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects);
  if (cost <= 0 || cash - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cost cash=" + cash + " cost=" + cost + " threshold=" + threshold + " town=" + bestTown);
    return true;
  }
  local built = AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_BUILD_STATUE);
  if (!built) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=failed town=" + bestTown + " cost=" + cost + " cash=" + cash + " threshold=" + threshold);
    return true;
  }
  if (this._v249StatueTowns != null) this._v249StatueTowns.append(bestTown);
  if (V249_STATUE == 1) {
    if (DECISION_LOG) OpexDecide("V249_STATUE", "town=" + bestTown + " cost=" + cost + " cash=" + cash + " threshold=" + threshold + " lines=" + bestLines + " profit=" + bestProfit);
  } else {
    local pbStr = "" + ((paybackYears * 10).tointeger() / 10.0);
    if (DECISION_LOG) OpexDecide("V249_STATUE", "town=" + bestTown + " gain=" + bestGain.tointeger() + " cost=" + cost + " payback=" + pbStr + " stations=" + bestStations + " rating_before=" + bestAvgRating + " cash=" + cash + " threshold=" + threshold);
  }
  return true;
}
