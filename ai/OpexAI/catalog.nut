/* Etage 0 : le catalogue.
 *
 * Mesure 2026-08-28 (results/catalogue_churn.json, 1970-1989) : un rafraichissement complet
 * coute ~21 500 opcodes. Sonde 1950-2000 (results/catalogue_churn_1950_2000.json) : electrique
 * 1967, INTERNATIONAL 1990, monorail 2000, maglev pas encore. Une campagne 1970-1989 a deja
 * l'electrique ; elle ne voit pas INTERNATIONAL. On prend le DERNIER type de rail disponible
 * (ci-dessous) : en 1970 c'est ELECTRIC, en 2000 ce serait MONO -- hors de nos 20 ans.
 * Toujours aucun motif d'optimiser le rafraichissement annuel.
 */

/* Nombre nominal de wagons qui tient dans un quai de `platformLength` tuiles.
 *
 * La campagne 42 mesure 8/16 pour la locomotive et 8/16 par wagon. Un quai de p tuiles mesure
 * p*16, donc 8 + w*8 <= p*16 donne w <= 2*p-1. Cette borne est celle appliquee par
 * OpexBuildTrains, pas une marge cachee. NoAI 15.3 ne donne pas la longueur avant construction :
 * le constructeur relit donc chaque vehicule reel et rejette un NewGRF plus long plutot que de
 * croire cette deduction vanilla. */
function OpexRailNominalMaxWagons(platformLength)
{
  local wagons = 2 * platformLength - 1;
  return wagons > 0 ? wagons : 0;
}

/* Marge de croissance des nouvelles rames, exprimee en wagons et non en tuiles : le modele
 * choisit d'abord le besoin de transport, puis traduit ce besoin en quai. Les longueurs vanilla
 * mesurees dans la campagne 42 sont 8/16 pour la locomotive et 8/16 par wagon. Une tuile vaut
 * 16/16, donc DEUX wagons representent exactement une tuile de croissance. C'est la plus petite
 * marge non nulle qui change la geometrie ; une marge de 1 wagon alternerait sans raison entre 0
 * et 1 tuile selon la parite du convoi. La securite n'est pas une tuile inventee : le test reel
 * dans OpexBuildTrains conserve la condition exacte  longueur_rame <= p*16. */
const RAIL_PLATFORM_GROWTH_WAGONS = 2;

/* Inverse entier de OpexRailNominalMaxWagons. Un wagon utile demande 1 tuile, car 8 + 8 =
 * 16/16 : c'est le plancher physique, ensuite protege par la mesure reelle du constructeur. */
function OpexRailPlatformLengthForWagons(wagons)
{
  if (wagons < 1) return 0;
  return (wagons + 2) / 2;
}

function OpexRailMinimumPlatformLength()
{
  return OpexRailPlatformLengthForWagons(1);
}

/* Le reglage de partie reste une borne haute, jamais la longueur ordonnee par defaut. Ajouter
 * deux wagons puis inverser la capacite nominale donne le quai voulu ; le min protege le cas ou
 * la partie limite deja le quai avant que la marge ne tienne. */
function OpexRailWantedPlatformLength(targetWagons, gameMaximum)
{
  local wanted = OpexRailPlatformLengthForWagons(targetWagons + RAIL_PLATFORM_GROWTH_WAGONS);
  return wanted < gameMaximum ? wanted : gameMaximum;
}

/* Force de traction et resistance exactement dans les unites du moteur, sur rail plat.
 *
 * OpenTTD 15.3 calcule F = min(TE * 1000, power * 746 * 18 / (5 * vitesse)) ; la resistance
 * mecanique vaut masse * (10 + 15 * (512 + vitesse) / 512), plus la trainee. Les 10 et 15 sont
 * les deux termes du source (essieux et roulement), pas un abattement calibre. La trainee par
 * defaut du jeu vaut 14 * clamp(2048 / vmax, 1, 192) * (1 + 3 * elements / 20) * v^2 / 1000.
 *
 * L'API ne livre pas la propriete NewGRF de trainee : cette formule est donc verifiee pour les
 * vehicules de base de la partie gelee, et reste une HYPOTHESE explicitement non generalisable aux
 * NewGRF. Le calcul est fait au catalogue, jamais dans une boucle de moteurs par candidat. */
function OpexRailForce(loco, speed)
{
  if (speed < 1) speed = 1;
  local powerForce = (loco.power * 746 * 18) / (speed * 5);
  local tractiveForce = loco.tractiveEffort * 1000;
  return powerForce < tractiveForce ? powerForce : tractiveForce;
}

function OpexRailResistance(loco, totalWeight, parts, speed)
{
  local airDrag = 2048 / loco.speed;
  if (airDrag < 1) airDrag = 1;
  if (airDrag > 192) airDrag = 192;
  local rolling = 15 * (512 + speed) / 512;
  local air = 14 * airDrag * (1 + (3 * parts) / 20.0) * speed * speed / 1000.0;
  return totalWeight * (10 + rolling) + air;
}

function OpexRailTrainWeight(loco, wagon, wagons)
{
  return loco.weight + wagons * wagon.fullWeight;
}

/* Vitesse de croisiere possible sur plat, AVANT la distance et les arrets. La recherche dichotomique
 * ne touche aucune API et a au plus log2(vitesse catalogue) tours ; meme une locomotive a 65 535
 * km/h en demanderait 16. Ce cout borne est paye une fois par couple loco/wagon/nombre de wagons au
 * catalogue annuel, et jamais dans le classement de milliers de candidats. */
function OpexRailCruiseSpeed(loco, wagon, wagons)
{
  local ceiling = loco.speed;
  if (wagon.speed > 0 && wagon.speed < ceiling) ceiling = wagon.speed;
  if (ceiling < 1) return 0;

  local totalWeight = OpexRailTrainWeight(loco, wagon, wagons);
  local parts = 1 + wagons;
  local low = 0;
  local high = ceiling;
  while (low < high) {
    local middle = (low + high + 1) / 2;
    if (OpexRailForce(loco, middle) > OpexRailResistance(loco, totalWeight, parts, middle)) {
      low = middle;
    } else {
      high = middle - 1;
    }
  }
  return low;
}

/* Acceleration OpenTTD en vitesse interne par demi-tick : (F - R) / (masse * 4).
 * L'effort de traction intervient ici, donc une locomotive qui atteint la meme vitesse de croisiere
 * mais peine a lancer le convoi lourd perd le departage du catalogue. */
function OpexRailAcceleration(loco, wagon, wagons, speed)
{
  local totalWeight = OpexRailTrainWeight(loco, wagon, wagons);
  if (totalWeight <= 0) return 0;
  local force = OpexRailForce(loco, speed);
  local resistance = OpexRailResistance(loco, totalWeight, 1 + wagons, speed);
  if (force <= resistance) return 0;
  local acceleration = (force - resistance) / (totalWeight * 4);
  return acceleration > 0 ? acceleration : 0;
}

