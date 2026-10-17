/* V221 : relever la composante « profit minimal » de la note de performance.
 *
 * OpenTTD 15.3, UpdateCompanyRatingAndValue (economy.cpp) : pour chaque vehicule
 * principal d'un type constructible, si economy_age > VEHICLE_PROFIT_MIN_AGE,
 * on retient le plus petit profit_last_year. VEHICLE_PROFIT_MIN_AGE vaut
 * CalendarTime::DAYS_IN_YEAR * 2, soit 730 (timer_game_common.h). Le montant est
 * decale de 8 bits (livres), ignore s'il est <= 0, puis clampe a 10 000 pour
 * 100 points (SCORE_MIN_PROFIT). GetDisplayProfitLastYear (vehicle_base.h) est
 * exactement profit_last_year >> 8 : pas d'extrapolation selon l'age. L'API
 * GetProfitLastYear renvoie cette valeur ; GetAge renvoie l'age calendaire
 * (script_vehicle.cpp). Hors mode wallclock, l'horloge economique suit le
 * calendrier (timer_game_economy.h).
 *
 * On agit donc sur GetProfitLastYear, pas sur GetProfitThisYear annualise :
 * la note ne lit que l'annee deja close, et une extrapolation en debut d'annee
 * confond une tournee pas encore bouclee avec une ligne structurellement faible.
 * Le seuil d'age 700 (730 - 30) fait sortir le vehicule avant qu'il n'entre dans
 * le calcul (economy_age > 730). Au-dela de 730, le meme critere retire ceux
 * qui tirent deja la composante a zero.
 *
 * Defaut 0 : le crochet de scheduler.nut est un seul test, cette fonction
 * n'est pas appelee, aucun etat n'est ecrit. */

/* 730 - 30. Le jeu n'englobe le vehicule qu'a economy_age > 730. */
V221_AGE_MIN <- 700;
/* Actions moteur (retrait, rebut, renouvellement) par passe mensuelle. */
V221_MAX_ACTIONS <- 4;
/* Pires candidats conserves pour encaisser les skips (depot, V92, ligne jeune). */
V221_CANDIDATE_CAP <- 32;

function OpexV221Log(vehicle, mode, lineId, age, profit, action, reason)
{
  if (!DECISION_LOG) return;
  OpexDecide("V221_CULL", "vehicle=" + vehicle + " mode=" + mode
      + " line=" + lineId + " age=" + age + " profit=" + profit
      + " action=" + action + " reason=" + reason);
}

function OpexV221ModeOfVehicle(vehicle)
{
  local kind = AIVehicle.GetVehicleType(vehicle);
  if (kind == AIVehicle.VT_ROAD) return "road";
  if (kind == AIVehicle.VT_RAIL) return "rail";
  if (kind == AIVehicle.VT_AIR) return "air";
  return "water";
}

function OpexV221LineYoung(line, date)
{
  if ("buildDate" in line) {
    local built = line.buildDate;
    if (built > 0) return (date - built) < 365;
  }
  if ("year" in line) return (AIDate.GetYear(date) - line.year) < 1;
  return false;
}

function OpexV221KeepWorst(rows, row, cap)
{
  if (rows.len() < cap) {
    rows.append(row);
    return;
  }
  local looseSlot = 0;
  local looseProfit = rows[0].profit;
  for (local i = 1; i < rows.len(); i++) {
    if (rows[i].profit > looseProfit) {
      looseProfit = rows[i].profit;
      looseSlot = i;
    }
  }
  if (row.profit < looseProfit) rows[looseSlot] = row;
}

function OpexV221SortByProfit(rows)
{
  for (local i = 1; i < rows.len(); i++) {
    local row = rows[i];
    local j = i;
    while (j > 0 && rows[j - 1].profit > row.profit) {
      rows[j] = rows[j - 1];
      j--;
    }
    rows[j] = row;
  }
}

