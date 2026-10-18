/* V257 : dimensionner UNE rame sur la production observable, sans facteur de note.
 * La repartition equilibre capacite/production (AAAHogEx-115,
 * estimator.nut::TrainPlan.IncreaseNumWagon:1985-1998), sans reprendre son implementation.
 * Bornes physiques : quai trouve, station_spread et vehicle.max_train_length ;
 * conversion nominale vanilla de catalog.nut, puis mesure reelle dans OpexBuildTrains.
 * Aucun nombre de wagons impose independamment de ces limites. */
function OpexV257ConsistPlan(catalog, cargo, monthly, kind, secondary, platform, distance, choices, wagonOverride = null)
{
  local wagon = wagonOverride != null ? wagonOverride : catalog.wagonByCargo[cargo];
  local wagon2 = secondary != null && secondary.monthly > 0
      && (secondary.cargo in catalog.wagonByCargo) ? catalog.wagonByCargo[secondary.cargo] : null;
  local limit = platform > 0 ? platform : catalog.platformLength;
  if (catalog.maxTrainLength > 0 && catalog.maxTrainLength < limit) limit = catalog.maxTrainLength;
  local maximum = OpexRailNominalMaxWagons(limit);
  if (maximum > choices.len()) maximum = choices.len();
  local last = null;
  for (local total = 1; total <= maximum; total++) {
    local n2 = 0;
    if (wagon2 != null && total > 1) {
      local need1 = monthly.tofloat() / wagon.capacity;
      local need2 = secondary.monthly.tofloat() / wagon2.capacity;
      /* Arrondi au wagon le plus proche ; au moins un wagon de chaque cargo si possible. */
      n2 = (total * need2 / (need1 + need2) + 0.5).tointeger();
      if (n2 < 1) n2 = 1;
      if (n2 >= total) n2 = total - 1;
    }
    local n1 = total - n2;
    local loco = choices[total - 1];
    if (loco == null) continue;
    local physical = clone wagon;
    if (n2 > 0) {
      physical.fullWeight = (n1 * wagon.fullWeight + n2 * wagon2.fullWeight).tofloat() / total;
      if (wagon2.speed > 0 && (physical.speed <= 0 || wagon2.speed < physical.speed)) physical.speed = wagon2.speed;
    }
    /* Pas de cache mono-cargo : sa cle ne distingue pas la composition mixte. */
    local speed = OpexRailEffectiveSpeed(loco, physical, total, distance);
    if (speed < 1) continue;
    // Conversion physique partagee avec OpexLineEconomics, docs/mecanique_jeu.md section 2.
    local days = distance.tofloat() / (0.036 * speed);
    if (days < 1) days = 1;
    local dwell = OpexRailStationDwellDays(wagon);
    if (n2 > 0) {
      local dwell2 = OpexRailStationDwellDays(wagon2);
      if (dwell2 > dwell) dwell = dwell2;
    }
    local trips = OpexLoadedTripsPerMonth(days + dwell, 2 * days + dwell, kind == "pax");
    last = { wagons = n1, wagons2 = n2, loco = loco, speed = speed,
             days = days, trips = trips, wagon2 = n2 > 0 ? wagon2 : null };
    if (n1 * wagon.capacity * trips >= monthly
        && (wagon2 == null || (n2 > 0 && n2 * wagon2.capacity * trips >= secondary.monthly))) break;
  }
  return last;
}

/* Une fois les emprises choisies : verifier le gisement secondaire reellement couvert.
 * GetCargoProduction compte des PRODUCTEURS, pas des unites mensuelles
 * (15.3 src/script/api/script_tile.hpp:390-404, station_cmd.cpp:GetProductionAroundTiles).
 * Ne jamais le substituer a GetLastMonthProduction. La production des deux villes
 * reste une borne d'offre de la paire, pas une prevision CargoDist origine/destination.
 * GetCargoAcceptance est en huitiemes (script_tile.hpp:385 : >= 8 = acceptation). */
function OpexV257ObservePair(candidate, planA, planB)
{
  local coverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  if (!("cargo2" in candidate) || !("monthly2" in candidate)) return;
  foreach (plan in [planA, planB]) {
    local horizontal = plan.step == AIMap.GetTileIndex(1, 0);
    local w = horizontal ? plan.length : 1;
    local h = horizontal ? 1 : plan.length;
    if ((candidate.kind == "pax" || plan == planB)
        && AITile.GetCargoAcceptance(plan.anchor, candidate.cargo2, w, h, coverage) < 8) {
      candidate.monthly2 = 0;
      return;
    }
  }
  if (OpexV207PlatformUnionValue(planA, candidate.cargo2, coverage) <= 0
      || (candidate.kind == "pax" && OpexV207PlatformUnionValue(planB, candidate.cargo2, coverage) <= 0)) {
    candidate.monthly2 = 0;
  }
}
