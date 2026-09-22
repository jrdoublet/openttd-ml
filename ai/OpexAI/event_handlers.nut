/* C65 passe 3 : un handler par type d'evenement, corps deplace depuis
 * _processEvents. Le continue de la boucle reste dans le dispatch. */
function OpexAI::_onVehicleCrashed(event)
{

  local crash = AIEventVehicleCrashed.Convert(event);
  if (crash != null) {
    local vehicle = crash.GetVehicleID();
    local reason = crash.GetCrashReason();
    local site = crash.GetCrashSite();
    local victims = crash.GetVictims();
    local line = OpexFindLineForVehicle(this._lines, vehicle, site);
    local lineId = line != null ? line.lineId : -1;
    local mode = line != null && ("mode" in line) ? line.mode : "unknown";

    if (C52_CRASH_LOG || DECISION_LOG) {
      OpexDecide("VEHICLE_CRASHED", "vehicle=" + vehicle + " reason=" + reason
                 + " mode=" + mode + " line=" + lineId + " site=" + site + " victims=" + victims);
    }

    if (EVENT_VEHICLE_CRASHED) {
      local year = AIDate.GetYear(AIDate.GetCurrentDate());
      OpexSign(AIMap.GetTileIndex(1, 1), "XC|" + (year % 100)
               + "|" + lineId + "|" + vehicle + "|" + AIMap.GetTileX(site) + "|"
               + AIMap.GetTileY(site) + "|" + victims + "|" + reason);

      if (line != null) {
        if (("vehicles" in line) && line.vehicles != null) {
          for (local i = 0; i < line.vehicles.len(); i++) {
            if (line.vehicles[i] == vehicle) {
              line.vehicles.remove(i);
              break;
            }
          }
        }
        if (("vehicle" in line) && line.vehicle == vehicle) {
          line.vehicle = -1;
        }
        if (("scrapVehicles" in line) && line.scrapVehicles != null) {
          for (local i = 0; i < line.scrapVehicles.len(); i++) {
            if (line.scrapVehicles[i] == vehicle) {
              line.scrapVehicles.remove(i);
              break;
            }
          }
        }
        if (("vehCount" in line) && line.vehCount > 0) line.vehCount--;
        if (("trains" in line) && line.trains > 0) line.trains--;
        /* Un evenement crash est confirme. suspectedCrashes est reserve au
         * filet annuel RX; le melanger aux deux faisait compter un crash rail
         * une seconde fois lors de _reportLines. */
        if ("confirmedCrashes" in line) line.confirmedCrashes++;
        else line.confirmedCrashes <- 1;
        if (("mode" in line) && (line.mode == "air" || line.mode == "water" || line.mode == "road")) {
          line.needsRefleet <- true;
        } else if (DECISION_LOG || C52_CRASH_LOG) {
          OpexDecide("CRASH_REFLEET", "mode=" + mode + " line=" + line.lineId + " status=unsupported_consist");
        }
        if (("mode" in line) && line.mode == "rail") {
          /* Le detecteur annuel part du stock apres crash : pas de RX double. */
          local liveAfterCrash = 0;
          if ("vehicles" in line && line.vehicles != null) {
            foreach (known in line.vehicles) {
              if (AIVehicle.IsValidVehicle(known) && AIVehicle.GetVehicleType(known) == AIVehicle.VT_RAIL) liveAfterCrash++;
            }
          }
          line.lastLiveVehicles <- liveAfterCrash;
        }
      }
      if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire)) {
        delete this._vehiclesToRetire[vehicle];
      }
      if (this._unprofitableStreaks != null && (vehicle in this._unprofitableStreaks)) {
        delete this._unprofitableStreaks[vehicle];
      }
    } else if (reason == AIEventVehicleCrashed.CRASH_TRAIN) {
      local year = AIDate.GetYear(AIDate.GetCurrentDate());
      OpexSign(AIMap.GetTileIndex(1, 1), "XC|" + (year % 100)
               + "|" + lineId + "|" + vehicle + "|" + AIMap.GetTileX(site) + "|"
               + AIMap.GetTileY(site) + "|" + victims);
    }
  }
  return;
}
function OpexAI::_onVehicleAutoreplaced(event)
{

  /* Integrite d'inventaire, pas une decision experimentale : le renouvellement
   * automatique est actif par defaut et les VehicleID peuvent etre reutilises.
   * Toujours remapper les references, les sondes ne controlent que le log. */
  {
    local replaceEvt = AIEventVehicleAutoReplaced.Convert(event);
    if (replaceEvt != null) {
      local oldVehicle = replaceEvt.GetOldVehicleID();
      local newVehicle = replaceEvt.GetNewVehicleID();
      local remapLineVehicles = 0;
      local remapLineVehicle = 0;
      local remapScrapVehicles = 0;
      local tracked = false;
      local mode = "unknown";
      foreach (line in this._lines) {
        local lineMode = ("mode" in line) ? line.mode : "unknown";
        if ("vehicles" in line) {
          local hasNew = false;
          foreach (vehicle in line.vehicles) {
            if (vehicle == newVehicle) { hasNew = true; break; }
          }
          local i = 0;
          while (i < line.vehicles.len()) {
            if (line.vehicles[i] != oldVehicle) { i++; continue; }
            tracked = true;
            if (mode == "unknown") mode = lineMode;
            remapLineVehicles++;
            if (hasNew) line.vehicles.remove(i);
            else { line.vehicles[i] = newVehicle; hasNew = true; i++; }
          }
        }
        if (("vehicle" in line) && line.vehicle == oldVehicle) {
          tracked = true;
          if (mode == "unknown") mode = lineMode;
          remapLineVehicle++;
          line.vehicle = newVehicle;
        }
        if ("scrapVehicles" in line) {
          local hasNew = false;
          foreach (vehicle in line.scrapVehicles) {
            if (vehicle == newVehicle) { hasNew = true; break; }
          }
          local i = 0;
          while (i < line.scrapVehicles.len()) {
            if (line.scrapVehicles[i] != oldVehicle) { i++; continue; }
            tracked = true;
            if (mode == "unknown") mode = lineMode;
            remapScrapVehicles++;
            if (hasNew) line.scrapVehicles.remove(i);
            else { line.scrapVehicles[i] = newVehicle; hasNew = true; i++; }
          }
        }
      }
      if (this._vehiclesToRetire != null && (oldVehicle in this._vehiclesToRetire)) {
        local lineId = this._vehiclesToRetire[oldVehicle];
        delete this._vehiclesToRetire[oldVehicle];
        this._vehiclesToRetire.rawset(newVehicle, lineId);
      }
      if (this._unprofitableStreaks != null && (oldVehicle in this._unprofitableStreaks)) {
        local oldStreak = this._unprofitableStreaks[oldVehicle];
        delete this._unprofitableStreaks[oldVehicle];
        if (!(newVehicle in this._unprofitableStreaks) || this._unprofitableStreaks[newVehicle] < oldStreak) {
          this._unprofitableStreaks.rawset(newVehicle, oldStreak);
        }
      }
      if (C52_AUTOREPLACE_LOG && C52_AUTOREPLACE_LEDGER != null) {
        local entry = C52_AUTOREPLACE_LEDGER;
        entry.events++;
        entry.remap_line_vehicles += remapLineVehicles;
        entry.remap_line_vehicle += remapLineVehicle;
        entry.remap_scrap_vehicles += remapScrapVehicles;
        if (!tracked) entry.untracked++;
        /* La ventilation doit venir du VEHICULE, pas de la ligne trouvee : la mesure 16 ans du
         * 2026-09-11 a rendu 33 evenements tous "untracked", donc tous "unknown" -- un mode
         * deduit d'une ligne introuvable n'apprend rien, et c'est precisement le cas qu'il faut
         * diagnostiquer. Le nouvel ID est valide au moment de l'evenement, contrairement a
         * l'ancien. Lecture faite UNIQUEMENT sous sonde : aucun cout en configuration normale. */
        local vType = AIVehicle.IsValidVehicle(newVehicle)
            ? AIVehicle.GetVehicleType(newVehicle) : AIVehicle.VT_INVALID;
        if (vType == AIVehicle.VT_RAIL) entry.rail++;
        else if (vType == AIVehicle.VT_ROAD) entry.road++;
        else if (vType == AIVehicle.VT_AIR) entry.air++;
        else if (vType == AIVehicle.VT_WATER) entry.water++;
        else entry.unknown++;
        if (mode == "rail") entry.line_rail++;
        else if (mode == "road") entry.line_road++;
        else if (mode == "air") entry.line_air++;
        else if (mode == "water") entry.line_water++;
      }
    }
  }
  return;
}
function OpexAI::_onVehicleUnprofitable(event)
{

  if (EVENT_VEHICLE_UNPROFITABLE || C52_UNPROFITABLE_LOG) {
    local unprofitableEvt = AIEventVehicleUnprofitable.Convert(event);
    if (unprofitableEvt != null) {
      local vehicle = unprofitableEvt.GetVehicleID();
      if (AIVehicle.IsValidVehicle(vehicle)) {
        local age = AIVehicle.GetAge(vehicle);
        local profitLast = AIVehicle.GetProfitLastYear(vehicle);
        local line = OpexFindLineForVehicle(this._lines, vehicle);
        local lineId = (line != null && ("lineId" in line)) ? line.lineId : -1;
        local mode = (line != null && ("mode" in line)) ? line.mode
                   : (AIVehicle.GetVehicleType(vehicle) == AIVehicle.VT_ROAD ? "road"
                   : (AIVehicle.GetVehicleType(vehicle) == AIVehicle.VT_RAIL ? "rail"
                   : (AIVehicle.GetVehicleType(vehicle) == AIVehicle.VT_AIR ? "air" : "water")));
        if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
          OpexDecide("VEHICLE_UNPROFITABLE", "vehicle=" + vehicle + " mode=" + mode
                     + " line=" + lineId + " age=" + age + " profit=" + profitLast);
        }

        if (EVENT_VEHICLE_UNPROFITABLE) {
          /* Le vehicule conserve ses ordres pendant son trajet au depot et peut
           * encore etre observe comme deficititaire. Une retraite deja en cours
           * ne doit ni decrementar une seconde fois les compteurs ni reabaisser
           * predTrains. */
          if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire)) return;
          // Garde demarrage : un vehicule en service depuis moins d'un an est encore en montee en charge.
          if (age >= 365) {
            if (this._unprofitableStreaks == null) this._unprofitableStreaks = {};
            local streak = (vehicle in this._unprofitableStreaks)
                ? this._unprofitableStreaks[vehicle] + 1 : 1;
            this._unprofitableStreaks.rawset(vehicle, streak);

            if (streak >= UNPROFITABLE_STREAK_THRESHOLD) {
              if (line != null) {
                local have = ("vehCount" in line) ? line.vehCount
                           : (("vehicles" in line && line.vehicles != null) ? line.vehicles.len()
                           : (("trains" in line) ? line.trains : 1));
                if (have > 1) {
                  /* Ligne multi-vehicules surcapacitaire : retrait unitaire, sans
                   * basculer la ligne dans scrapping. La tache scrap vend ensuite
                   * reellement le vehicule, independamment du traitement annuel de rebut. */
                  if (AIVehicle.SendVehicleToDepot(vehicle)) {
                    local now = AIDate.GetCurrentDate();
                    if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
                    this._vehiclesToRetire.rawset(vehicle, {
                      lineId = line.lineId, startedDate = now, lastSendDate = now, attempts = 1
                    });
                    if ("vehicles" in line && line.vehicles != null) {
                      for (local i = 0; i < line.vehicles.len(); i++) {
                        if (line.vehicles[i] == vehicle) {
                          line.vehicles.remove(i);
                          break;
                        }
                      }
                    }
                    /* Le scalaire est encore consulte par le resolveur. Ne pas
                     * lui laisser l'ID en retraite : prendre un pair vivant ou
                     * la sentinelle deja employee par le handler crash. */
                    if (("vehicle" in line) && line.vehicle == vehicle) {
                      local replacement = -1;
                      if (("vehicles" in line) && line.vehicles != null) {
                        foreach (candidate in line.vehicles) {
                          if (AIVehicle.IsValidVehicle(candidate)) {
                            replacement = candidate;
                            break;
                          }
                        }
                      }
                      line.vehicle = replacement;
                    }
                    if ("vehCount" in line && line.vehCount > 0) line.vehCount--;
                    if ("trains" in line && line.trains > 1) line.trains--;
                    /* Sans cette baisse, _refleetRoadLines reconstruirait au cycle
                     * suivant exactement le vehicule que cette decision vient de retirer. */
                    if ("predTrains" in line && line.predTrains > 1) line.predTrains--;
                    if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
                      OpexDecide("UNPROFITABLE_RETIRE", "action=send vehicle=" + vehicle + " line=" + line.lineId
                                 + " streak=" + streak + " profit=" + profitLast + " remaining=" + have);
                    }
                  } else if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
                    OpexDecide("UNPROFITABLE_RETIRE", "action=depot_refused vehicle=" + vehicle
                               + " line=" + line.lineId + " streak=" + streak);
                  }
                } else {
                  // Ligne a 1 seul vehicule (ou dernier) structurellement deficitaire : fermer la ligne.
                  this._triggerScrapLine(line, "unprofitable");
                  if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
                    OpexDecide("UNPROFITABLE_SCRAP", "line=" + line.lineId + " vehicle=" + vehicle
                               + " streak=" + streak + " profit=" + profitLast);
                  }
                }
              } else {
                // Vehicule orphelin hors ligne
                if (AIVehicle.SendVehicleToDepot(vehicle)) {
                  local now = AIDate.GetCurrentDate();
                  if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
                  this._vehiclesToRetire.rawset(vehicle, {
                    lineId = -1, startedDate = now, lastSendDate = now, attempts = 1
                  });
                  if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
                    OpexDecide("UNPROFITABLE_RETIRE", "action=orphan_send vehicle=" + vehicle
                               + " streak=" + streak + " profit=" + profitLast);
                  }
                } else if (C52_UNPROFITABLE_LOG || DECISION_LOG) {
                  OpexDecide("UNPROFITABLE_RETIRE", "action=orphan_depot_refused vehicle=" + vehicle
                             + " streak=" + streak);
                }
              }
            }
          }
        }
      }
    }
  }
  return;
}
function OpexAI::_onIndustryClose(event)
{

  if (C39_INVALIDATION_PROBE
      || (C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
    local probeEvt = AIEventIndustryClose.Convert(event);
    if (probeEvt != null) {
      this._markDirty("industry_close", ["industries"], ["rail", "road"], true, true,
                      "industry", probeEvt.GetIndustryID());
    }
  }
  return;
}
/* C77 : seul producteur de candidats subventionnes. Les offres ne sont suivies que sous
 * le double registre ; generateur et builder revalident l'offre avant construction. */
function OpexAI::_onSubsidyOffer(event)
{
  if (!C80_DOUBLE_REGISTER || !C77_OPPORTUNISTIC_CANDIDATES) return;
  local subEvt = AIEventSubsidyOffer.Convert(event);
  if (subEvt == null) return;
  local subId = subEvt.GetSubsidyID();
  if (!AISubsidy.IsValidSubsidy(subId)) return;
  local subData = {
    cargo = AISubsidy.GetCargoType(subId),
    srcType = AISubsidy.GetSourceType(subId), srcId = AISubsidy.GetSourceIndex(subId),
    dstType = AISubsidy.GetDestinationType(subId), dstId = AISubsidy.GetDestinationIndex(subId),
    expDate = AISubsidy.GetExpireDate(subId)
  };
  if (this._activeSubsidies != null) this._activeSubsidies.rawset(subId, subData);
  this._enqueueReactive("c77|subsidy|" + subId, "c77_subsidy", { subsidyId = subId });
  if (DECISION_LOG) {
    local matchedLine = OpexSubsidyMatchingLineId(subData, this._lines);
    OpexDecide("SUBSIDY_OFFER", "sub=" + subId + " cargo=" + AICargo.GetCargoLabel(subData.cargo)
        + " src_t=" + subData.srcType + " src=" + subData.srcId
        + " dst_t=" + subData.dstType + " dst=" + subData.dstId + " exp=" + subData.expDate
        + " matched=" + (matchedLine >= 0 ? matchedLine : "none"));
  }
}

/* Offre retiree du suivi : purge des candidats encore au vivier, puis reselection. */
function OpexAI::_c77RemoveSubsidy(subId)
{
  if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
    delete this._activeSubsidies[subId];
  }
  this._purgeSubsidyFromProjects(subId);
  if (this._projects != null) {
    this._projects = OpexReselectProjects(this._projects, OpexAvailableCapital());
    this._ranked = this._projects.rail;
  }
}

