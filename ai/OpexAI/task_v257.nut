/* V257 : file reactive rail privee, round-robin O(1) sur les lignes.
 * Aucun appel depuis le chemin OFF hormis la garde dans _runOrchestratorTick.
 * Les deltas de dechargement sont une borne observee, PAS un compteur exhaustif.
 * Physique et cadence : helpers catalogue/economie existants uniquement. */

function OpexV257Engine(engine, cargo, wagon)
{
  local weight = AIEngine.GetWeight(engine);
  local capacity = AIEngine.GetCapacity(engine);
  local cargoWeight = wagon ? AICargo.GetWeight(cargo, capacity) : 0;
  if (wagon && AICargo.IsFreight(cargo)) cargoWeight *= AIGameSettings.GetValue("vehicle.freight_trains");
  return {
    id = engine, speed = AIEngine.GetMaxSpeed(engine), power = AIEngine.GetPower(engine),
    weight = weight, tractiveEffort = AIEngine.GetMaxTractiveEffort(engine),
    price = AIEngine.GetPrice(engine), runningCost = AIEngine.GetRunningCost(engine),
    ageYears = AIEngine.GetMaxAge(engine) / 365, capacity = capacity,
    fullWeight = weight + cargoWeight
  };
}

/* train_cmd.cpp:184-188 : cached_max_speed est le min des vitesses non nulles.
 * Un wagon ne compte que si vehicle.wagon_speed_limits est actif ; une vitesse
 * 0 signifie « pas de plafond », pas un min a zero. economy.cpp:1747-1764
 * copie ensuite ce cache dans last_speed, tronque a un uint8. GetMaxSpeed rail
 * est deja cette unite (engine.cpp:360, km-ish/h), avant le plafond.
 * OpexRailCruiseSpeed ignore aussi le 0, mais c'est une vitesse de trajet :
 * elle ne plaque pas a 255 et ne lit pas le reglage. */
function OpexV257WagonSpeedLimits()
{
  if (!AIGameSettings.IsValid("vehicle.wagon_speed_limits")) return false;
  return AIGameSettings.GetValue("vehicle.wagon_speed_limits") != 0;
}

function OpexV257ConsistLastSpeed(loco, wagon, wagonLimits)
{
  local speed = loco.speed;
  if (wagonLimits && wagon != null && wagon.speed > 0 && wagon.speed < speed) speed = wagon.speed;
  if (speed > 255) speed = 255;
  if (speed < 0) speed = 0;
  return speed;
}

/* station_cmd.cpp:4048-4049 : rating += (last_speed - 85) >> 2 si last_speed >= 85.
 * OpexC121SpeedRatingPoints est ce meme terme APRES conversion avion
 * (plane_speed, puis * 10 / 128). L'appeler avec une vitesse rail fausserait
 * les points. OpexStationRatingForHeadway ne fait varier que le ramassage
 * d'une ligne neuve et ecraserait la note observee. */
function OpexV257SpeedRatingPoints(lastSpeed)
{
  if (lastSpeed > 255) lastSpeed = 255;
  if (lastSpeed <= 85) return 0;
  return (lastSpeed - 85) >> 2;
}

/* Note prevue = note observee (octet, via l'inverse deja livre) + ecart de
 * points de vitesse. MoveGoodsToStation, gare seule (station_cmd.cpp:4629-4632)
 * puis UpdateStationWaiting (station_cmd.cpp:4411, amount >>= 8) :
 * production captee = production * (note + 1) / 256. La demande observee est
 * deja cette part. Le ratio (note_prevue + 1) / (note_observee + 1) reutilise
 * OpexC121StationAllocatedMonthly, cas sans concurrent. note 0 exclut la gare
 * (station_cmd.cpp:4584). Meme vitesse : la demande observee, sans derivee. */
function OpexV257CapturedMonthly(monthly, ratingPercent, serviceSpeed, planSpeed)
{
  if (monthly <= 0 || ratingPercent < 0) return monthly;
  if (planSpeed == serviceSpeed) return monthly;
  local observed = OpexC121RatingPercentToByteMid(ratingPercent);
  local predicted = observed + OpexV257SpeedRatingPoints(planSpeed) - OpexV257SpeedRatingPoints(serviceSpeed);
  if (predicted < 0) predicted = 0;
  if (predicted > 255) predicted = 255;
  if (predicted <= 0) return 0;
  if (observed <= 0) return monthly;
  local observedShare = OpexC121StationAllocatedMonthly(1.0, observed, null);
  local predictedShare = OpexC121StationAllocatedMonthly(1.0, predicted, null);
  if (observedShare <= 0) return monthly;
  return monthly.tofloat() * predictedShare / observedShare;
}

/* Cash-flow annuel d'UNE rame, sans amortissement : le remboursement compte deja
 * l'achat net. monthly est le flux capte observe. Chaque plan le recale sur
 * sa propre note de vitesse avant de plafonner le transport. */
