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
 *   1  economy.nut       -- profit annuel attendu d'une ligne (rail ET route)
 *   2  candidates.nut    -- cout en iterations d'A* attendu, et le classement par rapport
 *   3  builder_rail.nut  -- construction, sous budget d'iterations calcule par l'arret optimal
 *
 * Plus trois constructeurs secondaires, chacun avec son propre classement ou sa propre unicite :
 * builder_air.nut et builder_water.nut (une liaison passagers chacun), et builder_road.nut, qui
 * est le seul a batir plusieurs lignes par an -- des petites lignes courtes, bus entre villes et
 * surtout CAMIONS pour le fret, dans la bande de 5 a 25 tuiles que le rail refuse.
 *
 * Instrumentation : AILog.Info n'apparait PAS dans la sortie capturee par OpenTTDLab (verifie le
 * 2026-08-28), et un nom de panneau echoue SILENCIEUSEMENT au-dela de 31 caracteres. D'ou des
 * panneaux courts et nombreux plutot que de longues lignes.
 */

import("pathfinder.rail", "RailPathFinder", 1);

/* Declare avant les require() : catalog.nut consulte ce drapeau dans son cycle annuel. Repli
 * actif jusqu'a la lecture unique de road_mode dans Start(), comme les autres reglages de
 * decision. Le defaut vrai est celui de info.nut ; 0 reconstitue la baseline sans route, dont le
 * chemin d'opcodes reste alors EXACTEMENT celui des campagnes anterieures. */
ROAD_BUILD_ENABLED <- true;

/* Part du bassin de ville propre aux bus. 86 est le calibrage route adopte au banc.
 * Le reglage road_pax_catchment_pct vaut 0 pour reconstituer le repli rail a 22 % ; une valeur
 * positive ne touche que OpexRoadPaxCandidates, jamais le rail ni le fret. */
ROAD_PAX_CATCHMENT_SHARE_PCT <- 86;

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

/* Le classement ne contient que TOP_K = 20 candidats. Le plafond de continuation est exactement
 * cette borne existante, pas un second seuil arbitraire : une annee sans argent examine au plus
 * 20 candidats, donc au plus 20 appels de solde et de _tooClose, sans lancer A* avant le test de
 * cash. L'ancien break en examinait 1 ; parcourir les 19 restants est le cout borne qui rend enfin
 * visible un candidat moins rentable par iteration mais financable en capital. */
CASH_CANDIDATE_SCAN_LIMIT <- TOP_K;

/* Phase routiere (2026-08-29). La v1 batissait UNE liaison bus passagers et restait desactivee :
 * sur la graine gelee elle mesurait -599/an pendant 19 ans, mais avec des notes d'arret a -1,
 * c'est-a-dire un bus qui n'a jamais charge un seul passager -- le chiffre condamnait un BUG, pas
 * un mode. Le bug est corrige (bit de route perpendiculaire absent des facades) et le mode devient
 * une phase a part entiere : autant de petites lignes courtes que le classement en propose, et
 * surtout du FRET, camions industrie->industrie et industrie->ville, la ou la v1 ne savait faire
 * que du passager.
 *
 * Deux plafonds annuels, tous deux ARBITRAIRES et a trancher au banc :
 *  - le nombre de lignes neuves, parce que chaque ligne immobilise de la tresorerie que le rail --
 *    qui vaut un ordre de grandeur de plus par ligne -- servira l'annee suivante ;
 *  - le nombre de TENTATIVES, parce qu'un plan qui echoue coute quand meme ses sondes de site et
 *    ses validations d'aretes. Sans lui, une annee ou aucun candidat n'est constructible paierait
 *    le plan des douze. */
const ROAD_MAX_NEW_LINES_PER_YEAR = 3;
const ROAD_MAX_ATTEMPTS_PER_YEAR = 6;

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

/* Raccordement de gare : repli actif jusqu'a la lecture unique de station_join dans Start().
 * Commande AUSSI la relaxation d'origine a la generation (candidates.nut) : les deux moities du
 * meme mecanisme partagent un seul reglage, sans quoi le bras de controle du banc ne reproduirait
 * pas le comportement historique. Repli FAUX depuis le 2026-08-29 : deux bancs (vivier, puis
 * post-traction) montrent un effet de construction sans valeur. Tout le verdict est dans info.nut. */
STATION_JOIN <- false;
/* Porte H1 : 0 = pas de plafond (v1 inerte). N = rejeter la jointure si
 * candidate.distance >= N, sans A*. Defaut 0. Valeur de travail 50
 * (docs/opex_join_pop.json). Inerte si station_join = 0. */
JOIN_MAX_DISTANCE <- 0;
/* H2 : joindre au lieu, pas en repli _tooClose. Defaut 0. Les candidats
 * naissent d'une gare rail OpexAI vers une origine libre dans 25-75
 * tuiles, avec l'objet join deja attache. Independant de station_join :
 * le banc doit pouvoir attribuer. JOINPATH reste dedie. */
JOIN_PLACE <- false;

/* Filtre d'origine sitable : repli FAUX jusqu'a la lecture unique de origin_sitable dans
 * Start(). Defaut 0 apres banc apparie (pas d'effet etabli) ; 1 ecarte du TOP_K les sources
 * fret sans tuile de terre dans le bassin. Le classement a 0 est celui d'avant le filtre. */
ORIGIN_SITABLE <- false;

/* Partage de bassin : repli FAUX jusqu'a la lecture unique de basin_share dans Start().
 * Defaut 0 apres banc apparie : le partage declasse les jointures sans porter de valeur.
 * Inerte si station_join = 0. */
BASIN_SHARE <- false;

/* Reconstitution de flotte routiere : repli ACTIF jusqu'a la lecture unique de road_refleet
 * dans Start(). Defaut 1 : une ligne a zero vehicule avec l'infrastructure payee est un
 * bug, pas un choix. 0 reproduit l'abandon silencieux mesure (graine 42, 2->1->0). */
ROAD_REFLEET <- true;

/* Multistop routier : repli FAUX jusqu'a la lecture unique de road_multistop dans Start().
 * Defaut 0 : un arret par bout, deux vehicules. 1 tente un arret extra joint (meme facade)
 * a chaque extremite, et n'ajoute de vehicules que si les deux bouts ont double. */
ROAD_MULTISTOP <- false;

/* Reemprunt a la demande : repli FAUX jusqu'a la lecture unique de reborrow dans Start().
 * Defaut 0 : le trou "desendetter puis manquer d'argent" est vide (412 GC a emprunt max,
 * 0 tirage). Sans lui, _tryRepayLoan reste a sens unique. */
REBORROW <- false;

/* Item 7 : forcer la construction d'un echantillon de paires rejetees pour profit
 * predit <= 0. Repli FAUX jusqu'a la lecture unique de probe_negative dans Start().
 * Defaut 0 : ce n'est PAS un changement de classement. 1 ne batit qu'apres _tryBuild,
 * au plus une tentative rail par an, sur le cash que le TOP_K n'a pas pris. */
PROBE_NEGATIVE <- false;

/* Retuning pax borne : repli FAUX jusqu'a la lecture unique de pax_near dans Start().
 * Defaut 0. 1 admet au classement les pax <=100 tuiles a predit > -200, une
 * tentative/an au plafond dur. Le long et le fret restent filtres. */
PAX_NEAR <- false;

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
  /* Le diagnostic mono-bus (_roadDiag, _reportRoad, echantillon trimestriel RQ/RE/RI) a ete retire
   * le 2026-08-29 : il servait a trouver pourquoi UNE liaison ne chargeait rien, la reponse est
   * connue et documentee (builder_road.nut), et les lignes routieres rejoignent desormais _lines,
   * donc _reportLines les mesure comme les autres avec OY/OZ/OU/OO. */
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
  function _tryBuildRoads(year);
  function _tryBuild(ranked, year);
  function _tryProbeNegative(ranked, year);
  function _reportYear(year, ranked);
  function _reportLines(year);
  function _scrapDeadLines(year);
  function _refleetRoadLines(year);
  function _processEvents();
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
  if (reason == "SITEA") return "B";
  if (reason == "SITEB") return "C";
  if (reason == "SITEAB") return "G";
  if (reason == "ECON") return "F";
  if (reason == "SHORT") return "H";
  if (reason == "NOMATCH") return "M";
  if (reason == "JOINPATH") return "J";
  if (reason == "STNFAIL") return "S";
  if (reason == "TRKFAIL") return "T";
  if (reason == "DEPFAIL") return "E";
  if (reason == "SIGFAIL") return "U";
  if (reason == "ORDFAIL") return "R";
  if (reason == "NOTRAIN") return "V";
  return "X";
}