/* Vitesse moyenne entre deux arrets, pas vitesse catalogue. Le moteur met a jour deux fois par tick
 * et il y a 74 ticks/jour : l'acceleration calculee ci-dessus devient a * 148 / 256 km/h par jour.
 * On integre un profil trapezoidal (ou triangulaire si la distance est trop courte) avec la conversion
 * verifiee de docs/mecanique_jeu.md section 2 : 0.036 tuile/jour par km/h.
 *
 * Les virages, pentes, ponts et temps de chargement restent INCONNUS avant A*. Le source impose
 * 61 km/h sur un angle droit et 111 a courbure 2 ; aucun pourcentage de virages n'est invente.
 * Mesure 2026-08-30 (results/opex_speed_yield.json, n=832) : mediane reel/catalogue 0,96,
 * reel/traction 1,18. Le 70 % etait trop pessimiste. Pas de retuning. */
function OpexRailEffectiveSpeed(loco, wagon, wagons, distance, profile = null, cruiseCache = null, freightCruiseProfile = false, freightSpeedDetailProfile = false, freightAccelerationCache = false, freightEffectiveSpeedProfile = false)
{
  if (profile != null) {
    local key = loco.id + "|" + wagon.id + "|" + wagons + "|" + distance;
    if (key in profile.paxSpeedKeys) profile.paxSpeedCacheableHits++;
    else {
      profile.paxSpeedKeys[key] <- true;
      profile.paxSpeedUniqueKeys++;
    }
    if (freightEffectiveSpeedProfile) {
      if (key in profile.freightSpeedKeys) profile.freightSpeedCacheableHits++;
      else { profile.freightSpeedKeys[key] <- true; profile.freightSpeedUniqueKeys++; }
      profile.freightSpeedCalls++;
    }
    local cruiseKey = loco.id + "|" + wagon.id + "|" + wagons;
    if (cruiseKey in profile.paxCruiseKeys) profile.paxCruiseCacheableHits++;
    else {
      profile.paxCruiseKeys[cruiseKey] <- true;
      profile.paxCruiseUniqueKeys++;
    }
    /* C41.37 : exactement la cle que le cache fret proposera, mais isolee du pax. */
    if (freightCruiseProfile) {
      if (cruiseKey in profile.freightCruiseKeys) profile.freightCruiseCacheableHits++;
      else {
        profile.freightCruiseKeys[cruiseKey] <- true;
        profile.freightCruiseUniqueKeys++;
      }
    }
  }
  local cruiseKey = loco.id + "|" + wagon.id + "|" + wagons;
  local cruise = null;
  if (cruiseCache != null && cruiseKey in cruiseCache) {
    cruise = cruiseCache[cruiseKey].cruise;
  } else {
    local cruiseMark = profile != null ? OpexOpsMeasureBegin() : null;
    cruise = OpexRailCruiseSpeed(loco, wagon, wagons);
    if (profile != null) {
      profile.paxCruiseOps += OpexOpsMeasureEnd(cruiseMark);
      profile.paxCruiseCalls++;
      if (freightCruiseProfile) profile.freightCruiseCalls++;
    }
    if (cruiseCache != null) cruiseCache[cruiseKey] <- { cruise = cruise };
  }
  if (cruise < 1 || distance < 1) return 0;

  local halfSpeed = cruise / 2;
  if (halfSpeed < 1) halfSpeed = 1;
  local acceleration = null;
  if (freightAccelerationCache && cruiseCache != null && cruiseKey in cruiseCache && ("acceleration" in cruiseCache[cruiseKey])) {
    acceleration = cruiseCache[cruiseKey].acceleration;
  } else {
    local accelerationMark = profile != null ? OpexOpsMeasureBegin() : null;
    acceleration = OpexRailAcceleration(loco, wagon, wagons, halfSpeed);
    if (profile != null) {
      local accelerationOps = OpexOpsMeasureEnd(accelerationMark);
      profile.paxAccelerationOps += accelerationOps;
      if (freightSpeedDetailProfile) { profile.freightAccelerationOps += accelerationOps; profile.freightAccelerationCalls++; }
    }
    if (freightAccelerationCache && cruiseCache != null) cruiseCache[cruiseKey].acceleration <- acceleration;
  }
  if (acceleration < 1) return 0;
  local integrationMark = profile != null ? OpexOpsMeasureBegin() : null;
  local speedPerDay = acceleration * 148.0 / 256.0;
  local startDays = cruise / speedPerDay;
  local startDistance = 0.036 * (cruise / 2.0) * startDays;
  local travelDays = 0.0;

  if (distance >= 2 * startDistance) {
    travelDays = 2 * startDays + (distance - 2 * startDistance) / (0.036 * cruise);
  } else {
    local peak = sqrt(distance * speedPerDay / 0.036);
    travelDays = 2 * peak / speedPerDay;
  }
  if (travelDays <= 0) {
    if (profile != null) profile.paxIntegrationOps += OpexOpsMeasureEnd(integrationMark);
    return 0;
  }
  local result = distance / (0.036 * travelDays);
  if (profile != null) {
    local integrationOps = OpexOpsMeasureEnd(integrationMark);
    profile.paxIntegrationOps += integrationOps;
    if (freightSpeedDetailProfile) { profile.freightIntegrationOps += integrationOps; profile.freightIntegrationCalls++; }
  }
  return result;
}

/* Safe AIR Pareto prefilter. A choice is removed only when another aircraft has the same
 * compatibility domain (planeType), capacity and speed, while being no more expensive to buy/run
 * and having at least the same range. Those inputs make the economic curve decision-equivalent. */
function OpexAirRangeDominates(a, b)
{
  if (a == null || b == null) return false;
  if (a.planeType != b.planeType || a.capacity != b.capacity || a.speed != b.speed) return false;
  local rangeA = a.maxOrderDistance == 0 ? 2147483647 : a.maxOrderDistance;
  local rangeB = b.maxOrderDistance == 0 ? 2147483647 : b.maxOrderDistance;
  if (a.price > b.price || a.runningCost > b.runningCost || rangeA < rangeB) return false;
  return a.price < b.price || a.runningCost < b.runningCost || rangeA > rangeB;
}

function OpexAirSafeParetoChoices(choices)
{
  local kept = [];
  if (choices == null) return kept;
  foreach (candidate in choices) {
    local dominated = false;
    foreach (other in choices) {
      if (candidate == other) continue;
      if (OpexAirRangeDominates(other, candidate)) { dominated = true; break; }
    }
    if (!dominated) kept.append(candidate);
  }
  return kept;
}