function OpexV257Plan(line, loco, wagon, wagons, monthly, rating, serviceSpeed, wagonLimits)
{
  local distance = ("routeDistance" in line) ? line.routeDistance : line.distance;
  local speed = OpexRailEffectiveSpeed(loco, wagon, wagons, distance);
  if (speed <= 0 || monthly <= 0) return null;
  local captured = OpexV257CapturedMonthly(monthly, rating, serviceSpeed, OpexV257ConsistLastSpeed(loco, wagon, wagonLimits));
  if (captured <= 0) return null;
  local days = distance.tofloat() / (0.036 * speed);
  if (days < 1) days = 1;
  local dwell = OpexRailStationDwellDays(wagon);
  local trips = OpexLoadedTripsPerMonth(days + dwell, 2 * days + dwell, line.kind == "pax");
  local capacity = wagons * wagon.capacity;
  local carried = capacity * trips;
  /* Le plafond est la demande de CE plan. Deux plans de meme last_speed
   * gardent le meme plafond : leur ecart de recette ne vient plus que du
   * trajet. Un plan plus lent perd des points de note, donc du fret remis,
   * meme s'il saturait l'ancienne demande. Les wagons vanilla ont une classe
   * de cout courant nulle, donc leur nombre ne change pas l'entretien. */
  if (carried > captured) carried = captured;
  local revenue = 12 * carried * AICargo.GetCargoIncome(line.cargo, line.distance, OpexCeilDiv(days, 1));
  return { loco = loco, wagon = wagon, wagons = wagons, revenue = revenue,
           running = loco.runningCost + wagons * wagon.runningCost,
           price = loco.price + wagons * wagon.price, speed = speed, days = days };
}

/* ESTIM-1 : meme modele de trafic avant/apres remplacement, recettes corrigees
 * via k_R rail, entretien reel des deux compositions et amortissement net du
 * nouveau vehicule sur sa duree utile. Aucun horizon de retour sur achat. */
function OpexEstimV257Project(current, target, oldVehicle, sale)
{
  if (current == null || target == null || sale == null
      || current.revenue <= 0) return null;
  local years = AIEngine.GetMaxAge(target.loco.id).tofloat() / 365.0;
  if (years <= 0) return null;
  local netPrice = target.price - sale;
  if (netPrice < 0) netPrice = 0;
  return OpexEstimVProject("rail", target.revenue - current.revenue,
      target.running - AIVehicle.GetRunningCost(oldVehicle),
      netPrice / years, netPrice);
}

function OpexV257ReviewLog(line, current, best, gain, cost, decision, reason, profit = 0, waiting = 0, rating = -1, load = 0, delivered = 0)
{
  if (DECISION_LOG) OpexDecide("V257_REVIEW", "line=" + line.lineId + " current=" + current
      + " best=" + best + " gain=" + gain + " cost=" + cost + " decision=" + decision
      + " reason=" + reason + " line_profit=" + profit + " waiting=" + waiting
      + " rating=" + rating + " load=" + load + " delivered_lower_bound=" + delivered);
}

/* GetCurrentValue(tete) exclut les wagons en API 15.3. Avant le depot,
 * cette valeur donne seulement une borne prudente du prix net. Au depot,
 * simuler la vente de TOUTE la rame fournit sa vraie recette de revente.
 * L'accounting local absorbe les couts simules sans toucher au caller. */
function OpexV257SaleValue(vehicle)
{
  if (!AIVehicle.IsStoppedInDepot(vehicle)) return AIVehicle.GetCurrentValue(vehicle);
  local accounting = AIAccounting();
  local test = AITestMode();
  if (!AIVehicle.SellVehicle(vehicle)) return null;
  return -accounting.GetCosts();
}

function OpexV257Discard(owner, vehicle)
{
  if (!AIVehicle.IsValidVehicle(vehicle)) return;
  if (AIVehicle.IsStoppedInDepot(vehicle) && AIVehicle.SellVehicle(vehicle)) return;
  /* Une commande refusee conserve une identite suivie. lineId=-1 empeche le
   * retireur de reinserer un wagon libre ou une rame incomplete dans la ligne. */
  if (owner._vehiclesToRetire == null) owner._vehiclesToRetire = {};
  owner._vehiclesToRetire.rawset(vehicle, { lineId = -1,
    startedDate = AIDate.GetCurrentDate(), lastSendDate = AIDate.GetCurrentDate(), attempts = 1 });
}