/* Identifiants encore rattaches a la ligne. stationA est une tuile.
 * La route n'a pas de tableau vehicles : OpexLineVehicleIds filtre par ordres. */
function OpexV221LineIds(line)
{
  if (line == null) return null;
  if (("stationA" in line) && line.stationA != null) {
    local stationA = AIStation.GetStationID(line.stationA);
    if (AIStation.IsValidStation(stationA)) return OpexLineVehicleIds(line, stationA);
  }
  if (("vehicles" in line) && line.vehicles != null) return line.vehicles;
  return null;
}

/* Un retrait deja engage reste dans la liste par ordres (route) jusqu'a la vente.
 * _triggerScrapLine rappellerait SendVehicleToDepot et ANNULERAIT ce trajet. */
function OpexV221HasPendingRetire(owner, line)
{
  local pending = owner._vehiclesToRetire;
  if (pending == null) return false;
  local ids = OpexV221LineIds(line);
  if (ids == null) return false;
  foreach (id in ids) {
    if (id in pending) return true;
  }
  return false;
}

/* Vehicules encore comptes sur la ligne, hors retraites deja engagees.
 * Un vehicule deja au rebut ne doit pas faire croire que la ligne est multiple. */
function OpexV221LiveCount(owner, line, vehicle)
{
  local ids = OpexV221LineIds(line);
  local n = 0;
  local seen = false;
  local pending = owner._vehiclesToRetire;
  if (ids != null) {
    foreach (id in ids) {
      if (!AIVehicle.IsValidVehicle(id) || !AIVehicle.IsPrimaryVehicle(id)) continue;
      if (pending != null && (id in pending)) continue;
      if (AIVehicle.GetVehicleType(id) != OpexLineVehicleType(line)) continue;
      n++;
      if (id == vehicle) seen = true;
    }
  }
  if (!seen && AIVehicle.IsValidVehicle(vehicle)) {
    if (pending == null || !(vehicle in pending)) n++;
  }
  if (n < 1) n = 1;
  return n;
}

function OpexV221DepotTile(line)
{
  if (line == null) return null;
  local mode = ("mode" in line) ? line.mode : "";
  if (mode == "air") {
    /* stationA est la tuile d'aeroport, comme dans air_fleet.nut. */
    if (!("stationA" in line) || line.stationA == null) return null;
    if (!AIAirport.IsAirportTile(line.stationA)) return null;
    local hangar = AIAirport.GetHangarOfAirport(line.stationA);
    if (AIMap.IsValidTile(hangar) && AIAirport.IsHangarTile(hangar)) return hangar;
    return null;
  }
  local depot = ("depot" in line) ? line.depot : null;
  if (mode == "rail") {
    if (depot != null && AIRail.IsRailDepotTile(depot)) return depot;
    if (("depot2" in line) && line.depot2 != null && AIRail.IsRailDepotTile(line.depot2)) return line.depot2;
    return null;
  }
  if (mode == "road") {
    if (depot != null && AIRoad.IsRoadDepotTile(depot)) return depot;
    return null;
  }
  if (mode == "water") {
    if (depot != null && AIMarine.IsWaterDepotTile(depot)) return depot;
    return null;
  }
  if (depot != null && AIMap.IsValidTile(depot)) return depot;
  return null;
}

/* Prix d'un vehicule neuf du meme modele, wagons compris. Sert de plancher
 * de tresorerie : on exige deux fois ce prix, sans compter la revente. */
function OpexV221ReplacePrice(vehicle)
{
  local total = 0;
  local units = AIVehicle.GetNumWagons(vehicle);
  if (units < 1) units = 1;
  if (units > 32) units = 32;
  for (local i = 0; i < units; i++) {
    local engineId = AIVehicle.GetWagonEngineType(vehicle, i);
    if (engineId == null || engineId < 0) continue;
    local price = AIEngine.GetPrice(engineId);
    if (price > 0) total += price;
  }
  if (total > 0) return total;
  local front = AIVehicle.GetEngineType(vehicle);
  if (front == null || front < 0) return 0;
  local price = AIEngine.GetPrice(front);
  return price > 0 ? price : 0;
}

