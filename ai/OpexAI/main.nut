/* OpexAI -- une IA qui traite les opcodes comme une ressource de jeu.
 *
 * Principe directeur : le budget du VM (10 000 opcodes par tick) n'est pas un stock qu'on
 * economise mais un DEBIT non reportable. La seule decision est donc l'ALLOCATION : a quel
 * candidat va le prochain tick de calcul. Ordre des objectifs, explicite et stable :
 *   1. maximiser le profit attendu par opcode ;
 *   2. maximiser la performance de compagnie ;
 *   3. maximiser les notes ;
 *   4. maximiser la valeur de compagnie.
 * Un objectif inferieur ne justifie jamais de sacrifier un objectif superieur.
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

require("globals_pre.nut");

const RAIL_EXPAND_STREAK = 2;
const RAIL_EXPAND_UTIL_PERMILLE = 850;
const RAIL_EXPAND_TIMEOUT_DAYS = 120;
/* Meme enveloppe locale que les signaux d'approche rail
 * (builder_rail.nut::OpexPlacePathApproachSignal, maxDistance=8). L'expansion ne deroute donc
 * une rame vers le depot qu'une fois entree dans cette zone locale. */
const RAIL_EXPAND_APPROACH_TILES = 8;

const CASH_RESERVE_STATIC = 25000;
const CASH_RESERVE_MIN = 5000;
const CASH_RESERVE_MAX = 25000;

require("budget.nut");
require("catalog.nut");
require("economy.nut");
require("spatial.nut");
require("candidates.nut");
require("tension.nut");
require("projects.nut");
require("builder_rail.nut");
require("builder_air.nut");
require("builder_water.nut");
require("builder_road.nut");
require("globals_post.nut");

/* Filet physique : deux gares reellement posees trop pres l'une de l'autre partagent leur bassin
 * de desserte, MEME si ce sont deux villes/industries differentes. Un rayon de couverture de gare
 * "petite" standard est ~4 tuiles ; MIN_SEPARATION couvre le double (dos-a-dos) plus une marge.
 * Abaisse de 15 a 10 le 2026-08-28 : mesure sur graine 42/20 ans, 84 % des rejets _tooClose
 * etaient a distance <5 de la MEME origine deja servie (couverts desormais par ORIGIN_SEPARATION
 * ci-dessous, avec precision, pas par ce filet) ; les 16 % restants, a distance 5-14, rejetaient
 * une ville VOISINE mais DIFFERENTE -- un faux positif du au seuil de 15, bien au-dela de tout
 * recouvrement de bassin plausible. Voir results/opex_full_campaign_20y.json (signs GT/GN). */
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

/* Marge laissee au moteur pour ne pas suspendre au milieu d'une transaction, et plafond de taches
 * par tick pour qu'un tour de file entierement compose de taches hors periode ne brule pas le
 * budget en pur ordonnancement. */
const LOOP_BUDGET_FLOOR = 2000;
const LOOP_BUDGET_MAX_TASKS = 8;

const DYNAMIC_BATCH_OPS_FLOOR = 2500;
/* Gain absolu minimal avant de rejouer la generation : en dessous, le cout en opcodes ne vaut pas
 * la peine d'etre paye pour quelques milliers de livres. */
const PORTFOLIO_REFRESH_MIN_GAIN = 50000;

/* Ligne fret morte (2026-08-28) : une industrie source qui ferme NE garantit PAS l'effondrement --
 * la gare peut recuperer une industrie voisine du meme cargo (ligne 4, campagne 20 ans, restee
 * rentable malgre srcAlive=0). Le diagnostic se fie donc TOUJOURS a la performance REELLE
 * (note de gare et revenu implicite), jamais a srcAlive seul, ET exige DEUX annees CONSECUTIVES
 * de confirmation pour exclure un accroc transitoire -- cf. OpexAI::_reportLines. */