function OpexAI::_v257ReactiveStep()
{
  /* Le format court ne conserve pas les lignes : aucune transaction de flotte
   * n'y est ouverte. Le defaut save_full_state=1 reste intact. */
  if (!SAVE_FULL_STATE) return;
  local mark = OpexOpsMeasureBegin();
  local span = PROBE_SPAN_TRACE ? OpexSpanBegin("task.v257_rail_refresh") : null;
  if (this._v257State == null) this._v257State = {};
  if (this._v257Cache == null) this._v257Cache = {};
  if (this._catalog != null) {
    local revision = this._c76GetLayerRevision("engines.rail");
    if (this._v257CatalogRef != this._catalog.railLocos || this._v257EngineRevision != revision) {
      /* Invalidation O(1), aucune boucle sur les lignes lors d'un evenement.
       * Le premier catalogue apres Load reconstruit les caches sans effacer la cadence. */
      local changed = this._v257CatalogRef != null
          || (this._v257EngineRevision >= 0 && this._v257EngineRevision != revision);
      this._v257CatalogRef = this._catalog.railLocos;
      this._v257EngineRevision = revision;
      this._v257Cache = {};
      if (changed) {
        this._v257Cursor = 0;
        this._v257PriorityRemaining = this._lines != null ? this._lines.len() : 0;
      }
    }
  }
  if (this._v257Pending != null) {
    this._v257ReplaceStep();
  } else if (this._lines != null && this._lines.len() > 0 && this._catalog != null) {
    if (this._v257Cursor < 0 || this._v257Cursor >= this._lines.len()) this._v257Cursor = 0;
    local line = this._lines[this._v257Cursor++];
    local force = this._v257PriorityRemaining > 0;
    if (force) this._v257PriorityRemaining--;
    if (line != null && ("mode" in line) && line.mode == "rail"
        && (!("scrapping" in line) || !line.scrapping)) {
      if (!(line.lineId in this._v257State)) {
        this._v257State.rawset(line.lineId, {
          since = AIDate.GetCurrentDate(), nextDate = -1, delivered = 0, loads = {},
          annualDelivered = 0, annualDays = 0
        });
      }
      this._v257Review(line, this._v257State[line.lineId], AIDate.GetCurrentDate(), force);
    }
  }
  local ops = OpexOpsMeasureEnd(mark);
  if (span != null) OpexSpanEnd(span);
  if (DECISION_LOG) OpexDecide("V257_OPS", "ops=" + ops + " cursor=" + this._v257Cursor);
}

/* Meilleur couple pour UNE rame en service. La note prevue depend de sa
 * last_speed : le cache inclut donc la note observee et cette vitesse.
 * Deux rames de vitesses differentes ne partagent pas le meme choix. */
function OpexV257BestPlan(owner, line, monthly, rating, serviceSpeed, railType, wagonLimits)
{
  if (owner._v257Cache == null) owner._v257Cache = {};
  local cached = (line.lineId in owner._v257Cache) ? owner._v257Cache[line.lineId] : null;
  if (cached != null && cached.monthly == monthly && cached.railType == railType
      && cached.platformLength == line.platformLength && cached.rating == rating
      && cached.serviceSpeed == serviceSpeed && cached.wagonLimits == wagonLimits) {
    return cached.target;
  }
  local best = null;
  local locos = [];
  local wagons = [];
  local engines = AIEngineList(AIVehicle.VT_RAIL);
  /* OPCODE-AILIST L4 : predicats API natifs sur la liste deja construite.
   * Le departage metier est inchange ; la parite d'ordre a ete observee sur
   * les moteurs de 36 appels, suivie du banc economique neutre 20x10. */
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  engines.Valuate(AIEngine.CanRunOnRail, railType);
  engines.KeepValue(1);
  for (local engine = engines.Begin(); !engines.IsEnd(); engine = engines.Next()) {
    /* GetCapacity vaut -1, jamais 0, si aucune partie ne porte de cargo
     * (OpenTTD 15.3 ScriptEngine::GetCapacity). == 0 excluait toute locomotive. */
    if (AIEngine.IsWagon(engine)) {
      if (AIEngine.GetCargoType(engine) == line.cargo && AIEngine.GetCapacity(engine) > 0)
        wagons.append(OpexV257Engine(engine, line.cargo, true));
    } else if (AIEngine.HasPowerOnRail(engine, railType) && AIEngine.GetCapacity(engine) <= 0 && AIEngine.GetPower(engine) > 0
               && AIEngine.GetMaxSpeed(engine) > 0 && AIEngine.GetMaxTractiveEffort(engine) > 0) {
      locos.append(OpexV257Engine(engine, line.cargo, false));
    }
  }
  local length = line.platformLength;
  local maxLength = AIGameSettings.GetValue("vehicle.max_train_length");
  if (maxLength < length) length = maxLength;
  foreach (loco in locos) {
    foreach (wagon in wagons) {
      for (local number = 1; number <= OpexRailNominalMaxWagons(length); number++) {
        local plan = OpexV257Plan(line, loco, wagon, number, monthly, rating, serviceSpeed, wagonLimits);
        if (plan == null) continue;
        if (best == null || plan.revenue - plan.running > best.revenue - best.running
            || (plan.revenue - plan.running == best.revenue - best.running && plan.price < best.price)) best = plan;
      }
    }
  }
  owner._v257Cache.rawset(line.lineId, { target = best, monthly = monthly,
      railType = railType, platformLength = line.platformLength, rating = rating,
      serviceSpeed = serviceSpeed, wagonLimits = wagonLimits });
  return best;
}

