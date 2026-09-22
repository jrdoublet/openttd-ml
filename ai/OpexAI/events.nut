/* C65 : deplace depuis main.nut (passe 1, deplacement pur, aucun corps retouche). */
/* Compte avant toute branche de _processEvents : les continue existants ne doivent jamais
 * rendre un evenement invisible. Les conversions restent limitees au seul ID necessaire pour
 * dedoublonner ET_VEHICLE_UNPROFITABLE dans la fenetre annuelle. */
function OpexC52EventExposureObserve(event, eventType)
{
  if (!C52_EVENT_EXPOSURE_PROBE || C52_EVENT_EXPOSURE_LEDGER == null) return;
  local entry = C52_EVENT_EXPOSURE_LEDGER;
  if (eventType == AIEvent.ET_VEHICLE_CRASHED) {
    entry.vehicle_crashed++;
    local crash = AIEventVehicleCrashed.Convert(event);
    if (crash != null && crash.GetCrashReason() == AIEventVehicleCrashed.CRASH_TRAIN) {
      entry.crashed_train++;
    } else entry.crashed_other++;
  } else if (eventType == AIEvent.ET_VEHICLE_WAITING_IN_DEPOT) entry.vehicle_waiting_in_depot++;
  else if (eventType == AIEvent.ET_INDUSTRY_OPEN) entry.industry_open++;
  else if (eventType == AIEvent.ET_INDUSTRY_CLOSE) entry.industry_close++;
  else if (eventType == AIEvent.ET_TOWN_FOUNDED) entry.town_founded++;
  else if (eventType == AIEvent.ET_ENGINE_AVAILABLE) entry.engine_available++;
  else if (eventType == AIEvent.ET_VEHICLE_LOST) entry.vehicle_lost++;
  else if (eventType == AIEvent.ET_SUBSIDY_OFFER) entry.subsidy_offer++;
  else if (eventType == AIEvent.ET_SUBSIDY_OFFER_EXPIRED) entry.subsidy_offer_expired++;
  else if (eventType == AIEvent.ET_SUBSIDY_AWARDED) entry.subsidy_awarded++;
  else if (eventType == AIEvent.ET_SUBSIDY_EXPIRED) entry.subsidy_expired++;
  else if (eventType == AIEvent.ET_VEHICLE_AUTOREPLACED) entry.vehicle_autoreplaced++;
  else if (eventType == AIEvent.ET_VEHICLE_UNPROFITABLE) {
    entry.vehicle_unprofitable++;
    local unprofitable = AIEventVehicleUnprofitable.Convert(event);
    if (unprofitable != null) entry.unprofitable_vehicles.rawset(unprofitable.GetVehicleID(), true);
  } else if (eventType == AIEvent.ET_AIRCRAFT_DEST_TOO_FAR) entry.aircraft_dest_too_far++;
  else if (eventType == AIEvent.ET_STATION_FIRST_VEHICLE) entry.station_first_vehicle++;
  else if (eventType == AIEvent.ET_ROAD_RECONSTRUCTION) entry.road_reconstruction++;
  else if (eventType == AIEvent.ET_ENGINE_PREVIEW) entry.engine_preview++;
  else if (eventType == AIEvent.ET_EXCLUSIVE_TRANSPORT_RIGHTS) entry.exclusive_transport_rights++;
  else entry.other++;
}
/* C39.0 : note une invalidation sans la consommer. Les listes sont volontairement passees par
 * valeur, ce qui garde l'etat serialisable et le routeur sans dependance aux objets de plan.
 * Cette tranche ne change AUCUN dueCycle, ni `_portfolioInvalidated`, ni un candidat. */