/* Le station_id est l'identite de bassin, pas la tuile de quai : deux lignes raccordees ont des
 * sorties differentes mais le meme ID. Un ancien etat sauvegarde sans la liste vehicles retombe
 * prudemment sur la requete par gare ; les nouvelles lignes rail n'utilisent jamais ce repli
 * ambigu.
 *
 * 🔴 EXCEPTION ROUTE (2026-08-29), et c'est une correction, pas une commodite. Mesure, campagne
 * 20 ans graine 42 : trois lignes routieres sur quatre finissaient a vehCount = 0 alors que leur
 * gare gardait une note de 48 a 60 -- et l'une d'elles est repassee de 0 a 1 vehicule d'une annee
 * sur l'autre, ce qu'aucune disparition ne peut expliquer. La liste figee a la construction est
 * donc FAUSSE des qu'un vehicule est remplace : le renouvellement automatique detruit l'ancien
 * identifiant et en cree un neuf, et OpenTTD RECYCLE les identifiants liberes -- une liste figee
 * finit par ne plus rien designer, ou pire par designer le vehicule d'une autre ligne.
 *
 * La raison qui imposait la liste figee cote rail ne s'applique pas ici : un arret routier est
 * toujours pose en STATION_NEW et n'est jamais joint a un autre, donc AIVehicleList_Station rend
 * exactement les vehicules de CETTE ligne. C'est la seule source de verite qui survit au
 * renouvellement. */
function OpexLineVehicleIds(line, stationId)
{
  if (("mode" in line) && line.mode == "road") {
    local roadIds = [];
    local roadVehicles = AIVehicleList_Station(stationId);
    for (local v = roadVehicles.Begin(); !roadVehicles.IsEnd(); v = roadVehicles.Next()) {
      roadIds.append(v);
    }
    return roadIds;
  }
  if ("vehicles" in line) return line.vehicles;
  local ids = [];
  local vehicles = AIVehicleList_Station(stationId);
  for (local v = vehicles.Begin(); !vehicles.IsEnd(); v = vehicles.Next()) ids.append(v);
  return ids;
}

/* Le type de vehicule se deduit du mode de la ligne, et d'un seul endroit : _reportLines et
 * _scrapDeadLines le demandaient chacun de leur cote, le second en le codant en dur a VT_RAIL --
 * ce qui aurait laisse une ligne routiere morte rouler pour toujours. */
function OpexMedianInt(values)
{
  local n = values.len();
  if (n == 0) return 0;
  for (local i = 1; i < n; i++) {
    local v = values[i];
    local j = i;
    while (j > 0 && values[j - 1] > v) {
      values[j] = values[j - 1];
      j--;
    }
    values[j] = v;
  }
  return values[n / 2];
}