function OpexAI::_v257Review(line, state, date, force)
{
  if (!("vehicles" in line) || line.vehicles == null || line.vehicles.len() == 0) return;
  if (!("depot" in line) || !AIRail.IsRailDepotTile(line.depot)) return;
  /* Les compositions mixtes ont d'autres contrats de refit : ne pas les demolir. */
  if ((("wagons2" in line) && line.wagons2 > 0) || this._railExpansion != null) return;
  local stationA = AIStation.GetStationID(line.stationA);
  local stationB = AIStation.GetStationID(line.stationB);
  if (!AIStation.IsValidStation(stationA) || !AIStation.IsValidStation(stationB)) return;
  local waiting = AIStation.GetCargoWaiting(stationA, line.cargo);
  local rating = AIStation.GetCargoRating(stationA, line.cargo);
  if (line.kind == "pax") {
    waiting += AIStation.GetCargoWaiting(stationB, line.cargo);
    local ratingB = AIStation.GetCargoRating(stationB, line.cargo);
    if (ratingB < rating) rating = ratingB;
  }
  local load = 0;
  local lineProfit = 0;
  local count = 0;
  local liveLoads = {};
  foreach (vehicle in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(vehicle)) continue;
    count++;
    lineProfit += AIVehicle.GetProfitLastYear(vehicle);
    local amount = AIVehicle.GetCargoLoad(vehicle, line.cargo);
    load += amount;
    /* Ne compter que la baisse constatee a une gare payee ; pas une disparition
     * de vehicule ni un transfert au depot. Les livraisons manquees restent inconnues. */
    local atStation = AIStation.GetStationID(AIVehicle.GetLocation(vehicle));
    if ((vehicle in state.loads) && state.loads[vehicle] > amount
        && (atStation == stationB || (line.kind == "pax" && atStation == stationA))) {
      state.delivered += state.loads[vehicle] - amount;
    }
    liveLoads.rawset(vehicle, amount);
  }
  state.loads = liveLoads;
  local year = AIDate.GetYear(date);
  local elapsed = date - state.since;
  if (elapsed >= AIDate.GetDate(year + 1, 1, 1) - AIDate.GetDate(year, 1, 1)) {
    state.annualDelivered = state.delivered;
    state.annualDays = elapsed;
    state.delivered = 0;
    state.since = date;
  }
  if (count == 0 || (!force && date < state.nextDate)) return;
  /* Un an d'observation et une annee civile pleine pour le profit de chaque train.
   * L'absence de preuve ne devient jamais une demande nulle rentable par convention. */
  if (state.annualDays <= 0 || state.annualDelivered <= 0 || rating < 0) {
    OpexV257ReviewLog(line, -1, -1, 0, 0, "keep", "observation", lineProfit, waiting, rating, load, state.annualDelivered);
    state.nextDate = date + (AIDate.GetDate(year + 1, 1, 1) - AIDate.GetDate(year, 1, 1));
    return;
  }
  state.nextDate = AIDate.GetDate(year + 1, AIDate.GetMonth(date), 1) + AIDate.GetDayOfMonth(date) - 1;
  local railType = AIRail.GetRailType(line.depot);
  /* Stock en attente amorti sur un an, jamais considere comme un flux mensuel.
   * La moyenne mesuree et le stock sont partages entre les rames de la ligne. */
  local monthly = (state.annualDelivered * 365.0 / state.annualDays + waiting) / (12 * count);
  local selected = null;
  local selectedVehicle = -1;
  local selectedGain = 0;
  local selectedScore = 0;
  local selectedCost = 0;
  local selectedCurrent = -1;
  local currentYearStart = AIDate.GetDate(year - 1, 1, 1);
  /* Le choix depend de la last_speed de la rame en service. Une composition
   * non modelisable (automotrice, rame mixte, trop courte) garde l'ancien
   * catalogue non recale, seulement pour le journal. */
  local wagonLimits = OpexV257WagonSpeedLimits();
  local catalogueLogged = false;
  foreach (vehicle in line.vehicles) {
    if (!AIVehicle.IsValidVehicle(vehicle)) continue;
    if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire)) continue;
    local currentEngine = AIVehicle.GetEngineType(vehicle);
    local number = AIVehicle.GetNumWagons(vehicle) - 1; // API 15.3 inclut la locomotive.
    local wagonEngine = -1;
    local homogeneous = false;
    if (number >= 1) {
      wagonEngine = AIVehicle.GetWagonEngineType(vehicle, 1);
      homogeneous = true;
      for (local index = 1; index <= number; index++) {
        if (AIVehicle.GetWagonEngineType(vehicle, index) != wagonEngine) homogeneous = false;
      }
    }
    local serviceLoco = null;
    local serviceWagon = null;
    local serviceSpeed = 0;
    local planRating = -1;
    if (number >= 1 && homogeneous && AIEngine.GetCapacity(currentEngine) <= 0
        && AIEngine.IsWagon(wagonEngine) && AIEngine.GetCargoType(wagonEngine) == line.cargo) {
      serviceLoco = OpexV257Engine(currentEngine, line.cargo, false);
      serviceWagon = OpexV257Engine(wagonEngine, line.cargo, true);
      serviceSpeed = OpexV257ConsistLastSpeed(serviceLoco, serviceWagon, wagonLimits);
      planRating = rating;
    }
    local best = OpexV257BestPlan(this, line, monthly, planRating, serviceSpeed, railType, wagonLimits);
    if (best == null) {
      /* Une autre rame de la ligne peut encore avoir un plan. Ne pas effacer
       * un remplacement deja retenu en sortant de la boucle. */
      if (!catalogueLogged) {
        OpexV257ReviewLog(line, -1, -1, 0, 0, "keep", "catalogue", lineProfit, waiting, rating, load, state.delivered);
        catalogueLogged = true;
      }
      continue;
    }
    if (date - AIVehicle.GetAge(vehicle) > currentYearStart) {
      OpexV257ReviewLog(line, currentEngine, best.loco.id, 0, 0, "keep", "partial_profit_year");
      continue;
    }
    if (AIEngine.GetCapacity(currentEngine) > 0) continue; // automotrices : modele dedie necessaire.
    if (number < 1) continue;
    if (!homogeneous || !AIEngine.IsWagon(wagonEngine) || AIEngine.GetCargoType(wagonEngine) != line.cargo) continue;
    if (currentEngine == best.loco.id && number == best.wagons && wagonEngine == best.wagon.id) {
      OpexV257ReviewLog(line, currentEngine, best.loco.id, 0, 0, "keep", "current_best");
      continue;
    }
    local current = OpexV257Plan(line, serviceLoco, serviceWagon, number, monthly, planRating, serviceSpeed, wagonLimits);
    if (current == null || current.revenue <= 0) continue;
    /* Ancrage au cash-flow reel : la recette prevue est calibree par le profit
     * realise + le cout courant reel. Aucun gain d'amortissement fictif. */
    local realRevenue = AIVehicle.GetProfitLastYear(vehicle) + AIVehicle.GetRunningCost(vehicle);
    if (realRevenue <= 0) continue;
    local gain = realRevenue * (best.revenue.tofloat() / current.revenue - 1.0)
        + AIVehicle.GetRunningCost(vehicle) - best.running;
    local sale = OpexV257SaleValue(vehicle);
    if (sale == null) continue;
    local cost = best.price - sale;
    local remaining = AIVehicle.GetAgeLeft(vehicle) / 365.0;
    local newLife = AIEngine.GetMaxAge(best.loco.id) / 365.0;
    if (newLife < remaining) remaining = newLife;
    local pays = gain > 0 && remaining > 0 && gain * remaining >= cost;
    local estimProject = null;
    if ((ESTIM_UNIFIE & 4) != 0) {
      estimProject = OpexEstimV257Project(current, best, vehicle, sale);
      if (estimProject == null) continue;
      OpexEstimVLog("V257", line.lineId, estimProject);
      gain = estimProject.deltaP;
      pays = estimProject.deltaP > 0 && estimProject.score > 0;
    }
    OpexV257ReviewLog(line, currentEngine, best.loco.id, gain, cost, pays ? "replace" : "keep",
        pays ? "payback" : "payback_failed", lineProfit, waiting, rating, load, state.annualDelivered);
    if (pays && (selected == null || ((ESTIM_UNIFIE & 4) != 0
        ? estimProject.score > selectedScore
        : gain > selectedGain))) {
      selected = best; selectedVehicle = vehicle; selectedGain = gain;
      selectedCost = cost; selectedCurrent = currentEngine;
      if ((ESTIM_UNIFIE & 4) != 0)
        selectedScore = estimProject.score;
    }
  }
  if (selected != null) {
    /* Le depot atteint decide du depot de reconstruction, pas le premier depot
     * de la ligne : important pour les deux voies independantes. */
    this._v257Pending = { lineId = line.lineId, vehicle = selectedVehicle,
      engine = selected.loco.id, wagon = selected.wagon.id, wagons = selected.wagons,
      gain = selectedGain.tointeger(), cost = selectedCost, current = selectedCurrent,
      deadline = state.nextDate, newVehicle = -1, phase = "depot",
      order = AIOrder.ResolveOrderPosition(selectedVehicle, AIOrder.ORDER_CURRENT),
      lineProfit = lineProfit, waiting = waiting, rating = rating, load = load,
      delivered = state.annualDelivered };
    this._v257PendingLine = line;
    /* 15.3 Vehicle::SendToDepot renvoie une erreur si la rame est deja arretee
     * au depot. La transaction continue au passage suivant. Tout autre echec
     * est journalise ; l'ancienne rame n'est pas vendue. */
    if (!AIVehicle.IsStoppedInDepot(selectedVehicle) && !AIVehicle.SendVehicleToDepot(selectedVehicle)) {
      OpexV257ReviewLog(line, selectedCurrent, selected.loco.id, selectedGain, selectedCost, "keep",
          "depot_send_failed", lineProfit, waiting, rating, load, state.annualDelivered);
      this._v257Pending = null; this._v257PendingLine = null;
    }
  }
}