class OpexCatalog {
  towns = null;        // [{id, tile, pop}]
  townAcceptors = null; // cargo -> [{id, tile, pop}]
  industries = null;   // [{id, tile, type}]
  producers = null;    // cargo -> [index dans industries]
  acceptors = null;    // cargo -> [index dans industries]
  cargos = null;       // [cargo_id]
  paxCargo = -1;
  mailCargo = -1;
  year = 0;

  railType = -1;       // type de rail courant
  /* `loco` reste le plus rapide CATALOGUE pour le panneau annuel historique. La decision par
   * ligne passe exclusivement par locoByCargoWagons, qui depend de la rame reellement chargee. */
  loco = null;
  railLocos = null;          // profils complets des locomotives avec puissance, masse et TE
  wagonByCargo = null;       // cargo -> {id, capacity, speed, price, weight, fullWeight}
  locoByCargoWagons = null;  // cargo -> [1 wagon..max] -> meilleur profil deja choisi
  wagonChoicesByCargo = null; // M3 probe only: cargo -> tous les wagons + choix loco associes
  platformLength = 0;        // AIGameSettings station.station_spread, lu une fois par annee
  railCoverage = 0;          // rayon exact de AIStation.STATION_TRAIN, lu avec les autres proprietes rail
  freightTrainMultiplier = 1;
  costTrackPerTile = 0;
  costStation = 0;
  costRailDepot = 0;

  airport = null;      // {type, width, height, coverage, price, maintenance} ou null
  plane = null;        // {id, capacity, speed, price, runningCost, maxOrderDistance} ou null
  airCombos = null;    // [{kind="large"|"small", airport={...}, plane={...}}] ou null
  airAirportChoices = null; // types d'aeroport disponibles, sans avion preselectionne
  airPlaneChoicesByAirport = null; // M3/C68: airport type -> appareils compatibles
  airParetoChoicesByAirport = null; // AIR lifecycle: safe Pareto subset
  airParetoStats = null; // {raw, kept, pruned}

  ships = null;        // [{id, capacity, speed, price, runningCost, maxOrderDistance}]
  maxShipPrice = 0;
  costDock = 0;
  costWaterDepot = 0;

  roadType = -1;              // route normale (pas tram), ou -1 si indisponible
  /* cargo -> {id, capacity, speed, price, runningCost, ageYears}. Un SEUL vehicule retenu par
   * cargo (le plus capacitaire), bus comme camion : le choix du type d'arret ne se deduit pas du
   * moteur mais du cargo (CC_PASSENGERS => arret de bus, sinon aire de chargement), cf.
   * docs/mecanique_jeu.md S11 -- un bus ne chargera JAMAIS sur une aire de chargement camion. */
  roadEngineByCargo = null;
  roadEngineChoicesByCargo = null; // M3 probe only: cargo -> vehicules compatibles
  maxRoadVehiclePrice = 0;
  costRoadPerTile = 0;
  costRoadBusStop = 0;
  costRoadTruckStop = 0;
  costRoadDepot = 0;

  /* Frontieres modales de l'epoque (OpexRefreshEpochBounds). Null avant le
   * premier refresh ; les generateurs passent par OpexCatalogBounds. */
  bounds = null;
  airBoundsEnvelope = null; // enveloppe AIR multi-appareils decisionnelle
  airBoundsLegacy = null;   // temoin passif de l'ancienne borne mono-bestPlane
  _ticksAnchorDate = -1;
  _ticksAnchorTick = -1;

  constructor()
  {
    this.towns = [];
    this.townAcceptors = {};
    this.industries = [];
    this.producers = {};
    this.acceptors = {};
    this.cargos = [];
    this.wagonByCargo = {};
    this.railLocos = [];
    this.locoByCargoWagons = {};
    this.wagonChoicesByCargo = {};
    this.ships = [];
    this.roadEngineByCargo = {};
    this.roadEngineChoicesByCargo = {};
    this.airAirportChoices = [];
    this.airPlaneChoicesByAirport = {};
    this.airParetoChoicesByAirport = {};
    this.airParetoStats = { raw = 0, kept = 0, pruned = 0 };
    this.bounds = null;
    this.airBoundsEnvelope = null;
    this.airBoundsLegacy = null;
    this._ticksAnchorDate = -1;
    this._ticksAnchorTick = -1;
  }

  function refresh(budget, year);
  function _refreshCargos();
  function _refreshTowns();
  function _refreshIndustries();
  function _refreshRail();
  function _refreshAir();
  function _refreshWater();
  /* C41.1 : point d'entree public d'une seule sous-regeneration materiel. */
  function refreshWater(budget);
  /* C41.2 : meme filtre unitaire que _refreshWater(), sans enumerer le catalogue entier. */
  function isWaterEngineRelevant(engine);
  function _refreshRoad();
  /* C41.15 : point d'entree cible, homologue de refreshWater(). */
  function refreshRoad(budget);
  function _cargoArray(list);
}

/* M3/G12 : reproduit STRICTEMENT le departage locomotive courant pour un wagon alternatif.
 * Cette fonction n'est appelee que lorsque equipment_roi_probe=1 ; le chemin livre continue
 * d'utiliser la boucle historique inline ci-dessous. Le resultat sert uniquement a donner a
 * OpexLineEconomics un couple wagon/locomotive physiquement coherent pour le diagnostic. */
function OpexM3RailLocoChoices(railLocos, wagon, maxWagons)
{
  local choices = [];
  if (railLocos == null || railLocos.len() == 0 || maxWagons < 1) return choices;
  for (local wagons = 1; wagons <= maxWagons; wagons++) {
    local best = null;
    local bestSpeed = -1;
    local bestAcceleration = -1;
    local topCeiling = railLocos[0].speed;
    if (wagon.speed > 0 && wagon.speed < topCeiling) topCeiling = wagon.speed;
    local topSustained = false;
    foreach (loco in railLocos) {
      if (topSustained && loco.speed < topCeiling) continue;
      local ceiling = loco.speed;
      if (wagon.speed > 0 && wagon.speed < ceiling) ceiling = wagon.speed;
      local totalWeight = loco.weight + wagons * wagon.fullWeight;
      local parts = 1 + wagons;
      local airDrag = 2048 / loco.speed;
      if (airDrag < 1) airDrag = 1;
      if (airDrag > 192) airDrag = 192;
      local airFactor = 14 * airDrag * (1 + (3 * parts) / 20.0) / 1000.0;
      local low = 0;
      local high = ceiling;
      while (low < high) {
        local middle = (low + high + 1) / 2;
        local powerForce = (loco.power * 746 * 18) / (middle * 5);
        local tractiveForce = loco.tractiveEffort * 1000;
        local force = powerForce < tractiveForce ? powerForce : tractiveForce;
        local rolling = 15 * (512 + middle) / 512;
        local resistance = totalWeight * (10 + rolling) + airFactor * middle * middle;
        if (force > resistance) low = middle;
        else high = middle - 1;
      }
      local cruise = low;
      if (cruise < 1) continue;
      if (loco.id == railLocos[0].id && cruise == topCeiling) topSustained = true;
      local halfSpeed = cruise / 2;
      if (halfSpeed < 1) halfSpeed = 1;
      local powerForce = (loco.power * 746 * 18) / (halfSpeed * 5);
      local tractiveForce = loco.tractiveEffort * 1000;
      local force = powerForce < tractiveForce ? powerForce : tractiveForce;
      local rolling = 15 * (512 + halfSpeed) / 512;
      local resistance = totalWeight * (10 + rolling) + airFactor * halfSpeed * halfSpeed;
      local acceleration = force > resistance ? (force - resistance) / (totalWeight * 4) : 0;
      if (best == null || cruise > bestSpeed ||
          (cruise == bestSpeed && acceleration > bestAcceleration) ||
          (cruise == bestSpeed && acceleration == bestAcceleration && loco.runningCost < best.runningCost) ||
          (cruise == bestSpeed && acceleration == bestAcceleration && loco.runningCost == best.runningCost &&
           loco.price < best.price)) {
        best = loco;
        bestSpeed = cruise;
        bestAcceleration = acceleration;
      }
    }
    choices.append(best);
  }
  return choices;
}