function OpexAI::_onSubsidyOfferExpired(event)
{
  if (!C80_DOUBLE_REGISTER || !C77_OPPORTUNISTIC_CANDIDATES) return;
  local subEvt = AIEventSubsidyOfferExpired.Convert(event);
  if (subEvt == null) return;
  local subId = subEvt.GetSubsidyID();
  this._c77RemoveSubsidy(subId);
  if (DECISION_LOG) OpexDecide("SUBSIDY_OFFER_EXPIRED", "sub=" + subId);
}

function OpexAI::_onSubsidyAwarded(event)
{
  if (!C80_DOUBLE_REGISTER || !C77_OPPORTUNISTIC_CANDIDATES) return;
  local subEvt = AIEventSubsidyAwarded.Convert(event);
  if (subEvt == null) return;
  local subId = subEvt.GetSubsidyID();
  local company = AISubsidy.IsValidSubsidy(subId) ? AISubsidy.GetAwardedTo(subId) : -1;
  if (company != AICompany.ResolveCompanyID(AICompany.COMPANY_SELF)) {
    this._c77RemoveSubsidy(subId);
    if (DECISION_LOG) OpexDecide("SUBSIDY_AWARDED", "sub=" + subId + " company=" + company + " is_self=0");
    return;
  }
  /* Gagnee par nous : la ligne existe deja, aucun candidat a purger. */
  if (this._activeSubsidies != null && (subId in this._activeSubsidies)) {
    delete this._activeSubsidies[subId];
  }
  local matchedLine = -1;
  foreach (line in this._lines) {
    if (("isSubsidy" in line) && line.isSubsidy && ("subsidyId" in line) && line.subsidyId == subId) {
      matchedLine = line.lineId;
      line.subsidyAwarded <- true;
      break;
    }
  }
  if (DECISION_LOG) OpexDecide("C42_SUBSIDY_WON", "sub=" + subId + " line=" + matchedLine + " company=" + company);
}

