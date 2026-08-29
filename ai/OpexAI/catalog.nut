/* Etage 0 : le catalogue.
 *
 * Mesure faite le 2026-08-28 (ai/CatalogProbe, docs/catalogue_churn.json) : un rafraichissement
 * complet coute ~21 500 opcodes, soit 0,008 % du budget d'une partie si on le refait chaque
 * annee. Il n'y a donc AUCUNE raison de l'optimiser -- pas de rafraichissement incrementiel, pas
 * de planification sur les dates d'introduction connues. On refait tout, tous les ans.
 *
 * Ce qui bouge reellement en 20 ans : le nombre de villes ne change pas, les industries subissent
 * ~2,6 % de churn par an, et le parc de moteurs route/avion croit fortement (+83 % / +38 %).
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
 * pourtant 61 km/h sur un angle droit et 111 a courbure 2 ; aucun pourcentage de virages non mesure
 * ne leur est donc invente ici. Cette limite est documentee comme hypothese a verifier, pas masquee
 * par le precedent SPEED_EFFICIENCY_PCT = 70. */
function OpexRailEffectiveSpeed(loco, wagon, wagons, distance)
{
  local cruise = OpexRailCruiseSpeed(loco, wagon, wagons);
  if (cruise < 1 || distance < 1) return 0;

  local halfSpeed = cruise / 2;
  if (halfSpeed < 1) halfSpeed = 1;
  local acceleration = OpexRailAcceleration(loco, wagon, wagons, halfSpeed);
  if (acceleration < 1) return 0;
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
  if (travelDays <= 0) return 0;
  return distance / (0.036 * travelDays);
}

class OpexCatalog {
  towns = null;        // [{id, tile, pop}]
  industries = null;   // [{id, tile, type}]
  producers = null;    // cargo -> [index dans industries]
  acceptors = null;    // cargo -> [index dans industries]
  cargos = null;       // [cargo_id]
  paxCargo = -1;
  year = 0;

  railType = -1;       // type de rail courant
  /* `loco` reste le plus rapide CATALOGUE pour le panneau annuel historique. La decision par
   * ligne passe exclusivement par locoByCargoWagons, qui depend de la rame reellement chargee. */
  loco = null;
  railLocos = null;          // profils complets des locomotives avec puissance, masse et TE
  wagonByCargo = null;       // cargo -> {id, capacity, speed, price, weight, fullWeight}
  locoByCargoWagons = null;  // cargo -> [1 wagon..max] -> meilleur profil deja choisi
  platformLength = 0;        // AIGameSettings station.station_spread, lu une fois par annee
  railCoverage = 0;          // rayon exact de AIStation.STATION_TRAIN, lu avec les autres proprietes rail
  freightTrainMultiplier = 1;
  costTrackPerTile = 0;
  costStation = 0;

  airport = null;      // {type, width, height, coverage, price, maintenance} ou null
  plane = null;        // {id, capacity, speed, price, runningCost, maxOrderDistance} ou null

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
  maxRoadVehiclePrice = 0;
  costRoadPerTile = 0;
  costRoadBusStop = 0;
  costRoadTruckStop = 0;
  costRoadDepot = 0;

  constructor()
  {
    this.towns = [];
    this.industries = [];
    this.producers = {};
    this.acceptors = {};
    this.cargos = [];
    this.wagonByCargo = {};
    this.railLocos = [];
    this.locoByCargoWagons = {};
    this.ships = [];
    this.roadEngineByCargo = {};
  }

  function refresh(budget, year);
  function _refreshCargos();
  function _refreshTowns();
  function _refreshIndustries();
  function _refreshRail();
  function _refreshAir();
  function _refreshWater();
  function _refreshRoad();
  function _cargoArray(list);
}

/* Le materiel roulant disponible AUJOURD'HUI, et ce que coute la voie.
 *
 * Necessaire a l'etage 1 : sans la vitesse du convoi on ne sait pas estimer le temps de trajet,
 * donc pas les penalites de retard, qui sont la moitie du revenu (docs/mecanique_jeu.md §1-2).
 * Le parc evolue reellement : sur 20 ans le nombre de moteurs routiers passe de 12 a 22 et les
 * avions de 13 a 18 (docs/catalogue_churn.json) -- d'ou le rafraichissement annuel. */
