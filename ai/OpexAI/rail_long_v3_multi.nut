/* RAIL-LONG v3 MULTI : traction comparee 1/2/3 motrices et assemblage
 * transactionnel. Opt-in exclusif mode 3. Aucune modification des rames
 * historiques, aucun appel de ce constructeur sous 0/1/2.
 *
 * OpenTTD 15.3 : AIVehicle.MoveWagon peut joindre une seconde motrice
 * comme une voiture. Son succes n'est PAS presuppose : longueur, moteur
 * reel, indices de toutes les motrices et des wagons sont relus apres
 * chaque operation. Aucun vehicule ne demarre avant validation des ordres.
 * Echec => liste exhaustive a OpexRollback (qui vend seulement au depot).
 * Les moteurs articules sont refuses : leur longueur et leurs indices
 * depasseraient le contrat simple [locos...][wagons...]. */

function OpexRailLongV3MultiLog(event, fields)
{
  if (DECISION_LOG) OpexDecide("RAIL_LONG_V3_MULTI", "event=" + event + " " + fields);
}

function OpexRailLongV3MultiLine(line)
{
  return line != null && typeof line == "table"
      && (("railLongV3LocoCount" in line) && line.railLongV3LocoCount > 1
          || (("railLongV3Multihead" in line) && line.railLongV3Multihead));
}

/* Borne vanilla pour n locomotives de demi-tuile (un seul wagon de
 * demi-tuile). Un NewGRF ne peut jamais beneficier de cette hypothese :
 * AIVehicle.GetLength est obligatoire apres chaque BuildVehicle/MoveWagon. */
function OpexRailLongV3MultiNominalMax(platformLength, locoCount)
{
  if (platformLength < 1 || locoCount < 1 || locoCount > 3) return 0;
  return max(0, 2 * platformLength - locoCount);
}

/* Le moteur realiste applique masse_chargee * pente_pct * 100 N aux
 * elements en rampe. En l'absence de trace A* complet au devis, mettre
 * TOUT le convoi en montee est une borne conservatrice, non une moyenne
 * de pentes inventee. Le grade lu via OpexTrainSlopeSteepness est le
 * reglage reel (3 par defaut); la masse des wagons vient de
 * AICargo.GetWeight * vehicle.freight_trains dans le catalogue. */
function OpexRailLongV3MultiGradeSpeed(loco, wagon, wagons, locoCount, gradePct)
{
  if (loco == null || wagon == null || wagons < 1
      || locoCount < 1 || locoCount > 3 || gradePct < 0) return 0;
  local weight = loco.weight * locoCount + wagon.fullWeight * wagons;
  if (weight <= 0 || loco.speed <= 0 || loco.power <= 0
      || loco.tractiveEffort <= 0) return 0;
  local profile = {
    id = loco.id, speed = loco.speed, power = loco.power * locoCount,
    weight = loco.weight * locoCount,
    tractiveEffort = loco.tractiveEffort * locoCount
  };
  local ceiling = profile.speed;
  if (wagon.speed > 0 && wagon.speed < ceiling) ceiling = wagon.speed;
  local low = 0;
  local high = ceiling;
  local slopeResistance = weight * gradePct * 100;
  while (low < high) {
    local speed = (low + high + 1) / 2;
    local force = OpexRailForce(profile, speed);
    local resistance = OpexRailResistance(profile, weight, locoCount + wagons, speed)
        + slopeResistance;
    if (force > resistance) low = speed;
    else high = speed - 1;
  }
  return low;
}

/* Compare toutes les locomotives eligibles du catalogue et 1, 2 puis
 * 3 exemplaires identiques. Les doubles sont retenues UNIQUEMENT si
 * aucune motrice simple n'atteint 35 km/h sur la charge entiere en
 * pente maximale; idem triples uniquement apres refus doubles.
 * Entre candidats de meme nombre: cout achat + 5 ans d'entretien
 * minimum, avec vitesse effective comme departage.
 * Retourne un profil AGREGE pour l'economie et l'EngineID pour la pose. */