function OpexAI::_markDirty(reason, catalogLayers = null, candidateLayers = null,
                            portfolio = false, selection = false, affectedKind = null,
                            affectedId = -1, affectedMode = null, targetedRelevant = true)
{
  local functional = C80_DOUBLE_REGISTER && (C76_REGEN_TARGETED || C77_OPPORTUNISTIC_CANDIDATES);
  if ((!C39_INVALIDATION_PROBE && !functional) || this._staleness == null) return;
  local revisionTracking = C41_REVISION_PROBE || functional;
  local revisionBumped = false;
  if (C39_DECISION_DELTA_PROBE && !this._staleness.topBeforeCaptured) {
    this._staleness.topBefore = OpexC39ProjectSignature(this._projects);
    this._staleness.topBeforeCaptured = true;
  }
  if (catalogLayers != null) {
    foreach (layer in catalogLayers) {
      if (layer in this._staleness.catalog) {
        if (revisionTracking && targetedRelevant && !this._staleness.catalog[layer]) {
          this._staleness.revisions.catalog[layer]++;
          this._staleness.dirtySince.catalog[layer] = AIDate.GetCurrentDate();
          if (layer == "water") {
            this._staleness.waterCatalogDirtyDate = AIDate.GetCurrentDate();
            this._staleness.waterCatalogDirtyTick = AIController.GetTick();
          }
          revisionBumped = true;
        }
        this._staleness.catalog[layer] = true;
      }
    }
  }
  if (candidateLayers != null) {
    foreach (layer in candidateLayers) {
      if (layer in this._staleness.candidates) {
        if (revisionTracking && targetedRelevant && !this._staleness.candidates[layer]) {
          this._staleness.revisions.candidates[layer]++;
          this._staleness.dirtySince.candidates[layer] = AIDate.GetCurrentDate();
          revisionBumped = true;
        }
        this._staleness.candidates[layer] = true;
      }
    }
  }
  if (portfolio) {
    if (revisionTracking && targetedRelevant && !this._staleness.portfolio) {
      this._staleness.revisions.portfolio++;
      this._staleness.dirtySince.portfolio = AIDate.GetCurrentDate();
      revisionBumped = true;
    }
    this._staleness.portfolio = true;
  }
  if (selection) {
    if (revisionTracking && targetedRelevant && !this._staleness.selection) {
      this._staleness.revisions.selection++;
      this._staleness.dirtySince.selection = AIDate.GetCurrentDate();
      revisionBumped = true;
    }
    this._staleness.selection = true;
  }
  this._staleness.events++;
  if (reason in this._staleness.reasons) this._staleness.reasons[reason]++;
  else this._staleness.reasons.rawset(reason, 1);
  if (affectedId >= 0) {
    if (affectedKind == "town") this._staleness.towns.rawset("" + affectedId, true);
    else if (affectedKind == "industry") this._staleness.industries.rawset("" + affectedId, true);
    else if (affectedKind == "engine") {
      this._staleness.engines.rawset("" + affectedId, true);
      if (affectedMode != null) this._staleness.engineModes.rawset("" + affectedId, affectedMode);
    }
  }
  OpexC39Log("C39_DIRTY", "reason=" + reason + " catalog=" + (catalogLayers != null ? catalogLayers.len() : 0)
             + " candidates=" + (candidateLayers != null ? candidateLayers.len() : 0)
             + " portfolio=" + (portfolio ? 1 : 0) + " selection=" + (selection ? 1 : 0)
             + " id=" + affectedId);
  if (C41_REVISION_PROBE && revisionBumped) {
    OpexC39Log("C41_REVISION", OpexC41RevisionSnapshot(this._staleness.revisions));
  }
  if (functional && targetedRelevant && candidateLayers != null) {
    local targeted = C77_OPPORTUNISTIC_CANDIDATES
        && affectedId >= 0 && (affectedKind == "town" || affectedKind == "industry")
        && reason != "industry_close";
    local shouldRoute = C76_REGEN_TARGETED
        || (C77_OPPORTUNISTIC_CANDIDATES && (targeted || reason == "engine_available"));
    local modes = [];
    foreach (layer in candidateLayers) {
      if (targeted && affectedKind == "town" && layer == "water") continue;
      modes.append(layer);
    }
    if (shouldRoute && modes.len() > 0) {
      this._c76EnqueueRegen(modes, targeted ? affectedKind : null,
                            targeted ? affectedId : -1, targeted, targeted, reason);
    }
  }
  if (WATER_OPCODE_COMPAT_FALSE && targetedRelevant && catalogLayers != null) {
    /* Ancien armement C41 WATER : branche impossible, conserve seulement le cout du test. */
  }
}
/* C39.0 : photographie coalescée juste avant de jeter l'etat, apres la regeneration mensuelle
 * historique. La signature du premier projet ne sert pas encore a DECIDER : elle donne au
 * diagnostic le resultat auquel les futures invalidations devront etre comparees. */
