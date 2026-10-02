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
require("terrain_map.nut");
require("water_graph.nut");
require("candidates.nut");
require("tension.nut");
require("projects.nut");
require("pathfinder_v90/binary_heap.nut");
require("pathfinder_v90/aystar.nut");
require("pathfinder_v90/rail.nut");
require("builder_rail.nut");
require("builder_air.nut");
require("builder_water.nut");
require("builder_road.nut");
require("opcode_exact.nut");
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

/* V88 : Hypothese de conversion intrants -> biens pour une usine de transformation (Factory).
 * En climat tempere avec un seul intrant actif (cereales, betail ou acier), chaque unite
 * d'intrant livree produit environ une unite de biens (ratio de transformation standard = 1.0). */
const OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT = 1.0;

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
  /* V88 : etat de la chaine industrielle de biens en cours (etape 2 en attente de fonds/recherche) */
  _activeGoodsChain = null;
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
  _saveProjection = null;       // {line -> copie serialisable}, voir _refreshSaveProjection
  _saveProjectionMonth = -1;
  _recomputeEpochBounds = false;
  /* Transaction asynchrone d'expansion rail : le train roule vers son depot pendant que la
   * boucle principale continue par pas de dix jours. Jamais de Sleep bloquant dans la tache. */
  _railExpansion = null;
  /* Recherche A* ferroviaire reprise d'un tour de file a l'autre (docs/taches.md A4). Meme
   * patron que _railExpansion : l'etat vit ici, il est repris en TETE de _runNextTask, et on
   * termine en remettant _railSearch = null. Le pathfinder lui-meme est dans state.pathfinder. */
  _railSearch = null;
  /* C80 : orchestrateur à double registre (intentions réactives et registre d'exécution). */
  _reactiveQueue = null;
  _activeWorker = null;
  _railWorkerSteppedThisTick = false;
  /* C80 étape 1 : table des tracés rail prêts validés par les workers, indexée par pairKey.
   * Transitoire / reconstructible : initialisée à {}, jamais persistée dans Save(). */
  _railReadyStock = null;
  /* C80 étape 2 : table des paires en retrait temporaire (cooldown), indexée par pairKey.
   * Transitoire / reconstructible : initialisée à {}, jamais persistée dans Save(). */
  _railStockCooldown = null;
  /* C121 preparation rail de l'annee AIR : liste de candidats et mois de generation.
   * Non sauvegardes. Reconstructibles au prochain passage projects si le reglage est arme.
   * MinAirCap : -1 = aucun plan AIR vivant au dernier scan (fin de passe). */
  _c121RailPrepCandidates = null;
  _c121RailPrepMonth = -1;
  _c121RailPrepHold = false;
  _c121RailPrepYieldLogged = false;
  _c121RailPrepMinAirCap = -1;
  /* C80 étape 2 : seuil de score grossier pour le worker rail (score du dernier projet financé
   * lors de la dernière sélection non vide). Mémoire transitoire, réinitialisée à 0 au chargement. */
  _railStockLastFundedScore = 0.0;
  _railStockLastFundedDate = -1;
  /* C67.4 : service de carte par blocs, reconstruit, jamais sauvegarde (task_terrain.nut). */
  _c67Terrain = null;
  _c67BgCursor = 0;
  _c67BgFresh = 0;
  _c67BgIdle = false;
  _c67LinesSeen = 0;
  _c67Ledger = null;
  _c67Year = -1;
  /* C67.6 : sonde passive d'exposition eau, jamais sauvegardee. */
  _c67Water = null;
  /* 11.6 : _railSearch contient un pathfinder vivant. Il n'est pas serialise ;
   * Save/Load conserve sa presence pour forcer une reconstruction propre du portefeuille. */
  _reloadDroppedRailSearch = false;
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
  /* V89 : débit de recherche A* rail opportuniste et instrumentation passive */
  _v89EstimatedSliceOps = 2000;
  _v89LastDay = -1;
  _v89YearIters = 0;
  _v89YearSlices = 0;
  _v89SearchDaysThisYear = 0;
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
  _townWorkerStats = null;
  /* V95 item 1 : pile de frames observatoires (selection de tache). Jamais sauvegardee. */
  _schedIdlePeekTask = null;
  _schedIdlePredReason = null;
  _schedIdlePredClass = null;
  _schedIdlePreVehCount = 0;
  _schedIdlePreLinesCount = 0;
  _schedIdlePreLoan = 0;
  _schedIdlePreRailSearch = null;
  _schedIdlePreActiveWorker = null;
  _schedIdlePreProjects = null;
  _schedIdlePreBestLen = 0;
  _schedIdlePreHadAbandons = false;
  _schedIdlePreC83Preempt = 0;
  _schedIdlePreC78Rebuild = null;
  _schedIdlePreDate = -1;
  _schedIdlePreTick = -1;
  _schedIdleLastWorkDate = null;
  _schedIdleLastWorkTick = null;
  _schedIdleProjectsLastDate = -1;
  _schedIdleProjectsLastTick = -1;
  _schedIdleSinceProjectsSel = 0;
  _schedIdleSinceProjectsWork = 0;
  /* P2 : observatoire du cycle de vie du portefeuille post-build (sous probe_scheduler). */
  _p2BuildSeq = 0;
  _p2PendingBuilds = null;
  _p2PreCapital = 0;
  _p2PreCandidateGroupsLen = 0;
  _p2CatalogPreReason = null;
  /* P2 bis : observatoire de reconciliation des passages projects (sous probe_scheduler). */
  _p2ProjectsSeq = 0;
  _p2TasksSinceProjects = null;
  _p2LastProjectsPostBest = -1;
  _p2LastProjectsPostCap = -1;
  /* P5 : observatoire pre-planification A* rail et reliquat d'attente (sous probe_scheduler). */
  _p5EpisodeActive = false;
  _p5EpisodeId = -1;
  _p5EpisodeUnusedOps = 0;
  _p5EpisodeUsedOps = 0;
  _p5EpisodeDispatches = 0;
  _p5RailSearchSeq = 0;
  _p5ActiveRailSearch = null;
  _p5LastTrackedRailSearch = null;
  _schedIdlePreMarkLeft = 10000;
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
  /* town_growth_plan_memo : townId -> nombre de maisons au moment du dernier echec de planification.
   * Non sauvegarde : apres chargement, chaque ville est simplement replanifiee une fois. */
  _townPlanFailures = null;
  /* Dates C69/C75 lues dans la sauvegarde, restaurees par _reconcileAfterLoad(). */
  _reloadC69BuildDates = null;
  _reloadC75PassDates = null;
  /* C83 preempt : lus dans la sauvegarde, appliques apres les reglages. */
  _reloadC83PreemptTown = null;
  _reloadC83PreemptStopped = null;
  _reloadC83PreemptQueued = null;
  _reloadC83PreemptRace = null;
  /* Retraites C52 unitaires, consommees par la tache de rebut dediee. */
  _vehiclesToRetire = null;
  /* C52 #4 : suivi des annees consecutives de deficit par vehicule */
  _unprofitableStreaks = null;
  /* C41.8 : ensemble coalescé par ligne, consommé par une seule micro-tâche. */
  _c41RailSignalLines = null;
  /* C41.10 : même schéma, réparation de raccord au lieu de pose PBS. */
  _c41RailJunctionLines = null;
  _activeSubsidies = null;
  /* G4§1 : drapeau pose par _markPairAbandoned dans _tryBuildProjects, lu en fin de passe
   * pour declencher la reelection incrementale sans dependre de DECISION_LOG. */
  _hadAbandonsThisPass = false;
  /* Consommés par _c63RecordPassAndProbe : sonde empty_probe à la transition
   * non-vide→vide ou une fois par mois, pas à chaque passe vide. */
  _lastBestCount = -1;
  _lastEmptyProbeMonth = -1;
  /* C76 étape 2 / C80 tranche 3 : révisions réelles du vivier pilotées par les invalidations */
  _c76Revisions = null;
  _c76AckRevisions = null;
  _c76ModeConsumed = null;
  _c76ModeConsumedRevision = null;
  _c76LastRegenQuarter = -1;
  _c76ForceReloadRegen = false;
  /* C83.1 : cache reconstructible townId -> etat slot/possession Opex. Non
   * serialise : apres Load, une ville deja menacee est simplement resondee.
   * _c83SlotRace : date du dernier enqueue reussi (c83_fixes). Meme regime. */
  _c83SlotWatch = null;
  _c83SlotRace = null;
  /* Horloge et mesures P4 reconstructibles, jamais serialisees. */
  _expC83WatchDaily = null;
  /* c83_preempt_open : date de rearm par ville, ville deja demandee, et
   * nombre d'enqueues de la passe. Non lus quand le reglage est a 0. */
  _c83PreemptRace = null;
  _c83PreemptQueued = -1;
  _c83PreemptEnqueued = 0;

  constructor()
  {
    this._lastBestCount = -1;
    this._lastEmptyProbeMonth = -1;
    this._c76Revisions = {
      towns = 0,
      industries = 0,
      lines = 0,
      engines = { rail = 0, road = 0, air = 0, water = 0 }
    };
    this._c76AckRevisions = {
      towns = 0,
      industries = 0,
      lines = 0,
      engines = { rail = 0, road = 0, air = 0, water = 0 }
    };
    this._c76ModeConsumed = {};
    this._c76ModeConsumedRevision = {};
    this._c76LastRegenQuarter = -1;
    this._c76ForceReloadRegen = false;
    this._c83SlotWatch = {};
    this._c83SlotRace = {};
    this._c83PreemptRace = {};
    this._c83PreemptQueued = -1;
    this._c83PreemptEnqueued = 0;
    this._budget = OpexBudget();
    this._catalog = OpexCatalog();
    this._lines = [];
    this._pendingLines = null;
    this._abandonedPairs = {};
    this._abandonCounts = {};
    this._vehiclesToRetire = {};
    this._unprofitableStreaks = {};
    OpexAirResetSiteCache();
    this._activeSubsidies = {};
    this._railReadyStock = {};
    this._railStockCooldown = {};
    this._railStockLastFundedScore = 0.0;
    this._railStockLastFundedDate = -1;
    this._c121RailPrepCandidates = null;
    this._c121RailPrepMonth = -1;
    this._c121RailPrepHold = false;
    this._c121RailPrepYieldLogged = false;
    this._c121RailPrepMinAirCap = -1;
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
    this._townWorkerStats = { slices = 0, opsMax = 0, opsTotal = 0, built = 0 };
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
      { name = "air", dueCycle = 0, enabled = true },
      { name = "air_fleet", dueCycle = 0, enabled = true },
      { name = "projects", dueCycle = 0, enabled = true },
      { name = "expand", dueCycle = 0, enabled = true },
      { name = "refleet", dueCycle = 0, enabled = true },
      { name = "town_growth", dueCycle = 0, enabled = true },
      { name = "repay", dueCycle = 0, enabled = true },
    ];
    this._activeGoodsChain = null;
  }

  function Start();
  function _tooClose(candidate);
  function _tryBuildGoodsChainStep2(year, passDiscards, anchor, yy);
  function _setActiveGoodsChain(chain);
  function _tryBuildAir(year);
  function _tryBuildProjects(year);
  function _c39StampFinanceable(capital = null, isProjectsTurn = false);
  function _tryTownGrowth(year);
  function _prepareTownGrowth();
  function _tryTownGrowthCity(townId, year, anchor = null);
  function _markTownGrowthRejected(townId);
  function _recordTownWorkerSlice(sliceOps, builtCount);
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
  function _schedIdleEnsure();
  function _schedIdlePreDispatch();
  function _schedIdlePostDispatch(taskName, ran, ops, days, ticks);
  function _p5OnRailSearchStart(kind, cand, budget);
  function _p5OnRailSearchEnd(state, outcome, result);
  function _recordC49ScarcityPass(best, builtRanks, attemptedRanks, passDiscards);
  function _logC49ScarcityLedger(year);
  function _logC54VehicleOrders(year);
  function _logC48IncrementalLedger(year);
  function _recordC69BuildingPass(year, projects, builtProjects);
  function _reportYear(year, ranked);
  function _reportLines(year);
  function _reportC78Candidates(year);
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
  function _purgeSubsidyFromProjects(subId);
  function _onVehicleCrashed(event);
  function _onVehicleAutoreplaced(event);
  function _onVehicleUnprofitable(event);
  function _onIndustryClose(event);
  function _onSubsidyOffer(event);
  function _onSubsidyOfferExpired(event);
  function _onSubsidyAwarded(event);
  function _onSubsidyExpired(event);
  function _onVehicleLost(event);
  function _onIndustryOpen(event);
  function _onTownFounded(event);
  function _onEngineAvailable(event);
  function _onStationFirstVehicle(event);
  function _c78SlotOnProjectsPass();
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
  function _c76RecordRegen(kind, ops, days, year, reason = "unknown");
  function _c76RecordAvoided(year);
  function _c76RotateFreight(year);
  function _c76BumpLayer(layer, isEvent = false);
  function _c76GetLayerRevision(layer);
  function _c76GetModeDeps(mode);
  function _c76ModeNeedsRegen(mode);
  function _c76AnyLayerChanged();
  function _c76AcknowledgeAllLayers();
  function _c76DoFullRegen(reason, year);
  function _c76PurgeInvalidCandidates(modeFilter = null);
  function _c80ModeRegenModes();
  function _c80DoModeRegen(modes, reason, year);
  function _c76SaveRevisions();
  function _c76LoadRevisions(data);
  function _c76RunSelfTest();
  function _runOrchestratorTick();
  function _c67TerrainInit();
  function _c67NoteNewLines();
  function _c67FeedBackground();
  function _c67LogYear();
  function _c67TerrainSlackStep();
  function _c67SlackHook();
  function _c67WaterLogYear();
  function _c67WaterNextQuery(job);
  function _c67WaterFinish(job, result, reason, cdist);
  function _c67WaterExposureStep();
  function _runBackgroundQueue();
  function _enqueueReactive(key, kind, payload);
  function _popReactive();
  function _hasReactiveIntentions();
  function _clearReactiveQueue();
  function _dispatchReactiveIntention(intention);
  function _c80RunSelfTest();
  function _advanceRailSearchSliceWithLedgers();
  function _c77EnqueueEntity(modes, entityKind = null, entityId = -1, buildAfter = false,
                             reason = "event");
  function _c77RefreshModeCatalog(mode);
  function _c77InjectSubsidy(subId);
  function _c77RemoveSubsidy(subId);
  function _c77RegenEntitySync(payload);
  function _c83WatchAirSlotTransitions();
  function _expC83PollAirSlots(source = "main");
  function enqueue(key, kind, payload);
  function pop();
  function _advanceRailSearchThroughput(maxSlices = -1);
  function _v89TrackSearchDays(now);
  function _logC89AnnualRail(year);
  function _updateRailStockSelectionThreshold();
  function _tryStartRailStockWorker();
  function _startRailStockSearch(candidate, isRepair = false, repairReason = null, coarseScore = null);
  function _handleRailStockSearchTimeout();
  function _handleRailStockSearchCompleted();
  function _checkRailStockExpiry();
  function _revalidateRailStockPlan(candidate, plan);
  function _c121CheapestLivingAirCap();
  function _c121RailPrepAirFundable();
  function _c121RailPrepAirFundableCheap();
  function _c121RailPrepCashBelowAir();
  function _c121RailSearchIsPrep();
  function _c121RailPrepTrigger();
  function _c121RailPrepRememberStock();
  function _c121RailPrepDropStock(candidate, reason, ops, ticks);
  function _c121RailPrepOnPassStart();
  function _c121RailPrepAfterProjectsPass();
  function _c121RailPrepMaybeCatalog();
  function _tryStartC121RailPrepSearch();
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
require("rail_prep_c121.nut");
require("task_report.nut");
require("task_road.nut");
require("task_terrain.nut");
require("task_town.nut");
require("task_water.nut");
require("selftests.nut");