function OpexRailLongV3MultiChoose(catalog, cargo, platformLength, wagons, distance)
{
  if (!RAIL_LONG_V3 || catalog == null || !(cargo in catalog.wagonByCargo)
      || catalog.railLocos == null || distance <= 0 || wagons < 1
      || platformLength < 6 || catalog.railType < 0) return null;
  local wagon = catalog.wagonByCargo[cargo];
  if (wagon.capacity <= 0 || wagon.fullWeight <= wagon.weight) return null;
  local grade = OpexTrainSlopeSteepness();
  if (grade < 0 || grade > 10) return null;
  local best = null;
  local sawTraction = false;
  local sawCashRejection = false;
  for (local count = 1; count <= 3; count++) {
    if (wagons > OpexRailLongV3MultiNominalMax(platformLength, count)) continue;
    foreach (loco in catalog.railLocos) {
      if (loco == null || loco.power <= 0 || loco.weight <= 0
          || loco.tractiveEffort <= 0 || loco.speed <= 0 || loco.price <= 0
          || !AIEngine.IsBuildable(loco.id) || AIEngine.IsWagon(loco.id)
          || AIEngine.IsArticulated(loco.id)
          || AIEngine.GetCapacity(loco.id) > 0
          || !AIEngine.CanRunOnRail(loco.id, catalog.railType)
          || !AIEngine.HasPowerOnRail(loco.id, catalog.railType)) continue;
      local gradeSpeed = OpexRailLongV3MultiGradeSpeed(loco, wagon, wagons, count, grade);
      if (gradeSpeed < 35) continue;
      sawTraction = true;
      local fullPrice = count * loco.price + wagons * wagon.price;
      local cash = OpexAvailableCapital();
      if (cash < fullPrice + 50000) {
        sawCashRejection = true;
        continue;
      }
      local profile = clone loco;
      profile.power = loco.power * count;
      profile.weight = loco.weight * count;
      profile.tractiveEffort = loco.tractiveEffort * count;
      profile.price = loco.price * count;
      profile.runningCost = loco.runningCost * count;
      local flatSpeed = OpexRailEffectiveSpeed(profile, wagon, wagons, distance);
      /* min() dans NoAI exige des entiers, mais flatSpeed est un float. */
      local serviceSpeed = flatSpeed < gradeSpeed ? flatSpeed : gradeSpeed;
      if (serviceSpeed < 35) continue;
      local cost = profile.price + 5 * profile.runningCost;
      if (best == null || cost < best.cost
          || (cost == best.cost && serviceSpeed > best.speed))
        best = { count = count, loco = loco, profile = profile,
                 speed = serviceSpeed, gradeSpeed = gradeSpeed,
                 cost = cost, vehiclePrice = fullPrice, grade = grade };
    }
    if (best != null) {
      OpexRailLongV3MultiLog("choice",
          "locos=" + best.count + " engine=" + best.loco.id
          + " wagons=" + wagons + " grade=" + grade
          + " speed=" + best.speed + " price=" + best.vehiclePrice);
      return best; // minimum physique en nombre de motrices
    }
  }
  OpexRailLongV3MultiLog("choice_reject",
      "reason=" + (sawCashRejection ? "CASH" : (sawTraction ? "SPEED" : "TRACTION"))
      + " wagons=" + wagons + " platform=" + platformLength + " grade=" + grade);
  return null;
}

/* Derniere verification de la caisse, du rail et de la charge sur donnees
 * AIEngine live ; jamais la table de catalogue seule. */