function OpexAI::_logStalenessRefresh(reason)
{
  if (!C39_INVALIDATION_PROBE || this._staleness == null) return;
  local cat = "";
  foreach (layer in ["cargos", "towns", "industries", "rail", "road", "air", "water"]) {
    if (!this._staleness.catalog[layer]) continue;
    /* `slice`/`substr` differs between Squirrel builds; names explicites gardent la sonde
     * compatible avec l'API embarquee d'OpenTTD. */
    if (layer == "cargos") cat += "c";
    else if (layer == "towns") cat += "t";
    else if (layer == "industries") cat += "i";
    else if (layer == "rail") cat += "r";
    else if (layer == "road") cat += "d";
    else if (layer == "air") cat += "a";
    else if (layer == "water") cat += "w";
  }
  if (cat == "") cat = "-";
  local cand = "";
  foreach (layer in ["rail", "road", "air", "water"]) {
    if (!this._staleness.candidates[layer]) continue;
    if (layer == "rail") cand += "r";
    else if (layer == "road") cand += "d";
    else if (layer == "air") cand += "a";
    else if (layer == "water") cand += "w";
  }
  if (cand == "") cand = "-";
  local towns = 0;
  foreach (key, value in this._staleness.towns) towns++;
  local industries = 0;
  foreach (key, value in this._staleness.industries) industries++;
  local engines = 0;
  foreach (key, value in this._staleness.engines) engines++;
  local top = OpexC39ProjectSignature(this._projects);
  local topBefore = this._staleness.topBeforeCaptured ? this._staleness.topBefore : top;
  local topChanged = topBefore != top;
  local waterAgeDays = this._staleness.waterCatalogDirtyDate >= 0
      ? AIDate.GetCurrentDate() - this._staleness.waterCatalogDirtyDate : -1;
  OpexC39Log("C39_REFRESH", "reason=" + reason + " events=" + this._staleness.events
             + " cat=" + cat + " cand=" + cand + " portfolio=" + (this._staleness.portfolio ? 1 : 0)
             + " selection=" + (this._staleness.selection ? 1 : 0) + " towns=" + towns
             + " industries=" + industries + " engines=" + engines + " top=" + top);
  if (C39_DECISION_DELTA_PROBE && this._staleness.events > 0) {
    OpexC39Log("C39_DECISION_DELTA", "events=" + this._staleness.events + " top_before="
               + topBefore + " top_after=" + top + " top_changed=" + (topChanged ? 1 : 0));
    foreach (engine, mode in this._staleness.engineModes) {
      OpexC39Log("C39_ENGINE_DELTA", "engine=" + engine + " mode=" + mode + " retained="
                 + (OpexC39CatalogUsesEngine(this._catalog, engine.tointeger(), mode) ? 1 : 0)
                 + " top_changed=" + (topChanged ? 1 : 0));
      if (C39_AIR_REASON_PROBE && mode == "air") {
        local engineId = engine.tointeger();
        local planeType = AIEngine.IsValidEngine(engineId) ? AIEngine.GetPlaneType(engineId) : -1;
        local capacity = AIEngine.IsValidEngine(engineId) ? AIEngine.GetCapacity(engineId) : -1;
        OpexC39Log("C39_AIR_ENGINE_REASON", "engine=" + engine + " reason="
                   + OpexC39AirEngineReason(this._catalog, engineId) + " plane_type="
                   + planeType + " capacity=" + capacity);
      }
    }
  }
  /* C41.0 : le rebuild historique vient effectivement de refaire tout le catalogue et le
   * portefeuille ; il peut donc acquitter toutes les couches. Les micro-taches futures ne
   * copieront que leurs propres revisions. */
  if (C41_REVISION_PROBE) {
    /* C41.12 : publier AVANT de remettre les dates a blanc. Seules les revisions reellement
     * marquees ont un horodatage >= 0 ; une invalidation prefiltrée n'est pas un faux age. */
    if (C41_STALENESS_LEDGER) {
      foreach (layer in ["cargos", "towns", "industries", "rail", "road", "air", "water"]) {
        local since = this._staleness.dirtySince.catalog[layer];
        if (since >= 0) {
          OpexC41StalenessLog("C41_STALENESS_ACK", "layer=catalog." + layer + " method=full"
                              + " revision=" + this._staleness.revisions.catalog[layer]
                              + " age_days=" + (AIDate.GetCurrentDate() - since));
        }
      }
      foreach (layer in ["rail", "road", "air", "water"]) {
        local since = this._staleness.dirtySince.candidates[layer];
        if (since >= 0) {
          OpexC41StalenessLog("C41_STALENESS_ACK", "layer=candidates." + layer + " method=full"
                              + " revision=" + this._staleness.revisions.candidates[layer]
                              + " age_days=" + (AIDate.GetCurrentDate() - since));
        }
      }
      if (this._staleness.dirtySince.portfolio >= 0) {
        OpexC41StalenessLog("C41_STALENESS_ACK", "layer=portfolio method=full revision="
                            + this._staleness.revisions.portfolio + " age_days="
                            + (AIDate.GetCurrentDate() - this._staleness.dirtySince.portfolio));
      }
      if (this._staleness.dirtySince.selection >= 0) {
        OpexC41StalenessLog("C41_STALENESS_ACK", "layer=selection method=full revision="
                            + this._staleness.revisions.selection + " age_days="
                            + (AIDate.GetCurrentDate() - this._staleness.dirtySince.selection));
      }
    }
    this._staleness.acknowledged.catalog = {
      cargos = this._staleness.revisions.catalog.cargos, towns = this._staleness.revisions.catalog.towns,
      industries = this._staleness.revisions.catalog.industries, rail = this._staleness.revisions.catalog.rail,
      road = this._staleness.revisions.catalog.road, air = this._staleness.revisions.catalog.air,
      water = this._staleness.revisions.catalog.water,
    };
    this._staleness.acknowledged.candidates = {
      rail = this._staleness.revisions.candidates.rail, road = this._staleness.revisions.candidates.road,
      air = this._staleness.revisions.candidates.air, water = this._staleness.revisions.candidates.water,
    };
    this._staleness.acknowledged.portfolio = this._staleness.revisions.portfolio;
    this._staleness.acknowledged.selection = this._staleness.revisions.selection;
    if (this._staleness.events > 0) {
      OpexC39Log("C41_ACK", "reason=" + reason + " "
                 + OpexC41RevisionSnapshot(this._staleness.acknowledged)
                 + " water_staleness_age_days=" + waterAgeDays);
    }
  }
  this._staleness.catalog = { cargos = false, towns = false, industries = false, rail = false,
                              road = false, air = false, water = false };
  this._staleness.candidates = { rail = false, road = false, air = false, water = false };
  this._staleness.portfolio = false;
  this._staleness.selection = false;
  this._staleness.reasons = {};
  this._staleness.towns = {};
  this._staleness.industries = {};
  this._staleness.engines = {};
  this._staleness.engineModes = {};
  this._staleness.events = 0;
  this._staleness.topBefore = "none";
  this._staleness.topBeforeCaptured = false;
  this._staleness.waterCatalogDirtyDate = -1;
  this._staleness.waterCatalogDirtyTick = -1;
  this._staleness.dirtySince = {
    catalog = { cargos = -1, towns = -1, industries = -1, rail = -1, road = -1, air = -1, water = -1 },
    candidates = { rail = -1, road = -1, air = -1, water = -1 }, portfolio = -1, selection = -1,
  };
}
/* Event moteur exact : CRASH_TRAIN est emis dans train_cmd.cpp au moment ou deux trains
 * entrent en collision. XC garde la ligne, le vehicule, la tuile et les victimes ; RX reste le
 * filet annuel pour toute disparition sans evenement reconnu. */