function OpexAI::_onSubsidyExpired(event)
{
  if (!C80_DOUBLE_REGISTER || !C77_OPPORTUNISTIC_CANDIDATES) return;
  local subEvt = AIEventSubsidyExpired.Convert(event);
  if (subEvt == null) return;
  local subId = subEvt.GetSubsidyID();
  this._c77RemoveSubsidy(subId);
  if (DECISION_LOG) OpexDecide("SUBSIDY_EXPIRED", "sub=" + subId);
}
function OpexAI::_onVehicleLost(event)
{

  /* C41.4 : mesurer d'abord la qualite de l'attribution evenement -> ligne avant de
   * concevoir une reparation. La lecture de _lines est volontairement directe : un
   * vehicule absent de cette persistance est un orphelin a compter, pas a deviner via
   * une recherche de stations couteuse. */
  if (C41_VEHICLE_LOST_PROBE) {
    local probeEvt = AIEventVehicleLost.Convert(event);
    if (probeEvt != null) {
      local probeVehicle = probeEvt.GetVehicleID();
      local probeLine = OpexC41PersistedLineForVehicle(this._lines, probeVehicle);
      local probeLineId = probeLine != null ? probeLine.lineId : -1;
      local probeMode = probeLine != null && ("mode" in probeLine) ? probeLine.mode : "orphan";
      local probeValid = AIVehicle.IsValidVehicle(probeVehicle);
      OpexC41VehicleLostLog("vehicle=" + probeVehicle +
                            " valid=" + (probeValid ? 1 : 0) +
                            " line=" + probeLineId + " mode=" + probeMode +
                            " orphan=" + (probeLineId < 0 ? 1 : 0));
      /* C41.5 : seuls les Lost rail attribues et encore vivants ont des ordres et un depot
       * interpretables. `target_line` dit un fait (destination de l'ordre dans les deux
       * gares persistees), jamais que la voie est praticable. */
      if (C41_RAIL_LOST_PROBE && probeValid && probeLine != null && probeMode == "rail") {
        local orderCount = AIOrder.GetOrderCount(probeVehicle);
        local currentOrder = AIOrder.ResolveOrderPosition(probeVehicle, AIOrder.ORDER_CURRENT);
        local orderValid = currentOrder >= 0 && currentOrder < orderCount
            && AIOrder.IsValidVehicleOrder(probeVehicle, currentOrder);
        local target = orderValid ? AIOrder.GetOrderDestination(probeVehicle, currentOrder) : -1;
        local targetStation = AIMap.IsValidTile(target) ? AIStation.GetStationID(target) : -1;
        local stationA = OpexLineStationId(probeLine, "A");
        local stationB = OpexLineStationId(probeLine, "B");
        local targetLine = targetStation == stationA || targetStation == stationB;
        local location = AIVehicle.GetLocation(probeVehicle);
        local depot = ("depot" in probeLine) && probeLine.depot != null ? probeLine.depot : -1;
        local depotValid = AIMap.IsValidTile(depot) && AIRail.IsRailDepotTile(depot);
        OpexC41RailLostLog("vehicle=" + probeVehicle + " line=" + probeLineId
                           + " state=" + AIVehicle.GetState(probeVehicle)
                           + " orders=" + orderCount + " current=" + currentOrder
                           + " order_valid=" + (orderValid ? 1 : 0)
                           + " target=" + target + " target_line=" + (targetLine ? 1 : 0)
                           + " location=" + location
                           + " location_rail=" + (AIMap.IsValidTile(location) && AIRail.IsRailTile(location) ? 1 : 0)
                           + " location_depot=" + (AIMap.IsValidTile(location) && AIRail.IsRailDepotTile(location) ? 1 : 0)
                           + " depot=" + depot + " depot_valid=" + (depotValid ? 1 : 0));
        /* C41.6 : uniquement les attributs deja stockes a la construction/extension. Les
         * compteurs de signaux ne le sont pas ; les inventer ou rescanner le trace serait une
         * autre sonde, pas une propriete de cette ligne. */
        if (C41_RAIL_LOST_TOPOLOGY_PROBE) {
          local depot2 = ("depot2" in probeLine) && probeLine.depot2 != null ? probeLine.depot2 : -1;
          local depot2Valid = AIMap.IsValidTile(depot2) && AIRail.IsRailDepotTile(depot2);
          local vehicleCount = ("vehicles" in probeLine) && probeLine.vehicles != null
              ? probeLine.vehicles.len() : 0;
          OpexC41RailLostTopologyLog("vehicle=" + probeVehicle + " line=" + probeLineId
                                     + " double_track=" + (("doubleTrack" in probeLine && probeLine.doubleTrack == 1) ? 1 : 0)
                                     + " depot2_valid=" + (depot2Valid ? 1 : 0)
                                     + " platform=" + (("platformLength" in probeLine) ? probeLine.platformLength : 0)
                                     + " vehicles=" + vehicleCount
                                     + " trains=" + (("trains" in probeLine) ? probeLine.trains : 0)
                                     + " wagons=" + (("wagons" in probeLine) ? probeLine.wagons : 0)
                                     + " kind=" + (("kind" in probeLine) ? probeLine.kind : "unknown"));
        }
        if (C41_RAIL_LOST_PHYSICAL_PROBE) {
          local approachA = OpexC41RailApproachFacts(("platformA" in probeLine) ? probeLine.platformA : null);
          local approachB = OpexC41RailApproachFacts(("platformB" in probeLine) ? probeLine.platformB : null);
          local approachA2 = OpexC41RailApproachFacts(("platformA2" in probeLine) ? probeLine.platformA2 : null,
                                                      ("stationA2" in probeLine) ? probeLine.stationA2 : null);
          local approachB2 = OpexC41RailApproachFacts(("platformB2" in probeLine) ? probeLine.platformB2 : null,
                                                      ("stationB2" in probeLine) ? probeLine.stationB2 : null);
          local depotFacts = OpexC41RailDepotFrontFacts(depot);
          local depot2Tile = ("depot2" in probeLine) && probeLine.depot2 != null ? probeLine.depot2 : -1;
          local depot2Facts = OpexC41RailDepotFrontFacts(depot2Tile);
          OpexC41RailLostPhysicalLog("vehicle=" + probeVehicle + " line=" + probeLineId
                                     + " a_rail=" + approachA.rail + " a_tracks=" + approachA.tracks + " a_signal=" + approachA.signal
                                     + " b_rail=" + approachB.rail + " b_tracks=" + approachB.tracks + " b_signal=" + approachB.signal
                                     + " a2_rail=" + approachA2.rail + " a2_tracks=" + approachA2.tracks + " a2_signal=" + approachA2.signal
                                     + " b2_rail=" + approachB2.rail + " b2_tracks=" + approachB2.tracks + " b2_signal=" + approachB2.signal
                                     + " depot_front_rail=" + depotFacts.rail + " depot_front_tracks=" + depotFacts.tracks
                                     + " depot2_front_rail=" + depot2Facts.rail + " depot2_front_tracks=" + depot2Facts.tracks);
        }
        if (C41_RAIL_LOST_CONNECTIVITY_PROBE) {
          local exitA = ("platformA" in probeLine && probeLine.platformA != null && ("station_exit" in probeLine.platformA)) ? probeLine.platformA.station_exit : null;
          local exitB = ("platformB" in probeLine && probeLine.platformB != null && ("station_exit" in probeLine.platformB)) ? probeLine.platformB.station_exit : null;
          local leadA = OpexC41RailApproachLead(("platformA" in probeLine) ? probeLine.platformA : null);
          local leadB = OpexC41RailApproachLead(("platformB" in probeLine) ? probeLine.platformB : null);
          local leadA2 = OpexC41RailApproachLead(("platformA2" in probeLine) ? probeLine.platformA2 : null,
                                                 ("stationA2" in probeLine) ? probeLine.stationA2 : null);
          local leadB2 = OpexC41RailApproachLead(("platformB2" in probeLine) ? probeLine.platformB2 : null,
                                                 ("stationB2" in probeLine) ? probeLine.stationB2 : null);
          local a = OpexC41RailLocalLinks(leadA, exitA);
          local b = OpexC41RailLocalLinks(leadB, exitB);
          local a2 = OpexC41RailLocalLinks(leadA2, ("stationA2" in probeLine) ? probeLine.stationA2 : null);
          local b2 = OpexC41RailLocalLinks(leadB2, ("stationB2" in probeLine) ? probeLine.stationB2 : null);
          local front = depotValid ? AIRail.GetRailDepotFrontTile(depot) : null;
          local depotLinks = OpexC41RailLocalLinks(front, depot);
          local depot2 = ("depot2" in probeLine) && probeLine.depot2 != null ? probeLine.depot2 : -1;
          local front2 = AIMap.IsValidTile(depot2) && AIRail.IsRailDepotTile(depot2) ? AIRail.GetRailDepotFrontTile(depot2) : null;
          local depot2Links = OpexC41RailLocalLinks(front2, depot2);
          local vehicleLinks = OpexC41RailLocalLinks(location);
          OpexC41RailLostConnectivityLog("vehicle=" + probeVehicle + " line=" + probeLineId
                                         + " a_branches=" + a.branches + " a_links=" + a.links
                                         + " b_branches=" + b.branches + " b_links=" + b.links
                                         + " a2_branches=" + a2.branches + " a2_links=" + a2.links
                                         + " b2_branches=" + b2.branches + " b2_links=" + b2.links
                                         + " depot_branches=" + depotLinks.branches + " depot_links=" + depotLinks.links
                                         + " depot2_branches=" + depot2Links.branches + " depot2_links=" + depot2Links.links
                                         + " vehicle_rail=" + vehicleLinks.rail + " vehicle_branches=" + vehicleLinks.branches);
        }
        /* C41.8 : l'evenement ne construit rien. Il coalesce l'identite stable de la ligne
         * et reveille la micro-tache qui executera au plus une reparation ciblee. */
        if (C41_RAIL_LOST_SIGNAL_REPAIR && ("doubleTrack" in probeLine) && probeLine.doubleTrack == 1 &&
            this._c41RailSignalLines != null) {
          this._c41RailSignalLines.rawset("" + probeLineId, true);
          if (this._taskQueue != null) {
            foreach (signalTask in this._taskQueue) {
              if (signalTask.name == "c41_rail_signals") {
                signalTask.enabled = true;
                signalTask.dueCycle = this._taskCycle;
                break;
              }
            }
          }
          OpexC41RailSignalRepairLog("C41_RAIL_SIGNAL_ARM", "line=" + probeLineId + " vehicle=" + probeVehicle);
        }
        /* C41.10 : arme independamment de C41.8 -- raccord manquant et signal manquant sont
         * deux causes distinctes du meme VehicleLost. Meme schema de coalescage. */
        if (C41_RAIL_LOST_JUNCTION_REPAIR && ("doubleTrack" in probeLine) && probeLine.doubleTrack == 1 &&
            this._c41RailJunctionLines != null) {
          this._c41RailJunctionLines.rawset("" + probeLineId, true);
          if (this._taskQueue != null) {
            foreach (junctionTask in this._taskQueue) {
              if (junctionTask.name == "c41_rail_junction") {
                junctionTask.enabled = true;
                junctionTask.dueCycle = this._taskCycle;
                break;
              }
            }
          }
          OpexC41RailJunctionRepairLog("C41_RAIL_JUNCTION_ARM", "line=" + probeLineId + " vehicle=" + probeVehicle);
        }
      }
    }
  }
  return;
}
function OpexAI::_onIndustryOpen(event)
{

  if (C39_INVALIDATION_PROBE
      || (C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
    local probeEvt = AIEventIndustryOpen.Convert(event);
    if (probeEvt != null) {
      this._markDirty("industry_open", ["industries"], ["rail", "road"], true, true,
                      "industry", probeEvt.GetIndustryID());
    }
  }
  if (EVENT_CATALOG_INVALIDATE) {
    local indEvt = AIEventIndustryOpen.Convert(event);
    if (indEvt != null) {
      local indId = indEvt.GetIndustryID();
      if (AIIndustry.IsValidIndustry(indId)) {
        local indType = AIIndustry.GetIndustryType(indId);
        if (DECISION_LOG) {
          OpexDecide("EVENT_INDUSTRY_OPEN", "industry=" + indId + " type=" + indType);
        }
        local year = AIDate.GetYear(AIDate.GetCurrentDate());
        OpexSign(AIMap.GetTileIndex(1, 1), "IO|" + (year % 100) + "|" + indId + "|" + indType);
        if (this._catalog != null) {
          this._catalog._refreshIndustries();
        }
        if (!(C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
          this._portfolioInvalidated = true;
          if (this._taskQueue != null) {
            foreach (t in this._taskQueue) {
              if (t.name == "catalog" || t.name == "projects") t.dueCycle = 0;
            }
          }
        }
      }
    }
  }
  return;
}
function OpexAI::_onTownFounded(event)
{

  if (C39_INVALIDATION_PROBE
      || (C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
    local probeEvt = AIEventTownFounded.Convert(event);
    if (probeEvt != null) {
      this._markDirty("town_founded", ["towns"], ["rail", "road", "air", "water"],
                      true, true, "town", probeEvt.GetTownID());
    }
  }
  if (EVENT_CATALOG_INVALIDATE) {
    local townEvt = AIEventTownFounded.Convert(event);
    if (townEvt != null) {
      local townId = townEvt.GetTownID();
      if (AITown.IsValidTown(townId)) {
        local pop = AITown.GetPopulation(townId);
        if (DECISION_LOG) {
          OpexDecide("EVENT_TOWN_FOUNDED", "town=" + townId + " pop=" + pop);
        }
        local year = AIDate.GetYear(AIDate.GetCurrentDate());
        OpexSign(AIMap.GetTileIndex(1, 1), "TF|" + (year % 100) + "|" + townId + "|" + pop);
        if (this._catalog != null) {
          this._catalog._refreshTowns();
        }
        if (!(C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
          this._portfolioInvalidated = true;
          if (this._taskQueue != null) {
            foreach (t in this._taskQueue) {
              if (t.name == "catalog" || t.name == "projects") t.dueCycle = 0;
            }
          }
        }
      }
    }
  }
  return;
}
function OpexAI::_onEngineAvailable(event)
{

  this._recomputeEpochBounds = true;
  if (this._catalog != null) OpexRefreshEpochBounds(this._catalog);
  if (C39_INVALIDATION_PROBE || C39_ENGINE_REFRESH
      || (C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
    local engineEvt = AIEventEngineAvailable.Convert(event);
    if (engineEvt != null) {
      local engine = engineEvt.GetEngineID();
      local vehicleType = AIEngine.IsValidEngine(engine) ? AIEngine.GetVehicleType(engine) : -1;
      local mode = null;
      if (vehicleType == AIVehicle.VT_RAIL) mode = "rail";
      else if (vehicleType == AIVehicle.VT_ROAD) mode = "road";
      else if (vehicleType == AIVehicle.VT_AIR) mode = "air";
      else if (vehicleType == AIVehicle.VT_WATER) mode = "water";
      if (mode != null) {
        /* La sonde reste la seule à conserver l'état/les IDs. C39.2 consomme le chemin
         * historique sans changer les cas industrie déjà couverts par P3. */
        if (C39_INVALIDATION_PROBE || (C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
          local targetedRelevant = !(WATER_OPCODE_COMPAT_FALSE && WATER_OPCODE_COMPAT_FALSE
              && mode == "water");
          this._markDirty("engine_available", [mode], [mode], true, true, "engine", engine,
                          mode, targetedRelevant);
        }
        if (C39_ENGINE_REFRESH
            && !(C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES))) {
          this._portfolioInvalidated = true;
          if (this._taskQueue != null) {
            foreach (t in this._taskQueue) {
              if (t.name == "catalog" || t.name == "projects") t.dueCycle = 0;
            }
          }
        }
      }
    }
  }
  return;
}
function OpexAI::_onStationFirstVehicle(event)
{

  if (C52_STATION_FIRST_VEHICLE_LOG || DECISION_LOG) {
    local sfv = AIEventStationFirstVehicle.Convert(event);
    if (sfv != null) {
      local stId = sfv.GetStationID();
      local vehId = sfv.GetVehicleID();
      local stLoc = AIStation.IsValidStation(stId) ? AIStation.GetLocation(stId) : -1;
      local isOurStation = (stLoc >= 0) && AICompany.IsMine(AITile.GetOwner(stLoc));
      if (isOurStation) {
        local vehType = AIVehicle.IsValidVehicle(vehId) ? AIVehicle.GetVehicleType(vehId) : -1;
        local mode = (vehType == AIVehicle.VT_RAIL) ? "rail"
                   : ((vehType == AIVehicle.VT_ROAD) ? "road"
                   : ((vehType == AIVehicle.VT_AIR) ? "air"
                   : ((vehType == AIVehicle.VT_WATER) ? "water" : "unknown")));

        local line = OpexFindLineForVehicle(this._lines, vehId);
        local lineId = line != null ? (("id" in line) ? line.id : (("lineId" in line) ? line.lineId : -1)) : -1;
        local cargo = (line != null && ("cargo" in line)) ? line.cargo : (AIVehicle.IsValidVehicle(vehId) ? AIEngine.GetCargoType(AIVehicle.GetEngineType(vehId)) : -1);
        local cargoStr = AICargo.IsValidCargo(cargo) ? AICargo.GetCargoLabel(cargo) : "none";
        local lineKind = (line != null && ("kind" in line)) ? line.kind
                       : (AICargo.IsValidCargo(cargo) && AICargo.HasCargoClass(cargo, AICargo.CC_PASSENGERS) ? "pax" : "freight");

        local initialRating = (AICargo.IsValidCargo(cargo) && AIStation.HasCargoRating(stId, cargo)) ? AIStation.GetCargoRating(stId, cargo) : -1;

        OpexDecide("STATION_FIRST_VEHICLE", "station=" + stId + " vehicle=" + vehId
                   + " mode=" + mode + " kind=" + lineKind + " cargo=" + cargoStr
                   + " line=" + lineId + " rating=" + initialRating
                   + " tile=" + stLoc);
      }
    }
  }
  return;
}