function OpexRailLongV3MultiDepotReady(catalog, cargo, depot, loco, count, wagons, platform)
{
  if (!RAIL_LONG_V3 || !AIRail.IsRailDepotTile(depot)
      || !AIEngine.IsBuildable(loco.id) || AIEngine.IsWagon(loco.id)
      || AIEngine.IsArticulated(loco.id)
      || !AIEngine.HasPowerOnRail(loco.id, AIRail.GetRailType(depot))
      || !AIEngine.CanRunOnRail(loco.id, AIRail.GetRailType(depot))
      || !(cargo in catalog.wagonByCargo)
      || wagons > OpexRailLongV3MultiNominalMax(platform, count)) return false;
  local wagon = catalog.wagonByCargo[cargo];
  if (!AIEngine.IsBuildable(wagon.id) || !AIEngine.IsWagon(wagon.id)
      || AIEngine.GetCargoType(wagon.id) != cargo
      || AIEngine.GetPower(loco.id) != loco.power
      || AIEngine.GetMaxTractiveEffort(loco.id) != loco.tractiveEffort
      || AIEngine.GetWeight(loco.id) != loco.weight
      || AIEngine.GetPrice(loco.id) != loco.price
      || AIEngine.GetRunningCost(loco.id) != loco.runningCost
      || AIEngine.GetMaxSpeed(loco.id) != loco.speed
      || AIEngine.GetCapacity(wagon.id) != wagon.capacity
      || AIEngine.GetWeight(wagon.id) != wagon.weight
      || AIEngine.GetPrice(wagon.id) != wagon.price) return false;
  local loaded = AIEngine.GetWeight(wagon.id)
      + AICargo.GetWeight(cargo, AIEngine.GetCapacity(wagon.id))
          * AIGameSettings.GetValue("vehicle.freight_trains");
  if (loaded != wagon.fullWeight) return false;
  if (OpexRailLongV3MultiGradeSpeed(loco, wagon, wagons, count,
      OpexTrainSlopeSteepness()) < 35) return false;
  local money = count * AIEngine.GetPrice(loco.id) + wagons * AIEngine.GetPrice(wagon.id);
  return OpexAvailableCapital() >= money * 1.10 + 50000;
}

/* API commune OpexBuildTrains, et meme champ rollbackVehicles. Toute locomotive
 * supplementaire est posee en tete AVANT les wagons. Les indices sont
 * valides apres MoveWagon; si le moteur refuse un transfert de motrice,
 * l'essai est refuse sans mettre en circulation un train orphelin. */
