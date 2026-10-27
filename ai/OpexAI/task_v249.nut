/* V249 : une statue par mois quand on est riche. Aucun montant fixe.
 * Mode 1 : riche = aucun emprunt, aucune passe projets arretee faute de caisse depuis le
 * mois precedent (V249_CASH_STOP), et apres la statue la caisse couvre encore
 * le projet le plus cher du portefeuille. Ville au plus fort profit historique.
 * Mode 2 (V249a+b+c) : gain marginal capturable sur les gares qui chargent, note cible (+26),
 * production disponible (ville pour passagers/courrier, industrie source pour fret),
 * plafonnee par la capacite disponible de la ligne (saturation). Achat seulement si
 * gain annuel x horizon (5 ans) > cout mesure. Preservation du meilleur
 * projet admissible et financable et de la flotte V252.
 * Aucun etat sauvegarde. La statue est un bit du monde (AITown.HasStatue). */

const V249_HORIZON_YEARS = 5;

/* ESTIM-1 lot 3 (bit 4) : contrat M1 commun aux investissements sur lignes
 * existantes. deltaR est une recette BRUTE, deltaE l'entretien annuel,
 * deltaA l'amortissement annuel des vehicules, deltaC le prix net a payer.
 * La correction de recette est autonome du bit 1 (apprentissage facultatif).
 * Une amelioration peut avoir deltaR/deltaE negatifs : garder leurs signes. */
function OpexEstimVProject(mode, deltaR, deltaE, deltaA, deltaC, kDec = -1, modeRevenues = null, distance = 0)
{
  local kR = mode == "rail" && (ESTIM_UNIFIE & 16) != 0 ? OpexEstimRailRevenueFactor(distance)
      : ((mode in ESTIM_K_R) ? ESTIM_K_R[mode] : 1.0);
  local calibrated = kR * deltaR;
  if (modeRevenues != null) {
    calibrated = 0.0;
    foreach (revenueMode, revenue in modeRevenues)
      calibrated += revenue * ((revenueMode in ESTIM_K_R) ? ESTIM_K_R[revenueMode] : 1.0);
  }
  local deltaP = (calibrated - deltaE - deltaA).tointeger();
  if (kDec < 0) kDec = OpexC69ComputeKDec().K_dec;
  local capital = deltaC > 0 ? deltaC : 0;
  local denominator = capital > kDec ? capital : kDec;
  return { mode = mode, deltaR = deltaR, deltaE = deltaE, deltaA = deltaA,
      deltaC = deltaC, deltaP = deltaP, score = OpexProjectScore(deltaP, denominator) };
}

function OpexEstimVLog(kind, id, project)
{
  if (!DECISION_LOG || project == null) return;
  OpexDecide("ESTIM_VPROJECT", "kind=" + kind + " id=" + id
      + " mode=" + project.mode + " deltaR=" + project.deltaR
      + " deltaE=" + project.deltaE + " deltaA=" + project.deltaA
      + " deltaC=" + project.deltaC + " deltaP=" + project.deltaP
      + " score=" + project.score);
}

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

/* V249 mode 2 : capital du meilleur projet admissible et financable maintenant dans projects.best */
function OpexV249BestAdmissibleCapital(projects, lines, currentCash)
{
  if (projects == null || !("best" in projects) || projects.best == null) return 0;
  foreach (project in projects.best) {
    if (project == null) continue;
    if (!OpexModeVehicleRoom(project.mode, OpexTensionProjectVehicleCount(project))) continue;
    if (project.mode == "air" && !OpexAirBatchPlanStillLive(project.payload, lines)) continue;
    local cap = OpexProjectFinanceCapital(project);
    if (cap > 0 && cap <= currentCash) {
      return cap;
    }
  }
  return 0;
}