function OpexLineVehicleType(line)
{
  if (!("mode" in line)) return AIVehicle.VT_RAIL;
  if (line.mode == "air") return AIVehicle.VT_AIR;
  if (line.mode == "water") return AIVehicle.VT_WATER;
  if (line.mode == "road") return AIVehicle.VT_ROAD;
  return AIVehicle.VT_RAIL;
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
 * seul conflit logique.
 *
 * Succes : table avec candidateEnd / stationId / platform. Refus : { refuse = code }, jamais
 * null -- le null d'avant ne disait pas laquelle des trois conditions avait tue.
 *   M  plusieurs StationID, ou les deux extremites du candidat
 *   K  rail, mais kind ou cargo different
 *   R  meme cargo fret, roles inverses (source contre puits)
 *   N  aucune ligne rail avec un plan de quai (air / dock / etat ancien)
 *   E  conflicts vide (ne devrait pas arriver si blocking >= 0) */
function OpexFindStationJoin(candidate, conflicts)
{
  if (conflicts.len() == 0) return { refuse = "E" };
  local first = conflicts[0];
  foreach (conflict in conflicts) {
    if (conflict.end != first.end || conflict.stationId != first.stationId) return { refuse = "M" };
  }
  local refuse = "N";
  foreach (conflict in conflicts) {
    if (OpexJoinCompatible(candidate, conflict)) {
      local platform = conflict.lineEnd == "A" ? conflict.line.platformA : conflict.line.platformB;
      return { candidateEnd = conflict.end, stationId = conflict.stationId, platform = platform };
    }
    local line = conflict.line;
    if (("mode" in line) || !("platformA" in line) || !("platformB" in line)) continue;
    if (!("kind" in line) || line.kind != candidate.kind || line.cargo != candidate.cargo) {
      if (refuse == "N") refuse = "K";
      continue;
    }
    refuse = "R";
  }
  return { refuse = refuse };
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
  local need = capital + CASH_RESERVE + AIR_CAPITAL_MARGIN;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    if (REBORROW) money = OpexTryReborrow(need, money);
    if (money < need) return;
  }

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
  local need = capital + CASH_RESERVE + WATER_CAPITAL_MARGIN;
  local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  if (money < need) {
    if (REBORROW) money = OpexTryReborrow(need, money);
    if (money < need) return;
  }
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

/* La phase routiere : autant de petites lignes courtes que le classement en propose, dans la
 * limite des deux plafonds annuels ci-dessus.
 *
 * Elle tourne APRES _tryBuild, et c'est une decision, pas un detail d'ordonnancement. Les deux
 * modes ne se disputent jamais la meme PAIRE (leurs bandes de distance sont disjointes : le rail
 * commence ou la route s'arrete, a 25 tuiles) mais ils se disputent les memes ORIGINES et la meme
 * tresorerie. Le rail vaut un ordre de grandeur de plus par ligne : il choisit donc en premier, et
 * la route prend ce qui reste -- des villes et des industries qu'aucune ligne rail n'a retenues,
 * avec l'argent qui dort une fois la reserve rail respectee. C'est aussi ce qui garde la baseline
 * rail lisible au banc : a road_mode = 0 il ne se passe litteralement rien de plus.
 *
 * Le classement est recalcule ICI et non dans le cycle annuel : les lignes rail de l'annee
 * viennent d'entrer dans _lines, et leurs origines doivent etre exclues avant que la route ne
 * choisisse. */
function OpexAI::_tryBuildRoads(year)
{
  if (!ROAD_BUILD_ENABLED || this._catalog.roadType < 0) return;
  local anchor = AIMap.GetTileIndex(1, 1);
  local ranked = OpexBuildRoadCandidates(this._catalog, this._budget, this._lines);
  local best = ranked.best;
  local attempts = 0;
  local builtCount = 0;
  local yy = year % 100;

  for (local i = 0; i < best.len(); i++) {
    if (builtCount >= ROAD_MAX_NEW_LINES_PER_YEAR) break;
    if (attempts >= ROAD_MAX_ATTEMPTS_PER_YEAR) break;
    local candidate = best[i];
    /* Le classement a ete etabli avant la premiere construction de cette boucle : une ligne batie
     * il y a deux tours a pu prendre l'une des deux extremites de ce candidat. Sans cette
     * reverification, deux lignes routieres de la meme annee se poseraient sur la meme ville. */
    if (OpexOriginServed(this._lines, candidate.src, true)) continue;
    if (OpexOriginServed(this._lines, candidate.dst, true)) continue;

    local need = candidate.capital + CASH_RESERVE + ROAD_CAPITAL_MARGIN;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need) {
      if (REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) break;
    }

    attempts++;
    this._budget.begin();
    local planning = OpexRoadPlanFor(this._catalog, candidate);
    local planOps = this._budget.end("build_road_plans");
    local plan = planning.plan;
    local idx = this._nextLineId;
    if (plan == null) {
      /* "RA|99|999|6|TRACEX|0" = 20 caracteres, sous le plafond silencieux de 31. Deux choses y
       * comptent. La RAISON porte l'etape qui a bute (SITEA, SITEB, TRACEX, DEPOTX) plutot qu'un
       * "pas de plan" indifferencie : chacune appelle un correctif different. Et le rang de la
       * tentative DANS L'ANNEE est indispensable, parce que _nextLineId n'avance que sur un succes
       * -- sans lui, toutes les tentatives echouees d'une annee partageraient un identifiant, leurs
       * panneaux de cout RB seraient indistinguables, et le depouillement compterait plusieurs fois
       * les memes opcodes. */
      OpexSign(anchor, "RA|" + yy + "|" + idx + "|" + attempts + "|" + planning.reason + "|0");
      OpexSign(anchor, "RB|" + yy + "|" + idx + "|" + attempts + "|" + planOps + "|0");
      /* SITEA/B : cargo vu / tuiles constructibles plates / commandes acceptees. Sans ca, 48
       * sondes brulees sur des maisons ne se distinguent pas d'une industrie sans herbe.
       * "RI|99|999|6|999|99|99" = 22 caracteres. */
      if ((planning.reason == "SITEA" || planning.reason == "SITEB") && ("site" in planning)) {
        local s = planning.site;
        OpexSign(anchor, "RI|" + yy + "|" + idx + "|" + attempts + "|" + s.nCargo + "|"
                                 + s.nBuildable + "|" + s.nCmd);
      }
      /* TRACEX/DEPOTX : essais / L trop long / traverse l'arret / arete refusee.
       * "RT|99|999|6|32|99|99|99" = 23 caracteres. */
      if ((planning.reason == "TRACEX" || planning.reason == "DEPOTX") && ("trace" in planning)) {
        local t = planning.trace;
        OpexSign(anchor, "RT|" + yy + "|" + idx + "|" + attempts + "|" + t.trials + "|"
                                 + t.nLong + "|" + t.nHit + "|" + t.nUnb);
      }
      continue;
    }
    local result = OpexBuildRoadRoute(this._catalog, this._budget, plan, candidate);
    /* Le cout REEL d'une tentative, plan et construction separes. Mesure 2026-08-30
     * (docs/opex_road_rb_calibrate.json) : le plan OK est ~0,29x le modele, et un classement
     * unique affamerait le rail. Le panneau reste, pour ne pas reposer la question a l'aveugle. */
    OpexSign(anchor, "RB|" + yy + "|" + idx + "|" + attempts + "|" + planOps
                             + "|" + result.opcodes);
    if (!result.ok) {
      OpexSign(anchor, "RA|" + yy + "|" + idx + "|" + attempts + "|" + result.reason
                               + "|" + result.error);
      continue;
    }

    builtCount++;
    /* Memes panneaux de prediction que le rail, et volontairement : ils sont indexes par lineId
     * dans un espace de numerotation commun, donc sweeps/opex_full_campaign.py croise deja
     * predit et reel sans rien savoir du mode. PM porte le mode et la distance, RC le cout paye et
     * la flotte reellement obtenue (un clone peut echouer sans faire echouer la ligne). */
    OpexSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
    OpexSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
    OpexSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
    OpexSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains);
    OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays + "|" + candidate.distance);
    OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                             + "|" + candidate.monthly);
    OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));
    OpexSign(anchor, "PM|" + idx + "|R|" + candidate.distance + "|"
                             + AICargo.GetCargoLabel(candidate.cargo));
    /* "RC|99|999|6|999999|2" = 20 caracteres. L'annee et le rang de la tentative y figurent pour
     * apparier ce succes a son panneau RB de cout, indexe par ce meme triplet. */
    OpexSign(anchor, "RC|" + yy + "|" + idx + "|" + attempts + "|" + result.cost
                             + "|" + result.vehicles.len());
    /* "RM|99|999|6|2|2|4" = 16 caracteres. Gate comme CJ : a 0, zero panneau, le bras
     * de controle du banc ne paie pas la commande. nStops 1 ou 2 par bout. */
    if (ROAD_MULTISTOP) {
      OpexSign(anchor, "RM|" + yy + "|" + idx + "|" + attempts + "|"
                               + result.nStopsA + "|" + result.nStopsB + "|"
                               + result.vehicles.len());
    }

    /* La ligne routiere rejoint _lines comme les autres : elle est ainsi rapportee chaque annee
     * (_reportLines) et mise au rebut si elle meurt (_scrapDeadLines), sans code parallele. Le
     * champ mode = "road" est ce qui la retire des deux filets rail -- OpexOriginServed appele
     * avec includeRoad = false, et _tooClose -- pour qu'une desserte de bus de 12 tuiles ne
     * verrouille jamais une ville contre une liaison rail interurbaine. */
    this._lines.append({
      stationA = result.stopA, stationB = result.stopB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = candidate.profitAnnual, iterations = candidate.iterations,
      trains = result.vehicles.len(), distance = candidate.distance, year = year,
      predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
      predAmort = candidate.amortAnnual, predCarried = candidate.carried,
      predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
      effectiveSpeed = candidate.effectiveSpeed,
      catalogSpeed = candidate.engine.speed,
      /* Pas de champ `vehicles` ici, DELIBEREMENT : une liste figee ne survit pas au
       * renouvellement automatique, qui detruit l'identifiant et le fait recycler par le moteur
       * (cf. OpexLineVehicleIds). Une ligne routiere interroge toujours sa gare. */
      mode = "road", kind = candidate.kind, depot = result.depot,
      nStopsA = result.nStopsA, nStopsB = result.nStopsB,
      /* Une extremite de ville n'est pas une industrie : GetIndustryID y rendrait un identifiant
       * invalide, que _reportLines rapporterait comme une industrie fermee. Seule une extremite
       * reellement industrielle (townId < 0 dans le candidat) est interrogee. */
      srcIndustry = (candidate.kind == "freight" && candidate.srcTown < 0)
                    ? AIIndustry.GetIndustryID(candidate.src) : -1,
      dstIndustry = (candidate.kind == "freight" && candidate.dstTown < 0)
                    ? AIIndustry.GetIndustryID(candidate.dst) : -1,
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lineId = idx,
    });
    this._nextLineId++;
  }

  /* "RN|99|999|9|9|999999" = 20 caracteres : candidats classes, tentatives, lignes baties, et le
   * cout en opcodes de la GENERATION de candidats. Le denominateur qui manquait a la v1 -- sans
   * lui, zero ligne routiere une annee donnee ne distingue pas "aucun candidat" de "six plans en
   * echec" -- plus le prix paye les annees ou la phase ne batit rien du tout. */
  OpexSign(anchor, "RN|" + yy + "|" + ranked.all + "|" + attempts + "|" + builtCount
                           + "|" + ranked.opcodes);
  /* "RS|99|9999|9999|999" = 19 caracteres. RN dit combien de candidats ont SURVECU ; RS dit ce que
   * le vivier contenait avant filtrage et ce que le plancher de profit a coupe. Sans lui, "quatre
   * candidats classes" ne distingue pas une carte pauvre en paires courtes d'un plancher trop
   * haut -- et le plancher, lui, est arbitraire (cf. ROAD_MIN_PROFIT_ANNUAL). */
  OpexSign(anchor, "RS|" + yy + "|" + ranked.stats.pairsInBand + "|"
                           + ranked.stats.profitTooLow + "|" + ranked.stats.accepted);
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
 * Rend trois champs :
 *  - `hard` : distance d'un rejet SANS APPEL, ou -1. Un seul cas depuis le 2026-08-29 -- les DEUX
 *    extremites reutilisent une origine deja servie, c'est-a-dire un corridor deja tenu.
 *  - `blocking` : distance du conflit le plus proche qui EXIGE un quai joint, ou -1 si le candidat
 *    est libre. Reunit les deux tests : une extremite (une seule) sur une origine servie, et le
 *    filet physique MIN_SEPARATION.
 *  - `conflicts` : les gares touchees, pour qu'OpexFindStationJoin arbitre. Une entree par couple
 *    (extremite du candidat, extremite de ligne existante) ; un doublon exact -- meme gare vue par
 *    les deux tests -- est inoffensif, l'arbitrage ne regarde que `end` et `stationId`.
 *
 * HISTOIRE, parce que ce point s'est deja retourne une fois. Le 2026-08-28, le test 1 (identite
 * d'origine) avait ete deplace en amont, a la generation (candidates.nut), pour ne pas gaspiller
 * le TOP_K ; le 2026-08-29 la mesure a montre que ce deplacement tuait le vivier ENTIER a partir
 * de 1982 et rendait station_join inatteignable (0 tentative en 20 ans). La generation ne coupe
 * donc plus que les paires dont les deux bouts sont servis, et le test 1 REVIENT ici -- ou il peut
 * offrir la jointure au lieu de rejeter. La regle de fond n'a pas bouge : jamais deux gares a nous
 * sur la meme origine. */