const DEAD_STREAK_THRESHOLD = 2;
/* Duree maximale de la phase de ferraillage. Au-dela, la ligne est retiree meme s'il reste des
 * vehicules injoignables : mieux vaut abandonner quelques camions que garder a vie une ligne qui
 * paie son exploitation et bloque ses origines pour de nouveaux candidats. Deux ans laissent
 * largement le temps a un vehicule sain de rejoindre son depot. */
const SCRAP_TIMEOUT_YEARS = 2;

class OpexAI extends AIController {
  _budget = null;
  _catalog = null;
  _startTick = 0;
  _lines = null;        // [{stationA, stationB, cargo, predicted, iterations, trains, lineId, ...
                         //   deadStreak, scrapping, scrapVehicles (fret uniquement, cf.
                         //   _reportLines / _scrapDeadLines)}]
  /* Lignes brutes de Save : aucune lecture du monde dans Load(), la reconciliation attend Start(). */
  _pendingLines = null;
  /* Paires qui ont rendu ABND : table indexee par cle chaine, donc test O(1), et volontairement
   * petite (quelques abandons par partie) plutot qu'un historique de toutes les tentatives. */
  _abandonedPairs = null;
  _abandonCounts = null;
  _airBuilt = false;
  _waterBuilt = false;
  /* Ordonnanceur permanent : une tache utile et due par tour de file. dueCycle reporte le
   * travail inutile a un tour futur ; le calendrier du jeu ne reordonne jamais la file. */
  _taskQueue = null;
  _taskCursor = 0;
  _taskCycle = 0;
  _ranked = null;
  _projects = null;
  _generationStage = 0;
  _generationStageMonth = -1;
  _lastFreightCargo = -1;
  _bootstrapFreightCargo = -1;
  _loadedFromSave = false;
  _recomputeEpochBounds = false;
  /* Transaction asynchrone d'expansion rail : le train roule vers son depot pendant que la
   * boucle principale continue par pas de dix jours. Jamais de Sleep bloquant dans la tache. */
  _railExpansion = null;
  /* Recherche A* ferroviaire reprise d'un tour de file a l'autre (docs/taches.md A4). Meme
   * patron que _railExpansion : l'etat vit ici, il est repris en TETE de _runNextTask, et on
   * termine en remettant _railSearch = null. Le pathfinder lui-meme est dans state.pathfinder. */
  _railSearch = null;
  /* C38 : etat transitoire d'un batch dynamique, necessaire si un A* rail rend la main. */
  _dynamicBatch = null;
  /* C80 : orchestrateur à double registre (intentions réactives et registre d'exécution). */
  _reactiveQueue = null;
  _activeWorker = null;
  _c76LastReconcileMonth = -1;
  /* 11.6 : _railSearch contient un pathfinder vivant et _dynamicBatch reference _projects.
   * Ils ne sont pas serialises ; Save/Load ne conserve que leur presence pour forcer une
   * reconstruction propre du portefeuille apres reload. */
  _reloadDroppedRailSearch = false;
  _reloadDroppedDynamicBatch = false;
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
  _lastCatalogMonth = -1;
  _lastReportYear = -1;
  _c55PaxLastYear = -1;
  _c55PaxLastFlushedYear = -1;
  /* C43/E3 famille 2 : dernier compte cumulatif publie, pour ne journaliser que le delta annuel. */
  _cashReserveProbeLastCalls = 0;
  _cashReserveProbeLastMinBinds = 0;
  _cashReserveProbeLastMaxBinds = 0;
  _portfolioRefreshProbeLastChecks = 0;
  _portfolioRefreshProbeLastGainOk = 0;
  _portfolioRefreshProbeLastDoubleOk = 0;
  _portfolioRefreshProbeLastDoubleOnly = 0;
  _portfolioRefreshProbeLastRefreshOps = 0;
  _portfolioRefreshProbeLastRefreshCount = 0;
  _lastRepayMonth = -1;
  /* G2 : une ouverture d'industrie ou fondation de ville rend le catalogue ET le
   * portefeuille derive perimes. dueCycle = 0 ne suffit pas : catalog peut deja
   * avoir tourne ce mois-ci et sortir par son garde de cadence. */
  _portfolioInvalidated = false;
  /* C39.0 : etat plat, coalescable et serialisable de ce qui est devenu stale.
   * Il est strictement observatoire dans cette tranche : `_runNextTask` ne le lit
   * jamais pour choisir ou eviter un travail. */
  _staleness = null;
  _c41SlackLedger = null;
  _c41MonthlyBusyLedger = null;
  _c41MonthlyBusyMonth = -1;
  _c41OpportunityLedger = null;
  _c41AdmissionLedger = null;
  /* C41.46 : accumulateur unique (pas par categorie) -- separe la tranche A* nette de la tache de
   * file executee dans la meme passe de _runNextTask. Les trois champs _c41RailSliceLast* sont un
   * scratch REMIS A -1/0 a chaque passe, lu par le wrapper juste apres _runNextTask(). */
  _c41RailSliceLedger = null;
  _c41RailSliceLastOps = -1;
  _c41RailSliceLastIterDelta = 0;
  _c41RailSliceLastDone = false;
  _c41LastTaskName = "idle";
  /* C39.6 : scratch de la SEULE tranche A* pour la passe courante -- meme patron que
   * _c41RailSliceLast* : sentinelle -1 = aucune tranche cette passe, remise a chaque entree dans
   * _runNextTask, lue par _runNextTaskWithSlackLedger juste apres son retour. Independant des
   * champs _c41RailSliceLast* ci-dessus (reglages differents, duree de vie identique). */
  _c39PassClockSliceDays = -1;
  _c39PassClockSliceTicks = -1;
  _c39PassClockSliceOps = -1;
  /* C39.6 : accumulateur annuel, cle = "<nom de tache>|slice" ou "<nom de tache>|noslice". */
  _c39PassClockLedger = null;
  /* C48 : deux accumulateurs annuels distincts : une ligne par tentative et la vue par passe. */
  _c49ScarcityLedger = null;
  _c49ScarcityRegime = "cash";
  /* C50 : cache mensuel des refus de tresorerie et memoire du dernier mois de releve tresorerie. */
  _c50RefuseCache = null;
  _c50LastTreasuryMonth = null;
  _c39CadenceLastDate = null;
  _c39CadenceLastTick = null;
  _c39CadenceLastCycle = null;
  _c39FinanceableSince = null;
  _startYear = -1;
  /* Dates C69/C75 lues dans la sauvegarde, restaurees par _reconcileAfterLoad(). */
  _reloadC69BuildDates = null;
  _reloadC75PassDates = null;
  /* Retraites C52 unitaires, consommees par la tache de rebut dediee. */
  _vehiclesToRetire = null;
  /* C52 #4 : suivi des annees consecutives de deficit par vehicule */
  _unprofitableStreaks = null;
  /* C41.8 : ensemble coalescé par ligne, consommé par une seule micro-tâche. */
  _c41RailSignalLines = null;
  /* C41.10 : même schéma, réparation de raccord au lieu de pose PBS. */
  _c41RailJunctionLines = null;
  /* G4§1 : drapeau pose par _markPairAbandoned dans _tryBuildProjects, lu en fin de passe
   * pour declencher la reelection incrementale sans dependre de DECISION_LOG. */
  _hadAbandonsThisPass = false;
  /* Consommés par _c63RecordPassAndProbe : sonde empty_probe à la transition
   * non-vide→vide ou une fois par mois, pas à chaque passe vide. */
  _lastBestCount = -1;
  _lastEmptyProbeMonth = -1;

