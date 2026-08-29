/* OpexAI -- une IA qui traite les opcodes comme une ressource de jeu.
 *
 * Principe directeur : le budget du VM (10 000 opcodes par tick) n'est pas un stock qu'on
 * economise mais un DEBIT non reportable. La seule decision est donc l'ALLOCATION : a quel
 * candidat va le prochain tick de calcul. D'ou deux metriques :
 *   - externe, l'arbitre : company_value au banc (sweeps/bench.py) ;
 *   - interne, la regle d'allocation : profit par opcode.
 * En cas de desaccord, le banc gagne.
 *
 * Quatre etages :
 *   0  catalog.nut       -- villes, industries, cargos, materiel roulant (rafraichi chaque annee)
 *   1  economy.nut       -- profit annuel attendu d'une ligne
 *   2  candidates.nut    -- cout en iterations d'A* attendu, et le classement par rapport
 *   3  builder_rail.nut  -- construction, sous budget d'iterations calcule par l'arret optimal
 *
 * Instrumentation : AILog.Info n'apparait PAS dans la sortie capturee par OpenTTDLab (verifie le
 * 2026-08-28), et un nom de panneau echoue SILENCIEUSEMENT au-dela de 31 caracteres. D'ou des
 * panneaux courts et nombreux plutot que de longues lignes.
 */

import("pathfinder.rail", "RailPathFinder", 1);

/* Declare avant les require() : catalog.nut consulte ce drapeau dans son cycle annuel. */
ROAD_BUILD_ENABLED <- false;

/* Panneaux de diagnostic : lu UNE fois depuis le reglage dans Start(), pas a chaque appel (57
 * panneaux par an, GetSetting a chaque fois serait du gaspillage d'opcodes pour une valeur qui ne
 * change jamais en cours de partie). Defaut vrai : voir info.nut::debug_signs -- toute
 * l'instrumentation de sweeps/*.py passe par ces panneaux, AILog.Info n'etant pas capture par
 * OpenTTDLab. On ne les coupe que pour une partie avec des humains. */
DEBUG_SIGNS <- true;

/* Unique point de passage vers AISign.BuildSign : permet de tout couper d'un reglage sans
 * conditionner 57 appels un par un. Meme signature que l'appel d'origine. */
function OpexSign(anchor, name)
{
  if (!DEBUG_SIGNS) return;
  AISign.BuildSign(anchor, name);
}

require("budget.nut");
require("catalog.nut");
require("economy.nut");
require("candidates.nut");
require("builder_rail.nut");
require("builder_air.nut");
require("builder_water.nut");
require("builder_road.nut");

/* Filet physique : deux gares reellement posees trop pres l'une de l'autre partagent leur bassin
 * de desserte, MEME si ce sont deux villes/industries differentes. Un rayon de couverture de gare
 * "petite" standard est ~4 tuiles ; MIN_SEPARATION couvre le double (dos-a-dos) plus une marge.
 * Abaisse de 15 a 10 le 2026-08-28 : mesure sur graine 42/20 ans, 84 % des rejets _tooClose
 * etaient a distance <5 de la MEME origine deja servie (couverts desormais par ORIGIN_SEPARATION
 * ci-dessous, avec precision, pas par ce filet) ; les 16 % restants, a distance 5-14, rejetaient
 * une ville VOISINE mais DIFFERENTE -- un faux positif du au seuil de 15, bien au-dela de tout
 * recouvrement de bassin plausible. Voir docs/opex_full_campaign_20y.json (signs GT/GN). */
const MIN_SEPARATION = 10;

/* Identite d'origine : candidate.src/dst est TOUJOURS la tuile exacte du catalogue (ville ou
 * industrie), stable d'une annee sur l'autre -- une reutilisation reelle de la MEME origine tombe
 * donc a distance 0 quel que soit l'endroit ou la gare a fini par etre posee (jusqu'a
 * STATION_SEARCH_RADIUS = 30 tuiles plus loin, builder_rail.nut). C'est la vraie protection
 * "pas de second raccordement sur une extremite deja servie" -- MIN_SEPARATION comparait a tort
 * l'origine du candidat a la gare BATIE d'une ligne existante, un proxy bruite par cet ecart de
 * recherche. La petite marge n'est qu'une precaution, pas le mecanisme principal. */
const ORIGIN_SEPARATION = 3;

/* Fenetre de temps accordee a une tentative, en plus du budget d'iterations. A ~3,7 iterations
 * par tick, N iterations demandent ~N/3,7 ticks ; la marge couvre la pose elle-meme. */
const BUILD_TICK_MARGIN = 3000;

/* Reserve de tresorerie. Sans elle l'IA construit jusqu'a la ruine : mesure du 2026-08-28,
 * 4 lignes construites puis solde a -542 avec l'emprunt au maximum. Une compagnie a sec ne peut
 * plus ni renouveler ses vehicules ni saisir une occasion, et la valeur d'entreprise tombe a 1. */
const CASH_RESERVE = 50000;

/* Route v1 : le constructeur et son rollback sont conserves, mais la campagne gelee graine 42 a
 * mesure une liaison de 23 tuiles a -599/-601 par an pendant 19 ans (notes d'arret -1) et une
 * valeur finale de 1 749 226 contre 2 787 970 sans route. La transaction n'est donc PAS allouee
 * tant qu'un protocole a demontre une desserte routiere rentable. Start garde l'appel conditionnel
 * a _tryBuildRoad : reactivation localisee a ce seul drapeau, sans debit sur la baseline. */

/* Seuil de remboursement d'emprunt : sous ce plancher de tresorerie on ne rembourse pas, un
 * emprunt a 5 % coute bien moins qu'une ligne manquee faute de cash. Au-dessus, l'argent qui
 * dort ne rapporte rien -- autant reduire l'emprunt.
 *
 * Devenu reglable le 2026-08-29 pour que le banc puisse l'opposer a lui-meme en une seule
 * campagne, puis abaisse de 1 000 000 a 300 000 apres verdict de ce banc. La valeur ci-dessous
 * n'est qu'un repli : Start() la remplace par le reglage. Tout le raisonnement, la mesure qui
 * condamne l'ancienne valeur et le verdict sont dans info.nut. */
LOAN_REPAY_FLOOR <- 300000;

/* Plafond absolu du pathfinder. Initialisation de repli seulement : Start() le remplace UNE fois
 * par pathfinder_hard_cap_k. Mesure du 2026-08-29 (4 graines x 20 ans) : 36 600 iterations est le
 * maximum d'une reussite ; le defaut 40 000 garde 9 % de marge et evite les ABND a 60 000 qui
 * absorbaient 56,5 % des opcodes de construction. */
HARD_ITERATION_CAP <- 40000;

/* La memoire est l'autre correctif, independamment des 40 000 iterations. Elle reste un repli
 * actif jusqu'a la lecture unique de abandon_memory dans Start(), comme les autres reglages de
 * decision qui ne changent pas pendant une partie. */
ABANDON_MEMORY <- true;

/* Raccordement de gare : repli actif jusqu'a la lecture unique de station_join dans Start(). Le
 * defaut vrai rend disponible la seule sortie utile au filet physique ; 0 reconstitue le bras
 * historique pour le banc apparie. */
STATION_JOIN <- true;

/* Ligne fret morte (2026-08-28) : une industrie source qui ferme NE garantit PAS l'effondrement --
 * la gare peut recuperer une industrie voisine du meme cargo (ligne 4, campagne 20 ans, restee
 * rentable malgre srcAlive=0). Le diagnostic se fie donc TOUJOURS a la performance REELLE
 * (note de gare et revenu implicite), jamais a srcAlive seul, ET exige DEUX annees CONSECUTIVES
 * de confirmation pour exclure un accroc transitoire -- cf. OpexAI::_reportLines. */