/* Le materiel roulant disponible AUJOURD'HUI, et ce que coute la voie.
 *
 * Necessaire a l'etage 1 : sans la vitesse du convoi on ne sait pas estimer le temps de trajet,
 * donc pas les penalites de retard, qui sont la moitie du revenu (docs/mecanique_jeu.md §1-2).
 * Le parc evolue reellement : sur 20 ans le nombre de moteurs routiers passe de 12 a 22 et les
 * avions de 13 a 18 (results/catalogue_churn.json) -- d'ou le rafraichissement annuel. */
function OpexCatalog::_refreshRail()
{
  this.loco = null;
  this.railLocos = [];
  this.wagonByCargo = {};
  this.locoByCargoWagons = {};
  this.wagonChoicesByCargo = {};

  /* `station_spread` est la borne que CmdBuildRailStation controle sur `length`. Dans OpenTTD
   * 15.3 elle est entiere, entre 4 et 64, et vaut 12 dans la configuration gelee ; on lit donc la
   * partie, jamais un "7" suppose. Une valeur invalide signifie API/reglage indisponible : mieux
   * vaut alors rendre le rail non constructible que fabriquer une longueur silencieuse. */
  this.platformLength = AIGameSettings.GetValue("station.station_spread");
  this.freightTrainMultiplier = AIGameSettings.GetValue("vehicle.freight_trains");
  this.railCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  if (this.platformLength < 1 || this.freightTrainMultiplier < 1 || this.railCoverage < 1) return;

  /* Dernier type disponible. 1970 = ELECTRIC (intro 1967). 2000 = MONO : ne pas
   * allonger une campagne jusque-la sans figer le type. Maglev pas encore en 2000
   * (results/catalogue_churn_1950_2000.json). */
  local types = AIRailTypeList();
  types.Valuate(AIRail.IsRailTypeAvailable);
  types.KeepValue(1);
  /* Le choix ne doit PAS dependre de l'ordre d'iteration : le tri par defaut d'une AIList est
   * SORT_BY_VALUE DECROISSANT (script_list.cpp:397-403), donc le Valuate ci-dessus change cet
   * ordre. L'ancien "le dernier gagne" rendait le type de rail dependant du tri -- invisible a
   * 3 ans de partie ou un seul type est disponible, et instable des qu'il y en a plusieurs.
   * Voir docs/mecanique_jeu.md S15.1. */
  local chosen = -1;
  for (local t = types.Begin(); !types.IsEnd(); t = types.Next()) {
    if (t > chosen) chosen = t;
  }
  if (chosen < 0) return;
  this.railType = chosen;
  AIRail.SetCurrentRailType(chosen);
  this.costTrackPerTile = AIRail.GetBuildCost(chosen, AIRail.BT_TRACK);
  this.costStation = AIRail.GetBuildCost(chosen, AIRail.BT_STATION);
  /* Le depot rail etait le seul cout d'infrastructure absent du modele, alors que la route
   * et l'eau comptent le leur et que builder_rail.nut le paie reellement. */
  this.costRailDepot = AIRail.GetBuildCost(chosen, AIRail.BT_DEPOT);

  local engines = AIEngineList(AIVehicle.VT_RAIL);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    if (AIEngine.IsWagon(e)) {
      local cargo = AIEngine.GetCargoType(e);
      local capacity = AIEngine.GetCapacity(e);
      if (capacity <= 0) continue;
      /* Un seul wagon retenu par cargo : le plus capacitaire. La sonde M3 conserve en parallele
       * les alternatives SANS changer ce departage, y compris son premier-gagne en cas d'egalite. */
      local replaces = !(cargo in this.wagonByCargo) || capacity > this.wagonByCargo[cargo].capacity;
      if (!replaces && !EQUIPMENT_ROI_PROBE) continue;
      local cargoWeight = AICargo.GetWeight(cargo, capacity);
      /* Le moteur applique `vehicle.freight_trains` aux seuls cargos fret dans Train::GetWeight.
       * AICargo.GetWeight livre le poids nu, donc le multiplicateur lu ci-dessus est indispensable
       * pour que la masse utilisee par le catalogue soit celle du convoi plein reel. */
      if (AICargo.IsFreight(cargo)) cargoWeight *= this.freightTrainMultiplier;
      local entry = {
        id = e, capacity = capacity, speed = AIEngine.GetMaxSpeed(e), price = AIEngine.GetPrice(e),
        weight = AIEngine.GetWeight(e), fullWeight = AIEngine.GetWeight(e) + cargoWeight,
        runningCost = AIEngine.GetRunningCost(e), ageYears = AIEngine.GetMaxAge(e) / 365,
      };
      if (EQUIPMENT_ROI_PROBE) {
        if (!(cargo in this.wagonChoicesByCargo)) this.wagonChoicesByCargo.rawset(cargo, []);
        this.wagonChoicesByCargo[cargo].append(entry);
      }
      if (replaces) {
        if (cargo in this.wagonByCargo) this.wagonByCargo[cargo] = entry;
        else this.wagonByCargo.rawset(cargo, entry);
      }
    } else {
      /* ⚠️ PIEGE D'API, verifie le 2026-08-28. CanRunOnRail() ne suffit PAS : une locomotive
       * ELECTRIQUE "peut rouler" sur une voie non electrifiee (elle peut y etre tractee), mais
       * elle n'y a AUCUNE PUISSANCE. Symptome observe : AIEngine.IsBuildable et CanRunOnRail
       * rendaient tous deux vrai, le depot etait valide, la tresorerie suffisante -- et
       * AIVehicle.BuildVehicle echouait avec ERR_UNKNOWN sur les 100 tentatives. Le diagnostic
       * qui a tranche : engine_rail = 1 (electrifie) contre depot_rail = 0.
       * HasPowerOnRail() est le bon predicat. */
      if (!AIEngine.CanRunOnRail(e, chosen)) continue;
      if (!AIEngine.HasPowerOnRail(e, chosen)) continue;
      local speed = AIEngine.GetMaxSpeed(e);
      local power = AIEngine.GetPower(e);
      local weight = AIEngine.GetWeight(e);
      local tractiveEffort = AIEngine.GetMaxTractiveEffort(e);
      if (speed <= 0 || power <= 0 || weight <= 0 || tractiveEffort <= 0) continue;
      local entry = {
        id = e, speed = speed, power = power, weight = weight, tractiveEffort = tractiveEffort,
        price = AIEngine.GetPrice(e), runningCost = AIEngine.GetRunningCost(e),
        ageYears = AIEngine.GetMaxAge(e) / 365,
      };
      this.railLocos.append(entry);
      /* Conserve seulement le comparateur historique pour OL annuel : il ne decide plus RIEN. */
      if (this.loco == null || speed > this.loco.speed) {
        this.loco = entry;
      }
    }
  }

  /* Precalcul de la seule boucle couteuse : cargos x compositions x locomotives, une fois par
   * annee. Le catalogue complet mesurait 21 492 opcodes (0,008 % du budget de partie) ; cette
   * table supprime ensuite toute boucle moteur du chemin OpexLineEconomics, appele pour chaque
   * paire ville/industrie. La cle est le nombre de wagons, donc la selection voit bien la charge
   * reelle, pas une rame fictive de cinq wagons.
   *
   * La dichotomie est ecrite ici, plutot que par les appels imbriques OpexRailCruiseSpeed(),
   * OpexRailForce() et OpexRailResistance(). A 12 tuiles, au plus 23 wagons et 16 iterations par
   * moteur, les appels Squirrel faisaient monter ce seul cache a 1,12 M opcodes/an au smoke 42,
   * soit 52 fois les 21 492 du catalogue mesure. Les memes equations, deroulees sans fermeture ni
   * appel, gardent le cout annualise et mesurable par `cat_rail`, sans payer ce facteur 52.
   *
   * Les profils sont tries par vitesse decroissante avant ce cache. Si le premier soutient son
   * plafond, un moteur dont le plafond est inferieur ne peut mathematiquement ni le depasser ni
   * l'egaler : il est saute. Les seuls ex aequo possibles (meme plafond de wagon ou de moteur)
   * restent evalues pour conserver le departage acceleration, cout annuel, capital. C'est une
   * equivalence, pas un echantillonnage : si le plus rapide ne soutient pas son plafond, tous les
   * moteurs sont de nouveau evalues. Le smoke 42 mesure apres ce garde 175 768 opcodes en 1970,
   * soit 0,066 % du meme budget ou 21 492 valaient 0,008 % : c'est un cout annuel borne et non
   * le million repete qui aurait rendu le catalogue disproportionne. */
  local maxWagons = OpexRailNominalMaxWagons(this.platformLength);
  if (maxWagons < 1 || this.railLocos.len() == 0) return;
  for (local i = 1; i < this.railLocos.len(); i++) {
    local current = this.railLocos[i];
    local j = i - 1;
    while (j >= 0 && this.railLocos[j].speed < current.speed) {
      this.railLocos[j + 1] = this.railLocos[j];
      j--;
    }
    this.railLocos[j + 1] = current;
  }
  foreach (cargo, wagon in this.wagonByCargo) {
    local choices = [];
    for (local wagons = 1; wagons <= maxWagons; wagons++) {
      local best = null;
      local bestSpeed = -1;
      local bestAcceleration = -1;
      local topCeiling = this.railLocos[0].speed;
      if (wagon.speed > 0 && wagon.speed < topCeiling) topCeiling = wagon.speed;
      local topSustained = false;
      foreach (loco in this.railLocos) {
        if (topSustained && loco.speed < topCeiling) continue;
        local ceiling = loco.speed;
        if (wagon.speed > 0 && wagon.speed < ceiling) ceiling = wagon.speed;
        local totalWeight = loco.weight + wagons * wagon.fullWeight;
        local parts = 1 + wagons;
        local airDrag = 2048 / loco.speed;
        if (airDrag < 1) airDrag = 1;
        if (airDrag > 192) airDrag = 192;
        local airFactor = 14 * airDrag * (1 + (3 * parts) / 20.0) / 1000.0;
        local low = 0;
        local high = ceiling;
        while (low < high) {
          local middle = (low + high + 1) / 2;
          local powerForce = (loco.power * 746 * 18) / (middle * 5);
          local tractiveForce = loco.tractiveEffort * 1000;
          local force = powerForce < tractiveForce ? powerForce : tractiveForce;
          local rolling = 15 * (512 + middle) / 512;
          local resistance = totalWeight * (10 + rolling) + airFactor * middle * middle;
          if (force > resistance) low = middle;
          else high = middle - 1;
        }
        local cruise = low;
        if (cruise < 1) continue;
        if (loco.id == this.railLocos[0].id && cruise == topCeiling) topSustained = true;
        local halfSpeed = cruise / 2;
        if (halfSpeed < 1) halfSpeed = 1;
        local powerForce = (loco.power * 746 * 18) / (halfSpeed * 5);
        local tractiveForce = loco.tractiveEffort * 1000;
        local force = powerForce < tractiveForce ? powerForce : tractiveForce;
        local rolling = 15 * (512 + halfSpeed) / 512;
        local resistance = totalWeight * (10 + rolling) + airFactor * halfSpeed * halfSpeed;
        local acceleration = force > resistance ? (force - resistance) / (totalWeight * 4) : 0;
        /* Regle de selection, dans cet ordre : vitesse soutenable de la rame pleine, acceleration
         * a mi-vitesse (donc effort de traction et puissance), cout annuel, puis capital. Les deux
         * derniers ne servent qu'a departager deux locomotives que la physique rend equivalentes. */
        if (best == null || cruise > bestSpeed ||
            (cruise == bestSpeed && acceleration > bestAcceleration) ||
            (cruise == bestSpeed && acceleration == bestAcceleration && loco.runningCost < best.runningCost) ||
            (cruise == bestSpeed && acceleration == bestAcceleration && loco.runningCost == best.runningCost &&
             loco.price < best.price)) {
          best = loco;
          bestSpeed = cruise;
          bestAcceleration = acceleration;
        }
      }
      choices.append(best);
    }
    this.locoByCargoWagons.rawset(cargo, choices);
  }
  if (EQUIPMENT_ROI_PROBE) {
    foreach (cargo, wagons in this.wagonChoicesByCargo) {
      if (!(cargo in this.wagonByCargo) || !(cargo in this.locoByCargoWagons)) continue;
      local selectedId = this.wagonByCargo[cargo].id;
      foreach (wagon in wagons) {
        wagon.m3LocoChoices <- (wagon.id == selectedId)
            ? this.locoByCargoWagons[cargo]
            : OpexM3RailLocoChoices(this.railLocos, wagon, maxWagons);
      }
    }
  }
}

