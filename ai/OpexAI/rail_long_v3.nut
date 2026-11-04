/* RAIL-LONG v3 : selection fret 7/6 et certification des rames longues.
 * Les compositions de 2/3 motrices sont construites par
 * rail_long_v3_multi.nut ; les extensions de lignes existantes restent
 * dans le module distinct de l'autre worker.
 *
 * Les fonctions ci-dessous sont sans effet physique ; OpexBuildTrains
 * conserve la mesure AIVehicle.GetLength de chaque unite et le rollback
 * historique. La certification post-construction empeche qu'un trim V301
 * fasse passer une rame devenue trop courte pour une composition v3. */

function OpexRailLongV3Log(event, candidate, reason)
{
  if (!DECISION_LOG) return;
  OpexDecide("RAIL_LONG_V3", "event=" + event
      + " src=" + (("src" in candidate) ? candidate.src : -1)
      + " dst=" + (("dst" in candidate) ? candidate.dst : -1)
      + " reason=" + reason);
}

/* Gabarit 7 sinon 6 sinon le plan court existant. On ne se base pas sur
 * la demande estimee d'une rame de 3 wagons, mais le vrai devis long
 * (prix, revenu, vitesse, capital) sera controle apres les sites. */
function OpexRailLongV3SiteLength(catalog, candidate)
{
  if (!RAIL_LONG_V3 || candidate.kind != "freight"
      || OpexV233LIs(candidate) || OpexV190Active() || OpexV198Active()
      || (("railLongShortRetry" in candidate) && candidate.railLongShortRetry)
      || !(candidate.cargo in catalog.wagonByCargo)
      || !("monthly" in candidate) || candidate.monthly <= 0)
    return 0;
  local limit = catalog.platformLength;
  if (catalog.maxTrainLength > 0 && catalog.maxTrainLength < limit)
    limit = catalog.maxTrainLength;
  if (limit < 6) return 0;
  /* Pas de seuil forfaitaire 1970-1972 : le prix du projet LONG, y compris
   * les 8+ wagons, est calcule dans OpexRailPlatformPlans et compare a la
   * caisse avec une reserve de 50k + 10% du devis. */
  return limit >= 7 ? 7 : 6;
}

/* Une, deux ou trois locomotives : la borne initiale ne sait que
 * convertir le besoin de fret en wagons ; le gabarit exact depend du
 * nombre reel de motrices et est revu dans MultiChoose puis MultiBuild. */
function OpexRailLongV3WagonFloor(wagon, platformLength)
{
  if (platformLength < 6 || wagon == null || wagon.capacity <= 0) return 0;
  local minWagons = max(8, OpexCeilDiv(200, wagon.capacity));
  return minWagons <= OpexRailNominalMaxWagons(platformLength)
      ? minWagons : 0;
}

/* Les API du catalogue mesurent puissance, effort et masse du fret plein
 * (AICargo.GetWeight * vehicle.freight_trains). La pente reelle n'est
 * connue qu'apres A* et le profil sur pentes reste une porte distincte.
 * Ne jamais pretendre que l'absence de cette preuve autorise une motrice
 * supplementaire ou un train roulant en pente. */
function OpexRailLongV3SingleTractionOK(loco, wagon, wagons)
{
  if (loco == null || wagon == null || loco.power <= 0
      || loco.tractiveEffort <= 0 || loco.weight <= 0
      || wagon.fullWeight <= wagon.weight || wagons < 1) return false;
  local trainWeight = OpexRailTrainWeight(loco, wagon, wagons);
  return trainWeight > 0 && OpexRailAcceleration(loco, wagon, wagons, 25) > 0
      && OpexRailCruiseSpeed(loco, wagon, wagons) >= 25;
}

/* Apres OpexBuildTrains : la longueur reelle, la composition et la
 * capacite doivent correspondre a l'engagement financier avant que le
 * moteur ne demarre le moindre train. Un echec remonte au rollback
 * physique du constructeur V190/normal. */
function OpexRailLongV3TrainsCertified(candidate, trains, catalog)
{
  if (!RAIL_LONG_V3 || !("railLongV3Chosen" in candidate)
      || !candidate.railLongV3Chosen) return true;
  if (trains == null || trains.failed || trains.built < 1
      || !(candidate.cargo in catalog.wagonByCargo)) return false;
  local floor = OpexRailLongV3WagonFloor(catalog.wagonByCargo[candidate.cargo],
      candidate.platformLength);
  if (floor == 0 || candidate.wagons < floor || candidate.platformLength < 6)
    return false;
  local locoCount = ("railLongV3LocoCount" in candidate)
      ? candidate.railLongV3LocoCount : 1;
  if (locoCount < 1 || locoCount > 3
      || candidate.wagons > OpexRailLongV3MultiNominalMax(candidate.platformLength, locoCount))
    return false;
  foreach (train in trains.vehicles) {
    if (!AIVehicle.IsValidVehicle(train)
        || AIVehicle.GetLength(train) > candidate.platformLength * 16
        || !AIVehicle.IsStoppedInDepot(train)
        || AIVehicle.GetNumWagons(train) != locoCount + candidate.wagons
        || candidate.wagons < floor
        || AIVehicle.GetCapacity(train, candidate.cargo) < 200) {
      OpexRailLongV3Log("train_reject", candidate, "PHYSICAL_LENGTH_CAPACITY");
      return false;
    }
    for (local locoIndex = 0; locoIndex < locoCount; locoIndex++)
      if (AIVehicle.GetWagonEngineType(train, locoIndex) != candidate.loco.id)
        return false;
    for (local wagonIndex = locoCount; wagonIndex < locoCount + candidate.wagons; wagonIndex++)
      if (AIVehicle.GetWagonEngineType(train, wagonIndex) != catalog.wagonByCargo[candidate.cargo].id)
        return false;
  }
  return trains.vehicles.len() == trains.built;
}