function OpexCatalog::_refreshRail()
{
  this.loco = null;
  this.railLocos = [];
  this.wagonByCargo = {};
  this.locoByCargoWagons = {};

  /* `station_spread` est la borne que CmdBuildRailStation controle sur `length`. Dans OpenTTD
   * 15.3 elle est entiere, entre 4 et 64, et vaut 12 dans la configuration gelee ; on lit donc la
   * partie, jamais un "7" suppose. Une valeur invalide signifie API/reglage indisponible : mieux
   * vaut alors rendre le rail non constructible que fabriquer une longueur silencieuse. */
  this.platformLength = AIGameSettings.GetValue("station.station_spread");
  this.freightTrainMultiplier = AIGameSettings.GetValue("vehicle.freight_trains");
  this.railCoverage = AIStation.GetCoverageRadius(AIStation.STATION_TRAIN);
  if (this.platformLength < 1 || this.freightTrainMultiplier < 1 || this.railCoverage < 1) return;

  local types = AIRailTypeList();
  local chosen = -1;
  for (local t = types.Begin(); !types.IsEnd(); t = types.Next()) {
    if (AIRail.IsRailTypeAvailable(t)) chosen = t;
  }
  if (chosen < 0) return;
  this.railType = chosen;
  AIRail.SetCurrentRailType(chosen);
  this.costTrackPerTile = AIRail.GetBuildCost(chosen, AIRail.BT_TRACK);
  this.costStation = AIRail.GetBuildCost(chosen, AIRail.BT_STATION);

  local engines = AIEngineList(AIVehicle.VT_RAIL);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    if (!AIEngine.IsBuildable(e)) continue;
    if (AIEngine.IsWagon(e)) {
      local cargo = AIEngine.GetCargoType(e);
      local capacity = AIEngine.GetCapacity(e);
      if (capacity <= 0) continue;
      /* Un seul wagon retenu par cargo : le plus capacitaire. */
      if (!(cargo in this.wagonByCargo) || capacity > this.wagonByCargo[cargo].capacity) {
        local cargoWeight = AICargo.GetWeight(cargo, capacity);
        /* Le moteur applique `vehicle.freight_trains` aux seuls cargos fret dans Train::GetWeight.
         * AICargo.GetWeight livre le poids nu, donc le multiplicateur lu ci-dessus est indispensable
         * pour que la masse utilisee par le catalogue soit celle du convoi plein reel. */
        if (AICargo.IsFreight(cargo)) cargoWeight *= this.freightTrainMultiplier;
        local entry = {
          id = e, capacity = capacity, speed = AIEngine.GetMaxSpeed(e), price = AIEngine.GetPrice(e),
          weight = AIEngine.GetWeight(e), fullWeight = AIEngine.GetWeight(e) + cargoWeight,
        };
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
}

/* Le premier aeroport est volontairement simple : LARGE tant qu'il est disponible (c'est le cas
 * du vanilla 1970), sinon SMALL puis COMMUTER. Une piste courte ne recoit jamais un gros avion.
 * On choisit, pour le type d'aeroport retenu, l'appareil passagers refittable le plus capacitaire. */
function OpexCatalog::_refreshAir()
{
  this.airport = null;
  this.plane = null;
  if (this.paxCargo < 0) return;

  local airportTypes = [
    { type = AIAirport.AT_LARGE, allowBig = true },
    { type = AIAirport.AT_SMALL, allowBig = false },
    { type = AIAirport.AT_COMMUTER, allowBig = false },
  ];
  local engines = AIEngineList(AIVehicle.VT_AIR);
  foreach (choice in airportTypes) {
    if (!AIAirport.IsValidAirportType(choice.type)) continue;
    local best = null;
    for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
      if (!AIEngine.IsBuildable(e)) continue;
      if (!AIEngine.CanRefitCargo(e, this.paxCargo)) continue;
      local planeType = AIEngine.GetPlaneType(e);
      if (planeType != AIAirport.PT_SMALL_PLANE && planeType != AIAirport.PT_BIG_PLANE) continue;
      if (planeType == AIAirport.PT_BIG_PLANE && !choice.allowBig) continue;
      local capacity = AIEngine.GetCapacity(e);
      local speed = AIEngine.GetMaxSpeed(e);
      if (capacity <= 0) continue;
      if (best == null || capacity > best.capacity ||
          (capacity == best.capacity && speed > best.speed)) {
        best = {
          id = e, capacity = capacity, speed = speed, price = AIEngine.GetPrice(e),
          runningCost = AIEngine.GetRunningCost(e),
          maxOrderDistance = AIEngine.GetMaximumOrderDistance(e),
        };
      }
    }
    if (best == null) continue;
    this.airport = {
      type = choice.type,
      width = AIAirport.GetAirportWidth(choice.type),
      height = AIAirport.GetAirportHeight(choice.type),
      coverage = AIAirport.GetAirportCoverageRadius(choice.type),
      price = AIAirport.GetPrice(choice.type),
      maintenance = AIAirport.GetMonthlyMaintenanceCost(choice.type),
    };
    this.plane = best;
    return;
  }
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
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    if (!AIEngine.IsBuildable(e)) continue;
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
   * parc mesure (12 a 22 moteurs routiers en 20 ans, docs/catalogue_churn.json) et une douzaine de
   * cargos, cela reste tres en dessous du budget annuel du catalogue. */
  local usable = [];
  local engines = AIEngineList(AIVehicle.VT_ROAD);
  for (local e = engines.Begin(); !engines.IsEnd(); e = engines.Next()) {
    if (!AIEngine.IsBuildable(e)) continue;
    if (!AIEngine.CanRunOnRoad(e, this.roadType)) continue;
    if (!AIEngine.HasPowerOnRoad(e, this.roadType)) continue;
    if (AIEngine.IsArticulated(e)) continue;
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
    foreach (engine in usable) {
      if (engine.defaultCargo != cargo && !AIEngine.CanRefitCargo(engine.id, cargo)) continue;
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
    if (best.price > this.maxRoadVehiclePrice) this.maxRoadVehiclePrice = best.price;
  }
}

function OpexCatalog::_refreshCargos()
{
  this.cargos = [];
  this.paxCargo = -1;
  local list = AICargoList();
  for (local c = list.Begin(); !list.IsEnd(); c = list.Next()) {
    this.cargos.append(c);
    if (this.paxCargo < 0 && AICargo.HasCargoClass(c, AICargo.CC_PASSENGERS)) this.paxCargo = c;
  }
}

function OpexCatalog::_refreshTowns()
{
  this.towns = [];
  local list = AITownList();
  for (local t = list.Begin(); !list.IsEnd(); t = list.Next()) {
    this.towns.append({
      id = t,
      tile = AITown.GetLocation(t),
      pop = AITown.GetPopulation(t),
    });
  }
}

function OpexCatalog::_refreshIndustries()
{
  this.industries = [];
  this.producers = {};
  this.acceptors = {};

  local list = AIIndustryList();
  for (local i = list.Begin(); !list.IsEnd(); i = list.Next()) {
    this.industries.append({ id = i, tile = AIIndustry.GetLocation(i), type = AIIndustry.GetIndustryType(i) });
  }

  /* Les cargos produits/acceptes se lisent sur le TYPE d'industrie, pas sur l'instance
   * (AIIndustry.IsCargoProduced n'existe pas). On memorise par type : il y a une poignee de
   * types pour des dizaines d'industries, donc les listes ne sont lues qu'une fois chacune. */
  local producedByType = {};
  local acceptedByType = {};
  for (local k = 0; k < this.industries.len(); k++) {
    local type = this.industries[k].type;
    if (!(type in producedByType)) {
      producedByType.rawset(type, this._cargoArray(AIIndustryType.GetProducedCargo(type)));
      acceptedByType.rawset(type, this._cargoArray(AIIndustryType.GetAcceptedCargo(type)));
    }
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
  this._refreshTowns();
  budget.end("cat_towns");

  budget.begin();
  this._refreshIndustries();
  budget.end("cat_industries");

  budget.begin();
  this._refreshRail();
  budget.end("cat_rail");

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
}