function OpexAI::_tooClose(candidate)
{
  local entries = [["A", candidate.src], ["B", candidate.dst]];
  local conflicts = [];

  /* Test 1 : identite d'origine. On distingue les deux extremites du CANDIDAT, parce que "une
   * seule servie" est desormais recuperable et "les deux servies" ne l'est pas. */
  local originA = -1;
  local originB = -1;
  foreach (line in this._lines) {
    /* Les lignes routieres partagent ce tableau depuis le 2026-08-29 mais sont invisibles aux deux
     * filets rail, origine comme filet physique : une desserte routiere de 12 tuiles n'epuise pas
     * une ville, et son arret (rayon 3) ne cannibalise pas le bassin d'une gare rail. Les laisser
     * ici rejetterait des candidats rail bien plus rentables au profit de bus. */
    if (("mode" in line) && line.mode == "road") continue;
    foreach (lineEnd in ["A", "B"]) {
      local originTile = lineEnd == "A" ? line.originA : line.originB;
      foreach (entry in entries) {
        local d = AIMap.DistanceManhattan(entry[1], originTile);
        if (d >= ORIGIN_SEPARATION) continue;
        if (entry[0] == "A") originA = OpexRememberClosest(d, ORIGIN_SEPARATION, originA);
        else originB = OpexRememberClosest(d, ORIGIN_SEPARATION, originB);
        /* Une ligne dont la gare n'est plus valide (ferraillee) ne propose aucune jointure : elle
         * ne peut pas entrer dans `conflicts`, et l'extremite reste donc bloquante sans issue. */
        local stationId = OpexLineStationId(line, lineEnd);
        if (stationId < 0) continue;
        conflicts.append({ end = entry[0], line = line, lineEnd = lineEnd,
                           stationId = stationId, distance = d });
      }
    }
  }
  if (originA >= 0 && originB >= 0) {
    return { hard = (originA < originB ? originA : originB), blocking = -1, conflicts = [] };
  }
  local blocking = originA >= 0 ? originA : originB;

  /* Test 2 : filet physique. Depend de la gare BATIE, donc incalculable a la generation. */
  foreach (line in this._lines) {
    if (("mode" in line) && line.mode == "road") continue;   // cf. commentaire ci-dessus
    foreach (lineEnd in ["A", "B"]) {
      local stationId = OpexLineStationId(line, lineEnd);
      if (stationId < 0) continue;
      local stationTile = lineEnd == "A" ? line.stationA : line.stationB;
      foreach (entry in entries) {
        local d = AIMap.DistanceManhattan(entry[1], stationTile);
        blocking = OpexRememberClosest(d, MIN_SEPARATION, blocking);
        if (d < MIN_SEPARATION) {
          conflicts.append({ end = entry[0], line = line, lineEnd = lineEnd,
                             stationId = stationId, distance = d });
        }
      }
    }
  }
  return { hard = -1, blocking = blocking, conflicts = conflicts };
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
  local nJoinRefuseMulti = 0;   // M : plusieurs gares, ou les deux extremites
  local nJoinRefuseKind = 0;    // K : kind / cargo
  local nJoinRefuseRole = 0;    // R : roles fret inverses
  local nJoinRefuseOther = 0;   // N / E
  local nJoinRefuseDist = 0;    // D : join_max_distance, pas d'A*
  local nOriginServedRanked = 0;   // candidats du TOP_K qui n'existent QUE grace a la jointure
  local nPlaceJoinRanked = 0;
  local nPlaceJoinBuilt = 0;
  local nPaxNearTried = 0;
  local nPaxNearOk = 0;

  for (local i = 0; i < best.len() && i < CASH_CANDIDATE_SCAN_LIMIT; i++) {
    local candidate = best[i];
    local abandonedKey = null;
    if (ABANDON_MEMORY) {
      abandonedKey = OpexAbandonedPairKey(candidate);
      if (abandonedKey in this._abandonedPairs) {
        nAbandonMemory++;
        continue;
      }
    }
    if (candidate.originServed) nOriginServedRanked++;
    local close = this._tooClose(candidate);
    local join = null;
    local placeJoin = ("placeJoin" in candidate) ? candidate.placeJoin : null;
    if (placeJoin != null) nPlaceJoinRanked++;
    if (close.hard >= 0) {
      nTooClose++;
      if (close.hard < 5) nTooCloseNear++; else nTooCloseFar++;
      continue;
    }
    if (placeJoin != null) {
      /* H2 : le join vient de la generation, pas du filet. Le bout libre
       * reste arme ; un second StationID sur le bout joint est un M. */
      join = placeJoin;
      local joinEnd = join.candidateEnd;
      local refuse = null;
      if (!AIStation.IsValidStation(join.stationId)) refuse = "N";
      else {
        foreach (conflict in close.conflicts) {
          if (conflict.end != joinEnd || conflict.stationId != join.stationId) {
            refuse = "M";
            break;
          }
        }
      }
      if (refuse == null && JOIN_MAX_DISTANCE > 0 && candidate.distance >= JOIN_MAX_DISTANCE) {
        refuse = "D";
      }
      if (refuse != null) {
        if (refuse == "M") nJoinRefuseMulti++;
        else if (refuse == "D") nJoinRefuseDist++;
        else nJoinRefuseOther++;
        nTooClose++;
        if (close.blocking >= 0 && close.blocking < 5) nTooCloseNear++;
        else if (close.blocking >= 5) nTooCloseFar++;
        join = null;
        continue;
      }
    } else if (close.blocking >= 0) {
      /* Le filet garde la main tant que le candidat ne peut pas reutiliser UNE gare logique avec
       * un quai rail dedie. Ne pas choisir une autre gare ni une autre extremite ici : ce serait
       * desarmer MIN_SEPARATION au-dela de l'objet precis de la tranche. */
      if (STATION_JOIN) {
        join = OpexFindStationJoin(candidate, close.conflicts);
        if ("refuse" in join) {
          local r = join.refuse;
          if (r == "M") nJoinRefuseMulti++;
          else if (r == "K") nJoinRefuseKind++;
          else if (r == "R") nJoinRefuseRole++;
          else nJoinRefuseOther++;
          join = null;
        } else if (JOIN_MAX_DISTANCE > 0 && candidate.distance >= JOIN_MAX_DISTANCE) {
          /* H1 : le long est le reliquat qui ne paie pas (docs/opex_join_pop.json).
           * Rejet tooClose historique, zero A*. */
          nJoinRefuseDist++;
          join = null;
        }
      }
      if (join == null) {
        nTooClose++;
        if (close.blocking < 5) nTooCloseNear++; else nTooCloseFar++;
        continue;
      }
    }

    local need = candidate.capital + CASH_RESERVE;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need) {
      if (REBORROW) money = OpexTryReborrow(need, money);
      if (money < need) {
        nCashBlocked++;
        OpexSign(anchor, "GC|" + year + "|" + money + "|" + candidate.capital);
        /* Le ratio trie le profit/iteration, pas le capital. Continuer est donc la seule facon de
         * chercher une ligne financable plus bas ; CASH_CANDIDATE_SCAN_LIMIT borne ce parcours a la
         * taille deja plafonnee du TOP_K. */
        continue;
      }
    }

    local isPaxNear = PAX_NEAR && ("paxNear" in candidate) && candidate.paxNear;
    if (isPaxNear && nPaxNearTried >= PAX_NEAR_MAX_ATTEMPTS_PER_YEAR) continue;

    local alternativeSource = (i + 1 < best.len()) ? "S" : "L";
    local alternativeRatio = (alternativeSource == "S") ? best[i + 1].ratio : MIN_RATIO;
    /* pax_near : profit negatif -> forme fermee negative -> plancher 2000, qui
     * abandonnait le 75-100. alternativeRatio 0 = chemin Z, HARD_ITERATION_CAP. */
    if (isPaxNear) alternativeRatio = 0;
    local result = OpexBuildLine(this._catalog, this._budget, candidate, alternativeRatio, join,
                                 CASH_RESERVE);
    if (isPaxNear) nPaxNearTried++;
    /* La longueur retenue peut etre plus courte que le souhait, ou celle d'un quai joint plus
     * longue. OpexBuildLine a alors recalcule le capital avant toute demolition. Ce rejet reste
     * financier, pas un echec de plan ou de voie, et le classement continue comme ci-dessus. */
    if (result.reason == "CASH") {
      /* OpexBuildLine a deja tente le reemprunt sur le capital recalcule. S'il ressort CASH,
       * le plafond d'emprunt n'y suffisait pas : meme continue que ci-dessus. */
      nCashBlocked++;
      OpexSign(anchor, "GC|" + year + "|" + result.money + "|" + result.capital);
      continue;
    }
    if (join != null) nJoinAttempts++;
    local budgetInfo = result.budgetInfo;
    local iterationBudget = result.iterationBudget;

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
     * de la tentative, plus la distance -- sans elle, P(construite | distance) est incalculable
     * (les ABND n'avaient que des iterations). Pire nom OB|A|99|999|400|9999999|200 : 28. */
    OpexSign(anchor, "OB|A|" + (year % 100) + "|" + this._nextLineId + "|" + rankPacked
                             + "|" + result.opcodes + "|" + candidate.distance);
    /* PS decompose SITEA/B/AB : rectangles libres, ceux qui ont du cargo, ceux que
     * BuildRailStation a acceptes. Le rang packed aligne le panneau sur OR.
     * JoinEnd A/B/N dit si l'echec est le parallele joint. Pire nom
     * `PS|89|999|400|9999|999|99|P|A` : 29 caracteres. */
    if (result.reason == "SITEA" || result.reason == "SITEB" || result.reason == "SITEAB") {
      OpexSign(anchor, "PS|" + (year % 100) + "|" + this._nextLineId + "|" + rankPacked
                              + "|" + result.siteClear + "|" + result.siteCargo + "|"
                              + result.siteCmd + "|" + result.siteKind + "|"
                              + result.joinEnd);
    }
    if (result.error != 0) OpexSign(anchor, "OV|" + this._nextLineId + "|" + result.error);
    if (result.diag != null) {
      OpexSign(anchor, "OG|" + result.diag.railtype + "|" + result.diag.isDepot
                               + "|" + result.diag.buildable + "|" + result.diag.canRun);
      OpexSign(anchor, "OH|" + result.diag.price + "|" + result.diag.cash);
      OpexSign(anchor, "OI|" + result.diag.engineRail + "|" + result.diag.depotRail
                               + "|" + result.diag.vehType + "|" + result.diag.testOk);
    }

    /* Capacity telemetry is emitted for both success and fail-closed rollback. On failure the
     * next line id identifies the attempt, just like OR/OB above. */
    if (candidate.trains > 1 && (result.capacitySignalSegments > 0 ||
                                 result.capacitySignalFailures.len() > 0 ||
                                 result.reason == "SIGFAIL")) {
      OpexSign(anchor, "SC|" + this._nextLineId + "|" + result.capacitySignalsOk + "|"
                               + result.capacitySignalsFail + "|" + result.capacitySignalSegments);
      foreach (failure in result.capacitySignalFailures) {
        OpexSign(anchor, "SF|" + this._nextLineId + "|" + failure.slot + "|" + failure.error + "|"
                                 + failure.tracks + "|" + failure.x + "|" + failure.y);
      }
    }
    /* DT|id|posee|trains|skip : skip 1=join 2=quai 3=chemin 4=voie 5=gare 6=depot 7=cash 8=chevauche 9=court.
     * Pire nom DT|999|1|2|9 = 12 caracteres. */
    if (candidate.trains > 1 && (result.ok || result.doubleTrack != 0 || result.doubleSkip != 0)) {
      OpexSign(anchor, "DT|" + this._nextLineId + "|" + result.doubleTrack + "|"
                               + result.trains + "|" + result.doubleSkip);
    }

    if (join != null && (result.signalsOk > 0 || result.signalsFail > 0 ||
                         result.signalsSkip > 0 || result.reason == "SIGFAIL")) {
      OpexSign(anchor, "SG|" + this._nextLineId + "|" + result.signalsOk + "|"
                               + result.signalsFail + "|" + result.signalJunc);
      OpexSign(anchor, "SJ|" + this._nextLineId + "|" + result.signalsSkip + "|"
                               + result.signalFailures.len());
      foreach (failure in result.signalFailures) {
        OpexSign(anchor, "JF|" + this._nextLineId + "|" + failure.kind + "|" + failure.slot + "|"
                                 + failure.error + "|" + failure.tracks + "|" + failure.x + "|"
                                 + failure.y);
      }
    }

    if (result.ok) {
      nBuilt++;
      if (join != null) nJoinBuilt++;
      if (placeJoin != null) nPlaceJoinBuilt++;
      if (isPaxNear) nPaxNearOk++;
      local idx = this._nextLineId;
      /* Predit-vs-reel (etage 1) : le detail du calcul au moment de la construction, pour pouvoir
       * le comparer plus tard a la mesure reelle (_reportLines). Les dimensions traction ajoutent
       * trois panneaux courts plutot qu'un nom trop long : OQ reste sous 31 caracteres avec debit,
       * flotte, wagons et capacite ; OT porte le temps, la distance, le quai et la vitesse ; PL
       * confronte enfin le quai et les wagons attendus a la longueur AIVehicle.GetLength mesuree. */
      OpexSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
      OpexSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
      OpexSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
      OpexSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains
                              + "|" + candidate.wagons + "|" + candidate.perTrain);
      /* Arbitrage visible : offre apres note, capacite, intervalle finalement choisi, note estimee,
       * puis nombre que le headway de 7 jours aurait impose. Sans ce panneau, un train long unique
       * et trois trains courts auraient le meme OQ et la correction resterait inverifiable. */
      OpexSign(anchor, "PT|" + idx + "|" + candidate.offered.tointeger() + "|"
                              + candidate.monthlyCapacity.tointeger() + "|"
                              + candidate.headwayDays.tointeger() + "|"
                              + candidate.stationRating.tointeger() + "|"
                              + candidate.trainsForHeadway);
      /* La distance quitte OR (panneau deja plein) et rejoint ce panneau de succes existant. */
      OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays.tointeger() + "|" + candidate.distance
                              + "|" + candidate.platformLength + "|" + candidate.effectiveSpeed.tointeger());
      /* L'ancienne politique ne gardait que la locomotive catalogue la plus rapide (160 km/h en
       * 1970), sans masse, puissance ni effort de traction. Ce panneau expose maintenant la locomotive
       * REELLEMENT attelee a cette
       * charge : identifiant, plafond catalogue, vitesse traction, puissance et effort de traction. */
      OpexSign(anchor, "OL|" + idx + "|" + candidate.loco.id + "|" + candidate.loco.speed
                              + "|" + candidate.effectiveSpeed.tointeger() + "|" + candidate.loco.power
                              + "|" + candidate.loco.tractiveEffort);
      OpexSign(anchor, "PL|" + idx + "|" + result.platformLength + "|" + result.wagons
                              + "|" + result.trainLength + "|" + result.locoLength
                              + "|" + result.wagonLength);
      /* PD rend le repli controle lisible : quai voulu, quai finalement bati, puis nombre de
       * plans utilisables aux deux extremites a cette longueur, et 1 si le site n'est pas plat.
       * Les champs plans restent plafonnes a MAX_STATION_PLANS = 12 ; ils mesurent le choix
       * donne a A*, pas le terrain de toute la carte. `PD|99|12|12|12|12|1` : 22 caracteres. */
      OpexSign(anchor, "PD|" + idx + "|" + result.wantedPlatformLength + "|"
                              + result.platformLength + "|" + result.plansA + "|"
                              + result.plansB + "|" + result.slopeRelaxed);
      /* pax vs freight, et la production mensuelle BRUTE utilisee comme entree : pour trancher si
       * le residu du gap vient de la ville entiere comptee au lieu du seul rayon de la gare
       * (candidates.nut le signale deja comme biais non calibre sur les paires de villes). */
      OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                               + "|" + candidate.monthly);
      /* Le label cargo est stable et tient dans un panneau court; il rend la repartition finale
       * lisible sans devoir deviner le type a partir de son identifiant interne. */
      OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));
      /* Le marqueur qui manquait pour chiffrer le BIAIS CONNU de candidates.nut (2026-08-29).
       * nJoinBuilt est un compteur ANNUEL : il dit combien de jointures ont abouti, jamais
       * LESQUELLES, donc il ne permet pas de comparer le predit au reel ligne par ligne.
       *  - champ 2 : extremite jointe, "A"/"B", ou "N" si la ligne a bati ses deux gares ;
       *  - champ 3 : 1 si le CANDIDAT reutilisait une origine deja desservie.
       * Les deux ne coincident pas : une jointure peut naitre d'un conflit purement PHYSIQUE
       * (MIN_SEPARATION, une autre origine), et ce cas-la n'a aucun double comptage a corriger.
       * C'est le champ 3, pas le champ 2, qui isole les lignes suspectes.
       * Gate sur STATION_JOIN comme GM/CJ/OB : a 0 les deux champs valent "N" et 0 pour toutes
       * les lignes, donc le panneau ne porterait aucune information et couterait quand meme une
       * commande par ligne au bras de controle. */
      if (STATION_JOIN || JOIN_PLACE) {
        local joinHow = "";
        if (placeJoin != null) joinHow = "|P";
        else if (join != null) joinHow = "|T";
        OpexSign(anchor, "PJ|" + idx + "|" + (join == null ? "N" : join.candidateEnd)
                                 + "|" + (candidate.originServed ? 1 : 0) + joinHow);
      }
      if (isPaxNear) OpexSign(anchor, "PY|" + idx);

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
        wagons = candidate.wagons, platformLength = candidate.platformLength,
        loco = candidate.loco, effectiveSpeed = candidate.effectiveSpeed,
        headwayDays = candidate.headwayDays, stationRating = candidate.stationRating,
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
        lastLiveVehicles = result.trains, suspectedCrashes = 0,
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

  /* Sommaire annuel du goulot : _tooClose est publie ci-dessous ; chaque rejet de tresorerie est
   * deja publie par GC avec son solde et son capital. Il n'y a plus de suffixe inexplore : le
   * continue parcourt la borne CASH_CANDIDATE_SCAN_LIMIT. */
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
  if (STATION_JOIN || JOIN_PLACE) OpexSign(anchor, "OB|J|" + year + "|" + nJoinAttempts + "|"
                                      + nJoinBuilt + "|" + nJoinFailed);
  /* Compagnons de OB|J : les refus AVANT tentative. 6e champ = D (join_max_distance).
   * "OB|R|1989|20|20|20|20|20" = 26 caracteres. */
  if (STATION_JOIN || JOIN_PLACE) OpexSign(anchor, "OB|R|" + year + "|" + nJoinRefuseMulti + "|"
                                      + nJoinRefuseKind + "|" + nJoinRefuseRole + "|"
                                      + nJoinRefuseOther + "|" + nJoinRefuseDist);
  /* Combien du classement n'existe QUE parce qu'une extremite servie peut etre reprise : c'est la
   * mesure directe de la tranche du 2026-08-29, celle qui dit si le vivier est bien rouvert --
   * independamment du fait que la jointure aboutisse ou non. */
  if (STATION_JOIN || JOIN_PLACE) OpexSign(anchor, "OB|S|" + year + "|" + nOriginServedRanked
                                      + "|" + best.len());
  /* H2 : paires generees / presentes au TOP_K / construites.
   * PH|99|999|20|20 = 16 caracteres. */
  if (JOIN_PLACE) {
    local generated = ("placeJoinAccepted" in ranked.stats) ? ranked.stats.placeJoinAccepted : 0;
    OpexSign(anchor, "PH|" + (year % 100) + "|" + generated + "|" + nPlaceJoinRanked
                             + "|" + nPlaceJoinBuilt);
  }
  /* pax_near : admis au classement / tentatives / succes. Gate : a 0, zero panneau.
   * PE|99|99|9|9 : 14 caracteres. */
  if (PAX_NEAR) {
    local admitted = ("paxNearAdmitted" in ranked.stats) ? ranked.stats.paxNearAdmitted : 0;
    OpexSign(anchor, "PE|" + (year % 100) + "|" + admitted + "|" + nPaxNearTried
                             + "|" + nPaxNearOk);
  }
}