const DEAD_STREAK_THRESHOLD = 2;

class OpexAI extends AIController {
  _budget = null;
  _catalog = null;
  _startTick = 0;
  _lines = null;        // [{stationA, stationB, cargo, predicted, iterations, trains, lineId, ...
                         //   deadStreak, scrapping, scrapVehicles (fret uniquement, cf.
                         //   _reportLines / _scrapDeadLines)}]
  /* Paires qui ont rendu ABND : table indexee par cle chaine, donc test O(1), et volontairement
   * petite (quelques abandons par partie) plutot qu'un historique de toutes les tentatives. */
  _abandonedPairs = null;
  _airBuilt = false;
  _waterBuilt = false;
  _roadBuilt = false;
  /* Diagnostic bus (2026-08-28) : le bus routier ne rejoint jamais _lines (cf. commentaire dans
   * _tryBuildRoad), donc _reportLines ne le voit jamais. _roadDiag garde juste assez pour le
   * mesurer chaque annee sans toucher a _tooClose/_lines : vehicule, station IDs, cargo, et les
   * tuiles de facade (front) du depot et des deux arrets pour tester la connectivite reelle. */
  _roadDiag = null;
  /* Echantillon hebdomadaire du bus (2026-08-28), en plus du rapport annuel _reportRoad : deux
   * releves annuels consecutifs a la MEME tuile (RL fige) laissent planer le doute entre
   * "bloque" et "boucle si lente qu'un an ne suffit pas a en sortir". Borne a 40 echantillons
   * (~280 jours a raison d'un par semaine) pour ne jamais s'emballer si le diagnostic tourne
   * plus longtemps que prevu. */
  _roadSampleTick = -1;
  _roadSampleCount = 0;
  /* Identite stable des lignes pour les panneaux (2026-08-28) : this._lines.len() n'est plus un
   * identifiant valide des que _scrapDeadLines peut retirer un element -- Array.remove() DECALE
   * tous les indices suivants, donc un panneau IA|5|... loggue une annee peut, apres un retrait,
   * pointer sur une ligne totalement differente l'annee suivante (collision mesuree sur la
   * premiere execution : l'indice 5 melangeait une ligne fret morte 1977-1979 et une ligne saine
   * qui avait glisse dans ce slot). _nextLineId ne recule jamais, contrairement a _lines.len(). */
  _nextLineId = 0;

  constructor()
  {
    this._budget = OpexBudget();
    this._catalog = OpexCatalog();
    this._lines = [];
    this._abandonedPairs = {};
  }

  function Start();
  function _tooClose(candidate);
  function _tryBuildAir(year);
  function _tryBuildWater(year);
  function _tryBuildRoad(year);
  function _tryBuild(ranked, year);
  function _reportYear(year, ranked);
  function _reportLines(year);
  function _reportRoad(year);
  function _scrapDeadLines(year);
}

/* Code d'arret compact pour OR. Le panneau contient deja beaucoup de mesures ; un seul caractere
 * garde le nom sous le plafond silencieux de 31 caracteres. */
function OpexAttemptReasonCode(reason)
{
  if (reason == "OK") return "K";
  if (reason == "ABND") return "A";
  if (reason == "DEAD") return "D";
  if (reason == "NOPA") return "P";
  if (reason == "NOPLAN") return "L";
  if (reason == "SHORT") return "H";
  if (reason == "NOMATCH") return "M";
  if (reason == "JOINPATH") return "J";
  if (reason == "STNFAIL") return "S";
  if (reason == "TRKFAIL") return "T";
  if (reason == "DEPFAIL") return "E";
  if (reason == "ORDFAIL") return "R";
  if (reason == "NOTRAIN") return "V";
  return "X";
}

/* Le station_id est l'identite de bassin, pas la tuile de quai : deux lignes raccordees ont des
 * sorties differentes mais le meme ID. Un ancien etat sauvegarde sans la liste vehicles retombe
 * prudemment sur la requete par gare ; les nouvelles lignes n'utilisent jamais ce repli ambigu. */
function OpexLineVehicleIds(line, stationId)
{
  if ("vehicles" in line) return line.vehicles;
  local ids = [];
  local vehicles = AIVehicleList_Station(stationId);
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) ids.append(v);
  return ids;
}

function OpexLineStationId(line, end)
{
  local tile = end == "A" ? line.stationA : line.stationB;
  local stationId = AIStation.GetStationID(tile);
  return AIStation.IsValidStation(stationId) ? stationId : -1;
}

function OpexRememberClosest(distance, threshold, closest)
{
  return distance < threshold && (closest < 0 || distance < closest) ? distance : closest;
}

/* Le seul partage autorise dans v1 est une ligne rail dont on a garde le plan de quai. Les autres
 * modes ont bien le droit de continuer a proteger leur bassin avec MIN_SEPARATION, mais aucune
 * geometrie rail sure ne peut etre deduite de leur tuile d'aeroport ou de dock. Pour le fret, une
 * source jointe a un puits ferait accepter localement le cargo qui devait voyager : roles egaux
 * seulement. */
function OpexJoinCompatible(candidate, conflict)
{
  local line = conflict.line;
  if (("mode" in line) || !("platformA" in line) || !("platformB" in line)) return false;
  if (!("kind" in line) || line.kind != candidate.kind || line.cargo != candidate.cargo) return false;
  if (candidate.kind == "freight" && conflict.end != conflict.lineEnd) return false;
  return true;
}

/* Un seul objet gare et une seule extremite candidate peuvent etre court-circuites. Si une autre
 * gare physique est aussi dans le disque, la ligne neuve lui volerait son bassin : le filet reste
 * arme. Les doublons de lignes deja jointes ont le meme StationID et sont donc volontairement un
 * seul conflit logique. */
function OpexFindStationJoin(candidate, conflicts)
{
  if (conflicts.len() == 0) return null;
  local first = conflicts[0];
  foreach (conflict in conflicts) {
    if (conflict.end != first.end || conflict.stationId != first.stationId) return null;
  }
  foreach (conflict in conflicts) {
    if (!OpexJoinCompatible(candidate, conflict)) continue;
    local platform = conflict.lineEnd == "A" ? conflict.line.platformA : conflict.line.platformB;
    return { candidateEnd = conflict.end, stationId = conflict.stationId, platform = platform };
  }
  return null;
}

/* Les tuiles candidate.src/dst sont des positions, tandis que les identifiants de ville/industrie
 * restent stables si le plan de gare evolue. Les deux types actuels ont ces identifiants ; le
 * repli sur les tuiles garde la fonction sure pour un futur type de candidat. La cle fret reste
 * orientee (producteur -> accepteur), mais la cle pax normalise les deux villes pour survivre a un
 * changement de l'ordre de catalog.towns entre deux rafraichissements. */
function OpexAbandonedPairKey(candidate)
{
  local src = candidate.src;
  local dst = candidate.dst;
  if (candidate.kind == "pax") {
    /* catalog.nut garde AITown.GetLocation(t), donc GetClosestTown retrouve ici t a distance 0. */
    src = AITile.GetClosestTown(candidate.src);
    dst = AITile.GetClosestTown(candidate.dst);
    if (src > dst) {
      local swap = src;
      src = dst;
      dst = swap;
    }
  } else if (candidate.kind == "freight") {
    src = AIIndustry.GetIndustryID(candidate.src);
    dst = AIIndustry.GetIndustryID(candidate.dst);
  }
  return candidate.kind + "|" + candidate.cargo + "|" + src + "|" + dst;
}

/* Un seul avion suffit pour cette premiere liaison. Le scan des vehicules empeche un doublon apres
 * rechargement, ou si l'etat transitoire de l'IA a ete perdu. */