  constructor()
  {
    this._lastBestCount = -1;
    this._lastEmptyProbeMonth = -1;
    this._budget = OpexBudget();
    this._catalog = OpexCatalog();
    this._lines = [];
    this._pendingLines = null;
    this._abandonedPairs = {};
    this._abandonCounts = {};
    this._vehiclesToRetire = {};
    this._unprofitableStreaks = {};
    OpexAirResetSiteCache();
    this._c41RailSignalLines = {};
    this._c41RailJunctionLines = {};
    this._staleness = {
      catalog = { cargos = false, towns = false, industries = false, rail = false,
                  road = false, air = false, water = false },
      candidates = { rail = false, road = false, air = false, water = false },
      portfolio = false, selection = false,
      reasons = {}, towns = {}, industries = {}, engines = {}, engineModes = {}, events = 0,
      topBefore = "none", topBeforeCaptured = false,
      revisions = {
        catalog = { cargos = 0, towns = 0, industries = 0, rail = 0, road = 0, air = 0, water = 0 },
        candidates = { rail = 0, road = 0, air = 0, water = 0 }, portfolio = 0, selection = 0,
      },
      acknowledged = {
        catalog = { cargos = 0, towns = 0, industries = 0, rail = 0, road = 0, air = 0, water = 0 },
        candidates = { rail = 0, road = 0, air = 0, water = 0 }, portfolio = 0, selection = 0,
      },
      /* C41.3a : horodatage du premier salissement coalescé de catalog.water. Les revisions
       * restent l'autorite ; ces deux scalaires ne servent qu'a mesurer sa fraicheur. */
      waterCatalogDirtyDate = -1, waterCatalogDirtyTick = -1,
      dirtySince = {
        catalog = { cargos = -1, towns = -1, industries = -1, rail = -1, road = -1, air = -1, water = -1 },
        candidates = { rail = -1, road = -1, air = -1, water = -1 }, portfolio = -1, selection = -1,
      },
    };
    this._c41SlackLedger = {};
    this._c41OpportunityLedger = {};
    this._c41AdmissionLedger = {};
    this._c39PassClockLedger = {};
    this._c39CadenceLastDate = -1;
    this._c39CadenceLastTick = -1;
    this._c39CadenceLastCycle = -1;
    this._c39FinanceableSince = {};
    this._generationStage = 0;
    this._generationStageMonth = -1;
    this._lastFreightCargo = -1;
    this._bootstrapFreightCargo = -1;
    this._loadedFromSave = false;
    this._recomputeEpochBounds = false;
    this._reactiveQueue = OpexReactiveQueue();
    this._activeWorker = null;
    this._c76LastReconcileMonth = -1;
    /* Priorite : donnees et stop-loss, croissance des flottes existantes avant nouveaux projets,
     * portefeuille multimodal ROI, croissance urbaine, dette. */
    this._taskQueue = [
      { name = "catalog", dueCycle = 0, enabled = true },
      /* Slots historiques conserves pour la compatibilite du taskCursor numerique des sauvegardes.
       * Ils restent toujours desactives et n'ont plus de dispatcher. */
      { name = "c41_water", dueCycle = 2147483647, enabled = false },
      { name = "c41_road", dueCycle = 2147483647, enabled = false },
      /* C41.8 : ne travaille qu'une ligne rail explicitement signalée par VehicleLost. */
      { name = "c41_rail_signals", dueCycle = 2147483647, enabled = false },
      /* C41.10 : idem, réparation de raccord au lieu de pose PBS. */
      { name = "c41_rail_junction", dueCycle = 2147483647, enabled = false },
      { name = "report", dueCycle = 0, enabled = true },
      { name = "scrap", dueCycle = 0, enabled = true },
      /* fleet_before_new : la croissance de flotte passe AVANT la construction de lignes neuves.
       * La note de gare est un multiplicateur, pas un bonus (docs/mecanique_jeu.md S3 : 51 % de la
       * note vient du delai depuis le dernier ramassage) : une ligne mal servie effondre sa note et
       * degrade tout ce qu'elle touche. On regle donc l'existant avant d'ajouter une liaison.
       *
       * Ce n'est pas un arbitrage, c'est un ORDRE DE SERVICE, et la mesure dit pourquoi : la
       * croissance de flotte aerienne est refusee 31 fois sur 32 pour TRESORERIE, jamais pour le
       * plafond de l'aeroport -- 1,6 avion par ligne pour un plafond de 16 (docs/taches.md
       * S0 quinvicies). Quand `air` passe en premier, il ne reste rien pour `air_fleet`.
       *
       * ⚠️ L'echange N'A PAS LIEU ICI : ce constructeur s'execute AVANT Start(), donc avant la
       * lecture des reglages, et FLEET_BEFORE_NEW y vaut encore son repli. La file est batie dans
       * l'ordre historique et echangee dans Start(), une fois le reglage connu.
       *
       * L'ordre historique reste joignable par le reglage a 0 pour que le banc puisse trancher. */
      { name = "air", dueCycle = 0, enabled = true },
      { name = "air_fleet", dueCycle = 0, enabled = true },
      { name = "projects", dueCycle = 0, enabled = true },
      { name = "expand", dueCycle = 0, enabled = true },
      { name = "refleet", dueCycle = 0, enabled = true },
      { name = "town_growth", dueCycle = 0, enabled = true },
      { name = "repay", dueCycle = 0, enabled = true },
    ];
  }