/* Deux types d'aeroports et appareils :
 * 1. Grand aeroport (AT_INTERNATIONAL, AT_METROPOLITAN, AT_LARGE) avec gros avion (PT_BIG_PLANE) ou petit avion
 * 2. Petit aeroport (AT_COMMUTER, AT_SMALL) avec petit avion (PT_SMALL_PLANE) STRICTEMENT (les gros avions y sont interdits). */
function OpexCatalog::_refreshAir()
{
  this.airport = null;
  this.plane = null;
  this.airCombos = [];
  this.airAirportChoices = [];
  this.airPlaneChoicesByAirport = {};
  this.airParetoChoicesByAirport = {};
  this.airParetoStats = { raw = 0, kept = 0, pruned = 0 };
  if (this.paxCargo < 0) return;

  local airportLargeTypes = [
    { type = AIAirport.AT_INTERNATIONAL, allowBig = true, name = "INTERNATIONAL" },
    { type = AIAirport.AT_METROPOLITAN, allowBig = true, name = "METROPOLITAN" },
    { type = AIAirport.AT_LARGE, allowBig = true, name = "LARGE" },
  ];
  local airportSmallTypes = [
    { type = AIAirport.AT_COMMUTER, allowBig = false, name = "COMMUTER" },
    { type = AIAirport.AT_SMALL, allowBig = false, name = "SMALL" },
  ];

  local engines = AIEngineList(AIVehicle.VT_AIR);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  local keepPlaneChoices = EQUIPMENT_ROI_PROBE || AIR_ROUTE_PLANE_SELECTION
      || AIR_EQUIPMENT_REGRET_PROBE || AIR_BEST_EQUIPMENT;

  // 1. Combo Grand Aeroport + Avion compatible
  foreach (choice in airportLargeTypes) {
    if (!AIAirport.IsValidAirportType(choice.type)) continue;
    local best = null;
    local probeChoices = [];
    for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
      if (!AIEngine.CanRefitCargo(e, this.paxCargo)) continue;
      local planeType = AIEngine.GetPlaneType(e);
      if (planeType != AIAirport.PT_SMALL_PLANE && planeType != AIAirport.PT_BIG_PLANE) continue;
      local capacity = AIEngine.GetCapacity(e);
      local speed = AIEngine.GetMaxSpeed(e);
      if (capacity <= 0) continue;
      local isBig = (planeType == AIAirport.PT_BIG_PLANE);
      local bestIsBig = (best != null && best.isBig);
      local replaces = best == null || (isBig && !bestIsBig) ||
          (isBig == bestIsBig && (capacity > best.capacity || (capacity == best.capacity && speed > best.speed)));
      if (!replaces && !keepPlaneChoices) continue;
      local entry = {
        id = e, defaultCargo = AIEngine.GetCargoType(e), capacity = capacity, speed = speed,
        price = AIEngine.GetPrice(e), runningCost = AIEngine.GetRunningCost(e),
        maxOrderDistance = AIEngine.GetMaximumOrderDistance(e), planeType = planeType, isBig = isBig,
      };
      if (keepPlaneChoices) probeChoices.append(entry);
      if (replaces) best = entry;
    }
    if (keepPlaneChoices && probeChoices.len() > 0) {
      this.airPlaneChoicesByAirport.rawset(choice.type, probeChoices);
      local pareto = OpexAirSafeParetoChoices(probeChoices);
      this.airParetoChoicesByAirport.rawset(choice.type, pareto);
      this.airParetoStats.raw += probeChoices.len();
      this.airParetoStats.kept += pareto.len();
      this.airParetoStats.pruned += probeChoices.len() - pareto.len();
    }
    if (best != null) {
      local ap = {
        type = choice.type,
        kind = "large",
        name = choice.name,
        allowBig = true,
        width = AIAirport.GetAirportWidth(choice.type),
        height = AIAirport.GetAirportHeight(choice.type),
        coverage = AIAirport.GetAirportCoverageRadius(choice.type),
        price = AIAirport.GetPrice(choice.type),
        maintenance = AIAirport.GetMonthlyMaintenanceCost(choice.type),
      };
      this.airAirportChoices.append(ap);
      this.airCombos.append({ kind = "large", airport = ap, plane = best });
      if (this.airport == null) {
        this.airport = ap;
        this.plane = best;
      }
    }
  }

  // 2. Combo Petit Aeroport + Petit Avion (strictement PT_SMALL_PLANE)
  foreach (choice in airportSmallTypes) {
    if (!AIAirport.IsValidAirportType(choice.type)) continue;
    local best = null;
    local probeChoices = [];
    for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
      if (!AIEngine.CanRefitCargo(e, this.paxCargo)) continue;
      local planeType = AIEngine.GetPlaneType(e);
      // Règle d'or : les gros avions ne vont JAMAIS dans les petits aeroports
      if (planeType != AIAirport.PT_SMALL_PLANE) continue;
      local capacity = AIEngine.GetCapacity(e);
      local speed = AIEngine.GetMaxSpeed(e);
      if (capacity <= 0) continue;
      local replaces = best == null || capacity > best.capacity ||
          (capacity == best.capacity && speed > best.speed);
      if (!replaces && !keepPlaneChoices) continue;
      local entry = {
        id = e, defaultCargo = AIEngine.GetCargoType(e), capacity = capacity, speed = speed,
        price = AIEngine.GetPrice(e), runningCost = AIEngine.GetRunningCost(e),
        maxOrderDistance = AIEngine.GetMaximumOrderDistance(e), planeType = planeType, isBig = false,
      };
      if (keepPlaneChoices) probeChoices.append(entry);
      if (replaces) best = entry;
    }
    if (keepPlaneChoices && probeChoices.len() > 0) {
      this.airPlaneChoicesByAirport.rawset(choice.type, probeChoices);
      local pareto = OpexAirSafeParetoChoices(probeChoices);
      this.airParetoChoicesByAirport.rawset(choice.type, pareto);
      this.airParetoStats.raw += probeChoices.len();
      this.airParetoStats.kept += pareto.len();
      this.airParetoStats.pruned += probeChoices.len() - pareto.len();
    }
    if (best != null) {
      local ap = {
        type = choice.type,
        kind = "small",
        name = choice.name,
        allowBig = false,
        width = AIAirport.GetAirportWidth(choice.type),
        height = AIAirport.GetAirportHeight(choice.type),
        coverage = AIAirport.GetAirportCoverageRadius(choice.type),
        price = AIAirport.GetPrice(choice.type),
        maintenance = AIAirport.GetMonthlyMaintenanceCost(choice.type),
      };
      this.airAirportChoices.append(ap);
      this.airCombos.append({ kind = "small", airport = ap, plane = best });
      if (this.airport == null) {
        this.airport = ap;
        this.plane = best;
      }
    }
  }
  AILog.Info("_refreshAir: combos=" + this.airCombos.len()
    + " airport=" + (this.airport != null ? "YES" : "NULL")
    + " plane=" + (this.plane != null ? "YES" : "NULL"));
}