/* Meme sequence que la retraite unitaire de _onVehicleUnprofitable :
 * envoi au depot, ticket _vehiclesToRetire, retrait de l'inventaire, baisse
 * de vehCount / trains / predTrains. Le ticket est pose avant la baisse :
 * un second passage retrouve le vehicule et ne decremente plus. */
function OpexAI::_v221RetireUnit(vehicle, line)
{
  if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire)) return false;
  if (line != null && OpexAirLineReequipPending(line)) return false;
  if (!AIVehicle.SendVehicleToDepot(vehicle)) return false;
  local now = AIDate.GetCurrentDate();
  if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
  local lineId = -1;
  if (line != null && ("lineId" in line)) lineId = line.lineId;
  this._vehiclesToRetire.rawset(vehicle, {
    lineId = lineId, startedDate = now, lastSendDate = now, attempts = 1
  });
  if (line == null) return true;
  if ("vehicles" in line && line.vehicles != null) {
    for (local i = 0; i < line.vehicles.len(); i++) {
      if (line.vehicles[i] == vehicle) {
        line.vehicles.remove(i);
        break;
      }
    }
  }
  if (("vehicle" in line) && line.vehicle == vehicle) {
    local replacement = -1;
    if (("vehicles" in line) && line.vehicles != null) {
      foreach (other in line.vehicles) {
        if (AIVehicle.IsValidVehicle(other)) {
          replacement = other;
          break;
        }
      }
    }
    line.vehicle = replacement;
  }
  if ("vehCount" in line && line.vehCount > 0) line.vehCount--;
  if ("trains" in line && line.trains > 1) line.trains--;
  /* Sans cette baisse, _refleetRoadLines reconstruirait le vehicule retire. */
  if ("predTrains" in line && line.predTrains > 1) line.predTrains--;
  return true;
}

/* Renouvellement : vehicule neuf du meme modele, ordres partages, puis envoi
 * de l'ancien au depot. Les compteurs de flotte ne bougent pas : c'est un
 * remplacement, pas un retrait. null = fait, sinon la raison du skip. */
function OpexAI::_v221Renew(vehicle, line, reserve)
{
  if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire)) return "retire_pending";
  if (OpexAirLineReequipPending(line)) return "v92";
  local depot = OpexV221DepotTile(line);
  if (depot == null) return "no_depot";
  local price = OpexV221ReplacePrice(vehicle);
  if (price <= 0) return "no_price";
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (cash < price * 2 + reserve) return "cash";
  local fresh = AIVehicle.CloneVehicle(depot, vehicle, true);
  if (!AIVehicle.IsValidVehicle(fresh)) return "build_fail";
  if (!AIVehicle.StartStopVehicle(fresh)) {
    if (AIVehicle.IsStoppedInDepot(fresh)) AIVehicle.SellVehicle(fresh);
    return "start";
  }
  if (!AIVehicle.SendVehicleToDepot(vehicle)) {
    if (AIVehicle.IsStoppedInDepot(fresh)) {
      AIVehicle.SellVehicle(fresh);
    } else if (AIVehicle.SendVehicleToDepot(fresh)) {
      if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
      local undoNow = AIDate.GetCurrentDate();
      this._vehiclesToRetire.rawset(fresh, {
        lineId = -1, startedDate = undoNow, lastSendDate = undoNow, attempts = 1
      });
    }
    return "depot_refused";
  }
  local now = AIDate.GetCurrentDate();
  if (this._vehiclesToRetire == null) this._vehiclesToRetire = {};
  local lineId = ("lineId" in line) ? line.lineId : -1;
  this._vehiclesToRetire.rawset(vehicle, {
    lineId = lineId, startedDate = now, lastSendDate = now, attempts = 1
  });
  if (("vehicles" in line) && line.vehicles != null) {
    line.vehicles.append(fresh);
    for (local i = 0; i < line.vehicles.len(); i++) {
      if (line.vehicles[i] == vehicle) {
        line.vehicles.remove(i);
        break;
      }
    }
  }
  if (("vehicle" in line) && line.vehicle == vehicle) line.vehicle = fresh;
  return null;
}