/* V249 mode 2 : cout du renouvellement V252 en attente sur une ligne rentable (ne pas l'evincer) */
function OpexV249GetPendingV252Cost(ai)
{
  if (ai == null || ai._lines == null || ai._lines.len() == 0 || ai._catalog == null) return 0;
  local loan = AICompany.GetLoanAmount();
  if (loan > 0) return 0;
  if (V252_CASH_STOP) return 0;

  local candidates = [];
  local rank = 0;
  foreach (line in ai._lines) {
    if (line == null) continue;
    if (("mode" in line) && line.mode != "air") continue;
    if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) continue;
    if (("scrapping" in line) && line.scrapping) continue;

    local lineProfit = 0;
    foreach (v in line.vehicles) {
      if (AIVehicle.IsValidVehicle(v)) lineProfit += AIVehicle.GetProfitLastYear(v);
    }
    if (lineProfit <= 0) continue;

    foreach (v in line.vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (ai._vehiclesToRetire != null && (v in ai._vehiclesToRetire)) continue;
      candidates.append({
        veh = v,
        line = line,
        age = AIVehicle.GetAge(v),
        profit = AIVehicle.GetProfitLastYear(v),
        engine = AIVehicle.GetEngineType(v),
        rank = rank++
      });
    }
  }
  if (candidates.len() == 0) return 0;

  candidates.sort(function(a, b) {
    if (a.age != b.age) return a.age > b.age ? -1 : 1;
    if (a.profit != b.profit) return a.profit < b.profit ? -1 : 1;
    if (a.rank != b.rank) return a.rank < b.rank ? -1 : 1;
    return 0;
  });

  local lineTargetCache = {};
  foreach (cand in candidates) {
    local lineKey = ("lineId" in cand.line) ? cand.line.lineId : cand.line;
    if (!(lineKey in lineTargetCache)) {
      lineTargetCache[lineKey] <- OpexAirBestEngineForLine(cand.line, ai._catalog);
    }
    local targetEngine = lineTargetCache[lineKey];
    if (targetEngine == null || cand.engine == targetEngine) continue;

    local airportTile = ("originA" in cand.line) && AIAirport.IsAirportTile(cand.line.originA)
        ? cand.line.originA : cand.line.stationA;
    local hangar = AIAirport.GetHangarOfAirport(airportTile);
    if (!AIMap.IsValidTile(hangar) || !AIAirport.IsHangarTile(hangar)) continue;

    local price = AIEngine.GetPrice(targetEngine);
    if (price > 0) return price;
  }
  return 0;
}

function OpexV249LineProfit(line)
{
  local stationId = OpexLineStationId(line, "A");
  if (stationId < 0) stationId = OpexLineStationId(line, "B");
  local vehicles = null;
  if (stationId >= 0) {
    vehicles = OpexLineVehicleIds(line, stationId);
  } else if (("vehicles" in line) && line.vehicles != null) {
    vehicles = line.vehicles;
  } else {
    return 0;
  }
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

/* Capacite disponible et revenu unitaire estime d'une ligne pour un cargo donne */
function OpexV249LineServiceInfo(line, stationId, cargo)
{
  local vehicles = OpexLineVehicleIds(line, stationId);
  local totalVehCap = 0;
  local vehCount = 0;
  if (vehicles != null) {
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      totalVehCap += AIVehicle.GetCapacity(v, cargo);
      vehCount++;
    }
  }
  if (vehCount == 0 || totalVehCap <= 0) {
    return { spareCapacity = 0, unitRevenue = 0.0 };
  }

  local waiting = AIStation.GetCargoWaiting(stationId, cargo);
  if (waiting > totalVehCap * 2) {
    return { spareCapacity = 0, unitRevenue = 0.0 };
  }

  local oneWayDays = 0;
  if (("predOneWayDays" in line) && line.predOneWayDays > 0) {
    oneWayDays = line.predOneWayDays;
  } else if (("distance" in line) && line.distance > 0) {
    oneWayDays = line.distance;
  } else {
    oneWayDays = 30;
  }
  local roundTripDays = 2 * oneWayDays;
  if (roundTripDays < 1) roundTripDays = 1;
  local annualTrips = 365.0 / roundTripDays;
  local annualCapacity = (totalVehCap * annualTrips).tointeger();

  /* predCarried est mensuel (economy.nut, air_economics_c121.nut : capacite par mois) ; le reste
   * du calcul est annuel. */
  local currentCarried = ("predCarried" in line && line.predCarried > 0) ? line.predCarried * 12 : 0;
  local spareCapacity = annualCapacity - currentCarried;
  if (spareCapacity < 0) spareCapacity = 0;

  local profit = OpexV249LineProfit(line);
  local unitRevenue = 0.0;
  if (profit > 0 && currentCarried > 0) {
    unitRevenue = profit.tofloat() / currentCarried;
    if ((ESTIM_UNIFIE & 4) != 0) {
      local expenses = 0;
      foreach (vehicle in vehicles)
        if (AIVehicle.IsValidVehicle(vehicle)) expenses += AIVehicle.GetRunningCost(vehicle);
      unitRevenue = (profit + expenses).tofloat() / currentCarried;
    }
  } else if (("predRevenue" in line) && line.predRevenue > 0 && ("predCarried" in line) && line.predCarried > 0) {
    unitRevenue = line.predRevenue.tofloat() / (line.predCarried * 12);
  } else if (("predicted" in line) && line.predicted > 0 && ("predCarried" in line) && line.predCarried > 0) {
    unitRevenue = line.predicted.tofloat() / (line.predCarried * 12);
  }

  return { spareCapacity = spareCapacity, unitRevenue = unitRevenue };
}