function OpexAI::_processEvents()
{
  while (AIEventController.IsEventWaiting()) {
    local event = AIEventController.GetNextEvent();
    if (event == null) continue;
    local eventType = event.GetEventType();
    if (C52_EVENT_EXPOSURE_PROBE) OpexC52EventExposureObserve(event, eventType);
    if (C39_INVALIDATION_PROBE) OpexC76ObserveEvent(eventType);

    if (eventType == AIEvent.ET_VEHICLE_CRASHED) {
      this._onVehicleCrashed(event);
      continue;
    }

    if (eventType == AIEvent.ET_VEHICLE_WAITING_IN_DEPOT) {
      continue;
    }

    if (eventType == AIEvent.ET_VEHICLE_AUTOREPLACED) {
      this._onVehicleAutoreplaced(event);
      continue;
    }

    if (eventType == AIEvent.ET_VEHICLE_UNPROFITABLE) {
      this._onVehicleUnprofitable(event);
      continue;
    }

    if (eventType == AIEvent.ET_INDUSTRY_CLOSE) {
      this._onIndustryClose(event);
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_OFFER) {
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_OFFER_EXPIRED) {
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_AWARDED) {
      continue;
    }

    if (eventType == AIEvent.ET_SUBSIDY_EXPIRED) {
      continue;
    }

    if (eventType == AIEvent.ET_VEHICLE_LOST) {
      this._onVehicleLost(event);
      continue;
    }

    if (eventType == AIEvent.ET_INDUSTRY_OPEN) {
      this._onIndustryOpen(event);
      continue;
    }

    if (eventType == AIEvent.ET_TOWN_FOUNDED) {
      this._onTownFounded(event);
      continue;
    }

    if (eventType == AIEvent.ET_ENGINE_AVAILABLE) {
      this._onEngineAvailable(event);
      continue;
    }

    if (eventType == AIEvent.ET_STATION_FIRST_VEHICLE) {
      this._onStationFirstVehicle(event);
      continue;
    }
  }
}