function OpexAI::_tryBuildAir(year)
{
  if (this._airBuilt || this._catalog.airport == null || this._catalog.plane == null) return;
  local vehicles = AIVehicleList();
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    if (AIVehicle.GetVehicleType(v) == AIVehicle.VT_AIR) {
      this._airBuilt = true;
      return;
    }
  }

  this._budget.begin();
  local plan = OpexAirPlans(this._catalog);
  local planOps = this._budget.end("build_air_plans");
  if (plan == null) return;

  local capital = 2 * this._catalog.airport.price + this._catalog.plane.price;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < capital + CASH_RESERVE + AIR_CAPITAL_MARGIN) return;

  local result = OpexBuildAirRoute(this._catalog, this._budget, plan);
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "OA|" + year + "|" + plan.distance + "|" + planOps + "|" + result.reason);
  if (result.error != 0) OpexSign(anchor, "OE|A|" + result.error);
  if (!result.ok) return;

  this._airBuilt = true;
  this._lines.append({
    stationA = result.stationA, stationB = result.stationB,
    /* Pas de notion d'origine distincte pour l'avion (une seule liaison jamais dupliquee, gardee
     * par _airBuilt) -- la gare batie sert de repli pour que _tooClose n'ait pas a distinguer les
     * modes. */
    originA = result.stationA, originB = result.stationB,
    cargo = this._catalog.paxCargo,
    predicted = 0, iterations = 0, trains = 1, distance = plan.distance, year = year,
    mode = "air", vehicle = result.vehicle, vehicles = [result.vehicle],
    lineId = this._nextLineId,
  });
  OpexSign(anchor, "PM|" + this._nextLineId + "|A|" + plan.distance + "|"
                   + AICargo.GetCargoLabel(this._catalog.paxCargo));
  this._nextLineId++;
}

/* Une seule route v1 ; le scan apres rechargement empeche tout doublon maritime. */
function OpexAI::_tryBuildWater(year)
{
  if (this._waterBuilt || this._catalog.ships.len() == 0 || this._catalog.paxCargo < 0) return;
  local vehicles = AIVehicleList();
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    if (AIVehicle.GetVehicleType(v) == AIVehicle.VT_WATER) {
      this._waterBuilt = true;
      return;
    }
  }
  this._budget.begin();
  local plan = OpexWaterPlans(this._catalog);
  local planOps = this._budget.end("build_water_plans");
  if (plan == null) return;
  local capital = 2 * this._catalog.costDock + this._catalog.costWaterDepot + this._catalog.maxShipPrice;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < capital + CASH_RESERVE + WATER_CAPITAL_MARGIN) return;
  local result = OpexBuildWaterRoute(this._catalog, this._budget, plan);
  local anchor = AIMap.GetTileIndex(1, 1);
  if (result.ok) OpexSign(anchor, "OM|W|" + year + "|" + plan.distance + "|" + planOps);
  else OpexSign(anchor, "ON|W|" + result.reason + "|" + result.error);
  if (!result.ok) return;
  this._waterBuilt = true;
  this._lines.append({
    stationA = result.dockA, stationB = result.dockB,
    /* Idem avion : pas de notion d'origine distincte, repli sur le quai bati. */
    originA = result.dockA, originB = result.dockB,
    cargo = this._catalog.paxCargo,
    predicted = 0, iterations = 0, trains = 1, distance = plan.distance, year = year,
    mode = "water", vehicle = result.vehicle, vehicles = [result.vehicle],
    lineId = this._nextLineId,
  });
  OpexSign(anchor, "PM|" + this._nextLineId + "|W|" + plan.distance + "|"
                   + AICargo.GetCargoLabel(this._catalog.paxCargo));
  this._nextLineId++;
}

/* Une seule liaison bus v1. Le scan est volontairement aussi large que ceux de l'air/de l'eau :
 * OpexAI ne construit aucun autre vehicule routier, donc tout VT_ROAD qui nous appartient suffit
 * a reconnaitre la transaction apres rechargement et a eviter un doublon. */
function OpexAI::_tryBuildRoad(year)
{
  if (!ROAD_BUILD_ENABLED) return;
  if (this._roadBuilt || this._catalog.roadBuses.len() == 0 || this._catalog.paxCargo < 0) return;
  local vehicles = AIVehicleList();
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) {
    if (AIVehicle.GetVehicleType(v) == AIVehicle.VT_ROAD) {
      this._roadBuilt = true;
      return;
    }
  }

  this._budget.begin();
  local plan = OpexRoadPlans(this._catalog);
  local planOps = this._budget.end("build_road_plans");
  if (plan == null) return;
  local capital = plan.routeDistance * this._catalog.costRoadPerTile
                + 2 * this._catalog.costRoadStation + this._catalog.costRoadDepot
                + this._catalog.maxRoadBusPrice;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < capital + CASH_RESERVE + ROAD_CAPITAL_MARGIN) return;

  local result = OpexBuildRoadRoute(this._catalog, this._budget, plan);
  local anchor = AIMap.GetTileIndex(1, 1);
  if (!result.ok) {
    OpexSign(anchor, "OE|R|" + result.reason + "|" + result.error);
    return;
  }
  local idx = this._nextLineId;
  /* Le pire nom est OM|R|99|999|999|999|25|999999 : 31 caracteres, plafond inclus. */
  OpexSign(anchor, "OM|R|" + (year % 100) + "|" + idx + "|" + plan.townA.id + "|"
                           + plan.townB.id + "|" + plan.distance + "|" + planOps);
  OpexSign(anchor, "OC|R|" + idx + "|" + result.cost + "|" + plan.routeDistance);
  OpexSign(anchor, "OV|R|" + idx + "|" + result.vehicle + "|" + result.capacity);
  this._roadBuilt = true;
  /* Contrairement aux lignes rail, le bus court ne rejoint pas _lines : OpexOriginServed et
   * _tooClose ne doivent jamais en deduire qu'une ville est verrouillee pour une liaison rail
   * interurbaine. Son unicite est assuree par _roadBuilt et par le scan VT_ROAD. */
  this._nextLineId++;

  /* Diagnostic de non-chargement (2026-08-28) : garde de quoi mesurer le bus chaque annee dans
   * _reportRoad, hors de _lines. */
  this._roadDiag = {
    vehicle = result.vehicle, cargo = this._catalog.paxCargo,
    stationA = result.stationA, stationB = result.stationB,
    stopA = result.stopA, stopB = result.stopB,
    coverage = AIStation.GetCoverageRadius(AIStation.STATION_BUS_STOP),
  };
  /* Geometrie brute (2026-08-28), UNE fois : tuile + facade des deux arrets et du depot, pour
   * reconstruire offline (tile = y*mapSizeX+x, carte 256x256) si le bus boucle pres d'un point
   * particulier plutot que d'atteindre stopA. */
  OpexSign(anchor, "RT|" + idx + "|sA|" + plan.stopA.tile + "|" + plan.stopA.front);
  OpexSign(anchor, "RT|" + idx + "|sB|" + plan.stopB.tile + "|" + plan.stopB.front);
  OpexSign(anchor, "RT|" + idx + "|dp|" + plan.depot.tile + "|" + plan.depot.front);
  OpexSign(anchor, "RT|" + idx + "|sh|" + plan.shape);
}