/* Coques refittables : la capacite reelle depend du depot et du GRF. */
function OpexCatalog::_refreshWater()
{
  this.ships = [];
  this.maxShipPrice = 0;
  this.costDock = AIMarine.GetBuildCost(AIMarine.BT_DOCK);
  this.costWaterDepot = AIMarine.GetBuildCost(AIMarine.BT_DEPOT);
  if (this.paxCargo < 0) return;
  local engines = AIEngineList(AIVehicle.VT_WATER);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    if (!AIEngine.CanRefitCargo(e, this.paxCargo)) continue;
    local capacity = AIEngine.GetCapacity(e);
    local speed = AIEngine.GetMaxSpeed(e);
    local ship = { id = e, capacity = capacity, speed = speed, price = AIEngine.GetPrice(e),
                   runningCost = AIEngine.GetRunningCost(e),
                   maxOrderDistance = AIEngine.GetMaximumOrderDistance(e) };
    this.ships.append(ship);
    if (ship.price > this.maxShipPrice) this.maxShipPrice = ship.price;
  }
}

/* C41.1 : ne touche ni villes, ni industries, ni les autres modes. Le budget passe par la meme
 * mesure que refresh(), pour que le cout cible soit comparable au cout historique cat_water. */
function OpexCatalog::refreshWater(budget)
{
  budget.begin();
  this._refreshWater();
  return budget.end("cat_water_targeted");
}