  function Start();
  function _tooClose(candidate);
  function _tryBuildAir(year);
  function _tryBuildProjects(year);
  function _c39StampFinanceable(capital = null, isProjectsTurn = false);
  function _tryTownGrowth(year);
  function _runNextTask();
  function _runNextTaskWithSlackLedger();
  function _logC41SlackLedger(year);
  function _recordC41StaleOpportunity(slackLeft);
  function _logC41OpportunityLedger(year);
  function _logC41AdmissionLedger(year);
  function _recordC41RailSliceLedger(netOps, taskOps, iterDelta, done);
  function _logC41RailSliceLedger(year);
  function _recordC39PassClockLedger(key, days, ticks, ops, sliceDays, sliceTicks, sliceOps);
  function _logC39PassClockLedger(year);
  function _recordC49ScarcityPass(best, builtRanks, attemptedRanks, passDiscards);
  function _logC49ScarcityLedger(year);
  function _logC54VehicleOrders(year);
  function _logC48IncrementalLedger(year);
  function _recordC69BuildingPass(year, projects, builtProjects);
  function _reportYear(year, ranked);
  function _reportLines(year);
  function _scrapDeadLines(year);
  function _scrapRetiredVehicles(year);
  function _purgeUnprofitableStreaks();
  function _triggerScrapLine(line, criterion);
  function _refleetRoadLines(year);
  function _refleetCrashedWaterLines(year);
  function _resizeAirFleets(year);
  function _expandRailLines(year);
  function _continueRailExpansion();
  function _startRailSearch(candidate, alternativeRatio, hardCap, projectIndex);
  function _continueRailSearch();
  function _consumeRailSearch(year);
  function _recordRailAttempt(candidate, result, posPacked, year);
  function _startRailUpgradeSearch(line, prep);
  function _consumeRailUpgrade();
  function _findLineById(lineId);
  function _processEvents();
  function _markDirty(reason, catalogLayers = null, candidateLayers = null,
                      portfolio = false, selection = false, affectedKind = null, affectedId = -1,
                      affectedMode = null, targetedRelevant = true);
  function _logStalenessRefresh(reason);
  function _markPairAbandoned(key);
  function _padAirFailedSites(plan, result);
  function _pruneAbandonedPairs(now);
  function _onVehicleCrashed(event);
  function _onVehicleAutoreplaced(event);
  function _onVehicleUnprofitable(event);
  function _onIndustryClose(event);
  function _onVehicleLost(event);
  function _onIndustryOpen(event);
  function _onTownFounded(event);
  function _onEngineAvailable(event);
  function _onStationFirstVehicle(event);
  function _dispatchCatalog(task, year);
  function _dispatchC41RailSignals(task, year);
  function _dispatchC41RailJunction(task, year);
  function _dispatchReport(task, year);
  function _dispatchScrap(task, year);
  function _dispatchAir(task, year);
  function _dispatchAirFleet(task, year);
  function _dispatchProjects(task, year);
  function _dispatchExpand(task, year);
  function _dispatchRefleet(task, year);
  function _dispatchTownGrowth(task, year);
  function _dispatchRepay(task, year);
  function _c76RecordRegen(kind, ops, days, year);
  function _runOrchestratorTick();
  function _runBackgroundQueue();
  function _enqueueReactive(key, kind, payload);
  function _popReactive();
  function _hasReactiveIntentions();
  function _clearReactiveQueue();
  function _dispatchReactiveIntention(intention);
  function _c80RunSelfTest();
  function _c76EnqueueRegen(modes, entityKind = null, entityId = -1, targeted = false,
                             buildAfter = false, reason = "event");
  function _c76RefreshModeCatalog(mode);
  function _c76AcknowledgeMode(mode);
  function _c76PeriodicReconcile(yearMonth);
  function enqueue(key, kind, payload);
  function pop();
}