/* Une extremite deja desservie par nous ne merite pas un second raccordement.
 *
 * Deux tests distincts, mesure du 2026-08-28 a l'appui (docs/opex_full_campaign_20y.json,
 * signs GT/GN) :
 *  1. Identite d'origine (ORIGIN_SEPARATION, serre) : la MEME ville/industrie deja servie, quel
 *     que soit l'endroit ou sa gare a fini par etre posee. C'etait 84 % des rejets sous l'ancien
 *     test unique -- desormais couvert avec precision, pas par une distance bruitee.
 *  2. Filet physique (MIN_SEPARATION, plus large mais abaisse) : deux gares BATIES reellement
 *     trop proches, meme pour deux origines differentes -- le vrai risque de cannibalisation.
 *
 * Rend les deux conflits SEPARES. L'identite d'origine est toujours un rejet ; le conflit
 * physique transporte en plus les gares touchees, afin que _tryBuild puisse proposer un quai
 * joint sans desarmer le filet pour l'autre extremite.
 *
 * Depuis le 2026-08-28, le test 1 (identite d'origine) est DEJA applique en amont, a la
 * generation (OpexOriginServed dans candidates.nut) -- un candidat qui reutilise une origine
 * servie n'atteint plus jamais le TOP_K, donc plus jamais ce test-ci. Cette fonction reste
 * l'unique verification pour le test 2 (MIN_SEPARATION), qui depend de la gare BATIE et ne peut
 * pas se calculer avant la tentative de construction. */
function OpexAI::_tooClose(candidate)
{
  local origin = -1;
  foreach (line in this._lines) {
    local d;
    d = AIMap.DistanceManhattan(candidate.src, line.originA);
    origin = OpexRememberClosest(d, ORIGIN_SEPARATION, origin);
    d = AIMap.DistanceManhattan(candidate.src, line.originB);
    origin = OpexRememberClosest(d, ORIGIN_SEPARATION, origin);
    d = AIMap.DistanceManhattan(candidate.dst, line.originA);
    origin = OpexRememberClosest(d, ORIGIN_SEPARATION, origin);
    d = AIMap.DistanceManhattan(candidate.dst, line.originB);
    origin = OpexRememberClosest(d, ORIGIN_SEPARATION, origin);
  }
  if (origin >= 0) return { origin = origin, physical = -1, conflicts = [] };

  local physical = -1;
  local conflicts = [];
  local entries = [["A", candidate.src], ["B", candidate.dst]];
  foreach (line in this._lines) {
    foreach (lineEnd in ["A", "B"]) {
      local stationId = OpexLineStationId(line, lineEnd);
      if (stationId < 0) continue;
      local stationTile = lineEnd == "A" ? line.stationA : line.stationB;
      foreach (entry in entries) {
        local d = AIMap.DistanceManhattan(entry[1], stationTile);
        physical = OpexRememberClosest(d, MIN_SEPARATION, physical);
        if (d < MIN_SEPARATION) {
          conflicts.append({ end = entry[0], line = line, lineEnd = lineEnd,
                             stationId = stationId, distance = d });
        }
      }
    }
  }
  return { origin = -1, physical = physical, conflicts = conflicts };
}

/* Le coeur de l'allocation : on descend le classement tant qu'il reste de l'argent, et chaque
 * tentative recoit un budget d'iterations egal a ce qu'il faut pour continuer a battre le
 * candidat SUIVANT. Pour le dernier, l'alternative reelle n'est pas l'absence de travail : c'est
 * attendre le prochain rafraichissement annuel et son classement. MIN_RATIO est precisement le
 * plus petit rapport acceptable dans ce classement ; il remplace donc le suivant absent, sans
 * introduire de seuil propre a l'arret. */