/* C41.2 : le catalogue eau conserve tous les navires constructibles et refittables passagers,
 * sans autre score ni plafond. Ce predicat est donc exactement le garde local qui permet de ne
 * pas armer une regeneration pour un moteur que _refreshWater() ecarterait. */
function OpexCatalog::isWaterEngineRelevant(engine)
{
  if (this.paxCargo < 0 || !AIEngine.IsValidEngine(engine)) return false;
  if (AIEngine.GetVehicleType(engine) != AIVehicle.VT_WATER) return false;
  return AIEngine.IsBuildable(engine) && AIEngine.CanRefitCargo(engine, this.paxCargo);
}

/* Route : l'equivalent du piege CanRunOnRail/HasPowerOnRail existe bien. Un vehicule peut etre
 * compatible avec un type de route sans y avoir de puissance ; le catalogue exige les deux, puis
 * CanRefitCargo (ou le cargo deja configure) avant de le proposer au constructeur. La capacite
 * apres refit reste verifiee dans builder_road.nut, car un NewGRF peut la changer selon le depot.
 *
 * Depuis le 2026-08-29 le catalogue ne connait plus "les bus" mais UN vehicule par cargo, bus ou
 * camion : le mode route ne construit plus une liaison passagers unique mais autant de petites
 * lignes que le classement en propose, dont des lignes de fret (voir candidates.nut,
 * OpexRoadCandidates). Le cout des DEUX types d'arret est releve, car le type est impose par le
 * cargo, pas choisi.
 *
 * ⚠️ Vehicules articules ECARTES : ils ne peuvent pas utiliser un arret en cul-de-sac, et c'est la
 * seule disposition que builder_road.nut sait poser (les arrets traversants ont ete mesures puis
 * abandonnes -- 912 232 opcodes pour aucun gain, cf. docs/opexai_mode_route et le commentaire en
 * tete de builder_road.nut). Les laisser entrer donnerait un moteur que le depot accepte de
 * construire et que l'arret refuse de charger. */
function OpexCatalog::_refreshRoad()
{
  this.roadType = -1;
  this.roadEngineByCargo = {};
  this.roadEngineChoicesByCargo = {};
  this.maxRoadVehiclePrice = 0;
  this.costRoadPerTile = 0;
  this.costRoadBusStop = 0;
  this.costRoadTruckStop = 0;
  this.costRoadDepot = 0;
  if (!AIRoad.IsRoadTypeAvailable(AIRoad.ROADTYPE_ROAD)) return;
  this.roadType = AIRoad.ROADTYPE_ROAD;
  AIRoad.SetCurrentRoadType(this.roadType);
  this.costRoadPerTile = AIRoad.GetBuildCost(this.roadType, AIRoad.BT_ROAD);
  this.costRoadBusStop = AIRoad.GetBuildCost(this.roadType, AIRoad.BT_BUS_STOP);
  this.costRoadTruckStop = AIRoad.GetBuildCost(this.roadType, AIRoad.BT_TRUCK_STOP);
  this.costRoadDepot = AIRoad.GetBuildCost(this.roadType, AIRoad.BT_DEPOT);

  /* Deux passes plutot qu'une boucle imbriquee sur AIEngineList : les predicats chers
   * (IsBuildable, CanRunOnRoad, HasPowerOnRoad, IsArticulated) sont evalues UNE fois par moteur,
   * et seul CanRefitCargo -- le seul qui depende du cargo -- est repaye pour chaque paire. Sur le
   * parc mesure (12 a 22 moteurs routiers en 20 ans, results/catalogue_churn.json) et une douzaine de
   * cargos, cela reste tres en dessous du budget annuel du catalogue. */
  local usable = [];
  local engines = AIEngineList(AIVehicle.VT_ROAD);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  engines.Valuate(AIEngine.IsArticulated);
  engines.KeepValue(0);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    if (!AIEngine.CanRunOnRoad(e, this.roadType)) continue;
    if (!AIEngine.HasPowerOnRoad(e, this.roadType)) continue;
    local capacity = AIEngine.GetCapacity(e);
    if (capacity <= 0) continue;
    usable.append({
      id = e, defaultCargo = AIEngine.GetCargoType(e), capacity = capacity,
      speed = AIEngine.GetMaxSpeed(e), price = AIEngine.GetPrice(e),
      runningCost = AIEngine.GetRunningCost(e),
      /* GetMaxAge rend des jours, comme pour la locomotive. */
      ageYears = AIEngine.GetMaxAge(e) / 365,
    });
  }

  foreach (cargo in this.cargos) {
    local best = null;
    local probeChoices = [];
    foreach (engine in usable) {
      if (engine.defaultCargo != cargo && !AIEngine.CanRefitCargo(engine.id, cargo)) continue;
      if (EQUIPMENT_ROI_PROBE) probeChoices.append(engine);
      /* capacity est celle du cargo D'ORIGINE : apres refit elle peut changer (le GRF decide).
       * C'est une approximation assumee pour le CLASSEMENT ; la valeur qui sert au dimensionnement
       * reel est relue depuis le depot par GetBuildWithRefitCapacity dans builder_road.nut. */
      if (best == null || engine.capacity > best.capacity ||
          (engine.capacity == best.capacity && engine.speed > best.speed)) {
        best = engine;
      }
    }
    if (best == null) continue;
    this.roadEngineByCargo.rawset(cargo, best);
    if (EQUIPMENT_ROI_PROBE) this.roadEngineChoicesByCargo.rawset(cargo, probeChoices);
    if (best.price > this.maxRoadVehiclePrice) this.maxRoadVehiclePrice = best.price;
  }
}