function OpexRailLongV3MultiBuild(catalog, cargo, kind, depot, exitA, exitB,
                                  loco, locoCount, wagons, platformLength)
{
  local vehicles = [];
  local rollbackVehicles = [];
  local result = { built = 0, vehicles = vehicles, rollbackVehicles = rollbackVehicles,
                   failed = true, failure = "MULTI_PREFLIGHT", error = 0, diag = null,
                   trainLength = 0, locoLength = 0, wagonLength = 0,
                   v3LocoCount = locoCount };
  if (kind != "freight" || locoCount < 2 || locoCount > 3
      || !OpexRailLongV3MultiDepotReady(catalog, cargo, depot, loco,
                                        locoCount, wagons, platformLength)) return result;
  local maxLength = platformLength * 16;
  local wagon = catalog.wagonByCargo[cargo];
  local train = AIVehicle.BuildVehicle(depot, loco.id);
  if (!AIVehicle.IsValidVehicle(train)) {
    result.failure = "MULTI_ENGINE_FIRST";
    result.error = AIError.GetLastError();
    return result;
  }
  vehicles.append(train);
  rollbackVehicles.append(train);
  local length = AIVehicle.GetLength(train);
  if (length <= 0 || length > maxLength || AIVehicle.GetNumWagons(train) != 1
      || !AIVehicle.IsStoppedInDepot(train)) {
    result.failure = "MULTI_LENGTH_LOCO";
    return result;
  }
  for (local n = 1; n < locoCount; n++) {
    local second = AIVehicle.BuildVehicle(depot, loco.id);
    if (!AIVehicle.IsValidVehicle(second)) {
      result.failure = "MULTI_ENGINE";
      result.error = AIError.GetLastError();
      return result;
    }
    rollbackVehicles.append(second);
    local partLength = AIVehicle.GetLength(second);
    if (partLength <= 0 || length + partLength > maxLength
        || AIVehicle.GetNumWagons(second) != 1
        || !AIVehicle.IsStoppedInDepot(second)) {
      result.failure = "MULTI_LENGTH_LOCO";
      return result;
    }
    if (!AIVehicle.MoveWagon(second, 0, train, n - 1)) {
      result.failure = "MULTI_MOVE_ENGINE";
      result.error = AIError.GetLastError();
      return result;
    }
    length = AIVehicle.GetLength(train);
    if (!AIVehicle.IsValidVehicle(train) || AIVehicle.GetNumWagons(train) != n + 1
        || !AIVehicle.IsStoppedInDepot(train) || length <= 0 || length > maxLength) {
      result.failure = "MULTI_ENGINE_ORDER";
      return result;
    }
    for (local j = 0; j <= n; j++)
      if (AIVehicle.GetWagonEngineType(train, j) != loco.id) {
        result.failure = "MULTI_ENGINE_ORDER";
        return result;
      }
  }
  result.locoLength = length;
  for (local w = 0; w < wagons; w++) {
    local car = AIVehicle.BuildVehicle(depot, wagon.id);
    if (!AIVehicle.IsValidVehicle(car)) {
      result.failure = "MULTI_WAGON_BUILD";
      result.error = AIError.GetLastError();
      return result;
    }
    rollbackVehicles.append(car);
    local carLength = AIVehicle.GetLength(car);
    if (carLength <= 0 || length + carLength > maxLength
        || !AIVehicle.IsStoppedInDepot(car)) {
      result.failure = "MULTI_LENGTH_WAGON";
      return result;
    }
    if (!AIVehicle.MoveWagon(car, 0, train, locoCount + w - 1)) {
      result.failure = "MULTI_MOVE_WAGON";
      result.error = AIError.GetLastError();
      return result;
    }
    length = AIVehicle.GetLength(train);
    result.wagonLength = carLength;
    if (!AIVehicle.IsValidVehicle(train) || AIVehicle.GetNumWagons(train) != locoCount + w + 1
        || !AIVehicle.IsStoppedInDepot(train) || length > maxLength || length <= 0) {
      result.failure = "MULTI_WAGON_ORDER";
      return result;
    }
    if (AIVehicle.GetWagonEngineType(train, locoCount + w) != wagon.id) {
      result.failure = "MULTI_WAGON_ORDER";
      return result;
    }
  }
  if (AIVehicle.GetNumWagons(train) != locoCount + wagons
      || AIVehicle.GetCapacity(train, cargo) != wagons * wagon.capacity
      || wagons * wagon.capacity < 200) {
    result.failure = "MULTI_CAPACITY";
    return result;
  }
  local flagsA = AIOrder.OF_FULL_LOAD_ANY | AIOrder.OF_NON_STOP_INTERMEDIATE;
  local flagsB = AIOrder.OF_NONE | AIOrder.OF_NON_STOP_INTERMEDIATE;
  if (!AIOrder.AppendOrder(train, exitA, flagsA)
      || !AIOrder.AppendOrder(train, exitB, flagsB)
      || AIOrder.GetOrderCount(train) != 2) {
    result.failure = "MULTI_ORDER";
    result.error = AIError.GetLastError();
    return result;
  }
  result.built = 1;
  result.failed = false;
  result.failure = "";
  result.trainLength = length;
  OpexRailLongV3MultiLog("assembled", "train=" + train + " locos=" + locoCount
      + " wagons=" + wagons + " length16=" + length
      + " capacity=" + AIVehicle.GetCapacity(train, cargo));
  return result; // start par constructeur APRES validation supplementaire
}