function OpexAI::_tryBuild(ranked, year)
{
  local best = ranked.best;
  local anchor = AIMap.GetTileIndex(1, 1);

  /* Diagnostic goulot (2026-08-28) : _tooClose et la reserve de tresorerie rejettent tous deux
   * des candidats, mais rien ne comptait lequel des deux domine -- l'hypothese MIN_SEPARATION
   * n'etait deduite que par elimination. Ces compteurs le mesurent directement. */
  local nTooClose = 0;
  local nTooCloseNear = 0;   // distance 0..4 : origine reutilisee (ORIGIN_SEPARATION) ou gare tres proche
  local nTooCloseFar = 0;    // distance 5..MIN_SEPARATION-1 : filet physique seul (ORIGIN_SEPARATION=3 exclu)
  local nCashBlocked = 0;
  local nBuilt = 0;
  local nAttemptFailed = 0;  // ni tooClose ni cash, mais result.ok == false (pathfinding, etc.)
  local nAbandonMemory = 0;  // exclu avant _tooClose et cash : compteur separe, jamais un echec
  local nJoinAttempts = 0;
  local nJoinBuilt = 0;
  local nJoinFailed = 0;

  for (local i = 0; i < best.len(); i++) {
    local candidate = best[i];
    local abandonedKey = null;
    if (ABANDON_MEMORY) {
      abandonedKey = OpexAbandonedPairKey(candidate);
      if (abandonedKey in this._abandonedPairs) {
        nAbandonMemory++;
        continue;
      }
    }
    local close = this._tooClose(candidate);
    local tooCloseDist = close.origin;
    local join = null;
    if (tooCloseDist >= 0) {
      nTooClose++;
      if (tooCloseDist < 5) nTooCloseNear++; else nTooCloseFar++;
      continue;
    }
    if (close.physical >= 0) {
      /* Le filet garde la main tant que le candidat ne peut pas reutiliser UNE gare logique avec
       * un quai rail dedie. Ne pas choisir une autre gare ni une autre extremite ici : ce serait
       * desarmer MIN_SEPARATION au-dela de l'objet precis de la tranche. */
      if (STATION_JOIN) join = OpexFindStationJoin(candidate, close.conflicts);
      if (join == null) {
        nTooClose++;
        if (close.physical < 5) nTooCloseNear++; else nTooCloseFar++;
        continue;
      }
    }

    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < candidate.capital + CASH_RESERVE) {  // classement decroissant
      nCashBlocked++;
      OpexSign(anchor, "GC|" + year + "|" + money + "|" + candidate.capital);
      break;
    }

    local alternativeSource = (i + 1 < best.len()) ? "S" : "L";
    local alternativeRatio = (alternativeSource == "S") ? best[i + 1].ratio : MIN_RATIO;
    local budgetInfo = OpexIterationBudget(candidate.profitAnnual, alternativeRatio);
    local iterationBudget = budgetInfo.budget;
    local deadline = AIController.GetTick() + iterationBudget / 3 + BUILD_TICK_MARGIN;

    if (join != null) nJoinAttempts++;
    local result = OpexBuildLine(this._catalog, this._budget, candidate, iterationBudget, deadline,
                                 join);

    /* Instrumentation d'une tentative, sans ajouter de panneau :
     * OR|aa|id|rang20|PSR|budget|iterations
     * aa = annee modulo 100 ; rang20 = rang * TOP_K + longueur (reversible, 1..400) ;
     * PSR = chemin de budget (Z/F/C/N), source (S=suivant, L=dernier), raison compacte.
     * Le pire nom de la campagne est OR|99|999|400|ZLA|60000|60000 : 29 caracteres.
     * idx = this._nextLineId, pas this._lines.len() : depuis que _scrapDeadLines peut retirer un
     * element (et donc decaler tous les indices suivants), la longueur du tableau n'est plus un
     * identifiant stable -- cf. commentaire sur _nextLineId. _nextLineId ne recule jamais et
     * n'avance que sur un succes, exactement comme le faisait _lines.len() avant que le retrait
     * n'existe. */
    local rankPacked = i * TOP_K + best.len();
    OpexSign(anchor, "OR|" + (year % 100) + "|" + this._nextLineId + "|" + rankPacked
                             + "|" + budgetInfo.path + alternativeSource
                             + OpexAttemptReasonCode(result.reason) + "|" + iterationBudget
                             + "|" + result.iterations);
    /* OR est deja au bord du plafond de 31 caracteres; ce panneau compagnon garde le cout reel
     * de la tentative pour comparer les lignes abouties aux abandons, sans changer son format. */
    OpexSign(anchor, "OB|A|" + (year % 100) + "|" + this._nextLineId + "|" + rankPacked
                             + "|" + result.opcodes);
    if (result.error != 0) OpexSign(anchor, "OV|" + this._nextLineId + "|" + result.error);
    if (result.diag != null) {
      OpexSign(anchor, "OG|" + result.diag.railtype + "|" + result.diag.isDepot
                               + "|" + result.diag.buildable + "|" + result.diag.canRun);
      OpexSign(anchor, "OH|" + result.diag.price + "|" + result.diag.cash);
      OpexSign(anchor, "OI|" + result.diag.engineRail + "|" + result.diag.depotRail
                               + "|" + result.diag.vehType + "|" + result.diag.testOk);
    }

    if (result.ok) {
      nBuilt++;
      if (join != null) nJoinBuilt++;
      local idx = this._nextLineId;
      /* Predit-vs-reel (etage 1) : le detail du calcul au moment de la construction, pour pouvoir
       * le comparer plus tard a la mesure reelle (_reportLines). Un sign par grandeur : jamais
       * plus de 2 valeurs numeriques par nom pour rester sous la limite silencieuse de 31
       * caracteres meme quand i et les valeurs sont a leur maximum plausible. */
      OpexSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
      OpexSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
      OpexSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
      OpexSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains);
      /* La distance quitte OR (panneau deja plein) et rejoint ce panneau de succes existant. */
      OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays + "|" + candidate.distance);
      /* pax vs freight, et la production mensuelle BRUTE utilisee comme entree : pour trancher si
       * le residu du gap vient de la ville entiere comptee au lieu du seul rayon de la gare
       * (candidates.nut le signale deja comme biais non calibre sur les paires de villes). */
      OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                               + "|" + candidate.monthly);
      /* Le label cargo est stable et tient dans un panneau court; il rend la repartition finale
       * lisible sans devoir deviner le type a partir de son identifiant interne. */
      OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));

      /* Diagnostic effondrement fret (2026-08-28) : garder de quoi verifier, annee apres annee,
       * si les DEUX industries d'une ligne fret restent valides -- sans ca on ne peut pas
       * departager "industrie fermee" de "train coince" comme cause de la note -1. */
      this._lines.append({
        stationA = result.stationA, stationB = result.stationB,
        /* Identite d'origine (ville ou industrie) pour _tooClose -- cf. commentaire sur
         * ORIGIN_SEPARATION : la tuile exacte du candidat, pas la gare batie. */
        originA = candidate.src, originB = candidate.dst,
        cargo = candidate.cargo,
        predicted = candidate.profitAnnual, iterations = result.iterations,
        trains = result.trains, distance = candidate.distance, year = year,
        predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
        predAmort = candidate.amortAnnual, predCarried = candidate.carried,
        predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
        /* La liste est l'identite de la ligne, pas une requete par StationID : sur une gare
         * jointe, celle-ci verrait aussi les convois de la voisine (rapport et rebut doivent les
         * laisser intacts). Les plans rendent le prochain quai adjacent deterministe. */
        vehicles = result.vehicles, platformA = result.platformA, platformB = result.platformB,
        kind = candidate.kind,
        srcIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.src) : -1,
        dstIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.dst) : -1,
        /* Ligne morte (2026-08-28) : deadStreak/scrapping/scrapVehicles n'ont de sens que pour le
         * fret (cf. _reportLines et _scrapDeadLines) mais sont initialises ici pour toutes les
         * lignes rail -- inoffensif pour le pax, dont deadStreak reste a 0 pour toujours faute de
         * srcIndustry valide. */
        deadStreak = 0, scrapping = false, scrapVehicles = [],
        lineId = idx,
      });
      this._nextLineId++;
    } else {
      nAttemptFailed++;
      if (join != null) nJoinFailed++;
      /* Seulement ABND signifie que le plafond d'iterations a joue. DEAD est le deadline, NOPA
       * une file vide, et les echecs de construction ne disent rien sur cette paire : les garder
       * hors memoire preserve leur possibilite de reussir plus tard. */
      if (ABANDON_MEMORY && result.reason == "ABND") {
        this._abandonedPairs[abandonedKey] <- true;
      }
    }

  }

  /* Sommaire annuel du goulot : combien de candidats classes ont ete rejetes par _tooClose,
   * combien par la reserve de tresorerie (dont l'"break" laisse le reste du classement
   * inexplore -- nUnreached compte ceux-la a part pour ne pas les confondre avec un rejet). */
  /* YT, pose dans Start() apres _tryRepayLoan(), remplace le panneau GT : la mesure ne doit pas
   * ajouter une commande de panneau annuelle au scenario de reference. Les compteurs GT ne sont
   * pas consommes par le banc. */
  /* Repartition des rejets _tooClose : proche (probable meme ville) vs lointain (probable ville
   * DIFFERENTE, simple voisine -- signe que MIN_SEPARATION est trop grossier plutot que trop
   * grand). */
  OpexSign(anchor, "GN|" + year + "|" + nTooCloseNear + "|" + nTooCloseFar);
  /* GM est separe de OR, deja au plafond de 31 caracteres. Quand la memoire est coupee, ne pas
   * poser meme ce panneau conserve le bras hard_cap=60/memoire=0 structurellement identique aux
   * choix anterieurs ; le parseur interprete alors son absence comme zero. */
  if (ABANDON_MEMORY) OpexSign(anchor, "GM|" + year + "|" + nAbandonMemory);
  /* OR est sature et GM deja reserve a la memoire : compagnon court, avec essais / succes /
   * echecs du raccordement. "OB|J|9999|20|20|20" reste largement sous les 31 caracteres. */
  if (STATION_JOIN) OpexSign(anchor, "OB|J|" + year + "|" + nJoinAttempts + "|" + nJoinBuilt
                                      + "|" + nJoinFailed);
}

/* Le releve qui permet de calibrer l'etage 1 : pour chaque ligne, la note de gare REELLE (on
 * suppose STATION_RATING_PCT = 75) et le profit REEL des vehicules (on a predit profitAnnual).
 * C'est exactement la mesure qui manquait a la campagne v3. */