function OpexAI::Start()
{
  AICompany.SetName("OpexAI");
  this._startTick = AIController.GetTick();

  OpexLoadSettings();

  if (!STAGED_BOOTSTRAP) this._generationStage = OPEX_STAGE_COMPLETE;

  if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {}
  if (TENSION_PROBE) OpexTensionEnable(this._budget);
  if (C49_SCARCITY_LEDGER) {
    this._c49ScarcityLedger = { passes = 0, cash = 0, vehicles = 0, site = 0,
        decision_attempted = 0, decision_unattempted = 0, none = 0,
        stop_k_pass = 0, stop_cash = 0, stop_rail_search = 0, stop_list_end = 0, stop_other = 0 };
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
  OpexExpC83ResetWatchDaily(this);
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
    local spLoan = PROBE_SPAN_TRACE ? OpexSpanBegin("start.loan") : null;
    AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
    if (DECISION_LOG) {
      OpexDecide("LOAN", "action=initial_borrow amount=" + AICompany.GetLoanAmount() + " max_loan=" + AICompany.GetMaxLoanAmount());
    }
    if (spLoan != null) OpexSpanEnd(spLoan);
  }

  local spSelf = PROBE_SPAN_TRACE ? OpexSpanBegin("start.selftest") : null;
  if (C80_DOUBLE_REGISTER) {
    this._c80RunSelfTest();
  }
  if (C76_REGEN_TARGETED) {
    this._c76RunSelfTest();
  }
  if (spSelf != null) OpexSpanEnd(spSelf);
  if (C80_RAIL_STOCK_GATE && C80_RAIL_STOCK_WORKER) {
    ::OpexPromoteLiveDefensiveAirBase <- ::OpexPromoteLiveDefensiveAir;
    ::OpexPromoteLiveDefensiveAir = ::OpexPromoteLiveDefensiveAirStock;
    this._tryStartRailStockWorker();
  }

  if (PROBE_LOOP_OPS && C80_DOUBLE_REGISTER) this._mainLoopProfiled();
  while (true) {
    if (PROBE_SPAN_TRACE) {
      OpexSpanRescueOrphans();
      OpexSpanYearRoll();
    }
    if (C56_TASK_TRACE) {
      /* C56 : une trace tous les 200 tours pour ne pas noyer le journal. */
      C56_LOOP_TICK_COUNT++;
      if (C56_LOOP_TICK_COUNT % 200 == 0) {
        OpexC56TaskLog("LOOP_TICK", "-", this._taskCycle);
      }
    }
    local spEvents = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.events") : null;
    this._processEvents();
    if (spEvents != null) OpexSpanEnd(spEvents);
    if (this._lines != null && this._lines.len() >= SAVE_PROJECTION_MIN_LINES) {
      local spSave = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.save_projection") : null;
      this._refreshSaveProjection();
      if (spSave != null) OpexSpanEnd(spSave);
    } else if (this._saveProjection != null) this._saveProjection = null;
    if (EXP_C83_WATCH_DAILY) {
      local spC83 = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.c83") : null;
      this._expC83PollAirSlots();
      if (spC83 != null) OpexSpanEnd(spC83);
    }
    if (C117_AIR_THROUGHPUT_PROBE || C121_AIR_ECONOMICS_SHADOW || C121_AIR_ECONOMICS) {
      local spC117 = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.c117") : null;
      OpexC117AirThroughputStep(this._lines, this._catalog);
      if (spC117 != null) OpexSpanEnd(spC117);
    }
    if (C56_TASK_TRACE) this._v89TrackSearchDays(AIDate.GetCurrentDate());
    if (C80_DOUBLE_REGISTER) {
      local spOrch = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.orch") : null;
      this._runOrchestratorTick();
      if (spOrch != null) OpexSpanEnd(spOrch);
      if (C121_CATALOG_INCREMENTAL) {
        local spResume = null;
        local catalogPending = true;
        local continuationTick = AIController.GetTick();
        while (catalogPending && OpexC121CatalogCanContinue(this, continuationTick)) {
          catalogPending = false;
          foreach (queuedTask in this._taskQueue) {
            if (queuedTask.name == "catalog" && ("c78AirRebuild" in queuedTask)
                && queuedTask.c78AirRebuild != null) {
              if (spResume == null && PROBE_SPAN_TRACE) spResume = OpexSpanBegin("loop.c121_catalog_resume");
              catalogPending = true;
              local spCat = PROBE_SPAN_TRACE ? OpexSpanBegin("task.catalog") : null;
              this._dispatchCatalog(queuedTask, AIDate.GetYear(AIDate.GetCurrentDate()));
              if (spCat != null) OpexSpanEnd(spCat);
              break;
            }
          }
          local spMid = (PROBE_SPAN_TRACE && catalogPending) ? OpexSpanBegin("loop.orch") : null;
          if (catalogPending) this._runOrchestratorTick();
          if (spMid != null) OpexSpanEnd(spMid);
        }
        if (spResume != null) OpexSpanEnd(spResume);
      }
      local spAstar = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.astar_v89") : null;
      if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();
      if (spAstar != null) OpexSpanEnd(spAstar);
      if (C67_SLACK_HOOK) {
        local spC67 = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.c67") : null;
        this._c67SlackHook();
        if (spC67 != null) OpexSpanEnd(spC67);
      }
      local spSleep = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.sleep") : null;
      AIController.Sleep(1);
      if (spSleep != null) OpexSpanEnd(spSleep);
    } else if (OPEX_ECONOMY_OPCODE_COMPAT_FALSE) {
    } else {
      local spLegacy = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.legacy") : null;
      this._runNextTaskWithSlackLedger();
      if (spLegacy != null) OpexSpanEnd(spLegacy);
      /* C121 : les tranches rendent la main aux taches dues dans la file, mais
       * ne doivent pas imposer un Sleep entre deux tranches lorsque le tick a
       * encore des opcodes. La file continue son tour normal a chaque appel. */
      if (C121_CATALOG_INCREMENTAL) {
        local spResumeLeg = null;
        local catalogPending = true;
        local continuationTick = AIController.GetTick();
        while (catalogPending && OpexC121CatalogCanContinue(this, continuationTick)) {
          catalogPending = false;
          foreach (queuedTask in this._taskQueue) {
            if (queuedTask.name == "catalog" && ("c78AirRebuild" in queuedTask)
                && queuedTask.c78AirRebuild != null) {
              if (spResumeLeg == null && PROBE_SPAN_TRACE) spResumeLeg = OpexSpanBegin("loop.c121_catalog_resume");
              catalogPending = true;
              local spCatLeg = PROBE_SPAN_TRACE ? OpexSpanBegin("task.catalog") : null;
              this._dispatchCatalog(queuedTask, AIDate.GetYear(AIDate.GetCurrentDate()));
              if (spCatLeg != null) OpexSpanEnd(spCatLeg);
              break;
            }
          }
          local spLegMid = (PROBE_SPAN_TRACE && catalogPending) ? OpexSpanBegin("loop.legacy") : null;
          if (catalogPending) this._runNextTaskWithSlackLedger();
          if (spLegMid != null) OpexSpanEnd(spLegMid);
        }
        if (spResumeLeg != null) OpexSpanEnd(spResumeLeg);
      }
      local spAstarLeg = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.astar_v89") : null;
      if (V89_RAIL_SEARCH_THROUGHPUT) this._advanceRailSearchThroughput();
      if (spAstarLeg != null) OpexSpanEnd(spAstarLeg);
      if (C67_SLACK_HOOK) {
        local spC67Leg = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.c67") : null;
        this._c67SlackHook();
        if (spC67Leg != null) OpexSpanEnd(spC67Leg);
      }
      local spSleepLeg = PROBE_SPAN_TRACE ? OpexSpanBegin("loop.sleep") : null;
      AIController.Sleep(1);
      if (spSleepLeg != null) OpexSpanEnd(spSleepLeg);
    }
  }
}