function OpexAI::_v257ReplaceStep()
{
  local pending = this._v257Pending;
  local line = this._v257PendingLine; // pas de recherche O(nombre de lignes) par passage.
  local oldVehicle = pending.vehicle;
  /* Champs absents d'une sauvegarde anterieure : les defauts du journal. */
  local lineProfit = ("lineProfit" in pending) ? pending.lineProfit : 0;
  local waiting = ("waiting" in pending) ? pending.waiting : 0;
  local rating = ("rating" in pending) ? pending.rating : -1;
  local load = ("load" in pending) ? pending.load : 0;
  local delivered = ("delivered" in pending) ? pending.delivered : 0;
  if (line == null || (("scrapping" in line) && line.scrapping) || !AIVehicle.IsValidVehicle(oldVehicle)) {
    this._v257Pending = null; this._v257PendingLine = null;
    return;
  }
  if (!AIVehicle.IsStoppedInDepot(oldVehicle)) {
    if (AIDate.GetCurrentDate() >= pending.deadline) {
      AIVehicle.SendVehicleToDepot(oldVehicle); // deuxieme appel : annule l'ordre automatique.
      OpexV257ReviewLog(line, pending.current, pending.engine, pending.gain, pending.cost, "keep", "depot_timeout",
          lineProfit, waiting, rating, load, delivered);
      this._v257Pending = null; this._v257PendingLine = null;
    }
    return;
  }
  if (pending.phase == "resume") {
    if (AIVehicle.StartStopVehicle(oldVehicle)) { this._v257Pending = null; this._v257PendingLine = null; }
    return;
  }
  local depot = AIVehicle.GetLocation(oldVehicle);
  local loco = OpexV257Engine(pending.engine, line.cargo, false);
  local wagon = OpexV257Engine(pending.wagon, line.cargo, true);
  local price = loco.price + pending.wagons * wagon.price;
  local sale = OpexV257SaleValue(oldVehicle);
  local cost = sale != null ? price - sale : price;
  /* Recontrole au depot : prix, duree restante, compatibilite et liquidite brute.
   * La revente ne finance jamais un achat qui pourrait echouer ensuite. */
  local compatible = AIRail.IsRailDepotTile(depot) && AIEngine.IsBuildable(pending.engine)
      && AIEngine.IsBuildable(pending.wagon) && AIEngine.HasPowerOnRail(pending.engine, AIRail.GetRailType(depot))
      && AIEngine.CanRunOnRail(pending.wagon, AIRail.GetRailType(depot));
  /* Le trajet jusqu'au depot peut traverser un nouvel exercice ou une variation
   * de prix. Recalculer le gain avec le profit/entretien actuels et le stock
   * maintenant observe, sans figer le gain du jour de l'envoi. */
  local state = (line.lineId in this._v257State) ? this._v257State[line.lineId] : null;
  local number = AIVehicle.GetNumWagons(oldVehicle) - 1;
  local gain = 0.0;
  local currentPlan = null;
  local targetPlan = null;
  if (state != null && state.annualDays > 0 && number > 0 && line.vehicles.len() > 0) {
    local wagonEngine = AIVehicle.GetWagonEngineType(oldVehicle, 1);
    local stock = AIStation.GetCargoWaiting(AIStation.GetStationID(line.stationA), line.cargo);
    if (line.kind == "pax") stock += AIStation.GetCargoWaiting(AIStation.GetStationID(line.stationB), line.cargo);
    local monthly = (state.annualDelivered * 365.0 / state.annualDays + stock) / (12 * line.vehicles.len());
    local stationA = AIStation.GetStationID(line.stationA);
    if (AIStation.IsValidStation(stationA)) {
      local ratingNow = AIStation.GetCargoRating(stationA, line.cargo);
      if (line.kind == "pax") {
        local stationB = AIStation.GetStationID(line.stationB);
        if (AIStation.IsValidStation(stationB)) {
          local ratingB = AIStation.GetCargoRating(stationB, line.cargo);
          if (ratingB < ratingNow) ratingNow = ratingB;
        }
      }
      if (ratingNow >= 0) rating = ratingNow;
    }
    local wagonLimits = OpexV257WagonSpeedLimits();
    local serviceLoco = OpexV257Engine(AIVehicle.GetEngineType(oldVehicle), line.cargo, false);
    local serviceWagon = OpexV257Engine(wagonEngine, line.cargo, true);
    local serviceSpeed = OpexV257ConsistLastSpeed(serviceLoco, serviceWagon, wagonLimits);
    local current = OpexV257Plan(line, serviceLoco, serviceWagon, number, monthly, rating, serviceSpeed, wagonLimits);
    local target = OpexV257Plan(line, loco, wagon, pending.wagons, monthly, rating, serviceSpeed, wagonLimits);
    currentPlan = current;
    targetPlan = target;
    local realRevenue = AIVehicle.GetProfitLastYear(oldVehicle) + AIVehicle.GetRunningCost(oldVehicle);
    if (current != null && target != null && current.revenue > 0 && realRevenue > 0) {
      gain = realRevenue * (target.revenue.tofloat() / current.revenue - 1.0)
          + AIVehicle.GetRunningCost(oldVehicle) - target.running;
    }
  }
  pending.gain = gain.tointeger();
  local remaining = AIVehicle.GetAgeLeft(oldVehicle) / 365.0;
  local newLife = AIEngine.GetMaxAge(pending.engine) / 365.0;
  if (newLife < remaining) remaining = newLife;
  local estimPays = false;
  if ((ESTIM_UNIFIE & 4) != 0) {
    local refreshed = OpexEstimV257Project(currentPlan, targetPlan, oldVehicle, sale);
    if (refreshed != null) {
      pending.gain = refreshed.deltaP;
      OpexEstimVLog("V257_DEPOT", line.lineId, refreshed);
      estimPays = refreshed.deltaP > 0 && refreshed.score > 0;
    }
  }
  if (sale == null || !compatible || ((ESTIM_UNIFIE & 4) != 0 ? !estimPays
      : (remaining <= 0 || pending.gain <= 0 || pending.gain * remaining < cost))
      || AICompany.GetBankBalance(AICompany.COMPANY_SELF) <
          ((ESTIM_UNIFIE & 2) != 0
              ? OpexEstimFinanceCashNeeded("rail", price, 0, true)
              : price + OpexCashReserve())) {
    pending.phase = "resume";
    local resumed = AIVehicle.StartStopVehicle(oldVehicle);
    OpexV257ReviewLog(line, pending.current, pending.engine, pending.gain, cost, "keep", "depot_recheck",
        lineProfit, waiting, rating, load, delivered);
    if (resumed) { this._v257Pending = null; this._v257PendingLine = null; }
    return;
  }
  local previousType = AIRail.GetCurrentRailType();
  AIRail.SetCurrentRailType(AIRail.GetRailType(depot));
  /* Le builder existant mesure la longueur reelle et conserve chaque wagon
   * pour rollback. Il ne demarre aucun vehicule avant validation des ordres. */
  local equipment = { wagonByCargo = {} };
  equipment.wagonByCargo.rawset(line.cargo, wagon);
  /* Une sauvegarde peut interrompre les commandes du builder. Conserver le
   * contenu initial du depot pour retrouver ses creations partielles au Load. */
  pending.depot <- depot;
  pending.before <- [];
  local before = AIVehicleList(); // inclut les wagons libres, contrairement a la liste par ordres.
  for (local vehicle = before.Begin(); !before.IsEnd(); vehicle = before.Next()) {
    if (AIVehicle.GetLocation(vehicle) == depot) pending.before.append(vehicle);
  }
  pending.phase = "building";
  local built = OpexBuildTrains(equipment, line.cargo, line.kind, depot,
      line.stationA, line.stationB, 1, loco, pending.wagons, line.platformLength, false);
  AIRail.SetCurrentRailType(previousType);
  local newVehicle = built.vehicles.len() > 0 ? built.vehicles[0] : -1;
  pending.newVehicle = newVehicle;
  /* CopyOrders ne reinitialise l'index que si le nombre d'ordres differe
   * (15.3 CmdCloneOrder). La rame neuve est deja sur l'ordre 0, et
   * CmdSkipToOrder refuse l'ordre deja courant. Deja courant = succes. */
  local reason = null;
  if (built.failed) {
    reason = "build_failed";
  } else if (!AIOrder.CopyOrders(newVehicle, oldVehicle)) {
    reason = "copy_orders_failed";
  } else {
    local here = AIOrder.ResolveOrderPosition(newVehicle, AIOrder.ORDER_CURRENT);
    if (here != pending.order && !AIOrder.SkipToOrder(newVehicle, pending.order)) {
      reason = "skip_order_failed";
    } else if (!AIVehicle.StartStopVehicle(newVehicle)) {
      reason = "start_failed";
    }
  }
  if (reason != null) {
    foreach (vehicle in built.rollbackVehicles) {
      OpexV257Discard(this, vehicle);
    }
    pending.phase = "resume";
    local resumed = AIVehicle.StartStopVehicle(oldVehicle);
    OpexV257ReviewLog(line, pending.current, pending.engine, pending.gain, cost, "keep", reason,
        lineProfit, waiting, rating, load, delivered);
    if (resumed) { this._v257Pending = null; this._v257PendingLine = null; }
    return;
  }
  pending.phase = "started";
  for (local index = 0; index < line.vehicles.len(); index++) {
    if (line.vehicles[index] == oldVehicle) { line.vehicles[index] = newVehicle; break; }
  }
  line.loco = loco;
  line.wagons = pending.wagons;
  line.wagonId = pending.wagon;
  this._saveProjection = null; // identites de flotte a jour des la prochaine sauvegarde.
  /* L'ancien train est arrete au depot ; le retireur existant reessaie une vente refusee. */
  if (!AIVehicle.SellVehicle(oldVehicle)) {
    if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
    this._vehiclesToRetire.rawset(oldVehicle, { lineId = line.lineId,
      startedDate = AIDate.GetCurrentDate(), lastSendDate = AIDate.GetCurrentDate(), attempts = 1 });
  }
  if (DECISION_LOG) OpexDecide("V257_REPLACE", "line=" + line.lineId + " old_veh=" + oldVehicle
      + " new_veh=" + newVehicle + " current=" + pending.current + " best=" + pending.engine
      + " wagons=" + pending.wagons + " price=" + price + " cost=" + cost + " gain=" + pending.gain);
  this._v257Pending = null; this._v257PendingLine = null;
}