function OpexAI::_reportLines(year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    local stationA = AIStation.GetStationID(line.stationA);
    local stationB = AIStation.GetStationID(line.stationB);
    if (!AIStation.IsValidStation(stationA)) continue;

    local ratingA = AIStation.GetCargoRating(stationA, line.cargo);
    local ratingB = AIStation.IsValidStation(stationB)
        ? AIStation.GetCargoRating(stationB, line.cargo) : -1;
    /* line.lineId, pas i : identite stable qui survit a un retrait de _lines par _scrapDeadLines
     * (cf. commentaire sur _nextLineId). Toutes les lignes rail/avion/bateau en ont une. */
    OpexSign(anchor, "OY|" + line.lineId + "|" + year + "|" + ratingA + "|" + ratingB);

    /* Profit reel (deja mesure), plus le detail qui manquait : combien de convois roulent
     * VRAIMENT (vs. le trains predit dans _tryBuild), leur cout de fonctionnement reel, et le
     * revenu reel implicite (profit + cout de fonctionnement, puisque GetProfitLastYear n'est
     * pas decompose par l'API). C'est ce qui permet de departager "note de gare fausse" de
     * "cout de fonctionnement fausse" de "convois manquants" comme cause du 10x. */
    local profit = 0;
    local runCost = 0;
    local vehCount = 0;
    local isFreight = ("kind" in line) && line.kind == "freight";
    local vehicleType = AIVehicle.VT_RAIL;
    if ("mode" in line && line.mode == "air") vehicleType = AIVehicle.VT_AIR;
    else if ("mode" in line && line.mode == "water") vehicleType = AIVehicle.VT_WATER;
    local diagSlot = 0;
    /* Une gare jointe possede un seul StationID : AIVehicleList_Station melangerait les lignes.
     * La liste figee a la construction est l'attribution correcte ; le helper ne consulte la gare
     * que pour les etats sauvegardes anterieurs a ce correctif. */
    local vehicles = OpexLineVehicleIds(line, stationA);
    foreach (v in vehicles) {
      if (!AIVehicle.IsValidVehicle(v)) continue;
      if (AIVehicle.GetVehicleType(v) != vehicleType) continue;
      profit += AIVehicle.GetProfitLastYear(v);
      runCost += AIVehicle.GetRunningCost(v);
      vehCount++;
      /* Diagnostic effondrement fret : etat REEL de CHAQUE convoi (pas juste le premier -- une
       * gare a UNE seule voie, donc un convoi bloque au puits peut faire la queue derriere les
       * autres, qui rendraient "en marche, vitesse 0" sans etre eux-memes la cause). L'ordre
       * courant (0 = source, 1 = puits), l'etat, la vitesse et le chargement du cargo de la
       * ligne. Limite a 3 convois (MAX_TRAINS le permet toujours ici en pratique). */
      if (isFreight && diagSlot < 3) {
        local state = AIVehicle.GetState(v);
        local order = AIOrder.ResolveOrderPosition(v, AIOrder.ORDER_CURRENT);
        local speed = AIVehicle.GetCurrentSpeed(v);
        local load = AIVehicle.GetCargoLoad(v, line.cargo);
        OpexSign(anchor, "VS|" + line.lineId + "|" + year + "|" + diagSlot + "|" + state + "|" + order);
        OpexSign(anchor, "VL|" + line.lineId + "|" + year + "|" + diagSlot + "|" + speed + "|" + load);
        diagSlot++;
      }
    }
    OpexSign(anchor, "OZ|" + line.lineId + "|" + year + "|" + profit);
    OpexSign(anchor, "OU|" + line.lineId + "|" + year + "|" + vehCount + "|" + runCost);
    OpexSign(anchor, "OO|" + line.lineId + "|" + year + "|" + (profit + runCost));

    /* Les deux industries sont-elles encore valides ? Et l'industrie source produit-elle encore ?
     * Depart le blocage "train coince" (hypothese 2) de la fermeture d'industrie (hypothese 1). */
    if (isFreight) {
      local srcAlive = AIIndustry.IsValidIndustry(line.srcIndustry) ? 1 : 0;
      local dstAlive = AIIndustry.IsValidIndustry(line.dstIndustry) ? 1 : 0;
      local srcProd = srcAlive ? AIIndustry.GetLastMonthProduction(line.srcIndustry, line.cargo) : -1;
      OpexSign(anchor, "IA|" + line.lineId + "|" + year + "|" + srcAlive + "|" + dstAlive + "|" + srcProd);

      /* Detection ligne morte : srcAlive=0 seul ne suffit PAS (cf. commentaire DEAD_STREAK_THRESHOLD
       * -- une gare peut recuperer une industrie voisine). srcSuffering couvre aussi l'industrie
       * encore ouverte mais a production nulle, meme consequence pour la ligne qu'une fermeture.
       * collapsed exige EN PLUS la preuve REELLE, mesuree ici meme : note de gare a -1 (aucun
       * cargo jamais vu) ET revenu implicite (profit + cout de fonctionnement) nul ou negatif,
       * c'est-a-dire rien transporte du tout cette annee. deadStreak ne compte que les annees
       * CONSECUTIVES ou les trois tiennent ensemble ; un seul manque et le compteur retombe a 0. */
      local srcSuffering = (!srcAlive) || (srcProd == 0);
      local collapsed = srcSuffering && ratingA <= 0 && (profit + runCost) <= 0;
      line.deadStreak = collapsed ? line.deadStreak + 1 : 0;
      if (line.deadStreak > 0) {
        OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|" + line.deadStreak);
      }
    }
  }
}

/* Remediation ligne morte (2026-08-28) : une fois deadStreak >= DEAD_STREAK_THRESHOLD confirme
 * par _reportLines, on arrete l'hemorragie de cout de fonctionnement en vendant les convois --
 * mais AIVehicle.SellVehicle exige un convoi a l'arret DANS un depot (verifie sur la doc API
 * ai-api/classAIVehicle.html le 2026-08-28 : precondition "the vehicle must be stopped in the
 * depot", exception ERR_VEHICLE_NOT_IN_DEPOT sinon). La vente est donc etalee sur plusieurs
 * annees, au meme rythme annuel que le reste du cycle : l'annee ou le seuil est franchi on
 * envoie chaque convoi au depot (SendVehicleToDepot) et on fige la liste de leurs IDs sur la
 * ligne (scrapVehicles), depuis la liste vehicles posee par cette ligne -- PAS une interrogation
 * par gare qui prendrait les convois du voisin sur un StationID partage. Les annees suivantes, on
 * verifie IsStoppedInDepot() sur cette liste figee
 * et on vend (SellVehicle) ce qui est arrive ; quand elle est vide, la ligne est retiree de
 * _lines -- ce qui l'arrete d'etre rapportee chaque annee ET libere stationA/stationB/originA/
 * originB du filet _tooClose, pour qu'une ligne neuve et proche ne soit plus bloquee par un
 * cadavre. Les gares et voies physiques ne sont PAS demolies : une fois hors de _lines elles ne
 * bloquent plus rien (le seul frein etait la presence dans _lines), et demolir ajoute un risque
 * (note d'autorite locale, infrastructure partagee) pour un gain nul ici. */

/* Diagnostic bus (2026-08-28) : mesure REELLE annuelle de l'unique liaison routiere, en dehors de
 * _lines/_reportLines (cf. commentaire sur _roadDiag). But : departager "le bus n'atteint jamais
 * ses arrets" de "les arrets n'ont aucun bassin" -- decisif via RW (cargo en attente en gare).
 * Panneaux, valeurs max plausibles pour rester sous 31 caracteres :
 *   RS|aa|etat|ordre|charge   -- etat/ordre/charge du vehicule (GetState, ResolveOrderPosition,
 *                                GetCargoLoad) ; "RS|99|9|9|999" = 13 caracteres.
 *   RD|aa|distA|distB         -- distance Manhattan REELLE du vehicule aux deux arrets, pour
 *                                savoir s'il a seulement quitte le depot ; jusqu'a 5 chiffres
 *                                chacun sur une carte 256x256 -- "RD|99|99999|99999" = 18.
 *   RY|aa|ratingA|ratingB     -- note de gare (-1 si HasCargoRating faux) ; "RY|99|-1|-1" = 11.
 *   RW|aa|waitA|waitB         -- passagers en ATTENTE aux deux arrets (GetCargoWaiting), avant
 *                                tout chargement -- "RW|99|9999|9999" = 16.
 */