/* C65 : modules extraits de main.nut, requis APRES la classe OpexAI. */
require("capital.nut");
require("events.nut");
require("event_handlers.nut");
require("ledgers.nut");
require("lines.nut");
require("orchestrator.nut");
require("persist.nut");
require("probes.nut");
require("scheduler.nut");
require("scheduler_tasks.nut");
require("settings.nut");
require("task_air.nut");
require("task_projects.nut");
require("task_rail.nut");
require("task_report.nut");
require("task_road.nut");
require("task_town.nut");
require("task_water.nut");

function OpexAI::Start()
{
  AICompany.SetName("OpexAI");
  this._startTick = AIController.GetTick();

  OpexLoadSettings();

  if (!STAGED_BOOTSTRAP) this._generationStage = OPEX_STAGE_COMPLETE;

  /* La file a ete batie par le constructeur, avant que ce reglage ne soit lisible : c'est donc
   * ici, et seulement ici, que l'ordre de service peut etre echange. */
  if (FLEET_BEFORE_NEW) {
    for (local i = 0; i < this._taskQueue.len() - 1; i++) {
      if (this._taskQueue[i].name == "air" && this._taskQueue[i + 1].name == "air_fleet") {
        local swap = this._taskQueue[i];
        this._taskQueue[i] = this._taskQueue[i + 1];
        this._taskQueue[i + 1] = swap;
        break;
      }
    }
  }
  if (TENSION_PROBE) OpexTensionEnable(this._budget);
  if (C49_SCARCITY_LEDGER) {
    this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
        decision_attempted = 0, decision_unattempted = 0, none = 0 };
    this._c49ScarcityRegime = "cash";
  }
  if (C50_CHRONOLOGY_PROBE) {
    this._c50RefuseCache = {};
    this._c50LastTreasuryMonth = -1;
  }
  if (C69_TRACK_BUILDS) {
    C69_BUILD_DATES = [];
    C69_PENDING_FOLLOWUPS = [];
    C69_BUILD_PASS_COUNT = 0;
    C69_LAST_AFFORDABLE = null;
    C69_LAST_KDEC_DATA = null;
    C69_CACHED_KDEC_DATE = -1;
    C69_CACHED_KDEC_VALUE = 0;
    C69_PLANE_CHOICE_CALLS = 0;
    C69_PLANE_CHOICE_DIFFER_ROI = 0;
    C69_PLANE_CHOICE_DIFFER_C69 = 0;
  }
  if (C75_TRACK_PASSES) {
    C75_PASS_DATES = [];
    OpexC75ResetYearLedger();
  }
  if (WATER_OPCODE_COMPAT_FALSE && this._taskQueue != null) {
    /* Branche de compatibilite volontairement vide : l'ancien flag etait force false. */
  }
  if (this._loadedFromSave) this._reconcileAfterLoad();
  if (DECISION_LOG) {
    OpexDecide("SETTINGS", "road_pax_build=" + ROAD_PAX_BUILD_ENABLED
               + " road_pax_voirie=" + ROAD_PAX_VOIRIE
               + " road_pax_overlap=" + ROAD_PAX_OVERLAP);
  }
  OpexAirResetSiteCache();

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
  AICompany.SetAutoRenewMoney(OpexCashReserve());

  /* L'emprunt maximal des le depart : la note de compagnie recompense l'emprunt a zero (5 %),
   * mais une ligne non construite faute de tresorerie coute bien davantage. Le remboursement
   * viendra quand la tresorerie le permettra. */
  if (!this._loadedFromSave || this._startYear < 0) {
    /* Une sauvegarde porte son annee de debut : ne pas remettre yearsElapsed a zero au reload. */
    this._startYear = AIDate.GetYear(AIDate.GetCurrentDate());
  }
  OPEX_START_YEAR = this._startYear;
  if (!this._loadedFromSave) {
    /* Le reload reprend la dette effectivement choisie : ne pas reemprunter sans decision. */
    AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=initial_borrow amount=" + AICompany.GetLoanAmount() + " max_loan=" + AICompany.GetMaxLoanAmount());
    }
  }

  if (C80_DOUBLE_REGISTER) {
    this._c80RunSelfTest();
  }

  while (true) {
    if (C56_TASK_TRACE) {
      /* C56 : une trace tous les 200 tours pour ne pas noyer le journal. */
      C56_LOOP_TICK_COUNT++;
      if (C56_LOOP_TICK_COUNT % 200 == 0) {
        OpexC56TaskLog("LOOP_TICK", "-", this._taskCycle);
      }
    }
    this._processEvents();
    if (C80_DOUBLE_REGISTER) {
      this._runOrchestratorTick();
      AIController.Sleep(1);
    } else if (LOOP_BUDGET) {
      /* Le budget d'un tick n'est PAS reportable : ce qui n'est pas depense est perdu. L'ancienne
       * boucle executait exactement UNE tache puis rendait la main, donc un tick qui tirait une
       * tache hors de sa periode (catalog hors de son mois, report hors de son annee, repay hors
       * du sien) depensait quelques centaines d'opcodes et jetait les ~9 700 restants.
       * On draine desormais le tick tant qu'il reste de quoi travailler. */
      local drained = 0;
      while (AIController.GetOpsTillSuspend() > LOOP_BUDGET_FLOOR && drained < LOOP_BUDGET_MAX_TASKS) {
        if (!this._runNextTaskWithSlackLedger()) break;
        drained++;
      }
      /* Le plancher garde de la marge pour ne pas etre suspendu au milieu d'une transaction, et
       * le plafond de taches empeche un tour de file entierement compose de taches inutiles de
       * bruler le budget en pur ordonnancement. */
      if (drained == 0) this._runNextTaskWithSlackLedger();
      /* AUCUN Sleep ici, et c'est deliberé. Le Sleep de fin de tour rendait la main alors qu'il
       * restait du budget, ce qui est un auto-handicap face a une IA qui ne dort pas entre ses
       * chunks (docs/philosophie_armes_egales : les bridages servent aux parties avec des HUMAINS,
       * jamais entre IA). Le moteur nous suspend de lui-meme quand le budget du tick est epuise et
       * nous reprend au tick suivant exactement ou il nous avait laisses : la boucle reste donc
       * bornee, et la partie avance normalement. */
    } else {
      this._runNextTaskWithSlackLedger();
      AIController.Sleep(1);
    }
  }
}