/* V249 mode 2 : gain marginal capturable (V249a + V249b + V249c) */
function OpexV249DispatchMode2(ai, ym, year)
{
  local byTownCargoStation = {};
  local nLines = 0;
  if (ai._lines != null) {
    foreach (line in ai._lines) {
      if (line == null) continue;
      nLines++;
      local isFreight = (("kind" in line) && line.kind == "freight");
      local cargos = [line.cargo];
      if (("cargo2" in line) && line.cargo2 >= 0 && line.cargo2 != line.cargo) {
        cargos.append(line.cargo2);
      }

      foreach (cg in cargos) {
        if (!AICargo.IsValidCargo(cg)) continue;
        local loadingEnds = [];
        if (isFreight) {
          loadingEnds.append("A");
        } else {
          loadingEnds.append("A");
          loadingEnds.append("B");
        }

        foreach (endName in loadingEnds) {
          local stationId = OpexLineStationId(line, endName);
          if (stationId < 0 || !AIStation.IsValidStation(stationId)) continue;
          if (!AIStation.HasCargoRating(stationId, cg)) continue;
          local townId = AIStation.GetNearestTown(stationId);
          if (!AITown.IsValidTown(townId)) continue;

          if (!(townId in byTownCargoStation)) byTownCargoStation[townId] <- {};
          if (!(cg in byTownCargoStation[townId])) byTownCargoStation[townId][cg] <- {};
          if (!(stationId in byTownCargoStation[townId][cg])) {
            byTownCargoStation[townId][cg][stationId] <- [];
          }
          byTownCargoStation[townId][cg][stationId].append(line);
        }
      }
    }
  }

  local bestTown = -1;
  local bestGain = 0;
  local bestStation = -1;
  local bestCargo = -1;
  local bestRating = -1;
  local bestProd = 0;
  local bestProject = null;
  local found = false;
  local nStatue = 0;
  local nUnavail = 0;
  local nTowns = 0;
  local kDec = (ESTIM_UNIFIE & 4) != 0 ? OpexC69ComputeKDec().K_dec : -1;

  foreach (townId, cargoMap in byTownCargoStation) {
    nTowns++;
    if (AITown.HasStatue(townId)) {
      nStatue++;
      continue;
    }
    if (!AITown.IsActionAvailable(townId, AITown.TOWN_ACTION_BUILD_STATUE)) {
      nUnavail++;
      continue;
    }

    local townGain = 0;
    local townModeRevenues = {};
    local topSt = -1;
    local topCg = -1;
    local topRt = -1;
    local topPr = 0;
    local topStGain = -1;

    foreach (cg, stations in cargoMap) {
      local isPax = AICargo.HasCargoClass(cg, AICargo.CC_PASSENGERS) || AICargo.HasCargoClass(cg, AICargo.CC_MAIL);
      local prodMonthly = 0;
      if (isPax) {
        prodMonthly = AITown.GetLastMonthProduction(townId, cg);
      } else {
        foreach (stId, linesList in stations) {
          foreach (line in linesList) {
            local ind = ("srcIndustry" in line && AIIndustry.IsValidIndustry(line.srcIndustry))
                ? line.srcIndustry
                : (("originA" in line) ? AIIndustry.GetIndustryID(line.originA) : -1);
            if (AIIndustry.IsValidIndustry(ind)) {
              local p = AIIndustry.GetLastMonthProduction(ind, cg);
              if (p > prodMonthly) prodMonthly = p;
            }
            if (prodMonthly <= 0 && ("monthly" in line) && line.monthly > prodMonthly) {
              prodMonthly = line.monthly;
            }
          }
        }
      }
      if (prodMonthly <= 0) continue;
      local annualProd = prodMonthly * 12;
      local maxTownExtra = (annualProd * 26) / 256;

      local cargoExtraTotal = 0;
      local cargoRevSum = 0.0;
      local cargoModeRevenues = {};

      foreach (stId, linesList in stations) {
        local ratingPct = AIStation.GetCargoRating(stId, cg);
        if (ratingPct < 0) continue;
        local curByte = OpexC121RatingPercentToByteMid(ratingPct);
        local targetByte = curByte + 26;
        if (targetByte > 255) targetByte = 255;
        local deltaByte = targetByte - curByte;
        if (deltaByte <= 0) continue;

        local stationDeltaCargo = (annualProd * deltaByte) / 256;
        local stationSpareCap = 0;
        local stationRevWeighted = 0.0;

        foreach (line in linesList) {
          local sInfo = OpexV249LineServiceInfo(line, stId, cg);
          stationSpareCap += sInfo.spareCapacity;
          stationRevWeighted += sInfo.spareCapacity * sInfo.unitRevenue;
        }

        if (stationSpareCap <= 0) continue;
        local stationAvgUnitRev = stationRevWeighted / stationSpareCap;
        local deliverableStation = stationDeltaCargo < stationSpareCap ? stationDeltaCargo : stationSpareCap;
        if (deliverableStation <= 0) continue;

        local stGain = (deliverableStation * stationAvgUnitRev).tointeger();
        if (stGain > topStGain) {
          topStGain = stGain;
          topSt = stId;
          topCg = cg;
          topRt = ratingPct;
          topPr = prodMonthly;
        }

        cargoExtraTotal += deliverableStation;
        cargoRevSum += deliverableStation * stationAvgUnitRev;
        if ((ESTIM_UNIFIE & 4) != 0) {
          foreach (line in linesList) {
            local sInfo = OpexV249LineServiceInfo(line, stId, cg);
            local mode = ("mode" in line) ? line.mode : "unknown";
            if (!(mode in cargoModeRevenues)) cargoModeRevenues.rawset(mode, 0.0);
            cargoModeRevenues[mode] += deliverableStation * sInfo.spareCapacity
                * sInfo.unitRevenue / stationSpareCap;
          }
        }
      }

      if (cargoExtraTotal <= 0) continue;
      local deliverableCargoTown = cargoExtraTotal < maxTownExtra ? cargoExtraTotal : maxTownExtra;
      local avgCargoUnitRev = cargoRevSum / cargoExtraTotal;
      townGain += (deliverableCargoTown * avgCargoUnitRev).tointeger();
      if ((ESTIM_UNIFIE & 4) != 0)
        foreach (mode, revenue in cargoModeRevenues) {
          if (!(mode in townModeRevenues)) townModeRevenues.rawset(mode, 0.0);
          townModeRevenues[mode] += revenue * deliverableCargoTown / cargoExtraTotal;
        }
    }

    if (townGain <= 0) continue;
    local statueProject = null;
    if ((ESTIM_UNIFIE & 4) != 0) {
      local statueCost = OpexV249MeasureStatueCost(townId);
      statueProject = OpexEstimVProject("mixed", townGain, 0, 0, statueCost,
          kDec, townModeRevenues);
      if (statueProject.deltaP <= 0 || statueProject.deltaC <= 0) continue;
    }
    if (!found || ((ESTIM_UNIFIE & 4) != 0
        ? (statueProject.score > bestProject.score
          || (statueProject.score == bestProject.score && townId < bestTown))
        : (townGain > bestGain || (townGain == bestGain && townId < bestTown)))) {
      found = true;
      bestTown = townId;
      bestGain = townGain;
      bestProject = statueProject;
      bestStation = topSt;
      bestCargo = topCg;
      bestRating = topRt;
      bestProd = topPr;
    }
  }

  if (!found) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=no_town statue=" + nStatue + " unavailable=" + nUnavail + " towns=" + nTowns + " lines=" + nLines);
    return true;
  }

  local cost = OpexV249MeasureStatueCost(bestTown);
  local bestCargoLabel = AICargo.IsValidCargo(bestCargo) ? AICargo.GetCargoLabel(bestCargo) : "unknown";

  if ((ESTIM_UNIFIE & 4) != 0) {
    local project = bestProject;
    project.deltaC = cost;
    OpexEstimVLog("V249", bestTown, project);
    if (project.deltaP <= 0 || project.deltaC <= 0) {
      if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=estim_margin town=" + bestTown + " deltaP=" + project.deltaP);
      return true;
    }
  }

  if ((ESTIM_UNIFIE & 4) == 0 && bestGain * V249_HORIZON_YEARS <= cost) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=payback town=" + bestTown + " station=" + bestStation + " cargo=" + bestCargoLabel + " rating=" + bestRating + " prod=" + bestProd + " gain=" + bestGain + " cost=" + cost + " horizon=" + V249_HORIZON_YEARS);
    return true;
  }

  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local bestProjCap = OpexV249BestAdmissibleCapital(ai._projects, ai._lines, cash);
  local v252Cost = OpexV249GetPendingV252Cost(ai);
  local threshold = bestProjCap + v252Cost;
  if ((ESTIM_UNIFIE & 2) != 0)
    threshold = 0;

  if (cost <= 0 || cash - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cost town=" + bestTown + " station=" + bestStation + " cargo=" + bestCargoLabel + " rating=" + bestRating + " prod=" + bestProd + " gain=" + bestGain + " cost=" + cost + " cash=" + cash + " threshold=" + threshold + " best_proj=" + bestProjCap + " v252=" + v252Cost);
    return true;
  }

  local built = AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_BUILD_STATUE);
  if (!built) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=failed town=" + bestTown + " station=" + bestStation + " cargo=" + bestCargoLabel + " rating=" + bestRating + " prod=" + bestProd + " gain=" + bestGain + " cost=" + cost + " cash=" + cash + " threshold=" + threshold);
    return true;
  }

  if (DECISION_LOG) OpexDecide("V249_STATUE", "town=" + bestTown + " station=" + bestStation + " cargo=" + bestCargoLabel + " rating=" + bestRating + " prod=" + bestProd + " gain=" + bestGain + " cost=" + cost + " cash=" + cash + " threshold=" + threshold + " horizon=" + V249_HORIZON_YEARS);
  return true;
}