function OpexAI::_reportRoad(year)
{
  if (this._roadDiag == null) return;
  local d = this._roadDiag;
  local anchor = AIMap.GetTileIndex(1, 1);
  local yy = year % 100;

  if (!AIVehicle.IsValidVehicle(d.vehicle)) {
    OpexSign(anchor, "RX|" + yy);
    return;
  }

  local state = AIVehicle.GetState(d.vehicle);
  local order = AIOrder.ResolveOrderPosition(d.vehicle, AIOrder.ORDER_CURRENT);
  local load = AIVehicle.GetCargoLoad(d.vehicle, d.cargo);
  OpexSign(anchor, "RS|" + yy + "|" + state + "|" + order + "|" + load);
  /* Vitesse REELLE (2026-08-28) : RL fige d'une annee sur l'autre laisse deux lectures possibles
   * -- vehicule bloque (vitesse ~0) ou boucle si lente qu'un an ne suffit pas a en sortir (vitesse
   * non nulle mais faible). GetCurrentSpeed tranche. */
  local speed = AIVehicle.GetCurrentSpeed(d.vehicle);
  OpexSign(anchor, "RV|" + yy + "|" + speed);

  local loc = AIVehicle.GetLocation(d.vehicle);
  local distA = AIMap.DistanceManhattan(loc, d.stopA);
  local distB = AIMap.DistanceManhattan(loc, d.stopB);
  OpexSign(anchor, "RD|" + yy + "|" + distA + "|" + distB);
  /* Position brute (2026-08-28) : RD frozen 3 annees de suite a la meme distance de stopA est
   * ambigu (boucle courte qui repasserait par hasard au meme point chaque relevé annuel, vs
   * vehicule reellement bloque). RL compare la tuile EXACTE d'une annee sur l'autre. */
  OpexSign(anchor, "RL|" + yy + "|" + loc);

  if (AIStation.IsValidStation(d.stationA) && AIStation.IsValidStation(d.stationB)) {
    local ratingA = AIStation.GetCargoRating(d.stationA, d.cargo);
    local ratingB = AIStation.GetCargoRating(d.stationB, d.cargo);
    OpexSign(anchor, "RY|" + yy + "|" + ratingA + "|" + ratingB);

    local waitA = AIStation.GetCargoWaiting(d.stationA, d.cargo);
    local waitB = AIStation.GetCargoWaiting(d.stationB, d.cargo);
    OpexSign(anchor, "RW|" + yy + "|" + waitA + "|" + waitB);

    /* Reprend EXACTEMENT le test de production utilise a la construction (OpexRoadStopSites,
     * meme tuile, meme rayon) pour savoir si la sonde de placement reste valide dans la duree,
     * ou si elle etait deja un faux positif au moment de la construction. */
    local prodA = AITile.GetCargoProduction(d.stopA, d.cargo, 1, 1, d.coverage);
    local prodB = AITile.GetCargoProduction(d.stopB, d.cargo, 1, 1, d.coverage);
    OpexSign(anchor, "RP|" + yy + "|" + prodA + "|" + prodB);
  }
}

function OpexAI::_scrapDeadLines(year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local toRemove = [];

  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("deadStreak" in line)) continue;  // pax/avion/bateau : jamais candidates

    if (!line.scrapping && line.deadStreak >= DEAD_STREAK_THRESHOLD) {
      line.scrapping = true;
      local stationA = AIStation.GetStationID(line.stationA);
      local ids = [];
      if (AIStation.IsValidStation(stationA)) {
        local vehicles = OpexLineVehicleIds(line, stationA);
        foreach (v in vehicles) {
          if (!AIVehicle.IsValidVehicle(v)) continue;
          if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_RAIL) continue;
          AIVehicle.SendVehicleToDepot(v);
          ids.append(v);
        }
      }
      line.scrapVehicles = ids;
      OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|2");
    }

    if (line.scrapping) {
      local remaining = [];
      foreach (v in line.scrapVehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;  // deja vendu ou detruit
        if (AIVehicle.IsStoppedInDepot(v)) {
          AIVehicle.SellVehicle(v);
        } else {
          remaining.append(v);
        }
      }
      line.scrapVehicles = remaining;
      if (remaining.len() == 0) {
        toRemove.append(i);  // i = position physique dans _lines, pour le retrait -- pas le sign
        OpexSign(anchor, "DL|" + year + "|" + line.lineId + "|3");
      }
    }
  }

  /* Retrait du plus grand indice au plus petit pour ne jamais invalider un indice pas encore
   * traite dans toRemove. */
  for (local k = toRemove.len() - 1; k >= 0; k--) {
    this._lines.remove(toRemove[k]);
  }
}

function OpexAI::_reportYear(year, ranked)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local best = ranked.best.len() > 0 ? ranked.best[0] : null;
  local stats = ranked.stats;

  OpexSign(anchor, "OX|" + year + "|" + this._catalog.towns.len()
                           + "|" + this._catalog.industries.len() + "|" + ranked.all);
  OpexSign(anchor, "OC|" + year + "|" + this._budget.get("cat_towns")
                           + "|" + this._budget.get("cat_industries")
                           + "|" + this._budget.get("cat_rail"));
  OpexSign(anchor, "OP|" + year + "|" + this._budget.get("cand_pax")
                           + "|" + this._budget.get("cand_freight"));
  OpexSign(anchor, "OS|" + year + "|" + this._budget.get("cand_rank")
                           + "|" + this._budget.utilisationPerMille(this._startTick));

  /* Le poste qui domine tout le reste : la recherche de chemin et la construction. */
  local buildOps = this._budget.get("build_plans") + this._budget.get("build_search")
                 + this._budget.get("build_stations") + this._budget.get("build_track")
                 + this._budget.get("build_trains") + this._budget.get("build_water_plans")
                 + this._budget.get("build_docks") + this._budget.get("build_water_depot")
                 + this._budget.get("build_ships");
  OpexSign(anchor, "OW|" + year + "|" + buildOps + "|" + this._lines.len());

  /* Ces quatre panneaux mesurent les rejets AVANT TOP_K : sans eux, ranked.all ne dit pas si le
   * vivier est epuise par les origines, les bornes de distance ou le plancher de rendement. */
  OpexSign(anchor, "CG|" + year + "|" + stats.townsServed + "|" + stats.townsUnserved + "|"
                           + stats.industriesServed + "|" + stats.industriesUnserved);
  OpexSign(anchor, "CR|" + year + "|" + stats.pairsTotal + "|" + stats.pairsOriginServed
                           + "|" + stats.noMonthly);
  OpexSign(anchor, "CD|" + year + "|" + stats.distanceShort + "|" + stats.distanceLong);
  OpexSign(anchor, "CE|" + year + "|" + stats.economicsUnavailable + "|"
                           + stats.profitNonPositive + "|" + stats.ratioTooLow);
  OpexSign(anchor, "CK|" + year + "|" + stats.accepted + "|" + stats.topKOmitted);

  if (best != null) {
    OpexSign(anchor, "OB|" + year + "|" + best.distance
                             + "|" + best.monthly + "|" + best.ratio);
    OpexSign(anchor, "OE|" + year + "|" + best.trains
                             + "|" + best.profitAnnual + "|" + best.capital);
  }
  OpexSign(anchor, "OD|" + year + "|" + ranked.bands[0] + "|" + ranked.bands[1]
                           + "|" + ranked.bands[2] + "|" + ranked.bands[3]);
  if (this._catalog.loco != null) {
    OpexSign(anchor, "OL|" + year + "|" + this._catalog.loco.speed
                             + "|" + this._catalog.costTrackPerTile
                             + "|" + this._catalog.costStation);
  }
}

/* Remboursement annuel : une fois la tresorerie confortablement au-dessus du plancher, on
 * rembourse le maximum d'emprunt qui laisse encore ce plancher disponible pour l'annee
 * suivante. SetLoanAmount exige un multiple de GetLoanInterval() ; on arrondit donc le nouvel
 * emprunt VERS LE HAUT (jamais vers le bas, ce qui rembourserait plus que permis et pourrait
 * passer sous le plancher). Aucune reprise automatique d'emprunt n'existe ailleurs dans le
 * fichier (grep confirme le 2026-08-28) : rembourser ici ne sera donc pas annule au tick suivant. */