/* C41.15 : ne touche ni cargos, ni villes, ni les autres modes. Les candidats route et le
 * portefeuille restent volontairement sales : seul le catalogue materiel est acquitte. */
function OpexCatalog::refreshRoad(budget)
{
  budget.begin();
  this._refreshRoad();
  return budget.end("cat_road_targeted");
}

function OpexCatalog::_refreshCargos()
{
  this.cargos = [];
  this.paxCargo = -1;
  this.mailCargo = -1;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    this.cargos.append(c);
    if (this.paxCargo < 0 && AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) this.paxCargo = c;
    if (this.mailCargo < 0 && AICargo.HasCargoClass(c, AICargo.CC_MAIL)) this.mailCargo = c;
  }
}

function OpexCatalog::_refreshTowns()
{
  this.towns = [];
  this.townAcceptors = {};
  local list = AITownList();
  for (local t = list.Begin(); !list.IsEnd(); t = list.Next()) {
    local tile = AITown.GetLocation(t);
    local pop = AITown.GetPopulation(t);
    local houses = AITown.GetHouseCount(t);
    local townObj = {
      id = t,
      tile = tile,
      pop = pop,
      houses = houses,
    };
    this.towns.append(townObj);

    /* Indexation des marchandises complexes et cargos urbains acceptes par la ville (Goods, Food, Mail, etc.) */
    foreach (cargo in this.cargos) {
      if (cargo == this.paxCargo) continue;
      local acceptance = AITile.GetCargoAcceptance(tile, cargo, 2, 2, this.railCoverage > 0 ? this.railCoverage : 4);
      if (acceptance >= 8 || (pop >= 300 && AICargo.HasCargoClass(cargo, AICargo.CC_EXPRESS))) {
        if (!(cargo in this.townAcceptors)) this.townAcceptors.rawset(cargo, []);
        this.townAcceptors[cargo].append(townObj);
      }
    }
  }
}

function OpexCatalog::_refreshIndustries()
{
  this.industries = [];
  this.producers = {};
  this.acceptors = {};

  local list = AIIndustryList();
  for (local i = list.Begin(); !list.IsEnd(); i = list.Next()) {
    if (!AIIndustry.IsValidIndustry(i)) continue;
    local type = AIIndustry.GetIndustryType(i);
    if (!AIIndustryType.IsValidIndustryType(type)) continue;
    this.industries.append({ id = i, tile = AIIndustry.GetLocation(i), type = type });
  }

  /* Les cargos produits/acceptes se lisent sur le TYPE d'industrie, pas sur l'instance
   * (AIIndustry.IsCargoProduced n'existe pas). On memorise par type : il y a une poignee de
   * types pour des dizaines d'industries, donc les listes ne sont lues qu'une fois chacune. */
  local producedByType = {};
  local acceptedByType = {};
  for (local k = 0; k < this.industries.len(); k++) {
    local type = this.industries[k].type;
    if (!(type in producedByType)) {
      local prodList = AIIndustryType.IsValidIndustryType(type) ? AIIndustryType.GetProducedCargo(type) : null;
      local accList = AIIndustryType.IsValidIndustryType(type) ? AIIndustryType.GetAcceptedCargo(type) : null;
      producedByType.rawset(type, this._cargoArray(prodList));
      acceptedByType.rawset(type, this._cargoArray(accList));
    }
    local isTransformer = (producedByType[type].len() > 0 && acceptedByType[type].len() > 0);
    this.industries[k].isTransformer <- isTransformer;
    foreach (cargo in producedByType[type]) {
      if (!(cargo in this.producers)) this.producers.rawset(cargo, []);
      this.producers[cargo].append(k);
    }
    foreach (cargo in acceptedByType[type]) {
      if (!(cargo in this.acceptors)) this.acceptors.rawset(cargo, []);
      this.acceptors[cargo].append(k);
    }
  }
}

function OpexCatalog::_cargoArray(list)
{
  local out = [];
  if (list == null) return out;
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) out.append(c);
  return out;
}

function OpexCatalog::refresh(budget, year)
{
  this.year = year;

  budget.begin();
  this._refreshCargos();
  budget.end("cat_cargos");

  budget.begin();
  this._refreshRail();
  budget.end("cat_rail");

  budget.begin();
  this._refreshTowns();
  budget.end("cat_towns");

  budget.begin();
  this._refreshIndustries();
  budget.end("cat_industries");

  /* Propose du 2026-09-08 (docs/taches.md C43/E3) : au lieu d'une fenetre de selection fixe,
   * la caler sur le contenu reel de la carte plutot que sur une constante posee a vue. Inerte a
   * 0 (defaut) : PROJECT_TOP_K reste au reglage project_top_k, comme avant cette mecanique. */
  if (PROJECT_TOP_K_DYNAMIC) {
    local dynamic = this.towns.len() + this.industries.len();
    if (dynamic < 16) dynamic = 16;
    if (dynamic > 128) dynamic = 128;
    PROJECT_TOP_K = dynamic;
    if (DECISION_LOG) {
      OpexDecide("TOP_K_DYNAMIC", "towns=" + this.towns.len() + " industries="
                 + this.industries.len() + " top_k=" + PROJECT_TOP_K);
    }
  }

  budget.begin();
  this._refreshAir();
  budget.end("cat_air");

  budget.begin();
  this._refreshWater();
  budget.end("cat_water");

  /* Le catalogue route n'est rafraichi que si le mode est actif : a road_mode = 0, le chemin
   * d'opcodes de la baseline rail reste EXACTEMENT celui des campagnes anterieures, ce qui rend le
   * banc apparie lisible (une trajectoire ne diverge que par une decision, pas par un debit). */
  if (ROAD_BUILD_ENABLED) {
    budget.begin();
    this._refreshRoad();
    budget.end("cat_road");
  }

  budget.begin();
  OpexRefreshEpochBounds(this);
  budget.end("cat_bounds");
}