function OpexAI::_v221MinProfitCull()
{
  if (V221_MIN_PROFIT <= 0) return;
  if (this._lines == null) return;
  local date = AIDate.GetCurrentDate();
  local ym = AIDate.GetYear(date) * 12 + AIDate.GetMonth(date);
  if (V221_LAST_MONTH == ym) return;
  V221_LAST_MONTH = ym;

  local rows = [];
  foreach (vehicle, _ in AIVehicleList()) {
    if (!AIVehicle.IsPrimaryVehicle(vehicle)) continue;
    local age = AIVehicle.GetAge(vehicle);
    if (age < V221_AGE_MIN) continue;
    /* Annee close uniquement : c'est le montant lu par la note. */
    local profit = AIVehicle.GetProfitLastYear(vehicle);
    if (profit >= V221_MIN_PROFIT) continue;
    OpexV221KeepWorst(rows, { id = vehicle, profit = profit, age = age }, V221_CANDIDATE_CAP);
  }
  if (rows.len() == 0) return;
  OpexV221SortByProfit(rows);

  local actions = 0;
  local reserve = OpexCashReserve();
  foreach (row in rows) {
    if (actions >= V221_MAX_ACTIONS) break;
    local vehicle = row.id;
    if (!AIVehicle.IsValidVehicle(vehicle) || !AIVehicle.IsPrimaryVehicle(vehicle)) continue;
    if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire)) continue;
    local mode = OpexV221ModeOfVehicle(vehicle);
    local line = OpexFindLineForVehicle(this._lines, vehicle);
    local lineId = -1;
    if (line != null && ("lineId" in line)) lineId = line.lineId;
    if (line != null && ("mode" in line)) mode = line.mode;
    if (AIVehicle.GetState(vehicle) == AIVehicle.VS_CRASHED) {
      OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "crashed");
      continue;
    }
    if (AIVehicle.IsInDepot(vehicle) || AIVehicle.IsStoppedInDepot(vehicle)
        || AIOrder.IsGotoDepotOrder(vehicle, AIOrder.ORDER_CURRENT)) {
      OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "depot");
      continue;
    }
    if (line != null && ("scrapping" in line) && line.scrapping) continue;
    if (line != null && OpexAirLineReequipPending(line)) {
      OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "v92");
      continue;
    }
    if (line != null && OpexV221LineYoung(line, date)) {
      OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "line_young");
      continue;
    }
    if (line == null) {
      if (this._v221RetireUnit(vehicle, null)) {
        actions++;
        OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "retire", "orphan");
      } else {
        OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "depot_refused");
      }
      continue;
    }
    local have = OpexV221LiveCount(this, line, vehicle);
    if (have > 1) {
      if (this._v221RetireUnit(vehicle, line)) {
        actions++;
        OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "retire", "multi");
      } else {
        OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "depot_refused");
      }
      continue;
    }
    if (row.profit <= 0) {
      if (OpexV221HasPendingRetire(this, line)) {
        OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", "retire_pending");
        continue;
      }
      this._triggerScrapLine(line, "v221");
      actions++;
      OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "retire", "line_loss");
      continue;
    }
    local reason = this._v221Renew(vehicle, line, reserve);
    if (reason == null) {
      actions++;
      OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "renew", "ok");
    } else {
      OpexV221Log(vehicle, mode, lineId, row.age, row.profit, "skip", reason);
    }
  }
}