function OpexAI::_tryRepayLoan(year)
{
  local loan = AICompany.GetLoanAmount();
  local cash = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  /* Diagnostic emprunt (2026-08-29) : LR ne se pose qu'en cas de remboursement REUSSI, donc un
   * emprunt qui ne descend jamais ne laisse aucune trace expliquant pourquoi. LF enregistre
   * inconditionnellement ce que cette fonction VOIT -- et elle est appelee juste apres _tryBuild,
   * donc au creux annuel de la tresorerie, pas a son sommet. A recouper avec LB. */
  OpexSign(AIMap.GetTileIndex(1, 1), "LF|" + (year % 100) + "|" + cash + "|" + loan);
  if (loan <= 0) return;
  if (cash <= LOAN_REPAY_FLOOR) return;

  local interval = AICompany.GetLoanInterval();
  local minNewLoan = loan - (cash - LOAN_REPAY_FLOOR);
  if (minNewLoan < 0) minNewLoan = 0;
  local newLoan = ((minNewLoan + interval - 1) / interval) * interval;
  if (newLoan >= loan) return;  // moins d'un palier remboursable : pas la peine

  local repaid = loan - newLoan;
  AICompany.SetLoanAmount(newLoan);
  local anchor = AIMap.GetTileIndex(1, 1);
  OpexSign(anchor, "LR|" + year + "|" + repaid + "|" + newLoan);
}

function OpexAI::Start()
{
  AICompany.SetName("OpexAI");
  this._startTick = AIController.GetTick();

  /* Lu une seule fois : le reglage ne change pas en cours de partie, et OpexSign est appele des
   * dizaines de fois par an. Un GetSetting par appel serait du gaspillage pur. */
  DEBUG_SIGNS = AIController.GetSetting("debug_signs") != 0;
  /* Exprime en milliers dans le reglage : AddSetting ne porte que des entiers, et un pas de
   * 50 000 sur une plage de 0 a 2 000 000 serait illisible en unites brutes. */
  LOAN_REPAY_FLOOR = AIController.GetSetting("loan_repay_floor_k") * 1000;
  /* Memes reglages lus UNE fois : OpexIterationBudget et _tryBuild tournent pour chaque candidat,
   * donc les GetSetting dans ces boucles seraient du debit d'opcodes perdu. */
  HARD_ITERATION_CAP = AIController.GetSetting("pathfinder_hard_cap_k") * 1000;
  ABANDON_MEMORY = AIController.GetSetting("abandon_memory") != 0;
  STATION_JOIN = AIController.GetSetting("station_join") != 0;

  /* L'emprunt maximal des le depart : la note de compagnie recompense l'emprunt a zero (5 %),
   * mais une ligne non construite faute de tresorerie coute bien davantage. Le remboursement
   * viendra quand la tresorerie le permettra. */
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());

  local lastYear = -1;
  while (true) {
    local year = AIDate.GetYear(AIDate.GetCurrentDate());
    if (year != lastYear) {
      /* Mesure directe du cycle annuel. YT|aa|debut|fin|tryBuild|saut[C] : aa est l'annee
       * modulo 100 ; saut compte les annees civiles sautees depuis le dernier cycle et C prouve
       * leur rattrapage. Le pire nom est YT|99|999999|999999|999999|99C : 30 caracteres. Un seul
       * panneau par cycle, pose APRES le travail, suffit : fin-debut est la duree totale et le
       * reste (total - tryBuild) couvre catalogue, candidats, rapports, entretien et emprunt. */
      local blockStartTick = AIController.GetTick();
      local skippedYears = (lastYear < 0) ? 0 : year - lastYear - 1;
      /* Tresorerie AVANT toute depense du cycle : c'est le sommet annuel, celui que _tryRepayLoan
       * ne voit jamais puisqu'il est appele apres _tryBuild. LB - LF mesure donc exactement ce que
       * la construction retire au remboursement. */
      OpexSign(AIMap.GetTileIndex(1, 1), "LB|" + (year % 100) + "|"
               + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
      /* Un cycle de construction ne se rejoue jamais retroactivement : ses candidats, son argent
       * et le monde ont deja evolue. En revanche les rapports de lignes, le rebut des lignes
       * mortes et le remboursement restent des decisions valides au moment du rattrapage. Les
       * executer pour chaque annee manquee empeche qu'une annee complete soit totalement ignoree.
       * Le catalogue est ensuite rafraichi une seule fois, a son etat reel courant, avant le
       * classement et la construction de l'annee courante. */
      if (lastYear >= 0) {
        for (local missedYear = lastYear + 1; missedYear < year; missedYear++) {
          this._reportLines(missedYear);
          this._reportRoad(missedYear);
          this._scrapDeadLines(missedYear);
          this._tryRepayLoan(missedYear);
        }
      }
      lastYear = year;
      this._catalog.refresh(this._budget, year);
      local ranked = OpexBuildCandidates(this._catalog, this._budget, this._lines);
      this._reportYear(year, ranked);
      this._reportLines(year);
      this._reportRoad(year);
      this._scrapDeadLines(year);
      this._tryBuildAir(year);
      this._tryBuildWater(year);
      if (ROAD_BUILD_ENABLED) this._tryBuildRoad(year);
      local buildStartTick = AIController.GetTick();
      this._tryBuild(ranked, year);
      local tryBuildTicks = AIController.GetTick() - buildStartTick;
      this._tryRepayLoan(year);
      local blockEndTick = AIController.GetTick();
      local anchor = AIMap.GetTileIndex(1, 1);
      local skippedMarker = skippedYears > 0 ? skippedYears + "C" : "0";
      OpexSign(anchor, "YT|" + (year % 100) + "|" + blockStartTick + "|" + blockEndTick
                               + "|" + tryBuildTicks + "|" + skippedMarker);
    }

    /* Echantillon trimestriel du bus, cf. commentaire sur _roadSampleTick. RQ|q|vitesse|distA :
     * "RQ|40|255|510" = 14 caracteres, tres sous le plafond. */
    if (this._roadDiag != null && this._roadSampleCount < 40) {
      local nowTick = AIController.GetTick();
      if (nowTick - this._roadSampleTick >= 74 * 7) {
        this._roadSampleTick = nowTick;
        this._roadSampleCount++;
        if (AIVehicle.IsValidVehicle(this._roadDiag.vehicle)) {
          local qAnchor = AIMap.GetTileIndex(1, 1);
          local qSpeed = AIVehicle.GetCurrentSpeed(this._roadDiag.vehicle);
          local qLoc = AIVehicle.GetLocation(this._roadDiag.vehicle);
          local qDistA = AIMap.DistanceManhattan(qLoc, this._roadDiag.stopA);
          OpexSign(qAnchor, "RQ|" + this._roadSampleCount + "|" + qSpeed + "|" + qDistA);
          /* La destination REELLE de l'ordre courant (2026-08-28) : le cycle vitesse qui remonte
           * a zero puis redescend toutes les ~5 semaines dans RQ evoque un aller-retour depot
           * plutot qu'une avance vers stopA/stopB -- ceci le prouve ou l'ecarte directement. */
          local qDest = AIOrder.GetOrderDestination(this._roadDiag.vehicle, AIOrder.ORDER_CURRENT);
          OpexSign(qAnchor, "RE|" + this._roadSampleCount + "|" + qDest);
          /* Fait binaire (2026-08-28) : litteralement gare DANS le depot, ou non -- pour trancher
           * entre "les lectures de vitesse sont un artefact, le bus n'a jamais quitte le depot" et
           * "il roule vraiment mais ne progresse jamais". */
          local qParked = AIVehicle.IsStoppedInDepot(this._roadDiag.vehicle) ? 1 : 0;
          OpexSign(qAnchor, "RI|" + this._roadSampleCount + "|" + qParked);
        }
      }
    }

    AIController.Sleep(74 * 10);
  }
}