/* Item 7 : au plus UNE tentative rail par an sur une paire que le modele a rejetee
 * (profit predit <= 0). Le classement n'en a jamais vu : stash des moins negatives,
 * hors TOP_K. On ne joint pas, on n'emprunte pas.
 *
 * Budget : alternativeRatio 0, chemin Z, HARD_ITERATION_CAP (40 000). Le premier
 * sondage (docs/opex_probe_negative_20y_5seeds.json) passait MIN_RATIO et tombait
 * au plancher 2000 : 48/52 ABND, mediane 123 tuiles. Le volume des rejets est le
 * long ; 2000 ne le mesure pas. 0 n'ajoute aucun parametre a OpexBuildLine, donc
 * le chemin d'opcodes du classement reste intact.
 *
 * Panneaux, tous gates par probe_negative donc absents du defaut :
 *  PQ|aa|stash|close|cash|tried  -- entonnoir annuel
 *  PN|aa|id|profit|dist|R|iter   -- la tentative, profit AU CLASSEMENT (celui du rejet)
 *  PX|id                         -- la ligne batie est un probe, pas un candidat classe
 * Pire PN|99|999|-999999|200|A|40000 : 29 caracteres. */
function OpexAI::_tryProbeNegative(ranked, year)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local stats = ranked.stats;
  local stash = stats.negativeStash;
  local nClose = 0;
  local nCash = 0;
  local tried = 0;

  for (local i = 0; i < stash.len() && tried == 0; i++) {
    local candidate = stash[i];
    local abandonedKey = null;
    if (ABANDON_MEMORY) {
      abandonedKey = OpexAbandonedPairKey(candidate);
      if (abandonedKey in this._abandonedPairs) {
        nClose++;
        continue;
      }
    }
    local close = this._tooClose(candidate);
    if (close.hard >= 0 || close.blocking >= 0) {
      nClose++;
      continue;
    }
    local need = candidate.capital + CASH_RESERVE;
    local money = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
    if (money < need) {
      nCash++;
      continue;
    }

    local rankingProfit = candidate.profitAnnual;
    local rankingDistance = candidate.distance;
    /* alternativeRatio 0 : chemin Z, HARD_ITERATION_CAP. join = null : on mesure
     * la paire rejetee, pas une jointure. Pas de reemprunt. */
    local result = OpexBuildLine(this._catalog, this._budget, candidate, 0, null,
                                 CASH_RESERVE);
    /* Un seul OpexBuildLine par an : le sondage de site est deja un cout d'opcodes. */
    tried = 1;
    if (result.reason == "CASH") {
      nCash++;
      break;
    }
    local idx = this._nextLineId;
    OpexSign(anchor, "PN|" + (year % 100) + "|" + idx + "|" + rankingProfit + "|"
                             + rankingDistance + "|" + OpexAttemptReasonCode(result.reason)
                             + "|" + result.iterations);
    if (result.reason == "SITEA" || result.reason == "SITEB" || result.reason == "SITEAB") {
      OpexSign(anchor, "PS|" + (year % 100) + "|" + idx + "|1|" + result.siteClear + "|"
                              + result.siteCargo + "|" + result.siteCmd + "|"
                              + result.siteKind + "|" + result.joinEnd);
    }
    if (!result.ok) {
      if (ABANDON_MEMORY && result.reason == "ABND") {
        this._abandonedPairs[abandonedKey] <- true;
      }
      break;
    }

    OpexSign(anchor, "PX|" + idx);
    OpexSign(anchor, "OF|" + idx + "|" + candidate.revenueAnnual);
    OpexSign(anchor, "OJ|" + idx + "|" + candidate.runningAnnual);
    OpexSign(anchor, "OK|" + idx + "|" + candidate.amortAnnual);
    OpexSign(anchor, "OQ|" + idx + "|" + candidate.carried + "|" + candidate.trains
                            + "|" + candidate.wagons + "|" + candidate.perTrain);
    OpexSign(anchor, "PT|" + idx + "|" + candidate.offered.tointeger() + "|"
                            + candidate.monthlyCapacity.tointeger() + "|"
                            + candidate.headwayDays.tointeger() + "|"
                            + candidate.stationRating.tointeger() + "|"
                            + candidate.trainsForHeadway);
    OpexSign(anchor, "OT|" + idx + "|" + candidate.oneWayDays.tointeger() + "|"
                            + candidate.distance + "|" + candidate.platformLength + "|"
                            + candidate.effectiveSpeed.tointeger());
    OpexSign(anchor, "OL|" + idx + "|" + candidate.loco.id + "|" + candidate.loco.speed
                            + "|" + candidate.effectiveSpeed.tointeger() + "|"
                            + candidate.loco.power + "|" + candidate.loco.tractiveEffort);
    OpexSign(anchor, "PL|" + idx + "|" + result.platformLength + "|" + result.wagons
                            + "|" + result.trainLength + "|" + result.locoLength
                            + "|" + result.wagonLength);
    OpexSign(anchor, "PD|" + idx + "|" + result.wantedPlatformLength + "|"
                            + result.platformLength + "|" + result.plansA + "|"
                            + result.plansB + "|" + result.slopeRelaxed);
    OpexSign(anchor, "PK|" + idx + "|" + (candidate.kind == "pax" ? "P" : "F")
                             + "|" + candidate.monthly);
    OpexSign(anchor, "PC|" + idx + "|" + AICargo.GetCargoLabel(candidate.cargo));
    this._lines.append({
      stationA = result.stationA, stationB = result.stationB,
      originA = candidate.src, originB = candidate.dst,
      cargo = candidate.cargo,
      predicted = rankingProfit, iterations = result.iterations,
      trains = result.trains, distance = candidate.distance, year = year,
      predRevenue = candidate.revenueAnnual, predRunning = candidate.runningAnnual,
      predAmort = candidate.amortAnnual, predCarried = candidate.carried,
      predTrains = candidate.trains, predOneWayDays = candidate.oneWayDays,
      wagons = candidate.wagons, platformLength = candidate.platformLength,
      loco = candidate.loco, effectiveSpeed = candidate.effectiveSpeed,
      headwayDays = candidate.headwayDays, stationRating = candidate.stationRating,
      vehicles = result.vehicles, platformA = result.platformA, platformB = result.platformB,
      kind = candidate.kind,
      srcIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.src) : -1,
      dstIndustry = (candidate.kind == "freight") ? AIIndustry.GetIndustryID(candidate.dst) : -1,
      deadStreak = 0, scrapping = false, scrapVehicles = [],
      lastLiveVehicles = result.trains, suspectedCrashes = 0,
      lineId = idx,
      probe = true,
    });
    this._nextLineId++;
  }

  OpexSign(anchor, "PQ|" + (year % 100) + "|" + stash.len() + "|" + nClose + "|"
                           + nCash + "|" + tried);
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
    local vehicleType = OpexLineVehicleType(line);
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
    /* Collision/crash detector: an owned train that disappears outside the explicit freight
     * scrapping path is never silently ignored. RX is an alarm (loss can also be engine-side),
     * not an unsafe recovery action; no replacement is launched from this path. */
    if (vehicleType == AIVehicle.VT_RAIL) {
      local priorLive = ("lastLiveVehicles" in line) ? line.lastLiveVehicles : vehCount;
      if (!line.scrapping && vehCount < priorLive) {
        local lost = priorLive - vehCount;
        local priorCrashes = ("suspectedCrashes" in line) ? line.suspectedCrashes : 0;
        line.suspectedCrashes <- priorCrashes + lost;
        OpexSign(anchor, "RX|" + (year % 100) + "|" + line.lineId + "|" + lost + "|" + line.suspectedCrashes);
      }
      line.lastLiveVehicles <- vehCount;
    }
    OpexSign(anchor, "OO|" + line.lineId + "|" + year + "|" + (profit + runCost));
    /* Rendement de vitesse (taches S4.3). Instantane annuel des convois EN MARCHE
     * (vitesse > 0, donc pas a quai). med / cat = rendement vs catalogue ; med / pred
     * vs la traction. "RV|99|999|8|999|999|999" = 22 caracteres. Rail seulement. */
    if (vehicleType == AIVehicle.VT_RAIL) {
      local moving = [];
      local catalogs = [];
      foreach (v in vehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;
        if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_RAIL) continue;
        local speed = AIVehicle.GetCurrentSpeed(v);
        if (speed <= 0) continue;
        moving.append(speed);
        catalogs.append(AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v)));
      }
      local pred = ("effectiveSpeed" in line) ? line.effectiveSpeed.tointeger() : 0;
      local cat = 0;
      if (catalogs.len() > 0) cat = OpexMedianInt(catalogs);
      else if (("loco" in line) && line.loco != null && ("speed" in line.loco)) cat = line.loco.speed;
      OpexSign(anchor, "RV|" + (year % 100) + "|" + line.lineId + "|" + moving.len() + "|"
                               + OpexMedianInt(moving) + "|" + pred + "|" + cat);
    }
    /* Rendement route (ROAD_SPEED_EFFICIENCY_PCT = 60, hypothese). Meme instantane que RV.
     * "RY|99|999|P|8|999|999|999" = 24 caracteres. */
    if (vehicleType == AIVehicle.VT_ROAD) {
      local moving = [];
      local catalogs = [];
      foreach (v in vehicles) {
        if (!AIVehicle.IsValidVehicle(v)) continue;
        if (AIVehicle.GetVehicleType(v) != AIVehicle.VT_ROAD) continue;
        local speed = AIVehicle.GetCurrentSpeed(v);
        if (speed <= 0) continue;
        moving.append(speed);
        catalogs.append(AIEngine.GetMaxSpeed(AIVehicle.GetEngineType(v)));
      }
      local pred = ("effectiveSpeed" in line) ? line.effectiveSpeed.tointeger() : 0;
      local cat = 0;
      if (catalogs.len() > 0) cat = OpexMedianInt(catalogs);
      else if ("catalogSpeed" in line) cat = line.catalogSpeed;
      local kindCh = (("kind" in line) && line.kind == "pax") ? "P" : "F";
      OpexSign(anchor, "RY|" + (year % 100) + "|" + line.lineId + "|" + kindCh + "|"
                               + moving.len() + "|" + OpexMedianInt(moving) + "|"
                               + pred + "|" + cat);
    }
    /* `<-` : le slot n'existe pas a la construction. `=` leve "the index 'vehCount' does not
     * exist" et tue le script (mesure 2026-08-29, toutes les graines, des 1971). */
    line.vehCount <- vehCount;

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
      /* 🔴 CORRIGE LE 2026-08-29. La condition exigeait AUSSI ratingA <= 0, et cette clause etait
       * fausse : une gare CONSERVE sa derniere note quand plus rien n'y passe. Mesure, campagne
       * 20 ans graine 42 : la ligne routiere OIL_ a perdu son industrie source en 1979 et a roule
       * ONZE ANS a -842 par an sans jamais etre mise au rebut, note de gare figee a 67 tout du
       * long. Le revenu implicite (profit + cout de fonctionnement) suffit et ne ment pas : a zero,
       * la ligne n'a rien transporte de l'annee, quelle que soit la note affichee. La prudence
       * reste assuree par les deux autres conditions -- l'industrie source en souffrance, et
       * DEAD_STREAK_THRESHOLD annees CONSECUTIVES.
       * ⚠️ Comme le renouvellement automatique, ce correctif touche AUSSI les lignes rail. */
      local srcSuffering = (!srcAlive) || (srcProd == 0);
      local collapsed = srcSuffering && (profit + runCost) <= 0;
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
      local vehicleType = OpexLineVehicleType(line);
      if (AIStation.IsValidStation(stationA)) {
        local vehicles = OpexLineVehicleIds(line, stationA);
        foreach (v in vehicles) {
          if (!AIVehicle.IsValidVehicle(v)) continue;
          if (AIVehicle.GetVehicleType(v) != vehicleType) continue;
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

/* Une ligne routiere a zero (ou trop peu de) vehicules avec arrets et depot encore la :
 * l'infrastructure est payee, auto-renouvellement n'a pas suivi. Mesure, plusieurs campagnes
 * graine 42 : 2 -> 1 -> 0, notes 54 -> -1, plus jamais de reconstitution. On complete jusqu'au
 * predTrains d'origine, borne par les quais de la ligne (2 x min(nStops), sinon
 * MAX_ROAD_VEHICLES). Avant _tryBuild : un camion sur une route
 * deja posee rapporte plus, a l'opcode, qu'une ligne neuve. Panneau RF|year|id|added|after
 * (succes) ou RF|year|id|0|REASON (echec). */
function OpexAI::_refleetRoadLines(year)
{
  if (!ROAD_REFLEET) return;
  local anchor = AIMap.GetTileIndex(1, 1);
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    if (!("mode" in line) || line.mode != "road") continue;
    if (("scrapping" in line) && line.scrapping) continue;
    if (("deadStreak" in line) && line.deadStreak > 0) continue;
    local have = ("vehCount" in line) ? line.vehCount : 0;
    local target = ("predTrains" in line) ? line.predTrains : (("trains" in line) ? line.trains : 1);
    if (("trains" in line) && line.trains > target) target = line.trains;
    if (target < 1) target = 1;
    local cap = MAX_ROAD_VEHICLES;
    if (("nStopsA" in line) && ("nStopsB" in line)) {
      local nMin = line.nStopsA < line.nStopsB ? line.nStopsA : line.nStopsB;
      if (nMin < 1) nMin = 1;
      cap = 2 * nMin;
    }
    if (target > cap) target = cap;
    if (have >= target) continue;
    local refill = OpexRoadRefleet(this._catalog, line, have, target);
    if (refill.added > 0) {
      line.vehCount <- refill.after;
      if (("trains" in line) && line.trains < refill.after) line.trains = refill.after;
    }
    OpexSign(anchor, "RF|" + year + "|" + line.lineId + "|" + refill.added + "|"
                     + (refill.added > 0 ? refill.after : refill.reason));
  }
}

function OpexAI::_reportYear(year, ranked)
{
  local anchor = AIMap.GetTileIndex(1, 1);
  local best = ranked.best.len() > 0 ? ranked.best[0] : null;
  local stats = ranked.stats;

  OpexSign(anchor, "OX|" + year + "|" + this._catalog.towns.len()
                           + "|" + this._catalog.industries.len() + "|" + ranked.all);
  /* Croissance de ville (taches S4.5). Ville desservie = GetClosestTown d'une de
   * nos gares (rail/route/air/eau). "TV|89|12|9999|30|999" = 22 caracteres. */
  local servedTowns = {};
  for (local i = 0; i < this._lines.len(); i++) {
    local line = this._lines[i];
    local ends = [line.stationA];
    if (("stationB" in line) && line.stationB != null) ends.append(line.stationB);
    foreach (tile in ends) {
      if (tile == null || !AIMap.IsValidTile(tile)) continue;
      local town = AITile.GetClosestTown(tile);
      if (town >= 0) servedTowns.rawset(town, true);
    }
  }
  local servedPops = [];
  local freePops = [];
  foreach (town in this._catalog.towns) {
    if (town.id in servedTowns) servedPops.append(town.pop);
    else freePops.append(town.pop);
  }
  OpexSign(anchor, "TV|" + (year % 100) + "|" + servedPops.len() + "|"
                           + OpexMedianInt(servedPops) + "|" + freePops.len() + "|"
                           + OpexMedianInt(freePops));
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
  /* Le devenir des paires a UNE seule extremite servie, que la generation ne jette plus depuis le
   * 2026-08-29 : combien sont irrecuperables (aucune jointure concevable) et combien poursuivent
   * vers l'etage economique. La somme des deux est ce que l'ancienne regle coupait a l'aveugle.
   * Gate sur STATION_JOIN comme GM l'est sur ABANDON_MEMORY : le bras de controle du banc ne doit
   * pas payer une commande de panneau que l'autre bras ne paie pas. Son absence vaut zero. */
  if (STATION_JOIN || JOIN_PLACE) {
    OpexSign(anchor, "CJ|" + year + "|" + stats.pairsJoinImpossible + "|" + stats.pairsOneServed);
  }
  OpexSign(anchor, "CD|" + year + "|" + stats.distanceShort + "|" + stats.distanceLong);
  OpexSign(anchor, "CE|" + year + "|" + stats.economicsUnavailable + "|"
                           + stats.profitNonPositive + "|" + stats.ratioTooLow);
  OpexSign(anchor, "CK|" + year + "|" + stats.accepted + "|" + stats.topKOmitted);
  /* Item 7 : population des rejets profit<=0, pas seulement le compte CE.
   * NH|aa|n50|n75|n100|n200  bandes de distance ; NM|aa|pax|frt|near|mean.
   * Pire NM|99|9999|9999|9999|-999999 : 28 caracteres. Gate : a 0, zero panneau. */
  if (PROBE_NEGATIVE) {
    local mean = 0;
    if (stats.profitNonPositive > 0) mean = stats.negSum / stats.profitNonPositive;
    OpexSign(anchor, "NH|" + (year % 100) + "|" + stats.negBand50 + "|" + stats.negBand75
                             + "|" + stats.negBand100 + "|" + stats.negBand200);
    OpexSign(anchor, "NM|" + (year % 100) + "|" + stats.negPax + "|" + stats.negFreight
                             + "|" + stats.negNear + "|" + mean);
  }

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

/* Tire le palier d'emprunt manquant pour atteindre `need`, jamais le maximum. Appeler seulement
 * quand REBORROW est vrai ET que money < need : le chemin historique (reborrow=0) ne paie alors
 * ni GetLoanAmount ni cette fonction.
 *
 * Arrondi VERS LE HAUT au palier GetLoanInterval(), puis bride a GetMaxLoanAmount() -- le
 * symetrique de _tryRepayLoan, qui arrondit aussi vers le haut pour ne pas passer sous son
 * plancher. Pose GL seulement sur un tirage reel : GL|year|drew|newLoan|ok (ok=1 si le solde
 * couvre need). Pire nom GL|1999|9999999|9999999|0 = 26 caracteres. */
function OpexTryReborrow(need, money)
{
  local loan = AICompany.GetLoanAmount();
  local maxLoan = AICompany.GetMaxLoanAmount();
  if (loan >= maxLoan) return money;
  local interval = AICompany.GetLoanInterval();
  if (interval <= 0) return money;

  local gap = need - money;
  if (gap <= 0) return money;
  local target = loan + gap;
  if (target > maxLoan) target = maxLoan;
  local newLoan = ((target + interval - 1) / interval) * interval;
  if (newLoan > maxLoan) newLoan = (maxLoan / interval) * interval;
  if (newLoan <= loan) return money;

  AICompany.SetLoanAmount(newLoan);
  local after = AICompany.GetBankBalance(AICompany.COMPANY_SELF);
  local drew = after - money;
  if (drew <= 0) return after;
  local covered = after >= need ? 1 : 0;
  OpexSign(AIMap.GetTileIndex(1, 1),
           "GL|" + AIDate.GetYear(AIDate.GetCurrentDate()) + "|" + drew + "|" + newLoan
                 + "|" + covered);
  return after;
}

/* Remboursement annuel : une fois la tresorerie confortablement au-dessus du plancher, on
 * rembourse le maximum d'emprunt qui laisse encore ce plancher disponible pour l'annee
 * suivante. SetLoanAmount exige un multiple de GetLoanInterval() ; on arrondit donc le nouvel
 * emprunt VERS LE HAUT (jamais vers le bas, ce qui rembourserait plus que permis et pourrait
 * passer sous le plancher). Le reemprunt a la demande (OpexTryReborrow, derriere reborrow)
 * est le pendant : sans lui ce remboursement est a sens unique. */
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

/* Event moteur exact : CRASH_TRAIN est emis dans train_cmd.cpp au moment ou deux trains
 * entrent en collision. XC garde la ligne, le vehicule, la tuile et les victimes ; RX reste le
 * filet annuel pour toute disparition sans evenement reconnu. */
function OpexAI::_processEvents()
{
  while (AIEventController.IsEventWaiting()) {
    local event = AIEventController.GetNextEvent();
    if (event == null || event.GetEventType() != AIEvent.ET_VEHICLE_CRASHED) continue;
    local crash = AIEventVehicleCrashed.Convert(event);
    if (crash == null || crash.GetCrashReason() != AIEventVehicleCrashed.CRASH_TRAIN) continue;

    local vehicle = crash.GetVehicleID();
    local lineId = -1;
    foreach (line in this._lines) {
      if (!("vehicles" in line)) continue;
      foreach (known in line.vehicles) {
        if (known == vehicle) { lineId = line.lineId; break; }
      }
      if (lineId >= 0) break;
    }
    local site = crash.GetCrashSite();
    OpexSign(AIMap.GetTileIndex(1, 1), "XC|" + (AIDate.GetYear(AIDate.GetCurrentDate()) % 100)
             + "|" + lineId + "|" + vehicle + "|" + AIMap.GetTileX(site) + "|"
             + AIMap.GetTileY(site) + "|" + crash.GetVictims());
  }
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
  JOIN_MAX_DISTANCE = AIController.GetSetting("join_max_distance");
  JOIN_PLACE = AIController.GetSetting("join_place") != 0;
  ORIGIN_SITABLE = AIController.GetSetting("origin_sitable") != 0;
  BASIN_SHARE = AIController.GetSetting("basin_share") != 0;
  REBORROW = AIController.GetSetting("reborrow") != 0;
  /* Lu ici comme les autres reglages de decision : catalog.refresh le consulte des le premier
   * cycle annuel, qui a lieu apres Start(). */
  ROAD_BUILD_ENABLED = AIController.GetSetting("road_mode") != 0;
  local roadPaxCatchment = AIController.GetSetting("road_pax_catchment_pct");
  if (roadPaxCatchment > 0) ROAD_PAX_CATCHMENT_SHARE_PCT = roadPaxCatchment;
  ROAD_REFLEET = AIController.GetSetting("road_refleet") != 0;
  ROAD_MULTISTOP = AIController.GetSetting("road_multistop") != 0;
  ASTAR_COST_V2 = AIController.GetSetting("astar_cost") != 0;
  PROBE_NEGATIVE = AIController.GetSetting("probe_negative") != 0;
  PAX_NEAR = AIController.GetSetting("pax_near") != 0;

  /* 🔴 RENOUVELLEMENT AUTOMATIQUE (2026-08-29). Mesure : campagne 20 ans, graine 42 -- trois des
   * quatre lignes ROUTIERES finissent la partie avec vehCount = 0 et un profit de zero, alors que
   * leurs gares gardent une note de 48 a 60 et que l'industrie source produit toujours. Elles ne
   * sont pas mortes economiquement : leurs vehicules ont atteint l'age maximal et ont disparu, et
   * rien dans le code n'en rebatit. Un camion vit ~12 ans quand une locomotive en vit 20 a 30 --
   * d'ou un mode d'echec qui ne se voyait pas tant que l'IA ne roulait qu'en rail sur 20 ans, mais
   * qui amputait la ligne routiere du tiers de sa vie utile.
   *
   * ⚠️ Ce reglage vaut pour TOUTE la compagnie, rail compris : ce n'est donc PAS un morceau du mode
   * route, et il ne doit pas etre attribue a lui au banc. Les mois negatifs veulent dire "avant"
   * l'age maximal ; -6 laisse au vehicule le temps de rejoindre le depot de sa ligne. Le plancher
   * de tresorerie reprend CASH_RESERVE, pour que le renouvellement ne puisse pas vider la caisse
   * que la construction protege. */
  AICompany.SetAutoRenewStatus(true);
  AICompany.SetAutoRenewMonths(-6);
  AICompany.SetAutoRenewMoney(CASH_RESERVE);

  /* L'emprunt maximal des le depart : la note de compagnie recompense l'emprunt a zero (5 %),
   * mais une ligne non construite faute de tresorerie coute bien davantage. Le remboursement
   * viendra quand la tresorerie le permettra. */
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());

  local lastYear = -1;
  while (true) {
    this._processEvents();
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
          this._scrapDeadLines(missedYear);
          this._refleetRoadLines(missedYear);
          this._tryRepayLoan(missedYear);
        }
      }
      lastYear = year;
      this._catalog.refresh(this._budget, year);
      local ranked = OpexBuildCandidates(this._catalog, this._budget, this._lines);
      this._reportYear(year, ranked);
      this._reportLines(year);
      this._scrapDeadLines(year);
      this._refleetRoadLines(year);
      this._tryBuildAir(year);
      this._tryBuildWater(year);
      local buildStartTick = AIController.GetTick();
      this._tryBuild(ranked, year);
      local tryBuildTicks = AIController.GetTick() - buildStartTick;
      /* Item 7 : APRES le classement, AVANT la route. Le cash restant est celui que le
       * TOP_K n'a pas voulu ; la route ne le dispute pas encore. Hors YT : a 0, un seul
       * test, et la duree _tryBuild reste comparable aux campagnes anterieures. */
      if (PROBE_NEGATIVE) this._tryProbeNegative(ranked, year);
      /* APRES le rail, et delibere : cf. le commentaire en tete de _tryBuildRoads. YT continue de
       * ne mesurer que _tryBuild, pour que la duree du cycle rail reste comparable aux campagnes
       * anterieures ; le cout de la phase routiere se lit sur ses propres panneaux RB. */
      this._tryBuildRoads(year);
      this._tryRepayLoan(year);
      local blockEndTick = AIController.GetTick();
      local anchor = AIMap.GetTileIndex(1, 1);
      local skippedMarker = skippedYears > 0 ? skippedYears + "C" : "0";
      OpexSign(anchor, "YT|" + (year % 100) + "|" + blockStartTick + "|" + blockEndTick
                               + "|" + tryBuildTicks + "|" + skippedMarker);
    }

    AIController.Sleep(74 * 10);
  }
}