function OpexAI::_dispatchV249Statue(task, year)
{
  if (!V249_STATUE) return false;
  local date = AIDate.GetCurrentDate();
  local ym = year * 12 + AIDate.GetMonth(date);
  if (this._v249StatueMonth == ym) return false;
  this._v249StatueMonth = ym;

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

  if (V249_STATUE == 2 || (ESTIM_UNIFIE & 4) != 0) {
    return OpexV249DispatchMode2(this, ym, year);
  }

  local byTown = {};
  local nLines = 0;
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

  local bestTown = -1;
  local bestProfit = 0;
  local bestLines = 0;
  local found = false;
  local nStatue = 0;
  local nUnavail = 0;
  local nTowns = 0;
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
  if (!found) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=no_town statue=" + nStatue + " unavailable=" + nUnavail + " towns=" + nTowns + " lines=" + nLines);
    return true;
  }

  local cost = OpexV249MeasureStatueCost(bestTown);
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local threshold = OpexV249MaxListedCapital(this._projects);
  if ((ESTIM_UNIFIE & 2) != 0)
    threshold = 0;
  if (cost <= 0 || cash - cost < threshold) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=cost cash=" + cash + " cost=" + cost + " threshold=" + threshold + " town=" + bestTown);
    return true;
  }
  local built = AITown.PerformTownAction(bestTown, AITown.TOWN_ACTION_BUILD_STATUE);
  if (!built) {
    if (DECISION_LOG) OpexDecide("V249_SKIP", "reason=failed town=" + bestTown + " cost=" + cost + " cash=" + cash + " threshold=" + threshold);
    return true;
  }
  if (DECISION_LOG) OpexDecide("V249_STATUE", "town=" + bestTown + " cost=" + cost + " cash=" + cash + " threshold=" + threshold + " lines=" + bestLines + " profit=" + bestProfit);
  return true;
}