/* Apres liveLines : cadence/charges exactes conservees hors projection, caches
 * reconstruits. Une ancienne sauvegarde initialise simplement un curseur nul.
 * Une transaction interrompue avant Start est annulee ; apres Start elle est
 * adoptee par identite, y compris si l'ancienne tete a deja ete vendue. */
function OpexV257Reconcile(owner)
{
  owner._v257Cache = null;
  owner._v257CatalogRef = null;
  owner._v257PendingLine = null;
  if (owner._v257Cursor < 0 || owner._v257Cursor >= owner._lines.len()) owner._v257Cursor = 0;
  if (owner._v257PriorityRemaining < 0) owner._v257PriorityRemaining = 0;
  if (owner._v257PriorityRemaining > owner._lines.len()) owner._v257PriorityRemaining = owner._lines.len();
  local states = {};
  if (SAVE_FULL_STATE && owner._v257State != null) {
    foreach (line in owner._lines) {
      if (!(line.lineId in owner._v257State)) continue;
      local state = owner._v257State[line.lineId];
      if (typeof state != "table" || !("since" in state) || !("nextDate" in state)
          || !("delivered" in state) || !("loads" in state) || typeof state.loads != "table"
          || !("annualDelivered" in state) || !("annualDays" in state)) continue;
      states.rawset(line.lineId, state);
    }
  }
  owner._v257State = SAVE_FULL_STATE ? states : null;
  local pending = owner._v257Pending;
  if (pending == null) return;
  local line = owner._findLineById(pending.lineId);
  owner._v257PendingLine = line;
  local newVehicle = pending.newVehicle;
  local adopted = line != null && AIVehicle.IsValidVehicle(newVehicle)
      && !AIVehicle.IsStoppedInDepot(newVehicle);
  if (line == null && AIVehicle.IsValidVehicle(newVehicle)) OpexV257Discard(owner, newVehicle);
  if (line == null && AIVehicle.IsValidVehicle(pending.vehicle)) OpexV257Discard(owner, pending.vehicle);
  if (adopted) {
    local mapped = false;
    for (local index = 0; index < line.vehicles.len(); index++) {
      if (line.vehicles[index] == newVehicle) mapped = true;
      if (line.vehicles[index] == pending.vehicle) { line.vehicles[index] = newVehicle; mapped = true; }
    }
    if (!mapped) line.vehicles.append(newVehicle);
    line.loco = OpexV257Engine(pending.engine, line.cargo, false);
    line.wagons = pending.wagons;
    line.wagonId = pending.wagon;
    if (AIVehicle.IsValidVehicle(pending.vehicle) && AIVehicle.IsStoppedInDepot(pending.vehicle)) {
      if (!AIVehicle.SellVehicle(pending.vehicle)) {
        if (owner._vehiclesToRetire == null) owner._vehiclesToRetire = {};
        owner._vehiclesToRetire.rawset(pending.vehicle, { lineId = line.lineId,
          startedDate = AIDate.GetCurrentDate(), lastSendDate = AIDate.GetCurrentDate(), attempts = 1 });
      }
    }
  } else if (("depot" in pending) && ("before" in pending) && AIRail.IsRailDepotTile(pending.depot)) {
    local vehicles = AIVehicleList();
    for (local vehicle = vehicles.Begin(); !vehicles.IsEnd(); vehicle = vehicles.Next()) {
      if (AIVehicle.GetLocation(vehicle) == pending.depot && AIVehicle.IsStoppedInDepot(vehicle)
          && !OpexWaterContains(pending.before, vehicle)) OpexV257Discard(owner, vehicle);
    }
  }
  if (adopted || !SAVE_FULL_STATE || line == null || pending.phase != "depot") {
    local keepResume = false;
    if (!adopted && line != null && (!("scrapping" in line) || !line.scrapping)
        && AIVehicle.IsValidVehicle(pending.vehicle)) {
      if (AIVehicle.IsStoppedInDepot(pending.vehicle)) {
        if (!AIVehicle.StartStopVehicle(pending.vehicle) && SAVE_FULL_STATE) {
          pending.phase = "resume";
          keepResume = true;
        }
      }
      else if (pending.phase == "depot") AIVehicle.SendVehicleToDepot(pending.vehicle);
    }
    if (!keepResume) { owner._v257Pending = null; owner._v257PendingLine = null; }
  }
  owner._saveProjection = null;
}
